"""
Model configuration: identifiers, context limits, and inference settings.
"""

from agentica.common import ReasoningEffort

# Opus 4.6
if True:
    MAIN_AGENT_MODEL: str = "anthropic/claude-opus-4-6"
    SUBAGENT_MODEL: str = "anthropic/claude-opus-4-6"
    SUBAGENT_MAX_CONTEXT: int = 200_000
    REASONING_EFFORT: ReasoningEffort = "high"


# GPT 5.2
if False:
    MAIN_AGENT_MODEL: str = "openai/gpt-5.2"
    SUBAGENT_MODEL: str = "openai/gpt-5.2"
    SUBAGENT_MAX_CONTEXT: int = 400_000
    REASONING_EFFORT: ReasoningEffort = "high"
