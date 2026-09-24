"""Paint a reproducible, source-only ibushi-inspired surface atlas.

The pixels are original procedural art, informed by descriptions of polished
clay and smoke-deposited carbon, NOT a capture or measured PBR scan. Sixteen
cells make tile-to-tile firing variation possible without baking a roof image.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Environment/NyaagyuKawaraBay"
OUT.mkdir(parents=True, exist_ok=True)
SIZE, CELL = 2048, 512
RNG = np.random.default_rng(934172)


def band(radius: float) -> np.ndarray:
    raw = RNG.integers(0, 256, (CELL, CELL), dtype=np.uint8)
    smooth = np.asarray(
        Image.fromarray(raw).filter(ImageFilter.GaussianBlur(radius)),
        dtype=np.float32,
    )
    return (smooth - smooth.mean()) / max(float(smooth.std()), 1e-6)


def polish_marks() -> np.ndarray:
    """Fine hand-finish marks, aligned roughly down the slope of each tile."""
    image = Image.new("L", (CELL, CELL), 0)
    draw = ImageDraw.Draw(image)
    for _ in range(46):
        x = int(RNG.integers(0, CELL))
        y = int(RNG.integers(0, CELL))
        length = int(RNG.integers(20, 165))
        drift = int(RNG.integers(-13, 14))
        draw.line((x, y, x + drift, y + length), fill=int(RNG.integers(8, 24)), width=1)
    return np.asarray(image.filter(ImageFilter.GaussianBlur(.55)), dtype=np.float32) / 255


albedo = np.zeros((SIZE, SIZE, 3), dtype=np.uint8)
normal = np.zeros_like(albedo)
orm = np.zeros_like(albedo)
cell_records = []

coord = np.arange(CELL, dtype=np.float32) / (CELL - 1)
u, v = np.meshgrid(coord, coord)
# The roof mesh samples each atlas cell from 0.05 to 0.95. Center edge wear on
# the actual sampled boundaries; otherwise the wear is invisible on the mesh.
sample_edge = np.minimum.reduce(
    (np.maximum(u - .05, 0), np.maximum(.95 - u, 0),
     np.maximum(v - .05, 0), np.maximum(.95 - v, 0))
)
edge_profile = np.exp(-sample_edge / .010)

for index in range(16):
    row, col = divmod(index, 4)
    kiln = float(RNG.uniform(-.026, .026))
    broad = band(39)
    medium = band(12)
    fine = band(1.1)
    polish = polish_marks()
    # Subtle carbon-film irregularity: less visual energy than the former
    # gritty atlas. Exposed dark-clay edges are deliberately sparse.
    soot = np.clip(.009*broad + .006*medium, -.025, .025)
    wear = np.clip(edge_profile*(.45 + .16*medium), 0, 1)
    # Gravity concentrates fine airborne deposits just above the down-slope
    # nose (V=.05 on the actual mesh). Keep this subtle: ibushi is polished,
    # not a porous concrete-like surface.
    nose_deposit = np.exp(-((v - .103) / .036)**2) * np.clip(.65 + .18*medium, 0, 1)
    rain_lines = band(3.3) * np.exp(-((v - .37) / .39)**2)
    value = np.clip(.225 + kiln + soot + .0018*fine
                    - .021*wear - .017*nose_deposit - .003*rain_lines,
                    .13, .32)
    channels = np.stack((value*.97, value*.995, value*1.025), axis=-1)
    channels += np.stack((.009*wear, .002*wear, -.006*wear), axis=-1)
    channels += (polish*.035)[..., None]
    channels = np.clip(channels, 0, 1)

    # A single height field drives the normal map. 512 texels cover one tile:
    # ~0.47 mm/texel across a 240 mm pan. These tiny artistic heights avoid
    # turning a hand-polished ceramic skin into cratered concrete.
    height_m = .000016*fine + .000012*medium + .000010*polish
    pixel_m_x = .240 / (CELL*.90)
    pixel_m_y = .303 / (CELL*.90)
    sx = (np.roll(height_m, -1, axis=1) - np.roll(height_m, 1, axis=1)) / (2*pixel_m_x)
    sy = (np.roll(height_m, -1, axis=0) - np.roll(height_m, 1, axis=0)) / (2*pixel_m_y)
    # DirectX tangent space: +V/green is flipped against the GL convention.
    normals = np.stack((-sx, sy, np.ones_like(sx)), axis=-1)
    normals /= np.linalg.norm(normals, axis=-1, keepdims=True)
    rough = np.clip(.50 + .018*medium + .022*fine + .15*wear
                    + .10*nose_deposit + .045*polish,
                    .39, .75)
    ao = np.clip(.994 - .018*wear, .96, 1)

    ys, xs = row*CELL, col*CELL
    albedo[ys:ys+CELL, xs:xs+CELL] = np.uint8(np.rint(channels*255))
    normal[ys:ys+CELL, xs:xs+CELL] = np.uint8(np.rint((normals*.5+.5)*255))
    orm[ys:ys+CELL, xs:xs+CELL] = np.stack((
        np.uint8(np.rint(ao*255)), np.uint8(np.rint(rough*255)),
        np.zeros((CELL, CELL), dtype=np.uint8)), axis=-1)
    cell_records.append({
        "cell": index, "mean_albedo": [round(float(x), 4) for x in channels.mean((0, 1))],
        "mean_roughness": round(float(rough.mean()), 4),
    })

files = {}
for name, pixels in (("Albedo", albedo), ("NormalDX", normal), ("ORM", orm)):
    path = OUT / f"T_NyaagyuIbushi_{name}.png"
    Image.fromarray(pixels, "RGB").save(path, optimize=True)
    files[name] = {"file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

manifest = {
    "author": "SORA Arena original procedural material study",
    "generator": "scripts/art/build_nyaagyu_ibushi_surface.py",
    "source_type": "algorithmically painted; no third-party pixels",
    "reference": "https://koyoibushi.jp/en/",
    "reference_scope": "Published material/process description only; no sampled pixels or measured reflectance",
    "status": "source-only; artistic PBR estimate and not approved game art",
    "size": [SIZE, SIZE], "layout": "4x4", "files": files, "cells": cell_records,
}
(OUT / "ibushi_texture_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps({"status": manifest["status"], "files": files}, indent=2))
