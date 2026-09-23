"""Independent source/FBX integrity checks for the unintegrated dō study.

Run with the study .blend loaded in Blender. A pass verifies reproducibility
and export integrity, not visual quality or historical accuracy.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Characters/NyaakotoDoStudy"
manifest = json.loads((OUT / "manifest.json").read_text())
textures = json.loads((OUT / "texture_manifest.json").read_text())
assert Path(bpy.data.filepath).resolve() == (OUT / "Nyaakoto_Do_Study.blend").resolve()
base = ROOT / "Content/SourceArt/Characters/Hero/Nyaakoto_RuntimeSkin.blend"
assert hashlib.sha256(base.read_bytes()).hexdigest() == manifest["reference_blend_sha256"]
svg = ROOT / "Content/SourceArt/UI/sora_logo_NOtext2.svg"
assert hashlib.sha256(svg.read_bytes()).hexdigest() == manifest["source_svg_sha256"]
for record in manifest["files"] + textures["files"]:
    path = OUT / record["file"]
    assert path.is_file() and path.stat().st_size == record["bytes"], path
    assert hashlib.sha256(path.read_bytes()).hexdigest() == record["sha256"], path
assert textures["normal_convention"] == "DirectX"
assert textures["orm_channels"] == {"r": "occlusion", "g": "roughness", "b": "metallic"}
for image in bpy.data.images:
    if image.source == "FILE" and image.filepath:
        assert image.filepath.startswith("//"), (image.name, image.filepath)
        assert Path(bpy.path.abspath(image.filepath)).is_file(), image.name

collection = bpy.data.collections[manifest["armor_collection"]]
meshes = [obj for obj in collection.objects if obj.type == "MESH"]
curves = [obj for obj in collection.objects if obj.type == "CURVE"]
assert len(meshes) == manifest["mesh_parts"]
assert len(curves) == manifest["braided_curve_parts"]
assert len([o for o in meshes if o.name.startswith("Do_formed_lacquer_plate_")]) == 7
assert len([o for o in meshes if o.name.startswith("Kusazuri_panel_")]) == 15
crest = [o for o in meshes if o.name.startswith("DoExactSoraKamon_")]
assert len(crest) == 2 and all(o.get("source_svg_sha256") == manifest["source_svg_sha256"] for o in crest)
for obj in meshes:
    assert obj.data.polygons, obj.name
    if obj.name.startswith(("Do_formed_lacquer_plate_", "Kusazuri_panel_")):
        assert obj.data.uv_layers.active and len(obj.data.uv_layers.active.data) == len(obj.data.loops)
        assert obj.data.materials[0].name == "M_Nyaakoto_Do_AgedBlackLacquer"
for obj in curves:
    assert obj.data.bevel_depth > 0 and obj.data.splines, obj.name

# A fresh FBX import must preserve every plate and both exact source crests.
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(OUT / "SM_Nyaakoto_Do_Study.fbx"))
imported = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
assert len(imported) >= len(meshes) + len(curves) - 4, len(imported)
assert len([o for o in imported if o.name.startswith("Do_formed_lacquer_plate_")]) == 7
assert len([o for o in imported if o.name.startswith("Kusazuri_panel_")]) == 15
assert len([o for o in imported if o.name.startswith("DoExactSoraKamon_")]) == 2
print("NYAAKOTO_DO_STUDY_SOURCE_AND_FBX_PASS", json.dumps({
    "mesh_parts": len(meshes), "curve_parts": len(curves),
    "imported_meshes": len(imported), "texture_resolution": textures["resolution_px"]
}))
