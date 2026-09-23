"""Render the original and PBR bokken at one close studio camera.

This compares Blender source surfaces only. A packaged UE5.8.2 first-person
comparison is still the visual admission gate for the playable asset.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "Content/SourceArt/Weapons/Original"
PBR = ROOT / "Content/SourceArt/Weapons/DojoBokkenPBR"
OUT = ROOT / "docs/visual-reviews/dojo-bokken"
OUT.mkdir(parents=True, exist_ok=True)
base = json.loads((BASE / "manifest.json").read_text())
variant = json.loads((PBR / "manifest.json").read_text())


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


for src, expected, filename in (
    (BASE / base["source_blend"], base["blend_sha256"], "Bokken_Baseline_Close_Blender.png"),
    (PBR / variant["source_blend"], variant["blend_sha256"], "Bokken_PBRStudy_Close_Blender.png"),
):
    assert sha(src) == expected
    bpy.ops.wm.open_mainfile(filepath=str(src))
    scene = bpy.context.scene
    camera = scene.camera
    assert camera and camera.name == "Bokken_Preview_Camera"
    target = Vector((-.095, 0, .006))
    camera.location = (-.095, -.48, .28)
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = .53
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 48
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(OUT / filename)
    bpy.ops.render.render(write_still=True)
    print("BOKKEN_CLOSE_COMPARISON", filename, sha(OUT / filename))
