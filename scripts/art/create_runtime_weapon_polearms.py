"""Build the runtime polearms: yari (19), naginata (20), monofilament
naginata (12) and healing lance (17).

Run:  blender -b --factory-startup --python scripts/art/create_runtime_weapon_polearms.py [-- --only 19]

* Su-yari: a straight sankaku (triangular) blade of 20.6 cm (Met 30843) on a
  2.13 m foot-spear mount (Met 1727 note, ~7 ft). The blade, its bevelled
  machi shoulder and the kerakubi neck are one welded loft; the flat carries
  a hi and both edges a suguha hamon. Habaki, kuchigane ferrule, lacquered
  千段巻 cord binding, a black roiro shaft tapering toward the iron
  ishizuki.
* Naginata: a 46.7 cm naginata-zukuri blade with 2.1 cm sori (ColBase
  F-20202) widening toward the fukura, naginata-hi groove, habaki, seppa and
  small tsuba; the dōgane (with end rims, a brazed seam and a mekugi), a
  semegane band and a 千段巻 transition onto a lacquered oval ebu that
  tapers toward a long ishizuki.
* Monofilament naginata: the same form at 2.31 m (existing study length) with
  a smoked-oak and indigo-urushi shaft. The filament (0.5 mm) stands 1.5 mm
  off the ha on multi-turn silk bindings and glows warm (Mask R).
* Healing lance: a fictional apothecary lance with a hollow bronze needle,
  caged glass reservoir (Mask R marks the warm emissive remedy), a deep shu
  urushi shaft worn through where handled, and spiral, shingled indigo
  cotton grip wraps.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import bmesh
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import create_runtime_weapon_lib as L  # noqa: E402
import create_runtime_weapon_nihonto as N  # noqa: E402
import create_runtime_weapon_specs as S  # noqa: E402

GOLD, COPPER = N.GOLD, N.COPPER
BRASS = (0.91, 0.72, 0.38)
BRONZE_AGED = (0.27, 0.185, 0.10)         # cast bronze under its own brown oxide (F0)
BRONZE_PATINA = (0.040, 0.060, 0.036)     # brown-green patina in the recesses
BRONZE_OXIDE = (0.10, 0.07, 0.04)
SHU = L.srgb(168, 50, 30)                 # deep shu urushi (#A8321E)
AI = (0.012, 0.022, 0.055)
# League glows are warm (story bible 15.1); recorded in build_record.json.
REMEDY_GLOW = (1.0, 0.62, 0.30)           # warm honey-gold, ~2300 K
FILAMENT_GLOW = (1.0, 0.55, 0.22)         # warm amber-white thread


def smooth01(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


class NaginataBlade(N.Blade):
    """Naginata-zukuri: widening toward a long fukura, no yokote, with a
    naginata-hi groove in the shinogi-ji over the lower part. The hira is
    sampled finely so the broad polished faces shade without facets."""

    FR = (0.05, 0.13, 0.23, 0.35, 0.48, 0.62, 0.76, 0.89)

    def __init__(self, P, x_m):
        self.Wmax = P["sakihaba"]
        self.hi_end = P.get("hi_end", 0.38) * P["nagasa"]
        super().__init__(P, x_m)

    def width_body(self, s):
        u = max(0.0, min(1.0, s / max(self.s_yok, 1e-6)))
        return self.W0 + (self.Wmax - self.W0) * smooth01(u) ** 0.8

    def kasane(self, s):
        if s <= self.s_yok:
            return self.t0 + (self.t1 - self.t0) * max(0.0, s / self.s_yok)
        u = (s - self.s_yok) / self.K
        return self.t1 * (1.0 - u) ** 0.8

    def section(self, s):
        W = self.width(s)
        k = self.kasane(s)
        u = max(0.0, (s - self.s_yok) / self.K)
        t_s, t_m = k * 0.56, k * 0.46
        mh = t_m * 0.9
        sj = self.P["shinogi_ji"] * (W if s <= self.s_yok else self.W_yok * (1 - u))
        sj = min(sj, W * 0.6)
        hs = W - sj
        hm = max(W - mh, hs + 1e-5)
        side, roles = [], []
        for f in self.FR:
            side.append((t_s * math.sin(f * math.pi / 2) ** 0.85, hs * f))
            roles.append("hira")
        side.append((t_s, hs))
        roles.append("shinogi")
        depth = 0.42 * t_s * (1.0 - smooth01((s - (self.hi_end - 0.025)) / 0.025))
        for f, dd in ((0.14, 0.0), (0.30, 0.95), (0.70, 0.95), (0.86, 0.0)):
            h = hs + (hm - hs) * f
            y_lin = t_s + (t_m - t_s) * f
            side.append((max(y_lin - depth * dd, 0.0003), h))
            roles.append("sj")
        side.append((t_m, hm))
        roles.append("mune_corner")
        ring = [(0.0, 0.0)] + side + [(0.0, W)] + [(-y, h) for y, h in reversed(side)]
        role = ["edge"] + roles + ["mune"] + list(reversed(roles))
        zones = []
        for j in range(len(ring)):
            # face j runs from vertex j to j+1: classify by the pair of roles
            a, b = role[j], role[(j + 1) % len(ring)]
            pair = {a, b}
            if pair <= {"edge", "hira", "shinogi"} and "sj" not in pair:
                zones.append(3.0 if s > self.s_yok else 0.0)
            elif pair & {"mune"} or pair == {"mune_corner"}:
                zones.append(2.0)
            else:
                zones.append(1.0)
        sharp = [j for j, r in enumerate(role) if r in ("edge", "shinogi", "mune_corner", "mune")]
        return ring, zones, sharp


def shaft_sections(x0, x1, r0, r1, rz_ratio=1.0, step=0.02):
    secs = []
    n = max(2, int(abs(x1 - x0) / step))
    for i in range(n + 1):
        t = i / n
        r = r0 + (r1 - r0) * t
        secs.append((x0 + (x1 - x0) * t, r, r * rz_ratio))
    return secs


def capped_tube(name, x0, x1, ry, rz, mat, round_=0.001, sides=40, flare=None):
    secs = [(x0, ry - round_, rz - round_), (x0 + round_ * 0.7, ry, rz)]
    if flare:
        for fx, fr in flare:
            secs.append((fx, ry * fr, rz * fr))
    secs += [(x1 - round_ * 0.7, ry, rz), (x1, ry - round_, rz - round_)]
    secs.sort(key=lambda s: s[0])
    return L.tube(name, secs, mat, sides=sides, max_seg=0.01, chunk=0.25, sharp_angle=50.0)


def ishizuki(name, x_butt, length, ry, rz, mat, pointed=0.35):
    secs = [(x_butt, ry * 0.18, rz * 0.18), (x_butt + 0.004, ry * 0.55, rz * 0.55),
            (x_butt + length * pointed, ry * 0.94, rz * 0.94), (x_butt + length - 0.006, ry, rz),
            (x_butt + length - 0.0015, ry * 1.05, rz * 1.05), (x_butt + length, ry * 0.99, rz * 0.99)]
    return L.tube(name, secs, mat, sides=40, max_seg=0.008, chunk=0.2, sharp_angle=45.0)


# ---------------------------------------------------------------------------
# Yari
# ---------------------------------------------------------------------------

def yari_section(half, th, tb, hi_depth):
    """Sankaku section (y, z) from the +Y edge over the ridge to the -Y edge
    and back along the flat (-Z), whose middle is sunk into a hi.
    Returns points and a zone per point (1 inside the hi)."""
    pts = [(half, 0.0)]
    zone = [0.0]
    for f in (0.12, 0.28, 0.46, 0.66, 0.84):
        pts.append((half * (1 - f), th * math.sin(f * math.pi / 2) ** 0.8))
        zone.append(0.0)
    pts.append((0.0, th))
    zone.append(0.0)
    for f in (0.84, 0.66, 0.46, 0.28, 0.12):
        pts.append((-half * (1 - f), th * math.sin(f * math.pi / 2) ** 0.8))
        zone.append(0.0)
    pts.append((-half, 0.0))
    zone.append(0.0)
    hi_w = 0.30  # half-width of the hi as a fraction of the half-width
    for f in (-0.82, -0.55, -0.30, -0.15, 0.0, 0.15, 0.30, 0.55, 0.82):
        y = half * f
        z = -tb * (1 - f * f)
        if abs(f) < hi_w + 1e-6 and hi_depth > 0:
            g = math.sqrt(max(0.0, 1.0 - (f / (hi_w + 0.02)) ** 2))
            z += hi_depth * g
            zone.append(1.0)
        else:
            zone.append(0.0)
        pts.append((y, z))
    return pts, zone


def yari_head(x_m, length, w0, t_top, t_bot, mat):
    """Blade, bevelled machi shoulder and kerakubi neck as one welded loft."""
    rings, s_list, d_list, w_list, z_list = [], [], [], [], []
    base_pts, base_zone = yari_section(w0 / 2, t_top, t_bot, 0.0)
    n = len(base_pts)
    cz_base = sum(p[1] for p in base_pts) / n

    def neck_ring(x, r, blend, scale):
        out = []
        for (y, z) in base_pts:
            a = math.atan2(z - cz_base, y)
            ey, ez = r * math.cos(a), r * math.sin(a) + cz_base * 0.5
            out.append(Vector((x, ey + (y * scale - ey) * blend, ez + (z * scale - ez) * blend)))
        return out
    # Kerakubi (round neck, slight waist) into the machi shoulder bevel.
    for x, r, blend, scale in ((x_m - 0.040, 0.0062, 0.0, 1.0), (x_m - 0.026, 0.0060, 0.0, 1.0),
                               (x_m - 0.012, 0.0058, 0.0, 1.0), (x_m - 0.0055, 0.0064, 0.25, 0.80),
                               (x_m - 0.0022, 0.0070, 0.72, 0.93), (x_m - 0.0006, 0.0072, 0.95, 0.985)):
        rings.append(neck_ring(x, r, blend, scale))
        s_list.append(0.0)
        d_list.append([1.0] * n)
        w_list.append(w0)
        z_list.append([1.0] * n)
    n_s = 90
    s_vals = [length * (1 - (1 - i / n_s) ** 1.15) for i in range(n_s)]
    hi0, hi1 = 0.012, 0.62 * length
    for s in s_vals:
        u = s / length
        w = w0 * (1 - u ** 2.4) ** 0.85 * (1.0 + 0.06 * math.sin(math.pi * min(u * 1.6, 1.0)))
        th = t_top * (1 - u ** 1.6) ** 0.9
        tb = t_bot * (1 - u ** 1.6) ** 0.9
        depth = 0.0011 * smooth01((s - hi0) / 0.010) * (1.0 - smooth01((s - (hi1 - 0.02)) / 0.02))
        depth = min(depth, tb * 0.9)
        sec, zone = yari_section(w / 2, th, tb, depth)
        rings.append([Vector((x_m + s, y, z)) for y, z in sec])
        cum = [0.0]
        for j in range(1, n + 1):
            cum.append(cum[-1] + math.dist(sec[j % n], sec[j - 1]))
        per = cum[-1]
        e2 = 12  # index of the -Y edge
        d = []
        for j in range(n):
            de = min(abs(cum[j] - cum[0]), per - abs(cum[j] - cum[0]))
            d2 = min(abs(cum[j] - cum[e2]), per - abs(cum[j] - cum[e2]))
            d.append(min(de, d2))
        s_list.append(s)
        d_list.append(d)
        w_list.append(w)
        z_list.append(zone)
    tip = Vector((x_m + length, 0.0, 0.0))
    m = len(rings)

    def face_zone(i, j):
        i = min(i, m - 1)
        if i < 6:
            return 1.0  # burnished neck
        return 1.0 if (z_list[i][j] > 0.5 and z_list[i][(j + 1) % n] > 0.5) else 0.0
    blade = L.loft("Blade", rings, mat, closed=True, cap_start=True, tip_end=tip, chunk=0.2, sharp_angle=33.0,
                   point_attrs={"hamon_s": lambda i, j: s_list[min(i, m - 1)],
                                "hamon_d": lambda i, j: d_list[min(i, m - 1)][j],
                                "blade_w": lambda i, j: w_list[min(i, m - 1)]},
                   face_attr={"blade_zone": face_zone})
    # Carried flat side up: the hi and both suguha edges face the wielder.
    me = blade.data
    me.transform(Matrix.Scale(-1.0, 4, (0.0, 0.0, 1.0)))
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    me.update()
    return blade


def build_yari(b: L.Build):
    total = 2.13
    blade_len = 0.206
    x_b = -0.42  # butt; Grip_R (rear hand) at the origin
    x_tip = x_b + total
    x_m = x_tip - blade_len
    # Suguha along both edges; the hi and the neck are burnished (zone 1).
    steel = L.mat_blade_steel("M_Yari_Steel", hamon="suguha", s_yokote=blade_len * 1.5, w_yokote=0.012,
                              zukuri="shinogi")
    copper = L.mat_alloy("M_Yari_Habaki", N.SUAKA, 0.3, (0.12, 0.05, 0.03), 0.3, "nekogaki",
                         oxide=N.SUAKA_OXIDE, oxide_amount=0.5)
    iron = L.mat_iron("M_Yari_Iron", oxide=(0.028, 0.023, 0.019), rust=0.18, polish_edges=0.3, rough=0.5, metal=0.35,
                      tsuchime=0.6)
    r_top, r_butt = 0.0172, 0.0138
    sendan = L.mat_wrapped_lacquer("M_Yari_Sendanmaki", (0.016, 0.010, 0.007), 0.0030, 0.30, 0.35,
                                   (0.09, 0.05, 0.025), perimeter=math.tau * r_top)
    shaft = L.mat_urushi("M_Yari_Shaft_Roiro", (0.0075, 0.006, 0.005), 0.13, (0.09, 0.05, 0.025), 0.35,
                         crackle=0.6)
    b.add(yari_head(x_m, blade_len, 0.024, 0.0068, 0.0024, steel))
    b.add(capped_tube("Habaki", x_m - 0.058, x_m - 0.036, 0.0092, 0.0092, copper, 0.0008))
    b.add(capped_tube("Kuchigane", x_m - 0.105, x_m - 0.056, r_top + 0.0006, r_top + 0.0006, iron, 0.0012,
                      flare=[(x_m - 0.062, 1.03)]))
    x_sd0, x_sd1 = x_m - 0.36, x_m - 0.103

    def shaft_r(x):
        # The pole tapers from the head toward the ishizuki.
        t = (x - (x_b + 0.085)) / ((x_m - 0.103) - (x_b + 0.085))
        return r_butt + (r_top - r_butt) * max(0.0, min(1.0, t)) ** 0.8
    b.add(L.tube("Sendanmaki", [(x, shaft_r(x) + 0.0004, shaft_r(x) + 0.0004) for x in
                                [x_sd0 + (x_sd1 - x_sd0) * k / 12 for k in range(13)]],
                 sendan, sides=44, max_seg=0.0, chunk=0.25))
    xs0, xs1 = x_b + 0.085, x_sd0 + 0.004
    b.add(L.tube("Shaft", [(x, shaft_r(x), shaft_r(x)) for x in [xs0 + (xs1 - xs0) * k / 60 for k in range(61)]],
                 shaft, sides=40, max_seg=0.0, chunk=0.3))
    b.add(ishizuki("Ishizuki", x_b, 0.09, r_butt + 0.0006, r_butt + 0.0006, iron))
    b.socket("Grip_R", (0.0, 0.0, 0.0))
    b.socket("Grip_L", (0.72, 0.0, 0.0))
    b.socket("Muzzle", (x_tip, 0.0, 0.0))
    b.notes.update({"overall_m": total, "blade_m": blade_len, "section": "sankaku (triangular) with a hi on the flat",
                    "butt_x": x_b, "machi_x": round(x_m, 4),
                    "shaft_diameter_m": {"head": round(2 * r_top, 4), "butt": round(2 * r_butt, 4)}})


# ---------------------------------------------------------------------------
# Naginata family
# ---------------------------------------------------------------------------

NAGINATA = {
    20: dict(nagasa=0.467, sori=0.021, motohaba=0.030, sakihaba=0.0355, motokasane=0.0072, sakikasane=0.0052,
             kissaki=0.115, shinogi_ji=0.32, zukuri="shinogi", hi_end=0.36, overall=2.15,
             tsuba=dict(d_y=0.056, d_z=0.060, t=0.0045), shaft="roiro"),
    12: dict(nagasa=0.54, sori=0.030, motohaba=0.032, sakihaba=0.039, motokasane=0.0078, sakikasane=0.0056,
             kissaki=0.13, shinogi_ji=0.32, zukuri="shinogi", hi_end=0.40, overall=2.31,
             tsuba=dict(d_y=0.060, d_z=0.064, t=0.0048), shaft="smoked_oak_ai"),
}


def silk_binding(name, blade, sv, turns, pitch, cord, mat, below=0.0021):
    """A multi-turn cord binding wound round the blade section (and the
    filament standing off the ha) at arc position sv."""
    sec, _z, _sh = blade.section(sv)
    loop = L.offset_outline([(y, h) for y, h in sec], 0.0006)
    loop[0] = (0.0, -below)  # enclose the filament under the edge
    # resample the closed loop by arc length
    cum = [0.0]
    for i in range(1, len(loop) + 1):
        cum.append(cum[-1] + math.dist(loop[i % len(loop)], loop[i - 1]))
    per = cum[-1]

    def at(f):
        d = (f % 1.0) * per
        for i in range(len(loop)):
            if cum[i + 1] >= d:
                t = (d - cum[i]) / max(cum[i + 1] - cum[i], 1e-9)
                a, c = loop[i], loop[(i + 1) % len(loop)]
                return (a[0] + (c[0] - a[0]) * t, a[1] + (c[1] - a[1]) * t)
        return loop[0]
    n = int(turns * 64)
    path = []
    for k in range(n + 1):
        f = turns * k / n
        y, h = at(f)
        path.append(blade.point(sv - pitch * turns / 2 + pitch * f, y, h))
    return L.sweep(name, path, L.circle2d(cord / 2, 6), mat, up=(0, 1, 0), chunk=0.0, sharp_angle=None)


def build_naginata(b: L.Build, wid: int):
    P = NAGINATA[wid]
    x_b = -0.46
    # Oval ebu, taller edge-to-back, tapering from the dōgane to the butt.
    ebu_top = (0.0140, 0.0172)
    ebu_butt = (0.0122, 0.0148)
    Lh, ts, tt = 0.036, 0.0016, P["tsuba"]["t"]
    L_dogane = 0.050
    probe = NaginataBlade(P, 0.0)
    tip_dx = probe.tip().x
    x_m = x_b + P["overall"] - tip_dx
    blade = NaginataBlade(P, x_m)
    mono = wid == 12
    steel = L.mat_blade_steel("M_Naginata_Steel", hamon="notare_gunome" if wid == 20 else "suguha_ko_notare",
                              s_yokote=blade.s_yok, w_yokote=blade.W_yok, zukuri="shinogi", mask_hamon=not mono)
    habaki = L.mat_alloy("M_Naginata_Habaki", GOLD if wid == 20 else N.SUAKA, 0.25, (0.2, 0.1, 0.04), 0.15,
                         "nekogaki", wear_color=COPPER, oxide=None if wid == 20 else N.SUAKA_OXIDE,
                         oxide_amount=0.0 if wid == 20 else 0.5)
    seppa = L.mat_alloy("M_Naginata_Seppa", N.SUAKA, 0.3, (0.12, 0.05, 0.03), 0.3, "brushed_x",
                        oxide=N.SUAKA_OXIDE, oxide_amount=0.4)
    iron = L.mat_iron("M_Naginata_Iron", oxide=(0.026, 0.021, 0.017), tsuchime=0.9, rust=0.14,
                      polish_edges=0.25, rough=0.5, metal=0.3, forge_scale=0.4)
    dogane = L.mat_alloy("M_Naginata_Dogane", (0.62, 0.45, 0.24), 0.34, (0.07, 0.06, 0.035), 0.55, "cast",
                         oxide=(0.12, 0.08, 0.04), oxide_amount=0.45)
    b.add(N.blade_mesh(blade, steel, yokote=False, body_step=0.006))
    b.add(N.habaki_mesh(blade, Lh, habaki, t_mune=0.0030, t_ha=0.0017))
    fy, fz = ebu_top[0] + 0.0012, ebu_top[1] + 0.0012
    x_sepf = x_m - Lh
    b.add(N.oval_band("Seppa_Front", x_sepf - ts, x_sepf, fy + 0.004, fz + 0.005, seppa, 0.0004))
    x_tb = x_sepf - ts - tt
    T = P["tsuba"]
    n = 128
    outer = [(T["d_y"] / 2 * math.cos(math.tau * k / n), T["d_z"] / 2 * math.sin(math.tau * k / n)) for k in range(n)]
    b.add(L.extrude_outline("Tsuba", [outer], tt, 0.0008, iron, "YZ", x_tb + tt / 2))
    b.add(N.oval_band("Seppa_Back", x_tb - ts, x_tb, fy + 0.004, fz + 0.005, seppa, 0.0004))
    # Dōgane: a collar with raised rims at both ends, a brazed seam on the ha
    # side and the mekugi through it; then the semegane and a 千段巻 run.
    x_dog1 = x_tb - ts
    x_dog0 = x_dog1 - L_dogane
    b.add(N.oval_band("Dogane", x_dog0, x_dog1, fy, fz, dogane, 0.0009))
    for xa in (x_dog0, x_dog1 - 0.0045):
        b.add(N.oval_band(f"Dogane_Rim_{xa:.3f}", xa, xa + 0.0045, fy + 0.0009, fz + 0.0009, dogane, 0.0007))
    b.add(L.box("Dogane_Seam", ((x_dog0 + x_dog1) / 2, 0.0, -fz - 0.00015), (L_dogane - 0.010, 0.0022, 0.0007),
                dogane, 0.0003), lod_drop=2)
    for side in (-1, 1):
        pin = L.tube(f"Dogane_Mekugi_{side:+d}", [(0.0, 0.0028, 0.0028), (0.0008, 0.0027, 0.0027),
                                                   (0.0014, 0.0016, 0.0016)], iron, sides=18, max_seg=0.0, chunk=0.0)
        L.transform(pin, Matrix.Translation((x_dog0 + L_dogane * 0.42, side * (fy - 0.0002), 0.0)) @
                    L.rot("Z", 90 * side))
        b.add(pin, lod_drop=2)

    def ebu_r(x):
        t = max(0.0, min(1.0, (x - (x_b + 0.11)) / (x_dog0 - (x_b + 0.11))))
        return (ebu_butt[0] + (ebu_top[0] - ebu_butt[0]) * t, ebu_butt[1] + (ebu_top[1] - ebu_butt[1]) * t)

    def ebu_secs(x0, x1, grow=0.0, step=0.02):
        k = max(2, int((x1 - x0) / step))
        out = []
        for i in range(k + 1):
            x = x0 + (x1 - x0) * i / k
            ry, rz = ebu_r(x)
            out.append((x, ry + grow, rz + grow))
        return out
    x_sd1 = x_dog0 + 0.002
    x_sd0 = x_sd1 - 0.13
    x_seme = x_sd0 - 0.012
    band = L.mat_alloy("M_Naginata_Semegane", (0.62, 0.45, 0.24), 0.34, (0.07, 0.06, 0.035), 0.5, "cast",
                       oxide=(0.12, 0.08, 0.04), oxide_amount=0.4)
    ry_s, rz_s = ebu_r(x_seme)
    b.add(N.oval_band("Semegane", x_seme, x_seme + 0.012, ry_s + 0.0010, rz_s + 0.0010, band, 0.0006))
    sendan = L.mat_wrapped_lacquer("M_Naginata_Sendanmaki", (0.012, 0.008, 0.006), 0.0024, 0.35, 0.3,
                                   (0.10, 0.05, 0.025),
                                   perimeter=math.pi * (ebu_top[0] + ebu_top[1]))
    b.add(L.tube("Sendanmaki", ebu_secs(x_sd0, x_sd1, 0.0005, 0.01), sendan, sides=44, max_seg=0.0, chunk=0.25))
    if P["shaft"] == "roiro":
        shaft_mat = L.mat_urushi("M_Naginata_Ebu", (0.0075, 0.006, 0.005), 0.12, (0.12, 0.03, 0.015), 0.3,
                                 crackle=0.5)
        b.add(L.tube("Ebu", ebu_secs(x_b + 0.11, x_sd0 + 0.004), shaft_mat, sides=44, max_seg=0.0, chunk=0.3))
    else:
        oak = L.mat_wood("M_Mono_SmokedOak", tone="smoked", rough=(0.40, 0.62), lacquer=0.3, wear=0.3,
                         grips=((-0.12, 0.10), (0.62, 0.86)), rays=1.0)
        ai = L.mat_urushi("M_Mono_AiUrushi", AI, 0.12, (0.05, 0.03, 0.02), 0.3, crackle=0.4)
        seg = [(x_b + 0.11, x_b + 0.36, ai), (x_b + 0.36, x_sd0 - 0.30, oak), (x_sd0 - 0.30, x_sd0 + 0.004, ai)]
        for k, (x0, x1, mat) in enumerate(seg):
            b.add(L.tube(f"Ebu_{k}", ebu_secs(x0, x1), mat, sides=44, max_seg=0.0, chunk=0.3))
        # Filament: 0.5 mm, standing 1.5 mm off the ha on the silk bindings.
        silk = L.mat_braid("M_Mono_SilkBinding", (0.10, 0.030, 0.020), 0.5, kind="round", soil=0.2)
        wire = L.mat_emissive("M_Mono_Filament", (0.78, 0.74, 0.70), glow=FILAMENT_GLOW, strength=22.0, rough=0.08)
        pts = []
        s_list = [0.01 + (blade.s_yok + blade.K * 0.55 - 0.01) * i / 90 for i in range(91)]
        for sv in s_list:
            pts.append(blade.point(sv, 0.0, -0.0015))
        b.add(L.sweep("Monofilament", pts, L.circle2d(0.00025, 8), wire, up=(0, 1, 0), chunk=0.2))
        for k, sv in enumerate((0.04, 0.16, 0.28, 0.40, 0.50)):
            b.add(silk_binding(f"Mono_Binding_{k}", blade, sv, 6.0, 0.0011, 0.0009, silk), lod_drop=2)
        b.notes["glow"] = "filament Mask R, warm amber-white (League glows are warm)"
    b.add(ishizuki("Ishizuki", x_b, 0.115, ebu_butt[0] + 0.0012, ebu_butt[1] + 0.0012, iron, 0.3))
    b.socket("Grip_R", (0.0, 0.0, 0.0))
    b.socket("Grip_L", (0.75, 0.0, 0.0))
    m_tip, t_tip, n_tip = blade.frame(blade.arc)
    b.socket("Muzzle", tuple(m_tip), x=tuple(t_tip), z=tuple(n_tip))
    b.notes.update({"nagasa_m": P["nagasa"], "sori_m": P["sori"], "overall_m": P["overall"], "machi_x": round(x_m, 4),
                    "butt_x": x_b, "zukuri": "naginata-zukuri with naginata-hi",
                    "ebu_section_m": {"at_dogane": [2 * ebu_top[0], 2 * ebu_top[1]],
                                      "at_butt": [2 * ebu_butt[0], 2 * ebu_butt[1]],
                                      "shape": "oval, taller edge-to-back, tapering to the butt"}})


# ---------------------------------------------------------------------------
# Healing lance (fictional)
# ---------------------------------------------------------------------------

def build_healing_lance(b: L.Build):
    total = 1.85
    x_b = -0.40
    x_tip = x_b + total
    bronze = L.mat_alloy("M_Lance_Bronze", BRONZE_AGED, 0.45, BRONZE_PATINA, 0.6, "cast", oxide=BRONZE_OXIDE,
                         oxide_amount=0.5)
    # The needle is cast, then filed to its point: file strokes, not casting skin.
    needle_m = L.mat_alloy("M_Lance_Needle", BRONZE_AGED, 0.38, BRONZE_PATINA, 0.45, "nekogaki",
                           oxide=BRONZE_OXIDE, oxide_amount=0.4, wear_color=(0.66, 0.48, 0.28))
    brass = L.mat_alloy("M_Lance_Brass", (0.62, 0.47, 0.26), 0.36, (0.07, 0.06, 0.035), 0.45, "cast",
                        oxide=(0.12, 0.08, 0.04), oxide_amount=0.35)
    shu = L.mat_urushi("M_Lance_ShuShaft", SHU, 0.18, (0.012, 0.010, 0.009), 0.5,
                       rubs=((0.12, 0.24), (0.36, 0.60), (0.86, 1.00)), crackle=1.0)
    # Aizome (indigo) cotton, faded and soiled by handling.
    cloth = L.mat_cloth("M_Lance_CottonWrap", (0.30, 0.36, 0.50), tile=0.035, soil=1.0)
    bamboo = L.mat_bamboo("M_Lance_Cage", (0.40, 0.27, 0.11), smoked=0.3, lacquer=0.4)
    glass = L.mat_emissive("M_Lance_Remedy", (0.30, 0.18, 0.08), glow=REMEDY_GLOW, strength=5.0, rough=0.06)
    # Hollow needle head (a slender cone with a fine channel groove).
    head_len = 0.23
    xh = x_tip - head_len
    secs = []
    for i in range(41):
        t = i / 40
        r = 0.0068 * (1 - t) ** 1.25 + 0.0004
        secs.append((xh + head_len * t, r, r))
    b.add(L.tube("Needle", secs, needle_m, sides=32, max_seg=0.0, chunk=0.2, tip_end=(x_tip + 0.001, 0, 0),
                 cap_end=False))
    b.add(capped_tube("Needle_Collar", xh - 0.028, xh + 0.004, 0.0092, 0.0092, brass, 0.0009,
                      flare=[(xh - 0.012, 1.08)]))
    # Reservoir: glass vial in a four-slat bamboo cage between brass caps.
    xv0, xv1 = xh - 0.16, xh - 0.03
    b.add(L.tube("Remedy_Vial", [(xv0 + 0.006, 0.0115, 0.0115), (xv0 + 0.012, 0.0135, 0.0135),
                                 (xv1 - 0.012, 0.0135, 0.0135), (xv1 - 0.006, 0.0115, 0.0115)], glass, sides=40,
                 max_seg=0.01, chunk=0.0))
    b.add(capped_tube("Vial_Cap_Front", xv1 - 0.008, xv1, 0.0165, 0.0165, brass, 0.0009))
    b.add(capped_tube("Vial_Cap_Back", xv0, xv0 + 0.008, 0.0165, 0.0165, brass, 0.0009))
    for k in range(4):
        a = math.tau * k / 4 + math.pi / 4
        cy, cz = 0.0152 * math.cos(a), 0.0152 * math.sin(a)
        slat = L.tube(f"Cage_Slat_{k}", [(xv0 + 0.006, 0.0022, 0.0022, cy, cz), (xv1 - 0.006, 0.0022, 0.0022, cy, cz)],
                      bamboo, sides=12, max_seg=0.02, chunk=0.0)
        b.add(slat)
    b.add(capped_tube("Socket", xv0 - 0.07, xv0, 0.0158, 0.0158, bronze, 0.0012,
                      flare=[(xv0 - 0.012, 1.06), (xv0 - 0.06, 0.96)]))
    x_shaft_top = xv0 - 0.066

    def shaft_r(x):
        t = (x - (x_b + 0.07)) / (x_shaft_top - (x_b + 0.07))
        return 0.0148 + (0.0155 - 0.0148) * max(0.0, min(1.0, t))
    b.add(L.tube("Shaft", [(x, shaft_r(x), shaft_r(x)) for x in
                           [x_b + 0.07 + (x_shaft_top - x_b - 0.07) * k / 60 for k in range(61)]],
                 shu, sides=40, max_seg=0.0, chunk=0.3))
    # Spiral cotton wraps: an overlapping strip (shingled laps) over each hold.
    for k, (x0, x1) in enumerate(((-0.10, 0.12), (0.62, 0.84))):
        b.add(L.strip_wrap(f"Wrap_{k}", x0, x1, shaft_r, 0.020, 0.0009, 0.32, cloth, jitter=0.08, seed=1.7 * k))
    b.add(ishizuki("Ishizuki", x_b, 0.075, 0.0162, 0.0162, bronze, 0.3))
    b.socket("Grip_R", (0.0, 0.0, 0.0))
    b.socket("Grip_L", (0.73, 0.0, 0.0))
    b.socket("Muzzle", (x_tip, 0.0, 0.0))
    b.socket("Remedy", ((xv0 + xv1) / 2, 0.0, 0.0))
    b.notes.update({"overall_m": total, "fiction": "catalog special 17; Okuzu's apothecary lance (ch08)",
                    "glow": "remedy Mask R, warm honey-gold (League glows are warm)"})


BUILDERS = {
    19: build_yari,
    20: lambda b: build_naginata(b, 20),
    12: lambda b: build_naginata(b, 12),
    17: build_healing_lance,
}

if __name__ == "__main__":
    L.run({wid: BUILDERS[wid] for wid in S.by_builder("create_runtime_weapon_polearms.py")})
