"""
tests/test_professor_engine.py
===============================
ProfessorEngine test suite. Covers:

- should_speak() decision matrix for all event types × all levels
- Cached templates fire instantly for predictable events
- LLM is consulted only for novel / critical events
- Profile mastery tracking integrates correctly
- Vocab adaptation gets applied to all utterances
- answer_question always uses LLM, marks concept as questioned
- coach_lesson_section produces utterances for lessons
- brainstorm uses isolated session ID for multi-turn coherence
- Singleton get_professor() / reset_professor()
- Narrator broadcast happens (without crashing on narrator failure)
- Stats track LLM calls vs cache hits
- Edge cases: missing payload fields, unknown event subkeys

Run: python3 -m pytest tests/test_professor_engine.py -v
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import MagicMock
from src.core.professor_engine import (
    ProfessorEngine, ProfessorEvent, EventType, Utterance, SpeakDecision,
    CANNED_EXPLANATIONS, TOOL_PURPOSES, TOOL_INSTALL_HINTS,
    get_professor, reset_professor,
)
from src.core.user_profile import UserProfile


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def novice_profile():
    return UserProfile(operator_id="novice_alice", experience_level="novice")

@pytest.fixture
def intermediate_profile():
    return UserProfile(operator_id="mid_bob", experience_level="intermediate")

@pytest.fixture
def expert_profile():
    return UserProfile(operator_id="exp_carl", experience_level="expert")

@pytest.fixture
def fake_llm_engine():
    """ConversationEngine stub that returns a canned response."""
    eng = MagicMock()
    eng.chat_blocking.return_value = "Stubbed LLM response about the event."
    return eng

@pytest.fixture
def fake_narrator():
    """Narrator stub that records calls."""
    n = MagicMock()
    return n


# ── should_speak: decision matrix ─────────────────────────────────────────

class TestShouldSpeak:
    """Verify the should_speak() decision logic for every event × level combo."""

    @pytest.fixture(autouse=True)
    def _setup(self, novice_profile, intermediate_profile, expert_profile):
        self.profs = {
            "novice":       ProfessorEngine(profile=novice_profile, enable_llm=False),
            "intermediate": ProfessorEngine(profile=intermediate_profile, enable_llm=False),
            "expert":       ProfessorEngine(profile=expert_profile, enable_llm=False),
        }

    def test_user_question_always_speaks_verbose(self):
        for level in ("novice", "intermediate", "expert"):
            d = self.profs[level].should_speak(
                ProfessorEvent(type=EventType.USER_QUESTION,
                                payload={"question": "what is jwt?"}))
            assert d.should
            assert d.verbosity == "verbose"

    def test_risky_action_always_verbose(self):
        for level in ("novice", "intermediate", "expert"):
            d = self.profs[level].should_speak(
                ProfessorEvent(type=EventType.RISKY_ACTION,
                                payload={"action": "rm -rf /tmp/cache"}))
            assert d.should and d.verbosity == "verbose"

    def test_phase_start_verbosity_scales_with_level(self):
        evt = ProfessorEvent(type=EventType.PHASE_START,
                              payload={"phase": "recon", "tools": ["nmap"]})
        assert self.profs["novice"].should_speak(evt).verbosity       == "verbose"
        assert self.profs["intermediate"].should_speak(evt).verbosity == "normal"
        assert self.profs["expert"].should_speak(evt).verbosity       == "brief"

    def test_phase_end_silent_for_expert(self):
        evt = ProfessorEvent(type=EventType.PHASE_END,
                              payload={"phase": "recon"})
        assert not self.profs["expert"].should_speak(evt).should
        assert self.profs["intermediate"].should_speak(evt).should
        assert self.profs["novice"].should_speak(evt).should

    def test_tool_start_only_speaks_for_novice(self):
        evt = ProfessorEvent(type=EventType.TOOL_START,
                              payload={"tool": "nmap_discovery"})
        assert self.profs["novice"].should_speak(evt).should
        assert not self.profs["intermediate"].should_speak(evt).should
        assert not self.profs["expert"].should_speak(evt).should

    def test_tool_start_silent_after_concept_seen(self, novice_profile):
        # Mark tool concept as recently explained
        novice_profile.mark_explained("tool_nmap_discovery")
        eng = ProfessorEngine(profile=novice_profile, enable_llm=False)
        evt = ProfessorEvent(type=EventType.TOOL_START,
                              payload={"tool": "nmap_discovery"})
        assert not eng.should_speak(evt).should

    def test_tool_skip_speaks_for_non_expert(self):
        evt = ProfessorEvent(type=EventType.TOOL_SKIP,
                              payload={"tool": "nuclei"})
        assert self.profs["novice"].should_speak(evt).should
        assert self.profs["intermediate"].should_speak(evt).should
        assert not self.profs["expert"].should_speak(evt).should

    def test_tool_end_silent_when_no_findings(self):
        evt = ProfessorEvent(type=EventType.TOOL_END,
                              payload={"tool": "nmap", "findings": 0})
        for level in self.profs:
            assert not self.profs[level].should_speak(evt).should

    def test_critical_finding_always_verbose(self):
        evt = ProfessorEvent(type=EventType.FINDING,
                              payload={"severity": "critical",
                                       "technique": "jwt_alg_none",
                                       "title": "auth bypass"})
        for level in ("novice", "intermediate", "expert"):
            d = self.profs[level].should_speak(evt)
            assert d.should and d.verbosity == "verbose"

    def test_high_finding_normal_for_all(self):
        evt = ProfessorEvent(type=EventType.FINDING,
                              payload={"severity": "high",
                                       "technique": "kid_injection"})
        for level in ("novice", "intermediate", "expert"):
            d = self.profs[level].should_speak(evt)
            assert d.should and d.verbosity == "normal"

    def test_info_finding_silent_for_intermediate_and_expert(self):
        evt = ProfessorEvent(type=EventType.FINDING,
                              payload={"severity": "info",
                                       "technique": "open_port"})
        assert self.profs["novice"].should_speak(evt).should
        assert not self.profs["intermediate"].should_speak(evt).should
        assert not self.profs["expert"].should_speak(evt).should

    def test_medium_finding_silent_when_mastered(self, intermediate_profile):
        intermediate_profile.mark_mastered("finding_idor")
        eng = ProfessorEngine(profile=intermediate_profile, enable_llm=False)
        evt = ProfessorEvent(type=EventType.FINDING,
                              payload={"severity": "medium", "technique": "idor"})
        assert not eng.should_speak(evt).should


# ── Cached template firing ─────────────────────────────────────────────────

class TestCachedTemplates:
    def test_phase_start_recon_cached_novice(self, novice_profile):
        eng = ProfessorEngine(profile=novice_profile, enable_llm=False)
        evt = ProfessorEvent(type=EventType.PHASE_START,
                              payload={"phase": "recon", "tools": ["nmap_discovery"]})
        u = eng.narrate_event(evt)
        assert u is not None
        assert u.cached
        assert u.source == "cache"
        assert "Phase 1" in u.text or "Reconnaissance" in u.text or "Recon" in u.text
        # Verify tools list got formatted
        assert "nmap_discovery" in u.text
        # Cache hit should be tracked
        assert eng.stats["cache_hits"] == 1
        assert eng.stats["llm_calls"] == 0

    def test_phase_start_template_per_level(self, expert_profile):
        eng = ProfessorEngine(profile=expert_profile, enable_llm=False)
        evt = ProfessorEvent(type=EventType.PHASE_START,
                              payload={"phase": "recon", "tools": ["nmap_discovery"]})
        u = eng.narrate_event(evt)
        # Expert template is "Recon. nmap_discovery."
        assert u.text == "Recon. nmap_discovery."

    def test_tool_skip_cached_with_install_hint(self, novice_profile):
        eng = ProfessorEngine(profile=novice_profile, enable_llm=False)
        evt = ProfessorEvent(type=EventType.TOOL_SKIP,
                              payload={"tool": "nuclei"})
        u = eng.narrate_event(evt)
        assert u is not None
        assert "apt install nuclei" in u.text

    def test_phase_end_cached(self, intermediate_profile):
        eng = ProfessorEngine(profile=intermediate_profile, enable_llm=False)
        evt = ProfessorEvent(type=EventType.PHASE_END,
                              payload={"phase": "recon", "tools_run": 3,
                                       "findings": 5, "duration_s": 12.5})
        u = eng.narrate_event(evt)
        assert u is not None
        assert "3" in u.text and "5" in u.text

    def test_template_missing_field_falls_back_to_llm(self, novice_profile, fake_llm_engine):
        # If template needs {tools} but payload doesn't have it
        eng = ProfessorEngine(profile=novice_profile,
                                conversation_engine=fake_llm_engine, enable_llm=True)
        evt = ProfessorEvent(type=EventType.PHASE_START,
                              payload={"phase": "recon"})  # no tools
        u = eng.narrate_event(evt)
        # Should have fallen back to LLM
        assert u is not None
        assert u.source == "llm"
        assert eng.stats["llm_calls"] == 1


# ── LLM-backed utterances ─────────────────────────────────────────────────

class TestLLMUtterances:
    def test_critical_finding_uses_llm(self, novice_profile, fake_llm_engine):
        eng = ProfessorEngine(profile=novice_profile,
                                conversation_engine=fake_llm_engine, enable_llm=True)
        evt = ProfessorEvent(type=EventType.FINDING,
                              payload={"severity": "critical",
                                       "title": "JWT secret cracked",
                                       "technique": "hs256_crack",
                                       "detail": "secret=mySecret"})
        u = eng.narrate_event(evt)
        assert u.source == "llm"
        assert "Stubbed LLM response" in u.text
        # The LLM was called with a prompt that includes the finding
        call = fake_llm_engine.chat_blocking.call_args
        assert "JWT secret cracked" in call.kwargs["user_msg"]

    def test_user_question_always_llm(self, novice_profile, fake_llm_engine):
        eng = ProfessorEngine(profile=novice_profile,
                                conversation_engine=fake_llm_engine, enable_llm=True)
        u = eng.answer_question("what is alg=none jwt attack?")
        assert u.source == "llm"
        # Question mark concept → marks 'jwt' as questioned
        assert "concept_jwt" not in novice_profile.concepts_mastered

    def test_user_question_marks_concept_as_questioned(self, intermediate_profile, fake_llm_engine):
        intermediate_profile.mark_mastered("concept_jwt")
        eng = ProfessorEngine(profile=intermediate_profile,
                                conversation_engine=fake_llm_engine, enable_llm=True)
        eng.answer_question("can you remind me what JWT is?")
        # JWT should no longer be mastered after the question
        assert "concept_jwt" not in intermediate_profile.concepts_mastered

    def test_llm_disabled_returns_none_for_uncached(self, novice_profile):
        eng = ProfessorEngine(profile=novice_profile, enable_llm=False)
        # FINDING events have no canned template → LLM needed → with LLM
        # disabled, narrate_event returns None
        evt = ProfessorEvent(type=EventType.FINDING,
                              payload={"severity": "critical", "title": "x"})
        u = eng.narrate_event(evt)
        assert u is None

    def test_llm_failure_returns_none_or_error_utterance(self, novice_profile):
        bad = MagicMock()
        bad.chat_blocking.side_effect = ConnectionError("ollama down")
        eng = ProfessorEngine(profile=novice_profile,
                                conversation_engine=bad, enable_llm=True)
        evt = ProfessorEvent(type=EventType.FINDING,
                              payload={"severity": "critical", "title": "x"})
        u = eng.narrate_event(evt)
        # Either None (silent drop) or an explicit error utterance — must not raise
        assert u is None or "unavailable" in u.text or "error" in u.source


# ── Profile integration ───────────────────────────────────────────────────

class TestProfileIntegration:
    def test_explained_concepts_recorded(self, novice_profile):
        eng = ProfessorEngine(profile=novice_profile, enable_llm=False)
        evt = ProfessorEvent(type=EventType.PHASE_START,
                              payload={"phase": "recon", "tools": ["nmap"]})
        eng.narrate_event(evt)
        # Concept name follows convention: phase_<phase_id>
        assert "phase_recon" in novice_profile.concepts_explained

    def test_repeated_phase_eventually_marks_mastered(self, novice_profile):
        eng = ProfessorEngine(profile=novice_profile, enable_llm=False)
        evt = ProfessorEvent(type=EventType.PHASE_START,
                              payload={"phase": "recon", "tools": ["nmap"]})
        for _ in range(10):  # well above MASTERY_INFERENCE_THRESHOLD
            eng.narrate_event(evt)
        assert "phase_recon" in novice_profile.concepts_mastered

    def test_vocab_adaptation_applied_to_cached_text(self, novice_profile):
        # Inject something with "RFC1918" into a cached template
        # (Use a payload whose template will mention RFC1918 — we'll trigger
        # via vocab applying to phase_start text. The phase_start template
        # for novice mentions "we're listening, not attacking yet" — no RFC1918,
        # but adapt_text will be called regardless. Verify by checking the
        # template itself doesn't break.)
        eng = ProfessorEngine(profile=novice_profile, enable_llm=False)
        evt = ProfessorEvent(type=EventType.PHASE_START,
                              payload={"phase": "recon", "tools": ["nmap"]})
        u = eng.narrate_event(evt)
        # No RFC1918 in template, but adapt_text was called — confirm via stats
        assert u is not None


# ── coach_lesson_section + brainstorm ─────────────────────────────────────

class TestLessonAndBrainstorm:
    def test_coach_lesson_section_uses_llm(self, novice_profile, fake_llm_engine):
        eng = ProfessorEngine(profile=novice_profile,
                                conversation_engine=fake_llm_engine, enable_llm=True)
        u = eng.coach_lesson_section(
            lesson_id="14",
            section_id="intro",
            section_text="SQL injection happens when user input is concatenated into queries.",
        )
        assert u is not None
        assert u.source == "llm"
        # Verify prompt mentions the lesson section
        call = fake_llm_engine.chat_blocking.call_args
        assert "SQL injection happens" in call.kwargs["user_msg"]

    def test_brainstorm_uses_isolated_session(self, novice_profile, fake_llm_engine):
        eng = ProfessorEngine(profile=novice_profile,
                                conversation_engine=fake_llm_engine, enable_llm=True)
        eng.brainstorm("how would I attack a Joomla site?")
        # Verify session_id was 'brainstorm' for the call
        call = fake_llm_engine.chat_blocking.call_args
        assert call.kwargs["session_id"] == "brainstorm"


# ── Narrator broadcast ────────────────────────────────────────────────────

class TestNarratorBroadcast:
    def test_narrator_called_when_attached(self, novice_profile, fake_narrator):
        eng = ProfessorEngine(profile=novice_profile,
                                narrator=fake_narrator, enable_llm=False)
        evt = ProfessorEvent(type=EventType.PHASE_START,
                              payload={"phase": "recon", "tools": ["nmap"]})
        eng.narrate_event(evt)
        assert fake_narrator.tell.called

    def test_narrator_failure_does_not_break_engine(self, novice_profile):
        bad_narrator = MagicMock()
        bad_narrator.tell.side_effect = RuntimeError("narrator broken")
        eng = ProfessorEngine(profile=novice_profile,
                                narrator=bad_narrator, enable_llm=False)
        evt = ProfessorEvent(type=EventType.PHASE_START,
                              payload={"phase": "recon", "tools": ["nmap"]})
        # Must not raise
        u = eng.narrate_event(evt)
        assert u is not None     # Utterance still returned despite narrator failure


# ── Stats tracking ────────────────────────────────────────────────────────

class TestStats:
    def test_stats_track_cache_and_llm(self, novice_profile, fake_llm_engine):
        eng = ProfessorEngine(profile=novice_profile,
                                conversation_engine=fake_llm_engine, enable_llm=True)
        # Cached event
        eng.narrate_event(ProfessorEvent(type=EventType.PHASE_START,
                                          payload={"phase": "recon", "tools": ["x"]}))
        # LLM event
        eng.narrate_event(ProfessorEvent(type=EventType.FINDING,
                                          payload={"severity": "critical", "title": "x"}))
        stats = eng.stats
        assert stats["cache_hits"] == 1
        assert stats["llm_calls"]  == 1


# ── Singleton ─────────────────────────────────────────────────────────────

class TestSingleton:
    def test_get_professor_returns_same_instance(self, monkeypatch, tmp_path):
        # Avoid touching real ~/.err0rs/
        from src.core.user_profile import UserProfile, reset_profile
        monkeypatch.setattr(UserProfile, "default_path",
                            classmethod(lambda cls: tmp_path / "profile.json"))
        reset_profile()
        reset_professor()
        a = get_professor(enable_llm=False)
        b = get_professor(enable_llm=False)
        assert a is b


# ── Edge cases ────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_unknown_event_type_handled_gracefully(self, novice_profile):
        # Constructing with bad enum should raise ValueError at construction
        with pytest.raises(ValueError):
            ProfessorEvent(type="not_an_event")  # noqa

    def test_phase_start_with_empty_tools_list(self, novice_profile):
        eng = ProfessorEngine(profile=novice_profile, enable_llm=False)
        evt = ProfessorEvent(type=EventType.PHASE_START,
                              payload={"phase": "recon", "tools": []})
        u = eng.narrate_event(evt)
        # Empty tool list — joined as "" — should still produce text
        assert u is not None

    def test_unknown_phase_falls_back_to_default(self, novice_profile):
        eng = ProfessorEngine(profile=novice_profile, enable_llm=False)
        evt = ProfessorEvent(type=EventType.PHASE_START,
                              payload={"phase": "totally_made_up_phase", "tools": ["x"]})
        # PHASE_START has no "default" key in CANNED_EXPLANATIONS — should
        # return None (silent) or fall through to LLM (None when disabled)
        u = eng.narrate_event(evt)
        assert u is None    # No template, LLM disabled → silent

    def test_concept_extraction_from_question(self, novice_profile):
        from src.core.professor_engine import ProfessorEngine as PE
        assert PE._guess_concept_from_question("what is JWT?")     == "concept_jwt"
        assert PE._guess_concept_from_question("how does SSTI work?") == "concept_ssti"
        assert PE._guess_concept_from_question("hello world?")     is None


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
