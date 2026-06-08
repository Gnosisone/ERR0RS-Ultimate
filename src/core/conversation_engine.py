#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║         ERR0RS ULTIMATE — CONVERSATION ENGINE                   ║
║              src/core/conversation_engine.py                    ║
║                                                                  ║
║  Full conversational AI layer for ERR0RS.                       ║
║  Handles:                                                        ║
║    • Cybersecurity Q&A (CIS, OWASP, MITRE ATT&CK, CVEs)        ║
║    • Operation coaching (walk users through attacks step-by-step)║
║    • Concept explanations (any security topic, any depth)        ║
║    • Streaming responses back to WebSocket clients              ║
║    • Conversation history (multi-turn context)                  ║
║    • Operator state awareness (knows current target, findings)  ║
║                                                                  ║
║  Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone       ║
╚══════════════════════════════════════════════════════════════════╝
"""

import json
import threading
import subprocess
import requests
import time
import re
from typing import Optional, Callable, List, Dict


# ── System prompt — ERR0RS full personality + knowledge base ─────────────────
SYSTEM_PROMPT = """You are ERR0RS, the AI core of ERR0RS-Ultimate — an expert penetration testing assistant and cybersecurity coach running locally on a security operator's machine.

## YOUR IDENTITY
You are a senior red team operator and security educator combined. You think like an attacker and explain like a teacher. You are direct, technically precise, and never condescending. You speak to the operator as a peer and teammate, using "we" when planning operations.

## YOUR EXPERTISE
You have deep mastery across:

### Offensive Security
- Penetration testing methodology (reconnaissance, scanning, exploitation, post-exploitation, reporting)
- Web application attacks: SQLi, XSS, CSRF, SSRF, XXE, IDOR, JWT attacks, OAuth flaws, GraphQL injection, deserialization
- Network attacks: MITM, ARP spoofing, DNS poisoning, SMB relay, LLMNR/NBT-NS poisoning, Kerberoasting, AS-REP roasting
- Active Directory: BloodHound, SharpHound, pass-the-hash, pass-the-ticket, DCSync, Golden/Silver tickets, ACL abuse
- Wireless: WPA2 handshake capture, PMKID, evil twin, deauth attacks, WPS exploitation
- Social engineering: phishing, pretexting, vishing, physical security bypass
- Hardware attacks: BadUSB, HID injection, Flipper Zero RF/NFC/IR/Sub-GHz, WiFi Pineapple, Rubber Ducky
- Exploit development fundamentals: buffer overflows, ROP chains, shellcode
- Post-exploitation: lateral movement, persistence, defense evasion, credential harvesting, data exfiltration

### Defensive Security & Compliance
- CIS Controls v8 (all 18 controls — implementation groups IG1/IG2/IG3, specific safeguards)
- NIST Cybersecurity Framework (Identify, Protect, Detect, Respond, Recover)
- OWASP Top 10 2021 (all categories with attack and defense)
- MITRE ATT&CK Framework (tactics, techniques, sub-techniques, mitigations, detections)
- SOC operations: log analysis, SIEM, threat hunting, incident response
- Hardening: CIS Benchmarks, STIGs, secure baseline configs
- Compliance frameworks: PCI-DSS, HIPAA, SOC 2, ISO 27001

### Security Tools
- Metasploit (modules, msfvenom, post modules, evasion)
- Nmap (every flag, NSE scripts, output formats)
- Burp Suite (scanner, repeater, intruder, extensions)
- Wireshark / tcpdump (filters, analysis, IOC hunting)
- SQLmap (all tamper scripts, level/risk, output parsing)
- Nikto, Gobuster, ffuf, feroxbuster (web enumeration)
- Hydra, Medusa, CrackMapExec (credential attacks)
- Hashcat, John the Ripper (hash cracking, rules, masks)
- BloodHound, SharpHound, Impacket (AD attacks)
- Volatility, Autopsy (forensics)
- Suricata, Snort, Zeek (network IDS/IPS)
- Nuclei (template scanning)
- All tools in the Phoenix Arsenal (2,172 BlackArch tools)

## HOW YOU COACH OPERATIONS
When a user asks you to walk them through an operation or attack:
1. Start with a brief strategic overview — what we're doing and why
2. Break it into numbered phases/steps
3. For each step: explain WHAT to do, WHY it works, and show the EXACT command
4. Explain what output to look for and how to interpret it
5. Offer next steps based on what was found
6. Always pair offensive steps with their defensive detection/prevention

Example coaching style:
"Alright, here's how we approach this SQL injection. We have three phases:

**Phase 1 — Confirm the injection point**
We'll test the parameter manually first before throwing sqlmap at it. This tells us what kind of injection we're dealing with...

[command: curl 'http://target/search?q=test%27']

Look for: database error messages, blank responses, or different response lengths..."

## COMMUNICATION STYLE

**Adapt to who you're talking to:**
- If they seem new (asking "what is X" or "how does Y work"), explain from first principles. Use analogies. Be the mentor they couldn't afford.
- If they seem experienced, cut the basics and go deep. Give them the edge cases, the gotchas, the things that trip up even professionals.
- Read the room. If they say "I'm a beginner" — be patient, clear, step-by-step. If they say "just show me the command" — do that.

**How to write:**
- Use "we" when planning ops together — this is a team
- **Bold** key terms, commands, and findings
- Numbered lists for step-by-step procedures (never skip steps)
- Code blocks for every command — always complete, always copyable
- Never give a half-command. If the full command matters, show the full command.

**The WHY matters more than the WHAT:**
Every technique has a reason it works. Explain the underlying mechanism, not just the syntax.
Bad: "Run `sqlmap -u http://target.com`"
Good: "We'll use sqlmap to automate testing the `q` parameter. It works by sending payloads that break out of the SQL context — first single quotes to detect errors, then UNION injections to extract data."

**Tone:**
- Direct. Not rude, but not padded with corporate fluff.
- Say it once and trust them. Don't repeat safety warnings after the first time.
- When you don't know something (very new CVE, obscure edge case), say so honestly — "I'm not sure on that specific version, here's my best guess — verify it."
- Celebrate wins. When they crack something, acknowledge it.

**On ethics:**
- Mention authorization requirements exactly once when relevant, then move on. Don't moralize.
- These are professional security techniques. Treat the operator as a professional.

## BEGINNER COACHING MODE
When the operator is clearly a beginner (level 0-1), add these to every technical response:
1. A "What just happened?" summary in plain English
2. A "What to look for" section — what success looks like in the output
3. A "Next step" suggestion — what to do with what they found
4. A "Why this matters" one-liner connecting it to real security

This is the difference between ERR0RS and Google. Google gives you a command. ERR0RS gives you understanding.

## CURRENT OPERATOR CONTEXT
{operator_context}

## CONVERSATION HISTORY IS PROVIDED ABOVE
Continue naturally from where the conversation left off. Do not repeat greetings.
"""

# ── Conversation history manager ─────────────────────────────────────────────
class ConversationHistory:
    """Thread-safe per-session conversation history."""

    def __init__(self, max_turns: int = 20):
        self._lock     = threading.Lock()
        self._history: List[Dict] = []
        self._max      = max_turns

    def add(self, role: str, content: str):
        with self._lock:
            self._history.append({"role": role, "content": content})
            # Trim to max turns (keep pairs)
            if len(self._history) > self._max * 2:
                self._history = self._history[-(self._max * 2):]

    def get(self) -> List[Dict]:
        with self._lock:
            return list(self._history)

    def clear(self):
        with self._lock:
            self._history = []

    def last_n(self, n: int) -> List[Dict]:
        with self._lock:
            return list(self._history[-n:])


# ── Detect if a message is conversational vs a tool command ─────────────────
# Tool commands are short, imperative, usually start with known keywords
TOOL_KEYWORDS = {
    "nmap", "sqlmap", "nikto", "gobuster", "hydra", "hashcat", "nuclei",
    "amass", "subfinder", "ffuf", "wireshark", "tcpdump", "metasploit",
    "msfconsole", "burp", "dalfox", "enum4linux", "crackmapexec", "cme",
    "bloodhound", "impacket", "volatility", "autopsy", "suricata", "snort",
    "zeek", "aircrack", "wifite", "bettercap", "evilginx", "responder",
    "linpeas", "winpeas", "mimikatz", "rubeus", "certify", "villain",
    "flipper", "badusb", "report", "scan", "target", "autopilot",
    "workflow", "run", "kill", "teach", "help", "status", "devices",
    "solve", "juice-shop",
}

CONVERSATION_INDICATORS = [
    r"^(explain|describe|define|summarize|break down|detail)",  # explicit explain requests
    r"^(how|what|why|when|where|who|can|could|should|would|is|are|do|does|tell|explain)",
    r"(difference between|compare|vs\.?|versus)",
    r"(help me|walk me|guide me|show me|teach me)",
    r"(what is|what are|what does|what's)",
    r"(how do i|how do you|how does|how can)",
    r"(cis control|owasp|mitre|nist|pci|hipaa|soc 2|iso 27001)",
    r"(penetration test|pentest|red team|blue team|purple team)",
    r"(vulnerability|exploit|attack|defense|protect|harden|detect)",
    r"\?$",  # ends with question mark
    r"(step by step|walk me through|coach|guide)",
]

def is_conversational(text: str) -> bool:
    """Returns True if the message should go to the LLM conversation engine."""
    text_lower = text.lower().strip()

    # Very short commands that match tool keywords → not conversational
    words = text_lower.split()
    if words and words[0] in TOOL_KEYWORDS and len(words) <= 4:
        return False

    # Check conversation patterns
    for pattern in CONVERSATION_INDICATORS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True

    # Multi-word natural language (no tool keyword at start, >5 words)
    if len(words) > 5 and words[0] not in TOOL_KEYWORDS:
        return True

    return False


# ── Core conversation engine ─────────────────────────────────────────────────
class ConversationEngine:
    """
    Streaming LLM conversation engine for ERR0RS.
    Uses Ollama HTTP API for proper streaming (not subprocess).
    """

    # Chat model preference order — fastest first for conversation.
    # gemma3:1b promoted to top after 2026-05-20 stress tests proved it's
    # the only local model that reliably completes RAG-augmented teach
    # inference on Pi 5 hardware (TTFT 28.1s on chunked RAG).
    # See docs/STRESS_TESTS/FINDINGS_2026-05-20.md
    CHAT_MODEL_PREFERENCE = [
        "gemma3:1b",         # Pi 5 verified — primary
        "llama3.2:3b",       # fast fallback, decent quality
        "llama3.2:1b",       # very fast fallback when RAM-constrained
        "err0rs-pi5:latest", # custom model
        "qwen2.5-coder:7b",  # quality but slow on Pi (use only on >= 16GB hosts)
    ]

    def __init__(self,
                 model:       str = "gemma3:1b",
                 ollama_host: str = "http://localhost:11434"):
        self.ollama_host = ollama_host
        self._sessions: Dict[str, ConversationHistory] = {}
        self._lock       = threading.Lock()
        # Auto-select fastest available model
        self.model = self._pick_best_model(model)
        # Warm up the selected model in a background thread
        threading.Thread(target=self._warmup, daemon=True).start()

    def _pick_best_model(self, default: str) -> str:
        """Pick the fastest available model from preference list."""
        try:
            resp = requests.get(f"{self.ollama_host}/api/tags", timeout=5)
            if resp.ok:
                available = {m["name"] for m in resp.json().get("models", [])}
                for pref in self.CHAT_MODEL_PREFERENCE:
                    if pref in available:
                        print(f"[ERR0RS ConvEngine] Selected model: {pref}")
                        return pref
        except Exception:
            pass
        return default

    def _warmup(self):
        """Pre-load the model into RAM with a tiny request + keep_alive."""
        try:
            requests.post(
                f"{self.ollama_host}/api/chat",
                json={
                    "model":      self.model,
                    "messages":   [{"role": "user", "content": "ready"}],
                    "stream":     False,
                    "keep_alive": "15m",
                    "options":    {"num_predict": 5},
                },
                timeout=90,
            )
            print(f"[ERR0RS ConvEngine] Model {self.model} warmed up and ready")
        except Exception as e:
            print(f"[ERR0RS ConvEngine] Warmup failed (will retry on first query): {e}")

    def get_session(self, session_id: str) -> ConversationHistory:
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = ConversationHistory()
            return self._sessions[session_id]

    def clear_session(self, session_id: str):
        with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id].clear()

    def build_system_prompt(self, operator_state=None, user_msg: str = "") -> str:
        """Build system prompt with current operator context and teach engine data injected.

        RAG budget discipline (v3.7 Phase 2):
        gemma3:1b's interactive TTFT degrades sharply past ~7K total prompt
        chars (baseline 2026-05-20). The base SYSTEM_PROMPT is ~5.9K, so we
        budget AT MOST ONE RAG block per prompt — ~1-2K chars. Priority order:

          1. PROACTIVE (semantic match on user_msg) wins when user_msg is
             present — they asked a question, that's what they want help
             with now. Even if they just ran a tool, the question is the
             current intent.
          2. REACTIVE (retrieval for last tool run) only fires if proactive
             didn't, or if user_msg is empty (silent operator mode).

        This priority order minimizes the "I asked about X but ERR0RS keeps
        coaching me about the tool I just ran" failure mode.
        """
        ctx_lines = []
        rag_injected = False   # tracks whether any RAG block was added —
                               # prevents overflowing gemma3:1b's interactive budget

        # ── EARLY: try proactive RAG first when user has a question ───────
        # Done BEFORE the operator_state block so it takes priority over
        # the reactive (last-tool-run) injection further down.
        if user_msg and user_msg.strip():
            try:
                from src.ai.rag_retrieval import retrieve_for_query
                rag_block = retrieve_for_query(user_msg, n=2)
                if rag_block:
                    ctx_lines.append(rag_block)
                    rag_injected = True
            except Exception:
                pass
        if operator_state:
            try:
                if hasattr(operator_state, 'target') and operator_state.target:
                    ctx_lines.append(f"- Active target: {operator_state.target}")
                if hasattr(operator_state, 'mode') and operator_state.mode:
                    mode_val = operator_state.mode.value if hasattr(operator_state.mode, 'value') else str(operator_state.mode)
                    ctx_lines.append(f"- Operator mode: {mode_val}")

                # Recent tool runs
                if hasattr(operator_state, 'history') and operator_state.history:
                    recent = list(operator_state.history)[-3:]
                    ctx_lines.append(f"- Tools run this session: {', '.join(r.tool for r in recent)}")

                    last = recent[-1]
                    ctx_lines.append(f"\n### Most Recent Tool Run")
                    ctx_lines.append(f"Command: `{last.command}`")
                    ctx_lines.append(f"Target: {last.target}  |  Exit: {last.returncode}  |  Duration: {last.duration:.1f}s")
                    if last.findings:
                        sev_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵", "info": "⚪"}
                        ctx_lines.append(f"Findings ({len(last.findings)}):")
                        for f in last.findings[:6]:
                            icon = sev_icon.get(f.severity, "•")
                            ctx_lines.append(f"  {icon} [{f.severity}/{f.kind}] {f.value}")
                    else:
                        ctx_lines.append("Findings: none detected")

                    # Pull teach content for the last tool. Skip if proactive
                    # RAG already fired (budget discipline) — but always try
                    # legacy teach_engine as a smaller-cost summary.
                    rag_block = None
                    if not rag_injected:
                        try:
                            from src.ai.rag_retrieval import retrieve_for_tool
                            rag_block = retrieve_for_tool(last.tool, n=2)
                            if rag_block:
                                ctx_lines.append("\n" + rag_block)
                                rag_injected = True
                        except Exception:
                            rag_block = None
                    if not rag_block:
                        try:
                            from src.core import teach_engine
                            lesson = teach_engine.lookup(last.tool)
                            if lesson:
                                ctx_lines.append(f"\n### Teach Engine — {last.tool.upper()}")
                                ctx_lines.append(f"Summary: {lesson['summary']}")
                                ctx_lines.append(f"Typical use: {lesson['typical']}")
                                read_tips = lesson.get('read', [])
                                if read_tips:
                                    ctx_lines.append("How to read output:")
                                    for tip in read_tips[:4]:
                                        ctx_lines.append(f"  • {tip}")
                                next_steps = lesson.get('next', [])
                                if next_steps:
                                    ctx_lines.append(f"Logical next tools: {', '.join(next_steps)}")
                                if lesson.get('caution'):
                                    ctx_lines.append(f"Caution: {lesson['caution']}")
                        except Exception:
                            pass

                # All session findings summary
                if hasattr(operator_state, 'findings') and operator_state.findings:
                    ctx_lines.append(f"\n- Total session findings: {len(operator_state.findings)}")
                    crit = [f for f in operator_state.findings if f.severity in ("critical", "high")]
                    if crit:
                        ctx_lines.append(f"- Critical/High: {len(crit)} — these need immediate follow-up")

            except Exception:
                pass

        # On-demand reference: if the user mentions a tool not recently run,
        # inject context for it. Proactive RAG was already attempted at the
        # top of this method (highest-priority path). This block is the
        # LEGACY teach_engine fallback — broader coverage (any of the ~49
        # hand-written lessons), shallower depth. Fires only if RAG didn't
        # already cover the topic.
        if user_msg and not rag_injected:
            try:
                last_tool = ""
                if operator_state and hasattr(operator_state, 'history') and operator_state.history:
                    last_tool = list(operator_state.history)[-1].tool

                # Per-word lookup using the legacy teach_engine for tools
                # NOT covered by the chunked RAG (the 4,987 unteached tools
                # in the v3 registry, plus any custom mentions). We only
                # inject one such lesson per message to keep token budget
                # bounded.
                from src.core import teach_engine
                for word in re.findall(r'\b\w[\w-]*\b', user_msg.lower()):
                    if word == last_tool:
                        continue  # already covered in tool run section above
                    lesson = teach_engine.lookup(word)
                    if lesson:
                        ctx_lines.append(f"\n### On-Demand Reference — {word.upper()}")
                        ctx_lines.append(f"Summary: {lesson['summary']}")
                        ctx_lines.append(f"Typical: {lesson['typical']}")
                        for tip in lesson.get('read', [])[:3]:
                            ctx_lines.append(f"  • {tip}")
                        next_tools = lesson.get('next', [])
                        if next_tools:
                            ctx_lines.append(f"Next tools: {', '.join(next_tools)}")
                        break  # one lesson per message keeps token count manageable
            except Exception:
                pass

        ctx = "\n".join(ctx_lines) if ctx_lines else "No active engagement — ready to start."
        return SYSTEM_PROMPT.replace("{operator_context}", ctx)

    def inject_tool_context(self, tool: str, command: str, findings: list,
                            session_id: str = "operator_cli"):
        """
        Seed the conversation history after a tool runs so follow-up questions
        ("what does that mean?", "what should I do next?") work naturally.
        Injects as an assistant turn — ERR0RS 'already knows' what happened.
        """
        try:
            from src.core import teach_engine
            lesson = teach_engine.lookup(tool)
        except Exception:
            lesson = None

        sev_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵", "info": "⚪"}
        parts = [f"I just ran `{command}`."]

        if findings:
            parts.append(f"\nFindings ({len(findings)}):")
            for f in findings[:6]:
                icon = sev_icon.get(f.severity, "•")
                parts.append(f"  {icon} [{f.severity}] {f.kind}: {f.value}")
        else:
            parts.append("No notable findings from this run.")

        if lesson:
            parts.append(f"\n**{tool.upper()} — what this tells us:**")
            parts.append(lesson['summary'])
            read_tips = lesson.get('read', [])
            if read_tips:
                parts.append("Key things to understand from this output:")
                for tip in read_tips[:3]:
                    parts.append(f"  • {tip}")
            next_steps = lesson.get('next', [])
            if next_steps:
                parts.append(f"Logical next tools from here: {', '.join(next_steps[:3])}")

        parts.append("\nAsk me anything about what I found, what it means, or what to do next.")

        self.get_session(session_id).add("assistant", "\n".join(parts))

    def chat_stream(self,
                    user_msg:       str,
                    session_id:     str       = "default",
                    operator_state            = None,
                    on_token:       Callable  = None,
                    on_done:        Callable  = None,
                    model:          str       = None,
                    options:        dict      = None):
        """
        Stream a response to user_msg via Ollama HTTP streaming API.

        model   — optional per-call model override (teach mode uses err0rs-qwen
                  while general chat stays on the fast default). None → self.model.
        options — optional per-call Ollama options dict. None → default block.

        on_token(str)  — called for each token as it streams
        on_done(str)   — called once with the complete response
        """
        history = self.get_session(session_id)
        history.add("user", user_msg)

        system = self.build_system_prompt(operator_state, user_msg=user_msg)
        messages = [{"role": "system", "content": system}]
        messages.extend(history.last_n(18))  # last 9 turns

        payload = {
            "model":      model or self.model,
            "messages":   messages,
            "stream":     True,
            "keep_alive": "15m",   # keep model hot in RAM between requests
            "options":    options or {
                "temperature": 0.7,
                "num_predict": 2048,
                "num_ctx":     4096,
                "stop": [],
            }
        }

        full_response = []

        try:
            resp = requests.post(
                f"{self.ollama_host}/api/chat",
                json=payload,
                stream=True,
                timeout=300,
            )
            resp.raise_for_status()

            for line in resp.iter_lines():
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                    token = chunk.get("message", {}).get("content", "")
                    if token:
                        full_response.append(token)
                        if on_token:
                            on_token(token)
                    if chunk.get("done"):
                        break
                except json.JSONDecodeError:
                    continue

        except requests.exceptions.ConnectionError:
            err = "⚠️  Ollama is not running. Start it with: `ollama serve`"
            if on_token:
                on_token(err)
            full_response.append(err)
        except Exception as e:
            err = f"⚠️  LLM error: {str(e)[:200]}"
            if on_token:
                on_token(err)
            full_response.append(err)

        complete = "".join(full_response)
        history.add("assistant", complete)

        # Award XP for engaging with the AI coach
        try:
            from src.core.progression import award_xp
            award_xp("ask_question", user_msg[:60])
        except Exception:
            pass

        if on_done:
            on_done(complete)

        return complete

    def chat_blocking(self,
                      user_msg:       str,
                      session_id:     str = "default",
                      operator_state        = None) -> str:
        """Blocking (non-streaming) chat for fallback use."""
        return self.chat_stream(user_msg, session_id, operator_state)


# ── Global singleton ──────────────────────────────────────────────────────────
_engine: Optional[ConversationEngine] = None

def get_engine(model: str = "gemma3:1b",
               host:  str = "http://localhost:11434") -> ConversationEngine:
    global _engine
    if _engine is None:
        _engine = ConversationEngine(model=model, ollama_host=host)
    return _engine
