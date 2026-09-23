"""Render the Unreal-targeted katana texture set on its editable Blender mesh.

Run: blender -b Content/SourceArt/Nyaagyu_HeroKatana.blend \
  --python scripts/art/render_hero_katana_pbr_review.py
This is a source-art material review, not an Unreal gameplay screenshot.
"""

import json
from pathlib import Path

import bpy


root = Path(__file__).resolve().parents[2]
source = root / "Content/SourceArt/Weapons/HeroKatana/PBR"
record = json.loads((source / "manifest.json").read_text())
for name, profile in record["material_slots"].items():
    material = bpy.data.materials.get(name)
    if material is None:
        raise RuntimeError(f"The editable katana lost its source material: {name}")
    nodes = material.node_tree.nodes
    nodes.clear()
    links = material.node_tree.links
    output = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    albedo = nodes.new("ShaderNodeTexImage")
    albedo.image = bpy.data.images.load(str(source / f"T_HeroKatana_{profile['surface']}_Albedo.png"), check_existing=True)
    normal = nodes.new("ShaderNodeTexImage")
    normal.image = bpy.data.images.load(str(source / f"T_HeroKatana_{profile['surface']}_NormalDX.png"), check_existing=True)
    normal.image.colorspace_settings.name = "Non-Color"
    orm = nodes.new("ShaderNodeTexImage")
    orm.image = bpy.data.images.load(str(source / f"T_HeroKatana_{profile['surface']}_ORM.png"), check_existing=True)
    orm.image.colorspace_settings.name = "Non-Color"
    tint = nodes.new("ShaderNodeMixRGB")
    tint.blend_type = "MULTIPLY"
    tint.inputs[0].default_value = 1
    tint.inputs[2].default_value = (*profile["tint"], 1)
    links.new(albedo.outputs["Color"], tint.inputs[1])
    links.new(tint.outputs["Color"], bsdf.inputs["Base Color"])
    channels = nodes.new("ShaderNodeSeparateColor")
    links.new(orm.outputs["Color"], channels.inputs["Color"])
    rough = nodes.new("ShaderNodeMath")
    rough.operation = "MULTIPLY"
    rough.inputs[1].default_value = profile["roughness_scale"]
    links.new(channels.outputs["Green"], rough.inputs[0])
    links.new(rough.outputs["Value"], bsdf.inputs["Roughness"])
    metal = nodes.new("ShaderNodeMath")
    metal.operation = "MULTIPLY"
    metal.inputs[1].default_value = profile["metallic_scale"]
    links.new(channels.outputs["Blue"], metal.inputs[0])
    links.new(metal.outputs["Value"], bsdf.inputs["Metallic"])
    normal_node = nodes.new("ShaderNodeNormalMap")
    normal_node.inputs["Strength"].default_value = .45
    links.new(normal.outputs["Color"], normal_node.inputs["Color"])
    links.new(normal_node.outputs["Normal"], bsdf.inputs["Normal"])

scene = bpy.context.scene
detail = bpy.data.objects["Katana_Fittings_Detail_Camera"]
scene.camera = detail
scene.render.engine = "CYCLES"
scene.cycles.samples = 96
scene.cycles.use_denoising = True
scene.render.resolution_x = 1600
scene.render.resolution_y = 1100
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(root / "Content/SourceArt/Nyaagyu_HeroKatana_PBR_Review.png")
bpy.ops.render.render(write_still=True)
print("HERO_KATANA_PBR_REVIEW_READY", scene.render.filepath)
