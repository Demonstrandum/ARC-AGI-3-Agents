# The idea

What's particular about the **Arcgentica** "RLM" harness (built on the [Agentica](https://github.com/symbolica-ai/agentica-server) SDK) for ARC-AGI-3?

**Game-agnostic.** No game-specific prompting. The agent doesn't know what the
colors mean, what the actions do, or what the win condition is. It figures
everything out by interacting with the game and observing what changes.

**Orchestrator + specialized subagents.** One top-level orchestrator that never
touches the game directly. It delegates to subagents, accumulates knowledge, and
decides what to try next. If it starts looking at grids, its context fills up
with pixel data and it loses the ability to think strategically. Subagents
report back in short text summaries, not raw data.

**Subagents get only the tools they need.** Explorers get `submit_action` and a
frame -- they poke around, diff before/after, and report what they found.
Theorists get text summaries only (no `submit_action`), forcing them to reason
about rules without being tempted to waste actions. Testers get `submit_action`
with a tight budget to confirm or deny a hypothesis. Solvers get
`submit_action` and a confirmed strategy.

**Reuse vs. fresh.** Calling the same agent again is cheaper and it remembers
everything. But if a line of reasoning has clearly failed, anchoring on it is
worse than starting over. The orchestrator picks: feed new info into the existing
agent, or spawn a clean one with just a summary of what's been learned so far.

**Shared memory.** A `memories` database is shared across all agents for the
duration of the game. Subagents write confirmed facts (scene layout, mechanics,
win conditions) and hypotheses (clearly marked) as they work. New agents query
memories before starting, so they inherit collective knowledge without the
orchestrator having to relay everything manually. This is especially valuable
when retiring a context-saturated agent and spawning a replacement.

**Action budgets.** Actions are limited (~800 total across all levels). The
orchestrator sets per-subagent budgets via `make_bounded_submit_action(limit)`.
Agents are told to avoid redundant actions, not reset unless genuinely stuck,
and prefer targeted experiments over exhaustive sweeps. RESET is free (doesn't
count) but wastes all progress on the current attempt.

**Level transitions.** When a level is solved, the next one loads within the same
action. The returned frame already shows the new level. `state=WIN` only fires
when all levels are beaten; individual completion is detected by watching
`levels_completed` increment. The orchestrator decides whether the same strategy
applies or whether a fresh explore cycle is needed.

