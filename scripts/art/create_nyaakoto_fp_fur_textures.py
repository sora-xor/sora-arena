"""Author the fur-card atlas for Nyaakoto's first-person paws: original, seeded, no external images.

Run with the project's pinned Python (numpy, Pillow):
  python scripts/art/create_nyaakoto_fp_fur_textures.py [--out <dir>]

Writes to Content/SourceArt/Characters/NyaakotoFirstPersonPaws/FurCards/ (or
--out), with SHA-256 records and the atlas's dither measure in its
manifest.json:
- **The atlas:** 2048 x 1024, eight columns by two rows of clump tiles. Each
  tile is a card nyaakoto_fp_paws.fur_cards lays on the skin: the root at the
  tile's bottom edge (UV v up), the tip toward its top.
- **T_NyaakotoFP_FurCards_Albedo.png:** sRGB hair colour, near white so the
  card's vertex colour carries the tabby pattern. Alpha is each pixel's hair
  coverage, the opacity mask.
- **T_NyaakotoFP_FurCards_NormalDX.png:** each strand's and each hair's
  cylindrical normal across its width, in DirectX convention (green down).
- **T_NyaakotoFP_FurCards_Masks.png:** linear masks.
  - R: the root-to-tip gradient, for the occlusion between hairs.
  - G: each strand's random value, for tint and roughness variation.
  - B: the strand's depth in the clump: 1 front, 0 back.

v2 (root's review of the first paw originals: "stiff overlapping white
flakes, a coarse serrated outline"):
- **Straight colour:** v1 stored each texel's colour premultiplied by its
  coverage, so every hair's edge, the part the 0.33 clip keeps, came out dark
  (mean 0.65 against 0.95 in the cores).
- **Fill:** colour is carried 24 texels into the transparent area, so
  filtering and mips never darken an edge.
- Finer strands, more of them (150-230 hairs per tile).

v3 (the first lit Unreal originals, Saved/YumiFP/v2, and root's review of
them: "flecked/flat white fur clumps"): finer and more even, 260-360 hairs
per tile at 0.9-1.7 texels. The v2 atlas is archived at
Saved/NyaakotoFPPaws/Archive/v2_furcards.

v4 (capture v4, Saved/YumiFP/v4_*, and root's review: "white fur remains
coarse, blade-like, noisy"):
- **What was wrong:** the engine dithers every fragment whose mask is
  between 0 and clip + 0.5, drawing it with probability alpha / 0.83 at clip
  0.33 (fur_atlas_coverage.py, from BlueNoiseCommon.ush and
  MaterialTemplate.ush).
  - v3's hairs are about 5 um on a 1 mm card, so every footprint a view uses
    averages them to alpha 0.1 to 0.7.
  - 98 % (eye view) and 89 % (paw close-up) of the cards' covered area was
    dithered: each fur pixel was a per-frame coin flip.
  - The run-up comparison of the same capture did not resolve it.
- **What v4 does:** it makes a clump opaque where it is a clump, and puts the
  hair in colour and normal.
  - **Strand groups** at the scale the close-up resolves: 7 to 11 per tile,
    their roots 1.5 to 2.1 times the even share of the width, so the lower
    tile is fully covered.
  - **An opaque body:** alpha 1 inside it, with a 1.5-texel antialiased
    edge. It closes (TAPER) at 62 % to 82 % of its strand (FRINGE).
  - **A fringe:** the body's 4 to 8 hairs run on alone to the strand's tip,
    between 70 % and 100 % of the tile (TIP_V). Each fades in inside the
    body, so it leaves no seam. The dithered band is this fringe.
  - **Within a strand,** the hairs are streaks in colour (+-6 %, darker at
    their seams) and in the normal (each hair's cylinder on the strand's).
    The close-up resolves the strands, and the eye view averages them to a
    soft sheen.
  - **Odd rows run root at the top,** so tips abut tips and roots abut roots.
  - Measured (fur_atlas_coverage, in the manifest): dithered 47-49 % in the
    eye view and 37 % in the close-up. The speckle variance is 42 % and
    45 % of v3's.
- The v3 atlas is archived at Saved/NyaakotoFPPaws/Archive/v3_furcards.
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

ROOT = HERE.parents[1]
OUT = ROOT / "Content/SourceArt/Characters/NyaakotoFirstPersonPaws/FurCards"
SEED = 20261025
COLS, ROWS = 8, 2                     # nyaakoto_fp_paws.FUR["tiles"]
TW, TH = 256, 512                     # tile width, height in pixels
SEGMENTS = 14
STRANDS = (7, 12)                     # strand groups per tile (the upper bound excluded)
OVERLAP = (1.5, 2.1)                  # a strand's root width, in even shares of the tile's width
TIP_V = (0.70, 1.0)                   # where a strand's point ends, as a fraction of the tile
CLUMP = 0.30                          # how far each tip is pulled toward the clump's
HAIRS = (4, 9)                        # hair streaks across one strand (the upper bound excluded)
TAPER = (2.8, 0.6)                    # a strand's width: w_root x (1 - along^p)^q
FRINGE = (0.62, 0.82)                 # where a strand's body closes and its hairs run on, as a share of its length
HAIR_WIDTH = 1.3                      # a fringe hair's start, in even shares of the body's width there
HAIR_FADE = 0.2                       # the share of a fringe hair's length over which it fades in
CLIP = 0.33                           # the fur material's opacity_mask_clip_value (import_nyaakoto_fp_paws.py)


def centreline(u0, v0, u1, v1, bend, wave, phase):
    """A strand or hair from (u0, v0) to (u1, v1), in tile units, bent and waved."""
    t = np.linspace(0.0, 1.0, SEGMENTS + 1)
    u = u0 + (u1 - u0) * t + bend * t * (1 - t) * 4 + wave * np.sin(phase + t * 7.0) * t
    v = v0 + (v1 - v0) * t
    return np.stack([u * TW, (1.0 - v) * TH], 1)            # image rows run down: v up becomes row down


def nearest(poly, box):
    """Per texel of the box: the distance to the polyline, the signed distance across it, and the fraction along it."""
    x0, y0, x1, y1 = box
    xs = np.arange(x0, x1) + 0.5
    ys = np.arange(y0, y1) + 0.5
    X, Y = np.meshgrid(xs, ys)
    best = np.full(X.shape, np.inf)
    across = np.zeros(X.shape)
    along = np.zeros(X.shape)
    n = len(poly) - 1
    for i in range(n):
        a, b = poly[i], poly[i + 1]
        ab = b - a
        L2 = float(ab @ ab) or 1e-9
        t = np.clip(((X - a[0]) * ab[0] + (Y - a[1]) * ab[1]) / L2, 0.0, 1.0)
        px, py = a[0] + t * ab[0], a[1] + t * ab[1]
        d = np.hypot(X - px, Y - py)
        side = np.sign((X - a[0]) * ab[1] - (Y - a[1]) * ab[0])
        upd = d < best
        best = np.where(upd, d, best)
        across = np.where(upd, side * d, across)
        along = np.where(upd, (i + t) / n, along)
    return best, across, along


def coverage_of(best, across, width):
    """A 1.5-texel antialiased edge at half the width; a point narrower than 1.5 texels fades rather than aliases."""
    half = width * 0.5
    cover = np.clip((half + 0.75 - best) / 1.5, 0.0, 1.0) * np.clip(width / 1.5, 0.0, 1.0)
    return cover, np.clip(across / np.maximum(half, 1e-6), -1.0, 1.0)


def strand(poly, w_root, box):
    """A strand group's body: coverage, position across (-1 to 1) and along (0 root, 1 end), in the box.

    The width holds near the root and closes (TAPER), as a clump's hairs converge."""
    best, across, along = nearest(poly, box)
    cover, across = coverage_of(best, across, w_root * (1.0 - along ** TAPER[0]) ** TAPER[1])
    return cover, across, along


def hair(poly, w_start, box):
    """One hair running on past its strand's body: tapering from w_start to a 0.6-texel point.

    It fades in over its first HAIR_FADE of length, inside the body, so its start leaves no seam."""
    best, across, along = nearest(poly, box)
    cover, across = coverage_of(best, across, w_start + (0.6 - w_start) * along ** 0.8)
    fade = np.clip(along / HAIR_FADE, 0.0, 1.0)
    return cover * fade * fade * (3 - 2 * fade), across, along


def box_of(poly, reach):
    x0 = int(max(0, math.floor(poly[:, 0].min() - reach - 2)))
    x1 = int(min(TW, math.ceil(poly[:, 0].max() + reach + 2)))
    y0 = int(max(0, math.floor(poly[:, 1].min() - 2)))
    y1 = int(min(TH, math.ceil(poly[:, 1].max() + 2)))
    return (x0, y0, x1, y1) if x1 > x0 and y1 > y0 else None


def tile(rng, index):
    """One clump: overlapping strand groups, each opaque in its body and fringed by its own hairs, back to front."""
    buf = {"alpha": np.zeros((TH, TW)), "colour": np.zeros((TH, TW, 3)), "normal": np.zeros((TH, TW, 3)),
           "masks": np.zeros((TH, TW, 3))}
    buf["normal"][..., 2] = 1.0

    def over(box, cover, colour, nx, masks):
        """Composite one stroke in front of everything drawn so far (premultiplied "over" from black)."""
        x0, y0, x1, y1 = box
        sl = (slice(y0, y1), slice(x0, x1))
        buf["alpha"][sl] = cover + buf["alpha"][sl] * (1 - cover)
        sel = cover[..., None]
        buf["colour"][sl] = colour * sel + buf["colour"][sl] * (1 - sel)
        n_new = np.stack([nx, np.zeros_like(nx), np.sqrt(1 - nx * nx)], -1)
        buf["normal"][sl] = n_new * sel + buf["normal"][sl] * (1 - sel)
        buf["masks"][sl] = masks * sel + buf["masks"][sl] * (1 - sel)

    count = int(rng.integers(*STRANDS))
    clump_u = 0.5 + rng.normal(0.0, 0.05)
    roots = (np.arange(count) + 0.5) / count + rng.normal(0.0, 0.15 / count, count)
    tips = rng.uniform(*TIP_V, count)
    tips[rng.choice(count, size=2, replace=False)] = rng.uniform(0.92, 1.0, 2)    # the clump keeps its full length
    for depth_rank, k in enumerate(rng.permutation(count)):
        depth = depth_rank / max(count - 1, 1)                   # drawn back (0) to front (1)
        tip = float(tips[k])
        body_end = tip * rng.uniform(*FRINGE)                    # the body closes here; its hairs run on to tip
        root_u = float(roots[k])
        tip_u = root_u + (clump_u - root_u) * CLUMP + rng.normal(0.0, 0.03)
        end_u = root_u + (tip_u - root_u) * body_end / tip
        bend, wave, phase = rng.normal(0.0, 0.03), rng.normal(0.0, 0.01), rng.random() * 2 * math.pi
        w_root = TW / count * rng.uniform(*OVERLAP)
        hairs = int(rng.integers(*HAIRS))
        hair_tint = 1.0 + rng.uniform(-0.06, 0.06, hairs)
        tint, warm, grain = rng.uniform(0.90, 1.0), rng.normal(0.0, 0.015), rng.random()
        poly = centreline(root_u, -0.02, end_u, body_end, bend, wave, phase)
        box = box_of(poly, w_root)
        if box is None:
            continue
        cover, across, along = strand(poly, w_root, box)
        # The body's hairs: streaks across it, each its own tint, darker at its seams, and its own cylinder.
        pos = (across + 1.0) * 0.5 * hairs
        j = np.clip(np.floor(pos).astype(int), 0, hairs - 1)
        local = (pos - j) * 2.0 - 1.0                            # -1 to 1 across one hair
        value = tint * hair_tint[j] * (1.0 - 0.08 * local ** 4)
        v = -0.02 + (body_end + 0.02) * along                    # height in the tile: the masks' root-to-tip
        over(box, cover, np.stack([value + warm, value, value - warm], -1),
             np.clip(0.45 * across + 0.25 * local, -0.8, 0.8),
             np.stack([np.clip(v, 0, 1), np.full_like(v, grain), np.full_like(v, depth)], -1))
        # Its hairs run on alone from inside the body to their own points: the fringe.
        start_v = 0.45 * body_end
        s = (start_v + 0.02) / (body_end + 0.02)
        w_at = w_root * (1.0 - s ** TAPER[0]) ** TAPER[1]
        lengths = rng.uniform(0.86, 1.0, hairs)
        lengths *= tip / lengths.max()                           # the longest reaches the strand's tip
        for h in range(hairs):
            offset = ((h + 0.5) / hairs - 0.5) * w_at * 0.9 / TW
            u0 = root_u + (end_u - root_u) * s + offset
            u1 = end_u + offset * 0.6 + rng.normal(0.0, 0.01)
            hp = centreline(u0, start_v, u1, float(lengths[h]), rng.normal(0.0, 0.02), rng.normal(0.0, 0.008),
                            rng.random() * 2 * math.pi)
            w0 = w_at / hairs * HAIR_WIDTH
            hbox = box_of(hp, w0)
            if hbox is None:
                continue
            hc, ha, hl = hair(hp, w0, hbox)
            hv = tint * hair_tint[h] * (1.0 - 0.08 * ha ** 4)
            vv = start_v + (float(lengths[h]) - start_v) * hl
            over(hbox, hc, np.stack([hv + warm, hv, hv - warm], -1), np.clip(0.55 * ha, -0.8, 0.8),
                 np.stack([np.clip(vv, 0, 1), np.full_like(vv, grain), np.full_like(vv, depth)], -1))
    alpha, colour, normal, masks = buf["alpha"], buf["colour"], buf["normal"], buf["masks"]
    # Straight alpha: the composite above is premultiplied ("over" from black),
    # so divide the coverage back out wherever any strand is.
    colour = np.where(alpha[..., None] > 1e-4, colour / np.maximum(alpha[..., None], 1e-4), 0.0)
    nrm = normal / np.maximum(np.linalg.norm(normal, axis=-1, keepdims=True), 1e-9)
    return alpha, colour, nrm, masks


def atlas(seed=SEED):
    """The whole atlas, (H, W, 4) albedo (straight linear colour, alpha), (H, W, 3) normal and masks."""
    rng = np.random.default_rng(seed)
    W, H = COLS * TW, ROWS * TH
    albedo = np.zeros((H, W, 4))
    normal = np.zeros((H, W, 3))
    masks = np.zeros((H, W, 3))
    for r in range(ROWS):
        for c in range(COLS):
            a, col, n, m = tile(rng, r * COLS + c)
            if r % 2:
                # Odd rows run root at the top, so tips abut tips and roots abut roots: a mip read past a tile's
                # end (or wrapping past the atlas's) never pulls an opaque root into a tip (fur_cards maps them so).
                a, col, n, m = a[::-1], col[::-1], n[::-1], m[::-1]
            # UV row 0 is the image's bottom half (v up).
            y0 = (ROWS - 1 - r) * TH
            x0 = c * TW
            albedo[y0:y0 + TH, x0:x0 + TW, :3] = col
            albedo[y0:y0 + TH, x0:x0 + TW, 3] = a
            normal[y0:y0 + TH, x0:x0 + TW] = n
            masks[y0:y0 + TH, x0:x0 + TW] = m
    # Dilate colour under transparent texels, so mips and filtering don't pull in black.
    rgb = albedo[..., :3]
    have = albedo[..., 3] > 0.02
    fill = rgb.copy()
    for _ in range(24):
        nb = np.zeros_like(fill)
        cnt = np.zeros(have.shape)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nb += np.roll(np.roll(np.where(have[..., None], fill, 0.0), dy, 0), dx, 1)
            cnt += np.roll(np.roll(have, dy, 0), dx, 1)
        grow = ~have & (cnt > 0)
        fill[grow] = nb[grow] / cnt[grow][:, None]
        have = have | grow
    fill[~have] = rgb[albedo[..., 3] > 0.5].mean(0)
    albedo[..., :3] = fill
    return albedo, normal, masks


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, default=OUT)
    out = ap.parse_args(argv).out
    out.mkdir(parents=True, exist_ok=True)
    albedo, normal, masks = atlas()
    srgb = np.where(albedo[..., :3] <= 0.0031308, albedo[..., :3] * 12.92,
                    1.055 * np.power(np.clip(albedo[..., :3], 0, 1), 1 / 2.4) - 0.055)
    files = {
        "Albedo": (np.dstack([srgb, albedo[..., 3]]), "RGBA", "sRGB colour; A = hair coverage (opacity mask)"),
        "NormalDX": (np.dstack([normal[..., 0] * 0.5 + 0.5, -normal[..., 1] * 0.5 + 0.5, normal[..., 2] * 0.5 + 0.5]),
                     "RGB", "tangent space, DirectX (green down): each strand's and hair's cylinder across its width"),
        "Masks": (masks, "RGB", "linear: R root-to-tip, G per-strand random, B depth in the clump (1 front)"),
    }
    W, H = COLS * TW, ROWS * TH
    record = {"schema_version": 4, "generator": "scripts/art/create_nyaakoto_fp_fur_textures.py", "seed": SEED,
              "atlas": {"columns": COLS, "rows": ROWS, "tile_px": [TW, TH],
                        "uv": "even rows root at the tile's bottom (v up), odd rows root at its top: tips abut tips",
                        "strands_per_tile": list(STRANDS), "root_overlap": list(OVERLAP), "tip_v": list(TIP_V),
                        "clump": CLUMP, "hairs_per_strand": list(HAIRS)},
              "provenance": "original and procedural: every strand drawn by this script from its seed; no external "
                            "image, scan or third-party texture",
              "maps": {}}
    for key, (arr, mode, note) in files.items():
        path = out / f"T_NyaakotoFP_FurCards_{key}.png"
        img = Image.fromarray(np.clip(np.rint(arr * 255), 0, 255).astype(np.uint8), mode)
        img.save(path, optimize=True)
        record["maps"][key] = {"file": path.name, "size": [W, H], "mode": mode, "note": note, "sha256": sha256(path)}
    # The dither measure of the alpha as written (8-bit), at the views' footprints (fur_atlas_coverage).
    with Image.open(out / "T_NyaakotoFP_FurCards_Albedo.png") as im:
        written = np.asarray(im, np.float64)[..., 3] / 255.0
    record["dither_measure"] = C.measure(written, COLS, ROWS, CLIP)
    (out / "manifest.json").write_text(json.dumps(record, indent=1) + "\n")
    print("FUR_TEXTURES_READY", json.dumps({k: v["sha256"][:12] for k, v in record["maps"].items()}))
    for key, r in record["dither_measure"]["at"].items():
        print(f"  {key}: dithered {r['dithered_share']:.1%}, solid {r['solid_share']:.1%}, "
              f"speckle variance {r['speckle_variance']:.3f}")


if __name__ == "__main__":
    main()
