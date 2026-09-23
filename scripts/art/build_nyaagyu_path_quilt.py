"""Synthesize a co-registered 7.2 m Estate paving atlas from the pinned CC0 scan.

Eight-by-eight overlapping scan patches are selected by edge agreement and
cut on low-error seams. All four photographed PBR channels use *identical*
source crops and seam masks. No rotations, mirrors, invented stone normals, or
diffuse-only overlays are used. The atlas remains periodic at its outer edge.

Run: python3 scripts/art/build_nyaagyu_path_quilt.py
"""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "Content/SourceArt/Environment/NyaagyuTerrain"
OUT = SOURCE / "QuiltedPath"
OUT.mkdir(parents=True, exist_ok=True)
RECORD = json.loads((SOURCE / "manifest.json").read_text())["stone_pathway_scan"]
assert RECORD["asset_id"] == "grey_stone_path" and RECORD["license"] == "CC0-1.0"

SIDE = 4096
COUNT = 8
STEP = 512
OVERLAP = 128
PATCH = STEP + OVERLAP
EXTENT = SIDE + OVERLAP
SOURCE_RES = 1024  # 2048 px / 1.8 m resampled to 1024 px / 1.8 m.
SEED = 0x50A4A771
RNG = random.Random(SEED)
CHANNELS = ("Diffuse", "nor_dx", "arm", "disp")
SCORE_SCALE = 8


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


source = {}
source_records = {}
for record in RECORD["files"]:
    key = record["channel"]
    path = SOURCE / record["file"]
    assert key in CHANNELS and path.stat().st_size == record["bytes"] and sha(path) == record["sha256"]
    assert Image.open(path).size == (2048, 2048)
    # Poly Haven's displacement PNG is 16-bit. Converting it to Pillow "L"
    # clips almost the entire 1460..65145 source range to 255, silently
    # destroying the photographed relief. Resize in floating-point then keep
    # the 16-bit channel intact through the quilt and output.
    if key == "disp":
        source[key] = np.clip(np.asarray(Image.open(path).convert("F").resize(
            (SOURCE_RES, SOURCE_RES), Image.Resampling.LANCZOS)), 0, 65535).astype(np.uint16)
    else:
        source[key] = np.asarray(Image.open(path).convert("RGB").resize(
            (SOURCE_RES, SOURCE_RES), Image.Resampling.LANCZOS)).copy()
    source_records[key] = {"repo_path": str(path.relative_to(ROOT)), "sha256": record["sha256"]}

canvases = {key: np.zeros((EXTENT, EXTENT, 3 if key != "disp" else 1),
                          dtype=np.uint16 if key == "disp" else np.uint8)
            for key in CHANNELS}
candidate_positions = [(x, y) for y in range(0, SOURCE_RES - PATCH + 1, 16)
                       for x in range(0, SOURCE_RES - PATCH + 1, 16)]
assert len(candidate_positions) > 500
source_color_small = np.asarray(Image.fromarray(source["Diffuse"]).resize(
    (SOURCE_RES // SCORE_SCALE, SOURCE_RES // SCORE_SCALE), Image.Resampling.BOX), dtype=np.float32)


def minimum_vertical_seam(cost: np.ndarray) -> np.ndarray:
    """One x-coordinate per scanline across a left-hand overlap."""
    h, w = cost.shape
    acc = cost.astype(np.float32).copy()
    back = np.zeros((h, w), dtype=np.int8)
    for y in range(1, h):
        prev = acc[y - 1]
        options = np.stack((np.pad(prev[:-1], (1, 0), constant_values=1e20),
                            prev, np.pad(prev[1:], (0, 1), constant_values=1e20)))
        pick = np.argmin(options, axis=0)
        back[y] = pick.astype(np.int8) - 1
        acc[y] += options[pick, np.arange(w)]
    seam = np.empty(h, dtype=np.int16)
    seam[-1] = int(np.argmin(acc[-1]))
    for y in range(h - 1, 0, -1):
        seam[y - 1] = seam[y] + back[y, seam[y]]
    return seam


def stitch_one(row: int, col: int) -> dict:
    x0, y0 = col * STEP, row * STEP
    left = col != 0
    top = row != 0
    target = canvases["Diffuse"][y0:y0 + PATCH, x0:x0 + PATCH]
    # Compare downsampled overlap colors first, then choose stochastically
    # among the best 12 crops so local matches do not create a new regular grid.
    preview = np.asarray(Image.fromarray(target).resize((PATCH // SCORE_SCALE, PATCH // SCORE_SCALE), Image.Resampling.BOX),
                         dtype=np.float32)
    right_reference = None
    bottom_reference = None
    if col == COUNT - 1:
        first = canvases["Diffuse"][y0:y0 + PATCH, :OVERLAP]
        right_reference = np.asarray(Image.fromarray(first).resize((OVERLAP // SCORE_SCALE,
                                                                     PATCH // SCORE_SCALE),
                                                          Image.Resampling.BOX), dtype=np.float32)
    if row == COUNT - 1:
        first = canvases["Diffuse"][:OVERLAP, x0:x0 + PATCH]
        bottom_reference = np.asarray(Image.fromarray(first).resize((PATCH // SCORE_SCALE,
                                                                      OVERLAP // SCORE_SCALE),
                                                           Image.Resampling.BOX), dtype=np.float32)
    scores = []
    for sx, sy in candidate_positions:
        crop = source_color_small[sy // SCORE_SCALE:sy // SCORE_SCALE + PATCH // SCORE_SCALE,
                                  sx // SCORE_SCALE:sx // SCORE_SCALE + PATCH // SCORE_SCALE]
        score = 0.0
        if left:
            difference = crop[:, :OVERLAP // SCORE_SCALE] - preview[:, :OVERLAP // SCORE_SCALE]
            score += float(np.mean(difference * difference))
        if top:
            difference = crop[:OVERLAP // SCORE_SCALE] - preview[:OVERLAP // SCORE_SCALE]
            score += float(np.mean(difference * difference))
        if col == COUNT - 1:
            difference = crop[:, -OVERLAP // SCORE_SCALE:] - right_reference
            score += .7 * float(np.mean(difference * difference))
        if row == COUNT - 1:
            difference = crop[-OVERLAP // SCORE_SCALE:] - bottom_reference
            score += .7 * float(np.mean(difference * difference))
        scores.append(score)
    top_candidates = np.argpartition(np.asarray(scores), 12)[:12]
    choice = int(RNG.choice(sorted(top_candidates, key=lambda i: scores[i])))
    sx, sy = candidate_positions[choice]
    patch = source["Diffuse"][sy:sy + PATCH, sx:sx + PATCH]
    use_new = np.ones((PATCH, PATCH), dtype=bool)
    if left:
        cost = np.mean((patch[:, :OVERLAP].astype(np.float32) -
                        target[:, :OVERLAP].astype(np.float32)) ** 2, axis=2)
        seam = minimum_vertical_seam(cost)
        use_new[:, :OVERLAP] &= np.arange(OVERLAP)[None, :] >= seam[:, None]
    if top:
        cost = np.mean((patch[:OVERLAP].astype(np.float32) -
                        target[:OVERLAP].astype(np.float32)) ** 2, axis=2)
        seam = minimum_vertical_seam(cost.T)
        use_new[:OVERLAP] &= np.arange(OVERLAP)[:, None] >= seam[None, :]
    if row == 0 and col == 0:
        use_new[:] = True
    for key in CHANNELS:
        donor = source[key][sy:sy + PATCH, sx:sx + PATCH]
        if donor.ndim == 2:
            donor = donor[:, :, None]
        dest = canvases[key][y0:y0 + PATCH, x0:x0 + PATCH]
        dest[use_new] = donor[use_new]
    return {"row": row, "col": col, "source_xy_px_at_1024": [sx, sy],
            "overlap_px": OVERLAP, "edge_score": round(scores[choice], 3)}


patches = [stitch_one(row, col) for row in range(COUNT) for col in range(COUNT)]


def periodic_edge_finish(array: np.ndarray) -> np.ndarray:
    result = array[:SIDE, :SIDE].copy().astype(np.float32)
    # The wrap-aware patch choices minimize the outer mismatch. A narrow
    # 24-pixel paired feather makes the border exactly periodic for mipmaps.
    feather = 24
    for delta in range(feather):
        weight = .5 * (1 + np.cos(np.pi * delta / feather))
        left, right = result[:, delta].copy(), result[:, SIDE - 1 - delta].copy()
        middle = (left + right) * .5
        result[:, delta] = left * (1 - weight) + middle * weight
        result[:, SIDE - 1 - delta] = right * (1 - weight) + middle * weight
        top, bottom = result[delta].copy(), result[SIDE - 1 - delta].copy()
        middle = (top + bottom) * .5
        result[delta] = top * (1 - weight) + middle * weight
        result[SIDE - 1 - delta] = bottom * (1 - weight) + middle * weight
    if array.shape[2] == 3 and np.mean(array[:, :, 2]) > 225:
        # Re-normalize blended tangent-space normals, preserving DX green.
        tangent = result / 127.5 - 1.0
        tangent /= np.maximum(np.linalg.norm(tangent, axis=2, keepdims=True), 1e-6)
        result = (tangent + 1.0) * 127.5
    upper = 65535 if array.dtype == np.uint16 else 255
    return np.clip(result, 0, upper).astype(array.dtype)


outputs = {}
names = {"Diffuse": "T_NyaagyuPathQuilt_Albedo.jpg",
         "nor_dx": "T_NyaagyuPathQuilt_NormalDX.png",
         "arm": "T_NyaagyuPathQuilt_ARM.png",
         "disp": "T_NyaagyuPathQuilt_Height.png"}
for key in CHANNELS:
    image = periodic_edge_finish(canvases[key])
    if key == "disp":
        image = image[:, :, 0]
    target = OUT / names[key]
    if key == "Diffuse":
        Image.fromarray(image).save(target, quality=95, subsampling=0)
    elif key == "disp":
        Image.fromarray(image, mode="I;16").save(target, compress_level=6)
    else:
        Image.fromarray(image).save(target, compress_level=6)
    outputs[key] = {"file": names[key], "sha256": sha(target), "bytes": target.stat().st_size}

preview = OUT / "Nyaagyu_PathQuilt_Review.jpg"
Image.open(OUT / names["Diffuse"]).resize((1600, 1600), Image.Resampling.LANCZOS).save(preview, quality=93)
manifest = {
    "schema_version": 1,
    "generator": "scripts/art/build_nyaagyu_path_quilt.py",
    "generator_sha256": sha(ROOT / "scripts/art/build_nyaagyu_path_quilt.py"),
    "source_asset": "grey_stone_path", "source_url": RECORD["source_url"],
    "license": "CC0-1.0", "physical_size_cm": [720, 720],
    "texture_size_px": [SIDE, SIDE], "seed": SEED,
    "quilt": {"grid": [COUNT, COUNT], "patch_px": PATCH,
              "stride_px": STEP, "overlap_px": OVERLAP,
              "selection": "top 12 scan crops by color edge match; seeded choice; minimum-error seam",
              "registration": "all four channels use the exact same crop and seam mask; no rotations or mirrors"},
    "source_files": source_records, "patches": patches, "outputs": outputs,
    "review": {"file": preview.name, "sha256": sha(preview)},
    "limitations": "One licensed 1.8 m photograph synthesized into a larger 7.2 m atlas; some photographed stone identities recur, and final quality requires an eye-height packaged Unreal comparison. No collision, 5.8.2, Nanite, or performance claim.",
}
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("NYAAGYU_PATH_QUILT_CREATED", len(patches), outputs["Diffuse"]["bytes"])
