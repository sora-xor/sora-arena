"""How speckled a first-person capture's fur is: the high-frequency residual of its white fur pixels.

  python3 scripts/art/fur_capture_noise.py Saved/YumiFP/<out> --out <result.json>
  python3 scripts/art/fur_capture_noise.py --compare Saved/YumiFP/<runup4> Saved/YumiFP/<auto> --out <result.json>
  python3 scripts/art/fur_capture_noise.py --assets Saved/YumiFP/<before> Saved/YumiFP/<after> --out <result.json>

Capture v3's fur read as white speckle. A candidate cause was HighResShot's
four-frame run-up, too short for TSR to resolve dithered coverage
(render_yumi_fp_review.highres_runup). This measures the symptom, so a
controlled comparison can test that cause: the same hold shot with runup=4
and with runup=auto, nothing else changed. Capture v4 ran it, and the longer
run-up did not resolve the speckle in that pair (highres_runup). It is a
measurement, not a gate: real fur has texture, and no threshold here says
what is good.

**Per hold:**
- **The fur pixels:** bright and unsaturated (luminance above FUR_MIN_LUMINANCE,
  saturation below FUR_MAX_SATURATION), and in an eye-view hold also inside
  the paw's ID class (analyse_yumi_fp_review.classify). They are eroded by
  ERODE_PX, so silhouette edges don't count.
- **The residual:** |L - box3(L)| on display luminance, its mean and 90th
  percentile, and the 5x5 local standard deviation's mean.
- **The control,** in an eye-view hold: the same residual on the bow's ID
  class, eroded by 1 (the urushi stave is smooth). It gives the fur/bow
  ratio, given only when the control's residual is at least one 8-bit step
  (CONTROL_FLOOR).

**The comparison** (--compare A B, root's design for the run-up test) needs
two runs that differ only in their run-up. Every SETUP_KEYS entry of the two
manifests must be equal: the holds, cameras, poses, assets' materials,
exposure, sun and set. Otherwise it refuses.

Per hold it reports:
- each run's own threshold-selected fur pixels and residual (the selection
  can change as the speckle smooths);
- the residual of both runs on one common region, the intersection of the
  two selections.

**The asset comparison** (--assets A B) is for two captures of the same holds
with different paw assets, as v4 against v5 (NYAAKOTO_FP_FUR_V4.md).
- **What must match:** every ASSET_SETUP_KEYS entry of the two manifests, and
  for each hold they share its camera, hold, posed sockets and pose.
- **The tolerance is ASSET_TOL_CM,** because a hold solved in another order
  differs by about 1e-12 cm.
- **What may differ:** the requested holds (only common ones are compared),
  the study's digest (recorded) and the assets' bytes, which no manifest
  holds.
- It reports the same per-hold figures as --compare.

**It fails** (exit 1, naming each problem), and never returns an empty
measurement, when:
- the manifest is missing or unreadable;
- requested_holds is empty or not a list of distinct names;
- eye_view_holds is not a list of requested holds;
- an eye-view hold has no ID image (an ID pass must have run);
- a hold's image or ID file is missing, or its bytes differ from the
  manifest's hash.
It reads only the runs and writes only --out, created exclusively.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import analyse_yumi_fp_review as A  # noqa: E402

REC709 = np.array([0.2126, 0.7152, 0.0722])
FUR_MIN_LUMINANCE = 0.40
FUR_MAX_SATURATION = 0.25
ERODE_PX = 2
PAW, BOW = 3, 1                         # analyse_yumi_fp_review.classify's labels
CONTROL_FLOOR = 1.0 / 255.0             # a control residual below one 8-bit step gives no meaningful ratio
# What two runs must share to compare their fur: everything but the run-up, their files and the level's timestamped
# name.
SETUP_KEYS = ("fov", "mesh_scale", "holds", "sockets_cm", "poses_component_cm", "materials", "materials_after_id_pass",
              "solved", "id_colours", "control", "study", "requested_holds", "ids_enabled", "eye_view_holds",
              "resolution", "cameras", "assessment_camera", "set_materials", "sun", "ev100", "exposure_bias")


# What two captures of different paw assets must share (--assets): the capture's setup, and per common hold its
# camera, hold, posed sockets and pose, numbers within ASSET_TOL_CM.
ASSET_SETUP_KEYS = ("fov", "mesh_scale", "materials", "id_colours", "control", "ids_enabled", "resolution",
                    "assessment_camera", "set_materials", "sun", "ev100", "exposure_bias", "highres_runup")
ASSET_HOLD_KEYS = ("cameras", "holds", "sockets_cm", "poses_component_cm")
ASSET_TOL_CM = 1e-9


class NoiseError(Exception):
    pass


def _close(x, y, tol):
    """x and y alike, their numbers within tol (booleans and everything else exactly)."""
    if isinstance(x, dict) and isinstance(y, dict):
        return x.keys() == y.keys() and all(_close(x[k], y[k], tol) for k in x)
    if isinstance(x, list) and isinstance(y, list):
        return len(x) == len(y) and all(_close(u, v, tol) for u, v in zip(x, y))
    if isinstance(x, bool) or isinstance(y, bool):
        return x is y
    if isinstance(x, (int, float)) and isinstance(y, (int, float)):
        return abs(x - y) <= tol
    return x == y


def box(x, r):
    k = 2 * r + 1
    p = np.pad(x, r, mode="edge")
    s = np.zeros_like(x)
    for dy in range(k):
        for dx in range(k):
            s += p[dy:dy + x.shape[0], dx:dx + x.shape[1]]
    return s / (k * k)


def erode(mask, r):
    out = mask.copy()
    for _ in range(r):
        p = np.pad(out, 1, constant_values=False)
        out = out & p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:]
    return out


def fur_mask(rgb):
    """(H, W) bool: bright, unsaturated pixels, and (H, W) display luminance."""
    lum = rgb @ REC709
    mx, mn = rgb.max(axis=2), rgb.min(axis=2)
    sat = (mx - mn) / np.maximum(mx, 1e-6)
    return (lum > FUR_MIN_LUMINANCE) & (sat < FUR_MAX_SATURATION), lum


def residual_stats(lum, mask):
    if not mask.any():
        return {"pixels": 0}
    hf = np.abs(lum - box(lum, 1))
    sd = np.sqrt(np.maximum(box(lum * lum, 2) - box(lum, 2) ** 2, 0.0))
    return {"pixels": int(mask.sum()), "residual_mean": float(hf[mask].mean()),
            "residual_p90": float(np.percentile(hf[mask], 90)), "local_sd_mean": float(sd[mask].mean()),
            "luminance_mean": float(lum[mask].mean())}


def masks(rgb, ids_rgb=None):
    """(the eroded fur selection, display luminance, the eroded bow control or None) for one hold."""
    fur, lum = fur_mask(rgb)
    bow = None
    if ids_rgb is not None:
        cls = A.classify(ids_rgb)
        fur &= cls == PAW
        bow = erode(cls == BOW, 1)
    return erode(fur, ERODE_PX), lum, bow


def hold_noise(rgb, ids_rgb=None):
    """The fur's (and, with an ID image, the bow's) residual for one hold, from display values in [0, 1]."""
    fur, lum, bow = masks(rgb, ids_rgb)
    out = {}
    if bow is not None:
        out["bow"] = residual_stats(lum, bow)
    out["fur"] = residual_stats(lum, fur)
    if ("bow" in out and out["bow"].get("pixels") and out["fur"].get("pixels")
            and out["bow"]["residual_mean"] >= CONTROL_FLOOR):
        out["fur_over_bow"] = out["fur"]["residual_mean"] / out["bow"]["residual_mean"]
    return out


def _image(path):
    from PIL import Image                     # here only: the numpy functions above need no PIL

    with Image.open(path) as im:
        return np.asarray(im.convert("RGB"), dtype=np.float64) / 255.0


def _names(x):
    return isinstance(x, list) and all(isinstance(h, str) and h for h in x)


def load_run(run: Path):
    """(manifest, manifest bytes, {hold: (rgb, ids_rgb or None)}), or NoiseError naming every problem."""
    mpath = run / "manifest.json"
    if not mpath.is_file():
        raise NoiseError(f"{run}: no manifest.json")
    data = mpath.read_bytes()
    try:
        manifest = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise NoiseError(f"{mpath}: unreadable ({type(exc).__name__}: {exc})") from None
    if not isinstance(manifest, dict):
        raise NoiseError(f"{mpath}: not a record")
    requested, eye = manifest.get("requested_holds"), manifest.get("eye_view_holds", [])
    problems = []
    if not (_names(requested) and requested and len(set(requested)) == len(requested)):
        raise NoiseError(f"{mpath}: requested_holds {requested!r} is not a non-empty list of distinct hold names")
    if not (_names(eye) and set(eye) <= set(requested)):
        raise NoiseError(f"{mpath}: eye_view_holds {eye!r} is not a list of requested holds")
    files, id_files = manifest.get("files"), manifest.get("id_files", {})
    if not isinstance(files, dict) or not isinstance(id_files, dict):
        raise NoiseError(f"{mpath}: files or id_files is not a map")
    if eye and manifest.get("ids_enabled") is not True:
        problems.append(f"eye-view holds {eye} need the ID pass, but ids_enabled is {manifest.get('ids_enabled')!r}")
    images = {}
    for hold in requested:
        names = [f"{hold}.png"]
        if hold in eye:
            if not isinstance(id_files.get(hold), str) or not id_files.get(hold):
                problems.append(f"{hold}: an eye-view hold with no ID image")
                continue
            names.append(id_files[hold])
        bad = False
        for name in names:
            path = run / name
            if Path(name).name != name or not path.is_file():
                problems.append(f"{hold}: {name} is missing")
                bad = True
            elif hashlib.sha256(path.read_bytes()).hexdigest() != files.get(name):
                problems.append(f"{hold}: {name} differs from the manifest's hash")
                bad = True
        if not bad:
            images[hold] = (_image(run / names[0]), _image(run / names[1]) if len(names) > 1 else None)
    if problems:
        raise NoiseError(f"{mpath}: " + "; ".join(problems))
    return manifest, data, images


def run_noise(run: Path) -> dict:
    manifest, data, images = load_run(run)
    return {"schema_version": 2, "generator": "scripts/art/fur_capture_noise.py",
            "manifest_sha256": hashlib.sha256(data).hexdigest(), "highres_runup": manifest.get("highres_runup"),
            "holds": {hold: hold_noise(rgb, ids) for hold, (rgb, ids) in images.items()},
            "scope": "a measurement of capture noise in the fur, for a controlled comparison; not a gate"}


def _pair(ia, ib, holds):
    """Per hold: each run's own selection, and both on the intersection of their fur selections."""
    out = {}
    for hold in holds:
        (rgb_a, ids_a), (rgb_b, ids_b) = ia[hold], ib[hold]
        fur_a, lum_a, _bow = masks(rgb_a, ids_a)
        fur_b, lum_b, _bow = masks(rgb_b, ids_b)
        common = fur_a & fur_b
        out[hold] = {"a": hold_noise(rgb_a, ids_a), "b": hold_noise(rgb_b, ids_b), "common_pixels": int(common.sum()),
                     "a_on_common": residual_stats(lum_a, common), "b_on_common": residual_stats(lum_b, common)}
    return out


def compare_assets(run_a: Path, run_b: Path) -> dict:
    """Two captures of the same holds with different paw assets: per common hold, as compare_runs reports."""
    (ma, da, ia), (mb, db, ib) = load_run(run_a), load_run(run_b)
    common = [h for h in ma["requested_holds"] if h in mb["requested_holds"]]
    if not common:
        raise NoiseError(f"{run_a} and {run_b} have no hold in common")
    differ = [k for k in ASSET_SETUP_KEYS if ma.get(k) != mb.get(k)]
    for hold in common:
        for k in ASSET_HOLD_KEYS:
            a, b = ma.get(k), mb.get(k)
            if not (isinstance(a, dict) and isinstance(b, dict) and _close(a.get(hold), b.get(hold), ASSET_TOL_CM)):
                differ.append(f"{k}[{hold}]")
    if differ:
        raise NoiseError(f"{run_a} and {run_b} differ in {differ}: not one setup")
    return {"schema_version": 2, "generator": "scripts/art/fur_capture_noise.py", "compare_assets": True,
            "a": {"run": str(run_a), "manifest_sha256": hashlib.sha256(da).hexdigest()},
            "b": {"run": str(run_b), "manifest_sha256": hashlib.sha256(db).hexdigest()},
            "tolerance_cm": ASSET_TOL_CM, "study_same": ma.get("study") == mb.get("study"),
            "holds": _pair(ia, ib, common),
            "scope": "two paw assets under one setup: a measurement of capture noise in the fur, not a gate"}


def compare_runs(run_a: Path, run_b: Path) -> dict:
    """Two runs identical but for their run-up: per hold, each run's own selection, and both on their intersection."""
    (ma, da, ia), (mb, db, ib) = load_run(run_a), load_run(run_b)
    differ = [k for k in SETUP_KEYS if ma.get(k) != mb.get(k)]
    if differ:
        raise NoiseError(f"{run_a} and {run_b} differ in {differ}, not only in their run-up")
    holds = _pair(ia, ib, ma["requested_holds"])
    return {"schema_version": 2, "generator": "scripts/art/fur_capture_noise.py", "compare": True,
            "a": {"run": str(run_a), "manifest_sha256": hashlib.sha256(da).hexdigest(),
                  "highres_runup": ma.get("highres_runup")},
            "b": {"run": str(run_b), "manifest_sha256": hashlib.sha256(db).hexdigest(),
                  "highres_runup": mb.get("highres_runup")},
            "same_runup": ma.get("highres_runup") == mb.get("highres_runup"), "holds": holds,
            "scope": "a controlled comparison of capture noise in the fur; a measurement, not a gate"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("run", type=Path, nargs="?")
    ap.add_argument("--compare", type=Path, nargs=2, metavar=("RUN_A", "RUN_B"))
    ap.add_argument("--assets", type=Path, nargs=2, metavar=("RUN_A", "RUN_B"))
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if [a.run is not None, a.compare is not None, a.assets is not None].count(True) != 1:
        print("FUR_NOISE_FAILED: give one run, --compare RUN_A RUN_B or --assets RUN_A RUN_B", file=sys.stderr)
        return 1
    if a.out.exists():
        print(f"FUR_NOISE_FAILED: {a.out} exists; a result is never overwritten", file=sys.stderr)
        return 1
    try:
        result = (run_noise(a.run) if a.run is not None else compare_runs(*a.compare) if a.compare is not None
                  else compare_assets(*a.assets))
    except NoiseError as exc:
        print(f"FUR_NOISE_FAILED: {exc}", file=sys.stderr)
        return 1
    with open(a.out, "x", encoding="utf-8") as f:
        f.write(json.dumps(result, indent=1) + "\n")
    for hold, r in result["holds"].items():
        if result.get("compare") or result.get("compare_assets"):
            ca, cb = r["a_on_common"], r["b_on_common"]
            print(f"{hold}: own selections {r['a']['fur']['pixels']} / {r['b']['fur']['pixels']} px; on the common "
                  f"{r['common_pixels']} px, residual {ca.get('residual_mean', float('nan')):.4f} (A) vs "
                  f"{cb.get('residual_mean', float('nan')):.4f} (B)")
        else:
            fur = r["fur"]
            ratio = f", {r['fur_over_bow']:.1f}x the bow's" if "fur_over_bow" in r else ""
            print(f"{hold}: fur residual {fur.get('residual_mean', float('nan')):.4f} over {fur['pixels']} px{ratio}")
    print("FUR_NOISE", a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
