#!/usr/bin/env python3
"""
K.A.T. (Kali AI Technician) - Your uploaded code
Professional penetration testing assistant
"""

import sys
import os
import json
import subprocess
import time
from PyQt5.QtCore import QUrl, Qt, QTimer, QSize, QPoint
from PyQt5.QtGui import QIcon, QDesktopServices, QMovie
from PyQt5.QtQuick import QQuickView
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QWidget, QVBoxLayout
from screeninfo import get_monitors
import psutil
import pyautogui

class KATAssistant:
    """K.A.T. - Professional AI-powered pentesting assistant"""
    
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.primary_monitor = None
        self.kat_window = None
        self.animation_state = "booting"
        self.current_tool = None
        self.setup_monitors()
        self.setup_tray_icon()
        self.load_config()
        
    def setup_monitors(self):
        """Detect and configure monitors"""
        monitors = get_monitors()
        self.monitors = monitors
        self.primary_monitor = monitors[0]
        
        self.kat_position = QPoint(
            int(self.primary_monitor.width * 0.7),
            int(self.primary_monitor.height * 0.7)
        )
        
    def load_config(self):
        """Load K.A.T. configuration"""
        config_path = os.path.expanduser("~/.kat_config.json")
        default_config = {
            "animation_quality": "high",
            "auto_start": True,
            "preferred_monitor": "primary",
            "personality": "professional",
            "tooltips_enabled": True,
            "voice_feedback": False
        }
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                self.config = {**default_config, **json.load(f)}
        else:
            self.config = default_config
            with open(config_path, 'w') as f:
                json.dump(default_config, f, indent=4)
                
    def setup_tray_icon(self):
        """Create system tray icon"""
        self.tray_icon = QSystemTrayIcon()
        
        tray_menu = QMenu()
        
        show_action = tray_menu.addAction("Show K.A.T.")
        show_action.triggered.connect(self.show_kat)
        
        hide_action = tray_menu.addAction("Hide K.A.T.")
        hide_action.triggered.connect(self.hide_kat)
        
        tray_menu.addSeparator()
        
        exit_action = tray_menu.addAction("Exit")
        exit_action.triggered.connect(self.clean_exit)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        
    def show_kat(self):
        """Display the K.A.T. assistant"""
        if not self.kat_window:
            self.create_kat_window()
        self.kat_window.show()
        self.animation_state = "active"
        self.play_animation("greeting")
        
    def hide_kat(self):
        """Hide the K.A.T. assistant"""
        if self.kat_window:
            self.kat_window.hide()
            self.animation_state = "hidden"
            
    def create_kat_window(self):
        """Create the main K.A.T. window"""
        self.kat_window = QQuickView()
        self.kat_window.setFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.kat_window.setColor(Qt.transparent)
        self.kat_window.setResizeMode(QQuickView.SizeRootObjectToView)
        
        width = int(self.primary_monitor.width * 0.2)
        height = int(width * 1.2)
        self.kat_window.setGeometry(self.kat_position.x(), self.kat_position.y(), width, height)
        
    def play_animation(self, animation_name):
        """Play specific animation sequence"""
        animations = {
            "booting": "coding_animation",
            "greeting": "walk_toward_greet",
            "working": "typing_fast",
            "idle": "sitting_code_glance",
            "alert": "alert_look_around"
        }
        
        if animation_name in animations:
            print(f"Playing animation: {animations[animation_name]}")
            
    def execute_tool(self, tool_name, arguments=None):
        """Execute a Kali tool with K.A.T. supervision"""
        self.current_tool = tool_name
        self.play_animation("working")
        
        tool_commands = {
            "nmap": "nmap",
            "metasploit": "msfconsole",
            "burpsuite": "burpsuite",
            "wireshark": "wireshark",
            "sqlmap": "sqlmap",
            "john": "john",
            "hashcat": "hashcat",
            "aircrack": "aircrack-ng"
        }
        
        if tool_name in tool_commands:
            command = tool_commands[tool_name]
            if arguments:
                command += " " + " ".join(arguments)
                
            process = subprocess.Popen(command, shell=True)
            self.monitor_tool(process.pid, tool_name)
            
    def monitor_tool(self, pid, tool_name):
        """Monitor running tool and provide feedback"""
        timer = QTimer()
        timer.timeout.connect(lambda: self.check_tool_status(pid, tool_name))
        timer.start(1000)
        
    def check_tool_status(self, pid, tool_name):
        """Check if tool is still running"""
        if not psutil.pid_exists(pid):
            self.current_tool = None
            self.play_animation("idle")
            return False
        return True
        
    def clean_exit(self):
        """Clean shutdown of K.A.T."""
        if self.kat_window:
            self.kat_window.close()
        self.tray_icon.hide()
        sys.exit(0)
        
    def run(self):
        """Main execution loop"""
        self.show_kat()
        self.play_animation("booting")
        
        QTimer.singleShot(5000, lambda: self.play_animation("greeting"))
        
        sys.exit(self.app.exec_())

if __name__ == "__main__":
    print("Starting K.A.T. - Kali AI Technician")
    kat = KATAssistant()
    kat.run()
