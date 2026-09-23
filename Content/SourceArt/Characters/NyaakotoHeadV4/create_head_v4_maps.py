"""Deterministic artist-derived PBR map pass from the project-owned V3 unique UVs.

This is a source-study texture revision, not a captured animal-fur scan.
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent / "NyaakotoCoatV3"
src = np.asarray(Image.open(BASE / "T_Nyaakoto_CoatV3_Albedo.png").convert("RGBA"), dtype=np.float32) / 255
rgb = src[..., :3]
lum = rgb @ np.array([.2126, .7152, .0722], dtype=np.float32)
opaque = lum > .075
# The V3 gray atlas islands are too pale against the white ruff. Preserve the
# ivory fibers and their existing microvariation while moving tabby fur toward
# the darker gray value family in the supplied reference.
gray_weight = np.clip((.72 - lum) / .24, 0, 1) * opaque
rgb = rgb * (1 - .19 * gray_weight[..., None])
rgb = np.clip(rgb, 0, 1)
albedo = np.dstack((rgb, src[..., 3]))
Image.fromarray(np.uint8(np.round(albedo * 255)), "RGBA").save(ROOT / "T_Nyaakoto_HeadV4_Albedo.png")

# A deliberately subtle fiber normal from V3's own high-frequency color. It
# is a repeatable artist-derived bump, not a photogrammetric/scan normal.
smooth = (lum + np.roll(lum, 1, 0) + np.roll(lum, -1, 0) +
          np.roll(lum, 1, 1) + np.roll(lum, -1, 1)) / 5
height = np.clip((lum - smooth) * opaque, -.16, .16)
dx = np.clip((np.roll(height, -1, 1) - np.roll(height, 1, 1)) * 2.2, -.35, .35)
dy = np.clip((np.roll(height, -1, 0) - np.roll(height, 1, 0)) * 2.2, -.35, .35)
nx, ny = -dx, -dy
nz = np.ones_like(nx)
norm = np.sqrt(nx*nx + ny*ny + nz*nz)
gl = np.stack(((nx/norm+1)*.5, (ny/norm+1)*.5, (nz/norm+1)*.5), axis=-1)
gl[~opaque] = (.5, .5, 1)
dxmap = gl.copy(); dxmap[..., 1] = 1 - dxmap[..., 1]
Image.fromarray(np.uint8(np.round(gl*255)), "RGB").save(ROOT / "T_Nyaakoto_HeadV4_NormalGL.png")
Image.fromarray(np.uint8(np.round(dxmap*255)), "RGB").save(ROOT / "T_Nyaakoto_HeadV4_NormalDX.png")

# R white means AO has not been baked. B zero: all coat fibers are dielectric.
# Roughness stays high, varied gently by the existing fiber structure.
rough = np.clip(.82 - .11 * (lum - .48) + .05 * (lum - smooth), .71, .91)
orm = np.stack((np.ones_like(rough), rough, np.zeros_like(rough)), axis=-1)
Image.fromarray(np.uint8(np.round(orm*255)), "RGB").save(ROOT / "T_Nyaakoto_HeadV4_ORM.png")
print("NYAAKOTO_HEAD_V4_MAPS_COMPLETE", src.shape[:2])
