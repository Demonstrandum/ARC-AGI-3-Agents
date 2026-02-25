# Arcgentica

ARC-AGI-3 agent harness built on the [Agentica](https://github.com/symbolica-ai/agentica-server) SDK. It uses an orchestrator that delegates to specialized subagents -- explorers, theorists, testers, and solvers -- to figure out game mechanics from scratch and solve multi-level puzzles without any game-specific prompting.

See [`agents/templates/agentica/IDEA.md`](agents/templates/agentica/IDEA.md) for design philosophy and [`agents/templates/agentica/README.md`](agents/templates/agentica/README.md) for architecture.

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
uv run main.py --agent=arcgentica --game=ft09
uv run main.py --agent=arcgentica --game=ls20
uv run main.py --agent=arcgentica --game=vc33
```

### With the visualizer

The visualizer is a browser-based frontend that streams agent activity, grid states, and action history in real time.

```bash
# Start the frontend (in another terminal):
cd agents/templates/agentica/logging/frontend/
python -m http.server

# Run the agent with VISUALIZE=1:
VISUALIZE=1 uv run main.py --agent=arcgentica --game=vc33
```

Open `http://localhost:8000` in your browser. Drop `VISUALIZE=1` if you don't need the frontend.

See [`agents/templates/agentica/README.md`](agents/templates/agentica/README.md) for architecture and [`agents/templates/agentica/logging/README.md`](agents/templates/agentica/logging/README.md) for logging, replays, and visualizer details.

## Tests

```bash
uv run python -m pytest tests/test_smoke.py -v
```
