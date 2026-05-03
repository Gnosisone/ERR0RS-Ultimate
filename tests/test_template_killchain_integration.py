"""
tests/test_template_killchain_integration.py
=============================================
Integration tests for TemplateInjector + AutoKillChain wiring.

Covers:
- template_injector registered in native registry
- engine fingerprint detected in prior outputs
- math-eval echo detected in prior outputs
- speculative payloads still generated when no fingerprints found
- per-(technique, engine) findings rolled up cleanly
- proto_pollution RCE gadgets escalate severity to critical
- custom params (endpoint, command, collaborator) propagate

Run: python3 -m pytest tests/test_template_killchain_integration.py -v
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from src.orchestration.native_tools import (
    is_native, list_native_tools, run_native, NativeToolContext,
)


def _ctx(prior_outputs=None, params=None) -> NativeToolContext:
    return NativeToolContext(
        target="http://localhost:3000",
        target_parts={"ip":"localhost","port":"3000",
                      "url":"http://localhost:3000",
                      "url_host":"localhost:3000","scheme":"http",
                      "ip_port":"localhost:3000",
                      "raw":"http://localhost:3000"},
        phase_id="vuln_assessment",
        params=params or {},
        prior_outputs=prior_outputs or {},
        prior_findings=[],
    )


# ── Registry ──────────────────────────────────────────────────────────────

class TestRegistry:
    def test_template_injector_registered(self):
        assert is_native("template_injector")

    def test_all_three_native_tools_listed(self):
        tools = list_native_tools()
        assert "jwt_breaker" in tools
        assert "nosql_injector" in tools
        assert "template_injector" in tools


# ── Detection branch ──────────────────────────────────────────────────────

class TestDetectionBranch:
    def test_jinja2_error_in_prior_output_detected(self):
        ctx = _ctx(prior_outputs={
            "nuclei": "TemplateSyntaxError: jinja2.exceptions.UndefinedError",
        })
        result = run_native("template_injector", ctx)
        assert result.success
        engine_id = [f for f in result.findings
                     if f.get("technique") == "ssti_engine_id"]
        assert engine_id
        assert engine_id[0]["engine"] == "jinja2"

    def test_freemarker_error_detected(self):
        ctx = _ctx(prior_outputs={
            "nuclei": "FreeMarker template error: cannot resolve variable",
        })
        result = run_native("template_injector", ctx)
        engines = {f["engine"] for f in result.findings
                   if f.get("technique") == "ssti_engine_id"}
        assert "freemarker" in engines

    def test_math_echo_signals_confirmed_ssti(self):
        # If a prior probe got reflected and the response contains "49",
        # SSTI is confirmed
        ctx = _ctx(prior_outputs={
            "nuclei": "Response: hello 49 from server"
        })
        result = run_native("template_injector", ctx)
        assert "MATH-EVAL ECHO" in result.raw_output.upper() or \
               "math-eval echo" in result.raw_output.lower()

    def test_no_fingerprints_still_generates_payloads(self):
        ctx = _ctx(prior_outputs={"nmap_deep": "443/tcp open https"})
        result = run_native("template_injector", ctx)
        assert result.success
        # No engine_id findings
        assert not [f for f in result.findings
                    if f.get("technique") == "ssti_engine_id"]
        # But payload findings should exist
        techs = {f.get("technique") for f in result.findings}
        assert "ssti_rce" in techs
        assert "proto_pollution" in techs


# ── Per-(technique, engine) rollup ────────────────────────────────────────

class TestPayloadRollup:
    def test_each_tech_engine_combo_one_finding(self):
        ctx = _ctx()
        result = run_native("template_injector", ctx)
        # Group findings by (technique, engine)
        seen_keys: set = set()
        for f in result.findings:
            tech = f.get("technique")
            if tech == "ssti_engine_id":
                continue
            key = (tech, f.get("engine"))
            assert key not in seen_keys, f"Duplicate finding: {key}"
            seen_keys.add(key)

    def test_ssti_rce_severity_critical(self):
        ctx = _ctx()
        result = run_native("template_injector", ctx)
        rce = [f for f in result.findings if f.get("technique") == "ssti_rce"]
        assert rce
        for f in rce:
            assert f["severity"] == "critical"

    def test_examples_cap_at_three(self):
        ctx = _ctx()
        result = run_native("template_injector", ctx)
        for f in result.findings:
            ex = f.get("examples", [])
            assert len(ex) <= 3, f"Got {len(ex)} examples in {f.get('title')}"


# ── Severity escalation for RCE proto-pollution gadgets ──────────────────

class TestProtoPollutionSeverity:
    def test_proto_pollution_has_critical_findings(self):
        ctx = _ctx()
        result = run_native("template_injector", ctx)
        proto = [f for f in result.findings if f.get("technique") == "proto_pollution"]
        assert proto
        # At least one bucket should be critical (the RCE gadgets — sourceURL/outputFunctionName/etc.)
        criticals = [f for f in proto if f["severity"] == "critical"]
        assert criticals, "Expected at least one critical proto_pollution finding"


# ── Param propagation ─────────────────────────────────────────────────────

class TestParamPropagation:
    def test_custom_command_propagates(self):
        ctx = _ctx(params={"ssti_command": "whoami"})
        result = run_native("template_injector", ctx)
        # The first example in any ssti_rce bucket should contain whoami
        rce = next(f for f in result.findings if f.get("technique") == "ssti_rce")
        first = rce["examples"][0]
        assert "whoami" in first["payload"]

    def test_collaborator_enables_blind_dns(self):
        ctx = _ctx(params={"collaborator_domain": "abc123.oast.fun"})
        result = run_native("template_injector", ctx)
        blind = [f for f in result.findings if f.get("technique") == "blind_dns"]
        assert blind, "Blind DNS findings missing despite collaborator domain"

    def test_no_collaborator_no_blind(self):
        ctx = _ctx()
        result = run_native("template_injector", ctx)
        blind = [f for f in result.findings if f.get("technique") == "blind_dns"]
        assert not blind, "Blind DNS should not fire without collaborator"

    def test_disable_proto_pollution(self):
        ctx = _ctx(params={"include_proto_pollution": False})
        result = run_native("template_injector", ctx)
        proto = [f for f in result.findings if f.get("technique") == "proto_pollution"]
        assert not proto, "Proto pollution should be skipped when disabled"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
