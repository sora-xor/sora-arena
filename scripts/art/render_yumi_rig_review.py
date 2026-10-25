"""Review renders of the continuous yumi rig, from its exported FBX (a round trip).

Run (Blender 5.2.2):
  blender -b --factory-startup --python-exit-code 1 --python scripts/art/render_yumi_rig_review.py -- [--out DIR]

It imports Rig/SK_Weapon_18.fbx as exported, and checks that it comes back
with one armature of the rig record's bones (28), one skinned mesh and the 0-10 Draw take named
A_Weapon_18_Draw (imported without Blender's default one-frame offset).
Then it renders five states, Workbench (studio light, flat grey, outlines),
1600 x 1000. The states are braced, quarter, half, three-quarter and full
draw; the quarters lie between keys, so they show the exported take's own
playback. Six views each:
- the bow in profile, and the full profile with both tips;
- a close-up of the nigiri and the first bones above and below it, where
  skinning shear would show;
- the nocking point with its nakajikake, and each horn tip with the string
  leaving its groove, each followed to where the draw puts it.

Before rendering, it records the take as the FBX importer plays it
(W18_rig_playback_blender.npz): each bone's world matrix at the keys, the
quarter points and the midpoints, and every evaluated vertex at the braced
key, the ten midpoints and full draw. test_yumi_draw compares these with
yumi_draw's interpolation (Codex's review of 1b3cd68: a synthetic slerp test
is no proof of the exporter and importer's playback).

Review images only, not qualification. Default output: Saved/YumiRig/Renders/.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import yumi_draw as Y  # noqa: E402
FBX = ROOT / "Content/SourceArt/Weapons/Runtime/W18_Yumi/Rig/SK_Weapon_18.fbx"


PLAYBACK_QUARTERS = (0.0, 0.25, 0.5, 0.75)
# Braced, half and full, and the take between keys (Codex's review of the
# schema-2 attempt: the nocking point and both tips at each state, and the
# exported take's intermediate playback).
STATES = ((0.0, "Braced"), (2.5, "Quarter"), (5.0, "Half"), (7.5, "ThreeQuarter"), (10.0, "Full"))


def views_at(d):
    """The review's cameras at draw fraction d. Close views follow the nock and
    tips to where yumi_draw.string_frames puts them at that draw."""
    f = Y.string_frames(d)
    nock, tu, tl = (f[k][0] for k in ("String_Nock", "Tip_U", "Tip_L"))
    return {
        # Profile: looking along +Y (the bow's plane is XZ), the middle of the bow.
        "Profile": dict(loc=(-0.35, -3.6, 0.38), target=(-0.35, 0.0, 0.38), lens=50.0),
        # The full profile, both tips in frame (Codex's review of b55fe81: the Profile crops them).
        "FullProfile": dict(loc=(-0.25, -7.5, 0.37), target=(-0.25, 0.0, 0.37), lens=50.0),
        # The nigiri and the first bones: close, slightly from the archer's side.
        "GripClose": dict(loc=(-0.30, -0.55, 0.05), target=(-0.02, 0.0, 0.05), lens=50.0),
        # The nocking point and its nakajikake, where the string bends.
        "NockClose": dict(loc=(nock[0] + 0.06, -0.24, nock[2] + 0.05), target=(nock[0], 0.0, nock[2]), lens=50.0),
        # Each horn tip and the string leaving its groove.
        "TipUClose": dict(loc=(tu[0] - 0.06, -0.26, tu[2] - 0.03), target=(tu[0] + 0.005, 0.0, tu[2] - 0.035),
                          lens=50.0),
        "TipLClose": dict(loc=(tl[0] - 0.06, -0.26, tl[2] + 0.03), target=(tl[0] + 0.005, 0.0, tl[2] + 0.035),
                          lens=50.0),
    }


def out_dir():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return Path(argv[argv.index("--out") + 1]) if "--out" in argv else ROOT / "Saved/YumiRig/Renders"


def _fcurves(act):
    """Every F-curve of an action, layered (Blender 5) or not."""
    if hasattr(act, "layers"):
        return [fc for layer in act.layers for strip in layer.strips for bag in strip.channelbags for fc in bag.fcurves]
    return list(act.fcurves)


def playback(scene, arm, mesh, act, out):
    """The imported take at its keys and between them: bone world matrices
    at every key, quarter and midpoint; evaluated vertices (world metres) at
    the braced key, the midpoints and full draw."""
    import numpy as np
    times = [f + q for f in range(10) for q in PLAYBACK_QUARTERS] + [10.0]
    full = [t for t in times if t in (0.0, 10.0) or abs(t % 1.0 - 0.5) < 1e-9]
    names = [b.name for b in arm.data.bones]
    bones = np.zeros((len(times), len(names), 4, 4))
    verts = np.zeros((len(full), len(mesh.data.vertices), 3), np.float32)
    for i, t in enumerate(times):
        frame = int(math.floor(t))
        scene.frame_set(frame, subframe=t - frame)
        dg = bpy.context.evaluated_depsgraph_get()
        ea = arm.evaluated_get(dg)
        aw = np.array(ea.matrix_world)
        for b, n in enumerate(names):
            bones[i, b] = aw @ np.array(ea.pose.bones[n].matrix)
        if t in full:
            ev = mesh.evaluated_get(dg)
            me = ev.to_mesh()
            co = np.zeros(len(me.vertices) * 3)
            me.vertices.foreach_get("co", co)
            mw = np.array(ev.matrix_world)
            ev.to_mesh_clear()
            verts[full.index(t)] = co.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3]
    scene.frame_set(0)
    curves = _fcurves(act)
    interpolation = sorted({kp.interpolation for fc in curves for kp in fc.keyframe_points})
    key_frames = sorted({round(kp.co[0], 6) for fc in curves for kp in fc.keyframe_points})
    modes = sorted({pb.rotation_mode for pb in arm.pose.bones})
    path = out / "W18_rig_playback_blender.npz"
    np.savez_compressed(path, times=np.array(times), full_times=np.array(full), bones=bones,
                        bone_names=np.array(names), verts=verts, interpolation=np.array(interpolation),
                        key_frames=np.array(key_frames), rotation_modes=np.array(modes),
                        blender=np.array(bpy.app.version_string))
    report = {"file": path.name, "times": len(times), "vertex_frames": len(full), "vertices": len(mesh.data.vertices),
              "interpolation": interpolation, "key_frames": key_frames, "rotation_modes": modes,
              "fcurves": len(curves)}
    print("YUMI_RIG_REVIEW_PLAYBACK", json.dumps(report), flush=True)
    return report


def main():
    out = out_dir()
    out.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(FBX), axis_forward="-Y", axis_up="Z", global_scale=1.0,
                             use_custom_normals=True, use_image_search=False, automatic_bone_orientation=False,
                             anim_offset=0.0)
    arms = [o for o in bpy.context.scene.objects if o.type == "ARMATURE"]
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    if len(arms) != 1 or len(meshes) != 1:
        raise SystemExit(f"review: expected one armature and one mesh, got {len(arms)} and {len(meshes)}")
    arm, mesh = arms[0], meshes[0]
    act = arm.animation_data.action if arm.animation_data else None
    rng = tuple(int(f) for f in act.frame_range) if act else None
    report = {"bones": len(arm.data.bones), "mesh": mesh.name, "vertices": len(mesh.data.vertices),
              "action": act.name if act else None, "frame_range": rng,
              "skinned": any(m.type == "ARMATURE" for m in mesh.modifiers)}
    print("YUMI_RIG_REVIEW_IMPORT", json.dumps(report), flush=True)
    want_bones = len(json.loads((FBX.parent / "rig_record.json").read_text())["bones"])
    if (report["bones"] != want_bones or rng != (0, 10) or not report["skinned"]
            or not (act and act.name.endswith("A_Weapon_18_Draw"))):
        raise SystemExit(f"review: the round trip lost the rig: {report}")
    scene = bpy.context.scene
    playback(scene, arm, mesh, act, out)
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "SINGLE"
    scene.display.shading.single_color = (0.62, 0.62, 0.62)
    scene.display.shading.show_object_outline = True
    scene.render.resolution_x, scene.render.resolution_y = 1600, 1000
    world = bpy.data.worlds.new("Review")
    scene.world = world
    cam_data = bpy.data.cameras.new("ReviewCam")
    cam = bpy.data.objects.new("ReviewCam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    files = []
    for frame, label in STATES:
        scene.frame_set(int(frame), subframe=frame - int(frame))
        for vname, v in views_at(frame / 10.0).items():
            cam.location = Vector(v["loc"])
            d = Vector(v["target"]) - cam.location
            cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
            cam_data.lens = v["lens"]
            path = out / f"SK_Weapon_18_{label}_{vname}.png"
            scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            files.append(str(path))
            print("YUMI_RIG_REVIEW_RENDER", path.name, flush=True)
    print("YUMI_RIG_REVIEW_READY", len(files), "renders", flush=True)


if __name__ == "__main__":
    main()
