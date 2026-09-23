"""Independent hash, proportion, provenance and FBX round-trip checks.

Run:
  blender -b Content/SourceArt/Environment/NyaagyuDojo/Nyaagyu_EstateDojo.blend \
    --python scripts/art/validate_nyaagyu_dojo.py
"""

import atexit
import hashlib
import json
import os
import sys
from pathlib import Path

import bpy
from mathutils import Vector


validated = False


def fail_exit():
    if not validated:
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(1)


atexit.register(fail_exit)
root = Path(__file__).resolve().parents[2]
out = root / "Content/SourceArt/Environment/NyaagyuDojo"
palette = root / "Content/SourceArt/Environment/PolyHaven"
logo = root / "Content/SourceArt/UI/sora_logo_NOtext2.svg"
font = root / "Content/SourceArt/Fonts/NotoSansCJKjp-Regular.otf"
manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
name = "SM_Nyaagyu_EstateDojo"
assert bpy.app.version[:2] == (5, 2)
assert Path(bpy.data.filepath).resolve() == (out / manifest["source_blend"]).resolve()
assert manifest["schema_version"] == 1 and manifest["name"] == name
assert manifest["generator"] == "scripts/art/create_nyaagyu_dojo.py"
assert manifest["unreal_asset"] == f"/Game/Generated/Environment/Props/{name}.{name}"
assert manifest["fbx"] == name + ".fbx"
assert manifest["shoji_bays"] == 4 and manifest["roof_tile_count"] == 748
assert manifest["collision_boxes"] == 3
assert 300 <= manifest["source_parts"] <= 600
assert 45000 <= manifest["source_triangles"] < 120000
assert manifest["bounds_m"]["min"][0] < -3.5
assert manifest["bounds_m"]["max"][0] > 3.5
assert manifest["bounds_m"]["min"][1] < -4.0
assert 5.0 < manifest["bounds_m"]["max"][2] < 5.5
assert "Original project-owned geometry" in manifest["license"]
assert "CC0 Poly Haven" in manifest["license"]
assert "SIL OFL" in manifest["license"]
for filename, digest in (
    (manifest["source_blend"], manifest["blend_sha256"]),
    (manifest["fbx"], manifest["fbx_sha256"]),
    (manifest["preview"], manifest["preview_sha256"]),
):
    path = out / filename
    assert path.stat().st_size > 1000, path
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, path
assert hashlib.sha256(logo.read_bytes()).hexdigest() == manifest["sora_kamon_svg_sha256"]
assert hashlib.sha256(font.read_bytes()).hexdigest() == manifest["font_sha256"]
assert "SIL OPEN FONT LICENSE" in (font.parent / "OFL.txt").read_text()
palette_manifest = palette / "manifest.json"
assert hashlib.sha256(palette_manifest.read_bytes()).hexdigest() == manifest["palette_manifest_sha256"]
asset_records = {item["asset_id"]: item for item in json.loads(palette_manifest.read_text())["assets"]}
expected_images = set()
for asset_id in manifest["palette_asset_ids"]:
    record = asset_records[asset_id]
    assert record["license"] == "CC0-1.0"
    for item in record["files"]:
        path = palette / item["file"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
        expected_images.add(path.resolve())
linked_images = {Path(bpy.path.abspath(image.filepath)).resolve()
                 for image in bpy.data.images if image.source == "FILE"}
assert linked_images == expected_images, (linked_images, expected_images)
assert all(image.filepath.startswith("//../PolyHaven/")
           for image in bpy.data.images if image.source == "FILE")
assert any(data.filepath.startswith("//../../Fonts/") and
           Path(bpy.path.abspath(data.filepath)).resolve() == font.resolve()
           for data in bpy.data.fonts)
editable = bpy.data.collections.get("Nyaagyu_EstateDojo_Editable")
assert editable is not None
parts = [ob for ob in editable.objects if ob.type == "MESH"]
assert len(parts) == manifest["source_parts"]
assert sum(len(poly.vertices)-2 for ob in parts for poly in ob.data.polygons) == manifest["source_triangles"]
assert len([ob for ob in parts if ob.name.startswith("Shoji_Paper_")]) == 4
assert len([ob for ob in parts if ob.name.startswith("UserSupplied_SORAKamon_")]) == 4
assert all(ob.get("source_svg_sha256") == manifest["sora_kamon_svg_sha256"]
           for ob in parts if ob.name.startswith("UserSupplied_SORAKamon_"))
assert any(ob.name == "Kawara_CurvedTileCourses" for ob in parts)
assert any(ob.name == "Dojo_JapaneseSign" for ob in parts)
assert all(ob.get("author", "").startswith("Original SORA Arena") for ob in parts)
fbx = out / manifest["fbx"]
assert fbx.read_bytes().startswith(b"Kaydara FBX Binary")
assert b"/Users/" not in fbx.read_bytes()
before = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=str(fbx))
imported = [ob for ob in set(bpy.data.objects) - before if ob.type == "MESH"]
render = [ob for ob in imported if ob.name == name]
proxies = [ob for ob in imported if ob.name.startswith("UCX_" + name + "_")]
assert len(render) == 1 and len(proxies) == 3, [ob.name for ob in imported]
corners = [render[0].matrix_world @ Vector(corner) for corner in render[0].bound_box]
for axis in range(3):
    assert abs(min(p[axis] for p in corners)-manifest["bounds_m"]["min"][axis]) < .02
    assert abs(max(p[axis] for p in corners)-manifest["bounds_m"]["max"][axis]) < .02
slots = {slot.material.name.split(".", 1)[0] for slot in render[0].material_slots}
assert {"M_Env_Timber", "M_Env_Stone", "M_Dojo_Washi", "M_Dojo_LimePlaster",
        "M_Dojo_Kawara_0", "M_Dojo_AgedBrass"} <= slots, slots
assert not any(ob.name == name or ob.name.startswith("UCX_") for ob in editable.objects)
print("NYAAGYU_DOJO_FBX_ROUNDTRIP_PASS", manifest["source_parts"],
      manifest["source_triangles"], manifest["bounds_m"], sorted(slots), flush=True)
validated = True
