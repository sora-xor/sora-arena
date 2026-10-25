"""How much of a fur-card atlas the engine would dither, at the footprints the first-person views see.

  python3 scripts/art/fur_atlas_coverage.py <atlas albedo .png> [--clip 0.33] [--out result.json]

**The engine's rule** (UE 5.8, a masked material with DitherOpacityMask): a
fragment is drawn when mask - clip + 0.83 x noise - 0.5 > 0, with blue
noise in [0, 1) that changes every frame.
- Sources: BlueNoiseCommon.ush:19-26 GetBlueNoiseDitheredCoverage, reached
  through MaterialTemplate.ush GetDitheredCoverage, with GetMaterialMask =
  mask - clip (:3911).
- So a texel of alpha a is drawn with probability
  P = clamp((a - clip + 0.33) / 0.83, 0, 1). At clip 0.33 that is a / 0.83.
- Every alpha strictly between clip - 0.33 and clip + 0.5 is a per-frame
  coin flip: speckle, unless a temporal history averages it.

**The footprint:** a card's atlas tile spans the card's width and length.
One screen pixel then covers (pixel_mm / width_mm) x TW texels across and
(pixel_mm / length_mm) x TH along.
- The box average of alpha over that footprint stands in for the sampler's
  filtered, anisotropic read.
- It runs over the whole atlas with wrap addressing, as the sampler reads
  past a tile's edge into its neighbours, and the atlas's edges into each
  other.
- It is an approximation: mip boundaries and the hardware's filter shape
  differ.

**Per footprint, over the tile area the card covers at all** (filtered
alpha above 0.02):
- the dithered share (0 < P < 1);
- the solid share (P = 1);
- the mean Bernoulli variance P(1 - P), the speckle's energy;
- the alpha quartiles.

A measurement of the atlas, not of a render: the card's geometry, the
lighting and TSR are not in it.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

LEGACY = 0.83                     # BlueNoiseCommon.ush's LegacyAdjustement: the noise's span
DRAWN_FLOOR = 0.02


def draw_probability(alpha, clip):
    """The engine's expected coverage of a dithered masked fragment of mask ``alpha``.

    Values within 1e-9 of 0 or 1 are snapped there: clip + 0.5 - 0.83 is 0 for clip 0.33 only up to rounding, and
    a texel at the bound is solid (or empty), not dithered."""
    p = np.clip((np.asarray(alpha, np.float64) - clip - 0.5 + LEGACY) / LEGACY, 0.0, 1.0)
    return np.where(p > 1.0 - 1e-9, 1.0, np.where(p < 1e-9, 0.0, p))


def box_mean(a, along, across, wrap=True):
    """The mean of a (H, W) over an along x across box centred on each texel (a summed-area table).

    wrap: the texture's wrap addressing, so the box reads across the edges; otherwise zero beyond them."""
    h, w = a.shape
    ry, rx = max(1, int(round(along))), max(1, int(round(across)))
    if wrap:
        py, px = min(ry, h), min(rx, w)
        a = np.pad(a, ((py, py), (px, px)), mode="wrap")
    else:
        py = px = 0
    s = np.zeros((a.shape[0] + 1, a.shape[1] + 1))
    s[1:, 1:] = np.cumsum(np.cumsum(a, 0), 1)
    hh, ww = a.shape
    y0 = np.clip(np.arange(h) + py - ry // 2, 0, hh)
    y1 = np.clip(np.arange(h) + py - ry // 2 + ry, 0, hh)
    x0 = np.clip(np.arange(w) + px - rx // 2, 0, ww)
    x1 = np.clip(np.arange(w) + px - rx // 2 + rx, 0, ww)
    total = s[y1][:, x1] - s[y0][:, x1] - s[y1][:, x0] + s[y0][:, x0]
    return total / (ry * rx)


def footprint_texels(pixel_mm, card_mm, tile_px):
    """(along, across) texels one pixel covers on a card of card_mm = (width, length), its tile tile_px = (TW, TH)."""
    (width, length), (tw, th) = card_mm, tile_px
    return th * pixel_mm / length, tw * pixel_mm / width


def pixel_mm(distance_mm, fov_h_deg, width_px):
    """The width one pixel covers at distance_mm, for a horizontal FOV over width_px pixels."""
    return 2.0 * distance_mm * math.tan(math.radians(fov_h_deg) / 2.0) / width_px


def tiles(alpha, cols, rows):
    """The atlas's tiles, (rows x cols) of (TH, TW)."""
    h, w = alpha.shape
    th, tw = h // rows, w // cols
    return [alpha[r * th:(r + 1) * th, c * tw:(c + 1) * tw] for r in range(rows) for c in range(cols)]


def coverage(alpha, cols, rows, footprint, clip):
    """The dither statistics of an atlas's alpha (H, W in [0, 1]) at one footprint (along, across texels)."""
    filt = np.concatenate([t.ravel() for t in tiles(box_mean(alpha, *footprint), cols, rows)])
    drawn = filt > DRAWN_FLOOR
    if not drawn.any():
        raise ValueError("no texel of the atlas is covered at this footprint")
    p = draw_probability(filt[drawn], clip)
    a = filt[drawn]
    return {"footprint_texels": {"along": float(footprint[0]), "across": float(footprint[1])},
            "dithered_share": float(((p > 0) & (p < 1)).mean()), "solid_share": float((p >= 1).mean()),
            "speckle_variance": float((p * (1 - p)).mean()), "expected_coverage": float(p.mean()),
            "alpha_quartiles": [float(np.percentile(a, q)) for q in (25, 50, 75)]}


# The first-person views capture v4 used (render_yumi_fp_review.py; the paw inherits mesh_scale 0.75):
# - the eye view: the paw's Grip_L about 60.8 cm from the camera (root's bow.drawn anchor), 70 degrees over 1920 px;
# - the paw close-up: its camera 26.2 cm from that anchor, 32 degrees over 1920 px.
VIEWS = {"eye_view": pixel_mm(608.0, 70.0, 1920), "paw_close_up": pixel_mm(262.0, 32.0, 1920)}
# The cards (nyaakoto_fp_paws.FUR), mid-range, x 0.75: width 1.05 mm; a digit's length 3.3 mm, the metacarpus's 6.25 mm.
CARDS = {"digit": (0.75 * 1.05, 0.75 * 3.3), "dorsal": (0.75 * 1.05, 0.75 * 6.25)}


def measure(alpha, cols, rows, clip=0.33, views=VIEWS, cards=CARDS):
    th, tw = alpha.shape[0] // rows, alpha.shape[1] // cols
    out = {"clip": clip, "tile_px": [tw, th], "views_pixel_mm": dict(views), "cards_mm": {k: list(v) for k, v in cards.items()},
           "base_level": {"partial_share": float(((alpha > DRAWN_FLOOR) & (alpha < clip + 0.5)).sum()
                                                 / max(int((alpha > DRAWN_FLOOR).sum()), 1)),
                          "mean_alpha": float(alpha.mean())}, "at": {}}
    for view, px in views.items():
        for card, mm in cards.items():
            out["at"][f"{view}/{card}"] = coverage(alpha, cols, rows, footprint_texels(px, mm, (tw, th)), clip)
    return out


def main(argv=None) -> int:
    from PIL import Image

    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("albedo", type=Path)
    ap.add_argument("--cols", type=int, default=8)
    ap.add_argument("--rows", type=int, default=2)
    ap.add_argument("--clip", type=float, default=0.33)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args(argv)
    with Image.open(a.albedo) as im:
        if im.mode != "RGBA":
            print(f"FUR_ATLAS_COVERAGE_FAILED: {a.albedo} is {im.mode}, not RGBA", file=sys.stderr)
            return 1
        alpha = np.asarray(im, np.float64)[..., 3] / 255.0
    result = measure(alpha, a.cols, a.rows, a.clip)
    result["atlas"] = str(a.albedo)
    for key, r in result["at"].items():
        print(f"{key}: dithered {r['dithered_share']:.1%}, solid {r['solid_share']:.1%}, "
              f"speckle variance {r['speckle_variance']:.3f}")
    if a.out:
        with open(a.out, "x", encoding="utf-8") as f:
            f.write(json.dumps(result, indent=1) + "\n")
        print("FUR_ATLAS_COVERAGE", a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
