"""CatBaseV6: photoreal domestic-cat head and upper body over a real CT skull.

Shared base for Nyaakoto (grey tabby, white muzzle/chest, blue eyes), NPC cats
and the re-skinned alien banker cats. Unlike V2-V5 (primitive-derived shells)
the skin here is a signed-distance surface wrapped over the actual
University of Edinburgh R(D)SVS domestic-cat CT skull (CC BY 4.0, raw scan kept
private in Local/ThirdPartyRaw per decision D6), with soft-tissue volumes
(temporalis, masseter, jowls, whisker pads, chin, nasal planum, throat, neck)
placed on the skull's measured landmarks, eyelid shells over a layered eye and
a carved palpebral fissure, and pinnae fused into the head with a fillet.

Round 2 adds: a parametric pinna mesh (Henry's pocket, conchal ridges,
antitragus/tragus, seated into the head by SDF projection) joined to the cage
as its own mesh islands; an almond, tilted, 17 % smaller aperture over a globe
sunk 2 mm under a prouder upper lid, with the cornea cap carved out of the lid
cavity; a displaced concave iris with a black vesica slit; a buried sagittal
crest, rounded nape, stop and nasal bridge, mystacial lobes, throat and a
sculpted bust; surface-snapped mackerel markings baked by direct per-texel
field evaluation; and a groom with laid-down, gravity-bent, waved guides,
normal-following children, per-strand length jitter, fine clumps and a
shrink-wrap pass that keeps strands off the skin.

Round 3 (judged round-2 defects, score 3.5/10) re-proportions the skull and
face: pinched temples over a zygomatic flare, a muzzle carried 10 mm forward
with a raised shield-shaped nose leather whose comma nares are carved into
it, flattened whisker pads, a chin point, half the throat fill, a 10 %
shorter occiput with a nape dip, and a neck ~70 % of the skull width. It
widens and moves the eyes medially (40.5 x 31 mm aperture, ~1.2 eye widths
between the medial canthi), seats them behind an unblurred brow shelf, and
adds a swept lid-margin mesh, a vesica pupil and a deeper, more saturated
iris. The pinnae sit 15 mm higher and more medial as broad rounded
triangles with a rolled rim and clumped furnishing tufts. The QuadriFlow
halves are welded on the midline (round 2 shipped two unwelded islands,
which printed a crest and a fur part). The groom gets two clump levels, a
longer cheek/jowl/neck ruff, ~3 % stray guard hairs, darker roots, a ~0.6
white albedo and a view-independent cull of strands over the eye opening;
the whiskers aim forward and out in the world frame. The forehead carries a
real tabby M, the white boundaries are irregular, and three review lights
are added (ThreePoint, a Poly Haven exterior HDRI and a reference-matched
A/B frame).

Round 4 (judged round-3 defects, score 3/10) keeps the round-3 hair system
and midline weld and rebuilds what dominates at combat distance: a front
outline with no temple waist (temple/cheek skin half-width 0.86, maximum on
the zygomatic arch, jowls tapering into a ~20 % thicker neck), one convex
brow-crown-occiput-nape arc with the neck leaning forward from the
shoulders, a diagonal throat fill, raised shoulders, and a deep conchal
cone pinna (~200 deg bend at the base, twisted so the medial base runs
forward, furred back and rims, a hair fringe on both margins, white
furnishings fanning from the medial margin, antitragus and conchal floor,
pale translucent inner skin). The throat V and midline seams are removed
(one down-and-back body flow that cannot degenerate on the jaw underside,
no sternal parting, the head/body lift blended instead of switched at
z = -80). Eyes: a recessed globe, a lemon aperture with a pointed lower
medial canthus, a 2 mm wet pigmented lid margin straight into fur, a greyer
multi-scale iris and a slit-following pupillary ruff. Nose: an inverted-
triangle leather with alar folds and narrow lateral nares, finer pebbling
and a moist tip. Whisker pads bulge ~3 mm with five rows of follicle spots;
12 whiskers per side fan over the whole pad. Coat: a tabby M with a central
bar, a per-strand binary stripe/white choice, slate-root/pale-band/dark-tip
banding and an artistic fibre IOR of 1.2 that restores stripe contrast.

Run from the repository root (Blender 5.2.2 LTS, background):

  blender -b --factory-startup --python scripts/art/create_cat_base_v6.py -- \
      --stages skin,build,render,manifest --round 4 [--samples 256] \
      --lights Overcast,Studio,ThreePoint,Exterior,RefMatch

Stages are cached in the gitignored Local/CatBaseV6Cache/ so later stages can
be re-run alone. The committed outputs are written to
Content/SourceArt/Characters/CatBaseV6/. The raw CT never enters the .blend.

Frames: meters, +X is face-forward, +Z up (project convention), character
scale is 2.2x a real adult domestic cat.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path

import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Characters/CatBaseV6"
CACHE = ROOT / "Local/CatBaseV6Cache"
CT_UID = "7c99ca836d834c39872ecf5e9b5e2087"
CT_PATH = ROOT / f"Local/ThirdPartyRaw/scans/objaverse/{CT_UID}.glb"
CT_SHA256 = "ba3b7ae1548c279b"  # prefix; full hash recorded in sources_manifest.json
HDRI = ROOT / "Content/SourceArt/Environment/PolyHaven/kloofendal_overcast_puresky/kloofendal_overcast_puresky_4k.hdr"
# round 3 (CC0 Poly Haven, fetched privately by fetch_cat_base_v6_sources.py hdris)
HDRI_EXTERIOR = ROOT / "Local/ThirdPartyRaw/hdri/polyhaven/misty_pines_4k.hdr"
HDRI_REFMATCH = ROOT / "Local/ThirdPartyRaw/hdri/polyhaven/overcast_soil_4k.hdr"
HAIR_ASSETS = Path(bpy.utils.resource_path("LOCAL")) / "datafiles/assets/nodes/procedural_hair_node_assets.blend"

REAL_SKULL_LENGTH_M = 0.088  # greatest length, adult domestic cat
CHAR_SCALE = 2.2  # biped character relative to a real cat
HEAD_ORIGIN = Vector((0.0, 0.0, 1.52))  # skull-local origin in world space
MM = 0.001

RNG_SEED = 60623


def log(*a):
    print("[catv6]", *a, flush=True)


# ---------------------------------------------------------------------------
# Skull
# ---------------------------------------------------------------------------

def load_ct_skull():
    """Return (V, F) of the CT skull in skull-local meters (character scale).

    Axes: ct -Y (rostral) -> +X, ct +Z -> +Z. The origin is 0.40 CT units behind
    the rostral tip, which lands near the temporomandibular joint. The
    midsagittal plane is recovered by mirror-ICP (reflect, align, extract the
    -1 eigenvector) so the head is exactly left/right symmetric in +/-Y.
    """
    cache = CACHE / "ct_skull_local.npz"
    if cache.exists():
        d = np.load(cache)
        return d["V"].astype(np.float64), d["F"], d["meta"]
    if not CT_PATH.exists():
        raise SystemExit(f"missing private CT scan {CT_PATH}; run scripts/art/fetch_cat_base_v6_sources.py scans")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(CT_PATH))
    Vs, Fs, off = [], [], 0
    for o in list(bpy.context.scene.objects):
        if o.type != "MESH":
            continue
        me = o.data
        n = len(me.vertices)
        co = np.empty(n * 3, np.float32)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        M = np.array(o.matrix_world)
        Vs.append(co @ M[:3, :3].T + M[:3, 3])
        me.calc_loop_triangles()
        t = np.empty(len(me.loop_triangles) * 3, np.int32)
        me.loop_triangles.foreach_get("vertices", t)
        Fs.append(t.reshape(-1, 3) + off)
        off += n
    V = np.concatenate(Vs).astype(np.float64)
    F = np.concatenate(Fs)
    key = np.round(V / 1e-5).astype(np.int64)
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    V = V[first]
    F = inv.reshape(-1)[F]
    # ct -> character axes
    P = np.stack([-V[:, 1], V[:, 0], V[:, 2]], 1)
    tip = P[:, 0].max()
    c = np.array([tip - 0.40, (P[:, 1].min() + P[:, 1].max()) / 2, (P[:, 2].min() + P[:, 2].max()) / 2])
    # 0.587 CT units = skull greatest length measured on the aligned render
    k = REAL_SKULL_LENGTH_M / 0.587 * CHAR_SCALE
    P = (P - c) * k
    n, off_plane = fit_symmetry_plane(P)
    y = np.array([0.0, 1.0, 0.0])
    ax = np.cross(n, y)
    sa = np.linalg.norm(ax)
    if sa > 1e-9:
        ax /= sa
        K = np.array([[0, -ax[2], ax[1]], [ax[2], 0, -ax[0]], [-ax[1], ax[0], 0]])
        R = np.eye(3) + sa * K + (1 - n @ y) * K @ K
        P = P @ R.T
    P[:, 1] -= (P[:, 1].max() + P[:, 1].min()) / 2
    meta = np.array([k, *n, off_plane])
    CACHE.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(cache, V=P.astype(np.float32), F=F.astype(np.int32), meta=meta)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    return P, F, meta


def fit_symmetry_plane(P):
    rng = np.random.default_rng(RNG_SEED)
    S = P[rng.choice(len(P), 30000, replace=False)]
    kd = KDTree(len(S))
    for i, p in enumerate(S):
        kd.insert(p, i)
    kd.balance()
    Mr = np.diag([1.0, -1.0, 1.0])
    A = S @ Mr.T
    R = np.eye(3)
    t = np.zeros(3)
    for _ in range(25):
        X = A @ R.T + t
        idx = np.empty(len(X), np.int64)
        dist = np.empty(len(X))
        for i, x in enumerate(X):
            _, j, d = kd.find(x)
            idx[i] = j
            dist[i] = d
        keep = dist < np.percentile(dist, 90)
        a, b = A[keep], S[idx[keep]]
        ca, cb = a.mean(0), b.mean(0)
        U, _, Vt = np.linalg.svd((a - ca).T @ (b - cb))
        D = np.diag([1, 1, np.sign(np.linalg.det(Vt.T @ U.T))])
        R = Vt.T @ D @ U.T
        t = cb - R @ ca
    w, v = np.linalg.eig(R @ Mr)
    n = np.real(v[:, np.argmin(np.real(w))])
    n /= np.linalg.norm(n)
    if n[1] < 0:
        n = -n
    log("symmetry plane normal", n.round(5))
    return n, float(t @ n / 2)


# ---------------------------------------------------------------------------
# SDF helpers (all in meters, skull-local)
# ---------------------------------------------------------------------------

def smin(a, b, k):
    if k <= 0:
        return np.minimum(a, b)
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b + (a - b) * h - k * h * (1.0 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


def rot_matrix(yaw=0.0, pitch=0.0, roll=0.0):
    """Degrees. yaw about Z, pitch about Y (positive tips +X down), roll about X."""
    return np.array(Matrix.Rotation(math.radians(yaw), 3, "Z") @ Matrix.Rotation(math.radians(pitch), 3, "Y") @ Matrix.Rotation(math.radians(roll), 3, "X"))


def sd_ellipsoid(P, c, r, R=None):
    q = P - np.asarray(c)
    if R is not None:
        q = q @ np.asarray(R)  # world->local (R columns are local axes)
    r = np.asarray(r)
    k0 = np.linalg.norm(q / r, axis=-1)
    k1 = np.linalg.norm(q / (r * r), axis=-1)
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)


def sd_capsule(P, a, b, ra, rb):
    """Round cone between points a and b with radii ra, rb."""
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    ba = b - a
    L2 = ba @ ba
    pa = P - a
    h = np.clip((pa @ ba) / L2, 0.0, 1.0)
    d = np.linalg.norm(pa - h[..., None] * ba, axis=-1)
    return d - (ra + (rb - ra) * h)


def sd_sphere(P, c, r):
    return np.linalg.norm(P - np.asarray(c), axis=-1) - r


def mirror_y(fn):
    def both(P):
        Q = P.copy()
        Q[..., 1] = np.abs(Q[..., 1])
        return fn(Q)
    return both


# ---------------------------------------------------------------------------
# Anatomy description (skull-local, millimetres converted to meters)
# ---------------------------------------------------------------------------

def v(*xyz):
    return np.array(xyz, float) * MM


class Anatomy:
    """Soft-tissue landmarks measured on the aligned CT skull render grid.

    Skull landmarks (head frame, mm, character scale): rostral incisor tip
    x=+128 z=-45; nasal bone tip x=+128 z=+5; orbit centre x=+72 y=+/-39 z=+22
    (medial wall y=15, lateral y=62); zygomatic arch max y=+/-82 at x=+15..+35
    z=+15; postorbital processes x=+45 z=+41; external acoustic meatus x=-27
    z=0; temporomandibular joint x=-7 z=-15; occiput x=-80 z=+54; vertex z=+78
    at x=-20; mandible ventral border z=-75, symphysis x=+115 z=-68.

    The head frame is pitched HEAD_PITCH nose-down relative to the world so
    the forehead-to-nose line matches the profile photographs (~49 deg).
    """

    head_pitch = 12.0
    skin = 6.0 * MM  # dermis + subcutis over the (smoothed) bone

    # eye (real globe 21.4 mm -> 47 mm); lids follow the skull, gaze diverges 8 deg.
    # Round 3: the judged round-2 eyes were too small, too far apart and too
    # narrow (inner-canthus gap 1.85 eye widths, aperture ratio 0.6, sad
    # medially-falling upper lid). The aperture is now 41 x 31 mm (ratio
    # 0.76), the eye sits 2 mm more medially and 2.5 mm deeper in the orbit
    # (the brow shelf overhangs the cornea in profile), the gap between the
    # medial canthi is ~1.2 eye widths, and the upper arc is symmetric
    # (neutral resting expression) with only a small medial canthus drop.
    eye_r = 23.5 * MM
    # round 4: the whole eye is recessed (lid centre 1 mm back, globe a further
    # 0.8 mm behind the lids) so it no longer sits proud of the face and the
    # upper lid throws a contact shadow onto the iris
    lid_c = v(75.5, 37.5, 21.0)  # lid-shell centre (round 2: 79, 40, 21; round 3: 76.5)
    eye_sink = 2.0 * MM  # round 3: 1.2
    eye_yaw = 8.0
    eye_pitch = -10.0  # head frame; the head is pitched 12 deg down, so the gaze is ~level
    lid_gap = 0.6 * MM
    lid_t = 1.0 * MM
    lid_upper_extra = 1.1 * MM
    # round 4: a lemon-shaped aperture (pointed canthi, a pointed lower medial
    # canthus drawn toward the nose) instead of round 3's rounded ellipse
    fissure_w = 40.0 * MM  # canthus to canthus (round 1: 38, round 2: 32, round 3: 40.5)
    fissure_up = 14.0 * MM  # upper-lid arc height above the canthal line
    fissure_lo = 12.8 * MM  # lower-lid arc depth below it (aperture height/width ~0.67)
    fissure_tilt = 8.0  # deg, lateral canthus higher than medial

    # pinna (separate parametric mesh, see ear_arrays). Round 4 rebuilds it as
    # a deep conchal cone: the cross-section bends ~190 deg at the base (round
    # 3: 84 deg, which made a flat folded card), the visible base chord equals
    # the height, the opening faces 34 deg outward of forward, and the base is
    # 7 mm more lateral so the lateral margin runs on into the temple outline.
    ear_base = v(-9.0, 47.0, 69.0)
    ear_h = 68.0 * MM
    ear_chord = 76.0 * MM  # visible base chord (straight margin to margin)
    ear_tip_r = 5.5 * MM
    ear_t0 = 2.6 * MM  # cartilage + skin thickness at the base
    ear_t1 = 1.3 * MM  # at the tip
    ear_lean_out = 17.0
    ear_lean_back = 11.0
    ear_open_out = 38.0
    ear_twist = 18.0  # extra outward turn of the opening at the base (the medial base runs forward on the skull)

    # muzzle advance (round 3: 10 mm; round 4: 13 mm): the whole nasal
    # bridge, nose leather, whisker pads, upper lip and chin come forward so
    # the profile has a real muzzle
    mz = 13.0


A = Anatomy


def head_R():
    """Head frame -> world-local rotation."""
    return rot_matrix(pitch=A.head_pitch)


def gaze_frame(side=1.0):
    return rot_matrix(yaw=A.eye_yaw * side, pitch=A.eye_pitch)


def lid_center(side=1.0):
    c = A.lid_c.copy()
    c[1] *= side
    return c


def eye_center(side=1.0):
    """Globe centre: the lid centre moved eye_sink back along the gaze axis."""
    return lid_center(side) - gaze_frame(side)[:, 0] * A.eye_sink


def fissure_curves(uu):
    """Upper and lower lid arcs (m) of the almond aperture as functions of the
    canthal-line coordinate uu (m, + = lateral). The upper arc peaks medially,
    the lower arc laterally, and both close to sharp canthi."""
    hw = 0.5 * A.fissure_w
    t = np.clip(uu / hw, -1.0, 1.0)
    base = np.clip(1.0 - t * t, 0.0, 1.0)
    # round 4: a lemon (not an ellipse). base**1 keeps a finite slope at both
    # canthi, so they close to points; the (1 + k*base) factor keeps the
    # middle of each arc full. Round 3's base**0.66 gave vertical tangents at
    # the canthi, i.e. a rounded, goggle-like ellipse.
    up = A.fissure_up * base * (1.0 + 0.30 * base) / 1.30 * (1.0 + 0.05 * t)
    lo = -A.fissure_lo * base * (1.0 + 0.20 * base) / 1.20 * (1.0 + 0.10 * t)
    # medial canthus drawn down and forward toward the nose (the pointed
    # lower medial canthus that the lacrimal line runs out of)
    drop = 2.6 * MM * np.clip(-t, 0.0, 1.0) ** 2.2
    return up - drop, lo - drop


def fissure_uw(q, side):
    """Gaze-frame point -> rotated canthal coordinates (uu along the canthal
    line, + lateral; ww perpendicular, + up)."""
    u = q[..., 1] * side
    w = q[..., 2]
    t = math.radians(A.fissure_tilt)
    uu = u * math.cos(t) + w * math.sin(t)
    ww = -u * math.sin(t) + w * math.cos(t)
    return uu, ww


def sd_fissure(P, side=1.0):
    """Palpebral fissure prism (head frame): the almond outline in the plane
    normal to the eye axis, extruded forward of the globe centre. Distances are
    normalised by the local arc slope so the smooth subtraction stays even."""
    q = (P - eye_center(side)) @ gaze_frame(side)
    uu, ww = fissure_uw(q, side)
    up, lo = fissure_curves(uu)
    e = 0.2 * MM
    up2, lo2 = fissure_curves(uu + e)
    su = np.clip((up2 - up) / e, -6, 6)
    sl = np.clip((lo2 - lo) / e, -6, 6)
    d_up = (ww - up) / np.sqrt(1 + su * su)
    d_lo = (lo - ww) / np.sqrt(1 + sl * sl)
    d_side = np.abs(uu) - 0.5 * A.fissure_w
    d2 = np.maximum(np.maximum(d_up, d_lo), d_side)
    front = 2.0 * MM - q[..., 0]
    return np.maximum(d2, front)


def sd_lid_shell(P, side=1.0):
    """Lid shell around the lid centre; the upper lid is thicker so its margin
    overhangs the (sunk) cornea by ~1.3 mm and throws a shadow line."""
    q = (P - lid_center(side)) @ gaze_frame(side)
    r = np.linalg.norm(q, axis=-1)
    up = smoothstep(-4.0 * MM, 7.0 * MM, q[..., 2]) * smoothstep(-2.0 * MM, 10.0 * MM, q[..., 0])
    return r - (A.eye_r + A.lid_gap + A.lid_t + A.lid_upper_extra * up)


def ear_frame(side=1.0):
    """Pinna frame (head frame columns: opening normal, lateral*side, up).
    Round 3: the ear axis leans 16 deg outward and 10 deg back; the opening
    faces 22 deg outward of forward (orthogonalised against the axis)."""
    u = np.array([-math.tan(math.radians(A.ear_lean_back)), side * math.tan(math.radians(A.ear_lean_out)), 1.0])
    u /= np.linalg.norm(u)
    n = np.array([math.cos(math.radians(A.ear_open_out)), side * math.sin(math.radians(A.ear_open_out)), -0.05])
    n = n - (n @ u) * u
    n /= np.linalg.norm(n)
    return np.stack([n, np.cross(u, n), u], 1)


def cornea_dims():
    """Layered-eye dimensions (m) along the gaze axis from the globe centre."""
    r_i = 0.765 * A.eye_r
    d_i = math.sqrt(A.eye_r ** 2 - r_i ** 2) - 0.8 * MM
    Rc = 0.85 * A.eye_r
    rl = r_i + 0.4 * MM
    h = Rc - math.sqrt(Rc ** 2 - rl ** 2)
    return dict(r_i=r_i, d_i=d_i, Rc=Rc, rl=rl, h=h, apex=d_i + 0.3 * MM + h)


def _bump(t, a, b):
    """Smooth hump that is 1 across [a, b] and falls to 0 over 25 % of the span."""
    w = 0.25 * (b - a)
    return smoothstep(a - w, a + w, t) * (1.0 - smoothstep(b - w, b + w, t))


def head_sdf_sampler():
    """Blurred bulk-flesh SDF (world-local metres) cached by the skin stage."""
    p = CACHE / "bulk_field.npz"
    if not p.exists():
        return None
    d = np.load(p)
    B, org, vs = d["B"], d["origin"], float(d["vs"])
    return lambda P: trilinear(B, org, vs, P)


def seat_ear(Pw, t, sdf, depth=1.8 * MM, t_free=0.30, iters=5):
    """Pull the lower pinna into the head: every vertex below height fraction
    t_free is moved along the SDF gradient until it lies at least `depth`
    inside the bulk flesh at t <= 0, relaxing to no constraint at t_free, so
    the ear grows out of the head like a fillet instead of floating on it."""
    P = Pw.copy()
    lim = np.where(t <= 0.0, -depth, -depth + np.clip(t / t_free, 0, 1) ** 1.5 * 0.035)
    act = t < t_free
    h = 0.8 * MM
    for _ in range(iters):
        Q = P[act]
        d = sdf(Q)
        g = np.stack([(sdf(Q + np.eye(3)[k] * h) - sdf(Q - np.eye(3)[k] * h)) / (2 * h) for k in range(3)], -1)
        g /= np.linalg.norm(g, axis=-1, keepdims=True) + 1e-9
        over = np.maximum(d - lim[act], 0.0)
        P[act] = Q - g * over[:, None]
    return P


def ear_arrays(side=1.0, n_t=96, n_face=44, n_rim=7, sdf=None):
    """Parametric pinna (world-local metres) as a quad grid of closed rings.

    Ear-local axes: X = opening normal (forward, into the scoop), Y = lateral,
    Z = up the ear axis. Each ring (fixed height fraction t) runs across the
    inner (front) surface from the medial to the lateral margin, round the
    lateral rim, back across the outer (back) surface and round the medial
    rim.

    Round 4 (the judged round-3 ear read as bare folded card): the ring is
    now built from the VISIBLE chord (margin to margin), which falls from the
    base chord (76 mm, ~ the 68 mm height) to a rounded 5.5 mm tip with
    slightly convex margins, and from a bend angle that falls from ~205 deg
    at the base (a deep conchal cone whose margins curl forward round the
    cavity) through ~156 deg at mid-height to 70 deg at the tip. The arc
    length is derived from both, so the cone keeps its width however deep it
    is. The lower rings twist up to 18 deg further outward, so the medial
    base runs forward on the skull and the ear reads as a cone in profile.
    The sheet thins from 2.6 to 1.3 mm; Henry's pocket is a smooth lobe with a soft crease on
    the back, low on the lateral margin; the conchal ridges are broad and low
    (round 3's narrow ridges printed facets). The rolled rims are tagged as
    back surface (ear_face = -1), so the back coat wraps round both margins
    and no bare skin edge silhouettes.
    Returns (P, quads, tris, attrs) with per-vertex attributes is_ear, ear_t,
    ear_u (-1 medial .. +1 lateral margin) and ear_face (+1 inner, -1 back
    and rims)."""
    H = A.ear_h / MM
    C0 = A.ear_chord / MM
    tip = A.ear_tip_r / MM
    t_lo = -24.0 / H
    ts = np.concatenate([np.linspace(t_lo, 0.0, 14, endpoint=False), np.linspace(0.0, 1.0, n_t)])
    # arc parameter across the face: denser near the margins
    uf = np.sin(np.linspace(-0.5 * math.pi, 0.5 * math.pi, n_face))
    rings, attrs = [], []
    tcap = 1.0 - 1.6 * tip / H
    for t in ts:
        tc = float(np.clip(t, 0.0, 1.0))
        # visible chord: slightly convex margins, rounded tip
        ch = 2.0 * tip + (C0 - 2.0 * tip) * (1.0 - tc) ** 0.78
        if tc > tcap:
            ch = ch * math.sqrt(max(1.0 - ((tc - tcap) / (1.0 - tcap)) ** 2, 0.0)) + 0.3
        # a near half-cone for the lower half (so the ear reads as a broad
        # cone in profile, not a blade), flattening toward the tip
        bend = 70.0 + 135.0 * (1.0 - tc) ** 0.65
        if t < 0:
            # the buried funnel closes toward the canal
            f = min(-t / abs(t_lo), 1.0)
            ch *= 1.0 - 0.45 * f
            bend += 55.0 * f
        phi = math.radians(bend)
        S = ch * phi / (2.0 * math.sin(0.5 * phi))  # arc length for this chord
        kap = phi / S
        # Henry's pocket: a smooth lobe low on the lateral margin
        hp = float(_bump(np.array(tc), 0.05, 0.20))
        w_med = 0.48 * S
        w_lat = 0.52 * S + 2.6 * hp
        T = (A.ear_t0 + (A.ear_t1 - A.ear_t0) * tc) / MM
        if tc > tcap:
            T *= max(0.5, math.sqrt(max(1.0 - ((tc - tcap) / (1.0 - tcap)) ** 2, 0.0)))
        z = t * H
        xlean = -8.0 * tc ** 2 - 10.0 * min(t, 0.0) / t_lo
        ymed = -10.0 * min(t, 0.0) / t_lo  # buried part dives medially toward the canal

        def arc(sarc):
            a = kap * sarc
            y = np.sin(a) / kap
            x = (1.0 - np.cos(a)) / kap
            nin = np.stack([np.cos(a), -np.sin(a)], -1)  # toward the scoop
            tan = np.stack([np.sin(a), np.cos(a)], -1)
            return np.stack([x, y], -1), nin, tan

        s_front = np.where(uf < 0, uf * w_med, uf * w_lat)
        p, nin, tan = arc(s_front)
        # inner relief: two broad, low conchal ridges, antitragus and tragus
        ridge = np.zeros_like(uf)
        for tk in (0.07, 0.17):
            ridge += 0.55 * math.exp(-((tc - tk) / 0.035) ** 2) * (1.0 - smoothstep(0.30, 0.65, np.abs(uf + 0.05)))
        ridge += 1.8 * math.exp(-((t - 0.03) / 0.06) ** 2) * np.exp(-((uf - 0.74) / 0.16) ** 2)  # antitragus
        ridge += 1.3 * math.exp(-((t + 0.02) / 0.06) ** 2) * np.exp(-((uf + 0.80) / 0.14) ** 2)  # tragus
        front = p + nin * (0.5 * T + ridge)[:, None]
        # outer surface: Henry's pocket crease just inside the lateral margin
        crease = 0.5 * hp * np.exp(-((uf - 0.84) / 0.07) ** 2)
        back = p - nin * (0.5 * T - crease)[:, None]
        # rims: a rolled helix on both margins, its centre shifted slightly
        # toward the scoop so the rim curls over the inner face
        rim_pts, rim_u = [], []
        for end in (+1, -1):
            pe, ne, te = arc(np.array([w_lat if end > 0 else -w_med]))
            pe, ne, te = pe[0], ne[0], te[0] * end
            roll = (0.34 if end < 0 else 0.26) * (1.0 - 0.6 * tc)
            rr = 0.5 * T + roll
            pe = pe + ne * 0.6 * roll
            ang = np.linspace(0.0, math.pi, n_rim + 2)[1:-1]
            if end < 0:
                ang = ang[::-1]
            pts = pe[None, :] + (np.cos(ang)[:, None] * ne[None, :] + np.sin(ang)[:, None] * te[None, :]) * rr
            if end < 0:
                pts = pts[::-1]
            rim_pts.append(pts)
            rim_u.append(np.full(n_rim, float(end)))
        ring2 = np.concatenate([front, rim_pts[0], back[::-1], rim_pts[1][::-1]])
        u_ring = np.concatenate([uf, rim_u[0], uf[::-1], rim_u[1]])
        # round 4: the rims count as back surface (fur, coat colour)
        f_ring = np.concatenate([np.ones(n_face), -np.ones(n_rim), -np.ones(n_face), -np.ones(n_rim)])
        x = ring2[:, 0] + xlean
        y = ring2[:, 1] - ymed
        # the lateral margin runs a little further down the side of the head
        fade = 1.0 - smoothstep(0.0, 0.30, t)
        zz = np.full_like(x, z) - 0.24 * np.maximum(ring2[:, 1], 0.0) * fade
        # twist: the lower rings turn their opening further outward, so the
        # medial margin's base runs forward along the skull and the pinna
        # reads as a broad cone in profile
        tw = math.radians(A.ear_twist) * (1.0 - tc) ** 1.5
        x, y = x * math.cos(tw) - y * math.sin(tw), x * math.sin(tw) + y * math.cos(tw)
        rings.append(np.stack([x, y, zz], -1))
        attrs.append(np.stack([np.full_like(x, t), u_ring, f_ring], -1))
    R = np.array(rings) * MM  # (n_rings, n_ring_pts, 3) ear-local
    At = np.array(attrs)
    nr, npr, _ = R.shape
    q = R.reshape(-1, 3).copy()
    q[:, 1] *= side
    base = A.ear_base.copy()
    base[1] *= side
    Ph = base + q @ ear_frame(side).T
    Pw = Ph @ head_R().T
    if sdf is not None:
        Pw = seat_ear(Pw, At.reshape(-1, 3)[:, 0], sdf)
    # tip cap: one apex vertex above the centre of the last ring
    apex_w = Pw.reshape(nr, npr, 3)[-1].mean(0) + (np.array([0.0, 0.0, 0.25 * MM]) @ ear_frame(side).T) @ head_R().T
    Pw = np.vstack([Pw, apex_w[None]])
    idx = np.arange(nr * npr).reshape(nr, npr)
    quads = []
    for i in range(nr - 1):
        a, b = idx[i], idx[i + 1]
        quads.append(np.stack([a, np.roll(a, -1), np.roll(b, -1), b], -1))
    quads = np.concatenate(quads)
    apex = nr * npr
    last = idx[-1]
    tris = np.stack([last, np.roll(last, -1), np.full(npr, apex), np.full(npr, apex)], -1)
    A2 = At.reshape(-1, 3)
    A2 = np.vstack([A2, [[1.0, 0.0, -1.0]]])
    attrs = dict(is_ear=np.ones(len(Pw)), ear_t=A2[:, 0], ear_u=A2[:, 1], ear_face=A2[:, 2])
    return Pw, quads, tris, attrs


def ear_mesh(side=1.0, name=None):
    Pw, quads, tris, attrs = ear_arrays(side, sdf=head_sdf_sampler())
    me = bpy.data.meshes.new(name or f"CatBaseV6_Ear{'L' if side > 0 else 'R'}")
    faces = [tuple(q) for q in quads] + [(int(t[0]), int(t[1]), int(t[2])) for t in tris]
    me.from_pydata(Pw.tolist(), [], faces)
    me.update()
    # outward normals: the ring order (front medial->lateral, back lateral->medial)
    # winds differently per side, so orient against the ear's own centreline
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    for k, val in attrs.items():
        a = me.attributes.new(k, "FLOAT", "POINT")
        a.data.foreach_set("value", val.astype(np.float32))
    for p in me.polygons:
        p.use_smooth = True
    return me


def sd_ear_mound(P, side=1.0):
    """Auricular muscle mound where the separate pinna mesh inserts."""
    base = A.ear_base.copy()
    base[1] *= side
    q = (P - base) @ ear_frame(side)
    return sd_ellipsoid(q, (-1.0 * MM, 0.0, -9.0 * MM), (12.0 * MM, 26.0 * MM, 12.0 * MM))


class Op:
    """One SDF operation with a conservative world-space bounding box for tile
    culling. frame='head' ops are evaluated in the pitched head frame.
    Bulk ops are evaluated on the coarse grid and blurred into flesh; detail
    ops are evaluated at full resolution on top of the interpolated bulk."""

    def __init__(self, mode, fn, lo, hi, k, frame="head"):
        self.mode, self.fn, self.k, self.frame = mode, fn, k, frame
        pad = k + 6.0 * MM
        lo = np.asarray(lo, float) - pad
        hi = np.asarray(hi, float) + pad
        if frame == "head":
            corners = np.array([[a, b, c] for a in (lo[0], hi[0]) for b in (lo[1], hi[1]) for c in (lo[2], hi[2])])
            w = corners @ head_R().T
            lo, hi = w.min(0), w.max(0)
        self.lo, self.hi = lo, hi


def ell_op(c, r, R=None, k=10.0, mode="union", frame="head"):
    c = v(*c)
    r = v(*r)
    ext = np.full(3, r.max())
    return Op(mode, lambda P, B=None: sd_ellipsoid(P, c, r, R), c - ext, c + ext, k * MM, frame)


def cap_op(a, b, ra, rb, k=10.0, mode="union", frame="head"):
    a = v(*a)
    b = v(*b)
    rr = max(ra, rb) * MM
    return Op(mode, lambda P, B=None: sd_capsule(P, a, b, ra * MM, rb * MM), np.minimum(a, b) - rr, np.maximum(a, b) + rr, k * MM, frame)


def groove_op(poly2d, axes, extrude_axis, ext_lo, ext_hi, width, depth, k=1.0):
    """Surface-relative crease (head frame): a 2D polyline (mm) in the plane of
    `axes`, extruded along `extrude_axis` (ext_lo..ext_hi mm) but confined to
    `depth` mm beneath the bulk surface, so it can never leave slivers."""
    pts = np.asarray(poly2d, float) * MM
    w = np.broadcast_to(np.asarray(width, float) * MM, (len(pts),)).copy()
    dep = np.broadcast_to(np.asarray(depth, float) * MM, (len(pts),)).copy()
    a0, a1 = axes

    def fn(P, B):
        q = np.stack([P[..., a0], P[..., a1]], -1)
        d = np.full(P.shape[:-1], 1e3)
        dd = np.zeros(P.shape[:-1])
        for i in range(len(pts) - 1):
            p0, p1 = pts[i], pts[i + 1]
            e = p1 - p0
            t = np.clip(((q - p0) @ e) / (e @ e), 0.0, 1.0)
            dist = np.linalg.norm(q - (p0 + t[..., None] * e), axis=-1) - (w[i] + (w[i + 1] - w[i]) * t)
            better = dist < d
            dd = np.where(better, dep[i] + (dep[i + 1] - dep[i]) * t, dd)
            d = np.minimum(d, dist)
        x = P[..., extrude_axis]
        d = np.maximum(d, np.maximum(ext_lo * MM - x, x - ext_hi * MM))
        return np.maximum(d, -B - dd)  # only within `depth` of the bulk surface

    lo = np.zeros(3)
    hi = np.zeros(3)
    lo[a0], hi[a0] = pts[:, 0].min() - w.max(), pts[:, 0].max() + w.max()
    lo[a1], hi[a1] = pts[:, 1].min() - w.max(), pts[:, 1].max() + w.max()
    lo[extrude_axis], hi[extrude_axis] = ext_lo * MM, ext_hi * MM
    return Op("subtract", fn, lo, hi, k * MM)


def build_bulk_ops():
    """Bulk soft tissue (coarse grid, blurred).

    Round 4 (judged round 3: a pinched 'light-bulb' front outline, a flat
    occiput with a helmet-rim crease, a thin snake-like neck, a pouting chin):
    - front outline: the temporalis is wide again (temple / cheek half-width
      ~0.87, between round 2's 0.88 box and round 3's 0.76 bulb) and runs on
      one convex arc from the ear base down to the zygoma; the maximum width
      is on the zygomatic arch below and behind the lateral canthus, and the
      masseter/jowl taper into a thicker neck with no notch under the jaw;
    - profile: a longer cranial dome and an occipital mass give one convex
      arc from brow over the crown and occiput into the nape (no nape dip);
      the frontal bulge is smaller so the forehead slopes gently to a slight
      stop; the chin is smaller and does not pout;
    - neck: ~20 % thicker, with a diagonal throat fill so the chin-to-chest
      line is one convex curve, and the chest and shoulders are raised ~16 mm
      so the head sits lower on the shoulders."""
    ops = []
    mz = A.mz
    for s in (1.0, -1.0):
        # temporalis filling the temporal fossa and climbing over the parietal
        ops.append(ell_op((-6.0, 40.0 * s, 34.0), (64.0, 41.0, 44.0), rot_matrix(pitch=6.0), 24))
        # splenius / cervical muscles behind the ear: carries the head width
        # into the (thicker) neck
        ops.append(ell_op((-48.0, 32.0 * s, -4.0), (34.0, 32.0, 42.0), rot_matrix(pitch=-20.0), 28))
        # masseter (fibres run down/back) and jowl, tapering into the neck
        ops.append(ell_op((26.0, 62.0 * s, -16.0), (38.0, 21.0, 26.0), rot_matrix(pitch=-18.0), 18))
        ops.append(ell_op((4.0, 61.0 * s, -34.0), (32.0, 17.0, 26.0), None, 22))
        # zygomatic arch and cheek: the widest part of the face, just below
        # and behind the lateral canthus
        ops.append(cap_op((66.0, 60.0 * s, 2.0), (22.0, 80.0 * s, 8.0), 8.5, 9.5, 16))
        ops.append(ell_op((40.0, 70.0 * s, 2.0), (28.0, 18.0, 19.0), None, 20))
        # supraorbital brow: a soft base only (round 4 removes the crisp
        # overhanging shelf, which hid the eye in profile)
        ops.append(ell_op((80.0, 37.0 * s, 41.0), (18.0, 23.0, 6.5), rot_matrix(roll=12.0 * s, pitch=-8.0), 14))
        # periocular fill so the lids flow into brow and cheek (no goggle ring)
        g = gaze_frame(s)
        c = lid_center(s) - g[:, 0] * 11.0 * MM - g[:, 1] * s * 3.0 * MM
        ops.append(Op("union", (lambda c_, g_: lambda P, B=None: sd_ellipsoid(P, c_, v(24.5, 37.0, 34.0), g_))(c, g), c - 0.04, c + 0.04, 12 * MM))
        # mystacial (whisker) pad base; the rounded 3-4 mm bulge is a
        # surface-relative detail op (see build_detail_ops)
        ops.append(ell_op((126.0 + mz, 14.0 * s, -25.0), (13.0, 17.0, 14.0), rot_matrix(yaw=-22.0 * s), 11))
        # upper-lip drape toward the commissure
        ops.append(ell_op((106.0 + mz, 28.0 * s, -46.0), (19.0, 13.0, 11.0), None, 12))
        # lower lip: smaller (round 3's read as a pout)
        ops.append(ell_op((103.0 + mz, 10.0 * s, -56.0), (13.0, 7.0, 5.0), rot_matrix(yaw=-25.0 * s), 9))
        # ear-base (auricular) mound where the parametric pinna inserts
        ops.append(Op("union", (lambda s_: lambda P, B=None: sd_ear_mound(P, s_))(s), A.ear_base * np.array([1, s, 1]) - 0.04,
                      A.ear_base * np.array([1, s, 1]) + 0.04, 14 * MM))
        # --- bust (world frame), raised ~16 mm (round 4)
        # trapezius: sloped line from the nape down to the scapular spine
        ops.append(cap_op((-62.0, 22.0 * s, -76.0), (-58.0, 94.0 * s, -150.0), 24.0, 28.0, 34, frame="body"))
        # scapula: flat blade on the dorsolateral thorax
        ops.append(ell_op((-78.0, 62.0 * s, -196.0), (16.0, 38.0, 64.0), rot_matrix(roll=-16.0 * s), 30, frame="body"))
        # deltoid over the shoulder joint
        ops.append(ell_op((-34.0, 110.0 * s, -190.0), (38.0, 28.0, 62.0), rot_matrix(roll=-14.0 * s), 36, frame="body"))
        # upper arm
        ops.append(cap_op((-30.0, 120.0 * s, -212.0), (-14.0, 146.0 * s, -424.0), 34.0, 29.0, 26, frame="body"))
        # pectorals: fibres run from the sternum toward the arm
        ops.append(ell_op((28.0, 48.0 * s, -206.0), (32.0, 50.0, 48.0), rot_matrix(yaw=18.0 * s, roll=-10.0 * s), 32, frame="body"))
    # cranial dome over the braincase: longer, so brow, crown and occiput are
    # one arc (round 3's short dome left a flat crown and a domed forehead)
    ops.append(ell_op((-8.0, 0.0, 36.0), (62.0, 44.0, 46.0), None, 20))
    # occipital mass: rounds the back of the skull over the atlas clip and
    # carries the arc on into the nape (round 3: a flat vertical occiput with
    # a crease where the forward-set neck met it)
    ops.append(ell_op((-56.0, 0.0, 20.0), (34.0, 40.0, 42.0), rot_matrix(pitch=-25.0), 24))
    # frontal bulge over the eyes: smaller, so the forehead slopes gently to a
    # slight stop at eye level
    ops.append(ell_op((74.0, 0.0, 52.0), (24.0, 30.0, 11.0), rot_matrix(pitch=20.0), 16))
    ops.append(ell_op((121.0 + mz, 0.0, 18.0), (24.0, 17.0, 7.0), rot_matrix(pitch=40.0), 12))  # nasal bridge: broad and flat
    ops.append(ell_op((139.0 + mz, 0.0, -8.5), (10.0, 14.0, 10.5), rot_matrix(pitch=15.0), 9))  # nasal planum pad
    ops.append(ell_op((133.0 + mz, 0.0, -22.0), (8.0, 9.0, 9.0), None, 8))  # upper lip under the nose (philtrum fill)
    # chin: small, over the mandibular symphysis, no pout
    ops.append(ell_op((110.0 + mz, 0.0, -65.0), (9.0, 11.0, 7.0), rot_matrix(pitch=-20.0), 9))
    ops.append(ell_op((40.0, 0.0, -74.0), (62.0, 34.0, 17.0), rot_matrix(pitch=-12.0), 18))  # intermandibular
    # round 4: a soft fill under the jaw between chin and throat, so the chin
    # does not overhang the throat (a shadow edge under the chin in front)
    ops.append(ell_op((66.0, 0.0, -80.0), (34.0, 28.0, 13.0), rot_matrix(pitch=-22.0), 16))
    # neck and trunk (world frame). Round 4: ~20 % thicker (round 3's
    # 49-60 mm capsule read as a stick neck) and no longer set forward, so
    # its back continues the occipital arc
    ops.append(cap_op((-32.0, 0.0, -50.0), (-50.0, 0.0, -165.0), 71.0, 76.0, 34, frame="body"))
    # nape: continues the occipital arc down and BACK into the back (the
    # neck leans forward from the shoulders; no vertical wall behind the head)
    ops.append(ell_op((-66.0, 0.0, -62.0), (34.0, 44.0, 48.0), None, 30, frame="body"))
    # throat: a diagonal fill from under the jaw to the chest, so chin, throat
    # and chest are one convex line in profile (no 90 deg jowl shelf)
    ops.append(ell_op((44.0, 0.0, -118.0), (28.0, 42.0, 36.0), rot_matrix(pitch=-30.0), 24, frame="body"))
    ops.append(ell_op((46.0, 0.0, -170.0), (24.0, 32.0, 38.0), None, 26, frame="body"))  # manubrium / sternum
    ops.append(ell_op((-34.0, 0.0, -314.0), (102.0, 122.0, 205.0), None, 44, frame="body"))  # thorax
    return ops


# Nose leather, nostril, philtrum and lip-line layout (head frame, mm). Shared
# by the detail sculpt, the region masks and the vibrissa/follicle layout.
# Round 4 (judged round 3: a rounded-rectangle stamp with thick black comma
# nares that read as a grin or a pig snout): the leather is an inverted-
# triangle shield, wide and gently convex on top, its sides converging to a
# point that runs into the philtrum. The nares are narrow slits that start
# low beside the septum and curve up and out along the lateral walls, with a
# raised alar fold lateral to each. The lip line is only the short inverted
# Y; the side lip line stays hidden under the pad fur.
NOSE_X0 = 128.0 + A.mz  # the leather only exists on the front of the planum
LEATHER_HALF = [(0.0, 3.0), (4.5, 3.1), (8.5, 2.6), (11.2, 1.3), (12.3, -0.8), (12.0, -3.2), (10.6, -5.8),
                (8.6, -8.6), (6.3, -11.2), (4.0, -13.3), (2.1, -14.8), (0.8, -15.5), (0.0, -15.7)]
NOSTRIL_POLY = [(2.6, -12.0), (4.6, -11.2), (6.8, -9.4), (8.6, -7.0), (9.8, -4.4)]
NOSTRIL_W = [0.75, 0.65, 0.55, 0.45, 0.30]
NOSTRIL_D = [3.0, 3.2, 2.8, 2.0, 1.0]
# alar fold: a low ridge on the leather just lateral to each naris slit
ALAR_POLY = [(6.4, -11.8), (8.4, -9.6), (10.0, -7.2), (11.0, -4.6)]
PHILTRUM = [(0.0, -12.5), (0.0, -30.0)]
LIP_FRONT = [(0.0, -30.0), (3.0, -32.0), (6.2, -33.6), (9.0, -34.4)]
LIP_SIDE = [(131.0 + A.mz, -39.0), (120.0 + A.mz, -43.5), (108.0 + A.mz, -47.0), (98.0 + A.mz, -49.0)]
# whisker-pad bulge centres (head frame, mm): a rounded pad standing ~3.5 mm
# proud of the muzzle surface on each side of the philtrum
PAD_C = (0.0, 17.0, -27.0)  # (x unused, |y|, z)
PAD_R = (11.5, 9.5)  # (y, z) gaussian radii
PAD_H = 3.2


def leather_poly():
    """Closed shield outline (y, z mm), mirrored from LEATHER_HALF."""
    h = np.asarray(LEATHER_HALF, float)
    left = h[::-1] * np.array([-1.0, 1.0])
    return np.vstack([h, left[1:-1]])


def sd_poly2d(q, poly):
    """Signed distance (mm, negative inside) to a closed 2D polygon."""
    pts = np.asarray(poly, float)
    n = len(pts)
    d = np.full(q.shape[:-1], 1e9)
    inside = np.zeros(q.shape[:-1], bool)
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        e = b - a
        t = np.clip(((q - a) @ e) / (e @ e), 0.0, 1.0)
        d = np.minimum(d, np.linalg.norm(q - (a + t[..., None] * e), axis=-1))
        c1 = (a[1] > q[..., 1]) != (b[1] > q[..., 1])
        xint = a[0] + (q[..., 1] - a[1]) * e[0] / (e[1] if abs(e[1]) > 1e-12 else 1e-12)
        inside ^= c1 & (q[..., 0] < xint)
    return np.where(inside, -d, d)


def build_detail_ops():
    ops = []
    mz = A.mz
    # nose leather: an inverted-triangle shield ~1.4 mm proud of the planum,
    # with a raised alar fold lateral to each naris (round 4)
    lp = leather_poly()
    alar = [np.asarray([(y * s, z) for y, z in ALAR_POLY]) for s in (1.0, -1.0)]

    def leather(P, B):
        q = np.stack([P[..., 1], P[..., 2]], -1) / MM
        d2 = sd_poly2d(q, lp) * MM
        da = np.minimum(dist_poly2d(q, alar[0]), dist_poly2d(q, alar[1]))
        h = 1.1 + 0.6 * np.exp(-(da / 1.5) ** 2)
        d = np.maximum(d2, B - h * MM)
        return np.maximum(d, NOSE_X0 * MM - P[..., 0])

    ops.append(Op("union", leather, v(NOSE_X0, -14.0, -17.0), v(NOSE_X0 + 40.0, 14.0, 5.0), 0.9 * MM))
    # round 4: the whisker pads bulge ~3.6 mm proud and rounded. The bulge is
    # surface-relative (a gaussian displacement of the blurred bulk), so it
    # cannot leave a seam or a ledge
    for s in (1.0, -1.0):
        def pad(P, B, s_=s):
            y, z, x = P[..., 1] / MM, P[..., 2] / MM, P[..., 0] / MM
            w = np.exp(-((y - PAD_C[1] * s_) / PAD_R[0]) ** 2 - ((z - PAD_C[2]) / PAD_R[1]) ** 2)
            w = w * smoothstep(104.0 + mz, 118.0 + mz, x)
            return B - PAD_H * MM * w

        ylo, yhi = sorted(((PAD_C[1] - 30.0) * s, (PAD_C[1] + 30.0) * s))
        ops.append(Op("union", pad, v(100.0 + mz, ylo, -52.0), v(160.0 + mz, yhi, -2.0), 0.6 * MM))
    # eyes: lid shell around the lid centre, then carve the globe cavity
    # (around the sunk globe) and the almond fissure
    for s in (1.0, -1.0):
        c = lid_center(s)
        r = A.eye_r + A.lid_gap + A.lid_t + A.lid_upper_extra
        ops.append(Op("union", (lambda s_: lambda P, B=None: sd_lid_shell(P, s_))(s), c - r, c + r, 4.0 * MM))
    cd = cornea_dims()
    for s in (1.0, -1.0):
        c = eye_center(s)
        r = A.eye_r + A.lid_gap
        ops.append(Op("subtract", (lambda c_, r_: lambda P, B=None: sd_sphere(P, c_, r_))(c, r), c - r, c + r, 1.0 * MM))
        # the lids rest on the cornea, which bulges ~2.7 mm beyond the globe
        # sphere at the lid margin; carve its cap too so no glass pokes
        # through the lid skin (round 1's "chrome bezel")
        cc = c + gaze_frame(s)[:, 0] * (cd["apex"] - cd["Rc"])
        rc = cd["Rc"] + A.lid_gap
        ops.append(Op("subtract", (lambda c_, r_: lambda P, B=None: sd_sphere(P, c_, r_))(cc, rc), cc - rc, cc + rc, 1.0 * MM))
        ops.append(Op("subtract", (lambda s_: lambda P, B=None: sd_fissure(P, s_))(s), c - 0.04, c + 0.04, 1.2 * MM))
    # nostrils: narrow slits curving up and out along the lateral walls
    for s in (1.0, -1.0):
        poly = [(y * s, z) for y, z in NOSTRIL_POLY]
        ops.append(groove_op(poly, (1, 2), 0, NOSE_X0, NOSE_X0 + 47.0, NOSTRIL_W, NOSTRIL_D, 0.5))
    # septum / philtrum: a narrow groove from the leather's lower point into
    # the furred lip
    ops.append(groove_op(PHILTRUM, (1, 2), 0, 118.0 + mz, 175.0 + mz, [0.45, 0.7], [1.0, 1.6], 0.8))
    # closed-mouth lip line: the short inverted Y only (round 4 drops the
    # side groove back to the commissure, which read as a human mouth line)
    for s in (1.0, -1.0):
        poly = [(y * s, z) for y, z in LIP_FRONT]
        ops.append(groove_op(poly, (1, 2), 0, 100.0 + mz, 175.0 + mz, [0.65, 0.6, 0.5, 0.35], [2.0, 2.2, 1.8, 1.0], 1.0))
    return ops


BULK_OPS = None
DETAIL_OPS = None


def apply_ops(ops, P, f, B=None):
    """Apply ops to flat world-local points P (N,3) and field f (N,)."""
    Ph = P @ head_R()
    plo = P.min(0)
    phi = P.max(0)
    for op in ops:
        if np.any(op.hi < plo) or np.any(op.lo > phi):
            continue
        m = np.all((P >= op.lo) & (P <= op.hi), axis=1)
        if not m.any():
            continue
        idx = np.nonzero(m)[0]
        d = op.fn(Ph[idx] if op.frame == "head" else P[idx], None if B is None else B[idx])
        if op.mode == "union":
            f[idx] = smin(f[idx], d, op.k)
        else:
            f[idx] = smax(f[idx], -d, op.k)
    return f


def bulk_sdf(P, skull_d):
    global BULK_OPS
    if BULK_OPS is None:
        BULK_OPS = build_bulk_ops()
    shp = P.shape[:-1]
    P = P.reshape(-1, 3)
    f = (skull_d.reshape(-1) - A.skin).astype(np.float64)
    f = apply_ops(BULK_OPS, P, f)
    f = smax(f, -(P[:, 2] + 0.600), 12 * MM)  # bust bottom
    return f.reshape(shp)


def detail_sdf(P, Bv):
    global DETAIL_OPS
    if DETAIL_OPS is None:
        DETAIL_OPS = build_detail_ops()
    shp = P.shape[:-1]
    P = P.reshape(-1, 3)
    B = Bv.reshape(-1).astype(np.float64)
    f = apply_ops(DETAIL_OPS, P, B.copy(), B)
    return f.reshape(shp)


def smooth_skull(V, F, iters=40, lam=0.55):
    """Taubin-style Laplacian smoothing of the CT isosurface: removes CT
    staircase/noise so it cannot print through 6 mm of skin, while keeping the
    bony landmarks (orbits, arches, nasal bridge, mandible)."""
    V = V.copy()
    e = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    e = np.concatenate([e, e[:, ::-1]])
    deg = np.bincount(e[:, 0], minlength=len(V)).astype(np.float64)
    deg[deg == 0] = 1
    for it in range(iters):
        for fac in (lam, -0.53):
            acc = np.zeros_like(V)
            np.add.at(acc, e[:, 0], V[e[:, 1]])
            V += fac * (acc / deg[:, None] - V)
    return V


# ---------------------------------------------------------------------------
# Level-set meshing (sparse tiles, OpenVDB bundled with Blender)
# ---------------------------------------------------------------------------

DOMAIN_MIN = np.array([-0.265, -0.275, -0.615])
DOMAIN_MAX = np.array([0.180, 0.275, 0.232])


def skull_levelset(V, F, vs, band_m):
    import openvdb as vdb
    tr = vdb.createLinearTransform(voxelSize=vs)
    hw = band_m / vs
    g = vdb.FloatGrid.createLevelSetFromPolygons(V.astype(np.float32), triangles=F.astype(np.uint32), transform=tr, halfWidth=float(hw))
    return g


def sample_grid_dense(g, origin_ijk, shape):
    arr = np.empty(shape, np.float32)
    g.copyToArray(arr, ijk=tuple(int(x) for x in origin_ijk))
    return arr


def box_blur_axis(a, w, axis):
    r = w // 2
    pad = [(0, 0)] * a.ndim
    pad[axis] = (r + 1, r)
    c = np.cumsum(np.pad(a, pad, mode="edge"), axis=axis, dtype=np.float64)
    n = a.shape[axis]
    hi = np.take(c, np.arange(w, w + n), axis=axis)
    lo = np.take(c, np.arange(0, n), axis=axis)
    return ((hi - lo) / w).astype(np.float32)


def gaussian_blur3(a, w, passes=3):
    for _ in range(passes):
        for ax in range(3):
            a = box_blur_axis(a, w, ax)
    return a


def trilinear(G, origin, vs, P):
    """Sample dense grid G (origin = world of index 0) at points P (...,3)."""
    q = (P - origin) / vs
    i0 = np.floor(q).astype(np.int64)
    t = q - i0
    shp = np.array(G.shape)
    i0 = np.clip(i0, 0, shp - 2)
    t = np.clip(t, 0.0, 1.0)
    out = 0.0
    for dx in (0, 1):
        wx = t[..., 0] if dx else 1 - t[..., 0]
        for dy in (0, 1):
            wy = t[..., 1] if dy else 1 - t[..., 1]
            for dz in (0, 1):
                wz = t[..., 2] if dz else 1 - t[..., 2]
                out = out + wx * wy * wz * G[i0[..., 0] + dx, i0[..., 1] + dy, i0[..., 2] + dz]
    return out


def flood_fill_cavities(occ):
    ext = np.zeros_like(occ)
    ext[0, :, :] = ext[-1, :, :] = True
    ext[:, 0, :] = ext[:, -1, :] = True
    ext[:, :, 0] = ext[:, :, -1] = True
    free = ~occ
    ext &= free
    it = 0
    while True:
        n0 = int(ext.sum())
        for _ in range(8):
            g = ext.copy()
            g[1:] |= ext[:-1]
            g[:-1] |= ext[1:]
            g[:, 1:] |= ext[:, :-1]
            g[:, :-1] |= ext[:, 1:]
            g[:, :, 1:] |= ext[:, :, :-1]
            g[:, :, :-1] |= ext[:, :, 1:]
            ext = g & free
            it += 1
        if int(ext.sum()) == n0:
            break
    return free & ~ext, it


def build_bulk_field(V, F, vs=2.0 * MM, blur_w=5):
    """Coarse bulk-flesh SDF: smoothed CT shell + soft tissue, internal
    cavities closed by exterior flood fill, then Gaussian-blurred (3 box
    passes; sigma ~ 2.45 voxels = 4.9 mm) into continuous flesh."""
    import openvdb as vdb
    t0 = time.time()
    g = skull_levelset(V, F, vs, 40 * MM)
    lo = np.floor(DOMAIN_MIN / vs).astype(int) - 4
    hi = np.ceil(DOMAIN_MAX / vs).astype(int) + 4
    shape = tuple(hi - lo + 1)
    sk = np.abs(sample_grid_dense(g, lo, shape))
    xs = [np.arange(lo[a], hi[a] + 1) * vs for a in range(3)]
    Bf = np.empty(shape, np.float32)
    for a in range(shape[0]):
        J, K = np.meshgrid(xs[1], xs[2], indexing="ij")
        P = np.stack([np.full_like(J, xs[0][a]), J, K], -1)
        Bf[a] = bulk_sdf(P, sk[a])
    cav, it = flood_fill_cavities(Bf < 0)
    Bf = np.where(cav, -np.abs(Bf) - vs, Bf)
    Bb = gaussian_blur3(Bf, blur_w)
    # round 3: where thick muscle covers the bone (occiput, nape, the back and
    # top of the cranium) blend toward a much wider blur (sigma ~8.8 mm), so
    # the condyles, mastoids, atlas-clip edge and the ends of the temporalis
    # and splenius volumes no longer print as lumps and a spike behind the
    # ear; the face keeps the normal blur and its detail
    Bw = gaussian_blur3(Bf, 9)
    I = np.arange(shape[0])[:, None, None] * vs + lo[0] * vs
    K = np.arange(shape[2])[None, None, :] * vs + lo[2] * vs
    Xh = I * math.cos(math.radians(A.head_pitch)) - K * math.sin(math.radians(A.head_pitch))  # head-frame x
    wgt = smoothstep(10.0 * MM, -45.0 * MM, Xh) * np.ones((1, shape[1], 1))
    Bb = (Bb * (1.0 - wgt) + Bw * wgt).astype(np.float32)
    log(f"bulk field {shape} flood iters={it} cavity={int(cav.sum())} ({time.time()-t0:.1f}s)")
    return Bb, lo * vs


def build_skin_mesh(V, F, fine_vs=0.75 * MM, bulk_vs=2.0 * MM):
    import openvdb as vdb
    t0 = time.time()
    Bb, borg = build_bulk_field(V, F, bulk_vs)
    np.savez_compressed(CACHE / "bulk_field.npz", B=Bb, origin=borg, vs=bulk_vs)
    global DETAIL_OPS
    if DETAIL_OPS is None:
        DETAIL_OPS = build_detail_ops()
    union_boxes = [(op.lo, op.hi) for op in DETAIL_OPS if op.mode == "union"]
    bw = 3.0 * fine_vs
    out = vdb.FloatGrid(bw)
    out.transform = vdb.createLinearTransform(voxelSize=fine_vs)
    flo = np.floor(DOMAIN_MIN / fine_vs).astype(int)
    fhi = np.ceil(DOMAIN_MAX / fine_vs).astype(int)
    T = 64
    tiles = 0
    for ti in range(flo[0], fhi[0] + 1, T):
        for tj in range(flo[1], fhi[1] + 1, T):
            for tk in range(flo[2], fhi[2] + 1, T):
                o = np.array([ti, tj, tk])
                tlo = o * fine_vs
                thi = (o + T) * fine_vs
                # sample the bulk field on a 9^3 sub-grid of the tile: the
                # tile is skipped only if every sample has the same sign and
                # lies >10 mm from the surface (round 1 tested the centre
                # alone, which dropped tiles whose corner reached the skin and
                # left box-shaped pits)
                sub = [np.linspace(tlo[a], thi[a], 9) for a in range(3)]
                SG = np.stack(np.meshgrid(*sub, indexing="ij"), -1).reshape(-1, 3)
                bs = trilinear(Bb, borg, bulk_vs, SG)
                near = not (bs.min() > 0.010 or bs.max() < -0.010)
                if not near:
                    near = any(np.all(thi >= lo_) and np.all(tlo <= hi_) for lo_, hi_ in union_boxes)
                if not near:
                    continue
                ax = [np.arange(o[a], o[a] + T) * fine_vs for a in range(3)]
                I, J, K = np.meshgrid(*ax, indexing="ij")
                Pf = np.stack([I, J, K], -1)
                Bv = trilinear(Bb, borg, bulk_vs, Pf)
                f = detail_sdf(Pf, Bv).astype(np.float32)
                # only tiles entirely beyond the narrow band may stay inactive:
                # an inactive tile next to a surface lying within 1 voxel of
                # the tile wall lets signedFloodFill guess its sign wrongly and
                # prints a flat piece of the tile wall into the skin
                if f.min() >= bw:
                    continue
                if f.max() <= -bw:
                    out.copyFromArray(np.full((T, T, T), -bw, np.float32), ijk=tuple(int(x) for x in o))
                    continue
                out.copyFromArray(np.clip(f, -bw, bw), ijk=tuple(int(x) for x in o), tolerance=0.0)
                tiles += 1
    out.gridClass = vdb.GridClass.LEVEL_SET
    out.signedFloodFill()
    log(f"fine tiles={tiles} active={out.activeVoxelCount()} ({time.time()-t0:.1f}s)")
    pts, quads = out.convertToQuads(0.0)
    log(f"mesh quads={len(quads)} verts={len(pts)} ({time.time()-t0:.1f}s)")
    return pts.astype(np.float64), quads.astype(np.int64)


def keep_largest_component(pts, quads):
    n = len(pts)
    parent = np.arange(n)

    def find(a):
        while True:
            p = parent[a]
            gp = parent[p]
            if np.array_equal(p, gp):
                return p
            parent[a] = gp
            a = gp

    e = np.concatenate([quads[:, [0, 1]], quads[:, [1, 2]], quads[:, [2, 3]]])
    for _ in range(200):
        a = find(e[:, 0])
        b = find(e[:, 1])
        if np.array_equal(a, b):
            break
        np.minimum.at(parent, np.maximum(a, b), np.minimum(a, b))
    root = find(np.arange(n))
    labs, cnt = np.unique(root, return_counts=True)
    keep_root = labs[np.argmax(cnt)]
    vk = root == keep_root
    qk = vk[quads[:, 0]]
    remap = -np.ones(n, np.int64)
    remap[vk] = np.arange(vk.sum())
    log(f"components={len(labs)} kept {vk.sum()} of {n} verts")
    return pts[vk], remap[quads[qk]]


def mesh_from_arrays(name, pts, faces):
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(pts))
    me.vertices.foreach_set("co", pts.astype(np.float32).ravel())
    nf = len(faces)
    k = faces.shape[1]
    me.loops.add(nf * k)
    me.loops.foreach_set("vertex_index", faces.astype(np.int32).ravel())
    me.polygons.add(nf)
    me.polygons.foreach_set("loop_start", np.arange(0, nf * k, k, dtype=np.int32))
    me.update(calc_edges=True)
    me.validate()
    return me


def stage_skin(args):
    V, F, meta = load_ct_skull()
    log("skull", V.shape, "scale", meta[0])
    # drop the atlas (C1) fused to the CT: its wings would poke through the
    # nape as nubs. The nape/splenius soft tissue covers this region instead.
    keep = V[F].mean(1)[:, 0] > -0.084
    F = F[keep]
    log("atlas clip kept", int(keep.sum()), "of", len(keep), "faces")
    Vs = smooth_skull(V, F)
    Vw = Vs @ head_R().T
    pts, quads = build_skin_mesh(Vw, F, fine_vs=args.voxel * MM)
    pts, quads = keep_largest_component(pts, quads)
    # dual contouring from OpenVDB winds quads inward; flip to outward normals
    quads = quads[:, ::-1]
    np.savez_compressed(CACHE / "skin_dense.npz", pts=pts.astype(np.float32), quads=quads.astype(np.int32))
    return pts, quads


def preview_dense(args):
    d = np.load(CACHE / "skin_dense.npz")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    me = mesh_from_arrays("dense", d["pts"], d["quads"])
    ob = bpy.data.objects.new("dense", me)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = HEAD_ORIGIN
    for p in me.polygons:
        pass
    me.shade_smooth()
    for side in (1.0, -1.0):
        c = Vector(eye_center(side) @ head_R().T) + HEAD_ORIGIN
        bpy.ops.mesh.primitive_uv_sphere_add(radius=A.eye_r, location=c, segments=48, ring_count=24)
        bpy.ops.object.shade_smooth()
        g = Vector(head_R() @ gaze_frame(side)[:, 0])
        cc = cornea_dims()
        bpy.ops.mesh.primitive_uv_sphere_add(radius=cc["Rc"], location=c + g * (cc["apex"] - cc["Rc"]), segments=48, ring_count=24)
        bpy.ops.object.shade_smooth()
    if getattr(args, "with_ears", True):
        try:
            for side in (1.0, -1.0):
                ob = link(bpy.data.objects.new(f"ear{side}", ear_mesh(side)))
                ob.location = HEAD_ORIGIN
        except NameError:
            pass
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.show_cavity = True
    sc.render.resolution_x = 1400
    sc.render.resolution_y = 1400
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.lens = 85
    tgt = HEAD_ORIGIN + Vector((0.03, 0, 0.0))
    views = (("front", Vector((1, 0, 0)), 1.35), ("profile", Vector((0, -1, 0)), 1.35), ("tq", Vector((0.8, -0.6, 0.05)).normalized(), 1.35),
             ("top", Vector((0.2, 0, 1)).normalized(), 1.35), ("bust", Vector((0.85, -0.5, 0.0)).normalized(), 3.2),
             ("cu_front", Vector((1, 0, 0.05)).normalized(), 0.75), ("cu_tq", Vector((0.75, -0.62, 0.12)).normalized(), 0.75), ("cu_profile", Vector((0.02, -1, 0.02)).normalized(), 0.75))
    for name, d_, dist in views:
        t = tgt if name != "bust" else HEAD_ORIGIN + Vector((0, 0, -0.2))
        if name.startswith("cu_"):
            t = HEAD_ORIGIN + Vector((0.06, 0, 0.0))
        cam.location = t + d_ * dist
        cam.rotation_euler = (t - cam.location).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = str(Path(args.preview_dir) / f"dense_{name}.png")
        bpy.ops.render.render(write_still=True)


# ---------------------------------------------------------------------------
# Procedural noise and coat / region fields
# ---------------------------------------------------------------------------

def _hash3(i, j, k, seed):
    h = np.sin(i * 127.1 + j * 311.7 + k * 74.7 + seed * 19.19) * 43758.5453
    return h - np.floor(h)


def vnoise(P, scale, seed=0.0):
    q = P / scale
    i = np.floor(q)
    f = q - i
    u = f * f * (3.0 - 2.0 * f)
    out = 0.0
    for dx in (0, 1):
        wx = u[..., 0] if dx else 1 - u[..., 0]
        for dy in (0, 1):
            wy = u[..., 1] if dy else 1 - u[..., 1]
            for dz in (0, 1):
                wz = u[..., 2] if dz else 1 - u[..., 2]
                out = out + wx * wy * wz * _hash3(i[..., 0] + dx, i[..., 1] + dy, i[..., 2] + dz, seed)
    return out


def fbm(P, scale, octaves=4, seed=0.0):
    tot = 0.0
    amp = 0.5
    norm = 0.0
    for o in range(octaves):
        tot = tot + amp * vnoise(P, scale / (2 ** o), seed + o * 7.3)
        norm += amp
        amp *= 0.5
    return tot / norm


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def dist_polyline(P, pts):
    pts = np.asarray(pts, float)
    d = np.full(P.shape[:-1], 1e9)
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        e = b - a
        t = np.clip(((P - a) @ e) / (e @ e), 0, 1)
        d = np.minimum(d, np.linalg.norm(P - (a + t[..., None] * e), axis=-1))
    return d


def ear_local(Ph, side):
    base = A.ear_base.copy()
    base[1] *= side
    q = (Ph - base) @ ear_frame(side)
    return q[..., 0], q[..., 1] * side, q[..., 2]


# ---------------------------------------------------------------------------
# Mackerel-tabby markings: polylines (head frame, mm) snapped onto the skin
# ---------------------------------------------------------------------------

# name, control points (x, y, z) on the cat's left side (mirrored with
# per-side jitter), half-widths.
# Round 4 (judged round 3: the forehead read as two parallel vertical lines,
# the contrast had collapsed to a washed-out silver face): a tabby M with
# SHORT outer legs rising from above each eye to the M peaks, inner strokes
# that dip into a clear CENTRAL BAR (the dorsal midline line, which starts
# just above the top of the white blaze and runs over the crown to the nape),
# crown lines at ~20 mm and ~42 mm from the midline, a bold mascara line from
# the lateral canthus across the cheek, two cheek bars, and a thin dark
# lacrimal line running from the medial canthus down beside the nose. Every
# stroke is ~20-30 % wider than round 3.
MARKINGS = [
    ("mascara", [(83, 58, 24), (73, 68, 23), (57, 78, 19), (38, 85, 14), (18, 86, 9), (2, 82, 5)], [1.6, 2.5, 2.9, 2.8, 2.3, 1.3]),
    ("cheek2", [(86, 52, -6), (73, 63, -12), (57, 74, -18), (37, 81, -23), (18, 80, -22), (4, 74, -14)], [0.9, 1.6, 1.9, 1.9, 1.6, 0.9]),
    ("cheek3", [(64, 63, -30), (46, 70, -36), (26, 73, -42), (10, 69, -46)], [1.0, 1.6, 1.6, 0.9]),
    # M: short outer leg from above the middle of the eye up to the peak
    ("m_outer", [(92, 34, 43), (88, 29, 50), (83, 22, 58), (79, 16, 63)], [2.4, 3.0, 3.0, 2.6]),
    # M: inner stroke from the peak down into the central bar
    ("m_inner", [(79, 14, 63), (83, 9, 57), (87, 4.5, 51), (89, 1.5, 47)], [2.4, 2.2, 1.9, 1.6]),
    # central bar (both mirrored copies overlap on the midline, with
    # different jitter, so its edge is irregular)
    ("m_center", [(90, 0, 46), (84, 0, 55), (76, 0, 64), (62, 0, 74), (44, 0, 82), (10, 0, 89), (-24, 0, 88), (-56, 0, 72), (-80, 0, 44), (-94, 0, 12)],
     [2.0, 2.7, 3.1, 3.1, 2.9, 3.0, 3.1, 3.1, 3.0, 2.6]),
    ("crown_a", [(77, 19, 65), (61, 20, 75), (41, 21, 83), (16, 22, 88), (-14, 23, 88), (-46, 25, 77), (-72, 27, 53), (-88, 29, 23), (-96, 30, -5)],
     [2.6, 3.0, 3.3, 3.4, 3.4, 3.4, 3.3, 3.2, 2.9]),
    ("crown_lat", [(72, 48, 52), (57, 45, 63), (40, 42, 73), (21, 40, 79)], [1.7, 2.4, 2.3, 1.4]),
    # lacrimal line: from the medial canthus down and forward beside the nose
    ("lacrimal", [(89, 17.5, 14), (96, 15.0, 7), (103, 13.5, 0), (109, 12.5, -5)], [1.3, 1.2, 1.0, 0.6]),
]
MARK_JITTER_SEED = 4417

_MARK_CACHE = {}


def _newton_to_surface(W, sdf, iters=6):
    h = 0.5 * MM
    for _ in range(iters):
        d = sdf(W)
        g = np.stack([(sdf(W + np.eye(3)[k] * h) - sdf(W - np.eye(3)[k] * h)) / (2 * h) for k in range(3)], -1)
        g2 = np.sum(g * g, -1) + 1e-9
        W = W - g * (d / g2)[:, None]
    return W


def marking_curves():
    """Markings snapped onto the bulk skin (head frame, mm), both sides.
    Each entry is (points (M,3), half-widths (M,)) sampled every ~3 mm."""
    if "curves" in _MARK_CACHE:
        return _MARK_CACHE["curves"]
    sdf = head_sdf_sampler()
    out = []
    for mi, (name, pts, wid) in enumerate(MARKINGS):
        pts0 = np.asarray(pts, float)
        wid0 = np.asarray(wid, float)
        for s in (1.0, -1.0):
            # round 3: each side gets its own jitter (control points +-2.5 mm,
            # widths x0.7-1.3 along the stroke) so the two sides and the
            # stroke spacing are not machine-identical
            rng = np.random.default_rng(MARK_JITTER_SEED + 31 * mi + (0 if s > 0 else 7))
            pts = pts0 + rng.normal(0.0, 1.3, pts0.shape).clip(-2.5, 2.5)
            wid = wid0 * rng.uniform(0.72, 1.28, len(wid0))
            dense, dw = [pts[0]], [wid[0]]
            for i in range(len(pts) - 1):
                n = max(int(np.linalg.norm(pts[i + 1] - pts[i]) / 3.0), 1)
                for k in range(1, n + 1):
                    dense.append(pts[i] + (pts[i + 1] - pts[i]) * k / n)
                    dw.append(wid[i] + (wid[i + 1] - wid[i]) * k / n)
            Q = np.array(dense) * np.array([1.0, s, 1.0])
            if sdf is not None:
                Q = (_newton_to_surface((Q * MM) @ head_R().T, sdf) @ head_R()) / MM
            out.append((Q, np.array(dw)))
    _MARK_CACHE["curves"] = out
    return out


def dist_to_curves(P3, curves, pad=4.0):
    """Min over curves of (distance to the polyline - local half-width), mm."""
    out = np.full(len(P3), 1e3)
    for pts, wid in curves:
        lo = pts.min(0) - wid.max() - pad
        hi = pts.max(0) + wid.max() + pad
        m = np.all((P3 >= lo) & (P3 <= hi), axis=1)
        if not m.any():
            continue
        Q = P3[m]
        best = np.full(len(Q), 1e3)
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            e = b - a
            t = np.clip(((Q - a) @ e) / max(e @ e, 1e-9), 0.0, 1.0)
            d = np.linalg.norm(Q - (a + t[:, None] * e), axis=1) - (wid[i] + (wid[i + 1] - wid[i]) * t)
            best = np.minimum(best, d)
        out[m] = np.minimum(out[m], best)
    return out


def sd_triangle_2d(p, a, b, c):
    """Signed distance to a 2D triangle (Inigo Quilez)."""
    def seg(pa, ba):
        h = np.clip(np.sum(pa * ba, -1) / np.sum(ba * ba), 0.0, 1.0)
        return pa - ba * h[..., None]
    e0, e1, e2 = b - a, c - b, a - c
    v0, v1, v2 = p - a, p - b, p - c
    pq0, pq1, pq2 = seg(v0, e0), seg(v1, e1), seg(v2, e2)
    s = np.sign(e0[0] * e2[1] - e0[1] * e2[0])
    d0 = np.stack([np.sum(pq0 * pq0, -1), s * (v0[..., 0] * e0[1] - v0[..., 1] * e0[0])], -1)
    d1 = np.stack([np.sum(pq1 * pq1, -1), s * (v1[..., 0] * e1[1] - v1[..., 1] * e1[0])], -1)
    d2 = np.stack([np.sum(pq2 * pq2, -1), s * (v2[..., 0] * e2[1] - v2[..., 1] * e2[0])], -1)
    d = np.minimum(np.minimum(d0, d1), d2)
    return -np.sqrt(d[..., 0]) * np.sign(d[..., 1])


def dist_poly2d(q, poly):
    pts = np.asarray(poly, float)
    d = np.full(q.shape[:-1], 1e3)
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        e = b - a
        t = np.clip(((q - a) @ e) / (e @ e), 0.0, 1.0)
        d = np.minimum(d, np.linalg.norm(q - (a + t[..., None] * e), axis=-1))
    return d


def mystacial_roots():
    """Whisker follicle positions on the pads (head frame, mm). Round 4: 12
    per side in 4 rows of 3, spread over the whole pad (round 3's 21 roots
    were bunched near the nose and read as one parallel bundle): columns
    ~5.5 mm apart, rows ~4.6 mm apart, caudal columns slightly lower.
    Returns list of (side, row, col, point)."""
    out = []
    mz = A.mz
    for s in (1.0, -1.0):
        for row in range(4):
            for col in range(3):
                y = 11.5 + 5.6 * col + 1.6 * row
                z = -19.5 - 4.6 * row - 1.4 * col
                x = 128.5 + mz - 0.45 * (y - 10.0) - 1.2 * row
                out.append((s, row, col, np.array([x, y * s, z])))
    return out


def follicle_spots():
    """(y, z) head-frame mm of the dark follicle spots on the white pads, one
    side (mirrored in use): 5 rows of 7 (round 3 drew 3-4 isolated specks per
    side, because its 3D dot centres mostly missed the skin)."""
    pts = []
    for row in range(5):
        for col in range(7):
            pts.append((7.5 + 3.7 * col + 1.1 * row, -18.0 - 3.8 * row - 1.0 * col))
    return np.asarray(pts, float)


def ex_arrays(n, ex):
    z = np.zeros(n)
    if ex is None:
        return z, z, z, z
    return (ex.get("is_ear", z), ex.get("ear_t", z), ex.get("ear_u", z), ex.get("ear_face", z))


def coat_fields(Pw, Nw, ex=None):
    """Nyaakoto coat and anatomical fields at world-local points (HEAD_ORIGIN
    at 0) with normals; `ex` carries the pinna attributes (is_ear, ear_t,
    ear_u, ear_face) where the points lie on the parametric ears.

    Coat: white (muzzle, nose-bridge blaze, chin, throat, bib), stripe
    (mackerel markings with hair-scale edges: forehead M and central bar,
    crown and nape lines, mascara line, cheek bars, lacrimal line, necklaces,
    body bands, follicle spots), pale (spectacles, ear thumbprints). Regions:
    nose leather, black pigment (lid margins, conjunctiva, nostril slits,
    lip line, follicle spots, lacrimal line), inner-ear skin. Groom: length
    (m), density, lift (deg)."""
    Pw = np.asarray(Pw, float)
    Nw = np.asarray(Nw, float)
    n = len(Pw)
    is_ear, ear_t, ear_u, ear_face = ex_arrays(n, ex)
    earm = is_ear > 0.5
    Ph = Pw @ head_R()
    Nh = Nw @ head_R()
    x, y, z = Ph[:, 0] / MM, Ph[:, 1] / MM, Ph[:, 2] / MM
    ay = np.abs(y)
    xw, yw, zw = Pw[:, 0] / MM, Pw[:, 1] / MM, Pw[:, 2] / MM
    P3 = np.stack([x, y, z], -1)
    mz = A.mz
    # hair-scale edge jitter (~1 mm) on top of a broad waviness (~3 mm)
    jit = (fbm(Pw, 0.0011, 2, 11.0) - 0.5) * 1.3 + (fbm(Pw, 0.022, 2, 12.0) - 0.5) * 3.2
    edge = 0.30  # mm: half-width of the stripe/white transition (hair scale)

    # ---- white spotting: muzzle, nose-bridge blaze, chin, throat, bib
    muz = np.sqrt(((x - 124 - mz) / 32) ** 2 + (y / 40) ** 2 + ((z + 36) / 27) ** 2)
    d_white = (muz - 1.0) * 26.0
    # round 4: the blaze is broad between the medial canthi and narrows up
    # the forehead to end just below the M's central bar
    wb = np.clip(13.0 - 0.26 * (z + 5.0), 3.0, 13.0)
    blaze = np.maximum(np.maximum(ay - wb, z - 42.0), 98.0 - x)
    d_white = np.minimum(d_white, blaze)
    chin = (np.sqrt(((x - 104 - mz) / 26) ** 2 + (y / 30) ** 2 + ((z + 68) / 18) ** 2) - 1.0) * 18.0
    d_white = np.minimum(d_white, chin)
    # round 4: the throat white runs on without a gap into the bib (a grey
    # V between the chin and bib whites was part of round 3's throat seam)
    throat = np.maximum(np.maximum(ay - 32.0 - 0.30 * np.clip(-60 - z, 0, 90), z + 58.0), 18.0 - x)
    d_white = np.minimum(d_white, throat)
    wbib = 36.0 + 0.40 * np.clip(-95.0 - zw, 0.0, 400.0) - 0.0011 * np.clip(-95.0 - zw, 0.0, 400.0) ** 2 * 0.6
    bib = np.maximum(np.maximum(ay - wbib, zw + 80.0), -(Nw[:, 0] + 0.30) * 60.0)
    d_white = np.minimum(d_white, bib)
    d_white = np.where(earm, 1e3, d_white)
    # irregular, asymmetric white boundary (world-space noise, not mirrored);
    # round 4: the big lobes only start on the chest, so the throat white is
    # not broken into islands
    body_w = smoothstep(-110.0, -160.0, zw)
    lobes = (fbm(Pw, 0.030, 3, 21.0) - 0.5) * (8.0 + 24.0 * body_w)
    fing = (fbm(Pw * np.array([1.0, 1.0, 0.22]), 0.0045, 2, 23.0) - 0.5) * (3.0 + 9.0 * body_w)
    white = 1.0 - smoothstep(-edge, edge, d_white + jit + lobes + fing)

    # ---- mackerel stripes
    d_str = dist_to_curves(P3, marking_curves())
    stripe = 1.0 - smoothstep(-edge, edge, d_str + jit)
    # necklaces and body bands (world frame): narrow rings with broken edges
    ang = np.arctan2(yw, xw + 40.0)
    zz = zw + 5.0 * np.sin(ang * 2.0 + 0.7) + 3.0 * np.sin(ang * 5.0 + 1.3)
    per = 34.0
    ph_ = np.mod(zz + 8.0, per) - 0.5 * per
    wband = 5.6 + 1.2 * np.sin(ang * 3.0)
    body_band = (np.abs(ph_) - wband) * smoothstep(-30.0, -70.0, zw)
    # dorsal stripe down the spine
    dors = np.maximum(ay - 8.0, xw + 60.0) + 1e3 * (zw > -20.0)
    d_body = np.minimum(body_band + 1e3 * (zw > -80.0), dors)
    stripe = np.maximum(stripe, 1.0 - smoothstep(-edge, edge, d_body + jit))
    # ears: dark tabby back and rims, darker toward the tip, a faint pale
    # thumbprint; pale inner hairs
    ear_back = earm & (ear_face < 0.2)
    thumb = _bump(ear_t, 0.30, 0.60) * _bump(ear_u, -0.30, 0.40) * ear_back
    # the rim hair is agouti ground, not dark, so no dark line outlines the
    # ear from the front
    ear_rim_c = smoothstep(0.86, 0.98, np.abs(ear_u))
    ear_back_dark = (0.72 + 0.18 * smoothstep(0.70, 0.95, ear_t)) * (1.0 - 0.7 * ear_rim_c)
    stripe = np.where(earm, np.where(ear_face > 0.2, 0.0, ear_back_dark), stripe)
    # round 4: fully white inner hairs (at 0.85 the remaining agouti hairs'
    # dark tips printed as dirty specks on the pink inner skin)
    white = np.where(earm & (ear_face > 0.2), 1.0, white)
    stripe = np.clip(stripe * (1.0 - 0.6 * thumb), 0.0, 1.0)
    stripe = np.clip(stripe * (1.0 - white), 0.0, 1.0)
    # follicle spots on the pads (round 4: 5 rows, in the pad's (y, z) plane
    # on its front, so every spot lands on the skin)
    fs = follicle_spots()
    on_pad = smoothstep(112.0 + mz, 120.0 + mz, x) * smoothstep(0.15, 0.40, Nh[:, 0])
    fol = np.full(n, 1e3)
    m_pad = on_pad > 0
    if m_pad.any():
        q = np.stack([ay[m_pad], z[m_pad]], -1)
        dd = np.min(np.linalg.norm(q[:, None, :] - fs[None], axis=-1), axis=1)
        fol[m_pad] = dd - 0.75
    for s_, row, col, p in mystacial_roots():
        fol = np.minimum(fol, np.linalg.norm(P3[:, 1:] - p[1:], axis=1) - 0.95 + 1e3 * (on_pad <= 0))
    fdot = 0.9 * (1.0 - smoothstep(-0.25, 0.25, fol)) * on_pad
    stripe = np.maximum(stripe, fdot)
    white = white * (1.0 - fdot)
    q2l = np.stack([y, z], -1)
    d_leather = sd_poly2d(q2l, leather_poly())

    # ---- eyes: fissure distance (mm; + outside the aperture)
    d_fis = np.full(n, 1e3)
    near_eye = np.zeros(n, bool)
    for s in (1.0, -1.0):
        c = lid_center(s) / MM
        m = np.linalg.norm(P3 - c, axis=1) < 42.0
        if not m.any():
            continue
        near_eye |= m
        d2 = sd_fissure(Ph[m], s) / MM
        rr = np.linalg.norm(Ph[m] - eye_center(s), axis=1) / MM
        d2 = np.where(rr < (A.eye_r + A.lid_gap + A.lid_t + A.lid_upper_extra) / MM + 3.0, d2, 1e3)
        d_fis[m] = np.minimum(d_fis[m], d2)
    # pale spectacle rim just outside the black lid margin (round 4)
    spect = (1.0 - smoothstep(4.5, 7.5, d_fis)) * smoothstep(2.0, 2.8, d_fis)
    pale = np.clip(np.maximum(0.85 * spect, 0.6 * thumb), 0.0, 1.0)

    # ---- regions
    q2 = q2l
    # nose leather: the inverted-triangle shield, only on the front of the nose
    nose = (1.0 - smoothstep(-0.3, 0.3, d_leather)) * smoothstep(NOSE_X0 - 3.0, NOSE_X0 + 1.0, x) * smoothstep(-0.25, 0.05, Nh[:, 0])
    pig = np.zeros(n)
    # round 4: a 2 mm pigmented lid margin (round 3: ~1.1 mm, with a pale bare
    # strip before the fur) and the conjunctiva inside the aperture
    pig = np.maximum(pig, 1.0 - smoothstep(1.9, 2.5, np.abs(d_fis)))
    pig = np.maximum(pig, (d_fis < 0).astype(float) * near_eye)
    # nostril slits, cut into the leather (thin pigment: the darkness comes
    # from the cavity, not from a painted crescent)
    fr = smoothstep(NOSE_X0 - 6.0, NOSE_X0, x)
    for s in (1.0, -1.0):
        poly = [(yy * s, zz_) for yy, zz_ in NOSTRIL_POLY]
        dn = dist_poly2d(q2, poly) - 0.35
        pig = np.maximum(pig, 0.70 * (1.0 - smoothstep(0.0, 0.30, dn)) * fr)
    # a hairline dark edge on the leather itself (skin only; round 3's liner
    # also darkened the fur and smeared grey down the side of the nose)
    liner = (1.0 - smoothstep(0.0, 0.5, d_leather)) * smoothstep(-0.7, -0.1, d_leather) * smoothstep(NOSE_X0 - 2.0, NOSE_X0 + 1.0, x) * smoothstep(-2.0, -6.0, z)
    # (round 4: not applied; with the nares it read as a black grin)
    # lip line: the short inverted Y; the side line is faint and stays under
    # the pad fur
    for s in (1.0, -1.0):
        dl = dist_poly2d(q2, [(yy * s, zz_) for yy, zz_ in LIP_FRONT])
        pig = np.maximum(pig, (1.0 - smoothstep(0.6, 1.1, dl)) * smoothstep(118.0 + mz, 124.0 + mz, x))
    dls = dist_poly2d(np.stack([x, z], -1), LIP_SIDE)
    pig = np.maximum(pig, 0.35 * (1.0 - smoothstep(0.5, 0.9, dls)) * smoothstep(18.0, 24.0, ay) * (1.0 - smoothstep(40.0, 46.0, ay))
                     * (1.0 - smoothstep(112.0 + mz, 118.0 + mz, x)))
    pig = np.maximum(pig, 1.0 - smoothstep(-0.3, 0.3, fol))
    # lacrimal line: pigmented skin under the dark hairs of the line, strongest
    # at the (wet) medial canthus
    names = [m_[0] for m_ in MARKINGS for _ in (1.0, -1.0)]
    lac = [c_ for nm_, c_ in zip(names, marking_curves()) if nm_ == "lacrimal"]
    d_lac = dist_to_curves(P3, lac)
    pig = np.maximum(pig, 0.8 * (1.0 - smoothstep(-0.2, 0.5, d_lac + 0.4 * jit)))
    pig = np.where(earm, 0.0, pig)
    lipm = np.maximum.reduce([(1.0 - smoothstep(0.5, 1.0, dist_poly2d(q2, [(yy * s, zz_) for yy, zz_ in LIP_FRONT]))) * smoothstep(118.0 + mz, 124.0 + mz, x) for s in (1.0, -1.0)])
    # inner-ear skin: pale pink over the whole inner face, a little darker
    # deep in the concha (the deep cone now shades itself)
    inner = (earm & (ear_face > 0.2)).astype(float)
    ear_in = inner
    concha = inner * (1.0 - smoothstep(0.05, 0.30, ear_t)) * (1.0 - smoothstep(0.35, 0.75, np.abs(ear_u)))
    pig = np.maximum(pig, 0.22 * concha)

    # ---- groom: length (mm, character scale), lift (deg), density
    # round 4: the cheek/jowl ruff is shorter and its lift falls from 29 to
    # ~12 deg (it radiated like a mane); a short brow key stops the brow tuft
    # hiding the eye in profile; the throat runs smoothly into a 26-34 mm
    # neck ruff
    keys = [
        ((141 + mz, 0, -8), 2.4, 8), ((130 + mz, 0, 12), 3.0, 10), ((112 + mz, 0, 32), 3.8, 11), ((95, 0, 52), 5.2, 13), ((64, 0, 72), 7.0, 17),
        ((15, 0, 88), 9.5, 22), ((-35, 0, 82), 12.0, 24), ((-72, 0, 42), 15.0, 22), ((-90, 0, 0), 18.0, 22),
        ((136 + mz, 14, -24), 2.4, 9), ((130 + mz, 26, -34), 3.0, 10), ((114 + mz, 33, -46), 4.0, 10), ((112 + mz, 0, -62), 3.6, 10), ((84, 0, -80), 8.0, 10),
        ((92, 40, 21), 3.0, 12), ((86, 36, 44), 3.4, 8), ((80, 62, 5), 6.0, 13), ((50, 82, 5), 9.0, 14), ((24, 86, -18), 14.0, 16),
        ((4, 80, -44), 17.0, 18), ((32, 72, -42), 12.0, 14), ((46, 0, -86), 15.0, 18), ((0, 62, 70), 6.5, 13),
        ((-40, 55, 50), 11.0, 20), ((-70, 60, 10), 16.0, 22),
    ]
    num = np.zeros(n)
    den = np.full(n, 1e-6)
    for (c, Lk, sig) in keys:
        for s in ((1.0, -1.0) if c[1] else (1.0,)):
            d2 = ((x - c[0]) ** 2 + (y - c[1] * s) ** 2 + (z - c[2]) ** 2) / (sig * sig)
            w = np.exp(-d2)
            num += w * Lk
            den += w
    headL = num / den
    headw = np.clip(den * 1.5, 0.0, 1.0)
    # round 4: behind the jaw the head keys fade out over the upper neck, so
    # the neck ruff reaches up to the jaw (round-4 test: with full head
    # weight there the upper-neck hair stayed ~15 mm and flat, and the fur
    # silhouette of the neck was still ~0.69 of the cheek width)
    neckm = smoothstep(-50.0, -88.0, zw) * (1.0 - smoothstep(20.0, 55.0, x))
    headw = headw * (1.0 - neckm)
    # body (world): a neck ruff all round the neck, the chest ruff longest on
    # the sternum (round 4: no midline parting on the chest or throat)
    front = smoothstep(-0.2, 0.4, Nw[:, 0])
    ruff = _bump(zw, -235.0, -110.0) * front
    neck = _bump(zw, -150.0, -55.0)
    bodyL = 19.0 + 16.0 * ruff + 13.0 * neck + 3.0 * smoothstep(-150.0, -300.0, zw)
    arm = smoothstep(95.0, 125.0, ay) * smoothstep(-160.0, -220.0, zw)
    bodyL = bodyL * (1.0 - 0.35 * arm)
    L = headL * headw + bodyL * (1.0 - headw)
    L = L * (1.0 - 0.55 * np.exp(-np.maximum(d_fis, 0.0) / 3.0))  # short periocular hair
    # pinna (round 4): 3.8-4.6 mm dark coat over the whole convex back,
    # ~1.8 mm hair wrapping both rolled margins, fine 2.6-4.6 mm hairs on the
    # inner face near the margins (the long furnishings are grown separately)
    rimz = smoothstep(0.86, 0.98, np.abs(ear_u))
    L_back = (4.6 - 1.6 * smoothstep(0.85, 1.0, ear_t)) * (1.0 - 0.45 * rimz)
    L_in = 3.2 + 2.2 * smoothstep(0.6, 0.95, np.abs(ear_u))
    L = np.where(earm, np.where(ear_face > 0.2, L_in, L_back), L)
    L = L * (0.94 + 0.12 * fbm(Pw, 0.012, 2, 2.0))
    # lift: head and body values blended over a wide band (round 3 switched
    # them with a hard step at world z = -80, whose contour on the sloping
    # underside of the jaw drew the V-shaped throat seam)
    lift_h = (7.0 + 3.0 * smoothstep(40.0, 80.0, z) * (1 - np.clip(-zw / 100.0, 0, 1))
              + 8.0 * np.exp(-((x - 18) ** 2 + (ay - 82) ** 2 + (z + 34) ** 2) / 1100.0))
    throat_front = smoothstep(0.2, 0.7, Nw[:, 0])
    lift_b = 12.0 + 6.0 * ruff + 18.0 * neck * (1.0 - 0.8 * throat_front) - 3.0 * arm
    hb = np.maximum(smoothstep(-60.0, -125.0, zw), neckm)
    lift = lift_h * (1.0 - hb) + lift_b * hb
    lift = lift - 3.0 * np.exp(-((x - 122 - mz) ** 2 + (ay - 20) ** 2 + (z + 32) ** 2) / 500.0)  # muzzle lies flat
    lift = np.where(earm, np.where(ear_face > 0.2, 8.0 + 10.0 * rimz, 5.0 + 12.0 * rimz), lift)
    # smooth large-scale density (constant coverage: shorter hair, more strands)
    density = np.clip(7.0 / np.maximum(L, 1.0), 0.35, 1.0)
    # inner pinna: bare deep in the concha, sparse fine hairs near the margins
    deep = (1.0 - smoothstep(0.06, 0.18, ear_t)) * (1.0 - smoothstep(0.35, 0.6, np.abs(ear_u)))
    inner_d = (0.28 + 0.40 * smoothstep(0.55, 0.9, np.abs(ear_u))) * (1.0 - deep)
    density = np.where(earm, np.where(ear_face > 0.2, inner_d, 1.0 - 0.3 * smoothstep(0.93, 1.0, ear_t)), density)
    density = density * smoothstep(-598.0, -585.0, zw)
    # sharp exclusions (baked to the fur mask texture): nose leather, lip
    # margin, nostrils; round 4: the fur starts ~1.3-2.2 mm from the fissure,
    # on the pigmented margin, so no bare pale skin shows between them
    excl = (1.0 - nose) * (1.0 - lipm) * smoothstep(1.3, 2.2, d_fis)
    for s in (1.0, -1.0):
        dn = dist_poly2d(q2, [(yy * s, zz_) for yy, zz_ in NOSTRIL_POLY]) - 0.8
        excl = excl * np.where(x > NOSE_X0 - 4.0, smoothstep(0.0, 1.2, dn), 1.0)
    excl = np.where(earm, 1.0, excl)
    return dict(white=white, stripe=stripe, pale=pale, nose=nose, pig=np.clip(pig, 0, 1), ear_inner=ear_in,
                length=L * MM, density=np.clip(density, 0, 1), excl=np.clip(excl, 0, 1), lift=lift, d_fis=d_fis, lip=lipm)


def fur_direction(Pw, Nw, ex=None):
    """Tangent fur-flow field (world-local unit vectors): radial from the nose
    over the bridge, forehead, crown and cheeks (round 3: no midline parting;
    round 2's parting plus the unwelded midline printed a straight part down
    the crown); radial from each mystacial pad; combed away from and
    around each eye; back and down over the jowls; down the throat and the
    chest ruff, the nape, back and arms; toward the tip on the pinna.

    Round 4: the chin, the underside of the jaw, the throat and the whole
    body share ONE down-and-back direction (-0.55, 0, -0.84), blended in over
    a wide band, which never falls parallel to the surface normal there (the
    round-3 blend toward a pure 'down' vector degenerated on the underside of
    the jaw, and the sternal parting ran up the throat; together they drew
    the V and the midline seams). The cheek ruff sweeps caudoventrally."""
    Pw = np.asarray(Pw, float)
    Nw = np.asarray(Nw, float)
    n = len(Pw)
    is_ear, ear_t, ear_u, ear_face = ex_arrays(n, ex)
    Ph = Pw @ head_R()
    Nh = Nw @ head_R()
    P3 = Ph / MM
    x, y, z = P3[:, 0], P3[:, 1], P3[:, 2]
    ay = np.abs(y)
    sy = np.where(y >= 0, 1.0, -1.0)
    src = np.array([168.0 + A.mz, 0.0, -14.0])
    vh = P3 - src
    vh /= np.linalg.norm(vh, axis=1, keepdims=True) + 1e-9
    # mystacial pads: radial from the pad centres
    for s in (1.0, -1.0):
        c = np.array([127.0 + A.mz, PAD_C[1] * s, PAD_C[2]])
        w = np.exp(-np.sum((P3 - c) ** 2, 1) / (15.0 ** 2))[:, None]
        r = P3 - c
        r /= np.linalg.norm(r, axis=1, keepdims=True) + 1e-9
        vh = vh * (1 - w) + r * w
    # jowls and cheeks: back and down; chin and under the jaw: back and down
    wj = (smoothstep(55.0, 78.0, ay) * smoothstep(12.0, -25.0, z))[:, None]
    ruffdir = np.stack([np.full(n, -0.62), 0.12 * sy, np.full(n, -0.78)], 1)  # back and down (caudoventral)
    vh = vh * (1 - 0.75 * wj) + ruffdir * 0.75 * wj
    bdir_w = np.array([-0.55, 0.0, -0.84])
    bdir_w /= np.linalg.norm(bdir_w)
    bdir_h = bdir_w @ head_R()  # the same world direction in the head frame
    wc = (smoothstep(-50.0, -64.0, z) * smoothstep(30.0, 60.0, x) * (1 - smoothstep(40.0, 60.0, ay)))[:, None]
    vh = vh * (1 - 0.7 * wc) + bdir_h * 0.7 * wc
    # eyes: remove the component pointing into the eye, comb away at the margin
    for s in (1.0, -1.0):
        c = eye_center(s) / MM
        q = P3 - c
        m = np.linalg.norm(q, axis=1) < 45.0
        if not m.any():
            continue
        d2 = sd_fissure(Ph[m], s) / MM
        qm = q[m] - np.sum(q[m] * Nh[m], 1, keepdims=True) * Nh[m]
        rhat = qm / (np.linalg.norm(qm, axis=1, keepdims=True) + 1e-9)
        comp = np.sum(vh[m] * rhat, 1, keepdims=True)
        near = np.exp(-(np.maximum(d2, 0.0) / 9.0) ** 2)[:, None]
        vh[m] = vh[m] - rhat * np.minimum(comp, 0.0) * near + rhat * (0.9 * np.exp(-(np.maximum(d2, 0.0) / 3.0) ** 2))[:, None]
    vw = vh @ head_R().T
    # ears: toward the tip along the pinna axis; round 4: near both margins
    # the hair turns outward across the edge (a short fringe), so no bare
    # skin edge silhouettes
    earm = is_ear > 0.5
    if earm.any():
        for s in (1.0, -1.0):
            m = earm & (sy == s)
            F = ear_frame(s)
            ax = F[:, 2] @ head_R().T
            lat = (F[:, 1] * s) @ head_R().T
            rim = smoothstep(0.80, 0.97, np.abs(ear_u[m]))[:, None]
            out_ = np.sign(ear_u[m])[:, None] * lat[None, :]
            vw[m] = ax[None, :] * (1.0 - 0.75 * rim) + out_ * 0.75 * rim
    # body: one down-and-back direction (no sternal parting), blended in
    # over a wide band below the jaw
    zw = Pw[:, 2] / MM
    hb = smoothstep(-55.0, -130.0, zw)[:, None]
    down = np.tile(bdir_w, (n, 1))
    # neck ruff: on the sides of the neck the hair also sweeps outward
    side_w = (np.abs(Nw[:, 1]) * _bump(zw, -150.0, -60.0))[:, None]
    down = down + np.stack([np.zeros(n), 0.45 * np.sign(Pw[:, 1]), np.zeros(n)], 1) * side_w
    vw = np.where(earm[:, None], vw, vw * (1 - hb) + down * hb)
    t = vw - np.sum(vw * Nw, 1, keepdims=True) * Nw
    t /= np.linalg.norm(t, axis=1, keepdims=True) + 1e-9
    return t


# ---------------------------------------------------------------------------
# Blender object construction
# ---------------------------------------------------------------------------

def link(ob, coll=None):
    (coll or bpy.context.scene.collection).objects.link(ob)
    return ob


def set_active(ob):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)


def clean_manifold(me):
    bm = bmesh.new()
    bm.from_mesh(me)
    for _ in range(8):
        bad = [e for e in bm.edges if not e.is_manifold]
        badv = [vv for vv in bm.verts if not vv.is_manifold]
        if not bad and not badv:
            break
        faces = set()
        for e in bad:
            faces.update(e.link_faces)
        for vv in badv:
            faces.update(vv.link_faces)
        bmesh.ops.delete(bm, geom=list(faces), context="FACES")
        bmesh.ops.delete(bm, geom=[vv for vv in bm.verts if not vv.link_faces], context="VERTS")
        bmesh.ops.holes_fill(bm, edges=bm.edges, sides=0)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    me.update()


def mesh_arrays(me):
    n = len(me.vertices)
    co = np.empty(n * 3, np.float32)
    me.vertices.foreach_get("co", co)
    nr = np.empty(n * 3, np.float32)
    me.vertices.foreach_get("normal", nr)
    return co.reshape(-1, 3).astype(np.float64), nr.reshape(-1, 3).astype(np.float64)


def sanitize_for_quadriflow(me):
    clean_manifold(me)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=3e-6)
    bmesh.ops.dissolve_degenerate(bm, dist=3e-6, edges=bm.edges)
    bmesh.ops.delete(bm, geom=[e for e in bm.edges if e.is_wire], context="EDGES")
    bmesh.ops.delete(bm, geom=[vv for vv in bm.verts if not vv.link_faces], context="VERTS")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    clean_manifold(me)


def quadriflow_ready(me):
    """Mirror of Blender's mesh_is_manifold_consistent() used by QuadriFlow."""
    me.update()
    nl = len(me.loops)
    lv = np.empty(nl, np.int32)
    le = np.empty(nl, np.int32)
    me.loops.foreach_get("vertex_index", lv)
    me.loops.foreach_get("edge_index", le)
    cnt = np.bincount(le, minlength=len(me.edges))
    if cnt.max() > 2 or (cnt == 0).any():
        return False
    order = np.argsort(le, kind="stable")
    e_sorted = le[order]
    v_sorted = lv[order]
    first = np.r_[True, e_sorted[1:] != e_sorted[:-1]]
    pairs = ~first
    if np.any(v_sorted[pairs] == v_sorted[np.nonzero(pairs)[0] - 1]):
        return False
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    ev = np.empty(len(me.edges) * 2, np.int32)
    me.edges.foreach_get("vertices", ev)
    ev = ev.reshape(-1, 2)
    if np.any(np.all(np.abs(co[ev[:, 0]] - co[ev[:, 1]]) < 1e-4, axis=1)):
        return False
    return True


def build_skin(coll):
    d = np.load(CACHE / "skin_dense.npz")
    dense_me = mesh_from_arrays("CatBaseV6_SculptSource", d["pts"], d["quads"])
    clean_manifold(dense_me)
    dense = link(bpy.data.objects.new("CatBaseV6_SculptSource", dense_me), coll)
    dense.location = HEAD_ORIGIN
    # decimated sculpt target (kept in the .blend as the shrinkwrap/detail source)
    # and a QuadriFlow quad cage. QuadriFlow refuses meshes with flipped/non-
    # manifold edges or edges under 1e-4 units, so the target is scaled x100 and
    # sanitised; ratios are retried until Blender's own check would pass.
    cage = None
    for ratio in (0.16, 0.12, 0.2, 0.1):
        if cage is not None:
            bpy.data.objects.remove(cage, do_unlink=True)
        if "CatBaseV6_SculptTarget" in bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects["CatBaseV6_SculptTarget"], do_unlink=True)
        tgt = link(bpy.data.objects.new("CatBaseV6_SculptTarget", dense_me.copy()), coll)
        tgt.location = HEAD_ORIGIN
        set_active(tgt)
        m = tgt.modifiers.new("dec", "DECIMATE")
        m.ratio = ratio
        bpy.ops.object.modifier_apply(modifier="dec")
        sanitize_for_quadriflow(tgt.data)
        tgt.data.name = "CatBaseV6_SculptTarget"
        cage = link(bpy.data.objects.new("CatBaseV6_Skin", tgt.data.copy()), coll)
        cage.location = HEAD_ORIGIN
        cage.data.name = "CatBaseV6_SkinCage"
        set_active(cage)
        cage.data.use_mirror_y = True
        cage.data.transform(Matrix.Scale(100.0, 4))
        ok = quadriflow_ready(cage.data)
        r = bpy.ops.object.quadriflow_remesh(use_mesh_symmetry=True, use_preserve_sharp=False, use_preserve_boundary=False,
                                             preserve_attributes=False, smooth_normals=False, mode="FACES", target_faces=64000, seed=3)
        cage.data.transform(Matrix.Scale(0.01, 4))
        log("quadriflow", ratio, "precheck", ok, r, len(cage.data.polygons), "faces")
        if "FINISHED" in r:
            break
    else:
        raise RuntimeError("QuadriFlow could not remesh the sculpt target")
    weld_midline(cage.data)
    # ---- pinnae: separate parametric meshes joined into the skin as their own
    # mesh islands (the groom parts children by island, so ear fur only
    # interpolates ear guides); only the head is shrink-wrapped to the sculpt
    n_head = len(cage.data.vertices)
    for k in EAR_ATTRS:
        cage.data.attributes.new(k, "FLOAT", "POINT")
    ears = []
    for s in (1.0, -1.0):
        me = ear_mesh(s)
        ob = link(bpy.data.objects.new(me.name, me), coll)
        ob.location = HEAD_ORIGIN
        ears.append(ob)
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    cage.select_set(True)
    for e in ears:
        e.select_set(True)
    bpy.context.view_layer.objects.active = cage
    bpy.ops.object.join()
    vg = cage.vertex_groups.new(name="HeadShrink")
    vg.add(list(range(n_head)), 1.0, "REPLACE")
    # UVs
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(64), island_margin=0.0015, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    cage.data.uv_layers[0].name = "UVMap"
    for p in cage.data.polygons:
        p.use_smooth = True
    sub = cage.modifiers.new("Subdivision", "SUBSURF")
    sub.levels = 1
    sub.render_levels = 2
    sub.uv_smooth = "PRESERVE_BOUNDARIES"
    sw = cage.modifiers.new("SculptDetail", "SHRINKWRAP")
    sw.target = tgt
    sw.wrap_method = "NEAREST_SURFACEPOINT"
    sw.vertex_group = "HeadShrink"
    tgt.hide_render = True
    tgt.hide_viewport = True
    # smooth large-scale fur density on the cage (interpolated by subdivision);
    # the sharp exclusions live in the baked fur-mask texture
    co, nr = mesh_arrays(cage.data)
    ex = {k: attr_array(cage.data, k) for k in EAR_ATTRS}
    fields = coat_fields(co, nr, ex)
    a = cage.data.attributes.new("fur_density", "FLOAT", "POINT")
    a.data.foreach_set("value", fields["density"].astype(np.float32))
    return dense, tgt, cage


EAR_ATTRS = ("is_ear", "ear_t", "ear_u", "ear_face")


def mesh_islands(me):
    """Number of connected vertex islands (union-find over edges)."""
    n = len(me.vertices)
    ev = np.empty(len(me.edges) * 2, np.int64)
    me.edges.foreach_get("vertices", ev)
    ev = ev.reshape(-1, 2)
    parent = np.arange(n)
    for _ in range(64):
        a, b = parent[ev[:, 0]], parent[ev[:, 1]]
        lo_ = np.minimum(a, b)
        np.minimum.at(parent, ev[:, 0], lo_)
        np.minimum.at(parent, ev[:, 1], lo_)
        parent = parent[parent]
    return len(np.unique(parent))


def weld_midline(me):
    """Round 3: QuadriFlow's symmetric mode returns two mirrored halves that
    share duplicated, unwelded vertices on the midsagittal plane. Round 2
    shipped them unwelded: the Subdivision modifier treated the midline as an
    open boundary (a ridge along the crown, forehead, chin and throat) and the
    groom's Part by Mesh Islands parted the fur down the middle. Weld them."""
    before = mesh_islands(me)
    bm = bmesh.new()
    bm.from_mesh(me)
    mid = [vv for vv in bm.verts if abs(vv.co.y) < 1e-5]
    bmesh.ops.remove_doubles(bm, verts=mid, dist=2e-5)
    bnd = sum(1 for e in bm.edges if e.is_boundary)
    bm.to_mesh(me)
    bm.free()
    me.update()
    log(f"midline weld: {len(mid)} midline verts, islands {before} -> {mesh_islands(me)}, open boundary edges {bnd}")


def attr_array(me, name):
    n = len(me.vertices)
    out = np.zeros(n, np.float32)
    if name in me.attributes:
        me.attributes[name].data.foreach_get("value", out)
    return out.astype(np.float64)


# ---------------------------------------------------------------------------
# Texture bake: every covered texel is evaluated directly from the 3D fields
# ---------------------------------------------------------------------------

def rasterize_uv(UV, res, chunk=3_000_000):
    """Texels (row-major index), triangle ids and barycentrics for every texel
    centre covered by a UV triangle. UV: (T, 3, 2) in [0, 1]."""
    P = UV * res - 0.5
    a, b, c = P[:, 0], P[:, 1], P[:, 2]
    mn = np.clip(np.floor(P.min(1)).astype(np.int64), 0, res - 1)
    mx = np.clip(np.ceil(P.max(1)).astype(np.int64), 0, res - 1)
    size = (mx - mn + 1).max(1)
    v0, v1 = b - a, c - a
    d00 = (v0 * v0).sum(1)
    d01 = (v0 * v1).sum(1)
    d11 = (v1 * v1).sum(1)
    den = d00 * d11 - d01 * d01
    ok = np.abs(den) > 1e-10
    T, I, Bc = [], [], []
    for bsz in np.unique(size[ok]):
        ids = np.nonzero(ok & (size == bsz))[0]
        g = np.arange(bsz)
        gx, gy = np.meshgrid(g, g, indexing="ij")
        off = np.stack([gx.ravel(), gy.ravel()], -1)
        step = max(1, chunk // len(off))
        for k0 in range(0, len(ids), step):
            ch = ids[k0:k0 + step]
            pix = mn[ch][:, None, :] + off[None]
            v2 = pix - a[ch][:, None, :]
            d20 = (v2 * v0[ch][:, None, :]).sum(-1)
            d21 = (v2 * v1[ch][:, None, :]).sum(-1)
            vv = (d11[ch][:, None] * d20 - d01[ch][:, None] * d21) / den[ch][:, None]
            ww = (d00[ch][:, None] * d21 - d01[ch][:, None] * d20) / den[ch][:, None]
            uu = 1.0 - vv - ww
            e = 1e-4
            ins = (uu >= -e) & (vv >= -e) & (ww >= -e) & (pix[..., 0] < res) & (pix[..., 1] < res)
            r, q = np.nonzero(ins)
            T.append(ch[r])
            I.append(pix[r, q, 1] * res + pix[r, q, 0])
            Bc.append(np.stack([uu[r, q], vv[r, q], ww[r, q]], -1))
    return np.concatenate(T), np.concatenate(I), np.concatenate(Bc)


def dilate(img, mask, iters=12):
    img = img.copy()
    m = mask.copy()
    for _ in range(iters):
        acc = np.zeros_like(img)
        cnt = np.zeros(m.shape, np.float32)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            sm = np.roll(np.roll(m, dy, 0), dx, 1)
            acc += np.roll(np.roll(img, dy, 0), dx, 1) * sm[..., None]
            cnt += sm
        new = (~m) & (cnt > 0)
        img[new] = acc[new] / cnt[new][:, None]
        m |= new
    return img


def save_png(name, arr, depth="8"):
    res = arr.shape[0]
    img = bpy.data.images.new(name, res, res, alpha=False, float_buffer=False)
    img.colorspace_settings.name = "Non-Color"
    px = np.ones((res, res, 4), np.float32)
    px[..., :3] = np.clip(arr, 0.0, 1.0)
    img.pixels.foreach_set(px.ravel())
    tex_dir = OUT / "Textures"
    tex_dir.mkdir(parents=True, exist_ok=True)
    img.filepath_raw = str(tex_dir / f"{name}.png")
    img.file_format = "PNG"
    bpy.context.scene.render.image_settings.color_depth = depth
    img.save()
    img.filepath = "//Textures/" + f"{name}.png"
    return img


def bake_textures(cage, res):
    """Bake the coat, region and fur-mask maps by evaluating the procedural
    fields at the 3D point under every texel of the cage UVs (subdivided,
    shrink-wrapped surface), so stripe edges stay hair-sharp and the pinnae
    (not in the level set) are baked like the rest of the skin."""
    t0 = time.time()
    S = evaluated_surface(cage)
    UV = S["uv"][S["tl"]]
    tri, tex, bc = rasterize_uv(UV, res)
    log(f"bake raster: {len(tex)} texel samples from {len(S['tv'])} tris ({time.time()-t0:.0f}s)")
    coat = np.zeros((res * res, 3), np.float32)
    reg = np.zeros((res * res, 3), np.float32)
    msk = np.zeros((res * res, 3), np.float32)
    cov = np.zeros(res * res, bool)
    step = 1_000_000
    for k0 in range(0, len(tex), step):
        tr = tri[k0:k0 + step]
        w = bc[k0:k0 + step]
        vid = S["tv"][tr]
        P = np.einsum("ij,ijk->ik", w, S["co"][vid])
        Nn = np.einsum("ij,ijk->ik", w, S["nr"][vid])
        Nn /= np.linalg.norm(Nn, axis=1, keepdims=True) + 1e-12
        ex = {k: np.einsum("ij,ij->i", w, S["attrs"][k][vid]) for k in EAR_ATTRS}
        f = coat_fields(P, Nn, ex)
        ti = tex[k0:k0 + step]
        coat[ti] = np.stack([f["white"], f["stripe"], f["pale"]], -1)
        reg[ti] = np.stack([f["nose"], f["pig"], f["ear_inner"]], -1)
        msk[ti] = f["excl"][:, None]
        cov[ti] = True
    log(f"bake fields evaluated ({time.time()-t0:.0f}s)")
    cov2 = cov.reshape(res, res)
    images = {}
    for name, arr in (("Coat", coat), ("Regions", reg), ("FurMask", msk)):
        a = dilate(arr.reshape(res, res, 3), cov2, 10)
        images[name.lower()] = save_png(f"T_CatBaseV6_{name}", a)
    log(f"baked maps {res}px ({time.time()-t0:.0f}s)")
    return images


# ---------------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------------

def new_mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes.clear()
    return m, m.node_tree


def N(nt, kind, loc=(0, 0), **inputs):
    n = nt.nodes.new(kind)
    n.location = loc
    for k, val in inputs.items():
        n.inputs[k].default_value = val
    return n


def L(nt, a, b):
    nt.links.new(a, b)


def image_node(nt, img, loc, uv_attr=None):
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = img
    t.location = loc
    t.interpolation = "Linear"
    if uv_attr:
        at = nt.nodes.new("ShaderNodeAttribute")
        at.attribute_name = uv_attr
        at.location = (loc[0] - 250, loc[1])
        L(nt, at.outputs["Vector"], t.inputs["Vector"])
    else:
        uv = nt.nodes.new("ShaderNodeUVMap")
        uv.uv_map = "UVMap"
        uv.location = (loc[0] - 250, loc[1])
        L(nt, uv.outputs["UV"], t.inputs["Vector"])
    return t


def mix_rgb(nt, fac, a, b, loc):
    m = N(nt, "ShaderNodeMix", loc)
    m.data_type = "RGBA"
    for inp, val in ((m.inputs["Factor"], fac), (m.inputs[6], a), (m.inputs[7], b)):
        if isinstance(val, tuple):
            inp.default_value = val if len(val) == 4 else (*val, 1.0)
        elif isinstance(val, (int, float)):
            inp.default_value = val
        else:
            L(nt, val, inp)
    return m.outputs[2]


def skin_material(images):
    """Skin under the coat, pink nose leather, black lid/lip/nostril
    pigment and the inner-ear skin.

    Round 4: the leather pebbling is ~0.38 mm cells (round 3's 0.8 mm cells
    read as reptile scales) at less than half the bump; the leather is moist
    at the lower tip (roughness ~0.3) and matte on top (~0.55); the inner ear
    is thin pale-pink skin with real subsurface translucency; and there is no
    subsurface under the furred skin (round 3's white muzzle showed a faint
    pink cast)."""
    m, nt = new_mat("M_CatBaseV6_Skin")
    out = N(nt, "ShaderNodeOutputMaterial", (1600, 0))
    bs = N(nt, "ShaderNodeBsdfPrincipled", (1300, 0))
    coat = image_node(nt, images["coat"], (-900, 300))
    reg = image_node(nt, images["regions"], (-900, -200))
    sc = N(nt, "ShaderNodeSeparateColor", (-600, 300))
    sr = N(nt, "ShaderNodeSeparateColor", (-600, -200))
    L(nt, coat.outputs["Color"], sc.inputs["Color"])
    L(nt, reg.outputs["Color"], sr.inputs["Color"])
    c = mix_rgb(nt, sc.outputs["Green"], (0.15, 0.14, 0.135), (0.040, 0.036, 0.035), (-300, 500))
    c = mix_rgb(nt, sc.outputs["Red"], c, (0.50, 0.44, 0.42), (-100, 500))
    # inner-ear skin: thin, pale pink
    c = mix_rgb(nt, sr.outputs["Blue"], c, (0.56, 0.42, 0.40), (100, 500))
    # nose leather: fine pebbling as bump, faint crevice AO
    tc = N(nt, "ShaderNodeTexCoord", (-600, 900))
    vor = N(nt, "ShaderNodeTexVoronoi", (-350, 900))
    vor.feature = "DISTANCE_TO_EDGE"
    vor.inputs["Scale"].default_value = 2600.0
    vor.inputs["Randomness"].default_value = 0.85
    L(nt, tc.outputs["Object"], vor.inputs["Vector"])
    crev = N(nt, "ShaderNodeMapRange", (-100, 900))
    crev.inputs["From Min"].default_value = 0.0
    crev.inputs["From Max"].default_value = 0.16
    crev.interpolation_type = "SMOOTHSTEP"
    L(nt, vor.outputs["Distance"], crev.inputs["Value"])
    ao = N(nt, "ShaderNodeMapRange", (100, 900))
    ao.inputs["To Min"].default_value = 0.88
    ao.inputs["To Max"].default_value = 1.0
    L(nt, crev.outputs["Result"], ao.inputs["Value"])
    leather = N(nt, "ShaderNodeMix", (300, 800))
    leather.data_type = "RGBA"
    leather.blend_type = "MULTIPLY"
    leather.inputs["Factor"].default_value = 1.0
    leather.inputs[6].default_value = (0.40, 0.195, 0.18, 1.0)
    L(nt, ao.outputs["Result"], leather.inputs[7])
    c = mix_rgb(nt, sr.outputs["Red"], c, leather.outputs[2], (500, 500))
    c = mix_rgb(nt, sr.outputs["Green"], c, (0.012, 0.010, 0.010), (700, 500))
    L(nt, c, bs.inputs["Base Color"])
    # roughness: skin 0.55; leather moist at the lower tip (object z below
    # ~-44 mm) and matte on top; pigmented margins wet (0.2)
    sep = N(nt, "ShaderNodeSeparateXYZ", (-350, 650))
    L(nt, tc.outputs["Object"], sep.inputs["Vector"])
    wet = N(nt, "ShaderNodeMapRange", (-100, 650))
    L(nt, sep.outputs["Z"], wet.inputs["Value"])
    wet.inputs["From Min"].default_value = -0.047
    wet.inputs["From Max"].default_value = -0.031
    wet.inputs["To Min"].default_value = 0.30
    wet.inputs["To Max"].default_value = 0.56
    r1 = N(nt, "ShaderNodeMix", (800, 100))
    r1.data_type = "FLOAT"
    L(nt, sr.outputs["Red"], r1.inputs["Factor"])
    r1.inputs[2].default_value = 0.55
    L(nt, wet.outputs["Result"], r1.inputs[3])
    r2 = N(nt, "ShaderNodeMix", (1000, 100))
    r2.data_type = "FLOAT"
    L(nt, sr.outputs["Green"], r2.inputs["Factor"])
    L(nt, r1.outputs[0], r2.inputs[2])
    r2.inputs[3].default_value = 0.20
    L(nt, r2.outputs[0], bs.inputs["Roughness"])
    bump = N(nt, "ShaderNodeBump", (1000, -300))
    bump.inputs["Strength"].default_value = 1.0
    bump.inputs["Distance"].default_value = 0.00012
    bmul = N(nt, "ShaderNodeMath", (800, -300))
    bmul.operation = "MULTIPLY"
    L(nt, crev.outputs["Result"], bmul.inputs[0])
    L(nt, sr.outputs["Red"], bmul.inputs[1])
    L(nt, bmul.outputs[0], bump.inputs["Height"])
    L(nt, bump.outputs["Normal"], bs.inputs["Normal"])
    # subsurface only where the skin is bare: the inner ear (translucent) and
    # a little in the leather; none under the fur or in pigment
    s1 = N(nt, "ShaderNodeMath", (600, -600))
    s1.operation = "MULTIPLY"
    L(nt, sr.outputs["Blue"], s1.inputs[0])
    s1.inputs[1].default_value = 0.20
    s2 = N(nt, "ShaderNodeMath", (600, -750))
    s2.operation = "MULTIPLY"
    L(nt, sr.outputs["Red"], s2.inputs[0])
    s2.inputs[1].default_value = 0.12
    s3 = N(nt, "ShaderNodeMath", (800, -650))
    s3.operation = "ADD"
    L(nt, s1.outputs[0], s3.inputs[0])
    L(nt, s2.outputs[0], s3.inputs[1])
    s4 = N(nt, "ShaderNodeMath", (950, -650))
    s4.operation = "MULTIPLY"
    s4.use_clamp = True
    L(nt, s3.outputs[0], s4.inputs[0])
    inv = N(nt, "ShaderNodeMath", (800, -850))
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    L(nt, sr.outputs["Green"], inv.inputs[1])
    L(nt, inv.outputs[0], s4.inputs[1])
    L(nt, s4.outputs[0], bs.inputs["Subsurface Weight"])
    bs.inputs["Subsurface Radius"].default_value = (0.6, 0.30, 0.22)
    bs.inputs["Subsurface Scale"].default_value = 0.0010
    bs.inputs["Specular IOR Level"].default_value = 0.45
    L(nt, bs.outputs["BSDF"], out.inputs["Surface"])
    return m


def hair_material(name, images, under=False):
    """Chiang hair BSDF with direct colouring. The coat mask is sampled at the
    strand root UV (surface_uv_coordinate, as a UE groom keeps it): white,
    stripe and pale factors. Agouti banding runs along the strand parameter:
    silver base, dark band, pale band, black tip, with per-strand jitter."""
    m, nt = new_mat(name)
    out = N(nt, "ShaderNodeOutputMaterial", (1600, 0))
    hb = N(nt, "ShaderNodeBsdfHairPrincipled", (1300, 0))
    hb.parametrization = "COLOR"
    hb.model = "CHIANG"
    coat = image_node(nt, images["coat"], (-900, 300), uv_attr="surface_uv_coordinate")
    sc = N(nt, "ShaderNodeSeparateColor", (-600, 300))
    L(nt, coat.outputs["Color"], sc.inputs["Color"])
    info = N(nt, "ShaderNodeHairInfo", (-1000, -300))
    rnd = N(nt, "ShaderNodeMapRange", (-800, -450))
    L(nt, info.outputs["Random"], rnd.inputs["Value"])
    rnd.inputs["To Min"].default_value = -0.08
    rnd.inputs["To Max"].default_value = 0.08
    pos = N(nt, "ShaderNodeMath", (-600, -300))
    pos.operation = "ADD"
    L(nt, info.outputs["Intercept"], pos.inputs[0])
    L(nt, rnd.outputs["Result"], pos.inputs[1])

    def ramp(loc, stops):
        r = N(nt, "ShaderNodeValToRGB", loc)
        cr = r.color_ramp
        cr.interpolation = "EASE"
        cr.elements[0].position = stops[0][0]
        cr.elements[0].color = (*stops[0][1], 1)
        cr.elements[1].position = stops[-1][0]
        cr.elements[1].color = (*stops[-1][1], 1)
        for p_, col in stops[1:-1]:
            e = cr.elements.new(p_)
            e.color = (*col, 1)
        L(nt, pos.outputs[0], r.inputs["Fac"])
        return r.outputs["Color"]

    # round 4 (judged round 3: contrast collapsed to a washed-out silver
    # face): ground hairs are banded slate root / pale band / dark tip
    # (pale band ~0.32), stripe hairs are solid dark
    # (~0.045), and each strand is EITHER a stripe/white hair or not, chosen
    # per strand from its root mask value, so marking edges are crisp at hair
    # level instead of a blurred map
    if not under:
        agouti = ramp((-350, -100), [(0.0, (0.09, 0.09, 0.09)), (0.20, (0.125, 0.125, 0.123)), (0.32, (0.31, 0.305, 0.29)),
                                     (0.60, (0.33, 0.325, 0.31)), (0.72, (0.05, 0.048, 0.047)), (1.0, (0.03, 0.03, 0.03))])
        pale = ramp((-350, -350), [(0.0, (0.30, 0.30, 0.29)), (0.25, (0.55, 0.55, 0.54)), (0.75, (0.58, 0.575, 0.56)), (0.90, (0.40, 0.395, 0.38)),
                                   (1.0, (0.30, 0.30, 0.29))])
        stripe = ramp((-350, -600), [(0.0, (0.07, 0.07, 0.07)), (0.30, (0.045, 0.045, 0.045)), (1.0, (0.035, 0.035, 0.035))])
        white = (0.60, 0.595, 0.58)
    else:
        agouti = ramp((-350, -100), [(0.0, (0.12, 0.12, 0.12)), (1.0, (0.22, 0.22, 0.215))])
        pale = ramp((-350, -350), [(0.0, (0.36, 0.36, 0.35)), (1.0, (0.48, 0.48, 0.47))])
        stripe = ramp((-350, -600), [(0.0, (0.07, 0.07, 0.07)), (1.0, (0.045, 0.045, 0.045))])
        white = (0.46, 0.455, 0.445)
    # per-strand binary masks: stripe if G > Random, white if R > Random2
    r2a = N(nt, "ShaderNodeMath", (-200, -800))
    r2a.operation = "MULTIPLY_ADD"
    L(nt, info.outputs["Random"], r2a.inputs[0])
    r2a.inputs[1].default_value = 13.37
    r2a.inputs[2].default_value = 0.21
    r2 = N(nt, "ShaderNodeMath", (-50, -800))
    r2.operation = "FRACT"
    L(nt, r2a.outputs[0], r2.inputs[0])
    sb = N(nt, "ShaderNodeMath", (-50, -650))
    sb.operation = "GREATER_THAN"
    L(nt, sc.outputs["Green"], sb.inputs[0])
    L(nt, info.outputs["Random"], sb.inputs[1])
    wbn = N(nt, "ShaderNodeMath", (-50, -950))
    wbn.operation = "GREATER_THAN"
    L(nt, sc.outputs["Red"], wbn.inputs[0])
    L(nt, r2.outputs[0], wbn.inputs[1])
    c = mix_rgb(nt, sc.outputs["Blue"], agouti, pale, (0, -150))
    c = mix_rgb(nt, sb.outputs[0], c, stripe, (200, -150))
    c = mix_rgb(nt, wbn.outputs[0], c, white, (400, -150))
    jit = N(nt, "ShaderNodeMapRange", (400, -450))
    L(nt, info.outputs["Random"], jit.inputs["Value"])
    jit.inputs["To Min"].default_value = 0.88
    jit.inputs["To Max"].default_value = 1.08
    # every hair (white included) is a little darker at the root
    rootd = N(nt, "ShaderNodeMapRange", (400, -650))
    L(nt, info.outputs["Intercept"], rootd.inputs["Value"])
    rootd.inputs["From Max"].default_value = 0.35
    rootd.inputs["To Min"].default_value = 0.62
    rootd.inputs["To Max"].default_value = 1.0
    jr = N(nt, "ShaderNodeMath", (550, -550))
    jr.operation = "MULTIPLY"
    L(nt, jit.outputs["Result"], jr.inputs[0])
    L(nt, rootd.outputs["Result"], jr.inputs[1])
    mul = N(nt, "ShaderNodeVectorMath", (650, -250))
    mul.operation = "SCALE"
    L(nt, c, mul.inputs[0])
    L(nt, jr.outputs[0], mul.inputs["Scale"])
    L(nt, mul.outputs["Vector"], hb.inputs["Color"])
    # round 4: the achromatic R-lobe sheen added a near-constant veil to
    # every hair and collapsed the stripe/ground contrast (measured on the
    # CloseFront forehead: 2.5:1 linear with keratin's IOR 1.55 and coat
    # 0.10). An ARTISTIC fibre IOR of 1.2 (physically ~1.55) with rougher
    # lobes and no coat keeps the whites bright and gives ~3.8:1. Recorded
    # as a deliberate deviation in the README.
    hb.inputs["Roughness"].default_value = 0.38 if not under else 0.45
    hb.inputs["Radial Roughness"].default_value = 0.50
    hb.inputs["Coat"].default_value = 0.0
    hb.inputs["IOR"].default_value = 1.20
    hb.inputs["Offset"].default_value = math.radians(2.5)
    hb.inputs["Random Roughness"].default_value = 0.2
    L(nt, hb.outputs["BSDF"], out.inputs["Surface"])
    return m


def whisker_material():
    """White, slightly translucent vibrissae: low melanin with no red cast
    (round 1's 0.55 root melanin with redness 0.2 read as orange stubble)."""
    m, nt = new_mat("M_CatBaseV6_Vibrissa")
    out = N(nt, "ShaderNodeOutputMaterial", (600, 0))
    hb = N(nt, "ShaderNodeBsdfHairPrincipled", (300, 0))
    hb.parametrization = "MELANIN"
    hb.model = "CHIANG"
    info = N(nt, "ShaderNodeHairInfo", (-300, 0))
    mr = N(nt, "ShaderNodeMapRange", (0, 0))
    L(nt, info.outputs["Intercept"], mr.inputs["Value"])
    mr.inputs["From Max"].default_value = 0.25
    mr.inputs["To Min"].default_value = 0.06  # round 4: whiter roots (was 0.10)
    mr.inputs["To Max"].default_value = 0.02
    # round 3: a few dark whiskers in the lower rows (per-curve vib_dark)
    at = N(nt, "ShaderNodeAttribute", (-300, -250))
    at.attribute_name = "vib_dark"
    mel = N(nt, "ShaderNodeMix", (200, -100))
    mel.data_type = "FLOAT"
    L(nt, at.outputs["Fac"], mel.inputs["Factor"])
    L(nt, mr.outputs["Result"], mel.inputs[2])
    mel.inputs[3].default_value = 0.92
    L(nt, mel.outputs[0], hb.inputs["Melanin"])
    hb.inputs["Melanin Redness"].default_value = 0.05
    hb.inputs["Roughness"].default_value = 0.2
    hb.inputs["Radial Roughness"].default_value = 0.3
    hb.inputs["Coat"].default_value = 0.0
    hb.inputs["IOR"].default_value = 1.55
    L(nt, hb.outputs["BSDF"], out.inputs["Surface"])
    return m


def eye_materials():
    mats = {}
    # sclera: neutral, with a brownish pigmented conjunctival band near the limbus
    m, nt = new_mat("M_CatBaseV6_Sclera")
    out = N(nt, "ShaderNodeOutputMaterial", (600, 0))
    bs = N(nt, "ShaderNodeBsdfPrincipled", (300, 0))
    tc = N(nt, "ShaderNodeTexCoord", (-500, 0))
    sep = N(nt, "ShaderNodeSeparateXYZ", (-300, 0))
    L(nt, tc.outputs["Object"], sep.inputs["Vector"])
    band = N(nt, "ShaderNodeMapRange", (-100, 0))
    L(nt, sep.outputs["X"], band.inputs["Value"])
    band.inputs["From Min"].default_value = 0.0105
    band.inputs["From Max"].default_value = 0.0150
    c = mix_rgb(nt, band.outputs["Result"], (0.46, 0.42, 0.38), (0.16, 0.11, 0.09), (100, 0))
    L(nt, c, bs.inputs["Base Color"])
    bs.inputs["Roughness"].default_value = 0.3
    bs.inputs["Subsurface Weight"].default_value = 0.1
    bs.inputs["Subsurface Scale"].default_value = 0.001
    L(nt, bs.outputs["BSDF"], out.inputs["Surface"])
    mats["sclera"] = m
    # iris: vertex-coloured stroma on the displaced iris mesh; the pupil is an
    # absorbing black vesica slit (no reflection of its own: the cornea
    # supplies the only specular over it)
    m, nt = new_mat("M_CatBaseV6_Iris")
    out = N(nt, "ShaderNodeOutputMaterial", (1400, 0))
    bs = N(nt, "ShaderNodeBsdfPrincipled", (900, 150))
    col = N(nt, "ShaderNodeVertexColor", (500, 200))
    col.layer_name = "iris_col"
    L(nt, col.outputs["Color"], bs.inputs["Base Color"])
    # round 3: the iris sits inside the aqueous (IOR contrast ~0.05), so it has
    # essentially no specular of its own; round 2's 0.2 gave the wavy
    # "plastic wrap" highlight on the displaced fibres
    bs.inputs["Roughness"].default_value = 0.7
    bs.inputs["Specular IOR Level"].default_value = 0.0
    uv = N(nt, "ShaderNodeUVMap", (-700, -200))
    uv.uv_map = "IrisXY"
    sep = N(nt, "ShaderNodeSeparateXYZ", (-500, -200))
    L(nt, uv.outputs["UV"], sep.inputs["Vector"])
    # half-width(Y) = w0 * (1 - (Y/h)^2)^0.9 in iris-radius units
    yy = N(nt, "ShaderNodeMath", (-300, -300))
    yy.operation = "DIVIDE"
    L(nt, sep.outputs["Y"], yy.inputs[0])
    yy.inputs[1].default_value = PUPIL_H
    y2 = N(nt, "ShaderNodeMath", (-150, -300))
    y2.operation = "MULTIPLY"
    L(nt, yy.outputs[0], y2.inputs[0])
    L(nt, yy.outputs[0], y2.inputs[1])
    om = N(nt, "ShaderNodeMath", (0, -300))
    om.operation = "SUBTRACT"
    om.use_clamp = True
    om.inputs[0].default_value = 1.0
    L(nt, y2.outputs[0], om.inputs[1])
    pw = N(nt, "ShaderNodeMath", (150, -300))
    pw.operation = "POWER"
    L(nt, om.outputs[0], pw.inputs[0])
    pw.inputs[1].default_value = 1.15  # pointed vesica ends
    hw = N(nt, "ShaderNodeMath", (300, -300))
    hw.operation = "MULTIPLY"
    L(nt, pw.outputs[0], hw.inputs[0])
    hw.inputs[1].default_value = PUPIL_W0
    ax = N(nt, "ShaderNodeMath", (150, -150))
    ax.operation = "ABSOLUTE"
    L(nt, sep.outputs["X"], ax.inputs[0])
    dd = N(nt, "ShaderNodeMath", (450, -200))
    dd.operation = "SUBTRACT"
    L(nt, ax.outputs[0], dd.inputs[0])
    L(nt, hw.outputs[0], dd.inputs[1])
    pm = N(nt, "ShaderNodeMapRange", (650, -200))
    L(nt, dd.outputs[0], pm.inputs["Value"])
    pm.inputs["From Min"].default_value = -0.011
    pm.inputs["From Max"].default_value = 0.011
    pm.inputs["To Min"].default_value = 1.0
    pm.inputs["To Max"].default_value = 0.0
    black = N(nt, "ShaderNodeEmission", (900, -200))
    black.inputs["Strength"].default_value = 0.0
    black.inputs["Color"].default_value = (0, 0, 0, 1)
    mx = N(nt, "ShaderNodeMixShader", (1150, 0))
    L(nt, pm.outputs["Result"], mx.inputs["Fac"])
    L(nt, bs.outputs["BSDF"], mx.inputs[1])
    L(nt, black.outputs["Emission"], mx.inputs[2])
    L(nt, mx.outputs["Shader"], out.inputs["Surface"])
    mats["iris"] = m
    # cornea + aqueous: clear, transparent to shadow rays
    m, nt = new_mat("M_CatBaseV6_Cornea")
    out = N(nt, "ShaderNodeOutputMaterial", (600, 0))
    gl = N(nt, "ShaderNodeBsdfGlass", (100, 100))
    gl.inputs["IOR"].default_value = 1.376
    gl.inputs["Roughness"].default_value = 0.0
    tr = N(nt, "ShaderNodeBsdfTransparent", (100, -100))
    lp = N(nt, "ShaderNodeLightPath", (-200, 200))
    mx = N(nt, "ShaderNodeMixShader", (350, 0))
    L(nt, lp.outputs["Is Shadow Ray"], mx.inputs["Fac"])
    L(nt, gl.outputs["BSDF"], mx.inputs[1])
    L(nt, tr.outputs["BSDF"], mx.inputs[2])
    L(nt, mx.outputs["Shader"], out.inputs["Surface"])
    mats["cornea"] = m
    # tear meniscus along the lower lid only
    m, nt = new_mat("M_CatBaseV6_Tear")
    out = N(nt, "ShaderNodeOutputMaterial", (600, 0))
    bs = N(nt, "ShaderNodeBsdfPrincipled", (300, 0))
    bs.inputs["Base Color"].default_value = (0.8, 0.8, 0.8, 1)
    bs.inputs["Roughness"].default_value = 0.05
    bs.inputs["Transmission Weight"].default_value = 1.0
    bs.inputs["IOR"].default_value = 1.336
    L(nt, bs.outputs["BSDF"], out.inputs["Surface"])
    mats["tear"] = m
    # caruncle / nictitans edge: dark, wet
    m, nt = new_mat("M_CatBaseV6_Caruncle")
    out = N(nt, "ShaderNodeOutputMaterial", (600, 0))
    bs = N(nt, "ShaderNodeBsdfPrincipled", (300, 0))
    bs.inputs["Base Color"].default_value = (0.10, 0.055, 0.05, 1)
    bs.inputs["Roughness"].default_value = 0.12
    bs.inputs["Subsurface Weight"].default_value = 0.15
    bs.inputs["Subsurface Scale"].default_value = 0.0008
    L(nt, bs.outputs["BSDF"], out.inputs["Surface"])
    mats["caruncle"] = m
    return mats


# ---------------------------------------------------------------------------
# Eyes
# ---------------------------------------------------------------------------

PUPIL_W0 = 0.058  # slit half-width at the centre, iris radii (~5.8 % of iris width)
# round 3: a vesica whose pointed ends stop ~1 mm short of the lid margins
# (round 2's 0.90 ran under both lids and read as a square-ended bar)
PUPIL_H = 0.66  # slit half-height, iris radii


def world_from_head(p):
    return Vector(np.asarray(p) @ head_R().T) + HEAD_ORIGIN


def iris_arrays(side, rings=110, segs=420, seed=0):
    """Displaced iris (gaze-frame metres: x along the gaze) with vertex colours.

    Slightly concave: the pupillary zone sits 0.9 mm behind the iris root.
    Relief: a collarette ridge at 42 % radius, radial trabecular fibres, crypts
    (pits) in the ciliary zone and circular contraction furrows near the root.
    Colour (linear): blue stroma with pale fibres, darker furrows and crypts,
    a greyer-green pupillary zone, a pale collarette and a dark limbal ring."""
    rng = np.random.default_rng(RNG_SEED + 7 + seed)
    cd = cornea_dims()
    ri = cd["r_i"]
    rho = np.linspace(0.0, 1.0, rings)
    th = np.linspace(0.0, 2 * math.pi, segs, endpoint=False)
    R_, T_ = np.meshgrid(rho, th, indexing="ij")
    # angular fibre noise: sum of sinusoids with random phases (seamless)
    fib = np.zeros_like(R_)
    for k in range(14):
        f = rng.integers(40, 170)
        fib += np.sin(f * T_ + rng.random() * 6.28 + 3.0 * np.sin(2.0 * R_ * (1 + k % 3))) / 14.0
    fib2 = np.zeros_like(R_)
    for k in range(8):
        f = rng.integers(8, 30)
        fib2 += np.sin(f * T_ + rng.random() * 6.28 + 1.5 * R_) / 8.0
    # crypts: random pits in the ciliary zone
    crypt = np.zeros_like(R_)
    X, Y = R_ * np.cos(T_), R_ * np.sin(T_)
    for k in range(46):
        r0 = rng.uniform(0.47, 0.86)
        a0 = rng.uniform(0, 2 * math.pi)
        cx, cy = r0 * math.cos(a0), r0 * math.sin(a0)
        sr, sa = rng.uniform(0.02, 0.05), rng.uniform(0.04, 0.10)
        # elongated radially
        dr = (X - cx) * math.cos(a0) + (Y - cy) * math.sin(a0)
        da = -(X - cx) * math.sin(a0) + (Y - cy) * math.cos(a0)
        crypt = np.maximum(crypt, np.exp(-(dr / sa) ** 2 - (da / sr) ** 2))
    coll = np.exp(-((R_ - 0.42 - 0.025 * np.sin(11 * T_ + 1.0) - 0.015 * np.sin(23 * T_ + 2.3)) / 0.05) ** 2)
    furrow = sum(np.exp(-((R_ - rr) / 0.012) ** 2) for rr in (0.80, 0.86, 0.91)) * 0.6
    # round 4: finer multi-frequency stroma (two more crypt scales and a
    # high-frequency fibre octave), a low collarette ridge with no colour ring
    fib3 = np.zeros_like(R_)
    for k in range(10):
        f = rng.integers(170, 420)
        fib3 += np.sin(f * T_ + rng.random() * 6.28 + 5.0 * np.sin(3.0 * R_ * (1 + k % 4))) / 10.0
    crypt2 = np.zeros_like(R_)
    for k in range(140):
        r0 = rng.uniform(0.35, 0.90)
        a0 = rng.uniform(0, 2 * math.pi)
        cx, cy = r0 * math.cos(a0), r0 * math.sin(a0)
        sr, sa = rng.uniform(0.008, 0.018), rng.uniform(0.015, 0.04)
        dr = (X - cx) * math.cos(a0) + (Y - cy) * math.sin(a0)
        da = -(X - cx) * math.sin(a0) + (Y - cy) * math.cos(a0)
        crypt2 = np.maximum(crypt2, np.exp(-(dr / sa) ** 2 - (da / sr) ** 2))
    h = (-1.2 * MM * (1.0 - R_ ** 2) + 0.22 * MM * coll + 0.13 * MM * fib * smoothstep(0.1, 0.4, R_)
         + 0.04 * MM * fib3 * smoothstep(0.15, 0.4, R_) - 0.42 * MM * crypt - 0.18 * MM * crypt2 + 0.08 * MM * furrow)
    # colour (linear). Round 4 (judged round 3: over-saturated cobalt with a
    # procedural radial-streak look and a blurry collarette ring): a greyer,
    # ~35 % less saturated blue matched to Nyaakoto's pale grey-blue eyes,
    # fibre and crypt detail at three scales, darker toward the pupil, a soft
    # dark limbal ring, no pale collarette ring
    base = np.array([0.070, 0.118, 0.175])
    pale = np.array([0.26, 0.33, 0.40])
    dark = np.array([0.012, 0.020, 0.032])
    fibv = np.clip(0.5 + 0.55 * fib + 0.35 * fib3, 0.0, 1.0)
    col = base[None, None] * (1 - fibv[..., None] * 0.45) + pale[None, None] * (fibv[..., None] * 0.45)
    col = col * (0.80 + 0.4 * (0.5 + 0.5 * fib2))[..., None]
    cr = np.clip(0.55 * crypt + 0.45 * crypt2, 0.0, 1.0)
    col = col * (1 - cr[..., None]) + dark * cr[..., None]
    # darker toward the pupil (the pupillary zone), smoothly
    pz = 1.0 - smoothstep(0.18, 0.46, R_)
    col = col * (1.0 - 0.45 * pz)[..., None]
    # pupillary ruff: a thin dark rim that follows the SLIT margin (round 3's
    # circular ruff made the slit bulge at its midpoint)
    Xa, Ya = np.abs(R_ * np.cos(T_)), R_ * np.sin(T_)
    hw_slit = PUPIL_W0 * np.clip(1.0 - (Ya / PUPIL_H) ** 2, 0.0, 1.0) ** 1.15
    d_slit = np.where(np.abs(Ya) < PUPIL_H, Xa - hw_slit, np.hypot(np.maximum(Xa, 0.0), np.abs(Ya) - PUPIL_H))
    ruff = np.exp(-(np.maximum(d_slit, 0.0) / 0.025) ** 2)
    col = col * (1 - 0.55 * ruff[..., None])
    limb = smoothstep(0.84, 0.95, R_)
    col = col * (1 - limb[..., None] * 0.85) + np.array([0.008, 0.012, 0.020]) * (limb[..., None] * 0.85)
    # geometry in the gaze frame: x = along the gaze, y = lateral (*side), z = up
    x = cd["d_i"] + h
    y = R_ * ri * np.cos(T_)
    z = R_ * ri * np.sin(T_)
    P = np.stack([x, y, z], -1).reshape(-1, 3)
    uv = np.stack([np.cos(T_) * R_ * side, np.sin(T_) * R_], -1).reshape(-1, 2)  # + = lateral, up
    C = col.reshape(-1, 3)
    idx = np.arange(rings * segs).reshape(rings, segs)
    quads = []
    for i in range(rings - 1):
        a, b = idx[i], idx[i + 1]
        quads.append(np.stack([a, np.roll(a, -1), np.roll(b, -1), b], -1))
    return P, np.concatenate(quads), uv, C


def build_eyes(coll, mats, parent):
    objs = []
    cd = cornea_dims()
    for s, tag in ((1.0, "L"), (-1.0, "R")):
        c = world_from_head(eye_center(s))
        G = head_R() @ gaze_frame(s)  # world columns: gaze, lateral(+Y), up
        Mb = Matrix(G.tolist()).to_4x4()
        M = Matrix.Translation(c) @ Mb
        # sclera globe, opened at the limbus
        bpy.ops.mesh.primitive_uv_sphere_add(segments=128, ring_count=64, radius=A.eye_r)
        g = bpy.context.object
        g.name = f"CatBaseV6_Eye{tag}_Globe"
        g.matrix_world = M @ Matrix.Rotation(math.radians(90), 4, "Y")
        bpy.ops.object.shade_smooth()
        g.data.materials.append(mats["sclera"])
        bm = bmesh.new()
        bm.from_mesh(g.data)
        lim = math.cos(math.radians(49.0))
        axis_local = (g.matrix_world.inverted().to_3x3() @ (Mb.to_3x3() @ Vector((1, 0, 0)))).normalized()
        kill = [f for f in bm.faces if all((vv.co.normalized().dot(axis_local)) > lim for vv in f.verts)]
        bmesh.ops.delete(bm, geom=kill, context="FACES")
        bm.to_mesh(g.data)
        bm.free()
        # object coords for the sclera shader: x along the gaze (m)
        g.matrix_world = M
        g.data.transform(Matrix.Rotation(math.radians(90), 4, "Y"))
        # displaced iris (gaze frame) with the slit pupil in its UVs
        P, quads, uv, C = iris_arrays(s, seed=int(s > 0))
        me = bpy.data.meshes.new(f"CatBaseV6_Eye{tag}_Iris")
        me.from_pydata(P.tolist(), [], [tuple(q) for q in quads])
        me.update()
        ul = me.uv_layers.new(name="IrisXY")
        loop_v = np.empty(len(me.loops), np.int32)
        me.loops.foreach_get("vertex_index", loop_v)
        ul.data.foreach_set("uv", uv[loop_v].astype(np.float32).ravel())
        ca = me.color_attributes.new("iris_col", "FLOAT_COLOR", "POINT")
        ca.data.foreach_set("color", np.concatenate([C, np.ones((len(C), 1))], 1).astype(np.float32).ravel())
        for p in me.polygons:
            p.use_smooth = True
        ir = link(bpy.data.objects.new(me.name, me), coll)
        ir.matrix_world = M
        me.materials.append(mats["iris"])
        # cornea + aqueous: spherical cap from the limbus ring, a short wall
        # back past the iris and a back disc, so the iris sits in the medium
        Rc, rl = cd["Rc"], cd["rl"]
        x_l = cd["d_i"] + 0.3 * MM
        x_b = cd["d_i"] - 1.8 * MM
        apex_x = cd["apex"]
        bm = bmesh.new()
        rings, segs = 32, 128
        rows = []
        for i in range(1, rings + 1):
            t = i / rings
            rr = rl * t
            xx = apex_x - (Rc - math.sqrt(max(Rc ** 2 - rr ** 2, 0)))
            rows.append([bm.verts.new((xx, rr * math.cos(2 * math.pi * j / segs), rr * math.sin(2 * math.pi * j / segs))) for j in range(segs)])
        rows.append([bm.verts.new((x_b, rl * math.cos(2 * math.pi * j / segs), rl * math.sin(2 * math.pi * j / segs))) for j in range(segs)])
        for i in range(len(rows) - 1):
            for j in range(segs):
                j2 = (j + 1) % segs
                bm.faces.new((rows[i][j], rows[i][j2], rows[i + 1][j2], rows[i + 1][j]))
        apex = bm.verts.new((apex_x, 0, 0))
        for j in range(segs):
            bm.faces.new((apex, rows[0][j], rows[0][(j + 1) % segs]))
        bctr = bm.verts.new((x_b, 0, 0))
        for j in range(segs):
            bm.faces.new((bctr, rows[-1][(j + 1) % segs], rows[-1][j]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new(f"CatBaseV6_Eye{tag}_Cornea")
        bm.to_mesh(me)
        bm.free()
        co = link(bpy.data.objects.new(me.name, me), coll)
        co.matrix_world = M
        for p in me.polygons:
            p.use_smooth = True
        me.materials.append(mats["cornea"])
        # tear meniscus: lower lid only, thin, half buried in the lid-globe gap
        pts = fissure_outline_points(s, 200, lower_only=True)
        tube = tube_mesh(f"CatBaseV6_Eye{tag}_TearMeniscus", pts, 0.32 * MM, closed=False)
        tob = link(bpy.data.objects.new(tube.name, tube), coll)
        tob.location = HEAD_ORIGIN
        tube.materials.append(mats["tear"])
        # caruncle (wet lacrimal corner) at the medial canthus
        allp = fissure_outline_points(s, 200)
        med = allp[np.argmin(allp[:, 1] * s)]
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=1.0)
        cr = bpy.context.object
        cr.name = f"CatBaseV6_Eye{tag}_Caruncle"
        cr.location = Vector(med) + HEAD_ORIGIN
        cr.scale = (1.2 * MM, 1.0 * MM, 1.6 * MM)
        bpy.ops.object.shade_smooth()
        cr.data.materials.append(mats["caruncle"])
        for o in (g, cr):
            for uc in list(o.users_collection):
                uc.objects.unlink(o)
            coll.objects.link(o)
        objs += [g, ir, co, tob, cr]
    for o in objs:
        mw = o.matrix_world.copy()
        o.parent = parent
        o.matrix_world = mw
    return objs


def fissure_outline_points(side, n, lower_only=False):
    """World-local points (m) on the lid margin: the almond aperture projected
    onto the cornea/globe surface just inside the lid gap."""
    Gf = gaze_frame(side)
    t = math.radians(A.fissure_tilt)
    hw = 0.5 * A.fissure_w
    cd = cornea_dims()
    cc_off = cd["apex"] - cd["Rc"]
    out = []
    us = np.linspace(-hw * 0.985, hw * 0.985, n // 2)
    up, lo = fissure_curves(us)
    if lower_only:
        seq = list(zip(us[: int(0.8 * len(us))], lo[: int(0.8 * len(us))]))
    else:
        seq = list(zip(us, up)) + list(zip(us[::-1], lo[::-1]))
    for uu, ww in seq:
        u = uu * math.cos(t) - ww * math.sin(t)
        w = uu * math.sin(t) + ww * math.cos(t)
        r2 = u * u + w * w
        xg = math.sqrt(max((A.eye_r + 0.25 * MM) ** 2 - r2, 1e-8))
        xc = cc_off + math.sqrt(max((cd["Rc"] + 0.25 * MM) ** 2 - r2, 1e-8))
        local = np.array([max(xg, xc), u * side, w])
        out.append(eye_center(side) + Gf @ local)
    return np.array(out) @ head_R().T


def lid_margin_material():
    """Moist, pigmented lid margin: near-black with a soft wet sheen."""
    m, nt = new_mat("M_CatBaseV6_LidMargin")
    out = N(nt, "ShaderNodeOutputMaterial", (400, 0))
    bs = N(nt, "ShaderNodeBsdfPrincipled", (100, 0))
    bs.inputs["Base Color"].default_value = (0.014, 0.011, 0.010, 1)
    bs.inputs["Roughness"].default_value = 0.22
    bs.inputs["Specular IOR Level"].default_value = 0.55
    bs.inputs["Coat Weight"].default_value = 0.55
    bs.inputs["Coat Roughness"].default_value = 0.05
    L(nt, bs.outputs["BSDF"], out.inputs["Surface"])
    return m


def build_lid_margins(coll, parent, n=240):
    """Round 3: a smooth tri-strip-like lid margin swept along the almond
    fissure (an elliptical tube, ~1.1 mm radial x 0.8 mm, tapering into the
    canthi), sitting on the carved lid edge. It replaces the jagged,
    notched fur-hole edge of the level-set skin that round 2 showed as the
    lid rim, and it gives the lid visible thickness above the cornea."""
    mat = lid_margin_material()
    sdf = head_sdf_sampler()
    objs = []
    for s, tag in ((1.0, "L"), (-1.0, "R")):
        P = fissure_outline_points(s, n)
        c = eye_center(s) @ head_R().T
        m = len(P)
        cen = P.mean(0)
        bm = bmesh.new()
        rings = []
        segs = 12
        # height of the carved lid wall above the eye surface at each margin
        # point: march outward until both the lid shell and the bulk flesh
        # are left behind (capped at 6 mm)
        R = np.array(P)
        gw = head_R() @ gaze_frame(s)[:, 0]  # the carved wall runs along the gaze
        rr = np.tile(gw, (m, 1))
        wall = np.full(m, 6.0 * MM)
        found = np.zeros(m, bool)
        for step in np.arange(0.2, 6.01, 0.2) * MM:
            Q = R + rr * step
            inside = sd_lid_shell(Q @ head_R(), s) < 0
            if sdf is not None:
                inside |= sdf(Q) < 0
            newly = (~inside) & (~found)
            wall[newly] = step
            found |= ~inside
        wall = np.convolve(np.r_[wall[-6:], wall, wall[:6]], np.ones(13) / 13, mode="same")[6:-6]
        for i in range(m):
            p = P[i]
            t = P[(i + 1) % m] - P[i - 1]
            t /= np.linalg.norm(t)
            r = gw - (gw @ t) * t
            r /= np.linalg.norm(r)
            nrm = np.cross(t, r)
            if nrm @ (p - cen) < 0:
                nrm = -nrm  # in-plane direction pointing away from the pupil (into the lid)
            # taper into the canthi (the ends of each arc)
            u = (i % (m // 2)) / (m // 2)
            taper = 0.45 + 0.55 * math.sin(math.pi * u) ** 0.5
            h = float(np.clip(wall[i], 0.6 * MM, 3.0 * MM))
            # round 4 (judged round 3: a 0.5 mm black wire ring floating off
            # the globe): a flat, wide rounded margin ~2 mm across seen from
            # the front, seated down on the lid edge so its inner edge rests
            # on the cornea and its outer edge overlaps the pigmented lid skin
            a, b = 0.50 * MM * (0.6 + 0.4 * taper), 1.15 * MM * (0.6 + 0.4 * taper)
            ctr = p + r * max(h - 0.85 * MM, 0.25 * MM) + nrm * 0.55 * MM
            ring = []
            for j in range(segs):
                th = 2 * math.pi * j / segs
                ring.append(bm.verts.new(ctr + r * a * math.cos(th) + nrm * b * math.sin(th)))
            rings.append(ring)
        for i in range(m):
            r0, r1 = rings[i], rings[(i + 1) % m]
            for j in range(segs):
                bm.faces.new((r0[j], r0[(j + 1) % segs], r1[(j + 1) % segs], r1[j]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new(f"CatBaseV6_Eye{tag}_LidMargin")
        bm.to_mesh(me)
        bm.free()
        for p_ in me.polygons:
            p_.use_smooth = True
        me.materials.append(mat)
        ob = link(bpy.data.objects.new(me.name, me), coll)
        # set the world matrix directly: .location is not reflected in
        # matrix_world until a depsgraph update, so copying it here would
        # parent the margin at the world origin
        mw = Matrix.Translation(HEAD_ORIGIN)
        ob.parent = parent
        ob.matrix_world = mw
        objs.append(ob)
    return objs


def tube_mesh(name, pts, radius, closed=True, segs=8):
    bm = bmesh.new()
    n = len(pts)
    rings = []
    for i in range(n):
        p = pts[i]
        t = pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)] if not closed else pts[(i + 1) % n] - pts[i - 1]
        t /= np.linalg.norm(t)
        a = np.cross(t, [0, 0, 1.0])
        if np.linalg.norm(a) < 1e-6:
            a = np.cross(t, [0, 1.0, 0])
        a /= np.linalg.norm(a)
        b = np.cross(t, a)
        taper = 1.0 if closed else min(1.0, 4.0 * min(i, n - 1 - i) / max(n - 1, 1) + 0.15)
        rings.append([bm.verts.new(p + radius * taper * (math.cos(2 * math.pi * k / segs) * a + math.sin(2 * math.pi * k / segs) * b)) for k in range(segs)])
    for i in range(n if closed else n - 1):
        r0, r1 = rings[i], rings[(i + 1) % n]
        for k in range(segs):
            bm.faces.new((r0[k], r0[(k + 1) % segs], r1[(k + 1) % segs], r1[k]))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return me


# ---------------------------------------------------------------------------
# Groom
# ---------------------------------------------------------------------------

def evaluated_surface(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    me.calc_loop_triangles()
    n = len(me.vertices)
    co = np.empty(n * 3, np.float32)
    me.vertices.foreach_get("co", co)
    nr = np.empty(n * 3, np.float32)
    me.vertices.foreach_get("normal", nr)
    nt = len(me.loop_triangles)
    tv = np.empty(nt * 3, np.int32)
    me.loop_triangles.foreach_get("vertices", tv)
    tl = np.empty(nt * 3, np.int32)
    me.loop_triangles.foreach_get("loops", tl)
    uvs = np.empty(len(me.loops) * 2, np.float32)
    me.uv_layers["UVMap"].data.foreach_get("uv", uvs)
    attrs = {k: attr_array(me, k) for k in EAR_ATTRS}
    res = dict(co=co.reshape(-1, 3).astype(np.float64), nr=nr.reshape(-1, 3).astype(np.float64),
               tv=tv.reshape(-1, 3), tl=tl.reshape(-1, 3), uv=uvs.reshape(-1, 2).astype(np.float64), attrs=attrs)
    ev.to_mesh_clear()
    return res


def sample_roots(S, count, weight_fn, rng):
    P = S["co"][S["tv"]]
    area = 0.5 * np.linalg.norm(np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]), axis=1)
    cen = P.mean(1)
    ncen = S["nr"][S["tv"]].mean(1)
    ncen /= np.linalg.norm(ncen, axis=1, keepdims=True) + 1e-12
    exc = {k: S["attrs"][k][S["tv"]].mean(1) for k in EAR_ATTRS}
    w = np.maximum(area * weight_fn(cen, ncen, exc), 0)
    tri = rng.choice(len(w), size=count, p=w / w.sum())
    r1 = np.sqrt(rng.random(count))
    r2 = rng.random(count)
    b = np.stack([1 - r1, r1 * (1 - r2), r1 * r2], 1)
    pos = np.einsum("ij,ijk->ik", b, P[tri])
    nrm = np.einsum("ij,ijk->ik", b, S["nr"][S["tv"][tri]])
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
    uv = np.einsum("ij,ijk->ik", b, S["uv"][S["tl"][tri]])
    ex = {k: np.einsum("ij,ij->i", b, S["attrs"][k][S["tv"][tri]]) for k in EAR_ATTRS}
    return pos, nrm, uv, ex


def make_curves(name, strands, radius_root, radius_tip, coll, uv=None, surface=None, radii=None):
    npts = strands.shape[1]
    hc = bpy.data.hair_curves.new(name)
    hc.add_curves([npts] * len(strands))
    hc.attributes["position"].data.foreach_set("vector", strands.astype(np.float32).ravel())
    if radii is None:
        radii = np.linspace(radius_root, radius_tip, npts)[None, :].repeat(len(strands), 0)
    if "radius" not in hc.attributes:
        hc.attributes.new("radius", "FLOAT", "POINT")
    hc.attributes["radius"].data.foreach_set("value", radii.astype(np.float32).ravel())
    if uv is not None:
        a = hc.attributes.new("surface_uv_coordinate", "FLOAT2", "CURVE")
        a.data.foreach_set("vector", uv.astype(np.float32).ravel())
    ob = link(bpy.data.objects.new(name, hc), coll)
    if surface is not None:
        hc.surface = surface
        hc.surface_uv_map = "UVMap"
    return ob


def grow_guides(pos, nrm, ex, npts, rng, length_scale=None, lift_add=None, lay=0.8):
    """Guides that leave the skin at the lift angle and lie down toward the
    tip (lift falls to ~20 % along the strand), follow the flow field, sag
    with gravity in proportion to their length, and carry a slight wave and
    individual sideways bend. Round 3: optional per-strand length scale and
    extra lift (used for the stray guard hairs)."""
    f = coat_fields(pos, nrm, ex)
    tdir = fur_direction(pos, nrm, ex)
    n = len(pos)
    Lg = f["length"] * rng.uniform(0.9, 1.1, n)
    if length_scale is not None:
        Lg = Lg * length_scale
    a0 = np.radians(f["lift"] + (0.0 if lift_add is None else lift_add))
    side = np.cross(nrm, tdir)
    g = np.array([0.0, 0.0, -1.0])
    gt = g[None] - (nrm @ g)[:, None] * nrm
    droop = np.clip((Lg / MM - 6.0) / 30.0, 0.0, 0.55)
    wave_amp = rng.uniform(0.04, 0.12, n)
    freq = rng.uniform(0.6, 1.3, n)
    phase = rng.random(n) * 2 * math.pi
    bend = rng.normal(0.0, 0.07, n)
    strands = np.zeros((n, npts, 3))
    p = pos + nrm * 0.05 * MM
    strands[:, 0] = p
    seg = Lg / (npts - 1)
    for k in range(1, npts):
        sm = (k - 0.5) / (npts - 1)
        a = a0 * (1.0 - lay * sm) + math.radians(1.0)
        d = (tdir * np.cos(a)[:, None] + nrm * np.sin(a)[:, None]
             + side * (bend * sm + wave_amp * np.sin(2 * math.pi * freq * sm + phase))[:, None]
             + gt * (droop * sm * sm)[:, None])
        d /= np.linalg.norm(d, axis=1, keepdims=True)
        p = p + d * seg[:, None]
        strands[:, k] = p
    return strands, f


HEAD_ORIGIN_NP = np.zeros(3)


def load_hair_assets():
    names = ["Interpolate Hair Curves", "Clump Hair Curves", "Frizz Hair Curves", "Trim Hair Curves",
             "Set Hair Curve Profile", "Hair Curves Noise", "Curl Hair Curves", "Shrinkwrap Hair Curves", "Curve Root"]
    missing = [n for n in names if n not in bpy.data.node_groups]
    if missing:
        with bpy.data.libraries.load(str(HAIR_ASSETS), link=False) as (src, dst):
            dst.node_groups = [n for n in missing if n in src.node_groups]


def gn_mod(ob, group, **kw):
    """Add a geometry-nodes modifier and set its inputs by name; where two
    inputs share a name (e.g. Surface object/geometry) the socket type is
    chosen from the value."""
    m = ob.modifiers.new(group, "NODES")
    m.node_group = bpy.data.node_groups[group]
    items = [it for it in m.node_group.interface.items_tree if getattr(it, "in_out", "") == "INPUT"]
    for k, val in kw.items():
        key = k.replace("_", " ")
        cands = [it for it in items if it.name == key and it.socket_type != "NodeSocketGeometry"]
        if isinstance(val, bpy.types.Object):
            cands = [it for it in cands if it.socket_type == "NodeSocketObject"] or cands
        elif isinstance(val, bpy.types.Image):
            cands = [it for it in cands if it.socket_type == "NodeSocketImage"] or cands
        if not cands:
            raise KeyError(f"{group}: no input {key!r}")
        inp = getattr(m.properties.inputs, cands[0].identifier)
        if isinstance(val, tuple) and val and val[0] == "ATTR":
            inp.type = "ATTRIBUTE"
            inp.attribute_name = val[1]
        else:
            inp.value = val
    return m


def length_jitter_group():
    """Per-strand length scale, pinned at the root: each child curve is scaled
    about its root point by a random factor in [Min, Max] (shape preserved)."""
    name = "CatBaseV6 Length Jitter"
    if name in bpy.data.node_groups:
        return bpy.data.node_groups[name]
    ng = bpy.data.node_groups.new(name, "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    s_min = ng.interface.new_socket("Min", in_out="INPUT", socket_type="NodeSocketFloat")
    s_min.default_value = 0.7
    s_max = ng.interface.new_socket("Max", in_out="INPUT", socket_type="NodeSocketFloat")
    s_max.default_value = 1.3
    ng.interface.new_socket("Seed", in_out="INPUT", socket_type="NodeSocketInt")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    nd = ng.nodes
    gi = nd.new("NodeGroupInput")
    go = nd.new("NodeGroupOutput")
    root = nd.new("GeometryNodeGroup")
    root.node_tree = bpy.data.node_groups["Curve Root"]
    cop = nd.new("GeometryNodeCurveOfPoint")
    rnd = nd.new("FunctionNodeRandomValue")
    rnd.data_type = "FLOAT"
    pos = nd.new("GeometryNodeInputPosition")
    sub = nd.new("ShaderNodeVectorMath")
    sub.operation = "SUBTRACT"
    scl = nd.new("ShaderNodeVectorMath")
    scl.operation = "SCALE"
    add = nd.new("ShaderNodeVectorMath")
    add.operation = "ADD"
    sp = nd.new("GeometryNodeSetPosition")
    lk = ng.links.new
    lk(gi.outputs["Min"], rnd.inputs["Min"])
    lk(gi.outputs["Max"], rnd.inputs["Max"])
    lk(gi.outputs["Seed"], rnd.inputs["Seed"])
    lk(cop.outputs["Curve Index"], rnd.inputs["ID"])
    lk(pos.outputs["Position"], sub.inputs[0])
    lk(root.outputs["Root Position"], sub.inputs[1])
    lk(sub.outputs["Vector"], scl.inputs[0])
    lk(rnd.outputs["Value"], scl.inputs["Scale"])
    lk(root.outputs["Root Position"], add.inputs[0])
    lk(scl.outputs["Vector"], add.inputs[1])
    lk(gi.outputs["Geometry"], sp.inputs["Geometry"])
    lk(add.outputs["Vector"], sp.inputs["Position"])
    lk(sp.outputs["Geometry"], go.inputs["Geometry"])
    return ng


def build_groom(coll, skin, images, n_guides):
    rng = np.random.default_rng(RNG_SEED)
    S = evaluated_surface(skin)
    log("groom surface tris", len(S["tv"]))

    def wfn(c, n, ex):
        f = coat_fields(c, n, ex)
        return f["density"] * np.maximum(f["excl"], 0.05) / np.maximum(f["length"], 2.5 * MM)

    pos, nrm, uv, ex = sample_roots(S, n_guides, wfn, rng)
    strands, f = grow_guides(pos, nrm, ex, 8, rng)
    load_hair_assets()
    length_jitter_group()
    layers = []
    cull = eye_cull_group()
    # round 3: two clump levels on the guard coat (3.0 mm clumps at factor
    # 0.78, then 1.2 mm sub-clumps at 0.42); round 2's single 1.8 mm / 0.42
    # clump did not register and the coat read as flocked velour
    specs = [
        ("CatBaseV6_Fur_Guard", False, dict(density=4.6e6, trim=1.0, noise=0.16 * MM, nscale=160.0, frizz=0.07 * MM,
                                            clumps=((0.78, 3.0 * MM, 0.45), (0.42, 1.2 * MM, 0.35)), r0=0.068 * MM, seed=3)),
        ("CatBaseV6_Fur_Under", True, dict(density=6.0e6, trim=0.55, noise=0.35 * MM, nscale=520.0, frizz=0.18 * MM,
                                           clumps=((0.30, 2.0 * MM, 0.3),), r0=0.032 * MM, seed=7)),
    ]
    for name, under, sp in specs:
        ob = make_curves(name, strands, sp["r0"], sp["r0"] * 0.25, coll, uv=uv, surface=skin)
        ob.parent = skin
        ob.data.materials.append(hair_material(f"M_{name}", images, under))
        gn_mod(ob, "Interpolate Hair Curves", Follow_Surface_Normal=True, Part_by_Mesh_Islands=True, Density=sp["density"],
               Density_Mask=("ATTR", "fur_density"), Mask_Texture=images["furmask"], Interpolation_Guides=4,
               Viewport_Amount=0.05, Seed=sp["seed"])
        gn_mod(ob, "CatBaseV6 Length Jitter", Min=0.7, Max=1.3, Seed=sp["seed"] + 20)
        if sp["trim"] < 1.0:
            gn_mod(ob, "Trim Hair Curves", Scale_Uniform=False, Replace_Length=False, Length_Factor=sp["trim"], Random_Offset=0.0, Pin_at_Parameter=0.0, Seed=13)
        for ci, (cf, cd_, csh) in enumerate(sp["clumps"]):
            gn_mod(ob, "Clump Hair Curves", Factor=cf, Shape=csh, Tip_Spread=0.0, Existing_Guide_Map=False,
                   Guide_Distance=cd_, Guide_Mask=1.0, Preserve_Length=True, Seed=11 + 17 * ci)
        gn_mod(ob, "Hair Curves Noise", Factor=1.0, Distance=sp["noise"], Shape=0.5, Scale=sp["nscale"], Scale_along_Curve=1.0,
               Offset_per_Curve=1.0, Seed=5 if under else 9, Preserve_Length=True)
        gn_mod(ob, "Frizz Hair Curves", Factor=1.0, Distance=sp["frizz"], Shape=0.7, Seed=15 if under else 19, Preserve_Length=True)
        gn_mod(ob, "Shrinkwrap Hair Curves", Surface=skin, Factor=1.0, Offset_Distance=0.12 * MM, Smoothing_Steps=2, Lock_Roots=True)
        gn_mod(ob, "Set Hair Curve Profile", Replace_Radius=True, Radius=sp["r0"], Shape=-0.4, Factor_Min=0.0, Factor_Max=1.0)
        m_ = ob.modifiers.new("CatBaseV6 Eye Cull", "NODES")
        m_.node_group = cull
        layers.append(ob)
    # stray guard hairs. Round 4 (judged round 3: a static-electricity halo
    # under the rim light): half as many (16,000), 1.15-1.45x length, and
    # only 2-8 deg of extra lift (total capped at the local lift + 10 deg), so
    # they stay on the flow field and lie close to the coat
    n_stray = 16000
    sp_, sn_, suv, sex = sample_roots(S, n_stray, wfn, rng)
    st, _ = grow_guides(sp_, sn_, sex, 10, rng, length_scale=rng.uniform(1.15, 1.45, n_stray),
                        lift_add=rng.uniform(2.0, 8.0, n_stray), lay=0.75)
    ob = make_curves("CatBaseV6_Fur_Stray", st, 0.075 * MM, 0.012 * MM, coll, uv=suv, surface=skin)
    ob.parent = skin
    ob.data.materials.append(hair_material("M_CatBaseV6_Fur_Stray", images, False))
    m_ = ob.modifiers.new("CatBaseV6 Eye Cull", "NODES")
    m_.node_group = cull
    layers.append(ob)
    guides = make_curves("CatBaseV6_Fur_Guides", strands, 0.1 * MM, 0.05 * MM, coll, uv=uv, surface=skin)
    guides.parent = skin
    guides.hide_render = True
    guides.hide_viewport = True
    return layers, guides


def eye_cull_group():
    """Round 3: delete every strand that passes over the eye opening. The
    test is view-independent: a strand point is 'over the eye' when, in the
    gaze frame of the (mirrored) left eye, it lies inside the palpebral
    ellipse shrunk by ~1 mm and between the iris plane and 12 mm in front of
    the cornea apex. Round 2 claimed no hair crossed the cornea but white
    strands crossed both eyes in the close three-quarter view."""
    name = "CatBaseV6 Eye Cull"
    if name in bpy.data.node_groups:
        return bpy.data.node_groups[name]
    cd = cornea_dims()
    c = eye_center(1.0) @ head_R().T
    G = head_R() @ gaze_frame(1.0)
    g, l, u = G[:, 0], G[:, 1], G[:, 2]
    up0, lo0 = fissure_curves(np.array(0.0))
    a = 0.5 * A.fissure_w - 1.0 * MM
    b = 0.5 * (float(up0) - float(lo0)) - 0.6 * MM
    w0 = 0.5 * (float(up0) + float(lo0))
    tl = math.radians(A.fissure_tilt)
    ng = bpy.data.node_groups.new(name, "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    nd, lk = ng.nodes, ng.links.new
    gi, go = nd.new("NodeGroupInput"), nd.new("NodeGroupOutput")

    def math_(op, a_, b_=None):
        m = nd.new("ShaderNodeMath")
        m.operation = op
        for i, val in enumerate((a_, b_)):
            if val is None:
                continue
            if isinstance(val, (int, float)):
                m.inputs[i].default_value = float(val)
            else:
                lk(val, m.inputs[i])
        return m.outputs[0]

    def dot(vsock, vec):
        m = nd.new("ShaderNodeVectorMath")
        m.operation = "DOT_PRODUCT"
        lk(vsock, m.inputs[0])
        m.inputs[1].default_value = tuple(float(t) for t in vec)
        return m.outputs["Value"]

    pos = nd.new("GeometryNodeInputPosition")
    sep = nd.new("ShaderNodeSeparateXYZ")
    lk(pos.outputs["Position"], sep.inputs["Vector"])
    comb = nd.new("ShaderNodeCombineXYZ")
    lk(sep.outputs["X"], comb.inputs["X"])
    lk(math_("ABSOLUTE", sep.outputs["Y"]), comb.inputs["Y"])
    lk(sep.outputs["Z"], comb.inputs["Z"])
    sub = nd.new("ShaderNodeVectorMath")
    sub.operation = "SUBTRACT"
    lk(comb.outputs["Vector"], sub.inputs[0])
    sub.inputs[1].default_value = tuple(float(t) for t in c)
    d = sub.outputs["Vector"]
    qg, ql, qu = dot(d, g), dot(d, l), dot(d, u)
    uu = math_("ADD", math_("MULTIPLY", ql, math.cos(tl)), math_("MULTIPLY", qu, math.sin(tl)))
    ww = math_("SUBTRACT", math_("MULTIPLY", qu, math.cos(tl)), math_("MULTIPLY", ql, math.sin(tl)))
    e1 = math_("POWER", math_("DIVIDE", uu, a), 2.0)
    e2 = math_("POWER", math_("DIVIDE", math_("SUBTRACT", ww, w0), b), 2.0)
    inside = math_("LESS_THAN", math_("ADD", e1, e2), 1.0)
    front = math_("GREATER_THAN", qg, cd["d_i"] - 1.5 * MM)
    near = math_("LESS_THAN", qg, cd["apex"] + 12.0 * MM)
    bad = math_("MULTIPLY", math_("MULTIPLY", inside, front), near)
    ev = nd.new("GeometryNodeFieldOnDomain")
    ev.data_type = "FLOAT"
    ev.domain = "CURVE"
    lk(bad, ev.inputs[0])
    sel = math_("GREATER_THAN", ev.outputs[0], 1e-4)
    dele = nd.new("GeometryNodeDeleteGeometry")
    dele.domain = "CURVE"
    lk(gi.outputs["Geometry"], dele.inputs["Geometry"])
    lk(sel, dele.inputs["Selection"])
    lk(dele.outputs["Geometry"], go.inputs["Geometry"])
    return ng


def surface_point(S, kd, p_world_local):
    _, idx, _ = kd.find(p_world_local)
    return S["co"][idx], S["nr"][idx]


def build_vibrissae(coll, skin):
    """Round 4 vibrissae (judged round 3: too few and too thin to read at 3 m,
    a parallel bundle from one point, one brown whisker). Mystacial: 12 per
    side in 4 rows of 3 spread over the whole pad. Each fans out at its own
    azimuth (a ~36 deg fan from the rostro-dorsal to the caudo-ventral
    follicles) and elevation (upper rows slightly up, lower rows down), with
    a per-whisker forward-down curvature. Root radius 0.16-0.22 mm tapering
    to a fine tip; 55-85 mm in the upper rows, up to ~105 mm in the long
    middle rows, ~45-60 mm in the lowest row. All white/translucent. Plus 5
    superciliary and 3 genal whiskers per side."""
    rng = np.random.default_rng(RNG_SEED + 1)
    S = evaluated_surface(skin)
    kd = KDTree(len(S["co"]))
    for i, p in enumerate(S["co"]):
        kd.insert(p, i)
    kd.balance()
    Rh = head_R()
    strands, radii, dark = [], [], []
    npts = 24
    fwd_w = np.array([1.0, 0.0, 0.0])
    down_w = np.array([0.0, 0.0, -1.0])

    def add(root_h, d0_w, length, bend_deg, droop_deg, r0, is_dark=0.0, bend_dir=None):
        root, nr = surface_point(S, kd, root_h * MM @ Rh.T)
        d0 = np.asarray(d0_w, float)
        d0 /= np.linalg.norm(d0)
        bd = fwd_w if bend_dir is None else np.asarray(bend_dir, float)
        bd = bd - (bd @ d0) * d0
        if np.linalg.norm(bd) < 1e-6:
            bd = down_w - (down_w @ d0) * d0
        bd /= np.linalg.norm(bd)
        pts = [root - nr * 1.2 * MM]
        p = root.copy()
        seg = length / (npts - 1)
        for k in range(1, npts):
            s_ = k / (npts - 1)
            a = math.radians(bend_deg) * s_
            dd = d0 * math.cos(a) + bd * math.sin(a)
            dd = dd + down_w * math.tan(math.radians(droop_deg)) * s_ * s_
            dd /= np.linalg.norm(dd)
            p = p + dd * seg
            pts.append(p.copy())
        strands.append(pts)
        t = np.linspace(0, 1, npts)
        radii.append(r0 * (1.0 - t) ** 1.25 + 0.012 * MM)
        dark.append(is_dark)

    for i, (s_, row, col, p) in enumerate(mystacial_roots()):
        # lengths: short rostral columns, long caudal ones; middle rows longest
        row_len = ((55.0, 85.0), (62.0, 98.0), (64.0, 106.0), (45.0, 62.0))[row]
        L_ = (row_len[0] + (row_len[1] - row_len[0]) * col / 2.0) * rng.uniform(0.93, 1.07) * MM
        # fan: azimuth from forward grows caudally and ventrally (~36 deg
        # overall), elevation from +6 deg (top row) to -14 deg (bottom row)
        az = math.radians(40.0 + 9.0 * col + 5.0 * row + rng.normal(0.0, 2.5))
        el = math.radians(6.0 - 6.5 * row - 1.5 * col + rng.normal(0.0, 2.0))
        d0 = np.array([math.cos(el) * math.cos(az), s_ * math.cos(el) * math.sin(az), math.sin(el)])
        r0 = (0.16 + 0.03 * col) * MM * rng.uniform(0.95, 1.05)
        bend_dir = np.array([0.6, 0.0, -0.8])
        add(p, d0, L_, rng.uniform(8.0, 20.0), rng.uniform(1.0, 6.0), r0, 0.0, bend_dir=bend_dir)
    for s_ in (1.0, -1.0):
        for k in range(5):
            # superciliary: above the medial half of the upper lid
            root = np.array([88.0 - 2.2 * k, (25.0 + 4.0 * k) * s_, 45.0 + 1.3 * k])
            d0 = np.array([0.50 + rng.normal(0, 0.05), (0.50 + 0.1 * k) * s_, 0.72])
            add(root, d0, rng.uniform(46.0, 70.0) * MM, rng.uniform(6.0, 14.0), 2.0, 0.12 * MM,
                bend_dir=np.array([-0.3, 0.6 * s_, -0.2]))
        for k in range(3):
            # genal: on the cheek behind and below the lateral canthus
            root = np.array([46.0 - 6.0 * k, 84.0 * s_, -4.0 - 4.5 * k])
            d0 = np.array([-0.35 + 0.05 * k, 1.0 * s_, 0.25 - 0.08 * k])
            add(root, d0, rng.uniform(50.0, 66.0) * MM, 8.0, 2.0, 0.13 * MM)
    P = np.array(strands)
    hc = bpy.data.hair_curves.new("CatBaseV6_Vibrissae")
    hc.add_curves([npts] * len(P))
    hc.attributes["position"].data.foreach_set("vector", P.astype(np.float32).ravel())
    if "radius" not in hc.attributes:
        hc.attributes.new("radius", "FLOAT", "POINT")
    hc.attributes["radius"].data.foreach_set("value", np.array(radii).astype(np.float32).ravel())
    da = hc.attributes.new("vib_dark", "FLOAT", "CURVE")
    da.data.foreach_set("value", np.array(dark, np.float32))
    ob = link(bpy.data.objects.new("CatBaseV6_Vibrissae", hc), coll)
    ob.parent = skin
    ob.data.materials.append(whisker_material())
    return ob


def build_inner_ear_furnishings(coll, skin, images):
    """Round 4 ear furnishings (judged round 3: a flat buff/yellow brush pasted
    on the inner face). Clumped tufts of 6-10 white-to-pale-grey hairs,
    10-20 mm long, rooted along the medial margin of the inner face (lower
    two thirds) and on the antitragus at the lateral base. They fan up and
    across the conchal opening: the medial ones rise and lean laterally and
    forward, the antitragal ones rise and lean medially. Direct colouring
    (no melanin, so no ginger or buff cast)."""
    rng = np.random.default_rng(RNG_SEED + 2)
    S = evaluated_surface(skin)

    def wfn(c, n, ex):
        front = ex["is_ear"] * smoothstep(0.2, 0.6, ex["ear_face"])
        med = (1.0 - smoothstep(-0.78, -0.50, ex["ear_u"])) * _bump(ex["ear_t"], 0.08, 0.66)
        anti = smoothstep(0.45, 0.65, ex["ear_u"]) * (1.0 - smoothstep(0.86, 0.96, ex["ear_u"])) * _bump(ex["ear_t"], -0.02, 0.18)
        floor = _bump(ex["ear_t"], 0.04, 0.34) * (1.0 - smoothstep(0.5, 0.8, np.abs(ex["ear_u"])))
        return front * (1.4 * med + 1.0 * anti + 0.8 * floor)

    n_tuft = 1100
    cpos, cnrm, cuv, cex = sample_roots(S, n_tuft, wfn, rng)
    npts = 12
    strands, uvs = [], []
    for i in range(n_tuft):
        s = 1.0 if (cpos[i] @ head_R())[1] > 0 else -1.0
        F = ear_frame(s)
        up = F[:, 2] @ head_R().T
        fwd = F[:, 0] @ head_R().T
        lat = F[:, 1] * s @ head_R().T
        if cex["ear_u"][i] < 0.0:
            # medial margin: rise, lean laterally across the opening and forward
            d = 0.55 * up + 0.55 * fwd + 0.60 * lat + 0.25 * cnrm[i]
            Lt = rng.uniform(12.0, 20.0) * MM
        else:
            # antitragus: rise and lean medially
            d = 0.60 * up + 0.50 * fwd - 0.50 * lat + 0.25 * cnrm[i]
            Lt = rng.uniform(10.0, 15.0) * MM
        d /= np.linalg.norm(d)
        k = int(rng.integers(6, 11))
        for _ in range(k):
            off = rng.normal(0.0, 0.7 * MM, 3)
            off -= (off @ cnrm[i]) * cnrm[i]
            p = cpos[i] + off - cnrm[i] * 0.2 * MM
            dh = d + rng.normal(0.0, 0.10, 3)
            dh /= np.linalg.norm(dh)
            Lh = Lt * rng.uniform(0.75, 1.1)
            curl = rng.normal(0, 0.06, 3)
            pts = [p.copy()]
            for kk in range(1, npts):
                s_ = kk / (npts - 1)
                dd = dh + curl * s_ + np.array([0, 0, -0.18]) * s_ * s_
                dd /= np.linalg.norm(dd)
                p = p + dd * Lh / (npts - 1)
                pts.append(p.copy())
            strands.append(pts)
            uvs.append(cuv[i])
    strands = np.array(strands)
    uv = np.array(uvs)
    t = np.linspace(0, 1, npts)
    radii = np.repeat(((0.050 * MM) * (1 - t) ** 0.8 + 0.006 * MM)[None], len(strands), 0)
    ob = make_curves("CatBaseV6_Fur_EarFurnishings", strands, 0, 0, coll, uv=uv, surface=skin, radii=radii)
    ob.parent = skin
    m, nt = new_mat("M_CatBaseV6_EarFurnishing")
    out = N(nt, "ShaderNodeOutputMaterial", (600, 0))
    hb = N(nt, "ShaderNodeBsdfHairPrincipled", (300, 0))
    hb.parametrization = "COLOR"
    hb.model = "CHIANG"
    info = N(nt, "ShaderNodeHairInfo", (-400, 0))
    rj = N(nt, "ShaderNodeMapRange", (-200, 0))
    L(nt, info.outputs["Random"], rj.inputs["Value"])
    rj.inputs["To Min"].default_value = 0.50
    rj.inputs["To Max"].default_value = 0.64
    cc = N(nt, "ShaderNodeCombineColor", (0, 0))
    L(nt, rj.outputs["Result"], cc.inputs["Red"])
    L(nt, rj.outputs["Result"], cc.inputs["Green"])
    cc2 = N(nt, "ShaderNodeMath", (0, -150))
    cc2.operation = "MULTIPLY"
    L(nt, rj.outputs["Result"], cc2.inputs[0])
    cc2.inputs[1].default_value = 0.98
    L(nt, cc2.outputs[0], cc.inputs["Blue"])
    L(nt, cc.outputs["Color"], hb.inputs["Color"])
    hb.inputs["Roughness"].default_value = 0.30
    hb.inputs["Radial Roughness"].default_value = 0.3
    hb.inputs["Coat"].default_value = 0.05
    L(nt, hb.outputs["BSDF"], out.inputs["Surface"])
    ob.data.materials.append(m)
    return ob


# ---------------------------------------------------------------------------
# Lighting, cameras, render
# ---------------------------------------------------------------------------

CAM_TARGET = Vector((0.045, 0.0, 1.495))
FACE_TARGET = Vector((0.085, 0.0, 1.525))
CAMERAS = {
    # name: (direction from target, distance[, target]) -- identical every round
    "Front": (Vector((1.0, 0.0, 0.02)), 1.75),
    "Profile": (Vector((0.0, -1.0, 0.02)), 1.75),
    "ThreeQuarter": (Vector((0.72, -0.69, 0.05)), 1.75),
    # face close-ups (~0.9 m, conversation distance) for detail review
    "CloseFront": (Vector((1.0, 0.0, 0.03)), 0.95, FACE_TARGET),
    "CloseThreeQuarter": (Vector((0.72, -0.69, 0.06)), 0.95, FACE_TARGET),
}


# Round 3: one frame matched to a reference photograph's camera and light for
# direct A/B (profile ref "Cat (4938330260)", CC BY 2.0, overcast daylight,
# camera above and slightly behind the cat's right shoulder looking down).
REFMATCH = {"RefMatch_Profile": (Vector((-0.18, -0.93, 0.42)), 1.05, Vector((0.02, 0.0, 1.50)))}


def build_cameras(coll):
    cams = {}
    for name, spec in list(CAMERAS.items()) + list(REFMATCH.items()):
        d, dist = spec[0], spec[1]
        tgt_ = spec[2] if len(spec) > 2 else CAM_TARGET
        cd = bpy.data.cameras.new(f"CAM_{name}")
        cd.lens = 85.0 if name in CAMERAS else 70.0
        cd.sensor_width = 36.0
        cd.dof.use_dof = True
        cd.dof.aperture_fstop = 8.0
        cd.clip_start = 0.05
        cd.clip_end = 50
        cam = link(bpy.data.objects.new(f"CAM_{name}", cd), coll)
        cam.location = tgt_ + d.normalized() * dist
        cam.rotation_euler = (tgt_ - cam.location).to_track_quat("-Z", "Y").to_euler()
        # focus on the near eye
        eye = world_from_head(eye_center(1.0 if "Front" in name else -1.0))
        cd.dof.focus_distance = (eye - cam.location).length
        cams[name] = cam
    return cams


def build_lighting(coll):
    """Studio: a round octabox key (single soft catchlight), a large dim fill,
    two strong rim/kicker strips behind the subject (120-150 deg from the
    cameras) that outline the strand silhouette, and a curved mid-grey
    cyclorama wide enough that every Studio camera sees the same background.
    Overcast: CC0 Kloofendal overcast pure-sky HDRI with a wet-stone ground."""
    rigs = {}
    st = bpy.data.collections.new("Light_Studio")
    coll.children.link(st)

    def area(name, loc, size, power, color=(1, 1, 1), shape="RECTANGLE", sy=None, aim=None):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy = power
        ld.shape = shape
        ld.size = size
        ld.size_y = sy or size
        ld.color = color
        ob = link(bpy.data.objects.new(name, ld), st)
        ob.location = loc
        tgt = aim if aim is not None else CAM_TARGET
        ob.rotation_euler = (tgt - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        return ob

    # round 3: key disc 1.2 -> 0.72 m (the catchlight ~40 % smaller)
    area("Studio_Key", (1.30, -1.15, 2.25), 0.72, 40.0, (1.0, 0.97, 0.93), shape="DISK")
    area("Studio_Fill", (1.35, 1.55, 1.55), 1.8, 9.0, (0.93, 0.96, 1.0), shape="DISK")
    area("Studio_RimL", (-1.25, 1.05, 1.95), 0.45, 62.0, (1.0, 0.98, 0.95), sy=1.4)
    area("Studio_RimR", (-1.15, -1.25, 1.85), 0.45, 56.0, (1.0, 0.98, 0.95), sy=1.4)
    area("Studio_Top", (-0.35, 0.0, 2.6), 0.9, 10.0, (1.0, 0.99, 0.97), shape="DISK")
    # cyclorama: floor + cove + wall on a 3.2 m radius from azimuth 40 to 250
    # deg (covers the Front, Profile and ThreeQuarter backgrounds)
    bm = bmesh.new()
    R0, cove, H = 3.2, 0.9, 4.5
    prof = [(0.0, 0.0), (R0 - cove, 0.0)]
    for i in range(1, 17):
        a = i / 16 * math.pi / 2
        prof.append((R0 - cove + cove * math.sin(a), cove - cove * math.cos(a)))
    prof.append((R0, H))
    angs = np.radians(np.linspace(40.0, 250.0, 64))
    grid = [[bm.verts.new((r * math.cos(t), r * math.sin(t), z)) for (r, z) in prof] for t in angs]
    for i in range(len(angs) - 1):
        for j in range(len(prof) - 1):
            bm.faces.new((grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j]))
    me = bpy.data.meshes.new("Studio_Cyclorama")
    bm.to_mesh(me)
    bm.free()
    bd = link(bpy.data.objects.new("Studio_Cyclorama", me), st)
    for p in me.polygons:
        p.use_smooth = True
    m, nt = new_mat("M_Studio_Backdrop")
    out = N(nt, "ShaderNodeOutputMaterial", (300, 0))
    bs = N(nt, "ShaderNodeBsdfPrincipled", (0, 0))
    bs.inputs["Base Color"].default_value = (0.36, 0.36, 0.37, 1)
    bs.inputs["Roughness"].default_value = 0.9
    L(nt, bs.outputs["BSDF"], out.inputs["Surface"])
    me.materials.append(m)
    rigs["Studio"] = st
    # round 3: a true three-point rig with a strong rim, to reveal the
    # silhouette breakup and the fur sheen (the Studio rig reads flat).
    # Round 4: both rims 40 % lower (round 3's clipped to a white halo)
    tp = bpy.data.collections.new("Light_ThreePoint")
    coll.children.link(tp)
    st_saved = st

    def area_tp(name, loc, size, power, color=(1, 1, 1), shape="RECTANGLE", sy=None):
        ob = area(name, loc, size, power, color, shape, sy, aim=FACE_TARGET)
        for uc in list(ob.users_collection):
            uc.objects.unlink(ob)
        tp.objects.link(ob)
        return ob

    area_tp("TP_Key", (1.05, -1.35, 2.35), 0.7, 55.0, (1.0, 0.96, 0.91), shape="DISK")
    area_tp("TP_Fill", (1.45, 1.20, 1.60), 1.6, 11.0, (0.90, 0.95, 1.0), shape="DISK")  # round 4: 1:9 -> ~1:5
    area_tp("TP_RimL", (-1.30, 0.75, 2.05), 0.30, 126.0, (1.0, 0.98, 0.95), sy=1.2)
    area_tp("TP_RimR", (-1.20, -0.85, 2.00), 0.30, 114.0, (1.0, 0.98, 0.95), sy=1.2)
    area_tp("TP_Hair", (-0.45, 0.0, 2.75), 0.6, 30.0, (1.0, 0.99, 0.97), shape="DISK")
    bd2 = link(bpy.data.objects.new("ThreePoint_Cyclorama", me), tp)
    bd2.data = me.copy()
    m2, nt2 = new_mat("M_ThreePoint_Backdrop")
    out2 = N(nt2, "ShaderNodeOutputMaterial", (300, 0))
    bs2 = N(nt2, "ShaderNodeBsdfPrincipled", (0, 0))
    bs2.inputs["Base Color"].default_value = (0.07, 0.07, 0.075, 1)
    bs2.inputs["Roughness"].default_value = 0.9
    L(nt2, bs2.outputs["BSDF"], out2.inputs["Surface"])
    bd2.data.materials.clear()
    bd2.data.materials.append(m2)
    rigs["ThreePoint"] = tp
    # round 3: exterior HDRI passes (real environments, no CG ground plane)
    for nm in ("Exterior", "RefMatch"):
        c_ = bpy.data.collections.new(f"Light_{nm}")
        coll.children.link(c_)
        rigs[nm] = c_
    oc = bpy.data.collections.new("Light_Overcast")
    coll.children.link(oc)
    bpy.ops.mesh.primitive_plane_add(size=40.0)
    gr = bpy.context.object
    gr.name = "Overcast_Ground"
    for uc in list(gr.users_collection):
        uc.objects.unlink(gr)
    oc.objects.link(gr)
    m, nt = new_mat("M_Overcast_Ground")
    out = N(nt, "ShaderNodeOutputMaterial", (300, 0))
    bs = N(nt, "ShaderNodeBsdfPrincipled", (0, 0))
    bs.inputs["Base Color"].default_value = (0.09, 0.09, 0.085, 1)
    bs.inputs["Roughness"].default_value = 0.55
    L(nt, bs.outputs["BSDF"], out.inputs["Surface"])
    gr.data.materials.append(m)
    rigs["Overcast"] = oc
    return rigs


def set_world(kind):
    w = bpy.data.worlds.get("CatBaseV6_World") or bpy.data.worlds.new("CatBaseV6_World")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = N(nt, "ShaderNodeOutputWorld", (400, 0))
    bg = N(nt, "ShaderNodeBackground", (200, 0))
    if kind in ("Studio", "ThreePoint"):
        bg.inputs["Color"].default_value = (0.045, 0.045, 0.048, 1) if kind == "Studio" else (0.012, 0.012, 0.013, 1)
        bg.inputs["Strength"].default_value = 1.0
    else:
        path, rot = {"Overcast": (HDRI, 120.0), "Exterior": (HDRI_EXTERIOR, 200.0), "RefMatch": (HDRI_REFMATCH, 60.0)}[kind]
        if not Path(path).exists():
            raise SystemExit(f"missing HDRI {path}; run scripts/art/fetch_cat_base_v6_sources.py hdris")
        env = N(nt, "ShaderNodeTexEnvironment", (-100, 0))
        env.image = bpy.data.images.load(str(path), check_existing=True)
        mp = N(nt, "ShaderNodeMapping", (-300, 0))
        tc = N(nt, "ShaderNodeTexCoord", (-500, 0))
        L(nt, tc.outputs["Generated"], mp.inputs["Vector"])
        mp.inputs["Rotation"].default_value = (0, 0, math.radians(rot))
        L(nt, mp.outputs["Vector"], env.inputs["Vector"])
        L(nt, env.outputs["Color"], bg.inputs["Color"])
        bg.inputs["Strength"].default_value = 1.0
    L(nt, bg.outputs["Background"], out.inputs["Surface"])


def configure_render(samples):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "METAL"
    prefs.get_devices()
    for d in prefs.devices:
        d.use = d.type == "METAL"
    sc.cycles.device = "GPU"
    sc.cycles.samples = samples
    sc.cycles.adaptive_threshold = 0.012
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = "OPENIMAGEDENOISE"
    sc.cycles.max_bounces = 32
    sc.cycles.diffuse_bounces = 6
    sc.cycles.glossy_bounces = 10
    sc.cycles.transmission_bounces = 24
    sc.cycles.transparent_max_bounces = 32
    sc.cycles.sample_clamp_indirect = 8.0
    sc.cycles_curves.shape = "THICK"
    sc.cycles_curves.subdivisions = 2
    sc.render.resolution_x = 1920
    sc.render.resolution_y = 1080
    sc.render.resolution_percentage = getattr(configure_render, "percent", 100)
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_depth = "8"
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass


def scrub_private_paths():
    """Keep local absolute paths (the user's home) out of committed files.

    The factory Shading workspace's file browser stores the home directory in the .blend,
    and Blender stamps the absolute .blend path into render PNG metadata ("File").
    """
    for scr in bpy.data.screens:
        for area in scr.areas:
            for sp in area.spaces:
                if sp.type == "FILE_BROWSER" and sp.params:
                    # .blend files store the whole char array, so overwrite stale bytes first
                    sp.params.directory = b"/" + b"_" * 400 + b"/"
                    sp.params.directory = b"//"
                    sp.params.filename = "_" * 200
                    sp.params.filename = ""
    for sc in bpy.data.scenes:
        sc.render.use_stamp_filename = False


def render_round(args, rigs, cams):
    rdir = Path(args.render_dir) if args.render_dir else OUT / "Renders" / f"round_{args.round}"
    rdir.mkdir(parents=True, exist_ok=True)
    sc = bpy.context.scene
    configure_render.percent = args.percent
    configure_render(args.samples)
    scrub_private_paths()
    written = []
    views = args.views.split(",") if args.views else ["Front", "Profile", "ThreeQuarter"]
    exposure = {"Studio": -0.25, "Overcast": 0.35, "ThreePoint": -0.10, "Exterior": 0.55, "RefMatch": 0.45}
    for light in args.lights.split(","):
        for nm, col in rigs.items():
            col.hide_render = nm != light
        set_world(light)
        sc.view_settings.exposure = exposure.get(light, 0.35)
        lviews = list(REFMATCH) if light == "RefMatch" else views
        sc.render.resolution_x = 1440 if light == "RefMatch" else 1920
        sc.render.resolution_y = 1080
        for view in lviews:
            sc.camera = cams[view]
            fp = rdir / f"CatBaseV6_R{args.round}_{light}_{view}.png"
            sc.render.filepath = str(fp)
            t0 = time.time()
            bpy.ops.render.render(write_still=True)
            log(f"rendered {fp.name} in {time.time()-t0:.0f}s")
            written.append(fp)
    return written


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def stage_build(args):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    configure_render(args.samples)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    root = bpy.data.collections.new("CatBaseV6")
    sc.collection.children.link(root)
    t0 = time.time()
    dense, tgt, skin = build_skin(root)
    log(f"skin cage {len(skin.data.polygons)} quads, target {len(tgt.data.polygons)} ({time.time()-t0:.0f}s)")
    images = bake_textures(skin, args.tex)
    bpy.data.objects.remove(dense, do_unlink=True)  # keep the .blend free of the 1.5M-quad source
    skin.data.materials.append(skin_material(images))
    mats = eye_materials()
    build_eyes(root, mats, skin)
    build_lid_margins(root, skin)
    layers, guides = build_groom(root, skin, images, args.guides)
    build_vibrissae(root, skin)
    build_inner_ear_furnishings(root, skin, images)
    cams = build_cameras(root)
    rigs = build_lighting(root)
    dg = bpy.context.evaluated_depsgraph_get()
    counts = {}
    for ob in layers:
        ev = ob.evaluated_get(dg)
        counts[ob.name] = len(ev.data.curves)
    log("strand counts (10% viewport preview)", counts)
    def set_amount(val):
        for ob in layers:
            for md in ob.modifiers:
                if md.node_group and md.node_group.name == "Interpolate Hair Curves":
                    ids = {it.name: it.identifier for it in md.node_group.interface.items_tree if getattr(it, "in_out", "") == "INPUT"}
                    getattr(md.properties.inputs, ids["Viewport Amount"]).value = val

    set_amount(1.0)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    for ob in layers:
        ev = ob.evaluated_get(dg)
        counts[ob.name] = len(ev.data.curves)
    log("strand counts after setting 100% (may be stale; the render stage recounts)", counts)
    set_amount(0.1)  # keep the saved file responsive in the viewport; render uses 100%
    OUT.mkdir(parents=True, exist_ok=True)
    blend = OUT / "CatBaseV6.blend"
    for img in images.values():
        img.filepath = "//Textures/" + Path(img.filepath_raw).name
    scrub_private_paths()
    bpy.ops.wm.save_as_mainfile(filepath=str(blend), compress=True, relative_remap=True)
    stats = dict(cage_quads=len(skin.data.polygons), sculpt_target_faces=len(tgt.data.polygons),
                 guides=args.guides, strands_viewport_preview_10pct=counts, build_seconds=round(time.time() - t0))
    (CACHE / "build_stats.json").write_text(json.dumps(stats, indent=2))
    log("saved", blend, stats)
    return rigs, cams


def stage_render(args):
    blend = OUT / "CatBaseV6.blend"
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    rigs = {nm: bpy.data.collections[f"Light_{nm}"] for nm in ("Studio", "Overcast", "ThreePoint", "Exterior", "RefMatch")
            if f"Light_{nm}" in bpy.data.collections}
    cams = {n: bpy.data.objects[f"CAM_{n}"] for n in list(CAMERAS) + list(REFMATCH) if f"CAM_{n}" in bpy.data.objects}
    counts = count_strands()
    (CACHE / f"strand_counts_round{args.round}.json").write_text(json.dumps(counts, indent=2))
    log("strand counts at 100% density", counts)
    return render_round(args, rigs, cams)


def count_strands():
    counts = {}
    for ob in bpy.data.objects:
        if ob.type != "CURVES":
            continue
        mods = [md for md in ob.modifiers if md.type == "NODES" and md.node_group and md.node_group.name == "Interpolate Hair Curves"]
        for md in mods:
            ids = {it.name: it.identifier for it in md.node_group.interface.items_tree if getattr(it, "in_out", "") == "INPUT"}
            getattr(md.properties.inputs, ids["Viewport Amount"]).value = 1.0
        ob.update_tag()
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        ev = ob.evaluated_get(dg)
        counts[ob.name] = dict(curves=len(ev.data.curves), points=len(ev.data.points), render=not ob.hide_render)
        for md in mods:
            ids = {it.name: it.identifier for it in md.node_group.interface.items_tree if getattr(it, "in_out", "") == "INPUT"}
            getattr(md.properties.inputs, ids["Viewport Amount"]).value = 0.1
        ob.update_tag()
    bpy.context.view_layer.update()
    return counts


def stage_manifest(args):
    """Hash every committed CatBaseV6 output and record the build parameters."""
    files = sorted(pth for pth in OUT.rglob("*") if pth.is_file() and pth.suffix in (".blend", ".png", ".json", ".md") and pth.name != "manifest.json")
    src = json.loads((OUT / "sources_manifest.json").read_text())
    ct = next(sc for sc in src["scans"] if CT_UID in sc["asset_id"])
    stats = json.loads((CACHE / "build_stats.json").read_text()) if (CACHE / "build_stats.json").exists() else {}
    if "strands" in stats:  # older key: counts were taken at the 10% viewport preview amount
        stats["strands_viewport_preview_10pct"] = stats.pop("strands")
    counts_p = CACHE / f"strand_counts_round{args.round}.json"
    counts = json.loads(counts_p.read_text()) if counts_p.exists() else {}
    man = {
        "schema": "sora-arena-source-ledger/2-draft",
        "asset_id": "CatBaseV6",
        "tier": "PUB-BY (derived original)",
        "status": "source-only art study; not runtime-approved",
        "round": args.round,
        "generator": "scripts/art/create_cat_base_v6.py",
        "source_fetcher": "scripts/art/fetch_cat_base_v6_sources.py",
        "blender": bpy.app.version_string,
        "units": "meters; +X face forward; +Z up; character scale 2.2x adult domestic cat",
        "derived_from": {
            "skull": {"name": ct["name"], "origin_url": ct["origin_url"], "license": ct["license"], "license_url": ct["license_url"],
                      "sha256": ct["sha256"], "storage": "Local/ThirdPartyRaw (private, decision D6)",
                      "attribution_text": "Domestic Cat (Felis catus) CT - original CT information courtesy of Dr Tobias Schwarz; adapted and prepared by Brian Mather, The Royal (Dick) School of Veterinary Studies, The University of Edinburgh (The University of Edinburgh Open.Ed, Sketchfab), CC BY 4.0",
                      "changes": "aligned to the midsagittal plane, scaled 2.2x, pitched 12 deg, Laplacian-smoothed, converted to a level set and used only as the bone surface under a new procedurally sculpted soft-tissue skin; no CT triangles are stored in the .blend"},
            "hdri": {"path": "Content/SourceArt/Environment/PolyHaven/kloofendal_overcast_puresky/kloofendal_overcast_puresky_4k.hdr", "license": "CC0-1.0", "author": "Greg Zaal (Poly Haven)"},
            "hdri_round3": [{"asset_id": h["asset_id"], "file": h["files"][0]["file"], "sha256": h["files"][0]["sha256"], "license": h["license"],
                             "authors": h["authors"], "role": h["role"], "storage": h["storage"]} for h in src.get("hdris", [])],
            "reference_photos": "sources_manifest.json (viewed only; no pixels used)",
        },
        "build": stats,
        "strand_counts_100pct": counts,
        "files": [{"path": str(pth.relative_to(ROOT)), "bytes": pth.stat().st_size, "sha256": sha256_file(pth)} for pth in files],
    }
    (OUT / "manifest.json").write_text(json.dumps(man, indent=2, ensure_ascii=False) + "\n")
    log("manifest", len(files), "files")


def stage_measure(args):
    """Round 3: numeric proportion check of the cached level-set skin (world
    frame, mm, head origin at 0) as the fixed Profile and Front cameras see
    it. Writes Local/CatBaseV6Cache/measure_round<N>.json."""
    d = np.load(CACHE / "skin_dense.npz")
    P = d["pts"].astype(np.float64) / MM
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    head = z > -60.0
    nose_x = float(x[head].max())
    occ_x = float(x[z > -10.0].min())
    crown = float(z[np.abs(y) < 5.0].max())
    cd = cornea_dims()
    gw = head_R() @ gaze_frame(-1.0)[:, 0]
    c = eye_center(-1.0) @ head_R().T / MM
    apex = c + gw * cd["apex"] / MM
    iris = c + gw * cd["d_i"] / MM
    band = (np.abs(np.abs(y) - abs(apex[1])) < 8.0) & (z > apex[2] + 8.0) & (z < apex[2] + 22.0)
    brow_x = float(x[band].max())
    L = nose_x - occ_x
    fo = np.array(fissure_outline_points(1.0, 200)) / MM
    med_y, lat_y = float(fo[:, 1].min()), float(fo[:, 1].max())
    eye_w = lat_y - med_y
    gap = 2.0 * med_y
    widths = {}
    for zz in range(-100, 100, 10):
        b = np.abs(z - zz) < 2.5
        if b.any():
            widths[str(zz)] = round(float(np.abs(y[b]).max()), 1)
    neck_min = min(widths[k] for k in widths if -110 <= int(k) <= -60)
    zyg = max(widths[k] for k in widths if -30 <= int(k) <= 20)
    temple = max(widths[k] for k in widths if 40 <= int(k) <= 60)
    Pw, _, _, at = ear_arrays(1.0, sdf=head_sdf_sampler())
    Pe = Pw / MM
    lo = (at["ear_t"] > 0.22) & (at["ear_t"] < 0.28)
    ear_med, ear_lat = float(Pe[lo, 1].min()), float(Pe[lo, 1].max())
    out = dict(
        nose_tip_x=round(nose_x, 1), occiput_x=round(occ_x, 1), crown_z=round(crown, 1), head_length=round(L, 1),
        cornea_apex_x=round(float(apex[0]), 1), iris_centre_x=round(float(iris[0]), 1), brow_front_x=round(brow_x, 1),
        brow_overhang_mm=round(brow_x - float(apex[0]), 1),
        cornea_to_nose_ratio=round((nose_x - apex[0]) / L, 3), iris_to_nose_ratio=round((nose_x - iris[0]) / L, 3),
        fissure_medial_canthus_y=round(med_y, 1), fissure_lateral_canthus_y=round(lat_y, 1),
        fissure_width_front_mm=round(eye_w, 1), medial_canthus_gap_mm=round(gap, 1), gap_over_eye_width=round(gap / eye_w, 2),
        cheek_half_width=zyg, temple_half_width=temple, temple_over_cheek=round(temple / zyg, 2),
        neck_min_half_width=neck_min, neck_over_cheek_skin=round(neck_min / zyg, 2),
        eye_width_over_bizygomatic_skin=round(eye_w / (2.0 * zyg), 3),
        ear_base_medial_y=round(ear_med, 1), ear_base_lateral_y=round(ear_lat, 1),
        ear_base_gap_over_width=round(2.0 * ear_med / (ear_lat - ear_med), 2), half_widths_by_world_z=widths,
        note="skin level (no fur); world frame mm, head origin at 0; eye values from the analytic eye/fissure")
    (CACHE / f"measure_round{args.round}.json").write_text(json.dumps(out, indent=2) + "\n")
    log("measure", json.dumps({k: v for k, v in out.items() if k != "half_widths_by_world_z"}))
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", type=int, default=1)
    ap.add_argument("--stages", default="skin,preview")
    ap.add_argument("--voxel", type=float, default=0.75)
    ap.add_argument("--samples", type=int, default=256)
    ap.add_argument("--preview-dir", default=str(CACHE / "preview"))
    ap.add_argument("--tex", type=int, default=4096)
    ap.add_argument("--guides", type=int, default=70000)
    ap.add_argument("--lights", default="Studio,Overcast")
    ap.add_argument("--views", default="")
    ap.add_argument("--render-dir", default="")
    ap.add_argument("--percent", type=int, default=100)
    args = ap.parse_args(argv)
    CACHE.mkdir(parents=True, exist_ok=True)
    Path(args.preview_dir).mkdir(parents=True, exist_ok=True)
    stages = args.stages.split(",")
    if "skin" in stages:
        stage_skin(args)
    if "preview" in stages:
        preview_dense(args)
    if "build" in stages:
        stage_build(args)
    if "render" in stages:
        stage_render(args)
    if "measure" in stages:
        stage_measure(args)
    if "manifest" in stages:
        stage_manifest(args)


if __name__ == "__main__":
    main()
