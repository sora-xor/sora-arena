"""Build the alien (Stellar Credit House) weapons: plasma matchlock (14),
needle SMG (3), phantom SMG (13), pulse carbine (11) and shock emitter (16).

Run:  blender -b --factory-startup --python scripts/art/create_runtime_weapon_alien.py [-- --only 14]

Story bible section 15.1: the alien family is "cold and extruded": micro-
engraved graphite, black glass with a thin-film tint, brushed titanium and
cyan emissive ledger lines. Alien arms carry the ledger sigil (a closed ring
of tally notches, deliberately unlike the SORA mon) and never the SORA mon.
All five are fictional; their lengths are design values. Emissive parts are
flagged in Mask R so Unreal can drive charge and pulse states.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import create_runtime_weapon_lib as L  # noqa: E402
import create_runtime_weapon_specs as S  # noqa: E402

CYAN = (0.12, 0.85, 1.0)


class Kit:
    def __init__(self, prefix):
        self.graphite = L.mat_graphite(f"M_{prefix}_Graphite", ledger=None)
        # Panel graphite: a lighter, more deeply micro-engraved composite (no glow;
        # emissive ledger lines are separate, sparse strips).
        self.ledger = L.mat_graphite(f"M_{prefix}_PanelGraphite", color=(0.045, 0.047, 0.052), rough=0.36,
                                     engrave=1.6, ledger=None)
        self.ti = L.mat_titanium(f"M_{prefix}_Titanium")
        self.glass = L.mat_black_glass(f"M_{prefix}_BlackGlass")
        self.glow = L.mat_emissive(f"M_{prefix}_Ledger", (0.02, 0.05, 0.06), CYAN, 8.0)


def chamfer_plate(name, outline, thick, mat, y=0.0, chamfer=None, radius=0.0):
    """Extruded outline with a flat chamfer: thick parts get a faceted,
    machined cross-section (chamfer ~11 % of the thickness)."""
    if chamfer is None:
        chamfer = max(0.0008, min(0.0045, thick * 0.11))
    pts = L.fillet_poly(outline, radius, 2) if radius else outline
    return L.extrude_outline(name, [pts], thick, chamfer, mat, "XZ", y, bevel_res=1, sharp_angle=30.0)


def bolt(b, name, x, z, y_face, side, kit, r=0.0017):
    hexp = L.polygon2d(6, 1.0, 0.0, 1, rot=0.0)
    t = L.tube(name, [(0.0, r, r), (0.0006, r, r), (0.0009, r * 0.8, r * 0.8)], kit.ti, sides=6, shape="poly",
               poly=hexp, max_seg=0.0, chunk=0.0, sharp_angle=30.0)
    # tube axis +X -> outward face normal (side * Y)
    L.transform(t, Matrix.Translation((x, y_face, z)) @ L.rot("Z", 90 * side))
    b.add(t, lod_drop=2)


def layered(b, name, outline, core, mat_core, panels, radius=0.0, kit=None, bolts=True):
    """A core plate plus raised, chamfered side panels (inset outline) on both
    faces, with hex fasteners near the panel corners."""
    b.add(chamfer_plate(name, outline, core, mat_core, 0.0, None, radius))
    for k, (inset, extra, mat) in enumerate(panels):
        inner = L.offset_outline(L.orient(outline, True), -inset)
        b.add(chamfer_plate(f"{name}_Panel{k}", inner, core + 2 * extra, mat, 0.0, 0.0012))
        if bolts and kit is not None:
            spots = L.offset_outline(inner, -0.0055)
            # keep up to four well-separated corners
            chosen = []
            for p_ in spots:
                if all((Vector(p_) - Vector(q)).length > 0.03 for q in chosen):
                    chosen.append(p_)
                if len(chosen) == 4:
                    break
            for j, (px, pz) in enumerate(chosen):
                for side in (-1, 1):
                    bolt(b, f"{name}_Bolt{k}_{j}_{side:+d}", px, pz, side * (core / 2 + extra), side, kit)


def glow_strip(b, name, x0, x1, z, y_face, h=0.0022, kit=None, side=-1):
    p = L.box(name, ((x0 + x1) / 2, y_face + side * 0.0002, z), (x1 - x0, 0.0012, h), kit.glow, 0.0003)
    b.add(p, lod_drop=2)


def ledger_sigil(b, name, cx, cz, r, y_face, kit, side=-1):
    """Closed ring with tally notches (groups of four plus a slash)."""
    ring_out = [(cx + r * math.cos(math.tau * k / 48), cz + r * math.sin(math.tau * k / 48)) for k in range(48)]
    ring_in = [(cx + r * 0.78 * math.cos(math.tau * k / 48), cz + r * 0.78 * math.sin(math.tau * k / 48))
               for k in range(48)]
    ring = L.extrude_outline(name, [ring_out, ring_in], 0.0010, 0.0002, kit.glow, "XZ", y_face + side * 0.0003)
    b.add(ring, lod_drop=2)
    n = 0
    for g in range(5):
        base = math.tau * g / 5
        for t in range(5):
            a = base + t * 0.105
            tick_len = r * 0.42
            ca, sa = math.cos(a), math.sin(a)
            if t < 4:
                p0 = Vector((cx + ca * r * 0.74, cz + sa * r * 0.74))
                p1 = Vector((cx + ca * (r * 0.74 - tick_len), cz + sa * (r * 0.74 - tick_len)))
            else:
                a0, a1 = base - 0.02, base + 0.34
                p0 = Vector((cx + math.cos(a0) * r * 0.70, cz + math.sin(a0) * r * 0.70))
                p1 = Vector((cx + math.cos(a1) * r * 0.40, cz + math.sin(a1) * r * 0.40))
            d = (p1 - p0)
            nrm = Vector((-d.y, d.x)).normalized() * 0.0005
            quad = [tuple(p0 - nrm), tuple(p1 - nrm), tuple(p1 + nrm), tuple(p0 + nrm)]
            tick = L.extrude_outline(f"{name}_Tick{n}", [quad], 0.0010, 0.0001, kit.glow, "XZ", y_face + side * 0.0003)
            b.add(tick, lod_drop=2)
            n += 1


def ring_emitter(b, name, x, r_out, r_in, depth, kit, bz):
    b.add(L.tube(f"{name}_Collar", [(x - depth, r_out * 0.94, r_out * 0.94, 0.0, bz), (x - depth + 0.002, r_out, r_out, 0.0, bz),
                                    (x - 0.002, r_out, r_out, 0.0, bz), (x, r_out * 0.95, r_out * 0.95, 0.0, bz)],
                 kit.ti, sides=48, max_seg=0.01, chunk=0.0, sharp_angle=35.0))
    b.add(L.tube(f"{name}_Glow", [(x - 0.004, r_in, r_in, 0.0, bz), (x + 0.0006, r_in, r_in, 0.0, bz)], kit.glow,
                 sides=48, max_seg=0.0, chunk=0.0))
    b.add(L.tube(f"{name}_Glass", [(x - 0.010, r_in * 0.9, r_in * 0.9, 0.0, bz), (x - 0.003, r_in * 0.9, r_in * 0.9, 0.0, bz)],
                 kit.glass, sides=48, max_seg=0.0, chunk=0.0))


def top_rail(b, name, x0, x1, z, kit, width=0.016):
    """Low titanium rail with evenly spaced cross-teeth."""
    b.add(chamfer_plate(f"{name}_Base", [(x0, z), (x1, z), (x1 - 0.003, z + 0.004), (x0 + 0.003, z + 0.004)],
                        width, kit.ti, 0.0, 0.0008))
    n = max(2, int((x1 - x0 - 0.01) / 0.0105))
    for i in range(n):
        x = x0 + 0.008 + i * 0.0105
        b.add(L.box(f"{name}_Tooth{i}", (x, 0.0, z + 0.0055), (0.0052, width * 0.92, 0.003), kit.ti, 0.0005),
              lod_drop=2)


def vent_block(b, name, x0, x1, zc, h, y_face, side, kit, n=5):
    """Recessed frame with slanted black-glass louvres on a side face."""
    frame = [(x0, zc - h / 2), (x1, zc - h / 2), (x1, zc + h / 2), (x0, zc + h / 2)]
    hole = L.fillet_poly([(x0 + 0.003, zc - h / 2 + 0.003), (x1 - 0.003, zc - h / 2 + 0.003),
                          (x1 - 0.003, zc + h / 2 - 0.003), (x0 + 0.003, zc + h / 2 - 0.003)], 0.0015, 2)
    b.add(L.extrude_outline(f"{name}_Frame", [frame, hole], 0.0024, 0.0005, kit.graphite, "XZ",
                            y_face + side * 0.0010, bevel_res=1))
    step = (x1 - x0 - 0.006) / n
    for i in range(n):
        xa = x0 + 0.003 + step * (i + 0.15)
        lv = [(xa, zc - h / 2 + 0.003), (xa + step * 0.45, zc - h / 2 + 0.003),
              (xa + step * 0.85, zc + h / 2 - 0.003), (xa + step * 0.4, zc + h / 2 - 0.003)]
        b.add(chamfer_plate(f"{name}_Louvre{i}", lv, 0.0016, kit.glass, y_face + side * 0.0004, 0.0003), lod_drop=2)


def cable(b, name, pts, kit, r=0.0024):
    path = []
    pts = [Vector(p_) for p_ in pts]
    for i in range(len(pts) - 1):
        for k in range(10):
            path.append(pts[i].lerp(pts[i + 1], k / 10))
    path.append(pts[-1])
    sm = [path[0]] + [(path[i - 1] + path[i] * 2 + path[i + 1]) / 4 for i in range(1, len(path) - 1)] + [path[-1]]
    b.add(L.sweep(name, sm, L.circle2d(r, 10), kit.graphite, up=(0, 1, 0), chunk=0.15, sharp_angle=None))
    for end in (sm[0], sm[-1]):
        c = L.tube(f"{name}_Ferrule", [(-0.004, r * 1.35, r * 1.35), (0.004, r * 1.35, r * 1.35)], kit.ti, sides=12,
                   max_seg=0.0, chunk=0.0)
        L.transform(c, Matrix.Translation(end))
        b.add(c, lod_drop=2)


def trigger_guard(b, name, x0, x1, z_top, depth, kit):
    guard = [(x0, z_top), (x1, z_top), (x1 - 0.01, z_top - depth), (x0, z_top - depth + 0.004)]
    hole = L.fillet_poly([(x0 + 0.006, z_top - 0.005), (x1 - 0.012, z_top - 0.005),
                          (x1 - 0.016, z_top - depth + 0.006), (x0 + 0.006, z_top - depth + 0.008)], 0.005, 3)
    b.add(L.extrude_outline(name, [L.fillet_poly(guard, [0.002, 0.003, 0.01, 0.01], 3), hole], 0.007, 0.0012,
                            kit.graphite, "XZ", 0.0, bevel_res=1, sharp_angle=30.0))


def build_plasma_matchlock(b: L.Build):
    k = Kit("PM")
    bz = 0.032
    x_back, xm = -0.36, 0.96
    stock = [(0.20, bz + 0.004), (0.02, bz + 0.010), (-0.06, bz - 0.004), (-0.12, 0.020), (-0.36, 0.012),
             (-0.362, -0.074), (-0.25, -0.080), (-0.12, -0.036), (-0.05, -0.020), (0.06, -0.016), (0.20, -0.004)]
    layered(b, "Stock", stock, 0.030, k.graphite, [(0.008, 0.0025, k.ledger)], radius=0.004, kit=k)
    # Receiver: titanium frame with an exposed charge coil inside a cage.
    # Open receiver: titanium top and bottom rails with end blocks, so the
    # charge coil shows through the cheek windows.
    b.add(chamfer_plate("Receiver_Rail_Top", [(-0.04, bz + 0.030), (0.18, bz + 0.026), (0.18, bz + 0.013),
                                              (-0.04, bz + 0.013)], 0.020, k.ti, 0.0, 0.0015))
    b.add(chamfer_plate("Receiver_Rail_Bottom", [(-0.03, bz - 0.010), (0.19, bz - 0.010), (0.19, bz - 0.018),
                                                 (-0.03, bz - 0.022)], 0.020, k.ti, 0.0, 0.0015))
    for xa, xb_ in ((-0.04, 0.012), (0.155, 0.19)):
        b.add(chamfer_plate(f"Receiver_Block_{xa:.2f}", [(xa, bz + 0.014), (xb_, bz + 0.014), (xb_, bz - 0.011),
                                                         (xa, bz - 0.011)], 0.020, k.ti, 0.0, 0.0015))
    for side in (-1, 1):
        cage = [(0.0, bz + 0.024), (0.17, bz + 0.022), (0.17, bz - 0.016), (0.0, bz - 0.018)]
        wins = [L.fillet_poly([(x0, bz + 0.014), (x0 + 0.034, bz + 0.014), (x0 + 0.034, bz - 0.008),
                               (x0, bz - 0.008)], 0.004, 3) for x0 in (0.014, 0.066, 0.118)]
        b.add(L.extrude_outline(f"Receiver_Cheek_{side:+d}", [cage] + wins, 0.005, 0.0012, k.graphite, "XZ",
                                side * 0.0145, bevel_res=1))
        b.add(chamfer_plate(f"Receiver_Glass_{side:+d}", [(0.0, bz + 0.024), (0.17, bz + 0.022), (0.17, bz + 0.017),
                                                          (0.0, bz + 0.019)], 0.006, k.glass, side * 0.0145))
    b.add(L.helix("Charge_Coil", 0.02, 0.15, 0.0085, 0.0034, 0.0022, k.glow, 0.0, bz + 0.003, 24, 6))
    b.add(L.tube("Coil_Core", [(0.015, 0.006, 0.006, 0.0, bz + 0.003), (0.155, 0.006, 0.006, 0.0, bz + 0.003)], k.ti,
                 sides=24, max_seg=0.03, chunk=0.0))
    # Long octagonal barrel (the matchlock silhouette) with a graphite shroud.
    oct8 = L.polygon2d(8, 1.0, 0.05, 1, rot=math.pi / 8)
    bar = L.bore_tube("Barrel", [(0.18, 0.0118, 0.0118), (0.60, 0.0108, 0.0108), (xm - 0.03, 0.0100, 0.0100),
                                 (xm, 0.0100, 0.0100)], 0.0048, 0.06, k.ti, shape="poly", poly=oct8, chunk=0.25,
                      sharp_angle=30.0)
    L.transform(bar, Matrix.Translation((0, 0, bz)))
    b.add(bar)
    for x0, x1 in ((0.20, 0.44), (0.47, 0.70)):
        sh = [(x0, bz + 0.016), (x1, bz + 0.015), (x1 + 0.01, bz), (x1, bz - 0.020), (x0, bz - 0.021), (x0 - 0.01, bz)]
        b.add(chamfer_plate(f"Shroud_{x0:.2f}", sh, 0.026, k.ledger, 0.0, 0.003))
        b.add(chamfer_plate(f"Charge_Rail_{x0:.2f}", [(x0 + 0.01, bz + 0.0145), (x1 - 0.01, bz + 0.0135),
                                                      (x1 - 0.012, bz + 0.0205), (x0 + 0.012, bz + 0.0215)],
                            0.010, k.glass, 0.0, 0.0015))
        for bx in (x0 + 0.02, x1 - 0.02):
            for side in (-1, 1):
                bolt(b, f"Shroud_Bolt_{x0:.2f}_{bx:.2f}_{side:+d}", bx, bz + 0.008, side * 0.013, side, k)
        glow_strip(b, f"Shroud_Line_{x0:.2f}_L", x0 + 0.01, x1 - 0.01, bz - 0.002, 0.013, 0.0016, k, 1)
        glow_strip(b, f"Shroud_Line_{x0:.2f}_R", x0 + 0.01, x1 - 0.01, bz - 0.002, -0.013, 0.0016, k, -1)
    # Titanium clamp collars mount the shroud segments to the barrel (rear,
    # between the segments and in front), each drawn up by hex bolts.
    for cx0, cx1 in ((0.186, 0.204), (0.436, 0.474), (0.696, 0.716)):
        col = L.tube(f"Shroud_Clamp_{cx0:.3f}", [(cx0, 0.0125, 0.0125), (cx0 + 0.0015, 0.0150, 0.0150),
                                                  (cx1 - 0.0015, 0.0150, 0.0150), (cx1, 0.0125, 0.0125)],
                     k.ti, sides=8, shape="poly", poly=oct8, max_seg=0.0, chunk=0.0, sharp_angle=30.0)
        L.transform(col, Matrix.Translation((0.0, 0.0, bz)))
        b.add(col)
        lug = chamfer_plate(f"Shroud_Lug_{cx0:.3f}", [(cx0 + 0.002, bz - 0.021), (cx1 - 0.002, bz - 0.021),
                                                     (cx1 - 0.002, bz - 0.012), (cx0 + 0.002, bz - 0.012)],
                            0.018, k.ti, 0.0, 0.0010)
        b.add(lug)
        for side in (-1, 1):
            for bx in ((cx0 + cx1) / 2,) if cx1 - cx0 < 0.03 else (cx0 + 0.009, cx1 - 0.009):
                bolt(b, f"Shroud_Clamp_Bolt_{cx0:.3f}_{bx:.3f}_{side:+d}", bx, bz + 0.002, side * 0.0152, side, k,
                     r=0.0019)
                bolt(b, f"Shroud_Lug_Bolt_{cx0:.3f}_{bx:.3f}_{side:+d}", bx, bz - 0.0165, side * 0.0092, side, k,
                     r=0.0015)
    ring_emitter(b, "Muzzle", xm + 0.004, 0.0145, 0.0072, 0.03, k, bz)
    # Charge lever (in place of the hibasami), trigger and guard.
    lever = [(0.0, 0.0), (0.006, 0.0), (0.004, 0.030), (-0.012, 0.042), (-0.016, 0.038), (-0.002, 0.026)]
    b.add(chamfer_plate("Charge_Lever", [(x + 0.03, z + bz + 0.020) for x, z in lever], 0.004, k.ti, -0.012, 0.0008))
    guard = [(-0.02, -0.018), (0.07, -0.016), (0.06, -0.048), (-0.02, -0.046)]
    hole = L.fillet_poly([(-0.008, -0.024), (0.056, -0.022), (0.05, -0.040), (-0.008, -0.040)], 0.006, 3)
    b.add(L.extrude_outline("Trigger_Guard", [L.fillet_poly(guard, [0.003, 0.004, 0.012, 0.012], 3), hole], 0.006,
                            0.0008, k.graphite, "XZ", 0.0, bevel_res=1))
    b.add(chamfer_plate("Trigger", [(0.020, -0.018), (0.027, -0.018), (0.024, -0.034), (0.018, -0.036)], 0.004, k.ti))
    ledger_sigil(b, "Sigil", -0.20, -0.025, 0.018, -0.0175, k, -1)
    glow_strip(b, "Stock_Line", -0.33, -0.10, 0.004, -0.0175, 0.0018, k, -1)
    cable(b, "Charge_Cable", [(0.17, -0.013, bz - 0.012), (0.22, -0.016, bz - 0.022), (0.30, -0.015, bz - 0.024),
                              (0.36, -0.013, bz - 0.016)], k, 0.0026)
    for side in (-1, 1):
        vent_block(b, f"Stock_Vent_{side:+d}", -0.14, -0.06, -0.010, 0.020, side * 0.0175, side, k, 5)
    b.socket("Grip_R", (0.0, 0.0, 0.0))
    b.socket("Grip_L", (0.30, 0.0, bz - 0.02))
    b.socket("Muzzle", (xm + 0.0046, 0.0, bz))
    b.socket("Charge", (0.085, 0.0, bz + 0.003))
    b.notes.update({"overall_m": round(xm + 0.004 - x_back, 3), "emissive": "Mask R: coil, ledger lines, sigil, muzzle"})


def build_needle_smg(b: L.Build):
    k = Kit("NS")
    bz = 0.030
    body = [(-0.06, bz + 0.030), (0.14, bz + 0.032), (0.24, bz + 0.018), (0.25, bz - 0.012), (0.20, bz - 0.024),
            (0.13, -0.004), (-0.02, -0.006), (-0.06, 0.004)]
    layered(b, "Body", body, 0.034, k.graphite, [(0.007, 0.0022, k.ledger)], radius=0.003, kit=k)
    grip = [(-0.028, -0.004), (0.018, -0.004), (-0.004, -0.105), (-0.046, -0.100)]
    b.add(chamfer_plate("Grip", grip, 0.030, k.graphite, 0.0, 0.0018, [0.002, 0.004, 0.01, 0.01]))
    mag = [(0.060, -0.004), (0.110, -0.004), (0.128, -0.120), (0.082, -0.124)]
    b.add(chamfer_plate("Needle_Magazine", mag, 0.022, k.glass, 0.0, 0.0012, [0.002, 0.002, 0.005, 0.005]))
    for side in (-1, 1):
        win = [(0.075, -0.020), (0.102, -0.020), (0.114, -0.100), (0.088, -0.102)]
        b.add(chamfer_plate(f"Needle_Window_{side:+d}", win, 0.0012, k.glow, side * 0.0112, 0.0002), lod_drop=2)
    for i in range(3):
        a = math.pi / 2 + math.tau * i / 3
        cy, cz = 0.0055 * math.cos(a), bz + 0.004 + 0.0055 * math.sin(a)
        b.add(L.bore_tube(f"Needle_Barrel_{i}", [(0.24, 0.0042, 0.0042), (0.36, 0.0036, 0.0036)], 0.0014, 0.02, k.ti,
                          sides=20, chunk=0.0))
        L.transform(b.groups["main"]["parts"][-1], Matrix.Translation((0, cy, cz)))
    b.add(L.tube("Barrel_Clamp", [(0.30, 0.0115, 0.0115, 0.0, bz + 0.004), (0.302, 0.0125, 0.0125, 0.0, bz + 0.004),
                                  (0.318, 0.0125, 0.0125, 0.0, bz + 0.004), (0.32, 0.0115, 0.0115, 0.0, bz + 0.004)],
                 k.ti, sides=40, max_seg=0.01, chunk=0.0, sharp_angle=35.0))
    # Folding wire stock.
    for zz in (bz + 0.018, -0.006):
        b.add(L.tube(f"Stock_Rod_{zz:.3f}", [(-0.20, 0.0035, 0.0035, 0.0, zz), (-0.06, 0.0035, 0.0035, 0.0, zz)], k.ti,
                     sides=16, max_seg=0.04, chunk=0.0))
    b.add(chamfer_plate("Butt_Pad", [(-0.212, bz + 0.026), (-0.198, bz + 0.026), (-0.198, -0.030), (-0.212, -0.030)],
                        0.030, k.graphite, 0.0, 0.002))
    b.add(chamfer_plate("Trigger", [(0.030, -0.006), (0.037, -0.006), (0.034, -0.022), (0.028, -0.024)], 0.004, k.ti))
    for side in (-1, 1):
        glow_strip(b, f"Body_Line_{side:+d}", 0.0, 0.20, bz + 0.014, side * 0.0172, 0.0016, k, side)
    ledger_sigil(b, "Sigil", 0.03, bz + 0.002, 0.012, -0.0172, k, -1)
    b.add(chamfer_plate("Sight", [(0.08, bz + 0.032), (0.14, bz + 0.033), (0.14, bz + 0.044), (0.09, bz + 0.042)],
                        0.012, k.glass, 0.0, 0.001))
    top_rail(b, "Rail", -0.04, 0.075, bz + 0.031, k, 0.014)
    for side in (-1, 1):
        vent_block(b, f"Vent_{side:+d}", 0.150, 0.228, bz + 0.004, 0.022, side * 0.0172, side, k, 5)
    b.add(L.tube("Muzzle_Shroud", [(0.305, 0.0118, 0.0118, 0.0, bz + 0.004), (0.307, 0.0128, 0.0128, 0.0, bz + 0.004),
                                   (0.352, 0.0122, 0.0122, 0.0, bz + 0.004), (0.355, 0.0110, 0.0110, 0.0, bz + 0.004)],
                 k.graphite, sides=6, shape="poly", poly=L.polygon2d(6, 1.0, 0.06, 1), max_seg=0.01, chunk=0.0,
                 sharp_angle=30.0))
    knob = L.tube("Charging_Knob", [(0.0, 0.0045, 0.0045), (0.012, 0.0045, 0.0045), (0.016, 0.0030, 0.0030)], k.ti,
                  sides=16, max_seg=0.004, chunk=0.0)
    L.transform(knob, Matrix.Translation((0.10, -0.019, bz + 0.016)) @ L.rot("Z", -90))
    b.add(knob)
    trigger_guard(b, "Trigger_Guard", 0.016, 0.066, -0.004, 0.030, k)
    b.socket("Grip_R", (0.0, 0.0, 0.0))
    b.socket("Grip_L", (0.095, 0.0, -0.06))
    b.socket("Muzzle", (0.36, 0.0, bz + 0.004))
    b.notes.update({"overall_m": 0.572, "emissive": "Mask R: needle window, ledger lines, sigil"})


def build_phantom_smg(b: L.Build):
    k = Kit("PS")
    bz = 0.030
    body = [(-0.07, bz + 0.026), (0.02, bz + 0.034), (0.16, bz + 0.030), (0.17, bz - 0.018), (0.10, bz - 0.030),
            (-0.03, -0.006), (-0.07, 0.000)]
    layered(b, "Body", body, 0.036, k.graphite, [(0.006, 0.0018, k.glass)], radius=0.002, kit=k)
    oct8 = L.polygon2d(8, 1.0, 0.04, 1, rot=math.pi / 8)
    sup = L.bore_tube("Suppressor", [(0.16, 0.0230, 0.0230), (0.40, 0.0225, 0.0225), (0.42, 0.0200, 0.0200)], 0.0045,
                      0.03, k.graphite, shape="poly", poly=oct8, chunk=0.2, sharp_angle=30.0)
    L.transform(sup, Matrix.Translation((0, 0, bz)))
    b.add(sup)
    for x0 in (0.20, 0.26, 0.32):
        band = L.tube(f"Sup_Band_{x0:.2f}", [(x0, 0.0238, 0.0238, 0.0, bz), (x0 + 0.012, 0.0238, 0.0238, 0.0, bz)],
                      k.glass, sides=8, max_seg=0.0, chunk=0.0, shape="poly", poly=oct8)
        b.add(band)
    grip = [(-0.032, -0.002), (0.014, -0.002), (-0.006, -0.100), (-0.048, -0.094)]
    b.add(chamfer_plate("Grip", grip, 0.030, k.graphite, 0.0, 0.0018, [0.002, 0.004, 0.01, 0.01]))
    mag = [(0.050, -0.010), (0.095, -0.012), (0.098, -0.105), (0.056, -0.105)]
    b.add(chamfer_plate("Magazine", mag, 0.022, k.ledger, 0.0, 0.0012))
    st = [(-0.07, bz + 0.022), (-0.22, bz + 0.010), (-0.22, -0.060), (-0.19, -0.060), (-0.10, -0.010), (-0.07, 0.0)]
    hole = L.fillet_poly([(-0.18, bz - 0.004), (-0.11, bz), (-0.12, -0.012), (-0.17, -0.040)], 0.008, 3)
    b.add(L.extrude_outline("Stock", [L.fillet_poly(st, [0.0, 0.006, 0.006, 0.01, 0.02, 0.0], 3), hole], 0.030,
                            0.0015, k.graphite, "XZ", 0.0, bevel_res=1, sharp_angle=30.0))
    b.add(chamfer_plate("Trigger", [(0.024, -0.004), (0.031, -0.004), (0.028, -0.020), (0.022, -0.022)], 0.004, k.ti))
    for side in (-1, 1):
        glow_strip(b, f"Body_Line_{side:+d}", -0.05, 0.15, bz + 0.020, side * 0.0198, 0.0012, k, side)
    ledger_sigil(b, "Sigil", -0.15, bz - 0.030, 0.010, -0.0152, k, -1)
    b.add(chamfer_plate("Top_Cover", [(-0.05, bz + 0.026), (0.02, bz + 0.036), (0.15, bz + 0.032), (0.16, bz + 0.024),
                                      (-0.05, bz + 0.020)], 0.026, k.graphite, 0.0, 0.004))
    for side in (-1, 1):
        vent_block(b, f"Vent_{side:+d}", 0.105, 0.155, bz - 0.002, 0.020, side * 0.0198, side, k, 4)
    for j in range(5):
        b.add(L.box(f"Mag_Rib_{j}", (0.0765, 0.0, -0.030 - j * 0.015), (0.046, 0.0235, 0.004), k.graphite, 0.0008),
              lod_drop=2)
    trigger_guard(b, "Trigger_Guard", 0.012, 0.050, -0.002, 0.028, k)
    b.socket("Grip_R", (0.0, 0.0, 0.0))
    b.socket("Grip_L", (0.075, 0.0, -0.06))
    b.socket("Muzzle", (0.42, 0.0, bz))
    b.notes.update({"overall_m": 0.64, "emissive": "Mask R: dim ledger lines and sigil"})


def build_pulse_carbine(b: L.Build):
    k = Kit("PC")
    bz = 0.032
    body = [(-0.08, bz + 0.024), (0.20, bz + 0.024), (0.22, bz + 0.010), (0.22, bz - 0.022), (0.10, -0.012),
            (-0.04, -0.014), (-0.08, -0.004)]
    layered(b, "Receiver", body, 0.038, k.graphite, [(0.007, 0.0022, k.ti)], radius=0.003, kit=k)
    hg = [(0.22, bz + 0.020), (0.46, bz + 0.016), (0.47, bz - 0.016), (0.22, bz - 0.022)]
    layered(b, "Handguard", hg, 0.034, k.ledger, [(0.006, 0.0015, k.graphite)], radius=0.003, kit=k,
            bolts=False)
    for side in (-1, 1):
        for j in range(3):
            glow_strip(b, f"HG_Line_{side:+d}_{j}", 0.24, 0.45, bz + 0.010 - j * 0.010, side * 0.0187, 0.0014, k, side)
    b.add(L.bore_tube("Barrel", [(0.46, 0.0085, 0.0085), (0.53, 0.0085, 0.0085)], 0.004, 0.03, k.ti, sides=32,
                      chunk=0.0))
    L.transform(b.groups["main"]["parts"][-1], Matrix.Translation((0, 0, bz)))
    for j, (x, r) in enumerate(((0.500, 0.020), (0.515, 0.017), (0.530, 0.014))):
        b.add(L.tube(f"Pulse_Ring_{j}", [(x, r - 0.003, r - 0.003, 0.0, bz), (x + 0.002, r, r, 0.0, bz),
                                         (x + 0.006, r, r, 0.0, bz), (x + 0.008, r - 0.003, r - 0.003, 0.0, bz)],
                     k.ti, sides=48, max_seg=0.0, chunk=0.0, sharp_angle=35.0))
    ring_emitter(b, "Muzzle", 0.56, 0.0120, 0.0060, 0.02, k, bz)
    mag = [(0.07, -0.012), (0.13, -0.012), (0.16, -0.10), (0.11, -0.112)]
    b.add(chamfer_plate("Cell_Magazine", mag, 0.024, k.glass, 0.0, 0.0015, [0.002, 0.002, 0.012, 0.012]))
    grip = [(-0.030, -0.012), (0.016, -0.012), (-0.004, -0.108), (-0.048, -0.102)]
    b.add(chamfer_plate("Grip", grip, 0.030, k.graphite, 0.0, 0.0018, [0.002, 0.004, 0.01, 0.01]))
    st = [(-0.08, bz + 0.018), (-0.28, bz + 0.006), (-0.28, -0.074), (-0.24, -0.074), (-0.12, -0.020), (-0.08, -0.004)]
    b.add(chamfer_plate("Stock", st, 0.032, k.graphite, 0.0, 0.0018, [0.0, 0.006, 0.006, 0.012, 0.03, 0.0]))
    b.add(chamfer_plate("Butt_Pad", [(-0.290, bz + 0.006), (-0.280, bz + 0.006), (-0.280, -0.074), (-0.290, -0.074)],
                        0.034, k.ti, 0.0, 0.0015))
    b.add(chamfer_plate("Optic", [(0.02, bz + 0.024), (0.12, bz + 0.024), (0.11, bz + 0.046), (0.03, bz + 0.046)],
                        0.020, k.glass, 0.0, 0.0012))
    b.add(chamfer_plate("Trigger", [(0.024, -0.012), (0.031, -0.012), (0.028, -0.028), (0.022, -0.030)], 0.004, k.ti))
    ledger_sigil(b, "Sigil", 0.05, bz + 0.004, 0.013, -0.0213, k, -1)
    top_rail(b, "Rail", 0.13, 0.44, bz + 0.024, k, 0.016)
    for side in (-1, 1):
        vent_block(b, f"Vent_{side:+d}", 0.155, 0.205, bz - 0.006, 0.020, side * 0.0213, side, k, 4)
    for j in range(4):
        b.add(L.box(f"Cell_Rib_{j}", (0.118 + j * 0.008, 0.0, -0.035 - j * 0.018), (0.052, 0.0255, 0.0035), k.ti,
                    0.0007), lod_drop=2)
    trigger_guard(b, "Trigger_Guard", 0.016, 0.068, -0.012, 0.030, k)
    cable(b, "Pulse_Cable", [(0.20, -0.021, bz - 0.018), (0.30, -0.024, bz - 0.024), (0.40, -0.022, bz - 0.020),
                             (0.47, -0.012, bz - 0.010)], k, 0.0022)
    b.socket("Grip_R", (0.0, 0.0, 0.0))
    b.socket("Grip_L", (0.34, 0.0, bz - 0.022))
    b.socket("Muzzle", (0.5606, 0.0, bz))
    b.notes.update({"overall_m": round(0.5606 + 0.29, 3), "emissive": "Mask R: handguard ledger lines, muzzle, sigil"})


def build_shock_emitter(b: L.Build):
    k = Kit("SE")
    bz = 0.034
    body = [(-0.06, bz + 0.028), (0.10, bz + 0.030), (0.12, bz - 0.022), (-0.02, -0.010), (-0.06, 0.002)]
    layered(b, "Body", body, 0.040, k.graphite, [(0.007, 0.0022, k.ledger)], radius=0.003, kit=k)
    b.add(L.tube("Spine", [(0.10, 0.012, 0.012, 0.0, bz), (0.36, 0.012, 0.012, 0.0, bz)], k.ti, sides=32, max_seg=0.03,
                 chunk=0.2))
    for j, x in enumerate((0.13, 0.19, 0.25)):
        b.add(L.tube(f"Capacitor_{j}", [(x, 0.016, 0.016, 0.0, bz), (x + 0.004, 0.030, 0.030, 0.0, bz),
                                        (x + 0.036, 0.030, 0.030, 0.0, bz), (x + 0.040, 0.016, 0.016, 0.0, bz)],
                     k.glass, sides=48, max_seg=0.01, chunk=0.0, sharp_angle=35.0))
        b.add(L.tube(f"Capacitor_Gap_{j}", [(x + 0.040, 0.0205, 0.0205, 0.0, bz), (x + 0.050, 0.0205, 0.0205, 0.0, bz)],
                     k.glow, sides=48, max_seg=0.0, chunk=0.0))
    b.add(L.tube("Head_Collar", [(0.33, 0.020, 0.020, 0.0, bz), (0.34, 0.024, 0.024, 0.0, bz), (0.37, 0.022, 0.022, 0.0, bz)],
                 k.ti, sides=48, max_seg=0.01, chunk=0.0, sharp_angle=35.0))
    for side in (-1, 1):
        prong = [(0.37, 0.0), (0.50, 0.008), (0.52, 0.004), (0.515, -0.002), (0.37, -0.008)]
        pr = chamfer_plate(f"Electrode_{side:+d}", prong, 0.008, k.ti, 0.0, 0.0012)
        L.transform(pr, Matrix.Translation((0, 0, bz + side * 0.014)))
        b.add(pr)
        tip = L.tube(f"Electrode_Tip_{side:+d}", [(0.505, 0.003, 0.003), (0.52, 0.0035, 0.0035), (0.524, 0.002, 0.002)],
                     k.glow, sides=16, max_seg=0.004, chunk=0.0)
        L.transform(tip, Matrix.Translation((0, 0, bz + side * 0.015)))
        b.add(tip)
    grip = [(-0.030, -0.008), (0.016, -0.008), (-0.004, -0.106), (-0.048, -0.100)]
    b.add(chamfer_plate("Grip", grip, 0.030, k.graphite, 0.0, 0.0018, [0.002, 0.004, 0.01, 0.01]))
    fg = [(0.16, bz - 0.030), (0.20, bz - 0.030), (0.19, bz - 0.100), (0.16, bz - 0.100)]
    b.add(chamfer_plate("Foregrip", fg, 0.028, k.graphite, 0.0, 0.0018, [0.004, 0.004, 0.01, 0.01]))
    st = [(-0.06, bz + 0.020), (-0.20, bz + 0.010), (-0.20, -0.060), (-0.16, -0.060), (-0.09, -0.010), (-0.06, 0.0)]
    b.add(chamfer_plate("Stock", st, 0.032, k.graphite, 0.0, 0.0018, [0.0, 0.006, 0.006, 0.012, 0.02, 0.0]))
    b.add(chamfer_plate("Trigger", [(0.024, -0.008), (0.031, -0.008), (0.028, -0.024), (0.022, -0.026)], 0.004, k.ti))
    for side in (-1, 1):
        glow_strip(b, f"Body_Line_{side:+d}", -0.04, 0.09, bz + 0.018, side * 0.0222, 0.0016, k, side)
    ledger_sigil(b, "Sigil", 0.03, bz - 0.002, 0.013, -0.0222, k, -1)
    for j in range(4):
        a = math.pi / 4 + math.tau * j / 4
        cy, cz = 0.033 * math.cos(a), bz + 0.033 * math.sin(a)
        b.add(L.box(f"Cage_Bar_{j}", (0.225, cy, cz), (0.24, 0.0042, 0.0042), k.ti, 0.0009))
    for x in (0.105, 0.345):
        b.add(L.tube(f"Cage_Ring_{x:.2f}", [(x - 0.004, 0.033, 0.033, 0.0, bz), (x + 0.004, 0.036, 0.036, 0.0, bz)],
                     k.ti, sides=8, shape="poly", poly=L.polygon2d(8, 1.0, 0.05, 1, rot=math.pi / 8), max_seg=0.0,
                     chunk=0.0, sharp_angle=30.0))
    for side in (-1, 1):
        cable(b, f"Feed_Cable_{side:+d}", [(0.07, side * 0.018, bz + 0.020), (0.10, side * 0.030, bz + 0.036),
                                           (0.16, side * 0.030, bz + 0.040), (0.21, side * 0.022, bz + 0.032)], k, 0.0022)
    top_rail(b, "Rail", -0.04, 0.08, bz + 0.031, k, 0.016)
    trigger_guard(b, "Trigger_Guard", 0.016, 0.066, -0.008, 0.030, k)
    b.socket("Grip_R", (0.0, 0.0, 0.0))
    b.socket("Grip_L", (0.18, 0.0, bz - 0.065))
    b.socket("Muzzle", (0.524, 0.0, bz))
    b.notes.update({"overall_m": 0.724, "emissive": "Mask R: capacitor gaps, electrode tips, ledger lines, sigil"})


BUILDERS = {14: build_plasma_matchlock, 3: build_needle_smg, 13: build_phantom_smg, 11: build_pulse_carbine,
            16: build_shock_emitter}

if __name__ == "__main__":
    L.run({wid: BUILDERS[wid] for wid in S.by_builder("create_runtime_weapon_alien.py", include_held=True)})
