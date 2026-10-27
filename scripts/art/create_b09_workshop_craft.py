"""Build the b09 lantern workshop's candidate meshes in Blender from b09_workshop_craft, one FBX per asset.

The meshes, pivots, material slots and sockets are b09_workshop_craft's, in Unreal centimetres. This script:
- converts them to Blender metres (x, -y, z) / 100, reversing each triangle's winding, since the Y flip mirrors;
- gives each its material slots;
- adds two UV channels:
  - UV0, a metric box projection (one unit per metre), for tiling maps;
  - UV1 (`Reveal`), (height_frac, azimuth_frac) for the washi's paste and oil reveal. It comes from the module's
    attributes where a mesh has them, and is computed in the lantern frame otherwise.
- smooths with sharp edges past 30 deg;
- adds SOCKET_ empties for the station sockets;
- exports in fbx_socket_export's socket convention (Blender's own axes, which are UE 5.8's FBX import axes, with the
  unit baked in), so Interchange imports each socket on its own axes at scale 1. The runtime weapon kit's -Y forward
  would import the vertices and socket positions the same but turn every socket 180 deg about Y
  (fbx_unreal_sockets.py).

**The assets** are b09_workshop_craft.candidates():
- **each station's static mesh**, in the station frame. The paste bench's form and hoops are split out as
  `SM_B09_PasteFrame` (lantern frame), since its turntable turns them;
- **every state mesh**, in its own frame (b09_workshop_craft.state_meshes);
- **the drying poles and their 40 hooks**, in world cm, placed at the world origin.
The UV layouts are the module's too (box_uv, reveal_uv), so check_b09_candidates_fbx.py compares the files with it.

These are candidates: they are written to a new folder under Saved/B09Workshop/Candidates, beside a manifest. Nothing
is saved to a .blend or to Content.

Run (lane holder):
  Blender -b --factory-startup --python-exit-code 1 --python scripts/art/create_b09_workshop_craft.py -- <new folder>
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import b09_workshop_craft as B  # noqa: E402
import fbx_socket_export as X  # noqa: E402

MARKER = "B09_CANDIDATES_BUILT"
TOOL = "scripts/art/create_b09_workshop_craft.py"
SHARP_DEG = 30.0


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def unit(v, default):
    """A socket axis in Unreal's frame, unit length (the default where the module gives none)."""
    v = np.asarray(default if v is None else v, float)
    return np.round(v / np.linalg.norm(v), 6).tolist()


def to_blender(v):
    v = np.asarray(v, float)
    return np.stack([v[..., 0], -v[..., 1], v[..., 2]], -1) / 100.0


def material(name):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    c = B.COLOURS.get(name, (0.6, 0.6, 0.6))
    m.diffuse_color = (c[0], c[1], c[2], 1.0)
    return m


def make_object(mesh, name, lantern_frame=False):
    me = bpy.data.meshes.new(name)
    verts = to_blender(mesh.verts)
    tris = mesh.tris[:, [0, 2, 1]]                      # the Y flip mirrors, so the winding turns back
    me.from_pydata(verts.tolist(), [], tris.tolist())
    me.update()
    slots = mesh.slots()
    names = list(dict.fromkeys(slots.tolist()))
    for n in names:
        me.materials.append(material(n))
    me.polygons.foreach_set("material_index", [names.index(s) for s in slots.tolist()])
    uv0 = me.uv_layers.new(name="UV0")
    uv1 = me.uv_layers.new(name="Reveal")
    uv0.data.foreach_set("uv", B.box_uv(mesh)[:, [0, 2, 1]].ravel())          # the loops run in Blender's winding
    uv1.data.foreach_set("uv", B.reveal_uv(mesh, lantern_frame)[tris.ravel()].ravel())
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(SHARP_DEG))
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def add_socket(obj, name, point, x_axis, z_axis):
    e = bpy.data.objects.new(f"SOCKET_{name}", None)
    e.empty_display_type = "ARROWS"
    e.empty_display_size = 0.03
    bpy.context.scene.collection.objects.link(e)
    x = Vector(to_blender(x_axis if x_axis is not None else (1.0, 0.0, 0.0)).tolist()).normalized()
    z = Vector(to_blender(z_axis if z_axis is not None else (0.0, 0.0, 1.0)).tolist()).normalized()
    y = z.cross(x)
    mat = Matrix((x, y, z)).transposed().to_4x4()
    mat.translation = Vector(to_blender(point).tolist())
    e.parent = obj
    e.matrix_parent_inverse = Matrix.Identity(4)
    e.matrix_basis = mat
    return e


def export(obj, empties, out):
    path = out / f"{obj.name}.fbx"
    X.export(path, obj, empties)                         # SOCKET_FBX and the library's LOD0 settings
    if not path.is_file():
        raise RuntimeError(f"{path.name} was not written")
    return path


def main():
    out = (ROOT / sys.argv[sys.argv.index("--") + 1]).resolve()
    if out.exists() or not out.is_relative_to(ROOT / "Saved/B09Workshop/Candidates"):
        raise SystemExit(f"the output must be a new folder under Saved/B09Workshop/Candidates: {out}")
    out.mkdir(parents=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    record = {"generator": "scripts/art/create_b09_workshop_craft.py", "generator_sha256": sha256(__file__),
              "module_sha256": sha256(B.__file__), "spec_sha256": sha256(ROOT / "docs/art-direction/data/b09_workshop_craft_spec.json"),
              "root_inputs": B.INPUTS, "blender": bpy.app.version_string, "units": "metres in Blender; FBX apply_unit_scale (Unreal cm)",
              "axes": "Unreal (x, y, z) cm -> Blender (x, -y, z) / 100",
              "export": {"convention": dict(X.SOCKET_FBX),
                         "rest": {k: (sorted(v) if isinstance(v, set) else v) for k, v in X.LIBRARY_LOD0_REST.items()},
                         "why": "fbx_socket_export's socket convention: the file declares UE 5.8's FBX import axes, so "
                                "Interchange converts nothing and imports each socket on its own axes at scale 1",
                         "gate": "scripts/art/check_b09_candidates_fbx.py, through fbx_unreal_sockets.interchange"},
              "collision": "none: every mesh is visual only (b09_workshop_craft, section 6)", "assets": {}}
    seen = set()
    for name, mesh, socks, frame, lantern_frame in B.candidates():
        if name in seen:
            raise SystemExit(f"two assets named {name}")
        seen.add(name)
        obj = make_object(mesh, name, lantern_frame)
        empties = [add_socket(obj, s, p, xa, za) for s, (p, xa, za) in sorted(socks.items())]
        path = export(obj, empties, out)
        lo, hi = mesh.bounds()
        record["assets"][name] = {"fbx": path.name, "sha256": sha256(path), "triangles": int(len(mesh.tris)),
                                  "slots": list(dict.fromkeys(mesh.slots().tolist())), "frame": frame,
                                  "bounds_cm": [np.round(lo, 3).tolist(), np.round(hi, 3).tolist()],
                                  "sockets": {s: np.round(p, 3).tolist() for s, (p, _, _) in sorted(socks.items())},
                                  "socket_axes": {s: {"x": list(unit(xa, (1.0, 0.0, 0.0))), "z": list(unit(za, (0.0, 0.0, 1.0)))}
                                                  for s, (_, xa, za) in sorted(socks.items())}}
        # The next asset reuses socket names (StationPoint, WorkStand), so these empties step aside by renaming.
        # Removing them instead (s144) left stale view-layer entries that fbx_socket_export.export then met as None.
        for e in empties:
            e.name = f"Done{len(record['assets']):02d}_{e.name}"
    with open(out / "manifest.json", "x") as fh:
        json.dump(record, fh, indent=1)
    print(MARKER, json.dumps({"assets": len(record["assets"]), "out": str(out.relative_to(ROOT))}), flush=True)


main()
