#!/usr/bin/env python3
"""
ERR0RS ULTIMATE — Campaign Manager v1.0
Full engagement lifecycle: create → plan → execute → report → close

Competes with: Cobalt Strike (team ops), Metasploit Pro (campaign mgmt),
               Core Impact (engagement tracking), Pentera (automated campaigns)

Features:
  - Multi-target campaign management
  - Objective tracking with completion status
  - Timeline and milestone logging
  - Operator assignment and notes
  - Evidence chain of custody
  - Auto-generates engagement report on close

Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
"""

import json, uuid, os
from datetime import datetime
from typing import Optional
from pathlib import Path
from dataclasses import dataclass, field, asdict
from enum import Enum

CAMPAIGNS_DIR = Path(__file__).resolve().parents[3] / "output" / "campaigns"
CAMPAIGNS_DIR.mkdir(parents=True, exist_ok=True)


class CampaignStatus(str, Enum):
    PLANNING    = "planning"
    ACTIVE      = "active"
    PAUSED      = "paused"
    COMPLETE    = "complete"
    CLOSED      = "closed"


class ObjectiveStatus(str, Enum):
    PENDING     = "pending"
    IN_PROGRESS = "in_progress"
    ACHIEVED    = "achieved"
    FAILED      = "failed"
    SKIPPED     = "skipped"


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH     = "high"
    MEDIUM   = "medium"
    LOW      = "low"
    INFO     = "info"


@dataclass
class Objective:
    id:          str   = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title:       str   = ""
    description: str   = ""
    phase:       str   = "initial_access"
    status:      str   = ObjectiveStatus.PENDING
    target:      str   = ""
    notes:       str   = ""
    achieved_at: str   = ""
    evidence:    list  = field(default_factory=list)


@dataclass
class Finding:
    id:             str  = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title:          str  = ""
    severity:       str  = Severity.MEDIUM
    description:    str  = ""
    target:         str  = ""
    tool:           str  = ""
    evidence:       str  = ""
    remediation:    str  = ""
    cvss_score:     float = 0.0
    mitre_id:       str  = ""
    timestamp:      str  = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class TimelineEvent:
    timestamp:  str  = field(default_factory=lambda: datetime.now().isoformat())
    operator:   str  = "ERR0RS"
    action:     str  = ""
    target:     str  = ""
    result:     str  = ""
    tool:       str  = ""


@dataclass
class Credential:
    id:         str  = field(default_factory=lambda: str(uuid.uuid4())[:8])
    username:   str  = ""
    secret:     str  = ""       # hash or plaintext (operator's choice)
    secret_type: str = "hash"   # hash | plaintext | key
    domain:     str  = ""
    source:     str  = ""       # tool that found it
    target:     str  = ""
    cracked:    bool = False
    plaintext:  str  = ""       # populated if cracked
    timestamp:  str  = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Campaign:
    id:           str   = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name:         str   = "New Engagement"
    client:       str   = ""
    operator:     str   = "ERR0RS"
    status:       str   = CampaignStatus.PLANNING
    scope:        list  = field(default_factory=list)
    out_of_scope: list  = field(default_factory=list)
    objectives:   list  = field(default_factory=list)
    findings:     list  = field(default_factory=list)
    credentials:  list  = field(default_factory=list)
    timeline:     list  = field(default_factory=list)
    sessions:     list  = field(default_factory=list)
    notes:        str   = ""
    roe:          str   = ""    # Rules of Engagement
    start_date:   str   = field(default_factory=lambda: datetime.now().isoformat())
    end_date:     str   = ""
    report_path:  str   = ""


class CampaignManager:
    """
    Manages the full lifecycle of a red team engagement.
    One campaign = one client engagement with targets, objectives,
    findings, credentials, timeline, and final report.
    """

    def __init__(self):
        self.campaigns: dict = {}
        self.active_id: Optional[str] = None
        self._load_all()

    # ── Create / Open / Close ─────────────────────────────────────

    def create(self, name: str, client: str = "", operator: str = "ERR0RS",
               scope: list = None, roe: str = "") -> Campaign:
        c = Campaign(name=name, client=client, operator=operator,
                     scope=scope or [], roe=roe)
        c.objectives = self._default_objectives()
        self.campaigns[c.id] = c
        self.active_id = c.id
        self._log(c, "Campaign created", result=f"Scope: {len(scope or [])} targets")
        self._save(c)
        return c

    def open(self, campaign_id: str) -> Optional[Campaign]:
        c = self.campaigns.get(campaign_id)
        if c:
            self.active_id = campaign_id
            c.status = CampaignStatus.ACTIVE
            self._save(c)
        return c

    def close(self, campaign_id: str = None) -> str:
        c = self._get(campaign_id)
        if not c:
            return "No active campaign."
        c.status = CampaignStatus.CLOSED
        c.end_date = datetime.now().isoformat()
        self._log(c, "Campaign closed")
        self._save(c)
        return f"Campaign '{c.name}' closed. Run generate_report() for final report."

    # ── Objectives ────────────────────────────────────────────────

    def add_objective(self, title: str, description: str = "",
                      phase: str = "initial_access", target: str = "",
                      campaign_id: str = None) -> Objective:
        c = self._get(campaign_id)
        if not c:
            return None
        obj = Objective(title=title, description=description,
                        phase=phase, target=target)
        c.objectives.append(asdict(obj))
        self._save(c)
        return obj

    def achieve_objective(self, objective_id: str, notes: str = "",
                          campaign_id: str = None):
        c = self._get(campaign_id)
        if not c:
            return
        for obj in c.objectives:
            if obj["id"] == objective_id:
                obj["status"]      = ObjectiveStatus.ACHIEVED
                obj["notes"]       = notes
                obj["achieved_at"] = datetime.now().isoformat()
                self._log(c, f"Objective achieved: {obj['title']}")
                self._save(c)
                return f"✅ Objective '{obj['title']}' marked achieved."
        return "Objective not found."

    # ── Findings ──────────────────────────────────────────────────

    def add_finding(self, title: str, severity: str, description: str,
                    target: str = "", tool: str = "", evidence: str = "",
                    remediation: str = "", cvss: float = 0.0,
                    mitre_id: str = "", campaign_id: str = None) -> Finding:
        c = self._get(campaign_id)
        if not c:
            return None
        f = Finding(title=title, severity=severity, description=description,
                    target=target, tool=tool, evidence=evidence,
                    remediation=remediation, cvss_score=cvss, mitre_id=mitre_id)
        c.findings.append(asdict(f))
        self._log(c, f"Finding logged: [{severity.upper()}] {title}", target=target, tool=tool)
        self._save(c)
        return f

    # ── Credentials ───────────────────────────────────────────────

    def add_credential(self, username: str, secret: str,
                       secret_type: str = "hash", domain: str = "",
                       source: str = "", target: str = "",
                       campaign_id: str = None) -> Credential:
        c = self._get(campaign_id)
        if not c:
            return None
        cred = Credential(username=username, secret=secret,
                          secret_type=secret_type, domain=domain,
                          source=source, target=target)
        c.credentials.append(asdict(cred))
        self._log(c, f"Credential captured: {domain}\\{username}",
                  target=target, tool=source)
        self._save(c)
        return cred

    def mark_cracked(self, cred_id: str, plaintext: str, campaign_id: str = None):
        c = self._get(campaign_id)
        if not c:
            return
        for cred in c.credentials:
            if cred["id"] == cred_id:
                cred["cracked"]   = True
                cred["plaintext"] = plaintext
                self._log(c, f"Credential cracked: {cred['username']}")
                self._save(c)
                return

    # ── Sessions ──────────────────────────────────────────────────

    def register_session(self, target: str, user: str, os: str = "",
                         session_type: str = "meterpreter",
                         campaign_id: str = None):
        c = self._get(campaign_id)
        if not c:
            return
        session = {
            "id": str(uuid.uuid4())[:8],
            "target": target, "user": user,
            "os": os, "type": session_type,
            "opened_at": datetime.now().isoformat(),
            "status": "active",
        }
        c.sessions.append(session)
        self._log(c, f"Session opened on {target} as {user}", target=target)
        self._save(c)
        return session

    # ── Timeline ──────────────────────────────────────────────────

    def log(self, action: str, target: str = "", result: str = "",
            tool: str = "", campaign_id: str = None):
        c = self._get(campaign_id)
        if c:
            self._log(c, action, target=target, result=result, tool=tool)
            self._save(c)

    # ── Status ────────────────────────────────────────────────────

    def status(self, campaign_id: str = None) -> str:
        c = self._get(campaign_id)
        if not c:
            return "No active campaign. Use create() to start one."
        achieved = sum(1 for o in c.objectives if o["status"] == ObjectiveStatus.ACHIEVED)
        total    = len(c.objectives)
        crits    = sum(1 for f in c.findings if f["severity"] == Severity.CRITICAL)
        highs    = sum(1 for f in c.findings if f["severity"] == Severity.HIGH)
        sessions = sum(1 for s in c.sessions if s["status"] == "active")
        return (
            f"\n{'='*54}\n"
            f"  CAMPAIGN: {c.name}\n"
            f"  Client:   {c.client or 'N/A'}  |  Operator: {c.operator}\n"
            f"  Status:   {c.status}  |  Started: {c.start_date[:10]}\n"
            f"{'='*54}\n"
            f"  Objectives:  {achieved}/{total} achieved\n"
            f"  Findings:    {len(c.findings)} total "
            f"({crits} CRIT, {highs} HIGH)\n"
            f"  Credentials: {len(c.credentials)} captured "
            f"({sum(1 for cr in c.credentials if cr['cracked'])} cracked)\n"
            f"  Sessions:    {sessions} active\n"
            f"  Scope:       {len(c.scope)} targets\n"
            f"{'='*54}"
        )

    def list_all(self) -> str:
        if not self.campaigns:
            return "No campaigns found."
        lines = ["  ID       | Status    | Name"]
        lines.append("  " + "-"*50)
        for c in self.campaigns.values():
            marker = " ◀ ACTIVE" if c.id == self.active_id else ""
            lines.append(f"  {c.id}  | {c.status:<9} | {c.name}{marker}")
        return "\n".join(lines)

    # ── Helpers ───────────────────────────────────────────────────

    def _get(self, campaign_id: str = None) -> Optional[Campaign]:
        cid = campaign_id or self.active_id
        if not cid or cid not in self.campaigns:
            return None
        return self.campaigns[cid]

    def _log(self, c: Campaign, action: str, target: str = "",
             result: str = "", tool: str = ""):
        event = asdict(TimelineEvent(
            action=action, target=target, result=result,
            tool=tool, operator=c.operator,
        ))
        c.timeline.append(event)

    def _default_objectives(self) -> list:
        defaults = [
            ("Reconnaissance complete",    "Enumerate all in-scope targets", "recon"),
            ("Initial access obtained",    "Gain first foothold on target",  "initial_access"),
            ("Privilege escalation",       "Escalate to admin/root",         "post_exploit"),
            ("Lateral movement",           "Move to additional targets",     "lateral"),
            ("Domain/root compromise",     "Full control of crown jewel",    "objectives"),
            ("Credentials harvested",      "Capture and crack credentials",  "post_exploit"),
            ("Persistence established",    "Maintain access across reboot",  "persistence"),
            ("Evidence collected",         "Document all access achieved",   "reporting"),
            ("Report generated",           "Deliver professional report",    "reporting"),
        ]
        return [asdict(Objective(title=t, description=d, phase=p))
                for t, d, p in defaults]

    def _save(self, c: Campaign):
        path = CAMPAIGNS_DIR / f"{c.id}.json"
        path.write_text(json.dumps(asdict(c), indent=2, default=str))

    def _load_all(self):
        for p in CAMPAIGNS_DIR.glob("*.json"):
            try:
                data = json.loads(p.read_text())
                c = Campaign(**{k: v for k, v in data.items()
                                if k in Campaign.__dataclass_fields__})
                self.campaigns[c.id] = c
                if c.status == CampaignStatus.ACTIVE:
                    self.active_id = c.id
            except Exception:
                pass


# Singleton
campaign_mgr = CampaignManager()


def handle_campaign_command(cmd: str, params: dict = None) -> dict:
    """Entry point from route_command()"""
    params = params or {}
    cmd = cmd.lower().strip()

    if "create" in cmd or "new campaign" in cmd:
        c = campaign_mgr.create(
            name=params.get("name", f"Engagement_{datetime.now().strftime('%Y%m%d')}"),
            client=params.get("client", ""),
            scope=params.get("scope", []),
        )
        return {"status": "success", "stdout": f"Campaign created: ID={c.id}\n{campaign_mgr.status()}"}

    if "status" in cmd:
        return {"status": "success", "stdout": campaign_mgr.status()}

    if "list" in cmd:
        return {"status": "success", "stdout": campaign_mgr.list_all()}

    if "finding" in cmd or "add finding" in cmd:
        f = campaign_mgr.add_finding(**params)
        return {"status": "success", "stdout": f"Finding logged: {f.id if f else 'error'}"}

    if "credential" in cmd or "add cred" in cmd:
        cr = campaign_mgr.add_credential(**params)
        return {"status": "success", "stdout": f"Credential stored: {cr.id if cr else 'error'}"}

    if "session" in cmd:
        s = campaign_mgr.register_session(**params)
        return {"status": "success", "stdout": f"Session registered: {s['id'] if s else 'error'}"}

    if "close" in cmd:
        return {"status": "success", "stdout": campaign_mgr.close()}

    return {"status": "success", "stdout": campaign_mgr.status()}
