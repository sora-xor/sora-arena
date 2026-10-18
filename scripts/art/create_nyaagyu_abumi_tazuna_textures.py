"""Generate deterministic, original 2K PBR maps for the abumi/tazuna study.

Run from the repository root before create_nyaagyu_abumi_tazuna_study.py.
Every texture is generated here; museum photographs are references only.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Horses/NyaagyuAbumiTazunaStudy"
OUT.mkdir(parents=True, exist_ok=True)
SIZE = 2048


def multiscale(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    field = np.zeros((SIZE, SIZE), np.float32)
    for grid, amount in ((16, 0.33), (64, 0.28), (256, 0.19), (1024, 0.12)):
        small = rng.integers(0, 256, (grid, grid), dtype=np.uint8)
        up = Image.fromarray(small, "L").resize((SIZE, SIZE), Image.Resampling.BICUBIC)
        field += (np.asarray(up, np.float32) / 255.0 - 0.5) * amount
    field += (rng.random((SIZE, SIZE), dtype=np.float32) - 0.5) * 0.07
    return field


def save_rgb(name: str, value: np.ndarray) -> dict[str, str]:
    path = OUT / name
    Image.fromarray(np.clip(value, 0, 255).astype(np.uint8), "RGB").save(path, optimize=True)
    return {"file": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def maps(label: str, base: tuple[int, int, int], roughness: int,
         metallic: int, seed: int, height_scale: float, texture_kind: str):
    h = multiscale(seed)
    yy, xx = np.mgrid[0:SIZE, 0:SIZE]
    if texture_kind == "lacquer":
        # Broad, low-amplitude handmade lacquer undulation, no baked lighting.
        height = h * 0.28 + 0.07 * np.sin(xx / 37 + 0.4 * np.sin(yy / 120))
        chroma = h * 19
        rough = roughness + h * 22
    elif texture_kind == "iron":
        # Hammer-finished iron: shallow directionless peening and oxidized pores.
        height = h * 0.8 + 0.11 * np.sin(xx / 11) * np.sin(yy / 14)
        chroma = h * 36
        rough = roughness + h * 50
    elif texture_kind == "leather":
        # Long grain and fine pores; wrinkles are left to the geometry.
        height = h * 0.67 + 0.08 * np.sin(yy / 4 + np.sin(xx / 75))
        chroma = h * 32
        rough = roughness + h * 32
    else:
        # Interlaced silk/grip braid; modest specularity from fibre direction.
        weave = 0.5 * np.sin(xx * np.pi / 5) * np.sin(yy * np.pi / 7)
        height = h * 0.35 + weave * 0.12
        chroma = h * 22 + weave * 6
        rough = roughness + h * 22

    albedo = np.stack([base[c] + chroma * (1.0 if c == 0 else 0.8)
                       for c in range(3)], axis=2)
    orm = np.empty((SIZE, SIZE, 3), np.float32)
    orm[:, :, 0] = 255  # AO belongs to geometry/lighting, not invented in albedo.
    orm[:, :, 1] = rough
    orm[:, :, 2] = metallic

    dy, dx = np.gradient(height)
    normal = np.stack((128 - dx * height_scale,
                       128 + dy * height_scale,
                       np.full_like(height, 255)), axis=2)
    return [save_rgb(f"T_Nyaagyu_{label}_Albedo.png", albedo),
            save_rgb(f"T_Nyaagyu_{label}_ORM.png", orm),
            save_rgb(f"T_Nyaagyu_{label}_NormalDX.png", normal)]


sets = {
    "black_urushi": maps("black_urushi", (27, 24, 22), 64, 0, 7101, 5, "lacquer"),
    "red_urushi": maps("red_urushi", (103, 31, 24), 76, 0, 7102, 5, "lacquer"),
    "forged_iron": maps("forged_iron", (60, 62, 61), 118, 215, 7103, 12, "iron"),
    "oiled_leather": maps("oiled_leather", (79, 46, 31), 154, 0, 7104, 11, "leather"),
    "braided_silk": maps("braided_silk", (106, 66, 46), 169, 0, 7105, 10, "silk"),
}
manifest = {
    "schema_version": 1,
    "generator": "scripts/art/create_nyaagyu_abumi_tazuna_textures.py",
    "resolution": [SIZE, SIZE],
    "normal_convention": "DirectX; green channel is negative V",
    "orm_channels": "R=ambient occlusion, G=roughness, B=metallic",
    "sets": sets,
    "method": "Deterministic first-party procedural material estimates; no museum imagery or purchased texture used.",
    "qualification": "Source-art estimate, not measured BRDF or certified scanned material.",
}
(OUT / "textures_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(f"wrote {sum(map(len, sets.values()))} maps to {OUT}")
