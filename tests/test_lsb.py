"""Tests for LSB hide/extract roundtrip."""

from pathlib import Path

import pytest
from PIL import Image

from steg_toolkit.lsb import extract_from_image, hide_in_image


def _make_cover(path: Path, w: int = 64, h: int = 64) -> Path:
    img = Image.new("RGB", (w, h))
    pixels = [((x * 7 + y * 11) % 256, (x * 13) % 256, (y * 17) % 256)
              for y in range(h) for x in range(w)]
    img.putdata(pixels)
    img.save(path)
    return path


def test_lsb_roundtrip_short_string(tmp_path: Path) -> None:
    cover = _make_cover(tmp_path / "cover.png")
    stego = tmp_path / "stego.png"
    payload = b"hello world"
    hide_in_image(cover, payload, stego)
    assert extract_from_image(stego) == payload


def test_lsb_roundtrip_binary(tmp_path: Path) -> None:
    cover = _make_cover(tmp_path / "cover.png", 128, 128)
    stego = tmp_path / "stego.png"
    payload = bytes(range(256)) * 10
    hide_in_image(cover, payload, stego)
    assert extract_from_image(stego) == payload


def test_payload_too_big_raises(tmp_path: Path) -> None:
    cover = _make_cover(tmp_path / "cover.png", 16, 16)
    payload = b"X" * 10000
    with pytest.raises(ValueError, match="too large"):
        hide_in_image(cover, payload, tmp_path / "stego.png")
