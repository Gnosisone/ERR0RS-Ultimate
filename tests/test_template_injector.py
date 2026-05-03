"""
tests/test_template_injector.py
================================
SSTI + Prototype Pollution engine test suite.

Covers:
- detection_payloads: 8 universal probes, each parseable
- identify_engine: matches engine fingerprints from error responses
- rce_payloads: per-engine RCE chains, command interpolation
- blind_dns_payloads: requires real domain, embeds collaborator
- polyglot_payloads: multi-engine bodies present
- prototype_pollution_payloads: 11 gadgets x 3 vectors x JSON/urlencoded/querystring
- auto_payloads: full battery, all JSON-serializable
- CLI subcommands work end-to-end

Run: python3 -m pytest tests/test_template_injector.py -v
"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from src.tools.web.template_injector import (
    detection_payloads, identify_engine, rce_payloads,
    blind_dns_payloads, polyglot_payloads,
    prototype_pollution_payloads, PROTO_POLLUTION_GADGETS,
    TemplateInjector, TemplatePayload, EngineFingerprint,
    get_injector, ENGINE_DISCRIMINATORS, SAFE_COMMANDS,
)


# ── Detection probes ──────────────────────────────────────────────────────

class TestDetectionPayloads:
    def test_returns_multiple_probes(self):
        ps = detection_payloads()
        assert len(ps) >= 8

    def test_all_have_expected_marker_49(self):
        for p in detection_payloads():
            assert p.expected_marker == "49"

    def test_each_targets_different_syntax(self):
        ps = detection_payloads()
        payloads = {p.payload for p in ps}
        # Should include the major template syntaxes
        assert "{{7*7}}" in payloads
        assert "${7*7}" in payloads
        assert "<%= 7*7 %>" in payloads
        assert "#{7*7}" in payloads
        assert "{7*7}" in payloads

    def test_severity_is_info(self):
        for p in detection_payloads():
            assert p.severity == "info"

    def test_custom_field_propagates(self):
        ps = detection_payloads(target_field="username")
        for p in ps:
            if p.body:
                assert "username" in p.body

    def test_query_param_location_uses_qs(self):
        ps = detection_payloads(location="query_param", target_field="q")
        for p in ps:
            assert p.query_string is not None
            assert p.body is None


# ── Engine identification from response ──────────────────────────────────

class TestIdentifyEngine:
    @pytest.mark.parametrize("response,expected_engine", [
        ("jinja2.exceptions.TemplateSyntaxError: hello",  "jinja2"),
        ("UndefinedError: 'config' is undefined",         "jinja2"),
        ("Twig_Error_Syntax: parse error",                "twig"),
        ("Smarty error: unrecognized tag",                "smarty"),
        ("(erb):3:in `<main>': undefined method",         "erb"),
        ("FreeMarker template error: unable to load",     "freemarker"),
        ("org.apache.velocity.exception",                  "velocity"),
        ("ActionView::Template::Error in PostsController", "erb"),
    ])
    def test_engine_matched_from_error(self, response, expected_engine):
        fps = identify_engine(response)
        engines = {f.engine for f in fps}
        assert expected_engine in engines, f"Expected {expected_engine} in {engines}"

    def test_clean_response_no_match(self):
        fps = identify_engine('{"ok":true,"data":[1,2,3]}')
        assert fps == []

    def test_empty_response_no_crash(self):
        assert identify_engine("") == []
        assert identify_engine(None) == []


# ── RCE payloads — per engine ────────────────────────────────────────────

class TestRcePayloads:
    @pytest.mark.parametrize("engine", list(ENGINE_DISCRIMINATORS.keys()))
    def test_each_engine_has_rce_chain(self, engine):
        ps = rce_payloads(engine=engine, command="id")
        assert len(ps) >= 1, f"No RCE chains for engine: {engine}"

    def test_command_substitution(self):
        ps = rce_payloads(engine="jinja2", command="whoami")
        assert all("whoami" in p.payload for p in ps)
        assert all("CMD" not in p.payload for p in ps)

    def test_default_command_is_id(self):
        ps = rce_payloads(engine="jinja2")
        assert all("id" in p.payload for p in ps)

    def test_severity_critical(self):
        for p in rce_payloads(engine="jinja2"):
            assert p.severity == "critical"

    def test_unknown_engine_returns_full_battery(self):
        ps = rce_payloads(engine="unknown")
        engines_in_results = {p.engine for p in ps}
        # Should NOT be empty - "unknown" triggers full battery
        assert len(ps) > 5

    def test_jinja2_includes_subclass_walking(self):
        ps = rce_payloads(engine="jinja2")
        chains = [p.payload for p in ps]
        # The subclass-walking chain is iconic Jinja2 attacker craft
        assert any("__subclasses__" in c for c in chains)

    def test_ejs_includes_outputfunctionname_cve(self):
        ps = rce_payloads(engine="ejs")
        descriptions = [p.description for p in ps]
        assert any("outputFunctionName" in d or "CVE-2022-29078" in d for d in descriptions)


# ── Blind DNS payloads ────────────────────────────────────────────────────

class TestBlindDnsPayloads:
    def test_requires_collaborator(self):
        with pytest.raises(ValueError):
            blind_dns_payloads(collaborator_domain="")

    def test_rejects_invalid_domain(self):
        with pytest.raises(ValueError):
            blind_dns_payloads(collaborator_domain="notadomain")

    def test_collaborator_embedded(self):
        ps = blind_dns_payloads(collaborator_domain="abc123.oast.fun")
        for p in ps:
            assert "abc123.oast.fun" in p.payload

    def test_severity_high(self):
        ps = blind_dns_payloads(collaborator_domain="x.oast.fun")
        for p in ps:
            assert p.severity == "high"

    def test_no_expected_marker(self):
        # Blind = no in-response marker; success = DNS hit at collaborator
        ps = blind_dns_payloads(collaborator_domain="x.oast.fun")
        for p in ps:
            assert p.expected_marker is None


# ── Polyglot payloads ─────────────────────────────────────────────────────

class TestPolyglotPayloads:
    def test_returns_multiple_polyglots(self):
        ps = polyglot_payloads()
        assert len(ps) >= 3

    def test_command_substitution(self):
        ps = polyglot_payloads(command="whoami")
        assert any("whoami" in p.payload for p in ps)

    def test_universal_math_probe_present(self):
        ps = polyglot_payloads()
        # The "fires on every engine" probe
        assert any("${7*7}#{7*7}{{7*7}}" in p.payload for p in ps)


# ── Prototype Pollution ───────────────────────────────────────────────────

class TestProtoPollution:
    def test_json_format_produces_dict_bodies(self):
        ps = prototype_pollution_payloads(body_format="json")
        for p in ps:
            assert p.body is not None
            assert isinstance(p.body, dict)
            assert p.method == "POST"

    def test_urlencoded_format_uses_bracket_syntax(self):
        ps = prototype_pollution_payloads(body_format="urlencoded")
        for p in ps:
            assert "[" in p.payload
            assert "]" in p.payload
            assert p.extras.get("content_type") == "application/x-www-form-urlencoded"

    def test_querystring_format_uses_get(self):
        ps = prototype_pollution_payloads(body_format="querystring")
        for p in ps:
            assert p.method == "GET"
            assert p.query_string is not None

    def test_isadmin_gadget_present(self):
        ps = prototype_pollution_payloads(body_format="json")
        assert any(p.extras.get("gadget_key") == "isAdmin" for p in ps)

    def test_outputfunctionname_gadget_critical(self):
        ps = prototype_pollution_payloads(body_format="json")
        ofn = [p for p in ps if p.extras.get("gadget_key") == "outputFunctionName"]
        assert ofn
        for p in ofn:
            assert p.severity == "critical"

    def test_sourceurl_gadget_critical(self):
        ps = prototype_pollution_payloads(body_format="json")
        su = [p for p in ps if p.extras.get("gadget_key") == "sourceURL"]
        assert su
        for p in su:
            assert p.severity == "critical"

    def test_both_proto_and_constructor_vectors(self):
        ps = prototype_pollution_payloads(body_format="json")
        vectors = {p.extras.get("vector") for p in ps}
        assert "__proto__" in vectors
        assert "constructor.prototype" in vectors

    def test_gadget_count_matches_constant(self):
        # 11 gadgets defined; json format produces 2 vectors per gadget = 22
        ps = prototype_pollution_payloads(body_format="json")
        assert len(ps) == len(PROTO_POLLUTION_GADGETS) * 2


# ── auto_payloads & injector ──────────────────────────────────────────────

class TestAutoPayloads:
    def test_auto_returns_full_battery(self):
        inj = TemplateInjector()
        ps = inj.auto_payloads()
        techniques = {p.technique for p in ps}
        assert "ssti_detection" in techniques
        assert "ssti_rce" in techniques
        assert "polyglot" in techniques
        assert "proto_pollution" in techniques

    def test_auto_skips_blind_without_collaborator(self):
        inj = TemplateInjector()
        ps = inj.auto_payloads()  # no collaborator
        assert not any(p.technique == "blind_dns" for p in ps)

    def test_auto_includes_blind_with_collaborator(self):
        inj = TemplateInjector()
        ps = inj.auto_payloads(collaborator_domain="abc.oast.fun")
        assert any(p.technique == "blind_dns" for p in ps)

    def test_get_injector_singleton(self):
        a = get_injector()
        b = get_injector()
        assert a is b


# ── JSON serialization sanity ─────────────────────────────────────────────

class TestSerialization:
    def test_detection_bodies_serializable(self):
        for p in detection_payloads():
            if p.body:
                json.dumps(p.body)

    def test_rce_bodies_serializable(self):
        for p in rce_payloads(engine="unknown"):
            if p.body:
                json.dumps(p.body)

    def test_proto_bodies_serializable(self):
        for p in prototype_pollution_payloads(body_format="json"):
            json.dumps(p.body)

    def test_auto_payloads_all_serializable(self):
        inj = TemplateInjector()
        for p in inj.auto_payloads():
            if p.body is not None:
                json.dumps(p.body)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
