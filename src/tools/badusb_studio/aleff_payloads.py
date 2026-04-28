"""
ERR0RS ULTIMATE — Aleff BadUSB Payload Library
================================================
Integrates aleff-github/my-flipper-shits into the ERR0RS
Payload Studio and Flipper Zero auto-load system.

Source: https://github.com/aleff-github/my-flipper-shits
License: GPL-3.0
Author credit: aleff (Aleff) | github.com/aleff-github

92 payloads across Windows (52), GNU-Linux (33), iOS (5), macOS (2).

PAP Legend:
  green  = Plug-and-Play, no config needed
  yellow = Needs minor config (webhook URL, token, etc.)
  red    = Manual setup required

Purple Team format: every payload has teach + defend notes.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional

ALEFF_REPO_URL  = "https://github.com/aleff-github/my-flipper-shits"
ALEFF_AUTHOR    = "aleff (Aleff)"
ALEFF_LICENSE   = "GPL-3.0"


@dataclass
class AleffPayload:
    name:        str
    category:    str          # Credentials, Exfiltration, Execution, Phishing, Prank, Incident_Response
    platform:    str          # Windows, GNU-Linux, iOS, macOS
    pap:         str          # green | yellow | red
    path:        str          # path inside the repo
    description: str
    teach:       str          # ERR0RS teach note — what it does and why
    defend:      str          # Blue team detection / remediation
    config_needed: List[str] = field(default_factory=list)  # What the operator must configure
    mitre:       List[str]   = field(default_factory=list)


# ── PAYLOAD CATALOGUE ────────────────────────────────────────────────────────
# Full 92-payload library from aleff-github/my-flipper-shits
# Organized by platform → category → name

ALEFF_PAYLOADS: List[AleffPayload] = [

    # ═══════════════════════════════════════════════════════
    # WINDOWS — CREDENTIALS
    # ═══════════════════════════════════════════════════════
    AleffPayload(
        name        = "WiFi Windows Passwords",
        category    = "Credentials",
        platform    = "Windows",
        pap         = "yellow",
        path        = "Windows/Credentials/WiFiPasswords_Windows",
        description = "Extracts all saved WiFi passwords from Windows and exfiltrates via Discord webhook.",
        teach       = "Windows stores WiFi credentials in plain text accessible via 'netsh wlan show profile name=X key=clear'. This payload automates extraction of every saved network and sends the results to a Discord webhook. No admin rights required — any logged-in user can read their own saved WiFi passwords.",
        defend      = "Disable Discord webhook exfiltration at the network perimeter (block outbound to discord.com/api/webhooks). Use Windows Credential Guard to protect stored credentials. Monitor for netsh wlan commands in process creation logs (Event 4688).",
        config_needed = ["Discord Webhook URL"],
        mitre       = ["T1081 - Credentials in Files", "T1048 - Exfiltration Over Alternative Protocol"]
    ),
    AleffPayload(
        name        = "Defend Against CVE-2023-23397",
        category    = "Credentials",
        platform    = "Windows",
        pap         = "green",
        path        = "Windows/Credentials/Defend_yourself_from_CVE-2023-23397",
        description = "Defensive payload that patches CVE-2023-23397 (Outlook NTLM hash theft via calendar invite). Plug-and-play — no config needed.",
        teach       = "CVE-2023-23397 is a critical Outlook vulnerability where a specially crafted calendar invite causes Windows to authenticate to an attacker-controlled SMB server, leaking the user's NTLM hash without any user interaction. This defensive payload applies the recommended registry fix.",
        defend      = "This IS the defense. Apply KB5023478 patch. Block outbound SMB (port 445) to internet at the firewall. Use Protected Users security group for privileged accounts.",
        config_needed = [],
        mitre       = ["T1187 - Forced Authentication", "T1557.001 - NTLM Relay"]
    ),

    # ═══════════════════════════════════════════════════════
    # WINDOWS — EXFILTRATION
    # ═══════════════════════════════════════════════════════
    AleffPayload(
        name        = "Exfiltrate Windows Product Key",
        category    = "Exfiltration",
        platform    = "Windows",
        pap         = "yellow",
        path        = "Windows/Exfiltration/Exfiltrate_Windows_Product_Key",
        description = "Retrieves the Windows product key and license type, exfiltrates via Discord webhook. No admin needed.",
        teach       = "Windows product keys are stored in WMI (SoftwareLicensingService). The command 'wmic path softwarelicensingservice get OA3xOriginalProductKey' retrieves it without elevation. This demonstrates how basic system information that seems benign is actually valuable data — product keys confirm genuine OS, reveal volume licensing, and can be resold.",
        defend      = "Block outbound Discord webhook requests at the perimeter. Monitor for wmic.exe querying SoftwareLicensingService (unusual in normal operation). USB Device Control policies prevent BadUSB devices from enumerating as keyboards.",
        config_needed = ["Discord Webhook URL"],
        mitre       = ["T1082 - System Information Discovery", "T1048 - Exfiltration Over Alternative Protocol"]
    ),
    AleffPayload(
        name        = "Exfiltrate Process Info (Windows)",
        category    = "Exfiltration",
        platform    = "Windows",
        pap         = "yellow",
        path        = "Windows/Exfiltration/ExfiltrateProcessInfo_Windows",
        description = "Dumps running processes and system info, exfiltrates via Discord webhook.",
        teach       = "Running process enumeration reveals installed security software (AV/EDR processes), active applications, and system state. 'Get-Process' or tasklist output tells an attacker which defenses are running, what applications are open, and potential injection targets. This is reconnaissance done physically in seconds.",
        defend      = "Monitor Get-Process and tasklist in PowerShell logs (Event 4104). Block unauthorized outbound webhooks. Physical security: lock workstations when unattended, USB port locks.",
        config_needed = ["Discord Webhook URL"],
        mitre       = ["T1057 - Process Discovery", "T1048 - Exfiltration Over Alternative Protocol"]
    ),
    AleffPayload(
        name        = "Exfiltrate Computer Screenshots",
        category    = "Exfiltration",
        platform    = "Windows",
        pap         = "yellow",
        path        = "Windows/Exfiltration/ExfiltrateComputerScreenshots",
        description = "Takes a screenshot of all monitors and exfiltrates the image via Discord webhook.",
        teach       = "Screenshots capture whatever the user has on screen at that moment — open documents, emails, application data, sensitive files. Combined with physical access, a screenshot payload captures what cannot be extracted by reading files (e.g., a document open in a DRM-protected viewer). Runs silently in a hidden PowerShell window.",
        defend      = "PowerShell transcription logging (Event 4104) catches screenshot commands. EDR behavioral detection of hidden PowerShell windows. Physical access controls are the root defense here.",
        config_needed = ["Discord Webhook URL"],
        mitre       = ["T1113 - Screen Capture", "T1048 - Exfiltration Over Alternative Protocol"]
    ),
    AleffPayload(
        name        = "Export Cookies From Firefox",
        category    = "Exfiltration",
        platform    = "Windows",
        pap         = "yellow",
        path        = "Windows/Exfiltration/Export_Cookies_From_Firefox",
        description = "Copies Firefox's cookies.sqlite database and exfiltrates via Discord webhook. Captures all active session tokens.",
        teach       = "Browser cookies contain session tokens that authenticate you to websites. Stealing cookies = stealing sessions, bypassing passwords AND MFA entirely. Firefox stores cookies in %APPDATA%\\Mozilla\\Firefox\\Profiles\\*.default\\cookies.sqlite. A plain file copy gets every active session. The attacker imports the cookie into their browser and is logged in as you.",
        defend      = "Only hardware MFA (FIDO2/WebAuthn) resists cookie theft — session cookies become worthless if the session requires device binding. Clear cookies on browser close. Use separate browser profiles for privileged access. Monitor for reads of Firefox profile directories from unexpected processes.",
        config_needed = ["Discord Webhook URL"],
        mitre       = ["T1539 - Steal Web Session Cookie", "T1048 - Exfiltration Over Alternative Protocol"]
    ),
    AleffPayload(
        name        = "Exfiltrate Download Links History",
        category    = "Exfiltration",
        platform    = "Windows",
        pap         = "yellow",
        path        = "Windows/Exfiltration/Exports_all_the_links_of_the_downloads",
        description = "Extracts all download history links from the browser and exfiltrates via Discord webhook.",
        teach       = "Browser download history reveals what software a user installed, what documents they received, and what external services they use. Download links can expose internal file shares, cloud storage URLs with embedded tokens, and confirm software versions for targeted exploit development.",
        defend      = "Monitor browser history access from non-browser processes. USB Device Control to block HID enumeration of unauthorized devices.",
        config_needed = ["Discord Webhook URL"],
        mitre       = ["T1217 - Browser Bookmark Discovery", "T1048 - Exfiltration Over Alternative Protocol"]
    ),
    AleffPayload(
        name        = "Exfiltrate OS Tree Structure",
        category    = "Exfiltration",
        platform    = "Windows",
        pap         = "yellow",
        path        = "Windows/Exfiltration/Tree_structure_of_the_operating_system",
        description = "Runs tree /f on key directories and exfiltrates the full filesystem structure via Discord webhook.",
        teach       = "A filesystem tree reveals installed applications, user directories, sensitive file locations, and organizational structure — all without opening a single file. Attackers use this for targeted follow-up: knowing C:\\Finance\\Q3_Payroll.xlsx exists is enough to plan a second attack.",
        defend      = "Monitor tree.exe or Get-ChildItem with recurse flags from unauthorized sources. Block webhook exfiltration at perimeter.",
        config_needed = ["Discord Webhook URL"],
        mitre       = ["T1083 - File and Directory Discovery", "T1048 - Exfiltration Over Alternative Protocol"]
    ),
    AleffPayload(
        name        = "Export Thunderbird Settings",
        category    = "Exfiltration",
        platform    = "Windows",
        pap         = "yellow",
        path        = "Windows/Exfiltration/Save_Your_Thunderbird_Settings",
        description = "Exfiltrates Thunderbird email client configuration including saved account credentials.",
        teach       = "Thunderbird stores email account configurations including passwords in its profile directory. Exfiltrating the profile gives access to email credentials, SMTP/IMAP servers, and potentially OAuth tokens. Email access is a high-value pivot for business email compromise (BEC) attacks.",
        defend      = "Use OS credential manager integration rather than app-stored passwords. Monitor Thunderbird profile directory access from non-Thunderbird processes.",
        config_needed = ["Discord Webhook URL"],
        mitre       = ["T1539 - Steal Web Session Cookie", "T1528 - Steal Application Access Token"]
    ),
    AleffPayload(
        name        = "Create And Exfiltrate Discord Webhook",
        category    = "Exfiltration",
        platform    = "Windows",
        pap         = "yellow",
        path        = "Windows/Exfiltration/Create_And_Exfiltrate_A_Webhook_Of_Discord",
        description = "Creates a new Discord webhook in any server the user has access to and exfiltrates the webhook URL.",
        teach       = "If a target is logged into Discord with server admin permissions, this payload creates a persistent exfiltration channel that survives beyond the physical access window. The attacker now has a webhook URL they control — they can send messages posing as the compromised server, or use it as a C2 channel.",
        defend      = "Restrict webhook creation permissions to administrators only. Audit webhook creation events in Discord server audit logs. Monitor for Discord API calls from unexpected processes.",
        config_needed = ["Discord server access on target machine"],
        mitre       = ["T1071.001 - Application Layer Protocol: Web Protocols", "T1566 - Phishing"]
    ),
    AleffPayload(
        name        = "ProtonVPN Config Exfiltration",
        category    = "Exfiltration",
        platform    = "Windows",
        pap         = "yellow",
        path        = "Windows/Exfiltration/ProtonVPNConfigFile_Windows",
        description = "Extracts ProtonVPN configuration files and credentials via Discord webhook.",
        teach       = "VPN configuration files often contain pre-shared keys, certificates, or saved credentials. Extracting a ProtonVPN config lets an attacker authenticate to the same VPN endpoint as the victim, masking their traffic origin and potentially accessing VPN-connected internal resources.",
        defend      = "Store VPN credentials in OS credential manager, not in plaintext config files. Monitor VPN profile directory access.",
        config_needed = ["Discord Webhook URL"],
        mitre       = ["T1552 - Unsecured Credentials", "T1048 - Exfiltration Over Alternative Protocol"]
    ),
    AleffPayload(
        name        = "Exfiltrate Adobe Reader Certificates",
        category    = "Exfiltration",
        platform    = "Windows",
        pap         = "yellow",
        path        = "Windows/Exfiltration/Export_all_saved_certificates_with_Adobe_Reader",
        description = "Exports all certificates saved in Adobe Reader's trusted certificate store.",
        teach       = "Adobe Reader maintains its own certificate trust store. Certificates used for document signing, encryption, or authentication represent high-value identity artifacts. Exfiltrating them can enable document forgery or authentication bypass depending on certificate purpose.",
        defend      = "Monitor Adobe Reader profile directory access from non-Adobe processes. Certificate management should use OS-level certificate stores with appropriate ACLs.",
        config_needed = ["Discord Webhook URL"],
        mitre       = ["T1552.004 - Private Keys", "T1048 - Exfiltration Over Alternative Protocol"]
    ),
    AleffPayload(
        name        = "Exfiltrate Notion Client Database",
        category    = "Exfiltration",
        platform    = "Windows",
        pap         = "yellow",
        path        = "Windows/Exfiltration/Exfiltrates_the_entire_database_of_the_Notion_client",
        description = "Extracts the entire local Notion client SQLite database containing cached workspace content.",
        teach       = "Notion's desktop client caches workspace content in a local SQLite database. This contains notes, documents, databases, and project data — essentially the entire workspace available offline. Exfiltrating this database gives access to sensitive business information without ever touching Notion's servers.",
        defend      = "Disable Notion desktop client offline caching where not needed. Monitor Notion appdata directory access from non-Notion processes.",
        config_needed = ["Discord Webhook URL"],
        mitre       = ["T1005 - Data from Local System", "T1048 - Exfiltration Over Alternative Protocol"]
    ),
    AleffPayload(
        name        = "Windows Netstat Exfiltration",
        category    = "Exfiltration",
        platform    = "Windows",
        pap         = "red",
        path        = "Windows/Exfiltration/Netstat_Windows",
        description = "Captures active network connections and listening ports, exfiltrates via configured endpoint.",
        teach       = "Netstat output reveals every active network connection: what the machine is talking to, what services are listening, and what remote IPs are currently connected. For an attacker mapping a network, a netstat from one machine reveals internal IPs, service ports, and potentially VPN/remote desktop connections to other systems.",
        defend      = "Monitor netstat.exe execution from non-administrative contexts. Network monitoring tools (Zeek, Suricata) already capture this data — the attacker is just saving you a step for their own use.",
        config_needed = ["Exfiltration endpoint (custom setup required)"],
        mitre       = ["T1049 - System Network Connections Discovery", "T1046 - Network Service Discovery"]
    ),

    # ═══════════════════════════════════════════════════════
    # WINDOWS — EXECUTION
    # ═══════════════════════════════════════════════════════
    AleffPayload(
        name        = "Install Official VSCode Extension",
        category    = "Execution",
        platform    = "Windows",
        pap         = "green",
        path        = "Windows/Execution/Install_Official_VSCode_Extension",
        description = "Silently installs any official VSCode extension by ID. Plug-and-play.",
        teach       = "VSCode extensions have full access to the filesystem, network, and terminal. A malicious extension is a persistent backdoor that survives reboots and looks legitimate. This payload demonstrates how physical access can plant a malicious extension — or how to quickly deploy security extensions (SARIF Viewer, GitLens, etc.) across a fleet.",
        defend      = "Restrict extension installation to approved list via VSCode policy (extensions.allowed). Monitor VSCode extension installation events. Audit installed extensions regularly.",
        config_needed = [],
        mitre       = ["T1176 - Browser Extensions", "T1059 - Command and Scripting Interpreter"]
    ),
    AleffPayload(
        name        = "Install Arbitrary VSCode Extension",
        category    = "Execution",
        platform    = "Windows",
        pap         = "yellow",
        path        = "Windows/Execution/Install_Any_Arbitrary_VSCode_Extension",
        description = "Installs any specified VSCode extension (official or arbitrary) silently.",
        teach       = "By specifying any extension ID, an attacker can install a custom malicious extension from the VSCode marketplace or a local path. Extensions run with full user privileges and can exfiltrate code, keylog, establish C2 channels, or modify code before compilation.",
        defend      = "Use extensions.allowed policy to whitelist approved extensions. Endpoint monitoring for code --install-extension commands.",
        config_needed = ["Extension ID to install"],
        mitre       = ["T1176 - Browser Extensions", "T1059.001 - PowerShell"]
    ),
    AleffPayload(
        name        = "Set Arbitrary DNS (IPv4)",
        category    = "Execution",
        platform    = "Windows",
        pap         = "green",
        path        = "Windows/Execution/Set_An_Arbitrary_DNS-IPv4_version",
        description = "Changes Windows DNS server settings to a specified IPv4 address. Plug-and-play.",
        teach       = "Changing DNS servers is a classic attack: route all hostname lookups through an attacker-controlled DNS server for logging (passive surveillance) or DNS hijacking (redirect login pages to phishing sites). Takes 2 seconds physically. The victim notices nothing until connections start failing or getting redirected.",
        defend      = "Monitor registry changes to DNS server settings (HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters). Use DHCP with DNS enforcement. Network monitoring for DNS traffic to unexpected resolvers.",
        config_needed = [],
        mitre       = ["T1565.001 - Stored Data Manipulation", "T1557 - Adversary-in-the-Middle"]
    ),
    AleffPayload(
        name        = "Set Tor Arbitrary Circuit",
        category    = "Execution",
        platform    = "Windows",
        pap         = "yellow",
        path        = "Windows/Execution/Set_An_Arbitrary_And_Persistent_Tor_Circuit",
        description = "Configures Tor to use specific entry/middle/exit nodes for a persistent, controlled circuit.",
        teach       = "By controlling which Tor nodes are used in the circuit, an attacker (or researcher) can ensure traffic routes through specific jurisdictions or trusted relays. This is advanced Tor tradecraft — controlling the circuit removes the randomness that could route traffic through a compromised node.",
        defend      = "Monitor torrc file modifications. Block Tor traffic at the network perimeter (Tor guard node IPs are published). Detect Tor usage via traffic analysis (JA3 fingerprinting, timing patterns).",
        config_needed = ["Entry/Middle/Exit node fingerprints from metrics.torproject.org"],
        mitre       = ["T1090.003 - Multi-hop Proxy", "T1572 - Protocol Tunneling"]
    ),
    AleffPayload(
        name        = "Set Tor Bridge",
        category    = "Execution",
        platform    = "Windows",
        pap         = "yellow",
        path        = "Windows/Execution/Set_Tor_Bridge",
        description = "Configures Tor to use bridge relays, bypassing Tor blocking at the network level.",
        teach       = "Tor bridges are unpublished relays that help users bypass ISP or corporate Tor blocking. Configuring a bridge makes Tor traffic harder to detect and block. Used legitimately in censored countries; used offensively to evade network monitoring that blocks known Tor guard IPs.",
        defend      = "Deep packet inspection for Tor's obfs4 obfuscation protocol. Traffic analysis for timing patterns characteristic of Tor even through bridges.",
        config_needed = ["Bridge relay addresses (from bridges.torproject.org)"],
        mitre       = ["T1090.003 - Multi-hop Proxy", "T1572 - Protocol Tunneling"]
    ),
    AleffPayload(
        name        = "Close All Applications",
        category    = "Execution",
        platform    = "Windows",
        pap         = "green",
        path        = "Windows/Execution/CloseAllApplications_Windows",
        description = "Force-closes all running user applications. Plug-and-play.",
        teach       = "Used in physical access scenarios to clear the screen before executing follow-up payloads (so the user returns to a 'clean' desktop), or as a disruptive action during red team exercises to simulate ransomware pre-encryption behavior (closing open file handles).",
        defend      = "Monitor for taskkill /f commands or Stop-Process -Force in bulk. Physical security prevents physical access that enables this class of attack.",
        config_needed = [],
        mitre       = ["T1489 - Service Stop", "T1059.001 - PowerShell"]
    ),
    AleffPayload(
        name        = "Add Avast Antivirus Exception",
        category    = "Execution",
        platform    = "Windows",
        pap         = "green",
        path        = "Windows/Execution/Add_An_Excepiton_To_Avast_Antivirus",
        description = "Adds an arbitrary folder path to Avast's exclusion list, blinding it to files in that location.",
        teach       = "AV exclusions are one of the most powerful persistence techniques. Adding C:\\Temp\\ or a user profile folder to AV exclusions allows any malware dropped there to run undetected. This payload demonstrates how physical access for 5 seconds can permanently compromise endpoint protection.",
        defend      = "Monitor AV exclusion modifications (Avast logs, Event 5007 for Windows Defender). Alert on any programmatic modification of AV exclusion lists. Require admin authentication to modify AV settings.",
        config_needed = [],
        mitre       = ["T1562.001 - Impair Defenses: Disable or Modify Tools"]
    ),
    AleffPayload(
        name        = "Change Windows Username",
        category    = "Execution",
        platform    = "Windows",
        pap         = "yellow",
        path        = "Windows/Execution/Change_Windows_User_Name",
        description = "Renames the current Windows user account.",
        teach       = "Renaming a user account is a persistence and evasion technique — if analysts are looking for 'john.doe' in logs, and the account is now named 'svc_backup', correlation becomes harder. Can also be used to impersonate legitimate service accounts.",
        defend      = "Monitor account rename events (Event 4781 - Account name changed). Alert on any username changes outside of IT change management processes.",
        config_needed = ["New username"],
        mitre       = ["T1036 - Masquerading", "T1098 - Account Manipulation"]
    ),
    AleffPayload(
        name        = "Launch Admin PowerShell",
        category    = "Execution",
        platform    = "Windows",
        pap         = "green",
        path        = "Windows/Execution/Starting_a_PowerShell_with_administrator_permissions_in_Windows",
        description = "Opens an elevated PowerShell session by automating the UAC prompt. Plug-and-play.",
        teach       = "Physical access to a logged-in machine with a standard user can still achieve elevation if the UAC prompt can be automated. This payload opens Run (Win+R), launches PowerShell as admin, and handles the UAC confirmation — giving an elevated shell to whoever is physically present.",
        defend      = "Configure UAC to require secure desktop (no automation possible). Require Ctrl+Alt+Del for UAC prompts. Physical security and screen locks are the primary control.",
        config_needed = [],
        mitre       = ["T1548.002 - Abuse Elevation Control Mechanism: Bypass User Account Control"]
    ),
    AleffPayload(
        name        = "Change Windows User Password",
        category    = "Execution",
        platform    = "Windows",
        pap         = "yellow",
        path        = "Windows/Execution/Change_the_password_of_the_windows_user",
        description = "Changes the current Windows local user account password.",
        teach       = "Changing a user's password on an unlocked machine locks them out of their own account and gives the attacker persistent access. The attacker can return later and log in. This is a disruptive, destructive action — use only in authorized engagements. Documents that physical access = account takeover.",
        defend      = "Monitor password change events (Event 4723 - Password change attempt, Event 4724 - Admin reset). Alert on password changes outside of IT workflows.",
        config_needed = ["New password to set"],
        mitre       = ["T1098 - Account Manipulation", "T1531 - Account Access Removal"]
    ),
    AleffPayload(
        name        = "Stop A Single Process",
        category    = "Execution",
        platform    = "Windows",
        pap         = "yellow",
        path        = "Windows/Execution/Stop_A_Single_Process_In_Windows",
        description = "Kills a specific named process — useful for disabling security tools or clearing obstacles.",
        teach       = "Killing a specific process (e.g., the AV process, a DLP agent, a monitoring tool) is the fastest way to blind defenses. Physical access + 5 seconds = security tool disabled. This is why defense-in-depth matters — no single security tool should be the only layer.",
        defend      = "Security tools should run as protected processes (PPL - Protected Process Light) that cannot be killed by user-mode code without kernel-level exploitation. Monitor for taskkill targeting security processes.",
        config_needed = ["Process name to kill"],
        mitre       = ["T1562.001 - Impair Defenses: Disable or Modify Tools", "T1489 - Service Stop"]
    ),
    AleffPayload(
        name        = "Uninstall Specific App via Control Panel",
        category    = "Execution",
        platform    = "Windows",
        pap         = "yellow",
        path        = "Windows/Execution/Uninstall_A_Specific_App_On_Windows_Through_Control_Panel",
        description = "Silently uninstalls a specified application through Control Panel automation.",
        teach       = "Uninstalling security software, VPN clients, or monitoring agents removes protection without leaving obvious malware. An attacker who uninstalls the DLP agent before exfiltrating data bypasses data loss prevention entirely. Demonstrates why tamper protection is critical for security software.",
        defend      = "Security software should require admin credentials AND tamper protection verification to uninstall. Monitor uninstall events (Event Log / Application event source MsiInstaller).",
        config_needed = ["Application name to uninstall"],
        mitre       = ["T1562.001 - Impair Defenses", "T1059.001 - PowerShell"]
    ),
    AleffPayload(
        name        = "Uninstall Signal",
        category    = "Execution",
        platform    = "Windows",
        pap         = "green",
        path        = "Windows/Execution/UninstallSignal",
        description = "Silently uninstalls the Signal encrypted messaging application. Plug-and-play.",
        teach       = "Removing encrypted communications software forces targets to use less secure alternatives. In a corporate espionage scenario, uninstalling Signal prevents secure communications and potentially forces migration to monitored channels. Demonstrates insider threat and physical access risk.",
        defend      = "Monitor application uninstall events. MDM/endpoint management should alert on removal of approved applications.",
        config_needed = [],
        mitre       = ["T1562 - Impair Defenses", "T1059.001 - PowerShell"]
    ),
    AleffPayload(
        name        = "Change Git Remote Link",
        category    = "Execution",
        platform    = "Windows",
        pap         = "yellow",
        path        = "Windows/Execution/ChangeGitRemoteLink",
        description = "Changes a Git repository's remote URL to an attacker-controlled server.",
        teach       = "If a developer pushes code to an attacker-controlled Git remote, the attacker receives all future code commits — including secrets, API keys, and proprietary code embedded in commits. This is a supply chain attack enabled by physical access to a developer workstation.",
        defend      = "Monitor .git/config file modifications. Use Git commit signing (GPG) to detect unauthorized commits. Corporate Git servers should require authentication and audit push origins.",
        config_needed = ["Attacker-controlled Git remote URL"],
        mitre       = ["T1195 - Supply Chain Compromise", "T1565 - Data Manipulation"]
    ),
    AleffPayload(
        name        = "Send Messages In Discord Channel",
        category    = "Execution",
        platform    = "Windows",
        pap         = "yellow",
        path        = "Windows/Execution/Send_Messages_In_Discord_Channel-Server",
        description = "Posts a message to a Discord channel using an existing logged-in Discord session.",
        teach       = "If Discord is open on the target machine, an attacker can post messages appearing to come from the victim's account — spreading misinformation, social engineering other users, or posting malicious links in trusted channels. This is account impersonation without credential theft.",
        defend      = "Log out of Discord when away from desk. Discord session expiry settings. Monitor for unexpected outbound Discord API calls from automated processes.",
        config_needed = ["Discord Webhook URL or channel target"],
        mitre       = ["T1534 - Internal Spearphishing", "T1566 - Phishing"]
    ),
    AleffPayload(
        name        = "Install And Run Arbitrary Executable",
        category    = "Execution",
        platform    = "Windows",
        pap         = "yellow",
        path        = "Windows/Execution/Install_And_Run_Any_Arbitrary_Executable-No_Internet_And_Root_Needed",
        description = "Runs any executable from a specified path. No internet or admin rights required.",
        teach       = "This payload demonstrates that arbitrary code execution via BadUSB requires only a logged-in user session — no elevated privileges, no internet connection. The Flipper types the path to a pre-staged executable and runs it. This is why application whitelisting is critical.",
        defend      = "Application whitelisting (Windows Defender Application Control / AppLocker) prevents unauthorized executables from running regardless of how they're invoked. Monitor for execution of binaries from unusual paths.",
        config_needed = ["Path to executable to run"],
        mitre       = ["T1204 - User Execution", "T1059 - Command and Scripting Interpreter"]
    ),
    AleffPayload(
        name        = "Shutdown After 1 Minute",
        category    = "Execution",
        platform    = "Windows",
        pap         = "green",
        path        = "Windows/Execution/Shutdown_After_1_Minute-By_NexusWannaBe",
        description = "Schedules a system shutdown in 60 seconds. Disruptive/DoS payload. By NexusWannaBe.",
        teach       = "A 60-second shutdown timer is a disruptive payload in physical red team exercises — it forces the user to emergency-save their work and reveals that physical access occurred. Also demonstrates that physical access = ability to disrupt operations, even without data theft.",
        defend      = "Physical security controls. Monitor for shutdown.exe with /t parameter from user-mode processes.",
        config_needed = [],
        mitre       = ["T1529 - System Shutdown/Reboot"]
    ),
    AleffPayload(
        name        = "Immediate Shutdown",
        category    = "Execution",
        platform    = "Windows",
        pap         = "green",
        path        = "Windows/Execution/Immediate_Shutdown-By_NexusWannaBe",
        description = "Immediately forces a system shutdown. No warning. By NexusWannaBe.",
        teach       = "Immediate forced shutdown is a destructive payload. In an authorized engagement it proves physical access capability. In a real attack, forced shutdown during file operations can corrupt data, disrupt active work, and cover tracks by clearing volatile memory (RAM).",
        defend      = "Physical security. BIOS/UEFI password to prevent unauthorized reboots. Monitor shutdown commands from unexpected processes.",
        config_needed = [],
        mitre       = ["T1529 - System Shutdown/Reboot"]
    ),
    AleffPayload(
        name        = "Make Windows Performant",
        category    = "Execution",
        platform    = "Windows",
        pap         = "green",
        path        = "Windows/Execution/Make_Windows_performant_(but_ugly_and_boring)",
        description = "Applies Windows performance optimization settings: disables animations, visual effects, etc.",
        teach       = "Disabling Windows visual effects significantly improves performance on older hardware or VM environments. In a pentest context, this is a benign payload demonstrating that physical access enables arbitrary system configuration changes — without admin rights for user-scoped settings.",
        defend      = "Monitor registry changes to user visual preferences. Group Policy can enforce UI settings.",
        config_needed = [],
        mitre       = ["T1059.001 - PowerShell"]
    ),

    # ═══════════════════════════════════════════════════════
    # WINDOWS — INCIDENT RESPONSE
    # ═══════════════════════════════════════════════════════
    AleffPayload(
        name        = "Defend Against CVE-2023-36884",
        category    = "Incident_Response",
        platform    = "Windows",
        pap         = "green",
        path        = "Windows/Incident_Response/Defend_yourself_against_CVE-2023-36884_Office_and_Windows_HTML_Remote_Code_Execution_Vulnerability",
        description = "Applies registry-based defense against CVE-2023-36884 Office/Windows HTML RCE. Plug-and-play.",
        teach       = "CVE-2023-36884 is a remote code execution vulnerability in Microsoft Office and Windows HTML that was exploited by Russian APT group RomCom in 2023. Opening a specially crafted Office document triggers execution without user interaction beyond opening the file. This payload applies the recommended registry mitigation.",
        defend      = "Apply Microsoft security updates (KB5027441 and related patches). This payload IS the defense — apply it to unpatched systems.",
        config_needed = [],
        mitre       = ["T1203 - Exploitation for Client Execution", "T1566.001 - Spearphishing Attachment"]
    ),
    AleffPayload(
        name        = "Exploit Citrix NetScaler (CVE-2023-4966) - Windows",
        category    = "Incident_Response",
        platform    = "Windows",
        pap         = "red",
        path        = "Windows/Incident_Response/Exploit_Citrix_NetScaler_ADC_and_Gateway_through_CVE-2023-4966",
        description = "Checks for and exploits CVE-2023-4966 (Citrix Bleed) — unauthenticated session token theft from NetScaler ADC and Gateway.",
        teach       = "CVE-2023-4966 'Citrix Bleed' is a buffer overflow in Citrix NetScaler that allows unauthenticated attackers to extract session tokens from memory. These tokens grant full authenticated access to the VPN/gateway without credentials. Exploited by LockBit ransomware group in late 2023 against thousands of organizations.",
        defend      = "Apply Citrix security bulletin CTX579459 immediately. Invalidate all active sessions after patching (stolen tokens persist). Monitor for unauthenticated requests to /oauth/idp/.well-known/openid-configuration.",
        config_needed = ["Manual setup — target Citrix NetScaler URL"],
        mitre       = ["T1190 - Exploit Public-Facing Application", "T1550 - Use Alternate Authentication Material"]
    ),

    # ═══════════════════════════════════════════════════════
    # WINDOWS — PRANK
    # ═══════════════════════════════════════════════════════
    AleffPayload(
        name        = "Rick Roll (Never Gonna Give You Up)",
        category    = "Prank",
        platform    = "Windows",
        pap         = "green",
        path        = "Windows/Prank/NeverGonnaGiveYouUp_Windows",
        description = "Opens YouTube Rick Roll in the default browser. The classic. Plug-and-play.",
        teach       = "The first BadUSB payload most people write. Demonstrates the HID attack concept harmlessly. In security awareness training, receiving a Rick Roll from a 'USB found in the parking lot' makes the lesson memorable and non-threatening.",
        defend      = "This IS awareness training in payload form. Physical security briefings should mention USB drops. USB Device Control policies prevent HID enumeration.",
        config_needed = [],
        mitre       = ["T1200 - Hardware Additions"]
    ),
    AleffPayload(
        name        = "Alien Message From Computer",
        category    = "Prank",
        platform    = "Windows",
        pap         = "green",
        path        = "Windows/Prank/AlienMessageFromComputer",
        description = "Displays a full-screen alien message popup. Harmless prank payload. Plug-and-play.",
        teach       = "Full-screen popups via PowerShell WPF/WinForms are a social engineering tool — make the victim believe the machine is compromised, crashed, or infected to induce panic responses (like calling a fake tech support number). This harmless version is for demonstration only.",
        defend      = "User awareness: tech support will never appear as an automatic popup. Monitor for PowerShell spawning .NET UI windows from unexpected parent processes.",
        config_needed = [],
        mitre       = ["T1491 - Defacement"]
    ),
    AleffPayload(
        name        = "Change Wallpaper With Screenshot",
        category    = "Prank",
        platform    = "Windows",
        pap         = "yellow",
        path        = "Windows/Prank/ChangeWallpaperWithScreenshot",
        description = "Takes a screenshot of the current desktop, sets it as wallpaper, then hides the taskbar — making the desktop appear frozen.",
        teach       = "Classic prank that teaches the HID attack surface. The user sees what looks like a normal desktop but nothing is clickable because the taskbar is hidden. Also a technique for covering tracks after an attack — the desktop looks normal.",
        defend      = "Monitor registry changes to wallpaper settings (HKCU\\Control Panel\\Desktop\\Wallpaper). Physical security.",
        config_needed = ["Scripting tool path may need adjustment"],
        mitre       = ["T1491 - Defacement"]
    ),
    AleffPayload(
        name        = "Play Song Through Spotify",
        category    = "Prank",
        platform    = "Windows",
        pap         = "green",
        path        = "Windows/Prank/PlayASongThroughSpotify",
        description = "Opens and plays a specific song in Spotify. Plug-and-play.",
        teach       = "Harmless demonstration that applications can be controlled via keyboard automation. Used in physical security demos to show that an unlocked workstation can have arbitrary actions performed on it.",
        defend      = "Lock your workstation when leaving. Physical security.",
        config_needed = [],
        mitre       = ["T1200 - Hardware Additions"]
    ),
    AleffPayload(
        name        = "The Mouse Moves By Itself",
        category    = "Prank",
        platform    = "Windows",
        pap         = "yellow",
        path        = "Windows/Prank/The_Mouse_Moves_By_Itself",
        description = "Runs a PowerShell script that moves the mouse cursor continuously in random patterns.",
        teach       = "Random mouse movement is a persistence/disruption technique — it makes the machine appear to be remotely controlled, induces paranoia, prevents screensavers/locks, and can prevent automated processes from running if they require user inactivity detection.",
        defend      = "Monitor for PowerShell scripts using Windows SendInput or mouse movement APIs from unexpected processes.",
        config_needed = ["Script hosting location"],
        mitre       = ["T1059.001 - PowerShell"]
    ),
    AleffPayload(
        name        = "Follow Someone On Instagram",
        category    = "Prank",
        platform    = "Windows",
        pap         = "yellow",
        path        = "Windows/Prank/Follow_Someone_On_Instagram",
        description = "Automates following a specific Instagram account using the victim's logged-in browser session.",
        teach       = "Demonstrates browser session abuse via keyboard automation. The same technique that follows an Instagram account can be used to send phishing messages, post content, or exfiltrate DMs from any open web application session.",
        defend      = "Lock workstations. Web applications should implement bot detection (CAPTCHA) for sensitive actions.",
        config_needed = ["Instagram username to follow"],
        mitre       = ["T1185 - Browser Session Hijacking"]
    ),
    AleffPayload(
        name        = "Send Signal Messages",
        category    = "Prank",
        platform    = "Windows",
        pap         = "yellow",
        path        = "Windows/Prank/SendSignalMessages_Windows",
        description = "Sends a message through Signal Desktop using the victim's logged-in account.",
        teach       = "If Signal Desktop is open, physical access enables sending messages impersonating the victim. Even end-to-end encrypted messaging apps are vulnerable to physical session abuse. Recipients believe the message is legitimate — this is high-trust social engineering.",
        defend      = "Lock workstations. Signal Desktop session timeouts. Physical security.",
        config_needed = ["Target Signal contact and message"],
        mitre       = ["T1534 - Internal Spearphishing"]
    ),
    AleffPayload(
        name        = "Send Microsoft Teams Messages",
        category    = "Prank",
        platform    = "Windows",
        pap         = "yellow",
        path        = "Windows/Prank/SendMessagesInTeams",
        description = "Sends a message in Microsoft Teams using the victim's logged-in corporate account.",
        teach       = "Corporate Teams accounts have high trust — a message appearing to come from a colleague or manager is extremely effective social engineering. Physical access + Teams open = impersonation of the victim to their entire organization. This is a real business risk.",
        defend      = "Lock workstations. Teams session monitoring. Conditional Access policies requiring re-authentication for sensitive actions.",
        config_needed = ["Teams contact/channel and message"],
        mitre       = ["T1534 - Internal Spearphishing"]
    ),
    AleffPayload(
        name        = "Spam Terminals",
        category    = "Prank",
        platform    = "Windows",
        pap         = "green",
        path        = "Windows/Prank/Spam_Terminals-by_bst04",
        description = "Opens many terminal windows simultaneously. Disruptive/DoS prank. By bst04.",
        teach       = "Opening excessive terminal windows demonstrates DoS via physical access and tests process limit configurations. In a real engagement this could be used to crash the session or exhaust system resources.",
        defend      = "Process creation rate limiting. Physical security.",
        config_needed = [],
        mitre       = ["T1499 - Endpoint Denial of Service"]
    ),

    # ═══════════════════════════════════════════════════════
    # GNU-LINUX — EXFILTRATION
    # ═══════════════════════════════════════════════════════
    AleffPayload(
        name        = "Exfiltrate Process Info (Linux)",
        category    = "Exfiltration",
        platform    = "GNU-Linux",
        pap         = "yellow",
        path        = "GNU-Linux/Exfiltration/ExfiltrateProcessInfo_Linux",
        description = "Dumps running processes on Linux and exfiltrates via Discord webhook.",
        teach       = "Linux process listing (ps aux) reveals running services, daemons, security tools (auditd, ossec, fail2ban), and potentially processes with credentials in their command arguments. Exfiltrating this gives an attacker a complete picture of what defenses are active.",
        defend      = "Monitor Discord webhook outbound connections. Block unauthorized external connections at the firewall. auditd rules on ps execution can log who ran process enumeration.",
        config_needed = ["Discord Webhook URL"],
        mitre       = ["T1057 - Process Discovery", "T1048 - Exfiltration Over Alternative Protocol"]
    ),
    AleffPayload(
        name        = "Exfiltrate Network Traffic (Linux)",
        category    = "Exfiltration",
        platform    = "GNU-Linux",
        pap         = "yellow",
        path        = "GNU-Linux/Exfiltration/ExfiltrateNetworkTraffic_Linux",
        description = "Captures live network traffic briefly and exfiltrates the PCAP via Discord webhook.",
        teach       = "Physical access + tcpdump = passive network tap. Any unencrypted traffic is immediately readable. Even encrypted traffic reveals connection metadata (who's talking to whom). A 30-second capture on an active network segment can contain authentication handshakes, DNS queries revealing internal infrastructure, and unencrypted protocol data.",
        defend      = "Encrypt all internal traffic (TLS everywhere). Monitor tcpdump execution from non-root users (requires CAP_NET_RAW). auditd rule on tcpdump execution.",
        config_needed = ["Discord Webhook URL"],
        mitre       = ["T1040 - Network Sniffing", "T1048 - Exfiltration Over Alternative Protocol"]
    ),
    AleffPayload(
        name        = "Exfiltrate Linux Documents",
        category    = "Exfiltration",
        platform    = "GNU-Linux",
        pap         = "yellow",
        path        = "GNU-Linux/Exfiltration/ExfiltrateDocumentsFolder_Linux",
        description = "Archives and exfiltrates the user's Documents folder via Discord webhook.",
        teach       = "The Documents folder contains the most sensitive user-created files. A zip + Discord upload exfiltrates everything accessible to the current user in seconds. This demonstrates that data exfiltration via physical access needs no network shares, no USB drives, and leaves no removable media evidence.",
        defend      = "DLP (Data Loss Prevention) solutions that monitor file archiving and upload activity. Block Discord at perimeter. File access auditing with auditd.",
        config_needed = ["Discord Webhook URL"],
        mitre       = ["T1005 - Data from Local System", "T1048 - Exfiltration Over Alternative Protocol"]
    ),
    AleffPayload(
        name        = "Exfiltrate Linux Log Files",
        category    = "Exfiltration",
        platform    = "GNU-Linux",
        pap         = "yellow",
        path        = "GNU-Linux/Exfiltration/ExfiltrateLogFiles_Linux",
        description = "Exfiltrates system logs (/var/log/) via Discord webhook.",
        teach       = "System logs contain authentication events, sudo usage, cron jobs, and service activity. For attackers: logs reveal security tool configurations, user activity patterns, and evidence of previous intrusions. For defenders doing IR: these same logs are forensic evidence. Stealing logs before an attack erases that evidence.",
        defend      = "Centralized log management (SIEM) — send logs off-machine in real time so local log theft doesn't erase the trail. Monitor access to /var/log from non-root/non-syslog processes.",
        config_needed = ["Discord Webhook URL"],
        mitre       = ["T1005 - Data from Local System", "T1070.002 - Clear Linux or Mac System Logs"]
    ),
    AleffPayload(
        name        = "Exfiltrate Network Configuration (Linux)",
        category    = "Exfiltration",
        platform    = "GNU-Linux",
        pap         = "yellow",
        path        = "GNU-Linux/Exfiltration/ExfiltrateNetworkConfiguration_Linux",
        description = "Exfiltrates ip addr, routing table, and DNS config via Discord webhook.",
        teach       = "Network configuration reveals internal IP addressing, routing paths to other subnets, and DNS server locations. This is reconnaissance that maps the internal network without active scanning — critical for planning lateral movement and identifying pivot targets.",
        defend      = "Monitor ip/ifconfig/route commands from unexpected processes. Block webhook exfiltration at perimeter.",
        config_needed = ["Discord Webhook URL"],
        mitre       = ["T1016 - System Network Configuration Discovery", "T1048 - Exfiltration Over Alternative Protocol"]
    ),
    AleffPayload(
        name        = "Exfiltrate Email/Password by Phishing (Linux)",
        category    = "Exfiltration",
        platform    = "GNU-Linux",
        pap         = "yellow",
        path        = "GNU-Linux/Exfiltration/ExfiltrateEmailAndPasswordByPhising_Linux",
        description = "Displays a fake authentication dialog on Linux to phish the user's credentials.",
        teach       = "GUI phishing on Linux uses zenity or kdialog to display a native-looking password prompt. The user assumes it's a legitimate system dialog and enters their credentials. This captures passwords without any network intrusion — purely via physical access and social engineering the OS UI.",
        defend      = "User awareness: legitimate system prompts appear on the lock screen, not while you're logged in. Monitor zenity/kdialog invocations from unexpected parent processes.",
        config_needed = ["Exfiltration endpoint configured"],
        mitre       = ["T1056.002 - Input Capture: GUI Input Capture", "T1566 - Phishing"]
    ),
    AleffPayload(
        name        = "Exfiltrate Sudo Password by Phishing (Linux)",
        category    = "Exfiltration",
        platform    = "GNU-Linux",
        pap         = "yellow",
        path        = "GNU-Linux/Exfiltration/ExfiltrateSudoPasswordByPhising_Linux",
        description = "Displays a fake sudo authentication dialog to capture the user's sudo password.",
        teach       = "The sudo password IS the user's login password on most Linux systems. Capturing it via a fake GUI prompt gives the attacker the ability to escalate to root on any system this user has sudo access to. Once you have the sudo password, the machine is fully compromised.",
        defend      = "Use polkit with separate admin accounts rather than sudo with the user's own password. Monitor unusual sudo-related processes. Physical security.",
        config_needed = ["Exfiltration endpoint configured"],
        mitre       = ["T1056.002 - GUI Input Capture", "T1548.003 - Sudo and Sudo Caching"]
    ),
    AleffPayload(
        name        = "Exfiltrate WiFi Passwords (Linux)",
        category    = "Exfiltration",
        platform    = "GNU-Linux",
        pap         = "yellow",
        path        = "GNU-Linux/Exfiltration/ExfiltrateWiFiPasswords_Linux",
        description = "Extracts all saved WiFi passwords from NetworkManager and exfiltrates via Discord webhook.",
        teach       = "NetworkManager stores WiFi credentials in /etc/NetworkManager/system-connections/ with 600 permissions — readable by root. If the user has sudo access, their WiFi passwords for every network they've connected to are readable. Corporate WiFi credentials enable network access from outside the building.",
        defend      = "Use separate service accounts with minimal privileges. Monitor access to /etc/NetworkManager/system-connections/. Block outbound webhook connections.",
        config_needed = ["Discord Webhook URL"],
        mitre       = ["T1081 - Credentials in Files", "T1048 - Exfiltration Over Alternative Protocol"]
    ),
    AleffPayload(
        name        = "Exfiltrate Photos Through Shell (Linux)",
        category    = "Exfiltration",
        platform    = "GNU-Linux",
        pap         = "yellow",
        path        = "GNU-Linux/Exfiltration/ExfiltratePhotosThroughShell",
        description = "Archives and exfiltrates the user's Pictures directory via Discord webhook.",
        teach       = "Photo exfiltration captures visual evidence of physical environments (office layouts, whiteboards with diagrams, ID badges), personal identification documents, and screenshots. In corporate espionage this can reveal product roadmaps photographed from presentations.",
        defend      = "DLP policies monitoring file archiving and upload. Block Discord webhook at perimeter. Physical security.",
        config_needed = ["Discord Webhook URL"],
        mitre       = ["T1005 - Data from Local System", "T1048 - Exfiltration Over Alternative Protocol"]
    ),

    # ═══════════════════════════════════════════════════════
    # GNU-LINUX — EXECUTION
    # ═══════════════════════════════════════════════════════
    AleffPayload(
        name        = "Persistent Reverse Shell - Telegram",
        category    = "Execution",
        platform    = "GNU-Linux",
        pap         = "yellow",
        path        = "GNU-Linux/Execution/Persistent_Reverse_Shell-Telegram_Based",
        description = "Installs a persistent reverse shell that uses Telegram as the C2 channel. Survives reboots.",
        teach       = "Telegram-based C2 is increasingly common because Telegram traffic blends with legitimate chat traffic and is rarely blocked. The bot receives commands via Telegram messages and sends output back — encrypted, through Telegram's infrastructure. Physical access for 10 seconds = persistent remote access that survives reboots.",
        defend      = "Monitor for new cron jobs and systemd units created by non-root users. Block Telegram API (api.telegram.org) at the perimeter for corporate environments. Endpoint monitoring for outbound connections to Telegram from non-user-initiated processes.",
        config_needed = ["Telegram Bot Token", "Chat ID"],
        mitre       = ["T1059.004 - Unix Shell", "T1071.001 - Application Layer Protocol", "T1547 - Boot or Logon Autostart"]
    ),
    AleffPayload(
        name        = "Telegram Persistent Connection",
        category    = "Execution",
        platform    = "GNU-Linux",
        pap         = "yellow",
        path        = "GNU-Linux/Execution/Telegram_Persistent_Connection_Linux",
        description = "Establishes a persistent connection channel via Telegram bot for command execution.",
        teach       = "A persistent Telegram connection acts as an always-on remote access channel. Unlike traditional reverse shells that need a listening server, this pulls commands from Telegram — NAT and firewall traversal is built in because it uses outbound HTTPS. Extremely stealthy in environments that allow web browsing.",
        defend      = "Same as Telegram reverse shell. Block api.telegram.org for non-user processes. Monitor persistent connection patterns (regular beacon intervals) in network logs.",
        config_needed = ["Telegram Bot Token", "Chat ID"],
        mitre       = ["T1071.001 - Web Protocols", "T1573 - Encrypted Channel", "T1547 - Boot or Logon Autostart"]
    ),
    AleffPayload(
        name        = "Persistent Keylogger - Telegram",
        category    = "Execution",
        platform    = "GNU-Linux",
        pap         = "yellow",
        path        = "GNU-Linux/Execution/Persistent_Keylogger-Telegram_Based",
        description = "Installs a persistent kernel-level keylogger that exfiltrates keystrokes via Telegram.",
        teach       = "A keylogger captures everything typed: passwords, encryption keys, sensitive documents, messages. Linux keyloggers at the user level use /dev/input devices or Python libraries like pynput. Combined with Telegram C2, every keystroke is sent to the attacker in real time — including passwords to systems not on this machine.",
        defend      = "Monitor for processes reading /dev/input/ from unexpected applications. EDR solutions detect keylogger behaviors. Physical security is the primary control for BadUSB-delivered keyloggers.",
        config_needed = ["Telegram Bot Token", "Chat ID"],
        mitre       = ["T1056.001 - Keylogging", "T1071.001 - Web Protocols", "T1547 - Boot or Logon Autostart"]
    ),
    AleffPayload(
        name        = "Change MAC Address (Linux)",
        category    = "Execution",
        platform    = "GNU-Linux",
        pap         = "yellow",
        path        = "GNU-Linux/Execution/ChangeMacAddress_Linux",
        description = "Changes the network interface MAC address to bypass MAC-based access controls.",
        teach       = "MAC address filtering (often used on WiFi and 802.1X networks) can be bypassed by spoofing a known-good MAC address. Physical access to a machine on the network allows reading its MAC, then using a different device with that MAC to gain network access. MAC filtering is not a security control against determined attackers.",
        defend      = "Use 802.1X with certificate-based authentication rather than MAC filtering. MAC filtering alone is trivially bypassed. Network access control (NAC) solutions detect MAC spoofing.",
        config_needed = ["Target MAC address to spoof"],
        mitre       = ["T1036 - Masquerading", "T1016 - System Network Configuration Discovery"]
    ),
    AleffPayload(
        name        = "Set Arbitrary VPN (Linux)",
        category    = "Execution",
        platform    = "GNU-Linux",
        pap         = "yellow",
        path        = "GNU-Linux/Execution/SetArbitraryVPN_Linux",
        description = "Configures and connects to a specified VPN server on Linux.",
        teach       = "Routing a target machine's traffic through an attacker-controlled VPN gives full visibility into all network traffic from that machine. Combined with DNS control, this enables a complete man-in-the-middle position without any network-level attack — the victim connected their own machine to the attacker's infrastructure.",
        defend      = "Corporate endpoint management should prevent unauthorized VPN client installation. Monitor for new VPN connections via NetworkManager. Egress filtering prevents connecting to unauthorized VPN endpoints.",
        config_needed = ["VPN server details"],
        mitre       = ["T1572 - Protocol Tunneling", "T1557 - Adversary-in-the-Middle"]
    ),
    AleffPayload(
        name        = "Exploiting An Executable File (Linux)",
        category    = "Execution",
        platform    = "GNU-Linux",
        pap         = "green",
        path        = "GNU-Linux/Execution/ExploitingAnExecutableFile",
        description = "Runs a pre-staged executable on the target Linux system. Plug-and-play template.",
        teach       = "Template payload for executing arbitrary code via BadUSB. Open terminal, navigate to staged payload, execute. Demonstrates that code execution via physical access requires no exploitation — the OS is already running and trusting the logged-in user.",
        defend      = "Application whitelisting (SELinux/AppArmor policies). Monitor executions of binaries from user home directories. Physical security.",
        config_needed = [],
        mitre       = ["T1204 - User Execution", "T1059.004 - Unix Shell"]
    ),
    AleffPayload(
        name        = "Change Network Configuration (Linux)",
        category    = "Execution",
        platform    = "GNU-Linux",
        pap         = "yellow",
        path        = "GNU-Linux/Execution/ChangeNetworkConfiguration_Linux",
        description = "Modifies Linux network interface configuration — IP, gateway, DNS.",
        teach       = "Changing network configuration (IP, gateway, DNS) redirects all traffic through an attacker-controlled path. Set DNS to an attacker server and every domain lookup is logged and potentially hijacked. Change the gateway and all traffic routes through the attacker. Physical access makes this trivial.",
        defend      = "Network configuration management via DHCP with enforcement. Monitor NetworkManager configuration file changes. Immutable /etc/resolv.conf with chattr +i.",
        config_needed = ["New network settings"],
        mitre       = ["T1565.001 - Stored Data Manipulation", "T1557 - Adversary-in-the-Middle"]
    ),
    AleffPayload(
        name        = "Edit Default App With Arbitrary",
        category    = "Execution",
        platform    = "GNU-Linux",
        pap         = "yellow",
        path        = "GNU-Linux/Execution/Edit_The_Default_Real_App_With_An_Arbitrary",
        description = "Replaces a default application handler with an arbitrary executable for persistence.",
        teach       = "Replacing default application handlers (xdg-mime, .desktop file associations) is a persistence technique — when the user opens a PDF, they actually run your malware. This works without root because user-level .desktop files in ~/.local/share/applications/ override system defaults.",
        defend      = "Monitor .desktop file modifications in user home directories. Audit xdg-mime changes. EDR baseline comparison detects handler modifications.",
        config_needed = ["Application to replace and payload path"],
        mitre       = ["T1546 - Event Triggered Execution", "T1036 - Masquerading"]
    ),
    AleffPayload(
        name        = "Set Arbitrary Tor Circuit (Linux)",
        category    = "Execution",
        platform    = "GNU-Linux",
        pap         = "yellow",
        path        = "GNU-Linux/Execution/Set_An_Arbitrary_And_Persistent_Tor_Circuit",
        description = "Configures Tor on Linux to use specific entry/middle/exit nodes persistently.",
        teach       = "Same technique as Windows version — controlling Tor circuit nodes ensures traffic routes through trusted/known relays. On Linux, modifies /etc/tor/torrc (requires sudo) or user-level config. The 'Persistent' aspect means the configuration survives reboots.",
        defend      = "Monitor torrc file modifications. Block Tor at the perimeter. Detect Tor usage via traffic fingerprinting.",
        config_needed = ["Node fingerprints from metrics.torproject.org", "sudo password or root access"],
        mitre       = ["T1090.003 - Multi-hop Proxy", "T1572 - Protocol Tunneling"]
    ),
    AleffPayload(
        name        = "Defend Against AtlasVPN Bugdoor (Linux)",
        category    = "Execution",
        platform    = "GNU-Linux",
        pap         = "yellow",
        path        = "GNU-Linux/Execution/Defend_yourself_against_AtlasVPN_bugdoor",
        description = "Applies defensive fix for the AtlasVPN local privilege escalation vulnerability on Linux.",
        teach       = "AtlasVPN for Linux had a local socket API that any process could communicate with, allowing any local user to disconnect the VPN without authentication. This could be exploited to de-anonymize users or expose traffic. This payload applies the fix.",
        defend      = "Update AtlasVPN to the patched version. This payload IS the defense for unpatched systems.",
        config_needed = ["May require sudo depending on system"],
        mitre       = ["T1548 - Abuse Elevation Control Mechanism"]
    ),
    AleffPayload(
        name        = "Change Git Remote Link (Linux)",
        category    = "Execution",
        platform    = "GNU-Linux",
        pap         = "yellow",
        path        = "GNU-Linux/Execution/ChangeGitRemoteLink",
        description = "Changes a Git repository remote URL to an attacker-controlled server on Linux.",
        teach       = "Same supply chain attack as the Windows version — redirect future git pushes to an attacker server. On Linux developer workstations this is especially high-value since Linux devs often work on infrastructure code (Ansible, Terraform, Kubernetes configs) that gets pushed directly to production.",
        defend      = "Git remote URL monitoring. GPG commit signing. Pre-push hooks verifying remote URLs against an allowlist.",
        config_needed = ["Attacker-controlled Git remote URL"],
        mitre       = ["T1195 - Supply Chain Compromise", "T1565 - Data Manipulation"]
    ),

    # ═══════════════════════════════════════════════════════
    # GNU-LINUX — PHISHING
    # ═══════════════════════════════════════════════════════
    AleffPayload(
        name        = "Standard Phishing Attack (Linux)",
        category    = "Phishing",
        platform    = "GNU-Linux",
        pap         = "yellow",
        path        = "GNU-Linux/Phising/StandardPhishingAttack_Linux",
        description = "Opens a browser phishing page and displays a credential prompt on Linux.",
        teach       = "Combines browser-based phishing with a GUI credential prompt for a convincing attack. The user sees what appears to be a legitimate login page requesting re-authentication. Captures credentials and exfiltrates them. Demonstrates that phishing doesn't require email — physical access enables direct browser-based social engineering.",
        defend      = "Password managers refuse to autofill on lookalike domains (critical defense). FIDO2 hardware keys are domain-bound. User awareness training.",
        config_needed = ["Phishing page URL", "Exfiltration endpoint"],
        mitre       = ["T1566 - Phishing", "T1056.002 - GUI Input Capture"]
    ),
    AleffPayload(
        name        = "Standard Phishing via KDialog (Linux KDE)",
        category    = "Phishing",
        platform    = "GNU-Linux",
        pap         = "yellow",
        path        = "GNU-Linux/Phising/StandardPhishingPayloadUsingKdialog_Linux",
        description = "Uses kdialog (KDE) to display a native-looking credential prompt on KDE desktops.",
        teach       = "KDE's kdialog creates native-looking GUI dialogs from the command line. On a KDE desktop, a kdialog credential prompt is visually indistinguishable from a legitimate system authentication request. More convincing than a browser popup because it uses native OS UI components.",
        defend      = "Monitor kdialog execution from non-system processes. User awareness: legitimate re-auth prompts come from PolicyKit, not random applications.",
        config_needed = ["Exfiltration endpoint"],
        mitre       = ["T1056.002 - GUI Input Capture", "T1566 - Phishing"]
    ),

    # ═══════════════════════════════════════════════════════
    # GNU-LINUX — INCIDENT RESPONSE
    # ═══════════════════════════════════════════════════════
    AleffPayload(
        name        = "Linux Forensic Triage Collector",
        category    = "Incident_Response",
        platform    = "GNU-Linux",
        pap         = "yellow",
        path        = "GNU-Linux/Incident_Response/Linux_Forensic_Triage_Collector",
        description = "Automated forensic triage collection: processes, network, logs, persistence locations. By bad-antics.",
        teach       = "First response to a compromised Linux system. Collects: running processes (ps aux), network connections (netstat/ss), listening ports, logged-in users (who/w/last), cron jobs, systemd timers, /tmp contents, recently modified files, and SUID binaries. Everything an IR analyst needs for initial triage in one automated script.",
        defend      = "This payload IS the defense tool — use it on systems you own to collect evidence during incident response. Run with appropriate permissions and preserve chain of custody.",
        config_needed = ["Output destination for triage data"],
        mitre       = ["T1057 - Process Discovery", "T1049 - System Network Connections Discovery", "T1083 - File and Directory Discovery"]
    ),
    AleffPayload(
        name        = "Linux IOC Scanner",
        category    = "Incident_Response",
        platform    = "GNU-Linux",
        pap         = "yellow",
        path        = "GNU-Linux/Incident_Response/Linux_IOC_Scanner",
        description = "Scans for Indicators of Compromise on a Linux system. By bad-antics.",
        teach       = "IOC scanning checks for known malware artifacts: suspicious process names, known C2 domains in network connections, modified system binaries (checksum comparison), suspicious cron jobs, unauthorized SSH keys, and known rootkit indicators. Rapid deployment via Flipper means you can scan any accessible Linux machine during physical security assessments.",
        defend      = "Run this during incident response to identify compromised indicators. Deploy regularly as a health check. AIDE (Advanced Intrusion Detection Environment) does this continuously.",
        config_needed = ["IOC list to scan against"],
        mitre       = ["T1518 - Software Discovery", "T1083 - File and Directory Discovery"]
    ),
    AleffPayload(
        name        = "Linux Persistence Hunter",
        category    = "Incident_Response",
        platform    = "GNU-Linux",
        pap         = "yellow",
        path        = "GNU-Linux/Incident_Response/Linux_Persistence_Hunter",
        description = "Hunts for all persistence mechanisms on a Linux system. By bad-antics.",
        teach       = "Enumerates every persistence location an attacker might use: cron jobs (user and system), systemd units, ~/.bashrc/.profile modifications, /etc/rc.local, /etc/init.d/, SUID/SGID binaries, authorized_keys files, LD_PRELOAD hijacks, and PAM module modifications. If anything unexpected is found, it was put there by someone.",
        defend      = "Run this during IR to find attacker persistence. Schedule it as a regular audit. Compare output against a known-good baseline.",
        config_needed = ["Output destination"],
        mitre       = ["T1547 - Boot or Logon Autostart", "T1053 - Scheduled Task/Job", "T1543 - Create or Modify System Process"]
    ),
    AleffPayload(
        name        = "Check Cisco IOS XE Backdoor (CVE-2023-20198)",
        category    = "Incident_Response",
        platform    = "GNU-Linux",
        pap         = "red",
        path        = "GNU-Linux/Incident_Response/Auto-Check_Cisco_IOS_XE_Backdoor_based_on_CVE-2023-20198_and_CVE",
        description = "Checks for CVE-2023-20198 and CVE-2023-20273 Cisco IOS XE backdoor implant.",
        teach       = "CVE-2023-20198 was a critical 0-day in Cisco IOS XE that allowed unauthenticated remote code execution via the web UI. Thousands of devices were backdoored with implants before the patch was released. This payload automates checking whether a Cisco IOS XE device is compromised by querying known backdoor indicators.",
        defend      = "Apply Cisco security advisory cisco-sa-iosxe-webui-privesc-j22SaA4Z patches immediately. Disable web UI access if not needed. Monitor for unauthorized accounts in show user detail output.",
        config_needed = ["Manual setup — target Cisco device IP required"],
        mitre       = ["T1190 - Exploit Public-Facing Application", "T1505.003 - Web Shell"]
    ),
    AleffPayload(
        name        = "Exploit Citrix NetScaler (CVE-2023-4966) - Linux",
        category    = "Incident_Response",
        platform    = "GNU-Linux",
        pap         = "red",
        path        = "GNU-Linux/Incident_Response/Exploit_Citrix_NetScaler_ADC_and_Gateway_through_CVE-2023-4966",
        description = "Linux version of the Citrix Bleed CVE-2023-4966 session token extraction exploit.",
        teach       = "Same vulnerability as the Windows version — Citrix Bleed allows unauthenticated session token extraction from NetScaler memory. The Linux version runs from a compromised Linux host on the same network as the NetScaler appliance, making it a post-exploitation lateral movement tool.",
        defend      = "Same as Windows version: apply CTX579459, invalidate all sessions, monitor for exploitation indicators.",
        config_needed = ["Manual setup — target NetScaler URL required"],
        mitre       = ["T1190 - Exploit Public-Facing Application", "T1550 - Use Alternate Authentication Material"]
    ),

    # ═══════════════════════════════════════════════════════
    # GNU-LINUX — PRANK
    # ═══════════════════════════════════════════════════════
    AleffPayload(
        name        = "Change Desktop Wallpaper (KDE Linux)",
        category    = "Prank",
        platform    = "GNU-Linux",
        pap         = "yellow",
        path        = "GNU-Linux/Prank/ChangeDesktopWallpaper_LinuxKDE",
        description = "Changes the KDE desktop wallpaper to a specified image.",
        teach       = "KDE wallpaper changes via qdbus demonstrate that desktop environments are scriptable via D-Bus. The same D-Bus interface can control application behavior, send notifications, and interact with system services — wallpaper changing is the harmless demonstration.",
        defend      = "Physical security. D-Bus monitoring for unexpected inter-process communication.",
        config_needed = ["Image URL or path for new wallpaper"],
        mitre       = ["T1491 - Defacement"]
    ),
    AleffPayload(
        name        = "Send Telegram Messages (Linux)",
        category    = "Prank",
        platform    = "GNU-Linux",
        pap         = "yellow",
        path        = "GNU-Linux/Prank/SendTelegramMessages_Linux",
        description = "Sends a Telegram message using the victim's logged-in Telegram Desktop session.",
        teach       = "If Telegram Desktop is open on Linux, physical access enables sending messages impersonating the victim — to individuals or groups. Same high-trust impersonation risk as Teams/Signal. The victim's contacts believe the message is legitimate.",
        defend      = "Lock workstations when stepping away. Telegram session timeouts.",
        config_needed = ["Target Telegram contact and message"],
        mitre       = ["T1534 - Internal Spearphishing"]
    ),
    AleffPayload(
        name        = "Change The App That Will Be Run",
        category    = "Prank",
        platform    = "GNU-Linux",
        pap         = "yellow",
        path        = "GNU-Linux/Prank/Change_The_App_That_Will_Be_Runned",
        description = "Modifies a .desktop launcher to run a different application when clicked.",
        teach       = "Modifying .desktop files in ~/.local/share/applications/ replaces what runs when a user clicks an app icon. The user thinks they're opening their text editor but they're running your payload. Persistence via application hijacking requires no root and looks completely normal.",
        defend      = "Monitor .desktop file modifications. Compare desktop file hashes against a baseline. EDR behavioral detection.",
        config_needed = ["Target .desktop file and replacement command"],
        mitre       = ["T1546 - Event Triggered Execution", "T1036 - Masquerading"]
    ),
    AleffPayload(
        name        = "This Damn Shell Doesn't Work (Kali)",
        category    = "Prank",
        platform    = "GNU-Linux",
        pap         = "green",
        path        = "GNU-Linux/Prank/This_damn_shell_doesn_t_work___so_sad!-KALI",
        description = "Makes terminal commands appear to fail with humorous error messages on Kali Linux.",
        teach       = "Modifying shell configuration (bash aliases) can make any command produce fake output — a technique used to hide malware (alias ls='ls && malware') or confuse incident responders (alias ps='echo no processes'). This harmless version is for demonstration.",
        defend      = "Monitor ~/.bashrc and ~/.bash_aliases modifications. Shell configuration management via configuration management tools.",
        config_needed = [],
        mitre       = ["T1036 - Masquerading"]
    ),
    AleffPayload(
        name        = "This Damn Shell Doesn't Work (Linux)",
        category    = "Prank",
        platform    = "GNU-Linux",
        pap         = "green",
        path        = "GNU-Linux/Prank/This_damn_shell_doesn_t_work___so_sad!-LINUX",
        description = "Generic Linux version of the shell confusion prank. Plug-and-play.",
        teach       = "Same technique as the Kali version, adapted for generic Linux distributions. Demonstrates shell alias hijacking which is a real attacker persistence technique.",
        defend      = "Same as Kali version — monitor shell config file modifications.",
        config_needed = [],
        mitre       = ["T1036 - Masquerading"]
    ),
    AleffPayload(
        name        = "Send Email Through Thunderbird (Linux)",
        category    = "Prank",
        platform    = "GNU-Linux",
        pap         = "green",
        path        = "GNU-Linux/Prank/SendEmailThroughThunderbird",
        description = "Sends an email using the victim's open Thunderbird session on Linux.",
        teach       = "Open Thunderbird = access to the victim's email identity. Physical access enables sending emails appearing to come from the victim — to anyone in their contacts. Business email compromise (BEC) without compromising email credentials.",
        defend      = "Lock workstations. Thunderbird session timeouts. Physical security.",
        config_needed = [],
        mitre       = ["T1534 - Internal Spearphishing"]
    ),

    # ═══════════════════════════════════════════════════════
    # iOS — PRANK / EXECUTION
    # ═══════════════════════════════════════════════════════
    AleffPayload(
        name        = "Text Someone With iPhone",
        category    = "Execution",
        platform    = "iOS",
        pap         = "yellow",
        path        = "iOS/Execution/Text_Someone_Message_With_iPhone-by_bst04",
        description = "Sends an iMessage/SMS from an unlocked iPhone to a specified contact. By bst04.",
        teach       = "An unlocked iPhone connected via USB as a BadUSB host enables keyboard injection into iOS via Lightning/USB-C. This payload opens Messages and sends a text from the victim's phone number. Critical for demonstrating physical iPhone security — unlock screens matter.",
        defend      = "iPhone screen lock (Face ID/Touch ID) prevents this payload entirely. Never leave iPhone unlocked and unattended. USB Restricted Mode (Settings > Face ID > USB Accessories) blocks data connection after 1 hour.",
        config_needed = ["Recipient phone number or contact name", "Message text"],
        mitre       = ["T1534 - Internal Spearphishing"]
    ),
    AleffPayload(
        name        = "Play A Song With iPhone",
        category    = "Prank",
        platform    = "iOS",
        pap         = "yellow",
        path        = "iOS/Prank/Play_A_Song_With_An_iPhone",
        description = "Opens Music app on iPhone and plays a specified song.",
        teach       = "Demonstrates iOS keyboard injection capability. If you can type into the phone, you can control any app that accepts keyboard input. Apple Music search and play = full media control via HID.",
        defend      = "iPhone screen lock. USB Restricted Mode. Physical security.",
        config_needed = ["Song name to search and play"],
        mitre       = ["T1200 - Hardware Additions"]
    ),
    AleffPayload(
        name        = "Call Someone With iPhone",
        category    = "Prank",
        platform    = "iOS",
        pap         = "yellow",
        path        = "iOS/Prank/Call_Someone_With_An_iPhone",
        description = "Initiates a phone call from an unlocked iPhone to a specified number.",
        teach       = "Initiating calls from a victim's phone number enables caller-ID spoofing attacks — the recipient sees the victim's number, not the attacker's. Combined with social engineering, this is a high-trust vishing (voice phishing) setup using physical access.",
        defend      = "iPhone screen lock. USB Restricted Mode. Physical security.",
        config_needed = ["Phone number to call"],
        mitre       = ["T1534 - Internal Spearphishing", "T1566 - Phishing"]
    ),
    AleffPayload(
        name        = "Edit A Reminder With iPhone",
        category    = "Prank",
        platform    = "iOS",
        pap         = "yellow",
        path        = "iOS/Prank/Edit_A_Reminder_With_An_iPhone",
        description = "Edits an existing reminder on an unlocked iPhone.",
        teach       = "Demonstrates that all iOS app content is accessible via keyboard injection on an unlocked device. Reminders, calendar events, contacts — all modifiable. In a targeted attack, modifying an executive's calendar appointment could redirect a meeting or cause a missed commitment.",
        defend      = "iPhone screen lock. USB Restricted Mode.",
        config_needed = ["Reminder name to edit", "New content"],
        mitre       = ["T1565 - Data Manipulation"]
    ),
    AleffPayload(
        name        = "Delete A Reminder With iPhone",
        category    = "Prank",
        platform    = "iOS",
        pap         = "yellow",
        path        = "iOS/Prank/Delete_A_Reminder_With_An_iPhone",
        description = "Deletes a specific reminder on an unlocked iPhone.",
        teach       = "Deleting calendar items, reminders, or contacts is a subtle sabotage technique that may not be immediately noticed. The victim misses an important meeting or appointment without knowing why. Demonstrates destructive capability via physical access.",
        defend      = "iPhone screen lock. USB Restricted Mode. iCloud sync means deletions propagate to all devices — but iCloud also allows recovery within 30 days.",
        config_needed = ["Reminder name to delete"],
        mitre       = ["T1485 - Data Destruction"]
    ),

    # ═══════════════════════════════════════════════════════
    # macOS — EXECUTION
    # ═══════════════════════════════════════════════════════
    AleffPayload(
        name        = "IP Logger via Discord Webhook (macOS)",
        category    = "Execution",
        platform    = "macOS",
        pap         = "yellow",
        path        = "MacOS/Execution/IPLogger-Discord_Webhook-by_bst04",
        description = "Logs the macOS machine's public IP address and system info via Discord webhook. By bst04.",
        teach       = "Quickly capturing the public IP of a target machine confirms network location — useful for identifying whether a laptop is in the office, at home, or on a corporate VPN. The system info (hostname, username, OS version) combined with IP logging is basic asset fingerprinting.",
        defend      = "Block Discord webhook connections at perimeter. Monitor curl/wget to external IPs from Terminal. USB Restricted Mode equivalent on macOS: System Settings > Privacy > USB accessories.",
        config_needed = ["Discord Webhook URL"],
        mitre       = ["T1016 - System Network Configuration Discovery", "T1048 - Exfiltration Over Alternative Protocol"]
    ),
    AleffPayload(
        name        = "Set Volume Max (macOS)",
        category    = "Execution",
        platform    = "macOS",
        pap         = "green",
        path        = "MacOS/Execution/SetVolumeMax-MacOS",
        description = "Sets macOS system volume to maximum. Plug-and-play. By bst04.",
        teach       = "Harmless demonstration of macOS AppleScript/osascript keyboard control. The same 'osascript' interface that sets volume can control any application, read files, display dialogs, and execute shell commands — it's a full scripting attack surface on macOS.",
        defend      = "Physical security. Monitor osascript execution from Terminal from unexpected parent processes.",
        config_needed = [],
        mitre       = ["T1059.002 - AppleScript"]
    ),

    # ═══════════════════════════════════════════════════════
    # WINDOWS — CREDENTIALS (additional)
    # ═══════════════════════════════════════════════════════
    AleffPayload(
        name        = "Defend Yourself From CVE-2023-23397",
        category    = "Incident_Response",
        platform    = "Windows",
        pap         = "green",
        path        = "Windows/Credentials/Defend_yourself_from_CVE-2023-23397",
        description = "Automated defense against CVE-2023-23397 — a critical zero-click Microsoft Outlook NTLM hash theft vulnerability.",
        teach       = "CVE-2023-23397 lets an attacker steal your Windows NTLM hash simply by sending you a calendar invite with a UNC path reminder. No click required — Outlook processes it automatically. This payload applies the registry fix that blocks Outlook from automatically resolving UNC paths, neutralizing the attack vector.",
        defend      = "Apply the official Microsoft patch. Set registry HKCU\\Software\\Microsoft\\Office\\16.0\\Outlook\\Options\\Mail DisableUNCPaths=1. Monitor outbound SMB (port 445) from Outlook.exe — any such connection is a sign of active exploitation.",
        config_needed = [],
        mitre       = ["T1187 - Forced Authentication", "T1557 - Adversary-in-the-Middle"]
    ),

    # ═══════════════════════════════════════════════════════
    # WINDOWS — EXFILTRATION (additional)
    # ═══════════════════════════════════════════════════════
    AleffPayload(
        name        = "Exports all the links of the downloads",
        category    = "Exfiltration",
        platform    = "Windows",
        pap         = "yellow",
        path        = "Windows/Exfiltration/Exports_all_the_links_of_the_downloads",
        description = "Extracts all download source URLs from the Windows Downloads folder metadata and exfiltrates via Discord webhook.",
        teach       = "Windows stores the original download URL in NTFS Alternate Data Streams (Zone.Identifier). This payload reads those streams to reconstruct exactly where every file was downloaded from — browser history without touching the browser. Useful for understanding what software a target has obtained and from where.",
        defend      = "Monitor for PowerShell reading Zone.Identifier ADS streams at scale. The Get-Item -Stream command accessing multiple files rapidly is a detection signal. User education: be suspicious of USB devices plugged into workstations.",
        config_needed = ["Discord webhook URL"],
        mitre       = ["T1005 - Data from Local System", "T1048 - Exfiltration Over Alternative Protocol"]
    ),
    AleffPayload(
        name        = "Tree structure of the operating system",
        category    = "Exfiltration",
        platform    = "Windows",
        pap         = "yellow",
        path        = "Windows/Exfiltration/Tree_structure_of_the_operating_system",
        description = "Maps the complete filesystem directory tree and exfiltrates the structure via Discord webhook.",
        teach       = "A directory tree dump reveals installed software, user profiles, custom application directories, and project names without touching any file contents. This gives an attacker a reconnaissance map of the entire machine in seconds — what's installed, where data lives, and what to target for follow-up exfiltration.",
        defend      = "Monitor for 'tree /f /a' command execution from non-administrative processes. Outbound webhook calls (HTTPS POST to discord.com) from cmd.exe or powershell.exe are suspicious.",
        config_needed = ["Discord webhook URL"],
        mitre       = ["T1083 - File and Directory Discovery", "T1048 - Exfiltration Over Alternative Protocol"]
    ),
    AleffPayload(
        name        = "Export all saved certificates with Adobe Reader",
        category    = "Exfiltration",
        platform    = "Windows",
        pap         = "yellow",
        path        = "Windows/Exfiltration/Export_all_saved_certificates_with_Adobe_Reader",
        description = "Extracts all digital certificates stored in Adobe Reader's trusted certificate store and exfiltrates them.",
        teach       = "Adobe Reader maintains its own certificate trust store separate from the Windows certificate store. Organizations using digital signatures for contracts and documents store their signing certificates here. Extracting them reveals trusted certificate authorities and potentially signing keys used for document authentication.",
        defend      = "Restrict Adobe Reader certificate store access via GPO. Monitor for Adobe Reader launching alongside PowerShell. Keep Adobe Reader updated — certificate stores are also attack targets for trust injection.",
        config_needed = ["Exfiltration endpoint"],
        mitre       = ["T1552.004 - Private Keys", "T1005 - Data from Local System"]
    ),
    AleffPayload(
        name        = "Exfiltrates the entire database of the Notion client",
        category    = "Exfiltration",
        platform    = "Windows",
        pap         = "yellow",
        path        = "Windows/Exfiltration/Exfiltrates_the_entire_database_of_the_Notion_client",
        description = "Exfiltrates the local SQLite database of the Notion desktop client containing cached workspace content.",
        teach       = "Notion's desktop client caches all workspace content locally in a SQLite database. This includes notes, project plans, meeting minutes, passwords stored in Notion, and any sensitive documents the user has accessed recently. This payload copies and exfiltrates that entire cache — everything the user has in Notion without touching the Notion API or leaving API logs.",
        defend      = "Disable Notion desktop client local caching via workspace settings where possible. Monitor for access to %APPDATA%\\Notion\\notion.db. Enforce DLP policies on desktop applications that cache sensitive content locally.",
        config_needed = ["Discord webhook URL or Dropbox token"],
        mitre       = ["T1005 - Data from Local System", "T1552 - Unsecured Credentials"]
    ),
    AleffPayload(
        name        = "Save Your Thunderbird Settings",
        category    = "Exfiltration",
        platform    = "Windows",
        pap         = "yellow",
        path        = "Windows/Exfiltration/Save_Your_Thunderbird_Settings",
        description = "Compresses and exfiltrates the entire Mozilla Thunderbird profile including emails, contacts, and account configuration.",
        teach       = "Thunderbird stores its entire profile — email accounts, saved passwords, message history, calendar data, contacts — in a single profile directory. Exfiltrating this gives access to: all email account credentials (stored in key4.db / logins.json), full email history, contact list, and any saved attachments. This is equivalent to full email account compromise without ever touching the mail server.",
        defend      = "Thunderbird should use a master password (enforced via enterprise policy) which encrypts stored credentials. Monitor for compression of %APPDATA%\\Thunderbird\\Profiles. Enterprise mail clients should use hardware tokens for authentication rather than stored passwords.",
        config_needed = ["Dropbox access token"],
        mitre       = ["T1552.001 - Credentials in Files", "T1114 - Email Collection"]
    ),

    # ═══════════════════════════════════════════════════════
    # WINDOWS — EXECUTION (additional)
    # ═══════════════════════════════════════════════════════
    AleffPayload(
        name        = "Install Any Arbitrary VSCode Extension",
        category    = "Execution",
        platform    = "Windows",
        pap         = "yellow",
        path        = "Windows/Execution/Install_Any_Arbitrary_VSCode_Extension",
        description = "Silently installs any arbitrary VSCode extension by ID, including malicious or backdoored extensions.",
        teach       = "VSCode extensions run with full user-level privileges and have access to the filesystem, network, and terminal. A malicious extension can keylog, exfiltrate code, maintain persistence, and communicate with C2 infrastructure — all appearing as legitimate development tooling. This payload silently installs any extension by its marketplace ID using 'code --install-extension'.",
        defend      = "Enforce extension allowlisting via VSCode enterprise policies (extensions.allowed list). Monitor for 'code --install-extension' execution from non-interactive processes. Audit installed extensions regularly against approved list. Disable auto-update for extensions in sensitive environments.",
        config_needed = ["VSCode extension ID to install"],
        mitre       = ["T1059.001 - PowerShell", "T1546 - Event Triggered Execution"]
    ),
    AleffPayload(
        name        = "Set An Arbitrary And Persistent Tor Circuit (Linux)",
        category    = "Execution",
        platform    = "GNU-Linux",
        pap         = "yellow",
        path        = "GNU-Linux/Execution/Set_An_Arbitrary_And_Persistent_Tor_Circuit",
        description = "Configures specific Tor relay nodes (entry, middle, exit) persistently in the torrc file, locking the circuit.",
        teach       = "Tor normally selects random relay nodes for each circuit. By hardcoding specific nodes in torrc (EntryNodes, MiddleNodes, ExitNodes with StrictNodes 1), you force all Tor traffic through relays you control or trust. This is used for: ensuring traffic exits from a specific country, using known-clean relays for sensitive operations, or testing specific relay performance. The modification persists across Tor restarts.",
        defend      = "Monitor modifications to /etc/tor/torrc or ~/.tor/torrc. Alert on StrictNodes appearing in torrc — this is unusual in legitimate use. Outbound Tor connections from workstations may violate security policy; block TCP 9001 and 9030 at the firewall.",
        config_needed = ["Entry node fingerprint", "Middle node fingerprint", "Exit node fingerprint", "Root password or sudo password"],
        mitre       = ["T1090.003 - Multi-hop Proxy", "T1564.003 - Hidden Window"]
    ),
    AleffPayload(
        name        = "Set An Arbitrary And Persistent Tor Circuit (Windows)",
        category    = "Execution",
        platform    = "Windows",
        pap         = "yellow",
        path        = "Windows/Execution/Set_An_Arbitrary_And_Persistent_Tor_Circuit",
        description = "Configures specific Tor relay nodes persistently in TorBrowser's torrc on Windows.",
        teach       = "Same concept as the Linux version — forces TorBrowser to use specific relays. On Windows this requires navigating the TorBrowser UI to find and edit the torrc file. The payload automates the GUI navigation and text insertion. Requires TorBrowser to be installed.",
        defend      = "Monitor %APPDATA%\\TorBrowser modifications. Alert on TorBrowser launching via keyboard injection (parent process = Flipper/HID device). Block outbound Tor ports at perimeter firewall.",
        config_needed = ["Bridge/relay fingerprints", "TorBrowser version (UI may vary)"],
        mitre       = ["T1090.003 - Multi-hop Proxy"]
    ),
    AleffPayload(
        name        = "Edit The Default Real App With An Arbitrary",
        category    = "Execution",
        platform    = "GNU-Linux",
        pap         = "yellow",
        path        = "GNU-Linux/Execution/Edit_The_Default_Real_App_With_An_Arbitrary",
        description = "Replaces the default application handler for a file type with an arbitrary executable on Linux.",
        teach       = "Linux desktop environments use .desktop files and xdg-mime to associate file types with applications. By modifying these associations, you can replace the 'open PDF' action with a malicious script — the next time the user double-clicks a PDF, they execute your payload instead of Evince/Okular. This is a persistence technique that survives reboots and is extremely hard to detect visually.",
        defend      = "Monitor changes to ~/.local/share/applications/ and /etc/xdg/ for new or modified .desktop files. Audit xdg-mime database changes. User-level persistence here doesn't require root — make it part of your Linux endpoint hardening audit checklist.",
        config_needed = ["Target file type (MIME type)", "Path to arbitrary executable"],
        mitre       = ["T1546.004 - Unix Shell Configuration Modification", "T1574 - Hijack Execution Flow"]
    ),
    AleffPayload(
        name        = "Set An Arbitrary DNS - IPv4 version",
        category    = "Execution",
        platform    = "Windows",
        pap         = "green",
        path        = "Windows/Execution/Set_An_Arbitrary_DNS-IPv4_version",
        description = "Changes the system DNS server to an arbitrary IPv4 address via PowerShell without admin rights where possible.",
        teach       = "DNS is the phonebook of the internet. By changing DNS to an attacker-controlled server, you enable: DNS hijacking (intercept all domain lookups), traffic redirection to phishing sites, DNS-based C2 communication, and bypassing DNS-based security filters. This payload changes DNS for the active network adapter using PowerShell's Set-DnsClientServerAddress.",
        defend      = "Monitor for DNS server changes via Windows Event ID 11 (network configuration change). Enforce DNS settings via GPO (the policy overrides manual changes). Use DHCP-enforced DNS so clients always receive the correct server. Monitor for DNS queries to unusual resolver IPs from endpoints.",
        config_needed = [],
        mitre       = ["T1565.001 - Stored Data Manipulation", "T1071.004 - DNS"]
    ),
    AleffPayload(
        name        = "Add An Exception To Avast Antivirus",
        category    = "Execution",
        platform    = "Windows",
        pap         = "green",
        path        = "Windows/Execution/Add_An_Excepiton_To_Avast_Antivirus",
        description = "Adds an exclusion path to Avast Antivirus via the UI, allowing malware in that directory to evade scanning.",
        teach       = "Antivirus exclusions tell the scanner to skip specific directories entirely. By adding an exclusion for %TEMP% or a custom path, you create a landing zone where dropped payloads will never be scanned. This payload navigates the Avast UI to add the exclusion — no admin rights or registry access required. This technique works against many AV products that expose exclusion management to the logged-in user.",
        defend      = "Enforce AV exclusion policy centrally via management console — prevent users from adding their own exclusions. Alert on Avast exclusion additions (visible in Avast logs and Windows Event Log). Monitor for processes being spawned from excluded directories.",
        config_needed = [],
        mitre       = ["T1562.001 - Disable or Modify Tools", "T1036 - Masquerading"]
    ),
    AleffPayload(
        name        = "Starting a PowerShell with administrator permissions",
        category    = "Execution",
        platform    = "Windows",
        pap         = "green",
        path        = "Windows/Execution/Starting_a_PowerShell_with_administrator_permissions_in_Windows",
        description = "Opens an elevated PowerShell prompt using keyboard shortcuts, bypassing the need to right-click and 'Run as Administrator'.",
        teach       = "This payload uses WIN+X → A to open an admin PowerShell — the fastest way to get elevated execution via HID injection. If the target machine uses standard UAC (not maximum), this brings up a UAC prompt that the payload automatically confirms. Useful as a precursor to any payload requiring administrator privileges.",
        defend      = "Configure UAC to 'Always notify' (highest level) which makes UAC prompts harder to auto-confirm. Require Secure Desktop for UAC prompts (the dimmed screen) — HID devices cannot interact with the Secure Desktop. Monitor for PowerShell processes with elevated tokens spawned without a preceding user interaction.",
        config_needed = [],
        mitre       = ["T1548.002 - Bypass User Account Control", "T1059.001 - PowerShell"]
    ),
    AleffPayload(
        name        = "Change the password of the Windows user",
        category    = "Execution",
        platform    = "Windows",
        pap         = "yellow",
        path        = "Windows/Execution/Change_the_password_of_the_windows_user",
        description = "Changes the current Windows user's password via net user command.",
        teach       = "If you know the current password (or have admin rights), 'net user USERNAME NEWPASSWORD' instantly changes the account password. This enables: account lockout of the legitimate user, persistent access with known credentials, or account takeover. Requires knowing the current username (payload auto-detects with $env:USERNAME).",
        defend      = "Windows Security Event 4723 (password change attempt) and 4724 (password reset attempt) — alert on these from non-interactive sessions. Monitor for 'net user' execution. Privileged account password changes should require MFA confirmation.",
        config_needed = ["New password to set"],
        mitre       = ["T1531 - Account Access Removal", "T1098 - Account Manipulation"]
    ),
    AleffPayload(
        name        = "Uninstall A Specific App On Windows Through Control Panel",
        category    = "Execution",
        platform    = "Windows",
        pap         = "yellow",
        path        = "Windows/Execution/Uninstall_A_Specific_App_On_Windows_Through_Control_Panel",
        description = "Navigates Control Panel to uninstall a specified application without admin rights (user-installed apps).",
        teach       = "This payload navigates Control Panel → Programs → Uninstall a program to remove a target application via UI automation. Useful for: removing security software the user installed, removing monitoring tools, or disabling productivity software. The target app name must be specified — the payload searches and clicks through the UI.",
        defend      = "Monitor for msiexec.exe /x or wusa.exe /uninstall invocations. Windows Installer Event ID 1034 logs software removal. Enterprise software should be installed at the machine level (requiring admin for uninstall) rather than user level.",
        config_needed = ["Application name to uninstall"],
        mitre       = ["T1562.001 - Disable or Modify Tools"]
    ),
    AleffPayload(
        name        = "Defend yourself against AtlasVPN bugdoor",
        category    = "Incident_Response",
        platform    = "GNU-Linux",
        pap         = "yellow",
        path        = "GNU-Linux/Execution/Defend_yourself_against_AtlasVPN_bugdoor",
        description = "Applies the remediation for the AtlasVPN Linux API backdoor vulnerability that exposed the local socket to unauthenticated commands.",
        teach       = "AtlasVPN's Linux client exposed an unprotected local API socket that any local process could send commands to — including 'disconnect VPN'. This was a backdoor that could be exploited by malicious websites via DNS rebinding to disconnect users from their VPN without their knowledge. This payload applies the fix by removing the vulnerable socket or updating the client.",
        defend      = "Always update VPN clients promptly. Audit local listening sockets with 'ss -tlnp' or 'netstat -tlnp'. Local API sockets should require authentication even for local processes. This class of vulnerability (unauthenticated local API) affects many VPN clients.",
        config_needed = ["Sudo password"],
        mitre       = ["T1562.001 - Disable or Modify Tools", "T1498 - Network Denial of Service"]
    ),

    # ═══════════════════════════════════════════════════════
    # WINDOWS — PRANK (additional)
    # ═══════════════════════════════════════════════════════
    AleffPayload(
        name        = "Continuous Print In Terminal",
        category    = "Prank",
        platform    = "Windows",
        pap         = "green",
        path        = "Windows/Prank/ContinuousPrintInTerminal",
        description = "Opens a terminal and continuously prints a customizable message in an infinite loop.",
        teach       = "A harmless but visually alarming prank — opens CMD and runs an infinite loop printing whatever text is configured. Demonstrates HID injection speed and the ease with which physical access translates to UI control. Used in security awareness demonstrations to show what BadUSB can do in under 5 seconds.",
        defend      = "Physical security is the only defense against HID injection. USB port locks, endpoint USB device control policies, and security awareness training about unknown USB devices.",
        config_needed = [],
        mitre       = ["T1200 - Hardware Additions"]
    ),
    AleffPayload(
        name        = "Play A Song Through Spotify",
        category    = "Prank",
        platform    = "Windows",
        pap         = "green",
        path        = "Windows/Prank/PlayASongThroughSpotify",
        description = "Opens Spotify and plays a specific song or playlist via keyboard shortcuts.",
        teach       = "Demonstrates UI automation via HID — Spotify's keyboard shortcut system allows searching and playing without mouse interaction. Harmless demonstration payload. In a social engineering context, unexpected audio playing from a workstation causes confusion and distraction — useful for red team physical access demonstrations.",
        defend      = "Physical security. Disable USB ports on workstations in secure areas.",
        config_needed = [],
        mitre       = ["T1200 - Hardware Additions"]
    ),
    AleffPayload(
        name        = "Full-Screen Banner Joke",
        category    = "Prank",
        platform    = "Windows",
        pap         = "green",
        path        = "Windows/Prank/Full-ScreenBannerJoke",
        description = "Creates and displays a full-screen PowerShell window with a customizable banner message.",
        teach       = "Uses PowerShell's WPF capabilities to create a full-screen overlay window with custom text and colors. Harmless demonstration of how HID injection can create convincing fake UI elements — the same technique used in more malicious scenarios to create fake login prompts or ransomware-style lock screens.",
        defend      = "Physical security. Monitor for PowerShell creating WPF/Windows Forms windows from non-interactive sessions.",
        config_needed = [],
        mitre       = ["T1200 - Hardware Additions", "T1036 - Masquerading"]
    ),
    AleffPayload(
        name        = "Try To Catch Me",
        category    = "Prank",
        platform    = "Windows",
        pap         = "yellow",
        path        = "Windows/Prank/Try_To_Catch_Me",
        description = "Creates a window with a button that moves away from the mouse cursor every time the user tries to click it.",
        teach       = "Demonstrates PowerShell GUI capabilities via HID injection. The moving button prank illustrates that HID-injected code can create interactive UI elements that persist and run independently after the USB device is removed. The Flipper is gone — the code keeps running.",
        defend      = "Physical security. Monitor for PowerShell spawning GUI windows from unexpected parent processes.",
        config_needed = [],
        mitre       = ["T1200 - Hardware Additions"]
    ),
    AleffPayload(
        name        = "Pranh(ex)",
        category    = "Prank",
        platform    = "Windows",
        pap         = "green",
        path        = "Windows/Prank/Pranh(ex)",
        description = "Opens the Windows Settings app to the 'About' page repeatedly in a loop.",
        teach       = "Simple UI disruption prank. Demonstrates persistent UI automation — keeps opening Settings pages. Harmless but shows the concept of infinite execution loops via HID injection.",
        defend      = "Physical security controls.",
        config_needed = [],
        mitre       = ["T1200 - Hardware Additions"]
    ),
    AleffPayload(
        name        = "Change Github Profile Settings",
        category    = "Prank",
        platform    = "Windows",
        pap         = "yellow",
        path        = "Windows/Prank/Change_Github_Profile_Settings",
        description = "Opens GitHub in a browser and navigates to profile settings to modify the user's GitHub profile.",
        teach       = "If a user is logged into GitHub in their browser, this payload navigates to github.com/settings/profile and makes changes to their public profile. Demonstrates browser session hijacking via HID — no credentials needed because the browser session cookie provides authentication. The same technique works for any site the user is currently logged into.",
        defend      = "Log out of sensitive web services when not actively using them. Browser session timeouts. Hardware security keys bind sessions to the origin domain — but don't protect against an already-authenticated browser session being abused via HID.",
        config_needed = ["GitHub profile field to modify", "New value"],
        mitre       = ["T1185 - Browser Session Hijacking", "T1200 - Hardware Additions"]
    ),
    AleffPayload(
        name        = "Prank In The Middle - Thunderbird",
        category    = "Prank",
        platform    = "Windows",
        pap         = "green",
        path        = "Windows/Prank/Prank_In_The_Middle_Thunderbird",
        description = "Opens Thunderbird and composes a new email using whatever address is configured, injecting a prank message.",
        teach       = "Demonstrates that HID injection can interact with any open application — including email clients. If Thunderbird is installed and configured, this payload composes and sends an email using the victim's own account. In a real attack context this would be a social engineering delivery mechanism — a 'message from the CEO's own computer'.",
        defend      = "Physical security. Email gateway inspection should catch anomalous sending behavior. Monitor for Thunderbird being launched by non-user processes.",
        config_needed = [],
        mitre       = ["T1200 - Hardware Additions", "T1534 - Internal Spearphishing"]
    ),

    # ═══════════════════════════════════════════════════════
    # MACOS — EXECUTION (additional)
    # ═══════════════════════════════════════════════════════
    AleffPayload(
        name        = "IPLogger - Discord Webhook",
        category    = "Exfiltration",
        platform    = "macOS",
        pap         = "yellow",
        path        = "MacOS/Execution/IPLogger-Discord_Webhook-by_bst04",
        description = "Retrieves the external IP address of the macOS target and exfiltrates it via Discord webhook. By bst04.",
        teach       = "Knowing a target's external IP address enables: geolocation, ISP identification, network range scanning, and targeted attacks against their home/office router. On macOS this uses 'curl ifconfig.me' or similar to get the public IP, then posts it to a Discord webhook. No admin rights required.",
        defend      = "Physical security. Monitor for curl commands to IP-check services (ifconfig.me, icanhazip.com, api.ipify.org). Network-level: block outbound requests to known IP-logging services.",
        config_needed = ["Discord webhook URL"],
        mitre       = ["T1590 - Gather Victim Network Information", "T1048 - Exfiltration Over Alternative Protocol"]
    ),

    # ═══════════════════════════════════════════════════════
    # WINDOWS — EXECUTION (additional)
    # ═══════════════════════════════════════════════════════
    AleffPayload(
        name        = "CheckBattery - by bst04",
        category    = "Execution",
        platform    = "Windows",
        pap         = "green",
        path        = "Windows/Execution/CheckBattery-by_bst04",
        description = "Checks and displays the current battery status and percentage on Windows via PowerShell.",
        teach       = "Utility payload demonstrating PowerShell's WMI query capabilities for hardware info. Uses Get-WmiObject Win32_Battery to retrieve battery charge level, status, and estimated runtime. Useful as a building block for payloads that need to check whether the target is a laptop (mobile target vs desktop).",
        defend      = "Physical security. WMI queries are legitimate admin activity — context matters for detection.",
        config_needed = [],
        mitre       = ["T1082 - System Information Discovery"]
    ),

    # ═══════════════════════════════════════════════════════
    # iOS — EXECUTION (additional)
    # ═══════════════════════════════════════════════════════
    AleffPayload(
        name        = "Text Someone Message With iPhone",
        category    = "Execution",
        platform    = "iOS",
        pap         = "yellow",
        path        = "iOS/Execution/Text_Someone_Message_With_iPhone-by_bst04",
        description = "Opens the iOS Messages app and sends a text message to a specified contact. By bst04.",
        teach       = "iOS's Bluetooth HID profile accepts keyboard input when paired. If a Flipper Zero is paired to an iPhone, it can inject keystrokes to navigate the Messages app and send texts. Demonstrates that BadUSB/HID attacks extend beyond computers to mobile devices. Useful for red team demonstrations of physical mobile device security.",
        defend      = "Only pair Bluetooth HID devices you trust. iOS prompts for pairing confirmation — users should never accept unexpected Bluetooth pairing requests. Enable USB Restricted Mode on iOS (Settings → Face ID & Passcode) to prevent USB accessories when locked.",
        config_needed = ["Recipient contact name or number", "Message text"],
        mitre       = ["T1200 - Hardware Additions", "T1534 - Internal Spearphishing"]
    ),

    # ═══════════════════════════════════════════════════════
    # GNU-LINUX — PRANK (additional)
    # ═══════════════════════════════════════════════════════
    AleffPayload(
        name        = "Kali Linux - This_damn_shell_doesn_t_work",
        category    = "Prank",
        platform    = "GNU-Linux",
        pap         = "green",
        path        = "GNU-Linux/Prank/This_damn_shell_doesn_t_work___so_sad!-KALI",
        description = "Kali Linux specific prank — replaces shell aliases so that common commands print fake error messages.",
        teach       = "Creates bash aliases that intercept common commands (ls, cd, pwd, etc.) and print realistic-looking error messages instead. Demonstrates persistent prank via shell configuration — the alias modifications survive session restarts. Shows how .bashrc/.zshrc modification (a real persistence technique) works.",
        defend      = "Monitor .bashrc, .zshrc, .bash_aliases for unauthorized modifications. Alert on alias commands being added to shell config files from non-interactive sessions.",
        config_needed = [],
        mitre       = ["T1546.004 - Unix Shell Configuration Modification"]
    ),
    AleffPayload(
        name        = "Linux - This_damn_shell_doesn_t_work",
        category    = "Prank",
        platform    = "GNU-Linux",
        pap         = "green",
        path        = "GNU-Linux/Prank/This_damn_shell_doesn_t_work___so_sad!-LINUX",
        description = "Generic Linux prank — replaces shell aliases so common commands print fake errors. Works on Ubuntu, Debian, Fedora.",
        teach       = "Same technique as the Kali version but tuned for generic Linux distributions and their default terminal configurations. Demonstrates shell configuration persistence and how the same attack must be adapted per distribution due to different default shells (bash vs zsh vs fish).",
        defend      = "Shell config file integrity monitoring. EDR with file system monitoring on user home directories.",
        config_needed = [],
        mitre       = ["T1546.004 - Unix Shell Configuration Modification"]
    ),

    # ═══════════════════════════════════════════════════════
    # GNU-LINUX — INCIDENT RESPONSE (additional)
    # ═══════════════════════════════════════════════════════
    AleffPayload(
        name        = "Auto-Check Cisco IOS XE Backdoor (CVE-2023-20198 / CVE-2023-20273)",
        category    = "Incident_Response",
        platform    = "GNU-Linux",
        pap         = "red",
        path        = "GNU-Linux/Incident_Response/Auto-Check_Cisco_IOS_XE_Backdoor_based_on_CVE-2023-20198_and_CVE",
        description = "Automatically checks a Cisco IOS XE device for the CVE-2023-20198 and CVE-2023-20273 backdoor implant.",
        teach       = "CVE-2023-20198 was a zero-day in Cisco IOS XE's web management interface that allowed unauthenticated RCE with privilege level 15 (full admin). Attackers exploited it to implant a backdoor (CVE-2023-20273). This payload automates the detection check — sending the specific HTTP request that reveals whether a device has been compromised. Critical for IR teams responding to Cisco device incidents.",
        defend      = "Disable the Cisco IOS XE web UI if not required (ip http server / ip http secure-server). Apply Cisco patches immediately. Monitor for new user accounts on IOS XE devices — the backdoor creates a local admin account. Use Cisco's published IOC checks.",
        config_needed = ["Target Cisco device IP (manual setup required)"],
        mitre       = ["T1190 - Exploit Public-Facing Application", "T1505.003 - Web Shell"]
    ),

    # ═══════════════════════════════════════════════════════
    # WINDOWS — INCIDENT RESPONSE (additional)
    # ═══════════════════════════════════════════════════════
    AleffPayload(
        name        = "Defend yourself against CVE-2023-36884",
        category    = "Incident_Response",
        platform    = "Windows",
        pap         = "green",
        path        = "Windows/Incident_Response/Defend_yourself_against_CVE-2023-36884_Office_and_Windows_HTML_Remote_Code_Execution_Vulnerability",
        description = "Applies the registry mitigation for CVE-2023-36884 — a critical Microsoft Office/Windows HTML RCE vulnerability used in targeted attacks.",
        teach       = "CVE-2023-36884 was exploited by Storm-0978 (RomCom group) in targeted attacks against NATO summit attendees. The vulnerability allows RCE via specially crafted Office documents without requiring the preview pane or any macros. This payload applies the documented registry workaround that blocks exploitation while waiting for the official patch. Demonstrates using Flipper Zero for rapid defensive deployment across multiple machines.",
        defend      = "Apply Microsoft's official patch (KB5027698). The registry workaround sets HKLM\\SOFTWARE\\Microsoft\\Internet Explorer\\Main\\FeatureControl\\FEATURE_BLOCK_CROSS_PROTOCOL_FILE_NAVIGATION. Verify with: reg query HKLM\\SOFTWARE\\Microsoft\\Internet Explorer\\Main\\FeatureControl\\FEATURE_BLOCK_CROSS_PROTOCOL_FILE_NAVIGATION",
        config_needed = [],
        mitre       = ["T1203 - Exploitation for Client Execution", "T1566.001 - Phishing: Spearphishing Attachment"]
    ),
]


# ── Helper functions for ERR0RS integration ───────────────────────────────────


# ── Helper functions for ERR0RS integration ───────────────────────────────────

def get_all_payloads() -> List[AleffPayload]:
    """Return the complete aleff payload catalogue."""
    return ALEFF_PAYLOADS


def get_payloads_by_platform(platform: str) -> List[AleffPayload]:
    """Filter payloads by platform: Windows, GNU-Linux, iOS, macOS."""
    return [p for p in ALEFF_PAYLOADS if p.platform.lower() == platform.lower()]


def get_payloads_by_category(category: str) -> List[AleffPayload]:
    """Filter by category: Credentials, Exfiltration, Execution, Phishing, Prank, Incident_Response."""
    return [p for p in ALEFF_PAYLOADS if p.category.lower() == category.lower()]


def get_payloads_by_pap(pap: str) -> List[AleffPayload]:
    """Filter by PAP level: green (plug-and-play), yellow (minor config), red (manual setup)."""
    return [p for p in ALEFF_PAYLOADS if p.pap == pap]


def get_payload_by_name(name: str) -> Optional[AleffPayload]:
    """Find a payload by exact or partial name match."""
    name_lower = name.lower()
    for p in ALEFF_PAYLOADS:
        if name_lower in p.name.lower():
            return p
    return None


def summary_stats() -> dict:
    """Return stats for display in ERR0RS Payload Studio."""
    return {
        "total":          len(ALEFF_PAYLOADS),
        "windows":        len(get_payloads_by_platform("Windows")),
        "linux":          len(get_payloads_by_platform("GNU-Linux")),
        "ios":            len(get_payloads_by_platform("iOS")),
        "macos":          len(get_payloads_by_platform("macOS")),
        "plug_and_play":  len(get_payloads_by_pap("green")),
        "minor_config":   len(get_payloads_by_pap("yellow")),
        "manual_setup":   len(get_payloads_by_pap("red")),
        "credentials":    len(get_payloads_by_category("Credentials")),
        "exfiltration":   len(get_payloads_by_category("Exfiltration")),
        "execution":      len(get_payloads_by_category("Execution")),
        "phishing":       len(get_payloads_by_category("Phishing")),
        "prank":          len(get_payloads_by_category("Prank")),
        "incident_response": len(get_payloads_by_category("Incident_Response")),
        "source":         ALEFF_REPO_URL,
        "author":         ALEFF_AUTHOR,
        "license":        ALEFF_LICENSE,
    }
