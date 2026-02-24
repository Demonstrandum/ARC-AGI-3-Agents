"""
Model configuration: identifiers, context limits, and inference settings.
"""

from dataclasses import dataclass

from agentica.common import ReasoningEffort


@dataclass(slots=True, frozen=True)
class ModelConfig:
    main_agent_model: str
    subagent_model: str
    max_context: int
    reasoning_effort: ReasoningEffort


# Opus 4.6
OPUS_4_6 = ModelConfig(
    main_agent_model="anthropic/claude-opus-4-6",
    subagent_model="anthropic/claude-opus-4-6",
    max_context=200_000,
    reasoning_effort="high",
)

# GPT 5.2
GPT_5_2 = ModelConfig(
    main_agent_model="openai/gpt-5.2",
    subagent_model="openai/gpt-5.2",
    max_context=400_000,
    reasoning_effort="high",
)
