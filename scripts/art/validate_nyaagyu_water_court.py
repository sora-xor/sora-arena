"""Fail-closed source and FBX roundtrip checks for the water-court art study.

Run: blender -b Content/SourceArt/Environment/NyaagyuWaterCourt/Nyaagyu_WaterCourt_Source.blend \
       --python scripts/art/validate_nyaagyu_water_court.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "Content/SourceArt/Environment/NyaagyuWaterCourt"
record = json.loads((ART / "manifest.json").read_text())
assert record["schema_version"] == 1
assert record["name"] == "SM_Nyaagyu_WaterCourt_4m"
assert record["placement_policy"].startswith("visual-only")
assert record["source_triangles"] == record["export_triangles"]
assert record["source_triangles"] >= 30_000
assert record["culms"] >= 30 and record["leaves"] >= 1500
assert len(record["material_slots"]) >= 8


def hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


for relative, expected in record["source_files_sha256"].items():
    path = ROOT / relative
    assert path.exists() and hash_file(path) == expected, path

for role, dep in record["scan_dependencies"].items():
    assert dep["license"] in {"CC0-1.0", "original-project-art"}, role
    assert set(dep["files"]) == {"Albedo", "NormalDX", "ORM"}, role
    for channel, desc in dep["files"].items():
        path = ROOT / desc["path"]
        assert path.exists() and hash_file(path) == desc["sha256"], (role, channel)
        if dep["license"] == "CC0-1.0":
            assert desc["url"].startswith("https://dl.polyhaven.org/"), (role, channel)
        if role.startswith("Bamboo"):
            image = bpy.data.images.load(str(path), check_existing=True)
            assert tuple(image.size) == (2048, 2048), (role, channel)

export = bpy.data.objects.get(record["name"])
assert export and export.type == "MESH"
assert export.data.uv_layers.get("UVMap")
assert [m.name for m in export.data.materials] == record["material_slots"]
assert all(poly.material_index < len(export.data.materials) for poly in export.data.polygons)
assert sum(len(poly.vertices) - 2 for poly in export.data.polygons) == record["export_triangles"]
assert export.get("collision_policy") == "visual_only"
editable = bpy.data.collections.get("WaterCourt_Editable")
assert editable and len(editable.objects) == record["source_mesh_parts"]
assert len([o for o in editable.objects if o.name.startswith("Bamboo_Leaf_")]) == record["leaves"]
subset = bpy.data.objects.get(record["subset_name"])
assert subset and subset.type == "MESH"
assert subset.data.uv_layers.get("UVMap")
assert subset.get("collision_policy") == "visual_only"
assert record["subset_source_parts"] > 2000
assert sum(len(poly.vertices) - 2 for poly in subset.data.polygons) == record["subset_triangles"]
assert [m.name for m in subset.data.materials] == record["subset_material_slots"]
assert not any(name.startswith(("M_Court_Cedar", "M_Court_Roof"))
               for name in record["subset_material_slots"])
subset_coords = [subset.matrix_world @ vertex.co for vertex in subset.data.vertices]
for i, axis in enumerate("xyz"):
    bounds = [round(min(v[i] for v in subset_coords), 4),
              round(max(v[i] for v in subset_coords), 4)]
    assert bounds == record["subset_bounds_m"][axis], (axis, bounds)

coords = [export.matrix_world @ vertex.co for vertex in export.data.vertices]
for i, axis in enumerate("xyz"):
    bounds = [round(min(v[i] for v in coords), 4), round(max(v[i] for v in coords), 4)]
    assert bounds == record["bounds_m"][axis], (axis, bounds)
assert -2.5 <= record["bounds_m"]["x"][0] < 0
assert 2.0 < record["bounds_m"]["x"][1] <= 3.1
assert -.7 <= record["bounds_m"]["y"][0] < 0
assert 2.2 < record["bounds_m"]["y"][1] <= 3.1
assert -.1 <= record["bounds_m"]["z"][0] < 0
assert 3.0 < record["bounds_m"]["z"][1] <= 3.6

before = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=str(ART / (record["name"] + ".fbx")))
imported = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
assert len(imported) == 1, [o.name for o in imported]
mesh = imported[0]
assert mesh.data.uv_layers.get("UVMap")
assert {m.name.removesuffix(".001") for m in mesh.data.materials} == set(record["material_slots"])
imported_tris = sum(len(poly.vertices) - 2 for poly in mesh.data.polygons)
assert imported_tris == record["export_triangles"], (imported_tris, record["export_triangles"])
import_coords = [mesh.matrix_world @ vertex.co for vertex in mesh.data.vertices]
for i, axis in enumerate("xyz"):
    bounds = [min(v[i] for v in import_coords), max(v[i] for v in import_coords)]
    expected = record["bounds_m"][axis]
    assert max(abs(bounds[j] - expected[j]) for j in range(2)) < .025, (axis, bounds, expected)

before = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=str(ART / (record["subset_name"] + ".fbx")))
imported = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
assert len(imported) == 1, [o.name for o in imported]
subset_mesh = imported[0]
assert subset_mesh.data.uv_layers.get("UVMap")
assert {m.name.removesuffix(".001").removesuffix(".002")
        for m in subset_mesh.data.materials} == set(record["subset_material_slots"])
assert sum(len(poly.vertices) - 2 for poly in subset_mesh.data.polygons) == record["subset_triangles"]
subset_import_coords = [subset_mesh.matrix_world @ vertex.co for vertex in subset_mesh.data.vertices]
for i, axis in enumerate("xyz"):
    bounds = [min(v[i] for v in subset_import_coords),
              max(v[i] for v in subset_import_coords)]
    expected = record["subset_bounds_m"][axis]
    assert max(abs(bounds[j] - expected[j]) for j in range(2)) < .025, (axis, bounds, expected)

print("WATER_COURT_SOURCE_AND_FBX_PASS", json.dumps({
    "parts": record["source_mesh_parts"],
    "triangles": record["source_triangles"],
    "culms": record["culms"],
    "leaves": record["leaves"],
    "bounds_m": record["bounds_m"],
    "subset_triangles": record["subset_triangles"],
    "subset_bounds_m": record["subset_bounds_m"],
}))
