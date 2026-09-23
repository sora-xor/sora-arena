"""Independent Blender 5.2.2 source and FBX round-trip for the Silk Foundry loom.

Run: blender -b Content/SourceArt/Environment/SilkFoundryLoom/SilkFoundry_LevyLoom.blend \
    --python scripts/art/validate_silk_foundry_loom.py
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
    # Blender sometimes reports process success despite an uncaught assertion.
    if not validated:
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(1)


atexit.register(fail_exit)
root = Path(__file__).resolve().parents[2]
out = root / "Content/SourceArt/Environment/SilkFoundryLoom"
palette = root / "Content/SourceArt/Environment/PolyHaven"
font = root / "Content/SourceArt/Fonts/NotoSansCJKjp-Regular.otf"
manifest = json.loads((out / "manifest.json").read_text())
name = "SM_SilkFoundry_LevyLoom"
assert bpy.app.version[:2] == (5, 2)
assert Path(bpy.data.filepath).resolve() == (out / manifest["source_blend"]).resolve()
assert manifest["schema_version"] == 1 and manifest["name"] == name
assert manifest["generator"] == "scripts/art/create_silk_foundry_loom.py"
assert manifest["unreal_asset"] == f"/Game/Generated/Environment/Props/{name}.{name}"
assert manifest["fbx"] == name + ".fbx"
assert "Original project-owned geometry" in manifest["license"]
assert "CC0 Poly Haven" in manifest["license"] and "SIL OFL" in manifest["license"]
assert manifest["source_parts"] >= 250
assert 15000 <= manifest["source_triangles"] < 50000
assert manifest["collision_boxes"] == 4
assert manifest["bounds_m"]["min"][2] == 0
assert 2.20 < manifest["bounds_m"]["max"][2] < 2.4
for filename, field in ((manifest["source_blend"], "blend_sha256"),
                        (manifest["fbx"], "fbx_sha256"),
                        (manifest["preview"], "preview_sha256")):
    path = out / filename
    assert path.stat().st_size > 1000, path
    assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest[field], path
assert hashlib.sha256(font.read_bytes()).hexdigest() == manifest["font_sha256"]
assert "SIL OPEN FONT LICENSE" in (font.parent / "OFL.txt").read_text()
palette_file = palette / "manifest.json"
assert hashlib.sha256(palette_file.read_bytes()).hexdigest() == manifest["palette_manifest_sha256"]
palette_manifest = json.loads(palette_file.read_text())
assert palette_manifest["asset_license"] == "CC0-1.0"
assert manifest["palette_asset_ids"] == ["wood_planks_dirt", "rusty_metal_02"]
records = {record["asset_id"]: record for record in palette_manifest["assets"]}
expected_images = set()
for asset_id in manifest["palette_asset_ids"]:
    record = records[asset_id]
    assert record["license"] == "CC0-1.0"
    assert {item["channel"].lower() for item in record["files"]} == {"diffuse", "nor_dx", "arm"}
    for item in record["files"]:
        path = palette / item["file"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
        expected_images.add(path.resolve())
linked_images = {Path(bpy.path.abspath(image.filepath)).resolve()
                 for image in bpy.data.images if image.source == "FILE"}
assert linked_images == expected_images, (linked_images, expected_images)
assert all(image.filepath.startswith("//../PolyHaven/")
           for image in bpy.data.images if image.source == "FILE")
assert any(data.filepath.startswith("//../../Fonts/")
           and Path(bpy.path.abspath(data.filepath)).resolve() == font.resolve()
           for data in bpy.data.fonts)
collection = bpy.data.collections.get("SilkFoundryLoom_Editable")
assert collection is not None
parts = [obj for obj in collection.objects if obj.type == "MESH"]
assert len(parts) == manifest["source_parts"]
assert sum(len(face.vertices) - 2 for obj in parts for face in obj.data.polygons) == manifest["source_triangles"]
assert len([obj for obj in parts if obj.name.startswith("Ivory_WarpThread_")]) == 65
assert any(obj.name == "Indigo_Silk_InProgress" for obj in parts)
assert any(obj.name == "Alien_LevyGlass" for obj in parts)
assert any(obj.name == "Silk_Production_Label" for obj in parts)
fbx = out / manifest["fbx"]
fbx_bytes = fbx.read_bytes()
assert fbx_bytes.startswith(b"Kaydara FBX Binary")
assert b"/Users/" not in fbx_bytes
before = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=str(fbx))
imported = [obj for obj in set(bpy.data.objects) - before if obj.type == "MESH"]
render = [obj for obj in imported if obj.name == name]
proxies = [obj for obj in imported if obj.name.startswith("UCX_" + name + "_")]
assert len(render) == 1 and len(proxies) == 4, [obj.name for obj in imported]
corners = [render[0].matrix_world @ Vector(corner) for corner in render[0].bound_box]
for axis in range(3):
    assert abs(min(point[axis] for point in corners) - manifest["bounds_m"]["min"][axis]) < .02
    assert abs(max(point[axis] for point in corners) - manifest["bounds_m"]["max"][axis]) < .02
slots = {slot.material.name.split(".", 1)[0] for slot in render[0].material_slots}
assert {"M_Env_Timber", "M_Env_Metal", "M_Loom_IndigoSilk",
        "M_Loom_ProductionCyan", "M_Loom_LevyRed"} <= slots, slots
assert not any(obj.name == name or obj.name.startswith("UCX_")
               for obj in collection.objects)
print("SILK_FOUNDRY_LOOM_FBX_ROUNDTRIP_PASS", manifest["source_parts"],
      manifest["source_triangles"], manifest["bounds_m"], sorted(slots), len(proxies))
validated = True
