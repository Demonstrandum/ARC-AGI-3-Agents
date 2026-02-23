"""
Frame wrapper around arcengine.FrameData with grid inspection helpers.
"""

from dataclasses import dataclass
from typing import Literal, Self

from arcengine import FrameData, GameAction, GameState


@dataclass(slots=True)
class DiffRegion:
    """
    A contiguous region of changed cells between two frames.

    Attributes:
        x0, y0, x1, y1: Bounding box (inclusive start, exclusive end).
        changes: [(x, y, old_val, new_val), ...] within this region.
    """

    x0: int
    y0: int
    x1: int
    y1: int
    changes: list[tuple[int, int, int, int]]

    @property
    def width(self) -> int:
        return self.x1 - self.x0

    @property
    def height(self) -> int:
        return self.y1 - self.y0

    @property
    def count(self) -> int:
        return len(self.changes)

    def __repr__(self) -> str:
        return (
            f"DiffRegion(x=[{self.x0},{self.x1}) y=[{self.y0},{self.y1}), "
            f"{self.count} changes)"
        )


def _cluster_changes(
    changes: list[tuple[int, int, int, int]],
    margin: int = 2,
) -> list[DiffRegion]:
    """
    Group changes into contiguous regions.

    Two changes belong to the same region if their bounding boxes
    (expanded by *margin* pixels) overlap.
    """
    if not changes:
        return []

    # Sort by (y, x) for spatial locality
    sorted_changes = sorted(changes, key=lambda c: (c[1], c[0]))

    regions: list[list[tuple[int, int, int, int]]] = []
    boxes: list[list[int]] = []  # [min_x, min_y, max_x, max_y] per region

    for change in sorted_changes:
        x, y = change[0], change[1]
        merged = False
        for i, box in enumerate(boxes):
            if (
                x >= box[0] - margin
                and x <= box[2] + margin
                and y >= box[1] - margin
                and y <= box[3] + margin
            ):
                regions[i].append(change)
                box[0] = min(box[0], x)
                box[1] = min(box[1], y)
                box[2] = max(box[2], x)
                box[3] = max(box[3], y)
                merged = True
                break
        if not merged:
            regions.append([change])
            boxes.append([x, y, x, y])

    # Merge any regions whose expanded boxes now overlap
    merged_any = True
    while merged_any:
        merged_any = False
        i = 0
        while i < len(boxes):
            j = i + 1
            while j < len(boxes):
                bi, bj = boxes[i], boxes[j]
                if (
                    bi[0] - margin <= bj[2] + margin
                    and bi[2] + margin >= bj[0] - margin
                    and bi[1] - margin <= bj[3] + margin
                    and bi[3] + margin >= bj[1] - margin
                ):
                    # Merge j into i
                    regions[i].extend(regions[j])
                    bi[0] = min(bi[0], bj[0])
                    bi[1] = min(bi[1], bj[1])
                    bi[2] = max(bi[2], bj[2])
                    bi[3] = max(bi[3], bj[3])
                    regions.pop(j)
                    boxes.pop(j)
                    merged_any = True
                else:
                    j += 1
            i += 1

    return [
        DiffRegion(x0=box[0], y0=box[1], x1=box[2] + 1, y1=box[3] + 1, changes=region)
        for region, box in zip(regions, boxes)
    ]


class Frame:
    """
    Wrapper around FrameData with grid inspection helpers.

    Attributes:
        grid: 2D list[list[int]] — the current level's grid.
        winning_frame: A full Frame of the just-completed level when a level
            transition occurred on this action, otherwise None. Has all the
            same helpers (render, diff, find, etc.) so you can inspect what
            the winning state looked like.
        state: Current GameState (NOT_FINISHED, WIN, GAME_OVER).
        levels_completed: Levels beaten so far.
        win_levels: Total levels required to win the game.
        game_id: Game identifier string.
        available_actions: Action name strings that can be passed to submit_action.
        width, height: Grid dimensions.
    """

    _data: FrameData
    grid: list[list[int]]
    winning_frame: "Frame | None"
    state: GameState
    levels_completed: int
    win_levels: int
    game_id: str

    __slots__ = ("_data", "grid", "winning_frame", "state", "levels_completed", "win_levels", "game_id")

    def __init__(self, data: FrameData) -> None:
        self._data = data
        self.grid = data.frame[-1]
        self.state = data.state
        self.levels_completed = data.levels_completed
        self.win_levels = data.win_levels
        self.game_id = data.game_id
        if len(data.frame) > 1:
            win: Frame = object.__new__(Frame)
            win._data = data
            win.grid = data.frame[0]
            win.winning_frame = None
            win.state = data.state
            win.levels_completed = data.levels_completed - 1
            win.win_levels = data.win_levels
            win.game_id = data.game_id
            self.winning_frame = win
        else:
            self.winning_frame = None

    @property
    def width(self) -> int:
        return len(self.grid[0]) if self.grid else 0

    @property
    def height(self) -> int:
        return len(self.grid)

    @property
    def available_actions(self) -> list[str]:
        """
        Action names (e.g. 'ACTION1') that can be passed to submit_action.
        """
        actions = [GameAction.from_id(a).name for a in self._data.available_actions]
        if "RESET" not in actions:
            actions.append("RESET")
        return actions

    def render(
        self,
        keys: str = "0123456789abcdef",
        gap: str = " ",
        y_ticks: bool = False,
        x_ticks: bool = False,
        crop: tuple[int, int, int, int] | None = None,
    ) -> str:
        """
        Render the grid as a text string.

        Args:
            keys: 16-char string mapping each int 0-15 to a display character.
            gap: Separator between cells horizontally; default is " " (no gap might reduce legibility).
            y_ticks: Prefix each row with its y coordinate.
            x_ticks: Add column-number header lines.
            crop: (x1, y1, x2, y2) sub-region with exclusive end. None = full grid.
        """
        x1, y1, x2, y2 = crop or (0, 0, self.width, self.height)
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(self.width, x2), min(self.height, y2)

        lines: list[str] = []
        pad = "       " if y_ticks else ""

        if x_ticks:
            lines.append(pad + gap.join(str(c // 10) for c in range(x1, x2)))
            lines.append(pad + gap.join(str(c % 10) for c in range(x1, x2)))
            data_width = len(gap.join("x" for _ in range(x1, x2)))
            lines.append(pad + "-" * data_width)

        for y in range(y1, y2):
            row = gap.join(keys[self.grid[y][x]] for x in range(x1, x2))
            if y_ticks:
                lines.append(f"y={y:>2d} | {row}")
            else:
                lines.append(row)

        return "\n".join(lines)

    def diff(self, other: Self, margin: int = 2) -> list[DiffRegion]:
        """
        Cells that changed between self and other, grouped by contiguous region.

        Changes within *margin* pixels of each other are merged into the same
        DiffRegion.  Each region has a bounding box and a list of individual
        cell changes ``(x, y, old_val, new_val)``.

        Tip: call ``diff()`` first to identify regions, then use
        ``render_diff(other, crop=(r.x0, r.y0, r.x1, r.y1))`` to visualize
        a specific region.
        """
        changes: list[tuple[int, int, int, int]] = []
        for y in range(min(self.height, other.height)):
            self_row, other_row = self.grid[y], other.grid[y]
            for x in range(min(len(self_row), len(other_row))):
                if self_row[x] != other_row[x]:
                    changes.append((x, y, self_row[x], other_row[x]))
        return _cluster_changes(changes, margin=margin)

    def render_diff(
        self,
        other: Self,
        keys: str = "0123456789abcdef",
        gap: str = " ",
        crop: tuple[int, int, int, int] | Literal["auto"] | None = None,
    ) -> str:
        """
        Render a visual diff showing what changed between self and other.

        Args:
            keys: Character map for color values 0-15.
            gap: Separator between cells.
            crop: Region to render.
                - None: show all changes (no crop, full grid bounds).
                - 'auto': auto-crop to the bounding box of all changes.
                - (x1, y1, x2, y2): explicit crop with exclusive end.

        Changed cells show their new value; unchanged cells show as ".".
        Includes a summary header and y/x tick marks.

        Tip: call ``diff()`` first to get DiffRegions, then pass a region's
        bounds as ``crop=(r.x0, r.y0, r.x1, r.y1)`` to zoom into it.
        """
        regions = self.diff(other)
        if not regions:
            return "No changes."

        all_changes: dict[tuple[int, int], int] = {}
        total = 0
        for region in regions:
            for x, y, _, new_val in region.changes:
                all_changes[(x, y)] = new_val
            total += region.count

        if crop == "auto":
            min_x = min(r.x0 for r in regions)
            min_y = min(r.y0 for r in regions)
            max_x = max(r.x1 for r in regions)
            max_y = max(r.y1 for r in regions)
        elif crop is not None:
            min_x, min_y, max_x, max_y = crop
        else:
            min_x, min_y = 0, 0
            max_x, max_y = self.width, self.height

        header = f"{total} changes in {len(regions)} region{'s' if len(regions) != 1 else ''}"
        if len(regions) > 1:
            region_strs = [
                f"  [{r.x0},{r.y0})-[{r.x1},{r.y1}): {r.count} changes" for r in regions
            ]
            header += "\n" + "\n".join(region_strs)

        lines: list[str] = [header]

        pad = "       "
        lines.append(pad + gap.join(str(c // 10) for c in range(min_x, max_x)))
        lines.append(pad + gap.join(str(c % 10) for c in range(min_x, max_x)))
        data_width = len(gap.join("x" for _ in range(min_x, max_x)))
        lines.append(pad + "-" * data_width)

        for y in range(min_y, max_y):
            cells: list[str] = []
            for x in range(min_x, max_x):
                if (x, y) in all_changes:
                    cells.append(keys[all_changes[(x, y)]])
                else:
                    cells.append(".")
            lines.append(f"y={y:>2d} | {gap.join(cells)}")

        return "\n".join(lines)

    def find(self, *colors: int) -> list[tuple[int, int, int]]:
        """
        All pixels matching any of the given color values.

        Returns:
            [(x, y, value), ...] sorted by (y, x).
        """
        target = set(colors)
        return [
            (x, y, val)
            for y, row in enumerate(self.grid)
            for x, val in enumerate(row)
            if val in target
        ]

    def color_counts(self) -> dict[int, int]:
        """
        Count of each color value present in the grid.
        """
        bins = [0] * 16
        for row in self.grid:
            for val in row:
                bins[val] += 1
        return {c: n for c, n in enumerate(bins) if n}

    def bounding_box(self, *colors: int) -> tuple[int, int, int, int] | None:
        """
        Tight bounding box of matching pixels: (x1, y1, x2, y2), exclusive end.

        At least one color must be specified.
        Returns None if no pixels match.
        """
        target = set(colors)
        min_x, max_x = self.width, -1
        min_y, max_y = self.height, -1
        for y, row in enumerate(self.grid):
            for x, val in enumerate(row):
                if val in target:
                    if x < min_x:
                        min_x = x
                    if x > max_x:
                        max_x = x
                    if y < min_y:
                        min_y = y
                    if y > max_y:
                        max_y = y
        if max_x < 0:
            return None
        return (min_x, min_y, max_x + 1, max_y + 1)

    def __repr__(self) -> str:
        actions = ", ".join(self.available_actions)
        return (
            f"Frame(level={self.levels_completed}/{self.win_levels}, "
            f"state={self.state.name}, "
            f"grid={self.width}x{self.height}, "
            f"actions=[{actions}])"
        )
