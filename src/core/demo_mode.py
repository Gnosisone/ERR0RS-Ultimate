#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║         ERR0RS ULTIMATE — DEMO MODE                             ║
║              src/core/demo_mode.py                              ║
║                                                                  ║
║  Self-contained demonstration that runs without a lab.          ║
║  Shows every major ERR0RS capability against safe local         ║
║  targets (localhost only, no external network access).          ║
║                                                                  ║
║  Invoke: python3 src/ui/errorz_launcher.py --demo               ║
║       or: bash scripts/demo.sh                                  ║
║                                                                  ║
║  Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone       ║
╚══════════════════════════════════════════════════════════════════╝
"""

import time
import threading
import json
from typing import Callable, Optional

# ── Demo script — what ERR0RS says and does in sequence ──────────────────────
DEMO_SCRIPT = [
    {
        "type": "narrate",
        "delay": 0.5,
        "text": "ERR0RS-Ultimate v3.2.0 — Demo Mode Active",
    },
    {
        "type": "narrate",
        "delay": 0.3,
        "text": "Running against localhost only. No external network access.",
    },

    # ── Phase 1: Show the conversation engine ─────────────────────────────────
    {
        "type": "section",
        "delay": 1.0,
        "title": "PHASE 1 — AI COACHING",
    },
    {
        "type": "user_input",
        "delay": 0.5,
        "text": "explain sql injection",
    },
    {
        "type": "ai_response",
        "delay": 0.3,
        "text": """SQL injection is one of the oldest vulnerabilities in existence — and still in OWASP's Top 10 in 2021 because it's still everywhere.

**What's happening:** When user input is concatenated directly into a SQL query, an attacker can "inject" their own SQL to change what the query does.

**Example — vulnerable code:**
```python
query = "SELECT * FROM users WHERE username = '" + username + "'"
```

If you enter `admin'--` as the username, the query becomes:
```sql
SELECT * FROM users WHERE username = 'admin'--'
```
The `--` comments out the rest — including the password check. You're logged in as admin without knowing the password.

**The full attack chain:**
1. Find an injectable parameter (URL param, form field, header)
2. Confirm injection with `'` or `1=1` or `1=2`
3. Determine injection type: UNION, Boolean-blind, Time-based
4. Extract: database names → tables → columns → data
5. Check for FILE privilege → OS shell potential

**Defensive fix:** Parameterized queries (prepared statements). Always. One line of code eliminates the entire class.

**Try it:** `sqlmap -u 'http://localhost:3000/rest/products/search?q=1' --dbs --batch`
""",
    },

    # ── Phase 2: Show tool execution + auto coach ─────────────────────────────
    {
        "type": "section",
        "delay": 1.5,
        "title": "PHASE 2 — TOOL EXECUTION + AUTO COACH",
    },
    {
        "type": "user_input",
        "delay": 0.5,
        "text": "nmap -sV localhost",
    },
    {
        "type": "tool_output",
        "delay": 0.1,
        "lines": [
            "Starting Nmap 7.94 ( https://nmap.org ) at 2026-04-26",
            "Nmap scan report for localhost (127.0.0.1)",
            "Host is up (0.000047s latency).",
            "",
            "PORT     STATE SERVICE VERSION",
            "22/tcp   open  ssh     OpenSSH 9.7p1 Debian",
            "80/tcp   open  http    Apache httpd 2.4.62",
            "3000/tcp open  http    Node.js (Express middleware)",
            "8765/tcp open  http    ERR0RS Web UI",
            "11434/tcp open  http   Ollama REST API",
            "",
            "Service detection performed. Please report any incorrect results.",
            "Nmap done: 1 IP address (1 host up) scanned in 3.24 seconds",
        ],
    },
    {
        "type": "coach_block",
        "delay": 0.5,
        "severity": "info",
        "heading": "LOCALHOST SCAN COMPLETE — Services Mapped",
        "explain": (
            "We can see 5 services running on localhost. Port 3000 (Node.js/Express) "
            "is the OWASP Juice Shop — that's our practice target. Port 8765 is ERR0RS itself. "
            "In a real engagement, each open port is a potential attack vector."
        ),
        "next_steps": [
            ("nikto -h http://localhost:3000", "Web vulnerability scan of Juice Shop"),
            ("gobuster dir -u http://localhost:3000 -w /usr/share/wordlists/dirb/common.txt", "Find hidden directories"),
            ("curl -s http://localhost:3000/api/Challenges | python3 -m json.tool | head -50", "List Juice Shop challenges"),
        ],
        "defense": "Every open port is attack surface. Close what you don't need. Version details help attackers — use version-hiding in production.",
    },

    # ── Phase 3: Show the progression system ─────────────────────────────────
    {
        "type": "section",
        "delay": 1.5,
        "title": "PHASE 3 — OPERATOR PROGRESSION",
    },
    {
        "type": "narrate",
        "delay": 0.3,
        "text": "Awarding XP for demo session...",
    },
    {
        "type": "xp_toast",
        "delay": 0.5,
        "xp": 30,
        "level_up": False,
        "message": "+30 XP — Recon complete",
    },
    {
        "type": "narrate",
        "delay": 0.3,
        "text": "Operator level: APPRENTICE (130/500 XP to PRACTITIONER)",
    },

    # ── Phase 4: Teach engine ─────────────────────────────────────────────────
    {
        "type": "section",
        "delay": 1.5,
        "title": "PHASE 4 — OFFLINE CURRICULUM",
    },
    {
        "type": "user_input",
        "delay": 0.5,
        "text": "teach me nmap",
    },
    {
        "type": "lesson_preview",
        "delay": 0.3,
        "topic": "nmap",
        "preview": (
            "NMAP — Network scanner, maps hosts, ports, services, and vulnerabilities\n"
            "Typical: nmap -sV -sC -p- 192.168.1.100\n\n"
            "Key flags: -sV (version detection), -sC (default scripts), -p- (all ports),\n"
            "           -A (aggressive), -sS (stealth SYN), --script (NSE modules)\n\n"
            "Reading output: 'open' = investigate. Service version = search for CVEs.\n"
            "VULNERABLE in NSE output = confirmed finding, escalate immediately.\n\n"
            "Next steps: nikto (web), enum4linux (SMB), hydra (credential attack)"
        ),
    },

    # ── Phase 5: Report ───────────────────────────────────────────────────────
    {
        "type": "section",
        "delay": 1.5,
        "title": "PHASE 5 — PROFESSIONAL REPORTING",
    },
    {
        "type": "narrate",
        "delay": 0.3,
        "text": "Generating demonstration report...",
    },
    {
        "type": "report_preview",
        "delay": 0.5,
        "content": (
            "ENGAGEMENT REPORT — ERR0RS DEMO\n"
            "Generated: 2026-04-26\n"
            "Target: localhost (demo mode)\n\n"
            "EXECUTIVE SUMMARY\n"
            "The demonstration engagement identified 5 services running on the target host.\n"
            "No critical vulnerabilities were identified in demo scope (localhost).\n"
            "OWASP Juice Shop (port 3000) represents an intentionally vulnerable\n"
            "application suitable for security training and tool validation.\n\n"
            "FINDINGS: 0 Critical | 0 High | 1 Medium | 3 Info\n\n"
            "MEDIUM: Port 80 running Apache — version disclosure in Server header\n"
            "INFO: 5 services identified on localhost\n"
            "INFO: Juice Shop practice target available on port 3000\n"
            "INFO: ERR0RS platform operational on port 8765\n\n"
            "RECOMMENDATIONS\n"
            "1. Start Juice Shop lab: bash scripts/start_lab.sh\n"
            "2. Begin guided mission: type 'target http://localhost:3000'\n"
            "3. Run full scan: nmap -sV -sC localhost\n"
        ),
    },

    # ── End ───────────────────────────────────────────────────────────────────
    {
        "type": "section",
        "delay": 1.5,
        "title": "DEMO COMPLETE",
    },
    {
        "type": "narrate",
        "delay": 0.3,
        "text": "ERR0RS-Ultimate demo complete. This is what every engagement looks like.",
    },
    {
        "type": "narrate",
        "delay": 0.3,
        "text": "To start the full lab: bash scripts/start_lab.sh",
    },
    {
        "type": "narrate",
        "delay": 0.3,
        "text": "To explore: http://127.0.0.1:8765",
    },
]


class DemoRunner:
    """Runs the ERR0RS demo sequence, broadcasting events via callback."""

    def __init__(self, broadcast_fn: Callable, speed: float = 1.0):
        self.broadcast = broadcast_fn
        self.speed     = speed  # 0.5 = double speed, 2.0 = half speed
        self._running  = False

    def run(self):
        """Execute the full demo sequence in a background thread."""
        self._running = True
        t = threading.Thread(target=self._execute, daemon=True)
        t.start()
        return t

    def stop(self):
        self._running = False

    def _execute(self):
        for step in DEMO_SCRIPT:
            if not self._running:
                break

            delay = step.get("delay", 0.5) * self.speed
            time.sleep(delay)

            stype = step["type"]

            if stype == "narrate":
                self.broadcast({"type": "system", "data": f"[ERR0RS] {step['text']}"})

            elif stype == "section":
                self.broadcast({"type": "system", "data": f"\n{'═'*54}"})
                self.broadcast({"type": "system", "data": f"  {step['title']}"})
                self.broadcast({"type": "system", "data": f"{'═'*54}\n"})

            elif stype == "user_input":
                self.broadcast({"type": "input_echo", "data": f"ERR0RS@demo:~$ {step['text']}"})

            elif stype == "tool_output":
                for line in step["lines"]:
                    if not self._running:
                        break
                    self.broadcast({"type": "output", "data": line})
                    time.sleep(0.05 * self.speed)

            elif stype == "ai_response":
                # Stream the AI response token by token
                text = step["text"]
                self.broadcast({"type": "system", "data": "[ERR0RS] 🧠 llama3.2:3b — generating..."})
                words = text.split()
                chunk = []
                for word in words:
                    if not self._running:
                        break
                    chunk.append(word)
                    if len(chunk) >= 8 or word.endswith("\n"):
                        self.broadcast({"type": "chat_token", "data": " ".join(chunk) + " "})
                        chunk = []
                        time.sleep(0.04 * self.speed)
                if chunk:
                    self.broadcast({"type": "chat_token", "data": " ".join(chunk)})
                self.broadcast({"type": "chat_done", "data": ""})

            elif stype == "coach_block":
                self.broadcast({
                    "type":   "coach",
                    "data":   _format_coach_text(step),
                    "result": {
                        "heading":    step["heading"],
                        "explain":    step["explain"],
                        "severity":   step["severity"],
                        "next_steps": [{"command": c, "label": l} for c, l in step["next_steps"]],
                        "defense":    step["defense"],
                        "xp_event":   None,
                        "finding_count": 1,
                    },
                    "tool": "nmap",
                })

            elif stype == "xp_toast":
                # Award real XP to the progression system
                try:
                    from src.core.progression import award_xp
                    award_xp("complete_recon", "demo mode")
                except Exception:
                    pass
                self.broadcast({
                    "type": "xp_award",
                    "data": json.dumps({
                        "xp_gained": step["xp"],
                        "level_up":  step["level_up"],
                        "message":   step["message"],
                    }),
                })

            elif stype == "lesson_preview":
                self.broadcast({"type": "output", "data": "\n" + "═"*54})
                self.broadcast({"type": "output", "data": f"📖 {step['topic'].upper()} LESSON PREVIEW"})
                self.broadcast({"type": "output", "data": "─"*54})
                for line in step["preview"].split("\n"):
                    self.broadcast({"type": "output", "data": line})
                self.broadcast({"type": "output", "data": "═"*54 + "\n"})

            elif stype == "report_preview":
                self.broadcast({"type": "output", "data": "\n" + "═"*54})
                self.broadcast({"type": "output", "data": "📄 REPORT PREVIEW"})
                self.broadcast({"type": "output", "data": "─"*54})
                for line in step["content"].split("\n"):
                    self.broadcast({"type": "output", "data": line})
                self.broadcast({"type": "output", "data": "═"*54 + "\n"})

        self._running = False


def _format_coach_text(step: dict) -> str:
    """Format a demo coach step as terminal text."""
    lines = [
        f"\n{'═'*60}",
        f"⚪ ERR0RS ANALYSIS: {step['heading']}",
        f"{'─'*60}",
    ]
    if step.get("explain"):
        lines.append(f"\n📋 WHAT THIS MEANS:\n{step['explain']}\n")
    if step.get("next_steps"):
        lines.append("⚡ NEXT STEPS:")
        for i, (cmd, label) in enumerate(step["next_steps"], 1):
            lines.append(f"  {i}. [{label}]\n     $ {cmd}")
    if step.get("defense"):
        lines.append(f"\n🛡️  DEFENSE: {step['defense']}")
    lines.append(f"{'═'*60}\n")
    return "\n".join(lines)


# ── Module-level runner used by errorz_launcher.py --demo flag ───────────────
_demo_runner: Optional[DemoRunner] = None

def start_demo(broadcast_fn: Callable, speed: float = 1.0) -> DemoRunner:
    global _demo_runner
    _demo_runner = DemoRunner(broadcast_fn, speed)
    _demo_runner.run()
    return _demo_runner

def stop_demo():
    global _demo_runner
    if _demo_runner:
        _demo_runner.stop()
        _demo_runner = None
