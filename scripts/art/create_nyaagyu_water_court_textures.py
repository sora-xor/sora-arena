"""Make original, deterministic bamboo PBR maps for the Nyaagyu water court.

The geometry and these pixels are project-authored. Pinned photographic scans
for its wood, stone, and tile materials are separately listed in manifest.json.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Environment/NyaagyuWaterCourt/Textures"
OUT.mkdir(parents=True, exist_ok=True)
SIZE = 2048
RNG = np.random.default_rng(0xE0D051)


def smooth_noise(width: int, height: int, cells_x: int, cells_y: int) -> np.ndarray:
    small = RNG.integers(0, 256, (cells_y, cells_x), dtype=np.uint8)
    image = Image.fromarray(small, "L").resize((width, height), Image.Resampling.BICUBIC)
    return np.asarray(image, dtype=np.float32) / 255.0 - 0.5


def save_rgb(name: str, data: np.ndarray) -> None:
    image = Image.fromarray(np.uint8(np.clip(data, 0, 255)), "RGB")
    image.save(OUT / name, optimize=True)


def normal_dx(height: np.ndarray, amount: float) -> np.ndarray:
    dx = np.gradient(height, axis=1) * amount
    dy = np.gradient(height, axis=0) * amount
    vec = np.stack((-dx, dy, np.ones_like(height)), axis=-1)
    vec /= np.maximum(np.linalg.norm(vec, axis=-1, keepdims=True), 1e-6)
    return (vec * 0.5 + 0.5) * 255


def bamboo_culm() -> None:
    w = h = SIZE
    xx = np.linspace(0, 1, w, dtype=np.float32)[None, :]
    yy = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    fibers = (np.sin(xx * 510 + np.sin(yy * 17) * 0.7) * 0.035
              + np.sin(xx * 1730 + yy * 9) * 0.014)
    long_color = smooth_noise(w, h, 140, 5) * .16
    large_color = smooth_noise(w, h, 13, 17) * .24
    specks = smooth_noise(w, h, 290, 310) * .052
    vertical_age = np.clip((yy - .55) * .20, 0, .12)
    strand = fibers + long_color + large_color + specks
    red = 111 + strand * 63 + vertical_age * 45
    green = 119 + strand * 59 - vertical_age * 69
    blue = 62 + strand * 42 - vertical_age * 67
    albedo = np.stack(np.broadcast_arrays(red, green, blue), axis=-1)
    save_rgb("T_WaterCourt_BambooCulm_Albedo.png", albedo)

    height = (smooth_noise(w, h, 410, 11) * .2
              + np.sin(xx * 560 + yy * 11) * .015
              + smooth_noise(w, h, 54, 63) * .045)
    save_rgb("T_WaterCourt_BambooCulm_NormalDX.png", normal_dx(height, 5.3))
    rough = 175 + long_color * 25 + specks * 20 + yy * 14
    orm = np.stack(np.broadcast_arrays(np.full_like(rough, 255), rough,
                                        np.zeros_like(rough)), axis=-1)
    save_rgb("T_WaterCourt_BambooCulm_ORM.png", orm)


def bamboo_leaf() -> None:
    w = h = SIZE
    xx = np.linspace(0, 1, w, dtype=np.float32)[None, :]
    yy = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    panel = np.minimum((xx * 4).astype(np.int32), 3)
    across = xx * 4 - panel
    palette = np.array([[55, 86, 42], [76, 94, 43],
                        [105, 108, 53], [87, 78, 43]], dtype=np.float32)
    base = palette[panel]
    grain = (smooth_noise(w, h, 100, 15) * 13
             + smooth_noise(w, h, 340, 128) * 6)
    central_vein = np.exp(-((across - .5) / .013) ** 2) * 16
    side_veins = np.sin((yy * 43 + across * 22) * np.pi) * 2.5
    # Deliberately subdued chlorophyll color: the court lives in overcast,
    # damp shade, and a saturated emerald canopy would look painted.
    albedo = base + grain[..., None] + central_vein[..., None] + side_veins[..., None]
    albedo[..., 2] -= 2.5 * yy
    save_rgb("T_WaterCourt_BambooLeaf_Albedo.png", albedo)
    height = central_vein * .004 + side_veins * .008 + smooth_noise(w, h, 320, 370) * .016
    save_rgb("T_WaterCourt_BambooLeaf_NormalDX.png", normal_dx(height, 3.3))
    rough = 178 + smooth_noise(w, h, 37, 28) * 15 + yy * 11
    orm = np.stack(np.broadcast_arrays(np.full_like(rough, 255), rough,
                                        np.zeros_like(rough)), axis=-1)
    save_rgb("T_WaterCourt_BambooLeaf_ORM.png", orm)


if __name__ == "__main__":
    bamboo_culm()
    bamboo_leaf()
    print("WATER_COURT_TEXTURES_READY", OUT)
