"""
ERR0RS ULTIMATE - Nmap Integration
Network reconnaissance and port scanning

Nmap is the world's most powerful network scanner
"""

import re
from typing import Dict, List, Any
from src.core.base_tool import BaseTool, ToolCategory


class NmapTool(BaseTool):
    """
    Nmap - Network Mapper
    The king of network reconnaissance
    """
    
    def __init__(self):
        super().__init__(
            tool_name="nmap",
            category=ToolCategory.RECONNAISSANCE,
            description="Network discovery and security auditing",
            requires_root=True,
            timeout=300  # 5 minutes default
        )
    
    def validate_params(self, params: Dict[str, Any]) -> bool:
        """Validate Nmap parameters"""
        # Require target
        if "target" not in params:
            return False
        
        # Validate target format (IP or domain)
        target = params["target"]
        if not target or len(target) < 3:
            return False
        
        return True
    
    def build_command(self, params: Dict[str, Any]) -> str:
        """Build Nmap command"""
        target = params["target"]
        scan_type = params.get("scan_type", "sS")  # SYN scan default
        
        # Base command
        command = f"nmap -{scan_type}"
        
        # Add version detection
        if params.get("version_detection", True):
            command += " -sV"
        
        # Add OS detection
        if params.get("os_detection", False):
            command += " -O"
        
        # Add scripts
        if params.get("default_scripts", True):
            command += " -sC"        
        # Add ports
        ports = params.get("ports", "")
        if ports:
            command += f" -p {ports}"
        
        # Add timing
        timing = params.get("timing", "3")  # Normal speed
        command += f" -T{timing}"
        
        # Output format
        output_file = params.get("output", "nmap_scan")
        command += f" -oA {output_file}"
        
        # Add target
        command += f" {target}"
        
        return command
    
    def parse_output(self, output: str) -> List[Dict[str, Any]]:
        """Parse Nmap output into structured findings"""
        findings = []
        
        # Parse open ports
        port_pattern = r"(\d+)/(\w+)\s+open\s+(\S+)"
        for match in re.finditer(port_pattern, output):
            port, protocol, service = match.groups()
            finding = {
                "type": "open_port",
                "port": int(port),
                "protocol": protocol,
                "service": service,
                "severity": "info"
            }
            findings.append(finding)
        
        # Parse OS detection
        os_pattern = r"OS details: (.+)"
        os_match = re.search(os_pattern, output)
        if os_match:
            findings.append({
                "type": "os_detection",
                "os": os_match.group(1),
                "severity": "info"
            })
        
        # Parse vulnerabilities from scripts
        vuln_pattern = r"VULNERABLE:\s*(.+)"
        for match in re.finditer(vuln_pattern, output):
            findings.append({
                "type": "vulnerability",
                "description": match.group(1).strip(),
                "severity": "medium"
            })
        
        return findings    
    def _get_when_to_use(self) -> str:
        """When to use Nmap"""
        return """
Use Nmap at the beginning of ANY penetration test for:
- Discovering live hosts on a network
- Identifying open ports and services
- Detecting operating systems
- Finding potential vulnerabilities

Nmap is your first step in understanding the attack surface.
"""
    
    def _get_how_to_use(self) -> str:
        """How to use Nmap"""
        return """
Basic Nmap usage:
1. Simple scan: nmap <target>
2. SYN scan (stealth): nmap -sS <target>
3. Service version detection: nmap -sV <target>
4. OS detection: nmap -O <target>
5. All options: nmap -sS -sV -sC -O <target>

Common scan types:
- -sS: SYN scan (stealth, requires root)
- -sT: TCP connect scan (no root needed)
- -sU: UDP scan
- -sV: Version detection
- -O: OS detection
- -sC: Default NSE scripts
- -p-: Scan all 65535 ports
- -T4: Faster timing (0-5 scale)

Advanced techniques:
- Firewall evasion: -f, --mtu, -D
- Script scanning: --script=vuln
- Output formats: -oN, -oX, -oG, -oA
"""
    
    def _get_why_important(self) -> str:
        """Why Nmap is important"""
        return """
Nmap is THE most important tool in penetration testing because:

1. **Discovery**: Find what's actually running
2. **Mapping**: Understand network topology
3. **Fingerprinting**: Identify exact services and versions
4. **Vulnerability Detection**: NSE scripts find known vulns
5. **Attack Surface**: See what attackers see

Without Nmap, you're blind. It's your eyes into the network.
"""
    
    def _get_cautions(self) -> str:
        """Nmap cautions"""
        return """
⚠️ CRITICAL WARNINGS:

1. **Authorization Required**: Never scan networks you don't own
2. **Legal Issues**: Unauthorized scanning is illegal in most countries
3. **Detection**: Scans are VERY noisy and will trigger IDS/IPS
4. **Network Impact**: Aggressive scans can crash systems
5. **Timing**: Slow scans (-T0, -T1) are stealthier but take time

ALWAYS:
- Get written permission before scanning
- Use appropriate timing (-T3 default)
- Start with safe scans before aggressive ones
- Document your authorization
- Respect scope boundaries

Nmap can be detected and logged. Use responsibly!
"""


# Example usage
if __name__ == "__main__":
    nmap = NmapTool()
    
    # Print educational content
    education = nmap.get_educational_content()
    print("=== NMAP EDUCATION ===")
    for key, value in education.items():
        print(f"\n{key.upper()}:")
        print(value)
    
    # Example scan (requires authorization!)
    # params = {
    #     "target": "scanme.nmap.org",
    #     "scan_type": "sS",
    #     "version_detection": True,
    #     "ports": "80,443,22,21",
    #     "timing": "3"
    # }
    # result = nmap.execute(params)
    # print(f"\nStatus: {result.status}")
    # print(f"Findings: {len(result.findings)}")
