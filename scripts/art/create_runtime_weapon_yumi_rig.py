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
   There are 28 bones:
   - Grip, the root at Grip_L;
   - LimbU_01-12 and LimbL_01-08 at yumi_draw.bone_joints of the braced
     shape, each a child of Grip;
   - the string's seven (yumi_draw.string_frames): Tip_L and Tip_U at the
     grooves, and String_Bend_L2, String_Bend_L1, String_Nock,
     String_Bend_U1 and String_Bend_U2 round the nock. Each turns with the
     string, so its sections stay square to it.
3. **Weights,** deterministic and the model of yumi_draw.skinning_error.
   - Only the string's own island may ride the string bones: the mesh
     island almost wholly on the braced string line. Choosing vertex by
     vertex by distance put the loops round the hazu on the limbs and the
     recurved tip's stave on the string, and webs stretched between them
     (Codex's review of the schema-2 attempt).
   - A string vertex within 4 mm of the braced string line, between its two
     grooves, goes to String_Nock and the nearer tip, linear in height, so
     each segment stays straight.
   - The string's loops beyond its grooves, and every other vertex, go to
     the two limb joints either side of its arc position along the stave
     centreline, linear in arc. The loops therefore ride the hazu they wrap.
4. **The Draw action** (A_Weapon_18_Draw): frame i is draw fraction i/10, 11
   keys. The scene runs at 10 fps, so the take's time in seconds is the draw
   fraction (0-1 s). The scene is named after the action, so the FBX take
   (and Unreal's animation) is A_Weapon_18_Draw, not "Scene". Each limb bone is posed from yumi_draw.shape_at(d): its joint's head
   and its tangent's turn about Y. The string's bones follow string_frames:
   the tips at the drawn grooves turned with their segments, and the bend
   round its fillet, whose apex (String_Nock, Grip_R) is 3.4 mm inside the
   drawn V at (-0.88, 0, 0.07).
5. **Checks, on the evaluated (deformed) mesh at every key:**
   - every stave vertex against its section carried rigidly by the solved
     shape;
   - the string vertices on their two straight segments;
   - the string's length unstretched;
   - the braced key identical to the static mesh;
   - every triangle against its rest size. An edge may grow 25% or 1 mm,
     whichever is larger. A face joining two differently driven parts
     stretches although each vertex alone passes.
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
     - each bone's bind and every key's pose matrices (yumi_draw.RIG_SCHEMA);
     - the committed arrow (SM_Weapon_18_Ya) in its own frame, Nock at the
       origin and Tip on +X.

The arrow (SM_Weapon_18_Ya) stays its own static mesh, attached by the
runtime at String_Nock. Gameplay aim, ammo and damage are unchanged.
"""
from __future__ import annotations

import bisect
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
STRING_ISLAND_SHARE = 0.98       # an island this much within STRING_RADIUS_M of the line is the string's own
STRETCH_RATIO = 1.25            # a triangle edge may grow 25% through the draw...
STRETCH_ABS_M = 0.001           # ...or 1 mm, whichever is larger; past both, the build refuses
SECTION_TOL_M = 0.0003          # a string vertex's distance from the string's axis may change this much
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
    # The string's seven bones (yumi_draw.string_frames), each along the string.
    frames = Y.string_frames(0.0)
    for name in Y.STRING_BONES:
        head, phi = frames[name]
        b = arm_data.edit_bones.new(name)
        b.head = Vector(tuple(head))
        b.tail = b.head + Vector((math.cos(phi), 0.0, math.sin(phi))) * 0.02
        b.roll = 0.0
        b.parent = grip
        b.use_connect = False
    for name, loc in (("Tip_U", sockets["String_Upper"]), ("Tip_L", sockets["String_Lower"]),
                      ("String_Nock", sockets["Grip_R"])):
        if (Vector(tuple(frames[name][0])) - Vector(loc)).length > 2e-5:
            raise RuntimeError(f"yumi rig: {name} at {tuple(frames[name][0])}, its socket at {loc}")
    bpy.ops.object.mode_set(mode="OBJECT")
    return arm


def islands(me):
    """Each vertex's connected-component id over the mesh's faces."""
    parent = list(range(len(me.vertices)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for poly in me.polygons:
        vs = poly.vertices
        r0 = find(vs[0])
        for v in vs[1:]:
            r = find(v)
            if r != r0:
                parent[r] = r0
    return [find(v) for v in range(len(me.vertices))]


def string_vertices(obj, a, b):
    """The string's islands, chosen whole by geometry: (segment, loops).

    Only the string's own islands may ride the string bones (Codex's review
    of the schema-2 attempt). Chosen vertex by vertex by distance from the
    string line, the loops round both hazu went to the limbs and the
    recurved upper tip's stave to the string; 110 faces between them
    stretched up to 14.9x at full draw. The static bow has one baked slot
    (M_Weapon_18), so islands are told apart by shape, not material:
    - **The string:** every island almost wholly (STRING_ISLAND_SHARE)
      within STRING_RADIUS_M of the braced line rides the string bones
      whole. That is the string itself and what is wound on it, such as the
      nakajikake.
    - **Loops:** a short island at a groove's end rides the limb whole.
    - **Everything else** is stave, however close some of its vertices come
      to the string."""
    me = obj.data
    comp = islands(me)
    ab = b - a
    members = {}
    for v in me.vertices:
        members.setdefault(comp[v.index], []).append(v.index)
    segment, loops = set(), set()
    for c, vs in members.items():
        ts, offs = [], []
        for i in vs:
            p = me.vertices[i].co
            t = (p - a).dot(ab) / ab.length_squared
            ts.append(t)
            offs.append((a + ab * t - p).length)
        near = sum(o < STRING_RADIUS_M for o in offs) / len(vs)
        if near < STRING_ISLAND_SHARE:
            continue
        at_groove = min(ts) < 0.02 or max(ts) > 0.98
        if at_groove and max(ts) - min(ts) <= 0.5:
            loops.update(vs)                     # a loop round a hazu: it stays with the tip
            continue
        if max(offs) >= STRING_RADIUS_M:
            raise RuntimeError(f"yumi rig: a string island has vertices {max(offs) * 1e3:.2f} mm off its line")
        # The string itself, and anything wound on it between the grooves (the
        # nakajikake serving at the nock): it travels with the string. Corrected
        # attempt 1 sent the serving to the limb, to float near brace at full draw.
        segment.update(vs)
    if not any(max((me.vertices[i].co - a).dot(ab) / ab.length_squared for i in vs) -
               min((me.vertices[i].co - a).dot(ab) / ab.length_squared for i in vs) > 0.5
               for c, vs in members.items() if set(vs) <= segment):
        raise RuntimeError("yumi rig: no island spans the string between its grooves")
    return segment, loops


def assign_weights(obj, arm, braced, bind, sockets):
    """Deterministic weights (see the module docstring). Returns per-vertex
    (kind, data) for the checks: ('string', s) or ('stave', sig); the
    string's loops beyond its grooves are 'stave', riding the limb tip."""
    cl = centreline(braced)
    a, b = Vector(sockets["String_Lower"]), Vector(sockets["String_Upper"])
    groups = {}
    for name in ["Grip", *Y.STRING_BONES, *sum(bone_names(), [])]:
        groups[name] = obj.vertex_groups.new(name=name)
    f0 = Y.string_frames(0.0)
    v0 = Vector(tuple(f0["String_Nock"][0]))
    e0 = Vector((math.cos(f0["Tip_L"][1]), 0.0, math.sin(f0["Tip_L"][1])))
    sig_b = [(Vector(tuple(f0[n][0])) - v0).dot(e0) for n in Y.STRING_BONES]
    ab = b - a
    lims = {"upper": Y.L_UP, "lower": Y.L_LOW}
    info = []
    counts = {"string": 0, "stave": 0, "string_loops": 0}
    segment, loops = string_vertices(obj, a, b)
    for v in obj.data.vertices:
        p = v.co
        is_string = v.index in segment
        if v.index in loops:
            counts["string_loops"] += 1
        if is_string:
            # Along the braced string from the nock: between the two string
            # bones either side, linear, so straight parts stay straight and
            # the bend follows the fillet's bones.
            sig = (p - v0).dot(e0)
            k = max(min(bisect.bisect_right(sig_b, sig) - 1, len(sig_b) - 2), 0)
            w = min(max((sig - sig_b[k]) / (sig_b[k + 1] - sig_b[k]), 0.0), 1.0)
            groups[Y.STRING_BONES[k]].add([v.index], 1.0 - w, "REPLACE")
            groups[Y.STRING_BONES[k + 1]].add([v.index], w, "REPLACE")
            info.append(("string", sig))
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
    # The string's bones turn with it: each segment's two ends with that
    # segment, the bend bones with the fillet round the nock (string_frames).
    f0, fd = Y.string_frames(0.0), Y.string_frames(d)
    for name in Y.STRING_BONES:
        dphi = math.atan2(math.sin(fd[name][1] - f0[name][1]), math.cos(fd[name][1] - f0[name][1]))
        out[name] = (Vector(tuple(fd[name][0])), Matrix.Rotation(-dphi, 4, "Y"))
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


def stretch(rest, co, tris):
    """Each triangle edge's growth through the deform, against STRETCH_RATIO
    and STRETCH_ABS_M, for every face: (largest ratio, largest growth in m,
    triangles past both)."""
    import numpy as np
    e0 = np.stack([np.linalg.norm(rest[tris[:, i]] - rest[tris[:, (i + 1) % 3]], axis=1) for i in range(3)], 1)
    e1 = np.stack([np.linalg.norm(co[tris[:, i]] - co[tris[:, (i + 1) % 3]], axis=1) for i in range(3)], 1)
    ratio = e1 / np.maximum(e0, 1e-9)
    grow = e1 - e0
    past = ((ratio > STRETCH_RATIO) & (grow > STRETCH_ABS_M)).any(1)
    return float(ratio.max()), float(grow.max()), int(past.sum())


def axis_distance(points, polyline):
    """Each point's distance from a polyline (numpy arrays)."""
    import numpy as np
    best = np.full(len(points), np.inf)
    for q0, q1 in zip(polyline[:-1], polyline[1:]):
        u = q1 - q0
        L2 = float(u @ u)
        if L2 < 1e-18:
            continue
        t = np.clip(((points - q0) @ u) / L2, 0.0, 1.0)
        best = np.minimum(best, np.linalg.norm(points - (q0 + t[:, None] * u), axis=1))
    return best


def check(obj, arm, info, braced, bind, rest_co):
    """The deformed mesh at every key: each vertex against the solved shape,
    and every face against its rest size (a face spanning two differently
    driven parts stretches, as the schema-2 attempt's string-to-stave webs did,
    though each vertex alone passed)."""
    import numpy as np
    scene = bpy.context.scene
    cl0 = centreline(braced)
    frames0 = Y._frames(braced["low"], braced["up"])
    tris = np.array([p.vertices[:] for p in obj.data.polygons], np.int64)
    rest_np = np.array([v[:] for v in rest_co])
    is_string = np.array([kind == "string" for kind, _ in info])
    rest_axis = axis_distance(rest_np[is_string], Y.string_centreline(0.0, 400))
    results = []
    for frame, d in enumerate(FRACTIONS):
        scene.frame_set(frame)
        dg = bpy.context.evaluated_depsgraph_get()
        ev = obj.evaluated_get(dg)
        me = ev.to_mesh()
        co = [v.co.copy() for v in me.vertices]
        ev.to_mesh_clear()
        co_np = np.array([c[:] for c in co])
        s_ratio, s_grow, s_bad = stretch(rest_np, co_np, tris)
        # The string round its fillet: every string vertex keeps its distance
        # from the string's axis (string_centreline), so sections stay rigid.
        axis_d = axis_distance(co_np[is_string], Y.string_centreline(d, 400))
        section_change = float(np.abs(axis_d - rest_axis).max())
        string_err = max(0.0, float(axis_d.max()) - STRING_RADIUS_M)
        shape = Y.shape_at(d)
        frames_d = Y._frames(shape["low"], shape["up"])
        sig_list = [f[0] for f in frames0]
        stave_err = 0.0
        s = shape["sockets"]
        a, b, n = Vector(s["String_Lower"]), Vector(s["String_Upper"]), Vector(s["Grip_R"])
        for i, (kind, val) in enumerate(info):
            p = co[i]
            if kind == "string":
                continue                          # measured above, against the string's own axis
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
                        "string_length_m": round(length, 7), "braced_max_diff_m": rest_diff,
                        "edge_ratio_max": round(s_ratio, 4), "edge_growth_max_m": round(s_grow, 6),
                        "stretched_triangles": s_bad, "string_section_change_m": round(section_change, 7)})
    scene.frame_set(0)
    braced_len = braced["string_m"]
    failures = []
    for r in results:
        if r["stretched_triangles"]:
            failures.append(f"key {r['frame']}: {r['stretched_triangles']} triangles stretch past {STRETCH_RATIO}x "
                            f"and {STRETCH_ABS_M * 1e3:.0f} mm (largest {r['edge_ratio_max']}x, "
                            f"{r['edge_growth_max_m'] * 1e3:.1f} mm)")
        if r["string_section_change_m"] > SECTION_TOL_M:
            failures.append(f"key {r['frame']}: a string section changes by {r['string_section_change_m']*1e3:.3f} mm "
                            "about the string's axis")
        if r["stave_max_error_m"] > TOL_STAVE_M:
            failures.append(f"key {r['frame']}: a stave vertex is {r['stave_max_error_m']*1e3:.2f} mm off the solved shape")
        if r["string_off_segment_m"] > TOL_STRING_M:
            failures.append(f"key {r['frame']}: a string vertex leaves the string's axis by {r['string_off_segment_m']*1e3:.3f} mm")
        if abs(r["string_length_m"] - braced_len) > 1e-6:
            failures.append(f"key {r['frame']}: the string is {r['string_length_m'] - braced_len:+.2e} m long")
    if results[0]["braced_max_diff_m"] > 1e-6:
        failures.append(f"the braced key moves a vertex {results[0]['braced_max_diff_m']:.2e} m from the static mesh")
    return results, failures


def socket_frames(arm, bone, mesh_frame):
    """A socket's mesh-frame location and its bone-local offset on ``bone``
    (Blender metres), from the bone's bind matrix; plus the bind itself."""
    b = arm.data.bones[bone]
    local = b.matrix_local.inverted() @ Vector(mesh_frame)
    return {"bone": bone, "mesh_frame_m": [round(c, 7) for c in mesh_frame],
            "bone_local_m": [round(c, 7) for c in local],
            "bone_bind_matrix": [[round(c, 7) for c in row] for row in b.matrix_local]}


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
    pose = np.zeros((len(FRACTIONS), len(names), 4, 4), np.float64)
    bind = np.array([np.array(arm.data.bones[n].matrix_local) for n in names], np.float64)
    for frame in range(len(FRACTIONS)):
        scene.frame_set(frame)
        for i, n in enumerate(names):
            pose[frame, i] = np.array(arm.pose.bones[n].matrix)   # armature space = local to Grip (identity)
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
    # bind and pose (armature space, which is local to the identity Grip root)
    # let the checker interpolate between keys as the take plays: each bone's
    # local translation lerped and rotation nlerped. Y.RIG_SCHEMA is the only
    # schema yumi_draw.load_rig accepts.
    np.savez_compressed(path, schema=np.array(Y.RIG_SCHEMA), rest=rest, tris=tris, bone_index=bi, bone_weight=bw,
                        bones=np.array(names), bind=bind, pose=pose, fractions=np.array(FRACTIONS, np.float32),
                        arrow_verts=av, arrow_tris=at)
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
        # 3: the string's seven turning bones round a fillet at the nock (28 bones).
        "schema_version": 3, "check_geometry_schema": Y.RIG_SCHEMA,
        "asset": "SK_Weapon_18", "skeleton": "SK_Weapon_18_Skeleton", "action": "A_Weapon_18_Draw",
        "generator": GEN, "generator_sha256": sha256(ROOT / GEN),
        "inputs": {rel(p): sha256(p) for p in (STATIC_FBX, ARROW_FBX, RECORD, HERE / "yumi_draw.py",
                                                HERE / "create_runtime_weapon_yumi.py")},
        "versions": {"blender": bpy.app.version_string},
        "draw": {"frames": "frame i = draw fraction i/10 at 10 fps: the take A_Weapon_18_Draw's time in seconds is the "
                           "draw fraction (0-1 s); drive the animation's time from it",
                 "full_draw_m": Y.DRAW_M, "nock_z_m": Y.NOCK_Z, "string_m": braced["string_m"],
                 "release": "back to brace (frame 0) in 0.03 s; no overshoot past brace (the string is unstretched)"},
        "bones": bones, "weights": counts, "keys": keys,
        # Each socket in both frames (Codex's review of b55fe81): the mesh
        # (armature) frame as the static bow's record has it, and the bone-local
        # offset Unreal's skeleton socket needs, from the bone's own bind
        # matrix. Copying a mesh-frame offset onto a bone puts Muzzle 102.86 mm off.
        "sockets": {name: socket_frames(arm, bone, sockets[name])
                    for name, bone in (("Grip_L", "Grip"), ("Muzzle", "Grip"), ("Grip_R", "String_Nock"),
                                       ("String_Upper", "Tip_U"), ("String_Lower", "Tip_L"))},
        "axes": record["axes"], "static_bounds_m": [round(c, 6) for c in size],
        "checks": results,
        "stretch_gate": {"ratio": STRETCH_RATIO, "growth_m": STRETCH_ABS_M, "applies_to": "every face, no exception",
                         "string_section_tol_m": SECTION_TOL_M},
        "string": {"bones": list(Y.STRING_BONES), "bend_half_arc_m": Y.STRING_BEND_M,
                   "nock": "String_Nock is the apex of the bend's fillet: Grip_R and the arrow's nock ride it, "
                           "3.4 mm inside the model's sharp V at full draw"},
        "scope": "rig built on the committed static mesh; deformed vertices checked at the 11 keys in Blender. Not "
                 "imported, not drawn in the engine, not visually qualified.",
        "check_geometry": geo_summary,
        "exports": {rel(path): {"sha256": sha256(path), "bytes": path.stat().st_size} for path in (fbx, geo)},
    }
    (OUT / "rig_record.json").write_text(json.dumps(rig, indent=1) + "\n")
    print("YUMI_RIG_READY", rel(fbx), f"{fbx.stat().st_size} bytes", f"{time.time() - t0:.1f}s", flush=True)


if __name__ == "__main__":
    main()
