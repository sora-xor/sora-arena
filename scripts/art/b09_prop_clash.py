"""Do the b09 station props pass through each other, and does each resting prop rest on its support? (CPU, exact)

Root's craft review asks that no prop pass through a bench or another prop (Coordination 241, 248). The paw gates
(b09_craft_poses.py) clear the arms from the props; this clears the props from each other, in every state a station
shows.

**A crossing** is an edge of one prop passing strictly through the interior of a triangle of the other: its two ends
strictly either side of the triangle's plane, and the point where it passes strictly inside the triangle. A part
resting on another meets it only at the plane or along an edge, so resting contact is not a crossing. Two crossing
solids always have such an edge, except where every crossing edge meets the other's triangles exactly on their edges
(two boxes on one grid, offset by half a face). So the test runs twice, the second prop jiggled by JIGGLE_CM and a
tiny turn one way and then the other: a crossing must show both ways. A resting contact parts one way, and a real
crossing, deeper than the jiggle, shows both.

**Containment** is a prop's island wholly inside a closed island of another, with no crossing: the median winding
number of the other's closed islands about up to 16 of the island's vertices (a resting part has vertices on the
surface and above it, so it is not contained).

**Support** is each resting prop's least distance to the part that carries it: within CONTACT_CM (the paws' contact
convention, 0.1-1.2 mm), so nothing floats.

The scenes (scenes(i)) are the states the station shows: the rib form at the start, middle and end of three hoops'
winding with the needle at its three marks; the paste bench with its sheets, rims and brush at rest, and with the rims
seated; the oil rack's finished lantern; the shell bench with every core and seat filled. rafter_scene() is the
drying poles with their 40 slot hooks and 40 lanterns hung (clashes(None), supports(None)). JOINTS lists any intended
crossing (a part let into another), with its reason. There are none.
"""
from __future__ import annotations

import itertools
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import b09_workshop_craft as B  # noqa: E402
import mesh_clearance as MC  # noqa: E402

CONTACT_CM = 0.12
JOINTS: dict = {}                            # {(name, name): reason}: intended crossings; none
ROOT = HERE.parent.parent
_WEAPON = {}


def weapon7():
    """SM_Weapon_07 as Unreal imports it (cm, its Y mirrored), from its LOD0 FBX: the real rope wrap, fibre cards,
    collar and cord, not a stand-in. Read once."""
    if "mesh" not in _WEAPON:
        import fbx_unreal_sockets as F
        g = F.geometry_arrays(str(ROOT / B.WEAPON7["fbx"]))["SM_Weapon_07"]
        v = g["Vertices"].reshape(-1, 3) * 100.0
        v[:, 1] *= -1.0
        idx = g["PolygonVertexIndex"].astype(np.int64)
        tris, start = [], 0
        for k in np.nonzero(idx < 0)[0]:
            poly = list(idx[start:k]) + [~idx[k]]
            tris += [(poly[0], poly[j + 1], poly[j]) for j in range(1, len(poly) - 1)]   # mirrored: reverse the winding
            start = k + 1
        _WEAPON["mesh"] = B.Mesh("SM_Weapon_07", v, np.array(tris, np.int64), "M_Weapon_07")
    return _WEAPON["mesh"]


HERO_FBX = "Content/SourceArt/Characters/Hero/SM_Nyaagyu_HeroCharacter.fbx"
BODY_HALF_WIDTH_CM = 22.0                    # the torso, legs, head and worn gear; the arms beyond are the sleeves' gate
ARM_BAND_Z = (55.0, 140.0)                   # where the rest pose's arms and sleeves hang in front of the body
TORSO_MARGIN = 0.08                          # the torso's section ellipse is grown by this share


def hero_body():
    """The hero's production mesh (SM_Nyaagyu_HeroCharacter.fbx) as Unreal places it: cm, its Y mirrored, feet on the
    floor, the body's axis at x = y = 0, facing +X. Only the triangles within BODY_HALF_WIDTH_CM of the axis are kept,
    so the rest-pose arms drop out (the pose gate's sleeves stand for the working arms); the gear worn on the body
    stays. Read once."""
    if "body" not in _WEAPON:
        import fbx_unreal_sockets as F
        g = F.geometry_arrays(str(ROOT / HERO_FBX))["SM_Nyaagyu_HeroCharacter"]
        v = g["Vertices"].reshape(-1, 3) * 100.0
        v[:, 1] *= -1.0
        idx = g["PolygonVertexIndex"].astype(np.int64)
        tris, start = [], 0
        for k in np.nonzero(idx < 0)[0]:
            poly = list(idx[start:k]) + [~idx[k]]
            tris += [(poly[0], poly[j + 1], poly[j]) for j in range(1, len(poly) - 1)]
            start = k + 1
        t = np.array(tris, np.int64)
        keep = np.all(np.abs(v[t][:, :, 1]) <= BODY_HALF_WIDTH_CM, axis=1)
        # The rest pose's forearms and sleeves come forward at the front diagonals between ARM_BAND_Z (14-27 cm ahead,
        # 14-37 cm out): inside the band, in the front half, keep only what lies within the torso's own section, an
        # ellipse through its front (|y| < 4) and side (|x| < 4) extents at that height, grown by TORSO_MARGIN.
        z0, z1 = ARM_BAND_Z
        bands = np.arange(z0, z1 + 4.0, 4.0)
        a_z, b_z = [], []
        for zb in bands:
            sl = v[(v[:, 2] >= zb - 2.0) & (v[:, 2] < zb + 2.0)]
            fr = sl[(np.abs(sl[:, 1]) < 4.0) & (sl[:, 0] > 0.0)]
            sd = sl[(np.abs(sl[:, 0]) < 4.0) & (np.abs(sl[:, 1]) <= BODY_HALF_WIDTH_CM)]
            a_z.append(float(fr[:, 0].max()) if len(fr) else 20.0)
            b_z.append(float(np.abs(sd[:, 1]).max()) if len(sd) else BODY_HALF_WIDTH_CM)
        a_v, b_v = np.interp(v[:, 2], bands, a_z), np.interp(v[:, 2], bands, b_z)
        inside = (np.maximum(v[:, 0], 0.0) / a_v) ** 2 + (v[:, 1] / b_v) ** 2 <= (1.0 + TORSO_MARGIN) ** 2
        arm = (v[:, 2] >= z0) & (v[:, 2] <= z1) & (v[:, 0] > 0.0) & ~inside
        keep &= ~np.any(arm[t], axis=1)
        _WEAPON["body"] = B.Mesh("SM_Nyaagyu_HeroCharacter", v, t[keep], "M_Hero")
    return _WEAPON["body"]


def body_at(stand, yaw_deg=0.0):
    """The hero's body standing at stand (station frame, the capsule's axis), facing +X turned by yaw_deg."""
    a = math.radians(yaw_deg)
    rz = np.array([[math.cos(a), -math.sin(a), 0.0], [math.sin(a), math.cos(a), 0.0], [0.0, 0.0, 1.0]])
    return hero_body().moved(np.array([stand[0], stand[1], 0.0]), rot=rz)


def weapon7_placed():
    origin, rot = B.weapon_rest()
    return weapon7().moved(origin, rot=rot)


def _through(p0, p1, a, b, c, eps=1e-6, tol=1e-7):
    """For n edges p0-p1 and n triangles abc: whether each edge passes strictly through its triangle's interior."""
    n = np.cross(b - a, c - a)
    nn = np.linalg.norm(n, axis=1)
    ok = nn > 1e-12
    n = n / np.where(ok, nn, 1.0)[:, None]
    d0 = np.einsum("ij,ij->i", p0 - a, n)
    d1 = np.einsum("ij,ij->i", p1 - a, n)
    straddle = ((d0 > eps) & (d1 < -eps)) | ((d0 < -eps) & (d1 > eps))
    t = d0 / np.where(straddle, d0 - d1, 1.0)
    x = p0 + (p1 - p0) * t[:, None]
    v0, v1, v2 = b - a, c - a, x - a
    d00, d01, d11 = (np.einsum("ij,ij->i", u, w) for u, w in ((v0, v0), (v0, v1), (v1, v1)))
    d20, d21 = np.einsum("ij,ij->i", v2, v0), np.einsum("ij,ij->i", v2, v1)
    den = d00 * d11 - d01 * d01
    den = np.where(np.abs(den) > 1e-18, den, 1.0)
    v = (d11 * d20 - d01 * d21) / den
    w = (d00 * d21 - d01 * d20) / den
    return ok & straddle & (1.0 - v - w > tol) & (v > tol) & (w > tol)


JIGGLE_CM, JIGGLE_RAD = 2e-5, 2e-7
_DIR = np.array([0.3, 0.5, 0.81]) / np.linalg.norm([0.3, 0.5, 0.81])
_AXIS = np.array([0.62, -0.47, 0.63]) / np.linalg.norm([0.62, -0.47, 0.63])


def _jiggled(verts, sign):
    c = verts.mean(0)
    t = sign * JIGGLE_RAD
    k = np.array([[0.0, -_AXIS[2], _AXIS[1]], [_AXIS[2], 0.0, -_AXIS[0]], [-_AXIS[1], _AXIS[0], 0.0]])
    rot = np.eye(3) + math.sin(t) * k + (1.0 - math.cos(t)) * (k @ k)
    return (verts - c) @ rot.T + c + sign * JIGGLE_CM * _DIR


def crossings(ma, mb):
    """(how many triangle pairs of ma and mb cross, a point near one): the fewer of the two jiggled tests, or 0 unless
    both find a crossing."""
    found = [_strict_crossings(ma.verts, ma.tris, _jiggled(mb.verts, sign), mb.tris) for sign in (1.0, -1.0)]
    if not (found[0][0] and found[1][0]):
        return 0, None
    return min(found, key=lambda f: f[0])


def _strict_crossings(va, ta, vb, tb):
    A, Bt = va[ta], vb[tb]
    pairs = MC.bbox_pairs(A.min(1), A.max(1), Bt.min(1), Bt.max(1), 0.0)
    if not len(pairs):
        return 0, None
    TA, TB = A[pairs[:, 0]], Bt[pairs[:, 1]]
    hit = np.zeros(len(pairs), bool)
    for P, Q in ((TA, TB), (TB, TA)):
        for e in range(3):
            hit |= _through(P[:, e], P[:, (e + 1) % 3], Q[:, 0], Q[:, 1], Q[:, 2])
    k = np.nonzero(hit)[0]
    if not len(k):
        return 0, None
    small = np.minimum(np.ptp(TA[k], axis=1).max(1), np.ptp(TB[k], axis=1).max(1))
    j = int(np.argmin(small))
    return int(len(k)), np.round((TA[k[j]].mean(0) + TB[k[j]].mean(0)) / 2.0, 2).tolist()


def contained(ma, mb):
    """How many of ma's islands lie wholly inside a closed island of mb."""
    isl_b = MC.islands(mb.tris)
    keep = np.isin(isl_b, np.nonzero(MC.closed_islands(mb.tris, isl_b))[0])
    if not keep.any():
        return 0
    tb = mb.verts[mb.tris[keep]]
    lo, hi = tb.reshape(-1, 3).min(0), tb.reshape(-1, 3).max(0)
    isl = MC.islands(ma.tris)
    out = 0
    for k in np.unique(isl):
        vs = np.unique(ma.tris[isl == k])
        pts = ma.verts[vs[np.linspace(0, len(vs) - 1, min(16, len(vs))).astype(int)]]
        if np.all((pts >= lo) & (pts <= hi)) and np.median([abs(MC.winding_number(q, tb)) for q in pts]) > 0.75:
            out += 1
    return out


def placed(m, socket, name=None):
    """A state mesh at a socket (point, x axis | None, z axis | None), as root places it."""
    p, x, z = socket
    rot = None
    if x is not None and z is not None:
        x, z = np.asarray(x, float), np.asarray(z, float)
        rot = np.stack([x, np.cross(z, x), z], 1)
    return m.moved(np.asarray(p, float), rot=rot, name=name or m.name)


def _turned(m, yaw, centre, name=None):
    return B.Mesh(name or m.name, B.to_station(m.verts, yaw, centre), m.tris, m.slot)


def scenes(i):
    """[(label, meshes, supports)]: each state station i shows, and its resting props' supports [(item, carrier)]."""
    parts, sk, _, _ = B.station_parts(i)
    sock = lambda n: np.asarray(sk[n][0], float)  # noqa: E731

    at = lambda m, socket, name=None: placed(m, sk[socket], name)  # noqa: E731

    out = []
    if i == 0:
        lc = B.lantern_centre(0)
        for k in (1, 4, 6):
            for f in (0.0, 0.5, 1.0):
                rib = [_turned(B.form(), B.form_yaw_deg(k - 1, f), lc)]
                rib += [_turned(B.hoop(j), B.form_yaw_deg(k - 1, f), lc) for j in range(1, k)]
                rib.append(_turned(B.hoop(k, f) if f < 1.0 else B.hoop(k), B.form_yaw_deg(k - 1, f), lc))
                ms = round(f * B.BEND_MS)
                needle = B.needle_at(ms)
                split = at(B.split_strip(), "SplitStripRest")
                out.append((f"hoop {k} at flex {f:g}, needle at {ms} ms", list(parts) + rib + [needle, split],
                            [("SM_B09_SplitStrip", "SM_B09_RibFormBench"), ("SM_B09_GaugeNeedle", "SM_B09_FlexGauge")]))
    elif i == 1:
        # The frame on its cradle (paste_frame): panel 1's gore laid on it with the next three sheets on the rack, and
        # all four panels on with the rims seated. The bottom rim is fitted to the frame's lower mouth from the start.
        st = {m.name: m for m, _, _ in B.state_meshes(1)}
        brush = at(st["SM_B09_PasteBrush"], "BrushRest")
        sheets = [at(st[f"SM_B09_WashiSheet{j}"], f"WashiSheet{j}") for j in (2, 3, 4)]
        first = B.Mesh(f"SM_B09_Washi{B.PASTE_ORDER[0]}", B.paste_frame(B.gore(B.PASTE_ORDER[0]).verts, 1), B.gore(B.PASTE_ORDER[0]).tris, "M_B09_Washi")
        laid = [B.Mesh(f"SM_B09_Washi{k}", B.paste_frame(B.gore(k).verts, 4), B.gore(k).tris, "M_B09_Washi") for k in B.PASTE_ORDER]
        bottom = at(B.rim("Bottom"), "RimBottomSeat", "SM_B09_RimBottom")
        sup = [("SM_B09_WashiSheet4", "SM_B09_SheetRack"), ("SM_B09_WashiSheet3", "SM_B09_WashiSheet4"),
               ("SM_B09_WashiSheet2", "SM_B09_WashiSheet3"), ("SM_B09_PastePot", "SM_B09_PotBracket"),
               ("SM_B09_PasteBrush", "SM_B09_PastePot"), ("SM_B09_RimBottom", "SM_B09_Form"),
               ("SM_B09_PasteCradle", "SM_B09_PasteBench"), ("SM_B09_PotBracket", "SM_B09_PasteBench"),
               ("SM_B09_SheetRack", "SM_B09_PasteBench"), ("SM_B09_RimShelf", "SM_B09_SheetRack")]
        out.append(("panel 1 laid; sheets 2-4 on the rack; the top rim on its shelf; the brush in the pot",
                    list(parts) + [first] + sheets + [at(B.rim("Top"), "RimTopRest", "SM_B09_RimTop"), bottom, brush],
                    sup + [("SM_B09_RimTop", "SM_B09_RimShelf")]))
        out.append(("all four panels on; the rims seated", list(parts) + laid + [brush, bottom, at(B.rim("Top"), "RimTopSeat", "SM_B09_RimTop")],
                    [("SM_B09_RimTop", "SM_B09_Form"), ("SM_B09_RimBottom", "SM_B09_Form")]))
    elif i == 2:
        hp = sock("LanternHang")
        lantern = [m.moved(hp - B.hang_point()) for m in B.lantern("finished")]
        st = {m.name: m for m, _, _ in B.state_meshes(2)}
        brush = at(st["SM_B09_OilBrush"], "BrushRest")
        out.append(("the finished lantern hung; the brush at rest", list(parts) + lantern + [brush],
                    [("SM_B09_OilBrush", "SM_B09_OilDish"), ("SM_B09_OilDish", "SM_B09_DishStand"), ("SM_B09_DishStand", "SM_B09_OilRack"),
                     ("SM_B09_Bail", "SM_B09_RackHook"), ("SM_B09_OilJar", "SM_B09_OilRack"), ("SM_B09_DripTray", "SM_B09_OilRack")]))
    else:
        weapon = weapon7_placed()
        shells = [B.shell("wrapped").moved(sock(f"ShellSeat{k}"), name=f"SM_B09_ShellWrapped{k}") for k in (1, 2, 3)]
        cores = [B.shell("core").moved(sock(f"ShellCore{k}"), name=f"SM_B09_ShellCore{k}") for k in (1, 2, 3)]
        sup = [(f"SM_B09_ShellWrapped{k}", "SM_B09_ShellRack") for k in (1, 2, 3)] + [(f"SM_B09_ShellCore{k}", "SM_B09_ShellTray") for k in (1, 2, 3)]
        sup += [(n, "SM_B09_ShellStand") for n in ("SM_B09_ShellRack", "SM_B09_ShellTray", "SM_B09_WrapPost", "SM_B09_FuseCoil")]
        sup += [("SM_B09_WrapPaper", "SM_B09_WrapPost")]
        sup += [("SM_Weapon_07", "SM_B09_WeaponCradle"), ("SM_B09_ShellStand", "SM_B09_ShellBench")]
        out.append(("every core in the tray, every seat filled; weapon 7 in its block", list(parts) + [weapon] + shells + cores, sup))
    return out


def rafter_scene():
    """The drying poles, their 40 slot hooks and the 40 finished lanterns hung from them (world cm), with the supports:
    each lantern's bail on its hook."""
    poles, hooks = B.hanging_parts()
    lantern = B.merge("SM_B09_LanternFinished", B.lantern("finished"))
    meshes, sup = [poles], []
    hang = B.hang_point()
    for k, (_, _, hp, yaw) in enumerate(B.slots()):
        a = math.radians(yaw)
        rot = np.array([[math.cos(a), -math.sin(a), 0.0], [math.sin(a), math.cos(a), 0.0], [0.0, 0.0, 1.0]])
        meshes.append(B.Mesh(f"lantern{k}", (lantern.verts - hang) @ rot.T + hp, lantern.tris, lantern.slot))
        sup.append((f"lantern{k}", f"hook{k}"))
    n = len(hooks.verts) // len(B.slots())
    tn = len(hooks.tris) // len(B.slots())
    for k in range(len(B.slots())):
        t = hooks.tris[k * tn:(k + 1) * tn] - k * n
        meshes.append(B.Mesh(f"hook{k}", hooks.verts[k * n:(k + 1) * n], t, hooks.slot))
        sup.append((f"hook{k}", "SM_B09_DryingPoles"))
    return meshes, sup


def clashes(i):
    """{scene: [(a, b, crossing pairs, contained islands, near)]} for the props of station i (None: the rafters),
    intended joints apart."""
    report = {}
    for label, meshes, _ in (scenes(i) if i is not None else [("the rafters, 40 lanterns hung", *rafter_scene())]):
        rows = []
        for a, b in itertools.combinations(meshes, 2):
            (la, ha), (lb, hb) = a.bounds(), b.bounds()
            if np.any(ha < lb) or np.any(hb < la) or (a.name, b.name) in JOINTS or (b.name, a.name) in JOINTS:
                continue
            n, near = crossings(a, b)
            c = 0 if n else contained(a, b) + contained(b, a)
            if n or c:
                rows.append((a.name, b.name, n, c, near))
        report[label] = rows
    return report


def supports(i):
    """{scene: [(item, carrier, least distance cm)]}: each resting prop's gap to what carries it."""
    report = {}
    for label, meshes, pairs in (scenes(i) if i is not None else [("the rafters, 40 lanterns hung", *rafter_scene())]):
        by = {}
        for m in meshes:
            by.setdefault(m.name, []).append(m)
        rows = []
        for item, carrier in pairs:
            for m in by[item]:
                c = B.merge(carrier, by[carrier])
                r = MC.exact_separation(m.verts, m.tris, c.verts, c.tris, limit=5.0)
                rows.append((item, carrier, None if r["separation_m"] is None else round(float(r["separation_m"]), 4)))
        report[label] = rows
    return report


if __name__ == "__main__":
    import json
    for i in range(4):
        print(B.STATIONS[i][0])
        print(" clashes", json.dumps(clashes(i), indent=1))
        print(" supports", json.dumps(supports(i), indent=1))
