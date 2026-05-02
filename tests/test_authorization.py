"""
tests/test_authorization.py
============================
Authorization gate test suite. The most important tests in the project.

Covers:
- ALWAYS_ALLOWED targets (loopback, RFC1918) authorize without flags or prompts
- REQUIRES_CONFIRM (public IPs) refuse without flag, refuse without 'yes' prompt
- ALWAYS_REFUSED (.gov, .mil, .edu, US DoD CIDR) refuse without override
- Bypass attempts (localhost.evil.com, 127.0.0.1.attacker.com) refused
- IDN homograph attempts refused
- Override-refused requires justification of >=20 chars
- Non-interactive mode never silently authorizes external targets

Run: python3 -m pytest tests/test_authorization.py -v
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from src.orchestration.authorization import (
    authorize, classify_target, TargetClass,
    AuthorizationResult, _extract_host, _is_bypass_attempt,
)


# ── Host extraction ────────────────────────────────────────────────────────

class TestHostExtraction:
    def test_bare_ip(self):
        assert _extract_host("192.168.1.1") == "192.168.1.1"

    def test_ip_with_port(self):
        assert _extract_host("192.168.1.1:8080") == "192.168.1.1"

    def test_bare_hostname(self):
        assert _extract_host("example.com") == "example.com"

    def test_http_url(self):
        assert _extract_host("http://example.com") == "example.com"

    def test_https_url_with_port_and_path(self):
        assert _extract_host("https://example.com:8443/admin") == "example.com"

    def test_localhost(self):
        assert _extract_host("localhost") == "localhost"

    def test_localhost_with_port(self):
        assert _extract_host("localhost:3000") == "localhost"

    def test_ipv6_brackets(self):
        assert _extract_host("[::1]:3000") == "::1"

    def test_hostname_with_path(self):
        assert _extract_host("example.com/admin/panel") == "example.com"

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            _extract_host("")


# ── Classification ─────────────────────────────────────────────────────────

class TestClassification:
    def test_loopback_allowed(self):
        cls, _, _ = classify_target("127.0.0.1")
        assert cls == TargetClass.ALWAYS_ALLOWED

    def test_loopback_localhost_allowed(self):
        cls, _, _ = classify_target("localhost")
        assert cls == TargetClass.ALWAYS_ALLOWED

    def test_loopback_with_port_allowed(self):
        cls, _, _ = classify_target("http://localhost:3000")
        assert cls == TargetClass.ALWAYS_ALLOWED

    def test_rfc1918_192_allowed(self):
        cls, _, _ = classify_target("192.168.1.50")
        assert cls == TargetClass.ALWAYS_ALLOWED

    def test_rfc1918_10_allowed(self):
        cls, _, _ = classify_target("10.0.0.5")
        assert cls == TargetClass.ALWAYS_ALLOWED

    def test_rfc1918_172_allowed(self):
        cls, _, _ = classify_target("172.16.0.1")
        assert cls == TargetClass.ALWAYS_ALLOWED

    def test_link_local_allowed(self):
        cls, _, _ = classify_target("169.254.1.1")
        assert cls == TargetClass.ALWAYS_ALLOWED

    def test_us_dod_ip_refused(self):
        # 6.0.0.1 → US Army space
        cls, reason, _ = classify_target("6.0.0.1")
        assert cls == TargetClass.ALWAYS_REFUSED
        assert "protected" in reason.lower()

    def test_us_disa_ip_refused(self):
        cls, _, _ = classify_target("214.0.0.1")
        assert cls == TargetClass.ALWAYS_REFUSED


# ── Bypass attempts ────────────────────────────────────────────────────────

class TestBypassAttempts:
    """These hosts LOOK local but resolve elsewhere. ALL must be refused."""

    def test_localhost_subdomain(self):
        # localhost.evil.com is owned by attacker, often resolves to attacker IP
        assert _is_bypass_attempt("localhost.evil.com") is not None

    def test_127_subdomain(self):
        assert _is_bypass_attempt("127.0.0.1.attacker.com") is not None

    def test_192_subdomain(self):
        assert _is_bypass_attempt("192.168.1.1.evil.com") is not None

    def test_10_subdomain(self):
        assert _is_bypass_attempt("10.0.0.1.evil.com") is not None

    def test_at_sign_in_host(self):
        assert _is_bypass_attempt("user@evil.com") is not None

    def test_unc_path(self):
        assert _is_bypass_attempt("\\\\server\\share") is not None

    def test_idn_homograph(self):
        # Cyrillic 'а' instead of Latin 'a' — common phishing trick
        assert _is_bypass_attempt("exаmple.com") is not None

    def test_legitimate_local_passes(self):
        assert _is_bypass_attempt("localhost") is None
        assert _is_bypass_attempt("127.0.0.1") is None
        assert _is_bypass_attempt("192.168.1.1") is None

    def test_classify_bypass_refused(self):
        cls, reason, _ = classify_target("localhost.evil.com")
        assert cls == TargetClass.ALWAYS_REFUSED
        assert "bypass" in reason.lower()


# ── Refused TLDs ───────────────────────────────────────────────────────────

class TestRefusedTLDs:
    @pytest.mark.parametrize("host", [
        "whitehouse.gov",
        "irs.gov",
        "army.mil",
        "navy.mil",
        "mit.edu",
        "stanford.edu",
        "parliament.gov.uk",
        "ato.gov.au",
        "ox.ac.uk",
    ])
    def test_protected_tlds_refused(self, host):
        cls, reason, _ = classify_target(f"http://{host}")
        assert cls == TargetClass.ALWAYS_REFUSED, f"{host}: {reason}"
        assert "TLD" in reason or "tld" in reason.lower()


# ── Authorize() decision logic ─────────────────────────────────────────────

class TestAuthorizeAllowed:
    def test_localhost_authorizes_no_flag(self):
        r = authorize("http://localhost:3000", operator="eros")
        assert r.authorized is True
        assert r.target_class == TargetClass.ALWAYS_ALLOWED

    def test_rfc1918_authorizes_no_prompt(self):
        # Even without TTY, RFC1918 just works
        r = authorize("192.168.1.50", operator="eros", interactive=False)
        assert r.authorized is True


class TestAuthorizeRefused:
    def test_gov_refused_without_override(self):
        r = authorize("http://whitehouse.gov", operator="eros",
                      have_authorization_flag=True)
        assert r.authorized is False
        assert "REFUSED" in r.reason

    def test_dod_ip_refused_without_override(self):
        r = authorize("http://6.0.0.1", operator="eros",
                      have_authorization_flag=True)
        assert r.authorized is False

    def test_gov_refused_with_override_no_justification(self):
        r = authorize("http://whitehouse.gov", operator="eros",
                      have_authorization_flag=True,
                      override_refused=True,
                      justification="too short")
        assert r.authorized is False
        assert "justification" in r.reason.lower()

    def test_gov_authorized_with_full_override(self):
        r = authorize(
            "http://whitehouse.gov",
            operator="eros",
            have_authorization_flag=True,
            override_refused=True,
            justification="Engagement under written contract #2026-001 with target's CISO",
        )
        assert r.authorized is True
        assert r.justification is not None
        assert "OVERRIDE" in r.reason

    def test_bypass_attempt_refused_even_with_all_flags(self):
        r = authorize("http://localhost.evil.com", operator="eros",
                      have_authorization_flag=True,
                      interactive=False)
        assert r.authorized is False
        assert r.target_class == TargetClass.ALWAYS_REFUSED


class TestAuthorizeRequiresConfirm:
    def test_public_ip_refused_without_flag(self):
        # 8.8.8.8 is Google DNS — public, won't have RFC1918 escape hatch
        r = authorize("http://8.8.8.8", operator="eros",
                      have_authorization_flag=False,
                      interactive=False)
        assert r.authorized is False
        assert "i-have-authorization" in r.reason

    def test_public_ip_refused_non_interactive_with_flag(self):
        # Even with the flag, non-interactive must refuse without explicit override
        r = authorize("http://8.8.8.8", operator="eros",
                      have_authorization_flag=True,
                      interactive=False)
        assert r.authorized is False
        assert "interactive" in r.reason.lower()

    def test_public_ip_refused_when_user_says_no(self):
        r = authorize(
            "http://8.8.8.8",
            operator="eros",
            have_authorization_flag=True,
            interactive=True,
            _input_fn=lambda _: "no",
            _print_fn=lambda *a, **k: None,
        )
        assert r.authorized is False

    def test_public_ip_refused_when_user_says_yeah(self):
        # Must type EXACTLY 'yes', not 'yeah', 'y', 'sure', etc.
        for ans in ("y", "Y", "Yes", "YES", "yeah", "sure", "ok", ""):
            r = authorize(
                "http://8.8.8.8",
                operator="eros",
                have_authorization_flag=True,
                interactive=True,
                _input_fn=lambda _, a=ans: a,
                _print_fn=lambda *a, **k: None,
            )
            assert r.authorized is False, f"Should have refused for answer {ans!r}"

    def test_public_ip_authorized_when_user_says_yes(self):
        r = authorize(
            "http://8.8.8.8",
            operator="eros",
            have_authorization_flag=True,
            interactive=True,
            _input_fn=lambda _: "yes",
            _print_fn=lambda *a, **k: None,
        )
        assert r.authorized is True
        assert "AUTHORIZED" in r.reason


class TestAuthorizationResultStructure:
    def test_result_has_timestamp(self):
        r = authorize("localhost", operator="eros")
        assert r.timestamp is not None
        assert "T" in r.timestamp  # ISO 8601

    def test_result_has_operator(self):
        r = authorize("localhost", operator="alice")
        assert r.operator == "alice"

    def test_result_has_target(self):
        r = authorize("http://127.0.0.1:3000", operator="eros")
        assert r.target == "http://127.0.0.1:3000"
        assert r.resolved_ip == "127.0.0.1"


# ── Pytest entry point ─────────────────────────────────────────────────────

if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
