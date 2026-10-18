"""Build the League firearms: coil matchlock (5), repeater (9), arc carbine
(1), grenade launcher (7) and micro-mortar (15).

Run:  blender -b --factory-startup --python scripts/art/create_runtime_weapon_firearms.py [-- --only 5]

All five speak the League's Japanese gunsmithing language (story bible 4.4,
15.1): a carved dai stock with a slim cheek butt (daijiri) whose underline
curves down from the wrist, the barrel pinned through the forestock with
mekugi, a brass karakuri lock on the right (-Y) side with its springs and
slotted screws, a brass trigger without a guard, and brass or bronze under
their own patina. The coil matchlock follows the tanegashima of Met 22492
(103.8 cm overall, 73 cm barrel, 16 mm bore) with an alien coil-ignition
sleeve grafted over the breech and a soft hinawa wound round the wrist;
it carries no SORA mon. The repeater, arc carbine, hand-mortar and
micro-mortar are fictional League weapons (timber, urushi, bronze, iron,
rattan, rice straw; SORA mon on the repeater, carbine and mortar; League
glows are warm, never cyan):

* repeater: a bronze karakuri box cast in two halves (a seam between body
  and cover, engraved border, slotted screws) on a dai stock with a brass
  butt cap, a ribbed bronze side drum with a riveted hub and loading gate,
  a hibasami-shaped hammer and an advance crank;
* arc carbine: a short negoro stock (shu urushi worn through to its black
  undercoat) with brass cheek plates carrying the SORA mon, a pinned iron
  barrel through copper coil stages in an open bronze cage, and a lower
  beam held to the barrel by bronze collars;
* grenade launcher: Tamakichi's 手筒 hand-mortar, a madake culm with a
  node and a cut, thick-walled muzzle, bound in hairy two-ply rice-straw
  nawa laid by hand (pitch and thickness wander, loose fibres, frayed
  ends), closed by a lathe-turned oak plug handle lashed and pinned into
  its base;
* micro-mortar: a cast bronze mortar under a brown-green patina (casting
  flash, pits, the cast SORA mon) bedded in a carved oak cradle and held by
  iron capsquare straps that wrap the barrel and are nailed to the bed.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import create_runtime_weapon_lib as L  # noqa: E402
import create_runtime_weapon_specs as S  # noqa: E402

BRASS = (0.80, 0.60, 0.30)            # handled brass under a thin oxide film (F0)
BRASS_WORN = (0.93, 0.76, 0.44)       # rubbed bright on the arrises
BRASS_OXIDE = (0.15, 0.10, 0.045)
BRONZE_AGED = (0.27, 0.185, 0.10)     # cast bronze under its own brown oxide (F0)
BRONZE_PATINA = (0.040, 0.060, 0.036)
BRONZE_OXIDE = (0.10, 0.07, 0.04)
COPPER = (0.93, 0.62, 0.50)
GOLD = (0.95, 0.66, 0.26)
NEGORO_SHU = L.srgb(146, 40, 24)      # negoro red coat over black (darker than #A8321E)
OCT = L.polygon2d(8, 1.0, 0.07, 2, rot=math.pi / 8)
ARC_GLOW = (1.0, 0.86, 0.70)          # warm white arc (League glows are warm)


def hash01(*k):
    """Deterministic pseudo-random value in [0, 1) from integers (no seeds)."""
    h = 0
    for v in k:
        h = (h * 1000003) ^ (int(v) & 0xFFFFFFFF)
        h = ((h ^ (h >> 13)) * 0x5BD1E995) & 0xFFFFFFFF
    h ^= h >> 15
    return (h & 0xFFFFFF) / float(0x1000000)


def jit(*k):
    return hash01(*k) * 2.0 - 1.0


def smooth01(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------------------
# Shared parts
# ---------------------------------------------------------------------------

def pchip(xs, ys):
    """Monotone cubic (Fritsch-Carlson) interpolant: smooth, no overshoot."""
    n = len(xs)
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    d = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    m[0], m[-1] = d[0], d[-1]
    for i in range(1, n - 1):
        if d[i - 1] * d[i] <= 0:
            m[i] = 0.0
        else:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])

    def f(x):
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        i = max(k for k in range(n - 1) if xs[k] <= x)
        t = (x - xs[i]) / h[i]
        t2, t3 = t * t, t * t * t
        return ((2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h[i] * m[i] + (-2 * t3 + 3 * t2) * ys[i + 1]
                + (t3 - t2) * h[i] * m[i + 1])
    return f


class Stock:
    """A carved dai stock from stations (x, z_top, z_bottom, half_width),
    butt first; sections are rounded rectangles (superellipses)."""

    def __init__(self, stations, power=3.4):
        xs = [s[0] for s in stations]
        self.x0, self.x1 = xs[0], xs[-1]
        self.top = pchip(xs, [s[1] for s in stations])
        self.bot = pchip(xs, [s[2] for s in stations])
        self.hw = pchip(xs, [s[3] for s in stations])
        self.power = power

    def section(self, x):
        return self.top(x), self.bot(x), self.hw(x)

    def mesh(self, name, mat, sides=44, step=0.008, end_round=0.004, x0=None, x1=None, grow=0.0):
        x0 = self.x0 if x0 is None else x0
        x1 = self.x1 if x1 is None else x1
        xs = [x0, x0 + end_round * 0.35, x0 + end_round]
        n = max(2, int((x1 - x0 - 2 * end_round) / step))
        xs += [x0 + end_round + (x1 - x0 - 2 * end_round) * k / n for k in range(1, n)]
        xs += [x1 - end_round, x1 - end_round * 0.35, x1]
        rings = []
        for x in xs:
            top, bot, hw = self.section(x)
            e = min(x - x0, x1 - x) / end_round if end_round else 1.0
            sc = 0.93 + 0.07 * smooth01(e)
            cz, rz = (top + bot) / 2, (top - bot) / 2
            rings.append(L.ring_superellipse((hw + grow) * sc, (rz + grow) * sc, sides, self.power, 0.0, cz, x))
        return L.loft(name, rings, mat, closed=True, cap_start=True, cap_end=True, chunk=0.25, sharp_angle=55.0)


def plate(name, outline, thickness, mat, y=0.0, bevel=0.0008, radius=0.0, seg=4, plane="XZ"):
    pts = L.fillet_poly(outline, radius, seg) if radius else outline
    return L.extrude_outline(name, [pts], thickness, bevel, mat, plane, y)


def plate_holes(name, outline, holes, thickness, mat, y=0.0, bevel=0.0008, radius=0.0, seg=4):
    pts = L.fillet_poly(outline, radius, seg) if radius else outline
    return L.extrude_outline(name, [pts] + holes, thickness, bevel, mat, "XZ", y)


def oct_barrel(name, secs, mat, bore_r, bore_depth=0.07):
    """secs: (x, across_flats) along +X; octagonal barrel with a real bore
    (bore_r 0 gives a solid capped octagonal sleeve or band)."""
    s2 = [(x, f / 2, f / 2) for x, f in secs]
    if bore_r <= 0:
        return L.tube(name, s2, mat, shape="poly", poly=OCT, max_seg=0.02, chunk=0.25, sharp_angle=40.0)
    return L.bore_tube(name, s2, bore_r, bore_depth, mat, shape="poly", poly=OCT, chunk=0.25, sharp_angle=40.0)


def round_barrel(name, secs, mat, bore_r, bore_depth=0.07, sides=40):
    s2 = [(x, r, r) for x, r in secs]
    return L.bore_tube(name, s2, bore_r, bore_depth, mat, sides=sides, chunk=0.25, sharp_angle=40.0)


def shift(obj, z=0.0, y=0.0, x=0.0):
    return L.transform(obj, Matrix.Translation((x, y, z)))


def orient_to(normal):
    """Rotation taking +X to ``normal``."""
    return Vector((1.0, 0.0, 0.0)).rotation_difference(Vector(normal).normalized()).to_matrix().to_4x4()


def screw(name, pos, normal, r, mat, slot_deg=0.0):
    """A domed, slotted screw head (axis along ``normal``)."""
    head = L.tube(name, [(-0.0004, r * 0.96, r * 0.96), (0.0, r, r), (r * 0.18, r * 0.98, r * 0.98),
                         (r * 0.36, r * 0.82, r * 0.82), (r * 0.48, r * 0.50, r * 0.50)], mat, sides=18, max_seg=0.0,
                  chunk=0.0, sharp_angle=50.0, tip_end=(r * 0.52, 0.0, 0.0))
    slot = L.box(name + "_slot", (r * 0.5, 0.0, 0.0), (r * 0.62, r * 2.6, r * 0.30), None, 0.0)
    L.transform(slot, L.rot("X", slot_deg))
    L.boolean(head, slot)
    L.transform(head, Matrix.Translation(pos) @ orient_to(normal))
    return head


def ellipse_wrap(name, x0, x1, cy, cz, ry, rz, pitch, wire, mat, sides=6, spt=32):
    turns = (x1 - x0) / pitch
    n = max(int(turns * spt), 8)
    path = []
    for i in range(n + 1):
        t = i / n
        a = math.tau * turns * t
        path.append(Vector((x0 + (x1 - x0) * t, cy + ry * math.cos(a), cz + rz * math.sin(a))))
    return L.sweep(name, path, L.circle2d(wire / 2, sides), mat, up=(1, 0, 0), chunk=0.15, sharp_angle=None)


def mon_on_side(name, x, z, diameter, mat, side=-1, y_face=0.0, thick=0.0006, wrap_r=None):
    """SORA mon inlay on a side face; readable (not mirrored) from that side.
    With ``wrap_r`` the mon is bent onto a cylinder of that radius about an
    X axis through (y = 0, z) (cast relief on a round barrel)."""
    mon = L.sora_mon(name, diameter, thick, mat, 0.0001)
    if wrap_r is not None:
        radius = wrap_r if callable(wrap_r) else (lambda _x: wrap_r)
        for v in mon.data.vertices:
            lx, ly, lz = v.co  # local x along X, local y up, local z outward
            wx = x + (lx if side < 0 else -lx)
            base = radius(wx)
            ang = ly / base
            r = base + lz + thick * 0.35
            v.co = Vector((wx, side * r * math.cos(ang), z + r * math.sin(ang)))
        mon.data.update()
        return mon
    if side < 0:  # face toward -Y: local x -> +X, local y -> +Z, local z -> -Y
        M = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
    else:         # face toward +Y: local x -> -X, local y -> +Z, local z -> +Y
        M = Matrix(((-1, 0, 0, 0), (0, 0, 1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
    L.transform(mon, Matrix.Translation((x, y_face + side * thick * 0.3, z)) @ M)
    return mon


def catmull(points, samples_per_seg=10):
    pts = [Vector(p) for p in points]
    out = []
    for i in range(len(pts) - 1):
        p0 = pts[max(i - 1, 0)]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[min(i + 2, len(pts) - 1)]
        for k in range(samples_per_seg):
            t = k / samples_per_seg
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 +
                              (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(pts[-1])
    return out


def mekugi_pins(b, stock, xs, z_of, brass, iron, prefix="Mekugi"):
    """Barrel pins through the forestock: brass escutcheon washers and the
    iron pin ends flush in them, on both sides."""
    for px in xs:
        hw = stock.hw(px)
        for side in (-1, 1):
            esc = L.tube(f"{prefix}_Esc_{px:.2f}_{side:+d}", [(-0.0005, 0.0038, 0.0038), (0.0, 0.0040, 0.0040),
                                                               (0.0005, 0.0036, 0.0036)], brass, sides=20,
                         max_seg=0.0, chunk=0.0)
            L.transform(esc, Matrix.Translation((px, side * (hw + 0.0002), z_of(px))) @ L.rot("Z", 90 * side))
            b.add(esc, lod_drop=2)
            pin = L.tube(f"{prefix}_Pin_{px:.2f}_{side:+d}", [(0.0, 0.0017, 0.0017), (0.0008, 0.0016, 0.0016)], iron,
                         sides=12, max_seg=0.0, chunk=0.0)
            L.transform(pin, Matrix.Translation((px, side * (hw + 0.0005), z_of(px))) @ L.rot("Z", 90 * side))
            b.add(pin, lod_drop=2)


def butt_cap(b, stock, mat, thick=0.0035, name="Butt_Cap"):
    """A metal cap conforming to the butt end."""
    x0 = stock.x0
    rings = []
    for dx, sc in ((-thick, 0.95), (-thick + 0.0008, 1.01), (-0.0006, 1.015), (0.0012, 1.012)):
        top, bot, hw = stock.section(x0 + max(dx, 0.0))
        cz, rz = (top + bot) / 2, (top - bot) / 2
        rings.append(L.ring_superellipse(hw * sc, rz * sc, 44, stock.power, 0.0, cz, x0 + dx))
    b.add(L.loft(name, rings, mat, closed=True, cap_start=True, cap_end=True, chunk=0.0, sharp_angle=50.0))


# ---------------------------------------------------------------------------
# Coil matchlock (tanegashima pattern)
# ---------------------------------------------------------------------------

ML_STATIONS = [(-0.263, 0.0140, -0.0505, 0.0170), (-0.250, 0.0145, -0.0500, 0.0172), (-0.215, 0.0155, -0.0470, 0.0172),
               (-0.165, 0.0175, -0.0390, 0.0168), (-0.110, 0.0200, -0.0280, 0.0162), (-0.062, 0.0230, -0.0195, 0.0156),
               (-0.020, 0.0270, -0.0145, 0.0160), (0.030, 0.0320, -0.0085, 0.0170), (0.080, 0.0325, -0.0030, 0.0168),
               (0.150, 0.0322, 0.0010, 0.0160), (0.300, 0.0318, 0.0040, 0.0150), (0.450, 0.0316, 0.0060, 0.0142),
               (0.600, 0.0314, 0.0080, 0.0133), (0.736, 0.0312, 0.0100, 0.0125)]


def build_coil_matchlock(b: L.Build):
    bz = 0.030
    xb0, xm = 0.045, 0.775
    iron = L.mat_iron("M_ML_Barrel", oxide=(0.020, 0.018, 0.017), rust=0.15, polish_edges=0.35, rough=0.42,
                      metal=0.55, forge_scale=0.3)
    stock_m = L.mat_wood("M_ML_Stock", tone="stock", value=1.0, rough=(0.30, 0.55), mapping="uv", lacquer=0.65,
                         wear=0.45, dirt=0.45, rays=0.6, grips=((-0.11, 0.02), (0.22, 0.40)))
    brass = L.mat_alloy("M_ML_Brass", BRASS, 0.30, (0.10, 0.08, 0.035), 0.5, "cast", wear_color=BRASS_WORN,
                        oxide=BRASS_OXIDE, oxide_amount=0.6)
    copper = L.mat_alloy("M_ML_CoilCopper", COPPER, 0.3, (0.06, 0.09, 0.06), 0.35, "brushed_x",
                         oxide=(0.16, 0.075, 0.045), oxide_amount=0.35)
    graphite = L.mat_graphite("M_ML_AlienSleeve", engrave=1.2)
    clamp = L.mat_iron("M_ML_Clamp", oxide=(0.04, 0.034, 0.028), rust=0.35, polish_edges=0.3, tsuchime=0.8)
    rope = L.mat_rope("M_ML_Hemp", "Rope001", tint=(0.62, 0.50, 0.33), tile=0.02, value=0.75)
    match = L.mat_rope("M_ML_Hinawa", "Rope002", tint=(0.35, 0.25, 0.16), tile=0.015, value=0.6, sat=0.7)
    ember = L.mat_emissive("M_ML_Ember", (0.12, 0.03, 0.01), glow=(1.0, 0.32, 0.05), strength=6.0, rough=0.8)
    horn = L.mat_horn("M_ML_Horn")
    st = Stock(ML_STATIONS, power=3.6)
    # Barrel: 73 cm octagonal, swelled muzzle, 16 mm bore.
    secs = [(xb0, 0.0270), (0.20, 0.0255), (0.45, 0.0232), (0.64, 0.0216), (0.735, 0.0212), (0.752, 0.0236),
            (0.766, 0.0256), (0.772, 0.0254), (xm, 0.0246)]
    barrel = oct_barrel("Barrel", secs, iron, 0.008, 0.09)
    shift(barrel, z=bz)
    b.add(barrel)
    # Bisen: the breech plug's tang, let flush into the top of the wrist.
    tang = [(-0.022, 0.0), (0.046, 0.0), (0.046, 0.0034), (0.030, 0.0042), (-0.012, 0.0036), (-0.024, 0.0020)]
    tz = st.top(0.0) - 0.0024
    b.add(plate("Bisen_Tang", [(x, z + tz) for x, z in tang], 0.0100, iron, 0.0, 0.0009, 0.002, 3), lod_drop=99)
    b.add(screw("Bisen_Screw", (-0.012, 0.0, tz + 0.0036), (0, 0, 1), 0.0026, iron, 20.0), lod_drop=2)
    # Dai: a slim cheek stock whose underline curves down from the wrist.
    b.add(st.mesh("Stock", stock_m))
    b.add(L.tube("Stock_Nose", [(0.733, st.hw(0.733) - 0.0004, (st.top(0.733) - st.bot(0.733)) / 2 - 0.0004, 0.0,
                                 (st.top(0.733) + st.bot(0.733)) / 2),
                                (0.742, st.hw(0.733) * 0.97, (st.top(0.733) - st.bot(0.733)) / 2 * 0.97, 0.0,
                                 (st.top(0.733) + st.bot(0.733)) / 2)],
                 horn, sides=40, shape="super", power=3.6, max_seg=0.0, chunk=0.0))
    # Karuka (ramrod) half-sunk along the underside, horn tip.
    kx = [0.12 + (0.735 - 0.12) * k / 30 for k in range(31)]
    b.add(L.tube("Karuka", [(x, 0.0040, 0.0040, 0.0, st.bot(x) + 0.0024) for x in kx], stock_m, sides=16,
                 max_seg=0.0, chunk=0.25))
    b.add(L.tube("Karuka_Tip", [(0.742, 0.0040, 0.0040, 0.0, st.bot(0.735) + 0.0024),
                                (0.748, 0.0044, 0.0044, 0.0, st.bot(0.735) + 0.0024),
                                (0.756, 0.0036, 0.0036, 0.0, st.bot(0.735) + 0.0024)], horn, sides=16, max_seg=0.004,
                 chunk=0.0))
    # Karakuri on the right (-Y): brass jiita, external mainspring, hibasami
    # pivoted behind the pan (shown cocked back; it snaps forward into the pan).
    y_pl = -(st.hw(0.03) + 0.0004)
    lp = [(-0.038, 0.006), (0.0, 0.017), (0.105, 0.019), (0.112, 0.004), (0.10, -0.007), (-0.02, -0.006)]
    b.add(plate("Jiita", lp, 0.0020, brass, y_pl, 0.0004, [0.004, 0.006, 0.004, 0.004, 0.004, 0.006], 4))
    y_out = y_pl - 0.0010
    spring = [Vector((0.090, y_out - 0.0006, -0.002)), Vector((0.075, y_out - 0.0006, 0.002)),
              Vector((0.058, y_out - 0.0006, 0.004)), Vector((0.042, y_out - 0.0006, 0.005))]
    b.add(L.sweep("Hajiki_Spring", catmull(spring, 6), [(-0.0006, -0.0015), (0.0006, -0.0015), (0.0006, 0.0015),
                                                        (-0.0006, 0.0015)], brass, up=(0, 1, 0), chunk=0.0,
                  sharp_angle=40.0), lod_drop=2)
    for sx, sz in ((-0.012, 0.004), (0.094, 0.010), (0.060, -0.002)):
        b.add(screw(f"Jiita_Screw_{sx:.3f}", (sx, y_out, sz), (0, -1, 0), 0.0021, brass, 35.0 * jit(int(sx * 1000))),
              lod_drop=2)
    piv = Vector((0.030, y_out - 0.0010, 0.010))
    arm = [piv, piv + Vector((-0.002, -0.001, 0.012)), piv + Vector((-0.008, -0.002, 0.024)),
           piv + Vector((-0.016, -0.003, 0.033)), piv + Vector((-0.021, -0.003, 0.036))]
    b.add(L.sweep("Hibasami", catmull(arm, 8), [(-0.0016, -0.0019), (0.0016, -0.0019), (0.0016, 0.0019),
                                                 (-0.0016, 0.0019)], brass, up=(0, 1, 0), chunk=0.0, sharp_angle=40.0))
    b.add(screw("Hibasami_Pivot", (piv.x, piv.y - 0.0019, piv.z), (0, -1, 0), 0.0036, brass, 60.0))
    head = arm[-1]
    b.add(L.box("Hibasami_Jaw", (head.x - 0.002, head.y, head.z + 0.001), (0.010, 0.006, 0.006), brass, 0.0012))
    # Hizara (pan) on the right of the breech, hibuta (cover) swung open forward.
    pan = L.box("Hizara", (0.062, -0.0150, bz + 0.002), (0.018, 0.010, 0.006), brass, 0.0012)
    dish = L.box("pan_cut", (0.062, -0.0167, bz + 0.0052), (0.012, 0.0055, 0.004), None, 0.0)
    L.boolean(pan, dish)
    b.add(pan)
    cover = plate("Hibuta", [(0.0, 0.0), (0.017, 0.0), (0.017, 0.0012), (0.0, 0.0012)], 0.010, brass, 0.0, 0.0003)
    L.transform(cover, Matrix.Translation((0.071, -0.0150, bz + 0.005)) @ L.rot("Y", -70))
    b.add(cover)
    # Trigger (hikigane): brass, no guard (period).
    trig = [(0.018, -0.004), (0.026, -0.004), (0.026, -0.016), (0.022, -0.028), (0.014, -0.034), (0.012, -0.031),
            (0.017, -0.022), (0.018, -0.014)]
    b.add(plate("Hikigane", trig, 0.0042, brass, 0.0, 0.0008, 0.0015, 3))
    # Hinawa: the burning end clamped in the jaw over the pan; the soft cord
    # trails back, is wound round the wrist and hangs in a loose loop.
    tip = head + Vector((0.012, 0.0, -0.006))
    ctrl = [tip, head + Vector((0.004, 0.0, 0.0)), head + Vector((-0.012, -0.001, 0.003)),
            Vector((-0.004, -0.024, 0.036)), Vector((-0.016, -0.026, 0.028))]
    wx0, wx1 = -0.022, -0.050
    for i in range(1, 37):
        f = i / 36
        a = -math.pi / 2 + math.tau * 1.35 * f
        x = wx0 + (wx1 - wx0) * f
        top, bot, hw = st.section(x)
        cz, rz = (top + bot) / 2, (top - bot) / 2
        ctrl.append(Vector((x, (hw + 0.0035) * math.cos(a) * -1.0, cz + (rz + 0.0035) * math.sin(a))))
    last = ctrl[-1]
    ctrl += [last + Vector((-0.012, -0.004, -0.030)), last + Vector((-0.020, -0.010, -0.070)),
             last + Vector((-0.040, -0.016, -0.090)), last + Vector((-0.062, -0.012, -0.070)),
             last + Vector((-0.070, -0.006, -0.040)), last + Vector((-0.074, -0.004, -0.018)),
             last + Vector((-0.080, -0.006, -0.045)), last + Vector((-0.086, -0.008, -0.078))]
    path = catmull(ctrl, 6)
    b.add(L.sweep("Hinawa", path, L.circle2d(0.0027, 8), match, up=(0, 1, 0), chunk=0.15, sharp_angle=None,
                  twist=lambda u: 40.0 * u))
    tipc = tip + (tip - ctrl[1]).normalized() * 0.0035
    b.add(L.sweep("Hinawa_Ember", [tip, tip.lerp(tipc, 0.5), tipc],
                  [(0.0027 * math.cos(math.tau * k / 8), 0.0027 * math.sin(math.tau * k / 8)) for k in range(8)],
                  ember, up=(0, 1, 0), chunk=0.0, sharp_angle=None, tip_end=tipc + (tipc - tip).normalized() * 0.0015,
                  cap_end=False, cap_start=False))
    # Sights and barrel pins.
    b.add(L.box("Motomeate", (0.205, 0.0, bz + 0.0145), (0.018, 0.009, 0.006), iron, 0.0012))
    notch = L.box("notch", (0.205, 0.0, bz + 0.0175), (0.02, 0.0022, 0.004), None, 0.0)
    L.boolean(b.groups["main"]["parts"][-1], notch)
    b.add(plate("Sakimeate", [(0.748, bz + 0.010), (0.758, bz + 0.010), (0.756, bz + 0.0165), (0.751, bz + 0.0165)],
                0.0018, iron, 0.0, 0.0004))
    mekugi_pins(b, st, (0.30, 0.48, 0.66), lambda x: bz - 0.010, brass, iron, "Mekugi")
    # Alien coil-ignition sleeve over the breech (the village graft).
    sleeve = oct_barrel("Coil_Sleeve", [(0.078, 0.0312), (0.150, 0.0300)], graphite, 0.0, 0.0)
    shift(sleeve, z=bz)
    b.add(sleeve)
    b.add(L.helix("Coil_Winding", 0.084, 0.144, 0.0162, 0.0024, 0.0017, copper, 0.0, bz, 28, 6))
    for x0 in (0.074, 0.146):
        band = oct_barrel(f"Coil_Clamp_{x0:.3f}", [(x0, 0.0345), (x0 + 0.008, 0.0345)], clamp, 0.0, 0.0)
        shift(band, z=bz)
        b.add(band)
        for side in (-1, 1):
            b.add(screw(f"Clamp_Rivet_{x0:.3f}_{side:+d}", (x0 + 0.004, side * 0.0172, bz), (0, side, 0), 0.0017,
                        clamp, 0.0), lod_drop=2)
    # Lead from the coil to a graphite cell lashed on the left of the wrist.
    hw_c = st.hw(-0.06)
    lead = [Vector((0.146, 0.0165, bz + 0.004)), Vector((0.12, 0.020, bz - 0.004)), Vector((0.06, 0.0195, 0.012)),
            Vector((0.0, hw_c + 0.003, 0.006)), Vector((-0.035, hw_c + 0.005, 0.004))]
    b.add(L.sweep("Coil_Lead", catmull(lead, 10), L.circle2d(0.0011, 6), copper, up=(0, 0, 1), chunk=0.0,
                  sharp_angle=None))
    b.add(L.box("Alien_Cell", (-0.06, hw_c + 0.0052, 0.0), (0.050, 0.010, 0.024), graphite, 0.002))
    top, bot, _ = st.section(-0.06)
    for x0 in (-0.045, -0.075):
        b.add(ellipse_wrap(f"Cell_Lashing_{x0:.3f}", x0 - 0.004, x0 + 0.004, 0.005, (top + bot) / 2,
                           hw_c + 0.0070, (top - bot) / 2 + 0.0022, 0.0021, 0.0019, rope, 6, 24))
    b.socket("Grip_R", (0.0, 0.0, 0.0))
    b.socket("Grip_L", (0.30, 0.0, st.bot(0.30)))
    b.socket("Muzzle", (xm, 0.0, bz))
    b.socket("Pan", (0.062, -0.0167, bz + 0.005))
    b.socket("MatchTip", tuple(tipc))
    b.notes.update({"overall_m": round(xm - st.x0, 4), "barrel_m": xm - xb0, "bore_m": 0.016,
                    "reference": "Met 22492 (plan 3.8)", "coil_breech": "fictional alien graft (story bible 4.4)",
                    "stock": "slim cheek daijiri, 6.4 cm deep at the butt, curved underline; shunkei lacquer",
                    "lock": "brass karakuri on the right (-Y); hibasami pivoted behind the pan, cocked"})


# ---------------------------------------------------------------------------
# Repeater (League foundry)
# ---------------------------------------------------------------------------

REP_STATIONS = [(-0.340, 0.0180, -0.0500, 0.0180), (-0.300, 0.0190, -0.0480, 0.0180), (-0.220, 0.0220, -0.0400, 0.0176),
                (-0.140, 0.0250, -0.0300, 0.0170), (-0.080, 0.0270, -0.0215, 0.0165), (-0.040, 0.0268, -0.0185, 0.0172),
                (0.000, 0.0232, -0.0180, 0.0178), (0.060, 0.0232, -0.0160, 0.0178), (0.105, 0.0240, -0.0100, 0.0172),
                (0.130, 0.0360, -0.0060, 0.0162), (0.300, 0.0355, 0.0000, 0.0150), (0.500, 0.0352, 0.0040, 0.0140),
                (0.700, 0.0350, 0.0080, 0.0130), (0.712, 0.0350, 0.0085, 0.0128)]


def build_repeater(b: L.Build):
    bz = 0.034
    xm = 0.78
    iron = L.mat_iron("M_Rep_Barrel", oxide=(0.022, 0.020, 0.018), rust=0.12, polish_edges=0.35, rough=0.42,
                      metal=0.55, forge_scale=0.3)
    bronze = L.mat_alloy("M_Rep_Bronze", BRONZE_AGED, 0.40, BRONZE_PATINA, 0.55, "cast", oxide=BRONZE_OXIDE,
                         oxide_amount=0.45, wear_color=(0.72, 0.52, 0.30))
    brass = L.mat_alloy("M_Rep_Brass", BRASS, 0.30, (0.10, 0.08, 0.035), 0.5, "cast", wear_color=BRASS_WORN,
                        oxide=BRASS_OXIDE, oxide_amount=0.6)
    gold = L.mat_alloy("M_Rep_MonGold", GOLD, 0.24, (0.2, 0.1, 0.03), 0.3)
    stock_m = L.mat_wood("M_Rep_Stock", tone="cherry", value=0.95, rough=(0.30, 0.55), mapping="uv", lacquer=0.6,
                         wear=0.4, dirt=0.45, rays=0.5, grips=((-0.13, -0.02), (0.22, 0.42)))
    knob = L.mat_wood("M_Rep_Knob", tone="kashi_red", value=0.8, mapping="box", axis="Z", lacquer=0.5, wear=0.6)
    st = Stock(REP_STATIONS, power=3.6)
    b.add(st.mesh("Stock", stock_m))
    butt_cap(b, st, brass)
    barrel = oct_barrel("Barrel", [(0.08, 0.0240), (0.40, 0.0222), (0.74, 0.0205), (xm, 0.0205)], iron, 0.00625, 0.08)
    shift(barrel, z=bz)
    b.add(barrel)
    b.add(round_barrel("Muzzle_Ring", [(xm - 0.018, 0.0128), (xm - 0.016, 0.0138), (xm - 0.001, 0.0138),
                                       (xm + 0.0015, 0.0130)], bronze, 0.0068, 0.004))
    shift(b.groups["main"]["parts"][-1], z=bz)
    # Karakuri box: body and cover cast separately (a seam between them).
    body = [(-0.036, bz + 0.004), (0.118, bz + 0.004), (0.118, bz - 0.012), (0.104, bz - 0.017), (-0.036, bz - 0.017)]
    cover = [(-0.036, bz + 0.0046), (0.118, bz + 0.0046), (0.112, bz + 0.016), (0.090, bz + 0.019),
             (-0.020, bz + 0.019), (-0.036, bz + 0.013)]
    b.add(plate("Receiver_Body", body, 0.036, bronze, 0.0, 0.0018, [0.003, 0.003, 0.004, 0.006, 0.004], 4))
    b.add(plate("Receiver_Cover", cover, 0.033, bronze, 0.0, 0.0018, [0.003, 0.003, 0.006, 0.01, 0.01, 0.006], 4))
    # Engraved borders: a raised bead frame on both side panels.
    inner = L.offset_outline(L.orient(body, True), -0.0028)
    frame_in = L.offset_outline(L.orient(body, True), -0.0043)
    for side in (-1, 1):
        b.add(L.extrude_outline(f"Receiver_Border_{side:+d}", [L.orient(inner, True), L.orient(frame_in, False)],
                                0.0010, 0.0003, bronze, "XZ", side * 0.0181), lod_drop=2)
        for j, (sx, sz) in enumerate(((-0.030, bz - 0.012), (0.112, bz - 0.009), (-0.030, bz + 0.0005),
                                      (0.112, bz + 0.0005))):
            b.add(screw(f"Receiver_Screw_{side:+d}_{j}", (sx, side * 0.0183, sz), (0, side, 0), 0.0019, brass,
                        70.0 * jit(side, j)), lod_drop=2)
    for j, sx in enumerate((-0.010, 0.050, 0.100)):
        b.add(screw(f"Cover_Screw_{j}", (sx, 0.0, bz + 0.0192 - 0.0004 * (sx > 0.09)), (0, 0, 1), 0.0022, brass,
                    40.0 * jit(j, 7)), lod_drop=2)
    b.add(mon_on_side("Receiver_Mon", 0.050, bz - 0.0065, 0.018, gold, -1, -0.0180))
    # Side drum magazine (left, +Y): ribbed, riveted hub, loading gate.
    dc = Vector((0.040, 0.018, bz - 0.004))
    drum_r, drum_t = 0.054, 0.028
    secs = [(0.0, drum_r - 0.004), (0.0015, drum_r), (0.004, drum_r + 0.0015), (0.0065, drum_r),
            (drum_t - 0.0065, drum_r), (drum_t - 0.004, drum_r + 0.0015), (drum_t - 0.0015, drum_r),
            (drum_t, drum_r - 0.005)]
    drum = L.tube("Drum", [(x, r, r) for x, r in secs], bronze, sides=80, max_seg=0.006, chunk=0.0, sharp_angle=40.0)
    L.transform(drum, Matrix.Translation(dc) @ L.rot("Z", 90))
    b.add(drum)
    face_y = dc.y + drum_t
    for k in range(12):
        a = math.tau * k / 12 + 0.13
        rib = L.box(f"Drum_Rib_{k}", (0.0, 0.0, 0.0), (0.0038, 0.0024, 0.028), bronze, 0.0008)
        L.transform(rib, Matrix.Translation(dc + Vector((0.0, drum_t + 0.0009, 0.0))) @ L.rot("Y", math.degrees(a)) @
                    Matrix.Translation((0.0, 0.0, 0.034)))
        b.add(rib, lod_drop=2)
    hub = L.tube("Drum_Hub", [(0.0, 0.021, 0.021), (0.003, 0.022, 0.022), (0.006, 0.020, 0.020)], bronze, sides=56,
                 max_seg=0.0, chunk=0.0)
    L.transform(hub, Matrix.Translation(dc + Vector((0, drum_t - 0.001, 0))) @ L.rot("Z", 90))
    b.add(hub)
    for k in range(8):
        a = math.tau * k / 8 + 0.2
        p = dc + Vector((0.028 * math.cos(a), drum_t + 0.0004, 0.028 * math.sin(a)))
        b.add(screw(f"Drum_Rivet_{k}", p, (0, 1, 0), 0.0017, bronze, 0.0), lod_drop=2)
    b.add(mon_on_side("Drum_Mon", dc.x, dc.z, 0.026, gold, 1, face_y + 0.0052))
    gate = plate("Drum_Gate", [(0.0, 0.0), (0.024, 0.0), (0.022, 0.010), (0.002, 0.010)], 0.0016, brass, 0.0, 0.0004,
                 0.002, 3)
    L.transform(gate, Matrix.Translation((dc.x - 0.012, face_y + 0.0008, dc.z + 0.036)))
    b.add(gate)
    hinge = L.tube("Drum_Gate_Hinge", [(0.0, 0.0016, 0.0016), (0.024, 0.0016, 0.0016)], brass, sides=12, max_seg=0.0,
                   chunk=0.0)
    L.transform(hinge, Matrix.Translation((dc.x - 0.012, face_y + 0.0012, dc.z + 0.0465)))
    b.add(hinge, lod_drop=2)
    # Advance crank on the right with a wooden knob.
    cp = Vector((0.040, -0.0195, bz - 0.004))
    crank = [(0.0, -0.004), (0.050, -0.003), (0.052, 0.003), (0.0, 0.004)]
    arm = plate("Crank_Arm", crank, 0.004, iron, 0.0, 0.0008, 0.002, 3)
    L.transform(arm, Matrix.Translation(cp + Vector((0, -0.002, 0))) @ L.rot("Y", 150))
    b.add(arm)
    b.add(screw("Crank_Nut", cp + Vector((0, -0.0042, 0)), (0, -1, 0), 0.0045, iron, 0.0))
    kb = L.tube("Crank_Knob", [(0.0, 0.004, 0.004), (0.003, 0.0065, 0.0065), (0.020, 0.0060, 0.0060),
                               (0.024, 0.0045, 0.0045)], knob, sides=20, max_seg=0.005, chunk=0.0)
    ca = math.radians(150.0)
    kpos = cp + Vector((0.048 * math.cos(ca), -0.004, -0.048 * math.sin(ca)))
    L.transform(kb, Matrix.Translation(kpos) @ L.rot("Z", -90))
    b.add(kb)
    # Hibasami-shaped hammer on the right, over the nipple at the breech.
    ham = [(0.0, 0.0), (0.010, 0.0), (0.009, 0.014), (0.001, 0.026), (-0.010, 0.032), (-0.014, 0.028), (-0.004, 0.018)]
    b.add(plate("Hammer", [(x - 0.018, z + bz + 0.004) for x, z in ham], 0.005, brass, -0.0215, 0.0008, 0.002, 3))
    b.add(screw("Hammer_Pivot", (-0.013, -0.0245, bz + 0.009), (0, -1, 0), 0.0030, brass, 10.0))
    # Trigger: brass hikigane, no guard.
    b.add(plate("Trigger", [(0.012, -0.012), (0.020, -0.012), (0.020, -0.022), (0.016, -0.034), (0.009, -0.037),
                            (0.008, -0.033), (0.013, -0.024)], 0.0042, brass, 0.0, 0.0008, 0.0015, 3))
    b.add(L.box("Rear_Sight", (0.10, 0.0, bz + 0.0215), (0.012, 0.010, 0.006), iron, 0.001))
    b.add(plate("Front_Sight", [(0.760, bz + 0.012), (0.768, bz + 0.012), (0.766, bz + 0.019), (0.762, bz + 0.019)],
                0.002, iron, 0.0, 0.0004))
    mekugi_pins(b, st, (0.30, 0.48, 0.64), lambda x: bz - 0.008, brass, iron, "Mekugi")
    b.socket("Grip_R", (0.0, 0.0, 0.0))
    b.socket("Grip_L", (0.30, 0.0, st.bot(0.30)))
    b.socket("Muzzle", (xm + 0.0015, 0.0, bz))
    b.socket("Magazine", tuple(dc))
    b.notes.update({"overall_m": round(xm + 0.0015 - (st.x0 - 0.0035), 4), "barrel_m": xm - 0.08, "bore_m": 0.0125,
                    "magazine": "36-round side drum",
                    "language": "dai stock with cheek butt, mekugi-pinned barrel, brass karakuri, no trigger guard"})


# ---------------------------------------------------------------------------
# Arc carbine (League, Tetsugorō)
# ---------------------------------------------------------------------------

ARC_STATIONS = [(-0.300, 0.0160, -0.0460, 0.0172), (-0.260, 0.0170, -0.0450, 0.0174), (-0.200, 0.0190, -0.0385, 0.0170),
                (-0.130, 0.0220, -0.0290, 0.0164), (-0.070, 0.0260, -0.0200, 0.0160), (-0.020, 0.0315, -0.0160, 0.0172),
                (0.060, 0.0345, -0.0140, 0.0185), (0.140, 0.0335, -0.0100, 0.0180), (0.180, 0.0320, -0.0080, 0.0170),
                (0.205, 0.0100, -0.0110, 0.0152), (0.350, 0.0095, -0.0120, 0.0146), (0.470, 0.0092, -0.0110, 0.0140),
                (0.482, 0.0092, -0.0105, 0.0138)]


def build_arc_carbine(b: L.Build):
    bz = 0.030
    xm = 0.56
    negoro = L.mat_urushi("M_Arc_Negoro", NEGORO_SHU, 0.22, undercoat=(0.012, 0.010, 0.009), wear=0.6,
                          grain_through=0.12, rubs=((-0.10, 0.0), (0.26, 0.38)), crackle=1.0)
    bronze = L.mat_alloy("M_Arc_Bronze", BRONZE_AGED, 0.40, BRONZE_PATINA, 0.55, "cast", oxide=BRONZE_OXIDE,
                         oxide_amount=0.45, wear_color=(0.72, 0.52, 0.30))
    # Cheek plates cut from sheet brass and filed: file strokes, not casting skin.
    brass = L.mat_alloy("M_Arc_Brass", BRASS, 0.30, (0.10, 0.08, 0.035), 0.5, "filemarks", wear_color=BRASS_WORN,
                        oxide=BRASS_OXIDE, oxide_amount=0.6)
    gold = L.mat_alloy("M_Arc_MonGold", GOLD, 0.24, (0.2, 0.1, 0.03), 0.3)
    copper = L.mat_alloy("M_Arc_Coil", COPPER, 0.3, (0.05, 0.08, 0.05), 0.35, "brushed_x",
                         oxide=(0.16, 0.075, 0.045), oxide_amount=0.35)
    arc = L.mat_emissive("M_Arc_Glow", (0.30, 0.26, 0.22), glow=ARC_GLOW, strength=4.0, rough=0.3)
    iron = L.mat_iron("M_Arc_Iron", oxide=(0.022, 0.020, 0.018), rust=0.12, polish_edges=0.4, forge_scale=0.3,
                      rough=0.44, metal=0.5)
    st = Stock(ARC_STATIONS, power=3.6)
    b.add(st.mesh("Stock", negoro))
    butt_cap(b, st, brass)
    # Barrel: iron octagon pinned through the forestock, bronze muzzle ring.
    barrel = oct_barrel("Barrel", [(0.10, 0.0196), (0.30, 0.0184), (xm, 0.0176)], iron, 0.005, 0.06)
    shift(barrel, z=bz)
    b.add(barrel)
    b.add(round_barrel("Muzzle_Ring", [(xm - 0.020, 0.0112), (xm - 0.018, 0.0122), (xm - 0.001, 0.0122),
                                       (xm + 0.0015, 0.0114)], bronze, 0.0055, 0.004))
    shift(b.groups["main"]["parts"][-1], z=bz)
    # Coil stages with their arc gaps inside an open bronze cage.
    for k in range(7):
        x0 = 0.215 + 0.036 * k
        ring = L.tube(f"Coil_Stage_{k}", [(x0, 0.0104, 0.0104), (x0 + 0.001, 0.0158, 0.0158),
                                          (x0 + 0.014, 0.0158, 0.0158), (x0 + 0.015, 0.0104, 0.0104)],
                      copper, sides=40, max_seg=0.005, chunk=0.0, sharp_angle=40.0)
        shift(ring, z=bz)
        b.add(ring)
        b.add(L.helix(f"Coil_Wire_{k}", x0 + 0.0015, x0 + 0.0135, 0.0162, 0.0016, 0.0013, copper, 0.0, bz, 20, 6),
              lod_drop=2)
        glow = L.tube(f"Arc_Gap_{k}", [(x0 + 0.015, 0.0094, 0.0094), (x0 + 0.021, 0.0099, 0.0099)], arc, sides=32,
                      max_seg=0.0, chunk=0.0)
        shift(glow, z=bz)
        b.add(glow, lod_drop=2)
    # Bronze collars clamp barrel and lower beam together (with screws).
    for x0, x1 in ((0.186, 0.212), (0.466, 0.492)):
        col = L.tube(f"Collar_{x0:.2f}", [(x0, 0.0175, 0.0175), (x0 + 0.002, 0.0192, 0.0192), (x1 - 0.002, 0.0192, 0.0192),
                                          (x1, 0.0175, 0.0175)], bronze, sides=48, max_seg=0.01, chunk=0.0,
                     sharp_angle=40.0)
        shift(col, z=bz)
        b.add(col)
        b.add(plate(f"Collar_Bracket_{x0:.2f}", [(x0 + 0.002, bz - 0.012), (x1 - 0.002, bz - 0.012),
                                                 (x1 - 0.002, st.top(x1) - 0.004), (x0 + 0.002, st.top(x0 + 0.01) - 0.004)],
                    0.022, bronze, 0.0, 0.0012, 0.002, 3))
        for side in (-1, 1):
            b.add(screw(f"Collar_Screw_{x0:.2f}_{side:+d}", ((x0 + x1) / 2, side * 0.0112, bz - 0.0195), (0, side, 0),
                        0.0018, brass, 30.0 * jit(int(x0 * 100), side)), lod_drop=2)
    for k in range(4):
        a = math.pi / 4 + math.tau * k / 4
        cy, cz = 0.0186 * math.cos(a), bz + 0.0186 * math.sin(a)
        b.add(L.tube(f"Cage_Bar_{k}", [(0.205, 0.0021, 0.0021, cy, cz), (0.473, 0.0021, 0.0021, cy, cz)], bronze, sides=10,
                     max_seg=0.03, chunk=0.0))
    # Karakuri cheek plates (brass) with the SORA mon; charging lever on the right.
    cheek = [(0.000, 0.000), (0.120, 0.000), (0.130, 0.012), (0.120, 0.026), (0.000, 0.026), (-0.010, 0.013)]
    for side in (-1, 1):
        y_face = side * (st.hw(0.06) + 0.0003)
        b.add(plate(f"Cheek_Plate_{side:+d}", cheek, 0.0016, brass, y_face, 0.0004, 0.004, 3))
        b.add(mon_on_side(f"Cheek_Mon_{side:+d}", 0.060, 0.013, 0.020, gold, side, y_face + side * 0.0008))
        for j, (sx, sz) in enumerate(((0.006, 0.004), (0.114, 0.004), (0.006, 0.022), (0.114, 0.022))):
            b.add(screw(f"Cheek_Screw_{side:+d}_{j}", (sx, y_face + side * 0.0008, sz), (0, side, 0), 0.0016, brass,
                        50.0 * jit(side, j, 3)), lod_drop=2)
    lever = [(0.0, 0.0), (0.009, 0.0), (0.008, 0.012), (0.000, 0.024), (-0.012, 0.030), (-0.015, 0.026), (-0.004, 0.016)]
    b.add(plate("Charge_Lever", [(x + 0.030, z + 0.030) for x, z in lever], 0.004, brass, -(st.hw(0.06) + 0.0034),
                0.0007, 0.002, 3))
    b.add(screw("Charge_Lever_Pivot", (0.034, -(st.hw(0.06) + 0.0058), 0.034), (0, -1, 0), 0.0028, brass, 25.0))
    # Trigger: brass hikigane, no guard.
    b.add(plate("Trigger", [(0.012, -0.012), (0.020, -0.012), (0.020, -0.022), (0.016, -0.034), (0.009, -0.037),
                            (0.008, -0.033), (0.013, -0.024)], 0.0042, brass, 0.0, 0.0008, 0.0015, 3))
    b.add(L.box("Sight_Rear", (0.13, 0.0, st.top(0.13) + 0.004), (0.014, 0.010, 0.008), brass, 0.0015))
    b.add(plate("Sight_Front", [(0.535, bz + 0.011), (0.545, bz + 0.011), (0.542, bz + 0.020), (0.538, bz + 0.020)],
                0.0022, brass, 0.0, 0.0004))
    mekugi_pins(b, st, (0.15,), lambda x: bz - 0.009, brass, iron, "Mekugi")
    b.socket("Grip_R", (0.0, 0.0, 0.0))
    b.socket("Grip_L", (0.33, 0.0, st.bot(0.33)))
    b.socket("Muzzle", (xm + 0.0015, 0.0, bz))
    b.notes.update({"overall_m": round(xm + 0.0015 - (st.x0 - 0.0035), 3),
                    "glow": "Mask R on the arc gaps; warm white, not cyan (League glows are warm)",
                    "language": "short negoro dai stock with cheek butt, pinned barrel, brass karakuri cheek plates"})


# ---------------------------------------------------------------------------
# Grenade launcher: Tamakichi's 手筒 hand-mortar
# ---------------------------------------------------------------------------

def nawa_helix(b, name, x0, x1, radius, rope_d, mat, seed, spt=30, lay=0.028):
    """Two-ply rice-straw rope wound on a helix round an X-axis tube: pitch,
    radius and thickness wander by hand; the plies twist along the rope."""
    pitch0 = rope_d * 0.90            # laid tight: each turn beds into the last
    turns = (x1 - x0) / pitch0
    n = int(turns * spt)
    pts, s_acc = [], 0.0
    for i in range(n + 1):
        f = i / n
        a = math.tau * turns * f + seed
        x = x0 + (x1 - x0) * f + 0.0016 * math.sin(a * 0.31 + seed) + 0.0009 * math.sin(a * 1.7 + 2 * seed)
        r = radius + rope_d / 2 + 0.0007 * math.sin(a * 0.53 + 3 * seed) + 0.0005 * math.sin(a * 2.3)
        pts.append(Vector((x, r * math.cos(a), r * math.sin(a))))
    length = sum((pts[i + 1] - pts[i]).length for i in range(len(pts) - 1))
    # Two plies: a waisted section whose waist twists round the rope.
    lobe = []
    for k in range(12):
        t = math.tau * k / 12
        waist = 1.0 - 0.34 * math.sin(t) ** 2
        lobe.append((rope_d * 0.5 * math.cos(t) * 1.08, rope_d * 0.5 * math.sin(t) * waist))

    def thick(u):
        s = 1.0 + 0.08 * math.sin(u * length / 0.07 + seed) + 0.05 * math.sin(u * length / 0.023)
        return (s, s)
    return L.sweep(name, pts, lobe, mat, up=(1, 0, 0), chunk=0.12, sharp_angle=None,
                   twist=lambda u: math.pi * u * length / lay, scale=thick), pts


def fibre_cards(name, pts, rope_d, mat, count, seed, frayed_end=None):
    """Alpha-masked straw fibre cards sticking out of a rope path at low
    angles (and a splayed brush at ``frayed_end``: (point, direction))."""
    verts, faces, uvm = [], [], []
    n = len(pts)
    for c in range(count):
        i = int(hash01(seed, c, 1) * (n - 3)) + 1
        p = pts[i]
        t = (pts[i + 1] - pts[i - 1]).normalized()
        radial = Vector((0.0, p.y, p.z)).normalized()
        around = t.cross(radial).normalized()
        ang = math.tau * hash01(seed, c, 2)
        out = (radial * math.cos(ang) + around * math.sin(ang)).normalized()
        if out.dot(radial) < -0.2:
            out = (out + radial * 0.8).normalized()
        base = p + out * (rope_d * 0.42)
        lean = 0.35 + 0.45 * hash01(seed, c, 3)
        dirc = (t * (1 if hash01(seed, c, 4) > 0.5 else -1) * math.cos(lean) + out * math.sin(lean)).normalized()
        ln = 0.008 + 0.012 * hash01(seed, c, 5)
        wd = 0.0016 + 0.0016 * hash01(seed, c, 6)
        side = dirc.cross(out).normalized()
        a0 = base - side * wd / 2
        a1 = base + side * wd / 2
        b1 = base + dirc * ln + side * wd / 2 + out * (0.002 * jit(seed, c, 7))
        b0 = base + dirc * ln - side * wd / 2
        k = len(verts)
        verts += [a0, a1, b1, b0]
        faces.append((k, k + 1, k + 2, k + 3))
        uvm.append([(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)])
    if frayed_end is not None:
        p, d = frayed_end
        d = d.normalized()
        q = d.orthogonal().normalized()
        r_ = d.cross(q)
        for c in range(26):
            ang = math.tau * c / 26 + 0.3 * jit(seed, c, 11)
            spread = 0.35 + 0.35 * hash01(seed, c, 12)
            dirc = (d * math.cos(spread) + (q * math.cos(ang) + r_ * math.sin(ang)) * math.sin(spread)).normalized()
            side = dirc.cross(q * math.cos(ang) + r_ * math.sin(ang)).normalized()
            base = p + (q * math.cos(ang) + r_ * math.sin(ang)) * rope_d * 0.25
            ln = 0.012 + 0.016 * hash01(seed, c, 13)
            wd = 0.0022
            k = len(verts)
            verts += [base - side * wd / 2, base + side * wd / 2, base + dirc * ln + side * wd / 2,
                      base + dirc * ln - side * wd / 2]
            faces.append((k, k + 1, k + 2, k + 3))
            uvm.append([(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)])
    return L.make_obj(name, verts, faces, mat, uvm=uvm, smooth=False, recalc=False)


def build_grenade_launcher(b: L.Build):
    x0, xm = 0.020, 0.640
    R, r_bore = 0.0380, 0.0280
    x_h0 = -0.200
    bamboo = L.mat_bamboo("M_GL_Madake", (0.25, 0.165, 0.055), smoked=0.6, rough=0.30, axis="X",
                          nodes=(0.575,), tube=(0.0, 0.0, r_bore))
    straw = L.mat_straw("M_GL_Nawa", tint=(1.0, 0.80, 0.50), tile=0.035, value=1.0, sat=1.15)
    fibre = L.mat_straw_fibre("M_GL_NawaFibre", tint=(0.62, 0.48, 0.24))
    oak = L.mat_wood("M_GL_PlugHandle", tone="kashi", value=0.9, rough=(0.46, 0.70), mapping="uv", wear=0.5,
                     dirt=0.5, rays=1.0, grips=((x_h0, -0.02),))
    iron = L.mat_iron("M_GL_Iron", oxide=(0.030, 0.026, 0.022), rust=0.45, polish_edges=0.3)
    fuse = L.mat_rope("M_GL_Fuse", "Rope002", tint=(0.25, 0.18, 0.12), tile=0.01, value=0.5)
    # Madake culm: thick wall, a node near the muzzle, the cut end showing
    # the wall and the pale inner skin.
    secs = [(x0, R - 0.0012), (x0 + 0.002, R), (0.574 - 0.006, R), (0.574 - 0.002, R + 0.0010), (0.575, R + 0.0016),
            (0.577, R + 0.0010), (0.574 + 0.008, R + 0.0002), (xm - 0.003, R), (xm - 0.0008, R - 0.0006),
            (xm, R - 0.0016)]
    b.add(round_barrel("Tube_Liner", secs, bamboo, r_bore, 0.58, sides=56))
    # Rice-straw nawa laid by hand over the culm, with loose fibres and a
    # frayed tail at each end.
    wrap0, wrap1 = x0 + 0.030, 0.535
    rope, pts = nawa_helix(b, "Nawa_Wrap", wrap0, wrap1, R, 0.0095, straw, 0.7)
    b.add(rope)
    b.add(fibre_cards("Nawa_Fibres", pts, 0.0095, fibre, 420, 3), lod_drop=2)
    for k, (p, d) in enumerate(((pts[0], Vector((-0.4, -0.3, -1.0))), (pts[-1], Vector((0.5, 0.2, -1.0))))):
        d = d.normalized()
        tail = [p + d * (0.012 * j) + Vector((0.0, 0.002 * math.sin(j), 0.0)) for j in range(6)]
        b.add(L.sweep(f"Nawa_Tail_{k}", tail, L.circle2d(0.0042, 8), straw, up=(1, 0, 0), chunk=0.0,
                      sharp_angle=None, scale=lambda u: (1.0 + 0.5 * u, 1.0 + 0.5 * u)))
        b.add(fibre_cards(f"Nawa_Fray_{k}", tail, 0.008, fibre, 0, 11 + k, frayed_end=(tail[-1], d)), lod_drop=2)
    # Oak plug handle turned from one piece: a spigot in the bore, a collar
    # capping the culm, the grip and a knob; lashed and pinned to the culm.
    b.add(L.tube("Plug_Handle", [(x_h0, 0.0150, 0.0150), (x_h0 + 0.004, 0.0205, 0.0205), (x_h0 + 0.014, 0.0212, 0.0212),
                                 (x_h0 + 0.024, 0.0186, 0.0186), (x_h0 + 0.070, 0.0176, 0.0176),
                                 (-0.060, 0.0170, 0.0170), (-0.030, 0.0190, 0.0190), (-0.016, 0.0300, 0.0300),
                                 (-0.010, R + 0.0022, R + 0.0022), (x0 - 0.0015, R + 0.0022, R + 0.0022),
                                 (x0, r_bore + 0.002, r_bore + 0.002), (x0 + 0.050, r_bore - 0.0002, r_bore - 0.0002)],
                 oak, sides=48, max_seg=0.012, chunk=0.25))
    lash, lpts = nawa_helix(b, "Plug_Lashing", x0 - 0.009, x0 + 0.022, R + 0.0006, 0.0075, straw, 2.1, spt=26)
    b.add(lash)
    b.add(fibre_cards("Plug_Lashing_Fibres", lpts, 0.0075, fibre, 60, 5), lod_drop=2)
    for side in (-1, 1):
        b.add(screw(f"Plug_Nail_{side:+d}", (x0 + 0.026, side * (R + 0.0002), 0.0), (0, side, 0), 0.0022, iron, 0.0),
              lod_drop=2)
    # Touch hole and fuse at the breech, between the collar and the wrap.
    fpath = [Vector((x0 + 0.010, 0.0, R + 0.001)), Vector((x0 + 0.004, 0.004, R + 0.020)),
             Vector((x0 - 0.010, 0.010, R + 0.028)), Vector((x0 - 0.018, 0.012, R + 0.022))]
    b.add(L.sweep("Fuse", catmull(fpath, 8), L.circle2d(0.0022, 8), fuse, up=(0, 1, 0), chunk=0.0, sharp_angle=None),
          lod_drop=2)
    b.add(L.tube("Touch_Hole_Bush", [(0.0, 0.0040, 0.0040), (0.0025, 0.0036, 0.0036)], iron, sides=16, max_seg=0.0,
                 chunk=0.0))
    L.transform(b.groups["main"]["parts"][-1], Matrix.Translation((x0 + 0.010, 0.0, R - 0.0008)) @ L.rot("Y", -90))
    b.socket("Grip_R", (0.0, 0.0, 0.0), x=(1, 0, 0), z=(0, 0, 1))
    b.socket("Grip_L", (0.30, 0.0, -(R + 0.0095)))
    b.socket("Muzzle", (xm, 0.0, 0.0))
    b.socket("Fuse", tuple(fpath[-1]))
    b.notes.update({"overall_m": round(xm - x_h0, 3), "bore_m": 2 * r_bore, "culm_diameter_m": 2 * R,
                    "nawa": "two-ply rice straw, ~9.5 mm, hand-laid (pitch/thickness jitter), loose fibre cards",
                    "handle": "turned oak plug handle, lashed and nailed into the culm base",
                    "basis": "Edo 手筒花火 rope-bound bamboo tube; fictional weapon"})


# ---------------------------------------------------------------------------
# Micro-mortar (League siege train)
# ---------------------------------------------------------------------------

def build_micro_mortar(b: L.Build):
    """Origin (Grip_R) is the grip bar framed by the hand hole at the back of
    the oak cradle."""
    ox = 0.072
    bz = 0.070
    xb, xm = 0.10 + ox, 0.56 + ox
    bronze = L.mat_alloy("M_MM_Bronze", BRONZE_AGED, 0.45, BRONZE_PATINA, 0.65, "cast", oxide=BRONZE_OXIDE,
                         oxide_amount=0.55, wear_color=(0.66, 0.48, 0.28))
    oak = L.mat_wood("M_MM_Cradle", tone="smoked", value=1.0, rough=(0.46, 0.72), mapping="uv", wear=0.45,
                     dirt=0.6, rays=1.0, tool=1.0, iron_bleed=0.8, grips=((-0.01, 0.07),))
    iron = L.mat_iron("M_MM_Iron", oxide=(0.030, 0.026, 0.022), rust=0.5, polish_edges=0.3, tsuchime=0.9,
                      forge_scale=0.6)
    gold = L.mat_alloy("M_MM_MonGilt", GOLD, 0.30, (0.2, 0.1, 0.03), 0.45, oxide=BRONZE_OXIDE, oxide_amount=0.3)
    fuse = L.mat_rope("M_MM_Fuse", "Rope002", tint=(0.25, 0.18, 0.12), tile=0.01, value=0.5)
    secs = [(xb, 0.030), (xb + 0.004, 0.052), (xb + 0.016, 0.064), (xb + 0.070, 0.068), (xb + 0.074, 0.072),
            (xb + 0.088, 0.072), (xb + 0.092, 0.066), (xb + 0.24, 0.058), (xb + 0.244, 0.062), (xb + 0.258, 0.062),
            (xb + 0.262, 0.057), (xm - 0.040, 0.056), (xm - 0.034, 0.064), (xm - 0.010, 0.067), (xm - 0.004, 0.068),
            (xm, 0.064)]
    b.add(round_barrel("Barrel", secs, bronze, 0.0375, 0.27, sides=64))
    shift(b.groups["main"]["parts"][-1], z=bz)
    rad = {x: r for x, r in secs}

    def barrel_r(xx):
        # the chase between the reinforcing rings tapers from 66 mm to 58 mm
        t = (xx - (xb + 0.092)) / (0.24 - 0.092)
        return 0.066 + (0.058 - 0.066) * max(0.0, min(1.0, t))
    # Casting flash along the mould's parting line (both sides of the chase).
    for side in (-1, 1):
        path = [Vector((x, side * (barrel_r(x) + 0.0003), bz)) for x in
                [xb + 0.095 + (0.235 - 0.095) * k / 20 for k in range(21)]]
        b.add(L.sweep(f"Casting_Flash_{side:+d}", path, [(-0.00025, -0.0009), (0.00025, -0.0009), (0.00025, 0.0009),
                                                          (-0.00025, 0.0009)], bronze, up=(0, side, 0), chunk=0.0,
                      sharp_angle=40.0), lod_drop=2)
    vent = L.tube("Vent_Boss", [(0.0, 0.009, 0.009), (0.010, 0.008, 0.008), (0.012, 0.0055, 0.0055)], bronze,
                  sides=24, max_seg=0.004, chunk=0.0)
    L.transform(vent, Matrix.Translation((xb + 0.035, 0.0, bz + 0.058)) @ L.rot("Y", -90))
    b.add(vent)
    b.add(mon_on_side("Cast_Mon", xb + 0.165, bz, 0.050, gold, -1, 0.0, 0.0014, wrap_r=barrel_r))
    # Oak cradle (daiza): a saddle carved to the breech, a grip bar framed by
    # a hand hole, chamfered arrises.
    half = 0.056
    blk = [(-0.008, 0.050), (0.16 + ox, 0.056), (0.206 + ox, 0.030), (0.206 + ox, -0.028), (0.052, -0.040),
           (-0.008, -0.034)]
    hole = L.fillet_poly([(0.012, -0.024), (0.060, -0.024), (0.060, 0.030), (0.012, 0.030)], 0.012, 4)
    cradle = L.extrude_outline("Cradle", [L.fillet_poly(blk, [0.02, 0.02, 0.03, 0.02, 0.03, 0.02], 5), hole],
                               2 * half, 0.006, oak, "XZ", 0.0)
    cut_secs = [(xb - 0.012, 0.032), (xb - 0.002, 0.0535), (xb + 0.014, 0.066), (xb + 0.068, 0.070), (xb + 0.072, 0.0745),
                (xb + 0.090, 0.0745), (xb + 0.094, 0.068), (0.210 + ox, 0.0665)]
    cutter = L.tube("cradle_cut", [(x, r + 0.0012, r + 0.0012, 0.0, bz) for x, r in cut_secs], None, sides=64,
                    max_seg=0.01, chunk=0.0)
    L.boolean(cradle, cutter)
    b.add(cradle)
    # Iron capsquare straps: each wraps over the barrel and runs down both
    # sides of the cradle, nailed off.
    for sx in (0.140 + ox, 0.186 + ox):
        rb = (rad.get(xb + 0.070, 0.068) if sx < xb + 0.07 else barrel_r(sx)) + 0.0015
        rb = max(rb, 0.0665)
        path = []
        t_s = 0.0030
        y_leg = half + t_s / 2 + 0.0002
        z_top_leg = bz - math.sqrt(max(rb ** 2 - y_leg ** 2, 0.0)) if rb > y_leg else bz
        for k in range(8):
            path.append(Vector((sx, -y_leg, -0.026 + (z_top_leg + 0.010 + 0.026) * k / 7)))
        a0 = math.pi + math.asin(min(1.0, (z_top_leg + 0.010 - bz) / -rb)) if rb > 0 else math.pi
        a_start = math.atan2(z_top_leg + 0.010 - bz, -y_leg)
        a_end = math.atan2(z_top_leg + 0.010 - bz, y_leg)
        n_arc = 40
        for k in range(1, n_arc):
            a = a_start + ((a_end - a_start) % -math.tau) * k / n_arc
            rr = max(rb + t_s / 2, math.hypot(y_leg, z_top_leg + 0.010 - bz))
            path.append(Vector((sx, rr * math.cos(a), bz + rr * math.sin(a))))
        for k in range(8):
            path.append(Vector((sx, y_leg, z_top_leg + 0.010 - (z_top_leg + 0.010 + 0.026) * k / 7)))
        b.add(L.sweep(f"Strap_{sx:.3f}", path, [(-0.009, -t_s / 2), (0.009, -t_s / 2), (0.009, t_s / 2),
                                                 (-0.009, t_s / 2)], iron, up=(1, 0, 0), chunk=0.0, sharp_angle=40.0))
        for side in (-1, 1):
            for zz in (-0.018, 0.004):
                b.add(screw(f"Strap_Nail_{sx:.3f}_{side:+d}_{zz:+.3f}", (sx, side * (y_leg + t_s / 2), zz), (0, side, 0),
                            0.0030, iron, 0.0), lod_drop=2)
    for side in (-1, 1):
        ring = [Vector((0.10 + ox + 0.022 * math.cos(math.tau * k / 24), side * (half + 0.004),
                        0.012 + 0.022 * math.sin(math.tau * k / 24))) for k in range(24)]
        b.add(L.sweep(f"Carry_Ring_{side:+d}", ring, L.circle2d(0.0035, 8), iron, up=(0, 1, 0), closed_path=True,
                      chunk=0.0, sharp_angle=None))
        b.add(screw(f"Carry_Ring_Staple_{side:+d}", (0.10 + ox, side * (half + 0.0005), 0.034), (0, side, 0), 0.0045,
                    iron, 0.0), lod_drop=2)
    fpath = [Vector((xb + 0.035, 0.0, bz + 0.070)), Vector((xb + 0.030, 0.006, bz + 0.086)),
             Vector((xb + 0.018, 0.010, bz + 0.094))]
    b.add(L.sweep("Fuse", catmull(fpath, 8), L.circle2d(0.0022, 8), fuse, up=(0, 1, 0), chunk=0.0, sharp_angle=None),
          lod_drop=2)
    b.socket("Grip_R", (0.0, 0.0, 0.0), x=(0, 0, 1), z=(-1, 0, 0))
    b.socket("Grip_L", (0.15 + ox, 0.0, -0.04))
    b.socket("Muzzle", (xm, 0.0, bz))
    b.socket("Fuse", tuple(fpath[-1]))
    b.notes.update({"overall_m": round(xm + 0.008, 3), "bore_m": 0.075,
                    "bronze": "cast, brown-green patina (base ~0.35/0.25/0.15), parting-line flash, pits",
                    "basis": "hand-held bronze mortar after the Edo 抱え大筒 (fictional League siege arm)"})


BUILDERS = {5: build_coil_matchlock, 9: build_repeater, 1: build_arc_carbine, 7: build_grenade_launcher,
            15: build_micro_mortar}

if __name__ == "__main__":
    L.run({wid: BUILDERS[wid] for wid in S.by_builder("create_runtime_weapon_firearms.py")})
