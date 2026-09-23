"""Validate the additive gate-foot study and its pinned CC0 scan independently.

  blender -b Content/SourceArt/Environment/NyaagyuToriiFootStudy/Nyaagyu_ToriiFoot_Study.blend --python scripts/art/validate_nyaagyu_torii_foot_study.py
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Environment/NyaagyuToriiFootStudy"
manifest = json.loads((OUT / "manifest.json").read_text())
assert manifest["schema_version"] == 1
assert manifest["generator"] == "scripts/art/create_nyaagyu_torii_foot_study.py"
assert manifest["material_slots"] == ["M_ToriiFoot_MossyRock_CC0"]
assert manifest["scan_asset"] == "https://polyhaven.com/a/mossy_rock"
assert manifest["scan_license"] == "CC0"
for image in bpy.data.images:
    if image.source == "FILE":
        assert image.filepath.startswith("//MossyRock/"), image.filepath
        assert Path(bpy.path.abspath(image.filepath)).is_file(), image.filepath
for channel, entry in manifest["scan_files"].items():
    scan = OUT / "MossyRock" / entry["file"]
    assert scan.is_file() and hashlib.sha256(scan.read_bytes()).hexdigest() == entry["sha256"], channel
    image = bpy.data.images.load(str(scan), check_existing=True)
    assert tuple(image.size) == (2048, 2048), (channel, image.size)

coll = bpy.data.collections["Torii_FittedFoot_Editable"]
parts = [o for o in coll.objects if o.type == "MESH"]
assert len(parts) == manifest["editable_parts"] >= 20
assert sum(len(p.vertices)-2 for o in parts for p in o.data.polygons) == manifest["source_triangles"]
feet = [o for o in parts if o.name.startswith("Hewn_StoneFoot_")]
assert len(feet) == 2
assert sorted(round(o["slot_origin_m"][0], 2) for o in feet) == [-2.35, 2.35]
for foot in feet:
    assert foot.get("covers_original_foot") is True
    assert abs(foot.get("displacement_geometry_amplitude_m", 0)-.008) < 1e-9
    assert foot.data.uv_layers.get("UVMap")
    bounds = [foot.matrix_world @ v.co for v in foot.data.vertices]
    min_z, max_z = min(p.z for p in bounds), max(p.z for p in bounds)
    assert -.025 <= min_z <= 0 and .43 <= max_z <= .46
    assert all(math.isfinite(x) for p in bounds for x in p)
assert all(o.get("art_role") == "visual-only hewn stone foot; no combat collision" for o in parts)

fbx = OUT / manifest["fbx"]
assert hashlib.sha256(fbx.read_bytes()).hexdigest() == manifest["fbx_sha256"]
before = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=str(fbx))
imported = [o for o in set(bpy.data.objects)-before if o.type == "MESH"]
assert len(imported) == 1, [o.name for o in imported]
mesh = imported[0]
assert len(mesh.data.materials) == 1
assert mesh.data.materials[0].name.startswith("M_ToriiFoot_MossyRock_CC0")
assert mesh.data.uv_layers.get("UVMap")
primary_uv = mesh.data.uv_layers[0]
assert primary_uv.name == "UVMap"
u = [loop.uv.x for loop in primary_uv.data]
v = [loop.uv.y for loop in primary_uv.data]
assert max(u)-min(u) > 1.0 and max(v)-min(v) > .6
assert len(mesh.data.polygons) == sum(len(o.data.polygons) for o in parts)
assert (OUT / "ToriiFoot_Before_Blender.png").is_file()
assert (OUT / "ToriiFoot_After_Blender.png").is_file()
print("NYAAGYU_TORII_FOOT_STUDY_VALIDATED",len(parts),manifest["source_triangles"])
