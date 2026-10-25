"""Build the continuous skeletal yumi, SK_Weapon_18, from the committed static bow.

Run (Blender 5.2.2):
  blender -b --factory-startup --python-exit-code 1 --python scripts/art/create_runtime_weapon_yumi_rig.py

Production W18 is a skeletal yumi with one continuous draw (viewmodels.json,
the W18 package; FIRST_PERSON_VIEWMODEL_CONTRACT). It is not a rest/drawn
mesh swap. This builder leaves the static bow and its committed dimensions
and sockets exactly as they are, and adds:

1. **Import.** It imports the committed SM_Weapon_18.fbx (the braced bow, its
   UVs and material slots) with the weapon exporter's own axes. It checks the
   bounds and SOCKET_ empties against W18's build record.
2. **The armature.** Its object is named "Armature", so Unreal adds no root.
   There are 24 bones:
   - Grip, the root at Grip_L;
   - LimbU_01-12 and LimbL_01-08 at yumi_draw.bone_joints of the braced
     shape, each a child of Grip;
   - Tip_U and Tip_L at the string grooves;
   - String_Nock at Grip_R.
3. **Weights,** deterministic and the model of yumi_draw.skinning_error.
   - A string vertex lies within 4 mm of the braced string line, behind
     the stave and clear of the tip loops. It goes to String_Nock and the
     nearer tip, linear in height, so each segment stays straight.
   - Every other vertex goes to the two limb joints either side of its arc
     position along the stave centreline, linear in arc.
4. **The Draw action** (A_Weapon_18_Draw): frame i is draw fraction i/10, 11
   keys. The scene runs at 10 fps, so the take's time in seconds is the draw
   fraction (0-1 s). The scene is named after the action, so the FBX take
   (and Unreal's animation) is A_Weapon_18_Draw, not "Scene". Each limb bone is posed from yumi_draw.shape_at(d): its joint's head
   and its tangent's turn about Y. Tip_U and Tip_L move to the drawn grooves,
   and String_Nock to the drawn nock (-0.88, 0, 0.07).
5. **Checks, on the evaluated (deformed) mesh at every key:**
   - every stave vertex against its section carried rigidly by the solved
     shape;
   - the string vertices on their two straight segments;
   - the string's length unstretched;
   - the braced key identical to the static mesh.
   A failure raises before export.
6. **Outputs:**
   - Content/SourceArt/Weapons/Runtime/W18_Yumi/Rig/SK_Weapon_18.fbx: the
     armature, the skinned mesh and the action, baked;
   - rig_record.json: bones and binds, every key's pose, the weight summary,
     the sockets on their bones for Unreal's skeleton, the checks, and the
     input and output hashes;
   - W18_rig_check_geometry.npz: the emitted geometry for yumi_draw's
     first-person checks, so they measure real triangles, not envelopes:
     - the bow's rest vertices and triangles, and each vertex's two bones
       and weights;
     - every key's bone deform matrices;
     - the committed arrow (SM_Weapon_18_Ya) in its own frame, Nock at the
       origin and Tip on +X.

The arrow (SM_Weapon_18_Ya) stays its own static mesh, attached by the
runtime at String_Nock. Gameplay aim, ammo and damage are unchanged.
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import yumi_draw as Y  # noqa: E402

ROOT = HERE.parents[1]
GEN = "scripts/art/create_runtime_weapon_yumi_rig.py"
W18 = ROOT / "Content/SourceArt/Weapons/Runtime/W18_Yumi"
STATIC_FBX = W18 / "SM_Weapon_18.fbx"
RECORD = W18 / "build_record.json"
OUT = W18 / "Rig"
FRACTIONS = [i / 10 for i in range(11)]
STRING_RADIUS_M = 0.004         # the string, its nakajikake and their margin
TOL_STAVE_M = 0.0025            # deformed stave vertex against the solved section
TOL_STRING_M = 0.0002           # string vertex off its straight segment (beyond its radius)
ARROW_FBX = W18 / "SM_Weapon_18_Ya.fbx"


def sha256(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def rel(path: Path) -> str:
    return str(Path(path).resolve().relative_to(ROOT))


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_static(record):
    bpy.ops.import_scene.fbx(filepath=str(STATIC_FBX), axis_forward="-Y", axis_up="Z", global_scale=1.0,
                             use_custom_normals=True, use_image_search=False)
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    if len(meshes) != 1:
        raise RuntimeError(f"yumi rig: expected one mesh in {STATIC_FBX.name}, got {[o.name for o in meshes]}")
    obj = meshes[0]
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    # The committed bounds and sockets, as the round trip must keep them.
    xs = [v.co for v in obj.data.vertices]
    size = [max(c[i] for c in xs) - min(c[i] for c in xs) for i in range(3)]
    want = record["assets"]["SM_Weapon_18"]["bounds_m"]
    if max(abs(a - b) for a, b in zip(size, want)) > 2e-5:
        raise RuntimeError(f"yumi rig: imported bounds {size} differ from the record's {want}")
    sockets = {}
    for e in bpy.context.scene.objects:
        if e.type == "EMPTY" and e.name.startswith("SOCKET_"):
            sockets[e.name[len("SOCKET_"):]] = tuple(e.matrix_world.translation)
    for name, want in record["assets"]["SM_Weapon_18"]["sockets"].items():
        got = sockets.get(name)
        if got is None or max(abs(a - b) for a, b in zip(got, want)) > 2e-5:
            raise RuntimeError(f"yumi rig: socket {name} imported at {got}, record {want}")
    for e in [e for e in bpy.context.scene.objects if e.type == "EMPTY"]:
        bpy.data.objects.remove(e, do_unlink=True)
    obj.name = "SK_Weapon_18"
    obj.data.name = "SK_Weapon_18"
    return obj, sockets, size


def centreline(shape):
    """[(sig, x, z)] lower tip -> upper tip, as the generator integrates it."""
    return list(reversed(shape["low"]))[:-1] + shape["up"]


def project_arc(cl, x, z):
    """Arc position (sig) of the centreline point nearest (x, z)."""
    best, best_d = 0.0, 1e9
    for (s0, x0, z0), (s1, x1, z1) in zip(cl, cl[1:]):
        dx, dz = x1 - x0, z1 - z0
        L2 = dx * dx + dz * dz
        t = 0.0 if L2 < 1e-18 else max(0.0, min(1.0, ((x - x0) * dx + (z - z0) * dz) / L2))
        px, pz = x0 + dx * t, z0 + dz * t
        d = (x - px) ** 2 + (z - pz) ** 2
        if d < best_d:
            best_d, best = d, s0 + (s1 - s0) * t
    return best


def bone_names():
    up = [f"LimbU_{j:02d}" for j in range(1, Y.RIG_BONES["upper"] + 1)]
    low = [f"LimbL_{j:02d}" for j in range(1, Y.RIG_BONES["lower"] + 1)]
    return up, low


def joint_bone(limb, j):
    """The bone carrying joint j (0 is the grip, shared by both limbs)."""
    if j == 0:
        return "Grip"
    return (f"LimbU_{j:02d}" if limb == "upper" else f"LimbL_{j:02d}")


def build_armature(bind, sockets):
    arm_data = bpy.data.armatures.new("SK_Weapon_18_Skeleton")
    arm = bpy.data.objects.new("Armature", arm_data)
    bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm_data.edit_bones.new("Grip")
    eb.head, eb.tail = Vector((0.0, 0.0, 0.0)), Vector((0.0, 0.0, 0.05))
    grip = eb
    for limb in ("upper", "lower"):
        joints = bind[limb]
        for j in range(1, len(joints)):
            _s, x, z, phi = joints[j]
            b = arm_data.edit_bones.new(joint_bone(limb, j))
            b.head = Vector((x, 0.0, z))
            b.tail = b.head + Vector((math.cos(phi), 0.0, math.sin(phi))) * 0.04
            b.roll = 0.0
            b.parent = grip
            b.use_connect = False
    for name, loc, tail in (("Tip_U", sockets["String_Upper"], (0.02, 0.0, 0.0)),
                            ("Tip_L", sockets["String_Lower"], (0.02, 0.0, 0.0)),
                            ("String_Nock", sockets["Grip_R"], (-0.03, 0.0, 0.0))):
        b = arm_data.edit_bones.new(name)
        b.head = Vector(loc)
        b.tail = Vector(loc) + Vector(tail)
        b.parent = grip
        b.use_connect = False
    bpy.ops.object.mode_set(mode="OBJECT")
    return arm


def assign_weights(obj, arm, braced, bind, sockets):
    """Deterministic weights (see the module docstring). Returns per-vertex
    (kind, data) for the checks: ('string', s) or ('stave', sig)."""
    cl = centreline(braced)
    a, b = Vector(sockets["String_Lower"]), Vector(sockets["String_Upper"])
    nock = Vector(sockets["Grip_R"])
    s_n = (nock.z - a.z) / (b.z - a.z)
    groups = {}
    for name in ["Grip", "Tip_U", "Tip_L", "String_Nock", *sum(bone_names(), [])]:
        groups[name] = obj.vertex_groups.new(name=name)
    ab = b - a
    lims = {"upper": Y.L_UP, "lower": Y.L_LOW}
    info = []
    counts = {"string": 0, "stave": 0}
    for v in obj.data.vertices:
        p = v.co
        t = (p - a).dot(ab) / ab.length_squared
        off = (a + ab * t - p).length
        is_string = (off < STRING_RADIUS_M and p.x < -0.05 and a.z + 0.03 < p.z < b.z - 0.03)
        if is_string:
            s = (p.z - a.z) / (b.z - a.z)
            if s <= s_n:
                w = s / s_n
                groups["Tip_L"].add([v.index], 1.0 - w, "REPLACE")
                groups["String_Nock"].add([v.index], w, "REPLACE")
            else:
                w = (s - s_n) / (1.0 - s_n)
                groups["String_Nock"].add([v.index], 1.0 - w, "REPLACE")
                groups["Tip_U"].add([v.index], w, "REPLACE")
            info.append(("string", s))
            counts["string"] += 1
            continue
        sig = project_arc(cl, p.x, p.z)
        limb = "upper" if sig >= 0 else "lower"
        n = Y.RIG_BONES[limb]
        s = min(abs(sig), lims[limb])
        step = lims[limb] / n
        j = min(int(s / step), n - 1)
        f = (s - j * step) / step
        for k, w in ((j, 1.0 - f), (j + 1, f)):
            if w > 0:
                groups[joint_bone(limb, k)].add([v.index], w, "ADD")
        info.append(("stave", sig))
        counts["stave"] += 1
    mod = obj.modifiers.new("Armature", "ARMATURE")
    mod.object = arm
    obj.parent = arm
    obj.matrix_parent_inverse = Matrix.Identity(4)
    return info, counts


def pose_targets(d, bind):
    """Armature-space matrices of every posed bone at draw fraction d."""
    shape = Y.shape_at(d)
    pose = Y.bone_joints(shape)
    out = {}
    for limb in ("upper", "lower"):
        for j in range(1, len(pose[limb])):
            _s, bx, bz, bphi = bind[limb][j]
            _s, px, pz, pphi = pose[limb][j]
            dphi = math.atan2(math.sin(pphi - bphi), math.cos(pphi - bphi))
            # A turn of the tangent by +dphi in the (x, z) plane is a rotation of -dphi about +Y.
            rot = Matrix.Rotation(-dphi, 4, "Y")
            out[joint_bone(limb, j)] = (Vector((px, 0.0, pz)), rot)
    s = shape["sockets"]
    out["Tip_U"] = (Vector(s["String_Upper"]), Matrix.Identity(4))
    out["Tip_L"] = (Vector(s["String_Lower"]), Matrix.Identity(4))
    out["String_Nock"] = (Vector(s["Grip_R"]), Matrix.Identity(4))
    return shape, out


def key_draw(arm, bind):
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
    keys = []
    for frame, d in enumerate(FRACTIONS):
        shape, targets = pose_targets(d, bind)
        for name, (head, rot) in targets.items():
            pb = arm.pose.bones[name]
            bind_m = arm.data.bones[name].matrix_local
            pb.matrix = Matrix.Translation(head) @ rot @ bind_m.to_3x3().to_4x4()
        bpy.context.view_layer.update()
        for pb in arm.pose.bones:
            pb.keyframe_insert("location", frame=frame)
            pb.keyframe_insert("rotation_quaternion", frame=frame)
        keys.append({"frame": frame, "draw": d, "nock": list(shape["sockets"]["Grip_R"]),
                     "string_upper": list(shape["sockets"]["String_Upper"]),
                     "string_lower": list(shape["sockets"]["String_Lower"]),
                     "bones": {pb.name: {"location": [round(c, 7) for c in pb.location],
                                         "rotation_quaternion": [round(c, 7) for c in pb.rotation_quaternion]}
                               for pb in arm.pose.bones}})
    bpy.ops.object.mode_set(mode="OBJECT")
    act = arm.animation_data.action
    act.name = "A_Weapon_18_Draw"
    scene = bpy.context.scene
    scene.name = "A_Weapon_18_Draw"           # the FBX take's name
    scene.render.fps, scene.render.fps_base = 10, 1.0
    scene.frame_start, scene.frame_end = 0, len(FRACTIONS) - 1
    return keys


def check(obj, arm, info, braced, bind, rest_co):
    """The deformed mesh at every key against the solved shape."""
    scene = bpy.context.scene
    cl0 = centreline(braced)
    frames0 = Y._frames(braced["low"], braced["up"])
    results = []
    for frame, d in enumerate(FRACTIONS):
        scene.frame_set(frame)
        dg = bpy.context.evaluated_depsgraph_get()
        ev = obj.evaluated_get(dg)
        me = ev.to_mesh()
        co = [v.co.copy() for v in me.vertices]
        ev.to_mesh_clear()
        shape = Y.shape_at(d)
        frames_d = Y._frames(shape["low"], shape["up"])
        sig_list = [f[0] for f in frames0]
        stave_err, string_err = 0.0, 0.0
        s = shape["sockets"]
        a, b, n = Vector(s["String_Lower"]), Vector(s["String_Upper"]), Vector(s["Grip_R"])
        for i, (kind, val) in enumerate(info):
            p = co[i]
            if kind == "string":
                seg = (a, n) if p.z <= n.z else (n, b)
                u = seg[1] - seg[0]
                t = max(0.0, min(1.0, (p - seg[0]).dot(u) / u.length_squared))
                off = (seg[0] + u * t - p).length
                string_err = max(string_err, off - STRING_RADIUS_M if off > STRING_RADIUS_M else 0.0)
                continue
            # The vertex's section, carried rigidly by the solved shape at d.
            import bisect
            k = min(max(bisect.bisect_left(sig_list, val), 1), len(sig_list) - 1)
            f0a, f0b = frames0[k - 1], frames0[k]
            fda, fdb = frames_d[k - 1], frames_d[k]
            w = (val - f0a[0]) / max(f0b[0] - f0a[0], 1e-12)
            c0 = Vector(f0a[1]).lerp(Vector(f0b[1]), w)
            cd = Vector(fda[1]).lerp(Vector(fdb[1]), w)
            t0 = Vector(f0a[2]).lerp(Vector(f0b[2]), w)
            td = Vector(fda[2]).lerp(Vector(fdb[2]), w)
            dphi = math.atan2(td.z, td.x) - math.atan2(t0.z, t0.x)
            dphi = math.atan2(math.sin(dphi), math.cos(dphi))
            ideal = cd + Matrix.Rotation(-dphi, 3, "Y") @ (rest_co[i] - c0)
            stave_err = max(stave_err, (p - ideal).length)
        length = (b - n).length + (n - a).length
        rest_diff = max((co[i] - rest_co[i]).length for i in range(len(co))) if d == 0 else None
        results.append({"frame": frame, "draw": d, "stave_max_error_m": round(stave_err, 6),
                        "string_off_segment_m": round(string_err, 7),
                        "string_length_m": round(length, 7), "braced_max_diff_m": rest_diff})
    scene.frame_set(0)
    braced_len = braced["string_m"]
    failures = []
    for r in results:
        if r["stave_max_error_m"] > TOL_STAVE_M:
            failures.append(f"key {r['frame']}: a stave vertex is {r['stave_max_error_m']*1e3:.2f} mm off the solved shape")
        if r["string_off_segment_m"] > TOL_STRING_M:
            failures.append(f"key {r['frame']}: a string vertex leaves its straight segment by {r['string_off_segment_m']*1e3:.3f} mm")
        if abs(r["string_length_m"] - braced_len) > 1e-6:
            failures.append(f"key {r['frame']}: the string is {r['string_length_m'] - braced_len:+.2e} m long")
    if results[0]["braced_max_diff_m"] > 1e-6:
        failures.append(f"the braced key moves a vertex {results[0]['braced_max_diff_m']:.2e} m from the static mesh")
    return results, failures


def export(obj, arm, path):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, object_types={"ARMATURE", "MESH"},
                             apply_unit_scale=True, apply_scale_options="FBX_SCALE_NONE", global_scale=1.0,
                             axis_forward="-Y", axis_up="Z", mesh_smooth_type="FACE", use_tspace=True,
                             use_triangles=True, use_mesh_modifiers=False, add_leaf_bones=False,
                             primary_bone_axis="Y", secondary_bone_axis="X", armature_nodetype="NULL",
                             bake_anim=True, bake_anim_use_all_bones=True, bake_anim_use_nla_strips=False,
                             bake_anim_use_all_actions=False, bake_anim_force_startend_keying=True,
                             bake_anim_step=1.0, bake_anim_simplify_factor=0.0)


def check_geometry(obj, arm, record):
    """The emitted geometry for yumi_draw's checks (see the module docstring)."""
    import numpy as np
    me = obj.data
    if any(len(poly.vertices) != 3 for poly in me.polygons):
        raise RuntimeError("yumi rig: the static mesh is not triangulated")
    rest = np.array([v.co[:] for v in me.vertices], np.float32)
    tris = np.array([poly.vertices[:] for poly in me.polygons], np.int32)
    names = [b.name for b in arm.data.bones]
    index = {n: i for i, n in enumerate(names)}
    gname = {g.index: g.name for g in obj.vertex_groups}
    bi = np.zeros((len(me.vertices), 2), np.int16)
    bw = np.zeros((len(me.vertices), 2), np.float32)
    for v in me.vertices:
        ws = sorted(((g.weight, gname[g.group]) for g in v.groups if g.weight > 0), reverse=True)
        if not ws or len(ws) > 2 or abs(sum(w for w, _ in ws) - 1.0) > 1e-5:
            raise RuntimeError(f"yumi rig: vertex {v.index} has weights {ws}")
        for k, (w, n) in enumerate(ws):
            bi[v.index, k], bw[v.index, k] = index[n], w
    scene = bpy.context.scene
    deform = np.zeros((len(FRACTIONS), len(names), 4, 4), np.float32)
    for frame in range(len(FRACTIONS)):
        scene.frame_set(frame)
        for i, n in enumerate(names):
            pb, b = arm.pose.bones[n], arm.data.bones[n]
            deform[frame, i] = np.array(pb.matrix @ b.matrix_local.inverted())
    scene.frame_set(0)
    # The arrow, as committed, in its own frame.
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(ARROW_FBX), axis_forward="-Y", axis_up="Z", global_scale=1.0,
                             use_custom_normals=True, use_image_search=False)
    new = [o for o in bpy.data.objects if o not in before]
    ya = [o for o in new if o.type == "MESH"]
    if len(ya) != 1:
        raise RuntimeError(f"yumi rig: expected one arrow mesh, got {[o.name for o in ya]}")
    bpy.ops.object.select_all(action="DESELECT")
    ya[0].select_set(True)
    bpy.context.view_layer.objects.active = ya[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    av = np.array([v.co[:] for v in ya[0].data.vertices], np.float32)
    at = np.array([poly.vertices[:] for poly in ya[0].data.polygons if len(poly.vertices) == 3], np.int32)
    if len(at) != len(ya[0].data.polygons):
        raise RuntimeError("yumi rig: the arrow mesh is not triangulated")
    size = (av.max(0) - av.min(0)).tolist()
    want = record["assets"]["SM_Weapon_18_Ya"]["bounds_m"]
    if max(abs(a - b) for a, b in zip(size, want)) > 2e-5:
        raise RuntimeError(f"yumi rig: arrow bounds {size} differ from the record's {want}")
    for o in new:
        bpy.data.objects.remove(o, do_unlink=True)
    path = OUT / "W18_rig_check_geometry.npz"
    np.savez_compressed(path, rest=rest, tris=tris, bone_index=bi, bone_weight=bw, bones=np.array(names),
                        deform=deform, fractions=np.array(FRACTIONS, np.float32), arrow_verts=av, arrow_tris=at)
    return path, {"bow_vertices": int(len(rest)), "bow_triangles": int(len(tris)), "arrow_vertices": int(len(av)),
                  "arrow_triangles": int(len(at)), "arrow_bounds_m": [round(c, 6) for c in size]}


def main():
    t0 = time.time()
    record = json.loads(RECORD.read_text())
    reset()
    obj, sockets, size = import_static(record)
    braced = Y.braced()
    for name, want in braced["sockets"].items():
        if max(abs(a - b) for a, b in zip(sockets[name], want)) > 2e-5:
            raise RuntimeError(f"yumi rig: the model's {name} {want} differs from the imported socket {sockets[name]}")
    bind = Y.bone_joints(Y.shape_at(0.0))
    arm = build_armature(bind, sockets)
    rest_co = [v.co.copy() for v in obj.data.vertices]
    info, counts = assign_weights(obj, arm, braced, bind, sockets)
    print("YUMI_RIG_WEIGHTS", json.dumps(counts), flush=True)
    keys = key_draw(arm, bind)
    results, failures = check(obj, arm, info, braced, bind, rest_co)
    for r in results:
        print("YUMI_RIG_KEY", json.dumps(r), flush=True)
    if failures:
        raise SystemExit("yumi rig: " + "; ".join(failures))
    OUT.mkdir(parents=True, exist_ok=True)
    fbx = OUT / "SK_Weapon_18.fbx"
    export(obj, arm, fbx)
    geo, geo_summary = check_geometry(obj, arm, record)
    print("YUMI_RIG_GEOMETRY", json.dumps(geo_summary), flush=True)
    bones = [{"name": b.name, "parent": b.parent.name if b.parent else None, "head": [round(c, 7) for c in b.head_local],
              "tail": [round(c, 7) for c in b.tail_local]} for b in arm.data.bones]
    rig = {
        "schema_version": 1, "asset": "SK_Weapon_18", "skeleton": "SK_Weapon_18_Skeleton", "action": "A_Weapon_18_Draw",
        "generator": GEN, "generator_sha256": sha256(ROOT / GEN),
        "inputs": {rel(p): sha256(p) for p in (STATIC_FBX, ARROW_FBX, RECORD, HERE / "yumi_draw.py",
                                                HERE / "create_runtime_weapon_yumi.py")},
        "versions": {"blender": bpy.app.version_string},
        "draw": {"frames": "frame i = draw fraction i/10 at 10 fps: the take A_Weapon_18_Draw's time in seconds is the "
                           "draw fraction (0-1 s); drive the animation's time from it",
                 "full_draw_m": Y.DRAW_M, "nock_z_m": Y.NOCK_Z, "string_m": braced["string_m"],
                 "release": "back to brace (frame 0) in 0.03 s; no overshoot past brace (the string is unstretched)"},
        "bones": bones, "weights": counts, "keys": keys,
        "sockets": {"Grip_L": {"bone": "Grip", "location_m": list(sockets["Grip_L"])},
                    "Muzzle": {"bone": "Grip", "location_m": list(sockets["Muzzle"])},
                    "Grip_R": {"bone": "String_Nock", "location_m": [0.0, 0.0, 0.0]},
                    "String_Upper": {"bone": "Tip_U", "location_m": [0.0, 0.0, 0.0]},
                    "String_Lower": {"bone": "Tip_L", "location_m": [0.0, 0.0, 0.0]}},
        "axes": record["axes"], "static_bounds_m": [round(c, 6) for c in size],
        "checks": results,
        "scope": "rig built on the committed static mesh; deformed vertices checked at the 11 keys in Blender. Not "
                 "imported, not drawn in the engine, not visually qualified.",
        "check_geometry": geo_summary,
        "exports": {rel(path): {"sha256": sha256(path), "bytes": path.stat().st_size} for path in (fbx, geo)},
    }
    (OUT / "rig_record.json").write_text(json.dumps(rig, indent=1) + "\n")
    print("YUMI_RIG_READY", rel(fbx), f"{fbx.stat().st_size} bytes", f"{time.time() - t0:.1f}s", flush=True)


if __name__ == "__main__":
    main()
