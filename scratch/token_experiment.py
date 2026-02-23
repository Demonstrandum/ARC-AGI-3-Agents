"""Quick experiment: how many input tokens does a low-detail image cost on claude-opus-4-6?"""

import argparse
import base64
import io
from collections import Counter

import anthropic
from PIL import Image, ImageDraw

COLOR_NAMES = {
    (0, 0, 0): "black",
    (0, 116, 217): "blue",
    (255, 65, 54): "red",
    (46, 204, 64): "green",
    (255, 220, 0): "yellow",
    (170, 170, 170): "gray",
    (240, 18, 190): "pink",
    (255, 133, 27): "orange",
    (127, 219, 255): "light blue",
    (135, 12, 37): "maroon",
    (200, 200, 200): "gray",
}


def dominant_color(png_bytes: bytes) -> str:
    img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    pixels = list(img.getdata())
    counts = Counter(pixels)
    top_color, top_count = counts.most_common(1)[0]
    total = len(pixels)
    if top_count / total < 0.15:
        return "none (all equal)"
    return COLOR_NAMES.get(top_color, f"rgb{top_color}")


def make_solid_image(w: int, h: int) -> bytes:
    img = Image.new("RGB", (w, h), color=(200, 200, 200))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


PALETTE = [
    (0, 0, 0), (0, 116, 217), (255, 65, 54), (46, 204, 64),
    (255, 220, 0), (170, 170, 170), (240, 18, 190), (255, 133, 27),
    (127, 219, 255), (135, 12, 37),
]

def make_arc_style_grid(rows: int, cols: int, cell_px: int = 20,
                        dominant_idx: int = 3, dominant_frac: float = 0.6) -> bytes:
    """Grid where ~dominant_frac of cells are one color, rest are random others."""
    import random
    random.seed(42)
    n_cells = rows * cols
    n_dominant = int(n_cells * dominant_frac)
    others = [i for i in range(len(PALETTE)) if i != dominant_idx]
    colors = [PALETTE[dominant_idx]] * n_dominant + [
        PALETTE[random.choice(others)] for _ in range(n_cells - n_dominant)
    ]
    random.shuffle(colors)

    w, h = cols * cell_px, rows * cell_px
    img = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)
    for r in range(rows):
        for c in range(cols):
            color = colors[r * cols + c]
            x0, y0 = c * cell_px, r * cell_px
            draw.rectangle([x0, y0, x0 + cell_px - 1, y0 + cell_px - 1], fill=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


TESTS = [
    ("solid gray 100x100",              lambda: make_solid_image(100, 100)),
    ("solid gray 200x200",              lambda: make_solid_image(200, 200)),
    ("solid gray 500x500",              lambda: make_solid_image(500, 500)),
    ("ARC 5x5 60% green (100x100px)",   lambda: make_arc_style_grid(5, 5, dominant_idx=3, dominant_frac=0.6)),
    ("ARC 10x10 60% green (200x200px)", lambda: make_arc_style_grid(10, 10, dominant_idx=3, dominant_frac=0.6)),
    ("ARC 10x10 60% red (200x200px)",   lambda: make_arc_style_grid(10, 10, dominant_idx=2, dominant_frac=0.6)),
    ("ARC 30x30 60% blue (600x600px)",  lambda: make_arc_style_grid(30, 30, dominant_idx=1, dominant_frac=0.6)),
    ("ARC 30x30 60% blue (300x300px)",  lambda: make_arc_style_grid(30, 30, cell_px=10, dominant_idx=1, dominant_frac=0.6)),
    ("ARC 30x30 40% yellow (600x600px)",lambda: make_arc_style_grid(30, 30, dominant_idx=4, dominant_frac=0.4)),
]


def measure_tokens(client: anthropic.Anthropic, label: str, png_bytes: bytes) -> None:
    b64 = base64.standard_b64encode(png_bytes).decode("ascii")
    img = Image.open(io.BytesIO(png_bytes))
    kb = len(png_bytes) / 1024
    expected = dominant_color(png_bytes)

    resp = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=16,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": "Reply with one word: what color is dominant?",
                    },
                ],
            }
        ],
    )
    usage = resp.usage
    answer = resp.content[0].text.strip().lower().strip("*")
    correct = expected in answer or answer in expected
    mark = "Y" if correct else ("~" if "none" in expected else "N")
    size = f"{img.size[0]}x{img.size[1]}"
    print(f"  {label:<42s} {size:>9s} {kb:>7.1f} KB {usage.input_tokens:>6d} {usage.output_tokens:>4d}   {answer:<14s} {expected:<20s} {mark}")

ROW_FMT = f"  {'Test':<42s} {'Size':>9s} {'File':>7s}    {'In':>4s}  {'Out':>3s}   {'Model said':<14s} {'Actual dominant':<20s} Ok?"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", required=True)
    args = parser.parse_args()

    client = anthropic.Anthropic(api_key=args.api_key)

    print(ROW_FMT)
    print("-" * len(ROW_FMT))
    for label, gen_fn in TESTS:
        png_bytes = gen_fn()
        measure_tokens(client, label, png_bytes)


if __name__ == "__main__":
    main()
