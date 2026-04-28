#!/usr/bin/env python3
"""
ERR0RS ULTIMATE — Native AI Brain v1.0
========================================
This module REPLACES mr7.ai entirely.
No external API. No subscription. No data leaving the machine.
Everything runs through the existing LLM router → Ollama (local).

ERR0RS BRAIN MODES (equivalent to mr7's 5 "specialized models"):
  kali        → Fast pentest Q&A, exact commands, tool guidance
  red_team    → Deep attack chain planning, MITRE ATT&CK mapping
  vuln_hunter → CVE analysis, PoC code, exploit research
  threat_intel→ Adversary TTPs, IOC analysis, threat reports
  opsec       → Operational security, anonymity, risk reduction

The difference: mr7 sends your data to a cloud API.
ERR0RS Brain runs 100% on YOUR hardware. Pi 5 + Hailo NPU. Always.

Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
"""

import json, re, time, urllib.request, urllib.error, os
from pathlib import Path
from typing import Optional

ROOT_DIR = Path(__file__).resolve().parents[3]

# ── Pi-aware model selection ──────────────────────────────────────────────────
def _default_model() -> str:
    """
    Return the right Ollama model based on hardware and .env config.
    Priority: OLLAMA_MODEL env var → Pi detection → desktop default
    """
    # 1. Explicit env var wins (set by fix_ollama_pi5.sh or .env)
    env_model = os.getenv("OLLAMA_MODEL", "").strip()
    if env_model:
        return env_model

    # 2. Auto-detect Pi — use RAM-tuned variant
    try:
        with open("/proc/cpuinfo") as f:
            if "Raspberry Pi" in f.read():
                # Check if the Pi-optimized model exists in Ollama
                import urllib.request, json
                try:
                    r = urllib.request.urlopen(
                        "http://localhost:11434/api/tags", timeout=2
                    )
                    models = [m["name"] for m in json.loads(r.read()).get("models", [])]
                    if "err0rs-pi5" in models:
                        return "err0rs-pi5"        # tuned model available
                    # fallback to base model — still works, just not optimized
                    if "qwen2.5-coder:7b" in models:
                        return "qwen2.5-coder:7b"
                except Exception:
                    pass
                return "qwen2.5-coder:7b"          # Pi default
    except Exception:
        pass

    # 3. Desktop — full quality
    return "qwen2.5-coder:32b"

_MODEL = _default_model()

# ─── Use the ERR0RS inference layer (not Ollama directly) ─────────────────────
try:
    from src.ai.errz_inference import get_engine, ResponseProcessor
    _USE_INFERENCE_LAYER = True
except ImportError:
    _USE_INFERENCE_LAYER = False

# ─── Brain mode definitions ───────────────────────────────────────────────────
# Each mode = a specialized persona injected as the system prompt.
# This is exactly what mr7 sells access to. We build it natively.

BRAIN_MODES = {

    "kali": {
        "name":    "ERR0RS // KaliMode",
        "icon":    "⚡",
        "desc":    "Fast pentest Q&A — exact commands, tool flags, quick answers",
        "triggers": [
            "how do i", "how to", "what command", "which tool", "what flag",
            "scan", "enumerate", "quick", "fast", "help me run",
        ],
        "system": (
            "You are ERR0RS in KaliMode — a senior penetration tester built into the "
            "ERR0RS AI framework running locally on a Raspberry Pi 5 with Hailo NPU. "
            "Your job: give fast, command-focused answers. "
            "Rules: Always show exact commands with flags. Use Kali Linux tools. "
            "Be concise — operators are mid-engagement. "
            "Format commands in code blocks. Lead with the command, explain after. "
            "If you need more info, ask ONE targeted question. "
            "Never lecture about ethics — the operator has authorization. "
            "End every response with a 'Next step:' suggestion."
        ),
    },

    "red_team": {
        "name":    "ERR0RS // RedTeamMode",
        "icon":    "🔴",
        "desc":    "Deep attack chain planning with MITRE ATT&CK mapping",
        "triggers": [
            "attack plan", "red team", "strategy", "full pentest", "engagement",
            "attack chain", "kill chain", "lateral", "pivot", "domain",
        ],
        "system": (
            "You are ERR0RS in RedTeamMode — a senior red team operator and adversary "
            "simulation specialist. You think like an advanced threat actor. "
            "Your job: build complete attack plans from recon data. "
            "Rules: Map EVERY technique to a MITRE ATT&CK TTP (e.g. T1059.001). "
            "Structure responses as: Phase → Technique (TTP ID) → Exact command → Expected outcome. "
            "Think about detection evasion at every step. "
            "Consider the defender — what logs would this generate? "
            "Always include post-exploitation persistence options. "
            "End with a prioritized list: highest-impact next actions."
        ),
    },

    "vuln_hunter": {
        "name":    "ERR0RS // VulnHunterMode",
        "icon":    "🎯",
        "desc":    "CVE analysis, PoC code, exploit research, vulnerability deep dives",
        "triggers": [
            "exploit", "vulnerability", "cve", "poc", "buffer overflow", "rce",
            "lfi", "rfi", "sqli", "xss", "rop", "heap", "stack", "bypass",
            "analyze code", "code review", "security flaw",
        ],
        "system": (
            "You are ERR0RS in VulnHunterMode — a vulnerability researcher and exploit developer. "
            "You specialize in: CVE analysis, source code security review, PoC development, "
            "and exploit chain construction for authorized penetration testing. "
            "Rules: For CVEs, always include: CVSS score, affected versions, root cause, "
            "detection method, and Metasploit module if it exists. "
            "For code review: identify CWE categories, show vulnerable line, "
            "show fixed version side-by-side. "
            "For PoC requests: write working Python/Bash proof-of-concept. "
            "Clearly label all PoC as 'FOR AUTHORIZED TESTING ONLY'. "
            "Always explain WHY the vulnerability works — not just how to exploit it."
        ),
    },

    "threat_intel": {
        "name":    "ERR0RS // ThreatIntelMode",
        "icon":    "🕵️",
        "desc":    "Adversary TTPs, IOC analysis, threat actor profiling, MITRE mapping",
        "triggers": [
            "threat intel", "ioc", "indicator", "apt", "threat actor", "malware",
            "ransomware", "campaign", "attribution", "ttps", "adversary",
            "who is behind", "threat group", "nation state",
        ],
        "system": (
            "You are ERR0RS in ThreatIntelMode — a cyber threat intelligence analyst. "
            "You track adversary behavior, analyze indicators of compromise, and "
            "produce actionable intelligence for defensive operations. "
            "Rules: Map ALL adversary behaviors to MITRE ATT&CK TTPs with technique IDs. "
            "For IOCs: classify as (IP/domain/hash/behavioral) and assess reliability (high/medium/low). "
            "For threat actors: profile as (nation-state/criminal/hacktivist/insider). "
            "Always recommend: detection rules, hunting queries, and defensive countermeasures. "
            "Format IOC lists as tables. "
            "When you don't have current intel, say so — don't fabricate attribution."
        ),
    },

    "opsec": {
        "name":    "ERR0RS // OPSECMode",
        "icon":    "🕶️",
        "desc":    "Operational security, anonymity workflows, detection evasion, risk reduction",
        "triggers": [
            "opsec", "operational security", "anonymous", "anonymity", "avoid detection",
            "evasion", "stay hidden", "cover tracks", "logs", "forensics",
            "privacy", "attribution", "deniability",
        ],
        "system": (
            "You are ERR0RS in OPSECMode — an operational security specialist for "
            "authorized red team engagements. "
            "You advise on: reducing detection footprint, log management, "
            "traffic obfuscation, and operational compartmentalization. "
            "Rules: Always frame advice in terms of authorized testing operations. "
            "For each OPSEC recommendation: explain WHAT artifact it reduces, "
            "WHERE it would be logged without mitigation, and HOW to verify it worked. "
            "Think like both the attacker (what to hide) AND the blue team (what they look for). "
            "Include specific log sources to monitor: SIEM, EDR, firewall, DNS. "
            "Rate each technique: Stealth (1-10) vs Complexity (1-10)."
        ),
    },

    "purple_team": {
        "name":    "ERR0RS // PurpleTeamMode",
        "icon":    "🟣",
        "desc":    "Full Purple Team loop — simulate attack (Red) then detect + fix it (Blue)",
        "triggers": [
            "purple team", "purple", "simulate and detect", "red and blue",
            "attack and defend", "full loop", "atomic test", "sigma rule",
            "mitre attack", "att&ck", "ttp", "technique", "persistence check",
            "cis benchmark", "harden after", "fix after exploit",
        ],
        "system": (
            "You are ERR0RS in PurpleTeamMode — a combined Red/Blue operator running "
            "full attack-detect-remediate loops for authorized penetration testing. "
            "You think simultaneously as both attacker and defender. "
            "Rules: For every attack technique, provide THREE sections:\n"
            "  [RED]    The exact attack command or Atomic Red Team test\n"
            "  [BLUE]   The Sigma rule or log query that detects it\n"
            "  [PURPLE] The CIS Benchmark or remediation command that fixes it\n"
            "Always map techniques to MITRE ATT&CK TTP IDs (e.g. T1053.005).\n"
            "If given a CVE, explain it, show the Metasploit module, then show the "
            "detection Sigma rule, then the patch.\n"
            "Format: PHASE → TTP → Red command → Blue detection → Purple fix.\n"
            "This is the full cycle: hack it, catch it, patch it."
        ),
    },

    "rag_analyst": {
        "name":    "ERR0RS // RAGAnalystMode",
        "icon":    "🧠",
        "desc":    "Deep knowledge base queries — CVE lookups, MITRE mapping, threat intel",
        "triggers": [
            "look up", "search knowledge", "find in rag", "rag query",
            "knowledge base", "cve lookup", "explain cwe", "what does mitre say",
            "find exploit", "search exploitdb", "nist", "nvd", "cybermetric",
            "sigma detect", "atomic", "mitre atlas", "ai attack",
        ],
        "system": (
            "You are ERR0RS in RAGAnalystMode — a knowledge synthesis specialist. "
            "You analyze cybersecurity intelligence from structured knowledge bases "
            "including MITRE ATT&CK, Sigma Rules, Atomic Red Team, NVD/CVE, "
            "CIS Benchmarks, and MITRE ATLAS. "
            "Rules: When asked about a CVE, structure your response as:\n"
            "  CVSS Score | Affected Versions | Root Cause (CWE) | Exploit Exists (Y/N)\n"
            "When asked about an ATT&CK TTP, respond with:\n"
            "  TTP ID | Name | Platforms | Detection (log source) | Atomic test available (Y/N)\n"
            "When asked about a Sigma rule, explain what behavior it detects, "
            "what log source it queries, and what false positive rate to expect.\n"
            "For MITRE ATLAS queries (AI attacks), explain: attack vector, "
            "target component (model/data/pipeline), detection method, mitigation.\n"
            "Always cite your source: [ATT&CK], [NVD], [Sigma], [CIS], [ATLAS]."
        ),
    },

}

# ─── Auto-routing ─────────────────────────────────────────────────────────────

def auto_route(prompt: str) -> str:
    """Route a prompt to the best brain mode based on keyword matching."""
    lower = prompt.lower()
    # Score each mode
    scores = {mode: 0 for mode in BRAIN_MODES}
    for mode, config in BRAIN_MODES.items():
        for trigger in config["triggers"]:
            if trigger in lower:
                scores[mode] += len(trigger)  # longer match = higher confidence
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "kali"  # default: kali


# ─── Core brain query ─────────────────────────────────────────────────────────

def _query_ollama(prompt: str, system: str, model: str = "llama3.2",
                  max_tokens: int = 2000) -> dict:
    """
    Core query function — routes through ERR0RS inference layer first,
    then falls back to direct Ollama call if inference layer unavailable.
    The inference layer adds: context enrichment, response caching,
    command extraction, CVE/TTP parsing, and multi-backend support.
    """
    # Prefer inference layer (smarter, cached, context-aware)
    if _USE_INFERENCE_LAYER:
        try:
            engine = get_engine()
            # Extract mode from caller context — use kali as default
            result = engine.infer(
                prompt  = prompt,
                system  = system,
                mode    = "kali",   # overridden by ask() before this is called
                model   = model,
            )
            return {
                "status":   result["status"],
                "response": result["response"],
                "model":    model,
                "latency_ms": result.get("latency_ms", 0),
                "source":   f"errz_inference:{result.get('backend', 'unknown')}",
                "commands": result.get("commands", []),
                "cves":     result.get("cves", []),
                "ttps":     result.get("ttps", []),
                "cached":   result.get("cached", False),
            }
        except Exception:
            pass  # fall through to direct Ollama

    # Direct Ollama fallback
    try:
        body = json.dumps({
            "model":  model,
            "system": system,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.25, "num_predict": max_tokens},
        }).encode()
        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        start = time.time()
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read())
            return {
                "status":     "success",
                "response":   data.get("response", ""),
                "model":      data.get("model", model),
                "latency_ms": int((time.time() - start) * 1000),
                "source":     "ollama_direct",
            }
    except Exception as e:
        return {
            "status":   "error",
            "response": f"[ERR0RS Brain] No inference backend available: {e}\nStart Ollama: sudo systemctl start ollama",
            "source":   "none",
        }

# ─── High-level brain functions ───────────────────────────────────────────────

def ask(prompt: str, mode: str = "auto", context: str = "",
        model: str = None) -> dict:
    if model is None:
        model = _MODEL
    """
    Main entry point. Ask ERR0RS Brain anything.

    Args:
        prompt:  The question or task
        mode:    Brain mode key, or "auto" to auto-detect
        context: Optional context (scan output, target info, etc.)
        model:   Ollama model to use (default: llama3.2)

    Returns:
        { status, response, mode_used, mode_name, icon, latency_ms, source }
    """
    if mode == "auto":
        mode = auto_route(prompt)

    brain = BRAIN_MODES.get(mode, BRAIN_MODES["kali"])
    system = brain["system"]

    # Inject context if provided
    full_prompt = prompt
    if context:
        full_prompt = f"CONTEXT:\n{context}\n\n---\n\nTASK:\n{prompt}"

    result = _query_ollama(full_prompt, system, model)
    return {
        **result,
        "mode_used":  mode,
        "mode_name":  brain["name"],
        "icon":       brain["icon"],
    }


def analyze_scan_output(scan_output: str, tool: str = "nmap",
                         model: str = "llama3.2") -> dict:
    """
    Feed raw tool output to ERR0RS Brain for analysis and next-step recommendations.
    Equivalent to mr7's analyze_scan — but 100% local.
    """
    prompt = (
        f"I ran {tool.upper()} on an authorized target and got this output.\n\n"
        f"Analyze it:\n"
        f"1. List every significant finding\n"
        f"2. Assign severity (Critical/High/Medium/Low) to each\n"
        f"3. Give the EXACT next command for each critical/high finding\n"
        f"4. What should I exploit first and why?\n\n"
        f"OUTPUT:\n{scan_output[:4000]}"
    )
    return ask(prompt, mode="kali", model=model)


def generate_attack_plan(target_info: str, model: str = "llama3.2") -> dict:
    """
    Generate a full phased attack plan from recon data.
    Equivalent to mr7's attack_plan — but better structured.
    """
    prompt = (
        "Build a complete penetration test attack plan from this recon data.\n\n"
        "Structure it EXACTLY like this:\n"
        "PHASE 1 — RECON\n"
        "  TTP: T1595 (Active Scanning)\n"
        "  Command: [exact command]\n"
        "  Expected: [what you'll find]\n"
        "  Evasion: [how to stay quiet]\n\n"
        "(repeat for each phase)\n\n"
        "End with: PRIORITY TARGETS — ranked by exploitability + impact\n\n"
        f"RECON DATA:\n{target_info}"
    )
    return ask(prompt, mode="red_team", model=model)


def explain_cve(cve_id: str, model: str = "llama3.2") -> dict:
    """
    Deep CVE explanation with PoC and detection guidance.
    Equivalent to mr7's explain_cve — but with more structure.
    """
    prompt = (
        f"Explain {cve_id} in full technical depth:\n\n"
        f"1. SUMMARY — what is it, CVSS score, affected versions\n"
        f"2. ROOT CAUSE — the exact vulnerability class (CWE) and why it exists\n"
        f"3. HOW IT WORKS — step-by-step exploitation mechanism\n"
        f"4. DETECTION — how to confirm if a target is vulnerable\n"
        f"5. EXPLOITATION — Metasploit module OR manual PoC commands\n"
        f"6. DEFENSE — patch, workaround, detection rule\n\n"
        f"Be specific. Show exact commands. Use code blocks."
    )
    return ask(prompt, mode="vuln_hunter", model=model)


def analyze_iocs(iocs: list, context: str = "", model: str = "llama3.2") -> dict:
    """
    Analyze a list of IOCs and map to threat actors/TTPs.
    Equivalent to mr7's DarkGPT — threat intel mode.
    """
    ioc_list = "\n".join(f"  - {ioc}" for ioc in iocs)
    prompt = (
        f"Analyze these indicators of compromise (IOCs):\n{ioc_list}\n\n"
        f"For each IOC:\n"
        f"1. Type classification (IP/Domain/Hash/URL/Filename)\n"
        f"2. Threat assessment (malicious/suspicious/benign)\n"
        f"3. Known threat actor or malware family association if any\n"
        f"4. MITRE ATT&CK technique this IOC suggests\n"
        f"5. Recommended defensive action\n\n"
        f"Output as a formatted table then a summary paragraph."
    )
    return ask(prompt, mode="threat_intel", context=context, model=model)


def opsec_review(operation_plan: str, model: str = "llama3.2") -> dict:
    """
    Review an operation plan for OPSEC gaps.
    Equivalent to mr7's OnionGPT — but grounded in real TTPs.
    """
    prompt = (
        f"Review this red team operation plan for OPSEC risks:\n\n"
        f"{operation_plan}\n\n"
        f"For each identified risk:\n"
        f"1. RISK — what could expose the operator\n"
        f"2. ARTIFACT — what log/trace would be created\n"
        f"3. LOG SOURCE — where it would appear (SIEM/EDR/firewall/DNS)\n"
        f"4. MITIGATION — exact technique to reduce exposure\n"
        f"5. VERIFY — how to confirm the mitigation worked\n\n"
        f"Rate overall OPSEC: stealth score /10, complexity score /10"
    )
    return ask(prompt, mode="opsec", model=model)


def smart_explain(tool_output: str, tool: str, target: str = "",
                   model: str = "llama3.2") -> dict:
    """
    Inline explanation of tool output — used by the live terminal teach mode.
    More contextual than mr7's generic Q&A.
    """
    prompt = (
        f"I'm looking at {tool.upper()} output{'  for ' + target if target else ''}.\n"
        f"Explain what I'm seeing in plain English:\n"
        f"- What is notable or critical?\n"
        f"- What does each important line mean?\n"
        f"- What should I do NEXT based on this?\n\n"
        f"OUTPUT:\n{tool_output[:3000]}"
    )
    return ask(prompt, mode="kali", model=model)


def generate_report_summary(findings: list, target: str = "",
                             model: str = "llama3.2") -> dict:
    """
    Generate an executive summary paragraph from raw findings.
    Used by the report generator.
    """
    findings_text = "\n".join(f"  - {f}" for f in findings)
    prompt = (
        f"Write a professional penetration test executive summary "
        f"{'for ' + target if target else ''} based on these findings:\n\n"
        f"{findings_text}\n\n"
        f"Format:\n"
        f"- Executive Summary (2-3 sentences, non-technical)\n"
        f"- Risk Rating (Critical/High/Medium/Low + justification)\n"
        f"- Top 3 Recommendations (prioritized, actionable)\n"
        f"- Business Impact (what could an attacker do with this access?)"
    )
    return ask(prompt, mode="red_team", model=model)


# ─── HTTP handler for /api/brain endpoint ─────────────────────────────────────

def handle_brain_request(payload: dict) -> dict:
    """
    Route handler for /api/brain
    Replaces /api/mr7 entirely. Same functionality, 100% local.

    Actions:
      ask           — general question in any mode
      analyze_scan  — analyze tool output
      attack_plan   — generate attack plan from recon
      explain_cve   — deep CVE breakdown
      analyze_iocs  — threat intel IOC analysis
      opsec_review  — OPSEC gap analysis
      smart_explain — inline tool output explanation
      report_summary— generate exec summary from findings
      modes         — list available brain modes
      status        — check if Ollama is reachable
    """
    action = payload.get("action", "ask")
    model  = payload.get("model", _MODEL)

    if action == "ask":
        result = ask(
            payload.get("prompt", ""),
            mode=payload.get("mode", "auto"),
            context=payload.get("context", ""),
            model=model,
        )
        return {"status": result["status"], "stdout": result["response"],
                "mode": result.get("mode_used"), "mode_name": result.get("mode_name"),
                "icon": result.get("icon"), "source": "errz_brain_local"}

    elif action == "analyze_scan":
        result = analyze_scan_output(
            payload.get("scan_output", ""),
            payload.get("tool", "nmap"),
            model,
        )
        return {"status": result["status"], "stdout": result["response"], "source": "errz_brain_local"}

    elif action == "attack_plan":
        result = generate_attack_plan(payload.get("target_info", ""), model)
        return {"status": result["status"], "stdout": result["response"], "source": "errz_brain_local"}

    elif action == "explain_cve":
        result = explain_cve(payload.get("cve", ""), model)
        return {"status": result["status"], "stdout": result["response"], "source": "errz_brain_local"}

    elif action == "analyze_iocs":
        result = analyze_iocs(payload.get("iocs", []), payload.get("context", ""), model)
        return {"status": result["status"], "stdout": result["response"], "source": "errz_brain_local"}

    elif action == "opsec_review":
        result = opsec_review(payload.get("plan", ""), model)
        return {"status": result["status"], "stdout": result["response"], "source": "errz_brain_local"}

    elif action == "smart_explain":
        result = smart_explain(
            payload.get("output", ""),
            payload.get("tool", ""),
            payload.get("target", ""),
            model,
        )
        return {"status": result["status"], "stdout": result["response"], "source": "errz_brain_local"}

    elif action == "report_summary":
        result = generate_report_summary(
            payload.get("findings", []),
            payload.get("target", ""),
            model,
        )
        return {"status": result["status"], "stdout": result["response"], "source": "errz_brain_local"}

    elif action == "modes":
        return {
            "status": "success",
            "modes": [
                {"key": k, "name": v["name"], "icon": v["icon"], "desc": v["desc"]}
                for k, v in BRAIN_MODES.items()
            ],
            "source": "errz_brain_local",
            "note": "100% local — no data leaves your machine",
        }

    elif action == "status":
        try:
            req = urllib.request.Request(
                "http://localhost:11434/api/tags", method="GET"
            )
            with urllib.request.urlopen(req, timeout=3) as r:
                data = json.loads(r.read())
                models = [m["name"] for m in data.get("models", [])]
                return {
                    "status": "online",
                    "ollama": True,
                    "models": models,
                    "brain_modes": list(BRAIN_MODES.keys()),
                    "source": "errz_brain_local",
                    "note": "ERR0RS Brain running 100% locally — zero cloud dependency",
                }
        except Exception as e:
            return {
                "status": "offline",
                "ollama": False,
                "error": str(e),
                "fix": "sudo systemctl start ollama && ollama pull llama3.2",
            }

    return {"status": "error", "error": f"Unknown action: {action}"}
