"""Create original tileable PBR maps for the Nyaagyu yumi museum study.

Run with python3. Inputs are deterministic mathematical surface fields, not
copies of photographs or scans. DirectX normal maps use a downward G axis.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Weapons/NyaagyuYumi/HistoricalStudy/Textures"
OUT.mkdir(parents=True, exist_ok=True)


def fractal_noise(size: int, seed: int, anisotropy: tuple[float, float]) -> np.ndarray:
    rng = np.random.default_rng(seed)
    value = np.zeros((size, size), np.float32)
    weights = (0.53, 0.27, 0.13, 0.07)
    for level, weight in enumerate(weights):
        cells_x = 6 * (2 ** level)
        cells_y = 6 * (2 ** level)
        grid = rng.normal(size=(cells_y, cells_x)).astype(np.float32)
        image = Image.fromarray(grid, mode="F").resize(
            (size, size), resample=Image.Resampling.BICUBIC
        )
        value += weight * np.asarray(image, dtype=np.float32)
    return value / max(0.001, float(np.std(value))) * anisotropy[0]


def save_maps(name: str, albedo: np.ndarray, height: np.ndarray,
              rough: np.ndarray, metal: np.ndarray) -> dict:
    h, w = height.shape
    assert albedo.shape == (h, w, 3)
    color = np.clip(np.round(albedo * 255), 0, 255).astype(np.uint8)
    dx = np.gradient(height, axis=1) * w * 0.007
    dy = np.gradient(height, axis=0) * h * 0.007
    nx, ny, nz = -dx, dy, np.ones_like(dx)
    length = np.sqrt(nx * nx + ny * ny + nz * nz)
    normal = np.stack((nx / length, ny / length, nz / length), axis=2)
    normal = np.clip(np.round((normal * 0.5 + 0.5) * 255), 0, 255).astype(np.uint8)
    orm = np.stack((np.full_like(rough, 0.98), rough, metal), axis=2)
    orm = np.clip(np.round(orm * 255), 0, 255).astype(np.uint8)
    files = {}
    for suffix, pixels in (("Albedo", color), ("NormalDX", normal), ("ORM", orm)):
        path = OUT / f"{name}_{suffix}.png"
        Image.fromarray(pixels, "RGB").save(path, optimize=True)
        files[suffix] = path.name
    return {"name": name, "resolution": [w, h], "files": files,
            "roughness_min_max": [round(float(rough.min()), 3), round(float(rough.max()), 3)],
            "metallic_min_max": [round(float(metal.min()), 3), round(float(metal.max()), 3)]}


N = 1024
yy, xx = np.mgrid[0:N, 0:N].astype(np.float32) / N
rng = np.random.default_rng(1935)
micro = rng.standard_normal((N, N)).astype(np.float32)
records = []

# Fibre directions follow the bow stave/arrow shaft's longitudinal UV axis.
fibres = (0.47 * np.sin(2 * np.pi * (xx * 46 + 0.09 * np.sin(yy * 7))) +
          0.24 * np.sin(2 * np.pi * (xx * 119 + yy * 1.2)) +
          0.12 * np.sin(2 * np.pi * (xx * 263 - yy * 4.5)))
nodes = np.maximum(0, np.cos(2 * np.pi * (yy * 6.8 + 0.08 * np.sin(xx * 15)))) ** 18
grain = fractal_noise(N, 714, (0.03, 0.03))
bamboo_h = 0.22 * fibres + 0.09 * nodes + grain + 0.009 * micro
bamboo_albedo = np.stack((0.52 + 0.06 * fibres - 0.11 * nodes + grain,
                          0.345 + 0.045 * fibres - 0.075 * nodes + grain * 0.75,
                          0.19 + 0.025 * fibres - 0.045 * nodes + grain * 0.45), axis=2)
bamboo_rough = np.clip(0.61 + 0.06 * fibres + 0.07 * nodes + grain, 0.43, 0.79)
records.append(save_maps("Bamboo", bamboo_albedo, bamboo_h, bamboo_rough,
                         np.zeros((N, N), np.float32)))

# Lacquer is a dielectric: the worn high spots reveal warm wood, never metal.
scuff = (np.sin(2 * np.pi * (xx * 24 + 0.02 * np.sin(yy * 33))) > .988).astype(np.float32)
scuff *= np.clip(0.30 + 0.8 * np.sin(yy * 87) ** 4, 0, 1)
lacquer_noise = fractal_noise(N, 711, (0.035, 0.035))
lacquer_h = 0.016 * np.sin(xx * 650) + 0.01 * micro + 0.035 * scuff + lacquer_noise * 0.35
lacquer_albedo = np.stack((0.052 + 0.035 * scuff + lacquer_noise * 0.22,
                           0.030 + 0.020 * scuff + lacquer_noise * 0.13,
                           0.025 + 0.012 * scuff + lacquer_noise * 0.10), axis=2)
lacquer_rough = np.clip(0.24 + 0.13 * scuff + 0.035 * micro + 0.35 * lacquer_noise, .16, .54)
records.append(save_maps("BlackLacquer", lacquer_albedo, lacquer_h,
                         lacquer_rough, np.zeros((N, N), np.float32)))

# Rattan face has longitudinal split-cane fibres and a softer, matte varnish.
rattan_fibre = (0.55 * np.sin(xx * 210 * 2 * np.pi + yy * 8) +
                0.24 * np.sin(xx * 520 * 2 * np.pi - yy * 11))
rattan_noise = fractal_noise(N, 710, (0.035, 0.035))
rattan_h = 0.08 * rattan_fibre + rattan_noise + micro * 0.007
rattan_albedo = np.stack((0.66 + 0.048 * rattan_fibre + rattan_noise,
                          0.47 + 0.035 * rattan_fibre + rattan_noise * .72,
                          0.27 + 0.021 * rattan_fibre + rattan_noise * .43), axis=2)
rattan_rough = np.clip(.68 + .045 * rattan_fibre + rattan_noise * .7, .56, .83)
records.append(save_maps("Rattan", rattan_albedo, rattan_h, rattan_rough,
                         np.zeros((N, N), np.float32)))

# Feather map is intentionally low contrast; geometric barbs carry the form.
barbs = np.sin(2 * np.pi * (yy * 118 + xx * 13))
band = np.sin(2 * np.pi * (yy * 8 + xx * 0.18))
feather_noise = fractal_noise(N, 717, (0.025, 0.025))
feather_h = .045 * barbs + feather_noise * .45 + .006 * micro
feather_albedo = np.stack((.25 + .055 * barbs + .11 * band + feather_noise,
                           .225 + .045 * barbs + .09 * band + feather_noise,
                           .19 + .035 * barbs + .07 * band + feather_noise), axis=2)
feather_rough = np.clip(.89 + .025 * barbs + feather_noise, .78, .98)
records.append(save_maps("Fletching", feather_albedo, feather_h, feather_rough,
                         np.zeros((N, N), np.float32)))

# Forged iron is the only metallic family in this study.
iron_noise = fractal_noise(N, 732, (0.04, 0.04))
brush = np.sin(xx * 540 * 2 * np.pi + yy * 3)
iron_h = .018 * brush + iron_noise * .25 + .006 * micro
iron_albedo = np.stack((.22 + iron_noise + .014 * brush,
                        .23 + iron_noise + .015 * brush,
                        .235 + iron_noise + .017 * brush), axis=2)
iron_rough = np.clip(.42 + iron_noise + .036 * brush, .3, .61)
records.append(save_maps("ForgedIron", iron_albedo, iron_h, iron_rough,
                         np.full((N, N), .9, np.float32)))

(OUT / "texture_manifest.json").write_text(json.dumps({
    "schema_version": 1,
    "license": "Original project-authored mathematical texture fields; no external pixels",
    "normal_convention": "DirectX/downward green",
    "orm_channels": {"R": "ambient occlusion", "G": "roughness", "B": "metallic"},
    "surfaces": records,
}, indent=2) + "\n")
print("YUMI_MAPS_BUILT", len(records), N)
