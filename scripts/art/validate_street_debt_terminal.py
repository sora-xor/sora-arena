"""Independent Blender source/FBX check for the Lantern Ward debt terminal.

Run: blender -b Content/SourceArt/Environment/StreetDebtTerminal/Alien_StreetDebtTerminal.blend \
    --python scripts/art/validate_street_debt_terminal.py
This cannot establish Unreal import, game lighting, or frame rate.
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
    # Blender may return status zero for an uncaught --python exception.
    if not validated:
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(1)


atexit.register(fail_exit)
root = Path(__file__).resolve().parents[2]
out = root / "Content/SourceArt/Environment/StreetDebtTerminal"
manifest = json.loads((out / "manifest.json").read_text())
name = "SM_Alien_StreetDebtTerminal"
assert bpy.app.version[:2] == (5, 2)
assert Path(bpy.data.filepath).resolve() == (out / manifest["source_blend"]).resolve()
assert manifest["schema_version"] == 1 and manifest["name"] == name
assert manifest["generator"] == "scripts/art/create_street_debt_terminal.py"
assert manifest["source_parts"] == 31 and manifest["source_triangles"] < 5000
assert manifest["unreal_asset"] == f"/Game/Generated/Environment/Props/{name}.{name}"
assert "Original project-owned geometry" in manifest["license"]
assert "SIL OFL" in manifest["license"] and "CC0 Poly Haven" in manifest["license"]
for filename, field in ((manifest["source_blend"], "blend_sha256"),
                        (manifest["fbx"], "fbx_sha256"),
                        (manifest["preview"], "preview_sha256"),
                        (manifest["blockout_preview"], "blockout_sha256"),
                        (manifest["comparison_preview"], "comparison_sha256")):
    path = out / filename
    assert path.stat().st_size > 1000
    assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest[field]

font = root / "Content/SourceArt/Fonts/NotoSansCJKjp-Regular.otf"
assert hashlib.sha256(font.read_bytes()).hexdigest() == manifest["font_sha256"]
assert "SIL OPEN FONT LICENSE" in (font.parent / "OFL.txt").read_text()
palette = root / "Content/SourceArt/Environment/PolyHaven"
palette_file = palette / "manifest.json"
assert hashlib.sha256(palette_file.read_bytes()).hexdigest() == manifest["palette_manifest_sha256"]
palette_manifest = json.loads(palette_file.read_text())
assert palette_manifest["asset_license"] == "CC0-1.0"
assert manifest["palette_asset_ids"] == ["wood_planks_dirt", "rusty_metal_02", "stone_floor"]
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
for font_data in bpy.data.fonts:
    if "NotoSansCJKjp-Regular" in font_data.name:
        assert Path(bpy.path.abspath(font_data.filepath)).resolve() == font.resolve()

collection = bpy.data.collections.get("StreetDebtTerminal_Editable")
assert collection is not None
parts = [obj for obj in collection.objects if obj.type == "MESH"]
assert len(parts) == manifest["source_parts"]
assert sum(len(poly.vertices)-2 for obj in parts for poly in obj.data.polygons) == manifest["source_triangles"]
assert any(obj.name == "Japanese_Levy_Mark" for obj in parts)

fbx = out / manifest["fbx"]
assert fbx.read_bytes().startswith(b"Kaydara FBX Binary")
assert b"/Users/" not in fbx.read_bytes()
before = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=str(fbx))
imported = [obj for obj in set(bpy.data.objects)-before if obj.type == "MESH"]
render = [obj for obj in imported if obj.name == name]
proxies = [obj for obj in imported if obj.name == "UCX_" + name + "_00"]
assert len(render) == 1 and len(proxies) == 1, [obj.name for obj in imported]
corners = [render[0].matrix_world @ Vector(corner) for corner in render[0].bound_box]
for axis in range(3):
    assert abs(min(point[axis] for point in corners)-manifest["bounds_m"]["min"][axis]) < .02
    assert abs(max(point[axis] for point in corners)-manifest["bounds_m"]["max"][axis]) < .02
slots = {slot.material.name.split(".", 1)[0] for slot in render[0].material_slots
         if slot.material is not None}
assert {"M_Env_Timber", "M_Env_Metal", "M_Env_Stone",
        "M_StreetTerminal_ColdLienSeal", "M_StreetTerminal_DebtTally"} <= slots
assert sum(len(poly.vertices)-2 for poly in render[0].data.polygons) == manifest["source_triangles"]
print("STREET_DEBT_TERMINAL_VALIDATED", manifest["source_triangles"],
      manifest["bounds_m"], len(slots), "slots", len(proxies), "UCX",
      len(expected_images), "CC0 PBR maps, flat/PBR/comparison preview digests")
validated = True
