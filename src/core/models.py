"""
ERR0RS ULTIMATE - Core Data Models
===================================
Every finding, scan result, and report in the entire framework
flows through these models. This is the single source of truth
for how data is structured.

TEACHING NOTE:
--------------
In real penetration testing, consistent data modeling is what
separates amateur tools from professional ones. When Nmap finds
an open port, when SQLMap finds an injection, when Metasploit
gets a shell — they all need to produce findings that look and
feel the same so the report engine can unify them.

This is how professional pentest firms do it. Every tool writes
to the same schema. The report reads from the same schema.
Nothing gets lost or reformatted manually.
"""

from enum import Enum
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
import uuid


# ---------------------------------------------------------------------------
# SEVERITY LEVELS
# ---------------------------------------------------------------------------
# These map directly to CVSS (Common Vulnerability Scoring System).
# This is the industry standard. Every CVE on the internet uses this.
# TEACHING NOTE: When you read a CVE advisory, these are the exact
# categories you will see. Understanding them is fundamental.
# ---------------------------------------------------------------------------

class Severity(Enum):
    CRITICAL = "Critical"    # CVSS 9.0-10.0 — Immediate exploitation likely
    HIGH     = "High"        # CVSS 7.0-8.9  — Significant risk
    MEDIUM   = "Medium"      # CVSS 4.0-6.9  — Moderate risk
    LOW      = "Low"         # CVSS 2.0-3.9  — Minor risk
    INFO     = "Info"        # CVSS 0.0-1.9  — Informational only

    @property
    def cvss_range(self) -> str:
        ranges = {
            "Critical": "9.0 - 10.0",
            "High":     "7.0 - 8.9",
            "Medium":   "4.0 - 6.9",
            "Low":      "2.0 - 3.9",
            "Info":     "0.0 - 1.9",
        }
        return ranges[self.value]

    @property
    def color_hex(self) -> str:
        colors = {
            "Critical": "#ff2d2d",
            "High":     "#ff8c00",
            "Medium":   "#ffd700",
            "Low":      "#4caf50",
            "Info":     "#2196f3",
        }
        return colors[self.value]

    @property
    def priority_order(self) -> int:
        """Lower number = higher priority for sorting."""
        order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "Info": 4}
        return order[self.value]


# ---------------------------------------------------------------------------
# PENTEST PHASES
# ---------------------------------------------------------------------------
# TEACHING NOTE: A professional pentest follows a structured kill chain.
# Every phase has a purpose. Skipping phases = missing findings.
# This is what frameworks like PTES and OWASP Testing Guide define.
# ---------------------------------------------------------------------------

class PentestPhase(Enum):
    RECONNAISSANCE  = "Reconnaissance"   # Gather info, don't touch target
    SCANNING        = "Scanning"         # Active probing — ports, services
    ENUMERATION     = "Enumeration"      # Dig deeper into what's running
    EXPLOITATION    = "Exploitation"     # Turn vulns into access
    POST_EXPLOIT    = "Post-Exploitation"# What can you do with access?
    REPORTING       = "Reporting"        # Document everything


class ToolStatus(Enum):
    PENDING  = "pending"
    RUNNING  = "running"
    SUCCESS  = "success"
    FAILED   = "failed"
    TIMEOUT  = "timeout"


# ---------------------------------------------------------------------------
# CORE DATACLASSES — THE BUILDING BLOCKS
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    """
    A single security finding. This is the atomic unit of a pentest.
    Every tool produces one or more Findings. The report engine reads them.

    TEACHING NOTE:
    A "finding" in professional pentesting is NOT just "I found a bug."
    It is a structured document: what was found, where, how bad it is,
    how to prove it, and how to fix it. THIS is what clients pay for.
    """
    id:              str              = field(default_factory=lambda: str(uuid.uuid4()))
    title:           str              = ""
    description:     str              = ""
    severity:        Severity         = Severity.INFO
    phase:           PentestPhase     = PentestPhase.SCANNING
    target:          str              = ""          # IP, domain, or URL
    tool_name:       str              = ""          # Which tool found this
    raw_output:      str              = ""          # Unprocessed tool output
    proof:           str              = ""          # Evidence (screenshot, payload, etc.)
    remediation:     str              = ""          # How to fix it
    references:      List[str]        = field(default_factory=list)   # CVEs, docs
    tags:            List[str]        = field(default_factory=list)   # OWASP, CWE
    timestamp:       datetime         = field(default_factory=datetime.now)
    confidence:      float            = 0.0         # 0.0-1.0 how sure the tool is
    false_positive:  bool             = False
    education:       Optional[str]    = None        # Teaching content for this finding

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "phase": self.phase.value,
            "target": self.target,
            "tool_name": self.tool_name,
            "proof": self.proof,
            "remediation": self.remediation,
            "references": self.references,
            "tags": self.tags,
            "timestamp": self.timestamp.isoformat(),
            "confidence": self.confidence,
            "education": self.education,
        }


@dataclass
class ScanResult:
    """
    The output of a single tool execution. One tool run = one ScanResult.
    A ScanResult contains zero or more Findings.

    TEACHING NOTE:
    Not every scan produces findings. A clean scan (zero findings) is
    still valuable data — it means that attack surface is hardened.
    Professional reports always include clean scans too.
    """
    id:         str                  = field(default_factory=lambda: str(uuid.uuid4()))
    tool_name:  str                  = ""
    status:     ToolStatus           = ToolStatus.PENDING
    phase:      PentestPhase         = PentestPhase.SCANNING
    target:     str                  = ""
    command:    str                  = ""            # Exact command that ran
    findings:   List[Finding]        = field(default_factory=list)
    raw_output: str                  = ""
    started_at: Optional[datetime]   = None
    ended_at:   Optional[datetime]   = None
    duration:   float                = 0.0           # seconds
    error_msg:  Optional[str]        = None

    @property
    def finding_count(self) -> int:
        return len(self.findings)

    @property
    def highest_severity(self) -> Optional[Severity]:
        if not self.findings:
            return None
        return min(self.findings, key=lambda f: f.severity.priority_order).severity

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tool_name": self.tool_name,
            "status": self.status.value,
            "phase": self.phase.value,
            "target": self.target,
            "command": self.command,
            "findings": [f.to_dict() for f in self.findings],
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "duration": self.duration,
        }


# ---------------------------------------------------------------------------
# ENGAGEMENT SESSION — THE FULL PENTEST CONTAINER
# ---------------------------------------------------------------------------
# TEACHING NOTE:
# In the real world, a "pentest engagement" is a contract. You have a
# defined scope (what targets), a timeline, rules of engagement, and a
# client. Everything you do gets logged under one engagement. This model
# mirrors exactly how professional firms structure their work.
# ---------------------------------------------------------------------------

@dataclass
class EngagementSession:
    """
    Top-level container for an entire pentest engagement.
    One session = one full pentest job, from recon through reporting.
    """
    id:              str                  = field(default_factory=lambda: str(uuid.uuid4()))
    name:            str                  = "Unnamed Engagement"
    client_name:     str                  = ""
    tester_name:     str                  = ""
    targets:         List[str]            = field(default_factory=list)
    scope_notes:     str                  = ""       # Rules of engagement
    started_at:      datetime             = field(default_factory=datetime.now)
    ended_at:        Optional[datetime]   = None
    scan_results:    List[ScanResult]     = field(default_factory=list)
    status:          str                  = "active" # active | completed | archived
    notes:           str                  = ""

    @property
    def all_findings(self) -> List[Finding]:
        """Flatten all findings from all scan results."""
        findings = []
        for result in self.scan_results:
            findings.extend(result.findings)
        return findings

    @property
    def finding_summary(self) -> Dict[str, int]:
        """
        Count findings by severity. This is the NUMBER ONE thing
        that goes on page 1 of every professional pentest report.
        """
        summary = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0, "Info": 0}
        for f in self.all_findings:
            summary[f.severity.value] += 1
        return summary

    @property
    def total_duration_seconds(self) -> float:
        return sum(r.duration for r in self.scan_results)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "client_name": self.client_name,
            "tester_name": self.tester_name,
            "targets": self.targets,
            "scope_notes": self.scope_notes,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "status": self.status,
            "finding_summary": self.finding_summary,
            "total_findings": len(self.all_findings),
            "scan_count": len(self.scan_results),
        }


# ---------------------------------------------------------------------------
# REPORT CONFIGURATION
# ---------------------------------------------------------------------------

@dataclass
class ReportConfig:
    """
    Controls what a generated report looks like and contains.
    Separates WHAT to report from HOW to format it.
    """
    format:              str      = "html"      # html | pdf | markdown | json
    template:            str      = "professional"  # professional | executive | technical
    include_executive:   bool     = True         # Exec summary (non-technical)
    include_technical:   bool     = True         # Full technical details
    include_education:   bool     = True         # Teaching explanations
    include_remediation: bool     = True         # How to fix each finding
    include_raw_output:  bool     = False        # Raw tool output (verbose)
    include_timeline:    bool     = True         # Visual timeline of the engagement
    severity_filter:     Optional[Severity] = None  # Only show this severity+
    logo_path:           Optional[str]       = None
    company_name:        str      = "ERR0RS Security Assessment"
