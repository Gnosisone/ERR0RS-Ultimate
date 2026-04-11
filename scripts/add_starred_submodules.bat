@echo off
echo ============================================================
echo  ERR0RS-Ultimate - Adding Starred Repo Submodules
echo  Source: github.com/Gnosisone/starred
echo ============================================================
echo.
cd /d H:\ERR0RS-Ultimate

:: ── EVASION ──────────────────────────────────────────────────
echo [+] Adding evasion knowledge...
git submodule add https://github.com/vxunderground/MalwareSourceCode.git knowledge/evasion/MalwareSourceCode
git submodule add https://github.com/vxunderground/VX-API.git knowledge/evasion/VX-API
git submodule add https://github.com/vxunderground/VXUG-Papers.git knowledge/evasion/VXUG-Papers

:: ── EXPLOITATION ─────────────────────────────────────────────
echo [+] Adding exploitation knowledge...
git submodule add https://github.com/MatheuZSecurity/Singularity.git knowledge/exploitation/Singularity-Rootkit

:: ── CREDENTIALS ──────────────────────────────────────────────
echo [+] Adding credential tools...
git submodule add https://github.com/AlessandroZ/LaZagne.git knowledge/credentials/LaZagne
git submodule add https://github.com/djhohnstein/KittyLitter.git knowledge/credentials/KittyLitter
git submodule add https://github.com/nccgroup/redsnarf.git knowledge/credentials/redsnarf


:: ── WINDOWS ──────────────────────────────────────────────────
echo [+] Adding Windows knowledge...
git submodule add https://github.com/djhohnstein/Priv2Admin.git knowledge/windows/Priv2Admin

:: ── RED TEAM ─────────────────────────────────────────────────
echo [+] Adding red team resources...
git submodule add https://github.com/mandiant/commando-vm.git knowledge/redteam/commando-vm
git submodule add https://github.com/nixawk/pentest-wiki.git knowledge/redteam/pentest-wiki
git submodule add https://github.com/OlivierLaflamme/Cheatsheet-God.git knowledge/redteam/Cheatsheet-God
git submodule add https://github.com/JoasASantos/OSCE3-Complete-Guide.git knowledge/redteam/OSCE3-Complete-Guide
git submodule add https://github.com/farhanashrafdev/90DaysOfCyberSecurity.git knowledge/redteam/90DaysOfCyberSecurity
git submodule add https://github.com/sundowndev/hacker-roadmap.git knowledge/redteam/hacker-roadmap
git submodule add https://github.com/Z4nzu/hackingtool.git knowledge/redteam/hackingtool

:: ── THREAT INTEL ─────────────────────────────────────────────
echo [+] Adding threat intel...
git submodule add https://github.com/CyberMonitor/APT_CyberCriminal_Campagin_Collections.git knowledge/threat-intel/APT-Collections
git submodule add https://github.com/BushidoUK/Open-source-tools-for-CTI.git knowledge/threat-intel/Open-source-CTI-tools

:: ── HARDWARE / BADUSB ────────────────────────────────────────
echo [+] Adding hardware and BadUSB...
git submodule add https://github.com/i-am-shodan/USBArmyKnife.git knowledge/hardware/USBArmyKnife
git submodule add https://github.com/dbisu/pico-ducky.git knowledge/hardware/pico-ducky
git submodule add https://github.com/justcallmekoko/ESP32Marauder.git knowledge/hardware/ESP32Marauder
git submodule add https://github.com/DarkFlippers/unleashed-firmware.git knowledge/hardware/flipper-unleashed
git submodule add https://github.com/greatscottgadgets/ubertooth.git knowledge/hardware/ubertooth
git submodule add https://github.com/beigeworm/BadUSB-Files-For-FlipperZero.git knowledge/badusb/BadUSB-FlipperZero-Scripts
git submodule add https://github.com/hak5/usbrubberducky-payloads.git knowledge/badusb/usbrubberducky-payloads


:: ── OSINT ────────────────────────────────────────────────────
echo [+] Adding OSINT tools...
git submodule add https://github.com/Lissy93/web-check.git knowledge/osint/web-check

:: ── ENUMERATION ──────────────────────────────────────────────
echo [+] Adding enumeration tools...
git submodule add https://github.com/trustedsec/ridenum.git knowledge/enumeration/ridenum
git submodule add https://github.com/bashcrumb/offsec-enum.git knowledge/enumeration/offsec-enum

:: ── SOCIAL ENGINEERING ───────────────────────────────────────
echo [+] Adding social engineering...
git submodule add https://github.com/jonaslejon/malicious-pdf.git knowledge/social-engineering/malicious-pdf

:: ── MOBILE / iOS ─────────────────────────────────────────────
echo [+] Adding mobile/iOS research...
git submodule add https://github.com/d4rks1d33/ios-resources.git knowledge/mobile/ios-resources
git submodule add https://github.com/jsharkey13/iphone_backup_decrypt.git knowledge/mobile/iphone-backup-decrypt
git submodule add https://github.com/00xglitch/Bella.git knowledge/mobile/Bella-macOS-RAT
git submodule add https://github.com/Marten4n6/EvilOSX.git knowledge/mobile/EvilOSX

:: ── NETWORK ──────────────────────────────────────────────────
echo [+] Adding network tools...
git submodule add https://github.com/IamFalseBeliefs/Arpoof.git knowledge/network/Arpoof

:: ── AI SECURITY ──────────────────────────────────────────────
echo [+] Adding AI security research...
git submodule add https://github.com/jivoi/awesome-ml-for-cybersecurity.git knowledge/ai-security/awesome-ml-cybersecurity
git submodule add https://github.com/Arcanum-Sec/arc_pi_taxonomy.git knowledge/ai-security/prompt-injection-taxonomy

:: ── FINALIZE ─────────────────────────────────────────────────
echo.
echo [+] Running git add and commit...
git add .gitmodules
git add knowledge/
git commit -m "feat: add starred repos as knowledge base submodules (Gnosisone/starred)

Added 35 new submodules across 10 categories:
- evasion: vxunderground MalwareSourceCode, VX-API, VXUG-Papers
- exploitation: Singularity Linux rootkit
- credentials: LaZagne, KittyLitter, redsnarf
- windows: Priv2Admin
- redteam: commando-vm, pentest-wiki, Cheatsheet-God, OSCE3, 90Days, hacker-roadmap, hackingtool
- threat-intel: APT Collections, CTI tools
- hardware: USBArmyKnife, pico-ducky, ESP32Marauder, unleashed-firmware, ubertooth
- badusb: BadUSB FlipperZero scripts, USB Rubber Ducky payloads
- osint: web-check
- enumeration: ridenum, offsec-enum
- social-engineering: malicious-pdf
- mobile: ios-resources, iphone-backup-decrypt, Bella, EvilOSX
- network: Arpoof
- ai-security: awesome-ml-cybersecurity, prompt-injection-taxonomy"

echo.
echo ============================================================
echo  Done! All starred repos added as submodules.
echo  Run: git push to sync with GitHub
echo ============================================================
pause
