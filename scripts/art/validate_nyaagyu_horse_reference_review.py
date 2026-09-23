"""Check fixed-view reference renders, eight-angle turntable and source pin."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image


ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"Content/SourceArt/Horses/Nyaagyu/AnatomyStudy/ReferenceReview"


def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


parser=argparse.ArgumentParser()
parser.add_argument("--archive",type=Path,help="Optional downloaded OpenGameArt horse.zip for source pin check")
args=parser.parse_args()
record=json.loads((OUT/"comparison_manifest.json").read_text())
assert record["source_page"]=="https://opengameart.org/content/realtime-ranchers-3d-model-pack"
assert record["archive_url"]=="https://opengameart.org/sites/default/files/horse.zip"
assert record["page_license"].startswith("CC0 1.0")
assert record["reference_mesh_in_game"] is False
assert record["rancher_source_triangles"]==14986
assert len(record["archive_sha256"])==64
if args.archive:
    assert sha(args.archive)==record["archive_sha256"]

views=record["views"]
assert set(views)=={"rancher_cc0","nyaagyu_anatomy_bare","nyaagyu_study_saddled"}
for label,images in views.items():
    assert set(images)=={"profile","front"}
    for view,digest in images.items():
        path=OUT/f"{label}_{view}.png"
        assert sha(path)==digest,path
        with Image.open(path) as image:
            assert image.size==(1400,900) and image.mode in {"RGBA","RGB"}

turntable=record["turntable_sha256"]
assert set(turntable)=={str(degrees) for degrees in range(0,360,45)}
for degrees,digest in turntable.items():
    path=OUT/f"nyaagyu_study_turntable_{int(degrees):03}.png"
    assert sha(path)==digest,path
    with Image.open(path) as image:
        assert image.size==(1400,900)

with Image.open(OUT/"nyaagyu_before_profile.png") as before:
    assert before.size==(1400,900)

kura=record["kura_structural_bounds"]["extent_m"]
abumi=record["abumi_left_toe_bounds"]["extent_m"]
assert len(kura)==len(abumi)==3
assert all(.35<=v<=.41 for v in kura[:2]) and .26<=kura[2]<=.30
assert .28<=abumi[0]<=.31 and .12<=abumi[1]<=.14 and .25<=abumi[2]<=.28

print("NYAAGYU_HORSE_CC0_REFERENCE_REVIEW_VALID",len(views)*2,len(turntable),
      "kura",kura,"abumi",abumi)
