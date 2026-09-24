"""Paint deterministic, estimated ibushi-clay maps for a source-only cap study.

The maps are authored noise, not sampled or measured historical ceramic. Run
before create_nyaagyu_sora_eave_cap_study.py. Uses the system Python/Pillow.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Environment/NyaagyuSoraEaveCapStudy"
OUT.mkdir(parents=True, exist_ok=True)
N = 1024
RNG = np.random.default_rng(175501)


def field(grid: int) -> np.ndarray:
    values = RNG.normal(0, 1, (grid, grid))
    pixels = np.uint8(np.clip(values * 38 + 127, 0, 255))
    image = Image.fromarray(pixels, "L").resize((N, N), Image.Resampling.BICUBIC)
    return (np.asarray(image, dtype=np.float32) - 127) / 38


large, medium, pores = field(12), field(80), field(380)
yy, xx = np.mgrid[:N, :N].astype(np.float32)
radius = np.hypot((xx - 511.5) / 511.5, (yy - 511.5) / 511.5)
edge_soot = np.clip((radius - .66) / .34, 0, 1)
chips = (RNG.random((N, N)) < .0014).astype(np.float32)
flecks = (RNG.random((N, N)) < .0018).astype(np.float32)

# Silver-charcoal smoked clay with restrained warm clay flecks. The map is a
# visual estimate and must be replaced by a measured, licensed capture for a
# final photoreal approval. It is not presented as an Edo ceramic sample.
body = 80 + 7.6 * large + 3.4 * medium + 1.9 * pores - 8.5 * edge_soot
rgb = np.stack((body + 1.7, body + 1.5, body + 1.0), axis=-1)
rgb += flecks[..., None] * np.array([13, 8, 4], dtype=np.float32)
rgb -= chips[..., None] * np.array([17, 17, 16], dtype=np.float32)
albedo = np.uint8(np.clip(rgb, 0, 255))

# Estimated microscopic pore height. Gradients are intentionally restrained;
# silhouette, lip and heraldic relief remain real modeled geometry.
height_mm = .060 * large + .028 * medium + .012 * pores - .12 * chips
step_mm = 140 / N  # mapping spans 140 mm in the authored planar UV square
grad_y, grad_x = np.gradient(height_mm, step_mm)
normal = np.stack((-grad_x, -grad_y, np.ones_like(grad_x)), axis=-1)
normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
normal_rgb = np.uint8(np.clip((normal * .5 + .5) * 255, 0, 255))

rough = np.uint8(np.clip(191 + 11 * large + 5 * medium + 15 * edge_soot, 118, 228))
orm = np.stack((np.full_like(rough, 255), rough, np.zeros_like(rough)), axis=-1)
files = {
    "albedo": "T_SoraEaveCap_Albedo.png",
    "normal_gl": "T_SoraEaveCap_NormalGL.png",
    "orm": "T_SoraEaveCap_ORM.png",
}
for key, pixels in (("albedo", albedo), ("normal_gl", normal_rgb), ("orm", orm)):
    Image.fromarray(pixels, "RGB").save(OUT / files[key], optimize=True)
record = {
    "status": "source-only authored PBR estimates; no measured ceramic capture",
    "generator": "scripts/art/build_nyaagyu_sora_eave_cap_maps.py",
    "seed": 175501,
    "size": [N, N],
    "normal_convention": "OpenGL/tangent +Y; invert green on DirectX import",
    "channels": "ORM R=AO estimate (white), G=roughness estimate, B=metallic (zero)",
    "files": {key: {"file": name, "sha256": hashlib.sha256((OUT / name).read_bytes()).hexdigest()}
              for key, name in files.items()},
}
(OUT / "texture_manifest.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps(record, indent=2))
