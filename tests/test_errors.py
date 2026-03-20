"""
ERR0RS ULTIMATE - Test Suite
================================
Run ALL tests with:
    python3 tests/test_errors.py

This tests everything WITHOUT needing actual network targets.
It uses mock data to simulate what real tools would return,
then verifies the models, reporting, education, orchestrator,
and guardrails all work correctly.

TEACHING NOTE:
--------------
Writing tests before writing code is called TDD (Test-Driven
Development). Professional security tools ship with test suites.
Every feature in ERR0RS has a corresponding test. If a test
fails, something broke. This is how production software stays
reliable.
"""

import sys
import os
import unittest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.models import (
    Finding, ScanResult, EngagementSession, ReportConfig,
    Severity, PentestPhase, ToolStatus
)
from education.education_engine import EducationContent
from education.knowledge_base import get_education, list_all_topics
from reporting.html_reporter import HTMLReportEngine
from security.guardrails import EthicalGuardrails, TOOL_RISK_LEVELS


# =============================================================================
# TEST 1: Core Models
# =============================================================================

class TestCoreModels(unittest.TestCase):
    """Verify the data models work correctly."""

    def test_severity_ordering(self):
        """Critical should sort before High, etc."""
        self.assertLess(Severity.CRITICAL.priority_order, Severity.HIGH.priority_order)
        self.assertLess(Severity.HIGH.priority_order, Severity.MEDIUM.priority_order)
        self.assertLess(Severity.MEDIUM.priority_order, Severity.LOW.priority_order)
        self.assertLess(Severity.LOW.priority_order, Severity.INFO.priority_order)

    def test_severity_colors(self):
        """Each severity has a hex color."""
        for sev in Severity:
            self.assertTrue(sev.color_hex.startswith("#"))
            self.assertEqual(len(sev.color_hex), 7)

    def test_finding_creation(self):
        """Create a Finding and verify all fields."""
        f = Finding(
            title="Test Finding",
            description="A test",
            severity=Severity.HIGH,
            target="192.168.1.1",
            tool_name="nmap",
        )
        self.assertEqual(f.title, "Test Finding")
        self.assertEqual(f.severity, Severity.HIGH)
        self.assertIsNotNone(f.id)
        self.assertIsNotNone(f.timestamp)

    def test_finding_to_dict(self):
        """Verify Finding serializes to dict properly."""
        f = Finding(title="Serialize Me", severity=Severity.MEDIUM, target="10.0.0.1", tool_name="test")
        d = f.to_dict()
        self.assertEqual(d["title"], "Serialize Me")
        self.assertEqual(d["severity"], "Medium")
        self.assertIn("timestamp", d)

    def test_scan_result_highest_severity(self):
        """ScanResult should report the worst finding's severity."""
        findings = [
            Finding(title="Low", severity=Severity.LOW, target="x", tool_name="t"),
            Finding(title="Critical", severity=Severity.CRITICAL, target="x", tool_name="t"),
            Finding(title="Medium", severity=Severity.MEDIUM, target="x", tool_name="t"),
        ]
        sr = ScanResult(tool_name="test", findings=findings)
        self.assertEqual(sr.highest_severity, Severity.CRITICAL)

    def test_scan_result_empty_findings(self):
        """Empty ScanResult should have None highest severity."""
        sr = ScanResult(tool_name="test", findings=[])
        self.assertIsNone(sr.highest_severity)


# =============================================================================
# TEST 2: Education System
# =============================================================================

class TestEducation(unittest.TestCase):
    """Verify the knowledge base and education engine work."""

    def test_knowledge_base_not_empty(self):
        """At least some topics should exist."""
        topics = list_all_topics()
        self.assertGreater(len(topics), 0)

    def test_lookup_known_topic(self):
        """Looking up 'sql_injection' should return content."""
        edu = get_education("sql_injection")
        self.assertIsNotNone(edu)
        self.assertIn("SQL", edu.what)
        self.assertTrue(len(edu.how) > 0)
        self.assertTrue(len(edu.defend) > 0)

    def test_lookup_unknown_topic(self):
        """Unknown topic returns None gracefully — no crash."""
        edu = get_education("this_topic_does_not_exist_xyz")
        self.assertIsNone(edu)

    def test_education_to_markdown(self):
        """Education content renders to valid markdown."""
        edu = get_education("port_scanning")
        self.assertIsNotNone(edu)
        md = edu.to_markdown()
        self.assertIn("## 📚 Learning:", md)
        self.assertIn("### What is it?", md)
        self.assertIn("### How does it work?", md)

    def test_education_to_html(self):
        """Education content renders to HTML with card structure."""
        edu = get_education("brute_force")
        self.assertIsNotNone(edu)
        html = edu.to_html_block()
        self.assertIn("education-card", html)
        self.assertIn("edu-header", html)

    def test_multiple_topics_have_references(self):
        """All education entries should have at least one reference."""
        for topic in list_all_topics():
            edu = get_education(topic)
            self.assertIsNotNone(edu.references, f"{topic} has no references")
            self.assertGreater(len(edu.references), 0, f"{topic} references list is empty")


# =============================================================================
# TEST 3: HTML Report Generation
# =============================================================================

class TestReportGeneration(unittest.TestCase):
    """Verify the report engine produces valid output."""

    def _make_sample_session(self) -> EngagementSession:
        """Helper: build a realistic EngagementSession with mock data."""
        findings_recon = [
            Finding(title="Open Port 22/tcp — SSH",
                    description="SSH service detected on port 22.",
                    severity=Severity.MEDIUM, phase=PentestPhase.RECONNAISSANCE,
                    target="192.168.1.100", tool_name="nmap",
                    tags=["ssh", "remote_access"],
                    proof="22/tcp open ssh OpenSSH 8.2",
                    remediation="Disable password auth. Use keys only."),
            Finding(title="Open Port 3306/tcp — MySQL",
                    description="MySQL database exposed on network.",
                    severity=Severity.HIGH, phase=PentestPhase.RECONNAISSANCE,
                    target="192.168.1.100", tool_name="nmap",
                    tags=["mysql", "database"],
                    proof="3306/tcp open mysql MySQL 5.7.44",
                    remediation="Bind MySQL to localhost. Block at firewall."),
        ]
        findings_web = [
            Finding(title="SQL Injection Vulnerability Detected",
                    description="Confirmed SQLi on /login?user= parameter.",
                    severity=Severity.CRITICAL, phase=PentestPhase.EXPLOITATION,
                    target="http://192.168.1.100/login",
                    tool_name="sqlmap",
                    tags=["sql_injection", "owasp_a03"],
                    proof="Parameter 'user' is vulnerable (UNION-based)",
                    remediation="Use prepared statements. Input validation. WAF."),
        ]

        session = EngagementSession(
            name="Lab Network Assessment",
            client_name="Test Client",
            tester_name="Gary Holden Schneider",
            targets=["192.168.1.100", "192.168.1.101"],
            scope_notes="Internal lab network. Full scope authorized.",
            status="completed",
        )
        session.scan_results = [
            ScanResult(tool_name="nmap", status=ToolStatus.SUCCESS,
                       phase=PentestPhase.RECONNAISSANCE,
                       target="192.168.1.100", findings=findings_recon,
                       duration=12.3, command="nmap -sV -sC --open 192.168.1.100"),
            ScanResult(tool_name="sqlmap", status=ToolStatus.SUCCESS,
                       phase=PentestPhase.EXPLOITATION,
                       target="http://192.168.1.100/login", findings=findings_web,
                       duration=45.7, command="sqlmap -u http://192.168.1.100/login?user=1"),
        ]
        return session

    def test_report_generates_html(self):
        """Report engine produces a non-empty HTML string."""
        session = self._make_sample_session()
        engine = HTMLReportEngine(ReportConfig())
        html = engine.generate(session)
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("ERR0RS ULTIMATE", html)

    def test_report_contains_cover_page(self):
        """Cover page has client name and tester name."""
        session = self._make_sample_session()
        html = HTMLReportEngine().generate(session)
        self.assertIn("Test Client", html)
        self.assertIn("Gary Holden Schneider", html)

    def test_report_contains_executive_summary(self):
        """Executive summary section exists and has risk assessment."""
        session = self._make_sample_session()
        html = HTMLReportEngine(ReportConfig(include_executive=True)).generate(session)
        self.assertIn("Executive Summary", html)
        self.assertIn("Overall Risk Assessment", html)

    def test_report_contains_dashboard(self):
        """Dashboard shows severity counts."""
        session = self._make_sample_session()
        html = HTMLReportEngine().generate(session)
        self.assertIn("Findings Dashboard", html)
        self.assertIn("dash-critical", html)

    def test_report_contains_findings(self):
        """Each finding title appears in the report."""
        session = self._make_sample_session()
        html = HTMLReportEngine().generate(session)
        self.assertIn("SQL Injection Vulnerability Detected", html)
        self.assertIn("Open Port 22/tcp", html)
        self.assertIn("Open Port 3306/tcp", html)

    def test_report_contains_remediation_roadmap(self):
        """Remediation roadmap renders when enabled."""
        session = self._make_sample_session()
        html = HTMLReportEngine(ReportConfig(include_remediation=True)).generate(session)
        self.assertIn("Remediation Roadmap", html)

    def test_report_severity_filter(self):
        """Severity filter hides findings below threshold."""
        session = self._make_sample_session()
        config = ReportConfig(severity_filter=Severity.HIGH)  # Only Critical + High
        html = HTMLReportEngine(config).generate(session)
        self.assertIn("SQL Injection", html)       # Critical — shown
        self.assertIn("MySQL", html)               # High — shown
        self.assertNotIn("Open Port 22", html)     # Medium — filtered out


# =============================================================================
# TEST 4: Security Guardrails
# =============================================================================

class TestGuardrails(unittest.TestCase):
    """Verify ethical guardrails block what they should."""

    def setUp(self):
        # No auth manager = lab mode (all targets allowed)
        self.guardrails = EthicalGuardrails(authorization_manager=None)

    def test_clean_command_passes(self):
        """Normal nmap command should pass all checks."""
        allowed, reason = self.guardrails.check_execution(
            tool_name="nmap",
            target="192.168.1.1",
            command="nmap -sV 192.168.1.1"
        )
        self.assertTrue(allowed)

    def test_rm_rf_blocked(self):
        """rm -rf should ALWAYS be blocked."""
        allowed, reason = self.guardrails.check_execution(
            tool_name="unknown",
            target="192.168.1.1",
            command="rm -rf /tmp/data"
        )
        self.assertFalse(allowed)
        self.assertIn("BLOCKED", reason)

    def test_format_blocked(self):
        """Disk format commands are blocked."""
        allowed, reason = self.guardrails.check_execution(
            tool_name="unknown",
            target="x",
            command="format C: /FS:NTFS"
        )
        self.assertFalse(allowed)

    def test_shutdown_blocked(self):
        """Shutdown commands are blocked."""
        allowed, reason = self.guardrails.check_execution(
            tool_name="unknown",
            target="x",
            command="shutdown -h now"
        )
        self.assertFalse(allowed)

    def test_known_tools_have_risk_levels(self):
        """All critical tools should have defined risk levels."""
        critical_tools = ["nmap", "sqlmap", "hydra", "metasploit", "gobuster"]
        for tool in critical_tools:
            self.assertIn(tool, TOOL_RISK_LEVELS, f"{tool} missing from risk map")


# =============================================================================
# TEST 5: Engagement Session Aggregation
# =============================================================================

class TestEngagementSession(unittest.TestCase):
    """Test the session-level aggregation logic."""

    def _build_session(self):
        s = EngagementSession(
            name="Test", targets=["10.0.0.1"],
            scan_results=[
                ScanResult(tool_name="nmap", findings=[
                    Finding(title="A", severity=Severity.INFO, target="10.0.0.1", tool_name="nmap"),
                    Finding(title="B", severity=Severity.HIGH, target="10.0.0.1", tool_name="nmap"),
                ], duration=5.0),
                ScanResult(tool_name="sqlmap", findings=[
                    Finding(title="C", severity=Severity.CRITICAL, target="10.0.0.1", tool_name="sqlmap"),
                ], duration=10.0),
            ]
        )
        return s

    def test_all_findings_flattened(self):
        """all_findings returns every finding across all scans."""
        s = self._build_session()
        self.assertEqual(len(s.all_findings), 3)

    def test_finding_summary_counts(self):
        """finding_summary counts each severity correctly."""
        s = self._build_session()
        summary = s.finding_summary
        self.assertEqual(summary["Critical"], 1)
        self.assertEqual(summary["High"], 1)
        self.assertEqual(summary["Info"], 1)
        self.assertEqual(summary["Medium"], 0)
        self.assertEqual(summary["Low"], 0)

    def test_total_duration(self):
        """total_duration_seconds sums all scan durations."""
        s = self._build_session()
        self.assertAlmostEqual(s.total_duration_seconds, 15.0)

    def test_session_to_dict(self):
        """Session serializes properly."""
        s = self._build_session()
        d = s.to_dict()
        self.assertEqual(d["name"], "Test")
        self.assertEqual(d["total_findings"], 3)
        self.assertEqual(d["scan_count"], 2)


# =============================================================================
# TEST RUNNER
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  ERR0RS ULTIMATE — Test Suite")
    print("=" * 60)
    print()

    # Run with verbose output so you see every test name
    unittest.main(verbosity=2)
