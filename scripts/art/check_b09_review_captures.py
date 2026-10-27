"""Check a b09 socket-pose review capture run (render_b09_workshop_review.py) on the host, before anyone reads it.

For the run's manifest.json:
- every requested shot has its PNG, at the manifest's SHA-256 and the camera's resolution;
- every camera is the world's 94 deg, at its image's aspect;
- every placed candidate drew its candidate materials in the capture's own editor;
- the inputs are the committed spec and the named import readback, which has no problems;
- no frame is unreadable: a median display luma under 0.02 (crushed) or over a fifth of its pixels near saturation.
The luma figures are display-output statistics (analyze_capture_luminance.stats). They say whether a frame can be
read, not whether its light or materials are right.

Prints B09_REVIEW_CHECK <json>; exits 1 on any problem.

Run (host): /usr/bin/python3 scripts/art/check_b09_review_captures.py Saved/B09Workshop/Review/<run> [record.json]
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import analyze_capture_luminance as L  # noqa: E402

SPEC = "docs/art-direction/data/b09_workshop_craft_spec.json"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    run = (ROOT / sys.argv[1]).resolve()
    record_path = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else None
    man = json.loads((run / "manifest.json").read_text())
    problems, rows = [], {}
    if sorted(man["files"]) != sorted(f"{s}.png" for s in man["shots_requested"]):
        problems.append(f"files {sorted(man['files'])} are not the requested shots")
    for name in man["shots_requested"]:
        path, shot = run / f"{name}.png", man["shots"].get(name)
        if shot is None or not path.is_file():
            problems.append(f"{name}: no shot record or no file")
            continue
        if sha256(path) != man["files"].get(path.name):
            problems.append(f"{name}: not the manifest's file")
        cam = shot["camera"]
        w, h = cam["resolution"]
        px = L.read_png(path)
        st = L.stats(px)
        rows[name] = {"station": shot["station"], "state": shot["state"], "camera": cam, "stats": st}
        if st["size"] != [w, h]:
            problems.append(f"{name}: {st['size']}, the camera asked {w}x{h}")
        if abs(cam["field_of_view_deg"] - 94.0) > 1e-4 or abs(cam["aspect_ratio"] - w / h) > 1e-4:
            problems.append(f"{name}: field of view {cam['field_of_view_deg']}, aspect {cam['aspect_ratio']}")
        if st["luma_p50"] < 0.02 or st["near_saturated_pct"] > 20.0:
            problems.append(f"{name}: unreadable (median luma {st['luma_p50']}, {st['near_saturated_pct']}% near saturation)")
    mats = f"{man.get('candidates')}/Materials/"
    for mesh, drawn in man.get("bindings", {}).items():
        if not drawn or any(m is None or not m.startswith(mats) for m in drawn):
            problems.append(f"{mesh} drew {drawn}")
    if not man.get("bindings"):
        problems.append("no bindings recorded")
    spec_sha = man["inputs"].get(SPEC)
    if spec_sha != sha256(ROOT / SPEC):
        problems.append("the run was made from another spec")
    unreal_inputs = [k for k in man["inputs"] if k.startswith("Saved/B09Workshop/Unreal/")]
    readback = next((k for k in unreal_inputs if not k.endswith("_review.json")), None)
    review = next((k for k in unreal_inputs if k.endswith("_review.json")), None)
    if readback is None or sha256(ROOT / readback) != man["inputs"][readback]:
        problems.append(f"the readback {readback} is not the one named")
    else:
        rb_problems = json.loads((ROOT / readback).read_text())["problems"]
        if rb_problems:                 # drawn only with a host review that explains every one
            rv = json.loads((ROOT / review).read_text()) if review and sha256(ROOT / review) == man["inputs"][review] else None
            if rv is None or rv["unexplained"] or sorted(rv["explained"]) != sorted(rb_problems) or \
                    rv["readback_sha256"] != man["inputs"][readback]:
                problems.append(f"the readback {readback} has problems that no named review explains")
    out = {"run": str(run.relative_to(ROOT)), "manifest_sha256": sha256(run / "manifest.json"), "checker_sha256": sha256(__file__),
           "shots": len(rows), "ev100": man.get("ev100"), "problems": problems,
           "luma_p50": {k: r["stats"]["luma_p50"] for k, r in rows.items()},
           "median_display_stops": {k: r["stats"]["median_display_stops"] for k, r in rows.items()}, "rows": rows,
           "scope": "display-output statistics of socket-pose review captures: readability only, not light, material "
                    "or hand-contact acceptance"}
    text = json.dumps(out, indent=1)
    if record_path is not None:
        with open(record_path, "x") as fh:
            fh.write(text + "\n")
    print("B09_REVIEW_CHECK " + json.dumps({k: out[k] for k in ("run", "shots", "ev100", "problems", "luma_p50")}, indent=1))
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
