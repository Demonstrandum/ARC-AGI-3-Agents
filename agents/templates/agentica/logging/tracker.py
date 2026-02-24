"""
Per-agent token usage tracking and reasoning accumulation.

UsageTracker is thread-safe and shared between WsLogger instances
(which write) and the submit_action closure (which drains reasoning).
"""

from __future__ import annotations

import json
import threading
from collections import defaultdict
from dataclasses import dataclass


@dataclass(slots=True)
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    reasoning_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


_IGNORED_CHUNK_TYPES = frozenset({"usage"})

# Leave ~1 KB headroom inside the 16 KB API limit for the JSON envelope.
_MAX_REASONING_BYTES = 15_000


class UsageTracker:
    """
    Accumulates reasoning text and token usage across all agents.

    WsLogger calls append_reasoning / record_usage on every chunk.
    submit_action calls drain_reasoning before each API step.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._reasoning: dict[int, list[str]] = defaultdict(list)
        self._usage: dict[int, TokenUsage] = defaultdict(TokenUsage)

    # -- writing (called from WsLogger.on_chunk) ---------------------------

    def append_reasoning(self, agent_id: int, chunk_type: str | None, text: str) -> None:
        if not text:
            return
        if chunk_type in _IGNORED_CHUNK_TYPES:
            return
        with self._lock:
            self._reasoning[agent_id].append(text)

    def record_usage(self, agent_id: int, content: str) -> None:
        try:
            obj = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            return
        inp = obj.get("input_tokens", 0) or 0
        out = obj.get("output_tokens", 0) or 0
        cached = 0
        reasoning = 0
        if details := obj.get("input_tokens_details"):
            cached = details.get("cached_tokens", 0) or 0
        if details := obj.get("output_tokens_details"):
            reasoning = details.get("reasoning_tokens", 0) or 0
        with self._lock:
            self._usage[agent_id] = TokenUsage(inp, out, cached, reasoning)

    # -- reading (called from submit_action / main) ------------------------

    def drain_reasoning(self) -> dict[str, object] | None:
        """
        Drain ALL accumulated reasoning across every agent and return a dict
        suitable for the API reasoning field, or None if nothing was buffered.
        """
        with self._lock:
            if not self._reasoning:
                return None
            all_buffers = dict(self._reasoning)
            self._reasoning.clear()
        parts: list[str] = []
        for aid in sorted(all_buffers):
            chunks = all_buffers[aid]
            if chunks:
                parts.append(f"[agent {aid}]\n" + "".join(chunks))
        if not parts:
            return None
        text = "\n\n".join(parts)
        encoded = text.encode("utf-8")
        if len(encoded) > _MAX_REASONING_BYTES:
            text = encoded[-_MAX_REASONING_BYTES:].decode("utf-8", errors="ignore")
        return {"text": text}

    def total_usage(self) -> TokenUsage:
        with self._lock:
            return TokenUsage(
                input_tokens=sum(u.input_tokens for u in self._usage.values()),
                output_tokens=sum(u.output_tokens for u in self._usage.values()),
                cached_tokens=sum(u.cached_tokens for u in self._usage.values()),
                reasoning_tokens=sum(u.reasoning_tokens for u in self._usage.values()),
            )

    def per_agent_usage(self) -> dict[int, TokenUsage]:
        with self._lock:
            return {aid: TokenUsage(u.input_tokens, u.output_tokens, u.cached_tokens, u.reasoning_tokens)
                    for aid, u in self._usage.items()}

    def summary(self) -> str:
        per_agent = self.per_agent_usage()
        total = self.total_usage()
        lines = ["Token Usage Summary", "=" * 60]
        if per_agent:
            lines.append(f"{'Agent':>8}  {'Input':>10}  {'Output':>10}  {'Cached':>10}  {'Reasoning':>10}")
            lines.append("-" * 60)
            for aid in sorted(per_agent):
                u = per_agent[aid]
                lines.append(f"{'#' + str(aid):>8}  {u.input_tokens:>10,}  {u.output_tokens:>10,}  {u.cached_tokens:>10,}  {u.reasoning_tokens:>10,}")
            lines.append("-" * 60)
        lines.append(f"{'TOTAL':>8}  {total.input_tokens:>10,}  {total.output_tokens:>10,}  {total.cached_tokens:>10,}  {total.reasoning_tokens:>10,}")
        lines.append(f"\nTotal tokens: {total.total_tokens:,}")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, object]:
        """JSON-serialisable snapshot for file output."""
        per_agent = self.per_agent_usage()
        total = self.total_usage()
        return {
            "total": {
                "input_tokens": total.input_tokens,
                "output_tokens": total.output_tokens,
                "cached_tokens": total.cached_tokens,
                "reasoning_tokens": total.reasoning_tokens,
                "total_tokens": total.total_tokens,
            },
            "per_agent": {
                str(aid): {
                    "input_tokens": u.input_tokens,
                    "output_tokens": u.output_tokens,
                    "cached_tokens": u.cached_tokens,
                    "reasoning_tokens": u.reasoning_tokens,
                    "total_tokens": u.total_tokens,
                }
                for aid, u in sorted(per_agent.items())
            },
        }
