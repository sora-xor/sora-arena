"""Skin the authored Nyaakoto source to the runtime samurai skeleton.

Run after create_nyaagyu_hero_character.py and rig_original_cats.py. The review
source remains editable/unrigged; this exports the campaign/Arena world visual
under the existing SK_NyaagyuSamurai and A_NyaagyuSamurai_Walk identities.
Armor, face, bow, arrows and kamon use rigid per-part weights so their authored
silhouettes survive movement. This is an animation integration pass, not a
production deformation/groom or a photoreal shipping-character claim.

**The third-person grip contract** (docs/art-direction/THIRD_PERSON_GRIP_CONTRACT.md),
slice A. Its part rules are shared with the LODs (nyaakoto_runtime_parts.py).
- **The arm bones** sit where the hero's arm parts are. The shoulder is
  Shoulder_joint's centre; the elbow and wrist are Fur_forearm's two ends;
  the hand runs from the wrist to the paw's grip channel. The inherited
  prototype bones lay 10.9 cm (elbow) and 12.1 cm (wrist) off the mesh
  (Saved/W18Rebuild/s60_grip_contract).
- **Sides are anatomical:** _R is the character's right (Blender -Y). The
  motion is unchanged, since each key keeps its side's sign.
- **The paws are closed** around a grip channel (third_person_rig.CHANNEL_CM),
  at most 11 cm across it. The open source fingers and thumb are rebuilt
  here as curled tubes; the review source keeps its own. The palm is
  narrowed to the same breadth.
- **The sheathed sword set** (Saya_, Sageo_, Katana_) leaves the body. The
  runtime carries the authored W00 saya and katana at sockets instead.
  No material slot is used by those parts alone (checked here), so the 23
  slots stay. The bow, quiver and arrows stay on the body until their gear
  assets exist.
- **A_NyaagyuSamurai_Guard** is solved by two-bone IK on these chains
  (third_person_rig) and keyed beside the walk. It is an interim one-paw
  guard: the contract's two-paw grip and left-hand closure stay open.
- **The checks** (mesh_clearance) run before anything is written. They use
  the posed visible mesh and the authored W00 katana and saya at their
  sockets. A failing check writes nothing.
- **Review renders:** the guard and the sheathed carry, from the front and
  the sides.
- **The record** (runtime_skin_manifest.json "third_person") carries:
  - the sockets' bind transforms, for the import;
  - every check, with its method and its calibration.

`--explore` measures candidate stances and saya placements, and the clearance
the two-paw grip lacks. It prints them and stops before writing anything.

`--study two_paw [--variant arm=1.15,palm=0.85,chest=0.9] --study-out <name>`
measures the contract's two-paw guard on an anatomy and armour variant. The
variant (nyaakoto_runtime_parts.apply_variant) is applied in memory only. It
writes its review renders to Saved/W18Rebuild/<name>/ and nothing else.
`--stance 34,0,106:far_fwd` measures and renders that one two-paw stance
(Grip_L in Unreal cm, and an elbow pole set) at full review quality, instead
of the whole grid. The contract-target shift analysis is then skipped.

`--study empty_paw` and `--study saya` measure, and render from the left, the
empty-fist shape keys and the saya carry candidates (both written to
Saved/W18Rebuild/<name>/ only).
"""

from __future__ import annotations

from collections import Counter
import hashlib
import json
import math
import os
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mesh_clearance as MC  # noqa: E402
import nyaakoto_runtime_parts as RP  # noqa: E402
import third_person_rig as TP  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
STUDY = ARGS[ARGS.index("--study") + 1] if "--study" in ARGS else None
EXPLORE = "--explore" in ARGS or STUDY is not None                  # a study writes only to Saved/
VARIANT = dict(kv.split("=") for kv in ARGS[ARGS.index("--variant") + 1].split(",")) if "--variant" in ARGS else {}
STUDY_OUT = ARGS[ARGS.index("--study-out") + 1] if "--study-out" in ARGS else None
STANCE = ARGS[ARGS.index("--stance") + 1] if "--stance" in ARGS else None    # "34,0,106:far_fwd", two_paw only

ROOT = Path(__file__).resolve().parents[2]
HERO = ROOT / "Content/SourceArt/Characters/Hero"
OUT = ROOT / "Content/SourceArt"
SOURCE = HERO / "Nyaagyu_HeroCharacter.blend"
MANIFEST = HERO / "runtime_skin_manifest.json"
W00_DIR = OUT / "Weapons/Runtime/W00_Katana"
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
bpy.context.preferences.filepaths.save_version = 0
source_record = json.loads((HERO / "manifest.json").read_text())
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == source_record["blend_sha256"]
assert source_record["insignia_sha256"] == json.loads(
    (OUT / "UI/sora_logo_manifest.json").read_text())["source_sha256"]
pbr_slots = set(json.loads((HERO / "PBR/manifest.json").read_text())["material_slots"])
w00_record = json.loads((W00_DIR / "build_record.json").read_text())
hero_gear = json.loads((ROOT / "Content/Data/viewmodels.json").read_text())["hero_gear"]
source = bpy.data.collections["NyaagyuHero_Editable"]
parts = sorted((o for o in source.objects if o.type == "MESH"), key=lambda o: o.name)
assert len(parts) == source_record["source_parts"]
by_name = {o.name: o for o in parts}
if VARIANT and STUDY is None:
    raise SystemExit("--variant is for studies only: the source body is not changed by a build")
variant_record = RP.apply_variant(parts, by_name, VARIANT)
ARMS = RP.arm_joints(by_name)


def materials_of(objs):
    return {m.name for o in objs for m in o.data.materials if m is not None}


runtime = bpy.data.collections.new("Nyaakoto_RuntimeSkin_NotReview")
bpy.context.scene.collection.children.link(runtime)
all_bones = ["root", "pelvis", "spine", "neck", "head", "tail_01", "tail_02", "tail_03"]
for side in ("L", "R"):
    all_bones.extend(f"{joint}_{side}" for joint in
                     ("upperarm", "forearm", "hand", "thigh", "shin", "foot"))
weights = Counter()
duplicates = []
kept_parts = [p for p in parts if RP.kept(p.name)]
removed = [p.name for p in parts if not RP.kept(p.name)]
added = {"R": RP.curled_paw("R", ARMS, by_name), "L": RP.curled_paw("L", ARMS, by_name)}
added_names = sorted(o.name for o in added["R"] + added["L"])   # the join below removes these objects
added_names_ordered = {s: [o.name for o in added[s]] for s in ("R", "L")}
# The slots: what leaves the body may use no slot alone; what the deferred gear alone uses is recorded.
deferred = [p for p in kept_parts if p.name.startswith(RP.DEFERRED_GEAR)]
body_materials = materials_of(kept_parts + added["R"] + added["L"])
assert body_materials == pbr_slots, sorted(body_materials ^ pbr_slots)
deferred_only = sorted(materials_of(deferred) - materials_of([p for p in kept_parts if p not in deferred]
                                                           + added["R"] + added["L"]))
part_names = []
for src in kept_parts + added["R"] + added["L"]:
    part_name = src.name                                  # before the rename below, which a fresh part shares
    fresh = part_name.startswith(RP.CURLED)
    obj = src if fresh else src.copy()
    if not fresh:
        obj.data = src.data.copy()
    runtime.objects.link(obj)
    if not fresh:
        obj.matrix_world = src.matrix_world.copy()
    if part_name.startswith("Paw_hand_"):                 # the palm narrowed to the closed paw's breadth
        RP.narrow_palm(obj)
    obj.name = f"Runtime_{part_name}"
    # The sculpted cheek and short-fur meshes have no UVs in the art-review
    # source. Give them stable face-plane coordinates before the final join so
    # the runtime fur normal/albedo maps do not collapse to one texel.
    if not obj.data.uv_layers:
        uv = obj.data.uv_layers.new(name="UVMap")
        for loop in obj.data.loops:
            point = obj.matrix_world @ obj.data.vertices[loop.vertex_index].co
            uv.data[loop.index].uv = ((point.y + .8) * 2.4, (point.z - .55) * 2.4)
    # Each face remembers its part through the join, for the clearance checks (removed again after the join).
    tag = obj.data.attributes.new("slice_a_part", "INT", "FACE")
    tag.data.foreach_set("value", [len(part_names)] * len(obj.data.polygons))
    vid = obj.data.attributes.new("slice_a_vid", "INT", "POINT")        # part << 20 | local vertex, through the join
    vid.data.foreach_set("value", [(len(part_names) << 20) | i for i in range(len(obj.data.vertices))])
    part_names.append(part_name)
    # Splitting source parts keeps hard armor, crest paths and arrow fletching
    # coherent while preserving every authored material slot on final join.
    groups = {bone: obj.vertex_groups.new(name=bone) for bone in all_bones}
    for vertex in obj.data.vertices:
        bone = RP.rig_bone(part_name, obj.matrix_world @ vertex.co)
        groups[bone].add([vertex.index], 1.0, "REPLACE")
        weights[bone] += 1
    duplicates.append(obj)
assert all(sum(1 for group in obj.data.vertices[0].groups) == 1 for obj in duplicates if obj.data.vertices)
assert weights["head"] > 1000 and weights["spine"] > 1000
bpy.ops.object.select_all(action="DESELECT")
for obj in duplicates:
    obj.select_set(True)
bpy.context.view_layer.objects.active = duplicates[0]
bpy.ops.object.join()
mesh = bpy.context.object
mesh.name = "SK_NyaagyuSamurai"
tag = mesh.data.attributes["slice_a_part"]
face_part = np.empty(len(mesh.data.polygons), np.int32)
tag.data.foreach_get("value", face_part)
mesh.data.attributes.remove(tag)
assert set(face_part.tolist()) == set(range(len(part_names)))
vid = mesh.data.attributes["slice_a_vid"]
vertex_tag = np.empty(len(mesh.data.vertices), np.int64)
_tmp = np.empty(len(mesh.data.vertices), np.int32)
vid.data.foreach_get("value", _tmp)
vertex_tag[:] = _tmp
mesh.data.attributes.remove(vid)
vertex_part, vertex_local = vertex_tag >> 20, vertex_tag & ((1 << 20) - 1)
# The empty fists as shape keys: a second curled paw per side on the closed channel, its tubes built exactly as the
# grip's, so vertex k of each empty part is vertex k of its grip part.
mesh.shape_key_add(name="Basis", from_mix=False)
inv_mesh = mesh.matrix_world.inverted()
empty_keys = {}
for side in ("R", "L"):
    empty_parts = RP.curled_paw(side, {side: RP.empty_arm(ARMS[side])}, by_name)
    key = mesh.shape_key_add(name=f"PawEmpty_{side}", from_mix=False)
    # Blender 5.2 starts a new key at value 1.0 (run s90's diagnosis). Left so, every pose that never calls
    # set_empty showed both paws as empty fists: s89's grip crossed the tsuka in 6,557 pairs. The grip is the default.
    key.value = 0.0
    moved_v = 0
    for name, empty_obj in zip([o for o in added_names_ordered[side]], empty_parts):
        pi = part_names.index(name)
        idx = np.nonzero(vertex_part == pi)[0]
        assert len(idx) == len(empty_obj.data.vertices), (name, len(idx), len(empty_obj.data.vertices))
        for vi, li in zip(idx.tolist(), vertex_local[idx].tolist()):
            key.data[vi].co = inv_mesh @ (empty_obj.matrix_world @ empty_obj.data.vertices[li].co)
        moved_v += len(idx)
    for o in empty_parts:
        me = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.meshes.remove(me)
    empty_keys[side] = moved_v
assert [(kb.name, kb.value) for kb in mesh.data.shape_keys.key_blocks[1:]] == [("PawEmpty_R", 0.0), ("PawEmpty_L", 0.0)]
assert {m.name for m in mesh.data.materials} == pbr_slots
coat=mesh.data.color_attributes.get("CoatBlend")
assert coat is not None and coat.domain=="CORNER"
mesh.data.color_attributes.active_color=coat
assert len(mesh.data.vertices) == sum(weights.values())
assert all(len(vertex.groups) == 1 for vertex in mesh.data.vertices)

bpy.ops.object.select_all(action="DESELECT")
bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
rig = bpy.context.object
rig.name = "RIG_NyaagyuSamurai"
bones = rig.data.edit_bones
bones.remove(bones[0])


def bone(name, head, tail, parent=None):
    b = bones.new(name)
    b.head = head
    b.tail = tail
    if parent:
        b.parent = bones[parent]


bone("root", (0, 0, 0), (0, 0, .20))
bone("pelvis", (0, 0, .65), (0, 0, .85), "root")
bone("spine", (0, 0, .85), (0, 0, 1.19), "pelvis")
bone("neck", (0, 0, 1.19), (0, 0, 1.39), "spine")
bone("head", (0, 0, 1.39), (0, 0, 1.75), "neck")
bone("tail_01", (-.12, 0, .70), (-.30, 0, .78), "pelvis")
bone("tail_02", (-.30, 0, .78), (-.48, 0, .9), "tail_01")
bone("tail_03", (-.48, 0, .9), (-.63, 0, 1.03), "tail_02")
for side, sign in (("R", -1), ("L", 1)):                 # _R is the character's right: Blender -Y
    arm = ARMS[side]
    bone(f"upperarm_{side}", arm["shoulder"], arm["elbow"], "spine")
    bone(f"forearm_{side}", arm["elbow"], arm["wrist"], f"upperarm_{side}")
    bone(f"hand_{side}", arm["wrist"], arm["channel"], f"forearm_{side}")
    bone(f"thigh_{side}", (0, sign * .14, .66), (0, sign * .15, .36), "pelvis")
    bone(f"shin_{side}", (0, sign * .15, .36), (0, sign * .15, .10), f"thigh_{side}")
    bone(f"foot_{side}", (0, sign * .15, .10), (.18, sign * .15, .055), f"shin_{side}")
bpy.ops.object.mode_set(mode="OBJECT")
assert len(rig.data.bones) == 20 and set(all_bones) == set(rig.data.bones.keys())
modifier = mesh.modifiers.new("Nyaakoto_SourcePartSkin", "ARMATURE")
modifier.object = rig
mesh.parent = rig
rig.animation_data_create()
actions = {}
if "--diag-keys" in ARGS:                                  # run s90: why s89's grip paws behaved as empty fists
    bpy.context.view_layer.update()
    keys = mesh.data.shape_keys
    rows = [{"name": kb.name, "value": kb.value, "relative_key": kb.relative_key.name, "mute": kb.mute}
            for kb in keys.key_blocks]
    finger = np.isin(vertex_part, [part_names.index(n) for s in ("R", "L") for n in added_names_ordered[s]])
    ev = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me_ev = ev.to_mesh()
    evaluated = np.array([list(v.co) for v in me_ev.vertices])
    ev.to_mesh_clear()
    base = np.array([list(v.co) for v in mesh.data.vertices])
    blocks = {kb.name: np.array([list(d.co) for d in kb.data]) for kb in keys.key_blocks}
    gap = lambda a, b: round(float(np.abs(a - b)[finger].max()), 6)  # noqa: E731
    print("DIAG_KEYS " + json.dumps({"reference": keys.reference_key.name, "use_relative": keys.use_relative,
                                     "blocks": rows, "active_index": mesh.active_shape_key_index,
                                     "show_only_shape_key": mesh.show_only_shape_key, "finger_vertices": int(finger.sum()),
                                     "evaluated_vs_mesh": gap(evaluated, base),
                                     "evaluated_vs_blocks": {n: gap(evaluated, b) for n, b in blocks.items()},
                                     "mesh_vs_blocks": {n: gap(base, b) for n, b in blocks.items()}}), flush=True)
    print("DIAG_KEYS_DONE", flush=True)
    sys.exit(0)

# --- Posing by the contract's sockets ---------------------------------------------------------------------------------
# GUARD is the stance A_NyaagyuSamurai_Guard holds, an interim one-paw (katate) chudan chosen from the --explore
# tables (Saved/W18Rebuild/s61_guard_explore.run*): in front of the right side, the blade 30 deg up and turned 15 deg
# in so the kissaki is near the centreline, the elbow out, the left paw at the hip by the saya. It does not close the
# contract's two-paw grip (4.5, 4.7), which stays open:
# - its first target, two paws with Grip_L at (24, 0, 100) at 30 deg, is reachable (88.6 % / 75.9 %), but the rear paw
#   lies against the chest armour (run1, run2; --explore measures what it lacks);
# - every two-paw grip far enough forward to clear it is out of the right arm's reach.
GUARD = {"grip_r": (40.0, 18.0, 110.0), "elevation_deg": 30.0, "yaw_deg": -15.0,
         "poles": {"R": (-0.3, -1.0, -0.5)}, "left_paw": (20.0, -34.0, 92.0)}
POLES = {"R": (-0.2, -0.5, -1.0), "L": (-0.2, 0.5, -1.0)}           # elbows down and out
# The saya's socket, measured on the visible mesh (Saved/W18Rebuild/s63_sliceA_explore_v2).
# - viewmodels.json's planned gear_saya_l, (17, -25, 95) at (0, 180, 0), lies above the obi. The saya crosses the
#   haori's skirt and, walking, the tail: up to 1238 visible triangle pairs. Its hilt crosses the dō's lowest plate.
# - At the obi's height the saya passes through the obi, its intended tuck. With the koiguchi at x 17 or 21, the tsuba
#   sits inside the obi or the sash band, whose front face is at 21.3.
# - Here, with the koiguchi at x 23 and the plan's rotation, there is no visible crossing and nothing contained, at rest
#   and through the walk. Its neighbours 1.5 cm out and 1 cm up also pass.
# - The plan's edge-down rotation also keeps the authored kurikata on the outer face.
SAYA_SOCKET = dict(hero_gear["sockets"]["gear_saya_l"], bind_component_cm=[23.0, -24.0, 85.5],
                   rotation_deg=[0.0, 180.0, 0.0])
SAYA_SOCKET_SOURCE = ("measured on the visible mesh (Saved/W18Rebuild/s63_sliceA_explore_v2); replaces viewmodels.json's "
                      "planned gear_saya_l (17, -25, 95), which crosses the haori, the tail and the dō")
TUCK = ("Obi_waist", "Resistance_sash_band")             # the obi the saya is thrust through: its crossings are the tuck
HEAD = {"head", "neck"}


def set_dir(pb, head, tail):
    """A pose bone's armature-space matrix with its Y along head -> tail, turned least from its rest."""
    rest = pb.bone.matrix_local.to_3x3()
    q = (rest @ Vector((0.0, 1.0, 0.0))).rotation_difference((tail - head).normalized())
    m = (q.to_matrix() @ rest).to_4x4()
    m.translation = head
    pb.matrix = m
    bpy.context.view_layer.update()


def socket_now(side):
    """The grip socket's current position (numpy) and rotation (numpy 3x3), from the posed hand bone."""
    ph = rig.pose.bones[f"hand_{side}"]
    rel = ph.bone.matrix_local.inverted() @ Matrix.Translation(ARMS[side]["channel"])
    pos = (ph.matrix @ rel).translation
    m3 = ph.matrix.to_3x3() @ ph.bone.matrix_local.to_3x3().inverted()
    rot = np.array([list(row) for row in m3]) @ ARMS[side]["socket_rot"]
    return np.array(pos), rot


def pose_arm(side, target_pos, target_rot, pole=None):
    arm = ARMS[side]
    pu, pf, ph = (rig.pose.bones[f"{j}_{side}"] for j in ("upperarm", "forearm", "hand"))
    s = np.array(pu.head)
    a, b = (arm["elbow"] - arm["shoulder"]).length, (arm["wrist"] - arm["elbow"]).length
    R, w = TP.hand_pose(np.array(arm["channel"]), arm["socket_rot"], np.array(arm["wrist"]), target_pos, target_rot)
    reach = float(np.linalg.norm(w - s) / (a + b))
    e = TP.two_bone(s, w, a, b, POLES[side] if pole is None else pole)   # ValueError when out of reach
    set_dir(pu, Vector(s), Vector(e))
    set_dir(pf, Vector(e), Vector(w))
    m = (Matrix(R.tolist()) @ ph.bone.matrix_local.to_3x3()).to_4x4()
    m.translation = Vector(w)
    ph.matrix = m
    bpy.context.view_layer.update()
    return reach


def pose_stance(stance, breath=0.0):
    tg = TP.socket_targets(stance, breath)
    poles = stance.get("poles", {})
    return {side: pose_arm(side, *tg[side], pole=poles.get(side)) for side in ("R", "L") if side in tg}


def reset_pose():
    for pb in rig.pose.bones:
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (0, 0, 0)
        pb.location = (0, 0, 0)
    bpy.context.view_layer.update()


def clip_pose(clip, t, guard=None):
    """The pose a clip keys at phase t (radians); the guard's arms by IK on the breathing body, the grips 0.4 cm up
    and down."""
    reset_pose()
    for side, sign in (("R", -1), ("L", 1)):              # each side keeps its sign, so the motion is unchanged
        rig.pose.bones[f"thigh_{side}"].rotation_euler[2] = math.sin(t) * .24 * sign if clip == "Walk" else 0
        rig.pose.bones[f"shin_{side}"].rotation_euler[2] = max(0, -math.sin(t) * sign) * .30 if clip == "Walk" else 0
        if clip != "Guard":
            rig.pose.bones[f"upperarm_{side}"].rotation_euler[2] = -math.sin(t) * .12 * sign if clip == "Walk" else math.sin(t) * .006
    rig.pose.bones["pelvis"].location[1] = abs(math.sin(t)) * .009 if clip == "Walk" else math.sin(t) * .003
    rig.pose.bones["spine"].rotation_euler[0] = math.sin(t) * .009
    rig.pose.bones["tail_02"].rotation_euler[0] = math.sin(t) * .08
    bpy.context.view_layer.update()
    if clip == "Guard":
        return pose_stance(guard or GUARD, breath=math.sin(t) * 0.004)
    return None


# --- The clearance checks' geometry: the posed body's triangles by part and bone; the W00 weapons as authored ---------
group_of = np.array([mesh.vertex_groups[v.groups[0].group].name for v in mesh.data.vertices])
if hasattr(mesh.data, "calc_loop_triangles"):
    mesh.data.calc_loop_triangles()
_lt = mesh.data.loop_triangles
TRI = np.empty(len(_lt) * 3, np.int32)
_lt.foreach_get("vertices", TRI)
TRI = TRI.reshape(-1, 3).astype(np.int64)
_poly = np.empty(len(_lt), np.int32)
_lt.foreach_get("polygon_index", _poly)
TRI_PART = np.array(part_names)[face_part[_poly]]
TRI_GROUPS = group_of[TRI]
UE = TP.blender_to_ue_point
BK = MC.BlenderBackend()


def posed_points():
    """The evaluated (posed, skinned) mesh's vertices in world metres."""
    bpy.context.view_layer.update()
    ev = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = ev.to_mesh()
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    ev.to_mesh_clear()
    mw = np.array([list(r) for r in mesh.matrix_world])
    return co.reshape(-1, 3).astype(np.float64) @ mw[:3, :3].T + mw[:3, 3]


def body_set(include=None, exclude=(), part_prefixes=None):
    """The body's triangles whose three vertices all follow bones in include (all if None) and none in exclude, or
    the parts named by prefix."""
    m = np.ones(len(TRI), bool)
    if include is not None:
        m &= np.isin(TRI_GROUPS, list(include)).all(1)
    if exclude:
        m &= ~np.isin(TRI_GROUPS, list(exclude)).any(1)
    if part_prefixes is not None:
        m &= np.array([n.startswith(part_prefixes) for n in TRI_PART])
    return MC.TriSet(TRI[m], TRI_PART[m])


SET = {
    "arms_low": body_set({"forearm_R", "forearm_L", "hand_R", "hand_L"}),
    "arm_low_R": body_set({"forearm_R", "hand_R"}), "arm_low_L": body_set({"forearm_L", "hand_L"}),
    "upper_arms": body_set({"upperarm_R", "upperarm_L"}),
    "torso": body_set({"spine", "pelvis"}),
    "head": body_set(HEAD),
    "hand_R": body_set({"hand_R"}),
    "body": body_set(),
    "body_but_hand_R": body_set(exclude={"hand_R"}),
    "body_but_head_hand_R": body_set(exclude=HEAD | {"hand_R"}),
    "hand_L": body_set({"hand_L"}), "hands": body_set({"hand_R", "hand_L"}),
    "body_but_hands": body_set(exclude={"hand_R", "hand_L"}),
    "body_but_head_hands": body_set(exclude=HEAD | {"hand_R", "hand_L"}),
    "obi": body_set(part_prefixes=TUCK),
}
DATA_KINDS = ("objects", "meshes", "materials", "images", "textures", "node_groups", "cameras", "lights", "actions",
              "armatures", "collections")
data_before_weapons = {k: set(getattr(bpy.data, k)) for k in DATA_KINDS}


def load_weapon(path, origin, expect):
    """An authored weapon FBX: its mesh in its origin socket's frame (Blender metres, the build record's axes), each
    socket read back against the build record within 1 mm, and the imported objects (kept for the review renders)."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(path))
    new = [o for o in bpy.data.objects if o not in before]
    sockets = {o.name.split(".")[0][len("SOCKET_"):]: o for o in new if o.name.startswith("SOCKET_")}
    loc, rot, _scale = sockets[origin].matrix_world.decompose()
    inv = (Matrix.Translation(loc) @ rot.to_matrix().to_4x4()).inverted()
    measured = {n: [round(float(v), 5) for v in (inv @ o.matrix_world.translation)] for n, o in sockets.items()}
    for n, want in expect.items():
        assert (Vector(measured[n]) - Vector(want)).length < 0.001, (path.name, n, measured[n], want)
    pts, tris, base = [], [], 0
    for o in new:
        if o.type != "MESH":
            continue
        me = o.data
        if hasattr(me, "calc_loop_triangles"):
            me.calc_loop_triangles()
        m = np.array([list(r) for r in (inv @ o.matrix_world)])
        co = np.empty(len(me.vertices) * 3, np.float32)
        me.vertices.foreach_get("co", co)
        pts.append(co.reshape(-1, 3).astype(np.float64) @ m[:3, :3].T + m[:3, 3])
        tv = np.empty(len(me.loop_triangles) * 3, np.int32)
        me.loop_triangles.foreach_get("vertices", tv)
        tris.append(tv.reshape(-1, 3).astype(np.int64) + base)
        base += len(me.vertices)
    return {"pts": np.concatenate(pts), "tris": np.concatenate(tris), "objects": new, "inv": inv,
            "imported": {o.name: o.matrix_world.copy() for o in new}, "sockets": measured, "file": path.name,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


KATANA = load_weapon(W00_DIR / "SM_Weapon_00.fbx", "Grip_R", w00_record["assets"]["SM_Weapon_00"]["sockets"])
SAYA = load_weapon(W00_DIR / "SM_Weapon_00_Saya.fbx", "Koiguchi", w00_record["assets"]["SM_Weapon_00_Saya"]["sockets"])
SEAT_X = TP.W00["sheath_seat_x"] / 100.0                 # m: Grip_R sits this far behind the Koiguchi, sheathed
seat_ring = int((np.abs(KATANA["pts"][:, 0] - SEAT_X) < 2e-5).sum())   # the front seppa's face is at the seat
assert seat_ring >= 8, seat_ring
K_ALL = MC.TriSet(KATANA["tris"], ["W00_Katana"] * len(KATANA["tris"]))
K_BLADE = MC.TriSet(KATANA["tris"][(KATANA["pts"][KATANA["tris"]][:, :, 0] >= SEAT_X - 1e-6).all(1)],
                    ["W00_habaki_to_kissaki"] * int((KATANA["pts"][KATANA["tris"]][:, :, 0] >= SEAT_X - 1e-6).all(1).sum()))
_hilt = (KATANA["pts"][KATANA["tris"]][:, :, 0] <= SEAT_X + 1e-6).all(1)   # sheathed, all of the katana that shows
K_HILT = MC.TriSet(KATANA["tris"][_hilt], ["W00_hilt"] * int(_hilt.sum()))
K_SAYA = MC.TriSet(SAYA["tris"], ["W00_Saya"] * len(SAYA["tris"]))


def place(weapon, pos, rot):
    return np.asarray(pos, np.float64) + weapon["pts"] @ np.asarray(rot, np.float64).T


def saya_at(entry):
    """A gear socket at the current pose: rigid on its bone (the rig sits at the origin)."""
    pb = rig.pose.bones[entry["bone"]]
    rel = pb.matrix @ pb.bone.matrix_local.inverted()
    pos, rot = TP.gear_socket_blender(entry)
    return np.array(rel @ Vector(pos)), np.array([list(r) for r in rel.to_3x3()]) @ rot


def sheathed(saya_pos, saya_rot):
    return saya_pos + saya_rot @ np.array([-SEAT_X, 0.0, 0.0]), saya_rot


def put(weapon, pos, rot):
    """Move the imported weapon so its origin socket sits at pos, rot (Blender)."""
    s = Matrix([[*rot[0], pos[0]], [*rot[1], pos[1]], [*rot[2], pos[2]], [0.0, 0.0, 0.0, 1.0]])
    for o in weapon["objects"]:
        if o.parent is None:
            o.matrix_world = s @ weapon["inv"] @ weapon["imported"][o.name]


REVIEW = {}
VIEWS = {"Front": (1.0, 0.0, 0.0), "SideRight": (0.0, -1.0, 0.0), "SideLeft": (0.0, 1.0, 0.0)}


def render_views(views, prefix, katana_at, saya_at_, samples=32, res=1100):
    """Ortho review renders of the current pose with the W00 katana and saya placed, one per view at
    "{prefix}_{view}.png". The source parts are hidden; the camera and sun are made once."""
    scene = bpy.context.scene
    for src in parts:
        src.hide_render = True
        src.hide_set(True)
    if not REVIEW:
        cam_data = bpy.data.cameras.new("SliceA_ReviewCam")
        cam = bpy.data.objects.new("SliceA_ReviewCam", cam_data)
        scene.collection.objects.link(cam)
        cam_data.type = "ORTHO"
        sun = bpy.data.objects.new("SliceA_ReviewSun", bpy.data.lights.new("SliceA_ReviewSun", "SUN"))
        sun.data.energy = 3.0
        scene.collection.objects.link(sun)
        REVIEW.update(cam=cam, sun=sun, old=scene.camera)
    cam, sun = REVIEW["cam"], REVIEW["sun"]
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    scene.render.resolution_x = scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    (kp, kr), (sp, sr) = katana_at, saya_at_
    put(SAYA, sp, sr)
    put(KATANA, kp, kr)
    every = np.concatenate([posed_points(), place(KATANA, kp, kr), place(SAYA, sp, sr)])
    lo, hi = every.min(0), every.max(0)
    centre = Vector(((lo + hi) / 2.0).tolist())
    out = []
    for view in views:
        d = Vector(VIEWS[view])
        span = max(float(np.abs((hi - lo) * (1.0 - np.abs(np.array(VIEWS[view]))))[:2].max()), float((hi - lo)[2]))
        cam.location = centre + d * 4.0
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        cam.data.ortho_scale = span * 1.08
        sun.rotation_euler = (-(d * 0.6) - Vector((0.0, 0.0, 0.8))).normalized().to_track_quat("-Z", "Y").to_euler()
        scene.camera = cam
        path = Path(f"{prefix}_{view}.png")
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        out.append(path)
    scene.camera = REVIEW["old"]
    return out


def end_review():
    for key in ("cam", "sun"):
        if key in REVIEW:
            bpy.data.objects.remove(REVIEW.pop(key), do_unlink=True)


def check_pose(saya_entry, held, only=None):
    """The visible-mesh checks at the current pose. held: the katana in the right paw (the guard), else sheathed.
    only: the names of the checks to run (all if None)."""
    pts = posed_points()
    sp, sr = saya_at(saya_entry)
    saya = place(SAYA, sp, sr)
    kp, kr = socket_now("R") if held else sheathed(sp, sr)
    katana = place(KATANA, kp, kr)
    hide = (SET["obi"], pts)
    plan = {"forearms_paws_vs_torso": lambda: MC.measure(BK, SET["arms_low"], pts, SET["torso"], pts, limit=0.02,
                                                         to_report=UE),
            "upper_arms_vs_torso": lambda: MC.measure(BK, SET["upper_arms"], pts, SET["torso"], pts, limit=0.0,
                                                      to_report=UE),
            "saya_vs_body": lambda: MC.measure(BK, K_SAYA, saya, SET["body"], pts, limit=0.0, hide=hide, allowed=TUCK,
                                               to_report=UE)}
    if held:
        plan.update({
            "katana_vs_body_but_holding_paw": lambda: MC.measure(BK, K_ALL, katana, SET["body_but_hand_R"], pts,
                                                                 limit=0.02, to_report=UE),
            "katana_vs_holding_paw": lambda: MC.measure(BK, K_ALL, katana, SET["hand_R"], pts, limit=0.01, to_report=UE),
            "blade_vs_head": lambda: MC.measure(BK, K_BLADE, katana, SET["head"], pts, limit=0.05, to_report=UE),
            "blade_vs_body": lambda: MC.measure(BK, K_BLADE, katana, SET["body_but_head_hand_R"], pts, limit=0.03,
                                                to_report=UE),
            "left_paw_vs_saya": lambda: MC.measure(BK, SET["arm_low_L"], pts, K_SAYA, saya, limit=0.02, to_report=UE)})
    else:                                                 # the blade is inside the saya; its hilt may not touch the obi
        plan["sheathed_hilt_vs_body"] = lambda: MC.measure(BK, K_HILT, katana, SET["body"], pts, limit=0.0, to_report=UE)
    out = {k: f() for k, f in plan.items() if only is None or k in only}
    kissaki = kp + kr @ (np.array(TP.W00["muzzle"]) / 100.0 * np.array([1.0, -1.0, 1.0]))
    out["kissaki_ue_cm"] = [round(float(v), 2) for v in UE(kissaki)]
    return out


GATES = {"forearms_paws_vs_torso": 0.0, "saya_vs_body": 0.0, "katana_vs_body_but_holding_paw": 0.0,
         "katana_vs_holding_paw": 0.0, "blade_vs_head": 0.05, "blade_vs_body": 0.03, "left_paw_vs_saya": 0.0,
         "sheathed_hilt_vs_body": 0.0}


def gates_of(res):
    """Each gated check: no visible crossing, nothing contained or ambiguous, and its exact minimum (5 cm blade to
    head, 3 cm blade to body). The upper arms at the shoulder are reported only: rigid parts meet there by build."""
    return {k: MC.passes(res[k], m) for k, m in GATES.items() if k in res}


def brief(res):
    return {k: (v if not isinstance(v, dict) else
                {f: v[f] for f in ("crossing_pairs_visible", "crossing_pairs_hidden", "crossing_pairs_allowed",
                                   "crossing_parts_visible", "contained", "contained_parts", "contained_allowed",
                                   "ambiguous", "open_islands", "separation_m", "separation_kind",
                                   "first_visible_crossing")})
            for k, v in res.items()}


# The empty fists by state: both paws empty out of combat; in the interim one-paw guard only the left. The runtime
# drives the same morph targets (PawEmpty_R, PawEmpty_L) by what each paw holds.
EMPTY_BY_CLIP = {"Idle": (1, 1), "Walk": (1, 1), "Guard": (0, 1)}


def set_empty(r_empty, l_empty):
    """The empty-fist shape keys: 1 an empty paw, 0 the paw round a hilt."""
    blocks = mesh.data.shape_keys.key_blocks
    blocks["PawEmpty_R"].value, blocks["PawEmpty_L"].value = float(r_empty), float(l_empty)
    bpy.context.view_layer.update()


if STUDY in ("saya", "empty_paw"):
    cal = MC.calibrate(BK)
    assert cal["ok"], cal
    out_dir = ROOT / "Saved/W18Rebuild" / STUDY_OUT if STUDY_OUT else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
    walk = (("Idle", 0.0), ("Walk", 0.0), ("Walk", math.pi / 2), ("Walk", math.pi), ("Walk", 1.5 * math.pi))
    if STUDY == "saya":
        base = dict(hero_gear["sockets"]["gear_saya_l"])
        cands = [dict(base, bind_component_cm=[23.0, y, 85.5], rotation_deg=[p_, 180.0 + yw, 0.0])
                 for y in (-24.0, -26.5) for p_ in (-10.0, -15.0, -20.0) for yw in (0.0, 8.0)]
        for k, c in enumerate(cands):
            row = {"socket": {f: c[f] for f in ("bind_component_cm", "rotation_deg")}, "frames": {}}
            ok = True
            for clip, ph in walk:
                clip_pose(clip, ph)
                set_empty(1, 1)
                res = check_pose(c, held=False, only={"saya_vs_body", "sheathed_hilt_vs_body"})
                g = gates_of(res)
                ok &= all(g.values())
                row["frames"][f"{clip}@{ph:.2f}"] = {"gates": g, "saya": brief(res)["saya_vs_body"],
                                                     "hilt": brief(res)["sheathed_hilt_vs_body"]}
            row["passes"] = bool(ok)
            if ok:                                     # the carry must clear the interim guard's empty left paw too
                clip_pose("Guard", 0.0)
                set_empty(0, 1)
                res = check_pose(c, held=True)
                g = gates_of(res)
                row["guard"] = {"gates": g, "checks": {n: brief(res)[n] for n in ("saya_vs_body", "left_paw_vs_saya")}}
                row["passes_guard"] = bool(all(g.values()))
            print("STUDY_SAYA " + json.dumps(row, default=str), flush=True)
            if ok and out_dir:
                clip_pose("Idle", 0.0)
                set_empty(1, 1)
                sp, sr = saya_at(c)
                render_views(("SideLeft",), out_dir / f"Saya_{k:02d}", sheathed(sp, sr), (sp, sr), samples=24, res=900)
                if row["passes_guard"]:
                    clip_pose("Guard", 0.0)
                    set_empty(0, 1)
                    render_views(("SideLeft",), out_dir / f"Saya_{k:02d}_Guard", socket_now("R"), saya_at(c), samples=24,
                                 res=900)
    else:
        for clip, (r_e, l_e) in (("Idle", (1, 1)), ("Guard", (0, 1))):
            clip_pose(clip, 0.0)
            set_empty(r_e, l_e)
            res = check_pose(SAYA_SOCKET, held=clip == "Guard")
            print("STUDY_EMPTY " + json.dumps({"clip": clip, "empty": [r_e, l_e], "gates": gates_of(res),
                                               "checks": brief(res)}, default=str), flush=True)
            if out_dir:
                sp, sr = saya_at(SAYA_SOCKET)
                held = socket_now("R") if clip == "Guard" else sheathed(sp, sr)
                render_views(("Front", "SideLeft", "SideRight"), out_dir / f"Empty_{clip}", held, (sp, sr), samples=24,
                             res=900)
    print("STUDY_COMPLETE", flush=True)
    sys.exit(0)

if STUDY == "two_paw":
    cal = MC.calibrate(BK)
    assert cal["ok"], cal
    lengths = {s: {"upper_arm_cm": round((ARMS[s]["elbow"] - ARMS[s]["shoulder"]).length * 100.0, 2),
                   "forearm_cm": round((ARMS[s]["wrist"] - ARMS[s]["elbow"]).length * 100.0, 2),
                   "channel_ue_cm": [round(float(v), 2) for v in UE(np.array(ARMS[s]["channel"]))]} for s in ("R", "L")}
    print("STUDY_VARIANT " + json.dumps({"variant": variant_record or "baseline", "arms": lengths}), flush=True)
    out_dir = ROOT / "Saved/W18Rebuild" / STUDY_OUT if STUDY_OUT else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
    # The contract's 4.5 target first. The palm reaches about 12 cm behind its grip and the haori's front is at x 20.6,
    # so the two-paw chudan is also tried further forward, where longer arms buy reach, and with the elbows brought
    # forward of the do.
    # The second round (Saved/W18Rebuild/s76_*): the forearms converge along the haori's front quadrant, so the elbows
    # are held forward and out of the chest, as a kendo chudan has them.
    pole_sets = {"fwd": {"R": (0.3, -0.3, -1.0), "L": (0.3, 0.3, -1.0)},
                 "out": {"R": (0.4, -1.0, -0.6), "L": (0.4, 1.0, -0.6)},
                 "far_fwd": {"R": (1.0, -0.6, -0.5), "L": (1.0, 0.6, -0.5)}}
    two_paw_stances = [{"grip_l": g, "elevation_deg": 30.0, "poles": poles, "pole_set": name}
                       for g in ((24.0, 0.0, 100.0), (28.0, 0.0, 100.0), (30.0, 0.0, 102.0), (32.0, 0.0, 104.0),
                                 (34.0, 0.0, 106.0))
                       for name, poles in pole_sets.items()]
    if STANCE:                                         # one stance, measured and rendered for review
        grip, pole_name = STANCE.split(":")
        two_paw_stances = [{"grip_l": tuple(float(v) for v in grip.split(",")), "elevation_deg": 30.0,
                            "poles": pole_sets[pole_name], "pole_set": pole_name}]
    for k, c in enumerate(two_paw_stances):
        reset_pose()
        row = {"stance": c}
        try:
            row["reach"] = {s: round(v, 4) for s, v in pose_stance(c).items()}
        except ValueError as exc:
            row["unreachable"] = str(exc)
            print("STUDY_TWO_PAW " + json.dumps(row, default=str), flush=True)
            continue
        pts = posed_points()
        kp, kr = socket_now("R")
        katana = place(KATANA, kp, kr)
        res = {"forearms_paws_vs_torso": MC.measure(BK, SET["arms_low"], pts, SET["torso"], pts, limit=0.02, to_report=UE),
               "katana_vs_body_but_paws": MC.measure(BK, K_ALL, katana, SET["body_but_hands"], pts, limit=0.02, to_report=UE),
               "katana_vs_paws": MC.measure(BK, K_ALL, katana, SET["hands"], pts, limit=0.01, to_report=UE),
               "blade_vs_head": MC.measure(BK, K_BLADE, katana, SET["head"], pts, limit=0.05, to_report=UE),
               "blade_vs_body": MC.measure(BK, K_BLADE, katana, SET["body_but_head_hands"], pts, limit=0.03, to_report=UE),
               "paw_vs_paw": MC.measure(BK, SET["hand_L"], pts, SET["hand_R"], pts, limit=0.02, to_report=UE),
               "upper_arms_vs_torso": MC.measure(BK, SET["upper_arms"], pts, SET["torso"], pts, limit=0.0, to_report=UE)}
        mins = {"blade_vs_head": 0.05, "blade_vs_body": 0.03}
        row["gates"] = {g: MC.passes(v, mins.get(g, 0.0)) for g, v in res.items() if g != "upper_arms_vs_torso"}
        row["checks"] = brief(res)
        row["kissaki_ue_cm"] = [round(float(v), 2) for v in UE(kp + kr @ (np.array(TP.W00["muzzle"]) / 100.0))]
        print("STUDY_TWO_PAW " + json.dumps(row, default=str), flush=True)
        if out_dir and k == 0:
            sp, sr = saya_at(SAYA_SOCKET)
            quality = {} if STANCE else {"samples": 24, "res": 900}  # with --stance: the build's review quality
            render_views(("Front", "SideRight", "SideLeft"), out_dir / "TwoPaw", (kp, kr), (sp, sr), **quality)
    if STANCE:
        print("STUDY_COMPLETE", flush=True)
        sys.exit(0)
    # How far each arm must still move forward at the contract's target to clear the torso by 5 mm.
    reset_pose()
    pose_stance(two_paw_stances[0])
    pts0 = posed_points()
    for side in ("L", "R"):
        verts = np.unique(SET[f"arm_low_{side}"].used)
        need, last = None, None
        for dx in [0.5 * i for i in range(0, 41)]:
            p = pts0.copy()
            p[verts, 0] += dx / 100.0
            r = MC.measure(BK, SET[f"arm_low_{side}"], p, SET["torso"], p, limit=0.005, to_report=UE)
            last = (dx, r["crossing_pairs_visible"], r["contained"], r["crossing_parts_visible"][:3])
            if MC.passes(r, 0.005):
                need = dx
                break
        print("STUDY_SHIFT " + json.dumps({"side": side, "forward_shift_needed_cm": need, "last": last}, default=str),
              flush=True)
    print("STUDY_COMPLETE", flush=True)
    sys.exit(0)

if EXPLORE:
    cal = MC.calibrate(BK)
    print("CLEARANCE_CALIBRATION " + json.dumps(cal, default=str), flush=True)
    assert cal["ok"], cal
    print("WEAPON_SOCKETS " + json.dumps({"katana": KATANA["sockets"], "saya": SAYA["sockets"], "seat_ring": seat_ring,
                                          "blade_triangles": len(K_BLADE), "hilt_triangles": len(K_HILT),
                                          "katana_triangles": len(K_ALL)}), flush=True)
    print("BODY " + json.dumps({"parts": len(part_names), "removed": len(removed), "vertices": len(mesh.data.vertices),
                                "triangles": len(TRI), "deferred_gear_parts": len(deferred),
                                "slots_only_deferred_gear_uses": deferred_only,
                                "islands": {k: [len(s.closed), int((~s.closed).sum())] for k, s in SET.items()}}),
          flush=True)
    reset_pose()
    rest_pts = posed_points()
    print("REST " + json.dumps(brief({k: MC.measure(BK, SET[a], rest_pts, SET["torso"], rest_pts, limit=lim, to_report=UE)
                                      for k, a, lim in (("forearms_paws_vs_torso", "arms_low", 0.02),
                                                        ("upper_arms_vs_torso", "upper_arms", 0.0))}), default=str),
          flush=True)
    # 1. The saya's socket: the plan first, then through the obi with the koiguchi just in front of it (the obi's
    #    front face is at x 19.8), at rest and through the walk. The nearest passing placement to the plan is chosen.
    planned = hero_gear["sockets"]["gear_saya_l"]
    saya_candidates = ([planned, dict(planned, bind_component_cm=[17.0, -26.5, 86.0])]
                       + [dict(planned, bind_component_cm=[x, y, z], rotation_deg=[0.0, 180.0, r])
                          for x in (21.0, 23.0) for y in (-24.0, -25.5) for z in (85.5, 86.5) for r in (0.0, 180.0)])
    passing = []
    for c in saya_candidates:
        row = {"socket": {k: c[k] for k in ("bone", "bind_component_cm", "rotation_deg")}, "frames": {}}
        ok = True
        for clip, t in (("Idle", 0.0), ("Walk", 0.0), ("Walk", math.pi / 2), ("Walk", math.pi), ("Walk", 1.5 * math.pi)):
            clip_pose(clip, t)
            res = check_pose(c, held=False, only={"saya_vs_body", "sheathed_hilt_vs_body"})
            g = gates_of(res)
            ok &= g["saya_vs_body"] and g["sheathed_hilt_vs_body"]
            row["frames"][f"{clip}@{t:.2f}"] = {"gates": g, "saya": brief(res)["saya_vs_body"],
                                                "sheathed_hilt": brief(res)["sheathed_hilt_vs_body"]}
        row["passes"] = bool(ok)
        print("SAYA_EXPLORE " + json.dumps(row, default=str), flush=True)
        if ok:
            passing.append(c)
    chosen = min(passing, key=lambda c: (float(np.linalg.norm(np.subtract(c["bind_component_cm"],
                                                                           planned["bind_component_cm"]))),
                                         c["rotation_deg"][2] != 0.0)) if passing else None
    print("SAYA_CHOSEN " + json.dumps(chosen), flush=True)
    saya_entry = chosen or planned
    # 2. The interim one-paw guard and its variants, and the contract's two-paw target kept, with the chosen saya.
    for c in ([{"grip_l": (24.0, 0.0, 100.0), "elevation_deg": 30.0}, GUARD, dict(GUARD, grip_r=(38.0, 16.0, 108.0)),
               dict(GUARD, grip_r=(40.0, 15.0, 105.0), yaw_deg=-12.0), dict(GUARD, left_paw=(14.0, -36.0, 90.0)),
               dict(GUARD, left_paw=(22.0, -33.0, 96.0))]):
        reset_pose()
        row = {"stance": c}
        try:
            row["reach"] = {s: round(v, 4) for s, v in pose_stance(c).items()}
            res = check_pose(saya_entry, held=True)
            row["gates"] = gates_of(res)
            row["checks"] = brief(res)
        except ValueError as exc:
            row["unreachable"] = str(exc)
        print("GUARD_EXPLORE " + json.dumps(row, default=str), flush=True)
    # 3. The two-paw target: how far forward each arm must move to clear the torso (no crossing, nothing contained,
    #    0.5 cm apart), and the reach a grip that far forward would need.
    two = {"grip_l": (24.0, 0.0, 100.0), "elevation_deg": 30.0}
    reset_pose()
    pose_stance(two)
    pts0 = posed_points()
    for side in ("L", "R"):
        verts = np.unique(SET[f"arm_low_{side}"].used)
        row = {"side": side, "steps_cm": []}
        need = None
        for dx in [0.5 * i for i in range(0, 41)]:
            p = pts0.copy()
            p[verts, 0] += dx / 100.0
            res = MC.measure(BK, SET[f"arm_low_{side}"], p, SET["torso"], p, limit=0.005, to_report=UE)
            ok = MC.passes(res, 0.005)
            row["steps_cm"].append([dx, res["crossing_pairs_visible"], res["contained"], res["separation_m"]]
                                   + ([res["crossing_parts_visible"][:4], res["contained_parts"][:2]]
                                      if dx in (0.0, 5.0, 10.0, 15.0, 20.0) else []))
            if ok:
                need = dx
                break
        row["forward_shift_needed_cm"] = need
        if need is not None:
            tg = TP.socket_targets(two)
            arm = ARMS[side]
            a, b = (arm["elbow"] - arm["shoulder"]).length, (arm["wrist"] - arm["elbow"]).length
            reach = {}
            for s2 in ("R", "L"):
                pos, rot = tg[s2]
                pos = pos + np.array([need / 100.0, 0.0, 0.0])
                arm2 = ARMS[s2]
                _R, w = TP.hand_pose(np.array(arm2["channel"]), arm2["socket_rot"], np.array(arm2["wrist"]), pos, rot)
                a2 = (arm2["elbow"] - arm2["shoulder"]).length + (arm2["wrist"] - arm2["elbow"]).length
                reach[s2] = round(float(np.linalg.norm(w - np.array(rig.pose.bones[f"upperarm_{s2}"].head)) / a2), 4)
            row["reach_if_grips_move_forward"] = reach
            row["arm_length_needed_cm"] = {s2: round(float(((ARMS[s2]["elbow"] - ARMS[s2]["shoulder"]).length
                                                            + (ARMS[s2]["wrist"] - ARMS[s2]["elbow"]).length)
                                                           * max(1.0, reach[s2] / TP.REACH_MAX)) * 100.0, 2)
                                           for s2 in ("R", "L")}
        print("TWO_PAW_SHIFT " + json.dumps(row, default=str), flush=True)
    print("EXPLORE_COMPLETE", flush=True)
    sys.exit(0)

# --- The clips: keyed first, checked, rendered, and only then exported -------------------------------------------------
CLIPS = (("Idle", 96), ("Walk", 32), ("Guard", 96))
for clip, frames in CLIPS:
    action = bpy.data.actions.new(rig.name + "_" + clip)
    action.use_fake_user = True
    rig.animation_data.action = action
    for frame in range(1, frames + 2, 4):
        clip_pose(clip, (frame - 1) / frames * math.tau)
        for pose in rig.pose.bones:
            pose.keyframe_insert(data_path="rotation_euler", frame=frame, group=pose.name)
            pose.keyframe_insert(data_path="location", frame=frame, group=pose.name)
    actions[clip] = action


def at_frame(clip, frame):
    rig.animation_data.action = actions[clip]
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()


# --- The contract's checks on this build (THIRD_PERSON_GRIP_CONTRACT.md 4.1, 4.2, 4.5) -------------------------------
rest_pts = np.array([list(mesh.matrix_world @ v.co) for v in mesh.data.vertices])
fit = {}
for side in ("R", "L"):
    for seg in ("upperarm", "forearm", "hand"):
        b = rig.data.bones[f"{seg}_{side}"]
        h, tl = np.array(b.head_local), np.array(b.tail_local)
        q = rest_pts[group_of == f"{seg}_{side}"]
        cen = q.mean(0)
        u = (tl - h) / np.linalg.norm(tl - h)
        evals, evecs = np.linalg.eigh(np.cov((q - cen).T))
        joint_ends = {"upperarm": ("shoulder", "elbow"), "forearm": ("elbow", "wrist"), "hand": ("wrist", "channel")}[seg]
        fit[f"{seg}_{side}"] = {"vertices": int(len(q)),
                                "head_tail_from_parts_cm": [round(float(np.linalg.norm(np.array(x) - np.array(ARMS[side][j]))) * 100.0, 4)
                                                            for x, j in ((h, joint_ends[0]), (tl, joint_ends[1]))],
                                "centroid_off_bone_cm": round(float(TP.segment_distance(h, tl, cen[None])[0]) * 100.0, 2),
                                "axis_to_bone_deg": round(math.degrees(math.acos(min(1.0, abs(float(evecs[:, -1] @ u))))), 1)}
channel_rows = {}
for side in ("R", "L"):
    arm = ARMS[side]
    loc = (rest_pts[group_of == f"hand_{side}"] - np.array(arm["channel"])) @ arm["socket_rot"]
    inside = (np.abs(loc[:, 0]) <= RP.PAW_HALF) & ((loc[:, 1] / RP.CHANNEL_HALF[0]) ** 2 + (loc[:, 2] / RP.CHANNEL_HALF[1]) ** 2 < 1.0)
    channel_rows[side] = {"breadth_along_channel_cm": round(float(np.ptp(loc[:, 0])) * 100.0, 2),
                          "vertices_inside_channel": int(inside.sum())}
calibration = MC.calibrate(BK)
assert calibration["ok"], calibration
checks, gate_rows = {}, {}
for clip, frames in (("Guard", (1, 25, 49, 73)), ("Idle", (1, 49)), ("Walk", (1, 9, 17, 25))):
    for f in frames:
        at_frame(clip, f)
        set_empty(*EMPTY_BY_CLIP[clip])
        res = check_pose(SAYA_SOCKET, held=clip == "Guard")
        if clip == "Guard":
            res["socket_error_cm"] = {s: round(float(np.linalg.norm(socket_now(s)[0] - tg[0])) * 100.0, 4)
                                      for s, tg in TP.socket_targets(GUARD, math.sin((f - 1) / 96 * math.tau) * 0.004).items()}
            res["socket_error_deg"] = {s: round(TP.angle_deg(socket_now(s)[1], tg[1]), 3)
                                       for s, tg in TP.socket_targets(GUARD, math.sin((f - 1) / 96 * math.tau) * 0.004).items()}
        checks[f"{clip}@{f}"] = res
        gate_rows[f"{clip}@{f}"] = gates_of(res)
reset_pose()
rig.animation_data.action = None
set_empty(0, 0)                                           # the bind pose: no morph
bpy.context.view_layer.update()
rest_posed = posed_points()
checks["rest"] = {"forearms_paws_vs_torso": MC.measure(BK, SET["arms_low"], rest_posed, SET["torso"], rest_posed,
                                                       limit=0.02, to_report=UE),
                  "upper_arms_vs_torso": MC.measure(BK, SET["upper_arms"], rest_posed, SET["torso"], rest_posed,
                                                    limit=0.0, to_report=UE)}
gate_rows["rest"] = gates_of(checks["rest"])
socket_ok = all(max(r["socket_error_cm"].values()) <= 1.0 for k, r in checks.items() if k.startswith("Guard"))
failed = sorted(f"{k}:{g}" for k, row in gate_rows.items() for g, ok in row.items() if not ok)
failed += [f"channel_{s}" for s, row in channel_rows.items()                  # 4.2: the paw closes round the channel
           if row["vertices_inside_channel"] or row["breadth_along_channel_cm"] > TP.PAW_BREADTH_MAX_CM + 1e-3]
failed += [f"arm_fit_{k}" for k, row in fit.items() if max(row["head_tail_from_parts_cm"]) > 0.1]
if failed or not socket_ok:
    print("NYAAKOTO_RUNTIME_SKIN_CHECKS_FAILED " + json.dumps({"failed": failed, "socket_ok": socket_ok,
                                                              "channel": channel_rows, "fit": fit,
                                                              "checks": {k: brief(v) for k, v in checks.items()}},
                                                             default=str), flush=True)
    sys.stdout.flush()
    os._exit(1)                                           # nothing exported, nothing written

# --- Review renders: the guard and the sheathed carry, with the authored W00 at its sockets --------------------------
renders = {}
for clip, views in (("Guard", ("Front", "SideRight", "SideLeft")), ("Idle", ("Front", "SideLeft"))):
    at_frame(clip, 1)
    set_empty(*EMPTY_BY_CLIP[clip])
    sp, sr = saya_at(SAYA_SOCKET)
    held = socket_now("R") if clip == "Guard" else sheathed(sp, sr)
    for path in render_views(views, HERO / f"Nyaakoto_RuntimeSkin_{clip}", held, (sp, sr)):
        renders[path.name] = path
end_review()
set_empty(0, 0)                                           # exported as morph targets at 0; the runtime drives them
# Nothing imported or added for the checks and renders stays in the runtime blend.
for kind in DATA_KINDS:
    for d in [d for d in getattr(bpy.data, kind) if d not in data_before_weapons[kind] and d not in actions.values()
              and not (kind == "images" and d.type in {"RENDER_RESULT", "COMPOSITING"})]:
        getattr(bpy.data, kind).remove(d)

# --- Export: Idle on the skeletal mesh, Walk and Guard beside it ---------------------------------------------------------
# Keep the painted iris packed in the editable runtime .blend, but omit its
# image node while exporting FBX. Blender otherwise embeds the artist's
# absolute workstation path even with path_mode="STRIP".
iris_nodes = bpy.data.materials["M_Hero_BlueEye"].node_tree.nodes
iris_links = bpy.data.materials["M_Hero_BlueEye"].node_tree.links
iris_node = iris_nodes["Painted radial iris pigment"]
iris_image = iris_node.image
iris_nodes.remove(iris_node)
for clip, frames in CLIPS:
    rig.animation_data.action = actions[clip]
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = frames + 1
    bpy.context.scene.frame_set(1)
    bpy.ops.object.select_all(action="DESELECT")
    mesh.select_set(True)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    filename = {"Idle": "SK_NyaagyuSamurai.fbx", "Walk": "A_NyaagyuSamurai_Walk.fbx", "Guard": "A_NyaagyuSamurai_Guard.fbx"}[clip]
    bpy.ops.export_scene.fbx(
        filepath=str(OUT / filename), use_selection=True,
        object_types={"MESH", "ARMATURE"}, axis_forward="-Y", axis_up="Z",
        apply_unit_scale=True, add_leaf_bones=False, use_armature_deform_only=True,
        bake_anim=True, bake_anim_use_nla_strips=False,
        bake_anim_use_all_actions=False, bake_anim_simplify_factor=0,
        path_mode="STRIP", prioritize_active_color=True)
iris_node = iris_nodes.new("ShaderNodeTexImage")
iris_node.name = "Painted radial iris pigment"
iris_node.image = iris_image
iris_links.new(iris_node.outputs["Color"], iris_nodes["Principled BSDF"].inputs["Base Color"])
iris_links.new(iris_node.outputs["Color"], iris_nodes["Bump"].inputs["Height"])
rig.animation_data.action = actions["Idle"]
bpy.context.scene.frame_set(1)
runtime_blend = HERO / "Nyaakoto_RuntimeSkin.blend"
preview = HERO / "Nyaakoto_RuntimeSkin_Blender.png"
bpy.context.scene.render.engine = "CYCLES"
bpy.context.scene.cycles.samples = 32
bpy.context.scene.render.resolution_x = 1000
bpy.context.scene.render.resolution_y = 1200
bpy.context.scene.render.resolution_percentage = 100
bpy.context.scene.render.filepath = str(preview)
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(runtime_blend))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


guard_reach = {}
at_frame("Guard", 1)
for side in ("R", "L"):                                   # the reach the keyed frame-1 solve used, recomputed
    arm, pu = ARMS[side], rig.pose.bones[f"upperarm_{side}"]
    a, b = (arm["elbow"] - arm["shoulder"]).length, (arm["wrist"] - arm["elbow"]).length
    guard_reach[side] = round(float((rig.pose.bones[f"hand_{side}"].head - pu.head).length / (a + b)), 4)
rig.animation_data.action = actions["Idle"]
bpy.context.scene.frame_set(1)
sockets = {}
for side, name in (("R", "hand_r_grip"), ("L", "hand_l_grip")):
    arm = ARMS[side]
    sockets[name] = {"bone": f"hand_{side}",
                     "component_cm": [round(float(v), 4) for v in TP.blender_to_ue_point(arm["channel"])],
                     "x_axis": [round(float(v), 6) for v in TP.flip_y(arm["socket_rot"][:, 0])],
                     "z_axis": [round(float(v), 6) for v in TP.flip_y(arm["socket_rot"][:, 2])]}
saya_pos, saya_rot = TP.gear_socket_blender(SAYA_SOCKET)
sockets["gear_saya_l"] = {"bone": SAYA_SOCKET["bone"],
                          "component_cm": [round(float(v), 4) for v in TP.blender_to_ue_point(saya_pos)],
                          "x_axis": [round(float(v), 6) for v in TP.flip_y(saya_rot[:, 0])],
                          "z_axis": [round(float(v), 6) for v in TP.flip_y(saya_rot[:, 2])],
                          "rotation_deg": SAYA_SOCKET["rotation_deg"], "source": SAYA_SOCKET_SOURCE,
                          "sheathed_katana": {"grip_r_in_koiguchi_cm": [-TP.W00["sheath_seat_x"], 0.0, 0.0],
                                              "from": "the front seppa's face (machi 9.52 less the 3.2 cm habaki); "
                                                      f"{seat_ring} katana vertices lie on it"}}
corners = [mesh.matrix_world @ Vector(c) for c in mesh.bound_box]
bounds = {"min": [round(min(p[i] for p in corners), 4) for i in range(3)],
          "max": [round(max(p[i] for p in corners), 4) for i in range(3)]}
third_person = {
    "contract": "docs/art-direction/THIRD_PERSON_GRIP_CONTRACT.md",
    "frames": "Unreal component cm = 100 x (x, -y, z) of Blender metres; sides anatomical (_R the character's right)",
    "arm_joints_blender_m": {side: {k: [round(float(c), 4) for c in ARMS[side][k]] for k in ("shoulder", "elbow", "wrist", "palm", "channel")}
                             for side in ("R", "L")},
    "removed_parts": removed, "added_parts": added_names,
    "empty_paws": {"shape_keys": ["PawEmpty_R", "PawEmpty_L"], "by_clip": EMPTY_BY_CLIP,
                   "vertices": empty_keys, "channel_share": RP.EMPTY_CHANNEL,
                   "note": "1 an empty fist, 0 the paw round a hilt; the checks and renders use these values"},
    "deferred_gear": {"parts": sorted(p.name for p in deferred), "slots_only_they_use": deferred_only,
                      "note": "The bow, quiver and arrows stay on the body until their gear assets exist; the "
                              "socket migration viewmodels.json plans stays open."},
    "channel_cm": list(TP.CHANNEL_CM), "paw_breadth_max_cm": TP.PAW_BREADTH_MAX_CM, "finger_pitch_m": RP.FINGER_PITCH,
    "guard": {"stance": GUARD, "reach": guard_reach,
              "status": "interim one-paw guard; the two-paw grip and left-hand closure (4.5, 4.7) stay open"},
    "weapons": {w["file"]: {"sha256": w["sha256"], "sockets_read_back_m": w["sockets"]} for w in (KATANA, SAYA)},
    "clearance": {"method": MC.__doc__.split("\n\n", 1)[1].strip(), "backend": BK.name, "calibration": calibration,
                  "gates": {k: ("no visible crossing, nothing contained or ambiguous" +
                                (f", and at least {m * 100:.0f} cm by exact triangle separation" if m else ""))
                            for k, m in GATES.items()},
                  "reported_only": {"upper_arms_vs_torso": "rigid parts meet at the shoulder by build"},
                  "tuck": list(TUCK), "results": checks, "passed": gate_rows},
    "checks": {"arm_fit": fit, "channel": channel_rows},
    "sockets": sockets,
    "guard_explore": "Saved/W18Rebuild/s61_guard_explore.run* (the contract's first target kept with its measurements)",
    "review_renders": {n: sha(p) for n, p in renders.items()},
}

record = {
    "schema_version": 1,
    "generator": "scripts/art/rig_nyaakoto_runtime.py",
    "source_blend": str(SOURCE.relative_to(ROOT)),
    "source_blend_sha256": source_record["blend_sha256"],
    "runtime_blend": runtime_blend.name,
    "runtime_blend_sha256": sha(runtime_blend),
    "runtime_preview": preview.name,
    "runtime_preview_sha256": sha(preview),
    "source_parts": len(parts),
    "source_vertices": len(mesh.data.vertices),
    "source_triangles": source_record["source_triangles"],
    "bounds_m": bounds,
    "skeletal_fbx": "SK_NyaagyuSamurai.fbx",
    "skeletal_fbx_sha256": sha(OUT / "SK_NyaagyuSamurai.fbx"),
    "walk_fbx": "A_NyaagyuSamurai_Walk.fbx",
    "walk_fbx_sha256": sha(OUT / "A_NyaagyuSamurai_Walk.fbx"),
    "guard_fbx": "A_NyaagyuSamurai_Guard.fbx",
    "guard_fbx_sha256": sha(OUT / "A_NyaagyuSamurai_Guard.fbx"),
    "skeleton_bones": all_bones,
    "sora_kamon_svg_sha256": source_record["insignia_sha256"],
    "sora_kamon_placements": source_record["sora_kamon_placements"],
    "head_weighted_vertices": weights["head"],
    "rigging": "20-bone runtime skeleton, its arm chains fitted to the hero's arm parts and its sides anatomical; rigid source-part skin; idle, walk and an interim one-paw guard",
    "third_person": third_person,
    "limitations": "No production deformation, lip sync, authored combat animation, strand groom, UE 5.8.2 visual review, or photoreal quality qualification. The guard is an interim one-paw pose. The katana and saya are the authored W00 at sockets, not body geometry; the bow, quiver and arrows remain back presentation geometry until their gear assets exist.",
}
MANIFEST.write_text(json.dumps(record, indent=2, ensure_ascii=False, default=str) + "\n")
print("NYAAKOTO_RUNTIME_SKIN_COMPLETE", len(parts), len(mesh.data.vertices), len(rig.data.bones), weights["head"])
