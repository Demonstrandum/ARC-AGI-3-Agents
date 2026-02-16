# arcgentica

Toolkit package for the ARC-AGI-3 agent: frame helpers, WebSocket visualizer, and session logging.

## Logging & output folders

| Folder | Contents | Purpose |
|---|---|---|
| `visualizer_logs/` | `{game_id}_{timestamp}.jsonl` | Every WebSocket event serialized as one JSON object per line. First line is always the `init` event (palette + game_id). Created automatically when the visualizer is enabled. |
| `actions_log/{game_id}/` | `level_{n}.jsonl` | Lightweight per-action log (action name, count, level, timestamp). Rotates file on level change. Always written, independent of the visualizer. |
| `recordings/` | `{game_id}.agentica.{guid}.recording.jsonl` | Raw engine recording (managed by the base `Agent` class, not this package). |

`visualizer_logs/` is gitignored. The JSONL files are self-contained replays of a full session.

## Architecture (high level)

```
agent (agentica_agent.py)
  |
  |-- EventServer (server.py)     WebSocket server + JSONL file writer
  |     |
  |     |-- index.html            Single-file frontend (arcgentica_frontend/)
  |     |-- replay.py             Replay a saved .jsonl session
  |
  |-- WsLogger (logger.py)        AgentLogger that pushes agent lifecycle events
  |-- Frame (frame.py)            Grid inspection helpers (render, diff, find, ...)
  |-- events.py                   Dataclasses for all event types
  |-- colors.py                   Palette and color name constants
  |-- game_ref.py                 GAME_REFERENCE and SYSTEM_PROMPT strings
```

The agent creates an `EventServer`, which opens a WebSocket and a JSONL log file.
`WsLogger` hooks into the agentica SDK's `AgentLogger` interface and pushes
agent spawn/call/chunk/exit events to the server. Game actions (grid snapshots)
are pushed separately by `submit_action`. The server broadcasts everything to
connected frontends and writes every event to the log file.

## Frontend & replay

The frontend (`arcgentica_frontend/index.html`) is a single self-contained HTML
file — inline CSS and JS, no build step. Open it in a browser while the agent
runs (or during replay). It connects via WebSocket and receives the same event
stream in both cases.

**Live:** the `EventServer` sends an `init` event (palette + game_id) on connect,
replays all buffered events, then streams new ones as they happen.

**Replay:** `python -m arcgentica.replay <logfile.jsonl>` starts an identical
WebSocket server, reads the saved JSONL, waits for a frontend to connect, then
replays events with original timing (adjustable with `--speed` or `--no-delay`).

```
python -m arcgentica.replay visualizer_logs/ls20-cb3b57cc_20260217_164918.jsonl
python -m arcgentica.replay session.jsonl --speed 4
python -m arcgentica.replay session.jsonl --no-delay
```
