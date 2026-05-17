"""Analysis helpers: entropy, strings recovery, LSB-plane heatmap."""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image


def shannon_entropy_per_channel(image_path: str | Path) -> dict[str, float]:
    """Return Shannon entropy (bits/byte) per channel.

    Sudden spike in any channel vs typical natural-image values (~5 bits)
    is a quick "this might contain hidden data" sniff test.
    """
    img = Image.open(image_path).convert("RGB")
    pixels = list(img.getdata())
    by_channel: dict[str, list[int]] = {"R": [], "G": [], "B": []}
    for r, g, b in pixels:
        by_channel["R"].append(r)
        by_channel["G"].append(g)
        by_channel["B"].append(b)
    return {c: _entropy(v) for c, v in by_channel.items()}


def _entropy(values: list[int]) -> float:
    n = len(values)
    if n == 0:
        return 0.0
    counts: dict[int, int] = {}
    for v in values:
        counts[v] = counts.get(v, 0) + 1
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def extract_strings(image_path: str | Path, min_len: int = 4) -> list[str]:
    """`strings(1)`-like ASCII recovery from raw image bytes."""
    data = Path(image_path).read_bytes()
    out: list[str] = []
    cur: list[int] = []
    for b in data:
        if 0x20 <= b <= 0x7e:  # printable ASCII
            cur.append(b)
        else:
            if len(cur) >= min_len:
                out.append(bytes(cur).decode("ascii", errors="replace"))
            cur = []
    if len(cur) >= min_len:
        out.append(bytes(cur).decode("ascii", errors="replace"))
    return out


def lsb_heatmap(image_path: str | Path, out_path: str | Path) -> None:
    """Visualize the LSB plane as black/white. Hidden data shows obvious patterns."""
    img = Image.open(image_path).convert("RGB")
    pixels = list(img.getdata())
    heatmap_pixels: list[tuple[int, int, int]] = []
    for r, g, b in pixels:
        # Average the LSBs of all three channels; scale to full-byte range.
        lsb_sum = (r & 1) + (g & 1) + (b & 1)
        v = (lsb_sum * 255) // 3
        heatmap_pixels.append((v, v, v))
    out = Image.new("RGB", img.size)
    out.putdata(heatmap_pixels)
    out.save(out_path)
