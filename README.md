# ARC-AGI-3-Agents

Fork of the [ARC-AGI-3 agent starter kit](https://github.com/arcprize/ARC-AGI-3-Agents). We added an **Agentica** agent harness (see [`agentica_agent.py`](agents/templates/agentica_agent.py) and [`arcgentica/`](arcgentica/)).

## Agentica

The `agentica` agent lives in [`agents/templates/agentica_agent.py`](agents/templates/agentica_agent.py) with its toolkit in [`arcgentica/`](arcgentica/). It uses an orchestrator that delegates to specialized subagents -- explorers, theorists, testers, and solvers -- to figure out game mechanics from scratch and solve multi-level puzzles without any game-specific prompting.

See [`arcgentica/IDEA.md`](arcgentica/IDEA.md) for the design philosophy and [`arcgentica/README.md`](arcgentica/README.md) for logging, replays, and architecture.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- An [ARC-AGI-3 API key](https://three.arcprize.org/)
- An LLM inference provider -- Anthropic API key, OpenRouter, OpenAI, or use the [Agentica platform](https://github.com/symbolica-ai/agentica-server)

## Setup

```bash
git clone https://github.com/symbolica-ai/ARC-AGI-3-Agents.git
cd ARC-AGI-3-Agents

cp .env.example .env
# Edit .env and set ARC_API_KEY
```

### Inference setup

**Option A: Agentica platform** -- no local server needed. Add to your `.env`:

```
AGENTICA_API_KEY=your_key_here
```

**Option B: Self-hosted agentica-server** -- run the server locally and point at your own inference provider. In a separate terminal:

```bash
uv run src/application/main.py --disable-otel \
  --inference-token=$ANTHROPIC_API_KEY \
  --inference-endpoint https://api.anthropic.com/v1/messages \
  --sandbox-mode='no_sandbox' \
  --max-concurrent-invocations 1200 \
  --port 2345
```

Then add to your `.env` so the agent connects to it:

```
S_M_BASE_URL=http://localhost:2345
```

See [symbolica-ai/agentica-server](https://github.com/symbolica-ai/agentica-server) for details.

## Running the agent

```bash
# Pick a game:
uv run main.py --agent=agentica --game=ft09
uv run main.py --agent=agentica --game=ls20
uv run main.py --agent=agentica --game=vc33
```

### With the visualizer

The visualizer is a browser-based frontend that streams agent activity, grid states, and action history in real time.

```bash
# Start the frontend (in another terminal):
cd arcgentica_frontend/
python -m http.server

# Run the agent with VISUALIZE=1:
VISUALIZE=1 uv run main.py --agent=agentica --game=vc33
```

Open `http://localhost:8000` in your browser. Drop `VISUALIZE=1` if you don't need the frontend.

See [`arcgentica/README.md`](arcgentica/README.md) for details on logging, replays, and architecture.

## Tests

```bash
uv run python -m pytest tests/test_smoke.py -v
```

## License

MIT. See [LICENSE](LICENSE).
