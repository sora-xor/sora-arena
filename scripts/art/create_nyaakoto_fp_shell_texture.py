"""Author the strand textures for Nyaakoto's first-person shell fur: original, seeded, no external images.

Run with the project's pinned Python (numpy, Pillow):
  python scripts/art/create_nyaakoto_fp_shell_texture.py [--out <dir>]

Writes to Content/SourceArt/Characters/NyaakotoFirstPersonPaws/FurShells/ (or
--out):
- T_NyaakotoFP_FurShells_Strands.png: coverage by height;
- T_NyaakotoFP_FurShells_Tint.png: each strand's brightness;
- manifest.json: their SHA-256, coverage per channel, the tint's mean, the
  coat's far-field composite and white gain, and the composite measure.

**Why shells.** Fur v4 and v5 were masked cards on a thin sheet. Thin alpha
dithered into speckle (v3); opaque cores tiled into flat flakes over gaps
(v4, v5; root's reviews of captures v5 and v6). Shell fur stacks translucent
offset layers of the skin instead (nyaakoto_fp_paws.fur_shells). Each layer
draws only the cross-sections of the strands that reach its height, so:
- there are no card outlines;
- there is no dither (the shells' material is translucent);
- every gap is the coat's deeper layers, not skin.

**v2: clumps (fur v7).** Capture v7 and root's review: "a white glove",
felt-like, with no strand definition. v1's strands were 0.18 mm apart on a
4 mm tile. At both first-person footprints (0.44 mm and 0.08 mm per pixel
after the paw's 0.75 scale) the mips average them to each layer's mean
coverage, so the ten layers composite to a uniform pile. On composite_measure's
model, luminance varies by a coefficient of 0.015 in the eye view and 0.044
in the close-up.

Real fur reads by its clumps. Here v1's strands stay as the fine structure,
gathered into clumps that read at those footprints:
- **Clumps:** blue-noise centres CLUMP_MM apart. Each strand belongs to its
  nearest centre, and with height it is drawn toward it, by CONVERGE (one
  value per clump) at the clump's length. So a clump tapers to a tip and
  partings open between clumps.
- **Length:** each clump has its own length, a share of the coat's height
  (CLUMP_LENGTH). Clumps run longer in the tuft field's crests, a tileable
  field a few millimetres across. Each strand is a share of its clump's
  length (STRAND_LENGTH). The tallest clumps pass the top shell, so every
  shell carries some coverage: a shell that draws nothing still costs its
  overdraw. A draft at 0.55-1.0 and 0.7-1.0 left the top shell empty
  (0.000 at 0.90) and the ninth at 1 %.
- **Tint:** each strand's brightness, written as a separate linear map. It is
  darker in the tuft field's troughs (TINT tuft), per clump (TINT clump) and
  per strand (TINT strand). The material multiplies the vertex colour by it.
- **The tile:** TILE_MM of skin, twice v1's, so clumps repeat less often.
  It keeps v1's texel size.

**The channels.** R, G, B and A of the strand map hold the strands' coverage
at four heights, HEIGHTS of the coat's. The material blends them by each
shell's height (its vertex colour's alpha). Coverage, not distance, is
stored so that mips average it correctly. Linear values, no sRGB.

**v3: irregular clumps.** The Cycles review of v2's build
(Saved/NyaakotoFPPaws/Archive/v7_attempt0_production) showed that the stripes
were gone. But the clumps read as a regular knit or terry grain: even sizes
in rows, each one outlined. So:
- the clumps' layout is looser (CLUMP_MIN_SPACING 0.5, from 0.8), so their
  sizes vary;
- they converge less (0.45-0.8, from 0.7-0.9), so neighbours merge more;
- the tint varies less per clump and more per tuft.

**The composite measure** (composite_measure) is a CPU model of what the
shader composites, recorded in the manifest. It models:
- the shells' heights (nyaakoto_fp_paws.SHELLS) and the material's tents and
  0.95;
- each layer read at a view's footprint (its mip, as a box), displaced along
  the flow by its height x tan(lean), and composited bottom to top;
- a flat coat of the dorsal height, seen straight down.

It reports the composite's mean and its coefficient of variation per view.
On it, v1's texture under v6's shells gives 0.015 in the eye view and 0.044
in the close-up; this one under v7's gives 0.049 and 0.094. It is a design
aid, not a render: the capture decides.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fur_atlas_coverage as C  # noqa: E402
import nyaakoto_fp_paws as P  # noqa: E402

ROOT = HERE.parents[1]
OUT = ROOT / "Content/SourceArt/Characters/NyaakotoFirstPersonPaws/FurShells"
NAME = "T_NyaakotoFP_FurShells_Strands.png"
TINT_NAME = "T_NyaakotoFP_FurShells_Tint.png"
SEED = 20261025
VERSION = 3
SIZE = 1024
TINT_SIZE = 512
TILE_MM = 8.0                         # skin a texture tile spans (nyaakoto_fp_paws.SHELLS uv_tile_m)
MIN_SPACING = 0.8                     # dart throwing's least distance, in spacings (the strands')
CLUMP_MIN_SPACING = 0.5               # the clumps': looser, so clumps differ in size (v3; v2 0.8)
STRAND_MM = 0.18                      # v1's strands: their centres' mean spacing
STRAND_R0 = 0.58                      # a strand's base radius, in strand spacings
STRAND_TAPER = 0.6                    # its radius closes as (1 - h / length)^STRAND_TAPER
STRAND_LENGTH = (0.8, 1.0)            # a strand's length, as a share of its clump's
CLUMP_MM = 1.2                        # clump centres' mean spacing
CLUMP_LENGTH = (0.75, 1.25)           # a clump's length, as a share of the coat's height: the tallest pass the top
                                      # shell, so every shell draws some tips (at 0.55-1.0 the top shell drew none)
TUFT_LENGTH = 0.6                     # how much of a clump's length the tuft field sets (the rest is its own)
CONVERGE = (0.45, 0.8)                # how far a clump's strands close on its centre by its tip (v3; v2 0.7-0.9)
TUFT_WAVES = ((2, 1), (1, 2), (3, 1), (2, -3), (1, -2), (3, 2))   # the tuft field's waves, in cycles per tile
TINT = {"tuft": 0.12, "clump": 0.03, "strand": 0.03}   # v3; v2 0.10 / 0.05 / 0.03
HEIGHTS = (0.15, 0.40, 0.65, 0.90)    # the four channels' heights, as shares of the coat's
AA = 0.06                             # the soft edge, in strand spacings
VIEWMODELS = ROOT / "Content/Data/viewmodels.json"


def blue_noise(rng, spacing, count, min_spacing=None):
    """Up to count wrapped dart-throwing points in the unit tile, at least min_spacing (MIN_SPACING) x spacing
    apart."""
    least = (MIN_SPACING if min_spacing is None else min_spacing) * spacing
    pts = []
    tries = 0
    while len(pts) < count and tries < 200 * count:
        tries += 1
        p = rng.random(2)
        if pts:
            d = np.abs(np.array(pts) - p)
            d = np.minimum(d, 1.0 - d)                       # wrapped
            if (np.hypot(d[:, 0], d[:, 1]) < least).any():
                continue
        pts.append(p)
    return np.array(pts)


def tuft_field(rng, size):
    """A tileable field in [0, 1] (size x size), a few millimetres across: TUFT_WAVES' cosines at seeded phases."""
    yy, xx = np.mgrid[0:size, 0:size] / size
    f = np.zeros((size, size))
    for a, b in TUFT_WAVES:
        f += np.cos(2 * math.pi * (a * xx + b * yy) + rng.uniform(0, 2 * math.pi))
    return (f - f.min()) / (f.max() - f.min())


def layout(rng):
    """The clumps and their strands: centres, lengths, convergence and tints; each strand's clump and offset."""
    sc, ss = CLUMP_MM / TILE_MM, STRAND_MM / TILE_MM
    clumps = blue_noise(rng, sc, int(round(1.0 / (sc * sc))), CLUMP_MIN_SPACING)
    strands = blue_noise(rng, ss, int(round(1.0 / (ss * ss))))
    tuft = tuft_field(rng, TINT_SIZE)
    at = np.clip((clumps * TINT_SIZE).astype(int), 0, TINT_SIZE - 1)
    crest = tuft[at[:, 1], at[:, 0]]
    lo, hi = CLUMP_LENGTH
    c_len = lo + (hi - lo) * (TUFT_LENGTH * crest + (1 - TUFT_LENGTH) * rng.random(len(clumps)))
    c_conv = rng.uniform(*CONVERGE, len(clumps))
    c_tint = 1.0 - TINT["tuft"] * (1.0 - crest) - TINT["clump"] * rng.random(len(clumps))
    d = strands[:, None, :] - clumps[None, :, :]
    d -= np.round(d)                                          # wrapped
    owner = np.argmin((d ** 2).sum(2), 1)
    offset = d[np.arange(len(strands)), owner]
    s_len = c_len[owner] * rng.uniform(*STRAND_LENGTH, len(strands))
    s_tint = c_tint[owner] * (1.0 - TINT["strand"] * rng.random(len(strands)))
    return {"clumps": clumps, "clump_length": c_len, "converge": c_conv, "clump_tint": c_tint, "strands": strands,
            "owner": owner, "offset": offset, "strand_length": s_len, "strand_tint": s_tint}


def nearest_clump_tint(lay):
    """(SIZE, SIZE): each texel's nearest clump centre's tint (wrapped), so a parting no strand reaches still has
    its clump's tint for the mips to average."""
    g = (np.arange(SIZE) + 0.5) / SIZE
    out = np.empty((SIZE, SIZE))
    for y0 in range(0, SIZE, 128):
        yy, xx = np.meshgrid(g[y0:y0 + 128], g, indexing="ij")
        dx = xx[..., None] - lay["clumps"][None, None, :, 0]
        dy = yy[..., None] - lay["clumps"][None, None, :, 1]
        dx -= np.round(dx)
        dy -= np.round(dy)
        out[y0:y0 + 128] = lay["clump_tint"][np.argmin(dx * dx + dy * dy, 2)]
    return out


def coverage(lay):
    """(SIZE, SIZE, 4) coverage by height, and (SIZE, SIZE) each texel's tint: its nearest strand's within a strand's
    reach at the lowest height, else its nearest clump's."""
    ss = STRAND_MM / TILE_MM
    out = np.zeros((SIZE, SIZE, len(HEIGHTS)))
    near = np.full((SIZE, SIZE), np.inf)
    tint = nearest_clump_tint(lay)
    reach = int(math.ceil((STRAND_R0 + AA) * ss * SIZE)) + 2
    off = np.arange(-reach, reach + 1)
    for k, centre in enumerate(lay["clumps"][lay["owner"]]):
        c = lay["owner"][k]
        for ch, h in enumerate(HEIGHTS):
            if h >= lay["strand_length"][k]:
                continue
            pos = (centre + lay["offset"][k] * (1.0 - lay["converge"][c] * h / lay["clump_length"][c])) % 1.0
            cx, cy = pos * SIZE
            xs = (int(math.floor(cx)) + off) % SIZE
            ys = (int(math.floor(cy)) + off) % SIZE
            X, Y = np.meshgrid(math.floor(cx) + off + 0.5, math.floor(cy) + off + 0.5)
            dist = np.hypot(X - cx, Y - cy) / (ss * SIZE)      # in strand spacings
            r = STRAND_R0 * (1.0 - h / lay["strand_length"][k]) ** STRAND_TAPER
            cov = np.clip((r + 0.5 * AA - dist) / AA, 0.0, 1.0)
            blk = np.ix_(ys, xs)
            out[blk + (ch,)] = np.maximum(out[blk + (ch,)], cov)
            if ch == 0:
                closer = dist < near[blk]
                near[blk] = np.where(closer, dist, near[blk])
                tint[blk] = np.where(closer, lay["strand_tint"][k], tint[blk])
    return out, tint


def tent(cov, share):
    """The material's opacity before its 0.95: the coverage channels blended by tents a quarter wide around the
    shell's height share, clamped to HEIGHTS' span."""
    h = min(max(share, HEIGHTS[0]), HEIGHTS[-1])
    return sum(max(1.0 - 4.0 * abs(h - c), 0.0) * cov[..., k] for k, c in enumerate(HEIGHTS))


def composite_measure(cov, tint, cfg=P.SHELLS, gain=1.0, region="dorsal", views=C.VIEWS):
    """Per view: the composite's mean and coefficient of variation, one sample per pixel. See the module notes."""
    scale = json.loads(VIEWMODELS.read_text(encoding="utf-8"))["mesh_scale"]
    texel_mm = TILE_MM / cov.shape[0]
    H_mm = cfg["height_m"][region] * 1e3
    lean = math.tan(math.radians(cfg["lean_deg"]))
    L = cfg["layers"]
    out = {}
    for view, pixel_mm in views.items():
        f = max(1, int(round(pixel_mm / (texel_mm * scale))))
        covf = np.stack([C.box_mean(cov[..., k], f, f) for k in range(cov.shape[2])], -1)
        tf = C.box_mean(tint, f, f) if tint.shape == cov.shape[:2] else np.full(cov.shape[:2], float(tint.mean()))
        comp = np.full(cov.shape[:2], cfg["skin_share"])
        for i in range(L):
            share = ((i + 0.5) / L) ** cfg["spacing_power"]
            d = int(round(share * H_mm * lean / texel_mm))
            a = 0.95 * tent(np.roll(covf, d, axis=1), share)
            shade = cfg["deep_shade"] + (1.0 - cfg["deep_shade"]) * (i + 0.5) / L
            comp = gain * shade * np.roll(tf, d, axis=1) * a + comp * (1.0 - a)
        px = comp[::f, ::f]
        out[view] = {"footprint_texels": f, "mean": round(float(px.mean()), 4),
                     "cv": round(float(px.std() / px.mean()), 4)}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, default=OUT)
    out = ap.parse_args(argv).out
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    lay = layout(rng)
    cov, tint = coverage(lay)
    small = tint.reshape(TINT_SIZE, SIZE // TINT_SIZE, TINT_SIZE, SIZE // TINT_SIZE).mean((1, 3))
    path, tpath = out / NAME, out / TINT_NAME
    Image.fromarray(np.clip(np.rint(cov * 255), 0, 255).astype(np.uint8)).save(path, optimize=True)        # RGBA
    Image.fromarray(np.clip(np.rint(small * 255), 0, 255).astype(np.uint8)).save(tpath, optimize=True)
    with Image.open(path) as im:
        written = np.asarray(im, np.float64) / 255.0
    with Image.open(tpath) as im:
        t_written = np.asarray(im, np.float64) / 255.0
    means = [float(written[..., c].mean()) for c in range(len(HEIGHTS))]
    t_mean = float(t_written.mean())
    gain = P.shell_white_gain(means, t_mean)
    up = np.repeat(np.repeat(t_written, SIZE // TINT_SIZE, 0), SIZE // TINT_SIZE, 1)
    record = {"schema_version": 2, "version": VERSION, "generator": "scripts/art/create_nyaakoto_fp_shell_texture.py",
              "seed": SEED,
              "texture": {"file": NAME, "size": [SIZE, SIZE], "mode": "RGBA", "colour_space": "linear",
                          "sha256": hashlib.sha256(path.read_bytes()).hexdigest()},
              "tint": {"file": TINT_NAME, "size": [TINT_SIZE, TINT_SIZE], "mode": "L", "colour_space": "linear",
                       "sha256": hashlib.sha256(tpath.read_bytes()).hexdigest(), "mean": round(t_mean, 4)},
              "tile_mm": TILE_MM, "heights": list(HEIGHTS), "aa": AA,
              "strand": {"spacing_mm": STRAND_MM, "count": int(len(lay["strands"])), "r0": STRAND_R0,
                         "taper": STRAND_TAPER, "length_of_clump": list(STRAND_LENGTH)},
              "clump": {"spacing_mm": CLUMP_MM, "count": int(len(lay["clumps"])), "length": list(CLUMP_LENGTH),
                        "tuft_length": TUFT_LENGTH, "converge": list(CONVERGE), "tuft_waves": [list(w) for w in TUFT_WAVES]},
              "tint_spread": TINT,
              "mean_coverage": {f"{'RGBA'[c]} (h {h})": round(means[c], 4) for c, h in enumerate(HEIGHTS)},
              "far_field": {"composite": round(P.shell_far_field(means, t_mean), 4), "white_gain": round(gain, 4),
                            "target": P.SHELLS["white_target"]},
              "composite_measure": composite_measure(written, up, gain=gain),
              "tileable": "wrapped: strand and clump distances and the discs wrap at the tile's edges",
              "provenance": "original and procedural: every clump and strand placed by this script from its seed; no "
                            "external image, scan or third-party texture"}
    (out / "manifest.json").write_text(json.dumps(record, indent=1) + "\n")
    print("SHELL_TEXTURE_READY", record["texture"]["sha256"][:12], record["tint"]["sha256"][:12],
          record["clump"]["count"], "clumps", record["strand"]["count"], "strands",
          json.dumps(record["mean_coverage"]), json.dumps(record["far_field"]), json.dumps(record["composite_measure"]))


if __name__ == "__main__":
    main()
