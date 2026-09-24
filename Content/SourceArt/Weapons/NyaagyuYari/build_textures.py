"""Reproducible original PBR texture study for the Nyaagyu su-yari.

Only noise, line work, and color values authored here are used.  No museum
photography or external asset is copied into these maps.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT = Path(__file__).resolve().parent / "Textures"
OUT.mkdir(parents=True, exist_ok=True)
N = 2048
RNG = np.random.default_rng(7199)


def blur_noise(radius: float) -> np.ndarray:
    raw = (RNG.random((N, N)) * 255).astype(np.uint8)
    image = Image.fromarray(raw, "L").filter(ImageFilter.GaussianBlur(radius))
    arr = np.asarray(image, dtype=np.float32) / 255.0
    return (arr - arr.mean()) / (arr.std() + 1e-6)


def save_rgb(name: str, arr: np.ndarray) -> None:
    Image.fromarray(np.clip(arr * 255, 0, 255).astype(np.uint8), "RGB").save(OUT / name)


def normal_from_height(height: np.ndarray, strength: float, name: str) -> None:
    gy, gx = np.gradient(height.astype(np.float32))
    nx = -gx * strength
    ny = gy * strength  # DirectX tangent-space convention.
    nz = np.ones_like(nx)
    mag = np.sqrt(nx * nx + ny * ny + nz * nz)
    save_rgb(name, np.stack(((nx / mag + 1) / 2,
                             (ny / mag + 1) / 2,
                             (nz / mag + 1) / 2), axis=-1))


def write_set(name: str, base: np.ndarray, rough: np.ndarray,
              metallic: float, height: np.ndarray, normal_strength: float) -> None:
    save_rgb(f"T_Yari_{name}_Albedo.png", base)
    orm = np.empty((*base.shape[:2], 3), dtype=np.float32)
    orm[..., 0] = 1.0
    orm[..., 1] = np.clip(rough, 0, 1)
    orm[..., 2] = metallic
    save_rgb(f"T_Yari_{name}_ORM.png", orm)
    normal_from_height(height, normal_strength, f"T_Yari_{name}_NormalDX.png")


# Forged steel: sparse lengthwise dressing lines, blotchy polish, and a shallow
# lengthwise differential sheen. This is a design texture, not a measured scan.
fine = blur_noise(1.4)
medium = blur_noise(24)
large = blur_noise(110)
scratch_image = Image.new("L", (N, N), 0)
draw = ImageDraw.Draw(scratch_image)
for _ in range(340):
    x = int(RNG.integers(0, N))
    y = int(RNG.integers(-100, N))
    length = int(RNG.integers(25, 400))
    x2 = x + int(RNG.integers(-3, 4))
    draw.line((x, y, x2, y + length), fill=int(RNG.integers(12, 70)), width=1)
scratch = np.asarray(scratch_image.filter(ImageFilter.GaussianBlur(.38)), dtype=np.float32) / 255
u = np.linspace(0, 1, N, dtype=np.float32)[None, :]
steel_h = .44 * fine + .22 * medium + .09 * large - 2.5 * scratch
steel_tone = .565 + .010 * medium + .009 * large - .045 * scratch
steel = np.stack((steel_tone * .96, steel_tone * .995,
                  steel_tone * 1.025), axis=-1)
steel_rough = .255 + .020 * medium + .012 * large + .25 * scratch
write_set("ForgedSteel", steel, steel_rough, 1.0, steel_h, .095)

# A separately authored iron finish for the ferrule and lower shoe. Fine
# oxidation and dressing variation are deliberately subtler than flaking rust.
patina_tone = .225 + .018 * medium + .014 * large - .015 * scratch
patina = np.stack((patina_tone * 1.03, patina_tone * 1.01,
                   patina_tone * .98), axis=-1)
patina_rough = .52 + .045 * medium + .025 * large + .09 * scratch
patina_h = .50 * medium + .16 * fine - 1.2 * scratch
write_set("PatinatedIron", patina, patina_rough, 1.0, patina_h, .28)

# The shaft's UV V axis runs with the wood grain. A few slowly wandering dark
# pores stay visible beneath the lacquer film; the texture is project-authored.
vertical = np.linspace(0, 1, N, dtype=np.float32)[:, None]
grain = (np.sin(u * 338 + 4 * np.sin(vertical * 10.2 + u * 13)) * .5
         + .36 * np.sin(u * 1080 + vertical * 24)
         + .18 * np.sin(u * 2010 + vertical * 63))
wood_h = grain * .42 + .25 * blur_noise(3.4) + .09 * blur_noise(48)
wood_tone = .33 + .046 * grain + .022 * blur_noise(38)
wood = np.stack((wood_tone * 1.08, wood_tone * .69,
                 wood_tone * .40), axis=-1)
write_set("AshWood", wood, .57 + .025 * grain, 0, wood_h, .080)

# A dark translucent-looking urushi concept: wood movement is understated;
# the smooth film and narrow roughness variation read through specular light.
lacquer_h = wood_h * .15 + .09 * blur_noise(2.4)
lacquer_tone = .050 + .0034 * grain + .0025 * blur_noise(90)
lacquer = np.stack((lacquer_tone * 1.38,
                    lacquer_tone * 1.01,
                    lacquer_tone * .75), axis=-1)
write_set("BlackUrushi", lacquer,
          .245 + .012 * grain + .008 * blur_noise(90), 0,
          lacquer_h, .021)

# A woven dark russet cord for the short modeled binding at the ferrule.
stripe = np.sin((u * 128 + vertical * 38) * 2 * np.pi)
cord_h = .40 * stripe + .25 * blur_noise(1.5)
cord_tone = .18 + .023 * stripe + .012 * blur_noise(18)
cord = np.stack((cord_tone * 1.32, cord_tone * .75,
                 cord_tone * .43), axis=-1)
write_set("RussetCord", cord, .76 + .024 * stripe, 0, cord_h, .11)

manifest = {
    "generator": "build_textures.py",
    "seed": 7199,
    "map_size": [N, N],
    "maps": "five original Albedo / ORM / DirectX normal sets",
    "source": "project-authored procedural color, grain, scratches, and height only",
    "limits": "art-estimated PBR values; not measured material scans or photoreal approval",
}
(OUT / "texture_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("YARI_TEXTURES", len(list(OUT.glob("T_Yari_*.png"))))
