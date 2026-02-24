"""
Event dataclasses for the WebSocket visualizer protocol.

Every event serialises to a JSON dict with at least ``type`` and ``ts`` fields.
The ``to_json`` method returns the serialised bytes ready for WebSocket transmission.
"""

import json
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import IntEnum


class EventType(IntEnum):
    AGENT_SPAWN = 0
    AGENT_CALL_ENTER = 1
    AGENT_CHUNK = 2
    AGENT_CALL_EXIT = 3
    GAME_ACTION = 4
    USAGE_SUMMARY = 5


_EVENT_TYPE_NAMES: tuple[str, ...] = (
    "agent_spawn",
    "agent_call_enter",
    "agent_chunk",
    "agent_call_exit",
    "game_action",
    "usage_summary",
)


def _now() -> float:
    return time.time()


@dataclass(slots=True)
class AgentSpawnEvent:
    agent_id: int
    parent_id: int | None
    ts: float = field(default_factory=_now)

    def to_dict(self) -> dict[str, object]:
        return {
            "type": _EVENT_TYPE_NAMES[EventType.AGENT_SPAWN],
            "agent_id": self.agent_id,
            "parent_id": self.parent_id,
            "ts": self.ts,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


@dataclass(slots=True)
class AgentCallEnterEvent:
    agent_id: int
    parent_id: int | None
    prompt: str
    ts: float = field(default_factory=_now)

    def to_dict(self) -> dict[str, object]:
        return {
            "type": _EVENT_TYPE_NAMES[EventType.AGENT_CALL_ENTER],
            "agent_id": self.agent_id,
            "parent_id": self.parent_id,
            "prompt": self.prompt,
            "ts": self.ts,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


@dataclass(slots=True)
class AgentChunkEvent:
    agent_id: int
    role: str
    content: str
    chunk_type: str | None
    ts: float = field(default_factory=_now)

    def to_dict(self) -> dict[str, object]:
        return {
            "type": _EVENT_TYPE_NAMES[EventType.AGENT_CHUNK],
            "agent_id": self.agent_id,
            "role": self.role,
            "content": self.content,
            "chunk_type": self.chunk_type,
            "ts": self.ts,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


@dataclass(slots=True)
class AgentCallExitEvent:
    agent_id: int
    result: str
    ts: float = field(default_factory=_now)

    def to_dict(self) -> dict[str, object]:
        return {
            "type": _EVENT_TYPE_NAMES[EventType.AGENT_CALL_EXIT],
            "agent_id": self.agent_id,
            "result": self.result,
            "ts": self.ts,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


@dataclass(slots=True)
class GameActionEvent:
    action: str
    count: int
    level: int
    win_levels: int
    state: str
    grid: Sequence[Sequence[int]]
    available_actions: list[str]
    click_x: int | None = None
    click_y: int | None = None
    ts: float = field(default_factory=_now)

    def to_dict(self) -> dict[str, object]:
        d: dict[str, object] = {
            "type": _EVENT_TYPE_NAMES[EventType.GAME_ACTION],
            "action": self.action,
            "count": self.count,
            "level": self.level,
            "win_levels": self.win_levels,
            "state": self.state,
            "grid": self.grid,
            "available_actions": self.available_actions,
            "ts": self.ts,
        }
        if self.click_x is not None:
            d["click_x"] = self.click_x
            d["click_y"] = self.click_y
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


@dataclass(slots=True)
class UsageSummaryEvent:
    input_tokens: int
    output_tokens: int
    cached_tokens: int
    reasoning_tokens: int
    total_tokens: int
    ts: float = field(default_factory=_now)

    def to_dict(self) -> dict[str, object]:
        return {
            "type": _EVENT_TYPE_NAMES[EventType.USAGE_SUMMARY],
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cached_tokens": self.cached_tokens,
            "reasoning_tokens": self.reasoning_tokens,
            "total_tokens": self.total_tokens,
            "ts": self.ts,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


type Event = (
    AgentSpawnEvent
    | AgentCallEnterEvent
    | AgentChunkEvent
    | AgentCallExitEvent
    | GameActionEvent
    | UsageSummaryEvent
)
