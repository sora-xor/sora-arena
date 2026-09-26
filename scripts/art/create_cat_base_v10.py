"""CatBaseV6 round 8 (generator v10): judged defects of round 7 (score 4.5/10).

Round 5 (create_cat_base_v7.py) took the head and neck shape from a real cat
scan ("Cat sitting upright" by elaughli, CC BY 4.0, private raw scan) and
kept the CT skull for landmarks; rounds 6 and 7 (v8, v9) reworked the eyes,
ears, nose, coat and bust on that surface. Round 8 keeps the method and the
scan field and fixes the round-7 judgement, most impactful first:

1. ear base: no separate ear shell turned on the old socket any more. The
   scan's old canal and socket are closed out of the scan field (a wider,
   stronger morphological closing and a re-smoothed temporal region), and
   the pinna's own skin flares onto the skull: every back and margin column
   of the pinna mesh bends into a quarter-round fillet (8-18 mm) that runs
   tangentially into the head skin and tucks under it, so the head skin and
   the ear back are one continuous surface with continuous fur. The concha
   is carved only in FRONT of the inner face (round 7 carved through the
   sheet and 0.35 of its thickness behind it: the slot along the back edge),
   down a funnel that narrows into a canal tube behind the tragus;
2. pinna form: cartilage 3.2 mm at the base tapering to 0.9 mm at the tip, a
   beaded medial margin and a rolled lateral one, a double-curvature shell
   (the back bows convex along the height as well as across it), conchal
   folds, a real antitragus and tragus, and Henry's pocket as a lateral fold
   that curls back on itself about a quarter of the way up with a notch
   above it;
3. ear size and set: 0.82x the height, 0.76x the base, 12 deg less splay, the
   medial bases 10 % closer, the lateral base above the upper-lid line,
   rounder tips;
4. furnishings rooted on the conchal floor and the medial-margin base,
   streaming up and out past the opening (3x denser in the lower third,
   15-25 deg jitter, clumped), a lateral-base tuft, short tip hairs and
   sparse vellus over the whole concha; the concha skin is greyer;
5. head: the cranium behind the ears 18 % shorter (a smooth warp) with a
   flatter occiput; a short (4-11 mm), flat head coat; one continuous flow
   field and one head guard layer, so there are no region edges;
6. profile face: the nose tip ~5 mm back, a deeper stop, the eyes 2.5 mm
   forward so the cornea domes proud of the lids, a wider fissure, a shorter
   flat chin coat and a mandible tucked behind the upper lip;
7. lower face: the chin raised, a mentum crease;
8. eyes: a smooth lid-margin sheet (the skin's faceted edge is hidden under
   it), periocular fur to within 0.5 mm of the margin, a Fresnel-only cornea,
   a darker limbal ring, a larger pink caruncle and a crisp tear line;
9. nose: a flat triangular planum overlapped by the dorsal-nose fur, liver-
   pink rim and lighter centre, a stronger cobblestone, wet nares and a
   philtrum groove through the upper lip;
10. neck and shoulders: the neck back to ~0.9 of the skull width, the
    scapular and shoulder forms halved, the shoulder coat combed down and
    back;
11. full coat to the ear base (no bald patch);
12. coat: cool silver agouti ground, crisp mackerel markings with a tabby M,
    mascara line, cheek bars and forehead lines.

Run from the repository root (Blender 5.2.2 LTS, background):

  blender -b --factory-startup --python scripts/art/create_cat_base_v10.py -- \\
      --stages skin,build,measure,render,compare,manifest --round 8 \\
      --samples 256 --views Front,Profile,ThreeQuarter,CloseFront,CloseThreeQuarter \\
      --lights Overcast,Studio,ThreePoint,Exterior,RefMatch

The `scan` stage of v7 (private raw scan -> Local/CatBaseV6Cache/scan_field.npz)
is reused unchanged; `--stages scan` here simply calls it.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import create_cat_base_v9 as v9  # noqa: E402

v8 = v9.v8
v7 = v9.v7
v6 = v9.v6
A = v6.A
MM = v6.MM
ROOT = v6.ROOT
OUT = v6.OUT
CACHE = v6.CACHE
log = v6.log
smoothstep = v6.smoothstep
_bump = v6._bump
N = v6.N
L = v6.L

ROUND = 8


# ---------------------------------------------------------------------------
# Head shape (skin stage)
# ---------------------------------------------------------------------------

# The round-7 muzzle warp moved the nose tip +13.8 mm and overshot (judged:
# a long tapering wedge from eye to nose). The warp is reduced from 11 to
# 8 mm and the nose pad is a flat planum (no 3.2 mm dome), ~5 mm back.
MUZZLE_DX_V10 = 9.0

# cranium behind the ears (judged: "the cranium runs about an ear-width
# behind the ear into a large occipital dome"): head-frame x behind
# CRANIUM_X0 is scaled by CRANIUM_SCALE (smoothly: the scale ramps in over
# the first 30 mm behind X0), fully above head z = -20 and fading out by
# z = -75 (the nape and neck are kept); the occiput is flattened by scaling
# the height above OCCIPUT_Z0 behind x = -40.
CRANIUM_X0 = -20.0
CRANIUM_SCALE = 0.82
OCCIPUT_Z0 = 10.0
OCCIPUT_SCALE = 0.90


# crown (the round-8 test frames next to the Nyaakoto reference and the
# front photographs: the crown sat ~0.74 eye spacings above the eye centres,
# the references ~0.9-1.1; the CT landmark check of round 5 also put the CT
# vertex ~14 mm above the scanned crown): the top of the head is lifted by
# up to CROWN_LIFT, fading out toward the occiput (kept flat), the sides and
# the brow
CROWN_LIFT = 13.0
CROWN_Z = (30.0, 70.0)


def crown_lift_src(Ph):
    x, y, z = Ph[..., 0] / MM, Ph[..., 1] / MM, Ph[..., 2] / MM
    # a wide lateral fade (round-8 test: fading over |y| 55-100 mm stood the
    # side of the head up as a wall above the cheek shelf)
    w = smoothstep(-75.0, -25.0, x) * (1.0 - smoothstep(105.0, 130.0, x)) * (1.0 - smoothstep(15.0, 115.0, np.abs(y)))
    out = np.array(Ph, float, copy=True)
    out[..., 2] -= CROWN_LIFT * smoothstep(CROWN_Z[0], CROWN_Z[1], z) * w * MM
    return out


def cranium_warp_src(Ph):
    """Source point (head frame, m) in the unwarped scan for destination Ph:
    the cranium behind CRANIUM_X0 shortened, the occiput flattened."""
    x, y, z = Ph[..., 0] / MM, Ph[..., 1] / MM, Ph[..., 2] / MM
    u = x - CRANIUM_X0
    ramp = smoothstep(0.0, -30.0, u)
    xs = CRANIUM_X0 + u * (1.0 + (1.0 / CRANIUM_SCALE - 1.0) * ramp)
    wz = smoothstep(-75.0, -20.0, z)
    xs = x + (xs - x) * wz
    wo = smoothstep(-40.0, -75.0, x) * smoothstep(-10.0, 10.0, z)
    zs = z + (z - OCCIPUT_Z0) * (1.0 / OCCIPUT_SCALE - 1.0) * wo * (z > OCCIPUT_Z0)
    out = np.array(Ph, float, copy=True)
    out[..., 0] = xs * MM
    out[..., 2] = zs * MM
    return out


# The scan's old ear canals and sockets (judged: "an open dark hole behind
# the near ear base in every three-quarter frame ... the scan's old ear
# canal or socket"): a morphological CLOSING with a larger radius inside
# larger masks than round 7, then a heavy blur there, so the temporal region
# is one smooth re-sculpted surface with no pit (scan units).
SCAN_CLOSE_V10 = 14.0
SCAN_CANAL_MASK = dict(c=(-64.0, 36.0, 10.0), r=18.0)  # scan units (H0), mirrored in y
SCAN_OPEN_V10 = 7.0
SCAN_EAR_MASK_SCALE_V10 = 1.45
SCAN_EAR_SMOOTH_V10 = 15
_SCAN_CLOSED_V10 = {}


def scan_field_v10():
    if "S" in _SCAN_CLOSED_V10:
        return _SCAN_CLOSED_V10
    p = CACHE / "scan_field_closed_v3f.npz"
    src = CACHE / "scan_field.npz"
    if p.exists() and p.stat().st_mtime >= src.stat().st_mtime:
        d = np.load(p)
        _SCAN_CLOSED_V10.update(S=d["S"].astype(np.float32), org=d["origin"].astype(np.float64), vs=float(d["vs"]))
        return _SCAN_CLOSED_V10
    t0 = time.time()
    d = np.load(src)
    S = d["S"].astype(np.float32)
    org, vs = d["origin"].astype(np.float64), float(d["vs"])
    r = SCAN_CLOSE_V10
    # first keep only the head's own shell: the round-5 opening left the
    # scanned pinnae as floating islands above the scalp (the skin mesher
    # dropped them as small components), and a closing this wide would
    # bridge them back onto the head as two large lobes
    S = v7.relevel(S, org, vs, band=r + 8.0)[0]
    X = [np.arange(S.shape[a]) * vs + org[a] for a in range(3)]
    gx, gy, gz = X[0][:, None, None], X[1][None, :, None], X[2][None, None, :]
    c, rr, soft = np.array(v7.SCAN_EAR_MASK["c"]), np.array(v7.SCAN_EAR_MASK["r"]), v7.SCAN_EAR_MASK["soft"]
    k = SCAN_EAR_MASK_SCALE_V10
    wear = np.zeros(S.shape, np.float32)
    for sgn in (1.0, -1.0):
        e = np.sqrt(((gx - c[0]) / (k * rr[0])) ** 2 + ((gy - sgn * c[1]) / (k * rr[1])) ** 2 + ((gz - c[2]) / (k * rr[2])) ** 2)
        wear = np.maximum(wear, 1.0 - smoothstep(1.0 - 1.6 * soft / rr.mean(), 1.0, e))
        # the scanned ear canals and their round-5 seals lie below the ear
        # masks (a shallow, nearly-open pit the skin insets opened up into a
        # crater with a boss): a second mask round them
        c2, r2 = np.array(SCAN_CANAL_MASK["c"]), SCAN_CANAL_MASK["r"]
        e2 = np.sqrt(((gx - c2[0]) / r2) ** 2 + ((gy - sgn * c2[1]) / r2) ** 2 + ((gz - c2[2]) / r2) ** 2)
        wear = np.maximum(wear, 1.0 - smoothstep(0.6, 1.0, e2))
    # first an OPENING inside the masks: the ledge the laid-back scanned ear
    # left along the side of the head (round-8 test frames: a round boss with
    # a groove round it behind the lateral ear base) is eroded away; its core
    # falls off as a separate component and is dropped by the re-level
    ro = SCAN_OPEN_V10
    So = v7.relevel(S + ro, org, vs, band=ro + 6.0)[0] - ro
    S = S + (np.maximum(So, S) - S) * wear
    # then the CLOSING: the old canals and sockets fill, and the corner
    # between the temple and the cheek shelf becomes a fillet of radius r
    Sd = v7.relevel(S - r, org, vs, band=r + 6.0)[0] + r
    Sc = S + (np.minimum(Sd, S) - S) * wear
    Sb = v6.gaussian_blur3(Sc, SCAN_EAR_SMOOTH_V10)
    Sc = Sc + (Sb - Sc) * wear
    np.savez_compressed(p, S=np.clip(Sc, -16.0, 16.0).astype(np.float16), origin=org, vs=vs)
    log(f"scan field closed v3 (r {r} scan units, mask x{k}) ({time.time()-t0:.0f}s)")
    _SCAN_CLOSED_V10.update(S=Sc.astype(np.float32), org=org, vs=vs)
    return _SCAN_CLOSED_V10


# neck (judged round 7: "after the 18 % neck narrowing the head sits on a
# stalk"): the extra side inset is cut from 15 to 5 mm and the nape dip
# from 15 to 9 mm, so the neck with its coat is ~0.9 of the skull width
NECK_SIDE_INSET_V10 = 2.0
NAPE_DIP_V10 = 9.0
# a shorter, flatter head coat (see coat_fields_v10) grows back on the
# cranium and cheeks: the skin comes out by the difference so the scanned
# silhouette is kept where the coat got thinner, except behind the ears
COAT_THIN_MM = {"cheek": 1.2, "jowl": 1.6}
TEMPLE_INSET = 3.0


def fur_inset_mm_v10(Pw_mm):
    t = v8.fur_inset_mm_v8(Pw_mm)
    x, y, z = Pw_mm[..., 0], np.abs(Pw_mm[..., 1]), Pw_mm[..., 2]
    band = smoothstep(-46.0, -86.0, z)
    side = smoothstep(26.0, 66.0, y) * (1.0 - smoothstep(70.0, 110.0, x))
    t = t + NECK_SIDE_INSET_V10 * band * side
    nape = np.exp(-((z + 72.0) / 22.0) ** 2) * smoothstep(-35.0, -85.0, x) * (1.0 - smoothstep(38.0, 72.0, y))
    t = t + NAPE_DIP_V10 * nape
    cheek = smoothstep(55.0, 85.0, y) * (1.0 - smoothstep(10.0, 40.0, z)) * smoothstep(-20.0, 20.0, x)
    jowl = smoothstep(-15.0, -55.0, z) * smoothstep(20.0, 70.0, y) * (1.0 - smoothstep(110.0, 135.0, x))
    t = t - COAT_THIN_MM["cheek"] * cheek - COAT_THIN_MM["jowl"] * jowl
    # temples: a gentle, broad 3 mm paring (an 8 mm narrow one, tried against
    # a bulge between the ear base and the cheek, left a ridge once the
    # scan's ear ledge was opened away and the corner closed into a fillet)
    Ph = Pw_mm @ v6.head_R()
    hx, hy, hz = Ph[..., 0], np.abs(Ph[..., 1]), Ph[..., 2]
    temple = np.exp(-((hx + 8.0) / 40.0) ** 2 - ((hz - 14.0) / 26.0) ** 2) * smoothstep(50.0, 95.0, hy)
    return t + TEMPLE_INSET * temple


# chin and mandible (judged: "mouth-to-chin is about 1.5x the reference
# ratio, the white chin a puffy mass"; "tuck the mandible behind the upper
# lip"): below the mouth the scan is sampled through a further lift and a
# backward shift
CHIN_LIFT = 10.0  # mm, at the chin
CHIN_TUCK = 4.0  # mm back at the chin


def chin_warp_src(Ph):
    x, y, z = Ph[..., 0] / MM, Ph[..., 1] / MM, Ph[..., 2] / MM
    wz = smoothstep(-24.0, -40.0, z) * (1.0 - smoothstep(-70.0, -95.0, z))
    wx = smoothstep(80.0, 118.0, x) * (1.0 - smoothstep(30.0, 60.0, np.abs(y)))
    w = wz * wx
    out = np.array(Ph, float, copy=True)
    out[..., 2] -= CHIN_LIFT * w * MM
    out[..., 0] += CHIN_TUCK * w * MM
    return out


def scan_head_neck_v10(P):
    """Round-8 scan head and neck: the closed v3 scan field, sampled through
    the cranium, chin and (reduced) muzzle warps, with the round-8 insets.
    The round-7 canal plugs are gone: the wider closing removes the pits,
    and a plug surfaced as a knob inside the new concha."""
    P = np.asarray(P, float)
    Pmm = P / MM
    Ph = P @ v6.head_R()
    Ps = v9.muzzle_warp_src(chin_warp_src(cranium_warp_src(crown_lift_src(Ph))))
    Psrc = Ps @ v6.head_R().T
    d = v7.scan_sdf_world(Psrc) + fur_inset_mm_v10(Pmm) * MM
    return v6.smax(d, (v7.Z_CUT - Pmm[..., 2]) * MM, v7.K_CUT * MM)


# bust (judged: "the shoulder points flare into epaulette-like tufts ... in
# profile the scapula makes a hard, curved shell-like ridge"): the scapular
# blade, its dorsal border and the point of the shoulder are halved
def build_bust_ops_v10():
    R = v6.rot_matrix
    dx, dz = v9.BUST_DX, v9.BUST_DZ

    def p(x, y, z):
        return (x + dx, y, z + dz)

    ops = []
    for s in (1.0, -1.0):
        ops.append(v6.cap_op(p(-62.0, 20.0 * s, -110.0), p(-64.0, 62.0 * s, -154.0), 22.0, 26.0, 30, frame="body"))  # trapezius
        ops.append(v6.ell_op(p(-76.0, 48.0 * s, -180.0), (9.0, 28.0, 50.0), R(roll=-22.0 * s, pitch=-8.0), 30, frame="body"))  # scapular blade (halved)
        ops.append(v6.ell_op(p(-30.0, 84.0 * s, -180.0), (32.0, 26.0, 46.0), R(roll=-12.0 * s), 30, frame="body"))  # deltoid
        ops.append(v6.ell_op(p(-6.0, 92.0 * s, -196.0), (16.0, 14.0, 16.0), None, 22, frame="body"))  # point of the shoulder (halved)
        ops.append(v6.cap_op(p(-20.0, 88.0 * s, -206.0), p(-6.0, 92.0 * s, -424.0), 30.0, 21.0, 28, frame="body"))  # forelimb
        ops.append(v6.ell_op(p(26.0, 40.0 * s, -206.0), (30.0, 38.0, 44.0), R(yaw=18.0 * s, roll=-10.0 * s), 28, frame="body"))  # pectoral
    ops.append(v6.cap_op(p(-22.0, 0.0, -104.0), p(-38.0, 0.0, -190.0), 62.0, 80.0, 32, frame="body"))  # neck base (wider)
    ops.append(v6.ell_op(p(54.0, 0.0, -172.0), (26.0, 24.0, 44.0), None, 26, frame="body"))  # keel
    ops.append(v6.ell_op((52.0, 0.0, -120.0), (32.0, 40.0, 38.0), None, 26, frame="body"))  # throat fill
    ops.append(v6.ell_op(p(-34.0, 0.0, -318.0), (96.0, 92.0, 205.0), None, 44, frame="body"))  # thorax
    for s in (1.0, -1.0):
        ops.append(v6.ell_op(p(34.0, 68.0 * s, -252.0), (14.0, 4.0, 40.0), R(yaw=-24.0 * s), 12, mode="subtract", frame="body"))
    return ops


def build_bust_field_v10(vs=2.0 * MM):
    t0 = time.time()
    lo = np.floor(v6.DOMAIN_MIN / vs).astype(int) - 4
    hi = np.ceil(v6.DOMAIN_MAX / vs).astype(int) + 4
    shape = tuple(hi - lo + 1)
    xs = [np.arange(lo[a], hi[a] + 1) * vs for a in range(3)]
    ops = build_bust_ops_v10()
    Bf = np.empty(shape, np.float32)
    for a in range(shape[0]):
        J, K = np.meshgrid(xs[1], xs[2], indexing="ij")
        P = np.stack([np.full_like(J, xs[0][a]), J, K], -1).reshape(-1, 3)
        f = np.full(len(P), 0.2)
        f = v6.apply_ops(ops, P, f)
        f = v6.smax(f, -(P[:, 2] + 0.600), 12 * MM)
        Bf[a] = f.reshape(J.shape)
    Bb = v6.gaussian_blur3(Bf, 5)
    log(f"bust field v10 {shape} ({time.time()-t0:.0f}s)")
    return Bb, lo * vs


# ---------------------------------------------------------------------------
# Pinna (round 8)
# ---------------------------------------------------------------------------

EAR_BASE_V10 = (-15.0, 45.0, 60.0)  # head mm (round 7: -18, 52, 47); on the lifted crown
EAR_H_V10 = 58.0  # mm (round 7: 66)
EAR_CHORD_V10 = 72.0  # visible base chord (round 7: 95)
EAR_TIP_R_V10 = 7.0
EAR_T0_V10 = 3.2  # cartilage + skin at the base
EAR_T1_V10 = 0.9  # at the tip
EAR_LEAN_OUT_V10 = 20.0  # splay (round 7: 32)
EAR_LEAN_BACK_V10 = 11.0
EAR_OPEN_OUT_V10 = 4.0  # opening 4 deg outward of forward (round 7: 6 deg inward)
EAR_TWIST_V10 = 8.0
HENRY_T = (0.14, 0.27)  # Henry's pocket along the lateral margin (height fraction)
HENRY_CURL_DEG = 140.0
HENRY_CURL_R = 1.6  # mm
FLARE_R = (5.5, 18.0)  # fillet radius (mm) at the lateral and the medial side of the base
FLARE_TUCK = 0.5  # mm under the head skin at the bottom of the fillet


def _curl_arc(s_pts, kap, s_c, kc, n=2000):
    """Cross-section centre line with curvature kap for s < s_c and kap - kc
    (a backward curl) beyond s_c: positions (x toward the opening, y
    lateral), inner normals and tangents at the arc lengths s_pts."""
    lo, hi = min(float(np.min(s_pts)), 0.0), max(float(np.max(s_pts)), 0.0)
    s = np.linspace(lo, hi, n)
    k = np.where(s > s_c, kap - kc, kap)
    ds = np.diff(s)
    i0 = int(np.argmin(np.abs(s)))
    a = np.zeros(n)
    a[1:] = np.cumsum(0.5 * (k[1:] + k[:-1]) * ds)
    a -= a[i0]
    tx, ty = np.sin(a), np.cos(a)
    x = np.zeros(n)
    y = np.zeros(n)
    x[1:] = np.cumsum(0.5 * (tx[1:] + tx[:-1]) * ds)
    y[1:] = np.cumsum(0.5 * (ty[1:] + ty[:-1]) * ds)
    x -= x[i0]
    y -= y[i0]
    ai = np.interp(s_pts, s, a)
    p = np.stack([np.interp(s_pts, s, x), np.interp(s_pts, s, y)], -1)
    nin = np.stack([np.cos(ai), -np.sin(ai)], -1)
    tan = np.stack([np.sin(ai), np.cos(ai)], -1)
    return p, nin, tan


def ear_rings_v10(n_t=120, n_face=52, n_rim=9):
    """Round-8 pinna cross-sections (ear-frame mm, x toward the opening, y
    lateral, z up the axis), with per-vertex attributes (t, u, face) and the
    cross-section's outward normal (x, y) used by the base flare.

    - thickness 3.2 mm at the base tapering (power 1.4) to 0.9 mm at the tip,
      thinner toward the margins;
    - a beaded medial margin (roll 1.35 -> 0.45 mm) and a rolled lateral one
      (0.75 -> 0.3 mm);
    - the cross-section bends 222 deg at the base (a cupped concha) and ~70
      deg at the tip; below t = 0 it narrows (0.45x) and closes (+85 deg) into
      the conchal funnel;
    - double curvature: the whole section bows back by up to 3 mm at mid-
      height, so the back is convex along the height as well as across;
    - conchal folds (three 1.0 mm ridges in the lower concha), an antitragus
      (3.4 mm) and a tragus (3.0 mm) at the entrance;
    - Henry's pocket: over HENRY_T the lateral margin grows a flap that curls
      165 deg BACK on itself (radius 2.3 mm), leaving a slit pocket between
      the flap and the back of the ear, with a notch above it."""
    H = A.ear_h / MM
    W0 = A.ear_chord / MM
    tip = A.ear_tip_r / MM
    t_lo = -22.0 / H
    ts = np.concatenate([np.linspace(t_lo, 0.0, 16, endpoint=False), np.linspace(0.0, 1.0, n_t)])
    uf = np.sin(np.linspace(-0.5 * math.pi, 0.5 * math.pi, n_face))
    rings, attrs, outs = [], [], []
    tcap = 1.0 - 1.7 * tip / H
    thin = 1.0 - 0.50 * smoothstep(0.55, 1.0, np.abs(uf))
    kc = 1.0 / HENRY_CURL_R
    for t in ts:
        tc = float(np.clip(t, 0.0, 1.0))
        W = 2.0 * tip + (W0 - 2.0 * tip) * (1.0 - tc) ** 0.62
        if tc > tcap:
            W = W * math.sqrt(max(1.0 - ((tc - tcap) / (1.0 - tcap)) ** 2, 0.0)) + 0.3
        bend = 70.0 + 152.0 * (1.0 - tc) ** 0.9
        if t < 0:
            f = min(-t / abs(t_lo), 1.0)
            W *= 1.0 - 0.55 * f
            bend += 85.0 * f
        phi = math.radians(bend)
        R = 0.5 * W if phi >= math.pi else 0.5 * W / math.sin(0.5 * phi)
        S = R * phi
        kap = 1.0 / R
        hp = float(_bump(np.array(tc), HENRY_T[0], HENRY_T[1]))
        notch = float(_bump(np.array(tc), HENRY_T[1] + 0.015, HENRY_T[1] + 0.06))
        curl_len = math.radians(HENRY_CURL_DEG) * HENRY_CURL_R * hp
        w_med = 0.47 * S
        w_lat0 = 0.53 * S - 2.4 * notch
        w_lat = w_lat0 + curl_len
        s_c = w_lat0 - 0.3
        T = (EAR_T1_V10 + (EAR_T0_V10 - EAR_T1_V10) * (1.0 - tc) ** 1.4)
        if tc > tcap:
            T *= max(0.55, math.sqrt(max(1.0 - ((tc - tcap) / (1.0 - tcap)) ** 2, 0.0)))
        z = t * H
        xlean = -6.0 * tc ** 2 - 12.0 * min(t, 0.0) / t_lo - 3.0 * math.sin(math.pi * tc) ** 1.2
        ymed = -6.0 * min(t, 0.0) / t_lo
        s_front = np.where(uf < 0, uf * w_med, uf * w_lat)
        kc_here = kc if hp > 1e-3 else 0.0
        p, nin, tan = _curl_arc(s_front, kap, s_c, kc_here)
        ridge = np.zeros_like(uf)
        for kk, (tk, hk, uk) in enumerate(((0.03, 0.8, -0.10), (0.075, 0.65, 0.05), (0.13, 0.5, -0.02))):
            tk_u = tk + 0.012 * np.sin(5.0 * uf + 1.7 * kk)
            ridge += hk * np.exp(-((tc - tk_u) / 0.016) ** 2) * (1.0 - smoothstep(0.22, 0.50, np.abs(uf - uk)))
        ridge += 3.4 * math.exp(-((t - 0.03) / 0.06) ** 2) * np.exp(-((uf - 0.70) / 0.14) ** 2)  # antitragus
        ridge += 3.0 * math.exp(-((t + 0.02) / 0.06) ** 2) * np.exp(-((uf + 0.78) / 0.12) ** 2)  # tragus
        Tl = T * thin
        front = p + nin * (0.5 * Tl + ridge)[:, None]
        back = p - nin * (0.5 * Tl)[:, None]
        rim_pts, rim_u, rim_o = [], [], []
        for end in (+1, -1):
            pe, ne, te = _curl_arc(np.array([w_lat if end > 0 else -w_med]), kap, s_c, kc_here)
            pe, ne, te = pe[0], ne[0], te[0] * end
            Te = T * thin[-1 if end > 0 else 0]
            if end < 0:
                roll = 1.35 * (1.0 - 0.67 * tc)
            else:
                roll = 0.75 * (1.0 - 0.6 * tc) * (1.0 - 0.5 * hp)
            rr = 0.5 * Te + roll
            pe = pe + ne * 0.6 * roll
            ang = np.linspace(0.0, math.pi, n_rim + 2)[1:-1]
            if end < 0:
                ang = ang[::-1]
            dirs = np.cos(ang)[:, None] * ne[None, :] + np.sin(ang)[:, None] * te[None, :]
            pts = pe[None, :] + dirs * rr
            if end < 0:
                pts = pts[::-1]
                dirs = dirs[::-1]
            rim_pts.append(pts)
            rim_u.append(np.full(n_rim, float(end)))
            rim_o.append(dirs)
        ring2 = np.concatenate([front, rim_pts[0], back[::-1], rim_pts[1][::-1]])
        # flare direction: the outward normal of the UNCURLED section (the
        # Henry's-pocket curl must not steer the fillet)
        _, nin0, _ = _curl_arc(s_front, kap, s_c, 0.0)
        o2 = np.concatenate([-nin0, -np.tile(nin0[-1:], (n_rim, 1)), -nin0[::-1], -np.tile(nin0[:1], (n_rim, 1))])
        u_ring = np.concatenate([uf, rim_u[0], uf[::-1], rim_u[1]])
        # the curled flap of Henry's pocket turns the inner face outward: it is
        # haired back skin (round-8 test: a bare pale card at the lateral base)
        cf = np.clip((s_front - s_c) / max(curl_len, 1e-3), 0.0, 1.0) * (hp > 1e-3)
        f_front = 1.0 - 2.0 * smoothstep(0.20, 0.55, cf)
        f_ring = np.concatenate([f_front, -np.ones(n_rim), -np.ones(n_face), -np.ones(n_rim)])
        x = ring2[:, 0] + xlean
        y = ring2[:, 1] - ymed
        fade = 1.0 - smoothstep(0.0, 0.30, t)
        zz = np.full_like(x, z) - 0.25 * np.maximum(ring2[:, 1], 0.0) * fade
        tw = math.radians(A.ear_twist) * (1.0 - tc) ** 1.5
        x, y = x * math.cos(tw) - y * math.sin(tw), x * math.sin(tw) + y * math.cos(tw)
        ox, oy = o2[:, 0] * math.cos(tw) - o2[:, 1] * math.sin(tw), o2[:, 0] * math.sin(tw) + o2[:, 1] * math.cos(tw)
        rings.append(np.stack([x, y, zz], -1))
        attrs.append(np.stack([np.full_like(x, t), u_ring, f_ring], -1))
        outs.append(np.stack([ox, oy, np.zeros_like(ox)], -1))
    return np.array(rings), np.array(attrs), np.array(outs)


def _sdf_grad(sdf, P, h=0.8 * MM):
    g = np.stack([(sdf(P + np.eye(3)[k] * h) - sdf(P - np.eye(3)[k] * h)) / (2 * h) for k in range(3)], -1)
    return g / (np.linalg.norm(g, axis=-1, keepdims=True) + 1e-12)


def flare_columns(Pw, At, Ow, sdf, n_face, n_rim):
    """Bend the back and margin columns of a seated pinna into a quarter-round
    fillet that runs tangentially onto the head skin and tucks FLARE_TUCK
    under it (judged round 7: a dark slot along the back edge, a raised fur
    lip round the base and an exposed socket, because the pinna was a
    separate shell stuck into the head). Each vertex at height a above the
    head (bulk field) moves out along its cross-section normal, slid along
    the head surface, by r_f (1 - sqrt(1 - (1 - a/r_f)^2)) for a < r_f;
    buried vertices spread further and are projected just under the skin.
    Returns the moved points and the flare weight (1 at the tucked foot, 0
    above the fillet)."""
    nr, npr, _ = Pw.shape
    P = Pw.reshape(-1, 3).copy()
    O = Ow.reshape(-1, 3)
    u = At[..., 1].reshape(-1)
    j = np.tile(np.arange(npr), nr)
    front = j < n_face
    uf = At[0, :n_face, 1]
    wb = np.ones(len(P))
    wb[front] = smoothstep(0.62, 0.95, np.abs(uf[j[front]]))
    r_f = (0.5 * (FLARE_R[0] + FLARE_R[1]) - 0.5 * (FLARE_R[1] - FLARE_R[0]) * np.clip(u, -1.0, 1.0)) * MM
    a = sdf(P)
    g = _sdf_grad(sdf, P)
    q = a / r_f
    delta = np.where(q >= 1.0, 0.0, np.where(q > 0.0, 1.0 - np.sqrt(np.clip(1.0 - (1.0 - q) ** 2, 0.0, 1.0)), 1.0 + 0.8 * (-q)))
    delta = delta * r_f * wb
    Ot = O - np.sum(O * g, 1, keepdims=True) * g
    Ot /= np.linalg.norm(Ot, axis=1, keepdims=True) + 1e-12
    P2 = P + Ot * delta[:, None]
    # tuck: the foot of the fillet goes just under the head skin
    wt = (1.0 - smoothstep(0.03, 0.16, q)) * wb
    Q = P2.copy()
    for _ in range(5):
        dq = sdf(Q) + FLARE_TUCK * MM
        gq = _sdf_grad(sdf, Q)
        Q = Q - gq * dq[:, None]
    P3 = P2 + (Q - P2) * wt[:, None]
    # relax each column along its height inside the fillet (no kinks)
    P3 = P3.reshape(nr, npr, 3)
    wr = ((1.0 - smoothstep(0.7, 1.1, q)) * wb).reshape(nr, npr)
    for _ in range(4):
        Pm = P3.copy()
        Pm[1:-1] = 0.25 * P3[:-2] + 0.5 * P3[1:-1] + 0.25 * P3[2:]
        P3 = P3 + (Pm - P3) * (0.6 * wr * (1.0 - wt.reshape(nr, npr)))[..., None]
    flare = np.clip((1.0 - np.clip(q, 0.0, 1.0)) * wb, 0.0, 1.0)
    return P3, flare.reshape(nr, npr)


def ear_arrays_v10(side=1.0, n_t=120, n_face=52, n_rim=9, sdf=None):
    """Round-8 pinna (see ear_rings_v10) placed on the head, seated 1 mm
    into it, its back and margins flared onto the skull (flare_columns), and
    split into the inner and back islands (the groom interpolates children
    per island). Attributes: is_ear, ear_t, ear_u, ear_face, ear_flare."""
    Rr, At, Oo = ear_rings_v10(n_t, n_face, n_rim)
    Rr = Rr * MM
    nr, npr, _ = Rr.shape
    q = Rr.reshape(-1, 3).copy()
    q[:, 1] *= side
    o = Oo.reshape(-1, 3).copy()
    o[:, 1] *= side
    base = A.ear_base.copy()
    base[1] *= side
    F = v6.ear_frame(side)
    Ph = base + q @ F.T
    Pw = (Ph @ v6.head_R().T).reshape(nr, npr, 3)
    Ow = ((o @ F.T) @ v6.head_R().T).reshape(nr, npr, 3)
    flare = np.zeros((nr, npr))
    if sdf is not None:
        Pw = v7.seat_ear_columns(Pw, At[:, 0, 0], side, sdf, depth=1.0 * MM, t_free=0.30)
        Pw, flare = flare_columns(Pw, At, Ow, sdf, n_face, n_rim)
    Pw = Pw.reshape(-1, 3)
    At2 = np.concatenate([At, flare[..., None]], -1)
    A2 = At2.reshape(-1, 4)
    idx = np.arange(nr * npr).reshape(nr, npr)
    cL = n_face + n_rim // 2
    cM = 2 * n_face + n_rim + n_rim // 2
    inner_cols = list(range(cM, npr)) + list(range(0, cL + 1))
    back_cols = list(range(cL, cM + 1))
    P_list = [Pw]
    A_list = [A2]
    nxt = nr * npr
    dup = {}
    for c in (cL, cM):
        dup[c] = np.arange(nxt, nxt + nr)
        P_list.append(Pw.reshape(nr, npr, 3)[:, c])
        A_list.append(At2[:, c])
        nxt += nr
    tip_ids = []
    for strip in (0, 1):
        cols = inner_cols if strip == 0 else back_cols
        tip_ids.append(nxt)
        P_list.append(Pw.reshape(nr, npr, 3)[-1, cols].mean(0)[None] + ((np.array([0.0, 0.0, 0.15 * MM]) @ F.T) @ v6.head_R().T)[None])
        A_list.append(np.array([[1.0, 0.0, 1.0 if strip == 0 else -1.0, 0.0]]))
        nxt += 1
    Pw = np.vstack(P_list)
    A2 = np.vstack(A_list)
    quads, tris = [], []
    for strip in (0, 1):
        cols = inner_cols if strip == 0 else back_cols
        col_ids = [idx[:, c] if not (strip == 1 and c in dup) else dup[c] for c in cols]
        for i in range(nr - 1):
            for k in range(len(cols) - 1):
                a0, a1 = col_ids[k][i], col_ids[k + 1][i]
                b0, b1 = col_ids[k][i + 1], col_ids[k + 1][i + 1]
                quads.append((a0, a1, b1, b0))
        for k in range(len(cols) - 1):
            tris.append((col_ids[k][-1], col_ids[k + 1][-1], tip_ids[strip], tip_ids[strip]))
    attrs = dict(is_ear=np.ones(len(Pw)), ear_t=A2[:, 0], ear_u=A2[:, 1], ear_face=A2[:, 2], ear_flare=A2[:, 3])
    return Pw, np.array(quads), np.array(tris), attrs


# ---------------------------------------------------------------------------
# Conchal cavity (front of the inner face only) and canal
# ---------------------------------------------------------------------------

EAR_CAVITY_T_V10 = (-0.20, 0.60)
CAVITY_K = 2.6 * MM  # smooth subtraction: the tragal lip in front of the concha is rounded, not cut
CANAL = dict(len=11.0, tilt=45.0, r=(3.0, 2.0))  # mm, deg from the ear axis toward the cranium centre, radii
_EAR_CAVITY_V10 = {}
EAR_CAVITY_REBUILD_V10 = [False]
_BUILDING_CAVITY = [False]


def build_ear_cavity_v10(sdf):
    """Voxelise the conchal cavity of each seated pinna: for every ring
    between EAR_CAVITY_T_V10 the region from 0.45 mm IN FRONT of the inner
    face to the chord joining the two margins (the Henry's-pocket flap
    excluded), so the head skin is carved only inside the cup and down its
    funnel, never behind the back of the ear (round 7's carve started 0.35
    of the sheet thickness behind the back face and left a slot along the
    back edge). The canal is a tapering tube down from the funnel floor."""
    t0 = time.time()
    n_face, n_rim = 52, 9
    npr = 2 * n_face + 2 * n_rim
    clouds = []
    for s in (1.0, -1.0):
        Pw, quads, tris, at = ear_arrays_v10(s, sdf=sdf)
        nr = (len(Pw) - 2) // (npr + 2)
        R = Pw[:nr * npr].reshape(nr, npr, 3)
        t = np.asarray(at["ear_t"])[:nr * npr].reshape(nr, npr)[:, 0]
        Fr = R[:, :n_face]
        Bk = R[:, n_face + n_rim:2 * n_face + n_rim][:, ::-1]
        nf = Fr - Bk
        nf /= np.linalg.norm(nf, axis=-1, keepdims=True) + 1e-12
        M = Fr + nf * 0.45 * MM
        keep = (t <= EAR_CAVITY_T_V10[1]) & (t >= EAR_CAVITY_T_V10[0])
        M, tt = M[keep], t[keep]
        kr = np.linspace(0, len(M) - 1, 3 * (len(M) - 1) + 1)
        i0 = np.clip(np.floor(kr).astype(int), 0, len(M) - 2)
        f = (kr - i0)[:, None, None]
        M = M[i0] * (1 - f) + M[i0 + 1] * f
        tt = tt[i0] * (1 - f[:, 0, 0]) + tt[i0 + 1] * f[:, 0, 0]
        ku = np.linspace(0, n_face - 1, 4 * (n_face - 1) + 1)
        j0 = np.clip(np.floor(ku).astype(int), 0, n_face - 2)
        g = (ku - j0)[None, :, None]
        M = M[:, j0] * (1 - g) + M[:, j0 + 1] * g
        uf = np.sin(np.linspace(-0.5 * math.pi, 0.5 * math.pi, n_face))
        uu = uf[j0] * (1 - g[0, :, 0]) + uf[j0 + 1] * g[0, :, 0]
        for i in range(len(M)):
            ti = float(tt[i])
            hp = float(_bump(np.array(ti), HENRY_T[0], HENRY_T[1]))
            # near the base the cavity keeps off the margins, whose fillets
            # rest on uncarved head skin (a carve under the medial margin
            # opened a crack at its foot)
            wm = float(smoothstep(0.02, 0.16, ti))
            u_max = (0.80 + 0.17 * wm) - 0.25 * hp
            u_min = -(0.74 + 0.23 * wm)
            sel = (uu <= u_max) & (uu >= u_min)
            Mi = M[i][sel]
            lam_u = np.linspace(0.0, 1.0, len(Mi))[:, None]
            C = Mi[:1] + (Mi[-1:] - Mi[:1]) * lam_u
            span = float(np.linalg.norm(Mi - C, axis=-1).max())
            # near the base the carve stops short of the chord, so the head
            # skin in front of the opening slopes into the concha as a low
            # tragal floor instead of a cut wall
            lam_max = 0.55 + 0.45 * float(smoothstep(0.0, 0.22, ti))
            nl = int(math.ceil(lam_max * span / (0.4 * MM))) + 1
            for lam in np.linspace(0.0, lam_max, nl):
                clouds.append(((1.0 - lam) * Mi + lam * C).astype(np.float32))
        # canal: a tapering tube from the floor of the seated funnel, down
        # the ear axis and a little medially (it opens at the bottom of the
        # concha, behind the tragus)
        Fm = v6.ear_frame(s)
        axw = Fm[:, 2] @ v6.head_R().T
        medw = (-Fm[:, 1] * s) @ v6.head_R().T
        low = (t >= EAR_CAVITY_T_V10[0]) & (t <= EAR_CAVITY_T_V10[0] + 0.06)
        c0 = Fr[low][:, 18:34].reshape(-1, 3).mean(0) + (Bk[low][:, 18:34].reshape(-1, 3).mean(0) - Fr[low][:, 18:34].reshape(-1, 3).mean(0)) * 0.0
        inw = (np.array([-10.0, 0.0, 20.0]) * MM) @ v6.head_R().T - c0
        inw /= np.linalg.norm(inw)
        dirw = -axw * math.cos(math.radians(CANAL["tilt"])) + inw * math.sin(math.radians(CANAL["tilt"]))
        dirw /= np.linalg.norm(dirw)
        for k in np.linspace(0.0, 1.0, 50):
            cen = c0 + dirw * (CANAL["len"] * k * MM)
            rad = CANAL["r"][0] + (CANAL["r"][1] - CANAL["r"][0]) * k
            gg = np.stack(np.meshgrid(*[np.linspace(-rad, rad, int(2 * rad / 0.4) + 1)] * 3, indexing="ij"), -1).reshape(-1, 3)
            gg = gg[np.linalg.norm(gg, axis=1) <= rad]
            clouds.append((cen + gg * MM).astype(np.float32))
    pts = np.concatenate(clouds)
    vs = v9.EAR_CAVITY_VS
    lo = np.floor(pts.min(0) / vs).astype(int) - 6
    hi = np.ceil(pts.max(0) / vs).astype(int) + 6
    shape = tuple(hi - lo + 1)
    ijk = np.floor(pts / vs).astype(int) - lo
    occ = np.zeros(shape, bool)
    occ[ijk[:, 0], ijk[:, 1], ijk[:, 2]] = True
    occ = v7.dilate6(occ, 1)
    ob = v6.gaussian_blur3(occ.astype(np.float32), 3)
    G = ((0.5 - ob) * 3.0 * MM).astype(np.float32)
    log(f"ear cavity v10 {shape} from {len(pts)} samples, {int(occ.sum())} voxels ({time.time()-t0:.0f}s)")
    return G, lo * vs, vs


def ear_cavity_v10():
    if "G" not in _EAR_CAVITY_V10:
        p = CACHE / "ear_cavity_v10.npz"
        if EAR_CAVITY_REBUILD_V10[0] or not p.exists():
            _BUILDING_CAVITY[0] = True
            G, org, vs = build_ear_cavity_v10(v6.head_sdf_sampler())
            _BUILDING_CAVITY[0] = False
            np.savez_compressed(p, G=G.astype(np.float16), origin=org, vs=vs)
            EAR_CAVITY_REBUILD_V10[0] = False
        d = np.load(p)
        G = d["G"].astype(np.float32)
        G = np.where(G >= 1.45 * MM, np.float32(25.0 * MM), G)
        _EAR_CAVITY_V10.update(G=G, org=d["origin"].astype(np.float64), vs=float(d["vs"]))
    return _EAR_CAVITY_V10


def ear_cavity_sd_v10(Pw):
    c = ear_cavity_v10()
    G, org, vs = c["G"], c["org"], c["vs"]
    P = np.asarray(Pw, float)
    shp = P.shape[:-1]
    P2 = P.reshape(-1, 3)
    out = np.full(len(P2), 25.0 * MM)
    hi = org + (np.array(G.shape) - 1) * vs
    m = np.all((P2 > org) & (P2 < hi), axis=1)
    if m.any():
        out[m] = v6.trilinear(G, org, vs, P2[m])
    return out.reshape(shp)


def cup_weight_v10(Pw):
    """1 on head skin inside the carved concha (pale inner-ear skin, vellus
    and furnishings there), 0 elsewhere: only inside the cavity, not round
    its rim (round 7's rim band cut the head coat to 1.5 mm and left the
    bald, stippled patch in front of the medial ear base)."""
    return 1.0 - smoothstep(-1.2 * MM, 0.3 * MM, ear_cavity_sd_v10(Pw))


# ---------------------------------------------------------------------------
# Eyes, nose, mouth, chin (detail ops)
# ---------------------------------------------------------------------------

EYE_FORWARD_V10 = 2.5  # mm: the globes 2.5 mm forward along the gaze (the lid centre is kept)
FISSURE_UP_V10 = 9.8  # mm (round 7: 9.4): the fissure opens a little, also in profile
FISSURE_LO_V10 = 10.9  # mm (round 7: 10.9)
LEATHER_EDGE_H_V10 = 0.55  # mm: a nearly flush planum (round 7: 2.0 edge + 3.2 dome)
LEATHER_DOME_V10 = 0.7
LEATHER_BEVEL_V10 = 0.9
ALAR_H_V10 = 1.5
STOP_DEPTH_V10 = 3.0  # round 7: 1.6 (and its centre sat ~15 mm below the round-7 surface, so it had no effect)
STOP_C_V10 = (136.0, 26.0)  # head (x, z) mm, on the round-8 dorsal profile: stop-to-tip ~0.93 fissure widths
BROW_H_V10 = 2.2
BROW_C_V10 = (113.0, 43.0)
CHIN_H_V10 = 1.2  # round 7: 3.0 (the puffy chin)
MENTUM_Z = -33.5  # head z of the mentum crease (between the lower lip and the chin)
# surface-relative lifts and dips (B -/+ h w) are applied with a hard min /
# max: a smooth min of two nearly equal fields lowers the result by k/4
# everywhere inside the op's box, so round 7's k = 0.5-0.8 mm drew a 0.1-0.2
# mm step at the box edges (the seam across the forehead)
K_REL = 1e-7


def build_detail_ops_v10():
    """Round 8 detail ops (surface-relative on the warped scan bulk). Changes
    from round 7 (build_detail_ops_v9):

    - nose: a nearly flush, flat triangular planum (0.55 mm edge, 0.7 mm
      centre, 0.9 mm bevel) instead of the 5.2 mm domed cap (judged: "a pink
      rubber eraser cap"), alar wings 1.5 mm flaring beside comma nostrils on
      the front plane;
    - a deeper stop (3.2 mm) under a fuller brow (3.0 mm);
    - a flatter chin (1.2 mm) and a shallow mentum crease below the lower lip;
    - a deeper philtrum groove carried through the upper lip to the mouth;
    - eyes: the round-7 lid shell, carves and lid fill band, about globes
      2.5 mm further forward;
    - the conchal cavity from the front of each inner face (ear_cavity_v10)."""
    ops = []
    mz = A.mz
    lp = v6.leather_poly()
    zc = v9.leather_centre()
    alar = [np.asarray([(y * s, z) for y, z in v6.ALAR_POLY]) for s in (1.0, -1.0)]

    def leather(P, B):
        q = np.stack([P[..., 1], P[..., 2]], -1) / MM
        d2 = v6.sd_poly2d(q, lp)
        inside = np.clip(-d2 / LEATHER_BEVEL_V10, 0.0, 1.0)
        bev = np.sqrt(np.clip(1.0 - (1.0 - inside) ** 2, 0.0, 1.0))
        dome = LEATHER_DOME_V10 * np.exp(-(q[..., 0] / 7.5) ** 2 - ((q[..., 1] - zc - 1.0) / 6.0) ** 2)
        da = np.minimum(v6.dist_poly2d(q, alar[0]), v6.dist_poly2d(q, alar[1]))
        wing = ALAR_H_V10 * np.exp(-(da / 1.2) ** 2)
        h = (LEATHER_EDGE_H_V10 + dome + wing) * bev
        d = np.maximum(d2 * MM, B - h * MM)
        return np.maximum(d, v6.NOSE_X0 * MM - P[..., 0])

    ops.append(v6.Op("union", leather, v6.v(v6.NOSE_X0, -14.0, -17.0), v6.v(v6.NOSE_X0 + 40.0, 14.0, 14.0), 0.35 * MM))

    def bridge(P, B):
        x, y, z = P[..., 0] / MM, P[..., 1] / MM, P[..., 2] / MM
        w = np.exp(-(y / 9.0) ** 2) * smoothstep(104.0, 124.0, x) * smoothstep(-2.0, 7.0, z) * (1.0 - smoothstep(28.0, 38.0, z))
        w = w * (1.0 - 0.6 * smoothstep(v6.NOSE_X0 - 6.0, v6.NOSE_X0 + 4.0, x))
        return B - 1.8 * MM * w

    ops.append(v6.Op("union", bridge, v6.v(96.0, -30.0, -6.0), v6.v(v6.NOSE_X0 + 30.0, 30.0, 45.0), K_REL))

    def brow(P, B):
        x, y, z = P[..., 0] / MM, P[..., 1] / MM, P[..., 2] / MM
        w = np.exp(-((x - BROW_C_V10[0]) / 12.0) ** 2 - (y / 22.0) ** 2 - ((z - BROW_C_V10[1]) / 9.0) ** 2)
        return B - BROW_H_V10 * MM * w

    def stop(P, B):
        x, y, z = P[..., 0] / MM, P[..., 1] / MM, P[..., 2] / MM
        w = np.exp(-((x - STOP_C_V10[0]) / 7.0) ** 2 - (y / 12.0) ** 2 - ((z - STOP_C_V10[1]) / 7.0) ** 2)
        return -(B + STOP_DEPTH_V10 * MM * w)

    ops.append(v6.Op("union", brow, v6.v(75.0, -60.0, 15.0), v6.v(150.0, 60.0, 75.0), K_REL))
    ops.append(v6.Op("subtract", stop, v6.v(105.0, -40.0, 5.0), v6.v(160.0, 40.0, 55.0), K_REL))
    for s in (1.0, -1.0):
        def pad(P, B, s_=s):
            y, z, x = P[..., 1] / MM, P[..., 2] / MM, P[..., 0] / MM
            w = np.exp(-((y - v9.PAD_C_V9[1] * s_) / v9.PAD_R_V9[0]) ** 2 - ((z - v9.PAD_C_V9[2]) / v9.PAD_R_V9[1]) ** 2)
            w = w * smoothstep(104.0 + mz, 120.0 + mz, x)
            return B - v9.PAD_H_V9 * MM * w

        ylo, yhi = sorted(((v9.PAD_C_V9[1] - 30.0) * s, (v9.PAD_C_V9[1] + 30.0) * s))
        ops.append(v6.Op("union", pad, v6.v(100.0 + mz, ylo, -48.0), v6.v(170.0 + mz, yhi, 2.0), K_REL))
    LL = v9.LOWER_LIP_V9

    def lower_lip(P, B):
        y, z, x = P[..., 1] / MM, P[..., 2] / MM, P[..., 0] / MM
        w = np.exp(-((y - LL[0]) / LL[2]) ** 2 - ((z - LL[1]) / LL[3]) ** 2)
        w = w * smoothstep(104.0 + mz, 118.0 + mz, x)
        return B - LL[4] * MM * w

    ops.append(v6.Op("union", lower_lip, v6.v(100.0 + mz, -25.0, -45.0), v6.v(170.0 + mz, 25.0, -12.0), K_REL))
    CH = v9.CHIN_V9

    def chin(P, B):
        y, z, x = P[..., 1] / MM, P[..., 2] / MM, P[..., 0] / MM
        w = np.exp(-((y - CH["c"][0]) / CH["r"][0]) ** 2 - ((z - (CH["c"][1] + 3.0)) / CH["r"][1]) ** 2)
        w = w * smoothstep(96.0 + mz, 112.0 + mz, x)
        return B - CHIN_H_V10 * MM * w

    ops.append(v6.Op("union", chin, v6.v(92.0 + mz, -30.0, -62.0), v6.v(170.0 + mz, 30.0, -20.0), K_REL))
    for s in (1.0, -1.0):
        c = v6.lid_center(s)
        r = A.eye_r + A.lid_gap + A.lid_t + A.lid_upper_extra + 6.0 * MM
        ops.append(v6.Op("union", (lambda s_: lambda P, B=None: v6.sd_lid_shell(P, s_))(s), c - r, c + r, 4.0 * MM))
    cd = v6.cornea_dims()
    for s in (1.0, -1.0):
        c = v6.eye_center(s)
        r = A.eye_r + A.lid_gap
        ops.append(v6.Op("subtract", (lambda c_, r_: lambda P, B=None: v6.sd_sphere(P, c_, r_))(c, r), c - r, c + r, 1.0 * MM))
        cc = c + v6.gaze_frame(s)[:, 0] * (cd["apex"] - cd["Rc"])
        rc = cd["Rc"] + A.lid_gap
        ops.append(v6.Op("subtract", (lambda c_, r_: lambda P, B=None: v6.sd_sphere(P, c_, r_))(cc, rc), cc - rc, cc + rc, 1.0 * MM))
        ops.append(v6.Op("subtract", (lambda s_: lambda P, B=None: v6.sd_fissure(P, s_))(s), c - 0.045, c + 0.045, 0.6 * MM))
        rr = A.eye_r + 8.0 * MM
        ops.append(v6.Op("union", (lambda s_: lambda P, B=None: v9.lid_band_sd(P, s_))(s), c - rr, c + rr, 0.7 * MM))
    for s in (1.0, -1.0):
        def nostril(P, B, s_=s):
            q = np.stack([P[..., 1], P[..., 2]], -1) / MM
            d = v9.nostril_sd_mm(q, s_) * MM
            d = np.maximum(d, v6.NOSE_X0 * MM - P[..., 0])
            return np.maximum(d, -B - 3.2 * MM)

        poly = np.asarray([(y * s, z) for y, z in v6.NOSTRIL_POLY])
        lo = np.array([v6.NOSE_X0, poly[:, 0].min() - 2.0, poly[:, 1].min() - 2.0]) * MM
        hi = np.array([v6.NOSE_X0 + 47.0, poly[:, 0].max() + 2.0, poly[:, 1].max() + 2.0]) * MM
        ops.append(v6.Op("subtract", nostril, lo, hi, 0.35 * MM))
    ops.append(v6.groove_op(v6.PHILTRUM, (1, 2), 0, 118.0 + mz, 185.0 + mz, [0.34, 0.46, 0.44], [1.3, 1.4, 1.1], 0.45))
    for s in (1.0, -1.0):
        poly = [(y * s, z) for y, z in v9.LIP_Y_V9]
        ops.append(v6.groove_op(poly, (1, 2), 0, 100.0 + mz, 185.0 + mz, [0.40, 0.36, 0.30, 0.18], [1.1, 1.0, 0.7, 0.3], 0.55))
    ops.append(v6.groove_op(v9.MOUTH_NOTCH, (1, 2), 0, 100.0 + mz, 185.0 + mz, [0.25, 0.45, 0.25], [0.3, 0.7, 0.3], 0.9))
    # mentum crease: a shallow shadow line across the chin below the lower lip
    ops.append(v6.groove_op([(-10.0, MENTUM_Z + 1.2), (-5.0, MENTUM_Z + 0.2), (0.0, MENTUM_Z), (5.0, MENTUM_Z + 0.2), (10.0, MENTUM_Z + 1.2)],
                            (1, 2), 0, 96.0 + mz, 185.0 + mz, [0.2, 0.55, 0.65, 0.55, 0.2], [0.2, 0.6, 0.7, 0.6, 0.2], 1.1))
    c = ear_cavity_v10()
    hi = c["org"] + (np.array(c["G"].shape) - 1) * c["vs"]
    ops.append(v6.Op("subtract", lambda P, B=None: ear_cavity_sd_v10(P), c["org"], hi, CAVITY_K, frame="body"))
    return ops


# ---------------------------------------------------------------------------
# Markings (round 8): crisp mackerel strokes (head frame mm, half-widths mm)
# ---------------------------------------------------------------------------

# judged round 7: "diffuse, marbled camouflage blotches ... the face lacks
# the tabby M, the mascara line from the lateral canthus and the cheek bars".
# Narrower strokes with a 0.45 mm edge and only fine (sub-stroke) jitter.
MARKINGS_V10 = [
    # tabby M: outer legs rise from above the medial third of each eye to
    # the peaks, inner strokes fall to the central bar
    ("m_outer", [(90, 33, 42), (86, 28, 49), (82, 22, 56), (78, 17, 61)], [2.0, 2.6, 2.6, 2.2]),
    ("m_inner", [(78, 15, 62), (82, 10, 57), (86, 6, 52), (88, 3, 48)], [2.0, 1.8, 1.6, 1.3]),
    ("m_center", [(90, 0, 47), (84, 0, 55), (76, 0, 63), (62, 0, 71), (44, 0, 77), (18, 0, 80), (-10, 0, 76), (-40, 0, 64), (-66, 0, 42)],
     [1.6, 2.4, 2.8, 3.0, 3.0, 3.1, 3.1, 3.0, 2.8]),
    # forehead lines running back over the crown between the ears
    ("fore_a", [(80, 12, 60), (66, 12, 68), (48, 13, 75), (26, 14, 79), (2, 15, 78), (-24, 16, 71), (-50, 17, 57)],
     [1.8, 2.3, 2.5, 2.6, 2.6, 2.4, 2.0]),
    ("fore_b", [(84, 24, 50), (72, 24, 60), (56, 25, 68), (36, 26, 74), (14, 27, 76), (-8, 28, 72)], [1.5, 2.1, 2.3, 2.3, 2.1, 1.6]),
    ("fore_c", [(80, 36, 48), (68, 35, 58), (52, 34, 66), (34, 34, 72), (14, 35, 74)], [1.2, 1.8, 2.0, 1.9, 1.4]),
    # mascara line: from the lateral canthus back and slightly down
    ("mascara", [(69, 59, 23), (61, 66, 21), (51, 73, 17), (40, 79, 12), (28, 83, 7), (16, 84, 2)], [1.0, 1.8, 2.3, 2.3, 2.0, 1.2]),
    # cheek bars: two curved bars below it
    ("cheek2", [(78, 56, 4), (66, 65, -1), (53, 73, -7), (40, 79, -12), (27, 81, -15), (15, 79, -16)], [0.9, 1.7, 2.2, 2.2, 1.8, 1.0]),
    ("cheek3", [(70, 61, -17), (58, 69, -22), (46, 74, -27), (33, 76, -31), (21, 74, -33)], [0.8, 1.5, 1.8, 1.5, 0.9]),
    # tear line: from the medial canthus down beside the nose
    ("lacrimal", [(88, 18.5, 14), (95, 16.5, 7), (102, 15.0, 0), (108, 14.0, -5)], [0.8, 0.75, 0.65, 0.4]),
]
MARK_EDGE_V10 = 0.45


# ---------------------------------------------------------------------------
# Coat, groom and layer fields (round 8)
# ---------------------------------------------------------------------------

HEAD_LENGTH_KEYS_V10 = [
    # (head-frame centre, length mm, sigma mm): a short (1.6-9 mm), flat
    # head coat (judged round 7: "2-3x too long for a shorthair, hides the
    # skull"; round 7: up to 10.5 mm on the occiput and 15 mm on the jowls)
    ((141, 0, -8), 1.6, 8), ((130, 0, 12), 2.0, 10), ((112, 0, 32), 2.6, 11), ((95, 0, 52), 3.4, 13), ((64, 0, 72), 4.5, 17),
    ((15, 0, 80), 5.5, 22), ((-35, 0, 70), 6.5, 24), ((-72, 0, 30), 7.5, 22), ((-85, 0, -10), 8.5, 22),
    ((136, 14, -20), 2.0, 9), ((130, 26, -30), 2.6, 10), ((114, 33, -42), 3.2, 10), ((112, 0, -50), 3.4, 10), ((84, 0, -80), 5.5, 10),
    ((92, 40, 21), 2.2, 12), ((86, 36, 44), 2.8, 8), ((80, 62, 5), 3.8, 13), ((50, 82, 5), 5.5, 14), ((24, 86, -18), 7.0, 16),
    ((4, 80, -44), 8.5, 18), ((32, 72, -42), 7.0, 14), ((46, 0, -86), 8.0, 18), ((0, 62, 70), 5.0, 13),
    ((-40, 55, 50), 6.0, 20), ((-70, 60, 10), 8.0, 22),
]


def ear_near_weight_v10(Ph):
    """~1 on the head skin round each ear base, falling off over ~40 mm
    (judged: region parameters must blend over >= 15 mm real)."""
    w = np.zeros(Ph.shape[:-1])
    for s in (1.0, -1.0):
        x, y, z = v8.ear_q(Ph, s)
        e = np.sqrt(((x - 10.0) / 40.0) ** 2 + (y / 52.0) ** 2 + (z / 26.0) ** 2)
        w = np.maximum(w, 1.0 - smoothstep(0.45, 1.5, e))
    return w


def ear_behind_weight_v10(Ph):
    w = np.zeros(Ph.shape[:-1])
    for s in (1.0, -1.0):
        x, y, z = v8.ear_q(Ph, s)
        e = np.sqrt(((x - 10.0) / 40.0) ** 2 + (y / 52.0) ** 2 + (z / 26.0) ** 2)
        w = np.maximum(w, (1.0 - smoothstep(0.55, 1.6, e)) * (1.0 - smoothstep(-10.0, 18.0, x)))
    return w


def coat_fields_v10(Pw, Nw, ex=None):
    """Round 8 coat, region, groom and layer fields (replaces coat_fields_v9).
    Changes, per judged defect:

    - markings (MARKINGS_V10): crisp strokes (0.45 mm edge) with only fine
      jitter (round 7: a 3.2 mm, 22 mm-scale jitter marbled every stroke);
    - head coat 1.6-9 mm and flat (3-4 deg), no separate ruff: every region
      parameter blends over >= 35 mm;
    - lids: fur to within ~0.5 mm of the margin, 2.2-4 mm long, lying flat
      (round 7: <= 0.7 mm there, which left a bald grey ring);
    - chin: 3.4-4.5 mm, flat; neck and ruff 16-22 mm, standing 10-12 deg;
    - ear base: full head coat up to the base and up the fillet (the flare
      ramps the length from the head coat to the ear-back coat), no short
      'cup' band outside the concha (round 7's bald patch);
    - pinna: back coat 5.5 -> 3.2 mm to the tip, dense to the margins;
      inner face: sparse vellus everywhere, denser over the lower third;
      the concha skin is greyer (cup)."""
    Pw = np.asarray(Pw, float)
    Nw = np.asarray(Nw, float)
    n = len(Pw)
    is_ear, ear_t, ear_u, ear_face = v6.ex_arrays(n, ex)
    flare = ex.get("ear_flare", np.zeros(n)) if ex is not None else np.zeros(n)
    earm = is_ear > 0.5
    inner = earm & (ear_face > 0.2)
    back = earm & ~inner
    au = np.abs(ear_u)
    Ph = Pw @ v6.head_R()
    Nh = Nw @ v6.head_R()
    x, y, z = Ph[:, 0] / MM, Ph[:, 1] / MM, Ph[:, 2] / MM
    ay = np.abs(y)
    xw, yw, zw = Pw[:, 0] / MM, Pw[:, 1] / MM, Pw[:, 2] / MM
    P3 = np.stack([x, y, z], -1)
    mz = A.mz
    jit = (v6.fbm(Pw, 0.0011, 2, 11.0) - 0.5) * 0.7 + (v6.fbm(Pw, 0.006, 2, 12.0) - 0.5) * 0.9
    jit_w = (v6.fbm(Pw, 0.0011, 2, 11.0) - 0.5) * 1.3 + (v6.fbm(Pw, 0.022, 2, 12.0) - 0.5) * 3.2
    cup = cup_weight_v10(Pw) * (~earm)

    # ---- white: muzzle, blaze, chin, throat, bib (round 7's masks)
    muz = np.sqrt(((x - 124 - mz) / 32) ** 2 + (y / 40) ** 2 + ((z + 33) / 27) ** 2)
    d_white = (muz - 1.0) * 26.0
    muz2 = np.sqrt(((x - 126.0 - mz) / 34.0) ** 2 + (y / 45.0) ** 2 + ((z + 27.0) / 30.0) ** 2)
    d_white = np.minimum(d_white, (muz2 - 1.0) * 26.0)
    wb2 = np.clip(17.0 - 0.30 * (z + 5.0), 4.0, 17.0)
    d_white = np.minimum(d_white, np.maximum(np.maximum(ay - wb2, z - 44.0), 96.0 - x))
    chin = (np.sqrt(((x - 104 - mz) / 26) ** 2 + (y / 30) ** 2 + ((z + 62) / 20) ** 2) - 1.0) * 18.0
    d_white = np.minimum(d_white, chin)
    throat = np.maximum(np.maximum(ay - 30.0 - 0.30 * np.clip(-60 - z, 0, 90), z + 56.0), 18.0 - x)
    d_white = np.minimum(d_white, throat)
    wbib = 28.0 + 0.32 * np.clip(-95.0 - zw, 0.0, 400.0) - 0.0006 * np.clip(-95.0 - zw, 0.0, 400.0) ** 2
    bib = np.maximum(np.maximum(ay - wbib, zw + 80.0), -(Nw[:, 0] + 0.05) * 60.0)
    d_white = np.minimum(d_white, bib)
    d_white = np.where(earm, 1e3, d_white)
    body_w = smoothstep(-110.0, -160.0, zw)
    lobes = (v6.fbm(Pw, 0.030, 3, 21.0) - 0.5) * (8.0 + 24.0 * body_w) + (v6.fbm(Pw, 0.060, 2, 31.0) - 0.5) * 40.0 * body_w
    tufts = (v6.fbm(Pw, 0.009, 2, 23.0) - 0.5) * (3.0 + 11.0 * smoothstep(-95.0, -140.0, zw))
    ew = 0.35 + 3.6 * smoothstep(-95.0, -140.0, zw)
    white = 1.0 - smoothstep(-ew, ew, d_white + jit_w + lobes + tufts)

    # ---- mackerel strokes: crisp
    dm = v8.dist_fields_per_marking(P3)
    stripe = np.zeros(n)
    for nm, d in dm.items():
        e = MARK_EDGE_V10 if nm != "lacrimal" else 0.35
        stripe = np.maximum(stripe, 1.0 - smoothstep(-e, e, d + jit))
    ang = np.arctan2(yw, xw + 40.0)
    zz = zw + 5.0 * np.sin(ang * 2.0 + 0.7) + 3.0 * np.sin(ang * 5.0 + 1.3) + (v6.fbm(Pw, 0.040, 2, 45.0) - 0.5) * 16.0
    per = 34.0
    ph_ = np.mod(zz + 8.0, per) - 0.5 * per
    wband = 5.2 + 1.0 * np.sin(ang * 3.0)
    brk = (v6.fbm(Pw, 0.018, 2, 47.0) - 0.5) * 7.0
    body_band = (np.abs(ph_) - wband + np.maximum(brk, 0.0)) * smoothstep(-120.0, -150.0, zw)
    dors = np.maximum(ay - 8.0, xw + 60.0) + 1e3 * (zw > -20.0)
    d_body = np.minimum(body_band + 1e3 * (zw > -125.0), dors)
    stripe = np.maximum(stripe, 1.0 - smoothstep(-0.6, 0.6, d_body + jit))
    thumb = _bump(ear_t, 0.30, 0.60) * _bump(ear_u, -0.30, 0.40) * back
    ear_rim_c = smoothstep(0.86, 0.98, au)
    ear_back_dark = (0.55 + 0.30 * smoothstep(0.65, 0.95, ear_t)) * (1.0 - 0.3 * ear_rim_c) * (1.0 - flare)
    # the inner half of each rolled margin carries the back coat wrapping over
    # the edge (judged: 'a bare, flat, bevelled grey or white ribbon')
    wrap = inner * smoothstep(0.90, 0.985, au)
    stripe = np.where(earm, np.where(inner, 0.75 * ear_back_dark * wrap, np.maximum(ear_back_dark, stripe * flare)), stripe)
    white = np.where(inner, 1.0 - wrap, white)
    stripe = np.clip(stripe * (1.0 - 0.6 * thumb), 0.0, 1.0)
    white = np.maximum(white, 0.6 * smoothstep(0.3, 0.7, cup))
    stripe = np.clip(stripe * (1.0 - white) * (1.0 - cup), 0.0, 1.0)

    # ---- follicles (round 7)
    on_pad = smoothstep(112.0 + mz, 120.0 + mz, x) * smoothstep(0.15, 0.40, Nh[:, 0])
    fol_d = np.full(n, 1e3)
    m_pad = on_pad > 0
    if m_pad.any():
        for s in (1.0, -1.0):
            ms = m_pad & ((y > 0) if s > 0 else (y <= 0))
            if not ms.any():
                continue
            grid = v9.follicle_grid_v9(s)
            fg = np.array([(yy, zz_) for _, _, yy, zz_ in grid])
            rad = np.array([0.30 if col == 0 else 0.42 for _, col, _, _ in grid])
            q = np.stack([ay[ms], z[ms]], -1)
            dd = np.linalg.norm(q[:, None, :] - fg[None], axis=-1) - rad[None]
            fol_d[ms] = dd.min(1)
    follicle = (1.0 - smoothstep(-0.12, 0.22, fol_d)) * on_pad

    # ---- eyes: fissure distance
    d_fis = np.full(n, 1e3)
    near_eye = np.zeros(n, bool)
    for s in (1.0, -1.0):
        c = v6.lid_center(s) / MM
        m = np.linalg.norm(P3 - c, axis=1) < 44.0
        if not m.any():
            continue
        near_eye |= m
        d2 = v6.sd_fissure(Ph[m], s) / MM
        rr = np.linalg.norm(Ph[m] - v6.eye_center(s), axis=1) / MM
        d2 = np.where(rr < (A.eye_r + A.lid_gap + A.lid_t + A.lid_upper_extra) / MM + 7.0, d2, 1e3)
        d_fis[m] = np.minimum(d_fis[m], d2)
    spect = (1.0 - smoothstep(6.0, 10.0, d_fis)) * smoothstep(3.0, 5.0, d_fis)
    pale = np.clip(np.maximum(0.20 * spect, 0.6 * thumb), 0.0, 1.0) * (1.0 - cup)

    # ---- regions (round 7)
    q2 = np.stack([y, z], -1)
    d_leather = v6.sd_poly2d(q2, v6.leather_poly())
    nose = (1.0 - smoothstep(-0.25, 0.25, d_leather)) * smoothstep(v6.NOSE_X0 - 3.0, v6.NOSE_X0 + 1.0, x) * smoothstep(-0.25, 0.05, Nh[:, 0])
    rim = (1.0 - smoothstep(0.35, 1.3, -d_leather)) * nose
    pig = np.zeros(n)
    pig = np.maximum(pig, 1.0 - smoothstep(0.30, 0.65, np.abs(d_fis)))
    pig = np.maximum(pig, (d_fis < 0).astype(float) * near_eye)
    fr = smoothstep(v6.NOSE_X0 - 6.0, v6.NOSE_X0, x)
    nost = np.full(n, 1e3)
    for s in (1.0, -1.0):
        nost = np.minimum(nost, v9.nostril_sd_mm(q2, s))
    pig = np.maximum(pig, 0.85 * (1.0 - smoothstep(-0.25, 0.15, nost)) * fr)
    lipd = np.full(n, 1e3)
    for s in (1.0, -1.0):
        lipd = np.minimum(lipd, v6.dist_poly2d(q2, [(yy * s, zz_) for yy, zz_ in v9.LIP_Y_V9]))
    lipf = smoothstep(110.0 + mz, 118.0 + mz, x) * smoothstep(0.1, 0.35, Nh[:, 0])
    pig = np.maximum(pig, 0.65 * (1.0 - smoothstep(0.25, 0.55, lipd)) * lipf)
    d_lac = dm.get("lacrimal", np.full(n, 1e3))
    pig = np.maximum(pig, 0.45 * (1.0 - smoothstep(-0.1, 0.4, d_lac + 0.3 * jit)))
    pig = np.where(earm, 0.0, pig)
    lipm = (1.0 - smoothstep(0.25, 0.45, lipd)) * lipf
    conch = inner * (1.0 - smoothstep(0.0, 0.25, ear_t)) * (1.0 - smoothstep(0.45, 0.9, au))
    ear_in = np.where(inner, 1.0 - 0.5 * smoothstep(0.88, 0.99, au), np.where(back, 0.5, 0.0))
    ear_in = np.maximum(ear_in, cup)
    pig = np.maximum(pig, np.maximum(0.55 * conch, 0.55 * cup))
    vessel = np.where(inner, v8.ear_vessels(ear_t, ear_u), 0.0)

    # ---- groom: length (mm)
    num = np.zeros(n)
    den = np.full(n, 1e-6)
    for (c, Lk, sig) in HEAD_LENGTH_KEYS_V10:
        cx = c[0] + (mz if c[0] >= 100 else 0.0)
        for s in ((1.0, -1.0) if c[1] else (1.0,)):
            d2 = ((x - cx) ** 2 + (y - c[1] * s) ** 2 + (z - c[2]) ** 2) / (sig * sig)
            w = np.exp(-d2)
            num += w * Lk
            den += w
    headL = num / den
    headw = np.clip(den * 1.5, 0.0, 1.0)
    neckm = smoothstep(-45.0, -95.0, zw) * (1.0 - smoothstep(20.0, 60.0, x))
    headw = headw * (1.0 - neckm)
    frontn = smoothstep(-0.2, 0.4, Nw[:, 0])
    ruff = _bump(zw, -235.0, -110.0) * frontn
    neck = _bump(zw, -160.0, -55.0)
    nape_b = smoothstep(-0.25, -0.65, Nw[:, 0]) * (1.0 - smoothstep(40.0, 80.0, np.abs(yw)))
    # the neck coat stays full on the sides (round 7 cut it by 70 % there,
    # which, with the narrower neck, made the stalk)
    bodyL = 14.0 + 5.0 * ruff + 6.0 * neck + 3.0 * smoothstep(-150.0, -300.0, zw) - 5.0 * neck * nape_b
    arm = smoothstep(70.0, 100.0, ay) * smoothstep(-150.0, -210.0, zw)
    bodyL = bodyL * (1.0 - 0.30 * arm)
    Lh = headL * headw + bodyL * (1.0 - headw)
    # periocular: 2.2 mm at the margin, lengthening outward, lying flat
    lcap = 2.2 + 0.32 * np.maximum(d_fis - 0.5, 0.0)
    Lh = np.where(d_fis < 14.0, np.minimum(Lh, lcap), Lh)
    # bridge hair over the planum's top edge: short, overlapping the edge
    top_edge = (1.0 - smoothstep(0.6, 2.6, d_leather)) * (d_leather > -0.4) * smoothstep(v9.leather_centre() - 1.0, v9.leather_centre() + 2.0, z) * (x > v6.NOSE_X0 - 6.0)
    Lh = Lh * (1.0 - top_edge) + 1.5 * top_edge
    # chin and under the jaw: short, flat (judged: "a goatee")
    chin_m = (1.0 - smoothstep(14.0, 32.0, ay)) * smoothstep(-28.0, -40.0, z) * smoothstep(85.0 + mz, 105.0 + mz, x)
    Lh = Lh * (1.0 - chin_m) + np.minimum(Lh, 4.2) * chin_m
    # pinna and fillet
    rimz = smoothstep(0.86, 0.98, au)
    rn1 = v9.rim_noise(Pw, 61.0)
    L_back = 3.2 + 2.6 * (1.0 - smoothstep(0.08, 0.75, ear_t))
    pocket = _bump(ear_t, 0.10, 0.30) * smoothstep(0.55, 0.80, ear_u)
    L_back = L_back * (1.0 - 0.35 * pocket)
    L_back = L_back * (1.0 - rimz) + L_back * (0.75 + 0.35 * rn1) * rimz
    L_back = L_back + (Lh - L_back) * np.clip(flare, 0.0, 1.0)
    lower = 1.0 - smoothstep(0.30, 0.55, ear_t)
    low_med = (1.0 - smoothstep(-0.55, -0.25, ear_u)) * (1.0 - smoothstep(0.40, 0.62, ear_t))
    L_in = (1.8 + 1.2 * lower + 0.8 * low_med) * (1.0 - rimz) + (2.6 + 0.8 * rn1) * rimz
    L = np.where(earm, np.where(inner, L_in, L_back), Lh)
    L = np.where(cup > 0.5, 2.4, L)
    L = L * (0.94 + 0.12 * v6.fbm(Pw, 0.012, 2, 2.0))
    # lift (deg): flat head coat, a standing neck ruff
    lift_h = 3.5 + 1.5 * smoothstep(40.0, 80.0, z) * (1 - np.clip(-zw / 100.0, 0, 1))
    throat_front = smoothstep(0.2, 0.7, Nw[:, 0])
    lift_b = 10.0 + 2.0 * ruff + 4.0 * neck * (1.0 - 0.8 * throat_front) * (1.0 - 0.7 * nape_b) - 3.0 * arm
    hb = np.maximum(smoothstep(-55.0, -125.0, zw), neckm)
    lift = lift_h * (1.0 - hb) + lift_b * hb
    wper = 1.0 - smoothstep(2.0, 8.0, np.maximum(d_fis, 0.0))
    lift = lift * (1.0 - wper) + 1.5 * wper
    lift = lift * (1.0 - chin_m) + np.minimum(lift, 2.5) * chin_m
    lift_ear = np.where(inner, (16.0 + 10.0 * low_med) * (1.0 - rimz) + 4.0 * rimz, 2.0 + 2.5 * rimz)
    lift = np.where(earm, lift_ear + (lift - lift_ear) * np.clip(flare, 0.0, 1.0), lift)
    lift = np.where(cup > 0.5, 20.0, lift)
    # density
    density = np.clip(7.0 / np.maximum(L, 1.0), 0.35, 1.0)
    deep = (1.0 - smoothstep(-0.05, 0.05, ear_t)) * (1.0 - smoothstep(0.45, 0.7, au))
    inner_d = (0.14 + 0.22 * lower + 0.14 * low_med) * (1.0 - 0.6 * deep)
    inner_d = inner_d * (1.0 - rimz) + 0.85 * rimz
    back_d = (0.80 - 0.10 * smoothstep(0.6, 1.0, ear_t)) * (1.0 - rimz) + 0.72 * rimz
    back_d = back_d + (1.0 - back_d) * np.clip(flare, 0.0, 1.0)
    density = np.where(earm, np.where(inner, inner_d, back_d), density)
    density = np.where(cup > 0.5, 0.22, density)
    density = density * smoothstep(-598.0, -585.0, zw)
    # sharp exclusions (fur mask): fur roots from ~0.45 mm off the lid margin;
    # the planum's top edge is broken up so the bridge coat overlaps it
    topw = smoothstep(-2.0, 2.0, z - 2.0)
    nose_ex = (1.0 - smoothstep(-0.25, 0.25, d_leather + 0.45 * topw + 0.40 * jit * topw)) * smoothstep(v6.NOSE_X0 - 3.0, v6.NOSE_X0 + 1.0, x) * smoothstep(-0.25, 0.05, Nh[:, 0])
    excl = (1.0 - nose_ex) * (1.0 - lipm) * smoothstep(0.30, 0.50, d_fis)
    excl = excl * np.where(x > v6.NOSE_X0 - 4.0, smoothstep(0.0, 0.8, nost + 0.5), 1.0)
    excl = excl * (1.0 - 0.85 * (1.0 - smoothstep(-0.1, 0.2, fol_d)) * on_pad)
    excl = np.where(earm, 1.0, excl)
    # layer weights (sum to 1): head (face, crown, cheeks, chin, inner ear,
    # concha), body (neck, torso), chest (bib), ear back (pinna back and
    # fillet); the head/body transition runs over 70 mm
    w_ear = back.astype(float)
    w_chest = (~earm) * smoothstep(-100.0, -140.0, zw) * smoothstep(-0.05, 0.45, Nw[:, 0]) * (1.0 - smoothstep(60.0, 85.0, np.abs(yw)))
    # the neck coat belongs to the body layer from high on the nape (round-8
    # test frames: long head-layer hair lying flat there read as a pale sheen band)
    w_body = (~earm) * smoothstep(-35.0, -100.0, zw) * (1.0 - w_chest)
    w_head = np.clip(1.0 - w_ear - w_chest - w_body, 0.0, 1.0) * (~back)
    return dict(white=np.clip(white, 0, 1), stripe=np.clip(stripe, 0, 1), pale=pale, nose=nose, pig=np.clip(pig, 0, 1), ear_inner=ear_in,
                length=L * MM, density=np.clip(density, 0, 1), excl=np.clip(excl, 0, 1), lift=lift, d_fis=d_fis, lip=lipm,
                vessel=np.clip(vessel, 0, 1), rim=np.clip(np.where(earm, smoothstep(0.93, 0.995, au), rim), 0, 1), follicle=np.clip(follicle, 0, 1),
                cup=cup, near_ear=ear_near_weight_v10(Ph), flare=flare,
                w_head=w_head, w_body=w_body, w_chest=w_chest, w_ear=w_ear,
                w_face=w_head, w_ruff=np.zeros(n))


def fur_direction_v10(Pw, Nw, ex=None):
    """Round-8 flow: round 7's field (v8 face / pads / eyes / ears / body)
    with the ear-base blend widened to ~40 mm (one continuous flow onto the
    fillet and up the ear back), the ear-back hair near both margins turned
    a little outward so it wraps 1-2 mm over the edge (no bare rim), and
    the body coat over the shoulders combed down and back instead of out
    to the sides (judged: 'epaulette-like tufts with a horizontal fringe')."""
    Pw = np.asarray(Pw, float)
    Nw = np.asarray(Nw, float)
    n = len(Pw)
    is_ear, ear_t, ear_u, ear_face = v6.ex_arrays(n, ex)
    earm = is_ear > 0.5
    t = v8.fur_direction_v8(Pw, Nw, ex)
    Ph = Pw @ v6.head_R()
    sy = np.where(Ph[:, 1] >= 0, 1.0, -1.0)
    near_e = ear_behind_weight_v10(Ph)
    for s in (1.0, -1.0):
        F = v6.ear_frame(s)
        ax = F[:, 2] @ v6.head_R().T
        lat = (F[:, 1] * s) @ v6.head_R().T
        m = earm & (sy == s)
        if m.any():
            base = A.ear_base * np.array([1.0, s, 1.0])
            tip_w = (base + F @ np.array([-6.0 * MM, 0.0, A.ear_h])) @ v6.head_R().T
            dt = tip_w[None, :] - Pw[m]
            dt /= np.linalg.norm(dt, axis=1, keepdims=True) + 1e-9
            rim = smoothstep(0.80, 0.98, np.abs(ear_u[m]))[:, None]
            out_ = np.sign(ear_u[m])[:, None] * lat[None, :]
            backm = (ear_face[m] < 0.2)[:, None]
            k_out = np.where(backm, 0.35, 0.30)
            t[m] = dt * (1.0 - k_out * rim) + out_ * k_out * rim
        mh = (~earm) & (sy == s)
        if mh.any():
            wn = (0.75 * near_e[mh])[:, None]
            t[mh] = t[mh] * (1.0 - wn) + ax[None, :] * wn
    # the short bridge coat just above the planum's top edge lies DOWN over
    # the edge (judged: 'a hard edge where the top meets the fur')
    Ph3 = Ph / MM
    near_n = Ph3[:, 0] > v6.NOSE_X0 - 6.0
    if near_n.any():
        q2 = np.stack([Ph3[near_n, 1], Ph3[near_n, 2]], -1)
        dl = v6.sd_poly2d(q2, v6.leather_poly())
        zc = v9.leather_centre()
        band = (1.0 - smoothstep(0.6, 2.6, dl)) * (dl > -0.4) * smoothstep(zc - 1.0, zc + 2.0, Ph3[near_n, 2])
        if band.any():
            tgt = (np.array([v6.NOSE_X0 + 30.0, 0.0, zc - 6.0]) * MM) @ v6.head_R().T
            dv = tgt[None, :] - Pw[near_n]
            dv /= np.linalg.norm(dv, axis=1, keepdims=True) + 1e-9
            t[near_n] = t[near_n] * (1.0 - band[:, None]) + dv * band[:, None]
    zw = Pw[:, 2] / MM
    # shoulders: down and back
    sh = (smoothstep(45.0, 80.0, np.abs(Pw[:, 1] / MM)) * _bump(zw, -250.0, -120.0) * (~earm))[:, None]
    if sh.any():
        db = np.array([-0.45, 0.0, -1.0])
        db = db / np.linalg.norm(db)
        t = t * (1.0 - 0.8 * sh) + db[None, :] * 0.8 * sh
    hb = smoothstep(-70.0, -130.0, zw) * (~earm)
    if hb.any():
        a = (v6.fbm(Pw, 0.05, 2, 41.0) - 0.5) * 0.45 * hb
        b = np.cross(Nw, t)
        t = t * np.cos(a)[:, None] + b * np.sin(a)[:, None]
    t = t - np.sum(t * Nw, 1, keepdims=True) * Nw
    t /= np.linalg.norm(t, axis=1, keepdims=True) + 1e-9
    return t


def grow_guides_v10(pos, nrm, ex, npts, rng, length_scale=None, lift_add=None, lay=0.8):
    """v9's guide growth with a flatter lay on the head (0.88) so the short
    head coat lies down, and a milder per-guide bend there."""
    f = v6.coat_fields(pos, nrm, ex)
    tdir = v6.fur_direction(pos, nrm, ex)
    n = len(pos)
    Lg = f["length"] * rng.uniform(0.9, 1.1, n)
    if length_scale is not None:
        Lg = Lg * length_scale
    a0 = np.radians(f["lift"] + (0.0 if lift_add is None else lift_add))
    side = np.cross(nrm, tdir)
    g = np.array([0.0, 0.0, -1.0])
    gt = g[None] - (nrm @ g)[:, None] * nrm
    droop = np.clip((Lg / MM - 8.0) / 30.0, 0.0, 0.5)
    chest = f["w_chest"]
    body = f["w_body"]
    head = f["w_head"]
    wave_amp = rng.uniform(0.03, 0.09, n) * (1.0 - chest) * (1.0 - 0.5 * head)
    freq = rng.uniform(0.6, 1.3, n)
    phase = rng.random(n) * 2 * math.pi
    bend = rng.normal(0.0, 0.06, n) * (1.0 + 1.2 * body) + chest * rng.choice([-1.0, 1.0], n) * rng.uniform(0.18, 0.34, n)
    is_ear = ex["is_ear"] > 0.5 if ex is not None else np.zeros(n, bool)
    lay_v = np.where(is_ear, 0.95, lay + (0.88 - lay) * head * (1.0 - smoothstep(8.0 * MM, 14.0 * MM, Lg)))
    strands = np.zeros((n, npts, 3))
    p = pos + nrm * 0.05 * MM
    strands[:, 0] = p
    seg = Lg / (npts - 1)
    for k in range(1, npts):
        sm = (k - 0.5) / (npts - 1)
        a = a0 * (1.0 - lay_v * sm) + math.radians(1.0)
        d = (tdir * np.cos(a)[:, None] + nrm * np.sin(a)[:, None]
             + side * (bend * sm * sm + wave_amp * np.sin(2 * math.pi * freq * sm + phase))[:, None]
             + gt * (droop * sm * sm)[:, None])
        d /= np.linalg.norm(d, axis=1, keepdims=True)
        p = p + d * seg[:, None]
        strands[:, k] = p
    return strands, f


# ---------------------------------------------------------------------------
# Skin cage attributes and the groom (round 8)
# ---------------------------------------------------------------------------

def build_skin_v10(coll):
    """v6.build_skin (the round-8 pinnae carry ear_flare) plus the per-layer
    density attributes."""
    dense, tgt, cage = v9._V6_BUILD_SKIN(coll)
    co, nr = v6.mesh_arrays(cage.data)
    ex = {k: v6.attr_array(cage.data, k) for k in v6.EAR_ATTRS}
    f = coat_fields_v10(co, nr, ex)
    for nm, key in (("fd_head", "w_head"), ("fd_body", "w_body"), ("fd_chest", "w_chest"), ("fd_ear", "w_ear")):
        a = cage.data.attributes.new(nm, "FLOAT", "POINT")
        a.data.foreach_set("value", (f["density"] * f[key]).astype(np.float32))
    a = cage.data.attributes.new("fd_under", "FLOAT", "POINT")
    a.data.foreach_set("value", (f["density"] * (1.0 - 0.6 * f["w_ear"]) * (1.0 - 0.7 * f["cup"])).astype(np.float32))
    return dense, tgt, cage


GUARD_LAYERS_V10 = [
    # one head layer (face, crown, cheeks, chin, inner ear) with light, fine
    # clumping: round 7's separate face and ruff layers met at hard edges
    ("CatBaseV6_Fur_Head", "fd_head", ((0.50, 1.5 * MM, 0.35, 0.10 * MM), (0.35, 0.7 * MM, 0.25, 0.04 * MM)), 0.10 * MM, 260.0, 0.05 * MM, (0.82, 1.18), 0.058 * MM),
    ("CatBaseV6_Fur_Body", "fd_body", ((0.80, 6.5 * MM, 0.45, 0.6 * MM), (0.55, 2.4 * MM, 0.35, 0.18 * MM), (0.30, 0.8 * MM, 0.25, 0.0)), 0.28 * MM, 90.0, 0.10 * MM, (0.7, 1.3), 0.066 * MM),
    ("CatBaseV6_Fur_Chest", "fd_chest", ((0.88, 5.5 * MM, 0.60, 0.5 * MM), (0.60, 2.0 * MM, 0.40, 0.15 * MM)), 0.22 * MM, 110.0, 0.08 * MM, (0.75, 1.3), 0.064 * MM),
    ("CatBaseV6_Fur_EarBack", "fd_ear", ((0.48, 1.4 * MM, 0.32, 0.08 * MM), (0.32, 0.6 * MM, 0.25, 0.0)), 0.06 * MM, 280.0, 0.04 * MM, (0.82, 1.18), 0.052 * MM),
]


def build_groom_v10(coll, skin, images, n_guides):
    """Round 8 groom: four guard layers (head, body, chest, ear back) sharing
    one guide set, one material and one flow field; the undercoat; stray
    guard hairs (fewer and shorter on the head) and fly-aways on the neck and
    body only (judged round 7: the head read as a fur hood)."""
    rng = np.random.default_rng(v6.RNG_SEED)
    S = v6.evaluated_surface(skin)
    log("groom surface tris", len(S["tv"]))

    def wfn(c, n, ex):
        f = v6.coat_fields(c, n, ex)
        return f["density"] * np.maximum(f["excl"], 0.05) / np.maximum(f["length"], 2.5 * MM)

    pos, nrm, uv, ex = v6.sample_roots(S, n_guides, wfn, rng)
    strands, f = grow_guides_v10(pos, nrm, ex, 8, rng)
    v6.load_hair_assets()
    v6.length_jitter_group()
    layers = []
    cull = v6.eye_cull_group()
    gdata = v6.make_curves("CatBaseV6_Fur_GuardGuides", strands, 0.064 * MM, 0.016 * MM, coll, uv=uv, surface=skin)
    gdata_ob = gdata
    gdata = gdata.data
    gdata.materials.append(hair_material_v10("M_CatBaseV6_Fur_Guard", images, False, tip_alpha=True))
    bpy.data.objects.remove(gdata_ob, do_unlink=True)
    for li, (name, attr, clumps, noise, nscale, frizz, jitter, r0) in enumerate(GUARD_LAYERS_V10):
        ob = v6.link(bpy.data.objects.new(name, gdata), coll)
        ob.parent = skin
        seed = 3 + 10 * li
        v6.gn_mod(ob, "Interpolate Hair Curves", Follow_Surface_Normal=True, Part_by_Mesh_Islands=True, Density=5.0e6,
                  Density_Mask=("ATTR", attr), Mask_Texture=images["furmask"], Interpolation_Guides=4, Viewport_Amount=0.05, Seed=seed)
        v6.gn_mod(ob, "CatBaseV6 Length Jitter", Min=jitter[0], Max=jitter[1], Seed=seed + 20)
        for ci, (cf, cd_, csh, spread) in enumerate(clumps):
            v6.gn_mod(ob, "Clump Hair Curves", Factor=cf, Shape=csh, Tip_Spread=spread, Existing_Guide_Map=False,
                      Guide_Distance=cd_, Guide_Mask=1.0, Preserve_Length=True, Seed=11 + 17 * ci + seed)
        v6.gn_mod(ob, "Hair Curves Noise", Factor=1.0, Distance=noise, Shape=0.5, Scale=nscale, Scale_along_Curve=1.0,
                  Offset_per_Curve=1.0, Seed=9 + seed, Preserve_Length=True)
        v6.gn_mod(ob, "Frizz Hair Curves", Factor=1.0, Distance=frizz, Shape=0.7, Seed=19 + seed, Preserve_Length=True)
        v6.gn_mod(ob, "Shrinkwrap Hair Curves", Surface=skin, Factor=1.0, Offset_Distance=0.12 * MM, Smoothing_Steps=2, Lock_Roots=True)
        v6.gn_mod(ob, "Set Hair Curve Profile", Replace_Radius=True, Radius=r0, Shape=-0.5, Factor_Min=0.0, Factor_Max=1.0)
        m_ = ob.modifiers.new("CatBaseV6 Eye Cull", "NODES")
        m_.node_group = cull
        layers.append(ob)
    ob = v6.make_curves("CatBaseV6_Fur_Under", strands, 0.030 * MM, 0.0075 * MM, coll, uv=uv, surface=skin)
    ob.parent = skin
    ob.data.materials.append(hair_material_v10("M_CatBaseV6_Fur_Under", images, True, tip_alpha=False))
    v6.gn_mod(ob, "Interpolate Hair Curves", Follow_Surface_Normal=True, Part_by_Mesh_Islands=True, Density=6.0e6,
              Density_Mask=("ATTR", "fd_under"), Mask_Texture=images["furmask"], Interpolation_Guides=4, Viewport_Amount=0.05, Seed=7)
    v6.gn_mod(ob, "CatBaseV6 Length Jitter", Min=0.7, Max=1.3, Seed=27)
    v6.gn_mod(ob, "Trim Hair Curves", Scale_Uniform=False, Replace_Length=False, Length_Factor=0.55, Random_Offset=0.0, Pin_at_Parameter=0.0, Seed=13)
    v6.gn_mod(ob, "Clump Hair Curves", Factor=0.30, Shape=0.3, Tip_Spread=0.0, Existing_Guide_Map=False, Guide_Distance=2.0 * MM, Guide_Mask=1.0,
              Preserve_Length=True, Seed=11)
    v6.gn_mod(ob, "Hair Curves Noise", Factor=1.0, Distance=0.35 * MM, Shape=0.5, Scale=520.0, Scale_along_Curve=1.0, Offset_per_Curve=1.0, Seed=5,
              Preserve_Length=True)
    v6.gn_mod(ob, "Frizz Hair Curves", Factor=1.0, Distance=0.16 * MM, Shape=0.7, Seed=15, Preserve_Length=True)
    v6.gn_mod(ob, "Shrinkwrap Hair Curves", Surface=skin, Factor=1.0, Offset_Distance=0.12 * MM, Smoothing_Steps=2, Lock_Roots=True)
    v6.gn_mod(ob, "Set Hair Curve Profile", Replace_Radius=True, Radius=0.030 * MM, Shape=-0.5, Factor_Min=0.0, Factor_Max=1.0)
    m_ = ob.modifiers.new("CatBaseV6 Eye Cull", "NODES")
    m_.node_group = cull
    layers.append(ob)
    # stray guard hairs: fewer and shorter on the head
    n_stray = 9000
    sp_, sn_, suv, sex = v6.sample_roots(S, n_stray, wfn, rng)
    fs = v6.coat_fields(sp_, sn_, sex)
    ls = rng.uniform(1.10, 1.40, n_stray) * (1.0 - 0.15 * fs["w_head"])
    st, _ = grow_guides_v10(sp_, sn_, sex, 10, rng, length_scale=ls, lift_add=rng.uniform(1.0, 5.0, n_stray) * (1.0 - 0.6 * fs["w_head"]), lay=0.78)
    keep = (sex["is_ear"] < 0.5) & (fs["d_fis"] > 4.0) & (fs["excl"] > 0.95) & (fs["cup"] < 0.3)
    keep &= rng.random(n_stray) < (1.0 - 0.7 * fs["w_head"])
    st, suv = st[keep], suv[keep]

    def wfly(c, n, ex):
        f = v6.coat_fields(c, n, ex)
        zw = c[:, 2] / MM
        sil = f["w_body"] * (1.0 - smoothstep(-160.0, -230.0, zw)) + 0.3 * f["w_chest"]
        return f["density"] * np.maximum(f["excl"], 0.0) * sil

    n_fly = 1500
    fp, fn_, fuv, fex = v6.sample_roots(S, n_fly, wfly, rng)
    ft, _ = grow_guides_v10(fp, fn_, fex, 10, rng, length_scale=rng.uniform(1.35, 1.9, n_fly), lift_add=rng.uniform(5.0, 13.0, n_fly), lay=0.6)
    ffs = v6.coat_fields(fp, fn_, fex)
    fk = (fex["is_ear"] < 0.5) & (ffs["d_fis"] > 6.0) & (ffs["excl"] > 0.95)
    ft, fuv = ft[fk], fuv[fk]
    t = np.linspace(0, 1, st.shape[1])
    radii = np.concatenate([np.repeat(((0.068 * MM) * (1 - t) ** 1.3 + 0.008 * MM)[None], len(st), 0),
                            np.repeat(((0.050 * MM) * (1 - t) ** 1.2 + 0.006 * MM)[None], len(ft), 0)])
    ob = v6.make_curves("CatBaseV6_Fur_Stray", np.concatenate([st, ft]), 0, 0, coll, uv=np.concatenate([suv, fuv]), surface=skin, radii=radii)
    ob.parent = skin
    ob.data.materials.append(hair_material_v10("M_CatBaseV6_Fur_Stray", images, False))
    m_ = ob.modifiers.new("CatBaseV6 Eye Cull", "NODES")
    m_.node_group = cull
    layers.append(ob)
    log(f"strays {len(st)} + fly-aways {len(ft)}")
    guides = v6.make_curves("CatBaseV6_Fur_Guides", strands, 0.1 * MM, 0.05 * MM, coll, uv=uv, surface=skin)
    guides.parent = skin
    guides.hide_render = True
    guides.hide_viewport = True
    return layers, guides


FURN_COLOUR = (0.70, 0.68, 0.62)


def build_inner_ear_furnishings_v10(coll, skin, images):
    """Round 8 furnishings (judged round 7: 'a single white feather along the
    upper-medial margin ... the lower concha bare ... a comb of parallel
    brush strands ... a mohawk crest'). Tufts of 3-7 pale hairs rooted

    - on the conchal floor (head skin inside the carved concha) and the
      lower third of the inner face, 3x denser there than round 7,
    - at the base of the medial margin,
    - in a lateral-base tuft by the antitragus,
    - and short tip hairs (7-11 mm) at the apex,

    that stream up and OUT past the opening, partly covering the base, each
    tuft with 15-25 deg of direction jitter and its own clump."""
    rng = np.random.default_rng(v6.RNG_SEED + 12)
    S = v6.evaluated_surface(skin)
    cupw = cup_weight_v10(S["co"])

    def wfn(c, n, ex):
        cp = cup_weight_v10(c) * (1.0 - ex["is_ear"])
        front = ex["is_ear"] * smoothstep(0.2, 0.6, ex["ear_face"])
        t, u = ex["ear_t"], ex["ear_u"]
        low = (1.0 - smoothstep(0.30, 0.42, t)) * smoothstep(-0.12, 0.0, t)
        med = (1.0 - smoothstep(-0.80, -0.50, u)) * _bump(t, 0.0, 0.45)
        lat = smoothstep(0.45, 0.65, u) * (1.0 - smoothstep(0.90, 0.99, u)) * _bump(t, -0.02, 0.18)
        tipz = smoothstep(0.88, 0.96, t)
        return front * (3.0 * low + 1.6 * med + 1.8 * lat + 0.35 * tipz + 0.25) + 3.2 * cp

    n_tuft = 1650
    cpos, cnrm, cuv, cex = v6.sample_roots(S, n_tuft, wfn, rng)
    npts = 12
    strands, uvs, radii = [], [], []
    tt = np.linspace(0, 1, npts)
    for i in range(n_tuft):
        s = 1.0 if (cpos[i] @ v6.head_R())[1] > 0 else -1.0
        F = v6.ear_frame(s)
        up = F[:, 2] @ v6.head_R().T
        fwd = F[:, 0] @ v6.head_R().T
        lat = F[:, 1] * s @ v6.head_R().T
        eu = cex["ear_u"][i]
        et = cex["ear_t"][i]
        on_ear = cex["is_ear"][i] > 0.5
        nn = cnrm[i]
        if on_ear and et > 0.86:
            d = 0.85 * up + 0.35 * fwd + 0.15 * nn
            Lt = rng.uniform(7.0, 11.0) * MM
            k = int(rng.integers(2, 4))
        elif on_ear and eu > 0.45:
            d = 0.60 * up - 0.45 * lat + 0.55 * fwd + 0.25 * nn
            Lt = rng.uniform(12.0, 20.0) * MM
            k = int(rng.integers(3, 7))
        elif on_ear and eu < -0.45:
            d = 0.62 * up + 0.55 * lat + 0.50 * fwd + 0.25 * nn
            Lt = rng.uniform(18.0, 30.0) * MM
            k = int(rng.integers(3, 7))
        else:
            # conchal floor and lower inner face: up and out of the opening
            d = 0.70 * up + 0.70 * fwd + 0.20 * lat * rng.normal() + 0.20 * nn
            Lt = rng.uniform(16.0, 28.0) * MM
            k = int(rng.integers(4, 8))
        d /= np.linalg.norm(d) + 1e-9
        # 15-25 deg tuft direction jitter
        jit_ang = math.radians(rng.uniform(15.0, 25.0))
        ax_ = np.cross(d, rng.normal(size=3))
        ax_ /= np.linalg.norm(ax_) + 1e-9
        d = d * math.cos(jit_ang) + np.cross(ax_, d) * math.sin(jit_ang)
        curl = rng.normal(0, 0.10, 3)
        tipp = None
        for _ in range(k):
            off = rng.normal(0.0, 0.45 * MM, 3)
            off -= (off @ nn) * nn
            p = cpos[i] + off - nn * 0.15 * MM
            fan = rng.normal(0.0, 0.07, 3)
            Lh = Lt * rng.uniform(0.7, 1.1)
            c2 = curl + rng.normal(0, 0.04, 3)
            pts = [p.copy()]
            for kk in range(1, npts):
                s_ = kk / (npts - 1)
                dd = d + fan * s_ ** 1.2 + c2 * s_ + up * 0.25 * s_ - np.array([0.0, 0.0, 0.12]) * s_ * s_
                dd /= np.linalg.norm(dd)
                p = p + dd * Lh / (npts - 1)
                pts.append(p.copy())
            pts = np.array(pts)
            # clump: tips drawn together
            if tipp is None:
                tipp = pts[-1].copy()
            pts = pts + (tipp - pts[-1])[None, :] * (0.35 * tt ** 2)[:, None]
            strands.append(pts)
            uvs.append(cuv[i])
            radii.append((0.055 * MM) * (1 - tt) ** 1.0 + 0.006 * MM)
    strands = np.array(strands)
    uv = np.array(uvs)
    radii = np.array(radii)
    ob = v6.make_curves("CatBaseV6_Fur_EarFurnishings", strands, 0, 0, coll, uv=uv, surface=skin, radii=radii)
    ob.parent = skin
    m, nt = v6.new_mat("M_CatBaseV6_EarFurnishingV10")
    out = N(nt, "ShaderNodeOutputMaterial", (900, 0))
    hb = N(nt, "ShaderNodeBsdfHairPrincipled", (300, 0))
    hb.parametrization = "COLOR"
    hb.model = "CHIANG"
    info = N(nt, "ShaderNodeHairInfo", (-400, 0))
    rj = N(nt, "ShaderNodeMapRange", (-200, 0))
    L(nt, info.outputs["Random"], rj.inputs["Value"])
    rj.inputs["To Min"].default_value = 0.80
    rj.inputs["To Max"].default_value = 1.05
    col = N(nt, "ShaderNodeVectorMath", (0, 0))
    col.operation = "SCALE"
    col.inputs[0].default_value = FURN_COLOUR
    L(nt, rj.outputs["Result"], col.inputs["Scale"])
    L(nt, col.outputs["Vector"], hb.inputs["Color"])
    hb.inputs["Roughness"].default_value = 0.34
    hb.inputs["Radial Roughness"].default_value = 0.4
    hb.inputs["Coat"].default_value = 0.0
    hb.inputs["IOR"].default_value = 1.3
    tip = N(nt, "ShaderNodeMapRange", (300, -300))
    L(nt, info.outputs["Intercept"], tip.inputs["Value"])
    tip.inputs["From Min"].default_value = 0.84
    tip.inputs["From Max"].default_value = 1.0
    tip.inputs["To Min"].default_value = 0.0
    tip.inputs["To Max"].default_value = 0.65
    trn = N(nt, "ShaderNodeBsdfTransparent", (500, -200))
    mx = N(nt, "ShaderNodeMixShader", (700, 0))
    L(nt, tip.outputs["Result"], mx.inputs["Fac"])
    L(nt, hb.outputs["BSDF"], mx.inputs[1])
    L(nt, trn.outputs["BSDF"], mx.inputs[2])
    L(nt, mx.outputs["Shader"], out.inputs["Surface"])
    ob.data.materials.append(m)
    log(f"ear furnishings v10: {n_tuft} tufts, {len(strands)} hairs")
    return ob


# ---------------------------------------------------------------------------
# Materials (round 8)
# ---------------------------------------------------------------------------

def hair_material_v10(name, images, under=False, tip_alpha=True):
    """Round 8 hair (judged round 7: 'the ground colour is warm olive-brown
    rather than cool silver-grey'): every ground hair is agouti-banded grey
    root / pale silver band / dark tip, cool and near-neutral; stripe hairs
    are solid near-black (the per-hair binary stripe choice gives the crisp
    mackerel edges); white is a cool off-white. Built on round 6's node
    layout (hair_material_v8), with new ramp colours."""
    m = v8.hair_material_v8(name, images, under, tip_alpha)
    nt = m.node_tree
    ramps = [nd for nd in nt.nodes if nd.type == "VALTORGB"]
    ramps.sort(key=lambda nd: -nd.location.y)
    if not under:
        stops = [
            [(0.0, (0.060, 0.061, 0.064)), (0.24, (0.085, 0.086, 0.089)), (0.34, (0.36, 0.355, 0.335)),
             (0.58, (0.40, 0.395, 0.375)), (0.67, (0.040, 0.040, 0.041)), (1.0, (0.024, 0.024, 0.025))],
            [(0.0, (0.28, 0.28, 0.27)), (0.25, (0.52, 0.515, 0.49)), (0.75, (0.56, 0.55, 0.525)), (0.90, (0.38, 0.375, 0.36)), (1.0, (0.28, 0.28, 0.27))],
            [(0.0, (0.040, 0.040, 0.041)), (0.30, (0.026, 0.026, 0.027)), (1.0, (0.021, 0.021, 0.022))],
        ]
        white = (0.66, 0.655, 0.635)
    else:
        stops = [[(0.0, (0.090, 0.090, 0.092)), (1.0, (0.22, 0.215, 0.205))],
                 [(0.0, (0.30, 0.295, 0.285)), (1.0, (0.42, 0.415, 0.40))],
                 [(0.0, (0.055, 0.055, 0.056)), (1.0, (0.040, 0.040, 0.041))]]
        white = (0.50, 0.495, 0.48)
    for r, st in zip(ramps, stops):
        cr = r.color_ramp
        while len(cr.elements) > 2:
            cr.elements.remove(cr.elements[1])
        cr.elements[0].position = st[0][0]
        cr.elements[0].color = (*st[0][1], 1)
        cr.elements[1].position = st[-1][0]
        cr.elements[1].color = (*st[-1][1], 1)
        for p_, col in st[1:-1]:
            e = cr.elements.new(p_)
            e.color = (*col, 1)
    for nd in nt.nodes:
        if nd.type == "MIX" and getattr(nd, "data_type", "") == "RGBA":
            b_ = nd.inputs[7]
            if not b_.is_linked and tuple(round(c_, 3) for c_ in b_.default_value[:3]) in ((0.62, 0.6, 0.565), (0.47, 0.455, 0.43)):
                b_.default_value = (*white, 1.0)
    return m


EAR_SKIN_V10 = (0.37, 0.295, 0.285)  # 20 % less saturated toward grey-pink (round 7: 0.40, 0.29, 0.275)
LEATHER_CENTRE_V10 = (0.47, 0.285, 0.265)  # lighter, desaturated centre
LEATHER_RIM_V10 = (0.20, 0.095, 0.088)  # liver-pink rim


def skin_material_v10(images):
    """Round 9's skin shader (skin_material_v9) with round-8 values: greyer
    inner-ear skin; a liver-pink leather rim and lighter centre, 20 % less
    saturated; a cobblestone bump 1.6x deeper (it now reads at 1 m); wet
    nares (roughness 0.18 inside the nostrils); the ear subsurface and
    translucency cut at the thick base (ear_t attribute)."""
    v9.EAR_SKIN_V9 = EAR_SKIN_V10
    m = v9.skin_material_v9(images)
    nt = m.node_tree
    nodes = nt.nodes
    for nd in nodes:
        if nd.type == "MIX" and getattr(nd, "data_type", "") == "RGBA":
            a_, b_ = nd.inputs[6], nd.inputs[7]
            av = tuple(round(c_, 3) for c_ in a_.default_value[:3])
            bv = tuple(round(c_, 3) for c_ in b_.default_value[:3])
            if av == (0.34, 0.15, 0.14) and bv == (0.17, 0.07, 0.062):
                a_.default_value = (*LEATHER_CENTRE_V10, 1.0)
                b_.default_value = (*LEATHER_RIM_V10, 1.0)
        if nd.type == "BUMP":
            nd.inputs["Distance"].default_value = 0.00055
        if nd.type == "TEX_VORONOI":
            # cobbles ~0.8 mm and a 2 mm octave (round 7: 0.33 / 0.87 mm,
            # below a pixel at 1 m)
            sc_ = nd.inputs["Scale"].default_value
            nd.inputs["Scale"].default_value = 1250.0 if sc_ > 2000.0 else 520.0
    bs = next(nd for nd in nodes if nd.type == "BSDF_PRINCIPLED")
    # wet nares: Regions G (pigment) x Regions R (nose) -> lower roughness
    reg = next(nd for nd in nodes if nd.type == "TEX_IMAGE" and nd.image is not None and "Regions" in nd.image.name)
    sr = next(l_.to_node for l_ in nt.links if l_.from_node == reg and l_.to_node.type == "SEPARATE_COLOR")
    rough_src = bs.inputs["Roughness"].links[0].from_socket
    wet = N(nt, "ShaderNodeMath", (1500, 400))
    wet.operation = "MULTIPLY"
    L(nt, sr.outputs["Red"], wet.inputs[0])
    L(nt, sr.outputs["Green"], wet.inputs[1])
    mr = N(nt, "ShaderNodeMix", (1650, 300))
    mr.data_type = "FLOAT"
    L(nt, wet.outputs[0], mr.inputs["Factor"])
    L(nt, rough_src, mr.inputs[2])
    mr.inputs[3].default_value = 0.18
    L(nt, mr.outputs[0], bs.inputs["Roughness"])
    # ear SSS / translucency: full on the thin upper pinna, cut at the base
    at = N(nt, "ShaderNodeAttribute", (900, -1100))
    at.attribute_name = "ear_t"
    at.attribute_type = "GEOMETRY"
    fac = N(nt, "ShaderNodeMapRange", (1100, -1100))
    L(nt, at.outputs["Fac"], fac.inputs["Value"])
    fac.inputs["From Min"].default_value = 0.05
    fac.inputs["From Max"].default_value = 0.40
    fac.inputs["To Min"].default_value = 0.25
    fac.inputs["To Max"].default_value = 1.0
    sw = bs.inputs["Subsurface Weight"]
    if sw.links:
        src = sw.links[0].from_socket
        mul = N(nt, "ShaderNodeMath", (1350, -1000))
        mul.operation = "MULTIPLY"
        L(nt, src, mul.inputs[0])
        L(nt, fac.outputs["Result"], mul.inputs[1])
        L(nt, mul.outputs[0], sw)
    mx = next(nd for nd in nodes if nd.type == "MIX_SHADER")
    if mx.inputs["Fac"].links:
        src = mx.inputs["Fac"].links[0].from_socket
        mul2 = N(nt, "ShaderNodeMath", (1600, -1100))
        mul2.operation = "MULTIPLY"
        L(nt, src, mul2.inputs[0])
        L(nt, fac.outputs["Result"], mul2.inputs[1])
        L(nt, mul2.outputs[0], mx.inputs["Fac"])
    return m


def cornea_material_v10():
    """Fresnel-only cornea (judged round 7: 'the horizon reflection cuts
    each cornea at the same height, so the eyes read as milky glass
    marbles'): clear glass at IOR 1.376 plus the corneal Fresnel reflection
    only, no constant floor (round 7 added 0.045 everywhere)."""
    v9.CORNEA_FLOOR = 0.0
    m = v9.cornea_material_v9()
    m.name = "M_CatBaseV6_CorneaV10"
    for nd in m.node_tree.nodes:
        if nd.type == "MATH" and nd.operation == "MULTIPLY_ADD":
            nd.inputs[1].default_value = 1.0
            nd.inputs[2].default_value = 0.0
    return m


def iris_colour_v10(f, rho):
    """Round 7 iris with a darker, wider limbal ring (judged: 'no depth')."""
    col = v9.iris_colour_v9(f, rho)
    ring = smoothstep(0.80, 0.97, rho)[..., None]
    return col * (1.0 - 0.55 * ring) + np.array([0.010, 0.013, 0.018]) * (0.55 * ring)


# ---------------------------------------------------------------------------
# Lid margin sheet and caruncle (round 8)
# ---------------------------------------------------------------------------

def lid_margin_material_v10():
    """Margin sheet: wet at the eye contact (clear coat), then a thin dark
    brown-black margin, then the dark grey periocular skin under the fur (so
    the sheet is not a uniform black outline)."""
    m, nt = v6.new_mat("M_CatBaseV6_LidMarginV10")
    out = N(nt, "ShaderNodeOutputMaterial", (700, 0))
    bs = N(nt, "ShaderNodeBsdfPrincipled", (400, 0))
    at = N(nt, "ShaderNodeAttribute", (-500, 0))
    at.attribute_name = "margin_t"
    cr = N(nt, "ShaderNodeValToRGB", (-200, 200))
    L(nt, at.outputs["Fac"], cr.inputs["Fac"])
    ramp = cr.color_ramp
    ramp.elements[0].position = 0.0
    ramp.elements[0].color = (0.012, 0.010, 0.010, 1)
    ramp.elements[1].position = 1.0
    # beyond ~0.9 mm the sheet is periocular skin under the fur: grey, not
    # black (round-8 test frames: a dark crease line where the sheet met the
    # skin read as a doubled upper lid)
    ramp.elements[1].color = (0.105, 0.102, 0.100, 1)
    e = ramp.elements.new(0.30)
    e.color = (0.016, 0.013, 0.012, 1)
    e = ramp.elements.new(0.55)
    e.color = (0.035, 0.032, 0.030, 1)
    e = ramp.elements.new(0.70)
    e.color = (0.085, 0.082, 0.080, 1)
    # a little value variation along the loop, so the rim is not a uniform line
    tc_ = N(nt, "ShaderNodeTexCoord", (-700, 350))
    nz = N(nt, "ShaderNodeTexNoise", (-500, 350))
    nz.inputs["Scale"].default_value = 900.0
    nz.inputs["Detail"].default_value = 3.0
    L(nt, tc_.outputs["Object"], nz.inputs["Vector"])
    nm = N(nt, "ShaderNodeMapRange", (-300, 350))
    L(nt, nz.outputs["Fac"], nm.inputs["Value"])
    nm.inputs["From Min"].default_value = 0.3
    nm.inputs["From Max"].default_value = 0.7
    nm.inputs["To Min"].default_value = 0.7
    nm.inputs["To Max"].default_value = 1.35
    mulc = N(nt, "ShaderNodeVectorMath", (100, 250))
    mulc.operation = "SCALE"
    L(nt, cr.outputs["Color"], mulc.inputs[0])
    L(nt, nm.outputs["Result"], mulc.inputs["Scale"])
    L(nt, mulc.outputs["Vector"], bs.inputs["Base Color"])
    rr = N(nt, "ShaderNodeMapRange", (-200, -100))
    L(nt, at.outputs["Fac"], rr.inputs["Value"])
    rr.inputs["From Min"].default_value = 0.06
    rr.inputs["From Max"].default_value = 0.22
    rr.inputs["To Min"].default_value = 0.08
    rr.inputs["To Max"].default_value = 0.75
    rr.interpolation_type = "SMOOTHSTEP"
    L(nt, rr.outputs["Result"], bs.inputs["Roughness"])
    cw = N(nt, "ShaderNodeMapRange", (-200, -300))
    L(nt, at.outputs["Fac"], cw.inputs["Value"])
    cw.inputs["From Min"].default_value = 0.05
    cw.inputs["From Max"].default_value = 0.16
    cw.inputs["To Min"].default_value = 0.8
    cw.inputs["To Max"].default_value = 0.0
    cw.interpolation_type = "SMOOTHSTEP"
    L(nt, cw.outputs["Result"], bs.inputs["Coat Weight"])
    bs.inputs["Coat Roughness"].default_value = 0.02
    bs.inputs["Specular IOR Level"].default_value = 0.2
    L(nt, bs.outputs["BSDF"], out.inputs["Surface"])
    return m


def build_lid_margins_v10(coll, parent, n=720):
    """Round 8 lid margin (judged round 7: 'the upper lid margin is
    sawtoothed and notched ... a faceted edge on the lid-skin sheet'; 'a
    smooth hairless grey gasket'): a finely sampled (720) and relaxed
    margin sheet whose inner edge lies on the eye and which then runs OVER
    the lid skin, 0.10 mm above it, out to 2.4 mm before tucking under it,
    so the level-set skin's faceted edge is hidden; its heights come from
    the skin field and are relaxed along the loop. Wet at the contact, a
    ~0.6 mm dark margin, then periocular skin colour under the fur, which
    now grows to within ~0.5 mm of the margin. A tear meniscus runs along
    the lower lid."""
    mat = lid_margin_material_v10()
    tear = bpy.data.materials.get("M_CatBaseV6_Tear")
    objs = []
    A_S = np.array([0.0, 0.2, 0.45, 0.8, 1.3, 1.9, 2.4, 2.9]) * MM
    uu, low = v8.outline_params(n)
    t = uu / 0.999
    for s, tag in ((1.0, "L"), (-1.0, "R")):
        P, Nn = v7.eye_surface_outline(s, n)
        m = len(P)
        cen = P.mean(0)
        # relax the outline itself (a few Laplacian passes) before building
        for _ in range(6):
            P = P + 0.3 * (0.5 * (np.roll(P, 1, 0) + np.roll(P, -1, 0)) - P)
        T = np.roll(P, -1, 0) - np.roll(P, 1, 0)
        T /= np.linalg.norm(T, axis=1, keepdims=True)
        O = np.cross(T, Nn)
        flip = np.sum(O * (P - cen), 1) < 0
        O[flip] *= -1.0
        for _ in range(20):
            O = (np.roll(O, 1, 0) + 2.0 * O + np.roll(O, -1, 0)) / 4.0
        O -= np.sum(O * Nn, 1, keepdims=True) * Nn
        O /= np.linalg.norm(O, axis=1, keepdims=True)
        wf = np.where(low, 0.85, 1.0) * (0.55 + 0.45 * np.sqrt(np.clip(1.0 - t ** 4, 0.0, 1.0)))
        k = 9
        pad = np.r_[wf[-k:], wf, wf[:k]]
        wf = np.convolve(pad, np.ones(2 * k + 1) / (2 * k + 1), mode="same")[k:-k]
        H = np.zeros((m, len(A_S)))
        for j, a in enumerate(A_S):
            B0 = P + O * (a * wf)[:, None]
            lo_ = np.full(m, -0.5 * MM)
            hi_ = np.full(m, 6.0 * MM)
            for _ in range(28):
                mid = 0.5 * (lo_ + hi_)
                inside = v7.exact_skin_sdf(B0 + Nn * mid[:, None]) < 0.0
                lo_ = np.where(inside, mid, lo_)
                hi_ = np.where(inside, hi_, mid)
            H[:, j] = 0.5 * (lo_ + hi_)
        kk = 12
        padH = np.r_[H[-kk:], H, H[:kk]]
        H = np.stack([np.convolve(padH[:, j], np.ones(2 * kk + 1) / (2 * kk + 1), mode="same")[kk:-kk] for j in range(len(A_S))], 1)
        H = np.clip(H, 0.20 * MM, 2.2 * MM)
        # the sheet rides 0.10 mm above the (maximum of the local) skin height
        Hm = np.maximum.accumulate(H, axis=1)
        prof = [
            (0.00, np.full(m, -0.10 * MM)),
            (0.00, 0.45 * Hm[:, 1]),
            (0.08, 0.85 * Hm[:, 1]),
            (0.20, Hm[:, 1] + 0.04 * MM),
            (0.45, Hm[:, 2] + 0.05 * MM),
            (0.80, Hm[:, 3] + 0.05 * MM),
            (1.30, Hm[:, 4] + 0.03 * MM),
            (1.90, H[:, 5] - 0.06 * MM),
            (2.40, H[:, 6] - 0.18 * MM),
            (2.90, H[:, 7] - 0.35 * MM),
        ]
        rings = [P + O * (a * MM * wf)[:, None] + Nn * z[:, None] for a, z in prof]
        V = np.stack(rings, 1).reshape(-1, 3)
        nprof = len(prof)
        faces = []
        for i in range(m):
            i2 = (i + 1) % m
            for j in range(nprof - 1):
                faces.append((i * nprof + j, i2 * nprof + j, i2 * nprof + j + 1, i * nprof + j + 1))
        me = bpy.data.meshes.new(f"CatBaseV6_Eye{tag}_LidMargin")
        me.from_pydata(V.tolist(), [], faces)
        me.update()
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()
        ta = me.attributes.new("margin_t", "FLOAT", "POINT")
        mt = np.array([0.0, 0.05, 0.12, 0.22, 0.34, 0.50, 0.66, 0.80, 0.92, 1.0])
        ta.data.foreach_set("value", np.tile(mt, m).astype(np.float32))
        for p_ in me.polygons:
            p_.use_smooth = True
        me.materials.append(mat)
        ob = v6.link(bpy.data.objects.new(me.name, me), coll)
        ob.parent = parent
        ob.matrix_world = Matrix.Translation(v6.HEAD_ORIGIN) if parent is not None and parent.type != "EMPTY" else Matrix.Identity(4)
        objs.append(ob)
        sel = np.nonzero(low & (np.abs(t) < 0.86))[0]
        sel = sel[np.argsort(t[sel])]
        pts = P[sel] + Nn[sel] * 0.06 * MM + O[sel] * 0.05 * MM * wf[sel][:, None]
        tube = v6.tube_mesh(f"CatBaseV6_Eye{tag}_TearMeniscus", pts, 0.14 * MM, closed=False, segs=8)
        tob = v6.link(bpy.data.objects.new(tube.name, tube), coll)
        if tear is not None:
            tube.materials.append(tear)
        tob.parent = parent
        tob.matrix_world = Matrix.Translation(v6.HEAD_ORIGIN) if parent is not None and parent.type != "EMPTY" else Matrix.Identity(4)
        objs.append(tob)
    return objs


def build_caruncles_v10(coll, parent, mat):
    """A larger, pinker caruncle in each medial canthus (judged round 7: 'in
    3/4 the medial canthus is a black void'): 4.4 x 3.0 mm, lying on the
    eye, its medial half tucked under the lid."""
    objs = []
    for s, tag in ((1.0, "L"), (-1.0, "R")):
        P, Nn = v7.eye_surface_outline(s, 320)
        i = int(np.argmin(P[:, 1] * s))
        cen = P.mean(0)
        toward = cen - P[i]
        toward -= (toward @ Nn[i]) * Nn[i]
        toward /= np.linalg.norm(toward)
        c = P[i] + toward * 2.0 * MM + Nn[i] * 0.10 * MM
        bpy.ops.mesh.primitive_uv_sphere_add(segments=40, ring_count=20, radius=1.0)
        cr = bpy.context.object
        cr.name = f"CatBaseV6_Eye{tag}_Caruncle"
        zN = Vector(Nn[i]).normalized()
        xT = Vector(toward).normalized()
        yB = zN.cross(xT)
        M = Matrix((xT, yB, zN)).transposed().to_4x4()
        M.translation = Vector(c) + (v6.HEAD_ORIGIN if parent is not None and parent.type != "EMPTY" else Vector())
        cr.matrix_world = M @ Matrix.Diagonal((4.4 * MM, 3.0 * MM, 0.75 * MM, 1.0))
        bpy.ops.object.shade_smooth()
        if mat is not None:
            cr.data.materials.append(mat)
        for uc in list(cr.users_collection):
            uc.objects.unlink(cr)
        coll.objects.link(cr)
        if parent is not None:
            mw = cr.matrix_world.copy()
            cr.parent = parent
            cr.matrix_world = mw
        objs.append(cr)
    return objs


def eye_overrides_v10(objs, mats):
    v9.eye_overrides_v9(objs, mats)
    cm = mats.get("caruncle")
    if cm is not None:
        bs = next(n for n in cm.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        bs.inputs["Base Color"].default_value = (0.44, 0.20, 0.19, 1.0)
        bs.inputs["Roughness"].default_value = 0.08
        bs.inputs["Coat Weight"].default_value = 0.8
        bs.inputs["Subsurface Weight"].default_value = 0.25


def install_build_overrides_v10():
    if getattr(v6, "_ROUND8_BUILD", False):
        return
    v9.install_build_overrides_v9()
    v6._ROUND8_BUILD = True
    v6.build_skin = build_skin_v10
    v7.build_caruncles_v7 = build_caruncles_v10
    build_eyes_prev = v9.v6.build_eyes

    def build_eyes_v10(coll, mats, parent):
        objs = build_eyes_prev(coll, mats, parent)
        cmat = cornea_material_v10()
        for o in objs:
            if o.name.endswith("_Cornea"):
                o.data.materials.clear()
                o.data.materials.append(cmat)
        eye_overrides_v10(objs, mats)
        return objs

    v6.build_eyes = build_eyes_v10
    v6.build_lid_margins = build_lid_margins_v10
    v6.skin_material = skin_material_v10
    v6.build_groom = build_groom_v10
    v6.build_inner_ear_furnishings = build_inner_ear_furnishings_v10


# ---------------------------------------------------------------------------
# Overrides
# ---------------------------------------------------------------------------

def apply_round8_overrides():
    if getattr(v6, "_ROUND8", False):
        return
    v9.apply_round7_overrides()
    v6._ROUND8 = True
    # muzzle: 11 -> 8 mm forward (the muzzle-keyed layout follows)
    A.mz = A.mz - (v9.MUZZLE_DX - MUZZLE_DX_V10)
    v6.NOSE_X0 = 128.0 + A.mz
    v9.MUZZLE_DX = MUZZLE_DX_V10
    # skin: closed v3 scan field, cranium / chin warps, neck, bust, details
    v7.scan_field = scan_field_v10
    v7.scan_head_neck = scan_head_neck_v10
    v7.fur_inset_mm = fur_inset_mm_v10
    v7.build_bust_ops = build_bust_ops_v10
    v7.build_bust_field = build_bust_field_v10
    v6.build_detail_ops = build_detail_ops_v10
    v6.DETAIL_OPS = None
    # eyes: globes forward, a slightly wider fissure
    A.eye_sink = -EYE_FORWARD_V10 * MM
    A.fissure_up = FISSURE_UP_V10 * MM
    A.fissure_lo = FISSURE_LO_V10 * MM
    # ears: smaller, more upright, closer, flared into the skull
    A.ear_base = v6.v(*EAR_BASE_V10)
    A.ear_h = EAR_H_V10 * MM
    A.ear_chord = EAR_CHORD_V10 * MM
    A.ear_tip_r = EAR_TIP_R_V10 * MM
    A.ear_t0 = EAR_T0_V10 * MM
    A.ear_t1 = EAR_T1_V10 * MM
    A.ear_lean_out = EAR_LEAN_OUT_V10
    A.ear_lean_back = EAR_LEAN_BACK_V10
    A.ear_open_out = EAR_OPEN_OUT_V10
    A.ear_twist = EAR_TWIST_V10
    v6.ear_arrays = ear_arrays_v10
    v6.EAR_ATTRS = ("is_ear", "ear_t", "ear_u", "ear_face", "ear_flare")
    v9.cup_weight_v9 = cup_weight_v10
    v8.cup_weight_v8 = cup_weight_v10
    v7.cup_weight = cup_weight_v10
    v9.ear_cavity = ear_cavity_v10
    v9.ear_cavity_sd = ear_cavity_sd_v10
    # markings, coat, flow, guides, iris
    v6.MARKINGS = MARKINGS_V10
    v6._MARK_CACHE.clear()
    v6.coat_fields = coat_fields_v10
    v8.coat_fields_v8 = coat_fields_v10
    v9.coat_fields_v9 = coat_fields_v10
    v6.fur_direction = fur_direction_v10
    v6.grow_guides = grow_guides_v10
    v8.iris_colour = iris_colour_v10


# ---------------------------------------------------------------------------
# Review aids: Workbench previews of the bare skin at the review cameras,
# and skin measurements
# ---------------------------------------------------------------------------

def preview_v10(args):
    """Workbench renders of the bare round-8 skin level set, pinnae (with
    their fillets) and globes from the five fixed review cameras and three
    ear / eye / nose close-ups (no fur)."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    d = np.load(CACHE / "skin_dense.npz")
    me = v6.mesh_from_arrays("dense", d["pts"], d["quads"])
    me.shade_smooth()
    ob = v6.link(bpy.data.objects.new("dense", me))
    ob.location = v6.HEAD_ORIGIN
    cd = v6.cornea_dims()
    for s in (1.0, -1.0):
        c = Vector(v6.eye_center(s) @ v6.head_R().T) + v6.HEAD_ORIGIN
        g = Vector(v6.head_R() @ v6.gaze_frame(s)[:, 0])
        bpy.ops.mesh.primitive_uv_sphere_add(radius=A.eye_r, location=c, segments=96, ring_count=48)
        bpy.ops.object.shade_smooth()
        bpy.ops.mesh.primitive_uv_sphere_add(radius=cd["Rc"], location=c + g * (cd["apex"] - cd["Rc"]), segments=96, ring_count=48)
        bpy.ops.object.shade_smooth()
        eo = v6.link(bpy.data.objects.new(f"ear{s}", v6.ear_mesh(s)))
        eo.location = v6.HEAD_ORIGIN
        sub = eo.modifiers.new("sub", "SUBSURF")
        sub.levels = 1
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.show_cavity = True
    sc.display.shading.cavity_type = "BOTH"
    sc.render.resolution_x = 960
    sc.render.resolution_y = 540
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.sensor_width = 36.0
    views = []
    for name, spec in list(v6.CAMERAS.items()):
        d_, dist = spec[0], spec[1]
        tgt = spec[2] if len(spec) > 2 else v6.CAM_TARGET
        views.append((name, tgt, d_, dist, 85.0))
    ear = Vector(A.ear_base @ v6.head_R().T) + v6.HEAD_ORIGIN
    eye = Vector(v6.lid_center(-1.0) @ v6.head_R().T) + v6.HEAD_ORIGIN
    nose = Vector(np.array([v6.NOSE_X0 + 8.0, 0.0, -8.0]) * MM @ v6.head_R().T) + v6.HEAD_ORIGIN
    views += [("ear_tq", ear * Vector((1, -1, 1)) + Vector((0, 0, 0.015)), Vector((0.55, -0.8, 0.25)), 0.40, 85.0),
              ("ear_back", ear * Vector((1, -1, 1)) + Vector((0, 0, 0.015)), Vector((-0.75, -0.6, 0.25)), 0.40, 85.0),
              ("ear_profile", ear * Vector((1, -1, 1)) + Vector((0, 0, 0.015)), Vector((0.0, -1.0, 0.1)), 0.40, 85.0),
              ("ear_front", ear * Vector((1, -1, 1)) + Vector((0, 0, 0.015)), Vector((1.0, -0.2, 0.15)), 0.40, 85.0),
              ("eye_tq", eye, Vector((0.72, -0.69, 0.05)), 0.26, 85.0), ("eye_profile", eye, Vector((0.05, -1.0, 0.02)), 0.30, 85.0),
              ("nose_tq", nose, Vector((0.72, -0.69, 0.1)), 0.22, 85.0), ("nose_front", nose, Vector((1.0, 0.0, 0.05)), 0.22, 85.0)]
    for name, t, d_, dist, lens in views:
        cam.data.lens = lens
        cam.location = t + d_.normalized() * dist
        cam.rotation_euler = (t - cam.location).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = str(Path(args.preview_dir) / f"skin_{name}.png")
        bpy.ops.render.render(write_still=True)
    # the pinna alone (head hidden): the shell, rims, flare and pocket
    ob.hide_render = True
    for name, t, d_, dist, lens in views[5:9]:
        cam.data.lens = lens
        cam.location = t + d_.normalized() * dist
        cam.rotation_euler = (t - cam.location).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = str(Path(args.preview_dir) / f"earonly_{name}.png")
        bpy.ops.render.render(write_still=True)


def measure_skin_v10():
    """Proportions of the bare skin (head frame mm): nose tip, stop, the
    stop-to-tip length against the fissure width, the cranium behind the
    ear, mouth / chin heights, the neck-to-head width ratio and the pinna
    base (width, lateral-base height against the upper lid)."""
    d = np.load(CACHE / "skin_dense.npz")
    Pw = d["pts"].astype(float)
    Ph = Pw @ v6.head_R() / MM
    out = {}
    mid = Ph[np.abs(Ph[:, 1]) < 0.6]
    tip_i = int(np.argmax(mid[:, 0]))
    out["nose_tip_head_mm"] = mid[tip_i].round(1).tolist()
    # dorsal profile: the top of the midline section per x
    xs = np.arange(60.0, mid[tip_i, 0], 1.0)
    top = []
    for x in xs:
        sl = mid[np.abs(mid[:, 0] - x) < 0.6]
        sl = sl[sl[:, 2] > mid[tip_i, 2] - 2.0]
        top.append(sl[:, 2].max() if len(sl) else np.nan)
    top = np.array(top)
    # the stop: the dorsal profile point farthest below the chord from the
    # forehead (x = 70) to the top of the nose (12 mm behind the tip)
    x0, x1 = 70.0, float(mid[tip_i, 0]) - 12.0
    p0 = np.array([x0, np.interp(x0, xs, top)])
    p1 = np.array([x1, np.interp(x1, xs, top)])
    e = (p1 - p0) / np.linalg.norm(p1 - p0)
    nrm = np.array([-e[1], e[0]])
    dev = np.array([(np.array([x, zt]) - p0) @ nrm for x, zt in zip(xs, top)])
    ok = (xs > x0) & (xs < x1)
    k = int(np.nanargmin(np.where(ok, dev, np.inf)))
    out["stop_head_mm"] = [float(xs[k]), float(round(top[k], 1))]
    out["stop_depth_mm"] = float(round(-dev[k], 2))
    tipp2 = mid[tip_i, [0, 2]]
    stl = float(np.linalg.norm(tipp2 - np.array([xs[k], top[k]])))
    out["stop_to_tip_mm"] = round(stl, 1)
    out["stop_to_tip_over_fissure_width"] = round(stl / (A.fissure_w / MM), 2)
    out["dorsal_profile_z_every_5mm_from_x60"] = [float(round(v_, 1)) for v_ in top[::5]]
    back = []
    for z in (40.0, 20.0, 0.0, -20.0):
        sl = mid[np.abs(mid[:, 2] - z) < 0.6]
        back.append(float(round(sl[:, 0].min(), 1)))
    out["head_back_x_at_z40_20_0_m20"] = back
    out["head_length_mm"] = round(float(mid[tip_i, 0] - min(back)), 1)
    # chin: the lowest midline point in front of x = 100
    ch = mid[(mid[:, 0] > 100.0) & (mid[:, 2] < -20.0) & (mid[:, 2] > -80.0)]
    fr = ch[ch[:, 0] > np.percentile(ch[:, 0], 60)]
    out["chin_front_lowest_z"] = float(round(fr[:, 2].min(), 1)) if len(fr) else None
    # widths (world)
    def hw(z):
        sl = Pw[np.abs(Pw[:, 2] / MM - z) < 0.8]
        return float(np.abs(sl[:, 1]).max() / MM)
    head_w = max(hw(z) for z in range(-40, 30, 5))
    neck_w = min(hw(z) for z in range(-100, -60, 5))
    out["head_halfwidth_mm"] = round(head_w, 1)
    out["neck_min_halfwidth_mm"] = round(neck_w, 1)
    out["neck_over_head"] = round(neck_w / head_w, 3)
    # pinna base
    Pe, q_, t_, at = ear_arrays_v10(1.0, sdf=v6.head_sdf_sampler())
    Peh = Pe @ v6.head_R() / MM
    base = (np.abs(at["ear_t"] - 0.02) < 0.02) & (at["ear_face"] < 0)
    if base.any():
        yb = Peh[base, 1]
        out["pinna_base_y_range_mm"] = [float(round(yb.min(), 1)), float(round(yb.max(), 1))]
        out["pinna_base_width_over_head_width"] = round(float((yb.max() - yb.min()) / (2 * head_w)), 3)
        lat = base & (at["ear_u"] > 0.9)
        out["pinna_lateral_base_z"] = float(round(Peh[lat, 2].min(), 1)) if lat.any() else None
    ec = v6.eye_center(1.0) / MM
    out["upper_lid_z"] = float(round(ec[2] + A.fissure_up / MM * 0.9, 1))
    tipp = Peh[np.argmax(at["ear_t"])]
    out["pinna_tip_head_mm"] = tipp.round(1).tolist()
    cdm = v6.cornea_dims()
    apex = (v6.eye_center(1.0) + v6.gaze_frame(1.0)[:, 0] * cdm["apex"]) / MM
    out["cornea_apex_head_mm"] = apex.round(1).tolist()
    return out


# ---------------------------------------------------------------------------
# Measure, compare, manifest (round 8)
# ---------------------------------------------------------------------------

def stage_measure_v10(args):
    """Round-7 measures (proportions, CT tissue depths and landmark check) plus
    the round-8 skin measures (measure_skin_v10)."""
    out = v7.stage_measure_v7(args)
    out["round8_skin"] = measure_skin_v10()
    (CACHE / f"measure_round{args.round}.json").write_text(json.dumps(out, indent=2) + "\n")
    log("round-8 skin measures", json.dumps(out["round8_skin"]))
    return out


def stage_compare_v10(args):
    """Round-7 sheets (previous | this round at the reference framing, the
    five Overcast cameras, the close-ups, the backlit front, the Nyaakoto
    reference front and profile) plus a sheet of this round's three-quarter
    close-ups under all four lights (the ear base and eye checks)."""
    v9.stage_compare_v9(args)
    rn = args.round
    cur = OUT / "Renders" / f"round_{rn}"
    tag = f"R{rn}"
    ims = []
    for light in ("Overcast", "Exterior", "ThreePoint", "Studio"):
        f_ = cur / f"CatBaseV6_{tag}_{light}_CloseThreeQuarter.png"
        if f_.exists():
            ims.append(v7._img_load(f_)[100:980, 200:1720])
    if len(ims) == 4:
        top = v7._side_by_side(ims[:2], 540)
        bot = v7._side_by_side(ims[2:], 540)
        W = max(top.shape[1], bot.shape[1])
        sheet = np.full((top.shape[0] + bot.shape[0] + 8, W, 3), 0.02, np.float32)
        sheet[:top.shape[0], :top.shape[1]] = top
        sheet[top.shape[0] + 8:, :bot.shape[1]] = bot
        v7._img_save(sheet, cur / f"CatBaseV6_{tag}_CloseThreeQuarter_AllLights.png")
    log("round-8 comparison sheets written to", cur)


def stage_manifest_v10(args):
    v9.stage_manifest_v9(args)
    man = json.loads((OUT / "manifest.json").read_text())
    man["round"] = args.round
    man["generator"] = ("scripts/art/create_cat_base_v10.py (round 8; imports create_cat_base_v9.py, which imports "
                        "create_cat_base_v8.py, create_cat_base_v7.py and create_cat_base_v6.py)")
    man["round8"] = {
        "cranium": {"shorten_behind_head_x_mm": CRANIUM_X0, "scale": CRANIUM_SCALE, "occiput_z0_mm": OCCIPUT_Z0, "occiput_scale": OCCIPUT_SCALE},
        "crown_lift_mm": CROWN_LIFT, "crown_lift_head_z_ramp_mm": list(CROWN_Z), "temple_inset_mm": TEMPLE_INSET,
        "scan_cleanup_scan_units": {"order": "relevel (largest shell), opening, closing, blur (inside the masks)",
                                    "opening_radius": SCAN_OPEN_V10, "closing_radius": SCAN_CLOSE_V10, "ear_mask_scale": SCAN_EAR_MASK_SCALE_V10,
                                    "canal_mask": SCAN_CANAL_MASK, "smooth_box_width_voxels": SCAN_EAR_SMOOTH_V10,
                                    "cache": "Local/CatBaseV6Cache/scan_field_closed_v3f.npz"},
        "muzzle_forward_mm": MUZZLE_DX_V10, "chin": {"lift_mm": CHIN_LIFT, "tuck_mm": CHIN_TUCK, "bump_mm": CHIN_H_V10, "mentum_z_head_mm": MENTUM_Z},
        "neck": {"side_inset_mm": NECK_SIDE_INSET_V10, "nape_dip_mm": NAPE_DIP_V10},
        "stop": {"centre_head_xz_mm": list(STOP_C_V10), "depth_mm": STOP_DEPTH_V10, "brow_mm": BROW_H_V10},
        "nose_planum_mm": {"edge": LEATHER_EDGE_H_V10, "centre": LEATHER_DOME_V10, "bevel": LEATHER_BEVEL_V10, "alar": ALAR_H_V10},
        "eyes": {"globe_forward_mm": EYE_FORWARD_V10, "fissure_up_mm": FISSURE_UP_V10, "fissure_lo_mm": FISSURE_LO_V10,
                 "cornea": "Fresnel only, IOR 1.376 (no reflection floor)", "lid_margin_samples": 720},
        "ear": {"base_head_mm": list(EAR_BASE_V10), "height_mm": EAR_H_V10, "base_chord_mm": EAR_CHORD_V10, "tip_radius_mm": EAR_TIP_R_V10,
                "thickness_mm": [EAR_T0_V10, EAR_T1_V10], "lean_out_deg": EAR_LEAN_OUT_V10, "lean_back_deg": EAR_LEAN_BACK_V10,
                "open_out_deg": EAR_OPEN_OUT_V10, "henry_pocket_t": list(HENRY_T), "henry_curl_deg": HENRY_CURL_DEG,
                "flare_radius_mm_lateral_medial": list(FLARE_R), "flare_tuck_mm": FLARE_TUCK,
                "cavity_t": list(EAR_CAVITY_T_V10), "canal": CANAL, "cavity_cache": "Local/CatBaseV6Cache/ear_cavity_v10.npz"},
        "guard_layers": [g[0] for g in GUARD_LAYERS_V10],
        "markings": [m_[0] for m_ in MARKINGS_V10], "marking_edge_mm": MARK_EDGE_V10,
    }
    (OUT / "manifest.json").write_text(json.dumps(man, indent=2, ensure_ascii=False) + "\n")
    log("manifest (round 8 fields added)")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", type=int, default=ROUND)
    ap.add_argument("--stages", default="skin,skinpreview")
    ap.add_argument("--voxel", type=float, default=0.75)
    ap.add_argument("--samples", type=int, default=256)
    ap.add_argument("--preview-dir", default=str(CACHE / "preview_r8"))
    ap.add_argument("--tex", type=int, default=4096)
    ap.add_argument("--guides", type=int, default=70000)
    ap.add_argument("--lights", default="Overcast")
    ap.add_argument("--views", default="")
    ap.add_argument("--render-dir", default="")
    ap.add_argument("--percent", type=int, default=100)
    ap.add_argument("--border", default="", help="review aid: x0,y0,x1,y1 render border (0..1, crop to it)")
    args = ap.parse_args(argv)
    if args.border:
        bx = [float(t) for t in args.border.split(",")]
        _cfg = v6.configure_render

        def configure_border(samples):
            _cfg(samples)
            r = bpy.context.scene.render
            r.use_border = True
            r.use_crop_to_border = True
            r.border_min_x, r.border_min_y, r.border_max_x, r.border_max_y = bx

        configure_border.percent = 100
        v6.configure_render = configure_border
    CACHE.mkdir(parents=True, exist_ok=True)
    Path(args.preview_dir).mkdir(parents=True, exist_ok=True)
    apply_round8_overrides()
    stages = args.stages.split(",")
    if "scan" in stages:
        v7.stage_scan(args)
    if "skin" in stages:
        EAR_CAVITY_REBUILD_V10[0] = True
        _EAR_CAVITY_V10.clear()
        v7.stage_skin_v7(args)
    if "skinmeasure" in stages:
        m = measure_skin_v10()
        log("skin measure", json.dumps(m))
        (Path(args.preview_dir) / "skin_measure.json").write_text(json.dumps(m, indent=2))
    if "skinpreview" in stages:
        preview_v10(args)
    if "build" in stages:
        install_build_overrides_v10()
        v6.stage_build(args)
    if "render" in stages:
        v6.stage_render(args)
    if "measure" in stages:
        stage_measure_v10(args)
    if "compare" in stages:
        stage_compare_v10(args)
    if "manifest" in stages:
        stage_manifest_v10(args)


if __name__ == "__main__":
    main()
