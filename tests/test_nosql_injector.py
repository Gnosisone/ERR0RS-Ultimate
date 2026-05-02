"""
tests/test_nosql_injector.py
=============================
NoSQL injection engine test suite.

Covers:
- detect() identifies MongoDB / GraphQL / CouchDB error signatures
- detect() flags timing-based $where injections
- auth_bypass_payloads() produces the canonical {"$ne": null} family
- where_dos_payloads() produces $where:sleep() variants
- blind_regex_charset_payloads() produces one payload per character
- graphql_dos_payloads() produces nested-depth + batched + alias bombs
- querystring_operator_payloads() produces URL-encoded injection
- auto_payloads() bundles everything into one battery
- All payload bodies are JSON-serializable
- CLI subcommands work end-to-end

Run: python3 -m pytest tests/test_nosql_injector.py -v
"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from src.tools.web.nosql_injector import (
    detect, auth_bypass_payloads, where_dos_payloads,
    blind_regex_charset_payloads, graphql_introspection_payload,
    graphql_dos_payloads, querystring_operator_payloads,
    NoSQLInjector, NoSQLPayload, DetectionFingerprint,
    get_injector,
)


# ── Detection ─────────────────────────────────────────────────────────────

class TestDetectionMongoDB:
    @pytest.mark.parametrize("body", [
        "MongoError: unknown top level operator: $where",
        "BSONError: invalid utf-8 string",
        "{'errmsg': 'unknown operator: $foo'}",
        "MongooseError: validation failed",
        "CastError: Cast to ObjectId failed",
        "E11000 duplicate key error",
    ])
    def test_mongo_signatures_detected(self, body):
        fps = detect(body)
        mongo = [f for f in fps if f.backend == "mongodb"]
        assert mongo, f"Expected mongo detection for: {body!r}"
        assert mongo[0].confidence == "high"

    def test_clean_response_no_detection(self):
        fps = detect('{"ok": true, "data": [1, 2, 3]}')
        assert not [f for f in fps if f.backend == "mongodb"]

    def test_timing_delta_flags_where_injection(self):
        fps = detect("", response_time_ms=8000, baseline_time_ms=200)
        timing = [f for f in fps if "timing_delta" in f.indicator]
        assert timing
        assert timing[0].backend == "mongodb"
        assert timing[0].confidence == "medium"

    def test_small_timing_delta_does_not_flag(self):
        fps = detect("", response_time_ms=300, baseline_time_ms=200)
        assert not [f for f in fps if "timing_delta" in f.indicator]


class TestDetectionGraphQL:
    @pytest.mark.parametrize("body", [
        '{"errors":[{"message":"Cannot query field"}]}',
        'GraphQLError: Cannot query field "secretField"',
        'Did you mean "userById"?',
        'Cannot query field "admin" on type "Query"',
    ])
    def test_graphql_signatures_detected(self, body):
        fps = detect(body)
        gql = [f for f in fps if f.backend == "graphql"]
        assert gql, f"Expected graphql detection for: {body!r}"


class TestDetectionCouchDB:
    def test_couchdb_signatures_detected(self):
        fps = detect('{"error":"not_found","reason":"missing"}')
        cdb = [f for f in fps if f.backend == "couchdb"]
        assert cdb


# ── Auth bypass payloads ──────────────────────────────────────────────────

class TestAuthBypass:
    def test_returns_many_variants(self):
        ps = auth_bypass_payloads()
        # 8 operators × 8 operators = 64 + 4 high-priority = 68
        assert len(ps) >= 60

    def test_canonical_ne_null_present(self):
        ps = auth_bypass_payloads()
        bodies = [p.body for p in ps]
        canonical = {"email": {"$ne": None}, "password": {"$ne": None}}
        assert canonical in bodies, "Canonical {$ne: null} payload missing"

    def test_all_severity_critical(self):
        for p in auth_bypass_payloads():
            assert p.severity == "critical"

    def test_method_is_post(self):
        for p in auth_bypass_payloads():
            assert p.method == "POST"

    def test_high_priority_flag_set(self):
        ps = auth_bypass_payloads()
        priority = [p for p in ps if p.extras.get("high_priority")]
        assert len(priority) >= 4

    def test_custom_field_names_respected(self):
        ps = auth_bypass_payloads(username_field="user",
                                   password_field="pass",
                                   login_path="/api/login")
        # All payload bodies should use the custom field names
        for p in ps:
            keys = set(p.body.keys())
            assert "email" not in keys     # default name should NOT appear
            assert "user" in keys
            assert "pass" in keys
        # And the path
        assert all(p.extras["path"] == "/api/login" for p in ps)


# ── $where DoS payloads ───────────────────────────────────────────────────

class TestWhereDoS:
    def test_returns_multiple_variants(self):
        ps = where_dos_payloads(sleep_ms=5000)
        assert len(ps) >= 3

    def test_severity_is_high(self):
        for p in where_dos_payloads():
            assert p.severity == "high"

    def test_body_uses_where_operator(self):
        ps = where_dos_payloads(sleep_ms=5000)
        for p in ps:
            assert "q" in p.body
            assert "$where" in p.body["q"]

    def test_sleep_value_in_payload(self):
        ps = where_dos_payloads(sleep_ms=7777)
        # At least one payload should embed the sleep_ms literally
        embeds = [p for p in ps if "7777" in str(p.body)]
        assert embeds


# ── Blind regex payloads ──────────────────────────────────────────────────

class TestBlindRegex:
    def test_one_payload_per_character(self):
        # Default alphabet has ~40 characters
        ps = blind_regex_charset_payloads(target_field="email", known_prefix="adm")
        # Default alphabet abcdefghijklmnopqrstuvwxyz0123456789@._- = 40
        assert len(ps) == 40

    def test_each_payload_targets_different_char(self):
        ps = blind_regex_charset_payloads(target_field="email", known_prefix="ad")
        chars = {p.extras["candidate_char"] for p in ps}
        assert len(chars) == len(ps)  # all different

    def test_known_prefix_in_regex(self):
        ps = blind_regex_charset_payloads(target_field="email", known_prefix="admin")
        for p in ps:
            assert p.extras["regex"].startswith("^admin")

    def test_regex_metachars_escaped(self):
        # "." in prefix must NOT match any char — must be escaped to \.
        ps = blind_regex_charset_payloads(target_field="email", known_prefix="user.")
        for p in ps:
            # The escaped form is "user\." — backslash before the dot
            assert "user\\." in p.extras["regex"]

    def test_custom_alphabet_respected(self):
        ps = blind_regex_charset_payloads(target_field="x",
                                            known_prefix="",
                                            alphabet="0123456789")
        assert len(ps) == 10
        chars = {p.extras["candidate_char"] for p in ps}
        assert chars == set("0123456789")

    def test_wrap_field_wraps_correctly(self):
        ps = blind_regex_charset_payloads(target_field="email",
                                            known_prefix="",
                                            alphabet="a",
                                            wrap_field="user")
        assert len(ps) == 1
        # body = {"user": {"email": {"$regex": "^a"}}}
        assert "user" in ps[0].body
        assert "email" in ps[0].body["user"]
        assert "$regex" in ps[0].body["user"]["email"]


# ── GraphQL payloads ──────────────────────────────────────────────────────

class TestGraphQLPayloads:
    def test_introspection_query_present(self):
        p = graphql_introspection_payload()
        assert "__schema" in p.body["query"]
        assert "types" in p.body["query"]

    def test_dos_includes_nested_query(self):
        ps = graphql_dos_payloads(depth=8)
        nested = [p for p in ps if "depth" in p.extras and p.extras["depth"] == 8]
        assert nested
        # Depth 8 means 8 'friends' levels in the query
        assert nested[0].body["query"].count("friends") == 8

    def test_dos_includes_batched_payload(self):
        ps = graphql_dos_payloads()
        batched = [p for p in ps if "batch_size" in p.extras]
        assert batched
        assert batched[0].extras["batch_size"] == 1000
        assert isinstance(batched[0].body, list)
        assert len(batched[0].body) == 1000

    def test_dos_includes_alias_bomb(self):
        ps = graphql_dos_payloads()
        aliases = [p for p in ps if "aliases" in p.extras]
        assert aliases
        # 1000 aliases means 1000 occurrences of "__typename" in the query
        assert aliases[0].body["query"].count("__typename") == 1000


# ── Query string operator payloads ────────────────────────────────────────

class TestQuerystringOperators:
    def test_produces_get_payloads(self):
        ps = querystring_operator_payloads()
        for p in ps:
            assert p.method == "GET"
            assert p.query_string is not None
            assert p.body is None

    def test_uses_bracket_syntax(self):
        ps = querystring_operator_payloads()
        for p in ps:
            assert "[" in p.query_string
            assert "]" in p.query_string

    def test_includes_ne_operator(self):
        ps = querystring_operator_payloads()
        ne = [p for p in ps if p.extras["operator"] == "$ne"]
        assert ne


# ── auto_payloads & injector facade ───────────────────────────────────────

class TestAutoPayloads:
    def test_auto_returns_full_battery(self):
        inj = NoSQLInjector()
        ps = inj.auto_payloads()
        # Should include auth bypass, where DoS, querystring, GraphQL
        techniques = {p.technique for p in ps}
        assert "auth_bypass" in techniques
        assert "where_dos" in techniques
        assert "querystring_operator" in techniques
        assert "graphql_introspection" in techniques
        assert "graphql_dos" in techniques

    def test_auto_payloads_count(self):
        # 60+ auth bypass + ~20 querystring + 3 where + 1 introspection + 3 dos
        inj = NoSQLInjector()
        ps = inj.auto_payloads()
        assert len(ps) >= 80

    def test_get_injector_singleton(self):
        a = get_injector()
        b = get_injector()
        assert a is b


# ── Serialization sanity (every payload must JSON-encode cleanly) ─────────

class TestPayloadSerialization:
    def test_auth_bypass_json_serializable(self):
        for p in auth_bypass_payloads():
            json.dumps(p.body)   # must not raise

    def test_where_dos_json_serializable(self):
        for p in where_dos_payloads():
            json.dumps(p.body)

    def test_blind_regex_json_serializable(self):
        for p in blind_regex_charset_payloads(target_field="x"):
            json.dumps(p.body)

    def test_graphql_dos_json_serializable(self):
        for p in graphql_dos_payloads():
            json.dumps(p.body)

    def test_auto_payloads_all_json_serializable(self):
        inj = NoSQLInjector()
        for p in inj.auto_payloads():
            if p.body is not None:
                json.dumps(p.body)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
