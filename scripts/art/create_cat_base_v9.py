"""CatBaseV6 round 7 (generator v9): judged defects of round 6 (score 4.5/10).

Round 5 (create_cat_base_v7.py) took the head and neck shape from a real cat
scan ("Cat sitting upright" by elaughli, CC BY 4.0, private raw scan) and
kept the CT skull for landmarks; round 6 (create_cat_base_v8.py) reworked the
eyes, ears, nose, coat and bust on that surface. Round 7 keeps the method and
the scan field and fixes the round-6 judgement, most impactful first:

The judge's millimetres are real-cat millimetres; CatBaseV6 is 2.2x a real
cat, so they are scaled by 2.2 here (8-15 mm furnishings -> 18-33 mm).

1. ears: ~2,800 pale cream furnishing hairs (18-33 mm, a sixth of the medial
   ones to 38 mm) fanning from the medial margin and the base over the lower
   two thirds; bare pink-grey skin only in the upper-central third; veins at
   ~20 % and mostly in transmitted light (a translucent lobe); the three wide
   antihelical ridge bands and the grey chip (head skin poking through the
   inner face) are gone (two small ridges by the canal remain); all pinna
   hair combs toward the tip, so the margin hair runs along the edge and no
   longer draws a halo; pink-red, shorter-radius subsurface; a separate fine
   4.5-8 mm ear-back groom; a clearer Henry's pocket; the opening turned
   30 deg forward; the concha voxelised from the pinna itself; the scan's
   ear-base hollows closed and its brim rounded;
2. profile: the muzzle and nose 11 mm forward (a smooth warp of the scan
   field in front of the eyes), a raised nasal bridge with a stop, a domed
   nose pad (+5 mm at the centre), a chin; the lower muzzle lifted 8 mm
   (shorter upper lip); a narrower neck (sides inset up to 15 mm more behind
   the jaw), a nape dip, and a bust with scapulae, points of the shoulder
   and tapering forelimbs;
3. eyes: a lid fill band so the lid skin reaches the fissure everywhere (the
   round-6 cornea showed through gaps above and below the margin strip); a
   thin (<= 0.6 mm) tapered margin strip and pigment band; the lower lid
   0.9 mm higher, the upper lid 2.1 mm lower; the pink membrane at the MEDIAL
   canthus, dark conjunctiva at the lateral one; softer iris stroma with
   half the fibre contrast and low-frequency colour; a reflection floor so
   the sky covers the whole corneal dome;
4. nose: a real 3D leather pad (rounded top and bevel), comma nostrils with
   flared alar wings, a fine cobblestone normal at roughness 0.45, and a
   geometric (unpainted) philtrum groove;
5. mouth: only a short inverted Y (corners hidden under the pads), a shorter
   upper lip, puffier whisker pads, jittered grey follicle pits the whiskers
   emerge from;
6. bib: hair-level interleaving with irregular tufts (no vertical drips),
   clumped, slightly curved chest locks;
7. crown: the ear-base coat blends smoothly into the crown coat (no ridge
   or collar), flowing onto the ear back;
8. silhouette: per-region guard layers (face, crown/ruff, body, chest, ear
   back) with their own clumping, fly-away hairs and ruff clumps; body
   clumps are larger with tip spread so the torso no longer streaks.

Run from the repository root (Blender 5.2.2 LTS, background):

  blender -b --factory-startup --python scripts/art/create_cat_base_v9.py -- \\
      --stages skin,build,measure,render,compare,manifest --round 7 \\
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
import create_cat_base_v8 as v8  # noqa: E402

v7 = v8.v7
v6 = v8.v6
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

ROUND = 7


# ---------------------------------------------------------------------------
# Head shape: muzzle warp, neck, nape (skin stage)
# ---------------------------------------------------------------------------

# The scanned muzzle is short and the upper lip long next to the reference
# photographs (judged round 6: "a round helmet with a very short, flat face",
# nose-to-mouth ~2x the references). The scan field is sampled through a
# smooth warp in the head frame: everything in front of the eyes moves
# forward by up to MUZZLE_DX (a stretch between MUZZLE_X, so the eyes and the
# cranium are untouched), and the lower muzzle (pads' lower lobes, the lips
# and the chin) is lifted by up to LIP_DZ (a compression between LIP_Z, so
# the nose stays and the upper lip shortens). Both fade out on the throat.
MUZZLE_DX = 11.0
MUZZLE_X = (96.0, 130.0)
LIP_DZ = 8.0
LIP_Z = (-9.0, -28.0)


def muzzle_warp_src(Ph):
    """Source point (head frame, m) in the unwarped scan for destination Ph."""
    x, y, z = Ph[..., 0] / MM, Ph[..., 1] / MM, Ph[..., 2] / MM
    wz = smoothstep(-102.0, -74.0, z)
    ux = MUZZLE_DX * smoothstep(MUZZLE_X[0], MUZZLE_X[1], x) * wz
    wl = smoothstep(86.0, 122.0, x) * (1.0 - smoothstep(28.0, 72.0, np.abs(y))) * wz
    uz = LIP_DZ * smoothstep(LIP_Z[0], LIP_Z[1], z) * wl
    out = np.array(Ph, float, copy=True)
    out[..., 0] -= ux * MM
    out[..., 2] -= uz * MM
    return out


# The scan field around the removed scan ears keeps hollows: the opened
# ear-canal pits and the notches the morphological opening left. With the
# pinnae turned forward they are no longer inside the concha and read as
# dark holes behind and beside the ear bases. A morphological CLOSING
# (dilate, re-level, erode) inside the round-5 ear masks fills every hollow
# narrower than ~2 x SCAN_CLOSE (scan units).
SCAN_CLOSE = 6.0
SCAN_EAR_SMOOTH = 9  # box width (voxels of 0.5 scan units), 3 passes
_SCAN_CLOSED = {}


def scan_field_v9():
    if "S" in _SCAN_CLOSED:
        return _SCAN_CLOSED
    p = CACHE / "scan_field_closed_v2.npz"
    src = CACHE / "scan_field.npz"
    if p.exists() and p.stat().st_mtime >= src.stat().st_mtime:
        d = np.load(p)
        _SCAN_CLOSED.update(S=d["S"].astype(np.float32), org=d["origin"].astype(np.float64), vs=float(d["vs"]))
        return _SCAN_CLOSED
    t0 = time.time()
    d = np.load(src)
    S = d["S"].astype(np.float32)
    org, vs = d["origin"].astype(np.float64), float(d["vs"])
    r = SCAN_CLOSE
    Sd = v7.relevel(S - r, org, vs, band=r + 6.0)[0] + r
    X = [np.arange(S.shape[a]) * vs + org[a] for a in range(3)]
    gx, gy, gz = X[0][:, None, None], X[1][None, :, None], X[2][None, None, :]
    c, rr, soft = np.array(v7.SCAN_EAR_MASK["c"]), np.array(v7.SCAN_EAR_MASK["r"]), v7.SCAN_EAR_MASK["soft"]
    wear = np.zeros(S.shape, np.float32)
    for sgn in (1.0, -1.0):
        e = np.sqrt(((gx - c[0]) / (1.25 * rr[0])) ** 2 + ((gy - sgn * c[1]) / (1.25 * rr[1])) ** 2 + ((gz - c[2]) / (1.25 * rr[2])) ** 2)
        wear = np.maximum(wear, 1.0 - smoothstep(1.0 - soft / rr.mean(), 1.0, e))
    Sc = S + (np.minimum(Sd, S) - S) * wear
    # then round the brim the opening left round each former scan ear (it
    # read as a helmet-like ridge from each ear base across the crown)
    Sb = v6.gaussian_blur3(Sc, SCAN_EAR_SMOOTH)
    Sc = Sc + (Sb - Sc) * wear
    np.savez_compressed(p, S=np.clip(Sc, -16.0, 16.0).astype(np.float16), origin=org, vs=vs)
    log(f"scan field closed (r {r} scan units) inside the ear masks ({time.time()-t0:.0f}s)")
    _SCAN_CLOSED.update(S=Sc.astype(np.float32), org=org, vs=vs)
    return _SCAN_CLOSED


# neck and nape (judged round 6: "the head sits on a column as wide as the
# skull, with no nape dip or occiput")
NECK_SIDE_INSET = 15.0  # extra skin inset on the neck sides behind the jaw (mm)
NAPE_DIP = 15.0  # nape inset (mm) at world z ~ -72


def fur_inset_mm_v9(Pw_mm):
    t = v8.fur_inset_mm_v8(Pw_mm)
    x, y, z = Pw_mm[..., 0], np.abs(Pw_mm[..., 1]), Pw_mm[..., 2]
    band = smoothstep(-46.0, -86.0, z)
    side = smoothstep(26.0, 66.0, y) * (1.0 - smoothstep(70.0, 110.0, x))
    t = t + NECK_SIDE_INSET * band * side
    nape = np.exp(-((z + 72.0) / 22.0) ** 2) * smoothstep(-35.0, -85.0, x) * (1.0 - smoothstep(38.0, 72.0, y))
    return t + NAPE_DIP * nape


def scan_head_neck_v9(P):
    """Round-6 scan head and neck, sampled through the muzzle warp, with the
    round-7 neck and nape insets. The round-6 conchal funnel and bowl carve
    is gone: it was an ellipsoid in ear coordinates that, with the opening
    turned forward, left a crater outside the pinna and a scalp knob and a
    poke-through inside it. The concha is now carved from the pinna's own
    cavity (ear_cavity, a detail op)."""
    P = np.asarray(P, float)
    Pmm = P / MM
    Ph = P @ v6.head_R()
    Psrc = muzzle_warp_src(Ph) @ v6.head_R().T
    d = v7.scan_sdf_world(Psrc) + fur_inset_mm_v9(Pmm) * MM
    # plug the scan's open ear canals: with the openings turned forward the
    # pinna funnels no longer cover them, and each read as a ~30 mm deep
    # crater behind the ear (found by ray probes from inside the cranium)
    for (a0, a1), rp in ((canal_plug_axis(), CANAL_PLUG_R), (canal_pit2_axis(), CANAL_PIT2_R)):
        for s in (1.0, -1.0):
            m = np.array([1.0, s, 1.0])
            d = v6.smin(d, v6.sd_capsule(Ph, a0 * m * MM, a1 * m * MM, rp * MM, rp * MM), 5.0 * MM)
    return v6.smax(d, (v7.Z_CUT - Pmm[..., 2]) * MM, v7.K_CUT * MM)


CANAL_PIT = np.array([-32.0, 64.0, 21.0])  # head mm, round 5's opened-scan canal pit (left side)
CANAL_PLUG_R = 10.0
# a second, 12 mm deep pit found on the round-7 skin behind the lateral ear
# base (dense-skin depth relative to its 14 mm neighbourhood)
CANAL_PIT2 = np.array([-35.5, 76.0, 16.5])
CANAL_PIT2_R = 8.5


def canal_pit2_axis():
    c = np.array([-10.0, 0.0, 20.0])
    r = float(np.linalg.norm(CANAL_PIT2 - c))
    d = (CANAL_PIT2 - c) / r
    return c + d * (r - 18.0), c + d * (r + 3.0)


def canal_plug_axis():
    """Head-frame axis (mm) of the canal plug: from 56 to 83 mm along the ray
    from the cranium centre (-10, 0, 20) through the pit, nudged to the
    measured centre of the hole."""
    c = np.array([-10.0, 0.0, 20.0])
    d0 = (CANAL_PIT - c) / np.linalg.norm(CANAL_PIT - c)
    a = np.cross(d0, [0.0, 0.0, 1.0])
    a /= np.linalg.norm(a)
    b = np.cross(d0, a)
    d = d0 + 0.2 * a + 0.05 * b
    d /= np.linalg.norm(d)
    return c + d * 56.0, c + d * 83.0


# ---------------------------------------------------------------------------
# Conchal cavity from the pinna itself
# ---------------------------------------------------------------------------

EAR_CAVITY_VS = 1.0 * MM
EAR_CAVITY_T_MAX = 0.62
EAR_CAVITY_T_MIN = -0.12  # the deepest part of the buried funnel is not carved (it opened a pocket beside the lateral base)
_EAR_CAVITY = {}
EAR_CAVITY_REBUILD = [False]


def build_ear_cavity(sdf):
    """Voxelise the cavity of each seated pinna: for every ring between
    EAR_CAVITY_T_MIN and EAR_CAVITY_T_MAX (the top of the buried funnel included) the region between a
    surface just behind the sheet's back face and the chord joining its two margins. Returns a
    signed-distance-like grid (m, <0 inside the cavity): the head skin is
    carved out of it, so the concha is exactly the pinna's cup, runs down
    the funnel toward the canal, and no scalp rises inside the ear or pokes
    through its inner face."""
    t0 = time.time()
    n_face, n_rim = 52, 9
    npr = 2 * n_face + 2 * n_rim
    clouds = []
    for s in (1.0, -1.0):
        Pw, quads, tris, at = v6.ear_arrays(s, sdf=sdf)
        nr = (len(Pw) - 2) // (npr + 2)
        R = Pw[:nr * npr].reshape(nr, npr, 3)
        t = np.asarray(at["ear_t"])[:nr * npr].reshape(nr, npr)[:, 0]
        F = R[:, :n_face]
        Bk = R[:, n_face + n_rim:2 * n_face + n_rim][:, ::-1]
        # from 0.35 of the sheet thickness behind the back face toward the
        # chord: the carved head surface stays hidden behind the pinna (a
        # mid-sheet boundary let it show through the inner face)
        M = Bk + 0.35 * (Bk - F)
        keep = (t <= EAR_CAVITY_T_MAX) & (t >= EAR_CAVITY_T_MIN)
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
            # near the base the cavity keeps to the back and medial part of
            # the cup: the lateral wall and the front of the conchal opening
            # stay head skin (tragus / antitragus floor), otherwise the carve
            # opened a hole beside the lateral margin in profile
            ti = float(tt[i])
            u_max = 0.50 + 0.50 * float(smoothstep(0.06, 0.30, ti))
            lam_max = 0.55 + 0.45 * float(smoothstep(0.02, 0.25, ti))
            sel = uu <= u_max
            Mi = M[i][sel]
            lam_u = np.linspace(0.0, 1.0, len(Mi))[:, None]
            C = Mi[:1] + (Mi[-1:] - Mi[:1]) * lam_u
            span = float(np.linalg.norm(Mi - C, axis=-1).max())
            nl = int(math.ceil(lam_max * span / (0.4 * MM))) + 1
            for lam in np.linspace(0.0, lam_max, nl):
                clouds.append(((1.0 - lam) * Mi + lam * C).astype(np.float32))
    pts = np.concatenate(clouds)
    vs = EAR_CAVITY_VS
    lo = np.floor(pts.min(0) / vs).astype(int) - 6
    hi = np.ceil(pts.max(0) / vs).astype(int) + 6
    shape = tuple(hi - lo + 1)
    ijk = np.floor(pts / vs).astype(int) - lo
    occ = np.zeros(shape, bool)
    occ[ijk[:, 0], ijk[:, 1], ijk[:, 2]] = True
    occ = v7.dilate6(occ, 1)
    ob = v6.gaussian_blur3(occ.astype(np.float32), 3)
    G = ((0.5 - ob) * 3.0 * MM).astype(np.float32)
    log(f"ear cavity {shape} from {len(pts)} samples, {int(occ.sum())} voxels ({time.time()-t0:.0f}s)")
    return G, lo * vs, vs


def ear_cavity():
    if "G" not in _EAR_CAVITY:
        p = CACHE / "ear_cavity.npz"
        if EAR_CAVITY_REBUILD[0] or not p.exists():
            G, org, vs = build_ear_cavity(v6.head_sdf_sampler())
            np.savez_compressed(p, G=G.astype(np.float16), origin=org, vs=vs)
            EAR_CAVITY_REBUILD[0] = False
        d = np.load(p)
        G = d["G"].astype(np.float32)
        # far from any cavity the blurred occupancy is 0 and G is +1.5 mm; a
        # subtract op with that value would clamp the head's interior field at
        # -1.5 mm (the zero set is unchanged, but the CT tissue depths of the
        # measure stage read the clamped field), so far voxels get +25 mm
        G = np.where(G >= 1.45 * MM, np.float32(25.0 * MM), G)
        _EAR_CAVITY.update(G=G, org=d["origin"].astype(np.float64), vs=float(d["vs"]))
    return _EAR_CAVITY


def ear_cavity_sd(Pw):
    """Cavity distance (m, <0 inside) at world-local points; +25 mm far away."""
    c = ear_cavity()
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


def cup_weight_v9(Pw):
    """1 on head skin inside or at the rim of a pinna's cavity (pale inner-
    ear skin and short pale hair there), 0 elsewhere."""
    return 1.0 - smoothstep(-0.5 * MM, 2.5 * MM, ear_cavity_sd(Pw))


BUST_DX = v8.BUST_DX
BUST_DZ = v8.BUST_DZ


def build_bust_ops_v9():
    """Round 7 bust (judged round 6: "a straight-sided tube with no shoulder
    blades or forelimb tops"): a slimmer neck base, scapular blades whose
    dorsal borders stand above the back line behind the neck (withers), a
    point of the shoulder (humeral head) on each side, forelimbs that hang
    from it, merged into the chest but marked off by a shallow axillary
    groove, and the pectorals and keel between them."""
    R = v6.rot_matrix
    dx, dz = BUST_DX, BUST_DZ

    def p(x, y, z):
        return (x + dx, y, z + dz)

    ops = []
    for s in (1.0, -1.0):
        ops.append(v6.cap_op(p(-62.0, 20.0 * s, -110.0), p(-64.0, 60.0 * s, -154.0), 20.0, 24.0, 26, frame="body"))  # trapezius
        ops.append(v6.ell_op(p(-80.0, 48.0 * s, -178.0), (15.0, 30.0, 54.0), R(roll=-22.0 * s, pitch=-8.0), 24, frame="body"))  # scapular blade
        ops.append(v6.cap_op(p(-90.0, 36.0 * s, -136.0), p(-76.0, 66.0 * s, -212.0), 9.0, 7.0, 16, frame="body"))  # scapular dorsal border
        ops.append(v6.ell_op(p(-30.0, 88.0 * s, -178.0), (32.0, 25.0, 46.0), R(roll=-12.0 * s), 26, frame="body"))  # deltoid
        ops.append(v6.ell_op(p(-4.0, 98.0 * s, -194.0), (24.0, 22.0, 24.0), None, 18, frame="body"))  # point of the shoulder
        ops.append(v6.cap_op(p(-20.0, 90.0 * s, -206.0), p(-6.0, 94.0 * s, -424.0), 30.0, 21.0, 26, frame="body"))  # forelimb, tapering
        ops.append(v6.ell_op(p(26.0, 40.0 * s, -206.0), (30.0, 38.0, 44.0), R(yaw=18.0 * s, roll=-10.0 * s), 26, frame="body"))  # pectoral
    ops.append(v6.cap_op(p(-22.0, 0.0, -104.0), p(-38.0, 0.0, -190.0), 56.0, 76.0, 30, frame="body"))  # neck base (forward: nape dip)
    ops.append(v6.ell_op(p(54.0, 0.0, -172.0), (26.0, 24.0, 44.0), None, 24, frame="body"))  # manubrium: keel
    ops.append(v6.ell_op((52.0, 0.0, -120.0), (32.0, 38.0, 38.0), None, 24, frame="body"))  # throat fill
    ops.append(v6.ell_op(p(-34.0, 0.0, -318.0), (96.0, 92.0, 205.0), None, 44, frame="body"))  # thorax
    for s in (1.0, -1.0):
        # shallow axillary groove between the forelimb and the chest
        ops.append(v6.ell_op(p(34.0, 68.0 * s, -252.0), (14.0, 4.0, 40.0), R(yaw=-24.0 * s), 12, mode="subtract", frame="body"))
    return ops


def build_bust_field_v9(vs=2.0 * MM):
    """v7.build_bust_field with a lighter blur (w 5 -> 4), so the round-7
    shoulder forms survive."""
    t0 = time.time()
    lo = np.floor(v6.DOMAIN_MIN / vs).astype(int) - 4
    hi = np.ceil(v6.DOMAIN_MAX / vs).astype(int) + 4
    shape = tuple(hi - lo + 1)
    xs = [np.arange(lo[a], hi[a] + 1) * vs for a in range(3)]
    ops = build_bust_ops_v9()
    Bf = np.empty(shape, np.float32)
    for a in range(shape[0]):
        J, K = np.meshgrid(xs[1], xs[2], indexing="ij")
        P = np.stack([np.full_like(J, xs[0][a]), J, K], -1).reshape(-1, 3)
        f = np.full(len(P), 0.2)
        f = v6.apply_ops(ops, P, f)
        f = v6.smax(f, -(P[:, 2] + 0.600), 12 * MM)
        Bf[a] = f.reshape(J.shape)
    Bb = v6.gaussian_blur3(Bf, 4)
    log(f"bust field v9 {shape} ({time.time()-t0:.0f}s)")
    return Bb, lo * vs


# ---------------------------------------------------------------------------
# Eyes: fissure, lid fill band, margin strip, caruncle, iris, cornea
# ---------------------------------------------------------------------------

FISSURE_UP_V9 = 9.4  # mm (round 6: 11.5): the upper lid 2.1 mm lower, over the top of the iris
FISSURE_LO_V9 = 10.9  # mm (round 6: 11.8): the lower lid 0.9 mm higher


def eye_surface_sd(P, side):
    """Signed distance (m) to the eye surface: the union of the globe and the
    corneal dome."""
    cd = v6.cornea_dims()
    q = (P - v6.eye_center(side)) @ v6.gaze_frame(side)
    d_g = np.linalg.norm(q, axis=-1) - A.eye_r
    qc = q.copy()
    qc[..., 0] -= cd["apex"] - cd["Rc"]
    d_c = np.linalg.norm(qc, axis=-1) - cd["Rc"]
    return np.minimum(d_g, d_c)


_V6_SD_FISSURE = v6.sd_fissure


def sd_fissure_v9(P, side=1.0):
    """v6.sd_fissure capped 6 mm in front of the corneal apex. The round-6
    prism ran forward without limit inside its 45 mm box and, with the muzzle
    now further forward, grooved a thin vertical seam down the side of the
    muzzle (visible in the bare-skin profile)."""
    q = (P - v6.eye_center(side)) @ v6.gaze_frame(side)
    return np.maximum(_V6_SD_FISSURE(P, side), q[..., 0] - (v6.cornea_dims()["apex"] + 6.0 * MM))


def lid_band_sd(P, side, t=1.05 * MM, reach=5.0 * MM):
    """Lid fill: a sheet 0..t above the eye surface, outside the palpebral
    fissure prism and within `reach` of it, so the lid skin reaches the
    fissure all round (round 6: the smooth carves left gaps where the cornea
    showed above and below the margin strip)."""
    d_e = eye_surface_sd(P, side)
    band = np.abs(d_e - 0.5 * t) - 0.5 * t
    df = v6.sd_fissure(P, side)
    band = np.maximum(band, -df)
    return np.maximum(band, df - reach)


# ---------------------------------------------------------------------------
# Nose, mouth, pads, bridge, chin (detail ops)
# ---------------------------------------------------------------------------

LEATHER_DOME = 3.2  # mm extra height at the centre of the pad
LEATHER_EDGE_H = 2.0
LEATHER_BEVEL = 1.6
ALAR_H = 1.2
PHILTRUM_BOTTOM_Z = -20.0  # the inverted Y (round 6: -30)
LIP_Y_V9 = [(0.0, PHILTRUM_BOTTOM_Z), (1.8, PHILTRUM_BOTTOM_Z - 1.2), (3.8, PHILTRUM_BOTTOM_Z - 2.6), (5.6, PHILTRUM_BOTTOM_Z - 3.6)]
PAD_C_V9 = (0.0, 16.0, -21.5)
PAD_R_V9 = (11.5, 9.0)
PAD_H_V9 = 2.6
LOWER_LIP_V9 = (0.0, PHILTRUM_BOTTOM_Z - 7.0, 6.0, 2.6, 0.5)
BRIDGE_H = 2.2  # mm, nasal bridge lift
STOP_C, STOP_DEPTH = (101.0, 33.0), 1.6  # head (x, z) mm, depth mm
BROW_C, BROW_H = (80.0, 51.0), 2.2
MOUTH_NOTCH = [(-8.0, PHILTRUM_BOTTOM_Z - 9.5), (0.0, PHILTRUM_BOTTOM_Z - 9.0), (8.0, PHILTRUM_BOTTOM_Z - 9.5)]
CHIN_V9 = dict(c=(0.0, -39.0), r=(10.0, 7.0), h=3.0)  # (y, z) centre, (y, z) radii, height; x from the skin


def leather_centre():
    lp = v6.leather_poly()
    return 0.5 * (lp[:, 1].max() + lp[:, 1].min())


def nostril_sd_mm(q, s):
    """Signed distance (mm, <0 inside) of a comma nostril in (y, z) head mm:
    a round bulb low beside the septum tapering up and out along the lateral
    wall."""
    poly = np.asarray([(y * s, z) for y, z in v6.NOSTRIL_POLY], float)
    wid = np.asarray(v6.NOSTRIL_W, float)
    d = np.full(q.shape[:-1], 1e3)
    for i in range(len(poly) - 1):
        a, b = poly[i], poly[i + 1]
        e = b - a
        t = np.clip(((q - a) @ e) / (e @ e), 0.0, 1.0)
        dist = np.linalg.norm(q - (a + t[..., None] * e), axis=-1) - (wid[i] + (wid[i + 1] - wid[i]) * t)
        d = np.minimum(d, dist)
    return d


def build_detail_ops_v9():
    """Round 7 detail ops (surface-relative on the warped scan bulk):

    - nose leather: a domed pad (edge 1.5 mm, +1.9 mm at the centre) with a
      1.6 mm rounded bevel instead of round 6's flat 1.25 mm plateau with a
      cut edge; raised alar wings lateral to each nostril;
    - nasal bridge: a 2.2 mm midline lift from the stop to the leather;
    - pads: puffier twin lobes (2.6 mm), higher (the lower muzzle is lifted);
    - chin: a 2.6 mm rounded point under the lower lip;
    - eyes: the round-6 lid shell and carves, then a lid fill band;
    - nostrils: comma holes 3.5 mm deep with the wing rising lateral to them;
    - philtrum: a narrow geometric groove to the inverted Y; the lip line is
      only the short Y (the round-6 side groove to the mouth corners, the
      "frown", is gone)."""
    ops = []
    mz = A.mz
    lp = v6.leather_poly()
    zc = leather_centre()
    alar = [np.asarray([(y * s, z) for y, z in v6.ALAR_POLY]) for s in (1.0, -1.0)]

    def leather(P, B):
        q = np.stack([P[..., 1], P[..., 2]], -1) / MM
        d2 = v6.sd_poly2d(q, lp)
        inside = np.clip(-d2 / LEATHER_BEVEL, 0.0, 1.0)
        bev = np.sqrt(np.clip(1.0 - (1.0 - inside) ** 2, 0.0, 1.0))
        dome = LEATHER_DOME * np.exp(-(q[..., 0] / 7.5) ** 2 - ((q[..., 1] - zc - 1.0) / 6.0) ** 2)
        da = np.minimum(v6.dist_poly2d(q, alar[0]), v6.dist_poly2d(q, alar[1]))
        wing = ALAR_H * np.exp(-(da / 1.1) ** 2)
        h = (LEATHER_EDGE_H + dome + wing) * bev
        d = np.maximum(d2 * MM, B - h * MM)
        return np.maximum(d, v6.NOSE_X0 * MM - P[..., 0])

    ops.append(v6.Op("union", leather, v6.v(v6.NOSE_X0, -14.0, -17.0), v6.v(v6.NOSE_X0 + 40.0, 14.0, 14.0), 0.35 * MM))

    def bridge(P, B):
        x, y, z = P[..., 0] / MM, P[..., 1] / MM, P[..., 2] / MM
        w = np.exp(-(y / 9.0) ** 2) * smoothstep(100.0, 122.0, x) * smoothstep(-2.0, 7.0, z) * (1.0 - smoothstep(30.0, 40.0, z))
        w = w * (1.0 - 0.6 * smoothstep(v6.NOSE_X0 - 6.0, v6.NOSE_X0 + 4.0, x))
        return B - BRIDGE_H * MM * w

    ops.append(v6.Op("union", bridge, v6.v(96.0, -30.0, -6.0), v6.v(v6.NOSE_X0 + 30.0, 30.0, 45.0), 0.8 * MM))

    # a stop between the eyes (a shallow dip at the root of the bridge)
    # under a slightly fuller forehead, so the profile is not one straight
    # line from the crown to the nose
    def brow(P, B):
        x, y, z = P[..., 0] / MM, P[..., 1] / MM, P[..., 2] / MM
        w = np.exp(-((x - BROW_C[0]) / 15.0) ** 2 - (y / 24.0) ** 2 - ((z - BROW_C[1]) / 10.0) ** 2)
        return B - BROW_H * MM * w

    def stop(P, B):
        x, y, z = P[..., 0] / MM, P[..., 1] / MM, P[..., 2] / MM
        w = np.exp(-((x - STOP_C[0]) / 7.0) ** 2 - (y / 13.0) ** 2 - ((z - STOP_C[1]) / 6.0) ** 2)
        return -(B + STOP_DEPTH * MM * w)

    ops.append(v6.Op("union", brow, v6.v(45.0, -60.0, 25.0), v6.v(115.0, 60.0, 80.0), 0.5 * MM))
    ops.append(v6.Op("subtract", stop, v6.v(80.0, -40.0, 15.0), v6.v(122.0, 40.0, 52.0), 0.3 * MM))
    for s in (1.0, -1.0):
        def pad(P, B, s_=s):
            y, z, x = P[..., 1] / MM, P[..., 2] / MM, P[..., 0] / MM
            w = np.exp(-((y - PAD_C_V9[1] * s_) / PAD_R_V9[0]) ** 2 - ((z - PAD_C_V9[2]) / PAD_R_V9[1]) ** 2)
            w = w * smoothstep(104.0 + mz, 120.0 + mz, x)
            return B - PAD_H_V9 * MM * w

        ylo, yhi = sorted(((PAD_C_V9[1] - 30.0) * s, (PAD_C_V9[1] + 30.0) * s))
        ops.append(v6.Op("union", pad, v6.v(100.0 + mz, ylo, -48.0), v6.v(170.0 + mz, yhi, 2.0), 0.6 * MM))

    def lower_lip(P, B):
        y, z, x = P[..., 1] / MM, P[..., 2] / MM, P[..., 0] / MM
        w = np.exp(-((y - LOWER_LIP_V9[0]) / LOWER_LIP_V9[2]) ** 2 - ((z - LOWER_LIP_V9[1]) / LOWER_LIP_V9[3]) ** 2)
        w = w * smoothstep(104.0 + mz, 118.0 + mz, x)
        return B - LOWER_LIP_V9[4] * MM * w

    ops.append(v6.Op("union", lower_lip, v6.v(100.0 + mz, -25.0, -45.0), v6.v(170.0 + mz, 25.0, -12.0), 0.6 * MM))

    def chin(P, B):
        y, z, x = P[..., 1] / MM, P[..., 2] / MM, P[..., 0] / MM
        w = np.exp(-((y - CHIN_V9["c"][0]) / CHIN_V9["r"][0]) ** 2 - ((z - CHIN_V9["c"][1]) / CHIN_V9["r"][1]) ** 2)
        w = w * smoothstep(96.0 + mz, 112.0 + mz, x)
        return B - CHIN_V9["h"] * MM * w

    ops.append(v6.Op("union", chin, v6.v(92.0 + mz, -30.0, -62.0), v6.v(170.0 + mz, 30.0, -20.0), 0.8 * MM))
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
        ops.append(v6.Op("union", (lambda s_: lambda P, B=None: lid_band_sd(P, s_))(s), c - rr, c + rr, 0.7 * MM))
    for s in (1.0, -1.0):
        def nostril(P, B, s_=s):
            q = np.stack([P[..., 1], P[..., 2]], -1) / MM
            d = nostril_sd_mm(q, s_) * MM
            d = np.maximum(d, v6.NOSE_X0 * MM - P[..., 0])
            return np.maximum(d, -B - 3.5 * MM)

        poly = np.asarray([(y * s, z) for y, z in v6.NOSTRIL_POLY])
        lo = np.array([v6.NOSE_X0, poly[:, 0].min() - 2.0, poly[:, 1].min() - 2.0]) * MM
        hi = np.array([v6.NOSE_X0 + 47.0, poly[:, 0].max() + 2.0, poly[:, 1].max() + 2.0]) * MM
        ops.append(v6.Op("subtract", nostril, lo, hi, 0.35 * MM))
    ops.append(v6.groove_op(v6.PHILTRUM, (1, 2), 0, 118.0 + mz, 185.0 + mz, [0.30, 0.42, 0.40], [1.0, 1.1, 0.9], 0.45))
    for s in (1.0, -1.0):
        poly = [(y * s, z) for y, z in LIP_Y_V9]
        ops.append(v6.groove_op(poly, (1, 2), 0, 100.0 + mz, 185.0 + mz, [0.40, 0.36, 0.30, 0.18], [1.1, 1.0, 0.7, 0.3], 0.55))
    # mouth notch between the upper lip and the chin (profile), unpigmented
    ops.append(v6.groove_op(MOUTH_NOTCH, (1, 2), 0, 100.0 + mz, 185.0 + mz, [0.25, 0.45, 0.25], [0.3, 0.7, 0.3], 0.9))
    # conchal cavity: carve the head out of each pinna's cup
    c = ear_cavity()
    hi = c["org"] + (np.array(c["G"].shape) - 1) * c["vs"]
    ops.append(v6.Op("subtract", lambda P, B=None: ear_cavity_sd(P), c["org"], hi, 1.5 * MM, frame="body"))
    return ops


# ---------------------------------------------------------------------------
# Pinna (round 7)
# ---------------------------------------------------------------------------

EAR_OPEN_OUT_V9 = -6.0  # deg (round 6: 24): the opening turned 30 deg forward
EAR_LEAN_OUT_V9 = 32.0


def ear_arrays_v9(side=1.0, n_t=110, n_face=52, n_rim=9, sdf=None):
    """Round-6 pinna (v8.ear_arrays_v8) with the round-7 changes (judged
    round 6: a glossy horizontal ribbing across the inner face, a grey chip
    where the Henry's-pocket notch met the lowest ridge, an airplane-ear
    opening facing sideways):

    - the three wide antihelical bands are replaced by two small cartilage
      ridges (0.7 mm) near the canal entrance, confined to the conchal floor;
    - antitragus 2.2 mm and tragus flap 2.0 mm (round 6: 3.2 / 3.0);
    - Henry's pocket: a 5 mm lobe on the lateral margin at 7-20 % height with
      a clean 2.6 mm notch above it; the back crease is 0.2 of the local
      thickness (round 6's crease and ridge met in a flake);
    - the ear frame is set by EAR_OPEN_OUT_V9 / EAR_LEAN_OUT_V9."""
    H = A.ear_h / MM
    W0 = A.ear_chord / MM
    tip = A.ear_tip_r / MM
    t_lo = -26.0 / H
    ts = np.concatenate([np.linspace(t_lo, 0.0, 16, endpoint=False), np.linspace(0.0, 1.0, n_t)])
    uf = np.sin(np.linspace(-0.5 * math.pi, 0.5 * math.pi, n_face))
    rings, attrs = [], []
    tcap = 1.0 - 1.6 * tip / H
    thin = 1.0 - 0.55 * smoothstep(0.55, 1.0, np.abs(uf))
    for t in ts:
        tc = float(np.clip(t, 0.0, 1.0))
        W = 2.0 * tip + (W0 - 2.0 * tip) * (1.0 - tc) ** 0.60
        if tc > tcap:
            W = W * math.sqrt(max(1.0 - ((tc - tcap) / (1.0 - tcap)) ** 2, 0.0)) + 0.3
        bend = 70.0 + 135.0 * (1.0 - tc) ** 0.85
        if t < 0:
            f = min(-t / abs(t_lo), 1.0)
            W *= 1.0 - 0.60 * f
            bend += 75.0 * f
        phi = math.radians(bend)
        R = 0.5 * W if phi >= math.pi else 0.5 * W / math.sin(0.5 * phi)
        S = R * phi
        kap = 1.0 / R
        hp = float(v6._bump(np.array(tc), 0.07, 0.20))
        notch = float(v6._bump(np.array(tc), 0.235, 0.29))
        w_med = 0.47 * S
        w_lat = 0.53 * S + 5.0 * hp - 2.6 * notch
        T = (A.ear_t0 + (A.ear_t1 - A.ear_t0) * tc) / MM
        if tc > tcap:
            T *= max(0.5, math.sqrt(max(1.0 - ((tc - tcap) / (1.0 - tcap)) ** 2, 0.0)))
        z = t * H
        xlean = -6.0 * tc ** 2 - 12.0 * min(t, 0.0) / t_lo
        ymed = -6.0 * min(t, 0.0) / t_lo

        def arc(sarc):
            a = kap * sarc
            y = np.sin(a) / kap
            x = (1.0 - np.cos(a)) / kap
            nin = np.stack([np.cos(a), -np.sin(a)], -1)
            tan = np.stack([np.sin(a), np.cos(a)], -1)
            return np.stack([x, y], -1), nin, tan

        s_front = np.where(uf < 0, uf * w_med, uf * w_lat)
        p, nin, tan = arc(s_front)
        ridge = np.zeros_like(uf)
        for tk in (0.025, 0.075):
            ridge += 0.7 * math.exp(-((tc - tk) / 0.020) ** 2) * (1.0 - smoothstep(0.15, 0.42, np.abs(uf + 0.05)))
        ridge += 2.2 * math.exp(-((t - 0.02) / 0.06) ** 2) * np.exp(-((uf - 0.74) / 0.15) ** 2)  # antitragus
        ridge += 2.0 * math.exp(-((t + 0.02) / 0.06) ** 2) * np.exp(-((uf + 0.80) / 0.12) ** 2)  # tragus flap
        Tl = T * thin
        front = p + nin * (0.5 * Tl + ridge)[:, None]
        crease = 0.2 * Tl * hp * np.exp(-((uf - 0.80) / 0.06) ** 2)
        back = p - nin * (0.5 * Tl - crease)[:, None]
        rim_pts, rim_u = [], []
        roll_fade = 1.0 - smoothstep(0.0, 0.35, tc)
        for end in (+1, -1):
            pe, ne, te = arc(np.array([w_lat if end > 0 else -w_med]))
            pe, ne, te = pe[0], ne[0], te[0] * end
            Te = T * thin[-1 if end > 0 else 0]
            roll = (0.45 if end < 0 else 0.25) * roll_fade
            rr = 0.5 * Te + roll
            pe = pe + ne * 0.7 * roll
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
        f_ring = np.concatenate([np.ones(n_face), -np.ones(n_rim), -np.ones(n_face), -np.ones(n_rim)])
        x = ring2[:, 0] + xlean
        y = ring2[:, 1] - ymed
        fade = 1.0 - smoothstep(0.0, 0.30, t)
        zz = np.full_like(x, z) - 0.45 * np.maximum(ring2[:, 1], 0.0) * fade
        tw = math.radians(A.ear_twist) * (1.0 - tc) ** 1.5
        x, y = x * math.cos(tw) - y * math.sin(tw), x * math.sin(tw) + y * math.cos(tw)
        rings.append(np.stack([x, y, zz], -1))
        attrs.append(np.stack([np.full_like(x, t), u_ring, f_ring], -1))
    return v8._ear_finish(np.array(rings) * MM, np.array(attrs), side, sdf, n_face, n_rim)


# ---------------------------------------------------------------------------
# Markings, follicles, coat and groom fields (round 7)
# ---------------------------------------------------------------------------

FOLLICLE_SEED = 7707


def follicle_grid_v9(s=1.0):
    """Mystacial follicles on one side (head frame y (>0), z mm): 4 rows of 4
    following the (lifted) pad, each jittered ~0.6 mm per side (round 6's
    machine-regular grid read as painted freckles). Returns (row, col, y, z)."""
    rng = np.random.default_rng(FOLLICLE_SEED + (0 if s > 0 else 101))
    out = []
    for row in range(4):
        for col in range(4):
            y = 9.5 + 4.4 * col + 1.2 * row + float(rng.normal(0.0, 0.6))
            z = -15.5 - 3.7 * row - 1.1 * col - 0.2 * col * col + float(rng.normal(0.0, 0.55))
            out.append((row, col, y, z))
    return out


def mystacial_roots_v9():
    """Whisker-bearing follicles (every column but the most rostral one), at
    the jittered follicle positions, so each whisker emerges from its pit."""
    out = []
    for s in (1.0, -1.0):
        for row, col, y, z in follicle_grid_v9(s):
            if col == 0:
                continue
            out.append((s, row, col - 1, np.array([v6.NOSE_X0 - 6.0, y * s, z])))
    return out


def ear_near_weight_v9(Ph):
    """~1 on the head skin at each ear base, falling off smoothly over ~30 mm
    (round 6's sharp ring gave a ridge of fur round the skull)."""
    w = np.zeros(Ph.shape[:-1])
    for s in (1.0, -1.0):
        x, y, z = v8.ear_q(Ph, s)
        e = np.sqrt(((x - 30.0) / 42.0) ** 2 + (y / 60.0) ** 2 + (z / 22.0) ** 2)
        w = np.maximum(w, 1.0 - smoothstep(0.50, 1.45, e))
    return w


def ear_behind_weight_v9(Ph):
    w = np.zeros(Ph.shape[:-1])
    for s in (1.0, -1.0):
        x, y, z = v8.ear_q(Ph, s)
        e = np.sqrt(((x - 30.0) / 42.0) ** 2 + (y / 60.0) ** 2 + (z / 22.0) ** 2)
        w = np.maximum(w, (1.0 - smoothstep(0.7, 1.7, e)) * (1.0 - smoothstep(-6.0, 16.0, x)))
    return w


def rim_noise(Pw, seed):
    """Spatial noise (0..1) along the pinna margins, ~5 mm correlation."""
    return v6.fbm(np.asarray(Pw, float), 0.005, 2, seed)


def coat_fields_v9(Pw, Nw, ex=None):
    """Round 7 coat, region, groom and layer fields (replaces
    v8.coat_fields_v8). Changes, per judged defect:

    - bib: the vertically stretched 'finger' and 'streak' noises (the two
      dark drips down the bib) are gone; the boundary is broken by isotropic
      9 mm tufts and 30-60 mm lobes and mixes hair by hair over up to 4 mm;
    - body stripes start below the neck (world z < -125) and are broken by
      noise (round 6's first band sat at the head-neck junction as a collar);
    - lids: pigment only within ~0.6 mm of the fissure (round 6: a 0.5-1 mm
      band plus a 0.65 band out to 3.5 mm, a cartoon eyeliner); the fur
      reaches ~0.5 mm from the margin, <= 0.7 mm long there, growing out;
    - mouth: pigment only on the short inverted Y; nostrils pigmented only
      inside the holes; the philtrum is not painted;
    - follicles: jittered, small grey pits (Detail B), no dark hair;
    - ear base: the short coat blends into the crown over ~30 mm; the
      conchal cavity carries only sparse 1.5 mm pale hair (round 6: 5 mm
      lifted hair made a collar);
    - pinna: bare pink-grey skin in the upper-central third, short fine hair
      toward the margins and base, 2-4 mm back coat combed to the tip, and
      margin hair whose length and density vary along the rim;
    - neck sides: shorter coat (the narrower neck);
    - layer weights for the per-region guard layers: face, ruff (long head
      coat), body, chest (the bib locks) and ear back."""
    Pw = np.asarray(Pw, float)
    Nw = np.asarray(Nw, float)
    n = len(Pw)
    is_ear, ear_t, ear_u, ear_face = v6.ex_arrays(n, ex)
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
    jit = (v6.fbm(Pw, 0.0011, 2, 11.0) - 0.5) * 1.3 + (v6.fbm(Pw, 0.022, 2, 12.0) - 0.5) * 3.2
    edge = 0.7
    cup = cup_weight_v9(Pw) * (~earm)

    # ---- white: muzzle, blaze, chin, throat, bib
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
    white = 1.0 - smoothstep(-ew, ew, d_white + jit + lobes + tufts)

    # ---- mackerel strokes
    dm = v8.dist_fields_per_marking(P3)
    stripe = np.zeros(n)
    for nm, d in dm.items():
        e = v8.MARK_EDGE.get(nm, edge)
        wj = 1.0 if nm not in v8.MARK_EDGE else 1.8
        stripe = np.maximum(stripe, 1.0 - smoothstep(-e, e, d + wj * jit))
    ang = np.arctan2(yw, xw + 40.0)
    zz = zw + 5.0 * np.sin(ang * 2.0 + 0.7) + 3.0 * np.sin(ang * 5.0 + 1.3) + (v6.fbm(Pw, 0.040, 2, 45.0) - 0.5) * 16.0
    per = 34.0
    ph_ = np.mod(zz + 8.0, per) - 0.5 * per
    wband = 5.6 + 1.2 * np.sin(ang * 3.0)
    brk = (v6.fbm(Pw, 0.018, 2, 47.0) - 0.5) * 9.0
    body_band = (np.abs(ph_) - wband + np.maximum(brk, 0.0)) * smoothstep(-120.0, -150.0, zw)
    dors = np.maximum(ay - 8.0, xw + 60.0) + 1e3 * (zw > -20.0)
    d_body = np.minimum(body_band + 1e3 * (zw > -125.0), dors)
    stripe = np.maximum(stripe, 1.0 - smoothstep(-edge, edge, d_body + jit))
    thumb = _bump(ear_t, 0.30, 0.60) * _bump(ear_u, -0.30, 0.40) * back
    ear_rim_c = smoothstep(0.86, 0.98, au)
    ear_back_dark = (0.62 + 0.25 * smoothstep(0.70, 0.95, ear_t)) * (1.0 - 0.3 * ear_rim_c)
    stripe = np.where(earm, np.where(inner, 0.0, ear_back_dark), stripe)
    white = np.where(inner, 1.0, white)
    stripe = np.clip(stripe * (1.0 - 0.6 * thumb), 0.0, 1.0)
    white = np.maximum(white, 0.6 * smoothstep(0.3, 0.7, cup))
    stripe = np.clip(stripe * (1.0 - white) * (1.0 - cup), 0.0, 1.0)

    # ---- follicles: jittered grey pits
    on_pad = smoothstep(112.0 + mz, 120.0 + mz, x) * smoothstep(0.15, 0.40, Nh[:, 0])
    fol_d = np.full(n, 1e3)
    m_pad = on_pad > 0
    if m_pad.any():
        for s in (1.0, -1.0):
            ms = m_pad & ((y > 0) if s > 0 else (y <= 0))
            if not ms.any():
                continue
            grid = follicle_grid_v9(s)
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
    spect = (1.0 - smoothstep(4.0, 7.0, d_fis)) * smoothstep(1.6, 2.4, d_fis)
    pale = np.clip(np.maximum(0.45 * spect, 0.6 * thumb), 0.0, 1.0) * (1.0 - cup)

    # ---- regions
    q2 = np.stack([y, z], -1)
    d_leather = v6.sd_poly2d(q2, v6.leather_poly())
    nose = (1.0 - smoothstep(-0.25, 0.25, d_leather)) * smoothstep(v6.NOSE_X0 - 3.0, v6.NOSE_X0 + 1.0, x) * smoothstep(-0.25, 0.05, Nh[:, 0])
    rim = (1.0 - smoothstep(0.35, 0.95, -d_leather)) * nose
    pig = np.zeros(n)
    pig = np.maximum(pig, 1.0 - smoothstep(0.30, 0.65, np.abs(d_fis)))
    pig = np.maximum(pig, (d_fis < 0).astype(float) * near_eye)
    fr = smoothstep(v6.NOSE_X0 - 6.0, v6.NOSE_X0, x)
    nost = np.full(n, 1e3)
    for s in (1.0, -1.0):
        nost = np.minimum(nost, nostril_sd_mm(q2, s))
    pig = np.maximum(pig, 0.85 * (1.0 - smoothstep(-0.25, 0.15, nost)) * fr)
    lipd = np.full(n, 1e3)
    for s in (1.0, -1.0):
        lipd = np.minimum(lipd, v6.dist_poly2d(q2, [(yy * s, zz_) for yy, zz_ in LIP_Y_V9]))
    lipf = smoothstep(110.0 + mz, 118.0 + mz, x) * smoothstep(0.1, 0.35, Nh[:, 0])
    pig = np.maximum(pig, 0.65 * (1.0 - smoothstep(0.25, 0.55, lipd)) * lipf)
    d_lac = dm.get("lacrimal", np.full(n, 1e3))
    pig = np.maximum(pig, 0.35 * (1.0 - smoothstep(-0.1, 0.5, d_lac + 0.4 * jit)))
    pig = np.where(earm, 0.0, pig)
    lipm = (1.0 - smoothstep(0.25, 0.45, lipd)) * lipf
    conch = inner * (1.0 - smoothstep(0.0, 0.25, ear_t)) * (1.0 - smoothstep(0.45, 0.9, au))
    ear_in = np.where(inner, 1.0 - 0.2 * smoothstep(0.86, 0.99, au), np.where(back, 0.5, 0.0))
    ear_in = np.maximum(ear_in, cup)
    pig = np.maximum(pig, np.maximum(0.60 * conch, 0.6 * cup))
    vessel = np.where(inner, v8.ear_vessels(ear_t, ear_u), 0.0)

    # ---- groom: length (mm), lift (deg), density
    keys = [
        ((141 + mz, 0, -8), 1.8, 8), ((130 + mz, 0, 12), 2.4, 10), ((112 + mz, 0, 32), 3.0, 11), ((95, 0, 52), 3.8, 13), ((64, 0, 72), 5.0, 17),
        ((15, 0, 88), 6.5, 22), ((-35, 0, 82), 8.5, 24), ((-72, 0, 42), 10.0, 22), ((-90, 0, 0), 10.5, 22),
        ((136 + mz, 14, -20), 2.2, 9), ((130 + mz, 26, -30), 2.8, 10), ((114 + mz, 33, -42), 3.4, 10), ((112 + mz, 0, -50), 3.0, 10), ((84, 0, -80), 6.5, 10),
        ((92, 40, 21), 2.2, 12), ((86, 36, 44), 2.8, 8), ((80, 62, 5), 4.2, 13), ((50, 82, 5), 6.5, 14), ((24, 86, -18), 12.0, 16),
        ((4, 80, -44), 15.0, 18), ((32, 72, -42), 10.0, 14), ((46, 0, -86), 11.0, 18), ((0, 62, 70), 5.0, 13),
        ((-40, 55, 50), 8.0, 20), ((-70, 60, 10), 12.0, 22),
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
    neckm = smoothstep(-50.0, -88.0, zw) * (1.0 - smoothstep(20.0, 55.0, x))
    headw = headw * (1.0 - neckm)
    front = smoothstep(-0.2, 0.4, Nw[:, 0])
    ruff = _bump(zw, -235.0, -110.0) * front
    neck = _bump(zw, -150.0, -55.0)
    nside = smoothstep(30.0, 70.0, np.abs(yw)) * (1.0 - front)
    nape_b = smoothstep(-0.25, -0.65, Nw[:, 0]) * (1.0 - smoothstep(40.0, 80.0, np.abs(yw)))
    bodyL = 16.0 + 7.0 * ruff + 10.0 * neck * (1.0 - 0.7 * nside) + 3.0 * smoothstep(-150.0, -300.0, zw) - 11.0 * neck * nape_b
    arm = smoothstep(70.0, 100.0, ay) * smoothstep(-150.0, -210.0, zw)
    bodyL = bodyL * (1.0 - 0.35 * arm)
    Lh = headL * headw + bodyL * (1.0 - headw)
    # periocular: <= 0.7 mm within ~1.5 mm of the margin, growing to the
    # local coat length by ~7 mm
    lcap = 0.7 + 0.45 * np.maximum(d_fis - 1.0, 0.0) ** 1.25
    Lh = np.where(d_fis < 9.0, np.minimum(Lh, lcap), Lh)
    near = ear_near_weight_v9(Ph) * (1.0 - smoothstep(0.3, 0.6, cup))
    behind = ear_behind_weight_v9(Ph)
    Lh = Lh * (1.0 - near) + np.minimum(Lh, 5.5 + 2.5 * behind) * near
    latm = np.zeros(n)
    for s_ in (1.0, -1.0):
        ex_, ey_, ez_ = v8.ear_q(Ph, s_)
        latm = np.maximum(latm, smoothstep(18.0, 34.0, ey_) * (1.0 - smoothstep(52.0, 64.0, ey_)) * _bump(ex_, -6.0, 62.0) * (1.0 - smoothstep(14.0, 26.0, ez_)) * smoothstep(-40.0, -26.0, ez_))
    latm = latm * (~earm)
    Lh = Lh * (1.0 - latm) + np.minimum(Lh, 3.2) * latm
    # pinna
    rimz = smoothstep(0.84, 0.98, au)
    rn1 = rim_noise(Pw, 61.0)
    rn2 = rim_noise(Pw, 67.0)
    rim_len = 0.35 + 0.65 * rn1
    rim_den = np.clip(1.6 * (rn2 - 0.45), 0.0, 1.0) ** 1.5
    L_back = 4.5 + 3.5 * (1.0 - smoothstep(0.05, 0.9, ear_t))
    pocket = _bump(ear_t, 0.03, 0.26) * smoothstep(0.50, 0.75, ear_u)
    L_back = L_back * (1.0 - 0.45 * pocket)
    L_back = L_back * (1.0 - rimz) + L_back * rim_len * rimz
    low_med = (1.0 - smoothstep(-0.55, -0.25, ear_u)) * (1.0 - smoothstep(0.40, 0.62, ear_t))
    lat_band = smoothstep(0.80, 0.90, ear_u)
    base_band = 1.0 - smoothstep(0.10, 0.24, ear_t)
    bare = _bump(ear_t, 0.52, 1.05) * (1.0 - smoothstep(0.35, 0.65, au))
    lower = 1.0 - smoothstep(0.45, 0.66, ear_t)
    roll = smoothstep(0.975, 0.995, au)
    L_in = np.minimum(1.4 + 1.8 * lower * (1.0 - bare) + 1.0 * low_med + 0.6 * lat_band, 4.0) * (1.0 - rimz) + (1.6 + 0.9 * lat_band) * rim_len * rimz
    L = np.where(earm, np.where(inner, L_in, L_back), Lh)
    L = np.where(cup > 0.5, 1.5, L)
    L = L * (0.94 + 0.12 * v6.fbm(Pw, 0.012, 2, 2.0))
    # lift
    lift_h = (5.0 + 3.0 * smoothstep(40.0, 80.0, z) * (1 - np.clip(-zw / 100.0, 0, 1))
              + 8.0 * np.exp(-((x - 18) ** 2 + (ay - 82) ** 2 + (z + 34) ** 2) / 1100.0))
    throat_front = smoothstep(0.2, 0.7, Nw[:, 0])
    lift_b = 12.0 + 4.0 * ruff + 14.0 * neck * (1.0 - 0.8 * throat_front) * (1.0 - 0.7 * nape_b) - 3.0 * arm
    hb = np.maximum(smoothstep(-60.0, -125.0, zw), neckm)
    lift = lift_h * (1.0 - hb) + lift_b * hb
    lift = lift - 3.0 * np.exp(-((x - 122 - mz) ** 2 + (ay - 20) ** 2 + (z + 28) ** 2) / 500.0)
    wper = 1.0 - smoothstep(2.0, 6.0, np.maximum(d_fis, 0.0))
    lift = lift * (1.0 - wper) + np.minimum(lift, 2.5) * wper
    lift = lift * (1.0 - near) + np.minimum(lift, 4.0) * near
    lift = lift * (1.0 - latm) + np.minimum(lift, 1.5) * latm
    lift = np.where(earm, np.where(inner, 12.0 + 8.0 * low_med, 1.5 + 2.0 * rimz * rn1), lift)
    lift = np.where(cup > 0.5, 6.0, lift)
    # density
    density = np.clip(7.0 / np.maximum(L, 1.0), 0.35, 1.0)
    deep = (1.0 - smoothstep(0.05, 0.14, ear_t)) * (1.0 - smoothstep(0.45, 0.7, au))
    inner_d = np.clip(0.06 + 0.40 * lower + 0.20 * low_med + 0.25 * lat_band + 0.20 * base_band, 0.0, 0.65) * (1.0 - deep) * (1.0 - bare)
    inner_d = (inner_d * (1.0 - rimz) + 0.35 * rim_den * rimz) * (1.0 - roll) + 0.45 * rim_den * roll
    back_d = ((0.78 - 0.12 * smoothstep(0.6, 1.0, ear_t)) * (1.0 - rimz) + 0.55 * rim_den * rimz) * (1.0 - roll) + 0.45 * rim_den * roll
    density = np.where(earm, np.where(inner, inner_d, back_d), density)
    density = np.where(cup > 0.5, 0.25, density)
    density = density * smoothstep(-598.0, -585.0, zw)
    # sharp exclusions (fur mask)
    topw = smoothstep(-2.0, 2.0, z - 2.0)
    nose_ex = (1.0 - smoothstep(-0.25, 0.25, d_leather + 0.30 * topw + 0.30 * jit * topw)) * smoothstep(v6.NOSE_X0 - 3.0, v6.NOSE_X0 + 1.0, x) * smoothstep(-0.25, 0.05, Nh[:, 0])
    excl = (1.0 - nose_ex) * (1.0 - lipm) * smoothstep(0.30, 0.60, d_fis)
    excl = excl * np.where(x > v6.NOSE_X0 - 4.0, smoothstep(0.0, 0.8, nost + 0.5), 1.0)
    excl = excl * (1.0 - 0.85 * (1.0 - smoothstep(-0.1, 0.2, fol_d)) * on_pad)
    excl = np.where(earm, 1.0, excl)
    # layer weights (sum to 1)
    w_ear = back.astype(float)
    w_chest = (~earm) * smoothstep(-100.0, -135.0, zw) * smoothstep(-0.05, 0.45, Nw[:, 0]) * (1.0 - smoothstep(60.0, 85.0, np.abs(yw)))
    w_body = (~earm) * smoothstep(-58.0, -108.0, zw) * (1.0 - w_chest)
    rest = np.clip(1.0 - w_ear - w_chest - w_body, 0.0, 1.0) * (~back)
    chin_mid = (1.0 - smoothstep(12.0, 30.0, ay)) * smoothstep(-0.1, 0.4, Nw[:, 0]) * smoothstep(-15.0, -40.0, z)
    w_ruff = rest * smoothstep(5.5, 9.5, Lh) * (~earm) * (1.0 - smoothstep(0.3, 0.6, cup)) * (1.0 - chin_mid)
    w_face = np.clip(rest - w_ruff, 0.0, 1.0)
    return dict(white=np.clip(white, 0, 1), stripe=np.clip(stripe, 0, 1), pale=pale, nose=nose, pig=np.clip(pig, 0, 1), ear_inner=ear_in,
                length=L * MM, density=np.clip(density, 0, 1), excl=np.clip(excl, 0, 1), lift=lift, d_fis=d_fis, lip=lipm,
                vessel=np.clip(vessel, 0, 1), rim=np.clip(np.where(earm, smoothstep(0.93, 0.995, au), rim), 0, 1), follicle=np.clip(follicle, 0, 1), cup=cup, near_ear=near,
                w_face=w_face, w_ruff=w_ruff, w_body=w_body, w_chest=w_chest, w_ear=w_ear)


def fur_direction_v9(Pw, Nw, ex=None):
    """Round-6 flow (v8.fur_direction_v8) with the round-7 changes: the ear
    back hair near the rims turns slightly inward (its tips wrapped the thin
    margin, printed dark specks on the inner face and drew an even outline
    under rim light) and the margin hair is sparse and patchy; the head coat turns up
    the ear axis over a wider, softer band behind each ear (no ridge where
    the two flows met); and the body flow carries a +-15 deg low-frequency
    swirl so the torso coat does not read as parallel painted strokes."""
    Pw = np.asarray(Pw, float)
    Nw = np.asarray(Nw, float)
    n = len(Pw)
    is_ear, ear_t, ear_u, ear_face = v6.ex_arrays(n, ex)
    earm = is_ear > 0.5
    t = v8.fur_direction_v8(Pw, Nw, ex)
    Ph = Pw @ v6.head_R()
    sy = np.where(Ph[:, 1] >= 0, 1.0, -1.0)
    near_e = ear_behind_weight_v9(Ph)
    for s in (1.0, -1.0):
        F = v6.ear_frame(s)
        ax = F[:, 2] @ v6.head_R().T
        m = earm & (sy == s)
        if m.any():
            # pinna hair combs toward the ear tip, so near the slanted
            # margins it runs along the edge instead of crossing it (hair
            # combed up the ear axis crossed the margins and drew an even
            # white outline under rim light)
            base = A.ear_base * np.array([1.0, s, 1.0])
            tip_w = (base + F @ np.array([-6.0 * MM, 0.0, A.ear_h])) @ v6.head_R().T
            dt = tip_w[None, :] - Pw[m]
            t[m] = dt / (np.linalg.norm(dt, axis=1, keepdims=True) + 1e-9)
        mh = (~earm) & (sy == s)
        if mh.any():
            wn = (0.7 * near_e[mh])[:, None]
            t[mh] = t[mh] * (1.0 - wn) + ax[None, :] * wn
    zw = Pw[:, 2] / MM
    hb = smoothstep(-70.0, -130.0, zw) * (~earm)
    if hb.any():
        a = (v6.fbm(Pw, 0.05, 2, 41.0) - 0.5) * 0.55 * hb
        b = np.cross(Nw, t)
        t = t * np.cos(a)[:, None] + b * np.sin(a)[:, None]
    t = t - np.sum(t * Nw, 1, keepdims=True) * Nw
    t /= np.linalg.norm(t, axis=1, keepdims=True) + 1e-9
    return t


def grow_guides_v9(pos, nrm, ex, npts, rng, length_scale=None, lift_add=None, lay=0.8):
    """v8.grow_guides_v8 with slightly curved chest locks (one slow bend per
    guide instead of a wave) and a stronger per-guide bend on the body."""
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
    droop = np.clip((Lg / MM - 6.0) / 30.0, 0.0, 0.55)
    chest = f["w_chest"]
    body = f["w_body"]
    wave_amp = rng.uniform(0.03, 0.10, n) * (1.0 - chest)
    freq = rng.uniform(0.6, 1.3, n)
    phase = rng.random(n) * 2 * math.pi
    bend = rng.normal(0.0, 0.07, n) * (1.0 + 1.2 * body) + chest * rng.choice([-1.0, 1.0], n) * rng.uniform(0.18, 0.34, n)
    is_ear = ex["is_ear"] > 0.5 if ex is not None else np.zeros(n, bool)
    lay_v = np.where(is_ear, 0.95, lay)
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


LAYER_ATTRS = ("fd_face", "fd_ruff", "fd_body", "fd_chest", "fd_ear", "fd_under")


def build_skin_v9(coll):
    """v6.build_skin plus the per-layer density attributes on the cage."""
    dense, tgt, cage = _V6_BUILD_SKIN(coll)
    co, nr = v6.mesh_arrays(cage.data)
    ex = {k: v6.attr_array(cage.data, k) for k in v6.EAR_ATTRS}
    f = coat_fields_v9(co, nr, ex)
    for nm, key in (("fd_face", "w_face"), ("fd_ruff", "w_ruff"), ("fd_body", "w_body"), ("fd_chest", "w_chest"), ("fd_ear", "w_ear")):
        a = cage.data.attributes.new(nm, "FLOAT", "POINT")
        a.data.foreach_set("value", (f["density"] * f[key]).astype(np.float32))
    a = cage.data.attributes.new("fd_under", "FLOAT", "POINT")
    a.data.foreach_set("value", (f["density"] * (1.0 - 0.6 * f["w_ear"]) * (1.0 - f["cup"])).astype(np.float32))
    return dense, tgt, cage


_V6_BUILD_SKIN = None


GUARD_LAYERS = [
    # name, density attribute, clumps (factor, guide distance, shape, tip spread), noise, noise scale, frizz, jitter, r0
    ("CatBaseV6_Fur_Face", "fd_face", ((0.60, 1.7 * MM, 0.40, 0.12 * MM), (0.45, 0.8 * MM, 0.30, 0.05 * MM)), 0.12 * MM, 260.0, 0.05 * MM, (0.75, 1.25), 0.060 * MM),
    ("CatBaseV6_Fur_Ruff", "fd_ruff", ((0.86, 5.5 * MM, 0.50, 0.45 * MM), (0.60, 2.0 * MM, 0.35, 0.15 * MM), (0.30, 0.7 * MM, 0.25, 0.0)), 0.20 * MM, 140.0, 0.08 * MM, (0.6, 1.45), 0.066 * MM),
    ("CatBaseV6_Fur_Body", "fd_body", ((0.86, 7.5 * MM, 0.50, 0.8 * MM), (0.58, 2.6 * MM, 0.35, 0.2 * MM), (0.30, 0.8 * MM, 0.25, 0.0)), 0.30 * MM, 90.0, 0.10 * MM, (0.65, 1.35), 0.068 * MM),
    ("CatBaseV6_Fur_Chest", "fd_chest", ((0.92, 6.0 * MM, 0.62, 0.6 * MM), (0.62, 2.2 * MM, 0.40, 0.15 * MM)), 0.25 * MM, 110.0, 0.08 * MM, (0.75, 1.3), 0.066 * MM),
    ("CatBaseV6_Fur_EarBack", "fd_ear", ((0.45, 1.4 * MM, 0.30, 0.08 * MM), (0.30, 0.6 * MM, 0.25, 0.0)), 0.05 * MM, 300.0, 0.03 * MM, (0.75, 1.25), 0.050 * MM),
]


def build_groom_v9(coll, skin, images, n_guides):
    """Round 7 groom (judged round 6: smooth, unbroken outlines; a smeared,
    stroke-like torso coat; a fish-scale ear back): the guard coat is split
    into five layers by smooth density masks that sum to the round-6
    density, each with its own clumping: short, fine face coat; long crown
    and cheek ruff with 5.5 mm clumps and a wide length jitter (tufted
    silhouette); body coat with 7.5 mm clumps and tip spread (separated locks,
    no parallel streaks); the white chest in curved locks; and a fine 2-4 mm
    ear-back coat with almost no clumping. Undercoat as round 6. 14,000
    sampled stray guard hairs plus 2,600 fly-away hairs on the silhouette
    (cheek ruff, crown, nape, neck)."""
    rng = np.random.default_rng(v6.RNG_SEED)
    S = v6.evaluated_surface(skin)
    log("groom surface tris", len(S["tv"]))

    def wfn(c, n, ex):
        f = v6.coat_fields(c, n, ex)
        return f["density"] * np.maximum(f["excl"], 0.05) / np.maximum(f["length"], 2.5 * MM)

    pos, nrm, uv, ex = v6.sample_roots(S, n_guides, wfn, rng)
    strands, f = grow_guides_v9(pos, nrm, ex, 8, rng)
    v6.load_hair_assets()
    v6.length_jitter_group()
    layers = []
    cull = v6.eye_cull_group()
    # the five guard layers share one guide datablock and one material (the
    # layers differ only in their modifiers), which keeps the .blend small
    gdata = v6.make_curves("CatBaseV6_Fur_GuardGuides", strands, 0.064 * MM, 0.016 * MM, coll, uv=uv, surface=skin)
    gdata_ob = gdata
    gdata = gdata.data
    gdata.materials.append(v8.hair_material_v8("M_CatBaseV6_Fur_Guard", images, False, tip_alpha=True))
    bpy.data.objects.remove(gdata_ob, do_unlink=True)
    for li, (name, attr, clumps, noise, nscale, frizz, jitter, r0) in enumerate(GUARD_LAYERS):
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
    ob.data.materials.append(v8.hair_material_v8("M_CatBaseV6_Fur_Under", images, True, tip_alpha=False))
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
    # stray guard hairs + fly-aways on the silhouette
    n_stray = 14000
    sp_, sn_, suv, sex = v6.sample_roots(S, n_stray, wfn, rng)
    st, _ = grow_guides_v9(sp_, sn_, sex, 10, rng, length_scale=rng.uniform(1.12, 1.45, n_stray),
                           lift_add=rng.uniform(1.0, 6.0, n_stray), lay=0.78)
    fs = v6.coat_fields(sp_, sn_, sex)
    keep = (sex["is_ear"] < 0.5) & (fs["d_fis"] > 4.0) & (fs["excl"] > 0.95)
    st, suv = st[keep], suv[keep]

    def wfly(c, n, ex):
        f = v6.coat_fields(c, n, ex)
        zw = c[:, 2] / MM
        sil = f["w_ruff"] + 0.8 * f["w_body"] * (1.0 - smoothstep(-160.0, -230.0, zw)) + 0.3 * f["w_chest"]
        return f["density"] * np.maximum(f["excl"], 0.0) * sil

    n_fly = 2600
    fp, fn_, fuv, fex = v6.sample_roots(S, n_fly, wfly, rng)
    ft, _ = grow_guides_v9(fp, fn_, fex, 10, rng, length_scale=rng.uniform(1.45, 2.2, n_fly), lift_add=rng.uniform(7.0, 17.0, n_fly), lay=0.55)
    ffs = v6.coat_fields(fp, fn_, fex)
    fk = (fex["is_ear"] < 0.5) & (ffs["d_fis"] > 6.0) & (ffs["excl"] > 0.95)
    ft, fuv = ft[fk], fuv[fk]
    t = np.linspace(0, 1, st.shape[1])
    radii = np.concatenate([np.repeat(((0.072 * MM) * (1 - t) ** 1.3 + 0.008 * MM)[None], len(st), 0),
                            np.repeat(((0.050 * MM) * (1 - t) ** 1.2 + 0.006 * MM)[None], len(ft), 0)])
    ob = v6.make_curves("CatBaseV6_Fur_Stray", np.concatenate([st, ft]), 0, 0, coll, uv=np.concatenate([suv, fuv]), surface=skin, radii=radii)
    ob.parent = skin
    ob.data.materials.append(v8.hair_material_v8("M_CatBaseV6_Fur_Stray", images, False))
    m_ = ob.modifiers.new("CatBaseV6 Eye Cull", "NODES")
    m_.node_group = cull
    layers.append(ob)
    log(f"strays {len(st)} + fly-aways {len(ft)}")
    guides = v6.make_curves("CatBaseV6_Fur_Guides", strands, 0.1 * MM, 0.05 * MM, coll, uv=uv, surface=skin)
    guides.parent = skin
    guides.hide_render = True
    guides.hide_viewport = True
    return layers, guides


def build_inner_ear_furnishings_v9(coll, skin, images):
    """Round 7 furnishings (judged round 6: 260 invisible wisps; round 5's
    white furnished ears read more like a cat): 620 tufts of 3-6 pale cream
    hairs (~2,800 hairs, root radius 0.060 mm, each tuft a lock), 18-33 mm long (a sixth of the
    medial ones 30-38 mm, rising past the rim; the judged 8-15 mm are real-cat
    millimetres, and CatBaseV6 is 2.2x a real cat), rooted along the medial
    margin and the base and scattered over the lower two thirds of the inner
    face, never in its bare upper-central third. Each tuft leaves the skin
    at ~15 deg and runs up, out of the opening and across it (medial tufts
    laterally, antitragal tufts medially), arcing upward, so the tufts cross
    the dark concha from the front and break the ear's front edge in
    profile."""
    rng = np.random.default_rng(v6.RNG_SEED + 2)
    S = v6.evaluated_surface(skin)

    def wfn(c, n, ex):
        front = ex["is_ear"] * smoothstep(0.2, 0.6, ex["ear_face"])
        t, u = ex["ear_t"], ex["ear_u"]
        vis = smoothstep(0.0, 0.04, t)
        med = (1.0 - smoothstep(-0.80, -0.50, u)) * _bump(t, 0.02, 0.62)
        base = _bump(t, 0.0, 0.20) * (1.0 - smoothstep(0.60, 0.86, np.abs(u)))
        lower = _bump(t, 0.06, 0.58) * (1.0 - smoothstep(0.25, 0.60, np.abs(u + 0.05)))
        anti = smoothstep(0.45, 0.65, u) * (1.0 - smoothstep(0.86, 0.97, u)) * _bump(t, 0.0, 0.26)
        bare = _bump(t, 0.55, 1.05) * (1.0 - smoothstep(0.35, 0.65, np.abs(u)))
        return front * vis * (1.8 * med + 1.3 * base + 0.45 * lower + 0.6 * anti) * (1.0 - bare)

    n_tuft = 620
    cpos, cnrm, cuv, cex = v6.sample_roots(S, n_tuft, wfn, rng)
    npts = 12
    strands, uvs = [], []
    for i in range(n_tuft):
        s = 1.0 if (cpos[i] @ v6.head_R())[1] > 0 else -1.0
        F = v6.ear_frame(s)
        up = F[:, 2] @ v6.head_R().T
        fwd = F[:, 0] @ v6.head_R().T
        lat = F[:, 1] * s @ v6.head_R().T
        eu = cex["ear_u"][i]
        nn = cnrm[i]
        if eu < -0.45:
            d = 0.62 * up + 0.55 * lat + 0.50 * fwd + 0.25 * nn
            Lt = rng.uniform(30.0, 38.0) * MM if rng.random() < 0.17 else rng.uniform(18.0, 33.0) * MM
        elif eu > 0.45:
            d = 0.70 * up - 0.40 * lat + 0.45 * fwd + 0.25 * nn
            Lt = rng.uniform(16.0, 28.0) * MM
        else:
            d = 0.72 * up + 0.15 * lat * rng.normal() + 0.60 * fwd + 0.30 * nn
            Lt = rng.uniform(18.0, 30.0) * MM
        d /= np.linalg.norm(d) + 1e-9
        k = int(rng.integers(3, 7))
        curl = rng.normal(0, 0.10, 3)
        for _ in range(k):
            off = rng.normal(0.0, 0.35 * MM, 3)
            off -= (off @ nn) * nn
            p = cpos[i] + off - nn * 0.15 * MM
            fan = rng.normal(0.0, 0.09, 3)
            Lh = Lt * rng.uniform(0.7, 1.1)
            c2 = curl + rng.normal(0, 0.04, 3)
            pts = [p.copy()]
            for kk in range(1, npts):
                s_ = kk / (npts - 1)
                dd = d + fan * s_ ** 1.2 + c2 * s_ + up * 0.35 * s_ - np.array([0.0, 0.0, 0.10]) * s_ * s_
                dd /= np.linalg.norm(dd)
                p = p + dd * Lh / (npts - 1)
                pts.append(p.copy())
            strands.append(pts)
            uvs.append(cuv[i])
    strands = np.array(strands)
    uv = np.array(uvs)
    t = np.linspace(0, 1, npts)
    radii = np.repeat(((0.060 * MM) * (1 - t) ** 1.0 + 0.006 * MM)[None], len(strands), 0)
    ob = v6.make_curves("CatBaseV6_Fur_EarFurnishings", strands, 0, 0, coll, uv=uv, surface=skin, radii=radii)
    ob.parent = skin
    m, nt = v6.new_mat("M_CatBaseV6_EarFurnishing")
    out = N(nt, "ShaderNodeOutputMaterial", (900, 0))
    hb = N(nt, "ShaderNodeBsdfHairPrincipled", (300, 0))
    hb.parametrization = "COLOR"
    hb.model = "CHIANG"
    info = N(nt, "ShaderNodeHairInfo", (-400, 0))
    rj = N(nt, "ShaderNodeMapRange", (-200, 0))
    L(nt, info.outputs["Random"], rj.inputs["Value"])
    rj.inputs["To Min"].default_value = 0.82
    rj.inputs["To Max"].default_value = 1.05
    col = N(nt, "ShaderNodeVectorMath", (0, 0))
    col.operation = "SCALE"
    col.inputs[0].default_value = (0.70, 0.66, 0.57)
    L(nt, rj.outputs["Result"], col.inputs["Scale"])
    L(nt, col.outputs["Vector"], hb.inputs["Color"])
    hb.inputs["Roughness"].default_value = 0.34
    hb.inputs["Radial Roughness"].default_value = 0.4
    hb.inputs["Coat"].default_value = 0.0
    hb.inputs["IOR"].default_value = 1.3
    tip = N(nt, "ShaderNodeMapRange", (300, -300))
    L(nt, info.outputs["Intercept"], tip.inputs["Value"])
    tip.inputs["From Min"].default_value = 0.86
    tip.inputs["From Max"].default_value = 1.0
    tip.inputs["To Min"].default_value = 0.0
    tip.inputs["To Max"].default_value = 0.6
    trn = N(nt, "ShaderNodeBsdfTransparent", (500, -200))
    mx = N(nt, "ShaderNodeMixShader", (700, 0))
    L(nt, tip.outputs["Result"], mx.inputs["Fac"])
    L(nt, hb.outputs["BSDF"], mx.inputs[1])
    L(nt, trn.outputs["BSDF"], mx.inputs[2])
    L(nt, mx.outputs["Shader"], out.inputs["Surface"])
    ob.data.materials.append(m)
    log(f"ear furnishings: {n_tuft} tufts, {len(strands)} hairs")
    return ob


def build_vibrissae_v9(coll, skin):
    """v8.build_vibrissae_v8 on the round-7 (jittered, lifted) follicle pits."""
    return v8.build_vibrissae_v8(coll, skin)


# ---------------------------------------------------------------------------
# Materials (round 7)
# ---------------------------------------------------------------------------

EAR_SKIN_V9 = (0.40, 0.29, 0.275)
EAR_VEIN_BASE = 0.10  # vessel strength in reflected light (round 6: 0.55)
EAR_TRANSLUCENT = 0.10  # translucent lobe on the inner face (veins in transmitted light)
EAR_SSS_RADIUS = (0.62, 0.16, 0.21)  # pink-red, shorter (round 6: 1.0, 0.45, 0.30)
LEATHER_ROUGH = 0.45


def skin_material_v9(images):
    """Round 7 skin (judged round 6: a smooth mauve rubber inner ear with a
    painted vein map; saturated orange glow when backlit; a flat decal nose;
    reddish freckle follicles):

    - inner pinna: pale pink-grey (0.40, 0.29, 0.275); vessels at ~20 % of round
      6's strength in reflected light; a translucent lobe (0.10 on the inner
      face, 0.03 on the back) whose colour carries the vessels, so they read
      mainly in transmitted light; subsurface radius (0.62, 0.16, 0.21) mm,
      red longest and blue above green, so backlight glows pink-red, not
      orange;
    - nose leather: rose with a rose-brown margin, a fine 0.33 mm cobblestone
      bump (rounded cells, crevice darkening) and roughness 0.45 (0.40 at the
      moist lower tip);
    - follicles: grey pits (Detail B darkens to (0.13, 0.12, 0.12) and dents
      the normal);
    - skin under white fur is greyer (0.36, 0.32, 0.31), so the lip and
      philtrum grooves do not read as white lines."""
    m, nt = v6.new_mat("M_CatBaseV6_Skin")
    out = N(nt, "ShaderNodeOutputMaterial", (2000, 0))
    bs = N(nt, "ShaderNodeBsdfPrincipled", (1500, 0))
    coat = v6.image_node(nt, images["coat"], (-1100, 400))
    reg = v6.image_node(nt, images["regions"], (-1100, -100))
    det = v6.image_node(nt, images["detail"], (-1100, -600))
    sc = N(nt, "ShaderNodeSeparateColor", (-800, 400))
    sr = N(nt, "ShaderNodeSeparateColor", (-800, -100))
    sd = N(nt, "ShaderNodeSeparateColor", (-800, -600))
    L(nt, coat.outputs["Color"], sc.inputs["Color"])
    L(nt, reg.outputs["Color"], sr.inputs["Color"])
    L(nt, det.outputs["Color"], sd.inputs["Color"])

    def math_(op, a, b=None, loc=(0, 0), clamp=False):
        n_ = N(nt, "ShaderNodeMath", loc)
        n_.operation = op
        n_.use_clamp = clamp
        for i, val in enumerate((a, b)):
            if val is None:
                continue
            if isinstance(val, (int, float)):
                n_.inputs[i].default_value = float(val)
            else:
                L(nt, val, n_.inputs[i])
        return n_.outputs[0]

    def mr(val, a, b, c, d, loc):
        n_ = N(nt, "ShaderNodeMapRange", loc)
        L(nt, val, n_.inputs["Value"])
        n_.inputs["From Min"].default_value = a
        n_.inputs["From Max"].default_value = b
        n_.inputs["To Min"].default_value = c
        n_.inputs["To Max"].default_value = d
        return n_.outputs["Result"]

    c = v6.mix_rgb(nt, sc.outputs["Green"], (0.15, 0.135, 0.12), (0.040, 0.036, 0.034), (-400, 600))
    c = v6.mix_rgb(nt, sc.outputs["Red"], c, (0.36, 0.32, 0.31), (-200, 600))
    inner = mr(sr.outputs["Blue"], 0.7, 0.95, 0.0, 1.0, (-500, 200))
    vr = math_("MULTIPLY", sd.outputs["Red"], EAR_VEIN_BASE, (-400, 250))
    earc = v6.mix_rgb(nt, vr, EAR_SKIN_V9, (0.21, 0.10, 0.095), (-200, 250))
    c = v6.mix_rgb(nt, inner, c, earc, (0, 600))
    tc = N(nt, "ShaderNodeTexCoord", (-900, 1100))
    vor = N(nt, "ShaderNodeTexVoronoi", (-600, 1150))
    vor.feature = "DISTANCE_TO_EDGE"
    vor.inputs["Scale"].default_value = 3000.0
    vor.inputs["Randomness"].default_value = 0.85
    L(nt, tc.outputs["Object"], vor.inputs["Vector"])
    vor2 = N(nt, "ShaderNodeTexVoronoi", (-600, 950))
    vor2.feature = "DISTANCE_TO_EDGE"
    vor2.inputs["Scale"].default_value = 1150.0
    vor2.inputs["Randomness"].default_value = 0.8
    L(nt, tc.outputs["Object"], vor2.inputs["Vector"])
    # rounded cobbles: sqrt of the edge distance
    crev = math_("SQRT", mr(vor.outputs["Distance"], 0.0, 0.30, 0.0, 1.0, (-400, 1150)), None, (-250, 1150))
    crev2 = math_("SQRT", mr(vor2.outputs["Distance"], 0.0, 0.25, 0.0, 1.0, (-400, 950)), None, (-250, 950))
    hgt = math_("ADD", math_("MULTIPLY", crev, 0.70, (-100, 1150)), math_("MULTIPLY", crev2, 0.30, (-100, 950)), (50, 1050))
    ao = mr(hgt, 0.0, 1.0, 0.72, 1.0, (150, 1050))
    lcol = v6.mix_rgb(nt, sd.outputs["Green"], (0.34, 0.15, 0.14), (0.17, 0.07, 0.062), (150, 850))
    leather = N(nt, "ShaderNodeMix", (400, 950))
    leather.data_type = "RGBA"
    leather.blend_type = "MULTIPLY"
    leather.inputs["Factor"].default_value = 1.0
    L(nt, lcol, leather.inputs[6])
    L(nt, ao, leather.inputs[7])
    c = v6.mix_rgb(nt, sr.outputs["Red"], c, leather.outputs[2], (600, 600))
    c = v6.mix_rgb(nt, sd.outputs["Blue"], c, (0.13, 0.12, 0.12), (800, 600))
    c = v6.mix_rgb(nt, sr.outputs["Green"], c, (0.013, 0.011, 0.011), (1000, 600))
    L(nt, c, bs.inputs["Base Color"])
    sep = N(nt, "ShaderNodeSeparateXYZ", (-600, 750))
    L(nt, tc.outputs["Object"], sep.inputs["Vector"])
    wet = mr(sep.outputs["Z"], -0.050, -0.036, LEATHER_ROUGH - 0.05, LEATHER_ROUGH, (-350, 750))
    r1 = N(nt, "ShaderNodeMix", (900, 150))
    r1.data_type = "FLOAT"
    L(nt, sr.outputs["Red"], r1.inputs["Factor"])
    r1.inputs[2].default_value = 0.55
    L(nt, wet, r1.inputs[3])
    r2 = N(nt, "ShaderNodeMix", (1100, 150))
    r2.data_type = "FLOAT"
    L(nt, sr.outputs["Green"], r2.inputs["Factor"])
    L(nt, r1.outputs[0], r2.inputs[2])
    r2.inputs[3].default_value = 0.62
    r3 = N(nt, "ShaderNodeMix", (1300, 150))
    r3.data_type = "FLOAT"
    L(nt, inner, r3.inputs["Factor"])
    L(nt, r2.outputs[0], r3.inputs[2])
    r3.inputs[3].default_value = 0.46
    ear_rim = math_("MULTIPLY", sd.outputs["Green"], mr(sr.outputs["Blue"], 0.30, 0.45, 0.0, 1.0, (1200, 350)), (1350, 350))
    r4 = N(nt, "ShaderNodeMix", (1450, 150))
    r4.data_type = "FLOAT"
    L(nt, ear_rim, r4.inputs["Factor"])
    L(nt, r3.outputs[0], r4.inputs[2])
    r4.inputs[3].default_value = 0.85
    L(nt, r4.outputs[0], bs.inputs["Roughness"])
    L(nt, mr(ear_rim, 0.0, 1.0, 0.45, 0.15, (1450, 300)), bs.inputs["Specular IOR Level"])
    bump = N(nt, "ShaderNodeBump", (1200, -300))
    bump.inputs["Strength"].default_value = 1.0
    bump.inputs["Distance"].default_value = 0.00030
    hb_ = math_("MULTIPLY", hgt, sr.outputs["Red"], (900, -300))
    pit = math_("MULTIPLY", sd.outputs["Blue"], 1.2, (900, -420))
    L(nt, math_("SUBTRACT", hb_, pit, (1050, -350)), bump.inputs["Height"])
    L(nt, bump.outputs["Normal"], bs.inputs["Normal"])
    sss_ear = math_("MULTIPLY", math_("POWER", sr.outputs["Blue"], 2.0, (650, -600)), 0.22, (800, -600))
    sss_n = math_("MULTIPLY", sr.outputs["Red"], 0.12, (800, -750))
    sss = math_("ADD", sss_ear, sss_n, (1000, -650))
    inv = math_("SUBTRACT", 1.0, sr.outputs["Green"], (1000, -850))
    L(nt, math_("MULTIPLY", sss, inv, (1200, -700), clamp=True), bs.inputs["Subsurface Weight"])
    bs.inputs["Subsurface Radius"].default_value = EAR_SSS_RADIUS
    bs.inputs["Subsurface Scale"].default_value = 0.0010
    # translucent lobe on the pinna (Regions B 1.0 inner, 0.5 back)
    trc = v6.mix_rgb(nt, math_("MULTIPLY", sd.outputs["Red"], 0.35, (1100, -1000)), (0.55, 0.28, 0.25), (0.40, 0.10, 0.09), (1250, -1000))
    tr = N(nt, "ShaderNodeBsdfTranslucent", (1500, -900))
    L(nt, trc, tr.inputs["Color"])
    wtr = math_("MULTIPLY", mr(sr.outputs["Blue"], 0.45, 1.0, 0.03, EAR_TRANSLUCENT, (1100, -1150)),
                mr(sr.outputs["Blue"], 0.40, 0.50, 0.0, 1.0, (1100, -1300)), (1300, -1200))
    mx = N(nt, "ShaderNodeMixShader", (1750, 0))
    L(nt, wtr, mx.inputs["Fac"])
    L(nt, bs.outputs["BSDF"], mx.inputs[1])
    L(nt, tr.outputs["BSDF"], mx.inputs[2])
    L(nt, mx.outputs["Shader"], out.inputs["Surface"])
    return m


def bake_textures_v9(cage, res):
    """v8.bake_textures_v8 (the same four maps) evaluated with the round-7
    fields."""
    return v8.bake_textures_v8(cage, res)


# ---------------------------------------------------------------------------
# Eyes (round 7)
# ---------------------------------------------------------------------------

def iris_colour_v9(f, rho):
    """Round 7 iris (judged round 6: a human-like high-contrast pale radial
    starburst with posterised crypt blobs): half the fibre contrast, soft
    crypts that only deepen the colour a little, a low-frequency (5- and
    3-lobe) variation in value and hue, and a slightly lighter aqua-grey
    pupillary zone."""
    base = np.array([0.108, 0.150, 0.198])
    light = np.array([0.24, 0.29, 0.33])
    fv = smoothstep(0.35, 0.85, f["fib"])[..., None]
    col = base * (1 - 0.31 * fv) + light * (0.31 * fv)
    col = col * (0.86 + 0.28 * f["mot"])[..., None]
    th = f["th"]
    lf = 0.5 + 0.5 * np.sin(5.0 * th + 1.1) * np.cos(3.0 * th + 0.4)
    lf2 = pnoise_ring(th, rho)
    col = col * (0.90 + 0.20 * lf2)[..., None]
    col = col * (1 - 0.18 * lf[..., None]) + col * np.array([1.04, 1.07, 0.93]) * (0.18 * lf[..., None])
    pz = (1.0 - smoothstep(f["rc"] - 0.06, f["rc"] + 0.02, rho))[..., None]
    col = col * (1 - 0.5 * pz) + (col * np.array([1.06, 1.10, 1.00]) + np.array([0.028, 0.036, 0.030])) * (0.5 * pz)
    col = col * (1 - 0.22 * f["coll"][..., None]) + np.array([0.30, 0.35, 0.38]) * (0.22 * f["coll"][..., None])
    cr = np.clip(0.40 * f["crypt"] + 0.22 * f["cr2"], 0, 1)[..., None]
    col = col * (1 - 0.55 * cr)
    col = col * (1.0 - 0.22 * f["furrow"])[..., None]
    col = col * (1.0 - 0.24 * smoothstep(0.58, 0.86, rho))[..., None]
    lb = (0.88 * f["limb"])[..., None]
    col = col * (1 - lb) + np.array([0.012, 0.018, 0.028]) * lb
    return col


def pnoise_ring(th, rho):
    U = np.mod(th / (2.0 * math.pi), 1.0)
    return v8.pnoise(U * 4.0, rho * 1.6, 4, v8.IRIS_SEED + 30)


_V8_IRIS_FIELDS = v8.iris_fields


def iris_fields_v9(rho, th):
    f = _V8_IRIS_FIELDS(rho, th)
    # softer crypts (wider, shallower ramps)
    s = v8.IRIS_SEED
    U = np.mod(th / (2.0 * math.pi), 1.0)
    warp = (v8.pnoise(U * 10, rho * 2.5, 10, s + 1) - 0.5) * 0.030
    Uw = np.mod(U + warp, 1.0)
    cr = v8.pnoise(Uw * 55, rho * 7.5, 55, s + 9)
    zone = smoothstep(f["rc"] + 0.01, f["rc"] + 0.07, rho) * (1.0 - smoothstep(0.68, 0.82, rho))
    f["crypt"] = smoothstep(0.62, 0.92, cr) * zone
    f["cr2"] = f["cr2"] * 0.6
    f["th"] = th
    return f


def iris_height_mm_v9(f, rho):
    return (-1.0 * (1.0 - rho ** 2) + 0.14 * f["coll"] + 0.07 * (f["fib"] - 0.5) - 0.20 * f["crypt"] - 0.08 * f["cr2"]
            - 0.05 * f["furrow"] + 0.04 * (f["mot"] - 0.5))


CORNEA_FLOOR = 0.045  # constant tear-film reflectance added to 0.85x Fresnel


def cornea_material_v9():
    """Round 6 cornea with a reflection floor: mirror weight 0.045 + 0.85 x
    Fresnel (round 6: 0.8 x Fresnel, ~2 % at the centre), so the sky and
    ground read over the whole dome, not only near its rim and in a band
    across the pupil. Recorded in the README as an artistic tear-film term."""
    m, nt = v6.new_mat("M_CatBaseV6_CorneaV9")
    out = N(nt, "ShaderNodeOutputMaterial", (900, 0))
    gl = N(nt, "ShaderNodeBsdfGlass", (100, 150))
    gl.inputs["IOR"].default_value = 1.376
    gl.inputs["Roughness"].default_value = 0.0
    gy = N(nt, "ShaderNodeBsdfGlossy", (100, -50))
    gy.inputs["Roughness"].default_value = 0.0
    fr = N(nt, "ShaderNodeFresnel", (-300, -100))
    fr.inputs["IOR"].default_value = 1.376
    sc = N(nt, "ShaderNodeMath", (-150, -150))
    sc.operation = "MULTIPLY_ADD"
    L(nt, fr.outputs["Fac"], sc.inputs[0])
    sc.inputs[1].default_value = 0.85
    sc.inputs[2].default_value = CORNEA_FLOOR
    mixg = N(nt, "ShaderNodeMixShader", (300, -50))
    L(nt, sc.outputs[0], mixg.inputs["Fac"])
    tr0 = N(nt, "ShaderNodeBsdfTransparent", (100, -250))
    tr0.inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)
    L(nt, tr0.outputs["BSDF"], mixg.inputs[1])
    L(nt, gy.outputs["BSDF"], mixg.inputs[2])
    add = N(nt, "ShaderNodeAddShader", (500, 50))
    L(nt, gl.outputs["BSDF"], add.inputs[0])
    L(nt, mixg.outputs["Shader"], add.inputs[1])
    tr = N(nt, "ShaderNodeBsdfTransparent", (500, -200))
    lp = N(nt, "ShaderNodeLightPath", (300, 300))
    mx = N(nt, "ShaderNodeMixShader", (700, 0))
    L(nt, lp.outputs["Is Shadow Ray"], mx.inputs["Fac"])
    L(nt, add.outputs["Shader"], mx.inputs[1])
    L(nt, tr.outputs["BSDF"], mx.inputs[2])
    L(nt, mx.outputs["Shader"], out.inputs["Surface"])
    return m


def build_lid_margins_v9(coll, parent, n=360):
    """Round 7 lid margins (judged round 6: a thick black outline of constant
    width, like eyeliner, with a doubled line above the upper lid). The lid
    skin now reaches the fissure everywhere (the lid fill band), so the strip
    only has to be the margin itself: its inner edge lies on the eye, it
    rises to the lid skin within 0.15 mm and tucks under it by ~0.5 mm
    (upper lid 0.55x, lower lid 0.45-0.65x toward the medial canthus, 0.25x
    at the canthi), i.e. <= 0.6 mm visible. Round 6's strip ran out to
    1.2 mm and its skin pigment band to 3.5 mm."""
    mat = v8.lid_margin_material_v8()
    tear = bpy.data.materials.get("M_CatBaseV6_Tear")
    objs = []
    A_S = np.array([0.0, 0.15, 0.35, 0.6, 0.9]) * MM
    uu, low = v8.outline_params(n)
    t = uu / 0.999
    for s, tag in ((1.0, "L"), (-1.0, "R")):
        P, Nn = v7.eye_surface_outline(s, n)
        m = len(P)
        cen = P.mean(0)
        T = np.roll(P, -1, 0) - np.roll(P, 1, 0)
        T /= np.linalg.norm(T, axis=1, keepdims=True)
        O = np.cross(T, Nn)
        flip = np.sum(O * (P - cen), 1) < 0
        O[flip] *= -1.0
        for _ in range(14):
            O = (np.roll(O, 1, 0) + 2.0 * O + np.roll(O, -1, 0)) / 4.0
        O -= np.sum(O * Nn, 1, keepdims=True) * Nn
        O /= np.linalg.norm(O, axis=1, keepdims=True)
        wf = np.where(low, 0.45 + 0.20 * smoothstep(0.1, -0.75, t), 0.55)
        wf = wf * (0.45 + 0.55 * np.sqrt(np.clip(1.0 - t ** 4, 0.0, 1.0)))
        k = 5
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
        kk = 6
        padH = np.r_[H[-kk:], H, H[:kk]]
        H = np.stack([np.convolve(padH[:, j], np.ones(2 * kk + 1) / (2 * kk + 1), mode="same")[kk:-kk] for j in range(len(A_S))], 1)
        H = np.clip(H, 0.25 * MM, 2.0 * MM)
        h0 = H[:, 1]
        prof = [
            (0.00, np.full(m, -0.12 * MM)),
            (0.00, 0.40 * h0),
            (0.05, 0.80 * h0),
            (0.15, np.minimum(h0, H[:, 1]) - 0.03 * MM),
            (0.35, H[:, 2] - 0.18 * MM),
            (0.60, H[:, 3] - 0.45 * MM),
            (0.90, H[:, 4] - 0.80 * MM),
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
        ta.data.foreach_set("value", np.tile(np.linspace(0.0, 1.0, nprof), m).astype(np.float32))
        for p_ in me.polygons:
            p_.use_smooth = True
        me.materials.append(mat)
        ob = v6.link(bpy.data.objects.new(me.name, me), coll)
        ob.parent = parent
        ob.matrix_world = Matrix.Translation(v6.HEAD_ORIGIN) if parent is not None and parent.type != "EMPTY" else Matrix.Identity(4)
        objs.append(ob)
        sel = np.nonzero(low & (np.abs(t) < 0.86))[0]
        sel = sel[np.argsort(t[sel])]
        pts = P[sel] + Nn[sel] * 0.05 * MM + O[sel] * 0.06 * MM * wf[sel][:, None]
        tube = v6.tube_mesh(f"CatBaseV6_Eye{tag}_TearMeniscus", pts, 0.12 * MM, closed=False, segs=8)
        tob = v6.link(bpy.data.objects.new(tube.name, tube), coll)
        if tear is not None:
            tube.materials.append(tear)
        tob.parent = parent
        tob.matrix_world = Matrix.Translation(v6.HEAD_ORIGIN) if parent is not None and parent.type != "EMPTY" else Matrix.Identity(4)
        objs.append(tob)
    return objs


def build_caruncles_v9(coll, parent, mat):
    """The moist pink membrane (caruncle and the edge of the third eyelid)
    at the MEDIAL canthus (judged round 6: pink tissue showed at the lateral
    corners, which was the exposed sclera): a flattened lens lying on the eye
    surface in the medial corner, 3.2 x 2.2 mm, its outer part tucked under
    the lid skin."""
    objs = []
    for s, tag in ((1.0, "L"), (-1.0, "R")):
        P, Nn = v7.eye_surface_outline(s, 320)
        i = int(np.argmin(P[:, 1] * s))
        cen = P.mean(0)
        toward = cen - P[i]
        toward -= (toward @ Nn[i]) * Nn[i]
        toward /= np.linalg.norm(toward)
        c = P[i] + toward * 1.7 * MM + Nn[i] * 0.05 * MM
        bpy.ops.mesh.primitive_uv_sphere_add(segments=40, ring_count=20, radius=1.0)
        cr = bpy.context.object
        cr.name = f"CatBaseV6_Eye{tag}_Caruncle"
        zN = Vector(Nn[i]).normalized()
        xT = Vector(toward).normalized()
        yB = zN.cross(xT)
        M = Matrix((xT, yB, zN)).transposed().to_4x4()
        M.translation = Vector(c) + (v6.HEAD_ORIGIN if parent is not None and parent.type != "EMPTY" else Vector())
        cr.matrix_world = M @ Matrix.Diagonal((3.2 * MM, 2.2 * MM, 0.55 * MM, 1.0))
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


def eye_overrides_v9(objs, mats):
    """Sclera: darker, pigmented conjunctiva toward the canthi (the exposed
    lateral corner read as pink tissue in round 6); caruncle: moist pink."""
    sc_m = mats.get("sclera")
    if sc_m is not None:
        for nd in sc_m.node_tree.nodes:
            if nd.type == "MIX" and getattr(nd, "data_type", "") == "RGBA":
                nd.inputs[6].default_value = (0.20, 0.17, 0.155, 1.0)
                nd.inputs[7].default_value = (0.045, 0.036, 0.032, 1.0)
            if nd.type == "BSDF_PRINCIPLED":
                nd.inputs["Roughness"].default_value = 0.12
                nd.inputs["Coat Weight"].default_value = 0.4
                nd.inputs["Coat Roughness"].default_value = 0.03
    cm = mats.get("caruncle")
    if cm is not None:
        bs = next(n for n in cm.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        bs.inputs["Base Color"].default_value = (0.36, 0.165, 0.155, 1.0)
        bs.inputs["Roughness"].default_value = 0.10
        bs.inputs["Coat Weight"].default_value = 0.6
        bs.inputs["Coat Roughness"].default_value = 0.03
        bs.inputs["Subsurface Weight"].default_value = 0.2
        bs.inputs["Subsurface Radius"].default_value = (0.8, 0.25, 0.25)


def install_build_overrides_v9():
    global _V6_BUILD_SKIN
    if getattr(v6, "_ROUND7_BUILD", False):
        return
    v8.install_build_overrides_v8()
    v6._ROUND7_BUILD = True
    _V6_BUILD_SKIN = v6.build_skin
    v6.build_skin = build_skin_v9
    v7.build_caruncles_v7 = build_caruncles_v9
    build_eyes_v8 = v6.build_eyes

    def build_eyes_v9(coll, mats, parent):
        objs = build_eyes_v8(coll, mats, parent)
        cmat = cornea_material_v9()
        for o in objs:
            if o.name.endswith("_Cornea"):
                o.data.materials.clear()
                o.data.materials.append(cmat)
        eye_overrides_v9(objs, mats)
        return objs

    v6.build_eyes = build_eyes_v9
    v6.build_lid_margins = build_lid_margins_v9
    v6.bake_textures = bake_textures_v9
    v6.skin_material = skin_material_v9
    v6.build_groom = build_groom_v9
    v6.build_vibrissae = build_vibrissae_v9
    v6.build_inner_ear_furnishings = build_inner_ear_furnishings_v9


def stage_compare_v9(args):
    """Round-6 comparison sheets (v8.stage_compare_v8: the private A/B with
    the CC BY 2.0 photograph, previous | this round at the reference framing
    and the five Overcast cameras, the Nyaakoto reference beside CloseFront
    and Profile), plus a committed sheet of this round's reference-matched
    frame beside the previous round's and the Nyaakoto profile head."""
    v8.stage_compare_v8(args)
    rn = args.round
    cur = OUT / "Renders" / f"round_{rn}"
    prv = OUT / "Renders" / f"round_{rn - 1}"
    tag, ptag = f"R{rn}", f"R{rn - 1}"
    a = prv / f"CatBaseV6_{ptag}_ThreePoint_Front.png"
    b = cur / f"CatBaseV6_{tag}_ThreePoint_Front.png"
    if a.exists() and b.exists():
        v7._img_save(v7._side_by_side([v7._img_load(a)[100:900, 480:1440], v7._img_load(b)[100:900, 480:1440]], 800),
                     cur / f"CatBaseV6_{tag}_AB_{ptag}_ThreePoint_Front.png")
    rows = []
    for view in ("CloseFront", "CloseThreeQuarter"):
        a, b = prv / f"CatBaseV6_{ptag}_Overcast_{view}.png", cur / f"CatBaseV6_{tag}_Overcast_{view}.png"
        if a.exists() and b.exists():
            rows.append(v7._side_by_side([v7._img_load(a), v7._img_load(b)], 720))
    if rows:
        W = max(r.shape[1] for r in rows)
        sheet = np.full((sum(r.shape[0] for r in rows) + 8 * (len(rows) - 1), W, 3), 0.02, np.float32)
        yy = 0
        for r in rows:
            sheet[yy:yy + r.shape[0], :r.shape[1]] = r
            yy += r.shape[0] + 8
        v7._img_save(sheet, cur / f"CatBaseV6_{tag}_AB_{ptag}_Close.png")
    log("round-7 comparison sheets written to", cur)


def stage_manifest_v9(args):
    v8.stage_manifest_v8(args)
    man = json.loads((OUT / "manifest.json").read_text())
    man["generator"] = ("scripts/art/create_cat_base_v9.py (round 7; imports create_cat_base_v8.py, which imports "
                        "create_cat_base_v7.py, which imports create_cat_base_v6.py)")
    man["round7"] = {
        "muzzle_warp_mm": {"forward": MUZZLE_DX, "forward_ramp_head_x": MUZZLE_X, "lower_muzzle_lift": LIP_DZ, "lift_ramp_head_z": LIP_Z},
        "neck": {"side_inset_mm": NECK_SIDE_INSET, "nape_dip_mm": NAPE_DIP},
        "canal_plugs": [{"pit_head_mm": CANAL_PIT.tolist(), "radius_mm": CANAL_PLUG_R}, {"pit_head_mm": CANAL_PIT2.tolist(), "radius_mm": CANAL_PIT2_R}],
        "ear_mask_closing_scan_units": {"radius": SCAN_CLOSE, "smooth_box_width_voxels": SCAN_EAR_SMOOTH, "cache": "Local/CatBaseV6Cache/scan_field_closed_v2.npz"},
        "ear_cavity_t_range": [EAR_CAVITY_T_MIN, EAR_CAVITY_T_MAX],
        "ear": {"open_out_deg": EAR_OPEN_OUT_V9, "lean_out_deg": EAR_LEAN_OUT_V9, "cavity": "voxelised from the seated pinna (Local/CatBaseV6Cache/ear_cavity.npz)",
                "sss_radius_mm": list(EAR_SSS_RADIUS), "translucent_inner": EAR_TRANSLUCENT, "vein_reflected": EAR_VEIN_BASE},
        "fissure_mm": {"upper": FISSURE_UP_V9, "lower": FISSURE_LO_V9},
        "cornea_reflection": {"floor": CORNEA_FLOOR, "fresnel_scale": 0.85},
        "nose": {"edge_mm": LEATHER_EDGE_H, "dome_mm": LEATHER_DOME, "bevel_mm": LEATHER_BEVEL, "alar_mm": ALAR_H, "roughness": LEATHER_ROUGH},
        "mouth": {"inverted_y_z_head_mm": PHILTRUM_BOTTOM_Z, "pads_mm": PAD_H_V9, "chin_mm": CHIN_V9["h"]},
        "guard_layers": [g[0] for g in GUARD_LAYERS],
    }
    (OUT / "manifest.json").write_text(json.dumps(man, indent=2, ensure_ascii=False) + "\n")
    log("manifest (round 7 fields added)")


# ---------------------------------------------------------------------------
# Overrides
# ---------------------------------------------------------------------------

def apply_round7_overrides():
    if getattr(v6, "_ROUND7", False):
        return
    v8.apply_round6_overrides()
    v6._ROUND7 = True
    # muzzle 9 mm forward: every muzzle-keyed layout constant follows
    A.mz = A.mz + MUZZLE_DX
    v6.NOSE_X0 = 128.0 + A.mz
    # skin: warped scan, narrower neck, nape, new bust, new details
    v7.scan_head_neck = scan_head_neck_v9
    v7.scan_field = scan_field_v9
    v7.fur_inset_mm = fur_inset_mm_v9
    v7.build_bust_ops = build_bust_ops_v9
    v7.build_bust_field = build_bust_field_v9
    v6.build_detail_ops = build_detail_ops_v9
    v6.DETAIL_OPS = None
    v6.PHILTRUM = [(0.0, v6.PHILTRUM[0][1]), (0.0, v6.PHILTRUM[1][1]), (0.0, PHILTRUM_BOTTOM_Z)]
    # eyes: lower upper lid, higher lower lid, a capped fissure prism
    v6.sd_fissure = sd_fissure_v9
    A.fissure_up = FISSURE_UP_V9 * MM
    A.fissure_lo = FISSURE_LO_V9 * MM
    # ears: opening 30 deg forward, a little less lean
    A.ear_open_out = EAR_OPEN_OUT_V9
    A.ear_lean_out = EAR_LEAN_OUT_V9
    v6.ear_arrays = ear_arrays_v9
    v8.cup_weight_v8 = cup_weight_v9
    v7.cup_weight = cup_weight_v9
    v6._MARK_CACHE.clear()
    # coat, flow, follicles, iris
    v6.coat_fields = coat_fields_v9
    v8.coat_fields_v8 = coat_fields_v9
    v6.fur_direction = fur_direction_v9
    v6.grow_guides = grow_guides_v9
    v8.mystacial_roots_v8 = mystacial_roots_v9
    v6.mystacial_roots = mystacial_roots_v9
    v8.iris_fields = iris_fields_v9
    v8.iris_colour = iris_colour_v9
    v8.iris_height_mm = iris_height_mm_v9


def preview_v9(args):
    """Workbench review renders of the bare round-7 skin level set, pinnae,
    globes and corneas (no fur): head, profile, mouth, bust, ears, eyes."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    d = np.load(CACHE / "skin_dense.npz")
    me = v6.mesh_from_arrays("dense", d["pts"], d["quads"])
    me.shade_smooth()
    v6.link(bpy.data.objects.new("dense", me))
    cd = v6.cornea_dims()
    for s in (1.0, -1.0):
        c = Vector(v6.eye_center(s) @ v6.head_R().T)
        g = Vector(v6.head_R() @ v6.gaze_frame(s)[:, 0])
        bpy.ops.mesh.primitive_uv_sphere_add(radius=A.eye_r, location=c, segments=96, ring_count=48)
        bpy.ops.object.shade_smooth()
        bpy.ops.mesh.primitive_uv_sphere_add(radius=cd["Rc"], location=c + g * (cd["apex"] - cd["Rc"]), segments=96, ring_count=48)
        bpy.ops.object.shade_smooth()
        v6.link(bpy.data.objects.new(f"ear{s}", v6.ear_mesh(s)))
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.show_cavity = True
    sc.render.resolution_x = 1000
    sc.render.resolution_y = 1000
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.lens = 85
    ear = Vector(A.ear_base @ v6.head_R().T)
    eye = Vector(v6.lid_center(-1.0) @ v6.head_R().T)
    mouth = Vector(np.array([140.0 + MUZZLE_DX, 0.0, -30.0]) * MM @ v6.head_R().T)
    views = (("front", Vector((0.06, 0, 0.0)), Vector((1, 0, 0.03)), 0.9), ("profile", Vector((0.03, 0, -0.03)), Vector((0.0, -1, 0.02)), 1.1),
             ("tq", Vector((0.05, 0, 0.0)), Vector((0.72, -0.69, 0.06)), 0.9), ("bust_front", Vector((0.0, 0, -0.16)), Vector((1, 0, 0.02)), 2.2),
             ("bust_profile", Vector((0.0, 0, -0.16)), Vector((0, -1, 0.02)), 2.2), ("bust_tq", Vector((0.0, 0, -0.16)), Vector((0.72, -0.69, 0.05)), 2.2),
             ("ear_front", ear * Vector((1, -1, 1)) + Vector((0, 0, 0.02)), Vector((1, -0.25, 0.25)), 0.45),
             ("ear_tq", ear * Vector((1, -1, 1)) + Vector((0, 0, 0.02)), Vector((0.6, -0.8, 0.2)), 0.45),
             ("ear_profile", ear * Vector((1, -1, 1)) + Vector((0, 0, 0.02)), Vector((0.0, -1.0, 0.05)), 0.45),
             ("eye_front", eye, Vector((1.0, -0.1, 0.05)), 0.30), ("eye_tq", eye, Vector((0.72, -0.69, 0.05)), 0.30),
             ("mouth", mouth, Vector((1, 0, -0.1)), 0.35), ("mouth_profile", mouth, Vector((0.0, -1.0, 0.0)), 0.45))
    for name, t, d_, dist in views:
        cam.location = t + d_.normalized() * dist
        cam.rotation_euler = (t - cam.location).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = str(Path(args.preview_dir) / f"skin_{name}.png")
        bpy.ops.render.render(write_still=True)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", type=int, default=ROUND)
    ap.add_argument("--stages", default="skin,skinpreview")
    ap.add_argument("--voxel", type=float, default=0.75)
    ap.add_argument("--samples", type=int, default=256)
    ap.add_argument("--preview-dir", default=str(CACHE / "preview_r7"))
    ap.add_argument("--tex", type=int, default=4096)
    ap.add_argument("--guides", type=int, default=70000)
    ap.add_argument("--lights", default="Overcast")
    ap.add_argument("--views", default="")
    ap.add_argument("--render-dir", default="")
    ap.add_argument("--percent", type=int, default=100)
    ap.add_argument("--rescan", action="store_true")
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
    apply_round7_overrides()
    stages = args.stages.split(",")
    if "scan" in stages:
        v7.stage_scan(args)
    if "skin" in stages:
        EAR_CAVITY_REBUILD[0] = True
        _EAR_CAVITY.clear()
        v7.stage_skin_v7(args)
    if "skinpreview" in stages:
        preview_v9(args)
    if "build" in stages:
        install_build_overrides_v9()
        v6.stage_build(args)
    if "render" in stages:
        v6.stage_render(args)
    if "measure" in stages:
        v7.stage_measure_v7(args)
    if "compare" in stages:
        stage_compare_v9(args)
    if "manifest" in stages:
        stage_manifest_v9(args)


if __name__ == "__main__":
    main()
