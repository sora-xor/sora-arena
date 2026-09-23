"""Independently round-trip the rigged Nyaakoto FBX and exact SORA crest.

Run with Blender 5.2.2: blender -b --factory-startup --python
scripts/art/validate_nyaakoto_runtime_skin.py
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
from sora_kamon_validation import (PINNED_SVG_SHA256, assert_paths_embedded,
                                   expected_paths, reference_paths)

passed = False


def fail_on_exception():
    if not passed:
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(1)


atexit.register(fail_on_exception)
root = Path(__file__).resolve().parents[2]
out = root / "Content/SourceArt"
hero = out / "Characters/Hero"
record = json.loads((hero / "runtime_skin_manifest.json").read_text())
source = json.loads((hero / "manifest.json").read_text())
assert record["schema_version"] == 1
assert record["generator"] == "scripts/art/rig_nyaakoto_runtime.py"
assert record["source_blend_sha256"] == source["blend_sha256"]
assert record["sora_kamon_svg_sha256"] == source["insignia_sha256"] == PINNED_SVG_SHA256
assert record["sora_kamon_placements"] == source["sora_kamon_placements"]
assert record["source_parts"] == source["source_parts"]
for base, relative_root in (("source_blend", root),
                            ("runtime_blend", hero),
                            ("runtime_preview", hero),
                            ("skeletal_fbx", out),
                            ("walk_fbx", out)):
    file = relative_root / record[base]
    assert file.is_file() and file.stat().st_size > 1000, file
    assert hashlib.sha256(file.read_bytes()).hexdigest() == record[base + "_sha256"], file

before = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=str(out / record["skeletal_fbx"]))
added = set(bpy.data.objects) - before
meshes = [o for o in added if o.type == "MESH"]
armatures = [o for o in added if o.type == "ARMATURE"]
assert len(meshes) == len(armatures) == 1
mesh, rig = meshes[0], armatures[0]
assert mesh.name == "SK_NyaagyuSamurai" and mesh.parent == rig
assert mesh.type == "MESH" and len(mesh.data.vertices) == record["source_vertices"]
assert len(rig.data.bones) == 20
assert set(record["skeleton_bones"]) == set(rig.data.bones.keys())
assert all(len(v.groups) == 1 for v in mesh.data.vertices)
assert sum(1 for v in mesh.data.vertices if mesh.vertex_groups[v.groups[0].group].name == "head") == record["head_weighted_vertices"]
materials = {m.name for m in mesh.data.materials}
pbr = json.loads((hero / "PBR/manifest.json").read_text())
assert materials == set(pbr["material_slots"])
uv = mesh.data.uv_layers.active
assert uv is not None
grey_slot = next(i for i, material in enumerate(mesh.data.materials)
                 if material.name == "M_Hero_GreyTabbyFur")
grey_loops = [loop_index for polygon in mesh.data.polygons
              if polygon.material_index == grey_slot for loop_index in polygon.loop_indices]
grey_uv = [uv.data[index].uv for index in grey_loops]
assert grey_uv and max(point.x for point in grey_uv) - min(point.x for point in grey_uv) > .2
assert max(point.y for point in grey_uv) - min(point.y for point in grey_uv) > .2
for material in ("M_Hero_GreyTabbyFur", "M_Hero_WhiteFur", "M_Hero_BlueEye",
                 "M_Hero_OxbloodUrushi", "M_Hero_IndigoSilk", "M_Hero_ScarletSash",
                 "M_Hero_YumiLaminatedBamboo", "M_Hero_RedArrowFletch",
                 "M_Hero_SORAResistanceRed"):
    assert material in materials, material
corners = [mesh.matrix_world @ Vector(c) for c in mesh.bound_box]
assert -.02 < min(p.z for p in corners) < .02
assert 2.15 < max(p.z for p in corners) < 2.25

# The rigged FBX must retain the user's two exact paths at four placements.
paths = reference_paths(root)
marks = {
    "chest": expected_paths(paths, (.235, -.108, 1.207), .069, "YZ"),
    "waist": expected_paths(paths, (.245, 0, .858), .068, "YZ"),
    "sode_-1": expected_paths(paths, (.126, -.345, 1.325), .052, "YZ"),
    "sode_1": expected_paths(paths, (.126, .345, 1.325), .052, "YZ"),
}
assert_paths_embedded((mesh.matrix_world @ v.co for v in mesh.data.vertices), marks)
assert any(action.frame_range[1] - action.frame_range[0] >= 90 for action in bpy.data.actions)

before = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=str(out / record["walk_fbx"]))
walk_added = set(bpy.data.objects) - before
walk_rigs = [o for o in walk_added if o.type == "ARMATURE"]
walk_meshes = [o for o in walk_added if o.type == "MESH"]
assert len(walk_rigs) == len(walk_meshes) == 1
assert set(walk_rigs[0].data.bones.keys()) == set(rig.data.bones.keys())
assert any(30 <= action.frame_range[1] - action.frame_range[0] <= 36 for action in bpy.data.actions)
assert walk_rigs[0].animation_data and walk_rigs[0].animation_data.action
bpy.context.scene.frame_set(2)
first_pose = walk_rigs[0].pose.bones["thigh_L"].matrix.copy()
bpy.context.scene.frame_set(10)
second_pose = walk_rigs[0].pose.bones["thigh_L"].matrix.copy()
assert max(abs(first_pose[row][col] - second_pose[row][col])
           for row in range(4) for col in range(4)) > .1
print("NYAAKOTO_RUNTIME_SKIN_PASS", len(mesh.data.vertices), len(materials), len(rig.data.bones))
passed = True
