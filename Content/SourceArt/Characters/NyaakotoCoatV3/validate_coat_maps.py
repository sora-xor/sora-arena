"""Check map dimensions, channel packing, and GL/DX normal parity."""

from pathlib import Path
import json

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
albedo = np.asarray(Image.open(ROOT / "T_Nyaakoto_CoatV3_Albedo.png").convert("RGBA"))
gl = np.asarray(Image.open(ROOT / "T_Nyaakoto_CoatV3_NormalGL.png").convert("RGB"))
dx = np.asarray(Image.open(ROOT / "T_Nyaakoto_CoatV3_NormalDX.png").convert("RGB"))
orm = np.asarray(Image.open(ROOT / "T_Nyaakoto_CoatV3_ORM.png").convert("RGB"))
assert all(a.shape[:2] == (2048, 2048) for a in (albedo, gl, dx, orm))
assert np.array_equal(gl[:, :, 0], dx[:, :, 0])
assert np.array_equal(gl[:, :, 2], dx[:, :, 2])
assert np.array_equal(255 - gl[:, :, 1], dx[:, :, 1])
assert np.all(orm[:, :, 0] == 255), "No measured AO bake is claimed"
assert np.all(orm[:, :, 2] == 0), "Fur is nonmetallic"
assert 200 <= float(np.median(orm[:, :, 1])) <= 240
assert np.ptp(albedo[:, :, :3]) > 100
print(json.dumps({
    "status": "NYAAKOTO_COAT_V3_MAPS_VALID",
    "resolution": [2048, 2048],
    "median_roughness_u8": float(np.median(orm[:, :, 1])),
    "normal_y_pair": "GL and DX green channels are exact complements",
}, indent=2))
