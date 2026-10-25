"""Build Nyaakoto's first-person bow paw (SM_NyaakotoFP_PawL_Yumi) and review it on the real yumi.

Run (Blender 5.2, by the holder of the shared engine lane):
  blender -b --factory-startup --python-exit-code 1 --python scripts/art/create_nyaakoto_fp_paws.py -- \
      [--step 0.0009] [--samples 64] [--no-review]

The geometry comes from numpy: nyaakoto_fp_paws.py (skin, regions, fur cards)
and nyaakoto_fp_kote.py (the kote). This driver turns it into one static
mesh, in the Grip_L socket frame (bow metres, +X forward, +Y the wielder's
left, +Z up). The viewmodel attaches it to the imported socket and it
inherits the weapon's 0.75 scale. Its material slots:

- **M_NyaakotoFP_FurSkin:** the skin between the cards. The hero's white fur
  maps, box-projected and tinted by the tabby vertex colour.
- **M_NyaakotoFP_PawPad:** the bare pads, with the paw-pad PBR set.
- **M_NyaakotoFP_FurCards:** hair clumps from the fur atlas
  (create_nyaakoto_fp_fur_textures.py), alpha-cut and two-sided, coloured
  by the per-card tabby vertex colour.
- **M_NyaakotoFP_KoteSilk:** the hero's indigo silk.
- **M_NyaakotoFP_KoteUrushi:** indigo-black lacquered splints and the mon
  plate.
- **M_NyaakotoFP_CordVermilion:** two-ply silk cord.
- **M_NyaakotoFP_MonGold:** the pinned SORA mon (SM_SoraKamon), never
  redrawn, scaled to the plate.

Writes to Content/SourceArt/Characters/NyaakotoFirstPersonPaws/Production/:
- SM_NyaakotoFP_PawL_Yumi.fbx;
- Nyaakoto_FP_PawL_Yumi.blend, the editable source;
- build_record.json, with inputs, counts and fit checks against the bow;
- Renders/: Cycles review originals on SK_Weapon_18 at full draw, with the
  arrow nocked.

Review originals only. Not imported, admitted or a photoreal claim.
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

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import create_runtime_weapon_lib as L  # noqa: E402
import nyaakoto_fp_kote as K  # noqa: E402
import nyaakoto_fp_paws as P  # noqa: E402

GEN = "scripts/art/create_nyaakoto_fp_paws.py"
OUT = ROOT / "Content/SourceArt/Characters/NyaakotoFirstPersonPaws/Production"
FUR_TEX = ROOT / "Content/SourceArt/Characters/NyaakotoFirstPersonPaws/FurCards"
PAD_TEX = ROOT / "Content/SourceArt/Characters/NyaakotoFirstPersonPaws/Textures"
HERO_PBR = ROOT / "Content/SourceArt/Characters/Hero/PBR"
KAMON = ROOT / "Content/SourceArt/UI/SoraKamonMon/SM_SoraKamon.fbx"
RIG_FBX = ROOT / "Content/SourceArt/Weapons/Runtime/W18_Yumi/Rig/SK_Weapon_18.fbx"
ARROW_FBX = ROOT / "Content/SourceArt/Weapons/Runtime/W18_Yumi/SM_Weapon_18_Ya.fbx"
W18 = ROOT / "Content/SourceArt/Weapons/Runtime/W18_Yumi"
NAME = "SM_NyaakotoFP_PawL_Yumi"
SILK_INDIGO = (0.016, 0.023, 0.045)          # create_nyaakoto_pbr_textures.py "IndigoSilk", the hero's kimono
RIG_RECORD = ROOT / "Content/SourceArt/Weapons/Runtime/W18_Yumi/Rig/rig_record.json"


def args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = {"step": 0.0009, "samples": 64, "review": True}
    if "--step" in argv:
        out["step"] = float(argv[argv.index("--step") + 1])
    if "--samples" in argv:
        out["samples"] = int(argv[argv.index("--samples") + 1])
    if "--no-review" in argv:
        out["review"] = False
    return out


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return Path(path).resolve().relative_to(ROOT).as_posix()


# --- Meshes -------------------------------------------------------------------------

def make_mesh(name, verts, tris, uv=None, colour=None, mat_index=None, smooth=True, normals=None):
    """A mesh object from numpy arrays: from_pydata (robust across Blender
    versions), then per-loop UV0, per-point colour, per-face slots and, when
    given, per-vertex custom normals."""
    me = bpy.data.meshes.new(name)
    tris = np.asarray(tris, np.int64)
    me.from_pydata(np.asarray(verts, np.float64).tolist(), [], tris.tolist())
    me.validate(clean_customdata=False)
    if mat_index is not None:
        me.polygons.foreach_set("material_index", np.asarray(mat_index, np.int32))
    if uv is not None:
        layer = me.uv_layers.new(name="UV0")
        layer.data.foreach_set("uv", np.asarray(uv, np.float32)[tris.ravel()].ravel())
    if colour is not None:
        col = me.color_attributes.new(name="Col", type="BYTE_COLOR", domain="POINT")
        rgba = np.concatenate([np.asarray(colour, np.float32), np.ones((len(verts), 1), np.float32)], 1)
        col.data.foreach_set("color", rgba.ravel())
    if smooth:
        me.shade_smooth()
    if normals is not None:
        # Per-vertex custom normals (Mesh.normals_split_custom_set_from_vertices, as Blender 5.2's own glTF
        # importer sets them). The FBX exporter then writes corner normals (export_fbx_bin: normals_domain).
        me.normals_split_custom_set_from_vertices(np.asarray(normals, np.float64).tolist())
    me.update()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    return obj


# --- Materials (create_runtime_weapon_lib.NB: the Mix node's colour sockets, DX normals) -------

def vcol(nb):
    return nb.node("ShaderNodeVertexColor", layer_name="Col").outputs["Color"]


def mat_fur_skin():
    nb = L.NB("M_NyaakotoFP_FurSkin")
    box = nb.vmul(nb.obj(), 9.0)
    alb = nb.img(HERO_PBR / "T_Nyaakoto_fur_white_Albedo.png", box, "sRGB", box=True, blend=0.3)
    nrm = nb.img(HERO_PBR / "T_Nyaakoto_fur_white_NormalDX.png", nb.vmul(nb.uv("UV0"), 6.0), "Non-Color")
    # The undercoat between clumps. v3: 0.62 -> 0.82. A white cat's undercoat is
    # nearly as light as its guard hair; at 0.62 every gap read as a grey fleck
    # (root's review of Saved/YumiFP/v2: "flecked/flat white fur clumps").
    under = nb.mulc(nb.mulc(alb.outputs["Color"], vcol(nb)), (0.82, 0.80, 0.78))
    nb.feed(nb.bsdf.inputs["Base Color"], under)
    nb.feed(nb.bsdf.inputs["Normal"], nb.nmap_dx(nrm.outputs["Color"], 0.6, uv_map="UV0"))
    nb.feed(nb.bsdf.inputs["Roughness"], 0.78)
    nb.feed(nb.bsdf.inputs["Sheen Weight"], 0.5)
    nb.feed(nb.bsdf.inputs["Sheen Roughness"], 0.35)
    return nb.mat


def mat_pad():
    nb = L.NB("M_NyaakotoFP_PawPad")
    uv = nb.vmul(nb.uv("UV0"), 4.0)
    alb = nb.img(PAD_TEX / "T_Nyaakoto_PawPad_Albedo.png", uv, "sRGB")
    nrm = nb.img(PAD_TEX / "T_Nyaakoto_PawPad_NormalDX.png", uv, "Non-Color")
    orm = nb.img(PAD_TEX / "T_Nyaakoto_PawPad_ORM.png", uv, "Non-Color")
    nb.feed(nb.bsdf.inputs["Base Color"], alb.outputs["Color"])
    nb.feed(nb.bsdf.inputs["Roughness"], nb.sep(orm.outputs["Color"])[1])
    nb.feed(nb.bsdf.inputs["Normal"], nb.nmap_dx(nrm.outputs["Color"], 0.7, uv_map="UV0"))
    nb.feed(nb.bsdf.inputs["Subsurface Weight"], 0.25)
    nb.feed(nb.bsdf.inputs["Subsurface Radius"], (0.004, 0.0015, 0.0012))
    return nb.mat


def mat_fur_cards():
    nb = L.NB("M_NyaakotoFP_FurCards")
    uv = nb.uv("UV0")
    alb = nb.img(FUR_TEX / "T_NyaakotoFP_FurCards_Albedo.png", uv, "sRGB")
    nrm = nb.img(FUR_TEX / "T_NyaakotoFP_FurCards_NormalDX.png", uv, "Non-Color")
    msk = nb.img(FUR_TEX / "T_NyaakotoFP_FurCards_Masks.png", uv, "Non-Color")
    root, rand, _depth = nb.sep(msk.outputs["Color"])
    ao = nb.remap(root, 0.0, 0.6, 0.70, 1.0)                   # v3: 0.42 -> 0.70, so a card's root no longer reads as a dark flake
    tint = nb.mulc(alb.outputs["Color"], vcol(nb))
    nb.feed(nb.bsdf.inputs["Base Color"], nb.mixc(nb.one_minus(ao), tint, (0.0, 0.0, 0.0)))
    nb.feed(nb.bsdf.inputs["Alpha"], alb.outputs["Alpha"])
    nb.feed(nb.bsdf.inputs["Roughness"], nb.remap(rand, 0.0, 1.0, 0.50, 0.70))   # v3: from 0.38-0.62
    nb.feed(nb.bsdf.inputs["Normal"], nb.nmap_dx(nrm.outputs["Color"], 0.8, uv_map="UV0"))
    nb.feed(nb.bsdf.inputs["Sheen Weight"], 0.35)
    nb.feed(nb.bsdf.inputs["Subsurface Weight"], 0.12)
    nb.feed(nb.bsdf.inputs["Subsurface Radius"], (0.0025, 0.002, 0.0016))
    nb.mat.use_backface_culling = False
    return nb.mat


def mat_silk():
    nb = L.NB("M_NyaakotoFP_KoteSilk")
    uv = nb.vmul(nb.uv("UV0"), 3.0)
    alb = nb.img(HERO_PBR / "T_Nyaakoto_silk_indigo_Albedo.png", uv, "sRGB")
    nrm = nb.img(HERO_PBR / "T_Nyaakoto_silk_indigo_NormalDX.png", uv, "Non-Color")
    orm = nb.img(HERO_PBR / "T_Nyaakoto_silk_indigo_ORM.png", uv, "Non-Color")
    # The hero's own indigo (create_nyaakoto_pbr_textures.py "IndigoSilk") on
    # the undyed weave. v1's (0.42, 0.48, 0.80) and its pale sheen read white.
    nb.feed(nb.bsdf.inputs["Base Color"], nb.mulc(alb.outputs["Color"], SILK_INDIGO))
    # v3 (root: "broad glossy blue cloth"): a little rougher, and a weaker sheen.
    nb.feed(nb.bsdf.inputs["Roughness"], nb.m("MINIMUM", nb.mul(nb.sep(orm.outputs["Color"])[1], 1.15), 1.0))
    nb.feed(nb.bsdf.inputs["Normal"], nb.nmap_dx(nrm.outputs["Color"], 0.8, uv_map="UV0"))
    nb.feed(nb.bsdf.inputs["Sheen Weight"], 0.25)
    nb.feed(nb.bsdf.inputs["Sheen Tint"], (0.35, 0.42, 0.70, 1.0))
    return nb.mat


def mat_urushi():
    nb = L.NB("M_NyaakotoFP_KoteUrushi")
    # v3: one lobe at 0.25, as Unreal draws it. The coat (0.65 at 0.10) can't be
    # set from Unreal's Python (CustomData0/1 are hidden), and at Unreal's
    # defaults (1.0 at 0.1) it gave the splints mirror highlights (root's
    # review of Saved/YumiFP/v2). The two builds now match.
    nb.feed(nb.bsdf.inputs["Base Color"], (0.010, 0.013, 0.030))
    nb.feed(nb.bsdf.inputs["Roughness"], 0.25)
    return nb.mat


def mat_cord():
    nb = L.NB("M_NyaakotoFP_CordVermilion")
    nb.feed(nb.bsdf.inputs["Base Color"], (0.42, 0.035, 0.022))
    nb.feed(nb.bsdf.inputs["Roughness"], 0.52)
    nb.feed(nb.bsdf.inputs["Sheen Weight"], 0.7)
    nb.feed(nb.bsdf.inputs["Sheen Tint"], (1.0, 0.45, 0.35, 1.0))
    return nb.mat


def mat_gold():
    nb = L.NB("M_NyaakotoFP_MonGold")
    nb.feed(nb.bsdf.inputs["Base Color"], (1.0, 0.77, 0.36))
    nb.feed(nb.bsdf.inputs["Metallic"], 1.0)
    nb.feed(nb.bsdf.inputs["Roughness"], 0.24)
    return nb.mat


# --- Build --------------------------------------------------------------------------------

def place_mon(mon, mat):
    """Import the pinned SORA mon, scale its 1 m disc to the plate, face it outward."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(KAMON), axis_forward="-Y", axis_up="Z", global_scale=1.0)
    new = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    if len(new) != 1:
        raise RuntimeError(f"fp paws: expected the one SM_SoraKamon mesh, got {[o.name for o in new]}")
    o = new[0]
    bpy.context.view_layer.objects.active = o
    o.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    x = Vector(mon["normal"]).normalized()          # the mark faces +X; its legs are down (-Z)
    z = Vector(mon["up"]).normalized()
    z = (z - x * z.dot(x)).normalized()
    y = z.cross(x)
    R = Matrix((x, y, z)).transposed().to_4x4()
    s = mon["diameter"]                              # the disc is 1 m across
    o.matrix_world = Matrix.Translation(Vector(mon["centre"])) @ R @ Matrix.Diagonal((s, s, s, 1.0))
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    o.data.materials.clear()
    o.data.materials.append(mat)
    o.name = "Kote_SoraMon"
    o.select_set(False)
    return o


def build(step):
    t0 = time.time()
    m = P.mesh_bow_paw(step=step, smooth=6)
    skel = m["skeleton"]

    def field(p):
        return P.paw_sdf(p, skel)[0]
    fur = P.fur_cards(m, field)
    parts, mon = K.bow_kote(skel)
    t1 = time.time()
    mats = {"skin": mat_fur_skin(), "pad": mat_pad(), "fur": mat_fur_cards(), "M_NyaakotoFP_KoteSilk": mat_silk(),
            "M_NyaakotoFP_KoteUrushi": mat_urushi(), "M_NyaakotoFP_CordVermilion": mat_cord(), "gold": mat_gold()}
    is_pad = np.array([str(r).startswith("pad") for r in m["region"]])
    tri_pad = is_pad[m["tris"]].sum(1) >= 2
    skin_col = P.tabby_colour(m["verts"], skel)
    skin = make_mesh("PawL_Skin", m["verts"], m["tris"], colour=skin_col, mat_index=tri_pad.astype(np.int32))
    skin.data.materials.append(mats["skin"])
    skin.data.materials.append(mats["pad"])
    bpy.context.view_layer.objects.active = skin
    skin.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(island_margin=0.01)
    bpy.ops.object.mode_set(mode="OBJECT")
    skin.data.uv_layers.active.name = "UV0"
    skin.select_set(False)
    cards = make_mesh("PawL_FurCards", fur["verts"], fur["tris"], uv=fur["uv"], colour=fur["colour"],
                      normals=fur["normals"])
    cards.data.materials.append(mats["fur"])
    kote = []
    for part in parts:
        o = make_mesh(part["name"], part["verts"], part["tris"], uv=part["uv"])
        o.data.materials.append(mats[part["material"]])
        kote.append(o)
    mon_obj = place_mon(mon, mats["gold"])
    objs = [skin, cards] + kote + [mon_obj]
    info = {"skin_triangles": int(len(m["tris"])), "fur_cards": int(fur["cards"]), "fur_card_triangles": int(len(fur["tris"])),
            "kote_parts": len(parts), "kote_triangles": int(sum(len(p["tris"]) for p in parts)),
            "mon_triangles": len(mon_obj.data.polygons), "build_s": round(t1 - t0, 1),
            "fur_skin_normal_weight": P.FUR["skin_normal"]}
    return m, fur, parts, objs, info


def card_normal_angles(verts, tris, normals):
    """Each card corner's normal against its triangle's face, in degrees, skipping degenerate triangles (cut
    strands): v4's bent normals sit a few degrees off their faces, where a recomputed normal sits on them."""
    face = np.cross(verts[tris[:, 1]] - verts[tris[:, 0]], verts[tris[:, 2]] - verts[tris[:, 0]])
    area = np.linalg.norm(face, axis=1)
    live = area > 1e-14
    unit = face[live] / area[live, None]
    cos = np.concatenate([np.einsum("ij,ij->i", unit, normals[tris[live, c]]) for c in range(3)])
    return np.degrees(np.arccos(np.clip(cos, -1.0, 1.0)))


def angle_stats(deg):
    return {"mean": round(float(deg.mean()), 3), "p90": round(float(np.percentile(deg, 90)), 3),
            "max": round(float(deg.max()), 3), "corners": int(deg.size)}


def checks(m, fur, parts):
    """Fit against the bow and the checker's design envelope; closure of every solid part; the cards' fronts
    and shading normals (v4)."""
    skel = m["skeleton"]
    V = m["verts"]
    g = P.grip_sdf(V)
    tips = P.grip_sdf(fur["tips"])
    FV, FT, K = fur["verts"], fur["tris"], P.FUR["segments"]
    face = np.cross(FV[FT[:, 1]] - FV[FT[:, 0]], FV[FT[:, 2]] - FV[FT[:, 0]])
    area = np.linalg.norm(face, axis=1)
    live = area > 1e-14
    card = (np.arange(len(FT)) % (fur["cards"] * K)) // K
    front = np.einsum("ij,ij->i", face[live] / area[live, None], fur["root_normals"][card[live]])
    skin = np.repeat(fur["root_normals"], 2 * (K + 1), axis=0)
    bent = np.degrees(np.arccos(np.clip(np.einsum("ij,ij->i", fur["normals"], skin), -1.0, 1.0)))
    env = P.round_cone(V, np.array((-0.004, 0.0, -0.055)), np.array((-0.004, 0.0, 0.062)), 0.036, 0.036)
    out = {
        "skin_closed": P.is_closed_manifold(m["tris"]),
        "skin_min_clearance_mm": round(float(g.min()) * 1e3, 3),
        "skin_contact_vertices": int((g < 0.0005).sum()),
        "fur_tips_inside_bow": int((tips < 0.0).sum()),
        "kote_parts_closed": all(P.is_closed_manifold(p["tris"]) for p in parts),
        "kote_min_clearance_mm": round(min(float(P.grip_sdf(p["verts"]).min()) for p in parts) * 1e3, 2),
        "skin_outside_paw_l_envelope_share": round(float((env > 0).mean()), 4),
        "dewclaw_tip_below_arrow_mm": round((P.ARROW_PASS[2] - P.ARROW_SHAFT_R - float(
            skel["chains"]["I"][0][-1][2] + skel["chains"]["I"][1][-1])) * 1e3, 2),
        "fur_live_triangle_share": round(float(live.mean()), 5),
        "fur_front_min_cos_to_skin": round(float(front.min()), 4),
        "fur_shading_normal_max_deg_from_skin": round(float(bent.max()), 3),
        "fur_corner_normal_from_face_deg": angle_stats(card_normal_angles(FV, FT, fur["normals"])),
    }
    out["ok"] = (out["skin_closed"] and out["skin_min_clearance_mm"] >= 0.1 and out["fur_tips_inside_bow"] == 0
                 and out["kote_parts_closed"] and out["kote_min_clearance_mm"] > 0
                 and out["fur_front_min_cos_to_skin"] > 0 and out["fur_shading_normal_max_deg_from_skin"] <= 20.0)
    return out


def fbx_card_normals(path, slot="M_NyaakotoFP_FurCards"):
    """The exported FBX's fur-card corners, re-imported with their custom normals: each corner normal's angle from
    its triangle's face, as checks() measured it on the built arrays and the Unreal readback measures it."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(path), use_custom_normals=True, use_image_search=False)
    new = [o for o in bpy.data.objects if o not in before]
    try:
        obj = next(o for o in new if o.type == "MESH")
        me = obj.data
        fur = [i for i, s in enumerate(obj.material_slots) if s.material and s.material.name.split(".")[0] == slot]
        if len(fur) != 1:
            raise SystemExit(f"fp paws: the re-imported FBX has {len(fur)} {slot} slots")
        n_poly, n_loop = len(me.polygons), len(me.loops)
        mat = np.empty(n_poly, np.int32)
        me.polygons.foreach_get("material_index", mat)
        total = np.empty(n_poly, np.int32)
        me.polygons.foreach_get("loop_total", total)
        if (total != 3).any():
            raise SystemExit("fp paws: the re-imported FBX is not all triangles")
        pn = np.empty(n_poly * 3)
        me.polygon_normals.foreach_get("vector", pn)
        cn = np.empty(n_loop * 3)
        me.corner_normals.foreach_get("vector", cn)
        sel = mat == fur[0]
        pn, cn = pn.reshape(-1, 3)[sel], cn.reshape(-1, 3, 3)[sel]
        live = np.linalg.norm(pn, axis=1) > 0.5
        cos = np.einsum("ij,ikj->ik", pn[live], cn[live]).ravel()
        return angle_stats(np.degrees(np.arccos(np.clip(cos, -1.0, 1.0))))
    finally:
        for o in new:
            data = o.data if o.type == "MESH" else None
            bpy.data.objects.remove(o, do_unlink=True)
            if data is not None and data.users == 0:
                bpy.data.meshes.remove(data)


def export(objs, path):
    bpy.ops.object.select_all(action="DESELECT")
    dup = []
    for o in objs:
        c = o.copy()
        c.data = o.data.copy()
        bpy.context.scene.collection.objects.link(c)
        dup.append(c)
    for c in dup:
        # Every part carries custom normals into the join, its own where it had none, so the fur cards' survive
        # it beside parts that never had any.
        if not c.data.has_custom_normals:
            cn = np.empty(len(c.data.loops) * 3)
            c.data.corner_normals.foreach_get("vector", cn)
            c.data.normals_split_custom_set(cn.reshape(-1, 3).tolist())
        c.select_set(True)
    bpy.context.view_layer.objects.active = dup[0]
    bpy.ops.object.join()
    joined = bpy.context.view_layer.objects.active
    joined.name = NAME
    joined.data.name = NAME
    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, object_types={"MESH"},
                             apply_unit_scale=True, apply_scale_options="FBX_SCALE_NONE", global_scale=1.0,
                             axis_forward="-Y", axis_up="Z", mesh_smooth_type="FACE", use_tspace=True,
                             use_triangles=True, use_mesh_modifiers=False, colors_type="SRGB",
                             add_leaf_bones=False, bake_anim=False, path_mode="STRIP")
    slots = [s.material.name for s in joined.material_slots]
    tris = len(joined.data.polygons)
    # The exported bounds in the socket frame, so the Unreal import can be held
    # to them: Unreal = 100 x (x, -y, z) cm, as for the bow.
    mw = joined.matrix_world
    co = [mw @ v.co for v in joined.data.vertices]
    bounds = {"min": [round(min(c[i] for c in co), 7) for i in range(3)],
              "max": [round(max(c[i] for c in co), 7) for i in range(3)]}
    bpy.data.objects.remove(joined, do_unlink=True)
    return slots, tris, bounds


# --- Review -------------------------------------------------------------------------------

def w18_material():
    nb = L.NB("M_W18_Review")
    tc = nb.node("ShaderNodeTexCoord").outputs["UV"]
    alb = nb.img(W18 / "T_Weapon_18_BaseColor.png", tc, "sRGB")
    orm = nb.img(W18 / "T_Weapon_18_ORM.png", tc, "Non-Color")
    nrm = nb.img(W18 / "T_Weapon_18_NormalDX.png", tc, "Non-Color")
    nb.feed(nb.bsdf.inputs["Base Color"], alb.outputs["Color"])
    nb.feed(nb.bsdf.inputs["Alpha"], alb.outputs["Alpha"])
    _ao, rough, metal = nb.sep(orm.outputs["Color"])
    nb.feed(nb.bsdf.inputs["Roughness"], rough)
    nb.feed(nb.bsdf.inputs["Metallic"], metal)
    r, g, b = nb.sep(nrm.outputs["Color"])
    comb = nb.node("ShaderNodeCombineColor")
    nb.feed(comb.inputs[0], r)
    nb.feed(comb.inputs[1], nb.one_minus(g))
    nb.feed(comb.inputs[2], b)
    nm = nb.node("ShaderNodeNormalMap", space="TANGENT")
    nb.link(comb.outputs[0], nm.inputs["Color"])
    nb.feed(nb.bsdf.inputs["Normal"], nm.outputs["Normal"])
    return nb.mat


def rig_socket(arm, name):
    """A rig socket's world point at the current frame, in metres: its mesh-frame
    point through its bone's skinning matrix. The rig's FBX is in centimetres, so
    the imported armature carries 0.01 (render_yumi_rig_review.socket_world)."""
    s = json.loads(RIG_RECORD.read_text())["sockets"][name]
    ea = arm.evaluated_get(bpy.context.evaluated_depsgraph_get())
    pb, b = ea.pose.bones[s["bone"]], arm.data.bones[s["bone"]]
    unit = ea.matrix_world.to_scale()[0]
    return ea.matrix_world @ (pb.matrix @ b.matrix_local.inverted() @ (Vector(s["mesh_frame_m"]) / unit))


def review(objs, samples):
    scene = bpy.context.scene
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(RIG_FBX), axis_forward="-Y", axis_up="Z", global_scale=1.0,
                             use_custom_normals=True, use_image_search=False, automatic_bone_orientation=False,
                             anim_offset=0.0)
    bpy.ops.import_scene.fbx(filepath=str(ARROW_FBX), axis_forward="-Y", axis_up="Z", global_scale=1.0,
                             use_custom_normals=True, use_image_search=False)
    new = [o for o in bpy.data.objects if o not in before]
    arms = [o for o in new if o.type == "ARMATURE"]
    if len(arms) != 1:
        raise SystemExit(f"fp paws: expected the rig's one armature, got {[o.name for o in arms]}")
    rig_arm = arms[0]
    wmat = w18_material()
    arrow = None
    for o in new:
        if o.type == "MESH":
            o.data.materials.clear()
            o.data.materials.append(wmat)
            if "Ya" in o.name:
                arrow = o
    scene.frame_set(10)                                          # full draw
    if arrow is not None:
        # Nocked at the delivered rig's posed Grip_R (String_Nock, the apex of the
        # string's bend) and laid through the Muzzle, as the bow review and the
        # runtime do. v1 hardcoded the model's sharp V, 3.4 mm off (root's review).
        nock, muzzle = rig_socket(rig_arm, "Grip_R"), rig_socket(rig_arm, "Muzzle")
        x = (muzzle - nock).normalized()
        y = Vector((0, 0, 1)).cross(x).normalized()
        z = x.cross(y)
        arrow.matrix_world = Matrix.Translation(nock) @ Matrix((x, y, z)).transposed().to_4x4()
        print("FP_PAWS_ARROW", json.dumps({"nock_m": [round(c, 7) for c in nock],
                                           "muzzle_m": [round(c, 7) for c in muzzle]}), flush=True)
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Base Contrast"
    world = bpy.data.worlds.new("Review")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.20, 0.21, 0.23, 1.0)
    bg.inputs["Strength"].default_value = 0.55
    for name, loc, energy, size, colour in (("Key", (-0.55, -0.45, 0.65), 55.0, 0.45, (1.0, 0.95, 0.88)),
                                            ("Fill", (-0.10, 0.70, 0.25), 14.0, 0.8, (0.82, 0.88, 1.0)),
                                            ("Rim", (0.55, 0.25, 0.45), 40.0, 0.25, (1.0, 0.97, 0.92))):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy, ld.size, ld.color = energy, size, colour
        lo = bpy.data.objects.new(name, ld)
        scene.collection.objects.link(lo)
        lo.location = loc
        d = Vector((0, 0, 0.01)) - lo.location
        lo.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam_data = bpy.data.cameras.new("ReviewCam")
    cam = bpy.data.objects.new("ReviewCam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam_data.sensor_fit = "HORIZONTAL"
    cam_data.clip_start = 0.01
    views = {
        # the first-person eye at the A4 bow.drawn anchor (60, -6, -14) cm at mesh scale 0.75; FP FOV 70 degrees
        "FirstPerson": dict(loc=(-0.80, -0.08, 0.187), target=(0.2, -0.08, 0.187), fov=70.0, res=(1920, 1080)),
        "ArcherClose": dict(loc=(-0.30, -0.06, 0.09), target=(-0.03, 0.02, 0.0), fov=44.0, res=(1600, 1200)),
        "LeftSide": dict(loc=(-0.08, 0.36, 0.03), target=(-0.06, 0.0, -0.01), fov=50.0, res=(1600, 1200)),
        "FurMacro": dict(loc=(-0.13, 0.12, 0.10), target=(-0.035, 0.02, 0.02), fov=30.0, res=(1600, 1200)),
    }
    files = []
    (OUT / "Renders").mkdir(parents=True, exist_ok=True)
    for name, v in views.items():
        cam.location = Vector(v["loc"])
        cam.rotation_euler = (Vector(v["target"]) - cam.location).to_track_quat("-Z", "Y").to_euler()
        cam_data.angle = math.radians(v["fov"])
        scene.render.resolution_x, scene.render.resolution_y = v["res"]
        path = OUT / "Renders" / f"{NAME}_{name}.png"
        scene.render.filepath = str(path)
        t = time.time()
        bpy.ops.render.render(write_still=True)
        files.append({"file": rel(path), "sha256": sha256(path), "seconds": round(time.time() - t, 1)})
        print("FP_PAWS_RENDER", rel(path), files[-1]["seconds"], flush=True)
    return files


def main():
    a = args()
    t0 = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    OUT.mkdir(parents=True, exist_ok=True)
    m, fur, parts, objs, info = build(a["step"])
    print("FP_PAWS_BUILT", json.dumps(info), flush=True)
    chk = checks(m, fur, parts)
    print("FP_PAWS_CHECKS", json.dumps(chk), flush=True)
    if not chk["ok"]:
        raise SystemExit(f"fp paws: checks failed {chk}")
    fbx = OUT / f"{NAME}.fbx"
    slots, tris, bounds = export(objs, fbx)
    print("FP_PAWS_EXPORTED", rel(fbx), tris, "triangles", slots, flush=True)
    # The FBX carries the built normals: re-imported, the card corners sit off their faces as the arrays do.
    trip = fbx_card_normals(fbx)
    built = chk["fur_corner_normal_from_face_deg"]
    chk["fbx_round_trip_fur_corner_normal_from_face_deg"] = trip
    print("FP_PAWS_FBX_NORMALS", json.dumps({"built": built, "fbx": trip}), flush=True)
    if abs(trip["mean"] - built["mean"]) > 0.5:
        raise SystemExit(f"fp paws: the FBX's card normals ({trip}) are not the built ones ({built})")
    renders = review(objs, a["samples"]) if a["review"] else []
    blend = OUT / "Nyaakoto_FP_PawL_Yumi.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend), compress=True)
    inputs = [HERE / "nyaakoto_fp_paws.py", HERE / "nyaakoto_fp_kote.py", FUR_TEX / "manifest.json", KAMON, RIG_FBX,
              RIG_RECORD, ARROW_FBX] + sorted(FUR_TEX.glob("T_*.png")) + sorted(PAD_TEX.glob("T_*.png")) + \
        [HERO_PBR / f"T_Nyaakoto_{s}_{c}.png" for s in ("fur_white", "silk_indigo") for c in ("Albedo", "NormalDX")] + \
        [HERO_PBR / "T_Nyaakoto_silk_indigo_ORM.png"]
    record = {
        "schema_version": 1, "asset": NAME, "generator": GEN, "generator_sha256": sha256(ROOT / GEN),
        "inputs": {rel(p): sha256(p) for p in inputs}, "versions": {"blender": bpy.app.version_string},
        "frame": "Grip_L socket: bow metres, +X forward, +Y the wielder's left, +Z up; attaches to the imported "
                 "Grip_L with the weapon's 0.75 scale",
        "step_m": a["step"], "counts": dict(info, export_triangles=tris), "material_slots": slots, "checks": chk,
        "bounds_m": bounds,
        "exports": {rel(fbx): {"sha256": sha256(fbx), "bytes": fbx.stat().st_size},
                    rel(blend): {"sha256": sha256(blend), "bytes": blend.stat().st_size}},
        "renders": renders,
        "scope": "source asset and Blender review originals; not imported, admitted, rigged for motion or a "
                 "photoreal claim. Fur is cards on a skin (first-person and Mac target), not strands.",
    }
    (OUT / "build_record.json").write_text(json.dumps(record, indent=1) + "\n")
    print("FP_PAWS_READY", rel(fbx), f"{time.time() - t0:.1f}s", flush=True)


if __name__ == "__main__":
    main()
