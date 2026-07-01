#!/usr/bin/env python3
"""Generate a 512x512 PNG app icon for electron-builder."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "icons" / "icon.png"


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    size = 512
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Brand gradient approximation (indigo → violet), inspired by frontend/logo.svg
    for y in range(size):
        t = y / (size - 1)
        r = int(99 + (139 - 99) * t)
        g = int(102 + (92 - 102) * t)
        b = int(241 + (246 - 241) * t)
        draw.line([(0, y), (size, y)], fill=(r, g, b, 255))

    margin = 72
    draw.rounded_rectangle(
        (margin, margin, size - margin, size - margin),
        radius=48,
        fill=(255, 255, 255, 235),
    )
    draw.rounded_rectangle(
        (margin + 36, margin + 36, size - margin - 36, size - margin - 36),
        radius=24,
        outline=(99, 102, 241, 255),
        width=8,
    )

    img.save(OUT, format="PNG")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
