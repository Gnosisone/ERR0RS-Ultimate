# core/context.py
# ERR0RS-Ultimate Shared Context + Event Bus
# Single source of truth passed to every plugin

import uuid
import logging
import threading
from collections import defaultdict
from datetime import datetime


# ── Event Bus ────────────────────────────────────────────────────────────────

class EventBus:
    """
    Lightweight pub/sub event bus.
    Plugins emit events, core listeners react — zero tight coupling.
    """

    def __init__(self):
        self._listeners = defaultdict(list)
        self._lock = threading.Lock()

    def on(self, event: str, callback):
        """Register a persistent listener for an event."""
        with self._lock:
            self._listeners[event].append(callback)

    def off(self, event: str, callback):
        """Unregister a listener."""
        with self._lock:
            self._listeners[event] = [
                cb for cb in self._listeners[event] if cb != callback
            ]

    def once(self, event: str, callback):
        """One-shot listener — auto-removes after first fire."""
        def wrapper(evt, data):
            callback(evt, data)
            self.off(event, wrapper)
        self.on(event, wrapper)

    def emit(self, event: str, data=None):
        """Fire an event — calls all registered listeners."""
        with self._lock:
            listeners = list(self._listeners[event])
        for cb in listeners:
            try:
                cb(event, data)
            except Exception as e:
                logging.getLogger("EventBus").error(
                    f"Listener error on '{event}': {e}"
                )


# ── Shared Context ───────────────────────────────────────────────────────────

class SharedContext:
    """
    Passed to every plugin at load time.
    Holds: history, targets, hardware registry, findings, permissions, KV store.
    """

    def __init__(self, config: dict = None):
        self.config    = config or {}
        self.logger    = logging.getLogger("ERR0RS")
        self.event_bus = EventBus()
        self._lock     = threading.Lock()
        self._store    = {}

        # Core state — mirrors original dict shape
        self.history   = []   # command/action log
        self.targets   = []   # scoped target list
        self.hardware  = {}   # connected hardware registry

        self.session = {
            "id":           self._new_session_id(),
            "start_time":   datetime.utcnow().isoformat(),
            "active_target": None,
            "findings":     [],
            "permissions":  ["network", "filesystem", "hardware"],
        }

    # ── Target management ────────────────────────────────────────

    def add_target(self, target: str):
        with self._lock:
            if target not in self.targets:
                self.targets.append(target)
        self.event_bus.emit("target.added", {"target": target})
        self.logger.info(f"Target added: {target}")

    def set_active_target(self, target: str):
        if target not in self.targets:
            self.add_target(target)
        self.session["active_target"] = target
        self.event_bus.emit("target.set", {"target": target})
        self.logger.info(f"Active target: {target}")

    def get_active_target(self):
        return self.session["active_target"]

    # ── Action history ───────────────────────────────────────────

    def log_action(self, plugin: str, command: str, args: dict, result=None):
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "plugin":    plugin,
            "command":   command,
            "args":      args,
            "result":    result,
        }
        with self._lock:
            self.history.append(entry)
        self.event_bus.emit("action.logged", entry)

    # ── Findings ─────────────────────────────────────────────────

    def add_finding(self, finding: dict):
        """Universal finding sink — all plugins push here."""
        finding["timestamp"] = datetime.utcnow().isoformat()
        with self._lock:
            self.session["findings"].append(finding)
        self.event_bus.emit("finding.added", finding)

    def get_findings(self, plugin=None, finding_type=None):
        with self._lock:
            results = list(self.session["findings"])
        if plugin:
            results = [f for f in results if f.get("plugin") == plugin]
        if finding_type:
            results = [f for f in results if f.get("type") == finding_type]
        return results

    # ── Hardware registry ────────────────────────────────────────

    def register_hardware(self, name: str, info: dict):
        with self._lock:
            self.hardware[name] = {**info, "connected_at": datetime.utcnow().isoformat()}
        self.event_bus.emit("hardware.connected", {"name": name, "info": info})
        self.logger.info(f"Hardware registered: {name}")

    def unregister_hardware(self, name: str):
        with self._lock:
            self.hardware.pop(name, None)
        self.event_bus.emit("hardware.disconnected", {"name": name})

    def get_hardware(self, name: str):
        return self.hardware.get(name)

    # ── Permissions ──────────────────────────────────────────────

    def has_permission(self, perm: str) -> bool:
        return perm in self.session["permissions"]

    def grant_permission(self, perm: str):
        if perm not in self.session["permissions"]:
            self.session["permissions"].append(perm)

    def revoke_permission(self, perm: str):
        self.session["permissions"] = [
            p for p in self.session["permissions"] if p != perm
        ]

    # ── Generic KV store ─────────────────────────────────────────

    def set(self, key: str, value):
        with self._lock:
            self._store[key] = value

    def get(self, key: str, default=None):
        with self._lock:
            return self._store.get(key, default)

    def delete(self, key: str):
        with self._lock:
            self._store.pop(key, None)

    # ── Utility ──────────────────────────────────────────────────

    def summary(self):
        return {
            "session_id":    self.session["id"],
            "active_target": self.session["active_target"],
            "targets":       self.targets,
            "findings":      len(self.session["findings"]),
            "history":       len(self.history),
            "hardware":      list(self.hardware.keys()),
            "permissions":   self.session["permissions"],
            "start_time":    self.session["start_time"],
        }

    def _new_session_id(self):
        return str(uuid.uuid4())[:8].upper()
