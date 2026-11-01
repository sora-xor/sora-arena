"""Count each part's real pixels in the first-person ID originals, or fail saying why not.

  python3 scripts/art/analyse_yumi_fp_review.py Saved/YumiFP/<out>

render_yumi_fp_review.py's ID pass draws each part in one unlit colour (bow
red, arrow green, paw blue; the fur cards and the W18 islands keep their
alpha masks), with the set, sky and lights hidden.

**What it reports**, for each requested eye-view hold's <hold>_ids.png, per
part:
- pixels, and their share of the frame;
- the screen extent, in half-widths and half-heights from the centre, as
  check_viewmodel_framing measures sockets;
- whether the part touches each frame edge;
- pixels inside the reticle's clear disc, and so whether the reticle is
  occluded.

**What it reads** is only the capture's own record, never a file that could
have changed since:
- the requested and eye-view holds;
- whether the ID pass ran;
- the resolution and each hold's camera, as read back from the spawned actor;
- the assessment camera (its reticle_clear_radius);
- the hold study's digest;
- every file's SHA-256.

**It fails** (exit 1, naming each problem), and never prints an empty
analysis, when:
- the manifest is missing, unreadable, or predates this contract;
- a recorded value has the wrong type, checked before anything divides by
  it or compares it. The resolution must be two positive integers; the
  reticle radius and each camera aspect positive finite numbers, never a
  boolean, NaN or infinity; ids_enabled a boolean; the holds lists of names;
  the file maps names to names (Codex's review of 841d246: a NaN radius
  reported the reticle clear);
- the ID pass was off, or the run has no eye-view hold;
- a requested eye-view hold has no ID file, or there is one for a hold that
  was not requested;
- an ID file is missing or empty, outside the run, or its bytes disagree with
  the manifest's hash;
- an image is not the recorded resolution, or a hold's camera aspect is not
  the resolution's.
Custom hold subsets are analysed as requested.

**Classification:** a pixel belongs to a part when that part's channel is at
least ID_MIN and twice each other channel. Anything else is background,
including a bright unsaturated sky if one were left.

Writes analysis.json beside the manifest. Pixels of review originals: not an
admission.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
PARTS = ("bow", "arrow", "paw")
ID_MIN = 0.25
REQUIRED = ("requested_holds", "eye_view_holds", "ids_enabled", "resolution", "cameras", "assessment_camera",
            "files", "id_files", "study")


class AnalysisError(Exception):
    """The run cannot be analysed as recorded; the message names every problem."""


def _number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def positive_finite(x):
    """A real, finite number above zero: not a boolean, NaN or infinity."""
    return _number(x) and math.isfinite(x) and x > 0


def positive_int(x):
    return isinstance(x, int) and not isinstance(x, bool) and x > 0


def _names(x):
    return isinstance(x, list) and all(isinstance(h, str) for h in x)


def _name_map(x):
    return isinstance(x, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in x.items())


def validate(manifest):
    """Problems with the recorded values' types, before any of them is divided or compared."""
    problems = []
    if not isinstance(manifest["ids_enabled"], bool):
        problems.append(f"ids_enabled {manifest['ids_enabled']!r} is not a boolean")
    for key in ("requested_holds", "eye_view_holds"):
        if not _names(manifest[key]):
            problems.append(f"{key} {manifest[key]!r} is not a list of hold names")
    res = manifest["resolution"]
    if not (isinstance(res, list) and len(res) == 2 and all(positive_int(c) for c in res)):
        problems.append(f"resolution {res!r} is not two positive integers")
    for key in ("files", "id_files"):
        if not _name_map(manifest[key]):
            problems.append(f"{key} is not a map of names to names")
    for key in ("cameras", "assessment_camera", "study"):
        if not isinstance(manifest[key], dict):
            problems.append(f"{key} {manifest[key]!r} is not a record")
    cam = manifest["assessment_camera"]
    if isinstance(cam, dict) and not positive_finite(cam.get("reticle_clear_radius")):
        problems.append(f"the recorded reticle_clear_radius {cam.get('reticle_clear_radius')!r} is not a positive "
                        "finite number")
    return problems


def classify(rgb):
    """(H, W) int: 0 background, 1 bow (red), 2 arrow (green), 3 paw (blue), from display values in [0, 1]."""
    rgb = np.asarray(rgb, dtype=np.float64)
    top = rgb.argmax(axis=2)
    srt = np.sort(rgb, axis=2)
    best, second = srt[..., 2], srt[..., 1]
    ok = (best >= ID_MIN) & (best >= 2.0 * second)
    return np.where(ok, top + 1, 0)


def analyse(rgb, reticle_clear_radius):
    """Per-part pixel statistics for one ID image (H, W, 3) in [0, 1]."""
    if not positive_finite(reticle_clear_radius):
        raise ValueError(f"reticle_clear_radius {reticle_clear_radius!r} is not a positive finite number")
    cls = classify(rgb)
    h, w = cls.shape
    yy, xx = np.mgrid[0:h, 0:w]
    u = (xx + 0.5 - w / 2) / (w / 2)                  # half-widths, +right
    v = -(yy + 0.5 - h / 2) / (h / 2)                 # half-heights, +up
    r = np.hypot(u * (w / h), v)                      # half-heights from the centre
    disc = r <= reticle_clear_radius
    out = {"pixels": int(h * w), "reticle_disc_pixels": int(disc.sum()), "parts": {}}
    for k, name in enumerate(PARTS, start=1):
        m = cls == k
        n = int(m.sum())
        part = {"pixels": n, "share": n / (h * w), "in_reticle_disc": int((m & disc).sum())}
        if n:
            part["extent_uv"] = {"u": [float(u[m].min()), float(u[m].max())], "v": [float(v[m].min()), float(v[m].max())]}
            part["touches"] = {"left": bool(m[:, 0].any()), "right": bool(m[:, -1].any()),
                               "top": bool(m[0, :].any()), "bottom": bool(m[-1, :].any())}
        out["parts"][name] = part
    any_part = cls > 0
    out["viewmodel_share"] = float(any_part.mean())
    out["reticle_occluded"] = bool((any_part & disc).any())
    out["reticle_disc_covered_share"] = float((any_part & disc).sum() / max(int(disc.sum()), 1))
    return out


def _load_rgb(path: Path):
    from PIL import Image                      # here only: classify() and analyse() need no PIL

    with Image.open(path) as im:
        return np.asarray(im.convert("RGB"), dtype=np.float64) / 255.0


def analyse_run(run: Path) -> dict:
    """The analysis of one capture directory, or AnalysisError naming every problem found."""
    manifest_path = run / "manifest.json"
    if not manifest_path.is_file():
        raise AnalysisError(f"{run}: no manifest.json")
    manifest_bytes = manifest_path.read_bytes()
    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise AnalysisError(f"{manifest_path}: unreadable ({type(exc).__name__}: {exc})") from None
    if not isinstance(manifest, dict):
        raise AnalysisError(f"{manifest_path}: not a record")
    missing = [k for k in REQUIRED if k not in manifest]
    if missing:
        raise AnalysisError(f"{manifest_path}: no {missing}; it predates the ID analysis contract (capture it again)")
    bad = validate(manifest)
    if bad:
        raise AnalysisError(f"{manifest_path}: " + "; ".join(bad))
    if not manifest["ids_enabled"]:
        raise AnalysisError(f"{manifest_path}: the ID pass was off (ids=0); there is nothing to analyse")
    eye = list(manifest["eye_view_holds"])
    if not eye:
        raise AnalysisError(f"{manifest_path}: no eye-view hold was requested ({manifest['requested_holds']}); "
                            "there is nothing to analyse")
    problems = []
    if not set(eye) <= set(manifest["requested_holds"]):
        problems.append(f"eye-view holds {eye} are not all requested holds {manifest['requested_holds']}")
    extra = sorted(set(manifest["id_files"]) - set(eye))
    if extra:
        problems.append(f"ID files for holds that were not eye-view holds: {extra}")
    width, height = manifest["resolution"]                  # validated: two positive integers
    radius = manifest["assessment_camera"]["reticle_clear_radius"]      # validated: positive and finite
    images = {}
    for hold in eye:
        name = manifest["id_files"].get(hold)
        if name is None:
            problems.append(f"{hold}: no ID file recorded")
            continue
        path = run / name
        if Path(name).name != name:
            problems.append(f"{hold}: ID file {name!r} is not a file in the run")
            continue
        if not path.is_file():
            problems.append(f"{hold}: {name} is missing")
            continue
        data = path.read_bytes()
        if not data:
            problems.append(f"{hold}: {name} is empty")
            continue
        want = manifest["files"].get(name)
        got = hashlib.sha256(data).hexdigest()
        if want is None:
            problems.append(f"{hold}: {name} has no hash in the manifest's files")
        elif got != want:
            problems.append(f"{hold}: {name} is {got[:12]}..., the manifest records {want[:12]}...")
        cam = manifest["cameras"].get(hold)
        if not isinstance(cam, dict):
            problems.append(f"{hold}: no camera recorded")
        elif not positive_finite(cam.get("aspect_ratio")):
            problems.append(f"{hold}: camera aspect_ratio {cam.get('aspect_ratio')!r} is not a positive finite number")
        elif abs(cam["aspect_ratio"] - width / height) > 1e-6:
            problems.append(f"{hold}: camera aspect {cam['aspect_ratio']} is not the resolution's {width / height:.6f}")
        try:
            rgb = _load_rgb(path)
        except Exception as exc:                 # an unreadable image is a problem, not a crash
            problems.append(f"{hold}: {name} does not decode ({type(exc).__name__}: {exc})")
            continue
        if rgb.shape[:2] != (height, width):
            problems.append(f"{hold}: {name} is {rgb.shape[1]}x{rgb.shape[0]}, the capture's resolution {width}x{height}")
            continue
        images[hold] = (name, got, rgb)
    if problems:
        raise AnalysisError(f"{manifest_path}: " + "; ".join(problems))
    record = {"schema_version": 2, "generator": "scripts/art/analyse_yumi_fp_review.py",
              "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(), "study": manifest["study"],
              "resolution": [width, height], "reticle_clear_radius": radius, "id_colours": manifest.get("id_colours"),
              "scope": "pixels of editor review originals: not an admission", "holds": {}}
    for hold in eye:
        name, digest, rgb = images[hold]
        res = analyse(rgb, radius)
        res.update(file=name, sha256=digest, camera=manifest["cameras"][hold],
                   assess=manifest.get("assess", {}).get(hold))
        record["holds"][hold] = res
    return record


def main(argv):
    if len(argv) != 2:
        raise SystemExit(__doc__)
    run = Path(argv[1])
    run = run if run.is_absolute() else ROOT / run
    try:
        record = analyse_run(run)
    except AnalysisError as exc:
        print(f"YUMI_FP_ANALYSIS_FAILED: {exc}", file=sys.stderr)
        return 1
    for hold, res in record["holds"].items():
        parts = ", ".join(f"{k} {v['pixels']} px ({v['share']:.1%}; {v['in_reticle_disc']} in the reticle disc)"
                          for k, v in res["parts"].items())
        print(f"{hold}: {parts}; reticle occluded: {res['reticle_occluded']}")
    (run / "analysis.json").write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
    print("YUMI_FP_ANALYSIS", run / "analysis.json")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
