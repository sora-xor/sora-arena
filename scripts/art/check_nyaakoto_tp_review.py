"""Check a third-person review capture's originals (render_nyaakoto_tp_review.py) on the host.

What it checks, without changing a file:
- **Files.** Every file manifest.json lists exists with its recorded SHA-256 and is a PNG at the recorded resolution.
  There is exactly one per shot the run was asked for.
- **Gates.** Each shot recorded its gates before and after the image: both grips within 1 cm and 2 deg of the stance
  targets, the morph weights of its state, and the forced and predicted LOD its name states.
- **The morph took.** A paw's holding and empty shots share a camera (the same location, rotation and field of view
  read back), and their images differ: more than 0.5% of the pixels change by more than 8 of 255 in some channel.
- **Not blank.** Every image's luminance varies (standard deviation above 2 of 255). Its shares of clipped black and
  white are reported.
- **Clear views.** Each chosen view says whether its sight line cleared the body; any that did not are listed with what
  blocked them.

It judges no art. The images are root's to review.

Run (host: /usr/bin/python3 has PIL and numpy):
    /usr/bin/python3 scripts/art/check_nyaakoto_tp_review.py <capture dir> <out.json> [manifest.partial.json]
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

CHANGED_LEVEL = 8            # of 255, in any channel
CHANGED_SHARE = 0.005
MIN_LUMA_STD = 2.0           # of 255
POSE_TOL_CM, POSE_TOL_DEG = 1.0, 2.0


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rgb(path):
    with Image.open(path) as im:
        return np.asarray(im.convert("RGB"), dtype=np.int16), im.size, im.format


def gate_problems(name, shot, gates):
    out = []
    for sock, row in gates["sockets"].items():
        if row["error_cm"] > POSE_TOL_CM or row["error_deg"] > POSE_TOL_DEG:
            out.append(f"{name}: {sock} {row['error_cm']:.4f} cm, {row['error_deg']:.3f} deg")
    weight = 1.0 if shot["state"] == "empty" else 0.0
    if any(abs(v - weight) > 1e-6 for v in gates["morphs"].values()):
        out.append(f"{name}: morphs {gates['morphs']}, want {weight}")
    if gates["forced_lod"] != shot["lod"] + 1 or gates["predicted_lod"] != shot["lod"]:
        out.append(f"{name}: forced LOD {gates['forced_lod']}, predicted {gates['predicted_lod']}")
    return out


def check(capture, manifest_name="manifest.json"):
    manifest = json.loads((capture / manifest_name).read_text())
    width, height = manifest["resolution"]
    problems, files, images = [], {}, {}
    requested = manifest["shots_requested"]
    want_files = {f"{n}.png" for n in requested}
    if set(manifest["files"]) != want_files:
        problems.append(f"files {sorted(set(manifest['files']) ^ want_files)} differ from the shots requested")
    for name, digest in sorted(manifest["files"].items()):
        p = capture / name
        if not p.is_file():
            problems.append(f"{name} is missing")
            continue
        got = sha256(p)
        a, size, fmt = rgb(p)
        luma = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
        files[name] = {"sha256": got, "matches_manifest": got == digest, "format": fmt, "size": list(size),
                       "luma_mean": round(float(luma.mean()), 3), "luma_std": round(float(luma.std()), 3),
                       "clipped_black_share": round(float((a.max(-1) <= 3).mean()), 5),
                       "clipped_white_share": round(float((a.min(-1) >= 252).mean()), 5)}
        images[name] = a
        if got != digest:
            problems.append(f"{name}: SHA-256 {got[:12]} is not the manifest's {digest[:12]}")
        if fmt != "PNG" or tuple(size) != (width, height):
            problems.append(f"{name}: {fmt} {size}, want PNG {width}x{height}")
        if luma.std() <= MIN_LUMA_STD:
            problems.append(f"{name}: blank (luminance std {luma.std():.3f})")
    shots = manifest["shots"]
    for name, row in shots.items():
        shot = row["shot"]
        if not name.endswith(f"_LOD{shot['lod']}"):
            problems.append(f"{name} does not state LOD{shot['lod']}")
        for key in ("gates", "gates_after"):
            if key not in row:
                problems.append(f"{name}: no {key}")
            else:
                problems += gate_problems(name, shot, row[key])
    pairs = {}
    for name, row in shots.items():
        if row["shot"]["kind"] == "paw":
            pairs.setdefault(row["shot"]["camera"], {})[row["shot"]["state"]] = name
    morph = {}
    for cam, pair in sorted(pairs.items()):
        if set(pair) != {"holding", "empty"}:
            problems.append(f"{cam}: states {sorted(pair)}")
            continue
        h, e = shots[pair["holding"]]["camera"], shots[pair["empty"]]["camera"]
        same = all(np.allclose(h[k], e[k], atol=1e-6) for k in ("location_cm", "rotation_deg")) and \
            abs(h["field_of_view_deg"] - e["field_of_view_deg"]) < 1e-9
        a, b = images.get(pair["holding"] + ".png"), images.get(pair["empty"] + ".png")
        row = {"holding": pair["holding"], "empty": pair["empty"], "same_camera": bool(same)}
        if a is not None and b is not None:
            diff = np.abs(a - b).max(-1)
            row.update(changed_share=round(float((diff > CHANGED_LEVEL).mean()), 5),
                       mean_abs_diff=round(float(np.abs(a - b).mean()), 4))
            if row["changed_share"] <= CHANGED_SHARE:
                problems.append(f"{cam}: holding and empty differ in only {row['changed_share']:.4%} of the pixels")
        if not same:
            problems.append(f"{cam}: holding and empty were shot from different cameras")
        morph[cam] = row
    views = {}
    for name, row in shots.items():
        c = row.get("choice", {})
        if "clear" in c:
            views[name] = {k: c.get(k) for k in ("rank", "of", "clear", "blocked", "joint", "preference")}
    return {"capture": str(capture), "manifest": manifest_name, "manifest_sha256": sha256(capture / manifest_name),
            "resolution": [width, height],
            "shots": len(requested), "files": files, "morph_pairs": morph, "views": views,
            "views_not_clear": sorted(n for n, v in views.items() if not v["clear"]),
            "lod_build_settings": manifest.get("lod_build_settings"), "problems": problems}


def main():
    capture, out = Path(sys.argv[1]), Path(sys.argv[2])
    manifest_name = sys.argv[3] if len(sys.argv) > 3 else "manifest.json"     # e.g. a failed run's manifest.partial.json
    if out.exists():
        raise SystemExit(f"{out} exists")
    result = check(capture, manifest_name)
    out.write_text(json.dumps(result, indent=1) + "\n")
    print("NYAAKOTO_TP_REVIEW_CHECK " + json.dumps({"shots": result["shots"], "problems": result["problems"],
                                                    "views_not_clear": result["views_not_clear"],
                                                    "morph_pairs": {k: v.get("changed_share") for k, v in result["morph_pairs"].items()}}))


if __name__ == "__main__":
    main()
