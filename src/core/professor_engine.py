"""
ERR0RS Professor Engine
========================
Real-time AI security coach. Subscribes to engagement events, decides when
to speak, formulates explanations using cached templates + LLM + RAG.

Three modes share the same engine:
  1. Live narration (during 'err0rs own <target> --professor')
  2. Brainstorm (standalone Q&A via 'err0rs brainstorm')
  3. Coach (during 'err0rs lesson <N>')

Architecture:
-------------
    +-----------------+      +-----------------+      +-----------------+
    | AutoKillChain   |--->  | ProfessorEngine |--->  | LiveNarrator    |
    | (events)        |      | - decision      |      | (terminal+WS+   |
    +-----------------+      | - cached resp   |      |  log)           |
                             | - LLM fallback  |      +-----------------+
    +-----------------+      | - RAG citation  |
    | UserProfile     |--->  | - profile-aware |
    | (verbosity)     |      |                 |
    +-----------------+      +-----------------+
                                    ^
    +-----------------+             |
    | User Question   |-------------+
    | (via WebSocket) |
    +-----------------+

The engine is thread-safe. Live narration runs sync (called from kill chain
threads), user questions run via async event loop hooked to the WebSocket
endpoint. They share a lock around ConversationEngine session state.

LLM Budget on Pi 5 (~38s warm per response):
  - phase_start, tool_start, tool_skip:  CACHED — instant, zero LLM calls
  - finding_emitted (1st of kind):       LLM if novel, cached if seen before
  - finding_emitted (Nth of same kind):  CACHED short version
  - user_question:                       LLM (always)
  - risky_action_proposed:               CACHED + parameter substitution
  - lesson_section:                      LLM with RAG citations

Result: 5-15 LLM calls per typical 15-min engagement. Budget OK.

Author: Gary Holden Schneider (Eros) | Sprint 04 Workstream A
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional


# ── Event types (closed enum) ──────────────────────────────────────────────

class EventType(str, Enum):
    """The set of events the professor can react to. Closed enum on purpose."""
    PHASE_START          = "phase_start"
    PHASE_END            = "phase_end"
    TOOL_START           = "tool_start"
    TOOL_END             = "tool_end"
    TOOL_SKIP            = "tool_skip"
    FINDING              = "finding"
    RISKY_ACTION         = "risky_action_proposed"
    USER_QUESTION        = "user_question"
    LESSON_SECTION       = "lesson_section"
    BRAINSTORM_TURN      = "brainstorm_turn"


@dataclass
class ProfessorEvent:
    """An event the professor may react to."""
    type:        EventType
    payload:     dict = field(default_factory=dict)
    timestamp:   str  = ""
    engagement_id: Optional[str] = None

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        # Coerce string to enum if needed
        if isinstance(self.type, str):
            self.type = EventType(self.type)


@dataclass
class Utterance:
    """What the professor says about an event."""
    text:        str
    event_type:  EventType
    source:      str       # "cache" | "llm" | "rag+llm" | "template"
    citations:   list      = field(default_factory=list)   # [{source, passage_id}]
    cached:      bool      = False
    duration_ms: int       = 0


@dataclass
class SpeakDecision:
    """Outcome of should_speak() — yes/no plus reasoning."""
    should:    bool
    verbosity: str       = "brief"   # silent | brief | normal | verbose
    reason:    str       = ""
    template:  Optional[str] = None  # if cached template applies


# ── Cached canned explanations ────────────────────────────────────────────
# These fire INSTANTLY (no LLM) for predictable events. The {placeholders}
# get filled in at runtime from event payload.
#
# Keep these professional — they appear in real engagement transcripts.

CANNED_EXPLANATIONS = {
    # ── Phase narration ───────────────────────────────────────────────
    EventType.PHASE_START: {
        "recon": {
            "novice":       ("Starting Phase 1 — Reconnaissance. We're gathering "
                              "intel about the target before touching it. Tools: {tools}. "
                              "This phase is read-only — we're listening, not attacking yet."),
            "intermediate": ("Phase 1 (Recon): {tools}. MITRE TA0043. Read-only enumeration."),
            "expert":       ("Recon. {tools}."),
        },
        "scanning": {
            "novice":       ("Phase 2 — Scanning. Now we probe the services we found. "
                              "Tools: {tools}. We're identifying versions and behaviors so "
                              "the next phase can match them to known vulnerabilities."),
            "intermediate": ("Phase 2 (Scanning): {tools}. Service fingerprinting + dir bust."),
            "expert":       ("Scan. {tools}."),
        },
        "vuln_assessment": {
            "novice":       ("Phase 3 — Vulnerability Assessment. This is where our native "
                              "engines fire: jwt_breaker scans for tokens, nosql_injector "
                              "probes for Mongo/GraphQL, template_injector checks for SSTI. "
                              "Tools: {tools}."),
            "intermediate": ("Phase 3 (Vuln assessment): {tools}. Native engines + nuclei."),
            "expert":       ("VA. {tools}."),
        },
        "exploitation": {
            "novice":       ("Phase 4 — Exploitation. We deliver the payloads built in Phase 3. "
                              "Read-only exploits run automatically (file reads, info disclosure). "
                              "Anything destructive needs your approval. Tools: {tools}."),
            "intermediate": ("Phase 4 (Exploit): {tools}. Read-only auto, destructive gated."),
            "expert":       ("Exploit. {tools}."),
        },
        "post_exploitation": {
            "novice":       ("Phase 5 — Post-Exploitation. With access established, we look "
                              "for credentials, lateral pivots, and persistence opportunities. "
                              "Tools: {tools}."),
            "intermediate": ("Phase 5 (Post-exploit): {tools}. Cred harvest + pivot recon."),
            "expert":       ("Post. {tools}."),
        },
        "lateral_movement": {
            "novice":       ("Phase 6 — Lateral Movement. We use harvested credentials to "
                              "access additional systems. Tools: {tools}. This is where one "
                              "compromise becomes a full network breach."),
            "intermediate": ("Phase 6 (Lateral): {tools}. Cred reuse + pivot."),
            "expert":       ("Lat-mov. {tools}."),
        },
        "reporting": {
            "novice":       ("Phase 7 — Reporting. Generating the findings document with "
                              "MITRE mappings, CVSS scores, and remediation guidance. "
                              "Tools: {tools}."),
            "intermediate": ("Phase 7 (Report): {tools}. MITRE+CVSS formatted output."),
            "expert":       ("Report. {tools}."),
        },
    },

    # ── Tool dispatch narration ───────────────────────────────────────
    EventType.TOOL_START: {
        "default": {
            "novice":       "Running {tool} now. {tool_purpose}",
            "intermediate": "▶ {tool}",
            "expert":       "▶ {tool}",   # expert sees the same — terminal already shows it
        },
    },

    EventType.TOOL_SKIP: {
        "default": {
            "novice":       ("Skipping {tool} — it's not installed on this system. "
                              "Install it later with: {install_hint}. Continuing with "
                              "the rest of the phase."),
            "intermediate": "Skip {tool} (not installed; {install_hint} to add).",
            "expert":       "Skip {tool} (n/a).",
        },
    },

    # ── Phase wrap-up ─────────────────────────────────────────────────
    EventType.PHASE_END: {
        "default": {
            "novice":       ("Phase complete: {phase}. Ran {tools_run} tools, "
                              "produced {findings} findings in {duration_s}s."),
            "intermediate": "Phase {phase}: {tools_run} tools, {findings} findings, {duration_s}s.",
            "expert":       "{phase}: {tools_run}t/{findings}f/{duration_s}s.",
        },
    },
}


# Tool-purpose mini-descriptions for novice TOOL_START narration.
# Kept short — full explanations come from LLM if the user asks.
TOOL_PURPOSES = {
    "nmap_discovery":      "scans for open ports + service versions",
    "nmap_deep":           "deep port scan with vulnerability scripts",
    "nmap_vuln_scripts":   "runs nmap's NSE vulnerability scripts",
    "subfinder":           "enumerates subdomains via passive DNS",
    "theHarvester":        "harvests emails + subdomains from public sources",
    "gobuster":            "brute-forces directories and virtual hosts",
    "ffuf":                "fast web fuzzing for hidden paths and parameters",
    "nuclei":              "runs templated CVE / misconfiguration checks",
    "nuclei_cve":          "runs nuclei templates filtered to CVEs",
    "nikto":               "scans web servers for known issues",
    "enum4linux":          "enumerates SMB shares + users",
    "searchsploit":        "looks up exploits in Exploit-DB by service version",
    "metasploit_auto":     "auto-runs Metasploit modules matched to findings",
    "sqlmap":              "tests for SQL injection across endpoints",
    "hydra":               "brute-forces login credentials",
    "msf_post_suggester":  "suggests post-exploitation modules from session info",
    "msf_hashdump":        "dumps password hashes from a compromised host",
    "msf_enum":            "enumerates the post-compromise environment",
    "crackmapexec_sweep":  "sweeps SMB/WinRM with credentials looking for reuse",
    "psexec_spray":        "tests psexec across hosts using captured creds",
    "ssh_key_sweep":       "tests SSH keys against discovered hosts",
    "pro_reporter":        "generates the final engagement report",
    "jwt_breaker":         "ERR0RS native: attacks JWTs with 5+ techniques",
    "nosql_injector":      "ERR0RS native: NoSQL injection + GraphQL probes",
    "template_injector":   "ERR0RS native: SSTI + prototype pollution chains",
}


# Tool install hints for TOOL_SKIP
TOOL_INSTALL_HINTS = {
    "nmap_discovery":      "apt install nmap",
    "nmap_deep":           "apt install nmap",
    "nmap_vuln_scripts":   "apt install nmap",
    "subfinder":           "apt install subfinder OR github.com/projectdiscovery/subfinder",
    "theHarvester":        "apt install theharvester",
    "gobuster":            "apt install gobuster",
    "ffuf":                "apt install ffuf",
    "nuclei":              "apt install nuclei OR github.com/projectdiscovery/nuclei",
    "nuclei_cve":          "apt install nuclei",
    "nikto":               "apt install nikto",
    "enum4linux":          "apt install enum4linux",
    "searchsploit":        "apt install exploitdb",
    "metasploit_auto":     "apt install metasploit-framework",
    "sqlmap":              "apt install sqlmap",
    "hydra":               "apt install hydra",
    "crackmapexec_sweep":  "pipx install crackmapexec",
}


# ── ProfessorEngine ───────────────────────────────────────────────────────

class ProfessorEngine:
    """
    Coordinates cached templates + LLM + RAG to produce real-time
    coaching utterances. Thread-safe; safe to call from kill chain
    threads and async user-question handlers concurrently.
    """

    def __init__(self,
                 *,
                 profile,                              # UserProfile
                 conversation_engine = None,           # ConversationEngine | None (lazy)
                 narrator            = None,           # Narrator | None
                 rag_retriever       = None,           # RagRetriever | None (Sprint 04+)
                 enable_llm:    bool = True):
        """
        profile: UserProfile instance — drives verbosity decisions
        conversation_engine: ConversationEngine; lazily loaded if None
        narrator: Narrator instance; if provided, utterances auto-broadcast
        rag_retriever: optional RAG layer for citations (lazy stub for now)
        enable_llm: if False, ProfessorEngine never calls the LLM (test-friendly)
        """
        self.profile        = profile
        self._conv_engine   = conversation_engine
        self._narrator      = narrator
        self._rag           = rag_retriever
        self.enable_llm     = enable_llm
        self._lock          = threading.Lock()
        self._session_id    = "professor"   # ConversationEngine session key
        self._llm_calls     = 0
        self._cache_hits    = 0

    # ── Conversation engine lazy loader ──────────────────────────────

    def _conv(self):
        """Lazy-load ConversationEngine — avoids cost when LLM disabled."""
        if not self.enable_llm:
            return None
        with self._lock:
            if self._conv_engine is None:
                from src.core.conversation_engine import get_engine
                self._conv_engine = get_engine()
            return self._conv_engine

    # ── Stats ────────────────────────────────────────────────────────

    @property
    def stats(self) -> dict:
        return {
            "llm_calls":  self._llm_calls,
            "cache_hits": self._cache_hits,
        }

    # ── Decision: should we speak about this event? ───────────────────

    def should_speak(self, event: ProfessorEvent) -> SpeakDecision:
        """
        Adaptive verbosity decision. Returns SpeakDecision describing
        whether to speak and at what verbosity.
        """
        level = self.profile.experience_level

        # ALWAYS speak about user questions and risky actions
        if event.type == EventType.USER_QUESTION:
            return SpeakDecision(should=True, verbosity="verbose",
                                 reason="user explicitly asked")
        if event.type == EventType.RISKY_ACTION:
            return SpeakDecision(should=True, verbosity="verbose",
                                 reason="risky action requires explicit explanation")
        if event.type == EventType.BRAINSTORM_TURN:
            return SpeakDecision(should=True, verbosity="verbose",
                                 reason="brainstorm turns are pure dialogue")
        if event.type == EventType.LESSON_SECTION:
            return SpeakDecision(should=True, verbosity="normal",
                                 reason="lesson sections are coaching content")

        # Phase boundaries — always speak, but verbosity adapts to level
        if event.type == EventType.PHASE_START:
            return SpeakDecision(should=True,
                                 verbosity={"novice": "verbose",
                                             "intermediate": "normal",
                                             "expert": "brief"}[level],
                                 reason="phase boundaries always announced")

        if event.type == EventType.PHASE_END:
            # Expert: silent on phase end (no value)
            if level == "expert":
                return SpeakDecision(should=False, reason="expert: phase summary in stdout already")
            return SpeakDecision(should=True,
                                 verbosity="brief",
                                 reason="brief phase summary")

        # Tool start — only speak for novices, and only if concept is novel
        if event.type == EventType.TOOL_START:
            tool = event.payload.get("tool", "")
            if level == "expert":
                return SpeakDecision(should=False, reason="expert: stdout shows tool name")
            if level == "intermediate":
                return SpeakDecision(should=False, reason="intermediate: stdout sufficient")
            # Novice
            if self.profile.has_mastered(f"tool_{tool}"):
                return SpeakDecision(should=False, reason=f"already mastered: {tool}")
            if self.profile.has_seen(f"tool_{tool}"):
                return SpeakDecision(should=False, reason=f"recently explained: {tool}")
            return SpeakDecision(should=True, verbosity="brief",
                                 reason=f"novice + first time seeing {tool}")

        # Tool skip — explain to novices what they're missing
        if event.type == EventType.TOOL_SKIP:
            if level == "expert":
                return SpeakDecision(should=False)
            return SpeakDecision(should=True, verbosity="brief")

        # Tool end — silent unless something meaningful happened
        if event.type == EventType.TOOL_END:
            findings = event.payload.get("findings", 0)
            if findings == 0:
                return SpeakDecision(should=False, reason="no findings, no narration needed")
            # Findings > 0 — defer to FINDING event for the actual content
            return SpeakDecision(should=False, reason="findings narrate via FINDING events")

        # Findings — adaptive based on severity AND novelty
        if event.type == EventType.FINDING:
            severity = event.payload.get("severity", "info")
            tech     = event.payload.get("technique", "")

            # Critical findings: always speak, verbose
            if severity == "critical":
                return SpeakDecision(should=True, verbosity="verbose",
                                     reason="critical finding")
            # High findings: always speak, normal verbosity
            if severity == "high":
                return SpeakDecision(should=True, verbosity="normal")
            # Medium findings: speak unless mastered concept
            if severity == "medium":
                if tech and self.profile.has_mastered(f"finding_{tech}"):
                    return SpeakDecision(should=False, reason=f"mastered: {tech}")
                return SpeakDecision(should=True, verbosity="brief")
            # Low / info findings: novice only, and only if novel
            if level == "expert":
                return SpeakDecision(should=False)
            if level == "intermediate":
                return SpeakDecision(should=False)
            # Novice + low/info
            if tech and self.profile.has_seen(f"finding_{tech}"):
                return SpeakDecision(should=False, reason=f"recently seen: {tech}")
            return SpeakDecision(should=True, verbosity="brief")

        # Default: silent
        return SpeakDecision(should=False, reason=f"no rule for {event.type.value}")

    # ── Cached template lookup ───────────────────────────────────────

    def _try_cached(self, event: ProfessorEvent, decision: SpeakDecision) -> Optional[Utterance]:
        """
        Try to satisfy this event from cached templates.
        Returns Utterance or None if no template applies.
        """
        templates_for_type = CANNED_EXPLANATIONS.get(event.type)
        if not templates_for_type:
            return None

        # Choose template by event payload's "key" (e.g. phase_id / tool_id)
        key = self._template_key(event)
        template_set = templates_for_type.get(key) or templates_for_type.get("default")
        if not template_set:
            return None

        level = self.profile.experience_level
        template = template_set.get(level) or template_set.get("novice")
        if not template:
            return None

        try:
            text = self._fill_template(template, event)
        except KeyError:
            # Template needs a field the payload doesn't have — bail to LLM
            return None

        # Apply vocab adaptation
        text = self.profile.adapt_text(text)

        self._cache_hits += 1
        return Utterance(
            text=text,
            event_type=event.type,
            source="cache",
            cached=True,
            duration_ms=0,
        )

    @staticmethod
    def _template_key(event: ProfessorEvent) -> str:
        """Pick the template subkey based on event type + payload."""
        if event.type == EventType.PHASE_START:
            return event.payload.get("phase", "default")
        if event.type in (EventType.TOOL_START, EventType.TOOL_SKIP):
            # Tool-specific templates exist for some tools but most use default
            return "default"
        return "default"

    @staticmethod
    def _fill_template(template: str, event: ProfessorEvent) -> str:
        """
        Fill {placeholders} from event.payload. Adds derived fields like
        tool_purpose/install_hint based on the payload.
        """
        ctx = dict(event.payload)
        # Pretty-format tools list
        if "tools" in ctx and isinstance(ctx["tools"], (list, tuple)):
            ctx["tools"] = ", ".join(ctx["tools"])
        # Tool purpose for TOOL_START
        if "tool" in ctx:
            ctx.setdefault("tool_purpose", TOOL_PURPOSES.get(ctx["tool"],
                                                              "running this tool"))
            ctx.setdefault("install_hint", TOOL_INSTALL_HINTS.get(ctx["tool"],
                                                                    "consult tool docs"))
        return template.format(**ctx)

    # ── LLM-backed utterance ─────────────────────────────────────────

    def _try_llm(self, event: ProfessorEvent, decision: SpeakDecision) -> Optional[Utterance]:
        """
        Build a prompt for this event, send to ConversationEngine, return
        the resulting utterance. Returns None if LLM is disabled / unavailable.
        """
        if not self.enable_llm:
            return None
        engine = self._conv()
        if engine is None:
            return None

        prompt = self._build_llm_prompt(event, decision)

        # Build mini operator-state object for the system prompt
        operator_state = type("OS", (), {
            "target":   event.payload.get("target", ""),
            "findings": event.payload.get("prior_findings", []),
            "mode":     event.payload.get("mode", "SUPERVISED"),
        })()

        start_ms = int(datetime.now().timestamp() * 1000)
        try:
            text = engine.chat_blocking(
                user_msg=prompt,
                session_id=self._session_id,
                operator_state=operator_state,
            )
        except Exception as e:
            return Utterance(
                text=f"[Professor LLM unavailable: {e}]",
                event_type=event.type,
                source="llm-error",
            )
        duration_ms = int(datetime.now().timestamp() * 1000) - start_ms

        # Apply vocab adaptation
        text = self.profile.adapt_text(text)

        self._llm_calls += 1
        return Utterance(
            text=text,
            event_type=event.type,
            source="llm",
            cached=False,
            duration_ms=duration_ms,
        )

    def _build_llm_prompt(self, event: ProfessorEvent, decision: SpeakDecision) -> str:
        """
        Build the user-message prompt for the LLM based on event type
        and verbosity. The system prompt (full ERR0RS personality) is
        already wired into ConversationEngine.
        """
        verb = decision.verbosity
        level = self.profile.experience_level
        verb_hint = {
            "brief":   "1-2 short sentences",
            "normal":  "2-4 sentences",
            "verbose": "1-2 short paragraphs, with concrete examples",
        }.get(verb, "2-4 sentences")

        if event.type == EventType.USER_QUESTION:
            q = event.payload.get("question", "")
            return (f"The operator asked: {q!r}\n\n"
                    f"Respond as their security coach. Operator level: {level}. "
                    f"Length: {verb_hint}. Cite sources where possible.")

        if event.type == EventType.FINDING:
            return (f"During the engagement, this finding just landed:\n"
                    f"  Title:    {event.payload.get('title', '?')}\n"
                    f"  Severity: {event.payload.get('severity', '?')}\n"
                    f"  Technique:{event.payload.get('technique', '?')}\n"
                    f"  Detail:   {event.payload.get('detail', '?')}\n\n"
                    f"Explain what this means to a {level}-level operator in "
                    f"{verb_hint}. Cover: what the finding is, why it matters, "
                    f"and what remediation the team should write up.")

        if event.type == EventType.RISKY_ACTION:
            return (f"About to take a risky action:\n"
                    f"  Action: {event.payload.get('action', '?')}\n"
                    f"  Target: {event.payload.get('target', '?')}\n"
                    f"  Risk:   {event.payload.get('risk', '?')}\n\n"
                    f"Explain to the {level} operator what's about to happen, "
                    f"what could go wrong, and what alternatives exist. "
                    f"Length: {verb_hint}.")

        if event.type == EventType.LESSON_SECTION:
            return (f"Walk a {level}-level student through this lesson section:\n"
                    f"  Lesson:  {event.payload.get('lesson_id', '?')}\n"
                    f"  Section: {event.payload.get('section_text', '')}\n\n"
                    f"Explain the concept, give one concrete example, then ask "
                    f"a Socratic check question. Length: {verb_hint}.")

        if event.type == EventType.BRAINSTORM_TURN:
            return event.payload.get("question", "")

        # Generic fallback
        return (f"Comment on this engagement event for a {level}-level operator: "
                f"{event.payload!r}. Length: {verb_hint}.")

    # ── Public API ───────────────────────────────────────────────────

    def narrate_event(self, event: ProfessorEvent) -> Optional[Utterance]:
        """
        Process an event. Decides whether to speak; if so, returns an
        Utterance (cached or LLM-generated). May return None (silent).

        Side effects:
          - Updates profile.mark_explained() for the relevant concept
          - Broadcasts via narrator if attached
        """
        decision = self.should_speak(event)
        if not decision.should:
            return None

        # Try cache first
        utterance = self._try_cached(event, decision)
        if utterance is None:
            utterance = self._try_llm(event, decision)
        if utterance is None:
            # Both failed — silently drop rather than emit garbage
            return None

        # Track concept exposure
        concept = self._concept_for_event(event)
        if concept:
            self.profile.mark_explained(concept)

        # Broadcast via narrator
        if self._narrator is not None:
            try:
                self._narrator.tell(
                    message=utterance.text,
                    phase="teaching",
                    teach=utterance.text if event.type != EventType.PHASE_START else "",
                )
            except Exception:
                pass    # narrator failures must never break the engagement

        return utterance

    def answer_question(self, question: str,
                        engagement_id: Optional[str] = None) -> Utterance:
        """
        Operator asked a question. Always LLM, always answered.
        Marks the concept as questioned (knowledge gap signal).
        """
        # Crude concept extraction: take the first capitalized acronym
        concept = self._guess_concept_from_question(question)
        if concept:
            self.profile.mark_questioned(concept)

        event = ProfessorEvent(
            type=EventType.USER_QUESTION,
            payload={"question": question},
            engagement_id=engagement_id,
        )
        decision = self.should_speak(event)
        utterance = self._try_llm(event, decision)
        if utterance is None:
            return Utterance(
                text=("I would normally answer this, but the LLM is currently "
                      "unavailable. Try again, or check `ollama serve` is running."),
                event_type=event.type,
                source="error",
            )

        if self._narrator is not None:
            try:
                self._narrator.tell(message=utterance.text, phase="teaching",
                                    teach=utterance.text)
            except Exception:
                pass

        return utterance

    def coach_lesson_section(self, lesson_id: str, section_id: str,
                              section_text: str) -> Optional[Utterance]:
        """
        Walk operator through a lesson section. LLM-backed.
        """
        event = ProfessorEvent(
            type=EventType.LESSON_SECTION,
            payload={
                "lesson_id":    lesson_id,
                "section_id":   section_id,
                "section_text": section_text,
            },
        )
        return self.narrate_event(event)

    def brainstorm(self, message: str) -> Utterance:
        """
        Multi-turn brainstorming session — uses ConversationEngine's
        history under a brainstorm session ID for coherence.
        """
        event = ProfessorEvent(
            type=EventType.BRAINSTORM_TURN,
            payload={"question": message},
        )
        decision = self.should_speak(event)
        # Brainstorm uses its own session for multi-turn memory
        old_session = self._session_id
        self._session_id = "brainstorm"
        try:
            utterance = self._try_llm(event, decision)
        finally:
            self._session_id = old_session

        if utterance is None:
            return Utterance(
                text="LLM unavailable — try `ollama serve`.",
                event_type=event.type,
                source="error",
            )
        return utterance

    # ── Concept extraction (for profile updates) ─────────────────────

    @staticmethod
    def _concept_for_event(event: ProfessorEvent) -> Optional[str]:
        """Map event → concept name for profile tracking."""
        if event.type == EventType.PHASE_START:
            return f"phase_{event.payload.get('phase', '')}"
        if event.type == EventType.TOOL_START:
            return f"tool_{event.payload.get('tool', '')}"
        if event.type == EventType.FINDING:
            tech = event.payload.get("technique")
            return f"finding_{tech}" if tech else None
        return None

    @staticmethod
    def _guess_concept_from_question(question: str) -> Optional[str]:
        """
        Heuristic: pull the most likely concept out of a question.
        Returns lowercase identifier or None.
        """
        # Look for known security acronyms / keywords
        q_lower = question.lower()
        for word in ("jwt", "ssti", "xss", "sqli", "csrf", "ssrf", "xxe",
                     "rce", "nosql", "ldap", "smb", "kerberos", "lfi", "rfi"):
            if word in q_lower:
                return f"concept_{word}"
        return None


# ── Module-level singleton ────────────────────────────────────────────────

_engine_lock = threading.Lock()
_engine: Optional[ProfessorEngine] = None


def get_professor(profile=None, narrator=None, enable_llm: bool = True) -> ProfessorEngine:
    """
    Get or create the singleton ProfessorEngine.
    Pass profile/narrator on first call; subsequent calls reuse the instance.
    """
    global _engine
    with _engine_lock:
        if _engine is None:
            if profile is None:
                from src.core.user_profile import get_profile
                profile = get_profile()
            _engine = ProfessorEngine(
                profile=profile,
                narrator=narrator,
                enable_llm=enable_llm,
            )
        return _engine


def reset_professor() -> None:
    """For tests — clear the singleton."""
    global _engine
    with _engine_lock:
        _engine = None
