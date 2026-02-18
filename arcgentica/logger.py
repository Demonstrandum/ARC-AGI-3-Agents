"""
Custom AgentLogger that pushes all events to the EventServer over WebSocket.
"""

from typing import override

from agentica.common import Chunk
from agentica.logging.agent_logger import AgentLogger, DefaultLogId, LogId

from .events import (
    AgentCallEnterEvent,
    AgentCallExitEvent,
    AgentChunkEvent,
    AgentSpawnEvent,
)
from .server import EventServer


def _log_id_int(lid: LogId) -> int:
    """
    Extract the integer id from a LogId, working around the DefaultLogId.lid typo.
    """
    return lid.id  # type: ignore[union-attr]


class WsLogger(AgentLogger):
    """
    AgentLogger that serialises lifecycle and chunk events to an EventServer.
    """

    local_id: LogId | None
    parent_local_id: LogId | None

    def __init__(self, server: EventServer) -> None:
        self.local_id = None
        self.parent_local_id = None
        self._server = server

    @override
    def should_stream(self) -> bool:
        return True

    @override
    def on_spawn(self) -> None:
        if self.local_id is None:
            self.local_id = DefaultLogId()
        self._server.push(
            AgentSpawnEvent(
                agent_id=_log_id_int(self.local_id),
                parent_id=_log_id_int(self.parent_local_id)
                if self.parent_local_id is not None
                else None,
            )
        )

    @override
    def on_call_enter(
        self, user_prompt: str, parent_local_id: LogId | None = None
    ) -> None:
        self.parent_local_id = parent_local_id
        assert self.local_id is not None
        self._server.push(
            AgentCallEnterEvent(
                agent_id=_log_id_int(self.local_id),
                parent_id=_log_id_int(parent_local_id)
                if parent_local_id is not None
                else None,
                prompt=user_prompt,
            )
        )

    @override
    def on_call_exit(self, result: object) -> None:
        assert self.local_id is not None
        self._server.push(
            AgentCallExitEvent(
                agent_id=_log_id_int(self.local_id),
                result=str(result),
            )
        )

    @override
    async def on_chunk(self, chunk: Chunk) -> None:
        assert self.local_id is not None
        self._server.push(
            AgentChunkEvent(
                agent_id=_log_id_int(self.local_id),
                role=chunk.role.role,
                content=chunk.content,
                chunk_type=chunk.type,
            )
        )
