"""Measure the selected weapon FBXs with Blender's installed parser, without launching Blender.

Writes source-pinned bounds/triangle/UV envelopes for each authored LOD. --check
compares the committed output. Does not update runtime_weapon_review's approval hash.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "unreal"))
import fbx_unreal_sockets as F
import runtime_weapon_review as R
import verify_weapon_review_geometry as V

ROOT = HERE.parents[1]


def build(root):
    root = Path(root).resolve()
    def entry(relative):
        return {"file": relative, "sha256": hashlib.sha256((root / relative).read_bytes()).hexdigest()}
    manifest = R.SOURCE + "/manifest.json"
    listed = {e["file"]: e["sha256"] for e in json.loads((root / manifest).read_text())["files"]}
    plan = {"schema": "sora.weapon-review.v1", "source_manifest": entry(manifest), "kits": {}, "assets": {}}
    for path in sorted((root / R.SOURCE).glob("W*/build_record.json")):
        record = json.loads(path.read_text())
        if record["id"] not in R.KIT_IDS:
            continue
        relative = str(path.relative_to(root))
        R.require(entry(relative)["sha256"] == listed[relative], "unlisted record")
        plan["kits"][record["key"]] = entry(relative)
        for name, asset in record["assets"].items():
            R.require(name in R.ASSETS, "unreviewed asset: " + name)
            rows = []
            for lod in asset["lods"]:
                R.require(entry(lod["file"])["sha256"] == lod["sha256"] == listed[lod["file"]], "changed LOD")
                fbx = root / lod["file"]
                arrays, vertices = F.geometry_arrays(fbx), F.interchange(F.read_fbx(fbx))["vertices"]
                R.require(len(arrays) == len(vertices) == 1, "expected one mesh")
                points, data = next(iter(vertices.values())), next(iter(arrays.values()))
                indices = data["PolygonVertexIndex"]
                R.require(len(indices) % 3 == 0 and np.all(indices.reshape(-1, 3)[:, 2] < 0), "nontriangulated FBX")
                R.require(len(indices) // 3 == lod["triangles"] and np.isfinite(points).all(), "invalid source geometry")
                uv_channels = sum(k.startswith("LayerElementUV[") and k.endswith(".UV") for k in data)
                R.require(uv_channels == 2, "expected authored UV0/UVMetric")
                uvs = np.array(V.source_section(fbx)["uvs"])
                rows.append({**lod, "min_cm": points.min(axis=0).tolist(), "max_cm": points.max(axis=0).tolist(),
                             "uv_channels": uv_channels, "uv_min": uvs.min(axis=0).tolist(), "uv_max": uvs.max(axis=0).tolist(),
                             "atlas_uv_outside_corners": int(np.any((uvs < 0) | (uvs > 1), axis=1).sum())})
            plan["assets"][name] = {"kit": record["key"], "lods": rows, "screen_sizes": asset["screen_sizes"]}
    R.require(tuple(sorted(plan["assets"])) == R.ASSETS, "missing assets")
    return plan


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    data = (json.dumps(build(ROOT), indent=2, allow_nan=False) + "\n").encode()
    path = ROOT / R.ENVELOPE
    if args.check:
        R.require(path.read_bytes() == data, "stale geometry envelope")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    print(f"20 meshes / 60 LOD envelopes: {hashlib.sha256(data).hexdigest()}")


if __name__ == "__main__":
    main()
