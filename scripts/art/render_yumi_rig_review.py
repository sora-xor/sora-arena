"""Review renders of the continuous yumi rig, from its exported FBX (a round trip).

Run (Blender 5.2.2):
  blender -b --factory-startup --python-exit-code 1 --python scripts/art/render_yumi_rig_review.py -- [--out DIR]

It imports Rig/SK_Weapon_18.fbx as exported, and checks that it comes back
with one armature of 24 bones, one skinned mesh and the 0-10 Draw take named
A_Weapon_18_Draw (imported without Blender's default one-frame offset).
Then it renders the braced, half and full draw in two views, Workbench
(studio light, flat grey, outlines), 1600 x 1000:
- the whole bow in profile;
- a close-up of the nigiri and the first bones above and below it, where
  skinning shear would show.

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
FBX = ROOT / "Content/SourceArt/Weapons/Runtime/W18_Yumi/Rig/SK_Weapon_18.fbx"


def out_dir():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return Path(argv[argv.index("--out") + 1]) if "--out" in argv else ROOT / "Saved/YumiRig/Renders"


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
    if (report["bones"] != 24 or rng != (0, 10) or not report["skinned"]
            or not (act and act.name.endswith("A_Weapon_18_Draw"))):
        raise SystemExit(f"review: the round trip lost the rig: {report}")
    scene = bpy.context.scene
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
    views = {
        # Profile: looking along +Y (the bow's plane is XZ), the middle of the bow.
        "Profile": dict(loc=(-0.35, -3.6, 0.38), target=(-0.35, 0.0, 0.38), lens=50.0),
        # The full profile, both tips in frame (Codex's review of b55fe81: the Profile crops them).
        "FullProfile": dict(loc=(-0.25, -7.5, 0.37), target=(-0.25, 0.0, 0.37), lens=50.0),
        # The nigiri and the first bones: close, slightly from the archer's side.
        "GripClose": dict(loc=(-0.30, -0.55, 0.05), target=(-0.02, 0.0, 0.05), lens=50.0),
    }
    files = []
    for frame, label in ((0, "Braced"), (5, "Half"), (10, "Full")):
        scene.frame_set(frame)
        for vname, v in views.items():
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
