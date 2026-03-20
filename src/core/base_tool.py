"""
ERR0RS ULTIMATE - Base Tool Module
Foundation class for all security tool integrations

This provides a unified interface for 120+ security tools
"""

import subprocess
import logging
import time
import json
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ToolCategory(Enum):
    """Tool categories for organization"""
    RECONNAISSANCE = "reconnaissance"
    VULNERABILITY = "vulnerability"
    EXPLOITATION = "exploitation"
    PASSWORD = "password"
    WIRELESS = "wireless"
    WEB = "web"
    SOCIAL = "social"
    POSTEX = "postexploitation"
    FORENSICS = "forensics"
    MOBILE = "mobile"


class ToolStatus(Enum):
    """Execution status"""
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class ToolResult:
    """Standardized tool result"""
    tool_name: str
    status: ToolStatus
    output: str
    errors: str
    execution_time: float
    exit_code: int
    findings: List[Dict[str, Any]]
    metadata: Dict[str, Any]


class BaseTool(ABC):
    """
    Base class for all security tools
    
    Provides:
    - Standardized execution interface
    - Timeout protection
    - Output parsing
    - Error handling
    - Educational content
    - Safety checks
    """
    
    def __init__(
        self,
        tool_name: str,
        category: ToolCategory,
        description: str,
        requires_root: bool = False,
        timeout: int = 60
    ):
        self.tool_name = tool_name
        self.category = category
        self.description = description
        self.requires_root = requires_root
        self.timeout = timeout
        self.status = ToolStatus.READY
        
    @abstractmethod
    def validate_params(self, params: Dict[str, Any]) -> bool:
        """Validate parameters before execution"""
        pass
    
    @abstractmethod
    def build_command(self, params: Dict[str, Any]) -> str:
        """Build the command to execute"""
        pass
    
    @abstractmethod
    def parse_output(self, output: str) -> List[Dict[str, Any]]:
        """Parse tool output into structured findings"""
        pass    
    def execute(self, params: Dict[str, Any]) -> ToolResult:
        """
        Execute the tool with given parameters
        
        Features:
        - Parameter validation
        - Timeout protection
        - Error handling
        - Output parsing
        - Audit logging
        """
        start_time = time.time()
        
        # Validate parameters
        if not self.validate_params(params):
            return ToolResult(
                tool_name=self.tool_name,
                status=ToolStatus.FAILED,
                output="",
                errors="Invalid parameters",
                execution_time=0,
                exit_code=-1,
                findings=[],
                metadata={}
            )
        
        # Build command
        command = self.build_command(params)
        logger.info(f"Executing {self.tool_name}: {command}")
        
        # Execute with timeout protection
        try:
            self.status = ToolStatus.RUNNING
            
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            try:
                stdout, stderr = process.communicate(timeout=self.timeout)
                exit_code = process.returncode
                status = ToolStatus.COMPLETED if exit_code == 0 else ToolStatus.FAILED
                
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                exit_code = -1
                status = ToolStatus.TIMEOUT
                logger.warning(f"{self.tool_name} timed out after {self.timeout}s")
                
        except Exception as e:
            stdout = ""
            stderr = str(e)
            exit_code = -1
            status = ToolStatus.FAILED
            logger.error(f"{self.tool_name} execution failed: {e}")
        
        execution_time = time.time() - start_time
        
        # Parse output into findings
        findings = []
        if stdout and status == ToolStatus.COMPLETED:
            try:
                findings = self.parse_output(stdout)
            except Exception as e:
                logger.error(f"Failed to parse {self.tool_name} output: {e}")
        
        # Create result
        result = ToolResult(
            tool_name=self.tool_name,
            status=status,
            output=stdout,
            errors=stderr,
            execution_time=execution_time,
            exit_code=exit_code,
            findings=findings,
            metadata={
                "category": self.category.value,
                "command": command,
                "params": params
            }
        )
        
        self.status = status
        return result
    
    def get_educational_content(self) -> Dict[str, str]:
        """Get educational information about this tool"""
        return {
            "what": self.description,
            "when": self._get_when_to_use(),
            "how": self._get_how_to_use(),
            "why": self._get_why_important(),
            "caution": self._get_cautions()
        }
    
    @abstractmethod
    def _get_when_to_use(self) -> str:
        """When to use this tool in a pentest"""
        pass
    
    @abstractmethod
    def _get_how_to_use(self) -> str:
        """How to use this tool effectively"""
        pass
    
    @abstractmethod
    def _get_why_important(self) -> str:
        """Why this tool is important"""
        pass
    
    @abstractmethod
    def _get_cautions(self) -> str:
        """Safety and ethical considerations"""
        pass
