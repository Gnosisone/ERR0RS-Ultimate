"""
ERR0RS Engagement Audit Log
============================
Append-only, fsync-per-write structured event log for a single engagement.

Philosophy:
-----------
If ERR0RS is going to be aimed at real targets, EVERY action it takes must
be reproducible after the fact. Not "best effort" — guaranteed.

Every event written here is:
  • Timestamped (UTC, microsecond precision)
  • Typed (event_type from a closed enum)
  • Atomic (single line of JSON, fsynced before return)
  • Immutable (file is opened in append mode only; no rewrites ever)

This file is the legal artifact for an engagement. If a client asks
"why did you scan this endpoint at 03:47:22 UTC?", the answer is in audit.jsonl.

Event schema:
-------------
{
  "ts":         "2026-05-01T03:47:22.123456+00:00",
  "engagement": "2026-05-01-001",
  "event":      "phase_start",  # see EventType enum below
  "operator":   "eros",
  "phase":      "recon",        # optional, depends on event
  "data":       {...},          # event-specific payload
  "seq":        47              # monotonic per engagement
}

Author: Gary Holden Schneider (Eros) | Sprint 00
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional


# ── Event types (closed enum — no free-form types) ─────────────────────────

class EventType(str, Enum):
    # Lifecycle
    ENGAGEMENT_START      = "engagement_start"
    ENGAGEMENT_END        = "engagement_end"
    ENGAGEMENT_ABORT      = "engagement_abort"

    # Authorization
    AUTH_REQUESTED        = "auth_requested"
    AUTH_GRANTED          = "auth_granted"
    AUTH_DENIED           = "auth_denied"

    # Phase lifecycle
    PHASE_START           = "phase_start"
    PHASE_END             = "phase_end"
    PHASE_SKIP            = "phase_skip"
    PHASE_TIMEOUT         = "phase_timeout"

    # Tool execution
    TOOL_START            = "tool_start"
    TOOL_END              = "tool_end"
    TOOL_TIMEOUT          = "tool_timeout"
    TOOL_ERROR            = "tool_error"

    # Findings
    FINDING               = "finding"

    # Operator interaction
    OPERATOR_PROMPT       = "operator_prompt"
    OPERATOR_RESPONSE     = "operator_response"
    OPERATOR_APPROVE      = "operator_approve"
    OPERATOR_DENY         = "operator_deny"

    # Free-form (use sparingly)
    NOTE                  = "note"
    ERROR                 = "error"


# ── Audit logger ───────────────────────────────────────────────────────────

@dataclass
class AuditLogger:
    """
    One AuditLogger per engagement. Thread-safe append.
    File is opened on first write; never rewritten.

    Use as context manager when you can:
        with AuditLogger.for_engagement("2026-05-01-001", operator="eros") as log:
            log.event(EventType.PHASE_START, phase="recon")

    Or instantiate directly and let the file close on GC:
        log = AuditLogger.for_engagement("2026-05-01-001", operator="eros")
        log.event(EventType.PHASE_START, phase="recon")
    """

    engagement_id: str
    log_path:      Path
    operator:      str
    _seq:          int                  = field(default=0, init=False)
    _lock:         threading.Lock       = field(default_factory=threading.Lock, init=False)
    _fh:           Optional[Any]        = field(default=None, init=False)

    # ── Construction helpers ───────────────────────────────────────────────

    @classmethod
    def new_engagement_id(cls) -> str:
        """Generate a new engagement ID: YYYY-MM-DD-NNN-<hexsuffix>."""
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        suffix = uuid.uuid4().hex[:6]
        # The "NNN" counter is per-day — find the next available
        base = Path.home() / ".err0rs" / "engagements"
        base.mkdir(parents=True, exist_ok=True)
        existing = sorted([p.name for p in base.iterdir()
                          if p.is_dir() and p.name.startswith(date)])
        next_n = len(existing) + 1
        return f"{date}-{next_n:03d}-{suffix}"

    @classmethod
    def for_engagement(cls, engagement_id: str, operator: str,
                       base_dir: Optional[Path] = None) -> "AuditLogger":
        """
        Open (or create) the audit log for a given engagement ID.
        Default location: ~/.err0rs/engagements/<id>/audit.jsonl
        """
        base = base_dir or (Path.home() / ".err0rs" / "engagements")
        engagement_dir = base / engagement_id
        engagement_dir.mkdir(parents=True, exist_ok=True)
        log_path = engagement_dir / "audit.jsonl"

        logger = cls(
            engagement_id=engagement_id,
            log_path=log_path,
            operator=operator,
        )

        # If this engagement already has prior events, continue the seq
        if log_path.exists() and log_path.stat().st_size > 0:
            with open(log_path, "r") as f:
                last_seq = 0
                for line in f:
                    try:
                        rec = json.loads(line)
                        last_seq = max(last_seq, int(rec.get("seq", 0)))
                    except (json.JSONDecodeError, ValueError):
                        continue
                logger._seq = last_seq

        return logger

    # ── Context manager ────────────────────────────────────────────────────

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False  # never swallow exceptions

    def close(self):
        """Flush and close the underlying file handle."""
        with self._lock:
            if self._fh is not None:
                try:
                    self._fh.flush()
                    os.fsync(self._fh.fileno())
                except (OSError, ValueError):
                    pass
                try:
                    self._fh.close()
                except (OSError, ValueError):
                    pass
                self._fh = None

    # ── Core event writer ──────────────────────────────────────────────────

    def event(self, event_type: EventType, *,
              phase: Optional[str] = None,
              data: Optional[dict] = None,
              operator_override: Optional[str] = None) -> int:
        """
        Append a structured event. Thread-safe, fsync-per-write.

        Returns the sequence number of the event.
        """
        if not isinstance(event_type, EventType):
            # Defensive: refuse free-form event types
            raise TypeError(
                f"event_type must be EventType enum, got {type(event_type).__name__}"
            )

        with self._lock:
            self._seq += 1
            record = {
                "ts":         datetime.now(timezone.utc).isoformat(),
                "engagement": self.engagement_id,
                "event":      event_type.value,
                "operator":   operator_override or self.operator,
                "seq":        self._seq,
            }
            if phase is not None:
                record["phase"] = phase
            if data is not None:
                record["data"] = self._sanitize(data)

            line = json.dumps(record, separators=(",", ":"), ensure_ascii=True)

            if self._fh is None:
                # Open in append + buffered text mode
                self._fh = open(self.log_path, "a", encoding="ascii")

            self._fh.write(line + "\n")
            self._fh.flush()
            try:
                os.fsync(self._fh.fileno())
            except (OSError, ValueError):
                pass

            return self._seq

    # ── Convenience wrappers ───────────────────────────────────────────────

    def engagement_start(self, target: str, mode: str, **kw) -> int:
        return self.event(EventType.ENGAGEMENT_START,
                          data={"target": target, "mode": mode, **kw})

    def engagement_end(self, status: str, summary: Optional[dict] = None) -> int:
        return self.event(EventType.ENGAGEMENT_END,
                          data={"status": status, "summary": summary or {}})

    def auth(self, granted: bool, target: str, target_class: str,
             reason: str, resolved_ip: Optional[str] = None,
             justification: Optional[str] = None) -> int:
        evt = EventType.AUTH_GRANTED if granted else EventType.AUTH_DENIED
        return self.event(evt, data={
            "target": target,
            "target_class": target_class,
            "resolved_ip": resolved_ip,
            "reason": reason,
            "justification": justification,
        })

    def phase_start(self, phase: str, tools: list[str]) -> int:
        return self.event(EventType.PHASE_START, phase=phase,
                          data={"tools_planned": tools})

    def phase_end(self, phase: str, tools_run: int, findings: int,
                  duration_s: float) -> int:
        return self.event(EventType.PHASE_END, phase=phase, data={
            "tools_run": tools_run,
            "findings": findings,
            "duration_s": round(duration_s, 3),
        })

    def tool_start(self, tool: str, command: str, phase: str) -> int:
        return self.event(EventType.TOOL_START, phase=phase,
                          data={"tool": tool, "command": command})

    def tool_end(self, tool: str, phase: str, *, success: bool,
                 duration_s: float, findings: int = 0,
                 stdout_preview: str = "", stderr_preview: str = "") -> int:
        return self.event(EventType.TOOL_END, phase=phase, data={
            "tool":     tool,
            "success":  success,
            "duration_s": round(duration_s, 3),
            "findings": findings,
            "stdout_preview": stdout_preview[:500],
            "stderr_preview": stderr_preview[:500],
        })

    def finding(self, *, title: str, severity: str, phase: str,
                tool: str = "", detail: str = "", mitre: str = "",
                cve: str = "") -> int:
        return self.event(EventType.FINDING, phase=phase, data={
            "title": title,
            "severity": severity,
            "tool": tool,
            "detail": detail[:2000],
            "mitre": mitre,
            "cve": cve,
        })

    def operator_approve(self, action: str, target: str, phase: str) -> int:
        return self.event(EventType.OPERATOR_APPROVE, phase=phase,
                          data={"action": action, "target": target})

    def operator_deny(self, action: str, target: str, phase: str,
                       reason: str = "") -> int:
        return self.event(EventType.OPERATOR_DENY, phase=phase, data={
            "action": action, "target": target, "reason": reason,
        })

    def note(self, message: str, phase: Optional[str] = None) -> int:
        return self.event(EventType.NOTE, phase=phase, data={"message": message})

    def error(self, message: str, phase: Optional[str] = None,
              exception_type: str = "") -> int:
        return self.event(EventType.ERROR, phase=phase, data={
            "message": message, "exception_type": exception_type,
        })

    # ── Read-back helpers ──────────────────────────────────────────────────

    def replay(self) -> list[dict]:
        """Read all events from disk in order. Useful for crash recovery."""
        if not self.log_path.exists():
            return []
        events = []
        with open(self.log_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    # Skip corrupt lines but log a marker
                    events.append({"event": "corrupt", "raw": line[:200]})
        return events

    def summary(self) -> dict:
        """Quick stats from the event stream."""
        events = self.replay()
        from collections import Counter
        types = Counter(e.get("event", "?") for e in events)
        findings = [e for e in events if e.get("event") == "finding"]
        sev_counts = Counter(
            (e.get("data") or {}).get("severity", "info") for e in findings
        )
        return {
            "engagement_id": self.engagement_id,
            "total_events": len(events),
            "event_breakdown": dict(types),
            "findings_total": len(findings),
            "findings_by_severity": dict(sev_counts),
        }

    # ── Private helpers ────────────────────────────────────────────────────

    @staticmethod
    def _sanitize(data: Any) -> Any:
        """
        Best-effort sanitize: strip non-serializable values, truncate huge strings.
        We never let a bad payload break the audit log.
        """
        if isinstance(data, dict):
            return {k: AuditLogger._sanitize(v) for k, v in data.items()
                    if not k.startswith("_")}
        if isinstance(data, list):
            return [AuditLogger._sanitize(x) for x in data[:100]]  # cap list size
        if isinstance(data, (str, int, float, bool, type(None))):
            if isinstance(data, str) and len(data) > 4000:
                return data[:4000] + "...[truncated]"
            return data
        # Fall back to repr for unknown types
        try:
            return repr(data)[:500]
        except Exception:
            return "<unserializable>"
