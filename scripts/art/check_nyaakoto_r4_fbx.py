"""Host checks of the r4 candidate's FBX (assemble_nyaakoto_r4_paws.py) against the production SK FBX and its own control.

1. **The control is the production export.** Blender's export of the unmodified runtime blend must equal
   Content/SourceArt/SK_NyaagyuSamurai.fbx element for element, with two exceptions:
   - FBXHeaderExtension (its time stamp and scene info) is not compared;
   - object UIDs are compared by the object they name. Blender's exporter derives them from Python's hash() of
     strings, which each process seeds anew. s141's first check (s141_fbx_check.json) counted those as 822
     differences. Objects are matched by their order and identity (class, name, type).
   This shows the assembly exports as the build does.
2. **The candidate differs from the control only where the paws changed:**
   - the mesh's positions, polygons, edges, normals, colours, UVs and materials;
   - the hand_R and hand_L clusters' indexes and weights;
   - the two empty-fist shapes, and their channels' per-vertex weights.
   Every other element (bones, bind poses, materials, the idle's curves, connections) must be equal.
3. **Semantics,** with the preparation's arrays and the assembly's record:
   - **Vertices:** the old ones are where they were. A new one lies on its baseline edge at the cut's parameter.
   - **Polygons:** the kept ones are the control's, in order, corner for corner. The cut's faces follow, right paw
     first, as prepared.
   - **Materials:** kept faces are unchanged. The cut's faces are the old skin's fur slot, or its pad slot for pads.
   - **UVs:** kept corners are unchanged, except the strands', which take their roots' new UVs. The cut's corners are the
     preparation's (float32).
   - **Colours:** kept corners are unchanged. The cut's corners at baseline vertices equal the old skin's there. At new
     vertices they are the sRGB byte of the coat rule; the largest byte difference from Python's sRGB formula is
     reported.
   - **Normals:** kept corners within KEPT_NORMAL_TOL_DEG of the control's. A cut corner at a baseline vertex has its parent
     face's old corner normal there. At a new vertex it has the normalised interpolation of the parent face's old
     corner normals at its edge's ends, within CUT_NORMAL_TOL_DEG. Angles are float64, atan2(|a x b|, a . b).
   - **Weights:** the hand clusters gain exactly their paw's new vertices, at 1.0. No other cluster has them.
   - **The empty fist:** each shape keeps its old entries.
     - A new vertex of that paw moves to empty_points of its own position, through the mesh's transform. The transform
       is fitted on the paw's baseline vertices, and the rule is compared in world metres.
     - The other paw's new vertices do not move.
   - **The cut skin, read from the file:** a closed, oriented manifold (Euler 0), and no UV face folded.

Writes a new JSON file and prints NYAAKOTO_R4_FBX_CHECK with its summary. It exits non-zero on any failed check.

Run (host, numpy): /usr/bin/python3 scripts/art/check_nyaakoto_r4_fbx.py <assembly folder> <prep folder> <out.json>
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import fbx_unreal_sockets as FUS  # noqa: E402
import measure_paw_surface_prototypes as MS  # noqa: E402
import nyaakoto_tp_paws as TPP  # noqa: E402
import plan_nyaakoto_tp_review as PL  # noqa: E402

PRODUCTION = ROOT / "Content/SourceArt/SK_NyaagyuSamurai.fbx"
KEPT_NORMAL_TOL_DEG = 1e-6             # kept corners keep their stored codes (assemble_nyaakoto_r4_paws.py)
CUT_NORMAL_TOL_DEG = 0.05              # the cut skin: the INT16 smooth-fan encoding of each fan's wanted normal
MORPH_TOL_M = 2e-6
NAMED = {b"Geometry", b"Model", b"Deformer", b"Material", b"Pose", b"NodeAttribute", b"AnimationCurve",
         b"AnimationCurveNode", b"AnimationStack", b"AnimationLayer"}
ALLOWED = {("Geometry", "Mesh"): {"Vertices", "PolygonVertexIndex", "Edges", "LayerElementNormal/Normals",
                                  "LayerElementNormal/NormalsIndex", "LayerElementColor/Colors",
                                  "LayerElementColor/ColorIndex", "LayerElementUV/UV", "LayerElementUV/UVIndex",
                                  "LayerElementMaterial/Materials"},
           ("Geometry", "Shape"): {"Indexes", "Vertices", "Normals"},
           ("Deformer", "BlendShapeChannel"): {"FullWeights"},
           ("Deformer", "Cluster"): {"Indexes", "Weights"}}
HAND_CLUSTERS = {"hand_R", "hand_L"}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def obj_name(e):
    return e.props[1].split(b"\x00\x01")[0].decode()


def step(e):
    if e.id in NAMED and len(e.props) > 2 and isinstance(e.props[1], (bytes, bytearray)):
        return f"{e.id.decode()}[{obj_name(e)}|{bytes(e.props[2]).decode()}]"
    return e.id.decode()


def uid_order(root):
    """Each object's UID (and the documents') by its place in the file, with its identity: {uid: (place, identity)}."""
    out = {}
    for group in (b"Documents", b"Objects"):
        for k, e in enumerate(FUS._child(root, group).elems):
            if e.props and isinstance(e.props[0], int):
                out[e.props[0]] = ((group, k), (e.id, bytes(e.props[1]) if len(e.props) > 1 else b"",
                                                bytes(e.props[2]) if len(e.props) > 2 else b""))
    return out


def same_prop(x, y, ua, ub):
    if type(x) is not type(y):
        return False
    if isinstance(x, int) and (x in ua or y in ub):
        return x in ua and y in ub and ua[x] == ub[y]
    return x == y


def diff(a, b, path, out, ua, ub):
    """The element paths where a and b differ: their properties (UIDs by the object they name), or the number of their
    children."""
    if a.id != b.id or bytes(a.props_type) != bytes(b.props_type) or len(a.props) != len(b.props):
        out.append(path + "#shape")
        return
    if not all(same_prop(x, y, ua, ub) for x, y in zip(a.props, b.props)):
        out.append(path)
    if len(a.elems) != len(b.elems):
        out.append(path + "#children")
        return
    for x, y in zip(a.elems, b.elems):
        diff(x, y, path + "/" + step(x), out, ua, ub)


def tree_diff(root_a, root_b):
    out = []
    if [e.id for e in root_a.elems] != [e.id for e in root_b.elems]:
        return ["#top-level"]
    ua, ub = uid_order(root_a), uid_order(root_b)
    if sorted(v for v in ua.values()) != sorted(v for v in ub.values()):
        return ["#objects"]
    for x, y in zip(root_a.elems, root_b.elems):
        if x.id == b"FBXHeaderExtension":
            continue
        diff(x, y, step(x), out, ua, ub)
    return out


def allowed(path):
    """Whether a candidate-vs-control difference is one the paws' change may make."""
    parts = path.split("/")
    if len(parts) < 3 or parts[0] != "Objects" or "#" in path:
        return False
    head = parts[1]
    kind, rest = head.split("[", 1)
    name, sub = rest.rstrip("]").rsplit("|", 1)
    if (kind, sub) not in ALLOWED or "/".join(parts[2:]) not in ALLOWED[(kind, sub)]:
        return False
    return not (kind == "Deformer" and sub == "Cluster" and name not in HAND_CLUSTERS)


def mesh_data(root):
    """The skinned mesh's arrays from a parsed FBX: per-vertex positions, polygons, per-corner normals, colours and UVs,
    per-polygon materials, the clusters' weights by bone and the shapes' deltas by name, in the file's mesh space."""
    objects = {o.props[0]: o for o in FUS._child(root, b"Objects").elems}
    links = [(c.props[0], c.props[1], c.props[2]) for c in FUS._child(root, b"Connections").elems]
    geo = next(o for o in objects.values() if o.id == b"Geometry" and o.props[2] == b"Mesh")
    arr = lambda e, k, dt=float: np.array(FUS._child(e, k).props[0], dt)  # noqa: E731
    V = arr(geo, b"Vertices").reshape(-1, 3)
    pvi = arr(geo, b"PolygonVertexIndex", np.int64)
    corner_vertex = np.where(pvi < 0, ~pvi, pvi)
    ends = np.flatnonzero(pvi < 0)
    starts = np.concatenate([[0], ends[:-1] + 1])

    def layer(name, data, index, width):
        el = FUS._child(geo, name)
        if FUS._child(el, b"MappingInformationType").props[0] != b"ByPolygonVertex":
            raise SystemExit(f"{name.decode()} is not per corner")
        vals = arr(el, data).reshape(-1, width)
        return vals[arr(el, index, np.int64)] if FUS._child(el, b"ReferenceInformationType").props[0] == b"IndexToDirect" else vals
    out = {"V": V, "corner_vertex": corner_vertex, "starts": starts, "counts": ends - starts + 1,
           "normals": layer(b"LayerElementNormal", b"Normals", b"NormalsIndex", 3),
           "colors": layer(b"LayerElementColor", b"Colors", b"ColorIndex", 4),
           "uv": layer(b"LayerElementUV", b"UV", b"UVIndex", 2),
           "materials": arr(FUS._child(geo, b"LayerElementMaterial"), b"Materials", np.int64)}
    clusters = {}
    for o in objects.values():
        if o.id == b"Deformer" and o.props[2] == b"Cluster" and FUS._child(o, b"Indexes") is not None:
            clusters[obj_name(o)] = dict(zip(arr(o, b"Indexes", np.int64).tolist(), arr(o, b"Weights").tolist()))
    shapes = {}
    for o in objects.values():
        if o.id == b"Geometry" and o.props[2] == b"Shape":
            shapes[obj_name(o)] = dict(zip(arr(o, b"Indexes", np.int64).tolist(), map(tuple, arr(o, b"Vertices").reshape(-1, 3))))
    out["clusters"], out["shapes"] = clusters, shapes
    if len(out["materials"]) != len(starts):
        raise SystemExit("the materials are not one per polygon")
    return out


def polygons(m):
    return [tuple(m["corner_vertex"][s:s + c]) for s, c in zip(m["starts"], m["counts"])]


def corners_of(m, faces):
    return np.concatenate([np.arange(m["starts"][f], m["starts"][f] + m["counts"][f]) for f in faces])


def angle_deg(a, b):
    """Degrees between row vectors, in float64 as atan2(|a x b|, a . b) (arccos misreads near-equal unit vectors)."""
    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    return np.degrees(np.arctan2(np.linalg.norm(np.cross(a, b), axis=1), (a * b).sum(1)))


def srgb_byte(linear):
    x = np.clip(linear, 0.0, 1.0)
    s = np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1.0 / 2.4) - 0.055)
    return np.round(s * 255.0).astype(int)


def fit_affine(src, dst):
    """dst ~ src @ A.T + t, least squares: (A, t, the largest residual)."""
    X = np.hstack([src, np.ones((len(src), 1))])
    sol, *_ = np.linalg.lstsq(X, dst, rcond=None)
    A, t = sol[:3].T, sol[3]
    return A, t, float(np.abs(src @ A.T + t - dst).max())


def main():
    asm_dir, prep_dir, out_path = (Path(a) if Path(a).is_absolute() else ROOT / a for a in sys.argv[1:4])
    if out_path.exists():
        raise SystemExit(f"{out_path} exists")
    rec = json.loads((asm_dir / "record.json").read_text())
    prep = json.loads((prep_dir / "record.json").read_text())
    failed = []
    control_path, cand_path = asm_dir / rec["control"]["file"], asm_dir / rec["candidate"]["file"]
    for path, digest in ((control_path, rec["control"]["sha256"]), (cand_path, rec["candidate"]["sha256"])):
        if sha256(path) != digest:
            raise SystemExit(f"{path.name} is not the assembly's")
    manifest = json.loads(PL.MANIFEST.read_text())
    if sha256(PRODUCTION) != manifest["skeletal_fbx_sha256"]:
        raise SystemExit("the production SK FBX is not the manifest's")
    if rec["inputs"]["prep_record"] != sha256(prep_dir / "record.json"):
        raise SystemExit("the preparation is not the one the assembly used")
    parse = FUS.parser().parse
    prod, control, cand = (parse(str(p))[0] for p in (PRODUCTION, control_path, cand_path))
    report = {"inputs": {"production": sha256(PRODUCTION), "control": rec["control"]["sha256"], "candidate": rec["candidate"]["sha256"],
                         "assembly_record": sha256(asm_dir / "record.json"), "prep_record": sha256(prep_dir / "record.json"),
                         "scripts/art/check_nyaakoto_r4_fbx.py": sha256(__file__)}}
    d_prod = tree_diff(prod, control)
    report["control_vs_production"] = {"differences": d_prod[:50], "count": len(d_prod)}
    if d_prod:
        failed.append(f"the control differs from the production FBX in {len(d_prod)} places")
    d_cand = tree_diff(control, cand)
    report["candidate_vs_control"] = {"differences": d_cand, "outside_the_paws": [p for p in d_cand if not allowed(p)]}
    if report["candidate_vs_control"]["outside_the_paws"]:
        failed.append(f"the candidate differs outside the paws: {report['candidate_vs_control']['outside_the_paws'][:5]}")
    c, r = mesh_data(control), mesh_data(cand)
    nv = len(c["V"])
    if nv != rec["mesh"]["vertices_before"] or not np.array_equal(r["V"][:nv], c["V"]):
        failed.append("the old vertices are not where they were")
    cpolys, rpolys = polygons(c), polygons(r)
    skin = set()
    paws = {}
    base = nv
    for side in ("R", "L"):
        d = {k: v for k, v in np.load(prep_dir / f"paw_{side}.npz", allow_pickle=False).items()}
        row = rec["paws"][side]
        off, n, s3 = row["block"][0], row["skin_vertices"], row["strand_vertices"]
        m = row["new_vertices"]
        sf = [f for f, p in enumerate(cpolys) if all(off <= v < off + n for v in p)]
        stf = [f for f, p in enumerate(cpolys) if all(off + n <= v < off + n + s3 for v in p)]
        skin |= set(sf)
        paws[side] = dict(d=d, off=off, n=n, s3=s3, m=m, base=base, skin_faces=sf, strand_faces=stf,
                          vmap=np.concatenate([off + np.arange(n), base + np.arange(m)]))
        base += m
    kept = [f for f in range(len(cpolys)) if f not in skin]
    if rpolys[:len(kept)] != [cpolys[f] for f in kept]:
        failed.append("the kept polygons are not the control's, in order")
    if not np.array_equal(r["materials"][:len(kept)], c["materials"][kept]):
        failed.append("a kept polygon's material changed")
    ck, rk = corners_of(c, kept), np.arange(sum(c["counts"][kept]))
    strand_rows = np.concatenate([np.searchsorted(kept, p["strand_faces"]) for p in paws.values()])
    strand_corners = set(corners_of(r, strand_rows).tolist())
    keep_uv = np.array([k not in strand_corners for k in rk])
    checks = {}
    if not np.array_equal(r["uv"][rk][keep_uv], c["uv"][ck][keep_uv]):
        failed.append("a kept non-strand corner's UV changed")
    if not np.array_equal(r["colors"][rk], c["colors"][ck]):
        failed.append("a kept corner's colour changed")
    kn = angle_deg(r["normals"][rk], c["normals"][ck])
    checks["kept_normals_deg"] = {"max": float(kn.max()), "exact_share": float((kn == 0).mean())}
    if kn.max() > KEPT_NORMAL_TOL_DEG:
        failed.append(f"kept normals moved up to {kn.max()} deg")
    face_at = len(kept)
    tris_all = []
    for side, p in paws.items():
        d, n, vmap = p["d"], p["n"], p["vmap"]
        F2 = len(d["cut_tris"])
        rows = list(range(face_at, face_at + F2))
        want = [tuple(t) for t in vmap[d["cut_tris"]].tolist()]
        got = rpolys[face_at:face_at + F2]
        row = {"cut_faces": F2, "corners_as_prepared": got == want}
        if got != want:
            failed.append(f"paw {side}: the cut faces are not as prepared")
        # Materials: the old skin's two slots.
        old_mats = c["materials"][p["skin_faces"]]
        old_pad = np.asarray(prep["paws"][side]["baseline"]["pad_faces"])
        slots = sorted(set(old_mats.tolist()))
        counts = {s: int((old_mats == s).sum()) for s in slots}
        pad_slot = next(s for s, k in counts.items() if k == int(old_pad))
        fur_slot = next(s for s in slots if s != pad_slot)
        want_mat = np.where(d["pad"], pad_slot, fur_slot)
        if not np.array_equal(r["materials"][rows], want_mat):
            failed.append(f"paw {side}: the cut faces' materials")
        cc = corners_of(r, rows)
        cv = d["cut_tris"].ravel()
        at_base = cv < n
        # UVs and strands.
        if not np.array_equal(r["uv"][cc], d["uv"].reshape(-1, 2).astype(np.float32).astype(float)):
            failed.append(f"paw {side}: the cut faces' UVs are not the preparation's")
        srows = np.searchsorted(kept, p["strand_faces"])
        su = r["uv"][corners_of(r, srows)].reshape(-1, 3, 2)
        if not np.array_equal(su, np.repeat(d["strand_uv"].astype(np.float32).astype(float)[:, None, :], 3, 1)):
            failed.append(f"paw {side}: the strands' UVs are not their roots' new ones")
        # Colours and normals against the old skin, per vertex.
        old_c = corners_of(c, p["skin_faces"])
        old_v = c["corner_vertex"][old_c] - p["off"]
        vcol = np.zeros((n, 4))
        vcol[old_v] = c["colors"][old_c]
        old_tri = old_v.reshape(-1, 3)                               # the control's skin faces, prepared order
        old_n = c["normals"][old_c].reshape(-1, 3, 3)

        def parent_corner(P, v):
            hit = old_tri[P] == v[:, None]
            if not hit.any(1).all():
                raise SystemExit(f"paw {side}: a cut corner's vertex is not on its parent face")
            return old_n[P, np.argmax(hit, 1)]
        if not np.array_equal(r["colors"][cc][at_base], vcol[cv[at_base]]):
            failed.append(f"paw {side}: the cut skin's colours at baseline vertices differ from the old skin's")
        coat_new = d["coat"][cv[~at_base]]
        byte_diff = np.abs(np.round(r["colors"][cc][~at_base][:, 0] * 255.0).astype(int) - srgb_byte(coat_new))
        row["new_vertex_coat_byte_vs_python_srgb_max"] = int(byte_diff.max()) if len(byte_diff) else 0
        if len(byte_diff) and byte_diff.max() > 1:
            failed.append(f"paw {side}: new vertices' coat bytes are up to {byte_diff.max()} from the rule")
        a, b, t = d["new_parents"][:, 0], d["new_parents"][:, 1], d["new_t"]
        P = np.repeat(d["cut_parent"], 3)
        want_n = np.zeros((len(cv), 3))
        want_n[at_base] = parent_corner(P[at_base], cv[at_base])
        j = cv[~at_base] - n
        w = parent_corner(P[~at_base], a[j]) * (1.0 - t[j])[:, None] + parent_corner(P[~at_base], b[j]) * t[j][:, None]
        want_n[~at_base] = w / np.linalg.norm(w, axis=1, keepdims=True)
        nd = angle_deg(r["normals"][cc], want_n)
        row["cut_normals_deg_max"] = float(nd.max())
        if nd.max() > CUT_NORMAL_TOL_DEG:
            failed.append(f"paw {side}: cut skin normals up to {nd.max()} deg from the old skin's")
        # New vertices on their edges.
        Va, Vb = r["V"][p["off"] + a], r["V"][p["off"] + b]
        on_edge = np.abs(r["V"][p["base"]:p["base"] + p["m"]] - (Va + (Vb - Va) * t[:, None])).max()
        row["new_vertex_off_edge_file_units"] = float(on_edge)
        # Weights.
        for bone, w in r["clusters"].items():
            old = c["clusters"].get(bone, {})
            gained = {k: v for k, v in w.items() if k not in old}
            if any(w.get(k) != v for k, v in old.items()):
                failed.append(f"cluster {bone} changed an old weight")
            mine = set(range(p["base"], p["base"] + p["m"]))
            if bone == f"hand_{side}":
                if set(gained) & set(range(nv, base)) != mine or any(gained[k] != 1.0 for k in mine):
                    failed.append(f"hand_{side} does not gain exactly its new vertices at 1.0")
            elif set(gained) & mine:
                failed.append(f"cluster {bone} gained paw {side}'s new vertices")
        # The empty fist: old entries kept; new ones at the rule, through the fitted transform.
        A, tt, resid = fit_affine(d["skin_verts"], r["V"][p["off"]:p["off"] + n])
        row["mesh_from_world_fit_residual_file_units"] = resid
        Ainv = np.linalg.inv(A)
        to_world = lambda x: (x - tt) @ Ainv.T  # noqa: E731
        for name, deltas in r["shapes"].items():
            old = c["shapes"][name]
            if any(deltas.get(k) != v for k, v in old.items()):
                failed.append(f"shape {name} changed an old entry")
            new_here = {k: v for k, v in deltas.items() if p["base"] <= k < p["base"] + p["m"]}
            if name != f"PawEmpty_{side}":
                if new_here:
                    failed.append(f"shape {name} moves paw {side}'s new vertices")
                continue
            idx = np.arange(p["base"], p["base"] + p["m"])
            delta = np.array([new_here.get(int(k), (0.0, 0.0, 0.0)) for k in idx])
            moved_world = to_world(r["V"][idx] + delta)
            skel = PL.rebuild(side, manifest["third_person"]["paws"]["by_side"])["skeleton"]
            rule = TPP.empty_points(to_world(r["V"][idx]), skel)
            err = float(np.abs(moved_world - rule).max())
            row["new_vertex_morph_vs_rule_m"] = err
            row["new_vertices_moved_by_morph"] = int(len(new_here))
            if err > MORPH_TOL_M:
                failed.append(f"paw {side}: the new vertices' empty fist is {err} m from the rule")
        # The cut skin from the file: topology and UV folds (world positions through the fit).
        T = np.array(got, np.int64)
        local = np.unique(T)
        remap = {v: i for i, v in enumerate(local.tolist())}
        Tl = np.vectorize(remap.get)(T)
        row["topology"] = MS.topology(Tl, len(local))
        if row["topology"]["edges_not_shared_by_two"] or not row["topology"]["every_edge_has_its_opposite"] or row["topology"]["euler"] != 0:
            failed.append(f"paw {side}: the cut skin's topology {row['topology']}")
        world = to_world(r["V"][local])
        st = MS.stretch_report(world, Tl, r["uv"][cc].reshape(-1, 3, 2), {"all": np.ones(len(Tl), bool)})
        row["uv_flipped_faces"] = st["flipped_faces"]
        if st["flipped_faces"]:
            failed.append(f"paw {side}: {st['flipped_faces']} UV faces folded in the file")
        checks[side] = row
        face_at += F2
        tris_all.append(T)
    report["checks"] = checks
    report["failed"] = failed
    with open(out_path, "x") as fh:
        json.dump(report, fh, indent=1)
    print("NYAAKOTO_R4_FBX_CHECK " + json.dumps({"failed": failed, "control_vs_production": len(d_prod),
                                                "candidate_differences": len(d_cand),
                                                "outside_the_paws": len(report["candidate_vs_control"]["outside_the_paws"]),
                                                "kept_normals_deg_max": checks["kept_normals_deg"]["max"]}))
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
