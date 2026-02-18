# The idea

**Totally game-agnostic.** The agent receives no game-specific prompting at all.
It doesn't know what the colors mean, what the actions do, what the win
condition is, or how many levels there are. It has to figure all of that out
from scratch by interacting with the game and observing what changes.

**Orchestrator + specialized subagents.** One top-level orchestrator that never
touches the game. It delegates to subagents, accumulates knowledge, and decides
what to try next. If it starts looking at grids, its context fills up with pixel
data and it loses the ability to think strategically.

**Subagents get only the tools they need.** Explorers get `submit_action` and a
frame, poke around, diff before/after, and report what they found. Theorists get
text summaries only (no `submit_action`), forcing them to reason about rules
without being tempted to waste actions. Testers get `submit_action` with a tight
budget to confirm or deny a hypothesis. Solvers get `submit_action` and a
confirmed strategy.

**Reuse vs. fresh.** Calling the same agent again is cheaper and it remembers
everything. But if a line of reasoning has clearly failed, anchoring on it is
worse than starting over. The orchestrator picks: feed new info into the existing
agent, or spawn a clean one with just a summary of what's been learned so far.

**Knowledge accumulation.** The orchestrator maintains a running knowledge base
passed to every new subagent. Scene map (what each color means, where objects
are, how layout changes across levels), confirmed mechanics (what each action
does, win/lose conditions), what analysis techniques worked ("cropping to the
active region made structure obvious"), and what didn't (dead ends, disproven
hypotheses, wasted approaches). Agents shouldn't start from scratch. Every
subagent inherits the collective learning of all previous subagents.

**Action budgets.** Actions are limited (~800 total). The orchestrator sets
per-subagent budgets ("use at most 10 actions to explore"). Agents are told to
avoid redundant actions, not reset unless stuck, and prefer targeted experiments
over exhaustive sweeps. RESET is free (doesn't count) but wastes a turn if the
level is already clean.

**Level transitions.** When a level is solved, the next one loads within the same
action. The returned frame already shows the new level. `state=WIN` only fires
when all levels are beaten; individual completion is detected by watching
`levels_completed` increment. The orchestrator decides whether the same strategy
applies or whether a fresh explore cycle is needed.

**Not yet implemented.** Parallel subagents on forked game states. The engine is
stateful, not a pure function, but deep-copying the game instance to run parallel
hypotheses looks feasible in local mode. Also no long-term memory across
different game_ids.
