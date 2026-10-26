"""The runtime body's part rules, shared by rig_nyaakoto_runtime.py (LOD0) and generate_nyaakoto_lods.py (LOD1/2), so
every LOD carries the same body (docs/art-direction/THIRD_PERSON_GRIP_CONTRACT.md, slice A).

- **Bones by anatomical side:** _R is the character's right, Blender -Y.
- **Parts that leave the body:**
  - the sheathed sword set (Saya_, Sageo_, Katana_); the runtime carries the authored W00 saya and katana at sockets;
  - the source's open paw: its palm, fingers and thumb (Paw_hand_, Finger_, Thumb_).
- **What replaces the open paws:** one furred paw per side, closed round the grip channel (nyaakoto_tp_paws, built
  here as a Blender part by fur_paw). Every LOD meshes its own at its own step, and every LOD's empty fist comes from
  the same rule. The curled tubes and narrowed palm that came first (slice A) read as white tubes in root's 05:15 UTC
  review (2026-10-26) and are gone.
- **The arm joints** come from the hero's own arm parts; the source palm, though it leaves the body, still sets the
  channel and the paw's palm.

**What stays for now:** the bow, quiver and arrows (Ebira_, Ya_, Yumi_). viewmodels.json moves them to gear sockets,
but their gear assets do not exist yet. Removing them now would drop their material slots. That socket migration
stays open.
"""
from __future__ import annotations

import math

import bpy
import numpy as np
from mathutils import Vector

import nyaakoto_fp_paws as FP
import nyaakoto_tp_fur as TPF
import nyaakoto_tp_paws as TPP
import third_person_rig as TP

SWORD_SET = ("Saya_", "Sageo_", "Katana_")
OPEN_PAW = ("Finger_", "Thumb_")                   # the source's open fingers, knuckles, claws and thumb
PALM = ("Paw_hand_",)                              # the source's palm; arm_joints still measures it
REMOVED = SWORD_SET + OPEN_PAW + PALM
FRESH = ("PawFur_",)                               # parts made here, not copied from the source
FUR_PAW_MATERIAL = "M_Hero_GreyTabbyFur"           # its CoatBlend blends to the white coat (import_nyaakoto_pbr.py)
DEFERRED_GEAR = ("Ebira_", "Ya_", "Yumi_")         # still on the body: the socket migration waits for its assets
PAW_HALF = TP.PAW_BREADTH_MAX_CM / 200.0           # m: the closed paw's half breadth along its channel
CHANNEL_HALF = (TP.CHANNEL_CM[0] / 200.0, TP.CHANNEL_CM[1] / 200.0)   # m: across (Y_s), deep (Z_s)
CHANNEL_DIR = Vector((0.589, 0.0, -0.808)).normalized()   # from the palm's centre to the channel: down and forward
# m: how far the channel's palm side sits inside the palm's surface. Negative is clear of it. At +3 mm (the first
# build) the palm's triangles crossed the W00 tsuka in 28 pairs while no palm vertex lay inside the channel
# (Saved/W18Rebuild/s62_sliceA_explore). The palm is convex and its facets lie inside its vertices' surface, so
# 0.5 mm clear keeps the tsuka off it.
CHANNEL_EMBED = -0.0005


def kept(name):
    return not name.startswith(REMOVED)


def rig_bone(name: str, world_position: Vector) -> str:
    """The bone a source (or curled) part's vertex follows: rigid per part, sides anatomical."""
    if name.startswith("UserSupplied_SORAKamon_sode_") or name.startswith("Sode_kamon_backing_"):
        return "upperarm_R" if "_-1" in name else "upperarm_L"
    if name.startswith("UserSupplied_SORAKamon_waist"):
        return "pelvis"
    if name.startswith("UserSupplied_SORAKamon_chest"):
        return "spine"
    if name.startswith(("Skull", "Head_", "Lower_jaw", "Ear_", "Cheek_", "Muzzle_", "Eye_", "Vertical_pupil", "Corneal_", "Angular_", "Whisker_", "Tiger_", "Guard_hair_", "Soft_nose", "White_nose", "Forehead_", "Triangular_nose", "Philtrum", "Mouth_")):
        return "head"
    if name.startswith(("Fur_neck", "White_throat")):
        return "neck"
    if name.startswith("Tail_"):
        return "tail_01" if world_position.x > -.34 else "tail_02" if world_position.x > -.49 else "tail_03"
    if name.startswith(("Saya_", "Sageo_", "Katana_", "Obi_", "Resistance_sash", "Clan_mon", "Layered_hakama")):
        return "pelvis"
    if name.startswith(("Ebira_", "Ya_", "Yumi_", "Resistance_insignia", "Linen_under", "Indigo_samurai", "Under_kimono", "Do_")):
        return "spine"
    side = "R" if world_position.y < 0 else "L"          # Blender -Y is the character's right
    if name.startswith(("Hakama_upper_leg", "Hakama_fold")):
        return f"thigh_{side}"
    if name.startswith(("Hakama_shin", "Kyahan_", "Greave_")):
        return f"shin_{side}"
    if name.startswith(("Heel_", "Tabi_", "Toe_", "Claw_")):
        return f"foot_{side}"
    if name.startswith(("Shoulder_", "Linen_sleeve", "Sode_")):
        return f"upperarm_{side}"
    if name.startswith(("Fur_forearm", "Kote_", "Karakuri_", "Wrist_cell_")):
        return f"forearm_{side}"
    if name.startswith(("Paw_hand", "Finger_", "Thumb_", "PawFur_")):
        return f"hand_{side}"
    raise ValueError(f"Unclassified Nyaakoto part: {name}")


def cone_ends(obj):
    """create_nyaagyu_hero_character.bone(): a cone along its local Z from a (-depth/2) to b (+depth/2), centred."""
    zs = [v.co.z for v in obj.data.vertices]
    half = (max(zs) - min(zs)) / 2.0
    axis = (obj.matrix_world.to_3x3() @ Vector((0.0, 0.0, 1.0))).normalized()
    c = obj.matrix_world.translation
    return c - axis * half, c + axis * half


def arm_joints(by_name):
    """Per side: the shoulder (Shoulder_joint's centre), the elbow and wrist (Fur_forearm's ends), the palm's centre,
    the grip channel's centre, and the grip socket's rotation at bind (numpy columns X, Y, Z)."""
    arms = {}
    for side, sign in (("R", -1), ("L", 1)):
        shoulder = by_name[f"Shoulder_joint_{sign}"].matrix_world.translation.copy()
        a, b = cone_ends(by_name[f"Fur_forearm_{sign}"])
        elbow, wrist = (a, b) if a.z > b.z else (b, a)
        palm = by_name[f"Paw_hand_{sign}"]
        centre = palm.matrix_world.translation.copy()
        xs, zs = [v.co.x for v in palm.data.vertices], [v.co.z for v in palm.data.vertices]
        rx, rz = (max(xs) - min(xs)) / 2.0, (max(zs) - min(zs)) / 2.0
        surface = 1.0 / math.sqrt((CHANNEL_DIR.x / rx) ** 2 + (CHANNEL_DIR.z / rz) ** 2)
        channel = centre + CHANNEL_DIR * (surface + CHANNEL_HALF[1] - CHANNEL_EMBED)
        x_s = Vector((0.0, -float(sign), 0.0))           # along the channel, little finger to thumb: inboard
        z_s = (centre - channel).normalized()            # to the back of the paw (the mune side)
        arms[side] = {"sign": sign, "shoulder": shoulder, "elbow": elbow, "wrist": wrist, "palm": centre,
                      "channel": channel, "socket_rot": TP.frame(np.array(x_s), np.array(z_s))}
    return arms


CHEST_FRONT = ("Indigo_samurai_haori", "Linen_under_kimono", "Under_kimono_cross_collar", "Do_",
               "UserSupplied_SORAKamon_chest", "Resistance_insignia")
KAMON = "UserSupplied_SORAKamon_"
# The parts that ride with each kamon placement: its two exact SVG paths and the lacquered disc behind them.
KAMON_BACKING = {"Resistance_insignia_backing": "chest", "Sode_kamon_backing_-1": "sode_-1",
                 "Sode_kamon_backing_1": "sode_1"}


def kamon_group(name):
    """The kamon placement a part rides with ("chest", "waist", "sode_-1", "sode_1"), or None."""
    if name.startswith(KAMON):
        return name[len(KAMON):].rsplit("_Path_", 1)[0]
    return KAMON_BACKING.get(name)


def apply_variant(parts, by_name, variant):
    """An anatomy and armour study variant, applied in memory to the source parts (never saved over the source):
    - arm: stretch each upper arm along its shoulder-to-elbow axis about the shoulder, and each forearm along its
      elbow-to-wrist axis about the moved elbow. The paw moves with the wrist; the shoulder ball stays rigid.
    - palm: scale the palm (Paw_hand) about its centre; the channel and the paw built on it follow it.
    - chest: bring the front half (x > 0) of the haori, kimono, collar, dō, chest kamon and insignia toward the body,
      x scaled about 0.
    Each part's origin moves with its vertices. The joints are measured from the origins (arm_joints, cone_ends), so
    a first version that moved only the vertices left them behind (Saved/W18Rebuild/s73_twopaw_v01).
    Each SORA kamon, with its backing, moves rigidly by its centre's displacement (kamon_group). The user-supplied
    paths stay exact: the arm's stretch would otherwise have stretched the sode kamon along the upper arm, and the
    validators check every path vertex against the SVG to 0.02 mm. Returns what moved, and each kamon's displacement,
    for the record."""
    arm, palm, chest = (float(variant.get(k, 1.0)) for k in ("arm", "palm", "chest"))
    if arm == palm == chest == 1.0:
        return {}
    joints = {side: (by_name[f"Shoulder_joint_{sign}"].matrix_world.translation.copy(),
                     *sorted(cone_ends(by_name[f"Fur_forearm_{sign}"]), key=lambda q: -q.z)) for side, sign in (("R", -1), ("L", 1))}

    def deform(name, p):
        q = p.copy()
        seg, _, side = rig_bone(name, p).partition("_")
        if arm != 1.0 and seg in ("upperarm", "forearm", "hand"):
            s_, e_, w_ = joints[side]
            u, f = (e_ - s_).normalized(), (w_ - e_).normalized()
            e2 = e_ + (arm - 1.0) * (e_ - s_).length * u
            w2 = w_ + (e2 - e_) + (arm - 1.0) * (w_ - e_).length * f
            if seg == "upperarm":
                if not name.startswith("Shoulder_joint"):
                    q = p + (arm - 1.0) * max(0.0, (p - s_).dot(u)) * u
            elif seg == "forearm":
                q = p + (e2 - e_) + (arm - 1.0) * max(0.0, (p - e_).dot(f)) * f
            else:
                q = p + (w2 - w_)
        if chest != 1.0 and name.startswith(CHEST_FRONT) and q.x > 0.0:
            q.x *= chest
        return q

    centres = {}
    for obj in parts:
        g = kamon_group(obj.name)
        if g is not None and obj.name.startswith(KAMON):
            centres.setdefault(g, []).extend(obj.matrix_world @ v.co for v in obj.data.vertices)
    rigid = {}
    for g, pts in centres.items():
        c = Vector([(min(p[i] for p in pts) + max(p[i] for p in pts)) / 2.0 for i in range(3)])
        rigid[g] = deform(f"{KAMON}{g}_Path_0", c) - c
    moved = 0
    for obj in parts:
        mw = obj.matrix_world.copy()
        old = [mw @ v.co for v in obj.data.vertices]
        g = kamon_group(obj.name)
        if g is not None:
            new = [p + rigid[g] for p in old]
            origin = mw.translation + rigid[g]
        else:
            new = [deform(obj.name, p) for p in old]
            origin = deform(obj.name, mw.translation.copy())
        if palm != 1.0 and obj.name.startswith("Paw_hand_"):
            new = [origin + (q - origin) * palm for q in new]
        if (origin - mw.translation).length < 1e-9 and all((a - b).length < 1e-9 for a, b in zip(old, new)):
            continue
        m2 = mw.copy()
        m2.translation = origin
        obj.matrix_world = m2
        inv = m2.inverted()
        for v, q in zip(obj.data.vertices, new):
            v.co = inv @ q
        obj.data.update()
        moved += 1
    bpy.context.view_layer.update()
    return {"arm": arm, "palm": palm, "chest": chest, "parts_moved": moved,
            "kamon_moved_m": {g: [float(x) for x in d] for g, d in sorted(rigid.items())}}


def palm_radii(by_name, sign):
    """The source palm's half extents along the world axes (create_nyaagyu_hero_character.sphere is axis-aligned)."""
    o = by_name[f"Paw_hand_{sign}"]
    mw = np.array([list(r) for r in o.matrix_world])
    co = np.empty(len(o.data.vertices) * 3, np.float32)
    o.data.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3).astype(np.float64) @ mw[:3, :3].T + mw[:3, 3]
    return tuple(float(x) for x in (co.max(0) - co.min(0)) / 2.0)


def fur_paw(side, arms, by_name, step=TPP.LOD_STEPS[0], strands=TPF.LOD_DENSITY[0]):
    """The furred paw for one side as an unlinked Blender part, PawFur_{sign}: its skin (nyaakoto_tp_paws) and its fur
    strands (nyaakoto_tp_fur, this share of LOD0's density), its vertices in world metres (identity transform), the
    UVMap and CoatBlend per corner, M_Hero_GreyTabbyFur, smooth shading. Returns the object and the mesh: the skin's
    own arrays under "skin_*", the whole part's under verts and tris (its skeleton gives the empty fist)."""
    arm = arms[side]
    sign = arm["sign"]
    m = TPP.mesh_paw(arm, palm_radii(by_name, sign), step=step)
    m["palm_radii"] = palm_radii(by_name, sign)
    sv, st, suv, scoat, pruned = TPF.grow(m, strands)
    n = len(m["verts"])
    m.update(skin_verts=m["verts"], skin_tris=m["tris"], strands=int(len(st)), strands_pruned=int(pruned),
             strand_share=strands, verts=np.concatenate([m["verts"], sv]), tris=np.concatenate([m["tris"], st + n]),
             uvs=np.concatenate([m["uvs"], suv]), coat=np.concatenate([m["coat"], scoat]))
    name = f"PawFur_{sign}"
    me = bpy.data.meshes.new(name)
    me.from_pydata(m["verts"].tolist(), [], m["tris"].tolist())
    me.update()
    assert len(me.vertices) == len(m["verts"]) and len(me.loops) == m["tris"].size
    uv = me.uv_layers.new(name="UVMap")
    uv.data.foreach_set("uv", m["uvs"].reshape(-1).astype(np.float32))
    col = me.color_attributes.new(name="CoatBlend", type="BYTE_COLOR", domain="CORNER")
    rgba = np.repeat(m["coat"].reshape(-1, 1), 4, 1)
    rgba[:, 3] = 1.0
    col.data.foreach_set("color", rgba.reshape(-1).astype(np.float32))
    me.color_attributes.active_color = col
    me.materials.append(bpy.data.materials[FUR_PAW_MATERIAL])
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    obj = bpy.data.objects.new(name, me)
    obj["provenance"] = "scripts/art/nyaakoto_tp_paws.py (mesh_paw) on the hero source's arm joints and palm"
    return obj, m


def fur_paw_record(side, arms, m):
    """The paw's own checks, both states. The skin: a closed outward 2-manifold, no self-crossing, nothing within the
    carve of the channel, no face turned over by the empty fist, and the closure's fold margin. The whole part, its
    strands with it: no vertex inside the channel, the breadth along it (the rig's 4.2 gate), and no strand crossing
    the skin. "failed" names any that fail."""
    arm = arms[side]
    V, T = m["skin_verts"], m["skin_tris"]
    A = m["verts"]
    E = TPP.empty_points(V, m["skeleton"])
    _, _, e = TPP.channel_coords(V, m["skeleton"]["frame"])
    loc = (A - np.array([float(v) for v in arm["channel"]])) @ np.asarray(arm["socket_rot"])
    inside = (np.abs(loc[:, 0]) <= PAW_HALF) & ((loc[:, 1] / CHANNEL_HALF[0]) ** 2 + (loc[:, 2] / CHANNEL_HALF[1]) ** 2 < 1.0)
    n0 = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]])
    n1 = np.cross(E[T[:, 1]] - E[T[:, 0]], E[T[:, 2]] - E[T[:, 0]])

    def volume(X):
        return float(np.einsum("ij,ij->i", X[T[:, 0]], np.cross(X[T[:, 1]], X[T[:, 2]])).sum() / 6.0)

    fr = m["skeleton"]["frame"]
    sv, st = A[len(V):], m["tris"][len(T):] - len(V)
    strand_x = {state: int(len(TPF.skin_crossing_strands(
        V if state == "grip" else E, T, sv if state == "grip" else TPP.empty_points(sv, m["skeleton"]), st)))
        for state in ("grip", "empty")}
    row = {"step_m": m["step"], "vertices": int(len(A)), "triangles": int(len(m["tris"])),
           "skin": {"vertices": int(len(V)), "triangles": int(len(T))},
           "strands": {"count": int(len(st)), "share_of_lod0": m["strand_share"], "pruned": m["strands_pruned"],
                       "crossing_the_skin": strand_x},
           "palm_radii_m": [float(r) for r in m["palm_radii"]],
           "frame": {k: ([float(x) for x in v] if isinstance(v, np.ndarray) else v) for k, v in fr.items()},
           "closed_manifold": FP.is_closed_manifold(T),
           "volume_cm3": {"grip": round(volume(V) * 1e6, 2), "empty": round(volume(E) * 1e6, 2)},
           "self_crossings": {"grip": int(len(TPP.self_crossings(V, T))), "empty": int(len(TPP.self_crossings(E, T)))},
           "min_offset_from_channel_mm": round(float(e.min()) * 1000.0, 4),
           "vertices_inside_channel": int(inside.sum()),
           "breadth_along_channel_cm": round(float(np.ptp(loc[:, 0])) * 100.0, 3),
           "faces_turned_over_by_morph": int((np.einsum("ij,ij->i", n0, n1) <= 0.0).sum()),
           "max_morph_move_cm": round(float(np.linalg.norm(E - V, axis=1).max()) * 100.0, 3),
           "fold_margin": round(TPP.fold_margin(m["skeleton"]["frame"]), 4)}
    row["failed"] = [k for k, bad in (("closed_manifold", not row["closed_manifold"]),
                                      ("volume", min(row["volume_cm3"].values()) <= 0.0),
                                      ("self_crossings", any(row["self_crossings"].values())),
                                      ("carve", row["min_offset_from_channel_mm"] < TPP.CARVE_MARGIN * 1000.0 - 0.01),
                                      ("channel", row["vertices_inside_channel"] > 0),
                                      ("breadth", row["breadth_along_channel_cm"] > TP.PAW_BREADTH_MAX_CM + 1e-3),
                                      ("turned_over", row["faces_turned_over_by_morph"] > 0),
                                      ("strands", any(strand_x.values())),
                                      ("fold_margin", row["fold_margin"] <= 0.0)) if bad]
    return row
