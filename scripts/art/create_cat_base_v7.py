"""CatBaseV6 round 5: scan-derived head, ears and neck (generator v7).

Rounds 1-4 (scripts/art/create_cat_base_v6.py) sculpted the soft tissue
procedurally over a real CT skull. Four judged rounds did not converge on the
head shape (flat ears with a bat-like set, a tombstone occiput over a pillar
neck, lids floating off the globe, proportion drift), so round 5 changes the
method: the head and neck SHAPE come from real photogrammetry of a real cat,
and the CT skull is kept only for landmarks.

Ground truth: "Cat sitting upright" by elaughli (Sketchfab, CC BY 4.0, raw
scan kept private in Local/ThirdPartyRaw; see sources_manifest.json). It is
the only awake, upright scan of the two cat scans on file (the Neo_minigan
"Cat (Take 2)" scan is a sleeping, curled cat with its head fused to the
cushion). Its left half (the cat's left) is clean; its right half, the ear
tips and the top of the head carry photogrammetry noise, and its ears are
laid back.

What is taken from the scan and what is changed (also recorded in
sources_manifest.json and the README round log):

1. frame: the midsagittal plane of the face is recovered by mirror-ICP from
   three landmark picks (nose tip, both eyes) and the head is expressed in
   that frame (the head was turned ~85 deg on the body);
2. symmetry: only the clean left half is kept and mirrored (removes the
   noisy right half and the pose asymmetry);
3. noise: the scan surface becomes a 0.5 mm (scan units) signed distance
   field whose sign is flood-filled through voxels > 4 mm from the scan (so
   the open ear canals and junk tunnels are sealed) and regrown downhill to
   the surface; it is re-levelled, blurred along y at the mirror seam and
   smoothed (sigma ~0.7 mm on the face, ~1.6-3 mm on cranium and neck);
4. ears: the scan's laid-back, noisy pinnae are removed by a morphological
   opening (erode/dilate 9 mm) inside two masks, and new pinnae are modelled
   (ear_arrays_v7) on the scan's ear bases in an alert pose, with the scalp
   carved out of each conchal cup;
5. fur: the scan records the fur surface, so the skin is inset by the
   thickness of the groom grown back on it (0.8-15 character mm by region);
6. scale/pose: a similarity (uniform scale 1.874, 5.1 deg pitch, offset)
   fitted by 2D ICP of the scan's midsagittal face profile onto the round-4
   skin profile; the CT skull is kept for landmarks (eye globes at its
   orbits) and a tissue-depth check (`measure`);
7. below the neck the scan is faded into the round-4 biped bust (shoulders,
   arms, chest), because the scanned cat sits as a quadruped.

Round 5 also replaces the floating lid-margin tube with a strip whose inner
edge lies on the eye, carves the globe 0.25 mm inside the eye, relaxes the
fissure, adds a moist caruncle, and refits the groom (inner-ear hair,
furnishings, short coat round the ear bases, wider white muzzle and facial
stripes).

No scan triangle or texture is stored in the .blend or the repository: the
committed skin is a new QuadriFlow quad cage shrink-wrapped onto the derived
level set.

Run from the repository root (Blender 5.2.2 LTS, background):

  blender -b --factory-startup --python scripts/art/create_cat_base_v7.py -- \\
      --stages scan,skin,build,measure,render,compare,manifest --round 5 \\
      --samples 256 --views Front,Profile,ThreeQuarter,CloseFront,CloseThreeQuarter \\
      --lights Overcast,Studio,ThreePoint,Exterior,RefMatch

The v6 generator is imported as a module and its stages are reused; this
file only overrides what round 5 changes.
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
from mathutils.kdtree import KDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import create_cat_base_v6 as v6  # noqa: E402

A = v6.A
MM = v6.MM
ROOT = v6.ROOT
OUT = v6.OUT
CACHE = v6.CACHE
log = v6.log
smoothstep = v6.smoothstep

SCAN_UID = "3ffbfcabc4c34b58b03d43fd4f445b54"
SCAN_PATH = ROOT / f"Local/ThirdPartyRaw/scans/objaverse/{SCAN_UID}.glb"
# Landmark picks on the raw scan (scan metres), read off gridded orthographic
# renders: nose-leather tip and the centres of the two closed-eye bulges.
SCAN_PICKS = dict(nose=(-0.06018, -0.03240, 0.07617), eye_r=(-0.08185, -0.00731, 0.09544), eye_l=(-0.04217, -0.00249, 0.09358))
SCAN_VS = 0.5  # mm (real) voxel of the scan distance field
# crop box in the scan head frame H0 (real mm: x forward, y = cat's left, z up)
SCAN_BOX = (np.array([-150.0, -92.0, -175.0]), np.array([62.0, 92.0, 72.0]))


def _scan_sha():
    try:
        src = json.loads((OUT / "sources_manifest.json").read_text())
        return next(s["sha256"] for s in src["scans"] if SCAN_UID in s["asset_id"])
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Scan loading, head frame, symmetrisation
# ---------------------------------------------------------------------------

def load_scan_raw():
    """(V, F) of the private scan in scan metres (all mesh objects, world space)."""
    if not SCAN_PATH.exists():
        raise SystemExit(f"missing private scan {SCAN_PATH}; run scripts/art/fetch_cat_base_v6_sources.py scans")
    sha = _scan_sha()
    if sha:
        got = v6.sha256_file(SCAN_PATH)
        if got != sha:
            raise SystemExit(f"scan hash mismatch {got} != {sha}")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(SCAN_PATH))
    Vs, Fs, off = [], [], 0
    for o in list(bpy.context.scene.objects):
        if o.type != "MESH":
            continue
        me = o.data
        n = len(me.vertices)
        co = np.empty(n * 3, np.float32)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3).astype(np.float64)
        M = np.array(o.matrix_world)
        Vs.append(co @ M[:3, :3].T + M[:3, 3])
        me.calc_loop_triangles()
        t = np.empty(len(me.loop_triangles) * 3, np.int32)
        me.loop_triangles.foreach_get("vertices", t)
        Fs.append(t.reshape(-1, 3) + off)
        off += n
    bpy.ops.wm.read_factory_settings(use_empty=True)
    return np.concatenate(Vs), np.concatenate(Fs)


def scan_head_frame(V):
    """Midsagittal plane of the scanned face by mirror-ICP (trimmed, damped),
    seeded by the landmark picks, on the 30 mm ball around the muzzle (the
    right half of the head is noisy, so larger balls drift). Returns the
    rotation rows (forward, left, up) and origin (eye midpoint on the plane),
    scan metres."""
    nose, eR, eL = (np.array(SCAN_PICKS[k]) for k in ("nose", "eye_r", "eye_l"))
    m = 0.5 * (eR + eL)
    n = (eL - eR) / np.linalg.norm(eL - eR)
    cf = 0.5 * (m + nose)
    Fp = V[np.linalg.norm(V - cf, axis=1) < 0.030]
    kd = KDTree(len(Fp))
    for i, p in enumerate(Fp):
        kd.insert(p, i)
    kd.balance()
    d0 = m @ n
    for it in range(80):
        dd = Fp @ n - d0
        Rf = Fp - 2.0 * dd[:, None] * n
        idx = np.empty(len(Rf), np.int64)
        dist = np.empty(len(Rf))
        for i, p in enumerate(Rf):
            _, j, d = kd.find(p)
            idx[i] = j
            dist[i] = d
        keep = dist < np.percentile(dist, 50)
        P, Q = Fp[keep], Fp[idx[keep]]
        D = P - Q
        big = np.linalg.norm(D, axis=1) > 0.006
        D = D[big] * np.sign(D[big] @ n)[:, None]
        w, vv = np.linalg.eigh(D.T @ D)
        nn = vv[:, -1] * np.sign(vv[:, -1] @ n)
        d0 = float(np.median((0.5 * (P + Q))[big] @ nn))
        n = 0.5 * n + 0.5 * nn
        n /= np.linalg.norm(n)
    resid = float(np.median(dist)) * 1000.0
    z = np.array([0.0, 0.0, 1.0]) - n[2] * n
    z /= np.linalg.norm(z)
    f = np.cross(n, z)
    o = m - (m @ n - d0) * n
    log(f"scan midsagittal plane n={n.round(4)} residual {resid:.2f} mm (mirror-ICP, 30 mm muzzle ball)")
    return np.stack([f, n, z]), o, resid


def scan_soup_h0(V, F, R, o):
    """Clean left half + its mirror image, cropped to SCAN_BOX, in H0 mm."""
    H = (V - o) @ R.T * 1000.0
    cen = H[F].mean(1)
    lo, hi = SCAN_BOX
    keep = (cen[:, 1] > -1.5) & np.all((cen > lo - 2.0) & (cen < hi + 2.0), axis=1)
    Fk = F[keep]
    used = np.unique(Fk)
    remap = -np.ones(len(H), np.int64)
    remap[used] = np.arange(len(used))
    Pk = H[used]
    Fk = remap[Fk]
    Pm = Pk * np.array([1.0, -1.0, 1.0])
    P = np.vstack([Pk, Pm])
    Fm = Fk[:, ::-1] + len(Pk)
    return P, np.vstack([Fk, Fm])


def dilate6(m, iters):
    for _ in range(iters):
        g = m.copy()
        g[1:] |= m[:-1]
        g[:-1] |= m[1:]
        g[:, 1:] |= m[:, :-1]
        g[:, :-1] |= m[:, 1:]
        g[:, :, 1:] |= m[:, :, :-1]
        g[:, :, :-1] |= m[:, :, 1:]
        m = g
    return m


def flood_exterior(free, seed_faces):
    """Voxels of `free` connected to the given domain faces (6-connected)."""
    ext = np.zeros_like(free)
    for ax, side in seed_faces:
        sl = [slice(None)] * 3
        sl[ax] = 0 if side == 0 else -1
        ext[tuple(sl)] = True
    ext &= free
    it = 0
    while True:
        n0 = int(ext.sum())
        for _ in range(12):
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
    return ext, it


def scan_distance_field(P, F, vs=SCAN_VS, wall=4.0):
    """Signed distance field (mm, + outside) of the symmetrised scan soup.

    Unsigned distance from OpenVDB (narrow band), sign by flood-filling the
    exterior through voxels farther than `wall` mm from the scan, then
    growing it (and the interior core) back into the wall band only downhill
    in the distance, so the sign flips at the scan surface. Tunnels narrower
    than ~2*wall stay sealed: the scan's open ear canals (it tunnels down the
    vertical canal and out of the mesh) and some internal junk surfaces
    would otherwise let the exterior flood the head. Pits that taper (the
    conchae, the lid creases) are reclaimed by the downhill growth; constant-
    width tunnels are filled."""
    import openvdb as vdb
    t0 = time.time()
    tr = vdb.createLinearTransform(voxelSize=vs)
    hwv = 2.0 * wall / vs + 4.0
    g = vdb.FloatGrid.createLevelSetFromPolygons(P.astype(np.float32), triangles=F.astype(np.uint32), transform=tr, halfWidth=hwv)
    lo, hi = SCAN_BOX
    ilo = np.floor(lo / vs).astype(int)
    ihi = np.ceil(hi / vs).astype(int)
    shape = tuple(ihi - ilo + 1)
    D = np.empty(shape, np.float32)
    g.copyToArray(D, ijk=tuple(int(x) for x in ilo))
    D = np.abs(D)
    log(f"scan udf {shape} ({time.time()-t0:.0f}s)")
    free = D > wall
    # seed only from the top and front faces: the scanned body runs out of
    # the crop box through the bottom, back and side faces, so its interior
    # touches them; all the air around it is connected to the top face
    faces = [(0, 1), (2, 1)]
    ext, it = flood_exterior(free, faces)
    # resolve the sign inside the wall band: grow the exterior and the
    # interior core into the band only downhill in the unsigned distance, so
    # the two fronts meet at the distance minimum (the scan surface)
    E = ext.copy()
    I = (~ext) & (D > wall)
    U = ~(E | I)
    for _ in range(int(4 * wall / vs) + 24):
        ce = np.zeros_like(U)
        ci = np.zeros_like(U)
        for ax in range(3):
            for sgn in (1, -1):
                sl_dst = [slice(None)] * 3
                sl_src = [slice(None)] * 3
                if sgn > 0:
                    sl_dst[ax], sl_src[ax] = slice(1, None), slice(None, -1)
                else:
                    sl_dst[ax], sl_src[ax] = slice(None, -1), slice(1, None)
                d_, s_ = tuple(sl_dst), tuple(sl_src)
                down = D[s_] > D[d_]
                ce[d_] |= E[s_] & down
                ci[d_] |= I[s_] & down
        ne = U & ce
        ni = U & ci & ~ce
        if not ne.any() and not ni.any():
            break
        E |= ne
        I |= ni
        U &= ~(ne | ni)
    for _ in range(8):
        if not U.any():
            break
        ce = np.zeros(U.shape, np.int8)
        for ax in range(3):
            ce += np.roll(E, 1, ax).astype(np.int8) + np.roll(E, -1, ax).astype(np.int8)
            ce -= np.roll(I, 1, ax).astype(np.int8) + np.roll(I, -1, ax).astype(np.int8)
        ne = U & (ce > 0)
        ni = U & (ce < 0)
        E |= ne
        I |= ni
        U &= ~(ne | ni)
    I |= U
    log(f"scan sign band: {int(U.sum())} voxels left ambiguous (set inside)")
    S = np.where(E, D, -D).astype(np.float32)
    inside = int((S < 0).sum())
    log(f"scan sign: flood iters={it}, inside voxels={inside} ({inside * vs ** 3 / 1e3:.0f} cm3) ({time.time()-t0:.0f}s)")
    return S, ilo * vs


def stage_scan_field(args):
    """Scan -> symmetric signed distance field in H0 (cached)."""
    t0 = time.time()
    V, F = load_scan_raw()
    log(f"scan {len(V)} verts {len(F)} tris ({time.time()-t0:.0f}s)")
    R, o, resid = scan_head_frame(V)
    P, Fs = scan_soup_h0(V, F, R, o)
    log(f"symmetric soup {len(P)} verts {len(Fs)} tris ({time.time()-t0:.0f}s)")
    S, org = scan_distance_field(P, Fs)
    np.savez_compressed(CACHE / "scan_raw_field.npz", S=np.clip(S, -8.0, 8.0).astype(np.float16), origin=org, vs=SCAN_VS,
                        R=R, o=o, resid=resid)
    log(f"scan field saved ({time.time()-t0:.0f}s)")


def relevel(S, org, vs, smooth_w=0, band=16.0):
    """Re-derive a clean signed distance field from the zero set of S: the
    sign-resolved field keeps small negative values at internal junk surfaces
    of the scan, which a fine level set would mesh as bubbles. Mesh the zero
    isosurface (OpenVDB), keep its largest shell, rebuild the level set from
    that closed mesh. Optionally box-blur (3 passes of width smooth_w)."""
    import openvdb as vdb
    g = vdb.FloatGrid(float(np.abs(S).max()))
    g.transform = vdb.createLinearTransform(voxelSize=vs)
    ilo = np.round(np.asarray(org) / vs).astype(int)
    g.copyFromArray(S.astype(np.float32), ijk=tuple(int(x) for x in ilo), tolerance=0.0)
    g.gridClass = vdb.GridClass.LEVEL_SET
    pts, quads = g.convertToQuads(0.0)
    pts, quads = v6.keep_largest_component(pts.astype(np.float64), quads.astype(np.int64))
    tris = np.concatenate([quads[:, [0, 1, 2]], quads[:, [0, 2, 3]]])
    hw = band / vs
    g2 = vdb.FloatGrid.createLevelSetFromPolygons(pts.astype(np.float32), triangles=tris.astype(np.uint32),
                                                   transform=vdb.createLinearTransform(voxelSize=vs), halfWidth=hw)
    out = np.empty(S.shape, np.float32)
    g2.copyToArray(out, ijk=tuple(int(x) for x in ilo))
    if smooth_w:
        out = v6.gaussian_blur3(out, smooth_w)
    return out, pts, quads


# ---------------------------------------------------------------------------
# Scan field finalisation (H0, scan units) and the scan -> character mapping
# ---------------------------------------------------------------------------

# Similarity from the scan head frame H0 (scan units) to the character's
# world-local frame (mm, head origin at 0): fitted once by 2D ICP of the
# scan's midsagittal FACE profile (forehead, nose, muzzle, chin; trimmed at
# 85 %) onto the round-4 skin profile, whose skull is the CT placed in
# rounds 1-4. It fixes only scale, pitch and offset (rms 1.96 mm); every
# proportion comes from the scan. The scan is not metric (its eye spacing
# and sitting height are ~1.25x a real cat's): k maps scan units to
# character mm directly. A free 3D fit of the CT skull into the scan by
# tissue depths (exploratory, round 5) gave k = 1.78 (5 % smaller); the
# `measure` stage reports the CT tissue depths under the adopted mapping.
SCAN_TO_WORLD = dict(k=1.87386, phi=5.0795, tx=95.2167, tz=11.5345)
# scan ear regions (H0 scan units, mirrored in y): the laid-back, noisy
# pinnae are replaced by a heavily blurred scalp inside these ellipsoids
SCAN_EAR_MASK = dict(c=(-40.0, 54.0, 38.0), r=(34.0, 34.0, 26.0), soft=8.0, open=9.0)


def scan_to_world_mm(Ps):
    k, phi = SCAN_TO_WORLD["k"], math.radians(SCAN_TO_WORLD["phi"])
    c, s = math.cos(phi), math.sin(phi)
    x, y, z = Ps[..., 0], Ps[..., 1], Ps[..., 2]
    return np.stack([k * (c * x - s * z) + SCAN_TO_WORLD["tx"], k * y, k * (s * x + c * z) + SCAN_TO_WORLD["tz"]], -1)


def world_mm_to_scan(Pw):
    k, phi = SCAN_TO_WORLD["k"], math.radians(SCAN_TO_WORLD["phi"])
    c, s = math.cos(phi), math.sin(phi)
    qx, qy, qz = (Pw[..., 0] - SCAN_TO_WORLD["tx"]) / k, Pw[..., 1] / k, (Pw[..., 2] - SCAN_TO_WORLD["tz"]) / k
    return np.stack([c * qx + s * qz, qy, -s * qx + c * qz], -1)


def finalize_scan_field(S, org, vs):
    """Relevel, remove the midline crease, smooth fur noise (lighter on the
    face than on the cranium and neck) and replace the scan's pinnae by a
    heavily blurred scalp. All in H0 scan units."""
    t0 = time.time()
    Sc, _, _ = relevel(S, org, vs)
    X = [np.arange(Sc.shape[a]) * vs + org[a] for a in range(3)]
    gx = X[0][:, None, None]
    gy = X[1][None, :, None]
    gz = X[2][None, None, :]
    # midline: the mirrored halves meet with a slope break wherever the
    # scanned surface is not normal to the midsagittal plane; blur along y
    # only, within ~6 mm of the plane (the field is symmetric, so it stays so)
    By = Sc.copy()
    for _ in range(3):
        By = v6.box_blur_axis(By, 9, 1)
    wmid = np.exp(-(gy / 6.0) ** 2)
    Sc = Sc + (By - Sc) * wmid
    # fur-clump noise: sigma ~0.7 mm on the face, ~1.6 mm on the cranium,
    # nape and neck (fur texture there is coarse and the groom is long)
    S1 = v6.gaussian_blur3(Sc, 3)
    S2 = v6.gaussian_blur3(Sc, 7)
    S3 = v6.gaussian_blur3(Sc, 13)
    wb = np.clip(smoothstep(-8.0, -38.0, gx) + smoothstep(-42.0, -70.0, gz) + smoothstep(22.0, 40.0, gz), 0.0, 1.0)
    Sf = S1 + (S2 - S1) * wb
    Sf = Sf + (S3 - Sf) * np.clip(smoothstep(-48.0, -75.0, gz), 0.0, 1.0)
    # pinnae: a morphological opening (erode 9 mm, re-level, dilate 9 mm)
    # removes the laid-back, noisy scan ears and leaves the rounded scalp
    # under them; it is blended in only inside the ear masks
    r_open = SCAN_EAR_MASK["open"]
    So = relevel(Sf + r_open, org, vs, band=r_open + 6.0)[0] - r_open
    c, r, soft = np.array(SCAN_EAR_MASK["c"]), np.array(SCAN_EAR_MASK["r"]), SCAN_EAR_MASK["soft"]
    wear = np.zeros_like(Sf)
    for sgn in (1.0, -1.0):
        e = np.sqrt(((gx - c[0]) / r[0]) ** 2 + ((gy - sgn * c[1]) / r[1]) ** 2 + ((gz - c[2]) / r[2]) ** 2)
        wear = np.maximum(wear, 1.0 - smoothstep(1.0 - soft / r.mean(), 1.0, e))
    Sf = Sf + (np.maximum(So, Sf) - Sf) * wear
    log(f"scan field finalised ({time.time()-t0:.0f}s)")
    return Sf.astype(np.float32)


_SCAN_FIELD = {}


def scan_field():
    if "S" not in _SCAN_FIELD:
        d = np.load(CACHE / "scan_field.npz")
        _SCAN_FIELD.update(S=d["S"].astype(np.float32), org=d["origin"].astype(np.float64), vs=float(d["vs"]))
    return _SCAN_FIELD


def scan_sdf_world(P):
    """Signed distance (m, + outside) of the scan's fur surface at world-local
    points P (m), in character units."""
    f = scan_field()
    Ps = world_mm_to_scan(np.asarray(P, float) / MM)
    return v6.trilinear(f["S"], f["org"], f["vs"], Ps) * SCAN_TO_WORLD["k"] * MM


def stage_scan(args):
    raw = CACHE / "scan_raw_field.npz"
    if not raw.exists() or getattr(args, "rescan", False):
        stage_scan_field(args)
    d = np.load(raw)
    Sf = finalize_scan_field(d["S"].astype(np.float32), d["origin"], float(d["vs"]))
    np.savez_compressed(CACHE / "scan_field.npz", S=np.clip(Sf, -16.0, 16.0).astype(np.float16), origin=d["origin"], vs=d["vs"],
                        R=d["R"], o=d["o"], resid=d["resid"])
    _SCAN_FIELD.clear()
    log("scan field cached", CACHE / "scan_field.npz")


# ---------------------------------------------------------------------------
# Round-5 skin: scan head and neck + round-4 biped bust + surface details
# ---------------------------------------------------------------------------

# the scanned cat sits as a quadruped: below the neck its shoulders splay
# out; the scan is faded out here and the round-4 biped bust takes over
Z_CUT = -96.0  # world-local mm
K_CUT = 30.0
K_BUST = 30.0
# conchal cavity carved under each pinna (ear frame mm: x toward the opening)
CONCHA_C = (16.0, 0.0, -12.0)
CONCHA_R = (13.0, 15.0, 18.0)
# scalp cleared out of the cup: an elliptic prism (ear-frame x, y) above a
# floor that follows the pinna's base (medial margin high, lateral low)
CUP_C = (32.0, 8.0)
CUP_R = (20.0, 30.0)
CUP_FLOOR = (-28.0, -0.60)


def fur_inset_mm(Pw_mm):
    """Skin depth under the scan's fur surface (character mm): the thickness
    of the groom grown back on each region, so that skin + groom reproduces
    the scanned fur silhouette. Face 1.2-2, periocular 0.8, cranium 3,
    cheeks 4, jowl ruff 5.5, throat 7, neck ruff 15 (the scanned
    cat's neck ruff is deep; the round-4 pillar neck came from sculpting a
    fur-thick neck under fur)."""
    x, y, z = Pw_mm[..., 0], np.abs(Pw_mm[..., 1]), Pw_mm[..., 2]
    t = np.full(x.shape, 3.0)
    face = smoothstep(55.0, 95.0, x)
    t = t + (1.8 - t) * face
    t = t + (1.2 - t) * smoothstep(118.0, 135.0, x)
    cheek = smoothstep(55.0, 85.0, y) * (1.0 - smoothstep(10.0, 40.0, z))
    t = t + (4.2 - t) * cheek
    jowl = smoothstep(-15.0, -55.0, z) * smoothstep(20.0, 70.0, y) * (1.0 - smoothstep(110.0, 135.0, x))
    t = t + (5.5 - t) * jowl
    throat = smoothstep(-55.0, -80.0, z) * (1.0 - smoothstep(115.0, 130.0, x))
    t = t + (7.0 - t) * throat
    neck = smoothstep(-66.0, -100.0, z)
    t = t + (15.0 - t) * neck
    # periocular: the lids carry only very short hair
    for s in (1.0, -1.0):
        c = v6.eye_center(s) @ v6.head_R().T / MM
        d = np.sqrt((Pw_mm[..., 0] - c[0]) ** 2 + (Pw_mm[..., 1] - c[1]) ** 2 + (Pw_mm[..., 2] - c[2]) ** 2)
        t = t + (0.8 - t) * (1.0 - smoothstep(26.0, 36.0, d))
    return t


def scan_head_neck(P):
    """Scan-derived skin SDF (m) at world-local points P (m): fur surface
    minus the groom inset, faded out below Z_CUT."""
    Pmm = np.asarray(P, float) / MM
    d = scan_sdf_world(P) + fur_inset_mm(Pmm) * MM
    # conchal cavity: sink the scalp under each pinna's opening so the
    # concha reads as a deep, dark funnel (not a floor of scalp skin)
    Ph = np.asarray(P, float) @ v6.head_R()
    for s in (1.0, -1.0):
        base = A.ear_base * np.array([1.0, s, 1.0])
        q = (Ph - base) @ v6.ear_frame(s)
        d = v6.smax(d, -v6.sd_ellipsoid(q, v6.v(*CONCHA_C), v6.v(*CONCHA_R)), 4.0 * MM)
        # clear the scalp out of the cup between the margins (above the
        # pinna's base level), so no head skin rises inside the ear
        qm = q / MM
        rr = np.sqrt(((qm[..., 0] - CUP_C[0]) / CUP_R[0]) ** 2 + ((qm[..., 1] - CUP_C[1]) / CUP_R[1]) ** 2)
        e2 = (rr - 1.0) * min(CUP_R)
        # a bowl, not a flat floor: 9 mm deeper at the centre
        floor = CUP_FLOOR[0] + CUP_FLOOR[1] * qm[..., 1] - 9.0 * np.clip(1.0 - rr * rr, 0.0, 1.0)
        d_cup = np.maximum(e2, floor - qm[..., 2]) * MM
        d = v6.smax(d, -d_cup, 3.0 * MM)
    return v6.smax(d, (Z_CUT - Pmm[..., 2]) * MM, K_CUT * MM)


def build_bust_ops():
    """Round-4 biped bust ops (world frame) without the round-4 neck, nape
    and throat volumes, which the scanned neck replaces."""
    R = v6.rot_matrix
    ops = []
    for s in (1.0, -1.0):
        ops.append(v6.cap_op((-58.0, 30.0 * s, -92.0), (-56.0, 100.0 * s, -160.0), 26.0, 30.0, 34, frame="body"))
        ops.append(v6.ell_op((-78.0, 62.0 * s, -196.0), (16.0, 38.0, 64.0), R(roll=-16.0 * s), 30, frame="body"))
        ops.append(v6.ell_op((-34.0, 110.0 * s, -190.0), (38.0, 28.0, 62.0), R(roll=-14.0 * s), 36, frame="body"))
        ops.append(v6.cap_op((-30.0, 120.0 * s, -212.0), (-14.0, 146.0 * s, -424.0), 34.0, 29.0, 26, frame="body"))
        ops.append(v6.ell_op((28.0, 48.0 * s, -206.0), (32.0, 50.0, 48.0), R(yaw=18.0 * s, roll=-10.0 * s), 32, frame="body"))
    # neck base: carries the scanned neck section down into the thorax
    ops.append(v6.cap_op((-30.0, 0.0, -96.0), (-40.0, 0.0, -178.0), 78.0, 90.0, 30, frame="body"))
    ops.append(v6.ell_op((46.0, 0.0, -170.0), (24.0, 32.0, 38.0), None, 26, frame="body"))  # manubrium / sternum
    ops.append(v6.ell_op((-34.0, 0.0, -314.0), (102.0, 122.0, 205.0), None, 44, frame="body"))  # thorax
    return ops


def build_bust_field(vs=2.0 * MM):
    t0 = time.time()
    lo = np.floor(v6.DOMAIN_MIN / vs).astype(int) - 4
    hi = np.ceil(v6.DOMAIN_MAX / vs).astype(int) + 4
    shape = tuple(hi - lo + 1)
    xs = [np.arange(lo[a], hi[a] + 1) * vs for a in range(3)]
    ops = build_bust_ops()
    Bf = np.empty(shape, np.float32)
    for a in range(shape[0]):
        J, K = np.meshgrid(xs[1], xs[2], indexing="ij")
        P = np.stack([np.full_like(J, xs[0][a]), J, K], -1).reshape(-1, 3)
        f = np.full(len(P), 0.2)
        f = v6.apply_ops(ops, P, f)
        f = v6.smax(f, -(P[:, 2] + 0.600), 12 * MM)
        Bf[a] = f.reshape(J.shape)
    Bb = v6.gaussian_blur3(Bf, 5)
    log(f"bust field {shape} ({time.time()-t0:.0f}s)")
    return Bb, lo * vs


def combined_bulk(P, Bb, borg, bvs):
    """Scan head/neck united with the (blurred) bust."""
    return v6.smin(scan_head_neck(P), v6.trilinear(Bb, borg, bvs, P), K_BUST * MM)


def build_skin_mesh_v7(fine_vs=0.75 * MM, bulk_vs=2.0 * MM):
    import openvdb as vdb
    t0 = time.time()
    Bb, borg = build_bust_field(bulk_vs)
    np.savez_compressed(CACHE / "bust_field.npz", B=Bb, origin=borg, vs=bulk_vs)
    # coarse combined field (culling + the samplers used by the ear seat,
    # marking snap and lid margins)
    shape = Bb.shape
    xs = [np.arange(shape[a]) * bulk_vs + borg[a] for a in range(3)]
    Bc = np.empty(shape, np.float32)
    for a in range(shape[0]):
        J, K = np.meshgrid(xs[1], xs[2], indexing="ij")
        P = np.stack([np.full_like(J, xs[0][a]), J, K], -1)
        Bc[a] = combined_bulk(P, Bb, borg, bulk_vs)
    np.savez_compressed(CACHE / "bulk_field.npz", B=Bc, origin=borg, vs=bulk_vs)
    log(f"combined coarse field ({time.time()-t0:.0f}s)")
    v6.DETAIL_OPS = v6.build_detail_ops()
    union_boxes = [(op.lo, op.hi) for op in v6.DETAIL_OPS if op.mode == "union"]
    bw = 3.0 * fine_vs
    out = vdb.FloatGrid(bw)
    out.transform = vdb.createLinearTransform(voxelSize=fine_vs)
    flo = np.floor(v6.DOMAIN_MIN / fine_vs).astype(int)
    fhi = np.ceil(v6.DOMAIN_MAX / fine_vs).astype(int)
    T = 64
    tiles = 0
    for ti in range(flo[0], fhi[0] + 1, T):
        for tj in range(flo[1], fhi[1] + 1, T):
            for tk in range(flo[2], fhi[2] + 1, T):
                o = np.array([ti, tj, tk])
                tlo = o * fine_vs
                thi = (o + T) * fine_vs
                sub = [np.linspace(tlo[a], thi[a], 9) for a in range(3)]
                SG = np.stack(np.meshgrid(*sub, indexing="ij"), -1).reshape(-1, 3)
                bs = v6.trilinear(Bc, borg, bulk_vs, SG)
                near = not (bs.min() > 0.010 or bs.max() < -0.010)
                if not near:
                    near = any(np.all(thi >= lo_) and np.all(tlo <= hi_) for lo_, hi_ in union_boxes)
                if not near:
                    continue
                ax = [np.arange(o[a], o[a] + T) * fine_vs for a in range(3)]
                I, J, K = np.meshgrid(*ax, indexing="ij")
                Pf = np.stack([I, J, K], -1)
                Bv = combined_bulk(Pf, Bb, borg, bulk_vs)
                f = v6.detail_sdf(Pf, Bv).astype(np.float32)
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


def stage_skin_v7(args):
    pts, quads = build_skin_mesh_v7(fine_vs=args.voxel * MM)
    pts, quads = v6.keep_largest_component(pts, quads)
    quads = quads[:, ::-1]
    np.savez_compressed(CACHE / "skin_dense.npz", pts=pts.astype(np.float32), quads=quads.astype(np.int32))
    return pts, quads


# ---------------------------------------------------------------------------
# Exact skin field and the lid margin strip (round 5)
# ---------------------------------------------------------------------------

_BUST = {}


def exact_skin_sdf(P):
    """The skin level set's own field (scan + bust + detail ops), m."""
    if "B" not in _BUST:
        d = np.load(CACHE / "bust_field.npz")
        _BUST.update(B=d["B"], org=d["origin"], vs=float(d["vs"]))
        if v6.DETAIL_OPS is None:
            v6.DETAIL_OPS = v6.build_detail_ops()
    P = np.asarray(P, float)
    shp = P.shape[:-1]
    P2 = P.reshape(-1, 3)
    B = combined_bulk(P2, _BUST["B"], _BUST["org"], _BUST["vs"])
    return v6.detail_sdf(P2, B).reshape(shp)


def eye_surface_outline(side, n):
    """Closed almond outline ON the eye surface (globe or corneal cap, the
    outer of the two), 0.1 mm inside it: world-local points, eye-surface
    normals and the loop parameter (0..1: upper arc medial->lateral, then
    lower arc lateral->medial)."""
    Gf = v6.gaze_frame(side)
    t = math.radians(A.fissure_tilt)
    hw = 0.5 * A.fissure_w
    cd = v6.cornea_dims()
    cc_off = cd["apex"] - cd["Rc"]
    m = n // 2
    us = hw * np.sin(np.linspace(-0.5 * math.pi, 0.5 * math.pi, m + 1)) * 0.999
    up, lo = v6.fissure_curves(us)
    # upper arc medial -> lateral (both canthi included), lower arc lateral
    # -> medial (canthi excluded)
    uu = np.r_[us, us[-2:0:-1]]
    ww = np.r_[up, lo[-2:0:-1]]
    u = uu * math.cos(t) - ww * math.sin(t)
    w = uu * math.sin(t) + ww * math.cos(t)
    r2 = u * u + w * w
    xg = np.sqrt(np.maximum(A.eye_r ** 2 - r2, 1e-10))
    xc = cc_off + np.sqrt(np.maximum(cd["Rc"] ** 2 - r2, 1e-10))
    on_c = xc > xg
    x = np.maximum(xg, xc)
    local = np.stack([x, u * side, w], -1)
    nloc = np.where(on_c[:, None], local - np.array([cc_off, 0.0, 0.0]), local)
    nloc /= np.linalg.norm(nloc, axis=1, keepdims=True)
    local = local - nloc * 0.10 * MM
    ec = v6.eye_center(side)
    R = v6.head_R()
    P = (ec + local @ Gf.T) @ R.T
    Nn = (nloc @ Gf.T) @ R.T
    return P, Nn


def build_lid_margins_v7(coll, parent, n=320):
    """Round 5 lid margins (judged round 4: the margin floated off the globe
    as a separate ring). A swept strip per eye whose INNER EDGE LIES ON THE
    EYE (0.1 mm inside the globe/corneal surface along the almond fissure),
    rises as the ~1 mm lid-margin face to the actual lid skin (heights read
    from the skin's own field), rounds over 0.1-0.2 mm proud and tucks
    0.5-0.9 mm under the skin 2.6-3 mm out, so the black, wet margin
    contacts the cornea everywhere and covers the level set's voxel-scale
    lid edge. Tapers into the canthi."""
    mat = v6.lid_margin_material()
    bs = next(n_ for n_ in mat.node_tree.nodes if n_.type == "BSDF_PRINCIPLED")
    # round 5: darker and less glossy (the sky reflection greyed the margin
    # into a visor-like band in close-ups)
    bs.inputs["Base Color"].default_value = (0.009, 0.007, 0.007, 1.0)
    bs.inputs["Coat Roughness"].default_value = 0.10
    # wet only at the eye contact (margin_t < 0.3), matte pigmented skin
    # outward of it (the flat outer part mirrored the sky as a grey visor)
    nt = mat.node_tree
    at = v6.N(nt, "ShaderNodeAttribute", (-500, -200))
    at.attribute_name = "margin_t"
    mr = v6.N(nt, "ShaderNodeMapRange", (-250, -200))
    mr.interpolation_type = "SMOOTHSTEP"
    v6.L(nt, at.outputs["Fac"], mr.inputs["Value"])
    mr.inputs["From Min"].default_value = 0.22
    mr.inputs["From Max"].default_value = 0.45
    mr.inputs["To Min"].default_value = 0.24
    mr.inputs["To Max"].default_value = 0.62
    v6.L(nt, mr.outputs["Result"], bs.inputs["Roughness"])
    mc = v6.N(nt, "ShaderNodeMapRange", (-250, -400))
    mc.interpolation_type = "SMOOTHSTEP"
    v6.L(nt, at.outputs["Fac"], mc.inputs["Value"])
    mc.inputs["From Min"].default_value = 0.22
    mc.inputs["From Max"].default_value = 0.40
    mc.inputs["To Min"].default_value = 0.45
    mc.inputs["To Max"].default_value = 0.0
    v6.L(nt, mc.outputs["Result"], bs.inputs["Coat Weight"])
    objs = []
    A_S = np.array([0.0, 0.25, 0.6, 1.0, 1.5, 2.0, 2.6, 3.0]) * MM
    for s, tag in ((1.0, "L"), (-1.0, "R")):
        P, Nn = eye_surface_outline(s, n)
        m = len(P)
        cen = P.mean(0)
        T = np.roll(P, -1, 0) - np.roll(P, 1, 0)
        T /= np.linalg.norm(T, axis=1, keepdims=True)
        O = np.cross(T, Nn)
        flip = np.sum(O * (P - cen), 1) < 0
        O[flip] *= -1.0
        # smooth the outward direction round the sharp canthi
        for _ in range(14):
            O = (np.roll(O, 1, 0) + 2.0 * O + np.roll(O, -1, 0)) / 4.0
        O -= np.sum(O * Nn, 1, keepdims=True) * Nn
        O /= np.linalg.norm(O, axis=1, keepdims=True)
        # skin height above the eye surface at each outward offset
        H = np.zeros((m, len(A_S)))
        for j, a in enumerate(A_S):
            B0 = P + O * a
            lo = np.full(m, -0.5 * MM)
            hi = np.full(m, 6.0 * MM)
            for _ in range(30):
                mid = 0.5 * (lo + hi)
                inside = exact_skin_sdf(B0 + Nn * mid[:, None]) < 0.0
                lo = np.where(inside, mid, lo)
                hi = np.where(inside, hi, mid)
            H[:, j] = 0.5 * (lo + hi)
        # canthal taper: the strip narrows and flattens where the arcs meet
        # distance to the nearer canthus along the canthal line
        half = 0.5 * A.fissure_w
        lat = np.abs(((P - cen) @ v6.head_R()) @ v6.gaze_frame(s))[:, 1]
        taper = 0.35 + 0.65 * np.clip(1.0 - (lat / half) ** 4, 0.0, 1.0) ** 0.5
        k = 7
        pad = np.r_[H[-k:], H, H[:k]]
        H = np.stack([np.convolve(pad[:, j], np.ones(2 * k + 1) / (2 * k + 1), mode="same")[k:-k] for j in range(len(A_S))], 1)
        H = np.maximum(H, 0.35 * MM)
        h0 = H[:, 1]
        prof = [  # (outward a, height above the eye surface)
            (0.0, np.full(m, -0.15 * MM)),
            (0.0, 0.40 * h0),
            (0.10 * MM, 0.78 * h0),
            (0.30 * MM, h0 + 0.02 * MM * taper),
            (0.70 * MM, H[:, 2] + 0.03 * MM * taper),
            (1.20 * MM, H[:, 3] + 0.00 * MM),
            (1.80 * MM, H[:, 4] - 0.06 * MM),
            (2.30 * MM, H[:, 5] - 0.22 * MM),
            (2.80 * MM, H[:, 6] - 0.55 * MM),
            (3.10 * MM, H[:, 7] - 0.90 * MM),
        ]
        rings = [P + O * (a * (0.55 + 0.45 * taper))[:, None] + Nn * z[:, None] for a, z in prof]
        V = np.stack(rings, 1).reshape(-1, 3)  # (m * nprof)
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
        # attribute: 0 at the eye contact, 1 at the tucked outer edge (the
        # shader keeps the contact moist and pinkish-black)
        ta = me.attributes.new("margin_t", "FLOAT", "POINT")
        ta.data.foreach_set("value", np.tile(np.linspace(0.0, 1.0, nprof), m).astype(np.float32))
        for p_ in me.polygons:
            p_.use_smooth = True
        me.materials.append(mat)
        ob = v6.link(bpy.data.objects.new(me.name, me), coll)
        ob.parent = parent
        ob.matrix_world = Matrix.Translation(v6.HEAD_ORIGIN) if parent is not None and parent.type != "EMPTY" else Matrix.Identity(4)
        objs.append(ob)
    return objs


def build_caruncles_v7(coll, parent, mat):
    """A moist, pink-dark caruncle tucked into each medial canthus between
    the lid strip and the eye (round 4's was a 1.2 mm dot)."""
    objs = []
    for s, tag in ((1.0, "L"), (-1.0, "R")):
        P, Nn = eye_surface_outline(s, 320)
        i = int(np.argmin(P[:, 1] * s))
        c = P[i] + Nn[i] * 0.35 * MM
        cen = P.mean(0)
        toward = cen - P[i]
        toward /= np.linalg.norm(toward)
        c = c + toward * 2.4 * MM + Nn[i] * 0.25 * MM
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=1.0)
        cr = bpy.context.object
        cr.name = f"CatBaseV6_Eye{tag}_Caruncle"
        z = Vector(Nn[i]).normalized()
        x = Vector(toward).normalized()
        y = z.cross(x)
        M = Matrix((x, y, z)).transposed().to_4x4()
        M.translation = Vector(c) + (v6.HEAD_ORIGIN if parent is not None and parent.type != "EMPTY" else Vector())
        cr.matrix_world = M @ Matrix.Diagonal((2.8 * MM, 2.0 * MM, 1.4 * MM, 1.0))
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


# ---------------------------------------------------------------------------
# Round-5 pinna: a thick, deep conchal shell set on the scan's ear base
# ---------------------------------------------------------------------------

def seat_ear_columns(Pr, tr, side, sdf, depth=2.5 * MM, t_free=0.28):
    """Seat the pinna by sliding each ring column along the ear axis until
    its t = 0 point lies `depth` inside the head, fading to no shift at
    t_free (round 4's per-vertex gradient pull crumpled the lateral base,
    which stands far above the sloping head surface)."""
    u = v6.ear_frame(side)[:, 2] @ v6.head_R().T
    i0 = int(np.argmax(tr >= 0.0))
    P0 = Pr[i0]
    lo = np.full(len(P0), -0.036)  # shift along +u (m): negative = down
    hi = np.full(len(P0), 0.030)
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        inside = sdf(P0 + mid[:, None] * u[None, :]) < -depth
        lo = np.where(inside, mid, lo)
        hi = np.where(inside, hi, mid)
    delta = 0.5 * (lo + hi)
    k = 9
    pad = np.r_[delta[-k:], delta, delta[:k]]
    delta = np.convolve(pad, np.ones(2 * k + 1) / (2 * k + 1), mode="same")[k:-k]
    w = 1.0 - smoothstep(0.0, t_free, np.clip(tr, 0.0, None))
    w = np.where(tr < 0.0, 1.0, w)
    return Pr + (w[:, None, None] * delta[None, :, None]) * u[None, None, :]


def ear_arrays_v7(side=1.0, n_t=110, n_face=52, n_rim=9, sdf=None):
    """Parametric pinna (world-local metres) as closed quad rings, built like
    round 4's (inner face, lateral rim, back, medial rim per ring) but
    re-proportioned against the scanned head (judged round 4: cardboard-flat
    ears with no conchal depth, set like a bat's):

    - 1.4x taller (96 mm) and wider (78 mm) than round 4, set on the scan's
      ear base above its ear-canal pit, leaning 14 deg out and 12 deg back
      (upright in the world once the head's 12 deg pitch is applied), the
      opening facing 24 deg outward of forward (round 4: 38 + 18 deg twist);
    - the cross-section is sized by the ear WIDTH and bent 255 deg at the
      base (a nearly closed conchal tube whose rolled margins frame a dark
      entrance), ~170 deg at mid-height and ~75 deg at the tip;
    - real thickness: 3.2 mm of cartilage and skin at the base, 1.4 mm at the
      tip, with a rolled helix on both margins (medial rim ~2.3 mm, lateral
      ~1.8 mm);
    - Henry's pocket: a lobe on the lateral margin at 8-22 % height that
      stands out ~6 mm with a notch above it and a fold line on the back;
    - the inner face carries three transverse antihelical ridges in the
      lower 40 % and the antitragus/tragus at the entrance;
    - the buried funnel (t < 0) narrows and dives toward the canal pit so
      the entrance reads as a hole, not a pink floor.

    Attributes are round 4's (is_ear, ear_t, ear_u, ear_face)."""
    H = A.ear_h / MM
    W0 = A.ear_chord / MM
    tip = A.ear_tip_r / MM
    t_lo = -26.0 / H
    ts = np.concatenate([np.linspace(t_lo, 0.0, 16, endpoint=False), np.linspace(0.0, 1.0, n_t)])
    uf = np.sin(np.linspace(-0.5 * math.pi, 0.5 * math.pi, n_face))
    rings, attrs = [], []
    tcap = 1.0 - 1.6 * tip / H
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
        hp = float(v6._bump(np.array(tc), 0.08, 0.22))
        notch = float(v6._bump(np.array(tc), 0.25, 0.31))
        w_med = 0.47 * S
        w_lat = 0.53 * S + 6.0 * hp - 2.0 * notch
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
        for tk in (0.06, 0.15, 0.26):
            ridge += 0.9 * math.exp(-((tc - tk) / 0.028) ** 2) * (1.0 - smoothstep(0.25, 0.6, np.abs(uf + 0.25)))
        ridge += 2.4 * math.exp(-((t - 0.02) / 0.06) ** 2) * np.exp(-((uf - 0.74) / 0.15) ** 2)  # antitragus
        ridge += 1.8 * math.exp(-((t + 0.03) / 0.06) ** 2) * np.exp(-((uf + 0.80) / 0.13) ** 2)  # tragus
        front = p + nin * (0.5 * T + ridge)[:, None]
        crease = 1.2 * hp * np.exp(-((uf - 0.80) / 0.06) ** 2)
        back = p - nin * (0.5 * T - crease)[:, None]
        rim_pts, rim_u = [], []
        for end in (+1, -1):
            pe, ne, te = arc(np.array([w_lat if end > 0 else -w_med]))
            pe, ne, te = pe[0], ne[0], te[0] * end
            roll = (1.15 if end < 0 else 0.85) * (1.0 - 0.55 * tc)
            rr = 0.5 * T + roll
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
    Rr = np.array(rings) * MM
    At = np.array(attrs)
    nr, npr, _ = Rr.shape
    q = Rr.reshape(-1, 3).copy()
    q[:, 1] *= side
    base = A.ear_base.copy()
    base[1] *= side
    Ph = base + q @ v6.ear_frame(side).T
    Pw = Ph @ v6.head_R().T
    if sdf is not None:
        Pw = seat_ear_columns(Pw.reshape(nr, npr, 3), At[:, 0, 0], side, sdf).reshape(-1, 3)
    # two mesh islands per ear, split along the crest of each rolled rim:
    # the groom interpolates children only from guides on the same island,
    # so back-coat children can no longer take inner-face guides (or the
    # reverse) and poke through the 1.4-3 mm sheet (round-5 test frames:
    # dark specks on the inner face near the tip)
    A2 = At.reshape(-1, 3)
    idx = np.arange(nr * npr).reshape(nr, npr)
    cL = n_face + n_rim // 2
    cM = 2 * n_face + n_rim + n_rim // 2
    inner_cols = list(range(cM, npr)) + list(range(0, cL + 1))
    back_cols = list(range(cL, cM + 1))
    P_list = [Pw]
    A_list = [A2]
    nxt = nr * npr
    # duplicate the two split columns for the back island
    dup = {}
    for c in (cL, cM):
        dup[c] = np.arange(nxt, nxt + nr)
        P_list.append(Pw.reshape(nr, npr, 3)[:, c])
        A_list.append(At[:, c])
        nxt += nr
    tip_ids = []
    for strip in (0, 1):
        cols = inner_cols if strip == 0 else back_cols
        last = [idx[-1, c] if not (strip == 1 and c in dup) else dup[c][-1] for c in cols]
        tip_ids.append(nxt)
        P_list.append(Pw.reshape(nr, npr, 3)[-1, cols].mean(0)[None] + ((np.array([0.0, 0.0, 0.25 * MM]) @ v6.ear_frame(side).T) @ v6.head_R().T)[None])
        A_list.append(np.array([[1.0, 0.0, 1.0 if strip == 0 else -1.0]]))
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
    quads = np.array(quads)
    tris = np.array(tris)
    attrs = dict(is_ear=np.ones(len(Pw)), ear_t=A2[:, 0], ear_u=A2[:, 1], ear_face=A2[:, 2])
    return Pw, quads, tris, attrs


def ear_mesh_v7(side=1.0, name=None):
    """Like round 4's ear_mesh, but the two open islands are oriented by the
    pinna frame (the inner face's normals must face the opening, the back
    coat's face away); bmesh's normal recalculation is unreliable on open
    sheets."""
    Pw, quads, tris, attrs = v6.ear_arrays(side, sdf=v6.head_sdf_sampler())
    faces = [tuple(int(i) for i in q) for q in quads] + [(int(t[0]), int(t[1]), int(t[2])) for t in tris]
    # probe: a quad on the inner face at mid height, mid width
    fc = np.array([Pw[list(f)].mean(0) for f in faces[: len(quads)]])
    ef = attrs["ear_face"]
    et = attrs["ear_t"]
    eu = attrs["ear_u"]
    q = np.array(quads)
    inner = (ef[q].min(1) > 0.5) & (np.abs(et[q].mean(1) - 0.5) < 0.05) & (np.abs(eu[q].mean(1)) < 0.2)
    k = int(np.argmax(inner))
    a, b, c = Pw[q[k, 0]], Pw[q[k, 1]], Pw[q[k, 2]]
    nrm = np.cross(b - a, c - a)
    opening = (v6.ear_frame(side)[:, 0]) @ v6.head_R().T
    if nrm @ opening < 0:
        faces = [f[::-1] for f in faces]
    me = bpy.data.meshes.new(name or f"CatBaseV6_Ear{'L' if side > 0 else 'R'}")
    me.from_pydata(Pw.tolist(), [], faces)
    me.update()
    for k_, val in attrs.items():
        at = me.attributes.new(k_, "FLOAT", "POINT")
        at.data.foreach_set("value", np.asarray(val, np.float32))
    for p_ in me.polygons:
        p_.use_smooth = True
    return me


# ---------------------------------------------------------------------------
# Round-5 parameter overrides of the v6 layout (applied before any stage)
# ---------------------------------------------------------------------------

NOSE_DZ = 6.0  # the scanned nose sits ~6 mm higher (head frame) than round 4's


def apply_round5_overrides():
    if getattr(v6, "_ROUND5", False):
        return
    v6._ROUND5 = True
    # lids: the globe and corneal-cap cavities are carved 0.25 mm INSIDE the
    # globe, so the lid skin meets the eye with no gap (round 4 carved them
    # 0.6 mm outside it and floated a tube over the gap)
    A.lid_gap = -0.25 * MM
    # the scanned muzzle already has its whisker pads: only a 1 mm lift
    v6.PAD_H = 1.0
    # nose leather, nares, alar folds and the top of the philtrum follow the
    # scanned nose
    sh = lambda poly: [(a, b + NOSE_DZ) for a, b in poly]
    v6.LEATHER_HALF = sh(v6.LEATHER_HALF)
    v6.NOSTRIL_POLY = sh(v6.NOSTRIL_POLY)
    v6.ALAR_POLY = sh(v6.ALAR_POLY)
    v6.PHILTRUM = [(0.0, -12.5 + NOSE_DZ), (0.0, -30.0)]
    # pinnae on the scan's ear bases (above the ear-canal pits found in the
    # opened scan at head (-32, +/-64, 21)), 1.4x round 4's size
    A.ear_base = v6.v(-18.0, 52.0, 47.0)
    A.ear_h = 78.0 * MM
    A.ear_chord = 86.0 * MM
    A.ear_tip_r = 6.5 * MM
    A.ear_t0 = 3.2 * MM
    A.ear_t1 = 2.0 * MM
    A.ear_lean_out = 24.0
    A.ear_lean_back = 12.0
    A.ear_open_out = 24.0
    A.ear_twist = 10.0
    v6.ear_arrays = ear_arrays_v7
    v6.ear_mesh = ear_mesh_v7
    v6.coat_fields = coat_fields_v7
    # a relaxed, less wide-open eye (the round-5 test frames read as startled
    # next to the Nyaakoto reference): upper arc 14 -> 11.5 mm, lower 12.8 -> 11.8
    A.fissure_up = 11.5 * MM
    A.fissure_lo = 11.8 * MM
    # the mascara line and cheek bars read as thin hard lines on the broader
    # scanned cheeks (test frames): widen them into tabby stripes
    widen = {"mascara": 1.7, "cheek2": 1.35, "cheek3": 1.3}
    v6.MARKINGS = [(nm, pts, [w * widen.get(nm, 1.0) for w in wid]) for nm, pts, wid in v6.MARKINGS]
    v6._MARK_CACHE.clear()
    orig_iris = v6.iris_arrays

    def iris_arrays_v7(side, rings=110, segs=420, seed=0):
        # 20 % less chroma: Nyaakoto's eyes are a pale grey-blue
        P, quads, uv, C = orig_iris(side, rings, segs, seed)
        lum = (C @ np.array([0.2126, 0.7152, 0.0722]))[:, None]
        return P, quads, uv, lum + (C - lum) * 0.80

    v6.iris_arrays = iris_arrays_v7
    v6.fur_direction = fur_direction_v7


def preview_ears(args, with_head=True):
    """Workbench close-ups of the left pinna on the dense skin (review aid)."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    if with_head:
        d = np.load(CACHE / "skin_dense.npz")
        me = v6.mesh_from_arrays("dense", d["pts"], d["quads"])
        me.shade_smooth()
        ob = v6.link(bpy.data.objects.new("dense", me))
    for side in (1.0, -1.0):
        v6.link(bpy.data.objects.new(f"ear{side}", v6.ear_mesh(side)))
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.show_cavity = True
    sc.render.resolution_x = 900
    sc.render.resolution_y = 900
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.lens = 85
    base = Vector(A.ear_base @ v6.head_R().T) + Vector((0.0, 0.0, 0.04))
    views = (("e_front", Vector((1, 0.05, 0.1)), 0.42), ("e_lat", Vector((0.15, 1, 0.1)), 0.42), ("e_back", Vector((-1, 0.3, 0.2)), 0.42),
             ("e_tq", Vector((0.8, 0.6, 0.15)), 0.42), ("e_top", Vector((0.2, 0.1, 1)), 0.42), ("h_front", Vector((1, 0, 0.03)), 1.1),
             ("h_tq", Vector((0.72, -0.69, 0.06)), 1.1), ("h_profile", Vector((0.0, -1.0, 0.02)), 1.1))
    for name, d_, dist in views:
        t = base if name.startswith("e_") else Vector((0.06, 0.0, 0.0))
        cam.location = t + d_.normalized() * dist
        cam.rotation_euler = (t - cam.location).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = str(Path(args.preview_dir) / f"{name}.png")
        bpy.ops.render.render(write_still=True)


def preview_eyes(args):
    """Workbench close-ups of the left eye region: dense skin, globe, cornea
    and (when built) the lid-margin strip and caruncle (review aid)."""
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
    if getattr(args, "with_margin", True):
        coll = bpy.context.scene.collection
        par = bpy.data.objects.new("par", None)
        coll.objects.link(par)
        for ob in build_lid_margins_v7(coll, par):
            ob.matrix_world = Matrix.Identity(4)
        build_caruncles_v7(coll, par, None)
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.show_cavity = True
    sc.render.resolution_x = 900
    sc.render.resolution_y = 900
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.lens = 85
    eye = Vector(v6.lid_center(1.0) @ v6.head_R().T)
    for name, d_, dist in (("y_front", Vector((1, 0.1, 0.05)), 0.30), ("y_tq", Vector((0.75, 0.62, 0.1)), 0.30), ("y_side", Vector((0.2, 1, 0.05)), 0.30),
                           ("y_up", Vector((0.8, 0.2, 0.55)), 0.30), ("y_low", Vector((0.85, 0.25, -0.45)), 0.30), ("y_med", Vector((0.8, -0.55, 0.1)), 0.30)):
        cam.location = eye + d_.normalized() * dist
        cam.rotation_euler = (eye - cam.location).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = str(Path(args.preview_dir) / f"{name}.png")
        bpy.ops.render.render(write_still=True)


# ---------------------------------------------------------------------------
# Coat, groom and ear-furnishing refit for the scanned head (round 5)
# ---------------------------------------------------------------------------

def cup_weight(Pw):
    """1 on head skin inside a pinna's cleared conchal bowl (the head coat
    must not grow there: round-5 test frames showed a dark tabby patch
    inside the ear), 0 elsewhere."""
    Ph = np.asarray(Pw, float) @ v6.head_R()
    w = np.zeros(Ph.shape[:-1])
    for s in (1.0, -1.0):
        base = A.ear_base * np.array([1.0, s, 1.0])
        q = (Ph - base) @ v6.ear_frame(s) / MM
        rr = np.sqrt(((q[..., 0] - CUP_C[0]) / CUP_R[0]) ** 2 + ((q[..., 1] - CUP_C[1]) / CUP_R[1]) ** 2)
        floor = CUP_FLOOR[0] + CUP_FLOOR[1] * q[..., 1] - 9.0 * np.clip(1.0 - rr * rr, 0.0, 1.0)
        ws = (1.0 - smoothstep(0.92, 1.10, rr)) * smoothstep(floor - 14.0, floor - 8.0, q[..., 2])
        ec = np.sqrt(sum(((q[..., k] - CONCHA_C[k]) / CONCHA_R[k]) ** 2 for k in range(3)))
        ws = np.maximum(ws, 1.0 - smoothstep(1.0, 1.25, ec))
        w = np.maximum(w, ws)
    return w


_V6_COAT = v6.coat_fields
_V6_FURDIR = v6.fur_direction


def coat_fields_v7(Pw, Nw, ex=None):
    f = _V6_COAT(Pw, Nw, ex)
    Pw = np.asarray(Pw, float)
    n = len(Pw)
    is_ear, ear_t, ear_u, ear_face = v6.ex_arrays(n, ex)
    earm = is_ear > 0.5
    inner = earm & (ear_face > 0.2)
    back = earm & ~inner
    au = np.abs(ear_u)
    cup = cup_weight(Pw) * (~earm)
    Ph = Pw @ v6.head_R()
    x, y, z = Ph[:, 0] / MM, Ph[:, 1] / MM, Ph[:, 2] / MM
    # white muzzle: the scanned pads sit higher and wider than round 4's
    jit = (v6.fbm(Pw, 0.0011, 2, 11.0) - 0.5) * 1.3 + (v6.fbm(Pw, 0.022, 2, 12.0) - 0.5) * 3.2
    muz = np.sqrt(((x - 126.0 - A.mz) / 34.0) ** 2 + (y / 45.0) ** 2 + ((z + 29.0) / 30.0) ** 2)
    w2 = (1.0 - smoothstep(-0.3, 0.3, (muz - 1.0) * 26.0 + jit)) * (~earm)
    # a broader blaze between the eyes, tapering up the forehead (Nyaakoto)
    wb2 = np.clip(17.0 - 0.30 * (z + 5.0), 4.0, 17.0)
    blaze2 = np.maximum(np.maximum(np.abs(y) - wb2, z - 44.0), 96.0 - x)
    w2 = np.maximum(w2, (1.0 - smoothstep(-0.3, 0.3, blaze2 + jit)) * (~earm))
    white = np.maximum(f["white"], w2)
    white = np.where(inner, 1.0, np.maximum(white, smoothstep(0.3, 0.7, cup)))
    stripe = f["stripe"] * (1.0 - w2) * (1.0 - cup)
    pale = f["pale"] * (1.0 - cup)
    # inner-ear skin: darker and greyer deep in the concha and in the bowl
    conch = inner * (1.0 - smoothstep(0.0, 0.40, ear_t)) * (1.0 - smoothstep(0.45, 0.9, au))
    pig = np.maximum(f["pig"], np.maximum(0.50 * conch, 0.55 * cup))
    ear_inner = np.maximum(f["ear_inner"], cup)
    # groom: inner face covered in fine pale hair that lengthens toward the
    # margins and lifts off the skin; short rim hair that lies along the
    # margin (round 4's outward rim fringe read as a pipe cleaner)
    L = f["length"] / MM
    rim = smoothstep(0.86, 0.98, au)
    L = np.where(inner, 4.0 + 3.6 * smoothstep(0.45, 0.92, au), L)
    L = np.where(back, np.where(rim > 0.5, 2.2, L * (1.0 - 0.35 * smoothstep(0.45, 0.9, ear_t))), L)
    L = np.where(cup > 0.5, 8.0, L)
    # short, flat coat just in front of and around each ear base (the crown
    # coat rose into the lower ear opening in the test frames)
    pre = np.zeros(n)
    for s_ in (1.0, -1.0):
        base = A.ear_base * np.array([1.0, s_, 1.0])
        q = (Ph - base) @ v6.ear_frame(s_) / MM
        pre = np.maximum(pre, v6._bump(q[:, 0], -5.0, 70.0) * v6._bump(q[:, 1], -40.0, 55.0) * v6._bump(q[:, 2], -45.0, 12.0))
    pre = pre * (~earm) * (1.0 - smoothstep(0.3, 0.6, cup))
    L = np.where(pre > 0.0, L * (1.0 - pre) + np.minimum(L, 4.5) * pre, L)
    lift = np.where(inner, 22.0 + 12.0 * smoothstep(0.5, 0.9, au), f["lift"])
    lift = lift * (1.0 - pre) + np.minimum(lift, 6.0) * pre
    lift = np.where(back, np.where(rim > 0.5, 3.0, np.minimum(lift, 6.0)), lift)
    lift = np.where(cup > 0.5, 32.0, lift)
    deep = 1.0 - smoothstep(0.03, 0.14, ear_t)
    dens = np.where(inner, (0.60 + 0.35 * smoothstep(0.45, 0.9, au)) * (1.0 - 0.5 * deep), f["density"])
    dens = np.where(cup > 0.5, 0.85, dens)
    # fur reaches ~0.9-1.6 mm from the fissure (round 4: 1.3-2.2) so it
    # overlaps the outer, matte part of the lid-margin strip
    excl = np.maximum(f["excl"], smoothstep(0.9, 1.6, f["d_fis"]) * (1.0 - f["nose"]) * (1.0 - f["lip"]) * (f["d_fis"] < 3.0))
    f.update(excl=np.clip(excl, 0, 1))
    f.update(white=np.clip(white, 0, 1), stripe=np.clip(stripe, 0, 1), pale=pale, pig=np.clip(pig, 0, 1), ear_inner=ear_inner,
             length=L * MM, lift=lift, density=np.clip(dens, 0, 1))
    return f


def fur_direction_v7(Pw, Nw, ex=None):
    t = _V6_FURDIR(Pw, Nw, ex)
    Pw = np.asarray(Pw, float)
    Nw = np.asarray(Nw, float)
    n = len(Pw)
    is_ear, ear_t, ear_u, ear_face = v6.ex_arrays(n, ex)
    earm = is_ear > 0.5
    cup = cup_weight(Pw) * (~earm)
    sy = np.where(Pw[:, 1] >= 0.0, 1.0, -1.0)
    for s in (1.0, -1.0):
        F = v6.ear_frame(s)
        ax = F[:, 2] @ v6.head_R().T
        lat = (F[:, 1] * s) @ v6.head_R().T
        m = earm & (sy == s)
        if m.any():
            rim = smoothstep(0.80, 0.97, np.abs(ear_u[m]))[:, None]
            out_ = np.sign(ear_u[m])[:, None] * lat[None, :]
            t[m] = ax[None, :] * (1.0 - 0.25 * rim) + out_ * 0.25 * rim
        mc = (cup > 0.3) & (sy == s)
        if mc.any():
            t[mc] = ax[None, :]
    t = t - np.sum(t * Nw, 1, keepdims=True) * Nw
    t /= np.linalg.norm(t, axis=1, keepdims=True) + 1e-9
    return t


def build_inner_ear_furnishings_v7(coll, skin, images):
    """Round 5 furnishings (judged round 4: they gathered along the medial
    margin and the lower opening read as bare pink): 2,600 clumped tufts
    of 6-11 white-to-pale-grey hairs, 14-30 mm, rooted over the whole lower
    inner face (medial margin, conchal floor and wall, antitragus) and the
    cleared bowl, fanning up and out of the conchal opening."""
    rng = np.random.default_rng(v6.RNG_SEED + 2)
    S = v6.evaluated_surface(skin)

    def wfn(c, n, ex):
        front = ex["is_ear"] * smoothstep(0.2, 0.6, ex["ear_face"])
        vis = smoothstep(0.02, 0.06, ex["ear_t"])  # not the buried funnel
        med = (1.0 - smoothstep(-0.80, -0.45, ex["ear_u"])) * v6._bump(ex["ear_t"], 0.06, 0.62)
        anti = smoothstep(0.40, 0.62, ex["ear_u"]) * (1.0 - smoothstep(0.88, 0.97, ex["ear_u"])) * v6._bump(ex["ear_t"], 0.04, 0.26)
        floor = v6._bump(ex["ear_t"], 0.04, 0.38) * (1.0 - smoothstep(0.55, 0.85, np.abs(ex["ear_u"])))
        return front * vis * (1.3 * med + 1.0 * anti + 1.5 * floor)

    n_tuft = 4000
    cpos, cnrm, cuv, cex = v6.sample_roots(S, n_tuft, wfn, rng)
    npts = 12
    strands, uvs = [], []
    for i in range(n_tuft):
        s = 1.0 if (cpos[i] @ v6.head_R())[1] > 0 else -1.0
        F = v6.ear_frame(s)
        up = F[:, 2] @ v6.head_R().T
        fwd = F[:, 0] @ v6.head_R().T
        lat = F[:, 1] * s @ v6.head_R().T
        eu, et = cex["ear_u"][i], cex["ear_t"][i]
        if abs(eu) < 0.5 and et < 0.45:
            # conchal floor and bowl: straight up and out of the opening
            d = 0.60 * up + 0.75 * fwd + 0.10 * lat * rng.normal() + 0.2 * cnrm[i]
            Lt = rng.uniform(20.0, 36.0) * MM
        elif eu < 0.0:
            # medial margin: rise, lean laterally across the opening and forward
            d = 0.55 * up + 0.65 * fwd + 0.50 * lat + 0.25 * cnrm[i]
            Lt = rng.uniform(18.0, 30.0) * MM
        else:
            # antitragus / lateral wall: rise and lean medially
            d = 0.60 * up + 0.60 * fwd - 0.40 * lat + 0.25 * cnrm[i]
            Lt = rng.uniform(14.0, 22.0) * MM
        d /= np.linalg.norm(d)
        k = int(rng.integers(6, 12))
        for _ in range(k):
            off = rng.normal(0.0, 0.5 * MM, 3)
            off -= (off @ cnrm[i]) * cnrm[i]
            p = cpos[i] + off - cnrm[i] * 0.2 * MM
            dh = d + rng.normal(0.0, 0.12, 3)
            dh /= np.linalg.norm(dh)
            Lh = Lt * rng.uniform(0.7, 1.1)
            curl = rng.normal(0, 0.07, 3)
            pts = [p.copy()]
            for kk in range(1, npts):
                s_ = kk / (npts - 1)
                dd = dh + curl * s_ + np.array([0, 0, -0.22]) * s_ * s_
                dd /= np.linalg.norm(dd)
                p = p + dd * Lh / (npts - 1)
                pts.append(p.copy())
            strands.append(pts)
            uvs.append(cuv[i])
    strands = np.array(strands)
    uv = np.array(uvs)
    t = np.linspace(0, 1, npts)
    radii = np.repeat(((0.068 * MM) * (1 - t) ** 0.8 + 0.008 * MM)[None], len(strands), 0)
    ob = v6.make_curves("CatBaseV6_Fur_EarFurnishings", strands, 0, 0, coll, uv=uv, surface=skin, radii=radii)
    ob.parent = skin
    m, nt = v6.new_mat("M_CatBaseV6_EarFurnishing")
    out = v6.N(nt, "ShaderNodeOutputMaterial", (600, 0))
    hb = v6.N(nt, "ShaderNodeBsdfHairPrincipled", (300, 0))
    hb.parametrization = "COLOR"
    hb.model = "CHIANG"
    info = v6.N(nt, "ShaderNodeHairInfo", (-400, 0))
    rj = v6.N(nt, "ShaderNodeMapRange", (-200, 0))
    v6.L(nt, info.outputs["Random"], rj.inputs["Value"])
    rj.inputs["To Min"].default_value = 0.62
    rj.inputs["To Max"].default_value = 0.80
    cc = v6.N(nt, "ShaderNodeCombineColor", (0, 0))
    v6.L(nt, rj.outputs["Result"], cc.inputs["Red"])
    v6.L(nt, rj.outputs["Result"], cc.inputs["Green"])
    cc2 = v6.N(nt, "ShaderNodeMath", (0, -150))
    cc2.operation = "MULTIPLY"
    v6.L(nt, rj.outputs["Result"], cc2.inputs[0])
    cc2.inputs[1].default_value = 0.98
    v6.L(nt, cc2.outputs[0], cc.inputs["Blue"])
    v6.L(nt, cc.outputs["Color"], hb.inputs["Color"])
    hb.inputs["Roughness"].default_value = 0.34
    hb.inputs["Radial Roughness"].default_value = 0.4
    hb.inputs["Coat"].default_value = 0.0
    hb.inputs["IOR"].default_value = 1.3
    v6.L(nt, hb.outputs["BSDF"], out.inputs["Surface"])
    ob.data.materials.append(m)
    return ob


_V6_SKIN_MAT = v6.skin_material


def skin_material_v7(images):
    """Round-4 skin shader with a darker, greyer inner-ear skin and less
    translucency (the round-5 test frames showed a bright pink sheet)."""
    m = _V6_SKIN_MAT(images)
    for nd in m.node_tree.nodes:
        if nd.type == "MIX" and nd.data_type == "RGBA":
            col = tuple(round(c, 2) for c in nd.inputs[7].default_value[:3])
            if col == (0.56, 0.42, 0.40):
                nd.inputs[7].default_value = (0.44, 0.31, 0.29, 1.0)
        if nd.type == "MATH" and nd.operation == "MULTIPLY" and abs(nd.inputs[1].default_value - 0.20) < 1e-6:
            nd.inputs[1].default_value = 0.12
    return m


# ---------------------------------------------------------------------------
# Measurement: CT landmark tissue depths under the scan-derived skin
# ---------------------------------------------------------------------------

CT_REGIONS = {  # skull-local char mm boxes, outward direction
    "frontal": (([60, -14, 0], [100, 14, 90]), (0, 0, 1)),
    "nasal": (([100, -10, -10], [132, 10, 40]), (0.3, 0, 1)),
    "premaxilla": (([112, -16, -60], [135, 16, -5]), (1, 0, 0)),
    "symphysis": (([95, -20, -90], [135, 20, -40]), (0.6, 0, -0.8)),
    "mandible_ventral": (([0, -60, -90], [90, 60, -50]), (0, 0, -1)),
    "zygomatic_arch": (([0, 55, -10], [50, 90, 35]), (0, 1, 0)),
    "postorbital": (([30, 30, 25], [60, 70, 60]), (0.3, 0.6, 0.7)),
    "vertex": (([-45, -10, 40], [25, 10, 90]), (0, 0, 1)),
    "cranium_side": (([-55, 30, 10], [0, 70, 70]), (0, 1, 0.3)),
    "occiput": (([-115, -40, -20], [-60, 40, 70]), (-1, 0, 0.2)),
}


def outer_points(P, u, bins=2.0):
    u = np.asarray(u, float)
    u /= np.linalg.norm(u)
    a = np.cross(u, [0.3, 0.5, 0.8])
    a /= np.linalg.norm(a)
    b = np.cross(u, a)
    key = np.floor(P @ a / bins).astype(np.int64) * 100000 + np.floor(P @ b / bins).astype(np.int64)
    pr = P @ u
    order = np.lexsort((-pr, key))
    k2 = key[order]
    first = np.r_[True, k2[1:] != k2[:-1]]
    return P[order[first]]


def ct_tissue_depths():
    """Depth (character mm) of the CT skull's outer bone surface under the
    round-5 skin, per landmark region (the CT is kept for landmarks only).
    Negative values would be bone poking through the skin."""
    V, F, meta = v6.load_ct_skull()
    Vmm = V / MM
    out = {}
    for name, ((lo, hi), u) in CT_REGIONS.items():
        m = np.all((Vmm >= lo) & (Vmm <= hi), axis=1)
        if not m.any():
            continue
        Q = outer_points(Vmm[m], u)
        W = (Q * MM) @ v6.head_R().T
        dep = -exact_skin_sdf(W) / MM
        out[name] = dict(n=int(len(Q)), mean=round(float(dep.mean()), 1), p10=round(float(np.percentile(dep, 10)), 1),
                         p90=round(float(np.percentile(dep, 90)), 1), min=round(float(dep.min()), 1))
    return out


CT_TARGET_DEPTH = {"frontal": 4.5, "nasal": 3.5, "premaxilla": 6.0, "symphysis": 6.0, "mandible_ventral": 7.0, "zygomatic_arch": 7.0,
                   "postorbital": 6.0, "vertex": 9.0, "cranium_side": 9.0, "occiput": 10.0}


def ct_landmark_fit():
    """Landmark check of the CT under the scanned head: re-pose the CT about
    the orbit axis (pitch, uniform scale, small offset) so that its outer
    bone lies inside the round-5 skin at plausible soft-tissue depths
    (character mm; bone outside the skin is penalised hard). Coordinate
    descent from the round-4 pose. Returns the pose and per-region depths."""
    V, F, meta = v6.load_ct_skull()
    Vmm = V / MM
    rng = np.random.default_rng(1)
    regs = {}
    for name, ((lo, hi), u) in CT_REGIONS.items():
        m = np.all((Vmm >= lo) & (Vmm <= hi), axis=1)
        Q = outer_points(Vmm[m], u)
        if len(Q) > 250:
            Q = Q[rng.choice(len(Q), 250, replace=False)]
        regs[name] = Q
    axis_pt = (v6.eye_center(1.0) + v6.eye_center(-1.0)) / 2 / MM

    def depths(p):
        pitch, scale, dx, dz = p
        a = math.radians(pitch)
        Ry = np.array([[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]])
        out = {}
        for name, Q in regs.items():
            q = (Q - axis_pt) @ Ry.T * scale + axis_pt + np.array([dx, 0.0, dz])
            out[name] = -exact_skin_sdf((q * MM) @ v6.head_R().T) / MM
        return out

    def cost(p):
        dd = depths(p)
        return sum(np.mean((d - CT_TARGET_DEPTH[k]) ** 2) + 20.0 * np.mean(np.maximum(1.0 - d, 0.0) ** 2) for k, d in dd.items())

    p = np.array([0.0, 1.0, 0.0, 0.0])
    c0 = cost(p)
    steps = np.array([5.0, 0.05, 4.0, 4.0])
    best = c0
    for _ in range(6):
        improved = True
        while improved:
            improved = False
            for i in range(4):
                for sgn in (1.0, -1.0):
                    q = p.copy()
                    q[i] += sgn * steps[i]
                    cq = cost(q)
                    if cq < best:
                        best, p, improved = cq, q, True
        steps *= 0.5
    dd = depths(p)
    return dict(pose=dict(pitch_deg=round(float(p[0]), 2), scale=round(float(p[1]), 3), dx_mm=round(float(p[2]), 1), dz_mm=round(float(p[3]), 1)),
                cost_round4_pose=round(float(c0), 1), cost_fitted=round(float(best), 1),
                depth_mm={k: dict(mean=round(float(d.mean()), 1), p10=round(float(np.percentile(d, 10)), 1), min=round(float(d.min()), 1))
                          for k, d in dd.items()})


def stage_measure_v7(args):
    out = v6.stage_measure(args)
    out["ct_tissue_depth_mm"] = ct_tissue_depths()
    out["ct_landmark_fit"] = ct_landmark_fit()
    log("ct landmark fit", json.dumps(out["ct_landmark_fit"]))
    out["scan_to_world"] = SCAN_TO_WORLD
    d = np.load(CACHE / "scan_field.npz")
    out["scan_midsagittal_residual_mm"] = round(float(d["resid"]), 2)
    (CACHE / f"measure_round{args.round}.json").write_text(json.dumps(out, indent=2) + "\n")
    log("ct tissue depths", json.dumps(out["ct_tissue_depth_mm"]))
    return out


# ---------------------------------------------------------------------------
# Side-by-side comparison sheets (round 5)
# ---------------------------------------------------------------------------

REF_PHOTO = ROOT / "Local/ThirdPartyRaw/reference/wikimedia/profile__Cat__4938330260_.jpg"  # CC BY 2.0, tier REF (private)
HERO_REF = ROOT / "Content/SourceArt/Characters/Hero/Reference/Nyaakoto_PhotorealTurnaround_v2.png"
HERO_FACE_CROP = (40, 30, 300, 250)  # x0, y0, x1, y1 (pixels, top-left origin) of the front panel's face


def _img_load(path):
    im = bpy.data.images.load(str(path), check_existing=False)
    w, h = im.size
    px = np.empty(w * h * 4, np.float32)
    im.pixels.foreach_get(px)
    bpy.data.images.remove(im)
    return px.reshape(h, w, 4)[::-1, :, :3].copy()  # top-left origin


def _img_resize(a, w, h):
    H, W = a.shape[:2]
    ys = (np.arange(h) + 0.5) * H / h - 0.5
    xs = (np.arange(w) + 0.5) * W / w - 0.5
    y0 = np.clip(np.floor(ys).astype(int), 0, H - 2)
    x0 = np.clip(np.floor(xs).astype(int), 0, W - 2)
    fy = np.clip(ys - y0, 0, 1)[:, None, None]
    fx = np.clip(xs - x0, 0, 1)[None, :, None]
    a00, a01 = a[y0][:, x0], a[y0][:, x0 + 1]
    a10, a11 = a[y0 + 1][:, x0], a[y0 + 1][:, x0 + 1]
    return (a00 * (1 - fx) + a01 * fx) * (1 - fy) + (a10 * (1 - fx) + a11 * fx) * fy


def _img_save(a, path):
    h, w = a.shape[:2]
    im = bpy.data.images.new(Path(path).stem, w, h, alpha=False)
    px = np.ones((h, w, 4), np.float32)
    px[..., :3] = np.clip(a[::-1], 0, 1)
    im.pixels.foreach_set(px.ravel())
    im.filepath_raw = str(path)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)


def _side_by_side(images, height, gap=8):
    rs = [_img_resize(a, int(round(a.shape[1] * height / a.shape[0])), height) for a in images]
    W = sum(r.shape[1] for r in rs) + gap * (len(rs) - 1)
    out = np.full((height, W, 3), 0.02, np.float32)
    x = 0
    for r in rs:
        out[:, x:x + r.shape[1]] = r
        x += r.shape[1] + gap
    return out


def stage_compare(args):
    """Side-by-sides: (1) private A/B of the reference-matched frame with the
    CC BY 2.0 profile photograph (tier REF: never committed); (2) committed
    round 4 | round 5 pairs at the reference-photo framing and the Overcast
    cameras; (3) committed round-5 CloseFront beside the face of the Nyaakoto
    hero reference (repository art) for the markings check."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    r5 = OUT / "Renders" / f"round_{args.round}"
    r4 = OUT / "Renders" / "round_4"
    tag = f"R{args.round}"
    ref5 = r5 / f"CatBaseV6_{tag}_RefMatch_RefMatch_Profile.png"
    if REF_PHOTO.exists() and ref5.exists():
        ab = CACHE / f"ab_round{args.round}"
        ab.mkdir(parents=True, exist_ok=True)
        _img_save(_side_by_side([_img_load(ref5), _img_load(REF_PHOTO)], 1080), ab / "refmatch_profile_AB.png")
        log("private A/B", ab / "refmatch_profile_AB.png")
    ref4 = r4 / "CatBaseV6_R4_RefMatch_RefMatch_Profile.png"
    if ref4.exists() and ref5.exists():
        _img_save(_side_by_side([_img_load(ref4), _img_load(ref5)], 810), r5 / f"CatBaseV6_{tag}_AB_R4_RefMatch_Profile.png")
    rows = []
    for view in ("Front", "Profile", "ThreeQuarter", "CloseFront", "CloseThreeQuarter"):
        a, b = r4 / f"CatBaseV6_R4_Overcast_{view}.png", r5 / f"CatBaseV6_{tag}_Overcast_{view}.png"
        if a.exists() and b.exists():
            rows.append(_side_by_side([_img_load(a), _img_load(b)], 540))
    if rows:
        W = max(r.shape[1] for r in rows)
        sheet = np.full((sum(r.shape[0] for r in rows) + 8 * (len(rows) - 1), W, 3), 0.02, np.float32)
        y = 0
        for r in rows:
            sheet[y:y + r.shape[0], :r.shape[1]] = r
            y += r.shape[0] + 8
        _img_save(sheet, r5 / f"CatBaseV6_{tag}_AB_R4_Overcast.png")
    cf = r5 / f"CatBaseV6_{tag}_Overcast_CloseFront.png"
    if HERO_REF.exists() and cf.exists():
        x0, y0, x1, y1 = HERO_FACE_CROP
        hero = _img_load(HERO_REF)[y0:y1, x0:x1]
        mine = _img_load(cf)[:, 240:1680]  # centre crop of the 1920-wide frame
        _img_save(_side_by_side([hero, mine], 1080), r5 / f"CatBaseV6_{tag}_AB_NyaakotoReference_CloseFront.png")
    log("comparison sheets written to", r5)


def stage_manifest_v7(args):
    """Round-4 manifest (hashes of every committed output) plus the round-5
    generator, the scan adaptation record and the CT's reduced role."""
    v6.stage_manifest(args)
    man = json.loads((OUT / "manifest.json").read_text())
    src = json.loads((OUT / "sources_manifest.json").read_text())
    sc = next(x for x in src["scans"] if SCAN_UID in x["asset_id"])
    ct = next(x for x in src["scans"] if v6.CT_UID in x["asset_id"])
    man["generator"] = "scripts/art/create_cat_base_v7.py (imports scripts/art/create_cat_base_v6.py)"
    man["derived_from"]["skull"]["changes"] = ct["changes"]
    man["derived_from"]["scan_head"] = {
        "name": sc["name"], "origin_url": sc["origin_url"], "license": sc["license"], "license_url": sc["license_url"],
        "sha256": sc["sha256"], "storage": "Local/ThirdPartyRaw (private, decision D6)",
        "attribution_text": sc["attribution_text"], "changes": sc["changes"],
        "scan_to_world": SCAN_TO_WORLD, "scan_picks_scan_metres": SCAN_PICKS,
    }
    mp = CACHE / f"measure_round{args.round}.json"
    if mp.exists():
        mj = json.loads(mp.read_text())
        man["measure"] = {k: mj[k] for k in ("ct_landmark_fit", "scan_midsagittal_residual_mm") if k in mj}
    (OUT / "manifest.json").write_text(json.dumps(man, indent=2, ensure_ascii=False) + "\n")
    log("manifest (round 5 fields added)")


def install_build_overrides():
    """Swap the v6 build steps that round 5 replaces."""
    if getattr(v6, "_ROUND5_BUILD", False):
        return
    v6._ROUND5_BUILD = True
    v6.build_lid_margins = build_lid_margins_v7
    v6.build_inner_ear_furnishings = build_inner_ear_furnishings_v7
    v6.skin_material = skin_material_v7
    orig_build_eyes = v6.build_eyes

    def build_eyes_v7(coll, mats, parent):
        objs = orig_build_eyes(coll, mats, parent)
        keep = []
        for o in objs:
            if o.name.endswith("_Caruncle"):
                bpy.data.objects.remove(o, do_unlink=True)
            else:
                keep.append(o)
        bs = next(n for n in mats["caruncle"].node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        bs.inputs["Base Color"].default_value = (0.21, 0.085, 0.075, 1.0)  # moist pink-dark
        bs.inputs["Roughness"].default_value = 0.07
        bs.inputs["Coat Weight"].default_value = 0.6
        bs.inputs["Coat Roughness"].default_value = 0.03
        return keep + build_caruncles_v7(coll, parent, mats["caruncle"])

    v6.build_eyes = build_eyes_v7


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", type=int, default=5)
    ap.add_argument("--stages", default="scan,skin,preview")
    ap.add_argument("--voxel", type=float, default=0.75)
    ap.add_argument("--samples", type=int, default=256)
    ap.add_argument("--preview-dir", default=str(CACHE / "preview_r5"))
    ap.add_argument("--tex", type=int, default=4096)
    ap.add_argument("--guides", type=int, default=70000)
    ap.add_argument("--lights", default="Overcast")
    ap.add_argument("--views", default="")
    ap.add_argument("--render-dir", default="")
    ap.add_argument("--percent", type=int, default=100)
    ap.add_argument("--rescan", action="store_true")
    args = ap.parse_args(argv)
    CACHE.mkdir(parents=True, exist_ok=True)
    Path(args.preview_dir).mkdir(parents=True, exist_ok=True)
    apply_round5_overrides()
    stages = args.stages.split(",")
    if "scan" in stages:
        stage_scan(args)
    if "skin" in stages:
        stage_skin_v7(args)
    if "preview" in stages:
        v6.preview_dense(args)
    if "earpreview" in stages:
        preview_ears(args)
    if "eyepreview" in stages:
        preview_eyes(args)
    if "build" in stages:
        install_build_overrides()
        v6.stage_build(args)
    if "render" in stages:
        v6.stage_render(args)
    if "measure" in stages:
        stage_measure_v7(args)
    if "compare" in stages:
        stage_compare(args)
    if "manifest" in stages:
        stage_manifest_v7(args)


if __name__ == "__main__":
    main()
