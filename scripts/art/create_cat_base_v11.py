"""CatBaseV6 round 9 (generator v11): judged defects of round 8 (score 5/10).

Rounds 5-8 (create_cat_base_v7.py to v10.py) build the head and neck from a
real cat scan ("Cat sitting upright" by elaughli, CC BY 4.0, private raw
scan) with the CT skull for landmarks only. Round 8 was judged 5/10: the ear
now grows out of the skull, but the lane's own round-8 review still listed
clear CG tells at 1 m. Round 9 keeps the method and the scan field and
answers that list, most visible first:

1. eyes: a smaller, less round aperture (canthus to canthus 40 -> 37 mm,
   the upper lid 1.2 mm lower over the top of the iris), the globes 1.1 mm
   further back so the cornea no longer domes out like a marble, a paler,
   more luminous grey-blue iris with deeper stroma relief (more parallax
   under the cornea), a thinner limbal ring, and a tear film with a faint
   low-frequency irregularity and 0.015 roughness, so the reflected horizon
   is no longer a ruler-straight line across both eyes; the QuadriFlow cage
   is twice as dense (QUAD_TARGET_V11) so its eye openings follow the lower
   upper lid (at round 8's density they tore open ~2.5 mm above the lid
   margin and the globe showed as a crescent above it);
2. inner pinna: pale vellus over the whole inner face (it was bare pink skin
   above the lower third), stronger vessel and pigment variation, denser
   furnishings that stay in the ear (FURN_*_V11), and the dark back-coat
   wrap over the margins halved (it read as a thin black outline round each
   ear in front view);
3. neck and temples: the neck skin 4 mm fuller at the sides, and the waist
   between the temple and the cheek filled (a 2.8 mm outset at zygomatic
   level), so the front silhouette runs from the ear base out to the cheek
   without a bump;
4. coat: fuller cheek fur standing a little off the face, white cheeks that
   rise from the muzzle toward the medial canthi as in the Nyaakoto
   reference, and a silver agouti ground hair (pale root, long silver band,
   short black tip; AGOUTI_V11) over a pale undercoat (UNDER_V11): round 8's
   dark-rooted, long-tipped hair turned local differences in length and lay
   into 5-20 mm light/dark blotches (the "mottling"); a matte, softly
   pebbled nose leather (it glittered);
5. body toward the bipedal samurai: a biped shoulder girdle (a trapezius
   sloping into small deltoid caps) and slim arms hanging from it (upper
   arm, elbow and the top of the forearm) replace the quadruped forelimb
   columns, with a short coat flowing down the arm;
6. first-person viewmodel: a separate right forearm and paw (the shipped
   first-person arm is its own mesh, as in any FPS): an SDF-sculpted
   forearm, wrist, metacarpus, four toes and a dewclaw, low bare digital,
   metacarpal and carpal pads with a muted, leathery shader, a white paw on
   a tabby forearm with a fringe round the pads and interdigital tufts, and
   a first-person camera (70 deg horizontal viewmodel FOV) at eye height.

Each constant that a review pass inside round 9 changed says in its comment
what the first value did wrong.

Run from the repository root (Blender 5.2.2 LTS, background):

  blender -b --factory-startup --python scripts/art/create_cat_base_v11.py -- \\
      --stages skin,build,measure,render,compare,manifest --round 9 \\
      --samples 256 --views Front,Profile,ThreeQuarter,CloseFront,CloseThreeQuarter \\
      --lights Overcast,Studio,ThreePoint,Exterior,RefMatch

The first-person paw frame is rendered by `--stages fprender` (Overcast and
Exterior light). The `scan` stage of v7 is reused unchanged.
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
import create_cat_base_v10 as v10  # noqa: E402

v9 = v10.v9
v8 = v10.v8
v7 = v10.v7
v6 = v10.v6
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

ROUND = 9


# ---------------------------------------------------------------------------
# Eyes (round 9)
# ---------------------------------------------------------------------------

# round-8 review: "large, round and glassy next to Nyaakoto's hooded eyes".
# Canthus to canthus 40 -> 37 mm (the eye was ~0.19 of the head width in the
# close front frame, the Nyaakoto reference and the CC0 front photographs
# ~0.15); the upper arc 9.8 -> 8.6 mm so the upper lid covers the top of the
# iris; the lower arc 10.9 -> 10.2 mm.
FISSURE_W_V11 = 37.0
FISSURE_UP_V11 = 8.6
FISSURE_LO_V11 = 10.2
# round 8 moved the globes 2.5 mm forward so the cornea broke the profile;
# at 1 m that read as a marble set on the face. 1.4 mm keeps a domed profile.
EYE_FORWARD_V11 = 1.4


def iris_colour_v11(f, rho):
    """Round 9 iris (round-8 review: 'the iris still looks painted at 1 m';
    in the Overcast frames it read as dark slate glass). Nyaakoto's eyes are
    a pale grey-blue: a lighter stroma (about 2.3x round 8's albedo) whose fine
    pale fibres carry most of the contrast, a slightly aqua-green pupillary
    zone inside an irregular pale collarette, soft crypts, contraction
    furrows, a gradual darkening toward the root and a THIN dark limbal ring
    (round 8's ring was 17 % of the radius wide)."""
    base = np.array([0.185, 0.260, 0.330])
    light = np.array([0.46, 0.53, 0.57])
    fv = smoothstep(0.30, 0.86, f["fib"])[..., None]
    col = base * (1 - 0.55 * fv) + light * (0.55 * fv)
    col = col * (0.84 + 0.32 * f["mot"])[..., None]
    th = f["th"]
    lf2 = v9.pnoise_ring(th, rho)
    col = col * (0.90 + 0.20 * lf2)[..., None]
    pz = (1.0 - smoothstep(f["rc"] - 0.06, f["rc"] + 0.02, rho))[..., None]
    col = col * (1 - 0.45 * pz) + np.array([0.21, 0.27, 0.25]) * (0.45 * pz)
    col = col * (1 - 0.35 * f["coll"][..., None]) + np.array([0.42, 0.47, 0.48]) * (0.35 * f["coll"][..., None])
    cr = np.clip(0.55 * f["crypt"] + 0.30 * f["cr2"], 0, 1)[..., None]
    col = col * (1 - 0.55 * cr)
    col = col * (1.0 - 0.30 * f["furrow"])[..., None]
    col = col * (1.0 - 0.30 * smoothstep(0.62, 0.90, rho))[..., None]
    lb = (0.90 * smoothstep(0.90, 0.985, rho))[..., None]
    return col * (1 - lb) + np.array([0.012, 0.018, 0.028]) * lb


def iris_height_mm_v11(f, rho):
    """Deeper stroma relief than round 8 (0.07 -> 0.16 mm fibres, 0.20 -> 0.34
    mm crypts, a 0.24 mm collarette ridge) and a slightly more concave iris,
    so the refracted iris shifts with the view (parallax) instead of reading
    as a decal under the cornea."""
    return (-1.25 * (1.0 - rho ** 2) + 0.24 * f["coll"] + 0.16 * (f["fib"] - 0.5) - 0.34 * f["crypt"] - 0.14 * f["cr2"]
            - 0.09 * f["furrow"] + 0.06 * (f["mot"] - 0.5))


CORNEA_ROUGH_V11 = 0.015
TEAR_BUMP = dict(scale=85.0, detail=2.0, distance=0.00022)  # object m: ~12 mm features, 0.22 mm height


def cornea_material_v11():
    """Round-8 Fresnel-only cornea plus a tear film that is not a perfect
    mirror: a faint low-frequency height (~12 mm features, 0.22 mm) bends the
    reflected horizon a few degrees, and 0.015 roughness softens it (round-8
    review: 'a straight horizon reflection crosses both corneas')."""
    m = v10.cornea_material_v10()
    m.name = "M_CatBaseV6_CorneaV11"
    nt = m.node_tree
    tc = N(nt, "ShaderNodeTexCoord", (-700, -500))
    nz = N(nt, "ShaderNodeTexNoise", (-500, -500))
    nz.inputs["Scale"].default_value = TEAR_BUMP["scale"]
    nz.inputs["Detail"].default_value = TEAR_BUMP["detail"]
    L(nt, tc.outputs["Object"], nz.inputs["Vector"])
    bp = N(nt, "ShaderNodeBump", (-300, -500))
    bp.inputs["Strength"].default_value = 1.0
    bp.inputs["Distance"].default_value = TEAR_BUMP["distance"]
    L(nt, nz.outputs["Fac"], bp.inputs["Height"])
    for nd in list(nt.nodes):
        if nd.type in ("BSDF_GLOSSY", "BSDF_GLASS", "FRESNEL") and "Normal" in nd.inputs:
            L(nt, bp.outputs["Normal"], nd.inputs["Normal"])
        if nd.type == "BSDF_GLOSSY":
            nd.inputs["Roughness"].default_value = CORNEA_ROUGH_V11
    return m


# ---------------------------------------------------------------------------
# Skin stage: cheek fill, neck, bust (round 9)
# ---------------------------------------------------------------------------

# round-8 known issues: "a soft 2 mm bump at eye level remains in the front
# silhouette, with a 1.3 mm waist of the skin at head z = 0" and "the neck
# silhouette is 0.85 of the cheeks (target >= 0.9)". World-local mm.
CHEEK_FILL = dict(amp=2.8, z0=1.0, sz=9.5, x0=2.0, sx=32.0, y=(70.0, 92.0))
NECK_OUTSET_V11 = 5.0
NECK_Z_V11 = (-126.0, -92.0)  # world-local mm: below the jaw, where the scan fades into the bust
_V10_INSET = v10.fur_inset_mm_v10


def fur_inset_mm_v11(Pw_mm):
    """Round-8 insets with the zygomatic waist filled (the front silhouette
    now widens monotonically from the temple to the cheek) and the neck
    sides 5 mm fuller below the jaw."""
    t = _V10_INSET(Pw_mm)
    x, y, z = Pw_mm[..., 0], np.abs(Pw_mm[..., 1]), Pw_mm[..., 2]
    c = CHEEK_FILL
    cheek = np.exp(-((z - c["z0"]) / c["sz"]) ** 2 - ((x - c["x0"]) / c["sx"]) ** 2) * smoothstep(c["y"][0], c["y"][1], y)
    neck = _bump(z, NECK_Z_V11[0], NECK_Z_V11[1]) * smoothstep(30.0, 70.0, y) * (1.0 - smoothstep(70.0, 110.0, x))
    return t - c["amp"] * cheek - NECK_OUTSET_V11 * neck


# the biped shoulder girdle and arms (world-local mm, before BUST_DX/DZ):
# shoulder joint, elbow and the forearm top; hanging a little out and back.
# A first round-9 pass put the joint at (-24, 132, -206) with a 38 x 34 x 52
# mm deltoid cap and a 38 -> 30 mm upper arm: in the Front and ThreeQuarter
# frames that read as square padded shoulders and thick columns (a mascot
# suit). The joint is now 16 mm lower and 10 mm further in, so the
# trapezius slopes into a smaller cap, and the arm is slimmer.
SHOULDER_V11 = (-24.0, 122.0, -222.0)
ELBOW_V11 = (-40.0, 140.0, -480.0)
WRIST_DIR_V11 = (-18.0, 134.0, -660.0)
DELTOID_V11 = (33.0, 30.0, 46.0)  # mm radii of the deltoid cap
ARM_R_V11 = (33.0, 27.0, 27.0, 23.0)  # mm: upper arm at the shoulder / elbow, forearm at the elbow / cut


def build_bust_ops_v11():
    """Round 9 bust: the bipedal samurai's shoulders and arms. Round 8's
    quadruped forelimb columns (hanging straight down 90 mm from the midline)
    are replaced by a biped girdle: a trapezius sloping from the neck to the
    shoulder, a deltoid cap over a humeral head at ~124 mm, an upper arm
    hanging a little out and back to the elbow (~470 mm below the head
    origin), the olecranon, and the top of the forearm to the bust cut. The
    arms join the chest only at the armpit (small blend radius), so they stay
    free of the ribcage. A broad ribcage under the shoulders and a longer,
    narrower thorax (down to the bust cut) replace round 8's egg-shaped
    thorax; the neck base is fuller; keel and throat are kept."""
    R = v6.rot_matrix
    dx, dz = v9.BUST_DX, v9.BUST_DZ

    def p(x, y, z):
        return (x + dx, y, z + dz)

    ops = []
    sx, sy, sz = SHOULDER_V11
    ex_, ey, ez = ELBOW_V11
    wx, wy, wz = WRIST_DIR_V11
    for s in (1.0, -1.0):
        ops.append(v6.cap_op(p(-60.0, 24.0 * s, -104.0), p(-36.0, 100.0 * s, -190.0), 24.0, 30.0, 30, frame="body"))  # trapezius, sloping
        ops.append(v6.ell_op(p(-76.0, 50.0 * s, -186.0), (9.0, 28.0, 50.0), R(roll=-22.0 * s, pitch=-8.0), 30, frame="body"))  # scapular blade
        ops.append(v6.ell_op(p(sx - 2.0, (sy - 6.0) * s, sz + 6.0), DELTOID_V11, R(roll=-24.0 * s), 24, frame="body"))  # deltoid cap
        ops.append(v6.ell_op(p(sx, sy * s, sz), (27.0, 26.0, 27.0), None, 16, frame="body"))  # humeral head
        ops.append(v6.cap_op(p(sx, sy * s, sz - 6.0), p(ex_, ey * s, ez), ARM_R_V11[0], ARM_R_V11[1], 14, frame="body"))  # upper arm
        ops.append(v6.ell_op(p(ex_ - 8.0, ey * s, ez), (25.0, 23.0, 27.0), None, 10, frame="body"))  # elbow, olecranon
        ops.append(v6.cap_op(p(ex_, ey * s, ez - 8.0), p(wx, wy * s, wz), ARM_R_V11[2], ARM_R_V11[3], 10, frame="body"))  # forearm top
        ops.append(v6.ell_op(p(-10.0, (sy - 44.0) * s, -250.0), (34.0, 26.0, 60.0), R(roll=-8.0 * s), 24, frame="body"))  # biceps / chest side
        ops.append(v6.ell_op(p(24.0, 46.0 * s, -212.0), (30.0, 42.0, 44.0), R(yaw=18.0 * s, roll=-10.0 * s), 26, frame="body"))  # pectoral
    ops.append(v6.cap_op(p(-22.0, 0.0, -104.0), p(-38.0, 0.0, -190.0), 72.0, 86.0, 32, frame="body"))  # neck base (fuller)
    ops.append(v6.ell_op(p(54.0, 0.0, -172.0), (26.0, 24.0, 44.0), None, 26, frame="body"))  # keel
    ops.append(v6.ell_op((52.0, 0.0, -120.0), (32.0, 40.0, 38.0), None, 26, frame="body"))  # throat fill
    ops.append(v6.ell_op(p(-30.0, 0.0, -238.0), (90.0, 102.0, 118.0), None, 36, frame="body"))  # ribcage: broad under the shoulders
    ops.append(v6.ell_op(p(-34.0, 0.0, -330.0), (90.0, 84.0, 290.0), None, 44, frame="body"))  # thorax and waist, down to the bust cut
    return ops


def build_bust_field_v11(vs=2.0 * MM):
    t0 = time.time()
    lo = np.floor(v6.DOMAIN_MIN / vs).astype(int) - 4
    hi = np.ceil(v6.DOMAIN_MAX / vs).astype(int) + 4
    shape = tuple(hi - lo + 1)
    xs = [np.arange(lo[a], hi[a] + 1) * vs for a in range(3)]
    ops = build_bust_ops_v11()
    Bf = np.empty(shape, np.float32)
    for a in range(shape[0]):
        J, K = np.meshgrid(xs[1], xs[2], indexing="ij")
        P = np.stack([np.full_like(J, xs[0][a]), J, K], -1).reshape(-1, 3)
        f = np.full(len(P), 0.2)
        f = v6.apply_ops(ops, P, f)
        f = v6.smax(f, -(P[:, 2] + 0.600), 12 * MM)
        Bf[a] = f.reshape(J.shape)
    Bb = v6.gaussian_blur3(Bf, 4)
    log(f"bust field v11 {shape} ({time.time()-t0:.0f}s)")
    return Bb, lo * vs


# ---------------------------------------------------------------------------
# Coat and flow (round 9)
# ---------------------------------------------------------------------------

# fuller cheek fur (round-8 review: 'Nyaakoto's cheeks fuller and whiter
# below the eyes'), a little less on the temple behind the eye (where the
# silhouette bump sat)
_LEN_V11 = {(80, 62, 5): 4.6, (50, 82, 5): 7.2, (24, 86, -18): 8.8, (4, 80, -44): 9.2, (32, 72, -42): 8.0,
            (-40, 55, 50): 5.2, (-70, 60, 10): 7.0}
HEAD_LENGTH_KEYS_V11 = [(c, _LEN_V11.get(tuple(c), Lk), sig) for (c, Lk, sig) in v10.HEAD_LENGTH_KEYS_V10]
# white cheeks (head frame mm): from the muzzle up the side of the nose to a
# few mm under the medial canthus, as in the Nyaakoto reference
CHEEK_WHITE = dict(c=(118.0, 0.0, -14.0), r=(44.0, 56.0, 26.0))
ARM_COAT_SHORTEN_V11 = 0.50
_V10_COAT = v10.coat_fields_v10
_V10_FURDIR = v10.fur_direction_v10
_V10_HAIR = v10.hair_material_v10


def coat_fields_v11(Pw, Nw, ex=None):
    """Round-8 fields with the round-9 changes:

    - white cheeks rising from the muzzle toward the medial canthi;
    - cheek fur standing ~5 deg further off the face (fuller cheeks);
    - inner pinna: pale vellus over the whole inner face (density 0.42-0.72,
      2.6-4.2 mm; round 8: 0.14-0.50 and 1.8-3.8 mm, bare above the lower
      third), and the dark back coat wrapping over the margins halved;
    - arms and deltoid caps: a shorter coat (0.5x the body coat) that lies
      closer."""
    f = _V10_COAT(Pw, Nw, ex)
    Pw = np.asarray(Pw, float)
    Nw = np.asarray(Nw, float)
    n = len(Pw)
    is_ear, ear_t, ear_u, ear_face = v6.ex_arrays(n, ex)
    earm = is_ear > 0.5
    inner = earm & (ear_face > 0.2)
    au = np.abs(ear_u)
    Ph = Pw @ v6.head_R()
    x, y, z = Ph[:, 0] / MM, Ph[:, 1] / MM, Ph[:, 2] / MM
    ay = np.abs(y)
    zw = Pw[:, 2] / MM
    ayw = np.abs(Pw[:, 1] / MM)
    # white cheeks
    c, r = CHEEK_WHITE["c"], CHEEK_WHITE["r"]
    e = np.sqrt(((x - c[0]) / r[0]) ** 2 + ((ay - c[1]) / r[1]) ** 2 + ((z - c[2]) / r[2]) ** 2)
    jit_w = (v6.fbm(Pw, 0.0011, 2, 11.0) - 0.5) * 1.3 + (v6.fbm(Pw, 0.022, 2, 12.0) - 0.5) * 3.2
    lob = (v6.fbm(Pw, 0.030, 3, 21.0) - 0.5) * 8.0
    cw = (1.0 - smoothstep(-0.35, 0.35, (e - 1.0) * 26.0 + jit_w + lob)) * (~earm) * (f["d_fis"] > 3.0)
    white = np.maximum(f["white"], cw)
    stripe = f["stripe"] * (1.0 - cw)
    # inner pinna vellus and a lighter margin wrap
    lower = 1.0 - smoothstep(0.30, 0.55, ear_t)
    rimz = smoothstep(0.86, 0.98, au)
    d_in = (0.42 + 0.30 * lower) * (1.0 - rimz) + 0.85 * rimz
    L_in = ((2.6 + 1.6 * lower) * (1.0 - rimz) + 3.0 * rimz) * MM
    density = np.where(inner, d_in, f["density"])
    length = np.where(inner, L_in, f["length"])
    stripe = np.where(inner, 0.5 * stripe, stripe)
    # cheek fur stands a little off the face
    cheek = smoothstep(58.0, 82.0, ay) * _bump(z, -48.0, 12.0) * _bump(x, -12.0, 70.0) * (~earm) * f["w_head"]
    lift = f["lift"] + 5.0 * cheek
    # arms and the deltoid caps: a shorter, closer-lying coat (0.5x the body
    # coat; a first pass at 0.75x from below the cap read as knitwear on the
    # arms and fur balls on the shoulders)
    arm = smoothstep(98.0, 118.0, ayw) * smoothstep(-165.0, -215.0, zw) * (~earm)
    length = length * (1.0 - ARM_COAT_SHORTEN_V11 * arm)
    lift = lift * (1.0 - 0.50 * arm)
    f.update(white=np.clip(white, 0, 1), stripe=np.clip(stripe, 0, 1), density=np.clip(density, 0, 1), length=length, lift=lift)
    return f


def fur_direction_v11(Pw, Nw, ex=None):
    """Round-8 flow plus the arms: the coat runs down the arm toward the paw
    (a little backward over the upper arm), blended in over ~25 mm from the
    shoulder."""
    Pw = np.asarray(Pw, float)
    Nw = np.asarray(Nw, float)
    t = _V10_FURDIR(Pw, Nw, ex)
    n = len(Pw)
    is_ear = v6.ex_arrays(n, ex)[0]
    zw = Pw[:, 2] / MM
    ayw = np.abs(Pw[:, 1] / MM)
    aw = (smoothstep(96.0, 118.0, ayw) * smoothstep(-195.0, -240.0, zw) * (is_ear < 0.5))[:, None]
    if aw.any():
        db = np.array([-0.18, 0.0, -1.0])
        db = db / np.linalg.norm(db)
        t = t * (1.0 - 0.85 * aw) + db[None, :] * 0.85 * aw
        t = t - np.sum(t * Nw, 1, keepdims=True) * Nw
        t /= np.linalg.norm(t, axis=1, keepdims=True) + 1e-9
    return t


# Silver agouti ground hair (fraction along the hair from the root): a pale
# silver root, a long pale band and a short black tip. Round 8's hair was
# dark from the root to 0.26 and black from 0.64, so how much of each hair
# showed (set by the local length, lay and clumping) switched the coat
# between pale and dark in 5-20 mm blotches (the "mottling"); a constant-
# grey hair render of the same groom (review aid) shows no such blotches, so
# they came from the colour, not the lighting. In a silver tabby the root and
# the undercoat are pale; only the tip is black.
AGOUTI_V11 = [(0.0, (0.17, 0.170, 0.174)), (0.20, (0.29, 0.288, 0.283)), (0.30, (0.41, 0.405, 0.390)),
              (0.68, (0.43, 0.424, 0.408)), (0.78, (0.040, 0.040, 0.042)), (1.0, (0.022, 0.022, 0.023))]
UNDER_V11 = ([(0.0, (0.17, 0.170, 0.170)), (1.0, (0.29, 0.286, 0.278))],
             [(0.0, (0.29, 0.286, 0.278)), (1.0, (0.40, 0.395, 0.382))])


def _set_ramp(r, st):
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


def hair_material_v11(name, images, under=False, tip_alpha=True):
    """Round-8 hair with a silver agouti ground (round-8 review: 'large-scale
    light/dark mottling'): every ground hair is pale from the root through a
    long silver band to a short black tip (AGOUTI_V11), and the undercoat is
    pale silver (UNDER_V11; round 8: dark slate), so the visible colour no
    longer depends on how much of each hair shows. Stripe hairs stay solid
    near-black and white hairs white."""
    m = _V10_HAIR(name, images, under, tip_alpha)
    ramps = [nd for nd in m.node_tree.nodes if nd.type == "VALTORGB"]
    ramps.sort(key=lambda nd: -nd.location.y)
    if under:
        _set_ramp(ramps[0], UNDER_V11[0])
        _set_ramp(ramps[1], UNDER_V11[1])
        return m
    _set_ramp(ramps[0], AGOUTI_V11)
    return m


# ---------------------------------------------------------------------------
# Inner-ear furnishings (round 9)
# ---------------------------------------------------------------------------

FURN_TUFTS_V11 = 2200
FURN_MEDIAL_V11 = (0.80, 0.40, 0.42)  # up, lateral (across the opening), forward
FURN_MEDIAL_LEN_V11 = (16.0, 28.0)  # mm
FURN_FLOOR_LEN_V11 = (14.0, 24.0)  # mm


def build_inner_ear_furnishings_v11(coll, skin, images):
    """Round-8 furnishings, denser (round-8 review: 'the near ear's
    furnishings are sparse in the close three-quarter'): 2,200 tufts (round
    8: 1,650), a wider medial band up to 55 % of the height and a sparse
    scatter of 6-12 mm hairs over the upper inner face, all streaming up and
    out past the opening with clumped tips. A first round-9 pass also made
    them longer (medial margin 24-38 mm, conchal floor 18-32 mm, 2,600
    tufts); in the close three-quarter they then carpeted the inner face and
    spilled as long white wisps over the crown, so the medial-margin tufts
    are 16-28 mm (round 8: 18-30) and rise more steeply (FURN_MEDIAL_V11),
    and the floor and lower face tufts are 14-24 mm (round 8: 16-28)."""
    rng = np.random.default_rng(v6.RNG_SEED + 13)
    S = v6.evaluated_surface(skin)

    def wfn(c, n, ex):
        cp = v10.cup_weight_v10(c) * (1.0 - ex["is_ear"])
        front = ex["is_ear"] * smoothstep(0.2, 0.6, ex["ear_face"])
        t, u = ex["ear_t"], ex["ear_u"]
        low = (1.0 - smoothstep(0.30, 0.45, t)) * smoothstep(-0.12, 0.0, t)
        med = (1.0 - smoothstep(-0.78, -0.45, u)) * _bump(t, 0.0, 0.55)
        lat = smoothstep(0.45, 0.65, u) * (1.0 - smoothstep(0.90, 0.99, u)) * _bump(t, -0.02, 0.20)
        upper = _bump(t, 0.40, 0.85) * (1.0 - smoothstep(0.80, 0.95, np.abs(u)))
        tipz = smoothstep(0.88, 0.96, t)
        return front * (3.0 * low + 2.0 * med + 1.8 * lat + 0.55 * upper + 0.35 * tipz + 0.25) + 3.2 * cp

    cpos, cnrm, cuv, cex = v6.sample_roots(S, FURN_TUFTS_V11, wfn, rng)
    npts = 12
    strands, uvs, radii = [], [], []
    tt = np.linspace(0, 1, npts)
    for i in range(FURN_TUFTS_V11):
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
            Lt = rng.uniform(14.0, 24.0) * MM
            k = int(rng.integers(3, 7))
        elif on_ear and eu < -0.45:
            d = FURN_MEDIAL_V11[0] * up + FURN_MEDIAL_V11[1] * lat + FURN_MEDIAL_V11[2] * fwd + 0.25 * nn
            Lt = rng.uniform(*FURN_MEDIAL_LEN_V11) * MM
            k = int(rng.integers(3, 8))
        elif on_ear and et > 0.40:
            # sparse fine hairs over the upper inner face, lying up the pinna
            d = 0.90 * up + 0.25 * fwd + 0.30 * nn
            Lt = rng.uniform(6.0, 12.0) * MM
            k = int(rng.integers(1, 3))
        else:
            # conchal floor and lower inner face: up and out of the opening
            d = 0.70 * up + 0.70 * fwd + 0.20 * lat * rng.normal() + 0.20 * nn
            Lt = rng.uniform(*FURN_FLOOR_LEN_V11) * MM
            k = int(rng.integers(4, 9))
        d /= np.linalg.norm(d) + 1e-9
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
            if tipp is None:
                tipp = pts[-1].copy()
            pts = pts + (tipp - pts[-1])[None, :] * (0.35 * tt ** 2)[:, None]
            strands.append(pts)
            uvs.append(cuv[i])
            radii.append((0.052 * MM) * (1 - tt) ** 1.0 + 0.006 * MM)
    strands = np.array(strands)
    ob = v6.make_curves("CatBaseV6_Fur_EarFurnishings", strands, 0, 0, coll, uv=np.array(uvs), surface=skin, radii=np.array(radii))
    ob.parent = skin
    ob.data.materials.append(furnishing_material_v11())
    log(f"ear furnishings v11: {FURN_TUFTS_V11} tufts, {len(strands)} hairs")
    return ob


def furnishing_material_v11():
    """The round-8 furnishing hair (pale, Chiang, tips fading out)."""
    m, nt = v6.new_mat("M_CatBaseV6_EarFurnishingV11")
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
    col.inputs[0].default_value = v10.FURN_COLOUR
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
    return m


# ---------------------------------------------------------------------------
# Skin material and cage (round 9)
# ---------------------------------------------------------------------------

EAR_VEIN_V11 = 0.24  # vessel strength in reflected light (round 8: 0.10, read as uniform pink skin)
# nose leather: round 8's 0.55 mm bump on 0.8 mm cobbles at roughness 0.40-0.45
# lit every cobble as its own highlight (a glittering pink eraser at 1 m); a
# 0.34 mm bump at roughness 0.47-0.52 keeps the pebbling as soft leather
LEATHER_BUMP_V11 = 0.00034
LEATHER_ROUGH_V11 = 0.52


def skin_material_v11(images):
    """Round-8 skin with the inner-pinna vessels 2.4x stronger in reflected
    light (round-8 review: 'the upper two thirds of the inner pinna is
    smooth, uniform pink skin') and a matte, softly pebbled nose leather
    (LEATHER_BUMP_V11, LEATHER_ROUGH_V11)."""
    v9.EAR_VEIN_BASE = EAR_VEIN_V11
    v9.LEATHER_ROUGH = LEATHER_ROUGH_V11
    m = v10.skin_material_v10(images)
    for nd in m.node_tree.nodes:
        if nd.type == "BUMP":
            nd.inputs["Distance"].default_value = LEATHER_BUMP_V11
    return m


# QuadriFlow cage target (round 8: 64,000). At 64-84k faces (~2 mm quads on
# the head) the cage cannot follow the thin upper lid that overhangs the
# globe: its eye opening came out ragged and up to ~2.5 mm larger than the
# sculpt target's, and with round 9's lower upper lid the lid margin sheet
# (2.4 mm wide) no longer covered the difference, so the globe showed as a
# crescent between the margin and a second dark arc above it. At 160k
# (~173k faces) the cage opening matches the target almond to within a
# small notch that the margin sheet covers (Workbench review of the cage
# against the target from the CloseFront camera).
QUAD_TARGET_V11 = 160000


def build_skin_base_v11(coll):
    """v6.build_skin with a larger QuadriFlow target (QUAD_TARGET_V11: the
    eye openings, and the biped arms add ~25 % surface), otherwise identical: decimated sculpt target, a
    symmetric quad cage welded on the midline, the parametric pinnae joined
    as their own islands, UVs, subdivision and the shrinkwrap onto the
    target."""
    d = np.load(CACHE / "skin_dense.npz")
    dense_me = v6.mesh_from_arrays("CatBaseV6_SculptSource", d["pts"], d["quads"])
    v6.clean_manifold(dense_me)
    dense = v6.link(bpy.data.objects.new("CatBaseV6_SculptSource", dense_me), coll)
    dense.location = v6.HEAD_ORIGIN
    cage = None
    for ratio in (0.16, 0.12, 0.2, 0.1):
        if cage is not None:
            bpy.data.objects.remove(cage, do_unlink=True)
        if "CatBaseV6_SculptTarget" in bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects["CatBaseV6_SculptTarget"], do_unlink=True)
        tgt = v6.link(bpy.data.objects.new("CatBaseV6_SculptTarget", dense_me.copy()), coll)
        tgt.location = v6.HEAD_ORIGIN
        v6.set_active(tgt)
        m = tgt.modifiers.new("dec", "DECIMATE")
        m.ratio = ratio
        bpy.ops.object.modifier_apply(modifier="dec")
        v6.sanitize_for_quadriflow(tgt.data)
        tgt.data.name = "CatBaseV6_SculptTarget"
        cage = v6.link(bpy.data.objects.new("CatBaseV6_Skin", tgt.data.copy()), coll)
        cage.location = v6.HEAD_ORIGIN
        cage.data.name = "CatBaseV6_SkinCage"
        v6.set_active(cage)
        cage.data.use_mirror_y = True
        cage.data.transform(Matrix.Scale(100.0, 4))
        ok = v6.quadriflow_ready(cage.data)
        r = bpy.ops.object.quadriflow_remesh(use_mesh_symmetry=True, use_preserve_sharp=False, use_preserve_boundary=False,
                                             preserve_attributes=False, smooth_normals=False, mode="FACES",
                                             target_faces=QUAD_TARGET_V11, seed=3)
        cage.data.transform(Matrix.Scale(0.01, 4))
        log("quadriflow", ratio, "precheck", ok, r, len(cage.data.polygons), "faces")
        if "FINISHED" in r:
            break
    else:
        raise RuntimeError("QuadriFlow could not remesh the sculpt target")
    v6.weld_midline(cage.data)
    n_head = len(cage.data.vertices)
    for k in v6.EAR_ATTRS:
        cage.data.attributes.new(k, "FLOAT", "POINT")
    ears = []
    for s in (1.0, -1.0):
        me = v6.ear_mesh(s)
        ob = v6.link(bpy.data.objects.new(me.name, me), coll)
        ob.location = v6.HEAD_ORIGIN
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
    co, nr = v6.mesh_arrays(cage.data)
    ex = {k: v6.attr_array(cage.data, k) for k in v6.EAR_ATTRS}
    fields = v6.coat_fields(co, nr, ex)
    a = cage.data.attributes.new("fur_density", "FLOAT", "POINT")
    a.data.foreach_set("value", fields["density"].astype(np.float32))
    return dense, tgt, cage


# ---------------------------------------------------------------------------
# First-person viewmodel: the right forearm and paw (round 9)
# ---------------------------------------------------------------------------
#
# Paw frame (mm): origin at the wrist, +x distal (toward the toes), +y medial
# (the dewclaw side of the RIGHT paw), +z dorsal. Character scale (2.2x a
# real cat's front paw: ~33 mm wide, ~45 mm wrist to toe tip; digital pads
# ~7-8 mm, the metacarpal pad ~15-18 mm wide, forearm ~100 mm), with the
# forearm lengthened toward the biped's (~260 mm).

SOCK_V11 = (-34.0, -30.0)  # mm: the white edge dorsally, and how much further up it runs palmarly
PAW_DIGITS = [  # (y medial+, toe-tip x) for digits 2 (medial) .. 5 (lateral)
    (24.0, 64.0), (8.3, 71.0), (-8.3, 71.0), (-24.0, 63.5)]
PAW_BOX = (np.array([-282.0, -50.0, -30.0]), np.array([98.0, 52.0, 36.0]))  # mm
PAW_VOXEL = 0.45  # mm
PAW_DECIMATE = 0.5
PAW_TEX = 2048
PAW_GUIDES = 14000
VM_ORIGIN = Vector((0.0, 0.0, 0.0))  # the viewmodel lives in its own .blend (CatBaseV6_ViewmodelPaw.blend)
PAW_BLEND = "CatBaseV6_ViewmodelPaw.blend"
FP = dict(eye_h=1.555, pitch=-14.0, fov_h=70.0, fstop=8.0)  # f/5.6 left the toe beans soft 40 mm behind the focus
# the right paw in the camera frame (m): wrist position (right, up, forward),
# forearm direction (elbow -> wrist) and the supination about it (deg; 0 =
# palm down, 180 = palm up). A first pose (wrist 0.225 m ahead, the forearm
# entering from the right edge, 105 deg) left the paw small and low in the
# frame; the forearm now rises from the lower-right corner.
FP_POSE = dict(wrist=(0.035, -0.030, 0.190), axis=(-0.32, 0.55, 1.0), supination=112.0)


def _sdE(P, c, r, R=None):
    return v6.sd_ellipsoid(P, np.asarray(c, float), np.asarray(r, float), R)


def paw_parts(P):
    """Signed distances (mm) of the paw's body (forearm to toes, no pads) and
    of its pads, at paw-frame points P (mm, (..., 3)). A cat's toes are short
    and bunched: each is a rounded lobe ~11 mm beyond the metacarpus, with
    shallow clefts between them (not separate fingers)."""
    sm = v6.smin
    R = v6.rot_matrix
    Pf = P * np.array([1.0, 1.0, 1.0 / 0.90])  # the forearm is a little flattened dorsopalmarly
    body = v6.sd_capsule(Pf, (-282.0, 0.0, 3.0), (-34.0, 0.0, 0.0), 30.0, 21.5) * 0.95
    body = sm(body, _sdE(P, (-205.0, -3.0, 9.0), (78.0, 26.0, 24.0)), 9.0)  # extensor bellies
    body = sm(body, _sdE(P, (-190.0, 3.0, -9.0), (72.0, 24.0, 22.0)), 9.0)  # flexor bellies
    body = sm(body, _sdE(P, (-14.0, 0.0, -1.0), (25.0, 24.5, 18.5)), 7.0)  # wrist (carpus)
    body = sm(body, _sdE(P, (18.0, 0.0, 1.0), (31.0, 34.0, 15.5)), 7.0)  # metacarpus
    toes = np.full(P.shape[:-1], 1e3)
    for y, tip in PAW_DIGITS:
        ph = _sdE(P, (tip - 26.0, y * 0.92, 2.5), (12.0, 9.8, 10.5))  # proximal phalanx
        toe = _sdE(P, (tip - 11.0, y, 1.0), (11.5, 9.9, 10.2), R(pitch=12.0))  # the toe (middle + distal)
        toes = np.minimum(toes, sm(ph, toe, 4.0))
    body = sm(body, toes, 6.0)
    # dewclaw (digit 1): a short toe high on the medial side, tucked against the carpus
    body = sm(body, _sdE(P, (-12.0, 23.5, -7.0), (8.5, 6.2, 6.4), R(yaw=20.0, pitch=25.0)), 3.5)
    # pads (PAD_DROP_V11: a first round-9 pass let every pad stand 4-4.5 mm
    # proud of the toe with a sharp crease, so in the first-person frame the
    # toe beans read as pink balls stuck on; they now rise ~2.5 mm and blend
    # into the toe with a wider fillet, PAD_BLEND_V11)
    dz = PAD_DROP_V11
    pads = np.full(P.shape[:-1], 1e3)
    for y, tip in PAW_DIGITS:
        pads = np.minimum(pads, _sdE(P, (tip - 11.0, y, -8.3 + dz), (9.4, 8.1, 4.4)))
    # metacarpal pad: a rounded distal edge and three lobes on its proximal edge
    meta = _sdE(P, (21.0, 0.0, -12.7 + dz), (11.5, 17.0, 5.2))
    meta = sm(meta, _sdE(P, (10.5, 0.0, -13.2 + dz), (8.8, 8.6, 5.4)), 2.2)
    for s in (1.0, -1.0):
        meta = sm(meta, _sdE(P, (12.5, 11.2 * s, -12.8 + dz), (8.6, 8.0, 5.1)), 2.2)
    pads = np.minimum(pads, meta)
    pads = np.minimum(pads, _sdE(P, (-31.0, -3.0, -18.2), (5.0, 4.6, 3.0)))  # carpal pad
    pads = np.minimum(pads, _sdE(P, (-10.0, 26.5, -11.6), (3.6, 3.3, 2.6)))  # dewclaw pad
    return body, pads


PAD_DROP_V11 = 0.8  # mm: every palmar pad raised toward the toe (less proud)
PAD_BLEND_V11 = 1.8  # mm smooth-min radius between the pads and the paw (was 1.1)


def paw_sdf_mm(P):
    body, pads = paw_parts(P)
    return v6.smin(body, pads, PAD_BLEND_V11)


def build_paw_levelset():
    """Level set of the paw SDF at PAW_VOXEL (dense slabs -> OpenVDB), meshed
    to quads; returns the largest component (m, paw frame)."""
    import openvdb as vdb
    t0 = time.time()
    vs = PAW_VOXEL
    lo = np.floor(PAW_BOX[0] / vs).astype(int)
    hi = np.ceil(PAW_BOX[1] / vs).astype(int)
    shape = hi - lo + 1
    bw = 3.0 * vs
    grid = vdb.FloatGrid(bw)
    grid.transform = vdb.createLinearTransform(voxelSize=vs * MM)
    ys = (np.arange(lo[1], hi[1] + 1)) * vs
    zs = (np.arange(lo[2], hi[2] + 1)) * vs
    J, K = np.meshgrid(ys, zs, indexing="ij")
    T = 24
    for i0 in range(0, shape[0], T):
        xs = (np.arange(lo[0] + i0, min(lo[0] + i0 + T, hi[0] + 1))) * vs
        P = np.stack(np.broadcast_arrays(xs[:, None, None], J[None], K[None]), -1)
        f = paw_sdf_mm(P).astype(np.float32)
        grid.copyFromArray(np.clip(f, -bw, bw), ijk=(int(lo[0] + i0), int(lo[1]), int(lo[2])), tolerance=0.0)
    grid.gridClass = vdb.GridClass.LEVEL_SET
    grid.signedFloodFill()
    pts, quads = grid.convertToQuads(0.0)
    pts, quads = v6.keep_largest_component(pts.astype(np.float64), quads.astype(np.int64))
    log(f"paw level set {tuple(shape)} voxels at {vs} mm: {len(quads)} quads ({time.time()-t0:.0f}s)")
    return pts, quads[:, ::-1]


def paw_fields(Pm, Nn):
    """Paw coat, region and groom fields at paw-frame points (m) and normals.

    - pads: bare, where the surface lies on a pad bulge outside the body;
    - white sock (SOCK_V11): the paw white to the wrist dorsally and to
      ~30 mm above the carpal pad on the palmar side, with a ragged edge (a
      first round-9 pass ran the palmar white 106 mm up the forearm, so the
      first-person frame showed an all-white arm, not Nyaakoto's white paws
      on tabby forearms);
    - tabby bars across the forearm from just above the sock, strongest on
      the dorsal and lateral sides;
    - coat length: 14 mm at the elbow -> 9 mm at the wrist, 6 mm over the
      paw, 4 mm on the toes, a 6-7 mm fringe round the pads."""
    P = np.asarray(Pm, float) / MM
    Nn = np.asarray(Nn, float)
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    body, pads = paw_parts(P)
    pad = smoothstep(0.15, 1.1, body) * (1.0 - smoothstep(0.05, 0.7, pads))
    pad_near = 1.0 - smoothstep(0.0, 5.0, np.maximum(pads, 0.0))
    fb = v6.fbm(Pm, 0.030, 3, 71.0) - 0.5
    fb2 = v6.fbm(Pm, 0.008, 2, 73.0) - 0.5
    dors = np.clip(Nn[:, 2], -1.0, 1.0)
    xb = SOCK_V11[0] + SOCK_V11[1] * smoothstep(0.1, -0.6, dors) + 12.0 * fb + 4.0 * fb2
    white = 1.0 - smoothstep(-2.5, 2.5, xb - x)
    white = np.where(x > -20.0, 1.0, white)
    ang = np.arctan2(y, z)
    ph = np.mod(x + 9.0 * np.sin(ang + 0.5) + 14.0 * fb + 60.0, 44.0) - 22.0
    band = np.abs(ph) - (7.5 + 2.0 * fb2)
    side = smoothstep(-0.7, 0.3, 0.75 * dors - 0.45 * np.clip(Nn[:, 1], -1, 1))
    stripe = (1.0 - smoothstep(-0.8, 0.8, band)) * side * (1.0 - smoothstep(-58.0, -44.0, x))
    stripe = stripe * (1.0 - white)
    # lengths (mm)
    Lf = np.interp(x, [-282.0, -40.0], [14.0, 9.0])
    Lp = np.interp(x, [-40.0, 0.0, 40.0], [9.0, 6.5, 5.5])
    toe = np.zeros(len(P))
    for yy, tip in PAW_DIGITS:
        toe = np.maximum(toe, smoothstep(tip - 34.0, tip - 20.0, x) * (1.0 - smoothstep(6.0, 11.0, np.abs(y - yy))))
    Lp = Lp * (1.0 - 0.35 * toe)
    L = np.where(x < -40.0, Lf, Lp)
    fringe = pad_near * (1.0 - pad) * (dors < 0.2)
    L = L * (1.0 - fringe) + 6.5 * fringe
    lift = 9.0 * (x < -40.0) + 6.0 * (x >= -40.0) - 2.0 * toe + 10.0 * fringe
    density = np.clip(6.0 / np.maximum(L, 1.0), 0.45, 1.0) * (1.0 - pad)
    excl = 1.0 - smoothstep(0.2, 0.8, pad)
    pig = np.clip(0.55 * smoothstep(0.62, 0.80, v6.fbm(Pm, 0.004, 2, 79.0)) * pad, 0, 1)
    return dict(white=np.clip(white, 0, 1), stripe=np.clip(stripe, 0, 1), pale=np.zeros(len(P)), pad=np.clip(pad, 0, 1),
                pig=pig, length=L * MM, lift=lift, density=np.clip(density, 0, 1), excl=np.clip(excl, 0, 1),
                fringe=fringe, toe=toe, pads_sd=pads)


def paw_direction(Pm, Nn):
    """Flow: distal along the limb, toward each toe tip over the toes, and
    radially away from the pads on the palm (so the fringe lies over the pad
    edges)."""
    P = np.asarray(Pm, float) / MM
    Nn = np.asarray(Nn, float)
    x, y = P[:, 0], P[:, 1]
    t = np.tile(np.array([1.0, 0.0, -0.08]), (len(P), 1))
    for yy, tip in PAW_DIGITS:
        w = (smoothstep(tip - 36.0, tip - 22.0, x) * (1.0 - smoothstep(6.0, 12.0, np.abs(y - yy))))[:, None]
        tgt = np.array([tip + 6.0, yy, -6.0])
        dv = tgt[None, :] - P
        dv /= np.linalg.norm(dv, axis=1, keepdims=True) + 1e-9
        t = t * (1.0 - w) + dv * w
    palm = (smoothstep(0.1, -0.4, Nn[:, 2]) * (x > -45.0))[:, None]
    ctr = np.array([30.0, 0.0, -14.0])
    rad = P - ctr[None, :]
    rad[:, 2] = 0.0
    rad /= np.linalg.norm(rad, axis=1, keepdims=True) + 1e-9
    t = t * (1.0 - 0.7 * palm) + rad * 0.7 * palm
    t = t - np.sum(t * Nn, 1, keepdims=True) * Nn
    t /= np.linalg.norm(t, axis=1, keepdims=True) + 1e-9
    return t


def grow_paw_guides(pos, nrm, npts, rng, g_local, length_scale=None, lift_add=None, lay=0.8):
    f = paw_fields(pos, nrm)
    tdir = paw_direction(pos, nrm)
    n = len(pos)
    Lg = f["length"] * rng.uniform(0.9, 1.1, n)
    if length_scale is not None:
        Lg = Lg * length_scale
    a0 = np.radians(f["lift"] + (0.0 if lift_add is None else lift_add))
    side = np.cross(nrm, tdir)
    gt = g_local[None] - (nrm @ g_local)[:, None] * nrm
    droop = np.clip((Lg / MM - 8.0) / 30.0, 0.0, 0.4)
    wave_amp = rng.uniform(0.03, 0.08, n)
    freq = rng.uniform(0.6, 1.3, n)
    phase = rng.random(n) * 2 * math.pi
    bend = rng.normal(0.0, 0.07, n)
    strands = np.zeros((n, npts, 3))
    p = pos + nrm * 0.05 * MM
    strands[:, 0] = p
    seg = Lg / (npts - 1)
    for k in range(1, npts):
        sm_ = (k - 0.5) / (npts - 1)
        a = a0 * (1.0 - lay * sm_) + math.radians(1.0)
        d = (tdir * np.cos(a)[:, None] + nrm * np.sin(a)[:, None]
             + side * (bend * sm_ * sm_ + wave_amp * np.sin(2 * math.pi * freq * sm_ + phase))[:, None]
             + gt * (droop * sm_ * sm_)[:, None])
        d /= np.linalg.norm(d, axis=1, keepdims=True)
        p = p + d * seg[:, None]
        strands[:, k] = p
    return strands, f


PAD_COLOURS_V11 = ((0.43, 0.225, 0.215), (0.53, 0.295, 0.275))  # a first pass used (0.50-0.60): candy pink
PAD_SSS_V11 = 0.15  # a first pass used 0.30: the pads read as gummy


def paw_skin_material(images):
    """Skin under the paw coat (pinkish grey, pinker under the white sock)
    and the pads: a muted pink (PAD_COLOURS_V11), leathery, finely papillate
    (0.5 mm cells and a 1.6 mm octave), matte (roughness 0.52) with a soft
    sheen, darker in the pad creases, with a little subsurface."""
    m, nt = v6.new_mat("M_CatBaseV6_PawSkin")
    out = N(nt, "ShaderNodeOutputMaterial", (1600, 0))
    bs = N(nt, "ShaderNodeBsdfPrincipled", (1200, 0))
    coat = v6.image_node(nt, images["coat"], (-900, 400))
    reg = v6.image_node(nt, images["regions"], (-900, -100))
    sc = N(nt, "ShaderNodeSeparateColor", (-600, 400))
    sr = N(nt, "ShaderNodeSeparateColor", (-600, -100))
    L(nt, coat.outputs["Color"], sc.inputs["Color"])
    L(nt, reg.outputs["Color"], sr.inputs["Color"])
    c = v6.mix_rgb(nt, sc.outputs["Red"], (0.20, 0.17, 0.165), (0.40, 0.30, 0.29), (-300, 500))
    tc = N(nt, "ShaderNodeTexCoord", (-900, 900))
    vor = N(nt, "ShaderNodeTexVoronoi", (-600, 1000))
    vor.feature = "DISTANCE_TO_EDGE"
    vor.inputs["Scale"].default_value = 2000.0
    vor.inputs["Randomness"].default_value = 0.9
    L(nt, tc.outputs["Object"], vor.inputs["Vector"])
    vor2 = N(nt, "ShaderNodeTexVoronoi", (-600, 800))
    vor2.feature = "DISTANCE_TO_EDGE"
    vor2.inputs["Scale"].default_value = 620.0
    vor2.inputs["Randomness"].default_value = 0.85
    L(nt, tc.outputs["Object"], vor2.inputs["Vector"])

    def mr(val, a, b, c_, d, loc):
        n_ = N(nt, "ShaderNodeMapRange", loc)
        L(nt, val, n_.inputs["Value"])
        n_.inputs["From Min"].default_value = a
        n_.inputs["From Max"].default_value = b
        n_.inputs["To Min"].default_value = c_
        n_.inputs["To Max"].default_value = d
        return n_.outputs["Result"]

    def math_(op, a, b=None, loc=(0, 0)):
        n_ = N(nt, "ShaderNodeMath", loc)
        n_.operation = op
        for i, val in enumerate((a, b)):
            if val is None:
                continue
            if isinstance(val, (int, float)):
                n_.inputs[i].default_value = float(val)
            else:
                L(nt, val, n_.inputs[i])
        return n_.outputs[0]

    h1 = math_("SQRT", mr(vor.outputs["Distance"], 0.0, 0.32, 0.0, 1.0, (-400, 1000)), None, (-250, 1000))
    h2 = math_("SQRT", mr(vor2.outputs["Distance"], 0.0, 0.25, 0.0, 1.0, (-400, 800)), None, (-250, 800))
    hgt = math_("ADD", math_("MULTIPLY", h1, 0.6, (-100, 1000)), math_("MULTIPLY", h2, 0.4, (-100, 800)), (50, 900))
    ao = mr(hgt, 0.0, 1.0, 0.70, 1.0, (200, 900))
    nzp = N(nt, "ShaderNodeTexNoise", (-600, 600))
    nzp.inputs["Scale"].default_value = 160.0
    nzp.inputs["Detail"].default_value = 4.0
    L(nt, tc.outputs["Object"], nzp.inputs["Vector"])
    padc = v6.mix_rgb(nt, mr(nzp.outputs["Fac"], 0.35, 0.65, 0.0, 1.0, (-400, 600)), PAD_COLOURS_V11[0], PAD_COLOURS_V11[1], (-100, 600))
    padc = v6.mix_rgb(nt, sr.outputs["Green"], padc, (0.20, 0.10, 0.10), (100, 600))
    padm = N(nt, "ShaderNodeMix", (300, 700))
    padm.data_type = "RGBA"
    padm.blend_type = "MULTIPLY"
    padm.inputs["Factor"].default_value = 1.0
    L(nt, padc, padm.inputs[6])
    L(nt, ao, padm.inputs[7])
    c = v6.mix_rgb(nt, sr.outputs["Red"], c, padm.outputs[2], (500, 500))
    L(nt, c, bs.inputs["Base Color"])
    L(nt, mr(sr.outputs["Red"], 0.0, 1.0, 0.62, 0.52, (800, 200)), bs.inputs["Roughness"])
    bs.inputs["Specular IOR Level"].default_value = 0.42
    bs.inputs["Sheen Weight"].default_value = 0.15
    bs.inputs["Sheen Roughness"].default_value = 0.4
    bump = N(nt, "ShaderNodeBump", (900, -300))
    bump.inputs["Distance"].default_value = 0.00032
    L(nt, math_("MULTIPLY", hgt, sr.outputs["Red"], (700, -300)), bump.inputs["Height"])
    L(nt, bump.outputs["Normal"], bs.inputs["Normal"])
    L(nt, math_("MULTIPLY", sr.outputs["Red"], PAD_SSS_V11, (800, -500)), bs.inputs["Subsurface Weight"])
    bs.inputs["Subsurface Radius"].default_value = (1.0, 0.38, 0.30)
    bs.inputs["Subsurface Scale"].default_value = 0.0015
    L(nt, bs.outputs["BSDF"], out.inputs["Surface"])
    return m


def paw_frame_matrix():
    """World matrix of the paw frame for FP_POSE: the forearm axis, the
    supination about it and a slight wrist extension, placed in front of the
    first-person camera."""
    cam = fp_camera_matrix()
    Rc = cam.to_3x3()
    rt, up, fw = Rc.col[0], Rc.col[1], -Rc.col[2]
    w = FP_POSE["wrist"]
    W = cam.translation + rt * w[0] + up * w[1] + fw * w[2]
    a = FP_POSE["axis"]
    ax = (rt * a[0] + up * a[1] + fw * a[2]).normalized()
    z0 = (up - ax * up.dot(ax)).normalized()  # dorsal, palm down
    y0 = z0.cross(ax)  # medial (right-handed: x distal, y medial, z dorsal)
    rot = Matrix.Rotation(math.radians(FP_POSE["supination"]), 3, ax)
    X, Y, Z = ax, rot @ y0, rot @ z0
    M = Matrix((X, Y, Z)).transposed().to_4x4()
    M.translation = W
    return M


def fp_camera_matrix():
    loc = VM_ORIGIN + Vector((0.0, 0.0, FP["eye_h"]))
    fwd = Vector((math.cos(math.radians(FP["pitch"])), 0.0, math.sin(math.radians(FP["pitch"]))))
    M = fwd.to_track_quat("-Z", "Y").to_matrix().to_4x4()
    M.translation = loc
    return M


def bake_paw_textures(cage, res):
    """T_CatBaseV6_Paw_Coat (R white, G stripe, B pale), _Regions (R pad, G
    pad pigment) and _FurMask, evaluated from paw_fields under every texel."""
    t0 = time.time()
    S = v6.evaluated_surface(cage)
    UV = S["uv"][S["tl"]]
    tri, tex, bc = v6.rasterize_uv(UV, res)
    maps = {k: np.zeros((res * res, 3), np.float32) for k in ("coat", "regions", "furmask")}
    cov = np.zeros(res * res, bool)
    step = 1_000_000
    for k0 in range(0, len(tex), step):
        tr = tri[k0:k0 + step]
        w = bc[k0:k0 + step]
        vid = S["tv"][tr]
        P = np.einsum("ij,ijk->ik", w, S["co"][vid])
        Nn = np.einsum("ij,ijk->ik", w, S["nr"][vid])
        Nn /= np.linalg.norm(Nn, axis=1, keepdims=True) + 1e-12
        f = paw_fields(P, Nn)
        ti = tex[k0:k0 + step]
        maps["coat"][ti] = np.stack([f["white"], f["stripe"], f["pale"]], -1)
        maps["regions"][ti] = np.stack([f["pad"], f["pig"], np.zeros(len(P))], -1)
        maps["furmask"][ti] = f["excl"][:, None]
        cov[ti] = True
    cov2 = cov.reshape(res, res)
    images = {}
    for name, key in (("Coat", "coat"), ("Regions", "regions"), ("FurMask", "furmask")):
        a = v6.dilate(maps[key].reshape(res, res, 3), cov2, 10)
        images[key] = v6.save_png(f"T_CatBaseV6_Paw_{name}", a)
    log(f"paw maps {res}px ({time.time()-t0:.0f}s)")
    return images


PAW_LAYERS = [
    # name, clumps (factor, distance, shape, tip spread), noise, noise scale, frizz, length jitter, radius, density (/m2)
    ("CatBaseV6_Paw_Fur_Guard", ((0.62, 2.4 * MM, 0.42, 0.25 * MM), (0.38, 0.9 * MM, 0.28, 0.06 * MM)), 0.14 * MM, 150.0, 0.06 * MM,
     (0.8, 1.2), 0.062 * MM, 5.0e6),
]


def build_paw_cage(coll, pts, quads, Mw):
    """The paw skin: the 0.45 mm level-set mesh, cleaned, decimated to half,
    relaxed with a volume-preserving Laplacian smooth (the voxel facets go)
    and UV-unwrapped, placed at Mw. It is rendered directly: at first-person
    distance a 0.45 mm level set is finer than a pixel. (A QuadriFlow cage
    like the head's was tried first; QuadriFlow crashed on the paw.)"""
    me = v6.mesh_from_arrays("CatBaseV6_Paw_SkinMesh", pts, quads)
    v6.clean_manifold(me)
    skin = v6.link(bpy.data.objects.new("CatBaseV6_Paw_Skin", me), coll)
    v6.set_active(skin)
    m = skin.modifiers.new("dec", "DECIMATE")
    m.ratio = PAW_DECIMATE
    bpy.ops.object.modifier_apply(modifier="dec")
    m = skin.modifiers.new("relax", "LAPLACIANSMOOTH")
    m.lambda_factor = 0.6
    m.iterations = 4
    m.use_volume_preserve = True
    bpy.ops.object.modifier_apply(modifier="relax")
    v6.clean_manifold(skin.data)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(64), island_margin=0.002, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    skin.data.uv_layers[0].name = "UVMap"
    for p in skin.data.polygons:
        p.use_smooth = True
    skin.matrix_world = Mw
    co, nr = v6.mesh_arrays(skin.data)
    f = paw_fields(co, nr)
    for nm in ("fd_paw", "fd_paw_under"):
        a_ = skin.data.attributes.new(nm, "FLOAT", "POINT")
        a_.data.foreach_set("value", f["density"].astype(np.float32))
    log(f"paw skin {len(skin.data.polygons)} faces")
    return skin


def build_paw_groom(coll, skin, images, Mw):
    """Guard and undercoat layers interpolated from paw guides (the head's
    modifier stack: clumps, noise, frizz, shrinkwrap, profile), stray guard
    hairs, and interdigital tufts: short white hairs between the toe beans
    and round the metacarpal pad, standing off the palm."""
    rng = np.random.default_rng(v6.RNG_SEED + 31)
    S = v6.evaluated_surface(skin)
    g_local = np.array(Mw.to_3x3().inverted() @ Vector((0.0, 0.0, -1.0)))

    def wfn(c, n, ex):
        f = paw_fields(c, n)
        return f["density"] * np.maximum(f["excl"], 0.05) / np.maximum(f["length"], 2.5 * MM)

    pos, nrm, uv, ex = v6.sample_roots(S, PAW_GUIDES, wfn, rng)
    strands, f = grow_paw_guides(pos, nrm, 8, rng, g_local)
    v6.load_hair_assets()
    v6.length_jitter_group()
    layers = []
    gob = v6.make_curves("CatBaseV6_Paw_Fur_GuardGuides", strands, 0.062 * MM, 0.016 * MM, coll, uv=uv, surface=skin)
    gdata = gob.data
    gdata.materials.append(hair_material_v11("M_CatBaseV6_Paw_Fur_Guard", images, False, tip_alpha=True))
    bpy.data.objects.remove(gob, do_unlink=True)
    for li, (name, clumps, noise, nscale, frizz, jitter, r0, dens) in enumerate(PAW_LAYERS):
        ob = v6.link(bpy.data.objects.new(name, gdata), coll)
        ob.parent = skin
        seed = 41 + 10 * li
        v6.gn_mod(ob, "Interpolate Hair Curves", Follow_Surface_Normal=True, Part_by_Mesh_Islands=True, Density=dens,
                  Density_Mask=("ATTR", "fd_paw"), Mask_Texture=images["furmask"], Interpolation_Guides=4, Viewport_Amount=0.05, Seed=seed)
        v6.gn_mod(ob, "CatBaseV6 Length Jitter", Min=jitter[0], Max=jitter[1], Seed=seed + 20)
        for ci, (cf, cd_, csh, spread) in enumerate(clumps):
            v6.gn_mod(ob, "Clump Hair Curves", Factor=cf, Shape=csh, Tip_Spread=spread, Existing_Guide_Map=False,
                      Guide_Distance=cd_, Guide_Mask=1.0, Preserve_Length=True, Seed=11 + 17 * ci + seed)
        v6.gn_mod(ob, "Hair Curves Noise", Factor=1.0, Distance=noise, Shape=0.5, Scale=nscale, Scale_along_Curve=1.0,
                  Offset_per_Curve=1.0, Seed=9 + seed, Preserve_Length=True)
        v6.gn_mod(ob, "Frizz Hair Curves", Factor=1.0, Distance=frizz, Shape=0.7, Seed=19 + seed, Preserve_Length=True)
        v6.gn_mod(ob, "Shrinkwrap Hair Curves", Surface=skin, Factor=1.0, Offset_Distance=0.12 * MM, Smoothing_Steps=2, Lock_Roots=True)
        v6.gn_mod(ob, "Set Hair Curve Profile", Replace_Radius=True, Radius=r0, Shape=-0.5, Factor_Min=0.0, Factor_Max=1.0)
        layers.append(ob)
    ob = v6.make_curves("CatBaseV6_Paw_Fur_Under", strands, 0.030 * MM, 0.0075 * MM, coll, uv=uv, surface=skin)
    ob.parent = skin
    ob.data.materials.append(hair_material_v11("M_CatBaseV6_Paw_Fur_Under", images, True, tip_alpha=False))
    v6.gn_mod(ob, "Interpolate Hair Curves", Follow_Surface_Normal=True, Part_by_Mesh_Islands=True, Density=6.0e6,
              Density_Mask=("ATTR", "fd_paw_under"), Mask_Texture=images["furmask"], Interpolation_Guides=4, Viewport_Amount=0.05, Seed=57)
    v6.gn_mod(ob, "CatBaseV6 Length Jitter", Min=0.7, Max=1.3, Seed=77)
    v6.gn_mod(ob, "Trim Hair Curves", Scale_Uniform=False, Replace_Length=False, Length_Factor=0.55, Random_Offset=0.0, Pin_at_Parameter=0.0, Seed=63)
    v6.gn_mod(ob, "Clump Hair Curves", Factor=0.30, Shape=0.3, Tip_Spread=0.0, Existing_Guide_Map=False, Guide_Distance=2.0 * MM, Guide_Mask=1.0,
              Preserve_Length=True, Seed=61)
    v6.gn_mod(ob, "Hair Curves Noise", Factor=1.0, Distance=0.35 * MM, Shape=0.5, Scale=520.0, Scale_along_Curve=1.0, Offset_per_Curve=1.0, Seed=55,
              Preserve_Length=True)
    v6.gn_mod(ob, "Frizz Hair Curves", Factor=1.0, Distance=0.16 * MM, Shape=0.7, Seed=65, Preserve_Length=True)
    v6.gn_mod(ob, "Shrinkwrap Hair Curves", Surface=skin, Factor=1.0, Offset_Distance=0.12 * MM, Smoothing_Steps=2, Lock_Roots=True)
    v6.gn_mod(ob, "Set Hair Curve Profile", Replace_Radius=True, Radius=0.030 * MM, Shape=-0.5, Factor_Min=0.0, Factor_Max=1.0)
    layers.append(ob)
    # stray guard hairs
    n_stray = 1800
    sp_, sn_, suv, _ = v6.sample_roots(S, n_stray, wfn, rng)
    st, fs = grow_paw_guides(sp_, sn_, 10, rng, g_local, length_scale=rng.uniform(1.15, 1.45, n_stray),
                             lift_add=rng.uniform(2.0, 7.0, n_stray), lay=0.75)
    keep = fs["excl"] > 0.95
    st, suv = st[keep], suv[keep]
    # interdigital tufts: between the toe beans and round the metacarpal pad
    def wtuft(c, n, ex):
        f_ = paw_fields(c, n)
        xm = c[:, 0] / MM
        return (n[:, 2] < -0.25) * f_["excl"] * (1.0 - smoothstep(1.0, 4.5, np.maximum(f_["pads_sd"], 0.0))) * (xm > 2.0) * (xm < 76.0)

    n_tuft = 520
    tp, tn, tuv, _ = v6.sample_roots(S, n_tuft, wtuft, rng)
    npts = 10
    tt = np.linspace(0.0, 1.0, npts)
    tufts, tuvs, trad = [], [], []
    for i in range(n_tuft):
        nn = tn[i]
        d = nn * 0.75 + np.array([0.55, 0.0, 0.0])
        d /= np.linalg.norm(d)
        Lt = rng.uniform(7.0, 12.0) * MM
        k = int(rng.integers(3, 7))
        tipp = None
        for _ in range(k):
            off = rng.normal(0.0, 0.40 * MM, 3)
            off -= (off @ nn) * nn
            p = tp[i] + off - nn * 0.1 * MM
            fan = rng.normal(0.0, 0.10, 3)
            pts_ = [p.copy()]
            Lh = Lt * rng.uniform(0.75, 1.1)
            for kk in range(1, npts):
                s_ = kk / (npts - 1)
                dd = d + fan * s_ + g_local * 0.10 * s_ * s_
                dd /= np.linalg.norm(dd)
                p = p + dd * Lh / (npts - 1)
                pts_.append(p.copy())
            pts_ = np.array(pts_)
            if tipp is None:
                tipp = pts_[-1].copy()
            pts_ = pts_ + (tipp - pts_[-1])[None, :] * (0.30 * tt ** 2)[:, None]
            tufts.append(pts_)
            tuvs.append(tuv[i])
            trad.append((0.050 * MM) * (1 - tt) ** 1.1 + 0.006 * MM)
    tufts = np.array(tufts)
    # strays are resampled to the tufts' point count so both share one curves object
    st10 = st[:, np.linspace(0, st.shape[1] - 1, npts).round().astype(int)]
    radii = np.concatenate([np.repeat(((0.066 * MM) * (1 - tt) ** 1.3 + 0.008 * MM)[None], len(st10), 0), np.array(trad)])
    ob = v6.make_curves("CatBaseV6_Paw_Fur_StrayTufts", np.concatenate([st10, tufts]), 0, 0, coll,
                        uv=np.concatenate([suv, np.array(tuvs)]), surface=skin, radii=radii)
    ob.parent = skin
    ob.data.materials.append(hair_material_v11("M_CatBaseV6_Paw_Fur_Stray", images, False))
    layers.append(ob)
    log(f"paw groom: {PAW_GUIDES} guides, {len(st10)} strays, {len(tufts)} interdigital hairs in {n_tuft} tufts")
    return layers


def build_viewmodel_paw(root):
    """The first-person right forearm and paw with its own textures, skin,
    groom and the first-person camera, in collection CatBaseV6_Viewmodel."""
    t0 = time.time()
    coll = bpy.data.collections.new("CatBaseV6_Viewmodel")
    root.children.link(coll)
    pts, quads = build_paw_levelset()
    np.savez_compressed(CACHE / "paw_dense.npz", pts=pts.astype(np.float32), quads=quads.astype(np.int32))
    Mw = paw_frame_matrix()
    cage = build_paw_cage(coll, pts, quads, Mw)
    images = bake_paw_textures(cage, PAW_TEX)
    cage.data.materials.append(paw_skin_material(images))
    layers = build_paw_groom(coll, cage, images, Mw)
    cd = bpy.data.cameras.new("CAM_FirstPersonPaw")
    cd.sensor_width = 36.0
    cd.lens = 18.0 / math.tan(math.radians(0.5 * FP["fov_h"]))
    cd.clip_start = 0.02
    cd.clip_end = 400.0
    cd.dof.use_dof = True
    cd.dof.aperture_fstop = FP["fstop"]
    cam = v6.link(bpy.data.objects.new("CAM_FirstPersonPaw", cd), coll)
    cam.matrix_world = fp_camera_matrix()
    cd.dof.focus_distance = (Mw.translation + Mw.to_3x3() @ Vector((0.030, 0.0, 0.0)) - cam.matrix_world.translation).length
    stats = dict(paw_faces=len(cage.data.polygons), paw_guides=PAW_GUIDES,
                 fp_lens_mm=round(cd.lens, 2), fp_fov_h_deg=FP["fov_h"], build_seconds=round(time.time() - t0))
    (CACHE / "paw_build_stats.json").write_text(json.dumps(stats, indent=2))
    log("viewmodel paw", stats)
    return coll, layers


# ---------------------------------------------------------------------------
# Overrides
# ---------------------------------------------------------------------------

def apply_round9_overrides():
    if getattr(v6, "_ROUND9", False):
        return
    v10.apply_round8_overrides()
    v6._ROUND9 = True
    # eyes: a smaller, hooded aperture; the globes 1.1 mm back
    A.fissure_w = FISSURE_W_V11 * MM
    A.fissure_up = FISSURE_UP_V11 * MM
    A.fissure_lo = FISSURE_LO_V11 * MM
    A.eye_sink = -EYE_FORWARD_V11 * MM
    v8.iris_colour = iris_colour_v11
    v8.iris_height_mm = iris_height_mm_v11
    # skin: the zygomatic fill and fuller neck, the biped bust
    v10.fur_inset_mm_v10 = fur_inset_mm_v11
    v7.fur_inset_mm = fur_inset_mm_v11
    v7.build_bust_ops = build_bust_ops_v11
    v7.build_bust_field = build_bust_field_v11
    v6.DETAIL_OPS = None
    # coat, flow
    v10.HEAD_LENGTH_KEYS_V10 = HEAD_LENGTH_KEYS_V11
    v10.coat_fields_v10 = coat_fields_v11
    v9.coat_fields_v9 = coat_fields_v11
    v8.coat_fields_v8 = coat_fields_v11
    v6.coat_fields = coat_fields_v11
    v6.fur_direction = fur_direction_v11


def install_build_overrides_v11():
    if getattr(v6, "_ROUND9_BUILD", False):
        return
    v10.install_build_overrides_v10()
    v6._ROUND9_BUILD = True
    v9._V6_BUILD_SKIN = build_skin_base_v11
    prev_build_eyes = v6.build_eyes

    def build_eyes_v11(coll, mats, parent):
        objs = prev_build_eyes(coll, mats, parent)
        cmat = cornea_material_v11()
        for o in objs:
            if o.name.endswith("_Cornea"):
                o.data.materials.clear()
                o.data.materials.append(cmat)
        return objs

    v6.build_eyes = build_eyes_v11
    v6.skin_material = skin_material_v11
    v6.build_inner_ear_furnishings = build_inner_ear_furnishings_v11
    v10.hair_material_v10 = hair_material_v11


# ---------------------------------------------------------------------------
# Review aids: the bare skin (head and bust) and the bare paw, Workbench
# ---------------------------------------------------------------------------

def preview_bust_v11(args):
    """v10.preview_v10 (bare skin at the five cameras and the ear / eye / nose
    close-ups) plus two wide bust views for the shoulders and arms."""
    v10.preview_v10(args)
    sc = bpy.context.scene
    cam = sc.camera
    bpy.data.objects["dense"].hide_render = False
    for name, d_, dist, tgt in (("bust_front", Vector((1.0, 0.0, 0.05)), 2.6, Vector((0.0, 0.0, 1.20))),
                                ("bust_tq", Vector((0.72, -0.69, 0.10)), 2.6, Vector((0.0, 0.0, 1.20))),
                                ("bust_profile", Vector((0.0, -1.0, 0.05)), 2.6, Vector((0.0, 0.0, 1.20)))):
        cam.data.lens = 50.0
        cam.location = tgt + d_.normalized() * dist
        cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = str(Path(args.preview_dir) / f"skin_{name}.png")
        bpy.ops.render.render(write_still=True)


def preview_paw(args):
    """The bare paw level set (Workbench): from the first-person camera at the
    FP_POSE, and dorsal, palmar and side views in the paw frame."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    pts, quads = build_paw_levelset()
    me = v6.mesh_from_arrays("paw", pts, quads)
    me.shade_smooth()
    ob = v6.link(bpy.data.objects.new("paw", me))
    body, pads = paw_parts(pts / MM)
    col = me.color_attributes.new("pad", "FLOAT_COLOR", "POINT")
    padw = smoothstep(0.15, 1.1, body) * (1.0 - smoothstep(0.05, 0.7, pads))
    cc = np.ones((len(pts), 4), np.float32)
    cc[:, 1] = 1.0 - 0.6 * padw
    cc[:, 2] = 1.0 - 0.6 * padw
    col.data.foreach_set("color", cc.ravel())
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.color_type = "VERTEX"
    sc.display.shading.show_cavity = True
    sc.display.shading.cavity_type = "BOTH"
    sc.render.resolution_x = 960
    sc.render.resolution_y = 540
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.sensor_width = 36.0
    views = [("dorsal", Vector((0.02, 0.0, 0.0)), Vector((0.1, 0.0, 1.0)), 0.55, 50.0),
             ("palmar", Vector((0.02, 0.0, 0.0)), Vector((0.1, 0.0, -1.0)), 0.55, 50.0),
             ("side", Vector((0.0, 0.0, 0.0)), Vector((0.0, -1.0, 0.1)), 0.65, 50.0),
             ("toes", Vector((0.05, 0.0, -0.005)), Vector((1.0, 0.1, -0.5)), 0.30, 50.0),
             ("palm_close", Vector((0.03, 0.0, -0.01)), Vector((0.25, 0.15, -1.0)), 0.26, 50.0)]
    for name, t, d_, dist, lens in views:
        cam.data.lens = lens
        cam.location = t + d_.normalized() * dist
        cam.rotation_euler = (t - cam.location).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = str(Path(args.preview_dir) / f"paw_{name}.png")
        bpy.ops.render.render(write_still=True)
    ob.matrix_world = paw_frame_matrix()
    cam.matrix_world = fp_camera_matrix()
    cam.data.lens = 18.0 / math.tan(math.radians(0.5 * FP["fov_h"]))
    sc.render.resolution_x = 1920
    sc.render.resolution_y = 1080
    sc.render.resolution_percentage = 50
    sc.render.filepath = str(Path(args.preview_dir) / "paw_fp.png")
    bpy.ops.render.render(write_still=True)


# ---------------------------------------------------------------------------
# Measure, render, compare, manifest (round 9)
# ---------------------------------------------------------------------------

def measure_bust_v11():
    """Skin half-widths (world-local mm) for the temple-to-cheek run and the
    neck, the shoulder breadth and the arm (upper arm at mid-height) from
    the cached level set."""
    d = np.load(CACHE / "skin_dense.npz")
    P = d["pts"].astype(float) / MM
    out = {}
    hw = {}
    for z in range(40, -135, -5):
        sl = P[(np.abs(P[:, 2] - z) < 0.8) & (P[:, 0] > -60) & (P[:, 0] < 120) & (np.abs(P[:, 1]) < 115)]
        if len(sl):
            hw[z] = round(float(np.abs(sl[:, 1]).max()), 1)
    out["head_neck_halfwidth_by_z_mm"] = hw
    cheek = max(hw.get(z, 0.0) for z in range(-60, -5, 5))
    neck = min(hw.get(z, 1e3) for z in range(-115, -75, 5))
    out["temple_to_cheek_monotonic_z20_to_m35"] = bool(all(hw.get(z, 0) <= hw.get(z - 5, 0) + 0.3 for z in range(20, -35, -5)))
    out["neck_over_cheek_skin"] = round(neck / cheek, 3)
    sh = P[(P[:, 2] < -170) & (P[:, 2] > -260)]
    out["shoulder_halfwidth_mm"] = round(float(np.abs(sh[:, 1]).max()), 1)
    arm = P[(np.abs(P[:, 2] + 340) < 1.0) & (np.abs(P[:, 1]) > 105)]
    if len(arm):
        ys = np.abs(arm[:, 1])
        out["upper_arm_at_z_m340_y_range_mm"] = [round(float(ys.min()), 1), round(float(ys.max()), 1)]
    return out


def stage_measure_v11(args):
    out = v7.stage_measure_v7(args)
    out["round8_skin"] = v10.measure_skin_v10()
    out["round9_bust"] = measure_bust_v11()
    p = CACHE / "paw_build_stats.json"
    if p.exists():
        out["round9_paw"] = json.loads(p.read_text())
    (CACHE / f"measure_round{args.round}.json").write_text(json.dumps(out, indent=2) + "\n")
    log("round-9 measures", json.dumps(out["round8_skin"]), json.dumps(out["round9_bust"]))
    return out


def _open_for_render():
    bpy.ops.wm.open_mainfile(filepath=str(OUT / "CatBaseV6.blend"))
    rigs = {nm: bpy.data.collections[f"Light_{nm}"] for nm in ("Studio", "Overcast", "ThreePoint", "Exterior", "RefMatch")
            if f"Light_{nm}" in bpy.data.collections}
    cams = {n: bpy.data.objects[f"CAM_{n}"] for n in list(v6.CAMERAS) + list(v6.REFMATCH) if f"CAM_{n}" in bpy.data.objects}
    return rigs, cams


def stage_render_v11(args):
    """The fixed review frames (v6.render_round). Persistent data keeps the
    3.6 M-strand BVH between frames (only the camera, lights and world
    change), which does not change the image."""
    rigs, cams = _open_for_render()
    bpy.context.scene.render.use_persistent_data = True
    counts = v6.count_strands()
    (CACHE / f"strand_counts_round{args.round}.json").write_text(json.dumps(counts, indent=2))
    log("strand counts at 100% density", counts)
    return v6.render_round(args, rigs, cams)


def stage_silhouette(args):
    """Review aid: the Front camera with a transparent film (Overcast world,
    no ground plane, 50 %, 32 samples) so the fur silhouette is the alpha;
    writes the per-row half-width (world-local mm at the target distance)
    of the head, neck and shoulders to <preview-dir>/silhouette_front.json."""
    rigs, cams = _open_for_render()
    for nm, col in rigs.items():
        col.hide_render = True
    v6.set_world("Overcast")
    sc = bpy.context.scene
    v6.configure_render.percent = 50
    v6.configure_render(32)
    sc.render.film_transparent = True
    sc.render.image_settings.color_mode = "RGBA"
    sc.camera = cams["Front"]
    fp = Path(args.preview_dir) / "silhouette_front.png"
    sc.render.filepath = str(fp)
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(str(fp))
    w, h = img.size
    px = np.array(img.pixels[:], np.float32).reshape(h, w, 4)[::-1]
    a = px[..., 3] > 0.5
    mmpx = 1.75 * 36.0 / 85.0 / w * 1000.0
    out = {}
    for y in range(0, h, 2):
        xs = np.nonzero(a[y])[0]
        if len(xs) < 3:
            continue
        zl = round((h / 2 - y) * mmpx + (v6.CAM_TARGET.z - v6.HEAD_ORIGIN.z) / MM, 1)
        out[zl] = round(0.5 * (xs.max() - xs.min() + 1) * mmpx, 1)
    (Path(args.preview_dir) / "silhouette_front.json").write_text(json.dumps(out, indent=1))
    log("front silhouette half-widths (world-local z mm -> mm)", json.dumps({k: out[k] for k in list(out)[::6]}))
    return out


FP_LIGHTS = ("Overcast", "Exterior")


def stage_pawbuild(args):
    """Build the first-person forearm and paw on its own (a separate Blender
    pass and a separate .blend, CatBaseV6_ViewmodelPaw.blend, as the shipped
    first-person arm is its own mesh): level set, skin, baked maps, groom,
    the first-person camera and the fixed light rigs."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    v6.configure_render(args.samples)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    root = bpy.data.collections.new("CatBaseV6_ViewmodelPaw")
    sc.collection.children.link(root)
    build_viewmodel_paw(root)
    v6.build_lighting(root)
    for img in bpy.data.images:
        if img.name.startswith("T_CatBaseV6_Paw_"):
            img.filepath = "//Textures/" + Path(img.filepath_raw).name
    v6.scrub_private_paths()
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / PAW_BLEND), compress=True, relative_remap=True)
    log("saved", OUT / PAW_BLEND)


def stage_fprender(args):
    """The first-person paw frame(s) from CatBaseV6_ViewmodelPaw.blend: the
    CAM_FirstPersonPaw camera, Overcast (its ground plane enlarged 12x for
    this frame only, so its far edge sits on the horizon) and Exterior."""
    bpy.ops.wm.open_mainfile(filepath=str(OUT / PAW_BLEND))
    rigs = {nm: bpy.data.collections[f"Light_{nm}"] for nm in ("Studio", "Overcast", "ThreePoint", "Exterior", "RefMatch")
            if f"Light_{nm}" in bpy.data.collections}
    cam = bpy.data.objects["CAM_FirstPersonPaw"]
    counts = v6.count_strands()
    (CACHE / f"paw_strand_counts_round{args.round}.json").write_text(json.dumps(counts, indent=2))
    log("paw strand counts at 100% density", counts)
    rdir = Path(args.render_dir) if args.render_dir else OUT / "Renders" / f"round_{args.round}"
    rdir.mkdir(parents=True, exist_ok=True)
    sc = bpy.context.scene
    v6.configure_render.percent = args.percent
    v6.configure_render(args.samples)
    v6.scrub_private_paths()
    exposure = {"Overcast": 0.35, "Exterior": 0.55}
    gr = bpy.data.objects.get("Overcast_Ground")
    if gr is not None:
        gr.scale = (12.0, 12.0, 1.0)
    written = []
    lights = [l_ for l_ in args.lights.split(",") if l_ in FP_LIGHTS] or list(FP_LIGHTS)
    for light in lights:
        for nm, col in rigs.items():
            col.hide_render = nm != light
        v6.set_world(light)
        sc.view_settings.exposure = exposure[light]
        sc.render.resolution_x = 1920
        sc.render.resolution_y = 1080
        sc.camera = cam
        fp = rdir / f"CatBaseV6_R{args.round}_{light}_FirstPersonPaw.png"
        sc.render.filepath = str(fp)
        t0 = time.time()
        bpy.ops.render.render(write_still=True)
        log(f"rendered {fp.name} in {time.time()-t0:.0f}s")
        written.append(fp)
    return written


def stage_compare_v11(args):
    """Round-8 sheets (previous | this round at the reference framing, the
    five Overcast cameras, the close-ups, the backlit front, the Nyaakoto
    reference, the close three-quarter under all lights)."""
    v10.stage_compare_v10(args)


def stage_manifest_v11(args):
    v10.stage_manifest_v10(args)
    man = json.loads((OUT / "manifest.json").read_text())
    man["round"] = args.round
    man["generator"] = ("scripts/art/create_cat_base_v11.py (round 9; imports create_cat_base_v10.py, which imports "
                        "create_cat_base_v9.py, create_cat_base_v8.py, create_cat_base_v7.py and create_cat_base_v6.py)")
    pstats = CACHE / "paw_build_stats.json"
    man["round9"] = {
        "eyes": {"fissure_mm": {"width": FISSURE_W_V11, "upper": FISSURE_UP_V11, "lower": FISSURE_LO_V11}, "globe_forward_mm": EYE_FORWARD_V11,
                 "cornea": {"roughness": CORNEA_ROUGH_V11, "tear_film_bump": TEAR_BUMP},
                 "iris": "paler grey-blue stroma, deeper relief (iris_colour_v11, iris_height_mm_v11)"},
        "skin": {"cheek_fill": CHEEK_FILL, "neck_outset_mm": NECK_OUTSET_V11, "neck_outset_z_mm": list(NECK_Z_V11), "quadriflow_target_faces": QUAD_TARGET_V11},
        "bust": {"shoulder_joint_mm": list(SHOULDER_V11), "elbow_mm": list(ELBOW_V11), "forearm_toward_mm": list(WRIST_DIR_V11)},
        "coat": {"cheek_white_head_mm": CHEEK_WHITE, "ear_vessel": EAR_VEIN_V11, "furnishing_tufts": FURN_TUFTS_V11},
        "viewmodel_paw": {"frame": "paw frame: +x distal, +y medial (right paw), +z dorsal; mm at character scale",
                          "digits_y_tip_mm": PAW_DIGITS, "voxel_mm": PAW_VOXEL, "decimate_ratio": PAW_DECIMATE, "texture_px": PAW_TEX,
                          "guides": PAW_GUIDES, "first_person_camera": FP, "pose": FP_POSE,
                          "build": json.loads(pstats.read_text()) if pstats.exists() else None,
                          "textures": ["Textures/T_CatBaseV6_Paw_Coat.png", "Textures/T_CatBaseV6_Paw_Regions.png",
                                       "Textures/T_CatBaseV6_Paw_FurMask.png"]},
    }
    (OUT / "manifest.json").write_text(json.dumps(man, indent=2, ensure_ascii=False) + "\n")
    log("manifest (round 9 fields added)")


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
    ap.add_argument("--preview-dir", default=str(CACHE / "preview_r9"))
    ap.add_argument("--tex", type=int, default=4096)
    ap.add_argument("--guides", type=int, default=80000)
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
    apply_round9_overrides()
    stages = args.stages.split(",")
    if "scan" in stages:
        v7.stage_scan(args)
    if "skin" in stages:
        v10.EAR_CAVITY_REBUILD_V10[0] = True
        v10._EAR_CAVITY_V10.clear()
        v7.stage_skin_v7(args)
    if "skinmeasure" in stages:
        m = dict(v10.measure_skin_v10(), **measure_bust_v11())
        log("skin measure", json.dumps(m))
        (Path(args.preview_dir) / "skin_measure.json").write_text(json.dumps(m, indent=2))
    if "skinpreview" in stages:
        preview_bust_v11(args)
    if "pawpreview" in stages:
        preview_paw(args)
    if "build" in stages:
        install_build_overrides_v11()
        v6.stage_build(args)
    if "render" in stages:
        stage_render_v11(args)
    if "pawbuild" in stages:
        stage_pawbuild(args)
    if "fprender" in stages:
        stage_fprender(args)
    if "silhouette" in stages:
        stage_silhouette(args)
    if "measure" in stages:
        stage_measure_v11(args)
    if "compare" in stages:
        stage_compare_v11(args)
    if "manifest" in stages:
        stage_manifest_v11(args)


if __name__ == "__main__":
    main()
