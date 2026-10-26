"""A close-up preview of Nyaakoto's third-person paws (nyaakoto_tp_paws) on the hero source: each paw holding the W00
katana, and as the empty fist.

Run (Blender 5.2):
    Blender -b --factory-startup --python-exit-code 1 --python scripts/art/preview_nyaakoto_tp_paws.py --
        --out s96_tp_paws_preview --variant arm=1.2,chest=0.85 [--fur]

--fur adds nyaakoto_tp_fur's strands to each paw (LOD0's density), in the same part, so the empty fist's shape key
moves them with the skin.

**What it writes:** only Saved/W18Rebuild/<out>/, a fresh directory:
- a render per paw, state and view;
- preview.json: each paw's mesh checks and the inputs' hashes.

**How it builds the paws:**
- The hero source is opened and never saved. The variant is applied in memory, as the studies did (the production
  source gets A in its own step).
- Each paw is meshed at LOD0's step. Its empty fist is a shape key built from the same rule, set to 0, as the build
  will be; the empty renders set it to 1.
- Each paw's checks run before any render, and a failing check stops the job: a closed outward 2-manifold, no
  self-crossing in either state, nothing within the carve of the channel, and the rig's channel gate.

**What shows:** the katana is placed by its own sockets, Grip_R in the right paw and Grip_L in the left, at the bind
pose. The render scene holds only the new paw, that side's arm parts (forearm, kote, sleeve), the katana, a camera
and a sun: every collection and object of the source scene is unlinked from it first. s96 hid the other parts by
hide_render instead, and its renders still showed the body, the source's palm and the open fingers. The cause was
not traced in s96; unlinking does not depend on it.

Renders use the source's own materials (M_Hero_GreyTabbyFur, its CoatBlend blend to the white coat) under one sun and
a grey world. They are for reviewing the forms, not for photoreal acceptance.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
import time
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nyaakoto_fp_paws as FP  # noqa: E402
import nyaakoto_runtime_parts as RP  # noqa: E402
import nyaakoto_tp_fur as TPF  # noqa: E402
import nyaakoto_tp_paws as P  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT_NAME = ARGS[ARGS.index("--out") + 1]
VARIANT = dict(kv.split("=") for kv in ARGS[ARGS.index("--variant") + 1].split(",")) if "--variant" in ARGS else {}
FUR = "--fur" in ARGS
ROOT = Path(__file__).resolve().parents[2]
HERO = ROOT / "Content/SourceArt/Characters/Hero"
SOURCE = HERO / "Nyaagyu_HeroCharacter.blend"
W00 = ROOT / "Content/SourceArt/Weapons/Runtime/W00_Katana"
OUT = ROOT / "Saved/W18Rebuild" / OUT_NAME
OUT.mkdir(parents=True, exist_ok=False)
T0 = time.time()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


INPUT_SHA = {"nyaakoto_tp_paws_sha256": sha(Path(__file__).resolve().parent / "nyaakoto_tp_paws.py"),
             "nyaakoto_tp_fur_sha256": sha(Path(__file__).resolve().parent / "nyaakoto_tp_fur.py"),
             "preview_script_sha256": sha(Path(__file__))}           # at the start, before anything can change them


record = json.loads((HERO / "manifest.json").read_text())
assert sha(SOURCE) == record["blend_sha256"]
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
source = bpy.data.collections["NyaagyuHero_Editable"]
parts = sorted((o for o in source.objects if o.type == "MESH"), key=lambda o: o.name)
by_name = {o.name: o for o in parts}
variant_record = RP.apply_variant(parts, by_name, VARIANT)
ARMS = RP.arm_joints(by_name)
scene = bpy.context.scene


def palm_radii(sign):
    """The source palm's half extents along the world axes (create_nyaagyu_hero_character.sphere: axis-aligned)."""
    o = by_name[f"Paw_hand_{sign}"]
    mw = np.array([list(r) for r in o.matrix_world])
    co = np.array([v.co[:] for v in o.data.vertices]) @ mw[:3, :3].T + mw[:3, 3]
    return tuple(float(x) for x in (co.max(0) - co.min(0)) / 2.0)


def checks(side, m, empty):
    arm = ARMS[side]
    fr = m["skeleton"]["frame"]
    V, T = m["verts"], m["tris"]
    _, _, e = P.channel_coords(V, fr)
    loc = (V - np.array(arm["channel"])) @ arm["socket_rot"]
    inside = (np.abs(loc[:, 0]) <= P.PAW_HALF) & ((loc[:, 1] / P.CHANNEL_HALF[0]) ** 2 + (loc[:, 2] / P.CHANNEL_HALF[1]) ** 2 < 1.0)
    n0 = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]])
    n1 = np.cross(empty[T[:, 1]] - empty[T[:, 0]], empty[T[:, 2]] - empty[T[:, 0]])
    vol = lambda X: float(np.einsum("ij,ij->i", X[T[:, 0]], np.cross(X[T[:, 1]], X[T[:, 2]])).sum() / 6.0)  # noqa: E731
    row = {"vertices": int(len(V)), "triangles": int(len(T)), "closed_manifold": FP.is_closed_manifold(T),
           "volume_cm3": {"grip": round(vol(V) * 1e6, 2), "empty": round(vol(empty) * 1e6, 2)},
           "self_crossings": {"grip": int(len(P.self_crossings(V, T))), "empty": int(len(P.self_crossings(empty, T)))},
           "min_offset_from_channel_mm": round(float(e.min()) * 1000.0, 4),
           "vertices_inside_channel": int(inside.sum()),
           "breadth_along_channel_cm": round(float(np.ptp(loc[:, 0])) * 100.0, 3),
           "faces_turned_over_by_morph": int((np.einsum("ij,ij->i", n0, n1) <= 0.0).sum()),
           "max_morph_move_cm": round(float(np.linalg.norm(empty - V, axis=1).max()) * 100.0, 3),
           "fold_margin": round(P.fold_margin(fr), 4)}
    failed = [k for k, bad in (("closed_manifold", not row["closed_manifold"]),
                               ("volume", min(row["volume_cm3"].values()) <= 0.0),
                               ("self_crossings", any(row["self_crossings"].values())),
                               ("carve", row["min_offset_from_channel_mm"] < P.CARVE_MARGIN * 1000.0 - 0.01),
                               ("channel", row["vertices_inside_channel"] > 0),
                               ("breadth", row["breadth_along_channel_cm"] > P.PAW_HALF * 200.0 + 1e-3),
                               ("turned_over", row["faces_turned_over_by_morph"] > 0),
                               ("fold_margin", row["fold_margin"] <= 0.0)) if bad]
    row["failed"] = failed
    return row


def paw_object(side, m, empty):
    name = f"Paw_hand_fur_{side}"
    me = bpy.data.meshes.new(name)
    me.from_pydata(m["verts"].tolist(), [], m["tris"].tolist())       # the skin, then any strands
    me.update()
    assert len(me.loops) == m["tris"].size and len(me.vertices) == len(m["verts"])
    uv = me.uv_layers.new(name="UVMap")
    uv.data.foreach_set("uv", m["uvs"].reshape(-1).astype(np.float32))
    col = me.color_attributes.new(name="CoatBlend", type="BYTE_COLOR", domain="CORNER")
    rgba = np.repeat(m["coat"].reshape(-1, 1), 4, 1)
    rgba[:, 3] = 1.0
    col.data.foreach_set("color", rgba.reshape(-1).astype(np.float32))
    me.color_attributes.active_color = col
    me.materials.append(bpy.data.materials["M_Hero_GreyTabbyFur"])
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    obj = bpy.data.objects.new(name, me)
    scene.collection.objects.link(obj)
    obj.shape_key_add(name="Basis", from_mix=False)
    key = obj.shape_key_add(name=f"PawEmpty_{side}", from_mix=False)
    key.value = 0.0                                  # Blender 5.2 starts a new key at 1.0 (s90)
    key.data.foreach_set("co", empty.reshape(-1).astype(np.float32))
    assert [(kb.name, kb.value) for kb in me.shape_keys.key_blocks[1:]] == [(f"PawEmpty_{side}", 0.0)]
    return obj


def load_katana():
    path = W00 / "SM_Weapon_00.fbx"
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(path))
    new = [o for o in bpy.data.objects if o not in before]
    sockets = {o.name.split(".")[0][len("SOCKET_"):]: o for o in new if o.name.startswith("SOCKET_")}
    frames = {}
    for n, o in sockets.items():
        loc, rot, _ = o.matrix_world.decompose()
        frames[n] = Matrix.Translation(loc) @ rot.to_matrix().to_4x4()
    return {"objects": new, "imported": {o.name: o.matrix_world.copy() for o in new}, "frames": frames,
            "sha256": sha(path)}


def put_katana(k, socket, pos, rot):
    """Move the katana so its socket (Grip_R or Grip_L) sits at pos with rot (numpy 3x3)."""
    target = Matrix([[*rot[0], pos[0]], [*rot[1], pos[1]], [*rot[2], pos[2]], [0.0, 0.0, 0.0, 1.0]])
    s = target @ k["frames"][socket].inverted()
    for o in k["objects"]:
        if o.parent is None:
            o.matrix_world = s @ k["imported"][o.name]


SHOWN = ("Fur_forearm", "Kote_", "Karakuri_", "Wrist_cell_", "Linen_sleeve")
REPLACED = ("Paw_hand_",) + RP.OPEN_PAW
rows, renders = {}, []
paws, KATANA = {}, None
for side in ("R", "L"):
    arm = ARMS[side]
    radii = palm_radii(arm["sign"])
    t = time.time()
    m = P.mesh_paw(arm, radii, step=P.LOD_STEPS[0])
    empty = P.empty_points(m["verts"], m["skeleton"])
    rows[side] = dict(checks(side, m, empty), palm_radii_m=[round(r, 5) for r in radii], mesh_s=round(time.time() - t, 2),
                      channel_m=[round(float(v), 5) for v in arm["channel"]])
    if FUR:                                                            # the skin's checks above; then its strands
        sv, st, suv, scoat, pruned = TPF.grow(m, TPF.LOD_DENSITY[0])
        rows[side]["strands"] = {"count": int(len(st)), "pruned_for_crossing_the_skin": int(pruned)}
        n = len(m["verts"])
        m = dict(m, verts=np.concatenate([m["verts"], sv]), tris=np.concatenate([m["tris"], st + n]),
                 uvs=np.concatenate([m["uvs"], suv]), coat=np.concatenate([m["coat"], scoat]))
        empty = P.empty_points(m["verts"], m["skeleton"])
    print("NYAAKOTO_TP_PAW", side, json.dumps(rows[side]), flush=True)
    if rows[side]["failed"]:
        (OUT / "preview.json").write_text(json.dumps({"failed": {side: rows[side]["failed"]}, "paws": rows}, indent=2) + "\n")
        raise SystemExit(f"NYAAKOTO_TP_PAWS_PREVIEW_FAILED {side} {rows[side]['failed']}")
    paws[side] = paw_object(side, m, empty)

KATANA = load_katana()
cam = bpy.data.objects.new("Preview_Cam", bpy.data.cameras.new("Preview_Cam"))
scene.collection.objects.link(cam)
cam.data.lens = 60.0
sun = bpy.data.objects.new("Preview_Sun", bpy.data.lights.new("Preview_Sun", "SUN"))
sun.data.energy = 3.2
sun.data.angle = math.radians(6.0)
scene.collection.objects.link(sun)
scene.camera = cam
for child in list(scene.collection.children):    # the render scene holds only what is linked below
    scene.collection.children.unlink(child)
for o in list(scene.collection.objects):
    if o not in (cam, sun) and o not in paws.values():
        scene.collection.objects.unlink(o)
for o in KATANA["objects"]:
    if o.name not in scene.collection.objects:
        scene.collection.objects.link(o)
world = bpy.data.worlds.new("Preview_World")
scene.world = world
if not world.node_tree:
    world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs["Color"].default_value = (0.42, 0.43, 0.45, 1.0)
bg.inputs["Strength"].default_value = 0.55
scene.render.engine = "CYCLES"
scene.cycles.samples = 40
scene.cycles.use_denoising = True
scene.render.threads_mode = "FIXED"
scene.render.threads = 8                         # the host is shared; leave the other cores to the other jobs
scene.render.resolution_x = scene.render.resolution_y = 860
scene.render.resolution_percentage = 100


def views(sign):
    out = sign * 1.0                             # the paw's outer (little-finger) side is world +-Y
    return {"FrontOuter": Vector((1.0, 0.55 * out, 0.35)), "FrontLow": Vector((0.9, 0.2 * out, -0.6)),
            "Outer": Vector((0.15, 1.0 * out, 0.2)), "BackTop": Vector((-0.6, 0.3 * out, 0.9)),
            "Inner": Vector((0.25, -1.0 * out, 0.1))}


for side in ("R", "L"):
    arm = ARMS[side]
    sign = arm["sign"]
    shown = []
    for o in source.all_objects:
        if o.type == "MESH" and o.name.startswith(SHOWN) and not o.name.startswith(REPLACED) and o.data.vertices:
            at = o.matrix_world @ Vector(np.mean([v.co[:] for v in o.data.vertices[:64]], 0).tolist())
            if RP.rig_bone(o.name, at).endswith(f"_{side}"):
                scene.collection.objects.link(o)
                shown.append(o)
    print("NYAAKOTO_TP_PAW_SHOWN", side, sorted(o.name for o in shown), flush=True)
    for s2, obj in paws.items():
        obj.hide_render = s2 != side
    put_katana(KATANA, "Grip_R" if side == "R" else "Grip_L", np.array(arm["channel"]), arm["socket_rot"])
    centre = Vector(np.array(arm["channel"]).tolist()) + Vector((0.0, 0.0, 0.02))
    key = paws[side].data.shape_keys.key_blocks[f"PawEmpty_{side}"]
    for state, value, with_katana in (("Grip", 0.0, True), ("Empty", 1.0, False)):
        key.value = value
        for o in KATANA["objects"]:
            o.hide_render = not with_katana
        for view, d in views(sign).items():
            d = d.normalized()
            cam.location = centre + d * 0.40
            cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
            sun.rotation_euler = (-(d * 0.5) - Vector((0.2, 0.0, 0.85))).normalized().to_track_quat("-Z", "Y").to_euler()
            path = OUT / f"Paw_{side}_{state}_{view}.png"
            scene.render.filepath = str(path)
            t = time.time()
            bpy.ops.render.render(write_still=True)
            renders.append({"file": path.name, "side": side, "state": state, "view": view,
                            "render_s": round(time.time() - t, 1)})
            print("NYAAKOTO_TP_PAW_RENDER", path.name, flush=True)
    key.value = 0.0
    rows[side]["render_scene"] = sorted(o.name for o in scene.objects if o.type == "MESH" and not o.hide_render)
    for o in shown:
        scene.collection.objects.unlink(o)

summary = {
    "schema": 1,
    "generator": "scripts/art/preview_nyaakoto_tp_paws.py",
    "args": ARGS,
    "inputs": dict(INPUT_SHA, hero_blend_sha256=record["blend_sha256"], w00_katana_fbx_sha256=KATANA["sha256"]),
    "variant": variant_record,
    "lod0_step_m": P.LOD_STEPS[0],
    "paws": rows,
    "renders": renders,
    "elapsed_s": round(time.time() - T0, 1),
    "claims": "Form review renders of the paws on the source materials; not a visual, photoreal or runtime acceptance.",
}
(OUT / "preview.json").write_text(json.dumps(summary, indent=2) + "\n")
print("NYAAKOTO_TP_PAWS_PREVIEW_COMPLETE", len(renders), flush=True)
