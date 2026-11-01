"""Check the r4 matched views (render_nyaakoto_r4_comparison.py) on the host, and measure them. No file is changed.

For each view it reads, from the run:
- the s132 baseline, re-shot;
- s133's authored-normal candidate;
- the r4 paw candidate;
and, from earlier runs:
- s132's own original of that view;
- s134's two originals where s134 shot the view.

**Checks:**
- **Files:** every file manifest.json lists exists at its SHA-256, a PNG at the recorded resolution. s132's and s134's
  originals are at their own manifests' SHA-256.
- **Gates:** each shot recorded its gates before and after the image:
  - grips within 1 cm and 2 deg;
  - morphs as set;
  - the view's forced and predicted LOD;
  - a camera replaying s132's within 0.001 cm and 0.001 deg.

**Measures** (no judgement of the art). Each pair reports:
- the share of pixels whose largest channel difference exceeds 8 of 255;
- the mean absolute difference, and its 99th percentile.

The pairs:
- **repeat:** the baseline against s132's original (run-to-run noise of Lumen, TSR and the capture). Where s134 shot
  the view, also both s143 variants against s134's.
- **normals:** s133's candidate against the baseline (as s134 measured it).
- **paws:** r4 against s133's candidate. Only the paw surface differs between them, so this is the r4 change alone.
- **total:** r4 against the baseline.

**Where the paw change falls.** Both paws' skins are projected through the view's camera, in its pose and state (the
s136 baseline skins; the cut skin is the same surface). Each mask is dilated by MASK_GROW_PX to take in the strands.
The paws pair's changed pixels are counted inside and outside the masks; the repeat's outside share is beside them.

**Difference maps** (each pixel's largest channel difference times 8) are written beside the out file. Side-by-side
crops of each paw view (baseline | s133 | r4) go to <out>_crops. They are presentation only, cut from the originals,
which are not changed.

Run (host: /usr/bin/python3 has PIL, numpy and scipy):
    /usr/bin/python3 scripts/art/check_nyaakoto_r4_comparison.py <s143 dir> <s132 dir> <s134 dir> <out.json>
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import binary_dilation

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import diagnose_nyaakoto_paw_boundaries as D  # noqa: E402
import measure_paw_surface_prototypes as MS  # noqa: E402
import nyaakoto_tp_paws as TPP  # noqa: E402
import plan_nyaakoto_tp_review as PL  # noqa: E402

CHANGED_LEVEL = 8
POSE_TOL_CM, POSE_TOL_DEG = 1.0, 2.0
CAMERA_TOL = 1e-3
VARIANTS = ("baseline", "authored_normals", "r4_paws")
MASK_SCALE = 4                 # the paw masks are drawn at a quarter of the resolution, then scaled up
MASK_GROW_PX = 24              # full-resolution pixels: strands and anti-aliasing beyond the skin's outline
CROP_PAD_PX = 60


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rgb(path):
    with Image.open(path) as im:
        return np.asarray(im.convert("RGB"), dtype=np.int16), im.size, im.format


def pair(a, b, mask=None):
    d = np.abs(a - b)
    m = d.max(-1)
    row = {"changed_share": round(float((m > CHANGED_LEVEL).mean()), 6), "mean_abs_diff": round(float(d.mean()), 4),
           "p99_abs_diff": round(float(np.percentile(m, 99)), 2)}
    if mask is not None:
        changed = m > CHANGED_LEVEL
        row["changed_inside_paws_px"] = int((changed & mask).sum())
        row["changed_outside_paws_px"] = int((changed & ~mask).sum())
        row["outside_share_of_outside"] = round(float((changed & ~mask).sum() / max((~mask).sum(), 1)), 7)
    return row, m


def gate_problems(name, row):
    problems = []
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
    return problems


def paw_mask(paws, record, shot, cam, width, height):
    """Both paws' skins projected through the camera at the shot's pose and state, dilated: a full-resolution mask."""
    w, h = width // MASK_SCALE, height // MASK_SCALE
    mask = np.zeros((h, w), bool)
    for side, m in paws.items():
        verts = TPP.empty_points(m["verts"], m["skeleton"]) if shot["state"] == "empty" else m["verts"]
        pts = D.posed_ue(dict(m, verts=verts), side, record, shot["pose"])
        tris = np.asarray(m["tris"])
        _, drawn = MS.checker_render(pts, tris, np.zeros((len(tris), 3, 2)), np.zeros(len(tris), bool), cam, w, h)
        mask |= drawn
    full = np.repeat(np.repeat(mask, MASK_SCALE, 0), MASK_SCALE, 1)[:height, :width]
    return binary_dilation(full, iterations=MASK_GROW_PX)


def main():
    comparison, s132, s134, out = (Path(a) for a in sys.argv[1:5])
    if out.exists():
        raise SystemExit(f"{out} exists")
    man = json.loads((comparison / "manifest.json").read_text())
    base = json.loads((s132 / "manifest.json").read_text())
    m134 = json.loads((s134 / "manifest.json").read_text())
    record = json.loads(PL.MANIFEST.read_text())
    width, height = man["resolution"]
    problems, views = [], {}
    if man["variants_order"] != list(VARIANTS):
        problems.append(f"variants {man['variants_order']}")
    for name, digest in man["files"].items():
        p = comparison / name
        if not p.is_file() or sha256(p) != digest:
            problems.append(f"{name} is missing or not at its SHA-256")
    for name, row in man["shots"].items():
        problems += gate_problems(name, row)
    if len(man["files"]) != len(man["views"]) * len(VARIANTS):
        problems.append(f"{len(man['files'])} files for {len(man['views'])} views")
    paws = {side: PL.rebuild(side, record["third_person"]["paws"]["by_side"]) for side in ("R", "L")}
    maps = out.parent / (out.stem + "_maps")
    crops = out.parent / (out.stem + "_crops")
    maps.mkdir(exist_ok=False)
    crops.mkdir(exist_ok=False)
    for view in man["views"]:
        files = {v: comparison / f"{view}__{v}.png" for v in VARIANTS}
        files["s132"] = s132 / f"{view}.png"
        if sha256(files["s132"]) != base["files"][f"{view}.png"]:
            problems.append(f"s132's {view}.png is not at its recorded SHA-256")
        in134 = f"{view}__baseline.png" in m134["files"]
        if in134:
            for v in ("baseline", "authored_normals"):
                files[f"s134_{v}"] = s134 / f"{view}__{v}.png"
                if sha256(files[f"s134_{v}"]) != m134["files"][f"{view}__{v}.png"]:
                    problems.append(f"s134's {view}__{v}.png is not at its recorded SHA-256")
        imgs = {}
        for k, p in files.items():
            a, size, fmt = rgb(p)
            if fmt != "PNG" or tuple(size) != (width, height):
                problems.append(f"{p.name}: {fmt} {size}")
            imgs[k] = a
        shot = man["shots"][f"{view}__r4_paws"]["state"]
        cam = man["shots"][f"{view}__r4_paws"]["camera_from_s132"]     # s132's record: location, rotation, field of view
        mask = paw_mask(paws, record, shot, cam, width, height)
        rows = {}
        rows["repeat_baseline_vs_s132"], rm = pair(imgs["baseline"], imgs["s132"], mask)
        rows["normals_s133_vs_baseline"], nm = pair(imgs["authored_normals"], imgs["baseline"], mask)
        rows["paws_r4_vs_s133"], pm = pair(imgs["r4_paws"], imgs["authored_normals"], mask)
        rows["total_r4_vs_baseline"], tm = pair(imgs["r4_paws"], imgs["baseline"], mask)
        if in134:
            rows["repeat_baseline_vs_s134"], _ = pair(imgs["baseline"], imgs["s134_baseline"], mask)
            rows["repeat_s133_vs_s134"], _ = pair(imgs["authored_normals"], imgs["s134_authored_normals"], mask)
        for label, m in (("repeat", rm), ("normals", nm), ("paws", pm), ("total", tm)):
            Image.fromarray(np.clip(m * 8, 0, 255).astype(np.uint8)).save(maps / f"{view}__{label}.png")
        Image.fromarray((mask * 255).astype(np.uint8)).save(maps / f"{view}__paw_mask.png")
        rows["paw_mask_share"] = round(float(mask.mean()), 5)
        views[view] = rows
        if view.startswith("paw_"):
            ys, xs = np.nonzero(mask)
            box = (max(0, xs.min() - CROP_PAD_PX), max(0, ys.min() - CROP_PAD_PX),
                   min(width, xs.max() + CROP_PAD_PX), min(height, ys.max() + CROP_PAD_PX))
            strip = np.concatenate([imgs[v][box[1]:box[3], box[0]:box[2]] for v in VARIANTS], 1)
            Image.fromarray(strip.astype(np.uint8)).save(crops / f"{view}__baseline_s133_r4.png")
    result = {"comparison": str(comparison), "manifest_sha256": sha256(comparison / "manifest.json"),
              "s132_manifest_sha256": sha256(s132 / "manifest.json"), "s134_manifest_sha256": sha256(s134 / "manifest.json"),
              "script_sha256": sha256(__file__), "changed_level": CHANGED_LEVEL, "mask_grow_px": MASK_GROW_PX,
              "views": views, "maps": {p.name: sha256(p) for p in sorted(maps.glob("*.png"))},
              "crops": {p.name: sha256(p) for p in sorted(crops.glob("*.png"))}, "problems": problems}
    out.write_text(json.dumps(result, indent=1) + "\n")
    summary = {v: {"paws_changed_inside": r["paws_r4_vs_s133"]["changed_inside_paws_px"],
                   "paws_changed_outside": r["paws_r4_vs_s133"]["changed_outside_paws_px"],
                   "repeat_changed_outside": r["repeat_baseline_vs_s132"]["changed_outside_paws_px"]} for v, r in views.items()}
    print("NYAAKOTO_R4_COMPARISON_CHECK " + json.dumps({"problems": problems, "views": summary}))


if __name__ == "__main__":
    main()
