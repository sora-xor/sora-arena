"""Measure unchanged-grid paper ROI luminance at 1m/3m in raw A/B renders.

Run with host Python/Pillow/NumPy. No image pixels are modified.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Environment/ShojiPaperArtReview"
record = json.loads((OUT / "manifest.json").read_text())
assert len(record["renders"]) == 8
images = {}
for filename,digest in record["renders"].items():
    path = OUT / filename
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    images[filename] = np.asarray(Image.open(path).convert("RGB"),dtype=np.float32)
    assert images[filename].shape == (900,1600,3)


def roi_stats(image,rectangle):
    x0,y0,x1,y1 = rectangle
    crop = image[y0:y1,x0:x1]
    # Luminance in display-referred PNG only; not a radiometric paper measure.
    y = crop @ np.array([.2126,.7152,.0722],dtype=np.float32)
    return {"mean_display_luma_0_255":round(float(y.mean()),3),
            "std_display_luma_0_255":round(float(y.std()),3)}


regions = {"1m":[400,120,600,240],"3m":[680,230,720,270]}
metrics = {"schema_version":1,"scope":"display-referred raw-render ROI, not physical validation",
           "paper_only_rectangles_xyxy":regions,"conditions":{}}
for distance,region in regions.items():
    for light in ("Sun","Backlit"):
        entry = {}
        for role in ("Baseline","Candidate"):
            filename = f"Shoji_{distance}_{light}_{role}.png"
            entry[role] = roi_stats(images[filename],region)
        metrics["conditions"][f"{distance}_{light}"] = entry
(OUT / "metrics.json").write_text(json.dumps(metrics,indent=2)+"\n")
print(json.dumps(metrics,indent=2))
