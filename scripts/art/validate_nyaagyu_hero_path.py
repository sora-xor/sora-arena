"""Validate the editable hero-path source, scan derivation, and FBX round-trip.

Run: blender -b --factory-startup --python scripts/art/validate_nyaagyu_hero_path.py
This is source validation, not an Unreal cook or photorealism acceptance claim.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "Content/SourceArt/Environment/NyaagyuHeroPath"
record = json.loads((SOURCE / "manifest.json").read_text())
atlas = json.loads((SOURCE / "atlas_manifest.json").read_text())


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert record["schema_version"] == atlas["schema_version"] == 1
assert record["name"] == "SM_Nyaagyu_HeroStonePath_6m"
assert record["source_parts"] == record["individual_stones"] + 1 == 65
assert record["source_triangles"] >= 25000
assert record["collision"].startswith("Presentation only")
assert set(record["material_slots"]) == {"M_HeroPath_StoneFace", "M_HeroPath_StoneEdge", "M_HeroPath_SiltBed"}
assert record["generator_sha256"] == sha(ROOT / record["generator"])
assert atlas["generator_sha256"] == sha(ROOT / atlas["generator"])
assert record["atlas_manifest_sha256"] == sha(SOURCE / "atlas_manifest.json")
for item, digest in ((record["source_blend"], record["blend_sha256"]),
                     (record["fbx"], record["fbx_sha256"]),
                     (record["review"], record["review_sha256"]),
                     (record["overhead_review"], record["overhead_review_sha256"]),
                     (record["eye_height_review"], record["eye_height_review_sha256"])):
    assert sha(SOURCE / item) == digest, item
assert atlas["source_asset"] == "grey_stone_path" and atlas["source_license"] == "CC0-1.0"
assert atlas["count"] == record["individual_stones"] == len(atlas["cells"]) == 64
assert atlas["size_px"] == 4096 and atlas["grid"] == 8 and atlas["cell_px"] == 480
assert len({(cell["source_crop_xy_size_px"][0], cell["source_crop_xy_size_px"][1],
             cell["source_crop_xy_size_px"][2]) for cell in atlas["cells"]}) == 64
assert max(cell["source_dark_grout_fraction"] for cell in atlas["cells"]) <= .075
assert all(cell["quarter_turns"] == 0 and cell["mirrored"] is False for cell in atlas["cells"]), "DX tangent normals must not be rotated or mirrored"
for item in atlas["source_files"].values():
    path = ROOT / item["repo_path"]
    assert path.is_relative_to(ROOT / "Content/SourceArt/Environment/NyaagyuTerrain/GreyStonePath")
    assert sha(path) == item["sha256"]
for item in atlas["outputs"].values():
    path = SOURCE / item["file"]
    assert path.stat().st_size == item["bytes"] and sha(path) == item["sha256"]
for surface, dependency in record["dependencies"].items():
    assert dependency["license"] == "CC0-1.0"
    assert dependency["source_url"].startswith("https://polyhaven.com/a/")
    assert set(dependency["files"]) == {"Albedo", "NormalDX", "ORM"}
    for item in dependency["files"].values():
        assert sha(ROOT / item["repo_path"]) == item["sha256"]
assert set(record["dependencies"]) == {"FaceAtlas", "Mineral", "Silt"}


bpy.ops.wm.open_mainfile(filepath=str(SOURCE / record["source_blend"]))
editable = bpy.data.collections["HeroPath_Editable_IndividualStones"]
stones = sorted((obj for obj in editable.objects if obj.name.startswith("Stone_") and obj.type == "MESH"),
                key=lambda x: x.name)
bed = bpy.data.objects["SiltBed_Feathered"]
assert len(stones) == 64 and bed.name in editable.objects
assert {obj.name for obj in stones} == {f"Stone_{i:03}" for i in range(64)}
assert sum(len(poly.vertices) - 2 for obj in [bed] + stones for poly in obj.data.polygons) == record["source_triangles"]
for i, obj in enumerate(stones):
    assert {mat.name for mat in obj.data.materials} == {"M_HeroPath_StoneFace", "M_HeroPath_StoneEdge"}
    assert obj.data.uv_layers.get("UVMap") and obj.data.color_attributes.get("StoneMacro")
    assert len(obj.data.vertices) > 60 and len(obj.data.polygons) > 50
    assert .012 <= obj["nominal_gap_m"] <= .038
    assert .008 <= obj["stone_top_m"] <= .055
    umin, umax = (128 + (i % 8) * 480) / 4096, (128 + (i % 8) * 480 + 480) / 4096
    vmin = 1 - (128 + (i // 8) * 480 + 480) / 4096
    vmax = 1 - (128 + (i // 8) * 480) / 4096
    for loop in obj.data.uv_layers["UVMap"].data:
        assert umin - .006 < loop.uv[0] < umax + .006
        assert vmin - .006 < loop.uv[1] < vmax + .006
alpha = [loop.color[3] for loop in bed.data.color_attributes["StoneMacro"].data]
assert min(alpha) == 0 and max(alpha) == 1
assert {mat.name for mat in bed.data.materials} == {"M_HeroPath_SiltBed"}


# Verify the actual exported asset rather than inferring successful export
# from a Blender scene or manifest hash alone.
bpy.ops.import_scene.fbx(filepath=str(SOURCE / record["fbx"]))
fbx = bpy.data.objects.get(record["name"] + ".001") or bpy.data.objects.get(record["name"])
assert fbx is not None and fbx.type == "MESH", "Exported hero path mesh is absent"
assert {mat.name.split(".")[0] for mat in fbx.data.materials} == set(record["material_slots"])
assert fbx.data.uv_layers and fbx.data.color_attributes, "FBX lost UV0 or stone tint/edge alpha"
assert len(fbx.data.vertices) >= 20000, len(fbx.data.vertices)
bounds = record["bounds_m"]
assert -3.01 <= bounds["min"][0] < -2.95 and 2.95 < bounds["max"][0] <= 3.01
assert -.002 <= bounds["min"][2] and bounds["max"][2] <= .065
print("NYAAGYU_HERO_PATH_SOURCE_VALIDATED", len(stones), record["source_triangles"],
      len(fbx.data.vertices), record["stone_area_m2"], record["material_slots"])
