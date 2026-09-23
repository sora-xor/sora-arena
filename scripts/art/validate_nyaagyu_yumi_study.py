"""Validate editable yumi source, exact emblem, licensed PBR maps and FBX.

Run: blender -b --factory-startup --python scripts/art/validate_nyaagyu_yumi_study.py
"""

import hashlib
import json
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "Content/SourceArt/Weapons/NyaagyuYumi"
record = json.loads((SOURCE / "manifest.json").read_text())
assert record["schema_version"] == 1
assert record["name"] == "SM_Nyaagyu_Yumi_Study"
assert record["status"] == "source_only_visual_candidate"
assert record["runtime_integrated"] is False
assert record["units"] == "metres"
assert record["bow_height_m"] == 2.20
assert record["grip_height_from_lower_nock_m"] == .75
assert record["texture_license"] == "CC0-1.0"
assert record["kamon_source"] == "Content/SourceArt/UI/sora_logo_NOtext2.svg"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert sha(ROOT / record["generator"]) == record["generator_sha256"]
assert sha(ROOT / record["kamon_source"]) == record["kamon_source_sha256"]
for key, digest in (("source_blend", "source_blend_sha256"),
                    ("source_fbx", "source_fbx_sha256")):
    assert sha(SOURCE / record[key]) == record[digest]
assert len(record["renders"]) == 3
for item in record["renders"]:
    assert sha(SOURCE / item["file"]) == item["sha256"]
assert len(record["textures"]) == 6
for item in record["textures"]:
    path = SOURCE / item["file"]
    assert path.resolve().is_relative_to(SOURCE.resolve())
    assert sha(path) == item["sha256"]
    assert hashlib.md5(path.read_bytes()).hexdigest() == item["md5"]
    assert item["surface"] in ("bamboo", "leather")
    assert item["url"].startswith("https://dl.polyhaven.org/")

bpy.ops.wm.open_mainfile(filepath=str(SOURCE / record["source_blend"]))
source = bpy.data.collections["Yumi_Editable"]
meshes = [obj for obj in source.objects if obj.type == "MESH"]
assert len(meshes) >= 55, len(meshes)
assert all(obj.get("provenance") == "Original SORA Arena project-authored yumi study"
           for obj in meshes)
stave = bpy.data.objects["Asymmetric_LaminatedStave_220cm"]
grip = bpy.data.objects["Tsuka_LeatherSleeve"]
assert len(stave.data.vertices) == 888
assert [material.name for material in stave.data.materials] == [
    "M_Yumi_PhotographedBamboo", "M_Yumi_UrushiOverBamboo",
    "M_Yumi_VisibleLamination"]
assert [layer.name for layer in stave.data.uv_layers] == ["UV0"]
assert [layer.name for layer in grip.data.uv_layers] == ["UV0"]
assert abs(max(v.co.z for v in stave.data.vertices) -
           min(v.co.z for v in stave.data.vertices) - 2.20) < .001
logo = [obj for obj in meshes if obj.name.startswith("UserSupplied_SORAKamon_Grip_Path_")]
assert len(logo) == 2
assert all(obj.get("source_svg_sha256") == record["kamon_source_sha256"] for obj in logo)
assert "Ya_BambooShaft_98cm" in {obj.name for obj in meshes}
assert "Tsuru_Hemp_Unreleased" in {obj.name for obj in meshes}

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=str(SOURCE / record["source_fbx"]))
imported = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
assert len(imported) == len(meshes), (len(imported), len(meshes))
assert any(obj.name.startswith("Asymmetric_LaminatedStave") and len(obj.data.materials) == 3
           for obj in imported)
assert any(obj.name.startswith("Tsuka_LeatherSleeve") and len(obj.data.uv_layers) >= 1
           for obj in imported)
positions = [obj.matrix_world @ vert.co for obj in imported for vert in obj.data.vertices]
zmin, zmax = min(v.z for v in positions), max(v.z for v in positions)
assert -.80 < zmin < -.74 and 1.45 < zmax < 1.52, (zmin, zmax)
assert max(v.x for v in positions) > .75  # arrow tip
assert min(v.x for v in positions) < -.26  # fletching/nock
print("NYAAGYU_YUMI_STUDY_VALID", len(imported), round(zmax-zmin, 3))
