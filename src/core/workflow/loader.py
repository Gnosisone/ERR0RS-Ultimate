# src/core/workflow/loader.py
# ERR0RS-Ultimate — Workflow YAML Loader
# Loads and validates YAML-defined kill-chain workflows from disk.
#
# Workflow YAML schema:
#   id:    <string>       — machine-readable identifier
#   name:  <string>       — human-readable title
#   steps: list of:
#     name:      <string>          — step display name
#     command:   <string>          — plugin command to run
#     args:      <dict>            — command arguments ({target} is interpolated)
#     type:      analyze | deploy  — special step types (no plugin command)
#     condition: <expr string>     — Python expression evaluated against context
#     learn:     <bool>            — emit education output for this step
#     timeout:   <int>             — seconds before step is killed (default 120)
#
# Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone

from __future__ import annotations
import os
import logging
from typing import Dict, List, Optional

logger = logging.getLogger("WorkflowLoader")

# Built-in workflow definitions (fallback when YAML files are absent)
BUILTIN_WORKFLOWS: Dict[str, dict] = {
    "webapp": {
        "id":   "webapp",
        "name": "Web Application Assessment",
        "steps": [
            {"name": "Port & Service Recon",  "command": "scan",     "args": {"target": "{target}"}, "learn": True},
            {"name": "Analyse Services",       "type":    "analyze"},
            {"name": "Web Vulnerability Scan", "command": "web_scan", "args": {"target": "{target}"},
             "condition": "\"http\" in services or \"https\" in services", "learn": True},
            {"name": "Directory Bruteforce",   "command": "dirb",    "args": {"target": "{target}"},
             "condition": "\"http\" in services or \"https\" in services"},
            {"name": "SQLi Test",              "command": "sqlmap",  "args": {"target": "{target}"},
             "condition": "forms_detected == True"},
        ],
    },
    "network": {
        "id":   "network",
        "name": "Network Infrastructure Assessment",
        "steps": [
            {"name": "Full Port Scan",     "command": "portscan", "args": {"target": "{target}"}, "learn": True},
            {"name": "Analyse Services",   "type":    "analyze"},
            {"name": "SMB Enumeration",    "command": "smb_enum", "args": {"target": "{target}"},
             "condition": "445 in open_ports or 139 in open_ports"},
            {"name": "SSH Audit",          "command": "ssh_audit","args": {"target": "{target}"},
             "condition": "22 in open_ports"},
            {"name": "Vulnerability Scan", "command": "vuln",     "args": {"target": "{target}"}},
        ],
    },
    "hardware_attack": {
        "id":   "hardware_attack",
        "name": "Hardware-Assisted Physical Attack",
        "steps": [
            {"name": "Deploy WiFi Harvester", "command": "deploy",
             "args": {"device": "hak5", "payload": "wifi_harvest"}, "learn": True},
            {"name": "Flipper Sub-GHz Sniff", "command": "deploy",
             "args": {"device": "flipper", "payload": "subghz_sniff"}},
        ],
    },
    "quick": {
        "id":   "quick",
        "name": "Quick Recon",
        "steps": [
            {"name": "Scan", "command": "scan", "args": {"target": "{target}"}, "learn": True},
            {"name": "Analyse", "type": "analyze"},
        ],
    },
}


try:
    import yaml
    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False
    logger.warning("PyYAML not installed — YAML workflow files disabled. "
                   "pip install pyyaml --break-system-packages")


# ─────────────────────────────────────────────────────────────────────────────

class WorkflowLoader:
    """
    Loads workflow definitions from YAML files or built-in fallbacks.

    Search order for a workflow named 'webapp':
      1. <workflow_dir>/webapp.yaml
      2. <workflow_dir>/webapp/workflow.yaml
      3. Built-in BUILTIN_WORKFLOWS dict

    Parameters
    ----------
    workflow_dir : str
        Base directory to search for YAML workflow files.
        Defaults to  <repo_root>/workflows/
    """

    REQUIRED_FIELDS = ("id", "name", "steps")
    VALID_STEP_KEYS = {
        "name", "command", "args", "type",
        "condition", "learn", "timeout",
    }

    def __init__(self, workflow_dir: str = "workflows"):
        self.workflow_dir = os.path.abspath(workflow_dir)

    # ── Public API ────────────────────────────────────────────────────────

    def load(self, name: str) -> dict:
        """
        Load a workflow by name. Raises FileNotFoundError if not found.
        """
        workflow = self._load_from_file(name) or self._load_builtin(name)
        if not workflow:
            available = self.list_available()
            raise FileNotFoundError(
                f"Workflow '{name}' not found.\n"
                f"Available: {', '.join(available) or 'none'}"
            )
        self._validate(workflow)
        return workflow

    def list_available(self) -> List[str]:
        """Return names of all discoverable workflows."""
        names = set(BUILTIN_WORKFLOWS.keys())
        if os.path.isdir(self.workflow_dir) and _YAML_AVAILABLE:
            for fname in os.listdir(self.workflow_dir):
                if fname.endswith(".yaml") or fname.endswith(".yml"):
                    names.add(fname.rsplit(".", 1)[0])
        return sorted(names)

    # ── Internal loaders ──────────────────────────────────────────────────

    def _load_from_file(self, name: str) -> Optional[dict]:
        if not _YAML_AVAILABLE or not os.path.isdir(self.workflow_dir):
            return None

        candidates = [
            os.path.join(self.workflow_dir, f"{name}.yaml"),
            os.path.join(self.workflow_dir, f"{name}.yml"),
            os.path.join(self.workflow_dir, name, "workflow.yaml"),
        ]
        for path in candidates:
            if os.path.isfile(path):
                try:
                    with open(path, "r") as fh:
                        data = yaml.safe_load(fh)
                    logger.info(f"Loaded workflow from {path}")
                    return data
                except yaml.YAMLError as e:
                    logger.error(f"YAML parse error in {path}: {e}")
        return None

    def _load_builtin(self, name: str) -> Optional[dict]:
        wf = BUILTIN_WORKFLOWS.get(name)
        if wf:
            logger.info(f"Using built-in workflow: {name}")
            return dict(wf)   # shallow copy
        return None

    def _validate(self, workflow: dict):
        """Raise ValueError if the workflow is structurally invalid."""
        for field in self.REQUIRED_FIELDS:
            if field not in workflow:
                raise ValueError(f"Workflow missing required field: '{field}'")
        if not isinstance(workflow["steps"], list) or not workflow["steps"]:
            raise ValueError("Workflow 'steps' must be a non-empty list.")
        for i, step in enumerate(workflow["steps"]):
            if "name" not in step:
                raise ValueError(f"Step {i} is missing 'name'.")
            unknown = set(step.keys()) - self.VALID_STEP_KEYS
            if unknown:
                logger.warning(
                    f"Step '{step['name']}' has unrecognised keys: {unknown}"
                )
