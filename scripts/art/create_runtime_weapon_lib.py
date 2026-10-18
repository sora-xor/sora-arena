"""Shared Blender 5.2 toolkit for the runtime weapon meshes (SM_Weapon_*).

Imported by the ``create_runtime_weapon_<family>.py`` builders; it is not run
on its own. It provides

* measured procedural geometry: lofts along curved spines, lathed/oval tubes,
  swept ribbons and cords, bevelled outline extrusions and the pinned SORA mon;
* two UV layers per mesh: ``UV0`` (a unique, non-overlapping atlas that the
  PBR maps are baked into; long islands are split before packing) and
  ``UVMetric`` (continuous metre-scale coordinates used while authoring);
* authoring materials built from CC0 scans in ``Local/ThirdPartyRaw/cc0`` and
  the committed Poly Haven palette, plus original procedural masks (hamon,
  lacquer wear, nie, cavity dirt);
* the bake (BaseColor, DirectX normal, ORM, Mask), LOD1/LOD2 decimation,
  ``SOCKET_`` empties, FBX export, fixed-camera renders at 1 m under a
  neutral studio and the Estate's overcast sky, and a JSON build record.

Everything is deterministic: no random seeds depend on time and all noise is
positional. Units are metres; see create_runtime_weapon_specs.py for axes.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import create_runtime_weapon_specs as SPECS  # noqa: E402

ROOT = HERE.parents[1]
# RW_RUNTIME_DIR redirects every output (for preview builds outside the repo).
RUNTIME = Path(os.environ.get("RW_RUNTIME_DIR", str(ROOT / "Content/SourceArt/Weapons/Runtime")))
RENDERS = RUNTIME / "Renders"
CC0 = ROOT / "Local/ThirdPartyRaw/cc0"
PH_COMMITTED = ROOT / "Content/SourceArt/Environment/PolyHaven"
LOGO = ROOT / "Content/SourceArt/UI/sora_logo_NOtext2.svg"
LOGO_SHA256 = "d66413a71b70e25dcb8b2f118dcfe846a6446ed1db3de53ce88fc70c16ac0910"
CACHE = ROOT / "Saved/RuntimeWeaponBuild"
ESTATE_HDRI = PH_COMMITTED / "kloofendal_overcast_puresky/kloofendal_overcast_puresky_4k.hdr"

# Every third-party file an authoring material or render reads is recorded
# here and written to the lane's sources_manifest.json draft.
USED_SOURCES: set[str] = set()


def rel(path: Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(ROOT)).replace(os.sep, "/")
    except ValueError:
        return str(Path(path).resolve())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    opts = {"only": None, "no_bake": False, "no_render": False, "res": None, "samples": 112}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--only":
            opts["only"] = [int(x) for x in argv[i + 1].split(",")]
            i += 1
        elif a == "--no-bake":
            opts["no_bake"] = True
        elif a == "--no-render":
            opts["no_render"] = True
        elif a == "--res":
            opts["res"] = int(argv[i + 1])
            i += 1
        elif a == "--samples":
            opts["samples"] = int(argv[i + 1])
            i += 1
        i += 1
    return opts


# ---------------------------------------------------------------------------
# Scene
# ---------------------------------------------------------------------------

def reset_scene():
    bpy.context.preferences.filepaths.save_version = 0
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for coll in list(bpy.data.collections):
        bpy.data.collections.remove(coll)
    for block in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.images,
                  bpy.data.lights, bpy.data.cameras, bpy.data.node_groups, bpy.data.worlds):
        for item in list(block):
            block.remove(item)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    try:
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for dev in prefs.devices:
            dev.use = dev.type == "METAL"
        scene.cycles.device = "GPU"
    except Exception:  # pragma: no cover - CPU fallback
        scene.cycles.device = "CPU"
    world = bpy.data.worlds.new("RW_World")
    scene.world = world
    return scene


def collection(name, parent=None):
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(coll)
    return coll


def deselect_all():
    bpy.context.view_layer.update()
    for o in bpy.context.view_layer.objects:
        if o is not None:
            o.select_set(False)


def link_to(obj, coll):
    for c in tuple(obj.users_collection):
        c.objects.unlink(obj)
    coll.objects.link(obj)
    return obj


# ---------------------------------------------------------------------------
# Mesh construction
# ---------------------------------------------------------------------------

SOURCE_COLL = "RW_Source"


def _face_uv_flat(face_uvs):
    flat = []
    for corners in face_uvs:
        for u, v in corners:
            flat.extend((u, v))
    return flat


def box_uv(mesh, layer_name, scale=1.0):
    """Dominant-axis planar projection in metres (continuous per axis)."""
    layer = mesh.uv_layers[layer_name]
    co = np.empty(len(mesh.vertices) * 3)
    mesh.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    loops_v = np.empty(len(mesh.loops), dtype=np.int64)
    mesh.loops.foreach_get("vertex_index", loops_v)
    normals = np.empty(len(mesh.polygons) * 3)
    mesh.polygons.foreach_get("normal", normals)
    normals = np.abs(normals.reshape(-1, 3))
    loop_start = np.empty(len(mesh.polygons), dtype=np.int64)
    loop_total = np.empty(len(mesh.polygons), dtype=np.int64)
    mesh.polygons.foreach_get("loop_start", loop_start)
    mesh.polygons.foreach_get("loop_total", loop_total)
    axis = np.argmax(normals, axis=1)
    poly_of_loop = np.repeat(np.arange(len(mesh.polygons)), loop_total)
    a = axis[poly_of_loop]
    p = co[loops_v]
    u = np.where(a == 0, p[:, 1], p[:, 0])
    v = np.where(a == 2, p[:, 1], p[:, 2])
    uv = np.stack([u, v], axis=1) * scale
    layer.data.foreach_set("uv", uv.ravel())


def ensure_uv_layers(mesh):
    for name in ("UV0", "UVMetric"):
        if name not in mesh.uv_layers:
            mesh.uv_layers.new(name=name)
    # UV0 must be the first layer (FBX channel 0 in Unreal).
    names = [l.name for l in mesh.uv_layers]
    if names[0] != "UV0":
        raise RuntimeError(f"{mesh.name}: UV0 is not the first UV layer ({names})")


def make_obj(name, verts, faces, mat=None, uv0=None, uvm=None, smooth=True, sharp_angle=35.0,
             sharp_pairs=None, point_attrs=None, face_attrs=None, recalc=True):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    for n in [l.name for l in mesh.uv_layers]:
        mesh.uv_layers.remove(mesh.uv_layers[n])
    mesh.uv_layers.new(name="UV0")
    mesh.uv_layers.new(name="UVMetric")
    if uvm is not None:
        mesh.uv_layers["UVMetric"].data.foreach_set("uv", _face_uv_flat(uvm))
    else:
        mesh.update()
        box_uv(mesh, "UVMetric")
    obj = bpy.data.objects.new(name, mesh)
    coll = collection(SOURCE_COLL)
    coll.objects.link(obj)
    if uv0 is not None:
        mesh.uv_layers["UV0"].data.foreach_set("uv", _face_uv_flat(uv0))
        obj["rw_needs_unwrap"] = False
    else:
        obj["rw_needs_unwrap"] = True
    for aname, values in (point_attrs or {}).items():
        attr = mesh.attributes.new(aname, "FLOAT", "POINT")
        attr.data.foreach_set("value", list(values))
    for aname, values in (face_attrs or {}).items():
        attr = mesh.attributes.new(aname, "FLOAT", "FACE")
        attr.data.foreach_set("value", list(values))
    if mat is not None:
        mesh.materials.append(mat)
    mesh.update()
    if recalc:
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(mesh)
        bm.free()
    finish_shading(obj, smooth, sharp_angle, sharp_pairs)
    return obj


def finish_shading(obj, smooth=True, sharp_angle=35.0, sharp_pairs=None):
    mesh = obj.data
    if smooth:
        mesh.shade_smooth()
        if sharp_angle is not None:
            mesh.set_sharp_from_angle(angle=math.radians(sharp_angle))
    else:
        mesh.shade_flat()
    if sharp_pairs:
        attr = mesh.attributes.get("sharp_edge") or mesh.attributes.new("sharp_edge", "BOOLEAN", "EDGE")
        lookup = {tuple(sorted(e.vertices)): e.index for e in mesh.edges}
        values = [False] * len(mesh.edges)
        attr.data.foreach_get("value", values)
        for a, b in sharp_pairs:
            key = (a, b) if a < b else (b, a)
            if key in lookup:
                values[lookup[key]] = True
        attr.data.foreach_set("value", values)
    mesh.update()


def _newell(points):
    n = Vector((0.0, 0.0, 0.0))
    for i, p in enumerate(points):
        q = points[(i + 1) % len(points)]
        n.x += (p.y - q.y) * (p.z + q.z)
        n.y += (p.z - q.z) * (p.x + q.x)
        n.z += (p.x - q.x) * (p.y + q.y)
    return n.normalized() if n.length > 1e-12 else Vector((0, 0, 1))


def _planar_uv(points):
    c = sum(points, Vector()) / len(points)
    n = _newell(points)
    a1 = (points[0] - c)
    a1 = (a1 - n * a1.dot(n))
    if a1.length < 1e-9:
        a1 = n.orthogonal()
    a1.normalize()
    a2 = n.cross(a1)
    return [((p - c).dot(a1), (p - c).dot(a2)) for p in points]


def loft(name, rings, mat=None, closed=True, cap_start=True, cap_end=True, tip_start=None,
         tip_end=None, sharp_cols=(), sharp_rings=(), chunk=0.30, smooth=True, sharp_angle=35.0,
         point_attrs=None, face_attr=None, closed_u=False, v_scale=1.0, recalc=True):
    """Skin a list of equal-length rings (each ordered right-handed about the
    direction of travel) into a mesh with metric UVs.

    ``point_attrs``: name -> callable(i, j) evaluated per ring vertex (tips use
    i = -1/len). ``face_attr``: name -> callable(i, j) for side faces.
    """
    m = len(rings)
    n = len(rings[0])
    V = [Vector(p) for ring in rings for p in ring]
    idx = lambda i, j: (i % m) * n + (j % n)  # noqa: E731
    seg_count = m if closed_u else m - 1
    # Travelled distance along the loft, measured between ring centroids so
    # every ring maps to a straight UV row: a per-column distance shears the
    # rows of twisted ribbons until their triangulated quads overlap in UV.
    U = [[0.0] * n for _ in range(m + 1)]
    cents = [sum((V[idx(i, j)] for j in range(n)), Vector()) / n for i in range(m)]
    for i in range(1, m + (1 if closed_u else 0)):
        step = (cents[i % m] - cents[i - 1]).length
        if step < 1e-9:
            step = sum((V[idx(i, j)] - V[idx(i - 1, j)]).length for j in range(n)) / n
        for j in range(n):
            U[i][j] = U[i - 1][j] + step
    # Ring perimeter distance (n + 1 samples when closed).
    P = []
    for i in range(m):
        acc = [0.0]
        for j in range(n if closed else n - 1):
            acc.append(acc[-1] + (V[idx(i, j + 1)] - V[idx(i, j)]).length * v_scale)
        P.append(acc)
    faces, uvm, uv0, sharp = [], [], [], []
    fattrs = {k: [] for k in (face_attr or {})}
    cols = n if closed else n - 1
    for i in range(seg_count):
        i1 = i + 1
        umid = sum(U[i][j] + U[i1][j] for j in range(n)) / (2 * n)
        c = int(umid // chunk) if chunk else 0
        ustart = c * chunk
        pi, pi1 = P[i], P[i1 % m]
        for j in range(cols):
            a, d, cc, b = idx(i, j), idx(i, j + 1), idx(i1, j + 1), idx(i1, j)
            faces.append((a, d, cc, b))
            jn = (j + 1) % n
            quad = [(U[i][j], pi[j]), (U[i][jn], pi[j + 1]), (U[i1][jn], pi1[j + 1]), (U[i1][j], pi1[j])]
            uvm.append(quad)
            uv0.append([(u - ustart, v) for u, v in quad])
            for k, fn in (face_attr or {}).items():
                fattrs[k].append(fn(i, j))
    for j in sharp_cols:
        for i in range(seg_count):
            sharp.append((idx(i, j), idx(i + 1, j)))
    for i in sharp_rings:
        for j in range(cols):
            sharp.append((idx(i, j), idx(i, j + 1)))
    verts = list(V)
    extra_attr_rows = []

    def cap(i, reverse):
        ring = [V[idx(i, j)] for j in range(n)]
        order = list(range(n))[::-1] if reverse else list(range(n))
        f = tuple(idx(i, j) for j in order)
        faces.append(f)
        puv = _planar_uv([ring[j] for j in order])
        off = 10.0 + len(faces) * 0.0  # separate island (packing re-places it)
        uvm.append(puv)
        uv0.append([(u + off, v) for u, v in puv])
        for k in fattrs:
            fattrs[k].append(fattrs[k][-1] if fattrs[k] else 0.0)

    def tip(i, point, at_end):
        ti = len(verts)
        verts.append(Vector(point))
        extra_attr_rows.append((ti, i))
        ring_last = [V[idx(i, j)] for j in range(n)]
        dist = [(Vector(point) - p).length for p in ring_last]
        for j in range(cols):
            j1 = (j + 1) % n
            if at_end:
                f = (idx(i, j), idx(i, j + 1), ti)
                u0 = U[i][j]
                quad = [(u0, P[i][j]), (U[i][j1], P[i][j + 1]), (u0 + dist[j], (P[i][j] + P[i][j + 1]) / 2)]
            else:
                f = (idx(i, j + 1), idx(i, j), ti)
                quad = [(-0.0, P[i][j + 1]), (0.0, P[i][j]), (-dist[j], (P[i][j] + P[i][j + 1]) / 2)]
            faces.append(f)
            uvm.append(quad)
            base = int((sum(q[0] for q in quad) / 3) // chunk) * chunk if chunk else 0.0
            uv0.append([(u - base, v) for u, v in quad])
            for k, fn in (face_attr or {}).items():
                fattrs[k].append(fn(i, j))

    if not closed_u:
        if tip_start is not None:
            tip(0, tip_start, False)
        elif cap_start:
            cap(0, True)
        if tip_end is not None:
            tip(m - 1, tip_end, True)
        elif cap_end:
            cap(m - 1, False)
    pattrs = {}
    for k, fn in (point_attrs or {}).items():
        vals = [fn(i, j) for i in range(m) for j in range(n)]
        for ti, i in extra_attr_rows:
            vals.append(fn(i if i == 0 else m - 1, 0))
        pattrs[k] = vals
    return make_obj(name, verts, faces, mat, uv0=uv0, uvm=uvm, smooth=smooth, sharp_angle=sharp_angle,
                    sharp_pairs=sharp, point_attrs=pattrs, face_attrs=fattrs, recalc=recalc)


def ring_ellipse(ry, rz, sides, cy=0.0, cz=0.0, x=0.0, start=0.0):
    """Right-handed about +X: (y, z) = (ry cos t, rz sin t)."""
    return [(x, cy + ry * math.cos(start + math.tau * k / sides), cz + rz * math.sin(start + math.tau * k / sides))
            for k in range(sides)]


def ring_superellipse(ry, rz, sides, power=2.5, cy=0.0, cz=0.0, x=0.0):
    pts = []
    for k in range(sides):
        t = math.tau * k / sides
        c, s = math.cos(t), math.sin(t)
        y = ry * math.copysign(abs(c) ** (2.0 / power), c)
        z = rz * math.copysign(abs(s) ** (2.0 / power), s)
        pts.append((x, cy + y, cz + z))
    return pts


def polygon2d(k, r_flats, corner=0.0, seg=3, rot=None):
    """Regular k-gon (distance to flats r_flats) with rounded corners, CCW."""
    rot = math.pi / k if rot is None else rot
    r_corner = r_flats / math.cos(math.pi / k)
    pts = []
    for i in range(k):
        a = rot + math.tau * i / k
        if corner <= 0.0:
            pts.append((r_corner * math.cos(a), r_corner * math.sin(a)))
            continue
        # Fillet: centre moved inward so the arc is tangent to both flats.
        cdist = (r_flats - corner) / math.cos(math.pi / k)
        cx, cy = cdist * math.cos(a), cdist * math.sin(a)
        for s in range(seg + 1):
            t = a - math.pi / k + (math.tau / k) * s / seg
            pts.append((cx + corner * math.cos(t), cy + corner * math.sin(t)))
    return pts


def resample_sections(sections, max_seg):
    out = [tuple(sections[0])]
    for a, b in zip(sections[:-1], sections[1:]):
        steps = max(1, int(math.ceil(abs(b[0] - a[0]) / max_seg)))
        for k in range(1, steps + 1):
            t = k / steps
            out.append(tuple(pa + (pb - pa) * t for pa, pb in zip(a, b)))
    return out


def tube(name, sections, mat=None, sides=32, shape="ellipse", power=2.5, poly=None, max_seg=0.03, **kw):
    """Straight tube along +X. sections: (x, ry, rz[, cy, cz]); long spans are
    resampled to ``max_seg`` so UV islands can be split and LODs decimate well."""
    rings = []
    if max_seg:
        sections = resample_sections(sections, max_seg)
    for sec in sections:
        x, ry, rz = sec[:3]
        cy = sec[3] if len(sec) > 3 else 0.0
        cz = sec[4] if len(sec) > 4 else 0.0
        if shape == "ellipse":
            rings.append(ring_ellipse(ry, rz, sides, cy, cz, x))
        elif shape == "super":
            rings.append(ring_superellipse(ry, rz, sides, power, cy, cz, x))
        elif shape == "poly":
            pts = poly
            rings.append([(x, cy + ry * a, cz + rz * b) for a, b in pts])
        else:
            raise ValueError(shape)
    return loft(name, rings, mat, **kw)


def rmf_frames(path, up):
    """Rotation-minimising frames (double reflection) along a polyline."""
    pts = [Vector(p) for p in path]
    tangents = []
    for i in range(len(pts)):
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, len(pts) - 1)]
        t = (b - a)
        tangents.append(t.normalized() if t.length > 1e-12 else Vector((1, 0, 0)))
    up = Vector(up)
    n0 = up - tangents[0] * up.dot(tangents[0])
    if n0.length < 1e-9:
        n0 = tangents[0].orthogonal()
    normals = [n0.normalized()]
    for i in range(len(pts) - 1):
        v1 = pts[i + 1] - pts[i]
        c1 = v1.dot(v1)
        if c1 < 1e-18:
            normals.append(normals[-1].copy())
            continue
        rL = normals[i] - (2.0 / c1) * v1.dot(normals[i]) * v1
        tL = tangents[i] - (2.0 / c1) * v1.dot(tangents[i]) * v1
        v2 = tangents[i + 1] - tL
        c2 = v2.dot(v2)
        nn = rL - (2.0 / c2) * v2.dot(rL) * v2 if c2 > 1e-18 else rL
        normals.append(nn.normalized())
    frames = []
    for t, nrm in zip(tangents, normals):
        b = t.cross(nrm)
        frames.append((t, nrm, b))
    return pts, frames


def sweep(name, path, profile, mat=None, up=(0, 0, 1), twist=None, scale=None, offset=None,
          closed_path=False, **kw):
    """Sweep a 2D profile [(a, b)] (a along the frame normal, b along the
    binormal; counter-clockwise) along a polyline. twist/scale/offset are
    callables of the path parameter t in [0, 1] returning an angle, (sa, sb),
    and a Vector added to the ring centre."""
    pts, frames = rmf_frames(path, up)
    count = len(pts)
    if closed_path:
        # Distribute the frame mismatch at closure as a linear twist.
        t0, n0, _b0 = frames[0]
        _tl, nl, bl = frames[-1]
        mismatch = math.atan2(nl.cross(n0).dot(t0), nl.dot(n0))
    rings = []
    for i, (p, (t, nrm, b)) in enumerate(zip(pts, frames)):
        u = i / max(count - 1, 1)
        ang = twist(u) if twist else 0.0
        if closed_path:
            ang += mismatch * i / count
        sa, sb = scale(u) if scale else (1.0, 1.0)
        centre = p + (offset(u) if offset else Vector())
        ca, sn = math.cos(ang), math.sin(ang)
        n2 = nrm * ca + b * sn
        b2 = -nrm * sn + b * ca
        # Right-handed ordering about t requires n x b = t (true for these frames).
        rings.append([centre + n2 * (a * sa) + b2 * (bb * sb) for a, bb in profile])
    return loft(name, rings, mat, closed_u=closed_path, **kw)


def circle2d(r, sides):
    return [(r * math.cos(math.tau * k / sides), r * math.sin(math.tau * k / sides)) for k in range(sides)]


def lens2d(width, thick, sides=12, power=3.0):
    """Flat ribbon cross-section: a superellipse with half-width along b."""
    pts = []
    for k in range(sides):
        t = math.tau * k / sides
        c, s = math.cos(t), math.sin(t)
        a = thick / 2 * math.copysign(abs(c) ** (2.0 / power), c)
        b = width / 2 * math.copysign(abs(s) ** (2.0 / power), s)
        pts.append((a, b))
    return pts


PLANES = {
    # local x, local y, local z (extrusion) -> world axes
    "XZ": Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1))),
    "YZ": Matrix(((0, 0, 1, 0), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1))),
    "XY": Matrix.Identity(4),
}


def extrude_outline(name, loops, thickness, bevel=0.0005, mat=None, plane="XZ", center=0.0,
                    bevel_res=2, sharp_angle=35.0, fill_both=True):
    """Extrude closed 2D outlines (first = outer, rest = holes) symmetrically
    about ``center`` along the plane's normal, with a rounded bevel that keeps
    the outer size (curve offset compensates the bevel)."""
    cu = bpy.data.curves.new(name + "_curve", "CURVE")
    cu.dimensions = "2D"
    cu.fill_mode = "BOTH" if fill_both else "FRONT"
    bevel = min(bevel, thickness * 0.45)
    cu.extrude = max(thickness / 2.0 - bevel, 1e-6)
    cu.bevel_depth = bevel
    cu.bevel_resolution = bevel_res
    cu.offset = -bevel  # the bevel grows the outline by its depth; compensate
    cu.use_fill_caps = False
    loops = [orient(loop, k == 0) for k, loop in enumerate(loops)]
    for k, loop in enumerate(loops):
        sp = cu.splines.new("POLY")
        sp.points.add(len(loop) - 1)
        for pt, (a, b) in zip(sp.points, loop):
            pt.co = (a, b, 0.0, 1.0)
        sp.use_cyclic_u = True
    obj = bpy.data.objects.new(name + "_tmp", cu)
    bpy.context.scene.collection.objects.link(obj)
    dg = bpy.context.evaluated_depsgraph_get()
    mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
    bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.curves.remove(cu)
    mesh.name = name
    # ``center`` is the world coordinate along the plane normal (Y for XZ,
    # X for YZ, Z for XY); the XZ basis maps local +z to world -Y.
    offset = {"XZ": (0.0, center, 0.0), "YZ": (center, 0.0, 0.0), "XY": (0.0, 0.0, center)}[plane]
    mat4 = Matrix.Translation(offset) @ PLANES[plane]
    mesh.transform(mat4)
    for n in [l.name for l in mesh.uv_layers]:
        mesh.uv_layers.remove(mesh.uv_layers[n])
    mesh.uv_layers.new(name="UV0")
    mesh.uv_layers.new(name="UVMetric")
    mesh.materials.clear()
    if mat is not None:
        mesh.materials.append(mat)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    box_uv(mesh, "UVMetric")
    out = bpy.data.objects.new(name, mesh)
    collection(SOURCE_COLL).objects.link(out)
    out["rw_needs_unwrap"] = True
    finish_shading(out, True, sharp_angle)
    return out


def signed_area(loop):
    return 0.5 * sum(loop[i][0] * loop[(i + 1) % len(loop)][1] - loop[(i + 1) % len(loop)][0] * loop[i][1]
                     for i in range(len(loop)))


def orient(loop, ccw=True):
    """Return the loop counter-clockwise (outer) or clockwise (hole)."""
    loop = list(loop)
    return loop if (signed_area(loop) > 0) == ccw else list(reversed(loop))


def fillet_poly(points, radius, seg=5):
    """Round every corner of a closed 2D polygon. ``radius`` is a number or a
    per-corner list (0 keeps the corner sharp)."""
    n = len(points)
    radii = radius if isinstance(radius, (list, tuple)) else [radius] * n
    out = []
    for i in range(n):
        p0 = Vector(points[i - 1])
        p1 = Vector(points[i])
        p2 = Vector(points[(i + 1) % n])
        r = radii[i]
        d1 = (p0 - p1)
        d2 = (p2 - p1)
        if r <= 0 or d1.length < 1e-9 or d2.length < 1e-9:
            out.append((p1.x, p1.y))
            continue
        d1.normalize()
        d2.normalize()
        cosang = max(-0.9999, min(0.9999, d1.dot(d2)))
        half = math.acos(cosang) / 2.0
        if half < 1e-3 or abs(half - math.pi / 2) < 1e-3:
            out.append((p1.x, p1.y))
            continue
        dist = r / math.tan(half)
        lim = min((Vector(points[i - 1]) - p1).length, (Vector(points[(i + 1) % n]) - p1).length) * 0.49
        if dist > lim:
            dist = lim
            r = dist * math.tan(half)
        a = p1 + d1 * dist
        c = p1 + d2 * dist
        bis = (d1 + d2).normalized()
        centre = p1 + bis * (r / math.sin(half))
        a0 = math.atan2(a.y - centre.y, a.x - centre.x)
        a1 = math.atan2(c.y - centre.y, c.x - centre.x)
        da = a1 - a0
        while da > math.pi:
            da -= math.tau
        while da < -math.pi:
            da += math.tau
        for k in range(seg + 1):
            t = a0 + da * k / seg
            out.append((centre.x + r * math.cos(t), centre.y + r * math.sin(t)))
    return out


def catmull_closed(points, samples=6):
    pts = [Vector(p) for p in points]
    n = len(pts)
    out = []
    for i in range(n):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        for k in range(samples):
            t = k / samples
            t2, t3 = t * t, t * t * t
            q = 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 +
                       (-p0 + 3 * p1 - 3 * p2 + p3) * t3)
            out.append((q.x, q.y))
    return out


def helix(name, x0, x1, radius, pitch, wire, mat, cy=0.0, cz=0.0, samples_per_turn=32, sides=6):
    turns = (x1 - x0) / pitch
    n = max(int(turns * samples_per_turn), 8)
    path = []
    for i in range(n + 1):
        t = i / n
        a = math.tau * turns * t
        path.append(Vector((x0 + (x1 - x0) * t, cy + radius * math.cos(a), cz + radius * math.sin(a))))
    return sweep(name, path, circle2d(wire / 2, sides), mat, up=(1, 0, 0), chunk=0.15, sharp_angle=None)


def strip_wrap(name, x0, x1, radius, width, thick, overlap, mat, jitter=0.0, seed=0.0, samples_per_turn=40,
               ry_rz=1.0, lift=0.0):
    """A flat strip (cloth, leather, rattan) wound on a helix round an X-axis
    shaft of radius ``radius(x)`` (callable or number); each turn laps the
    previous by ``overlap`` of the width, so the strip is shingled (its
    leading edge stands a strip thickness proud) and every lap shows as a
    spiral step. ``jitter`` wobbles the pitch by hand."""
    rfn = radius if callable(radius) else (lambda _x, r=radius: r)
    pitch = width * (1.0 - overlap)
    turns = max((x1 - x0) / pitch, 1.0)
    n = max(int(turns * samples_per_turn), 16)
    path, normals = [], []
    for i in range(n + 1):
        t = i / n
        a = math.tau * turns * t
        wob = jitter * pitch * (math.sin(a * 0.37 + seed) * 0.6 + math.sin(a * 1.13 + 2.0 * seed) * 0.4)
        x = x0 + (x1 - x0) * t + wob
        r = rfn(x) + thick * 0.5 + lift
        nrm = Vector((0.0, math.cos(a), math.sin(a) * ry_rz)).normalized()
        path.append(Vector((x, r * math.cos(a), r * ry_rz * math.sin(a))))
        normals.append(nrm)
    tilt = thick / max(width * overlap, 1e-6) * 0.9
    # Turn k+1's -X edge rides on turn k's +X edge: raise the -X side.
    prof = [(a_ - b_ * tilt, b_) for a_, b_ in lens2d(width, thick, 10, 4.0)]
    rings = []
    for i in range(len(path)):
        p = path[i]
        tv = (path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]).normalized()
        nv = (normals[i] - tv * normals[i].dot(tv)).normalized()
        bv = tv.cross(nv)
        # The binormal runs along the shaft (toward +X); the lap rises toward
        # the side of the strip that covers the previous turn.
        if bv.x < 0:
            bv = -bv
        rings.append([p + nv * pa + bv * pb for pa, pb in prof])
    return loft(name, rings, mat, closed=True, chunk=0.15, sharp_angle=None)


def bore_tube(name, sections, bore_r, bore_depth, mat, sides=40, shape="ellipse", poly=None, **kw):
    """Barrel along +X whose muzzle face opens into a bore of radius bore_r
    that runs ``bore_depth`` back (dark end cap)."""
    rings = []
    secs = resample_sections(sections, 0.02)

    def ring(x, ry, rz):
        if shape == "poly":
            return [(x, ry * a, rz * b) for a, b in poly]
        return ring_ellipse(ry, rz, sides, 0.0, 0.0, x)
    for x, ry, rz in secs:
        rings.append(ring(x, ry, rz))
    xm = secs[-1][0]
    count = len(rings[0])
    inner = []
    for k in range(count):
        a = math.tau * k / count
        if shape == "poly":
            pa, pb = poly[k]
            a = math.atan2(pb, pa)
        inner.append((a,))
    bore_rings = []
    for x in (xm, xm - 0.002, xm - bore_depth):
        bore_rings.append([(x, bore_r * math.cos(t[0]), bore_r * math.sin(t[0])) for t in inner])
    rings += bore_rings
    return loft(name, rings, mat, closed=True, cap_start=True, cap_end=True, **kw)


def offset_outline(loop, d):
    """Inset (d < 0) or outset a CCW polyline outline by d (miter, clamped)."""
    n = len(loop)
    out = []
    for i in range(n):
        p0 = Vector(loop[i - 1])
        p1 = Vector(loop[i])
        p2 = Vector(loop[(i + 1) % n])
        e1 = (p1 - p0).normalized()
        e2 = (p2 - p1).normalized()
        n1 = Vector((e1.y, -e1.x))
        n2 = Vector((e2.y, -e2.x))
        nm = (n1 + n2)
        if nm.length < 1e-9:
            nm = n1
        nm.normalize()
        cosh = max(nm.dot(n1), 0.3)
        q = p1 + nm * (d / cosh)
        out.append((q.x, q.y))
    return out


def box(name, center, size, mat=None, bevel=0.0008, segments=2, sharp_angle=35.0):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2])) + Vector(center)
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=segments, profile=0.5,
                        affect="EDGES", clamp_overlap=True)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for n in [l.name for l in mesh.uv_layers]:
        mesh.uv_layers.remove(mesh.uv_layers[n])
    mesh.uv_layers.new(name="UV0")
    mesh.uv_layers.new(name="UVMetric")
    box_uv(mesh, "UVMetric")
    if mat is not None:
        mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    collection(SOURCE_COLL).objects.link(obj)
    obj["rw_needs_unwrap"] = True
    finish_shading(obj, True, sharp_angle)
    return obj


def transform(obj, matrix):
    obj.data.transform(matrix)
    obj.data.update()
    return obj


def rot(axis, degrees):
    return Matrix.Rotation(math.radians(degrees), 4, axis)


def trans(x, y=0.0, z=0.0):
    return Matrix.Translation(Vector((x, y, z)))


def apply_modifiers(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    mesh = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
    old = obj.data
    obj.modifiers.clear()
    obj.data = mesh
    mesh.name = old.name
    bpy.data.meshes.remove(old)
    return obj


def bevel_mod(obj, width, segments=2, angle=35.0, harden=False):
    mod = obj.modifiers.new("RW_Bevel", "BEVEL")
    mod.width = width
    mod.segments = segments
    mod.limit_method = "ANGLE"
    mod.angle_limit = math.radians(angle)
    mod.harden_normals = harden
    mod.use_clamp_overlap = True
    apply_modifiers(obj)
    ensure_uv_layers(obj.data)
    box_uv(obj.data, "UVMetric")
    obj["rw_needs_unwrap"] = True
    finish_shading(obj, True, angle)
    return obj


def boolean(obj, cutter, op="DIFFERENCE"):
    mod = obj.modifiers.new("RW_Bool", "BOOLEAN")
    mod.operation = op
    mod.object = cutter
    mod.solver = "EXACT"
    cutter.hide_render = True
    apply_modifiers(obj)
    bpy.data.objects.remove(cutter, do_unlink=True)
    ensure_uv_layers(obj.data)
    box_uv(obj.data, "UVMetric")
    obj["rw_needs_unwrap"] = True
    finish_shading(obj, True, 35.0)
    return obj


def join(objs, name):
    objs = [o for o in objs if o is not None]
    if len(objs) == 1:
        objs[0].name = name
        return objs[0]
    ctx = {"active_object": objs[0], "selected_editable_objects": objs, "object": objs[0]}
    needs = any(o.get("rw_needs_unwrap", True) for o in objs)
    with bpy.context.temp_override(**ctx):
        bpy.ops.object.join()
    objs[0].name = name
    objs[0].data.name = name
    objs[0]["rw_needs_unwrap"] = needs
    return objs[0]


def sora_mon(name, diameter, thickness, mat=None, bevel=0.0002):
    """The pinned user SORA SVG (two filled paths), centred, in the local XY
    plane facing +Z, extruded symmetrically; never redrawn or simplified."""
    if sha256(LOGO) != LOGO_SHA256:
        raise RuntimeError("The user-supplied SORA SVG changed; refusing to build the mon")
    before = set(bpy.data.objects)
    bpy.ops.import_curve.svg(filepath=str(LOGO))
    curves = [o for o in set(bpy.data.objects) - before if o.type == "CURVE"]
    assert len(curves) == 2, [o.name for o in curves]
    corners = [o.matrix_world @ Vector(c) for o in curves for c in o.bound_box]
    minx, maxx = min(p.x for p in corners), max(p.x for p in corners)
    miny, maxy = min(p.y for p in corners), max(p.y for p in corners)
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
    size = max(maxx - minx, maxy - miny)
    parts = []
    for o in curves:
        o.data.dimensions = "2D"
        o.data.fill_mode = "BOTH"
        o.data.extrude = max(thickness / 2 - bevel, 1e-6) / (diameter / size) / o.matrix_world.to_scale().x
        o.data.bevel_depth = bevel / (diameter / size) / o.matrix_world.to_scale().x
        o.data.bevel_resolution = 1
        dg = bpy.context.evaluated_depsgraph_get()
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
        me.transform(o.matrix_world)
        me.transform(Matrix.Scale(diameter / size, 4) @ Matrix.Translation(Vector((-cx, -cy, 0))))
        ob = bpy.data.objects.new(name + "_path", me)
        collection(SOURCE_COLL).objects.link(ob)
        parts.append(ob)
    for o in curves:
        data = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        if data.users == 0:
            bpy.data.curves.remove(data)
    for coll in list(bpy.data.collections):
        if coll.name.startswith("sora_logo") and not coll.objects:
            bpy.data.collections.remove(coll)
    obj = join(parts, name)
    mesh = obj.data
    for n in [l.name for l in mesh.uv_layers]:
        mesh.uv_layers.remove(mesh.uv_layers[n])
    mesh.uv_layers.new(name="UV0")
    mesh.uv_layers.new(name="UVMetric")
    box_uv(mesh, "UVMetric")
    mesh.materials.clear()
    if mat is not None:
        mesh.materials.append(mat)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    obj["rw_needs_unwrap"] = True
    obj["rw_sora_mon_sha256"] = LOGO_SHA256
    finish_shading(obj, True, 30.0)
    return obj


def wrap_to_cylinder(obj, radius_fn, axis_center=(0.0, 0.0)):
    """Bend a flat decal lying in local XY (facing +Z, sitting at z = 0) onto an
    X-axis surface: local y becomes arc length around X at radius r(x) and
    local z becomes radial offset. The decal's centre sits at angle 0 (+Y)."""
    for v in obj.data.vertices:
        x, y, z = v.co
        r = radius_fn(x) + z
        ang = y / max(radius_fn(x), 1e-6)
        v.co = Vector((x, axis_center[0] + r * math.cos(ang), axis_center[1] + r * math.sin(ang)))
    obj.data.update()
    return obj


# ---------------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------------

REG: dict[str, dict] = {}


def cc0(*parts) -> Path:
    path = CC0.joinpath(*parts)
    if not path.is_file():
        raise FileNotFoundError(f"CC0 raw input missing: {rel(path)} (run scripts/assets/fetch_cc0.py)")
    USED_SOURCES.add(rel(path))
    return path


def committed(*parts) -> Path:
    path = PH_COMMITTED.joinpath(*parts)
    if not path.is_file():
        raise FileNotFoundError(rel(path))
    USED_SOURCES.add(rel(path))
    return path


def load_image(path: Path, colorspace="sRGB"):
    key = f"{path.name}|{colorspace}"
    img = bpy.data.images.get(key)
    if img is None:
        img = bpy.data.images.load(str(path), check_existing=False)
        img.name = key
        img.colorspace_settings.name = colorspace
    return img


class NB:
    """Small node-graph builder: every helper returns an output socket."""

    def __init__(self, name):
        mat = bpy.data.materials.new(name)
        if mat.node_tree is None:
            mat.use_nodes = True
        self.mat = mat
        self.nt = mat.node_tree
        self.nt.nodes.clear()
        self.out = self.nt.nodes.new("ShaderNodeOutputMaterial")
        self.bsdf = self.nt.nodes.new("ShaderNodeBsdfPrincipled")
        self.nt.links.new(self.bsdf.outputs[0], self.out.inputs["Surface"])
        self._tc = None
        self._uv = {}

    # plumbing -------------------------------------------------------------
    def node(self, kind, **props):
        n = self.nt.nodes.new(kind)
        for k, v in props.items():
            setattr(n, k, v)
        return n

    def link(self, a, b):
        self.nt.links.new(a, b)

    def feed(self, sock, v):
        if isinstance(v, bpy.types.NodeSocket):
            self.link(v, sock)
        elif isinstance(v, (tuple, list)):
            if sock.type == "RGBA" and len(v) == 3:
                sock.default_value = (*v, 1.0)
            else:
                sock.default_value = tuple(v)
        else:
            sock.default_value = v

    # math -----------------------------------------------------------------
    def m(self, op, a, b=None, c=None, clamp=False):
        n = self.node("ShaderNodeMath", operation=op, use_clamp=clamp)
        self.feed(n.inputs[0], a)
        if b is not None:
            self.feed(n.inputs[1], b)
        if c is not None:
            self.feed(n.inputs[2], c)
        return n.outputs[0]

    def add(self, a, b):
        return self.m("ADD", a, b)

    def sub(self, a, b):
        return self.m("SUBTRACT", a, b)

    def mul(self, a, b, clamp=False):
        return self.m("MULTIPLY", a, b, clamp=clamp)

    def div(self, a, b):
        return self.m("DIVIDE", a, b)

    def clamp01(self, a):
        return self.m("MULTIPLY", a, 1.0, clamp=True)

    def sin(self, a):
        return self.m("SINE", a)

    def pow(self, a, b):
        return self.m("POWER", a, b)

    def maxi(self, a, b):
        return self.m("MAXIMUM", a, b)

    def mini(self, a, b):
        return self.m("MINIMUM", a, b)

    def absf(self, a):
        return self.m("ABSOLUTE", a)

    def one_minus(self, a):
        return self.m("SUBTRACT", 1.0, a, clamp=True)

    def gauss(self, x, sigma):
        """exp(-(x/sigma)^2)"""
        q = self.m("DIVIDE", x, sigma)
        q = self.m("MULTIPLY", q, q)
        return self.m("EXPONENT", self.m("MULTIPLY", q, -1.0))

    def remap(self, v, a0, a1, b0=0.0, b1=1.0, smooth=False, clamp=True):
        n = self.node("ShaderNodeMapRange", data_type="FLOAT",
                      interpolation_type="SMOOTHSTEP" if smooth else "LINEAR", clamp=clamp)
        self.feed(n.inputs["Value"], v)
        self.feed(n.inputs["From Min"], a0)
        self.feed(n.inputs["From Max"], a1)
        self.feed(n.inputs["To Min"], b0)
        self.feed(n.inputs["To Max"], b1)
        return n.outputs["Result"]

    def lerp(self, a, b, t):
        n = self.node("ShaderNodeMix", data_type="FLOAT")
        self.feed(n.inputs[0], t)
        self.feed(n.inputs[2], a)
        self.feed(n.inputs[3], b)
        return n.outputs[0]

    # colour ---------------------------------------------------------------
    def rgb(self, c):
        n = self.node("ShaderNodeRGB")
        n.outputs[0].default_value = (*c, 1.0)
        return n.outputs[0]

    def mixc(self, t, a, b, blend="MIX"):
        n = self.node("ShaderNodeMix", data_type="RGBA", blend_type=blend)
        self.feed(n.inputs[0], t)
        self.feed(n.inputs[6], a)
        self.feed(n.inputs[7], b)
        return n.outputs[2]

    def mulc(self, a, b):
        return self.mixc(1.0, a, b, "MULTIPLY")

    def hsv(self, c, h=0.5, s=1.0, v=1.0):
        n = self.node("ShaderNodeHueSaturation")
        self.feed(n.inputs["Hue"], h)
        self.feed(n.inputs["Saturation"], s)
        self.feed(n.inputs["Value"], v)
        self.feed(n.inputs["Color"], c)
        return n.outputs[0]

    def bw(self, c):
        n = self.node("ShaderNodeRGBToBW")
        self.feed(n.inputs[0], c)
        return n.outputs[0]

    def sep(self, c):
        n = self.node("ShaderNodeSeparateColor")
        self.feed(n.inputs[0], c)
        return n.outputs[0], n.outputs[1], n.outputs[2]

    def ramp(self, fac, stops):
        n = self.node("ShaderNodeValToRGB")
        self.feed(n.inputs[0], fac)
        els = n.color_ramp.elements
        while len(els) > 1:
            els.remove(els[-1])
        els[0].position = stops[0][0]
        els[0].color = (*stops[0][1], 1.0)
        for pos, col in stops[1:]:
            e = els.new(pos)
            e.color = (*col, 1.0)
        return n.outputs[0]

    # coordinates ----------------------------------------------------------
    def obj(self):
        if self._tc is None:
            self._tc = self.node("ShaderNodeTexCoord")
        return self._tc.outputs["Object"]

    def uv(self, name="UVMetric"):
        if name not in self._uv:
            self._uv[name] = self.node("ShaderNodeUVMap", uv_map=name).outputs[0]
        return self._uv[name]

    def vmul(self, vec, s):
        n = self.node("ShaderNodeVectorMath", operation="MULTIPLY")
        self.feed(n.inputs[0], vec)
        self.feed(n.inputs[1], s if isinstance(s, (tuple, list)) else (s, s, s))
        return n.outputs[0]

    def vadd(self, vec, s):
        n = self.node("ShaderNodeVectorMath", operation="ADD")
        self.feed(n.inputs[0], vec)
        self.feed(n.inputs[1], s)
        return n.outputs[0]

    def vxyz(self, vec):
        n = self.node("ShaderNodeSeparateXYZ")
        self.feed(n.inputs[0], vec)
        return n.outputs[0], n.outputs[1], n.outputs[2]

    def xyz(self, x, y, z):
        n = self.node("ShaderNodeCombineXYZ")
        self.feed(n.inputs[0], x)
        self.feed(n.inputs[1], y)
        self.feed(n.inputs[2], z)
        return n.outputs[0]

    # textures -------------------------------------------------------------
    def noise(self, vec=None, scale=1.0, detail=2.0, rough=0.5, distortion=0.0, dim="3D", w=None,
              lac=2.0):
        n = self.node("ShaderNodeTexNoise", noise_dimensions=dim)
        if vec is not None and dim != "1D":
            self.feed(n.inputs["Vector"], vec)
        if w is not None:
            self.feed(n.inputs["W"], w)
        self.feed(n.inputs["Scale"], scale)
        self.feed(n.inputs["Detail"], detail)
        self.feed(n.inputs["Roughness"], rough)
        self.feed(n.inputs["Lacunarity"], lac)
        self.feed(n.inputs["Distortion"], distortion)
        return n.outputs["Fac"]

    def voronoi(self, vec, scale, feature="F1", rand=1.0, dim="3D"):
        n = self.node("ShaderNodeTexVoronoi", feature=feature, voronoi_dimensions=dim)
        self.feed(n.inputs["Vector"], vec)
        self.feed(n.inputs["Scale"], scale)
        self.feed(n.inputs["Randomness"], rand)
        return n

    def wave(self, vec, scale, kind="BANDS", direction="X", profile="SIN", distortion=0.0, detail=0.0):
        n = self.node("ShaderNodeTexWave", wave_type=kind, bands_direction=direction, rings_direction="X",
                      wave_profile=profile)
        self.feed(n.inputs["Vector"], vec)
        self.feed(n.inputs["Scale"], scale)
        self.feed(n.inputs["Distortion"], distortion)
        self.feed(n.inputs["Detail"], detail)
        return n.outputs["Fac"]

    def img(self, path, vec, colorspace="sRGB", box=False, blend=0.25):
        n = self.node("ShaderNodeTexImage")
        n.image = load_image(path, colorspace)
        n.interpolation = "Cubic" if not box else "Linear"
        if box:
            n.projection = "BOX"
            n.projection_blend = blend
        self.feed(n.inputs["Vector"], vec)
        return n

    def attr(self, name):
        n = self.node("ShaderNodeAttribute", attribute_type="GEOMETRY", attribute_name=name)
        return n.outputs["Fac"]

    # surface effects -------------------------------------------------------
    def geo(self):
        return self.node("ShaderNodeNewGeometry")

    def edge(self, radius=0.0012, gain=6.0, samples=8):
        bev = self.node("ShaderNodeBevel", samples=samples)
        self.feed(bev.inputs["Radius"], radius)
        g = self.geo()
        dot = self.node("ShaderNodeVectorMath", operation="DOT_PRODUCT")
        self.link(bev.outputs[0], dot.inputs[0])
        self.link(g.outputs["Normal"], dot.inputs[1])
        return self.m("MULTIPLY", self.m("SUBTRACT", 1.0, dot.outputs["Value"]), gain, clamp=True)

    def cavity(self, distance=0.004, samples=12):
        ao = self.node("ShaderNodeAmbientOcclusion", samples=samples, inside=False, only_local=True)
        self.feed(ao.inputs["Distance"], distance)
        return self.one_minus(ao.outputs["AO"])

    def bump(self, height, strength=1.0, distance=0.0005, normal=None):
        n = self.node("ShaderNodeBump")
        self.feed(n.inputs["Height"], height)
        self.feed(n.inputs["Strength"], strength)
        self.feed(n.inputs["Distance"], distance)
        if normal is not None:
            self.feed(n.inputs["Normal"], normal)
        return n.outputs["Normal"]

    def bump_m(self, height_m, normal=None, strength=1.0):
        """Bump from a height in metres (distance 1): the baked NormalDX then
        carries physically scaled relief (a 20 um ridge on a 1 mm pitch)."""
        return self.bump(height_m, strength, 1.0, normal)

    def smoothstep(self, v, a, b):
        return self.remap(v, a, b, smooth=True)

    def noise1(self, w, detail=2.0, rough=0.5):
        return self.noise(dim="1D", w=w, detail=detail, rough=rough)

    def band(self, v, a0, a1, feather):
        """1 inside [a0, a1] with smooth edges of ``feather``."""
        return self.mul(self.smoothstep(v, a0 - feather, a0 + feather * 0.5),
                        self.one_minus(self.smoothstep(v, a1 - feather * 0.5, a1 + feather)))

    def zones(self, v, spans, feather=0.02):
        """Union of handled zones [(a0, a1), ...] along one coordinate."""
        m = None
        for a0, a1 in spans:
            z = self.band(v, a0, a1, feather)
            m = z if m is None else self.maxi(m, z)
        return m

    def nmap_dx(self, color, strength=1.0, uv_map="UVMetric"):
        """DirectX (Y-down) tangent normal texture -> Blender (Y-up) normal."""
        r, g, b = self.sep(color)
        comb = self.node("ShaderNodeCombineColor")
        self.feed(comb.inputs[0], r)
        self.feed(comb.inputs[1], self.one_minus(g))
        self.feed(comb.inputs[2], b)
        nm = self.node("ShaderNodeNormalMap", space="TANGENT", uv_map=uv_map)
        self.feed(nm.inputs["Strength"], strength)
        self.link(comb.outputs[0], nm.inputs["Color"])
        return nm.outputs["Normal"]

    def finish(self, base, rough, metal, normal=None, mask=(0.0, 0.0, 0.0), emission=None, ao_dist=0.03,
               ao_extra=None, alpha=None):
        """Register the authoring outputs. ``ao_extra`` multiplies the baked
        AO (micro-cavities of the relief); ``alpha`` is an opacity mask baked
        into BaseColor A (fletching barbs)."""
        def sock(v, color=False):
            if isinstance(v, bpy.types.NodeSocket):
                return v
            if color:
                return self.rgb(v)
            n = self.node("ShaderNodeValue")
            n.outputs[0].default_value = float(v)
            return n.outputs[0]

        base = sock(base, True)
        rough = sock(rough)
        metal = sock(metal)
        masks = tuple(sock(x) for x in mask)
        self.feed(self.bsdf.inputs["Base Color"], base)
        self.feed(self.bsdf.inputs["Roughness"], rough)
        self.feed(self.bsdf.inputs["Metallic"], metal)
        if normal is not None:
            self.feed(self.bsdf.inputs["Normal"], normal)
        if alpha is not None:
            self.feed(self.bsdf.inputs["Alpha"], alpha)
        if emission is not None:
            col, strength = emission
            self.feed(self.bsdf.inputs["Emission Color"], col)
            self.feed(self.bsdf.inputs["Emission Strength"], self.mul(masks[0], strength))
        emissive_r = not (isinstance(mask[0], (int, float)) and float(mask[0]) == 0.0)
        REG[self.mat.name] = dict(base=base, rough=rough, metal=metal, normal=normal, mask=masks,
                                  ao_dist=ao_dist, emission=emission if emissive_r else None,
                                  ao_extra=sock(ao_extra) if ao_extra is not None else None,
                                  alpha=sock(alpha) if alpha is not None else None)
        return self.mat


# Linear-RGB colour helpers --------------------------------------------------

def srgb(r, g, b):
    def f(c):
        c = c / 255.0 if c > 1.0 else c
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return (f(r), f(g), f(b))


# ---------------------------------------------------------------------------
# Material recipes (authoring). Metal colours are specular F0 in linear RGB.
# Relief heights are in metres (NB.bump_m), so the baked NormalDX carries
# physically scaled microsurface: file strokes, casting pits, hammer facets,
# grain, weave and nodules of tenths of a millimetre.
# ---------------------------------------------------------------------------

def mat_blade_steel(name, hamon="notare_gunome", s_yokote=0.68, w_yokote=0.023, zukuri="shinogi",
                    mask_hamon=True):
    """Polished nihontō steel with an original procedural hamon.

    Reads per-vertex ``hamon_s`` (m from the machi), ``hamon_d`` (m from the
    edge across the face), ``blade_w`` (local width) and the face attribute
    ``blade_zone`` (0 hira, 1 shinogi-ji, 2 mune, 3 kissaki face).

    The hamon line wanders: gunome heads on a noise-modulated spacing and
    height over a slow notare, a nioiguchi 0.5-1.5 mm wide, ashi running
    from the valleys toward the edge and nie sparkle on the boundary. The
    polish is modelled as a Japanese polisher leaves it: the ji a dark
    near-mirror (roughness ~0.08) showing itame hada, the hadori-whitened
    ha (+13 % value, roughness 0.25-0.35), a burnished shinogi-ji and mune
    (roughness ~0.03) and a narume-whitened kissaki. ``mask_hamon`` False
    keeps Mask R free for an emissive part on the same weapon."""
    nb = NB(name)
    s = nb.attr("hamon_s")
    d = nb.attr("hamon_d")
    w = nb.attr("blade_w")
    zone = nb.attr("blade_zone")
    o = nb.obj()
    two_pi = math.tau
    hira_z = zukuri == "hira"

    if hamon == "notare_gunome":
        lam = 0.0205

        def phase(sv):
            j1 = nb.noise1(nb.mul(sv, 7.0), 2.0)
            j2 = nb.noise1(nb.add(nb.mul(sv, 31.0), 3.0), 2.0)
            return nb.add(nb.div(sv, lam), nb.add(nb.mul(nb.sub(j1, 0.5), 2.6), nb.mul(nb.sub(j2, 0.5), 0.7)))
        notare = nb.add(nb.mul(nb.sin(nb.add(nb.mul(s, two_pi / 0.115), 0.4)), 0.035),
                        nb.mul(nb.sin(nb.add(nb.mul(s, two_pi / 0.049), 1.3)), 0.018))
        head = nb.pow(nb.absf(nb.sin(nb.mul(phase(s), math.pi))), 0.7)
        amp = nb.remap(nb.noise1(nb.add(nb.mul(s, 11.0), 7.0), 2.0), 0.30, 0.72, 0.12, 1.0)
        small = nb.mul(nb.sub(nb.noise1(nb.mul(s, 140.0), 3.0), 0.5), 0.035)
        wav = nb.add(nb.add(notare, nb.mul(nb.mul(head, amp), 0.095)), small)
        h0 = nb.mul(w, nb.add(0.23, wav))
        ashi_keep = 0.42
    elif hamon == "suguha_ko_notare":
        lam = 0.028

        def phase(sv):
            return nb.add(nb.div(sv, lam), nb.mul(nb.sub(nb.noise1(nb.mul(sv, 6.0), 2.0), 0.5), 2.0))
        wav = nb.mul(nb.sin(nb.add(nb.mul(s, two_pi / 0.09), 0.2)), 0.02)
        wav = nb.add(wav, nb.mul(nb.sub(nb.noise1(nb.mul(s, 30.0), 2.0), 0.5), 0.035))
        head = nb.mul(nb.pow(nb.absf(nb.sin(nb.mul(phase(s), math.pi))), 0.8),
                      nb.remap(nb.noise1(nb.add(nb.mul(s, 9.0), 2.0)), 0.3, 0.7, 0.0, 0.035))
        h0 = nb.mul(w, nb.add(0.22, nb.add(wav, head)))
        ashi_keep = 0.5
    else:  # suguha
        lam = 0.013

        def phase(sv):
            return nb.add(nb.div(sv, lam), nb.mul(nb.sub(nb.noise1(nb.mul(sv, 9.0), 2.0), 0.5), 2.2))
        wav = nb.add(nb.mul(nb.sub(nb.noise1(nb.mul(s, 25.0), 2.0), 0.5), 0.03),
                     nb.mul(nb.sin(nb.mul(s, two_pi / 0.07)), 0.012))
        h0 = nb.mul(w, nb.add(0.24, wav))
        ashi_keep = 0.55
    # Yakidashi: the hamon starts low just above the machi.
    h = nb.lerp(nb.mul(w, 0.15), h0, nb.smoothstep(s, 0.0, 0.035))
    # Bōshi: a constant width along the fukura (turning back at the tip).
    boshi = w_yokote * (0.30 if hira_z else 0.34)
    fade = 0.012 if hira_z else 0.004
    h = nb.lerp(h, boshi, nb.smoothstep(s, s_yokote - fade, s_yokote + fade))
    diff = nb.sub(h, d)  # > 0 inside the hardened edge
    if hira_z:
        hira = nb.one_minus(nb.band(zone, 1.5, 2.5, 0.05))
        is_sj = 0.0
        kiss = 0.0
    else:
        hira = nb.clamp01(nb.add(nb.one_minus(nb.smoothstep(zone, 0.5, 0.6)), nb.smoothstep(zone, 2.5, 2.6)))
        is_sj = nb.band(zone, 0.55, 1.45, 0.05)
        kiss = nb.smoothstep(zone, 2.5, 2.6)
    is_mune = nb.band(zone, 1.55, 2.45, 0.05)
    wn = nb.add(0.0005, nb.mul(nb.noise1(nb.add(nb.mul(s, 23.0), 5.0), 2.0), 0.0010))  # nioiguchi 0.5-1.5 mm
    inside = nb.mul(nb.remap(diff, nb.mul(wn, -0.5), nb.mul(wn, 0.5), smooth=True), hira)
    q = nb.div(diff, nb.mul(wn, 0.45))
    nioi = nb.mul(nb.m("EXPONENT", nb.mul(nb.mul(q, q), -1.0)), hira)
    hadori = nb.mul(nb.smoothstep(nb.add(diff, 0.0007), -0.0016, 0.0016), hira)
    # Ashi: legs of nioi from the gunome valleys toward the edge, slightly slanted.
    sa = nb.add(s, nb.mul(diff, 0.35))
    av = nb.absf(nb.sin(nb.mul(phase(sa), math.pi)))
    ashi_line = nb.one_minus(nb.smoothstep(av, 0.018, 0.05))
    keep = nb.smoothstep(nb.noise1(nb.mul(sa, 60.0), 1.0), ashi_keep, ashi_keep + 0.04)
    alen = nb.add(0.0015, nb.mul(nb.noise1(nb.add(nb.mul(s, 40.0), 11.0)), 0.003))
    along = nb.mul(nb.smoothstep(diff, 0.0002, 0.0007),
                   nb.one_minus(nb.remap(diff, nb.mul(alen, 0.5), alen, smooth=True)))
    ashi = nb.mul(nb.mul(ashi_line, keep), nb.mul(along, hira))
    # Nie: martensite sparkle straddling the boundary.
    vor = nb.voronoi(o, 2400.0, "F1", 1.0)
    speck = nb.one_minus(nb.remap(vor.outputs["Distance"], 0.0, 0.25))
    pick = nb.smoothstep(nb.sep(vor.outputs["Color"])[0], 0.60, 0.66)
    band = nb.mul(nb.smoothstep(diff, -0.0008, 0.0006), nb.one_minus(nb.smoothstep(diff, 0.0015, 0.004)))
    nie = nb.mul(nb.mul(speck, pick), nb.mul(band, hira))
    # Itame hada in the jigane and the polisher's long strokes.
    hada = nb.noise(nb.vmul(o, (25.0, 380.0, 380.0)), 1.0, 6.0, 0.62, 0.55)
    hada2 = nb.noise(nb.vmul(o, (9.0, 90.0, 90.0)), 1.0, 3.0, 0.5, 0.8)
    grain = nb.add(nb.mul(nb.sub(hada, 0.5), 0.8), nb.mul(nb.sub(hada2, 0.5), 0.4))
    lines = nb.noise(nb.vmul(o, (6.0, 3200.0, 3200.0)), 1.0, 2.0, 0.5, 0.0)
    ji = nb.hsv(nb.rgb((0.42, 0.44, 0.46)), v=nb.add(1.0, nb.mul(grain, 0.10)))
    ha = nb.hsv(nb.rgb((0.42, 0.44, 0.46)), v=nb.add(1.13, nb.mul(grain, 0.03)))
    base = nb.mixc(hadori, ji, ha)
    base = nb.mixc(nb.mul(nioi, 0.55), base, nb.rgb((0.52, 0.535, 0.55)))
    base = nb.mixc(nb.mul(ashi, 0.6), base, nb.rgb((0.44, 0.455, 0.47)))
    base = nb.mixc(nb.mul(nie, 0.85), base, nb.rgb((0.72, 0.73, 0.74)))
    if not hira_z:
        base = nb.mixc(nb.mul(kiss, nb.one_minus(hadori)), base, nb.rgb((0.47, 0.485, 0.50)))
        base = nb.mixc(is_sj, base, nb.hsv(nb.rgb((0.36, 0.37, 0.39)), v=nb.add(1.0, nb.mul(grain, 0.05))))
    base = nb.mixc(is_mune, base, nb.rgb((0.38, 0.39, 0.41)))
    r_ji = nb.add(0.08, nb.add(nb.mul(grain, 0.03), nb.mul(nb.sub(lines, 0.5), 0.03)))
    r_ha = nb.add(0.30, nb.mul(nb.sub(nb.noise(o, 900.0, 2.0, 0.5), 0.5), 0.08))
    rough = nb.lerp(r_ji, r_ha, hadori)
    if not hira_z:
        rough = nb.lerp(rough, 0.20, nb.mul(kiss, nb.one_minus(hadori)))
    rough = nb.lerp(rough, 0.22, nb.mul(nioi, 0.7))
    rough = nb.lerp(rough, 0.16, nb.mul(ashi, 0.8))
    rough = nb.lerp(rough, 0.06, nie)
    if not hira_z:
        rough = nb.lerp(rough, 0.03, is_sj)
    rough = nb.lerp(rough, 0.045, is_mune)
    height = nb.add(nb.mul(grain, 0.000012), nb.mul(nb.sub(lines, 0.5), 0.000005))
    height = nb.sub(height, nb.mul(hadori, 0.000002))
    # Burnishing levels the shinogi-ji and mune to a mirror: no hada relief
    # there, so the reflected horizon stays a clean line.
    burnished = is_mune if hira_z else nb.clamp01(nb.add(is_sj, is_mune))
    height = nb.mul(height, nb.one_minus(nb.mul(burnished, 0.9)))
    normal = nb.bump_m(height)
    return nb.finish(base, rough, 1.0, normal, mask=(inside if mask_hamon else 0.0, 0.0, nioi), ao_dist=0.01)


def _hammer_facets(nb, o, size, depth):
    """Tsuchime: shallow dished hammer facets ``size`` across, ``depth`` deep (m)."""
    vor = nb.voronoi(o, 1.0 / size, "F1", 0.9)
    dist = vor.outputs["Distance"]
    return nb.mul(nb.mul(dist, dist), depth * 4.0)


def _pits(nb, o, size, depth, thresh=0.18):
    vor = nb.voronoi(o, 1.0 / size, "F1", 1.0)
    pit = nb.one_minus(nb.smoothstep(vor.outputs["Distance"], 0.0, thresh))
    sel = nb.smoothstep(nb.sep(vor.outputs["Color"])[1], 0.35, 0.40)
    return nb.mul(nb.mul(pit, sel), -depth)


def mat_iron(name, oxide=(0.030, 0.026, 0.022), rust=0.25, tsuchime=0.0, polish_edges=0.5,
             rough=0.52, metal=0.55, scale=1.0, cast=False, forge_scale=0.0, tekkotsu=0.0, bright=None):
    """Patinated forged (or cast) iron: black-brown oxide mottled over the
    steel, rust in the cavities from the CC0 rusty_metal_02 scan, polished
    wear on the arrises, and physically scaled relief: forging undulation,
    optional tsuchime hammer facets, flaking forge scale, casting pits and
    tekkotsu (the hard 'iron bones' standing proud on a guard's rim).
    ``bright`` is a callable nb -> mask of surfaces worked bright (a sledge's
    struck faces, a sickle's ground bevel): bare steel, roughness ~0.2, with
    fine criss-cross scuffs and no scale."""
    nb = NB(name)
    o = nb.obj()
    rust_img = nb.img(committed("rusty_metal_02", "rusty_metal_02_diff_2k.jpg"), nb.vmul(o, 3.2 / scale), box=True)
    rust_arm = nb.img(committed("rusty_metal_02", "rusty_metal_02_arm_2k.png"), nb.vmul(o, 3.2 / scale),
                      "Non-Color", box=True)
    rust_nrm = nb.img(committed("rusty_metal_02", "rusty_metal_02_nor_dx_2k.png"), nb.vmul(o, 3.2 / scale),
                      "Non-Color", box=True)
    _ao, r_scan, _m = nb.sep(rust_arm.outputs["Color"])
    cav = nb.cavity(0.004 * scale)
    edge = nb.edge(0.0012 * scale, 5.0)
    patch = nb.noise(o, 60.0 / scale, 4.0, 0.6, 0.3)
    rust_mask = nb.clamp01(nb.mul(nb.add(nb.mul(cav, 1.6), nb.sub(patch, 0.55)), rust * 2.2))
    var = nb.noise(o, 180.0 / scale, 3.0, 0.55)
    mott = nb.noise(o, 35.0 / scale, 3.0, 0.5)
    base = nb.hsv(nb.rgb(oxide), v=nb.add(0.80, nb.mul(var, 0.4)))
    # Black-brown patina: browner where the mottle is high, bluer-black elsewhere.
    base = nb.mixc(nb.mul(nb.smoothstep(mott, 0.35, 0.65), 0.6), nb.mulc(base, nb.rgb((0.85, 0.9, 1.05))),
                   nb.mulc(base, nb.rgb((1.35, 1.05, 0.78))))
    rust_col = nb.hsv(rust_img.outputs["Color"], s=0.85, v=0.55)
    base = nb.mixc(rust_mask, base, rust_col)
    worn_col = nb.rgb((0.36, 0.36, 0.35))
    worn = nb.mul(edge, polish_edges)
    base = nb.mixc(worn, base, worn_col)
    rgh = nb.lerp(nb.add(rough, nb.mul(nb.sub(r_scan, 0.5), 0.25)), 0.82, rust_mask)
    rgh = nb.lerp(rgh, 0.28, worn)
    mtl = nb.lerp(nb.lerp(metal, 0.05, rust_mask), 1.0, worn)
    nrm = nb.nmap_dx(rust_nrm.outputs["Color"], 0.35 + rust)
    height = nb.mul(nb.sub(var, 0.5), 0.00005 * scale)
    height = nb.add(height, nb.mul(nb.sub(mott, 0.5), 0.00008 * scale))
    if tsuchime:
        height = nb.add(height, _hammer_facets(nb, o, 0.0055 * scale, 0.00032 * tsuchime * scale))
    if forge_scale:
        flakes = nb.voronoi(o, 1.0 / (0.0035 * scale), "F1", 1.0)
        lift = nb.mul(nb.sub(nb.sep(flakes.outputs["Color"])[2], 0.5), 0.00003 * forge_scale * scale)
        crack = nb.voronoi(o, 1.0 / (0.0035 * scale), "DISTANCE_TO_EDGE", 1.0)
        height = nb.add(height, nb.add(lift, nb.mul(nb.one_minus(nb.smoothstep(crack.outputs["Distance"],
                                                                                0.0, 0.05)), -0.00002 * forge_scale)))
    if tekkotsu:
        bones = nb.noise(nb.vmul(o, (220.0, 220.0, 220.0)), 1.0, 3.0, 0.6, 1.2)
        height = nb.add(height, nb.mul(nb.smoothstep(bones, 0.55, 0.75), 0.00006 * tekkotsu))
    if cast:
        height = nb.add(height, _pits(nb, o, 0.0014 * scale, 0.00006))
    if bright is not None:
        bm = nb.clamp01(bright(nb))
        sc1 = nb.noise(nb.vmul(o, (3000.0, 3000.0, 40.0)), 1.0, 2.0, 0.5, 0.3)
        sc2 = nb.noise(nb.vmul(o, (40.0, 3000.0, 3000.0)), 1.0, 2.0, 0.5, 0.3)
        scuff = nb.add(nb.mul(sc1, 0.5), nb.mul(sc2, 0.5))
        steel = nb.hsv(nb.rgb((0.52, 0.52, 0.51)), v=nb.add(0.88, nb.mul(scuff, 0.24)))
        base = nb.mixc(bm, base, steel)
        rgh = nb.lerp(rgh, nb.add(0.17, nb.mul(scuff, 0.08)), bm)
        mtl = nb.lerp(mtl, 1.0, bm)
        # Striking dents and scuffs replace the scale and oxide relief.
        dents = nb.voronoi(o, 1.0 / 0.004, "F1", 1.0)
        dent_h = nb.mul(nb.mul(dents.outputs["Distance"], dents.outputs["Distance"]), 0.00006)
        height = nb.lerp(height, nb.add(dent_h, nb.mul(scuff, 0.000012)), bm)
        worn = nb.maxi(worn, bm)
    normal = nb.bump_m(height, nrm)
    if bright is not None:
        normal = nb.node("ShaderNodeMix", data_type="VECTOR")
        nb.feed(normal.inputs[0], bm)
        nb.feed(normal.inputs[4], nb.bump_m(height, nrm))
        nb.feed(normal.inputs[5], nb.bump_m(height))
        normal = normal.outputs[1]
    ao_extra = nb.one_minus(nb.mul(cav, 0.35))
    return nb.finish(base, rgh, mtl, normal, mask=(0.0, worn, cav), ao_dist=0.02, ao_extra=ao_extra)


def mat_ground_bevel(name, attr_name="bev_d"):
    """The stone-ground single bevel of a laminated edge tool (kama, kogatana):
    per-vertex ``bev_d`` runs 0 at the edge to 1 at the bevel shoulder. The
    hard hagane shows as a bright band along the edge (roughness ~0.12)
    under a wavering lamination line; the soft jigane cladding above it
    takes the stone's hazy kasumi finish; fine grinding scratches run along
    the blade and the shoulder keeps a dark thread of the forge scale."""
    nb = NB(name)
    o = nb.obj()
    d = nb.attr(attr_name)
    wave = nb.add(0.42, nb.mul(nb.sub(nb.noise(o, 45.0, 3.0, 0.6), 0.5), 0.22))
    hag = nb.one_minus(nb.smoothstep(d, nb.sub(wave, 0.05), nb.add(wave, 0.05)))
    scr = nb.noise(nb.vmul(o, (2600.0, 2600.0, 30.0)), 1.0, 3.0, 0.55, 0.2)
    haze = nb.noise(o, 260.0, 4.0, 0.6)
    ji = nb.hsv(nb.rgb((0.40, 0.40, 0.39)), v=nb.add(0.85, nb.mul(haze, 0.25)))
    ha = nb.hsv(nb.rgb((0.62, 0.62, 0.61)), v=nb.add(0.94, nb.mul(scr, 0.10)))
    base = nb.mixc(hag, ji, ha)
    shoulder = nb.smoothstep(d, 0.93, 0.99)
    base = nb.mixc(nb.mul(shoulder, 0.8), base, nb.rgb((0.05, 0.045, 0.04)))
    rgh = nb.lerp(nb.add(0.30, nb.mul(nb.sub(haze, 0.5), 0.10)), nb.add(0.11, nb.mul(scr, 0.05)), hag)
    rgh = nb.lerp(rgh, 0.55, shoulder)
    height = nb.add(nb.mul(nb.sub(scr, 0.5), 0.000010), nb.mul(nb.sub(haze, 0.5), nb.mul(nb.one_minus(hag), 0.000018)))
    normal = nb.bump_m(height)
    return nb.finish(base, rgh, nb.lerp(1.0, 0.4, shoulder), normal, mask=(0.0, hag, 0.0), ao_dist=0.01)


def mat_alloy(name, color, rough=0.28, patina=(0.05, 0.045, 0.04), patina_amount=0.4, pattern=None,
              metal=1.0, wear_color=None, scale=1.0, oxide=None, oxide_amount=0.0):
    """Non-ferrous fittings: gold foil (kinkise), copper (suaka), brass,
    bronze and shakudō, with cavity patina, an optional oxide mottle and
    surface pattern: ``nekogaki`` (the crossing diagonal file marks of a
    habaki), ``filemarks`` (straight file strokes), ``nanako`` granulation,
    ``cast`` (casting skin, pits and flash) or ``brushed_x``."""
    nb = NB(name)
    o = nb.obj()
    cav = nb.cavity(0.003 * scale)
    edge = nb.edge(0.0008 * scale, 5.0)
    var = nb.noise(o, 220.0 / scale, 4.0, 0.6)
    base = nb.hsv(nb.rgb(color), v=nb.add(0.92, nb.mul(var, 0.16)))
    pmask = nb.clamp01(nb.mul(nb.add(cav, nb.mul(nb.sub(nb.noise(o, 70.0 / scale, 3.0), 0.5), 0.6)), patina_amount * 1.8))
    base = nb.mixc(pmask, base, nb.rgb(patina))
    omask = 0.0
    if oxide is not None:
        omask = nb.clamp01(nb.mul(nb.add(nb.smoothstep(nb.noise(o, 30.0 / scale, 4.0, 0.6, 0.4), 0.42, 0.72),
                                         nb.mul(cav, 0.8)), oxide_amount))
        base = nb.mixc(omask, base, nb.rgb(oxide))
    if wear_color is not None:
        base = nb.mixc(nb.mul(edge, 0.8), base, nb.rgb(wear_color))
    rgh = nb.add(rough, nb.mul(nb.sub(var, 0.5), 0.08))
    rgh = nb.lerp(rgh, min(rough + 0.30, 0.9), pmask)
    if oxide is not None:
        rgh = nb.lerp(rgh, min(rough + 0.2, 0.8), omask)
    rgh = nb.lerp(rgh, max(rough - 0.1, 0.08), nb.mul(edge, 0.6))
    mtl = nb.lerp(metal, 0.3, nb.mul(pmask, 0.7))
    height = nb.mul(nb.sub(var, 0.5), 0.000070 * scale)
    x, y, z = nb.vxyz(o)
    if pattern in ("nekogaki", "filemarks"):
        # Crossing diagonal file strokes (neko-gaki) or one straight set.
        wob = nb.mul(nb.sub(nb.noise(o, 300.0, 2.0), 0.5), 0.0012)
        u1 = nb.add(nb.add(nb.mul(x, 0.87), nb.mul(nb.add(y, z), 0.5)), wob)
        g1 = nb.m("FRACT", nb.div(u1, 0.00075))
        height = nb.add(height, nb.mul(g1, 0.000032))
        if pattern == "nekogaki":
            u2 = nb.add(nb.sub(nb.mul(x, 0.82), nb.mul(nb.add(y, z), 0.57)), wob)
            g2 = nb.m("FRACT", nb.div(u2, 0.0011))
            height = nb.add(height, nb.mul(g2, 0.000020))
            # The file strokes catch light as fine bright/dark hatching.
            base = nb.hsv(base, v=nb.add(0.90, nb.mul(nb.add(g1, g2), 0.10)))
        rgh = nb.add(rgh, nb.mul(nb.sub(g1, 0.5), 0.06))
    elif pattern == "nanako":
        vor = nb.voronoi(o, 1.0 / (0.00075 * scale), "F1", 0.35)
        dome = nb.one_minus(nb.remap(vor.outputs["Distance"], 0.0, 0.55))
        height = nb.add(height, nb.mul(nb.pow(dome, 0.5), 0.00009))
    elif pattern == "cast":
        # Sand-cast skin: a fine granular relief (the mould sand), shrinkage
        # pits and a slow undulation; the grain dulls the skin a little.
        # Grain sized to survive the bake (a texel is ~0.3 mm): ~1 mm sand
        # relief and 0.5-1 mm porosity pits.
        sand = nb.noise(o, 900.0 / scale, 2.0, 0.55)
        height = nb.add(height, _pits(nb, o, 0.0032 * scale, 0.00008, 0.26))
        height = nb.add(height, nb.mul(nb.sub(nb.noise(o, 120.0 / scale, 3.0, 0.6), 0.5), 0.00010))
        height = nb.add(height, nb.mul(nb.sub(sand, 0.5), 0.000075))
        rgh = nb.add(rgh, nb.mul(nb.sub(sand, 0.5), 0.10))
    elif pattern == "brushed_x":
        lines = nb.noise(nb.vmul(o, (8.0, 750.0, 750.0)), 1.0, 2.0, 0.5)
        height = nb.add(height, nb.mul(lines, 0.000045))
        rgh = nb.add(rgh, nb.mul(nb.sub(lines, 0.5), 0.08))
    normal = nb.bump_m(height)
    ao_extra = nb.one_minus(nb.mul(cav, 0.3))
    return nb.finish(base, rgh, mtl, normal, mask=(0.0, edge, cav), ao_dist=0.015, ao_extra=ao_extra)


def mat_urushi(name, color, rough=0.12, undercoat=(0.18, 0.035, 0.02), wear=0.3, ishime=0.0,
               grain_through=0.0, scale=1.0, axis="X", rubs=(), crackle=0.0):
    """Urushi lacquer over wood: brush strokes and orange-peel levelling, the
    wood grain telegraphing through the coats (the lacquer sinks into the
    pores as it cures), polishing haze, sparse knocks and fine scratches of
    use, and an original wear mask (edges, rubbed patches) exposing the
    undercoat. ``rubs`` are zones [(x0, x1)] along object X where hands
    have rubbed through to the undercoat (negoro wear); ``crackle`` adds the
    fine craquelure (danmon) of old lacquer, cells elongated along the part."""
    nb = NB(name)
    o = nb.obj()
    edge = nb.edge(0.0018 * scale, 4.0)
    wn = nb.noise(o, 140.0 / scale, 5.0, 0.65, 0.4)
    wear_mask = nb.clamp01(nb.mul(nb.sub(nb.add(nb.mul(edge, 1.2), nb.mul(wn, 0.9)), 1.05), 3.5 * wear))
    rub = nb.mul(nb.smoothstep(nb.noise(o, 12.0 / scale, 3.0, 0.5), 0.62, 0.78), nb.smoothstep(wn, 0.45, 0.6))
    wear_mask = nb.maxi(wear_mask, nb.mul(rub, wear * 0.8))
    if rubs:
        # Worn through where hands rub: crisp-edged patches that grow from the
        # zone's centre, plus pin chips, down to the undercoat.
        x, _y, _z = nb.vxyz(o)
        zone = nb.zones(x, rubs, 0.04)
        n1 = nb.noise(o, 55.0 / scale, 6.0, 0.7, 0.35)
        thr = nb.sub(0.655, nb.mul(zone, 0.075))
        patchy = nb.smoothstep(n1, thr, nb.add(thr, 0.025))
        speck = nb.smoothstep(nb.noise(o, 420.0 / scale, 3.0, 0.6), 0.72, 0.75)
        wear_mask = nb.maxi(wear_mask, nb.clamp01(nb.mul(zone, nb.add(patchy, nb.mul(speck, 0.7)))))
    peel = nb.noise(o, 250.0 / scale, 2.0, 0.5)
    along = {"X": (40.0, 1100.0, 1100.0), "Z": (1100.0, 1100.0, 40.0), "Y": (1100.0, 40.0, 1100.0)}[axis]
    brush = nb.noise(nb.vmul(o, along), 1.0, 3.0, 0.55)
    haze = nb.noise(nb.vmul(o, (40.0, 900.0, 900.0)), 1.0, 2.0, 0.5)
    base = nb.hsv(nb.rgb(color), v=nb.add(0.96, nb.mul(nb.noise(o, 25.0 / scale, 2.0), 0.08)))
    # The wood grain under the coats telegraphs through as a faint relief.
    gvec = nb.vmul(o, (1.0 / 1.13, 1.0 / 0.07, 1.0 / 0.07)) if axis == "X" else nb.vmul(o, (1.0 / 0.07, 1.0 / 0.07, 1.0 / 1.13))
    wood = nb.img(library("cedar_grainU_albedo" if axis == "X" else "cedar_grain_albedo"), gvec, box=True)
    grain_h = nb.bw(wood.outputs["Color"])
    if grain_through:
        base = nb.mixc(grain_through, base, nb.mulc(wood.outputs["Color"], nb.rgb(color)))
    base = nb.mixc(wear_mask, base, nb.rgb(undercoat))
    dust = nb.smoothstep(nb.noise(o, 400.0 / scale, 3.0, 0.6), 0.6, 0.8)
    # Knocks (small dents) and fine scratches of handling.
    kv = nb.voronoi(o, 1.0 / (0.007 * scale), "F1", 1.0)
    knock = nb.mul(nb.one_minus(nb.smoothstep(kv.outputs["Distance"], 0.0, 0.22)),
                   nb.smoothstep(nb.sep(kv.outputs["Color"])[0], 0.80, 0.83))
    scr = nb.noise(nb.vmul(o, (260.0, 2400.0, 1400.0)), 1.0, 2.0, 0.5, 0.6)
    scratch = nb.one_minus(nb.smoothstep(nb.absf(nb.sub(scr, 0.5)), 0.0, 0.02))
    rgh = nb.add(rough, nb.mul(nb.sub(haze, 0.5), 0.05))
    rgh = nb.lerp(rgh, rough + 0.2, nb.mul(dust, 0.4))
    rgh = nb.lerp(rgh, rough + 0.12, nb.mul(scratch, 0.5))
    rgh = nb.lerp(rgh, 0.45, wear_mask)
    # Perlin noise has a standard deviation of ~0.1, so these multipliers
    # give ~5 um of orange peel, ~4 um of brush (hake-me) ridges and the
    # grain telegraphing a few microns through the coats.
    height = nb.add(nb.mul(nb.sub(peel, 0.5), 0.000080), nb.mul(nb.sub(brush, 0.5), 0.000075))
    height = nb.add(height, nb.mul(grain_h, 0.000080))
    height = nb.sub(height, nb.mul(wear_mask, 0.000018))
    height = nb.sub(height, nb.add(nb.mul(knock, 0.000030), nb.mul(scratch, 0.000004)))
    if ishime:
        vor = nb.voronoi(o, 1800.0 / scale, "F1", 1.0)
        height = nb.add(height, nb.mul(vor.outputs["Distance"], 0.00006 * ishime))
        rgh = nb.add(rgh, ishime * 0.15)
    if crackle:
        stretch = (0.40, 1.0, 1.0) if axis == "X" else ((1.0, 1.0, 0.40) if axis == "Z" else (1.0, 0.40, 1.0))
        cv = nb.voronoi(nb.vmul(o, stretch), 1.0 / (0.0030 * scale), "DISTANCE_TO_EDGE", 1.0)
        crack = nb.mul(nb.one_minus(nb.smoothstep(cv.outputs["Distance"], 0.0, 0.14)),
                       nb.smoothstep(nb.noise(o, 20.0 / scale, 3.0, 0.6), 0.35, 0.55))
        crack = nb.mul(crack, crackle)
        height = nb.sub(height, nb.mul(crack, 0.000040))
        rgh = nb.add(rgh, nb.mul(crack, 0.10))
        base = nb.mixc(nb.mul(crack, 0.45), base, nb.mulc(base, nb.rgb((0.35, 0.33, 0.32))))
    normal = nb.bump_m(height)
    return nb.finish(base, rgh, 0.0, normal, mask=(0.0, wear_mask, 0.0), ao_dist=0.02)


def mat_wrapped_lacquer(name, color, pitch=0.0024, rough=0.35, wear=0.3, undercoat=(0.10, 0.07, 0.04),
                        perimeter=0.105):
    """千段巻/籐巻: a fine cord wound on a helix (UVMetric u along the part, v
    round it), lacquered: the pitch wanders with the hand that wound it,
    lacquer pools and levels in the grooves between turns, and the crowns
    wear through to the brown undercoat. Dielectric (metal 0)."""
    nb = NB(name)
    uvv = nb.uv("UVMetric")
    u, v, _ = nb.vxyz(uvv)
    j1 = nb.noise1(nb.mul(u, 22.0), 2.0)
    j2 = nb.noise1(nb.add(nb.mul(u, 97.0), 4.0), 2.0)
    phase = nb.add(nb.add(nb.div(u, pitch), nb.div(v, perimeter)),
                   nb.add(nb.mul(nb.sub(j1, 0.5), 1.8), nb.mul(nb.sub(j2, 0.5), 0.35)))
    f = nb.m("FRACT", phase)
    crown = nb.pow(nb.sin(nb.mul(f, math.pi)), 0.5)
    pool = 0.42
    pooled = nb.one_minus(nb.smoothstep(crown, pool - 0.05, pool + 0.12))
    h = nb.m("SMOOTH_MAX", crown, pool, 0.08)
    o = nb.obj()
    edge = nb.edge(0.0015, 3.0)
    wn = nb.noise(o, 120.0, 4.0, 0.6)
    wear_mask = nb.clamp01(nb.mul(nb.sub(nb.add(nb.mul(crown, 0.6), nb.add(nb.mul(edge, 0.5), nb.mul(wn, 0.6))), 1.05),
                                  4.0 * wear))
    col = nb.hsv(nb.rgb(color), v=nb.add(0.9, nb.mul(nb.noise(o, 60.0, 2.0), 0.2)))
    col = nb.mixc(wear_mask, col, nb.rgb(undercoat))
    col = nb.hsv(col, v=nb.add(0.85, nb.mul(crown, 0.25)))
    col = nb.mixc(nb.mul(pooled, 0.5), col, nb.mulc(nb.rgb(color), nb.rgb((0.7, 0.7, 0.7))))
    rgh = nb.lerp(nb.add(rough, nb.mul(nb.sub(wn, 0.5), 0.06)), 0.18, pooled)
    rgh = nb.lerp(rgh, 0.5, wear_mask)
    normal = nb.bump_m(nb.mul(h, 0.00040))
    ao_extra = nb.add(0.7, nb.mul(crown, 0.3))
    return nb.finish(col, rgh, 0.0, normal, mask=(0.0, wear_mask, nb.one_minus(crown)), ao_dist=0.01,
                     ao_extra=ao_extra)


def mat_braid(name, color, scale=1.0, sheen=0.5, rough=0.60, kind="flat", soil=0.0):
    """Flat silk or cotton braid (tsuka-ito, sageo) or round cord, following
    UVMetric: u runs along the ribbon, v across it. The chevron strands are
    original and carry ~0.2 mm of relief; ``soil`` darkens handled fibres."""
    nb = NB(name)
    uvv = nb.uv("UVMetric")
    u, v, _ = nb.vxyz(uvv)
    pitch = 0.0016 * scale
    if kind == "flat":
        chevron = nb.add(nb.div(u, pitch), nb.div(nb.absf(nb.sub(nb.m("FRACT", nb.div(v, 0.0058 * scale)), 0.5)),
                                                    0.45))
    else:
        chevron = nb.add(nb.div(u, pitch), nb.div(v, 0.004 * scale))
    strand = nb.m("FRACT", chevron)
    ridge = nb.sin(nb.mul(strand, math.pi))
    fibre = nb.noise(nb.xyz(nb.mul(u, 30.0), nb.mul(v, 900.0), 0.0), 1.0, 3.0, 0.6)
    fabric = nb.img(cc0("polyhaven", "crepe_satin", "crepe_satin_nor_dx_2k.exr"),
                    nb.vmul(uvv, 1.0 / 0.05), "Non-Color")
    col = nb.hsv(nb.rgb(color), v=nb.add(0.72, nb.mul(ridge, 0.45)))
    col = nb.hsv(col, v=nb.add(0.9, nb.mul(fibre, 0.2)))
    cav = nb.cavity(0.0025)
    col = nb.mixc(nb.mul(cav, 0.6), col, nb.mulc(col, nb.rgb((0.3, 0.3, 0.3))))
    if soil:
        o = nb.obj()
        dirt = nb.clamp01(nb.mul(nb.smoothstep(nb.noise(o, 40.0, 3.0, 0.6), 0.4, 0.7), soil))
        col = nb.mixc(dirt, col, nb.mulc(col, nb.rgb((0.62, 0.56, 0.48))))
    rgh = nb.add(rough, nb.mul(nb.sub(ridge, 0.5), -0.10))
    nrm = nb.nmap_dx(fabric.outputs["Color"], 0.35)
    normal = nb.bump_m(nb.add(nb.mul(ridge, 0.00022 * scale), nb.mul(fibre, 0.00003)), nrm)
    ao_extra = nb.add(0.65, nb.mul(ridge, 0.35))
    return nb.finish(col, rgh, 0.0, normal, mask=(0.0, 0.0, cav), ao_dist=0.01, ao_extra=ao_extra)


def mat_samegawa(name, color=(0.50, 0.47, 0.40), lacquer=None, scale=1.0, oyatsubu=None):
    """Ray skin: Poisson-like scattered hemispherical nodules 0.4-1.2 mm
    across (Voronoi cells at full randomness, each dome sized by its cell),
    ivory with grey value variation and grime between the nodules; the
    ``oyatsubu`` (x, y, z, radius) is the large king nodule placed under the
    omote menuki. Kuro-same (``lacquer``): black lacquer filled then polished
    back so only the nodule crowns show white."""
    nb = NB(name)
    o = nb.obj()
    cell = 0.00085 * scale
    vor = nb.voronoi(o, 1.0 / cell, "F1", 1.0)
    rnd = nb.sep(vor.outputs["Color"])
    r_m = nb.add(0.00020 * scale, nb.mul(rnd[0], 0.00040 * scale))       # dome radius 0.2-0.6 mm
    dist_m = nb.mul(vor.outputs["Distance"], cell)
    ratio = nb.clamp01(nb.div(dist_m, r_m))
    dome = nb.m("SQRT", nb.one_minus(nb.mul(ratio, ratio)))
    h = nb.mul(dome, nb.mul(r_m, 0.55))
    hn = nb.div(h, 0.00033 * scale)                                        # ~0..1
    if oyatsubu is not None:
        ox, oy, oz, orad = oyatsubu
        dv = nb.node("ShaderNodeVectorMath", operation="DISTANCE")
        nb.feed(dv.inputs[0], o)
        nb.feed(dv.inputs[1], (ox, oy, oz))
        big = nb.m("SQRT", nb.one_minus(nb.clamp01(nb.pow(nb.div(dv.outputs["Value"], orad), 2.0))))
        h = nb.maxi(h, nb.mul(big, orad * 0.35))
        hn = nb.maxi(hn, big)
    tone = nb.noise(o, 90.0 / scale, 3.0, 0.5)
    grey = nb.noise(o, 18.0 / scale, 2.0, 0.5)
    col = nb.hsv(nb.rgb(color), s=nb.add(0.75, nb.mul(grey, 0.5)),
                 v=nb.add(0.62, nb.add(nb.mul(hn, 0.34), nb.mul(tone, 0.12))))
    col = nb.mixc(nb.mul(nb.one_minus(hn), 0.45), col, nb.mulc(col, nb.rgb((0.55, 0.52, 0.47))))
    if lacquer is not None:
        col = nb.mixc(nb.smoothstep(hn, 0.80, 0.95), nb.rgb(lacquer), col)
        rgh = nb.lerp(0.18, 0.30, nb.smoothstep(hn, 0.8, 0.95))
    else:
        rgh = nb.lerp(0.58, 0.34, hn)
    normal = nb.bump_m(h)
    ao_extra = nb.add(0.55, nb.mul(hn, 0.45))
    return nb.finish(col, rgh, 0.0, normal, mask=(0.0, 0.0, nb.one_minus(hn)), ao_dist=0.01, ao_extra=ao_extra)


_LIB_CACHE = {}


def library(key: str) -> Path:
    """Derived CC0 textures cached under Saved/RuntimeWeaponBuild/Library.

    ``cedar_grain_*``: Poly Haven japanese_cedar_planks (4K scan, 113 cm tile)
    with the plank seams removed: single planks are cut at the detected seam
    columns, tone-matched and cross-faded side by side (wrapping), giving a
    seamless straight-grain board. The hardwood materials use only its grain
    structure (luminance and normal) and set the colour themselves."""
    if key in _LIB_CACHE:
        return _LIB_CACHE[key]
    out_dir = CACHE / "Library"
    out_dir.mkdir(parents=True, exist_ok=True)
    base = key.rsplit("_", 1)[0]
    if base in ("cedar_grain", "cedar_grainU"):
        paths = {f"{o}_{k}": out_dir / f"{o}_{k}.png" for o in ("cedar_grain", "cedar_grainU")
                 for k in ("albedo", "normal", "rough")}
        src_diff = cc0("polyhaven", "japanese_cedar_planks", "japanese_cedar_planks_diff_4k.jpg")
        src_nrm = cc0("polyhaven", "japanese_cedar_planks", "japanese_cedar_planks_nor_dx_4k.exr")
        src_arm = cc0("polyhaven", "japanese_cedar_planks", "japanese_cedar_planks_arm_4k.exr")
        if not all(p.is_file() for p in paths.values()):
            _build_cedar_grain(src_diff, src_nrm, src_arm, paths)
        _LIB_CACHE.update(paths)
        return _LIB_CACHE[key]
    raise KeyError(key)


def _img_np(path, colorspace):
    img = bpy.data.images.load(str(path), check_existing=False)
    img.colorspace_settings.name = colorspace
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    return px.reshape(h, w, 4)


def _save_np(arr, path, colorspace="Non-Color", is_srgb_encoded=False):
    h, w = arr.shape[:2]
    img = bpy.data.images.new(path.stem, w, h, alpha=False, float_buffer=False)
    img.colorspace_settings.name = colorspace
    rgba = np.ones((h, w, 4), dtype=np.float32)
    rgba[..., :3] = np.clip(arr[..., :3], 0.0, 1.0)
    img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw = str(path)
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


def _build_cedar_grain(src_diff, src_nrm, src_arm, paths):
    diff = _img_np(src_diff, "Non-Color")[..., :3]  # keep sRGB-encoded values
    nrm = _img_np(src_nrm, "Non-Color")[..., :3]
    arm = _img_np(src_arm, "Non-Color")[..., :3]
    h, w, _ = diff.shape
    lum = diff.mean(axis=2)
    col = lum.mean(axis=0)
    kernel = np.ones(61) / 61.0
    trend = np.convolve(np.pad(col, 30, mode="wrap"), kernel, mode="valid")
    detr = col - trend
    thr = detr.mean() - 1.3 * detr.std()
    seams = [i for i in range(1, w - 1) if detr[i] < thr and detr[i] <= detr[i - 1] and detr[i] <= detr[i + 1]]
    merged = []
    for s in seams:
        if not merged or s - merged[-1] > 40:
            merged.append(s)
    bounds = merged + [merged[0] + w] if merged else [0, w]
    planks = []
    for a, b in zip(bounds[:-1], bounds[1:]):
        if b - a > 180:
            planks.append((a + 18, b - 18))
    target = diff.reshape(-1, 3).mean(axis=0)
    strips_d, strips_n, strips_a = [], [], []
    for a, b in planks:
        cols = np.arange(a, b) % w
        d = diff[:, cols, :]
        d = d * (target / np.maximum(d.reshape(-1, 3).mean(axis=0), 1e-4))
        strips_d.append(d)
        strips_n.append(nrm[:, cols, :])
        strips_a.append(arm[:, cols, :])
    fade = 48
    out_d = strips_d[0]
    out_n = strips_n[0]
    out_a = strips_a[0]
    ramp = np.linspace(0.0, 1.0, fade)[None, :, None]
    for d, n_, a_ in zip(strips_d[1:], strips_n[1:], strips_a[1:]):
        out_d = np.concatenate([out_d[:, :-fade], out_d[:, -fade:] * (1 - ramp) + d[:, :fade] * ramp, d[:, fade:]], 1)
        out_n = np.concatenate([out_n[:, :-fade], out_n[:, -fade:] * (1 - ramp) + n_[:, :fade] * ramp, n_[:, fade:]], 1)
        out_a = np.concatenate([out_a[:, :-fade], out_a[:, -fade:] * (1 - ramp) + a_[:, :fade] * ramp, a_[:, fade:]], 1)
    # Wrap: blend the tail into the head so the board tiles across.
    for arr_name in ("d", "n", "a"):
        arr = {"d": out_d, "n": out_n, "a": out_a}[arr_name]
        head = arr[:, :fade].copy()
        arr[:, :fade] = arr[:, -fade:] * (1 - ramp) + head * ramp
        arr = arr[:, :-fade]
        if arr_name == "d":
            out_d = arr
        elif arr_name == "n":
            out_n = arr
        else:
            out_a = arr
    # Resample to 2048 x 2048 (width covers the stitched planks, height the tile).
    def resample(arr, size=2048):
        hh, ww, _ = arr.shape
        yi = (np.arange(size) * hh / size).astype(int)
        xi = (np.arange(size) * ww / size).astype(int)
        return arr[yi][:, xi]
    # Flatten the remaining plank-to-plank tone steps: divide by a wide
    # column-wise mean (keeps the grain, removes the board-level banding).
    colmean = out_d.mean(axis=0)
    k = 301
    padded = np.pad(colmean, ((k // 2, k // 2), (0, 0)), mode="wrap")
    smooth = np.stack([np.convolve(padded[:, c], np.ones(k) / k, mode="valid") for c in range(3)], axis=1)
    out_d = out_d * (out_d.reshape(-1, 3).mean(axis=0) / np.maximum(smooth, 1e-4))[None, :, :]
    out_d, out_n, out_a = resample(out_d), resample(out_n), resample(out_a)
    rough = np.repeat(out_a[..., 1:2], 3, axis=2)
    _save_np(out_d, paths["cedar_grain_albedo"])
    _save_np(out_n, paths["cedar_grain_normal"])
    _save_np(rough, paths["cedar_grain_rough"])
    # Grain along image u (rows <-> columns). A DirectX normal's tangent-space
    # x and y swap as well: new x = old y flipped to the DirectX convention.
    rot_n = np.transpose(out_n, (1, 0, 2)).copy()
    nx, ny = rot_n[..., 0].copy(), rot_n[..., 1].copy()
    rot_n[..., 0] = 1.0 - ny
    rot_n[..., 1] = 1.0 - nx
    _save_np(np.transpose(out_d, (1, 0, 2)), paths["cedar_grainU_albedo"])
    _save_np(rot_n, paths["cedar_grainU_normal"])
    _save_np(np.transpose(rough, (1, 0, 2)), paths["cedar_grainU_rough"])
    meta = {"source": [rel(src_diff), rel(src_nrm), rel(src_arm)], "planks": planks, "seams": merged,
            "stitched_width_px_4k": int(sum(b - a for a, b in planks) - fade * len(planks)),
            "tile_height_m": 1.13}
    (paths["cedar_grain_albedo"].parent / "cedar_grain.json").write_text(json.dumps(meta, indent=1))


def cedar_meta():
    library("cedar_grain_albedo")
    path = CACHE / "Library" / "cedar_grain.json"
    meta = json.loads(path.read_text())
    if "mean_luminance_linear" not in meta:
        px = _img_np(library("cedar_grain_albedo"), "Non-Color")[..., :3]
        lin = np.where(px <= 0.04045, px / 12.92, ((px + 0.055) / 1.055) ** 2.4)
        lum = lin[..., 0] * 0.2126 + lin[..., 1] * 0.7152 + lin[..., 2] * 0.0722
        meta["mean_luminance_linear"] = float(lum.mean())
        path.write_text(json.dumps(meta, indent=1))
    return meta


# Target mean colours (sRGB 0-255) of the hardwoods. The cedar scan supplies
# only the grain; the tone is set here. Kashi (Japanese evergreen oak): grey-
# to red-brown near the judged #5A3F2C, kept low in blue so it never reads
# pink under a warm key; stock: dark red-brown oak or cherry as found under
# the urushi of gun stocks; smoked: soot-darkened oak.
WOOD_TONES = {
    "kashi": (92, 66, 46),
    "kashi_red": (98, 64, 44),
    "stock": (72, 44, 30),
    "smoked": (60, 46, 34),
    "cherry": (92, 54, 36),
}


def mat_wood(name, tone="kashi", contrast=0.55, rough=(0.45, 0.7), mapping="uv", axis="X",
             lacquer=0.0, wear=0.25, dirt=0.35, grips=(), rays=0.8, tool=0.0, value=1.0, iron_bleed=0.0):
    """Hardwood: the grain of the seamless CC0 cedar board re-toned to a
    measured mean colour (``WOOD_TONES``), with oak ray fleck (short
    glossy flecks along the grain), vessel pores, heartwood tone drift,
    optional plane/chisel facets (``tool``) and urushi (``lacquer``).
    ``grips`` are handled zones [(x0, x1)] along object X: sweat-darkened,
    greasy-smooth and grimy. ``mapping='uv'`` follows UVMetric (u along a
    lofted part); ``'box'`` projects along ``axis`` ('X' or 'Z').
    ``iron_bleed`` stains the wood round driven iron (studs, bands, nails):
    the blue-black of iron tannate in oak with a rust-brown ring next to the
    metal, found from the local occlusion the iron parts cast on the joined
    bake mesh."""
    nb = NB(name)
    meta = cedar_meta()
    width_m = 1.13 * meta["stitched_width_px_4k"] / 4096.0
    height_m = 1.13
    o = nb.obj()
    x, y, z = nb.vxyz(o)
    if mapping == "uv":
        u, v, _ = nb.vxyz(nb.uv("UVMetric"))
        vec = nb.xyz(nb.div(u, height_m), nb.div(v, width_m), 0.0)
        box, lib = False, "cedar_grainU"
    else:
        if axis == "X":
            vec = nb.xyz(nb.div(x, height_m), nb.div(y, width_m), nb.div(z, width_m))
            lib = "cedar_grainU"
        else:
            vec = nb.xyz(nb.div(x, width_m), nb.div(y, width_m), nb.div(z, height_m))
            lib = "cedar_grain"
        box = True
    alb = nb.img(library(f"{lib}_albedo"), vec, "sRGB", box=box, blend=0.35)
    nrm_t = nb.img(library(f"{lib}_normal"), vec, "Non-Color", box=box, blend=0.35)
    rgh_t = nb.img(library(f"{lib}_rough"), vec, "Non-Color", box=box, blend=0.35)
    lum = nb.div(nb.bw(alb.outputs["Color"]), meta["mean_luminance_linear"])
    g = nb.pow(nb.maxi(lum, 0.05), contrast)
    tone_lin = srgb(*WOOD_TONES[tone])
    tone_lin = tuple(c * value for c in tone_lin)
    heart = nb.noise(o, 1.6, 2.0, 0.5)
    tone_c = nb.mixc(nb.smoothstep(heart, 0.4, 0.7), nb.rgb(tone_lin),
                     nb.rgb((tone_lin[0] * 1.08, tone_lin[1] * 0.93, tone_lin[2] * 0.86)))
    col = nb.hsv(tone_c, v=g)
    # Ray fleck and pores: stretched along the grain axis.
    if mapping == "uv" or axis == "X":
        fl_vec = nb.vmul(o, (1.0 / 0.009, 1.0 / 0.0009, 1.0 / 0.0009))
        po_vec = nb.vmul(o, (1.0 / 0.004, 1.0 / 0.0012, 1.0 / 0.0012))
        tl_vec = nb.vmul(o, (1.0 / 0.08, 1.0 / 0.007, 1.0 / 0.007))
    else:
        fl_vec = nb.vmul(o, (1.0 / 0.0009, 1.0 / 0.0009, 1.0 / 0.009))
        po_vec = nb.vmul(o, (1.0 / 0.0012, 1.0 / 0.0012, 1.0 / 0.004))
        tl_vec = nb.vmul(o, (1.0 / 0.007, 1.0 / 0.007, 1.0 / 0.08))
    fl = nb.voronoi(fl_vec, 1.0, "F1", 1.0)
    fleck = nb.mul(nb.one_minus(nb.smoothstep(fl.outputs["Distance"], 0.0, 0.22)),
                   nb.smoothstep(nb.sep(fl.outputs["Color"])[0], 0.55, 0.6))
    fleck = nb.mul(fleck, rays)
    col = nb.mixc(nb.mul(fleck, 0.45), col, nb.hsv(col, s=0.8, v=1.25))
    po = nb.voronoi(po_vec, 1.0, "F1", 1.0)
    pore = nb.mul(nb.one_minus(nb.smoothstep(po.outputs["Distance"], 0.0, 0.42)),
                  nb.smoothstep(nb.sep(po.outputs["Color"])[1], 0.5, 0.55))
    col = nb.mixc(nb.mul(pore, 0.35), col, nb.mulc(col, nb.rgb((0.55, 0.5, 0.45))))
    cav = nb.cavity(0.004)
    edge = nb.edge(0.0015, 4.0)
    grime = nb.clamp01(nb.mul(nb.add(cav, nb.mul(nb.sub(nb.noise(o, 50.0, 3.0), 0.5), 0.5)), dirt * 2.0))
    col = nb.mixc(grime, col, nb.mulc(col, nb.rgb((0.40, 0.36, 0.32))))
    polish = nb.mul(edge, wear)
    col = nb.mixc(polish, col, nb.hsv(col, v=1.15))
    grip = 0.0
    if grips:
        grip = nb.mul(nb.zones(x, grips, 0.025),
                      nb.add(0.75, nb.mul(nb.noise(o, 30.0, 3.0, 0.6), 0.5)))
        grip = nb.clamp01(grip)
        col = nb.mixc(grip, col, nb.hsv(nb.mulc(col, nb.rgb((0.60, 0.55, 0.50))), s=0.9))
    stain = 0.0
    if iron_bleed:
        ao = nb.node("ShaderNodeAmbientOcclusion", samples=24, inside=False, only_local=True)
        nb.feed(ao.inputs["Distance"], 0.030)
        prox = nb.one_minus(ao.outputs["AO"])
        brk = nb.add(0.45, nb.mul(nb.noise(o, 70.0, 4.0, 0.65, 0.4), 1.1))
        stain = nb.clamp01(nb.mul(nb.mul(nb.smoothstep(prox, 0.004, 0.060), brk), iron_bleed))
        ring = nb.clamp01(nb.mul(nb.mul(nb.smoothstep(prox, 0.07, 0.22), brk), iron_bleed))
        col = nb.mixc(nb.mul(stain, 0.85), col, nb.mulc(col, nb.rgb((0.26, 0.26, 0.29))))
        col = nb.mixc(nb.mul(ring, 0.75), col, nb.rgb((0.085, 0.040, 0.018)))
    r_base = nb.remap(nb.sep(rgh_t.outputs["Color"])[0], 0.0, 1.0, rough[0], rough[1])
    r_base = nb.lerp(r_base, nb.mul(r_base, 0.75), nb.mul(fleck, 1.0 - lacquer))
    if iron_bleed:
        r_base = nb.lerp(r_base, nb.add(r_base, 0.12), stain)
    if lacquer:
        # Old shunkei/urushi over wood: a satin gloss, not a mirror (a mirror
        # over the grain relief sparkles).
        r_base = nb.lerp(r_base, nb.maxi(nb.mul(r_base, 0.5), 0.22), lacquer)
    r_base = nb.lerp(r_base, nb.mul(r_base, 0.7), polish)
    if grips:
        # Handled wood is burnished and greasy, but satin (a mirror over the
        # grain relief would sparkle).
        r_base = nb.lerp(r_base, nb.maxi(nb.mul(r_base, 0.72), 0.32), grip)
    # The scan is rough-sawn cedar: planed hardwood carries only part of its
    # relief, lacquer levels most of the rest and handling polishes it.
    if not box:
        n_str = 0.65 * (1.0 - 0.85 * lacquer)
        if grips:
            n_str = nb.mul(nb.one_minus(nb.mul(grip, 0.6)), n_str)
        nrm = nb.nmap_dx(nrm_t.outputs["Color"], n_str)
    else:
        nrm = None
    relief = nb.mul(nb.sub(g, 1.0), -0.000035)               # soft earlywood worn below the latewood
    relief = nb.add(relief, nb.mul(fleck, 0.000012))
    # Lacquer fills the pores and levels the latewood ridges.
    relief = nb.add(relief, nb.mul(pore, -0.000016 * (1.0 - 0.85 * lacquer)))
    if tool:
        relief = nb.add(relief, nb.mul(nb.noise(tl_vec, 1.0, 2.0, 0.5), 0.00012 * tool))
    if grips:
        relief = nb.mul(relief, nb.one_minus(nb.mul(grip, 0.6)))
    if lacquer:
        relief = nb.mul(relief, 1.0 - 0.75 * lacquer)
    if iron_bleed:
        # The wood swells and checks round driven iron.
        relief = nb.add(relief, nb.mul(stain, nb.mul(nb.noise(o, 400.0, 3.0, 0.6), 0.00004)))
    normal = nb.bump_m(relief, nrm)
    ao_extra = nb.one_minus(nb.mul(nb.add(cav, nb.mul(pore, 0.5)), 0.3))
    grime_mask = nb.maxi(grime, stain) if iron_bleed else grime
    return nb.finish(col, r_base, 0.0, normal, mask=(0.0, nb.maxi(polish, grip) if grips else polish, grime_mask),
                     ao_dist=0.03, ao_extra=ao_extra)


def mat_scan(name, folder, stem, kind="ambientcg", tint=(1, 1, 1), sat=1.0, value=1.0, tile=0.3,
             rough_scale=1.0, rough_bias=0.0, uv="box", normal_strength=1.0, metal=0.0, cavity_dark=0.4,
             soil=0.0, height_m=0.0):
    """A tiled CC0 scan (ambientCG or Poly Haven), re-toned; ``soil`` adds
    handling grime patches, ``height_m`` adds relief from the scan's own
    luminance on top of its normal map."""
    nb = NB(name)
    if uv == "box":
        vec = nb.vmul(nb.obj(), 1.0 / tile)
    else:
        vec = nb.vmul(nb.uv("UVMetric"), 1.0 / tile)
    box = uv == "box"
    if kind == "ambientcg":
        col_t = nb.img(cc0("ambientcg", folder, f"{stem}_2K-JPG_Color.jpg"), vec, "sRGB", box)
        nrm_t = nb.img(cc0("ambientcg", folder, f"{stem}_2K-JPG_NormalDX.jpg"), vec, "Non-Color", box)
        rgh_t = nb.img(cc0("ambientcg", folder, f"{stem}_2K-JPG_Roughness.jpg"), vec, "Non-Color", box)
        r = nb.sep(rgh_t.outputs["Color"])[0]
    else:
        col_t = nb.img(cc0("polyhaven", folder, f"{stem}_diff_2k.jpg"), vec, "sRGB", box)
        nrm_t = nb.img(cc0("polyhaven", folder, f"{stem}_nor_dx_2k.exr"), vec, "Non-Color", box)
        arm_t = nb.img(cc0("polyhaven", folder, f"{stem}_arm_2k.exr"), vec, "Non-Color", box)
        r = nb.sep(arm_t.outputs["Color"])[1]
    col = nb.mulc(nb.hsv(col_t.outputs["Color"], s=sat, v=value), nb.rgb(tint))
    cav = nb.cavity(0.004)
    col = nb.mixc(nb.mul(cav, cavity_dark), col, nb.mulc(col, nb.rgb((0.25, 0.22, 0.2))))
    o = nb.obj()
    if soil:
        dirt = nb.clamp01(nb.mul(nb.add(nb.smoothstep(nb.noise(o, 25.0, 3.0, 0.6), 0.45, 0.7), nb.mul(cav, 0.6)),
                                 soil))
        col = nb.mixc(dirt, col, nb.mulc(col, nb.rgb((0.58, 0.50, 0.40))))
    rgh = nb.clamp01(nb.add(nb.mul(r, rough_scale), rough_bias))
    nrm = nb.nmap_dx(nrm_t.outputs["Color"], normal_strength, "UVMetric")
    if height_m:
        nrm = nb.bump_m(nb.mul(nb.bw(col_t.outputs["Color"]), height_m), nrm)
    ao_extra = nb.one_minus(nb.mul(cav, 0.3))
    return nb.finish(col, rgh, metal, nrm, mask=(0.0, 0.0, cav), ao_dist=0.02, ao_extra=ao_extra)


def mat_horn(name, color=(0.020, 0.016, 0.013), rough=0.2):
    nb = NB(name)
    o = nb.obj()
    streak = nb.noise(nb.vmul(o, (25.0, 400.0, 150.0)), 1.0, 4.0, 0.6, 0.7)
    col = nb.mixc(nb.remap(streak, 0.45, 0.75), nb.rgb(color), nb.rgb((0.07, 0.045, 0.028)))
    edge = nb.edge(0.001, 4.0)
    rgh = nb.lerp(rough, rough - 0.06, edge)
    fib = nb.noise(nb.vmul(o, (60.0, 1500.0, 900.0)), 1.0, 3.0, 0.6)
    normal = nb.bump_m(nb.add(nb.mul(streak, 0.00006), nb.mul(fib, 0.00004)))
    return nb.finish(col, rgh, 0.0, normal, mask=(0.0, edge, 0.0), ao_dist=0.015)


def mat_bamboo(name, color=(0.42, 0.30, 0.13), smoked=0.0, rough=0.38, axis="X", lacquer=0.0, nodes=(),
               tube=None):
    """Bamboo culm: waxy skin with fine longitudinal fibre and mottling
    (original procedural). ``nodes`` (positions along ``axis``) darken the
    node bands with their sheath scars; ``tube`` (cy, cz, r_bore) marks the
    cut end grain (vascular dots) and the pale inner skin of a hollow culm
    about an X axis."""
    nb = NB(name)
    o = nb.obj()
    x, y, z = nb.vxyz(o)
    sc = {"X": (6.0, 1800.0, 1800.0), "Z": (1800.0, 1800.0, 6.0), "Y": (1800.0, 6.0, 1800.0)}[axis]
    fib = nb.noise(nb.vmul(o, tuple(s * 0.45 if s > 100 else s for s in sc)), 1.0, 5.0, 0.6, 0.2)
    mott = nb.noise(nb.vmul(o, tuple(s / 60 for s in sc)), 1.0, 3.0, 0.5, 0.5)
    col = nb.hsv(nb.rgb(color), v=nb.add(0.8, nb.add(nb.mul(fib, 0.22), nb.mul(mott, 0.25))))
    if smoked:
        col = nb.mixc(nb.mul(nb.remap(mott, 0.3, 0.7), smoked), col, nb.rgb((0.07, 0.035, 0.015)))
    ax = {"X": x, "Y": y, "Z": z}[axis]
    height = nb.mul(nb.sub(fib, 0.5), 0.000090)
    height = nb.add(height, nb.mul(nb.sub(mott, 0.5), 0.00010))
    if nodes:
        band = nb.zones(ax, [(p - 0.004, p + 0.004) for p in nodes], 0.006)
        scar = nb.zones(ax, [(p - 0.0012, p + 0.0012) for p in nodes], 0.001)
        col = nb.mixc(nb.mul(band, 0.45), col, nb.mulc(col, nb.rgb((0.62, 0.55, 0.45))))
        col = nb.mixc(nb.mul(scar, 0.7), col, nb.rgb((0.06, 0.045, 0.03)))
        height = nb.sub(height, nb.mul(scar, 0.00012))
    cav = nb.cavity(0.003)
    col = nb.mixc(nb.mul(cav, 0.5), col, nb.mulc(col, nb.rgb((0.3, 0.25, 0.2))))
    rgh = nb.add(rough, nb.mul(nb.sub(fib, 0.5), 0.1))
    if lacquer:
        rgh = nb.lerp(rgh, 0.15, lacquer)
    if tube is not None:
        cy, cz, r_bore = tube
        g = nb.geo()
        nx, ny, nz = nb.vxyz(g.outputs["Normal"])
        radial = nb.node("ShaderNodeVectorMath", operation="NORMALIZE")
        nb.feed(radial.inputs[0], nb.xyz(0.0, nb.sub(y, cy), nb.sub(z, cz)))
        dotn = nb.node("ShaderNodeVectorMath", operation="DOT_PRODUCT")
        nb.feed(dotn.inputs[0], radial.outputs[0])
        nb.feed(dotn.inputs[1], g.outputs["Normal"])
        inner = nb.smoothstep(nb.mul(dotn.outputs["Value"], -1.0), 0.4, 0.7)
        end = nb.smoothstep(nb.absf(nx), 0.75, 0.9)
        dots = nb.voronoi(o, 1.0 / 0.0011, "F1", 1.0)
        vasc = nb.one_minus(nb.smoothstep(dots.outputs["Distance"], 0.0, 0.3))
        rr = nb.m("SQRT", nb.add(nb.mul(nb.sub(y, cy), nb.sub(y, cy)), nb.mul(nb.sub(z, cz), nb.sub(z, cz))))
        dens = nb.smoothstep(rr, r_bore + 0.001, r_bore + 0.009)   # bundles crowd toward the skin
        end_col = nb.mixc(nb.mul(vasc, nb.add(0.3, nb.mul(dens, 0.6))), nb.rgb((0.45, 0.36, 0.22)),
                          nb.rgb((0.16, 0.10, 0.05)))
        col = nb.mixc(end, col, end_col)
        col = nb.mixc(inner, col, nb.rgb((0.52, 0.47, 0.36)))
        rgh = nb.lerp(rgh, 0.75, nb.maxi(end, inner))
        height = nb.add(height, nb.mul(nb.mul(vasc, end), -0.00006))
    normal = nb.bump_m(height)
    ao_extra = nb.one_minus(nb.mul(cav, 0.3))
    return nb.finish(col, rgh, 0.0, normal, mask=(0.0, 0.0, cav), ao_dist=0.01, ao_extra=ao_extra)


def mat_rattan(name, lacquer=(0.012, 0.009, 0.008), skin=(0.42, 0.28, 0.12), lacquer_amount=0.85, wear=0.35):
    """Split rattan strip under urushi (shigetō bindings): the fibres and the
    glossy skin run along the strip (UVMetric u), the lacquer pools at the
    strip edges and wears through to the golden skin on the crowns."""
    nb = NB(name)
    uvv = nb.uv("UVMetric")
    u, v, _ = nb.vxyz(uvv)
    o = nb.obj()
    fib = nb.noise(nb.xyz(nb.mul(u, 35.0), nb.mul(v, 2600.0), 0.0), 1.0, 4.0, 0.6, 0.2)
    node = nb.smoothstep(nb.noise1(nb.mul(u, 9.0), 2.0), 0.72, 0.78)
    edge = nb.edge(0.0006, 5.0)
    wn = nb.noise(o, 180.0, 4.0, 0.6, 0.3)
    worn = nb.clamp01(nb.mul(nb.sub(nb.add(nb.mul(edge, 0.9), nb.mul(wn, 0.8)), 0.95), 4.0 * wear))
    skin_c = nb.hsv(nb.rgb(skin), v=nb.add(0.75, nb.mul(fib, 0.5)))
    skin_c = nb.mixc(nb.mul(node, 0.6), skin_c, nb.mulc(skin_c, nb.rgb((0.55, 0.45, 0.35))))
    lac_c = nb.hsv(nb.rgb(lacquer), v=nb.add(0.9, nb.mul(fib, 0.2)))
    cover = nb.clamp01(nb.sub(lacquer_amount, worn))
    col = nb.mixc(cover, skin_c, lac_c)
    rgh = nb.lerp(nb.add(0.34, nb.mul(fib, 0.1)), nb.add(0.13, nb.mul(wn, 0.05)), cover)
    height = nb.add(nb.mul(nb.sub(fib, 0.5), 0.000020), nb.mul(node, 0.00005))
    height = nb.mul(height, nb.sub(1.0, nb.mul(cover, 0.5)))
    normal = nb.bump_m(height)
    return nb.finish(col, rgh, 0.0, normal, mask=(0.0, worn, 0.0), ao_dist=0.008)


def mat_feather(name, color=(0.24, 0.018, 0.012), bar=(0.07, 0.010, 0.007), rachis=(0.55, 0.50, 0.40)):
    """Fletching vane with fibre and an opacity mask (UVMetric: u along the
    shaft, v out from it; ``vane_h`` per-vertex height of the trimmed vane).
    Dyed hawk feather: the dye over the feather's own wavy natural barring,
    uneven where it took; barbs angled toward the tip with a sheen along
    each barb, clumping and splitting; a pale rachis at the base and a
    ragged trimmed edge in alpha."""
    nb = NB(name)
    uvv = nb.uv("UVMetric")
    u, v, _ = nb.vxyz(uvv)
    vh = nb.attr("vane_h")
    barb_c = nb.add(u, nb.mul(v, 1.05))
    jit = nb.noise1(nb.mul(barb_c, 90.0), 2.0)
    bc = nb.add(nb.div(barb_c, 0.00085), nb.mul(jit, 3.0))
    barb = nb.m("FRACT", bc)
    ridge = nb.sin(nb.mul(barb, math.pi))
    clump = nb.noise1(nb.mul(barb_c, 45.0), 2.0)
    split_n = nb.noise1(nb.mul(barb_c, 160.0), 1.0)
    split = nb.mul(nb.smoothstep(split_n, 0.66, 0.70), nb.smoothstep(v, 0.002, 0.004))
    # Natural barring: wavy chevrons running across the barbs.
    wav = nb.mul(nb.sub(nb.noise1(nb.mul(v, 180.0), 2.0), 0.5), 0.010)
    ph = nb.add(nb.add(u, nb.mul(v, 0.55)), wav)
    bars = nb.smoothstep(nb.add(nb.sin(nb.mul(ph, math.tau / 0.026)), nb.mul(nb.sub(clump, 0.5), 0.8)), 0.15, 0.75)
    dye = nb.add(0.78, nb.mul(nb.noise(nb.xyz(nb.mul(u, 40.0), nb.mul(v, 90.0), 0.0), 1.0, 3.0, 0.6), 0.44))
    col = nb.mixc(nb.mul(bars, 0.8), nb.hsv(nb.rgb(color), v=dye), nb.rgb(bar))
    col = nb.hsv(col, v=nb.add(0.55, nb.mul(ridge, 0.75)))
    tipdark = nb.smoothstep(nb.div(v, nb.maxi(vh, 0.001)), 0.6, 1.0)
    col = nb.mixc(nb.mul(tipdark, 0.35), col, nb.mulc(col, nb.rgb((0.55, 0.5, 0.5))))
    base_zone = nb.one_minus(nb.smoothstep(v, 0.0008, 0.0022))
    col = nb.mixc(base_zone, col, nb.rgb(rachis))
    edge_rag = nb.mul(nb.sub(nb.noise1(nb.mul(u, 700.0), 2.0), 0.5), 0.0016)
    inside = nb.one_minus(nb.smoothstep(v, nb.sub(nb.add(vh, edge_rag), 0.0006), nb.add(vh, edge_rag)))
    alpha = nb.mul(inside, nb.one_minus(nb.mul(split, 0.9)))
    rgh = nb.add(0.58, nb.mul(ridge, -0.22))
    normal = nb.bump_m(nb.add(nb.mul(ridge, 0.00007), nb.mul(split, -0.00004)))
    return nb.finish(col, rgh, 0.0, normal, ao_dist=0.01, alpha=alpha)


def mat_graphite(name, color=(0.036, 0.038, 0.042), rough=0.34, engrave=1.0, ledger=None, scale=1.0,
                 glow=(0.12, 0.85, 1.0)):
    """Alien micro-engraved graphite composite: near-black (albedo ~0.04),
    machined along X with directional micro-grooves that give the
    anisotropic streak of the specular in a baked map (roughness ~0.3), a
    fine hex engraving and polished arrises. ``ledger`` adds emissive
    ledger-line grooves along X (Mask R = emissive)."""
    nb = NB(name)
    o = nb.obj()
    x, y, z = nb.vxyz(o)
    grooves = nb.m("FRACT", nb.div(nb.add(z, nb.mul(nb.sub(nb.noise(o, 80.0, 2.0), 0.5), 0.0008)), 0.0011 * scale))
    grooves = nb.sin(nb.mul(grooves, math.pi))
    hexv = nb.voronoi(nb.vmul(o, (1.0, 1.0, 1.0)), 1.0 / (0.0035 * scale), "DISTANCE_TO_EDGE", 0.0)
    hexl = nb.one_minus(nb.smoothstep(hexv.outputs["Distance"], 0.0, 0.05))
    grain = nb.noise(o, 600.0 / scale, 6.0, 0.7)
    col = nb.hsv(nb.rgb(color), v=nb.add(0.88, nb.mul(grain, 0.24)))
    edge = nb.edge(0.0008 * scale, 5.0)
    col = nb.mixc(nb.mul(edge, 0.5), col, nb.rgb((0.085, 0.088, 0.095)))
    col = nb.mixc(nb.mul(hexl, 0.25 * engrave), col, nb.mulc(col, nb.rgb((0.6, 0.6, 0.62))))
    rgh = nb.add(rough, nb.mul(nb.sub(grooves, 0.5), 0.10 * engrave))
    rgh = nb.lerp(rgh, rough - 0.12, nb.mul(edge, 0.5))
    # Face-milling swirl: shallow arcs of the cutter across the flats.
    sw = nb.voronoi(nb.vmul(o, (1.0, 1.0, 1.0)), 1.0 / (0.018 * scale), "F1", 0.6)
    swirl = nb.sin(nb.mul(nb.div(sw.outputs["Distance"], 0.012), math.tau))
    height = nb.add(nb.mul(grooves, 0.000032 * engrave), nb.mul(hexl, -0.000040 * engrave))
    height = nb.add(height, nb.mul(nb.sub(grain, 0.5), 0.000030))
    height = nb.add(height, nb.mul(swirl, 0.000004))
    emissive = 0.0
    if ledger is not None:
        spacing, width = ledger
        band = nb.m("FRACT", nb.div(z, spacing))
        line = nb.mul(nb.remap(band, 0.5 - width, 0.5 - width * 0.4, smooth=True),
                      nb.one_minus(nb.remap(band, 0.5 + width * 0.4, 0.5 + width, smooth=True)))
        ticks = nb.remap(nb.sin(nb.mul(x, math.tau / 0.006)), 0.2, 0.4)
        emissive = nb.mul(line, nb.maxi(ticks, 0.6))
        col = nb.mixc(emissive, col, nb.rgb((0.02, 0.05, 0.06)))
        height = nb.sub(height, nb.mul(emissive, 0.00004))
    normal = nb.bump_m(height)
    # A resin-bound composite: dielectric (near-black stays black in a bright
    # studio instead of turning into a grey metallic sheen).
    return nb.finish(col, rgh, 0.0, normal, mask=(emissive, edge, 0.0),
                     emission=(glow, 6.0), ao_dist=0.015)


def mat_titanium(name, color=(0.42, 0.40, 0.38), rough=0.36, axis="X"):
    """Bead-blasted then brushed titanium: brush bands coarse enough to
    survive the bake (~1.5 mm), a slow forming undulation, polished arrises."""
    nb = NB(name)
    o = nb.obj()
    sc = {"X": (6.0, 700.0, 700.0), "Z": (700.0, 700.0, 6.0)}[axis]
    lines = nb.noise(nb.vmul(o, sc), 1.0, 3.0, 0.55)
    var = nb.noise(o, 90.0, 3.0)
    col = nb.hsv(nb.rgb(color), v=nb.add(0.92, nb.mul(lines, 0.12)))
    tint = nb.remap(var, 0.3, 0.7)
    col = nb.mixc(nb.mul(tint, 0.25), col, nb.rgb((0.50, 0.46, 0.52)))
    edge = nb.edge(0.0008, 5.0)
    rgh = nb.add(rough, nb.mul(nb.sub(lines, 0.5), 0.14))
    rgh = nb.lerp(rgh, rough - 0.1, nb.mul(edge, 0.6))
    blast = nb.noise(o, 1500.0, 2.0, 0.5)
    normal = nb.bump_m(nb.add(nb.add(nb.mul(lines, 0.000110), nb.mul(nb.sub(var, 0.5), 0.00012)),
                              nb.mul(blast, 0.000060)))
    return nb.finish(col, rgh, 1.0, normal, mask=(0.0, edge, 0.0), ao_dist=0.015)


def mat_black_glass(name, rough=0.022, film=0.25, emissive_rgb=None):
    """Black glass read as depth: a near-black clear-coated body (roughness
    ~0.02) with a faint deep-blue lattice seen through the surface, thin-film
    hue drift, smudges and a very gentle float-glass waviness in the
    normal."""
    nb = NB(name)
    o = nb.obj()
    hue = nb.noise(o, 25.0, 2.0, 0.4)
    col = nb.ramp(hue, [(0.0, (0.006, 0.004, 0.010)), (0.5, (0.003, 0.007, 0.009)),
                        (1.0, (0.008, 0.006, 0.004))])
    col = nb.mixc(1.0 - film, col, nb.rgb((0.004, 0.005, 0.006)))
    lat = nb.voronoi(o, 1.0 / 0.006, "DISTANCE_TO_EDGE", 0.0)
    lattice = nb.one_minus(nb.smoothstep(lat.outputs["Distance"], 0.0, 0.03))
    col = nb.mixc(nb.mul(lattice, 0.6), col, nb.rgb((0.010, 0.022, 0.035)))
    smudge = nb.remap(nb.noise(o, 180.0, 4.0, 0.65), 0.55, 0.75)
    rgh = nb.lerp(rough, rough + 0.10, nb.mul(smudge, 0.5))
    wav = nb.noise(o, 40.0, 2.0, 0.4)
    normal = nb.bump_m(nb.add(nb.mul(wav, 0.000015), nb.mul(smudge, 0.000002)))
    em = 1.0 if emissive_rgb is not None else 0.0
    return nb.finish(col, rgh, 0.0, normal, mask=(em, 0.0, 0.0),
                     emission=(emissive_rgb or (0.1, 0.8, 1.0), 4.0), ao_dist=0.01)


def mat_emissive(name, color=(0.02, 0.05, 0.06), glow=(0.12, 0.85, 1.0), strength=8.0, rough=0.2):
    nb = NB(name)
    o = nb.obj()
    normal = nb.bump_m(nb.mul(nb.noise(o, 300.0, 2.0), 0.00004))
    return nb.finish(nb.rgb(color), rough, 0.0, normal, mask=(1.0, 0.0, 0.0), emission=(glow, strength))


def mat_paper(name, tint=(0.62, 0.56, 0.44), rough=0.8):
    return mat_scan(name, "Fabric001", "Fabric001", tint=tint, sat=0.4, value=1.0, tile=0.2,
                    rough_bias=0.1, normal_strength=1.2, height_m=0.00006)


def mat_cloth(name, tint=(0.8, 0.8, 0.8), tile=0.12, sat=0.0, value=1.0, uv="uv", soil=0.0):
    return mat_scan(name, "rough_linen", "rough_linen", kind="polyhaven", tint=tint, sat=sat, value=value,
                    tile=tile, uv=uv, normal_strength=1.6, soil=soil, height_m=0.00008)


def mat_leather(name, tint=(1.0, 1.0, 1.0), value=1.0, tile=0.25, uv="box", rough_bias=0.0, soil=0.0,
                folder="Leather014"):
    return mat_scan(name, folder, folder, tint=tint, value=value, tile=tile, uv=uv, rough_bias=rough_bias,
                    normal_strength=1.4, soil=soil, height_m=0.00006)


def mat_rope(name, folder="Rope001", tint=(1, 1, 1), tile=0.06, value=1.0, sat=1.0):
    return mat_scan(name, folder, folder, tint=tint, tile=tile, uv="uv", value=value, sat=sat,
                    normal_strength=1.4, cavity_dark=0.6, height_m=0.00008)


def mat_straw_fibre(name, tint=(0.56, 0.45, 0.25)):
    """Loose rice-straw fibres on alpha-masked cards (UVMetric u across the
    card 0..1, v from its root 0..1): a few split blades of straw per card,
    ragged at the tips, golden with grey weathering and darker at the root."""
    nb = NB(name)
    uvv = nb.uv("UVMetric")
    u, v, _ = nb.vxyz(uvv)
    o = nb.obj()
    wob = nb.mul(nb.sub(nb.noise1(nb.add(nb.mul(v, 7.0), nb.mul(u, 3.0)), 2.0), 0.5), 0.8)
    lanes = nb.add(nb.mul(u, 5.0), wob)
    k = nb.m("FRACT", lanes)
    blade = nb.one_minus(nb.smoothstep(nb.absf(nb.sub(k, 0.5)), 0.12, 0.26))
    pick = nb.smoothstep(nb.noise1(nb.add(nb.m("FLOOR", lanes), 3.7), 1.0), 0.38, 0.44)
    tip = nb.one_minus(nb.smoothstep(v, nb.add(0.55, nb.mul(nb.noise1(nb.m("FLOOR", lanes), 1.0), 0.4)), 1.0))
    alpha = nb.mul(nb.mul(blade, nb.maxi(pick, 0.35)), tip)
    shade = nb.noise(nb.vmul(o, (300.0, 300.0, 300.0)), 1.0, 3.0, 0.6)
    col = nb.hsv(nb.rgb(tint), s=nb.add(0.6, nb.mul(shade, 0.5)), v=nb.add(0.65, nb.mul(shade, 0.55)))
    col = nb.mixc(nb.mul(nb.one_minus(nb.smoothstep(v, 0.0, 0.35)), 0.5), col, nb.mulc(col, nb.rgb((0.5, 0.45, 0.4))))
    rgh = nb.add(0.52, nb.mul(shade, 0.12))
    normal = nb.bump_m(nb.mul(nb.sin(nb.mul(k, math.pi)), 0.00003))
    return nb.finish(col, rgh, 0.0, normal, ao_dist=0.006, alpha=alpha)


def mat_straw(name, tint=(1.0, 0.95, 0.85), tile=0.05, value=1.0, sat=0.9):
    """Rice-straw (nawa) fibre from the CC0 ambientCG thatch scan, along the
    ply (UVMetric u)."""
    return mat_scan(name, "ThatchedRoof001A", "ThatchedRoof001A", tint=tint, tile=tile, uv="uv", value=value,
                    sat=sat, normal_strength=1.5, cavity_dark=0.7, rough_bias=0.1, height_m=0.00012)


# ---------------------------------------------------------------------------
# Build pipeline
# ---------------------------------------------------------------------------

class Build:
    def __init__(self, weapon_id, opts):
        self.id = weapon_id
        self.spec = SPECS.WEAPONS[weapon_id]
        self.opts = opts
        self.key = self.spec["key"]
        self.dir = RUNTIME / self.key
        self.dir.mkdir(parents=True, exist_ok=True)
        RENDERS.mkdir(parents=True, exist_ok=True)
        self.res = opts.get("res") or self.spec.get("texture_res", 2048)
        self.groups = {"main": dict(asset=self.spec["asset"], offset=Vector(), origin=Vector(), parts=[])}
        self.sockets = {"main": []}
        self.notes = {}
        self.measure = {}
        self.t0 = time.time()
        self.scene = reset_scene()
        USED_SOURCES.clear()
        REG.clear()

    # registration -------------------------------------------------------
    def group(self, name, asset, offset, origin=(0, 0, 0), lay=True, floor=False):
        """An extra runtime mesh sharing the texture set. ``offset`` separates
        it in the bake; ``lay`` False keeps it as modelled (already lying
        flat, e.g. a coiled chain) in the Estate render; ``floor`` puts the
        studio floor under it in the Neutral render."""
        self.groups[name] = dict(asset=asset, offset=Vector(offset), origin=Vector(origin), parts=[], lay=lay,
                                 floor=floor)
        self.sockets[name] = []

    def add(self, obj, group="main", lod_drop=99):
        obj["rw_group"] = group
        obj["rw_lod_drop"] = lod_drop
        self.groups[group]["parts"].append(obj)
        link_to(obj, collection(SOURCE_COLL))
        return obj

    def socket(self, name, loc, x=(1, 0, 0), z=(0, 0, 1), group="main"):
        xa = Vector(x).normalized()
        za = Vector(z)
        za = (za - xa * za.dot(xa)).normalized()
        ya = za.cross(xa)
        m = Matrix((xa, ya, za)).transposed().to_4x4()
        m.translation = Vector(loc)
        self.sockets[group].append((name, m))

    # pipeline -------------------------------------------------------------
    def finalize(self):
        self.log("parts", sum(len(g["parts"]) for g in self.groups.values()))
        for gname, g in self.groups.items():
            if not g["parts"]:
                raise RuntimeError(f"group {gname} has no parts")
        names = {s[0] for s in self.sockets["main"]}
        missing = set(SPECS.SOCKETS) - names
        if missing:
            raise RuntimeError(f"{self.key}: missing sockets {sorted(missing)}")
        self.unwrap_parts()
        bake_obj = self.build_bake_mesh()
        self.pack_uv0(bake_obj)
        if not self.opts.get("no_bake"):
            self.bake(bake_obj)
            self.final_material(bake_obj)
        exports = self.split_and_export(bake_obj)
        self.save_blend()
        if not self.opts.get("no_render"):
            self.render(exports)
        self.write_record(exports)
        self.log("done", f"{time.time() - self.t0:.1f}s")

    def log(self, *args):
        print(f"[{self.key}]", *args, flush=True)

    def unwrap_parts(self):
        for g in self.groups.values():
            for obj in g["parts"]:
                ensure_uv_layers(obj.data)
                mesh = obj.data
                gi = list(self.groups).index(obj["rw_group"])
                for aname, val in (("rw_group", gi), ("rw_lod_drop", obj["rw_lod_drop"])):
                    attr = mesh.attributes.get(aname) or mesh.attributes.new(aname, "INT", "FACE")
                    attr.data.foreach_set("value", [int(val)] * len(mesh.polygons))
                if obj.get("rw_needs_unwrap", True):
                    mesh.uv_layers.active = mesh.uv_layers["UV0"]
                    deselect_all()
                    obj.select_set(True)
                    bpy.context.view_layer.objects.active = obj
                    bpy.ops.object.mode_set(mode="EDIT")
                    bpy.ops.mesh.select_all(action="SELECT")
                    bpy.ops.uv.smart_project(angle_limit=math.radians(52.0), island_margin=0.0,
                                             area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
                    bpy.ops.object.mode_set(mode="OBJECT")
                    obj["rw_needs_unwrap"] = False

    def build_bake_mesh(self):
        copies = []
        for gname, g in self.groups.items():
            for obj in g["parts"]:
                c = obj.copy()
                c.data = obj.data.copy()
                collection("RW_Bake").objects.link(c)
                c.data.transform(Matrix.Translation(g["offset"]))
                copies.append(c)
        bake = join(copies, f"{self.spec['asset']}_Bake")
        mesh = bake.data
        # Triangulate once so the baked tangent frame is the exported one.
        mod = bake.modifiers.new("RW_Tri", "TRIANGULATE")
        mod.quad_method = "BEAUTY"
        mod.ngon_method = "BEAUTY"
        mod.keep_custom_normals = True
        apply_modifiers(bake)
        mod = bake.modifiers.new("RW_WN", "WEIGHTED_NORMAL")
        mod.keep_sharp = True
        mod.weight = 50
        mod.mode = "FACE_AREA"
        apply_modifiers(bake)
        for p in [o for g in self.groups.values() for o in g["parts"]]:
            p.hide_render = True
            p.hide_set(True)
        self.log("bake mesh tris", len(bake.data.polygons))
        return bake

    def pack_uv0(self, obj):
        mesh = obj.data
        mesh.uv_layers.active = mesh.uv_layers["UV0"]
        deselect_all()
        obj.hide_set(False)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        margin = 10.0 / self.res
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.select_all(action="SELECT")
        bpy.ops.uv.average_islands_scale(scale_uv=False, shear=False)
        # Convex hulls, 90-degree rotations and an added margin keep packing
        # fast for weapons with hundreds of small islands.
        bpy.ops.uv.pack_islands(udim_source="CLOSEST_UDIM", rotate=True, rotate_method="CARDINAL", scale=True,
                                merge_overlap=False, margin_method="ADD", margin=margin,
                                shape_method="CONVEX")
        bpy.ops.object.mode_set(mode="OBJECT")
        uv = np.empty(len(mesh.loops) * 2)
        mesh.uv_layers["UV0"].data.foreach_get("uv", uv)
        uv = uv.reshape(-1, 2)
        if uv.min() < -1e-5 or uv.max() > 1 + 1e-5:
            raise RuntimeError(f"UV0 outside 0..1: {uv.min()} {uv.max()}")
        self.texel = texel_density(mesh, "UV0", self.res)
        self.log("texel density px/m", {k: round(v, 1) for k, v in self.texel.items()})

    # baking ---------------------------------------------------------------
    def bake(self, obj):
        scene = self.scene
        scene.render.engine = "CYCLES"
        scene.render.bake.margin = 12
        scene.render.bake.margin_type = "EXTEND"
        scene.render.bake.use_clear = True
        deselect_all()
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        res = self.res
        mats = [slot.material for slot in obj.material_slots if slot.material]
        has_alpha = any(REG[m.name].get("alpha") is not None for m in mats)
        keys = ("BaseColor", "ORM", "Mask", "Normal") + (("Alpha",) if has_alpha else ())
        images = {}
        for key in keys:
            img = bpy.data.images.new(f"RWBake_{key}", res, res, alpha=False, float_buffer=True)
            img.colorspace_settings.name = "Non-Color"
            images[key] = img
        tex_nodes = {}
        for mat in mats:
            n = mat.node_tree.nodes.new("ShaderNodeTexImage")
            n.name = "RW_BakeTarget"
            tex_nodes[mat.name] = n
            mat.node_tree.nodes.active = n
        passes = [("BaseColor", "EMIT", 8), ("ORM", "EMIT", 64), ("Mask", "EMIT", 8), ("Normal", "NORMAL", 16)]
        if has_alpha:
            passes.append(("Alpha", "EMIT", 8))
        for key, kind, samples in passes:
            scene.cycles.samples = samples
            for mat in mats:
                tex_nodes[mat.name].image = images[key]
                mat.node_tree.nodes.active = tex_nodes[mat.name]
                self._route(mat, key)
            t = time.time()
            if kind == "NORMAL":
                bpy.ops.object.bake(type="NORMAL", normal_space="TANGENT", normal_r="POS_X", normal_g="NEG_Y",
                                    normal_b="POS_Z", margin=12, margin_type="EXTEND", use_clear=True,
                                    uv_layer="UV0")
            else:
                bpy.ops.object.bake(type="EMIT", margin=12, margin_type="EXTEND", use_clear=True, uv_layer="UV0")
            self.log("baked", key, f"{time.time() - t:.1f}s")
        for mat in mats:
            self._route(mat, None)
            mat.node_tree.nodes.remove(tex_nodes[mat.name])
        # Write 8-bit PNGs (BaseColor carries the opacity mask in A when a
        # material has one).
        self.textures = {}
        alpha_px = None
        if has_alpha:
            ap = np.empty(res * res * 4, dtype=np.float32)
            images["Alpha"].pixels.foreach_get(ap)
            alpha_px = np.clip(ap.reshape(res, res, 4)[..., 0], 0.0, 1.0)
            bpy.data.images.remove(images.pop("Alpha"))
        for key, img in images.items():
            px = np.empty(res * res * 4, dtype=np.float32)
            img.pixels.foreach_get(px)
            px = px.reshape(res, res, 4)[..., :3]
            if key == "BaseColor":
                px = np.where(px <= 0.0031308, px * 12.92, 1.055 * np.power(np.clip(px, 0, None), 1 / 2.4) - 0.055)
            if key == "Normal":
                n = px * 2.0 - 1.0
                tilt = np.sqrt(n[..., 0] ** 2 + n[..., 1] ** 2)
                self.micro = {"normal_tilt_mean_all_texels": round(float(tilt.mean()), 4),
                              "normal_tilt_p90_all_texels": round(float(np.percentile(tilt, 90)), 4),
                              "by_material": self._tilt_by_material(obj, tilt, mats)}
                self.log("normal tilt", self.micro)
            name = f"T_{self.spec['asset'].replace('SM_', '')}_{key if key != 'Normal' else 'NormalDX'}"
            path = self.dir / f"{name}.png"
            with_a = key == "BaseColor" and alpha_px is not None
            out = bpy.data.images.new(name, res, res, alpha=with_a, float_buffer=False)
            out.colorspace_settings.name = "sRGB" if key == "BaseColor" else "Non-Color"
            rgba = np.ones((res, res, 4), dtype=np.float32)
            rgba[..., :3] = np.clip(px, 0.0, 1.0)
            if with_a:
                rgba[..., 3] = alpha_px
            out.pixels.foreach_set(rgba.ravel())
            save_png_max(out, path, rgba, with_a)
            bpy.data.images.remove(out)
            bpy.data.images.remove(img)
            self.textures[key] = path
            self.log("wrote", rel(path))
        self.has_alpha = has_alpha

    def _tilt_by_material(self, obj, tilt, mats):
        """Area-weighted mean tangent tilt per authoring material, sampled at
        each face's UV0 centroid (a diagnostic for the microsurface floor)."""
        me = obj.data
        res = tilt.shape[0]
        uv = np.empty(len(me.loops) * 2)
        me.uv_layers["UV0"].data.foreach_get("uv", uv)
        uv = uv.reshape(-1, 2)
        starts = np.empty(len(me.polygons), dtype=np.int64)
        totals = np.empty(len(me.polygons), dtype=np.int64)
        mat_idx = np.empty(len(me.polygons), dtype=np.int64)
        area = np.empty(len(me.polygons))
        me.polygons.foreach_get("loop_start", starts)
        me.polygons.foreach_get("loop_total", totals)
        me.polygons.foreach_get("material_index", mat_idx)
        me.polygons.foreach_get("area", area)
        cu = np.array([uv[s:s + t].mean(axis=0) for s, t in zip(starts, totals)])
        ix = np.clip((cu[:, 0] * res).astype(int), 0, res - 1)
        iy = np.clip((cu[:, 1] * res).astype(int), 0, res - 1)
        t = tilt[iy, ix]
        names = [slot.material.name if slot.material else "" for slot in obj.material_slots]
        out = {}
        for mi in np.unique(mat_idx):
            sel = mat_idx == mi
            w = area[sel].sum()
            if w <= 0 or mi >= len(names):
                continue
            out[names[mi]] = {"tilt": round(float((t[sel] * area[sel]).sum() / w), 4),
                              "area_m2": round(float(w), 5)}
        return out

    def _route(self, mat, key):
        reg = REG[mat.name]
        nt = mat.node_tree
        out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        for n in [n for n in nt.nodes if n.name.startswith("RW_Route")]:
            nt.nodes.remove(n)
        if key is None or key == "Normal":
            nt.links.new(bsdf.outputs[0], out.inputs["Surface"])
            return
        em = nt.nodes.new("ShaderNodeEmission")
        em.name = "RW_Route_Emission"
        em.inputs["Strength"].default_value = 1.0
        if key == "BaseColor":
            nt.links.new(reg["base"], em.inputs["Color"])
        elif key == "Alpha":
            if reg.get("alpha") is not None:
                nt.links.new(reg["alpha"], em.inputs["Color"])
            else:
                em.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
        else:
            comb = nt.nodes.new("ShaderNodeCombineColor")
            comb.name = "RW_Route_Combine"
            if key == "ORM":
                ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
                ao.name = "RW_Route_AO"
                ao.samples = 16
                ao.inputs["Distance"].default_value = reg["ao_dist"]
                if reg["normal"] is not None:
                    nt.links.new(reg["normal"], ao.inputs["Normal"])
                if reg.get("ao_extra") is not None:
                    mul = nt.nodes.new("ShaderNodeMath")
                    mul.name = "RW_Route_AOx"
                    mul.operation = "MULTIPLY"
                    mul.use_clamp = True
                    nt.links.new(ao.outputs["AO"], mul.inputs[0])
                    nt.links.new(reg["ao_extra"], mul.inputs[1])
                    nt.links.new(mul.outputs[0], comb.inputs[0])
                else:
                    nt.links.new(ao.outputs["AO"], comb.inputs[0])
                nt.links.new(reg["rough"], comb.inputs[1])
                nt.links.new(reg["metal"], comb.inputs[2])
            else:
                for i in range(3):
                    nt.links.new(reg["mask"][i], comb.inputs[i])
            nt.links.new(comb.outputs[0], em.inputs["Color"])
        nt.links.new(em.outputs[0], out.inputs["Surface"])

    def final_material(self, obj):
        name = f"M_{self.spec['asset'].replace('SM_', '')}"
        mat = bpy.data.materials.new(name)
        if mat.node_tree is None:
            mat.use_nodes = True
        nt = mat.node_tree
        nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        nt.links.new(bsdf.outputs[0], out.inputs["Surface"])
        uvn = nt.nodes.new("ShaderNodeUVMap")
        uvn.uv_map = "UV0"

        def tex(key, cs):
            n = nt.nodes.new("ShaderNodeTexImage")
            n.image = bpy.data.images.load(str(self.textures[key]), check_existing=True)
            n.image.colorspace_settings.name = cs
            n.interpolation = "Cubic"
            nt.links.new(uvn.outputs[0], n.inputs["Vector"])
            return n

        bc = tex("BaseColor", "sRGB")
        orm = tex("ORM", "Non-Color")
        nrm = tex("Normal", "Non-Color")
        msk = tex("Mask", "Non-Color")
        nt.links.new(bc.outputs["Color"], bsdf.inputs["Base Color"])
        if getattr(self, "has_alpha", False):
            bc.image.alpha_mode = "STRAIGHT"
            nt.links.new(bc.outputs["Alpha"], bsdf.inputs["Alpha"])
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(orm.outputs["Color"], sep.inputs[0])
        nt.links.new(sep.outputs[1], bsdf.inputs["Roughness"])
        nt.links.new(sep.outputs[2], bsdf.inputs["Metallic"])
        sepn = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(nrm.outputs["Color"], sepn.inputs[0])
        inv = nt.nodes.new("ShaderNodeMath")
        inv.operation = "SUBTRACT"
        inv.inputs[0].default_value = 1.0
        nt.links.new(sepn.outputs[1], inv.inputs[1])
        comb = nt.nodes.new("ShaderNodeCombineColor")
        nt.links.new(sepn.outputs[0], comb.inputs[0])
        nt.links.new(inv.outputs[0], comb.inputs[1])
        nt.links.new(sepn.outputs[2], comb.inputs[2])
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.uv_map = "UV0"
        nt.links.new(comb.outputs[0], nm.inputs["Color"])
        nt.links.new(nm.outputs[0], bsdf.inputs["Normal"])
        emission = next((r["emission"] for r in REG.values() if r.get("emission")), None)
        seps = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(msk.outputs["Color"], seps.inputs[0])
        if emission is not None:
            col, strength = emission
            bsdf.inputs["Emission Color"].default_value = (*col, 1.0)
            mul = nt.nodes.new("ShaderNodeMath")
            mul.operation = "MULTIPLY"
            mul.inputs[1].default_value = strength
            mul.name = "RW_EmissionStrength"
            nt.links.new(seps.outputs[0], mul.inputs[0])
            nt.links.new(mul.outputs[0], bsdf.inputs["Emission Strength"])
        self.final_mat = mat
        obj.data.materials.clear()
        obj.data.materials.append(mat)
        for poly in obj.data.polygons:
            poly.material_index = 0

    # export -----------------------------------------------------------------
    def split_and_export(self, bake):
        mesh = bake.data
        gattr = np.empty(len(mesh.polygons), dtype=np.int32)
        mesh.attributes["rw_group"].data.foreach_get("value", gattr)
        exports = {}
        coll = collection("RW_Export")
        for gi, (gname, g) in enumerate(self.groups.items()):
            lods = []
            for lod, ratio in enumerate(SPECS.LOD_RATIOS):
                obj = bake.copy()
                obj.data = bake.data.copy()
                coll.objects.link(obj)
                bm = bmesh.new()
                bm.from_mesh(obj.data)
                glayer = bm.faces.layers.int.get("rw_group")
                llayer = bm.faces.layers.int.get("rw_lod_drop")
                kill = [f for f in bm.faces if f[glayer] != gi or (lod > 0 and f[llayer] <= lod)]
                bmesh.ops.delete(bm, geom=kill, context="FACES")
                bm.to_mesh(obj.data)
                bm.free()
                obj.data.transform(Matrix.Translation(-g["offset"] - g["origin"]))
                name = g["asset"] if lod == 0 else f"{g['asset']}_LOD{lod}"
                obj.name = name
                obj.data.name = name
                for aname in ("rw_group", "rw_lod_drop", "hamon_s", "hamon_d", "blade_w", "blade_zone", "vane_h",
                              "bev_d"):
                    if aname in obj.data.attributes:
                        obj.data.attributes.remove(obj.data.attributes[aname])
                if lod > 0:
                    target = int(len(lods[0].data.polygons) * ratio)
                    cur = len(obj.data.polygons)
                    if cur > target:
                        mod = obj.modifiers.new("RW_Decimate", "DECIMATE")
                        mod.decimate_type = "COLLAPSE"
                        mod.ratio = target / cur
                        mod.use_collapse_triangulate = True
                        apply_modifiers(obj)
                    if obj.data.has_custom_normals:
                        with bpy.context.temp_override(object=obj, active_object=obj):
                            bpy.ops.mesh.customdata_custom_splitnormals_clear()
                    finish_shading(obj, True, 40.0)
                obj.hide_render = True
                lods.append(obj)
            # Sockets on LOD0.
            empties = []
            for sname, m in self.sockets[gname]:
                e = bpy.data.objects.new(f"SOCKET_{sname}", None)
                e.empty_display_type = "ARROWS"
                e.empty_display_size = 0.03
                coll.objects.link(e)
                mm = m.copy()
                mm.translation = mm.translation - g["origin"]
                e.parent = lods[0]
                e.matrix_parent_inverse = Matrix.Identity(4)
                e.matrix_basis = mm
                empties.append(e)
            files = []
            for lod, obj in enumerate(lods):
                path = self.dir / f"{obj.name}.fbx"
                deselect_all()
                obj.select_set(True)
                if lod == 0:
                    for e in empties:
                        e.select_set(True)
                bpy.context.view_layer.objects.active = obj
                bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, object_types={"MESH", "EMPTY"},
                                         apply_unit_scale=True, apply_scale_options="FBX_SCALE_NONE",
                                         global_scale=1.0, axis_forward="-Y", axis_up="Z",
                                         mesh_smooth_type="FACE", use_tspace=True, use_triangles=True,
                                         use_mesh_modifiers=True, add_leaf_bones=False, bake_anim=False,
                                         path_mode="STRIP", embed_textures=False, use_custom_props=False)
                files.append(path)
                self.log("exported", rel(path), len(obj.data.polygons), "tris")
            exports[gname] = dict(lods=lods, files=files, empties=empties)
        bpy.data.objects.remove(bake, do_unlink=True)
        return exports

    def save_blend(self):
        path = self.dir / f"{self.spec['asset']}.blend"
        for img in bpy.data.images:
            if img.filepath and not img.packed_file:
                img.filepath = bpy.path.abspath(img.filepath)
        bpy.ops.wm.save_as_mainfile(filepath=str(path), compress=True, relative_remap=False)
        bpy.ops.file.make_paths_relative()
        bpy.ops.wm.save_mainfile(compress=True)
        self.blend = path
        self.log("saved", rel(path))

    # rendering --------------------------------------------------------------
    def render(self, exports):
        render_weapon(self, exports)

    def write_record(self, exports):
        rec = {
            "id": self.id, "key": self.key, "ja": self.spec["ja"], "en": self.spec["en"],
            "faction": self.spec["faction"], "builder": self.spec["builder"], "library": "scripts/art/create_runtime_weapon_lib.py",
            "units": "metres in Blender; FBX exported with apply_unit_scale (Unreal imports centimetres)",
            "axes": "+X line of action, +Z up, +Y wielder's left (Unreal: -Y)",
            "origin": self.spec.get("origin", "Grip_R"),
            "texture_res": self.res,
            "texel_density_px_per_m": getattr(self, "texel", {}),
            "notes": self.notes,
            "assets": {},
            "sources": sorted(USED_SOURCES),
        }
        for gname, ex in exports.items():
            lods = ex["lods"]
            dims = lods[0].dimensions
            rec["assets"][self.groups[gname]["asset"]] = {
                "lods": [{"file": rel(p), "triangles": len(o.data.polygons), "sha256": sha256(p)}
                         for o, p in zip(lods, ex["files"])],
                "bounds_m": [round(dims.x, 5), round(dims.y, 5), round(dims.z, 5)],
                "sockets": {e.name[len("SOCKET_"):]: [round(c, 5) for c in e.matrix_basis.translation]
                            for e in ex["empties"]},
                "screen_sizes": list(SPECS.LOD_SCREEN_SIZES),
            }
        glows = []
        for mname, reg in REG.items():
            if reg.get("emission"):
                col, strength = reg["emission"]
                hexs = "#" + "".join(f"{round(255 * (c * 12.92 if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055)):02X}"
                                     for c in col)
                glows.append({"material": mname, "linear_rgb": [round(c, 4) for c in col], "srgb_hex": hexs,
                              "strength": strength})
        if glows:
            rec["emissive"] = {"mask": "Mask R", "glows": glows,
                               "note": self.notes.get("glow", "League glows are warm; only alien arms are cyan")}
        if hasattr(self, "textures"):
            rec["textures"] = {k: {"file": rel(p), "sha256": sha256(p)} for k, p in self.textures.items()}
            rec["material"] = {
                "name": self.final_mat.name,
                "BaseColor": "sRGB" + (", A = opacity mask (masked blend)" if getattr(self, "has_alpha", False) else ""),
                "NormalDX": "tangent, DirectX (green down), MikkTSpace from the exported mesh",
                "ORM": "R ambient occlusion, G roughness, B metallic",
                "Mask": "R hamon / emissive, G lacquer-or-edge wear, B cavity dirt",
            }
            if hasattr(self, "micro"):
                rec["microsurface"] = self.micro
        if hasattr(self, "blend"):
            rec["blend"] = {"file": rel(self.blend), "sha256": sha256(self.blend)}
        if hasattr(self, "render_files"):
            rec["renders"] = [rel(p) for p in self.render_files]
        (self.dir / "build_record.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1) + "\n",
                                                   encoding="utf-8")


def save_png_max(img, path, expected_rgba, with_alpha=False):
    """Write an 8-bit PNG at maximum zlib compression (the lane is short of
    disk), then verify the file holds exactly the intended bytes; fall back
    to Image.save() if a colour transform slipped in."""
    scene = bpy.context.scene
    vs = scene.view_settings
    saved = (vs.view_transform, vs.look, vs.exposure, vs.gamma)
    vs.view_transform, vs.look, vs.exposure, vs.gamma = "Standard", "None", 0.0, 1.0
    st = scene.render.image_settings
    st.file_format, st.color_mode, st.color_depth, st.compression = "PNG", "RGBA" if with_alpha else "RGB", "8", 100
    img.save_render(str(path), scene=scene)
    vs.view_transform, vs.look, vs.exposure, vs.gamma = saved
    chk = bpy.data.images.load(str(path), check_existing=False)
    chk.colorspace_settings.name = img.colorspace_settings.name
    w, h = chk.size
    got = np.empty(w * h * 4, dtype=np.float32)
    chk.pixels.foreach_get(got)
    bpy.data.images.remove(chk)
    ch = 4 if with_alpha else 3
    diff = float(np.abs(got.reshape(h, w, 4)[..., :ch] - np.round(expected_rgba[..., :ch] * 255) / 255).max())
    if diff > 1.5 / 255:
        img.filepath_raw = str(path)
        img.file_format = "PNG"
        img.save()


def texel_density(mesh, layer, res):
    """Area-weighted px/m per material-free mesh: overall and 5th percentile."""
    co = np.empty(len(mesh.vertices) * 3)
    mesh.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    loops_v = np.empty(len(mesh.loops), dtype=np.int64)
    mesh.loops.foreach_get("vertex_index", loops_v)
    uv = np.empty(len(mesh.loops) * 2)
    mesh.uv_layers[layer].data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    starts = np.empty(len(mesh.polygons), dtype=np.int64)
    mesh.polygons.foreach_get("loop_start", starts)
    tri = np.stack([starts, starts + 1, starts + 2], axis=1)
    p = co[loops_v[tri]]
    a3 = 0.5 * np.linalg.norm(np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0]), axis=1)
    t = uv[tri]
    a2 = 0.5 * np.abs((t[:, 1, 0] - t[:, 0, 0]) * (t[:, 2, 1] - t[:, 0, 1]) -
                      (t[:, 2, 0] - t[:, 0, 0]) * (t[:, 1, 1] - t[:, 0, 1]))
    ok = a3 > 1e-12
    dens = res * np.sqrt(a2[ok] / a3[ok])
    w = a3[ok]
    order = np.argsort(dens)
    cum = np.cumsum(w[order]) / w.sum()
    p5 = dens[order][np.searchsorted(cum, 0.05)]
    return {"mean": float(res * math.sqrt(a2.sum() / a3.sum())), "p05": float(p5),
            "uv_coverage": float(a2.sum())}


# ---------------------------------------------------------------------------
# Renders: 1 m camera, neutral studio and Estate overcast sky
# ---------------------------------------------------------------------------

def _look_at(cam, target):
    d = Vector(target) - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def _world_neutral(scene):
    w = bpy.data.worlds.new("RW_Neutral")
    nt = w.node_tree
    bg = nt.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.18, 0.18, 0.18, 1.0)
    bg.inputs["Strength"].default_value = 0.25
    return w


def _world_estate(scene):
    w = bpy.data.worlds.new("RW_Estate")
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    env = nt.nodes.new("ShaderNodeTexEnvironment")
    USED_SOURCES.add(rel(ESTATE_HDRI))
    env.image = bpy.data.images.load(str(ESTATE_HDRI), check_existing=True)
    mapping = nt.nodes.new("ShaderNodeMapping")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mapping.inputs["Rotation"].default_value = (0.0, 0.0, math.radians(120.0))
    nt.links.new(tc.outputs["Generated"], mapping.inputs["Vector"])
    nt.links.new(mapping.outputs[0], env.inputs["Vector"])
    nt.links.new(env.outputs[0], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 1.0
    nt.links.new(bg.outputs[0], out.inputs["Surface"])
    return w


# Review renders: the Neutral studio is exposed 0.6 EV under the scene-linear
# default (AgX); both lit renders add reflection cards.
NEUTRAL_EXPOSURE_EV = -0.6


def reflection_cards(coll, focus, cam_loc, normal, dist=1.6, bright=3.0, axis=(1.0, 0.0, 0.0)):
    """Two dark cards and a bright strip about the mirror direction of the
    dominant surface, seen only by glossy rays (not camera, diffuse or
    shadow rays): a stand-in for the eaves, tree line and open sky that a
    featureless overcast dome or studio lacks, so polished steel and
    lacquer show a horizon instead of flat grey. The card boundaries run
    across ``axis`` so the bands sweep along a blade's length."""
    focus = Vector(focus)
    view = (focus - Vector(cam_loc)).normalized()
    n = Vector(normal).normalized()
    r = (view - 2.0 * view.dot(n) * n).normalized()
    k = r.cross(Vector(axis))
    if k.length < 1e-4:
        k = r.orthogonal()
    k.normalize()
    cards = []

    def card(name, deg, size, color, strength):
        d = (Matrix.Rotation(math.radians(deg), 3, k) @ r).normalized()
        bpy.ops.mesh.primitive_plane_add(size=1.0, location=focus + d * dist)
        ob = bpy.context.object
        ob.name = name
        link_to(ob, coll)
        ob.scale = (size[0], size[1], 1.0)
        ob.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        mat = bpy.data.materials.new(name + "_Mat")
        if mat.node_tree is None:
            mat.use_nodes = True
        nt = mat.node_tree
        nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        em = nt.nodes.new("ShaderNodeEmission")
        em.inputs["Color"].default_value = (*color, 1.0)
        em.inputs["Strength"].default_value = strength
        nt.links.new(em.outputs[0], out.inputs["Surface"])
        ob.data.materials.append(mat)
        ob.visible_camera = False
        ob.visible_diffuse = False
        ob.visible_shadow = False
        ob.visible_transmission = False
        ob.visible_volume_scatter = False
        ob.visible_glossy = True
        cards.append(ob)

    card("RW_Card_Eave", 9.0, (2.0, 0.9), (0.030, 0.027, 0.024), 1.0)
    card("RW_Card_Sky", -9.0, (2.2, 0.32), (1.0, 0.99, 0.97), bright)
    card("RW_Card_Trees", -24.0, (2.6, 0.55), (0.012, 0.013, 0.011), 1.0)
    return cards


def render_weapon(build, exports):
    scene = build.scene
    spec = build.spec
    coll = collection("RW_Render")
    shown = []
    shown_groups = []
    # Display copies of every group's LOD0, laid out side by side.
    offsets = build.groups
    for gname, ex in exports.items():
        src = ex["lods"][0]
        disp = src.copy()
        disp.data = src.data
        coll.objects.link(disp)
        disp.hide_render = False
        disp.matrix_world = Matrix.Translation(offsets[gname]["origin"] + offsets[gname].get("display", Vector()))
        shown.append(disp)
        shown_groups.append(offsets[gname])
    for o in list(exports["main"]["lods"]) + [o for ex in exports.values() for o in ex["lods"]]:
        o.hide_render = True
    focus = Vector(spec.get("focus", (0.0, 0.0, 0.0)))
    corners = [o.matrix_world @ Vector(c) for o in shown for c in o.bound_box]
    lo = Vector((min(c.x for c in corners), min(c.y for c in corners), min(c.z for c in corners)))
    hi = Vector((max(c.x for c in corners), max(c.y for c in corners), max(c.z for c in corners)))
    scene.render.engine = "CYCLES"
    scene.cycles.samples = build.opts.get("samples", 160)
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    scene.render.image_settings.compression = 100
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "None"
    files = []
    asset = spec["asset"]

    cam_data = bpy.data.cameras.new("RW_Cam")
    cam = bpy.data.objects.new("RW_Cam", cam_data)
    coll.objects.link(cam)
    scene.camera = cam

    # --- Neutral studio -----------------------------------------------------
    grey = bpy.data.materials.new("RW_StudioGrey")
    grey.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.18, 0.18, 0.18, 1)
    grey.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.8
    floor_z = lo.z - 0.22
    rest = [min((d.matrix_world @ Vector(cn)).z for cn in d.bound_box)
            for d, g in zip(shown, shown_groups) if g.get("floor")]
    if rest:
        floor_z = min(rest) - 0.0004
    bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, floor_z))
    floor = bpy.context.object
    link_to(floor, coll)
    floor.data.materials.append(grey)
    lights = []

    def area(name, loc, energy, size, color, target):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy = energy
        ld.size = size
        ld.color = color
        lo_ = bpy.data.objects.new(name, ld)
        coll.objects.link(lo_)
        lo_.location = loc
        _look_at(lo_, target)
        lights.append(lo_)
        return lo_

    c = (lo + hi) / 2
    area("Key", c + Vector((-0.6, -1.4, 1.3)), 180, 1.4, (1.0, 0.97, 0.93), c)
    area("Fill", c + Vector((1.2, -0.8, 0.4)), 45, 1.8, (0.93, 0.96, 1.0), c)
    area("Rim", c + Vector((0.3, 1.5, 1.0)), 130, 1.0, (1.0, 1.0, 1.0), c)
    scene.world = _world_neutral(scene)
    cam_data.type = "PERSP"
    cam_data.lens = 35.0
    cam_data.sensor_width = 36.0
    direction = Vector((-0.42, -0.78, 0.46)).normalized()
    cam.location = focus + direction * 1.0
    _look_at(cam, focus)
    cards = reflection_cards(coll, focus, cam.location, (0.0, -1.0, 0.25), dist=1.4, bright=2.2)
    scene.view_settings.exposure = NEUTRAL_EXPOSURE_EV
    path = RENDERS / f"{asset}_Neutral_1m.png"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    files.append(path)
    build.log("render", rel(path))

    # Profile plate with a 10 cm ruler (orthographic, neutral light).
    ruler_mat = bpy.data.materials.new("RW_Ruler")
    ruler_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.8, 0.8, 0.78, 1)
    tick_mat = bpy.data.materials.new("RW_RulerTick")
    tick_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.02, 0.02, 0.02, 1)
    ruler_parts = []
    x0 = math.floor(lo.x * 10) / 10
    x1 = math.ceil(hi.x * 10) / 10
    rz = lo.z - 0.05
    r = box("RW_Ruler", ((x0 + x1) / 2, 0.0, rz), (x1 - x0, 0.004, 0.012), ruler_mat, 0.0)
    ruler_parts.append(r)
    k = 0
    x = x0
    while x <= x1 + 1e-6:
        h = 0.012 if k % 10 == 0 else 0.007
        t = box(f"RW_Tick{k}", (x, -0.003, rz + 0.006 - h / 2), (0.0012, 0.002, h), tick_mat, 0.0)
        ruler_parts.append(t)
        x += 0.01 if (x1 - x0) < 1.2 else 0.1
        k += 1 if (x1 - x0) < 1.2 else 10
    for rp in ruler_parts:
        link_to(rp, coll)
    cam_data.type = "ORTHO"
    span = max(hi.x - lo.x, (hi.z - lo.z) * 16 / 9) * 1.08 + 0.06
    cam_data.ortho_scale = span
    cam.location = Vector(((lo.x + hi.x) / 2, -3.0, (lo.z + hi.z) / 2 - 0.02))
    cam.rotation_euler = (math.radians(90), 0, 0)
    path = RENDERS / f"{asset}_Profile.png"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    files.append(path)
    build.log("render", rel(path))
    for rp in ruler_parts:
        bpy.data.objects.remove(rp, do_unlink=True)
    for cd in cards:
        bpy.data.objects.remove(cd, do_unlink=True)
    scene.view_settings.exposure = 0.0

    # --- Estate: overcast sky over the Estate's timber veranda ---------------
    for lo_ in lights:
        lo_.hide_render = True
    floor.hide_render = True
    scene.world = _world_estate(scene)
    planks = NB("RW_EstatePlanks")
    ov = planks.vmul(planks.obj(), 1.0 / 1.25)
    d_ = planks.img(committed("wood_planks_dirt", "wood_planks_dirt_diff_4k.jpg"), ov)
    a_ = planks.img(committed("wood_planks_dirt", "wood_planks_dirt_arm_4k.png"), ov, "Non-Color")
    n_ = planks.img(committed("wood_planks_dirt", "wood_planks_dirt_nor_dx_4k.png"), ov, "Non-Color")
    planks_mat = planks.finish(d_.outputs["Color"], planks.sep(a_.outputs["Color"])[1], 0.0,
                               planks.nmap_dx(n_.outputs["Color"]))
    bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 0, 0))
    veranda = bpy.context.object
    link_to(veranda, coll)
    veranda.data.materials.append(planks_mat)
    uvl = veranda.data.uv_layers.get("UVMap")
    if uvl:
        uvl.name = "UVMetric"
    # Lay each mesh on its right side (the -Y face up) on the boards; extra
    # meshes (saya, arrow) rest beside the weapon.
    lay = Matrix.Rotation(math.radians(-90.0), 4, "X")
    for k, d in enumerate(shown):
        if k > 0 and not shown_groups[k].get("lay", True):
            # Already lying flat as modelled (a coiled chain): drop it on the boards.
            zmin = min((d.matrix_world @ Vector(cn)).z for cn in d.bound_box)
            d.matrix_world = Matrix.Translation((0.0, 0.0, -zmin + 0.0004)) @ d.matrix_world
            continue
        base = lay if k == 0 else lay @ Matrix.Translation((0.0, 0.0, 0.0))
        m = base @ Matrix.Translation(d.matrix_world.translation if k == 0 else Vector((d.matrix_world.translation.x, 0.0, 0.0)))
        d.matrix_world = m
        zmin = min((d.matrix_world @ Vector(cn)).z for cn in d.bound_box)
        d.matrix_world = Matrix.Translation((0.0, 0.07 * k + (0.03 if k else 0.0), -zmin + 0.0004)) @ d.matrix_world
    focus_l = shown[0].matrix_world @ focus
    cam_data.type = "PERSP"
    cam_data.lens = 35.0
    direction = Vector((-0.35, -0.55, 0.76)).normalized()
    cam.location = focus_l + direction * 1.0
    _look_at(cam, focus_l)
    reflection_cards(coll, focus_l, cam.location, (0.0, 0.0, 1.0), dist=1.8, bright=2.6)
    cam_data.dof.use_dof = True
    cam_data.dof.focus_distance = 1.0
    cam_data.dof.aperture_fstop = 8.0
    path = RENDERS / f"{asset}_Estate_1m.png"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    files.append(path)
    build.log("render", rel(path))
    build.render_files = files
    # Leave the render rig in the saved blend? Keep the file lean: remove it.
    for o in list(coll.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.collections.remove(coll)


def run(builders: dict, opts=None):
    """Run the selected builder callables {weapon_id: fn(build)}."""
    opts = opts or parse_args()
    # Weapons still at blockout (specs status) are built only when named.
    ids = opts["only"] or [w for w in sorted(builders) if SPECS.WEAPONS[w].get("status") != "blockout"]
    for wid in ids:
        if wid not in builders:
            continue
        build = Build(wid, opts)
        builders[wid](build)
        build.finalize()
