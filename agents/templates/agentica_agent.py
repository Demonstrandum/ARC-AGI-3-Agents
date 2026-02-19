import asyncio
import json
import logging
import os
import time
from collections import deque
from pathlib import Path
from typing import Any, Literal

import numpy as np
from agentica import spawn
from agentica.common import ReasoningEffort
from agentica.logging import AgentListener, set_default_agent_listener
from arcengine import FrameData, GameAction, GameState

from arcgentica import EventServer, WsLogger
from arcgentica.frame import Frame
from arcgentica.game_ref import GAME_REFERENCE, SYSTEM_PROMPT

from ..agent import Agent
from ..tracing import trace_agent_session

logger = logging.getLogger()

ActionName = Literal[
    "RESET",
    "ACTION1",
    "ACTION2",
    "ACTION3",
    "ACTION4",
    "ACTION5",
    "ACTION6",
]

MAIN_AGENT_MODEL: str = "anthropic/claude-opus-4-6"
SUBAGENT_MODEL: str = "anthropic/claude-sonnet-4-6"
REASONING_EFFORT: ReasoningEffort = "high"


class Agentica(Agent):
    """
    Agent that uses the Agentica SDK with a submit_action tool.

    Calls the LLM once -- the LLM drives the game by calling
    submit_action repeatedly within a single agent.call() invocation.
    """

    MAX_ACTIONS = 800

    def __init__(self, *args: Any, visualize: bool = False, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.visualize = visualize or os.environ.get("VISUALIZE", "") == "1"
        self._server: EventServer | None = None
        self._action_log_dir: Path | None = None
        self._action_log_file: Any = None
        self._logged_level: int = -1

    def _log_action(self, action: GameAction, frame: Frame) -> None:
        """
        Append one JSONL line per action. Rotates file on level change.
        """
        if self._action_log_dir is None:
            self._action_log_dir = Path("actions_log") / self.game_id
            self._action_log_dir.mkdir(parents=True, exist_ok=True)

        level = frame.levels_completed
        if level != self._logged_level:
            if self._action_log_file is not None:
                self._action_log_file.close()
            path = self._action_log_dir / f"level_{level}.jsonl"
            self._action_log_file = open(path, "a")
            self._logged_level = level

        entry = {
            "action": action.name,
            "count": self.action_counter,
            "level": level,
            "state": frame.state.name,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        if action.is_complex():
            entry["x"] = action.action_data.x
            entry["y"] = action.action_data.y

        self._action_log_file.write(json.dumps(entry) + "\n")
        self._action_log_file.flush()

    def _close_action_log(self) -> None:
        if self._action_log_file is not None:
            self._action_log_file.close()
            self._action_log_file = None

    # Required abstract methods (not used since we override main)
    def is_done(self, frames: list[FrameData], latest_frame: FrameData) -> bool:
        return latest_frame.state is GameState.WIN

    def choose_action(
        self, frames: list[FrameData], latest_frame: FrameData
    ) -> GameAction:
        raise NotImplementedError("Agentica agent overrides main()")

    def _make_submit_action(self, server: EventServer | None = None):
        """
        Create the submit_action tool function for the agentica agent.
        """

        _MAX_HISTORY = 50
        last_available: list[int] = []
        # True when a non-RESET action has been taken since the last reset.
        # When False, the engine's _action_count is 0 and a RESET would
        # trigger a destructive full_reset back to level 0.
        has_moves_since_reset: bool = False
        last_frame: Frame | None = None
        _action_history: deque[tuple[str, Frame]] = deque(maxlen=_MAX_HISTORY)

        def _push_frame(action: GameAction, raw: FrameData) -> Frame:
            nonlocal last_available, has_moves_since_reset, last_frame
            last_available = raw.available_actions
            self.append_frame(raw)
            self.action_counter += 1
            if action is GameAction.RESET:
                has_moves_since_reset = False
            elif (
                last_frame is not None
                and raw.levels_completed != last_frame.levels_completed
            ):
                # Level transition: engine called set_level() which zeroed
                # _action_count, so the next RESET would be a full_reset.
                has_moves_since_reset = False
            else:
                has_moves_since_reset = True
            logger.info(
                f"{self.game_id} - {action.name}: count {self.action_counter}, "
                f"level {raw.levels_completed}/{raw.win_levels}"
            )
            frame = Frame(raw)
            last_frame = frame
            _action_history.append((action.name, frame))
            self._log_action(action, frame)
            if server is not None:
                cx = action.action_data.x if action.is_complex() else None
                cy = action.action_data.y if action.is_complex() else None
                server.push_game_action(
                    action.name,
                    frame,
                    self.action_counter,
                    click_x=cx,
                    click_y=cy,
                )
            return frame

        def submit_action(
            action_name: ActionName | Literal["NOOP"], x: int = 0, y: int = 0
        ) -> Frame:
            """
            Submit a game action and receive the new frame (sync function).

            Args:
                action_name: One of RESET, ACTION1-ACTION6.
                    You can also pass "NOOP" to retrieve the current frame
                    without taking any action or incrementing the action count.
                x: X coordinate (0-63), only for ACTION6
                y: Y coordinate (0-63), only for ACTION6

            Returns:
                Frame with the new game state, grid, and available actions.
            """
            if action_name.upper() == "NOOP":
                # Last frame will not be `None` since RESET is always called before any other action.
                return last_frame  # type: ignore[return-value]

            action = GameAction.from_name(action_name)

            if (
                last_available
                and action is not GameAction.RESET
                and action.value not in last_available
            ):
                allowed = [GameAction.from_id(a).name for a in last_available]
                raise ValueError(
                    f"{action.name} is not available. Available actions: {allowed}"
                )

            # Block redundant RESETs that would cause a full game reset.
            # The engine does full_reset when _action_count==0, which is
            # the case right after any level_reset or level transition.
            # Since no moves were taken, the level is already clean — just
            # return the current frame.
            if action is GameAction.RESET and not has_moves_since_reset:
                if last_frame is not None:
                    logger.info(f"{self.game_id} - RESET skipped (level already clean)")
                    return last_frame

            if action.is_complex():
                action.set_data({"x": x, "y": y})

            raw = self.take_action(action)

            # Session may have gone stale — RESET and retry once
            if raw is None and action is not GameAction.RESET:
                logger.warning(
                    f"{self.game_id} - {action.name} failed, "
                    "resetting session and retrying"
                )
                reset_raw = self.take_action(GameAction.RESET)
                if reset_raw:
                    self.append_frame(reset_raw)
                    self.action_counter += 1
                raw = self.take_action(action)

            if raw:
                return _push_frame(action, raw)

            raise ValueError("Action failed — no frame returned.")

        def history(n: int = _MAX_HISTORY) -> list[tuple[str, Frame]]:
            """
            Return the last n (action_name, Frame) pairs from the game, oldest first.
            This is a synchronous function, do NOT use await.

            Covers actions taken by ALL agents (not just the current one). Use this
            to review what happened after executing a sequence of actions, or to
            understand the game state before you started.

            Args:
                n: How many recent entries to return. Defaults to 50 (the max stored).
            """
            entries = list(_action_history)
            return entries[-n:] if n < len(entries) else entries

        return submit_action, history

    @staticmethod
    def _make_bounded_submit_action(inner, limit: int | None):
        """
        Wrap an existing submit_action, optionally with a hard action budget.

        The returned function delegates to `inner` for all calls. It shares
        inner's closure state (last_frame, has_moves_since_reset, etc.) so
        RESET guards and NOOP work correctly.

        Args:
            inner: The submit_action to wrap.
            limit: Maximum non-NOOP, non-RESET actions allowed, or None for unlimited.
        """
        if limit is None:

            def unbounded(
                action_name: ActionName | Literal["NOOP"], x: int = 0, y: int = 0
            ) -> Frame:
                return inner(action_name, x, y)

            unbounded.__doc__ = inner.__doc__
            unbounded.__name__ = "submit_action"
            return unbounded

        remaining = limit

        def bounded(
            action_name: ActionName | Literal["NOOP"], x: int = 0, y: int = 0
        ) -> Frame:
            nonlocal remaining
            upper = action_name.upper()
            if upper != "NOOP" and upper != "RESET":
                if remaining <= 0:
                    raise ValueError(
                        f"Action budget exhausted: all {limit} actions have been used."
                    )
                remaining -= 1
            return inner(action_name, x, y)

        bounded.__doc__ = (
            (inner.__doc__ or "")
            + f"\n\nThis instance is limited to {limit} game actions (NOOP and RESET are free)."
        )
        bounded.__name__ = "submit_action"
        return bounded

    async def spawn_agent(self, system_prompt: str | None = None):
        """
        Spawn a new subagent that can be called repeatedly.

        Returns an agent handle. Use ``await agent.call(return_type, task, **objects)``
        to invoke it. The same handle can be called multiple times; each call
        continues the conversation so the agent retains context from prior calls.
        Pass ``submit_action`` only to agents that need to take game actions.

        Be careful about when you want to reuse context vs. spawn a new agent,
        performance degrades as context grows, so there is a trade-off you have to consider.
        """
        return await spawn(
            model=SUBAGENT_MODEL,
            premise=system_prompt,
            reasoning_effort=REASONING_EFFORT,
            scope={
                "spawn_agent": self.spawn_agent,
                "np": np,
            },
        )

    async def _run(self) -> None:
        """
        Async entry point: spawn agentica agent and let it play.
        """
        server: EventServer | None = None
        if self.visualize:
            server = EventServer(game_id=self.game_id)
            await server.start()
            self._server = server
            set_default_agent_listener(lambda: AgentListener(WsLogger(server)))
        else:
            set_default_agent_listener(None)

        submit_action, history = self._make_submit_action(server=server)

        # TODO: future idea --- also allow restricting to a subset of actions, e.g. only ACTION1-ACTION4.
        #       determine if this is useful for any of the games.
        def make_bounded_submit_action(limit: int | None):
            """
            Create a new ``submit_action`` function, optionally with a hard action budget.

            Returns a ``submit_action`` that works identically to the normal one.
            If ``limit`` is an int, raises ValueError after that many game actions.
            If ``limit`` is None, the returned function is unbounded.
            NOOP and RESET are free and do not count toward the limit.

            Use this to enforce action budgets on subagents:
                bounded_sa = make_bounded_submit_action(10)
                await agent.call(..., submit_action=bounded_sa)

            Args:
                limit: Max game actions (ACTION1-ACTION6) allowed, or None for unlimited.
            """
            return Agentica._make_bounded_submit_action(submit_action, limit)

        # Double RESET guarantees a completely fresh game
        initial_raw = self.take_action(GameAction.RESET)
        if initial_raw:
            self.append_frame(initial_raw)
            self.action_counter += 1

        initial_frame = submit_action("RESET")

        orchestrator = await spawn(
            model=MAIN_AGENT_MODEL,
            premise=SYSTEM_PROMPT,
            reasoning_effort=REASONING_EFFORT,
            scope={
                "spawn_agent": self.spawn_agent,
                "np": np,
            },
        )
        remaining = self.MAX_ACTIONS - self.action_counter
        actions = ", ".join(initial_frame.available_actions)
        return await orchestrator.call(
            None,
            f"You are playing the game `{self.game_id}`. "
            f"Level {initial_frame.levels_completed}/{initial_frame.win_levels}. "
            f"{remaining} actions remaining.\n"
            f"Available actions for this level: {actions}\n\n"
            "Take a moment to plan your approach before spawning any agents. "
            "When ready, spawn an explorer and give it a bounded submit_action, "
            "`initial_frame`, and `GAME_REFERENCE`.",
            initial_frame=initial_frame,
            make_bounded_submit_action=make_bounded_submit_action,
            history=history,
            GAME_REFERENCE=GAME_REFERENCE,
        )

    @trace_agent_session
    def main(self) -> None:
        """
        Override the base agent loop — agentica drives the game.
        """
        self.timer = time.time()
        try:
            asyncio.run(self._run())
        finally:
            self._close_action_log()
            if self._server is not None:
                asyncio.run(self._server.stop())
            self.cleanup()
