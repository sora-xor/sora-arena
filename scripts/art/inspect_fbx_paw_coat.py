"""The paws' CoatBlend as an FBX holds it, against the coat nyaakoto_tp_paws wrote at the same vertices.

s103's renders and root's 12:53 UTC review of e8d5b587 (2026-10-26) show the paws white, with no tabby back. s97's
isolated preview showed a tabby back. Is the tabby back in the data? This reads an FBX with Blender's own parse_fbx
(fbx_unreal_sockets.parser, no bpy), so it runs on the host. It reads:
- **the paws:** the vertices each hand cluster (hand_R, hand_L) holds;
- **per corner:** the CoatBlend colour layer's R (1 is the white coat, 0 the tabby: create_nyaagyu_hero_character's
  fur mix) and the polygon's material;
- **the coat the build wrote,** recomputed at each vertex by the paw module that built the file (the runtime
  manifest's module_sha256): the digit weight times the COAT_TURN ramp, then stored as Blender stores a byte colour
  (sRGB-encoded) and exported (colors_type SRGB, the exporter's default).

It reports, per paw (its skin; r3's fur strands, isolated triangles carrying their root's coat, are counted apart,
with how many there are and how far off the skin they reach):
- the R distribution;
- the shares near tabby (< 0.05) and near white (> 0.95);
- the same over the paw's back (recomputed coat 0);
- the largest difference from the recomputed coat;
- the materials, by the file's own per-polygon index. Unreal's export of an imported LOD writes its sections' raw
  indices, not routed through LODMaterialMap as the renderer routes them: check_nyaakoto_lod_materials.py checks what
  Unreal renders.

The file's frame is found, not assumed. Of the axis maps listed in AXIS_MAPS, it is the one that puts both paws' skin
vertices (not the strands') on the paw's own surface, nyaakoto_tp_paws.paw_sdf: the skin is that field's zero set
pushed out by at most FUZZ_MAX. (A centroid test cannot tell: the palm's mass puts the paw's centroid some 6 cm off
its channel.)

Run (host Python with numpy): python3 scripts/art/inspect_fbx_paw_coat.py <fbx> <out.json> [<paw module dir>]
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FBX, OUT = Path(sys.argv[1]), Path(sys.argv[2])
sys.path[:0] = ([sys.argv[3]] if len(sys.argv) > 3 else []) + [str(HERE)]
import fbx_unreal_sockets as FUS  # noqa: E402
import nyaakoto_tp_paws as TPP  # noqa: E402

RECORD = json.loads((ROOT / "Content/SourceArt/Characters/Hero/runtime_skin_manifest.json").read_text())
PAWS = RECORD["third_person"]["paws"]
MODULE_SHA = hashlib.sha256(Path(TPP.__file__).read_bytes()).hexdigest()
if MODULE_SHA != PAWS["module_sha256"]:
    raise SystemExit(f"{TPP.__file__} ({MODULE_SHA[:12]}) is not the paw module that built the assets "
                     f"({PAWS['module_sha256'][:12]}): pass that module's directory")
# FBX centimetres to Blender metres: Blender's own export (axis_forward -Y, axis_up Z: a half turn about Z on the root
# nodes) and Unreal's (Blender's axes; Unreal mirrors its own y back on export).
AXIS_MAPS = {"identity": np.eye(3) / 100.0, "half_turn_z": np.diag([-1.0, -1.0, 1.0]) / 100.0,
             "mirror_y": np.diag([1.0, -1.0, 1.0]) / 100.0, "mirror_x": np.diag([-1.0, 1.0, 1.0]) / 100.0}
# m: an isolated polygon reaching past this off the paw's surface is a strand (nyaakoto_tp_fur keeps a strand only if
# its tip clears FUZZ_MAX by 0.1 mm); a skin triangle that Unreal's export isolates lies on the skin. In s128's export
# (2026-10-26) the strands reach 0.90 mm and more, the isolated skin triangles 0.67 mm at most.
STRAND_REACH_M = TPP.FUZZ_MAX + 0.00005


def srgb(x):
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1.0 / 2.4) - 0.055)


def frame(side):
    return {k: (np.array(v) if isinstance(v, list) else v) for k, v in PAWS["by_side"][side]["frame"].items()}


root, _version = FUS.parser().parse(str(FBX))
objects = {o.props[0]: o for o in FUS._child(root, b"Objects").elems}
links = [(c.props[0], c.props[1], c.props[2]) for c in FUS._child(root, b"Connections").elems]
name = lambda o: o.props[1].split(b"\x00\x01")[0].decode()  # noqa: E731
nodes = FUS.read_fbx(FBX)["nodes"]
out = {"fbx": str(FBX), "fbx_sha256": hashlib.sha256(FBX.read_bytes()).hexdigest(),
       "paw_module": {"file": TPP.__file__, "sha256": MODULE_SHA}, "meshes": {}}
for gid, geo in objects.items():
    if geo.id != b"Geometry" or geo.props[2] != b"Mesh":
        continue
    model_uid = next(d for k, s, d in links if k == b"OO" and s == gid and objects.get(d) is not None
                     and objects[d].id == b"Model")
    model = name(objects[model_uid])
    G = FUS.global_matrix(nodes, model)
    V = np.array(FUS._child(geo, b"Vertices").props[0], float).reshape(-1, 3)
    W = V @ G[:3, :3].T + G[:3, 3]                                         # the file's world, its own units
    pvi = np.array(FUS._child(geo, b"PolygonVertexIndex").props[0], np.int64)
    corner_vertex = np.where(pvi < 0, ~pvi, pvi)
    corner_poly = np.concatenate([[0], np.cumsum(pvi < 0)[:-1]])
    layers = {}
    for e in geo.elems:
        if e.id == b"LayerElementColor":
            layers[FUS._child(e, b"Name").props[0].decode()] = e
    coat_layer = layers.get("CoatBlend") or (next(iter(layers.values())) if layers else None)
    row = {"model": model, "vertices": int(len(V)), "corners": int(len(pvi)),
           "color_layers": sorted(layers), "coat_layer": None}
    if coat_layer is None:
        row["failed"] = "no colour layer"
        out["meshes"][model] = row
        continue
    mapping = FUS._child(coat_layer, b"MappingInformationType").props[0].decode()
    reference = FUS._child(coat_layer, b"ReferenceInformationType").props[0].decode()
    colors = np.array(FUS._child(coat_layer, b"Colors").props[0], float).reshape(-1, 4)
    idx = FUS._child(coat_layer, b"ColorIndex")
    direct = colors[np.array(idx.props[0], np.int64)] if reference == "IndexToDirect" else colors
    if mapping == "ByPolygonVertex":
        corner_rgba = direct
    elif mapping in ("ByVertice", "ByVertex"):                             # Unreal's export: one colour per vertex
        corner_rgba = direct[corner_vertex]
    else:
        raise SystemExit(f"{model}: colour mapping {mapping} is not modelled")
    row["coat_layer"] = {"name": FUS._child(coat_layer, b"Name").props[0].decode(), "mapping": mapping,
                         "reference": reference}
    mat_names = [name(objects[s]) for k, s, d in links if k == b"OO" and d == model_uid
                 and objects.get(s) is not None and objects[s].id == b"Material"]
    mat_layer = FUS._child(geo, b"LayerElementMaterial")
    poly_mat = np.array(FUS._child(mat_layer, b"Materials").props[0], np.int64) if mat_layer is not None else None
    def is_(uid, kind, sub):
        o = objects.get(uid)
        return o is not None and o.id == kind and (sub is None or o.props[2] == sub)

    # This mesh's own clusters: geometry <- skin <- cluster <- bone (Unreal's export has one skin per LOD mesh).
    skins = {s for k, s, d in links if d == gid and is_(s, b"Deformer", b"Skin")}
    own = {s for k, s, d in links if d in skins and is_(s, b"Deformer", b"Cluster")}
    clusters = {}
    for k, s, d in links:
        if d in own and is_(s, b"Model", None):
            ix = FUS._child(objects[d], b"Indexes")
            clusters[name(objects[s])] = np.array(ix.props[0], np.int64) if ix is not None else np.zeros(0, np.int64)
    hands = {side: clusters.get(f"hand_{side}", np.zeros(0, np.int64)) for side in ("R", "L")}
    if not all(len(h) for h in hands.values()):
        row["failed"] = "no hand clusters"
        out["meshes"][model] = row
        continue
    skels = {s: TPP.skeleton(frame(s), PAWS["by_side"][s]["palm_radii_m"]) for s in ("R", "L")}
    # r3's fur strands are isolated triangles: each of their corners is its vertex's only corner. Unreal's export
    # isolates some skin triangles too (it splits vertices at seams and section edges: its LOD2, which has no strands,
    # has 34-36 a paw); STRAND_REACH_M tells them apart below. The strands' tips stand up to 8 mm off the skin, so the
    # axis fit uses the polygons that share a vertex.
    uses = np.bincount(corner_vertex, minlength=len(V))
    n_poly = int(corner_poly[-1]) + 1
    isolated = (np.bincount(corner_poly, weights=(uses[corner_vertex] > 1).astype(float), minlength=n_poly) == 0)
    skin_vertex = np.zeros(len(V), bool)
    skin_vertex[corner_vertex[~isolated[corner_poly]]] = True
    skin_of = {s: hands[s][skin_vertex[hands[s]]] for s in ("R", "L")}
    fits = {}
    for label, M in AXIS_MAPS.items():
        fits[label] = max(float(np.percentile(np.abs(TPP.paw_sdf(W[skin_of[s]] @ M.T, skels[s])), 99)) for s in ("R", "L"))
    axis = min(fits, key=fits.get)
    row["axis_map"] = {"chosen": axis, "worst_paw_p99_off_surface_mm": {k: round(v * 1000.0, 3) for k, v in fits.items()}}
    if fits[axis] > TPP.FUZZ_MAX + 0.001:
        row["failed"] = "no axis map puts the paws on their own surface"
        out["meshes"][model] = row
        continue
    B = W @ AXIS_MAPS[axis].T                                               # Blender world metres
    for side in ("R", "L"):
        fr = frame(side)
        skel = skels[side]
        in_paw = np.zeros(len(V), bool)
        in_paw[hands[side]] = True
        # A strand is an isolated polygon reaching past the fuzzed skin. It carries its root's coat, which the coat at
        # the strand's own vertex need not equal: the strands are counted apart, and compared with nothing.
        sdf = np.full(len(V), -np.inf)
        sdf[hands[side]] = TPP.paw_sdf(B[hands[side]], skel)
        reach = np.full(n_poly, -np.inf)
        np.maximum.at(reach, corner_poly, sdf[corner_vertex])
        strand_poly = isolated & (reach > STRAND_REACH_M)
        lone_skin_poly = isolated & ~strand_poly
        strand = strand_poly[corner_poly]
        on_all = in_paw[corner_vertex]
        on = on_all & ~strand
        paw_polys = np.unique(corner_poly[on_all])
        cv = corner_vertex[on]
        r = corner_rgba[on, 0]
        coat = TPP.digit_weight(B[cv], skel, TPP.COAT_RAMP) * TPP.ease(*TPP.COAT_TURN, TPP.turn_of(B[cv], fr))
        stored = np.round(srgb(coat) * 255.0) / 255.0
        back = coat < 1e-6
        diff = np.abs(r - stored)
        rs = corner_rgba[on_all & strand, 0]
        side_row = {
            "paw_vertices": int(len(hands[side])), "paw_corners": int(on.sum()),
            "strands": int(strand_poly[paw_polys].sum()), "strand_corners": int((on_all & strand).sum()),
            "strand_reach_min_mm": round(float(reach[paw_polys][strand_poly[paw_polys]].min() * 1000.0), 4)
            if strand_poly[paw_polys].any() else None,
            "isolated_skin_polygons": int(lone_skin_poly[paw_polys].sum()),
            "isolated_skin_reach_max_mm": round(float(reach[paw_polys][lone_skin_poly[paw_polys]].max() * 1000.0), 4)
            if lone_skin_poly[paw_polys].any() else None,
            "strand_share_near_tabby_lt_0.05": round(float((rs < 0.05).mean()), 4) if len(rs) else None,
            "strand_share_near_white_gt_0.95": round(float((rs > 0.95).mean()), 4) if len(rs) else None,
            "R_percentiles_1_10_25_50_75_90_99": [round(float(np.percentile(r, q)), 4) for q in (1, 10, 25, 50, 75, 90, 99)],
            "share_near_tabby_lt_0.05": round(float((r < 0.05).mean()), 4),
            "share_near_white_gt_0.95": round(float((r > 0.95).mean()), 4),
            "back_corners_recomputed_coat_0": int(back.sum()),
            "back_R_max": round(float(r[back].max()), 4) if back.any() else None,
            "back_share_near_tabby": round(float((r[back] < 0.05).mean()), 4) if back.any() else None,
            "max_abs_diff_from_recomputed": round(float(diff.max()), 4),
            # Unrounded (root's precision probe, 20:37 UTC 2026-10-26): the rounded 0.0039 hides corners a few 1e-8
            # past one byte.
            "max_abs_diff_from_recomputed_unrounded": float(diff.max()),
            "corners_beyond_one_byte_plus_1e-9": int((diff > 1.0 / 255.0 + 1e-9).sum()),
            "max_excess_beyond_one_byte": float(max(0.0, diff.max() - 1.0 / 255.0)),
            "share_within_1_byte": round(float((diff <= 1.0 / 255.0 + 1e-9).mean()), 4),
            "rgb_equal": bool(np.allclose(corner_rgba[on, 0], corner_rgba[on, 1]) and np.allclose(corner_rgba[on, 0], corner_rgba[on, 2])),
        }
        if poly_mat is not None and mat_names:
            pm = poly_mat[corner_poly[on_all]] if len(poly_mat) == len(np.unique(corner_poly)) else np.zeros(int(on_all.sum()), np.int64)
            side_row["materials_by_file_index"] = sorted({mat_names[int(i)] for i in np.unique(pm)})
        row[side] = side_row
    out["meshes"][model] = row
OUT.write_text(json.dumps(out, indent=2) + "\n")
print("FBX_PAW_COAT " + json.dumps({m: {s: {k: r[s][k] for k in ("strands", "share_near_tabby_lt_0.05", "share_near_white_gt_0.95",
                                                                   "back_share_near_tabby", "max_abs_diff_from_recomputed",
                                                                   "materials_by_file_index") if k in r[s]}
                                        for s in ("R", "L") if s in r} | ({"failed": r["failed"]} if "failed" in r else {})
                                    for m, r in out["meshes"].items()}), flush=True)
