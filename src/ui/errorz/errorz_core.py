#!/usr/bin/env python3
"""
ERR0RZ Assistant - Your uploaded code
AI Hacking Cat with Graffiti Theme
"""

import sys
import os
import json
import subprocess
import time
import pygame
import threading
from pygame.locals import *

try:
    from PyQt5.QtCore import QUrl, Qt, QTimer, QSize, QPoint, QThread, pyqtSignal
    from PyQt5.QtGui import QIcon, QDesktopServices, QMovie, QFontDatabase
    from PyQt5.QtQuick import QQuickView
    from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QWidget, QVBoxLayout
except ImportError:
    print("⚠️ PyQt5 not installed. Run: pip install PyQt5")
    
try:
    from screeninfo import get_monitors
except ImportError:
    print("⚠️ screeninfo not installed. Run: pip install screeninfo")
    
try:
    import psutil
except ImportError:
    print("⚠️ psutil not installed. Run: pip install psutil")

try:
    import pyautogui
except ImportError:
    print("⚠️ pyautogui not installed. Run: pip install pyautogui")


class ERR0RZAssistant(QThread):
    """
    ERR0RZ - The AI Hacking Cat
    Your uploaded graffiti-style animated assistant
    """
    update_signal = pyqtSignal(str, str)
    
    def __init__(self):
        super().__init__()
        self.app = QApplication(sys.argv)
        self.primary_monitor = None
        self.errorz_window = None
        self.animation_state = "booting"
        self.current_tool = None
        self.setup_monitors()
        self.setup_tray_icon()
        self.load_config()
        self.pygame_init()
        
    def pygame_init(self):
        """Initialize PyGame for sprite animation"""
        pygame.init()
        self.screen = pygame.display.set_mode((300, 400), pygame.NOFRAME)
        pygame.display.set_caption("ERR0RZ")
        
        # Load sprites
        self.load_sprites()
        
        # Animation variables
        self.current_frame = 0
        self.animation_speed = 100
        self.last_update = pygame.time.get_ticks()
        
    def load_sprites(self):
        """Load sprite sheets for ERR0RZ"""
        self.sprites = {
            "booting": [pygame.Surface((100, 100)) for _ in range(8)],
            "coding": [pygame.Surface((100, 100)) for _ in range(12)],
            "walking": [pygame.Surface((100, 100)) for _ in range(8)],
            "greeting": [pygame.Surface((100, 100)) for _ in range(10)],
            "typing": [pygame.Surface((100, 100)) for _ in range(6)],
            "idle": [pygame.Surface((100, 100)) for _ in range(15)]
        }
        
        # Placeholder sprites (replace with actual graphics)
        for state, frames in self.sprites.items():
            for i, frame in enumerate(frames):
                frame.fill((30, 30, 30))
                font = pygame.font.Font(None, 36)
                text = font.render(f"ERR0RZ {state[0].upper()}", True, (0, 255, 0))
                frame.blit(text, (10, 10))
                
    def setup_monitors(self):
        """Detect and configure monitors"""
        try:
            monitors = get_monitors()
            self.monitors = monitors
            self.primary_monitor = monitors[0]
            
            self.errorz_position = QPoint(
                int(self.primary_monitor.width * 0.7),
                int(self.primary_monitor.height * 0.7)
            )
        except:
            print("⚠️ Could not detect monitors")
            
    def load_config(self):
        """Load ERR0RZ configuration"""
        config_path = os.path.expanduser("~/.errorz_config.json")
        default_config = {
            "animation_quality": "high",
            "auto_start": True,
            "personality": "hacker",
            "graffiti_style": True,
            "color_scheme": "cyberpunk"
        }
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                self.config = {**default_config, **json.load(f)}
        else:
            self.config = default_config
                
    def setup_tray_icon(self):
        """Create system tray icon"""
        self.tray_icon = QSystemTrayIcon()
        
        # Create tray menu
        tray_menu = QMenu()
        
        show_action = tray_menu.addAction("Show ERR0RZ")
        show_action.triggered.connect(self.show_errorz)
        
        hide_action = tray_menu.addAction("Hide ERR0RZ")
        hide_action.triggered.connect(self.hide_errorz)
        
        tray_menu.addSeparator()
        
        exit_action = tray_menu.addAction("Exit")
        exit_action.triggered.connect(self.clean_exit)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        
    def show_errorz(self):
        """Display the ERR0RZ assistant"""
        self.animation_state = "active"
        self.play_animation("greeting")
        
    def hide_errorz(self):
        """Hide the ERR0RZ assistant"""
        self.animation_state = "hidden"
        
    def play_animation(self, animation_name):
        """Play specific animation sequence"""
        self.animation_state = animation_name
        self.current_frame = 0
        print(f"Playing animation: {animation_name}")
            
    def execute_tool(self, tool_name, arguments=None):
        """Execute a Kali tool with ERR0RZ supervision"""
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
        try:
            if not psutil.pid_exists(pid):
                self.current_tool = None
                self.play_animation("idle")
                return False
            return True
        except:
            return False
        
    def clean_exit(self):
        """Clean shutdown of ERR0RZ"""
        self.tray_icon.hide()
        pygame.quit()
        sys.exit(0)
        
    def run(self):
        """Main execution loop"""
        self.show_errorz()
        self.play_animation("booting")
        self.animation_loop()
        
    def animation_loop(self):
        """Main animation loop using PyGame"""
        running = True
        clock = pygame.time.Clock()
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
            
            # Update animation
            current_time = pygame.time.get_ticks()
            if current_time - self.last_update > self.animation_speed:
                self.current_frame = (self.current_frame + 1) % len(self.sprites.get(self.animation_state, [1]))
                self.last_update = current_time
            
            # Draw current frame
            self.screen.fill((0, 0, 0, 0))
            if self.animation_state != "hidden" and self.animation_state in self.sprites:
                current_sprite = self.sprites[self.animation_state][self.current_frame]
                self.screen.blit(current_sprite, (0, 0))
            
            # Draw tool name if working
            if self.current_tool:
                font = pygame.font.Font(None, 20)
                text = font.render(f"Running: {self.current_tool}", True, (0, 255, 0))
                self.screen.blit(text, (10, 120))
            
            pygame.display.flip()
            clock.tick(30)
        
        pygame.quit()


if __name__ == "__main__":
    print("Starting ERR0RZ - AI Hacking Cat Assistant")
    errorz = ERR0RZAssistant()
    errorz.run()
