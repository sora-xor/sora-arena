"""Import an isolated, scan-led Estate road material for packaged ArtReview.

This creates one unreferenced material under /Game/Generated/Environment/ArtReview.
It leaves the main palette, terrain meshes, WorldBuilder, collision, and kernel
untouched. Run only with the pinned UE 5.8.2 editor; a diagnostic copy may
change just the version guard for UE 5.8.3 packaged comparison.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import unreal


version = unreal.SystemLibrary.get_engine_version()
if not version.startswith("5.8.2"):
    raise RuntimeError(f"Estate road variation import requires UE 5.8.2; got {version}")
root = Path(unreal.Paths.project_dir()).resolve()
manifest_path = root / "Content/SourceArt/Environment/NyaagyuTerrain/manifest.json"
manifest = json.loads(manifest_path.read_text())
scan = manifest["stone_pathway_scan"]
if (scan["asset_id"] != "grey_stone_path"
        or scan["source_url"] != "https://polyhaven.com/a/grey_stone_path"
        or scan["license"] != "CC0-1.0"
        or scan["tile_size_cm"] != 180):
    raise RuntimeError("Estate road scan identity changed")
for record in scan["files"]:
    path = manifest_path.parent / record["file"]
    if hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]:
        raise RuntimeError("Estate road PBR map changed: " + str(path))

assets = unreal.EditorAssetLibrary
lib = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
dest = "/Game/Generated/Environment/ArtReview/RojiTextureVariation"
assets.make_directory(dest)
source_textures = {}
for channel in ("Diffuse", "nor_dx", "arm", "disp"):
    name = "T_TerrainGreyStonePath_" + channel
    asset = assets.load_asset("/Game/Generated/Environment/Textures/" + name)
    if not isinstance(asset, unreal.Texture2D):
        raise RuntimeError("Pinned original Estate scan not imported: " + name)
    source_textures[channel] = asset

functions = {}
for name in ("TextureVariation", "TextureVariation_RotateNormals"):
    path = "/Engine/Functions/Engine_MaterialFunctions03/Texturing/" + name
    function = assets.load_asset(path)
    if not isinstance(function, unreal.MaterialFunctionInterface):
        raise RuntimeError("UE 5.8 texture function unavailable: " + path)
    functions[name] = function
actual_pins = {}
for name, function in functions.items():
    inputs, outputs = set(), set()
    for expr in lib.get_material_function_expressions(function):
        if isinstance(expr, unreal.MaterialExpressionFunctionInput):
            inputs.add(str(expr.get_editor_property("input_name")))
        if isinstance(expr, unreal.MaterialExpressionFunctionOutput):
            outputs.add(str(expr.get_editor_property("output_name")))
    actual_pins[name] = (inputs, outputs)
if (not {"Heightmap", "UVs"}.issubset(actual_pins["TextureVariation"][0])
        or not {"Shifted UVs", "DDX", "DDY", "Random Offset"}.issubset(
            actual_pins["TextureVariation"][1])
        or actual_pins["TextureVariation_RotateNormals"][0] != {"Vector", "Normal"}
        or "Result" not in actual_pins["TextureVariation_RotateNormals"][1]):
    raise RuntimeError("UE 5.8 texture variation function signature changed")


def node(material, cls, x, y, **props):
    result = lib.create_material_expression(material, cls, x, y)
    for key, value in props.items():
        result.set_editor_property(key, value)
    return result


def link(a, output, b, input_name):
    if not lib.connect_material_expressions(a, output, b, input_name):
        raise RuntimeError(f"Road variation material pin failed: {output}->{input_name}")


def output(a, pin, prop):
    if not lib.connect_material_property(a, pin, prop):
        raise RuntimeError(f"Road variation material output failed: {prop}")


name = "M_NyaagyuRoadScanVariation_ArtReview"
path = dest + "/" + name
material = assets.load_asset(path) if assets.does_asset_exist(path) else tools.create_asset(
    name, dest, unreal.Material, unreal.MaterialFactoryNew())
for old in list(lib.get_material_expressions(material)):
    lib.delete_material_expression(material, old)
if lib.get_num_material_expressions(material):
    raise RuntimeError("ArtReview material retained old expressions")

world = node(material, unreal.MaterialExpressionWorldPosition, -1900, -280)
xy = node(material, unreal.MaterialExpressionComponentMask, -1670, -280,
          r=True, g=True, b=False, a=False)
link(world, "XYZ", xy, "")
size = node(material, unreal.MaterialExpressionScalarParameter, -1670, -100,
            parameter_name="ScanWidthCm", default_value=180.0)
uv = node(material, unreal.MaterialExpressionDivide, -1430, -280)
link(xy, "", uv, "A")
link(size, "", uv, "B")

height = node(material, unreal.MaterialExpressionTextureObjectParameter, -1420, 90,
              parameter_name="Heightmap", texture=source_textures["disp"])
variation = node(material, unreal.MaterialExpressionMaterialFunctionCall, -1130, -190)
if not variation.set_material_function(functions["TextureVariation"]):
    raise RuntimeError("UE TextureVariation did not bind")
link(height, "", variation, "Heightmap")
link(uv, "", variation, "UVs")

samples = {}
for index, (parameter, channel) in enumerate((
        ("AlbedoMap", "Diffuse"), ("NormalMap", "nor_dx"), ("ARMMap", "arm"))):
    sample = node(material, unreal.MaterialExpressionTextureSampleParameter2D,
                  -700, -430 + 320 * index,
                  parameter_name=parameter, texture=source_textures[channel])
    sample.set_editor_property("mip_value_mode", unreal.TextureMipValueMode.TMVM_DERIVATIVE)
    link(variation, "Shifted UVs", sample, "UVs")
    link(variation, "DDX", sample, "DDX(UVs)")
    link(variation, "DDY", sample, "DDY(UVs)")
    samples[channel] = sample

vertex = node(material, unreal.MaterialExpressionVertexColor, -720, -740)
vertex_rgb = node(material, unreal.MaterialExpressionComponentMask, -530, -720,
                  r=True, g=True, b=True, a=False)
link(vertex, "", vertex_rgb, "")
macro = node(material, unreal.MaterialExpressionMultiply, -300, -400)
link(samples["Diffuse"], "RGB", macro, "A")
link(vertex_rgb, "", macro, "B")
output(macro, "", unreal.MaterialProperty.MP_BASE_COLOR)

rotate = node(material, unreal.MaterialExpressionMaterialFunctionCall, -260, -30)
if not rotate.set_material_function(functions["TextureVariation_RotateNormals"]):
    raise RuntimeError("UE TextureVariation_RotateNormals did not bind")
link(samples["nor_dx"], "RGB", rotate, "Normal")
link(variation, "Random Offset", rotate, "Vector")
output(rotate, "Result", unreal.MaterialProperty.MP_NORMAL)

for index, (prop, mask) in enumerate((
        (unreal.MaterialProperty.MP_AMBIENT_OCCLUSION, (True, False, False)),
        (unreal.MaterialProperty.MP_ROUGHNESS, (False, True, False)),
        (unreal.MaterialProperty.MP_METALLIC, (False, False, True)))):
    part = node(material, unreal.MaterialExpressionComponentMask, -240, 270 + 140 * index,
                r=mask[0], g=mask[1], b=mask[2], a=False)
    link(samples["arm"], "RGB", part, "")
    if prop == unreal.MaterialProperty.MP_ROUGHNESS:
        # Match the shipped terrain-only instance's source-authored wetness;
        # the A/B should isolate UV variation, not alter the PBR response.
        damp = node(material, unreal.MaterialExpressionScalarParameter, -650, 760,
                    parameter_name="TerrainDampRoughness", default_value=0.30)
        masked_damp = node(material, unreal.MaterialExpressionMultiply, -440, 760)
        link(vertex, "A", masked_damp, "A")
        link(damp, "", masked_damp, "B")
        dry = node(material, unreal.MaterialExpressionOneMinus, -220, 760)
        link(masked_damp, "", dry, "")
        wet_roughness = node(material, unreal.MaterialExpressionMultiply, 0, 760)
        link(part, "", wet_roughness, "A")
        link(dry, "", wet_roughness, "B")
        output(wet_roughness, "", prop)
    else:
        output(part, "", prop)

lib.layout_material_expressions(material)
lib.recompile_material(material)
assets.save_loaded_asset(material)
if not {"AlbedoMap", "NormalMap", "ARMMap"}.issubset(
        {str(p) for p in lib.get_texture_parameter_names(material)}):
    raise RuntimeError("ArtReview scan parameters incomplete")
unreal.log("NYAAGYU_ROAD_VARIATION_ART_REVIEW_IMPORTED: " + path +
           "; original scan, UE height-guided UV variation, no gameplay placement")
