"""Independent Blender round-trip of the pinned CC0 Nyaagyu foliage tiers.

Run with `blender -b --python scripts/art/validate_nyaagyu_photoreal_tree.py`.
This checks source provenance and game-ready meshes; an Unreal screenshot and
frame-time measurement are separate release requirements.
"""
import hashlib
import json
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "Content/SourceArt/Environment/PolyHaven/TreeSmall02"
manifest = json.loads((ART / "manifest.json").read_text())
assert manifest["schema_version"] == 1
assert manifest["asset_id"] == "tree_small_02"
assert manifest["upstream_page"] == "https://polyhaven.com/a/tree_small_02"
assert manifest["license"] == "CC0-1.0; https://polyhaven.com/license"
assert manifest["gameplay_collision"] is False
assert manifest["instances_in_nyaagyu_estate"] == 10
assert len(manifest["meshes"]) == 2
assert len(manifest["texture_files"]) == 10
assert len(manifest["upstream_files"]) == 11
assert manifest["material_slots"] == [
    "M_NyaagyuTree_Branches", "M_NyaagyuTree_Leaves", "M_NyaagyuTree_Trunk"]


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


for file in manifest["upstream_files"] + manifest["texture_files"]:
    path = ART / file["path"]
    assert path.is_file() and path.stat().st_size == file["bytes"]
    assert digest(path) == file["sha256"], path
for key, digest_key in (("source_blend", "source_blend_sha256"),
                        ("preview", "preview_sha256")):
    path = ART / manifest[key]
    assert path.stat().st_size > 1000 and digest(path) == manifest[digest_key]

for tier, entry in zip(("hi", "mac"), manifest["meshes"]):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    name = f"SM_NyaagyuTree_{tier.upper()}"
    path = ART / entry["fbx"]
    assert entry["tier"] == tier and entry["name"] == name
    assert entry["nanite"] == (tier == "hi")
    assert entry["unreal_asset"] == f"/Game/Generated/Environment/Foliage/{name}.{name}"
    assert path.read_bytes().startswith(b"Kaydara FBX Binary")
    assert b"/Users/" not in path.read_bytes()
    assert digest(path) == entry["fbx_sha256"]
    bpy.ops.import_scene.fbx(filepath=str(path))
    meshes = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    assert len(meshes) == 1, (tier, len(meshes))
    obj = meshes[0]
    count = sum(len(poly.vertices) - 2 for poly in obj.data.polygons)
    assert count == entry["source_triangles"], (tier, count, entry["source_triangles"])
    assert sorted(mat.name for mat in obj.data.materials) == sorted(manifest["material_slots"])
    assert len(obj.data.uv_layers) >= 1
    bounds = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    low = [min(v[i] for v in bounds) for i in range(3)]
    high = [max(v[i] for v in bounds) for i in range(3)]
    assert abs(high[2] - entry["bounds_m"]["max"][2]) < .02, (tier, high)
    assert abs(low[2] - entry["bounds_m"]["min"][2]) < .02, (tier, low)
    assert 4.45 < high[2] < 4.7
    assert low[2] > -.1
    if tier == "hi":
        assert 250000 < count < 400000
    else:
        assert 60000 < count < 130000
    print("SORA_TREE_ROUNDTRIP", tier, count, [round(x, 3) for x in low],
          [round(x, 3) for x in high], flush=True)

print("SORA_PHOTOREAL_TREE_SOURCE_VALIDATED", flush=True)
