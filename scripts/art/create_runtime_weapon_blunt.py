"""Build the runtime blunt weapons: kanabō (6) and forge hammer (8).

Run:  blender -b --factory-startup --python scripts/art/create_runtime_weapon_blunt.py [-- --only 6]

* Kanabō (金砕棒): a 1.52 m octagonal evergreen-oak club that tapers by a
  third from the head (8.8 cm across the flats) to the grip, densely shod
  with ~230 hand-forged pyramidal iron studs (hoshi) in staggered rows every
  3.3 cm, each stud a little different in size, height, lean and twist, with
  iron-tannate and rust staining bled into the oak round every stud and band;
  iron bands, a domed cap, an iron butt with a ring and a braided tekubi cord
  loop, and a shingled leather grip wrap (story bible ch08: oak body, forged
  iron studs, iron-bound butt). Kanabō dimensions are a documented gap in the
  museum records (plan 3.8), so they are labelled design values.
* Forge hammer (向こう鎚, the striker's sledge of ch05): a 16.5 cm forged head
  under black forge scale, both striking faces mushroomed into a 2-3 mm lip
  with chips and worked bright by use, on an 80 cm oval kashi handle that
  tapers into the eye, with grip grime and an iron wedge in the end grain.
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
    """Deterministic value in [-1, 1)."""
    return hash01(*k) * 2.0 - 1.0


def smooth01(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def octagon_ring(x, r_flats, corner, seg=3, cz=0.0):
    pts2 = L.polygon2d(8, r_flats, corner, seg, rot=math.pi / 8)
    return [(x, a, cz + b) for a, b in pts2]


def forged_stud(name, centre, nrm, along, base, height, twist, lean, apex, mat):
    """A hand-forged pyramidal stud: square in plan with slightly swollen
    faces, a flattened collar where it was driven home and a rounded apex.
    ``along`` is the body axis; the stud is set into the wood by 2 mm."""
    nrm = nrm.normalized()
    t1 = (along - nrm * along.dot(nrm)).normalized()
    t2 = nrm.cross(t1)
    ct, st = math.cos(twist), math.sin(twist)
    a1 = t1 * ct + t2 * st
    a2 = -t1 * st + t2 * ct
    axis = (nrm + a1 * lean[0] + a2 * lean[1]).normalized()
    rings = []
    # (height fraction, plan scale)
    for hz, sc in ((-0.18, 1.02), (0.0, 1.03), (0.07, 0.94), (0.30, 0.70), (0.55, 0.44), (0.78, 0.21),
                   (0.92, 0.08)):
        ring = []
        h = hz * height
        for k in range(8):
            ang = math.pi / 4 * k
            corner = k % 2 == 0
            # corners at 0, 90, 180, 270 degrees; mid-edge points swell out
            r = base / 2 * sc * (1.41 if corner else 1.0 * 1.06)
            ca, sa = math.cos(ang), math.sin(ang)
            off = a1 * (ca * r) + a2 * (sa * r)
            ring.append(centre + axis * h + off + (a1 * apex[0] + a2 * apex[1]) * max(hz, 0.0) * height)
        rings.append(ring)
    tip = centre + axis * height + (a1 * apex[0] + a2 * apex[1]) * height
    return L.loft(name, rings, mat, closed=True, cap_start=True, tip_end=tip, chunk=0.0, sharp_angle=62.0)


def build_kanabo(b: L.Build):
    spec = S.WEAPONS[6]
    total = spec["length"]
    flats_max, flats_min = spec["head_flats"]
    x_b = -0.25
    # The butt ring for the tekubi cord stands 1.9 cm proud of the butt; the
    # 1.52 m design length runs from the ring to the domed cap.
    x_top = x_b + total - 0.0190
    # Evergreen oak (kashi) darkened by handling and smoke, stained round the iron.
    oak = L.mat_wood("M_Kanabo_Oak", tone="smoked", value=1.12, rough=(0.46, 0.70), mapping="uv",
                     wear=0.35, dirt=0.7, tool=0.8, rays=1.0, iron_bleed=1.0)
    iron = L.mat_iron("M_Kanabo_Iron", oxide=(0.024, 0.020, 0.017), tsuchime=1.3, rust=0.45, polish_edges=0.35,
                      rough=0.56, metal=0.3, forge_scale=0.8)
    stud_iron = L.mat_iron("M_Kanabo_Studs", oxide=(0.020, 0.017, 0.015), tsuchime=0.8, rust=0.6, polish_edges=0.12,
                           rough=0.58, metal=0.3, forge_scale=0.9, scale=0.5)
    leather = L.mat_leather("M_Kanabo_GripLeather", tint=(0.55, 0.40, 0.30), value=0.55, tile=0.10, uv="uv",
                            rough_bias=0.22, soil=0.8)
    cord = L.mat_braid("M_Kanabo_TekubiCord", (0.075, 0.050, 0.032), 1.1, kind="round", soil=0.5)
    # Butt: iron-bound with a ring for the tekubi cord.
    b.add(L.tube("Ishizuki", [(x_b, 0.0150, 0.0150), (x_b + 0.003, 0.0200, 0.0200), (x_b + 0.030, 0.0212, 0.0212),
                              (x_b + 0.036, 0.0230, 0.0230), (x_b + 0.040, 0.0210, 0.0210)],
                 iron, sides=40, max_seg=0.006, chunk=0.0, sharp_angle=45.0))
    eye_c = Vector((x_b - 0.010, 0.0, 0.0))
    b.add(L.tube("Butt_Eye", [(x_b - 0.004, 0.0040, 0.0040), (x_b + 0.002, 0.0055, 0.0055)], iron, sides=20,
                 max_seg=0.0, chunk=0.0))
    ring_pts = [eye_c + Vector((0.0085 * math.cos(math.tau * k / 28), 0.0, 0.0085 * math.sin(math.tau * k / 28)))
                for k in range(28)]
    b.add(L.sweep("Butt_Ring", ring_pts, L.circle2d(0.0022, 8), iron, up=(0, 1, 0), closed_path=True, chunk=0.0,
                  sharp_angle=None))
    # Tekubi cord: a braided loop hung on the ring's lower wire; both strands
    # run together through a seizing, then open into the hand loop.
    loop = []
    n_l = 96
    z_top = eye_c.z - 0.0085 + 0.0022 + 0.0030
    for i in range(n_l):
        a = math.tau * i / n_l
        v = (1 - math.cos(a)) / 2          # 0 on the ring, 1 at the bottom of the loop
        hw = 0.0036 + 0.028 * smooth01((v - 0.22) / 0.50)
        side = math.sin(a) / math.sqrt(math.sin(a) ** 2 + 0.02)
        loop.append(eye_c + Vector((-0.0035 * v + 0.0012 * math.sin(2 * a), hw * side, z_top - eye_c.z - 0.118 * v)))
    b.add(L.sweep("Tekubi_Cord", loop, L.circle2d(0.0030, 8), cord, up=(1, 0, 0), closed_path=True, chunk=0.2,
                  sharp_angle=None), lod_drop=99)
    z_s0 = z_top - 0.118 * 0.10
    seiz = L.tube("Tekubi_Seizing", [(0.0, 0.0074, 0.0042), (0.0015, 0.0084, 0.0050), (0.0125, 0.0084, 0.0050),
                                     (0.014, 0.0074, 0.0042)], cord, sides=20, max_seg=0.003, chunk=0.0)
    L.transform(seiz, Matrix.Translation((eye_c.x - 0.0006, 0.0, z_s0)) @ L.rot("Y", 90))
    b.add(seiz, lod_drop=2)
    # Grip core and a shingled leather strap wound over it.
    grip_x0, grip_x1 = x_b + 0.038, x_b + 0.40

    def grip_r(x):
        return 0.0190 + 0.0012 * (x - grip_x0) / (grip_x1 - grip_x0)
    b.add(L.tube("Grip_Core", [(grip_x0, grip_r(grip_x0), grip_r(grip_x0)), (grip_x1, grip_r(grip_x1),
                                                                             grip_r(grip_x1))],
                 oak, sides=32, max_seg=0.02))
    b.add(L.strip_wrap("Grip_Strap", grip_x0 + 0.003, grip_x1 - 0.004, grip_r, 0.026, 0.0018, 0.28, leather,
                       jitter=0.10, seed=0.7))
    # Octagonal body: a third narrower at the grip than at the head.
    body_x0 = x_b + 0.435
    body_x1 = x_top - 0.028

    def flats_at(x):
        t = min(max((x - body_x0) / (body_x1 - body_x0), 0.0), 1.0)
        return flats_min + (flats_max - flats_min) * min(1.0, t / 0.84) ** 0.85 - 0.003 * max(0.0, (t - 0.84) / 0.16)
    rings = []
    steps = 120
    for i in range(steps + 1):
        x = body_x0 + (body_x1 - body_x0) * i / steps
        rings.append(octagon_ring(x, flats_at(x) / 2, 0.0026, 2))
    b.add(L.loft("Body", rings, oak, closed=True, chunk=0.3, sharp_angle=40.0))

    def band(name, x0, x1, extra=0.0022):
        rs = []
        for x, e in ((x0, extra * 0.5), (x0 + 0.002, extra), (x1 - 0.002, extra), (x1, extra * 0.5)):
            rs.append(octagon_ring(x, flats_at(min(max(x, body_x0), body_x1)) / 2 + e, 0.003, 2))
        return L.loft(name, rs, iron, closed=True, chunk=0.0, sharp_angle=40.0)

    r_hg = flats_at(body_x0) / 2
    b.add(L.tube("Hachigane_Grip", [(x_b + 0.398, 0.0226, 0.0226), (x_b + 0.402, r_hg * 0.86, r_hg * 0.86),
                                    (x_b + 0.438, r_hg + 0.0022, r_hg + 0.0022),
                                    (x_b + 0.444, r_hg + 0.0008, r_hg + 0.0008)],
                 iron, sides=40, max_seg=0.01, chunk=0.0, sharp_angle=45.0))
    x_mid = body_x0 + 0.46
    b.add(band("Band_Mid", x_mid, x_mid + 0.034))
    b.add(band("Band_Top", body_x1 - 0.060, body_x1 - 0.034, 0.0020))
    # Domed top cap.
    fr = flats_max / 2 - 0.003
    cap = []
    for x, s_ in ((body_x1 - 0.004, 1.03), (body_x1 + 0.004, 1.04), (x_top - 0.010, 1.0), (x_top - 0.004, 0.85),
                  (x_top - 0.001, 0.55), (x_top, 0.2)):
        cap.append(octagon_ring(x, fr * s_ + 0.0016, 0.003, 2))
    b.add(L.loft("Cap", cap, iron, closed=True, chunk=0.0, sharp_angle=40.0))
    # Studs: staggered rows every 3.3 cm on all eight faces, each forged by hand.
    pitch = 0.033
    xs0, xs1 = body_x0 + 0.030, body_x1 - 0.078
    studs = []
    along = Vector((1.0, 0.0, 0.0))
    for face in range(8):
        a = math.tau * face / 8
        nrm = Vector((0.0, math.cos(a), math.sin(a)))
        tan = Vector((0.0, -math.sin(a), math.cos(a)))
        row = 0
        x = xs0 + (pitch / 2 if face % 2 else 0.0)
        while x < xs1:
            if x_mid - 0.024 < x < x_mid + 0.058:
                x += pitch
                row += 1
                continue
            xj = x + 0.0022 * jit(face, row, 1)
            r = flats_at(xj) / 2
            gain = 0.86 + 0.14 * min(1.0, (xj - body_x0) / 0.55)
            base = 0.0100 * gain * (1.0 + 0.10 * jit(face, row, 2))
            height = 0.0115 * gain * (1.0 + 0.15 * jit(face, row, 3))
            c = Vector((xj, 0.0, 0.0)) + nrm * r + tan * (0.0014 * jit(face, row, 4))
            stud = forged_stud(f"Stud_{face}_{row:02d}", c, nrm, along, base, height,
                               math.radians(12.0) * jit(face, row, 5),
                               (0.07 * jit(face, row, 6), 0.07 * jit(face, row, 7)),
                               (0.06 * jit(face, row, 8), 0.06 * jit(face, row, 9)), stud_iron)
            studs.append(stud)
            x += pitch
            row += 1
    count = len(studs)
    b.add(L.join(studs, "Studs"))
    b.notes.update({"overall_m": total, "studs": count, "stud_row_pitch_m": pitch, "across_flats_max_m": flats_max,
                    "across_flats_grip_m": flats_min, "taper": round(1 - flats_min / flats_max, 3), "butt_x": x_b,
                    "basis": "design values (kanabō size records are a documented gap)"})
    b.socket("Grip_R", (0.0, 0.0, 0.0))
    b.socket("Grip_L", (-0.13, 0.0, 0.0))
    b.socket("Muzzle", (body_x0 + 0.82 * (body_x1 - body_x0), 0.0, flats_max / 2 + 0.011), x=(0, 0, 1), z=(1, 0, 0))


def build_forge_hammer(b: L.Build):
    spec = S.WEAPONS[8]
    handle_len = spec["handle"]
    hl, hx, hy = spec["head"]
    x_butt = -0.20
    x_head = x_butt + handle_len - hx / 2 - 0.0045

    def struck(nb):
        # Both striking faces (the head is lofted along Z) and the lip round them.
        _x, _y, z = nb.vxyz(nb.obj())
        g = nb.geo()
        _nx, _ny, nz = nb.vxyz(g.outputs["Normal"])
        face = nb.mul(nb.smoothstep(nb.absf(nz), 0.80, 0.93), nb.smoothstep(nb.absf(z), hl / 2 - 0.0045, hl / 2 - 0.0018))
        lip = nb.mul(nb.smoothstep(nb.absf(z), hl / 2 - 0.0035, hl / 2 - 0.0010),
                     nb.smoothstep(nb.noise(nb.obj(), 900.0, 2.0, 0.5), 0.45, 0.60))
        return nb.maxi(face, nb.mul(lip, 0.8))

    steel = L.mat_iron("M_Hammer_Head", oxide=(0.017, 0.016, 0.015), tsuchime=0.45, rust=0.12, polish_edges=0.5,
                       rough=0.62, metal=0.35, forge_scale=2.2, bright=struck)
    kashi = L.mat_wood("M_Hammer_Handle", tone="kashi", value=0.95, rough=(0.46, 0.70), mapping="uv", wear=0.45,
                       dirt=0.45, rays=1.2, grips=((x_butt, x_butt + 0.16), (x_head - 0.30, x_head - 0.13)))
    wedge_m = L.mat_iron("M_Hammer_Wedge", oxide=(0.03, 0.026, 0.022), rust=0.35, polish_edges=0.3, rough=0.55)
    # Head: lofted along Z; square with forged, rounded arrises; a swell round
    # the eye; both faces mushroomed into an uneven, chipped lip.
    prof = [(-hl / 2, 0.955), (-hl / 2 + 0.0004, 1.045), (-hl / 2 + 0.0014, 1.090), (-hl / 2 + 0.0034, 1.060),
            (-hl / 2 + 0.0070, 1.012), (-hl / 2 + 0.014, 0.990), (-hl / 2 + 0.035, 0.992), (-0.030, 1.010),
            (-0.012, 1.028), (0.0, 1.032), (0.012, 1.028), (0.030, 1.010), (hl / 2 - 0.035, 0.992),
            (hl / 2 - 0.014, 0.990), (hl / 2 - 0.0070, 1.012), (hl / 2 - 0.0034, 1.060), (hl / 2 - 0.0014, 1.090),
            (hl / 2 - 0.0004, 1.045), (hl / 2, 0.955)]
    base = L.polygon2d(4, hx / 2, 0.0055, 6, rot=math.pi / 4)
    rings = []
    for ri, (z, sc) in enumerate(prof):
        lipness = max(0.0, 1.0 - (hl / 2 - abs(z)) / 0.008)
        ring = []
        for k, (a, bb) in enumerate(base):
            ang = math.atan2(bb, a)
            # Uneven mushrooming and chips knocked out of the lip.
            wob = 0.004 * math.sin(3 * ang + 1.3 * (z > 0)) + 0.003 * math.sin(7 * ang + 0.7)
            chip = 0.0
            for c_ang, c_w, c_side in ((0.6, 0.12, 1), (2.9, 0.09, 1), (4.4, 0.15, -1), (1.7, 0.08, -1)):
                d = (ang - c_ang + math.pi) % math.tau - math.pi
                if (z > 0) == (c_side > 0):
                    chip += 0.035 * math.exp(-(d / c_w) ** 2)
            forge = 0.004 * math.sin(2.3 * z * 60 + ang * 2) * (1 - lipness)
            s_ = sc * (1.0 + lipness * (wob - chip)) + forge * 0.4
            ring.append(Vector((x_head + a * s_, bb * s_, z)))
        rings.append(ring)
    head = L.loft("Head", rings, steel, closed=True, chunk=0.0, sharp_angle=55.0,
                  tip_start=Vector((x_head, 0.0, -hl / 2 - 0.0008)), tip_end=Vector((x_head, 0.0, hl / 2 + 0.0008)))
    b.add(head)
    # Handle: oval, swelling a little at the butt, tapering into the eye and
    # standing 5 mm proud of the head with the wedge in its end grain.
    x_end = x_head + hx / 2 + 0.0050
    secs = [(x_butt, 0.0120, 0.0152), (x_butt + 0.004, 0.0137, 0.0172), (x_butt + 0.05, 0.0142, 0.0180),
            (x_butt + 0.25, 0.0131, 0.0166), (x_head - hx / 2 - 0.02, 0.0121, 0.0154),
            (x_head - hx / 2, 0.0117, 0.0148), (x_end - 0.0015, 0.0117, 0.0148), (x_end, 0.0108, 0.0139)]
    b.add(L.tube("Handle", secs, kashi, sides=36, max_seg=0.02, chunk=0.3))
    wedge = L.box("Wedge", (x_end - 0.0010, 0.0, 0.0), (0.0048, 0.0022, 0.0250), wedge_m, 0.0004)
    b.add(wedge, lod_drop=2)
    b.socket("Grip_R", (0.0, 0.0, 0.0))
    b.socket("Grip_L", (x_butt + 0.05, 0.0, 0.0))
    b.socket("Muzzle", (x_head, 0.0, -hl / 2), x=(0, 0, -1), z=(1, 0, 0))
    b.notes.update({"handle_m": handle_len, "head_m": [hl, hx, hy], "butt_x": x_butt,
                    "lip_overhang_m": round(hx / 2 * 0.09, 4),
                    "basis": "向こう鎚 striker's sledge proportions (design values)"})


BUILDERS = {6: build_kanabo, 8: build_forge_hammer}

if __name__ == "__main__":
    L.run({wid: BUILDERS[wid] for wid in S.by_builder("create_runtime_weapon_blunt.py")})
