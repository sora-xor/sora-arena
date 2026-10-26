"""The r4 candidate's skeletal FBX: Nyaakoto's runtime mesh with only its paw skins replaced by prepare_nyaakoto_r4_paws.py's
cut skins, built in memory from the runtime blend. Nothing is saved: the blend, the production FBXs and the LODs are
not written.

**Inputs, by hash:**
- the runtime blend (runtime_skin_manifest.json's runtime_blend_sha256, opened on the command line);
- the preparation's record and its two .npz files.

**What changes, per paw** (the hand_X vertices, a contiguous block: the skin, then its strands, 3 vertices each):
- **The block is checked against the preparation.** Its skin must be the preparation's baseline skin in world metres
  (matrix_world @ local), and its faces the same triangles, corners and order. Its strands must be the built strands.
- **The skin's faces are deleted; its vertices stay.** New vertices go on baseline edges at the cut's parameter, from
  the blend's own coordinates. The cut's faces are added in its order, with:
  - material index 9 (M_Hero_GreyTabbyFur) or 17 (M_Hero_RoseNose for pads), smooth;
  - UVMap per corner: the periodic map;
  - CoatBlend per corner: the coat rule. Written as the build writes it (ByteColorAttributeValue.color, linear in),
    and checked byte for byte against the old skin at baseline vertices.
- **Old edges the cut split** are removed; every other old edge is used by a new face.
- **Each new vertex:**
  - the hand_X group alone, at 1.0;
  - shape keys: Basis at its position, PawEmpty_X at empty_points (the preparation's, at the same point), and the other
    paw's key at its position.
- **The strands** keep everything but UVMap, which takes the cut skin's UV at each root.
- **Faces are ordered** as the mesh had them, with the cut's faces at the end, right paw first. BMesh refills deleted
  faces' slots, so every face is tagged and sorted before the mesh is written. The tags are checked and removed.

**Normals** stay as authored (Unreal imports them for this candidate):
- **The cut skin takes the old normals:**
  - at a baseline vertex, its parent face's old corner normal there;
  - at a new vertex, the normalised interpolation of the parent face's old corner normals at its edge's ends.
  So its shading is the uncut surface's, and only UVs and pads differ. Blender's own normal at a new vertex would be
  the bisector of its two faces' normals: 2.3 deg from the interpolation at the median, and up to 12.2 deg.
- **Encoding them leaves every other corner as stored.** normals_split_custom_set re-encodes every corner and averages
  each fan, and s140 saw that move 9% of the kept corners by up to 0.238 deg. So the kept corners' stored codes (the
  INT16 smooth-fan custom_normal attribute) are written back after it. The mesh is then rebuilt through BMesh, so its
  normals come from the stored codes.
- **Read back:** kept corners against their original normals (KEPT_NORMAL_TOL_DEG), and the cut skin against its wanted
  normals (CUT_NORMAL_TOL_DEG, the INT16 encoding of each fan).
- **Angles** are taken in float64 as atan2(|a x b|, a . b), with component differences beside them. s137 normalised
  float32 vectors and took arccos. That reads two equal unit vectors as up to about 0.024 deg apart, and s137 stopped
  on it. Its failure is kept as it was.

**Exports**, with rig_nyaakoto_runtime.py's SK settings: the idle action, frames 1-97, the shape keys at 0, and the
iris image node removed, as the build removes it.
- **A control:** the unmodified mesh, before any change. The host compares it with the production SK FBX
  (check_nyaakoto_r4_fbx.py), so that the export settings are verified.
- **The candidate.**

Writes <out>/SK_NyaagyuSamurai_control.fbx, SK_NyaagyuSamurai_R4Paws.fbx and record.json (a new folder).

Run (lane holder):
  Blender -b --factory-startup --python-exit-code 1 Content/SourceArt/Characters/Hero/Nyaakoto_RuntimeSkin.blend \\
      --python scripts/art/assemble_nyaakoto_r4_paws.py -- <prep folder> <new out folder>
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
import time
from pathlib import Path

import bmesh
import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
HERO = ROOT / "Content/SourceArt/Characters/Hero"
MARKER = "NYAAKOTO_R4_ASSEMBLED"
MESH, RIG = "SK_NyaagyuSamurai", "RIG_NyaagyuSamurai"
FUR_SLOT, PAD_SLOT = "M_Hero_GreyTabbyFur", "M_Hero_RoseNose"
KEYS = ("Basis", "PawEmpty_R", "PawEmpty_L")
IDLE_FRAMES = 96                      # rig_nyaakoto_runtime.CLIPS: the SK FBX bakes the idle over frames 1..97
POSITION_TOL_M = 2e-6                 # the blend's float32 paw against the host's rebuild, in world metres
KEPT_NORMAL_TOL_DEG = 1e-6           # kept corners: their own codes restored, so their normals are the old ones
CUT_NORMAL_TOL_DEG = 0.05             # the cut skin: INT16 smooth-fan encoding of each fan's wanted normal
EXPORT = dict(use_selection=True, object_types={"MESH", "ARMATURE"}, axis_forward="-Y", axis_up="Z",
              apply_unit_scale=True, add_leaf_bones=False, use_armature_deform_only=True,
              bake_anim=True, bake_anim_use_nla_strips=False, bake_anim_use_all_actions=False,
              bake_anim_simplify_factor=0, path_mode="STRIP", prioritize_active_color=True)


def fail(message):
    raise RuntimeError("nyaakoto r4 assembly: " + message)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def angle_deg(a, b):
    """Degrees between row vectors, in float64 as atan2(|a x b|, a . b). s137 normalised float32 vectors and took
    arccos, which reads two equal unit vectors as up to about 0.024 deg apart (a dot of 1 - 8.6e-8); it stopped on that."""
    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    return np.degrees(np.arctan2(np.linalg.norm(np.cross(a, b), axis=1), (a * b).sum(1)))


def read(me):
    """The mesh's arrays: positions, loops, faces, materials, keys, UVs, colours (sRGB bytes) and corner normals."""
    nv, nf, nl = len(me.vertices), len(me.polygons), len(me.loops)
    out = {}
    co = np.empty(nv * 3, np.float32)
    me.vertices.foreach_get("co", co)
    out["co"] = co.reshape(-1, 3)
    for name, n, dtype, coll in (("loop_start", nf, np.int32, me.polygons), ("loop_total", nf, np.int32, me.polygons),
                                 ("material_index", nf, np.int32, me.polygons), ("vertex_index", nl, np.int32, me.loops)):
        a = np.empty(n, dtype)
        coll.foreach_get(name, a)
        out[name] = a
    out["keys"] = {}
    for kb in me.shape_keys.key_blocks:
        k = np.empty(nv * 3, np.float32)
        kb.data.foreach_get("co", k)
        out["keys"][kb.name] = k.reshape(-1, 3)
    uv = np.empty(nl * 2, np.float32)
    me.uv_layers["UVMap"].data.foreach_get("uv", uv)
    out["uv"] = uv.reshape(-1, 2)
    col = np.empty(nl * 4, np.float32)
    me.color_attributes["CoatBlend"].data.foreach_get("color_srgb", col)
    out["coat_bytes"] = np.round(col.reshape(-1, 4) * 255.0).astype(np.int32)
    cn = np.empty(nl * 3, np.float32)
    me.corner_normals.foreach_get("vector", cn)
    out["normals"] = cn.reshape(-1, 3)
    smooth = np.empty(nf, bool)
    me.polygons.foreach_get("use_smooth", smooth)
    out["smooth"] = smooth
    return out


def canon(t):
    """Triangles from their smallest vertex, winding kept: the same face whichever corner a file starts it at."""
    k = np.argmin(t, 1)
    return np.stack([t[np.arange(len(t)), (k + j) % 3] for j in range(3)], 1)


def read_codes(me):
    """The raw custom-normal codes per corner (the INT16_2D smooth-fan attribute)."""
    a = me.attributes.get("custom_normal")
    if a is None or a.data_type != "INT16_2D" or a.domain != "CORNER":
        fail(f"custom_normal is {None if a is None else (a.data_type, a.domain)}, not INT16_2D per corner")
    out = np.empty(len(me.loops) * 2, np.int16)
    try:
        a.data.foreach_get("value", out)
    except (TypeError, RuntimeError):
        out = np.array([tuple(x.value) for x in a.data], np.int16).ravel()
    return out.reshape(-1, 2)


def write_codes(me, codes):
    a = me.attributes["custom_normal"]
    flat = np.ascontiguousarray(codes, np.int16).ravel()
    try:
        a.data.foreach_set("value", flat)
    except (TypeError, RuntimeError):
        for i, c in enumerate(codes.tolist()):
            a.data[i].value = c
    me.update()


def sharp_edges(me):
    if "sharp_edge" not in me.attributes:
        return 0
    a = np.zeros(len(me.edges), bool)
    me.attributes["sharp_edge"].data.foreach_get("value", a)
    return int(a.sum())


def groups_of(me):
    return [[(e.group, e.weight) for e in v.groups] for v in me.vertices]


def export(path, obj, rig):
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, IDLE_FRAMES + 1
    scene.frame_set(1)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    if not (obj.select_get() and rig.select_get()):
        fail("the mesh and the rig could not be selected for export")
    bpy.ops.export_scene.fbx(filepath=str(path), **EXPORT)
    if not path.is_file():
        fail(f"{path.name} was not written")
    return sha256(path)


def main():
    t0 = time.time()
    args = sys.argv[sys.argv.index("--") + 1:]
    prep_dir, out = (ROOT / args[0]).resolve(), (ROOT / args[1]).resolve()
    blend = Path(bpy.data.filepath).resolve()
    manifest = json.loads((HERO / "runtime_skin_manifest.json").read_text())
    prep = json.loads((prep_dir / "record.json").read_text())
    if blend != (HERO / "Nyaakoto_RuntimeSkin.blend").resolve():
        fail(f"opened {blend}, not the runtime blend")
    if sha256(blend) != manifest["runtime_blend_sha256"] or prep["inputs"]["runtime_blend_sha256"] != manifest["runtime_blend_sha256"]:
        fail("the runtime blend is not the one the manifest and the preparation name")
    if prep["inputs"]["runtime_skin_manifest"] != sha256(HERO / "runtime_skin_manifest.json"):
        fail("the runtime manifest changed since the preparation")
    for name, digest in prep["files"].items():
        if sha256(prep_dir / name) != digest:
            fail(f"{name} is not the preparation's")
    if out.exists() or not out.is_relative_to(ROOT / "Saved/NyaakotoThirdPerson/Candidates/r4"):
        fail(f"the output must be a new folder under Saved/NyaakotoThirdPerson/Candidates/r4: {out}")
    out.mkdir(parents=True)
    obj, rig = bpy.data.objects[MESH], bpy.data.objects[RIG]
    me = obj.data
    mats = [m.name if m else None for m in me.materials]
    FUR, PAD = mats.index(FUR_SLOT), mats.index(PAD_SLOT)
    if (FUR, PAD) != (9, 17) or len(mats) != 23:
        fail(f"the slots are {mats}")
    if tuple(kb.name for kb in me.shape_keys.key_blocks) != KEYS:
        fail(f"the shape keys are {[kb.name for kb in me.shape_keys.key_blocks]}")
    if any(kb.value != 0.0 for kb in me.shape_keys.key_blocks[1:]):
        fail("the empty-fist keys are not at 0")
    action = rig.animation_data.action if rig.animation_data else None
    if action is None or "Idle" not in action.name:
        fail(f"the rig's action is {action.name if action else None}, not the idle")
    record = {"inputs": {"runtime_blend": str(blend.relative_to(ROOT)), "runtime_blend_sha256": manifest["runtime_blend_sha256"],
                         "prep_record": sha256(prep_dir / "record.json"), "prep_files": prep["files"],
                         "scripts/art/assemble_nyaakoto_r4_paws.py": sha256(__file__)},
              "blender": bpy.app.version_string, "object": {"matrix_world": [list(r) for r in obj.matrix_world],
                                                            "modifiers": [(m.name, m.type) for m in obj.modifiers],
                                                            "parent": obj.parent.name if obj.parent else None,
                                                            "parent_type": obj.parent_type},
              "action": action.name, "slots": mats, "paws": {}}
    mw = np.array([list(r) for r in obj.matrix_world], float)
    inv = np.linalg.inv(mw)
    # --- The control export, before any change -------------------------------------------------------------------------
    iris_nodes = bpy.data.materials["M_Hero_BlueEye"].node_tree.nodes
    iris = iris_nodes.get("Painted radial iris pigment")
    if iris is None:
        fail("the iris image node is missing")
    iris_nodes.remove(iris)                              # as the build's export does; the blend is never saved
    record["control"] = {"file": "SK_NyaagyuSamurai_control.fbx",
                         "sha256": export(out / "SK_NyaagyuSamurai_control.fbx", obj, rig)}
    # --- The mesh as built -------------------------------------------------------------------------------------------
    before = read(me)
    codes_before = read_codes(me)
    groups = groups_of(me)
    nv, nf, nl = len(me.vertices), len(me.polygons), len(me.loops)
    world = before["co"].astype(np.float64) @ mw[:3, :3].T + mw[:3, 3]
    record["basis_equals_positions"] = bool(np.array_equal(before["keys"]["Basis"], before["co"]))
    gi = {g.name: g.index for g in obj.vertex_groups}
    ls, lt, lv = before["loop_start"], before["loop_total"], before["vertex_index"]
    sharp = np.zeros(len(me.edges), bool)
    if "sharp_edge" in me.attributes:
        me.attributes["sharp_edge"].data.foreach_get("value", sharp)
    edge_v = np.empty(len(me.edges) * 2, np.int32)
    me.edges.foreach_get("vertices", edge_v)
    edge_v = edge_v.reshape(-1, 2)
    paws = {}
    for side in ("R", "L"):
        g = gi[f"hand_{side}"]
        idx = np.array([i for i, m in enumerate(groups) if any(gg == g and w > 0.5 for gg, w in m)], np.int64)
        d = {k: v for k, v in np.load(prep_dir / f"paw_{side}.npz", allow_pickle=False).items()}
        n, s3 = len(d["skin_verts"]), len(d["strand_verts"])
        off = int(idx[0])
        if len(idx) != n + s3 or not np.array_equal(idx, np.arange(off, off + n + s3)):
            fail(f"hand_{side}'s vertices are not one block of the skin ({n}) and strands ({s3})")
        if any(groups[i] != [(g, 1.0)] for i in idx):
            fail(f"a hand_{side} vertex has another group or weight")
        err_skin = float(np.abs(world[off:off + n] - d["skin_verts"]).max())
        err_strand = float(np.abs(world[off + n:off + n + s3] - d["strand_verts"]).max())
        if max(err_skin, err_strand) > POSITION_TOL_M:
            fail(f"paw {side}: the blend's skin is {err_skin} m and strands {err_strand} m from the preparation's")
        corner_in = lambda lo, hi: (lv >= lo) & (lv < hi)  # noqa: E731
        n_skin = np.add.reduceat(corner_in(off, off + n).astype(np.int32), ls)
        skin_faces = np.flatnonzero(n_skin == lt)
        if ((n_skin > 0) & (n_skin < lt)).any():
            fail(f"paw {side}: a face mixes skin and other vertices")
        if (lt[skin_faces] != 3).any():
            fail(f"paw {side}: a skin face is not a triangle")
        tri = lv[ls[skin_faces][:, None] + np.arange(3)] - off
        if not np.array_equal(canon(tri), canon(d["skin_tris"])):
            fail(f"paw {side}: the skin's faces are not the preparation's baseline triangles in order")
        n_str = np.add.reduceat(corner_in(off + n, off + n + s3).astype(np.int32), ls)
        strand_faces = np.flatnonzero(n_str == lt)
        st = lv[ls[strand_faces][:, None] + np.arange(3)] - off - n
        if (lt[strand_faces] != 3).any() or not np.array_equal(canon(st), np.arange(s3).reshape(-1, 3)):
            fail(f"paw {side}: the strands are not (3k, 3k+1, 3k+2) in order")
        mat = before["material_index"][skin_faces]
        if set(np.unique(mat)) - {FUR, PAD} or int((mat == PAD).sum()) != prep["paws"][side]["baseline"]["pad_faces"]:
            fail(f"paw {side}: the skin's pads are not the record's")
        loops = (ls[skin_faces][:, None] + np.arange(3)).ravel()
        verts_of = lv[loops] - off
        # One coat byte per skin vertex (the coat is per vertex).
        vbytes = np.full((n, 4), -1, np.int32)
        vbytes[verts_of] = before["coat_bytes"][loops]
        if not np.array_equal(vbytes[verts_of], before["coat_bytes"][loops]):
            fail(f"paw {side}: a skin vertex has two coat bytes")
        # Normals per corner: how far a vertex's corners are apart is measured (float64, atan2, and by component), not
        # assumed. Each cut corner takes its parent face's own old corner normal at that vertex (below).
        vnorm = np.zeros((n, 3), np.float32)
        vnorm[verts_of] = before["normals"][loops]
        spread = {"deg_max": float(angle_deg(vnorm[verts_of], before["normals"][loops]).max()),
                  "component_max": float(np.abs(vnorm[verts_of].astype(np.float64) - before["normals"][loops]).max()),
                  "corners_differing": int((vnorm[verts_of] != before["normals"][loops]).any(1).sum())}
        strand_loops = (ls[strand_faces][:, None] + np.arange(3)).ravel()
        uv_built_err = float(np.abs(before["uv"][strand_loops].reshape(-1, 3, 2) - d["strand_uv_built"][:, None, :]).max())
        if uv_built_err > 1e-6:
            fail(f"paw {side}: the strands' UVs are {uv_built_err} from the preparation's built ones")
        skin_edges = (edge_v[:, 0] >= off) & (edge_v[:, 0] < off + n) & (edge_v[:, 1] >= off) & (edge_v[:, 1] < off + n)
        # The new vertices, on the blend's own edges.
        a, b, t = d["new_parents"][:, 0], d["new_parents"][:, 1], d["new_t"]
        ca, cb = before["co"][off + a].astype(np.float64), before["co"][off + b].astype(np.float64)
        loc = (ca + (cb - ca) * t[:, None]).astype(np.float32)
        new_world = loc.astype(np.float64) @ mw[:3, :3].T + mw[:3, 3]
        empty_local = (d["empty"][n:] @ inv[:3, :3].T + inv[:3, 3]).astype(np.float32)
        # The cut's corner normals: at a baseline vertex, its parent face's old corner normal there; at a new vertex,
        # the normalised interpolation of the parent face's old corner normals at its edge's ends.
        old_n = before["normals"][ls[skin_faces][:, None] + np.arange(3)].astype(np.float64)    # (F, 3, 3), blend order

        def parent_corner(P, v):
            hit = tri[P] == v[:, None]
            if not hit.any(1).all():
                fail(f"paw {side}: a cut corner's vertex is not on its parent face")
            return old_n[P, np.argmax(hit, 1)]
        P_all, cv_all = d["cut_parent"], d["cut_tris"]
        cut_n = np.zeros(cv_all.shape + (3,))
        for k in range(3):
            v = cv_all[:, k]
            at_base = v < n
            cut_n[at_base, k] = parent_corner(P_all[at_base], v[at_base])
            j = v[~at_base] - n
            w = (parent_corner(P_all[~at_base], a[j]) * (1.0 - t[j])[:, None]
                 + parent_corner(P_all[~at_base], b[j]) * t[j][:, None])
            cut_n[~at_base, k] = w / np.linalg.norm(w, axis=1, keepdims=True)
        paws[side] = {"g": g, "off": off, "n": n, "s3": s3, "d": d, "skin_faces": skin_faces, "strand_faces": strand_faces,
                      "vbytes": vbytes, "loc": loc, "empty_local": empty_local, "cut_normals": cut_n.reshape(-1, 3)}
        record["paws"][side] = {
            "block": [off, off + n + s3], "skin_vertices": n, "strand_vertices": s3, "skin_faces": int(len(skin_faces)),
            "strand_faces": int(len(strand_faces)), "baseline_pad_faces": int((mat == PAD).sum()),
            "skin_vs_prep_m": err_skin, "strands_vs_prep_m": err_strand, "strand_uv_built_vs_prep": uv_built_err,
            "corner_order_as_prepared": {"skin": bool(np.array_equal(tri, d["skin_tris"])),
                                         "strands": bool(np.array_equal(st, np.arange(s3).reshape(-1, 3)))},
            "skin_edges": int(skin_edges.sum()), "sharp_skin_edges": int(sharp[skin_edges].sum()),
            "new_vertices": int(len(t)), "new_vs_prep_m": float(np.abs(new_world - d["cut_verts"][n:]).max()),
            "old_skin_corner_normal_spread_per_vertex": spread}
    # --- The swap, in BMesh ------------------------------------------------------------------------------------------
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    deform = bm.verts.layers.deform.active
    shape = {name: bm.verts.layers.shape[name] for name in KEYS}
    uvl = bm.loops.layers.uv["UVMap"]
    orig = bm.faces.layers.int.new("r4_orig_face")
    cut = bm.faces.layers.int.new("r4_cut_face")
    for i, f in enumerate(bm.faces):
        f[orig] = i + 1
    doomed, old_edges, strand_refs = [], set(), {}
    for side, p in paws.items():
        faces = [bm.faces[i] for i in p["skin_faces"]]
        doomed += faces
        old_edges |= {e for f in faces for e in f.edges}
        strand_refs[side] = [bm.faces[i] for i in p["strand_faces"]]
    bmesh.ops.delete(bm, geom=doomed, context="FACES_ONLY")
    bm.verts.ensure_lookup_table()
    # Both paws' old vertices, before any is added (adding one outdates BMesh's index table; s138 stopped on that).
    old_verts = {side: [bm.verts[p["off"] + i] for i in range(p["n"])] for side, p in paws.items()}
    for side, p in paws.items():
        d, n = p["d"], p["n"]
        verts = list(old_verts[side])
        for j in range(len(p["loc"])):
            v = bm.verts.new(p["loc"][j].tolist())
            v[deform][p["g"]] = 1.0
            for name in KEYS:
                v[shape[name]] = (p["empty_local"][j] if name == f"PawEmpty_{side}" else p["loc"][j]).tolist()
            verts.append(v)
        sign = 1 if side == "R" else -1
        for fi, tri in enumerate(d["cut_tris"]):
            f = bm.faces.new((verts[tri[0]], verts[tri[1]], verts[tri[2]]))
            f.material_index = PAD if d["pad"][fi] else FUR
            f.smooth = True
            f[cut] = sign * (fi + 1)
            for c, loop in enumerate(f.loops):
                loop[uvl].uv = d["uv"][fi, c].tolist()
        for j, f in enumerate(strand_refs[side]):
            for loop in f.loops:
                loop[uvl].uv = d["strand_uv"][j].tolist()
    loose = [e for e in old_edges if e.is_valid and not e.link_faces]
    for e in loose:
        bm.edges.remove(e)
    record["old_edges_removed"] = len(loose)

    right_cut = len(paws["R"]["d"]["cut_tris"])

    def order(f):
        """One number (BMesh's sort takes no tuple; s139 stopped on that): kept faces by their old index, then the
        right paw's cut faces, then the left's."""
        if f[orig]:
            return f[orig]
        return nf + f[cut] if f[cut] > 0 else nf + right_cut - f[cut]
    bm.faces.sort(key=order)
    bm.to_mesh(me)
    bm.free()
    me.update()
    # --- Checks, and the attributes BMesh does not write as the build does -------------------------------------------
    after = read(me)
    nv2, nf2 = len(me.vertices), len(me.polygons)
    new_counts = [len(p["loc"]) for p in paws.values()]
    if nv2 != nv + sum(new_counts):
        fail(f"{nv2} vertices, expected {nv + sum(new_counts)}")
    tag_o = np.empty(nf2, np.int32)
    me.attributes["r4_orig_face"].data.foreach_get("value", tag_o)
    tag_c = np.empty(nf2, np.int32)
    me.attributes["r4_cut_face"].data.foreach_get("value", tag_c)
    kept = np.setdiff1d(np.arange(nf), np.concatenate([p["skin_faces"] for p in paws.values()]))
    want_o = np.concatenate([kept + 1, np.zeros(nf2 - len(kept), np.int32)])
    want_c = np.concatenate([np.zeros(len(kept), np.int32)] + [s * (np.arange(len(p["d"]["cut_tris"])) + 1)
                                                               for s, p in zip((1, -1), paws.values())])
    if not (np.array_equal(tag_o, want_o) and np.array_equal(tag_c, want_c)):
        fail("the faces are not in the kept-then-cut order")
    me.attributes.remove(me.attributes["r4_orig_face"])
    me.attributes.remove(me.attributes["r4_cut_face"])
    if not np.array_equal(after["co"][:nv], before["co"]):
        fail("an old vertex moved")
    if not np.array_equal(after["co"][nv:], np.concatenate([p["loc"] for p in paws.values()])):
        fail("the new vertices are not after the old ones, the right paw's first, in the cut's order")
    ls2, lt2, lv2 = after["loop_start"], after["loop_total"], after["vertex_index"]
    kept_loops_before = np.concatenate([np.arange(ls[f], ls[f] + lt[f]) for f in kept]) if len(kept) else np.zeros(0, int)
    kept_loops_after = np.arange(int(ls2[len(kept)])) if len(kept) < nf2 else np.arange(len(me.loops))
    if len(kept_loops_before) != len(kept_loops_after) or not np.array_equal(lv[kept_loops_before], lv2[kept_loops_after]):
        fail("the kept faces' corners changed")
    if not np.array_equal(before["material_index"][kept], after["material_index"][:len(kept)]):
        fail("a kept face's material changed")
    # New vertices' indices: after the old ones, the right paw's first.
    base = nv
    face_at = len(kept)
    expect_keys = {name: before["keys"][name].copy() for name in KEYS}
    expect_co = [before["co"]]
    for side, p in paws.items():
        d, n = p["d"], p["n"]
        m = len(p["loc"])
        vmap = np.concatenate([p["off"] + np.arange(n), base + np.arange(m)])
        F2 = len(d["cut_tris"])
        rows = np.arange(face_at, face_at + F2)
        if (lt2[rows] != 3).any():
            fail(f"paw {side}: a cut face is not a triangle")
        got = lv2[ls2[rows][:, None] + np.arange(3)]
        if not np.array_equal(got, vmap[d["cut_tris"]]):
            fail(f"paw {side}: the cut faces' corners are not the preparation's")
        want_mat = np.where(d["pad"], PAD, FUR)
        if not np.array_equal(after["material_index"][rows], want_mat) or not after["smooth"][rows].all():
            fail(f"paw {side}: the cut faces' materials or smoothing")
        cl = (ls2[rows][:, None] + np.arange(3)).ravel()
        if not np.array_equal(after["uv"][cl], d["uv"].reshape(-1, 2).astype(np.float32)):
            fail(f"paw {side}: the cut faces' UVs were not written")
        p.update(rows=rows, corner_loops=cl, vmap=vmap, base=base)
        for name in KEYS:
            expect_keys[name] = np.concatenate([expect_keys[name], p["empty_local"] if name == f"PawEmpty_{side}" else p["loc"]])
        expect_co.append(p["loc"])
        base += m
        face_at += F2
    # Strands: same loops, new UVs; every other kept corner's UV unchanged.
    strand_after = {}
    remap = np.full(nf, -1, np.int64)
    remap[kept] = np.arange(len(kept))
    uv_expect = after["uv"].copy()
    uv_expect[kept_loops_after] = before["uv"][kept_loops_before]
    for side, p in paws.items():
        rows = remap[p["strand_faces"]]
        sl = (ls2[rows][:, None] + np.arange(3)).ravel()
        uv_expect[sl] = np.repeat(p["d"]["strand_uv"].astype(np.float32), 3, 0)
        strand_after[side] = sl
    if not np.array_equal(after["uv"], uv_expect):
        bad = np.flatnonzero((after["uv"] != uv_expect).any(1))
        fail(f"{len(bad)} corners' UVs are not as expected (first {bad[:5].tolist()})")
    # Shape keys and positions, set explicitly (BMesh offsets dependent keys when it sees the basis move) and read back.
    expect_co = np.concatenate(expect_co)
    for kb in me.shape_keys.key_blocks:
        kb.data.foreach_set("co", expect_keys[kb.name].ravel())
    me.vertices.foreach_set("co", expect_co.ravel())
    me.update()
    check = read(me)
    for name in KEYS:
        if not np.array_equal(check["keys"][name], expect_keys[name]):
            fail(f"the {name} key did not read back")
    if not np.array_equal(check["co"], expect_co):
        fail("the positions did not read back")
    record["bmesh_keys_matched_before_reset"] = {name: bool(np.array_equal(after["keys"][name], expect_keys[name])) for name in KEYS}
    # CoatBlend on the cut skins, as the build writes it.
    col = me.color_attributes["CoatBlend"]
    for side, p in paws.items():
        coat = p["d"]["coat"][p["d"]["cut_tris"]].ravel()
        for li, c in zip(p["corner_loops"].tolist(), coat.tolist()):
            col.data[li].color = (c, c, c, 1.0)
    check = read(me)
    if not np.array_equal(check["coat_bytes"][kept_loops_after], before["coat_bytes"][kept_loops_before]):
        fail("a kept corner's coat changed")
    for side, p in paws.items():
        d, n = p["d"], p["n"]
        cv = d["cut_tris"].ravel()
        at_base = cv < n
        if not np.array_equal(check["coat_bytes"][p["corner_loops"]][at_base], p["vbytes"][cv[at_base]]):
            fail(f"paw {side}: the cut skin's coat bytes differ from the old skin's at baseline vertices")
        record["paws"][side]["coat_corners_checked_at_baseline_vertices"] = int(at_base.sum())
    # Groups: one each; the new vertices on their hand at 1.0.
    groups2 = groups_of(me)
    if groups2[:nv] != groups:
        fail("a kept vertex's groups changed")
    for side, p in paws.items():
        if any(groups2[i] != [(p["g"], 1.0)] for i in range(p["base"], p["base"] + len(p["loc"]))):
            fail(f"paw {side}: a new vertex's groups")
    # Normals: the old corners' own, and the cut skins' from the old skin.
    auto = check["normals"]
    record["normals_kept_before_reencoding"] = {
        "deg_max": float(angle_deg(auto[kept_loops_after], before["normals"][kept_loops_before]).max()),
        "component_max": float(np.abs(auto[kept_loops_after].astype(np.float64) - before["normals"][kept_loops_before]).max())}
    sharp_before = sharp_edges(me)
    want_n = np.zeros((len(me.loops), 3))
    want_n[kept_loops_after] = before["normals"][kept_loops_before]
    for side, p in paws.items():
        d, n = p["d"], p["n"]
        cv = d["cut_tris"].ravel()
        nn = p["cut_normals"]
        want_n[p["corner_loops"]] = nn
        at_new = cv >= n
        record["paws"][side]["new_normal_vs_edge_face_bisector_deg"] = {
            "p50": round(float(np.median(angle_deg(auto[p["corner_loops"]][at_new], nn[at_new]))), 4),
            "max": round(float(angle_deg(auto[p["corner_loops"]][at_new], nn[at_new]).max()), 4)}
        record["paws"][side]["baseline_vertex_auto_vs_old_deg_max"] = round(
            float(angle_deg(auto[p["corner_loops"]][~at_new], nn[~at_new]).max()), 5)
    if not np.all(np.linalg.norm(want_n, axis=1) > 0.5):
        fail("a corner has no normal to keep")
    # Kept corners' codes through BMesh, then the cut skin encoded. normals_split_custom_set re-encodes every corner:
    # s140 found that this moves 9% of the kept corners by up to 0.238 deg (it averages each fan). So the kept corners
    # get their own codes back afterwards. Their fans are as they were (same topology, no edge made sharp), so they
    # decode as before; only the cut skins keep the new codes.
    codes_bm = read_codes(me)
    record["custom_normal_codes_kept_through_bmesh"] = bool(np.array_equal(codes_bm[kept_loops_after], codes_before[kept_loops_before]))
    me.normals_split_custom_set(want_n.tolist())
    me.update()
    sharp_after = sharp_edges(me)
    if sharp_after != sharp_before:
        fail(f"setting the normals split fans: sharp edges {sharp_before} -> {sharp_after}")
    reencoded = read(me)
    codes = read_codes(me)
    moved_by_reencoding = angle_deg(reencoded["normals"][kept_loops_after], before["normals"][kept_loops_before])
    codes[kept_loops_after] = codes_before[kept_loops_before]
    write_codes(me, codes)
    # Normals are cached per mesh, and a raw attribute write need not clear that cache. A BMesh round trip rebuilds the
    # mesh, so what is read below (and what the FBX exporter evaluates) is computed from the codes now stored. The
    # keys and positions are set again after it, as after the swap.
    rt = bmesh.new()
    rt.from_mesh(me)
    rt.to_mesh(me)
    rt.free()
    me.update()
    for kb in me.shape_keys.key_blocks:
        kb.data.foreach_set("co", expect_keys[kb.name].ravel())
    me.vertices.foreach_set("co", expect_co.ravel())
    me.update()
    if not np.array_equal(read_codes(me), codes):
        fail("the custom-normal codes did not survive as written")
    final = read(me)
    drift_kept = angle_deg(final["normals"][kept_loops_after], before["normals"][kept_loops_before])
    drift_new = np.concatenate([angle_deg(final["normals"][p["corner_loops"]], want_n[p["corner_loops"]]) for p in paws.values()])
    record["normals"] = {"kept_corners_deg": {"max": float(drift_kept.max()), "exact_share": float((drift_kept == 0).mean())},
                         "kept_corners_component_max": float(np.abs(final["normals"][kept_loops_after].astype(np.float64)
                                                                    - before["normals"][kept_loops_before]).max()),
                         "kept_corners_bit_identical": bool(np.array_equal(final["normals"][kept_loops_after],
                                                                           before["normals"][kept_loops_before])),
                         "kept_moved_by_reencoding_before_restore_deg": {"max": float(moved_by_reencoding.max()),
                                                                         "share_moved": float((moved_by_reencoding > 0).mean())},
                         "cut_skin_corners_deg": {"p50": float(np.median(drift_new)), "max": float(drift_new.max())},
                         "tolerance_deg": {"kept": KEPT_NORMAL_TOL_DEG, "cut": CUT_NORMAL_TOL_DEG},
                         "sharp_edges": {"before": sharp_before, "after": sharp_after}}
    if drift_kept.max() > KEPT_NORMAL_TOL_DEG or drift_new.max() > CUT_NORMAL_TOL_DEG:
        fail(f"the normals are not as wanted: {record['normals']}")
    for key in ("co", "uv", "coat_bytes", "material_index", "vertex_index"):
        if not np.array_equal(final[key], check[key]):
            fail(f"setting the normals changed {key}")
    for name in KEYS:
        if not np.array_equal(final["keys"][name], expect_keys[name]):
            fail(f"setting the normals changed the {name} key")
    copy = me.copy()
    record["validate_changed"] = bool(copy.validate(verbose=False, clean_customdata=False))
    bpy.data.meshes.remove(copy)
    if record["validate_changed"]:
        fail("Mesh.validate would change the assembled mesh")
    record["mesh"] = {"vertices": len(me.vertices), "faces": len(me.polygons), "corners": len(me.loops),
                      "vertices_before": nv, "faces_before": nf, "corners_before": nl,
                      "kept_faces": int(len(kept)), "material_triangles": {mats[k]: int(c) for k, c in
                                                                           enumerate(np.bincount(final["material_index"], weights=final["loop_total"] - 2, minlength=23).astype(int)) if c}}
    for side, p in paws.items():
        record["paws"][side].update(cut_faces=int(len(p["rows"])), cut_pad_faces=int(p["d"]["pad"].sum()),
                                    new_vertex_range=[p["base"], p["base"] + len(p["loc"])],
                                    cut_face_range=[int(p["rows"][0]), int(p["rows"][-1]) + 1])
    # --- The candidate's export ------------------------------------------------------------------------------------------
    if any(kb.value != 0.0 for kb in me.shape_keys.key_blocks[1:]):
        fail("the empty-fist keys moved from 0")
    record["candidate"] = {"file": "SK_NyaagyuSamurai_R4Paws.fbx",
                           "sha256": export(out / "SK_NyaagyuSamurai_R4Paws.fbx", obj, rig)}
    record["seconds"] = round(time.time() - t0, 1)
    with open(out / "record.json", "x") as fh:
        json.dump(record, fh, indent=1)
    print(MARKER + " " + json.dumps({"mesh": record["mesh"], "normals": record["normals"], "control": record["control"],
                                     "candidate": record["candidate"], "seconds": record["seconds"]}), flush=True)


main()
