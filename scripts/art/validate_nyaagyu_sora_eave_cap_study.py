"""Independently check editable source, exact-logo provenance and FBX parity.

This is a geometry/source gate, not a visual, historical or Unreal performance
approval. Run under Blender 5.2.2 LTS after the build scripts.
"""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector
from mathutils.kdtree import KDTree


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Environment/NyaagyuSoraEaveCapStudy"
SVG = ROOT / "Content/SourceArt/UI/sora_logo_NOtext2.svg"
manifest = json.loads((OUT / "manifest.json").read_text())
textures = json.loads((OUT / "texture_manifest.json").read_text())
assert hashlib.sha256(SVG.read_bytes()).hexdigest() == manifest["source_svg_sha256"]
assert manifest["source_svg_sha256"] == "d66413a71b70e25dcb8b2f118dcfe846a6446ed1db3de53ce88fc70c16ac0910"
for name, expected in manifest["outputs"].items():
    assert hashlib.sha256((OUT / name).read_bytes()).hexdigest() == expected, name
for record in textures["files"].values():
    assert hashlib.sha256((OUT / record["file"]).read_bytes()).hexdigest() == record["sha256"]

bpy.ops.wm.open_mainfile(filepath=str(OUT / "Nyaagyu_SORA_EaveCap.blend"))
assert bpy.app.version_string == manifest["blender_version"]
asset = bpy.data.collections["SORA_EaveCap_Editable"]
objects = {obj.name: obj for obj in asset.objects}
assert set(objects) == {
    "EaveCap_SculptedClay", "VaultedCover_SolidClay",
    "MoldedCollar_0", "MoldedCollar_1",
    "SORA_ExactSVG_ClayRelief_Path_0", "SORA_ExactSVG_ClayRelief_Path_1",
}, set(objects)
assert all(obj.type == "MESH" for obj in objects.values())
assert "ReviewOnly_CharredCedarEave" not in objects

triangle_count = 0
for obj in objects.values():
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    assert all(edge.is_manifold for edge in bm.edges), (obj.name, Counter(len(e.link_faces) for e in bm.edges))
    assert bm.calc_volume(signed=True) > 0, obj.name
    bm.free()
    assert obj.data.uv_layers.active is not None, obj.name
    assert len(obj.data.materials) == 1, obj.name
    triangle_count += sum(len(poly.vertices)-2 for poly in obj.data.polygons)
disc = objects["EaveCap_SculptedClay"]
assert len(disc.data.vertices) >= 1500
for index in (0, 1):
    relief = objects[f"SORA_ExactSVG_ClayRelief_Path_{index}"]
    assert relief["source_svg_sha256"] == manifest["source_svg_sha256"]
    assert relief["source_path_index"] == index
    assert "WornMoldedHighs" in relief.data.materials[0].name
    y_values = [(relief.matrix_world @ vertex.co).y for vertex in relief.data.vertices]
    assert min(y_values) < -.0244 and max(y_values) > -.0214, (index,min(y_values),max(y_values))
    assert len(relief.data.vertices) > 100

# Re-import the source SVG from disk, without reading the production relief
# mesh, and compare the two filled source-path areas with the molded front faces.
before = set(bpy.data.objects)
bpy.ops.import_curve.svg(filepath=str(SVG))
fresh = sorted((obj for obj in set(bpy.data.objects)-before if obj.type == "CURVE"),
               key=lambda obj: obj.name)
assert len(fresh) == 2
corners = [obj.matrix_world @ Vector(corner) for obj in fresh for corner in obj.bound_box]
size = max(max(p.x for p in corners)-min(p.x for p in corners),
           max(p.y for p in corners)-min(p.y for p in corners))
scale = .093 / size
source_areas = []
for obj in fresh:
    obj.data.dimensions = "2D"
    obj.data.fill_mode = "BOTH"
    obj.data.resolution_u = 24
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target="MESH")
    filled = bpy.context.object
    area = 0.0
    for poly in filled.data.polygons:
        ring = [filled.matrix_world @ filled.data.vertices[i].co for i in poly.vertices]
        area += abs(sum(a.x*b.y-b.x*a.y for a,b in zip(ring,ring[1:]+ring[:1])))*.5
    source_areas.append(area*scale**2)
    bpy.data.objects.remove(filled, do_unlink=True)
front_areas = []
for index in (0,1):
    obj = objects[f"SORA_ExactSVG_ClayRelief_Path_{index}"]
    area = 0.0
    for poly in obj.data.polygons:
        normal = (obj.matrix_world.to_3x3() @ poly.normal).normalized()
        if normal.y >= -.995:
            continue
        ring = [obj.matrix_world @ obj.data.vertices[i].co for i in poly.vertices]
        area += abs(sum(a.x*b.z-b.x*a.z for a,b in zip(ring,ring[1:]+ring[:1])))*.5
    front_areas.append(area)
for expected, actual in zip(source_areas, front_areas):
    assert expected > 0 and abs(actual-expected)/expected < .10, (expected,actual)

source_meshes = objects
counts = {name: (len(obj.data.vertices),len(obj.data.polygons)) for name,obj in objects.items()}
world_vertices = {name: [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
                  for name,obj in objects.items()}
material_names = {name: [mat.name for mat in obj.data.materials] for name,obj in objects.items()}
source_uvs = {name: Counter((round(float(loop.uv.x),5),round(float(loop.uv.y),5))
                            for loop in obj.data.uv_layers.active.data)
              for name,obj in objects.items()}
source_face_slots = {name: [poly.material_index for poly in obj.data.polygons]
                     for name,obj in objects.items()}
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(OUT / "SM_Nyaagyu_SORA_EaveCap.fbx"))
roundtrip = {obj.name: obj for obj in bpy.context.scene.objects if obj.type == "MESH"}
assert set(roundtrip) == set(source_meshes), (set(roundtrip),set(source_meshes))
max_error = 0.0
for name, obj in roundtrip.items():
    assert (len(obj.data.vertices),len(obj.data.polygons)) == counts[name], name
    assert [mat.name for mat in obj.data.materials] == material_names[name], name
    assert obj.data.uv_layers.active is not None, name
    assert [poly.material_index for poly in obj.data.polygons] == source_face_slots[name], name
    found_uvs = Counter((round(float(loop.uv.x),5),round(float(loop.uv.y),5))
                        for loop in obj.data.uv_layers.active.data)
    assert found_uvs == source_uvs[name], (name,"UV parity")
    source = world_vertices[name]
    found = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    tree = KDTree(len(source))
    for i, point in enumerate(source): tree.insert(point,i)
    tree.balance()
    reverse = KDTree(len(found))
    for i, point in enumerate(found): reverse.insert(point,i)
    reverse.balance()
    for point in found:
        d = tree.find(point)[2]
        max_error = max(max_error,d)
        assert d < 2e-6, (name,d)
    for point in source:
        d = reverse.find(point)[2]
        max_error = max(max_error,d)
        assert d < 2e-6, (name,d)
print(json.dumps({"status":"passed source-only geometry/FBX gate; no UE or historic approval",
                  "mesh_count":len(objects), "triangle_count":triangle_count,
                  "source_crest_areas_m2":source_areas,
                  "relief_front_areas_m2":front_areas,
                  "max_fbx_world_vertex_error_um":round(max_error*1e6,3)},indent=2))
