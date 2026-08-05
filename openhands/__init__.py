"""OpenHands Cloud Integration for Self-Healing Agent.

This module provides integration with OpenHands Cloud API to:
- Start new conversations for self-healing tasks
- Monitor conversation status
- Generate task descriptions for agents
"""

from .client import OpenHandsClient, OpenHandsConfig
from .agent import TaskGenerator, SelfHealingTask

__all__ = [
    "OpenHandsClient",
    "OpenHandsConfig",
    "TaskGenerator",
    "SelfHealingTask",
]
