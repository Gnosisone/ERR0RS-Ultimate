#!/usr/bin/env python3
"""ERR0RS ULTIMATE — orchestration package"""

# Core orchestrator (may fail if deps missing — handled gracefully)
try:
    from .orchestrator import Orchestrator, ToolResult, AVAILABLE_WORKFLOWS
    _ORCH_OK = True
except Exception:
    _ORCH_OK = False

# Campaign Manager — always available (pure stdlib)
try:
    from .campaign_manager import (
        CampaignManager, Campaign, campaign_mgr, handle_campaign_command,
        CampaignStatus, ObjectiveStatus, Finding, Credential,
    )
    _CAMPAIGN_OK = True
except Exception:
    _CAMPAIGN_OK = False

# Auto Kill Chain
try:
    from .auto_killchain import (
        AutoKillChain, auto_pentest, handle_killchain_command, KILL_CHAIN_PHASES,
    )
    _KILLCHAIN_OK = True
except Exception:
    _KILLCHAIN_OK = False

# Execution modes
try:
    from .execution_modes import ExecutionEngine, ExecutionMode, ExecutionPlan
    _EXEC_OK = True
except Exception:
    _EXEC_OK = False

__all__ = [
    "campaign_mgr", "handle_campaign_command", "CampaignManager",
    "auto_pentest", "handle_killchain_command", "AutoKillChain",
    "ExecutionEngine", "ExecutionMode",
]
