"""Check the runtime SORA mon mesh keeps the pinned SVG's two paths exactly.

Run: blender -b --factory-startup --python scripts/art/validate_sora_kamon_mon.py
This validates the source FBX, not a cooked Unreal package or its readability.
"""

import atexit
import hashlib
import json
import os
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sora_kamon_validation import (PINNED_SVG_SHA256, assert_paths_embedded,
                                   expected_paths, reference_paths)


validated = False


def fail_exit():
    if not validated:
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(1)


atexit.register(fail_exit)
root = Path(__file__).resolve().parents[2]
out = root / "Content/SourceArt/UI/SoraKamonMon"
record = json.loads((out / "manifest.json").read_text())
fbx = out / record["fbx"]
assert record["schema_version"] == 1 and record["name"] == "SM_SoraKamon"
assert record["unreal_asset"] == "/Game/Generated/UI/SM_SoraKamon.SM_SoraKamon"
assert record["source_svg_sha256"] == PINNED_SVG_SHA256
assert hashlib.sha256((out / record["source_svg"]).read_bytes()).hexdigest() == PINNED_SVG_SHA256
assert hashlib.sha256(fbx.read_bytes()).hexdigest() == record["fbx_sha256"]
assert fbx.read_bytes().startswith(b"Kaydara FBX Binary")
diameter, thickness = record["diameter_m"], record["thickness_m"]
assert (diameter, thickness) == (1.0, .01)

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
source_paths = reference_paths(root)
# Every vertex of both paths lies on both faces of the mon.
faces = {
    "front": expected_paths(source_paths, (thickness / 2, 0, 0), diameter, "YZ"),
    "back": expected_paths(source_paths, (-thickness / 2, 0, 0), diameter, "YZ"),
}
before = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=str(fbx))
imported = [obj for obj in set(bpy.data.objects) - before if obj.type == "MESH"]
assert len(imported) == 1 and imported[0].name.startswith("SM_SoraKamon"), [obj.name for obj in imported]
mon = imported[0]
points = [mon.matrix_world @ vertex.co for vertex in mon.data.vertices]
assert_paths_embedded(points, faces)
assert len(points) == record["vertices"] and len(mon.data.polygons) == record["triangles"]
assert all(len(polygon.vertices) == 3 for polygon in mon.data.polygons)
assert [slot.name for slot in mon.material_slots] == record["material_slots"], [slot.name for slot in mon.material_slots]
# Flat on both faces, one disc across, and upright: the top bar's ends stand
# above the centre and the legs run to the bottom of the disc.
assert all(abs(abs(p.x) - thickness / 2) < 1e-5 for p in points)
assert abs(max(p.y for p in points) - min(p.y for p in points) - diameter) < 1e-3
assert abs(max(p.z for p in points) - min(p.z for p in points) - diameter) < 1e-3
bar_end = ((68.2 - 175.45) / 350.9 * diameter, (175.45 - 88.0) / 350.9 * diameter)
assert any(abs(p.y - bar_end[0]) < 1e-3 and abs(p.z - bar_end[1]) < 1e-3 for p in points), "The mon is not upright"
print("SORA_KAMON_MON_PASS", PINNED_SVG_SHA256, len(source_paths), len(points), len(mon.data.polygons))
validated = True
