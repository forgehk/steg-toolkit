"""LSB hide and extract for PNG-like images.

Format: first 32 bits of the LSB stream are a big-endian payload length,
followed by the payload bytes. Channels are written in row-major order:
(0,0).R, (0,0).G, (0,0).B, (0,1).R, ...
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image


def _bits_of(data: bytes) -> list[int]:
    out: list[int] = []
    for byte in data:
        for shift in range(7, -1, -1):
            out.append((byte >> shift) & 1)
    return out


def _bits_to_bytes(bits: list[int]) -> bytes:
    out = bytearray()
    for i in range(0, len(bits), 8):
        byte = 0
        for b in bits[i:i + 8]:
            byte = (byte << 1) | (b & 1)
        out.append(byte)
    return bytes(out)


def hide_in_image(cover_path: str | Path, payload: bytes, out_path: str | Path) -> int:
    """Embed `payload` into the cover image's LSB plane. Returns bytes embedded."""
    cover = Image.open(cover_path).convert("RGB")
    pixels = list(cover.getdata())  # list of (r, g, b)
    capacity_bits = len(pixels) * 3
    header = len(payload).to_bytes(4, "big")
    bits = _bits_of(header + payload)
    if len(bits) > capacity_bits:
        raise ValueError(
            f"payload too large: need {len(bits)} bits, image holds {capacity_bits}"
        )

    new_pixels: list[tuple[int, int, int]] = []
    bi = 0
    for r, g, b in pixels:
        if bi < len(bits): r = (r & ~1) | bits[bi]; bi += 1
        if bi < len(bits): g = (g & ~1) | bits[bi]; bi += 1
        if bi < len(bits): b = (b & ~1) | bits[bi]; bi += 1
        new_pixels.append((r, g, b))
    out = Image.new("RGB", cover.size)
    out.putdata(new_pixels)
    out.save(out_path)
    return len(payload)


def extract_from_image(stego_path: str | Path) -> bytes:
    """Recover the payload from a stego image. Reads the 4-byte length header first."""
    img = Image.open(stego_path).convert("RGB")
    pixels = list(img.getdata())
    bits: list[int] = []
    for r, g, b in pixels:
        bits.extend([r & 1, g & 1, b & 1])

    header_bits = bits[:32]
    if len(header_bits) < 32:
        raise ValueError("image too small to contain a header")
    length = int.from_bytes(_bits_to_bytes(header_bits), "big")
    if length < 0 or length * 8 + 32 > len(bits):
        raise ValueError("invalid length header (likely no payload present)")

    payload_bits = bits[32:32 + length * 8]
    return _bits_to_bytes(payload_bits)
