"""CatBaseV6 round 6 (generator v8): judged defects of round 5 (score ~5/10).

Round 5 (scripts/art/create_cat_base_v7.py) derived the head and neck from
a real cat scan ("Cat sitting upright" by elaughli, CC BY 4.0, private raw
scan) and kept the CT skull for landmarks. Round 6 keeps that method and the
scan-derived surface, and fixes what the round-5 judge still read as CG, most
impactful first:

1. eyes: a separate, steeper corneal dome (IOR 1.376) over a real anterior
   chamber; a recessed, concave iris textured with a painted 2048 px stroma
   (wavy fibres, crypts, a collarette, contraction furrows, a dark limbal
   ring) whose relief is displaced from the same fields; a lens-shaped,
   feathered slit that tapers to points inside the aperture; and a reflection
   boost so the environment reads on the cornea;
2. the globe and cornea sit 2 mm further forward and the corneal apex 1.5 mm
   prouder, the lids follow the corneal dome (the lid shell is offset from
   the globe AND the cornea), and the fur is cut to <= 1 mm within ~3.5 mm of
   the lid margin, so the clear dome breaks the profile;
3. lid margins: a tapered, flush strip (thicker at the lower medial lid),
   matte, with only a thin wet contact line; a thin tear meniscus instead of
   round 4's tube; a tear-duct notch at the medial canthus and a faint
   lacrimal line;
4-7. ears: 0.85x length, 1.1x base, 10 deg more outward lean; thin (<1 mm)
   rolled margins instead of a 5 mm rim band; deeper antihelical ridges,
   tragus and antitragus; sparse, flat, clumped back fur that overhangs the
   rim; a nearly bare, darker, vascular, translucent inner pinna with hair only
   on the lower inner-front third and a band along the outer edge; fewer,
   longer, finer furnishing wisps; a smooth conchal funnel carve (round 5's
   cup carve was also mirrored wrongly on the right ear) and head fur combed
   continuously onto the ear back;
8. nose leather 0.8x with comma nostrils, a philtrum split, a rose-brown
   margin and a 0.25 mm pebbled normal;
9. a curved, soft cheek line instead of the straight "glasses arm" stripe;
10. warm brown-grey agouti banding, broader crisp tabby strokes with 1-2 mm
   edges, shorter face fur so the strokes do not smear;
11. a narrower, higher bust (keel chest, shorter neck, fuller throat) and a
   body flow field without shoulder whorls;
12. a shorter, wavier white bib with a ragged, interlocking boundary;
13. orderly whisker-follicle rows (grey-pink, low contrast), a pigmented lip
   margin with mouth corners, a small lower lip;
14. tapered, curved whiskers; short brow whiskers that stay clear of the ears;
15. three clump levels, frizz and tip transparency on the guard coat.

Run from the repository root (Blender 5.2.2 LTS, background):

  blender -b --factory-startup --python scripts/art/create_cat_base_v8.py -- \\
      --stages skin,build,measure,render,compare,manifest --round 6 \\
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
from mathutils.kdtree import KDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import create_cat_base_v7 as v7  # noqa: E402

v6 = v7.v6
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

IRIS_SEED = 5171
IRIS_ROT = {1.0: 0.0, -1.0: 2.35}  # texture/relief rotation per eye (radians), so the two irides differ


# ---------------------------------------------------------------------------
# Eyes: cornea, fissure, lid shell, iris texture and relief
# ---------------------------------------------------------------------------

def cornea_dims_v8():
    """Round 6: a steeper corneal dome (radius 1.045x the limbus radius, as
    in a real cat's nearly hemispherical cornea; round 5 used 1.086x), so the
    clear dome stands ~1.5 mm prouder in front of the recessed iris."""
    r_i = 0.765 * A.eye_r
    d_i = math.sqrt(A.eye_r ** 2 - r_i ** 2) - 0.8 * MM
    rl = r_i + 0.4 * MM
    Rc = 1.045 * rl
    h = Rc - math.sqrt(Rc ** 2 - rl ** 2)
    return dict(r_i=r_i, d_i=d_i, Rc=Rc, rl=rl, h=h, apex=d_i + 0.3 * MM + h)


_V6_FISSURE = v6.fissure_curves


def fissure_curves_v8(uu):
    """Round 6: the medial canthus is drawn a further 2 mm down toward the
    nose, so both arcs close into a small downward-pointing tear-duct notch
    (judged round 5: the notch was missing)."""
    up, lo = _V6_FISSURE(uu)
    hw = 0.5 * A.fissure_w
    t = np.clip(uu / hw, -1.0, 1.0)
    notch = 0.9 * MM * smoothstep(-0.84, -1.0, t) ** 1.5
    return up - notch, lo - notch


def sd_lid_shell_v8(P, side=1.0):
    """Lid shell offset from the eye surface itself (the outer of the globe
    and the corneal dome), so the lids drape over the prouder cornea instead
    of letting it poke through the upper lid."""
    cd = v6.cornea_dims()
    q = (P - v6.eye_center(side)) @ v6.gaze_frame(side)
    up = smoothstep(-4.0 * MM, 7.0 * MM, q[..., 2]) * smoothstep(-2.0 * MM, 10.0 * MM, q[..., 0])
    t = A.lid_gap + A.lid_t + A.lid_upper_extra * up
    d_g = np.linalg.norm(q, axis=-1) - (A.eye_r + t)
    qc = q.copy()
    qc[..., 0] -= cd["apex"] - cd["Rc"]
    d_c = np.linalg.norm(qc, axis=-1) - (cd["Rc"] + t)
    return v6.smin(d_g, d_c, 1.5 * MM)


def _h2(i, j, seed):
    h = np.sin(i * 127.1 + j * 311.7 + seed * 19.19 + 0.123) * 43758.5453
    return h - np.floor(h)


def pnoise(u, v, pu, seed):
    """2D value noise, periodic in u with integer period pu (lattice units)."""
    iu = np.floor(u)
    iv = np.floor(v)
    fu = u - iu
    fv = v - iv
    su = fu * fu * (3.0 - 2.0 * fu)
    sv = fv * fv * (3.0 - 2.0 * fv)
    i0 = np.mod(iu, pu)
    i1 = np.mod(iu + 1.0, pu)
    a = _h2(i0, iv, seed)
    b = _h2(i1, iv, seed)
    c = _h2(i0, iv + 1.0, seed)
    d = _h2(i1, iv + 1.0, seed)
    return (a * (1 - su) + b * su) * (1 - sv) + (c * (1 - su) + d * su) * sv


def iris_fields(rho, th):
    """Stroma fields on the iris disc (rho 0..1 of the iris radius, th rad).
    Painted procedurally, designed from observation of macro photographs of
    cat irides (no photograph pixels are used): wavy radial fibre bundles at
    three scales (not straight starburst streaks), cellular mottling, an
    irregular collarette ridge at ~40 % radius, crypts (lacunae) just outside
    it, three broken contraction furrows in the ciliary zone, and the
    limbal ring."""
    s = IRIS_SEED
    U = np.mod(th / (2.0 * math.pi), 1.0)
    warp = (pnoise(U * 10, rho * 2.5, 10, s + 1) - 0.5) * 0.030 + (pnoise(U * 36, rho * 5.0, 36, s + 2) - 0.5) * 0.010
    Uw = np.mod(U + warp, 1.0)
    f1 = pnoise(Uw * 180, rho * 7.0, 180, s + 3)
    f2 = pnoise(Uw * 420, rho * 13.0, 420, s + 4)
    f3 = pnoise(Uw * 900, rho * 24.0, 900, s + 5)
    fib = 0.5 * f1 + 0.3 * f2 + 0.2 * f3
    mot = 0.6 * pnoise(U * 24, rho * 4.0, 24, s + 6) + 0.4 * pnoise(U * 60, rho * 9.0, 60, s + 7)
    rc = 0.40 + 0.05 * (pnoise(U * 9, np.zeros_like(rho) + 0.3, 9, s + 8) - 0.5) + 0.012 * np.sin(th * 19 + 0.7)
    coll = np.exp(-((rho - rc) / 0.028) ** 2)
    cr = pnoise(Uw * 55, rho * 7.5, 55, s + 9)
    zone = smoothstep(rc + 0.01, rc + 0.06, rho) * (1.0 - smoothstep(0.70, 0.80, rho))
    crypt = smoothstep(0.70, 0.84, cr) * zone
    cr2 = smoothstep(0.78, 0.90, pnoise(Uw * 140, rho * 16.0, 140, s + 10)) * smoothstep(0.18, 0.26, rho) * (1.0 - smoothstep(0.86, 0.93, rho))
    furrow = np.zeros_like(rho)
    for k, r0 in enumerate((0.74, 0.81, 0.87)):
        rr = r0 + 0.008 * np.sin(th * (7 + 3 * k) + k)
        furrow = furrow + np.exp(-((rho - rr) / 0.007) ** 2) * smoothstep(0.35, 0.65, pnoise(U * 10, np.full_like(rho, k * 3.1), 10, s + 11 + k))
    limb = smoothstep(0.84, 0.985, rho)
    return dict(fib=fib, mot=mot, coll=coll, crypt=crypt, cr2=cr2, furrow=np.clip(furrow, 0, 1), limb=limb, rc=rc)


def iris_colour(f, rho):
    """Linear albedo of Nyaakoto's grey-blue iris."""
    base = np.array([0.108, 0.150, 0.198])
    light = np.array([0.30, 0.35, 0.39])
    deep = np.array([0.026, 0.044, 0.068])
    fv = smoothstep(0.38, 0.80, f["fib"])[..., None]
    col = base * (1 - 0.62 * fv) + light * (0.62 * fv)
    col = col * (0.78 + 0.44 * f["mot"])[..., None]
    # pupillary zone: a little lighter and greyer
    pz = (1.0 - smoothstep(f["rc"] - 0.05, f["rc"] + 0.01, rho))[..., None]
    col = col * (1 - 0.55 * pz) + (col * np.array([1.05, 1.06, 0.98]) + np.array([0.030, 0.034, 0.030])) * (0.55 * pz)
    col = col * (1 - 0.45 * f["coll"][..., None]) + np.array([0.33, 0.38, 0.41]) * (0.45 * f["coll"][..., None])
    cr = np.clip(0.85 * f["crypt"] + 0.55 * f["cr2"], 0, 1)[..., None]
    col = col * (1 - cr) + deep * cr
    col = col * (1.0 - 0.35 * f["furrow"])[..., None]
    col = col * (1.0 - 0.28 * smoothstep(0.58, 0.86, rho))[..., None]
    lb = (0.92 * f["limb"])[..., None]
    col = col * (1 - lb) + np.array([0.010, 0.015, 0.024]) * lb
    return col


def iris_height_mm(f, rho):
    return (-1.0 * (1.0 - rho ** 2) + 0.20 * f["coll"] + 0.11 * (f["fib"] - 0.5) - 0.35 * f["crypt"] - 0.15 * f["cr2"]
            - 0.06 * f["furrow"] + 0.04 * (f["mot"] - 0.5))


def iris_arrays_v8(side, rings=120, segs=480, seed=0):
    """Round 6 iris mesh (gaze-frame metres): concave, relief displaced from
    the same stroma fields as the painted texture (crypts are pits, the
    collarette a ridge). Returns P, quads, the pupil UVs (IrisXY) and a
    fallback vertex colour."""
    cd = v6.cornea_dims()
    ri = cd["r_i"]
    rho = np.linspace(0.0, 1.0, rings)
    th = np.linspace(0.0, 2 * math.pi, segs, endpoint=False)
    R_, T_ = np.meshgrid(rho, th, indexing="ij")
    f = iris_fields(R_, T_ + IRIS_ROT[1.0 if side > 0 else -1.0])
    h = iris_height_mm(f, R_) * MM
    x = cd["d_i"] + h
    y = R_ * ri * np.cos(T_)
    z = R_ * ri * np.sin(T_)
    P = np.stack([x, y, z], -1).reshape(-1, 3)
    uv = np.stack([np.cos(T_) * R_ * side, np.sin(T_) * R_], -1).reshape(-1, 2)
    C = iris_colour(f, R_).reshape(-1, 3)
    idx = np.arange(rings * segs).reshape(rings, segs)
    quads = [np.stack([idx[i], np.roll(idx[i], -1), np.roll(idx[i + 1], -1), idx[i + 1]], -1) for i in range(rings - 1)]
    return P, np.concatenate(quads), uv, C


def linear_to_srgb(c):
    c = np.clip(c, 0.0, 1.0)
    return np.where(c <= 0.0031308, 12.92 * c, 1.055 * np.power(c, 1.0 / 2.4) - 0.055)


def bake_iris_texture(res=2048):
    """T_CatBaseV6_Iris.png: the painted stroma (sRGB), evaluated on the unit
    disc (u, v) = 0.5 + 0.5 (rho cos th, rho sin th)."""
    t0 = time.time()
    g = (np.arange(res) + 0.5) / res * 2.0 - 1.0
    X, Y = np.meshgrid(g, g, indexing="xy")  # row = v (bottom-up, as Blender stores pixels)
    rho = np.hypot(X, Y)
    th = np.arctan2(Y, X)
    rc = np.clip(rho, 0.0, 1.0)
    f = iris_fields(rc, th)
    col = iris_colour(f, rc)
    col = np.where((rho > 1.0)[..., None], np.array([0.010, 0.015, 0.024]), col)
    img = bpy.data.images.new("T_CatBaseV6_Iris", res, res, alpha=False, float_buffer=False)
    img.colorspace_settings.name = "sRGB"
    px = np.ones((res, res, 4), np.float32)
    px[..., :3] = linear_to_srgb(col)
    img.pixels.foreach_set(px.ravel())
    tex_dir = OUT / "Textures"
    tex_dir.mkdir(parents=True, exist_ok=True)
    img.filepath_raw = str(tex_dir / "T_CatBaseV6_Iris.png")
    img.file_format = "PNG"
    img.save()
    img.filepath = "//Textures/T_CatBaseV6_Iris.png"
    log(f"iris texture {res}px ({time.time()-t0:.0f}s)")
    return img


PUPIL_W0_V8 = 0.105  # slit half-width at its centre (iris radii)
PUPIL_H_V8 = 0.56  # slit half-height: both tapered ends lie inside the ~0.64 r_i aperture
PUPIL_FEATHER = 0.018


def iris_material_v8(tex):
    """Painted stroma texture, a darker pupillary ruff that follows the slit,
    and a lens-shaped (vesica) slit, feathered, that tapers to points inside
    the visible aperture (judged round 5: a constant-width, hard-edged black
    stripe; its taper was hidden under the lids)."""
    m, nt = v6.new_mat("M_CatBaseV6_IrisV8")
    out = N(nt, "ShaderNodeOutputMaterial", (1500, 0))
    bs = N(nt, "ShaderNodeBsdfPrincipled", (1000, 150))
    uvt = N(nt, "ShaderNodeUVMap", (-900, 300))
    uvt.uv_map = "IrisTex"
    ti = N(nt, "ShaderNodeTexImage", (-650, 300))
    ti.image = tex
    ti.interpolation = "Cubic"
    L(nt, uvt.outputs["UV"], ti.inputs["Vector"])
    bs.inputs["Roughness"].default_value = 0.75
    bs.inputs["Specular IOR Level"].default_value = 0.0
    uv = N(nt, "ShaderNodeUVMap", (-900, -200))
    uv.uv_map = "IrisXY"
    sep = N(nt, "ShaderNodeSeparateXYZ", (-700, -200))
    L(nt, uv.outputs["UV"], sep.inputs["Vector"])

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

    yy = math_("DIVIDE", sep.outputs["Y"], PUPIL_H_V8, (-500, -300))
    y2 = math_("MULTIPLY", yy, yy, (-350, -300))
    om = math_("SUBTRACT", 1.0, y2, (-200, -300), clamp=True)
    hw = math_("MULTIPLY", om, PUPIL_W0_V8, (-50, -300))
    ax = math_("ABSOLUTE", sep.outputs["X"], None, (-350, -150))
    dd = math_("SUBTRACT", ax, hw, (100, -200))
    pm = N(nt, "ShaderNodeMapRange", (300, -200))
    L(nt, dd, pm.inputs["Value"])
    pm.inputs["From Min"].default_value = -PUPIL_FEATHER
    pm.inputs["From Max"].default_value = PUPIL_FEATHER
    pm.inputs["To Min"].default_value = 1.0
    pm.inputs["To Max"].default_value = 0.0
    pm.interpolation_type = "SMOOTHSTEP"
    # pupillary ruff: the stroma darkens and browns in a thin band along the slit
    ru = N(nt, "ShaderNodeMapRange", (300, 50))
    L(nt, dd, ru.inputs["Value"])
    ru.inputs["From Min"].default_value = 0.0
    ru.inputs["From Max"].default_value = 0.075
    ru.inputs["To Min"].default_value = 0.40
    ru.inputs["To Max"].default_value = 1.0
    ru.interpolation_type = "SMOOTHSTEP"
    mul = N(nt, "ShaderNodeVectorMath", (550, 250))
    mul.operation = "SCALE"
    L(nt, ti.outputs["Color"], mul.inputs[0])
    L(nt, ru.outputs["Result"], mul.inputs["Scale"])
    L(nt, mul.outputs["Vector"], bs.inputs["Base Color"])
    black = N(nt, "ShaderNodeBsdfPrincipled", (1000, -250))
    black.inputs["Base Color"].default_value = (0.0025, 0.0028, 0.0030, 1.0)
    black.inputs["Roughness"].default_value = 1.0
    black.inputs["Specular IOR Level"].default_value = 0.0
    mx = N(nt, "ShaderNodeMixShader", (1250, 0))
    L(nt, pm.outputs["Result"], mx.inputs["Fac"])
    L(nt, bs.outputs["BSDF"], mx.inputs[1])
    L(nt, black.outputs["BSDF"], mx.inputs[2])
    L(nt, mx.outputs["Shader"], out.inputs["Surface"])
    return m


CORNEA_REFLECT_BOOST = 0.8


def cornea_material_v8():
    """Clear cornea and aqueous (IOR 1.376, roughness 0), transparent to
    shadow rays, plus a Fresnel-weighted mirror term (0.8x the corneal
    Fresnel) standing in for the tear film, so the environment reads over the
    whole dome (judged round 5: only a single disc catchlight read). An
    artistic boost of ~1.8x the bare-cornea reflectance, recorded in the README."""
    m, nt = v6.new_mat("M_CatBaseV6_CorneaV8")
    out = N(nt, "ShaderNodeOutputMaterial", (900, 0))
    gl = N(nt, "ShaderNodeBsdfGlass", (100, 150))
    gl.inputs["IOR"].default_value = 1.376
    gl.inputs["Roughness"].default_value = 0.0
    gy = N(nt, "ShaderNodeBsdfGlossy", (100, -50))
    gy.inputs["Roughness"].default_value = 0.0
    fr = N(nt, "ShaderNodeFresnel", (-200, -100))
    fr.inputs["IOR"].default_value = 1.376
    sc = N(nt, "ShaderNodeMath", (-50, -150))
    sc.operation = "MULTIPLY"
    L(nt, fr.outputs["Fac"], sc.inputs[0])
    sc.inputs[1].default_value = CORNEA_REFLECT_BOOST
    # scale the glossy by the Fresnel weight via a mix with a holdout-free black
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


# ---------------------------------------------------------------------------
# Lid margins and tear line (round 6)
# ---------------------------------------------------------------------------

def outline_params(n):
    """(uu/hw, is_lower) along v7.eye_surface_outline's loop order."""
    m = n // 2
    us = np.sin(np.linspace(-0.5 * math.pi, 0.5 * math.pi, m + 1)) * 0.999
    uu = np.r_[us, us[-2:0:-1]]
    low = np.r_[np.zeros(m + 1, bool), np.ones(m - 1, bool)]
    return uu, low


def lid_margin_material_v8():
    """Pigmented lid margin: matte near-black skin, wet only along a thin
    contact line with the eye (margin_t < ~0.12), where a clear coat gives a
    fine tear-line highlight (judged round 5: a grey, plastic 'wet strip'
    ribbon showed between the margin and the fur)."""
    m, nt = v6.new_mat("M_CatBaseV6_LidMarginV8")
    out = N(nt, "ShaderNodeOutputMaterial", (600, 0))
    bs = N(nt, "ShaderNodeBsdfPrincipled", (300, 0))
    bs.inputs["Base Color"].default_value = (0.010, 0.008, 0.008, 1.0)
    bs.inputs["Specular IOR Level"].default_value = 0.25
    at = N(nt, "ShaderNodeAttribute", (-400, 0))
    at.attribute_name = "margin_t"
    rr = N(nt, "ShaderNodeMapRange", (-100, 100))
    L(nt, at.outputs["Fac"], rr.inputs["Value"])
    rr.inputs["From Min"].default_value = 0.08
    rr.inputs["From Max"].default_value = 0.22
    rr.inputs["To Min"].default_value = 0.10
    rr.inputs["To Max"].default_value = 0.65
    rr.interpolation_type = "SMOOTHSTEP"
    L(nt, rr.outputs["Result"], bs.inputs["Roughness"])
    cw = N(nt, "ShaderNodeMapRange", (-100, -150))
    L(nt, at.outputs["Fac"], cw.inputs["Value"])
    cw.inputs["From Min"].default_value = 0.06
    cw.inputs["From Max"].default_value = 0.16
    cw.inputs["To Min"].default_value = 0.6
    cw.inputs["To Max"].default_value = 0.0
    cw.interpolation_type = "SMOOTHSTEP"
    L(nt, cw.outputs["Result"], bs.inputs["Coat Weight"])
    bs.inputs["Coat Roughness"].default_value = 0.03
    L(nt, bs.outputs["BSDF"], out.inputs["Surface"])
    return m


def build_lid_margins_v8(coll, parent, n=360):
    """Round 6 lid margins. The strip's inner edge still lies on the eye, but
    its visible width now varies round the fissure (upper lid ~0.7 mm, lower
    lid ~0.7 mm laterally to ~1.3 mm medially, ~0.3 mm at the canthi), it
    never rises above the lid skin (heights clamped to 2.2 mm), and its outer
    part tucks under the skin and the fur within ~1 mm. A thin tear meniscus (0.14 mm) runs
    along the lower lid contact, replacing round 4's 0.32 mm tube, whose
    reflections read as pale chips."""
    mat = lid_margin_material_v8()
    tear = bpy.data.materials.get("M_CatBaseV6_Tear")
    objs = []
    A_S = np.array([0.0, 0.2, 0.45, 0.8, 1.2, 1.6, 2.0]) * MM
    uu, low = outline_params(n)
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
        # width factor round the fissure
        wf = np.where(low, 0.72 + 0.62 * smoothstep(0.1, -0.75, t), 0.70)
        wf = wf * (0.40 + 0.60 * np.sqrt(np.clip(1.0 - t ** 4, 0.0, 1.0)))
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
        H = np.clip(H, 0.30 * MM, 2.2 * MM)
        h0 = H[:, 1]
        prof = [
            (0.00, np.full(m, -0.15 * MM)),
            (0.00, 0.35 * h0),
            (0.06, 0.72 * h0),
            (0.20, np.minimum(h0, H[:, 1]) - 0.02 * MM),
            (0.45, H[:, 2] - 0.10 * MM),
            (0.80, H[:, 3] - 0.35 * MM),
            (1.20, H[:, 4] - 0.70 * MM),
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
        # tear meniscus: a thin clear fillet along the lower-lid contact
        sel = np.nonzero(low & (np.abs(t) < 0.86))[0]
        sel = sel[np.argsort(t[sel])]
        pts = P[sel] + Nn[sel] * 0.06 * MM + O[sel] * 0.10 * MM * wf[sel][:, None]
        tube = v6.tube_mesh(f"CatBaseV6_Eye{tag}_TearMeniscus", pts, 0.14 * MM, closed=False, segs=8)
        tob = v6.link(bpy.data.objects.new(tube.name, tube), coll)
        if tear is not None:
            tube.materials.append(tear)
        tob.parent = parent
        tob.matrix_world = Matrix.Translation(v6.HEAD_ORIGIN) if parent is not None and parent.type != "EMPTY" else Matrix.Identity(4)
        objs.append(tob)
    return objs


# ---------------------------------------------------------------------------
# Pinna (round 6): smaller, broader, leaning out, thin margins
# ---------------------------------------------------------------------------

def ear_arrays_v8(side=1.0, n_t=110, n_face=52, n_rim=9, sdf=None):
    """Round-5 pinna (v7.ear_arrays_v7) with round-6 changes (judged round 5:
    a 3.2 mm sheet whose cut face read as a constant-width grey band with a
    cookie-cutter edge; tall, narrow, near-vertical inner edges):

    - the sheet thins toward both margins to ~0.45x its mid thickness
      (1.0 mm at the base, 0.5 mm at the tip) and each margin is a small
      rounded tube (radius = half the margin thickness plus a roll that is
      0.45 mm medially and 0.25 mm laterally at the base, gone by 35 %
      height) instead of round 5's 2.3-2.75 mm roll;
    - antihelical ridges twice as deep (1.8 mm), a 3.2 mm antitragus and a
      3.0 mm tragus flap at the conchal entrance, so the inner relief shadows
      itself from the front;
    - size and set come from Anatomy (0.85x length, 1.1x base, 34 deg lean).
    Attributes as round 5."""
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
            ridge += 1.8 * math.exp(-((tc - tk) / 0.026) ** 2) * (1.0 - smoothstep(0.25, 0.6, np.abs(uf + 0.25)))
        ridge += 3.2 * math.exp(-((t - 0.02) / 0.06) ** 2) * np.exp(-((uf - 0.74) / 0.15) ** 2)  # antitragus
        ridge += 3.0 * math.exp(-((t + 0.02) / 0.06) ** 2) * np.exp(-((uf + 0.80) / 0.12) ** 2)  # tragus flap
        Tl = T * thin
        front = p + nin * (0.5 * Tl + ridge)[:, None]
        crease = 0.25 * Tl * hp * np.exp(-((uf - 0.80) / 0.06) ** 2)
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
    return _ear_finish(np.array(rings) * MM, np.array(attrs), side, sdf, n_face, n_rim)


def _ear_finish(Rr, At, side, sdf, n_face, n_rim):
    """World placement, seating and the two-island split of v7.ear_arrays_v7."""
    nr, npr, _ = Rr.shape
    q = Rr.reshape(-1, 3).copy()
    q[:, 1] *= side
    base = A.ear_base.copy()
    base[1] *= side
    Ph = base + q @ v6.ear_frame(side).T
    Pw = Ph @ v6.head_R().T
    if sdf is not None:
        Pw = v7.seat_ear_columns(Pw.reshape(nr, npr, 3), At[:, 0, 0], side, sdf).reshape(-1, 3)
    A2 = At.reshape(-1, 3)
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
        A_list.append(At[:, c])
        nxt += nr
    tip_ids = []
    for strip in (0, 1):
        cols = inner_cols if strip == 0 else back_cols
        tip_ids.append(nxt)
        P_list.append(Pw.reshape(nr, npr, 3)[-1, cols].mean(0)[None] + ((np.array([0.0, 0.0, 0.2 * MM]) @ v6.ear_frame(side).T) @ v6.head_R().T)[None])
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
    attrs = dict(is_ear=np.ones(len(Pw)), ear_t=A2[:, 0], ear_u=A2[:, 1], ear_face=A2[:, 2])
    return Pw, np.array(quads), np.array(tris), attrs


def ear_q(Ph, s):
    """Ear-local coordinates (x toward the opening, y LATERAL, z up the
    axis), mm, for either ear. Round 5 used the raw frame's y, which is
    lateral on the left ear but medial on the right one."""
    base = A.ear_base * np.array([1.0, s, 1.0])
    q = (Ph - base) @ v6.ear_frame(s) / MM
    return q[..., 0], q[..., 1] * s, q[..., 2]


# conchal funnel carved under each pinna (ear-local mm): a round cone from
# the opening down toward the scanned ear-canal pit, carved with a wide
# smooth blend, so the head surface dips smoothly into the concha (round 5's
# prism cup left a crater and a scalp tab inside the ear)
FUNNEL_TOP = (20.0, 6.0, -2.0)
FUNNEL_BOT = (8.0, 8.0, -30.0)
FUNNEL_R = (14.0, 6.0)
# the bowl inside the pinna's U (ear-local centre and radii, mm): it reaches
# the back and side walls of the pinna and, at the open front, slopes down
# into the concha
BOWL_C = (26.0, 0.0, -8.0)
BOWL_R = (27.0, 46.0, 22.0)


def funnel_sd_mm(Ph, s):
    x, y, z = ear_q(Ph, s)
    q = np.stack([x, y, z], -1)
    d = v6.sd_capsule(q, np.array(FUNNEL_TOP), np.array(FUNNEL_BOT), FUNNEL_R[0], FUNNEL_R[1])
    return v6.smin(d, v6.sd_ellipsoid(q, np.array(BOWL_C), np.array(BOWL_R)), 6.0)


def scan_head_neck_v8(P):
    Pmm = np.asarray(P, float) / MM
    d = v7.scan_sdf_world(P) + v7.fur_inset_mm(Pmm) * MM
    Ph = np.asarray(P, float) @ v6.head_R()
    for s in (1.0, -1.0):
        d = v6.smax(d, -funnel_sd_mm(Ph, s) * MM, 6.0 * MM)
    return v6.smax(d, (v7.Z_CUT - Pmm[..., 2]) * MM, v7.K_CUT * MM)


def cup_weight_v8(Pw):
    """1 on head skin inside or at the rim of a conchal funnel (pale inner-ear
    skin and short pale hair there), 0 elsewhere."""
    Ph = np.asarray(Pw, float) @ v6.head_R()
    w = np.zeros(Ph.shape[:-1])
    for s in (1.0, -1.0):
        w = np.maximum(w, 1.0 - smoothstep(-1.0, 4.0, funnel_sd_mm(Ph, s)))
    return w


def ear_behind_weight(Ph):
    """ear_near_weight restricted to the head skin behind each pinna's back
    wall (ear-local x < ~10 mm): only there is the head coat combed up onto
    the ear back; in front of and lateral to the opening it keeps the head
    flow (hair combed up the ear axis there passed through the curled pinna
    and printed dark specks on its inner face)."""
    w = np.zeros(Ph.shape[:-1])
    for s in (1.0, -1.0):
        x, y, z = ear_q(Ph, s)
        e = np.sqrt(((x - 30.0) / 42.0) ** 2 + (y / 60.0) ** 2 + (z / 22.0) ** 2)
        w = np.maximum(w, (1.0 - smoothstep(0.85, 1.25, e)) * (1.0 - smoothstep(0.0, 10.0, x)))
    return w


def ear_near_weight(Ph):
    """~1 on the head skin round each ear base (within ~12 mm of the pinna
    base), 0 away from it; plus the ear-local frame for the flow."""
    w = np.zeros(Ph.shape[:-1])
    for s in (1.0, -1.0):
        x, y, z = ear_q(Ph, s)
        e = np.sqrt(((x - 30.0) / 42.0) ** 2 + (y / 60.0) ** 2 + (z / 22.0) ** 2)
        w = np.maximum(w, 1.0 - smoothstep(0.85, 1.25, e))
    return w


# ---------------------------------------------------------------------------
# Skin: bust, insets and surface details (round 6)
# ---------------------------------------------------------------------------

BUST_DX = -12.0
BUST_DZ = 18.0


def build_bust_ops_v8():
    """Round 6 bust (judged round 5: shoulders wider than the head, a long
    neck pinched under the jaw, a meerkat bust). The deltoids and arms move
    ~20 mm medially (shoulder skin half-width ~1.2x the cheek, ~1.1x with
    fur), the arms stay separate from a narrower, keel-shaped chest (a
    forward manubrium between the pectorals), the whole bust sits 18 mm
    higher and 12 mm further back (a shorter neck; the head is carried lower
    and further forward), and a throat fill makes chin, throat and chest one
    full line."""
    R = v6.rot_matrix
    dx, dz = BUST_DX, BUST_DZ

    def p(x, y, z):
        return (x + dx, y, z + dz)

    ops = []
    for s in (1.0, -1.0):
        ops.append(v6.cap_op(p(-58.0, 26.0 * s, -92.0), p(-58.0, 76.0 * s, -150.0), 26.0, 28.0, 34, frame="body"))
        ops.append(v6.ell_op(p(-80.0, 52.0 * s, -190.0), (16.0, 34.0, 60.0), R(roll=-14.0 * s), 30, frame="body"))
        ops.append(v6.ell_op(p(-36.0, 88.0 * s, -184.0), (32.0, 24.0, 54.0), R(roll=-10.0 * s), 30, frame="body"))
        ops.append(v6.cap_op(p(-30.0, 94.0 * s, -212.0), p(-16.0, 106.0 * s, -424.0), 27.0, 24.0, 22, frame="body"))
        ops.append(v6.ell_op(p(24.0, 40.0 * s, -202.0), (30.0, 40.0, 46.0), R(yaw=18.0 * s, roll=-10.0 * s), 30, frame="body"))
    ops.append(v6.cap_op(p(-30.0, 0.0, -96.0), p(-40.0, 0.0, -178.0), 72.0, 80.0, 30, frame="body"))
    ops.append(v6.ell_op(p(54.0, 0.0, -172.0), (26.0, 24.0, 44.0), None, 24, frame="body"))  # manubrium: keel
    ops.append(v6.ell_op((52.0, 0.0, -120.0), (34.0, 46.0, 40.0), None, 26, frame="body"))  # throat fill
    ops.append(v6.ell_op(p(-34.0, 0.0, -318.0), (96.0, 92.0, 205.0), None, 44, frame="body"))  # thorax
    return ops


def fur_inset_mm_v8(Pw_mm):
    """Round 5's insets with a thinner throat (7 -> 4.5 mm) and neck (15 ->
    11 mm) inset: the round-6 bib and neck ruff are shorter, and the neck
    must read full rather than pinched under the jaw."""
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
    t = t + (4.5 - t) * throat
    neck = smoothstep(-66.0, -100.0, z)
    t = t + (11.0 - t) * neck
    for s in (1.0, -1.0):
        c = v6.eye_center(s) @ v6.head_R().T / MM
        d = np.sqrt((Pw_mm[..., 0] - c[0]) ** 2 + (Pw_mm[..., 1] - c[1]) ** 2 + (Pw_mm[..., 2] - c[2]) ** 2)
        t = t + (0.8 - t) * (1.0 - smoothstep(26.0, 36.0, d))
    return t


LEATHER_SCALE = 0.8
LIP_SIDE_V8 = [(9.0, -34.4), (12.5, -35.9), (16.5, -38.0), (20.5, -40.8), (23.5, -43.6)]
LOWER_LIP = (0.0, -41.0, 7.0, 3.0, 0.7)  # (y, z, ry, rz, height mm)


def scale_about(poly, c, k):
    return [((a - c[0]) * k + c[0], (b - c[1]) * k + c[1]) for a, b in poly]


def build_detail_ops_v8():
    """Round-5 detail ops with round-6 changes: a 0.8x leather with a
    crisper top edge (blend 0.45 mm), taller alar wings curling over comma-
    shaped nostrils (a round, 1.2 mm bulb low beside the septum tapering up
    and out), a philtrum groove that splits the leather's lower edge, a lip
    margin that runs from the Y out to the mouth corners under the pads, and
    a small lower lip under the Y."""
    ops = []
    mz = A.mz
    lp = v6.leather_poly()
    alar = [np.asarray([(y * s, z) for y, z in v6.ALAR_POLY]) for s in (1.0, -1.0)]

    def leather(P, B):
        q = np.stack([P[..., 1], P[..., 2]], -1) / MM
        d2 = v6.sd_poly2d(q, lp) * MM
        da = np.minimum(v6.dist_poly2d(q, alar[0]), v6.dist_poly2d(q, alar[1]))
        h = 1.25 + 1.0 * np.exp(-(da / 1.2) ** 2)
        d = np.maximum(d2, B - h * MM)
        return np.maximum(d, v6.NOSE_X0 * MM - P[..., 0])

    ops.append(v6.Op("union", leather, v6.v(v6.NOSE_X0, -14.0, -17.0), v6.v(v6.NOSE_X0 + 40.0, 14.0, 12.0), 0.45 * MM))
    for s in (1.0, -1.0):
        def pad(P, B, s_=s):
            y, z, x = P[..., 1] / MM, P[..., 2] / MM, P[..., 0] / MM
            w = np.exp(-((y - v6.PAD_C[1] * s_) / v6.PAD_R[0]) ** 2 - ((z - v6.PAD_C[2]) / v6.PAD_R[1]) ** 2)
            w = w * smoothstep(104.0 + mz, 118.0 + mz, x)
            return B - v6.PAD_H * MM * w

        ylo, yhi = sorted(((v6.PAD_C[1] - 30.0) * s, (v6.PAD_C[1] + 30.0) * s))
        ops.append(v6.Op("union", pad, v6.v(100.0 + mz, ylo, -52.0), v6.v(160.0 + mz, yhi, -2.0), 0.6 * MM))

    def lower_lip(P, B):
        y, z, x = P[..., 1] / MM, P[..., 2] / MM, P[..., 0] / MM
        w = np.exp(-((y - LOWER_LIP[0]) / LOWER_LIP[2]) ** 2 - ((z - LOWER_LIP[1]) / LOWER_LIP[3]) ** 2)
        w = w * smoothstep(104.0 + mz, 118.0 + mz, x)
        return B - LOWER_LIP[4] * MM * w

    ops.append(v6.Op("union", lower_lip, v6.v(100.0 + mz, -25.0, -52.0), v6.v(160.0 + mz, 25.0, -28.0), 0.6 * MM))
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
        ops.append(v6.Op("subtract", (lambda s_: lambda P, B=None: v6.sd_fissure(P, s_))(s), c - 0.045, c + 0.045, 1.2 * MM))
    for s in (1.0, -1.0):
        poly = [(y * s, z) for y, z in v6.NOSTRIL_POLY]
        ops.append(v6.groove_op(poly, (1, 2), 0, v6.NOSE_X0, v6.NOSE_X0 + 47.0, v6.NOSTRIL_W, v6.NOSTRIL_D, 0.4))
    ops.append(v6.groove_op(v6.PHILTRUM, (1, 2), 0, 118.0 + mz, 175.0 + mz, [0.40, 0.55, 0.65], [1.1, 1.4, 1.5], 0.7))
    for s in (1.0, -1.0):
        poly = [(y * s, z) for y, z in v6.LIP_FRONT]
        ops.append(v6.groove_op(poly, (1, 2), 0, 100.0 + mz, 175.0 + mz, [0.55, 0.5, 0.45, 0.4], [1.8, 2.0, 1.7, 1.2], 0.8))
        poly = [(y * s, z) for y, z in LIP_SIDE_V8]
        ops.append(v6.groove_op(poly, (1, 2), 0, 90.0 + mz, 175.0 + mz, [0.40, 0.38, 0.36, 0.34, 0.25], [1.2, 1.1, 1.0, 0.9, 0.5], 0.7))
    return ops


# ---------------------------------------------------------------------------
# Markings, follicles and coat fields (round 6)
# ---------------------------------------------------------------------------

# Round 6 (judged round 5: a straight, hard 'glasses arm' from the eye to the
# ear; blurry marble instead of crisp mackerel strokes; no readable M): the
# cheek line leaves the lateral canthus and curves down and back across the
# cheek, stopping well short of the ear, with a second line below it; the M
# strokes, central bar and crown lines are ~1.35x broader (the face fur is
# also shorter, so strokes no longer smear along the hair).
MARKINGS_V8 = [
    ("mascara", [(84, 59, 22), (76, 66, 16), (67, 72, 8), (57, 77, -1), (47, 80, -10), (38, 81, -18)], [0.8, 1.4, 1.8, 1.8, 1.4, 0.5]),
    ("cheek2", [(79, 57, 2), (70, 65, -7), (60, 72, -16), (50, 76, -24), (41, 77, -31)], [0.6, 1.3, 1.6, 1.3, 0.5]),
    ("cheek3", [(64, 62, -30), (54, 68, -38), (44, 71, -45), (35, 70, -50)], [0.5, 1.0, 1.0, 0.4]),
    ("m_outer", [(92, 34, 43), (88, 29, 50), (83, 22, 58), (79, 16, 63)], [3.0, 3.9, 3.9, 3.3]),
    ("m_inner", [(79, 14, 63), (83, 9, 57), (87, 4.5, 51), (89, 1.5, 47)], [3.1, 2.8, 2.4, 1.9]),
    ("m_center", [(90, 0, 46), (84, 0, 55), (76, 0, 64), (62, 0, 74), (44, 0, 82), (10, 0, 89), (-24, 0, 88), (-56, 0, 72), (-80, 0, 44), (-94, 0, 12)],
     [2.4, 3.4, 4.0, 4.1, 3.9, 4.0, 4.1, 4.1, 4.0, 3.4]),
    ("crown_a", [(77, 19, 65), (61, 20, 75), (41, 21, 83), (16, 22, 88), (-14, 23, 88), (-46, 25, 77), (-72, 27, 53), (-88, 29, 23), (-96, 30, -5)],
     [3.3, 3.9, 4.3, 4.5, 4.5, 4.5, 4.3, 4.2, 3.8]),
    ("crown_lat", [(74, 47, 51), (61, 44, 62), (47, 41, 72), (34, 39, 78)], [1.6, 2.4, 2.2, 1.0]),
    ("lacrimal", [(89, 17.5, 12), (95, 15.5, 5), (101, 14.0, -1), (106, 13.0, -5)], [0.55, 0.5, 0.4, 0.2]),
]
# stripe edge half-widths (mm) per marking: 0.7 mm gives the 1-2 mm hair-
# level edges asked for; the cheek lines are softer
MARK_EDGE = {"mascara": 1.3, "cheek2": 1.3, "cheek3": 1.3, "lacrimal": 0.6, "crown_lat": 1.1}


def follicle_grid():
    """Mystacial follicles on one side (head frame y, z mm): 4 orderly rows of
    4, following the pad's curvature; returns (row, col, y, z)."""
    out = []
    for row in range(4):
        for col in range(4):
            y = 10.0 + 4.6 * col + 1.3 * row
            z = -19.0 - 4.4 * row - 1.2 * col - 0.25 * col * col
            out.append((row, col, y, z))
    return out


def mystacial_roots_v8():
    """Whisker-bearing follicles: every follicle except the most rostral
    column (12 per side), at the head-frame (y, z) of the follicle; x is
    found on the skin by the vibrissa builder."""
    out = []
    for s in (1.0, -1.0):
        for row, col, y, z in follicle_grid():
            if col == 0:
                continue
            out.append((s, row, col - 1, np.array([v6.NOSE_X0 - 6.0, y * s, z])))
    return out


def dist_fields_per_marking(P3):
    curves = v6.marking_curves()
    names = [m_[0] for m_ in v6.MARKINGS for _ in (1.0, -1.0)]
    out = {}
    for nm, cv in zip(names, curves):
        d = v6.dist_to_curves(P3, [cv])
        out[nm] = np.minimum(out.get(nm, np.full(len(P3), 1e3)), d)
    return out


def ear_vessels(ear_t, ear_u):
    """Branching vessel lines on the inner pinna (ear t/u space): three main
    trunks running up the pinna with side branches."""
    d = np.full(ear_t.shape, 1e3)
    for k, (u0, amp, ph) in enumerate(((-0.35, 0.05, 0.3), (0.05, 0.06, 1.7), (0.42, 0.05, 2.9))):
        uc = u0 + amp * np.sin(ear_t * 9.0 + ph) + 0.02 * np.sin(ear_t * 23.0 + 2 * ph)
        d = np.minimum(d, np.abs(ear_u - uc) / (0.018 * (1.2 - 0.6 * ear_t)))
        for b in range(3):
            tb = 0.25 + 0.2 * b + 0.05 * k
            ub = uc + (ear_t - tb) * (0.9 if (k + b) % 2 else -0.9)
            seg = _bump(ear_t, tb, tb + 0.16)
            d = np.minimum(d, np.abs(ear_u - ub) / (0.010 * seg + 1e-4) + 3.0 * (1.0 - seg))
    return 0.8 * np.exp(-d * d) * smoothstep(0.08, 0.22, ear_t) * (1.0 - smoothstep(0.85, 0.97, ear_t))


def coat_fields_v8(Pw, Nw, ex=None):
    """Round 6 coat, region and groom fields (consolidates v6.coat_fields and
    v7.coat_fields_v7). Keys as before plus `vessel`, `rim` (nose-leather
    margin) and `follicle`, baked to T_CatBaseV6_Detail."""
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
    cup = cup_weight_v8(Pw) * (~earm)

    # ---- white: muzzle, blaze, chin, throat, bib
    muz = np.sqrt(((x - 124 - mz) / 32) ** 2 + (y / 40) ** 2 + ((z + 36) / 27) ** 2)
    d_white = (muz - 1.0) * 26.0
    muz2 = np.sqrt(((x - 126.0 - mz) / 34.0) ** 2 + (y / 45.0) ** 2 + ((z + 29.0) / 30.0) ** 2)
    d_white = np.minimum(d_white, (muz2 - 1.0) * 26.0)
    wb2 = np.clip(17.0 - 0.30 * (z + 5.0), 4.0, 17.0)
    d_white = np.minimum(d_white, np.maximum(np.maximum(ay - wb2, z - 44.0), 96.0 - x))
    chin = (np.sqrt(((x - 104 - mz) / 26) ** 2 + (y / 30) ** 2 + ((z + 68) / 18) ** 2) - 1.0) * 18.0
    d_white = np.minimum(d_white, chin)
    throat = np.maximum(np.maximum(ay - 32.0 - 0.30 * np.clip(-60 - z, 0, 90), z + 58.0), 18.0 - x)
    d_white = np.minimum(d_white, throat)
    wbib = 28.0 + 0.32 * np.clip(-95.0 - zw, 0.0, 400.0) - 0.0006 * np.clip(-95.0 - zw, 0.0, 400.0) ** 2
    bib = np.maximum(np.maximum(ay - wbib, zw + 80.0), -(Nw[:, 0] + 0.05) * 60.0)
    d_white = np.minimum(d_white, bib)
    d_white = np.where(earm, 1e3, d_white)
    body_w = smoothstep(-110.0, -160.0, zw)
    lobes = (v6.fbm(Pw, 0.030, 3, 21.0) - 0.5) * (8.0 + 24.0 * body_w) + (v6.fbm(Pw, 0.060, 2, 31.0) - 0.5) * 40.0 * body_w
    fing = (v6.fbm(Pw * np.array([1.0, 1.0, 0.22]), 0.0045, 2, 23.0) - 0.5) * (3.0 + 9.0 * body_w)
    # round 6: flow-aligned (vertical) interlocking streaks, 2-4 mm wide,
    # along the bib boundary, so white and tabby interlock raggedly
    streak = (v6.fbm(Pw * np.array([1.0, 1.0, 0.12]), 0.0028, 3, 29.0) - 0.5) * (4.0 + 20.0 * smoothstep(-95.0, -140.0, zw))
    ew = 0.3 + 2.2 * smoothstep(-95.0, -140.0, zw)
    white = 1.0 - smoothstep(-ew, ew, d_white + jit + lobes + fing + streak)

    # ---- mackerel strokes (per-marking edge softness)
    dm = dist_fields_per_marking(P3)
    stripe = np.zeros(n)
    for nm, d in dm.items():
        e = MARK_EDGE.get(nm, edge)
        wj = 1.0 if nm not in MARK_EDGE else 1.8
        stripe = np.maximum(stripe, 1.0 - smoothstep(-e, e, d + wj * jit))
    ang = np.arctan2(yw, xw + 40.0)
    zz = zw + 5.0 * np.sin(ang * 2.0 + 0.7) + 3.0 * np.sin(ang * 5.0 + 1.3)
    per = 34.0
    ph_ = np.mod(zz + 8.0, per) - 0.5 * per
    wband = 5.6 + 1.2 * np.sin(ang * 3.0)
    body_band = (np.abs(ph_) - wband) * smoothstep(-30.0, -70.0, zw)
    dors = np.maximum(ay - 8.0, xw + 60.0) + 1e3 * (zw > -20.0)
    d_body = np.minimum(body_band + 1e3 * (zw > -80.0), dors)
    stripe = np.maximum(stripe, 1.0 - smoothstep(-edge, edge, d_body + jit))
    # ears: dark tabby back, darker to the tip, a pale thumbprint; the rim
    # hair is agouti ground; the inner face is white
    thumb = _bump(ear_t, 0.30, 0.60) * _bump(ear_u, -0.30, 0.40) * back
    ear_rim_c = smoothstep(0.86, 0.98, au)
    ear_back_dark = (0.62 + 0.25 * smoothstep(0.70, 0.95, ear_t)) * (1.0 - 0.3 * ear_rim_c)
    stripe = np.where(earm, np.where(inner, 0.0, ear_back_dark), stripe)
    white = np.where(inner, 1.0, white)
    stripe = np.clip(stripe * (1.0 - 0.6 * thumb), 0.0, 1.0)
    # pale conchal bowl / funnel hair
    white = np.maximum(white, 0.6 * smoothstep(0.3, 0.7, cup))
    stripe = np.clip(stripe * (1.0 - white) * (1.0 - cup), 0.0, 1.0)

    # ---- follicles (skin dots, grey-pink, no dark hair)
    on_pad = smoothstep(112.0 + mz, 120.0 + mz, x) * smoothstep(0.15, 0.40, Nh[:, 0])
    fol_d = np.full(n, 1e3)
    m_pad = on_pad > 0
    if m_pad.any():
        fg = np.array([(yy, zz_) for _, col, yy, zz_ in follicle_grid()])
        rad = np.array([0.42 if col == 0 else 0.55 for _, col, _, _ in follicle_grid()])
        q = np.stack([ay[m_pad], z[m_pad]], -1)
        dd = np.linalg.norm(q[:, None, :] - fg[None], axis=-1) - rad[None]
        fol_d[m_pad] = dd.min(1)
    follicle = (1.0 - smoothstep(-0.15, 0.25, fol_d)) * on_pad

    # ---- eyes: fissure distance (mm; + outside the aperture)
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
    pale = np.clip(np.maximum(0.6 * spect, 0.6 * thumb), 0.0, 1.0) * (1.0 - cup)

    # ---- regions
    q2 = np.stack([y, z], -1)
    d_leather = v6.sd_poly2d(q2, v6.leather_poly())
    nose = (1.0 - smoothstep(-0.25, 0.25, d_leather)) * smoothstep(v6.NOSE_X0 - 3.0, v6.NOSE_X0 + 1.0, x) * smoothstep(-0.25, 0.05, Nh[:, 0])
    rim = (1.0 - smoothstep(0.35, 0.95, -d_leather)) * nose
    pig = np.zeros(n)
    pig = np.maximum(pig, 1.0 - smoothstep(0.5, 1.0, np.abs(d_fis)))
    pig = np.maximum(pig, 0.65 * (1.0 - smoothstep(2.0, 3.5, d_fis)) * (d_fis > 0))
    pig = np.maximum(pig, (d_fis < 0).astype(float) * near_eye)
    fr = smoothstep(v6.NOSE_X0 - 6.0, v6.NOSE_X0, x)
    for s in (1.0, -1.0):
        poly = [(yy * s, zz_) for yy, zz_ in v6.NOSTRIL_POLY]
        dn = v6.dist_poly2d(q2, poly) - 0.45
        pig = np.maximum(pig, 0.75 * (1.0 - smoothstep(0.0, 0.35, dn)) * fr)
    lipd = np.full(n, 1e3)
    for s in (1.0, -1.0):
        lipd = np.minimum(lipd, v6.dist_poly2d(q2, [(yy * s, zz_) for yy, zz_ in v6.LIP_FRONT]))
        lipd = np.minimum(lipd, v6.dist_poly2d(q2, [(yy * s, zz_) for yy, zz_ in LIP_SIDE_V8]))
    lipf = smoothstep(110.0 + mz, 118.0 + mz, x) * smoothstep(0.1, 0.35, Nh[:, 0])
    pig = np.maximum(pig, 0.70 * (1.0 - smoothstep(0.40, 0.80, lipd)) * lipf)
    d_lac = dm.get("lacrimal", np.full(n, 1e3))
    pig = np.maximum(pig, 0.45 * (1.0 - smoothstep(-0.1, 0.5, d_lac + 0.4 * jit)))
    pig = np.where(earm, 0.0, pig)
    lipm = (1.0 - smoothstep(0.30, 0.55, lipd)) * lipf
    # inner-ear skin 1.0 (pale, vascular, translucent), ear back 0.5
    # (translucent under the coat), conchal funnel skin like the inner face
    conch = inner * (1.0 - smoothstep(0.0, 0.30, ear_t)) * (1.0 - smoothstep(0.45, 0.9, au))
    ear_in = np.where(inner, 1.0, np.where(back, 0.5, 0.0))
    ear_in = np.maximum(ear_in, cup)
    pig = np.maximum(pig, np.maximum(0.55 * conch, 0.6 * cup))
    vessel = np.where(inner, ear_vessels(ear_t, ear_u), 0.0)

    # ---- groom: length (mm), lift (deg), density
    keys = [
        ((141 + mz, 0, -8), 1.8, 8), ((130 + mz, 0, 12), 2.4, 10), ((112 + mz, 0, 32), 3.0, 11), ((95, 0, 52), 3.8, 13), ((64, 0, 72), 5.0, 17),
        ((15, 0, 88), 6.5, 22), ((-35, 0, 82), 8.5, 24), ((-72, 0, 42), 12.0, 22), ((-90, 0, 0), 15.0, 22),
        ((136 + mz, 14, -24), 2.2, 9), ((130 + mz, 26, -34), 2.8, 10), ((114 + mz, 33, -46), 3.4, 10), ((112 + mz, 0, -62), 3.0, 10), ((84, 0, -80), 6.5, 10),
        ((92, 40, 21), 2.2, 12), ((86, 36, 44), 2.8, 8), ((80, 62, 5), 4.2, 13), ((50, 82, 5), 6.5, 14), ((24, 86, -18), 12.0, 16),
        ((4, 80, -44), 15.0, 18), ((32, 72, -42), 10.0, 14), ((46, 0, -86), 11.0, 18), ((0, 62, 70), 5.0, 13),
        ((-40, 55, 50), 8.0, 20), ((-70, 60, 10), 14.0, 22),
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
    bodyL = 16.0 + 7.0 * ruff + 10.0 * neck + 3.0 * smoothstep(-150.0, -300.0, zw)
    arm = smoothstep(70.0, 100.0, ay) * smoothstep(-150.0, -210.0, zw)
    bodyL = bodyL * (1.0 - 0.35 * arm)
    Lh = headL * headw + bodyL * (1.0 - headw)
    # periocular: <= 1 mm within ~3.5 mm of the lid margin, blending out by 6 mm
    wper = 1.0 - smoothstep(3.5, 6.5, np.maximum(d_fis, 0.0))
    Lh = Lh * (1.0 - wper) + np.minimum(Lh, 1.0) * wper
    # head skin round the ear bases: short, flat coat that runs on into the
    # ear-back coat (no collar)
    near = ear_near_weight(Ph) * (1.0 - smoothstep(0.3, 0.6, cup))
    Lh = Lh * (1.0 - near) + np.minimum(Lh, 3.0) * near
    # head coat just lateral to and in front of the pinna's lateral margin
    # (which runs down the side of the head): short, so it cannot lie across
    # the margin onto the inner face (round-6 test frames: dark specks there)
    latm = np.zeros(n)
    for s_ in (1.0, -1.0):
        ex_, ey_, ez_ = ear_q(Ph, s_)
        latm = np.maximum(latm, smoothstep(18.0, 34.0, ey_) * (1.0 - smoothstep(52.0, 64.0, ey_)) * _bump(ex_, -6.0, 62.0) * (1.0 - smoothstep(14.0, 26.0, ez_)) * smoothstep(-40.0, -26.0, ez_))
    latm = latm * (~earm)
    Lh = Lh * (1.0 - latm) + np.minimum(Lh, 1.8) * latm
    # pinna
    rimz = smoothstep(0.86, 0.98, au)
    L_back = (3.8 - 1.2 * smoothstep(0.55, 1.0, ear_t)) * (1.0 - 0.35 * rimz)
    L_back = L_back + (4.0 - L_back) * (1.0 - smoothstep(0.0, 0.18, ear_t))
    pocket = _bump(ear_t, 0.03, 0.28) * smoothstep(0.50, 0.75, ear_u)
    L_back = L_back * (1.0 - 0.45 * pocket)
    low_med = (1.0 - smoothstep(-0.55, -0.25, ear_u)) * (1.0 - smoothstep(0.32, 0.48, ear_t))
    lat_band = smoothstep(0.80, 0.90, ear_u)
    L_in = 1.8 + 1.8 * low_med + 1.0 * lat_band
    L = np.where(earm, np.where(inner, L_in, L_back), Lh)
    L = np.where(cup > 0.5, 5.0, L)
    L = L * (0.94 + 0.12 * v6.fbm(Pw, 0.012, 2, 2.0))
    # lift
    lift_h = (5.0 + 3.0 * smoothstep(40.0, 80.0, z) * (1 - np.clip(-zw / 100.0, 0, 1))
              + 8.0 * np.exp(-((x - 18) ** 2 + (ay - 82) ** 2 + (z + 34) ** 2) / 1100.0))
    throat_front = smoothstep(0.2, 0.7, Nw[:, 0])
    lift_b = 12.0 + 4.0 * ruff + 14.0 * neck * (1.0 - 0.8 * throat_front) - 3.0 * arm
    hb = np.maximum(smoothstep(-60.0, -125.0, zw), neckm)
    lift = lift_h * (1.0 - hb) + lift_b * hb
    lift = lift - 3.0 * np.exp(-((x - 122 - mz) ** 2 + (ay - 20) ** 2 + (z + 32) ** 2) / 500.0)
    lift = lift * (1.0 - wper) + np.minimum(lift, 3.0) * wper
    lift = lift * (1.0 - near) + np.minimum(lift, 3.0) * near
    lift = lift * (1.0 - latm) + np.minimum(lift, 1.5) * latm
    lift = np.where(earm, np.where(inner, 10.0 + 8.0 * low_med, 1.5 + 1.5 * rimz), lift)
    lift = np.where(cup > 0.5, 26.0, lift)
    # density
    density = np.clip(7.0 / np.maximum(L, 1.0), 0.35, 1.0)
    deep = (1.0 - smoothstep(0.05, 0.14, ear_t)) * (1.0 - smoothstep(0.45, 0.7, au))
    inner_d = np.clip(0.10 + 0.30 * low_med + 0.30 * lat_band, 0.0, 0.5) * (1.0 - deep)
    back_d = 0.72 - 0.15 * smoothstep(0.6, 1.0, ear_t) + 0.15 * rimz
    density = np.where(earm, np.where(inner, inner_d, back_d), density)
    density = np.where(cup > 0.5, 0.30, density)
    density = density * smoothstep(-598.0, -585.0, zw)
    # sharp exclusions (fur mask): leather (with a jittered top edge the
    # bridge hair reaches), lip margin, nostrils, follicle centres, the
    # fissure (fur within ~0.6-1.0 mm of it)
    topw = smoothstep(-2.0, 2.0, z - 2.0)
    nose_ex = (1.0 - smoothstep(-0.25, 0.25, d_leather + 0.45 * topw + 0.25 * jit * topw)) * smoothstep(v6.NOSE_X0 - 3.0, v6.NOSE_X0 + 1.0, x) * smoothstep(-0.25, 0.05, Nh[:, 0])
    excl = (1.0 - nose_ex) * (1.0 - lipm) * smoothstep(0.35, 0.75, d_fis)
    for s in (1.0, -1.0):
        dn = v6.dist_poly2d(q2, [(yy * s, zz_) for yy, zz_ in v6.NOSTRIL_POLY]) - 0.9
        excl = excl * np.where(x > v6.NOSE_X0 - 4.0, smoothstep(0.0, 1.0, dn), 1.0)
    excl = excl * (1.0 - 0.85 * (1.0 - smoothstep(-0.1, 0.25, fol_d)) * on_pad)
    excl = np.where(earm, 1.0, excl)
    return dict(white=np.clip(white, 0, 1), stripe=np.clip(stripe, 0, 1), pale=pale, nose=nose, pig=np.clip(pig, 0, 1), ear_inner=ear_in,
                length=L * MM, density=np.clip(density, 0, 1), excl=np.clip(excl, 0, 1), lift=lift, d_fis=d_fis, lip=lipm,
                vessel=np.clip(vessel, 0, 1), rim=np.clip(rim, 0, 1), follicle=np.clip(follicle, 0, 1), cup=cup, near_ear=near)


def fur_direction_v8(Pw, Nw, ex=None):
    """Round 6 flow (v6.fur_direction + v7's ear rules) with two changes:

    - body: hair flows down and OUT from the neck axis ((-0.25, 0, -1) plus
      0.55x the horizontal outward direction from the neck axis), so it is
      combed from the nape over the shoulder blades and down the chest and
      arms with no singular point on the shoulders (round 5's single
      down-and-back direction degenerated where the shoulder normal faced it
      and grew a whorl, a 'pom-pom', on each shoulder);
    - the head coat round each ear base turns up the ear's axis, and the ear
      back hair near the rims turns slightly outward so its tips overhang
      the margin by 1-2 mm."""
    Pw = np.asarray(Pw, float)
    Nw = np.asarray(Nw, float)
    n = len(Pw)
    is_ear, ear_t, ear_u, ear_face = v6.ex_arrays(n, ex)
    earm = is_ear > 0.5
    Ph = Pw @ v6.head_R()
    Nh = Nw @ v6.head_R()
    P3 = Ph / MM
    x, y, z = P3[:, 0], P3[:, 1], P3[:, 2]
    ay = np.abs(y)
    sy = np.where(y >= 0, 1.0, -1.0)
    src = np.array([168.0 + A.mz, 0.0, -14.0])
    vh = P3 - src
    vh /= np.linalg.norm(vh, axis=1, keepdims=True) + 1e-9
    for s in (1.0, -1.0):
        c = np.array([127.0 + A.mz, v6.PAD_C[1] * s, v6.PAD_C[2]])
        w = np.exp(-np.sum((P3 - c) ** 2, 1) / (15.0 ** 2))[:, None]
        r = P3 - c
        r /= np.linalg.norm(r, axis=1, keepdims=True) + 1e-9
        vh = vh * (1 - w) + r * w
    wj = (smoothstep(55.0, 78.0, ay) * smoothstep(12.0, -25.0, z))[:, None]
    ruffdir = np.stack([np.full(n, -0.62), 0.12 * sy, np.full(n, -0.78)], 1)
    vh = vh * (1 - 0.75 * wj) + ruffdir * 0.75 * wj
    bdir_w = np.array([-0.55, 0.0, -0.84])
    bdir_w /= np.linalg.norm(bdir_w)
    bdir_h = bdir_w @ v6.head_R()
    wc = (smoothstep(-50.0, -64.0, z) * smoothstep(30.0, 60.0, x) * (1 - smoothstep(40.0, 60.0, ay)))[:, None]
    vh = vh * (1 - 0.7 * wc) + bdir_h * 0.7 * wc
    for s in (1.0, -1.0):
        c = v6.eye_center(s) / MM
        q = P3 - c
        m = np.linalg.norm(q, axis=1) < 45.0
        if not m.any():
            continue
        d2 = v6.sd_fissure(Ph[m], s) / MM
        qm = q[m] - np.sum(q[m] * Nh[m], 1, keepdims=True) * Nh[m]
        rhat = qm / (np.linalg.norm(qm, axis=1, keepdims=True) + 1e-9)
        comp = np.sum(vh[m] * rhat, 1, keepdims=True)
        near = np.exp(-(np.maximum(d2, 0.0) / 9.0) ** 2)[:, None]
        vh[m] = vh[m] - rhat * np.minimum(comp, 0.0) * near + rhat * (0.9 * np.exp(-(np.maximum(d2, 0.0) / 3.0) ** 2))[:, None]
    vw = vh @ v6.head_R().T
    # head coat round the ear bases: up the ear axis (continuous with the
    # ear-back coat)
    near_e = ear_behind_weight(Ph)
    cup = cup_weight_v8(Pw) * (~earm)
    for s in (1.0, -1.0):
        F = v6.ear_frame(s)
        ax = F[:, 2] @ v6.head_R().T
        lat = (F[:, 1] * s) @ v6.head_R().T
        m = earm & (sy == s)
        if m.any():
            rim = smoothstep(0.78, 0.97, np.abs(ear_u[m]))[:, None]
            out_ = np.sign(ear_u[m])[:, None] * lat[None, :]
            inner = (ear_face[m] > 0.2)[:, None]
            k_out = np.where(inner, 0.25, 0.40)
            vw[m] = ax[None, :] * (1.0 - k_out * rim) + out_ * k_out * rim
        mh = (~earm) & (sy == s)
        if mh.any():
            wn = (0.8 * near_e[mh])[:, None]
            vw[mh] = vw[mh] * (1.0 - wn) + ax[None, :] * np.linalg.norm(vw[mh], axis=1, keepdims=True) * wn
        mc = (cup > 0.3) & (sy == s)
        if mc.any():
            vw[mc] = ax[None, :]
    # body: down and out from the neck axis
    zw = Pw[:, 2] / MM
    hb = smoothstep(-55.0, -130.0, zw)[:, None]
    hout = np.stack([Pw[:, 0] / MM + 30.0, Pw[:, 1] / MM, np.zeros(n)], 1)
    hout /= np.linalg.norm(hout, axis=1, keepdims=True) + 1e-9
    down = np.array([-0.25, 0.0, -1.0])[None, :] + 0.55 * hout
    vw = np.where(earm[:, None], vw, vw * (1 - hb) + down * hb)
    t = vw - np.sum(vw * Nw, 1, keepdims=True) * Nw
    t /= np.linalg.norm(t, axis=1, keepdims=True) + 1e-9
    return t


# ---------------------------------------------------------------------------
# Texture bake with the extra detail map (round 6)
# ---------------------------------------------------------------------------

def bake_textures_v8(cage, res):
    """v6.bake_textures plus T_CatBaseV6_Detail (R inner-ear vessels, G nose-
    leather margin, B whisker follicles)."""
    t0 = time.time()
    S = v6.evaluated_surface(cage)
    UV = S["uv"][S["tl"]]
    tri, tex, bc = v6.rasterize_uv(UV, res)
    log(f"bake raster: {len(tex)} texel samples ({time.time()-t0:.0f}s)")
    maps = {k: np.zeros((res * res, 3), np.float32) for k in ("coat", "regions", "furmask", "detail")}
    cov = np.zeros(res * res, bool)
    step = 1_000_000
    for k0 in range(0, len(tex), step):
        tr = tri[k0:k0 + step]
        w = bc[k0:k0 + step]
        vid = S["tv"][tr]
        P = np.einsum("ij,ijk->ik", w, S["co"][vid])
        Nn = np.einsum("ij,ijk->ik", w, S["nr"][vid])
        Nn /= np.linalg.norm(Nn, axis=1, keepdims=True) + 1e-12
        ex = {k: np.einsum("ij,ij->i", w, S["attrs"][k][vid]) for k in v6.EAR_ATTRS}
        f = coat_fields_v8(P, Nn, ex)
        ti = tex[k0:k0 + step]
        maps["coat"][ti] = np.stack([f["white"], f["stripe"], f["pale"]], -1)
        maps["regions"][ti] = np.stack([f["nose"], f["pig"], f["ear_inner"]], -1)
        maps["furmask"][ti] = f["excl"][:, None]
        maps["detail"][ti] = np.stack([f["vessel"], f["rim"], f["follicle"]], -1)
        cov[ti] = True
    cov2 = cov.reshape(res, res)
    images = {}
    for name, key in (("Coat", "coat"), ("Regions", "regions"), ("FurMask", "furmask"), ("Detail", "detail")):
        a = v6.dilate(maps[key].reshape(res, res, 3), cov2, 10)
        images[key] = v6.save_png(f"T_CatBaseV6_{name}", a)
    log(f"baked maps {res}px ({time.time()-t0:.0f}s)")
    return images


# ---------------------------------------------------------------------------
# Materials (round 6)
# ---------------------------------------------------------------------------

def skin_material_v8(images):
    """Skin under the coat, nose leather, pigment, follicles and pinna skin.

    - nose leather: rose (0.34, 0.15, 0.14) with a darker rose-brown margin
      (Detail G), pebbled by a 0.25 mm cell normal plus a 0.7 mm octave with
      crevice darkening; roughness 0.48 on the top, 0.34 at the lower tip and
      round the nostrils;
    - pigmented lid, lip and nostril skin: near-black, roughness 0.45 (round
      5's 0.20 read as a grey plastic ribbon under the sky);
    - follicles (Detail B): grey-pink skin (0.20, 0.13, 0.13);
    - pinna: the inner skin darker than the face coat, pink-grey
      (0.27, 0.20, 0.19) with red vessels (Detail R, 0.55x), red subsurface
      (weight 0.20 x B^2, 1.0 mm: 0.20 on the inner face, 0.05 on the ear
      back, Regions B = 0.5), so the ear glows when backlit. A first
      0.45 / 1.5 mm setting rendered orange."""
    m, nt = v6.new_mat("M_CatBaseV6_Skin")
    out = N(nt, "ShaderNodeOutputMaterial", (1800, 0))
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
    c = v6.mix_rgb(nt, sc.outputs["Red"], c, (0.50, 0.44, 0.42), (-200, 600))
    # pinna skin: inner (B = 1) pink-grey with vessels; back (B = 0.5) keeps
    # the coat skin colour
    inner = mr(sr.outputs["Blue"], 0.7, 0.95, 0.0, 1.0, (-500, 200))
    vr = math_("MULTIPLY", sd.outputs["Red"], 0.55, (-400, 250))
    earc = v6.mix_rgb(nt, vr, (0.27, 0.20, 0.19), (0.21, 0.10, 0.095), (-200, 250))
    c = v6.mix_rgb(nt, inner, c, earc, (0, 600))
    # nose leather: pebbling (0.25 mm cells + 0.7 mm octave), crevice AO,
    # rose-brown margin
    tc = N(nt, "ShaderNodeTexCoord", (-900, 1100))
    vor = N(nt, "ShaderNodeTexVoronoi", (-600, 1150))
    vor.feature = "DISTANCE_TO_EDGE"
    vor.inputs["Scale"].default_value = 3300.0
    vor.inputs["Randomness"].default_value = 0.9
    L(nt, tc.outputs["Object"], vor.inputs["Vector"])
    vor2 = N(nt, "ShaderNodeTexVoronoi", (-600, 950))
    vor2.feature = "DISTANCE_TO_EDGE"
    vor2.inputs["Scale"].default_value = 1250.0
    vor2.inputs["Randomness"].default_value = 0.8
    L(nt, tc.outputs["Object"], vor2.inputs["Vector"])
    crev = mr(vor.outputs["Distance"], 0.0, 0.18, 0.0, 1.0, (-350, 1150))
    crev2 = mr(vor2.outputs["Distance"], 0.0, 0.14, 0.0, 1.0, (-350, 950))
    hgt = math_("ADD", math_("MULTIPLY", crev, 0.65, (-150, 1150)), math_("MULTIPLY", crev2, 0.35, (-150, 950)), (0, 1050))
    ao = mr(hgt, 0.0, 1.0, 0.70, 1.0, (150, 1050))
    lcol = v6.mix_rgb(nt, sd.outputs["Green"], (0.34, 0.15, 0.14), (0.16, 0.065, 0.058), (150, 850))
    leather = N(nt, "ShaderNodeMix", (400, 950))
    leather.data_type = "RGBA"
    leather.blend_type = "MULTIPLY"
    leather.inputs["Factor"].default_value = 1.0
    L(nt, lcol, leather.inputs[6])
    L(nt, ao, leather.inputs[7])
    c = v6.mix_rgb(nt, sr.outputs["Red"], c, leather.outputs[2], (600, 600))
    c = v6.mix_rgb(nt, sd.outputs["Blue"], c, (0.20, 0.13, 0.13), (800, 600))
    c = v6.mix_rgb(nt, sr.outputs["Green"], c, (0.013, 0.011, 0.011), (1000, 600))
    L(nt, c, bs.inputs["Base Color"])
    # roughness: skin 0.55; leather 0.48 top -> 0.34 lower tip (object z)
    # and round the nostrils (pigment inside the leather); pigment 0.45
    sep = N(nt, "ShaderNodeSeparateXYZ", (-600, 750))
    L(nt, tc.outputs["Object"], sep.inputs["Vector"])
    wet = mr(sep.outputs["Z"], -0.040, -0.030, 0.34, 0.48, (-350, 750))
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
    r3.inputs[3].default_value = 0.42
    L(nt, r3.outputs[0], bs.inputs["Roughness"])
    bump = N(nt, "ShaderNodeBump", (1200, -300))
    bump.inputs["Strength"].default_value = 1.0
    bump.inputs["Distance"].default_value = 0.00024
    L(nt, math_("MULTIPLY", hgt, sr.outputs["Red"], (1000, -300)), bump.inputs["Height"])
    L(nt, bump.outputs["Normal"], bs.inputs["Normal"])
    # subsurface: inner ear 0.45, ear back 0.22, leather 0.12; none in
    # pigment or under the body coat
    sss_ear = math_("MULTIPLY", math_("POWER", sr.outputs["Blue"], 2.0, (650, -600)), 0.20, (800, -600))
    sss_n = math_("MULTIPLY", sr.outputs["Red"], 0.12, (800, -750))
    sss = math_("ADD", sss_ear, sss_n, (1000, -650))
    inv = math_("SUBTRACT", 1.0, sr.outputs["Green"], (1000, -850))
    L(nt, math_("MULTIPLY", sss, inv, (1200, -700), clamp=True), bs.inputs["Subsurface Weight"])
    bs.inputs["Subsurface Radius"].default_value = (1.0, 0.45, 0.30)
    bs.inputs["Subsurface Scale"].default_value = 0.0010
    bs.inputs["Specular IOR Level"].default_value = 0.45
    L(nt, bs.outputs["BSDF"], out.inputs["Surface"])
    return m


def hair_material_v8(name, images, under=False, tip_alpha=True):
    """Round 6 hair (judged round 5: a cold blue-silver plush toy; no ticking
    at 1 m): warm brown-grey agouti banding on every ground hair (dark slate-
    brown root, a pale warm beige sub-tip band, a black tip) with per-strand
    band jitter, neutral black stripe hairs, warm white; the per-strand
    binary stripe/white choice is kept; hair tips fade to transparent over
    their last ~15 % so the silhouette breaks up."""
    m, nt = v6.new_mat(name)
    out = N(nt, "ShaderNodeOutputMaterial", (1800, 0))
    hb = N(nt, "ShaderNodeBsdfHairPrincipled", (1300, 0))
    hb.parametrization = "COLOR"
    hb.model = "CHIANG"
    coat = v6.image_node(nt, images["coat"], (-900, 300), uv_attr="surface_uv_coordinate")
    sc = N(nt, "ShaderNodeSeparateColor", (-600, 300))
    L(nt, coat.outputs["Color"], sc.inputs["Color"])
    info = N(nt, "ShaderNodeHairInfo", (-1000, -300))
    rnd = N(nt, "ShaderNodeMapRange", (-800, -450))
    L(nt, info.outputs["Random"], rnd.inputs["Value"])
    rnd.inputs["To Min"].default_value = -0.07
    rnd.inputs["To Max"].default_value = 0.07
    pos = N(nt, "ShaderNodeMath", (-600, -300))
    pos.operation = "ADD"
    L(nt, info.outputs["Intercept"], pos.inputs[0])
    L(nt, rnd.outputs["Result"], pos.inputs[1])

    def ramp(loc, stops, interp="EASE"):
        r = N(nt, "ShaderNodeValToRGB", loc)
        cr = r.color_ramp
        cr.interpolation = interp
        cr.elements[0].position = stops[0][0]
        cr.elements[0].color = (*stops[0][1], 1)
        cr.elements[1].position = stops[-1][0]
        cr.elements[1].color = (*stops[-1][1], 1)
        for p_, col in stops[1:-1]:
            e = cr.elements.new(p_)
            e.color = (*col, 1)
        L(nt, pos.outputs[0], r.inputs["Fac"])
        return r.outputs["Color"]

    if not under:
        agouti = ramp((-350, -100), [(0.0, (0.052, 0.045, 0.038)), (0.26, (0.074, 0.063, 0.052)), (0.36, (0.31, 0.245, 0.160)),
                                     (0.58, (0.35, 0.275, 0.180)), (0.67, (0.045, 0.039, 0.034)), (1.0, (0.026, 0.024, 0.023))])
        pale = ramp((-350, -350), [(0.0, (0.26, 0.23, 0.19)), (0.25, (0.50, 0.45, 0.37)), (0.75, (0.54, 0.49, 0.40)), (0.90, (0.36, 0.32, 0.26)),
                                   (1.0, (0.26, 0.23, 0.19))])
        stripe = ramp((-350, -600), [(0.0, (0.055, 0.052, 0.050)), (0.30, (0.034, 0.033, 0.032)), (1.0, (0.028, 0.027, 0.027))])
        white = (0.62, 0.60, 0.565)
    else:
        agouti = ramp((-350, -100), [(0.0, (0.085, 0.074, 0.060)), (1.0, (0.21, 0.17, 0.12))])
        pale = ramp((-350, -350), [(0.0, (0.30, 0.27, 0.23)), (1.0, (0.42, 0.38, 0.32))])
        stripe = ramp((-350, -600), [(0.0, (0.06, 0.057, 0.055)), (1.0, (0.042, 0.040, 0.039))])
        white = (0.47, 0.455, 0.43)
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
    c = v6.mix_rgb(nt, sc.outputs["Blue"], agouti, pale, (0, -150))
    c = v6.mix_rgb(nt, sb.outputs[0], c, stripe, (200, -150))
    c = v6.mix_rgb(nt, wbn.outputs[0], c, white, (400, -150))
    jit = N(nt, "ShaderNodeMapRange", (400, -450))
    L(nt, info.outputs["Random"], jit.inputs["Value"])
    jit.inputs["To Min"].default_value = 0.86
    jit.inputs["To Max"].default_value = 1.10
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
    hb.inputs["Roughness"].default_value = 0.38 if not under else 0.45
    hb.inputs["Radial Roughness"].default_value = 0.50
    hb.inputs["Coat"].default_value = 0.0
    hb.inputs["IOR"].default_value = 1.20
    hb.inputs["Offset"].default_value = math.radians(2.5)
    hb.inputs["Random Roughness"].default_value = 0.2
    if tip_alpha:
        tip = N(nt, "ShaderNodeMapRange", (1100, -400))
        L(nt, info.outputs["Intercept"], tip.inputs["Value"])
        tip.inputs["From Min"].default_value = 0.84
        tip.inputs["From Max"].default_value = 1.0
        tip.inputs["To Min"].default_value = 0.0
        tip.inputs["To Max"].default_value = 0.65
        tip.interpolation_type = "SMOOTHSTEP"
        trn = N(nt, "ShaderNodeBsdfTransparent", (1300, -300))
        mx = N(nt, "ShaderNodeMixShader", (1550, 0))
        L(nt, tip.outputs["Result"], mx.inputs["Fac"])
        L(nt, hb.outputs["BSDF"], mx.inputs[1])
        L(nt, trn.outputs["BSDF"], mx.inputs[2])
        L(nt, mx.outputs["Shader"], out.inputs["Surface"])
    else:
        L(nt, hb.outputs["BSDF"], out.inputs["Surface"])
    return m


# ---------------------------------------------------------------------------
# Groom (round 6)
# ---------------------------------------------------------------------------

def grow_guides_v8(pos, nrm, ex, npts, rng, length_scale=None, lift_add=None, lay=0.8):
    """v6.grow_guides plus a stronger, slower wave on the chest bib (a slight
    curl) and a flatter lay on the pinna back."""
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
    zw = pos[:, 2] / MM
    bibw = f["white"] * smoothstep(-95.0, -130.0, zw) * smoothstep(-0.1, 0.4, nrm[:, 0])
    wave_amp = rng.uniform(0.04, 0.12, n) + 0.22 * bibw
    freq = rng.uniform(0.6, 1.3, n) + 0.9 * bibw
    phase = rng.random(n) * 2 * math.pi
    bend = rng.normal(0.0, 0.07, n)
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
             + side * (bend * sm + wave_amp * np.sin(2 * math.pi * freq * sm + phase))[:, None]
             + gt * (droop * sm * sm)[:, None])
        d /= np.linalg.norm(d, axis=1, keepdims=True)
        p = p + d * seg[:, None]
        strands[:, k] = p
    return strands, f


def build_groom_v8(coll, skin, images, n_guides):
    """Round 6 groom (judged round 5: uniform airbrushed fuzz, weak clumps,
    smeared flow): three clump levels on the guard coat (3.6 mm at 0.82,
    1.4 mm at 0.55, 0.55 mm at 0.30) with tip spread, frizz and noise, the
    shorter per-region lengths of coat_fields_v8, hair-tip transparency and
    12,000 sampled stray guard hairs, of which those on the pinnae, near the
    lids or round the leather are dropped (7,817 kept)."""
    rng = np.random.default_rng(v6.RNG_SEED)
    S = v6.evaluated_surface(skin)
    log("groom surface tris", len(S["tv"]))

    def wfn(c, n, ex):
        f = v6.coat_fields(c, n, ex)
        return f["density"] * np.maximum(f["excl"], 0.05) / np.maximum(f["length"], 2.5 * MM)

    pos, nrm, uv, ex = v6.sample_roots(S, n_guides, wfn, rng)
    strands, f = grow_guides_v8(pos, nrm, ex, 8, rng)
    v6.load_hair_assets()
    v6.length_jitter_group()
    layers = []
    cull = v6.eye_cull_group()
    specs = [
        ("CatBaseV6_Fur_Guard", False, dict(density=5.0e6, trim=1.0, noise=0.12 * MM, nscale=180.0, frizz=0.06 * MM,
                                            clumps=((0.82, 3.6 * MM, 0.45, 0.25 * MM), (0.55, 1.4 * MM, 0.35, 0.10 * MM), (0.30, 0.55 * MM, 0.25, 0.0)),
                                            r0=0.064 * MM, seed=3)),
        ("CatBaseV6_Fur_Under", True, dict(density=6.0e6, trim=0.55, noise=0.35 * MM, nscale=520.0, frizz=0.16 * MM,
                                           clumps=((0.30, 2.0 * MM, 0.3, 0.0),), r0=0.030 * MM, seed=7)),
    ]
    for name, under, sp in specs:
        ob = v6.make_curves(name, strands, sp["r0"], sp["r0"] * 0.25, coll, uv=uv, surface=skin)
        ob.parent = skin
        ob.data.materials.append(hair_material_v8(f"M_{name}", images, under, tip_alpha=not under))
        v6.gn_mod(ob, "Interpolate Hair Curves", Follow_Surface_Normal=True, Part_by_Mesh_Islands=True, Density=sp["density"],
                  Density_Mask=("ATTR", "fur_density"), Mask_Texture=images["furmask"], Interpolation_Guides=4,
                  Viewport_Amount=0.05, Seed=sp["seed"])
        v6.gn_mod(ob, "CatBaseV6 Length Jitter", Min=0.7, Max=1.3, Seed=sp["seed"] + 20)
        if sp["trim"] < 1.0:
            v6.gn_mod(ob, "Trim Hair Curves", Scale_Uniform=False, Replace_Length=False, Length_Factor=sp["trim"], Random_Offset=0.0, Pin_at_Parameter=0.0, Seed=13)
        for ci, (cf, cd_, csh, spread) in enumerate(sp["clumps"]):
            v6.gn_mod(ob, "Clump Hair Curves", Factor=cf, Shape=csh, Tip_Spread=spread, Existing_Guide_Map=False,
                      Guide_Distance=cd_, Guide_Mask=1.0, Preserve_Length=True, Seed=11 + 17 * ci)
        v6.gn_mod(ob, "Hair Curves Noise", Factor=1.0, Distance=sp["noise"], Shape=0.5, Scale=sp["nscale"], Scale_along_Curve=1.0,
                  Offset_per_Curve=1.0, Seed=5 if under else 9, Preserve_Length=True)
        v6.gn_mod(ob, "Frizz Hair Curves", Factor=1.0, Distance=sp["frizz"], Shape=0.7, Seed=15 if under else 19, Preserve_Length=True)
        v6.gn_mod(ob, "Shrinkwrap Hair Curves", Surface=skin, Factor=1.0, Offset_Distance=0.12 * MM, Smoothing_Steps=2, Lock_Roots=True)
        v6.gn_mod(ob, "Set Hair Curve Profile", Replace_Radius=True, Radius=sp["r0"], Shape=-0.5, Factor_Min=0.0, Factor_Max=1.0)
        m_ = ob.modifiers.new("CatBaseV6 Eye Cull", "NODES")
        m_.node_group = cull
        layers.append(ob)
    n_stray = 12000
    sp_, sn_, suv, sex = v6.sample_roots(S, n_stray, wfn, rng)
    st, _ = grow_guides_v8(sp_, sn_, sex, 10, rng, length_scale=rng.uniform(1.12, 1.40, n_stray),
                           lift_add=rng.uniform(1.0, 6.0, n_stray), lay=0.78)
    # no strays on the pinna, the leather surround or the lids
    fs = v6.coat_fields(sp_, sn_, sex)
    keep = (sex["is_ear"] < 0.5) & (fs["d_fis"] > 4.0) & (fs["excl"] > 0.95)
    st, suv = st[keep], suv[keep]
    t = np.linspace(0, 1, st.shape[1])
    radii = np.repeat(((0.072 * MM) * (1 - t) ** 1.3 + 0.008 * MM)[None], len(st), 0)
    ob = v6.make_curves("CatBaseV6_Fur_Stray", st, 0, 0, coll, uv=suv, surface=skin, radii=radii)
    ob.parent = skin
    ob.data.materials.append(hair_material_v8("M_CatBaseV6_Fur_Stray", images, False))
    m_ = ob.modifiers.new("CatBaseV6 Eye Cull", "NODES")
    m_.node_group = cull
    layers.append(ob)
    guides = v6.make_curves("CatBaseV6_Fur_Guides", strands, 0.1 * MM, 0.05 * MM, coll, uv=uv, surface=skin)
    guides.parent = skin
    guides.hide_render = True
    guides.hide_viewport = True
    return layers, guides


def skin_hit_x(y, z, x_hi=180.0, x_lo=90.0):
    """Head-frame x (mm) of the skin surface along +x at head (y, z) mm."""
    Rh = v6.head_R()
    lo, hi = x_lo, x_hi
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        p = np.array([[mid, y, z]]) * MM @ Rh.T
        if v7.exact_skin_sdf(p)[0] < 0.0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def build_vibrissae_v8(coll, skin):
    """Round 6 vibrissae (judged round 5: uniform straight lines, a 106 mm
    straight whisker ran down past the cheek, brow whiskers crossed the ear
    openings). Mystacial: 12 per side, rooted exactly in the follicle rows
    (found on the skin along +x), ~40-95 mm, each with a thick base tapering
    to a fine tip (radius ~ (1 - t)^1.6) and a real forward-down arc of
    18-34 deg plus a slight counter-curve at the root. Superciliary: 5 per
    side, 26-36 mm, rising up, forward and out on a short arc that ends below
    and in front of the ears. Genal: 2 per side, 30-38 mm, lying back along
    the cheek."""
    rng = np.random.default_rng(v6.RNG_SEED + 1)
    S = v6.evaluated_surface(skin)
    kd = KDTree(len(S["co"]))
    for i, p in enumerate(S["co"]):
        kd.insert(p, i)
    kd.balance()
    Rh = v6.head_R()
    strands, radii = [], []
    npts = 28
    down_w = np.array([0.0, 0.0, -1.0])

    def add(root_w, nr, d0_w, length, bend_deg, droop_deg, r0, bend_dir, counter=0.0):
        d0 = np.asarray(d0_w, float)
        d0 /= np.linalg.norm(d0)
        bd = np.asarray(bend_dir, float)
        bd = bd - (bd @ d0) * d0
        if np.linalg.norm(bd) < 1e-6:
            bd = down_w - (down_w @ d0) * d0
        bd /= np.linalg.norm(bd)
        pts = [root_w - nr * 1.0 * MM]
        p = root_w.copy()
        seg = length / (npts - 1)
        for k in range(1, npts):
            s_ = k / (npts - 1)
            a = math.radians(bend_deg) * s_ ** 1.3 - math.radians(counter) * math.sin(math.pi * min(s_ / 0.3, 1.0)) * (s_ < 0.3)
            dd = d0 * math.cos(a) + bd * math.sin(a)
            dd = dd + down_w * math.tan(math.radians(droop_deg)) * s_ * s_
            dd /= np.linalg.norm(dd)
            p = p + dd * seg
            pts.append(p.copy())
        strands.append(pts)
        t = np.linspace(0, 1, npts)
        radii.append(r0 * (1.0 - t) ** 1.6 + 0.010 * MM)

    for s_, row, col, p in mystacial_roots_v8():
        xh = skin_hit_x(p[1], p[2])
        root_h = np.array([xh, p[1], p[2]])
        _, idx, _ = kd.find(root_h * MM @ Rh.T)
        nr = S["nr"][idx]
        root = root_h * MM @ Rh.T
        row_len = ((50.0, 70.0), (58.0, 86.0), (60.0, 92.0), (40.0, 56.0))[row]
        L_ = (row_len[0] + (row_len[1] - row_len[0]) * col / 2.0) * rng.uniform(0.94, 1.06) * MM
        az = math.radians(42.0 + 9.0 * col + 4.0 * row + rng.normal(0.0, 2.0))
        el = math.radians(5.0 - 5.5 * row - 1.5 * col + rng.normal(0.0, 1.5))
        d0 = np.array([math.cos(el) * math.cos(az), s_ * math.cos(el) * math.sin(az), math.sin(el)])
        r0 = (0.17 + 0.03 * col) * MM * rng.uniform(0.95, 1.05)
        add(root, nr, d0, L_, rng.uniform(18.0, 34.0), rng.uniform(1.0, 4.0), r0, np.array([0.7, 0.0, -0.7]), counter=rng.uniform(2.0, 5.0))
    for s_ in (1.0, -1.0):
        for k in range(5):
            root_h = np.array([88.0 - 2.4 * k, (24.0 + 4.2 * k) * s_, 44.0 + 1.2 * k])
            root, nr = v6.surface_point(S, kd, root_h * MM @ Rh.T)
            d0 = np.array([0.78, (0.42 + 0.06 * k) * s_, 0.45 + rng.normal(0, 0.04)])
            add(root, nr, d0, rng.uniform(26.0, 36.0) * MM, rng.uniform(14.0, 24.0), 0.0, (0.10 - 0.01 * k) * MM,
                np.array([0.0, 0.7 * s_, 0.3]))
        for k in range(2):
            root_h = np.array([44.0 - 7.0 * k, 84.0 * s_, -6.0 - 5.0 * k])
            root, nr = v6.surface_point(S, kd, root_h * MM @ Rh.T)
            d0 = np.array([-0.55, 0.80 * s_, -0.05])
            add(root, nr, d0, rng.uniform(30.0, 38.0) * MM, 12.0, 3.0, 0.11 * MM, np.array([-0.6, 0.0, -0.4]))
    P = np.array(strands)
    hc = bpy.data.hair_curves.new("CatBaseV6_Vibrissae")
    hc.add_curves([npts] * len(P))
    hc.attributes["position"].data.foreach_set("vector", P.astype(np.float32).ravel())
    if "radius" not in hc.attributes:
        hc.attributes.new("radius", "FLOAT", "POINT")
    hc.attributes["radius"].data.foreach_set("value", np.array(radii).astype(np.float32).ravel())
    da = hc.attributes.new("vib_dark", "FLOAT", "CURVE")
    da.data.foreach_set("value", np.zeros(len(P), np.float32))
    ob = v6.link(bpy.data.objects.new("CatBaseV6_Vibrissae", hc), coll)
    ob.parent = skin
    ob.data.materials.append(v6.whisker_material())
    return ob


def build_inner_ear_furnishings_v8(coll, skin, images):
    """Round 6 furnishings (judged round 5: uniform white plush brighter than
    the face): 260 wispy tufts of 4-8 fine hairs (root radius 0.026 mm),
    12-30 mm, each with its own random direction, rooted on the inner-front (medial) edge of the pinna's lower
    half and at the conchal entrance (tragus, antitragus), each tuft tight at
    the root and fanning toward the tips, curling up and out of the opening."""
    rng = np.random.default_rng(v6.RNG_SEED + 2)
    S = v6.evaluated_surface(skin)

    def wfn(c, n, ex):
        front = ex["is_ear"] * smoothstep(0.2, 0.6, ex["ear_face"])
        vis = smoothstep(0.0, 0.05, ex["ear_t"])
        med = (1.0 - smoothstep(-0.85, -0.55, ex["ear_u"])) * _bump(ex["ear_t"], 0.03, 0.40)
        base = _bump(ex["ear_t"], 0.0, 0.16) * (1.0 - smoothstep(0.60, 0.85, np.abs(ex["ear_u"])))
        anti = smoothstep(0.50, 0.65, ex["ear_u"]) * (1.0 - smoothstep(0.88, 0.97, ex["ear_u"])) * _bump(ex["ear_t"], 0.0, 0.20)
        return front * vis * (1.6 * med + 1.0 * base + 0.6 * anti)

    n_tuft = 260
    cpos, cnrm, cuv, cex = v6.sample_roots(S, n_tuft, wfn, rng)
    npts = 14
    strands, uvs = [], []
    for i in range(n_tuft):
        s = 1.0 if (cpos[i] @ v6.head_R())[1] > 0 else -1.0
        F = v6.ear_frame(s)
        up = F[:, 2] @ v6.head_R().T
        fwd = F[:, 0] @ v6.head_R().T
        lat = F[:, 1] * s @ v6.head_R().T
        eu, et = cex["ear_u"][i], cex["ear_t"][i]
        if eu < -0.5:
            d = 0.45 * up + 0.60 * fwd + 0.70 * lat + 0.20 * cnrm[i]
            Lt = rng.uniform(16.0, 30.0) * MM
        elif eu > 0.5:
            d = 0.55 * up + 0.65 * fwd - 0.45 * lat + 0.20 * cnrm[i]
            Lt = rng.uniform(12.0, 22.0) * MM
        else:
            d = 0.55 * up + 0.80 * fwd + 0.15 * lat * rng.normal() + 0.2 * cnrm[i]
            Lt = rng.uniform(16.0, 28.0) * MM
        d /= np.linalg.norm(d)
        k = int(rng.integers(4, 9))
        d = d + rng.normal(0.0, 0.28, 3)
        d /= np.linalg.norm(d)
        curl = rng.normal(0, 0.20, 3)
        for _ in range(k):
            off = rng.normal(0.0, 0.30 * MM, 3)
            off -= (off @ cnrm[i]) * cnrm[i]
            p = cpos[i] + off - cnrm[i] * 0.2 * MM
            fan = rng.normal(0.0, 0.24, 3)
            Lh = Lt * rng.uniform(0.65, 1.1)
            c2 = curl + rng.normal(0, 0.05, 3)
            pts = [p.copy()]
            for kk in range(1, npts):
                s_ = kk / (npts - 1)
                dd = d + fan * s_ ** 1.5 + c2 * s_ + np.array([0, 0, -0.20]) * s_ * s_
                dd /= np.linalg.norm(dd)
                p = p + dd * Lh / (npts - 1)
                pts.append(p.copy())
            strands.append(pts)
            uvs.append(cuv[i])
    strands = np.array(strands)
    uv = np.array(uvs)
    t = np.linspace(0, 1, npts)
    radii = np.repeat(((0.026 * MM) * (1 - t) ** 1.2 + 0.004 * MM)[None], len(strands), 0)
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
    rj.inputs["To Min"].default_value = 0.52
    rj.inputs["To Max"].default_value = 0.74
    cc = N(nt, "ShaderNodeCombineColor", (0, 0))
    L(nt, rj.outputs["Result"], cc.inputs["Red"])
    g_ = N(nt, "ShaderNodeMath", (0, 150))
    g_.operation = "MULTIPLY"
    L(nt, rj.outputs["Result"], g_.inputs[0])
    g_.inputs[1].default_value = 0.97
    L(nt, g_.outputs[0], cc.inputs["Green"])
    cc2 = N(nt, "ShaderNodeMath", (0, -150))
    cc2.operation = "MULTIPLY"
    L(nt, rj.outputs["Result"], cc2.inputs[0])
    cc2.inputs[1].default_value = 0.92
    L(nt, cc2.outputs[0], cc.inputs["Blue"])
    L(nt, cc.outputs["Color"], hb.inputs["Color"])
    hb.inputs["Roughness"].default_value = 0.34
    hb.inputs["Radial Roughness"].default_value = 0.4
    hb.inputs["Coat"].default_value = 0.0
    hb.inputs["IOR"].default_value = 1.3
    tip = N(nt, "ShaderNodeMapRange", (300, -300))
    L(nt, info.outputs["Intercept"], tip.inputs["Value"])
    tip.inputs["From Min"].default_value = 0.75
    tip.inputs["From Max"].default_value = 1.0
    tip.inputs["To Min"].default_value = 0.0
    tip.inputs["To Max"].default_value = 0.7
    trn = N(nt, "ShaderNodeBsdfTransparent", (500, -200))
    mx = N(nt, "ShaderNodeMixShader", (700, 0))
    L(nt, tip.outputs["Result"], mx.inputs["Fac"])
    L(nt, hb.outputs["BSDF"], mx.inputs[1])
    L(nt, trn.outputs["BSDF"], mx.inputs[2])
    L(nt, mx.outputs["Shader"], out.inputs["Surface"])
    ob.data.materials.append(m)
    return ob


# ---------------------------------------------------------------------------
# Overrides, previews, compare, manifest, main
# ---------------------------------------------------------------------------

def apply_round6_overrides():
    if getattr(v6, "_ROUND6", False):
        return
    v7.apply_round5_overrides()
    v6._ROUND6 = True
    # eyes: the globe 2 mm forward (the lid centre is kept), a steeper cornea,
    # lids draped over the cornea, a tear-duct notch
    A.eye_sink = 0.0
    v6.cornea_dims = cornea_dims_v8
    v6.fissure_curves = fissure_curves_v8
    v6.sd_lid_shell = sd_lid_shell_v8
    v6.iris_arrays = iris_arrays_v8
    # ears: 0.85x length, 1.1x base, 10 deg further out, thinner sheet
    A.ear_h = 66.0 * MM
    A.ear_chord = 95.0 * MM
    A.ear_tip_r = 5.0 * MM
    A.ear_t0 = 2.2 * MM
    A.ear_t1 = 1.2 * MM
    A.ear_lean_out = 34.0
    v6.ear_arrays = ear_arrays_v8
    # nose leather 0.8x about its centre, comma nostrils, philtrum split
    lh = np.asarray(v6.LEATHER_HALF, float)
    zc = 0.5 * (lh[:, 1].max() + lh[:, 1].min())
    c = (0.0, zc)
    v6.LEATHER_HALF = scale_about(v6.LEATHER_HALF, c, LEATHER_SCALE)
    npoly = scale_about(v6.NOSTRIL_POLY, c, LEATHER_SCALE)
    a_, b_ = np.asarray(npoly[-2]), np.asarray(npoly[-1])
    npoly[-1] = tuple(a_ + 0.45 * (b_ - a_))  # the tail stopped short of the leather edge (a hook of groove showed outside it)
    v6.NOSTRIL_POLY = npoly
    v6.ALAR_POLY = scale_about(v6.ALAR_POLY, c, LEATHER_SCALE)
    v6.NOSTRIL_W = [1.20, 0.95, 0.60, 0.38, 0.22]
    v6.NOSTRIL_D = [4.0, 3.6, 2.6, 1.6, 0.6]
    zb = zc + (lh[:, 1].min() - zc) * LEATHER_SCALE
    v6.PHILTRUM = [(0.0, zb + 2.6), (0.0, zb - 1.0), (0.0, -30.0)]
    v6.build_detail_ops = build_detail_ops_v8
    v6.DETAIL_OPS = None
    # coat, flow, markings, follicles
    v6.MARKINGS = MARKINGS_V8
    v6._MARK_CACHE.clear()
    v6.coat_fields = coat_fields_v8
    v6.fur_direction = fur_direction_v8
    v6.mystacial_roots = mystacial_roots_v8
    v6.grow_guides = grow_guides_v8
    # skin level set: bust, insets, conchal funnel
    v7.fur_inset_mm = fur_inset_mm_v8
    v7.build_bust_ops = build_bust_ops_v8
    v7.scan_head_neck = scan_head_neck_v8
    v7.cup_weight = cup_weight_v8


def install_build_overrides_v8():
    if getattr(v6, "_ROUND6_BUILD", False):
        return
    v7.install_build_overrides()
    v6._ROUND6_BUILD = True
    build_eyes_v7 = v6.build_eyes

    def build_eyes_v8(coll, mats, parent):
        objs = build_eyes_v7(coll, mats, parent)
        tex = bake_iris_texture()
        imat = iris_material_v8(tex)
        cmat = cornea_material_v8()
        keep = []
        for o in objs:
            if o.name.endswith("_TearMeniscus"):
                bpy.data.objects.remove(o, do_unlink=True)
                continue
            if o.name.endswith("_Iris"):
                side = 1.0 if "EyeL" in o.name else -1.0
                me = o.data
                co = np.empty(len(me.vertices) * 3, np.float32)
                me.vertices.foreach_get("co", co)
                co = co.reshape(-1, 3)
                ri = v6.cornea_dims()["r_i"]
                R_ = np.hypot(co[:, 1], co[:, 2]) / ri
                T_ = np.arctan2(co[:, 2], co[:, 1]) + IRIS_ROT[side]
                uvv = np.stack([0.5 + 0.5 * R_ * np.cos(T_), 0.5 + 0.5 * R_ * np.sin(T_)], -1)
                ul = me.uv_layers.new(name="IrisTex")
                loop_v = np.empty(len(me.loops), np.int32)
                me.loops.foreach_get("vertex_index", loop_v)
                ul.data.foreach_set("uv", uvv[loop_v].astype(np.float32).ravel())
                me.materials.clear()
                me.materials.append(imat)
            if o.name.endswith("_Cornea"):
                o.data.materials.clear()
                o.data.materials.append(cmat)
            keep.append(o)
        return keep

    v6.build_eyes = build_eyes_v8
    v6.build_lid_margins = build_lid_margins_v8
    v6.bake_textures = bake_textures_v8
    v6.skin_material = skin_material_v8
    v6.build_groom = build_groom_v8
    v6.build_vibrissae = build_vibrissae_v8
    v6.build_inner_ear_furnishings = build_inner_ear_furnishings_v8


def preview_skin(args):
    """Workbench review renders of the bare skin level set, pinnae, globes and
    corneas (no fur): the ear base, the eye in profile, the mouth and bust."""
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
    mouth = Vector(np.array([140.0, 0.0, -34.0]) * MM @ v6.head_R().T)
    views = (("front", Vector((0.06, 0, 0.0)), Vector((1, 0, 0.03)), 0.9), ("profile", Vector((0.03, 0, -0.03)), Vector((0.0, -1, 0.02)), 1.1),
             ("tq", Vector((0.05, 0, 0.0)), Vector((0.72, -0.69, 0.06)), 0.9), ("bust_front", Vector((0.0, 0, -0.16)), Vector((1, 0, 0.02)), 2.2),
             ("bust_profile", Vector((0.0, 0, -0.16)), Vector((0, -1, 0.02)), 2.2),
             ("ear_front", ear * Vector((1, -1, 1)) + Vector((0, 0, 0.02)), Vector((1, -0.25, 0.25)), 0.45),
             ("ear_tq", ear * Vector((1, -1, 1)) + Vector((0, 0, 0.02)), Vector((0.6, -0.8, 0.2)), 0.45),
             ("eye_profile", eye, Vector((0.02, -1, 0.0)), 0.35), ("eye_tq", eye, Vector((0.72, -0.69, 0.05)), 0.30),
             ("mouth", mouth, Vector((1, 0, -0.1)), 0.35))
    for name, t, d_, dist in views:
        cam.location = t + d_.normalized() * dist
        cam.rotation_euler = (t - cam.location).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = str(Path(args.preview_dir) / f"skin_{name}.png")
        bpy.ops.render.render(write_still=True)


REF_PHOTO = v7.REF_PHOTO
HERO_REF = v7.HERO_REF


def stage_compare_v8(args):
    """Side-by-sides: the private A/B of the reference-matched frame with the
    CC BY 2.0 photograph (never committed); committed previous-round | this-
    round pairs at the reference framing and the five Overcast cameras; the
    Nyaakoto reference face beside this round's CloseFront, and beside this
    round's Overcast Profile."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    rn = args.round
    cur = OUT / "Renders" / f"round_{rn}"
    prv = OUT / "Renders" / f"round_{rn - 1}"
    tag, ptag = f"R{rn}", f"R{rn - 1}"
    ref_c = cur / f"CatBaseV6_{tag}_RefMatch_RefMatch_Profile.png"
    if REF_PHOTO.exists() and ref_c.exists():
        ab = CACHE / f"ab_round{rn}"
        ab.mkdir(parents=True, exist_ok=True)
        v7._img_save(v7._side_by_side([v7._img_load(ref_c), v7._img_load(REF_PHOTO)], 1080), ab / "refmatch_profile_AB.png")
        log("private A/B", ab / "refmatch_profile_AB.png")
    ref_p = prv / f"CatBaseV6_{ptag}_RefMatch_RefMatch_Profile.png"
    if ref_p.exists() and ref_c.exists():
        v7._img_save(v7._side_by_side([v7._img_load(ref_p), v7._img_load(ref_c)], 810), cur / f"CatBaseV6_{tag}_AB_{ptag}_RefMatch_Profile.png")
    rows = []
    for view in ("Front", "Profile", "ThreeQuarter", "CloseFront", "CloseThreeQuarter"):
        a, b = prv / f"CatBaseV6_{ptag}_Overcast_{view}.png", cur / f"CatBaseV6_{tag}_Overcast_{view}.png"
        if a.exists() and b.exists():
            rows.append(v7._side_by_side([v7._img_load(a), v7._img_load(b)], 540))
    if rows:
        W = max(r.shape[1] for r in rows)
        sheet = np.full((sum(r.shape[0] for r in rows) + 8 * (len(rows) - 1), W, 3), 0.02, np.float32)
        yy = 0
        for r in rows:
            sheet[yy:yy + r.shape[0], :r.shape[1]] = r
            yy += r.shape[0] + 8
        v7._img_save(sheet, cur / f"CatBaseV6_{tag}_AB_{ptag}_Overcast.png")
    cf = cur / f"CatBaseV6_{tag}_Overcast_CloseFront.png"
    if HERO_REF.exists() and cf.exists():
        x0, y0, x1, y1 = v7.HERO_FACE_CROP
        hero = v7._img_load(HERO_REF)[y0:y1, x0:x1]
        mine = v7._img_load(cf)[:, 240:1680]
        v7._img_save(v7._side_by_side([hero, mine], 1080), cur / f"CatBaseV6_{tag}_AB_NyaakotoReference_CloseFront.png")
    pf = cur / f"CatBaseV6_{tag}_Overcast_Profile.png"
    if HERO_REF.exists() and pf.exists():
        hero = v7._img_load(HERO_REF)[40:280, 420:660]
        mine = v7._img_load(pf)[150:930, 520:1300]
        v7._img_save(v7._side_by_side([hero, mine], 1080), cur / f"CatBaseV6_{tag}_AB_NyaakotoReference_Profile.png")
    log("comparison sheets written to", cur)


def stage_manifest_v8(args):
    v7.stage_manifest_v7(args)
    man = json.loads((OUT / "manifest.json").read_text())
    man["generator"] = ("scripts/art/create_cat_base_v8.py (round 6; imports create_cat_base_v7.py, which imports "
                        "create_cat_base_v6.py)")
    man["round6"] = {
        "cornea": {"radius_over_limbus": 1.045, "ior": 1.376, "reflect_boost_x_fresnel": CORNEA_REFLECT_BOOST,
                   "globe_forward_mm": 2.0, "apex_from_globe_centre_mm": round(v6.cornea_dims()["apex"] / MM, 2)},
        "pupil": {"half_width_iris_radii": PUPIL_W0_V8, "half_height_iris_radii": PUPIL_H_V8, "feather": PUPIL_FEATHER},
        "ear": {"height_mm": A.ear_h / MM, "base_mm": A.ear_chord / MM, "lean_out_deg": A.ear_lean_out,
                "thickness_mm": [A.ear_t0 / MM, A.ear_t1 / MM], "margin_thickness_factor": 0.45},
        "nose_leather_scale": LEATHER_SCALE, "bust_shift_mm": {"x": BUST_DX, "z": BUST_DZ},
        "iris_texture": "Textures/T_CatBaseV6_Iris.png (procedural, painted from fields; no photograph pixels)",
        "detail_texture": "Textures/T_CatBaseV6_Detail.png (R inner-ear vessels, G leather margin, B whisker follicles)",
    }
    (OUT / "manifest.json").write_text(json.dumps(man, indent=2, ensure_ascii=False) + "\n")
    log("manifest (round 6 fields added)")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", type=int, default=6)
    ap.add_argument("--stages", default="skin,skinpreview")
    ap.add_argument("--voxel", type=float, default=0.75)
    ap.add_argument("--samples", type=int, default=256)
    ap.add_argument("--preview-dir", default=str(CACHE / "preview_r6"))
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
    apply_round6_overrides()
    stages = args.stages.split(",")
    if "scan" in stages:
        v7.stage_scan(args)
    if "skin" in stages:
        v7.stage_skin_v7(args)
    if "skinpreview" in stages:
        preview_skin(args)
    if "build" in stages:
        install_build_overrides_v8()
        v6.stage_build(args)
    if "render" in stages:
        v6.stage_render(args)
    if "measure" in stages:
        v7.stage_measure_v7(args)
    if "compare" in stages:
        stage_compare_v8(args)
    if "manifest" in stages:
        stage_manifest_v8(args)


if __name__ == "__main__":
    main()
