"""Validate pinned CC0 pine source, PBR maps and six FBX mesh tiers.

Run: blender -b --factory-startup --python scripts/art/validate_nyaagyu_pine_saplings.py
"""

import atexit
import hashlib
import json
import os
import sys
from pathlib import Path

import bpy
from mathutils import Vector


passed = False


def fail_on_exception():
    if not passed:
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(1)


atexit.register(fail_on_exception)
ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "Content/SourceArt/Environment/PolyHaven/PineSaplingSmall"
record = json.loads((ART / "manifest.json").read_text())
assert record["schema_version"] == 1
assert record["asset_id"] == "pine_sapling_small"
assert record["upstream_page"] == "https://polyhaven.com/a/pine_sapling_small"
assert record["license"] == "CC0-1.0; https://polyhaven.com/license"
assert record["generator"] == "scripts/art/create_nyaagyu_pine_saplings.py"
assert record["gameplay_collision"] is False
assert record["instances_in_nyaagyu_estate"] == 9
assert len(record["upstream_files"]) == 8
assert len(record["texture_files"]) == 8
assert len(record["meshes"]) == 6
assert record["material_slots"] == ["M_NyaagyuPine_Bark", "M_NyaagyuPine_Needles"]


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


for entry in record["upstream_files"] + record["texture_files"]:
    file = ART / entry["path"]
    assert file.is_file() and file.stat().st_size == entry["bytes"]
    assert sha(file) == entry["sha256"]
assert any(item["path"].endswith("twig_mask_2k.png") for item in record["texture_files"])
for key, digest in (("source_blend", "source_blend_sha256"),
                    ("preview", "preview_sha256")):
    path = ART / record[key]
    assert path.is_file() and path.stat().st_size > 1000 and sha(path) == record[digest]
bpy.ops.wm.open_mainfile(filepath=str(ART / record["source_blend"]))
assert not list(bpy.data.libraries)
assert all(image.filepath.startswith("//") for image in bpy.data.images
           if image.source == "FILE")

for variant in "abc":
    entries = [entry for entry in record["meshes"] if entry["variant"] == variant]
    assert [entry["tier"] for entry in entries] == ["hi", "mac"]
    assert entries[1]["source_triangles"] < entries[0]["source_triangles"] * .35
    for entry in entries:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        name = f"SM_NyaagyuPine_{variant.upper()}_{entry['tier'].upper()}"
        assert entry["name"] == name and entry["fbx"] == name + ".fbx"
        assert entry["nanite"] == (entry["tier"] == "hi")
        assert entry["unreal_asset"] == f"/Game/Generated/Environment/Foliage/{name}.{name}"
        fbx = ART / entry["fbx"]
        assert fbx.read_bytes().startswith(b"Kaydara FBX Binary")
        assert b"/Users/" not in fbx.read_bytes()
        assert sha(fbx) == entry["fbx_sha256"]
        bpy.ops.import_scene.fbx(filepath=str(fbx))
        meshes = [obj for obj in bpy.data.objects if obj.type == "MESH"]
        assert len(meshes) == 1
        mesh = meshes[0]
        count = sum(len(face.vertices) - 2 for face in mesh.data.polygons)
        assert count == entry["source_triangles"]
        assert sorted(mat.name for mat in mesh.data.materials) == record["material_slots"]
        assert len(mesh.data.uv_layers) >= 1
        corners = [mesh.matrix_world @ Vector(corner) for corner in mesh.bound_box]
        for axis in range(3):
            low = min(point[axis] for point in corners)
            high = max(point[axis] for point in corners)
            assert abs(low - entry["bounds_m"]["min"][axis]) < .012
            assert abs(high - entry["bounds_m"]["max"][axis]) < .012
        print("NYAAGYU_PINE_FBX_PASS", variant, entry["tier"], count, flush=True)

passed = True
