"""Check original bokken source and independent Blender FBX round trip.

Run: blender -b Content/SourceArt/Weapons/Original/Nyaagyu_DojoBokken.blend \
    --python scripts/art/validate_dojo_bokken.py
This cannot verify UE 5.8.2 import or rendered appearance.
"""

import atexit
import hashlib
import json
import os
import sys
from pathlib import Path

import bpy
from mathutils import Vector


# Blender can return process status zero after --python raises an exception.
validated = False


def fail_exit():
    if not validated:
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(1)


atexit.register(fail_exit)
root = Path(__file__).resolve().parents[2]
out = root / "Content/SourceArt/Weapons/Original"
manifest = json.loads((out / "manifest.json").read_text())
assert bpy.app.version[:2] == (5, 2), bpy.app.version_string
assert Path(bpy.data.filepath).resolve() == (out / manifest["source_blend"]).resolve()
assert manifest["schema_version"] == 1
assert manifest["name"] == "SM_Nyaagyu_DojoBokken"
assert manifest["source_triangles"] == 8208
for filename, field in ((manifest["source_blend"], "blend_sha256"),
                        (manifest["fbx"], "fbx_sha256"),
                        (manifest["preview"], "preview_sha256")):
    assert hashlib.sha256((out / filename).read_bytes()).hexdigest() == manifest[field]

collection = bpy.data.collections.get("DojoBokken_Editable")
assert collection is not None
parts = [obj for obj in collection.objects if obj.type == "MESH"]
assert len(parts) == 16
assert sum(len(poly.vertices)-2 for obj in parts for poly in obj.data.polygons) == manifest["source_triangles"]
assert all(obj.get("authorship", "").startswith("Original") for obj in parts)
assert not any(obj.name.startswith("SM_Weapon_") for obj in parts)

before = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=str(out / manifest["fbx"]))
imported = [obj for obj in set(bpy.data.objects)-before if obj.type == "MESH"]
assert len(imported) == 1, [obj.name for obj in imported]
mesh = imported[0]
points = [mesh.matrix_world @ Vector(corner) for corner in mesh.bound_box]
extent = [max(point[axis] for point in points)-min(point[axis] for point in points)
          for axis in range(3)]
assert abs(max(extent)-manifest["length_m"]) < .012, extent
assert sum(len(poly.vertices)-2 for poly in mesh.data.polygons) == manifest["source_triangles"]
material_names = {slot.material.name.split(".")[0] for slot in mesh.material_slots
                  if slot.material is not None}
assert {"M_Bokken_SeasonedWhiteOak", "M_Bokken_HandOiledGrip",
        "M_Bokken_EndGrain", "M_Bokken_QuietWoodGrain"} <= material_names
assert b"/Users/" not in (out / manifest["fbx"]).read_bytes()
print("DOJO_BOKKEN_VALIDATED", extent, manifest["source_triangles"], sorted(material_names))
validated = True
