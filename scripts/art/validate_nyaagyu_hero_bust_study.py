"""Check the separate Nyaagyu bust study and independent Blender FBX round trip.

Run: blender -b Content/SourceArt/Characters/HeroBustStudy/Nyaagyu_HeroBustStudy.blend \
  --python scripts/art/validate_nyaagyu_hero_bust_study.py
This cannot establish Unreal rendering, photorealism, rig quality or frame rate.
"""

import atexit
import hashlib
import json
import os
import sys
from pathlib import Path

import bpy
from mathutils import Vector


validated = False


def fail_exit():
    # Blender can otherwise exit with success after a Python assertion fails.
    if not validated:
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(1)


atexit.register(fail_exit)
root = Path(__file__).resolve().parents[2]
out = root / "Content/SourceArt/Characters/HeroBustStudy"
old = root / "Content/SourceArt/Characters/Hero/manifest.json"
manifest = json.loads((out / "manifest.json").read_text())
name = "SM_Nyaagyu_HeroBustStudy"
assert bpy.app.version[:2] == (5, 2), bpy.app.version_string
assert Path(bpy.data.filepath).resolve() == (out / manifest["source_blend"]).resolve()
assert manifest["schema_version"] == 1 and manifest["name"] == name
assert manifest["generator"] == "scripts/art/create_nyaagyu_hero_bust_study.py"
assert manifest["scope"].startswith("Unrigged static head/upper-body visual study")
assert "No Unreal import" in manifest["limitations"]
assert manifest["external_images"] == []
assert json.loads(old.read_text())["name"] == "SM_Nyaagyu_HeroCharacter"
assert 10000 < manifest["source_triangles"] < 160000
assert 25000 < manifest["fur_cards"] < 36000
assert manifest["head_voxel_m"] == .006
assert manifest["review_render"] == {"renderer":"Blender Cycles","resolution_px":[1200,1200],"samples":32,"denoising":True}
assert manifest["runtime_performance"].startswith("Unmeasured.")
assert .85 < manifest["bounds_m"]["min"][2] < .90
assert 1.84 < manifest["bounds_m"]["max"][2] < 1.90
assert manifest["local_forward"] == "+X face-forward; +Z up"
assert "Original project-owned" in manifest["license"]
assert not any(image.source == "FILE" for image in bpy.data.images)
for filename, digest in (
    (manifest["source_blend"], "blend_sha256"),
    (manifest["fbx"], "fbx_sha256"),
    (manifest["portrait_preview"], "portrait_preview_sha256"),
    (manifest["face_preview"], "face_preview_sha256"),
):
    path = out / filename
    assert path.stat().st_size > 1000, path
    assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest[digest], path
collection = bpy.data.collections.get("NyaagyuHeroBust_Editable")
assert collection is not None
parts = [obj for obj in collection.objects if obj.type == "MESH"]
assert len(parts) == manifest["source_parts"]
assert sum(len(face.vertices)-2 for obj in parts for face in obj.data.polygons) == manifest["source_triangles"]
assert sum(obj.get("card_count", 0) for obj in parts) == manifest["fur_cards"]
assert all(obj.get("authorship", "").startswith("Original SORA Arena") for obj in parts)
assert not any(obj.name == name for obj in parts)
head = next(obj for obj in parts if obj.name == "FusedAnatomicalHead")
assert head.get("method", "").startswith("Original merged feline anatomy")
assert head.data.color_attributes.get("CoatColor") is not None
cards = next(obj for obj in parts if obj.name == "FurCards_ShortScalpAndCheeks")
assert cards.get("card_topology", "").startswith("single tapered opaque triangle")
assert len(cards.data.polygons) == cards["card_count"]
assert len([obj for obj in parts if obj.name.startswith("FurCards_Pinna_")]) == 2
assert {"M_Bust_CoatVertexColor", "M_Bust_WeatheredIndigoLinen",
        "M_Bust_SmokedUrushi", "M_Bust_GoldGreenIris"} <= set(manifest["materials"])

fbx = out / manifest["fbx"]
assert fbx.read_bytes().startswith(b"Kaydara FBX Binary")
assert b"/Users/" not in fbx.read_bytes()
before = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=str(fbx))
imported = [obj for obj in set(bpy.data.objects)-before if obj.type == "MESH"]
assert len(imported) == 1 and imported[0].name == name, [obj.name for obj in imported]
joined = imported[0]
assert sum(len(face.vertices)-2 for face in joined.data.polygons) == manifest["source_triangles"]
points = [joined.matrix_world @ Vector(corner) for corner in joined.bound_box]
for axis in range(3):
    assert abs(min(point[axis] for point in points) - manifest["bounds_m"]["min"][axis]) < .02
    assert abs(max(point[axis] for point in points) - manifest["bounds_m"]["max"][axis]) < .02
slots = {slot.material.name.split(".", 1)[0] for slot in joined.material_slots if slot.material}
assert {"M_Bust_CoatVertexColor", "M_Bust_FurBrownCards", "M_Bust_EarSkin",
        "M_Bust_GoldGreenIris", "M_Bust_WeatheredIndigoLinen",
        "M_Bust_SmokedUrushi"} <= slots, slots
print("NYAAGYU_HERO_BUST_ROUNDTRIP_PASS",manifest["source_parts"],
      manifest["source_triangles"],manifest["fur_cards"],manifest["bounds_m"],len(slots))
validated = True
