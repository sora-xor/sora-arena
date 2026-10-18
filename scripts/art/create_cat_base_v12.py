"""CatBaseV6 round 10 (generator v12): judged defects of round 9.

Round 9 (create_cat_base_v11.py) was reviewed from its 11 finished frames.
The review listed these CG tells, most visible first; round 10 answers them
in that order:

1. eyes, 1 m: a hard horizon reflection through both pupils, a
   painted-marble iris with radial streaks and white veining, a milky
   softbox blob in one iris (a cataract read), a soft uniform pupil bar
   running under both lids, no limbal darkening; a grey margin-sheet line
   inside the black rim, a uniform black "eyeliner" gasket, a red speck
   and a dark void at the medial canthus;
2. expression: a flat upper lid over ~25 % of the iris and a drooping
   lateral canthus (sleepy, not alert); the far eye bulging past the nasal
   bridge in close 3/4;
3. head silhouette at 3 m: parallel sides from temple to jowl, no jaw or
   chin break, lumps at eye level under the rim light; a double hump on
   the nape and a pale band across it; a thick neck column;
4. bust: knitwear rings on the arms, primitive shoulder caps, a torso wider
   on screen than round 8;
5. ears: a smooth pink upper inner pinna, paper-thin margins (a dark rim
   and a pink cut edge), furnishings standing as a stiff white comb;
6. muzzle: a hard-edged painted white mask, flat whisker pads, no mouth
   line, a small nose leather without a dark rim;
7. coat: a stencilled forehead M and uniform painted bars, no agouti
   salt-and-pepper, fleece-like white fur, no guard-hair breakup;
8. paw: hazy pads, a visible dewclaw stub, no claw sheaths.

Round 10 keeps round 5's method (the head and neck from the elaughli scan
field, the CT for landmarks only), the fixed cameras and lights, and every
round-9 stage. Each constant says in its comment what the round-9 value did.

Run from the repository root (Blender 5.2.2 LTS, background):

  blender -b --factory-startup --python scripts/art/create_cat_base_v12.py -- \\
      --stages skin,build,pawbuild,measure --round 10
  blender -b --factory-startup --python scripts/art/create_cat_base_v12.py -- \\
      --stages render --round 10 --samples 256 --views Front,Profile,ThreeQuarter,CloseFront,CloseThreeQuarter \\
      --lights Overcast,Studio,ThreePoint,Exterior,RefMatch
  blender -b --factory-startup --python scripts/art/create_cat_base_v12.py -- \\
      --stages fprender --round 10 --samples 256 --lights Overcast,Exterior
  blender -b --factory-startup --python scripts/art/create_cat_base_v12.py -- --stages compare,manifest --round 10
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
import create_cat_base_v11 as v11  # noqa: E402

v10 = v11.v10
v9 = v11.v9
v8 = v11.v8
v7 = v11.v7
v6 = v11.v6
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

ROUND = 10


def _math(nt, op, a, b=None, loc=(0, 0), clamp=False):
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


def _maprange(nt, val, a, b, c, d, loc=(0, 0), smooth=False):
    n_ = N(nt, "ShaderNodeMapRange", loc)
    L(nt, val, n_.inputs["Value"])
    n_.inputs["From Min"].default_value = a
    n_.inputs["From Max"].default_value = b
    n_.inputs["To Min"].default_value = c
    n_.inputs["To Max"].default_value = d
    if smooth:
        n_.interpolation_type = "SMOOTHSTEP"
    return n_.outputs["Result"]


# ---------------------------------------------------------------------------
# Eyes: aperture and expression (round 10)
# ---------------------------------------------------------------------------

# round-9 review: "the smaller hooded aperture puts a flat upper lid over
# ~25 % of the iris, and the lateral canthus droops: sleepy or melancholy,
# not alert and hooded; real cats' lateral canthus tilts up toward the ear".
# Round 9: 37 mm wide, the upper arc 8.6 mm and the lower 10.2 mm above and
# below the canthal line, tilted 8 deg; the upper arc peaked medially and was
# flat-topped (fullness 0.30). The iris radius is 18.0 mm, so an 8.6 mm upper
# arc hid 9.4 mm (26 %) of it; at 12.8 mm the lid covers ~14 %.
FISSURE_W_V12 = 38.0
FISSURE_UP_V12 = 12.8
FISSURE_LO_V12 = 11.6
FISSURE_TILT_V12 = 12.5  # deg, the lateral canthus higher than the medial (round 9: 8)
UPPER_FULL_V12 = 0.10  # arc fullness (round 9: 0.30, a flat-topped lid)
UPPER_LATERAL_V12 = 0.10  # the upper arc peaks a little lateral of centre (round 9: +0.05)
MEDIAL_DROP_V12 = 2.2  # mm: the medial canthus drawn down toward the nose (round 9: 2.6)
# round-9 review: "in close 3/4 the far eye bulges past the nasal-bridge
# silhouette". Round 9 had the globes 1.4 mm forward of the orbit placement;
# 0.4 mm keeps the cornea domed in profile.
EYE_FORWARD_V12 = 0.4


def fissure_curves_v12(uu):
    """Upper and lower lid arcs (m) of the palpebral fissure. Both arcs still
    close to pointed canthi (base ** 1), but the upper arc is round rather
    than flat-topped and peaks a little lateral of centre, so with the 12.5
    deg canthal tilt the eye rises toward the ear; the medial canthus keeps
    the small tear-duct notch of round 6."""
    hw = 0.5 * A.fissure_w
    t = np.clip(uu / hw, -1.0, 1.0)
    base = np.clip(1.0 - t * t, 0.0, 1.0)
    up = A.fissure_up * base * (1.0 + UPPER_FULL_V12 * base) / (1.0 + UPPER_FULL_V12) * (1.0 + UPPER_LATERAL_V12 * t)
    lo = -A.fissure_lo * base * (1.0 + 0.20 * base) / 1.20 * (1.0 - 0.04 * t)
    drop = MEDIAL_DROP_V12 * MM * np.clip(-t, 0.0, 1.0) ** 2.2
    notch = 0.9 * MM * smoothstep(-0.84, -1.0, t) ** 1.5
    return up - drop - notch, lo - drop - notch


# ---------------------------------------------------------------------------
# Eyes: pupil, iris, cornea (round 10)
# ---------------------------------------------------------------------------

# round-9 review: "the pupil is a uniform, soft-edged dark bar that runs
# under both lids, not a sharp slit that tapers at both ends". Round 9 used
# round 6's slit: half-width 0.105 iris radii (3.8 mm wide), half-height 0.56
# (10.1 mm, the tips under both lids), a 0.018 feather and a parabolic
# profile. Overcast daylight gives a cat a narrow slit; the tips now lie
# inside the opened aperture and the edge is crisp.
PUPIL_W0_V12 = 0.060  # slit half-width at its centre, iris radii (2.2 mm wide)
PUPIL_H_V12 = 0.52  # slit half-height, iris radii (9.4 mm; the lids are at 12.8 / 11.6 mm)
PUPIL_EXP_V12 = 0.80  # width profile (1 - (y/H)^2)^0.8: full in the middle, pointed tips
PUPIL_FEATHER_V12 = 0.006
RUFF_V12 = 0.045  # dark pupillary ruff width, iris radii


def iris_fields_v12(rho, th):
    """Round-7 stroma fields plus a fine, even fibre texture (fine2): round 9's
    three wavy fibre octaves carried the colour contrast, and at 1 m they read
    as radial streaks and white veins in painted marble."""
    f = v9.iris_fields_v9(rho, th)
    s = v8.IRIS_SEED
    U = np.mod(th / (2.0 * math.pi), 1.0)
    f["fine2"] = 0.6 * v8.pnoise(U * 1400.0, rho * 30.0, 1400, s + 41) + 0.4 * v8.pnoise(U * 620.0, rho * 12.0, 620, s + 42)
    f["sector"] = v8.pnoise(U * 6.0, rho * 1.2, 6, s + 43)
    return f


IRIS_BASE_V12 = np.array([0.205, 0.300, 0.390])  # linear; a clear pale grey-blue (round 9: 0.185, 0.26, 0.33 base under 55 % pale fibres)
IRIS_LIMBUS_V12 = np.array([0.030, 0.046, 0.068])


def iris_colour_v12(f, rho):
    """Round 10 iris (round-9 review: 'painted marble, with radial streaks and
    patchy white veining ... no limbal darkening'). A clear grey-blue stroma
    whose texture is fine and low in contrast (fibres +-9 %, a +-6 %
    grain), soft crypts (-12 %), a faint lighter collarette (+7 %, not a
    white ring) round a slightly aqua pupillary zone, a broad darkening over
    the outer third and a soft dark limbal ring over the last ~9 % of the
    radius."""
    col = np.broadcast_to(IRIS_BASE_V12, rho.shape + (3,)).copy()
    fib = f["fib"] - 0.5
    col = col * (1.0 + 0.18 * fib)[..., None]
    col = col * (1.0 + 0.12 * (f["fine2"] - 0.5))[..., None]
    col = col * (0.94 + 0.12 * f["sector"])[..., None]
    col = col * (0.95 + 0.10 * f["mot"])[..., None]
    pz = (1.0 - smoothstep(f["rc"] - 0.08, f["rc"] + 0.02, rho))[..., None]
    col = col * (1.0 - 0.35 * pz) + (col * np.array([0.98, 1.06, 0.96])) * (0.35 * pz)
    col = col * (1.0 + 0.07 * f["coll"])[..., None]
    col = col * (1.0 - 0.12 * np.clip(f["crypt"] + 0.5 * f["cr2"], 0, 1))[..., None]
    col = col * (1.0 - 0.08 * f["furrow"])[..., None]
    col = col * (1.0 - 0.38 * smoothstep(0.62, 0.93, rho))[..., None]
    lb = smoothstep(0.90, 0.995, rho)[..., None]
    return col * (1.0 - 0.9 * lb) + IRIS_LIMBUS_V12 * (0.9 * lb)


def iris_height_mm_v12(f, rho):
    """A smooth concave iris with low relief (round 9's 0.16 mm fibres and
    0.34 mm crypts shaded as radial streaks under the key light)."""
    return (-1.20 * (1.0 - rho ** 2) + 0.10 * f["coll"] + 0.05 * (f["fib"] - 0.5) - 0.12 * f["crypt"] - 0.05 * f["cr2"]
            - 0.03 * f["furrow"] + 0.02 * (f["mot"] - 0.5))


def iris_material_v12(tex):
    """The painted stroma (T_CatBaseV6_Iris) with a crisp vesica slit
    (PUPIL_*_V12) and a thin dark pupillary ruff along it. The iris has no
    specular of its own (it sits in the aqueous)."""
    m, nt = v6.new_mat("M_CatBaseV6_IrisV12")
    out = N(nt, "ShaderNodeOutputMaterial", (1500, 0))
    bs = N(nt, "ShaderNodeBsdfPrincipled", (1000, 150))
    uvt = N(nt, "ShaderNodeUVMap", (-900, 300))
    uvt.uv_map = "IrisTex"
    ti = N(nt, "ShaderNodeTexImage", (-650, 300))
    ti.image = tex
    ti.interpolation = "Cubic"
    L(nt, uvt.outputs["UV"], ti.inputs["Vector"])
    bs.inputs["Roughness"].default_value = 0.80
    bs.inputs["Specular IOR Level"].default_value = 0.0
    uv = N(nt, "ShaderNodeUVMap", (-900, -200))
    uv.uv_map = "IrisXY"
    sep = N(nt, "ShaderNodeSeparateXYZ", (-700, -200))
    L(nt, uv.outputs["UV"], sep.inputs["Vector"])
    yy = _math(nt, "DIVIDE", sep.outputs["Y"], PUPIL_H_V12, (-500, -300))
    om = _math(nt, "SUBTRACT", 1.0, _math(nt, "MULTIPLY", yy, yy, (-350, -300)), (-200, -300), clamp=True)
    hw = _math(nt, "MULTIPLY", _math(nt, "POWER", om, PUPIL_EXP_V12, (-100, -300)), PUPIL_W0_V12, (0, -300))
    dd = _math(nt, "SUBTRACT", _math(nt, "ABSOLUTE", sep.outputs["X"], None, (-350, -150)), hw, (150, -200))
    # beyond the tips the slit distance is the distance to the tip
    ay = _math(nt, "ABSOLUTE", sep.outputs["Y"], None, (-350, -450))
    beyond = _math(nt, "SUBTRACT", ay, PUPIL_H_V12, (-200, -450))
    dd = _math(nt, "MAXIMUM", dd, beyond, (300, -250))
    pm = _maprange(nt, dd, -PUPIL_FEATHER_V12, PUPIL_FEATHER_V12, 1.0, 0.0, (450, -200), smooth=True)
    ru = _maprange(nt, dd, 0.0, RUFF_V12, 0.55, 1.0, (450, 50), smooth=True)
    mul = N(nt, "ShaderNodeVectorMath", (650, 250))
    mul.operation = "SCALE"
    L(nt, ti.outputs["Color"], mul.inputs[0])
    L(nt, ru, mul.inputs["Scale"])
    L(nt, mul.outputs["Vector"], bs.inputs["Base Color"])
    black = N(nt, "ShaderNodeBsdfPrincipled", (1000, -250))
    black.inputs["Base Color"].default_value = (0.002, 0.0022, 0.0025, 1.0)
    black.inputs["Roughness"].default_value = 1.0
    black.inputs["Specular IOR Level"].default_value = 0.0
    mx = N(nt, "ShaderNodeMixShader", (1250, 0))
    L(nt, pm, mx.inputs["Fac"])
    L(nt, bs.outputs["BSDF"], mx.inputs[1])
    L(nt, black.outputs["BSDF"], mx.inputs[2])
    L(nt, mx.outputs["Shader"], out.inputs["Surface"])
    return m


# round-9 review: "a milky softbox blob in the right iris (Studio
# CloseFront) reads as a cataract". The cornea is transparent to shadow rays
# (round 4), so the iris already receives the key light straight through it;
# diffuse rays leaving the iris were also refracted by the glass, so the key
# light reached the iris a second time, focused by the dome into a bright,
# soft oval. Diffuse rays now pass the cornea like shadow rays.
CORNEA_ROUGH_V12 = 0.006  # round 9: 0.015 (the catchlight spread into a haze)
TEAR_BUMP_V12 = 0.00008  # m; round 9: 0.00022 (a wobbling reflection)


def cornea_material_v12():
    """Round-9 cornea (Fresnel-only reflection over clear glass, IOR 1.376,
    a faint tear-film height) with the diffuse-ray pass-through above, a
    smaller tear-film height and a crisper reflection."""
    m = v11.cornea_material_v11()
    m.name = "M_CatBaseV6_CorneaV12"
    nt = m.node_tree
    for nd in nt.nodes:
        if nd.type == "BUMP":
            nd.inputs["Distance"].default_value = TEAR_BUMP_V12
        if nd.type == "BSDF_GLOSSY":
            nd.inputs["Roughness"].default_value = CORNEA_ROUGH_V12
    out = next(nd for nd in nt.nodes if nd.type == "OUTPUT_MATERIAL")
    mx = out.inputs["Surface"].links[0].from_node
    lp = mx.inputs["Fac"].links[0].from_node
    either = _math(nt, "MAXIMUM", lp.outputs["Is Shadow Ray"], lp.outputs["Is Diffuse Ray"], (500, 300))
    L(nt, either, mx.inputs["Fac"])
    return m


# ---------------------------------------------------------------------------
# Eyes: lid margin, tear line, caruncle, nictitans (round 10)
# ---------------------------------------------------------------------------

def lid_margin_material_v12():
    """Round-8 margin sheet recoloured: pigmented near-black at the contact,
    dark charcoal outward (round 9 turned grey, 0.085-0.105, beyond ~0.9 mm,
    and wherever the fur did not cover it that grey read as a second line
    inside the black rim), wet only along the contact."""
    m = v10.lid_margin_material_v10()
    m.name = "M_CatBaseV6_LidMarginV12"
    nt = m.node_tree
    cr = next(nd for nd in nt.nodes if nd.type == "VALTORGB")
    ramp = cr.color_ramp
    while len(ramp.elements) > 2:
        ramp.elements.remove(ramp.elements[1])
    ramp.elements[0].position = 0.0
    ramp.elements[0].color = (0.010, 0.009, 0.009, 1)
    ramp.elements[1].position = 1.0
    ramp.elements[1].color = (0.042, 0.039, 0.037, 1)
    e = ramp.elements.new(0.42)
    e.color = (0.013, 0.011, 0.011, 1)
    e = ramp.elements.new(0.66)
    e.color = (0.026, 0.024, 0.023, 1)
    for nd in nt.nodes:
        if nd.type == "MAP_RANGE" and abs(nd.inputs["To Min"].default_value - 0.8) < 1e-6:
            nd.inputs["From Max"].default_value = 0.10  # the clear coat only on the contact (round 9: to 0.16)
    return m


def margin_width_v12(t, low, side):
    """Visible margin width factor round the fissure (t: -1 medial .. +1
    lateral). Round 9 was nearly uniform (0.55-1.0 by the canthus taper only)
    and read as an eyeliner gasket; a real margin is widest at the medial
    canthus and along the medial lower lid (where the lacrimal line leaves
    it), thin along the lateral upper lid, and irregular."""
    base = 0.55 + 0.45 * np.sqrt(np.clip(1.0 - t ** 4, 0.0, 1.0))
    medial = np.where(low, 0.30, 0.12) * smoothstep(0.2, -0.9, t)
    lat_up = np.where(low, 0.0, 0.32) * smoothstep(0.0, 0.8, t)
    rng = np.random.default_rng(v6.RNG_SEED + (5 if side > 0 else 9))
    ph = rng.random(3) * 2 * math.pi
    s_ = np.linspace(0.0, 2 * math.pi, len(t), endpoint=False)
    wob = 0.10 * np.sin(3 * s_ + ph[0]) + 0.07 * np.sin(7 * s_ + ph[1]) + 0.05 * np.sin(13 * s_ + ph[2])
    return base * (1.0 + medial - lat_up + wob) * np.where(low, 0.92, 1.0)


TEAR_R_V12 = 0.085 * MM  # round 9: 0.14 mm, a continuous grey line along both lower lids


def tear_meniscus_mesh(name, pts, radius, seed, segs=8):
    """A thin clear fillet along the lower-lid contact whose radius tapers at
    both ends and varies along the lid (a uniform tube read as a drawn
    line)."""
    n = len(pts)
    rng = np.random.default_rng(seed)
    s_ = np.linspace(0.0, 1.0, n)
    ph = rng.random(2) * 2 * math.pi
    rad = radius * np.sin(np.pi * s_) ** 0.6 * (0.65 + 0.35 * np.sin(9 * s_ * np.pi + ph[0]) ** 2) * (0.85 + 0.15 * np.sin(23 * s_ + ph[1]))
    bm = bmesh.new()
    rings = []
    for i in range(n):
        p = pts[i]
        tg = pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]
        tg /= np.linalg.norm(tg)
        a = np.cross(tg, [0, 0, 1.0])
        if np.linalg.norm(a) < 1e-6:
            a = np.cross(tg, [0, 1.0, 0])
        a /= np.linalg.norm(a)
        b = np.cross(tg, a)
        r = max(float(rad[i]), 0.004 * MM)
        rings.append([bm.verts.new(p + r * (math.cos(2 * math.pi * k / segs) * a + math.sin(2 * math.pi * k / segs) * b)) for k in range(segs)])
    for i in range(n - 1):
        r0, r1 = rings[i], rings[i + 1]
        for k in range(segs):
            bm.faces.new((r0[k], r0[(k + 1) % segs], r1[(k + 1) % segs], r1[k]))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p_ in me.polygons:
        p_.use_smooth = True
    return me


def build_lid_margins_v12(coll, parent, n=720):
    """Round-8 margin sheet (finely sampled, relaxed, riding over the lid
    skin and tucking under it) with the round-10 width profile
    (margin_width_v12), the darker sheet material, and a thinner, broken
    tear meniscus along the lower lid."""
    mat = lid_margin_material_v12()
    tear = bpy.data.materials.get("M_CatBaseV6_Tear")
    if tear is not None:
        bs_ = next((nd for nd in tear.node_tree.nodes if nd.type == "BSDF_PRINCIPLED"), None)
        if bs_ is not None:
            bs_.inputs["Roughness"].default_value = 0.02
    objs = []
    A_S = np.array([0.0, 0.2, 0.45, 0.8, 1.3, 1.9, 2.4, 2.9]) * MM
    uu, low = v8.outline_params(n)
    t = uu / 0.999
    for s, tag in ((1.0, "L"), (-1.0, "R")):
        P, Nn = v7.eye_surface_outline(s, n)
        m = len(P)
        cen = P.mean(0)
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
        wf = margin_width_v12(t, low, s)
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
        sel = np.nonzero(low & (np.abs(t) < 0.80))[0]
        sel = sel[np.argsort(t[sel])]
        pts = P[sel] + Nn[sel] * 0.05 * MM + O[sel] * 0.04 * MM * wf[sel][:, None]
        tube = tear_meniscus_mesh(f"CatBaseV6_Eye{tag}_TearMeniscus", pts, TEAR_R_V12, v6.RNG_SEED + (3 if s > 0 else 4))
        tob = v6.link(bpy.data.objects.new(tube.name, tube), coll)
        if tear is not None:
            tube.materials.append(tear)
        tob.parent = parent
        tob.matrix_world = Matrix.Translation(v6.HEAD_ORIGIN) if parent is not None and parent.type != "EMPTY" else Matrix.Identity(4)
        objs.append(tob)
    return objs


# round-9 review: "a saturated red speck at the left medial canthus" (round
# 8's caruncle, (0.44, 0.20, 0.19) under a clear coat) and "in Overcast
# CloseThreeQuarter the near eye has a dark triangular void at the medial
# canthus ... the eyeball does not fill the socket". A cat's caruncle is
# small and pigmented, and the leading edge of the third eyelid
# (nictitans) lies in the medial canthus over the globe: a dark,
# pigmented, wet crescent.
CARUNCLE_COLOUR_V12 = (0.16, 0.095, 0.088)
NICTITANS_U_V12 = (-1.03, -0.70)  # canthal coordinate range (fraction of the half-width) the membrane covers
NICTITANS_EDGE_V12 = (0.80, 0.10)  # leading edge at uu/hw = -(a + b (ww/wmax)^2)


def nictitans_material():
    m, nt = v6.new_mat("M_CatBaseV6_Nictitans")
    out = N(nt, "ShaderNodeOutputMaterial", (700, 0))
    bs = N(nt, "ShaderNodeBsdfPrincipled", (400, 0))
    at = N(nt, "ShaderNodeAttribute", (-400, 0))
    at.attribute_name = "nict_t"
    c = v6.mix_rgb(nt, at.outputs["Fac"], (0.030, 0.024, 0.022), (0.14, 0.095, 0.090), (100, 100))
    L(nt, c, bs.inputs["Base Color"])
    bs.inputs["Roughness"].default_value = 0.25
    bs.inputs["Coat Weight"].default_value = 0.7
    bs.inputs["Coat Roughness"].default_value = 0.03
    bs.inputs["Subsurface Weight"].default_value = 0.10
    bs.inputs["Subsurface Scale"].default_value = 0.0006
    L(nt, bs.outputs["BSDF"], out.inputs["Surface"])
    return m


def build_nictitans(coll, parent):
    """The third eyelid's leading edge in each medial canthus: a thin sheet
    0.12 mm above the eye surface (globe or corneal dome, the outer), from
    the medial canthus to a crescent edge ~15 % of the fissure width into
    the aperture; its far side runs under both lids. nict_t: 0 at the
    pigmented edge, 1 toward the canthus."""
    mat = nictitans_material()
    cd = v6.cornea_dims()
    cc_off = cd["apex"] - cd["Rc"]
    hw = 0.5 * A.fissure_w
    tl = math.radians(A.fissure_tilt)
    objs = []
    nu, nw = 28, 36
    for s, tag in ((1.0, "L"), (-1.0, "R")):
        Gf = v6.gaze_frame(s)
        ec = v6.eye_center(s)
        up0, lo0 = v6.fissure_curves(np.array(-0.80 * hw))
        wmax = max(float(up0), -float(lo0)) + 3.0 * MM
        ws = np.linspace(-wmax, wmax, nw)
        V, T = [], []
        for w_ in ws:
            edge = -(NICTITANS_EDGE_V12[0] + NICTITANS_EDGE_V12[1] * (w_ / wmax) ** 2) * hw
            for k in range(nu):
                a = k / (nu - 1)
                uu = NICTITANS_U_V12[0] * hw + (edge - NICTITANS_U_V12[0] * hw) * a
                u = uu * math.cos(tl) - w_ * math.sin(tl)
                w = uu * math.sin(tl) + w_ * math.cos(tl)
                r2 = u * u + w * w
                xg = math.sqrt(max((A.eye_r + 0.12 * MM) ** 2 - r2, 1e-10))
                xc = cc_off + math.sqrt(max((cd["Rc"] + 0.12 * MM) ** 2 - r2, 1e-10))
                V.append(ec + Gf @ np.array([max(xg, xc), u * s, w]))
                T.append(1.0 - a)
        V = np.array(V) @ v6.head_R().T
        faces = []
        for i in range(nw - 1):
            for k in range(nu - 1):
                a0 = i * nu + k
                faces.append((a0, a0 + 1, a0 + nu + 1, a0 + nu))
        me = bpy.data.meshes.new(f"CatBaseV6_Eye{tag}_Nictitans")
        me.from_pydata(V.tolist(), [], faces)
        me.update()
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        # normals away from the globe centre
        cen_w = Vector(ec @ v6.head_R().T)
        bm.faces.ensure_lookup_table()
        f0 = bm.faces[len(bm.faces) // 2]
        if f0.normal.dot(f0.calc_center_median() - cen_w) < 0:
            bmesh.ops.reverse_faces(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()
        at = me.attributes.new("nict_t", "FLOAT", "POINT")
        tt = np.array(T)
        at.data.foreach_set("value", smoothstep(0.0, 0.35, tt).astype(np.float32))
        for p_ in me.polygons:
            p_.use_smooth = True
        me.materials.append(mat)
        ob = v6.link(bpy.data.objects.new(me.name, me), coll)
        ob.parent = parent
        ob.matrix_world = Matrix.Translation(v6.HEAD_ORIGIN)
        objs.append(ob)
    return objs


# ---------------------------------------------------------------------------
# Skin stage: silhouette, nape, throat, bust (round 10)
# ---------------------------------------------------------------------------

# round-9 review, 3 m: "in front view the sides run near-vertical and
# parallel from temple to jowl, and the jowls sag straight into the neck
# with no jaw or chin break ... the ThreePoint Front rim light exposes lumps
# at eye level". Round 9's zygomatic fill (2.8 mm at world-local z +1, the
# eye's level is z ~ +5) made the lumps; its 5 mm neck outset (z -126..-92)
# filled the notch under the jowl (skin neck/cheek 0.93). World-local mm.
CHEEK_V12 = dict(amp=1.8, z0=-14.0, sz=14.0, x0=10.0, sx=34.0, y=(70.0, 92.0))  # outset under the eye, not at its level
TEMPLE_TAPER_V12 = dict(amp=2.0, z0=24.0, sz=12.0, x0=-10.0, sx=30.0, y=(72.0, 94.0))
JOWL_TAPER_V12 = dict(amp=3.5, z=(-78.0, -40.0), y=(66.0, 90.0), x=(-30.0, 95.0))
NECK_NOTCH_V12 = dict(amp=2.0, z=(-112.0, -80.0), y=(38.0, 70.0), x=80.0)
# round-9 review: "the nape shows a double hump ... the occiput and then a
# separate roll at the neck base with a concavity between". The skin's back
# profile has a 9 mm nape dip at z -72 (round 7/8, NAPE_DIP_V10) and then a
# step at the neck base; the dip is halved and the step filled.
NAPE_DIP_V12 = 4.5
NAPE_FILL_V12 = dict(amp=3.0, z0=-115.0, sz=18.0)


def fur_inset_mm_v12(Pw_mm):
    """Round-8 insets (v10.fur_inset_mm_v10 with the nape dip halved) plus the
    round-10 silhouette: an outset under the eye (the widest cheek at z ~
    -15, above the mouth), a taper at the temples and at the jowls, a notch
    under the jaw, and a nape fill that makes the occiput-to-withers line
    continuous."""
    t = v11._V10_INSET(Pw_mm)
    x, y, z = Pw_mm[..., 0], np.abs(Pw_mm[..., 1]), Pw_mm[..., 2]

    def gauss(c):
        return np.exp(-((z - c["z0"]) / c["sz"]) ** 2 - ((x - c["x0"]) / c["sx"]) ** 2) * smoothstep(c["y"][0], c["y"][1], y)

    cheek = gauss(CHEEK_V12)
    temple = gauss(TEMPLE_TAPER_V12)
    j = JOWL_TAPER_V12
    jowl = _bump(z, j["z"][0], j["z"][1]) * smoothstep(j["y"][0], j["y"][1], y) * _bump(x, j["x"][0], j["x"][1])
    nn = NECK_NOTCH_V12
    notch = _bump(z, nn["z"][0], nn["z"][1]) * smoothstep(nn["y"][0], nn["y"][1], y) * (1.0 - smoothstep(nn["x"] - 20.0, nn["x"], x))
    nf = NAPE_FILL_V12
    nape = np.exp(-((z - nf["z0"]) / nf["sz"]) ** 2) * smoothstep(-40.0, -90.0, x) * (1.0 - smoothstep(40.0, 80.0, y))
    return (t - CHEEK_V12["amp"] * cheek + TEMPLE_TAPER_V12["amp"] * temple + j["amp"] * jowl + nn["amp"] * notch
            - nf["amp"] * nape)


# the biped bust, sculpted from anatomy (round-9 review: "the shoulders are
# primitive caps with no clavicle, deltoid or pectoral structure ... the
# Front frames show the torso wider on screen than round 8"). Round 9: the
# shoulder joint at |y| 122, the elbow at |y| 140, a 33 x 30 x 46 mm cap and
# a 33 -> 27 mm upper arm (skin half-width 160 mm at the shoulders). World-
# local mm before the bust offset (BUST_DX, BUST_DZ).
SHOULDER_V12 = (-24.0, 108.0, -222.0)
ELBOW_V12 = (-36.0, 124.0, -470.0)
WRIST_DIR_V12 = (-16.0, 118.0, -660.0)
ARM_R_V12 = (27.0, 23.0, 23.0, 20.5)
RIBCAGE_V12 = (84.0, 88.0, 116.0)  # radii (round 9: 90, 102, 118)
ACROMION_V12 = (-16.0, 100.0, -192.0)
DELTOID_INSERT_V12 = (-28.0, 118.0, -312.0)
BUST_DX_V12 = -6.0  # round 9: -12; the chest comes 6 mm forward under the head
THROAT_V12 = ((40.0, 0.0, -128.0), (28.0, 36.0, 34.0))  # round 9: (52, 0, -120), (32, 40, 38): the throat was flush with the chin


def build_bust_ops_v12():
    """Round 10 bust: clavicles from the manubrium to the acromion, a
    trapezius sloping from the neck into the acromion, the scapular blade, a
    deltoid that tapers from the acromion to its insertion on the humerus
    (not a round cap), the humeral head under it, an upper arm with biceps
    and triceps bellies, the elbow and the top of the forearm; a pectoral
    fanning from the sternum toward the humerus; a narrower ribcage and
    thorax; a slimmer neck base; a throat set back behind the chin."""
    R = v6.rot_matrix
    dx, dz = BUST_DX_V12, v9.BUST_DZ

    def p(x, y, z):
        return (x + dx, y, z + dz)

    ops = []
    # the torso first: its wide blends must not fill in round the arms
    ops.append(v6.cap_op(p(-24.0, 0.0, -104.0), p(-40.0, 0.0, -190.0), 64.0, 82.0, 32, frame="body"))  # neck base (round 9: 72 -> 86)
    ops.append(v6.ell_op(p(52.0, 0.0, -172.0), (24.0, 22.0, 42.0), None, 24, frame="body"))  # keel
    ops.append(v6.ell_op(THROAT_V12[0], THROAT_V12[1], None, 24, frame="body"))  # throat, set back
    ops.append(v6.ell_op(p(-30.0, 0.0, -240.0), RIBCAGE_V12, None, 34, frame="body"))  # ribcage
    ops.append(v6.ell_op(p(-34.0, 0.0, -330.0), (88.0, 80.0, 290.0), None, 44, frame="body"))  # thorax and waist
    sx, sy, sz = SHOULDER_V12
    ex_, ey, ez = ELBOW_V12
    wx, wy, wz = WRIST_DIR_V12
    ax, ay_, az = ACROMION_V12
    ix, iy, iz = DELTOID_INSERT_V12
    for s in (1.0, -1.0):
        ops.append(v6.cap_op(p(-60.0, 22.0 * s, -106.0), p(ax - 16.0, (ay_ - 8.0) * s, az + 4.0), 22.0, 25.0, 30, frame="body"))  # trapezius
        ops.append(v6.ell_op(p(-76.0, 48.0 * s, -188.0), (9.0, 26.0, 48.0), R(roll=-22.0 * s, pitch=-8.0), 28, frame="body"))  # scapular blade
        ops.append(v6.cap_op(p(40.0, 14.0 * s, -160.0), p(ax + 6.0, (ay_ - 4.0) * s, az - 2.0), 7.5, 8.5, 10, frame="body"))  # clavicle
        ops.append(v6.ell_op(p(sx, sy * s, sz), (24.0, 22.0, 25.0), None, 14, frame="body"))  # humeral head
        ops.append(v6.cap_op(p(ax, ay_ * s, az - 8.0), p(ix, iy * s, iz), 26.0, 11.0, 12, frame="body"))  # deltoid, tapering to its insertion
        ops.append(v6.cap_op(p(sx, sy * s, sz - 6.0), p(ex_, ey * s, ez), ARM_R_V12[0], ARM_R_V12[1], 12, frame="body"))  # upper arm
        ops.append(v6.ell_op(p(sx + 18.0, (sy + 4.0) * s, -330.0), (15.0, 15.0, 70.0), None, 10, frame="body"))  # biceps belly
        ops.append(v6.ell_op(p(sx - 20.0, (sy + 8.0) * s, -345.0), (16.0, 15.0, 78.0), None, 10, frame="body"))  # triceps
        ops.append(v6.ell_op(p(ex_ - 7.0, ey * s, ez), (22.0, 20.0, 24.0), None, 9, frame="body"))  # elbow, olecranon
        ops.append(v6.cap_op(p(ex_, ey * s, ez - 8.0), p(wx, wy * s, wz), ARM_R_V12[2], ARM_R_V12[3], 9, frame="body"))  # forearm top
        ops.append(v6.ell_op(p(22.0, 42.0 * s, -206.0), (24.0, 42.0, 38.0), R(yaw=18.0 * s, roll=-10.0 * s), 24, frame="body"))  # pectoral
        ops.append(v6.ell_op(p(4.0, 80.0 * s, -214.0), (16.0, 24.0, 22.0), R(yaw=30.0 * s, roll=-18.0 * s), 14, frame="body"))  # pectoral toward the humerus
    return ops


def build_bust_field_v12(vs=2.0 * MM):
    t0 = time.time()
    lo = np.floor(v6.DOMAIN_MIN / vs).astype(int) - 4
    hi = np.ceil(v6.DOMAIN_MAX / vs).astype(int) + 4
    shape = tuple(hi - lo + 1)
    xs = [np.arange(lo[a], hi[a] + 1) * vs for a in range(3)]
    ops = build_bust_ops_v12()
    Bf = np.empty(shape, np.float32)
    for a in range(shape[0]):
        J, K = np.meshgrid(xs[1], xs[2], indexing="ij")
        P = np.stack([np.full_like(J, xs[0][a]), J, K], -1).reshape(-1, 3)
        f = np.full(len(P), 0.2)
        f = v6.apply_ops(ops, P, f)
        f = v6.smax(f, -(P[:, 2] + 0.600), 12 * MM)
        Bf[a] = f.reshape(J.shape)
    Bb = v6.gaussian_blur3(Bf, 4)
    log(f"bust field v12 {shape} ({time.time()-t0:.0f}s)")
    return Bb, lo * vs


# ---------------------------------------------------------------------------
# Detail ops: muzzle, whisker pads, mouth, chin, bridge (round 10)
# ---------------------------------------------------------------------------

# round-9 review: "the white muzzle is a painted, hard-edged mask. In
# profile it reads as a separate glued-on block, with a crease behind the
# whisker pad. The whisker pads lack volume. There is no upper-lip or mouth
# line and the chin is vestigial. The nose leather is ... undersized, with
# no darker rim or nostril flare."
PAD_H_V12 = 3.4  # mm (round 9: 2.6)
PAD_R_V12 = (12.5, 10.0)  # mm (round 9: 11.5, 9.0)
PAD_BACK_V12 = dict(h=1.3, c=(102.0, 22.0, -24.0), r=(16.0, 13.0, 12.0))  # head mm (x before the muzzle shift): fills the crease behind the pad
CHIN_H_V12 = 2.4  # mm (round 9: 1.2, the vestigial chin)
BRIDGE_V12 = dict(h=1.6, x=(86.0, 118.0), z=(8.0, 34.0), sy=12.0)  # the nasal bridge between the eyes (the far eye bulged past it)
LEATHER_SCALE_V12 = 1.12  # the leather 12 % larger about its centre (round 6 scaled it 0.8)
ALAR_H_V12 = 2.1  # mm (round 9: 1.5): the alar fold flares beside each naris
UPPER_LIP_V12 = [(0.0, -20.0), (1.8, -21.2), (3.8, -22.6), (5.6, -23.6), (8.4, -25.0), (11.4, -26.8), (14.4, -29.2), (17.0, -31.8)]
UPPER_LIP_W_V12 = [0.34, 0.34, 0.32, 0.30, 0.28, 0.26, 0.22, 0.14]
UPPER_LIP_D_V12 = [1.3, 1.3, 1.2, 1.1, 1.0, 0.9, 0.7, 0.3]


def build_detail_ops_v12():
    """Round-8 detail ops (with the round-10 pad, chin and alar constants
    already set on their modules) plus: a broad low fill behind each whisker
    pad, a higher nasal bridge between the eyes, and a deeper upper-lip line
    running from the philtrum out under the pads."""
    ops = v10.build_detail_ops_v10()
    mz = A.mz
    K_REL = v10.K_REL
    for s in (1.0, -1.0):
        def pad_back(P, B, s_=s):
            x, y, z = P[..., 0] / MM, P[..., 1] / MM, P[..., 2] / MM
            c, r = PAD_BACK_V12["c"], PAD_BACK_V12["r"]
            w = np.exp(-((x - c[0] - mz) / r[0]) ** 2 - ((y - c[1] * s_) / r[1]) ** 2 - ((z - c[2]) / r[2]) ** 2)
            return B - PAD_BACK_V12["h"] * MM * w

        c = PAD_BACK_V12["c"]
        ylo, yhi = sorted(((c[1] - 40.0) * s, (c[1] + 40.0) * s))
        ops.append(v6.Op("union", pad_back, v6.v(c[0] + mz - 45.0, ylo, c[2] - 40.0), v6.v(c[0] + mz + 45.0, yhi, c[2] + 40.0), K_REL))
    br = BRIDGE_V12

    def bridge(P, B):
        x, y, z = P[..., 0] / MM, P[..., 1] / MM, P[..., 2] / MM
        w = np.exp(-(y / br["sy"]) ** 2) * _bump(x, br["x"][0], br["x"][1]) * _bump(z, br["z"][0], br["z"][1])
        return B - br["h"] * MM * w

    ops.append(v6.Op("union", bridge, v6.v(br["x"][0] - 20.0, -40.0, br["z"][0] - 15.0), v6.v(br["x"][1] + 20.0, 40.0, br["z"][1] + 15.0), K_REL))
    for s in (1.0, -1.0):
        poly = [(y * s, z) for y, z in UPPER_LIP_V12]
        ops.append(v6.groove_op(poly, (1, 2), 0, 96.0 + mz, 185.0 + mz, UPPER_LIP_W_V12, UPPER_LIP_D_V12, 0.5))
    return ops


def scale_leather_v12():
    """The nose leather, nostrils and alar folds LEATHER_SCALE_V12 larger about
    the leather centre; the philtrum starts at the new lower edge."""
    lh = np.asarray(v6.LEATHER_HALF, float)
    zc = 0.5 * (lh[:, 1].max() + lh[:, 1].min())
    c = (0.0, zc)
    zb_old = lh[:, 1].min()
    v6.LEATHER_HALF = v8.scale_about(v6.LEATHER_HALF, c, LEATHER_SCALE_V12)
    v6.NOSTRIL_POLY = v8.scale_about(v6.NOSTRIL_POLY, c, LEATHER_SCALE_V12)
    v6.ALAR_POLY = v8.scale_about(v6.ALAR_POLY, c, LEATHER_SCALE_V12)
    v6.NOSTRIL_W = [w * 1.10 for w in v6.NOSTRIL_W]
    zb = zc + (zb_old - zc) * LEATHER_SCALE_V12
    ph = list(v6.PHILTRUM)
    ph[0] = (0.0, ph[0][1] + (zb - zb_old))
    ph[1] = (0.0, ph[1][1] + (zb - zb_old))
    v6.PHILTRUM = ph


# ---------------------------------------------------------------------------
# Markings (round 10)
# ---------------------------------------------------------------------------

# round-9 review: "the forehead M is a heavy stencilled V with a central
# bar, and the cheek and mascara bars are uniform-width painted strokes".
# The M is now four thin strokes per side (two legs and two inner lines)
# over a thin, broken central line; the crown lines are narrower; every
# stroke's width swells and thins along it, and the mascara line and the
# cheek bars taper and break.
MARKINGS_V12 = [
    ("m_outer", [(92, 34, 41), (88, 30, 47), (84, 25, 53), (80, 20, 59), (77, 17, 62)], [0.7, 1.4, 1.7, 1.3, 0.8]),
    ("m_outer2", [(90, 27, 44), (86, 23, 50), (82, 19, 56)], [0.6, 1.1, 0.7]),
    ("m_inner", [(78, 14, 62), (82, 10, 57), (85, 7, 53), (88, 4, 49)], [0.9, 1.2, 1.0, 0.6]),
    ("m_center", [(90, 0, 47), (85, 0, 54), (78, 0, 62), (64, 0, 72), (46, 0, 78), (20, 0, 81), (-8, 0, 77), (-38, 0, 65), (-64, 0, 44)],
     [0.5, 1.1, 1.5, 1.9, 2.2, 2.5, 2.6, 2.5, 2.3]),
    ("fore_a", [(80, 12, 60), (66, 12, 68), (48, 13, 75), (26, 14, 79), (2, 15, 78), (-24, 16, 71), (-50, 17, 57)],
     [0.9, 1.6, 2.0, 2.2, 2.2, 2.0, 1.6]),
    ("fore_b", [(84, 24, 50), (72, 24, 60), (56, 25, 68), (36, 26, 74), (14, 27, 76), (-8, 28, 72)], [0.8, 1.4, 1.8, 1.8, 1.5, 1.0]),
    ("fore_c", [(80, 36, 48), (68, 35, 58), (52, 34, 66), (34, 34, 72), (14, 35, 74)], [0.7, 1.2, 1.5, 1.3, 0.8]),
    ("mascara", [(69, 59, 23), (61, 66, 21), (51, 73, 17), (40, 79, 12), (28, 83, 7), (16, 84, 2)], [0.6, 1.5, 2.1, 1.6, 1.9, 0.8]),
    ("cheek2", [(78, 56, 4), (66, 65, -1), (53, 73, -7), (40, 79, -12), (27, 81, -15), (15, 79, -16)], [0.5, 1.3, 1.9, 1.2, 1.6, 0.6]),
    ("cheek3", [(70, 61, -17), (58, 69, -22), (46, 74, -27), (33, 76, -31), (21, 74, -33)], [0.4, 1.2, 1.5, 1.0, 0.5]),
    ("lacrimal", [(88, 18.5, 14), (95, 16.5, 7), (102, 15.0, 0), (108, 14.0, -5)], [0.8, 0.75, 0.65, 0.4]),
]
MARK_EDGE_V12 = 0.85  # mm (round 9: 0.45, a stencil edge); the per-hair stripe choice turns the ramp into a ticked edge
STRIPE_CORE_V12 = 0.86  # at most 86 % of the hairs in a head stroke are stripe hairs (round 9: 100 %)


# ---------------------------------------------------------------------------
# Coat and groom fields (round 10)
# ---------------------------------------------------------------------------

WHITE_EDGE_V12 = 1.5  # mm half-width of the face white edge (round 9: 0.35, a painted mask)
SPECTACLE_V12 = 0.45  # pale ring round the eyes (round 9: 0.20; the eye mask read as flat grey patches)
EAR_INNER_WHITE_V12 = 0.62  # fraction of white hairs on the inner pinna (round 9: all white, invisible on pink)
EAR_WRAP_V12 = 0.40  # back-coat darkness wrapping over the inner margin (round 9: 0.75 x, a dark outline)
ARM_BAND_V12 = dict(keep=0.70, lateral=(-0.2, 0.5))  # arm bars: broken, lateral only (round 9: full rings = knitwear)


def arm_weight_v12(Pw):
    """~1 on the arm (within ~8 mm of the skin round the shoulder-elbow-
    forearm axis, below the deltoid), 0 on the torso (world-local m in)."""
    P = np.asarray(Pw, float) / MM
    dx, dz = BUST_DX_V12, v9.BUST_DZ
    w = np.zeros(len(P))
    for s in (1.0, -1.0):
        pts = [np.array([SHOULDER_V12[0] + dx, SHOULDER_V12[1] * s, SHOULDER_V12[2] + dz]),
               np.array([ELBOW_V12[0] + dx, ELBOW_V12[1] * s, ELBOW_V12[2] + dz]),
               np.array([WRIST_DIR_V12[0] + dx, WRIST_DIR_V12[1] * s, WRIST_DIR_V12[2] + dz])]
        d = np.full(len(P), 1e3)
        for a, b in zip(pts[:-1], pts[1:]):
            e = b - a
            t = np.clip(((P - a) @ e) / (e @ e), 0.0, 1.0)
            d = np.minimum(d, np.linalg.norm(P - (a + t[:, None] * e), axis=1))
        w = np.maximum(w, (1.0 - smoothstep(ARM_R_V12[0] + 4.0, ARM_R_V12[0] + 14.0, d)) * smoothstep(-215.0, -250.0, P[:, 2]))
    return w


def _face_white_v12(Pw, Nw, x, y, z, ay, zw, earm):
    """Soft-edged face white (the round-8 muzzle, blaze, chin and throat
    masks and round 9's white cheeks, head frame mm) with a ~3 mm feathered,
    lobed edge in place of round 9's 0.7 mm painted edge."""
    mz = A.mz
    muz = np.sqrt(((x - 124 - mz) / 32) ** 2 + (y / 40) ** 2 + ((z + 33) / 27) ** 2)
    d = (muz - 1.0) * 26.0
    muz2 = np.sqrt(((x - 126.0 - mz) / 34.0) ** 2 + (y / 45.0) ** 2 + ((z + 27.0) / 30.0) ** 2)
    d = np.minimum(d, (muz2 - 1.0) * 26.0)
    wb2 = np.clip(17.0 - 0.30 * (z + 5.0), 4.0, 17.0)
    d = np.minimum(d, np.maximum(np.maximum(ay - wb2, z - 44.0), 96.0 - x))
    chin = (np.sqrt(((x - 104 - mz) / 26) ** 2 + (y / 30) ** 2 + ((z + 62) / 20) ** 2) - 1.0) * 18.0
    d = np.minimum(d, chin)
    throat = np.maximum(np.maximum(ay - 30.0 - 0.30 * np.clip(-60 - z, 0, 90), z + 56.0), 18.0 - x)
    d = np.minimum(d, throat)
    c, r = v11.CHEEK_WHITE["c"], v11.CHEEK_WHITE["r"]
    e = np.sqrt(((x - c[0]) / r[0]) ** 2 + ((ay - c[1]) / r[1]) ** 2 + ((z - c[2]) / r[2]) ** 2)
    d = np.minimum(d, (e - 1.0) * 26.0)
    hairn = (v6.fbm(Pw, 0.0009, 2, 111.0) - 0.5) * 2.2
    lobes = (v6.fbm(Pw, 0.009, 2, 112.0) - 0.5) * 5.0 + (v6.fbm(Pw, 0.024, 2, 113.0) - 0.5) * 4.0
    ew = WHITE_EDGE_V12
    return (1.0 - smoothstep(-ew, ew, d + hairn + lobes)) * (~earm)


def coat_fields_v12(Pw, Nw, ex=None):
    """Round-9 fields (coat_fields_v11 over the round-8 base, with the
    round-10 markings and edge set on their modules) and the round-10
    changes:

    - face white: a feathered, lobed ~3 mm edge (the per-hair white choice
      mixes white and agouti hairs across it) instead of a painted mask;
    - head strokes: at most STRIPE_CORE_V12 of the hairs in a stroke are
      stripe hairs, varying along the stroke, so the strokes read as ticked
      tabby marks, not stencils;
    - a paler ring round each eye (SPECTACLE_V12);
    - nose leather: a wider dark rim (0.3-2.0 mm inside the edge);
    - an upper-lip line: pigmented, bare skin along UPPER_LIP_V12;
    - inner pinna: a mix of white and silver hairs; the back coat's wrap over
      the inner margin lighter;
    - arms: broken bars on the lateral side only, a closer, shorter coat;
      w_arm splits the body layer for its own (lighter) clumping;
    - nape and neck: a continuous coat from the occiput to the withers (no
      shortened nape band, no flat head coat meeting a standing body coat),
      and a short, flat coat under the jaw so the chin break shows."""
    f = v11.coat_fields_v11(Pw, Nw, ex)
    Pw = np.asarray(Pw, float)
    Nw = np.asarray(Nw, float)
    n = len(Pw)
    is_ear, ear_t, ear_u, ear_face = v6.ex_arrays(n, ex)
    earm = is_ear > 0.5
    inner = earm & (ear_face > 0.2)
    au = np.abs(ear_u)
    Ph = Pw @ v6.head_R()
    Nh = Nw @ v6.head_R()
    x, y, z = Ph[:, 0] / MM, Ph[:, 1] / MM, Ph[:, 2] / MM
    ay = np.abs(y)
    xw, yw, zw = Pw[:, 0] / MM, Pw[:, 1] / MM, Pw[:, 2] / MM
    ayw = np.abs(yw)
    face = 1.0 - smoothstep(-75.0, -95.0, zw)
    # ---- face white, feathered (the round-8 masks' 0.35 mm edge is replaced
    # on the face; below the jaw the bib's own edge is already soft)
    wf = _face_white_v12(Pw, Nw, x, y, z, ay, zw, earm) * smoothstep(2.5, 4.0, f["d_fis"])
    white = np.where(earm, f["white"], wf * face + np.maximum(wf, f["white"]) * (1.0 - face))
    white = np.where(inner, np.minimum(f["white"], EAR_INNER_WHITE_V12), white)
    # ---- stripes: ticked cores on the head, lighter wrap on the inner margin
    head = (zw > -100.0) & (~earm)
    core = STRIPE_CORE_V12 + (1.0 - STRIPE_CORE_V12) * 0.6 * (v6.fbm(Pw, 0.012, 2, 121.0) - 0.5) * 2.0
    stripe = np.where(head, f["stripe"] * np.clip(core, 0.6, 1.0), f["stripe"])
    wrap = inner & (au > 0.88)
    stripe = np.where(wrap, stripe * (EAR_WRAP_V12 / 0.75), stripe)
    # ---- arms: broken lateral bars; the rest ground coat
    arm = arm_weight_v12(Pw) * (~earm)
    lat = smoothstep(ARM_BAND_V12["lateral"][0], ARM_BAND_V12["lateral"][1], Nw[:, 1] * np.sign(yw))
    brk = smoothstep(0.42, 0.62, v6.fbm(Pw, 0.030, 2, 131.0) + 0.25 * (v6.fbm(Pw, 0.008, 2, 132.0) - 0.5))
    stripe = stripe * (1.0 - arm) + stripe * arm * ARM_BAND_V12["keep"] * lat * brk
    # ---- pale spectacles round the eyes
    d_fis = f["d_fis"]
    spect = (1.0 - smoothstep(7.0, 12.0, d_fis)) * smoothstep(2.5, 4.5, d_fis)
    pale = np.maximum(f["pale"], SPECTACLE_V12 * spect * (~earm))
    # ---- nose leather rim, upper-lip line
    q2 = np.stack([y, z], -1)
    d_leather = v6.sd_poly2d(q2, v6.leather_poly())
    rim = np.where(earm, f["rim"], (1.0 - smoothstep(0.3, 2.0, -d_leather)) * f["nose"])
    lipd = np.full(n, 1e3)
    for s in (1.0, -1.0):
        lipd = np.minimum(lipd, v6.dist_poly2d(q2, [(yy * s, zz) for yy, zz in UPPER_LIP_V12]))
    lipf = smoothstep(104.0 + A.mz, 114.0 + A.mz, x) * smoothstep(0.0, 0.3, Nh[:, 0]) * (~earm)
    lipm = (1.0 - smoothstep(0.30, 0.70, lipd)) * lipf
    pig = np.maximum(f["pig"], 0.9 * (1.0 - smoothstep(0.35, 0.9, lipd)) * lipf)
    excl = f["excl"] * (1.0 - lipm)
    lip = np.maximum(f["lip"], lipm)
    # ---- nape: continuous coat; under the jaw: short and flat
    L = f["length"] / MM
    lift = f["lift"]
    nape = smoothstep(-0.2, -0.6, Nw[:, 0]) * (1.0 - smoothstep(35.0, 75.0, ayw)) * _bump(zw, -170.0, 10.0) * (~earm)
    Lnape = np.interp(zw, [-190.0, -120.0, -60.0, 0.0, 30.0], [15.0, 12.5, 10.0, 8.0, 7.0])
    L = L * (1.0 - nape) + Lnape * nape
    lnape = np.interp(zw, [-190.0, -120.0, -60.0, 0.0], [10.0, 8.0, 6.0, 4.0])
    lift = lift * (1.0 - nape) + lnape * nape
    under = smoothstep(0.1, 0.6, -Nh[:, 2] + 0.3 * Nh[:, 0]) * _bump(zw, -100.0, -58.0) * (1.0 - smoothstep(40.0, 70.0, ayw)) * smoothstep(0.0, 40.0, xw) * (~earm)
    L = L * (1.0 - under) + np.minimum(L, 7.0) * under
    lift = lift * (1.0 - under) + np.minimum(lift, 4.0) * under
    # arms: a shorter coat lying close (round 9 already halved it; its bars
    # read as knitwear under the body layer's 6.5 mm clumps: see GUARD_LAYERS_V12)
    f.update(arm_w=arm, white=np.clip(white, 0, 1), stripe=np.clip(stripe, 0, 1), pale=np.clip(pale, 0, 1), rim=np.clip(rim, 0, 1),
             pig=np.clip(pig, 0, 1), excl=np.clip(excl, 0, 1), lip=np.clip(lip, 0, 1), length=L * MM, lift=lift)
    return f


# Silver agouti ground hair with per-strand tip variation (round-9 review:
# "the references show fine agouti salt-and-pepper ticking that breaks up
# the stripes"). Round 9 moved every hair's ramp by +-0.07 only, so every
# hair showed the same black tip from ~78 %; the tip now starts anywhere
# from ~62 % to ~94 % of the length (+-0.15), so the surface is a fine
# mix of dark-tipped and silver hairs.
AGOUTI_V12 = [(0.0, (0.17, 0.170, 0.174)), (0.20, (0.29, 0.288, 0.283)), (0.30, (0.41, 0.405, 0.390)),
              (0.70, (0.44, 0.434, 0.418)), (0.79, (0.036, 0.036, 0.038)), (1.0, (0.020, 0.020, 0.021))]
AGOUTI_JITTER_V12 = 0.15
WHITE_JITTER_V12 = (0.74, 1.12)  # round 9: 0.86-1.10 (white fur read as uniform fleece)


_V11_HAIR = v11.hair_material_v11


def hair_material_v12(name, images, under=False, tip_alpha=True):
    """Round-9 hair (hair_material_v11) with the per-strand agouti tip
    variation and a wider per-strand value spread on white hairs."""
    m = _V11_HAIR(name, images, under, tip_alpha)
    nt = m.node_tree
    if not under:
        ramps = [nd for nd in nt.nodes if nd.type == "VALTORGB"]
        ramps.sort(key=lambda nd: -nd.location.y)
        v11._set_ramp(ramps[0], AGOUTI_V12)
    for nd in nt.nodes:
        if nd.type == "MAP_RANGE":
            lo, hi = nd.inputs["To Min"].default_value, nd.inputs["To Max"].default_value
            if abs(lo + 0.07) < 1e-6 and abs(hi - 0.07) < 1e-6 and not under:
                nd.inputs["To Min"].default_value = -AGOUTI_JITTER_V12
                nd.inputs["To Max"].default_value = AGOUTI_JITTER_V12
            if abs(lo - 0.86) < 1e-6 and abs(hi - 1.10) < 1e-6:
                nd.inputs["To Min"].default_value = WHITE_JITTER_V12[0]
                nd.inputs["To Max"].default_value = WHITE_JITTER_V12[1]
    return m


# guard layers (round-9 review: "tabby bands ring the arms like knitwear
# under strong 6.5 mm clumping ... the white fur is soft fleece"). The body
# layer's clumps are smaller; the arms get their own light-clumped layer;
# the chest bib clumps less (round 9: 0.88 at 5.5 mm).
GUARD_LAYERS_V12 = [
    ("CatBaseV6_Fur_Head", "fd_head", ((0.50, 1.5 * MM, 0.35, 0.10 * MM), (0.35, 0.7 * MM, 0.25, 0.04 * MM)), 0.10 * MM, 260.0, 0.05 * MM, (0.82, 1.18), 0.058 * MM),
    ("CatBaseV6_Fur_Body", "fd_body", ((0.66, 4.5 * MM, 0.42, 0.45 * MM), (0.50, 1.8 * MM, 0.32, 0.14 * MM), (0.30, 0.8 * MM, 0.25, 0.0)), 0.24 * MM, 100.0, 0.09 * MM, (0.7, 1.3), 0.066 * MM),
    ("CatBaseV6_Fur_Arm", "fd_arm", ((0.42, 1.6 * MM, 0.30, 0.10 * MM), (0.30, 0.7 * MM, 0.22, 0.03 * MM)), 0.12 * MM, 220.0, 0.06 * MM, (0.8, 1.2), 0.060 * MM),
    ("CatBaseV6_Fur_Chest", "fd_chest", ((0.62, 3.2 * MM, 0.45, 0.30 * MM), (0.45, 1.2 * MM, 0.30, 0.08 * MM)), 0.18 * MM, 140.0, 0.07 * MM, (0.72, 1.3), 0.062 * MM),
    ("CatBaseV6_Fur_EarBack", "fd_ear", ((0.48, 1.4 * MM, 0.32, 0.08 * MM), (0.32, 0.6 * MM, 0.25, 0.0)), 0.06 * MM, 280.0, 0.04 * MM, (0.82, 1.18), 0.052 * MM),
]
N_STRAY_V12 = 14000  # round 9: 9,000, cut by 70 % on the head (a velvet shell)
HEAD_STRAY_KEEP_V12 = 0.38  # fraction of head strays dropped (round 9: 0.70)


def build_skin_v12(coll):
    """v10.build_skin_v10 (cage, pinnae, per-layer densities) with the body
    density split into body and arm layers."""
    dense, tgt, cage = v10.build_skin_v10(coll)
    co, nr = v6.mesh_arrays(cage.data)
    ex = {k: v6.attr_array(cage.data, k) for k in v6.EAR_ATTRS}
    f = coat_fields_v12(co, nr, ex)
    body = f["density"] * f["w_body"]
    cage.data.attributes["fd_body"].data.foreach_set("value", (body * (1.0 - f["arm_w"])).astype(np.float32))
    a = cage.data.attributes.new("fd_arm", "FLOAT", "POINT")
    a.data.foreach_set("value", (body * f["arm_w"]).astype(np.float32))
    return dense, tgt, cage


def build_groom_v12(coll, skin, images, n_guides):
    """Round-8 groom (build_groom_v10) with the round-10 layers
    (GUARD_LAYERS_V12: an arm layer, smaller body clumps, a less clumped
    chest), the round-10 hair material, and more stray guard hairs on the
    head so its silhouette breaks up."""
    rng = np.random.default_rng(v6.RNG_SEED)
    S = v6.evaluated_surface(skin)
    log("groom surface tris", len(S["tv"]))

    def wfn(c, n, ex):
        f = v6.coat_fields(c, n, ex)
        return f["density"] * np.maximum(f["excl"], 0.05) / np.maximum(f["length"], 2.5 * MM)

    pos, nrm, uv, ex = v6.sample_roots(S, n_guides, wfn, rng)
    strands, f = v10.grow_guides_v10(pos, nrm, ex, 8, rng)
    v6.load_hair_assets()
    v6.length_jitter_group()
    layers = []
    cull = v6.eye_cull_group()
    gob = v6.make_curves("CatBaseV6_Fur_GuardGuides", strands, 0.064 * MM, 0.016 * MM, coll, uv=uv, surface=skin)
    gdata = gob.data
    gdata.materials.append(hair_material_v12("M_CatBaseV6_Fur_Guard", images, False, tip_alpha=True))
    bpy.data.objects.remove(gob, do_unlink=True)
    for li, (name, attr, clumps, noise, nscale, frizz, jitter, r0) in enumerate(GUARD_LAYERS_V12):
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
    ob.data.materials.append(hair_material_v12("M_CatBaseV6_Fur_Under", images, True, tip_alpha=False))
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
    # stray guard hairs: more of them on the head than round 9, a little
    # longer than the coat, so the head outline breaks up
    n_stray = N_STRAY_V12
    sp_, sn_, suv, sex = v6.sample_roots(S, n_stray, wfn, rng)
    fs = v6.coat_fields(sp_, sn_, sex)
    ls = rng.uniform(1.12, 1.45, n_stray) * (1.0 - 0.08 * fs["w_head"])
    st, _ = v10.grow_guides_v10(sp_, sn_, sex, 10, rng, length_scale=ls, lift_add=rng.uniform(1.5, 6.0, n_stray) * (1.0 - 0.4 * fs["w_head"]), lay=0.78)
    keep = (sex["is_ear"] < 0.5) & (fs["d_fis"] > 4.0) & (fs["excl"] > 0.95) & (fs["cup"] < 0.3)
    keep &= rng.random(n_stray) < (1.0 - HEAD_STRAY_KEEP_V12 * fs["w_head"])
    st, suv = st[keep], suv[keep]

    def wfly(c, n, ex):
        f_ = v6.coat_fields(c, n, ex)
        zw = c[:, 2] / MM
        sil = f_["w_body"] * (1.0 - smoothstep(-160.0, -230.0, zw)) + 0.3 * f_["w_chest"]
        return f_["density"] * np.maximum(f_["excl"], 0.0) * sil

    n_fly = 1500
    fp, fn_, fuv, fex = v6.sample_roots(S, n_fly, wfly, rng)
    ft, _ = v10.grow_guides_v10(fp, fn_, fex, 10, rng, length_scale=rng.uniform(1.35, 1.9, n_fly), lift_add=rng.uniform(5.0, 13.0, n_fly), lay=0.6)
    ffs = v6.coat_fields(fp, fn_, fex)
    fk = (fex["is_ear"] < 0.5) & (ffs["d_fis"] > 6.0) & (ffs["excl"] > 0.95)
    ft, fuv = ft[fk], fuv[fk]
    t = np.linspace(0, 1, st.shape[1])
    radii = np.concatenate([np.repeat(((0.068 * MM) * (1 - t) ** 1.3 + 0.008 * MM)[None], len(st), 0),
                            np.repeat(((0.050 * MM) * (1 - t) ** 1.2 + 0.006 * MM)[None], len(ft), 0)])
    ob = v6.make_curves("CatBaseV6_Fur_Stray", np.concatenate([st, ft]), 0, 0, coll, uv=np.concatenate([suv, fuv]), surface=skin, radii=radii)
    ob.parent = skin
    ob.data.materials.append(hair_material_v12("M_CatBaseV6_Fur_Stray", images, False))
    m_ = ob.modifiers.new("CatBaseV6 Eye Cull", "NODES")
    m_.node_group = cull
    layers.append(ob)
    log(f"strays {len(st)} + fly-aways {len(ft)}")
    guides = v6.make_curves("CatBaseV6_Fur_Guides", strands, 0.1 * MM, 0.05 * MM, coll, uv=uv, surface=skin)
    guides.parent = skin
    guides.hide_render = True
    guides.hide_viewport = True
    return layers, guides


# ---------------------------------------------------------------------------
# Ears (round 10)
# ---------------------------------------------------------------------------

# round-9 review: "the furnishings are a stiff white comb or mohawk along the
# ear margins and crown ... and fan across the crown between the ears in
# front view". Round 9: 2,200 tufts, medial-margin tufts 16-28 mm rising
# steeply (up 0.80), floor tufts 14-24 mm, tip tufts 7-11 mm straight up.
FURN_TUFTS_V12 = 1500
FURN_MEDIAL_V12 = (0.45, 0.62, 0.55)  # up, lateral (across the opening), forward: they arch into the ear
FURN_MEDIAL_LEN_V12 = (9.0, 17.0)
FURN_FLOOR_LEN_V12 = (9.0, 16.0)
FURN_TIP_LEN_V12 = (3.5, 6.5)
FURN_COLOUR_V12 = (0.58, 0.565, 0.53)  # round 9: 0.70, 0.68, 0.62 (a stiff white comb against the sky)
# round-9 review: "the margins read as paper-thin sheets"; the pinna tip
# thickness (cartilage and skin) 0.9 -> 1.4 mm.
EAR_T1_V12 = 1.4
EAR_PIGMENT_V12 = 0.45  # inner-pinna pigment mottling strength (round 9: none; smooth uniform pink)
EAR_RIM_DARK_V12 = (0.105, 0.090, 0.086)  # skin colour at the rolled margin (round 9: the pink inner skin ran to the cut edge)


def build_inner_ear_furnishings_v12(coll, skin, images):
    """Round-9 furnishings, fewer, shorter and curled into the ear: medial-
    margin tufts arch across the opening instead of rising over the crown,
    floor tufts are shorter, the tip tufts are short and sparse, and the
    tuft colour is a pale grey-white with more spread."""
    rng = np.random.default_rng(v6.RNG_SEED + 13)
    S = v6.evaluated_surface(skin)

    def wfn(c, n, ex):
        cp = v10.cup_weight_v10(c) * (1.0 - ex["is_ear"])
        front = ex["is_ear"] * smoothstep(0.2, 0.6, ex["ear_face"])
        t, u = ex["ear_t"], ex["ear_u"]
        low = (1.0 - smoothstep(0.30, 0.45, t)) * smoothstep(-0.12, 0.0, t)
        med = (1.0 - smoothstep(-0.78, -0.45, u)) * _bump(t, 0.0, 0.45)
        lat = smoothstep(0.45, 0.65, u) * (1.0 - smoothstep(0.90, 0.99, u)) * _bump(t, -0.02, 0.20)
        upper = _bump(t, 0.40, 0.85) * (1.0 - smoothstep(0.80, 0.95, np.abs(u)))
        tipz = smoothstep(0.90, 0.97, t)
        return front * (3.0 * low + 1.6 * med + 1.8 * lat + 0.45 * upper + 0.12 * tipz + 0.25) + 3.2 * cp

    cpos, cnrm, cuv, cex = v6.sample_roots(S, FURN_TUFTS_V12, wfn, rng)
    npts = 12
    strands, uvs, radii = [], [], []
    tt = np.linspace(0, 1, npts)
    for i in range(FURN_TUFTS_V12):
        s = 1.0 if (cpos[i] @ v6.head_R())[1] > 0 else -1.0
        F = v6.ear_frame(s)
        up = F[:, 2] @ v6.head_R().T
        fwd = F[:, 0] @ v6.head_R().T
        lat = F[:, 1] * s @ v6.head_R().T
        eu = cex["ear_u"][i]
        et = cex["ear_t"][i]
        on_ear = cex["is_ear"][i] > 0.5
        nn = cnrm[i]
        if on_ear and et > 0.88:
            d = 0.70 * up + 0.45 * fwd + 0.25 * nn
            Lt = rng.uniform(*FURN_TIP_LEN_V12) * MM
            k = int(rng.integers(1, 3))
        elif on_ear and eu > 0.45:
            d = 0.45 * up - 0.55 * lat + 0.60 * fwd + 0.25 * nn
            Lt = rng.uniform(10.0, 17.0) * MM
            k = int(rng.integers(3, 6))
        elif on_ear and eu < -0.45:
            d = FURN_MEDIAL_V12[0] * up + FURN_MEDIAL_V12[1] * lat + FURN_MEDIAL_V12[2] * fwd + 0.25 * nn
            Lt = rng.uniform(*FURN_MEDIAL_LEN_V12) * MM
            k = int(rng.integers(3, 7))
        elif on_ear and et > 0.40:
            d = 0.85 * up + 0.30 * fwd + 0.35 * nn
            Lt = rng.uniform(5.0, 9.0) * MM
            k = int(rng.integers(1, 3))
        else:
            d = 0.55 * up + 0.80 * fwd + 0.20 * lat * rng.normal() + 0.20 * nn
            Lt = rng.uniform(*FURN_FLOOR_LEN_V12) * MM
            k = int(rng.integers(3, 8))
        d /= np.linalg.norm(d) + 1e-9
        jit_ang = math.radians(rng.uniform(15.0, 28.0))
        ax_ = np.cross(d, rng.normal(size=3))
        ax_ /= np.linalg.norm(ax_) + 1e-9
        d = d * math.cos(jit_ang) + np.cross(ax_, d) * math.sin(jit_ang)
        curl = rng.normal(0, 0.14, 3) + 0.18 * lat * (1.0 if eu < 0 else -1.0)
        tipp = None
        for _ in range(k):
            off = rng.normal(0.0, 0.45 * MM, 3)
            off -= (off @ nn) * nn
            p = cpos[i] + off - nn * 0.15 * MM
            fan = rng.normal(0.0, 0.09, 3)
            Lh = Lt * rng.uniform(0.65, 1.1)
            c2 = curl + rng.normal(0, 0.05, 3)
            pts = [p.copy()]
            for kk in range(1, npts):
                s_ = kk / (npts - 1)
                dd = d + fan * s_ ** 1.2 + c2 * s_ + up * 0.10 * s_ - np.array([0.0, 0.0, 0.18]) * s_ * s_
                dd /= np.linalg.norm(dd)
                p = p + dd * Lh / (npts - 1)
                pts.append(p.copy())
            pts = np.array(pts)
            if tipp is None:
                tipp = pts[-1].copy()
            pts = pts + (tipp - pts[-1])[None, :] * (0.30 * tt ** 2)[:, None]
            strands.append(pts)
            uvs.append(cuv[i])
            radii.append((0.048 * MM) * (1 - tt) ** 1.0 + 0.006 * MM)
    strands = np.array(strands)
    ob = v6.make_curves("CatBaseV6_Fur_EarFurnishings", strands, 0, 0, coll, uv=np.array(uvs), surface=skin, radii=np.array(radii))
    ob.parent = skin
    v10.FURN_COLOUR = FURN_COLOUR_V12
    mat = v11.furnishing_material_v11()
    for nd in mat.node_tree.nodes:
        if nd.type == "MAP_RANGE" and abs(nd.inputs["To Min"].default_value - 0.80) < 1e-6:
            nd.inputs["To Min"].default_value = 0.62
            nd.inputs["To Max"].default_value = 1.08
    ob.data.materials.append(mat)
    log(f"ear furnishings v12: {FURN_TUFTS_V12} tufts, {len(strands)} hairs")
    return ob


def skin_material_v12(images):
    """Round-9 skin with the inner pinna mottled by pigment (grey-brown
    patches and fine dots, round 9 was a smooth uniform pink), the rolled
    ear margin darkened to the back coat's skin (no pink cut edge), and less
    subsurface at the margin."""
    m = v11.skin_material_v11(images)
    nt = m.node_tree
    bs = next(nd for nd in nt.nodes if nd.type == "BSDF_PRINCIPLED")
    reg = next(nd for nd in nt.nodes if nd.type == "TEX_IMAGE" and nd.image is not None and "Regions" in nd.image.name)
    det = next(nd for nd in nt.nodes if nd.type == "TEX_IMAGE" and nd.image is not None and "Detail" in nd.image.name)
    sr = next(l_.to_node for l_ in nt.links if l_.from_node == reg and l_.to_node.type == "SEPARATE_COLOR")
    sd = next(l_.to_node for l_ in nt.links if l_.from_node == det and l_.to_node.type == "SEPARATE_COLOR")
    inner = _maprange(nt, sr.outputs["Blue"], 0.7, 0.95, 0.0, 1.0, (2200, 900))
    rim = _math(nt, "MULTIPLY", sd.outputs["Green"], _maprange(nt, sr.outputs["Blue"], 0.30, 0.45, 0.0, 1.0, (2200, 700)), (2350, 700))
    tc = N(nt, "ShaderNodeTexCoord", (2000, 1300))
    nz = N(nt, "ShaderNodeTexNoise", (2200, 1300))
    nz.inputs["Scale"].default_value = 260.0
    nz.inputs["Detail"].default_value = 4.0
    L(nt, tc.outputs["Object"], nz.inputs["Vector"])
    vor = N(nt, "ShaderNodeTexVoronoi", (2200, 1100))
    vor.inputs["Scale"].default_value = 1400.0
    L(nt, tc.outputs["Object"], vor.inputs["Vector"])
    patches = _maprange(nt, nz.outputs["Fac"], 0.50, 0.66, 0.0, 1.0, (2400, 1300), smooth=True)
    dots = _maprange(nt, vor.outputs["Distance"], 0.0, 0.18, 1.0, 0.0, (2400, 1100), smooth=True)
    pigm = _math(nt, "MAXIMUM", patches, _math(nt, "MULTIPLY", dots, 0.6, (2550, 1100)), (2700, 1200))
    k = _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", pigm, inner, (2850, 1200)), EAR_PIGMENT_V12, (3000, 1200))
    src = bs.inputs["Base Color"].links[0].from_socket
    c = v6.mix_rgb(nt, k, src, (0.12, 0.095, 0.090), (3150, 1000))
    c = v6.mix_rgb(nt, _math(nt, "MULTIPLY", rim, 0.85, (3150, 800)), c, EAR_RIM_DARK_V12, (3300, 900))
    L(nt, c, bs.inputs["Base Color"])
    sw = bs.inputs["Subsurface Weight"]
    if sw.links:
        s0 = sw.links[0].from_socket
        L(nt, _math(nt, "MULTIPLY", s0, _math(nt, "SUBTRACT", 1.0, rim, (3150, 600)), (3300, 600)), sw)
    return m


# ---------------------------------------------------------------------------
# Eyes: build override (round 10)
# ---------------------------------------------------------------------------

def eye_overrides_v12(objs):
    for o in objs:
        if o.name.endswith("_Caruncle") and o.data.materials:
            m = o.data.materials[0]
            bs = next((n_ for n_ in m.node_tree.nodes if n_.type == "BSDF_PRINCIPLED"), None)
            if bs is not None:
                bs.inputs["Base Color"].default_value = (*CARUNCLE_COLOUR_V12, 1.0)
                bs.inputs["Coat Weight"].default_value = 0.5
                bs.inputs["Subsurface Weight"].default_value = 0.10


def install_build_overrides_v12():
    if getattr(v6, "_ROUND10_BUILD", False):
        return
    v11.install_build_overrides_v11()
    v6._ROUND10_BUILD = True
    prev_build_eyes = v6.build_eyes

    def build_eyes_v12(coll, mats, parent):
        objs = prev_build_eyes(coll, mats, parent)
        tex = bpy.data.images.get("T_CatBaseV6_Iris")
        imat = iris_material_v12(tex)
        cmat = cornea_material_v12()
        for o in objs:
            if o.name.endswith("_Iris"):
                o.data.materials.clear()
                o.data.materials.append(imat)
            if o.name.endswith("_Cornea"):
                o.data.materials.clear()
                o.data.materials.append(cmat)
        eye_overrides_v12(objs)
        objs += build_nictitans(coll, parent)
        return objs

    v6.build_eyes = build_eyes_v12
    v6.build_lid_margins = build_lid_margins_v12
    v6.skin_material = skin_material_v12
    v6.build_groom = build_groom_v12
    v6.build_inner_ear_furnishings = build_inner_ear_furnishings_v12
    v6.build_skin = build_skin_v12
    v10.hair_material_v10 = hair_material_v12


# ---------------------------------------------------------------------------
# First-person paw (round 10)
# ---------------------------------------------------------------------------

# round-9 known issues: "the toe beans are slightly soft and hazy (the pad
# fringe and sheen), and the dewclaw stub is visible on the bare paw"; the
# review adds "no claw sheaths". Each toe now ends in a claw sheath (a small
# fold over the retracted claw, whose tip just shows), the dewclaw is
# smaller and tucked against the carpus, and the fringe round the pads is
# shorter and lies flatter.
DEWCLAW_V12 = dict(c=(-14.0, 21.5, -6.0), r=(6.2, 4.8, 5.0))  # round 9: (-12, 23.5, -7), (8.5, 6.2, 6.4)
SHEATH_V12 = dict(back=4.5, r=(4.2, 3.6, 3.4), z=2.4)  # the sheath fold at each toe tip (mm)
CLAW_V12 = dict(len=7.5, r0=1.25, expose=2.2)  # mm: claw length from its base, root radius, tip showing beyond the sheath
FRINGE_V12 = (3.8, 4.0)  # mm length, deg lift of the hair round the pad edges (round 9: 6.5 mm, 10 deg)
PAD_SHEEN_V12 = 0.05  # round 9: 0.15 (a haze over the toe beans)
TUFTS_V12 = (300, 4.5, 7.5)  # interdigital tufts: count, length range (round 9: 520 tufts, 7-12 mm)


def paw_parts_v12(P):
    """Round-9 paw SDF with a smaller, tucked dewclaw and a claw-sheath fold
    at each toe tip (a small dorsal lobe and a shallow slit under it)."""
    sm = v6.smin
    R = v6.rot_matrix
    Pf = P * np.array([1.0, 1.0, 1.0 / 0.90])
    body = v6.sd_capsule(Pf, (-282.0, 0.0, 3.0), (-34.0, 0.0, 0.0), 30.0, 21.5) * 0.95
    body = sm(body, v11._sdE(P, (-205.0, -3.0, 9.0), (78.0, 26.0, 24.0)), 9.0)
    body = sm(body, v11._sdE(P, (-190.0, 3.0, -9.0), (72.0, 24.0, 22.0)), 9.0)
    body = sm(body, v11._sdE(P, (-14.0, 0.0, -1.0), (25.0, 24.5, 18.5)), 7.0)
    body = sm(body, v11._sdE(P, (18.0, 0.0, 1.0), (31.0, 34.0, 15.5)), 7.0)
    toes = np.full(P.shape[:-1], 1e3)
    sh = SHEATH_V12
    for y, tip in v11.PAW_DIGITS:
        ph = v11._sdE(P, (tip - 26.0, y * 0.92, 2.5), (12.0, 9.8, 10.5))
        toe = v11._sdE(P, (tip - 11.0, y, 1.0), (11.5, 9.9, 10.2), R(pitch=12.0))
        fold = v11._sdE(P, (tip - sh["back"], y, sh["z"]), sh["r"])
        toes = np.minimum(toes, sm(sm(ph, toe, 4.0), fold, 1.6))
    body = sm(body, toes, 6.0)
    dc = DEWCLAW_V12
    body = sm(body, v11._sdE(P, dc["c"], dc["r"], R(yaw=20.0, pitch=25.0)), 3.0)
    dz = v11.PAD_DROP_V11
    pads = np.full(P.shape[:-1], 1e3)
    for y, tip in v11.PAW_DIGITS:
        pads = np.minimum(pads, v11._sdE(P, (tip - 11.0, y, -8.3 + dz), (9.4, 8.1, 4.4)))
    meta = v11._sdE(P, (21.0, 0.0, -12.7 + dz), (11.5, 17.0, 5.2))
    meta = sm(meta, v11._sdE(P, (10.5, 0.0, -13.2 + dz), (8.8, 8.6, 5.4)), 2.2)
    for s in (1.0, -1.0):
        meta = sm(meta, v11._sdE(P, (12.5, 11.2 * s, -12.8 + dz), (8.6, 8.0, 5.1)), 2.2)
    pads = np.minimum(pads, meta)
    pads = np.minimum(pads, v11._sdE(P, (-31.0, -3.0, -18.2), (5.0, 4.6, 3.0)))
    pads = np.minimum(pads, v11._sdE(P, (dc["c"][0] + 2.0, dc["c"][1] + 2.0, dc["c"][2] - 4.0), (2.8, 2.6, 2.0)))
    return body, pads


_V11_PAW_FIELDS = v11.paw_fields


def paw_fields_v12(Pm, Nn):
    """Round-9 paw fields with a shorter, flatter fringe round the pads and
    the hair roots kept ~1 mm clear of each pad's edge."""
    f = _V11_PAW_FIELDS(Pm, Nn)
    fr = f["fringe"]
    L = f["length"] / MM
    L = np.where(fr > 0, L * (1.0 - fr) + FRINGE_V12[0] * fr, L)
    lift = f["lift"] - fr * (10.0 - FRINGE_V12[1])
    near = 1.0 - smoothstep(0.4, 1.2, np.maximum(f["pads_sd"], 0.0))
    excl = f["excl"] * (1.0 - near * (f["pad"] < 0.5))
    f.update(length=L * MM, lift=lift, excl=np.clip(excl, 0, 1))
    return f


def claw_material():
    m, nt = v6.new_mat("M_CatBaseV6_Paw_Claw")
    out = N(nt, "ShaderNodeOutputMaterial", (600, 0))
    bs = N(nt, "ShaderNodeBsdfPrincipled", (300, 0))
    bs.inputs["Base Color"].default_value = (0.62, 0.58, 0.52, 1)
    bs.inputs["Roughness"].default_value = 0.30
    bs.inputs["Subsurface Weight"].default_value = 0.35
    bs.inputs["Subsurface Radius"].default_value = (1.0, 0.8, 0.6)
    bs.inputs["Subsurface Scale"].default_value = 0.0012
    bs.inputs["Coat Weight"].default_value = 0.3
    bs.inputs["Coat Roughness"].default_value = 0.2
    L(nt, bs.outputs["BSDF"], out.inputs["Surface"])
    return m


def build_claws(coll, skin, Mw):
    """A retracted claw in each toe's sheath: a laterally flattened, curved
    keratin hook rooted inside the toe (hidden by the skin) whose last
    CLAW_V12["expose"] mm show below the sheath fold."""
    mat = claw_material()
    obs = []
    c = CLAW_V12
    nseg, nring = 16, 10
    for i, (y, tip) in enumerate(v11.PAW_DIGITS):
        S0 = np.array([tip - c["len"] + c["expose"], y, 3.2])
        E0 = np.array([tip + c["expose"], y, -1.6])
        up = np.array([0.0, 0.0, 1.0])
        bm = bmesh.new()
        rings = []
        for k in range(nseg + 1):
            s_ = k / nseg
            ctr = S0 + (E0 - S0) * s_ + up * 1.4 * math.sin(math.pi * s_)
            dctr = (E0 - S0) + up * 1.4 * math.pi * math.cos(math.pi * s_)
            tg = dctr / np.linalg.norm(dctr)
            a = np.array([0.0, 1.0, 0.0])
            b = np.cross(tg, a)
            b /= np.linalg.norm(b)
            r = c["r0"] * (1.0 - s_) ** 0.8 + 0.05
            rings.append([bm.verts.new((ctr + r * 0.55 * math.cos(2 * math.pi * j / nring) * a + r * math.sin(2 * math.pi * j / nring) * b) * MM)
                          for j in range(nring)])
        for k in range(nseg):
            for j in range(nring):
                bm.faces.new((rings[k][j], rings[k][(j + 1) % nring], rings[k + 1][(j + 1) % nring], rings[k + 1][j]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new(f"CatBaseV6_Paw_Claw{i + 2}")
        bm.to_mesh(me)
        bm.free()
        for p_ in me.polygons:
            p_.use_smooth = True
        me.materials.append(mat)
        ob = v6.link(bpy.data.objects.new(me.name, me), coll)
        ob.parent = skin
        ob.matrix_world = Mw
        obs.append(ob)
    return obs


_V11_PAW_SKIN = v11.paw_skin_material


def paw_skin_material_v12(images):
    """Round-9 pad shader with less sheen (PAD_SHEEN_V12)."""
    m = _V11_PAW_SKIN(images)
    bs = next(nd for nd in m.node_tree.nodes if nd.type == "BSDF_PRINCIPLED")
    bs.inputs["Sheen Weight"].default_value = PAD_SHEEN_V12
    return m


def build_paw_groom_v12(coll, skin, images, Mw):
    """Round-9 paw groom (guard and undercoat layers, stray guard hairs) with
    fewer, shorter interdigital tufts (TUFTS_V12; round 9's 520 tufts of
    7-12 mm hazed the toe beans in the first-person frame), the round-10
    hair material, and a claw in each toe sheath."""
    rng = np.random.default_rng(v6.RNG_SEED + 31)
    S = v6.evaluated_surface(skin)
    g_local = np.array(Mw.to_3x3().inverted() @ Vector((0.0, 0.0, -1.0)))

    def wfn(c, n, ex):
        f = v11.paw_fields(c, n)
        return f["density"] * np.maximum(f["excl"], 0.05) / np.maximum(f["length"], 2.5 * MM)

    pos, nrm, uv, ex = v6.sample_roots(S, v11.PAW_GUIDES, wfn, rng)
    strands, f = v11.grow_paw_guides(pos, nrm, 8, rng, g_local)
    v6.load_hair_assets()
    v6.length_jitter_group()
    layers = []
    gob = v6.make_curves("CatBaseV6_Paw_Fur_GuardGuides", strands, 0.062 * MM, 0.016 * MM, coll, uv=uv, surface=skin)
    gdata = gob.data
    gdata.materials.append(hair_material_v12("M_CatBaseV6_Paw_Fur_Guard", images, False, tip_alpha=True))
    bpy.data.objects.remove(gob, do_unlink=True)
    for li, (name, clumps, noise, nscale, frizz, jitter, r0, dens) in enumerate(v11.PAW_LAYERS):
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
    ob.data.materials.append(hair_material_v12("M_CatBaseV6_Paw_Fur_Under", images, True, tip_alpha=False))
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
    n_stray = 1800
    sp_, sn_, suv, _ = v6.sample_roots(S, n_stray, wfn, rng)
    st, fs = v11.grow_paw_guides(sp_, sn_, 10, rng, g_local, length_scale=rng.uniform(1.15, 1.45, n_stray),
                                 lift_add=rng.uniform(2.0, 7.0, n_stray), lay=0.75)
    keep = fs["excl"] > 0.95
    st, suv = st[keep], suv[keep]

    def wtuft(c, n, ex):
        f_ = v11.paw_fields(c, n)
        xm = c[:, 0] / MM
        return (n[:, 2] < -0.25) * f_["excl"] * (1.0 - smoothstep(1.2, 4.5, np.maximum(f_["pads_sd"], 0.0))) * (xm > 2.0) * (xm < 76.0)

    n_tuft, t_lo, t_hi = TUFTS_V12
    tp, tn, tuv, _ = v6.sample_roots(S, n_tuft, wtuft, rng)
    npts = 10
    tt = np.linspace(0.0, 1.0, npts)
    tufts, tuvs, trad = [], [], []
    for i in range(n_tuft):
        nn = tn[i]
        d = nn * 0.55 + np.array([0.75, 0.0, 0.0])
        d /= np.linalg.norm(d)
        Lt = rng.uniform(t_lo, t_hi) * MM
        k = int(rng.integers(2, 6))
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
            trad.append((0.046 * MM) * (1 - tt) ** 1.1 + 0.006 * MM)
    tufts = np.array(tufts)
    st10 = st[:, np.linspace(0, st.shape[1] - 1, npts).round().astype(int)]
    radii = np.concatenate([np.repeat(((0.066 * MM) * (1 - tt) ** 1.3 + 0.008 * MM)[None], len(st10), 0), np.array(trad)])
    ob = v6.make_curves("CatBaseV6_Paw_Fur_StrayTufts", np.concatenate([st10, tufts]), 0, 0, coll,
                        uv=np.concatenate([suv, np.array(tuvs)]), surface=skin, radii=radii)
    ob.parent = skin
    ob.data.materials.append(hair_material_v12("M_CatBaseV6_Paw_Fur_Stray", images, False))
    layers.append(ob)
    build_claws(coll, skin, Mw)
    log(f"paw groom v12: {v11.PAW_GUIDES} guides, {len(st10)} strays, {len(tufts)} interdigital hairs in {n_tuft} tufts, 4 claws")
    return layers


# ---------------------------------------------------------------------------
# Overrides
# ---------------------------------------------------------------------------

def apply_round10_overrides():
    if getattr(v6, "_ROUND10", False):
        return
    v11.apply_round9_overrides()
    v6._ROUND10 = True
    # eyes: a rounder, more open aperture tilting up toward the ear; the
    # globes 1 mm further back; the new pupil, iris and relief
    A.fissure_w = FISSURE_W_V12 * MM
    A.fissure_up = FISSURE_UP_V12 * MM
    A.fissure_lo = FISSURE_LO_V12 * MM
    A.fissure_tilt = FISSURE_TILT_V12
    A.eye_sink = -EYE_FORWARD_V12 * MM
    v6.fissure_curves = fissure_curves_v12
    v8.iris_fields = iris_fields_v12
    v8.iris_colour = iris_colour_v12
    v8.iris_height_mm = iris_height_mm_v12
    # skin: silhouette, nape, throat, bust
    v10.NAPE_DIP_V10 = NAPE_DIP_V12
    v10.fur_inset_mm_v10 = fur_inset_mm_v12
    v7.fur_inset_mm = fur_inset_mm_v12
    v7.build_bust_ops = build_bust_ops_v12
    v7.build_bust_field = build_bust_field_v12
    # muzzle, pads, chin, nose
    v9.PAD_H_V9 = PAD_H_V12
    v9.PAD_R_V9 = PAD_R_V12
    v10.CHIN_H_V10 = CHIN_H_V12
    v10.ALAR_H_V10 = ALAR_H_V12
    v10.LEATHER_RIM_V10 = (0.115, 0.056, 0.052)  # round 9: (0.20, 0.095, 0.088), no darker rim at 1 m
    scale_leather_v12()
    v6.build_detail_ops = build_detail_ops_v12
    v6.DETAIL_OPS = None
    # ears: thicker margins
    A.ear_t1 = EAR_T1_V12 * MM
    # markings, coat
    v6.MARKINGS = MARKINGS_V12
    v6._MARK_CACHE.clear()
    v10.MARK_EDGE_V10 = MARK_EDGE_V12
    v10.coat_fields_v10 = coat_fields_v12
    v9.coat_fields_v9 = coat_fields_v12
    v8.coat_fields_v8 = coat_fields_v12
    v6.coat_fields = coat_fields_v12
    # first-person paw
    v11.paw_parts = paw_parts_v12
    v11.paw_fields = paw_fields_v12
    v11.paw_skin_material = paw_skin_material_v12
    v11.build_paw_groom = build_paw_groom_v12


# ---------------------------------------------------------------------------
# Measure, manifest (round 10)
# ---------------------------------------------------------------------------

def stage_measure_v12(args):
    out = v11.stage_measure_v11(args)
    out["round10"] = {"fissure_mm": {"width": FISSURE_W_V12, "upper": FISSURE_UP_V12, "lower": FISSURE_LO_V12, "tilt_deg": FISSURE_TILT_V12},
                      "iris_hidden_by_upper_lid_fraction": round(max(0.0, (0.765 * A.eye_r / MM - FISSURE_UP_V12)) / (2 * 0.765 * A.eye_r / MM), 3),
                      "pupil_iris_radii": {"half_width": PUPIL_W0_V12, "half_height": PUPIL_H_V12}}
    (CACHE / f"measure_round{args.round}.json").write_text(json.dumps(out, indent=2) + "\n")
    log("round-10 measures", json.dumps(out["round10"]))
    return out


def stage_manifest_v12(args):
    v11.stage_manifest_v11(args)
    man = json.loads((OUT / "manifest.json").read_text())
    man["round"] = args.round
    man["generator"] = ("scripts/art/create_cat_base_v12.py (round 10; imports create_cat_base_v11.py, which imports "
                        "create_cat_base_v10.py, create_cat_base_v9.py, create_cat_base_v8.py, create_cat_base_v7.py and create_cat_base_v6.py)")
    man["round10"] = {
        "eyes": {"fissure_mm": {"width": FISSURE_W_V12, "upper": FISSURE_UP_V12, "lower": FISSURE_LO_V12}, "tilt_deg": FISSURE_TILT_V12,
                 "globe_forward_mm": EYE_FORWARD_V12,
                 "pupil": {"half_width": PUPIL_W0_V12, "half_height": PUPIL_H_V12, "profile_exponent": PUPIL_EXP_V12, "feather": PUPIL_FEATHER_V12},
                 "cornea": {"roughness": CORNEA_ROUGH_V12, "tear_bump_m": TEAR_BUMP_V12, "diffuse_rays_pass": True},
                 "tear_meniscus_radius_mm": TEAR_R_V12 / MM, "caruncle_colour": CARUNCLE_COLOUR_V12, "nictitans": True},
        "skin": {"cheek": CHEEK_V12, "temple_taper": TEMPLE_TAPER_V12, "jowl_taper": JOWL_TAPER_V12, "neck_notch": NECK_NOTCH_V12,
                 "nape_dip_mm": NAPE_DIP_V12, "nape_fill": NAPE_FILL_V12},
        "bust": {"shoulder_mm": list(SHOULDER_V12), "elbow_mm": list(ELBOW_V12), "acromion_mm": list(ACROMION_V12),
                 "deltoid_insertion_mm": list(DELTOID_INSERT_V12), "bust_dx_mm": BUST_DX_V12, "throat": [list(THROAT_V12[0]), list(THROAT_V12[1])]},
        "muzzle": {"pad_mm": PAD_H_V12, "pad_back": PAD_BACK_V12, "chin_mm": CHIN_H_V12, "bridge": BRIDGE_V12,
                   "leather_scale": LEATHER_SCALE_V12, "alar_mm": ALAR_H_V12},
        "coat": {"white_edge_mm": WHITE_EDGE_V12, "mark_edge_mm": MARK_EDGE_V12, "stripe_core": STRIPE_CORE_V12, "spectacle": SPECTACLE_V12,
                 "agouti_jitter": AGOUTI_JITTER_V12, "white_jitter": list(WHITE_JITTER_V12), "guard_layers": [g[0] for g in GUARD_LAYERS_V12],
                 "strays": N_STRAY_V12},
        "ears": {"furnishing_tufts": FURN_TUFTS_V12, "tip_thickness_mm": EAR_T1_V12, "pigment": EAR_PIGMENT_V12},
        "viewmodel_paw": {"dewclaw": DEWCLAW_V12, "sheath": SHEATH_V12, "claw": CLAW_V12, "fringe_mm_deg": list(FRINGE_V12),
                          "pad_sheen": PAD_SHEEN_V12, "tufts": list(TUFTS_V12)},
    }
    (OUT / "manifest.json").write_text(json.dumps(man, indent=2, ensure_ascii=False) + "\n")
    log("manifest (round 10 fields added)")


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
    ap.add_argument("--preview-dir", default=str(CACHE / "preview_r10"))
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
    apply_round10_overrides()
    stages = args.stages.split(",")
    if "skin" in stages:
        v10.EAR_CAVITY_REBUILD_V10[0] = True
        v10._EAR_CAVITY_V10.clear()
        v7.stage_skin_v7(args)
    if "skinmeasure" in stages:
        m = dict(v10.measure_skin_v10(), **v11.measure_bust_v11())
        log("skin measure", json.dumps(m))
        (Path(args.preview_dir) / "skin_measure.json").write_text(json.dumps(m, indent=2))
    if "skinpreview" in stages:
        v11.preview_bust_v11(args)
    if "pawpreview" in stages:
        v11.preview_paw(args)
    if "build" in stages:
        install_build_overrides_v12()
        v6.stage_build(args)
    if "render" in stages:
        v11.stage_render_v11(args)
    if "pawbuild" in stages:
        v11.stage_pawbuild(args)
    if "fprender" in stages:
        v11.stage_fprender(args)
    if "silhouette" in stages:
        v11.stage_silhouette(args)
    if "measure" in stages:
        stage_measure_v12(args)
    if "compare" in stages:
        v11.stage_compare_v11(args)
    if "manifest" in stages:
        stage_manifest_v12(args)


if __name__ == "__main__":
    main()
