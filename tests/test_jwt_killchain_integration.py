"""
tests/test_jwt_killchain_integration.py
==========================================
Integration tests for JWTBreaker + AutoKillChain wiring.

Covers:
- Native tool registry contains jwt_breaker
- find_jwts_in_text() extracts plausible JWTs from messy multiline strings
- find_jwts_in_prior_outputs() walks a dict of phase outputs
- jwt_breaker_native produces findings when prior outputs contain a JWT
- jwt_breaker_native returns empty (success) when no JWTs found
- Operator-supplied JWT via params['jwt'] gets attacked
- Multi-token output rolls up kid_injection into one finding (not 11)

Run: python3 -m pytest tests/test_jwt_killchain_integration.py -v
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from src.orchestration.native_tools import (
    is_native, list_native_tools, run_native, NativeToolContext,
    find_jwts_in_text, find_jwts_in_prior_outputs,
)
from src.tools.auth.jwt_breaker import pyjwt


# ── Registry ──────────────────────────────────────────────────────────────

class TestRegistry:
    def test_jwt_breaker_registered(self):
        assert is_native("jwt_breaker")

    def test_unknown_tool_not_registered(self):
        assert not is_native("nmap_deep")
        assert not is_native("totally_made_up")

    def test_list_includes_jwt_breaker(self):
        assert "jwt_breaker" in list_native_tools()


# ── Token discovery ───────────────────────────────────────────────────────

class TestJWTDiscovery:
    def test_find_jwt_in_clean_text(self):
        token = pyjwt.encode({"role": "user"}, "mySecret", algorithm="HS256")
        found = find_jwts_in_text(f"Authorization: Bearer {token}")
        assert token in found

    def test_find_jwt_in_messy_curl_output(self):
        token = pyjwt.encode({"x": 1}, "secret", algorithm="HS256")
        blob = f"""\
* TLS connection established
< HTTP/2 200
< content-type: application/json
< set-cookie: token={token}; HttpOnly
{{"user":"alice","jwt":"{token}","ok":true}}
"""
        found = find_jwts_in_text(blob)
        assert len(found) == 1   # de-duplicated
        assert found[0] == token

    def test_find_no_jwt_in_random_text(self):
        # Random base64-looking strings without three dot-separated parts
        assert find_jwts_in_text("hello world") == []
        assert find_jwts_in_text("eyJhbGciOiJIUzI1NiJ9") == []        # only 1 segment
        assert find_jwts_in_text("eyJaaa.eyJbbb") == []                # only 2 segments

    def test_find_multiple_jwts(self):
        t1 = pyjwt.encode({"u": "a"}, "s", algorithm="HS256")
        t2 = pyjwt.encode({"u": "b"}, "s", algorithm="HS256")
        found = find_jwts_in_text(f"first: {t1}\nsecond: {t2}\n")
        assert t1 in found and t2 in found
        assert len(found) == 2

    def test_find_jwts_in_prior_outputs(self):
        token = pyjwt.encode({"x": 1}, "secret", algorithm="HS256")
        outputs = {
            "nmap_deep":  "443/tcp open https",                  # no jwt
            "nuclei":     f"[medium] some token leak: {token}",  # jwt!
            "gobuster":   "/api 200",                            # no jwt
        }
        found = find_jwts_in_prior_outputs(outputs)
        assert len(found) == 1
        source, jwt = found[0]
        assert source == "nuclei"
        assert jwt == token


# ── Native tool dispatch ──────────────────────────────────────────────────

class TestJWTBreakerNative:
    def _ctx(self, prior_outputs=None, params=None) -> NativeToolContext:
        return NativeToolContext(
            target="http://localhost:3000",
            target_parts={"ip": "localhost", "port": "3000",
                          "url": "http://localhost:3000",
                          "url_host": "localhost:3000", "scheme": "http",
                          "ip_port": "localhost:3000",
                          "raw": "http://localhost:3000"},
            phase_id="vuln_assessment",
            params=params or {},
            prior_outputs=prior_outputs or {},
            prior_findings=[],
        )

    def test_no_jwts_means_no_findings(self):
        ctx = self._ctx(prior_outputs={"nmap_deep": "443/tcp open"})
        result = run_native("jwt_breaker", ctx)
        assert result.success
        assert result.findings == []
        assert "No JWTs detected" in result.raw_output

    def test_jwt_in_prior_output_gets_attacked(self):
        token = pyjwt.encode({"role": "user"}, "mySecret", algorithm="HS256")
        ctx = self._ctx(prior_outputs={
            "nuclei": f"[info] JWT in response: {token}",
        })
        result = run_native("jwt_breaker", ctx)
        assert result.success
        # We should have findings from at least: jwt_discovery + none_alg + hs256_crack + kid_injection
        techniques = {f.get("technique") for f in result.findings}
        assert "jwt_discovery" in techniques
        assert "none_alg" in techniques
        assert "hs256_crack" in techniques
        assert "kid_injection" in techniques

    def test_hs256_crack_finds_secret(self):
        token = pyjwt.encode({"role": "user"}, "mySecret", algorithm="HS256")
        ctx = self._ctx(prior_outputs={"nuclei": token})
        result = run_native("jwt_breaker", ctx)

        crack = next(f for f in result.findings
                     if f.get("technique") == "hs256_crack")
        assert crack["secret"] == "mySecret"
        assert crack["forged_token"] is not None
        assert crack["severity"] == "critical"

    def test_kid_injection_rolls_up_to_one_finding(self):
        # JWTBreaker.try_kid_injection produces 11 variants; we want ONE
        # consolidated finding in the report (not 11 noisy entries)
        token = pyjwt.encode({"role": "user"}, "mySecret", algorithm="HS256")
        ctx = self._ctx(prior_outputs={"nuclei": token})
        result = run_native("jwt_breaker", ctx)

        kid_findings = [f for f in result.findings
                        if f.get("technique") == "kid_injection"]
        assert len(kid_findings) == 1, "kid_injection must roll up to ONE finding"
        # But the rollup must record the variant count
        assert kid_findings[0].get("variants", 0) > 1

    def test_operator_supplied_jwt_via_params(self):
        token = pyjwt.encode({"role": "user"}, "secret", algorithm="HS256")
        ctx = self._ctx(prior_outputs={}, params={"jwt": token})
        result = run_native("jwt_breaker", ctx)
        assert result.success
        techniques = {f.get("technique") for f in result.findings}
        assert "hs256_crack" in techniques

    def test_target_claims_param_is_respected(self):
        token = pyjwt.encode({"role": "user"}, "mySecret", algorithm="HS256")
        ctx = self._ctx(
            prior_outputs={"nuclei": token},
            params={"jwt_target_claims": {"role": "superadmin", "kingmode": True}},
        )
        result = run_native("jwt_breaker", ctx)
        crack = next(f for f in result.findings
                     if f.get("technique") == "hs256_crack")
        # The forged token should contain superadmin
        from src.tools.auth.jwt_breaker import JWTBreaker
        forged = JWTBreaker().decode(crack["forged_token"])
        assert forged.claims["role"] == "superadmin"
        assert forged.claims["kingmode"] is True

    def test_jwt_severities_all_present(self):
        token = pyjwt.encode({"role": "user"}, "mySecret", algorithm="HS256")
        ctx = self._ctx(prior_outputs={"nuclei": token})
        result = run_native("jwt_breaker", ctx)

        sev_by_tech = {f["technique"]: f["severity"]
                       for f in result.findings if "technique" in f}
        # Critical findings — auth bypass / full forgery
        assert sev_by_tech.get("none_alg")    == "critical"
        assert sev_by_tech.get("hs256_crack") == "critical"
        # High — conditional
        assert sev_by_tech.get("kid_injection") == "high"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
