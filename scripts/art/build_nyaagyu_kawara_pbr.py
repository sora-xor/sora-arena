"""Bake original, deterministic ceramic color/normal/ORM atlas for a roof study.

These are artist-authored fired-clay fields, not a photographed or measured
historical tile. The atlas has sixteen nonidentical tile faces so geometry does
not repeat a whole-roof photograph over modeled kawara.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Environment/NyaagyuKawaraBay"
OUT.mkdir(parents=True, exist_ok=True)
SIZE = 2048
CELL = SIZE // 4
RNG = np.random.default_rng(172803)


def blurred_noise(radius: float) -> np.ndarray:
    small = RNG.integers(0, 256, (CELL, CELL), dtype=np.uint8)
    field = np.asarray(Image.fromarray(small).filter(ImageFilter.GaussianBlur(radius)), dtype=np.float32) / 255
    # Large-radius blur collapses variance. Renormalize *each* spatial band so
    # the weathering remains visible at roof distance rather than flat grey.
    return np.clip(.5 + (field - field.mean()) / max(float(field.std()), 1e-5) * .17, 0, 1)


albedo = np.zeros((SIZE, SIZE, 3), dtype=np.uint8)
normal = np.zeros_like(albedo)
orm = np.zeros_like(albedo)
details = []
for index in range(16):
    row, col = divmod(index, 4)
    # Silver-grey ibushi-inspired color with restrained clay and firing shifts.
    # Broad mottling affects color and roughness; only fine pores affect normal.
    broad = blurred_noise(42)
    mid = blurred_noise(9)
    pores = blurred_noise(1.2)
    speckle = RNG.random((CELL, CELL), dtype=np.float32)
    variant = float(RNG.uniform(-0.018, 0.018))
    field = (broad - .5) * .16 + (mid - .5) * .095 + variant
    soot = np.clip((mid - .56) * 1.25, 0, .12)
    clay = np.clip((.44 - broad) * .18, 0, .06)
    base = np.stack((.265 + field + clay - soot,
                     .282 + field + clay*.70 - soot,
                     .289 + field + clay*.42 - soot), axis=-1)
    mineral = (speckle > .996) & (mid > .50)
    base[mineral] += np.array((.065, .055, .038), dtype=np.float32)
    base = np.clip(base, .07, .48)
    height = (pores - .5) * .18 + (mid - .5) * .035
    dx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * .5
    dy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * .5
    n = np.stack((-dx*.9, dy*.9, np.ones_like(dx)), -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    rough = np.clip(.70 + (mid - .5)*.16 + soot*.46, .57, .85)
    occlusion = np.clip(.98 - np.maximum(.5-pores, 0)*.08, .93, 1)
    yy, xx = row*CELL, col*CELL
    albedo[yy:yy+CELL, xx:xx+CELL] = np.uint8(np.rint(base*255))
    normal[yy:yy+CELL, xx:xx+CELL] = np.uint8(np.rint((n*.5+.5)*255))
    orm[yy:yy+CELL, xx:xx+CELL] = np.stack((np.uint8(np.rint(occlusion*255)),
                                           np.uint8(np.rint(rough*255)),
                                           np.zeros((CELL,CELL),dtype=np.uint8)), -1)
    details.append({"cell": index, "mean_roughness": round(float(rough.mean()), 4),
                    "mean_albedo": [round(float(v),4) for v in base.mean((0,1))]})

files = {}
for name, pixels in (("Albedo", albedo), ("NormalDX", normal), ("ORM", orm)):
    path = OUT / f"T_NyaagyuKawara_{name}.png"
    Image.fromarray(pixels, "RGB").save(path, optimize=True)
    files[name] = {"file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
(OUT / "texture_manifest.json").write_text(json.dumps({
    "author": "SORA Arena original deterministic ceramic surface study",
    "generator": "scripts/art/build_nyaagyu_kawara_pbr.py",
    "source_type": "algorithmically painted; no third-party pixels",
    "status": "source-only; not measured ceramic or approved game art",
    "size": [SIZE, SIZE], "layout": "4x4", "files": files, "cells": details,
}, indent=2) + "\n")
print(OUT / "texture_manifest.json")
