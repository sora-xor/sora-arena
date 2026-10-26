"""Compare retained Unreal weapon render arrays with their exact source FBXs, on CPU.

Uses Blender's installed FBX parser without launching Blender or changing assets.
Preserves triangle winding and UV seams when matching split/reordered vertices.
"""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "unreal")]
import fbx_unreal_sockets as F
import runtime_weapon_review as R
import weapon_socket_gates as G

ROOT = HERE.parents[1]


def source_section(path):
    scene = F.read_fbx(path)
    transformed = F.interchange(scene)["vertices"]
    R.require(len(transformed) == 1, "expected a single source mesh")
    name, points = next(iter(transformed.items()))
    root, _ = F.parser().parse(str(path))
    geometries = [g for g in F._child(root, b"Objects").elems if g.id == b"Geometry" and g.props[2] == b"Mesh"]
    R.require(len(geometries) == 1, "ambiguous geometry")
    geometry = geometries[0]
    indices = np.array(F._child(geometry, b"PolygonVertexIndex").props[0], dtype=np.int64)
    R.require(len(indices) % 3 == 0 and np.all(indices.reshape(-1, 3)[:, :2] >= 0) and
              np.all(indices.reshape(-1, 3)[:, 2] < 0), "nontriangulated source")
    indices = np.where(indices < 0, -indices-1, indices)
    R.require(np.all((indices >= 0) & (indices < len(points))), "invalid source indices")

    def layer(kind, field, width):
        item = next(e for e in geometry.elems if e.id == kind and e.props[0] == 0)
        R.require(F._child(item, b"MappingInformationType").props[0] == b"ByPolygonVertex", "unmodelled source mapping")
        values = np.array(F._child(item, field).props[0], float).reshape(-1, width)
        reference = F._child(item, b"ReferenceInformationType").props[0]
        if reference == b"IndexToDirect":
            values = values[np.array(F._child(item, field+b"Index").props[0], dtype=np.int64)]
        else:
            R.require(reference == b"Direct", "unmodelled source reference")
        R.require(len(values) == len(indices) and np.isfinite(values).all(), "invalid source corner data")
        return values

    basis = F.MIRROR[:3, :3] @ F.conversion(scene["axes"]) @ F.global_matrix(scene["nodes"], name)[:3, :3]
    normals = layer(b"LayerElementNormal", b"Normals", 3) @ np.linalg.inv(basis)
    tangents = layer(b"LayerElementTangent", b"Tangents", 3) @ basis.T
    for values in (normals, tangents):
        lengths = np.linalg.norm(values, axis=1)
        valid = lengths > 1e-12
        values[valid] /= lengths[valid, None]
    uv = layer(b"LayerElementUV", b"UV", 2)
    uv[:, 1] = 1.0 - uv[:, 1]  # Unreal's texture origin is the top left.
    corners = np.arange(len(indices)).reshape(-1, 3)
    if np.linalg.det(basis) < 0:
        corners = corners[:, [2, 1, 0]]
    return {"positions": points[indices].tolist(), "indices": corners.ravel().tolist(),
            "normals": normals.tolist(), "tangents": tangents.tolist(), "uvs": uv.tolist()}


def compare(source, actual):
    for label, section in (("source", source), ("Unreal", actual)):
        R.require(bool(section["positions"]) and bool(section["indices"]), label + " empty section")
        R.require(not G.section_problems(section), label + " malformed section")
    pairing = G.corner_pairs(source, actual, tol=.001)
    R.require(pairing is not None, "triangle geometry or winding changed")
    pairs, method = pairing
    result = {"corners": len(pairs), "pairing": method, "position_cm": 0.0, "uv": 0.0,
              "normal_component": 0.0, "tangent_degrees": 0.0, "degenerate_mismatches": 0}
    for i, j in pairs:
        result["position_cm"] = max(result["position_cm"], math.dist(source["positions"][i], actual["positions"][j]))
        result["uv"] = max(result["uv"], math.dist(source["uvs"][i], actual["uvs"][j]))
        for key in ("normals", "tangents"):
            a, b = source[key][i], actual[key][j]
            va, vb = math.dist(a, [0, 0, 0]) >= G.DEGENERATE, math.dist(b, [0, 0, 0]) >= G.DEGENERATE
            result["degenerate_mismatches"] += int(va != vb)
            if key == "normals":
                result["normal_component"] = max(result["normal_component"], max(abs(x-y) for x, y in zip(a, b)))
            elif va and vb:
                result["tangent_degrees"] = max(result["tangent_degrees"], G._angle_deg(a, b))
    # Unreal stores the basis as FPackedNormal; allow at most two component steps
    # for source-to-packed normals and two degrees for its tangent readback.
    limits = {"position_cm": .001, "uv": .000002, "normal_component": 2/127,
              "tangent_degrees": 2.0, "degenerate_mismatches": 0}
    failed = [f"{key}={result[key]} > {limit}" for key, limit in limits.items() if result[key] > limit]
    return result, failed


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("readback", type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    plan, _ = R.source_plan(ROOT)
    report = json.loads(args.readback.read_text())
    R.require(tuple(sorted(report["meshes"])) == R.ASSETS and report["envelope_sha256"] == R.ENVELOPE_SHA256,
              "readback inventory/source mismatch")
    result = {"readback_sha256": R.sha(args.readback.read_bytes()), "envelope_sha256": R.ENVELOPE_SHA256,
              "verifier_sha256": R.sha(Path(__file__).read_bytes()), "meshes": {}, "failures": []}
    for name, expected in plan["assets"].items():
        row = report["meshes"][name]
        entry = row["render_arrays"]
        path = args.readback.parent / entry["file"]
        R.require(path.resolve().parent == args.readback.resolve().parent, "render evidence path escaped")
        raw = path.read_bytes()
        R.require(len(raw) == entry["bytes"] and hashlib.sha256(raw).hexdigest() == entry["sha256"], "changed render evidence")
        lods = json.loads(gzip.decompress(raw))
        R.geometry_readback(expected, lods, row["screen_sizes"])
        details = []
        for index, (lod, reference) in enumerate(zip(lods, expected["lods"])):
            try:
                measured, failures = compare(source_section(ROOT / reference["file"]), lod["sections"][0])
                details.append({"lod": index, "source_sha256": reference["sha256"], **measured, "failures": failures})
                result["failures"].extend(f"{name} LOD{index}: {f}" for f in failures)
            except Exception as error:
                result["failures"].append(f"{name} LOD{index}: {error}")
        result["meshes"][name] = details
        print(f"{name}: {len(details)} LOD comparisons; {len(result['failures'])} failures so far", flush=True)
    result["passed"] = not result["failures"]
    with args.output.open("x") as f:
        f.write(json.dumps(result, indent=2, allow_nan=False)+"\n")
    R.require(result["passed"], "source geometry comparison failed; see " + str(args.output))


if __name__ == "__main__":
    main()
