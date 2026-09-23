"""Author a reproducible, project-owned lacquer PBR study for Nyaakoto's dō.

The maps are an art study, not scans or a claim that the armor is finished.
Run from the repository root before create_nyaakoto_do_study.py.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Characters/NyaakotoDoStudy"
OUT.mkdir(parents=True, exist_ok=True)
SIZE = 2048
RNG = np.random.default_rng(648861)


def octave_noise(shape: tuple[int, int], coarse: int, octaves: int) -> np.ndarray:
    result = np.zeros(shape, np.float32)
    weight = 1.0
    total = 0.0
    for index in range(octaves):
        span = coarse * (2**index)
        grid = RNG.random((span, span), dtype=np.float32)
        layer = np.asarray(
            Image.fromarray(np.uint8(grid * 255), "L").resize(
                (shape[1], shape[0]), Image.Resampling.BICUBIC
            ),
            dtype=np.float32,
        ) / 255.0
        result += layer * weight
        total += weight
        weight *= 0.52
    return result / total


def save_rgb(name: str, array: np.ndarray) -> Path:
    path = OUT / name
    Image.fromarray(np.uint8(np.clip(array, 0, 255)), "RGB").save(path)
    return path


yy, xx = np.mgrid[:SIZE, :SIZE].astype(np.float32)
u, v = xx / (SIZE - 1), yy / (SIZE - 1)
macro = octave_noise((SIZE, SIZE), 6, 5) - 0.5
micro = octave_noise((SIZE, SIZE), 70, 3) - 0.5
scuffs = np.zeros((SIZE, SIZE), dtype=np.uint8)
scuff_im = Image.fromarray(scuffs, "L")
draw = ImageDraw.Draw(scuff_im)
for _ in range(3300):
    x = int(RNG.integers(0, SIZE))
    y = int(RNG.integers(0, SIZE))
    length = int(RNG.integers(2, 28))
    draw.line((x, y, min(SIZE - 1, x + length), y + int(RNG.integers(-2, 3))), fill=int(RNG.integers(18, 80)), width=1)
scuffs = np.asarray(scuff_im, dtype=np.float32) / 255.0

# Seven UV rows correspond to the overlapping horizontal plates. Wear stays
# close to each physical upper/lower hem, while the broad face remains lacquer.
within_band = np.mod(v * 7.0, 1.0)
edge = np.exp(-((within_band - 0.045) / 0.038) ** 2) + np.exp(-((within_band - 0.955) / 0.033) ** 2)
edge *= np.clip(0.55 + 0.9 * macro + 0.5 * micro, 0.1, 1.0)
crack = np.clip((micro - 0.11) * 2.2, 0, 0.42)
albedo = np.empty((SIZE, SIZE, 3), np.float32)
for channel, base in enumerate((27.0, 29.0, 35.0)):
    albedo[..., channel] = base + macro * (10.0 if channel < 2 else 13.0) + micro * 8.0
albedo += edge[..., None] * np.array([29.0, 18.0, 10.0], np.float32)
albedo += scuffs[..., None] * np.array([48.0, 38.0, 25.0], np.float32)
albedo += crack[..., None] * np.array([12.0, 3.0, 2.0], np.float32)
albedo_path = save_rgb("T_Nyaakoto_Do_Lacquer_Albedo.png", albedo)

# Height gradients supply a restrained DirectX tangent normal. The sculpted
# plate camber and rolled rims remain geometric instead of being painted here.
height = macro * 0.20 + micro * 0.23 + scuffs * 0.08 - edge * 0.09
dy, dx = np.gradient(height)
nx = -dx * 8.0
ny = dy * 8.0  # DirectX green convention
nz = np.ones_like(nx)
norm = np.sqrt(nx * nx + ny * ny + nz * nz)
normal = np.stack(((nx / norm + 1) * 127.5, (ny / norm + 1) * 127.5, (nz / norm + 1) * 127.5), axis=-1)
normal_path = save_rgb("T_Nyaakoto_Do_Lacquer_NormalDX.png", normal)

roughness = np.clip(0.34 + 0.20 * np.abs(macro) + 0.12 * edge + scuffs * 0.28 + micro * 0.06, 0.24, 0.75)
orm = np.stack((np.full_like(roughness, 255), roughness * 255, np.zeros_like(roughness)), axis=-1)
orm_path = save_rgb("T_Nyaakoto_Do_Lacquer_ORM.png", orm)

manifest = {
    "schema_version": 1,
    "license": "Project-owned original procedural texture study; no third-party bitmap input",
    "resolution_px": [SIZE, SIZE],
    "normal_convention": "DirectX",
    "orm_channels": {"r": "occlusion", "g": "roughness", "b": "metallic"},
    "files": [
        {"file": p.name, "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size}
        for p in (albedo_path, normal_path, orm_path)
    ],
}
(OUT / "texture_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("NYAAKOTO_DO_TEXTURES_READY", json.dumps({"resolution": SIZE, "files": [p.name for p in (albedo_path, normal_path, orm_path)]}))
