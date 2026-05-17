# steg-toolkit

> Image-steganography helpers for CTFs and security challenges. LSB hide/extract, `strings`-like text recovery, and entropy / heatmap analysis — pure Python, Pillow only.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg)]() [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## What it does

| Command | What it does |
|---|---|
| `steg hide <cover.png> <payload.txt> -o out.png` | Embeds `payload.txt` into the lowest-order bit of the cover image. The result is visually identical. |
| `steg extract <stego.png> -o recovered.txt` | Pulls the LSB payload back out, validates a 4-byte length header. |
| `steg strings <image>` | `strings(1)`-like ASCII recovery from raw image bytes. Catches the "they dropped a flag as raw bytes" pattern. |
| `steg entropy <image>` | Per-channel Shannon entropy. Sudden jumps from natural-image ~5 bits to encrypted-payload ~7.5 bits is a quick sniff test. |
| `steg heatmap <image> -o lsb.png` | Visualize the LSB plane. Hidden data shows up as obvious patterns instead of natural-image noise. |

---

## Quick example

```bash
$ echo "this is the flag: forgehk{lsb_steg_demo}" > secret.txt
$ steg hide cat.png secret.txt -o cat_with_secret.png
embedded 40 bytes into LSB of cat.png -> cat_with_secret.png

$ steg extract cat_with_secret.png
this is the flag: forgehk{lsb_steg_demo}

$ steg heatmap cat_with_secret.png -o lsb.png
wrote LSB plane visualization to lsb.png
```

Pairs with [`ctf-toolkit`](https://github.com/forgehk/ctf-toolkit) for a complete CTF-warmup setup — encoders, ciphers, hashes, plus steg.

---

## How LSB embedding works

Most images store each pixel channel as 8 bits. Flipping the **least-significant bit** changes the channel value by at most 1 — a difference the eye can't see. That gives 1 bit of payload per channel; for a 1024×1024 RGB image, that's ~384 KB of hidden capacity, more than enough for any flag, key, or shell-payload sized message.

```
cover pixel:    R=0b10110110  G=0b00100111  B=0b11001101
payload bit:        ^=1            ^=0           ^=1
stego pixel:    R=0b10110111  G=0b00100110  B=0b11001101
```

We prepend a 4-byte big-endian length so the extractor knows exactly how many bits to read.

---

## Install

```bash
pip install steg-toolkit
```

Requires Python 3.11+ and Pillow. No other dependencies.

---

## Roadmap

- [x] LSB hide / extract for PNG
- [x] `strings`-style ASCII recovery
- [x] Per-channel Shannon entropy
- [x] LSB plane heatmap visualization
- [ ] Custom bit-plane targeting (2nd LSB, alpha-channel-only, etc.)
- [ ] DCT-domain embedding (JPEG-resistant)
- [ ] Audio steg (WAV LSB)
- [ ] Auto-classifier: "does this image probably contain hidden data?"

---

## License

[MIT](LICENSE)

---

*Built by [@forgehk](https://github.com/forgehk) — [DarkForge AI](https://darkforgeai.com)*
