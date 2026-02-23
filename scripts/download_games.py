"""
Download all available games for offline use.

Usage: uv run python scripts/download_games.py [--game GAME_ID]

Without --game, downloads all games available to your API key.
With --game, downloads only the specified game (prefix match, e.g. "ls20").
"""

import argparse
import os

from dotenv import load_dotenv

load_dotenv(dotenv_path=".env.example")
load_dotenv(dotenv_path=".env", override=True)

from arc_agi import Arcade

# arc_agi's own import re-runs load_dotenv(override=True), so we must
# set this AFTER the import to actually override the .env value.
os.environ["OPERATION_MODE"] = "normal"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download ARC-AGI-3 games for offline use."
    )
    parser.add_argument(
        "-g", "--game", help="Game ID prefix to download (e.g. 'ls20'). Omit for all."
    )
    args = parser.parse_args()

    arcade = Arcade()
    envs = arcade.get_environments()

    if not envs:
        print("No environments found. Check your ARC_API_KEY.")
        return

    if args.game:
        envs = [e for e in envs if e.game_id.startswith(args.game)]
        if not envs:
            print(f"No environments matching '{args.game}'.")
            return

    print(f"Downloading {len(envs)} game(s)...")
    for env in envs:
        gid = env.game_id
        print(f"  {gid} ... ", end="", flush=True)
        wrapper = arcade.make(gid)
        if wrapper is not None:
            print("ok")
        else:
            print("FAILED")

    env_dir = os.getenv("ENVIRONMENTS_DIR", "environment_files")
    print(f"\nDone. Games saved to {env_dir}/")
    print("You can now run with OPERATION_MODE=offline")


if __name__ == "__main__":
    main()
