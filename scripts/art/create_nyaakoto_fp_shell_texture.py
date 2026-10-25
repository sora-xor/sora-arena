"""Author the strand texture for Nyaakoto's first-person shell fur: original, seeded, no external images.

Run with the project's pinned Python (numpy, Pillow):
  python scripts/art/create_nyaakoto_fp_shell_texture.py [--out <dir>]

Writes to Content/SourceArt/Characters/NyaakotoFirstPersonPaws/FurShells/ (or
--out) T_NyaakotoFP_FurShells_Strands.png and a manifest.json with its
SHA-256 and coverage per channel.

**Why shells.** Fur v4 and v5 were masked cards on a thin sheet. Thin alpha
dithered into speckle (v3); opaque cores tiled into flat flakes over gaps
(v4, v5; root's reviews of captures v5 and v6). Shell fur stacks translucent
offset layers of the skin instead (nyaakoto_fp_paws.fur_shells). Each layer
draws only the cross-sections of the strands that reach its height, so:
- there are no card outlines;
- there is no dither (the shells' material is translucent);
- every gap is the coat's deeper layers, not skin.

**The texture.** It is tileable, 512 x 512, and spans TILE_MM of skin.
- **The strands:** blue-noise centres (dart throwing, wrapped) about
  SPACING_MM apart. Each has its own length, a share of the coat's height
  (LENGTH), and tapers as r(h) = R0 x (1 - h / length)^TAPER in spacings,
  with an AA-wide soft edge.
- **The channels:** R, G, B and A hold the strands' coverage at four
  heights, HEIGHTS of the coat's. The material blends them by each shell's
  height (its vertex colour's alpha).
- **Coverage, not distance,** is stored so that mips average it correctly.
  A shell seen from far away draws its strands' mean coverage, not a
  thresholded edge.
Linear values, no sRGB.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Characters/NyaakotoFirstPersonPaws/FurShells"
NAME = "T_NyaakotoFP_FurShells_Strands.png"
SEED = 20261025
SIZE = 512
TILE_MM = 4.0                         # skin a texture tile spans (nyaakoto_fp_paws.SHELLS uv_tile_m)
SPACING_MM = 0.18                     # strand centres' mean spacing
MIN_SPACING = 0.8                     # dart throwing's least distance, in spacings
R0 = 0.58                             # a strand's base radius, in spacings
TAPER = 0.6                           # its radius closes as (1 - h / length)^TAPER
LENGTH = (0.45, 1.0)                  # a strand's length, as a share of the coat's height
HEIGHTS = (0.15, 0.40, 0.65, 0.90)    # the four channels' heights, as shares of the coat's
AA = 0.06                             # the soft edge, in spacings


def strands(rng):
    """Blue-noise strand centres in the unit tile (wrapped), and each strand's length."""
    s = SPACING_MM / TILE_MM
    target = int(round(1.0 / (s * s)))
    least = MIN_SPACING * s
    pts = []
    tries = 0
    while len(pts) < target and tries < 200 * target:
        tries += 1
        p = rng.random(2)
        if pts:
            d = np.abs(np.array(pts) - p)
            d = np.minimum(d, 1.0 - d)                       # wrapped
            if (np.hypot(d[:, 0], d[:, 1]) < least).any():
                continue
        pts.append(p)
    pts = np.array(pts)
    return pts, rng.uniform(*LENGTH, len(pts))


def coverage(pts, lengths):
    """(SIZE, SIZE, 4): each channel the union of the strands' tapered discs at its height."""
    s = SPACING_MM / TILE_MM
    out = np.zeros((SIZE, SIZE, len(HEIGHTS)))
    reach = int(math.ceil((R0 + AA) * s * SIZE)) + 1
    off = np.arange(-reach, reach + 1)
    for (u, v), length in zip(pts, lengths):
        cx, cy = u * SIZE, v * SIZE
        xs = (np.floor(cx).astype(int) + off) % SIZE
        ys = (np.floor(cy).astype(int) + off) % SIZE
        X, Y = np.meshgrid(np.floor(cx) + off + 0.5, np.floor(cy) + off + 0.5)
        d = np.hypot(X - cx, Y - cy) / (s * SIZE)               # in spacings
        for c, h in enumerate(HEIGHTS):
            if h >= length:
                continue
            r = R0 * (1.0 - h / length) ** TAPER
            cov = np.clip((r + 0.5 * AA - d) / AA, 0.0, 1.0)
            block = out[np.ix_(ys, xs, [c])][..., 0]
            out[np.ix_(ys, xs, [c])] = np.maximum(block, cov)[..., None]
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, default=OUT)
    out = ap.parse_args(argv).out
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    pts, lengths = strands(rng)
    cov = coverage(pts, lengths)
    path = out / NAME
    Image.fromarray(np.clip(np.rint(cov * 255), 0, 255).astype(np.uint8), "RGBA").save(path, optimize=True)
    with Image.open(path) as im:
        written = np.asarray(im, np.float64) / 255.0
    record = {"schema_version": 1, "generator": "scripts/art/create_nyaakoto_fp_shell_texture.py", "seed": SEED,
              "texture": {"file": NAME, "size": [SIZE, SIZE], "mode": "RGBA", "colour_space": "linear",
                          "sha256": hashlib.sha256(path.read_bytes()).hexdigest()},
              "tile_mm": TILE_MM, "spacing_mm": SPACING_MM, "strands": int(len(pts)), "r0": R0, "taper": TAPER,
              "length": list(LENGTH), "heights": list(HEIGHTS), "aa": AA,
              "mean_coverage": {f"{'RGBA'[c]} (h {h})": round(float(written[..., c].mean()), 4)
                                for c, h in enumerate(HEIGHTS)},
              "tileable": "wrapped: strand distances and the discs wrap at the tile's edges",
              "provenance": "original and procedural: every strand placed by this script from its seed; no external "
                            "image, scan or third-party texture"}
    (out / "manifest.json").write_text(json.dumps(record, indent=1) + "\n")
    print("SHELL_TEXTURE_READY", record["texture"]["sha256"][:12], record["strands"], "strands",
          json.dumps(record["mean_coverage"]))


if __name__ == "__main__":
    main()
