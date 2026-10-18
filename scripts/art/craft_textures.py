"""Procedural texture authoring for Edo lacquer craft: raden, maki-e, urushi, nanako.

Each function returns float32 numpy arrays in linear units (albedo in linear
reflectance, roughness/height in [0, 1]) so the same maps feed Blender review
renders and Unreal imports. Patterns are deterministic for a given seed.
Physical notes:

* Raden (mother-of-pearl) colour comes from thin-film interference in aragonite
  platelets; the albedo here is the diffuse body (near white), and `film`
  encodes relative platelet thickness for the shader's view-dependent hue.
  Growth lines are wavy, nearly parallel bands; atsugai (thick shell) pieces
  are polished flush with the lacquer, leaving only a fine lacquer seam.
* Hiramaki-e gold is metal powder settled in lacquer and burnished: warm gold,
  moderately rough, with a fine granular height. Nashiji scatters flakes in a
  translucent amber lacquer over black.
* Roiro (black mirror) urushi is near-black with very low roughness and faint
  polishing swirls.
"""

from __future__ import annotations

import math

import numpy as np


def rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)


def fbm(size: int, seed: int, octaves: int = 6, base: float = 4.0, persistence: float = 0.5,
        height: int | None = None) -> np.ndarray:
    """Tileable value-noise fBm in [0, 1] built from Fourier-filtered white noise."""
    height = size if height is None else height
    g = rng(seed)
    out = np.zeros((height, size), dtype=np.float64)
    amp, total = 1.0, 0.0
    fy = np.fft.fftfreq(height)[:, None] * height
    fx = np.fft.fftfreq(size)[None, :] * size
    radius = np.sqrt(fx * fx + fy * fy)
    for octave in range(octaves):
        freq = base * (2.0 ** octave)
        band = np.exp(-((radius - freq) ** 2) / (2 * (0.5 * freq) ** 2))
        noise = g.standard_normal((height, size))
        layer = np.real(np.fft.ifft2(np.fft.fft2(noise) * band))
        layer /= layer.std() + 1e-12
        out += amp * layer
        total += amp
        amp *= persistence
    out /= total
    lo, hi = np.percentile(out, [0.5, 99.5])
    return np.clip((out - lo) / (hi - lo + 1e-12), 0.0, 1.0).astype(np.float32)


def normal_from_height(height: np.ndarray, strength: float, *, directx: bool = True) -> np.ndarray:
    """Tangent-space normal map in [0, 1]; strength is height units per pixel."""
    gy, gx = np.gradient(height.astype(np.float64))
    nx, ny = -gx * strength, gy * strength  # +y up in image space (OpenGL convention)
    if directx:
        ny = -ny  # Unreal expects DirectX green (y down)
    nz = np.ones_like(nx)
    norm = np.sqrt(nx * nx + ny * ny + nz * nz)
    n = np.stack([nx / norm, ny / norm, nz / norm], axis=-1)
    return (n * 0.5 + 0.5).astype(np.float32)


# --- Raden (mother-of-pearl) -------------------------------------------------

def raden_maps(size: int, seed: int = 11, *, band_count: float = 34.0, warp: float = 0.09):
    """Return dict(albedo RGB, film [0,1], height, roughness) for a polished shell piece."""
    g = rng(seed)
    y, x = np.mgrid[0:size, 0:size].astype(np.float64) / size
    # Growth lines: concentric-ish bands around an off-piece umbo, domain-warped.
    cx, cy = -0.35 + 0.1 * g.random(), 1.25 + 0.1 * g.random()
    w1 = fbm(size, seed + 1, octaves=5, base=3.0) - 0.5
    w2 = fbm(size, seed + 2, octaves=5, base=3.0) - 0.5
    r = np.sqrt((x - cx + warp * w1) ** 2 + (y - cy + warp * w2) ** 2)
    bands = 0.5 + 0.5 * np.sin(2 * math.pi * band_count * r + 3.0 * w1)
    fine = 0.5 + 0.5 * np.sin(2 * math.pi * band_count * 5.3 * r + 7.0 * w2)
    patches = fbm(size, seed + 3, octaves=4, base=2.0)
    flakes = fbm(size, seed + 4, octaves=3, base=24.0)
    film = np.clip(0.18 + 0.42 * patches + 0.22 * bands + 0.08 * fine + 0.10 * flakes, 0, 1)
    # Body colour: silvery white with faint warm/cool drift (linear reflectance).
    drift = patches - 0.5
    albedo = np.stack([0.80 + 0.04 * drift, 0.79 + 0.01 * drift, 0.78 - 0.03 * drift], axis=-1)
    height = 0.6 * bands * 0.02 + 0.4 * fine * 0.01 + 0.5 * flakes * 0.004
    roughness = np.clip(0.07 + 0.05 * flakes + 0.03 * (1 - bands), 0, 1)
    return {"albedo": albedo.astype(np.float32), "film": film.astype(np.float32),
            "height": height.astype(np.float32), "roughness": roughness.astype(np.float32)}


def thin_film_rgb(film: np.ndarray, cos_theta: float = 1.0, n_film: float = 1.53,
                  nm_range=(260.0, 720.0)) -> np.ndarray:
    """Preview reflectance colour of a thin aragonite film (for Blender/sRGB previews).

    Two-beam interference: R(λ) ∝ 1 - cos(4π n d cosθt / λ). Uses three
    representative wavelengths; Unreal evaluates the same formula per pixel.
    """
    d = nm_range[0] + film * (nm_range[1] - nm_range[0])
    sin_t = math.sqrt(max(0.0, 1.0 - cos_theta * cos_theta)) / n_film
    cos_t = math.sqrt(1.0 - sin_t * sin_t)
    lam = np.array([650.0, 532.0, 460.0])
    phase = 4 * math.pi * n_film * d[..., None] * cos_t / lam
    return (0.5 - 0.5 * np.cos(phase)).astype(np.float32)


# --- Urushi lacquer ------------------------------------------------------------

def roiro_maps(size: int, seed: int = 21, *, base=(0.012, 0.010, 0.009)):
    """Black mirror lacquer: albedo, roughness with polish swirls, faint height."""
    g = rng(seed)
    swirl = fbm(size, seed, octaves=3, base=6.0)
    y, x = np.mgrid[0:size, 0:size].astype(np.float64) / size
    # Polishing arcs: many faint circular scratches of random centres/radii.
    scratches = np.zeros((size, size))
    for _ in range(140):
        cx, cy = g.random(2) * 1.4 - 0.2
        rad = 0.15 + 0.6 * g.random()
        width = 0.0006 + 0.0012 * g.random()
        ring = np.abs(np.sqrt((x - cx) ** 2 + (y - cy) ** 2) - rad)
        arc_mask = g.random() * 2 * math.pi
        ang = np.arctan2(y - cy, x - cx)
        span = (np.cos(ang - arc_mask) > 0.55).astype(np.float64)
        scratches += np.exp(-(ring / width) ** 2) * span * (0.3 + 0.7 * g.random())
    scratches = np.clip(scratches, 0, 1)
    albedo = np.empty((size, size, 3), dtype=np.float32)
    albedo[...] = np.array(base, dtype=np.float32)
    roughness = np.clip(0.035 + 0.025 * swirl + 0.10 * scratches, 0, 1).astype(np.float32)
    height = (0.002 * swirl - 0.004 * scratches).astype(np.float32)
    return {"albedo": albedo, "roughness": roughness, "height": height}


# --- Maki-e gold ---------------------------------------------------------------

GOLD_LINEAR = np.array([1.000, 0.766, 0.336], dtype=np.float32)   # pure gold F0
GOLD_RED_LINEAR = np.array([0.98, 0.68, 0.38], dtype=np.float32)  # aokin/akakin variation


def makie_powder(size: int, seed: int = 31, height: int | None = None):
    """Granular gold-powder roughness/height for burnished hiramaki-e."""
    from scipy import ndimage

    height = size if height is None else height
    g = rng(seed)
    grain = g.random((height, size))
    grain = ndimage.gaussian_filter(grain, 0.7)
    grain = (grain - grain.min()) / (grain.max() - grain.min() + 1e-12)
    soft = fbm(size, seed + 1, octaves=4, base=8.0, height=height)
    roughness = np.clip(0.22 + 0.12 * grain + 0.10 * soft, 0, 1).astype(np.float32)
    h = (0.6 * grain + 0.4 * soft).astype(np.float32)
    return roughness, h


def nashiji_flakes(size: int, seed: int = 41, density: float = 0.0035, height: int | None = None):
    """Sparse irregular gold flakes (coverage in [0,1]) for nashiji grounds."""
    from scipy import ndimage

    height = size if height is None else height
    g = rng(seed)
    count = int(size * height * density)
    canvas = np.zeros((height, size), dtype=np.float32)
    ys = g.integers(0, height, count)
    xs = g.integers(0, size, count)
    canvas[ys, xs] = 0.6 + 0.4 * g.random(count)
    canvas = ndimage.grey_dilation(canvas, size=(2, 3))
    canvas = ndimage.gaussian_filter(canvas, 0.6)
    return np.clip(canvas * 1.6, 0, 1)


# --- Maple leaf (momiji) and flowing water (Tatsuta-gawa) motifs ---------------

def maple_leaf_polygon(lobes: int = 7, serration: int = 11, depth: float = 0.50, seed: int = 0,
                       points: int = 1400) -> np.ndarray:
    """Acer palmatum leaf outline, unit radius, petiole at -y. Returns (N, 2)."""
    g = rng(seed)
    theta = np.linspace(0, 2 * math.pi, points, endpoint=False)
    # Lobes spread over ~300 degrees, leaving the petiole sinus at the bottom.
    spread = math.radians(300.0)
    phi = (theta - math.pi / 2) % (2 * math.pi)  # 0 at top
    phi = np.where(phi > math.pi, phi - 2 * math.pi, phi)  # (-pi, pi]
    t = np.clip(phi / (spread / 2), -1.0, 1.0)
    lobe_phase = (t + 1) / 2 * (lobes - 1)
    nearest = np.round(lobe_phase)
    off = lobe_phase - nearest  # -0.5..0.5 between lobe axes
    rank = np.abs(nearest - (lobes - 1) / 2) / ((lobes - 1) / 2)  # 0 centre lobe .. 1 basal lobes
    lobe_len = 1.0 - 0.22 * rank - 0.30 * rank ** 3
    lobe_len *= 1 + 0.06 * g.standard_normal(lobes)[nearest.astype(int)]
    # Deeply cut sinuses: radius drops toward the midpoint between lobes.
    a = np.abs(off) * 2
    profile = 1 - depth * a ** 3.2 - 0.12 * a ** 1.4  # broad ovate-lanceolate lobes, rounded sinus
    tip = np.exp(-(off / 0.05) ** 2) * 0.16  # long acuminate tips
    serr = 0.016 * np.maximum(0, np.sin(2 * math.pi * serration * off * 2)) ** 3 * (a < 0.85)
    r = lobe_len * (profile + tip) + serr
    r = np.where(np.abs(phi) > spread / 2, 0.20, r)  # petiole sinus
    x = r * np.cos(theta)
    y = r * np.sin(theta)
    return np.stack([x, y], axis=-1)


def rasterize_polygons(size: int, polys, *, supersample: int = 3, height: int | None = None) -> np.ndarray:
    """Union coverage of polygons in normalized raster space (x in [-0.5, 0.5], +y up)."""
    import sora_mark  # same directory

    return sora_mark.coverage_of_rings(size, [np.asarray(p, dtype=np.float64) for p in polys],
                                       supersample=supersample, height=height)


def stroke_polyline(size: int, lines, width: float, *, height: int | None = None) -> np.ndarray:
    """Anti-aliased round-capped strokes (width in normalized units) as coverage.

    Pure numpy (runs inside Blender): per segment, the exact distance from each
    pixel centre in its padded bounding box gives a 1-pixel analytic edge ramp.
    """
    height = size if height is None else height
    canvas = np.zeros((height, size), dtype=np.float32)
    half = width * size / 2.0  # stroke half-width in pixels
    pad = half + 1.5
    for line in lines:
        pts = np.array([((p[0] + 0.5) * size, (height / size * 0.5 - p[1]) * size) for p in line],
                       dtype=np.float64)
        for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
            lo_x = int(max(0, math.floor(min(x0, x1) - pad)))
            hi_x = int(min(size, math.ceil(max(x0, x1) + pad)))
            lo_y = int(max(0, math.floor(min(y0, y1) - pad)))
            hi_y = int(min(height, math.ceil(max(y0, y1) + pad)))
            if hi_x <= lo_x or hi_y <= lo_y:
                continue
            ys, xs = np.mgrid[lo_y:hi_y, lo_x:hi_x].astype(np.float64) + 0.5
            dx, dy = x1 - x0, y1 - y0
            ln2 = dx * dx + dy * dy
            t = np.clip(((xs - x0) * dx + (ys - y0) * dy) / ln2, 0.0, 1.0) if ln2 > 0 else 0.0
            d = np.hypot(xs - (x0 + t * dx), ys - (y0 + t * dy))
            cov = np.clip(half - d + 0.5, 0.0, 1.0).astype(np.float32)
            region = canvas[lo_y:hi_y, lo_x:hi_x]
            np.maximum(region, cov, out=region)
    return canvas
