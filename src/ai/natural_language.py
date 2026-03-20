#!/usr/bin/env python3
"""
ERR0RS ULTIMATE - Natural Language Interface
Convert plain English commands into security tool executions

Examples:
- "Scan target.com for open ports" -> Nmap scan
- "Check example.com for SQL injection" -> SQLMap
- "Crack this password hash" -> Hashcat
- "Find subdomains of target.com" -> Subfinder + Amass
"""

import re
import logging
import sys
import os
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

# ---------------------------------------------------------------------------
# Path fix – make "from src.core…" work regardless of launch directory
# ---------------------------------------------------------------------------
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.core.tool_executor import ToolExecutor  # noqa: E402

logger = logging.getLogger(__name__)


class IntentType(Enum):
    """Types of user intents"""
    SCAN = "scan"
    EXPLOIT = "exploit"
    ENUMERATE = "enumerate"
    CRACK = "crack"
    ANALYZE = "analyze"
    REPORT = "report"
    MONITOR = "monitor"
    SEARCH = "search"
    HELP = "help"
    UNKNOWN = "unknown"


class ToolCategory(Enum):
    """Tool categories"""
    NETWORK = "network"
    WEB = "web"
    PASSWORD = "password"
    WIRELESS = "wireless"
    OSINT = "osint"
    EXPLOITATION = "exploitation"
    POST_EXPLOITATION = "post_exploitation"


@dataclass
class ParsedIntent:
    """Structured intent from natural language"""
    intent: IntentType
    target: Optional[str]
    tools: List[str]
    parameters: Dict[str, Any]
    confidence: float
    raw_command: str


class NaturalLanguageInterface:
    """
    Converts natural language to tool executions
    
    Features:
    - Intent recognition
    - Target extraction
    - Tool selection
    - Parameter inference
    - Multi-step workflow planning
    """
    
    def __init__(self, llm_router=None):
        self.llm_router = llm_router
        self.intent_patterns  = self._build_intent_patterns()
        self.tool_keywords    = self._build_tool_keywords()
        self.execution_history = []
        self.executor         = ToolExecutor()   # real subprocess runner
        
    def _build_intent_patterns(self) -> Dict[IntentType, List[str]]:
        """Build regex patterns for intent detection"""
        return {
            IntentType.SCAN: [
                r"scan\s+(.+?)\s+for",
                r"check\s+(.+?)\s+for",
                r"find\s+(open\s+)?ports",
                r"discover\s+(services|hosts)",
                r"enumerate\s+(.+)",
                r"probe\s+(.+)",
                r"reconnaissance\s+on\s+(.+)",
                r"recon\s+(.+)",
            ],
            IntentType.EXPLOIT: [
                r"exploit\s+(.+)",
                r"attack\s+(.+)",
                r"pwn\s+(.+)",
                r"compromise\s+(.+)",
                r"gain\s+access\s+to\s+(.+)",
                r"test\s+(.+?)\s+for\s+(sql|xss|rce|lfi|rfi)",
            ],
            IntentType.CRACK: [
                r"crack\s+(this\s+)?(.+?)\s+(hash|password)",
                r"brute\s*force\s+(.+)",
                r"password\s+attack\s+on\s+(.+)",
                r"decrypt\s+(.+)",
            ],
            IntentType.ENUMERATE: [
                r"find\s+(all\s+)?subdomains\s+of\s+(.+)",
                r"enumerate\s+(users|directories|files)",
                r"list\s+(all\s+)?(.+)",
                r"discover\s+(.+)",
            ],
            IntentType.ANALYZE: [
                r"analyze\s+(.+)",
                r"inspect\s+(.+)",
                r"examine\s+(.+)",
                r"investigate\s+(.+)",
                r"review\s+(.+)",
            ],
            IntentType.REPORT: [
                r"generate\s+(a\s+)?report",
                r"create\s+(a\s+)?report",
                r"export\s+findings",
                r"summarize\s+results",
            ],
            IntentType.HELP: [
                r"help",
                r"how\s+to\s+(.+)",
                r"what\s+is\s+(.+)",
                r"explain\s+(.+)",
                r"show\s+me\s+(.+)",
            ]
        }
    
    def _build_tool_keywords(self) -> Dict[str, List[str]]:
        """Map keywords to tools"""
        return {
            "nmap": ["port", "scan", "network", "service", "host", "ip"],
            "sqlmap": ["sql", "injection", "sqli", "database"],
            "nikto": ["web", "server", "vulnerability", "cgi"],
            "gobuster": ["directory", "directories", "files", "bruteforce"],
            "hydra": ["password", "brute", "login", "crack"],
            "hashcat": ["hash", "crack", "md5", "sha", "password"],
            "metasploit": ["exploit", "payload", "shell", "reverse"],
            "burpsuite": ["proxy", "intercept", "request", "response"],
            "subfinder": ["subdomain", "dns", "enumerate"],
            "amass": ["subdomain", "osint", "recon", "intelligence"],
            "nuclei": ["vulnerability", "template", "scan", "detect"],
            "wpscan": ["wordpress", "wp", "cms"],
            "aircrack": ["wifi", "wireless", "wep", "wpa", "handshake"],
            "john": ["hash", "password", "crack", "wordlist"],
            "wireshark": ["packet", "capture", "network", "traffic", "pcap"],
        }

    def parse_command(self, user_input: str) -> ParsedIntent:
        """
        Parse natural language into structured intent
        
        Args:
            user_input: Plain English command
            
        Returns:
            ParsedIntent with tool and parameters
            
        Examples:
            "Scan example.com for open ports"
            -> Intent: SCAN, Tool: nmap, Target: example.com
            
            "Check target.com for SQL injection"
            -> Intent: EXPLOIT, Tool: sqlmap, Target: target.com
        """
        user_input = user_input.lower().strip()
        
        # Step 1: Detect intent
        intent = self._detect_intent(user_input)
        
        # Step 2: Extract target
        target = self._extract_target(user_input)
        
        # Step 3: Select tools
        tools = self._select_tools(user_input, intent)
        
        # Step 4: Extract parameters
        parameters = self._extract_parameters(user_input, intent, tools)
        
        # Step 5: Calculate confidence
        confidence = self._calculate_confidence(intent, target, tools)
        
        return ParsedIntent(
            intent=intent,
            target=target,
            tools=tools,
            parameters=parameters,
            confidence=confidence,
            raw_command=user_input
        )
    
    def _detect_intent(self, text: str) -> IntentType:
        """Detect user intent from text"""
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return intent
        return IntentType.UNKNOWN
    
    def _extract_target(self, text: str) -> Optional[str]:
        """Extract target (domain, IP, hash, etc.)"""
        # Domain pattern
        domain_pattern = r'\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}\b'
        domain_match = re.search(domain_pattern, text)
        if domain_match:
            return domain_match.group(0)
        
        # IP address pattern
        ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
        ip_match = re.search(ip_pattern, text)
        if ip_match:
            return ip_match.group(0)
        
        # Hash pattern (MD5, SHA1, SHA256)
        hash_pattern = r'\b[a-f0-9]{32,64}\b'
        hash_match = re.search(hash_pattern, text)
        if hash_match:
            return hash_match.group(0)
        
        # URL pattern
        url_pattern = r'https?://[^\s]+'
        url_match = re.search(url_pattern, text)
        if url_match:
            return url_match.group(0)
        
        return None
    
    def _select_tools(self, text: str, intent: IntentType) -> List[str]:
        """Select appropriate tools based on keywords and intent"""
        selected_tools = []
        scores = {}
        
        # Score each tool based on keyword matches
        for tool, keywords in self.tool_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in text:
                    score += 1
            if score > 0:
                scores[tool] = score
        
        # Get top tools
        if scores:
            sorted_tools = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            selected_tools = [tool for tool, score in sorted_tools[:3]]
        
        # Default tools by intent if nothing matched
        if not selected_tools:
            default_tools = {
                IntentType.SCAN: ["nmap"],
                IntentType.EXPLOIT: ["metasploit", "sqlmap"],
                IntentType.CRACK: ["hashcat", "john"],
                IntentType.ENUMERATE: ["gobuster", "subfinder"],
            }
            selected_tools = default_tools.get(intent, [])
        
        return selected_tools
    
    def _extract_parameters(
        self, 
        text: str, 
        intent: IntentType, 
        tools: List[str]
    ) -> Dict[str, Any]:
        """Extract parameters for tool execution"""
        params = {}
        
        # Port scanning parameters
        if "all ports" in text or "65535" in text:
            params["ports"] = "1-65535"
        elif "common ports" in text:
            params["ports"] = "top-1000"
        elif re.search(r'port[s]?\s+(\d+)', text):
            port_match = re.search(r'port[s]?\s+(\d+)', text)
            params["ports"] = port_match.group(1)
        
        # Speed/timing parameters
        if "fast" in text or "quick" in text:
            params["timing"] = "4"
        elif "slow" in text or "stealth" in text:
            params["timing"] = "1"
        else:
            params["timing"] = "3"
        
        # Scan types
        if "version" in text or "service" in text:
            params["version_detection"] = True
        if "os" in text or "operating system" in text:
            params["os_detection"] = True
        
        # SQL injection parameters
        if "sqli" in text or "sql injection" in text:
            params["attack_type"] = "sql_injection"
        
        # XSS parameters  
        if "xss" in text or "cross site" in text:
            params["attack_type"] = "xss"
        
        # Wordlist parameters
        if "wordlist" in text:
            wordlist_match = re.search(r'wordlist[:\s]+([^\s]+)', text)
            if wordlist_match:
                params["wordlist"] = wordlist_match.group(1)
        
        # Output format
        if "json" in text:
            params["output_format"] = "json"
        elif "html" in text:
            params["output_format"] = "html"
        elif "pdf" in text:
            params["output_format"] = "pdf"
        else:
            params["output_format"] = "html"
        
        return params
    def _calculate_confidence(
        self,
        intent: IntentType,
        target: Optional[str],
        tools: List[str]
    ) -> float:
        """Calculate confidence score for the parse"""
        confidence = 0.0
        
        # Intent detected
        if intent != IntentType.UNKNOWN:
            confidence += 0.3
        
        # Target found
        if target:
            confidence += 0.3
        
        # Tools selected
        if tools:
            confidence += 0.2 * min(len(tools), 3) / 3
        
        # Cap at 1.0
        return min(confidence, 1.0)
    
    async def execute_command(self, user_input: str, mode: str = "interactive") -> Dict[str, Any]:
        """
        Execute natural language command
        
        Args:
            user_input: Plain English command
            mode: "interactive" (ask before each step) or "yolo" (auto-execute)
            
        Returns:
            Execution results
        """
        # Parse the command
        parsed = self.parse_command(user_input)
        
        logger.info(f"Parsed intent: {parsed.intent}")
        logger.info(f"Target: {parsed.target}")
        logger.info(f"Tools: {parsed.tools}")
        logger.info(f"Confidence: {parsed.confidence:.2%}")
        
        # Low confidence - ask for clarification
        if parsed.confidence < 0.5:
            return {
                "status": "needs_clarification",
                "message": "I'm not sure what you want me to do. Can you be more specific?",
                "suggestions": self._get_suggestions(user_input)
            }
        
        # Interactive mode - confirm before execution
        if mode == "interactive":
            confirmation = {
                "status": "awaiting_confirmation",
                "parsed_intent": {
                    "intent": parsed.intent.value,
                    "target": parsed.target,
                    "tools": parsed.tools,
                    "parameters": parsed.parameters
                },
                "message": f"I'll {parsed.intent.value} {parsed.target} using {', '.join(parsed.tools)}. Proceed?",
                "confidence": parsed.confidence
            }
            return confirmation
        
        # YOLO mode - execute immediately
        elif mode == "yolo":
            results = await self._execute_tools(parsed)
            return results
    
    async def _execute_tools(self, parsed: ParsedIntent) -> Dict[str, Any]:
        """Execute the selected tools"""
        results = {
            "status": "executing",
            "intent": parsed.intent.value,
            "target": parsed.target,
            "tool_results": []
        }
        
        for tool_name in parsed.tools:
            try:
                # Import and execute tool
                tool_result = await self._run_tool(
                    tool_name,
                    parsed.target,
                    parsed.parameters
                )
                results["tool_results"].append(tool_result)
                
            except Exception as e:
                logger.error(f"Tool {tool_name} failed: {e}")
                results["tool_results"].append({
                    "tool": tool_name,
                    "status": "failed",
                    "error": str(e)
                })
        
        results["status"] = "completed"
        return results
    
    async def _run_tool(self, tool_name: str, target: str, params: Dict) -> Dict:
        """Run a specific tool via the real ToolExecutor subprocess engine."""
        tool_result = await self.executor.run(tool_name, target, params)
        return {
            "tool"           : tool_result.tool_name,
            "status"         : tool_result.status.value,
            "target"         : target,
            "params"         : params,
            "findings"       : tool_result.findings,
            "findings_count" : len(tool_result.findings),
            "duration_ms"    : tool_result.duration_ms,
            "stdout"         : tool_result.stdout,
            "stderr"         : tool_result.stderr,
            "error"          : tool_result.error,
        }
    
    def _get_suggestions(self, user_input: str) -> List[str]:
        """Get command suggestions"""
        suggestions = [
            "Try: 'Scan example.com for open ports'",
            "Try: 'Check target.com for SQL injection'",
            "Try: 'Find subdomains of example.com'",
            "Try: 'Crack this MD5 hash: 5d41402abc4b2a76b9719d911017c592'",
            "Try: 'Generate a report of findings'",
        ]
        return suggestions
    
    def get_help(self, topic: Optional[str] = None) -> str:
        """Get help information"""
        if not topic:
            return """
ERR0RS ULTIMATE - Natural Language Interface

You can use plain English to control the framework!

Examples:
  • "Scan example.com for open ports"
  • "Check target.com for SQL injection"
  • "Find subdomains of example.com"
  • "Crack password hash: 5d41402abc4b2a76b9719d911017c592"
  • "Enumerate directories on http://target.com"
  • "Test website.com for XSS vulnerabilities"
  • "Generate HTML report of findings"

Modes:
  • Interactive: Confirms before each action (default)
  • YOLO: Automatic execution (use with caution!)

For specific help: "How to scan for vulnerabilities"
"""
        
        # Topic-specific help
        help_topics = {
            "scan": "To scan: 'Scan [target] for [what]'",
            "sql": "To test SQL: 'Check [target] for SQL injection'",
            "crack": "To crack: 'Crack this [type] hash: [hash]'",
            "subdomain": "To find subdomains: 'Find subdomains of [domain]'",
        }
        
        for key, help_text in help_topics.items():
            if key in topic.lower():
                return help_text
        
        return "Topic not found. Use 'help' for general information."


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    
    # Create NLI instance
    nli = NaturalLanguageInterface()
    
    print("=== ERR0RS ULTIMATE - Natural Language Interface ===\n")
    
    # Test commands
    test_commands = [
        "Scan example.com for open ports",
        "Check target.com for SQL injection",
        "Find subdomains of google.com",
        "Crack this MD5 hash: 5d41402abc4b2a76b9719d911017c592",
        "Test website.com for XSS",
        "Generate HTML report",
    ]
    
    for cmd in test_commands:
        print(f"\n📝 Command: '{cmd}'")
        parsed = nli.parse_command(cmd)
        print(f"   Intent: {parsed.intent.value}")
        print(f"   Target: {parsed.target}")
        print(f"   Tools: {', '.join(parsed.tools)}")
        print(f"   Confidence: {parsed.confidence:.0%}")
        if parsed.parameters:
            print(f"   Parameters: {parsed.parameters}")
    
    print("\n" + "="*60)
    print("✅ Natural Language Interface Ready!")
    print("="*60)
