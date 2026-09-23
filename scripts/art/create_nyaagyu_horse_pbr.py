"""Build exact-wrap PBR maps for the project-owned Nyaagyu horse/tack study.

The source swatches are generated images, not measured material scans. Their
color pattern is the albedo source; normals represent only conservative
high-frequency relief, and roughness/metallic are authoring estimates.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
HORSE = ROOT / "Content/SourceArt/Horses/Nyaagyu"
OUT = HORSE / "PBR"
OUT.mkdir(parents=True, exist_ok=True)
SIZE = 2048
SOURCES = {
    "horse_coat": ("SealBrownHorseCoat_ImageGen_v1.png", "exec-4d1cc66a-c60e-491a-8d27-711f3f5c3ea6"),
    "tazuna_leather": ("TannedTazunaLeather_ImageGen_v1.png", "exec-ef17bea5-3cb0-4c50-986c-1dcd0c81127f"),
    "abumi_iron": ("BlackenedAbumiIron_ImageGen_v1.png", "exec-3533b491-95f4-4626-b062-5f5d1156131d"),
}
PROMPTS = {
    "horse_coat": (
        "Use case: photorealistic-natural. Asset type: PBR albedo source texture "
        "for an original Edo-era Japanese horse in an Unreal Engine game. A square "
        "top-down orthographic macro photograph-like swatch of a healthy compact "
        "horse's short sleek seal-brown coat: fine individual dark reddish-brown "
        "hairs, slightly darker roots and warm chestnut highlights, subtle natural "
        "mottling, no white patches. Every part of frame is horse coat at one "
        "consistent scale. Broad neutral diffused lighting suitable for albedo, "
        "with no cast shadow, specular hotspot, vignette or depth of field. "
        "Visually seamless opposite edges for tiling. No horse anatomy, saddle, "
        "mane, skin, face, background, text or watermark."
    ),
    "tazuna_leather": (
        "Use case: photorealistic-natural. Asset type: repeatable PBR albedo "
        "source for historically plausible Japanese horse tack leather in a game. "
        "Square top-down orthographic macro swatch of dark chestnut-brown "
        "vegetable-tanned leather with dense irregular grain, very fine age creases "
        "and subtle rubbed edges but no cuts or seam lines. Even neutral diffuse "
        "capture lighting suitable for albedo, no cast shadows or specular "
        "highlights. Material fills the frame at consistent scale and is visually "
        "seamless across opposite edges. No straps, buckles, stitching, saddle "
        "silhouette, labels, text, logo or watermark."
    ),
    "abumi_iron": (
        "Use case: photorealistic-natural. Asset type: PBR albedo source for "
        "Japanese horse stirrups, bit, and fittings in a historical game. Square "
        "top-down orthographic macro material swatch of hand-worked blackened "
        "wrought iron: deep charcoal iron with subtle irregular forge texture, "
        "worn grey edges suggested only through fine material variation, tiny "
        "oxidation specks, no rust flakes. Uniform neutral diffuse albedo lighting "
        "without shadows, reflections, depth of field, or specular hotspots. Same "
        "material at a consistent scale fills the whole frame, visually seamless "
        "opposite edges. No stirrup shape, bit, hardware silhouette, text, logo or "
        "watermark."
    ),
}
SURFACE = {
    "horse_coat": {"roughness": .72, "metallic": 0.0, "relief": 2.8},
    "tazuna_leather": {"roughness": .67, "metallic": 0.0, "relief": 3.2},
    "abumi_iron": {"roughness": .46, "metallic": .88, "relief": 2.5},
}
SLOTS = {
    "M_Horse_SealBrownCoat": {"surface": "horse_coat", "tint": [1.0, 1.0, 1.0]},
    "M_Horse_DarkPoints": {"surface": "horse_coat", "tint": [.54, .52, .51]},
    "M_Tack_DarkLeather": {"surface": "tazuna_leather", "tint": [.83, .78, .73]},
    "M_Tack_BlackenedIron": {"surface": "abumi_iron", "tint": [.91, .93, .95]},
}
RIGHTS = "https://openai.com/policies/row-terms-of-use/"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def wrap_exact(pixels: np.ndarray) -> np.ndarray:
    pixels = pixels.copy()
    row = ((pixels[0].astype(np.uint16) + pixels[-1].astype(np.uint16)) // 2).astype(np.uint8)
    pixels[0] = row
    pixels[-1] = row
    column = ((pixels[:, 0].astype(np.uint16) + pixels[:, -1].astype(np.uint16)) // 2).astype(np.uint8)
    pixels[:, 0] = column
    pixels[:, -1] = column
    return pixels


def periodic_photo(photo: np.ndarray) -> np.ndarray:
    height, width = photo.shape[:2]
    edge = np.zeros_like(photo)
    edge[:, 0] += photo[:, -1] - photo[:, 0]
    edge[:, -1] += photo[:, 0] - photo[:, -1]
    edge[0] += photo[-1] - photo[0]
    edge[-1] += photo[0] - photo[-1]
    yy = 2 * np.cos(2 * np.pi * np.arange(height) / height)[:, None]
    xx = 2 * np.cos(2 * np.pi * np.arange(width) / width)[None, :]
    denominator = yy + xx - 4
    denominator[0, 0] = 1
    smooth = np.fft.ifft2(np.fft.fft2(edge, axes=(0, 1)) / denominator[:, :, None], axes=(0, 1)).real
    return np.clip(photo - smooth, 0, 1).astype(np.float32)


def blur_periodic(values: np.ndarray, radius: int, axis: int) -> np.ndarray:
    if axis == 0:
        padded = np.concatenate((values[-radius:], values, values[:radius]), axis=0)
        summed = np.concatenate((np.zeros_like(padded[:1]), np.cumsum(padded, axis=0)), axis=0)
        return (summed[2 * radius + 1:] - summed[:-(2 * radius + 1)]) / (2 * radius + 1)
    padded = np.concatenate((values[:, -radius:], values, values[:, :radius]), axis=1)
    summed = np.concatenate((np.zeros_like(padded[:, :1]), np.cumsum(padded, axis=1)), axis=1)
    return (summed[:, 2 * radius + 1:] - summed[:, :-(2 * radius + 1)]) / (2 * radius + 1)


def maps_for(kind: str):
    filename, _ = SOURCES[kind]
    image = Image.open(OUT / "Source" / filename).convert("RGB")
    photo = np.asarray(image.resize((SIZE, SIZE), Image.Resampling.LANCZOS), dtype=np.float32) / 255
    color = periodic_photo(photo)
    albedo = wrap_exact(np.uint8(np.clip(color * 255, 0, 255)))
    light = color[:, :, 0] * .2126 + color[:, :, 1] * .7152 + color[:, :, 2] * .0722
    broad = blur_periodic(blur_periodic(light, 6, 0), 6, 1)
    relief = np.clip(light - broad, -.09, .09)
    dx = (np.roll(relief, -1, 1) - np.roll(relief, 1, 1)) * .5
    dy = (np.roll(relief, -1, 0) - np.roll(relief, 1, 0)) * .5
    strength = SURFACE[kind]["relief"]
    normal = np.stack((-dx * strength, dy * strength, np.ones_like(dx)), 2)
    normal /= np.linalg.norm(normal, axis=2, keepdims=True)
    normal_map = wrap_exact(np.uint8(np.clip((normal * .5 + .5) * 255, 0, 255)))
    roughness = np.uint8(np.clip((SURFACE[kind]["roughness"] - relief * .30) * 255, 0, 255))
    ao = np.uint8(np.clip((1 - np.maximum(-relief, 0) * .55) * 255, 0, 255))
    metal = np.full_like(roughness, round(SURFACE[kind]["metallic"] * 255))
    orm = wrap_exact(np.stack((ao, roughness, metal), 2))
    return albedo, normal_map, orm


horse_manifest = json.loads((HORSE / "manifest.json").read_text())
assert horse_manifest["insignia_sha256"]
sets = []
for kind in SOURCES:
    entries = []
    for channel, pixels in zip(("Albedo", "NormalDX", "ORM"), maps_for(kind)):
        path = OUT / f"T_Nyaagyu_{kind}_{channel}.png"
        Image.fromarray(pixels, "RGB").save(path, optimize=True)
        entries.append({"channel": channel, "file": path.name, "sha256": sha(path)})
    sets.append({"name": kind, "resolution": [SIZE, SIZE], "maps": entries,
                 "roughness": SURFACE[kind]["roughness"], "metallic": SURFACE[kind]["metallic"]})

record = {
    "schema_version": 1,
    "generator": "scripts/art/create_nyaagyu_horse_pbr.py",
    "base_horse_blend_sha256": horse_manifest["blend_sha256"],
    "base_horse_fbx_sha256": horse_manifest["fbx_sha256"],
    "sora_logo_sha256": horse_manifest["insignia_sha256"],
    "source_license": "First-party OpenAI image-generation output owned by the project user under the OpenAI Terms of Use, subject to those terms; no third-party stock textures",
    "sources": [
        {"surface": kind, "file": "Source/" + file, "sha256": sha(OUT / "Source" / file),
         "origin": "Built-in OpenAI image_gen.imagegen; text-only prompt; 2026-09-24",
         "origin_output_id": generation_id, "prompt": PROMPTS[kind],
         "source_url": None, "commercial_use_rights_basis": "OpenAI Terms of Use, Content ownership assignment; subject to the Terms",
         "rights_url": RIGHTS}
        for kind, (file, generation_id) in SOURCES.items()
    ],
    "maps": sets,
    "material_slots": SLOTS,
    "limitations": "Generated swatches are not measured scans. Normal/roughness are high-frequency authoring estimates, not calibrated material capture. Original horse anatomy, tack dimensions, and static rig limits remain unchanged.",
}
(OUT / "manifest.json").write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
print("NYAAGYU_HORSE_PBR_COMPLETE", len(sets), len(SLOTS))
