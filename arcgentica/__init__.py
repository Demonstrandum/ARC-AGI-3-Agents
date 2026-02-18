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
)
from .frame import DiffRegion, Frame
from .game_ref import GAME_REFERENCE, SYSTEM_PROMPT
from .logger import WsLogger
from .server import EventServer

__all__ = [
    "COLOR_LEGEND",
    "COLOR_NAMES",
    "PALETTE",
    "DiffRegion",
    "Frame",
    "GAME_REFERENCE",
    "SYSTEM_PROMPT",
    "AgentCallEnterEvent",
    "AgentCallExitEvent",
    "AgentChunkEvent",
    "AgentSpawnEvent",
    "GameActionEvent",
    "WsLogger",
    "EventServer",
]
