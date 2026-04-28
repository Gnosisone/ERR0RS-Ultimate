# src/ui/dashboard/auth.py
# ERR0RS-Ultimate — Flask Auth Blueprint
# Login, logout, register, session guard middleware.
# Uses bcrypt via src/core/db.py — NOT raw SHA256.
#
# Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone

from __future__ import annotations
import functools
import logging
from flask import (
    Blueprint, current_app, redirect, render_template_string,
    request, session, url_for, jsonify, flash
)
from src.core.db import authenticate, create_user, get_user, audit, init_db

logger  = logging.getLogger("Auth")
auth_bp = Blueprint("auth", __name__)

# ── Login guard decorator ─────────────────────────────────────────────────────

def login_required(f):
    """Decorator: redirects to /login if the user is not in session."""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login_page"))
        return f(*args, **kwargs)
    return wrapper


def role_required(role: str):
    """Decorator: 403 if logged-in user doesn't have the required role."""
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            uid  = session.get("user_id")
            user = get_user(uid) if uid else None
            if not user or user.get("role") not in (role, "admin"):
                return jsonify({"error": "Forbidden"}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator


# ── Templates (inline — avoids extra template files) ─────────────────────────

_LOGIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>ERR0RS — Login</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#04000a;color:#d4b8ff;font-family:'Share Tech Mono',monospace;
  display:flex;align-items:center;justify-content:center;min-height:100vh}
.box{background:#0c0020;border:1px solid #3d0080;border-radius:10px;
  padding:40px 36px;width:340px}
h1{color:#bf6fff;font-size:22px;margin-bottom:8px;letter-spacing:2px}
p.sub{color:#4a2870;font-size:12px;margin-bottom:28px}
label{font-size:11px;text-transform:uppercase;letter-spacing:1px;color:#7b2fbe;
  display:block;margin-bottom:4px}
input{width:100%;background:#08001a;border:1px solid #2d0060;color:#d4b8ff;
  padding:10px 12px;border-radius:6px;font-family:inherit;font-size:13px;
  margin-bottom:16px}
input:focus{outline:none;border-color:#7b2fbe}
button{width:100%;background:#7b2fbe;color:#fff;border:none;padding:11px;
  border-radius:6px;font-family:inherit;font-size:13px;cursor:pointer;
  letter-spacing:1px;margin-top:4px}
button:hover{background:#9b3fde}
.err{color:#ff2255;font-size:12px;margin-bottom:14px}
.link{text-align:center;margin-top:16px;font-size:12px}
.link a{color:#00f5ff}
</style>
</head>
<body>
<div class="box">
  <h1>⚡ ERR0RS</h1>
  <p class="sub">Authorized Access Only</p>
  {% if error %}<div class="err">{{ error }}</div>{% endif %}
  <form method="POST">
    <label>Username</label>
    <input type="text" name="username" autocomplete="username" autofocus>
    <label>Password</label>
    <input type="password" name="password" autocomplete="current-password">
    <button type="submit">Login</button>
  </form>
  <div class="link"><a href="/register">Create account</a></div>
</div>
</body>
</html>"""

_REGISTER_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>ERR0RS — Register</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#04000a;color:#d4b8ff;font-family:'Share Tech Mono',monospace;
  display:flex;align-items:center;justify-content:center;min-height:100vh}
.box{background:#0c0020;border:1px solid #3d0080;border-radius:10px;
  padding:40px 36px;width:340px}
h1{color:#bf6fff;font-size:22px;margin-bottom:8px;letter-spacing:2px}
p.sub{color:#4a2870;font-size:12px;margin-bottom:28px}
label{font-size:11px;text-transform:uppercase;letter-spacing:1px;color:#7b2fbe;
  display:block;margin-bottom:4px}
input{width:100%;background:#08001a;border:1px solid #2d0060;color:#d4b8ff;
  padding:10px 12px;border-radius:6px;font-family:inherit;font-size:13px;
  margin-bottom:16px}
input:focus{outline:none;border-color:#7b2fbe}
button{width:100%;background:#7b2fbe;color:#fff;border:none;padding:11px;
  border-radius:6px;font-family:inherit;font-size:13px;cursor:pointer;letter-spacing:1px}
button:hover{background:#9b3fde}
.err{color:#ff2255;font-size:12px;margin-bottom:14px}
.ok{color:#39ff14;font-size:12px;margin-bottom:14px}
.link{text-align:center;margin-top:16px;font-size:12px}
.link a{color:#00f5ff}
</style>
</head>
<body>
<div class="box">
  <h1>⚡ Register</h1>
  <p class="sub">ERR0RS-Ultimate Account</p>
  {% if error %}<div class="err">{{ error }}</div>{% endif %}
  {% if success %}<div class="ok">{{ success }}</div>{% endif %}
  <form method="POST">
    <label>Username</label>
    <input type="text" name="username" autocomplete="username" autofocus>
    <label>Password</label>
    <input type="password" name="password" autocomplete="new-password">
    <label>Confirm Password</label>
    <input type="password" name="confirm" autocomplete="new-password">
    <button type="submit">Create Account</button>
  </form>
  <div class="link"><a href="/login">Back to login</a></div>
</div>
</body>
</html>"""


# ── Routes ────────────────────────────────────────────────────────────────────

@auth_bp.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "GET":
        return render_template_string(_LOGIN_HTML, error=None)

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    if not username or not password:
        return render_template_string(_LOGIN_HTML, error="Username and password required.")

    user = authenticate(username, password)
    if not user:
        audit("login_fail", detail=username, ip=request.remote_addr)
        logger.warning(f"Failed login: {username} from {request.remote_addr}")
        return render_template_string(_LOGIN_HTML, error="Invalid credentials.")

    session.clear()
    session["user_id"]   = user["id"]
    session["username"]  = user["username"]
    session["role"]      = user["role"]
    session.permanent    = True

    audit("login_ok", detail=username, user_id=user["id"], ip=request.remote_addr)
    logger.info(f"Login: {username} [{user['role']}] from {request.remote_addr}")
    return redirect(url_for("pages.index"))


@auth_bp.route("/logout")
def logout():
    uid = session.get("user_id")
    uname = session.get("username", "?")
    session.clear()
    audit("logout", user_id=uid, ip=request.remote_addr)
    logger.info(f"Logout: {uname}")
    return redirect(url_for("auth.login_page"))


@auth_bp.route("/register", methods=["GET", "POST"])
def register_page():
    if request.method == "GET":
        return render_template_string(_REGISTER_HTML, error=None, success=None)

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    confirm  = request.form.get("confirm", "")

    if not username or not password:
        return render_template_string(_REGISTER_HTML,
            error="All fields required.", success=None)

    if len(password) < 8:
        return render_template_string(_REGISTER_HTML,
            error="Password must be at least 8 characters.", success=None)

    if password != confirm:
        return render_template_string(_REGISTER_HTML,
            error="Passwords do not match.", success=None)

    # First registered user becomes admin
    existing = get_db_usercount()
    role = "admin" if existing == 0 else "operator"

    ok = create_user(username, password, role=role)
    if not ok:
        return render_template_string(_REGISTER_HTML,
            error="Username already taken.", success=None)

    audit("register", detail=f"{username} [{role}]", ip=request.remote_addr)
    return render_template_string(_REGISTER_HTML,
        error=None, success=f"Account created! Role: {role}. You can now log in.")


@auth_bp.route("/api/me")
def api_me():
    """Return current session user info as JSON."""
    uid = session.get("user_id")
    if not uid:
        return jsonify({"error": "Not authenticated"}), 401
    return jsonify({
        "user_id":  uid,
        "username": session.get("username"),
        "role":     session.get("role"),
    })


# ── Helper ────────────────────────────────────────────────────────────────────

def get_db_usercount() -> int:
    try:
        from src.core.db import get_db
        row = get_db().execute("SELECT COUNT(*) as n FROM users").fetchone()
        return row["n"] if row else 0
    except Exception:
        return 0
