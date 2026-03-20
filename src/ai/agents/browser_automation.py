#!/usr/bin/env python3
"""
ERR0RS ULTIMATE – Browser Automation Agent

Responsibilities:
  • Crawl a target web application (depth-limited BFS).
  • Extract forms, input fields, endpoints.
  • Detect low-hanging fruit: comment leaks, header exposures,
    missing security headers, JS library versions.
  • Feed structured data back to the orchestrator so the
    Exploit Generator knows exactly what to target.

Implementation notes:
  • Uses the stdlib http.client for HTTP – no heavy dependencies.
  • If `requests` is available it uses that instead (faster, redirect-aware).
  • All network calls go to the TARGET only – nothing phoned home.
  • Crawl depth and page limit are configurable to avoid runaway scans.
"""

import logging
import re
import time
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    import http.client
    HAS_REQUESTS = False

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class PageResult:
    url             : str
    status_code     : int
    headers         : Dict[str, str] = field(default_factory=dict)
    forms           : List[Dict[str, Any]] = field(default_factory=list)
    links           : List[str]            = field(default_factory=list)
    js_libraries    : List[str]            = field(default_factory=list)
    comments        : List[str]            = field(default_factory=list)
    missing_headers : List[str]            = field(default_factory=list)
    body_snippet    : str = ""             # first 2 KB for quick review


SECURITY_HEADERS = [
    "X-Content-Type-Options",
    "X-Frame-Options",
    "X-XSS-Protection",
    "Strict-Transport-Security",
    "Content-Security-Policy",
    "Cache-Control",
    "Referrer-Policy",
    "Permissions-Policy",
]

# Common JS libraries with version-extract regexes
JS_LIBRARY_PATTERNS = [
    (r"jquery[.\-](\d+\.\d+[\.\d]*)", "jQuery"),
    (r"angular[.\-](\d+\.\d+[\.\d]*)", "AngularJS"),
    (r"react[.\-](\d+\.\d+[\.\d]*)", "React"),
    (r"vue[.\-](\d+\.\d+[\.\d]*)", "Vue.js"),
    (r"bootstrap[.\-](\d+\.\d+[\.\d]*)", "Bootstrap"),
    (r"lodash[.\-](\d+\.\d+[\.\d]*)", "Lodash"),
    (r"express[.\-](\d+\.\d+[\.\d]*)", "Express"),
    (r"wordpress", "WordPress"),
    (r"drupal", "Drupal"),
    (r"joomla", "Joomla"),
]


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------

def _fetch(url: str, timeout: int = 10) -> Optional[PageResult]:
    """
    Fetch a single URL and return a PageResult.
    Returns None on connection errors so the crawler can skip gracefully.
    """
    try:
        if HAS_REQUESTS:
            r = requests.get(url, timeout=timeout,
                             headers={"User-Agent": "ERR0RS-Scout/1.0 (authorized pentest)"},
                             verify=False, allow_redirects=True)
            body   = r.text
            status = r.status_code
            hdrs   = dict(r.headers)
        else:
            parsed = urlparse(url)
            conn   = http.client.HTTPSConnection(parsed.hostname, timeout=timeout) \
                     if parsed.scheme == "https" \
                     else http.client.HTTPConnection(parsed.hostname, timeout=timeout)
            conn.request("GET", parsed.path or "/",
                         headers={"User-Agent": "ERR0RS-Scout/1.0 (authorized pentest)"})
            resp   = conn.getresponse()
            status = resp.status
            hdrs   = {k: v for k, v in resp.getheaders()}
            body   = resp.read().decode("utf-8", errors="replace")
            conn.close()
    except Exception as e:
        logger.debug("Fetch %s failed: %s", url, e)
        return None

    return PageResult(
        url=url, status_code=status, headers=hdrs,
        body_snippet=body[:2048],
    ), body                                         # return full body for parsing


# ---------------------------------------------------------------------------
# Parsers (all operate on raw HTML strings – no lxml/bs4 required)
# ---------------------------------------------------------------------------

def _extract_links(base_url: str, html: str) -> List[str]:
    """Extract all <a href=…> links, resolve relative URLs."""
    links = []
    for m in re.finditer(r'<a\s[^>]*href=["\']([^"\']+)["\']', html, re.IGNORECASE):
        raw = m.group(1)
        if raw.startswith(("javascript:", "mailto:", "#")):
            continue
        links.append(urljoin(base_url, raw))
    return links


def _extract_forms(html: str) -> List[Dict[str, Any]]:
    """Extract <form> blocks with action, method, and input fields."""
    forms = []
    for m in re.finditer(r'<form\b([^>]*)>(.*?)</form>', html, re.IGNORECASE | re.DOTALL):
        attrs  = m.group(1)
        body   = m.group(2)

        action = ""
        method = "GET"
        am = re.search(r'action=["\']([^"\']*)["\']', attrs, re.IGNORECASE)
        if am:
            action = am.group(1)
        mm = re.search(r'method=["\']([^"\']*)["\']', attrs, re.IGNORECASE)
        if mm:
            method = mm.group(1).upper()

        inputs = []
        for inp in re.finditer(
            r'<input\b[^>]*(?:name=["\']([^"\']*)["\'])[^>]*(?:type=["\']([^"\']*)["\'])?',
            body, re.IGNORECASE
        ):
            inputs.append({"name": inp.group(1) or "", "type": inp.group(2) or "text"})
        # Also grab <textarea> and <select>
        for sel in re.finditer(r'<(?:textarea|select)\s[^>]*name=["\']([^"\']*)["\']',
                               body, re.IGNORECASE):
            inputs.append({"name": sel.group(1), "type": "textarea"})

        forms.append({"action": action, "method": method, "inputs": inputs})
    return forms


def _extract_comments(html: str) -> List[str]:
    """Pull HTML comments – often contain debug info or hints."""
    return re.findall(r'<!--(.*?)-->', html, re.DOTALL)


def _detect_js_libraries(html: str) -> List[str]:
    """Match known JS library filenames / version strings."""
    found = []
    lower = html.lower()
    for pattern, name in JS_LIBRARY_PATTERNS:
        m = re.search(pattern, lower)
        if m:
            ver = m.group(1) if m.lastindex else ""
            found.append(f"{name} {ver}".strip())
    return found


def _check_security_headers(headers: Dict[str, str]) -> List[str]:
    """Return list of MISSING security headers."""
    lower_hdrs = {k.lower(): v for k, v in headers.items()}
    missing = []
    for h in SECURITY_HEADERS:
        if h.lower() not in lower_hdrs:
            missing.append(h)
    return missing


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class BrowserAutomationAgent:
    """
    Crawls a target web application and returns structured findings.

    Usage:
        agent  = BrowserAutomationAgent()
        result = await agent.crawl_and_analyze("https://example.com")
    """

    def __init__(self, llm_router=None, max_depth: int = 3, max_pages: int = 50):
        self.llm_router = llm_router
        self.max_depth  = max_depth
        self.max_pages  = max_pages

    async def crawl_and_analyze(self, target: str) -> Dict[str, Any]:
        """
        BFS crawl of target, then aggregate findings.
        """
        # Normalise URL
        if not target.startswith(("http://", "https://")):
            target = "https://" + target
        parsed = urlparse(target)
        base_domain = parsed.netloc

        # BFS state
        visited : Set[str]  = set()
        queue   : List[tuple] = [(target, 0)]       # (url, depth)
        pages   : List[PageResult] = []
        all_forms: List[Dict] = []
        all_comments: List[str] = []
        all_js_libs : List[str] = []
        all_missing_hdrs: List[str] = []

        start = time.time()

        while queue and len(visited) < self.max_pages:
            url, depth = queue.pop(0)
            if url in visited or depth > self.max_depth:
                continue
            visited.add(url)

            result = _fetch(url)
            if result is None:
                continue

            page, full_body = result
            pages.append(page)

            # --- parse ---
            links        = _extract_links(url, full_body)
            forms        = _extract_forms(full_body)
            comments     = _extract_comments(full_body)
            js_libs      = _detect_js_libraries(full_body)
            missing_hdrs = _check_security_headers(page.headers)

            page.forms           = forms
            page.links           = links
            page.comments        = comments
            page.js_libraries    = js_libs
            page.missing_headers = missing_hdrs

            all_forms.extend(forms)
            all_comments.extend(comments)
            all_js_libs.extend(js_libs)
            all_missing_hdrs.extend(missing_hdrs)

            # Enqueue same-domain links
            for link in links:
                lp = urlparse(link)
                if lp.netloc == base_domain and link not in visited:
                    queue.append((link, depth + 1))

        duration_ms = int((time.time() - start) * 1000)

        # --- dedupe ---
        unique_js   = list(set(all_js_libs))
        unique_hdrs = list(set(all_missing_hdrs))

        return {
            "target"         : target,
            "pages_crawled"  : len(pages),
            "forms_found"    : len(all_forms),
            "forms"          : all_forms,
            "comments_found" : len(all_comments),
            "comments"       : all_comments[:20],        # cap display
            "js_libraries"   : unique_js,
            "missing_security_headers": unique_hdrs,
            "duration_ms"    : duration_ms,
            "findings"       : self._build_findings(pages, all_forms, unique_js, unique_hdrs, all_comments),
        }

    # ------------------------------------------------------------------
    # Findings builder  – turns raw data into actionable finding dicts
    # ------------------------------------------------------------------

    @staticmethod
    def _build_findings(pages, forms, js_libs, missing_hdrs, comments) -> List[Dict[str, Any]]:
        findings = []

        # Missing headers
        if missing_hdrs:
            findings.append({
                "type"     : "missing_security_headers",
                "severity" : "medium",
                "detail"   : f"Missing: {', '.join(missing_hdrs)}",
            })

        # Exposed comments
        interesting = [c for c in comments if any(kw in c.lower() for kw in
                       ("todo","fixme","hack","password","secret","key","debug","test","admin"))]
        if interesting:
            findings.append({
                "type"     : "interesting_comments",
                "severity" : "low",
                "detail"   : f"{len(interesting)} comments with interesting keywords",
                "samples"  : interesting[:5],
            })

        # JS libraries (potential version-based vulns)
        if js_libs:
            findings.append({
                "type"     : "detected_libraries",
                "severity" : "info",
                "detail"   : f"Detected: {', '.join(js_libs)}",
            })

        # Login / auth forms
        auth_forms = [f for f in forms if any(
            i.get("type") in ("password",) or "pass" in (i.get("name") or "").lower()
            for i in f.get("inputs", [])
        )]
        if auth_forms:
            findings.append({
                "type"     : "auth_forms_detected",
                "severity" : "info",
                "detail"   : f"{len(auth_forms)} authentication form(s) found",
                "forms"    : auth_forms,
            })

        return findings
