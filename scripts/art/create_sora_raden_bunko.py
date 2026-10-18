"""SORA raden bunko: an Edo-style maki-e document box on a neko-ashi stand.

Run (Blender 5.2.2):
  blender -b --factory-startup --python scripts/art/create_sora_raden_bunko.py -- [--no-render] [--res 4096]

The box follows Edo daimyo-trousseau lacquer practice (black roiro urushi,
hiramaki-e gold, kakiwari veins left as black lines, red shu interior,
fire-gilt copper corner fittings, silk cords and tassels). Its front carries
the SORA mark as a domed raden (mother-of-pearl) medallion in a gold rim; the
lid scatters three gold SORA mons among maple leaves floating on flowing
water (the Tatsuta-gawa motif). The stand's cat-paw (neko-ashi) legs are a
real Japanese furniture form. Mark geometry comes only from the pinned SVG.

Outputs go to Content/SourceArt/Environment/SoraCraft/SoraRadenBunko/.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import craft_textures as CT  # noqa: E402
import create_runtime_weapon_lib as L  # noqa: E402
import sora_mark  # noqa: E402
import sora_prop_lib as P  # noqa: E402

SPEC = dict(key="SoraRadenBunko", folder="SoraRadenBunko", asset="SM_SoraRadenBunko",
            ja="螺鈿文庫（そら紋）", en="SORA raden document box", texture_res=4096,
            faction="Nyaagyu house (SORA League)", builder="scripts/art/create_sora_raden_bunko.py")

# Dimensions in metres (Edo ryōshi-bako/bunko are typically 40-50 cm long).
STAND_TOP = (0.560, 0.410, 0.022)      # board size; top surface at STAND_H
STAND_H = 0.160
BODY = (0.460, 0.340, 0.150)
BODY_WALL = 0.009
LID = (0.470, 0.350, 0.055)
LID_WALL = 0.004
LID_TOP = 0.005
CROWN = 0.003
CORNER_R = 0.007
BODY_Z0 = STAND_H + 0.004               # sits on a 4 mm raised kōdai rim
LID_Z1 = BODY_Z0 + BODY[2] + LID_TOP    # lid top (before crown)
MEDALLION_D = 0.074
MEDALLION_Z = BODY_Z0 + 0.052


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------

def reset_uv_layers(mesh):
    """UV0 first (FBX channel 0), then UVMetric; drops importer/boolean layers."""
    for name in [layer.name for layer in mesh.uv_layers]:
        mesh.uv_layers.remove(mesh.uv_layers[name])
    mesh.uv_layers.new(name="UV0")
    mesh.uv_layers.new(name="UVMetric")
    L.box_uv(mesh, "UVMetric")


def _cluster(t, k=2.2):
    """Map [-1, 1] -> [-1, 1] clustering samples toward both ends (for edge rounding)."""
    return np.sign(t) * (1 - (1 - np.abs(t)) ** k) if k != 1 else t


def rounded_box(name, center, size, radius, mat=None, n=(40, 30, 16), crown=0.0, open_bottom=False):
    """Watertight rounded box from a clustered cube grid mapped through a clamp.

    q = clamp(p, -inner, inner) + radius * normalize(p - clamp(p)), which gives
    exact quarter-round edges and spherical corners. ``crown`` lifts the top
    (z > 0 faces) by crown * (1 - x'^2)(1 - y'^2). Quads only; UVMetric is boxed.
    """
    hx, hy, hz = size[0] / 2, size[1] / 2, size[2] / 2
    inner = np.array([hx - radius, hy - radius, hz - radius])
    half = np.array([hx, hy, hz])
    verts = []
    faces = []
    index = {}

    def vid(p):
        key = tuple(np.round(p, 9))
        if key not in index:
            index[key] = len(verts)
            verts.append(p)
        return index[key]

    # Six faces of a unit cube, each an (n_u x n_v) grid.
    axes = [(0, 1, 2, 1), (0, 1, 2, -1), (1, 2, 0, 1), (1, 2, 0, -1), (0, 2, 1, 1), (0, 2, 1, -1)]
    for a, b, c, sgn in axes:
        nu = n[a]
        nv = n[b]
        us = _cluster(np.linspace(-1, 1, nu + 1))
        vs = _cluster(np.linspace(-1, 1, nv + 1))
        grid = np.empty((nu + 1, nv + 1), dtype=np.int64)
        for i, u in enumerate(us):
            for j, v in enumerate(vs):
                p = np.zeros(3)
                p[a], p[b], p[c] = u * half[a], v * half[b], sgn * half[c]
                cl = np.clip(p, -inner, inner)
                d = p - cl
                ln = np.linalg.norm(d)
                q = cl + (radius * d / ln if ln > 1e-12 else 0)
                grid[i, j] = vid(q)
        for i in range(nu):
            for j in range(nv):
                quad = [grid[i, j], grid[i + 1, j], grid[i + 1, j + 1], grid[i, j + 1]]
                faces.append(quad if sgn > 0 else quad[::-1])
    V = np.array(verts)
    if crown:
        top = V[:, 2] > hz - radius * 1.5
        xn, yn = V[:, 0] / hx, V[:, 1] / hy
        lift = crown * np.clip(1 - xn ** 2, 0, 1) * np.clip(1 - yn ** 2, 0, 1)
        w = np.clip((V[:, 2] - (hz - radius * 1.5)) / (radius * 1.5), 0, 1)
        V[:, 2] += lift * np.where(top, w, 0.0)
    if open_bottom:
        cz = -hz + 1e-9
        keep = [f for f in faces if not all(V[k][2] <= cz for k in f)]
        faces = keep
    V = V + np.array(center)
    obj = L.make_obj(name, [tuple(v) for v in V], faces, mat, smooth=True, sharp_angle=None)
    # Faces of a grid cube can include the axis order mix-up; recalc normals outward.
    return obj


def hollow(obj, cutter_center, cutter_size, radius, inner_mat=None):
    cutter = rounded_box(obj.name + "_Cut", cutter_center, cutter_size, radius, inner_mat, n=(24, 18, 10))
    if inner_mat is not None and inner_mat.name not in [m.name for m in obj.data.materials]:
        obj.data.materials.append(inner_mat)
    mod = obj.modifiers.new("RW_Bool", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter
    mod.solver = "EXACT"
    mod.use_self = False
    L.apply_modifiers(obj)
    bpy.data.objects.remove(cutter, do_unlink=True)
    reset_uv_layers(obj.data)
    obj["rw_needs_unwrap"] = True
    L.finish_shading(obj, True, 40.0)
    return obj


def intersect_sphere(obj, center, radius):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=40, ring_count=20, radius=radius, location=center)
    sph = bpy.context.object
    mod = obj.modifiers.new("RW_Int", "BOOLEAN")
    mod.operation = "INTERSECT"
    mod.object = sph
    mod.solver = "EXACT"
    L.apply_modifiers(obj)
    bpy.data.objects.remove(sph, do_unlink=True)
    reset_uv_layers(obj.data)
    obj["rw_needs_unwrap"] = True
    L.finish_shading(obj, True, 40.0)
    return obj


def corner_cap(name, lid_center, lid_size, corner, mat, crown, radius_cap=0.036, thick=0.0011):
    """Gilt sheet cap conforming to a crowned rounded-box corner (sphere-cut outline)."""
    outer = rounded_box(name, lid_center, [s + 2 * thick for s in lid_size], CORNER_R + thick, mat,
                        n=(28, 22, 10), crown=crown)
    inner = rounded_box(name + "_In", lid_center, [s + 0.0002 for s in lid_size], CORNER_R + 0.0001, None,
                        n=(28, 22, 10), crown=crown)
    mod = outer.modifiers.new("RW_Bool", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = inner
    mod.solver = "EXACT"
    L.apply_modifiers(outer)
    bpy.data.objects.remove(inner, do_unlink=True)
    reset_uv_layers(outer.data)
    return intersect_sphere(outer, corner, radius_cap)


def lathe(name, profile, mat=None, sides=64, axis_matrix=None):
    """Revolve a (radius, height) polyline around local +Z; returns a mesh object."""
    rings = []
    for r, h in profile:
        rings.append([(max(r, 1e-6) * math.cos(math.tau * k / sides), max(r, 1e-6) * math.sin(math.tau * k / sides), h)
                      for k in range(sides)])
    obj = L.loft(name, rings, mat, cap_start=profile[0][0] > 1e-5, cap_end=profile[-1][0] > 1e-5)
    if axis_matrix is not None:
        L.transform(obj, axis_matrix)
    # A revolved disc's travel UVs are one long thin strip; let the planar
    # smart projection give it a round island with even texel density.
    obj["rw_needs_unwrap"] = True
    return obj


def ellipsoid(name, center, radii, mat, segments=32, rings=16):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, radius=1.0, location=(0, 0, 0))
    obj = bpy.context.object
    obj.name = name
    obj.data.name = name
    L.transform(obj, Matrix.Translation(center) @ Matrix.Diagonal((*radii, 1.0)))
    reset_uv_layers(obj.data)
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    L.link_to(obj, L.collection(L.SOURCE_COLL))
    obj["rw_needs_unwrap"] = True
    L.finish_shading(obj, True, None)
    return obj


def kozama_outline(width, height, samples=10):
    """Cusped-arch (格狭間) opening outline in local (x, z), z = 0 at its base."""
    w, h = width / 2, height
    ctrl = [(-w, 0.0), (-w * 1.02, h * 0.25), (-w * 0.92, h * 0.52), (-w * 0.97, h * 0.62),
            (-w * 0.80, h * 0.70), (-w * 0.45, h * 0.78), (-w * 0.12, h * 0.90), (0.0, h),
            (w * 0.12, h * 0.90), (w * 0.45, h * 0.78), (w * 0.80, h * 0.70), (w * 0.97, h * 0.62),
            (w * 0.92, h * 0.52), (w * 1.02, h * 0.25), (w, 0.0), (0.0, -h * 0.02)]
    return L.catmull_closed(ctrl, samples)


def neko_ashi(name, top, outward, height, mat, toe_mat):
    """Cat-paw cabriole leg: S-curved rounded-square shaft and a four-toed paw."""
    ox, oy = outward
    parts = []
    spine = []
    for k in range(25):
        t = k / 24
        # Knee bulges outward at 30 %, ankle returns inward at 80 %, foot steps out.
        bulge = 0.020 * math.sin(math.pi * min(t / 0.62, 1.0)) - 0.006 * max(0.0, (t - 0.62) / 0.38) ** 1.5
        spine.append(Vector((top.x + ox * bulge, top.y + oy * bulge, top.z - height * t + 0.018 * t)))
    def scale(u):
        s = 1.0 - 0.32 * math.sin(math.pi * min(u / 0.85, 1.0)) ** 0.8 if u < 0.85 else 0.70 + 0.5 * (u - 0.85)
        return (s, s)
    prof = L.polygon2d(4, 0.0135, corner=0.007, seg=4)
    shaft = L.sweep(name + "_Shaft", spine, prof, mat, up=(ox, oy, 0), scale=scale)
    parts.append(shaft)
    foot = spine[-1] + Vector((ox * 0.012, oy * 0.012, -spine[-1].z + 0.010))
    parts.append(ellipsoid(name + "_Pad", foot, (0.021, 0.019, 0.011), mat))
    # Four toes in an arc toward the outward direction.
    side = Vector((-oy, ox, 0.0))
    fwd = Vector((ox, oy, 0.0))
    for i, a in enumerate((-1.5, -0.5, 0.5, 1.5)):
        c = foot + fwd * (0.017 - 0.002 * abs(a)) + side * (0.0085 * a) + Vector((0, 0, -0.002))
        toe = ellipsoid(f"{name}_Toe{i}", c, (0.0072, 0.0062, 0.0075), toe_mat, 24, 12)
        parts.append(toe)
    return parts


def cord_path(points, samples=48):
    """Smooth open path through control points (Catmull-Rom)."""
    pts = [Vector(p) for p in points]
    out = []
    for i in range(len(pts) - 1):
        p0 = pts[max(i - 1, 0)]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[min(i + 2, len(pts) - 1)]
        for s in range(samples // (len(pts) - 1)):
            t = s / (samples // (len(pts) - 1))
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 +
                              (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(pts[-1])
    return out


def tassel(name, top, mat_cord, mat_silk, length=0.078, strands=64, seed=0):
    g = np.random.default_rng(seed)
    parts = []
    parts.append(ellipsoid(name + "_Knot", top + Vector((0, 0, -0.008)), (0.0078, 0.0078, 0.0072), mat_cord, 24, 12))
    head = lathe(name + "_Head", [(0.0005, -0.016), (0.0062, -0.0158), (0.0078, -0.020), (0.0080, -0.030),
                                 (0.0076, -0.034), (0.0005, -0.0345)], mat_silk, sides=28)
    L.transform(head, Matrix.Translation(top))
    parts.append(head)
    # Skirt: tapered strands flaring slightly, each a thin 5-sided tube.
    for k in range(strands):
        ang = g.random() * math.tau
        rr = 0.0068 * math.sqrt(g.random())
        x0, y0 = rr * math.cos(ang), rr * math.sin(ang)
        flare = 0.10 + 0.08 * g.random()
        ln = length * (0.92 + 0.10 * g.random())
        pts = []
        for s in range(7):
            t = s / 6
            pts.append(top + Vector((x0 * (1 + flare * t * 3.0), y0 * (1 + flare * t * 3.0), -0.034 - ln * t)))
        prof = L.circle2d(0.00042, 5)
        st = L.sweep(f"{name}_S{k:03d}", pts, prof, mat_silk, up=(1, 0, 0),
                     scale=lambda u: (1.0 - 0.45 * u ** 2, 1.0 - 0.45 * u ** 2), cap_start=False, cap_end=True)
        parts.append(st)
    return parts


# ---------------------------------------------------------------------------
# Designs (maki-e, raden) rasterized in numpy
# ---------------------------------------------------------------------------

def _leaf_polys(cx, cy, size, rot_deg, seed):
    poly = CT.maple_leaf_polygon(seed=seed)
    a = math.radians(rot_deg)
    R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    return (poly @ R.T) * size + np.array([cx, cy])


def _leaf_veins(cx, cy, size, rot_deg, lobes=7):
    """Kakiwari veins: midribs from the leaf centre to each lobe tip."""
    a0 = math.radians(rot_deg)
    lines = []
    spread = math.radians(300.0)
    for i in range(lobes):
        t = -1 + 2 * i / (lobes - 1)
        ang = math.pi / 2 + t * spread / 2 + a0
        ln = (1.0 - 0.33 * abs(t)) * 0.80 * size
        lines.append([(cx, cy), (cx + math.cos(ang) * ln, cy + math.sin(ang) * ln)])
    # Petiole.
    ang = -math.pi / 2 + a0
    lines.append([(cx, cy), (cx + math.cos(ang) * size * 0.55, cy + math.sin(ang) * size * 0.55)])
    return lines


def lid_top_design(w_px, h_px, w_m, h_m, seed=7):
    """Gold/raden/film maps for the lid top (x right, y toward the back)."""
    aspect = h_m / w_m
    g = np.random.default_rng(seed)
    # Normalized raster units: x in [-0.5, 0.5], y in [-aspect/2, aspect/2].
    mm = 1.0 / (w_m * 1000.0)
    border = []
    inset = 9 * mm
    bx, by = 0.5 - inset, aspect / 2 - inset
    border.append([(-bx, -by), (bx, -by), (bx, by), (-bx, by), (-bx, -by)])
    gold = CT.stroke_polyline(w_px, border, 1.4 * mm, height=h_px)
    # Flowing water: river band from upper left to lower right.
    lines = []
    for k in range(11):
        off = (k - 5) * 7.5 * mm
        pts = []
        for s in range(160):
            x = -0.52 + 1.04 * s / 159
            yc = 0.10 * aspect - 0.42 * x * aspect + 0.035 * math.sin(7.5 * x + 0.6 * k) + off
            pts.append((x, yc + 0.006 * math.sin(31 * x + k)))
        lines.append(pts)
    water = CT.stroke_polyline(w_px, lines, 0.75 * mm, height=h_px)
    # Clip water to inside the border.
    yy, xx = np.mgrid[0:h_px, 0:w_px]
    nx = (xx + 0.5) / w_px - 0.5
    ny = aspect / 2 - (yy + 0.5) / w_px
    inside = (np.abs(nx) < bx - 3 * mm) & (np.abs(ny) < by - 3 * mm)
    water *= inside
    # Maple leaves: gold with kakiwari veins; three of them raden.
    leaves = []
    tries = 0
    while len(leaves) < 15 and tries < 400:
        tries += 1
        cx = g.uniform(-bx + 25 * mm, bx - 25 * mm)
        cy = g.uniform(-by + 25 * mm, by - 25 * mm)
        size = g.uniform(17, 27) * mm
        if any((cx - a) ** 2 + (cy - b) ** 2 < (size + s + 6 * mm) ** 2 for a, b, s, _, _ in leaves):
            continue
        leaves.append((cx, cy, size, g.uniform(0, 360), int(g.integers(0, 1000))))
    mon_spots = [(-0.30, 0.17 * aspect * 2 - 0.10), (0.33, -0.05), (-0.05, -0.30 * aspect)]
    mon_d = 44 * mm
    keep = []
    for leaf in leaves:
        cx, cy, size = leaf[:3]
        if any((cx - mx) ** 2 + (cy - my) ** 2 < (size + mon_d / 2 + 4 * mm) ** 2 for mx, my in mon_spots):
            continue
        keep.append(leaf)
    leaf_cov = np.zeros((h_px, w_px), dtype=np.float32)
    raden_leaf = np.zeros_like(leaf_cov)
    vein = np.zeros_like(leaf_cov)
    for i, (cx, cy, size, rot_deg, s) in enumerate(keep):
        cov = CT.rasterize_polygons(w_px, [_leaf_polys(cx, cy, size, rot_deg, s)], supersample=2, height=h_px)
        v = CT.stroke_polyline(w_px, _leaf_veins(cx, cy, size, rot_deg), 0.55 * mm, height=h_px)
        if i % 5 == 2:
            raden_leaf = np.maximum(raden_leaf, cov)
        else:
            leaf_cov = np.maximum(leaf_cov, cov)
        vein = np.maximum(vein, v * cov)
    # Leaves float over the water: they occlude it.
    any_leaf = np.maximum(leaf_cov, raden_leaf)
    water *= 1.0 - any_leaf
    mons = np.zeros_like(leaf_cov)
    for mx, my in mon_spots:
        mons = np.maximum(mons, sora_mark.coverage_of_rings(
            w_px, sora_mark.transformed_rings(scale=mon_d, center=(mx, my)), supersample=3, height=h_px))
    water *= 1.0 - mons
    gold_map = np.clip(np.maximum.reduce([gold, water, leaf_cov * (1 - vein), mons]), 0, 1)
    raden_map = np.clip(raden_leaf * (1 - vein), 0, 1)
    film = CT.raden_maps(max(w_px, h_px), seed=seed + 5)["film"][:h_px, :w_px]
    return gold_map, raden_map, film


def band_design(w_px, h_px, w_m, h_m, seed, leaves=4, medallion_gap=None):
    """Side/front bands: double gold border lines and a few drifting leaves."""
    aspect = h_m / w_m
    mm = 1.0 / (w_m * 1000.0)
    g = np.random.default_rng(seed)
    top = aspect / 2 - 4 * mm
    bot = -aspect / 2 + 4 * mm
    lines = [[(-0.5, top), (0.5, top)], [(-0.5, top - 2.6 * mm), (0.5, top - 2.6 * mm)],
             [(-0.5, bot), (0.5, bot)]]
    gold = CT.stroke_polyline(w_px, lines, 0.9 * mm, height=h_px)
    cov_all = np.zeros((h_px, w_px), dtype=np.float32)
    placed = []
    tries = 0
    while len(placed) < leaves and tries < 200:
        tries += 1
        size = g.uniform(11, 16) * mm
        cx = g.uniform(-0.5 + size, 0.5 - size)
        cy = g.uniform(bot + size + 3 * mm, top - size - 4 * mm) if top - bot > 2 * size + 8 * mm else 0.0
        if medallion_gap is not None and abs(cx) < medallion_gap:
            continue
        if any(abs(cx - a) < (size + b + 8 * mm) for a, b in placed):
            continue
        placed.append((cx, size))
        rot_deg = g.uniform(0, 360)
        cov = CT.rasterize_polygons(w_px, [_leaf_polys(cx, cy, size, rot_deg, int(g.integers(0, 999)))],
                                    supersample=2, height=h_px)
        v = CT.stroke_polyline(w_px, _leaf_veins(cx, cy, size, rot_deg), 0.45 * mm, height=h_px)
        cov_all = np.maximum(cov_all, cov * (1 - v * cov))
    return np.clip(np.maximum(gold, cov_all), 0, 1)


def medallion_design(px):
    """Raden coverage = the mark's filled paths; film map for iridescence."""
    raden = sora_mark.coverage(px, scale=0.94, supersample=4)
    film = CT.raden_maps(px, seed=97, band_count=22.0, warp=0.06)["film"]
    return raden, film


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build(opts):
    b = P.PropBuild(SPEC, opts)
    scene = b.scene

    # Designs ---------------------------------------------------------------
    lw, lh = 2048, int(2048 * LID[1] / LID[0])
    gold_top, raden_top, film_top = lid_top_design(lw, lh, LID[0], LID[1])
    img_gold_top = P.design_image("D_LidTop_Gold", gold_top)
    img_raden_top = P.design_image("D_LidTop_Raden", raden_top)
    img_film_top = P.design_image("D_LidTop_Film", film_top)
    band_px = (2048, 256)
    designs = [dict(img_gold=img_gold_top, img_raden=img_raden_top, img_film=img_film_top,
                    origin=(-LID[0] / 2, -LID[1] / 2, 0.0), u=(1, 0, 0), v=(0, 1, 0), size=(LID[0], LID[1]),
                    facing=(0, 0, 1))]
    lid_side_h = LID[2]
    lid_z0 = LID_Z1 - LID[2]
    for name, origin, u, size, facing, seed in (
            ("LidFront", (-LID[0] / 2, 0, lid_z0), (1, 0, 0), (LID[0], lid_side_h), (0, -1, 0), 3),
            ("LidBack", (LID[0] / 2, 0, lid_z0), (-1, 0, 0), (LID[0], lid_side_h), (0, 1, 0), 4),
            ("LidLeft", (0, LID[1] / 2, lid_z0), (0, -1, 0), (LID[1], lid_side_h), (-1, 0, 0), 5),
            ("LidRight", (0, -LID[1] / 2, lid_z0), (0, 1, 0), (LID[1], lid_side_h), (1, 0, 0), 6)):
        arr = band_design(band_px[0], int(band_px[0] * size[1] / size[0]), size[0], size[1], seed, leaves=3)
        designs.append(dict(img_gold=P.design_image(f"D_{name}_Gold", arr), origin=origin, u=u, v=(0, 0, 1),
                            size=size, facing=facing))
    vis_h = LID_Z1 - LID[2] - BODY_Z0
    for name, origin, u, size, facing, seed, gap in (
            ("BodyFront", (-BODY[0] / 2, 0, BODY_Z0), (1, 0, 0), (BODY[0], vis_h), (0, -1, 0), 13, 0.11),
            ("BodyBack", (BODY[0] / 2, 0, BODY_Z0), (-1, 0, 0), (BODY[0], vis_h), (0, 1, 0), 14, None),
            ("BodyLeft", (0, BODY[1] / 2, BODY_Z0), (0, -1, 0), (BODY[1], vis_h), (-1, 0, 0), 15, 0.09),
            ("BodyRight", (0, -BODY[1] / 2, BODY_Z0), (0, 1, 0), (BODY[1], vis_h), (1, 0, 0), 16, 0.09)):
        arr = band_design(band_px[0], int(band_px[0] * size[1] / size[0]), size[0], size[1], seed, leaves=4,
                          medallion_gap=gap)
        designs.append(dict(img_gold=P.design_image(f"D_{name}_Gold", arr), origin=origin, u=u, v=(0, 0, 1),
                            size=size, facing=facing))
    med_raden, med_film = medallion_design(1024)
    img_med_raden = P.design_image("D_Medallion_Raden", med_raden)
    img_med_film = P.design_image("D_Medallion_Film", med_film)

    # Materials ---------------------------------------------------------------
    m_lacquer = P.mat_lacquer_design("Craft_RoiroMakie", designs, wear=0.10)
    m_stand = P.mat_lacquer_design("Craft_RoiroStand", [], wear=0.22, rough=0.11)
    m_gilt = P.mat_gilt_copper("Craft_GiltCopper")
    med_r = MEDALLION_D * 0.47
    m_medallion = P.mat_lacquer_design(
        "Craft_RadenMedallion",
        [dict(img_raden=img_med_raden, img_film=img_med_film, origin=(-med_r, 0, MEDALLION_Z - med_r),
              u=(1, 0, 0), v=(0, 0, 1), size=(2 * med_r, 2 * med_r), facing=(0, -1, 0))],
        wear=0.0, rough=0.035)
    m_cord = L.mat_braid("Craft_SilkCord", (0.36, 0.016, 0.014), scale=0.8, sheen=0.6, rough=0.42, kind="round")
    m_silk = L.mat_braid("Craft_SilkTassel", (0.40, 0.020, 0.016), scale=0.5, sheen=0.7, rough=0.38, kind="round")

    # Stand -------------------------------------------------------------------
    st = rounded_box("Stand_Top", (0, 0, STAND_H - STAND_TOP[2] / 2), STAND_TOP, 0.004, m_stand, n=(26, 20, 6))
    b.add(st)
    rim = rounded_box("Stand_Rim", (0, 0, STAND_H + 0.002), (BODY[0] + 0.024, BODY[1] + 0.024, 0.004), 0.0018,
                      m_stand, n=(24, 18, 4))
    hollow(rim, (0, 0, STAND_H + 0.002), (BODY[0] + 0.004, BODY[1] + 0.004, 0.010), 0.001)
    b.add(rim)
    apron_h = 0.044
    for name, center, size, plane in (
            ("Apron_Front", (0, -(STAND_TOP[1] / 2 - 0.022), STAND_H - STAND_TOP[2] - apron_h / 2),
             (STAND_TOP[0] - 0.060, 0.014, apron_h), "XZ"),
            ("Apron_Back", (0, (STAND_TOP[1] / 2 - 0.022), STAND_H - STAND_TOP[2] - apron_h / 2),
             (STAND_TOP[0] - 0.060, 0.014, apron_h), "XZ"),
            ("Apron_Left", (-(STAND_TOP[0] / 2 - 0.022), 0, STAND_H - STAND_TOP[2] - apron_h / 2),
             (0.014, STAND_TOP[1] - 0.060, apron_h), "YZ"),
            ("Apron_Right", ((STAND_TOP[0] / 2 - 0.022), 0, STAND_H - STAND_TOP[2] - apron_h / 2),
             (0.014, STAND_TOP[1] - 0.060, apron_h), "YZ")):
        ap = rounded_box(name, center, size, 0.0025, m_stand,
                         n=(20, 4, 8) if plane == "XZ" else (4, 20, 8))
        span = size[0] if plane == "XZ" else size[1]
        n_open = 3 if span > 0.45 else 2
        for k in range(n_open):
            c = -span / 2 + span * (k + 0.5) / n_open
            outline = kozama_outline(span / n_open * 0.62, apron_h * 0.62)
            z0 = center[2] - apron_h / 2 - 0.001
            if plane == "XZ":
                loop = [(c + x, z0 + z) for x, z in outline]
                cut = L.extrude_outline(name + f"_K{k}", [loop], 0.05, bevel=0.0008, plane="XZ", center=center[1])
            else:
                loop = [(c + x, z0 + z) for x, z in outline]
                cut = L.extrude_outline(name + f"_K{k}", [loop], 0.05, bevel=0.0008, plane="YZ", center=center[0])
            L.boolean(ap, cut)
        b.add(ap)
    leg_h = STAND_H - STAND_TOP[2]
    for i, (sx, sy) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1))):
        top = Vector((sx * (STAND_TOP[0] / 2 - 0.040), sy * (STAND_TOP[1] / 2 - 0.040), leg_h))
        out = Vector((sx, sy, 0)).normalized()
        for part in neko_ashi(f"Leg{i}", top, (out.x, out.y), leg_h, m_stand, m_gilt):
            b.add(part, lod_drop=2 if "Toe" in part.name else 99)

    # Box body and lid ----------------------------------------------------------
    # The lid stays closed on its stand: body and lid are solid shells, so no
    # unseen interior takes atlas space. The body runs up under the lid.
    body_h = LID_Z1 - LID[2] - BODY_Z0 + 0.012
    body = rounded_box("Body", (0, 0, BODY_Z0 + body_h / 2), (BODY[0], BODY[1], body_h), CORNER_R, m_lacquer,
                       n=(30, 22, 10))
    b.add(body)
    lid_c = (0, 0, LID_Z1 - LID[2] / 2)
    lid = rounded_box("Lid", lid_c, LID, CORNER_R, m_lacquer, n=(34, 26, 8), crown=CROWN)
    b.add(lid)
    for i, (sx, sy) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1))):
        corner = (sx * (LID[0] / 2 - 0.004), sy * (LID[1] / 2 - 0.004), LID_Z1 - 0.004)
        b.add(corner_cap(f"Cap_Lid{i}", lid_c, LID, corner, m_gilt, CROWN), lod_drop=2)
        cornerb = (sx * (BODY[0] / 2 - 0.004), sy * (BODY[1] / 2 - 0.004), BODY_Z0 + 0.004)
        b.add(corner_cap(f"Cap_Body{i}", (0, 0, BODY_Z0 + BODY[2] / 2), BODY, cornerb, m_gilt, 0.0,
                         radius_cap=0.030), lod_drop=2)

    # Raden medallion in a gilt rim on the body front ------------------------------
    face_y = -BODY[1] / 2
    rim_prof = [(med_r - 0.0006, 0.0), (med_r + 0.0006, 0.0011), (med_r + 0.0024, 0.0019), (med_r + 0.0040, 0.0011),
                (med_r + 0.0046, 0.0)]
    mrim = lathe("Medallion_Rim", rim_prof, m_gilt, sides=96,
                 axis_matrix=Matrix.Translation((0, face_y, MEDALLION_Z)) @ L.rot("X", 90))
    b.add(mrim)
    dome = [(0.0004, 0.0018)] + [(med_r * t, 0.0018 - 0.0009 * t ** 2) for t in np.linspace(0.05, 1.0, 18)] + \
           [(med_r, 0.0003), (med_r - 0.0002, 0.0)]
    disc = lathe("Medallion_Raden", dome, m_medallion, sides=96,
                 axis_matrix=Matrix.Translation((0, face_y, MEDALLION_Z)) @ L.rot("X", 90))
    b.add(disc)

    # Side ring fittings, cords and tassels -------------------------------------------
    ring_z = BODY_Z0 + 0.060
    for sx in (-1, 1):
        x_face = sx * BODY[0] / 2
        plate = lathe(f"Kan_Plate{sx}", [(0.0004, 0.0028), (0.006, 0.0027), (0.009, 0.0018), (0.013, 0.0012),
                                         (0.0135, 0.0)], m_gilt, sides=48,
                      axis_matrix=Matrix.Translation((x_face, 0, ring_z)) @ L.rot("Y", 90 * sx))
        b.add(plate, lod_drop=2)
        ring_c = Vector((x_face + sx * 0.0045, 0.0, ring_z - 0.011))
        torus_pts = [ring_c + Vector((0.0, 0.0115 * math.sin(a), 0.0115 * math.cos(a)))
                     for a in np.linspace(0, math.tau, 49)[:-1]]
        # Drop ring (kan) hangs flat against the side, in the face's plane.
        ring = L.sweep(f"Kan_Ring{sx}", torus_pts, L.circle2d(0.0019, 10), m_gilt, up=(1, 0, 0), closed_path=True)
        b.add(ring, lod_drop=2)
        bottom = ring_c + Vector((0, 0, -0.0115))
        edge_x = sx * STAND_TOP[0] / 2
        path = cord_path([bottom, bottom + Vector((sx * 0.006, -0.004, -0.030)),
                          Vector((edge_x - sx * 0.010, -0.016, STAND_H + 0.0026)),
                          Vector((edge_x + sx * 0.0035, -0.020, STAND_H - 0.006)),
                          Vector((edge_x + sx * 0.0065, -0.024, STAND_H - 0.040)),
                          Vector((edge_x + sx * 0.0060, -0.026, STAND_H - 0.062))], samples=60)
        cord = L.sweep(f"Cord{sx}", path, L.circle2d(0.0023, 10), m_cord, up=(0, 1, 0))
        b.add(cord)
        for part in tassel(f"Tassel{sx}", path[-1], m_cord, m_silk, seed=5 + sx):
            b.add(part, lod_drop=2 if "_S" in part.name else 99)

    b.notes["design"] = ("Edo daimyo-trousseau lacquer: roiro black, hiramaki-e gold Tatsuta-gawa water and maple "
                         "leaves with kakiwari veins, three gold SORA mons (mon-chirashi), raden leaves, domed raden "
                         "SORA medallion in a gilt rim, shu red interior, gilt copper corner caps with nanako, "
                         "silk cords and tassels; neko-ashi (cat-paw) stand with kōzama aprons.")
    b.notes["scale"] = "Box 460 x 340 x 150 mm, lid 470 x 350 x 55 mm, stand 560 x 410 x 160 mm."
    b.finalize()
    return b


if __name__ == "__main__":
    build(L.parse_args())
