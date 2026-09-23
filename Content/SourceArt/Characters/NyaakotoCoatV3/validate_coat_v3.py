"""Validate the isolated Nyaakoto V3 source and static-mesh FBX round trip."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parent
manifest = json.loads((ROOT / "manifest.json").read_text())
assert manifest["production_status"].startswith("REVIEW_ONLY")
assert manifest["user_reference_embedded"] is False
base = ROOT.parent / "NyaakotoAnatomyV2" / "Nyaakoto_FacialAnatomy_V2_Study.blend"
assert hashlib.sha256(base.read_bytes()).hexdigest() == manifest["v2_source_blend_sha256"]
for name, expected in manifest["files_sha256"].items():
    path = ROOT / name
    assert path.is_file(), name
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, name

bpy.ops.wm.open_mainfile(filepath=str(ROOT / manifest["source_blend"]))
head = bpy.data.objects.get("SM_Nyaakoto_HeadCoat_V3_Study")
assert head and head.type == "MESH"
assert len(head.data.polygons) >= 70000
assert head.data.uv_layers and head.data.uv_layers[0].name == "UVMap"
assert "CoatMix" in head.data.color_attributes
assert len([o for o in bpy.data.objects if o.type == "MESH"]) >= 45
assert all(o.data.uv_layers for o in bpy.data.objects if o.type == "MESH")
for side in (-1, 1):
    ear = bpy.data.objects.get(f"Ear_CuppedOrganic_{side}")
    assert ear and "EarSkinMix" in ear.data.color_attributes
    assert bpy.data.objects.get(f"Ear_AuralFur_{side}_V3")
    assert bpy.data.objects.get(f"Eye_globe_{side}")
groom = bpy.data.objects.get("Groom_Nyaakoto_ShortDirectional_V3")
assert groom and groom.type == "CURVE"
assert len(groom.data.splines) == manifest["groom_strands"]
assert len(groom.data.splines) >= 25000
assert not any(o.type == "ARMATURE" for o in bpy.data.objects)
for name in (
    "T_Nyaakoto_CoatV3_Albedo.png",
    "T_Nyaakoto_CoatV3_NormalGL.png",
    "T_Nyaakoto_CoatV3_ORM.png",
):
    image = next((im for im in bpy.data.images if im.name == name), None)
    assert image and image.packed_file and tuple(image.size) == (2048, 2048), name

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=str(ROOT / manifest["fbx"]))
meshes = [o for o in bpy.data.objects if o.type == "MESH"]
assert len(meshes) >= 45
assert all(o.data.uv_layers for o in meshes)
rt = bpy.data.objects.get("SM_Nyaakoto_HeadCoat_V3_Study")
assert rt and len(rt.data.polygons) >= 70000
print("NYAAKOTO_COAT_V3_SOURCE_VALID", len(meshes), "FBX meshes", manifest["groom_strands"], "source strands")
