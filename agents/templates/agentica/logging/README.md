# logging

## Output folders

| Folder | Contents | Purpose |
|---|---|---|
| `visualizer_logs/` | `{game_id}_{timestamp}.jsonl` | Every WebSocket event serialized as one JSON object per line. First line is always the `init` event (palette + game_id). Created automatically when the visualizer is enabled. |
| `actions_log/{game_id}/` | `level_{n}.jsonl` | Lightweight per-action log (action name, count, level, timestamp). Rotates file on level change. Always written, independent of the visualizer. |
| `recordings/` | `{game_id}.agentica.{guid}.recording.jsonl` | Raw engine recording (managed by the base `Agent` class, not this package). |

`visualizer_logs/` and `actions_log/` are gitignored. The JSONL files are self-contained replays of a full session.

## Enabling the visualizer

Set the `VISUALIZE` environment variable before running the agent:

```
VISUALIZE=1 uv run main.py --agent=agentica --game=ls20
```

Or pass `visualize=True` when constructing the `Agentica` agent in code.

## Frontend & replay

The frontend (`logging/frontend/index.html`) is a single self-contained HTML
file — inline CSS and JS, no build step. Open it in a browser while the agent
runs (or during replay). It connects via WebSocket and receives the same event
stream in both cases.

**Live:** the `EventServer` sends an `init` event (palette + game_id) on connect,
replays all buffered events, then streams new ones as they happen.

**Replay:** `python -m agentica.logging.replay <logfile.jsonl>` starts an identical
WebSocket server, reads the saved JSONL, waits for a frontend to connect, then
replays events with original timing (adjustable with `--speed` or `--no-delay`).

```
uv run python -m agents.templates.agentica.logging.replay visualizer_logs/session.jsonl
uv run python -m agents.templates.agentica.logging.replay session.jsonl --speed 4
uv run python -m agents.templates.agentica.logging.replay session.jsonl --no-delay
```
