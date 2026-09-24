"""Check the source-only roof study's tile form, UV atlas and FBX round trip.

Run: blender -b --factory-startup --python scripts/art/validate_nyaagyu_kawara_bay.py
This checks editable geometry, not historic authenticity or UE visual quality.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import bpy

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
    assert tile_type in ("hira-gawara pan","mune-maru cover")
    cell=obj["tile_variant"]
    lo_u, hi_u=(cell%4)/4,(cell%4+1)/4
    lo_v, hi_v=(cell//4)/4,(cell//4+1)/4
    for loop in obj.data.uv_layers.active.data:
        u,v=loop.uv
        assert lo_u+0.003 <= u <= hi_u-0.003, (obj.name,u)
        assert lo_v+0.003 <= v <= hi_v-0.003, (obj.name,v)
    triangles += 2*len(obj.data.polygons)
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
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(OUT/"SM_Nyaagyu_KawaraBay.fbx"))
imported={o.name:o for o in bpy.context.scene.objects if o.type=="MESH"}
assert set(imported)==set(source_meshes), (set(imported)-set(source_meshes),set(source_meshes)-set(imported))
for name,obj in imported.items():
    assert len(obj.data.polygons)==source_counts[name], name
    if name.startswith(("HiraGawara","MaruGawara")):
        assert obj.data.uv_layers.active is not None, name
print(json.dumps({"status":"passed source/FBX checks; not UE art approval",
                  "tile_count":len(pans)+len(covers),"tile_triangles":triangles,
                  "atlas_variants":len(variants),"fbx_meshes":len(imported)},indent=2))
