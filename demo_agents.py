#!/usr/bin/env python3
"""
ERR0RS ULTIMATE - AI Agents Demo
Showcase the power of autonomous AI agents

Run this to see all agents in action!
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.ai.agents import (
    AgentOrchestrator,
    CVEIntelligenceAgent,
    BrowserAutomationAgent,
    ExploitGeneratorAgent
)


BANNER = """
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║   ███████╗██████╗ ██████╗  ██████╗ ██████╗ ███████╗             ║
║   ██╔════╝██╔══██╗██╔══██╗██╔═══██╗██╔══██╗██╔════╝             ║
║   █████╗  ██████╔╝██████╔╝██║   ██║██████╔╝███████╗             ║
║   ██╔══╝  ██╔══██╗██╔══██╗██║   ██║██╔══██╗╚════██║             ║
║   ███████╗██║  ██║██║  ██║╚██████╔╝██║  ██║███████║             ║
║   ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝             ║
║                                                                   ║
║              🤖 AI AGENTS DEMONSTRATION 🤖                        ║
║                                                                   ║
║   Powered by Claude - The World's Best AI                        ║
║   Created by Eros with ❤️                                        ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
"""


async def demo_cve_agent():
    """Demo: CVE Intelligence Agent"""
    print("\n" + "="*70)
    print("🔍 DEMO 1: CVE Intelligence Agent")
    print("="*70)
    print("\n📋 Analyzing target for CVE vulnerabilities...")
    
    agent = CVEIntelligenceAgent()
    
    target_info = {
        "software": ["Apache 2.4.49", "OpenSSH 7.6"],
        "os": "Ubuntu 20.04",
        "services": ["MySQL 5.7"]
    }
    
    cves = await agent.analyze_target(target_info)
    
    print(f"\n✅ Analysis complete!")
    print(f"   CVEs found: {len(cves)}")
    
    for cve in cves:
        print(f"\n   📌 {cve.cve_id}")
        print(f"      Severity: {cve.severity.value.upper()}")
        print(f"      CVSS Score: {cve.cvss_score}")
        print(f"      Exploitable: {'YES 🔥' if cve.exploit_available else 'No'}")
        if cve.exploit_sources:
            print(f"      Exploit Sources: {', '.join(cve.exploit_sources)}")
    
    # Generate report
    if cves:
        report = await agent.generate_threat_report(cves, "demo-target.com")
        print("\n" + "="*70)
        print("📝 THREAT INTELLIGENCE REPORT")
        print("="*70)
        print(report)


async def demo_browser_agent():
    """Demo: Browser Automation Agent"""
    print("\n" + "="*70)
    print("🌐 DEMO 2: Browser Automation Agent")
    print("="*70)
    print("\n📋 Crawling and analyzing web application...")
    
    agent = BrowserAutomationAgent()
    
    results = await agent.crawl_and_analyze("https://example.com")
    
    print(f"\n✅ Analysis complete!")
    print(f"   Pages crawled: {results['pages_crawled']}")
    print(f"   Forms discovered: {results['forms_found']}")
    print(f"   Endpoints found: {results['endpoints_discovered']}")
    print(f"   Findings: {len(results['findings'])}")
    
    if results['findings']:
        print(f"\n🔍 Security Findings:")
        for finding in results['findings'][:5]:
            print(f"\n   ⚠️  {finding.finding_type.upper()}")
            print(f"      Severity: {finding.severity}")
            print(f"      URL: {finding.url}")
            print(f"      Remediation: {finding.remediation}")


async def demo_exploit_agent():
    """Demo: Exploit Generator Agent"""
    print("\n" + "="*70)
    print("🔧 DEMO 3: Exploit Generator Agent")
    print("="*70)
    print("\n📋 Generating exploit from CVE data...")
    
    agent = ExploitGeneratorAgent()
    
    cve_details = {
        "cve_id": "CVE-2024-DEMO",
        "description": "Remote code execution vulnerability in web application",
        "affected_product": "Example App 1.0",
        "cvss_score": 9.8
    }
    
    exploit = await agent.generate_from_cve("CVE-2024-DEMO", cve_details)
    
    if exploit:
        print(f"\n✅ Exploit generated successfully!")
        print(f"   Exploit ID: {exploit.exploit_id}")
        print(f"   Type: {exploit.exploit_type.value}")
        print(f"   Target: {exploit.target}")
        print(f"   Reliability: {exploit.reliability.value}")
        print(f"   Success Probability: {exploit.success_probability:.0%}")
        
        print(f"\n📝 Exploitation Steps:")
        for step in exploit.steps:
            print(f"   {step}")
        
        print(f"\n🔐 Payload Preview:")
        print(f"   {exploit.payload}")


async def demo_full_orchestration():
    """Demo: Full Agent Orchestration - AUTONOMOUS PENTEST"""
    print("\n" + "="*70)
    print("🚀 DEMO 4: AUTONOMOUS PENETRATION TEST")
    print("="*70)
    print("\n📋 Running fully autonomous penetration test...")
    print("   This demonstrates ALL agents working together!\n")
    
    orchestrator = AgentOrchestrator()
    
    # Run autonomous pentest
    results = await orchestrator.autonomous_pentest("demo-target.com")
    
    print("\n" + "="*70)
    print("📊 FINAL RESULTS")
    print("="*70)
    
    duration = (results["end_time"] - results["start_time"]).seconds
    
    print(f"\nTarget: {results['target']}")
    print(f"Duration: {duration} seconds")
    
    print(f"\n✅ Intelligence Phase:")
    intel = results["phases"]["intelligence"]
    print(f"   CVEs Found: {len(intel.get('cves', []))}")
    print(f"   Critical: {intel.get('critical_count', 0)}")
    print(f"   Exploitable: {intel.get('exploitable_count', 0)}")
    
    print(f"\n✅ Web Analysis Phase:")
    web = results["phases"]["web_analysis"]
    print(f"   Pages Crawled: {web.get('pages_crawled', 0)}")
    print(f"   Forms Tested: {web.get('forms_tested', 0)}")
    
    print(f"\n✅ Exploit Development Phase:")
    exploit = results["phases"]["exploit_dev"]
    print(f"   Exploits Generated: {len(exploit.get('exploits', []))}")
    
    print(f"\n✅ Validation Phase:")
    validation = results["phases"]["validation"]
    print(f"   Confirmed Vulnerabilities: {validation.get('confirmed', 0)}")
    
    print("\n" + "="*70)
    print("📝 FULL REPORT")
    print("="*70)
    print(results["report"])


async def run_all_demos():
    """Run all agent demos"""
    print(BANNER)
    
    print("\n🎯 Welcome to ERR0RS ULTIMATE AI Agents Demo!")
    print("   This will showcase all autonomous agents in action.\n")
    
    input("Press ENTER to start Demo 1: CVE Intelligence Agent...")
    await demo_cve_agent()
    
    input("\nPress ENTER to start Demo 2: Browser Automation Agent...")
    await demo_browser_agent()
    
    input("\nPress ENTER to start Demo 3: Exploit Generator Agent...")
    await demo_exploit_agent()
    
    input("\nPress ENTER to start Demo 4: FULL AUTONOMOUS PENTEST...")
    await demo_full_orchestration()
    
    print("\n" + "="*70)
    print("🎉 ALL DEMOS COMPLETE!")
    print("="*70)
    print("""
✨ You just witnessed the power of ERR0RS ULTIMATE!

Key Features Demonstrated:
- ✅ CVE Intelligence & Threat Correlation
- ✅ Automated Web Application Testing
- ✅ AI-Powered Exploit Generation
- ✅ Multi-Agent Orchestration
- ✅ Fully Autonomous Penetration Testing

This is just the beginning. ERR0RS ULTIMATE will revolutionize
offensive security through AI automation and intelligence.

Built with ❤️ by Eros & Claude
Making the internet safer, one test at a time.
""")


if __name__ == "__main__":
    try:
        asyncio.run(run_all_demos())
    except KeyboardInterrupt:
        print("\n\n⏹️  Demo interrupted. Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
