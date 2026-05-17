"""steg-toolkit CLI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import analysis, lsb


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="steg", description="Image steganography helpers.")
    sub = p.add_subparsers(dest="cmd", required=True)

    h = sub.add_parser("hide", help="Embed a payload in image LSB.")
    h.add_argument("cover", type=Path); h.add_argument("payload", type=Path)
    h.add_argument("-o", "--out", required=True, type=Path)

    e = sub.add_parser("extract", help="Recover LSB payload.")
    e.add_argument("stego", type=Path); e.add_argument("-o", "--out", type=Path, default=None)

    s = sub.add_parser("strings", help="ASCII recovery from raw bytes.")
    s.add_argument("image", type=Path); s.add_argument("--min", type=int, default=4)

    en = sub.add_parser("entropy", help="Per-channel Shannon entropy.")
    en.add_argument("image", type=Path)

    hm = sub.add_parser("heatmap", help="Render LSB plane as a heatmap.")
    hm.add_argument("image", type=Path); hm.add_argument("-o", "--out", required=True, type=Path)

    args = p.parse_args(argv)
    try:
        if args.cmd == "hide":
            n = lsb.hide_in_image(args.cover, args.payload.read_bytes(), args.out)
            print(f"embedded {n} bytes into LSB of {args.cover.name} -> {args.out}")
        elif args.cmd == "extract":
            data = lsb.extract_from_image(args.stego)
            if args.out:
                args.out.write_bytes(data); print(f"wrote {len(data)} bytes -> {args.out}")
            else:
                sys.stdout.buffer.write(data)
        elif args.cmd == "strings":
            for line in analysis.extract_strings(args.image, args.min): print(line)
        elif args.cmd == "entropy":
            for ch, val in analysis.shannon_entropy_per_channel(args.image).items():
                bar = "█" * int(val * 4)
                print(f"  {ch}: {val:5.3f}  {bar}")
        elif args.cmd == "heatmap":
            analysis.lsb_heatmap(args.image, args.out); print(f"wrote LSB plane visualization to {args.out}")
    except (ValueError, FileNotFoundError) as e:
        print(f"error: {e}", file=sys.stderr); return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
