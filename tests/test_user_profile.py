"""
tests/test_user_profile.py
===========================
UserProfile test suite. Covers:

- Schema validation (closed enum on experience_level)
- Default field initialization (fresh profile is valid)
- to_dict / from_dict round-trip preserves all data
- Concept tracking (mark_explained, has_seen, has_mastered, decay)
- Vocab adaptation per level (novice gets DEFAULT_NOVICE_VOCAB, expert untouched)
- Word-boundary substitution (POST in 'POSTGRESQL' doesn't match)
- Mastery inference (5x explained without question -> mastered)
- Mastery decay (90 days no activity -> remastery needed)
- Skip list (concepts in skip_explanations always treated as mastered)
- Persistence (save/load round-trip)
- Atomic writes (tmp + rename, no partial files on disk)
- Corrupt file handling (load returns fresh profile, backs up corrupt)
- Schema migration hook
- Session inference (promote novice -> intermediate after silent session)
- Session inference (demote expert -> intermediate after many questions)
- Singleton pattern (get_profile / reset_profile)
- Custom path support (for multi-operator tests)

Run: python3 -m pytest tests/test_user_profile.py -v
"""

import sys, os, json, time, tempfile, shutil
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from src.core.user_profile import (
    UserProfile, ConceptStats, get_profile, reset_profile,
    DEFAULT_NOVICE_VOCAB, MASTERY_DECAY_DAYS, RECENT_EXPLANATION_DAYS,
    MASTERY_INFERENCE_THRESHOLD, SCHEMA_VERSION, VALID_LEVELS,
    _word_boundary_replace,
)


@pytest.fixture
def tmp_profile_path(tmp_path):
    """Isolated profile path per test."""
    return tmp_path / "profile.json"


# ── Schema validation ──────────────────────────────────────────────────────

class TestSchemaValidation:
    def test_default_construction(self):
        p = UserProfile(operator_id="alice")
        assert p.operator_id == "alice"
        assert p.experience_level == "novice"
        assert p.sessions_count == 0
        assert p.first_seen != ""
        assert p.last_seen == p.first_seen   # same on first construction

    def test_invalid_level_rejected(self):
        with pytest.raises(ValueError):
            UserProfile(operator_id="x", experience_level="ninja")

    def test_all_valid_levels_accepted(self):
        for level in VALID_LEVELS:
            p = UserProfile(operator_id="x", experience_level=level)
            assert p.experience_level == level

    def test_concepts_explained_normalized(self):
        # Pass dict-of-dicts; should normalize to dict-of-ConceptStats
        p = UserProfile(
            operator_id="x",
            concepts_explained={"jwt_alg_none": {"count": 3, "last": "2026-01-01T00:00:00+00:00"}},
        )
        assert isinstance(p.concepts_explained["jwt_alg_none"], ConceptStats)
        assert p.concepts_explained["jwt_alg_none"].count == 3

    def test_garbage_in_concepts_explained_skipped(self):
        # Defensive: garbage values get dropped, not crash
        p = UserProfile(
            operator_id="x",
            concepts_explained={"good": {"count": 1, "last": ""}, "bad": "not a dict"},
        )
        assert "good" in p.concepts_explained
        assert "bad" not in p.concepts_explained

    def test_mastered_dedup(self):
        # Duplicates in mastered list are silently de-duped
        p = UserProfile(operator_id="x", concepts_mastered=["a", "a", "b", "a"])
        assert p.concepts_mastered == ["a", "b"]

    def test_first_seen_set_on_blank(self):
        p = UserProfile(operator_id="x", first_seen="", last_seen="")
        # Both should now be ISO-8601
        assert "T" in p.first_seen
        assert p.first_seen == p.last_seen


# ── Round-trip serialization ───────────────────────────────────────────────

class TestSerializationRoundTrip:
    def test_to_dict_from_dict_round_trip(self):
        p1 = UserProfile(
            operator_id="eros",
            experience_level="intermediate",
            concepts_explained={"jwt_alg_none": ConceptStats(count=3, last="2026-05-01T10:00:00+00:00")},
            concepts_mastered=["sql_union_basic"],
            vocab_calibration={"foo": "bar"},
            preferred_techniques=["jwt_attacks", "ssti"],
            skip_explanations=["what_is_nmap"],
            sessions_count=42,
        )
        as_dict = p1.to_dict()
        p2 = UserProfile.from_dict(as_dict)
        assert p2.operator_id == p1.operator_id
        assert p2.experience_level == p1.experience_level
        assert p2.concepts_mastered == p1.concepts_mastered
        assert p2.vocab_calibration == p1.vocab_calibration
        assert p2.preferred_techniques == p1.preferred_techniques
        assert p2.skip_explanations == p1.skip_explanations
        assert p2.sessions_count == p1.sessions_count
        assert p2.concepts_explained["jwt_alg_none"].count == 3

    def test_from_dict_tolerates_missing_fields(self):
        p = UserProfile.from_dict({"operator_id": "bob"})
        assert p.operator_id == "bob"
        assert p.experience_level == "novice"  # safe default
        assert p.sessions_count == 0

    def test_from_dict_tolerates_unknown_level(self):
        p = UserProfile.from_dict({"operator_id": "x", "experience_level": "gibberish"})
        assert p.experience_level == "novice"  # falls back, doesn't crash

    def test_to_dict_is_json_serializable(self):
        p = UserProfile(operator_id="x")
        p.mark_explained("jwt_alg_none")
        # If json.dumps doesn't crash we're good
        as_str = json.dumps(p.to_dict())
        assert "jwt_alg_none" in as_str


# ── Concept tracking ───────────────────────────────────────────────────────

class TestConceptTracking:
    def test_mark_explained_increments(self):
        p = UserProfile(operator_id="x")
        assert "jwt" not in p.concepts_explained
        p.mark_explained("jwt")
        assert p.concepts_explained["jwt"].count == 1
        p.mark_explained("jwt")
        assert p.concepts_explained["jwt"].count == 2

    def test_mark_explained_sets_timestamp(self):
        p = UserProfile(operator_id="x")
        p.mark_explained("jwt")
        ts = p.concepts_explained["jwt"].last
        # Should be parseable ISO-8601
        datetime.fromisoformat(ts)

    def test_has_seen_recent(self):
        p = UserProfile(operator_id="x")
        p.mark_explained("jwt")
        assert p.has_seen("jwt", within_days=1)

    def test_has_seen_old(self):
        p = UserProfile(operator_id="x")
        old = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()
        p.concepts_explained["jwt"] = ConceptStats(count=1, last=old)
        assert not p.has_seen("jwt", within_days=30)

    def test_has_seen_unknown_concept(self):
        p = UserProfile(operator_id="x")
        assert not p.has_seen("never_explained")

    def test_has_seen_handles_corrupt_timestamp(self):
        p = UserProfile(operator_id="x")
        p.concepts_explained["jwt"] = ConceptStats(count=1, last="not-a-timestamp")
        assert not p.has_seen("jwt")  # safe default — don't crash

    def test_mastery_inference_after_threshold(self):
        p = UserProfile(operator_id="x")
        for _ in range(MASTERY_INFERENCE_THRESHOLD):
            p.mark_explained("jwt_basics")
        assert "jwt_basics" in p.concepts_mastered

    def test_mastery_inference_does_not_double_add(self):
        p = UserProfile(operator_id="x")
        for _ in range(MASTERY_INFERENCE_THRESHOLD * 2):
            p.mark_explained("jwt_basics")
        # Should appear exactly once
        assert p.concepts_mastered.count("jwt_basics") == 1

    def test_questioned_resets_mastery(self):
        p = UserProfile(operator_id="x")
        p.mark_mastered("jwt")
        assert p.has_mastered("jwt")
        p.mark_questioned("jwt")
        assert not p.has_mastered("jwt")

    def test_mastery_decays_after_90_days(self):
        p = UserProfile(operator_id="x")
        p.mark_mastered("jwt")
        old_ts = (datetime.now(timezone.utc) - timedelta(days=MASTERY_DECAY_DAYS + 1)).isoformat()
        p.concepts_explained["jwt"] = ConceptStats(count=1, last=old_ts)
        assert not p.has_mastered("jwt")

    def test_skip_list_always_mastered(self):
        p = UserProfile(operator_id="x")
        p.add_skip("what_is_nmap")
        assert p.has_mastered("what_is_nmap")  # even with no explained record

    def test_skip_list_dedup(self):
        p = UserProfile(operator_id="x")
        p.add_skip("x")
        p.add_skip("x")
        p.add_skip("x")
        assert p.skip_explanations.count("x") == 1


# ── Vocab adaptation ───────────────────────────────────────────────────────

class TestVocabAdaptation:
    def test_expert_no_substitution(self):
        p = UserProfile(operator_id="x", experience_level="expert")
        text = "Found RFC1918 IPs on the loopback interface"
        assert p.adapt_text(text) == text   # unchanged

    def test_novice_default_vocab_applied(self):
        p = UserProfile(operator_id="x", experience_level="novice")
        text = "RFC1918 networks include the loopback range"
        out  = p.adapt_text(text)
        assert "RFC1918" not in out  # substituted
        assert "private network IPs" in out

    def test_intermediate_only_explicit_calibration(self):
        p = UserProfile(
            operator_id="x",
            experience_level="intermediate",
            vocab_calibration={"weird_jargon": "plain word"},
        )
        text = "weird_jargon and RFC1918 stuff"
        out  = p.adapt_text(text)
        assert "weird_jargon" not in out      # replaced (operator-specified)
        assert "RFC1918" in out                # NOT replaced (intermediate skips defaults)

    def test_novice_operator_calibration_overrides_default(self):
        # If operator overrides RFC1918 to something else, default is NOT used
        p = UserProfile(
            operator_id="x",
            experience_level="novice",
            vocab_calibration={"RFC1918": "internal IPs"},
        )
        text = "RFC1918 is local"
        out  = p.adapt_text(text)
        assert "internal IPs" in out
        assert "private network IPs" not in out  # default was overridden

    def test_word_boundary_no_partial_match(self):
        # "POST" inside "POSTGRESQL" should NOT match
        p = UserProfile(operator_id="x", experience_level="novice")
        out = p.adapt_text("POSTGRESQL listens on port 5432")
        assert "POSTGRESQL" in out

    def test_word_boundary_punctuation_ok(self):
        # "POST," / "POST." should still match
        p = UserProfile(operator_id="x", experience_level="novice")
        out = p.adapt_text("Use POST, then GET.")
        # Both POST and GET have substitutions in DEFAULT_NOVICE_VOCAB
        assert "POST" not in out
        assert "GET." not in out  # GET's substitution applied

    def test_empty_text_safe(self):
        p = UserProfile(operator_id="x", experience_level="novice")
        assert p.adapt_text("") == ""
        assert p.adapt_text(None) == ""


# ── _word_boundary_replace ────────────────────────────────────────────────

class TestWordBoundaryReplace:
    def test_basic_replace(self):
        assert _word_boundary_replace("foo bar", "foo", "qux") == "qux bar"

    def test_partial_word_skipped(self):
        # 'foo' in 'foobar' should NOT match
        assert _word_boundary_replace("foobar", "foo", "X") == "foobar"

    def test_punctuation_boundary(self):
        assert _word_boundary_replace("foo, bar.", "foo", "X") == "X, bar."

    def test_case_sensitive(self):
        # CVE != cve — preserve intent
        assert _word_boundary_replace("CVE and cve", "CVE", "X") == "X and cve"


# ── Persistence ────────────────────────────────────────────────────────────

class TestPersistence:
    def test_save_creates_file(self, tmp_profile_path):
        p = UserProfile(operator_id="alice")
        p.save(tmp_profile_path)
        assert tmp_profile_path.exists()

    def test_save_creates_parent_dir(self, tmp_path):
        nested = tmp_path / "deeply" / "nested" / "profile.json"
        p = UserProfile(operator_id="alice")
        p.save(nested)
        assert nested.exists()

    def test_load_returns_default_when_file_missing(self, tmp_profile_path):
        assert not tmp_profile_path.exists()
        p = UserProfile.load(tmp_profile_path, operator_id="bob")
        assert p.operator_id == "bob"
        assert p.experience_level == "novice"

    def test_save_load_round_trip(self, tmp_profile_path):
        p1 = UserProfile(operator_id="eros", experience_level="intermediate")
        p1.mark_explained("jwt_alg_none")
        p1.mark_mastered("sql_union_basic")
        p1.add_skip("what_is_nmap")
        p1.save(tmp_profile_path)

        p2 = UserProfile.load(tmp_profile_path)
        assert p2.operator_id == "eros"
        assert p2.experience_level == "intermediate"
        assert "jwt_alg_none" in p2.concepts_explained
        assert "sql_union_basic" in p2.concepts_mastered
        assert "what_is_nmap" in p2.skip_explanations

    def test_corrupt_file_returns_fresh_and_backs_up(self, tmp_profile_path):
        tmp_profile_path.write_text("{not valid json", encoding="utf-8")
        p = UserProfile.load(tmp_profile_path, operator_id="bob")
        # Returned profile is fresh
        assert p.operator_id == "bob"
        assert p.sessions_count == 0
        # Original file was backed up (renamed with .corrupt suffix)
        backups = list(tmp_profile_path.parent.glob("profile.json.corrupt.*"))
        assert backups, "Expected corrupt file to be backed up"

    def test_atomic_write_no_partial_file(self, tmp_profile_path):
        # If save fails mid-write, should NOT leave a half-written profile.json
        p = UserProfile(operator_id="x")
        p.save(tmp_profile_path)
        # Just confirm no .tmp left over after a successful save
        leftover_tmps = list(tmp_profile_path.parent.glob("*.tmp"))
        assert not leftover_tmps

    def test_save_writes_indented_json(self, tmp_profile_path):
        p = UserProfile(operator_id="x")
        p.save(tmp_profile_path)
        text = tmp_profile_path.read_text()
        # Indent=2 means readable, not minified
        assert "\n" in text and "  " in text


# ── Schema migration ──────────────────────────────────────────────────────

class TestSchemaMigration:
    def test_old_schema_migrates_silently(self, tmp_profile_path):
        # Write a v0 profile without schema_version
        old = {"operator_id": "ancient", "experience_level": "novice"}
        tmp_profile_path.write_text(json.dumps(old))
        p = UserProfile.load(tmp_profile_path)
        assert p.schema_version == SCHEMA_VERSION
        assert p.operator_id == "ancient"


# ── Session inference ─────────────────────────────────────────────────────

class TestSessionInference:
    def _audit_event(self, evt_type, data=None):
        return {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": evt_type,
            "data": data or {},
        }

    def test_novice_to_intermediate_promotion(self):
        p = UserProfile(operator_id="x", experience_level="novice")
        events = [self._audit_event("phase_start") for _ in range(10)]
        events.append(self._audit_event("operator_approve"))
        # No questions in 11+ events
        p.update_from_session(events)
        assert p.experience_level == "intermediate"

    def test_intermediate_to_expert_promotion(self):
        p = UserProfile(operator_id="x", experience_level="intermediate")
        events = [self._audit_event("phase_start") for _ in range(20)]
        events.extend([self._audit_event("operator_approve") for _ in range(3)])
        p.update_from_session(events)
        assert p.experience_level == "expert"

    def test_expert_to_intermediate_demotion(self):
        p = UserProfile(operator_id="x", experience_level="expert")
        events = []
        # 5 questions (text contains '?')
        for _ in range(5):
            events.append(self._audit_event("operator_response", {"text": "what is jwt?"}))
        p.update_from_session(events)
        assert p.experience_level == "intermediate"

    def test_no_promotion_with_questions(self):
        p = UserProfile(operator_id="x", experience_level="novice")
        events = [self._audit_event("phase_start") for _ in range(15)]
        events.append(self._audit_event("operator_response", {"text": "what?"}))
        events.append(self._audit_event("operator_approve"))
        p.update_from_session(events)
        # User asked a question, so we don't promote
        assert p.experience_level == "novice"

    def test_empty_audit_no_change(self):
        p = UserProfile(operator_id="x", experience_level="intermediate")
        p.update_from_session([])
        assert p.experience_level == "intermediate"

    def test_begin_session_increments_count(self):
        p = UserProfile(operator_id="x")
        assert p.sessions_count == 0
        p.begin_session()
        assert p.sessions_count == 1
        p.begin_session()
        assert p.sessions_count == 2


# ── Singleton ─────────────────────────────────────────────────────────────

class TestSingleton:
    def test_get_profile_returns_same_instance(self, monkeypatch, tmp_path):
        # Point default_path to a tmp path so we don't touch real ~/.err0rs/
        monkeypatch.setattr(UserProfile, "default_path",
                            classmethod(lambda cls: tmp_path / "profile.json"))
        reset_profile()
        p1 = get_profile()
        p2 = get_profile()
        assert p1 is p2

    def test_reset_forces_reload(self, monkeypatch, tmp_path):
        monkeypatch.setattr(UserProfile, "default_path",
                            classmethod(lambda cls: tmp_path / "profile.json"))
        reset_profile()
        p1 = get_profile()
        reset_profile()
        p2 = get_profile()
        # After reset, should be a new instance (unless content identical)
        # Confirm by mutating p1 and checking p2 doesn't reflect it
        p1.mark_explained("foo")
        assert "foo" in p1.concepts_explained
        # p2 was created after reset, before the mutation — it should be clean
        assert "foo" not in p2.concepts_explained


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
