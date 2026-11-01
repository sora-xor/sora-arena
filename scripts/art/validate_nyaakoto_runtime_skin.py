"""Independently round-trip the rigged Nyaakoto FBX and exact SORA crest.

Run with Blender 5.2.2: blender -b --factory-startup --python
scripts/art/validate_nyaakoto_runtime_skin.py

The third-person grip contract, from the exported files themselves:
- the four SORA kamon, every SVG path vertex at the placement the hero source
  records (study A moved the chest and sode kamon rigidly);
- the empty-fist morph targets: PawEmpty_R and PawEmpty_L at 0, each moving
  exactly its paw's vertices, to where nyaakoto_tp_paws.empty_points puts them
  from the exported bind (the paw's frame from the record, at full precision);
- the Guard FBX round-trips: its own hand poses re-derive hand_r_grip and
  hand_l_grip at every frame, within 1 cm and 2 deg of the two-paw stance's
  targets; the StrikeMakko FBX likewise, against its keyed stance;
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
import nyaakoto_tp_paws as TPP  # noqa: E402
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
                            ("guard_fbx", out),
                            ("strike_fbx", out)):
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
# Each placement as the hero source records it: study A moved the chest and sode kamon rigidly (proportions).
assert set(source["sora_kamon_marks"]) == {"chest", "waist", "sode_-1", "sode_1"}
marks = {placement: expected_paths(paths, m["center"], m["diameter"], m["plane"])
         for placement, m in source["sora_kamon_marks"].items()}
assert_paths_embedded((mesh.matrix_world @ v.co for v in mesh.data.vertices), marks)

# The empty fists: two morph targets, 0 at bind, each moving exactly its own paw by the rule.
tp = record["third_person"]
keys = mesh.data.shape_keys
assert keys is not None and [kb.name for kb in keys.key_blocks] == ["Basis", "PawEmpty_R", "PawEmpty_L"]
assert all(kb.value == 0.0 for kb in keys.key_blocks[1:]), [kb.value for kb in keys.key_blocks]
mw = np.array([list(r) for r in mesh.matrix_world])


def key_world(block):
    co = np.empty(len(block.data) * 3, np.float32)
    block.data.foreach_get("co", co)
    return co.reshape(-1, 3).astype(np.float64) @ mw[:3, :3].T + mw[:3, 3]


bind = key_world(keys.key_blocks["Basis"])
group = np.array([mesh.vertex_groups[v.groups[0].group].name for v in mesh.data.vertices])
morph_rows = {}
for side in ("R", "L"):
    paw = tp["paws"]["by_side"][side]
    f = paw["frame"]
    skel = TPP.skeleton({k: (np.array(v) if isinstance(v, list) else v) for k, v in f.items()}, paw["palm_radii_m"])
    hand = group == f"hand_{side}"
    assert int(hand.sum()) == paw["vertices"], (side, int(hand.sum()), paw["vertices"])
    got = key_world(keys.key_blocks[f"PawEmpty_{side}"])
    rule_error = float(np.abs(got[hand] - TPP.empty_points(bind[hand], skel)).max())
    others = float(np.abs(got[~hand] - bind[~hand]).max())
    moved = float(np.linalg.norm(got[hand] - bind[hand], axis=1).max())
    assert rule_error < 1e-5 and others == 0.0 and moved > 0.02, (side, rule_error, others, moved)
    morph_rows[side] = {"rule_error_mm": round(rule_error * 1000.0, 5), "max_move_cm": round(moved * 100.0, 3)}
print("NYAAKOTO_EMPTY_PAW_MORPHS", morph_rows)
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
# --- The Guard and StrikeMakko FBX round trips, and the record's own gates -------------------------------------------
assert tp["clearance"]["calibration"]["ok"] is True
assert all(ok for row in tp["clearance"]["passed"].values() for ok in row.values()), tp["clearance"]["passed"]
assert set(tp["sockets"]) == {"hand_r_grip", "hand_l_grip", "gear_saya_l"}


def round_trip(fbx, targets_at):
    """Import an animation FBX and re-derive both grip sockets from its own hand poses at every frame; the worst
    distance (cm) and angle (deg) from targets_at(frame) per side, frame numbered from 1 as the rig keyed it. Blender's
    FBX import starts the action one frame later (frame_range (2, 26) for the strike's 1-25; s105's first run)."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(out / fbx))
    rigs = [o for o in set(bpy.data.objects) - before if o.type == "ARMATURE"]
    assert len(rigs) == 1 and set(rigs[0].data.bones.keys()) == set(rig.data.bones.keys())
    r = rigs[0]
    assert r.animation_data and r.animation_data.action
    start, end = (int(round(v)) for v in r.animation_data.action.frame_range)
    worst = {"R": [0.0, 0.0], "L": [0.0, 0.0]}
    for frame in range(start, end + 1):
        bpy.context.scene.frame_set(frame)
        for side, (want_pos, want_rot) in targets_at(frame - start + 1).items():
            pb = r.pose.bones[f"hand_{side}"]
            posed = r.matrix_world @ pb.matrix
            rest = r.matrix_world @ pb.bone.matrix_local
            rel = posed @ rest.inverted()                       # the hand's motion from its bind, in world
            channel = Vector(tp["arm_joints_blender_m"][side]["channel"])
            pos = np.array(rel @ channel)
            bind_axes = np.column_stack([TP.flip_y(tp["sockets"][f"hand_{side.lower()}_grip"][k]) for k in ("x_axis", "z_axis")])
            rot0 = TP.frame(bind_axes[:, 0], bind_axes[:, 1])
            r3 = rel.to_3x3()
            r3.normalize()
            rot = np.array([list(row) for row in r3]) @ rot0
            worst[side][0] = max(worst[side][0], float(np.linalg.norm(pos - want_pos)) * 100.0)
            worst[side][1] = max(worst[side][1], TP.angle_deg(rot, want_rot))
    return end - start + 1, worst


stance = tp["guard"]["stance"]
frames, worst = round_trip(record["guard_fbx"],
                           lambda frame: TP.socket_targets(stance, math.sin((frame - 1) / 96 * math.tau) * 0.004))
assert frames >= 91 and all(w[0] <= 1.0 and w[1] <= 2.0 for w in worst.values()), (frames, worst)
assert set(worst) == {"R", "L"}
print("NYAAKOTO_GUARD_ROUND_TRIP", frames, "frames; worst cm/deg", {s: [round(v, 3) for v in w] for s, w in worst.items()})
strike = tp["strike"]
keys_in_order = [stance] + [strike["keys"][k] | {"poles": strike["keys"][k].get("poles", {})} for k in ("raise", "hit", "follow")] + [stance]
frames, worst = round_trip(record["strike_fbx"], lambda frame: TP.socket_targets(
    TP.keyed_stance(keys_in_order, strike["times"], (frame - 1) / strike["frames"])))
assert frames == strike["frames"] + 1 and all(w[0] <= 1.0 and w[1] <= 2.0 for w in worst.values()), (frames, worst)
print("NYAAKOTO_STRIKE_ROUND_TRIP", frames, "frames; worst cm/deg", {s: [round(v, 3) for v in w] for s, w in worst.items()})
print("NYAAKOTO_RUNTIME_SKIN_PASS", len(mesh.data.vertices), len(materials), len(rig.data.bones))
passed = True
