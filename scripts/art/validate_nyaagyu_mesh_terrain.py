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
assert manifest["density"]["mac"]["quads_per_tile"]==[32,26]
assert manifest["density"]["hi"]["quad_spacing_cm"]==12.5
assert manifest["density"]["mac"]["quad_spacing_cm"]==50
assert manifest["macro_tint"]["vertex_color_attribute"]=="EstateMacroTint"
assert manifest["palette_license"].startswith("CC0-1.0")
assert "No UE 5.8.2 import" in manifest["limitations"]
for filename,field in ((manifest["source_blend"],"source_blend_sha256"),
                       (manifest["preview"],"preview_sha256"),
                       (manifest["detail_preview"],"detail_preview_sha256")):
    path=out/filename
    assert path.stat().st_size>1000,path
    assert hashlib.sha256(path.read_bytes()).hexdigest()==manifest[field],path
palette=root/"Content/SourceArt/Environment/PolyHaven/manifest.json"
assert (out/manifest["palette_manifest"]).resolve()==palette.resolve()
palette_manifest=json.loads(palette.read_text())
assert palette_manifest["asset_license"]=="CC0-1.0"
assert len(manifest["palette_files"])==7
displacement=[item for item in manifest["palette_files"]
              if item["role"]=="stone" and item["channel"]=="displacement"]
assert len(displacement)==1
assert displacement[0]["upstream_md5"]=="8413a85bb5748cabf486b5593daf7c33"
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
            tint=obj.data.color_attributes.get("EstateMacroTint")
            assert tint is not None and tint.domain=="CORNER"
            assert len(tint.data)==len(obj.data.loops)
            red=[sample.color[0] for sample in tint.data]
            assert .55<min(red)<1.15 and .65<max(red)<1.2
            assert max(red)-min(red)>.06
            fbx=out/t["fbx"]
            assert fbx.stat().st_size>2000
            fbx_bytes=fbx.read_bytes()
            assert fbx_bytes.startswith(b"Kaydara FBX Binary")
            assert hashlib.sha256(fbx_bytes).hexdigest()==t["fbx_sha256"]
            assert b"/Users/" not in fbx_bytes
            before=set(bpy.data.objects)
            bpy.ops.import_scene.fbx(filepath=str(fbx),colors_type="LINEAR")
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
            imported_tint=model.data.color_attributes.get("EstateMacroTint")
            assert imported_tint is not None and imported_tint.domain=="CORNER"
            assert len(imported_tint.data)==len(model.data.loops)
            imported_red=[sample.color[0] for sample in imported_tint.data]
            assert abs(min(red)-min(imported_red))<.001
            assert abs(max(red)-max(imported_red))<.001
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

# The road is no longer a flat blockout: the licensed stone displacement
# creates measurable (but sub-centimetre) relief in its central band.
stone_tile=mesh_by_key[("hi",1,1)]
stone_height_cm=[v.co.z*100 for v in stone_tile.data.vertices
                 if abs(v.co.y+stone_tile.location.y)<2]
assert max(stone_height_cm)-min(stone_height_cm)>.25

# Every Mac vertex coincides with the corresponding fourth dense sample.
for iy in range(4):
    for ix in range(4):
        hi=mesh_by_key[("hi",ix,iy)].data.vertices
        low=mesh_by_key[("mac",ix,iy)].data.vertices
        for j in range(27):
            for i in range(33):
                a=hi[(j*4)*129+i*4].co
                b=low[j*33+i].co
                assert all(abs(a[k]-b[k])<1e-6 for k in range(3))

print("NYAAGYU_MESH_TERRAIN_FBX_ROUNDTRIP_PASS",len(tiles),
      sum(t["triangles"] for t in tiles if t["tier"]=="hi"),
      sum(t["triangles"] for t in tiles if t["tier"]=="mac"))
validated=True
