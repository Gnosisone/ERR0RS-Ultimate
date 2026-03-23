"""
ERR0RS-Ultimate | OPSEC Mode
Operational Security guidance for penetration testers and red teamers.
Covers: anonymity, traffic obfuscation, persona management, anti-forensics, engagement hygiene.
TEACH + DEFEND on every technique — purple team philosophy.
"""

import subprocess
import shutil

OPSEC_BANNER = """
╔══════════════════════════════════════════════════════════╗
║         👁  ERR0RS OPSEC Mode  👁                        ║
║   Anonymity · Traffic Obfuscation · Persona Management   ║
╚══════════════════════════════════════════════════════════╝
[!] OPSEC guidance is for authorized penetration testing only.
    Misuse against systems you don't own is illegal.
"""

# ─────────────────────────────────────────────
#  TOR / PROXYCHAINS SETUP
# ─────────────────────────────────────────────

TOR_SETUP_GUIDE = """
═══════════════════════════════════════
  TOR + PROXYCHAINS SETUP
═══════════════════════════════════════

[TEACH] Tor routes traffic through 3+ relays (guard → middle → exit).
        Your real IP is hidden from the target — they see only the exit node.
        ProxyChains forces any tool through Tor (or SOCKS5 proxy chain).

[STEP 1] Install and start Tor
  sudo apt install tor -y
  sudo systemctl start tor
  sudo systemctl enable tor
  ss -tlnp | grep 9050     ← confirm Tor SOCKS5 listener

[STEP 2] Configure ProxyChains
  sudo nano /etc/proxychains4.conf
  ─ Ensure these settings:
    strict_chain          (use all proxies in order)
    proxy_dns             (route DNS through proxy too!)
    [ProxyList]
    socks5  127.0.0.1 9050

[STEP 3] Use ProxyChains with tools
  proxychains4 nmap -sT -Pn TARGET        (TCP connect scan only — SYN won't work through Tor)
  proxychains4 curl https://check.torproject.org
  proxychains4 sqlmap -u http://TARGET/page?id=1
  proxychains4 msfconsole

[STEP 4] Verify your exit IP
  proxychains4 curl -s https://api.ipify.org

[OPSEC WARNINGS]
  ✗ Never log into personal accounts through Tor (deanonymization!)
  ✗ Tor exit nodes are publicly listed — target can see you're using Tor
  ✗ JavaScript in browser can leak real IP — use Tor Browser, not just proxychains

[DEFEND] Log source IPs. Tor exit node IPs are public — block/alert on them.
         Use canary tokens to detect Tor-based reconnaissance.
"""

# ─────────────────────────────────────────────
#  MAC ADDRESS SPOOFING
# ─────────────────────────────────────────────

MAC_SPOOF_GUIDE = """
═══════════════════════════════════════
  MAC ADDRESS SPOOFING
═══════════════════════════════════════

[TEACH] MAC address uniquely identifies your NIC at Layer 2.
        Spoofing prevents local network logging from recording your real hardware ID.
        Critical for physical engagements and wireless attacks.

[STEP 1] Check current MAC
  ip link show eth0
  ip link show wlan0

[STEP 2] Spoof with macchanger
  sudo apt install macchanger -y
  sudo ip link set wlan0 down
  sudo macchanger -r wlan0          ← random MAC
  sudo macchanger -m AA:BB:CC:DD:EE:FF wlan0  ← specific MAC
  sudo ip link set wlan0 up
  macchanger -s wlan0               ← verify new MAC

[STEP 3] Spoof with ip command (no extra tool)
  sudo ip link set dev wlan0 address AA:BB:CC:DD:EE:FF

[OPSEC NOTES]
  • Use a MAC from the same vendor as surrounding devices (blend in)
  • Check vendor OUI: https://macvendors.com
  • MACs only matter on the local segment — beyond your router, IP is what identifies you

[DEFEND] 802.1X NAC (Network Access Control) ties port access to device certificates.
         ARP monitoring can detect rapid MAC changes.
"""

# ─────────────────────────────────────────────
#  VPN OVER TOR / DOUBLE HOP
# ─────────────────────────────────────────────

VPN_TOR_GUIDE = """
═══════════════════════════════════════
  VPN + TOR CHAINING
═══════════════════════════════════════

[TEACH] Layering VPN + Tor adds complexity to attribution.
        Two configurations:
        VPN → Tor:  VPN provider sees your traffic, Tor entry sees VPN IP
        Tor → VPN:  Harder — VPN sees Tor exit IP, but provider knows you paid

[CONFIGURATION: VPN → Tor (most common for pentesters)]
  1. Connect to VPN first (any provider, use cryptocurrency payment)
  2. Start Tor: sudo systemctl start tor
  3. Route all traffic: proxychains4 <tool>
  Result: Target sees Tor exit → Tor entry sees VPN IP → VPN sees your real IP

[CONFIGURATION: Whonix (best anonymity)]
  Whonix-Gateway handles all Tor routing at VM level
  Whonix-Workstation has no direct internet — all traffic forced through Tor
  Even malware can't bypass — it's OS-level isolation

[OPSEC NOTES]
  • Paid VPNs with no-log policy: Mullvad (accepts Monero), ProtonVPN
  • Never use free VPNs — they monetize your traffic
  • Tor Browser Bundle > ProxyChains for browser-based recon

[DEFEND] Deep packet inspection can fingerprint Tor traffic.
         VPN + Tor correlation attacks are a real NSA-level threat for high-value targets.
"""

# ─────────────────────────────────────────────
#  PERSONA MANAGEMENT
# ─────────────────────────────────────────────

PERSONA_GUIDE = """
═══════════════════════════════════════
  PERSONA MANAGEMENT
═══════════════════════════════════════

[TEACH] Red team operators create sock puppet identities for:
        • OSINT reconnaissance (target won't know who's asking)
        • Social engineering pretexts
        • Phishing campaign infrastructure

[STEP 1] Build a believable persona
  • Real-sounding name:     use namefakr.com or fakenamegenerator.com
  • Profile photo:          thispersondoesnotexist.com (AI-generated)
  • LinkedIn, Twitter, GitHub with some history (age the account ≥3 months)
  • Email: ProtonMail or Tutanota (no phone verification with Tor)

[STEP 2] Compartmentalization
  • Each persona = separate Whonix VM or Tails live boot
  • Never mix personas (different browser profiles, IPs, writing styles)
  • Different writing style: vary sentence length, vocab, punctuation habits

[STEP 3] Infrastructure separation
  • C2 domains registered via privacy-protecting registrars (Njalla, Porkbun + WHOIS privacy)
  • Pay with Monero for full financial separation
  • Use different VPS providers per engagement

[STEP 4] Tradecraft
  • Check what your tools send (User-Agent strings, metadata in documents)
  • Strip EXIF data: exiftool -all= document.docx
  • Never access persona accounts from your real IP — ever

[OPSEC NOTES]
  Writing style analysis (stylometry) can deanonymize even across personas.
  OPSEC is a discipline, not a tool — it's violated by human mistakes.

[DEFEND] Honeypots in HR/LinkedIn data. Monitor for fake profiles of employees.
         Train staff to verify identity before sharing information.
"""

# ─────────────────────────────────────────────
#  ANTI-FORENSICS / COVERING TRACKS
# ─────────────────────────────────────────────

ANTI_FORENSICS_GUIDE = """
═══════════════════════════════════════
  ANTI-FORENSICS & COVERING TRACKS
═══════════════════════════════════════

[TEACH] Authorized red teams document their artifacts and clean up after engagements.
        Understanding anti-forensics helps blue teamers build better detections.

[STEP 1] Log manipulation (Linux)
  shred -u ~/.bash_history && history -c && history -w
  echo "" > /var/log/auth.log         (if root — wipes auth log)
  echo "" > /var/log/syslog
  sed -i '/YOUR_IP/d' /var/log/auth.log  (targeted line removal)

[STEP 2] Timestomping
  touch -t 202001010000 suspicious_file   (set to Jan 1, 2020)
  touch -r /bin/ls suspicious_file        (copy timestamps from legit file)

[STEP 3] Secure file deletion
  shred -uzn 3 sensitive_file       (overwrite 3x then delete)
  srm -rf directory/                (secure-delete tool)

[STEP 4] In-memory operations (leave no disk artifacts)
  • Load payloads via reflective DLL injection / process hollowing
  • Use fileless malware techniques (PowerShell in-memory execution)
  • Avoid touching disk at all — live off the land (LOLBins)

[STEP 5] Network OPSEC
  • Use encrypted C2 channels (HTTPS, DNS, ICMP tunneling)
  • Blend C2 traffic with normal web traffic (Domain Fronting)
  • Rotate infrastructure after detection

[DEFEND] Immutable logs (WORM storage, remote syslog over TLS).
         SIEM with baseline alerting catches anomalous log gaps.
         File integrity monitoring (Tripwire, AIDE) detects timestomping.
         Memory forensics (Volatility) catches fileless malware.
"""

# ─────────────────────────────────────────────
#  PRE-ENGAGEMENT OPSEC CHECKLIST
# ─────────────────────────────────────────────

CHECKLIST = """
═══════════════════════════════════════
  PRE-ENGAGEMENT OPSEC CHECKLIST
═══════════════════════════════════════

[ ] Signed SOW / Rules of Engagement document on file
[ ] Scope defined (IPs, domains, time window, allowed techniques)
[ ] Emergency contact for client (to abort if needed)
[ ] Dedicated attack VM / OS (not your daily driver)
[ ] VPN or Tor configured and tested
[ ] MAC address spoofed (if physical/wireless engagement)
[ ] Burner email / persona set up (if social engineering in scope)
[ ] C2 infrastructure stood up on separate VPS
[ ] All tools updated: msfconsole, nmap, burpsuite, impacket, crackmapexec
[ ] Wordlists fresh: rockyou, seclists, cewl-generated list from target site
[ ] Screenshot/logging tool running (record EVERYTHING for report)
[ ] Start time logged, engagement clock running
[ ] Notify client engagement has started (required by most SOWs)

POST-ENGAGEMENT CHECKLIST:
[ ] Remove all backdoors, persistence mechanisms, and dropped files
[ ] Revoke created accounts, SSH keys, scheduled tasks
[ ] Restore changed configurations to original state
[ ] Wipe attack VM snapshots containing client data
[ ] Draft debrief report with findings, evidence, remediation
[ ] Schedule debrief call with client
"""


# ─────────────────────────────────────────────
#  MAIN DISPATCHER
# ─────────────────────────────────────────────

def run_opsec(topic: str = "") -> str:
    print(OPSEC_BANNER)
    dispatch = {
        "tor":           TOR_SETUP_GUIDE,
        "proxychains":   TOR_SETUP_GUIDE,
        "mac":           MAC_SPOOF_GUIDE,
        "macspoof":      MAC_SPOOF_GUIDE,
        "vpn":           VPN_TOR_GUIDE,
        "persona":       PERSONA_GUIDE,
        "identity":      PERSONA_GUIDE,
        "antiforensics": ANTI_FORENSICS_GUIDE,
        "anti-forensics": ANTI_FORENSICS_GUIDE,
        "tracks":        ANTI_FORENSICS_GUIDE,
        "covering":      ANTI_FORENSICS_GUIDE,
        "checklist":     CHECKLIST,
        "preengagement": CHECKLIST,
    }
    guide = dispatch.get(topic.lower().replace(" ", "").replace("_", ""))
    if guide:
        return guide
    # Default: full menu
    menu = "\n[OPSEC Mode — Choose a Topic]\n\n"
    menu += "  tor            — Tor + ProxyChains setup and usage\n"
    menu += "  mac            — MAC address spoofing\n"
    menu += "  vpn            — VPN + Tor chaining (Whonix, Mullvad)\n"
    menu += "  persona        — Sock puppet / persona management\n"
    menu += "  antiforensics  — Covering tracks, timestomping, log manipulation\n"
    menu += "  checklist      — Pre/post engagement OPSEC checklist\n\n"
    menu += "  Example: 'opsec tor'  |  'opsec checklist'  |  'opsec persona'\n"
    return menu
