"""Author a measured, repeatable PBR surface for the Nyaagyu torii lacquer.

The three maps are original procedural source art. The source is deliberately
kept independent of the licensed Poly Haven architectural palette so every
channel and its rights can be inspected before an Unreal import.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Environment/ToriiLacquer"
OUT.mkdir(parents=True, exist_ok=True)
SIZE = 2048
SEED = 450814
rng = np.random.default_rng(SEED)


def smooth_noise(cells: int) -> np.ndarray:
    """Bicubic, approximately periodic noise with a stable source seed."""
    small = rng.random((cells + 1, cells + 1), dtype=np.float32)
    small[-1, :] = small[0, :]
    small[:, -1] = small[:, 0]
    result = Image.fromarray(small, mode="F").resize((SIZE, SIZE), Image.Resampling.BICUBIC)
    return np.asarray(result, dtype=np.float32)


def vertical_fibers(count: int, shift: float) -> np.ndarray:
    samples = rng.normal(0, 1, count).astype(np.float32)
    samples[-1] = samples[0]
    x = np.linspace(0, count - 1, SIZE, dtype=np.float32)
    line = np.interp(x, np.arange(count), samples).astype(np.float32)
    y = np.arange(SIZE, dtype=np.float32)[:, None]
    flow = np.sin(y * .018 + line[None, :] * shift) * .18 + 1
    return line[None, :] * flow


# A multilayer vermilion coating: warm oxide variation, vertical brush drag,
# micro-crazing and sparse dark chips revealing the older undercoat.
macro = smooth_noise(22) - .5
meso = smooth_noise(95) - .5
fines = smooth_noise(360) - .5
grain = vertical_fibers(310, 1.8) * .55 + vertical_fibers(760, .35) * .12
streak = vertical_fibers(68, 3.1)
film = .68 * macro + .31 * meso + .08 * fines + .09 * grain
chip_field = smooth_noise(85) * .68 + smooth_noise(230) * .32
chip = np.clip((chip_field - .78) * 8.5, 0, 1)
chip *= np.clip((smooth_noise(43) - .28) * 2.5, 0, 1)
craze = np.clip((meso - .68) * 9, 0, 1) * .22
wash = np.clip(streak * .055, -.08, .08)

base = np.empty((SIZE, SIZE, 3), dtype=np.float32)
for index, (mid, film_scale, undercoat) in enumerate(((153, 67, 47), (38, 29, 25), (27, 20, 19))):
    base[:, :, index] = mid + film * film_scale - wash * 90 - craze * 22
    base[:, :, index] = base[:, :, index] * (1 - chip) + undercoat * chip
base = np.uint8(np.clip(base, 0, 255))

# Lacquer is dielectric. Painted film is glossier than exposed timber; darker
# cavities lose light, while no metallic response is invented for the paint.
roughness = np.clip(83 + meso * 32 + streak * 5 + craze * 28 + chip * 90, 32, 205)
ao = np.clip(249 - chip * 34 - craze * 16, 185, 255)
orm = np.stack((ao, roughness, np.zeros_like(roughness)), axis=-1).astype(np.uint8)

height = film * .45 - chip * .65 + grain * .018 - craze * .08
dy, dx = np.gradient(height)
nx = -dx * 4.0
ny = dy * 4.0  # DirectX tangent-space green channel.
denom = np.sqrt(nx * nx + ny * ny + 1)
normal = np.stack(((nx / denom * .5 + .5) * 255,
                   (ny / denom * .5 + .5) * 255,
                   (1 / denom * .5 + .5) * 255), axis=-1)
normal = np.uint8(np.clip(normal, 0, 255))

files = {}
for channel, array in (("Albedo", base), ("NormalDX", normal), ("ORM", orm)):
    path = OUT / f"T_Nyaagyu_ToriiLacquer_{channel}.png"
    Image.fromarray(array, "RGB").save(path, optimize=True)
    files[channel] = {"file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                      "resolution": [SIZE, SIZE]}

preview = Image.new("RGB", (1536, 512), (28, 30, 35))
for index, array in enumerate((base, normal, orm)):
    preview.paste(Image.fromarray(array, "RGB").resize((512, 512)), (index * 512, 0))
preview_path = OUT / "Nyaagyu_ToriiLacquer_PBR_Channels.png"
preview.save(preview_path, optimize=True)

manifest = {
    "schema_version": 1,
    "generator": "scripts/art/create_torii_lacquer_pbr.py",
    "seed": SEED,
    "material_slot": "M_Env_VermilionLacquer",
    "unreal_instance": "/Game/Generated/Environment/MI_Nyaagyu_ToriiLacquer.MI_Nyaagyu_ToriiLacquer",
    "tile_size_cm": 120.0,
    "license": "Original project-owned procedural texture; no third-party input image",
    "physical_intent": "Weathered vermilion dielectric lacquer with vertical brush drag and sparse exposed timber; RGB=albedo, DirectX normal, ORM=AO/roughness/metallic",
    "maps": files,
    "review": preview_path.name,
    "scope": "Material source art; actual Unreal appearance and frame cost require packaged review",
}
(OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("NYAAGYU_TORII_LACQUER_PBR_READY", OUT)
