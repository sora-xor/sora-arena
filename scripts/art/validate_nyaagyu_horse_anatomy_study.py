"""Validate the isolated Nyaagyu horse art study, including an FBX roundtrip."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"Content/SourceArt/Horses/Nyaagyu/AnatomyStudy"
MANIFEST=json.loads((OUT/"manifest.json").read_text())
TEXTURES=json.loads((OUT/"textures_manifest.json").read_text())


def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inside_blender():
    import bpy
    from mathutils import Vector

    bpy.ops.wm.open_mainfile(filepath=str(OUT/MANIFEST["source_blend"]))
    anatomy=bpy.data.collections["AnatomyStudy_Editable"]
    tack=bpy.data.collections["NyaagyuHorse_Editable"]
    meshes=[o for o in (*anatomy.objects,*tack.objects) if o.type=="MESH"]
    assert len(meshes)==MANIFEST["editable_mesh_parts"]
    assert all(o.data.uv_layers and o.data.uv_layers[0].name=="UV0" for o in meshes)
    assert all(o.data.uv_layers[0].data for o in meshes)
    triangles=sum(len(face.vertices)-2 for o in meshes for face in o.data.polygons)
    assert triangles==MANIFEST["triangles"]
    core=bpy.data.objects["HorseStudy_anatomical_core"]
    assert len(core.data.vertices)==MANIFEST["anatomical_core_vertices"]
    core_vertices=len(core.data.vertices)
    assert core.data.vertex_colors.get("CoatVariation") is not None
    assert len(core.data.vertices)>50000
    assert all(bpy.data.objects.get(f"HorseStudy_{kind}_hoof_{side}")
               for side in (-1,1) for kind in ("fore","hind"))
    for obj in tack.objects:
        if obj.name.startswith("SORA_kamon_exact_svg_"):
            assert obj["source_svg_sha256"]==MANIFEST["sora_logo_sha256"]
    assert len([o for o in tack.objects if o.name.startswith("SORA_kamon_exact_svg_")])==8
    for anchor in ("Horse_Root","Saddle_RiderSeat","Tazuna_LeftGrip",
                   "Tazuna_RightGrip","Abumi_LeftFoot","Abumi_RightFoot"):
        assert tack.objects.get(anchor) and tack.objects[anchor].type=="EMPTY"
    for material_name in MANIFEST["texture_slots"]:
        material=bpy.data.materials[material_name]
        names={node.name for node in material.node_tree.nodes}
        assert {"AnatomyStudy_Albedo","AnatomyStudy_ORM","AnatomyStudy_NormalDX"}<=names
    assert bpy.data.objects.get("SM_Nyaagyu_Horse_AnatomyStudy")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(OUT/MANIFEST["fbx"]))
    imported=[o for o in bpy.data.objects if o.type=="MESH"]
    assert len(imported)==1,[(o.name,o.type) for o in bpy.data.objects]
    fbx=imported[0]
    assert fbx.data.uv_layers and fbx.data.uv_layers[0].name=="UV0"
    assert len(fbx.data.polygons)>100000
    assert len(fbx.data.materials)>=15
    bounds=[fbx.matrix_world@Vector(c) for c in fbx.bound_box]
    extent=[max(p[i] for p in bounds)-min(p[i] for p in bounds) for i in range(3)]
    assert max(extent)>1.5 and min(extent)>.30,extent
    print("NYAAGYU_HORSE_ANATOMY_BLENDER_VALID",len(meshes),triangles,
          core_vertices,len(fbx.data.polygons))


def host():
    from PIL import Image
    import numpy as np

    baseline=ROOT/MANIFEST["baseline_blend"]
    assert sha(baseline)==MANIFEST["baseline_blend_sha256"]
    assert sha(OUT/"textures_manifest.json")==MANIFEST["texture_manifest_sha256"]
    for key,file_key,hash_key in (("blend","source_blend","source_blend_sha256"),
                                  ("fbx","fbx","fbx_sha256")):
        path=OUT/MANIFEST[file_key]
        assert path.stat().st_size>100000,key
        assert sha(path)==MANIFEST[hash_key],key
    for item in MANIFEST["preview_files"]:
        path=OUT/item["file"]
        assert path.stat().st_size>100000
        assert sha(path)==item["sha256"]
        with Image.open(path) as image:
            assert image.size==(1400,960)
    assert sha(ROOT/TEXTURES["base_coat_albedo"])==TEXTURES["base_coat_albedo_sha256"]
    assert set(TEXTURES["sets"])=={"coat_study","hoof_horn_study","oxblood_urushi_study"}
    for entries in TEXTURES["sets"].values():
        assert {e["channel"] for e in entries}=={"Albedo","NormalDX","ORM"}
        for entry in entries:
            path=OUT/entry["file"]
            assert sha(path)==entry["sha256"]
            with Image.open(path) as image:
                assert image.size==(2048,2048) and image.mode=="RGB"
                pixels=np.asarray(image)
                assert np.array_equal(pixels[0],pixels[-1]),path
                assert np.array_equal(pixels[:,0],pixels[:,-1]),path

    run=subprocess.run(["blender","-b","--factory-startup","--python",str(Path(__file__)),
                        "--","--inside-blender"],cwd=ROOT,text=True,capture_output=True,timeout=180)
    assert run.returncode==0 and "NYAAGYU_HORSE_ANATOMY_BLENDER_VALID" in run.stdout,(
        run.returncode,run.stdout[-5000:],run.stderr[-5000:])
    print(run.stdout.split("NYAAGYU_HORSE_ANATOMY_BLENDER_VALID",1)[1].splitlines()[0].strip())
    print("NYAAGYU_HORSE_ANATOMY_STUDY_VALID",MANIFEST["editable_mesh_parts"],
          MANIFEST["triangles"],len(MANIFEST["preview_files"]))


if __name__=="__main__":
    if "--inside-blender" in sys.argv:
        inside_blender()
    else:
        host()
