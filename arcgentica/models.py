"""
Model configuration: identifiers, context limits, and inference settings.
"""

from agentica.common import ReasoningEffort

MAIN_AGENT_MODEL: str = "anthropic/claude-opus-4-6"
SUBAGENT_MODEL: str = "anthropic/claude-opus-4-6"
SUBAGENT_MAX_CONTEXT: int = 200_000
REASONING_EFFORT: ReasoningEffort = "high"
