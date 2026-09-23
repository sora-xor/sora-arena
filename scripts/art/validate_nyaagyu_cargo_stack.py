"""Validate editable cargo source, envelope, provenance and FBX round-trip.

Run: blender -b Content/SourceArt/Environment/NyaagyuCargoStack/Nyaagyu_CargoStack.blend \
  --python scripts/art/validate_nyaagyu_cargo_stack.py
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


passed=False


def require_success():
    if not passed:
        sys.stdout.flush();sys.stderr.flush();os._exit(1)


atexit.register(require_success)
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"Content/SourceArt/Environment/NyaagyuCargoStack"
record=json.loads((OUT/"manifest.json").read_text())
pbr=json.loads((OUT/"PBR/manifest.json").read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert bpy.app.version[:2]==(5,2)
assert record["schema_version"]==1
assert record["name"]=="SM_Nyaagyu_CargoStack"
assert record["generator"]=="scripts/art/create_nyaagyu_cargo_stack.py"
assert record["unreal_asset"]=="/Game/Generated/Environment/Props/SM_Nyaagyu_CargoStack.SM_Nyaagyu_CargoStack"
assert record["collision_envelope_m"]==[2.30,1.80,1.40]
assert record["collision"].startswith("Visual only")
assert record["nanite_windows"] is True
assert record["mac_conventional_fallback"]=={
    "source_fbx":"SM_Nyaagyu_CargoStack.fbx",
    "fallback_percent_triangles":1.0,
    "fallback_target":"PercentTriangles",
    "generate_fallback":"Enabled",
    "render_config":"Config/Mac/MacEngine.ini"}
mac_config=(ROOT/record["mac_conventional_fallback"]["render_config"]).read_text()
assert "r.Nanite=0" in mac_config and "r.Nanite.ProxyRenderMode=0" in mac_config
assert record["pbr_manifest_sha256"]==sha(OUT/"PBR/manifest.json")
assert Path(bpy.data.filepath).resolve()==(OUT/record["source_blend"]).resolve()
for filename,key in ((record["source_blend"],"blend_sha256"),
                     (record["fbx"],"fbx_sha256"),
                     (record["review_before"],"review_before_sha256"),
                     (record["review_after"],"review_after_sha256")):
    path=OUT/filename
    assert path.stat().st_size>1000
    assert sha(path)==record[key],path
logo=(OUT/record["insignia_source"]).resolve()
assert sha(logo)==record["insignia_sha256"]
collection=bpy.data.collections["NyaagyuCargo_Editable"]
parts=[obj for obj in collection.objects if obj.type=="MESH"]
assert len(parts)==record["source_parts"] and len(parts)>100
assert all(obj.get("provenance")=="Original SORA Arena procedural cargo geometry" for obj in parts)
assert sum(len(poly.vertices)-2 for obj in parts for poly in obj.data.polygons)==record["source_triangles"]
assert all(obj.data.uv_layers for obj in parts)
assert all(len(obj.data.uv_layers.active.data)==len(obj.data.loops) for obj in parts)
names={obj.name for obj in parts}
for target in ("LeftRiceCrate_structural_core","RightClothCrate_structural_core",
               "Rice_tawara_inspired_bundle_0","Rice_tawara_inspired_bundle_1",
               "Indigo_craftspeople_cloth_bundle","Pallet_runner_+0.00"):
    assert target in names,target
assert sum("_front_" in name and "_plank_" in name for name in names)==24
assert sum("_nail_" in name for name in names)==48
assert sum("_lashing_" in name for name in names)==4
assert len(record["exact_sora_kamon_objects"])==2
for name in record["exact_sora_kamon_objects"]:
    assert name in names
    assert collection.objects[name]["source_svg_sha256"]==record["insignia_sha256"]

for slot in pbr["material_slots"]:
    material=bpy.data.materials[slot]
    images=[node.image for node in material.node_tree.nodes if node.type=="TEX_IMAGE"]
    assert len(images)==3
    assert all(image.packed_file is not None for image in images)

points=[obj.matrix_world @ vert.co for obj in parts for vert in obj.data.vertices]
bounds={"min":[round(min(point[i] for point in points),4) for i in range(3)],
        "max":[round(max(point[i] for point in points),4) for i in range(3)]}
assert bounds==record["bounds_m"]
assert bounds["min"][0]>=-1.15 and bounds["max"][0]<=1.15
assert bounds["min"][1]>=-.9 and bounds["max"][1]<=.9
assert bounds["min"][2]>=0 and bounds["max"][2]<=1.4
proxy=bpy.data.collections["Blender_Review_Only"].objects["Review_original_cover_cube"]
assert all(abs(proxy.dimensions[i]-record["collision_envelope_m"][i])<.001 for i in range(3))
assert proxy.hide_render

fbx=OUT/record["fbx"]
assert fbx.read_bytes().startswith(b"Kaydara FBX Binary")
assert b"/Users/" not in fbx.read_bytes()
before=set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=str(fbx))
imported=[obj for obj in set(bpy.data.objects)-before if obj.type=="MESH"]
assert len(imported)==1,imported
mesh=imported[0]
assert mesh.name.startswith("SM_Nyaagyu_CargoStack")
assert mesh.data.uv_layers and len(mesh.data.uv_layers[0].data)==len(mesh.data.loops)
slots=sorted(slot.material.name.split(".",1)[0] for slot in mesh.material_slots)
assert slots==record["material_slots"]
assert len(slots)==8
fbx_corners=[mesh.matrix_world @ Vector(corner) for corner in mesh.bound_box]
for axis in range(3):
    assert abs(min(point[axis] for point in fbx_corners)-bounds["min"][axis])<.02
    assert abs(max(point[axis] for point in fbx_corners)-bounds["max"][axis])<.02
print("NYAAGYU_CARGO_STACK_ROUNDTRIP_PASS",len(parts),record["source_triangles"],bounds,slots)
passed=True
