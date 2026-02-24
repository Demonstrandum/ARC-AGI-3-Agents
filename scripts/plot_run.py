#!/usr/bin/env python3
"""
Plot cumulative actions vs level progress for ARC-AGI-3 recording files.

Usage:
    uv run scripts/plot_run.py recordings/vc33-*.recording.jsonl
    uv run scripts/plot_run.py recordings/vc33-*.recording.jsonl -o plots/vc33.html
    uv run scripts/plot_run.py recordings/vc33-*.recording.jsonl --wins-only
"""

import argparse
import json
import sys
from pathlib import Path

import plotly.graph_objects as go

REPO_ROOT = Path(__file__).resolve().parent.parent

PALETTE = [
    "#636EFA", "#EF553B", "#00CC96", "#AB63FA", "#FFA15A",
    "#19D3F3", "#FF6692", "#B6E880", "#FF97FF", "#FECB52",
]


def parse_recording(path: Path) -> dict:
    """Parse a .recording.jsonl into run metadata (one frame = one action)."""
    game_id = ""
    win_levels = 0
    action_count = 0
    max_level = 0
    final_state = "NOT_FINISHED"
    steps: list[tuple[int, int]] = [(0, 0)]

    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            data = obj.get("data", {})
            if not data or "game_id" not in data:
                continue

            game_id = data["game_id"]
            win_levels = data.get("win_levels", 0)
            levels = data.get("levels_completed", 0)
            final_state = data.get("state", "NOT_FINISHED")

            action_count += 1

            if levels > max_level:
                max_level = levels
                steps.append((action_count, max_level))

    won = final_state == "WIN" or max_level >= win_levels > 0

    return {
        "path": path,
        "game_id": game_id,
        "win_levels": win_levels,
        "total_actions": action_count,
        "max_level": max_level,
        "won": won,
        "steps": steps,
    }


def load_baseline_from_metadata(game_id: str) -> list[int] | None:
    """Load baseline_actions from environment_files/<game>/<hash>/metadata.json."""
    parts = game_id.split("-", 1)
    if len(parts) != 2:
        return None
    meta_path = REPO_ROOT / "environment_files" / parts[0] / parts[1] / "metadata.json"
    if not meta_path.exists():
        return None
    with open(meta_path) as f:
        meta = json.load(f)
    ba = meta.get("baseline_actions")
    return ba if isinstance(ba, list) else None


def load_game_title(game_id: str) -> str:
    parts = game_id.split("-", 1)
    if len(parts) != 2:
        return game_id
    meta_path = REPO_ROOT / "environment_files" / parts[0] / parts[1] / "metadata.json"
    if not meta_path.exists():
        return game_id
    with open(meta_path) as f:
        meta = json.load(f)
    return meta.get("title", game_id)


def build_step_xy(steps: list[tuple[int, int]], tail_x: int, tail_y: int):
    """Expand step data into plotly-friendly step-connected x/y lists."""
    xs: list[int] = []
    ys: list[int] = []
    for i, (sx, sy) in enumerate(steps):
        if i > 0:
            xs.append(sx)
            ys.append(steps[i - 1][1])
        xs.append(sx)
        ys.append(sy)
    xs.append(tail_x)
    ys.append(tail_y)
    return xs, ys


TOP_LABELED = 5


def plot_game(recording_paths: list[Path], baseline_override: str | None = None,
              wins_only: bool = False) -> go.Figure | None:
    """Build a plotly Figure for one game's recordings. Returns None if no data."""
    runs = [parse_recording(p) for p in recording_paths]
    runs = [r for r in runs if r["game_id"]]
    if not runs:
        return None

    if wins_only:
        runs = [r for r in runs if r["won"]]
    runs = [r for r in runs if r["max_level"] > 0]
    if not runs:
        return None

    game_id = runs[0]["game_id"]
    title = load_game_title(game_id)
    win_levels = max(r["win_levels"] for r in runs)
    n_won = sum(1 for r in runs if r["won"])
    n_cancelled = sum(1 for r in runs if not r["won"])

    baseline: list[int] | None = None
    if baseline_override:
        baseline = [int(x.strip()) for x in baseline_override.split(",")]
    else:
        baseline = load_baseline_from_metadata(game_id)
        if baseline:
            print(f"Loaded human baseline for {game_id}: {baseline}")

    fig = go.Figure()

    # --- Human baseline ---
    if baseline:
        bx, by = [0], [0]
        cumulative = 0
        for i, b in enumerate(baseline):
            cumulative += b
            bx.append(cumulative)
            by.append(i)
            bx.append(cumulative)
            by.append(i + 1)
        fig.add_trace(go.Scatter(
            x=bx, y=by, mode="lines",
            name=f"Human baseline ({sum(baseline)} actions)",
            line=dict(color="black", width=3, dash="4px,3px"),
            hovertemplate="Actions: %{x}<br>Level: %{y}<extra>Human</extra>",
        ))

    # --- Win threshold ---
    fig.add_hline(
        y=win_levels, line_dash="dot", line_color="#cc3333", line_width=1.5,
        opacity=0.5, annotation_text=f"Win ({win_levels} levels)",
        annotation_position="top left",
        annotation_font_color="#cc3333", annotation_font_size=11,
    )

    # --- Agent runs ---
    sorted_runs = sorted(runs, key=lambda r: (-r["max_level"], r["total_actions"]))
    for i, run in enumerate(sorted_runs):
        xs, ys = build_step_xy(run["steps"], run["total_actions"], run["max_level"])
        guid = run["path"].stem.split(".")[-2][:8]

        if run["won"]:
            name = f"{guid} - WON in {run['total_actions']} actions"
            color, width, opacity = "#1a73e8", 3.5, 1.0
            legendrank = 100
        elif i < TOP_LABELED:
            name = f"{guid} - cancelled at L{run['max_level']} ({run['total_actions']} actions)"
            color = PALETTE[i % len(PALETTE)]
            width, opacity = 1.5, 0.7
            legendrank = 200 + i
        else:
            name = f"{guid} - cancelled at L{run['max_level']} ({run['total_actions']} actions)"
            color, width, opacity = "#aaaaaa", 1.0, 0.45
            legendrank = 300 + i

        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines", name=name,
            line=dict(color=color, width=width),
            opacity=opacity,
            legendrank=legendrank,
            showlegend=i < TOP_LABELED or run["won"],
            hovertemplate=f"Actions: %{{x}}<br>Level: %{{y}}<extra>{guid}</extra>",
        ))

    n_hidden = max(0, len(sorted_runs) - TOP_LABELED - n_won)
    if n_hidden > 0:
        fig.add_trace(go.Scatter(
            x=[None], y=[None], mode="lines", name=f"({n_hidden} more cancelled runs)",
            line=dict(color="#cccccc", width=1), legendrank=999, showlegend=True,
        ))

    subtitle_parts = []
    if n_won:
        subtitle_parts.append(f"{n_won} won")
    if n_cancelled:
        subtitle_parts.append(f"{n_cancelled} cancelled early")

    fig.update_layout(
        title=dict(
            text=f"<b>{title}</b> ({game_id})<br>"
                 f"<span style='font-size:13px;color:#666'>"
                 f"{len(runs)} runs: {', '.join(subtitle_parts)}</span>",
            x=0.5, xanchor="center",
        ),
        xaxis_title="Cumulative Actions",
        xaxis=dict(range=[0, max(r["total_actions"] for r in runs) * 1.03]),
        yaxis_title="Levels Completed",
        yaxis=dict(dtick=1, range=[-0.3, win_levels + 0.8]),
        template="plotly_white",
        legend=dict(
            font_size=11,
            bgcolor="rgba(255,255,255,0.85)",
            bordercolor="#ddd", borderwidth=1,
        ),
        margin=dict(t=90, b=60, l=60, r=30),
        hoverlabel=dict(font_size=12),
    )

    return fig


def main():
    parser = argparse.ArgumentParser(description="Plot actions vs level for ARC-AGI-3 runs")
    parser.add_argument("recordings", nargs="+", type=Path, help="Recording .jsonl files")
    parser.add_argument("--baseline", type=str,
                        help="Override per-level human baseline actions, comma-separated")
    parser.add_argument("--wins-only", action="store_true", help="Only plot winning runs")
    parser.add_argument("-o", "--output", type=Path, help="Save plot to file (.html or .png)")
    args = parser.parse_args()

    fig = plot_game(args.recordings, args.baseline, args.wins_only)
    if fig is None:
        print("No runs with level progress found.", file=sys.stderr)
        sys.exit(1)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        if args.output.suffix == ".png":
            fig.write_image(str(args.output), width=1200, height=600, scale=2)
        else:
            fig.write_html(str(args.output))
        print(f"Saved to {args.output}")
    else:
        fig.show()


if __name__ == "__main__":
    main()
