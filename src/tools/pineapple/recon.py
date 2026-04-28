"""
ERR0RS Pineapple Recon
Site survey, client discovery, handshake capture, and loot export.
"""

import json
from pathlib import Path
from .pineapple_client import PineappleClient

LOOT_DIR = Path(__file__).parent / "loot"


class PineappleRecon:
    """
    Recon operations using the WiFi Pineapple Nano:
    - Site survey (scan nearby access points)
    - Client list (devices currently connected)
    - Handshake capture requests
    - Loot export for ERR0RS reporting
    """

    def __init__(self, client: PineappleClient):
        self.client = client
        LOOT_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    #  SITE SURVEY                                                        #
    # ------------------------------------------------------------------ #

    def site_survey(self, interface: str = "wlan1") -> list:
        """
        Scan for nearby access points using the Pineapple's radio.
        Returns list of APs with SSID, BSSID, channel, encryption, signal.
        """
        result = self.client.post("/api/recon/survey", {"interface": interface})
        return result.get("networks", result)

    def site_survey_summary(self, interface: str = "wlan1") -> dict:
        """Run site survey and return summary statistics"""
        networks = self.site_survey(interface)
        if not isinstance(networks, list):
            return {"error": str(networks)}
        open_nets   = [n for n in networks if n.get("encryption", "").upper() in ("", "NONE", "OPN")]
        wpa2_nets   = [n for n in networks if "WPA2" in n.get("encryption", "").upper()]
        wpa3_nets   = [n for n in networks if "WPA3" in n.get("encryption", "").upper()]
        hidden_nets = [n for n in networks if not n.get("ssid", "").strip()]
        return {
            "total":   len(networks),
            "open":    len(open_nets),
            "wpa2":    len(wpa2_nets),
            "wpa3":    len(wpa3_nets),
            "hidden":  len(hidden_nets),
            "networks": networks,
            "open_networks": open_nets
        }

    def find_open_networks(self, interface: str = "wlan1") -> list:
        """Return only open (unencrypted) networks from site survey"""
        summary = self.site_survey_summary(interface)
        return summary.get("open_networks", [])

    # ------------------------------------------------------------------ #
    #  CLIENT DISCOVERY                                                   #
    # ------------------------------------------------------------------ #

    def get_clients(self) -> list:
        """Get all clients currently connected to the Pineapple"""
        result = self.client.get("/api/clients")
        return result.get("clients", result)

    def get_client_details(self, mac: str) -> dict:
        """Get detailed info about a specific connected client"""
        import urllib.parse
        return self.client.get(f"/api/clients/{urllib.parse.quote(mac, safe='')}")

    def deauth_client(self, mac: str, bssid: str, interface: str = "wlan0") -> dict:
        """
        Send deauth frames to kick a client off their current AP.
        Forces them to re-probe and potentially connect to the Pineapple.
        Requires: target client MAC and their current AP BSSID.
        """
        return self.client.post("/api/pineap/deauth", {
            "client": mac,
            "ap": bssid,
            "interface": interface,
            "count": 10
        })

    def deauth_all(self, bssid: str, interface: str = "wlan0") -> dict:
        """Deauth ALL clients from a specific AP"""
        return self.client.post("/api/pineap/deauth", {
            "ap": bssid,
            "interface": interface,
            "count": 10,
            "broadcast": True
        })

    # ------------------------------------------------------------------ #
    #  HANDSHAKE CAPTURE                                                  #
    # ------------------------------------------------------------------ #

    def start_handshake_capture(self, bssid: str = None,
                                interface: str = "wlan1mon") -> dict:
        """
        Start capturing WPA handshakes.
        Optionally filter by target BSSID.
        Handshakes are saved to the Pineapple and retrievable via get_handshakes().
        """
        payload = {"interface": interface}
        if bssid:
            payload["bssid"] = bssid
        return self.client.post("/api/capture/start", payload)

    def stop_handshake_capture(self) -> dict:
        """Stop active handshake capture"""
        return self.client.post("/api/capture/stop")

    def get_handshakes(self) -> list:
        """Get list of captured handshake files"""
        result = self.client.get("/api/capture/handshakes")
        return result.get("handshakes", result)

    def download_handshake(self, filename: str, output_dir: str = None) -> dict:
        """Download a captured handshake file to local loot directory"""
        import urllib.request
        out = Path(output_dir) if output_dir else LOOT_DIR
        out.mkdir(parents=True, exist_ok=True)
        dest = out / filename
        url  = f"{self.client.base_url}/api/capture/handshakes/{filename}"
        try:
            headers = {}
            if self.client.token:
                headers["Authorization"] = f"Bearer {self.client.token}"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                dest.write_bytes(resp.read())
            return {"success": True, "saved_to": str(dest)}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # ------------------------------------------------------------------ #
    #  LOOT EXPORT                                                        #
    # ------------------------------------------------------------------ #

    def export_all_loot(self, output_dir: str = None) -> dict:
        """Export everything: site survey, clients, handshake list"""
        out = Path(output_dir) if output_dir else LOOT_DIR
        out.mkdir(parents=True, exist_ok=True)
        survey    = self.site_survey_summary()
        clients   = self.get_clients()
        handshakes= self.get_handshakes()
        (out / "site_survey.json").write_text(json.dumps(survey, indent=2))
        (out / "clients.json").write_text(json.dumps(clients, indent=2))
        (out / "handshakes.json").write_text(json.dumps(handshakes, indent=2))
        return {
            "success": True,
            "output_dir": str(out),
            "networks_found": survey.get("total", 0),
            "clients_found": len(clients) if isinstance(clients, list) else "?",
            "handshakes_found": len(handshakes) if isinstance(handshakes, list) else "?"
        }
