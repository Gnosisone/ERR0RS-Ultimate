"""
tests/test_audit.py
====================
Audit log test suite.

Covers:
- Engagement ID generation is unique and deterministic format
- Events are appended in monotonic seq order
- File is fsynced (read-back from disk shows the event)
- Thread-safe concurrent appends never lose or interleave events
- Resuming an existing engagement continues seq correctly
- Closed-enum event types refuse free-form strings
- Sanitization handles huge strings, weird types, lists
- replay() and summary() work end-to-end
- Convenience wrappers all produce well-formed events
"""

import sys, os, json, threading, tempfile, shutil
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from pathlib import Path
from src.orchestration.audit import AuditLogger, EventType


@pytest.fixture
def tmpbase():
    d = tempfile.mkdtemp(prefix="err0rs_audit_test_")
    yield Path(d)
    shutil.rmtree(d, ignore_errors=True)


# ── Engagement ID generation ───────────────────────────────────────────────

class TestEngagementId:
    def test_format(self):
        eid = AuditLogger.new_engagement_id()
        # YYYY-MM-DD-NNN-XXXXXX
        parts = eid.split("-")
        # Date is YYYY-MM-DD = 3 parts, then NNN = 1 part, then suffix = 1 part
        assert len(parts) == 5
        assert len(parts[0]) == 4  # year
        assert len(parts[1]) == 2  # month
        assert len(parts[2]) == 2  # day
        assert len(parts[3]) == 3  # NNN counter
        assert len(parts[4]) == 6  # hex suffix

    def test_unique_across_calls(self):
        ids = {AuditLogger.new_engagement_id() for _ in range(20)}
        assert len(ids) == 20  # All 20 unique


# ── Basic event writing ────────────────────────────────────────────────────

class TestEventWriting:
    def test_first_event_has_seq_1(self, tmpbase):
        log = AuditLogger.for_engagement("test-001", "eros", base_dir=tmpbase)
        seq = log.event(EventType.NOTE, data={"msg": "hello"})
        assert seq == 1

    def test_seq_increments(self, tmpbase):
        log = AuditLogger.for_engagement("test-002", "eros", base_dir=tmpbase)
        s1 = log.event(EventType.NOTE, data={"a": 1})
        s2 = log.event(EventType.NOTE, data={"b": 2})
        s3 = log.event(EventType.NOTE, data={"c": 3})
        assert (s1, s2, s3) == (1, 2, 3)

    def test_event_persisted_to_disk(self, tmpbase):
        log = AuditLogger.for_engagement("test-003", "eros", base_dir=tmpbase)
        log.event(EventType.PHASE_START, phase="recon",
                  data={"tools_planned": ["nmap"]})
        log.close()

        log_file = tmpbase / "test-003" / "audit.jsonl"
        assert log_file.exists()
        content = log_file.read_text().strip()
        rec = json.loads(content)
        assert rec["event"] == "phase_start"
        assert rec["phase"] == "recon"
        assert rec["data"]["tools_planned"] == ["nmap"]
        assert rec["seq"] == 1

    def test_refuses_freeform_event_type(self, tmpbase):
        log = AuditLogger.for_engagement("test-004", "eros", base_dir=tmpbase)
        with pytest.raises(TypeError):
            log.event("phase_start", phase="recon")  # noqa: type-error on purpose

    def test_record_has_required_fields(self, tmpbase):
        log = AuditLogger.for_engagement("test-005", "eros", base_dir=tmpbase)
        log.event(EventType.NOTE, data={"x": 1})
        log.close()
        rec = json.loads((tmpbase / "test-005" / "audit.jsonl").read_text().strip())
        for field in ("ts", "engagement", "event", "operator", "seq"):
            assert field in rec


# ── Resumption ─────────────────────────────────────────────────────────────

class TestResumption:
    def test_seq_continues_across_open(self, tmpbase):
        log1 = AuditLogger.for_engagement("test-resume", "eros", base_dir=tmpbase)
        log1.event(EventType.NOTE, data={"a": 1})
        log1.event(EventType.NOTE, data={"b": 2})
        log1.close()

        log2 = AuditLogger.for_engagement("test-resume", "eros", base_dir=tmpbase)
        s = log2.event(EventType.NOTE, data={"c": 3})
        assert s == 3, "Resumed log should continue from seq 3, not restart at 1"

    def test_resume_handles_corrupt_lines(self, tmpbase):
        log_file = tmpbase / "test-corrupt" / "audit.jsonl"
        log_file.parent.mkdir(parents=True)
        log_file.write_text(
            '{"seq": 1}\n'
            'NOT JSON GARBAGE\n'
            '{"seq": 5}\n'
        )
        log = AuditLogger.for_engagement("test-corrupt", "eros", base_dir=tmpbase)
        s = log.event(EventType.NOTE, data={"x": 1})
        assert s == 6  # Continues past max(seq) = 5


# ── Thread safety ──────────────────────────────────────────────────────────

class TestThreadSafety:
    def test_concurrent_writes_no_loss(self, tmpbase):
        log = AuditLogger.for_engagement("test-threads", "eros", base_dir=tmpbase)

        N_THREADS = 8
        N_PER_THREAD = 50

        def worker(idx):
            for i in range(N_PER_THREAD):
                log.event(EventType.NOTE, data={"thread": idx, "i": i})

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(N_THREADS)]
        for t in threads: t.start()
        for t in threads: t.join()
        log.close()

        events = log.replay()
        assert len(events) == N_THREADS * N_PER_THREAD

        # Sequence numbers should be unique and contiguous 1..N
        seqs = sorted(e["seq"] for e in events)
        assert seqs == list(range(1, N_THREADS * N_PER_THREAD + 1))


# ── Sanitization ───────────────────────────────────────────────────────────

class TestSanitization:
    def test_huge_string_truncated(self, tmpbase):
        log = AuditLogger.for_engagement("test-huge", "eros", base_dir=tmpbase)
        log.event(EventType.NOTE, data={"big": "x" * 10000})
        log.close()
        rec = json.loads((tmpbase / "test-huge" / "audit.jsonl").read_text().strip())
        assert len(rec["data"]["big"]) <= 4500
        assert "truncated" in rec["data"]["big"]

    def test_huge_list_capped(self, tmpbase):
        log = AuditLogger.for_engagement("test-list", "eros", base_dir=tmpbase)
        log.event(EventType.NOTE, data={"items": list(range(500))})
        log.close()
        rec = json.loads((tmpbase / "test-list" / "audit.jsonl").read_text().strip())
        assert len(rec["data"]["items"]) == 100  # capped

    def test_unserializable_falls_back_to_repr(self, tmpbase):
        class Weird:
            def __repr__(self): return "WeirdObject<>"

        log = AuditLogger.for_engagement("test-weird", "eros", base_dir=tmpbase)
        log.event(EventType.NOTE, data={"obj": Weird()})
        log.close()
        rec = json.loads((tmpbase / "test-weird" / "audit.jsonl").read_text().strip())
        assert "WeirdObject" in rec["data"]["obj"]

    def test_underscore_keys_stripped(self, tmpbase):
        log = AuditLogger.for_engagement("test-priv", "eros", base_dir=tmpbase)
        log.event(EventType.NOTE, data={"public": 1, "_secret": "no-leak"})
        log.close()
        rec = json.loads((tmpbase / "test-priv" / "audit.jsonl").read_text().strip())
        assert "public" in rec["data"]
        assert "_secret" not in rec["data"]


# ── Convenience wrappers ───────────────────────────────────────────────────

class TestConvenienceWrappers:
    def test_engagement_lifecycle(self, tmpbase):
        log = AuditLogger.for_engagement("test-conv", "eros", base_dir=tmpbase)
        log.engagement_start("http://localhost:3000", "FULL_AUTO")
        log.phase_start("recon", ["nmap", "whatweb"])
        log.tool_start("nmap", "nmap -sV localhost", "recon")
        log.tool_end("nmap", "recon", success=True, duration_s=5.4, findings=3)
        log.finding(title="Open port 3000", severity="info", phase="recon",
                    tool="nmap", detail="3000/tcp open node")
        log.phase_end("recon", tools_run=2, findings=3, duration_s=12.0)
        log.engagement_end("complete", summary={"findings": 3})
        log.close()

        events = log.replay()
        types = [e["event"] for e in events]
        assert types == [
            "engagement_start", "phase_start", "tool_start", "tool_end",
            "finding", "phase_end", "engagement_end",
        ]

    def test_auth_event_records_grant(self, tmpbase):
        log = AuditLogger.for_engagement("test-auth", "eros", base_dir=tmpbase)
        log.auth(granted=True, target="http://localhost",
                 target_class="always_allowed", reason="loopback",
                 resolved_ip="127.0.0.1")
        log.close()
        rec = json.loads((tmpbase / "test-auth" / "audit.jsonl").read_text().strip())
        assert rec["event"] == "auth_granted"
        assert rec["data"]["target_class"] == "always_allowed"


# ── replay() and summary() ─────────────────────────────────────────────────

class TestReplayAndSummary:
    def test_replay_returns_all_events_in_order(self, tmpbase):
        log = AuditLogger.for_engagement("test-replay", "eros", base_dir=tmpbase)
        for i in range(10):
            log.event(EventType.NOTE, data={"i": i})
        log.close()

        events = log.replay()
        assert len(events) == 10
        for i, e in enumerate(events):
            assert e["data"]["i"] == i
            assert e["seq"] == i + 1

    def test_summary_counts_findings_by_severity(self, tmpbase):
        log = AuditLogger.for_engagement("test-summary", "eros", base_dir=tmpbase)
        log.finding(title="A", severity="critical", phase="exploit")
        log.finding(title="B", severity="critical", phase="exploit")
        log.finding(title="C", severity="high", phase="vuln")
        log.finding(title="D", severity="info", phase="recon")
        log.close()

        s = log.summary()
        assert s["findings_total"] == 4
        assert s["findings_by_severity"]["critical"] == 2
        assert s["findings_by_severity"]["high"] == 1
        assert s["findings_by_severity"]["info"] == 1


# ── Context manager ────────────────────────────────────────────────────────

class TestContextManager:
    def test_with_block_closes_handle(self, tmpbase):
        with AuditLogger.for_engagement("test-ctx", "eros", base_dir=tmpbase) as log:
            log.event(EventType.NOTE, data={"x": 1})
            assert log._fh is not None
        # After __exit__:
        assert log._fh is None

    def test_exception_propagates_through_with(self, tmpbase):
        with pytest.raises(ValueError):
            with AuditLogger.for_engagement("test-exc", "eros", base_dir=tmpbase) as log:
                log.event(EventType.NOTE, data={"x": 1})
                raise ValueError("boom")
        # File should still exist with the one event
        events = AuditLogger.for_engagement(
            "test-exc", "eros", base_dir=tmpbase
        ).replay()
        assert len(events) == 1


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
