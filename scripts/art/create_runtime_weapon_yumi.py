"""Build the runtime yumi (18) and its ya (SM_Weapon_18_Ya).

Run:  blender -b --factory-startup --python scripts/art/create_runtime_weapon_yumi.py

A braced 221 cm asymmetric shigetō war bow (All Japan Kyudo Federation
standard length; grip one third from the lower tip; ~15 cm brace height):
a laminated stave of rounded-rectangular section (2.85 x 2.15 cm at the
grip, tapering to the tips) in black urushi; groups of bands of flat split
rattan, each wound two-and-a-bit turns by hand (pitch, width and start
wander) and lacquered, worn through to the golden skin on the crowns; a
deerskin nigiri wound as a shingled spiral strip; horn hazu with string
grooves and a resin-coated hemp string with a thickened nakajikake. The bow
shape is integrated from a curvature profile solved so both tips sit on the
string line, the upper limb (two thirds) bending more gently than the lower.

The ya is a 98 cm yadake arrow: tapered bamboo shaft with four nodes, horn
hazu, three dyed hawk-feather vanes (三立羽; the red dye is Nyaakoto's
character choice) whose barbs, natural barring and ragged trimmed edge are
an alpha-masked texture on thin vane geometry, silk bindings and a forged
yanagi-ba point. It is a separate runtime mesh sharing the bow's texture set;
it is shown nocked on the right of the bow.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import create_runtime_weapon_lib as L  # noqa: E402
import create_runtime_weapon_nihonto as N  # noqa: E402
import create_runtime_weapon_specs as S  # noqa: E402

LENGTH = 2.21
L_LOW = LENGTH / 3.0          # grip centre one third from the lower tip
L_UP = LENGTH - L_LOW
BRACE = 0.15
GRIP_HALF = 0.05
POWER = 4.6                   # superellipse power of the stave section (rounded rectangle)
EX = 2.0 / POWER


def smooth01(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def thickness(sig):
    """(width Y, depth X) of the stave at arc position sig (0 = grip centre)."""
    lim = L_UP if sig >= 0 else L_LOW
    u = min(abs(sig) / lim, 1.0)
    w = 0.0285 - 0.0120 * u ** 0.9
    d = 0.0215 - 0.0095 * u ** 0.85
    if abs(sig) < GRIP_HALF + 0.03:
        g = 1.0 - smooth01((abs(sig) - GRIP_HALF) / 0.03)
        d += 0.004 * g
    return w, d


def section_point(p, n, w, d, a, e=0.0):
    """Point and outward normal on the stave's rounded-rectangular section
    (width w along Y, depth d along n) at section angle a, offset by e."""
    ca, sa = math.cos(a), math.sin(a)
    yy = w / 2 * math.copysign(abs(ca) ** EX, ca)
    xx = d / 2 * math.copysign(abs(sa) ** EX, sa)
    gy = math.copysign(abs(yy / (w / 2)) ** (POWER - 1), yy) / (w / 2)
    gx = math.copysign(abs(xx / (d / 2)) ** (POWER - 1), xx) / (d / 2)
    nrm = (Vector((0.0, gy, 0.0)) + n * gx)
    nrm = nrm.normalized() if nrm.length > 1e-9 else n.copy()
    return p + Vector((0.0, yy, 0.0)) + n * xx + nrm * e, nrm


def hash01(*k):
    h = 0
    for v in k:
        h = (h * 1000003) ^ (int(v) & 0xFFFFFFFF)
        h = ((h ^ (h >> 13)) * 0x5BD1E995) & 0xFFFFFFFF
    h ^= h >> 15
    return (h & 0xFFFFFF) / float(0x1000000)


def jit(*k):
    return hash01(*k) * 2.0 - 1.0


def curvature(sig, amp, reflex):
    lim = L_UP if sig >= 0 else L_LOW
    u = abs(sig) / lim
    bend = amp * math.sin(math.pi * min(u, 1.0) * 0.92) ** 1.3 * smooth01((u - 0.04) / 0.12)
    tip = reflex * smooth01((u - 0.84) / 0.12)
    return bend - tip


def integrate(amp_u, amp_l, reflex=5.0, step=0.004):
    """Centreline points from the lower tip to the upper tip. The limbs bend
    toward the archer (-X) as they leave the grip; theta is measured from +Z."""
    def limb(amp, sign, lim):
        pts = [(0.0, 0.0, 0.0)]
        th = 0.0
        x = z = 0.0
        s = 0.0
        while s < lim - 1e-9:
            ds = min(step, lim - s)
            k = curvature(sign * (s + ds / 2), amp, reflex)
            th += k * ds
            x += -math.sin(th) * ds
            z += math.cos(th) * ds * sign
            s += ds
            pts.append((s * sign, x, z))
        return pts
    up = limb(amp_u, 1.0, L_UP)
    low = limb(amp_l, -1.0, L_LOW)
    return low, up


def solve_shape():
    target = -(BRACE + thickness(0.0)[1] / 2)
    res = {}
    for key in ("up", "low"):
        def tip_x(amp):
            low, up = integrate(amp, amp)
            return (up if key == "up" else low)[-1][1]
        # Scan upward from a straight limb to the first bend that reaches the
        # string line (tip x decreases monotonically on this branch), then refine.
        amp, step = 0.0, 0.02
        while tip_x(amp + step) > target:
            amp += step
            if amp > 2.0:
                raise RuntimeError("yumi limb shape did not reach the brace line")
        lo, hi = amp, amp + step
        for _ in range(40):
            mid = (lo + hi) / 2
            if tip_x(mid) > target:
                lo = mid
            else:
                hi = mid
        res[key] = (lo + hi) / 2
    return integrate(res["up"], res["low"])


def build_yumi(b: L.Build):
    low, up = solve_shape()
    # Ordered samples from the lower tip to the upper tip: (sigma, x, z).
    samples = list(reversed(low))[:-1] + up
    urushi = L.mat_urushi("M_Yumi_Urushi", (0.0065, 0.0055, 0.0048), 0.13, undercoat=(0.22, 0.14, 0.05),
                          wear=0.22, axis="Z", crackle=0.45)
    rattan = L.mat_rattan("M_Yumi_Rattan", lacquer=(0.050, 0.016, 0.010), skin=(0.44, 0.29, 0.12),
                          lacquer_amount=0.95, wear=0.12)
    leather = L.mat_leather("M_Yumi_Nigiri", tint=(0.62, 0.46, 0.33), value=0.8, tile=0.06, uv="uv", rough_bias=0.12,
                            soil=0.6)
    horn = L.mat_horn("M_Yumi_Hazu", color=(0.030, 0.022, 0.016))
    hemp = L.mat_rope("M_Yumi_Tsuru", "Rope001", tint=(0.72, 0.56, 0.33), tile=0.012, value=0.8, sat=0.8)
    shaft_m = L.mat_bamboo("M_Ya_Yadake", (0.42, 0.27, 0.10), smoked=0.25, rough=0.34, axis="X", lacquer=0.5)
    feather = L.mat_feather("M_Ya_Hane")
    silk = L.mat_urushi("M_Ya_Silk", (0.012, 0.008, 0.007), 0.2, undercoat=(0.2, 0.05, 0.03), wear=0.1)
    point = L.mat_iron("M_Ya_Yajiri", oxide=(0.03, 0.027, 0.024), rust=0.1, polish_edges=0.9, rough=0.4, metal=0.6)

    def frame(i):
        sig, x, z = samples[i]
        a = samples[max(i - 1, 0)]
        c = samples[min(i + 1, len(samples) - 1)]
        t = Vector((c[1] - a[1], 0.0, c[2] - a[2])).normalized()
        n = Vector((0, 1, 0)).cross(t).normalized()  # toward +X (back of the bow)
        return sig, Vector((x, 0.0, z)), t, n

    rings = []
    stave_sig = []
    total = len(samples)
    for i in range(0, total, 2):
        sig, p, t, n = frame(i)
        w, d = thickness(sig)
        # Tip taper and string groove near each end.
        rem = min(sig + L_LOW, L_UP - sig)
        if rem < 0.035:
            f = rem / 0.035
            w *= 0.62 + 0.38 * f
            d *= 0.62 + 0.38 * f
        rings.append([section_point(p, n, w, d, math.tau * k / 28)[0] for k in range(28)])
        stave_sig.append(sig)
    stave = L.loft("Stave", rings, urushi, closed=True, chunk=0.25, sharp_angle=None)
    b.add(stave)
    by_sig = [(frame(i)) for i in range(total)]

    def at(sig):
        best = min(by_sig, key=lambda f: abs(f[0] - sig))
        return best

    sigs = [f[0] for f in by_sig]

    def at_exact(sig):
        """Frame interpolated between the integrated samples."""
        import bisect
        i = min(max(bisect.bisect_left(sigs, sig), 1), len(sigs) - 1)
        s0, p0, t0, n0 = by_sig[i - 1]
        s1, p1, t1, n1 = by_sig[i]
        f = (sig - s0) / max(s1 - s0, 1e-9)
        return sig, p0.lerp(p1, f), t0.lerp(t1, f).normalized(), n0.lerp(n1, f).normalized()

    def wound_strip(name, sig0, sig1, width, thick, overlap, mat, e0, seed, spt=40, a0=0.0, jitter=0.06):
        """A flat strip wound on the stave from sig0 to sig1: turn k+1 laps
        turn k by ``overlap`` of the width (0 = butted side by side); the
        pitch wanders by hand."""
        pitch = width * (1.0 - overlap)
        turns = max((sig1 - sig0) / pitch, 1.0)
        n_pts = max(int(turns * spt), 12)
        path, nrms = [], []
        tilt = thick / max(width * max(overlap, 0.05), 1e-6) * 0.9
        for i in range(n_pts + 1):
            f = i / n_pts
            a = a0 + math.tau * turns * f
            wob = jitter * pitch * (math.sin(a * 0.41 + seed) * 0.6 + math.sin(a * 1.27 + 2.0 * seed) * 0.4)
            sig = sig0 + (sig1 - sig0) * f + wob
            s_, p, t, n = at_exact(sig)
            w, d = thickness(sig)
            q, nr = section_point(p, n, w, d, a, e0 + thick / 2)
            path.append(q)
            nrms.append(nr)
        prof = [(a_ - b_ * tilt, b_) for a_, b_ in L.lens2d(width, thick, 8, 4.0)] if overlap > 0 else \
            L.lens2d(width, thick, 8, 4.0)
        return N.sweep_with_normals(name, path, nrms, prof, mat, [0.0] * len(path), [(1.0, 1.0)] * len(path))

    # Nigiri: a leather underlay built up on the grip, wound with a deerskin
    # strip whose shingled laps show as a spiral seam.
    grip_rings = []
    for sig in [-GRIP_HALF + k * (2 * GRIP_HALF) / 20 for k in range(21)]:
        s_, p, t, n = at(sig)
        w, d = thickness(sig)
        e = 0.0007 * (1.0 if abs(sig) < GRIP_HALF - 0.004 else 0.4)
        grip_rings.append([section_point(p, n, w, d, math.tau * k / 28, e)[0] for k in range(28)])
    b.add(L.loft("Nigiri", grip_rings, leather, closed=True, chunk=0.0))
    b.add(wound_strip("Nigiri_Wrap", -GRIP_HALF + 0.002, GRIP_HALF - 0.004, 0.019, 0.0011, 0.18, leather, 0.0007,
                      0.9, spt=44, a0=0.4, jitter=0.05))
    # Shigetō: groups of bands of flat split rattan, each band a strip wound
    # a little over two turns side by side, under lacquer.
    groups = [0.13, 0.26, 0.40, 0.55, 0.70, 0.86, 1.02, 1.18, 1.32, -0.12, -0.24, -0.37, -0.50, -0.62]
    band_count = 0
    for gi, g_sig in enumerate(groups):
        n_b = 3 if abs(g_sig) < 1.25 else 2
        for j in range(n_b):
            sw = 0.0031 * (1.0 + 0.06 * jit(gi, j, 1))
            turns = 2.25 + 0.15 * jit(gi, j, 2)
            sig0 = g_sig + (j - (n_b - 1) / 2) * 0.0125 + 0.0012 * jit(gi, j, 3) - sw * turns / 2
            b.add(wound_strip(f"Rattan_{band_count:02d}", sig0, sig0 + sw * turns, sw, 0.00065, 0.0, rattan, 0.0,
                              3.0 * hash01(gi, j, 4), spt=24, a0=math.tau * hash01(gi, j, 5), jitter=0.10),
                  lod_drop=2)
            band_count += 1
    # Hazu (horn nock caps) and string loops.
    tips = {}
    for end, sign in (("Motohazu", -1), ("Urahazu", 1)):
        sig_end = L_UP if sign > 0 else -L_LOW
        cap_rings = []
        for dd, sc in ((0.045, 1.02), (0.040, 1.06), (0.022, 1.02), (0.017, 0.88), (0.012, 0.88), (0.008, 1.0),
                       (0.003, 0.9), (0.0, 0.45)):
            sig = sig_end - sign * dd
            s_, p, t, n = at(sig)
            w, d = thickness(sig)
            rem = dd
            f = rem / 0.035 if rem < 0.035 else 1.0
            w *= (0.62 + 0.38 * f) * sc
            d *= (0.62 + 0.38 * f) * sc
            cap_rings.append([section_point(p, n, w, d, math.tau * k / 28, 0.0006)[0] for k in range(28)])
        if sign < 0:
            cap_rings.reverse()
        b.add(L.loft(end, cap_rings, horn, closed=True, chunk=0.0, sharp_angle=45.0))
        s_, p, t, n = at(sig_end - sign * 0.0145)
        tips[end] = (p, t, n)
    # Tsuru: from groove to groove on the belly side, with loops round the hazu.
    lo_p, lo_t, lo_n = tips["Motohazu"]
    up_p, up_t, up_n = tips["Urahazu"]
    a_pt = lo_p - lo_n * (thickness(-L_LOW + 0.0145)[1] * 0.3)
    b_pt = up_p - up_n * (thickness(L_UP - 0.0145)[1] * 0.3)
    string_pts = [a_pt.lerp(b_pt, k / 160) for k in range(161)]
    b.add(L.sweep("Tsuru", string_pts, L.circle2d(0.00245, 8), hemp, up=(0, 1, 0), chunk=0.25, sharp_angle=None))
    # Nakajikake: thickened, re-wrapped section at the nocking point.
    nock_z = 0.07
    tz = (nock_z - a_pt.z) / (b_pt.z - a_pt.z)
    nock_pt = a_pt.lerp(b_pt, tz)
    nk = [a_pt.lerp(b_pt, tz + (k / 30 - 0.35) * 0.1 / (b_pt.z - a_pt.z)) for k in range(31)]
    b.add(L.sweep("Nakajikake", nk, L.circle2d(0.0031, 10), hemp, up=(0, 1, 0), chunk=0.0, sharp_angle=None))
    for end, (p, t, n) in tips.items():
        loop = []
        w, d = thickness(-L_LOW + 0.0145 if end == "Motohazu" else L_UP - 0.0145)
        for k in range(24):
            a = math.tau * k / 24
            loop.append(p + Vector((0, (w / 2 * 0.75 + 0.0026) * math.cos(a), 0)) + n * ((d / 2 * 0.75 + 0.0026) * math.sin(a)))
        b.add(L.sweep(f"Tsuru_Loop_{end}", loop, L.circle2d(0.0024, 8), hemp, up=tuple(t), closed_path=True,
                      chunk=0.0, sharp_angle=None), lod_drop=2)
    # ---- ya (nocked on the right of the bow, -Y) ------------------------------
    w0, d0 = thickness(0.0)
    arrow_y = -(w0 / 2 + 0.0055)
    nock = Vector((nock_pt.x + 0.004, arrow_y, nock_z))
    build_ya(b, nock, shaft_m, feather, silk, point, horn)
    rest = Vector((d0 / 2 + 0.002, arrow_y, nock_z))
    b.socket("Grip_L", (0.0, 0.0, 0.0))
    b.socket("Grip_R", tuple(nock_pt))
    b.socket("Muzzle", tuple(rest))
    b.socket("String_Lower", tuple(a_pt))
    b.socket("String_Upper", tuple(b_pt))
    chord = (b_pt - a_pt).length
    b.notes.update({"bow_length_m": LENGTH, "grip_centre_from_lower_tip_m": round(L_LOW, 4),
                    "brace_height_m": BRACE, "string_chord_m": round(chord, 4), "rattan_bands": band_count,
                    "nocking_point_z_m": nock_z})


def build_ya(b, nock, shaft_m, feather, silk, point, horn):
    L_ya = 0.98
    x0 = nock.x
    ox = Vector((0.0, nock.y, nock.z))

    def P(x, y=0.0, z=0.0):
        return ox + Vector((x0 + x, y, z))

    def r_shaft(x):
        u = x / L_ya
        return 0.0041 + 0.0005 * math.sin(math.pi * min(max(u, 0), 1)) ** 0.8

    nodes = (0.085, 0.36, 0.63, 0.905)
    secs = []
    x = 0.018
    while x < L_ya - 0.05:
        r = r_shaft(x)
        for nd in nodes:
            r += 0.00045 * math.exp(-((x - nd) / 0.0022) ** 2)
        secs.append((x0 + x, r, r, ox.y, ox.z))
        x += 0.004 if any(abs(x - nd) < 0.01 for nd in nodes) else 0.02
    b.add(L.tube("Ya_Shaft", secs, shaft_m, sides=16, max_seg=0.0, chunk=0.25), group="ya")
    # Hazu: horn nock with the string slot.
    hz = L.tube("Ya_Hazu", [(x0 - 0.002, 0.0036, 0.0036, ox.y, ox.z), (x0 + 0.004, 0.0043, 0.0043, ox.y, ox.z),
                            (x0 + 0.020, 0.0043, 0.0043, ox.y, ox.z)], horn, sides=16, max_seg=0.005, chunk=0.0)
    slot = L.box("slot", (x0 - 0.001, ox.y, ox.z), (0.012, 0.0028, 0.02), None, 0.0)
    L.boolean(hz, slot)
    b.add(hz, group="ya")
    # Silk bindings.
    for xa, xb in ((0.020, 0.030), (0.183, 0.196), (L_ya - 0.085, L_ya - 0.052)):
        rr = r_shaft(xa) + 0.0004
        b.add(L.tube(f"Ya_Silk_{xa:.3f}", [(x0 + xa, rr - 0.0002, rr - 0.0002, ox.y, ox.z),
                                            (x0 + xa + 0.0008, rr, rr, ox.y, ox.z),
                                            (x0 + xb - 0.0008, rr, rr, ox.y, ox.z),
                                            (x0 + xb, rr - 0.0002, rr - 0.0002, ox.y, ox.z)],
                     silk, sides=16, max_seg=0.005, chunk=0.0), group="ya")
    # Three vanes at 120 degrees (one straight up). Each is thin geometry a
    # few millimetres taller than the trimmed vane; ``vane_h`` carries the
    # trimmed height above the shaft so the feather's alpha cuts the ragged
    # barbed outline, and UVMetric runs u along the shaft, v out from its
    # surface (barb angle, rachis, barring).
    for k in range(3):
        ang = math.pi / 2 + math.tau * k / 3
        dirv = Vector((0, math.cos(ang), math.sin(ang)))
        side = Vector((0, -math.sin(ang), math.cos(ang)))
        n = 60
        xs_v, hs = [], []
        for i in range(n + 1):
            t = i / n
            x = 0.028 + 0.152 * t
            h = 0.0140 * (min(1.0, t / 0.07) ** 0.6) * (1 - max(0.0, (t - 0.58) / 0.42) ** 1.5 * 0.80)
            xs_v.append(x)
            hs.append(max(h, 0.0012))
        rings = []
        for x, h in zip(xs_v, hs):
            r = r_shaft(x)
            base = P(x) + dirv * (r - 0.0003)
            topp = P(x) + dirv * (r + h + 0.0035)
            rings.append([base - side * 0.0006, base + side * 0.0006, topp + side * 0.00012,
                          topp - side * 0.00012])
        vane = L.loft(f"Ya_Hane_{k}", rings, feather, closed=True, chunk=0.0, sharp_angle=60.0,
                      point_attrs={"vane_h": lambda i, j, hs=hs: hs[min(max(i, 0), len(hs) - 1)]})
        me = vane.data
        uvm = me.uv_layers["UVMetric"]
        for poly in me.polygons:
            for li in poly.loop_indices:
                co = me.vertices[me.loops[li].vertex_index].co
                rel = co - ox
                radial = (rel - Vector((co.x - ox.x, 0, 0))).dot(dirv)
                uvm.data[li].uv = (co.x - x0, radial - r_shaft(co.x - x0))
        b.add(vane, group="ya")
    # Yajiri: forged willow-leaf point with its neck in the shaft.
    blade_l = 0.052
    xs = L_ya - 0.052
    rings = []
    for i in range(22):
        t = i / 22
        x = xs + blade_l * t
        wdt = 0.0072 * math.sin(math.pi * min(0.15 + t * 0.95, 1.0)) ** 0.8 + 0.0022 * (1 - t)
        thk = 0.0026 * (1 - t) ** 0.6 + 0.0003
        rings.append([P(x, wdt, 0), P(x, 0, thk), P(x, -wdt, 0), P(x, 0, -thk)])
    b.add(L.loft("Ya_Yajiri", rings, point, closed=True, cap_start=True, tip_end=P(L_ya), chunk=0.0,
                 sharp_cols=(0, 1, 2, 3), sharp_angle=None), group="ya")
    b.groups["ya"]["origin"] = nock.copy()
    b.socket("Nock", tuple(nock), group="ya")
    b.socket("Tip", tuple(P(L_ya)), group="ya")


def builder(b: L.Build):
    b.group("ya", "SM_Weapon_18_Ya", offset=(0.0, 0.45, 0.0))
    build_yumi(b)


if __name__ == "__main__":
    L.run({18: builder})
