"""LSB hide and extract for PNG-like images.

Format: first 32 bits of the embedded stream are a big-endian payload length,
followed by the payload bytes. Bits are written in row-major pixel order and,
within a pixel, in the order of the selected channels. With the defaults
(bit 0, channels "RGB") that is (0,0).R, (0,0).G, (0,0).B, (0,1).R, ...

`bit` picks the bit plane (0 = least significant, 7 = most significant) and
`channels` picks which of R, G, B and A carry data, so the same helpers cover
the 2nd-LSB and alpha-only variants that show up in CTF challenges. The
extractor has to be given the same `bit` and `channels` the payload was
hidden with.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

_VALID_CHANNELS = "RGBA"


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


def _pixels(img: Image.Image) -> list[tuple[int, ...]]:
    """Return the image's pixels as a list of tuples.

    ``Image.getdata`` is deprecated in recent Pillow releases and the
    replacement ``get_flattened_data`` only exists from Pillow 11.3, so use
    whichever this Pillow has.
    """
    reader = getattr(img, "get_flattened_data", None) or img.getdata
    return list(reader())


def _check_plane(bit: int, channels: str) -> tuple[str, list[int]]:
    """Validate `bit` and `channels`; return the image mode and channel indices."""
    if not isinstance(bit, int) or not 0 <= bit <= 7:
        raise ValueError(f"bit must be between 0 and 7, got {bit!r}")
    chans = channels.upper()
    if not chans:
        raise ValueError("channels must name at least one of R, G, B, A")
    bad = sorted(set(chans) - set(_VALID_CHANNELS))
    if bad:
        raise ValueError(f"unknown channel(s) {''.join(bad)!r}; use R, G, B or A")
    if len(set(chans)) != len(chans):
        raise ValueError(f"channels must not repeat, got {channels!r}")
    mode = "RGBA" if "A" in chans else "RGB"
    return mode, [_VALID_CHANNELS.index(c) for c in chans]


def hide_in_image(
    cover_path: str | Path,
    payload: bytes,
    out_path: str | Path,
    *,
    bit: int = 0,
    channels: str = "RGB",
) -> int:
    """Embed `payload` into bit plane `bit` of `channels`. Returns bytes embedded.

    Selecting the alpha channel writes an RGBA image; the output format has to
    keep alpha losslessly (PNG does).
    """
    mode, idx = _check_plane(bit, channels)
    cover = Image.open(cover_path).convert(mode)
    pixels = _pixels(cover)
    capacity_bits = len(pixels) * len(idx)
    header = len(payload).to_bytes(4, "big")
    bits = _bits_of(header + payload)
    if len(bits) > capacity_bits:
        raise ValueError(
            f"payload too large: need {len(bits)} bits, image holds {capacity_bits}"
        )

    clear = ~(1 << bit) & 0xFF
    new_pixels: list[tuple[int, ...]] = []
    bi = 0
    for px in pixels:
        if bi < len(bits):
            values = list(px)
            for c in idx:
                if bi >= len(bits):
                    break
                values[c] = (values[c] & clear) | (bits[bi] << bit)
                bi += 1
            px = tuple(values)
        new_pixels.append(px)
    out = Image.new(mode, cover.size)
    out.putdata(new_pixels)
    out.save(out_path)
    return len(payload)


def extract_from_image(
    stego_path: str | Path,
    *,
    bit: int = 0,
    channels: str = "RGB",
) -> bytes:
    """Recover the payload from bit plane `bit` of `channels`.

    Reads the 4-byte length header first.
    """
    mode, idx = _check_plane(bit, channels)
    img = Image.open(stego_path).convert(mode)
    bits: list[int] = []
    for px in _pixels(img):
        for c in idx:
            bits.append((px[c] >> bit) & 1)

    header_bits = bits[:32]
    if len(header_bits) < 32:
        raise ValueError("image too small to contain a header")
    length = int.from_bytes(_bits_to_bytes(header_bits), "big")
    if length < 0 or length * 8 + 32 > len(bits):
        raise ValueError("invalid length header (likely no payload present)")

    payload_bits = bits[32:32 + length * 8]
    return _bits_to_bytes(payload_bits)
