"""
NoSQL native tool — wraps src.tools.web.nosql_injector for AutoKillChain dispatch.

Triggered as part of vuln_assessment phase. Strategy:
  1. Look at prior phase outputs for Mongo/GraphQL error signatures
  2. Generate the full payload battery
  3. Each generated payload becomes a finding with a delivery hint
     (the orchestrator's exploitation phase delivers them)

Note: Like JWTBreaker, this module DOES NOT make network calls of its own.
It produces payloads. Delivery is the exploitation phase's job.

Author: Gary Holden Schneider (Eros) | Sprint 02
"""

from __future__ import annotations

from . import register, NativeToolContext, NativeToolResult


_SEVERITY = {
    "auth_bypass":            "critical",
    "where_dos":              "high",
    "blind_regex":            "high",
    "graphql_dos":            "high",
    "graphql_introspection":  "medium",
    "querystring_operator":   "high",
}


@register("nosql_injector")
def nosql_injector_native(ctx: NativeToolContext) -> NativeToolResult:
    """
    Walk prior phase outputs for NoSQL fingerprints, then generate the
    full payload battery. Each technique gets ONE rolled-up finding.
    """
    try:
        from src.tools.web.nosql_injector import (
            detect, NoSQLInjector,
        )
    except ImportError as e:
        return NativeToolResult(
            tool_id="nosql_injector",
            success=False,
            error=f"nosql_injector module unavailable: {e}",
        )

    inj = NoSQLInjector()

    # ── Detection: scan prior outputs for Mongo / GraphQL fingerprints ────
    fingerprints = []
    for tool_id, output in (ctx.prior_outputs or {}).items():
        if not isinstance(output, str):
            continue
        for fp in detect(output):
            fingerprints.append({"source": tool_id, "fingerprint": fp})

    raw_lines = []
    findings: list[dict] = []

    if fingerprints:
        backends_detected = sorted({f["fingerprint"].backend for f in fingerprints})
        raw_lines.append(f"[+] NoSQL backend(s) detected: {', '.join(backends_detected)}")
        for f in fingerprints[:10]:   # cap noise
            fp = f["fingerprint"]
            raw_lines.append(f"    {fp.backend} ({fp.confidence}) "
                             f"in {f['source']}: {fp.indicator!r}")
            findings.append({
                "title":     f"NoSQL backend detected: {fp.backend}",
                "severity":  "info",
                "detail":    f"Source: {f['source']} | {fp.detail}",
                "technique": "nosql_detection",
                "backend":   fp.backend,
            })
    else:
        raw_lines.append("[*] No NoSQL fingerprint matches in prior output. "
                          "Generating speculative payload battery anyway.")

    # ── Payload generation: full battery, one finding per technique ───────
    # The orchestrator's exploitation phase delivers them; here we just
    # publish them so the report shows what's queued up.
    login_path   = ctx.params.get("login_path",   "/rest/user/login")
    search_path  = ctx.params.get("search_path",  "/rest/products/search")
    graphql_path = ctx.params.get("graphql_path", "/graphql")

    payloads = inj.auto_payloads(
        login_path=login_path,
        search_path=search_path,
        graphql_path=graphql_path,
        username_field=ctx.params.get("username_field", "email"),
        password_field=ctx.params.get("password_field", "password"),
    )

    # Bucket payloads by technique — roll up to one finding per technique
    by_technique: dict[str, dict] = {}
    for p in payloads:
        if p.technique not in by_technique:
            by_technique[p.technique] = {
                "title":      f"NoSQL {p.technique} payloads queued",
                "severity":   _SEVERITY.get(p.technique, "medium"),
                "technique":  p.technique,
                "detail":     p.description,
                "count":      0,
                "examples":   [],
                "method":     p.method,
                "first_path": p.extras.get("path"),
            }
        bucket = by_technique[p.technique]
        bucket["count"] += 1
        if len(bucket["examples"]) < 3:
            ex = {
                "method":   p.method,
                "location": p.location,
                "body":     p.body,
            }
            if p.query_string:
                ex["query_string"] = p.query_string
            bucket["examples"].append(ex)

    for tech, bucket in by_technique.items():
        if bucket["count"] > len(bucket["examples"]):
            bucket["detail"] = (
                f"{bucket['count']} payload variants generated. "
                f"First example: {bucket['detail']}"
            )
        findings.append(bucket)
        raw_lines.append(
            f"    [{bucket['severity'].upper()}] {tech}: "
            f"{bucket['count']} payloads queued"
        )

    return NativeToolResult(
        tool_id="nosql_injector",
        success=True,
        raw_output="\n".join(raw_lines),
        findings=findings,
    )
