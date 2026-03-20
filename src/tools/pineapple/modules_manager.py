"""
ERR0RS Pineapple Modules Manager
Install, remove, configure, and control Pineapple modules:
Evil Portal, DNSspoof, urlsnarf, tcpdump, and more.
"""

from .pineapple_client import PineappleClient


class ModulesManager:
    """
    Manage WiFi Pineapple modules.
    Key modules for red team ops:
      - Evil Portal   : Captive portal credential harvest
      - DNSspoof      : DNS spoofing / redirect
      - urlsnarf      : Capture URLs from HTTP traffic
      - tcpdump       : Raw packet capture
      - nmap          : Port scanning from Pineapple
      - SSLsplit      : SSL interception
    """

    def __init__(self, client: PineappleClient):
        self.client = client

    # ------------------------------------------------------------------ #
    #  MODULE MANAGEMENT                                                  #
    # ------------------------------------------------------------------ #

    def list_installed(self) -> list:
        """List all installed Pineapple modules"""
        result = self.client.get("/api/modules")
        return result.get("modules", result)

    def list_available(self) -> list:
        """List modules available for install from Pineapple repo"""
        result = self.client.get("/api/modules/available")
        return result.get("modules", result)

    def install(self, module_name: str, storage: str = "internal") -> dict:
        """
        Install a module. storage = 'internal' or 'sd'.
        Common module names: EvilPortal, DNSspoof, urlsnarf, tcpdump,
        nmap, SSLsplit, Deauth, Recon, MacChanger
        """
        return self.client.post("/api/modules/install", {
            "module": module_name,
            "storage": storage
        })

    def remove(self, module_name: str) -> dict:
        """Remove an installed module"""
        return self.client.delete(f"/api/modules/{module_name}")

    def start(self, module_name: str) -> dict:
        """Start a module"""
        return self.client.post(f"/api/modules/{module_name}/start")

    def stop(self, module_name: str) -> dict:
        """Stop a running module"""
        return self.client.post(f"/api/modules/{module_name}/stop")

    def status(self, module_name: str) -> dict:
        """Get status of a specific module"""
        return self.client.get(f"/api/modules/{module_name}")

    def configure(self, module_name: str, config: dict) -> dict:
        """Configure a module with given settings dict"""
        return self.client.put(f"/api/modules/{module_name}/config", config)

    # ------------------------------------------------------------------ #
    #  EVIL PORTAL                                                        #
    # ------------------------------------------------------------------ #

    def evil_portal_start(self, portal_name: str = "default") -> dict:
        """
        Start Evil Portal captive portal.
        Victims connecting to Pineapple get redirected to the portal page.
        Credentials they enter are captured in the portal log.
        """
        self.configure("EvilPortal", {"portal": portal_name, "enabled": True})
        return self.start("EvilPortal")

    def evil_portal_stop(self) -> dict:
        """Stop Evil Portal"""
        return self.stop("EvilPortal")

    def evil_portal_get_creds(self) -> list:
        """Retrieve credentials captured by Evil Portal"""
        result = self.client.get("/api/modules/EvilPortal/credentials")
        return result.get("credentials", result)

    def evil_portal_list_portals(self) -> list:
        """List available portal templates"""
        result = self.client.get("/api/modules/EvilPortal/portals")
        return result.get("portals", result)

    def evil_portal_set_portal(self, portal_name: str) -> dict:
        """Switch to a different portal template"""
        return self.configure("EvilPortal", {"portal": portal_name})

    # ------------------------------------------------------------------ #
    #  DNS SPOOF                                                          #
    # ------------------------------------------------------------------ #

    def dnsspoof_start(self, rules: list[dict] = None) -> dict:
        """
        Start DNS spoofing.
        rules format: [{"domain": "example.com", "address": "192.168.1.100"}]
        If no rules given, redirects all DNS to Pineapple IP.
        """
        if rules:
            self.configure("DNSspoof", {"rules": rules})
        return self.start("DNSspoof")

    def dnsspoof_stop(self) -> dict:
        """Stop DNS spoofing"""
        return self.stop("DNSspoof")

    def dnsspoof_add_rule(self, domain: str, redirect_ip: str) -> dict:
        """Add a DNS spoof rule: redirect domain to specific IP"""
        return self.client.post("/api/modules/DNSspoof/rules", {
            "domain": domain,
            "address": redirect_ip
        })

    def dnsspoof_redirect_all(self, redirect_ip: str = None) -> dict:
        """Redirect ALL DNS queries to given IP (or Pineapple IP)"""
        ip = redirect_ip or self.client.ip
        return self.dnsspoof_add_rule("*", ip)

    # ------------------------------------------------------------------ #
    #  TRAFFIC CAPTURE                                                    #
    # ------------------------------------------------------------------ #

    def urlsnarf_start(self, interface: str = "br-lan") -> dict:
        """Start urlsnarf to capture all HTTP URLs from connected clients"""
        self.configure("urlsnarf", {"interface": interface})
        return self.start("urlsnarf")

    def urlsnarf_stop(self) -> dict:
        return self.stop("urlsnarf")

    def urlsnarf_get_log(self) -> list:
        """Get captured URLs from urlsnarf"""
        result = self.client.get("/api/modules/urlsnarf/log")
        return result.get("urls", result)

    def tcpdump_start(self, interface: str = "br-lan",
                      filter_expr: str = "", output_file: str = "capture.pcap") -> dict:
        """
        Start tcpdump packet capture.
        filter_expr: BPF filter e.g. 'port 80' or 'host 192.168.1.100'
        Output saved to Pineapple filesystem.
        """
        return self.configure("tcpdump", {
            "interface": interface,
            "filter": filter_expr,
            "outputFile": output_file,
            "enabled": True
        })

    def tcpdump_stop(self) -> dict:
        return self.stop("tcpdump")

    # ------------------------------------------------------------------ #
    #  MAC CHANGER                                                        #
    # ------------------------------------------------------------------ #

    def mac_changer_randomize(self, interface: str = "wlan0") -> dict:
        """Randomize Pineapple MAC address on given interface"""
        return self.client.post("/api/modules/MacChanger/randomize",
                                {"interface": interface})

    def mac_changer_set(self, mac: str, interface: str = "wlan0") -> dict:
        """Set a specific MAC address on given interface"""
        return self.client.post("/api/modules/MacChanger/set",
                                {"interface": interface, "mac": mac})
