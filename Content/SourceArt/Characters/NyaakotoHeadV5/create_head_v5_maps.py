"""Project-owned V4 unique-UV coat grade for the V5 anatomy study.

This changes albedo only. V4's artist-derived normal and ORM are reused by
reference; neither source should be mistaken for measured/photogrammetric PBR.
"""
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
source = ROOT.parent / "NyaakotoHeadV4" / "T_Nyaakoto_HeadV4_Albedo.png"
a = np.asarray(Image.open(source).convert("RGBA"), dtype=np.float32) / 255.
lum = a[..., :3] @ np.array([.2126,.7152,.0722], dtype=np.float32)
gray = np.clip((.73-lum)/.27,0,1) * (lum>.08)
# A modest cool-grey shift raises separation between tabby coat and ivory
# muzzle without shading the source photograph or inventing a fur normal.
a[..., :3] *= 1-.14*gray[..., None]
a[..., 2] = np.clip(a[..., 2]+.012*gray,0,1)
Image.fromarray(np.uint8(np.round(np.clip(a,0,1)*255)),"RGBA").save(ROOT/"T_Nyaakoto_HeadV5_Albedo.png")
print("NYAAKOTO_V5_ALBEDO_COMPLETE",a.shape[:2])
