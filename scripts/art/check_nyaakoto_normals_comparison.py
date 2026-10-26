"""Check root's authored-normal comparison (render_nyaakoto_normals_comparison.py) on the host, and measure it.

For each view it reads three originals:
- **the baseline**, the s132 asset re-shot in this run;
- **the authored-normal candidate**, shot right after it in the same level and light;
- **s132's own original** of that view.

What it checks, without changing a file:
- **Files.** Every file manifest.json lists exists at its SHA-256, a PNG at the recorded resolution. s132's original is
  at s132's recorded SHA-256.
- **Gates.** Each shot recorded its gates before and after the image: grips within 1 cm and 2 deg, morphs as set, the
  forced and predicted LOD of its view. Its camera replayed s132's within 0.001 cm and 0.001 deg.

What it measures (no judgement of the art):
- **Repeat:** the baseline against s132's original, which is the run-to-run noise of Lumen, TSR and the capture.
- **Effect:** the candidate against the baseline.
- **For each pair:** the share of pixels whose largest channel difference exceeds 8 of 255, the mean absolute
  difference, its 99th percentile, and the effect's changed share over the repeat's.
- **Difference maps:** written as PNG beside the out file, each pixel's largest channel difference times 8.

Run (host: /usr/bin/python3 has PIL and numpy):
    /usr/bin/python3 scripts/art/check_nyaakoto_normals_comparison.py <comparison dir> <s132 dir> <out.json>
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

CHANGED_LEVEL = 8
POSE_TOL_CM, POSE_TOL_DEG = 1.0, 2.0
CAMERA_TOL = 1e-3


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rgb(path):
    with Image.open(path) as im:
        return np.asarray(im.convert("RGB"), dtype=np.int16), im.size, im.format


def pair(a, b):
    d = np.abs(a - b)
    m = d.max(-1)
    return {"changed_share": round(float((m > CHANGED_LEVEL).mean()), 5), "mean_abs_diff": round(float(d.mean()), 4),
            "p99_abs_diff": round(float(np.percentile(m, 99)), 2)}, m


def check(comparison, s132, out):
    man = json.loads((comparison / "manifest.json").read_text())
    base = json.loads((s132 / "manifest.json").read_text())
    width, height = man["resolution"]
    problems, views = [], {}
    for name, digest in man["files"].items():
        p = comparison / name
        if not p.is_file() or sha256(p) != digest:
            problems.append(f"{name} is missing or not at its SHA-256")
    for name, row in man["shots"].items():
        for key in ("gates", "gates_after"):
            g = row.get(key)
            if g is None:
                problems.append(f"{name}: no {key}")
                continue
            for sock, s in g["sockets"].items():
                if s["error_cm"] > POSE_TOL_CM or s["error_deg"] > POSE_TOL_DEG:
                    problems.append(f"{name} {key}: {sock} {s['error_cm']:.4f} cm {s['error_deg']:.3f} deg")
            want = 1.0 if row["state"]["state"] == "empty" else 0.0
            if any(abs(v - want) > 1e-6 for v in g["morphs"].values()):
                problems.append(f"{name} {key}: morphs {g['morphs']}")
            if g["forced_lod"] != row["state"]["lod"] + 1 or g["predicted_lod"] != row["state"]["lod"]:
                problems.append(f"{name} {key}: LOD forced {g['forced_lod']} predicted {g['predicted_lod']}")
        if row["camera_drift"]["location_cm"] > CAMERA_TOL or row["camera_drift"]["rotation_deg"] > CAMERA_TOL:
            problems.append(f"{name}: camera drift {row['camera_drift']}")
    maps = out.parent / (out.stem + "_maps")
    maps.mkdir(exist_ok=False)
    for view in man["views"]:
        files = {"baseline": comparison / f"{view}__baseline.png", "authored_normals": comparison / f"{view}__authored_normals.png",
                 "s132": s132 / f"{view}.png"}
        if sha256(files["s132"]) != base["files"][f"{view}.png"]:
            problems.append(f"s132's {view}.png is not at its recorded SHA-256")
        imgs = {}
        for k, p in files.items():
            a, size, fmt = rgb(p)
            if fmt != "PNG" or tuple(size) != (width, height):
                problems.append(f"{p.name}: {fmt} {size}")
            imgs[k] = a
        repeat, repeat_map = pair(imgs["baseline"], imgs["s132"])
        effect, effect_map = pair(imgs["authored_normals"], imgs["baseline"])
        for label, m in (("repeat", repeat_map), ("effect", effect_map)):
            Image.fromarray(np.clip(m * 8, 0, 255).astype(np.uint8)).save(maps / f"{view}__{label}.png")
        views[view] = {"repeat_baseline_vs_s132": repeat, "effect_candidate_vs_baseline": effect,
                       "effect_over_repeat_changed_share": round(effect["changed_share"] / max(repeat["changed_share"], 1e-6), 2)}
    return {"comparison": str(comparison), "manifest_sha256": sha256(comparison / "manifest.json"),
            "s132_manifest_sha256": sha256(s132 / "manifest.json"), "views": views,
            "maps": {p.name: sha256(p) for p in sorted(maps.glob("*.png"))}, "problems": problems}


def main():
    comparison, s132, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    if out.exists():
        raise SystemExit(f"{out} exists")
    result = check(comparison, s132, out)
    out.write_text(json.dumps(result, indent=1) + "\n")
    print("NYAAKOTO_NORMALS_COMPARISON_CHECK " + json.dumps({"problems": result["problems"], "views": result["views"]}))


if __name__ == "__main__":
    main()
