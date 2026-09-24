"""Hash and image-mask audit for the source-only Nyaakoto pose A/B.

Run with the project's host Python, where Pillow and NumPy are available.
This script does not alter images: it writes only metrics JSON.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Characters/NyaakotoBokutoViewmodel/PoseProbe"
record = json.loads((OUT / "manifest.json").read_text())
assert record["schema_version"] == 1
assert record["current_root_cm"] == [40,18,-18]
assert record["proposed_root_cm"] == [40,8,-7]
assert record["resolution"] == [1600,900]
assert record["horizontal_fov_degrees"] == 70


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


images = {}
for filename,item in record["outputs"].items():
    path = OUT / filename
    assert path.stat().st_size == item["bytes"]
    assert sha(path) == item["sha256"], filename
    image = np.asarray(Image.open(path).convert("RGB"),dtype=np.int16)
    assert image.shape == (900,1600,3)
    images[filename.removesuffix(".png")] = image

empty = images["Empty_SameCameraAndLight"]
height,width = empty.shape[:2]
yy,xx = np.ogrid[:height,:width]
cx,cy = width//2,height//2
reticle_disc = (xx-cx)**2+(yy-cy)**2 <= 80**2


def metrics(a,b):
    changed = np.max(np.abs(a-b),axis=2) > 8
    coords = np.argwhere(changed)
    bbox = None if not len(coords) else [int(coords[:,1].min()),int(coords[:,0].min()),
                                         int(coords[:,1].max()+1),int(coords[:,0].max()+1)]
    center = int(np.logical_and(changed,reticle_disc).sum())
    nearest = None if not len(coords) else float(np.sqrt(((coords[:,1]-cx)**2+
                                                        (coords[:,0]-cy)**2).min()))
    return {"changed_pixels_gt8_of_255":int(changed.sum()),
            "fraction":float(changed.mean()),"bbox_xyxy":bbox,
            "reticle_disc_radius_px":80,"reticle_disc_changed_pixels":center,
            "nearest_changed_pixel_to_reticle_px":nearest}


result = {"schema_version":1,"threshold_per_channel_8_of_255":8,
          "reticle_center_px":[cx,cy],"poses":{}}
for pose in ("Current","Proposed"):
    full = images[f"{pose}_Full"]
    bokuto = images[f"{pose}_BokutoOnly"]
    grip = images[f"{pose}_GripOnly"]
    paws = images[f"{pose}_PawsOnly"]
    result["poses"][pose] = {
        "full_vs_empty":metrics(full,empty),
        "grip_only_vs_empty":metrics(grip,empty),
        "paws_only_vs_empty":metrics(paws,empty),
        "paws_effect_in_full_vs_bokuto_only":metrics(full,bokuto),
    }
out = OUT / "metrics.json"
out.write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps(result,indent=2))
