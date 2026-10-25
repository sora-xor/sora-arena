"""Version 2.1 of the dojo timber logs (sora-timber-geometry-v2.1), for the six-member pilot.

Numpy only; mesh creation and export reuse sora_timber_lib.to_blender in Blender.
Version 1 (sora_timber_lib.py) and the frozen 6b0e93e kit are untouched: this
module only imports v1, never changes it, and writes nothing.

What v2 adds, all as real geometry on the Nanite logs:

* **Raised grain.** The planed surface's latewood stands proud of the earlywood
  by a physically scaled relief: 25-45 um indoors, 0.1-0.18 mm where hands wear
  a rail's top. The ridges come from the **same ring phase the timber
  materials shade** (shared RingNoise and Fibre arrays, the member's ring
  width, the log frame stored in UVLogQ/UVLogZ). So each ridge sits on its
  shaded latewood band. Samples are placed at fixed phases of every ring, so
  triangles run along the grain.
* **Adze (chona) faces** use v1's scallop field, sampled finely enough to
  resolve every scallop.
* **Split checks.** Each check:
  - meanders, and its opening varies along it, with fibre bridges;
  - runs on past its ends as a shallow hairline, and may fork there;
  - has an asymmetric V, depth proportional to the opening, and torn lips
    with splinters.

  Its 17 samples across are constant row to row: nothing else is sampled
  inside its zone.
* **Bokken dents** across the grain, with a crushed rim, sampled at 1.5 mm.
* **Local feature rows.** Rows added for a feature carry dense samples only on
  their own face. The arrises keep every sample in every row.
* **A slight drying twist,** on top of v1's bow.

**v2.1** fixes what the v2 pilot's run 1 renders showed:
* **Check staircase:** each check is stitched in its own frame (ladder).
* **Ring beading near knots:** rows and samples are refined until the
  materials' linear interpolation holds the rings (RING_TOL_*).
* **Knot-edge streaks:** UVLogQ stays continuous; the knot's own rings move to
  UVKnot (UV4).
* **The wobble seam at atan2's wrap:** the wobble is periodic (wobble).
* **Forks:** each names its own parent check; Y-junctions are explicit
  (junctions).

UV_CONTRACT is the importer and material mapping. material_phase is its
reference.

``check_mesh`` checks that the built mesh is closed, consistently oriented,
free of degenerate or folded triangles and of row-order crossings. It
checks that every groove runs unbroken (forks only at their recorded
Y-junctions) and that the rings stay where the log's are between vertices.
It also checks that the checks, dents, raised grain and adze have the relief
they specify. The SM5 fallback (``fallback``) keeps the checks as geometry
and leaves the rest to the bake, as in v1.
"""
from __future__ import annotations

import dataclasses
import hashlib
import math
from dataclasses import dataclass, field

import numpy as np

import sora_timber_lib as T

DIGEST_VERSION = "sora-timber-geometry-v2.1"
LATEWOOD = 0.24                        # the masters' Latewood parameter
# v2.1: between vertices the materials interpolate the log frame (UVLogQ)
# linearly, so rows and samples go wherever that would move a ring. The
# tolerance is the linear-interpolation error in rings: 0.03 where a player
# comes within about a metre (under 0.4 px at 0.3 m in game), 0.2 elsewhere
# (under half a pixel at 94 degrees and 1080p from a metre or more, for a
# 1.4-2.4 mm ring).
RING_TOL_CLOSE = 0.03
RING_TOL_FAR = 0.2
# How far past a check's zone (m) the stitching frame still follows the check.
STITCH_BAND = 0.010
# A fork shares its parent's groove for at most this long, over at most this
# many row pairs per junction (check_joins).
JUNCTION_MAX_LENGTH = 0.006
JUNCTION_MAX_PAIRS = 4
# check_mesh's limits on that ring error at triangle centroids: (p99, max).
RING_ERROR_CLOSE = (0.03, 0.10)
RING_ERROR_FAR = (0.2, 0.4)
# Ring phases sampled across every ring. The geometric ridge is piecewise
# linear through them: the flat earlywood floor (1.0 back to 0.51), the
# latewood rise (0.51-0.70-0.83), and the abrupt fall to the next year's
# earlywood (0.83-1.0). It stays within 5 um of the masters' smooth ridge at
# a 40 um relief.
RIDGE_KNOTS = np.array([0.0, 0.51, 0.70, 0.83])
# The ring-width wander, corrected from v1. v1 ran the whole 1024-texel
# RingNoise row over 6 rings (nu = r / 6w), about 170 texels per ring, and
# its +/-1.5-ring term reversed the phase hundreds of times across a face:
# fine chaotic striping, not rings. v2 runs about 3.4 texels per ring, so
# the noise's shortest wave (about 17 texels) spans about 5 rings. A 2.6-ring
# amplitude then varies ring widths by up to about +/-25% while the phase
# stays monotonic.
WANDER_RINGS_PER_UNIT = 300.0
WANDER_AMPLITUDE = 2.6
CHECK_ACROSS = np.array([-1.6, -1.0, -0.66, -0.33, 0.0, 0.33, 0.66, 1.0, 1.6])
CHECK_BEYOND = np.array([0.0003, 0.0008, 0.0016, 0.0028])


@dataclass
class MemberV2(T.Member):
    grain: dict = field(default_factory=dict)      # {face: (amp_lo, amp_hi)}: earlywood recess, metres
    grain_zone: tuple | None = None                # (z0, z1) of geometric grain; None: the whole length
    row_sp: float = 0.04
    across_sp: float = 0.02
    check_row_sp: float = 0.008
    check_end_sp: float = 0.002
    fine: float = 0.0015
    dent_sp: float = 0.0015
    grain_row_sp: float = 0.010             # also the lattice of rows along checks
    adze_sp: float = 0.004
    hw_floor: float = 0.00016
    margin: float = 0.03
    twist: float = 0.0                             # corner displacement over the length (m)


def to_v2(m: T.Member, **kw) -> MemberV2:
    """A v1 member (same log, seeds and finish) as a v2 member."""
    base = {f.name: getattr(m, f.name) for f in dataclasses.fields(T.Member)}
    return MemberV2(**{**base, **kw})


def fallback(m: MemberV2) -> MemberV2:
    """The SM5 fallback: the same log and checks at the fallback spacing; grain,
    adze scallops, knots and dents go to the bake."""
    sp = m.fallback_spacing
    return dataclasses.replace(m, name=m.name + "_Fallback", fallback=True, spacing=sp, row_sp=sp, across_sp=sp,
                               check_row_sp=sp, check_end_sp=sp, hidden_spacing=max(m.hidden_spacing, 2 * sp),
                               corner_samples=4, grain={})


# ---------------------------------------------------------------------------
# The materials' ring phase (Blender look-dev; Unreal after its V-flip fix)
# ---------------------------------------------------------------------------

def shared_arrays(seed: int = 90210):
    """The arrays sora_timber_lib.shared_textures writes, from the same RNG order."""
    rng = np.random.default_rng(seed)
    rows = []
    for _ in range(64):
        white = rng.standard_normal(1024)
        f = np.fft.rfftfreq(1024)
        with np.errstate(divide="ignore"):
            spec = np.fft.rfft(white) * np.where(f > 0, (f * 1024) ** -1.1, 0.0) * np.exp(-(f / 0.06) ** 2)
        row = np.fft.irfft(spec, 1024)
        rows.append((row - row.min()) / (row.max() - row.min() + 1e-12))
    ring_noise = (np.array(rows) * 65535).astype(np.uint16)
    ring_random = (rng.random((256, 256)) * 255).astype(np.uint8)
    fib = T._filtered_noise(rng, (1024, 1024), 0.22, 0.012)
    streak = T._filtered_noise(rng, (1024, 1024), 0.035, 0.004)
    drift = T._filtered_noise(rng, (1024, 1024), 0.004, 0.004)
    fibre = (np.stack([fib, streak, drift], -1) * 255).astype(np.uint8)
    return {"RingNoise": ring_noise, "RingRandom": ring_random, "Fibre": fibre}


def sample_linear(img: np.ndarray, u, v):
    """Blender's Linear/REPEAT lookup of a PNG array (row 0 = the file's top) at UV
    (u, v) with v up; Unreal samples the same texel at (u, 1 - v)."""
    h, w = img.shape[:2]
    x = np.asarray(u, np.float64) * w - 0.5
    y = (1.0 - np.asarray(v, np.float64)) * h - 0.5
    x0, y0 = np.floor(x), np.floor(y)
    fx, fy = x - x0, y - y0
    x0 = x0.astype(np.int64) % w
    y0 = y0.astype(np.int64) % h
    x1, y1 = (x0 + 1) % w, (y0 + 1) % h
    a = img[y0, x0] * (1 - fx) + img[y0, x1] * fx
    b = img[y1, x0] * (1 - fx) + img[y1, x1] * fx
    return a * (1 - fy) + b * fy


def ring_phase(q: np.ndarray, seed01: float, uv0: np.ndarray, ring_width: float, arrays: dict):
    """The v2 ring phase at log-frame offsets ``q`` (N, 2) and metric UV0 (N, 2): the
    v1 masters' model with the corrected wander (WANDER_*). The v2 look-dev and
    Unreal materials compute the same."""
    streak = sample_linear(arrays["Fibre"][..., 1].astype(np.float64) / 255.0, uv0[:, 0] / 0.25, uv0[:, 1] / 0.25)
    r = np.hypot(q[:, 0], q[:, 1]) + (streak - 0.5) * 0.00025
    return _phase_of_r(r, seed01, ring_width, arrays)


def _phase_of_r(r, seed01, ring_width, arrays):
    nu = r / (WANDER_RINGS_PER_UNIT * ring_width) + seed01 * 37.0
    nv = np.full_like(np.asarray(r, np.float64), (seed01 * 7.31) % 1.0)
    var = sample_linear(arrays["RingNoise"].astype(np.float64) / 65535.0, nu, nv)
    return np.asarray(r) / ring_width + (var - 0.5) * WANDER_AMPLITUDE


# ---------------------------------------------------------------------------
# The v2.1 UV contract: what each channel carries and how Unreal decodes it
# ---------------------------------------------------------------------------

UNREAL_NAMESPACE = "/Game/Generated/Qualification/DojoTimberPilotV21"
UV_CONTRACT = {
    "geometry": DIGEST_VERSION,
    "unreal_content_path": UNREAL_NAMESPACE,
    "import_decode": "Interchange imports every channel as (U, 1 - V). Decode with flip_v before reading UV0/UVLogQ/"
                     "UVLogZ/UVKnot as data; sample shared images at computed Blender coordinates through "
                     "sample_blender (flip_v again), as import_nyaagyu_dojo_timbers.py (cd10643) does.",
    "channels": [
        {"index": 0, "blender_layer": "UV0", "payload": "metric (s, z): arc length round the section, height (m)",
         "unreal": "flip_v(TexCoord[0])"},
        {"index": 1, "blender_layer": "UV1", "payload": "unique bake atlas (fallback NormalDX/Masks)",
         "unreal": "TexCoord[1] as imported"},
        {"index": 2, "blender_layer": "UVLogQ", "payload": "signed log-frame offset q = (P - pith) * r_warp / r (m). "
         "r_warp adds the periodic wobble (sora_timber_v2.wobble) and every knot's swirl. Continuous across knot "
         "edges: no knot-centred swap (that was v2).", "unreal": "flip_v(TexCoord[2])"},
        {"index": 3, "blender_layer": "UVLogZ", "payload": "(z m, seed01)", "unreal": "seed = 1 - TexCoord[3].g"},
        {"index": 4, "blender_layer": "UVKnot", "payload": "(knot ring radius r_k in the materials' ring units "
         "(0.55 mm knot rings), signed distance d from the knot's edge in knot radii, clamped to [-1, 1]); "
         "inside the knot where d < 0. Fallbacks carry (0, 1).", "unreal": "r_k = TexCoord[4].r; d = 1 - TexCoord[4].g"},
    ],
    "textures": [
        {"name": "T_TimberFibre", "pixels": "1024 x 1024 8-bit RGB, linear (no sRGB)", "sampler": "Masks",
         "use": "R fine fibres, G streaks (also the ring radius jitter), B broad drift; UV0 / 0.25 m, drift at UV0 x 0.11"},
        {"name": "T_TimberRingNoise", "pixels": "1024 x 64 16-bit grey, linear", "sampler": "LinearGrayscale",
         "use": "R: ring-width wander row per log seed, bilinear, wrap"},
        {"name": "T_TimberRingRandom", "pixels": "256 x 256 8-bit grey, linear", "sampler": "LinearGrayscale",
         "use": "R: per-year latewood strength, NEAREST filtering, wrap"},
        {"name": "T_<asset>_NormalDX (fallback only)", "pixels": "bake, DirectX green", "sampler": "Normal",
         "use": "UV1"},
        {"name": "T_<asset>_Masks (fallback only)", "pixels": "bake RGBA, linear", "sampler": "Masks",
         "use": "UV1; RGB = cavity, wear, soot; the knot weight is the sample's own alpha output, not a component of RGB"},
        {"name": "vertex colour Masks (dense)", "pixels": "per vertex RGBA floats", "sampler": "-",
         "use": "RGB = cavity, wear, soot; A = knot weight (0.55-1.0, dead knots highest)"},
    ],
    "ring": {
        "radius": "r = (d < 0 ? r_k : length(UVLogQ)) + (Fibre.G(UV0 / 0.25) - 0.5) * 0.00025",
        "phase": "r / w + (RingNoise.R(nu, nv) - 0.5) * WANDER_AMPLITUDE, nu = r / (WANDER_RINGS_PER_UNIT * w) "
                 "+ seed * 37, nv = frac(seed * 7.31); RingNoise sampled at the Blender coordinate (sample_blender)",
        "wander_rings_per_unit": WANDER_RINGS_PER_UNIT, "wander_amplitude": WANDER_AMPLITUDE,
        "knot_edge": "the select on d is per pixel; anti-alias over the pixel footprint, "
                     "inside = saturate(0.5 - d / max(fwidth(d), 1e-6))",
    },
}


def material_phase(uv0: np.ndarray, uv2: np.ndarray, uv3: np.ndarray, uv4: np.ndarray, ring_width: float,
                   arrays: dict, inside: np.ndarray | None = None):
    """The materials' ring phase from the decoded Blender channels (UV_CONTRACT):
    the reference that the look-dev graph and Unreal's timber master must
    reproduce. ``inside`` overrides the per-pixel knot select (d < 0)."""
    sel = (uv4[:, 1] < 0.0) if inside is None else inside
    q = np.where(sel[:, None], np.stack([uv4[:, 0], np.zeros(len(uv4))], 1), uv2)
    return ring_phase(q, float(uv3[0, 1]) if len(uv3) else 0.0, uv0, ring_width, arrays)


def ridge(f: np.ndarray, latewood: float = LATEWOOD):
    """The masters' latewood ridge on ring fraction ``f``: 0 in the earlywood, 1 at the ridge."""
    return T.smoothstep(1.0 - latewood - 0.25, 1.0 - latewood + 0.05, f) * (1.0 - T.smoothstep(0.82, 1.0, f))


# ---------------------------------------------------------------------------
# Checks v2
# ---------------------------------------------------------------------------

@dataclass
class CheckV2:
    face: int
    u0: float
    drift: float
    z0: float
    z1: float
    width: float
    depth: float
    meander: list                  # (amplitude, wavelength, phase) terms
    noise: list                    # opening variation terms
    bridges: list                  # (z centre, half length)
    ext0: float                    # hairline run past z0 (m)
    ext1: float
    steep: float                   # the steeper wall's width ratio (1.3-1.8)
    steep_left: bool
    ratio: float                   # depth / opening
    lip: list                      # torn-lip terms
    splinters: list                # (z centre, half length, side, height, offset)
    parent: int = -1               # a fork's parent check

    @property
    def lo(self):
        return self.z0 - self.ext0

    @property
    def hi(self):
        return self.z1 + self.ext1

    def at(self, z, straight=False):
        """Centre, left/right half-widths and depth at height(s) ``z``."""
        z = np.asarray(z, np.float64)
        span = max(1e-6, self.z1 - self.z0)
        t = np.clip((z - self.z0) / span, 0.0, 1.0)
        body = (z >= self.z0) & (z <= self.z1)
        taper = np.sin(math.pi * t) ** 0.55
        var = 0.55 + 0.45 * sum(0.5 + 0.5 * np.sin(2 * math.pi * z / lam + ph) for lam, ph in self.noise) / max(1, len(self.noise))
        w = self.width * taper * var
        for zc, hl in self.bridges:
            w = w * T.smoothstep(0.0, 1.0, np.abs(z - zc) / hl)
        hairline = ~body
        w = np.where(hairline, 0.0, w)
        uc = self.u0 + self.drift * (z - self.z0)
        if not straight:
            uc = uc + sum(a * np.sin(2 * math.pi * z / lam + ph) for a, lam, ph in self.meander)
        depth = np.minimum(self.depth, self.ratio * w)
        # The hairline past each end: a shallow fine crack fading out.
        run = np.where(z < self.z0, (self.z0 - z) / max(1e-6, self.ext0), (z - self.z1) / max(1e-6, self.ext1))
        hair_depth = 0.0004 * np.clip(1.0 - run, 0.0, 1.0)
        depth = np.where(hairline, hair_depth, depth)
        hw = np.maximum(w / 2.0, 0.0)
        a = 2.0 / (1.0 + self.steep)
        b = 2.0 * self.steep / (1.0 + self.steep)
        hl, hr = (hw * a, hw * b) if self.steep_left else (hw * b, hw * a)
        return uc, hl, hr, depth


def checks_v2(m: MemberV2):
    """v1's checks with their v2 detail, plus forked hairlines; all deterministic."""
    out = []
    for i, ck in enumerate(m.log.checks):
        h = lambda k: float(T.hash01(m.log.seed, i, k))  # noqa: E731
        n_bridges = 0 if (ck.z1 - ck.z0) < 0.6 else 1 + int(h(1) * 3)
        bridges = [(ck.z0 + (0.15 + 0.7 * h(10 + j)) * (ck.z1 - ck.z0), 0.005 + 0.010 * h(20 + j)) for j in range(n_bridges)]
        c = CheckV2(face=ck.face, u0=ck.u0, drift=ck.drift, z0=ck.z0, z1=ck.z1, width=ck.width, depth=ck.depth,
                    meander=[(0.0005 + 0.0015 * h(30 + j) / (j + 1), 0.08 + 0.12 * h(40 + j), 6.283 * h(50 + j))
                             for j in range(3)],
                    noise=[(0.02 + 0.06 * h(60 + j), 6.283 * h(70 + j)) for j in range(3)],
                    bridges=bridges, ext0=0.02 + 0.04 * h(2), ext1=0.02 + 0.04 * h(3),
                    steep=1.3 + 0.5 * h(4), steep_left=h(5) < 0.5, ratio=8.0 + 17.0 * h(6),
                    lip=[(0.00002 + 0.00006 * h(80 + j), 0.003 + 0.012 * h(90 + j), 6.283 * h(100 + j)) for j in range(3)],
                    splinters=[(ck.z0 + h(110 + j) * (ck.z1 - ck.z0), 0.0025 + 0.0075 * h(120 + j),
                                1 if h(130 + j) < 0.5 else -1, 0.00005 + 0.0001 * h(140 + j), 0.0003 + 0.0009 * h(150 + j))
                               for j in range(int((ck.z1 - ck.z0) / 0.3 * 3 * h(7)))])
        out.append(c)
        main = len(out) - 1          # v2.1: both ends' forks name this check (v2 gave a second fork the first)
        for end, z_end in ((0, ck.z0), (1, ck.z1)):
            if h(8 + end) >= 0.3:
                continue
            uc, _, _, _ = c.at(z_end)
            length = 0.02 + 0.03 * h(160 + end)
            sign = -1.0 if end == 0 else 1.0
            zf0, zf1 = (z_end - length, z_end) if end == 0 else (z_end, z_end + length)
            drift = (0.15 + 0.2 * h(170 + end)) * (1 if h(180 + end) < 0.5 else -1)
            u_start = float(uc) - (drift * (z_end - zf0) if end == 0 else 0.0)
            out.append(CheckV2(face=ck.face, u0=u_start, drift=drift, z0=zf0, z1=zf1, width=0.0004, depth=0.0008,
                               meander=[], noise=[], bridges=[], ext0=0.002, ext1=0.002, steep=1.3,
                               steep_left=True, ratio=4.0, lip=[], splinters=[], parent=main))
    return out


# ---------------------------------------------------------------------------
# Dents v2: bokken strikes across the grain
# ---------------------------------------------------------------------------

def dent_sites(m: MemberV2):
    """(face, u, z, a_u, a_z, depth, rim) per dent, independent of the sampling."""
    rng = np.random.default_rng(m.seed * 977 + 3)
    half_w, half_d = m.width / 2, m.depth / 2
    faces = []
    for f in range(4):
        if m.finish[f] == "hidden":
            continue
        half = half_d if f % 2 == 0 else half_w
        lo, hi = m.visible[f] if m.visible[f] is not None else (-half, half)
        faces.append((f, lo + 0.004, hi - 0.004, hi - lo))
    if not faces or m.dents <= 0:
        return []
    w = np.array([x[3] for x in faces])
    out = []
    for _ in range(m.dents):
        f, lo, hi, _ = faces[int(rng.choice(len(faces), p=w / w.sum()))]
        u = float(rng.uniform(lo, hi))
        z = float(np.clip(rng.normal((m.dent_zone[0] + m.dent_zone[1]) / 2, (m.dent_zone[1] - m.dent_zone[0]) / 3),
                          0.02, m.length - 0.02))
        a_u = float(rng.uniform(0.006, 0.022))
        a_z = float(max(0.0015, a_u * rng.uniform(0.12, 0.35)))
        out.append((f, u, z, a_u, a_z, float(rng.uniform(0.00015, 0.0009)), float(rng.uniform(0.00001, 0.00003))))
    return out


# ---------------------------------------------------------------------------
# Sampling
# ---------------------------------------------------------------------------

@dataclass
class SamplesV2(T.Samples):
    # Per row, every check sampled there: (check, face, centre u, zone lo, zone
    # hi, face u0, face u1, own), where own is False for the plain placeholder
    # grid just past a check's ends. ladder() stitches each check in its own frame.
    checks_at: list = field(default_factory=list)


def wobble(m: MemberV2, theta, z):
    """The log's ring wobble, periodic round the pith (v2.1).

    v1 evaluates ``log.wobble(0.08 theta, z)``. That jumps where atan2 wraps
    at theta = +-pi: a seam of up to 2.3 rings the full length of any face
    that crosses it (the pilot's open column, face 2; the frozen v1 kit has
    it too). Here the same field is sampled on a circle of the same
    circumference, so the wobble keeps its scale and has no seam."""
    return (m.log.wobble(0.08 * np.cos(theta), z) + m.log.wobble(0.08 * np.sin(theta) + 17.0, z)) / math.sqrt(2.0)


def _log_q(m: MemberV2, f, u, z, half_w, half_d):
    """UVLogQ, the warped log frame before any relief, on face ``f``'s plane at
    (u, z) as an (N, 2) array: the pith offset scaled for the log's wobble and
    every knot's swirl, as build() stores it. The materials interpolate it
    linearly and take its length per pixel, which is exact on a flat face but
    for the warp. So only the warp needs rows and samples."""
    u = np.asarray(u, np.float64)
    z = np.broadcast_to(np.asarray(z, np.float64), u.shape)
    x, y = T._face_xy(f, u, half_w, half_d)
    _mask, _kd, _kr, swirl, _dead, _kb = T._knots(m, np.stack([x, y, z], 1))
    px, py = m.log.pith_at(z)
    qx, qy = x - px, y - py
    r = np.hypot(qx, qy) + 1e-9
    r_warp = r + wobble(m, np.arctan2(qy, qx), z) * np.clip(r / 0.03, 0, 1) + swirl
    return np.stack([qx, qy], -1) * (r_warp / r)[..., None]


def _ring_radius(m: MemberV2, f, u, z, half_w, half_d):
    """|UVLogQ| on face ``f``'s plane at (u, z): the materials' ring radius."""
    return np.linalg.norm(_log_q(m, f, u, z, half_w, half_d), axis=-1)


def _interp_error(qa, qb, qm, ring_width):
    """Rings between the material's ring radius halfway along an edge
    (|mean of the end frames|) and the log's there (|qm|)."""
    return np.abs(np.linalg.norm((qa + qb) / 2, axis=-1) - np.linalg.norm(qm, axis=-1)) / ring_width


def _close_zone(m: MemberV2):
    """(z0, z1) where a player comes within about a metre: the geometric grain's
    zone, or None for a member never seen that close (and every fallback)."""
    if not m.grain:
        return None
    return m.grain_zone if m.grain_zone is not None else (0.0, m.length)


def _tol_at(m: MemberV2, z):
    close = _close_zone(m)
    z = np.asarray(z, np.float64)
    if close is None:
        return np.full(z.shape, RING_TOL_FAR)
    return np.where((z >= close[0]) & (z <= close[1]), RING_TOL_CLOSE, RING_TOL_FAR)


def _visible_span(m: MemberV2, f, half_w, half_d):
    u0, u1 = T._face_span(f, half_w, half_d, m.arris_r)
    if m.visible[f] is not None:
        u0, u1 = max(u0, m.visible[f][0]), min(u1, m.visible[f][1])
    return u0, u1


def _refine_rows(m: MemberV2, z_rows, max_passes=8, min_gap=0.0015):
    """``z_rows`` plus midpoints wherever interpolating the ring radius between
    two rows would move a ring by more than the tolerance, on any shown face.
    Knot swirls and the log's wobble bend the rings faster than a 10 mm or
    4 cm row gap can follow."""
    half_w, half_d = m.width / 2, m.depth / 2
    faces = [f for f in range(4) if m.finish[f] != "hidden"]
    grids = {}
    for f in faces:
        u0, u1 = _visible_span(m, f, half_w, half_d)
        if u1 - u0 > 0.004:
            grids[f] = np.linspace(u0 + 0.002, u1 - 0.002, max(2, int((u1 - u0) / 0.002)))
    z = np.asarray(z_rows, np.float64)
    for _ in range(max_passes):
        za, zb = z[:-1], z[1:]
        idx = np.nonzero(zb - za > min_gap)[0]
        if not idx.size:
            break
        zm = (za + zb) / 2
        err = np.zeros(zm.size)
        for f, u in grids.items():
            U = np.tile(u, idx.size)
            qa, qb = (_log_q(m, f, U, np.repeat(zz[idx], u.size), half_w, half_d) for zz in (za, zb))
            # At a third, half and two thirds of the gap: the warp isn't
            # quadratic over a long gap, so the midpoint alone can miss the worst.
            for t in (1 / 3, 0.5, 2 / 3):
                qt = _log_q(m, f, U, np.repeat(za[idx] + t * (zb[idx] - za[idx]), u.size), half_w, half_d)
                lin = (1 - t) * qa + t * qb
                e = (np.abs(np.linalg.norm(lin, axis=-1) - np.linalg.norm(qt, axis=-1)) / m.log.ring_width)
                err[idx] = np.maximum(err[idx], e.reshape(idx.size, u.size).max(1))
        new = zm[idx][err[idx] > _tol_at(m, zm[idx])]
        if not new.size:
            break
        z = np.unique(np.round(np.concatenate([z, new]), 7))
    return z


def _refine_across(m: MemberV2, f, z, u, half_w, half_d, keep_out, lo, hi, max_passes=8, min_gap=0.001):
    """Row ``u`` (sorted) plus midpoints, between ``lo`` and ``hi`` and outside
    ``keep_out``, wherever the ring radius between neighbours is off by more
    than the tolerance."""
    tol = float(_tol_at(m, z))
    for _ in range(max_passes):
        if u.size < 2:
            break
        um = (u[:-1] + u[1:]) / 2
        idx = np.nonzero((np.diff(u) > min_gap) & (um > lo) & (um < hi))[0]
        if not idx.size:
            break
        q = _log_q(m, f, np.concatenate([u[idx], u[idx + 1], um[idx]]), z, half_w, half_d)
        qa, qb, qm = np.split(q, 3)
        new = um[idx][_interp_error(qa, qb, qm, m.log.ring_width) > tol]
        for a, b in keep_out:
            new = new[(new < a) | (new > b)]
        if not new.size:
            break
        u = np.unique(np.concatenate([u, new]))
    return u


def _grain_on(m: MemberV2, f: int, z: float) -> bool:
    if m.fallback or f not in m.grain or m.finish[f] != "planed":
        return False
    return m.grain_zone is None or (m.grain_zone[0] <= z <= m.grain_zone[1])


def _phase_samples(m: MemberV2, f, z, lo, hi, half_w, half_d, arrays):
    """u where the undisplaced surface crosses each ring's sample phases (RIDGE_KNOTS)."""
    if hi - lo < 0.001:
        return np.zeros(0)
    u = np.arange(lo, hi, 0.00005)
    # v2.1: with the knots' swirl, as the stored frame has it, so the samples
    # sit on the ridges near knots too.
    r = _ring_radius(m, f, u, z, half_w, half_d)
    phase = _phase_of_r(r, (m.log.seed % 997) / 997.0, m.log.ring_width, arrays)
    out = []
    for k in RIDGE_KNOTS:
        g = phase - k
        g = g - np.round(g)           # signed distance to the nearest ring + k
        cross = np.nonzero((np.sign(g[:-1]) != np.sign(g[1:])) & (np.abs(g[:-1] - g[1:]) < 0.5))[0]
        t = g[cross] / (g[cross] - g[cross + 1])
        out.append(u[cross] + t * (u[cross + 1] - u[cross]))
    return np.concatenate(out) if out else np.zeros(0)


def sample(m: MemberV2, arrays=None) -> T.Samples:
    """The v2 sampling: closed rows like v1, with v2's feature-adaptive placement."""
    arrays = arrays if arrays is not None else shared_arrays()
    half_w, half_d = m.width / 2, m.depth / 2
    rng = np.random.default_rng(m.seed + 7001)
    checks = [c for c in checks_v2(m) if m.finish[c.face] != "hidden"]
    feet = [] if m.fallback else [ft for ft in T._knot_footprints(m)
                                  if m.finish[ft[0]] != "hidden" and T._visible(m, ft[0], ft[1])]
    dents = [] if m.fallback else dent_sites(m)
    def lattice(a, b, step):
        """Rows on the global lattice of ``step`` within [a, b]: features that
        overlap in height share their rows."""
        a, b = max(0.0, a), min(m.length, b)
        return np.arange(math.ceil(a / step), math.floor(b / step) + 1) * step if b > a else np.zeros(0)

    base = np.unique(np.round(np.concatenate([np.arange(0.0, m.length + 1e-9, m.row_sp), [m.length]]), 7))
    rows = [base]
    along = m.check_row_sp if m.fallback else m.grain_row_sp
    for f, u, zc, au, az in feet:
        rows.append(lattice(zc - az * 1.3, zc + az * 1.3, m.fine))
    for c in checks:
        rows.append(lattice(c.lo, c.hi, along))
        for zc in (c.z0, c.z1):
            rows.append(lattice(zc - 0.05, zc + 0.05, m.check_end_sp))
        for zc, hl in c.bridges:
            rows.append(lattice(zc - hl - 0.005, zc + hl + 0.005, m.check_end_sp))
        for zc, hl, *_ in c.splinters:
            rows.append(lattice(zc - hl - 0.002, zc + hl + 0.002, m.check_end_sp))
    for f, u, z, a_u, a_z, *_ in dents:
        rows.append(lattice(z - 2 * a_z, z + 2 * a_z, m.dent_sp))
    if not m.fallback and any(m.finish[f] == "adze" for f in range(4)):
        rows.append(lattice(0.0, m.length, m.adze_sp))
    if not m.fallback and m.grain:
        z0, z1 = m.grain_zone if m.grain_zone is not None else (0.0, m.length)
        rows.append(lattice(z0, z1, m.grain_row_sp))
    z_rows = np.unique(np.round(np.concatenate(rows), 7))
    z_rows = _refine_rows(m, z_rows[(z_rows >= 0) & (z_rows <= m.length)])
    base_set = set(base.tolist())

    def widened(a, b):
        """[a, b] out to the enclosing base rows. A feature's fine samples across
        the face fill every row of that window, so the change to the plain grid
        happens across a whole base-row gap. A 1 mm row gap would make needle
        triangles with unstable normals."""
        return math.floor(a / m.row_sp) * m.row_sp - 1e-9, math.ceil(b / m.row_sp) * m.row_sp + 1e-9

    feet_w = [(f, u, zc, au, az, *widened(zc - az * 1.3, zc + az * 1.3)) for f, u, zc, au, az in feet]
    dents_w = [(d, *widened(d[2] - 2 * d[4], d[2] + 2 * d[4])) for d in dents]
    checks_w = [(c, *widened(c.lo, c.hi)) for c in checks]
    hz, hs = m.handling
    corner_var = [T.Waves(rng, 6, (0.15, 2.5), 1.0) for _ in range(4)]
    tc = np.linspace(0.0, math.pi / 2, m.corner_samples, endpoint=False)
    grades = np.array([0.0025]) if m.fallback else np.array([0.0006, 0.0014, 0.0025])
    xs, ys, zz, nxs, nys, segs, us, taus, dets, starts, counts = ([] for _ in range(11))
    checks_at = []
    total = 0
    for z in z_rows:
        full = float(z) in base_set
        row_checks = []
        handled = math.exp(-((z - hz) / hs) ** 2)
        R, Pexp = [], []
        for c in range(4):
            var = float(corner_var[c](z, 0.0))
            r = m.arris_r[c] * (1.0 + 0.18 * var) + m.arris_wear[c] * handled * (0.75 + 0.25 * var)
            R.append(max(0.0006, r))
            wear_frac = min(1.0, m.arris_wear[c] * handled / max(1e-6, m.arris_r[c] + m.arris_wear[c]))
            Pexp.append(m.arris_p + (2.0 - m.arris_p) * wear_frac)
        for f in range(4):
            u0, u1 = T._face_span(f, half_w, half_d, R)
            vis = m.visible[f]
            if m.finish[f] == "hidden":
                g = np.arange(math.ceil(u0 / m.hidden_spacing), math.floor(u1 / m.hidden_spacing) + 1) * m.hidden_spacing
                u = np.concatenate([[u0], g])
                u = u[(u >= u0) & (u < u1 - 1e-7)]
            else:
                lo, hi = (vis if vis is not None else (u0, u1))
                lo, hi = max(lo, u0), min(hi, u1)
                g = np.arange(math.ceil(u0 / m.across_sp), math.floor(u1 / m.across_sp) + 1) * m.across_sp
                if vis is not None:
                    coarse = np.arange(math.ceil(u0 / m.hidden_spacing), math.floor(u1 / m.hidden_spacing) + 1) * m.hidden_spacing
                    g = np.concatenate([g[(g >= vis[0]) & (g <= vis[1])], coarse[(coarse < vis[0]) | (coarse > vis[1])]])
                pts = [np.array([u0]), u0 + grades, u1 - grades]
                spans, extra, zones = [], [], []
                for ci, (c, wa, wb) in enumerate(checks_w):
                    if c.face != f or not (wa <= z <= wb):
                        continue
                    if not (c.lo <= z <= c.hi):
                        # Just past the check: a fine plain grid where its zone will be.
                        uc0, _hl, _hr, _ = c.at(min(max(z, c.lo), c.hi), straight=False)
                        extra.append(float(uc0) + np.arange(-0.004, 0.0041, 0.0005))
                        row_checks.append((ci, f, float(uc0), float(uc0) - 0.004, float(uc0) + 0.004, u0, u1, False))
                        continue
                    uc, hl, hr, _ = c.at(z, straight=False)
                    hl, hr = max(float(hl), m.hw_floor), max(float(hr), m.hw_floor)
                    uc = float(uc)
                    own = np.concatenate([uc + np.where(CHECK_ACROSS < 0, hl, hr) * CHECK_ACROSS,
                                          uc - hl * 1.6 - CHECK_BEYOND, uc + hr * 1.6 + CHECK_BEYOND])
                    zones.append((uc - hl * 1.6 - CHECK_BEYOND[-1], uc + hr * 1.6 + CHECK_BEYOND[-1], own))
                    spans.append((uc - hl * 1.6 - 0.003, uc + hr * 1.6 + 0.003))
                    row_checks.append((ci, f, uc, zones[-1][0], zones[-1][1], u0, u1, True))
                for kf, ku, kz, au, az, wa, wb in feet_w:
                    if kf == f and wa <= z <= wb:
                        spans.append((ku - au * 1.3, ku + au * 1.3))
                        extra.append(np.arange(ku - au * 1.3, ku + au * 1.3, m.fine))
                for (df, du, dz, a_u, a_z, *_), wa, wb in dents_w:
                    if df == f and wa <= z <= wb:
                        spans.append((du - 2 * a_u, du + 2 * a_u))
                        extra.append(np.arange(du - 2 * a_u, du + 2 * a_u, m.dent_sp))
                if not m.fallback and m.finish[f] == "adze":
                    extra.append(np.arange(lo, hi, m.adze_sp))
                if _grain_on(m, f, z):
                    extra.append(_phase_samples(m, f, z, lo + 0.003, hi - 0.003, half_w, half_d, arrays))
                # The base grid stays in every row, so no stitch fans a short
                # edge across a whole face into a sliver with a meaningless normal.
                cand = np.concatenate([g, *extra]) if extra else g
                for a, b, _own in zones:
                    pad = m.across_sp / 2
                    cand = cand[(cand < a - 0.0002) | (cand > b + 0.0002)]
                    cand = cand[(np.abs(cand - (a + b) / 2) > (b - a) / 2 + pad) | ~np.isin(cand, g)]
                pts.append(cand)
                kept = np.zeros(0)
                for _a, _b, own in zones:
                    if kept.size:
                        own = own[np.min(np.abs(own[:, None] - kept[None, :]), axis=1) > 0.00005]
                    kept = np.concatenate([kept, own])
                    pts.append(own)
                u = np.unique(np.concatenate(pts))
                u = u[(u >= u0) & (u < u1 - 1e-7)]
                u = _refine_across(m, f, float(z), u, half_w, half_d,
                                   [(a - 0.0002, b + 0.0002) for a, b, _own in zones], lo, hi)
                if u.size > 1:
                    keep = np.ones(u.size, bool)
                    keep[1:] = np.diff(u) > 0.00005
                    # Never drop a check's own sample for a sliver; drop the
                    # neighbour instead.
                    own_all = np.isin(u, kept)
                    keep |= own_all
                    clash = np.zeros(u.size, bool)
                    clash[1:] |= (np.diff(u) <= 0.00005) & ~own_all[1:] & own_all[:-1]
                    clash[:-1] |= (np.diff(u) <= 0.00005) & ~own_all[:-1] & own_all[1:]
                    u = u[keep & ~clash]
            x, y = T._face_xy(f, u, half_w, half_d)
            xs.append(x)
            ys.append(y)
            nxs.append(np.full(u.size, T.FACE_N[f][0]))
            nys.append(np.full(u.size, T.FACE_N[f][1]))
            segs.append(np.full(u.size, 2 * f, np.int8))
            us.append(u)
            taus.append(2 * f + (u - u0) / max(1e-9, u1 - u0))
            if m.finish[f] == "hidden":
                dets.append(np.zeros(u.size, np.float32))
            elif vis is None:
                dets.append(np.ones(u.size, np.float32))
            else:
                dets.append(((u >= vis[0] - m.across_sp) & (u <= vis[1] + m.across_sp)).astype(np.float32))
            c = f
            cx, cy, cnx, cny = T._corner_points(c, tc, R[c], Pexp[c], half_w, half_d)
            xs.append(cx)
            ys.append(cy)
            nxs.append(cnx)
            nys.append(cny)
            segs.append(np.full(tc.size, 2 * c + 1, np.int8))
            us.append(tc)
            taus.append(2 * c + 1 + tc / (math.pi / 2))
            nxt = (f + 1) % 4
            hidden_corner = m.finish[f] == "hidden" and m.finish[nxt] == "hidden"
            dets.append(np.full(tc.size, 0.0 if hidden_corner else 1.0, np.float32))
        checks_at.append(row_checks)
        n = sum(a.size for a in xs[len(xs) - 8:])
        starts.append(total)
        counts.append(n)
        total += n
        zz.append(np.full(n, z))
    cat = np.concatenate
    return SamplesV2(x=cat(xs), y=cat(ys), z=cat(zz), nx=cat(nxs), ny=cat(nys), seg=cat(segs), u=cat(us),
                     tau=cat(taus), detail=cat(dets), row_start=np.array(starts), row_count=np.array(counts),
                     checks_at=checks_at)


# ---------------------------------------------------------------------------
# Adze v2
# ---------------------------------------------------------------------------

def _from_arris(m: MemberV2, f: int, u, width: float):
    """0 where face ``f`` can meet its arris round-over (at the widest radius
    the arris reaches anywhere along the member), rising smoothly to 1 over
    ``width``."""
    half = (m.depth if f % 2 == 0 else m.width) / 2
    lo_c, hi_c = (f - 1) % 4, f
    r_lo = m.arris_r[lo_c] * 1.18 + m.arris_wear[lo_c]
    r_hi = m.arris_r[hi_c] * 1.18 + m.arris_wear[hi_c]
    d = np.minimum(u - (-half + r_lo), (half - r_hi) - u)
    t = np.clip(d / width, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def adze(m: MemberV2, u, z, f):
    """Chona-hatsuri, v1's staggered scoops with a C1 rim. v1 used
    (1 - q) ** 0.8, which is infinitely steep at the rim and folded once
    sampled. Each scoop is (1 - q) ** 2; the deepest cut wins, so neighbouring
    scoops still meet in crisp creases. Plus v1's slow undulation."""
    seed = m.seed * 131 + f * 17
    rng = np.random.default_rng(seed)
    a = rng.uniform(0.034, 0.042)       # lane width across the face
    b = rng.uniform(0.050, 0.064)       # scoop pitch along the member
    j0 = np.floor(u / a).astype(np.int64)
    best = np.zeros(u.size)
    for dj in (-1, 0, 1):
        j = j0 + dj
        zoff = (j % 2) * b * 0.5 + (T.hash01(seed, j, 7) - 0.5) * b * 0.4
        k0 = np.floor((z - zoff) / b).astype(np.int64)
        for dk in (-1, 0, 1):
            k = k0 + dk
            uc = (j + 0.5 + (T.hash01(seed, j, k, 1) - 0.5) * 0.3) * a
            zc = zoff + (k + 0.5 + (T.hash01(seed, j, k, 2) - 0.5) * 0.35) * b
            dep = 0.0009 + 0.0014 * T.hash01(seed, j, k, 3)
            ru = a * (0.70 + 0.12 * T.hash01(seed, j, k, 4))
            dz = z - zc
            rz = np.where(dz > 0, 0.95 * b, 0.55 * b)
            q = ((u - uc) / ru) ** 2 + (dz / rz) ** 2
            best = np.minimum(best, -dep * np.clip(1.0 - q, 0.0, None) ** 2)
    return best + T._adze_undulation(m, f, u, z) - 0.001


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def ladder(S):
    """sora_timber_lib.ladder, with every check stitched in its own frame (v2.1).

    v1's ladder pairs consecutive rows by position along the face (tau). A
    check's meander moves it up to about 3 mm sideways between rows, several
    of its own half-widths. So pairing by position joined most rows' V-bottom
    to the next row's wall or lip: the groove closed and reopened, offset,
    every row (the pilot's staircase).

    Here each row's keys on a check's face are taken from the row before's own
    face frame, shifted by the check's sideways move since then: fully across
    its zone, blending back to the row's own keys STITCH_BAND beyond. So each
    of its samples meets its counterpart. The keys stay strictly increasing
    along every row, which the merge needs, because the shift is far smaller
    than the band. A reordering raises.
    """
    out_t = []
    out_w = []
    checks_at = getattr(S, "checks_at", None) or []
    for i in range(S.row_start.size - 1):
        a0, na = S.row_start[i], S.row_count[i]
        b0, nb = S.row_start[i + 1], S.row_count[i + 1]
        ta = S.tau[a0:a0 + na]
        tb = S.tau[b0:b0 + nb]
        if checks_at:
            before = {c[0]: c for c in checks_at[i]}
            shifted = None
            # Where frames overlap, the groove that continues through both rows
            # wins (applied last); then one just starting; then one ending into
            # its placeholder grid. A placeholder in both rows has no groove to
            # follow at all.
            def rank(e):
                was = e[0] in before and before[e[0]][7]
                return 2 if (e[7] and was) else 1 if e[7] else 0
            for ci, f, uc, lo, hi, u0, u1, own in sorted(checks_at[i + 1], key=rank):
                if ci not in before or not (own or before[ci][7]):
                    continue
                _ci, _f, uc_a, _lo, _hi, u0_a, u1_a, _own = before[ci]
                shifted = tb.copy() if shifted is None else shifted
                u = S.u[b0:b0 + nb]
                w = np.clip(1.0 - np.maximum(np.maximum(lo - u, u - hi), 0.0) / STITCH_BAND, 0.0, 1.0)
                # Where the row before had this sample, in its own face frame:
                # the arris radius changes a face's span row to row, so
                # matching tau alone can miss a sample spacing.
                follow = 2 * f + (u - (uc - uc_a) - u0_a) / (u1_a - u0_a)
                on = S.seg[b0:b0 + nb] == 2 * f
                shifted = np.where(on, (1.0 - w) * shifted + w * follow, shifted)
            if shifted is not None:
                if not np.all(np.diff(shifted) > 0):
                    raise ValueError(f"ladder: a check's stitching frame reorders row {i + 1}")
                tb = shifted
        # v1's merge: extended sequences, elements 1..n then the first again (+8 round).
        ka = np.concatenate([ta[1:], [ta[0] + 8.0]])
        kb = np.concatenate([tb[1:], [tb[0] + 8.0]])
        keys = np.concatenate([ka, kb])
        is_a = np.concatenate([np.ones(na, bool), np.zeros(nb, bool)])
        order = np.argsort(keys, kind="stable")
        isa = is_a[order]
        ca = np.cumsum(isa)
        cb = np.cumsum(~isa)
        cur_a = ca - isa
        cur_b = cb - (~isa)
        ia = lambda k: a0 + (k % na)  # noqa: E731
        ib = lambda k: b0 + (k % nb)  # noqa: E731
        t = np.where(isa[:, None],
                     np.stack([ia(cur_a), ia(ca), ib(cur_b)], 1),
                     np.stack([ia(cur_a), ib(cb), ib(cur_b)], 1))
        w = np.where(isa[:, None],
                     np.stack([cur_a >= na, ca >= na, cur_b >= nb], 1),
                     np.stack([cur_a >= na, cb >= nb, cur_b >= nb], 1))
        out_t.append(t)
        out_w.append(w)
    return np.concatenate(out_t).astype(np.int64), np.concatenate(out_w)


def _row_arc(P, S):
    s = np.zeros(P.shape[0])
    row_len = np.zeros(S.row_start.size)
    for i, (st, ct) in enumerate(zip(S.row_start, S.row_count)):
        seg = np.hypot(np.diff(P[st:st + ct, 0], append=P[st, 0]), np.diff(P[st:st + ct, 1], append=P[st, 1]))
        s[st:st + ct] = np.concatenate([[0.0], np.cumsum(seg[:-1])])
        row_len[i] = seg.sum()
    return s, row_len


def build(m: MemberV2, arrays=None):
    """Sample, displace and attribute a v2 member: the same dict as
    sora_timber_lib.build_member, so to_blender, the bake and the look-dev work
    unchanged. Adds the grain relief and ring phase used, for the checks."""
    arrays = arrays if arrays is not None else shared_arrays()
    S = sample(m, arrays)
    N = S.x.size
    disp = np.zeros(N)
    adze_depth = np.zeros(N)
    face_detail = (S.seg % 2 == 0) & (S.detail > 0)
    for f in range(4):
        sel = (S.seg == 2 * f) & (S.detail > 0)
        if not sel.any():
            continue
        # The hewn face meets the arris: the cut shallows out over the last 8 mm
        # and is exactly zero where the round-over starts, in every row.
        to_arris = _from_arris(m, f, S.u[sel], 0.008)
        if m.fallback:
            if m.finish[f] == "adze":
                disp[sel] += (T._adze_undulation(m, f, S.u[sel], S.z[sel]) - 0.001) * to_arris
            continue
        if m.finish[f] == "planed":
            disp[sel] += T._plane_strokes(m, S, f, sel)
        elif m.finish[f] == "adze":
            h = adze(m, S.u[sel], S.z[sel], f) * to_arris
            disp[sel] += h
            adze_depth[sel] = -h
    check_depth = np.zeros(N)
    check_core = np.zeros(N, bool)
    check_zone = np.zeros(N, bool)
    for c in checks_v2(m):
        if m.finish[c.face] == "hidden":
            continue
        sel = (S.seg == 2 * c.face) & (S.z >= c.lo) & (S.z <= c.hi) & (S.detail > 0)
        if not sel.any():
            continue
        z = S.z[sel]
        uc, hl, hr, dz = c.at(z, straight=False)
        hl = np.maximum(hl, m.hw_floor)
        hr = np.maximum(hr, m.hw_floor)
        du = S.u[sel] - uc
        rel = np.where(du < 0, -du / hl, du / hr)
        cut = dz * np.clip(1.0 - rel, 0.0, None) ** 1.15
        lip = sum(a * np.sin(2 * math.pi * z / lam + ph) for a, lam, ph in c.lip) if c.lip else 0.0
        lips = np.where((rel >= 1.0) & (rel < 1.6), lip * (1 - (rel - 1.0) / 0.6) + 0.00004 * (1 - (rel - 1.0) / 0.6), 0.0)
        raised = np.zeros(z.size)
        for zc, half, side, height, offset in c.splinters:
            along = np.clip(1.0 - np.abs(z - zc) / half, 0.0, 1.0)
            edge = (hr if side > 0 else hl) * 1.6
            across = np.exp(-((side * du - edge - offset) / 0.0004) ** 2)
            raised += height * along * across
        disp[sel] += -cut - lips + raised
        check_depth[sel] = np.maximum(check_depth[sel], cut)
        check_core[np.nonzero(sel)[0][rel < 1.6]] = True
        check_zone[np.nonzero(sel)[0][(du > -(hl * 1.6 + CHECK_BEYOND[-1] + 0.0016))
                                      & (du < hr * 1.6 + CHECK_BEYOND[-1] + 0.0016)]] = True
    dent_disp = np.zeros(N)
    if not m.fallback:
        for df, du0, dz0, a_u, a_z, dep, rim in dent_sites(m):
            sel = (S.seg == 2 * df) & (np.abs(S.z - dz0) < 3 * a_z) & (np.abs(S.u - du0) < 3 * a_u)
            if not sel.any():
                continue
            e = ((S.u[sel] - du0) / a_u) ** 2 + ((S.z[sel] - dz0) / a_z) ** 2
            dish = -dep * np.exp(-e)
            ring = rim * np.exp(-((np.sqrt(e) - 1.6) / 0.35) ** 2)
            dent_disp[sel] += dish + ring
        disp += dent_disp
    rng = np.random.default_rng(m.seed + 41)
    ang = rng.uniform(0, T.TAU)
    bow = m.bow * np.sin(math.pi * S.z / m.length)
    P = np.stack([S.x, S.y, S.z], 1)
    mask, kd, kr, swirl, dead, kb = T._knots(m, P)
    if not m.fallback:
        disp += np.where(S.detail > 0, kb, 0.0)
    P[:, 0] += S.nx * disp + bow * math.cos(ang)
    P[:, 1] += S.ny * disp + bow * math.sin(ang)
    if m.twist:
        phi = m.twist / math.hypot(m.width / 2, m.depth / 2) * (S.z / m.length - 0.5)
        c, s = np.cos(phi), np.sin(phi)
        P[:, 0], P[:, 1] = c * P[:, 0] - s * P[:, 1], s * P[:, 0] + c * P[:, 1]
    # The log frame, taken before the grain relief, is what the materials read (UVLogQ).
    px, py = m.log.pith_at(P[:, 2])
    qx, qy = P[:, 0] - px, P[:, 1] - py
    r = np.hypot(qx, qy) + 1e-9
    theta = np.arctan2(qy, qx)
    r_warp = r + wobble(m, theta, P[:, 2]) * np.clip(r / 0.03, 0, 1) + swirl
    q2x, q2y = qx * (r_warp / r), qy * (r_warp / r)
    inside = (kd < kr) & (not m.fallback)
    # v2.1: UVLogQ stays the log frame everywhere, continuous across a knot's
    # edge. v2 swapped in knot-centred rings inside, so triangles across the
    # edge blended two frames tens of rings apart: radial streaks.
    # The knot's own rings go to UVKnot = (r, d):
    # - r, its centred ring radius in the materials' units (0.55 mm rings);
    # - d, the signed distance from its edge in knot radii, clamped to [-1, 1].
    # The materials take the knot's rings where the interpolated d < 0, so the
    # edge is a smooth line through the triangles. A fallback keeps no knot
    # rings (d = 1), as before.
    knot_rings = m.log.ring_width / 0.00055
    near = np.isfinite(kd) & (not m.fallback)
    uv4 = np.stack([np.where(near, kd, 0.0) * knot_rings,
                    np.where(near, np.clip((kd - kr) / kr, -1.0, 1.0), 1.0)], 1)
    s, row_len = _row_arc(P, S)
    seed01 = (m.log.seed % 997) / 997.0
    grain_disp = np.zeros(N)
    phase = np.zeros(N)
    gsel = np.zeros(N, bool)
    for f, (lo, hi) in m.grain.items():
        sel = (S.seg == 2 * f) & (S.detail > 0) & ~inside & ~check_core
        if m.grain_zone is not None:
            sel &= (S.z >= m.grain_zone[0]) & (S.z <= m.grain_zone[1])
        if m.fallback or m.finish[f] != "planed" or not sel.any():
            continue
        idx = np.nonzero(sel)[0]
        ph = ring_phase(np.stack([q2x[idx], q2y[idx]], 1), seed01, np.stack([s[idx], P[idx, 2]], 1), m.log.ring_width, arrays)
        amp = lo + (hi - lo) * float(T.hash01(m.seed, f, 909))
        # Fade in over 3 cm at the zone ends, over 3 mm from where each arris's
        # round-over starts, and in dents (crushed fibres).
        fade = _from_arris(m, f, S.u[idx], 0.003)
        if m.grain_zone is not None:
            fade *= np.clip((S.z[idx] - m.grain_zone[0]) / 0.03, 0, 1) * np.clip((m.grain_zone[1] - S.z[idx]) / 0.03, 0, 1)
        fade *= np.clip(1.0 + dent_disp[idx] / 0.0002, 0, 1)
        h = amp * fade * (ridge(np.mod(ph, 1.0)) - 1.0)
        grain_disp[idx] = h
        phase[idx] = ph
        gsel[idx] = True
        P[idx, 0] += S.nx[idx] * h
        P[idx, 1] += S.ny[idx] * h
    tris, wrap = ladder(S)
    caps = T.end_caps(S, N) if m.end_caps else None
    row_of = np.repeat(np.arange(S.row_start.size), S.row_count)
    cavity = np.clip(check_depth / 0.004, 0, 1) * 0.9 + np.clip(adze_depth / 0.0025, 0, 1) * 0.35
    cavity = np.clip(cavity + mask * 0.15 + np.clip(-grain_disp / 0.0002, 0, 1) * 0.08, 0, 1)
    hz, hs = m.handling
    handled = np.exp(-((P[:, 2] - hz) / hs) ** 2)
    corner = (S.seg % 2 == 1).astype(np.float64)
    faces = S.seg % 2 == 0
    half = np.where((S.seg // 2) % 2 == 0, m.depth / 2, m.width / 2)
    from_arris = np.zeros(N)
    from_arris[faces] = half[faces] - np.abs(S.u[faces])
    near_corner = np.zeros(N)
    near_corner[faces] = np.clip(1.0 - from_arris[faces] / 0.012, 0, 1)
    broad = np.where(faces, np.clip(1.0 - from_arris / 0.045, 0, 1), 1.0)
    wear_noise = T.Waves(np.random.default_rng(m.seed + 77), 10, (0.02, 0.6), 0.5)
    shown = (S.detail > 0).astype(np.float64)
    grime = np.clip(broad * handled * (0.75 + 0.5 * wear_noise(S.tau * 0.1, P[:, 2])), 0, 1)
    edge = np.clip(np.maximum(corner, near_corner) * handled * (0.7 + wear_noise(S.tau * 0.1 + 3.0, P[:, 2])), 0, 1)
    wear = np.clip(0.5 * grime + 0.5 * edge, 0, 1) * shown
    soot_noise = T.Waves(np.random.default_rng(m.seed + 78), 10, (0.05, 1.5), 0.25)
    streak_field = T.Waves(np.random.default_rng(m.seed + 79), 14, (0.006, 0.05), 1.0)
    streaks = np.clip((streak_field(s, P[:, 2] * 0.04) - 0.35) * 1.6, 0, 1) * T.smoothstep(m.soot_from * 0.6, m.length, P[:, 2])
    floor_dirt = T.smoothstep(0.35, 0.0, P[:, 2]) * 0.55
    soot = np.clip(T.smoothstep(m.soot_from, m.length, P[:, 2]) * 0.55 + streaks * 0.45 + floor_dirt + cavity * 0.4
                   + soot_noise(S.tau * 0.1, P[:, 2]), 0, 1)
    knot_a = np.clip(mask * (0.55 + 0.45 * dead), 0, 1)
    colors = np.stack([cavity, wear, soot, knot_a], 1).astype(np.float32)
    return {
        "verts": P, "tris": tris, "wrap": wrap, "caps": caps, "s": s, "row_len": row_len, "row_of": row_of, "z": P[:, 2],
        "uv2": np.stack([q2x, q2y], 1), "uv3": np.stack([P[:, 2], np.full(N, seed01)], 1), "uv4": uv4, "colors": colors,
        "samples": S, "grain_disp": grain_disp, "grain_phase": phase, "grain_sel": gsel, "dent_disp": dent_disp,
        "check_depth": check_depth, "check_zone": check_zone, "knot_mask": mask, "adze_depth": adze_depth,
    }


def to_blender(name, B, m: MemberV2):
    """sora_timber_lib.to_blender, plus v2.1's UVKnot layer (UV4, after UVLogZ)."""
    obj = T.to_blender(name, B, m)
    me = obj.data
    vi = np.empty(len(me.loops), np.int32)
    me.loops.foreach_get("vertex_index", vi)
    uv4 = B["uv4"] if B["caps"] is None else np.concatenate([B["uv4"], [[0.0, 1.0], [0.0, 1.0]]])
    layer = me.uv_layers.new(name="UVKnot")
    layer.data.foreach_set("uv", uv4[vi].astype(np.float32).ravel())
    return obj


def canonical_digest(obj) -> str:
    """The v1 canonical digest of the mesh, namespaced under the v2 version."""
    return hashlib.sha256(f"{DIGEST_VERSION}:{T.canonical_digest(obj)}".encode()).hexdigest()


# ---------------------------------------------------------------------------
# Topology and feature checks
# ---------------------------------------------------------------------------

def _all_tris(B, m):
    P = B["verts"]
    S = B["samples"]
    tris = B["tris"]
    caps = B["caps"]
    if caps:
        ends = []
        for row in (0, S.row_start.size - 1):
            st, ct = S.row_start[row], S.row_count[row]
            ends.append(P[st:st + ct].mean(0))
        P = np.concatenate([P, np.array(ends)])
        tris = np.concatenate([tris] + list(caps))
    return P, tris


def junctions(m: MemberV2):
    """Every true Y-junction: where checks_v2 starts a forked hairline at its
    parent check's end. [(fork, parent, face, z)], indices in checks_v2 order.
    These are the only places a groove may part from the strip of rows."""
    cs = checks_v2(m)
    out = []
    for j, c in enumerate(cs):
        if c.parent < 0 or m.finish[c.face] == "hidden":
            continue
        par = cs[c.parent]
        # A fork before the parent ends at its z0; one after starts at its z1.
        z = c.z1 if abs(c.z1 - par.z0) <= abs(c.z0 - par.z1) else c.z0
        out.append((j, c.parent, c.face, float(z)))
    return out


def check_joins(B, m: MemberV2):
    """Every check on a shown face, forks included: of its consecutive rows
    (z0..z1), how many join their V-bottoms (the samples nearest its centre)
    with an edge. A row pair that doesn't is a step in the groove (a staircase).

    The one exception is a recorded Y-junction (junctions()). Its window is
    the rows where the fork and its parent both have their own samples and
    their V's overlap: one groove there, parting into two. A pair touching
    that window may join a V-bottom to the other branch's instead of its own,
    but must stay continuous. Each V-bottom must join a V-bottom of either
    branch in the adjacent row. The window is bounded (JUNCTION_MAX_LENGTH,
    JUNCTION_MAX_PAIRS). Returns (per-check joins, per-junction records)."""
    S, t = B["samples"], B["tris"]
    n = S.x.size + 2
    e = np.sort(np.concatenate([t[:, [0, 1]], t[:, [1, 2]], t[:, [2, 0]]]), 1)
    edge_set = set((e[:, 0] * n + e[:, 1]).tolist())
    z_row = S.z[S.row_start]
    cs = checks_v2(m)
    shown = [i for i, c in enumerate(cs) if m.finish[c.face] != "hidden"]      # sample()'s check order
    own = {}                                                                     # check -> {row: centre u}
    for k, entries in enumerate(getattr(S, "checks_at", None) or []):
        for ci, _f, uc, _lo, _hi, _u0, _u1, is_own in entries:
            if is_own:
                own.setdefault(shown[ci], {})[k] = uc

    def bottom(i, k):
        c = cs[i]
        st, ct = S.row_start[k], S.row_count[k]
        idx = st + np.nonzero(S.seg[st:st + ct] == 2 * c.face)[0]
        return int(idx[np.argmin(np.abs(S.u[idx] - float(c.at(z_row[k])[0])))])

    def joined(a, b):
        return (min(a, b) * n + max(a, b)) in edge_set

    def reach(c, z):
        _uc, hl, hr, _d = c.at(z)
        return 1.6 * max(float(hl), float(hr), m.hw_floor)

    records, exempt = [], {}
    for j, par, f, zj in junctions(m):
        both = sorted(set(own.get(j, {})) & set(own.get(par, {})))
        window = [k for k in both if abs(own[j][k] - own[par][k]) < reach(cs[j], z_row[k]) + reach(cs[par], z_row[k])]
        pairs, continuous = [], True
        for i, other in ((j, par), (par, j)):
            for k0 in sorted({k - 1 for k in window} | set(window)):
                k1 = k0 + 1
                if k0 not in own.get(i, {}) or k1 not in own.get(i, {}):
                    continue
                if not (cs[i].z0 <= z_row[k0] <= cs[i].z1 and cs[i].z0 <= z_row[k1] <= cs[i].z1):
                    continue
                a, b = bottom(i, k0), bottom(i, k1)
                if joined(a, b):
                    continue
                # Not its own: it must reach the other branch's V-bottom, both ways.
                alt0 = bottom(other, k0) if k0 in own.get(other, {}) else None
                alt1 = bottom(other, k1) if k1 in own.get(other, {}) else None
                fwd = alt1 is not None and joined(a, alt1)
                back = alt0 is not None and joined(alt0, b)
                ok = (fwd or (alt0 is not None and joined(alt0, alt1 if alt1 is not None else b))) and (back or fwd)
                continuous &= bool(ok)
                exempt.setdefault(i, set()).add(k0)
                pairs.append({"check": i, "z": [round(float(z_row[k0]), 5), round(float(z_row[k1]), 5)],
                              "to_other_branch": bool(fwd or back), "continuous": bool(ok),
                              "branch_offset_mm": round(1e3 * abs(own[j].get(k0, own[j].get(k1, 0.0)) -
                                                                  own[par].get(k0, own[par].get(k1, 0.0))), 3)})
        zs = [float(z_row[k]) for k in window]
        records.append({"fork": j, "parent": par, "face": f, "z": round(zj, 5),
                        "window_rows": len(window), "window_length_m": round(max(zs) - min(zs), 5) if zs else 0.0,
                        "exempt_pairs": pairs, "continuous": bool(continuous)})
    out = []
    for i, c in enumerate(cs):
        if m.finish[c.face] == "hidden":
            continue
        rows = np.nonzero((z_row >= c.z0) & (z_row <= c.z1))[0]
        if rows.size < 2:
            continue
        pairs = [(int(a), int(b)) for a, b in zip(rows, rows[1:]) if b == a + 1]
        ok = [joined(bottom(i, a), bottom(i, b)) for a, b in pairs]
        at_junction = [a in exempt.get(i, ()) for a, b in pairs]
        out.append({"check": i, "fork": c.parent >= 0, "row_pairs": len(pairs), "joined": int(sum(ok)),
                    "junction_pairs": int(sum(at_junction)),
                    "steps": int(sum(1 for o, jn in zip(ok, at_junction) if not o and not jn))})
    return out, records


def ring_error(B, m: MemberV2):
    """How far the materials' rings sit from the log's between vertices: at
    every shown side triangle's centroid, the interpolated |UVLogQ| against the
    frame build() would store there, in rings. Reported for the close zone and
    the rest. As in build(), the frame is taken before the grain relief, with
    the knots' swirl at the undeformed surface."""
    P, S, t = B["verts"], B["samples"], B["tris"]
    shown = (S.seg % 2 == 0) & (S.detail > 0)
    tt = t[shown[t].all(1)]
    pre = P.copy()
    pre[:, 0] -= S.nx * B["grain_disp"]
    pre[:, 1] -= S.ny * B["grain_disp"]
    cen = pre[tt].mean(1)
    undeformed = np.stack([S.x, S.y, S.z], 1)[tt].mean(1)
    _mask, _kd, _kr, swirl, _dead, _kb = T._knots(m, undeformed)
    px, py = m.log.pith_at(cen[:, 2])
    qx, qy = cen[:, 0] - px, cen[:, 1] - py
    r = np.hypot(qx, qy) + 1e-9
    exact = r + wobble(m, np.arctan2(qy, qx), cen[:, 2]) * np.clip(r / 0.03, 0, 1) + swirl
    q = B["uv2"][tt].mean(1)
    err = np.abs(np.hypot(q[:, 0], q[:, 1]) - exact) / m.log.ring_width
    close = _close_zone(m)
    in_close = np.zeros(err.size, bool) if close is None else (cen[:, 2] >= close[0]) & (cen[:, 2] <= close[1])
    out = {}
    for name, sel in (("close", in_close), ("far", ~in_close)):
        if sel.any():
            out[name] = {"triangles": int(sel.sum()), "p50": round(float(np.percentile(err[sel], 50)), 4),
                         "p99": round(float(np.percentile(err[sel], 99)), 4), "max": round(float(err[sel].max()), 4)}
    return out


def check_mesh(B, m: MemberV2):
    """Topology and feature checks of a built member. Returns {"ok", "failures", "metrics"}."""
    failures, metrics = [], {}
    P, tris = _all_tris(B, m)
    S = B["samples"]
    n_side = B["tris"].shape[0]
    # Closed and consistently oriented: every edge once in each direction.
    e = np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]])
    und = np.sort(e, 1)
    key = und[:, 0] * (P.shape[0] + 1) + und[:, 1]
    _, cnt = np.unique(key, return_counts=True)
    metrics["edges"] = int(cnt.size)
    metrics["edges_not_shared_by_two"] = int(np.sum(cnt != 2))
    if metrics["edges_not_shared_by_two"]:
        failures.append(f"{metrics['edges_not_shared_by_two']} edges are not shared by exactly two triangles (not closed)")
    dkey = e[:, 0] * (P.shape[0] + 1) + e[:, 1]
    metrics["repeated_directed_edges"] = int(dkey.size - np.unique(dkey).size)
    if metrics["repeated_directed_edges"]:
        failures.append(f"{metrics['repeated_directed_edges']} directed edges repeat (inconsistent winding)")
    a, b, c = P[tris[:, 0]], P[tris[:, 1]], P[tris[:, 2]]
    cr = np.cross(b - a, c - a)
    area = 0.5 * np.linalg.norm(cr, axis=1)
    metrics["volume_m3"] = float(np.sum(np.einsum("ij,ij->i", a, np.cross(b, c))) / 6.0)
    if metrics["volume_m3"] <= 0:
        failures.append("the surface's signed volume is not positive (faces point inward)")
    metrics["degenerate_triangles"] = int(np.sum(area < 1e-14))
    if metrics["degenerate_triangles"]:
        failures.append(f"{metrics['degenerate_triangles']} triangles have (near) zero area")
    # Folds: side triangles must face the way their samples' section normals do.
    n = cr[:n_side] / (np.linalg.norm(cr[:n_side], axis=1, keepdims=True) + 1e-30)
    t = B["tris"]
    expect = np.stack([S.nx[t].mean(1), S.ny[t].mean(1), np.zeros(n_side)], 1)
    expect /= np.linalg.norm(expect, axis=1, keepdims=True) + 1e-30
    dots = np.einsum("ij,ij->i", n, expect)
    in_check = (B["check_depth"][t] > 0).any(1)
    metrics["min_dot_outside_checks"] = float(dots[~in_check].min()) if (~in_check).any() else 1.0
    metrics["min_dot_in_checks"] = float(dots[in_check].min()) if in_check.any() else 1.0
    # A fold faces away from the surface. Steep relief (a dent wall, an adze
    # crease, a check wall at up to ~89 degrees) is legitimate and only counted.
    folded = int(np.sum(dots[~in_check] <= 0.0)) + int(np.sum(dots[in_check] < -0.05))
    metrics["folded_triangles"] = folded
    metrics["steep_triangles_outside_checks"] = int(np.sum(dots[~in_check] < 0.2))
    if folded:
        failures.append(f"{folded} triangles fold back against the surface")
    # Slivers: longest edge over the height to it, outside check zones (whose
    # along-crack triangles are long by design).
    la, lb, lc = (np.linalg.norm(P[t[:, i]] - P[t[:, (i + 1) % 3]], axis=1) for i in range(3))
    longest = np.maximum(np.maximum(la, lb), lc)
    height = 2.0 * area[:n_side] / (longest + 1e-30)
    aspect = longest / (height + 1e-30)
    out_aspect = aspect[~in_check]
    metrics["aspect_p99_outside_checks"] = round(float(np.percentile(out_aspect, 99)), 1) if out_aspect.size else 0.0
    metrics["aspect_max_outside_checks"] = round(float(out_aspect.max()), 1) if out_aspect.size else 0.0
    # Needles (an interior angle near 180 degrees, three nearly collinear
    # points) have unstable normals; thin wedges with a tiny angle are fine.
    def angle(p, q, r):
        v1, v2 = P[t[:, q]] - P[t[:, p]], P[t[:, r]] - P[t[:, p]]
        cosv = np.einsum("ij,ij->i", v1, v2) / (np.linalg.norm(v1, axis=1) * np.linalg.norm(v2, axis=1) + 1e-30)
        return np.degrees(np.arccos(np.clip(cosv, -1, 1)))
    max_angle = np.maximum(np.maximum(angle(0, 1, 2), angle(1, 2, 0)), angle(2, 0, 1))
    out_angle = max_angle[~in_check]
    metrics["max_angle_outside_checks_deg"] = round(float(out_angle.max()), 3) if out_angle.size else 0.0
    metrics["needles_over_175deg_outside_checks"] = int(np.sum(out_angle > 175.0))
    if out_angle.size and out_angle.max() > 179.0:
        failures.append(f"a needle triangle outside the checks has a {out_angle.max():.2f} degree angle (> 179)")
    # Row order: along each face in each row, samples stay in order once displaced.
    crossings = 0
    for st, ct in zip(S.row_start, S.row_count):
        seg = S.seg[st:st + ct]
        for f in range(4):
            idx = st + np.nonzero(seg == 2 * f)[0]
            if idx.size < 2:
                continue
            tang = T.FACE_T[f]
            proj = P[idx, 0] * tang[0] + P[idx, 1] * tang[1]
            crossings += int(np.sum(np.diff(proj) <= 0))
    metrics["row_order_crossings"] = crossings
    if crossings:
        failures.append(f"{crossings} samples cross their neighbours along a row (local self-intersection)")
    # v2.1: every check's groove runs unbroken, row to row; forks part only
    # at their recorded, bounded, continuous Y-junctions.
    joins, junction_records = check_joins(B, m)
    metrics["check_joins"] = joins
    metrics["junctions"] = junction_records
    broken = [j for j in joins if j["steps"]]
    if broken:
        failures.append("checks " + ", ".join(f"{j['check']} ({j['steps']}/{j['row_pairs']})" for j in broken)
                        + " step: consecutive rows don't join their V-bottoms")
    for r in junction_records:
        if not r["continuous"]:
            failures.append(f"the Y-junction of fork {r['fork']} and check {r['parent']} at z {r['z']} breaks the groove")
        if r["window_length_m"] > JUNCTION_MAX_LENGTH or len(r["exempt_pairs"]) > JUNCTION_MAX_PAIRS:
            failures.append(f"the Y-junction of fork {r['fork']} and check {r['parent']} at z {r['z']} spans "
                            f"{r['window_length_m'] * 1e3:.1f} mm and {len(r['exempt_pairs'])} row pairs "
                            f"(limits {JUNCTION_MAX_LENGTH * 1e3:.0f} mm, {JUNCTION_MAX_PAIRS})")
    # v2.1: between vertices the materials' rings stay where the log's are.
    ring = ring_error(B, m)
    metrics["ring_error_rings"] = ring
    for name, (p99_max, max_max) in (("close", RING_ERROR_CLOSE), ("far", RING_ERROR_FAR)):
        if name in ring and (ring[name]["p99"] > p99_max or ring[name]["max"] > max_max):
            failures.append(f"the materials' rings sit up to {ring[name]['max']:.3f} rings (p99 {ring[name]['p99']:.3f}) "
                            f"from the log's between vertices ({name}; limits p99 {p99_max}, max {max_max})")
    # Features.
    if not m.fallback:
        metrics.update(_feature_metrics(B, m, failures))
    metrics["triangles"] = int(tris.shape[0])
    metrics["vertices"] = int(P.shape[0])
    return {"ok": not failures, "failures": failures, "metrics": metrics}


def _feature_metrics(B, m, failures):
    out = {}
    S = B["samples"]
    # Checks: the count across each check is constant; the depth at the centre is the model's.
    topo = []
    for i, c in enumerate(checks_v2(m)):
        if m.finish[c.face] == "hidden" or c.parent >= 0:
            continue
        counts, depth_err = [], []
        for st, ct in zip(S.row_start, S.row_count):
            z = S.z[st]
            if not (c.z0 <= z <= c.z1):
                continue
            seg = S.seg[st:st + ct]
            u = S.u[st:st + ct][seg == 2 * c.face]
            uc, hl, hr, dz = c.at(z)
            hl, hr = max(float(hl), m.hw_floor), max(float(hr), m.hw_floor)
            counts.append(int(np.sum((u > uc - hl * 1.6 - CHECK_BEYOND[-1] - 0.0001) &
                                     (u < uc + hr * 1.6 + CHECK_BEYOND[-1] + 0.0001))))
            k = st + np.nonzero(seg == 2 * c.face)[0][np.argmin(np.abs(u - uc))]
            depth_err.append(abs(B["check_depth"][k] - float(dz)))
        if len(counts) < 2:
            continue
        cc = np.array(counts)
        topo.append({"check": i, "count_min": int(cc.min()), "count_max": int(cc.max()),
                     "row_to_row_changes": int(np.sum(np.diff(cc) != 0)), "depth_error_max_m": round(float(max(depth_err)), 6)})
    out["checks"] = topo
    # Dents: the deepest displacement near each centre approaches its depth.
    dents = []
    for df, du, dz, a_u, a_z, dep, rim in dent_sites(m):
        near = (S.seg == 2 * df) & (np.abs(S.z - dz) < a_z) & (np.abs(S.u - du) < a_u)
        if near.any():
            dents.append(float(-B["dent_disp"][near].min() / dep))
    out["dent_depth_reached"] = [round(v, 3) for v in dents]
    if dents and min(dents) < 0.6:
        failures.append(f"a dent reaches only {min(dents):.2f} of its depth (under-sampled)")
    # Raised grain: its relief, and that the materials' ring phase rebuilt from
    # the stored UVs (UVLogQ, UV0 = (s, z), UVLogZ seed) is exactly the phase
    # the ridges were cut from, so each ridge sits on its shaded latewood.
    g = B["grain_sel"]
    if g.any():
        h = -B["grain_disp"][g]
        out["grain_vertices"] = int(g.sum())
        out["grain_recess_p50_m"] = round(float(np.percentile(h, 50)), 7)
        out["grain_recess_p95_m"] = round(float(np.percentile(h, 95)), 7)
        rebuilt = ring_phase(B["uv2"][g], float(B["uv3"][0, 1]), np.stack([B["s"][g], B["z"][g]], 1),
                             m.log.ring_width, shared_arrays())
        err = float(np.max(np.abs(rebuilt - B["grain_phase"][g])))
        out["grain_phase_from_stored_uvs_max_error"] = err
        if err > 1e-6:
            failures.append(f"the stored UVs give a ring phase {err:.2e} away from the ridges' (not aligned)")
        fade_ok = h <= max(mx for _lo, mx in m.grain.values()) * (1 + 1e-9)
        if not fade_ok.all():
            failures.append("a grain recess exceeds its specified amplitude")
    if (B["adze_depth"] > 0).any():
        d = B["adze_depth"][B["adze_depth"] > 0]
        out["adze_depth_p50_m"] = round(float(np.percentile(d, 50)), 6)
        out["adze_depth_p95_m"] = round(float(np.percentile(d, 95)), 6)
    return out


def relief_visibility(B, m, face=3, grazing=30.0):
    """Tilt of the side triangles on ``face`` by class, and the shading change at
    the p95 tilt under raking light at ``grazing`` degrees."""
    P, S, t = B["verts"], B["samples"], B["tris"]
    on = (S.seg == 2 * face) & (S.detail > 0)
    sel = on[t].all(1)
    tt = t[sel]
    n = np.cross(P[tt[:, 1]] - P[tt[:, 0]], P[tt[:, 2]] - P[tt[:, 0]])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-30
    fn = np.array([T.FACE_N[face][0], T.FACE_N[face][1], 0.0])
    tilt = np.degrees(np.arccos(np.clip(np.abs(n @ fn), 0, 1)))
    cls = np.where((B["check_depth"][tt].max(1) > 0) | B["check_zone"][tt].any(1), "check",
                   np.where(B["knot_mask"][tt].max(1) > 0.01, "knot",
                            np.where(np.abs(B["dent_disp"][tt]).max(1) > 2e-6, "dent",
                                     np.where(B["grain_sel"][tt].all(1), "grain",
                                              np.where(B["adze_depth"][tt].max(1) > 0, "adze", "plain")))))
    out = {}
    for name in ("plain", "grain", "adze", "dent", "knot", "check"):
        a = tilt[cls == name]
        if a.size:
            p95 = float(np.percentile(a, 95))
            out[name] = {"triangles": int(a.size), "tilt_p50_deg": round(float(np.percentile(a, 50)), 3),
                         "tilt_p95_deg": round(p95, 3),
                         f"shading_p95_at_{int(grazing)}deg_pct": round(100 * math.radians(p95) / math.tan(math.radians(grazing)), 1)}
    return out
