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


def _make_rgba_cover(path: Path, w: int = 32, h: int = 32) -> Path:
    img = Image.new("RGBA", (w, h))
    pixels = [((x * 7) % 256, (y * 5) % 256, (x + y) % 256, 200 + (x % 50))
              for y in range(h) for x in range(w)]
    img.putdata(pixels)
    img.save(path)
    return path


def _pixel_list(path: Path, mode: str) -> list[tuple[int, ...]]:
    with Image.open(path) as src:
        img = src.convert(mode)
    return [img.getpixel((x, y)) for y in range(img.height) for x in range(img.width)]


@pytest.mark.parametrize("bit", [1, 3, 7])
def test_roundtrip_on_higher_bit_planes(tmp_path: Path, bit: int) -> None:
    cover = _make_cover(tmp_path / "cover.png")
    stego = tmp_path / "stego.png"
    payload = b"forgehk{bit_plane_" + str(bit).encode() + b"}"
    hide_in_image(cover, payload, stego, bit=bit)
    assert extract_from_image(stego, bit=bit) == payload


def test_only_the_chosen_bit_changes(tmp_path: Path) -> None:
    cover = _make_cover(tmp_path / "cover.png")
    stego = tmp_path / "stego.png"
    hide_in_image(cover, bytes(range(200)), stego, bit=1)
    mask = 0b10
    for before, after in zip(_pixel_list(cover, "RGB"), _pixel_list(stego, "RGB")):
        for a, b in zip(before, after):
            assert (a ^ b) & ~mask == 0


def test_wrong_bit_plane_does_not_recover_payload(tmp_path: Path) -> None:
    cover = _make_cover(tmp_path / "cover.png")
    stego = tmp_path / "stego.png"
    payload = b"second lsb only"
    hide_in_image(cover, payload, stego, bit=1)
    try:
        recovered = extract_from_image(stego, bit=0)
    except ValueError:
        return
    assert recovered != payload


def test_single_channel_leaves_other_channels_alone(tmp_path: Path) -> None:
    cover = _make_cover(tmp_path / "cover.png")
    stego = tmp_path / "stego.png"
    payload = b"blue only"
    hide_in_image(cover, payload, stego, channels="B")
    assert extract_from_image(stego, channels="b") == payload
    for before, after in zip(_pixel_list(cover, "RGB"), _pixel_list(stego, "RGB")):
        assert before[:2] == after[:2]


def test_channel_order_matters(tmp_path: Path) -> None:
    cover = _make_cover(tmp_path / "cover.png")
    stego = tmp_path / "stego.png"
    payload = b"bgr order"
    hide_in_image(cover, payload, stego, channels="BGR")
    assert extract_from_image(stego, channels="BGR") == payload
    try:
        assert extract_from_image(stego, channels="RGB") != payload
    except ValueError:
        pass


def test_alpha_only_roundtrip_keeps_rgb(tmp_path: Path) -> None:
    cover = _make_rgba_cover(tmp_path / "cover.png")
    stego = tmp_path / "stego.png"
    payload = b"alpha channel secret"
    hide_in_image(cover, payload, stego, channels="A")
    with Image.open(stego) as img:
        assert img.mode == "RGBA"
    assert extract_from_image(stego, channels="A") == payload
    for before, after in zip(_pixel_list(cover, "RGBA"), _pixel_list(stego, "RGBA")):
        assert before[:3] == after[:3]


def test_capacity_scales_with_channel_count(tmp_path: Path) -> None:
    cover = _make_cover(tmp_path / "cover.png", 16, 16)  # 256 pixels
    # One channel holds 256 bits: a 4-byte header plus 28 payload bytes.
    hide_in_image(cover, b"x" * 28, tmp_path / "ok.png", channels="R")
    with pytest.raises(ValueError, match="too large"):
        hide_in_image(cover, b"x" * 29, tmp_path / "too_big.png", channels="R")


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"bit": 8}, "between 0 and 7"),
        ({"bit": -1}, "between 0 and 7"),
        ({"channels": ""}, "at least one"),
        ({"channels": "RGX"}, "unknown channel"),
        ({"channels": "RR"}, "must not repeat"),
    ],
)
def test_invalid_plane_arguments(tmp_path: Path, kwargs: dict, message: str) -> None:
    cover = _make_cover(tmp_path / "cover.png", 8, 8)
    with pytest.raises(ValueError, match=message):
        hide_in_image(cover, b"x", tmp_path / "stego.png", **kwargs)
    with pytest.raises(ValueError, match=message):
        extract_from_image(cover, **kwargs)


def test_cli_hide_and_extract_with_bit_and_channels(tmp_path: Path, capsys) -> None:
    from steg_toolkit.cli import main

    cover = _make_rgba_cover(tmp_path / "cover.png")
    secret = tmp_path / "secret.txt"
    secret.write_bytes(b"forgehk{cli_plane}")
    stego = tmp_path / "stego.png"
    out = tmp_path / "out.txt"

    assert main(["hide", str(cover), str(secret), "-o", str(stego),
                 "--bit", "2", "--channels", "GA"]) == 0
    assert "into bit 2 of GA of cover.png" in capsys.readouterr().out
    assert main(["extract", str(stego), "-o", str(out),
                 "--bit", "2", "--channels", "GA"]) == 0
    assert out.read_bytes() == b"forgehk{cli_plane}"

    assert main(["hide", str(cover), str(secret), "-o", str(stego),
                 "--channels", "RQ"]) == 1
    assert "unknown channel" in capsys.readouterr().err
