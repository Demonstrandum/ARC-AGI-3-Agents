"""
Replay a saved visualizer session over WebSocket.

Usage:
    python -m arcgentica.replay <logfile.jsonl> [--speed 1.0] [--port 8765]
    uv run python arcgentica/replay.py <logfile.jsonl> [--speed 2.0] [--no-delay]
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

import websockets
import websockets.asyncio.server

_FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"

# ANSI formatting helpers
_CYAN = "\033[96m"
_GREEN = "\033[92m"
_YELLOW = "\033[93m"
_BOLD = "\033[1m"
_UNDERLINE = "\033[4m"
_RESET = "\033[0m"
_TAG = f"{_CYAN}[replay]{_RESET}"


async def _replay(
    log_path: Path,
    host: str,
    port: int,
    speed: float,
    no_delay: bool,
) -> None:
    lines = log_path.read_text().splitlines()
    if not lines:
        print("[replay] Log file is empty, nothing to replay.")
        return

    game_id: str | None = None
    events: list[tuple[float | None, str]] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        parsed = json.loads(line)
        ts = parsed.get("ts")
        if parsed.get("type") in ("init", "palette") and "game_id" in parsed:
            game_id = parsed["game_id"]
        events.append((ts, line))

    label = f"{game_id} — " if game_id else ""
    print(f"[replay] Loaded {len(events)} events from {log_path} ({label}{len(events)} events)")

    connected: asyncio.Event = asyncio.Event()
    clients: set[websockets.asyncio.server.ServerConnection] = set()

    async def on_connect(ws: websockets.asyncio.server.ServerConnection) -> None:
        clients.add(ws)
        n = len(clients)
        print(f"{_GREEN}[replay]{_RESET} Frontend connected ({n} client{'s' if n != 1 else ''})")
        connected.set()
        try:
            async for _ in ws:
                pass
        finally:
            clients.discard(ws)
            n = len(clients)
            print(f"{_YELLOW}[replay]{_RESET} Frontend disconnected ({n} client{'s' if n != 1 else ''} remaining)")

    server = await websockets.asyncio.server.serve(on_connect, host, port)
    addr = f"ws://{host}:{port}"
    frontend_path = _FRONTEND_DIR / "index.html"
    print(f"{_TAG} Server listening on {_BOLD}{addr}{_RESET}")
    print(f"{_TAG} Open frontend: {_UNDERLINE}file://{frontend_path}{_RESET}")
    print(f"{_TAG} Waiting for frontend connection ...")

    await connected.wait()
    await asyncio.sleep(0.1)

    prev_ts: float | None = None
    sent = 0
    for ts, raw in events:
        if not no_delay and ts is not None and prev_ts is not None:
            delta = (ts - prev_ts) / speed
            if delta > 0:
                await asyncio.sleep(delta)
        prev_ts = ts

        dead: list[websockets.asyncio.server.ServerConnection] = []
        for ws in list(clients):
            try:
                await ws.send(raw)
            except websockets.exceptions.ConnectionClosed:
                dead.append(ws)
        for ws in dead:
            clients.discard(ws)

        sent += 1

    speed_str = "instant" if no_delay else f"{speed}x"
    print(f"{_GREEN}[replay]{_RESET} Done — sent {sent} events ({speed_str})")
    print(f"{_TAG} Keeping server alive for inspection. Ctrl+C to quit.")

    try:
        await asyncio.Future()
    except asyncio.CancelledError:
        pass
    finally:
        server.close()
        await server.wait_closed()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Replay a saved ARC-AGI-3 visualizer session",
    )
    parser.add_argument("logfile", type=Path, help="Path to the .jsonl session log")
    parser.add_argument("--speed", type=float, default=1.0, help="Playback speed multiplier (default: 1.0)")
    parser.add_argument("--no-delay", action="store_true", help="Send all events instantly (ignores --speed)")
    parser.add_argument("--host", default="localhost", help="WebSocket host (default: localhost)")
    parser.add_argument("--port", type=int, default=8765, help="WebSocket port (default: 8765)")
    args = parser.parse_args()

    if not args.logfile.exists():
        print(f"[replay] File not found: {args.logfile}", file=sys.stderr)
        sys.exit(1)

    try:
        asyncio.run(_replay(args.logfile, args.host, args.port, args.speed, args.no_delay))
    except KeyboardInterrupt:
        print(f"\n{_TAG} Stopped.")


if __name__ == "__main__":
    main()
