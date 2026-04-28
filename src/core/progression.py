#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║           ERR0RS ULTIMATE — OPERATOR PROGRESSION ENGINE         ║
║              src/core/progression.py                            ║
║                                                                  ║
║  Skill tree + XP system for security education.                 ║
║  Every tool run, every question, every discovery earns XP.      ║
║  Beginners get guided. Veterans get unleashed.                   ║
║                                                                  ║
║  Levels:                                                         ║
║    0 — SCRIPT KIDDIE   (just started, guided mode)              ║
║    1 — APPRENTICE      (knows the basics)                        ║
║    2 — PRACTITIONER    (can run engagements)                     ║
║    3 — SPECIALIST      (deep in one domain)                      ║
║    4 — OPERATOR        (full red team)                           ║
║    5 — ELITE           (creates custom tools)                    ║
║                                                                  ║
║  Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone       ║
╚══════════════════════════════════════════════════════════════════╝
"""

import json
import os
import time
from datetime import datetime
from typing import Dict, List, Optional

PROGRESSION_FILE = os.path.expanduser("~/.err0rs/progression.json")

# ── Level definitions ──────────────────────────────────────────────────────────
LEVELS = [
    {"id": 0, "name": "SCRIPT KIDDIE",  "xp_required": 0,     "color": "#888",    "badge": "🔰"},
    {"id": 1, "name": "APPRENTICE",     "xp_required": 100,   "color": "#22d3ee", "badge": "🎯"},
    {"id": 2, "name": "PRACTITIONER",  "xp_required": 500,   "color": "#a855f7", "badge": "⚡"},
    {"id": 3, "name": "SPECIALIST",    "xp_required": 1500,  "color": "#f59e0b", "badge": "🔥"},
    {"id": 4, "name": "OPERATOR",      "xp_required": 4000,  "color": "#ef4444", "badge": "💀"},
    {"id": 5, "name": "ELITE",         "xp_required": 10000, "color": "#c084fc", "badge": "👑"},
]

# ── XP awards ──────────────────────────────────────────────────────────────────
XP_AWARDS = {
    # Tool runs
    "run_nmap":         10,
    "run_nikto":        10,
    "run_gobuster":     10,
    "run_sqlmap":       25,
    "run_hydra":        20,
    "run_nuclei":       15,
    "run_metasploit":   30,
    "run_bloodhound":   35,
    "run_mimikatz":     40,
    "run_volatility":   30,
    # Findings
    "found_vuln":       50,
    "found_cve":        75,
    "found_creds":      60,
    "found_shell":      100,
    # Learning
    "ask_question":     5,
    "complete_lesson":  30,
    "read_writeup":     20,
    # Operations
    "complete_recon":   40,
    "complete_scan":    30,
    "complete_exploit": 80,
    "complete_report":  50,
    "complete_ctf":     150,
    "juice_shop_challenge": 25,
    # Streaks
    "daily_login":      10,
    "week_streak":      50,
}

# ── Skill domains ──────────────────────────────────────────────────────────────
SKILL_DOMAINS = {
    "web_app":      {"name": "Web App Security",     "icon": "🌐", "xp": 0, "max": 1000},
    "network":      {"name": "Network Attacks",      "icon": "🔌", "xp": 0, "max": 1000},
    "active_dir":   {"name": "Active Directory",     "icon": "🏢", "xp": 0, "max": 1000},
    "wireless":     {"name": "Wireless Hacking",     "icon": "📡", "xp": 0, "max": 1000},
    "hardware":     {"name": "Hardware / Physical",  "icon": "🔧", "xp": 0, "max": 1000},
    "forensics":    {"name": "Digital Forensics",    "icon": "🔍", "xp": 0, "max": 1000},
    "social_eng":   {"name": "Social Engineering",   "icon": "🎭", "xp": 0, "max": 1000},
    "defense":      {"name": "Blue Team / Defense",  "icon": "🛡️", "xp": 0, "max": 1000},
}

# ── Domain XP mapping: which tool/event boosts which domain ───────────────────
DOMAIN_BOOSTS = {
    "run_nmap":       ["network"],
    "run_nikto":      ["web_app"],
    "run_gobuster":   ["web_app"],
    "run_sqlmap":     ["web_app"],
    "run_hydra":      ["network", "web_app"],
    "run_nuclei":     ["web_app", "network"],
    "run_metasploit": ["network", "web_app"],
    "run_bloodhound": ["active_dir"],
    "run_mimikatz":   ["active_dir"],
    "run_volatility": ["forensics"],
    "complete_ctf":   ["web_app", "network"],
    "juice_shop_challenge": ["web_app"],
    "ask_question":   [],  # no domain boost for questions
}


class ProgressionEngine:
    """Tracks operator XP, level, domain skills, and achievements."""

    def __init__(self):
        os.makedirs(os.path.dirname(PROGRESSION_FILE), exist_ok=True)
        self._data = self._load()

    def _load(self) -> dict:
        if os.path.exists(PROGRESSION_FILE):
            try:
                with open(PROGRESSION_FILE) as f:
                    return json.load(f)
            except Exception:
                pass
        return self._default_profile()

    def _default_profile(self) -> dict:
        return {
            "xp":           0,
            "level":        0,
            "total_events": 0,
            "joined":       datetime.now().isoformat(),
            "last_active":  datetime.now().isoformat(),
            "streak_days":  0,
            "domains":      {k: 0 for k in SKILL_DOMAINS},
            "achievements": [],
            "history":      [],
            "tools_used":   {},
            "findings":     0,
            "operator_name": "OPERATOR",
        }

    def _save(self):
        try:
            with open(PROGRESSION_FILE, "w") as f:
                json.dump(self._data, f, indent=2)
        except Exception:
            pass

    def award(self, event: str, context: str = "") -> dict:
        """Award XP for an event. Returns {xp_gained, level_up, new_level, message}."""
        xp = XP_AWARDS.get(event, 5)
        old_level = self.level

        self._data["xp"] += xp
        self._data["total_events"] += 1
        self._data["last_active"] = datetime.now().isoformat()
        self._data["history"].append({
            "event": event, "xp": xp,
            "ts": datetime.now().isoformat(),
            "context": context[:80],
        })
        # Keep history to last 200 events
        self._data["history"] = self._data["history"][-200:]

        # Domain boosts
        for domain in DOMAIN_BOOSTS.get(event, []):
            self._data["domains"][domain] = min(
                self._data["domains"].get(domain, 0) + xp,
                SKILL_DOMAINS[domain]["max"]
            )

        # Track tools used
        if event.startswith("run_"):
            tool = event[4:]
            self._data["tools_used"][tool] = self._data["tools_used"].get(tool, 0) + 1

        new_level = self.level
        level_up = new_level > old_level
        if level_up:
            self._data["level"] = new_level

        self._check_achievements()
        self._save()

        return {
            "xp_gained": xp,
            "total_xp":  self._data["xp"],
            "level_up":  level_up,
            "new_level": LEVELS[new_level],
            "old_level": LEVELS[old_level],
            "message":   self._level_up_message(new_level) if level_up else f"+{xp} XP",
        }

    @property
    def level(self) -> int:
        xp = self._data["xp"]
        for i in range(len(LEVELS) - 1, -1, -1):
            if xp >= LEVELS[i]["xp_required"]:
                return i
        return 0

    @property
    def xp_to_next(self) -> int:
        lvl = self.level
        if lvl >= len(LEVELS) - 1:
            return 0
        return LEVELS[lvl + 1]["xp_required"] - self._data["xp"]

    @property
    def is_beginner(self) -> bool:
        return self.level <= 1

    def get_summary(self) -> dict:
        lvl = self.level
        return {
            "xp":          self._data["xp"],
            "level":       lvl,
            "level_name":  LEVELS[lvl]["name"],
            "level_badge": LEVELS[lvl]["badge"],
            "level_color": LEVELS[lvl]["color"],
            "xp_to_next":  self.xp_to_next,
            "next_level":  LEVELS[lvl + 1]["name"] if lvl < len(LEVELS) - 1 else "MAX",
            "domains":     self._domain_summary(),
            "tools_used":  len(self._data["tools_used"]),
            "findings":    self._data["findings"],
            "achievements":len(self._data["achievements"]),
            "streak":      self._data["streak_days"],
            "is_beginner": self.is_beginner,
        }

    def _domain_summary(self) -> list:
        result = []
        for key, cfg in SKILL_DOMAINS.items():
            domain_xp = self._data["domains"].get(key, 0)
            pct = int((domain_xp / cfg["max"]) * 100)
            result.append({
                "key":   key,
                "name":  cfg["name"],
                "icon":  cfg["icon"],
                "xp":    domain_xp,
                "max":   cfg["max"],
                "pct":   pct,
            })
        return sorted(result, key=lambda x: x["xp"], reverse=True)

    def _check_achievements(self):
        achieved = set(self._data["achievements"])
        new = []

        checks = {
            "first_blood":     self._data["total_events"] >= 1,
            "recon_master":    self._data["tools_used"].get("nmap", 0) >= 10,
            "web_hunter":      self._data["tools_used"].get("sqlmap", 0) >= 5,
            "password_cracker":self._data["tools_used"].get("hydra", 0) >= 5,
            "ad_pwner":        self._data["tools_used"].get("bloodhound", 0) >= 3,
            "centurion":       self._data["xp"] >= 100,
            "five_hundred":    self._data["xp"] >= 500,
            "elite_operator":  self._data["xp"] >= 4000,
        }

        for name, condition in checks.items():
            if condition and name not in achieved:
                new.append(name)
                self._data["achievements"].append(name)

        return new

    def _level_up_message(self, new_level: int) -> str:
        msgs = {
            1: "🎯 APPRENTICE UNLOCKED — You've learned the basics. Time to go deeper.",
            2: "⚡ PRACTITIONER — You can run real engagements now. Stay ethical.",
            3: "🔥 SPECIALIST — You've mastered a domain. The network respects you.",
            4: "💀 OPERATOR — Full red team capability. You ARE the threat model.",
            5: "👑 ELITE — You don't just use tools, you build them. Legendary.",
        }
        return msgs.get(new_level, f"Level {new_level} reached!")


# ── Global singleton ──────────────────────────────────────────────────────────
_engine: Optional[ProgressionEngine] = None

def get_progression() -> ProgressionEngine:
    global _engine
    if _engine is None:
        _engine = ProgressionEngine()
    return _engine

def award_xp(event: str, context: str = "") -> dict:
    return get_progression().award(event, context)
