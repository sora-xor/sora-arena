"""Ring, latewood and colour statistics of the CC0 hinoki and sugi plank scans, at physical scale.

Numpy and PIL only: no Blender, no Unreal. The focused timber patch study (one
column and one rail of the v2.3 pilot) is judged against these two scans, so
it needs their structure in millimetres, not by eye:

  python -I scripts/art/timber_scan_reference.py <raw root>

where <raw root> holds cc0/polyhaven/<asset>/<asset>_diff_4k.jpg (the cached
Poly Haven downloads; the art worktree has no copy). The physical size of
each scan is its ledger entry's source_dimensions_mm
(scripts/assets/manifests/polyhaven-first-slice.json).

All measurements are on the diffuse map's linear luminance (sRGB decoded,
Rec. 709 weights):

- **Grain axis:** the axis with the weaker mean squared gradient (the fibres
  and ring lines run along it).
- **Plank seams:** dips of the across-grain profile of along-grain medians
  (a seam is straight and runs the whole length; latewood lines wander), at
  least SEAM_SIGMA robust deviations below a 10 mm running median, and at
  least SEAM_MIN_MM apart. Windows keep SEAM_KEEP_OUT_MM clear of them.
- **Windows:** WINDOW_ACROSS_MM across the grain by WINDOW_ALONG_MM along it,
  short enough along the grain that a flat-sawn arch stays nearly straight.
  A window counts only where its structure tensor says the ring lines run
  within ORIENT_MAX_DEG of the grain axis, coherently (COHERENCE_MIN), so
  every spacing is measured across the lines.
- **Apparent ring spacing:** the first autocorrelation peak of the window's
  across-grain profile (detrended), refined by a parabola, between
  LAG_MIN_MM and half the window, at a correlation of at least PEAK_MIN.
  This is the spacing of the lines on the face, which on a flat-sawn face is
  wider than the true ring width.
- **Latewood fraction:** the share of the profile below the midpoint of its
  5th and 95th percentiles (dark latewood).
- **Contrast:** the profile's 95th over 5th percentile luminance.
- **Colour:** linear RGB means of the earlywood and latewood samples.
- **Fibre band:** the RMS of the profile's spectrum at FIBRE_BAND_MM periods
  (fine longitudinal fibres and pores; the hinoki scan's Nyquist is 0.92 mm),
  over the RMS at RING_BAND_MM periods, and relative to the mean luminance.
  The JPEG may soften this band, so it is a lower bound on the scans' fibre.

Writes docs/art-direction/data/timber_scan_reference.json. A reference
measurement, not a gate and not an admission.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "scripts/assets/manifests/polyhaven-first-slice.json"
OUT = ROOT / "docs/art-direction/data/timber_scan_reference.json"
ASSETS = ("hinoki_planks", "japanese_cedar_planks")

REC709 = np.array([0.2126, 0.7152, 0.0722])
SEAM_SIGMA = 4.0
SEAM_MIN_MM = 30.0
SEAM_KEEP_OUT_MM = 4.0
WINDOW_ACROSS_MM = 36.0
WINDOW_ALONG_MM = 8.0
STEP_ACROSS_MM = 12.0
STEP_ALONG_MM = 40.0
ORIENT_MAX_DEG = 12.0
COHERENCE_MIN = 0.3
LAG_MIN_MM = 0.7
PEAK_MIN = 0.15
FIBRE_BAND_MM = (0.92, 1.5)
RING_BAND_MM = (1.5, 15.0)


def srgb_to_linear(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def linear_to_srgb8(c):
    c = np.clip(np.asarray(c, dtype=float), 0.0, 1.0)
    s = np.where(c <= 0.0031308, 12.92 * c, 1.055 * c ** (1.0 / 2.4) - 0.055)
    return "#" + "".join(f"{int(round(255 * v)):02x}" for v in s)


def ledger_mm(asset):
    for r in json.loads(LEDGER.read_text(encoding="utf-8"))["records"]:
        if r["asset_id"] == asset:
            w, h = r["source_dimensions_mm"]
            return float(w), float(h)
    raise KeyError(f"timber scan reference: {asset} is not in {LEDGER}")


def running_median(x, n):
    pad = n // 2
    xp = np.pad(x, pad, mode="reflect")
    win = np.lib.stride_tricks.sliding_window_view(xp, n)
    return np.median(win, axis=1)[: len(x)]


def seams(profile, mm):
    """Plank seams: deep, narrow dips of the along-grain median profile, in pixels across."""
    base = running_median(profile, max(3, int(round(10.0 / mm)) | 1))
    dip = base - profile
    mad = np.median(np.abs(dip - np.median(dip))) * 1.4826
    cand = np.where((dip > SEAM_SIGMA * mad) & (dip >= np.roll(dip, 1)) & (dip >= np.roll(dip, -1)))[0]
    keep = []
    for i in sorted(cand, key=lambda i: -dip[i]):
        if all(abs(i - j) * mm >= SEAM_MIN_MM for j in keep):
            keep.append(int(i))
    return sorted(keep)


def first_peak(p, mm):
    """The first autocorrelation peak of a detrended profile: (lag in mm, correlation) or None."""
    x = np.arange(len(p))
    q = p - np.polyval(np.polyfit(x, p, 1), x)
    q = q - q.mean()
    den = float((q * q).sum())
    if den <= 0.0:
        return None
    n = len(q) // 2
    r = np.array([float((q[: len(q) - k] * q[k:]).sum()) / den for k in range(n + 1)])
    lo = max(2, int(np.ceil(LAG_MIN_MM / mm)))
    for k in range(lo, n):
        if r[k] >= r[k - 1] and r[k] > r[k + 1] and r[k] >= PEAK_MIN:
            a, b, c = r[k - 1], r[k], r[k + 1]
            d = a - 2.0 * b + c
            off = 0.5 * (a - c) / d if d != 0.0 else 0.0
            return (k + off) * mm, float(b)
    return None


def band_rms(p, mm, band):
    """RMS of the detrended profile's spectrum between two periods (mm), Hann-windowed."""
    x = np.arange(len(p))
    q = (p - np.polyval(np.polyfit(x, p, 1), x)) * np.hanning(len(p))
    spec = np.abs(np.fft.rfft(q)) ** 2
    period = np.divide(len(p) * mm, np.arange(len(spec)), out=np.full(len(spec), np.inf), where=np.arange(len(spec)) > 0)
    sel = (period >= band[0]) & (period < band[1])
    return float(np.sqrt(spec[sel].sum() * 2.0 / (len(p) * (np.hanning(len(p)) ** 2).sum())))


def analyse(rgb, mm):
    """Every statistic above, for a linear RGB image (H, W, 3) at ``mm`` millimetres per pixel.

    Shared with render_timber_patch_study.py, which runs it on rendered base
    colour, so the scans and the timber are measured the same way."""
    Y = rgb @ REC709
    gx = float((np.diff(Y, axis=1) ** 2).mean())
    gy = float((np.diff(Y, axis=0) ** 2).mean())
    along_x = gx < gy
    if not along_x:                               # rows across the grain, columns along it
        Y, rgb = Y.T, np.transpose(rgb, (1, 0, 2))
    profile = np.median(Y, axis=1)
    seam_rows = seams(profile, mm)
    keep_out = int(np.ceil(SEAM_KEEP_OUT_MM / mm))
    blocked = np.zeros(Y.shape[0], bool)
    for s_ in seam_rows:
        blocked[max(0, s_ - keep_out): s_ + keep_out + 1] = True
    wa, wl = int(round(WINDOW_ACROSS_MM / mm)), int(round(WINDOW_ALONG_MM / mm))
    sa, sl = int(round(STEP_ACROSS_MM / mm)), int(round(STEP_ALONG_MM / mm))
    rows = {"spacing_mm": [], "latewood": [], "contrast": [], "early": [], "late": [], "fibre_ring": [], "fibre_rel": []}
    tried = oriented = 0
    for a0 in range(0, Y.shape[0] - wa, sa):
        if blocked[a0: a0 + wa].any():
            continue
        for l0 in range(0, Y.shape[1] - wl, sl):
            tried += 1
            win = Y[a0: a0 + wa, l0: l0 + wl]
            g_across = np.diff(win, axis=0)[:, :-1]
            g_along = np.diff(win, axis=1)[:-1, :]
            jaa, jll, jal = (g_across ** 2).sum(), (g_along ** 2).sum(), (g_across * g_along).sum()
            tr = jaa + jll
            if tr <= 0.0:
                continue
            coherence = np.sqrt((jaa - jll) ** 2 + 4.0 * jal ** 2) / tr
            angle = 0.5 * np.degrees(np.arctan2(2.0 * jal, jaa - jll))     # gradient off the across axis
            if coherence < COHERENCE_MIN or abs(angle) > ORIENT_MAX_DEG:
                continue
            oriented += 1
            p = win.mean(axis=1)
            peak = first_peak(p, mm)
            if peak is None:
                continue
            p5, p95 = np.percentile(p, (5.0, 95.0))
            dark = p < 0.5 * (p5 + p95)
            c = rgb[a0: a0 + wa, l0: l0 + wl].mean(axis=1)
            rows["spacing_mm"].append(peak[0])
            rows["latewood"].append(float(dark.mean()))
            rows["contrast"].append(float(p95 / max(p5, 1e-6)))
            rows["early"].append(c[~dark].mean(axis=0))
            rows["late"].append(c[dark].mean(axis=0))
            fib, ring = band_rms(p, mm, FIBRE_BAND_MM), band_rms(p, mm, RING_BAND_MM)
            rows["fibre_ring"].append(fib / max(ring, 1e-9))
            rows["fibre_rel"].append(fib / float(p.mean()))

    def pct(v):
        if not len(v):
            return None
        return {f"p{q}": round(float(np.percentile(v, q)), 4) for q in (10, 25, 50, 75, 90)}

    out = {
        "mm_per_px": mm,
        "grain_axis": "x (rows across)" if along_x else "y (columns across)",
        "seams": {"count": len(seam_rows), "spacing_mm": pct(np.diff(seam_rows) * mm)},
        "windows": {"tried": tried, "oriented": oriented, "measured": len(rows["spacing_mm"])},
        "apparent_ring_spacing_mm": pct(rows["spacing_mm"]),
        "latewood_fraction": pct(rows["latewood"]),
        "contrast_p95_over_p5": pct(rows["contrast"]),
        "fibre_over_ring_rms": pct(rows["fibre_ring"]),
        "fibre_rms_over_mean": pct(rows["fibre_rel"]),
    }
    if rows["early"]:
        early, late = np.mean(rows["early"], axis=0), np.mean(rows["late"], axis=0)
        out.update({
            "earlywood_linear_rgb": [round(float(v), 4) for v in early],
            "latewood_linear_rgb": [round(float(v), 4) for v in late],
            "earlywood_srgb": linear_to_srgb8(early),
            "latewood_srgb": linear_to_srgb8(late),
            "early_over_late_luminance": round(float(early @ REC709 / (late @ REC709)), 4),
        })
    return out


def measure(asset, raw_root):
    from PIL import Image                      # here only: Blender's Python has no PIL

    path = Path(raw_root) / "cc0/polyhaven" / asset / f"{asset}_diff_4k.jpg"
    data = path.read_bytes()
    rgb = srgb_to_linear(np.asarray(Image.open(path).convert("RGB"), dtype=np.float64) / 255.0)
    w_mm, h_mm = ledger_mm(asset)
    if abs(w_mm / rgb.shape[1] - h_mm / rgb.shape[0]) > 1e-9:
        raise ValueError(f"{asset}: non-square texels")
    out = {"source": f"cc0/polyhaven/{asset}/{path.name}", "sha256": hashlib.sha256(data).hexdigest(),
           "pixels": [rgb.shape[1], rgb.shape[0]], "size_mm": [w_mm, h_mm]}
    out.update(analyse(rgb, w_mm / rgb.shape[1]))
    return out


def main(argv):
    if len(argv) != 2:
        raise SystemExit(__doc__)
    record = {
        "schema_version": 1,
        "generator": "scripts/art/timber_scan_reference.py",
        "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "ledger": str(LEDGER.relative_to(ROOT)),
        "method": {k: v for k, v in globals().items() if k.isupper() and isinstance(v, (float, tuple))},
        "scope": "a reference measurement of two CC0 scans for the focused timber patch study; not a gate or admission",
        "scans": {a: measure(a, argv[1]) for a in ASSETS},
    }
    OUT.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    for a, m in record["scans"].items():
        print(a, json.dumps({k: m[k] for k in ("seams", "windows", "apparent_ring_spacing_mm", "latewood_fraction",
                                               "contrast_p95_over_p5", "earlywood_srgb", "latewood_srgb",
                                               "early_over_late_luminance", "fibre_over_ring_rms",
                                               "fibre_rms_over_mean")}))
    print("TIMBER_SCAN_REFERENCE", OUT)


if __name__ == "__main__":
    main(sys.argv)
