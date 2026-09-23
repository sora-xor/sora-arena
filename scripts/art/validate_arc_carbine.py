"""Independently verify the editable Arc carbine and Blender FBX round trip.

Run: blender -b Content/SourceArt/Weapons/Original/Nyaagyu_ArcCarbine.blend \
  --python scripts/art/validate_arc_carbine.py
The check cannot substitute for a UE import or in-game visual/performance review.
"""

import atexit
import hashlib
import json
import os
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sora_kamon_validation import (PINNED_SVG_SHA256, assert_path_objects,
                                   assert_paths_embedded, expected_paths,
                                   reference_paths)


validated = False


def fail_exit():
    # Blender can otherwise return zero after an uncaught script assertion.
    if not validated:
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(1)


atexit.register(fail_exit)
root = Path(__file__).resolve().parents[2]
out = root / "Content/SourceArt/Weapons/Original"
palette = root / "Content/SourceArt/Environment/PolyHaven"
manifest = json.loads((out / "arc_carbine_manifest.json").read_text())
name = "SM_Nyaagyu_ArcCarbine"
assert bpy.app.version[:2] == (5, 2), bpy.app.version_string
assert Path(bpy.data.filepath).resolve() == (out / manifest["source_blend"]).resolve()
assert manifest["schema_version"] == 1 and manifest["name"] == name
assert manifest["generator"] == "scripts/art/create_arc_carbine.py"
assert manifest["unreal_asset"] == f"/Game/Generated/Meshes/{name}.{name}"
assert manifest["fbx"] == name + ".fbx"
assert manifest["mesh_origin_m"] == [0, 0, 0]
assert manifest["grip_web_m"] == [-.11, 0, -.05]
assert manifest["grip_palm_center_m"] == [-.11, 0, -.12]
assert manifest["palette_asset_ids"] == ["wood_planks_dirt", "rusty_metal_02"]
assert manifest["sora_kamon_svg_sha256"] == PINNED_SVG_SHA256
assert manifest["sora_kamon_placements"] == ["receiver_-1", "receiver_1"]
assert "Original project-owned geometry" in manifest["license"]
assert "CC0 Poly Haven" in manifest["license"]
assert 3000 < manifest["source_triangles"] < 30000
for filename, field in ((manifest["source_blend"], "blend_sha256"),
                        (manifest["fbx"], "fbx_sha256"),
                        (manifest["preview"], "preview_sha256")):
    path = out / filename
    assert path.stat().st_size > 1000, path
    assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest[field], path
palette_file = palette / "manifest.json"
assert hashlib.sha256(palette_file.read_bytes()).hexdigest() == manifest["palette_manifest_sha256"]
palette_manifest = json.loads(palette_file.read_text())
assert palette_manifest["asset_license"] == "CC0-1.0"
records = {record["asset_id"]: record for record in palette_manifest["assets"]}
expected_images = set()
for asset_id in manifest["palette_asset_ids"]:
    record = records[asset_id]
    assert record["license"] == "CC0-1.0"
    assert {file["channel"].lower() for file in record["files"]} == {"diffuse", "nor_dx", "arm"}
    for file in record["files"]:
        path = palette / file["file"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == file["sha256"]
        expected_images.add(path.resolve())
linked_images = {Path(bpy.path.abspath(image.filepath)).resolve()
                 for image in bpy.data.images if image.source == "FILE"}
assert linked_images == expected_images, (linked_images, expected_images)
assert all(image.filepath.startswith("//../../Environment/PolyHaven/")
           for image in bpy.data.images if image.source == "FILE")
collection = bpy.data.collections.get("ArcCarbine_Editable")
assert collection is not None
parts = [obj for obj in collection.objects if obj.type == "MESH"]
assert len(parts) == manifest["source_parts"]
assert sum(len(face.vertices)-2 for obj in parts for face in obj.data.polygons) == manifest["source_triangles"]
assert all(obj.get("author", "").startswith("Original SORA Arena") for obj in parts)
assert any(obj.name.startswith("CopperInductionCoil_") for obj in parts)
assert any(obj.name == "PistolGrip_OakCore" for obj in parts)
assert any(obj.name == "MuzzleEmitter" for obj in parts)
assert not any(obj.name == name for obj in collection.objects)
assert not any(obj.name.startswith(("Crest_Whisker_", "Crest_Nose_")) for obj in parts)
source_paths = reference_paths(root)
kamon = {}
for side in (-1, 1):
    placement = f"receiver_{side}"
    expected = expected_paths(source_paths, (-.009, side*.060, .030), .054, "XZ")
    assert_path_objects(parts, placement, expected)
    kamon[placement] = expected

fbx = out / manifest["fbx"]
assert fbx.read_bytes().startswith(b"Kaydara FBX Binary")
assert b"/Users/" not in fbx.read_bytes()
before = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=str(fbx))
imported = [obj for obj in set(bpy.data.objects)-before if obj.type == "MESH"]
assert len(imported) == 1 and imported[0].name == name, [obj.name for obj in imported]
render = imported[0]
corners = [render.matrix_world @ Vector(corner) for corner in render.bound_box]
for axis in range(3):
    assert abs(min(point[axis] for point in corners) - manifest["bounds_m"]["min"][axis]) < .02
    assert abs(max(point[axis] for point in corners) - manifest["bounds_m"]["max"][axis]) < .02
assert sum(len(face.vertices)-2 for face in render.data.polygons) == manifest["source_triangles"]
assert len(render.data.uv_layers) >= 1
assert_paths_embedded((render.matrix_world @ vertex.co for vertex in render.data.vertices), kamon)
slots = {slot.material.name.split(".", 1)[0] for slot in render.material_slots if slot.material}
assert {"M_Arc_OxbloodUrushi", "M_Arc_Gunmetal", "M_Arc_AgedBronze",
        "M_Arc_CoilCopper", "M_Arc_IonJade", "M_Arc_Timber",
        "M_Arc_PatinatedMetal"} <= slots, slots
print("ARC_CARBINE_FBX_ROUNDTRIP_PASS", manifest["source_parts"],
      manifest["source_triangles"], manifest["bounds_m"], sorted(slots))
validated = True
