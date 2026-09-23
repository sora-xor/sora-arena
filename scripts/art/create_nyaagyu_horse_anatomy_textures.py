"""Make project-owned PBR study maps from the existing licensed horse swatch.

This is authored texture work, not measured photogrammetry. Run with python3.
The albedo contains no baked lighting; NormalDX uses the DirectX Y convention;
ORM is occlusion, roughness, metallic in R/G/B.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Horses/Nyaagyu/AnatomyStudy"
BASE = ROOT / "Content/SourceArt/Horses/Nyaagyu/PBR"
OUT.mkdir(parents=True, exist_ok=True)
SIZE = 2048
RNG = np.random.default_rng(0x5A0A2026)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def exact_wrap(array: np.ndarray) -> np.ndarray:
    array = array.copy()
    array[0] = array[-1] = (array[0].astype(np.float32) + array[-1].astype(np.float32)) * .5
    array[:, 0] = array[:, -1] = (array[:, 0].astype(np.float32) + array[:, -1].astype(np.float32)) * .5
    return array


def periodic_noise(low_size: int) -> np.ndarray:
    low = RNG.standard_normal((low_size, low_size)).astype(np.float32)
    low[0] = low[-1] = (low[0] + low[-1]) * .5
    low[:, 0] = low[:, -1] = (low[:, 0] + low[:, -1]) * .5
    image = Image.fromarray(low, "F")
    return np.asarray(image.resize((SIZE, SIZE), Image.Resampling.BICUBIC), dtype=np.float32)


def save_set(name: str, albedo: np.ndarray, height: np.ndarray, roughness: np.ndarray,
             metallic: float, normal_strength: float) -> list[dict]:
    albedo = exact_wrap(np.clip(albedo, 0, 1))
    height = exact_wrap(height)
    roughness = exact_wrap(np.clip(roughness, .03, 1))
    dx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * .5
    dy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * .5
    normal = np.stack((-dx * normal_strength, dy * normal_strength,
                       np.ones_like(dx)), axis=2)
    normal /= np.linalg.norm(normal, axis=2, keepdims=True)
    normal = exact_wrap(normal * .5 + .5)
    ao = np.clip(1 - np.maximum(-height, 0) * .15, .6, 1)
    orm = np.stack((ao, roughness, np.full_like(ao, metallic)), axis=2)
    orm = exact_wrap(orm)
    files = []
    for channel, arr in (("Albedo", albedo), ("NormalDX", normal), ("ORM", orm)):
        path = OUT / f"T_Nyaagyu_{name}_{channel}.png"
        Image.fromarray(np.uint8(np.clip(arr * 255 + .5, 0, 255)), "RGB").save(path, optimize=True)
        files.append({"channel": channel, "file": path.name, "sha256": digest(path), "resolution": [SIZE, SIZE]})
    return files


base_path = BASE / "T_Nyaagyu_horse_coat_Albedo.png"
base = np.asarray(Image.open(base_path).convert("RGB"), dtype=np.float32) / 255
assert base.shape == (SIZE, SIZE, 3)
yy, xx = np.mgrid[:SIZE, :SIZE].astype(np.float32)
fine = periodic_noise(256)
medium = periodic_noise(54)
broad = periodic_noise(12)
streak = np.sin(xx * .59 + .09 * medium + 3.1 * np.sin(yy * .015))
coat_factor = np.clip(.965 + .027 * broad + .013 * medium + .010 * streak, .88, 1.06)
coat_color = base * coat_factor[:, :, None]
coat_lum = np.dot(base, np.array([.2126, .7152, .0722], dtype=np.float32))
coat_height = .19 * (coat_lum - coat_lum.mean()) + .025 * fine + .016 * streak
coat_rough = np.clip(.77 + .027 * medium + .016 * fine, .69, .85)

hoof_broad = periodic_noise(21)
hoof_fine = periodic_noise(225)
hoof_ridge = np.sin(xx * .047 + 1.5 * hoof_broad)
horn = np.empty((SIZE, SIZE, 3), dtype=np.float32)
for channel, value in enumerate((.075, .052, .038)):
    horn[:, :, channel] = value * np.clip(1 + .19 * hoof_broad + .08 * hoof_fine + .12 * hoof_ridge, .65, 1.45)
horn_height = .12 * hoof_ridge + .042 * hoof_broad + .018 * hoof_fine
horn_rough = np.clip(.64 + .045 * hoof_broad + .025 * hoof_fine, .54, .76)

lacquer_broad = periodic_noise(32)
lacquer_fine = periodic_noise(350)
lacquer_color = np.empty((SIZE, SIZE, 3), dtype=np.float32)
for channel, value in enumerate((.060, .020, .019)):
    lacquer_color[:, :, channel] = value * np.clip(1 + .095 * lacquer_broad + .015 * lacquer_fine, .78, 1.22)
lacquer_height = .008 * lacquer_broad + .003 * lacquer_fine
lacquer_rough = np.clip(.265 + .035 * lacquer_broad + .013 * lacquer_fine, .20, .35)

sets = {
    "coat_study": save_set("coat_study", coat_color, coat_height, coat_rough, 0.0, 2.3),
    "hoof_horn_study": save_set("hoof_horn_study", horn, horn_height, horn_rough, 0.0, 2.1),
    "oxblood_urushi_study": save_set("oxblood_urushi_study", lacquer_color, lacquer_height,
                                     lacquer_rough, 0.0, 1.25),
}
record = {
    "schema_version": 1,
    "generator": "scripts/art/create_nyaagyu_horse_anatomy_textures.py",
    "base_coat_albedo": "Content/SourceArt/Horses/Nyaagyu/PBR/" + base_path.name,
    "base_coat_albedo_sha256": digest(base_path),
    "provenance": "Original project-authored variation over a first-party image-generation coat swatch; procedural horn and lacquer maps. No museum photograph or third-party texture copied.",
    "sets": sets,
    "limitations": "Artist-estimated surface maps; not calibrated scans or directional-groom capture. PBR response requires review under neutral HDRI and UE project lighting.",
}
(OUT / "textures_manifest.json").write_text(json.dumps(record, indent=2) + "\n")
print("NYAAGYU_ANATOMY_TEXTURES_READY", sum(len(v) for v in sets.values()))
