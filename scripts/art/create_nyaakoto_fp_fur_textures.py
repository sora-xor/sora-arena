"""Author the fur-card atlas for Nyaakoto's first-person paws: original, seeded, no external images.

Run with the project's pinned Python (numpy, Pillow):
  python scripts/art/create_nyaakoto_fp_fur_textures.py

Writes to Content/SourceArt/Characters/NyaakotoFirstPersonPaws/FurCards/, with
SHA-256 records in its manifest.json:
- **The atlas:** 2048 x 1024, eight columns by two rows of clump tiles. Each
  tile is a card nyaakoto_fp_paws.fur_cards lays on the skin: the root at the
  tile's bottom edge (UV v up), the tip toward its top.
- **T_NyaakotoFP_FurCards_Albedo.png:** sRGB hair colour, near white so the
  card's vertex colour carries the tabby pattern. Alpha is each pixel's hair
  coverage, the opacity mask.
- **T_NyaakotoFP_FurCards_NormalDX.png:** each hair's cylindrical normal
  across its width, in DirectX convention (green down).
- **T_NyaakotoFP_FurCards_Masks.png:** linear masks.
  - R: the root-to-tip gradient, for the occlusion between hairs.
  - G: each hair's random value, for tint and roughness variation.
  - B: the hair's depth in the clump: 1 front, 0 back.

The hairs are drawn one by one as tapered, curved strokes. Each tile's hairs
converge from a spread root toward the clump's tip, with a few flyaways, so
a card reads as a clump of real hairs, not a painted stripe.

v2 (root's review of the first paw originals: "stiff overlapping white
flakes, a coarse serrated outline"):
- **Straight colour:** v1 stored each texel's colour premultiplied by its
  coverage, so every hair's edge, the part the 0.33 clip keeps, came out dark
  (mean 0.65 against 0.95 in the cores).
- **Fill:** colour is carried 24 texels into the transparent area, so
  filtering and mips never darken an edge.
- **Finer strands, more of them:** 150-230 hairs per tile, 1.3-2.3 px at the
  root, tapering to 0.25 px, with tips spread from 55% to 97% of the tile so
  a clump's end breaks up instead of ending in a row.

v3 (the first lit Unreal originals, Saved/YumiFP/v2, and root's review of
them: "flecked/flat white fur clumps"): finer and more even.
- **More, finer hairs:** 260-360 per tile, 0.9-1.7 px at the root (flyaways
  0.6-1.0).
- **Softer clump edges:** clumped less (0.45 -> 0.25), with tips from 45% to
  98% of the tile.
- **Fewer strays:** flyaways at 6% (from 12%).
- **Less flecking:** each hair's tint 0.90-1.0 (from 0.86-1.0), and a
  flatter cylinder normal (0.85 -> 0.6 across the width).
- The v2 atlas is archived at Saved/NyaakotoFPPaws/Archive/v2_furcards.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Characters/NyaakotoFirstPersonPaws/FurCards"
SEED = 20261025
COLS, ROWS = 8, 2                     # nyaakoto_fp_paws.FUR["tiles"]
TW, TH = 256, 512                     # tile width, height in pixels
SEGMENTS = 14


def hair_polyline(rng, root_u, tip_u, tip_v, bend, wave, phase):
    """A hair from (root_u, 0.015) to (tip_u, tip_v), in tile units, bent and waved."""
    t = np.linspace(0.0, 1.0, SEGMENTS + 1)
    u = root_u + (tip_u - root_u) * t + bend * t * (1 - t) * 4 + wave * np.sin(phase + t * 7.0) * t
    v = 0.015 + (tip_v - 0.015) * (t ** 0.92)
    return np.stack([u * TW, (1.0 - v) * TH], 1)            # image rows run down: v up becomes row down


def stroke(poly, w_root, w_tip, box):
    """Coverage (0-1), signed distance across the hair, and position along it, in the box."""
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
    width = w_root + (w_tip - w_root) * along ** 0.8
    half = np.maximum(width * 0.5, 0.25)
    cover = np.clip((half + 0.6 - best) / 1.2, 0.0, 1.0)     # a 1.2 px antialiased edge
    cover *= np.clip(width / 1.0, 0.0, 1.0)                  # sub-pixel tips fade rather than alias
    return cover, np.clip(across / half, -1.0, 1.0), along


def tile(rng, index):
    """One clump: hairs converging to the clump's tip, a few flyaways, front to back."""
    alpha = np.zeros((TH, TW))
    colour = np.zeros((TH, TW, 3))
    normal = np.zeros((TH, TW, 3))
    normal[..., 2] = 1.0
    masks = np.zeros((TH, TW, 3))
    count = int(rng.integers(260, 360))
    tip_u = 0.5 + rng.normal(0.0, 0.07)
    spread = rng.uniform(0.55, 0.85)
    for k in range(count):
        depth = k / max(count - 1, 1)                        # drawn back (0) to front (1)
        fly = rng.random() < 0.06
        root_u = 0.5 + (rng.random() - 0.5) * spread
        clump = 0.25 if not fly else 0.0
        t_u = root_u + (tip_u - root_u) * clump + rng.normal(0.0, 0.06 if not fly else 0.16)
        t_v = rng.uniform(0.45, 0.98) if not fly else rng.uniform(0.45, 0.99)
        poly = hair_polyline(rng, root_u, t_u, t_v, rng.normal(0.0, 0.05), rng.normal(0.0, 0.02),
                             rng.random() * 2 * math.pi)
        w_root = rng.uniform(0.9, 1.7) if not fly else rng.uniform(0.6, 1.0)
        x0 = int(max(0, math.floor(poly[:, 0].min() - w_root - 2)))
        x1 = int(min(TW, math.ceil(poly[:, 0].max() + w_root + 2)))
        y0 = int(max(0, math.floor(poly[:, 1].min() - w_root - 2)))
        y1 = int(min(TH, math.ceil(poly[:, 1].max() + w_root + 2)))
        if x1 <= x0 or y1 <= y0:
            continue
        cover, across, along = stroke(poly, w_root, 0.25, (x0, y0, x1, y1))
        tint = rng.uniform(0.90, 1.0)
        warm = rng.normal(0.0, 0.015)
        c = np.array((tint + warm, tint, tint - warm))
        # "over": this hair sits in front of everything drawn so far
        a0 = alpha[y0:y1, x0:x1]
        alpha[y0:y1, x0:x1] = cover + a0 * (1 - cover)
        sel = cover[..., None]
        colour[y0:y1, x0:x1] = c[None, None, :] * sel + colour[y0:y1, x0:x1] * (1 - sel)
        nx = across * 0.6
        nz = np.sqrt(np.maximum(1 - nx * nx, 0.0))
        n_new = np.stack([nx, np.zeros_like(nx), nz], -1)
        normal[y0:y1, x0:x1] = n_new * sel + normal[y0:y1, x0:x1] * (1 - sel)
        m_new = np.stack([along, np.full_like(along, rng.random()), np.full_like(along, depth)], -1)
        masks[y0:y1, x0:x1] = m_new * sel + masks[y0:y1, x0:x1] * (1 - sel)
    # Straight alpha: the composite above is premultiplied ("over" from black),
    # so divide the coverage back out wherever any hair is.
    colour = np.where(alpha[..., None] > 1e-4, colour / np.maximum(alpha[..., None], 1e-4), 0.0)
    nrm = normal / np.maximum(np.linalg.norm(normal, axis=-1, keepdims=True), 1e-9)
    return alpha, colour, nrm, masks


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    W, H = COLS * TW, ROWS * TH
    albedo = np.zeros((H, W, 4))
    normal = np.zeros((H, W, 3))
    masks = np.zeros((H, W, 3))
    for r in range(ROWS):
        for c in range(COLS):
            a, col, n, m = tile(rng, r * COLS + c)
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
    srgb = np.where(albedo[..., :3] <= 0.0031308, albedo[..., :3] * 12.92,
                    1.055 * np.power(np.clip(albedo[..., :3], 0, 1), 1 / 2.4) - 0.055)
    files = {
        "Albedo": (np.dstack([srgb, albedo[..., 3]]), "RGBA", "sRGB colour; A = hair coverage (opacity mask)"),
        "NormalDX": (np.dstack([normal[..., 0] * 0.5 + 0.5, -normal[..., 1] * 0.5 + 0.5, normal[..., 2] * 0.5 + 0.5]),
                     "RGB", "tangent space, DirectX (green down): each hair's cylinder across its width"),
        "Masks": (masks, "RGB", "linear: R root-to-tip, G per-hair random, B depth in the clump (1 front)"),
    }
    record = {"schema_version": 3, "generator": "scripts/art/create_nyaakoto_fp_fur_textures.py", "seed": SEED,
              "atlas": {"columns": COLS, "rows": ROWS, "tile_px": [TW, TH], "uv": "root at each tile's bottom (v up)"},
              "provenance": "original and procedural: every hair drawn by this script from its seed; no external "
                            "image, scan or third-party texture",
              "maps": {}}
    for key, (arr, mode, note) in files.items():
        path = OUT / f"T_NyaakotoFP_FurCards_{key}.png"
        img = Image.fromarray(np.clip(np.rint(arr * 255), 0, 255).astype(np.uint8), mode)
        img.save(path, optimize=True)
        record["maps"][key] = {"file": path.name, "size": [W, H], "mode": mode, "note": note, "sha256": sha256(path)}
    (OUT / "manifest.json").write_text(json.dumps(record, indent=1) + "\n")
    print("FUR_TEXTURES_READY", json.dumps({k: v["sha256"][:12] for k, v in record["maps"].items()}))


if __name__ == "__main__":
    main()
