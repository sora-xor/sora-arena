#!/usr/bin/env python3
"""Display-output statistics of original capture PNGs, for room-readability review.

  python3 scripts/art/analyze_capture_luminance.py [LABEL=]<png or folder> ... [--rois ROIS.json] [--json OUT]

These are statistics of the **SDR output image**, after tone mapping,
saturation and bloom. They are not camera exposure (EV100), not
pre-tonemap scene luminance, and not what the engine's histogram meters
(a trimmed distribution with its own weights). Per frame:

* **Display luma:** Rec. 709 luminance of the inverse-sRGB pixels,
  re-encoded to sRGB 0-1, at the 5th, 50th and 95th percentiles.
* **Top, middle and bottom thirds:** the median of each pixel band. These are
  bands, not surfaces; per-camera regions of interest (``--rois``) are what
  measure a wall, a floor or a lamp pool.
* **Median display stops:** log2 of the median linear display luminance. It
  is a relative output-brightness stop, so subtract two frames' values to
  compare them.
* **Near-saturated pixels:** any channel at 254 or more. This is an output
  proxy, not proof that detail is lost in every channel. Crushed pixels are
  luma 0.03 or less.
* **R/B:** mean linear red over mean linear blue. It is weighted by whatever
  material and highlights the view contains, so it is not a calibrated white
  balance.
* **Colourfulness:** Hasler and Süsstrunk's.

**Pairing.** Each frame belongs to a run and a source group:

* the run is the capture folder (``<timestamp>-sm5-<pid>``, ``...-sm6-...``,
  or a bare ``sm5``/``sm6`` folder);
* the source group is an explicit ``LABEL=`` on the argument, else the
  run's ``source-commit.txt``.

An SM5 and an SM6 frame pair only with the same source group and file name.
If a source group holds two frames of one name in one mode, they are
reported as ambiguous and never paired; nothing is overwritten. Every row
and pair carries its paths, SHA-256 and run.

``ROIS.json`` maps a frame file name to named rectangles in 0-1 frame
coordinates, ``{"Dojo_Kamiza.png": {"lamp_left": [x0, y0, x1, y1], ...}}``
with y down. Each one reports its median display luma and display stops.

The numbers describe pixels only. They don't judge an image, and they never
replace looking at the originals. Uses Pillow when present, else a built-in
decoder for 8-bit RGB/RGBA PNGs; it needs numpy and only reads.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import struct
import sys
import zlib
from pathlib import Path

import numpy as np

RUN = re.compile(r"(?:^|-)(sm[56])(?:-|$)")


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


def decode_png(data: bytes, label: str = "PNG") -> np.ndarray:
    """8-bit RGB pixels (height, width, 3) from an 8-bit RGB/RGBA non-interlaced PNG."""
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{label}: not a PNG")
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
        raise ValueError(f"{label}: only 8-bit RGB/RGBA non-interlaced PNGs (got depth {depth}, type {colour})")
    bpp = 3 if colour == 2 else 4
    return _unfilter(zlib.decompress(b"".join(idat)), width, height, bpp)[:, :, :3]


def read_png(path: Path) -> np.ndarray:
    try:
        from PIL import Image
    except ImportError:
        return decode_png(path.read_bytes(), str(path))
    with Image.open(path) as im:
        return np.asarray(im.convert("RGB"))


def to_linear(srgb: np.ndarray) -> np.ndarray:
    return np.where(srgb <= 0.04045, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4)


def to_srgb(linear: np.ndarray) -> np.ndarray:
    return np.where(linear <= 0.0031308, linear * 12.92, 1.055 * np.power(np.maximum(linear, 0), 1 / 2.4) - 0.055)


def display_luminance(pixels: np.ndarray) -> np.ndarray:
    return to_linear(pixels.astype(np.float64) / 255.0) @ np.array([0.2126, 0.7152, 0.0722])


def stops(linear: float) -> float:
    return round(math.log2(max(linear, 1e-6)), 3)


def stats(pixels: np.ndarray, rois: dict | None = None) -> dict:
    lin = to_linear(pixels.astype(np.float64) / 255.0)
    y = lin @ np.array([0.2126, 0.7152, 0.0722])
    luma = to_srgb(y)
    h, w = luma.shape
    thirds = [float(np.median(luma[i * h // 3:(i + 1) * h // 3])) for i in range(3)]
    r, g, b = (pixels[..., i].astype(np.float64) for i in range(3))
    rg, yb = r - g, 0.5 * (r + g) - b
    colourfulness = math.hypot(rg.std(), yb.std()) + 0.3 * math.hypot(rg.mean(), yb.mean())
    out = {
        "size": [int(w), int(h)],
        "luma_p05": round(float(np.percentile(luma, 5)), 4),
        "luma_p50": round(float(np.median(luma)), 4),
        "luma_p95": round(float(np.percentile(luma, 95)), 4),
        "luma_thirds_top_middle_bottom": [round(v, 4) for v in thirds],
        "median_display_stops": stops(float(np.median(y))),
        "near_saturated_pct": round(100.0 * float(np.mean(pixels.max(axis=2) >= 254)), 3),
        "crushed_pct": round(100.0 * float(np.mean(luma <= 0.03)), 3),
        "r_over_b_output_proxy": round(float(lin[..., 0].mean() / max(lin[..., 2].mean(), 1e-6)), 3),
        "colourfulness": round(colourfulness, 2),
    }
    if rois:
        out["rois"] = {}
        for name, (x0, y0, x1, y1) in rois.items():
            if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
                raise ValueError(f"ROI {name}: {x0, y0, x1, y1} is not inside the 0-1 frame")
            region = y[int(round(y0 * h)):max(int(round(y1 * h)), int(round(y0 * h)) + 1),
                       int(round(x0 * w)):max(int(round(x1 * w)), int(round(x0 * w)) + 1)]
            med = float(np.median(region))
            out["rois"][name] = {"rect": [x0, y0, x1, y1], "luma_p50": round(float(to_srgb(np.array(med))), 4),
                                 "median_display_stops": stops(med)}
    return out


def run_of(path: Path):
    """(run folder, mode): the nearest enclosing folder named for a shader mode."""
    for folder in [path.parent, *path.parent.parents]:
        m = RUN.search(folder.name.lower())
        if m:
            return folder, m.group(1)
    return None, None


def source_of(run: Path | None):
    if run is None:
        return None
    marker = run / "source-commit.txt"
    return marker.read_text().strip() if marker.is_file() else None


def frames(args):
    """(explicit label or None, png path) for every argument."""
    for arg in args:
        label, _, rest = arg.partition("=") if "=" in arg and not Path(arg).exists() else (None, None, arg)
        p = Path(rest)
        if p.is_dir():
            for q in sorted(p.rglob("*.png")):
                yield label, q
        else:
            yield label, p


def pair(rows):
    """SM5/SM6 pairs within a source group, and the ambiguous groups that cannot pair."""
    groups, ambiguous, pairs = {}, [], []
    for row in rows:
        if row["mode"] and row["source_group"]:
            groups.setdefault((row["source_group"], Path(row["file"]).name), {}).setdefault(row["mode"], []).append(row)
    for (group, name), modes in sorted(groups.items()):
        if any(len(v) > 1 for v in modes.values()):
            ambiguous.append({"source_group": group, "frame": name,
                              "files": sorted(r["file"] for v in modes.values() for r in v)})
            continue
        if {"sm5", "sm6"} <= set(modes):
            a, b = modes["sm5"][0], modes["sm6"][0]
            pairs.append({"source_group": group, "frame": name,
                          "sm5": {"file": a["file"], "sha256": a["sha256"], "run": a["run"]},
                          "sm6": {"file": b["file"], "sha256": b["sha256"], "run": b["run"]},
                          "sm5_minus_sm6_display_stops": round(a["median_display_stops"] - b["median_display_stops"], 3)})
    return pairs, ambiguous


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("paths", nargs="+", help="PNG files or folders, optionally LABEL=path to name the source group")
    ap.add_argument("--rois", type=Path, help="JSON of per-frame named rectangles (0-1, y down)")
    ap.add_argument("--json", type=Path, help="also write the results here")
    a = ap.parse_args(argv)
    rois = json.loads(a.rois.read_text()) if a.rois else {}
    rows = []
    for label, path in frames(a.paths):
        run, mode = run_of(path)
        data = path.read_bytes()
        row = {"file": str(path), "sha256": hashlib.sha256(data).hexdigest(),
               "run": run.name if run else None, "mode": mode,
               "source_group": label or source_of(run),
               **stats(read_png(path), rois.get(path.name))}
        rows.append(row)
        print(f"{path.name:28s} {row['mode'] or '-':3s} {str(row['source_group'])[:12]:12s} "
              f"luma p05/p50/p95 {row['luma_p05']:.3f}/{row['luma_p50']:.3f}/{row['luma_p95']:.3f} "
              f"thirds {row['luma_thirds_top_middle_bottom']} stops {row['median_display_stops']:+.2f} "
              f"sat {row['near_saturated_pct']:.2f}% crush {row['crushed_pct']:.2f}% "
              f"R/B {row['r_over_b_output_proxy']:.2f}", flush=True)
    pairs, ambiguous = pair(rows)
    for p in pairs:
        print(f"pair {p['source_group'][:12]} {p['frame']}: SM5 - SM6 median {p['sm5_minus_sm6_display_stops']:+.2f} "
              f"display stops ({p['sm5']['run']} / {p['sm6']['run']})")
    for amb in ambiguous:
        print(f"AMBIGUOUS {amb['source_group'][:12]} {amb['frame']}: {len(amb['files'])} frames in one mode; "
              "not paired (name the source groups with LABEL=path)", file=sys.stderr)
    if a.json:
        a.json.write_text(json.dumps({"frames": rows, "pairs": pairs, "ambiguous": ambiguous}, indent=1) + "\n")
    return 2 if ambiguous else 0


if __name__ == "__main__":
    sys.exit(main())
