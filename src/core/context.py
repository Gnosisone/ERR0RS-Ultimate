# src/core/context.py
# ERR0RS-Ultimate Shared Context + Event Bus

import uuid
import logging
import threading
from collections import defaultdict
from datetime import datetime


class EventBus:
    def __init__(self):
        self._listeners = defaultdict(list)
        self._lock = threading.Lock()

    def on(self, event: str, callback):
        with self._lock:
            self._listeners[event].append(callback)

    def off(self, event: str, callback):
        with self._lock:
            self._listeners[event] = [
                cb for cb in self._listeners[event] if cb != callback
            ]

    def once(self, event: str, callback):
        def wrapper(evt, data):
            callback(evt, data)
            self.off(event, wrapper)
        self.on(event, wrapper)

    def emit(self, event: str, data=None):
        with self._lock:
            listeners = list(self._listeners[event])
        for cb in listeners:
            try:
                cb(event, data)
            except Exception as e:
                logging.getLogger("EventBus").error(
                    f"Listener error on '{event}': {e}"
                )


class SharedContext:
    def __init__(self, config: dict = None):
        self.config    = config or {}
        self.logger    = logging.getLogger("ERR0RS")
        self.event_bus = EventBus()
        self._lock     = threading.Lock()
        self._store    = {}
        self.history   = []
        self.targets   = []
        self.hardware  = {}
        self.session   = {
            "id":            self._new_session_id(),
            "start_time":    datetime.utcnow().isoformat(),
            "active_target": None,
            "findings":      [],
            "permissions":   ["network", "filesystem", "hardware"],
        }

    def add_target(self, target: str):
        with self._lock:
            if target not in self.targets:
                self.targets.append(target)
        self.event_bus.emit("target.added", {"target": target})

    def set_active_target(self, target: str):
        if target not in self.targets:
            self.add_target(target)
        self.session["active_target"] = target
        self.event_bus.emit("target.set", {"target": target})

    def get_active_target(self):
        return self.session["active_target"]

    def log_action(self, plugin: str, command: str, args: dict, result=None):
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "plugin": plugin, "command": command,
            "args": args, "result": result,
        }
        with self._lock:
            self.history.append(entry)
        self.event_bus.emit("action.logged", entry)

    def add_finding(self, finding: dict):
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

    def register_hardware(self, name: str, info: dict):
        with self._lock:
            self.hardware[name] = {**info, "connected_at": datetime.utcnow().isoformat()}
        self.event_bus.emit("hardware.connected", {"name": name, "info": info})

    def unregister_hardware(self, name: str):
        with self._lock:
            self.hardware.pop(name, None)
        self.event_bus.emit("hardware.disconnected", {"name": name})

    def get_hardware(self, name: str):
        return self.hardware.get(name)

    def has_permission(self, perm: str) -> bool:
        return perm in self.session["permissions"]

    def set(self, key: str, value):
        with self._lock:
            self._store[key] = value

    def get(self, key: str, default=None):
        with self._lock:
            return self._store.get(key, default)

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
