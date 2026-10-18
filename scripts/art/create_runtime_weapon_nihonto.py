"""Build the runtime nihontō: katana (0), wakizashi (4) and tantō (10).

Run:  blender -b --factory-startup --python scripts/art/create_runtime_weapon_nihonto.py [-- --only 0]

Each sword is modelled from its measured parameters in
create_runtime_weapon_specs.NIHONTO: a curved blade lofted along a circular
mune arc (shinogi-zukuri with iori-mune, yokote, ko-shinogi and fukura, or
hira-zukuri for the tantō), habaki, seppa, tsuba with hitsu-ana, fuchi,
kashira, a samegawa core, SORA-mon or plain menuki, a bamboo mekugi and two
hineri-maki tsuka-ito strands that cross over/under on the omote and ura
faces and twist at the edges. The saya (koiguchi mouth with the blade slot,
kurikata with shitodome, kojiri and a wrapped sageo) is a separate runtime
mesh sharing the texture set.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import create_runtime_weapon_lib as L  # noqa: E402
import create_runtime_weapon_specs as S  # noqa: E402

GOLD = (0.95, 0.66, 0.26)
COPPER = (0.80, 0.43, 0.27)          # copper F0 (wear through gold foil, bronze fittings)
COPPER_WEAR = COPPER
SUAKA = L.srgb(242, 163, 138)        # suaka (refined copper) habaki and seppa, metallic F0
SUAKA_OXIDE = (0.16, 0.075, 0.045)   # brown cuprous oxide on handled suaka
SHAKUDO = (0.040, 0.036, 0.042)      # near-black shakudō (copper-gold alloy, patinated)
KON = (0.009, 0.013, 0.036)
KURO = (0.010, 0.010, 0.011)
CHA = (0.060, 0.030, 0.014)


def smooth01(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


class Blade:
    """Mune arc and cross-section geometry of one blade."""

    def __init__(self, P, x_machi):
        self.P = P
        self.L = P["nagasa"]
        self.sori = P["sori"]
        self.x_m = x_machi
        self.W0, self.W1 = P["motohaba"], P["sakihaba"]
        self.t0, self.t1 = P["motokasane"], P["sakikasane"]
        self.K = P["kissaki"]
        self.hira = P["zukuri"] == "hira"
        if abs(self.sori) > 1e-5:
            s = abs(self.sori)
            self.R = (self.L ** 2 / 4 + s ** 2) / (2 * s)
            self.sign = 1.0 if self.sori > 0 else -1.0
            self.phi_tip = 2 * math.asin(self.L / (2 * self.R))
            self.arc = self.R * self.phi_tip
        else:
            self.R = None
            self.sign = 1.0
            self.arc = self.L
        self.s_yok = self.arc - self.K
        self.W_yok = self.width_body(self.s_yok)
        # Fukura: circular arc tangent to the edge at the yokote through the tip.
        self.Rf = (self.K ** 2 + self.W_yok ** 2) / (2 * self.W_yok)
        self.z_mune0 = self.W0 / 2.0

    def width_body(self, s):
        return self.W0 + (self.W1 - self.W0) * max(0.0, min(1.0, s / max(self.s_yok, 1e-6)))

    def width(self, s):
        if s <= self.s_yok:
            return self.width_body(s)
        d = min(s - self.s_yok, self.Rf)
        he = self.Rf - math.sqrt(max(self.Rf ** 2 - d ** 2, 0.0))
        return max(self.W_yok - he, 0.0)

    def kasane(self, s):
        if s <= self.s_yok:
            return self.t0 + (self.t1 - self.t0) * max(0.0, s / self.s_yok)
        u = (s - self.s_yok) / self.K
        # Shinogi-zukuri steps down at the yokote; hira-zukuri has no yokote
        # and thins continuously into the fukura.
        return self.t1 * (1.0 if self.hira else 0.93) * (1.0 - u) ** 0.85

    def frame(self, s):
        """Mune point, tangent and up (toward the mune) at arc length s."""
        if self.R is None:
            return (Vector((self.x_m + s, 0.0, self.z_mune0)), Vector((1, 0, 0)), Vector((0, 0, 1)))
        phi = s / self.R
        m = Vector((self.x_m + self.R * math.sin(phi), 0.0,
                    self.z_mune0 + self.sign * self.R * (1 - math.cos(phi))))
        t = Vector((math.cos(phi), 0.0, self.sign * math.sin(phi)))
        n = Vector((-self.sign * math.sin(phi), 0.0, math.cos(phi)))
        return m, t, n

    def section(self, s):
        """(y, h) ring points, h measured from the edge; plus zones per face."""
        W = self.width(s)
        k = self.kasane(s)
        u = max(0.0, (s - self.s_yok) / self.K)
        if self.hira:
            t_half = k / 2.0
            mh = t_half * 0.85
            hc = W - mh
            fr = (0.07, 0.2, 0.38, 0.58, 0.77, 0.92)
            side = [(t_half * math.sin(f * math.pi / 2) ** 0.62, hc * f) for f in fr]
            side.append((t_half, hc))
            ring = [(0.0, 0.0)] + side + [(0.0, W)] + [(-y, h) for y, h in reversed(side)]
            sharp = [0, 7, 8, 9]
            zones = [2.0 if j in (7, 8) else 0.0 for j in range(len(ring))]
            return ring, zones, sharp
        t_s = k * 0.56
        t_m = k * 0.50
        mh = t_m * 0.9
        if s <= self.s_yok:
            sj = self.P["shinogi_ji"] * W
        else:
            sj = self.P["shinogi_ji"] * self.W_yok * (1.0 - u)
        sj = min(sj, W * 0.6)
        hs = W - sj
        fr = (0.08, 0.22, 0.42, 0.66, 0.86)
        side = [(t_s * math.sin(f * math.pi / 2) ** 0.85, hs * f) for f in fr]
        side.append((t_s, hs))                      # shinogi
        side.append((t_m, max(W - mh, hs + 1e-5)))  # mune corner
        ring = [(0.0, 0.0)] + side + [(0.0, W)] + [(-y, h) for y, h in reversed(side)]
        zones = []
        for j in range(len(ring)):
            if j <= 5 or j >= 10:
                zones.append(3.0 if s > self.s_yok else 0.0)
            elif j in (6, 9):
                zones.append(1.0)
            else:
                zones.append(2.0)
        return ring, zones, [0, 6, 7, 8, 9, 10]

    def point(self, s, y, h):
        m, t, n = self.frame(s)
        e = m - n * self.width(s)
        return e + n * h + Vector((0, 1, 0)) * y

    def tip(self):
        return self.frame(self.arc)[0]


def blade_mesh(blade: Blade, mat, yokote=True, name="Blade", body_step=0.005):
    # A ring exactly at the machi (s = 0) anchors the nagasa measurement.
    s_vals = [-0.004]
    s = 0.0
    while s < blade.s_yok - 1e-6:
        s_vals.append(s)
        s += body_step
    n_k = 44
    if yokote:
        # Two rings straddling the yokote give its crisp line.
        s_vals.append(blade.s_yok - 0.0002)
        s_vals.append(blade.s_yok + 0.0004)
        for i in range(1, n_k):
            u = i / n_k
            s_vals.append(blade.s_yok + 0.0004 + (blade.K - 0.0004) * (1 - (1 - u) ** 1.25))
    else:
        # No yokote (hira- or naginata-zukuri): even spacing into the tip.
        s_vals.append(blade.s_yok)
        for i in range(1, n_k):
            u = i / n_k
            s_vals.append(blade.s_yok + blade.K * (1 - (1 - u) ** 1.25))
    rings, zones_by_ring, dists, widths = [], [], [], []
    sharp_cols = None
    for sv in s_vals:
        sec, zones, sharp = blade.section(max(sv, 0.0))
        sharp_cols = sharp
        pts = [blade.point(max(sv, 0.0), y, h) + (Vector((sv, 0, 0)) if sv < 0 else Vector()) for y, h in sec]
        rings.append(pts)
        zones_by_ring.append(zones)
        acc = [0.0]
        n = len(sec)
        half = n // 2
        # distance from the edge along each side of the ring
        d = [0.0] * n
        for j in range(1, half + 1):
            d[j] = d[j - 1] + math.dist(sec[j], sec[j - 1])
        for j in range(n - 1, half, -1):
            nxt = (j + 1) % n
            d[j] = d[nxt] + math.dist(sec[j], sec[nxt])
        dists.append(d)
        widths.append(blade.width(max(sv, 0.0)))
    yok_i = s_vals.index(blade.s_yok + 0.0004) if yokote else 0
    tip = blade.tip()
    obj = L.loft(
        name, rings, mat, closed=True, cap_start=True, tip_end=tip, sharp_cols=sharp_cols,
        sharp_rings=(yok_i - 1, yok_i) if yokote else (), chunk=0.20, sharp_angle=None,
        point_attrs={
            "hamon_s": lambda i, j: max(s_vals[i], 0.0),
            "hamon_d": lambda i, j: dists[i][j],
            "blade_w": lambda i, j: widths[i],
        },
        face_attr={"blade_zone": lambda i, j: zones_by_ring[min(i, len(zones_by_ring) - 1)][j]},
    )
    return obj


def habaki_mesh(blade: Blade, length, mat, t_mune=0.0029, t_ha=0.0016, front=0.70, slant=0.0014):
    """Habaki collar. Its wall follows the blade section but is thicker at
    the mune than at the ha (the collar tapers toward the ha), thins from
    the rear toward the blade, and its front edge recedes a little toward
    the ha."""
    sec, _z, _s = blade.section(0.0)
    # The ring runs edge -> +y side -> mune -> -y side: counter-clockwise in
    # (y, h), so the right-hand edge normal points outward.
    poly = [Vector((y, h)) for y, h in sec]
    n = len(poly)
    W = blade.W0
    normals = []
    for i in range(n):
        e1 = (poly[i] - poly[i - 1]).normalized()
        e2 = (poly[(i + 1) % n] - poly[i]).normalized()
        nm = Vector((e1.y, -e1.x)) + Vector((e2.y, -e2.x))
        normals.append(nm.normalized() if nm.length > 1e-9 else Vector((e1.y, -e1.x)))
    m, _t, nn = blade.frame(0.0)
    e = m - nn * blade.W0
    x_front = blade.x_m
    specs = [(-length, 0.62, False), (-length + 0.0006, 1.0, False), (-length * 0.5, (1.0 + front) / 2, False),
             (-0.0012, front, True), (-0.0003, front * 0.55, True)]
    rings = []
    for dx, f, is_front in specs:
        ring = []
        for p, nm in zip(poly, normals):
            hf = max(0.0, min(1.0, p.y / W))
            d = (t_ha + (t_mune - t_ha) * hf) * f
            x = x_front + dx - (slant * (1.0 - hf) if is_front else 0.0)
            q = p + nm * d
            ring.append(Vector((x, q.x, e.z + q.y)))
        rings.append(ring)
    return L.loft("Habaki", rings, mat, closed=True, chunk=0.0, sharp_angle=40.0)


def kashira_mesh(name, x_k0, Lk, ry, rz, mat, dome, lip=0.0006):
    """Domed oval kashira: a side wall from the mouth (rolled lip) to the
    dome base, then an elliptical dome closing at the end of the tsuka."""
    secs = [(x_k0 + Lk, ry - lip, rz - lip), (x_k0 + Lk - 0.0006, ry, rz),
            (x_k0 + dome + 0.0015, ry * 0.998, rz * 0.998)]
    n = 16
    for i in range(n):
        th = 0.47 * math.pi * i / (n - 1)       # 0 at the dome base toward the apex
        secs.append((x_k0 + dome * (1.0 - math.sin(th)), ry * math.cos(th), rz * math.cos(th)))
    secs.sort(key=lambda s: s[0])
    return L.tube(name, secs, mat, sides=56, max_seg=0.004, chunk=0.0, sharp_angle=50.0, cap_start=False,
                  tip_start=(x_k0, 0.0, 0.0))


def kashira_kake(x_k0, Lk, RY, RZ, dome, prof, mat, x_sh, width=0.0085, thick=0.0012):
    """Kashira-kake: two ito ends leave the wrap, run up the kashira wall,
    pass through the omote and ura shitodome and cross over the domed end
    in an X (strand A over strand B at the crossing)."""
    x_mouth = x_k0 + Lk
    ito_lift = 0.0004   # the ends run under the last turns of the wrap

    def wall(x, psi):
        if x > x_mouth - 0.0004:
            ry, rz = prof(min(x, x_mouth + 0.02))
            k = min(1.0, (x - (x_mouth - 0.0004)) / 0.004)
            ry = RY + (ry + ito_lift - RY) * k
            rz = RZ + (rz + ito_lift - RZ) * k
        else:
            ry, rz = RY, RZ
        c, s = math.cos(psi), math.sin(psi)
        p = Vector((x, ry * c, rz * s))
        nrm = Vector((0.0, c / ry, s / rz)).normalized()
        return p, nrm

    def cap(theta, psi):
        xc = x_k0 + dome
        c, s = math.cos(psi), math.sin(psi)
        p = Vector((xc - dome * math.sin(theta), RY * math.cos(theta) * c, RZ * math.cos(theta) * s))
        nrm = Vector(((p.x - xc) / dome ** 2, p.y / RY ** 2, p.z / RZ ** 2)).normalized()
        return p, nrm

    objs = []
    for strand, sign in (("A", 1.0), ("B", -1.0)):
        def ang(deg):
            return math.radians(deg * sign)
        pts, nrms, wscale = [], [], []

        def add_wall(x0, a0, x1, a1, n, narrow_end=False, narrow_start=False):
            for i in range(n):
                t = i / n
                p, nm = wall(x0 + (x1 - x0) * t, a0 + (a1 - a0) * t)
                pts.append(p)
                nrms.append(nm)
                w = 1.0
                if narrow_end:
                    w = 1.0 - 0.62 * smooth01((t - 0.55) / 0.45)
                if narrow_start:
                    w = 0.38 + 0.62 * smooth01(t / 0.45)
                wscale.append(w)
        xs = x_sh - 0.0011 * sign
        add_wall(x_mouth + 0.014, ang(210), xs, ang(180), 30, narrow_end=True)
        add_wall(xs, ang(180), x_k0 + dome, ang(155), 12, narrow_start=True)
        for i in range(18):
            p, nm = cap(0.5 * math.pi * i / 18, ang(155))
            pts.append(p)
            nrms.append(nm)
            wscale.append(1.0)
        for i in range(18):
            p, nm = cap(0.5 * math.pi * (1.0 - i / 18), ang(335))
            pts.append(p)
            nrms.append(nm)
            wscale.append(1.0)
        add_wall(x_k0 + dome, ang(335), xs, ang(360), 12, narrow_end=True)
        add_wall(xs, ang(360), x_mouth + 0.014, ang(330), 31, narrow_start=True)
        path, lifted = [], []
        for k, (p, nm) in enumerate(zip(pts, nrms)):
            lift = thick / 2 + 0.0001
            # A crosses over B at the apex of the dome.
            apex = (p - Vector((x_k0, 0.0, 0.0))).length
            if strand == "A":
                lift += thick * math.exp(-(apex / 0.004) ** 2)
            path.append(p + nm * lift)
            lifted.append(nm)
        prof_l = L.lens2d(width, thick, sides=8, power=3.2)
        objs.append(sweep_with_normals(f"Kashira_Ito_{strand}", path, lifted, prof_l, mat, [0.0] * len(path),
                                       [(1.0, w) for w in wscale]))
    return objs


def shitodome(name, x_sh, side, RY, mat, rr=0.0027, wire=0.0006):
    """A small metal grommet ring on the kashira wall (hole axis along Y)."""
    c = Vector((x_sh, side * (RY + wire * 0.3), 0.0))
    ring = [c + Vector((rr * math.cos(math.tau * k / 24), 0.0, rr * 1.15 * math.sin(math.tau * k / 24)))
            for k in range(24)]
    return L.sweep(name, ring, L.circle2d(wire, 8), mat, up=(0, side, 0), closed_path=True, chunk=0.0,
                   sharp_angle=None)


def oval_band(name, x0, x1, ry, rz, mat, round_=0.0008, sides=48, cz=0.0):
    secs = [(x0, ry - round_, rz - round_, 0.0, cz), (x0 + round_ * 0.6, ry, rz, 0.0, cz),
            (x1 - round_ * 0.6, ry, rz, 0.0, cz), (x1, ry - round_, rz - round_, 0.0, cz)]
    return L.tube(name, secs, mat, sides=sides, max_seg=0.01, chunk=0.0, sharp_angle=50.0)


def ellipse_r(ry, rz, theta):
    """Surface point/normal of the ellipse y = ry sin t, z = rz cos t."""
    y, z = ry * math.sin(theta), rz * math.cos(theta)
    n = Vector((0.0, math.sin(theta) / ry, math.cos(theta) / rz)).normalized()
    return y, z, n


def tsuka_profile(P, x_k0, x_f):
    T = x_f - x_k0
    h, w = P["tsuka_height"] / 2.0, P["tsuka_width"] / 2.0

    def at(x):
        u = (x - x_k0) / T  # 0 kashira .. 1 fuchi
        waist = 1.0 - 0.055 * math.sin(math.pi * min(max(u, 0), 1)) ** 1.5
        grow = 0.965 + 0.035 * u
        return w * waist * grow, h * waist * grow
    return at


def tsuka_ito(P, prof, x_s, x_e, mat, menuki_spots, n_d, width=0.0105, thick=0.0012, face_angle=40.0):
    """Two opposed hineri-maki strands (theta: 0 mune edge, pi/2 +Y ura,
    pi ha edge, 3pi/2 -Y omote).

    Strand A goes around with theta and x(theta) = x0 + d theta / pi - c sin 2theta,
    so it crosses each side face on a ~40 degree diagonal and, at each edge,
    travels back while it twists through 180 degrees (the hineri). Strand B
    mirrors it (phi = pi - theta). They cross at the centre of each side face,
    omote and ura staggered by d, leaving the small hishi windows on the same.
    """
    d = (x_e - x_s) / (2 * n_d + 2)
    rz_mid = prof((x_s + x_e) / 2)[1]
    c = (rz_mid * math.tan(math.radians(face_angle)) - d / math.pi) / 2.0
    # Start and finish under the kashira and fuchi rims so no bare same shows
    # at either end of the wrap.
    x0 = x_s - d * 0.25
    theta_max = math.pi * (x_e + d * 0.25 - x0) / d
    crossings = []
    objs = []
    for strand in (0, 1):
        samples = int(theta_max / math.tau * 100)
        path, normals, twist_vals, scales = [], [], [], []
        for i in range(samples + 1):
            th = theta_max * i / samples
            x = x0 + d * th / math.pi - c * math.sin(2 * th)
            phi = th if strand == 0 else math.pi - th
            ry, rz = prof(x)
            y, z, nrm = ellipse_r(ry, rz, phi)
            lift = 0.0
            # Over/under: A on top on the ura (+Y) crossings, B on the omote.
            for k in range(int(theta_max / math.pi) + 2):
                th_c = math.pi / 2 + k * math.pi
                on_top = (k % 2 == 0) == (strand == 0)
                g = math.exp(-((th - th_c) / 0.32) ** 2)
                lift += g * (0.00065 if on_top else -0.0001)
            for mx, mside, mh, mrad in menuki_spots:
                side_angle = math.pi / 2 if mside > 0 else 3 * math.pi / 2
                dth = (phi - side_angle + math.pi) % math.tau - math.pi
                gx = math.exp(-((x - mx) / (mrad * 1.15)) ** 4)
                ga = math.exp(-(dth * ry / (mrad * 1.25)) ** 4)
                lift += 1.25 * mh * gx * ga
            tw = 0.0
            pinch = 0.0
            for m in range(0, int(theta_max / math.pi) + 2):
                u = (th - m * math.pi) / 0.42
                tw += math.pi * smooth01((u + 1) / 2)
                pinch = max(pinch, math.exp(-(u / 0.8) ** 2))
            wfac = 1.0 - 0.48 * pinch
            tfac = 1.0 + 0.9 * pinch
            twist_vals.append(tw)
            scales.append((tfac, wfac))
            stand = (width * wfac / 2) * abs(math.sin(tw)) * 0.35
            centre = Vector((x, y, z)) + nrm * (thick * tfac / 2 + 0.00006 + lift + stand)
            path.append(centre)
            normals.append(nrm)
        for k in range(int(theta_max / math.pi) + 1):
            xc = x0 + d * (0.5 + k)
            if xc <= x_e:
                crossings.append((xc, 1 if k % 2 == 0 else -1))
        profile = L.lens2d(width, thick, sides=8, power=3.2)
        objs.append(sweep_with_normals(f"Tsuka_Ito_{'AB'[strand]}", path, normals, profile, mat,
                                       twist_vals, scales))
    crossings = sorted(set(crossings))
    return objs, crossings, 2 * d


def sweep_with_normals(name, path, normals, profile, mat, twists, scales):
    rings = []
    count = len(path)
    for i in range(count):
        a = path[max(i - 1, 0)]
        b = path[min(i + 1, count - 1)]
        t = (b - a).normalized()
        n = normals[i] - t * normals[i].dot(t)
        n.normalize()
        bn = t.cross(n)
        ang = twists[i]
        ca, sa = math.cos(ang), math.sin(ang)
        n2 = n * ca + bn * sa
        b2 = -n * sa + bn * ca
        tf, wf = scales[i]
        rings.append([path[i] + n2 * (pa * tf) + b2 * (pb * wf) for pa, pb in profile])
    return L.loft(name, rings, mat, closed=True, chunk=0.12, sharp_angle=None)


def hitsu_outline(kind, cy, cz, flip=1.0):
    """Kozuka-hitsu (half-moon D slot) or kogai-hitsu (lobed slot) in (y, z)."""
    pts = []
    h = 0.0085
    wdt = 0.0028
    if kind == "kozuka":
        for k in range(24):
            t = math.pi * k / 23 - math.pi / 2
            pts.append((cy + flip * (wdt * 0.2 + wdt * 0.8 * math.cos(t)), cz + h * math.sin(t)))
        pts.append((cy - flip * wdt, cz + h))
        pts.append((cy - flip * wdt, cz - h))
    else:
        for k in range(48):
            t = math.tau * k / 48
            lobe = 1.0 + 0.18 * math.cos(3 * t) ** 2 * (1 if abs(math.sin(t)) > 0.7 else 0)
            pts.append((cy + wdt * math.cos(t), cz + h * math.sin(t) * lobe))
    # Holes are wound opposite to the outer outline (CW).
    area = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
               for i in range(len(pts)))
    return list(reversed(pts)) if area > 0 else pts


def tsuba_mesh(P, x_back, mats, has_mon):
    T = P["tsuba"]
    ry, rz, th = T["d_y"] / 2, T["d_z"] / 2, T["t"]
    n = 160
    outer = [(ry * math.cos(math.tau * k / n), rz * math.sin(math.tau * k / n)) for k in range(n)]
    rim_w = 0.0032
    inner = [(p[0] * (1 - rim_w / ry), p[1] * (1 - rim_w / rz)) for p in outer]
    plate_edge = [(p[0] * (1 - (rim_w - 0.0009) / ry), p[1] * (1 - (rim_w - 0.0009) / rz)) for p in outer]
    holes = []
    for idx, kind in enumerate(T["hitsu"]):
        cy = (0.0205 if idx == 0 else -0.0205)
        holes.append(hitsu_outline(kind, cy, 0.0, 1.0 if idx == 0 else -1.0))
    xc = x_back + th / 2
    # The mimi (rim) is its own iron: tekkotsu grains standing proud.
    rim = L.extrude_outline("Tsuba", [outer, list(reversed(inner))], th, 0.0007, mats["mimi"], "YZ", xc)
    plate = L.extrude_outline("Tsuba_Plate", [plate_edge] + holes, th * 0.84, 0.0004, mats["iron"], "YZ", xc)
    parts = [plate, rim]
    if has_mon:
        for side in (-1, 1):
            mon = L.sora_mon("Tsuba_SoraMon", 0.0105, 0.0005, mats["gold"], 0.0001)
            # Mon plane YZ facing -X (tsuka side) or +X (blade side), at the upper plate.
            M = Matrix(((0, 0, side, 0), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
            if side < 0:
                M = Matrix(((0, 0, -1, 0), (-1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
            L.transform(mon, Matrix.Translation((xc + side * (th * 0.42 + 0.00022), 0.0, rz - 0.0102)) @ M)
            parts.append(mon)
    return parts


def build_sword(b: L.Build, wid: int):
    P = S.NIHONTO[wid]
    katana = wid == 0
    aikuchi = P["tsuba"] is None
    # ---- materials -------------------------------------------------------
    mats = {}
    blade_tmp = Blade(P, 0.0)
    mats["steel"] = L.mat_blade_steel("M_Nihonto_Steel", hamon=P["hamon"], s_yokote=blade_tmp.s_yok,
                                      w_yokote=blade_tmp.W_yok, zukuri=P["zukuri"])
    if P["habaki"] == "kinkise":
        mats["habaki"] = L.mat_alloy("M_Habaki_Kinkise", GOLD, 0.24, (0.30, 0.16, 0.06), 0.10, "nekogaki",
                                     wear_color=COPPER_WEAR)
        mats["seppa"] = L.mat_alloy("M_Seppa_Kinkise", GOLD, 0.26, (0.30, 0.16, 0.06), 0.15, "brushed_x",
                                    wear_color=COPPER_WEAR)
    else:
        mats["habaki"] = L.mat_alloy("M_Habaki_Suaka", SUAKA, 0.30, (0.14, 0.06, 0.035), 0.20, "nekogaki",
                                     oxide=SUAKA_OXIDE, oxide_amount=0.55)
        mats["seppa"] = L.mat_alloy("M_Seppa_Suaka", SUAKA, 0.32, (0.14, 0.06, 0.035), 0.25, "brushed_x",
                                    oxide=SUAKA_OXIDE, oxide_amount=0.5)
    mats["iron"] = L.mat_iron("M_Tsuba_Iron", oxide=(0.026, 0.020, 0.016), tsuchime=1.2, rust=0.12,
                              polish_edges=0.2, rough=0.5, metal=0.3, forge_scale=0.5)
    mats["mimi"] = L.mat_iron("M_Tsuba_Mimi", oxide=(0.022, 0.017, 0.014), tsuchime=0.6, rust=0.08,
                              polish_edges=0.45, rough=0.46, metal=0.35, tekkotsu=1.0)
    mats["gold"] = L.mat_alloy("M_Gold_Inlay", GOLD, 0.24, (0.2, 0.1, 0.03), 0.30)
    if P["fittings"] == "shakudo":
        mats["fittings"] = L.mat_alloy("M_Fuchi_Shakudo", SHAKUDO, 0.30, (0.02, 0.018, 0.02), 0.2, "nanako",
                                       metal=1.0)
    elif P["fittings"] == "iron":
        mats["fittings"] = L.mat_iron("M_Fuchi_Iron", oxide=(0.024, 0.020, 0.017), tsuchime=0.7, rust=0.1,
                                      polish_edges=0.35, rough=0.45, metal=0.35)
    else:
        mats["fittings"] = L.mat_horn("M_Fuchi_Horn")
    mats["menuki"] = mats["gold"] if P["menuki"] == "sora_mon" else L.mat_alloy(
        "M_Menuki_Shakudo", SHAKUDO, 0.3, (0.02, 0.018, 0.02), 0.2, "nanako", metal=1.0)
    ito_col = {"kon": KON, "kuro": KURO}.get(P["ito_color"], KURO)
    mats["ito"] = L.mat_braid("M_Tsuka_Ito", ito_col, 1.0, soil=0.25)
    mats["mekugi"] = L.mat_bamboo("M_Mekugi_Bamboo", (0.10, 0.055, 0.022), smoked=0.5, axis="Y")
    mats["saya"] = L.mat_urushi("M_Saya_Roiro", (0.0065, 0.0055, 0.005), 0.09,
                                undercoat=(0.16, 0.03, 0.015) if katana else (0.05, 0.03, 0.02),
                                wear=0.35 if katana else 0.2)
    mats["horn"] = L.mat_horn("M_Saya_Horn")
    sageo_col = {"kon": KON, "cha": CHA, "kuro": KURO}[P["sageo"]]
    mats["sageo"] = L.mat_braid("M_Sageo", sageo_col, 1.25, soil=0.1)

    # ---- layout along X ---------------------------------------------------
    Lh = 0.032 if katana else (0.027 if wid == 4 else 0.024)
    ts = 0.0016 if not aikuchi else 0.0
    tt = P["tsuba"]["t"] if not aikuchi else 0.0
    Lf = 0.013 if katana else (0.012 if wid == 4 else 0.011)
    Lk = 0.030 if katana else (0.026 if wid == 4 else 0.018)
    dome = 0.009 if katana else (0.008 if wid == 4 else 0.006)
    x_f = 0.055 if katana else (0.045 if wid == 4 else 0.040)
    x_m = x_f + Lh + 2 * ts + tt
    x_k0 = x_f - P["tsuka"]
    blade = Blade(P, x_m)
    b.notes.update({"nagasa_m": P["nagasa"], "sori_m": P["sori"], "arc_m": round(blade.arc, 5),
                    "machi_x": round(x_m, 5), "fuchi_face_x": round(x_f, 5), "kashira_end_x": round(x_k0, 5)})

    # ---- blade and collar --------------------------------------------------
    b.add(blade_mesh(blade, mats["steel"], yokote=P["zukuri"] != "hira"))
    b.add(habaki_mesh(blade, Lh, mats["habaki"]))
    prof = tsuka_profile(P, x_k0, x_f)
    fy, fz = prof(x_f)
    if not aikuchi:
        sy, sz = fy + 0.0045, fz + 0.0065
        b.add(oval_band("Seppa_Front", x_m - Lh - ts, x_m - Lh, sy, sz, mats["seppa"], 0.0004))
        b.add(oval_band("Seppa_Back", x_f, x_f + ts, sy, sz, mats["seppa"], 0.0004))
        for p in tsuba_mesh(P, x_f + ts, mats, P["tsuba"]["mon"]):
            b.add(p, lod_drop=2 if p.name.startswith("Tsuba_SoraMon") else 99)

    # ---- tsuka ------------------------------------------------------------
    wall = 0.0019 if not aikuchi else 0.0012
    b.add(oval_band("Fuchi", x_f - Lf, x_f, fy + wall, fz + wall, mats["fittings"], 0.0007))
    ky, kz = prof(x_k0 + Lk)
    RY, RZ = ky + wall, kz + wall
    b.add(kashira_mesh("Kashira", x_k0, Lk, RY, RZ, mats["fittings"], dome))
    core_secs = []
    n_core = 40
    for i in range(n_core + 1):
        x = x_k0 + Lk * 0.6 + (x_f - Lf * 0.5 - (x_k0 + Lk * 0.6)) * i / n_core
        ry, rz = prof(x)
        core_secs.append((x, ry, rz))

    x_s = x_k0 + Lk + 0.0015
    x_e = x_f - Lf - 0.0015
    menuki_spots = []
    if P["menuki"]:
        T = x_e - x_s
        spots = [(x_s + 0.62 * T, -1), (x_s + 0.36 * T, 1)] if katana else [(x_s + 0.6 * T, -1), (x_s + 0.4 * T, 1)]
        for mx, side in spots:
            ry, rz = prof(mx)
            if P["menuki"] == "sora_mon":
                m = L.sora_mon("Menuki", 0.025, 0.0020, mats["menuki"], 0.0003)
                mh = 0.0020
                rad = 0.0125
            else:
                m = L.tube("Menuki", [(-0.014, 0.0001, 0.0001), (-0.012, 0.0022, 0.0009),
                                      (0.0, 0.0045, 0.0017), (0.012, 0.0022, 0.0009), (0.014, 0.0001, 0.0001)],
                           mats["menuki"], sides=24, max_seg=0.003, chunk=0.0)
                mh = 0.0017
                rad = 0.012
            # Decal frame: local x along the tsuka, local y around, local z out.
            L.transform(m, Matrix.Translation((mx, 0.0, 0.0)))
            for v in m.data.vertices:
                x, yl, zl = v.co
                r_side = ry
                if side > 0:  # seen from +Y: local x runs toward -X, local y toward +Z
                    x = mx - (x - mx)
                    theta = math.pi / 2 - yl / r_side
                else:         # seen from -Y: local x toward +X, local y toward +Z
                    theta = 3 * math.pi / 2 + yl / r_side
                ry_x, rz_x = prof(x)
                sy_, sz_, nrm = ellipse_r(ry_x, rz_x, theta)
                p = Vector((x, sy_, sz_)) + nrm * (zl + mh * 0.5)
                v.co = p
            m.data.update()
            b.add(m, lod_drop=2)
            menuki_spots.append((mx, side, mh, rad))
    # Same: the oyatsubu (king nodule) sits under the omote (-Y) menuki.
    omote = [s_ for s_ in menuki_spots if s_[1] < 0]
    oya = None
    if omote and not aikuchi:
        ox = omote[0][0]
        oya = (ox, -prof(ox)[0], 0.0, 0.0052)
    if aikuchi:
        mats["same"] = L.mat_samegawa("M_KuroSame", lacquer=(0.008, 0.007, 0.006))
    else:
        mats["same"] = L.mat_samegawa("M_Samegawa", oyatsubu=oya)
    b.add(L.tube("Tsuka_Samegawa", core_secs, mats["same"], sides=48, max_seg=0.0, chunk=0.12))
    b.notes["same"] = {"nodules_mm": [0.4, 1.2], "oyatsubu_x_m": round(oya[0], 4) if oya else None}

    if P["ito_diamonds"]:
        strands, crossings, pitch = tsuka_ito(P, prof, x_s, x_e, mats["ito"], menuki_spots, P["ito_diamonds"])
        for s_ in strands:
            b.add(s_)
        # Kashira-kake: the ito crosses the domed kashira through the shitodome.
        x_sh = x_k0 + dome + 0.0038
        for k_ in kashira_kake(x_k0, Lk, RY, RZ, dome, prof, mats["ito"], x_sh):
            b.add(k_)
        for side in (-1, 1):
            b.add(shitodome(f"Shitodome_Kashira_{side:+d}", x_sh, side, RY, mats["gold"] if katana else mats["fittings"]),
                  lod_drop=2)
        # Mekugi: in the window between the first two omote crossings from the fuchi.
        omote_x = sorted([xc for xc, side in crossings if side < 0], reverse=True)
        mx = (omote_x[0] + omote_x[1]) / 2 if len(omote_x) > 1 else x_e - 0.03
        b.notes["ito_pitch_m"] = round(pitch, 5)
        b.notes["ito_crossings_per_face"] = len(omote_x)
        b.notes["kashira"] = "domed oval with shitodome; ito crosses it (kashira-kake)"
    else:
        mx = x_f - 0.028
    ry, rz = prof(mx)
    mek = L.tube("Mekugi", [(-ry - 0.0009, 0.0026, 0.0026), (-ry - 0.0003, 0.0027, 0.0027),
                            (ry + 0.0003, 0.0027, 0.0027), (ry + 0.0009, 0.0026, 0.0026)],
                 mats["mekugi"], sides=20, max_seg=0.004, chunk=0.0)
    L.transform(mek, Matrix.Translation((mx, 0, 0)) @ L.rot("Z", 90))
    b.add(mek, lod_drop=2)

    # ---- saya ---------------------------------------------------------------
    build_saya(b, P, blade, x_m - Lh, mats, katana, aikuchi, prof(x_f))

    # ---- sockets ------------------------------------------------------------
    b.socket("Grip_R", (0.0, 0.0, 0.0))
    b.socket("Grip_L", (x_k0 + 0.045 if katana else x_k0 + 0.022, 0.0, 0.0))
    m_tip, t_tip, n_tip = blade.frame(blade.arc)
    b.socket("Muzzle", tuple(m_tip), x=tuple(t_tip), z=tuple(n_tip))


def sageo_path(centre, dims, disp, s0, a0, sigma, turns, span, spread=0.35, samples_per_turn=72):
    """Points and surface normals of one sageo strand spiralling down the
    saya from arc position s0, starting ``spread`` rad beside angle a0 and
    ending exactly on it (sigma +-1 = direction)."""
    pts, nrms, angs, ss = [], [], [], []
    n = int(turns * samples_per_turn)
    for i in range(n + 1):
        f = i / n
        s = s0 + span * f
        a = a0 + sigma * (spread * (1.0 - f) + math.tau * turns * f)
        cc, _t, nn = centre(s)
        ww, hh = dims(s)
        ca, sa = math.cos(a), math.sin(a)
        yy = ww * math.copysign(abs(ca) ** (2 / 2.3), ca)
        zz = hh * math.copysign(abs(sa) ** (2 / 2.3), sa)
        nrm = Vector((0, math.copysign(abs(ca) ** 0.5, ca) / ww, 0)) + nn * (math.copysign(abs(sa) ** 0.5, sa) / hh)
        nrm.normalize()
        pts.append(cc + disp + Vector((0, yy, 0)) + nn * zz)
        nrms.append(nrm)
        angs.append(a)
        ss.append(s)
    return pts, nrms, angs, ss


def build_sageo(centre, dims, disp, s_k, a0, hole_c, hole_axis, fin_t, mat, span, turns, tail_len,
                width=0.009, thick=0.0016):
    """One continuous flat braided sageo (~9 mm x 1.6 mm, ~1.5 m): through
    the kurikata, both halves spiral down the saya in opposite senses and
    cross (over and under) on the omote and ura, meet in a knot and end in
    two short tails lying along the saya."""
    s_start = s_k + 0.014
    # Each half leaves the hole on its own side of the fin.
    halves = {}
    for sigma in (1.0, -1.0):
        halves[sigma] = sageo_path(centre, dims, disp, s_start, a0, sigma, turns, span)
    # Over/under at the crossings: the halves meet where their angles agree.
    lift_over = thick * 1.05

    def lifted(sigma):
        pts, nrms, angs, ss = halves[sigma]
        out = []
        other = halves[-sigma]
        for k, (p, nm) in enumerate(zip(pts, nrms)):
            lift = thick / 2 + 0.0002
            q = other[0][k]
            dist = (p - q).length
            if dist < 0.012 and k < len(pts) - 40:
                # Count the meetings so far and alternate which half is on top.
                meet = int(round(abs(angs[k] - other[2][k]) / math.tau))
                on_top = (meet % 2 == 0) == (sigma > 0)
                g = math.exp(-(dist / 0.006) ** 2)
                lift += g * (lift_over if on_top else 0.0)
            out.append(p + nm * lift)
        return out, nrms
    pa, na = lifted(1.0)
    pb, nb_ = lifted(-1.0)
    # Through-hole run: from the -sigma half's start, across the hole, to the +sigma half.
    ax = hole_axis.normalized()
    c_plus = pa[0]
    c_minus = pb[0]
    if (c_plus - hole_c).dot(ax) < 0:
        ax = -ax
    reach = fin_t / 2 + 0.003
    hp = hole_c + ax * reach
    hm = hole_c - ax * reach
    thru = []
    for k in range(9):
        thru.append(hm.lerp(hp, k / 8))

    def bridge(p0, p1, n=10, bulge=0.003, up=None):
        out = []
        for k in range(1, n):
            t = k / n
            q = p0.lerp(p1, smooth01(t))
            if up is not None:
                q = q + up * (bulge * math.sin(math.pi * t))
            out.append(q)
        return out
    c_mid, _t, n_mid = centre(s_k)
    up_out = (hole_c - (c_mid + disp)).normalized()
    lead_plus = bridge(hp, c_plus, 12, 0.002, up_out)
    lead_minus = bridge(c_minus, hm, 12, 0.002, up_out)
    # Knot: where the halves meet at the end, the + half throws a tight loop
    # round the - half; then both tails lie along the saya toward the kojiri.
    end_p = pa[-1]
    end_n = na[-1]
    s_end = s_start + span
    _c, t_end, _n = centre(s_end)
    side = end_n.cross(t_end).normalized()
    knot, knot_n = [], []
    kr = 0.0042
    kc = end_p + end_n * (thick * 1.4 + kr * 0.6)
    for k in range(1, 37):
        a = math.tau * 1.25 * k / 36
        q = end_p + end_n * (thick * 1.4 + kr * 0.6 * (1 - math.cos(a))) + t_end * (0.004 * k / 36) \
            + side * (kr * math.sin(a))
        knot.append(q)
        radial = q - (kc + t_end * (0.004 * k / 36))
        knot_n.append(radial.normalized() if radial.length > 1e-6 else end_n)

    def tail(p0, s0, lateral):
        """A tail lying on the saya: it follows the centreline's own drift."""
        out, nrm_out = [], []
        c0 = centre(s0)[0]
        for k in range(1, 25):
            f = k / 24
            out.append(p0 + (centre(s0 + tail_len * f)[0] - c0) + side * (lateral * f))
            nrm_out.append(end_n)
        return out, nrm_out
    tail_a, tn_a = tail(knot[-1], s_end + 0.004, 0.004)
    tail_b, tn_b = tail(pb[-1] + end_n * (thick * 0.6), s_end, -0.004)
    # One path: tail B (reversed) -> half B (reversed) -> hole -> half A -> knot -> tail A.
    path = list(reversed(tail_b)) + list(reversed(pb)) + lead_minus + thru + lead_plus + pa + knot + tail_a
    norms = (list(reversed(tn_b)) + list(reversed(nb_)) + [up_out] * (len(lead_minus) + len(thru) + len(lead_plus))
             + na + knot_n + tn_a)
    # Normals along the hole run follow the fin (the cord lies flat in the hole).
    prof = L.lens2d(width, thick, 10, 3.0)
    obj = sweep_with_normals("Sageo", path, norms, prof, mat, [0.0] * len(path), [(1.0, 1.0)] * len(path))
    total = sum((path[i + 1] - path[i]).length for i in range(len(path) - 1))
    return obj, total


def build_saya(b, P, blade: Blade, x_mouth, mats, katana, aikuchi, fuchi_r):
    disp_y = 0.075 if katana else 0.065
    disp = Vector((0, disp_y, 0))
    # Saya centreline: follow the blade's centre arc (linear-taper width).
    s0 = -(blade.x_m - x_mouth)
    s1 = blade.arc + (0.024 if katana else 0.020)
    wall_h = 0.0048
    wall_w = 0.0090 if not aikuchi else 0.0072

    def centre(s):
        sc = min(max(s, 0.0), blade.arc)
        m, t, n = blade.frame(sc)
        if s > blade.arc:
            m = m + t * (s - blade.arc)
        if s < 0:
            m = m + t * s
        wb = blade.width_body(min(max(s, 0.0), blade.s_yok))
        return m - n * (wb / 2.0), t, n

    def dims(s):
        u = min(max(s, 0.0) / blade.arc, 1.0)
        if aikuchi:
            h = fuchi_r[1] * (1 - 0.18 * u)
            w = fuchi_r[0] * (1 - 0.15 * u)
        else:
            h = (blade.W0 / 2 + wall_h) * (1 - 0.22 * u)
            w = (blade.t0 / 2 + wall_w) * (1 - 0.20 * u)
        return w, h

    def ring(s, scale=1.0, sides=40):
        c, t, n = centre(s)
        w, h = dims(s)
        y_axis = Vector((0, 1, 0))
        pts = []
        for k in range(sides):
            a = math.tau * k / sides
            ca, sa = math.cos(a), math.sin(a)
            yy = w * scale * math.copysign(abs(ca) ** (2 / 2.3), ca)
            zz = h * scale * math.copysign(abs(sa) ** (2 / 2.3), sa)
            pts.append(c + y_axis * yy + n * zz + disp)
        return pts

    L_koi = 0.016 if not aikuchi else 0.010
    L_koj = 0.024 if katana else 0.018
    body = []
    s = s0 + L_koi - 0.0002
    body_end = s1 - L_koj + 0.0002
    steps = int((body_end - s) / 0.01) + 1
    for i in range(steps + 1):
        body.append(ring(s + (body_end - s) * i / steps))
    b.add(L.loft("Saya", body, mats["saya"], closed=True, chunk=0.2), group="saya")
    # Koiguchi: outer band, front annulus and the blade slot going inward.
    slot_sec, _z, _s = blade.section(0.0)
    slot = [(y * 1.25 + math.copysign(0.0008, y) if abs(y) > 1e-6 else 0.0, h) for y, h in slot_sec]

    def slot_ring(s, sides=40):
        c, t, n = centre(s)
        pts2 = []
        # resample the slot polygon by angle to ``sides`` points (CCW like ring())
        ch_ = blade.W0 / 2
        poly = [(y, h - ch_) for y, h in slot]
        for k in range(sides):
            a = math.tau * k / sides
            d = Vector((math.cos(a), math.sin(a)))
            best = None
            for i in range(len(poly)):
                p1 = Vector(poly[i])
                p2 = Vector(poly[(i + 1) % len(poly)])
                e = p2 - p1
                den = d.x * (-e.y) - d.y * (-e.x)
                if abs(den) < 1e-12:
                    continue
                tt = (p1.x * (-e.y) - p1.y * (-e.x)) / den
                uu = (d.x * p1.y - d.y * p1.x) / den
                if tt > 0 and -1e-9 <= uu <= 1 + 1e-9 and (best is None or tt < best):
                    best = tt
            r = best or 0.001
            yy, zz = d.x * r * 1.02, d.y * r * 1.02
            pts2.append(c + Vector((0, 1, 0)) * yy + n * zz + disp)
        return pts2

    koi_rings = [ring(s0 + L_koi, 1.0), ring(s0 + 0.0008, 1.0), ring(s0, 0.97), slot_ring(s0),
                 slot_ring(s0 + 0.03)]
    b.add(L.loft("Koiguchi", koi_rings, mats["horn"], closed=True, cap_start=True, cap_end=True, chunk=0.0,
                 sharp_angle=45.0), group="saya")
    koj = [ring(s1 - L_koj), ring(s1 - 0.004), ring(s1 - 0.0012, 0.93), ring(s1, 0.72)]
    b.add(L.loft("Kojiri", koj, mats["horn"], closed=True, chunk=0.0, sharp_angle=45.0), group="saya")
    # Kurikata: a fin on the omote (-Y) face toward the ha side, hole along Y.
    s_k = s0 + (0.105 if katana else 0.075)
    c, t, n = centre(s_k)
    w, h = dims(s_k)
    fin_len, fin_h, fin_t = (0.030 if katana else 0.025), 0.0105, 0.0072
    outline = []
    for k in range(40):
        a = math.pi * k / 39
        outline.append((fin_len / 2 * math.cos(a), -0.002 + fin_h * math.sin(a) ** 0.7))
    outline.append((-fin_len / 2, -0.004))
    outline.append((fin_len / 2, -0.004))
    outline = list(reversed(outline))
    hole = [(0.0048 * math.cos(math.tau * k / 24), 0.0045 + 0.0023 * math.sin(math.tau * k / 24))
            for k in range(24)]
    hole = list(reversed(hole))
    fin = L.extrude_outline("Kurikata", [list(reversed(outline)), hole], fin_t, 0.0012, mats["horn"], "XZ", 0.0)
    ang = math.radians(135.0)
    R = Matrix.Rotation(ang, 4, "X")
    base_pt = c + disp + Vector((0, -w * 0.72, 0)) + n * (-h * 0.62)
    L.transform(fin, Matrix.Translation(base_pt) @ R)
    b.add(fin, group="saya")
    hole_c = base_pt + (R @ Vector((0, 0, 0.0045)))
    normal_dir = (R @ Vector((0, 1, 0))).normalized()
    for side in (-1, 1):
        ring_o = L.tube("Shitodome", [(-0.0006, 0.0060, 0.0036), (-0.0002, 0.0062, 0.0038),
                                      (0.0002, 0.0062, 0.0038), (0.0006, 0.0060, 0.0036)],
                        mats["gold"], sides=28, max_seg=0.0, chunk=0.0)
        L.transform(ring_o, Matrix.Translation(hole_c + normal_dir * side * (fin_t / 2 + 0.0001)) @ R @
                    Matrix.Rotation(math.radians(90), 4, "Z"))
        b.add(ring_o, group="saya", lod_drop=2)
    # Sageo: one continuous braided cord through the kurikata.
    a_k = math.atan2(-0.62, -0.72)   # the kurikata's angle round the saya section
    # Wrap span, turns (a multiple of 1/2 so both halves meet at the knot)
    # and tail length scale with the saya.
    span, turns, tail_len = {True: (0.21, 5.0, 0.085)}.get(katana, (0.085, 2.5, 0.05) if aikuchi else
                                                              (0.15, 4.0, 0.07))
    sageo, length = build_sageo(centre, dims, disp, s_k, a_k, hole_c, normal_dir, fin_t, mats["sageo"],
                                span, turns, tail_len)
    b.add(sageo, group="saya")
    b.notes["sageo"] = {"length_m": round(length, 3), "width_m": 0.009,
                        "tie": "through the kurikata; crossing spiral down the saya, knot and two tails"}
    # Group registration: origin at the mouth centre in display space.
    c0, t0, n0 = centre(s0)
    origin = c0 + disp
    b.groups["saya"]["origin"] = origin
    # Review renders show the saya below the sword so both silhouettes read.
    b.groups["saya"]["display"] = Vector((0.0, 0.0, -0.07))
    b.socket("Koiguchi", tuple(origin), x=tuple(t0), z=tuple(n0), group="saya")
    b.socket("Kurikata", tuple(hole_c), group="saya")


def make_builder(wid):
    def fn(b: L.Build):
        spec = S.WEAPONS[wid]
        b.group("saya", spec["extra_assets"][0], offset=(0.0, 0.45, 0.0))
        build_sword(b, wid)
    return fn


if __name__ == "__main__":
    L.run({wid: make_builder(wid) for wid in S.by_builder("create_runtime_weapon_nihonto.py")})
