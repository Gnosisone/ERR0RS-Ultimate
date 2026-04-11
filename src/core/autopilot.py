# src/core/autopilot.py
# ERR0RS-Ultimate — Autonomous Kill Chain AutoPilot
# AI-driven recon → enum → vuln loop with structured JSON decisions

import json
import re
import time

# ── Kill chain stage order ───────────────────────────────────────────────────
KILL_CHAIN = ["scan", "vuln", "portscan", "full"]

ESCALATION_TRIGGERS = {
    "scan":     ["open", "http", "ssh", "ftp", "smb", "443", "80"],
    "vuln":     ["CVE", "VULNERABLE", "exploit", "RCE", "SQLi"],
    "portscan": ["open", "filtered"],
    "full":     [],
}

SYSTEM_PROMPT = """You are ERR0RS-Ultimate, an AI penetration testing assistant.
Analyze scan results and decide the next kill chain action.

Respond ONLY with a valid JSON object — no prose, no markdown, no explanation.

Schema:
{
  "command":    "scan|portscan|stealth|udp|vuln|full|null",
  "target":     "the target IP or hostname",
  "reason":     "one sentence explaining why",
  "confidence": 0.0-1.0,
  "done":       true|false
}

Set "done": true and "command": "null" if no further action is needed.
Never include anything outside the JSON object."""


def _build_prompt(target: str, stage: str, result: str) -> str:
    return (
        f"Target: {target}\n"
        f"Completed stage: {stage}\n\n"
        f"Scan output:\n{result.strip()[:3000]}\n\n"
        f"What is the next best action?"
    )


def _parse_decision(ai_text: str, target: str) -> dict:
    """Safely parse AI JSON. Falls back gracefully if AI returns prose."""
    clean = re.sub(r"```(?:json)?|```", "", ai_text).strip()
    try:
        decision = json.loads(clean)
        assert "command" in decision
        return decision
    except Exception:
        # extract best guess command from prose
        command = None
        for cmd in ["vuln", "full", "portscan", "stealth", "udp", "scan"]:
            if cmd in ai_text.lower():
                command = cmd
                break
        return {
            "command":    command,
            "target":     target,
            "reason":     ai_text[:200],
            "confidence": 0.4,
            "done":       command is None,
        }


def _should_escalate(output: str, stage: str) -> bool:
    triggers = ESCALATION_TRIGGERS.get(stage, [])
    if not triggers:
        return True
    lower = output.lower()
    return any(t.lower() in lower for t in triggers)


class AutoPilot:
    def __init__(self, router, ctx=None, delay: float = 1.0):
        self.router      = router
        self.ctx         = ctx
        self.interpreter = router.interpreter
        self.delay       = delay

    def run(self, target: str, max_steps: int = 5) -> dict:
        print(f"\n  \033[92m🚀 AutoPilot → {target}\033[0m")
        print(f"  Kill chain: {' → '.join(KILL_CHAIN)} | Max steps: {max_steps}\n")
        print("  " + "─" * 60)

        if self.ctx:
            self.ctx.set_active_target(target)

        results   = []
        stage     = "scan"
        step      = 0

        while step < max_steps:
            step += 1
            print(f"\n  \033[96m[Step {step}/{max_steps}]\033[0m "
                  f"Stage: \033[93m{stage}\033[0m → {target}")

            # ── 1. Execute plugin ─────────────────────────────────
            plugin_result = self.router.plugin_manager.execute(
                stage, {"target": target}
            )

            if not plugin_result or plugin_result.startswith("[ERR0RS]"):
                print(f"  \033[91m✗\033[0m {plugin_result}")
                results.append({"step": step, "stage": stage,
                                 "status": "error", "output": plugin_result})
                break

            lines = plugin_result.strip().splitlines()
            for line in lines[:15]:
                print(f"    {line}")
            if len(lines) > 15:
                print(f"    ... ({len(lines)-15} more lines in findings)")

            # ── 2. Interpreter fast-path ──────────────────────────
            next_cmd, itp_reason = self.interpreter.top_command(plugin_result)
            itp_findings = self.interpreter.analyze_output(plugin_result)
            itp_priority = itp_findings[0]["priority"] if itp_findings else 99

            # ── 3. AI structured decision ─────────────────────────
            prompt   = _build_prompt(target, stage, plugin_result)
            ai_raw   = self.router.ai_brain.process(
                prompt, system=SYSTEM_PROMPT
            ).get("result", "")
            decision = _parse_decision(ai_raw, target)

            # Interpreter overrides AI for critical/high findings
            if next_cmd and itp_priority <= 2:
                decision["command"]    = next_cmd
                decision["reason"]     = itp_reason
                decision["confidence"] = 0.95

            print(f"\n  \033[93m🧠\033[0m {decision['reason'][:200]}")
            print(f"  Confidence: {decision.get('confidence', 0):.0%} | "
                  f"Next: \033[92m{decision['command']}\033[0m")

            # Suggestions
            if itp_findings:
                print(f"\n  \033[95m⚡ Findings:\033[0m")
                icons = {1: "🔴", 2: "🟠", 3: "🟡", 4: "⚪"}
                for f in itp_findings[:3]:
                    print(f"    {icons.get(f['priority'],'→')} {f['message']}")

            results.append({
                "step":     step,
                "stage":    stage,
                "status":   "complete",
                "output":   plugin_result,
                "decision": decision,
                "findings": itp_findings,
            })

            if self.ctx:
                self.ctx.log_action("autopilot", stage, {"target": target},
                                    plugin_result)

            # ── 4. Escalate or stop ───────────────────────────────
            next_stage = decision.get("command")

            if decision.get("done") or next_stage in (None, "null"):
                print("\n  \033[92m✓ AutoPilot complete — no further actions.\033[0m")
                break

            if next_stage == stage:
                print(f"\n  ⚠️  Same stage returned — stopping to avoid loop.")
                break

            if not _should_escalate(plugin_result, stage):
                print(f"\n  \033[90m↔ No escalation triggers. Stopping at {stage}.\033[0m")
                break

            stage = next_stage
            print(f"\n  \033[92m↑ Escalating → {stage}\033[0m")
            time.sleep(self.delay)

        # ── Final summary ─────────────────────────────────────────
        print("\n  " + "─" * 60)
        sev = self.interpreter.summary(
            " ".join(r.get("output", "") for r in results)
        )
        print(f"  \033[92m✓ Done\033[0m | {step} steps | {sev}")
        if self.ctx:
            s = self.ctx.summary()
            print(f"  Findings: {s['findings']} | History: {s['history']} entries")

        return {
            "target":  target,
            "steps":   step,
            "results": results,
            "summary": self.ctx.summary() if self.ctx else {},
        }
