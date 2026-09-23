"""Derive 64 aligned per-stone PBR atlas cells from the pinned CC0 path scan.

Run with system Python + Pillow/numpy before create_nyaagyu_hero_path.py.
This is texture editing, not a new third-party asset. We select photographed
stone *interiors* with little grout and crop the same pixels in all three
source channels. Tangent-space normals remain in their source orientation.
Each mesh stone gets its own island.
"""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
SCAN_DIR = ROOT / "Content/SourceArt/Environment/NyaagyuTerrain"
SCAN_MANIFEST = json.loads((SCAN_DIR / "manifest.json").read_text())
SCAN = SCAN_MANIFEST["stone_pathway_scan"]
OUT = ROOT / "Content/SourceArt/Environment/NyaagyuHeroPath"
OUT.mkdir(parents=True, exist_ok=True)
ATLAS_MANIFEST = OUT / "atlas_manifest.json"
GRID = 8
CELL = 480
SIDE = 4096
MARGIN = 128
COUNT = 64
rng = random.Random(0x51504A74)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


paths = {}
for item in SCAN["files"]:
    if item["channel"] not in {"Diffuse", "nor_dx", "arm"}:
        continue
    path = SCAN_DIR / item["file"]
    assert path.is_file() and path.stat().st_size == item["bytes"] and sha(path) == item["sha256"]
    paths[item["channel"]] = path
assert SCAN["asset_id"] == "grey_stone_path" and SCAN["license"] == "CC0-1.0"
assert set(paths) == {"Diffuse", "nor_dx", "arm"}
images = {key: Image.open(path).convert("RGB") for key, path in paths.items()}
assert all(im.size == (2048, 2048) for im in images.values())


# Integral image avoids a slow pixel loop across thousands of candidate crops.
# Dark grout is generally below 65 in this scan; we retain modest veins while
# excluding crops with broad grout bands.
albedo = np.asarray(images["Diffuse"], dtype=np.uint8)
gray = albedo.astype(np.float32).mean(axis=2)
dark = (gray < 65).astype(np.uint32)
integral = np.pad(dark, ((1, 0), (1, 0))).cumsum(0).cumsum(1)


def dark_fraction(x: int, y: int, size: int) -> float:
    count = (int(integral[y + size, x + size]) - int(integral[y, x + size])
             - int(integral[y + size, x]) + int(integral[y, x]))
    return count / (size * size)


candidates = []
for crop_size in (240, 224, 256):
    for y in range(0, 2048 - crop_size, 32):
        for x in range(0, 2048 - crop_size, 32):
            frac = dark_fraction(x, y, crop_size)
            if frac <= .075:
                candidates.append((x, y, crop_size, frac))
assert len(candidates) > 400, len(candidates)
rng.shuffle(candidates)
selected = []
for min_spacing in (145, 105, 65, 0):
    for x, y, size, frac in candidates:
        center = (x + size / 2, y + size / 2)
        if any((center[0] - sx) ** 2 + (center[1] - sy) ** 2 < min_spacing ** 2
               for sx, sy, _, _ in selected):
            continue
        selected.append((center[0], center[1], (x, y, size), frac))
        if len(selected) == COUNT:
            break
    if len(selected) == COUNT:
        break
assert len(selected) == COUNT, len(selected)


atlasses = {key: Image.new("RGB", (SIDE, SIDE), (82, 82, 82) if key == "Diffuse"
                          else ((128, 128, 255) if key == "nor_dx" else (255, 185, 0)))
            for key in images}
cells = []
for index, (_, _, (x, y, size), frac) in enumerate(selected):
    turns = 0
    mirror = False
    col, row = index % GRID, index // GRID
    at_x, at_y = MARGIN + col * CELL, MARGIN + row * CELL
    for channel, source in images.items():
        patch = source.crop((x, y, x + size, y + size))
        patch = patch.resize((CELL, CELL), Image.Resampling.LANCZOS)
        atlasses[channel].paste(patch, (at_x, at_y))
    cells.append({"index": index, "source_crop_xy_size_px": [x, y, size],
                  "source_dark_grout_fraction": round(frac, 5),
                  "quarter_turns": turns, "mirrored": mirror,
                  "atlas_xy_px": [at_x, at_y]})


outputs = {}
for channel, (filename, fmt) in {
        "Diffuse": ("T_HeroPath_StoneFaces_Albedo.jpg", "JPEG"),
        "nor_dx": ("T_HeroPath_StoneFaces_NormalDX.png", "PNG"),
        "arm": ("T_HeroPath_StoneFaces_ORM.png", "PNG")}.items():
    target = OUT / filename
    kwargs = {"quality": 95, "subsampling": 0} if fmt == "JPEG" else {"compress_level": 6}
    atlasses[channel].save(target, fmt, **kwargs)
    outputs[channel] = {"file": filename, "sha256": sha(target), "bytes": target.stat().st_size}


record = {
    "schema_version": 1,
    "generator": "scripts/art/build_nyaagyu_hero_path_atlas.py",
    "generator_sha256": sha(ROOT / "scripts/art/build_nyaagyu_hero_path_atlas.py"),
    "source_manifest": str((SCAN_DIR / "manifest.json").relative_to(ROOT)),
    "source_asset": "grey_stone_path",
    "source_url": SCAN["source_url"],
    "source_license": "CC0-1.0",
    "source_files": {key: {"repo_path": str(path.relative_to(ROOT)), "sha256": sha(path)}
                     for key, path in paths.items()},
    "size_px": SIDE, "grid": GRID, "cell_px": CELL, "margin_px": MARGIN,
    "count": COUNT,
    "crop_policy": "Co-registered 224-256 px stone-interior crops with <=7.5% dark grout; no tangent-space normal transforms",
    "cells": cells,
    "outputs": outputs,
    "limitations": "Cropped 2K scan texture detail can soften at extreme close range; individual hand-sculpted faces and a 4K per-stone scan set remain future AAA art requirements.",
}
ATLAS_MANIFEST.write_text(json.dumps(record, indent=2) + "\n")
print("NYAAGYU_HERO_PATH_ATLAS_CREATED", COUNT, len(candidates), max(c["source_dark_grout_fraction"] for c in cells))
