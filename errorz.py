#!/usr/bin/env python3
"""
ERR0RS ULTIMATE - Main CLI Entry Point
Natural language interface with Interactive & YOLO modes

Usage:
    errorz "scan example.com for open ports"
    errorz --mode yolo "check target.com for SQL injection"
    errorz --help
"""

import sys
import asyncio
import argparse
from typing import Optional

# Import our components
try:
    from src.ai.natural_language import NaturalLanguageInterface
    from src.orchestration.execution_modes import ExecutionEngine, ExecutionMode
except ImportError:
    # For development/testing
    import os
    sys.path.insert(0, os.path.dirname(__file__))
    from src.ai.natural_language import NaturalLanguageInterface
    from src.orchestration.execution_modes import ExecutionEngine, ExecutionMode


BANNER = """
   ___ ___  ___  ___  ___  ___     _   _ _   _____ ___ __  __   _ _____ ___ 
  | __| _ \| _ \/ _ \| _ \/ __|   | | | | | |_   _|_ _|  \/  | /_\_   _| __|
  | _||   /|   / (_) |   /\__ \   | |_| | |__ | |  | || |\/| |/ _ \| | | _| 
  |___|_|_\|_|_\\___/|_|_\|___/    \___/|____||_| |___|_|  |_/_/ \_\_| |___|

  🐱 AI-Powered Penetration Testing Framework
  💚 Created by Eros | Built with Claude
  🛡️ Mission: Make the internet safer for everyone

"""


class ERR0RSTerminal:
    """Main ERR0RS ULTIMATE terminal interface"""
    
    def __init__(self):
        self.nli = NaturalLanguageInterface()
        self.engine = ExecutionEngine()
        self.mode = ExecutionMode.INTERACTIVE
        
    def print_banner(self):
        """Print ERR0RS banner"""
        print(BANNER)
    
    async def execute_command(self, command: str, mode: str = "interactive"):
        """Execute a natural language command"""
        
        # Parse command
        print(f"\n🔍 Parsing: '{command}'")
        parsed = self.nli.parse_command(command)
        
        # Show what was understood
        print(f"\n✅ Understood:")
        print(f"   Intent: {parsed.intent.value}")
        print(f"   Target: {parsed.target}")
        print(f"   Tools: {', '.join(parsed.tools) if parsed.tools else 'None'}")
        print(f"   Confidence: {parsed.confidence:.0%}")
        
        # Check confidence
        if parsed.confidence < 0.5:
            print("\n⚠️  Low confidence in parsing. Please be more specific.")
            print("\n💡 Try something like:")
            for suggestion in self.nli._get_suggestions(command):
                print(f"   {suggestion}")
            return
        
        # No tools selected
        if not parsed.tools:
            print("\n⚠️  No tools selected. Try being more specific about what you want to do.")
            return
        
        # Create execution plan
        self.engine.set_mode(ExecutionMode[mode.upper()])
        plan = self.engine.create_plan(
            tools=parsed.tools,
            target=parsed.target or "unknown",
            parameters=parsed.parameters,
            intent=parsed.intent.value
        )
        
        # Execute based on mode
        if mode.lower() == "interactive":
            results = await self.engine.execute_interactive(plan)
        elif mode.lower() == "yolo":
            results = await self.engine.execute_yolo(plan)
        elif mode.lower() == "supervised":
            results = await self.engine.execute_supervised(plan)
        else:
            print(f"❌ Unknown mode: {mode}")
            return
        
        return results
    
    def run_interactive_shell(self):
        """Run interactive REPL shell"""
        self.print_banner()
        print("💬 Interactive Mode - Type your commands in plain English")
        print("💡 Try: 'scan example.com for ports' or 'help' or 'quit'")
        print()
        
        while True:
            try:
                # Get command
                command = input("errorz> ").strip()
                
                if not command:
                    continue
                
                # Handle special commands
                if command.lower() in ['quit', 'exit', 'q']:
                    print("\n👋 Goodbye! Stay ethical!")
                    break
                
                elif command.lower() in ['help', '?']:
                    print(self.nli.get_help())
                    continue
                
                elif command.lower() == 'clear':
                    import os
                    os.system('cls' if os.name == 'nt' else 'clear')
                    self.print_banner()
                    continue
                
                elif command.lower().startswith('mode '):
                    new_mode = command.split()[1].upper()
                    if new_mode in ['INTERACTIVE', 'YOLO', 'SUPERVISED']:
                        self.mode = ExecutionMode[new_mode]
                        print(f"✅ Mode set to: {new_mode}")
                    else:
                        print("❌ Invalid mode. Use: INTERACTIVE, YOLO, or SUPERVISED")
                    continue
                
                # Execute command
                asyncio.run(self.execute_command(command, self.mode.value))
                
            except KeyboardInterrupt:
                print("\n\n⏹️  Interrupted. Type 'quit' to exit.")
            except EOFError:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                import traceback
                traceback.print_exc()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="ERR0RS ULTIMATE - AI-Powered Penetration Testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  errorz "scan example.com for open ports"
  errorz --mode yolo "check target.com for vulnerabilities"
  errorz --interactive
  
Modes:
  interactive - Ask before each step (default, safe)
  yolo - Full automation (fast, use with caution!)
  supervised - Execute then review (balanced)

For more help: errorz help
"""
    )
    
    parser.add_argument(
        'command',
        nargs='*',
        help='Natural language command to execute'
    )
    
    parser.add_argument(
        '--mode', '-m',
        choices=['interactive', 'yolo', 'supervised'],
        default='interactive',
        help='Execution mode (default: interactive)'
    )
    
    parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='Start interactive shell'
    )
    
    parser.add_argument(
        '--version', '-v',
        action='store_true',
        help='Show version information'
    )
    
    args = parser.parse_args()
    
    # Create terminal
    terminal = ERR0RSTerminal()
    
    # Show version
    if args.version:
        terminal.print_banner()
        print("Version: 1.0.0-alpha")
        print("Natural Language Interface: ✅ Active")
        print("Execution Modes: Interactive, YOLO, Supervised")
        return
    
    # Interactive shell
    if args.interactive or not args.command:
        terminal.run_interactive_shell()
        return
    
    # Single command execution
    command = ' '.join(args.command)
    terminal.print_banner()
    asyncio.run(terminal.execute_command(command, args.mode))


if __name__ == "__main__":
    main()
