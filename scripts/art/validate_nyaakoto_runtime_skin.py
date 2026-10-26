"""Independently round-trip the rigged Nyaakoto FBX and exact SORA crest.

Run with Blender 5.2.2: blender -b --factory-startup --python
scripts/art/validate_nyaakoto_runtime_skin.py

The third-person grip contract's slice A, from the exported files themselves:
- the Guard FBX round-trips: its own hand_R pose re-derives hand_r_grip at
  every frame, within 1 cm and 2 deg of the interim stance's targets;
- the record's clearance gates and calibration all passed.
"""

import atexit
import hashlib
import json
import os
import sys
from pathlib import Path

import math

import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sora_kamon_validation import (PINNED_SVG_SHA256, assert_paths_embedded,
                                   expected_paths, reference_paths)
import third_person_rig as TP

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
                            ("walk_fbx", out),
                            ("guard_fbx", out)):
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
assert uv is not None and len(mesh.data.uv_layers) == 1 and uv.name == "UVMap"
grey_slot = next(i for i, material in enumerate(mesh.data.materials)
                 if material.name == "M_Hero_GreyTabbyFur")
grey_loops = [loop_index for polygon in mesh.data.polygons
              if polygon.material_index == grey_slot for loop_index in polygon.loop_indices]
coat = mesh.data.color_attributes.get("CoatBlend")
assert coat is not None and coat.domain == "CORNER"
assert len(mesh.data.color_attributes) == 1 and len(coat.data) == len(mesh.data.loops)
grey_blend = [coat.data[index].color[0] for index in grey_loops]
assert min(grey_blend) < .01 and max(grey_blend) > .99
assert sum(.1 < value < .9 for value in grey_blend) > 1000
grey_uv = [uv.data[index].uv for index in grey_loops]
assert grey_uv and max(point.x for point in grey_uv) - min(point.x for point in grey_uv) > .2
assert max(point.y for point in grey_uv) - min(point.y for point in grey_uv) > .2
# The shared Unreal PBR material samples UV0.  The face/iris once exported
# authored UVs on channel 2 while channel 0 was a single dark corner texel.
for name in ("M_Hero_GreyTabbyFur", "M_Hero_WhiteFur", "M_Hero_BlueEye"):
    slot = next(i for i, material in enumerate(mesh.data.materials)
                if material.name == name)
    loops = [index for polygon in mesh.data.polygons
             if polygon.material_index == slot for index in polygon.loop_indices]
    points = [uv.data[index].uv for index in loops]
    assert points and sum(abs(point.x) > 1e-6 or abs(point.y) > 1e-6
                          for point in points) / len(points) > .95, name
    if name == "M_Hero_BlueEye":
        assert .01 <= min(point.x for point in points) < .05
        assert .95 < max(point.x for point in points) <= .99
        assert .01 <= min(point.y for point in points) < .05
        assert .95 < max(point.y for point in points) <= .99
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
# --- Slice A: the Guard FBX round trip, and the record's own gates ---------------------------------------------------
tp = record["third_person"]
assert tp["clearance"]["calibration"]["ok"] is True
assert all(ok for row in tp["clearance"]["passed"].values() for ok in row.values()), tp["clearance"]["passed"]
assert set(tp["sockets"]) == {"hand_r_grip", "hand_l_grip", "gear_saya_l"}
before = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=str(out / record["guard_fbx"]))
guard_added = set(bpy.data.objects) - before
guard_rigs = [o for o in guard_added if o.type == "ARMATURE"]
assert len(guard_rigs) == 1 and set(guard_rigs[0].data.bones.keys()) == set(rig.data.bones.keys())
grig = guard_rigs[0]
assert grig.animation_data and grig.animation_data.action
start, end = (int(round(v)) for v in grig.animation_data.action.frame_range)
assert end - start >= 90, (start, end)
stance = tp["guard"]["stance"]
worst = {"R": [0.0, 0.0], "L": [0.0, 0.0]}
for frame in range(start, end + 1):
    bpy.context.scene.frame_set(frame)
    targets = TP.socket_targets(stance, math.sin((frame - 1) / 96 * math.tau) * 0.004)
    for side, (want_pos, want_rot) in targets.items():
        pb = grig.pose.bones[f"hand_{side}"]
        posed = grig.matrix_world @ pb.matrix
        rest = grig.matrix_world @ pb.bone.matrix_local
        rel = posed @ rest.inverted()                       # the hand's motion from its bind, in world
        channel = Vector(tp["arm_joints_blender_m"][side]["channel"])
        pos = np.array(rel @ channel)
        bind = np.column_stack([TP.flip_y(tp["sockets"][f"hand_{side.lower()}_grip"][k]) for k in ("x_axis", "z_axis")])
        rot0 = TP.frame(bind[:, 0], bind[:, 1])
        r3 = rel.to_3x3()
        r3.normalize()
        rot = np.array([list(r) for r in r3]) @ rot0
        worst[side][0] = max(worst[side][0], float(np.linalg.norm(pos - want_pos)) * 100.0)
        worst[side][1] = max(worst[side][1], TP.angle_deg(rot, want_rot))
assert all(w[0] <= 1.0 and w[1] <= 2.0 for w in worst.values()), worst
print("NYAAKOTO_GUARD_ROUND_TRIP", end - start + 1, "frames; worst cm/deg", {s: [round(v, 3) for v in w] for s, w in worst.items()})
print("NYAAKOTO_RUNTIME_SKIN_PASS", len(mesh.data.vertices), len(materials), len(rig.data.bones))
passed = True
