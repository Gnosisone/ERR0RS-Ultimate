@echo off
REM ═══════════════════════════════════════════════════════════════
REM  ERR0RS Ultimate — New KB Submodule Addition Script
REM  Sources: nccgroup, djhohnstein, S3cur3Th1sSh1t, trustedsec,
REM           karma9874, dineshshetty, hakaioffsec
REM  Run from: H:\ERR0RS-Ultimate\
REM ═══════════════════════════════════════════════════════════════

cd /d H:\ERR0RS-Ultimate
echo [ERR0RS] Adding new knowledge base submodules...

REM ─── NCC GROUP ───────────────────────────────────────────────
echo [1/18] NCC Group: ScoutSuite (multi-cloud auditing)
git submodule add https://github.com/nccgroup/ScoutSuite.git knowledge/recon/ScoutSuite

echo [2/18] NCC Group: Singularity (DNS rebinding framework)
git submodule add https://github.com/nccgroup/singularity.git knowledge/exploitation/singularity

echo [3/18] NCC Group: SteppingStones (Red Team activity hub)
git submodule add https://github.com/nccgroup/SteppingStones.git knowledge/redteam/SteppingStones

echo [4/18] NCC Group: House (Frida mobile analysis web GUI)
git submodule add https://github.com/nccgroup/house.git knowledge/mobile/house-frida

REM ─── DJHOHNSTEIN (IBM X-Force Red / Kali contrib) ────────────
echo [5/18] djhohnstein: SharpChromium (.NET browser cred stealer)
git submodule add https://github.com/djhohnstein/SharpChromium.git knowledge/credentials/SharpChromium

echo [6/18] djhohnstein: SharpWeb (Chrome/Firefox/IE creds)
git submodule add https://github.com/djhohnstein/SharpWeb.git knowledge/credentials/SharpWeb

echo [7/18] djhohnstein: SharpShares (domain share enumeration)
git submodule add https://github.com/djhohnstein/SharpShares.git knowledge/enumeration/SharpShares

echo [8/18] djhohnstein: EventLogParser (parse PS + security logs)
git submodule add https://github.com/djhohnstein/EventLogParser.git knowledge/enumeration/EventLogParser

echo [9/18] djhohnstein: WireTap (video/audio/keyboard hardware)
git submodule add https://github.com/djhohnstein/WireTap.git knowledge/surveillance/WireTap

REM ─── S3CUR3TH1SSH1T ──────────────────────────────────────────
echo [10/18] S3cur3Th1sSh1t: WinPwn (Windows pentest automation)
git submodule add https://github.com/S3cur3Th1sSh1t/WinPwn.git knowledge/windows/WinPwn

echo [11/18] S3cur3Th1sSh1t: Amsi-Bypass-Powershell (AMSI bypass collection)
git submodule add https://github.com/S3cur3Th1sSh1t/Amsi-Bypass-Powershell.git knowledge/evasion/Amsi-Bypass-Powershell

echo [12/18] S3cur3Th1sSh1t: PowerSharpPack (.NET tools in PowerShell)
git submodule add https://github.com/S3cur3Th1sSh1t/PowerSharpPack.git knowledge/windows/PowerSharpPack

echo [13/18] S3cur3Th1sSh1t: OffensiveVBA (VBA macro AV evasion)
git submodule add https://github.com/S3cur3Th1sSh1t/OffensiveVBA.git knowledge/evasion/OffensiveVBA

REM ─── TRUSTEDSEC ──────────────────────────────────────────────
echo [14/18] TrustedSec: social-engineer-toolkit (SET)
git submodule add https://github.com/trustedsec/social-engineer-toolkit.git knowledge/social-engineering/SET

echo [15/18] TrustedSec: CS-Situational-Awareness-BOF (Cobalt Strike BOFs)
git submodule add https://github.com/trustedsec/CS-Situational-Awareness-BOF.git knowledge/c2/CS-Situational-Awareness-BOF

echo [16/18] TrustedSec: hate_crack (Hashcat automation)
git submodule add https://github.com/trustedsec/hate_crack.git knowledge/credentials/hate_crack

REM ─── KARMA9874 ───────────────────────────────────────────────
echo [17/18] karma9874: AndroRAT (Android RAT - Java/Python)
git submodule add https://github.com/karma9874/AndroRAT.git knowledge/mobile/AndroRAT

REM ─── HAKAIOFFSEC ─────────────────────────────────────────────
echo [18/18] hakaioffsec: beerus-android (Android framework)
git submodule add https://github.com/hakaioffsec/beerus-android.git knowledge/mobile/beerus-android

echo.
echo [ERR0RS] All submodules added! Committing...
git add .gitmodules
git add knowledge/
git commit -m "feat: Add 18 new KB submodules - nccgroup/djhohnstein/S3cur3Th1sSh1t/trustedsec/karma9874/hakaioffsec"
git push origin main

echo.
echo [ERR0RS] DONE! Pull on Kali:
echo   cd ~/ERR0RS-Ultimate-fresh ^&^& git pull ^&^& git submodule update --init --recursive
pause
