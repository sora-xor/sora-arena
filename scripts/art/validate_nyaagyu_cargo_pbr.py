"""Validate original cargo texture generation, exact wraps and hashes.

Run: python3 scripts/art/validate_nyaagyu_cargo_pbr.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image


ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"Content/SourceArt/Environment/NyaagyuCargoStack"
PBR=OUT/"PBR"
record=json.loads((PBR/"manifest.json").read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert record["schema_version"]==1
assert record["generator"]=="scripts/art/create_nyaagyu_cargo_pbr.py"
assert sha(ROOT/record["generator"])==record["generator_sha256"]
assert record["seed"]==416819
assert record["origin"]=="Original project-authored deterministic procedural pixels; no external texture inputs"
assert "no third-party image" in record["license"]
assert [item["name"] for item in record["sets"]]==["Wood","Straw","IndigoCloth"]
assert set(record["material_slots"])=={
    "M_Cargo_AgedTimber","M_Cargo_DarkInterior","M_Cargo_WornEdge",
    "M_Cargo_StrawWrap","M_Cargo_HempRope","M_Cargo_IndigoCloth"}
for item in record["sets"]:
    assert item["resolution"]==[2048,2048]
    assert {part["channel"] for part in item["maps"]}=={"Albedo","NormalDX","ORM"}
    for part in item["maps"]:
        path=(PBR/part["file"]).resolve()
        assert path.parent==PBR.resolve()
        assert sha(path)==part["sha256"]
        pixels=np.asarray(Image.open(path).convert("RGB"))
        assert pixels.shape==(2048,2048,3)
        assert np.array_equal(pixels[0],pixels[-1])
        assert np.array_equal(pixels[:,0],pixels[:,-1])
        if part["channel"]=="Albedo":
            assert float(pixels.std())>8
        elif part["channel"]=="NormalDX":
            assert 205<float(pixels[:,:,2].mean())<=255
        else:
            assert pixels[:,:,0].min()>=220
            assert abs(float(pixels[:,:,2].mean())-round(item["metallic"]*255))<1
    print("NYAAGYU_CARGO_PBR_SET_PASS",item["name"])
print("NYAAGYU_CARGO_PBR_PROVENANCE_PASS",len(record["sets"]),len(record["material_slots"]))
