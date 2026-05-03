"""
Template injection native tool — wraps src.tools.web.template_injector for
AutoKillChain dispatch.

Triggered as part of vuln_assessment phase. Strategy:
  1. Scan prior phase outputs for engine fingerprints (error messages)
  2. Scan prior phase outputs for echo'd math eval (SSTI confirmed)
  3. Generate the full payload battery — RCE chains for known engines,
     full battery for unknowns, plus prototype-pollution gadgets
  4. Roll up by (technique, engine) so the report stays clean

Note: Like JWTBreaker and NoSQLInjector, this DOES NOT make network calls.
It produces payloads. Delivery happens in the exploitation phase, gated
by the authorization layer.

Author: Gary Holden Schneider (Eros) | Sprint 03
"""

from __future__ import annotations

import re
from . import register, NativeToolContext, NativeToolResult


_SEVERITY_MAP = {
    "ssti_detection":  "info",
    "ssti_rce":        "critical",
    "blind_dns":       "high",
    "polyglot":        "high",
    "proto_pollution": "high",   # individual payloads override to critical for RCE gadgets
}

# Math-eval echoes that indicate SSTI is confirmed (server interpreted our probe)
_MATH_ECHO_PATTERNS = [
    re.compile(r"\b49\b"),                     # {{7*7}} → 49
    re.compile(r"\b7777777\b"),                # {{7*'7'}} → 7777777 in Jinja2
]


@register("template_injector")
def template_injector_native(ctx: NativeToolContext) -> NativeToolResult:
    """
    Walk prior phase outputs for SSTI fingerprints / math-eval echoes,
    then generate the full payload battery. Each (technique, engine)
    combo gets ONE rolled-up finding.
    """
    try:
        from src.tools.web.template_injector import (
            identify_engine, TemplateInjector,
        )
    except ImportError as e:
        return NativeToolResult(
            tool_id="template_injector",
            success=False,
            error=f"template_injector module unavailable: {e}",
        )

    inj = TemplateInjector()

    # ── Detection: scan prior outputs for engine fingerprints ─────────
    fingerprints: list[dict] = []
    math_echoes: list[str] = []

    for tool_id, output in (ctx.prior_outputs or {}).items():
        if not isinstance(output, str):
            continue
        # Engine error-message fingerprints
        for fp in identify_engine(output):
            fingerprints.append({"source": tool_id, "fingerprint": fp})
        # Math-eval echo detection (confirms a probe was reflected and evaluated)
        for pat in _MATH_ECHO_PATTERNS:
            if pat.search(output):
                math_echoes.append(tool_id)
                break

    raw_lines: list[str] = []
    findings: list[dict] = []

    if fingerprints:
        engines = sorted({f["fingerprint"].engine for f in fingerprints})
        raw_lines.append(f"[+] Template engine(s) fingerprinted: {', '.join(engines)}")
        for f in fingerprints[:10]:
            fp = f["fingerprint"]
            raw_lines.append(f"    {fp.engine} ({fp.confidence}) "
                             f"in {f['source']}: {fp.indicator!r}")
            findings.append({
                "title":     f"Template engine fingerprinted: {fp.engine}",
                "severity":  "info",
                "detail":    f"Source: {f['source']} | {fp.detail}",
                "technique": "ssti_engine_id",
                "engine":    fp.engine,
                "tool":      "template_injector",
            })

    if math_echoes:
        raw_lines.append(f"[!] Math-eval echo detected in: {', '.join(set(math_echoes))} "
                         "— SSTI HIGHLY LIKELY CONFIRMED")

    if not fingerprints and not math_echoes:
        raw_lines.append("[*] No SSTI fingerprints in prior output. "
                         "Generating speculative payload battery anyway.")

    # ── Payload generation: full battery ──────────────────────────────
    endpoint     = ctx.params.get("endpoint",            "/")
    target_field = ctx.params.get("target_field",        "q")
    command      = ctx.params.get("ssti_command",        "id")
    collaborator = ctx.params.get("collaborator_domain")

    payloads = inj.auto_payloads(
        endpoint=endpoint,
        target_field=target_field,
        command=command,
        collaborator_domain=collaborator,
        include_proto_pollution=ctx.params.get("include_proto_pollution", True),
    )

    # ── Roll up by (technique, engine) ────────────────────────────────
    by_key: dict[tuple[str, str], dict] = {}
    for p in payloads:
        key = (p.technique, p.engine)
        if key not in by_key:
            sev = p.severity   # use the payload's actual severity (proto_pollution
                                # has critical for RCE gadgets, high for others)
            by_key[key] = {
                "title":      f"SSTI/PP: {p.technique} — {p.engine}",
                "severity":   sev,
                "technique":  p.technique,
                "engine":     p.engine,
                "detail":     p.description,
                "count":      0,
                "examples":   [],
                "method":     p.method,
                "first_path": p.extras.get("path"),
                "tool":       "template_injector",
            }
        bucket = by_key[key]
        bucket["count"] += 1
        # Escalate severity if any payload in the bucket is critical
        if p.severity == "critical" and bucket["severity"] != "critical":
            bucket["severity"] = "critical"
        if len(bucket["examples"]) < 3:
            ex = {
                "method":   p.method,
                "location": p.location,
                "payload":  p.payload[:300],   # cap noise
            }
            if p.body is not None:
                ex["body"] = p.body
            if p.query_string:
                ex["query_string"] = p.query_string
            if p.expected_marker:
                ex["expected_marker"] = p.expected_marker
            bucket["examples"].append(ex)

    for (tech, engine), bucket in by_key.items():
        if bucket["count"] > len(bucket["examples"]):
            bucket["detail"] = (
                f"{bucket['count']} payload variants generated. "
                f"First example: {bucket['detail']}"
            )
        findings.append(bucket)
        raw_lines.append(
            f"    [{bucket['severity'].upper():<8}] {tech} ({engine}): "
            f"{bucket['count']} payloads queued"
        )

    return NativeToolResult(
        tool_id="template_injector",
        success=True,
        raw_output="\n".join(raw_lines),
        findings=findings,
    )
