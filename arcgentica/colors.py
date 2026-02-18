"""
Color constants for ARC-AGI-3 grids.
"""

COLOR_NAMES: tuple[str, ...] = (
    "white",
    "off-white",
    "light gray",
    "gray",
    "off-black",
    "black",
    "magenta",
    "light magenta",
    "red",
    "blue",
    "light blue",
    "yellow",
    "orange",
    "maroon",
    "green",
    "purple",
)

# Hex strings for the frontend / canvas rendering.
PALETTE: tuple[str, ...] = (
    "#FFFFFF",  # 0  White
    "#CCCCCC",  # 1  Off-white
    "#999999",  # 2  Neutral light
    "#666666",  # 3  Neutral
    "#333333",  # 4  Off-black
    "#000000",  # 5  Black
    "#E53AA3",  # 6  Magenta
    "#FF7BCC",  # 7  Magenta light
    "#F93C31",  # 8  Red
    "#1E93FF",  # 9  Blue
    "#88D8F1",  # 10 Blue light
    "#FFDC00",  # 11 Yellow
    "#FF851B",  # 12 Orange
    "#921231",  # 13 Maroon
    "#4FCC30",  # 14 Green
    "#A356D6",  # 15 Purple
)

COLOR_LEGEND: str = ", ".join(f"{i}: {n}" for i, n in enumerate(COLOR_NAMES))
