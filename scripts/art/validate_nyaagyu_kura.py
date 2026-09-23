"""Independent Blender and FBX validation for the provision storehouse.

Run:
  blender -b Content/SourceArt/Environment/NyaagyuKura/Nyaagyu_ProvisionKura.blend \
    --python scripts/art/validate_nyaagyu_kura.py
"""

import atexit
import hashlib
import json
import os
import sys
from pathlib import Path

import bpy
from mathutils import Vector


valid = False


def fail_exit():
    if not valid:
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(1)


atexit.register(fail_exit)
root = Path(__file__).resolve().parents[2]
out = root / "Content/SourceArt/Environment/NyaagyuKura"
palette = root / "Content/SourceArt/Environment/PolyHaven"
font = root / "Content/SourceArt/Fonts/NotoSansCJKjp-Regular.otf"
logo = root / "Content/SourceArt/UI/sora_logo_NOtext2.svg"
record = json.loads((out / "manifest.json").read_text())
name = "SM_Nyaagyu_ProvisionKura"
assert bpy.app.version[:2] == (5, 2)
assert Path(bpy.data.filepath).resolve() == (out / record["source_blend"]).resolve()
assert record["schema_version"] == 1 and record["name"] == name
assert record["generator"] == "scripts/art/create_nyaagyu_kura.py"
assert record["unreal_asset"] == f"/Game/Generated/Environment/Props/{name}.{name}"
assert record["fbx"] == name + ".fbx"
assert record["roof_tile_count"] == 600 and record["shutter_count"] == 4
assert record["collision_boxes"] == 3
assert 300 <= record["source_parts"] <= 500
assert 45000 <= record["source_triangles"] < 100000
assert -3.8 < record["bounds_m"]["min"][0] < -3.5
assert 3.5 < record["bounds_m"]["max"][0] < 3.8
assert record["bounds_m"]["min"][1] < -3.8
assert 5.1 < record["bounds_m"]["max"][2] < 5.5
assert "Original project-owned geometry" in record["license"]
assert "CC0 Poly Haven" in record["license"] and "SIL OFL" in record["license"]
for filename, digest in ((record["source_blend"],record["blend_sha256"]),
                         (record["fbx"],record["fbx_sha256"]),
                         (record["preview"],record["preview_sha256"])):
    path = out / filename
    assert path.stat().st_size > 1000, path
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, path
assert hashlib.sha256(font.read_bytes()).hexdigest() == record["font_sha256"]
assert "SIL OPEN FONT LICENSE" in (font.parent / "OFL.txt").read_text()
assert hashlib.sha256(logo.read_bytes()).hexdigest() == record["sora_kamon_svg_sha256"]
assert hashlib.sha256((palette / "manifest.json").read_bytes()).hexdigest() == record["palette_manifest_sha256"]
roof_manifest = palette / "GreyRoofTiles/manifest.json"
assert hashlib.sha256(roof_manifest.read_bytes()).hexdigest() == record["roof_manifest_sha256"]
roof = json.loads(roof_manifest.read_text())
assert roof["asset_id"] == "grey_roof_tiles" and roof["license"] == "CC0-1.0"
assert record["palette_asset_ids"] == ["wood_planks_dirt","stone_floor","grey_roof_tiles"]
palette_records = {item["asset_id"]:item for item in json.loads((palette/"manifest.json").read_text())["assets"]}
expected_images = set()
for asset_id in record["palette_asset_ids"]:
    source = roof if asset_id == "grey_roof_tiles" else palette_records[asset_id]
    base = palette/"GreyRoofTiles" if asset_id == "grey_roof_tiles" else palette
    for item in source["files"]:
        path = base / item["file"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
        expected_images.add(path.resolve())
linked = {Path(bpy.path.abspath(image.filepath)).resolve()
          for image in bpy.data.images if image.source == "FILE"}
assert linked == expected_images, (linked,expected_images)
assert all(image.filepath.startswith("//../PolyHaven/")
           for image in bpy.data.images if image.source == "FILE")
assert any(data.filepath.startswith("//../../Fonts/") and
           Path(bpy.path.abspath(data.filepath)).resolve() == font.resolve()
           for data in bpy.data.fonts)
editable = bpy.data.collections.get("Nyaagyu_ProvisionKura_Editable")
assert editable is not None
parts = [obj for obj in editable.objects if obj.type == "MESH"]
assert len(parts) == record["source_parts"]
assert sum(len(face.vertices)-2 for obj in parts for face in obj.data.polygons) == record["source_triangles"]
assert len([obj for obj in parts if obj.name.startswith("Window_Reveal_")]) == 4
assert len([obj for obj in parts if obj.name.startswith("Kawara_CurvedCourses_")]) == 2
assert len([obj for obj in parts if obj.name.startswith("UserSupplied_SORAKamon_")]) == 4
assert all(obj.get("source_svg_sha256") == record["sora_kamon_svg_sha256"]
           for obj in parts if obj.name.startswith("UserSupplied_SORAKamon_"))
assert all(obj.get("author", "").startswith("Original SORA Arena") for obj in parts)
fbx = out / record["fbx"]
assert fbx.read_bytes().startswith(b"Kaydara FBX Binary")
assert b"/Users/" not in fbx.read_bytes()
before=set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=str(fbx))
imported=[obj for obj in set(bpy.data.objects)-before if obj.type=="MESH"]
render=[obj for obj in imported if obj.name==name]
proxies=[obj for obj in imported if obj.name.startswith("UCX_"+name+"_")]
assert len(render)==1 and len(proxies)==3,[obj.name for obj in imported]
corners=[render[0].matrix_world @ Vector(corner) for corner in render[0].bound_box]
for axis in range(3):
    assert abs(min(p[axis] for p in corners)-record["bounds_m"]["min"][axis])<.02
    assert abs(max(p[axis] for p in corners)-record["bounds_m"]["max"][axis])<.02
slots={slot.material.name.split(".",1)[0] for slot in render[0].material_slots}
assert {"M_Env_Timber","M_Env_Stone","M_Kura_Kawara","M_Kura_LimePlaster",
        "M_Kura_CharredCedar","M_Kura_AgedBrass"} <= slots, slots
assert not any(obj.name==name or obj.name.startswith("UCX_") for obj in editable.objects)
print("NYAAGYU_KURA_FBX_ROUNDTRIP_PASS",record["source_parts"],
      record["source_triangles"],record["bounds_m"],sorted(slots),flush=True)
valid=True
