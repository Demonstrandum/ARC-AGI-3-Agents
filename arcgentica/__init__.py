"""
arcgentica — ARC-AGI-3 agent toolkit: frame helpers, colors, WebSocket visualizer.
"""

from .colors import COLOR_LEGEND, COLOR_NAMES, PALETTE
from .events import (
    AgentCallEnterEvent,
    AgentCallExitEvent,
    AgentChunkEvent,
    AgentSpawnEvent,
    GameActionEvent,
    UsageSummaryEvent,
)
from .frame import DiffRegion, Frame
from .game_ref import GAME_REFERENCE, SYSTEM_PROMPT
from .logger import WsLogger
from .models import (
    MAIN_AGENT_MODEL,
    REASONING_EFFORT,
    SUBAGENT_MAX_CONTEXT,
    SUBAGENT_MODEL,
)
from .server import EventServer
from .tracker import TokenUsage, UsageTracker

__all__ = [
    "COLOR_LEGEND",
    "COLOR_NAMES",
    "PALETTE",
    "DiffRegion",
    "Frame",
    "GAME_REFERENCE",
    "MAIN_AGENT_MODEL",
    "REASONING_EFFORT",
    "SUBAGENT_MAX_CONTEXT",
    "SUBAGENT_MODEL",
    "SYSTEM_PROMPT",
    "AgentCallEnterEvent",
    "AgentCallExitEvent",
    "AgentChunkEvent",
    "AgentSpawnEvent",
    "GameActionEvent",
    "UsageSummaryEvent",
    "TokenUsage",
    "UsageTracker",
    "WsLogger",
    "EventServer",
]
