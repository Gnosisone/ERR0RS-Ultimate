#!/usr/bin/env python3
"""
ERR0RS ULTIMATE - Nuclei Integration
Fast vulnerability scanner using templates

Nuclei is used to send requests across targets based on templates,
leading to zero false positives and effective scanning for thousands
of various security checks.

Features:
- Template-based scanning
- 1000+ built-in templates
- Custom template support
- Fast concurrent scanning
- YAML-based templates
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional
from pathlib import Path

from ..core.base_tool import BaseTool, ToolCategory, ToolStatus, ToolResult

logger = logging.getLogger(__name__)


class NucleiTool(BaseTool):
    """
    Nuclei - Fast vulnerability scanner
    
    Template-based vulnerability detection
    """
    
    def __init__(self):
        super().__init__(
            name="Nuclei",
            category=ToolCategory.WEB,
            description="Fast and customizable vulnerability scanner",
            command="nuclei"
        )
        self.severity_levels = ["info", "low", "medium", "high", "critical"]
    
    def validate_params(self, **params) -> bool:
        """Validate parameters"""
        if "target" not in params and "targets" not in params:
            raise ValueError("target or targets parameter is required")
        return True
    
    def build_command(self, **params) -> List[str]:
        """Build Nuclei command"""
        cmd = ["nuclei"]
        
        # Target
        if params.get("target"):
            cmd.extend(["-u", params["target"]])
        elif params.get("targets"):
            cmd.extend(["-l", params["targets"]])
        
        # Templates
        if params.get("templates"):
            if isinstance(params["templates"], list):
                for template in params["templates"]:
                    cmd.extend(["-t", template])
            else:
                cmd.extend(["-t", params["templates"]])
        
        # Template tags
        if params.get("tags"):
            cmd.extend(["-tags", ",".join(params["tags"])])
        
        # Severity filter
        if params.get("severity"):
            cmd.extend(["-severity", ",".join(params["severity"])])
        
        # Exclude severities
        if params.get("exclude_severity"):
            cmd.extend(["-exclude-severity", ",".join(params["exclude_severity"])])
        
        # Automatic template selection
        if params.get("automatic_scan", False):
            cmd.append("-as")
        
        # Update templates before scan
        if params.get("update_templates", False):
            cmd.append("-update-templates")
        
        # Concurrency
        threads = params.get("threads", 25)
        cmd.extend(["-c", str(threads)])
        
        # Rate limit (requests per second)
        if params.get("rate_limit"):
            cmd.extend(["-rate-limit", str(params["rate_limit"])])
        
        # Timeout
        timeout = params.get("timeout", 5)
        cmd.extend(["-timeout", str(timeout)])
        
        # Retries
        retries = params.get("retries", 1)
        cmd.extend(["-retries", str(retries)])
        
        # Output
        if params.get("output_file"):
            cmd.extend(["-o", params["output_file"]])
        
        # JSON output
        if params.get("json", False):
            cmd.append("-json")
        
        # Silent mode
        if params.get("silent", True):
            cmd.append("-silent")
        
        # Verbose mode
        if params.get("verbose", False):
            cmd.append("-v")
        
        # Follow redirects
        if params.get("follow_redirects", True):
            cmd.append("-follow-redirects")
        
        # System DNS
        if params.get("system_resolvers", False):
            cmd.append("-system-resolvers")
        
        return cmd
    
    def parse_output(self, output: str, **params) -> Dict:
        """Parse Nuclei output"""
        vulnerabilities = []
        
        if params.get("json", False):
            # Parse JSON output
            for line in output.strip().split("\n"):
                if line:
                    try:
                        vuln = json.loads(line)
                        vulnerabilities.append({
                            "template_id": vuln.get("template-id", ""),
                            "name": vuln.get("info", {}).get("name", ""),
                            "severity": vuln.get("info", {}).get("severity", "unknown"),
                            "host": vuln.get("host", ""),
                            "matched_at": vuln.get("matched-at", ""),
                            "extracted_results": vuln.get("extracted-results", []),
                            "timestamp": vuln.get("timestamp", ""),
                            "curl_command": vuln.get("curl-command", "")
                        })
                    except json.JSONDecodeError:
                        continue
        else:
            # Parse plain text output
            for line in output.strip().split("\n"):
                if line and "[" in line:
                    vulnerabilities.append({
                        "raw_output": line,
                        "severity": "unknown"
                    })
        
        # Count by severity
        severity_counts = {}
        for vuln in vulnerabilities:
            sev = vuln.get("severity", "unknown")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
        
        return {
            "vulnerabilities": vulnerabilities,
            "total_found": len(vulnerabilities),
            "severity_counts": severity_counts,
            "critical": severity_counts.get("critical", 0),
            "high": severity_counts.get("high", 0),
            "medium": severity_counts.get("medium", 0),
            "low": severity_counts.get("low", 0),
            "info": severity_counts.get("info", 0)
        }
    
    def get_educational_content(self) -> Dict[str, str]:
        """Educational content about Nuclei"""
        return {
            "what": """
Nuclei is a fast, template-based vulnerability scanner that uses
YAML-based templates to detect security issues. It has over 1000
community-contributed templates covering various vulnerability types.

Templates are like smart recipes that tell Nuclei:
- What to look for
- How to test it
- How to verify the vulnerability
- What severity to assign
""",
            "when": """
Use Nuclei for:
- Automated vulnerability scanning
- CI/CD security checks
- Bug bounty reconnaissance
- Security audits
- Compliance testing
- After subdomain enumeration
- During active reconnaissance
- For known vulnerability detection
""",
            "how": """
Nuclei scanning workflow:
1. Select target(s)
2. Choose templates (by severity/tags/specific)
3. Configure concurrency and rate limits
4. Run scan
5. Review findings
6. Validate vulnerabilities manually

Templates are organized by:
- CVE (specific vulnerabilities)
- Technologies (WordPress, Jira, etc.)
- Exposure (config files, backups)
- Takeover (subdomain takeover)
- Default credentials
""",
            "why": """
Nuclei is powerful because:
- Template-based = highly accurate
- Community-driven = constantly updated
- Fast = can scan thousands of URLs
- Customizable = write your own templates
- Zero false positives = templates are verified
- Open source = free and transparent
- Well-maintained = active development
""",
            "caution": """
⚠️ Best practices:
- Start with low concurrency on unfamiliar targets
- Use rate limiting to avoid DoS
- Always get authorization before scanning
- Some templates are intrusive (use carefully)
- Update templates regularly (-update-templates)
- Review findings manually (validate)
- Respect target's infrastructure
- Consider using -severity to start with criticals only
"""
        }


# Example usage
if __name__ == "__main__":
    async def test_nuclei():
        tool = NucleiTool()
        
        print("⚡ Testing Nuclei Integration...")
        print(f"Tool: {tool.name}")
        print(f"Category: {tool.category.value}")
        
        # Test parameters
        params = {
            "target": "https://example.com",
            "severity": ["critical", "high"],
            "threads": 50,
            "silent": True,
            "json": False
        }
        
        print(f"\nParameters: {params}")
        
        # Build command
        cmd = tool.build_command(**params)
        print(f"Command: {' '.join(cmd)}")
        
        # Show educational content
        edu = tool.get_educational_content()
        print(f"\n📚 What is Nuclei?")
        print(edu["what"])
        
        print(f"\n⚠️ Important Cautions:")
        print(edu["caution"])
    
    asyncio.run(test_nuclei())
