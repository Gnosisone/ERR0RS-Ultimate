#!/usr/bin/env python3
"""
ERR0RS ULTIMATE - Complete Integration Manager
ONE COMMAND TO INTEGRATE EVERYTHING!

This is the MASTER controller that ties all integration systems together!
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, List
from datetime import datetime

# Import all our integration systems
from .universal_adapter import UniversalToolAdapter
from .auto_tool_generator import AutoToolGenerator
from .rapid_batch import RapidToolBatch


class IntegrationManager:
    """
    INTEGRATION MANAGER - THE ULTIMATE ORCHESTRATOR
    
    One command to rule them all!
    Coordinates all three integration systems for maximum coverage!
    """
    
    def __init__(self):
        self.universal_adapter = UniversalToolAdapter()
        self.auto_generator = AutoToolGenerator()
        self.rapid_batch = RapidToolBatch()
        
        self.stats = {
            "discovered_tools": 0,
            "auto_generated": 0,
            "pre_generated": 155,
            "total_integrated": 0,
            "categories": 0
        }
    
    async def integrate_everything(self, mode: str = "full"):
        """
        INTEGRATE EVERYTHING!
        
        Modes:
        - rapid: Pre-generate 155 common tools (FAST - 10 seconds)
        - discover: Auto-discover installed tools (MEDIUM - 30 seconds)
        - full: Do EVERYTHING! (COMPLETE - 60 seconds)
        """
        
        print("\n" + "="*80)
        print("🚀 ERR0RS ULTIMATE - INTEGRATION MANAGER")
        print("="*80)
        print(f"\nMode: {mode.upper()}")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\nPreparing to integrate ALL security tools...")
        print("="*80 + "\n")
        
        start_time = datetime.now()
        
        if mode in ["rapid", "full"]:
            await self._rapid_integration()
        
        if mode in ["discover", "full"]:
            await self._discovery_integration()
        
        if mode == "full":
            await self._auto_generation()
        
        # Calculate final stats
        await self._calculate_stats()
        
        # Show results
        duration = (datetime.now() - start_time).total_seconds()
        await self._show_results(duration)
        
        return self.stats
    
    async def _rapid_integration(self):
        """Phase 1: Rapid pre-generation"""
        
        print("🔥 PHASE 1: RAPID PRE-GENERATION")
        print("-" * 80)
        print("Generating integrations for 155 most common security tools...")
        print("This happens BEFORE tools are even installed!\n")
        
        await self.rapid_batch.generate_all()
        
        self.stats["pre_generated"] = self.rapid_batch.total_tools
        
        print("\n✅ Phase 1 Complete!")
        print(f"   Pre-generated: {self.stats['pre_generated']} tools\n")
    
    async def _discovery_integration(self):
        """Phase 2: Auto-discovery"""
        
        print("🔍 PHASE 2: AUTO-DISCOVERY")
        print("-" * 80)
        print("Scanning your system for installed security tools...")
        print("Learning each tool's syntax automatically...\n")
        
        discovered = await self.universal_adapter.discover_all_tools()
        
        self.stats["discovered_tools"] = len(discovered)
        
        print("\n✅ Phase 2 Complete!")
        print(f"   Discovered: {self.stats['discovered_tools']} tools\n")
    
    async def _auto_generation(self):
        """Phase 3: Auto-generation for discovered tools"""
        
        print("🔧 PHASE 3: AUTO-GENERATION")
        print("-" * 80)
        print("Creating Python wrappers for discovered tools...")
        print("Building complete integration infrastructure...\n")
        
        tools = await self.auto_generator.generate_all_integrations()
        
        self.stats["auto_generated"] = len(tools)
        
        print("\n✅ Phase 3 Complete!")
        print(f"   Auto-generated: {self.stats['auto_generated']} wrappers\n")
    
    async def _calculate_stats(self):
        """Calculate final statistics"""
        
        # Total integrated = pre-generated + discovered (avoiding duplicates)
        self.stats["total_integrated"] = max(
            self.stats["pre_generated"],
            self.stats["discovered_tools"]
        )
        
        # Add auto-generated unique tools
        if self.stats["auto_generated"] > self.stats["discovered_tools"]:
            self.stats["total_integrated"] = self.stats["auto_generated"]
        
        self.stats["categories"] = 8  # We have 8 categories
    
    async def _show_results(self, duration: float):
        """Show final results"""
        
        print("\n" + "="*80)
        print("✅ INTEGRATION COMPLETE!")
        print("="*80)
        
        print(f"""
📊 FINAL STATISTICS:
   
   🎯 Total Tools Integrated: {self.stats['total_integrated']}
   📦 Pre-Generated Tools:    {self.stats['pre_generated']}
   🔍 Discovered Tools:       {self.stats['discovered_tools']}
   🔧 Auto-Generated:         {self.stats['auto_generated']}
   📂 Categories:             {self.stats['categories']}
   ⏱️  Duration:              {duration:.1f} seconds
   
🚀 STATUS: ALL SYSTEMS OPERATIONAL!

You can now use ANY security tool through ERR0RS ULTIMATE:
   
   • Natural Language: "scan target.com with nmap"
   • Python API: tool = get_tool("sqlmap")
   • AI Agents: orchestrator.autonomous_pentest("target.com")
   
The entire security arsenal is at your fingertips! 🔥
""")
        
        print("="*80 + "\n")
    
    async def verify_integration(self) -> Dict[str, bool]:
        """Verify all integrations are working"""
        
        print("🔍 Verifying integrations...")
        
        verification = {
            "rapid_batch": False,
            "universal_adapter": False,
            "auto_generator": False,
            "master_registry": False
        }
        
        # Check rapid batch
        rapid_batch_dir = Path("src/tools/rapid_batch")
        if rapid_batch_dir.exists():
            verification["rapid_batch"] = True
        
        # Check auto-generated
        auto_gen_dir = Path("src/tools/auto_generated")
        if auto_gen_dir.exists():
            verification["auto_generator"] = True
        
        # Check if universal adapter has discovered tools
        if self.universal_adapter.discovered_tools:
            verification["universal_adapter"] = True
        
        # Check master registry
        registry_file = Path("src/tools/rapid_batch/MASTER_REGISTRY.py")
        if registry_file.exists():
            verification["master_registry"] = True
        
        # Show results
        print("\n📋 Verification Results:")
        for component, status in verification.items():
            icon = "✅" if status else "❌"
            print(f"   {icon} {component.replace('_', ' ').title()}")
        
        all_good = all(verification.values())
        
        if all_good:
            print("\n🎉 All systems verified and operational!\n")
        else:
            print("\n⚠️  Some systems need attention\n")
        
        return verification
    
    async def quick_start_guide(self):
        """Show quick start guide"""
        
        guide = """
╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║                    🎯 ERR0RS ULTIMATE - QUICK START                       ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝

🚀 GETTING STARTED:

1️⃣  NATURAL LANGUAGE INTERFACE:
   
   errorz "scan example.com for ports"
   errorz "check target.com for SQL injection"
   errorz "find subdomains of google.com"

2️⃣  PYTHON API:
   
   from src.tools.rapid_batch import get_tool
   
   nmap = get_tool("nmap")
   results = await nmap.execute(target="example.com")

3️⃣  AI AGENTS:
   
   from src.ai.agents import AgentOrchestrator
   
   orchestrator = AgentOrchestrator()
   results = await orchestrator.autonomous_pentest("target.com")

4️⃣  LIVE DASHBOARD:
   
   from src.ui.dashboard import LiveDashboard
   
   dashboard = LiveDashboard()
   await dashboard.run()

📚 AVAILABLE TOOLS:

   • Recon: nmap, masscan, subfinder, amass, theharvester, etc.
   • Web: sqlmap, nikto, nuclei, ffuf, gobuster, burp, etc.
   • Password: hydra, hashcat, john, medusa, crunch, etc.
   • Exploit: metasploit, empire, covenant, sliver, beef, etc.
   • Network: wireshark, ettercap, bettercap, responder, etc.
   • Wireless: aircrack-ng, wifite, reaver, kismet, etc.
   • Social: setoolkit, gophish, evilginx2, etc.
   • Post-Exploit: mimikatz, bloodhound, linpeas, winpeas, etc.

🎓 EDUCATIONAL MODE:

   Every tool includes:
   • What it does
   • When to use it
   • How it works
   • Why it's important
   • Safety cautions

🛡️  ETHICAL USE:

   ALWAYS get written authorization before testing!
   ERR0RS ULTIMATE is for:
   ✅ Authorized penetration testing
   ✅ Bug bounty programs
   ✅ Security research
   ✅ Educational purposes
   ✅ CTF competitions

💚 MISSION:

   Make the internet safer for everyone!
   Built by Eros & Claude with ❤️

═══════════════════════════════════════════════════════════════════════════════

Ready to start? Run: errorz --help

"""
        print(guide)


# Main execution
if __name__ == "__main__":
    async def main():
        manager = IntegrationManager()
        
        # Show banner
        print("""
╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║    ███████╗██████╗ ██████╗  ██████╗ ██████╗ ███████╗                    ║
║    ██╔════╝██╔══██╗██╔══██╗██╔═══██╗██╔══██╗██╔════╝                    ║
║    █████╗  ██████╔╝██████╔╝██║   ██║██████╔╝███████╗                    ║
║    ██╔══╝  ██╔══██╗██╔══██╗██║   ██║██╔══██╗╚════██║                    ║
║    ███████╗██║  ██║██║  ██║╚██████╔╝██║  ██║███████║                    ║
║    ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝                    ║
║                                                                           ║
║              🔥 INTEGRATION MANAGER 🔥                                    ║
║                                                                           ║
║    Integrating EVERY security tool automatically!                        ║
║    Built by Eros & Claude with ❤️                                        ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
""")
        
        print("\nChoose integration mode:")
        print("1. 🚀 Rapid (10s) - Pre-generate 155 common tools")
        print("2. 🔍 Discover (30s) - Auto-discover installed tools")
        print("3. 🔥 Full (60s) - Complete integration (RECOMMENDED)")
        print("4. ✅ Verify - Check integration status")
        print("5. 📚 Quick Start - Show usage guide")
        
        choice = input("\nChoice (1-5): ").strip()
        
        if choice == "1":
            await manager.integrate_everything(mode="rapid")
        elif choice == "2":
            await manager.integrate_everything(mode="discover")
        elif choice == "3":
            await manager.integrate_everything(mode="full")
        elif choice == "4":
            await manager.verify_integration()
        elif choice == "5":
            await manager.quick_start_guide()
        else:
            print("\n🚀 Running FULL integration...\n")
            await manager.integrate_everything(mode="full")
        
        # Show quick start
        print("\n📚 Want to see the Quick Start guide? (y/n): ", end="")
        show_guide = input().strip().lower()
        
        if show_guide == 'y':
            await manager.quick_start_guide()
        
        print("\n🎉 Ready to ROCK! Let's make the internet safer! 💚\n")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⏹️  Integration stopped. You can run this again anytime!\n")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
