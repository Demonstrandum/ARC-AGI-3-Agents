# arcgentica

ARC-AGI-3 agent harness built on the Agentica SDK. Orchestrator, frame helpers, WebSocket visualizer, and session logging.

## Folder structure

```
agentica/
  agent.py              Main agent (orchestrator + submit_action + bounded budget)
  model.py              ModelConfig dataclass and presets (OPUS_4_6, GPT_5_2)
  prompts.py            GAME_REFERENCE and premise strings
  colors.py             palette and color name constants

  scope/                What the agent sees/uses:
    frame.py            * grid inspection helpers (render, diff, find, change_summary, ...)
    memories.py         * shared memory database for cross-agent knowledge

  logging/              Logging agent actions:
    server.py           * EventServer — WebSocket server + JSONL file writer
    logger.py           * WsLogger — AgentListener that pushes lifecycle events
    tracker.py          * UsageTracker — reasoning accumulation + token accounting
    events.py           * structures for event types
    replay.py           * replay a saved .jsonl session
    frontend/           * single-file browser UI (index.html)
```

See `logging/README.md` for visualizer setup, output folders, and replay instructions.
