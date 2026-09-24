"""Check the authored ibushi candidate maps before Blender or Unreal import.

These numerical checks catch broken channels, flat normals, repeated cells,
metallic leakage, and stale hashes. They cannot certify historic appearance or
photorealism; the material still needs same-light visual and runtime review.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Environment/NyaagyuKawaraBay"
manifest = json.loads((OUT / "ibushi_texture_manifest.json").read_text())
assert manifest["size"] == [2048, 2048] and manifest["layout"] == "4x4"

maps = {}
for channel in ("Albedo", "NormalDX", "ORM"):
    record = manifest["files"][channel]
    path = OUT / record["file"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == record["sha256"], channel
    image = Image.open(path)
    assert image.mode == "RGB" and image.size == (2048, 2048), channel
    maps[channel] = np.asarray(image, dtype=np.uint8)

albedo, normal, orm = (maps[k] for k in ("Albedo", "NormalDX", "ORM"))
assert 32 <= int(albedo.min()) and int(albedo.max()) < 100
assert int(normal[:, :, 2].min()) > 240  # shallow ceramic relief, not large craters
assert 75 <= int(orm[:, :, 1].min()) < int(orm[:, :, 1].max()) <= 192
assert np.all(orm[:, :, 2] == 0)  # carbon-coated clay is not a metal map
assert int(orm[:, :, 0].min()) >= 240

means = []
for row in range(4):
    for col in range(4):
        cell = albedo[row*512:(row+1)*512, col*512:(col+1)*512]
        means.append(float(cell.mean()))
assert len({round(mean, 2) for mean in means}) >= 12, means
assert max(means) - min(means) >= 6, means
assert float(normal[:, :, :2].std()) > 1.0
assert float(orm[:, :, 1].std()) > 2.0

print(json.dumps({
    "status": "passed numerical source-map checks; visual and Unreal review pending",
    "cells": len(means),
    "cell_mean_luma_range": [round(min(means), 2), round(max(means), 2)],
    "normal_blue_min": int(normal[:, :, 2].min()),
    "roughness_range_8bit": [int(orm[:, :, 1].min()), int(orm[:, :, 1].max())],
}, indent=2))
