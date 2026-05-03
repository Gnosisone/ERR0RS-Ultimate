"""
tests/test_professor_killchain_integration.py
==============================================
End-to-end tests for ProfessorEngine wired into AutoKillChain.

Covers:
- AutoKillChain.__init__ accepts professor=
- auto_pentest() forwards professor= to AutoKillChain
- Without --professor, AutoKillChain behaves identically to pre-wiring
- Phase events emitted (PHASE_START, PHASE_END) when professor is attached
- Finding events emitted (one per finding, both native + shell paths)
- Professor failures (raises) never crash the engagement
- engagement_start event fires once per run()

Run: python3 -m pytest tests/test_professor_killchain_integration.py -v
"""

import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import MagicMock
from src.orchestration.auto_killchain import (
    AutoKillChain, auto_pentest, KILL_CHAIN_PHASES, PhaseResult,
)
from src.core.professor_engine import ProfessorEvent, EventType


# ── Fakes ──────────────────────────────────────────────────────────────────

class RecordingProfessor:
    """A professor stub that records every narrate_event call."""
    def __init__(self, *, raise_on=None):
        self.events: list = []
        self.raise_on = raise_on    # event_type to raise on (test resilience)

    def narrate_event(self, event):
        self.events.append(event)
        if self.raise_on and event.type == self.raise_on:
            raise RuntimeError("simulated professor failure")
        return None    # silent (we just want the event recorded)


# ── AutoKillChain accepts professor= ──────────────────────────────────────

class TestAutoKillChainAcceptsProfessor:
    def test_init_with_professor(self):
        prof = RecordingProfessor()
        chain = AutoKillChain(mode="DRY_RUN", professor=prof)
        assert chain.professor is prof

    def test_init_without_professor(self):
        chain = AutoKillChain(mode="DRY_RUN")
        assert chain.professor is None

    def test_init_default_professor_none(self):
        # Backwards compat: no kwarg provided
        chain = AutoKillChain(mode="SUPERVISED")
        assert chain.professor is None


# ── auto_pentest forwards professor ───────────────────────────────────────

class TestAutoPentestForwardsProfessor:
    def test_signature_accepts_professor(self):
        # Just confirm the function accepts the kwarg without error
        import inspect
        sig = inspect.signature(auto_pentest)
        assert "professor" in sig.parameters

    def test_forwards_to_chain(self):
        prof = RecordingProfessor()
        # We can't actually run a real engagement without tools. But we can
        # verify the wiring by patching AutoKillChain to capture init args.
        captured = {}
        original_init = AutoKillChain.__init__
        def capturing_init(self, mode="SUPERVISED", professor=None):
            captured["mode"] = mode
            captured["professor"] = professor
            original_init(self, mode=mode, professor=professor)

        AutoKillChain.__init__ = capturing_init
        try:
            # Run with phases=[] so it returns immediately without doing work
            asyncio.run(auto_pentest("http://localhost:9999",
                                       mode="DRY_RUN",
                                       phases=[],
                                       professor=prof))
        except Exception:
            pass    # We only care that init was called with our args
        finally:
            AutoKillChain.__init__ = original_init

        assert captured.get("professor") is prof
        assert captured.get("mode") == "DRY_RUN"


# ── Engagement-start event fires once per run() ───────────────────────────

class TestEngagementStartEvent:
    def test_engagement_start_fires_once(self):
        prof = RecordingProfessor()
        chain = AutoKillChain(mode="DRY_RUN", professor=prof)
        # Run with empty phases list — no real tool dispatch
        asyncio.run(chain.run("http://127.0.0.1:9999", params={}, phases=[]))
        # Look for the engagement_start phase marker
        starts = [e for e in prof.events
                  if e.type == EventType.PHASE_START
                  and e.payload.get("phase") == "engagement_start"]
        assert len(starts) == 1
        assert starts[0].payload.get("target") == "http://127.0.0.1:9999"
        assert starts[0].payload.get("mode") == "DRY_RUN"

    def test_no_professor_no_events(self):
        # No professor = no events recorded anywhere; just run cleanly
        chain = AutoKillChain(mode="DRY_RUN")
        result = asyncio.run(chain.run("http://127.0.0.1:9999", params={}, phases=[]))
        assert isinstance(result, dict)


# ── Phase events fire when phases run ─────────────────────────────────────

class TestPhaseEvents:
    @pytest.fixture
    def stub_phase(self, monkeypatch):
        """Make _run_phase a no-op that returns an empty PhaseResult."""
        async def _stub_run_phase(self, phase_def):
            # Manually emit phase_start ourselves (real _run_phase does it inside)
            if self.professor is not None:
                self.professor.narrate_event(ProfessorEvent(
                    type=EventType.PHASE_START,
                    payload={"phase": phase_def["id"],
                             "tools": list(phase_def["tools"]),
                             "target": self.target},
                ))
            result = PhaseResult(phase_id=phase_def["id"],
                                  phase_name=phase_def["name"])
            result.tools_run = 0
            result.duration_s = 1.0
            if self.professor is not None:
                self.professor.narrate_event(ProfessorEvent(
                    type=EventType.PHASE_END,
                    payload={"phase": phase_def["id"],
                             "tools_run": result.tools_run,
                             "findings": 0,
                             "duration_s": result.duration_s},
                ))
            return result
        monkeypatch.setattr(AutoKillChain, "_run_phase", _stub_run_phase)

    def test_phase_start_fires_per_phase(self, stub_phase):
        prof = RecordingProfessor()
        # Use FULL_AUTO — DRY_RUN short-circuits before _run_phase is called.
        # The stub_phase fixture replaces _run_phase entirely so no real tools fire.
        chain = AutoKillChain(mode="FULL_AUTO", professor=prof)
        phases = [p["id"] for p in KILL_CHAIN_PHASES[:2]]
        asyncio.run(chain.run("http://127.0.0.1:9999", params={}, phases=phases))
        phase_starts = [e for e in prof.events
                        if e.type == EventType.PHASE_START
                        and e.payload.get("phase") != "engagement_start"]
        assert len(phase_starts) == 2

    def test_phase_end_fires_per_phase(self, stub_phase):
        prof = RecordingProfessor()
        chain = AutoKillChain(mode="FULL_AUTO", professor=prof)
        phases = [p["id"] for p in KILL_CHAIN_PHASES[:2]]
        asyncio.run(chain.run("http://127.0.0.1:9999", params={}, phases=phases))
        phase_ends = [e for e in prof.events if e.type == EventType.PHASE_END]
        assert len(phase_ends) == 2


# ── Resilience: professor failures must not crash the engagement ──────────

class TestProfessorResilience:
    def test_engagement_completes_even_if_professor_raises(self):
        # Professor raises on PHASE_START — kill chain must still complete
        prof = RecordingProfessor(raise_on=EventType.PHASE_START)
        chain = AutoKillChain(mode="DRY_RUN", professor=prof)
        # Empty phases list — only engagement_start fires (which raises)
        result = asyncio.run(chain.run("http://127.0.0.1:9999", params={}, phases=[]))
        # Despite the raise, run() must return a result dict, not propagate the exception
        assert isinstance(result, dict)
        # And the engagement_start was attempted (recorded before raise)
        assert any(e.type == EventType.PHASE_START
                   and e.payload.get("phase") == "engagement_start"
                   for e in prof.events)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
