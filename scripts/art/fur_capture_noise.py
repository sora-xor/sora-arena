"""How speckled a first-person capture's fur is: the high-frequency residual of its white fur pixels.

  python3 scripts/art/fur_capture_noise.py Saved/YumiFP/<out> --out <result.json>

Capture v3's fur read as white speckle. A candidate cause is HighResShot's
four-frame run-up, too short for TSR to resolve dithered coverage
(render_yumi_fp_review.highres_runup). This measures the symptom, so a
controlled comparison can test that cause: the same hold shot with runup=4
and with runup=auto, nothing else changed. It is a measurement, not a gate:
real fur has texture, and no threshold here says what is good.

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

**It fails** (exit 1, naming each problem) when the manifest is missing, a
hold's image or ID file is missing, or a file's bytes differ from the
manifest's hash. It reads only the run and writes only --out, created
exclusively.
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


class NoiseError(Exception):
    pass


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


def hold_noise(rgb, ids_rgb=None):
    """The fur's (and, with an ID image, the bow's) residual for one hold, from display values in [0, 1]."""
    fur, lum = fur_mask(rgb)
    out = {}
    if ids_rgb is not None:
        cls = A.classify(ids_rgb)
        fur &= cls == PAW
        out["bow"] = residual_stats(lum, erode(cls == BOW, 1))
    out["fur"] = residual_stats(lum, erode(fur, ERODE_PX))
    if ("bow" in out and out["bow"].get("pixels") and out["fur"].get("pixels")
            and out["bow"]["residual_mean"] >= CONTROL_FLOOR):
        out["fur_over_bow"] = out["fur"]["residual_mean"] / out["bow"]["residual_mean"]
    return out


def _image(path):
    from PIL import Image                     # here only: the numpy functions above need no PIL

    with Image.open(path) as im:
        return np.asarray(im.convert("RGB"), dtype=np.float64) / 255.0


def run_noise(run: Path) -> dict:
    mpath = run / "manifest.json"
    if not mpath.is_file():
        raise NoiseError(f"{run}: no manifest.json")
    manifest = json.loads(mpath.read_text(encoding="utf-8"))
    files, id_files = manifest.get("files", {}), manifest.get("id_files", {})
    problems, holds = [], {}
    for hold in manifest.get("requested_holds", []):
        names = [f"{hold}.png"] + ([id_files[hold]] if hold in id_files else [])
        for name in names:
            path = run / name
            if not path.is_file():
                problems.append(f"{hold}: {name} is missing")
            elif hashlib.sha256(path.read_bytes()).hexdigest() != files.get(name):
                problems.append(f"{hold}: {name} differs from the manifest's hash")
        if not problems:
            holds[hold] = hold_noise(_image(run / names[0]), _image(run / names[1]) if len(names) > 1 else None)
    if problems:
        raise NoiseError("; ".join(problems))
    return {"schema_version": 1, "generator": "scripts/art/fur_capture_noise.py",
            "manifest_sha256": hashlib.sha256(mpath.read_bytes()).hexdigest(),
            "highres_runup": manifest.get("highres_runup"), "holds": holds,
            "scope": "a measurement of capture noise in the fur, for a controlled comparison; not a gate"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("run", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.out.exists():
        print(f"FUR_NOISE_FAILED: {a.out} exists; a result is never overwritten", file=sys.stderr)
        return 1
    try:
        result = run_noise(a.run)
    except NoiseError as exc:
        print(f"FUR_NOISE_FAILED: {exc}", file=sys.stderr)
        return 1
    with open(a.out, "x", encoding="utf-8") as f:
        f.write(json.dumps(result, indent=1) + "\n")
    for hold, r in result["holds"].items():
        fur = r["fur"]
        ratio = f", {r['fur_over_bow']:.1f}x the bow's" if "fur_over_bow" in r else ""
        print(f"{hold}: fur residual {fur.get('residual_mean', float('nan')):.4f} over {fur['pixels']} px{ratio}")
    print("FUR_NOISE", a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
