"""Make a reproducible *art estimate*, not a measured washi transmission map.

TextureCan Paper0017 supplies height but no opacity or transmission. This
source-only 2K grayscale map merely bakes the documented Blender shader range
for review. It must not be presented as a physical capture.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
TEXTURES = ROOT / "Content/SourceArt/Environment/ShojiPaperArtReview/Textures"
SOURCE = TEXTURES / "paper_0017_height_2k.png"
OUTPUT = TEXTURES / "paper_0017_translucency_ART_ESTIMATE_2k.png"
SOURCE_SHA256 = "ddcee8e3779d271ab816c2567d673c7f0abf3bc158f68d601426282192b21035"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert sha(SOURCE) == SOURCE_SHA256, "Paper0017 source height changed"
height = np.asarray(Image.open(SOURCE), dtype=np.float32)
assert height.shape == (2048, 2048)
normalized = height / 65535.0
estimated_fraction = .22 + .30 * np.clip((normalized - .490) / .020, 0, 1)
pixels = np.rint(estimated_fraction * 255).astype(np.uint8)
Image.fromarray(pixels, mode="L").save(OUTPUT, optimize=True)
print("SHOJI_TRANSLUCENCY_ART_ESTIMATE", OUTPUT, sha(OUTPUT),
      int(pixels.min()), int(pixels.max()), flush=True)
