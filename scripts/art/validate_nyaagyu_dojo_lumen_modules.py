"""Validate the source-only Dojo Lumen module FBXs against the authored .blend.

Run:
  blender -b Content/SourceArt/Environment/NyaagyuDojo/Nyaagyu_EstateDojo.blend \
    --python scripts/art/validate_nyaagyu_dojo_lumen_modules.py

This checks exact source part/triangle/material partition, then FBX roundtrip
polygon indices/material assignments and each world-space vertex within 2 µm.
It does not test Unreal import, cards, lighting, or runtime placement.
"""

from __future__ import annotations

import atexit
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import sys

import bpy


DONE = False


def fail_if_incomplete():
    if not DONE:
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(1)


atexit.register(fail_if_incomplete)
ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "Content/SourceArt/Environment/NyaagyuDojo"
OUT = SOURCE / "LumenModules"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from nyaagyu_dojo_module_common import (  # noqa: E402
    bounds_close, classify, material_name, material_triangle_counts,
    triangle_count, triangle_digest, triangle_records, union_bounds, world_bounds,
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def base_name(imported_name: str) -> str:
    return re.sub(r"\.\d{3}$", "", imported_name)


assert bpy.app.version[:2] == (5, 2), bpy.app.version
original = json.loads((SOURCE / "manifest.json").read_text())
manifest = json.loads((OUT / "manifest.json").read_text())
assert manifest["schema_version"] == 1
assert Path(bpy.data.filepath).resolve() == (SOURCE / original["source_blend"]).resolve()
assert sha(SOURCE / original["source_blend"]) == manifest["source_blend_sha256"] == original["blend_sha256"]
assert sha(SOURCE / original["fbx"]) == manifest["source_combined_fbx_sha256"] == original["fbx_sha256"]
assert manifest["generator_sha256"] == sha(ROOT / manifest["generator"])
assert manifest["classification_sha256"] == sha(ROOT / manifest["classification"])
assert manifest["license"] == original["license"]
assert "Original project-owned geometry" in manifest["license"]
assert "CC0 Poly Haven" in manifest["license"]

editable = bpy.data.collections["Nyaagyu_EstateDojo_Editable"]
parts = [obj for obj in editable.objects if obj.type == "MESH"]
groups = classify(parts)
assert len(parts) == manifest["source_parts"] == 424
assert triangle_count(parts) == manifest["source_triangles"] == 73946
source_records = triangle_records(parts)
assert triangle_digest(source_records) == manifest["source_world_triangle_sha256"]
assert world_bounds(parts) == manifest["source_world_bounds_m"]
assert material_triangle_counts(parts) == manifest["source_material_triangle_counts"]
assert [item["name"].rsplit("_", 1)[-1] for item in manifest["modules"]] == [
    "Roof", "Eaves", "Body", "Shoji"
]

all_records = []
all_imported_bounds = []
total_fbx_bytes = 0
max_vertex_error_m = 0.0
for item in manifest["modules"]:
    label = item["name"].rsplit("_", 1)[-1]
    selected = groups[label]
    selected_by_name = {obj.name: obj for obj in selected}
    assert len(selected) == item["parts"]
    assert [obj.name for obj in selected] == item["part_names"]
    assert set(item["export_object_names"]) == set(item["part_names"])
    assert len(set(item["export_object_names"].values())) == len(selected)
    assert triangle_count(selected) == item["triangles"]
    assert world_bounds(selected) == item["world_bounds_m"]
    assert material_triangle_counts(selected) == item["material_triangle_counts"]
    records = triangle_records(selected)
    assert triangle_digest(records) == item["world_triangle_sha256"]
    all_records.extend(records)
    actual_slots = {
        obj.name: [slot.material.name if slot.material else None
                   for slot in obj.material_slots]
        for obj in selected
    }
    assert actual_slots == item["part_material_slots"]
    assert sorted({name for names in actual_slots.values() for name in names if name}) == item["material_slots"]

    fbx = OUT / item["fbx"]
    assert fbx.stat().st_size == item["fbx_bytes"] > 1000
    assert sha(fbx) == item["fbx_sha256"]
    assert fbx.read_bytes().startswith(b"Kaydara FBX Binary")
    assert b"/Users/" not in fbx.read_bytes()
    total_fbx_bytes += fbx.stat().st_size
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(fbx))
    new_objects = set(bpy.data.objects) - before
    imported = [obj for obj in new_objects if obj.type == "MESH"]
    assert len(imported) == item["export_object_count"] == len(selected)
    imported_by_export_name = {obj.name: obj for obj in imported}
    assert set(imported_by_export_name) == set(item["export_object_names"].values()), (
        label, sorted(set(imported_by_export_name) ^ set(item["export_object_names"].values()))
    )
    assert triangle_count(imported) == item["triangles"]
    assert material_triangle_counts(imported) == item["material_triangle_counts"]
    assert bounds_close(world_bounds(imported), item["world_bounds_m"], 0.000002)
    all_imported_bounds.append(world_bounds(imported))
    for name, source_obj in selected_by_name.items():
        imported_obj = imported_by_export_name[item["export_object_names"][name]]
        assert len(source_obj.data.vertices) == len(imported_obj.data.vertices), name
        assert len(source_obj.data.polygons) == len(imported_obj.data.polygons), name
        assert len(source_obj.data.uv_layers) == len(imported_obj.data.uv_layers), name
        source_slots = [slot.material.name if slot.material else None
                        for slot in source_obj.material_slots]
        imported_slots = [base_name(slot.material.name) if slot.material else None
                          for slot in imported_obj.material_slots]
        assert source_slots == imported_slots, (name, source_slots, imported_slots)
        for original_vertex, roundtrip_vertex in zip(
                source_obj.data.vertices, imported_obj.data.vertices):
            source_position = source_obj.matrix_world @ original_vertex.co
            imported_position = imported_obj.matrix_world @ roundtrip_vertex.co
            error = (source_position - imported_position).length
            max_vertex_error_m = max(max_vertex_error_m, error)
            assert error <= 0.000002, (name, original_vertex.index, error)
        for source_face, imported_face in zip(
                source_obj.data.polygons, imported_obj.data.polygons):
            assert tuple(source_face.vertices) == tuple(imported_face.vertices), (
                name, source_face.index, "topology or winding changed"
            )
            assert material_name(source_obj, source_face) == material_name(
                imported_obj, imported_face
            ), (name, source_face.index, "material face binding changed")
        for source_uv, imported_uv in zip(
                source_obj.data.uv_layers, imported_obj.data.uv_layers):
            assert len(source_uv.data) == len(imported_uv.data), name
            for original_loop, roundtrip_loop in zip(
                    source_uv.data, imported_uv.data):
                assert (original_loop.uv - roundtrip_loop.uv).length < 0.00001, name
    print("NYAAGYU_DOJO_MODULE_ROUNDTRIP", label, len(imported), item["triangles"],
          max_vertex_error_m, flush=True)
    for obj in new_objects:
        bpy.data.objects.remove(obj, do_unlink=True)

assert total_fbx_bytes < 100_000_000
assert sorted(all_records) == source_records
assert bounds_close(union_bounds(all_imported_bounds), manifest["source_world_bounds_m"], 0.000002)
assert len(editable.objects) == 424
assert sha(SOURCE / original["source_blend"]) == original["blend_sha256"]
assert sha(SOURCE / original["fbx"]) == original["fbx_sha256"]
print("NYAAGYU_DOJO_MODULES_VALIDATED", len(manifest["modules"]), len(parts),
      len(source_records), "max_world_vertex_error_m", max_vertex_error_m, flush=True)
DONE = True
