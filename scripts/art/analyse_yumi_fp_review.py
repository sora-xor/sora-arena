"""Count each part's real pixels in the first-person ID originals.

  python3 scripts/art/analyse_yumi_fp_review.py Saved/YumiFP/<out>

render_yumi_fp_review.py's ID pass draws each part in one unlit colour (bow
red, arrow green, paw blue; the fur cards and the W18 islands keep their
alpha masks), with the set, sky and lights hidden. For each <hold>_ids.png
in the capture's manifest, this reports per part:

- pixels, and their share of the frame;
- the screen extent, in half-widths and half-heights from the centre, as
  check_viewmodel_framing measures sockets;
- whether the part touches each frame edge;
- pixels inside the reticle's clear disc (reticle_clear_radius half-heights,
  the contract's camera, pinned in the capture's hold study), and so whether
  the reticle is occluded.

A pixel belongs to a part when that part's channel is at least ID_MIN and
twice each other channel. Anything else is background, including a bright
unsaturated sky if one were left. Writes analysis.json beside the manifest,
with every input's SHA-256. Pixels of review originals: not an admission.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
PARTS = ("bow", "arrow", "paw")
ID_MIN = 0.25


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


def main(argv):
    if len(argv) != 2:
        raise SystemExit(__doc__)
    from PIL import Image

    run = Path(argv[1])
    run = run if run.is_absolute() else ROOT / run
    manifest_path = run / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    study = json.loads((ROOT / "docs/art-direction/data/yumi_fp_hold_study.json").read_text(encoding="utf-8"))
    radius = study["root_control"]["camera"]["reticle_clear_radius"]
    record = {"schema_version": 1, "generator": "scripts/art/analyse_yumi_fp_review.py",
              "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
              "reticle_clear_radius": radius, "id_colours": manifest.get("id_colours"),
              "scope": "pixels of editor review originals: not an admission", "holds": {}}
    for hold, name in manifest.get("id_files", {}).items():
        path = run / name
        rgb = np.asarray(Image.open(path).convert("RGB"), dtype=np.float64) / 255.0
        res = analyse(rgb, radius)
        res["file"], res["sha256"] = name, hashlib.sha256(path.read_bytes()).hexdigest()
        res["assess"] = manifest.get("assess", {}).get(hold)
        record["holds"][hold] = res
        parts = ", ".join(f"{k} {v['pixels']} px ({v['share']:.1%}; {v['in_reticle_disc']} in the reticle disc)"
                          for k, v in res["parts"].items())
        print(f"{hold}: {parts}; reticle occluded: {res['reticle_occluded']}")
    (run / "analysis.json").write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
    print("YUMI_FP_ANALYSIS", run / "analysis.json")


if __name__ == "__main__":
    main(sys.argv)
