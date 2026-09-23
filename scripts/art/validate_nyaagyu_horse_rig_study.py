"""Check source rig, walk poses, tack anchors, hashes, and FBX round trip.

Run: blender -b Content/SourceArt/Horses/Nyaagyu/RigStudy/Nyaagyu_Horse_RigStudy.blend \
    --python scripts/art/validate_nyaagyu_horse_rig_study.py
"""

from __future__ import annotations

import atexit
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import bpy


passed = False


def exit_on_failure():
    if not passed:
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(1)


atexit.register(exit_on_failure)
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Horses/Nyaagyu/RigStudy"
manifest = json.loads((OUT / "manifest.json").read_text())
assert bpy.app.version[:2] == (5, 2)
assert manifest["schema_version"] == 1
assert manifest["name"] == "SK_Nyaagyu_Horse_RigStudy"
assert manifest["generator"] == "scripts/art/create_nyaagyu_horse_rig_study.py"
assert manifest["validator"] == "scripts/art/validate_nyaagyu_horse_rig_study.py"
assert Path(bpy.data.filepath).resolve() == (OUT / manifest["source_blend"]).resolve()
assert manifest["base_commit"] == "d319aadae6ecf2bad1967f9462b6660f2136612a"
pointer = subprocess.check_output(["git", "show", f'{manifest["base_commit"]}:{manifest["base_source_path"]}'], cwd=ROOT)
base = subprocess.check_output(["git", "lfs", "smudge"], input=pointer, cwd=ROOT)
assert hashlib.sha256(base).hexdigest() == manifest["base_source_sha256"]
base_manifest = json.loads(subprocess.check_output(
    ["git", "show", f'{manifest["base_commit"]}:Content/SourceArt/Horses/Nyaagyu/manifest.json'],
    cwd=ROOT))
assert base_manifest["blend_sha256"] == manifest["base_source_sha256"]
for field, hash_field in (("source_blend", "source_blend_sha256"), ("fbx", "fbx_sha256")):
    path = OUT / manifest[field]
    assert path.stat().st_size > 1000
    assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest[hash_field]
assert (OUT / manifest["fbx"]).read_bytes().startswith(b"Kaydara FBX Binary")
for record in manifest["review_frames"]:
    path = OUT / record["file"]
    assert path.stat().st_size > 100_000
    assert hashlib.sha256(path.read_bytes()).hexdigest() == record["sha256"]
assert len({r["sha256"] for r in manifest["review_frames"]}) == 4
logo = ROOT / "Content/SourceArt/UI/sora_logo_NOtext2.svg"
assert hashlib.sha256(logo.read_bytes()).hexdigest() == manifest["sora_logo_sha256"]
assert base_manifest["insignia_sha256"] == manifest["sora_logo_sha256"]

arm = bpy.data.objects[manifest["name"]]
assert arm.type == "ARMATURE"
assert len(arm.data.bones) == len(manifest["bone_names"]) == 28
assert sorted(b.name for b in arm.data.bones) == manifest["bone_names"]
assert arm.animation_data and arm.animation_data.action
assert arm.animation_data.action.name == manifest["walk"]["name"]
assert manifest["walk"]["footfall_order"] == ["hind_L", "fore_L", "hind_R", "fore_R"]
assert manifest["walk"]["contact_frames"] == {"hind_L": 1, "fore_L": 10, "hind_R": 19, "fore_R": 28}
assert manifest["walk"]["in_place"] is True
assert (bpy.context.scene.frame_start, bpy.context.scene.frame_end, bpy.context.scene.render.fps) == (1, 37, 30)
core = bpy.data.objects["Horse_anatomical_core"]
assert core.parent == arm
assert len(core.data.vertices) == manifest["skinned_core_vertices"] > 30000
assert len(core.vertex_groups) >= 23
assert any(m.type == "ARMATURE" and m.object == arm for m in core.modifiers)
assert all(vertex.groups for vertex in core.data.vertices)

source = bpy.data.collections["NyaagyuHorse_RigStudy_Source"]
meshes = [o for o in source.objects if o.type == "MESH"]
assert len(meshes) == manifest["source_parts"] == 252
kamon = [o for o in meshes if o.name.startswith("SORA_kamon_exact_svg_")]
assert len(kamon) == 8
assert all(o.get("source_svg_sha256") == manifest["sora_logo_sha256"] for o in kamon)
for side in (-1, 1):
    letter = "L" if side < 0 else "R"
    for name in (f"Abumi_{side}_broad_iron_footplate", f"Abumi_{side}_hato_mune_iron_toe_shell",
                 f"Abumi_{side}_strap", f"Tazuna_rein_{side}"):
        obj = bpy.data.objects[name]
        assert obj.parent == arm and obj.parent_type == "BONE"
        assert obj.parent_bone == (f"abumi_{letter}" if name.startswith("Abumi_") else f"tazuna_{letter}")
    for family in ("fore", "hind"):
        obj = bpy.data.objects[f"Horse_{family}_{side}_hoof"]
        assert obj.parent_bone == f"{family}_{letter}_hoof"
for name, target in manifest["anchor_bones"].items():
    obj = bpy.data.objects[name]
    assert obj.type == "EMPTY" and obj.parent == arm and obj.parent_bone == target
assert {bpy.data.objects[n].parent_bone for n in ("Saddle_RiderSeat", "Abumi_LeftFoot", "Abumi_RightFoot", "Tazuna_LeftGrip", "Tazuna_RightGrip")} == {
    "saddle_mount", "abumi_L", "abumi_R", "tazuna_L", "tazuna_R"
}

scene = bpy.context.scene
angles = {}
hoof_positions = {}
for frame in (1, 10, 19, 28, 37):
    scene.frame_set(frame)
    angles[frame] = tuple(tuple(round(value, 5) for value in arm.pose.bones[f"{family}_upper"].rotation_quaternion)
                          for family in manifest["walk"]["footfall_order"])
    hoof_positions[frame] = tuple(round(sum((obj.matrix_world @ v.co).x for v in obj.data.vertices) / len(obj.data.vertices), 5)
                                  for family, side in (("hind", -1), ("fore", -1), ("hind", 1), ("fore", 1))
                                  for obj in (bpy.data.objects[f"Horse_{family}_{side}_hoof"],))
assert len({angles[f] for f in (1, 10, 19, 28)}) == 4
assert len({hoof_positions[f] for f in (1, 10, 19, 28)}) == 4
assert all(abs(angles[1][i][j] - angles[37][i][j]) < .00001 for i in range(4) for j in range(4))
assert all(abs(hoof_positions[1][i] - hoof_positions[37][i]) < .00001 for i in range(4))
assert all(max(hoof_positions[f][i] for f in (1, 10, 19, 28)) -
           min(hoof_positions[f][i] for f in (1, 10, 19, 28)) > .045
           for i in range(4)), hoof_positions
scene.frame_set(1)

before = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=str(OUT / manifest["fbx"]))
imported = set(bpy.data.objects) - before
fbx_arms = [o for o in imported if o.type == "ARMATURE"]
assert len(fbx_arms) == 1
fbx_arm = fbx_arms[0]
assert len(fbx_arm.data.bones) == 28
fbx_meshes = [o for o in imported if o.type == "MESH"]
assert len(fbx_meshes) >= 200
fbx_core = next(o for o in fbx_meshes if o.name.startswith("Horse_anatomical_core"))
assert len(fbx_core.data.vertices) > 30000
assert any(m.type == "ARMATURE" for m in fbx_core.modifiers)
assert fbx_arm.animation_data and fbx_arm.animation_data.action
fbx_rotations = []
for frame in (1, 10, 19, 28):
    scene.frame_set(frame)
    fbx_rotations.append(tuple(round(value, 5) for value in fbx_arm.pose.bones["hind_L_upper"].rotation_quaternion))
assert len(set(fbx_rotations)) >= 3, fbx_rotations
print("NYAAGYU_HORSE_RIG_ROUNDTRIP_PASS", len(fbx_arm.data.bones), len(fbx_meshes),
      angles, [p.name for p in (OUT / r["file"] for r in manifest["review_frames"])])
passed = True
