"""Derive editable-study PBR maps from the project-owned V2 unique-UV albedo.

These normals are an artist-authored micro-fiber approximation, not a scan or
measured displacement. Both GL and DX green-channel conventions are exported.
"""

from pathlib import Path
import json
import hashlib

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / "NyaakotoAnatomyV2" / "T_Nyaakoto_HeadStudy_Albedo.png"
ALBEDO = ROOT / "T_Nyaakoto_CoatV3_Albedo.png"
NORMAL_GL = ROOT / "T_Nyaakoto_CoatV3_NormalGL.png"
NORMAL_DX = ROOT / "T_Nyaakoto_CoatV3_NormalDX.png"
ORM = ROOT / "T_Nyaakoto_CoatV3_ORM.png"

source = Image.open(SOURCE).convert("RGBA")
source.save(ALBEDO)
rgb = np.asarray(source, dtype=np.float32)[:, :, :3] / 255.0
alpha = np.asarray(source, dtype=np.uint8)[:, :, 3]
gray = (rgb[:, :, 0] * .2126 + rgb[:, :, 1] * .7152 + rgb[:, :, 2] * .0722)
blurred = np.asarray(
    Image.fromarray(np.uint8(gray * 255), "L").filter(ImageFilter.GaussianBlur(3)),
    dtype=np.float32,
) / 255.0
# Remove broad color markings from the height field. Keeping only the fiber
# scale avoids physically implausible 3D ridges at tabby/ivory boundaries.
height = np.clip(gray - blurred, -.10, .10)
gy, gx = np.gradient(height)
strength = 6.0
nx = -gx * strength
ny = -gy * strength
nz = np.ones_like(nx)
norm = np.sqrt(nx * nx + ny * ny + nz * nz)
nx /= norm
ny /= norm
nz /= norm
base = np.full_like(nx, 128, dtype=np.uint8)
gl = np.dstack((
    np.uint8(np.clip((nx * .5 + .5) * 255, 0, 255)),
    np.uint8(np.clip((ny * .5 + .5) * 255, 0, 255)),
    np.uint8(np.clip((nz * .5 + .5) * 255, 0, 255)),
))
dx = gl.copy()
dx[:, :, 1] = 255 - dx[:, :, 1]
Image.fromarray(gl, "RGB").save(NORMAL_GL)
Image.fromarray(dx, "RGB").save(NORMAL_DX)
rough = np.uint8(np.clip((.84 + .07 * np.abs(height) / .10) * 255, 0, 255))
# White AO is deliberate: there is no trustworthy sculpt-to-retopo bake here.
# R=AO, G=roughness, B=metalness.
orm = np.dstack((np.full_like(base, 255), rough, np.zeros_like(base)))
Image.fromarray(orm, "RGB").save(ORM)
print(json.dumps({
    "maps": [str(p.name) for p in (ALBEDO, NORMAL_GL, NORMAL_DX, ORM)],
    "resolution": list(source.size),
    "opaque_texels": int(np.count_nonzero(alpha)),
    "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
}, indent=2))
