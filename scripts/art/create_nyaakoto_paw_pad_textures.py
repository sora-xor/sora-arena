"""Author an original, tileable paw-pad PBR set for the Nyaakoto grip study.

The maps are intentionally subtle. Surface pores and compression creases should
read at a close first-person distance without turning pads into pebbled rubber.
No external texture is sampled by this generator.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Characters/NyaakotoFirstPersonPaws/Textures"
OUT.mkdir(parents=True, exist_ok=True)
N = 1024
SEED = 741823
rng = np.random.default_rng(SEED)


def smooth_noise(size: int) -> np.ndarray:
    a = (rng.random((size, size)) * 255).astype(np.uint8)
    image = Image.fromarray(a, "L").resize((N, N), Image.Resampling.BICUBIC)
    return np.asarray(image, dtype=np.float32) / 255.0 - 0.5


macro = smooth_noise(16)
meso = smooth_noise(82)
micro = smooth_noise(330)
height = 0.50 + 0.095 * macro + 0.035 * meso + 0.018 * micro

# Broken, curved compression furrows follow a large pad's contact direction.
crease = Image.new("L", (N, N), 0)
pen = ImageDraw.Draw(crease)
for j in range(63):
    y = int(rng.integers(-20, N + 20))
    x = int(rng.integers(-120, N))
    span = int(rng.integers(32, 150))
    bend = int(rng.integers(-12, 13))
    pen.line([(x, y), (x + span // 2, y + bend), (x + span, y + bend // 2)],
             fill=int(rng.integers(15, 42)), width=int(rng.integers(1, 3)))
crease = np.asarray(crease.filter(ImageFilter.GaussianBlur(1.0)), dtype=np.float32) / 255.0
height -= crease * 0.22

# Warm desaturated paw skin, with minute color variance but no baked lighting.
rgb = np.empty((N, N, 3), dtype=np.uint8)
variation = 10.0 * macro + 4.0 * meso + 1.7 * micro - 8.0 * crease
for c, base in enumerate((108, 68, 69)):
    rgb[..., c] = np.clip(base + variation * (1.0 if c == 0 else 0.72), 0, 255)

rough = np.clip(0.59 + 0.10 * macro + 0.055 * micro + 0.12 * crease, 0.36, 0.86)
gy, gx = np.gradient(height)
strength = 6.0
nx, ny = -gx * strength, gy * strength  # DirectX green convention.
nz = np.ones_like(nx)
length = np.sqrt(nx * nx + ny * ny + nz * nz)
normal = np.stack((nx / length, ny / length, nz / length), axis=-1)
normal = np.clip((normal * 0.5 + 0.5) * 255.0, 0, 255).astype(np.uint8)
orm = np.stack((np.full_like(rgb[..., 0], 255),
                np.clip(rough * 255, 0, 255).astype(np.uint8),
                np.zeros_like(rgb[..., 0])), axis=-1)

files = {
    "Albedo": "T_Nyaakoto_PawPad_Albedo.png",
    "NormalDX": "T_Nyaakoto_PawPad_NormalDX.png",
    "ORM": "T_Nyaakoto_PawPad_ORM.png",
}
for channel, data in (("Albedo", rgb), ("NormalDX", normal), ("ORM", orm)):
    Image.fromarray(data, "RGB").save(OUT / files[channel], optimize=True)

manifest = {
    "schema_version": 1,
    "generator": "scripts/art/create_nyaakoto_paw_pad_textures.py",
    "license": "Original project-owned procedural texture; no third-party data",
    "seed": SEED,
    "resolution": [N, N],
    "maps": {channel: {"file": name, "sha256": hashlib.sha256((OUT / name).read_bytes()).hexdigest()}
             for channel, name in files.items()},
}
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps({"created": files, "resolution": N}))
