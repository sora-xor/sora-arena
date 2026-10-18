"""Tsumagizaka dojo hall kit: modular walls, columns, hinoki floor, coffered ceiling, kamiza.

Run (Blender 5.2.2):
  blender -b --factory-startup --python scripts/art/create_nyaagyu_dojo_kit.py

Builds the visual shell for the campaign's estate hall zones (36 x 26 m,
7 m walls in chapter 1). The world builder repeats these modules along the
zone's walls; its primitive floor, wall and cover boxes stay the collision.
Construction follows Edo shinkabe practice: square hinoki columns stand
proud of recessed infill; tate-hameita (vertical boards with battens) up to
the uchinori-nageshi at door-head height, earthen plaster above with a nuki
rail and a ceiling cornice; renji-mado (diamond-section slat windows) low and
high; akari-shoji with kumiko lattice; a coffered gotenjo whose panels carry
the SORA mark in gold leaf on indigo, alternating with maple roundels.

Every module is closed, at least 18 cm thick where it must stop light
(Lumen distance fields leak through thinner walls), and uses metre-scale
UV0 for tiling scans, except floor boards (per-board UV windows into the
plank scan so no two neighbours repeat) and coffer panels (design atlas).
Outputs: Content/SourceArt/Environment/NyaagyuDojoKit/.
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
import sora_arch_lib as A  # noqa: E402
import sora_mark  # noqa: E402

OUT = A.ROOT / "Content/SourceArt/Environment/NyaagyuDojoKit"
GEN = "scripts/art/create_nyaagyu_dojo_kit.py"

BAY_W = 1.80        # nominal bay (1 ken = 6 shaku is 1.82 m); placement scales X to fit
WALL_H = 7.00
COL = 0.24          # column section
COL_FRONT = -0.04   # column face, 4 cm into the room (inside the player's capsule radius)
INFILL = 0.020      # board/plaster plane
SLAB0, SLAB1 = 0.030, 0.210  # light-stopping backing slab
NAGESHI = (2.10, 2.30, -0.070)
CORNICE = (6.78, 7.00, -0.080)
KOSHI = (0.88, 1.00, -0.005)
NUKI = (4.30, 4.42, 0.000)
HALF_IN = BAY_W / 2 - COL / 2   # infill half width between columns


def h_member(name, z0, z1, face_y, role="DarkTimber", half=BAY_W / 2, depth=None):
    back = SLAB0 if depth is None else face_y + depth
    return A.block(name, -half, half, face_y, back, z0, z1, role, bevel=0.004)


def boards(name, x0, x1, z0, z1, y_face, role="CedarBoard", width=0.30, batten=True, seed=0):
    """Vertical boards (tate-hameita) with oshibuchi battens; each board samples
    its own window of the plank scan (UV0 in metres + a random offset)."""
    g = np.random.default_rng(seed)
    parts = []
    n = max(1, int(round((x1 - x0) / width)))
    w = (x1 - x0) / n
    for i in range(n):
        bx0 = x0 + i * w
        b = A.block(f"{name}_B{i}", bx0 + 0.001, bx0 + w - 0.001, y_face, y_face + 0.018, z0, z1, role, bevel=0.0015)
        A.metric_uv0(b)
        du, dv = g.uniform(0, 4.0), g.uniform(0, 4.0)
        uv = b.data.uv_layers["UV0"].data
        for loop in uv:
            loop.uv = (loop.uv[0] + du, loop.uv[1] + dv)
        parts.append(b)
        if batten and i > 0:
            bt = A.block(f"{name}_T{i}", bx0 - 0.016, bx0 + 0.016, y_face - 0.016, y_face + 0.002, z0, z1, "DarkTimber",
                         bevel=0.003)
            parts.append(A.metric_uv0(bt))
    return parts


def plaster(name, x0, x1, z0, z1, y_face=0.030):
    p = A.block(name, x0, x1, y_face, SLAB1, z0, z1, "Plaster", bevel=0.004)
    return A.metric_uv0(p)


def slab(name, x0, x1, z0, z1):
    s = A.block(name, x0, x1, SLAB0, SLAB1, z0, z1, "Plaster", bevel=0.002)
    return A.metric_uv0(s)


def renji(name, x0, x1, z0, z1, y=0.08, bar=0.030, pitch=0.090):
    """Renji-mado: frame plus diamond-section bars (square bars turned 45 degrees)."""
    parts = []
    fr = 0.050
    parts += [A.block(f"{name}_Sill", x0 - fr, x1 + fr, -0.03, SLAB1, z0 - fr, z0, "DarkTimber", bevel=0.004),
              A.block(f"{name}_Head", x0 - fr, x1 + fr, -0.03, SLAB1, z1, z1 + fr, "DarkTimber", bevel=0.004),
              A.block(f"{name}_JambL", x0 - fr, x0, -0.03, SLAB1, z0, z1, "DarkTimber", bevel=0.004),
              A.block(f"{name}_JambR", x1, x1 + fr, -0.03, SLAB1, z0, z1, "DarkTimber", bevel=0.004)]
    n = max(2, int(round((x1 - x0) / pitch)))
    for i in range(n):
        cx = x0 + (i + 0.5) * (x1 - x0) / n
        b = A.block(f"{name}_Bar{i}", cx - bar / 2, cx + bar / 2, y - bar / 2, y + bar / 2, z0, z1, "RenjiBar", bevel=0.002)
        L.transform(b, Matrix.Translation((cx, y, 0)) @ L.rot("Z", 45) @ Matrix.Translation((-cx, -y, 0)))
        parts.append(b)
    return [A.metric_uv0(p) for p in parts]


def shoji_pair(name, x0, x1, z0, z1, y=0.02):
    """Two akari-shoji: cedar stiles/rails, kumiko lattice, koshi panel and paper."""
    parts = []
    mid = (x0 + x1) / 2
    for k, (a, b) in enumerate(((x0, mid + 0.015), (mid - 0.015, x1))):
        yy = y + (0.0 if k == 0 else 0.035)  # the two panels run in separate grooves
        st = 0.032
        parts += [A.block(f"{name}{k}_StileL", a, a + st, yy - 0.015, yy + 0.015, z0, z1, "Kumiko", bevel=0.002),
                  A.block(f"{name}{k}_StileR", b - st, b, yy - 0.015, yy + 0.015, z0, z1, "Kumiko", bevel=0.002),
                  A.block(f"{name}{k}_RailT", a, b, yy - 0.015, yy + 0.015, z1 - st, z1, "Kumiko", bevel=0.002),
                  A.block(f"{name}{k}_RailB", a, b, yy - 0.015, yy + 0.015, z0, z0 + 0.30, "CedarBoard", bevel=0.002)]
        # Kumiko: thin bars, vertical every ~26 cm, horizontal every ~28 cm.
        nv = max(2, int(round((b - a) / 0.26)))
        for i in range(1, nv):
            cx = a + (b - a) * i / nv
            parts.append(A.block(f"{name}{k}_KV{i}", cx - 0.0045, cx + 0.0045, yy - 0.010, yy + 0.008,
                                 z0 + 0.30, z1 - st, "Kumiko", bevel=0.001))
        nh = max(2, int(round((z1 - z0 - 0.33) / 0.28)))
        for i in range(1, nh):
            cz = z0 + 0.30 + (z1 - st - z0 - 0.30) * i / nh
            parts.append(A.block(f"{name}{k}_KH{i}", a + st, b - st, yy - 0.010, yy + 0.008, cz - 0.0045, cz + 0.0045,
                                 "Kumiko", bevel=0.001))
        paper = A.block(f"{name}{k}_Paper", a + st, b - st, yy + 0.009, yy + 0.011, z0 + 0.30, z1 - st, "ShojiPaper",
                        bevel=0.0)
        parts.append(paper)
    return [A.metric_uv0(p) for p in parts]


def panel_bay(kind, seed):
    """One 1.8 m bay between column centres. ``kind``: Panel, Renji, RenjiHigh, Shoji, DoorOpen."""
    parts = []
    x0, x1 = -HALF_IN, HALF_IN
    # Lower zone (0 .. nageshi).
    if kind in ("Panel", "RenjiHigh"):
        parts += boards(f"{kind}_Low", x0, x1, 0.0, NAGESHI[0], INFILL, seed=seed)
        parts.append(slab(f"{kind}_LowSlab", x0, x1, 0.0, NAGESHI[0]))
        parts.append(h_member(f"{kind}_Koshi", KOSHI[0], KOSHI[1], KOSHI[2], half=HALF_IN))
    elif kind == "Renji":
        win = (1.00, NAGESHI[0] - 0.05)
        parts += boards(f"{kind}_Low", x0, x1, 0.0, KOSHI[0], INFILL, seed=seed)
        parts.append(slab(f"{kind}_LowSlab", x0, x1, 0.0, KOSHI[0]))
        parts.append(h_member(f"{kind}_Koshi", KOSHI[0], KOSHI[1], KOSHI[2], half=HALF_IN))
        parts += renji(f"{kind}_Win", -0.62, 0.62, win[0] + 0.05, win[1])
        # Boards either side of the window.
        parts += boards(f"{kind}_SideL", x0, -0.67, KOSHI[1], NAGESHI[0], INFILL, width=0.11, batten=False, seed=seed + 1)
        parts += boards(f"{kind}_SideR", 0.67, x1, KOSHI[1], NAGESHI[0], INFILL, width=0.11, batten=False, seed=seed + 2)
        parts.append(slab(f"{kind}_SideSlabL", x0, -0.67, KOSHI[1], NAGESHI[0]))
        parts.append(slab(f"{kind}_SideSlabR", 0.67, x1, KOSHI[1], NAGESHI[0]))
    elif kind == "Shoji":
        parts += shoji_pair(f"{kind}_Shoji", x0, x1, 0.0, NAGESHI[0])
        parts.append(A.block(f"{kind}_Shikii", x0, x1, -0.02, SLAB1, -0.01, 0.012, "DarkTimber", bevel=0.003))
    elif kind == "DoorOpen":
        parts.append(A.block(f"{kind}_Shikii", x0, x1, -0.02, SLAB1, -0.01, 0.012, "DarkTimber", bevel=0.003))
        # Engawa outside: boards to 1.35 m, an edge beam and a post per bay, and
        # the garden ground half a metre below.
        for i in range(6):
            y0 = SLAB1 + 0.005 + i * 0.19
            bd = A.block(f"{kind}_Engawa{i}", -BAY_W / 2, BAY_W / 2, y0, y0 + 0.185, -0.03, 0.0, "Hinoki", bevel=0.002)
            parts.append(A.metric_uv0(bd))
        parts.append(A.block(f"{kind}_EngawaEdge", -BAY_W / 2, BAY_W / 2, 1.36, 1.48, -0.22, 0.0, "DarkTimber",
                             bevel=0.004))
        parts.append(A.block(f"{kind}_Post", -BAY_W / 2, -BAY_W / 2 + 0.15, 1.36, 1.51, -0.50, 2.95, "DarkTimber",
                             bevel=0.006))
        parts.append(A.block(f"{kind}_Keta", -BAY_W / 2, BAY_W / 2, 1.33, 1.53, 2.95, 3.15, "DarkTimber", bevel=0.006))
        for i in range(6):
            cx = -BAY_W / 2 + (i + 0.5) * BAY_W / 6
            r = A.block(f"{kind}_Taruki{i}", cx - 0.035, cx + 0.035, SLAB1, 2.70, 3.10, 3.18, "DarkTimber", bevel=0.004)
            # Rafter slope: drop 0.42 m over the eave's reach.
            for v in r.data.vertices:
                v.co.z -= (v.co.y - SLAB1) / (2.70 - SLAB1) * 0.42 * (1 if v.co.z > 3.0 else 1)
            parts.append(A.metric_uv0(r))
        soffit = A.block(f"{kind}_Soffit", -BAY_W / 2, BAY_W / 2, SLAB1, 2.70, 3.18, 3.20, "CedarBoard", bevel=0.0)
        for v in soffit.data.vertices:
            v.co.z -= (v.co.y - SLAB1) / (2.70 - SLAB1) * 0.42
        parts.append(A.metric_uv0(soffit))
        parts.append(A.metric_uv0(A.block(f"{kind}_Garden", -BAY_W / 2, BAY_W / 2, 1.48, 5.0, -0.56, -0.50, "Stone",
                                          bevel=0.0)))
    # Nageshi and the upper wall.
    parts.append(A.metric_uv0(h_member(f"{kind}_Nageshi", NAGESHI[0], NAGESHI[1], NAGESHI[2])))
    if kind == "RenjiHigh":
        wz0, wz1 = 4.55, 5.75
        parts.append(plaster(f"{kind}_UpA", x0, x1, NAGESHI[1], NUKI[0]))
        parts.append(A.metric_uv0(h_member(f"{kind}_Nuki", NUKI[0], NUKI[1], NUKI[2], half=HALF_IN)))
        parts.append(plaster(f"{kind}_UpB", x0, x1, NUKI[1], wz0 - 0.05))
        parts += renji(f"{kind}_HighWin", -0.62, 0.62, wz0, wz1)
        parts.append(plaster(f"{kind}_UpL", x0, -0.67, wz0 - 0.05, wz1 + 0.05))
        parts.append(plaster(f"{kind}_UpR", 0.67, x1, wz0 - 0.05, wz1 + 0.05))
        parts.append(plaster(f"{kind}_UpC", x0, x1, wz1 + 0.05, CORNICE[0]))
    else:
        parts.append(plaster(f"{kind}_UpA", x0, x1, NAGESHI[1], NUKI[0]))
        parts.append(A.metric_uv0(h_member(f"{kind}_Nuki", NUKI[0], NUKI[1], NUKI[2], half=HALF_IN)))
        parts.append(plaster(f"{kind}_UpB", x0, x1, NUKI[1], CORNICE[0]))
    parts.append(A.metric_uv0(h_member(f"{kind}_Cornice", CORNICE[0], CORNICE[1], CORNICE[2])))
    for p in parts:
        if p.get("rw_needs_unwrap", True):
            A.metric_uv0(p)
    return parts


def column():
    c = A.block("Column", -COL / 2, COL / 2, COL_FRONT, COL_FRONT + COL, 0.0, WALL_H, "DarkTimber", bevel=0.010,
                segments=2)
    return [A.metric_uv0(c)]


def floor_tile(seed, size=(3.6, 2.6), board_w=1.89 / 13, plank_rows=13, tex_m=1.89):
    """Hinoki boards running along X with staggered butt joints. UV0: each board
    maps to one plank row of the 4K scan (13 rows across ``tex_m`` metres) at a
    random offset along the grain, so the floor never repeats a board."""
    g = np.random.default_rng(seed)
    sx, sy = size
    parts = []
    rows = int(round(sy / board_w))
    bw = sy / rows
    for r in range(rows):
        y0 = -sy / 2 + r * bw
        x = -sx / 2
        # Lengths of 1.8 or 3.6 m with a random first cut so joints stagger.
        cut = g.choice([0.9, 1.8, 2.7])
        segs = [cut] + [3.6] * 3
        for k, ln in enumerate(segs):
            x1 = min(sx / 2, x + ln)
            if x1 - x < 0.05:
                break
            b = A.block(f"Floor_R{r}_S{k}", x + 0.0008, x1 - 0.0008, y0 + 0.0008, y0 + bw - 0.0008, -0.03, 0.0,
                        "Hinoki", bevel=0.0012)
            me = b.data
            row = int(g.integers(0, plank_rows))
            u_off = g.uniform(0, 1)
            uv = me.uv_layers["UV0"].data
            for poly in me.polygons:
                for li in poly.loop_indices:
                    co = me.vertices[me.loops[li].vertex_index].co
                    # Along the grain (X) in texture widths; across within one row.
                    across = (co.y - y0) / bw
                    uv[li].uv = (u_off + co.x / tex_m, (row + 0.06 + 0.88 * across) / plank_rows)
            b["rw_needs_unwrap"] = False
            parts.append(b)
            x = x1
            if x >= sx / 2 - 1e-6:
                break
    return parts


COFFER = 0.90


def coffer_designs(px=1024):
    """Gold-leaf SORA mon on indigo, and gold maple roundels on black lacquer.

    Returns (base_rgb, orm, mask) atlases 2 x 1 panels; Mask G = gold."""
    w, h = px * 2, px
    base = np.zeros((h, w, 3), np.float32)
    orm = np.zeros((h, w, 3), np.float32)
    mask = np.zeros((h, w, 3), np.float32)
    indigo = np.array([0.020, 0.032, 0.085], np.float32)
    black = np.array([0.011, 0.010, 0.009], np.float32)
    gold = np.array([1.0, 0.77, 0.34], np.float32)
    fbm = CT.fbm(px, 5, octaves=5, base=6.0)
    for k in range(2):
        cov_ring = CT.stroke_polyline(px, [[(0.42 * math.cos(t), 0.42 * math.sin(t))
                                            for t in np.linspace(0, math.tau, 240)]], 0.012)
        if k == 0:
            mark = sora_mark.coverage(px, scale=0.62, supersample=3)
            gold_cov = np.maximum(mark, cov_ring)
            ground = indigo
        else:
            leaves = np.zeros((px, px), np.float32)
            for i in range(5):
                a = math.tau * i / 5 + 0.3
                poly = CT.maple_leaf_polygon(seed=40 + i) * 0.13
                ang = a + math.pi / 2
                R = np.array([[math.cos(ang), -math.sin(ang)], [math.sin(ang), math.cos(ang)]])
                poly = poly @ R.T + np.array([0.22 * math.cos(a), 0.22 * math.sin(a)])
                leaves = np.maximum(leaves, CT.rasterize_polygons(px, [poly], supersample=2))
            gold_cov = np.maximum(leaves, cov_ring)
            ground = black
        tint = (0.92 + 0.16 * fbm)[..., None]
        panel = ground * tint * (1 - gold_cov[..., None]) + gold * (0.9 + 0.1 * fbm[..., None]) * gold_cov[..., None]
        base[:, k * px:(k + 1) * px] = panel
        orm[:, k * px:(k + 1) * px, 0] = 1.0
        orm[:, k * px:(k + 1) * px, 1] = (0.55 + 0.1 * fbm) * (1 - gold_cov) + 0.30 * gold_cov
        orm[:, k * px:(k + 1) * px, 2] = gold_cov
        mask[:, k * px:(k + 1) * px, 1] = gold_cov
    return base, orm, mask


def save_png(path: Path, arr: np.ndarray, srgb: bool):
    arr = np.clip(arr, 0, 1)
    if srgb:
        arr = np.where(arr <= 0.0031308, arr * 12.92, 1.055 * np.power(arr, 1 / 2.4) - 0.055)
    h, w = arr.shape[:2]
    img = bpy.data.images.new(path.stem, w, h, alpha=False, float_buffer=False)
    img.colorspace_settings.name = "sRGB" if srgb else "Non-Color"
    rgba = np.ones((h, w, 4), np.float32)
    rgba[..., :3] = arr
    img.pixels.foreach_set(rgba[::-1].ravel())
    L.save_png_max(img, path, rgba[::-1], False)
    bpy.data.images.remove(img)
    return path


def ceiling_tile():
    """Two by two coffers (gotenjo): lacquered ribs, recessed painted panels and
    gilt cross fittings at the rib crossings. Ribs at z 7.00, panels 10 cm up."""
    parts = []
    half = BAY_W / 2
    z0 = WALL_H
    rib = 0.085
    for i, x in enumerate((-half, 0.0, half)):
        parts.append(A.block(f"Ceil_RibX{i}", x - rib / 2, x + rib / 2, -half, half, z0, z0 + 0.11, "Lacquer", bevel=0.004))
    for i, y in enumerate((-half, 0.0, half)):
        parts.append(A.block(f"Ceil_RibY{i}", -half, half, y - rib / 2, y + rib / 2, z0 + 0.002, z0 + 0.108, "Lacquer",
                             bevel=0.004))
    for i, x in enumerate((-half, 0.0, half)):
        for j, y in enumerate((-half, 0.0, half)):
            parts.append(A.block(f"Ceil_Fit{i}{j}", x - 0.07, x + 0.07, y - 0.07, y + 0.07, z0 - 0.006, z0 + 0.004,
                                 "Gilt", bevel=0.003))
    for i, cx in enumerate((-half / 2, half / 2)):
        for j, cy in enumerate((-half / 2, half / 2)):
            k = (i + j) % 2  # alternate mon and maple panels
            p = A.block(f"Ceil_Panel{i}{j}", cx - half / 2 + rib / 2, cx + half / 2 - rib / 2,
                        cy - half / 2 + rib / 2, cy + half / 2 - rib / 2, z0 + 0.10, z0 + 0.12, "CofferPanel", bevel=0.0)
            me = p.data
            uv = me.uv_layers["UV0"].data
            span = half - rib
            for poly in me.polygons:
                for li in poly.loop_indices:
                    co = me.vertices[me.loops[li].vertex_index].co
                    u = (co.x - (cx - span / 2)) / span
                    v = (co.y - (cy - span / 2)) / span
                    uv[li].uv = ((k + np.clip(u, 0, 1)) / 2.0, np.clip(v, 0, 1))
            p["rw_needs_unwrap"] = False
            parts.append(p)
    for p in parts:
        if p.get("rw_needs_unwrap", True):
            A.metric_uv0(p)
    return parts


def kamiza(width=4 * BAY_W, depth=1.80, open_h=3.40):
    """East-wall shrine alcove beyond the wall plane: raised hinoki dais, shoji
    back wall glowing with the dawn, lintel, side walls, board ceiling and the
    standard upper wall above the lintel with two high renji-mado."""
    parts = []
    hw = width / 2
    dais = 0.30
    parts.append(A.block("Kamiza_DaisEdge", -hw, hw, -0.02, 0.06, 0.0, dais, "Lacquer", bevel=0.006))
    g = np.random.default_rng(3)
    nb = int(round(depth / 0.24))
    for i in range(nb):
        y0 = 0.06 + i * (depth - 0.06) / nb
        b = A.block(f"Kamiza_Board{i}", -hw, hw, y0, y0 + (depth - 0.06) / nb - 0.001, dais - 0.03, dais, "Hinoki",
                    bevel=0.0012)
        A.metric_uv0(b)
        off = g.uniform(0, 3)
        for loop in b.data.uv_layers["UV0"].data:
            loop.uv = (loop.uv[0] + off, loop.uv[1])
        parts.append(b)
    parts.append(A.metric_uv0(A.block("Kamiza_Base", -hw, hw, 0.06, depth, 0.0, dais - 0.03, "DarkTimber", bevel=0.0)))
    # Back wall: four shoji pairs between posts.
    for i in range(4):
        cx0 = -hw + i * width / 4
        parts += [p for p in shoji_pair(f"Kamiza_Shoji{i}", cx0 + 0.06, cx0 + width / 4 - 0.06, dais, open_h - 0.02,
                                        y=depth - 0.05)]
        parts.append(A.metric_uv0(A.block(f"Kamiza_Post{i}", cx0 - 0.06, cx0 + 0.06, depth - 0.10, depth + 0.06, dais,
                                          open_h, "DarkTimber", bevel=0.006)))
    parts.append(A.metric_uv0(A.block("Kamiza_Post4", hw - 0.06, hw + 0.06, depth - 0.10, depth + 0.06, dais, open_h,
                                      "DarkTimber", bevel=0.006)))
    # Side walls, ceiling and lintel.
    for s in (-1, 1):
        parts.append(A.metric_uv0(A.block(f"Kamiza_Side{s}", s * hw - (0.18 if s > 0 else 0), s * hw + (0 if s > 0 else 0.18)
                                          , 0.0, depth + 0.06, 0.0, open_h, "Plaster", bevel=0.003)))
    parts.append(A.metric_uv0(A.block("Kamiza_Ceiling", -hw, hw, 0.0, depth + 0.06, open_h, open_h + 0.04, "CedarBoard",
                                      bevel=0.0)))
    parts.append(A.metric_uv0(A.block("Kamiza_Roof", -hw - 0.2, hw + 0.2, -0.0, depth + 0.4, open_h + 0.04, open_h + 0.26,
                                      "DarkTimber", bevel=0.0)))
    parts.append(A.metric_uv0(A.block("Kamiza_Lintel", -hw, hw, -0.07, SLAB1, open_h, open_h + 0.22, "DarkTimber",
                                      bevel=0.006)))
    # Upper wall over the alcove: plaster with two high renji windows.
    up0 = open_h + 0.22
    parts.append(plaster("Kamiza_UpA", -hw, hw, up0, NUKI[0]))
    parts.append(A.metric_uv0(h_member("Kamiza_Nuki", NUKI[0], NUKI[1], NUKI[2], half=hw)))
    wz0, wz1 = 4.55, 5.75
    for k, cx in enumerate((-hw / 2, hw / 2)):
        parts += renji(f"Kamiza_HighWin{k}", cx - 0.9, cx + 0.9, wz0, wz1)
    parts.append(plaster("Kamiza_UpB0", -hw, -hw / 2 - 0.95, NUKI[1], wz1 + 0.05))
    parts.append(plaster("Kamiza_UpB1", -hw / 2 + 0.95, hw / 2 - 0.95, NUKI[1], wz1 + 0.05))
    parts.append(plaster("Kamiza_UpB2", hw / 2 + 0.95, hw, NUKI[1], wz1 + 0.05))
    parts.append(plaster("Kamiza_UpB3", -hw, hw, NUKI[1], wz0 - 0.05))
    parts.append(plaster("Kamiza_UpC", -hw, hw, wz1 + 0.05, CORNICE[0]))
    parts.append(A.metric_uv0(h_member("Kamiza_Cornice", CORNICE[0], CORNICE[1], CORNICE[2], half=hw)))
    for p in parts:
        if p.get("rw_needs_unwrap", True):
            A.metric_uv0(p)
    return parts


def build():
    A.reset()
    OUT.mkdir(parents=True, exist_ok=True)
    modules = []
    for i, kind in enumerate(("Panel", "Renji", "RenjiHigh", "Shoji", "DoorOpen")):
        parts = panel_bay(kind, seed=10 + i)
        name = f"SM_DojoBay_{kind}"
        modules.append(A.export_module(name, parts, OUT, lod_ratios=(1.0,),
                                       record={"role": "wall bay", "nominal_width_m": BAY_W}))
        for p in parts:
            bpy.data.objects.remove(p, do_unlink=True)
        print("DOJO_KIT", name, modules[-1]["lods"][0]["triangles"], flush=True)
    parts = column()
    modules.append(A.export_module("SM_DojoColumn", parts, OUT, lod_ratios=(1.0,),
                                   record={"role": "column at bay boundaries"}))
    for p in parts:
        bpy.data.objects.remove(p, do_unlink=True)
    for v in range(4):
        parts = floor_tile(100 + v)
        modules.append(A.export_module(f"SM_DojoFloor_{v}", parts, OUT, lod_ratios=(1.0,),
                                       record={"role": "floor tile 3.6 x 2.6 m", "uv0": "per-board plank windows"}))
        for p in parts:
            bpy.data.objects.remove(p, do_unlink=True)
    parts = ceiling_tile()
    modules.append(A.export_module("SM_DojoCeiling", parts, OUT, lod_ratios=(1.0,),
                                   record={"role": "coffered ceiling tile 1.8 x 1.8 m",
                                           "uv0": "CofferPanel: 2x1 design atlas; others metric"}))
    for p in parts:
        bpy.data.objects.remove(p, do_unlink=True)
    parts = kamiza()
    modules.append(A.export_module("SM_DojoKamiza", parts, OUT, lod_ratios=(1.0,),
                                   record={"role": "east-wall kamiza alcove, four bays wide, beyond the wall plane"}))
    for p in parts:
        bpy.data.objects.remove(p, do_unlink=True)
    base, orm, mask = coffer_designs()
    tex = {"BaseColor": save_png(OUT / "T_DojoCoffer_BaseColor.png", base, True),
           "ORM": save_png(OUT / "T_DojoCoffer_ORM.png", orm, False),
           "Mask": save_png(OUT / "T_DojoCoffer_Mask.png", mask, False)}
    notes = {
        "collision": "Visual only. The world builder keeps its floor/wall/cover boxes as collision and hides them only when every module loads.",
        "sora_mark": {"svg": L.rel(sora_mark.SVG_PATH), "sha256": sora_mark.PINNED_SVG_SHA256,
                      "use": "coffer panels: gold leaf on indigo (T_DojoCoffer_*), rasterized from the SVG paths"},
        "textures": {k: {"file": L.rel(p), "sha256": L.sha256(p)} for k, p in tex.items()},
        "roles": {"Hinoki": "Poly Haven hinoki_planks (CC0)", "CedarBoard": "Poly Haven japanese_cedar_planks (CC0)",
                  "Plaster": "Poly Haven clay_plaster (CC0)", "DarkTimber": "cedar scan, aged/darkened",
                  "ShojiPaper": "TextureCan Paper 0017 (CC0), two-sided translucent",
                  "CofferPanel": "original design atlas above"},
    }
    A.write_manifest(OUT, "NyaagyuDojoKit", GEN, modules, notes)
    print("DOJO_KIT_READY", len(modules), "modules", flush=True)


if __name__ == "__main__":
    build()
