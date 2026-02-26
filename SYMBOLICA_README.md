# Arcgentica

ARC-AGI-3 agent harness built on the [Agentica](https://github.com/symbolica-ai/agentica-server) SDK. It uses an orchestrator that delegates to specialized subagents -- explorers, theorists, testers, and solvers -- to figure out game mechanics from scratch and solve multi-level puzzles without any game-specific prompting.

See [`agents/templates/agentica/IDEA.md`](agents/templates/agentica/IDEA.md) for design philosophy and [`agents/templates/agentica/README.md`](agents/templates/agentica/README.md) for architecture.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [Git LFS](https://git-lfs.com/) (for pulling recording logs)
- An [ARC-AGI-3 API key](https://three.arcprize.org/)
- An LLM inference provider -- Anthropic API key, OpenRouter, OpenAI, or use the [Agentica platform](https://github.com/symbolica-ai/agentica-server)

## Setup

```bash
# Install Git LFS (if not already installed):
#   macOS: brew install git-lfs
#   Ubuntu: sudo apt install git-lfs
git lfs install

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

**Option B: Self-hosted agentica-server** -- run the server locally and point at your own inference provider.

The server supports multiple providers:

| Provider | `--inference-token` | `--inference-endpoint` |
|---|---|---|
| **Anthropic** | `$ANTHROPIC_API_KEY` | `https://api.anthropic.com/v1/messages` |
| **OpenAI** | `$OPENAI_API_KEY` | `https://api.openai.com/v1/responses` |
| **OpenRouter** | `$OPENROUTER_API_KEY` | `https://openrouter.ai/api/v1/responses` |

In a separate terminal:

```bash
uv run src/application/main.py --disable-otel \
  --inference-token=$ANTHROPIC_API_KEY \
  --inference-endpoint https://api.anthropic.com/v1/messages \
  --sandbox-mode='no_sandbox' \
  --max-concurrent-invocations 200 \
  --port 2345
```

> `--max-concurrent-invocations` caps how many LLM calls the server handles in parallel.
> In practice the arcgentica agent only has a few agents active at once, so a low value
> is fine for a single game. Increase if you want to run parallel agents, swarm runs,
> or multiple games concurrently.

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

## Logs and Replay

See the official ARC-AGI-3 recording logs in `recordings/` and the visualizer replay logs in `visualizer_logs/` (need Git LFS)

- `ls20`:
  - run ID: `ls20-cb3b57cc/09f5aec7-3fcf-41b3-b079-1ed13319b930`
  - scorecard ID: `b8cf9179-4262-462b-8bcc-409204aa205f`
  - as of commit: `8fd5c5e`
- `vc33`:
  - run ID: `vc33-9851e02b/b432e1b7-39c9-498c-a0b2-df6db4b02855`
  - scorecard ID: `87dccf60-b2b8-4a3a-a7e2-44c9e0b9c745`
  - as of commit: `8fd5c5e`
- `ft09`:
  - run ID: `ft09-9ab2447a/142c3c7f-2a22-46b7-a40e-79209935e674`
  - scorecard ID: `e218993-60de-448b-ad98-dafa624d7be8`
  - as of commit: `8fd5c5e`

### Replaying a visualizer log

```bash
# Start the frontend:
cd agents/templates/agentica/logging/frontend/ && python -m http.server &

# Replay a log:
uv run python -m agents.templates.agentica.logging.replay visualizer_logs/ls20-cb3b57cc_20260217_172701.jsonl
```

Then open `http://localhost:8000`. Use `--speed 4` to speed up or `--no-delay` to skip timing.