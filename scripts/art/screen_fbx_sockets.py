"""Screen FBX files for SOCKET_ empties that UE 5.8 would import turned or scaled. CPU only.

Run: python3 scripts/art/screen_fbx_sockets.py [--json out.json] [file.fbx ...]
With no files, it screens every tracked FBX that holds a SOCKET_ node.

**The rule.** Each socket goes through fbx_unreal_sockets.interchange, UE 5.8 Interchange's rule. The rule is
calibrated on one real import: root's 0eb8c5e readback of the drone's fc0858a9. For any other file the result is a
prediction until a real import reads it back.

**A socket passes when Unreal would import it:**
- at scale 1 within 1e-4, SoraViewmodelComponent's admission tolerance;
- on the axes its own geometry carries, its authored axes, within 0.01 deg.

It exits 1 when any socket fails, and 2 when a file cannot be read (for example, an LFS pointer).
"""

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fbx_unreal_sockets as F  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SCALE_TOL = 1e-4
TURN_TOL_DEG = 0.01


def angle_deg(a, b):
    """The angle between two vectors: atan2 of the cross and dot products, well conditioned near 0 and 180 deg."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    return math.degrees(math.atan2(float(np.linalg.norm(np.cross(a, b))), float(np.dot(a, b))))


def screen(path):
    """One row per socket of an FBX file (screen_scene)."""
    return screen_scene(F.read_fbx(path), path)


def screen_scene(scene, path):
    """One row per socket: Unreal's transform under Interchange's rule, beside the authored (carried) axes."""
    result = F.interchange(scene)
    c = np.eye(4)
    c[:3, :3] = F.conversion(scene["axes"])
    rows = []
    for name, s in sorted(result["sockets"].items()):
        carried = (F.MIRROR @ c @ F.global_matrix(scene["nodes"], "SOCKET_" + name))[:3, :3]
        authored_x, authored_z = carried[:, 0] / np.linalg.norm(carried[:, 0]), carried[:, 2] / np.linalg.norm(carried[:, 2])
        authored_y = np.cross(authored_z, authored_x)            # Unreal's right: Y = Z x X (FRotationMatrix rows)
        turned = max(angle_deg(s["x"], authored_x), angle_deg(s["y"], authored_y), angle_deg(s["z"], authored_z))
        scale_off = float(np.abs(s["scale"] - 1.0).max())
        rows.append({"file": str(path), "socket": name, "position_cm": s["position_cm"].round(5).tolist(),
                     "scale": s["scale"].round(7).tolist(), "forward": s["x"].round(7).tolist(),
                     "right": s["y"].round(7).tolist(), "z": s["z"].round(7).tolist(),
                     "authored_forward": authored_x.round(7).tolist(), "authored_right": authored_y.round(7).tolist(),
                     "authored_z": authored_z.round(7).tolist(), "turned_deg": round(turned, 4),
                     "scale_off": round(scale_off, 7), "axes": {k: list(v) for k, v in scene["axes"].items()},
                     "passes": bool(scale_off < SCALE_TOL and turned < TURN_TOL_DEG)})
    return rows


def socketed_files():
    """Every tracked FBX whose bytes hold a SOCKET_ node; LFS pointers are returned too, to be reported."""
    out = subprocess.run(["git", "ls-files", "*.fbx"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    found = []
    for rel in out.split():
        path = ROOT / rel
        data = path.read_bytes() if path.is_file() else b""
        if data[:4] == b"vers" or b"SOCKET_" in data:
            found.append(path)
    return found


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("files", nargs="*")
    ap.add_argument("--json")
    args = ap.parse_args(argv)
    files = [Path(f).resolve() for f in args.files] or socketed_files()
    rows, unreadable = [], []
    for path in files:
        if path.read_bytes()[:4] == b"vers":
            unreadable.append({"file": str(path), "why": "an LFS pointer, not the file"})
            continue
        try:
            rows.extend(screen(path))
        except (ValueError, KeyError) as e:
            unreadable.append({"file": str(path), "why": str(e)})
    for r in rows:
        rel = Path(r["file"]).relative_to(ROOT) if Path(r["file"]).is_relative_to(ROOT) else r["file"]
        print(f"{'pass' if r['passes'] else 'FAIL'}  {str(rel):64s} {r['socket']:14s} scale {max(r['scale']):9.4f}  "
              f"turned {r['turned_deg']:6.2f} deg")
    for u in unreadable:
        print(f"UNREAD {u['file']}: {u['why']}")
    failing = [r for r in rows if not r["passes"]]
    summary = {"files": len({r["file"] for r in rows}), "sockets": len(rows), "failing_sockets": len(failing),
               "failing_files": len({r["file"] for r in failing}), "unreadable": len(unreadable)}
    print("SCREEN_FBX_SOCKETS " + json.dumps(summary))
    if args.json:
        Path(args.json).write_text(json.dumps({"summary": summary, "rows": rows, "unreadable": unreadable}, indent=1) + "\n")
    return 2 if unreadable else (1 if failing else 0)


if __name__ == "__main__":
    sys.exit(main())
