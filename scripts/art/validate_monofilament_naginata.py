"""Independently verify the editable naginata and one-mesh FBX round trip.

Run: blender -b Content/SourceArt/Weapons/MonofilamentNaginata/\
Nyaagyu_MonofilamentNaginata.blend --python scripts/art/validate_monofilament_naginata.py
This does not establish Unreal appearance, performance, or combat behavior.
"""

import atexit
import hashlib
import json
import os
from pathlib import Path
import sys

import bpy
from mathutils import Vector


passed = False


def fail_exit():
    if not passed:
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(1)


atexit.register(fail_exit)
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Weapons/MonofilamentNaginata"
manifest = json.loads((OUT / "manifest.json").read_text())
name = "SM_Nyaagyu_MonofilamentNaginata"
assert bpy.app.version[:2] == (5, 2), bpy.app.version_string
assert Path(bpy.data.filepath).resolve() == (OUT / manifest["source_blend"]).resolve()
assert manifest["schema_version"] == 1 and manifest["name"] == name
assert manifest["weapon_id"] == 12 and manifest["weapon_name_en"] == "Monofilament Naginata"
assert manifest["generator"] == "scripts/art/create_monofilament_naginata.py"
assert manifest["validator"] == "scripts/art/validate_monofilament_naginata.py"
assert manifest["fbx"] == name + ".fbx"
assert manifest["unreal_asset"] == f"/Game/ArtReview/Weapons/{name}.{name}"
assert manifest["mesh_origin_m"] == [0, 0, 0]
assert manifest["local_forward"] == "+X toward blade tip; +Z up"
assert manifest["rear_grip_center_m"] == [-.47, 0, 0]
assert manifest["front_grip_center_m"] == [.445, 0, 0]
assert manifest["muzzle_center_m"] is None
assert 2.2 < manifest["length_m"] < 2.4
assert -0.91 < manifest["bounds_m"]["min"][0] < -.82
assert 1.42 < manifest["bounds_m"]["max"][0] < 1.48
assert manifest["external_images"] == []
assert "Original project-owned" in manifest["license"]
assert "no third-party or purchased" in manifest["license"]
assert "Principled BSDF" in manifest["material_provenance"]
assert "material/scale/appearance approval pending" in manifest["scope"]
assert 10 < manifest["source_parts"] < 80
assert 3000 < manifest["source_triangles"] < 50000
for filename, key in ((manifest["source_blend"], "blend_sha256"),
                      (manifest["fbx"], "fbx_sha256"),
                      (manifest["preview"], "preview_sha256"),
                      (manifest["detail_preview"], "detail_preview_sha256")):
    path = OUT / filename
    assert path.stat().st_size > 1000, path
    assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest[key], path
assert not any(image.source == "FILE" for image in bpy.data.images)

collection = bpy.data.collections.get("Naginata_Editable")
assert collection is not None
parts = [obj for obj in collection.objects if obj.type == "MESH"]
assert len(parts) == manifest["source_parts"]
assert sum(len(face.vertices) - 2 for obj in parts for face in obj.data.polygons) == manifest["source_triangles"]
assert all(obj.get("author", "").startswith("Original SORA Arena") for obj in parts)
part_names = {obj.name for obj in parts}
assert {"SmokedOakTaperedShaft", "ForgedCurvedNaginataBlade",
        "KuchiganeBladeSocket", "CeramicEdgeCapacitor",
        "RestrainedMonofilamentEdgeInlay"} <= part_names
assert not any(obj.name == name for obj in collection.objects)
for prefix, minimum, maximum in (("RearIndigoIto", -.62, -.32),
                                 ("FrontIndigoIto", .29, .60)):
    grip_parts = [obj for obj in parts if obj.name.startswith(prefix)]
    assert len(grip_parts) == 2
    points = [obj.matrix_world @ vertex.co for obj in grip_parts for vertex in obj.data.vertices]
    assert abs(min(point.x for point in points) - minimum) < .01
    assert abs(max(point.x for point in points) - maximum) < .01
materials = {mat.name: mat for mat in bpy.data.materials}
for expected in ("M_Nag_SmokedOak", "M_Nag_IndigoUrushi", "M_Nag_WovenIndigoIto",
                 "M_Nag_ForgedTamahagane", "M_Nag_PolishedHa", "M_Nag_Hamon",
                 "M_Nag_BlackenedIron", "M_Nag_AgedBronze", "M_Nag_IvoryCeramic",
                 "M_Nag_InductionCopper", "M_Nag_MonofilamentInlay"):
    assert expected in materials
    bsdf = materials[expected].node_tree.nodes.get("Principled BSDF")
    assert bsdf is not None
    assert 0 <= bsdf.inputs["Metallic"].default_value <= 1
    assert 0 < bsdf.inputs["Roughness"].default_value <= 1

fbx = OUT / manifest["fbx"]
fbx_bytes = fbx.read_bytes()
assert fbx_bytes.startswith(b"Kaydara FBX Binary")
assert b"/Users/" not in fbx_bytes and b"/Volumes/" not in fbx_bytes
before = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=str(fbx))
imported = [obj for obj in set(bpy.data.objects) - before if obj.type == "MESH"]
assert len(imported) == 1 and imported[0].name == name, [obj.name for obj in imported]
render = imported[0]
corners = [render.matrix_world @ Vector(corner) for corner in render.bound_box]
for axis in range(3):
    assert abs(min(point[axis] for point in corners) - manifest["bounds_m"]["min"][axis]) < .02
    assert abs(max(point[axis] for point in corners) - manifest["bounds_m"]["max"][axis]) < .02
assert sum(len(face.vertices) - 2 for face in render.data.polygons) == manifest["source_triangles"]
assert len(render.data.uv_layers) >= 1
slots = {slot.material.name.split(".", 1)[0] for slot in render.material_slots if slot.material}
assert {"M_Nag_SmokedOak", "M_Nag_IndigoUrushi", "M_Nag_ForgedTamahagane",
        "M_Nag_PolishedHa", "M_Nag_AgedBronze", "M_Nag_IvoryCeramic",
        "M_Nag_MonofilamentInlay"} <= slots
print("NAGINATA_FBX_ROUNDTRIP_PASS", len(parts), manifest["source_triangles"],
      manifest["bounds_m"], sorted(slots))
passed = True
