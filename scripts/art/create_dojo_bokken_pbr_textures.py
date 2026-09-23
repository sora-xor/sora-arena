"""Derive conservative first-person oak PBR maps from the pinned source image.

The generated image is an albedo study, not a measured material scan. Normal
and roughness channels are authored estimates and must be visually reviewed in
Unreal. No simulated knot, plank seam, or false metallic response is added.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, __version__ as PILLOW_VERSION


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Weapons/DojoBokkenPBR"
SOURCE = OUT / "Source/Oak_QuarterSawn_ImageGen_v1.png"
EXPECTED_SOURCE_SHA = "e6a1034167a367d2469fa67b2013a63522b50313544d4f25dd2dd2c38d97af8f"
SIZE = 2048


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert sha(SOURCE) == EXPECTED_SOURCE_SHA
original = Image.open(SOURCE).convert("RGB")
assert original.size == (1254, 1254)
sample = original.resize((SIZE, SIZE), Image.Resampling.LANCZOS)
array = np.asarray(sample, dtype=np.float32) / 255.0
# The reference image is a little pale for oiled white oak. Preserve its
# photographic pores while reducing the broad illumination range.
albedo = np.clip(array * np.array([.85, .83, .80], dtype=np.float32), 0, 1)
albedo_image = Image.fromarray(np.uint8(np.round(albedo * 255)), mode="RGB")
albedo_path = OUT / "T_DojoBokken_WhiteOak_Albedo_2k.png"
albedo_image.save(albedo_path, compress_level=9)

luminance = np.asarray(sample.convert("L"), dtype=np.float32) / 255.0
blurred = np.asarray(sample.convert("L").filter(ImageFilter.GaussianBlur(radius=7)), dtype=np.float32) / 255.0
fine = np.asarray(sample.convert("L").filter(ImageFilter.GaussianBlur(radius=1.2)), dtype=np.float32) / 255.0
height = .68 * (fine - blurred) + .32 * (luminance - fine)
# The photographed grain runs vertically; the map follows cylindrical UV0.
dy, dx = np.gradient(height)
nx = -dx * 2.8
ny = dy * 2.8  # DirectX tangent-space Y convention.
length = np.sqrt(nx * nx + ny * ny + 1.0)
normal = np.stack((nx / length, ny / length, 1 / length), axis=-1)
normal = np.uint8(np.round(np.clip(normal * .5 + .5, 0, 1) * 255))
normal_path = OUT / "T_DojoBokken_WhiteOak_NormalDX_2k.png"
Image.fromarray(normal, mode="RGB").save(normal_path, compress_level=9)

roughness = np.clip(.55 + (blurred - .58) * .20 + np.abs(height) * .55, .44, .68)
orm = np.zeros((SIZE, SIZE, 3), dtype=np.uint8)
orm[:, :, 0] = 255  # No painted AO; the mesh and Lumen provide contact shading.
orm[:, :, 1] = np.uint8(np.round(roughness * 255))
orm_path = OUT / "T_DojoBokken_WhiteOak_ORM_2k.png"
Image.fromarray(orm, mode="RGB").save(orm_path, compress_level=9)

record = {
    "schema_version": 1,
    "generator": "scripts/art/create_dojo_bokken_pbr_textures.py",
    "pillow_version": PILLOW_VERSION,
    "numpy_version": np.__version__,
    "source": str(SOURCE.relative_to(OUT)),
    "source_sha256": EXPECTED_SOURCE_SHA,
    "source_output_id": "exec-e8f16775-bb5f-479b-8efb-478432eeb9fe",
    "source_prompt": (
        "Use case: photorealistic-natural. Asset type: source albedo texture for a close-view, "
        "hand-shaped Japanese white-oak bokken used in a photorealistic Unreal Engine "
        "first-person samurai game. Generate ONE seamless/tileable square orthographic "
        "surface photograph of quarter-sawn Japanese white oak, long fine grain running "
        "vertically through the entire image, pale honey to light tan with subtle darker "
        "pores, natural irregularity and a few quiet mineral streaks, extremely fine scale, "
        "no plank seams or end grain. Flat color-calibrated overcast illumination suitable "
        "as unlit PBR base color, no directional shadows, no specular highlights, no vignette. "
        "Fill frame edge to edge with wood. Do not depict a sword, tabletop, object, writing, "
        "logo, knots, splits, dirt, bark, dramatic streaks, or background. Prioritize "
        "photographic material realism and non-repeating natural detail; no illustration "
        "or painting."
    ),
    "source_rights": "Project-generated bitmap via built-in image generation; OpenAI Terms of Use, no purchased third-party asset.",
    "maps": {
        "Albedo": {"file": albedo_path.name, "sha256": sha(albedo_path), "resolution": [SIZE, SIZE]},
        "NormalDX": {"file": normal_path.name, "sha256": sha(normal_path), "resolution": [SIZE, SIZE]},
        "ORM": {"file": orm_path.name, "sha256": sha(orm_path), "resolution": [SIZE, SIZE]},
    },
    "limitations": "The source is 1254 px and resampled to 2048 px; no additional detail is created by upsampling. Normal and roughness derive from color, not measured surface height. In-engine visual approval remains required.",
}
(OUT / "texture_manifest.json").write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
print("DOJO_BOKKEN_PBR_TEXTURES_READY", sha(albedo_path), sha(normal_path), sha(orm_path))
