"""
ERR0RS Ultimate — DarkCoderSc Knowledge Base Module
=====================================================
Indexes all DarkCoderSc repos (Jean-Pierre LESUEUR / Phrozen Security) for
RAG-powered AI queries. Covers C2 architecture, remote access, evasion,
PowerShell implants, and legacy RAT internals (SubSeven / Sub7).

Sources (all Apache-2.0 / GPL-3.0 open-source, research-grade):
  knowledge/c2/SubSeven             — SubSeven legacy RAT source (Delphi/Pascal)
  knowledge/c2/OptixGate            — Multi-purpose remote access tool (Pascal)
  knowledge/c2/PowerRemoteShell     — PowerShell bind/reverse shell module
  knowledge/c2/Sub7Fun              — Sub7 companion utilities
  knowledge/c2/PowerRemoteDesktop_LogonUI — WinLogon I/O plugin (C#)
  knowledge/evasion/inno-shellcode-example — InnoSetup shellcode loader
  knowledge/windows/run-as          — Windows RunAs utility (Delphi/Pascal)

Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
"""

from __future__ import annotations
import os
import json
import hashlib
import logging
from pathlib import Path
from typing import Optional

log = logging.getLogger("errors.ai.darkcodersc_kb")

ROOT_DIR = Path(__file__).resolve().parents[2]

# ── Repo catalogue ────────────────────────────────────────────────────────────
DARKCODERSC_REPOS = [
    {
        "id":       "subseven",
        "path":     "knowledge/c2/SubSeven",
        "title":    "SubSeven — Legacy RAT Source Code",
        "category": "c2",
        "tags":     ["rat", "remote-access", "c2", "delphi", "pascal", "legacy",
                     "subseven", "sub7", "remote-control", "darkcodersc"],
        "summary": (
            "SubSeven is one of the most historically significant Remote Access Trojans "
            "ever written. Originally created in the late 1990s, Jean-Pierre LESUEUR "
            "open-sourced the complete Pascal/Delphi codebase under Apache-2.0. "
            "Covers: stub/server architecture, plugin system, keylogger, screen capture, "
            "webcam capture, port redirect, file manager, registry editor, password stealer, "
            "chat, process manager, clipboard monitor, and full C2 protocol implementation. "
            "Critical for understanding legacy RAT internals, C2 design patterns, and how "
            "modern EDRs evolved to detect these behaviors."
        ),
        "attack_categories": [
            "C2 server/client architecture",
            "Remote keylogging",
            "Remote desktop / screen capture",
            "Password harvesting",
            "File system access",
            "Registry manipulation",
            "Process injection",
            "Port redirection / tunneling",
            "Plugin-based implant design",
        ],
        "defense_notes": (
            "SubSeven connections are detected by: unusual outbound TCP on ports 1243/27374, "
            "process hollowing artifacts, registry Run key persistence at "
            "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run, and network signatures "
            "for the Sub7 binary protocol header. Modern EDRs flag the binary on hash + "
            "behavioral analysis (keylogger + screencap + C2 beacon pattern)."
        ),
    },
    {
        "id":       "optixgate",
        "path":     "knowledge/c2/OptixGate",
        "title":    "OptixGate — Open-Source Windows Remote Access Tool",
        "category": "c2",
        "tags":     ["rat", "remote-access", "windows", "pascal", "c2",
                     "remote-desktop", "infosec", "darkcodersc", "phrozen"],
        "summary": (
            "OptixGate is a modern, actively maintained open-source multi-purpose remote "
            "access tool for Windows, built by Jean-Pierre LESUEUR (Microsoft MVP, Phrozen). "
            "Unlike legacy RATs it is designed for legitimate remote administration and "
            "security research — source code fully auditable under GPL-3.0. "
            "Covers: encrypted C2 channel, remote desktop streaming, file transfer, "
            "shell access, process management, and modular plugin architecture. "
            "Excellent reference for understanding how modern RAT/RMM tools implement "
            "secure C2 channels versus legacy plaintext protocols."
        ),
        "attack_categories": [
            "Encrypted C2 channel implementation",
            "Remote desktop streaming protocol",
            "Authenticated file transfer",
            "Interactive remote shell",
            "Process enumeration and management",
            "Modular implant plugin system",
        ],
        "defense_notes": (
            "OptixGate uses encrypted channels — detection relies on behavioral analysis "
            "rather than signature matching. Look for: unusual persistent processes with "
            "outbound encrypted TCP, screen-capture API calls (BitBlt, GetDC), "
            "CreateRemoteThread activity, and anomalous network connections from "
            "non-browser processes."
        ),
    },
    {
        "id":       "powerremoteshell",
        "path":     "knowledge/c2/PowerRemoteShell",
        "title":    "PowerRemoteShell — PowerShell Bind/Reverse Shell Module",
        "category": "c2",
        "tags":     ["powershell", "reverse-shell", "bind-shell", "c2",
                     "remote-shell", "windows", "infosec", "darkcodersc"],
        "summary": (
            "PowerRemoteShell is a PowerShell module (and standalone script) by "
            "Jean-Pierre LESUEUR that implements both bind and reverse shell with "
            "optional authentication. Designed for pentesting and security research. "
            "Features: encrypted session support, credential authentication on shell open, "
            "both TCP bind and reverse TCP modes, works as importable PS module or "
            "standalone one-liner. Critical ERR0RS integration target — can be invoked "
            "directly as a post-exploitation shell module."
        ),
        "attack_categories": [
            "PowerShell reverse TCP shell",
            "PowerShell bind shell",
            "Authenticated shell sessions",
            "Post-exploitation interactive access",
            "Living-off-the-land (LOLBAS) technique",
        ],
        "defense_notes": (
            "Detection: PowerShell network connections (powershell.exe establishing TCP), "
            "AMSI scanning of the module content, Script Block Logging (Event ID 4104), "
            "Module Logging (Event ID 4103), Windows Defender ATP behavioral detection "
            "on reverse shell pattern. LOLBAS — no dropped binary, evades file-based AV."
        ),
        "errz_integration": (
            "Wire into ERR0RS post-exploitation module: "
            "errz> shell powershell-reverse LHOST=<IP> LPORT=<PORT>"
        ),
    },
    {
        "id":       "inno_shellcode",
        "path":     "knowledge/evasion/inno-shellcode-example",
        "title":    "InnoSetup Shellcode Loader — AV Evasion via Installer Engine",
        "category": "evasion",
        "tags":     ["shellcode", "evasion", "inno", "innosetup", "loader",
                     "av-bypass", "windows", "malware", "darkcodersc"],
        "summary": (
            "Demonstrates shellcode execution through the InnoSetup Pascal scripting engine "
            "— a legitimate Windows installer framework. Technique: embed shellcode in a "
            "valid-looking software installer, execute via InnoSetup's built-in Pascal "
            "script engine at install time. AV evasion is achieved because InnoSetup.exe "
            "is a signed, trusted binary — most security tools whitelist it. "
            "Critical for understanding living-off-the-land loader techniques and "
            "how attackers abuse legitimate signed binaries for shellcode delivery."
        ),
        "attack_categories": [
            "Signed binary shellcode loader",
            "AV/EDR evasion via trusted process",
            "Living-off-the-land (LOLBAS)",
            "Shellcode embedding in installer",
            "Pascal script engine abuse",
        ],
        "defense_notes": (
            "Detection: Monitoring InnoSetup process for unexpected network connections "
            "or process spawning, AMSI hooks on script engine, memory scanning for "
            "shellcode patterns (MZ header, PE headers in allocated RWX memory), "
            "Sysmon Event ID 8 (CreateRemoteThread), Event ID 10 (Process Access)."
        ),
    },
    {
        "id":       "run_as",
        "path":     "knowledge/windows/run-as",
        "title":    "run-as — Windows Token Impersonation / RunAs Utility",
        "category": "windows",
        "tags":     ["runas", "windows", "token", "impersonation", "privesc",
                     "delphi", "pascal", "darkcodersc"],
        "summary": (
            "A simple but powerful Windows RunAs program by Jean-Pierre LESUEUR that "
            "allows running processes as a different user via token duplication. "
            "Written in Delphi/Pascal with full source. Demonstrates Windows token "
            "impersonation APIs: LogonUser, DuplicateTokenEx, CreateProcessAsUser. "
            "Useful for understanding privilege escalation via token manipulation, "
            "lateral movement using stolen credentials, and how Windows process "
            "security tokens work at the API level."
        ),
        "attack_categories": [
            "Token impersonation / manipulation",
            "Privilege escalation via token duplication",
            "Lateral movement with alternate credentials",
            "CreateProcessAsUser API abuse",
            "Windows security token internals",
        ],
        "defense_notes": (
            "Detection: Logon events (Event ID 4624 type 9 — NewCredentials logon), "
            "Token duplication (Sysmon Event ID 10), unexpected process parent/child "
            "relationships, Security audit policy for token-based privilege abuse."
        ),
    },
    {
        "id":       "sub7fun",
        "path":     "knowledge/c2/Sub7Fun",
        "title":    "Sub7Fun — SubSeven Companion and Utility Tools",
        "category": "c2",
        "tags":     ["sub7", "subseven", "rat", "c2", "delphi", "pascal",
                     "remote-access", "darkcodersc", "companion"],
        "summary": (
            "Companion utilities for the SubSeven RAT ecosystem. Includes helper tools "
            "for working with Sub7 protocol, server building, and testing. Provides "
            "deeper insight into the Sub7/SubSeven C2 protocol and plugin communication "
            "format — useful for writing detection rules and understanding legacy "
            "RAT binary communication at the packet level."
        ),
        "attack_categories": [
            "Sub7 protocol analysis",
            "Legacy RAT C2 companion tools",
            "Server stub generation and testing",
        ],
        "defense_notes": (
            "Same as SubSeven — port/protocol signatures on 1243/27374, binary protocol "
            "header detection, behavioral patterns of Sub7-family implants."
        ),
    },
    {
        "id":       "powerremotedesktop_logonui",
        "path":     "knowledge/c2/PowerRemoteDesktop_LogonUI",
        "title":    "PowerRemoteDesktop LogonUI — WinLogon Screen Capture Plugin (C#)",
        "category": "c2",
        "tags":     ["winlogon", "logonui", "remote-desktop", "c2", "csharp",
                     "windows", "darkcodersc", "phrozen", "screen-capture"],
        "summary": (
            "A C# WinLogon I/O plugin for PowerRemoteDesktop that captures the Windows "
            "logon screen (WinLogon / LogonUI) — the UAC / Ctrl+Alt+Del / lock screen. "
            "Normally inaccessible to remote desktop tools, this plugin hooks into the "
            "WinLogon process to capture and stream the secure desktop. "
            "Demonstrates: SYSTEM-level process interaction, WinLogon session 0 isolation "
            "bypass, secure desktop capture, and advanced remote access techniques that "
            "go beyond standard RDP capabilities."
        ),
        "attack_categories": [
            "Secure desktop / WinLogon capture",
            "Session 0 isolation bypass",
            "SYSTEM-level process interaction",
            "Advanced remote desktop techniques",
            "Credential capture at logon screen",
        ],
        "defense_notes": (
            "Detection: Unexpected DLLs injected into WinLogon.exe (Sysmon Event ID 7), "
            "SYSTEM-level process spawning unusual children, WinLogon network connections, "
            "Protected Process Light (PPL) bypass detection."
        ),
    },
]


# ── File walker — indexes actual source files from submodule paths ────────────

INDEXED_EXTENSIONS = {
    ".pas", ".dpr", ".dfm",       # Delphi/Pascal
    ".cs",                        # C#
    ".ps1", ".psm1", ".psd1",     # PowerShell
    ".iss",                       # InnoSetup
    ".py",                        # Python
    ".md", ".txt",                # Docs
    ".json",                      # Config/metadata
}

MAX_FILE_SIZE_KB = 64  # Skip huge binary/asset files


def _walk_repo_files(repo_path: Path) -> list[dict]:
    """Walk a repo directory and return file chunks for RAG ingestion."""
    chunks = []
    if not repo_path.exists():
        log.warning(f"Repo path not found: {repo_path}")
        return chunks

    for fpath in repo_path.rglob("*"):
        if fpath.is_dir():
            continue
        if fpath.suffix.lower() not in INDEXED_EXTENSIONS:
            continue
        try:
            size_kb = fpath.stat().st_size / 1024
            if size_kb > MAX_FILE_SIZE_KB:
                continue
            content = fpath.read_text(encoding="utf-8", errors="replace")
            if len(content.strip()) < 50:
                continue
            rel = fpath.relative_to(repo_path)
            chunks.append({
                "file":    str(rel),
                "content": content[:4000],  # cap per-file at 4k chars
            })
        except Exception as e:
            log.debug(f"Skip {fpath}: {e}")
    return chunks


def build_darkcodersc_chunks() -> list[dict]:
    """
    Build flat RAG chunk list from all DarkCoderSc repos.
    Each repo gets:
      1. A summary chunk (high-level description + tags)
      2. Per-file source chunks (capped)
    """
    all_chunks = []

    for repo in DARKCODERSC_REPOS:
        repo_path = ROOT_DIR / repo["path"]

        # ── Chunk 1: repo summary ──────────────────────────────────────────
        summary_text = (
            f"REPO: {repo['title']}\n"
            f"CATEGORY: {repo['category']}\n"
            f"TAGS: {', '.join(repo['tags'])}\n\n"
            f"OVERVIEW:\n{repo['summary']}\n\n"
            f"ATTACK TECHNIQUES:\n"
            + "\n".join(f"  • {a}" for a in repo.get("attack_categories", []))
            + f"\n\nDEFENSE / DETECTION:\n{repo.get('defense_notes', '')}"
        )
        if "errz_integration" in repo:
            summary_text += f"\n\nERR0RS INTEGRATION:\n{repo['errz_integration']}"

        all_chunks.append({
            "id":       f"dcs_{repo['id']}_summary",
            "title":    repo["title"],
            "category": repo["category"],
            "tags":     repo["tags"],
            "source":   "darkcodersc",
            "content":  summary_text,
        })

        # ── Chunk 2+: per-file source ──────────────────────────────────────
        file_chunks = _walk_repo_files(repo_path)
        for fc in file_chunks:
            ext   = Path(fc["file"]).suffix.lower()
            lang  = {
                ".pas":"Pascal", ".dpr":"Delphi", ".dfm":"Delphi Form",
                ".cs":"C#", ".ps1":"PowerShell", ".psm1":"PowerShell Module",
                ".iss":"InnoSetup", ".py":"Python",
                ".md":"Markdown", ".txt":"Text", ".json":"JSON",
            }.get(ext, "code")

            chunk_id = f"dcs_{repo['id']}_{hashlib.md5(fc['file'].encode()).hexdigest()[:8]}"
            all_chunks.append({
                "id":       chunk_id,
                "title":    f"{repo['title']} — {fc['file']}",
                "category": repo["category"],
                "tags":     repo["tags"] + [lang.lower(), fc["file"]],
                "source":   "darkcodersc",
                "content":  (
                    f"FILE: {fc['file']} ({lang})\n"
                    f"REPO: {repo['title']}\n\n"
                    f"{fc['content']}"
                ),
            })

        log.info(f"DarkCoderSc: indexed '{repo['id']}' — "
                 f"1 summary + {len(file_chunks)} file chunks")

    log.info(f"DarkCoderSc total chunks: {len(all_chunks)}")
    return all_chunks


# ── Quick-access lookup for ERR0RS natural language triggers ──────────────────

DARKCODERSC_TRIGGERS = {
    # RAT / C2
    "subseven": "dcs_subseven_summary",
    "sub7":     "dcs_subseven_summary",
    "rat architecture": "dcs_subseven_summary",
    "legacy rat": "dcs_subseven_summary",
    "optixgate": "dcs_optixgate_summary",
    "remote access tool": "dcs_optixgate_summary",
    # Shells
    "powershell reverse shell": "dcs_powerremoteshell_summary",
    "powershell bind shell":    "dcs_powerremoteshell_summary",
    "ps reverse shell":         "dcs_powerremoteshell_summary",
    "powerremoteshell":         "dcs_powerremoteshell_summary",
    # Evasion
    "innosetup shellcode": "dcs_inno_shellcode_summary",
    "shellcode loader":    "dcs_inno_shellcode_summary",
    "lolbas installer":    "dcs_inno_shellcode_summary",
    # Windows
    "runas token":       "dcs_run_as_summary",
    "token impersonation": "dcs_run_as_summary",
    "createprocessasuser": "dcs_run_as_summary",
    # Logon
    "winlogon capture":  "dcs_powerremotedesktop_logonui_summary",
    "logonui":           "dcs_powerremotedesktop_logonui_summary",
    "secure desktop":    "dcs_powerremotedesktop_logonui_summary",
}


def get_darkcodersc_summary() -> str:
    """Return a formatted summary of all DarkCoderSc repos for ERR0RS help/info."""
    lines = [
        "=" * 56,
        "  DarkCoderSc (Jean-Pierre LESUEUR) -- KB Integration",
        "  Security & Malware Researcher @ Phrozen",
        "=" * 56,
        "",
    ]
    for repo in DARKCODERSC_REPOS:
        lines.append(f"  [{repo['category'].upper()}] {repo['title']}")
        lines.append(f"    Tags: {', '.join(repo['tags'][:5])}")
        lines.append(f"    Path: {repo['path']}")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    chunks = build_darkcodersc_chunks()
    print(f"\n[OK] Built {len(chunks)} chunks from DarkCoderSc repos")
    print(f"\n{get_darkcodersc_summary()}")
