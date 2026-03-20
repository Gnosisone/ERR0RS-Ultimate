#!/usr/bin/env python3
"""
Tool Integration System - From your uploads
Integrates security tools with AI supervision
"""

import subprocess
import threading
import time
import json
import os

class ToolIntegration:
    """Tool integration for both ERR0RZ and K.A.T."""
    
    def __init__(self, assistant_instance):
        self.assistant = assistant_instance
        self.active_tools = {}
        self.tool_configs = self.load_tool_configs()
        
    def load_tool_configs(self):
        """Load configuration for all Kali tools"""
        configs = {
            "nmap": {
                "command": "nmap",
                "monitor_output": True,
                "patterns": {
                    "open": "Found open port",
                    "vulnerable": "Potential vulnerability detected",
                    "os detected": "Operating system identified"
                },
                "default_args": ["-sS", "-sV", "-O"]
            },
            "metasploit": {
                "command": "msfconsole",
                "monitor_output": False,
                "patterns": {},
                "default_args": ["-q"]
            },
            "sqlmap": {
                "command": "sqlmap",
                "monitor_output": True,
                "patterns": {
                    "injectable": "Parameter is injectable",
                    "database": "Database detected",
                    "dumped": "Data dumped successfully"
                },
                "default_args": ["--batch", "--level=1", "--risk=1"]
            },
            "hydra": {
                "command": "hydra",
                "monitor_output": True,
                "patterns": {
                    "valid": "Valid password found",
                    "attempting": "Attempting login"
                },
                "default_args": ["-V"]
            },
            "hashcat": {
                "command": "hashcat",
                "monitor_output": True,
                "patterns": {
                    "cracked": "Password successfully cracked",
                    "exhausted": "All hashes exhausted"
                },
                "default_args": ["-m", "0", "-a", "0"]
            },
            "burpsuite": {
                "command": "burpsuite",
                "monitor_output": False,
                "patterns": {},
                "default_args": []
            },
            "nikto": {
                "command": "nikto",
                "monitor_output": True,
                "patterns": {
                    "vulnerability": "Vulnerability found",
                    "interesting": "Interesting finding"
                },
                "default_args": ["-Display", "V"]
            },
            "gobuster": {
                "command": "gobuster",
                "monitor_output": True,
                "patterns": {
                    "found": "Found directory",
                    "status": "Status"
                },
                "default_args": ["dir", "-t", "50"]
            }
        }
        
        return configs
    
    def execute_with_assistant(self, tool_name, args=None, assistant_feedback=True):
        """Execute a tool with assistant supervision"""
        if tool_name not in self.tool_configs:
            return {"success": False, "error": f"Tool {tool_name} not configured"}
            
        config = self.tool_configs[tool_name]
        command = config.get('command', tool_name)
        
        if args:
            if isinstance(args, str):
                command += " " + args
            elif isinstance(args, list):
                command += " " + " ".join(args)
        elif config.get('default_args'):
            command += " " + " ".join(config.get('default_args'))
                
        # Start assistant working animation if requested
        if assistant_feedback and hasattr(self.assistant, 'play_animation'):
            self.assistant.play_animation("working")
            self.assistant.current_tool = tool_name
            
        # Execute the command
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Store process reference
        self.active_tools[process.pid] = {
            "name": tool_name,
            "process": process,
            "start_time": time.time()
        }
        
        # Monitor output in separate thread
        if config.get('monitor_output', False):
            thread = threading.Thread(
                target=self.monitor_tool_output,
                args=(process, tool_name)
            )
            thread.daemon = True
            thread.start()
            
        return {"success": True, "pid": process.pid}
    
    def monitor_tool_output(self, process, tool_name):
        """Monitor tool output for important information"""
        for line in iter(process.stdout.readline, ''):
            if line:
                self.analyze_output(line.strip(), tool_name)
                
    def analyze_output(self, output, tool_name):
        """Analyze tool output for significant events"""
        significant_patterns = self.tool_configs[tool_name].get('patterns', {})
        
        for pattern, message in significant_patterns.items():
            if pattern in output.lower():
                print(f"[{tool_name}] {message}")
                if hasattr(self.assistant, 'update_signal'):
                    self.assistant.update_signal.emit("alert", f"{tool_name}: {message}")
                
    def get_tool_suggestions(self, target, phase=None):
        """Get AI-powered tool suggestions based on target and phase"""
        phases = {
            "recon": ["nmap", "subfinder", "theharvester", "amass"],
            "vulnerability": ["nikto", "nuclei", "skipfish", "wpscan"],
            "exploitation": ["metasploit", "sqlmap", "burpsuite", "john"],
            "post_exploitation": ["metasploit", "mimikatz", "bloodhound", "powersploit"]
        }
        
        if phase and phase in phases:
            return phases[phase]
        else:
            return list(self.tool_configs.keys())
    
    def stop_tool(self, pid):
        """Stop a running tool"""
        if pid in self.active_tools:
            process = self.active_tools[pid]['process']
            process.terminate()
            
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                
            del self.active_tools[pid]
            
            if hasattr(self.assistant, 'play_animation'):
                self.assistant.play_animation("idle")
                self.assistant.current_tool = None
                
            return True
        return False

# Example usage
if __name__ == "__main__":
    print("Tool Integration System")
    print("Supports:", ["nmap", "metasploit", "sqlmap", "hydra", "hashcat", "burpsuite", "nikto", "gobuster"])
