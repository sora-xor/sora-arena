"""Validate Estate wall source, licenses, envelope, and FBX round-trip.

Run: blender -b Content/SourceArt/Environment/NyaagyuEstateWall/Nyaagyu_EstateWall.blend \
  --python scripts/art/validate_nyaagyu_estate_wall.py
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
OUT = ROOT / "Content/SourceArt/Environment/NyaagyuEstateWall"
record = json.loads((OUT / "manifest.json").read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert bpy.app.version[:2] == (5, 2)
assert record["schema_version"] == 1
assert record["name"] == "SM_Nyaagyu_EstateWall_4m"
assert record["generator"] == "scripts/art/create_nyaagyu_estate_wall.py"
assert record["generator_sha256"] == sha(ROOT / record["generator"])
assert record["unreal_asset"] == "/Game/Generated/Environment/Props/SM_Nyaagyu_EstateWall_4m.SM_Nyaagyu_EstateWall_4m"
assert record["module_length_m"] == 4.0
assert record["collision_envelope_m"] == [1.0,4.0,5.4]
assert record["collision"].startswith("Visual-only")
assert record["nanite_windows"] is True
assert record["mac_conventional_fallback"] == {
    "source_fbx": "SM_Nyaagyu_EstateWall_4m.fbx",
    "fallback_percent_triangles": 1.0,
    "fallback_target": "PercentTriangles",
    "generate_fallback": "Enabled",
    "render_config": "Config/Mac/MacEngine.ini",
}
mac_config = (ROOT / record["mac_conventional_fallback"]["render_config"]).read_text()
assert "r.Nanite=0" in mac_config and "r.Nanite.ProxyRenderMode=0" in mac_config
world = (ROOT / "Source/SoraArena/Private/SoraWorldBuilder.cpp").read_text()
assert "FVector(100,5200,540)" in world and "FVector(6400,100,540)" in world
assert Path(bpy.data.filepath).resolve() == (OUT / record["source_blend"]).resolve()
for filename, key in ((record["source_blend"], "blend_sha256"),
                      (record["fbx"], "fbx_sha256"),
                      (record["review_before"], "review_before_sha256"),
                      (record["review_after"], "review_after_sha256")):
    path = OUT / filename
    assert path.stat().st_size > 1000
    assert sha(path) == record[key], path

assert set(record["dependencies"]) == {"Stone","Plaster","Timber","Kawara"}
rock = json.loads((OUT / "ScanRock01/manifest.json").read_text())
assert record["scan_manifest_sha256"] == sha(OUT / "ScanRock01/manifest.json")
assert rock["asset_id"] == "rock_01" and rock["license"] == "CC0-1.0"
assert rock["authors"] == {"Rob Tuytel": "All"}
assert {part["channel"] for part in rock["files"]} == {"Diffuse","nor_dx","arm"}
for part in rock["files"]:
    scan = OUT / "ScanRock01" / part["file"]
    assert sha(scan) == part["sha256"] and scan.stat().st_size == part["bytes"]
for surface, dependency in record["dependencies"].items():
    assert dependency["license"] == "CC0-1.0"
    assert dependency["source_url"].startswith("https://polyhaven.com/a/")
    assert dependency["authors"] and dependency["license_url"] == "https://polyhaven.com/license"
    assert set(dependency["files"]) == {"Albedo","NormalDX","ORM"}
    for file in dependency["files"].values():
        path = ROOT / file["repo_path"]
        assert (path.resolve().is_relative_to((ROOT / "Content/SourceArt/Environment/PolyHaven").resolve())
                or path.resolve().is_relative_to((OUT / "ScanRock01").resolve()))
        assert sha(path) == file["sha256"]
        assert file["upstream_url"].startswith("https://dl.polyhaven.org/")

expected_slots = {
    "M_Wall_CharredTimber", "M_Wall_EarthenScar", "M_Wall_Kawara",
    "M_Wall_LimePlaster", "M_Wall_StoneDark", "M_Wall_StoneFoundation",
}
assert set(record["material_slots"]) == expected_slots
assert set(record["slot_definitions"]) == expected_slots
for slot, definition in record["slot_definitions"].items():
    assert definition["source"] in record["dependencies"]
    assert len(definition["tint"]) == 3
    material = bpy.data.materials[slot]
    images = [node.image for node in material.node_tree.nodes if node.type == "TEX_IMAGE"]
    assert len(images) == 3 and all(image.packed_file for image in images)

collection = bpy.data.collections["NyaagyuEstateWall_Editable"]
parts = [obj for obj in collection.objects if obj.type == "MESH"]
assert len(parts) == record["source_parts"] and len(parts) > 120
assert all(obj.get("provenance") == "Original project-authored Estate wall geometry" for obj in parts)
assert all(obj.data.uv_layers for obj in parts)
assert sum(len(poly.vertices)-2 for obj in parts for poly in obj.data.polygons) == record["source_triangles"]
names = {obj.name for obj in parts}
assert sum(name.startswith("Stone_") for name in names) >= 50
assert sum(name.startswith("Kawara_") for name in names) == 40
assert sum(name.startswith("Ridge_cap_") for name in names) == 20
assert sum(name.startswith("Plaster_chip_") for name in names) == 24
assert "Stone_core" in names and "Tile_subroof" in names
points = [obj.matrix_world @ vert.co for obj in parts for vert in obj.data.vertices]
bounds = {"min": [round(min(point[i] for point in points), 4) for i in range(3)],
          "max": [round(max(point[i] for point in points), 4) for i in range(3)]}
assert bounds == record["bounds_m"]
assert bounds["min"][0] >= -.5 and bounds["max"][0] <= .5
assert bounds["min"][1] >= -2 and bounds["max"][1] <= 2
assert bounds["min"][2] >= -2.7 and bounds["max"][2] <= 2.7
proxy = bpy.data.collections["Blender_Review_Only"].objects["Review_original_collision_wall"]
assert all(abs(proxy.dimensions[i] - record["collision_envelope_m"][i]) < .001 for i in range(3))
assert proxy.hide_render

fbx = OUT / record["fbx"]
assert fbx.read_bytes().startswith(b"Kaydara FBX Binary")
assert b"/Users/" not in fbx.read_bytes()
before = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=str(fbx))
imported = [obj for obj in set(bpy.data.objects)-before if obj.type == "MESH"]
assert len(imported) == 1
mesh = imported[0]
assert mesh.data.uv_layers
slots = sorted(slot.material.name.split(".",1)[0] for slot in mesh.material_slots)
assert slots == record["material_slots"]
fbx_corners = [mesh.matrix_world @ Vector(corner) for corner in mesh.bound_box]
for axis in range(3):
    assert abs(min(p[axis] for p in fbx_corners) - bounds["min"][axis]) < .02
    assert abs(max(p[axis] for p in fbx_corners) - bounds["max"][axis]) < .02
print("NYAAGYU_ESTATE_WALL_ROUNDTRIP_PASS", len(parts), record["source_triangles"], bounds, slots)
passed = True
