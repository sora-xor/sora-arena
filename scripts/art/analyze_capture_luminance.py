#!/usr/bin/env python3
"""Exposure and colour statistics of original capture PNGs, for room-readability review.

  python3 scripts/art/analyze_capture_luminance.py <png or folder> ... [--json OUT]

Per frame it reports:

* luma (Rec. 709 luminance, sRGB-encoded 0-1) at the 5th, 50th and 95th
  percentiles;
* the median of the top, middle and bottom thirds of the frame (in a dojo
  view: ceiling, walls, floor), the plane separation a viewer reads;
* the median's exposure in EV, for comparing SM5 with SM6 at one camera;
* clipped pixels (any channel at 254 or more) and crushed ones (luma 0.03 or
  less);
* the warm cast (mean linear red over mean linear blue; 1.0 is neutral);
* Hasler and Süsstrunk's colourfulness.

Frames that share a name under an ``sm5`` and an ``sm6`` capture folder are
also paired by the EV difference of their medians.

The numbers describe the pixels only. They don't judge the image, and
they never replace looking at the originals. Uses Pillow when present, else a
built-in decoder for 8-bit RGB/RGBA PNGs; it needs numpy and only reads.
"""
from __future__ import annotations

import argparse
import json
import math
import struct
import sys
import zlib
from pathlib import Path

import numpy as np


def _unfilter(raw: bytes, width: int, height: int, bpp: int) -> np.ndarray:
    stride = width * bpp
    out = bytearray(stride * height)
    prior = bytearray(stride)
    pos = 0
    for row in range(height):
        kind = raw[pos]
        line = bytearray(raw[pos + 1:pos + 1 + stride])
        pos += 1 + stride
        if kind == 1:
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 255
        elif kind == 2:
            for i in range(stride):
                line[i] = (line[i] + prior[i]) & 255
        elif kind == 3:
            for i in range(stride):
                left = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((left + prior[i]) >> 1)) & 255
        elif kind == 4:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                b = prior[i]
                c = prior[i - bpp] if i >= bpp else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        elif kind != 0:
            raise ValueError(f"PNG filter type {kind}")
        out[row * stride:(row + 1) * stride] = line
        prior = line
    return np.frombuffer(bytes(out), dtype=np.uint8).reshape(height, width, bpp)


def read_png(path: Path) -> np.ndarray:
    """8-bit RGB pixels (height, width, 3)."""
    try:
        from PIL import Image
        with Image.open(path) as im:
            return np.asarray(im.convert("RGB"))
    except ImportError:
        pass
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{path}: not a PNG")
    pos, idat, header = 8, [], None
    while pos < len(data):
        length, kind = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if kind == b"IHDR":
            header = struct.unpack(">IIBBBBB", body)
        elif kind == b"IDAT":
            idat.append(body)
        elif kind == b"IEND":
            break
    width, height, depth, colour, _, _, interlace = header
    if depth != 8 or colour not in (2, 6) or interlace:
        raise ValueError(f"{path}: only 8-bit RGB/RGBA non-interlaced PNGs (got depth {depth}, type {colour})")
    bpp = 3 if colour == 2 else 4
    return _unfilter(zlib.decompress(b"".join(idat)), width, height, bpp)[:, :, :3]


def to_linear(srgb: np.ndarray) -> np.ndarray:
    return np.where(srgb <= 0.04045, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4)


def to_srgb(linear: np.ndarray) -> np.ndarray:
    return np.where(linear <= 0.0031308, linear * 12.92, 1.055 * np.power(np.maximum(linear, 0), 1 / 2.4) - 0.055)


def stats(pixels: np.ndarray) -> dict:
    rgb = pixels.astype(np.float64) / 255.0
    lin = to_linear(rgb)
    y = lin @ np.array([0.2126, 0.7152, 0.0722])
    luma = to_srgb(y)
    h = luma.shape[0]
    thirds = [float(np.median(luma[i * h // 3:(i + 1) * h // 3])) for i in range(3)]
    r, g, b = (pixels[..., i].astype(np.float64) for i in range(3))
    rg, yb = r - g, 0.5 * (r + g) - b
    colourfulness = math.hypot(rg.std(), yb.std()) + 0.3 * math.hypot(rg.mean(), yb.mean())
    median_y = float(np.median(y))
    return {
        "size": [int(pixels.shape[1]), int(pixels.shape[0])],
        "luma_p05": round(float(np.percentile(luma, 5)), 4),
        "luma_p50": round(float(np.median(luma)), 4),
        "luma_p95": round(float(np.percentile(luma, 95)), 4),
        "luma_thirds_top_mid_bottom": [round(v, 4) for v in thirds],
        "median_ev": round(math.log2(max(median_y, 1e-6)), 3),
        "clipped_pct": round(100.0 * float(np.mean(pixels.max(axis=2) >= 254)), 3),
        "crushed_pct": round(100.0 * float(np.mean(luma <= 0.03)), 3),
        "warm_cast_r_over_b": round(float(lin[..., 0].mean() / max(lin[..., 2].mean(), 1e-6)), 3),
        "colourfulness": round(colourfulness, 2),
    }


def frames(paths):
    for p in paths:
        p = Path(p)
        if p.is_dir():
            yield from sorted(q for q in p.rglob("*.png"))
        else:
            yield p


def mode_of(path: Path):
    for part in path.parts:
        low = part.lower()
        if "-sm5-" in low or low.endswith("-sm5"):
            return "sm5"
        if "-sm6-" in low or low.endswith("-sm6"):
            return "sm6"
    return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--json", type=Path, help="also write the results here")
    a = ap.parse_args(argv)
    results = []
    for path in frames(a.paths):
        row = {"file": str(path), "mode": mode_of(path), **stats(read_png(path))}
        results.append(row)
        print(f"{path.name:32s} {row['mode'] or '-':3s} p05/p50/p95 {row['luma_p05']:.3f}/{row['luma_p50']:.3f}/"
              f"{row['luma_p95']:.3f} thirds {row['luma_thirds_top_mid_bottom']} EV {row['median_ev']:+.2f} "
              f"clip {row['clipped_pct']:.2f}% crush {row['crushed_pct']:.2f}% R/B {row['warm_cast_r_over_b']:.2f} "
              f"colour {row['colourfulness']:.1f}", flush=True)
    pairs = []
    by_name = {}
    for row in results:
        if row["mode"]:
            by_name.setdefault(Path(row["file"]).name, {})[row["mode"]] = row
    for name, modes in sorted(by_name.items()):
        if {"sm5", "sm6"} <= set(modes):
            delta = round(modes["sm5"]["median_ev"] - modes["sm6"]["median_ev"], 3)
            pairs.append({"frame": name, "sm5_minus_sm6_ev": delta})
            print(f"pair {name}: SM5 - SM6 median {delta:+.2f} EV")
    if a.json:
        a.json.write_text(json.dumps({"frames": results, "pairs": pairs}, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
