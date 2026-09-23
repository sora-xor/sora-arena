"""Independently inspect the editable integrated road study and its FBXs.

Run: blender -b Content/SourceArt/Environment/NyaagyuIntegratedRoji/Nyaagyu_IntegratedRoji_Source.blend --python scripts/art/validate_nyaagyu_integrated_roji.py
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Environment/NyaagyuIntegratedRoji"
manifest = json.loads((OUT / "manifest.json").read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert manifest["schema_version"] == 1
assert manifest["generator"] == "scripts/art/create_nyaagyu_integrated_roji.py"
assert sha(ROOT / manifest["generator"]) == manifest["generator_sha256"]
assert sha(OUT / manifest["source_blend"]) == manifest["source_blend_sha256"]
assert sha(OUT / manifest["eye_height_review"]) == manifest["eye_height_sha256"]
assert sha(OUT / manifest["overhead_review"]) == manifest["overhead_sha256"]
for key in ("base_terrain", "stone_scan", "soil_scan", "gravel_scan"):
    source = ROOT / manifest[key + "_manifest"]
    assert source.is_file() and sha(source) == manifest[key + "_manifest_sha256"]
assert manifest["collision"].startswith("Unchanged flat Estate box")
assert manifest["old_repeating_scan_removed"] is True
assert manifest["road_extent_m"] == [64, 5.24]
assert 300 <= manifest["nominal_stone_count"] <= 800
assert len(manifest["tile_records"]) == 16
assert all(record["slots"] == ["M_Roji_EstateSoil", "M_Roji_MineralBed",
                                "M_Roji_IndividualStone", "M_Roji_EdgeMineral"]
           for record in manifest["tile_records"])

gravel = json.loads((ROOT / manifest["gravel_scan_manifest"]).read_text())
assert gravel["asset_id"] == "gravel_ground_01"
assert gravel["license"] == "CC0-1.0"
assert gravel["source_dimensions_mm"] == [3000, 3000]
for f in gravel["files"]:
    p = ROOT / "Content/SourceArt/Environment/NyaagyuIntegratedRoji/GravelGround01" / f["file"]
    assert p.is_file() and p.stat().st_size == f["bytes"] and sha(p) == f["sha256"]

base_info = json.loads((ROOT / manifest["base_terrain_manifest"]).read_text())
base_blend = (ROOT / manifest["base_terrain_manifest"]).parent / base_info["source_blend"]
assert sha(base_blend) == base_info["source_blend_sha256"]
with bpy.data.libraries.load(str(base_blend), link=False) as (available, loaded):
    names = [f"SourceTerrain_{tier}_X{x}_Y{y}"
             for tier in ("hi", "mac") for y in (1, 2) for x in range(4)]
    assert set(names).issubset(set(available.objects))
    loaded.objects = names
base = {obj.name: obj for obj in loaded.objects}

counts = {"hi": 0, "mac": 0}
triangles = {"hi": 0, "mac": 0}
stone_per_x = {"hi": [], "mac": []}
for tier in ("hi", "mac"):
    for y in (1, 2):
        for x in range(4):
            record = next(r for r in manifest["tile_records"]
                          if r["tier"] == tier and r["index"] == [x, y])
            path = OUT / record["fbx"]
            assert path.is_file() and sha(path) == record["fbx_sha256"]
            obj = bpy.data.objects.get(record["name"])
            assert obj is not None and obj.type == "MESH"
            assert record["placement_center_cm"] == [-2400 + 1600 * x, -1950 + 1300 * y, 0]
            assert [m.name for m in obj.data.materials] == record["slots"]
            assert obj.data.uv_layers.get("UV0") is not None
            assert obj.data.color_attributes.get("RojiPatina") is not None
            assert obj.get("presentation_only") is True
            original = base[f"SourceTerrain_{tier}_X{x}_Y{y}"]
            n = len(original.data.vertices)
            assert len(obj.data.vertices) > n
            # The under-bed is the original Estate grid exactly: no gameplay
            # terrain shift, mesh hole, or seam crack is introduced by stones.
            for i in range(n):
                assert (obj.data.vertices[i].co - original.data.vertices[i].co).length < 1e-6
            slots = {p.material_index for p in obj.data.polygons}
            assert slots == {0, 1, 2, 3}, slots
            assert len(obj.data.polygons) > len(original.data.polygons)
            tr = sum(len(p.vertices) - 2 for p in obj.data.polygons)
            assert tr == record["total_triangles"]
            assert record["stone_count"] == obj["stone_count"]
            assert 0 < record["stone_count"] < 200
            assert record["stone_triangles"] < tr
            counts[tier] += record["stone_count"]
            triangles[tier] += tr
            stone_per_x[tier].append(record["stone_count"])
    assert counts[tier] == manifest["nominal_stone_count"]
    assert len(set(stone_per_x[tier])) >= 4  # not repeated copies of one module
assert triangles["hi"] > triangles["mac"]

# FBX round-trip checks the Mac and HI source meshes, material identity,
# vertex color, UV0 and local bounds. It catches a visually correct .blend
# that silently exported a single material or lost authored patina.
for tier in ("hi", "mac"):
    record = next(r for r in manifest["tile_records"]
                  if r["tier"] == tier and r["index"] == [0, 1])
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(OUT / record["fbx"]), use_image_search=False)
    imported = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    assert len(imported) == 1, imported
    imp = imported[0]
    slots = [m.name for m in imp.data.materials]
    assert len(slots) == 4 and all(a in b for a, b in zip(record["slots"], slots)), slots
    assert imp.data.uv_layers.active is not None
    assert imp.data.color_attributes, "FBX lost RojiPatina vertex color"
    size = imp.dimensions
    assert 15.9 < max(size.x, size.y) < 17.5
    assert 12.9 < min(size.x, size.y) < 13.5
    assert math.isclose(sum(len(p.vertices) - 2 for p in imp.data.polygons),
                        record["total_triangles"], rel_tol=0, abs_tol=0)
    bpy.data.objects.remove(imp, do_unlink=True)

print("NYAAGYU_INTEGRATED_ROJI_VALID", counts, triangles, stone_per_x)
