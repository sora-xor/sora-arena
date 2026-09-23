"""Make project-owned, tileable Nyaakoto surface maps for the Unreal skin.

The fibers and weave are authored as deterministic height/color fields, then
converted to albedo, DirectX tangent normal, and AO/roughness/metallic maps.
They are material detail maps, not a substitute for groomed fur or sculpting.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / "Content/SourceArt/Characters/Hero/PBR"
DEST.mkdir(parents=True, exist_ok=True)
SIZE = 2048
SEED = 270426


def periodic_blur(field: np.ndarray, radius: int, axis: int) -> np.ndarray:
    if axis == 0:
        padded = np.concatenate((field[-radius:], field, field[:radius]), axis=0)
        total = np.concatenate((np.zeros_like(padded[:1]), np.cumsum(padded, axis=0)), axis=0)
        return (total[2 * radius + 1:] - total[:-(2 * radius + 1)]) / (2 * radius + 1)
    padded = np.concatenate((field[:, -radius:], field, field[:, :radius]), axis=1)
    total = np.concatenate((np.zeros_like(padded[:, :1]), np.cumsum(padded, axis=1)), axis=1)
    return (total[:, 2 * radius + 1:] - total[:, :-(2 * radius + 1)]) / (2 * radius + 1)


def map_fields(kind: str, seed: int):
    rng = np.random.default_rng(seed)
    noise = rng.standard_normal((SIZE, SIZE), dtype=np.float32)
    broad = rng.standard_normal((SIZE, SIZE), dtype=np.float32)
    for _ in range(3):
        broad = periodic_blur(periodic_blur(broad, 7, 0), 7, 1)
    if kind.startswith("fur_"):
        # Closely spaced directional shafts with broad coat variation. The
        # separated dark tabby stripes remain modeled geometry on the face.
        fiber = periodic_blur(noise, 10, 0)
        fiber += .38 * periodic_blur(np.roll(noise, 17, 1), 4, 0)
        height = fiber * .65 + broad * 2.4
        roughness = {"fur_grey": .87, "fur_white": .91, "fur_charcoal": .89}[kind]
        color = .88 + np.clip(height, -.7, .7) * .12
    elif kind == "silk_indigo":
        line = np.arange(SIZE, dtype=np.float32) * np.pi * 2 / 8
        warp = np.cos(line)[None, :]
        weft = np.cos(line)[:, None]
        height = .35 * warp + .35 * weft + .08 * noise + broad
        roughness = .58
        color = .84 + .055 * warp + .045 * weft + np.clip(broad, -.4, .4) * .13
    elif kind == "lacquer_oxblood":
        grain = periodic_blur(noise, 2, 1)
        height = grain * .16 + broad * .38
        roughness = .26
        color = .88 + np.clip(broad, -.4, .4) * .05 + grain * .014
    else:
        raise ValueError(kind)
    # Enforce exact texel agreement at the wrap boundaries in each channel.
    color[-1] = color[0]
    color[:, -1] = color[:, 0]
    height[-1] = height[0]
    height[:, -1] = height[:, 0]
    dx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * .5
    dy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * .5
    normal = np.stack((-dx * .24, dy * .24, np.ones_like(dx)), 2)
    normal /= np.linalg.norm(normal, axis=2, keepdims=True)
    normal_rgb = np.uint8(np.clip((normal * .5 + .5) * 255, 0, 255))
    normal_rgb[-1] = normal_rgb[0]
    normal_rgb[:, -1] = normal_rgb[:, 0]
    albedo = np.uint8(np.clip(color * 255, 0, 255))
    albedo_rgb = np.repeat(albedo[:, :, None], 3, 2)
    varied_rough = np.uint8(np.clip((roughness + np.clip(height, -.5, .5) * .045) * 255, 0, 255))
    orm = np.stack((np.full_like(varied_rough, 255), varied_rough,
                    np.zeros_like(varied_rough)), 2)
    return albedo_rgb, normal_rgb, orm


def save(name: str, channel: str, pixels: np.ndarray):
    path = DEST / f"T_Nyaakoto_{name}_{channel}.png"
    Image.fromarray(pixels, "RGB").save(path, optimize=True)
    return {"channel": channel, "file": path.name,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


profiles = ["fur_grey", "fur_white", "fur_charcoal", "silk_indigo", "lacquer_oxblood"]
sets = []
for index, kind in enumerate(profiles):
    albedo, normal, orm = map_fields(kind, SEED + index * 377)
    sets.append({"name": kind, "resolution": [SIZE, SIZE],
                 "maps": [save(kind, "Albedo", albedo), save(kind, "NormalDX", normal),
                          save(kind, "ORM", orm)]})

neutral = np.full((4, 4, 3), 255, dtype=np.uint8)
flat_normal = np.empty_like(neutral)
flat_normal[:] = (128, 128, 255)
sets.append({"name": "neutral", "resolution": [4, 4],
             "maps": [save("neutral", "Albedo", neutral),
                      save("neutral", "NormalDX", flat_normal),
                      save("neutral", "ORM", neutral)]})

# Each imported FBX slot is assigned a physically distinct surface. These are
# linear tint values; the texture maps carry microstructure and roughness.
slots = {
    "AgedBrass": ("neutral", (.43, .25, .093), .32, .89),
    "BambooArrowShaft": ("neutral", (.48, .32, .17), .72, 0),
    "BlackenedIron": ("neutral", (.052, .057, .06), .35, .9),
    "BlackUrushi": ("lacquer_oxblood", (.022, .021, .021), .95, 0),
    "BlueEye": ("neutral", (.095, .35, .64), .15, 0),
    "CharcoalStripeFur": ("fur_charcoal", (.045, .053, .063), 1, 0),
    "EarSkin": ("neutral", (.4, .17, .17), .82, 0),
    "EyeGlint": ("neutral", (.83, .78, .61), .15, 0),
    "EyePupil": ("neutral", (.008, .012, .013), .19, 0),
    "FoldedIndigo": ("silk_indigo", (.03, .041, .068), 1.30, 0),
    "GreyTabbyFur": ("fur_grey", (.18, .21, .245), 1, 0),
    "IndigoSilk": ("silk_indigo", (.016, .023, .045), 1, 0),
    "IvoryClaw": ("neutral", (.63, .59, .48), .43, 0),
    "JadeCircuit": ("neutral", (.016, .4, .34), .25, .19),
    "OxbloodUrushi": ("lacquer_oxblood", (.105, .011, .016), 1, 0),
    "RedArrowFletch": ("neutral", (.66, .05, .055), .88, 0),
    "RoseNose": ("neutral", (.42, .17, .18), .47, 0),
    "ScarletSash": ("silk_indigo", (.23, .011, .024), 1.34, 0),
    "SORAResistanceRed": ("neutral", (.72, .036, .065), .48, 0),
    "UndyedLinen": ("silk_indigo", (.42, .37, .31), 1.50, 0),
    "WhiteFur": ("fur_white", (.77, .8, .79), 1, 0),
    "YumiLaminatedBamboo": ("neutral", (.27, .15, .065), .56, 0),
    "YumiSilkString": ("silk_indigo", (.7, .66, .53), 1.4, 0),
}
manifest = {
    "schema_version": 1,
    "generator": "scripts/art/create_nyaakoto_pbr_textures.py",
    "source_license": "Project-owned procedurally authored maps; no external texture asset",
    "seed": SEED,
    "maps": sets,
    "material_slots": {"M_Hero_" + key: {"surface": surface, "tint": tint,
                                         "roughness_scale": rough, "metallic_scale": metal}
                       for key, (surface, tint, rough, metal) in slots.items()},
}
(DEST / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("NYAAKOTO_PBR_MAPS_COMPLETE", len(sets), len(slots))
