"""Independently validate the Kura front source, PBR provenance, and FBX roundtrip.

Run with Blender 5.2.2 LTS from the repository root:
  blender -b --factory-startup --python scripts/art/validate_nyaagyu_kura_front.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Environment/NyaagyuKuraFront"
manifest = json.loads((OUT / "manifest.json").read_text())
texture_manifest = json.loads((OUT / "texture_manifest.json").read_text())
palette = json.loads((ROOT / "Content/SourceArt/Environment/PolyHaven/manifest.json").read_text())


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert manifest["schema_version"] == texture_manifest["schema_version"] == 1
assert manifest["name"] == "SM_Nyaagyu_KuraFront_Candidate"
assert manifest["generator_sha256"] == sha(ROOT / manifest["generator"])
assert manifest["base_source_sha256"] == sha(ROOT / manifest["base_source"])
assert manifest["texture_manifest_sha256"] == sha(OUT / manifest["texture_manifest"])
for field, digest in (("source_blend", "source_blend_sha256"),
                      ("fbx", "fbx_sha256"), ("preview", "preview_sha256"),
                      ("baseline_preview", "baseline_preview_sha256")):
    assert sha(OUT / manifest[field]) == manifest[digest], field
assert texture_manifest["license"].startswith("Derived from Rob Tuytel")
asset = next(x for x in palette["assets"] if x["asset_id"] == "wood_planks_dirt")
assert asset["license"] == "CC0-1.0"
for role, item in texture_manifest["source_files"].items():
    assert sha(ROOT / item["file"]) == item["sha256"], role
    assert item["sha256"] in {x["sha256"] for x in asset["files"]}, role
for role, item in texture_manifest["atlas_files"].items():
    assert sha(OUT / item["file"]) == item["sha256"], role
assert texture_manifest["board_count"] == manifest["door_board_count"] == 14
assert texture_manifest["normal_convention"].startswith("DirectX")
assert "collision" in manifest and "Visual only" in manifest["collision"]
world = (ROOT / "Source/SoraArena/Private/SoraWorldBuilder.cpp").read_text()
assert manifest["name"] not in world, "Candidate was admitted to runtime unexpectedly"

bpy.ops.wm.open_mainfile(filepath=str(OUT / manifest["source_blend"]))
editable = bpy.data.collections["Nyaagyu_ProvisionKura_Editable"]
retro = bpy.data.collections["KuraFront_Editable_PatinaAndJoinery"]
source = [o for coll in (editable,retro) for o in coll.objects if o.type == "MESH"]
assert len(source) == manifest["source_parts"]
assert sum(len(p.vertices)-2 for o in source for p in o.data.polygons) == manifest["source_triangles"]
assert not [o for o in editable.objects if o.name.startswith(("LoadingDoor_", "Door_PlankSeam_", "Door_CrossRail_"))]
boards = sorted((o for o in retro.objects if o.name.startswith("CedarPlank_")), key=lambda o:o.name)
assert len(boards) == 14, len(boards)
for i, board in enumerate(boards):
    assert board.name == f"CedarPlank_{i:02d}"
    assert "UV0" in board.data.uv_layers, board.name
    assert len(board.data.polygons) >= 28, board.name
    us = [loop.uv.x for loop in board.data.uv_layers["UV0"].data]
    vs = [loop.uv.y for loop in board.data.uv_layers["UV0"].data]
    assert min(us) >= i/14-.0001 and max(us) <= (i+1)/14+.0001
    assert min(vs) >= -.01 and max(vs) <= 1.01
    assert any(m and m.name == "M_KuraFront_CC0CedarAtlas" for m in board.data.materials)
assert len([o for o in retro.objects if o.name.startswith("Hammered_Strap_")]) == 6
assert len([o for o in retro.objects if o.name.startswith("Peened_Rivet_")]) == 24
assert len([o for o in retro.objects if o.name.startswith("Forged_PullRing_")]) == 2

for image in bpy.data.images:
    if image.source == "FILE" and image.name.startswith("T_KuraFront_"):
        path = Path(bpy.path.abspath(image.filepath)).resolve()
        assert path.is_file() and path.is_relative_to(OUT.resolve()), image.name

# A fresh Blender FBX import checks that the shipped mesh, not only its source
# parts, retains physical bounds, explicit UVs and exact material identities.
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
for material in list(bpy.data.materials):
    bpy.data.materials.remove(material)
before = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=str(OUT / manifest["fbx"]), use_custom_normals=False)
imported = [o for o in set(bpy.data.objects)-before if o.type == "MESH"]
assert len(imported) == 1, [o.name for o in imported]
mesh = imported[0]
assert not mesh.name.startswith("UCX_")
assert "UV0" in mesh.data.uv_layers, [x.name for x in mesh.data.uv_layers]
slots = {m.name for m in mesh.data.materials if m}
assert "M_KuraFront_CC0CedarAtlas" in slots, slots
assert "M_KuraFront_ForgedIron" in slots, slots
assert mesh.data.uv_layers[0].name == "UVMap", [x.name for x in mesh.data.uv_layers]
cedar_index = next(i for i,m in enumerate(mesh.data.materials)
                   if m and m.name == "M_KuraFront_CC0CedarAtlas")
cedar_faces = [face for face in mesh.data.polygons if face.material_index == cedar_index]
assert len(cedar_faces) >= 400, len(cedar_faces)
cedar_u = [mesh.data.uv_layers[0].data[i].uv.x
           for face in cedar_faces for i in face.loop_indices]
cedar_v = [mesh.data.uv_layers[0].data[i].uv.y
           for face in cedar_faces for i in face.loop_indices]
assert min(cedar_u) <= .005 and max(cedar_u) >= .995, (min(cedar_u),max(cedar_u))
assert min(cedar_v) <= .005 and max(cedar_v) >= .995, (min(cedar_v),max(cedar_v))
assert min(cedar_u) >= -.01 and max(cedar_u) <= 1.01
assert min(cedar_v) >= -.01 and max(cedar_v) <= 1.01
bounds = {"min":[min((mesh.matrix_world @ Vector(c))[axis] for c in mesh.bound_box)
                 for axis in range(3)],
          "max":[max((mesh.matrix_world @ Vector(c))[axis] for c in mesh.bound_box)
                 for axis in range(3)]}
for end in ("min", "max"):
    for got, expected in zip(bounds[end], manifest["bounds_m"][end]):
        assert abs(got-expected) <= .015, (end,got,expected)
roundtrip_triangles = sum(len(p.vertices)-2 for p in mesh.data.polygons)
assert abs(roundtrip_triangles-manifest["source_triangles"]) <= manifest["source_triangles"]*.02, roundtrip_triangles

report = {
    "result": "PASS",
    "source_parts": len(source),
    "source_triangles": manifest["source_triangles"],
    "board_uv0": 14,
    "fbx_cedar_channel0_uv_extent": {
        "u": [min(cedar_u), max(cedar_u)],
        "v": [min(cedar_v), max(cedar_v)],
        "polygons": len(cedar_faces),
    },
    "forged_straps": 6,
    "fbx_roundtrip_objects": len(imported),
    "fbx_roundtrip_polygons": len(mesh.data.polygons),
    "fbx_roundtrip_triangles": roundtrip_triangles,
    "fbx_bounds_m": bounds,
    "source_only": True,
}
(OUT / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
print("NYAAGYU_KURA_FRONT_VALIDATION_PASS", json.dumps(report), flush=True)
