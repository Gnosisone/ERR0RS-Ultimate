# src/core/command_router.py
# ERR0RS-Ultimate — Command Router
# Natural language → intent resolution → plugin execution

import re

# ── Intent map: keyword → (plugin_name, command) ────────────────────────────
INTENT_MAP = {
    "scan":         ("nmap_plugin", "scan"),
    "portscan":     ("nmap_plugin", "portscan"),
    "port scan":    ("nmap_plugin", "portscan"),
    "stealth":      ("nmap_plugin", "stealth"),
    "udp":          ("nmap_plugin", "udp"),
    "vuln":         ("nmap_plugin", "vuln"),
    "vulnerabilit": ("nmap_plugin", "vuln"),
    "full scan":    ("nmap_plugin", "full"),
    "subghz":       ("flipper_plugin", "subghz"),
    "badusb":       ("flipper_plugin", "badusb"),
    "nfc":          ("flipper_plugin", "nfc"),
    "infrared":     ("flipper_plugin", "ir"),
    "flipper":      ("flipper_plugin", "status"),
}

_TARGET_RE = re.compile(
    r'\b(?:\d{1,3}\.){3}\d{1,3}(?:/\d+)?\b'
    r'|(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}'
)


def _extract_target(text: str):
    match = _TARGET_RE.search(text)
    return match.group(0) if match else None


def _resolve_intent(text: str):
    lower = text.lower()
    for keyword, mapping in INTENT_MAP.items():
        if keyword in lower:
            return mapping
    return None


class CommandRouter:
    def __init__(self, ai_brain, plugin_manager, interpreter, context=None):
        self.ai_brain       = ai_brain
        self.plugin_manager = plugin_manager
        self.interpreter    = interpreter
        self.context        = context

    def handle_input(self, user_input: str) -> dict:
        # ── Step 1: AI processes input ───────────────────────────
        ai_response = self.ai_brain.process(user_input)
        if "error" in ai_response:
            return ai_response

        ai_text = ai_response.get("result", "")
        reason  = ai_response.get("reason", "")

        # ── Step 2: Extract target ───────────────────────────────
        target = (
            _extract_target(user_input)
            or _extract_target(ai_text)
            or (self.context.get_active_target()
                if self.context else None)
        )
        if self.context and target:
            self.context.set_active_target(target)

        # ── Step 3: Resolve intent → plugin command ──────────────
        intent = _resolve_intent(user_input) or _resolve_intent(ai_text)

        plugin_result = None
        plugin_error  = None

        if intent:
            plugin_name, command = intent
            if not target:
                plugin_error = (
                    f"[Router] Identified '{command}' but no target found. "
                    f"Try: 'scan 192.168.1.1'"
                )
            else:
                args = {"target": target}
                plugin_result = self.plugin_manager.execute(command, args)
                if self.context:
                    self.context.log_action(plugin_name, command, args, plugin_result)
        else:
            plugin_result = ai_text

        # ── Step 4: Interpret output ─────────────────────────────
        raw_output  = plugin_result or plugin_error or ai_text
        suggestions = self.interpreter.analyze_output(raw_output)

        return {
            "result":      raw_output,
            "reason":      reason,
            "intent":      f"{intent[0]}.{intent[1]}" if intent else "ai_only",
            "target":      target,
            "suggestions": suggestions,
            "plugin_ran":  intent is not None and plugin_error is None,
        }
