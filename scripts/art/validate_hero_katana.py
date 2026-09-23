"""Independently check the katana's source, UVs, PBR maps and drawn FBX.

Run: blender -b Content/SourceArt/Nyaagyu_HeroKatana.blend \
  --python scripts/art/validate_hero_katana.py
This verifies source transfer, not Unreal appearance or historical technique.
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


def failed():
    if not validated:
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(1)


atexit.register(failed)
root = Path(__file__).resolve().parents[2]
source = root / "Content/SourceArt"
manifest = json.loads((source / "manifest.json").read_text())
hero = manifest["hero_katana"]
pbr = source / "Weapons/HeroKatana/PBR"
surfaces = json.loads((pbr / "manifest.json").read_text())
assert bpy.app.version[:2] == (5, 2), bpy.app.version_string
assert Path(bpy.data.filepath).resolve() == (source / hero["source_blend"]).resolve()
assert hero["name"] == "SM_Nyaagyu_HeroKatana"
assert hero["generator"] == "scripts/art/create_hero_katana.py"
assert hero["runtime_export"].startswith("Drawn katana only")
fbx = source / hero["fbx"]
assert fbx.stat().st_size > 100_000
assert hashlib.sha256(fbx.read_bytes()).hexdigest() == hero["fbx_sha256"]
assert b"/Users/" not in fbx.read_bytes()
assert hero["saya_name"] == "SM_Nyaagyu_HeroSaya"
saya_fbx = source / hero["saya_fbx"]
assert saya_fbx.stat().st_size > 10_000
assert hashlib.sha256(saya_fbx.read_bytes()).hexdigest() == hero["saya_fbx_sha256"]
assert b"/Users/" not in saya_fbx.read_bytes()
assert surfaces["schema_version"] == 1
assert len(surfaces["material_slots"]) == 12
assert {entry["name"] for entry in surfaces["maps"]} == {
    "forged_steel", "patinated_metal", "woven_silk", "ray_skin", "urushi", "neutral"}
for group in surfaces["maps"]:
    assert {entry["channel"] for entry in group["maps"]} == {"Albedo", "NormalDX", "ORM"}
    for entry in group["maps"]:
        file = pbr / entry["file"]
        assert hashlib.sha256(file.read_bytes()).hexdigest() == entry["sha256"], file

collection = bpy.data.collections["Nyaagyu_HeroKatana_Asset"]
parts = [obj for obj in collection.objects if obj.type == "MESH"]
assert len(parts) >= 20
assert all(part.data.uv_layers.get("HeroKatanaProjection") for part in parts)
assert any(part.name.startswith("Saya_") for part in parts)
assert any(part.name.startswith("Sageo_") for part in parts)
assert any(part.name.startswith("Hamon_") for part in parts)
assert any(part.name.startswith("Tsuba_") for part in parts)
assert {slot.name for part in parts for slot in part.data.materials if slot} == set(surfaces["material_slots"])

before = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=str(fbx))
imported = [obj for obj in set(bpy.data.objects) - before if obj.type == "MESH"]
assert len(imported) == 1, [obj.name for obj in imported]
weapon = imported[0]
assert weapon.name == hero["name"]
assert len(weapon.data.uv_layers) >= 1
assert len(weapon.material_slots) == 9, [slot.material.name for slot in weapon.material_slots]
weapon_slots = {slot.material.name.split(".", 1)[0] for slot in weapon.material_slots}
assert weapon_slots <= set(surfaces["material_slots"])
assert sum(len(face.vertices)-2 for face in weapon.data.polygons) > 5000
corners = [weapon.matrix_world @ Vector(corner) for corner in weapon.bound_box]
minimum = [min(c[axis] for c in corners) for axis in range(3)]
maximum = [max(c[axis] for c in corners) for axis in range(3)]
assert -.40 < minimum[0] < -.30 and .80 < maximum[0] < .90, (minimum, maximum)
assert -.10 < minimum[1] < 0 and 0 < maximum[1] < .10, (minimum, maximum)
assert -.10 < minimum[2] < 0 and 0 < maximum[2] < .10, (minimum, maximum)
before = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=str(saya_fbx))
imported_saya = [obj for obj in set(bpy.data.objects) - before if obj.type == "MESH"]
assert len(imported_saya) == 1 and imported_saya[0].name == hero["saya_name"]
saya = imported_saya[0]
assert len(saya.data.uv_layers) >= 1
assert len(saya.material_slots) == 4
saya_slots = {slot.material.name.split(".", 1)[0] for slot in saya.material_slots}
assert weapon_slots | saya_slots == set(surfaces["material_slots"])
saya_corners = [saya.matrix_world @ Vector(corner) for corner in saya.bound_box]
assert max(abs(c[1]) for c in saya_corners) < .1
print("HERO_KATANA_ROUNDTRIP_PASS", len(parts),
      sum(len(face.vertices)-2 for face in weapon.data.polygons),
      len(weapon.material_slots), len(saya.material_slots), minimum, maximum)
validated = True
