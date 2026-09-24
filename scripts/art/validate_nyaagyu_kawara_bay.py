"""Check the source-only roof study's tile form, UV atlas and FBX round trip.

Run: blender -b --factory-startup --python scripts/art/validate_nyaagyu_kawara_bay.py
This checks editable geometry, not historic authenticity or UE visual quality.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import bpy
import bmesh
from mathutils.kdtree import KDTree

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Environment/NyaagyuKawaraBay"
manifest = json.loads((OUT / "manifest.json").read_text())
tex_manifest = json.loads((OUT / "texture_manifest.json").read_text())
for filename, expected in manifest["outputs"].items():
    assert hashlib.sha256((OUT / filename).read_bytes()).hexdigest() == expected, filename
for channel, record in tex_manifest["files"].items():
    assert hashlib.sha256((OUT / record["file"]).read_bytes()).hexdigest() == record["sha256"], channel
assert hashlib.sha256((OUT / manifest["generated_albedo"]["file"]).read_bytes()).hexdigest() == manifest["generated_albedo"]["sha256"]

bpy.ops.wm.open_mainfile(filepath=str(OUT / "Nyaagyu_KawaraBay.blend"))
asset = bpy.data.collections["KawaraBay_Editable"]
pans = sorted((o for o in asset.objects if o.name.startswith("HiraGawara_Pan_")), key=lambda o:o.name)
covers = sorted((o for o in asset.objects if o.name.startswith("MaruGawara_Cover_")), key=lambda o:o.name)
assert len(pans)==30 and len(covers)==25
assert len({o.name for o in pans+covers})==55
assert len(asset.objects)==64  # 55 tiles, 5 battens, fascia, cap, ring, logo
variants=set()
triangles=0
for obj in pans+covers:
    assert obj.type=="MESH" and obj.data.uv_layers.active
    assert all(len(poly.vertices)==4 for poly in obj.data.polygons)
    variants.add(obj["tile_variant"])
    tile_type=obj["tile_type"]
    assert tile_type in ("hira-gawara pan","maru-gawara cover")
    cell=obj["tile_variant"]
    lo_u, hi_u=(cell%4)/4,(cell%4+1)/4
    lo_v, hi_v=(3-cell//4)/4,(4-cell//4)/4
    for loop in obj.data.uv_layers.active.data:
        u,v=loop.uv
        assert lo_u+0.012 <= u <= hi_u-0.012, (obj.name,u)
        assert lo_v+0.012 <= v <= hi_v-0.012, (obj.name,v)
    triangles += 2*len(obj.data.polygons)
    bm=bmesh.new()
    bm.from_mesh(obj.data)
    assert all(edge.is_manifold for edge in bm.edges), obj.name
    assert bm.calc_volume(signed=True) > 0, obj.name
    bm.free()
    # First x-side pair and first y-end pair expose the four cap windings.
    nx,ny=12,8
    assert obj.data.polygons[2*nx*ny].normal.x < -.5, obj.name
    assert obj.data.polygons[2*nx*ny+1].normal.x > .5, obj.name
    assert obj.data.polygons[2*nx*ny+2*ny].normal.y < -.5, obj.name
    assert obj.data.polygons[2*nx*ny+2*ny+1].normal.y > .5, obj.name
assert variants == set(range(16))

def top_row_shape(obj):
    # The generator stores 13 transverse vertices per longitudinal ring.
    z0=obj.data.vertices[0].co.z
    zmid=obj.data.vertices[6].co.z
    zend=obj.data.vertices[12].co.z
    return zmid-(z0+zend)/2

assert top_row_shape(pans[0]) < -.03, top_row_shape(pans[0])
assert top_row_shape(covers[0]) > .018, top_row_shape(covers[0])

source_meshes={o.name:o for o in asset.objects if o.type=="MESH"}
source_counts={name:len(o.data.polygons) for name,o in source_meshes.items()}
source_world={name:[o.matrix_world @ v.co for v in o.data.vertices]
              for name,o in source_meshes.items()}
source_materials={name:[m.name for m in o.data.materials]
                  for name,o in source_meshes.items()}
source_face_slots={name:[p.material_index for p in o.data.polygons]
                   for name,o in source_meshes.items()}
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(OUT/"SM_Nyaagyu_KawaraBay.fbx"))
imported={o.name:o for o in bpy.context.scene.objects if o.type=="MESH"}
assert set(imported)==set(source_meshes), (set(imported)-set(source_meshes),set(source_meshes)-set(imported))
max_world_error=0.0
for name,obj in imported.items():
    assert len(obj.data.polygons)==source_counts[name], name
    assert [m.name for m in obj.data.materials]==source_materials[name], name
    assert [p.material_index for p in obj.data.polygons]==source_face_slots[name], name
    original=source_world[name]
    assert len(obj.data.vertices)==len(original), name
    source_tree=KDTree(len(original))
    for index,point in enumerate(original): source_tree.insert(point,index)
    source_tree.balance()
    imported_world=[obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    imported_tree=KDTree(len(imported_world))
    for index,point in enumerate(imported_world): imported_tree.insert(point,index)
    imported_tree.balance()
    for point in imported_world:
        _,_,distance=source_tree.find(point)
        max_world_error=max(max_world_error,distance)
        assert distance < 2e-6, (name,distance)
    for point in original:
        _,_,distance=imported_tree.find(point)
        max_world_error=max(max_world_error,distance)
        assert distance < 2e-6, (name,distance)
    if name.startswith(("HiraGawara","MaruGawara")):
        assert obj.data.uv_layers.active is not None, name
        bm=bmesh.new()
        bm.from_mesh(obj.data)
        assert all(edge.is_manifold for edge in bm.edges), name
        assert bm.calc_volume(signed=True) > 0, name
        bm.free()
print(json.dumps({"status":"passed source/FBX checks; not UE art approval",
                  "tile_count":len(pans)+len(covers),"tile_triangles":triangles,
                  "atlas_variants":len(variants),"fbx_meshes":len(imported),
                  "max_fbx_world_vertex_error_um":round(max_world_error*1e6,3)},indent=2))
