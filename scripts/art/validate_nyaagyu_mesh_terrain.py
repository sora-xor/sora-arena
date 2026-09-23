"""Independent geometry/hash/license/FBX round-trip checks for Estate tiles.

Run: blender -b Content/SourceArt/Environment/NyaagyuTerrain/\
Nyaagyu_Estate_MeshTerrain_Source.blend --python \
scripts/art/validate_nyaagyu_mesh_terrain.py
"""

import atexit
import hashlib
import json
import os
import sys
from pathlib import Path

import bpy
from mathutils import Vector


validated=False
def fail_exit():
    if not validated:
        sys.stdout.flush();sys.stderr.flush();os._exit(1)
atexit.register(fail_exit)

root=Path(__file__).resolve().parents[2]
out=root/"Content/SourceArt/Environment/NyaagyuTerrain"
manifest=json.loads((out/"manifest.json").read_text())
assert bpy.app.version[:2]==(5,2)
assert Path(bpy.data.filepath).resolve()==(out/manifest["source_blend"]).resolve()
assert manifest["schema_version"]==1
assert manifest["generator"]=="scripts/art/create_nyaagyu_mesh_terrain.py"
assert manifest["validator"]=="scripts/art/validate_nyaagyu_mesh_terrain.py"
assert manifest["world_xy_cm"]==[-3200,-2600,3200,2600]
assert manifest["tile_layout"]==[4,4]
assert manifest["tile_size_cm"]==[1600,1300]
assert manifest["density"]["hi"]["quads_per_tile"]==[128,104]
assert manifest["density"]["mac"]["quads_per_tile"]==[16,13]
assert manifest["density"]["hi"]["quad_spacing_cm"]==12.5
assert manifest["density"]["mac"]["quad_spacing_cm"]==100
assert manifest["palette_license"].startswith("CC0-1.0")
assert "No UE 5.8.2 import" in manifest["limitations"]
for filename,field in ((manifest["source_blend"],"source_blend_sha256"),
                       (manifest["preview"],"preview_sha256")):
    path=out/filename
    assert path.stat().st_size>1000,path
    assert hashlib.sha256(path.read_bytes()).hexdigest()==manifest[field],path
palette=root/"Content/SourceArt/Environment/PolyHaven/manifest.json"
assert (out/manifest["palette_manifest"]).resolve()==palette.resolve()
palette_manifest=json.loads(palette.read_text())
assert palette_manifest["asset_license"]=="CC0-1.0"
assert len(manifest["palette_files"])==6
for item in manifest["palette_files"]:
    path=root/item["path"]
    assert path.stat().st_size==item["bytes"],path
    assert hashlib.sha256(path.read_bytes()).hexdigest()==item["sha256"],path
for image in bpy.data.images:
    if image.source=="FILE":
        assert image.filepath.startswith("//../PolyHaven/"),image.filepath
        assert Path(bpy.path.abspath(image.filepath)).resolve().is_file()

assert set(manifest["material_slots"])=={
    "M_Terrain_Soil_PolyHaven","M_Terrain_Stone_PolyHaven"}
tiles=manifest["tiles"]
assert len(tiles)==32
assert len({t["name"] for t in tiles})==32
assert len({t["fbx"] for t in tiles})==32
by_key={(t["tier"],*t["index"]):t for t in tiles}
assert set(by_key)=={(tier,x,y) for tier in ("hi","mac")
                    for x in range(4) for y in range(4)}
mesh_by_key={}
for tier in ("hi","mac"):
    collection=bpy.data.collections.get(
        "EstateTerrain_HighDensity_NaniteCandidate" if tier=="hi"
        else "EstateTerrain_ConventionalMacCandidate")
    assert collection is not None
    assert len([o for o in collection.objects if o.type=="MESH"])==16
    nx,ny=manifest["density"][tier]["quads_per_tile"]
    for iy in range(4):
        for ix in range(4):
            t=by_key[(tier,ix,iy)]
            obj=collection.objects.get(t["source_object"])
            assert obj and obj.type=="MESH",t
            mesh_by_key[(tier,ix,iy)]=obj
            assert tuple(obj["world_tile_index"])==(ix,iy)
            assert obj["asset_tier"]==tier
            assert len(obj.data.vertices)==(nx+1)*(ny+1)
            assert len(obj.data.polygons)==nx*ny
            assert t["sample_grid"]==[nx+1,ny+1]
            assert t["triangles"]==2*nx*ny
            expected_center=(-2400+1600*ix,-1950+1300*iy,0)
            assert t["placement_center_cm"]==list(expected_center)
            assert all(abs(obj.location[k]*100-expected_center[k])<.001
                       for k in range(3))
            expected_bounds=[-3200+1600*ix,-2600+1300*iy,
                             -1600+1600*ix,-1300+1300*iy]
            assert t["world_bounds_xy_cm"]==expected_bounds
            z=[v.co.z*100 for v in obj.data.vertices]
            assert abs(min(z)-t["z_range_cm"][0])<.0002
            assert abs(max(z)-t["z_range_cm"][1])<.0002
            assert min(z)>0 and max(z)<manifest["max_visual_collision_delta_cm"]
            assert len(obj.data.materials)==2
            assert [m.name for m in obj.data.materials]==manifest["material_slots"]
            assert len(obj.data.uv_layers)==1
            fbx=out/t["fbx"]
            assert fbx.stat().st_size>2000
            fbx_bytes=fbx.read_bytes()
            assert fbx_bytes.startswith(b"Kaydara FBX Binary")
            assert hashlib.sha256(fbx_bytes).hexdigest()==t["fbx_sha256"]
            assert b"/Users/" not in fbx_bytes
            before=set(bpy.data.objects)
            bpy.ops.import_scene.fbx(filepath=str(fbx))
            imported=[o for o in set(bpy.data.objects)-before if o.type=="MESH"]
            assert len(imported)==1,[o.name for o in imported]
            model=imported[0]
            assert model.name.startswith(t["name"]),model.name
            box=[model.matrix_world @ Vector(c) for c in model.bound_box]
            assert abs(min(v.x for v in box)+8)<.0005
            assert abs(max(v.x for v in box)-8)<.0005
            assert abs(min(v.y for v in box)+6.5)<.0005
            assert abs(max(v.y for v in box)-6.5)<.0005
            tri=sum(len(poly.vertices)-2 for poly in model.data.polygons)
            assert tri==t["triangles"],(tier,ix,iy,tri)
            slots={s.material.name.split(".",1)[0] for s in model.material_slots}
            assert slots==set(manifest["material_slots"]),slots
            bpy.data.objects.remove(model,do_unlink=True)

# Exact edge heights are independently checked at all thirty internal seams.
for tier in ("hi","mac"):
    nx,ny=manifest["density"][tier]["quads_per_tile"]
    for iy in range(4):
        for ix in range(4):
            here=mesh_by_key[(tier,ix,iy)].data.vertices
            if ix<3:
                east=mesh_by_key[(tier,ix+1,iy)].data.vertices
                for j in range(ny+1):
                    assert abs(here[j*(nx+1)+nx].co.z-east[j*(nx+1)].co.z)<1e-6
            if iy<3:
                north=mesh_by_key[(tier,ix,iy+1)].data.vertices
                for i in range(nx+1):
                    assert abs(here[ny*(nx+1)+i].co.z-north[i].co.z)<1e-6

# Every Mac vertex coincides with the corresponding eighth dense sample.
for iy in range(4):
    for ix in range(4):
        hi=mesh_by_key[("hi",ix,iy)].data.vertices
        low=mesh_by_key[("mac",ix,iy)].data.vertices
        for j in range(14):
            for i in range(17):
                a=hi[(j*8)*129+i*8].co
                b=low[j*17+i].co
                assert all(abs(a[k]-b[k])<1e-6 for k in range(3))

print("NYAAGYU_MESH_TERRAIN_FBX_ROUNDTRIP_PASS",len(tiles),
      sum(t["triangles"] for t in tiles if t["tier"]=="hi"),
      sum(t["triangles"] for t in tiles if t["tier"]=="mac"))
validated=True
