"""
ERR0RS ULTIMATE — Listener Manager (OPERATE-tier feature)
═══════════════════════════════════════════════════════════════════

When an OPERATE-tier user generates a payload that calls back (reverse
shell, exfiltration channel, BadUSB callback), they need a listener
waiting. This module is the central authority for opening, tracking,
and tearing down those listeners with the consent and audit guarantees
the ERR0RS mission requires.

DESIGN PRINCIPLES:

  1. OPERATE-tier only.
     spin_up() raises TierRequired if the user is below OPERATE. No
     env-var bypass. No "I'm just testing." If you need a listener at
     LEARN tier, you need to upgrade first.

  2. Loopback by default.
     Listeners bind to 127.0.0.1 unless the caller explicitly passes
     bind="0.0.0.0" with consent acknowledgment. A loopback listener
     can't be reached by anything off this device — the friction of
     declaring otherwise is the point.

  3. Per-listener consent.
     Even at OPERATE tier, each spin_up() requires a fresh consent
     check via the caller (the launcher's UI). This module DOES NOT
     prompt — it raises ConsentRequired if no prior consent token is
     passed. The launcher is responsible for asking the user and
     passing the resulting token.

  4. Persistent visibility.
     active_listeners() returns every listener, with port, bind,
     purpose, started-at. The UI is expected to show this somewhere
     persistent (banner, status bar) while anything is active.

  5. Clean teardown.
     atexit + SIGTERM/SIGINT handlers ensure listeners die on normal
     exit. SIGKILL leaks — documented honestly, not papered over.

  6. Audit log.
     Every spin_up / shutdown writes a line to ~/.err0rs/listeners.log
     with timestamp, port, purpose, user. If a legal record matters
     later, it exists.

USAGE (from the launcher's OPERATE-only code paths):

    from src.security.listener_manager import (
        get_manager, ConsentToken, ListenerKind, TierRequired
    )

    mgr = get_manager()

    # Step 1: ask the user for consent (UI's job, not ours)
    token = ConsentToken(
        granted_by="user",
        purpose="BadUSB reverse-shell callback for engagement Acme-Q3",
    )

    # Step 2: spin it up
    listener = mgr.spin_up(
        port=4444,
        kind=ListenerKind.TCP_RAW,
        consent=token,
        bind="127.0.0.1",        # explicit even though it's the default
    )

    # Listener is live; banner now shows it. Connections are accepted
    # and lines forwarded to listener.on_data callback if set.

    # Step 3: when done
    mgr.shutdown(listener.id)
    # or: mgr.shutdown_all() at exit (also called by atexit handler)
"""
from __future__ import annotations

import atexit
import json
import logging
import os
import signal
import socket
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

from .operator_tier import OperatorTier, current_tier, has_valid_attestation

log = logging.getLogger(__name__)

LISTENER_LOG_PATH = Path.home() / ".err0rs" / "listeners.log"
LOOPBACK_BINDS = {"127.0.0.1", "::1", "localhost"}


# ── Exceptions ───────────────────────────────────────────────────────────

class TierRequired(Exception):
    """Raised when listener ops are attempted below OPERATE tier."""


class ConsentRequired(Exception):
    """Raised when spin_up() is called without a valid consent token."""


class ListenerError(Exception):
    """Raised for socket/bind failures and operational errors."""


# ── Data types ───────────────────────────────────────────────────────────

class ListenerKind(Enum):
    """What kind of listener the caller wants. Today we ship only TCP_RAW.

    TCP_RAW    — raw TCP socket, line-buffered, suitable for nc-style
                 reverse shells and simple callback channels
    TLS        — placeholder for v3.9; requires a cert chain
    HTTP       — placeholder for v3.9; useful for exfil-via-HTTP payloads
    MSF_HANDLER — placeholder for v3.9; wraps msfconsole exploit/multi/handler
    """
    TCP_RAW    = "tcp_raw"
    TLS        = "tls"
    HTTP       = "http"
    MSF_HANDLER = "msf_handler"


@dataclass
class ConsentToken:
    """The launcher hands us this AFTER the user has affirmatively
    consented to a specific listener spinup. We treat absence of a
    token as 'no consent obtained' — a refusal, not a default-yes."""
    granted_by:   str       # 'user' | 'auto-engagement' | etc.
    purpose:      str       # human-readable, ends up in the audit log
    granted_at:   float = field(default_factory=time.time)

    def is_recent(self, max_age_seconds: int = 300) -> bool:
        """A token is valid only for a short window after grant. Forces
        the user's consent and the actual spin_up call to be close in
        time so consent isn't reused stale from an earlier session."""
        return (time.time() - self.granted_at) <= max_age_seconds


@dataclass
class Listener:
    """A live listener tracked by the manager."""
    id:           int
    port:         int
    bind:         str
    kind:         ListenerKind
    purpose:      str
    started_at:   float
    bound_pub:    bool = False          # True if bind != loopback
    on_data:      Optional[Callable[[str], None]] = None
    on_connect:   Optional[Callable[[str], None]] = None
    _server_sock: Optional[socket.socket] = None
    _client_socks: list = field(default_factory=list)
    _thread:      Optional[threading.Thread] = None
    _stop_event:  threading.Event = field(default_factory=threading.Event)

    def summary(self) -> dict:
        """Public-safe snapshot — no sockets or callbacks."""
        return {
            "id":          self.id,
            "port":        self.port,
            "bind":        self.bind,
            "kind":        self.kind.value,
            "purpose":     self.purpose,
            "started_at":  datetime.fromtimestamp(self.started_at).isoformat(),
            "bound_pub":   self.bound_pub,
            "client_count": len(self._client_socks),
            "age_seconds": int(time.time() - self.started_at),
        }


# ── Audit log ────────────────────────────────────────────────────────────

def _audit(event: str, **fields):
    """Append a JSON line to the audit log. Best-effort — if write
    fails we still want the listener op to succeed."""
    record = {
        "event":  event,
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "ts_local": datetime.now().isoformat(),
        "user":   os.environ.get("USER", "unknown"),
        "pid":    os.getpid(),
        **fields,
    }
    try:
        LISTENER_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LISTENER_LOG_PATH.open("a") as f:
            f.write(json.dumps(record) + "\n")
        # Tighten perms on first creation
        if LISTENER_LOG_PATH.stat().st_size <= len(json.dumps(record)) + 1:
            try:
                LISTENER_LOG_PATH.chmod(0o600)
            except Exception:
                pass
    except Exception as e:
        log.warning(f"audit write failed: {e}")


# ── ListenerManager ──────────────────────────────────────────────────────

class ListenerManager:
    """Singleton-style manager. Don't instantiate directly — use
    get_manager()."""

    def __init__(self):
        self._lock = threading.Lock()
        self._listeners: dict[int, Listener] = {}
        self._next_id = 1
        self._signals_installed = False

    # ── Lifecycle ────────────────────────────────────────────────────

    def _ensure_signal_handlers(self):
        """Install SIGTERM/SIGINT handlers exactly once. atexit covers
        normal Python exit; signals cover Ctrl+C and `kill <pid>`."""
        if self._signals_installed:
            return
        try:
            # Only install if we're on the main thread — Python signals
            # can only be set from main, and the launcher might import
            # this from a worker.
            if threading.current_thread() is threading.main_thread():
                signal.signal(signal.SIGTERM, self._signal_teardown)
                signal.signal(signal.SIGINT, self._signal_teardown)
            atexit.register(self.shutdown_all)
            self._signals_installed = True
        except Exception as e:
            log.warning(f"could not install signal handlers: {e}")

    def _signal_teardown(self, signum, _frame):
        """Triggered by SIGTERM/SIGINT. Shut everything down, then
        re-raise the signal's default behavior."""
        log.warning(f"received signal {signum}, shutting down listeners")
        self.shutdown_all()
        # Re-raise default behavior so the rest of ERR0RS can exit cleanly
        signal.signal(signum, signal.SIG_DFL)
        os.kill(os.getpid(), signum)

    # ── Spin up ──────────────────────────────────────────────────────

    def spin_up(
        self,
        port: int,
        kind: ListenerKind,
        consent: ConsentToken,
        bind: str = "127.0.0.1",
        on_data: Optional[Callable[[str], None]] = None,
        on_connect: Optional[Callable[[str], None]] = None,
    ) -> Listener:
        """Open a new listener. Raises TierRequired, ConsentRequired,
        or ListenerError if the request is rejected.

        Caller MUST have already shown the user a consent prompt and
        captured an affirmative response into the ConsentToken."""
        # ── Gate 1: tier ────────────────────────────────────────────
        if current_tier() < OperatorTier.OPERATE:
            raise TierRequired(
                "Listener spinup requires OPERATE tier. "
                "Set ERR0RS_OPERATOR_TIER=operate in your .env and "
                "complete the attestation."
            )

        # ── Gate 2: attestation actually on file ────────────────────
        # Defense in depth — tier could be set without attestation
        # if someone edits .env but never runs the launcher's first-
        # run flow.
        if not has_valid_attestation():
            raise TierRequired(
                "OPERATE tier requested but no valid attestation on file. "
                "Run ERR0RS interactively to complete the attestation "
                "before opening listeners."
            )

        # ── Gate 3: consent ─────────────────────────────────────────
        if consent is None:
            raise ConsentRequired(
                "No consent token provided. The launcher must capture "
                "user consent before each spin_up call."
            )
        if not consent.is_recent():
            raise ConsentRequired(
                "Consent token expired. Consent must be fresh (within "
                "5 minutes) to remain valid."
            )

        # ── Gate 4: only TCP_RAW implemented today ──────────────────
        if kind != ListenerKind.TCP_RAW:
            raise ListenerError(
                f"Listener kind {kind.value} is not implemented yet. "
                f"Today's options: tcp_raw"
            )

        # ── Gate 5: sane port ───────────────────────────────────────
        if not (1 <= port <= 65535):
            raise ListenerError(f"port {port} out of range 1-65535")
        if port < 1024:
            # Privileged ports — we could accept with sudo, but for
            # safety we refuse. OPERATE users can run on >= 1024.
            raise ListenerError(
                f"port {port} is privileged (<1024). Use a port >= 1024."
            )

        # ── Gate 6: bind interface ──────────────────────────────────
        bind_clean = bind.strip()
        bound_pub = bind_clean not in LOOPBACK_BINDS
        if bound_pub:
            # Public bind requires explicit acknowledgment in the
            # consent purpose — we look for the string [BIND_ALL_ACK].
            # The launcher is expected to ask a separate question and
            # inject that token into the purpose if granted.
            if "[BIND_ALL_ACK]" not in consent.purpose:
                raise ConsentRequired(
                    f"Bind to non-loopback ({bind_clean}) requires an "
                    f"explicit BIND_ALL acknowledgment in the consent "
                    f"token. The launcher must ask 'expose this port to "
                    f"your LAN?' separately and add [BIND_ALL_ACK] to "
                    f"the purpose when the user says yes."
                )

        # ── Open the socket ─────────────────────────────────────────
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((bind_clean, port))
            sock.listen(5)
            sock.settimeout(1.0)   # allow the accept loop to check stop_event
        except OSError as e:
            raise ListenerError(f"could not bind {bind_clean}:{port} — {e}")

        # ── Register and start accept loop ──────────────────────────
        with self._lock:
            self._ensure_signal_handlers()
            listener_id = self._next_id
            self._next_id += 1
            listener = Listener(
                id=listener_id,
                port=port,
                bind=bind_clean,
                kind=kind,
                purpose=consent.purpose,
                started_at=time.time(),
                bound_pub=bound_pub,
                on_data=on_data,
                on_connect=on_connect,
                _server_sock=sock,
            )
            self._listeners[listener_id] = listener

        # Accept loop runs in its own thread so spin_up returns immediately
        listener._thread = threading.Thread(
            target=self._accept_loop,
            args=(listener,),
            daemon=True,
            name=f"err0rs-listener-{port}",
        )
        listener._thread.start()

        _audit(
            "listener_open",
            listener_id=listener_id,
            port=port,
            bind=bind_clean,
            bound_pub=bound_pub,
            kind=kind.value,
            purpose=consent.purpose,
            consent_granted_by=consent.granted_by,
        )
        log.info(
            f"listener opened: id={listener_id} {bind_clean}:{port} "
            f"({kind.value}) — {consent.purpose}"
        )
        return listener

    # ── Accept loop ──────────────────────────────────────────────────

    def _accept_loop(self, listener: Listener):
        """Run in a background thread. Accepts connections, spawns a
        per-client read loop, dies cleanly when stop_event is set."""
        sock = listener._server_sock
        while not listener._stop_event.is_set():
            try:
                client, addr = sock.accept()
            except socket.timeout:
                continue
            except OSError:
                # Socket closed from teardown path
                break

            log.info(f"listener {listener.id}: connect from {addr}")
            _audit(
                "listener_connect",
                listener_id=listener.id,
                remote_addr=f"{addr[0]}:{addr[1]}",
            )
            if listener.on_connect:
                try:
                    listener.on_connect(f"{addr[0]}:{addr[1]}")
                except Exception as e:
                    log.warning(f"on_connect callback failed: {e}")

            listener._client_socks.append(client)
            t = threading.Thread(
                target=self._client_loop,
                args=(listener, client, addr),
                daemon=True,
                name=f"err0rs-client-{listener.port}-{addr[1]}",
            )
            t.start()

    def _client_loop(self, listener: Listener, client: socket.socket, addr):
        """Read lines from a connected client, forward to on_data callback."""
        client.settimeout(1.0)
        buf = b""
        while not listener._stop_event.is_set():
            try:
                chunk = client.recv(4096)
            except socket.timeout:
                continue
            except OSError:
                break
            if not chunk:
                break
            buf += chunk
            while b"\n" in buf:
                line, _, buf = buf.partition(b"\n")
                if listener.on_data:
                    try:
                        listener.on_data(line.decode("utf-8", errors="replace"))
                    except Exception as e:
                        log.warning(f"on_data callback failed: {e}")
        try:
            client.close()
        except Exception:
            pass
        log.info(f"listener {listener.id}: client {addr} disconnected")

    # ── Shutdown ─────────────────────────────────────────────────────

    def shutdown(self, listener_id: int) -> bool:
        """Tear down one listener by id. Idempotent — returns True if
        the listener existed and was shut down, False if it didn't exist."""
        with self._lock:
            listener = self._listeners.pop(listener_id, None)
        if listener is None:
            return False

        listener._stop_event.set()
        # Closing the server socket unblocks accept()
        try:
            if listener._server_sock:
                listener._server_sock.close()
        except Exception:
            pass
        # Close any connected clients
        for c in list(listener._client_socks):
            try:
                c.close()
            except Exception:
                pass
        # Wait briefly for accept thread to die
        if listener._thread:
            listener._thread.join(timeout=2.0)

        _audit(
            "listener_close",
            listener_id=listener.id,
            port=listener.port,
            age_seconds=int(time.time() - listener.started_at),
        )
        log.info(f"listener closed: id={listener_id} port={listener.port}")
        return True

    def shutdown_all(self):
        """Tear down every active listener. Called by atexit and signal
        handlers. Safe to call repeatedly."""
        with self._lock:
            ids = list(self._listeners.keys())
        for lid in ids:
            try:
                self.shutdown(lid)
            except Exception as e:
                log.warning(f"shutdown({lid}) failed: {e}")

    # ── Inspection ───────────────────────────────────────────────────

    def active_listeners(self) -> list[dict]:
        """Return public summaries of all active listeners."""
        with self._lock:
            return [l.summary() for l in self._listeners.values()]

    def has_active(self) -> bool:
        with self._lock:
            return bool(self._listeners)

    def get(self, listener_id: int) -> Optional[Listener]:
        with self._lock:
            return self._listeners.get(listener_id)

    def banner_text(self) -> str:
        """Human-readable persistent banner for the UI to display while
        listeners are active. Empty string when none are open."""
        actives = self.active_listeners()
        if not actives:
            return ""
        pub_count = sum(1 for a in actives if a["bound_pub"])
        lines = [f"⚠️  {len(actives)} ERR0RS listener(s) active"]
        for a in actives:
            warn = " [LAN-EXPOSED]" if a["bound_pub"] else ""
            lines.append(f"   • {a['bind']}:{a['port']} ({a['kind']}){warn} — {a['purpose']}")
        if pub_count:
            lines.append(
                f"   ⚠ {pub_count} listener(s) bound to non-loopback — "
                f"reachable from your network"
            )
        return "\n".join(lines)


# ── Module-level singleton accessor ──────────────────────────────────────

_manager_lock = threading.Lock()
_manager: Optional[ListenerManager] = None


def get_manager() -> ListenerManager:
    """Return the singleton ListenerManager, creating on first call."""
    global _manager
    with _manager_lock:
        if _manager is None:
            _manager = ListenerManager()
        return _manager


# ── Test helpers ─────────────────────────────────────────────────────────

def _reset_for_testing():
    """Tear down all listeners and reset the singleton. Tests only."""
    global _manager
    if _manager:
        _manager.shutdown_all()
    with _manager_lock:
        _manager = None
