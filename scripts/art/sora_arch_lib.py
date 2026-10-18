"""Shared Blender 5.2 helpers for modular Japanese architecture kits.

Architecture uses tiling, physically scaled scan materials in Unreal rather than
unique bakes: every module's UV0 is a continuous metre-scale projection
(1 UV unit = 1 m), so a material instance's TileMeters sets real texel density
and walls continue across modules. Material slots are named for the surface
role (``M_Arch_<Role>``); the importer binds each role to its instance.

Modules are exported one FBX per LOD with a JSON record (bounds, triangles,
slots, hashes). Units are metres; FBX export applies unit scale so Unreal
receives centimetres. Wall modules use a local frame with X along the wall,
+Y outward (into the wall), Z up from the floor; the room is at -Y.
"""

from __future__ import annotations

import hashlib
import json
import math
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
import create_runtime_weapon_lib as L  # noqa: E402

ROOT = L.ROOT
_MATS: dict[str, bpy.types.Material] = {}

# Preview colours (linear) for Blender review only; Unreal binds scan materials.
ROLE_PREVIEW = {
    "Hinoki": (0.42, 0.29, 0.16), "CedarBoard": (0.20, 0.11, 0.06), "Plaster": (0.55, 0.47, 0.36),
    "DarkTimber": (0.06, 0.035, 0.022), "RenjiBar": (0.05, 0.03, 0.02), "ShojiPaper": (0.80, 0.76, 0.66),
    "Kumiko": (0.30, 0.21, 0.12), "Lacquer": (0.012, 0.010, 0.009), "Gilt": (1.0, 0.77, 0.34),
    "CofferPanel": (0.03, 0.05, 0.12), "Tatami": (0.45, 0.42, 0.22), "Stone": (0.30, 0.29, 0.27),
    "Hemp": (0.62, 0.55, 0.42), "Iron": (0.05, 0.05, 0.05),
}


def role_mat(role: str) -> bpy.types.Material:
    name = f"M_Arch_{role}"
    if name in _MATS:
        return _MATS[name]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    col = ROLE_PREVIEW.get(role, (0.5, 0.5, 0.5))
    bsdf.inputs["Base Color"].default_value = (*col, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.35 if role in ("Hinoki", "Lacquer", "Gilt") else 0.7
    bsdf.inputs["Metallic"].default_value = 1.0 if role in ("Gilt", "Iron") else 0.0
    _MATS[name] = mat
    return mat


def reset():
    _MATS.clear()
    return L.reset_scene()


def block(name, x0, x1, y0, y1, z0, z1, role, bevel=0.003, segments=1):
    """Axis-aligned bevelled box between two corners (metres)."""
    c = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
    s = (abs(x1 - x0), abs(y1 - y0), abs(z1 - z0))
    bev = min(bevel, min(s) * 0.45)
    return L.box(name, c, s, role_mat(role), bevel=bev, segments=segments)


def metric_uv0(obj, rot_axes=None):
    """Copy UVMetric (box-projected metres) into UV0 for tiling materials."""
    me = obj.data
    L.ensure_uv_layers(me)
    L.box_uv(me, "UVMetric")
    src = np.empty(len(me.loops) * 2)
    me.uv_layers["UVMetric"].data.foreach_get("uv", src)
    me.uv_layers["UV0"].data.foreach_set("uv", src)
    obj["rw_needs_unwrap"] = False
    return obj


def set_uv0_rect(obj, face_filter, u0, v0, du_per_m, dv_per_m, axis_u="x", axis_v="y"):
    """Planar UV0 for selected faces: u = u0 + coord_u * du, v = v0 + coord_v * dv."""
    me = obj.data
    uv = me.uv_layers["UV0"].data
    ai = "xyz".index(axis_u)
    bi = "xyz".index(axis_v)
    for poly in me.polygons:
        if not face_filter(poly):
            continue
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uv[li].uv = (u0 + co[ai] * du_per_m, v0 + co[bi] * dv_per_m)


def join_all(objs, name):
    obj = L.join(objs, name)
    obj.data.name = name
    return obj


def _triangulate(obj):
    mod = obj.modifiers.new("Tri", "TRIANGULATE")
    mod.quad_method = "BEAUTY"
    mod.keep_custom_normals = True
    L.apply_modifiers(obj)


def export_module(name, objs, folder: Path, lod_ratios=(1.0, 0.5, 0.25), lod_keep=None, record=None):
    """Join parts, triangulate and export LOD0..n FBX files; returns a record dict.

    ``lod_keep``: callable(obj_name, lod) -> bool deciding whether a source part
    survives into a LOD before decimation (drop small details first).
    """
    folder.mkdir(parents=True, exist_ok=True)
    files = []
    tris = []
    base_parts = list(objs)
    for lod, ratio in enumerate(lod_ratios):
        parts = []
        for o in base_parts:
            if lod_keep is not None and not lod_keep(o.name, lod):
                continue
            c = o.copy()
            c.data = o.data.copy()
            L.collection("ARCH_Export").objects.link(c)
            parts.append(c)
        obj = join_all(parts, name if lod == 0 else f"{name}_LOD{lod}")
        _triangulate(obj)
        if lod > 0 and ratio < 1.0:
            target = int(tris[0] * ratio)
            cur = len(obj.data.polygons)
            if cur > target:
                mod = obj.modifiers.new("Dec", "DECIMATE")
                mod.decimate_type = "COLLAPSE"
                mod.ratio = max(0.05, target / cur)
                mod.use_collapse_triangulate = True
                L.apply_modifiers(obj)
        L.finish_shading(obj, True, 40.0)
        path = folder / f"{obj.name}.fbx"
        L.deselect_all()
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, object_types={"MESH"},
                                 apply_unit_scale=True, apply_scale_options="FBX_SCALE_NONE", global_scale=1.0,
                                 axis_forward="-Y", axis_up="Z", mesh_smooth_type="FACE", use_tspace=True,
                                 use_triangles=True, use_mesh_modifiers=True, add_leaf_bones=False,
                                 bake_anim=False, path_mode="STRIP", embed_textures=False,
                                 use_custom_props=False)
        files.append(path)
        tris.append(len(obj.data.polygons))
        if lod == 0:
            dims = obj.dimensions.copy()
            bb = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
            lo = [min(p[i] for p in bb) for i in range(3)]
            hi = [max(p[i] for p in bb) for i in range(3)]
            slots = sorted({m.name for m in obj.data.materials if m})
        bpy.data.objects.remove(obj, do_unlink=True)
    rec = {
        "asset": name,
        "lods": [{"file": L.rel(p), "triangles": t, "sha256": L.sha256(p)} for p, t in zip(files, tris)],
        "bounds_m": {"min": [round(v, 5) for v in lo], "max": [round(v, 5) for v in hi]},
        "material_slots": slots,
    }
    if record:
        rec.update(record)
    return rec


def write_manifest(folder: Path, kit: str, generator: str, modules: list[dict], notes: dict):
    manifest = {
        "schema_version": 1,
        "kit": kit,
        "generator": generator,
        "generator_sha256": L.sha256(ROOT / generator),
        "units": "metres in Blender; FBX apply_unit_scale (Unreal centimetres)",
        "frame": "wall modules: +X along the wall, +Y outward into the wall, Z up; room at -Y; origin at floor on the inner wall plane",
        "uv0": "continuous metre-scale projection (1 UV = 1 m) for tiling scan materials, except where noted",
        "modules": modules,
        "notes": notes,
    }
    (folder / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return manifest
