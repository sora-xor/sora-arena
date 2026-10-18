"""Exact geometry and texture masks for the user-supplied SORA mark.

The mark is `Content/SourceArt/UI/sora_logo_NOtext2.svg`, pinned by SHA-256.
This module parses its two filled paths without simplification, flattens the
cubic Béziers to a stated chord tolerance and rasterizes them with analytic
supersampling. Everything that paints or carves the mark (raden, maki-e,
banners, lanterns, roof tiles) derives from these functions so the geometry
cannot drift. It runs in plain Python 3 with numpy and inside Blender.
"""

from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SVG_PATH = ROOT / "Content/SourceArt/UI/sora_logo_NOtext2.svg"
PINNED_SVG_SHA256 = "d66413a71b70e25dcb8b2f118dcfe846a6446ed1db3de53ce88fc70c16ac0910"
VIEWBOX = 350.9  # square viewBox side in SVG units
BRAND_RED_SRGB = (0xE3, 0x24, 0x2D)

_TOKEN = re.compile(r"[MmLlHhVvCcSsZz]|-?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?")


def svg_text() -> str:
    data = SVG_PATH.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != PINNED_SVG_SHA256:
        raise SystemExit(f"SORA mark changed: {SVG_PATH} has SHA-256 {digest}")
    return data.decode("utf-8")


def _path_data(text: str) -> list[str]:
    paths = re.findall(r'<path[^>]*\sd="([^"]+)"', text, flags=re.S)
    if len(paths) != 2:
        raise SystemExit(f"Expected the mark's two filled paths, found {len(paths)}")
    return paths


def _segments(d: str):
    """Yield subpaths as lists of segments: ('L', p0, p1) or ('C', p0, c1, c2, p1)."""
    tokens = _TOKEN.findall(d)
    i = 0
    cmd = None
    cur = np.zeros(2)
    start = np.zeros(2)
    last_ctrl = None
    subpath: list = []
    subpaths: list = []

    def number():
        nonlocal i
        value = float(tokens[i])
        i += 1
        return value

    while i < len(tokens):
        if re.fullmatch(r"[A-Za-z]", tokens[i]):
            cmd = tokens[i]
            i += 1
            if cmd in "Zz":
                if np.linalg.norm(cur - start) > 1e-9:
                    subpath.append(("L", cur.copy(), start.copy()))
                cur = start.copy()
                subpaths.append(subpath)
                subpath = []
                last_ctrl = None
                continue
        rel = cmd.islower()
        base = cur if rel else np.zeros(2)
        kind = cmd.upper()
        if kind == "M":
            cur = base + np.array([number(), number()])
            start = cur.copy()
            if subpath:
                subpaths.append(subpath)
                subpath = []
            cmd = "l" if rel else "L"  # implicit lineto after moveto
            last_ctrl = None
        elif kind == "L":
            p1 = base + np.array([number(), number()])
            subpath.append(("L", cur.copy(), p1))
            cur = p1
            last_ctrl = None
        elif kind == "H":
            x = number() + (cur[0] if rel else 0.0)
            p1 = np.array([x, cur[1]])
            subpath.append(("L", cur.copy(), p1))
            cur = p1
            last_ctrl = None
        elif kind == "V":
            y = number() + (cur[1] if rel else 0.0)
            p1 = np.array([cur[0], y])
            subpath.append(("L", cur.copy(), p1))
            cur = p1
            last_ctrl = None
        elif kind == "C":
            c1 = base + np.array([number(), number()])
            c2 = base + np.array([number(), number()])
            p1 = base + np.array([number(), number()])
            subpath.append(("C", cur.copy(), c1, c2, p1))
            cur = p1
            last_ctrl = c2
        elif kind == "S":
            c1 = 2 * cur - last_ctrl if last_ctrl is not None else cur.copy()
            c2 = base + np.array([number(), number()])
            p1 = base + np.array([number(), number()])
            subpath.append(("C", cur.copy(), c1, c2, p1))
            cur = p1
            last_ctrl = c2
        else:
            raise SystemExit(f"Unsupported SVG path command {cmd!r}")
    if subpath:
        subpaths.append(subpath)
    return subpaths


def _flatten(seg, tolerance: float) -> list[np.ndarray]:
    if seg[0] == "L":
        return [seg[2]]
    _, p0, c1, c2, p1 = seg
    # Chord-error bound for cubic Béziers: max second difference.
    dd = max(np.linalg.norm(p0 - 2 * c1 + c2), np.linalg.norm(c1 - 2 * c2 + p1))
    n = max(2, int(math.ceil(math.sqrt(0.75 * dd / max(tolerance, 1e-12)))))
    t = np.linspace(0.0, 1.0, n + 1)[1:, None]
    mt = 1.0 - t
    pts = mt**3 * p0 + 3 * mt**2 * t * c1 + 3 * mt * t**2 * c2 + t**3 * p1
    return list(pts)


def polygons(tolerance_svg_units: float = 0.01) -> list[list[np.ndarray]]:
    """Return the mark as two filled polygons (one per SVG path, each a list of rings).

    Coordinates are normalized so the mark's 350.9-unit circle spans [-0.5, 0.5]
    with +y up (SVG y points down).
    """
    rings_per_path = []
    for d in _path_data(svg_text()):
        rings = []
        for sub in _segments(d):
            pts = [sub[0][1]]
            for seg in sub:
                pts.extend(_flatten(seg, tolerance_svg_units))
            ring = np.array(pts)
            if np.linalg.norm(ring[0] - ring[-1]) < 1e-9:
                ring = ring[:-1]
            ring = (ring - VIEWBOX / 2) / VIEWBOX
            ring[:, 1] *= -1.0
            rings.append(ring)
        rings_per_path.append(rings)
    return rings_per_path


def all_rings(tolerance_svg_units: float = 0.01) -> list[np.ndarray]:
    return [ring for rings in polygons(tolerance_svg_units) for ring in rings]


def coverage(size: int, *, scale: float = 1.0, center=(0.0, 0.0), supersample: int = 4,
             rotation_deg: float = 0.0, tolerance_svg_units: float = 0.005) -> np.ndarray:
    """Anti-aliased [0, 1] coverage of the filled mark on a size x size raster.

    `scale` is the mark diameter as a fraction of the raster width; `center` is
    the mark centre in normalized raster units ([-0.5, 0.5], +y up). Uses the
    non-zero/even-odd agnostic union of both paths (they do not overlap).
    """
    return coverage_of_rings(size, transformed_rings(scale=scale, center=center, rotation_deg=rotation_deg,
                                                     tolerance_svg_units=tolerance_svg_units),
                             supersample=supersample)


def transformed_rings(*, scale: float = 1.0, center=(0.0, 0.0), rotation_deg: float = 0.0,
                      tolerance_svg_units: float = 0.005) -> list[np.ndarray]:
    """Mark rings placed in normalized raster space ([-0.5, 0.5], +y up)."""
    c, s = math.cos(math.radians(rotation_deg)), math.sin(math.radians(rotation_deg))
    rot = np.array([[c, -s], [s, c]])
    return [ring @ rot.T * scale + np.asarray(center) for ring in all_rings(tolerance_svg_units)]


def coverage_of_rings(size: int, rings: list[np.ndarray], *, supersample: int = 4,
                      height: int | None = None) -> np.ndarray:
    """Even-odd scanline fill of rings given in normalized raster space.

    Rings use x in [-0.5, 0.5] across the width and y in [-h/2w, h/2w] (+y up).
    """
    height = size if height is None else height
    sw, sh = size * supersample, height * supersample
    toggles = np.zeros((sh, sw + 1), dtype=np.int32)
    rows_y = (np.arange(sh) + 0.5)  # sample-row centres in pixel units, top to bottom
    for ring in rings:
        # Normalized -> supersampled pixel coordinates (x right, y down).
        px = (ring[:, 0] + 0.5) * sw
        py = (height / size * 0.5 - ring[:, 1]) * sw
        ax, ay = px, py
        bx, by = np.roll(px, -1), np.roll(py, -1)
        for x0, y0, x1, y1 in zip(ax, ay, bx, by):
            if y0 == y1:
                continue
            lo, hi = (y0, y1) if y0 < y1 else (y1, y0)
            r0 = max(0, int(math.ceil(lo - 0.5)))
            r1 = min(sh, int(math.ceil(hi - 0.5)))
            if r1 <= r0:
                continue
            ys = rows_y[r0:r1]
            xs = x0 + (ys - y0) * (x1 - x0) / (y1 - y0)
            cols = np.clip(np.ceil(xs - 0.5).astype(np.int64), 0, sw)
            np.add.at(toggles, (np.arange(r0, r1), cols), 1)
    inside = (np.cumsum(toggles[:, :sw], axis=1) & 1).astype(np.float32)
    return inside.reshape(height, supersample, size, supersample).mean(axis=(1, 3))


def signed_distance(size: int, **kwargs) -> np.ndarray:
    """Signed distance (in raster pixels, positive inside) from a 1x coverage mask."""
    from scipy import ndimage

    cov = coverage(size, **kwargs)
    inside = cov >= 0.5
    d_in = ndimage.distance_transform_edt(inside)
    d_out = ndimage.distance_transform_edt(~inside)
    # Sub-pixel refinement from coverage near the edge.
    return (d_in - d_out + (cov - 0.5)).astype(np.float32)


def blender_path_points(tolerance_svg_units: float = 0.01):
    """Rings for Blender mesh construction: list of lists of (x, y) tuples, unit diameter."""
    return [[tuple(map(float, p)) for p in ring] for ring in all_rings(tolerance_svg_units)]


if __name__ == "__main__":
    import sys

    from PIL import Image

    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "Saved/ClaudeArt/sora_mark_check.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    cov = coverage(1024, scale=0.98)
    rgb = np.zeros((1024, 1024, 4), dtype=np.uint8)
    rgb[..., 0], rgb[..., 1], rgb[..., 2] = BRAND_RED_SRGB
    rgb[..., 3] = np.round(cov * 255).astype(np.uint8)
    Image.fromarray(rgb, "RGBA").save(out)
    rings = all_rings()
    print(f"{len(rings)} rings, {sum(len(r) for r in rings)} vertices; wrote {out}")
