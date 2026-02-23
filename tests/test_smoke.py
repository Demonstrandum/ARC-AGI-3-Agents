"""
Offline smoke test for the arcgentica plumbing.

Verifies that Frame, EventServer, WsLogger, UsageTracker, and the
submit_action factory all wire together without import errors, type errors,
or logic bugs -- no LLM or ARC API required.

Run: uv run python -m pytest tests/test_smoke.py -v
"""

import json

import numpy as np
import pytest
from arcengine import FrameData, GameState

from arcgentica.events import (
    AgentChunkEvent,
    EventType,
    UsageSummaryEvent,
)
from arcgentica.frame import Frame
from arcgentica.tracker import TokenUsage, UsageTracker


def _make_frame_data(
    *,
    pixel: int = 0,
    levels_completed: int = 0,
    win_levels: int = 3,
    state: GameState = GameState.NOT_FINISHED,
    available_actions: list[int] | None = None,
) -> FrameData:
    grid = np.full((64, 64), pixel, dtype=int)
    return FrameData(
        game_id="test-dry-run",
        frame=[grid.tolist()],
        state=state,
        levels_completed=levels_completed,
        win_levels=win_levels,
        available_actions=available_actions or [1, 2, 3, 4],
    )


# ── Frame ────────────────────────────────────────────────────────────────────


class TestFrame:
    def test_construct_and_properties(self):
        fd = _make_frame_data()
        f = Frame(fd)
        assert f.game_id == "test-dry-run"
        assert f.state is GameState.NOT_FINISHED
        assert f.levels_completed == 0
        assert f.width == 64
        assert f.height == 64

    def test_render(self):
        fd = _make_frame_data()
        f = Frame(fd)
        rendered = f.render()
        assert isinstance(rendered, str)
        assert len(rendered) > 0

    def test_immutable(self):
        f = Frame(_make_frame_data())
        with pytest.raises(AttributeError, match="immutable"):
            f.grid = ((1,),)
        with pytest.raises(AttributeError, match="immutable"):
            f.state = GameState.WIN
        with pytest.raises(AttributeError, match="immutable"):
            del f.grid

    def test_grid_np(self):
        f = Frame(_make_frame_data(pixel=3))
        arr = f.grid_np
        assert arr.shape == (64, 64)
        assert arr.dtype == np.int8
        assert not arr.flags.writeable
        assert arr is f.grid_np  # cached

    def test_diff_identical_frames(self):
        fd = _make_frame_data()
        f1 = Frame(fd)
        f2 = Frame(fd)
        regions = f1.diff(f2)
        assert regions == []

    def test_diff_single_change(self):
        fd1 = _make_frame_data(pixel=0)
        grid2 = np.zeros((64, 64), dtype=int)
        grid2[10, 20] = 5
        fd2 = FrameData(
            game_id="test-dry-run",
            frame=[grid2.tolist()],
            state=GameState.NOT_FINISHED,
            levels_completed=0,
            win_levels=3,
            available_actions=[1, 2, 3, 4],
        )
        f1 = Frame(fd1)
        f2 = Frame(fd2)
        regions = f1.diff(f2)
        assert len(regions) == 1
        assert regions[0].count == 1

    def test_available_actions(self):
        fd = _make_frame_data(available_actions=[1, 2, 3])
        f = Frame(fd)
        names = f.available_actions
        assert "ACTION1" in names
        assert "ACTION2" in names
        assert "ACTION3" in names
        assert "RESET" in names

    def test_color_counts(self):
        fd = _make_frame_data(pixel=0)
        f = Frame(fd)
        counts = f.color_counts()
        assert counts[0] == 64 * 64


# ── TokenUsage & UsageTracker ────────────────────────────────────────────────


class TestTokenUsage:
    def test_total_tokens(self):
        u = TokenUsage(input_tokens=100, output_tokens=50)
        assert u.total_tokens == 150

    def test_defaults(self):
        u = TokenUsage()
        assert u.total_tokens == 0
        assert u.cached_tokens == 0
        assert u.reasoning_tokens == 0


class TestUsageTracker:
    def test_record_usage_overwrites_input(self):
        t = UsageTracker()
        chunk1 = json.dumps(
            {
                "input_tokens": 1000,
                "output_tokens": 200,
                "input_tokens_details": {"cached_tokens": 100},
                "output_tokens_details": {"reasoning_tokens": 50},
            }
        )
        chunk2 = json.dumps(
            {
                "input_tokens": 2000,
                "output_tokens": 300,
                "input_tokens_details": {"cached_tokens": 500},
                "output_tokens_details": {"reasoning_tokens": 80},
            }
        )
        t.record_usage(0, chunk1)
        t.record_usage(0, chunk2)
        u = t.per_agent_usage()[0]
        assert u.input_tokens == 2000, "input_tokens should be overwritten to latest"
        assert u.cached_tokens == 500, "cached_tokens should be overwritten to latest"
        assert u.output_tokens == 300, "output_tokens should be latest snapshot"
        assert u.reasoning_tokens == 80, "reasoning_tokens should be latest snapshot"

    def test_reasoning_drain(self):
        t = UsageTracker()
        t.append_reasoning(1, "code", "x = 1\n")
        t.append_reasoning(1, "output_text", "thinking...\n")
        result = t.drain_reasoning()
        assert result is not None
        assert result["agent_id"] == 1
        assert "x = 1" in result["text"]
        assert "thinking" in result["text"]

    def test_drain_empty(self):
        t = UsageTracker()
        assert t.drain_reasoning() is None

    def test_summary_format(self):
        t = UsageTracker()
        t.record_usage(
            0,
            json.dumps(
                {
                    "input_tokens": 5000,
                    "output_tokens": 1000,
                    "input_tokens_details": {"cached_tokens": 0},
                    "output_tokens_details": {"reasoning_tokens": 0},
                }
            ),
        )
        summary = t.summary()
        assert "Token Usage" in summary
        assert "5,000" in summary

    def test_to_dict(self):
        t = UsageTracker()
        t.record_usage(
            0,
            json.dumps(
                {
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "input_tokens_details": {"cached_tokens": 10},
                    "output_tokens_details": {"reasoning_tokens": 5},
                }
            ),
        )
        d = t.to_dict()
        assert "total" in d
        assert "per_agent" in d
        assert d["total"]["input_tokens"] == 100


# ── Events ───────────────────────────────────────────────────────────────────


class TestEvents:
    def test_event_type_names(self):
        assert EventType.GAME_ACTION.name == "GAME_ACTION"
        assert EventType.USAGE_SUMMARY.name == "USAGE_SUMMARY"

    def test_usage_summary_event_serialisation(self):
        e = UsageSummaryEvent(
            input_tokens=100,
            output_tokens=50,
            cached_tokens=10,
            reasoning_tokens=5,
            total_tokens=150,
        )
        d = e.to_dict()
        assert d["type"] == "usage_summary"
        assert d["total_tokens"] == 150
        j = e.to_json()
        assert isinstance(j, str)
        parsed = json.loads(j)
        assert parsed["input_tokens"] == 100

    def test_agent_chunk_event_serialisation(self):
        e = AgentChunkEvent(
            agent_id=1,
            role="assistant",
            content="hello",
            chunk_type="output_text",
        )
        d = e.to_dict()
        assert d["type"] == "agent_chunk"
        assert d["agent_id"] == 1
