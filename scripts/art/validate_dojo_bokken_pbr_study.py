"""Validate the editable bokken PBR study and independently imported FBX."""

from __future__ import annotations

import atexit
import hashlib
import json
import os
import sys
from pathlib import Path

import bpy


passed = False


def fail_exit():
    if not passed:
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(1)


atexit.register(fail_exit)
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "Content/SourceArt/Weapons/Original"
OUT = ROOT / "Content/SourceArt/Weapons/DojoBokkenPBR"
base = json.loads((BASE / "manifest.json").read_text())
texture = json.loads((OUT / "texture_manifest.json").read_text())
record = json.loads((OUT / "manifest.json").read_text())


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parts():
    return sorted((obj for obj in bpy.data.collections["DojoBokken_Editable"].objects
                   if obj.type == "MESH"), key=lambda obj: obj.name)


def geometry_fingerprint(objects) -> str:
    digest = hashlib.sha256()
    for obj in objects:
        digest.update(obj.name.encode())
        for vertex in obj.data.vertices:
            digest.update(("%.7f,%.7f,%.7f;" % tuple(obj.matrix_world @ vertex.co)).encode())
        for poly in obj.data.polygons:
            digest.update((",".join(str(value) for value in poly.vertices) + ";").encode())
    return digest.hexdigest()


assert bpy.app.version[:2] == (5, 2)
assert record["schema_version"] == texture["schema_version"] == 1
assert record["generator"] == "scripts/art/create_dojo_bokken_pbr_study.py"
assert record["base_blend_sha256"] == base["blend_sha256"] == sha(BASE / base["source_blend"])
assert record["base_fbx_sha256"] == base["fbx_sha256"] == sha(BASE / base["fbx"])
assert record["texture_manifest_sha256"] == sha(OUT / "texture_manifest.json")
assert record["source_parts"] == 16 and record["source_triangles"] == base["source_triangles"]
assert record["unreal_asset"] == ("/Game/Generated/ArtReview/DojoBokkenPBR/"
                                  "SM_Nyaagyu_DojoBokken_PBRStudy.SM_Nyaagyu_DojoBokken_PBRStudy")
assert "No gameplay promotion" in record["scope"]
assert texture["source_rights"].startswith("Project-generated")
assert sha(OUT / texture["source"]) == texture["source_sha256"]
for data in texture["maps"].values():
    assert data["resolution"] == [2048, 2048]
    assert sha(OUT / data["file"]) == data["sha256"]
for filename, key in ((record["source_blend"], "blend_sha256"),
                      (record["fbx"], "fbx_sha256"),
                      (record["preview"], "preview_sha256")):
    assert sha(OUT / filename) == record[key]

bpy.ops.wm.open_mainfile(filepath=str(BASE / base["source_blend"]))
original_geometry = geometry_fingerprint(parts())
assert original_geometry == record["geometry_sha256"]
bpy.ops.wm.open_mainfile(filepath=str(OUT / record["source_blend"]))
source_parts = parts()
assert geometry_fingerprint(source_parts) == original_geometry
assert len(source_parts) == 16
assert all(len(obj.data.uv_layers) == 1 and obj.data.uv_layers[0].name == "UV0"
           for obj in source_parts)
assert all(len(obj.data.uv_layers[0].data) == len(obj.data.loops) for obj in source_parts)
for name in record["material_slots"]:
    material = bpy.data.materials[name]
    image_nodes = [node for node in material.node_tree.nodes if node.type == "TEX_IMAGE"]
    assert len(image_nodes) == 3 and all(node.image.packed_file for node in image_nodes)

fbx_path = OUT / record["fbx"]
assert fbx_path.read_bytes().startswith(b"Kaydara FBX Binary")
assert b"/Users/" not in fbx_path.read_bytes()
before = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=str(fbx_path))
imported = [obj for obj in set(bpy.data.objects) - before if obj.type == "MESH"]
assert len(imported) == 1
mesh = imported[0].data
assert len(mesh.uv_layers) == 1 and mesh.uv_layers[0].name == "UV0"
assert len(mesh.uv_layers[0].data) == len(mesh.loops)
assert sum(len(face.vertices) - 2 for face in mesh.polygons) == record["source_triangles"]
slot_names = sorted(slot.material.name.split(".", 1)[0] for slot in imported[0].material_slots)
assert slot_names == record["material_slots"]
for material_name in ("M_Bokken_SeasonedWhiteOak", "M_Bokken_HandOiledGrip"):
    slot = next(index for index, entry in enumerate(imported[0].material_slots)
                if entry.material.name.split(".", 1)[0] == material_name)
    loops = [loop for face in mesh.polygons if face.material_index == slot
             for loop in face.loop_indices]
    u = [mesh.uv_layers[0].data[index].uv.x for index in loops]
    v = [mesh.uv_layers[0].data[index].uv.y for index in loops]
    assert max(u) - min(u) > .5 and max(v) - min(v) > .2, material_name

print("DOJO_BOKKEN_PBR_STUDY_PASS", len(source_parts), record["source_triangles"], slot_names)
passed = True
