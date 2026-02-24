"""
WebSocket event server for the ARC-AGI-3 visualizer.

Runs as an asyncio background task in the same event loop as the agent.
Buffers all events so late-connecting frontends get a full replay, then
streams live events as they arrive.
"""

import asyncio
import json
import logging
import threading
import time
from pathlib import Path
from typing import TextIO

import websockets
import websockets.asyncio.server

from ..colors import PALETTE
from .events import Event, GameActionEvent
from ..scope.frame import Frame

logger = logging.getLogger(__name__)

_FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"

# ANSI formatting helpers
_CYAN = "\033[96m"
_GREEN = "\033[92m"
_YELLOW = "\033[93m"
_BOLD = "\033[1m"
_UNDERLINE = "\033[4m"
_RESET = "\033[0m"
_TAG = f"{_CYAN}[visualizer]{_RESET}"


class EventServer:
    """
    Async WebSocket server that broadcasts visualizer events.
    """

    _host: str
    _port: int
    _game_id: str
    _buffer: list[str]
    _clients: set[websockets.asyncio.server.ServerConnection]
    _server: websockets.asyncio.server.Server | None
    _loop: asyncio.AbstractEventLoop | None
    _lock: threading.Lock
    _log_file: TextIO | None
    _log_path: Path | None

    def __init__(self, game_id: str, host: str = "localhost", port: int = 8765, log_dir: str | Path = "visualizer_logs") -> None:
        self._host = host
        self._port = port
        self._game_id = game_id
        self._buffer = []
        self._clients = set()
        self._server = None
        self._loop = None
        self._lock = threading.Lock()
        self._log_file = None
        self._log_path = None
        self._log_dir = Path(log_dir)

    # -- lifecycle ------------------------------------------------------------

    async def start(self) -> None:
        """
        Start the WebSocket server as a background task.
        """
        self._loop = asyncio.get_running_loop()
        self._log_dir.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        self._log_path = self._log_dir / f"{self._game_id}_{ts}.jsonl"
        self._log_file = open(self._log_path, "w")
        init_line = json.dumps({"type": "init", "game_id": self._game_id, "colors": list(PALETTE)})
        self._log_file.write(init_line + "\n")
        self._log_file.flush()
        print(f"{_TAG} Starting WebSocket server on {self._host}:{self._port} ...")
        print(f"{_TAG} Logging events to {_UNDERLINE}{self._log_path}{_RESET}")
        self._server = await websockets.asyncio.server.serve(
            self._on_connect,
            self._host,
            self._port,
        )
        addr = f"ws://{self._host}:{self._port}"
        frontend_path = _FRONTEND_DIR / "index.html"
        print(f"{_TAG} Server listening on {_BOLD}{addr}{_RESET}")
        print(f"{_TAG} Open frontend: {_UNDERLINE}file://{frontend_path}{_RESET}")
        print(f"{_TAG} Waiting for frontend connection ...")

    async def stop(self) -> None:
        """
        Gracefully shut down the server (requires a running event loop).
        """
        if self._server is not None:
            print(f"{_TAG} Shutting down server ...")
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        self._close_log()

    def _close_log(self) -> None:
        if self._log_file is not None:
            self._log_file.close()
            print(f"{_TAG} Session log saved to {_UNDERLINE}{self._log_path}{_RESET}")
            self._log_file = None
        self._loop = None

    # -- client handling ------------------------------------------------------

    async def _on_connect(
        self,
        ws: websockets.asyncio.server.ServerConnection,
    ) -> None:
        self._clients.add(ws)
        n = len(self._clients)
        print(f"{_GREEN}[visualizer]{_RESET} Frontend connected ({n} client{'s' if n != 1 else ''})")
        # Send init (palette + game_id) so the frontend knows color mappings and session info.
        await ws.send(json.dumps({"type": "init", "game_id": self._game_id, "colors": list(PALETTE)}))
        # Replay the full event buffer.
        with self._lock:
            snapshot = list(self._buffer)
        for msg in snapshot:
            await ws.send(msg)
        # Keep the connection alive until the client disconnects.
        try:
            async for _ in ws:
                pass  # we don't expect inbound messages
        finally:
            self._clients.discard(ws)
            n = len(self._clients)
            print(f"{_YELLOW}[visualizer]{_RESET} Frontend disconnected ({n} client{'s' if n != 1 else ''} remaining)")

    # -- event pushing --------------------------------------------------------

    def push(self, event: Event) -> None:
        """
        Push an event (sync-safe — may be called from any thread).
        """
        msg = event.to_json()
        with self._lock:
            self._buffer.append(msg)
        if self._log_file is not None:
            self._log_file.write(msg + "\n")
        loop = self._loop
        if loop is not None and self._clients:
            loop.call_soon_threadsafe(self._schedule_broadcast, msg)

    def push_game_action(
        self,
        action_name: str,
        frame: Frame,
        action_count: int,
        click_x: int | None = None,
        click_y: int | None = None,
    ) -> None:
        """
        Convenience wrapper to push a GameActionEvent from submit_action.
        """
        self.push(
            GameActionEvent(
                action=action_name,
                count=action_count,
                level=frame.levels_completed,
                win_levels=frame.win_levels,
                state=frame.state.name,
                grid=frame.grid,
                available_actions=frame.available_actions,
                click_x=click_x,
                click_y=click_y,
            )
        )

    # -- internal broadcast ---------------------------------------------------

    def _schedule_broadcast(self, msg: str) -> None:
        asyncio.ensure_future(self._broadcast(msg))

    async def _broadcast(self, msg: str) -> None:
        dead: list[websockets.asyncio.server.ServerConnection] = []
        for ws in list(self._clients):
            try:
                await ws.send(msg)
            except websockets.exceptions.ConnectionClosed:
                dead.append(ws)
        for ws in dead:
            self._clients.discard(ws)
