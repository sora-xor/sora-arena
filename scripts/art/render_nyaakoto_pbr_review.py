"""Render the existing rigged Nyaakoto mesh with the Unreal fur PBR maps.

This is a Blender material study, not an Unreal screenshot or photoreal
qualification. It does not alter the runtime blend or any mesh/LOD geometry.
"""

from __future__ import annotations

import json
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
HERO = ROOT / "Content/SourceArt/Characters/Hero"
PBR = HERO / "PBR"
record = json.loads((PBR / "manifest.json").read_text())
bpy.ops.wm.open_mainfile(filepath=str(HERO / "Nyaakoto_RuntimeSkin.blend"))


def image(path: Path, color_space: str):
    source = bpy.data.images.load(str(path), check_existing=True)
    source.colorspace_settings.name = color_space
    source.alpha_mode = "NONE"
    return source


for suffix in ("GreyTabbyFur", "WhiteFur", "CharcoalStripeFur"):
    slot = record["material_slots"]["M_Hero_" + suffix]
    surface = slot["surface"]
    material = bpy.data.materials["M_Hero_" + suffix]
    material.use_nodes = True
    nodes = material.node_tree.nodes
    nodes.clear()
    links = material.node_tree.links
    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (510, 0)
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    shader.location = (260, 0)
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    albedo = nodes.new("ShaderNodeTexImage")
    albedo.image = image(PBR / f"T_Nyaakoto_{surface}_Albedo.png", "sRGB")
    albedo.location = (-730, 380)
    tint = nodes.new("ShaderNodeRGB")
    tint.outputs["Color"].default_value = (*slot["tint"], 1)
    tint.location = (-700, 150)
    color = nodes.new("ShaderNodeMixRGB")
    color.blend_type = "MULTIPLY"
    color.inputs[0].default_value = 1
    color.location = (-160, 330)
    links.new(albedo.outputs["Color"], color.inputs[1])
    links.new(tint.outputs["Color"], color.inputs[2])
    links.new(color.outputs["Color"], shader.inputs["Base Color"])
    normal_texture = nodes.new("ShaderNodeTexImage")
    normal_texture.image = image(PBR / f"T_Nyaakoto_{surface}_NormalDX.png", "Non-Color")
    normal_texture.location = (-720, -80)
    normal = nodes.new("ShaderNodeNormalMap")
    normal.space = "TANGENT"
    normal.inputs["Strength"].default_value = .55
    normal.location = (-120, -50)
    links.new(normal_texture.outputs["Color"], normal.inputs["Color"])
    links.new(normal.outputs["Normal"], shader.inputs["Normal"])
    orm = nodes.new("ShaderNodeTexImage")
    orm.image = image(PBR / f"T_Nyaakoto_{surface}_ORM.png", "Non-Color")
    orm.location = (-720, -360)
    split = nodes.new("ShaderNodeSeparateColor")
    split.location = (-430, -360)
    links.new(orm.outputs["Color"], split.inputs["Color"])
    roughness = nodes.new("ShaderNodeMath")
    roughness.operation = "MULTIPLY"
    roughness.inputs[1].default_value = slot["roughness_scale"]
    roughness.location = (-120, -300)
    links.new(split.outputs["Green"], roughness.inputs[0])
    links.new(roughness.outputs[0], shader.inputs["Roughness"])

scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.samples = 48
scene.render.resolution_x = 1200
scene.render.resolution_y = 1050
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(PBR / "Nyaakoto_PBR_Review.png")
scene.camera.location = (1.52, -1.45, 2.12)
scene.camera.rotation_euler = (Vector((.08, 0, 1.64)) - scene.camera.location).to_track_quat("-Z", "Y").to_euler()
scene.camera.data.type = "ORTHO"
scene.camera.data.ortho_scale = .79
bpy.ops.render.render(write_still=True)
print("NYAAKOTO_PBR_REVIEW", scene.render.filepath)
