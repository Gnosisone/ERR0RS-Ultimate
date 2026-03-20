#!/usr/bin/env python3
"""
ERR0RS ULTIMATE - Subfinder Integration
Subdomain enumeration using Subfinder

Subfinder is a subdomain discovery tool that returns valid subdomains
for websites, using passive online sources.

Features:
- Fast subdomain enumeration
- Multiple data sources
- DNS resolution
- Wildcard filtering
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional
from pathlib import Path

from ..core.base_tool import BaseTool, ToolCategory, ToolStatus, ToolResult

logger = logging.getLogger(__name__)


class SubfinderTool(BaseTool):
    """
    Subfinder - Subdomain Discovery Tool
    
    Fast and powerful subdomain enumeration
    """
    
    def __init__(self):
        super().__init__(
            name="Subfinder",
            category=ToolCategory.RECON,
            description="Fast subdomain enumeration using passive sources",
            command="subfinder"
        )
        self.sources = [
            "alienvault", "certspotter", "crtsh", "hackertarget",
            "rapiddns", "shodan", "threatcrowd", "virustotal"
        ]
    
    def validate_params(self, **params) -> bool:
        """Validate parameters"""
        if "domain" not in params:
            raise ValueError("domain parameter is required")
        return True
    
    def build_command(self, **params) -> List[str]:
        """Build Subfinder command"""
        domain = params["domain"]
        
        cmd = ["subfinder", "-d", domain]
        
        # Output options
        if params.get("output_file"):
            cmd.extend(["-o", params["output_file"]])
        
        # JSON output
        if params.get("json", False):
            cmd.append("-json")
        
        # Silent mode (only show subdomains)
        if params.get("silent", True):
            cmd.append("-silent")
        
        # All sources
        if params.get("all_sources", False):
            cmd.append("-all")
        
        # Specific sources
        if params.get("sources"):
            cmd.extend(["-sources", ",".join(params["sources"])])
        
        # Recursive enumeration
        if params.get("recursive", False):
            cmd.append("-recursive")
        
        # Number of threads
        threads = params.get("threads", 10)
        cmd.extend(["-t", str(threads)])
        
        # Timeout
        timeout = params.get("timeout", 30)
        cmd.extend(["-timeout", str(timeout)])
        
        return cmd
    
    def parse_output(self, output: str, **params) -> Dict:
        """Parse Subfinder output"""
        subdomains = []
        
        if params.get("json", False):
            # Parse JSON output
            for line in output.strip().split("\n"):
                if line:
                    try:
                        data = json.loads(line)
                        subdomains.append({
                            "subdomain": data.get("host", ""),
                            "source": data.get("source", "unknown"),
                            "ip": data.get("ip", [])
                        })
                    except json.JSONDecodeError:
                        continue
        else:
            # Parse plain text output
            for line in output.strip().split("\n"):
                if line and not line.startswith("["):
                    subdomains.append({
                        "subdomain": line.strip(),
                        "source": "unknown",
                        "ip": []
                    })
        
        return {
            "subdomains": subdomains,
            "total_found": len(subdomains),
            "unique_count": len(set(s["subdomain"] for s in subdomains))
        }
    
    def get_educational_content(self) -> Dict[str, str]:
        """Educational content about Subfinder"""
        return {
            "what": """
Subfinder is a subdomain discovery tool that uses passive online sources.
It queries multiple databases and services to find subdomains without
actively scanning the target, making it stealthy and fast.
""",
            "when": """
Use Subfinder during the reconnaissance phase:
- At the very beginning of a penetration test
- Before active scanning
- To map out the attack surface
- To find hidden assets and forgotten subdomains
- For bug bounty reconnaissance
""",
            "how": """
Subfinder works by:
1. Querying passive DNS databases
2. Checking certificate transparency logs
3. Searching search engines
4. Using APIs from various sources
5. Aggregating and deduplicating results

It's completely passive - no packets sent to target!
""",
            "why": """
Finding subdomains is crucial because:
- Subdomains often have weaker security
- Development/staging environments may be exposed
- Old/forgotten subdomains may be vulnerable
- Increases attack surface understanding
- Essential for comprehensive testing
""",
            "caution": """
⚠️ Important considerations:
- Results depend on data source freshness
- May miss very new or private subdomains
- Some sources require API keys for full results
- Always verify subdomains actually exist (DNS resolution)
- Respect rate limits of data sources
"""
        }


# Example usage
if __name__ == "__main__":
    async def test_subfinder():
        tool = SubfinderTool()
        
        print("🔍 Testing Subfinder Integration...")
        print(f"Tool: {tool.name}")
        print(f"Category: {tool.category.value}")
        
        # Test parameters
        params = {
            "domain": "example.com",
            "silent": True,
            "threads": 20
        }
        
        print(f"\nParameters: {params}")
        
        # Build command
        cmd = tool.build_command(**params)
        print(f"Command: {' '.join(cmd)}")
        
        # Show educational content
        edu = tool.get_educational_content()
        print(f"\n📚 What is Subfinder?")
        print(edu["what"])
        
        print(f"\n🎯 When to use:")
        print(edu["when"])
    
    asyncio.run(test_subfinder())
