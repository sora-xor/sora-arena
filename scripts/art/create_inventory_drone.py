"""Build the Inventory drone (目録): a floating disc with a cyan eye (story bible §7), to the measured envelope of
docs/art-direction/INVENTORY_DRONE_ENVELOPE.md.

Run:  blender -b --factory-startup --python scripts/art/create_inventory_drone.py [-- --no-render --res 1024]

It uses the runtime weapon library unchanged (scripts/art/create_runtime_weapon_lib.py): its alien materials, UV,
bake, LODs and FBX export. A drone is not a weapon, so DroneBuild replaces only:
- the spec and the output folder (Content/SourceArt/Characters/Enemies/InventoryDrone);
- the socket set (Eye, NetMuzzle);
- LOD0's FBX, with its sockets and UCX hulls, in UE 5.8's own axes and unit (LOD0_FBX);
- the renders;
- an amendment to the record.

**The body:** authored at its real size, actor scale 1.0, its pivot at its centre (the flight height). The axes are
+X forward (the eye), +Z up, +Y the drone's left (Unreal -Y).
- A lens-shaped hull 70 cm across. Its lower half is graphite and its upper half panel graphite, with a titanium rim
  band and a cyan ledger line under it.
- A cyan eye recessed in the front rim.
- A black-glass dorsal dome ringed by the ledger sigil: a closed ring of tally notches, never the SORA mon.
- A ventral net pod with its muzzle 45 deg down and forward.
- Three hover vents.

The eye, ledger line, vents and muzzle glow are flagged in Mask R, so Unreal can drive the net's cyan telegraph.

**The envelope check:** every vertex of every LOD lies within ENVELOPE_M of the centre (the body's design bound),
inside the proposed collision sphere. It is recorded in build_record.json "envelope", and the build fails otherwise.

**The hit hulls.** The movement sphere is mostly empty space, so precision shots resolve against three simple
convex hulls of the body: the disc, the dorsal dome and the net pod. They are exported in the LOD0 FBX as Unreal
custom collision: UCX_SM_Drone_Inventory_00, _01, _02.
- Each hull is the exact convex hull of low-poly proxies of its group's parts. The proxies are circumscribed, so they
  enclose and never cut in.
- The build proves that every visual vertex of its group lies inside it.
- Root owns the collision responses.
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("RW_RUNTIME_DIR", str(ROOT / "Content/SourceArt/Characters/Enemies"))

import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import create_runtime_weapon_lib as L  # noqa: E402

CYAN = (0.12, 0.85, 1.0)                        # the alien family's ledger cyan (create_runtime_weapon_alien.py)
ENVELOPE_M = 0.365                              # the body's design bound from its centre
COLLISION_RADIUS_M = 0.38                       # the proposed sphere (capsule radius = half-height), actor scale 1.0
LEDGER_HALL = {"ceiling_cm": 600, "flight_cm": 550, "shelf_top_cm": 450}     # SoraLedgerRules (root 65f4aaea)
SPEC = {"key": "InventoryDrone", "asset": "SM_Drone_Inventory", "ja": "目録", "en": "Inventory drone",
        "faction": "Stellar Credit House (credit_house)", "builder": "scripts/art/create_inventory_drone.py",
        "origin": "Centre", "texture_res": 2048}
SOCKETS = {"Eye", "NetMuzzle"}
# The hit hulls: Unreal's UCX index, and the parts (by name prefix) each one encloses.
HIT_GROUPS = {"00": ("Disc", ("Hull_", "Rim_", "Ledger_", "Eye_", "Sigil_", "Vent_")),
              "01": ("Dome", ("Dorsal_",)), "02": ("NetPod", ("Net_",))}
# LOD0's FBX (the only file with sockets) for UE 5.8. Root's import of fc0858a9 (0eb8c5e) read both sockets at
# scale 100 with +X reversed, positions right. The library's convention puts the axis turn (-Y forward) and the x100
# unit on the mesh node:
# - Interchange converts that file's axes, then turns each socket by the inverse conversion;
# - and it folds the node's scale into the socket.
# fbx_unreal_sockets.py cites the source lines. So LOD0 is written in Blender's own axes, which are Unreal's FBX
# import axes, with the unit baked into the vertices and socket translations. No node carries a rotation or a scale,
# and no importer converts anything. LOD1 and LOD2 have no sockets and keep the library's convention.
LOD0_FBX = dict(apply_unit_scale=True, apply_scale_options="FBX_SCALE_NONE", global_scale=1.0,
                axis_forward="Y", axis_up="Z", bake_space_transform=True)
MUZZLE = Matrix.Translation((0.040, 0.0, -0.115)) @ Matrix.Rotation(math.radians(45.0), 4, "Y")
VENT_DEG = (60.0, 180.0, 300.0)
HULL_GROWTH = 1.003

# The hull's profile, (z, radius) in metres from the bottom up: a lens 70 cm across, its rim at z 0.
HULL_LOWER = [(-0.060, 0.105), (-0.057, 0.150), (-0.052, 0.200), (-0.045, 0.255), (-0.035, 0.300), (-0.026, 0.328),
              (-0.018, 0.343), (-0.010, 0.349), (0.000, 0.350)]
HULL_UPPER = [(0.000, 0.350), (0.010, 0.349), (0.018, 0.343), (0.028, 0.322), (0.040, 0.280), (0.050, 0.225),
              (0.057, 0.170), (0.062, 0.110)]


def hull_radius(z):
    prof = HULL_LOWER + HULL_UPPER[1:]
    for (z0, r0), (z1, r1) in zip(prof, prof[1:]):
        if z0 <= z <= z1:
            return r0 + (r1 - r0) * (z - z0) / (z1 - z0)
    raise ValueError(z)


def revolve(name, profile, mat, sides=96, tip=None, caps=True, **kw):
    """A surface of revolution about Z from (z, r) sections, bottom up: the library's tube along +X, turned up."""
    obj = L.tube(name, [(z, r, r) for z, r in profile], mat, sides=sides, max_seg=0.0, chunk=0.0,
                 tip_end=(tip, 0.0, 0.0) if tip is not None else None, cap_start=caps, cap_end=caps, **kw)
    # A revolution's loft UV is one long strip round its circumference (6:1 on the hull), which packs into about a
    # tenth of the atlas (the first build: 494 px/m). The library's smart-project unwrap packs it properly.
    obj["rw_needs_unwrap"] = True
    return L.transform(obj, L.rot("Y", -90.0))


def band(name, z0, z1, r_in, r_out, mat, sides=96):
    """An open annular band (its inside hidden in the hull): flat faces at z0 and z1, an outer wall at r_out."""
    return revolve(name, [(z0, r_in), (z0, r_out), (z1, r_out), (z1, r_in)], mat, sides=sides, caps=False,
                   sharp_angle=30.0)


class Kit:
    def __init__(self):
        # The library cuts its machining grooves at constant z, 1.1 mm apart: lines along a weapon, but contour rings
        # 4-11 mm apart on this gently sloped lens. At about 1.2 mm per texel they also alias (the first passing build's
        # top view). So the drone keeps the hex engraving and grain, with almost no grooves.
        self.graphite = L.mat_graphite("M_Drone_Graphite", engrave=0.15, ledger=None)
        self.panel = L.mat_graphite("M_Drone_PanelGraphite", color=(0.045, 0.047, 0.052), rough=0.36, engrave=0.25,
                                    ledger=None)
        self.ti = L.mat_titanium("M_Drone_Titanium")
        self.glass = L.mat_black_glass("M_Drone_BlackGlass")
        self.eye = L.mat_black_glass("M_Drone_EyeLens", emissive_rgb=CYAN)
        self.glow = L.mat_emissive("M_Drone_Ledger", (0.02, 0.05, 0.06), CYAN, 8.0)


def build_drone(b):
    k = Kit()
    b.add(revolve("Hull_Lower", HULL_LOWER, k.graphite))
    b.add(revolve("Hull_Upper", HULL_UPPER, k.panel))
    b.add(band("Rim_Band", -0.007, 0.007, 0.346, 0.356, k.ti))
    z0, z1 = -0.024, -0.020                                   # the ledger line, just proud of the lower hull
    b.add(revolve("Ledger_Line", [(z0, hull_radius(z0) - 0.002), (z0, hull_radius(z0) + 0.0012),
                                  (z1, hull_radius(z1) + 0.0012), (z1, hull_radius(z1) - 0.002)], k.glow, caps=False))
    # The eye: a brow-like housing through the front rim, a titanium bezel and the cyan lens, all inside the rim's reach.
    b.add(L.tube("Eye_Housing", [(0.300, 0.030, 0.030), (0.330, 0.034, 0.034), (0.348, 0.033, 0.033),
                                 (0.352, 0.029, 0.029)], k.graphite, sides=48, max_seg=0.0, chunk=0.0, sharp_angle=35.0))
    b.add(L.tube("Eye_Bezel", [(0.350, 0.0285, 0.0285), (0.3545, 0.0285, 0.0285), (0.3550, 0.0255, 0.0255)], k.ti,
                 sides=48, max_seg=0.0, chunk=0.0, cap_start=False, sharp_angle=35.0))
    b.add(L.tube("Eye_Lens", [(0.3525, 0.0250, 0.0250), (0.3570, 0.0215, 0.0215), (0.3600, 0.0130, 0.0130)], k.eye,
                 sides=48, max_seg=0.0, chunk=0.0, tip_end=(0.3612, 0.0, 0.0)))
    # A dark glass pupil over the cyan iris, so it reads as an eye, not a lamp.
    b.add(L.tube("Eye_Pupil", [(0.3598, 0.0105, 0.0105), (0.3610, 0.0085, 0.0085), (0.3618, 0.0045, 0.0045)], k.glass,
                 sides=32, max_seg=0.0, chunk=0.0, tip_end=(0.3622, 0.0, 0.0)))
    # The dorsal sensor dome and the ledger sigil round it: a closed ring of twelve tally notches.
    b.add(revolve("Dorsal_Dome", [(0.058, 0.100), (0.070, 0.090), (0.082, 0.065), (0.090, 0.035)], k.glass, tip=0.0935))
    z_sig = 0.057 + (0.170 - 0.125) / (0.170 - 0.110) * 0.005
    for j in range(12):
        a = math.tau * j / 12
        notch = L.box(f"Sigil_Notch_{j}", (0.125, 0.0, z_sig + 0.0015), (0.020, 0.0045, 0.006), k.ti, 0.0006)
        b.add(L.transform(notch, Matrix.Rotation(a, 4, "Z")), lod_drop=2)
    b.add(band("Sigil_Ring", z_sig - 0.002, z_sig + 0.0022, 0.140, 0.146, k.glow), lod_drop=2)
    # The ventral net pod; its top is 5 mm inside the hull, so no face is coplanar with the hull's bottom cap.
    b.add(revolve("Net_Pod", [(-0.140, 0.060), (-0.132, 0.075), (-0.118, 0.085), (-0.075, 0.090), (-0.055, 0.088)],
                  k.graphite))
    muzzle = MUZZLE
    b.add(L.transform(L.tube("Net_Muzzle", [(0.0, 0.032, 0.032), (0.045, 0.036, 0.036), (0.052, 0.034, 0.034)], k.ti,
                             sides=40, max_seg=0.0, chunk=0.0, cap_end=False, sharp_angle=35.0), muzzle))
    b.add(L.transform(L.tube("Net_Muzzle_Glow", [(0.044, 0.027, 0.027), (0.048, 0.027, 0.027)], k.glow, sides=40,
                             max_seg=0.0, chunk=0.0), muzzle))
    mouth = muzzle @ Vector((0.052, 0.0, 0.0))
    # Three hover vents under the hull, clear of the eye's side.
    for j, deg in enumerate(VENT_DEG):
        a = math.radians(deg)
        at = Matrix.Translation((0.25 * math.cos(a), 0.25 * math.sin(a), 0.0))
        b.add(L.transform(revolve(f"Vent_{j}", [(-0.058, 0.026), (-0.050, 0.030), (-0.042, 0.030)], k.ti, sides=32), at),
              lod_drop=2)
        b.add(L.transform(revolve(f"Vent_Glow_{j}", [(-0.0570, 0.021), (-0.0560, 0.021)], k.glow, sides=32), at),
              lod_drop=2)
    b.socket("Eye", (0.3622, 0.0, 0.0))
    b.socket("NetMuzzle", tuple(mouth), x=(math.cos(math.radians(45)), 0.0, -math.sin(math.radians(45))),
             z=(math.sin(math.radians(45)), 0.0, math.cos(math.radians(45))))
    b.notes.update({"diameter_m": 0.712, "height_m": round(0.0935 + 0.140, 4), "eye": "cyan iris (Mask R) round a dark glass pupil",
                    "emissive": "Mask R: eye lens, ledger line, sigil ring, vent glows, net muzzle glow",
                    "glow": "alien family: cyan (story bible 15.1)"})


def ring_points(profile, sides, matrix=Matrix.Identity(4), axis="Z"):
    """A circumscribed polygon's corners for each (axial, radius) section: a polygon of `sides` whose edges touch the
    circle, so it encloses the round part. axis Z: (z, r) about Z; axis X: (x, r) about X, as the library's tubes."""
    k = 1.0 / math.cos(math.pi / sides)
    out = []
    for a, r in profile:
        for j in range(sides):
            t = math.tau * (j + 0.5) / sides
            c, s = r * k * math.cos(t), r * k * math.sin(t)
            out.append(matrix @ (Vector((c, s, a)) if axis == "Z" else Vector((a, c, s))))
    return out


def hull_proxies():
    """Low-poly points whose convex hull encloses each group's parts."""
    prof = HULL_LOWER + HULL_UPPER[1:]
    z0, z1 = -0.024, -0.020
    disc = ring_points(prof, 16) + ring_points([(-0.007, 0.356), (0.007, 0.356)], 16)
    disc += ring_points([(z0, hull_radius(z0) + 0.0012), (z1, hull_radius(z1) + 0.0012)], 16)
    disc += ring_points([(0.300, 0.034), (0.330, 0.034), (0.352, 0.034)], 8, axis="X")
    # The lens dome bulges past the cone from the housing to its tip (the second build: 108 vertices 2.2 mm outside).
    disc += ring_points([(0.3525, 0.0250), (0.3570, 0.0215), (0.3600, 0.0130)], 8, axis="X")
    disc += ring_points([(0.3500, 0.0285), (0.3545, 0.0285), (0.3550, 0.0255)], 8, axis="X")    # the bezel
    disc += ring_points([(0.3598, 0.0105), (0.3610, 0.0085), (0.3618, 0.0045)], 8, axis="X")      # the pupil
    disc += [Vector((0.3622, 0.0, 0.0))]
    z_sig = 0.057 + (0.170 - 0.125) / (0.170 - 0.110) * 0.005
    disc += ring_points([(z_sig - 0.002, 0.146), (z_sig + 0.0022, 0.146)], 16)
    for j in range(12):
        rz = Matrix.Rotation(math.tau * j / 12, 4, "Z")
        disc += [rz @ Vector((0.125 + sx * 0.0103, sy * 0.0026, z_sig + 0.0015 + sz * 0.0031))
                 for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
    for deg in VENT_DEG:
        a = math.radians(deg)
        at = Matrix.Translation((0.25 * math.cos(a), 0.25 * math.sin(a), 0.0))
        disc += ring_points([(-0.058, 0.030), (-0.042, 0.030)], 8, at)
    dome = ring_points([(0.058, 0.100), (0.070, 0.090), (0.082, 0.065), (0.090, 0.035)], 16) + [Vector((0.0, 0.0, 0.0935))]
    pod = ring_points([(-0.140, 0.060), (-0.132, 0.075), (-0.118, 0.085), (-0.075, 0.090), (-0.055, 0.090)], 16)
    pod += ring_points([(0.0, 0.036), (0.052, 0.036)], 12, MUZZLE, axis="X")
    # Vertices on a circumscribed edge's tangent sit exactly on the hull, where Blender's hull, which merges
    # near-coplanar points, can pass microns inside (the fourth build: 3-10 um). So each hull is grown 0.3 % about its
    # proxies' centroid: under a millimetre at the rim.
    out = {}
    for idx, pts in {"00": disc, "01": dome, "02": pod}.items():
        c = sum(pts, Vector()) / len(pts)
        out[idx] = [c + (q - c) * HULL_GROWTH for q in pts]
    return out


def convex_hull_mesh(name, points):
    bm = bmesh.new()
    for p in points:
        bm.verts.new(p)
    res = bmesh.ops.convex_hull(bm, input=list(bm.verts), use_existing_faces=False)
    # A vertex can be listed both interior and unused; delete each once.
    drop = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
    bmesh.ops.delete(bm, geom=drop, context="VERTS")
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.uv_layers.new(name="UV0")
    return bpy.data.objects.new(name, me)


def hull_planes(obj):
    """Each face's outward unit normal and offset, in the object's frame."""
    me = obj.data
    v = np.array([list(x.co) for x in me.vertices])
    centre = v.mean(0)
    n, d = [], []
    for poly in me.polygons:
        q = v[list(poly.vertices)]
        nn = np.cross(q[1] - q[0], q[2] - q[0])
        nn /= np.linalg.norm(nn)
        if nn @ (q[0] - centre) < 0:
            nn = -nn
        n.append(nn)
        d.append(nn @ q[0])
    return np.array(n), np.array(d), v


class DroneBuild(L.Build):
    """L.Build for a non-weapon asset: the drone's spec, folder, sockets, renders and record."""

    def __init__(self, opts):                                 # as L.Build.__init__, without the weapon specs
        self.id = "drone"
        self.spec = SPEC
        self.opts = opts
        self.key = SPEC["key"]
        self.dir = L.RUNTIME / self.key
        self.dir.mkdir(parents=True, exist_ok=True)
        L.RENDERS.mkdir(parents=True, exist_ok=True)
        self.res = opts.get("res") or SPEC["texture_res"]
        self.groups = {"main": dict(asset=SPEC["asset"], offset=Vector(), origin=Vector(), parts=[])}
        self.sockets = {"main": []}
        self.notes = {}
        self.measure = {}
        self.t0 = time.time()
        self.scene = L.reset_scene()
        L.USED_SOURCES.clear()
        L.REG.clear()

    def finalize(self):                                       # as L.Build.finalize, with the drone's checks
        names = {s[0] for s in self.sockets["main"]}
        if names != SOCKETS:
            raise RuntimeError(f"{self.key}: sockets {sorted(names)}, not {sorted(SOCKETS)}")
        # Each hit group's visual vertices, before the parts are joined for the bake.
        self.hit_points, self.hit_owner = {}, {}
        for idx, (_label, prefixes) in HIT_GROUPS.items():
            parts = [o for o in self.groups["main"]["parts"] if o.name.startswith(prefixes)]
            if not parts:
                raise RuntimeError(f"hit group {idx} has no parts")
            self.hit_points[idx] = np.array([list(o.matrix_world @ v.co) for o in parts for v in o.data.vertices])
            self.hit_owner[idx] = np.array([o.name for o in parts for _v in o.data.vertices])
        unassigned = [o.name for o in self.groups["main"]["parts"]
                      if not o.name.startswith(tuple(p for _l, ps in HIT_GROUPS.values() for p in ps))]
        if unassigned:
            raise RuntimeError(f"parts in no hit group: {unassigned}")
        self.unwrap_parts()
        bake_obj = self.build_bake_mesh()
        self.pack_uv0(bake_obj)
        if not self.opts.get("no_bake"):
            self.bake(bake_obj)
            self.final_material(bake_obj)
        exports = self.split_and_export(bake_obj)
        self.envelope = envelope_check(exports)
        self.hit_hulls = self.export_hit_hulls(exports)
        self.save_blend()
        if not self.opts.get("no_render"):
            self.render(exports)
        self.write_record(exports)
        self.log("done", f"{time.time() - self.t0:.1f}s")

    def export_hit_hulls(self, exports):
        """The UCX hulls: built, proved to enclose their groups, and exported with LOD0 and its sockets."""
        lod0, path = exports["main"]["lods"][0], exports["main"]["files"][0]
        coll = L.collection("RW_Export")
        hulls, rows = [], {}
        for idx, pts in hull_proxies().items():
            obj = convex_hull_mesh(f"UCX_{SPEC['asset']}_{idx}", pts)
            coll.objects.link(obj)
            n, d, v = hull_planes(obj)
            inside = (self.hit_points[idx] @ n.T - d).max(1)
            if inside.max() > 1e-6:
                out = inside > 1e-6
                worst_by_part = {}
                for name, dist, pt in zip(self.hit_owner[idx][out], inside[out], self.hit_points[idx][out]):
                    if dist > worst_by_part.get(name, (0.0, None))[0]:
                        worst_by_part[name] = (round(float(dist), 6), [round(float(c), 4) for c in pt])
                raise RuntimeError(f"{obj.name} leaves {int(out.sum())} vertices outside, by {inside.max():.5f} m: "
                                   f"{worst_by_part}")
            hulls.append(obj)
            rows[obj.name] = {"encloses": HIT_GROUPS[idx][0], "parts": list(HIT_GROUPS[idx][1]),
                              "vertices": len(v), "triangles": len(obj.data.polygons),
                              "bounds_min_m": [round(float(c), 4) for c in v.min(0)],
                              "bounds_max_m": [round(float(c), 4) for c in v.max(0)],
                              "visual_vertices_enclosed": int(len(inside)), "deepest_outside_m": round(float(inside.max()), 7)}
        export_lod0(path, lod0, exports["main"]["empties"], hulls)
        self.log("exported", L.rel(path), "with", len(hulls), "UCX hulls")
        for h in hulls:
            h.hide_render = True
        zs = np.concatenate([np.array([list(x.co) for x in h.data.vertices])[:, 2] for h in hulls])
        sphere = 4.0 / 3.0 * math.pi * COLLISION_RADIUS_M ** 3
        vol = sum(hull_volume(h) for h in hulls)
        return {"convention": "Unreal FBX custom collision: UCX_<mesh>_<nn>, convex, in the LOD0 FBX", "hulls": rows,
                "vertical_span_m": [round(float(zs.min()), 4), round(float(zs.max()), 4)],
                "volume_m3": round(vol, 5), "movement_sphere_volume_m3": round(sphere, 5),
                "share_of_movement_sphere": round(vol / sphere, 4),
                "use": "precision hits (arrows, rifle shots) against these hulls, not the 38 cm movement sphere; root owns responses"}

    def render(self, exports):
        render_drone(self, exports)

    def write_record(self, exports):
        super().write_record(exports)
        path = self.dir / "build_record.json"
        rec = json.loads(path.read_text(encoding="utf-8"))
        rec["axes"] = "+X forward (the eye), +Z up, +Y the drone's left (Unreal: -Y); origin at the body's centre"
        rec["contract"] = "docs/art-direction/INVENTORY_DRONE_ENVELOPE.md"
        rec["envelope"] = self.envelope
        rec["hit_hulls"] = self.hit_hulls
        rec["lod0_fbx"] = lod0_fbx_record()
        rec["socket_axes"] = socket_axes(exports["main"]["empties"])
        top = LEDGER_HALL["flight_cm"] + COLLISION_RADIUS_M * 100.0
        bottom = LEDGER_HALL["flight_cm"] - COLLISION_RADIUS_M * 100.0
        rec["collision_proposal"] = {
            "shape": "sphere: capsule radius = half-height", "radius_cm": COLLISION_RADIUS_M * 100.0,
            "actor_scale": 1.0, "enemies_json_scale_permille": 1000,
            "ledger_hall": {**LEDGER_HALL, "top_cm": round(top, 2), "ceiling_clearance_cm": round(LEDGER_HALL["ceiling_cm"] - top, 2),
                            "bottom_cm": round(bottom, 2), "above_shelf_tops_cm": round(bottom - LEDGER_HALL["shelf_top_cm"], 2)},
            "today": {"radius_cm": 20.4, "half_height_cm": 52.8, "from": "34/88 humanoid capsule at scale_permille 600"},
            "for_root": "the hit volume (76 cm tall against a 23 cm body) and every other drone route's clearance"}
        path.write_text(json.dumps(rec, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def export_lod0(path, lod0, empties, hulls):
    """LOD0's FBX: the body, its SOCKET_ empties and the UCX hulls, in the LOD0_FBX convention."""
    L.deselect_all()
    for obj in (lod0, *empties, *hulls):
        obj.select_set(True)
    bpy.context.view_layer.objects.active = lod0
    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, object_types={"MESH", "EMPTY"}, **LOD0_FBX,
                             mesh_smooth_type="FACE", use_tspace=True, use_triangles=True,
                             use_mesh_modifiers=True, add_leaf_bones=False, bake_anim=False,
                             path_mode="STRIP", embed_textures=False, use_custom_props=False)


def lod0_fbx_record():
    return {"export": dict(LOD0_FBX),
            "axes": "Blender's own (up Z, forward Y), which are UE 5.8's FBX import axes (Z up, -Y front, "
                    "right-handed). The file declares them, so no importer converts it",
            "unit": "centimetres, baked into the vertices and the socket translations. No node carries a rotation "
                    "or a scale, so each socket imports at scale 1 on its own axes",
            "gate": "scripts/art/validate_inventory_drone.py, through scripts/art/fbx_unreal_sockets.py "
                    "(Interchange's socket rule, calibrated on root's import of fc0858a9)",
            "lod1_lod2": "the library's convention (-Y forward, x100 on the node), unchanged. They carry no "
                         "sockets, and Unreal bakes them to the same vertices"}


def socket_axes(empties):
    """Each socket's unit X (forward) and Z axes, in the drone's Blender frame."""
    out = {}
    for e in empties:
        m = e.matrix_basis.to_3x3().normalized()
        out[e.name[len("SOCKET_"):]] = {"x": [round(c, 6) for c in m.col[0]], "z": [round(c, 6) for c in m.col[2]]}
    return out


def hull_volume(obj):
    """A closed triangle mesh's volume (divergence theorem)."""
    me = obj.data
    v = np.array([list(x.co) for x in me.vertices])
    c = v.mean(0)
    total = 0.0
    for poly in me.polygons:
        a, b, cc = (v[i] - c for i in poly.vertices[:3])
        total += abs(np.dot(a, np.cross(b, cc))) / 6.0
    return total


def envelope_check(exports):
    """Every vertex of every LOD inside ENVELOPE_M of the centre (and so inside the collision sphere)."""
    rows = []
    for lod, obj in enumerate(exports["main"]["lods"]):
        mw = obj.matrix_world
        pts = [mw @ v.co for v in obj.data.vertices]
        far = max(pts, key=lambda p: p.length)
        rows.append({"lod": lod, "vertices": len(pts), "triangles": len(obj.data.polygons),
                     "max_from_centre_m": round(far.length, 5), "farthest_point_m": [round(c, 4) for c in far],
                     "bounds_min_m": [round(min(p[i] for p in pts), 4) for i in range(3)],
                     "bounds_max_m": [round(max(p[i] for p in pts), 4) for i in range(3)]})
    worst = max(r["max_from_centre_m"] for r in rows)
    if worst > ENVELOPE_M + 1e-5 or worst >= COLLISION_RADIUS_M:
        raise RuntimeError(f"the drone reaches {worst:.4f} m from its centre, beyond {ENVELOPE_M} m")
    return {"design_bound_m": ENVELOPE_M, "collision_radius_m": COLLISION_RADIUS_M, "max_from_centre_m": worst,
            "margin_to_collision_cm": round((COLLISION_RADIUS_M - worst) * 100.0, 2), "lods": rows}


def render_drone(build, exports):
    """Review originals in the library's neutral studio:
    - front, side, top and three-quarter views;
    - the envelope: the body in its 38 cm sphere, today's 20.4/52.8 capsule, and the ledger hall's ceiling and shelf
      tops;
    - a lineup beside the hero (SK_NyaagyuSamurai.fbx at its bind pose)."""
    scene = build.scene
    coll = L.collection("Drone_Render")
    body = exports["main"]["lods"][0]
    disp = body.copy()
    disp.data = body.data
    coll.objects.link(disp)
    disp.hide_render = False
    for o in [o for ex in exports.values() for o in ex["lods"]]:
        o.hide_render = True
    scene.render.engine = "CYCLES"
    scene.cycles.samples = build.opts.get("samples", 112)
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = 1600, 1000
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.exposure = L.NEUTRAL_EXPOSURE_EV
    scene.world = L._world_neutral(scene)
    cam_data = bpy.data.cameras.new("Drone_Cam")
    cam = bpy.data.objects.new("Drone_Cam", cam_data)
    coll.objects.link(cam)
    scene.camera = cam
    key = bpy.data.objects.new("Drone_Key", bpy.data.lights.new("Drone_Key", "AREA"))
    key.data.energy, key.data.size = 70.0, 0.6               # small and dim, so near-black graphite reads near-black
    coll.objects.link(key)
    fill = bpy.data.objects.new("Drone_Fill", bpy.data.lights.new("Drone_Fill", "AREA"))
    fill.data.energy, fill.data.size = 20.0, 2.0
    coll.objects.link(fill)
    files = []

    def shot(name, direction, ortho=None, target=(0.0, 0.0, 0.0), lens=85.0, dist=2.6):
        d = Vector(direction).normalized()
        cam.location = Vector(target) + d * dist
        L._look_at(cam, target)
        cam_data.type = "ORTHO" if ortho else "PERSP"
        if ortho:
            cam_data.ortho_scale = ortho
        cam_data.lens = lens
        key.location = Vector(target) + (d + Vector((0.0, 0.6, 1.2))).normalized() * 2.5
        L._look_at(key, target)
        fill.location = Vector(target) + (d + Vector((0.0, -1.2, 0.2))).normalized() * 2.2
        L._look_at(fill, target)
        path = L.RENDERS / f"{SPEC['asset']}_{name}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        files.append(path)
        build.log("render", L.rel(path))

    shot("Front", (1.0, 0.0, 0.18))
    shot("Side", (0.0, -1.0, 0.0), ortho=0.95)
    shot("Top", (0.0, 0.0, 1.0), ortho=1.3)
    shot("ThreeQuarter", (0.8, -0.6, 0.45))
    # The envelope: the 38 cm sphere as wire, today's capsule as wire, the ceiling 50 cm up, the shelf tops 1 m down.
    wire = bpy.data.materials.new("Drone_Wire_Green")
    wire.node_tree.nodes["Principled BSDF"].inputs["Emission Color"].default_value = (0.05, 0.8, 0.3, 1.0)
    wire.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 3.0
    red = bpy.data.materials.new("Drone_Wire_Red")
    red.node_tree.nodes["Principled BSDF"].inputs["Emission Color"].default_value = (0.9, 0.08, 0.05, 1.0)
    red.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 3.0
    bpy.ops.mesh.primitive_uv_sphere_add(radius=COLLISION_RADIUS_M, segments=48, ring_count=24, location=(0, 0, 0))
    sphere = bpy.context.object
    sphere.data.materials.append(wire)
    mod = sphere.modifiers.new("wire", "WIREFRAME")
    mod.thickness = 0.002
    bpy.ops.mesh.primitive_cylinder_add(radius=0.204, depth=2 * (0.528 - 0.204), location=(-0.55, 0, 0))
    old = bpy.context.object
    for z in (0.528 - 0.204, -(0.528 - 0.204)):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.204, segments=32, ring_count=16, location=(-0.55, 0, z))
        cap = bpy.context.object
        cap.data.materials.append(red)
        m2 = cap.modifiers.new("wire", "WIREFRAME")
        m2.thickness = 0.002
        L.link_to(cap, coll)
    old.data.materials.append(red)
    m3 = old.modifiers.new("wire", "WIREFRAME")
    m3.thickness = 0.002
    slabs = []
    for name, z in (("Ceiling", (LEDGER_HALL["ceiling_cm"] - LEDGER_HALL["flight_cm"]) / 100.0),
                    ("ShelfTop", (LEDGER_HALL["shelf_top_cm"] - LEDGER_HALL["flight_cm"]) / 100.0)):
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, 0.3, z + (0.01 if name == "Ceiling" else -0.01)))
        slab = bpy.context.object
        slab.scale = (2.6, 0.02, 0.02)
        slabs.append(slab)
    for o in (sphere, old, *slabs):
        L.link_to(o, coll)
    shot("Envelope", (0.0, -1.0, 0.0), ortho=2.9, target=(-0.25, 0.0, -0.25), dist=4.0)   # 1.8 m tall: ceiling to shelves
    for o in (sphere, old, *slabs):
        o.hide_render = True
    for o in [o for o in coll.objects if o.name.startswith("Sphere")]:
        o.hide_render = True
    # The lineup: beside the hero at the hero's eye height, for scale.
    before = set(bpy.data.objects)
    hero = ROOT / "Content/SourceArt/SK_NyaagyuSamurai.fbx"
    bpy.ops.import_scene.fbx(filepath=str(hero))
    L.USED_SOURCES.add(L.rel(hero))
    for o in set(bpy.data.objects) - before:                # beside the drone across the frame, not behind it
        o.animation_data_clear()                             # the FBX's baked take would hold the rig at the origin
        if o.parent is None:
            o.location.y += 0.95
    disp.location = (0.0, 0.0, 1.60)
    shot("Lineup", (1.0, 0.0, 0.05), ortho=3.6, target=(0.0, 0.5, 1.1), dist=6.0)
    build.render_files = files


if __name__ == "__main__":
    opts = L.parse_args()
    b = DroneBuild(opts)
    build_drone(b)
    b.finalize()
    print("INVENTORY_DRONE_BUILT", json.dumps({"max_from_centre_m": b.envelope["max_from_centre_m"],
                                               "lods": [(r["lod"], r["triangles"]) for r in b.envelope["lods"]],
                                               "hulls": {k: (v["vertices"], v["deepest_outside_m"]) for k, v in b.hit_hulls["hulls"].items()},
                                               "hull_share_of_sphere": b.hit_hulls["share_of_movement_sphere"]}))
