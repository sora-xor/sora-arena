"""Check the editable UV variant and PBR FBX round-trip in Blender 5.2 LTS.

Run: blender -b --factory-startup --python scripts/art/validate_nyaagyu_horse_pbr_variant.py
"""

from __future__ import annotations

import atexit
import hashlib
import json
import os
from pathlib import Path
import sys

import bpy
from mathutils import Vector


passed = False


def require_success():
    if not passed:
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(1)


atexit.register(require_success)
ROOT = Path(__file__).resolve().parents[2]
HORSE = ROOT / "Content/SourceArt/Horses/Nyaagyu"
PBR = HORSE / "PBR"
base = json.loads((HORSE / "manifest.json").read_text())
record = json.loads((PBR / "variant_manifest.json").read_text())


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_meshes():
    return sorted((obj for obj in bpy.data.collections["NyaagyuHorse_Editable"].objects
                   if obj.type == "MESH"), key=lambda o: o.name)


def geometry_fingerprint(meshes):
    digest = hashlib.sha256()
    for obj in meshes:
        digest.update(obj.name.encode())
        digest.update("|".join(material.name for material in obj.data.materials).encode())
        for vert in obj.data.vertices:
            point = obj.matrix_world @ vert.co
            digest.update(("%.7f,%.7f,%.7f;" % tuple(point)).encode())
        for poly in obj.data.polygons:
            digest.update((",".join(str(index) for index in poly.vertices) + ";").encode())
    return digest.hexdigest()


assert bpy.app.version[:2] == (5, 2)
assert record["schema_version"] == 1
assert record["base_blend_sha256"] == base["blend_sha256"]
assert record["base_fbx_sha256"] == base["fbx_sha256"]
assert record["pbr_manifest_sha256"] == sha(PBR / "manifest.json")
assert record["sora_logo_sha256"] == base["insignia_sha256"]
assert record["source_parts"] == base["source_parts"]
assert record["source_triangles"] == base["source_triangles"]
assert record["anchors_m"] == base["anchors_m"]
assert record["unreal_asset"] == (
    "/Game/ArtReview/Horses/NyaagyuPBR/SM_Nyaagyu_HorseAndTack_PBR."
    "SM_Nyaagyu_HorseAndTack_PBR"
)
for filename, key in ((record["blend"], "blend_sha256"),
                      (record["fbx"], "fbx_sha256"),
                      (record["review"], "review_sha256")):
    path = PBR / filename
    assert path.stat().st_size > 1000
    assert sha(path) == record[key], path

bpy.ops.wm.open_mainfile(filepath=str(HORSE / base["source_blend"]))
original = geometry_fingerprint(source_meshes())
assert original == record["source_geometry_sha256"]
bpy.ops.wm.open_mainfile(filepath=str(PBR / record["blend"]))
meshes = source_meshes()
assert len(meshes) == record["source_parts"]
assert geometry_fingerprint(meshes) == original
assert all(obj.data.uv_layers.get("Nyaagyu_PBR_UV") for obj in meshes)
assert all(len(obj.data.uv_layers["Nyaagyu_PBR_UV"].data) == len(obj.data.loops)
           for obj in meshes)
assert sorted(obj.name for obj in meshes if obj.name.startswith("SORA_kamon_exact_svg_")) == record["exact_sora_kamon_objects"]
assert all(obj["source_svg_sha256"] == base["insignia_sha256"]
           for obj in meshes if obj.name.startswith("SORA_kamon_exact_svg_"))
for name, position in record["anchors_m"].items():
    obj = bpy.data.collections["NyaagyuHorse_Editable"].objects.get(name)
    assert obj and obj.type == "EMPTY"
    assert all(abs(obj.location[i] - position[i]) < 1e-5 for i in range(3))

texture_record = json.loads((PBR / "manifest.json").read_text())
for slot in texture_record["material_slots"]:
    material = bpy.data.materials[slot]
    images = [node.image for node in material.node_tree.nodes if node.type == "TEX_IMAGE"]
    assert len(images) == 3
    assert all(image.packed_file is not None for image in images)

fbx = PBR / record["fbx"]
assert fbx.read_bytes().startswith(b"Kaydara FBX Binary")
assert b"/Users/" not in fbx.read_bytes()
before = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=str(fbx))
imported = [obj for obj in set(bpy.data.objects) - before if obj.type == "MESH"]
assert len(imported) == 1, imported
mesh = imported[0]
assert mesh.name.startswith("SM_Nyaagyu_HorseAndTack_PBR")
assert mesh.data.uv_layers and len(mesh.data.uv_layers[0].data) == len(mesh.data.loops)
slots = sorted(slot.material.name.split(".", 1)[0] for slot in mesh.material_slots)
assert slots == record["material_slots"]
assert len(slots) == 17
corners = [mesh.matrix_world @ Vector(corner) for corner in mesh.bound_box]
for axis in range(3):
    assert abs(min(point[axis] for point in corners) - base["bounds_m"]["min"][axis]) < .025
    assert abs(max(point[axis] for point in corners) - base["bounds_m"]["max"][axis]) < .025
print("NYAAGYU_HORSE_PBR_VARIANT_ROUNDTRIP_PASS", len(meshes), slots)
passed = True
