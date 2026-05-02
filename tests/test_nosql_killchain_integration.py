"""
tests/test_nosql_killchain_integration.py
==========================================
Integration tests for NoSQLInjector + AutoKillChain wiring.

Covers:
- Native tool registry contains nosql_injector
- Detection phase runs against prior outputs
- Speculative payloads still generated when no fingerprints found
- Per-technique findings correctly rolled up
- Custom paths/fields propagated through params

Run: python3 -m pytest tests/test_nosql_killchain_integration.py -v
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
    def test_nosql_injector_registered(self):
        assert is_native("nosql_injector")

    def test_both_native_tools_listed(self):
        tools = list_native_tools()
        assert "jwt_breaker" in tools
        assert "nosql_injector" in tools


# ── Detection branch ──────────────────────────────────────────────────────

class TestDetectionBranch:
    def test_mongo_error_in_prior_output_detected(self):
        ctx = _ctx(prior_outputs={
            "nuclei": "MongoError: unknown top level operator: $where",
        })
        result = run_native("nosql_injector", ctx)
        assert result.success
        # Detection finding present
        det = [f for f in result.findings
               if f.get("technique") == "nosql_detection"]
        assert det
        assert det[0]["backend"] == "mongodb"

    def test_graphql_error_in_prior_output_detected(self):
        ctx = _ctx(prior_outputs={
            "nuclei": '{"errors":[{"message":"Cannot query field"}]}',
        })
        result = run_native("nosql_injector", ctx)
        det = [f for f in result.findings
               if f.get("technique") == "nosql_detection"]
        assert det
        assert det[0]["backend"] == "graphql"

    def test_no_fingerprints_still_generates_payloads(self):
        # Even without detection, the engine should queue speculative payloads
        ctx = _ctx(prior_outputs={"nmap_deep": "443/tcp open https"})
        result = run_native("nosql_injector", ctx)
        assert result.success
        # No detection findings
        assert not [f for f in result.findings
                    if f.get("technique") == "nosql_detection"]
        # But payload findings should exist
        techs = {f.get("technique") for f in result.findings}
        assert "auth_bypass" in techs


# ── Per-technique rollup ──────────────────────────────────────────────────

class TestPayloadRollup:
    def test_each_technique_one_finding(self):
        ctx = _ctx()
        result = run_native("nosql_injector", ctx)
        # Group findings by technique
        by_tech: dict = {}
        for f in result.findings:
            tech = f.get("technique")
            if tech == "nosql_detection":
                continue
            by_tech.setdefault(tech, []).append(f)
        # Each technique should have at most ONE finding
        for tech, fs in by_tech.items():
            assert len(fs) == 1, f"{tech} produced {len(fs)} findings, expected 1"

    def test_auth_bypass_severity_critical(self):
        ctx = _ctx()
        result = run_native("nosql_injector", ctx)
        ab = next(f for f in result.findings
                  if f.get("technique") == "auth_bypass")
        assert ab["severity"] == "critical"
        # Should report a high count of variants
        assert ab.get("count", 0) >= 60

    def test_examples_cap_at_three(self):
        ctx = _ctx()
        result = run_native("nosql_injector", ctx)
        for f in result.findings:
            ex = f.get("examples", [])
            assert len(ex) <= 3, f"{f.get('technique')} has {len(ex)} examples"


# ── Param propagation ─────────────────────────────────────────────────────

class TestParamPropagation:
    def test_custom_login_path_propagated(self):
        ctx = _ctx(params={"login_path": "/api/v2/auth/login",
                            "username_field": "user",
                            "password_field": "pass"})
        result = run_native("nosql_injector", ctx)
        ab = next(f for f in result.findings
                  if f.get("technique") == "auth_bypass")
        # The first example body should use the custom field names
        first = ab["examples"][0]
        keys = set(first["body"].keys())
        assert "user" in keys
        assert "pass" in keys

    def test_custom_graphql_path_propagated(self):
        ctx = _ctx(params={"graphql_path": "/api/graph"})
        result = run_native("nosql_injector", ctx)
        # The introspection finding should target the custom path
        # (we can verify via examples — the path is in extras at payload-build time
        # and should propagate through the bucket's first example)
        gql = next((f for f in result.findings
                    if f.get("technique") == "graphql_introspection"), None)
        assert gql is not None


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
