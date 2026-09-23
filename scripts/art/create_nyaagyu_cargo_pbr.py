"""Create deterministic project-original PBR surfaces for Estate cargo.

These are authored procedural textures, not photographs or material scans.
Run: python3 scripts/art/create_nyaagyu_cargo_pbr.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Environment/NyaagyuCargoStack"
PBR = OUT / "PBR"
PBR.mkdir(parents=True, exist_ok=True)
SIZE = 2048
SEED = 416819


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def wrap_exact(pixels: np.ndarray) -> np.ndarray:
    pixels = pixels.copy()
    edge = ((pixels[0].astype(np.uint16) + pixels[-1].astype(np.uint16)) // 2).astype(np.uint8)
    pixels[0] = edge
    pixels[-1] = edge
    edge = ((pixels[:, 0].astype(np.uint16) + pixels[:, -1].astype(np.uint16)) // 2).astype(np.uint8)
    pixels[:, 0] = edge
    pixels[:, -1] = edge
    return pixels


def save(name: str, kind: str, pixels: np.ndarray) -> dict:
    path = PBR / f"T_NyaagyuCargo_{name}_{kind}.png"
    Image.fromarray(wrap_exact(np.uint8(np.clip(pixels, 0, 255))), "RGB").save(path, optimize=True)
    return {"channel": kind, "file": path.name, "sha256": sha(path)}


def maps(name: str, base_rgb, color_relief, height, roughness, metallic):
    albedo = np.clip(np.asarray(base_rgb, np.float32)[None, None, :] + color_relief, 0, 255)
    dx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * .5
    dy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * .5
    normal = np.stack((-dx * 2.4, dy * 2.4, np.ones_like(dx)), 2)
    normal /= np.linalg.norm(normal, axis=2, keepdims=True)
    normal = (normal * .5 + .5) * 255
    ao = np.clip(251 - np.maximum(-height, 0) * 11, 220, 255)
    rough = np.clip((roughness + height * -.035) * 255, 0, 255)
    metal = np.full_like(rough, round(metallic * 255))
    orm = np.stack((ao, rough, metal), 2)
    return {"name": name, "resolution": [SIZE, SIZE], "roughness": roughness,
            "metallic": metallic,
            "maps": [save(name, "Albedo", albedo), save(name, "NormalDX", normal),
                     save(name, "ORM", orm)]}


u = np.arange(SIZE, dtype=np.float32)[None, :] / SIZE
v = np.arange(SIZE, dtype=np.float32)[:, None] / SIZE
rng = np.random.default_rng(SEED)

# Long, gently wavering grain: darker pores run along plank length. Distinct
# broad and fine streaks keep boards legible in a first-person close view.
wood_warp = .011 * np.sin(2 * np.pi * (u * 3 + v * 2)) + .003 * np.sin(2 * np.pi * u * 13)
wood_grain = np.sin(2 * np.pi * (v * 37 + wood_warp))
wood_fine = np.sin(2 * np.pi * (v * 217 + wood_warp * 3))
wood_tonal = 11 * np.sin(2 * np.pi * (v * 5 + u * .5)) + 6 * np.sin(2 * np.pi * u * 7)
wood_pores = rng.normal(0, 2.1, (SIZE, SIZE)).astype(np.float32)
wood_height = .075 * wood_grain + .026 * wood_fine + .006 * wood_pores
wood_relief = (wood_tonal + 8 * wood_grain + 2.3 * wood_fine + wood_pores)[:, :, None]
wood_relief = wood_relief * np.array([1.0, .83, .56], np.float32)
wood = maps("Wood", [118, 78, 45], wood_relief, wood_height, .74, 0)
del wood_warp, wood_grain, wood_fine, wood_tonal, wood_pores, wood_height, wood_relief

# Coarse rice-straw weave. Crossing warp and weft is visible without baked
# directional lighting; roughness is high and the normal relief stays subtle.
straw_warp = np.sin(2 * np.pi * (u * 94 + .006 * np.sin(2 * np.pi * v * 11)))
straw_weft = np.sin(2 * np.pi * (v * 98 + .005 * np.sin(2 * np.pi * u * 9)))
straw_weave = straw_warp * straw_weft
straw_mottle = 6 * np.sin(2 * np.pi * (u * 7 + v * 4)) + 4 * np.sin(2 * np.pi * (u * 13 - v * 5))
straw_height = .048 * straw_warp + .048 * straw_weft + .029 * straw_weave
straw_relief = (straw_mottle + 9 * straw_weave + 3 * straw_warp)[:, :, None]
straw_relief = straw_relief * np.array([1.0, .89, .68], np.float32)
straw = maps("Straw", [158, 132, 82], straw_relief, straw_height, .91, 0)
del straw_warp, straw_weft, straw_weave, straw_mottle, straw_height, straw_relief

# Dyed cotton bundles use a finer interlaced weave and nonuniform indigo dye.
cloth_warp = np.sin(2 * np.pi * u * 177)
cloth_weft = np.sin(2 * np.pi * v * 183)
cloth_weave = cloth_warp * cloth_weft
cloth_dye = 5 * np.sin(2 * np.pi * (u * 4 + v * 3)) + 4 * np.sin(2 * np.pi * (u * 8 - v * 2))
cloth_height = .025 * cloth_warp + .025 * cloth_weft + .02 * cloth_weave
cloth_relief = (cloth_dye + 4 * cloth_weave)[:, :, None]
cloth_relief = cloth_relief * np.array([.65, .90, 1.2], np.float32)
cloth = maps("IndigoCloth", [38, 55, 80], cloth_relief, cloth_height, .83, 0)

record = {
    "schema_version": 1,
    "generator": "scripts/art/create_nyaagyu_cargo_pbr.py",
    "generator_sha256": sha(Path(__file__)),
    "origin": "Original project-authored deterministic procedural pixels; no external texture inputs",
    "license": "Original project-owned procedural texture output; no third-party image or paid asset",
    "seed": SEED,
    "sets": [wood, straw, cloth],
    "material_slots": {
        "M_Cargo_AgedTimber": {"surface": "Wood", "tint": [1, 1, 1]},
        "M_Cargo_DarkInterior": {"surface": "Wood", "tint": [.42, .42, .42]},
        "M_Cargo_WornEdge": {"surface": "Wood", "tint": [1.21, 1.17, 1.08]},
        "M_Cargo_StrawWrap": {"surface": "Straw", "tint": [1, 1, 1]},
        "M_Cargo_HempRope": {"surface": "Straw", "tint": [.77, .72, .62]},
        "M_Cargo_IndigoCloth": {"surface": "IndigoCloth", "tint": [1, 1, 1]},
    },
    "limitations": "Authored procedural maps are not measured scans. Normal and roughness response are art estimates; no actual fiber geometry is baked into these maps.",
}
(PBR / "manifest.json").write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
print("NYAAGYU_CARGO_PBR_CREATED", len(record["sets"]), len(record["material_slots"]))
