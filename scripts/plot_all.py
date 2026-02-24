#!/usr/bin/env python3
"""
Discover all games in recordings/ and generate a plot for each into plots/.

Usage:
    uv run scripts/plot_all.py
    uv run scripts/plot_all.py --wins-only
"""

import argparse
from collections import defaultdict
from pathlib import Path

from plot_run import REPO_ROOT, plot_game, load_game_title

RECORDINGS_DIR = REPO_ROOT / "recordings"
PLOTS_DIR = REPO_ROOT / "plots"


def write_index(games: list[tuple[str, str, int]]):
    """Write plots/index.html linking to all game plots.

    games is a list of (game_id, title, n_recordings).
    """
    rows = ""
    for game_id, title, n_rec in games:
        rows += (
            f'      <div class="card">\n'
            f'        <a href="{game_id}.html">\n'
            f'          <img src="{game_id}.png" alt="{title}">\n'
            f'        </a>\n'
            f'        <div class="label">\n'
            f'          <strong>{title}</strong>\n'
            f'          <span>{game_id} &middot; {n_rec} recordings</span>\n'
            f'        </div>\n'
            f'      </div>\n'
        )

    html = (
        '<!DOCTYPE html>\n'
        '<html lang="en"><head>\n'
        '<meta charset="utf-8">\n'
        '<title>ARC-AGI-3 Agent Plots</title>\n'
        '<style>\n'
        '  * { box-sizing: border-box; margin: 0; padding: 0; }\n'
        '  body { font-family: system-ui, sans-serif; background: #f5f5f5; padding: 2rem; }\n'
        '  h1 { text-align: center; margin-bottom: .3rem; }\n'
        '  .subtitle { text-align: center; color: #666; margin-bottom: 2rem; font-size: .95rem; }\n'
        '  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(540px, 1fr));\n'
        '          gap: 1.5rem; max-width: 1400px; margin: 0 auto; }\n'
        '  .card { background: #fff; border-radius: 8px; overflow: hidden;\n'
        '          box-shadow: 0 1px 4px rgba(0,0,0,.1); transition: transform .15s; }\n'
        '  .card:hover { transform: translateY(-3px); box-shadow: 0 4px 12px rgba(0,0,0,.15); }\n'
        '  .card a { display: block; }\n'
        '  .card img { width: 100%; display: block; }\n'
        '  .label { padding: .75rem 1rem; }\n'
        '  .label strong { display: block; font-size: 1.05rem; }\n'
        '  .label span { color: #888; font-size: .85rem; }\n'
        '</style>\n'
        '</head><body>\n'
        '<h1>ARC-AGI-3 Agent Plots</h1>\n'
        f'<p class="subtitle">{len(games)} games &middot; click a card for the interactive plot</p>\n'
        '<div class="grid">\n'
        f'{rows}'
        '</div>\n'
        '</body></html>\n'
    )

    (PLOTS_DIR / "index.html").write_text(html)


def main():
    parser = argparse.ArgumentParser(description="Plot all ARC-AGI-3 games")
    parser.add_argument("--wins-only", action="store_true")
    args = parser.parse_args()

    by_game: dict[str, list[Path]] = defaultdict(list)
    for p in sorted(RECORDINGS_DIR.glob("*.recording.jsonl")):
        game_id = p.name.split(".")[0]
        by_game[game_id].append(p)

    if not by_game:
        print(f"No recordings found in {RECORDINGS_DIR}")
        return

    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    index_entries: list[tuple[str, str, int]] = []
    for game_id, paths in sorted(by_game.items()):
        print(f"\n--- {game_id} ({len(paths)} recordings) ---")
        fig = plot_game(paths, wins_only=args.wins_only)
        if fig is None:
            print("  Skipped (no runs with level progress)")
            continue
        html_out = PLOTS_DIR / f"{game_id}.html"
        png_out = PLOTS_DIR / f"{game_id}.png"
        fig.write_html(str(html_out))
        fig.write_image(str(png_out), width=1200, height=600, scale=2)
        print(f"  Saved to {html_out} + {png_out}")
        index_entries.append((game_id, load_game_title(game_id), len(paths)))

    write_index(index_entries)
    print(f"\nAll plots + index.html written to {PLOTS_DIR}/")


if __name__ == "__main__":
    main()
