"""
╔══════════════════════════════════════════════════════════════════╗
║   ERR0RS ULTIMATE — MODULE 4: Engagement Memory & Knowledge Graph║
║                   src/memory/engagement_memory.py                ║
║                                                                  ║
║  Every engagement teaches ERR0RS something. This module builds   ║
║  a local knowledge graph that grows smarter with every job.      ║
║  When you start a new engagement, ERR0RS says:                   ║
║  "Last time I hit a similar target, THIS attack chain worked."   ║
║                                                                  ║
║  100% LOCAL — graph stored as JSON on disk. No cloud. No leaks.  ║
╚══════════════════════════════════════════════════════════════════╝

WHAT THIS STORES (Visual):
──────────────────────────
  [Engagement A — Apache 2.4.49, Ubuntu 20]
    └─ CVE-2021-41773 exploited via Metasploit
         └─ Privilege escalation via sudo misconfig
              └─ Total time: 23 minutes

  [Engagement B — Same tech stack]
    ← ERR0RS says: "I've seen this before. Here's what worked."
    ← Proposes attack chain from Engagement A as starting point

THE KNOWLEDGE GRAPH:
────────────────────
  Nodes:
    • Technology nodes (Apache 2.4.49, OpenSSH 8.x, MySQL 5.7...)
    • Vulnerability nodes (CVE IDs, finding titles)
    • Attack nodes (Exploit names, payloads, techniques)
    • Target type nodes (web server, domain controller, IoT...)

  Edges:
    • "is_vulnerable_to"  (Tech → CVE)
    • "exploited_by"      (CVE → Attack)
    • "leads_to"          (Attack → next Attack)
    • "detected_on"       (CVE → TargetType)
    • "bypassed_by"       (Detection → Technique)

QUERY EXAMPLES:
───────────────
  "What worked against Apache 2.4.x before?"
  "Which privilege escalation techniques worked on Ubuntu?"
  "What's the fastest path from port 80 to root?"
  "Which wordlists cracked passwords on this target type?"
"""

import os
import sys
import json
import time
import hashlib
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from src.core.models import EngagementSession, Finding, ScanResult, Severity, PentestPhase

log = logging.getLogger("errors.memory.engagement_memory")


# ─────────────────────────────────────────────────────────────────
# GRAPH DATA MODELS
# ─────────────────────────────────────────────────────────────────

@dataclass
class GraphNode:
    """A node in the knowledge graph."""
    id:         str
    node_type:  str       # technology | vulnerability | attack | target_type | credential
    label:      str
    properties: Dict = field(default_factory=dict)
    seen_count: int = 1   # How many times we've encountered this
    first_seen: str = field(default_factory=lambda: datetime.now().isoformat())
    last_seen:  str = field(default_factory=lambda: datetime.now().isoformat())

    def update_seen(self):
        self.seen_count += 1
        self.last_seen = datetime.now().isoformat()


@dataclass
class GraphEdge:
    """A directed edge between two nodes."""
    id:           str
    source_id:    str
    target_id:    str
    relationship: str     # is_vulnerable_to | exploited_by | leads_to | found_on etc.
    weight:       float = 1.0   # Higher = more reliable relationship
    evidence:     List[str] = field(default_factory=list)  # Engagement IDs that confirmed this
    success_rate: float = 1.0   # What % of the time this path worked
    avg_time_sec: float = 0.0   # Average time this step took

    def update(self, success: bool, time_taken: float = 0.0):
        """Update edge statistics with new observation."""
        n = len(self.evidence)
        self.success_rate = ((self.success_rate * n) + (1.0 if success else 0.0)) / (n + 1)
        if time_taken > 0:
            self.avg_time_sec = ((self.avg_time_sec * n) + time_taken) / (n + 1)
        self.weight = self.success_rate * (1.0 + len(self.evidence) * 0.1)


@dataclass
class AttackPattern:
    """
    A stored attack pattern — a sequence of steps that successfully
    compromised a particular type of target.
    """
    id:           str = field(default_factory=lambda: f"ap_{int(time.time())}")
    name:         str = ""
    target_type:  str = ""      # "web_server", "windows_ad", "linux_server" etc.
    tech_stack:   List[str] = field(default_factory=list)   # Technologies involved
    steps:        List[Dict] = field(default_factory=list)  # Ordered attack steps
    success_count: int = 1
    total_time_sec: float = 0.0
    avg_severity:   str = "High"
    engagement_ids: List[str] = field(default_factory=list)
    created_at:    str = field(default_factory=lambda: datetime.now().isoformat())
    last_used:     str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def success_rate(self) -> float:
        return self.success_count / max(len(self.engagement_ids), 1)

    def to_summary(self) -> str:
        steps_str = " → ".join([s.get("tool", "?") for s in self.steps])
        return (f"[{self.name}] Target: {self.target_type} | "
                f"Stack: {', '.join(self.tech_stack[:3])} | "
                f"Steps: {steps_str} | "
                f"Successes: {self.success_count} | "
                f"Avg time: {self.total_time_sec/60:.1f}min")


@dataclass
class CredentialRecord:
    """
    Stores anonymized credential intelligence (hashes, patterns, not plaintext).
    Used to recognize patterns — e.g. "this target type tends to reuse default creds."
    NEVER stores actual plaintext passwords.
    """
    id:             str = field(default_factory=lambda: f"cred_{int(time.time())}")
    target_type:    str = ""
    service:        str = ""
    wordlist_used:  str = ""
    cracked:        bool = False
    hash_type:      str = ""       # md5, ntlm, bcrypt etc.
    pattern_hint:   str = ""       # e.g. "Season+Year format", never actual password
    engagement_id:  str = ""


# ─────────────────────────────────────────────────────────────────
# KNOWLEDGE GRAPH
# ─────────────────────────────────────────────────────────────────

class KnowledgeGraph:
    """
    Core graph data structure. Nodes and edges stored as dicts in JSON.
    Supports querying by node type, relationship, and properties.
    """

    def __init__(self):
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: Dict[str, GraphEdge] = {}

    def add_node(self, node_id: str, node_type: str, label: str,
                 properties: dict = None) -> GraphNode:
        if node_id in self.nodes:
            self.nodes[node_id].update_seen()
            if properties:
                self.nodes[node_id].properties.update(properties)
            return self.nodes[node_id]
        node = GraphNode(id=node_id, node_type=node_type, label=label,
                         properties=properties or {})
        self.nodes[node_id] = node
        return node

    def add_edge(self, source_id: str, target_id: str, relationship: str,
                 evidence_id: str = "", success: bool = True,
                 time_sec: float = 0.0) -> GraphEdge:
        edge_id = f"{source_id}__{relationship}__{target_id}"
        if edge_id in self.edges:
            edge = self.edges[edge_id]
            if evidence_id and evidence_id not in edge.evidence:
                edge.evidence.append(evidence_id)
            edge.update(success, time_sec)
            return edge
        edge = GraphEdge(
            id=edge_id, source_id=source_id, target_id=target_id,
            relationship=relationship, evidence=[evidence_id] if evidence_id else [],
        )
        self.edges[edge_id] = edge
        return edge

    def get_neighbors(self, node_id: str, relationship: str = None,
                      direction: str = "outbound") -> List[Tuple[GraphEdge, GraphNode]]:
        """Get all neighboring nodes connected by a given relationship."""
        results = []
        for edge in self.edges.values():
            if direction in ("outbound", "both") and edge.source_id == node_id:
                if relationship is None or edge.relationship == relationship:
                    target = self.nodes.get(edge.target_id)
                    if target:
                        results.append((edge, target))
            if direction in ("inbound", "both") and edge.target_id == node_id:
                if relationship is None or edge.relationship == relationship:
                    source = self.nodes.get(edge.source_id)
                    if source:
                        results.append((edge, source))
        return sorted(results, key=lambda x: x[0].weight, reverse=True)

    def find_nodes(self, node_type: str = None, label_contains: str = None) -> List[GraphNode]:
        results = []
        for node in self.nodes.values():
            if node_type and node.node_type != node_type:
                continue
            if label_contains and label_contains.lower() not in node.label.lower():
                continue
            results.append(node)
        return sorted(results, key=lambda n: n.seen_count, reverse=True)

    def find_attack_paths(self, from_node_id: str,
                          max_depth: int = 5) -> List[List[GraphEdge]]:
        """BFS to find all attack paths from a starting node."""
        paths = []
        queue = [([from_node_id], [])]
        while queue:
            current_path, edge_path = queue.pop(0)
            if len(current_path) > max_depth:
                continue
            neighbors = self.get_neighbors(current_path[-1], direction="outbound")
            if not neighbors and len(edge_path) > 0:
                paths.append(edge_path)
            for edge, neighbor in neighbors:
                if neighbor.id not in current_path:
                    queue.append((current_path + [neighbor.id],
                                  edge_path + [edge]))
        return sorted(paths, key=lambda p: sum(e.weight for e in p), reverse=True)

    def to_dict(self) -> dict:
        return {
            "nodes": {k: asdict(v) for k, v in self.nodes.items()},
            "edges": {k: asdict(v) for k, v in self.edges.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "KnowledgeGraph":
        g = cls()
        for k, v in data.get("nodes", {}).items():
            g.nodes[k] = GraphNode(**v)
        for k, v in data.get("edges", {}).items():
            g.edges[k] = GraphEdge(**v)
        return g



# ─────────────────────────────────────────────────────────────────
# ENGAGEMENT INGESTER — Extracts knowledge from completed sessions
# ─────────────────────────────────────────────────────────────────

class EngagementIngester:
    """
    Takes a completed EngagementSession and extracts all learnable
    intelligence into the knowledge graph.

    What it extracts:
    - Service/version combos seen on targets
    - Which CVEs/findings were confirmed
    - Which tools successfully exploited them
    - Timing data (how long each phase took)
    - Attack chain (what led to what)
    - Target type classification
    """

    # Map service names to technology node IDs
    SERVICE_NORMALIZER = {
        "http": "http_server", "https": "http_server",
        "ssh": "ssh", "ftp": "ftp",
        "mysql": "mysql", "postgresql": "postgresql",
        "ms-sql": "mssql", "mssql": "mssql",
        "smb": "smb", "microsoft-ds": "smb",
        "rdp": "rdp", "ms-wbt-server": "rdp",
        "mongodb": "mongodb", "redis": "redis",
        "elasticsearch": "elasticsearch",
    }

    def ingest(self, session: EngagementSession,
               graph: KnowledgeGraph) -> List[AttackPattern]:
        """
        Process a completed session into the knowledge graph.
        Returns any new AttackPatterns discovered.
        """
        log.info(f"[MEMORY] Ingesting session: {session.name}")
        target_type = self._classify_target(session)
        patterns = []

        # Add target type node
        tt_node_id = f"tt_{target_type.replace(' ', '_').lower()}"
        graph.add_node(tt_node_id, "target_type", target_type,
                       {"engagement_id": session.id})

        # Process each scan result
        for scan in session.scan_results:
            # Add technology nodes from service detection
            tech_node_id = self._add_tech_node(scan, graph)

            # Add finding/vulnerability nodes
            for finding in scan.findings:
                vuln_id = self._finding_to_node_id(finding)
                graph.add_node(vuln_id, "vulnerability", finding.title, {
                    "severity": finding.severity.value,
                    "tool": finding.tool_name,
                    "phase": finding.phase.value,
                })

                # Edge: technology → vulnerability
                if tech_node_id:
                    graph.add_edge(
                        tech_node_id, vuln_id, "is_vulnerable_to",
                        evidence_id=session.id,
                        success=True,
                        time_sec=scan.duration,
                    )

                # Edge: vulnerability → target type
                graph.add_edge(
                    vuln_id, tt_node_id, "found_on",
                    evidence_id=session.id,
                )

                # Add attack/exploit nodes for successful exploits
                if finding.phase == PentestPhase.EXPLOITATION and finding.tool_name:
                    attack_id = f"attack_{finding.tool_name}_{vuln_id}"
                    graph.add_node(attack_id, "attack", f"{finding.tool_name} — {finding.title}", {
                        "tool": finding.tool_name,
                        "technique": finding.tags[0] if finding.tags else "",
                    })
                    graph.add_edge(vuln_id, attack_id, "exploited_by",
                                   evidence_id=session.id, success=True)

        # Build attack chain edges (Phase ordering creates natural "leads_to" relationships)
        chain_pattern = self._build_chain_pattern(session, target_type, graph)
        if chain_pattern:
            patterns.append(chain_pattern)

        log.info(f"[MEMORY] Ingested: {len(session.all_findings)} findings, "
                 f"target_type: {target_type}")
        return patterns

    def _classify_target(self, session: EngagementSession) -> str:
        """Try to classify the target type from its findings and services."""
        finding_tools = set(f.tool_name for f in session.all_findings)
        if "bloodhound" in finding_tools or "mimikatz" in finding_tools:
            return "windows_active_directory"
        if "wifite" in finding_tools or "aircrack" in finding_tools:
            return "wireless_network"
        if "sqlmap" in finding_tools:
            return "web_application"
        # Check for common web services
        for scan in session.scan_results:
            if "http" in scan.tool_name.lower() or "nikto" in scan.tool_name.lower():
                return "web_server"
        return "generic_server"

    def _add_tech_node(self, scan: ScanResult,
                       graph: KnowledgeGraph) -> Optional[str]:
        """Create a technology node from scan data."""
        service = self.SERVICE_NORMALIZER.get(scan.tool_name.lower(), scan.tool_name.lower())
        if not service:
            return None
        node_id = f"tech_{service}"
        graph.add_node(node_id, "technology", scan.tool_name, {
            "service": service,
        })
        return node_id

    def _finding_to_node_id(self, finding: Finding) -> str:
        """Create a stable node ID for a finding."""
        key = f"{finding.title}_{finding.tool_name}"
        return f"vuln_{hashlib.md5(key.encode()).hexdigest()[:10]}"

    def _build_chain_pattern(self, session: EngagementSession,
                              target_type: str,
                              graph: KnowledgeGraph) -> Optional[AttackPattern]:
        """Extract a reusable attack pattern from the engagement chain."""
        findings = sorted(
            session.all_findings,
            key=lambda f: (
                {PentestPhase.RECONNAISSANCE: 0, PentestPhase.SCANNING: 1,
                 PentestPhase.ENUMERATION: 2, PentestPhase.EXPLOITATION: 3,
                 PentestPhase.POST_EXPLOIT: 4}.get(f.phase, 5),
                f.timestamp
            )
        )
        if len(findings) < 2:
            return None

        steps = [
            {
                "step": i + 1,
                "phase": f.phase.value,
                "tool": f.tool_name,
                "finding": f.title,
                "severity": f.severity.value,
            }
            for i, f in enumerate(findings)
        ]

        tech_stack = list(set(f.tool_name for f in findings if f.tool_name))
        name = f"{target_type.replace('_', ' ').title()} via {', '.join(tech_stack[:2])}"

        return AttackPattern(
            name           = name,
            target_type    = target_type,
            tech_stack     = tech_stack,
            steps          = steps,
            total_time_sec = session.total_duration_seconds,
            engagement_ids = [session.id],
            avg_severity   = findings[0].severity.value if findings else "Medium",
        )


# ─────────────────────────────────────────────────────────────────
# ENGAGEMENT MEMORY — Main class
# ─────────────────────────────────────────────────────────────────

class EngagementMemory:
    """
    Main memory system. Persists the knowledge graph and attack patterns
    across all engagements. Gets smarter with every job.

    Usage:
        memory = EngagementMemory()

        # After an engagement completes:
        memory.learn(completed_session)

        # Before starting a new engagement:
        recommendations = memory.recommend("192.168.1.100", context="Apache web server")
        for rec in recommendations:
            print(rec)

        # Query what's worked before:
        patterns = memory.find_patterns("web_application")
        best = patterns[0]
        print(best.to_summary())
    """

    def __init__(self, memory_dir: str = "./engagement_memory"):
        self.memory_dir   = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.graph        = self._load_graph()
        self.patterns:    List[AttackPattern] = self._load_patterns()
        self.credentials: List[CredentialRecord] = self._load_creds()
        self.ingester     = EngagementIngester()
        log.info(f"[MEMORY] Loaded graph: {len(self.graph.nodes)} nodes, "
                 f"{len(self.graph.edges)} edges, "
                 f"{len(self.patterns)} patterns")

    # ── Learning ──────────────────────────────────────────────────

    def learn(self, session: EngagementSession):
        """
        Ingest a completed engagement session into memory.
        Call this at the end of every engagement.
        """
        print(f"\n[MEMORY] Learning from: {session.name}")
        new_patterns = self.ingester.ingest(session, self.graph)
        for pattern in new_patterns:
            self._merge_pattern(pattern)
        self._save_all()
        print(f"[MEMORY] ✅ Learned {len(session.all_findings)} findings. "
              f"Graph now: {len(self.graph.nodes)} nodes, {len(self.graph.edges)} edges.")

    def _merge_pattern(self, new_pattern: AttackPattern):
        """Merge a new pattern into existing ones or add as new."""
        for existing in self.patterns:
            if (existing.target_type == new_pattern.target_type and
                    set(existing.tech_stack[:2]) == set(new_pattern.tech_stack[:2])):
                # Merge into existing
                existing.success_count += 1
                existing.engagement_ids.extend(new_pattern.engagement_ids)
                existing.last_used = datetime.now().isoformat()
                existing.total_time_sec = (
                    (existing.total_time_sec * (existing.success_count - 1) +
                     new_pattern.total_time_sec) / existing.success_count
                )
                return
        self.patterns.append(new_pattern)

    # ── Querying & Recommendations ────────────────────────────────

    def recommend(self, target: str, context: str = "",
                  top_n: int = 3) -> List[str]:
        """
        Given a target and context, recommend attack approaches
        based on past successful engagements.
        """
        recommendations = []

        # Find patterns that match the context
        context_lower = context.lower()
        relevant = [p for p in self.patterns
                    if any(t.lower() in context_lower for t in p.tech_stack)
                    or p.target_type.lower().replace("_", " ") in context_lower]

        if not relevant:
            relevant = sorted(self.patterns, key=lambda p: p.success_count, reverse=True)

        for pattern in relevant[:top_n]:
            steps_str = " → ".join([s.get("tool", "?") for s in pattern.steps[:4]])
            avg_min = pattern.total_time_sec / 60
            recommendations.append(
                f"🎯 Pattern: '{pattern.name}'\n"
                f"   Seen {pattern.success_count}x on {pattern.target_type} targets\n"
                f"   Chain: {steps_str}\n"
                f"   Avg time to completion: {avg_min:.0f} minutes\n"
                f"   Last used: {pattern.last_used[:10]}"
            )

        # Add graph-based recommendations
        tech_nodes = self.graph.find_nodes("technology", label_contains=context[:20])
        for node in tech_nodes[:2]:
            vulns = self.graph.get_neighbors(node.id, "is_vulnerable_to")
            for edge, vuln_node in vulns[:2]:
                recommendations.append(
                    f"💡 '{node.label}' has known vulnerability: {vuln_node.label} "
                    f"(seen {edge.weight:.1f}x, success rate {edge.success_rate:.0%})"
                )

        if not recommendations:
            recommendations.append(
                "No prior engagement data matches this target context. "
                "This will be a new pattern — results will be learned after completion."
            )
        return recommendations

    def find_patterns(self, target_type: str = None) -> List[AttackPattern]:
        """Return attack patterns, optionally filtered by target type."""
        if not target_type:
            return sorted(self.patterns, key=lambda p: p.success_count, reverse=True)
        return [p for p in self.patterns
                if target_type.lower() in p.target_type.lower()]

    def what_worked_against(self, technology: str) -> str:
        """Plain-English summary of what's worked against a technology."""
        nodes = self.graph.find_nodes("technology", label_contains=technology)
        if not nodes:
            return f"No prior data for '{technology}'."

        lines = [f"📚 Knowledge about '{technology}':"]
        for node in nodes[:3]:
            lines.append(f"\n  Tech: {node.label} (seen {node.seen_count}x)")
            vulns = self.graph.get_neighbors(node.id, "is_vulnerable_to")
            for edge, vuln in vulns[:3]:
                lines.append(f"    Vulnerable to: {vuln.label} "
                              f"(confirmed {len(edge.evidence)}x)")
                attacks = self.graph.get_neighbors(vuln.id, "exploited_by")
                for _, atk in attacks[:2]:
                    lines.append(f"      Exploited by: {atk.label}")
        return "\n".join(lines)

    def get_stats(self) -> dict:
        """Return memory statistics."""
        return {
            "total_engagements_learned": len(set(
                eid for p in self.patterns for eid in p.engagement_ids
            )),
            "graph_nodes": len(self.graph.nodes),
            "graph_edges": len(self.graph.edges),
            "attack_patterns": len(self.patterns),
            "top_target_types": [
                p.target_type for p in
                sorted(self.patterns, key=lambda x: x.success_count, reverse=True)[:3]
            ],
        }

    # ── Persistence ───────────────────────────────────────────────

    def _save_all(self):
        (self.memory_dir / "graph.json").write_text(
            json.dumps(self.graph.to_dict(), indent=2, default=str)
        )
        (self.memory_dir / "patterns.json").write_text(
            json.dumps([asdict(p) for p in self.patterns], indent=2, default=str)
        )

    def _load_graph(self) -> KnowledgeGraph:
        path = self.memory_dir / "graph.json"
        if path.exists():
            try:
                return KnowledgeGraph.from_dict(json.loads(path.read_text()))
            except Exception as e:
                log.warning(f"Graph load failed: {e}")
        return KnowledgeGraph()

    def _load_patterns(self) -> List[AttackPattern]:
        path = self.memory_dir / "patterns.json"
        if path.exists():
            try:
                return [AttackPattern(**p) for p in json.loads(path.read_text())]
            except Exception as e:
                log.warning(f"Patterns load failed: {e}")
        return []

    def _load_creds(self) -> List[CredentialRecord]:
        path = self.memory_dir / "cred_intel.json"
        if path.exists():
            try:
                return [CredentialRecord(**c) for c in json.loads(path.read_text())]
            except Exception:
                pass
        return []


__all__ = [
    "EngagementMemory", "KnowledgeGraph",
    "GraphNode", "GraphEdge", "AttackPattern",
    "EngagementIngester", "CredentialRecord",
]
