#!/usr/bin/env bash
#
# Start the agentica session manager.
#
# Required env vars (set in .env or export before running):
#   INFERENCE_API_KEY   - Anthropic/OpenAI API key
#   INFERENCE_URL       - Inference endpoint (default: https://api.anthropic.com/v1/messages)
#
# Optional env vars:
#   AGENTICA_SERVER_DIR - Path to the agentica-server checkout
#                         (default: ../agentica-server)
#   SM_PORT             - Port to run on (default: 2345)
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Load project .env for API keys
if [[ -f "$PROJECT_DIR/.env" ]]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
fi

SM_DIR="${AGENTICA_SERVER_DIR:-$(dirname "$PROJECT_DIR")/agentica-server}"
SM_PORT="${SM_PORT:-2345}"
INFERENCE_ENDPOINT="${INFERENCE_URL:-https://api.anthropic.com/v1/messages}"

if [[ -z "${INFERENCE_API_KEY:-}" ]]; then
    echo "ERROR: INFERENCE_API_KEY is not set." >&2
    exit 1
fi

if [[ ! -d "$SM_DIR" ]]; then
    echo "ERROR: Session manager directory not found: $SM_DIR" >&2
    echo "Set AGENTICA_SERVER_DIR to the correct path." >&2
    exit 1
fi

echo "Starting session manager on port $SM_PORT ..."
echo "  dir:      $SM_DIR"
echo "  endpoint: $INFERENCE_ENDPOINT"

cd "$SM_DIR"
exec uv run src/application/main.py \
    --disable-otel \
    --inference-token="$INFERENCE_API_KEY" \
    --inference-endpoint "$INFERENCE_ENDPOINT" \
    --sandbox-mode='no_sandbox' \
    --max-concurrent-invocations 1200 \
    --port "$SM_PORT"
