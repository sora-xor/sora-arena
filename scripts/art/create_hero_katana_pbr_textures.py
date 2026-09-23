"""Author tileable first-person surface detail for Nyaakoto's katana.

Run with the project Python before create_hero_katana.py.  These measured-in-
spirit microstructure maps complement the modeled blade, samegawa beads and ito;
they are not scans or a claim that the result is production photorealism.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / "Content/SourceArt/Weapons/HeroKatana/PBR"
DEST.mkdir(parents=True, exist_ok=True)
SIZE = 2048
SEED = 20051839


def blur(field: np.ndarray, radius: int, axis: int) -> np.ndarray:
    if radius == 0:
        return field
    padded = np.concatenate((np.take(field, range(-radius, 0), axis=axis),
                             field,
                             np.take(field, range(radius), axis=axis)), axis=axis)
    cumulative = np.concatenate((np.zeros_like(np.take(padded, [0], axis=axis)),
                                 np.cumsum(padded, axis=axis)), axis=axis)
    if axis == 0:
        return (cumulative[2 * radius + 1:] - cumulative[:-(2 * radius + 1)]) / (2 * radius + 1)
    return (cumulative[:, 2 * radius + 1:] - cumulative[:, :-(2 * radius + 1)]) / (2 * radius + 1)


def surface(kind: str, seed: int):
    rng = np.random.default_rng(seed)
    fine = rng.standard_normal((SIZE, SIZE), dtype=np.float32)
    broad = blur(blur(fine, 24, 0), 24, 1)
    if kind == "forged_steel":
        # Fine lengthwise polish and uneven but restrained hardening contrast.
        direction = blur(fine, 15, 1)
        height = .55 * direction + .07 * fine + 1.6 * broad
        color = .83 + .026 * direction + .035 * broad
        roughness = .235 + .030 * direction + .026 * broad
        metallic = 255
        normal_strength = .18
    elif kind == "patinated_metal":
        pits = np.clip(blur(fine, 2, 0), -1.5, 1.5)
        height = .26 * pits + 1.2 * broad
        color = .82 + .055 * pits + .035 * broad
        roughness = .43 + .055 * pits + .04 * broad
        metallic = 255
        normal_strength = .34
    elif kind == "woven_silk":
        coordinate = np.arange(SIZE, dtype=np.float32) * np.pi / 3
        warp = np.cos(coordinate)[None, :]
        weft = np.cos(coordinate)[:, None]
        height = .42 * warp + .28 * weft + .08 * fine + .35 * broad
        color = .83 + .052 * warp + .033 * weft + .02 * broad
        roughness = .65 + .025 * warp - .025 * weft
        metallic = 0
        normal_strength = .36
    elif kind == "ray_skin":
        # A material-scale relief below the separately modeled 0.7 mm nodules.
        yy, xx = np.indices((SIZE, SIZE), dtype=np.float32)
        yy /= 11.0
        xx = xx / 11.0 + .5 * (np.floor(yy).astype(np.int32) & 1)
        distance = np.sqrt((xx - np.round(xx)) ** 2 + (yy - np.round(yy)) ** 2)
        nodules = np.exp(-18.0 * distance * distance)
        height = .72 * nodules + .08 * fine + .5 * broad
        color = .79 + .08 * nodules + .03 * broad
        roughness = .73 - .06 * nodules + .025 * broad
        metallic = 0
        normal_strength = .31
    elif kind == "urushi":
        long_grain = blur(fine, 14, 1)
        height = .08 * long_grain + .2 * broad
        color = .88 + .015 * long_grain + .025 * broad
        roughness = .215 + .013 * long_grain + .018 * broad
        metallic = 0
        normal_strength = .075
    else:
        raise ValueError(kind)
    for field in (height, color, roughness):
        field[-1, :] = field[0, :]
        field[:, -1] = field[:, 0]
    dx = (np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1)) * .5
    dy = (np.roll(height, -1, axis=0) - np.roll(height, 1, axis=0)) * .5
    normal = np.stack((-dx * normal_strength, dy * normal_strength,
                       np.ones_like(height)), axis=2)
    normal /= np.linalg.norm(normal, axis=2, keepdims=True)
    normal_rgb = np.uint8(np.clip((normal * .5 + .5) * 255, 0, 255))
    normal_rgb[-1, :] = normal_rgb[0, :]
    normal_rgb[:, -1] = normal_rgb[:, 0]
    gray = np.uint8(np.clip(color * 255, 0, 255))
    albedo = np.repeat(gray[:, :, None], 3, axis=2)
    rough = np.uint8(np.clip(roughness * 255, 0, 255))
    orm = np.stack((np.full_like(rough, 255), rough,
                    np.full_like(rough, metallic)), axis=2)
    return albedo, normal_rgb, orm


def write_map(name: str, channel: str, pixels: np.ndarray):
    path = DEST / f"T_HeroKatana_{name}_{channel}.png"
    Image.fromarray(pixels, "RGB").save(path, optimize=True)
    return {"channel": channel, "file": path.name,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


sets = []
for index, name in enumerate(("forged_steel", "patinated_metal", "woven_silk",
                              "ray_skin", "urushi")):
    pixels = surface(name, SEED + index * 1039)
    sets.append({"name": name, "resolution": [SIZE, SIZE], "maps": [
        write_map(name, channel, image) for channel, image in
        zip(("Albedo", "NormalDX", "ORM"), pixels)
    ]})
neutral = np.full((4, 4, 3), 255, np.uint8)
flat = neutral.copy()
flat[:] = (128, 128, 255)
dielectric = neutral.copy()
dielectric[:, :, 1] = 128
dielectric[:, :, 2] = 0
sets.append({"name": "neutral", "resolution": [4, 4], "maps": [
    write_map("neutral", "Albedo", neutral),
    write_map("neutral", "NormalDX", flat),
    write_map("neutral", "ORM", dielectric),
]})

# Linear-color tints retain the source art's subdued forged steel, indigo and
# black urushi palette.  The actual physical detail comes from the maps above.
slots = {
    "M_HK_Tamahagane_Polished": ("forged_steel", (.37, .43, .47), .94, 1.0),
    "M_HK_Ha_BrightSteel": ("forged_steel", (.62, .66, .67), .67, 1.0),
    "M_HK_Hamon_FrostedSteel": ("forged_steel", (.47, .50, .51), 1.55, 1.0),
    "M_HK_Mune_BrushedSteel": ("forged_steel", (.22, .26, .28), 1.36, 1.0),
    "M_HK_PatinatedIron": ("patinated_metal", (.070, .072, .069), 1.0, .94),
    "M_HK_AgedBrass": ("patinated_metal", (.43, .30, .12), .80, .94),
    "M_HK_BuffaloHorn": ("urushi", (.025, .026, .025), 1.35, 0.0),
    "M_HK_RaySkin_Ivory": ("ray_skin", (.34, .32, .25), 1.0, 0.0),
    "M_HK_IndigoIto": ("woven_silk", (.031, .052, .069), 1.0, 0.0),
    "M_HK_Urushi_BlackBrown": ("urushi", (.024, .017, .013), 1.0, 0.0),
    "M_HK_Sageo_Silk": ("woven_silk", (.08, .085, .08), 1.05, 0.0),
    "M_HK_Induction_Inlay": ("neutral", (.018, .31, .29), .46, 0.0),
}
manifest = {"schema_version": 1,
            "generator": "scripts/art/create_hero_katana_pbr_textures.py",
            "license": "Original project-owned procedural surface maps; no third-party texture data",
            "seed": SEED,
            "maps": sets,
            "material_slots": {name: {"surface": surface, "tint": tint,
                                      "roughness_scale": rough,
                                      "metallic_scale": metal}
                               for name, (surface, tint, rough, metal) in slots.items()}}
(DEST / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("HERO_KATANA_PBR_READY", len(sets), len(slots))
