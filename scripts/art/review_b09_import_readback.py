"""Explain an import readback's problems on the host, or refuse them (b09 candidates).

The import (import_b09_workshop_candidates.py) fails on any problem. This review allows one kind, exactly explained: a
mesh with fewer triangles than built because Unreal's static-mesh build removes degenerate triangles. A triangle is
degenerate when two of its corners are within THRESH_POINTS_ARE_SAME (0.00002 cm) in every component
(FVector::Equals), and the build drops it (bRemoveDegenerates).

The deviation counts as explained only if, for every mesh in the readback, Unreal's count is exactly the module's
built count less its degenerate triangles. Anything else is unexplained and refused. s147: the shells' sphere poles
are rings 1e-4 cm across, so each sphere loses 128 slivers of at most 4.6e-6 cm^2.

Writes a new review record and prints B09_READBACK_REVIEW <json>; exits 1 if anything is unexplained.

Run (host): /usr/bin/python3 scripts/art/review_b09_import_readback.py Saved/B09Workshop/Unreal/<readback>.json <new review>.json
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import b09_workshop_craft as B  # noqa: E402

THRESH_POINTS_ARE_SAME = 2e-5        # cm: UnrealMathUtility.h
COUNT = re.compile(r"^(SM_B09_\w+): (\d+) triangles, built (\d+)$")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def degenerate(mesh, thresh=THRESH_POINTS_ARE_SAME):
    """Per triangle: two corners equal within thresh in every component."""
    v = mesh.verts[mesh.tris]
    same = lambda a, b: (np.abs(a - b) <= thresh).all(1)  # noqa: E731
    return same(v[:, 0], v[:, 1]) | same(v[:, 1], v[:, 2]) | same(v[:, 2], v[:, 0])


def main():
    rb_path, out_path = ROOT / sys.argv[1], Path(sys.argv[2]).resolve()
    rb = json.loads(rb_path.read_text())
    build = ROOT / rb["build"]
    meshes = {n: m for n, m, *_ in B.candidates()}
    unexplained, explained, per_mesh = [], {}, {}
    if sha256(build / "manifest.json") != rb["build_manifest_sha256"]:
        unexplained.append("the readback names another build")
    for name, mesh in meshes.items():
        row = rb["meshes"].get(name)
        d = degenerate(mesh)
        v = mesh.verts[mesh.tris]
        area = 0.5 * np.linalg.norm(np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0]), axis=1)
        per_mesh[name] = {"built": int(len(mesh.tris)), "unreal": None if row is None else row["triangles"],
                          "degenerate": int(d.sum()),
                          "degenerate_max_area_cm2": float(area[d].max()) if d.any() else None,
                          "kept_min_area_cm2": float(area[~d].min())}
        if row is None or row["triangles"] != len(mesh.tris) - int(d.sum()):
            unexplained.append(f"{name}: Unreal has {None if row is None else row['triangles']} triangles, "
                               f"built {len(mesh.tris)} less {int(d.sum())} degenerate")
    for p in rb["problems"]:
        m = COUNT.match(p)
        if m and m.group(1) in per_mesh and int(m.group(3)) - int(m.group(2)) == per_mesh[m.group(1)]["degenerate"] > 0:
            explained[p] = (f"Unreal's build removed {per_mesh[m.group(1)]['degenerate']} degenerate triangles "
                            f"(corners within {THRESH_POINTS_ARE_SAME} cm), each at most "
                            f"{per_mesh[m.group(1)]['degenerate_max_area_cm2']:.2g} cm^2")
        else:
            unexplained.append(f"problem not explained: {p}")
    out = {"readback": str(rb_path.relative_to(ROOT)), "readback_sha256": sha256(rb_path), "reviewer_sha256": sha256(__file__),
           "module_sha256": sha256(B.__file__), "threshold_cm": THRESH_POINTS_ARE_SAME,
           "rule": "UE static-mesh build drops triangles with two corners equal within THRESH_POINTS_ARE_SAME per component",
           "explained": explained, "unexplained": unexplained,
           "meshes_with_degenerate": {n: r for n, r in per_mesh.items() if r["degenerate"]}, "meshes_checked": len(per_mesh)}
    with open(out_path, "x") as fh:
        json.dump(out, fh, indent=1)
        fh.write("\n")
    print("B09_READBACK_REVIEW " + json.dumps({k: out[k] for k in ("readback", "explained", "unexplained", "meshes_checked")}, indent=1))
    sys.exit(1 if unexplained else 0)


if __name__ == "__main__":
    main()
