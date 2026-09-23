"""Independent Blender FBX/source and provenance gate for the fern substrate.

Run: blender -b --factory-startup --python-exit-code 1 \
    --python scripts/art/validate_nyaagyu_fern_ground_transition.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import bpy


ROOT=Path(__file__).resolve().parents[2]
FERN=ROOT/"Content/SourceArt/Environment/PolyHaven/Fern02"
OUT=FERN/"GroundTransition"
record=json.loads((OUT/"manifest.json").read_text())


def sha(path):
    digest=hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda:stream.read(1024*1024),b""):
            digest.update(block)
    return digest.hexdigest()


assert record["schema_version"]==1
assert record["name"]=="SM_NyaagyuFernGroundTransition"
assert record["generator"]=="scripts/art/create_nyaagyu_fern_ground_transition.py"
assert sha(ROOT/record["generator"])==record["generator_sha256"]
assert record["gameplay_collision"] is False
assert record["nanite_windows"] is True
assert record["recommended_review_origin_cm"]==[-1950,335,0]
assert len(record["placements_local_m"])==6
assert sha(OUT/record["source_blend"])==record["source_blend_sha256"]
assert sha(FERN/"manifest.json")==record["fern_source_manifest_sha256"]
assert sha(ROOT/"Content/SourceArt/Environment/NyaagyuGroundDressing/manifest.json")==record["ground_dressing_manifest_sha256"]
assert set(record["scan_dependencies"])=={"DampSilt","ForestLitter","RiverStone"}
for dep in record["scan_dependencies"].values():
    assert dep["license"]=="CC0-1.0"
    assert dep["source_url"].startswith("https://polyhaven.com/a/")
    for item in dep["files"].values():
        path=ROOT/item["repo_path"]
        assert path.is_file() and sha(path)==item["sha256"]
        assert item["upstream_url"].startswith("https://dl.polyhaven.org/")
for tier in ("hi","mac_lod1"):
    preview=record["previews"][tier]
    assert sha(OUT/preview["file"])==preview["sha256"]

mesh_records=record["meshes"]
assert set(mesh_records)=={"hi","mac_lod1"}
assert mesh_records["hi"]["triangles"]>mesh_records["mac_lod1"]["triangles"]
for tier,item in mesh_records.items():
    path=OUT/item["fbx"]
    assert path.name==f"{record['name']}_{'HI' if tier=='hi' else 'MAC_LOD1'}.fbx"
    assert sha(path)==item["sha256"]
    assert item["nanite_candidate"]==(tier=="hi")
    assert item["material_slots"]==[
        "M_FernGround_Soil","M_FernGround_Litter","M_FernGround_Stone","M_FernGround_Root",
        "M_Fern02_4K" if tier=="hi" else "M_Fern02_2K"]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path))
    found=[obj for obj in bpy.data.objects if obj.type=="MESH"]
    assert len(found)==1,path
    obj=found[0]
    assert obj.name==path.stem
    assert sum(len(face.vertices)-2 for face in obj.data.polygons)==item["triangles"]
    assert [material.name for material in obj.data.materials]==item["material_slots"]
    assert len(obj.data.uv_layers)>=1
    assert len(obj.data.vertices)>3000
    assert obj.dimensions.x<3.8 and obj.dimensions.y<1.8 and obj.dimensions.z<.55
    print("FERN_GROUND_FBX_VALID",path.name,item["triangles"],flush=True)

bpy.ops.wm.open_mainfile(filepath=str(OUT/record["source_blend"]))
assert len([obj for obj in bpy.data.objects if obj.name.startswith("Fern_hi_")])==6
assert len([obj for obj in bpy.data.objects if obj.name.startswith("Fern_mac_")])==6
assert abs(bpy.context.scene.camera.location.z-1.56)<.001
for tier in ("4K","2K"):
    mat=bpy.data.materials[f"M_Fern02_{tier}"]
    shader=next(node for node in mat.node_tree.nodes if node.type=="BSDF_PRINCIPLED")
    alpha=shader.inputs["Alpha"].links
    assert len(alpha)==1 and f"alpha_{tier.lower()}" in alpha[0].from_node.image.filepath
    assert not mat.use_backface_culling
print("FERN_GROUND_SOURCE_VALID",len(record["placements_local_m"]),"contacted ferns; no gameplay collision",flush=True)
