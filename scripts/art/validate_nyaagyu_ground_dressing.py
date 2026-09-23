"""Validate the roadside dressing Blender source and FBX round-trip.

Run: blender -b Content/SourceArt/Environment/NyaagyuGroundDressing/Nyaagyu_RoadsideLeafSilt.blend \
  --python scripts/art/validate_nyaagyu_ground_dressing.py
"""

from __future__ import annotations

import atexit
import hashlib
import json
import os
from pathlib import Path
import sys

import bpy
from mathutils import Vector


passed = False


def require_success():
    if not passed:
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(1)


atexit.register(require_success)
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Environment/NyaagyuGroundDressing"
record = json.loads((OUT / "manifest.json").read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert bpy.app.version[:2] == (5,2)
assert record["schema_version"] == 1
assert record["name"] == "SM_Nyaagyu_RoadsideLeafSilt_4m"
assert record["generator"] == "scripts/art/create_nyaagyu_ground_dressing.py"
assert record["generator_sha256"] == sha(ROOT / record["generator"])
assert record["unreal_asset"] == "/Game/Generated/Environment/Props/SM_Nyaagyu_RoadsideLeafSilt_4m.SM_Nyaagyu_RoadsideLeafSilt_4m"
assert record["nominal_road_length_m"] == 4.0
assert record["orientation"] == "Local X follows Estate road; +Y points outward from road center; +Z up"
assert record["collision"].startswith("Visual only")
assert record["nanite_windows"] is True
assert record["mac_conventional_fallback"] == {
    "source_fbx": "SM_Nyaagyu_RoadsideLeafSilt_4m.fbx",
    "fallback_percent_triangles": 1.0,
    "fallback_target": "PercentTriangles",
    "generate_fallback": "Enabled",
    "render_config": "Config/Mac/MacEngine.ini",
}
mac_config = (ROOT / record["mac_conventional_fallback"]["render_config"]).read_text()
assert "r.Nanite=0" in mac_config and "r.Nanite.ProxyRenderMode=0" in mac_config
assert Path(bpy.data.filepath).resolve() == (OUT / record["source_blend"]).resolve()
for filename,key in ((record["source_blend"],"blend_sha256"),
                     (record["fbx"],"fbx_sha256"),
                     (record["review"],"review_sha256"),
                     (record["scatter_review"],"scatter_review_sha256")):
    path=OUT/filename
    assert path.stat().st_size>1000 and sha(path)==record[key],path

scan=json.loads((OUT/"ScanForestLeaves02/manifest.json").read_text())
assert record["new_scan_manifest_sha256"] == sha(OUT/"ScanForestLeaves02/manifest.json")
assert scan["asset_id"] == "forest_leaves_02" and scan["license"] == "CC0-1.0"
assert scan["authors"] == {"Rob Tuytel":"All"}
assert {item["channel"] for item in scan["files"]} == {"Diffuse","nor_dx","arm"}
for item in scan["files"]:
    path=OUT/"ScanForestLeaves02"/item["file"]
    assert path.stat().st_size == item["bytes"] and sha(path) == item["sha256"]
    assert item["url"].startswith("https://dl.polyhaven.org/")
assert set(record["dependencies"]) == {"DampSilt","ForestLitter","RiverStone"}
for dep in record["dependencies"].values():
    assert dep["license"] == "CC0-1.0" and dep["license_url"] == "https://polyhaven.com/license"
    assert dep["source_url"].startswith("https://polyhaven.com/a/") and dep["authors"]
    assert set(dep["files"]) == {"Albedo","NormalDX","ORM"}
    for file in dep["files"].values():
        path=(ROOT/file["repo_path"]).resolve()
        assert (path.is_relative_to((ROOT/"Content/SourceArt/Environment/PolyHaven").resolve())
                or path.is_relative_to((OUT/"ScanForestLeaves02").resolve())
                or path.is_relative_to((ROOT/"Content/SourceArt/Environment/NyaagyuEstateWall/ScanRock01").resolve()))
        assert sha(path) == file["sha256"]
        assert file["upstream_url"].startswith("https://dl.polyhaven.org/")

slots={"M_Ground_DampSilt","M_Ground_LeafUmber","M_Ground_LeafOchre",
       "M_Ground_Moss","M_Ground_RiverStone","M_Ground_WetStone"}
assert set(record["material_slots"]) == slots
assert set(record["slot_definitions"]) == slots
for slot,definition in record["slot_definitions"].items():
    assert definition["source"] in record["dependencies"] and len(definition["tint"])==3
    material=bpy.data.materials[slot]
    images=[node.image for node in material.node_tree.nodes if node.type=="TEX_IMAGE"]
    assert len(images)==3 and all(image.packed_file for image in images)

objects=list(bpy.data.collections["NyaagyuRoadside_Editable"].objects)
parts=[obj for obj in objects if obj.type=="MESH"]
assert len(parts)==record["source_parts"] and len(parts)>=180
assert all(obj.get("provenance")=="Original project-authored organic roadside geometry" for obj in parts)
assert all(obj.data.uv_layers and obj.data.uv_layers[0].name=="UVMap" for obj in parts)
assert all(obj.data.color_attributes and obj.data.color_attributes[0].name=="EdgeBlend" for obj in parts)
assert any(any(color.color[3]<.01 for color in obj.data.color_attributes["EdgeBlend"].data)
           for obj in parts if obj.name.startswith(("Silt_lens_","Moss_hummock_")))
assert sum(len(poly.vertices)-2 for obj in parts for poly in obj.data.polygons)==record["source_triangles"]
names=[obj.name for obj in parts]
assert sum(n.startswith("Silt_lens_") for n in names)==5
assert sum(n.startswith("Moss_hummock_") for n in names)==17
assert sum(n.startswith("Irregular_stone_") for n in names)==22
assert sum(n.startswith("Fallen_leaf_") for n in names)==126
assert sum(n.startswith("Twig_") for n in names)==22
assert sum(n.startswith("Moss_sprigs_") for n in names)==17
points=[obj.matrix_world@vert.co for obj in parts for vert in obj.data.vertices]
bounds={"min":[round(min(p[i] for p in points),4) for i in range(3)],
        "max":[round(max(p[i] for p in points),4) for i in range(3)]}
assert bounds==record["bounds_m"]
assert -2.2<=bounds["min"][0] and bounds["max"][0]<=2.2
assert -1.3<=bounds["min"][1] and bounds["max"][1]<=1.3
assert -.02<=bounds["min"][2] and bounds["max"][2]<=.2
assert "Review_existing_terrain_only" in bpy.data.collections["Blender_Review_Only"].objects
assert (OUT/record["fbx"]).read_bytes().startswith(b"Kaydara FBX Binary")
assert b"/Users/" not in (OUT/record["fbx"]).read_bytes()

before=set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=str(OUT/record["fbx"]))
imported=[obj for obj in set(bpy.data.objects)-before if obj.type=="MESH"]
assert len(imported)==1
mesh=imported[0]
assert mesh.data.uv_layers and mesh.data.uv_layers[0].name=="UVMap"
assert mesh.data.color_attributes and mesh.data.color_attributes[0].name=="EdgeBlend"
assert record["placement_variants"] == [
    {"yaw_deg":14.0,"uniform_scale":.92,"review_x_m":-4.25,"review_y_m":.35},
    {"yaw_deg":171.0,"uniform_scale":1.04,"review_x_m":0.0,"review_y_m":-.22},
    {"yaw_deg":-22.0,"uniform_scale":.87,"review_x_m":4.18,"review_y_m":.40},
]
imported_slots=sorted(slot.material.name.split(".",1)[0] for slot in mesh.material_slots)
assert imported_slots==record["material_slots"]
corners=[mesh.matrix_world@Vector(p) for p in mesh.bound_box]
for axis in range(3):
    assert abs(min(p[axis] for p in corners)-bounds["min"][axis])<.02
    assert abs(max(p[axis] for p in corners)-bounds["max"][axis])<.02
print("NYAAGYU_GROUND_DRESSING_ROUNDTRIP_PASS",len(parts),record["source_triangles"],bounds,imported_slots)
passed=True
