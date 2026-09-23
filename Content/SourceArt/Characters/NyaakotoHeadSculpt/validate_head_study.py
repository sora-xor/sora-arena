"""Source-only Blender and FBX round-trip contract for the isolated head study."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parent
manifest = json.loads((ROOT / "manifest.json").read_text())
for relative, expected in manifest["files_sha256"].items():
    path = ROOT / relative
    assert path.is_file(), f"Missing study file: {relative}"
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    assert actual == expected, f"Hash changed: {relative}"

blend_path = ROOT / manifest["source_blend"]
bpy.ops.wm.open_mainfile(filepath=str(blend_path))
head = bpy.data.objects.get("SM_Nyaakoto_AnatomicalHead_Study")
assert head and head.type == "MESH"
assert len(head.data.polygons) >= 60000
assert head.data.uv_layers and head.data.uv_layers[0].name == "UVMap"
assert "CoatMix" in head.data.color_attributes
assert all(bpy.data.objects.get(f"Ear_CuppedCartilage_{s}") for s in (-1,1))
assert all(bpy.data.objects.get(f"Iris_UV0_{s}") for s in (-1,1))
assert all(bpy.data.objects.get(f"Cornea_ClearConvex_{s}") for s in (-1,1))
cards = bpy.data.objects.get("Fur_Cards_Head_Directional")
assert cards and len(cards.data.polygons) >= 400
assert all(o.data.uv_layers for o in bpy.data.objects if o.type == "MESH")

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=str(ROOT / manifest["fbx"]))
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
assert len(meshes) >= 100, len(meshes)
assert all(o.data.uv_layers for o in meshes), "FBX UV0 missing"
head_rt = bpy.data.objects.get("SM_Nyaakoto_AnatomicalHead_Study")
assert head_rt and len(head_rt.data.polygons) >= 60000
assert len(head_rt.data.uv_layers[0].data) == len(head_rt.data.loops)
zs = [v.co.z for v in head_rt.data.vertices]
assert 1.37 < min(zs) < 1.48, min(zs)
assert 1.77 < max(zs) < 1.85, max(zs)
print("NYAAKOTO_HEAD_STUDY_VALID",len(meshes),"FBX meshes",len(head_rt.data.polygons),"head polygons")
