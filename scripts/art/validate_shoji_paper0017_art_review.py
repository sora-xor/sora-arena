"""Independent geometry/material/provenance audit for Shoji Paper0017 ArtReview.

Run from repository root with Blender 5.2.2 LTS.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Environment/ShojiPaperArtReview"
DOJO = ROOT / "Content/SourceArt/Environment/NyaagyuDojo"
record = json.loads((OUT / "manifest.json").read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


assert record["schema_version"] == 1
assert record["status"].startswith("source-only")
assert record["source_page"] == "https://www.texturecan.com/details/281/"
assert record["license_page"] == "https://www.texturecan.com/terms/"
assert "CC0" in record["license"] and "not photographed" in record["source_type"]
assert sha(ROOT / record["source_dojo_blend"]) == record["source_dojo_blend_sha256"]
assert sha(OUT / record["source_blend"]) == record["source_blend_sha256"]
assert len(record["source_maps"]) == 4
for role,item in record["source_maps"].items():
    assert sha(OUT / item["file"]) == item["sha256"], role
derived = record["derived_translucency"]
assert "art estimate" in derived["interpretation"]
assert sha(OUT / derived["file"]) == derived["sha256"]
for filename,digest in record["renders"].items():
    assert sha(OUT / filename) == digest, filename
assert len(record["renders"]) == 8


def in_bay(name):
    return (name == "Shoji_Paper_0" or name == "Shoji_Pull_0" or
            name.startswith("Shoji_Jamb_0_") or
            name.startswith("Shoji_KumikoV_0_") or
            name.startswith("Shoji_KumikoH_0_"))


def shape(obj):
    values = {
        "type":obj.type,
        "vertices":[[round(float(v),7) for v in vert.co]
                    for vert in obj.data.vertices],
        "faces":[list(poly.vertices) for poly in obj.data.polygons],
        "matrix":[round(float(v),7) for row in obj.matrix_world for v in row],
        "modifiers":[(mod.name,mod.type) for mod in obj.modifiers],
    }
    return sha_bytes(json.dumps(values,sort_keys=True).encode())


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


bpy.ops.wm.open_mainfile(filepath=str(ROOT / record["source_dojo_blend"]))
original = {obj.name:shape(obj) for obj in bpy.data.objects
            if obj.type == "MESH" and in_bay(obj.name)}
assert len(original) == 16
bpy.ops.wm.open_mainfile(filepath=str(OUT / record["source_blend"]))
baseline = bpy.data.collections["ArtReview_OriginalDojoBay_Baseline"]
candidate = bpy.data.collections["ArtReview_Paper0017_OneBay_Candidate"]
assert len(baseline.objects) == len(candidate.objects) == 16
assert set(record["bay_source_names"]) == set(original)
for name,signature in original.items():
    base = bpy.data.objects[name]
    cand = bpy.data.objects["Candidate_"+name]
    assert shape(base) == signature, (name,"baseline geometry diverged")
    assert shape(cand) == signature, (name,"candidate geometry diverged")
    if name != "Shoji_Paper_0":
        assert base.data is cand.data, (name,"lattice mesh must be shared")
        assert [m.name for m in base.data.materials] == [m.name for m in cand.data.materials]
paper = bpy.data.objects["Candidate_Shoji_Paper_0"]
assert paper.data is not bpy.data.objects["Shoji_Paper_0"].data
assert len(paper.data.uv_layers) == 1 and paper.data.uv_layers[0].name == "UV0"
coords = [loop.uv for loop in paper.data.uv_layers[0].data]
assert all(math.isfinite(v) for p in coords for v in p)
assert max(p.x for p in coords)-min(p.x for p in coords) > 1.5
assert max(p.y for p in coords)-min(p.y for p in coords) > 3
mat = paper.data.materials[0]
assert mat.name == "M_ArtReview_Paper0017_FiberTranslucency"
nodes = mat.node_tree.nodes
assert any(node.type == "UVMAP" and node.uv_map == "UV0" for node in nodes)
assert any(node.type == "BSDF_TRANSLUCENT" for node in nodes)
assert any(node.type == "MAPPING" for node in nodes) is False
assert any(node.label == "Art estimate, NOT measured paper transmission"
           for node in nodes)
for role,item in record["source_maps"].items():
    node = nodes["Paper0017_"+role]
    assert Path(bpy.path.abspath(node.image.filepath)).resolve() == (OUT / item["file"]).resolve()
    node.image.reload()
    assert tuple(node.image.size) == (2048,2048), (role, tuple(node.image.size), node.image.filepath)
translucency = nodes["ArtEstimate_Translucency"]
assert translucency.label == "Art estimate, NOT measured paper transmission"
assert Path(bpy.path.abspath(translucency.image.filepath)).resolve() == (OUT / derived["file"]).resolve()
translucency.image.reload()
assert tuple(translucency.image.size) == (2048,2048)
assert any(link.from_node == translucency and link.to_node.type == "MIX_SHADER"
           for link in mat.node_tree.links)
assert math.isclose(bpy.data.objects["Camera_1m_Frontage"].location.y, -3.765, abs_tol=1e-5)
assert math.isclose(bpy.data.objects["Camera_3m_Frontage"].location.y, -5.765, abs_tol=1e-5)
for filename in record["renders"]:
    img = bpy.data.images.load(str(OUT / filename),check_existing=True)
    assert tuple(img.size) == (1600,900)
print("SHOJI_PAPER0017_SOURCE_VALID",len(original),len(record["renders"]),flush=True)
