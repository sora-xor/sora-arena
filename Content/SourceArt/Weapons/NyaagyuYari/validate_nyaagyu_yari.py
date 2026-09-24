"""Independent Blender/FBX geometry checks for the source-only su-yari study."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector, kdtree

OUT = Path(__file__).resolve().parent
manifest = json.loads((OUT / "manifest.json").read_text())
assert manifest["museum_anchor"]["accession"] == "OA+.7199"
assert manifest["museum_anchor"]["catalog_measurements_m"] == {
    "overall": 1.93, "blade": .18, "tang": .48}

texture_files = sorted((OUT / "Textures").glob("T_Yari_*.png"))
assert len(texture_files) == 15
assert {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in texture_files} == manifest["textures_sha256"]
fbx = OUT / "SM_Nyaagyu_Suyari_SourceStudy.fbx"
assert hashlib.sha256(fbx.read_bytes()).hexdigest() == manifest["fbx_sha256"]
for name in manifest["renders"]:
    assert (OUT / name).stat().st_size > 100_000

bpy.ops.wm.open_mainfile(filepath=str(OUT / "Nyaagyu_Suyari_SourceStudy.blend"))
collection = bpy.data.collections["NyaagyuSuyari_EditableWeapon"]
source = {o.name: o for o in collection.objects if o.type == "MESH"}
assert len(source) == 10, source.keys()
assert "SuyariBlade_EightFacetDiamond" in source
assert "SteelTang_480mm_InsideHaft" in source
assert "UrushiCoatedHaft" in source


def global_coords(obj):
    return sorted(tuple(round(v, 6) for v in obj.matrix_world @ vertex.co)
                  for vertex in obj.data.vertices)


world_vertices = {}
total_triangles = 0
for name, obj in source.items():
    assert obj.data.uv_layers.active, name
    assert len(obj.data.uv_layers.active.data) == len(obj.data.loops), name
    assert all(poly.area > 1e-12 for poly in obj.data.polygons), name
    assert all(0 <= item.uv.x <= 1.001 and 0 <= item.uv.y <= 1.001
               for item in obj.data.uv_layers.active.data), name
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    assert all(edge.is_manifold for edge in bm.edges), name
    volume = bm.calc_volume(signed=True)
    assert volume > 0, (name, volume)
    bm.free()
    total_triangles += sum(len(poly.vertices)-2 for poly in obj.data.polygons)
    world_vertices[name] = global_coords(obj)

all_z = [v[2] for verts in world_vertices.values() for v in verts]
blade_z = [v[2] for v in world_vertices["SuyariBlade_EightFacetDiamond"]]
tang_z = [v[2] for v in world_vertices["SteelTang_480mm_InsideHaft"]]
assert abs(min(all_z)) <= 1e-6 and abs(max(all_z)-1.93) <= 1e-6
assert abs((max(blade_z)-min(blade_z))-.18) <= 1e-6
assert abs((max(tang_z)-min(tang_z))-.48) <= 1e-6
blade = source["SuyariBlade_EightFacetDiamond"]
assert len(blade.data.vertices) == 80
assert blade["blade_section"].startswith("original eight-facet diamond")

for obj in source.values():
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.import_scene.fbx(filepath=str(fbx), use_custom_normals=True)
roundtrip = {o.name: o for o in bpy.context.selected_objects if o.type == "MESH"}
assert set(roundtrip) == set(world_vertices), (roundtrip.keys(),world_vertices.keys())
max_error = 0.0
for name, expected in world_vertices.items():
    obj = roundtrip[name]
    assert obj.data.uv_layers.active, name
    actual = global_coords(obj)
    assert len(actual) == len(expected), (name, len(actual), len(expected))
    tree = kdtree.KDTree(len(actual))
    for index, point in enumerate(actual):
        tree.insert(Vector(point), index)
    tree.balance()
    error = max(tree.find(Vector(point))[2] for point in expected)
    max_error = max(max_error, error)
assert max_error <= .000002, max_error

print("YARI_SOURCE_VALID", len(source), total_triangles,
      f"max_roundtrip_error_m={max_error:.8f}",
      "overall=1.93m blade=.18m tang=.48m")
