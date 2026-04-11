# src/core/db.py
# ERR0RS-Ultimate — SQLite database layer
# Session storage, user accounts, audit log, findings persistence.
# Uses a thread-local connection pool for safety.
#
# Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone

from __future__ import annotations
import logging
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger("DB")

DB_PATH     = os.environ.get("ERR0RS_DB", "errors.db")
_local      = threading.local()


# ── Connection helpers ────────────────────────────────────────────────────────

def get_db(path: str = DB_PATH) -> sqlite3.Connection:
    """
    Return a thread-local SQLite connection.
    Row factory is set so rows behave like dicts.
    """
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = sqlite3.connect(path, check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA foreign_keys=ON")
    return _local.conn


@contextmanager
def db_cursor(path: str = DB_PATH):
    """Context manager: yields a cursor and commits on clean exit."""
    conn = get_db(path)
    cur  = conn.cursor()
    try:
        yield cur
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"DB error (rolled back): {e}")
        raise


def close_db():
    """Close the thread-local connection."""
    if hasattr(_local, "conn") and _local.conn:
        _local.conn.close()
        _local.conn = None


# ── Schema ────────────────────────────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    username   TEXT    UNIQUE NOT NULL,
    password   TEXT    NOT NULL,
    role       TEXT    DEFAULT 'operator',   -- admin | operator | viewer
    created_at TEXT    DEFAULT (datetime('now')),
    last_login TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id TEXT    NOT NULL,
    target     TEXT,
    data       TEXT,                          -- JSON blob of history
    started_at TEXT    DEFAULT (datetime('now')),
    ended_at   TEXT
);

CREATE TABLE IF NOT EXISTS findings (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id     TEXT,
    target         TEXT,
    title          TEXT,
    severity       TEXT,
    description    TEXT,
    evidence       TEXT,
    recommendation TEXT,
    mitre_id       TEXT,
    plugin         TEXT,
    created_at     TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS audit_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER REFERENCES users(id),
    session_id TEXT,
    action     TEXT,
    detail     TEXT,
    ip         TEXT,
    ts         TEXT DEFAULT (datetime('now'))
);
"""


def init_db(path: str = DB_PATH):
    """Create all tables if they don't exist. Safe to call repeatedly."""
    conn = get_db(path)
    conn.executescript(SCHEMA)
    conn.commit()
    logger.info(f"Database initialised: {path}")


# ── User operations ───────────────────────────────────────────────────────────

def _hash(password: str) -> str:
    """bcrypt hash — falls back to sha256 + salt if bcrypt unavailable."""
    try:
        import bcrypt
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    except ImportError:
        import hashlib, secrets
        salt = secrets.token_hex(16)
        hsh  = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
        return f"sha256${salt}${hsh}"


def _verify(password: str, stored: str) -> bool:
    try:
        import bcrypt
        return bcrypt.checkpw(password.encode(), stored.encode())
    except ImportError:
        import hashlib
        if stored.startswith("sha256$"):
            _, salt, hsh = stored.split("$", 2)
            return hashlib.sha256(f"{salt}{password}".encode()).hexdigest() == hsh
        return False


def create_user(username: str, password: str, role: str = "operator") -> bool:
    """Create a new user. Returns False if username already exists."""
    try:
        with db_cursor() as cur:
            cur.execute(
                "INSERT INTO users (username, password, role) VALUES (?,?,?)",
                (username, _hash(password), role),
            )
        logger.info(f"User created: {username} [{role}]")
        return True
    except sqlite3.IntegrityError:
        logger.warning(f"User already exists: {username}")
        return False


def authenticate(username: str, password: str) -> Optional[Dict]:
    """
    Validate credentials. Returns user dict on success, None on failure.
    Also updates last_login timestamp.
    """
    with db_cursor() as cur:
        row = cur.execute(
            "SELECT * FROM users WHERE username=?", (username,)
        ).fetchone()
        if not row:
            return None
        if not _verify(password, row["password"]):
            return None
        cur.execute(
            "UPDATE users SET last_login=? WHERE id=?",
            (datetime.utcnow().isoformat(), row["id"]),
        )
    return dict(row)


def get_user(user_id: int) -> Optional[Dict]:
    row = get_db().execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    return dict(row) if row else None


# ── Session persistence ───────────────────────────────────────────────────────

def save_session(user_id: int, session_id: str, target: str, history: list) -> bool:
    """Persist a pentest session to DB."""
    import json
    try:
        with db_cursor() as cur:
            cur.execute(
                "INSERT INTO sessions (user_id, session_id, target, data) VALUES (?,?,?,?)",
                (user_id, session_id, target, json.dumps(history, default=str)),
            )
        return True
    except Exception as e:
        logger.error(f"save_session error: {e}")
        return False


def load_sessions(user_id: int) -> List[Dict]:
    rows = get_db().execute(
        "SELECT * FROM sessions WHERE user_id=? ORDER BY started_at DESC",
        (user_id,)
    ).fetchall()
    return [dict(r) for r in rows]


# ── Finding persistence ───────────────────────────────────────────────────────

def save_finding(finding: Dict, session_id: str = "", target: str = "") -> bool:
    try:
        with db_cursor() as cur:
            cur.execute(
                """INSERT INTO findings
                   (session_id, target, title, severity, description,
                    evidence, recommendation, mitre_id, plugin)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    session_id, target,
                    finding.get("title", ""),
                    finding.get("severity", "info"),
                    finding.get("description", ""),
                    finding.get("evidence", ""),
                    finding.get("recommendation", ""),
                    finding.get("mitre_id", ""),
                    finding.get("plugin", ""),
                ),
            )
        return True
    except Exception as e:
        logger.error(f"save_finding error: {e}")
        return False


def get_findings(session_id: str = None, severity: str = None) -> List[Dict]:
    q    = "SELECT * FROM findings"
    args = []
    if session_id:
        q += " WHERE session_id=?"
        args.append(session_id)
    if severity:
        q += (" AND " if args else " WHERE ") + "severity=?"
        args.append(severity)
    q += " ORDER BY created_at DESC"
    return [dict(r) for r in get_db().execute(q, args).fetchall()]


# ── Audit log ─────────────────────────────────────────────────────────────────

def audit(action: str, detail: str = "", user_id: int = None,
          session_id: str = "", ip: str = ""):
    try:
        with db_cursor() as cur:
            cur.execute(
                "INSERT INTO audit_log (user_id, session_id, action, detail, ip) VALUES (?,?,?,?,?)",
                (user_id, session_id, action, detail, ip),
            )
    except Exception as e:
        logger.debug(f"Audit log error: {e}")
