"""Build the runtime kusarigama (2): Otane's farm sickle on a chain.

Run:  blender -b --factory-startup --python scripts/art/create_runtime_weapon_kusarigama.py

``SM_Weapon_02``: a 45 cm oval kashi handle (sweat-dark at the grip) with an
iron ferrule, butt cap and chain ring (kan); a 17.5 cm single-bevel (kataba)
sickle blade with a rounded 4.8 mm spine, a black-forged (kurouchi) flat and
a 6 mm stone-ground bevel whose bright hagane band runs along the edge.

``SM_Weapon_02_Chain``: the 2.7 m chain as its own runtime mesh, so Unreal
can drive it with physics from the handle's ``Chain_Anchor`` socket. Its rest
pose is a loose flat coil as it lies on a floor: ~155 hand-forged oval links
(4.2 mm wire), each within +-10 % of the nominal size, a little out of round,
with a forge-weld swelling and its own lean, alternating flat and on edge,
and an octagonal iron fundō at the inner end.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import create_runtime_weapon_lib as L  # noqa: E402
import create_runtime_weapon_specs as S  # noqa: E402


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


def link_mesh(name, centre, tangent, width_dir, length, width, wire, mat, seed):
    """A hand-forged oval link: a stadium path a little out of round, the
    wire swelling where the ends were forge-welded (on one long side)."""
    t = tangent.normalized()
    n = (width_dir - t * width_dir.dot(t)).normalized()
    half_l = length / 2 - wire / 2
    r = width / 2 - wire / 2
    straight = max(half_l - r, 0.0)
    path = []
    seg = 8
    for side in (1, -1):
        for k in range(seg):
            a = -math.pi / 2 + math.pi * k / seg
            if side < 0:
                a += math.pi
            cx = straight * side
            wob = 1.0 + 0.045 * math.sin(2 * a + 6.0 * hash01(seed, 1)) + 0.03 * math.sin(3 * a + 6.0 * hash01(seed, 2))
            path.append(centre + t * (cx + r * math.cos(a) * wob) + n * (r * math.sin(a) * wob))
    weld = hash01(seed, 3) * 0.5 + 0.25          # along the path, on a long side

    def scale(u):
        d = min(abs(u - weld), 1 - abs(u - weld))
        s = 1.0 + 0.16 * math.exp(-(d / 0.05) ** 2)
        return (s, s * 0.92)
    return L.sweep(name, path, L.circle2d(wire / 2, 7), mat, up=tuple(t.cross(n)), closed_path=True, chunk=0.0,
                   sharp_angle=None, scale=scale)


def build_kusarigama(b: L.Build):
    spec = S.WEAPONS[2]
    kashi = L.mat_wood("M_Kama_Handle", tone="kashi", value=0.92, rough=(0.46, 0.70), mapping="uv", wear=0.5,
                       dirt=0.5, rays=1.1, grips=((-0.10, 0.20),))
    iron = L.mat_iron("M_Kama_Iron", oxide=(0.024, 0.021, 0.018), tsuchime=0.8, rust=0.35, polish_edges=0.4,
                      rough=0.55, metal=0.35, forge_scale=0.6)
    chain_iron = L.mat_iron("M_Kama_Chain", oxide=(0.026, 0.023, 0.020), rust=0.35, polish_edges=0.8, rough=0.50,
                            metal=0.45, scale=0.5, forge_scale=1.0, tsuchime=0.6)
    kurouchi = L.mat_iron("M_Kama_Kurouchi", oxide=(0.016, 0.015, 0.014), tsuchime=1.3, rust=0.22,
                          polish_edges=0.25, rough=0.60, metal=0.3, forge_scale=1.3)
    bevel = L.mat_ground_bevel("M_Kama_Bevel")
    x_butt = -0.10
    x_top = x_butt + spec["handle"]
    # Handle: oval, swelling a little toward the butt, tapering to the head.
    secs = [(x_butt + 0.012, 0.0124, 0.0146), (x_butt + 0.05, 0.0130, 0.0153), (x_butt + 0.20, 0.0125, 0.0147),
            (x_top - 0.05, 0.0119, 0.0139), (x_top - 0.004, 0.0117, 0.0137)]
    b.add(L.tube("Handle", secs, kashi, sides=32, max_seg=0.02, chunk=0.25))
    b.add(L.tube("Ferrule", [(x_top - 0.034, 0.0126, 0.0146), (x_top - 0.032, 0.0132, 0.0152),
                             (x_top - 0.002, 0.0132, 0.0152), (x_top, 0.0125, 0.0145)],
                 iron, sides=32, max_seg=0.01, chunk=0.0, sharp_angle=45.0))
    b.add(L.tube("Butt_Cap", [(x_butt, 0.0106, 0.0122), (x_butt + 0.002, 0.0130, 0.0150),
                              (x_butt + 0.016, 0.0133, 0.0154), (x_butt + 0.018, 0.0127, 0.0148)],
                 iron, sides=32, max_seg=0.01, chunk=0.0, sharp_angle=45.0))
    # Rivet (mekugi) through the head that holds the blade's tang.
    for side in (-1, 1):
        rv = L.tube(f"Tang_Rivet_{side:+d}", [(0.0, 0.0030, 0.0030), (0.0009, 0.0028, 0.0028),
                                              (0.0016, 0.0016, 0.0016)], iron, sides=16, max_seg=0.0, chunk=0.0)
        L.transform(rv, Matrix.Translation((x_top - 0.018, side * 0.0131, 0.0)) @ L.rot("Z", 90 * side))
        b.add(rv, lod_drop=2)
    # Butt ring (kan) for the chain.
    ring_c = Vector((x_butt - 0.011, 0.0, 0.0))
    ring_path = [ring_c + Vector((0.0085 * math.cos(math.tau * k / 24), 0.0, 0.0085 * math.sin(math.tau * k / 24)))
                 for k in range(24)]
    b.add(L.sweep("Butt_Ring", ring_path, L.circle2d(0.0024, 8), iron, up=(0, 1, 0), closed_path=True, chunk=0.0,
                  sharp_angle=None))
    # Sickle blade: lofted down -Z from the head; spine on +X, edge toward -X
    # (facing the wielder); ground bevel on the omote (-Y), flat ura at +Y.
    rings, bev_attr = [], []
    n_s = 52
    blade_len = spec["blade"]
    for i in range(n_s):
        u = i / n_s
        z = 0.010 - (blade_len + 0.010) * u
        x_sp = x_top - 0.004 - 0.062 * u ** 1.7
        w = 0.040 * (1 - u ** 1.6) ** 0.8 + 0.0014
        t = 0.0048 * (1 - u) ** 0.55 + 0.0008          # spine thickness
        t_sh = 0.0021 * (1 - u) ** 0.4 + 0.0005        # thickness at the bevel shoulder
        bev = min(0.0062, w * 0.42)
        x_e = x_sp - w
        r_sp = min(t * 0.35, 0.0012)
        sec = [(x_sp, -t / 2 + r_sp), (x_sp + r_sp * 0.55, 0.0), (x_sp, t / 2 - r_sp),
               (x_sp - min(0.004, w * 0.2), t / 2), (x_e + bev, -t / 2 + t_sh),
               (x_e + bev * 0.45, -t / 2 + t_sh * 0.45), (x_e, -t / 2), (x_e + min(0.004, w * 0.2), -t / 2),
               (x_sp - w * 0.5, -t / 2)]
        # The ground bevel is on the omote (-Y, the wielder's right); the
        # flat ura faces +Y (the mirrored ring's normals are recomputed).
        rings.append([Vector((xx, -yy, z)) for xx, yy in sec])
    bev_cols = {4: 1.0, 5: 0.45, 6: 0.0}
    tip = Vector((x_top - 0.004 - 0.062 - 0.0014, 0.0012, -blade_len - 0.012))
    blade = L.loft("Kama_Blade", rings, kurouchi, closed=True, cap_start=True, tip_end=tip, sharp_cols=(4, 6),
                   chunk=0.2, sharp_angle=None, point_attrs={"bev_d": lambda i, j: bev_cols.get(j, 1.0)})
    blade.data.materials.append(bevel)
    n = len(rings[0])
    for poly in blade.data.polygons:
        cols = {v % n for v in poly.vertices if v < n_s * n}
        if cols and cols <= {4, 5, 6} and len(cols) >= 2:
            poly.material_index = 1
    b.add(blade)
    b.socket("Grip_R", (0.0, 0.0, 0.0))
    b.socket("Grip_L", (0.06, 0.23, -0.03), x=(0, 0, -1), z=(1, 0, 0))
    b.socket("Muzzle", tuple(tip), x=(0, 0, -1), z=(1, 0, 0))
    b.socket("Chain_Anchor", tuple(ring_c))
    build_chain(b, spec, ring_c, chain_iron, iron)
    b.notes.update({"handle_m": spec["handle"], "blade_m": blade_len, "bevel_m": 0.0062, "spine_m": 0.0056})


def build_chain(b: L.Build, spec, ring_c, chain_iron, iron):
    """The chain as a loose flat coil on the floor (z = floor), outer end the
    anchor lead, fundō at the centre."""
    pitch = spec["link_pitch"]
    wire = spec["link_wire"]
    link_w = 0.0145
    floor = -0.30
    cx, cy = 0.16, 0.30
    # Per-link inner lengths (+-10 %) define the spacing of link centres.
    total = spec["chain"]
    lengths = []
    acc = 0.0
    k = 0
    while acc < total - pitch * 0.5:
        p = pitch * (1.0 + 0.10 * jit(k, 11))
        lengths.append(p)
        acc += p
        k += 1
    scale_l = total / acc
    lengths = [p * scale_l for p in lengths]
    count = len(lengths)
    # Centre positions: a straight lead in from the anchor side, then an
    # irregular inward spiral (spacing > the link width, no self-crossing).
    lead = 0.16
    r0, r1 = 0.175, 0.055
    spiral_len = total - lead
    turns_est = spiral_len / (math.tau * (r0 + r1) / 2)

    def path_point(s):
        if s < lead:
            f = s / lead
            start = Vector((cx - r0 - 0.012, cy - lead, 0.0))
            end = Vector((cx - r0, cy, 0.0))
            return start.lerp(end, f) + Vector((0.006 * math.sin(math.pi * f), 0.0, 0.0))
        # arc length -> angle on a spiral r(theta) = r0 - (r0 - r1) theta / theta_max
        f = (s - lead) / spiral_len
        theta_max = math.tau * turns_est
        th = theta_max * (1 - math.sqrt(1 - f * (1 - (r1 / r0) ** 2))) / (1 - r1 / r0) if r0 != r1 else f * theta_max
        th = min(th, theta_max)
        rr = r0 - (r0 - r1) * th / theta_max
        rr += 0.004 * math.sin(2.3 * th + 0.4) + 0.0025 * math.sin(5.1 * th + 1.1)
        a = math.pi - th
        return Vector((cx + rr * math.cos(a), cy + rr * math.sin(a), 0.0))
    s_c = []
    acc = lengths[0] / 2
    for i in range(count):
        s_c.append(acc)
        if i + 1 < count:
            acc += (lengths[i] + lengths[i + 1]) / 2
    # Resample the target curve finely, then walk it by chord length so the
    # link centres sit the right distance apart.
    fine = [path_point(total * i / 4000) for i in range(4001)]
    cum = [0.0]
    for a_, b_ in zip(fine[:-1], fine[1:]):
        cum.append(cum[-1] + (b_ - a_).length)
    scale_c = total / cum[-1]

    def at(s):
        s = s / scale_c
        j = 0
        lo, hi = 0, len(cum) - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if cum[mid] < s:
                lo = mid + 1
            else:
                hi = mid
        j = max(1, lo)
        f = (s - cum[j - 1]) / max(cum[j] - cum[j - 1], 1e-9)
        return fine[j - 1].lerp(fine[j], min(max(f, 0.0), 1.0))
    centres = [at(s) for s in s_c]
    up = Vector((0.0, 0.0, 1.0))
    for i in range(count):
        c = centres[i]
        a = centres[max(i - 1, 0)]
        d_ = centres[min(i + 1, count - 1)]
        tan = (d_ - a).normalized()
        side = up.cross(tan).normalized()
        flat = i % 2 == 0
        L_out = lengths[i] + 2 * wire
        W_out = link_w * (1.0 + 0.06 * jit(i, 12))
        w_i = wire * (1.0 + 0.05 * jit(i, 13))
        roll = math.radians(9.0 if flat else 14.0) * jit(i, 14)
        yaw = math.radians(4.0) * jit(i, 15)
        tan = (tan * math.cos(yaw) + side * math.sin(yaw)).normalized()
        side = up.cross(tan).normalized()
        if flat:
            wd = side * math.cos(roll) + up * math.sin(roll)
            z = floor + w_i / 2 + (W_out / 2 - w_i / 2) * abs(math.sin(roll)) * 0.6
        else:
            wd = up * math.cos(roll) + side * math.sin(roll)
            z = floor + (W_out / 2) * math.cos(roll) * 0.94
        centre = Vector((c.x, c.y, z))
        b.add(link_mesh(f"Chain_Link_{i:03d}", centre, tan, wd, L_out, W_out, w_i, chain_iron, i), group="chain")
    # Fundō: octagonal iron weight lying on a flat at the inner end, eye first.
    last = centres[-1]
    prev = centres[-2]
    dirv = (last - prev).normalized()
    fl, fd = spec["fundo"]
    eye_c = Vector((last.x, last.y, 0.0)) + dirv * (lengths[-1] / 2 + wire + 0.004)
    side = up.cross(dirv).normalized()
    eye = [eye_c + dirv * (0.0065 * math.cos(math.tau * k / 20)) + up * (0.0065 * math.sin(math.tau * k / 20))
           for k in range(20)]
    eye = [Vector((p.x, p.y, p.z + floor + fd / 2)) for p in eye]
    b.add(L.sweep("Fundo_Eye", eye, L.circle2d(0.0022, 8), iron, up=tuple(side), closed_path=True, chunk=0.0,
                  sharp_angle=None), group="chain")
    body0 = eye_c + dirv * 0.009
    fr = []
    for dx, sc in ((0.0, 0.55), (0.003, 0.9), (0.008, 1.0), (fl - 0.008, 1.0), (fl - 0.003, 0.9), (fl, 0.55)):
        pts2 = L.polygon2d(8, fd / 2 * sc, 0.0015, 2, rot=math.pi / 8)
        cen = body0 + dirv * dx
        fr.append([Vector((cen.x, cen.y, floor + fd / 2)) + side * a_ + up * b_ for a_, b_ in pts2])
    b.add(L.loft("Fundo", fr, iron, closed=True, chunk=0.0, sharp_angle=40.0), group="chain")
    anchor = Vector((centres[0].x, centres[0].y, floor + wire / 2)) - (centres[1] - centres[0]).normalized() * (
        lengths[0] / 2 + wire)
    b.groups["chain"]["origin"] = anchor
    b.socket("Anchor", tuple(anchor), group="chain")
    b.socket("Fundo", tuple(body0 + dirv * (fl / 2) + Vector((0, 0, floor + fd / 2))), group="chain")
    modelled = sum(lengths)
    b.notes["chain"] = {"asset": "SM_Weapon_02_Chain", "links": count, "modelled_m": round(modelled, 3),
                        "link": {"pitch_m": pitch, "pitch_variance": 0.10, "wire_m": wire, "outer_width_m": link_w},
                        "rest_pose": "loose flat coil on the floor; Unreal drives it from Chain_Anchor",
                        "fundo_m": [fl, fd]}


def builder(b: L.Build):
    b.group("chain", "SM_Weapon_02_Chain", offset=(0.0, 0.8, 0.0), lay=False, floor=True)
    build_kusarigama(b)


if __name__ == "__main__":
    L.run({2: builder})
