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
FUR_SOURCES = {
    "fur_grey": "Nyaakoto_GreyFur_ImageGen_v1.png",
    "fur_white": "Nyaakoto_WhiteFur_ImageGen_v1.png",
    "fur_charcoal": "Nyaakoto_CharcoalFur_ImageGen_v1.png",
}
FUR_GENERATION_IDS = {
    "fur_grey": "exec-67dc9aa3-fbdb-4fc7-b195-336e6edf1fba",
    "fur_white": "exec-e08190d3-bb7f-4545-be43-f53aad717117",
    "fur_charcoal": "exec-eaaaa9f4-9353-437f-ba30-cd03fa217db1",
}
FUR_PROMPTS = {
    "fur_grey": (
        "Use case: photorealistic-natural. Asset type: repeatable PBR fur albedo "
        "reference for an Unreal Engine feline samurai character. Create a square, "
        "perfectly top-down orthographic macro photograph-like texture swatch of "
        "dense short-haired grey tabby cat coat, with fine distinct guard hairs "
        "and undercoat; subtle warm grey, charcoal, beige agouti variation and "
        "non-regular faint tabby mottling. Every part of the frame is fur at the "
        "same scale. Broad even diffused lighting so the image can serve as albedo, "
        "with no cast shadows, no specular hotspots, no vignette. The texture must "
        "be visually seamless across opposite edges for tiling. No cat anatomy, "
        "no eyes, no nose, no ears, no background, no text, no logo, no watermark."
    ),
    "fur_white": (
        "Use case: photorealistic-natural. Asset type: PBR albedo source swatch "
        "for a feline samurai game character. Square, top-down orthographic macro "
        "photograph-like texture of dense short creamy-white domestic cat fur, "
        "with thousands of fine individual guard hairs and undercoat, subtle "
        "ivory, cream and pale grey color variation, 4–8 mm directional fibers, "
        "same scale everywhere. Broad even diffused lighting with no directional "
        "shadow or highlight so it can be used as material albedo. Fur fills the "
        "entire frame. Visually seamless tiling across opposite edges. No cat "
        "anatomy, no skin, no eye, no nose, no ear, no background, no text or "
        "watermark."
    ),
    "fur_charcoal": (
        "Use case: photorealistic-natural. Asset type: PBR albedo source swatch "
        "for dark tabby markings on a feline game character. Square top-down "
        "orthographic macro photograph-like texture of dense short charcoal and "
        "smoky-brown cat fur, fine individual guard hairs and undercoat, natural "
        "directional 4–8 mm fibers, subtle warm grey variation, low contrast dark "
        "markings with no large stripes. Every frame area is the same-scale fur. "
        "Broad even neutral diffuse light for albedo capture, without cast shadows, "
        "specular highlights or vignette. Visually seamless opposite edges for "
        "tiling. No anatomy, no skin, no eye, no nose, no ear, no background, no "
        "text, no watermark."
    ),
}
RIGHTS_URL = "https://openai.com/policies/row-terms-of-use/"


def exact_wrap(pixels: np.ndarray) -> np.ndarray:
    """Give all output channels identical opposite edge texels."""
    pixels = pixels.copy()
    row = ((pixels[0].astype(np.uint16) + pixels[-1].astype(np.uint16)) // 2).astype(np.uint8)
    pixels[0] = row
    pixels[-1] = row
    column = ((pixels[:, 0].astype(np.uint16) + pixels[:, -1].astype(np.uint16)) // 2).astype(np.uint8)
    pixels[:, 0] = column
    pixels[:, -1] = column
    return pixels


def periodic_photo(photo: np.ndarray) -> np.ndarray:
    """Remove broad edge mismatch without mirroring the animal's coat pattern.

    The periodic-plus-smooth decomposition keeps the photographed high-frequency
    fibers while distributing boundary correction across the tile. The final
    byte-for-byte wrap is handled by exact_wrap after quantization.
    """
    height, width = photo.shape[:2]
    edge = np.zeros_like(photo)
    edge[:, 0] += photo[:, -1] - photo[:, 0]
    edge[:, -1] += photo[:, 0] - photo[:, -1]
    edge[0] += photo[-1] - photo[0]
    edge[-1] += photo[0] - photo[-1]
    y = 2 * np.cos(2 * np.pi * np.arange(height) / height)[:, None]
    x = 2 * np.cos(2 * np.pi * np.arange(width) / width)[None, :]
    divisor = y + x - 4
    divisor[0, 0] = 1
    smooth = np.fft.ifft2(
        np.fft.fft2(edge, axes=(0, 1)) / divisor[:, :, None], axes=(0, 1)
    ).real
    return np.clip(photo - smooth, 0, 1).astype(np.float32)


def photo_fur_fields(kind: str):
    """Build albedo and conservative micro-normal/ORM from generated swatches.

    The swatches supply coat color and visible hair pattern only. Height is a
    high-pass estimate for small fiber relief, not a photogrammetry measurement.
    """
    source = DEST / "Source" / FUR_SOURCES[kind]
    photo = Image.open(source).convert("RGB").resize((SIZE, SIZE), Image.Resampling.LANCZOS)
    color = periodic_photo(np.asarray(photo, dtype=np.float32) / 255)
    albedo = exact_wrap(np.uint8(np.clip(color * 255, 0, 255)))
    luminance = color[:, :, 0] * .2126 + color[:, :, 1] * .7152 + color[:, :, 2] * .0722
    # Remove swatch-scale light/dark mottling before estimating hair relief;
    # broad photographic lighting must not become a normal-map ridge.
    broad = periodic_blur(periodic_blur(luminance, 6, 0), 6, 1)
    hair = np.clip(luminance - broad, -.09, .09)
    dx = (np.roll(hair, -1, 1) - np.roll(hair, 1, 1)) * .5
    dy = (np.roll(hair, -1, 0) - np.roll(hair, 1, 0)) * .5
    normal = np.stack((-dx * 3.5, dy * 3.5, np.ones_like(dx)), 2)
    normal /= np.linalg.norm(normal, axis=2, keepdims=True)
    normal_rgb = exact_wrap(np.uint8(np.clip((normal * .5 + .5) * 255, 0, 255)))
    base_roughness = {"fur_grey": .83, "fur_white": .86, "fur_charcoal": .87}[kind]
    roughness = np.uint8(np.clip((base_roughness - hair * .32) * 255, 0, 255))
    occlusion = np.uint8(np.clip((1 - np.maximum(-hair, 0) * .52) * 255, 0, 255))
    orm = exact_wrap(np.stack((occlusion, roughness, np.zeros_like(roughness)), 2))
    return albedo, normal_rgb, orm


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
    if kind in FUR_SOURCES:
        albedo, normal, orm = photo_fur_fields(kind)
    else:
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
    # The iris has a separately painted blue-grey albedo; tinting it blue again
    # discards the pigment variation and darkens the limbal fibers in Unreal.
    "BlueEye": ("neutral", (1, 1, 1), .15, 0),
    "CharcoalStripeFur": ("fur_charcoal", (.75, .76, .78), 1, 0),
    "EarSkin": ("neutral", (.4, .17, .17), .82, 0),
    "EyeGlint": ("neutral", (.83, .78, .61), .15, 0),
    "EyePupil": ("neutral", (.008, .012, .013), .19, 0),
    "FoldedIndigo": ("silk_indigo", (.03, .041, .068), 1.30, 0),
    "GreyTabbyFur": ("fur_grey", (.76, .78, .80), 1, 0),
    "IndigoSilk": ("silk_indigo", (.016, .023, .045), 1, 0),
    "IvoryClaw": ("neutral", (.63, .59, .48), .43, 0),
    "JadeCircuit": ("neutral", (.016, .4, .34), .25, .19),
    "OxbloodUrushi": ("lacquer_oxblood", (.105, .011, .016), 1, 0),
    "RedArrowFletch": ("neutral", (.66, .05, .055), .88, 0),
    "RoseNose": ("neutral", (.42, .17, .18), .47, 0),
    "ScarletSash": ("silk_indigo", (.23, .011, .024), 1.34, 0),
    "SORAResistanceRed": ("neutral", (.72, .036, .065), .48, 0),
    "UndyedLinen": ("silk_indigo", (.42, .37, .31), 1.50, 0),
    "WhiteFur": ("fur_white", (.92, .93, .94), 1, 0),
    "YumiLaminatedBamboo": ("neutral", (.27, .15, .065), .56, 0),
    "YumiSilkString": ("silk_indigo", (.7, .66, .53), 1.4, 0),
}
manifest = {
    "schema_version": 1,
    "generator": "scripts/art/create_nyaakoto_pbr_textures.py",
    "source_license": "Project-owned OpenAI image-generation output and procedural PBR conversion; no external stock texture. Output ownership is assigned to the user under the OpenAI Terms of Use, subject to those terms.",
    "seed": SEED,
    "fur_sources": [
        {"surface": kind, "file": "Source/" + filename,
         "sha256": hashlib.sha256((DEST / "Source" / filename).read_bytes()).hexdigest(),
         "origin": "Built-in OpenAI image_gen.imagegen, text-only prompt, 2026-09-24",
         "origin_output_id": FUR_GENERATION_IDS[kind],
         "source_url": None,
         "prompt": FUR_PROMPTS[kind],
         "commercial_use_rights_basis": "OpenAI Terms of Use, Content ownership assignment; subject to the Terms",
         "rights_url": RIGHTS_URL}
        for kind, filename in FUR_SOURCES.items()
    ],
    "maps": sets,
    "material_slots": {"M_Hero_" + key: {"surface": surface, "tint": tint,
                                         "roughness_scale": rough, "metallic_scale": metal}
                       for key, (surface, tint, rough, metal) in slots.items()},
}
(DEST / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("NYAAKOTO_PBR_MAPS_COMPLETE", len(sets), len(slots))
