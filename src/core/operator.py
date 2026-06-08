"""
ERR0RS Operator Brain
═════════════════════
Central state machine. Every user message flows through here.

Three modes:
  MANUAL — wait for operator after every tool (default)
  AUTO   — chain tools toward a goal without stopping
  PAUSED — auto halted; operator can resume or take over
"""
import time, threading, logging
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any, Callable
from enum import Enum

log = logging.getLogger("err0rs.operator")


class Mode(Enum):
    MANUAL = "manual"
    AUTO   = "auto"
    PAUSED = "paused"


@dataclass
class Finding:
    tool: str
    kind: str
    value: str
    detail: Dict[str, Any] = field(default_factory=dict)
    severity: str = "info"
    timestamp: float = field(default_factory=time.time)


@dataclass
class ToolRun:
    tool: str
    args: List[str]
    target: str
    command: str
    stdout: str = ""
    stderr: str = ""
    returncode: int = -1
    duration: float = 0.0
    success: bool = False
    findings: List[Finding] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


@dataclass
class Suggestion:
    tool: str
    args: List[str]
    reason: str
    confidence: float
    phase: str = "unknown"


@dataclass
class OperatorState:
    mode: Mode = Mode.MANUAL
    target: Optional[str] = None
    goal: Optional[str] = None
    history: List[ToolRun] = field(default_factory=list)
    findings: List[Finding] = field(default_factory=list)
    pending_question: Optional[str] = None
    last_suggestions: List[Suggestion] = field(default_factory=list)
    auto_step_count: int = 0
    auto_max_steps: int = 25
    teach_mode: bool = True
    tool_use_counts: Dict[str, int] = field(default_factory=dict)

    def summary(self) -> Dict[str, Any]:
        return {
            "mode":   self.mode.value,
            "target": self.target,
            "goal":   self.goal,
            "tools_run":  len(self.history),
            "findings":   len(self.findings),
            "waiting_on_user": self.pending_question is not None,
            "auto_step": self.auto_step_count,
            "teach_mode": self.teach_mode,
        }


class Operator:
    """Singleton brain. One instance per ERR0RS process."""
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self.state = OperatorState()
        self._broadcast: Optional[Callable] = None
        self._busy = threading.Lock()
        self._active_learn_session: Optional[str] = None

    @classmethod
    def instance(cls) -> "Operator":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def set_broadcast(self, fn: Callable):
        self._broadcast = fn


    def say(self, msg: str, kind: str = "narrator", extra: Dict = None):
        log.info(f"[{kind}] {msg}")
        if self._broadcast:
            try:
                self._broadcast(kind, msg, extra or {})
            except Exception as e:
                log.warning(f"broadcast failed: {e}")

    def receive(self, user_msg: str) -> Dict[str, Any]:
        """Main entrypoint — user types something, figure out what to do."""
        from src.core import intent_parser
        user_msg = (user_msg or "").strip()
        if not user_msg:
            return {"status": "empty", "reply": "Say something, operator."}

        if self.state.pending_question:
            q = self.state.pending_question
            self.state.pending_question = None
            return self._handle_answer(q, user_msg)

        # Learn trigger — the launcher Learn button (or a typed "learn <tool>")
        # opens a LIVE, conversation-grounded lesson on the err0rs-qwen teaching
        # model. Intercepted before intent parsing so it never gets misrouted.
        _low = user_msg.lower().strip()
        if _low == "learn" or _low.startswith("learn "):
            return self._learn(user_msg[5:].strip() or None)

        intent = intent_parser.parse(user_msg, state=self.state)
        log.info(f"Intent: {intent}")
        action = intent.get("action")

        if action == "set_target":
            self.state.target = intent["target"]
            self.say(f"🎯 Target locked: {self.state.target}", "narrator")
            return {"status": "ok", "reply": f"Target set to {self.state.target}"}


        if action == "set_mode":
            self.state.mode = Mode(intent["mode"])
            self.say(f"Mode → {self.state.mode.value.upper()}", "narrator")
            return {"status": "ok", "reply": f"Mode = {self.state.mode.value}"}

        if action == "start_auto":
            return self._start_auto(intent.get("goal","full_chain"),
                                    intent.get("target") or self.state.target)

        if action == "pause":
            self.state.mode = Mode.PAUSED
            self.say("⏸ Auto paused. Type 'resume' to continue.", "narrator")
            return {"status": "paused", "reply": "Paused."}

        if action == "resume":
            if self.state.mode == Mode.PAUSED:
                self.state.mode = Mode.AUTO
                self.say("▶ Resuming auto mode...", "narrator")
                threading.Thread(target=self._auto_loop, daemon=True).start()
                return {"status": "resumed", "reply": "Resumed"}
            return {"status": "noop", "reply": "Not paused"}

        if action == "status":
            return {"status": "ok", "reply": "State report",
                    "state": self.state.summary()}

        if action == "teach":
            return self._teach(intent.get("topic"))

        if action == "next_lesson":
            return self._next_lesson()

        if action == "report":
            return self._generate_report()

        if action == "juice_shop":
            return self._juice_shop(intent.get("sub","all"),
                                    intent.get("challenge"))


        if action == "run_tool":
            return self._run_tool(
                tool=intent["tool"],
                args=intent.get("args", []),
                target=intent.get("target") or self.state.target,
                reason=intent.get("reason", ""),
            )

        if action == "ask_user":
            self.state.pending_question = intent.get("question_key", "unknown")
            q = intent.get("question", "Can you clarify?")
            self.say(f"🤔 {q}", "narrator")
            return {"status": "question", "reply": q}

        if action == "chat":
            return self._chat(user_msg)

        return {"status": "unknown",
                "reply": "Try: 'nmap 192.168.1.1', 'set target 10.0.0.5', 'auto full chain', or 'teach nmap'"}

    def _run_tool(self, tool, args, target, reason=""):
        """Execute tool via OperatorTerminal + phoenix_bridge, analyze, suggest."""
        from src.core import output_analyzer, next_step_engine
        from src.core.live_terminal import build_command, get_operator_terminal
        from src.core.phoenix_bridge import run_tool as phoenix_run

        # Running a tool exits any active Learn session → back to operator chat.
        self._active_learn_session = None

        if not target and tool not in ("msfconsole","update"):
            self.state.pending_question = "need_target"
            q = f"I need a target for {tool}. IP, CIDR, hostname, or URL?"
            self.say(q, "narrator")
            return {"status": "question", "reply": q}

        # ── Persist target into operator state ─────────────────────────────
        # Bug from live test: each tool run extracted target from the intent
        # parser but never wrote it back to self.state.target. Result: the
        # next_step_engine and LLM prompts all saw target=null even after
        # nmap had clearly been run against localhost. Persisting here means
        # subsequent suggestions, replays, and auto-chains all share the
        # same target context until the user changes it.
        if target:
            self.state.target = target


        if not args:
            cmd_str = build_command(tool, target)
            parts = cmd_str.split()
            args = parts[1:] if parts and parts[0] == tool else parts
        else:
            cmd_str = f"{tool} " + " ".join(str(a) for a in args)

        if reason:
            self.say(f"💡 {reason}", "narrator")
        self.say(f"▶ Running: {cmd_str}", "narrator",
                 {"tool": tool, "target": target})

        # Spawn in OperatorTerminal xterm on desktop
        try:
            op_term = get_operator_terminal()
            op_term.ensure_alive()
            op_term.send_command(cmd_str, tool=tool, announce=True)
        except Exception as e:
            log.warning(f"OperatorTerminal spawn failed: {e}")

        # Execute via phoenix_bridge
        # Per-tool timeout — most tools finish in <60s; sqlmap/nikto need longer
        tool_timeouts = {
            "sqlmap": 600, "nikto": 180, "nmap": 300, "nuclei": 240,
            "gobuster": 180, "ffuf": 180, "wpscan": 180, "hydra": 600,
            "metasploit": 900, "dalfox": 120, "whatweb": 60,
        }
        tool_timeout = tool_timeouts.get(tool, 180)
        run = ToolRun(tool=tool, args=[str(a) for a in args],
                      target=target or "", command=cmd_str)
        try:
            result = phoenix_run(tool, args, timeout=tool_timeout)
            run.stdout, run.stderr = result.stdout, result.stderr
            run.returncode, run.duration = result.returncode, result.duration
            run.success = result.success
        except Exception as e:
            run.stderr = str(e)
            log.error(f"{tool} crashed: {e}")


        findings = output_analyzer.analyze(tool, run.stdout, target=target)
        run.findings = findings
        self.state.findings.extend(findings)
        self.state.history.append(run)

        icon = "✅" if run.success else "⚠️"
        self.say(f"{icon} {tool} rc={run.returncode} in {run.duration:.1f}s",
                 "narrator", {"tool": tool, "success": run.success})

        if findings:
            self.say(f"📋 {len(findings)} items of interest:", "narrator")
            for f in findings[:8]:
                sev_icon = {"critical":"🔴","high":"🟠","medium":"🟡",
                            "low":"🔵","info":"⚪"}.get(f.severity, "•")
                self.say(f"  {sev_icon} [{f.kind}] {f.value}", "intel",
                         {"kind": f.kind, "severity": f.severity})

        # ── Award XP for the tool run ────────────────────────────────────────
        # Critical: this path (Operator Brain → phoenix_run) was previously
        # bypassing the XP/tools_used counter entirely. Every nmap, nikto,
        # gobuster, sqlmap etc. invoked through the Brain (which is most of
        # them — mission stepper, kill chain, suggestion-card clicks all
        # route here) added zero to "Tools Used" and zero domain XP.
        # The tool_executor.py path was the only one awarding correctly,
        # but the Brain doesn't use it.
        #
        # award_xp("run_<tool>") increments tools_used[<tool>] in
        # progression.py:170, fires achievement checks (recon_master at 10
        # nmaps, web_hunter at 5 sqlmaps, etc.), and updates skill domain XP.
        # found_vuln/found_creds add bonus XP when findings are present.
        try:
            from src.core.progression import award_xp
            if run.success:
                award_xp(f"run_{tool}", target or "")
                if findings:
                    award_xp("found_vuln", f"{tool}: {len(findings)} findings")
        except Exception as _xpe:
            # XP failures must NEVER block tool execution flow
            log.warning(f"award_xp failed for {tool}: {_xpe}")

        # ── Target-down detection: coach instead of hanging the LLM ──────────
        # When a tool can't reach the target (Juice Shop not started, wrong
        # port, service down), the raw output is just "Unable to connect" and
        # the LLM next-step suggester would spend ~30-45s trying to reason
        # about an empty result set. A SOC mentor recognizes "your target
        # isn't up" instantly and tells the student how to fix it — then
        # SKIPS the pointless LLM call. This is the constitution in action:
        # teach the fix, don't dump a raw error.
        _out_low = (run.stdout + " " + run.stderr).lower()
        _conn_fail_markers = (
            "unable to connect", "connection refused", "failed to connect",
            "could not connect", "no route to host", "connection timed out",
            "couldn't connect to server", "name or service not known",
        )
        if any(m in _out_low for m in _conn_fail_markers):
            tgt = target or "the target"
            self.say(f"🎯 {tool} couldn't reach {tgt} — the target isn't responding.",
                     "narrator")
            # Tailored guidance for the Juice Shop lab (the default mission target)
            if "3000" in str(tgt) or "localhost" in str(tgt) or "juice" in str(tgt).lower():
                self.say("   This usually means OWASP Juice Shop isn't running yet.",
                         "narrator")
                self.say("   Start the lab, then re-run this step:", "narrator")
                self.say("     bash scripts/start_lab.sh", "suggestion",
                         {"tool": "shell", "args": ["bash", "scripts/start_lab.sh"],
                          "confidence": 0.95,
                          "reason": "Start OWASP Juice Shop + lab targets"})
                self.say("   Or directly with Docker:", "narrator")
                self.say("     docker run -d -p 3000:3000 bkimminich/juice-shop",
                         "suggestion",
                         {"tool": "shell",
                          "args": ["docker","run","-d","-p","3000:3000","bkimminich/juice-shop"],
                          "confidence": 0.9,
                          "reason": "Launch Juice Shop container directly"})
                self.say("   Give it ~20-30s to boot, confirm with: curl -s localhost:3000 | head",
                         "narrator")
            else:
                self.say(f"   Check: is the service up? Is {tgt} the right host/port?",
                         "narrator")
                self.say("   Verify reachability first with: nmap -p <port> <host>",
                         "narrator")
            # Record the run, award nothing extra, and return WITHOUT the
            # expensive LLM next-step call — there's nothing to suggest until
            # the target is reachable.
            return {
                "status": "target_down",
                "reply": f"{tool} could not reach {tgt} — target appears down",
                "tool": tool, "returncode": run.returncode, "duration": run.duration,
                "findings":    [asdict(f) for f in findings],
                "suggestions": [],
                "coaching": "target_unreachable",
            }

        suggestions = next_step_engine.suggest(
            tool=tool, findings=findings, state=self.state,
        )
        self.state.last_suggestions = suggestions

        if suggestions:
            self.say("➡  Next best steps:", "narrator")
            for i, s in enumerate(suggestions[:4], 1):
                self.say(f"  {i}. [{s.tool}] {s.reason}", "suggestion",
                         {"tool": s.tool, "args": s.args,
                          "confidence": s.confidence, "reason": s.reason})

        # Seed conversation engine so follow-up questions about this run work in context
        try:
            from src.core.conversation_engine import get_engine
            get_engine().inject_tool_context(
                tool=tool, command=cmd_str, findings=findings,
                session_id="operator_cli",
            )
        except Exception as _te:
            log.debug(f"teach context inject skipped: {_te}")

        # Teach mode — Socratic question or quiz depending on use count
        self.state.tool_use_counts[tool] = self.state.tool_use_counts.get(tool, 0) + 1
        if self.state.teach_mode and self._broadcast:
            use_count = self.state.tool_use_counts[tool]
            if use_count == 3:
                threading.Thread(target=self._quiz, args=(tool,), daemon=True).start()
            else:
                threading.Thread(target=self._socratic_question,
                                 args=(tool, findings), daemon=True).start()

        return {
            "status": "ok",
            "reply": f"{tool} done — {len(findings)} findings",
            "tool": tool, "returncode": run.returncode, "duration": run.duration,
            "findings":    [asdict(f) for f in findings],
            "suggestions": [asdict(s) for s in suggestions],
        }


    def _start_auto(self, goal, target):
        if not target:
            self.state.pending_question = "need_target_auto"
            self.state.goal = goal
            q = "Auto mode needs a target. What should I go after?"
            self.say(q, "narrator")
            return {"status": "question", "reply": q}
        self.state.target = target
        self.state.goal = goal
        self.state.mode = Mode.AUTO
        self.state.auto_step_count = 0
        self.say(f"🔥 AUTO MODE — target={target} goal={goal}", "narrator")
        threading.Thread(target=self._auto_loop, daemon=True).start()
        return {"status": "auto_started",
                "reply": f"Auto chain started against {target}"}

    def _auto_loop(self):
        from src.core import next_step_engine
        while (self.state.mode == Mode.AUTO
               and self.state.auto_step_count < self.state.auto_max_steps):
            self.state.auto_step_count += 1
            step = self.state.auto_step_count

            if not self.state.history:
                next_action = next_step_engine.first_step(self.state.target, self.state.goal)
            else:
                sugs = next_step_engine.suggest(
                    tool=self.state.history[-1].tool,
                    findings=self.state.history[-1].findings,
                    state=self.state,
                )
                next_action = sugs[0] if sugs else None


            if not next_action:
                self.say("✅ Auto chain complete — no more suggested steps", "narrator")
                self.state.mode = Mode.MANUAL
                break

            self.say(f"🤖 [AUTO {step}] → {next_action.tool}: {next_action.reason}",
                     "narrator", {"step": step})
            self._run_tool(next_action.tool, next_action.args,
                           self.state.target, next_action.reason)

            if next_step_engine.goal_reached(self.state):
                self.say(f"🏁 Goal '{self.state.goal}' reached in {step} steps!",
                         "narrator")
                self.state.mode = Mode.MANUAL
                self._generate_report()
                break

        if self.state.auto_step_count >= self.state.auto_max_steps:
            self.say(f"⏹ Auto max steps ({self.state.auto_max_steps}) reached",
                     "narrator")
            self.state.mode = Mode.MANUAL
            self._generate_report()

    def _handle_answer(self, question_key, answer):
        if question_key in ("need_target", "need_target_auto"):
            self.state.target = answer.strip()
            self.say(f"🎯 Target locked: {self.state.target}", "narrator")
            if question_key == "need_target_auto":
                return self._start_auto(self.state.goal or "full_chain",
                                        self.state.target)
            return {"status": "ok",
                    "reply": f"Target = {self.state.target}. What tool?"}
        return {"status": "ok", "reply": f"Noted: {answer}"}


    def _teach(self, topic):
        from src.core import teach_engine
        if not topic:
            topics = ", ".join(sorted(teach_engine.LESSONS.keys()))
            msg = f"📖 What do you want to learn? Try: {topics}"
            self.say(msg, "narrator")
            return {"status": "ok", "reply": msg}
        lesson_text = teach_engine.format_lesson(topic)
        # NOTE: we intentionally do NOT broadcast the lesson line-by-line over
        # the narrator WS channel anymore. Doing so caused two field bugs:
        #   1. RACE: when the lesson was triggered by opening the live terminal
        #      (e.g. the "Continue Lessons" button), the WS subscriber wasn't
        #      connected yet, so the broadcast lines were emitted to nothing —
        #      the lesson "printed" only to the launcher's stdout, never the
        #      xterm the student was looking at.
        #   2. DOUBLE-PRINT: when the WS *was* connected, the lesson rendered
        #      twice (once per line via narrator, plus the HTTP reply).
        # The full lesson is returned synchronously in the HTTP response below
        # as `lesson`; the frontend renders it straight into the live terminal,
        # which has no race and no duplication. A single short narrator ping
        # keeps the intel feed informed without spamming the terminal.
        self.say(f"📖 Lesson: {topic}", "narrator")

        # ── Mark the lesson as completed ────────────────────────────────────
        # The user has now SEEN the lesson — that's "completion" for our
        # progress tracker. Without this, Continue Lessons just stockpiles
        # "started" topics forever and never advances the X/23 counter on
        # the skill panel. mark_lesson is idempotent (re-firing is a no-op),
        # so re-running 'teach <topic>' for review is safe.
        try:
            from src.core.operator_profile import mark_lesson
            mark_lesson(topic, "completed")
            # Award lesson XP. progression.py has 'lesson_completed' = 15 XP
            # mapped to whatever skill domain the topic belongs to.
            # progression.XP_AWARDS has 'complete_lesson' at 30 XP — use that
            # canonical event name so the XP fires correctly.
            from src.core.progression import award_xp
            award_xp("complete_lesson", topic)
        except Exception as _le:
            # Lesson tracking must NEVER block the user seeing the lesson
            pass

        # Summary return for HTTP caller
        first_line = lesson_text.splitlines()[0] if lesson_text else "no lesson"
        return {"status": "ok", "reply": first_line, "lesson": lesson_text,
                "topic": topic, "kind": "lesson"}

    def _next_lesson(self):
        """Advance the teaching flow: teach the next unread topic.

        Backs the 'next'/'continue' command and the live-terminal Continue
        button. Uses the same next-unread selection as the skill panel so the
        X/N progress counter stays consistent across both entry points.
        """
        topic = None
        try:
            from src.core.operator_profile import get_lesson_state
            ls = get_lesson_state()
            topic = ls.get("next_unread")
        except Exception as _le:
            log.debug(f"next_lesson state lookup failed: {_le}")
        if not topic:
            # Either everything is done, or state is unavailable — fall back
            # to the first topic the user hasn't obviously seen. If lessons
            # are all complete, celebrate rather than erroring.
            msg = "🎓 All lessons complete — you've covered every topic. Type 'teach <topic>' to review any of them."
            self.say(msg, "narrator")
            return {"status": "ok", "reply": msg, "all_complete": True}
        return self._teach(topic)

    def _juice_shop(self, sub, challenge_id=None):
        """Handle Juice Shop CTF commands."""
        from src.core import juice_shop_solver as js
        base = self.state.target or "http://localhost:3000"
        if not base.startswith("http"):
            base = f"http://{base}"

        if sub == "list":
            chs = js.list_challenges()
            self.say(f"📋 {len(chs)} Juice Shop challenges available:", "narrator")
            for c in chs:
                stars = "★" * c["stars"]
                self.say(f"  {stars:6s} [{c['id']:20s}] {c['name']:30s} — {c['category']}",
                         "narrator")
            return {"status":"ok","reply":f"{len(chs)} challenges",
                    "challenges": chs}

        if sub == "status":
            st = js.status()
            solved = list(st.get("solved", {}).keys())
            self.say(f"🏆 {len(solved)} solved / {len(js.CHALLENGES)} total", "narrator")
            for cid, info in st.get("solved",{}).items():
                self.say(f"  ✅ {cid}: {info.get('detail','')[:70]}", "narrator")
            return {"status":"ok","reply":f"{len(solved)} solved",
                    "state": st}

        if sub == "all":
            self.say(f"🎯 Solving ALL Juice Shop challenges against {base}...",
                     "narrator")
            result = js.solve_all(base=base)
            self.say(f"🏁 Done — {result['solved']}/{result['total']} solved "
                     f"({result['pct']}%)", "narrator")
            for r in result["results"]:
                icon = "✅" if r["status"] == "ok" else "❌"
                stars = "★" * r["stars"]
                self.say(f"  {icon} {stars:6s} [{r['id']:20s}] {r['detail'][:80]}",
                         "narrator" if r['status']=='ok' else "intel",
                         {"challenge": r["id"], "success": r["status"]=="ok"})
                if r["status"] == "ok":
                    self.state.findings.append(Finding(
                        tool="juice-shop", kind="challenge_solved",
                        value=f"[{r['stars']}★ {r['category']}] {r['name']}: {r['detail'][:100]}",
                        detail={"id": r["id"], "category": r["category"], "stars": r["stars"]},
                        severity="critical" if r["stars"] >= 4 else
                                 "high" if r["stars"] >= 3 else "medium",
                    ))
            return {"status":"ok", "reply":f"{result['solved']}/{result['total']} solved",
                    "summary": result}

        if challenge_id:
            r = js.solve(challenge_id, base=base)
            icon = "✅" if r["status"] == "ok" else "❌"
            stars = "★" * r.get("stars",0)
            self.say(f"{icon} [{r.get('id','?')}] {r.get('name','?')} {stars} — {r.get('detail','')[:100]}",
                     "narrator")
            if r["status"] == "ok":
                self.state.findings.append(Finding(
                    tool="juice-shop", kind="challenge_solved",
                    value=f"[{r.get('stars',0)}★] {r.get('name','?')}: {r.get('detail','')[:100]}",
                    detail={"id": r.get("id"), "category": r.get("category")},
                    severity="critical" if r.get("stars",0) >= 4 else "high",
                ))
            return r
        return {"status":"error","reply":"Usage: solve juice-shop [all|<id>] or juice-shop list/status"}

    def _learn(self, tool):
        """Open a LIVE, conversation-grounded lesson on a tool.

        Unlike _teach() (which prints a static lesson into the terminal), this
        seeds the err0rs-qwen teaching persona with a mentor prompt, streams the
        reply as chat bubbles, and keeps the per-tool session open so the student
        can ask follow-ups back-and-forth. Lesson + RAG context are auto-injected
        by conversation_engine.build_system_prompt().
        """
        from src.core import teach_engine
        from src.core.conversation_engine import get_engine
        if not tool:
            topics = ", ".join(sorted(teach_engine.LESSONS.keys()))
            msg = f"📖 What do you want to learn? Try: {topics}"
            self.say(msg, "narrator")
            return {"status": "ok", "reply": msg}

        tool = tool.strip().lower()
        session_id = f"learn_{tool}"
        self._active_learn_session = session_id
        self.say(f"🎓 Live lesson on {tool} — ask me anything when it's done", "narrator")

        seed = (
            f"I want to learn how to use `{tool}` for authorized penetration testing "
            f"in my own lab. Teach me like a patient mentor: a short friendly intro to "
            f"what {tool} is and why it matters, one or two real example commands each "
            f"with a one-line explanation, the defensive/detection angle, then invite me "
            f"to ask follow-up questions. Keep it concise and beginner-friendly."
        )
        # Stress test (docs/STRESS_TESTS/FINDINGS_2026-05-20.md) proved gemma3:1b
        # is the ONLY local model that completes RAG-grounded teach inference on
        # Pi 5 CPU within wall-clock — 7B/3B hard-timeout. So teach uses the
        # default warmed model, grounded by RAG, not a heavier persona model.
        if self._broadcast:
            def _tok(t):  self._broadcast("chat_token", t, {})
            def _done(_): self._broadcast("chat_done",  "", {})
            get_engine().chat_stream(seed, session_id, self.state,
                                     on_token=_tok, on_done=_done)
            return {"status": "streaming", "session": session_id, "topic": tool}
        reply = get_engine().chat_blocking(seed, session_id, self.state)
        return {"status": "ok", "reply": reply, "topic": tool}

    def _chat(self, msg):
        """Routes question through conversation engine, streaming tokens as chat bubbles.

        When a Learn session is active, follow-ups continue in that per-tool
        session (coherent thread) — but stay on the default gemma3:1b model,
        the only one viable for RAG teach inference on Pi 5 CPU. General chat
        uses the operator_cli session.
        """
        # Keep the per-tool session for coherent follow-ups; default model.
        session = self._active_learn_session or "operator_cli"
        try:
            from src.core.conversation_engine import get_engine
            engine = get_engine()
            if self._broadcast:
                def _tok(t):  self._broadcast("chat_token", t, {})
                def _done(_): self._broadcast("chat_done",  "", {})
                engine.chat_stream(msg, session, self.state,
                                   on_token=_tok, on_done=_done)
                return {"status": "streaming"}
            else:
                reply = engine.chat_blocking(msg, session, self.state)
                if not reply:
                    reply = "Ready. Ask me about any security topic, CIS control, or type 'help'."
                return {"status": "ok", "reply": reply}
        except Exception as _e:
            err = f"LLM unavailable ({_e}). Make sure Ollama is running: ollama serve"
            if self._broadcast:
                self._broadcast("chat_token", err, {})
                self._broadcast("chat_done",  "", {})
                return {"status": "streaming"}
            return {"status": "error", "reply": err}

    def _socratic_question(self, tool: str, findings: list):
        """After a tool run in teach mode, broadcast one probing question via WS."""
        if not self._broadcast:
            return
        try:
            from src.core import teach_engine
            from src.core.conversation_engine import get_engine
            lesson = teach_engine.lookup(tool) or {}
            sev_icons = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵", "info": "⚪"}
            findings_txt = (
                "Findings: " + ", ".join(
                    f"{sev_icons.get(f.severity,'•')}{f.kind}:{f.value}" for f in findings[:3]
                ) if findings else "no notable findings"
            )
            prompt = (
                f"The operator just ran `{tool}` against `{self.state.target or 'the target'}`. "
                f"{findings_txt}. "
                "You are in teach mode. Ask ONE concise probing question that tests their understanding "
                "of what was found or what this tool reveals. Make it thought-provoking, not trivial. "
                "Start your response with '🎓 ' then the question only — no preamble, no answer."
            )
            engine = get_engine()
            def _tok(t): self._broadcast("chat_token", t, {})
            def _done(_): self._broadcast("chat_done", "", {})
            engine.chat_stream(prompt, "teach_session", self.state, on_token=_tok, on_done=_done)
        except Exception as e:
            log.debug(f"Socratic question failed: {e}")

    def _quiz(self, tool: str):
        """After a tool is used 3 times, broadcast a 3-question knowledge quiz."""
        if not self._broadcast:
            return
        try:
            from src.core import teach_engine
            from src.core.conversation_engine import get_engine
            lesson = teach_engine.lookup(tool) or {}
            flags_str = "; ".join(
                f"{k} ({v[:50]})" for k, v in list(lesson.get("flags", {}).items())[:4]
            )
            read_tips = "; ".join(lesson.get("read", [])[:2])
            prompt = (
                f"The operator has now run {tool} 3 times — time for a checkpoint quiz! "
                f"Generate exactly 3 numbered questions testing their knowledge of {tool}. "
                f"Base questions on: summary='{lesson.get('summary','')}'; "
                f"key flags='{flags_str}'; reading output='{read_tips}'. "
                f"After each question include the correct answer on a new line starting with 'Answer:'. "
                f"Start with: '🧪 {tool.upper()} CHECKPOINT — you've run this 3 times, let's see what stuck:\n'"
            )
            engine = get_engine()
            def _tok(t): self._broadcast("chat_token", t, {})
            def _done(_): self._broadcast("chat_done", "", {})
            engine.chat_stream(prompt, f"quiz_{tool}", None, on_token=_tok, on_done=_done)
        except Exception as e:
            log.debug(f"Quiz failed: {e}")

    def _generate_report(self):
        """Generate HTML pentest report from current state."""
        from src.core import report_gen
        try:
            path = report_gen.generate(self.state, output_dir="/tmp")
            msg = f"📄 Report generated → {path}"
            self.say(msg, "narrator", {"report_path": path})
            try:
                import subprocess, os as _os
                _env = {**_os.environ, "DISPLAY": _os.environ.get("DISPLAY", ":0")}
                subprocess.Popen(["xdg-open", path], env=_env,
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL,
                                 start_new_session=True)
            except Exception:
                pass
            return {"status": "ok", "reply": msg, "report_path": path}
        except Exception as e:
            log.error(f"Report generation failed: {e}", exc_info=True)
            err = f"❌ Report failed: {e}"
            self.say(err, "narrator")
            return {"status": "error", "reply": err}


def get_operator() -> Operator:
    return Operator.instance()
