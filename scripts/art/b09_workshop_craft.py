"""The chapter-03 b09 lantern workshop's craft assets, proposed on the CPU: parts, bounds, pivots, sockets, states and
pose clearances for root's integration. Root owns state, accounting and collision; this module owns the art's shape.

**Inputs** (root's tree at INPUTS["root_commit"], each file pinned by its git blob in INPUTS):
- **The four stations and their floors:** SoraLanternWorkshopRules.h.
  - Stations: rib form (2100, -620), paste bench (2100, -950), oil rack (2100, -1300), all on the 45 cm plank floor;
    shell bench (2790, -2050), in the yard under the storehouse's west eaves.
  - Steps by station: 0, 1, 1, 2, 3, 3.
- **The six steps** (chapter_03.json ch03.b09):
  1. bend x6: 800 ms release, +-160 ms;
  2. paste x4: 1.5 s holds;
  3. assemble the top and bottom rims (1);
  4. paste perilla oil (1);
  5. assemble x3 shells;
  6. inspect the fuse (1).
  Output: 40 lanterns, the whole workshop's night of work.
- **Working a station** (SoraCampaignWorkshopCraft.cpp, SoraCampaignReach.h, SoraCharacterBase.cpp):
  - feet within 8 cm of the station's floor, within 260 cm (2D);
  - a Visibility trace from the capsule's centre (floor + 88 cm; capsule radius 34, half-height 88) to the station
    point at floor + 110 cm;
  - the standing eye at the capsule's centre + (4, 0, 64) cm (SoraPlayerCharacter.cpp).
- **Weapon 7** (build_record.json): an 84 cm bamboo tube with a 5.6 cm bore in a 7.6 cm culm. Its mesh runs from
  -20 to +64 cm along its bore (X), and its muzzle is at +64. Fuse socket (0.2, -1.2, 6.0) cm in Unreal axes.
- **History** (chapter-03.md 4.3): separate hoops (輪骨) hooked onto a form, perilla oil (荏油), and simple hanging
  lanterns for 1623.

**Frames.** Unreal centimetres: X, Y, Z with Z up, and Unreal's left-handed axes. A station's frame has its origin at
the station point on its floor, (X, Y, FloorAt(X, Y)), and the world's axes (yaw 0). That is where the world builder's
Floor() puts its bench today. The hero works each station from its west side, facing +X. The craftspeople (X 2250)
face back across the benches.

**The lantern** (lantern frame: origin at its centre):
- a barrel 44 cm tall and 30 cm across, with 18 cm openings: a superellipse profile, exponent LANTERN_P;
- six bamboo hoops (輪骨), evenly spaced between the rims;
- four washi gores, each a quarter of the round plus 4 deg of overlap at each seam;
- top and bottom rims (口輪) and an iron bail.
At the rib form and paste bench its centre sits at the station point (floor + 110). It hangs at the same height on the
oil rack, and from the drying poles in the rafters.

**Collision.** Every mesh here is visual only. Root keeps or replaces the world builder's boxes, which this module
proposes as COLLISION proxies:
- each is under 86 cm, below the 88 cm start of every station ray, so no proxy can block a station's Visibility trace;
- the taller parts carry no collision (rack posts, form spindle, gauge, poles, lanterns).

**What this module gives** (all deterministic):
- meshes (numpy), with per-vertex attributes for root's material progress;
- sockets, with optional X and Z axes;
- the state each view field drives;
- AABB bounds;
- clearance checks: the hero at each work stand, the eye's line to the work, every eligible station ray against the
  proxies, the hanging lanterns against the hero's head, the shells against the bore;
- spec(), the JSON proposal: docs/art-direction/data/b09_workshop_craft_spec.json;
- previews: a CPU shaded rasteriser and a plan, presentation only.

Run (host, /usr/bin/python3: numpy and PIL):
  /usr/bin/python3 scripts/art/b09_workshop_craft.py --spec docs/art-direction/data/b09_workshop_craft_spec.json
  /usr/bin/python3 scripts/art/b09_workshop_craft.py --previews <new folder>
"""
from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

# --- Root's inputs, pinned ----------------------------------------------------------------------------------------------
INPUTS = {
    # Re-pinned from c1f0b5af to root's 2a846a6a: two files changed, both additively. SoraWorkshopCraftRules.h gained
    # FView; SoraCampaignWorkshopCraft.cpp gained WorkshopCraftView() and the failed-strip bookkeeping. The timing,
    # eligibility and station trace are unchanged. SoraWorldBuilder.h carries FSoraKitView::LanternCraft.
    # Re-pinned to fcf3ffb5 (Coordination 239): of these files only chapter_03.json changed, for b10's ground routes
    # in ch03_lantern_ward. The ch03.b09 beat is identical.
    # Re-pinned to 102c18d9 (Coordination 240). SoraLanternWorkshopRules.h shortens the east yard wall to end at
    # Y -400, opening the main street; SOLIDS follows it. SoraWorldBuilder.h gives Lanterns a notice-square argument.
    # The stations, recipe, state and eligibility are unchanged.
    "root_commit": "102c18d9e3b0664c9f6970dec64a24b1c5b30d78",
    "blobs": {
        "Source/SoraArena/Public/SoraLanternWorkshopRules.h": "c7aa71efafc72ecfdd085f67bedbdf84899c4b51",
        "Source/SoraArena/Public/SoraWorkshopCraftRules.h": "39c36512c2a772c187164d8f1b3547e8ebac2d2b",
        "Source/SoraArena/Public/SoraWorldBuilder.h": "72ce871f533a7019591062e5c2bc6626e2c3d254",
        "Source/SoraArena/Private/Game/SoraCampaignReach.h": "96ede9639f397714300be52c4a0b5e5b2520418f",
        "Source/SoraArena/Private/Game/SoraCampaignWorkshopCraft.cpp": "ddac4fc51ac93d31cc33fd77fcf45b742812b8b9",
        "Source/SoraArena/Private/Characters/SoraCharacterBase.cpp": "3221fa817a15e57d94f0426b202409e8d56289b2",
        "Source/SoraArena/Private/Characters/SoraPlayerCharacter.cpp": "b8e4fb6b25592aae949ab855fe33e7ea33a2039e",
        "docs/campaign/chapter-03.md": "4141dcc335b4ecf24e9d3ad626b55f1325f3647d",
        "Content/Data/campaign/chapter_03.json": "75874ff583570026946b889c31e075dcedd07e79",
        "Content/SourceArt/Weapons/Runtime/W07_GrenadeLauncher/build_record.json": "95f796814125b324f8a5325a92c2b537307d502b",
    },
}
STATIONS = (("st_b09_rib_form", (2100.0, -620.0)), ("st_b09_paste_bench", (2100.0, -950.0)),
            ("st_b09_oil_rack", (2100.0, -1300.0)), ("st_b09_shell_bench", (2790.0, -2050.0)))
STEP_STATIONS = (0, 1, 1, 2, 3, 3)
STEPS = (("bend", 6), ("paste", 4), ("assemble", 1), ("paste", 1), ("assemble", 3), ("inspect", 1))
BEND_MS, BEND_TOL_MS, PASTE_MS = 800, 160, 1500
OUTPUT_LANTERNS = 40
REACH_CM = 260.0
FEET_TOL_CM = 8.0
CAPSULE_R, CAPSULE_HALF = 34.0, 88.0
EYE = (4.0, 0.0, 64.0)                       # from the capsule's centre, in the hero's facing frame
RAY_FROM_Z, RAY_TO_Z = 88.0, 110.0           # the station trace: capsule centre -> station point (above the floor)
# Standing only. AtWorkshopStation starts the trace at the actor's centre and does not forbid crouching, and a crouched
# capsule's half-height is 44 cm (root, Coordination 236). The ray and proxy proof below covers the standing capsule;
# crouched and native coverage are root's. clearance() reports a crouched CPU estimate, labelled as one.
CROUCH_HALF = 44.0
HEAD_TOP_CM = 195.0                          # feet to ear tips, a conservative head clearance for hanging work
# The hero's camera draws the world at 94 deg (horizontal, held at every aspect). 70 deg is its first-person field of
# view, for first-person primitives (the viewmodel) only (SoraPlayerCharacter.cpp). The props here are world meshes.
WORLD_HFOV_DEG = 94.0
ASPECTS = {"16:9": 16 / 9, "21:9": 21 / 9}    # 21:9 keeps 94 deg across and loses height: the stress case
CEILING_Z = 430.0                            # the room's ceiling underside (the 20 cm slab at z 440)
WEAPON7 = {"bore_cm": 5.6, "culm_cm": 7.6, "x_range_cm": (-20.0, 64.0), "half_width_cm": 6.11,
           "z_range_cm": (-11.54, 6.81), "muzzle_cm": (64.0, 0.0, 0.0), "fuse_cm": (0.2, -1.2, 6.0)}


def floor_at(x, y):
    """SoraLanternWorkshopRules::FloorAt."""
    if 1780 <= x <= 2320 and -1500 <= y <= -400:
        return 45.0
    if (1710 <= x < 1780 and -1494 <= y <= -406) or (1830 <= x <= 1970 and -1570 <= y < -1500):
        return 22.5
    return 0.0


def _solids():
    """SoraLanternWorkshopRules::Solids, as (centre, size) boxes in world cm (the ground slab left out).
    check_b09_root_inputs.py compares them, box by box, with the pinned header."""
    b = [(2050, -950, 22.5, 540, 1100, 45), (1745, -950, 11.25, 70, 1088, 22.5), (1900, -1535, 11.25, 140, 70, 22.5),
         (1600, -950, 215, 12, 1100, 430), (2320, -950, 215, 12, 1100, 430), (1960, -400, 215, 720, 12, 430),
         (1715, -1500, 215, 230, 12, 430), (2145, -1500, 215, 350, 12, 430), (1900, -1500, 345, 140, 12, 170),
         (1960, -950, 440, 750, 1130, 20), (2860, -650, 210, 1080, 500, 420),
         (1600, -1850, 100, 12, 700, 200), (1755, -2200, 100, 310, 12, 200), (2495, -2200, 100, 810, 12, 200),
         (3400, -1375, 80, 12, 450, 160), (3700, -1450, 100, 12, 2100, 200)]
    for s in (-1, 1):
        b += [(2600 + s * 65, -1400, 40, 30, 160, 80), (2600, -1400 + s * 65, 40, 100, 30, 80)]
    b += [(3400, -1900, 319, 16, 600, 638), (3150, -1600, 319, 500, 16, 638), (3150, -2200, 319, 500, 16, 638),
          (2900, -2095, 319, 16, 210, 638), (2900, -1705, 319, 16, 210, 638), (2900, -1900, 444, 16, 180, 388),
          (3050, -1900, 644, 700, 640, 12)]
    return [(np.array(c[:3], float), np.array(c[3:], float)) for c in b]


SOLIDS = _solids()
# Each box's ESurface in the header (Wood unless named): the yard's east wall, the well curb and the storehouse are
# Stone.
SOLID_SURFACES = ["Wood"] * 15 + ["Stone"] * 5 + ["Stone"] * 6 + ["Wood"]
FLOOR_SLABS = (0, 1, 2)                     # the plank floor and its two steps: walked on, not walls

# --- The lantern ----------------------------------------------------------------------------------------------------
LANTERN_H, LANTERN_R, LANTERN_RIM_R, LANTERN_P = 44.0, 15.0, 9.0, 2.2
WORK_Z = 110.0                               # the station point's height above its floor (the trace's target)
# The lantern's centre at each lantern station. At 110, the station point's height, the lower shoulder of a seam or
# stroke hides behind the lantern's belly from standing eye height (152). At 130, chest height, the front seam shows
# in full (first_person()). The rib form keeps 110, where every hoop shows.
LANTERN_Z = {0: 110.0, 1: 130.0, 2: 130.0}
HOOP_W, HOOP_T = 0.40, 0.16                  # bamboo strip (ひご): width along the lantern's axis, radial thickness
HOOP_LAP_DEG = 25.0                          # the strip's ends overlap by this much at the hook
PAPER_GAP = 0.06                             # washi sits this far outside the hoops
GORE_OVERLAP_DEG = 4.0                       # each gore runs this far past its quarter at each seam
RIM_H, RIM_T = 2.0, 0.8                      # 口輪: height, radial thickness
BAIL_RISE = 9.0                              # the bail's top above the top rim: the hanging point
FLEX_STAGES = (0.0, 0.25, 0.5, 0.75, 1.0)


def profile_r(z):
    """The lantern's radius at height z (lantern frame, -22..22)."""
    h = LANTERN_H / 2.0
    s = np.clip(np.abs(np.asarray(z, float)) / h, 0.0, 1.0)
    return LANTERN_RIM_R + (LANTERN_R - LANTERN_RIM_R) * (1.0 - s ** LANTERN_P) ** (1.0 / LANTERN_P)


def hoop_z():
    """The six hoops' heights, evenly spaced between the rims (lantern frame)."""
    h = LANTERN_H / 2.0
    return np.array([-h + LANTERN_H * k / 7.0 for k in range(1, 7)])


def hoop_r():
    return profile_r(hoop_z()) + HOOP_T / 2.0


def hang_point():
    return np.array([0.0, 0.0, LANTERN_H / 2.0 + RIM_H / 2.0 + BAIL_RISE])


# --- Meshes ---------------------------------------------------------------------------------------------------------
@dataclass
class Mesh:
    name: str
    verts: np.ndarray
    tris: np.ndarray
    slot: str
    attrs: dict = field(default_factory=dict)
    collision: str = "none (visual only)"
    tri_slots: object = None                 # per-triangle material slots, where a mesh has more than one
    tri_uv0: object = None                   # per-corner UV0 (n_tris, 3, 2) in metres, from its construction (box_uv)

    def slots(self):
        return np.asarray(self.tri_slots, object) if self.tri_slots is not None else np.full(len(self.tris), self.slot, object)

    def moved(self, offset=(0.0, 0.0, 0.0), rot=None, name=None):
        v = self.verts @ np.asarray(rot, float).T if rot is not None else self.verts.copy()
        return Mesh(name or self.name, v + np.asarray(offset, float), self.tris.copy(), self.slot,
                    {k: a.copy() for k, a in self.attrs.items()}, self.collision,
                    None if self.tri_slots is None else np.asarray(self.tri_slots, object).copy(),
                    None if self.tri_uv0 is None else np.asarray(self.tri_uv0, float).copy())

    def bounds(self):
        return self.verts.min(0), self.verts.max(0)


def merge(name, meshes, slot=None):
    """One mesh from several, each triangle keeping its part's material slot (an early version kept only the first
    part's, which turned the gauge's band and ticks into its face)."""
    v, t, ts, off = [], [], [], 0
    for m in meshes:
        v.append(m.verts)
        t.append(m.tris + off)
        ts.append(m.slots())
        off += len(m.verts)
    tri_slots = np.concatenate(ts)
    primary = slot or meshes[0].slot
    uv = None
    if any(m.tri_uv0 is not None for m in meshes):         # each part keeps its own mapping (box parts their projection)
        uv = np.concatenate([np.asarray(box_uv(m), float) for m in meshes])
    return Mesh(name, np.concatenate(v), np.concatenate(t), primary, {}, "none (visual only)",
                None if (tri_slots == primary).all() else tri_slots, uv)


def box(name, lo, hi, slot):
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    c = np.array([[x, y, z] for z in (0, 1) for y in (0, 1) for x in (0, 1)], float)
    v = lo + c * (hi - lo)
    t = np.array([[0, 2, 1], [1, 2, 3], [4, 5, 6], [5, 7, 6], [0, 1, 4], [1, 5, 4], [2, 6, 3], [3, 6, 7],
                  [0, 4, 2], [2, 4, 6], [1, 3, 5], [3, 7, 5]])
    return Mesh(name, v, t, slot)


def _frames(path, closed):
    """Rotation-minimising frames along a polyline: (tangents, normals, binormals)."""
    p = np.asarray(path, float)
    d = np.roll(p, -1, 0) - np.roll(p, 1, 0) if closed else np.gradient(p, axis=0)
    tg = d / np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-12)
    ref = np.array([0.0, 0.0, 1.0]) if abs(tg[0, 2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    n0 = np.cross(tg[0], ref)
    n0 /= np.linalg.norm(n0)
    ns = [n0]
    for k in range(1, len(p)):
        n = ns[-1] - np.dot(ns[-1], tg[k]) * tg[k]
        ns.append(n / max(np.linalg.norm(n), 1e-12))
    ns = np.array(ns)
    return tg, ns, np.cross(tg, ns)


def sweep(name, path, slot, radius=None, rect=None, closed=False, segments=8, up=None):
    """A tube along a polyline: round (radius) or rectangular (rect = (width along `up` or the binormal, thickness
    along the normal)). Open tubes are capped."""
    p = np.asarray(path, float)
    tg, nrm, bin_ = _frames(p, closed)
    if up is not None:                       # a fixed width direction (a strip's width along the lantern's axis)
        bin_ = np.repeat(np.asarray(up, float)[None], len(p), 0)
        nrm = np.cross(bin_, tg)
        nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-12)
    if rect is not None:
        w, th = rect
        ring = [(-w / 2, -th / 2), (w / 2, -th / 2), (w / 2, th / 2), (-w / 2, th / 2)]
        sec = [(b, a) for a, b in ring]
    else:
        sec = [(radius * math.cos(2 * math.pi * k / segments), radius * math.sin(2 * math.pi * k / segments))
               for k in range(segments)]
    m = len(sec)
    v = np.array([p[i] + a * nrm[i] + b * bin_[i] for i in range(len(p)) for a, b in sec])
    rows = len(p) if not closed else len(p) + 1
    # UV0 (m): u is the arc length along the path, v the distance round the section, so grain runs along a strip.
    run = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(np.vstack([p, p[:1]]) if closed else p, axis=0), axis=1))])
    sv = np.concatenate([[0.0], np.cumsum([math.dist(sec[k], sec[(k + 1) % m]) for k in range(m)])])
    t, uv = [], []
    for i in range(rows - 1):
        i0, i1 = i % len(p), (i + 1) % len(p)
        u0, u1 = run[i] / 100.0, run[i + 1] / 100.0
        for k in range(m):
            a, b = i0 * m + k, i0 * m + (k + 1) % m
            c, d = i1 * m + k, i1 * m + (k + 1) % m
            va, vb = sv[k] / 100.0, sv[k + 1] / 100.0
            t += [[a, c, b], [b, c, d]]
            uv += [[(u0, va), (u1, va), (u0, vb)], [(u0, vb), (u1, va), (u1, vb)]]
    if not closed:
        for i0, flip in ((0, True), (len(p) - 1, False)):
            ctr = len(v)
            v = np.vstack([v, p[i0]])
            for k in range(m):
                a, b = i0 * m + k, i0 * m + (k + 1) % m
                ka, kb = (np.asarray(sec[k]) / 100.0, np.asarray(sec[(k + 1) % m]) / 100.0)
                t.append([ctr, b, a] if flip else [ctr, a, b])
                uv.append([(0.0, 0.0), tuple(kb), tuple(ka)] if flip else [(0.0, 0.0), tuple(ka), tuple(kb)])
    return Mesh(name, v, np.array(t), slot, tri_uv0=np.array(uv, float))


def revolve(name, zr, slot, az0=0.0, az1=360.0, n_az=48, cap=False):
    """A surface of revolution about Z from (z, r) samples, azimuths az0..az1 (deg).

    A sample on the axis (r = 0) is a pole: one vertex, met by a fan. A ring stands for it only if Unreal would keep
    the ring's triangles. A 1e-4 cm pole ring has corners 2e-5 cm apart, within THRESH_POINTS_ARE_SAME, so Unreal's
    build dropped 128 slivers from each shell (s147).

    Attributes: height fraction (0 at the lowest sample, 1 at the highest) and azimuth fraction across the patch (0 at
    a pole). (It was once 0 at the first sample and 1 at the last, which runs to 2e12 on a profile that ends where it
    began, as a rim's does.)"""
    zr = np.asarray(zr, float)
    if (zr[:, 1] < 0).any():
        raise ValueError(f"{name}: a negative radius")
    full = abs((az1 - az0) - 360.0) < 1e-9
    cols = n_az if full else n_az + 1
    a = np.radians(az0 + (az1 - az0) * np.arange(cols) / n_az)
    hf_of = (zr[:, 0] - zr[:, 0].min()) / max(np.ptp(zr[:, 0]), 1e-12)
    v, hf, af, first = [], [], [], []
    for i, (z, r) in enumerate(zr):
        first.append(len(v))
        if r == 0.0:                                             # a pole
            v.append([0.0, 0.0, z])
            hf.append(hf_of[i])
            af.append(0.0)
        else:
            v += [[r * math.cos(t), r * math.sin(t), z] for t in a]
            hf += [hf_of[i]] * cols
            af += list(np.arange(cols) / n_az)
    t, uv = [], []
    # UV0 (m): u round the widest radius, v along the profile, so paper fibre and wood grain wrap the part.
    r_ref = max(float(zr[:, 1].max()), 1e-6)
    ua = (az1 - az0) * np.arange(n_az + 1) / n_az * math.pi / 180.0 * r_ref / 100.0
    vrow = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(zr[:, 0]), np.diff(zr[:, 1])))]) / 100.0
    for i in range(len(zr) - 1):
        pole_a, pole_b = zr[i, 1] == 0.0, zr[i + 1, 1] == 0.0
        for j in range(n_az):
            if pole_a and pole_b:
                break
            um = 0.5 * (ua[j] + ua[j + 1])
            if pole_a:                                           # [p, q, r] of the quad, with p = q at the pole: dropped
                t.append([first[i], first[i + 1] + (j + 1) % cols, first[i + 1] + j])
                uv.append([(um, vrow[i]), (ua[j + 1], vrow[i + 1]), (ua[j], vrow[i + 1])])
            elif pole_b:                                         # [q, s, r] of the quad, with s = r at the pole: dropped
                t.append([first[i] + j, first[i] + (j + 1) % cols, first[i + 1]])
                uv.append([(ua[j], vrow[i]), (ua[j + 1], vrow[i]), (um, vrow[i + 1])])
            else:
                p, q = first[i] + j, first[i] + (j + 1) % cols
                r_, s_ = first[i + 1] + j, first[i + 1] + (j + 1) % cols
                t += [[p, q, r_], [q, s_, r_]]
                uv += [[(ua[j], vrow[i]), (ua[j + 1], vrow[i]), (ua[j], vrow[i + 1])],
                       [(ua[j + 1], vrow[i]), (ua[j + 1], vrow[i + 1]), (ua[j], vrow[i + 1])]]
    mesh = Mesh(name, np.array(v, float), np.array(t), slot, {"height_frac": np.array(hf), "azimuth_frac": np.array(af)},
                tri_uv0=np.array(uv, float))
    if cap and full:                                             # close an end ring with a centre vertex
        for i, flip in ((0, True), (len(zr) - 1, False)):
            if zr[i, 1] == 0.0:
                continue
            ctr = len(mesh.verts)
            mesh.verts = np.vstack([mesh.verts, [0.0, 0.0, zr[i, 0]]])
            for k in range(n_az):
                p, q = first[i] + k, first[i] + (k + 1) % cols
                mesh.tris = np.vstack([mesh.tris, [ctr, q, p] if flip else [ctr, p, q]])
                cap = [(0.0, 0.0), tuple(mesh.verts[q][:2] / 100.0), tuple(mesh.verts[p][:2] / 100.0)]   # planar (x, y)
                mesh.tri_uv0 = np.vstack([mesh.tri_uv0, [cap if flip else [cap[0], cap[2], cap[1]]]])
            for key in mesh.attrs:
                mesh.attrs[key] = np.append(mesh.attrs[key], mesh.attrs[key][first[i]])
    return mesh


def sphere(name, r, slot, n=24):
    """A sphere of radius r with true poles (one vertex each, met by a fan)."""
    zr = [(r * math.cos(math.pi * (1 - k / n)), 0.0 if k in (0, n) else r * math.sin(math.pi * k / n)) for k in range(n + 1)]
    return revolve(name, zr, slot, n_az=2 * n)


def brush(name, width, bristle=4.0, handle=18.0):
    """A flat brush (刷毛): its bristles' tip at the origin, the bristles along +Y, then the handle."""
    return merge(name, [box(name, (-width / 2, 0.0, -0.5), (width / 2, bristle, 0.5), "M_B09_Bristle"),
                        box(name, (-1.0, bristle, -0.6), (1.0, bristle + handle, 0.6), "M_B09_TimberBench")])


def bench(name, depth, width, top, slot="M_B09_TimberBench", leg=6.0, thick=4.0):
    """A plain workbench: a top over four legs and two stretchers, origin on the floor at its centre."""
    hx, hy = depth / 2.0, width / 2.0
    parts = [box(name, (-hx, -hy, top - thick), (hx, hy, top), slot)]
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = sx * (hx - leg), sy * (hy - leg)
            parts.append(box(name, (cx - leg / 2, cy - leg / 2, 0), (cx + leg / 2, cy + leg / 2, top - thick), slot))
    for sy in (-1, 1):
        cy = sy * (hy - leg)
        parts.append(box(name, (-hx + leg, cy - 2, 14), (hx - leg, cy + 2, 19), slot))
    return merge(name, parts, slot)


# --- The lantern's parts (lantern frame) ------------------------------------------------------------------------------
def hoop_path(k, flex=1.0, segments=192):
    """Strip k's centreline as it bends: (points, outward normals, arc parameter s, end). flex 0 is a straight strip
    tangent to the form on the hero's side (-X); 1 is the closed hoop, its ends lapped. end is -1 on the trailing
    end's scarf, +1 on the leading end's and 0 between. The strip keeps its length at every flex."""
    z, r = hoop_z()[k - 1], hoop_r()[k - 1]
    length = r * math.radians(360.0 + HOOP_LAP_DEG)
    lap = r * math.radians(HOOP_LAP_DEG)
    s = np.linspace(-length / 2, length / 2, segments + 1)
    wrapped = flex * length / 2.0
    pts, nrm = [], []
    for si in s:
        if abs(si) <= wrapped:
            th = math.pi + si / r                               # centred on -X, facing the hero
            pts.append([r * math.cos(th), r * math.sin(th), z])
        else:
            sign = 1.0 if si > 0 else -1.0
            th = math.pi + sign * wrapped / r
            base = np.array([r * math.cos(th), r * math.sin(th), z])
            pts.append(base + sign * np.array([-math.sin(th), math.cos(th), 0.0]) * (abs(si) - wrapped))
        nrm.append([math.cos(th), math.sin(th), 0.0])
    end = np.where(s >= length / 2 - lap - 1e-9, 1, np.where(s <= -length / 2 + lap + 1e-9, -1, 0))
    return np.array(pts), np.array(nrm), s, end


def hoop(k, flex=1.0, segments=192):
    """Hoop k (1..6) as its strip bends (hoop_path).

    **The ends are scarfed (削ぎ):** each is shaved to half thickness over the lap, the leading end on the outer half
    and the trailing end on the inner half. Closed, the lap is flush within the strip's own thickness, so the washi
    clears it as it clears the rest. s148 showed the earlier lap, the leading end riding a full thickness out, and its
    outward hook tip piercing the paper. The hoops sit in the form boards' notches, so a hoop needs no hook of its
    own (the notches are not modelled)."""
    pts, nrm, s, end = hoop_path(k, flex, segments)
    name = f"SM_B09_Hoop{k}" + ("" if flex >= 1.0 else f"_Flex{int(round(flex * 100)):03d}")
    i_trail = int(np.nonzero(end == -1)[0].max())                # the last sample of the trailing scarf
    i_lead = int(np.nonzero(end == 1)[0].min())                  # the first of the leading scarf
    runs = [(slice(0, i_trail + 1), -1), (slice(i_trail, i_lead + 1), 0), (slice(i_lead, len(s)), 1)]
    parts = []
    for sl, e in runs:
        off = e * HOOP_T / 4                                     # a scarf's centre: a quarter thickness in or out
        th = HOOP_T if e == 0 else HOOP_T / 2
        parts.append(sweep(name, pts[sl] + nrm[sl] * off, "M_B09_Bamboo", rect=(HOOP_W, th), up=(0.0, 0.0, 1.0)))
    return merge(name, parts)


def split_strip(k=6):
    """A failed strip, split lengthwise along 60% of its length and splayed, lying flat (frame: its middle)."""
    r = hoop_r()[k - 1]
    length = r * math.radians(360.0 + HOOP_LAP_DEG)
    n = 40
    halves = []
    for side in (-1, 1):
        pts = []
        for i in range(n + 1):
            x = -length / 2 + length * i / n
            split = max(0.0, (x - (-length / 2 + 0.4 * length)) / (0.6 * length))
            pts.append([x, side * (HOOP_W / 4 + 3.0 * split ** 1.5), HOOP_T / 2 + 0.3 * split * (side + 1)])
        halves.append(sweep("SM_B09_SplitStrip", pts, "M_B09_Bamboo", rect=(HOOP_W / 2, HOOP_T), up=(0, 1, 0)))
    return merge("SM_B09_SplitStrip", halves)


RIB_RAMP = 0.6                               # cm: the washi returns from a rib to its profile over this height


def paper_r(z):
    """The washi's radius at height z. It rests on the ribs, as pasted paper does: PAPER_GAP outside a strip's outer
    face wherever a strip lies under it, easing back over RIB_RAMP. Between the ribs it is HOOP_T + PAPER_GAP outside
    the profile.

    A strip's face is upright (its width along the axis), so on the lantern's shoulders, where the profile slopes
    0.26, its narrow-side edge stood outside paper that followed only the profile. s148 showed the end hoops crossing
    it."""
    z = np.asarray(z, float)
    out = profile_r(z) + HOOP_T + PAPER_GAP
    for zk, rk in zip(hoop_z(), hoop_r()):
        over = rk + HOOP_T / 2 + PAPER_GAP                       # PAPER_GAP outside the strip's outer face
        d = np.abs(z - zk) - HOOP_W / 2
        w = np.clip(1.0 - d / RIB_RAMP, 0.0, 1.0)                # 1 over the strip, 0 beyond the ramp
        out = np.maximum(out, out + (over - out) * w)
    return out


def gore(k, n_z=48, n_az=32):
    """Washi gore k (1..4): a quarter of the round plus GORE_OVERLAP_DEG at each seam, resting on the hoops (paper_r).
    It is sampled at every strip's edges and ramp ends, so the paper lies over each strip's full width. Attributes for
    root's paste progress: height_frac (0 at the bottom rim, 1 at the top) and azimuth_frac (0 at its leading seam)."""
    h = LANTERN_H / 2.0
    edges = [zk + sgn * e for zk in hoop_z() for sgn in (-1, 1) for e in (HOOP_W / 2, HOOP_W / 2 + RIB_RAMP)]
    zs = np.unique(np.round(np.concatenate([np.linspace(-h, h, n_z + 1), edges]), 9))
    zr = np.stack([zs, paper_r(zs) + 0.02 * (k - 1)], 1)       # later gores lie over earlier ones
    a0 = 180.0 + 90.0 * (k - 1) - GORE_OVERLAP_DEG
    return revolve(f"SM_B09_Washi{k}", zr, "M_B09_Washi", a0, a0 + 90.0 + 2 * GORE_OVERLAP_DEG, n_az)


def rim(which):
    """A rim (口輪), centred on its own pivot (the ring's centre); it moves between Rim*Rest and Rim*Seat."""
    zc = 0.0
    r_in = LANTERN_RIM_R - RIM_T / 2
    pts = [(zc - RIM_H / 2, r_in), (zc - RIM_H / 2, r_in + RIM_T), (zc + RIM_H / 2, r_in + RIM_T),
           (zc + RIM_H / 2, r_in), (zc - RIM_H / 2, r_in)]
    return revolve(f"SM_B09_Rim{which}", pts, "M_B09_RimLacquer", n_az=96)


def bail():
    h = LANTERN_H / 2.0 + RIM_H / 2
    pts = [[LANTERN_RIM_R * math.cos(t), 0.0, h + BAIL_RISE * math.sin(t)] for t in np.linspace(0, math.pi, 25)]
    ring = [[0.6 * math.cos(t), 0.0, h + BAIL_RISE + 0.6 + 0.6 * math.sin(t)] for t in np.linspace(0, 2 * math.pi, 13)]
    return merge("SM_B09_Bail", [sweep("SM_B09_Bail", pts, "M_B09_Iron", radius=0.12, segments=10),
                                 sweep("SM_B09_Bail", ring, "M_B09_Iron", radius=0.1, segments=10)])


def form(collapsed=False, boards=8):
    """The collapsible form (型): a spindle, two collars and radial boards just inside the hoops. Collapsed, the boards
    fold to 40% of their reach, as when the form is drawn out of a pasted lantern."""
    h = LANTERN_H / 2.0
    parts = [sweep("SM_B09_Form", [[0, 0, -h - 8], [0, 0, h + 16]], "M_B09_TimberForm", radius=1.25, segments=20)]
    for zc in (-h - 1.0, h + 1.0):
        parts.append(revolve("SM_B09_Form", [(zc - 1, 0.0), (zc - 1, 3.0), (zc + 1, 3.0), (zc + 1, 0.0)],
                             "M_B09_TimberForm", n_az=48))
    zs = np.linspace(-h, h, 23)
    reach = profile_r(zs) - 0.15
    if collapsed:
        reach = 1.3 + 0.4 * (reach - 1.3)
    for b in range(boards):
        th = math.radians(22.5 + 360.0 * b / boards)
        c, s = math.cos(th), math.sin(th)
        v, t = [], []
        for i, (z, rr) in enumerate(zip(zs, reach)):
            for side in (-0.4, 0.4):
                for rad in (1.3, rr):
                    v.append([rad * c - side * s, rad * s + side * c, z])
        for i in range(len(zs) - 1):
            q = [4 * i + j for j in range(8)]
            for a, b_, c_, d in ((q[0], q[1], q[4], q[5]), (q[2], q[3], q[6], q[7]), (q[1], q[3], q[5], q[7])):
                t += [[a, b_, c_], [b_, d, c_]]
        parts.append(Mesh("SM_B09_Form", np.array(v), np.array(t), "M_B09_TimberForm"))
    return merge("SM_B09_Form" + ("_Collapsed" if collapsed else ""), parts, "M_B09_TimberForm")


def lantern(stage):
    """The lantern at a stage: "frame" (form and six hoops), "papered" (+ four gores), "rimmed" (+ rims), "finished"
    (form drawn out, bail fitted: the oil rack's and the rafters' lantern). Lantern frame."""
    parts = [hoop(k) for k in range(1, 7)]
    if stage in ("frame", "papered", "rimmed"):
        parts.append(form())
    if stage in ("papered", "rimmed", "finished"):
        parts += [gore(k) for k in range(1, 5)]
    if stage in ("rimmed", "finished"):
        parts += [rim("Top").moved((0.0, 0.0, LANTERN_H / 2)), rim("Bottom").moved((0.0, 0.0, -LANTERN_H / 2))]
    if stage == "finished":
        parts.append(bail())
    return parts


# --- Stations -------------------------------------------------------------------------------------------------------
WORK_STAND = (-80.0, 0.0)                    # station frame: where the hero stands to work, facing +X
WORK_OBJECT = {"SM_B09_Form", "SM_B09_FormBase"} | {f"SM_B09_Hoop{k}" for k in range(1, 7)}
# The flex gauge: a dial on a post at the bench's right (the hero's right, +Y), its face toward the hero (-X).
# - Its pivot is above the highest hoop and beside the form, so the bending strip's free ends never sweep through it,
#   and it sits near the hero's line to the form.
# - The face is cream, the release band green (fixed: the 640-960 ms window), the ticks dark, the needle vermilion.
#   Root's review of v2 (2026-10-26 23:53) found the old gauge, low at the front-left in one colour, partly outside the
#   frame and with no readable band.
# - Angles are measured in the dial's plane from upright (+Z) toward the hero's right (+Y).
# - The needle sweeps the whole half-dial, -90 to +90 deg, over 0-960 ms, so the 640-960 ms release band spans 60 deg
#   (+30 to +90). The band then reads above 2 deg from the far edge of reach; a 40 deg band did not past about 2 m.
GAUGE = {"pivot": (-4.0, 34.0, 132.0), "radius": 11.0, "band_r": (8.0, 12.0), "face_r": 13.5,
         "angles_deg": (-90.0, 90.0), "full_ms": BEND_MS + BEND_TOL_MS, "ticks_ms": (0, 400, 800)}


def dial_point(angle_deg, radius, depth=0.0):
    """A point on the gauge's dial (station frame): its angle from upright toward +Y, its radius, and its depth toward
    the hero (-X) in front of the face."""
    g = np.array(GAUGE["pivot"])
    a = math.radians(angle_deg)
    return g + [-depth, radius * math.sin(a), radius * math.cos(a)]


def _sector(name, r0, r1, a0, a1, depth, thick, slot, n=24):
    """An annular sector of the dial, raised `thick` toward the hero from `depth` in front of the face."""
    v, t = [], []
    angles = np.linspace(a0, a1, n + 1)
    for a in angles:
        for d in (depth, depth + thick):
            for r in (r0, r1):
                v.append(dial_point(a, r, d))
    for i in range(n):
        q = [4 * i + j for j in range(8)]
        for a_, b_, c_, d_ in ((q[0], q[1], q[4], q[5]), (q[2], q[6], q[3], q[7]), (q[0], q[4], q[2], q[6]), (q[1], q[3], q[5], q[7])):
            t += [[a_, b_, c_], [b_, d_, c_]]
    return Mesh(name, np.array(v), np.array(t), slot)


def gauge_mesh(top):
    """The flex gauge (station frame): a foot and post from the bench top, the dial's face (an upper half-disc), the
    scale's dark rim, the green release band, and dark ticks at 0, 400 and 800 ms and at the band's edges."""
    g = np.array(GAUGE["pivot"])
    lo_b, hi_b = GAUGE["band_r"]
    band = (gauge_angle(BEND_MS - BEND_TOL_MS), gauge_angle(BEND_MS + BEND_TOL_MS))
    parts = [box("SM_B09_FlexGauge", (g[0] - 3, g[1] - 4, top), (g[0] + 3, g[1] + 4, top + 1.5), "M_B09_TimberBench"),
             box("SM_B09_FlexGauge", (g[0] - 0.8, g[1] - 1.2, top + 1.5), (g[0] + 0.8, g[1] + 1.2, g[2] - 0.5), "M_B09_TimberBench"),
             _sector("SM_B09_FlexGauge", 0.05, GAUGE["face_r"], -90.0, 90.0, -0.8, 0.8, "M_B09_GaugeFace", n=96),
             _sector("SM_B09_FlexGauge", hi_b, hi_b + 0.5, *GAUGE["angles_deg"], 0.02, 0.12, "M_B09_GaugeMarks", n=96),
             _sector("SM_B09_FlexGauge", lo_b, hi_b, *band, 0.02, 0.12, "M_B09_GaugeBand", n=32)]
    for a in sorted({gauge_angle(ms) for ms in GAUGE["ticks_ms"]} | set(band)):
        parts.append(_sector("SM_B09_FlexGauge", lo_b - 0.6, hi_b + 0.5, a - 0.9, a + 0.9, 0.02, 0.16, "M_B09_GaugeMarks", n=2))
    return merge("SM_B09_FlexGauge", parts, "M_B09_GaugeFace")


def gauge_angle(ms):
    """The flex gauge's needle (deg, about its pivot's X axis, 0 upright) at a held bend's elapsed ms."""
    a0, a1 = GAUGE["angles_deg"]
    return a0 + (a1 - a0) * min(max(ms, 0), GAUGE["full_ms"]) / GAUGE["full_ms"]


def flex_stage(ms):
    """The flexing strip's stage (an index into FLEX_STAGES) at a held bend's elapsed ms: fully bent at 800 ms."""
    f = min(max(ms, 0) / BEND_MS, 1.0)
    return int(round(f * (len(FLEX_STAGES) - 1)))


def weapon_rest():
    """Weapon 7 on the shell bench's cradle (station frame). Its bore runs along +Y. It is rolled so that its handle
    lies toward the back (+X) and its fuse faces the hero (-X)."""
    x_axis, z_axis = np.array([0.0, 1.0, 0.0]), np.array([-1.0, 0.0, 0.0])
    y_axis = np.cross(z_axis, x_axis)
    origin = np.array([12.0, -22.0, 72.0 + 6.0 + WEAPON7["culm_cm"] / 2])
    rot = np.stack([x_axis, y_axis, z_axis], 1)
    return origin, rot


def station_parts(i):
    """Each station's meshes in its frame, its sockets {name: (point, x_axis | None, z_axis | None)}, its collision
    proxies [(lo, hi)], and the work point the hero looks at."""
    lift = np.array([0.0, 0.0, LANTERN_Z.get(i, WORK_Z)])
    sockets, proxies = {}, []
    if i in (0, 1):
        depth, width, top = (60.0, 100.0, 75.0) if i == 0 else (70.0, 110.0, 75.0)
        parts = [bench("SM_B09_RibFormBench" if i == 0 else "SM_B09_PasteBench", depth, width, top)]
        base_top = lift[2] - LANTERN_H / 2 - 8.0                 # the form's spindle starts 8 cm below the lantern
        if base_top - top <= 6.0:
            parts.append(revolve("SM_B09_FormBase", [(top, 0.0), (top, 6.5), (top + 4, 6.5), (base_top, 2.0), (base_top, 0.0)],
                                 "M_B09_TimberForm", n_az=64))
        else:                                                    # a turned pedestal and turntable, to chest height
            parts.append(revolve("SM_B09_FormBase", [(top, 0.0), (top, 7.5), (top + 3, 7.5), (top + 3.5, 2.6), (base_top - 3.5, 2.6),
                                                     (base_top - 3, 6.5), (base_top, 6.5), (base_top, 0.0)], "M_B09_TimberForm", n_az=64))
        proxies.append((np.array([-depth / 2 - 2, -width / 2 - 2, 0.0]), np.array([depth / 2 + 2, width / 2 + 2, top + 3])))
        for k, (z, r) in enumerate(zip(hoop_z(), hoop_r()), 1):
            sockets[f"HoopSeat{k}"] = (lift + [0.0, 0.0, z], None, None)
        if i == 0:
            parts.append(form().moved(lift))
            g = np.array(GAUGE["pivot"])
            parts.append(gauge_mesh(top))
            sockets["GaugePivot"] = (g, np.array([1.0, 0.0, 0.0]), np.array([0.0, 0.0, 1.0]))
            stock = [sweep("SM_B09_StripStock", [[18.0 + 0.5 * (j % 4), -48.0, top + 0.3 + 0.2 * (j // 4)],
                                                  [18.0 + 0.5 * (j % 4), 48.0, top + 0.3 + 0.2 * (j // 4)]],
                           "M_B09_Bamboo", rect=(HOOP_W, HOOP_T), up=(1, 0, 0)) for j in range(12)]
            parts.append(merge("SM_B09_StripStock", stock))
            sockets["StripStock"] = (np.array([18.0, 0.0, top + 0.3]), np.array([0.0, 1.0, 0.0]), np.array([0.0, 0.0, 1.0]))
            sockets["SplitStripRest"] = (np.array([-18.0, -6.0, top + HOOP_T]), np.array([0.0, 1.0, 0.0]), np.array([0.0, 0.0, 1.0]))
            for side, y in (("L", 1), ("R", -1)):
                sockets[f"StripHold{side}"] = (lift + [-hoop_r()[0] - 4.0, y * 14.0, hoop_z()[0]], None, None)
        else:
            parts.append(form().moved(lift))
            for j in range(1, 5):
                sockets[f"WashiSheet{j}"] = (np.array([8.0, -34.5, top + 0.1 * (j - 1)]), None, None)
            parts += [m.moved(lift) for m in lantern("frame") if m.name != "SM_B09_Form"]   # the six hoops, done at the form
            parts.append(revolve("SM_B09_PastePot", [(top, 0.0), (top, 5.0), (top + 0.6, 6.0), (top + 6.5, 6.2), (top + 7.0, 5.6),
                                                     (top + 1.0, 5.3), (top + 1.0, 0.0)], "M_B09_Ceramic", n_az=48).moved((-20.0, -42.0, 0.0)))
            sockets["BrushRest"] = (np.array([-22.0, -32.0, top + 0.5]), np.array([1.0, 0.0, 0.0]), np.array([0.0, 0.0, 1.0]))
            for which, z in (("Bottom", RIM_H / 2), ("Top", 1.5 * RIM_H)):     # stacked, bottom rim under the top
                sockets[f"Rim{which}Rest"] = (np.array([14.0, 32.0, top + z]), None, None)
                sockets[f"Rim{which}Seat"] = (lift + [0.0, 0.0, (1 if which == "Top" else -1) * LANTERN_H / 2], None, None)
            sockets["Turntable"] = (np.array([0.0, 0.0, base_top]), np.array([1.0, 0.0, 0.0]), np.array([0.0, 0.0, 1.0]))
            for k in range(1, 5):
                az = math.radians(180.0 + 90.0 * (k - 1))
                for j, z in enumerate(np.linspace(-LANTERN_H / 2, LANTERN_H / 2, 9)):
                    r = float(paper_r(z)) + 0.6
                    sockets[f"Seam{k}_{j}"] = (lift + [r * math.cos(az), r * math.sin(az), z], None, None)
        work = lift
    elif i == 2:
        hp = hang_point()
        hook_top = lift[2] + hp[2]                              # the lantern hangs with its centre at chest height
        bar = hook_top + 13.0
        top = bar + 10.0
        parts = []
        for y in (-45.0, 45.0):
            parts.append(box("SM_B09_OilRack", (-3.0, y - 3, 5.0), (3.0, y + 3, top), "M_B09_TimberBench"))
            parts.append(box("SM_B09_OilRack", (-35.0, y - 3, 0.0), (35.0, y + 3, 5.0), "M_B09_TimberBench"))
        parts.append(box("SM_B09_OilRack", (-2.5, -48.0, bar), (2.5, 48.0, bar + 5.0), "M_B09_TimberBench"))
        parts.append(box("SM_B09_OilRack", (-20.0, -42.0, 18.0), (20.0, 42.0, 20.5), "M_B09_TimberBench"))
        parts = [merge("SM_B09_OilRack", parts)]
        parts.append(sweep("SM_B09_RackHook", [[0, 0, bar], [0, 0, hook_top + 1.8], [0.9, 0, hook_top + 0.6], [0, 0, hook_top]],
                           "M_B09_Iron", radius=0.25, segments=10))
        parts.append(revolve("SM_B09_OilJar", [(20.5, 0.0), (20.5, 6.0), (24.0, 8.8), (34.0, 9.0), (41.0, 6.5), (43.5, 4.2),
                                               (44.5, 4.6), (44.5, 3.6), (36.0, 3.2), (36.0, 0.0)], "M_B09_Ceramic", n_az=64).moved((8.0, 24.0, 0.0)))
        parts.append(revolve("SM_B09_DripTray", [(0.0, 0.0), (0.0, 17.0), (3.0, 18.0), (3.0, 17.2), (0.8, 16.4), (0.8, 0.0)],
                             "M_B09_Ceramic", n_az=64))
        proxies.append((np.array([-38.0, -52.0, 0.0]), np.array([38.0, 52.0, 22.0])))
        sockets["LanternHang"] = (np.array([0.0, 0.0, hook_top]), None, None)
        sockets["OilJar"] = (np.array([8.0, 24.0, 44.5]), None, None)
        # The oil brush rests across the jar's mouth, its tip over the oil.
        sockets["BrushRest"] = (np.array([8.0, 22.0, 45.1]), np.array([1.0, 0.0, 0.0]), np.array([0.0, 0.0, 1.0]))
        for j, z in enumerate(np.linspace(LANTERN_H / 2, -LANTERN_H / 2, 9)):
            for q, az in enumerate((180.0, 225.0, 135.0)):
                r = float(paper_r(z)) + 0.7
                a = math.radians(az)
                sockets[f"OilStroke{q}_{j}"] = (lift + [r * math.cos(a), r * math.sin(a), z], None, None)
        work = lift
    else:
        top = 72.0
        parts = [bench("SM_B09_ShellBench", 70.0, 120.0, top)]
        proxies.append((np.array([-37.0, -62.0, 0.0]), np.array([37.0, 62.0, top + 3])))
        origin, rot = weapon_rest()
        for y in (origin[1] + 14.0, origin[1] + 52.0):              # along the culm, ahead of the handle plug
            parts.append(merge("SM_B09_WeaponCradle", [box("SM_B09_WeaponCradle", (origin[0] - 6, y - 2.5, top), (origin[0] - 4, y + 2.5, origin[2] - 1.0), "M_B09_TimberBench"),
                                                       box("SM_B09_WeaponCradle", (origin[0] + 4, y - 2.5, top), (origin[0] + 6, y + 2.5, origin[2] - 1.0), "M_B09_TimberBench"),
                                                       box("SM_B09_WeaponCradle", (origin[0] - 6, y - 2.5, top), (origin[0] + 6, y + 2.5, top + 2.0), "M_B09_TimberBench")]))
        parts = parts[:1] + [merge("SM_B09_WeaponCradle", parts[1:])]
        sockets["WeaponRest"] = (origin, rot[:, 0], rot[:, 2])
        sockets["Muzzle"] = (origin + rot @ np.array(WEAPON7["muzzle_cm"]), rot[:, 0], rot[:, 2])
        sockets["FuseInspect"] = (origin + rot @ np.array(WEAPON7["fuse_cm"]), rot[:, 0], rot[:, 2])
        rack_lo, rack_hi = np.array([-24.0, -50.0, top]), np.array([-15.0, -24.0, top + 4.0])
        parts.append(box("SM_B09_ShellRack", rack_lo, rack_hi, "M_B09_TimberBench"))
        for k, y in enumerate((-45.0, -37.0, -29.0), 1):
            sockets[f"ShellSeat{k}"] = (np.array([-19.5, y, top + 4.0 - 2.0 + SHELL["wrapped_cm"] / 2]), None, np.array([0.0, 0.0, 1.0]))
            sockets[f"ShellCore{k}"] = (np.array([-18.0, 30.0 + 5.5 * (k - 2), top + 1.5 + SHELL["core_cm"] / 2]), None, None)
        parts.append(revolve("SM_B09_ShellTray", [(top, 0.0), (top, 9.0), (top + 3.0, 9.6), (top + 3.0, 9.0), (top + 1.0, 8.4), (top + 1.0, 0.0)],
                             "M_B09_TimberBench", n_az=64).moved((-18.0, 30.0, 0.0)))
        parts.append(box("SM_B09_WrapPaper", (-30.0, -8.0, top), (-10.0, 12.0, top + 0.2), "M_B09_ShellPaper"))
        sockets["WrapSpot"] = (np.array([-20.0, 2.0, top + 0.2 + SHELL["wrapped_cm"] / 2]), None, None)
        coil = [[-4.0 + (2.0 + 0.32 * t) * math.cos(t), 48.0 + (2.0 + 0.32 * t) * math.sin(t), top + 0.25] for t in np.linspace(0, 5 * math.pi, 90)]
        parts.append(sweep("SM_B09_FuseCoil", coil, "M_B09_FuseCord", radius=0.25, segments=10))
        sockets["FuseCoil"] = (np.array([-4.0, 48.0, top + 0.5]), None, None)
        work = np.array([-12.0, -10.0, top + 8.0])
    sockets["StationPoint"] = (np.array([0.0, 0.0, WORK_Z]), None, None)      # the trace's target, wherever the lantern sits
    sockets["WorkStand"] = (np.array([WORK_STAND[0], WORK_STAND[1], 0.0]), np.array([1.0, 0.0, 0.0]), np.array([0.0, 0.0, 1.0]))
    return parts, sockets, proxies, work


def needle():
    """The flex gauge's needle: its hinge at the origin, pointing upright (+Z), a tapered vermilion blade 0.3 cm in
    front of the face. Root turns it in the dial's plane so it points along (0, sin a, cos a), a = gauge_angle(ms)."""
    r = GAUGE["band_r"][1] - 0.4
    v = np.array([[-0.3, -0.45, -1.2], [-0.3, 0.45, -1.2], [-0.3, 0.12, r], [-0.3, -0.12, r],
                  [-0.6, -0.45, -1.2], [-0.6, 0.45, -1.2], [-0.6, 0.12, r], [-0.6, -0.12, r]])
    t = np.array([[0, 1, 2], [0, 2, 3], [4, 6, 5], [4, 7, 6], [0, 4, 5], [0, 5, 1], [1, 5, 6], [1, 6, 2], [2, 6, 7], [2, 7, 3], [3, 7, 4], [3, 4, 0]])
    hub = revolve("SM_B09_GaugeNeedle", [(-0.75, 0.0), (-0.75, 0.9), (-0.2, 0.9), (-0.2, 0.0)], "M_B09_Iron", n_az=24)
    hub.verts = hub.verts[:, [2, 1, 0]]                    # its axis along X
    hub.tris = hub.tris[:, [0, 2, 1]]
    return merge("SM_B09_GaugeNeedle", [Mesh("SM_B09_GaugeNeedle", v, t, "M_B09_GaugeNeedle"), hub], "M_B09_GaugeNeedle")


def needle_at(ms):
    """The needle placed on the dial at a held bend's elapsed ms (station frame)."""
    a = math.radians(gauge_angle(ms))
    rot = np.array([[1.0, 0.0, 0.0], [0.0, math.cos(a), math.sin(a)], [0.0, -math.sin(a), math.cos(a)]])  # +Z -> (0, sin a, cos a)
    return needle().moved(GAUGE["pivot"], rot=rot)


def state_meshes(i):
    """The meshes a station's view state shows, each with its pivot: [(mesh, pivot description, where root places it)]."""
    lf = "the lantern's centre"
    if i == 0:
        rows = [(hoop(k, f), lf, "LanternCentre") for k in range(1, 7) for f in FLEX_STAGES]
        rows += [(split_strip(), "its middle, lying flat", "SplitStripRest"), (needle(), "its hinge", "GaugePivot")]
    elif i == 1:
        rows = [(gore(k), lf, "LanternCentre (turned by the turntable)") for k in range(1, 5)]
        rows += [(box(f"SM_B09_WashiSheet{j}", (-14.0, -12.5, 0.0), (14.0, 12.5, 0.1), "M_B09_Washi"),
                  "its bottom face's centre", f"WashiSheet{j} (the stack: sheet 4 on top, taken first)") for j in range(1, 5)]
        rows += [(rim(w), "the ring's centre", f"Rim{w}Rest, then Rim{w}Seat") for w in ("Top", "Bottom")]
        rows.append((brush("SM_B09_PasteBrush", 6.0), "the bristles' tip", "BrushRest, then along Seam{k}_0..8"))
    elif i == 2:
        rows = [(merge("SM_B09_LanternFinished", lantern("finished")), lf + "; it hangs from its hang point", "LanternHang - hang_point")]
        rows.append((brush("SM_B09_OilBrush", 5.0, 4.0, 16.0), "the bristles' tip", "BrushRest, then along OilStroke*"))
    else:
        rows = [(shell("core"), "its centre", "ShellCore1..3"), (shell("wrapped"), "its centre", "WrapSpot, then ShellSeat1..3")]
    return rows


# --- Shells ---------------------------------------------------------------------------------------------------------
SHELL = {"core_cm": 4.8, "wrapped_cm": 5.4, "neck_cm": 1.6}


def shell(stage):
    """A festival shell: "core" (the paste-and-paper ball, 4.8 cm, with its fuse stub) or "wrapped" (5.4 cm, its paper
    gathered into a twisted neck and tied). Frame: its centre. The bore is 5.6 cm, so a wrapped shell seats with 1 mm
    clear all round."""
    d = SHELL["core_cm"] if stage == "core" else SHELL["wrapped_cm"]
    parts = [sphere("SM_B09_Shell" + stage.title(), d / 2, "M_B09_ShellPaper" if stage == "wrapped" else "M_B09_ShellCore")]
    top = d / 2
    if stage == "wrapped":
        neck = [(top - 0.3, 0.9), (top + 0.4, 0.45), (top + SHELL["neck_cm"] - 0.3, 0.35), (top + SHELL["neck_cm"], 0.6)]
        parts.append(revolve("SM_B09_ShellWrapped", neck, "M_B09_ShellPaper", n_az=24))
        parts.append(revolve("SM_B09_ShellWrapped", [(top + 0.5, 0.52), (top + 0.5, 0.62), (top + 0.8, 0.62), (top + 0.8, 0.52)],
                             "M_B09_Twine", n_az=24))
        fuse_from = top + SHELL["neck_cm"]
    else:
        fuse_from = top
    parts.append(sweep("SM_B09_Shell" + stage.title(), [[0, 0, fuse_from - 0.2], [0.1, 0, fuse_from + 1.8], [0.5, 0, fuse_from + 3.0]],
                       "M_B09_FuseCord", radius=0.18, segments=10))
    return merge("SM_B09_Shell" + stage.title(), parts)


# --- The hanging output -------------------------------------------------------------------------------------------------
POLES_Y = (-560.0, -820.0, -1080.0, -1340.0)
POLE_Z = 395.0
POLE_X = (1795.0, 2305.0)                    # inside the walls (inner faces x 1606 and 2314)
SLOT_X = tuple(1830.0 + 50.0 * i for i in range(10))
PLAYER_SLOT = 36                             # pole 4 (nearest the oil rack), the 7th hook (x 2130)


def slots():
    """The 40 hook slots (world cm): (pole, index, hook point, yaw deg). Each lantern's yaw is a fixed jitter, so the
    painted mon faces vary."""
    out = []
    for p, y in enumerate(POLES_Y):
        for i, x in enumerate(SLOT_X):
            k = p * 10 + i
            yaw = float((k * 137.508) % 360.0)
            out.append((p, i, np.array([x, y + 2.4, POLE_Z - 4.0]), yaw))
    return out


def hanging_parts():
    parts = []
    for y in POLES_Y:
        parts.append(sweep("SM_B09_DryingPole", [[POLE_X[0], y, POLE_Z], [POLE_X[1], y, POLE_Z]], "M_B09_Bamboo", radius=2.0, segments=24))
        for x in (POLE_X[0] + 40.0, POLE_X[1] - 40.0):
            parts.append(sweep("SM_B09_PoleHanger", [[x, y, CEILING_Z], [x, y, POLE_Z + 2.0]], "M_B09_Cord", radius=0.35, segments=10))
    hooks = []
    for _, _, hp, _ in slots():
        top = np.array([hp[0], hp[1] - 2.4, POLE_Z + 2.3])
        hooks.append(sweep("SM_B09_SlotHook", [top + [0, -0.6, -0.4], top + [0, 0.4, 0.2], top + [0, 2.4, -1.2], hp + [0, 0, 1.0],
                                               hp + [0, 0.3, 0.0], hp + [0, 0.6, 0.6]],
                           "M_B09_Iron", radius=0.18, segments=10))
    return merge("SM_B09_DryingPoles", parts, "M_B09_Bamboo"), merge("SM_B09_SlotHooks", hooks, "M_B09_Iron")


# --- Checks ---------------------------------------------------------------------------------------------------------
def segment_hits_box(a, b, lo, hi):
    """Whether the segment a-b passes through the open box (lo, hi)."""
    d = b - a
    t0, t1 = 0.0, 1.0
    for k in range(3):
        if abs(d[k]) < 1e-12:
            if a[k] <= lo[k] or a[k] >= hi[k]:
                return False
            continue
        ta, tb = (lo[k] - a[k]) / d[k], (hi[k] - a[k]) / d[k]
        t0, t1 = max(t0, min(ta, tb)), min(t1, max(ta, tb))
        if t0 >= t1:
            return False
    return True


def circle_hits_box2d(c, r, lo, hi):
    q = np.clip(c, lo[:2], hi[:2])
    return float(np.linalg.norm(c - q)) < r


def eligible(i, x, y, proxies_world):
    """Whether the hero could stand at (x, y) to work station i: reach, floor, and a capsule clear of the walls and
    the proxies (in plan)."""
    sx, sy = STATIONS[i][1]
    fz = floor_at(sx, sy)
    if math.hypot(x - sx, y - sy) >= REACH_CM or abs(floor_at(x, y) - fz) > FEET_TOL_CM:
        return False
    c = np.array([x, y])
    for k, (cc, size) in enumerate(SOLIDS):
        if k in FLOOR_SLABS:
            continue
        lo, hi = cc - size / 2, cc + size / 2
        if hi[2] > fz + 2 and lo[2] < fz + 2 * CAPSULE_HALF and circle_hits_box2d(c, CAPSULE_R, lo, hi):
            return False
    for lo, hi in proxies_world:
        if circle_hits_box2d(c, CAPSULE_R, lo, hi):
            return False
    return True


def clearance(i, step=10.0):
    """Station i's clearances: the work stand, the eye's line to the work, and every eligible station ray against the
    proposed proxies (and the room's own solids, which the trace already meets today).

    The rays start at the **standing** capsule's centre (RAY_FROM_Z). The crouched rays, from CROUCH_HALF, are a CPU
    estimate for root: the same plan positions and boxes, not root's crouch or native coverage."""
    parts, sockets, proxies, work = station_parts(i)
    sx, sy = STATIONS[i][1]
    fz = floor_at(sx, sy)
    o = np.array([sx, sy, fz])
    pw = [(lo + o, hi + o) for lo, hi in proxies]
    others = []
    for j, (_, (xj, yj)) in enumerate(STATIONS):
        if j != i:
            oj = np.array([xj, yj, floor_at(xj, yj)])
            others += [(lo + oj, hi + oj) for lo, hi in station_parts(j)[2]]
    stand = o + [WORK_STAND[0], WORK_STAND[1], 0.0]
    ray_end = o + [0.0, 0.0, RAY_TO_Z]
    positions = [(x, y) for x in np.arange(sx - REACH_CM, sx + REACH_CM + 1, step) for y in np.arange(sy - REACH_CM, sy + REACH_CM + 1, step)]
    ok = [(x, y) for x, y in positions if eligible(i, x, y, pw + others)]
    blocked_by_proxy = [(x, y) for x, y in ok if any(segment_hits_box(np.array([x, y, fz + RAY_FROM_Z]), ray_end, lo, hi) for lo, hi in pw)]
    walls = [(cc - size / 2, cc + size / 2) for k, (cc, size) in enumerate(SOLIDS) if k not in FLOOR_SLABS]
    blocked_by_room = [(x, y) for x, y in ok if any(segment_hits_box(np.array([x, y, fz + RAY_FROM_Z]), ray_end, lo, hi) for lo, hi in walls)]
    crouched = [(x, y) for x, y in ok if any(segment_hits_box(np.array([x, y, fz + CROUCH_HALF]), ray_end, lo, hi) for lo, hi in pw)]
    # The hero at the work stand: the capsule's gap to every part, and the eye's line to the work point.
    capsule_gap = min(_capsule_gap(stand, m.moved(o)) for m in parts)
    eye = stand + [EYE[0], EYE[1], CAPSULE_HALF + EYE[2]]
    wp = work + o
    sight = wp - eye
    occluders = sorted({m.name for m in parts if m.name not in WORK_OBJECT and _segment_meets_mesh(eye, wp, m.moved(o))})
    pitch = math.degrees(math.atan2(sight[2], math.hypot(sight[0], sight[1])))
    return {"posture": "standing: rays from the capsule's centre at 88 cm. Crouched (half-height 44) is not covered by "
                       "this proof; crouched and native coverage are root's",
            "eligible_positions": len(ok), "grid_cm": step,
            "rays_blocked_by_proposed_proxies": len(blocked_by_proxy), "rays_blocked_by_room_today": len(blocked_by_room),
            "crouched_estimate": {"ray_from_cm": CROUCH_HALF, "rays_blocked_by_proposed_proxies": len(crouched),
                                  "note": "a CPU estimate on the same plan positions and boxes, not root's coverage"},
            "work_stand_eligible": eligible(i, stand[0], stand[1], pw),
            "work_stand_ray_clear": not any(segment_hits_box(stand + [0, 0, RAY_FROM_Z], ray_end, lo, hi) for lo, hi in pw + walls),
            "capsule_gap_cm": round(capsule_gap, 2), "eye_to_work_cm": round(float(np.linalg.norm(sight)), 1),
            "eye_pitch_deg": round(pitch, 1), "sight_occluded_by": occluders,
            "proxy_tops_cm": [round(float(hi[2]), 1) for lo, hi in proxies]}


def _capsule_gap(stand, mesh):
    """The plan gap between the hero's capsule at the stand and a mesh's bounds (cm), if the mesh rises into the
    capsule's height. Bounds hold the mesh, so the true gap is at least this."""
    lo, hi = mesh.bounds()
    if hi[2] < stand[2] or lo[2] > stand[2] + 2 * CAPSULE_HALF:
        return float("inf")
    q = np.clip(stand[:2], lo[:2], hi[:2])
    return float(np.linalg.norm(stand[:2] - q) - CAPSULE_R)


def _segment_meets_mesh(a, b, mesh, stop=1.0):
    """Whether the segment a -> a + stop (b - a) crosses any of the mesh's triangles (Moller-Trumbore)."""
    d = (b - a) * stop
    v0, v1, v2 = mesh.verts[mesh.tris[:, 0]], mesh.verts[mesh.tris[:, 1]], mesh.verts[mesh.tris[:, 2]]
    e1, e2 = v1 - v0, v2 - v0
    p = np.cross(d, e2)
    det = (e1 * p).sum(1)
    ok = np.abs(det) > 1e-12
    inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
    s = a - v0
    u = (s * p).sum(1) * inv
    q = np.cross(s, e1)
    w = (q * d).sum(1) * inv          # the second barycentric
    t = (e2 * q).sum(1) * inv
    hit = ok & (u >= 0) & (w >= 0) & (u + w <= 1) & (t > 1e-6) & (t < 1.0)
    return bool(hit.any())


# --- First-person view ------------------------------------------------------------------------------------------------
VIEW_MARGIN_DEG = 2.0
DIAL_FACING_DEG = 65.0                       # the dial reads from within this angle of its face's normal
BAND_MIN_DEG = 2.0                           # the release band subtends at least this (about 41 px at 1920 across)


def key_points(i):
    """Each station's elements the hero must see while working it, as station-frame sample points:
    {element: (points, meshes of the element itself)}."""
    lift = np.array([0.0, 0.0, LANTERN_Z.get(i, WORK_Z)])
    if i == 0:
        band = (gauge_angle(BEND_MS - BEND_TOL_MS), gauge_angle(BEND_MS + BEND_TOL_MS))
        dial = [dial_point(a, r, 0.1) for a in (*GAUGE["angles_deg"], *band) for r in (GAUGE["band_r"][0], GAUGE["band_r"][1] + 0.5)]
        dial += [dial_point(a, GAUGE["band_r"][1] - 0.4, 0.45) for a in np.linspace(*GAUGE["angles_deg"], 7)]   # the needle's tip
        dial.append(np.array(GAUGE["pivot"]) - [0.45, 0, 0])
        hoops = [lift + [-r - HOOP_T, 0.0, z] for z, r in zip(hoop_z(), hoop_r())]
        return {"gauge": (dial, {"SM_B09_FlexGauge"}), "hoops": (hoops, WORK_OBJECT)}
    if i == 1:
        _, sockets, _, _ = station_parts(1)
        # The seam's bottom end, at the rim line, is reported. From standing eye height the lantern's lower flare hides
        # it, as a real lantern's would. The v5 gores' coarse facets dipped inside that flare and passed it; the
        # 48-row gores resolve it.
        return {"seam": ([sockets[f"Seam1_{j}"][0] for j in range(1, 9)], WORK_OBJECT),
                "seam's bottom end at the rim (reported)": ([sockets["Seam1_0"][0]], WORK_OBJECT)}
    if i == 2:
        _, sockets, _, _ = station_parts(2)
        # The front stroke is required. The side strokes (+-45 deg) are reported: their lowest samples, on the bottom
        # shoulder, hide behind the belly from standing eye height, as a real lantern's do.
        return {"oil front stroke": ([sockets[f"OilStroke0_{j}"][0] for j in range(9)], set()),
                "oil side strokes (reported)": ([sockets[f"OilStroke{q}_{j}"][0] for q in (1, 2) for j in range(9)], set())}
    _, sockets, _, _ = station_parts(3)
    return {"shells": ([sockets[k][0] for k in ("ShellSeat1", "ShellSeat2", "ShellSeat3", "WrapSpot")], {"SM_B09_ShellRack", "SM_B09_WrapPaper"}),
            "fuse": ([sockets["FuseInspect"][0], sockets["Muzzle"][0]], set())}


def _camera(eye, target):
    f = np.asarray(target, float) - eye
    f /= np.linalg.norm(f)
    r = np.cross([0.0, 0.0, 1.0], f)
    r /= np.linalg.norm(r)
    return f, r, np.cross(f, r)


def in_view(eye, target, points, aspect, hfov=WORLD_HFOV_DEG, margin=VIEW_MARGIN_DEG):
    """Whether every point is inside the camera's frame, `margin` deg in from its edges, looking from eye at target.
    The frame keeps `hfov` across and loses height at wider aspects, as the hero's camera does."""
    f, r, u = _camera(eye, target)
    tx = math.tan(math.radians(hfov / 2 - margin))
    ty = math.tan(math.atan(math.tan(math.radians(hfov / 2)) / aspect) - math.radians(margin))
    for p in points:
        d = np.asarray(p, float) - eye
        z = d @ f
        if z <= 0 or abs(d @ r) / z > tx or abs(d @ u) / z > ty:
            return False
    return True


def view_check(i, eye, meshes, aspect):
    """For each key element of station i (station frame): in the frame looking at the work, unoccluded by the
    station's other meshes, and, for the gauge, facing the eye and large enough to read."""
    _, _, _, work = station_parts(i)
    out = {}
    for name, (points, own) in key_points(i).items():
        others = [m for m in meshes if m.name not in own]
        visible = in_view(eye, work, points, aspect)
        occluded = [m.name for m in others if any(_segment_meets_mesh(eye, eye + (p - eye) * 0.995, m) for p in points)]
        row = {"in_frame": visible, "occluded_by": sorted(set(occluded))}
        if name == "gauge":
            g = np.array(GAUGE["pivot"])
            to_eye = (eye - g) / np.linalg.norm(eye - g)
            row["facing_deg"] = round(math.degrees(math.acos(np.clip(to_eye @ [-1.0, 0.0, 0.0], -1, 1))), 1)
            rm = sum(GAUGE["band_r"]) / 2
            a, b = (dial_point(gauge_angle(ms), rm, 0.1) - eye for ms in (BEND_MS - BEND_TOL_MS, BEND_MS + BEND_TOL_MS))
            row["band_deg"] = round(math.degrees(math.acos(np.clip(a @ b / np.linalg.norm(a) / np.linalg.norm(b), -1, 1))), 2)
            row["ok"] = visible and not occluded and row["facing_deg"] <= DIAL_FACING_DEG and row["band_deg"] >= BAND_MIN_DEG
        else:
            row["ok"] = visible and not occluded
        out[name] = row
    return out


def approach_positions(i, step=10.0):
    """The working side: eligible positions in front of the bench (station frame x <= -40) within 60 deg of the
    approach (-X), in station-frame cm."""
    sx, sy = STATIONS[i][1]
    o = np.array([sx, sy, floor_at(sx, sy)])
    pw = []
    for j, (_, (xj, yj)) in enumerate(STATIONS):
        oj = np.array([xj, yj, floor_at(xj, yj)])
        pw += [(lo + oj, hi + oj) for lo, hi in station_parts(j)[2]]
    out = []
    for lx in np.arange(-REACH_CM, -40.0 + 1e-9, step):
        for ly in np.arange(-REACH_CM, REACH_CM + 1e-9, step):
            if abs(ly) <= math.tan(math.radians(60.0)) * -lx and eligible(i, sx + lx, sy + ly, pw):
                out.append(np.array([lx, ly, 0.0]))
    return out


def first_person(i, step=10.0):
    """Station i's first-person check: at the work stand, and the share of the working side's positions at which each
    element passes, for each aspect."""
    parts, sockets, proxies, work = station_parts(i)
    meshes = list(parts)
    if i == 0:
        meshes += [hoop(k).moved((0, 0, LANTERN_Z[0])) for k in range(1, 7)]
    elif i == 1:
        meshes += [gore(k).moved((0, 0, LANTERN_Z[1])) for k in (2, 3, 4)]  # the gores already pasted, the seam's own one aside
    elif i == 2:
        meshes += [m.moved(sockets["LanternHang"][0] - hang_point()) for m in lantern("finished")]
    eye_of = lambda pos: pos + [EYE[0], EYE[1], CAPSULE_HALF + EYE[2]]  # noqa: E731
    stand = np.array([WORK_STAND[0], WORK_STAND[1], 0.0])
    out = {"hfov_deg": WORLD_HFOV_DEG, "margin_deg": VIEW_MARGIN_DEG, "stand": {}, "approach": {}}
    positions = approach_positions(i, step)
    out["approach_positions"] = len(positions)
    for label, aspect in ASPECTS.items():
        out["stand"][label] = view_check(i, eye_of(stand), meshes, aspect)
        tally = {}
        for pos in positions:
            for name, row in view_check(i, eye_of(pos), meshes, aspect).items():
                tally.setdefault(name, []).append(row["ok"])
        out["approach"][label] = {name: round(float(np.mean(v)), 4) for name, v in tally.items()}
    return out


def hanging_clearance():
    """The hanging output: every lantern clear of the hero's head over its floor, of the ceiling, of the walls, and of
    its neighbours."""
    hp = hang_point()
    rows, low = [], []
    for p, i, point, yaw in slots():
        centre = point - hp
        bottom = centre[2] - LANTERN_H / 2 - RIM_H / 2
        fz = floor_at(point[0], point[1])
        rows.append({"slot": p * 10 + i + 1, "bottom_above_head_cm": round(bottom - (fz + HEAD_TOP_CM), 1)})
        low.append(bottom - (fz + HEAD_TOP_CM))
    xs = np.array(SLOT_X)
    return {"slots": len(rows), "min_head_clear_cm": round(float(min(low)), 1),
            "hook_top_below_ceiling_cm": round(CEILING_Z - (POLE_Z + 2.0), 1),
            "neighbour_gap_cm": round(float(np.diff(xs).min() - 2 * LANTERN_R), 1),
            "pole_gap_cm": round(float(np.diff(sorted(POLES_Y)).min() - 2 * LANTERN_R), 1),
            "inside_room": bool(POLE_X[0] > 1606 and POLE_X[1] < 2314 and min(POLES_Y) > -1494 and max(POLES_Y) < -406)}


def bore_fit():
    r_clear = (WEAPON7["bore_cm"] - SHELL["wrapped_cm"]) / 2
    return {"bore_cm": WEAPON7["bore_cm"], "wrapped_shell_cm": SHELL["wrapped_cm"], "radial_clear_mm": round(r_clear * 10, 2)}


# --- The spec ---------------------------------------------------------------------------------------------------------
# Root's view (SoraWorkshopCraftRules::FView, read as FSoraKitView::LanternCraft at 2a846a6a): Active, RecipeComplete,
# Assist; Step; Committed[6] in recipe order; HeldStep (-1 idle) and HeldMs; FailedStripSerial and FailedStripAgeMs (-1
# absent). The presentation reads it and never advances it. A new press clears the split pose, pause or cancel clears
# held work, and a retry clears the failure, all in root's state. The art keeps no state of its own.
VIEW_CONTRACT = ("SoraWorkshopCraftRules::FView via FSoraKitView::LanternCraft: Active, RecipeComplete, Assist, Step, "
                 "Committed[6], HeldStep, HeldMs, FailedStripSerial, FailedStripAgeMs")
SPLIT_SHOW_MS = 1200                         # a suggestion: how long the split strip lies on the bench (root's choice)
STATES = {
    "st_b09_rib_form": [
        {"view": "Committed[0] = n (0..6)", "shows": "SM_B09_Hoop1..n on the form (HoopSeat1..n)"},
        {"view": "HeldStep == 0, HeldMs", "shows": "hoop n+1's strip at flex_stage(HeldMs) (SM_B09_Hoop{n+1}_Flex000..075, "
                                                   "then Hoop{n+1}); the needle along gauge_angle(HeldMs)"},
        {"view": "HeldStep == -1", "shows": "the needle at rest (gauge_angle(0), -90 deg); no strip on the form"},
        {"view": "FailedStripAgeMs >= 0", "shows": f"SM_B09_SplitStrip at SplitStripRest while FailedStripAgeMs < {SPLIT_SHOW_MS} "
                                                    "(suggested), then a fresh strip; a new press clears it (root's -1)"},
        {"view": "Assist", "shows": "the same gauge; the strip completes at 800 ms (the rules' assist pass)"}],
    "st_b09_paste_bench": [
        {"view": "Committed[0] == 6", "shows": "the form with all six hoops (the bends are done to come here)"},
        {"view": "Committed[1] = n (0..4)", "shows": "SM_B09_Washi1..n; the stack keeps sheets 1..4 - n (1..3 - n while a "
                                                     "paste is held: its sheet is Washi{n+1}); the turntable turns the "
                                                     "lantern by -90 deg x n about Z, so seam n+1 faces the hero"},
        {"view": "HeldStep == 1, HeldMs", "shows": "Washi{n+1} revealed to height_frac <= HeldMs / 1500 along seam n+1 "
                                                   "(sockets Seam{n+1}_0..8, bottom to top), the brush between them"},
        {"view": "Committed[2] == 1", "shows": "SM_B09_RimTop/Bottom from Rim*Rest to Rim*Seat"}],
    "st_b09_oil_rack": [
        {"view": "Committed[2] == 1, Committed[3] == 0", "shows": "the finished lantern (bail fitted, form drawn out) on "
                                                                  "LanternHang, dry washi; before that the rack is empty"},
        {"view": "HeldStep == 3, HeldMs", "shows": "oil wetness to height_frac >= 1 - HeldMs / 1500 (top down); the brush "
                                                   "along OilStroke0_0..8"},
        {"view": "Committed[3] == 1", "shows": "the rack empties; the lantern hangs at PLAYER_SLOT in the rafters"}],
    "st_b09_shell_bench": [
        {"view": "Committed[4] = n (0..3)", "shows": "n wrapped shells seated (ShellSeat1..n); 3 - n cores in the tray"},
        {"view": "Committed[5] == 1", "shows": "the fuse inspected (FuseInspect); weapon 7 is handed over at the beat's end"}],
    "all": [
        {"view": "RecipeComplete (later checkpoints)", "shows": "every station in its finished state and all 40 slots filled"},
        {"view": "!Active && !RecipeComplete", "shows": "every station at its start; the suggested 24 craftspeople's lanterns"}],
}


def spec():
    out = {"schema": 1, "generator": "scripts/art/b09_workshop_craft.py", "inputs": INPUTS,
           "frames": "Unreal cm, Z up. A station's frame: its origin is the station point on its floor (world X, Y, "
                     "FloorAt), with the world's axes. The hero works from -X, facing +X.",
           "view_contract": VIEW_CONTRACT, "states_all": STATES["all"],
           "recipe": {"steps": [{"step": k, "kind": kind, "count": n, "station": STATIONS[STEP_STATIONS[k]][0]}
                                for k, (kind, n) in enumerate(STEPS)], "bend_ms": [BEND_MS, BEND_TOL_MS], "paste_ms": PASTE_MS,
                      "output_lanterns": OUTPUT_LANTERNS},
           "collision": "every mesh is visual only; root keeps or replaces its boxes with the proposed proxies. Each "
                        "proxy is under the standing station trace's 88 cm start, so no standing ray meets one. That "
                        "covers the standing capsule only: crouched (half-height 44) the trace starts at 44 cm, and "
                        "proxy tops of 75-78 cm can block close crouched approaches, as today's generic benches can. "
                        "Crouched and native coverage are root's",
           "lantern": {"height_cm": LANTERN_H, "diameter_cm": 2 * LANTERN_R, "rim_diameter_cm": 2 * LANTERN_RIM_R,
                       "hoop_heights_cm": [round(float(z), 3) for z in hoop_z()], "hoop_radii_cm": [round(float(r), 3) for r in hoop_r()],
                       "hang_point_cm": hang_point().round(3).tolist(), "flex_stages": list(FLEX_STAGES),
                       "pivot": "its centre (lantern frame); at the rib form and paste bench it sits at the station point"},
           "camera": {"world_hfov_deg": WORLD_HFOV_DEG, "aspects": list(ASPECTS), "margin_deg": VIEW_MARGIN_DEG,
                      "dial_facing_max_deg": DIAL_FACING_DEG, "band_min_deg": BAND_MIN_DEG,
                      "note": "a CPU geometric estimate of framing from the standing eye; it does not establish Unreal framing, "
                              "materials or hand contact"},
           "lantern_centre_by_station_cm": {STATIONS[k][0]: z for k, z in LANTERN_Z.items()},
           "gauge": {"pivot_cm": list(GAUGE["pivot"]), "angles_deg": list(GAUGE["angles_deg"]), "full_ms": GAUGE["full_ms"],
                     "band_radii_cm": list(GAUGE["band_r"]), "face_radius_cm": GAUGE["face_r"], "ticks_ms": list(GAUGE["ticks_ms"]),
                     "needle": "points along (0, sin a, cos a) in the station frame, a = gauge_angle(ms)",
                     "green_band_deg": [round(gauge_angle(BEND_MS - BEND_TOL_MS), 2), round(gauge_angle(BEND_MS + BEND_TOL_MS), 2)]},
           "shells": dict(SHELL, bore_fit=bore_fit()),
           # For review captures only: root's solids as (centre, size); collision stays root's.
           "room": {"solids_cm": [np.concatenate([c, s]).round(3).tolist() for c, s in SOLIDS],
                    "floor_slabs": list(FLOOR_SLABS),
                    "ceilings": [k for k, (c, s) in enumerate(SOLIDS) if c[2] - s[2] / 2 >= CEILING_Z],
                    "surfaces": list(SOLID_SURFACES),
                    "source": "SoraLanternWorkshopRules::Solids (the ground slab left out)"},
           "stations": [], "hanging_output": {}}
    for i, (sid, (x, y)) in enumerate(STATIONS):
        parts, sockets, proxies, work = station_parts(i)
        row = {"id": sid, "index": i, "world_cm": [x, y], "floor_cm": floor_at(x, y),
               "steps": [k for k, s in enumerate(STEP_STATIONS) if s == i],
               "work_stand": {"local_cm": [WORK_STAND[0], WORK_STAND[1], 0.0], "yaw_deg": 0.0},
               "work_point_cm": [round(float(c), 2) for c in work],
               "parts": [], "sockets": {}, "collision_proxies": [], "states": STATES[sid], "clearance": clearance(i)}
        for m in parts:
            lo, hi = m.bounds()
            row["parts"].append({"name": m.name, "slots": sorted(set(m.slots())), "triangles": int(len(m.tris)),
                                 "bounds_cm": [lo.round(2).tolist(), hi.round(2).tolist()],
                                 "pivot": "station frame origin", "collision": m.collision})
        for name, (p, xa, za) in sorted(sockets.items()):
            row["sockets"][name] = {"cm": np.round(p, 3).tolist()} | ({"x_axis": np.round(xa, 6).tolist()} if xa is not None else {}) | \
                ({"z_axis": np.round(za, 6).tolist()} if za is not None else {})
        for lo, hi in proxies:
            row["collision_proxies"].append({"lo_cm": np.round(lo, 2).tolist(), "hi_cm": np.round(hi, 2).tolist()})
        if i in (0, 1):
            row["sockets"]["LanternCentre"] = {"cm": [0.0, 0.0, LANTERN_Z[i]]}
        row["state_meshes"] = []
        for m, pivot, where in state_meshes(i):
            lo, hi = m.bounds()
            row["state_meshes"].append({"name": m.name, "slots": sorted(set(m.slots())), "triangles": int(len(m.tris)), "pivot": pivot,
                                        "placed_at": where, "bounds_cm": [lo.round(2).tolist(), hi.round(2).tolist()],
                                        "attributes": sorted(m.attrs), "collision": m.collision})
        row["first_person"] = first_person(i, step=20.0)
        out["stations"].append(row)
    lantern_parts = {}
    for stage in ("frame", "papered", "rimmed", "finished"):
        meshes = lantern(stage)
        lo = np.min([m.bounds()[0] for m in meshes], 0)
        hi = np.max([m.bounds()[1] for m in meshes], 0)
        lantern_parts[stage] = {"meshes": sorted({m.name for m in meshes}), "bounds_cm": [lo.round(2).tolist(), hi.round(2).tolist()]}
    out["lantern"]["stages"] = lantern_parts
    out["hanging_output"] = {"poles_y_cm": list(POLES_Y), "pole_z_cm": POLE_Z, "pole_x_cm": list(POLE_X),
                             "slots": [{"slot": p * 10 + i + 1, "hook_cm": np.round(hp, 2).tolist(), "yaw_deg": round(yaw, 2)}
                                       for p, i, hp, yaw in slots()],
                             "player_slot": PLAYER_SLOT, "lantern_pivot": "its hang point (the bail's ring) on the hook",
                             "clearance": hanging_clearance(),
                             "suggested_fill": "root's, from the completion mask: e.g. 24 of the craftspeople's lanterns from the start, "
                                               "the player's at PLAYER_SLOT once the oil step completes, and all 40 at the beat's end"}
    return out


# --- The candidate assets (create_b09_workshop_craft.py builds them; check_b09_candidates_fbx.py checks them) ---------
STATION_ASSETS = {0: "SM_B09_RibFormStation", 1: "SM_B09_PasteStation", 2: "SM_B09_OilStation", 3: "SM_B09_ShellStation"}


def candidates():
    """The candidate assets in export order: [(name, mesh, sockets {name: (point, x | None, z | None)}, frame,
    lantern_frame)].
    - Each station's static mesh, in the station frame. The paste bench's form and hoops are split out as
      SM_B09_PasteFrame (lantern frame), since its turntable turns them.
    - Every state mesh, in its own frame (state_meshes).
    - The drying poles and their 40 hooks, in world cm, placed at the world origin."""
    out = []
    for i, (sid, _) in enumerate(STATIONS):
        parts, sockets, proxies, work = station_parts(i)
        if i == 1:
            frame_names = {"SM_B09_Form"} | {f"SM_B09_Hoop{k}" for k in range(1, 7)}
            frame = [m.moved((0.0, 0.0, -LANTERN_Z[1])) for m in parts if m.name in frame_names]
            parts = [m for m in parts if m.name not in frame_names]
            out.append(("SM_B09_PasteFrame", merge("SM_B09_PasteFrame", frame), {},
                        "lantern frame (place at LanternCentre; turns about Z)", True))
        name = STATION_ASSETS[i]
        socks = dict(sockets)
        if i in (0, 1):
            socks["LanternCentre"] = (np.array([0.0, 0.0, LANTERN_Z[i]]), None, None)
        out.append((name, merge(name, parts), socks, f"station frame ({sid})", False))
        for m, pivot, where in state_meshes(i):
            out.append((m.name, m, {}, f"{pivot}; placed at {where}", pivot.startswith("the lantern's centre")))
    poles, hooks = hanging_parts()
    out.append(("SM_B09_DryingPoles", poles, {}, "world cm (place at the world origin)", False))
    out.append(("SM_B09_SlotHooks", hooks, {}, "world cm (place at the world origin)", False))
    return out


def reveal_uv(mesh, lantern_frame):
    """UV1 (`Reveal`) per vertex: the module's (height_frac, azimuth_frac) where the mesh has them; for a lantern-frame
    mesh, its height across the lantern and its azimuth; else zeros. The washi's paste and oil masks read U."""
    if "height_frac" in mesh.attrs:
        return np.stack([mesh.attrs["height_frac"], mesh.attrs["azimuth_frac"]], 1)
    if lantern_frame:
        v = mesh.verts
        h = np.clip((v[:, 2] + LANTERN_H / 2) / LANTERN_H, 0.0, 1.0)
        a = (np.arctan2(v[:, 1], v[:, 0]) / (2 * math.pi)) % 1.0
        return np.stack([h, a], 1)
    return np.zeros((len(mesh.verts), 2))


def box_uv(mesh):
    """UV0 per triangle corner, (n_tris, 3, 2) in the module's corner order, in metres: the mesh's own mapping from its
    construction (sweep: along the path; revolve: round the widest radius) where it has one. Otherwise a box
    projection, each triangle along its normal's dominant axis. The materials scale metres to their tile."""
    if mesh.tri_uv0 is not None:
        return np.asarray(mesh.tri_uv0, float)
    t = mesh.tris
    n = np.cross(mesh.verts[t[:, 1]] - mesh.verts[t[:, 0]], mesh.verts[t[:, 2]] - mesh.verts[t[:, 0]])
    keep = np.array([[1, 2], [0, 2], [0, 1]])[np.argmax(np.abs(n), 1)]
    p = mesh.verts[t] / 100.0
    return np.take_along_axis(p, np.repeat(keep[:, None, :], 3, 1), 2)


# --- Unreal's build ---------------------------------------------------------------------------------------------------
THRESH_POINTS_ARE_SAME = 2e-5                # cm (UnrealMathUtility.h): corners this close in every component are one
MIN_EDGE_CM = 1e-3                           # the host gate: 50 x that, so no candidate edge comes near it


def unreal_degenerate(mesh):
    """Per triangle: two corners within THRESH_POINTS_ARE_SAME in every component (FVector::Equals). Unreal's
    static-mesh build drops such triangles; s147 lost 128 pole slivers from each shell."""
    v = mesh.verts[mesh.tris]
    same = lambda a, b: (np.abs(a - b) <= THRESH_POINTS_ARE_SAME).all(1)  # noqa: E731
    return same(v[:, 0], v[:, 1]) | same(v[:, 1], v[:, 2]) | same(v[:, 2], v[:, 0])


def shortest_edge(mesh):
    v = mesh.verts[mesh.tris]
    return float(np.linalg.norm(v - np.roll(v, -1, axis=1), axis=2).min())


# --- Previews (presentation only) ---------------------------------------------------------------------------------------
COLOURS = {"M_B09_GaugeFace": (0.86, 0.82, 0.70), "M_B09_GaugeBand": (0.16, 0.62, 0.30), "M_B09_GaugeMarks": (0.08, 0.07, 0.07),
           "M_B09_GaugeNeedle": (0.80, 0.20, 0.10),
           "M_B09_TimberBench": (0.42, 0.30, 0.19), "M_B09_TimberForm": (0.70, 0.57, 0.40), "M_B09_Bamboo": (0.78, 0.70, 0.43),
           "M_B09_Washi": (0.93, 0.91, 0.85), "M_B09_RimLacquer": (0.08, 0.07, 0.07), "M_B09_Iron": (0.16, 0.16, 0.17),
           "M_B09_Ceramic": (0.32, 0.22, 0.16), "M_B09_Bristle": (0.62, 0.55, 0.42),
           "M_B09_ShellPaper": (0.72, 0.60, 0.45), "M_B09_ShellCore": (0.55, 0.45, 0.36), "M_B09_Twine": (0.52, 0.40, 0.25),
           "M_B09_FuseCord": (0.20, 0.18, 0.16), "M_B09_Cord": (0.50, 0.42, 0.30), "Proxy": (0.9, 0.2, 0.2)}


def render(meshes, eye, target, fov_deg, size=(1280, 720), light=(-0.4, 0.3, 0.86)):
    """A plain z-buffered, Lambert-shaded raster of the meshes (Unreal axes; +Y is drawn to the right as Unreal does)."""
    w, h = size
    f = np.asarray(target, float) - eye
    f /= np.linalg.norm(f)
    r = np.cross([0.0, 0.0, 1.0], f)            # Unreal's right (left-handed): Z x forward
    r /= np.linalg.norm(r)
    u = np.cross(f, r)
    th = math.tan(math.radians(fov_deg) / 2)
    img = np.full((h, w, 3), 0.18)
    z = np.full((h, w), np.inf)
    L = np.asarray(light, float) / np.linalg.norm(light)
    for m in meshes:
        v = m.verts - eye
        d = v @ f
        x = (v @ r) / np.maximum(d, 1e-3) / th
        y = (v @ u) / np.maximum(d, 1e-3) / th * (w / h)
        px = (x + 1) * 0.5 * w
        py = (1 - y) * 0.5 * h
        tri = m.tris
        nrm = np.cross(m.verts[tri[:, 1]] - m.verts[tri[:, 0]], m.verts[tri[:, 2]] - m.verts[tri[:, 0]])
        nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-12)
        shade = 0.35 + 0.65 * np.abs(nrm @ L)
        bases = np.array([COLOURS.get(sl, (0.6, 0.6, 0.6)) for sl in m.slots()])
        for t_, s_, base in zip(tri, shade, bases):
            if (d[t_] < 1.0).any():
                continue
            xs, ys = px[t_], py[t_]
            x0, x1 = int(max(0, math.floor(xs.min()))), int(min(w - 1, math.ceil(xs.max())))
            y0, y1 = int(max(0, math.floor(ys.min()))), int(min(h - 1, math.ceil(ys.max())))
            if x0 > x1 or y0 > y1:
                continue
            gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            (ax, ay), (bx, by), (cx, cy) = zip(xs, ys)
            den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
            if abs(den) < 1e-12:
                continue
            l0 = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / den
            l1 = ((cy - ay) * (gx - cx) + (ax - cx) * (gy - cy)) / den
            l2 = 1 - l0 - l1
            inside = (l0 >= 0) & (l1 >= 0) & (l2 >= 0)
            if not inside.any():
                continue
            depth = l0 * d[t_[0]] + l1 * d[t_[1]] + l2 * d[t_[2]]
            zs = z[y0:y1 + 1, x0:x1 + 1]
            nearer = inside & (depth < zs)
            zs[nearer] = depth[nearer]
            img[y0:y1 + 1, x0:x1 + 1][nearer] = base * s_
    return (np.clip(img, 0, 1) * 255).astype(np.uint8)


def previews(out):
    from PIL import Image, ImageDraw
    out = Path(out)
    if out.exists():
        raise SystemExit(f"{out} exists")
    out.mkdir(parents=True)
    files = {}
    for i, (sid, (x, y)) in enumerate(STATIONS):
        parts, sockets, proxies, work = station_parts(i)
        meshes = list(parts)
        lift = np.array([0.0, 0.0, LANTERN_Z.get(i, WORK_Z)])
        if i == 0:
            meshes += [hoop(k).moved(lift) for k in range(1, 4)] + [hoop(4, 0.75).moved(lift)]
        elif i == 1:
            meshes += [m.moved(lift) for m in lantern("frame")[:6]] + [gore(1).moved(lift), gore(2).moved(lift)]
            sheets = {m.name: m for m, _, _ in state_meshes(1)}
            meshes += [sheets[f"SM_B09_WashiSheet{j}"].moved(sockets[f"WashiSheet{j}"][0]) for j in (1, 2)]   # 4 - 2 left
        elif i == 2:
            hp = sockets["LanternHang"][0]
            meshes += [m.moved(hp - hang_point()) for m in lantern("finished")]
        else:
            origin, rot = weapon_rest()
            # A stand-in for SM_Weapon_07 (the existing asset, placed at WeaponRest): its culm, in previews only.
            culm = sweep("SM_Weapon_07_StandIn", [origin + rot @ [WEAPON7["x_range_cm"][0], 0, 0], origin + rot @ [WEAPON7["x_range_cm"][1], 0, 0]],
                         "M_B09_Bamboo", radius=WEAPON7["culm_cm"] / 2, segments=16)
            meshes.append(culm)
            for k in (1, 2):
                meshes.append(shell("wrapped").moved(sockets[f"ShellSeat{k}"][0]))
            meshes.append(shell("core").moved(sockets["ShellCore3"][0]))
        stand = np.array([WORK_STAND[0], WORK_STAND[1], 0.0])
        eye = stand + [EYE[0], EYE[1], CAPSULE_HALF + EYE[2]]
        if i == 0:
            meshes.append(needle_at(BEND_MS))                    # in the band, at the ideal release
        img = render(meshes, eye, work, WORLD_HFOV_DEG)
        p = out / f"b09_{sid}_hero_eye.png"
        Image.fromarray(img).save(p)
        files[p.name] = p
        if i == 0:
            img = render(meshes, eye, work, WORLD_HFOV_DEG, size=(1680, 720))
            p = out / f"b09_{sid}_hero_eye_21x9.png"
            Image.fromarray(img).save(p)
            files[p.name] = p
            for label, pos in (("front_left", (-150.0, -90.0, 0.0)), ("front_right", (-150.0, 90.0, 0.0))):
                e = np.array(pos) + [EYE[0], EYE[1], CAPSULE_HALF + EYE[2]]
                img = render(meshes, e, work, WORLD_HFOV_DEG)
                p = out / f"b09_{sid}_approach_{label}.png"
                Image.fromarray(img).save(p)
                files[p.name] = p
        img = render(meshes, np.array([-150.0, -170.0, 210.0]), work, 45.0)
        p = out / f"b09_{sid}_three_quarter.png"
        Image.fromarray(img).save(p)
        files[p.name] = p
    # The lantern's stages side by side, and the plan.
    stages = []
    for k, stage in enumerate(("frame", "papered", "rimmed", "finished")):
        stages += [m.moved([0.0, 40.0 * k - 60.0, 0.0]) for m in lantern(stage)]
    img = render(stages, np.array([-150.0, 0.0, 10.0]), np.array([0.0, 0.0, 0.0]), 50.0)
    p = out / "b09_lantern_stages.png"
    Image.fromarray(img).save(p)
    files[p.name] = p
    img = plan()
    p = out / "b09_plan.png"
    img.save(p)
    files[p.name] = p
    return files


def plan(scale=0.4):
    """Top view: the room, the yard's solids, the stations, their benches, reach and stands, and the 40 slots."""
    from PIL import Image, ImageDraw
    x0, x1, y0, y1 = 1450, 3700, -2500, 200
    w, h = int((x1 - x0) * scale), int((y1 - y0) * scale)
    im = Image.new("RGB", (w, h), (34, 32, 30))
    dr = ImageDraw.Draw(im)
    tx = lambda x: (x - x0) * scale  # noqa: E731
    ty = lambda y: (y1 - y) * scale  # noqa: E731
    for k, (c, size) in enumerate(SOLIDS):
        lo, hi = c - size / 2, c + size / 2
        col = (90, 75, 55) if k == 0 else (60, 58, 56) if k in FLOOR_SLABS else (150, 150, 150) if hi[2] < 400 else (110, 110, 125)
        if k == 9:
            continue                         # the ceiling
        dr.rectangle([tx(lo[0]), ty(hi[1]), tx(hi[0]), ty(lo[1])], outline=col, fill=col if k in FLOOR_SLABS else None)
    for p, i, hp, yaw in slots():
        dr.ellipse([tx(hp[0] - LANTERN_R), ty(hp[1] + LANTERN_R), tx(hp[0] + LANTERN_R), ty(hp[1] - LANTERN_R)],
                   outline=(240, 220, 160) if p * 10 + i + 1 != PLAYER_SLOT else (255, 120, 60))
    for i, (sid, (x, y)) in enumerate(STATIONS):
        parts, sockets, proxies, work = station_parts(i)
        dr.ellipse([tx(x - REACH_CM), ty(y + REACH_CM), tx(x + REACH_CM), ty(y - REACH_CM)], outline=(60, 120, 160))
        for lo, hi in proxies:
            dr.rectangle([tx(x + lo[0]), ty(y + hi[1]), tx(x + hi[0]), ty(y + lo[1])], outline=(220, 70, 60))
        sx, sy = x + WORK_STAND[0], y + WORK_STAND[1]
        dr.ellipse([tx(sx - CAPSULE_R), ty(sy + CAPSULE_R), tx(sx + CAPSULE_R), ty(sy - CAPSULE_R)], outline=(120, 220, 120))
        dr.text((tx(x) + 4, ty(y) - 12), sid.replace("st_b09_", ""), fill=(230, 230, 230))
    return im


def main():
    args = sys.argv[1:]
    if args[:1] == ["--spec"]:
        path = Path(args[1])
        path.write_text(json.dumps(spec(), indent=1, ensure_ascii=False) + "\n")
        print("B09_SPEC", path)
    elif args[:1] == ["--previews"]:
        files = previews(args[1])
        print("B09_PREVIEWS", json.dumps(sorted(files)))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
