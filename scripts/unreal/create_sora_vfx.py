"""Build SORA Arena's Niagara effects into /Game/Generated/VFX (an import-mac.sh step).

Every system is a copy of engine template emitters from
/Niagara/DefaultAssets/Templates/Emitters, re-parameterised through the
SoraVfxAuthoring editor plugin (UE 5.8 keeps Niagara stack editing in C++),
with the project's original particle textures (Content/SourceArt/VFX, made by
scripts/art/create_vfx_textures.py) and materials authored here. Nothing is
hand-edited: rerunning the script rebuilds every asset in place.

Conventions the game code relies on (docs/vfx.md):
  * local +X is the muzzle direction, the hit surface normal, the beam/trail
    axis or a telegraph's forward; +Z is up;
  * User.FlashScale (1 by default) scales what flashes: flashes, sparks
    and their counts, the lights of flashes, and the flicker or pulse
    amplitude of steady lights and telegraphs. Steady lights and glows
    (fires, forge, ward, lanterns, embers, motes) keep their brightness. The
    game passes a lower value when the player turns on "reduce flashing";
  * brightness is scene-referred: emissive in cd/m2 against a lit white
    surface of about 8 cd/m2 in the Estate's daylight, lights in lumens
    (converted to the engine's inverse-square units).

While iterating, SORA_VFX_ONLY=muzzle_matchlock,rain (builder names; an unknown
name is an error) rebuilds only some systems and SORA_VFX_REUSE_MATERIALS=1 keeps
the textures and materials of the last full run. Such a run ends with
SORA_VFX_PARTIAL. Only a complete build (every texture checked, every
material's shaders and every system compiled without errors) prints
SORA_VFX_READY: <n> systems, n being len(SYSTEMS); import-mac.sh clears both
variables and requires that exact count.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from pathlib import Path

import unreal

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sora_engine_pin import require_running_engine  # noqa: E402

require_running_engine("VFX build")
ROOT = Path(unreal.Paths.project_dir()).resolve()
SOURCE = ROOT / "Content/SourceArt/VFX"
DEST = "/Game/Generated/VFX"
ENVIRONMENT = "/Game/Generated/Environment/Textures"
AUTHOR = unreal.SoraNiagaraAuthoring
assets = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
mel = unreal.MaterialEditingLibrary
TEMPLATE = "/Niagara/DefaultAssets/Templates/Emitters/"
MODULE = "/Niagara/Modules/"
PS, PU, EU = "ParticleSpawnScript", "ParticleUpdateScript", "EmitterUpdateScript"
ONLY = {name for name in os.environ.get("SORA_VFX_ONLY", "").split(",") if name}
REUSE_MATERIALS = os.environ.get("SORA_VFX_REUSE_MATERIALS", "") == "1"
LUMEN_TO_LIGHT = 100.0 * 100.0 / (4.0 * math.pi)   # lumens -> inverse-square light units (cm)


def check(result, what):
    """Raise on a non-empty error from the authoring plugin; return the rest."""
    error = result[0] if isinstance(result, tuple) else result
    if error:
        raise RuntimeError(f"{what}: {error}")
    if isinstance(result, tuple):
        return result[1] if len(result) == 2 else result[1:]
    return None


def log(message):
    unreal.log(f"SORA_VFX: {message}")


# ---------------------------------------------------------------- textures

TEXTURE_SETTINGS = {
    # channels -> (compression, sampler)
    "L": ("TC_GRAYSCALE", "SAMPLERTYPE_LINEAR_GRAYSCALE"),
    "RGB": ("TC_BC7", "SAMPLERTYPE_LINEAR_COLOR"),
    "RGBA": ("TC_BC7", "SAMPLERTYPE_LINEAR_COLOR"),
}


def import_textures():
    manifest = json.loads((SOURCE / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("tier") != "OWN" or manifest.get("generator") != "scripts/art/create_vfx_textures.py":
        raise RuntimeError("Content/SourceArt/VFX/manifest.json is not the generator's OWN manifest")
    textures, samplers = {}, {}
    for entry in manifest["files"]:
        path = ROOT / entry["file"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            raise RuntimeError(f"VFX texture hash mismatch: {path}; rerun scripts/art/create_vfx_textures.py")
        name = path.stem
        task = unreal.AssetImportTask()
        task.filename = str(path)
        task.destination_path = DEST + "/Textures"
        task.destination_name = name
        task.automated = True
        task.replace_existing = True
        task.save = False
        tools.import_asset_tasks([task])
        texture = assets.load_asset(f"{DEST}/Textures/{name}")
        if not isinstance(texture, unreal.Texture2D):
            raise RuntimeError(f"VFX texture import failed: {name}")
        compression, sampler = TEXTURE_SETTINGS[entry["channels"]]
        if entry["srgb"]:
            sampler = "SAMPLERTYPE_COLOR"
        texture.set_editor_property("srgb", bool(entry["srgb"]))
        texture.set_editor_property("compression_settings", getattr(unreal.TextureCompressionSettings, compression))
        texture.set_editor_property("lod_group", unreal.TextureGroup.TEXTUREGROUP_EFFECTS)
        if name != "T_VFX_Noise":
            texture.set_editor_property("address_x", unreal.TextureAddress.TA_CLAMP)
            texture.set_editor_property("address_y", unreal.TextureAddress.TA_CLAMP)
        assets.save_loaded_asset(texture)
        textures[name] = texture
        samplers[name] = getattr(unreal.MaterialSamplerType, sampler)
    log(f"imported {len(textures)} textures")
    return textures, samplers


# ---------------------------------------------------------------- materials

class Graph:
    """A material rebuilt from nothing each run."""

    def __init__(self, name, *, blend, shading, lighting=None, two_sided=False, sprites=True, ribbons=False, meshes=False):
        folder = DEST + "/Materials"
        path = f"{folder}/{name}"
        if assets.does_asset_exist(path):
            self.mat = assets.load_asset(path)
            for expression in list(mel.get_material_expressions(self.mat)):
                mel.delete_material_expression(self.mat, expression)
        else:
            self.mat = tools.create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())
        if mel.get_num_material_expressions(self.mat):
            raise RuntimeError(f"Material {name} kept expressions from its last build")
        self.name = name
        self.x, self.y = -1800, -600
        mat = self.mat
        mat.set_editor_property("blend_mode", blend)
        mat.set_editor_property("shading_model", shading)
        if lighting is not None:
            mat.set_editor_property("translucency_lighting_mode", lighting)
        mat.set_editor_property("two_sided", two_sided)
        mat.set_editor_property("used_with_niagara_sprites", sprites)
        mat.set_editor_property("used_with_niagara_ribbons", ribbons)
        mat.set_editor_property("used_with_niagara_mesh_particles", meshes)

    def node(self, cls, **properties):
        expression = mel.create_material_expression(self.mat, cls, self.x, self.y)
        self.y += 160
        if self.y > 900:
            self.y, self.x = -600, self.x + 320
        for key, value in properties.items():
            expression.set_editor_property(key, value)
        return expression

    def scalar(self, name, value):
        return self.node(unreal.MaterialExpressionScalarParameter, parameter_name=name, default_value=value)

    def vector(self, name, value):
        return self.node(unreal.MaterialExpressionVectorParameter, parameter_name=name, default_value=value)

    def link(self, source, output, target, pin):
        if not mel.connect_material_expressions(source, output, target, pin):
            raise RuntimeError(f"{self.name}: cannot connect {source.get_name()}.{output!r} -> {target.get_name()}.{pin!r}")

    def custom(self, code, inputs, output="float3", extra=()):
        """A Custom HLSL node; inputs maps pin name -> (expression, output name)."""
        types = {"float1": unreal.CustomMaterialOutputType.CMOT_FLOAT1, "float2": unreal.CustomMaterialOutputType.CMOT_FLOAT2,
                 "float3": unreal.CustomMaterialOutputType.CMOT_FLOAT3, "float4": unreal.CustomMaterialOutputType.CMOT_FLOAT4}
        node = self.node(unreal.MaterialExpressionCustom, code=code, output_type=types[output])
        pins = []
        for name in inputs:
            pin = unreal.CustomInput()
            pin.set_editor_property("input_name", name)
            pins.append(pin)
        node.set_editor_property("inputs", pins)
        outputs = []
        for name, kind in extra:
            out = unreal.CustomOutput()
            out.set_editor_property("output_name", name)
            out.set_editor_property("output_type", types[kind])
            outputs.append(out)
        node.set_editor_property("additional_outputs", outputs)
        for name, (source, source_output) in inputs.items():
            self.link(source, source_output, node, name)
        return node

    def out(self, prop, source, output=""):
        if not mel.connect_material_property(source, output, prop):
            raise RuntimeError(f"{self.name}: cannot drive {prop} from {source.get_name()}.{output!r}")

    def finish(self):
        mel.layout_material_expressions(self.mat)
        mel.recompile_material(self.mat)
        # Compile the shaders for this editor's platform now: a Custom-node or
        # type error that the HLSL translation accepts only fails here (and the
        # game would fall back to the default material).
        stats = mel.get_statistics(self.mat)
        pixel = stats.get_editor_property("num_pixel_shader_instructions")
        vertex = stats.get_editor_property("num_vertex_shader_instructions")
        if pixel <= 0:
            raise RuntimeError(f"{self.name} did not compile its shaders (see the log for the shader error)")
        log(f"{self.name}: {pixel} pixel / {vertex} vertex shader instructions, "
            f"{stats.get_editor_property('num_pixel_texture_samples')} texture samples")
        assets.save_loaded_asset(self.mat)
        return self.mat


def instance(name, parent, scalars=None, vectors=None, textures=None):
    folder = DEST + "/Materials"
    path = f"{folder}/{name}"
    mi = assets.load_asset(path) if assets.does_asset_exist(path) else tools.create_asset(
        name, folder, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mel.set_material_instance_parent(mi, parent)
    mel.clear_all_material_instance_parameters(mi)
    # The library's setters report failure even when they work (UE 5.8), so
    # check each name against the parent and read the value back.
    known = {"scalar": set(map(str, mel.get_scalar_parameter_names(parent))),
             "vector": set(map(str, mel.get_vector_parameter_names(parent))),
             "texture": set(map(str, mel.get_texture_parameter_names(parent)))}
    for kind, values, setter, getter in (
            ("scalar", scalars, mel.set_material_instance_scalar_parameter_value, mel.get_material_instance_scalar_parameter_value),
            ("vector", vectors, mel.set_material_instance_vector_parameter_value, mel.get_material_instance_vector_parameter_value),
            ("texture", textures, mel.set_material_instance_texture_parameter_value, mel.get_material_instance_texture_parameter_value)):
        for key, value in (values or {}).items():
            if key not in known[kind]:
                raise RuntimeError(f"{name}: {parent.get_name()} has no {kind} parameter {key}")
            if value is None:
                raise RuntimeError(f"{name}: {kind} parameter {key} has no value")
            setter(mi, key, value)
            read = getter(mi, key)
            same = abs(read - value) <= 1e-4 * max(1.0, abs(value)) if kind == "scalar" else read == value
            if not same:
                raise RuntimeError(f"{name}: {kind} parameter {key} did not take {value!r}")
    mel.update_material_instance(mi)
    assets.save_loaded_asset(mi)
    return mi


def soft_fade(g, distance):
    """Depth-fade factor (0 at an intersecting surface, 1 past Distance) for soft particles."""
    fade = g.node(unreal.MaterialExpressionDepthFade, opacity_default=1.0, fade_distance_default=distance)
    g.link(g.scalar("SoftDistance", distance), "", fade, "FadeDistance")
    return fade


class DynamicParameter:
    """Dynamic parameter 0 with its outputs addressed by our names (UE 5.8 names them R, G, B, A)."""

    def __init__(self, g, names, default):
        self.node = g.node(unreal.MaterialExpressionDynamicParameter, default_value=unreal.LinearColor(*default))
        self.names = list(names)

    def __getitem__(self, name):
        return self.node, "RGBA"[self.names.index(name)]


def dynamic(g, names, default):
    return DynamicParameter(g, names, default)


def build_materials(textures, samplers):
    if "-nullrhi" in unreal.SystemLibrary.get_command_line().lower():
        raise RuntimeError("VFX materials must compile their shaders to be checked: run this step without -nullrhi "
                           "(import-mac.sh passes -RenderOffscreen), or set SORA_VFX_REUSE_MATERIALS=1")
    BM, SM, TLM = unreal.BlendMode, unreal.MaterialShadingModel, unreal.TranslucencyLightingMode
    MP = unreal.MaterialProperty
    mats = {}

    def subuv(g, name, texture):
        return g.node(unreal.MaterialExpressionTextureSampleParameterSubUV, parameter_name=name,
                      texture=textures[texture], sampler_type=samplers[texture], blend=True)

    def cell_sample(g, texture):
        """Sample one cell of a 2x2 sheet chosen by the Cell parameter."""
        uv = g.node(unreal.MaterialExpressionTextureCoordinate)
        cell_uv = g.custom("float2 c = float2(fmod(Cell, 2.0), floor(Cell / 2.0)); return (frac(UV) + c) * 0.5;",
                           {"UV": (uv, ""), "Cell": (g.scalar("Cell", 0.0), "")}, "float2")
        sample = g.node(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name="Sheet",
                        texture=textures[texture], sampler_type=samplers[texture])
        g.link(cell_uv, "", sample, "UVs")
        return sample

    # Lit smoke: flipbook density, self-shadow darkening, incandescent core while hot.
    g = Graph("M_SoraVFX_SmokeLit", blend=BM.BLEND_TRANSLUCENT, shading=SM.MSM_DEFAULT_LIT,
              lighting=TLM.TLM_VOLUMETRIC_DIRECTIONAL)
    tex = subuv(g, "Flipbook", "T_VFX_SmokePuff")
    pc = g.node(unreal.MaterialExpressionParticleColor)
    dyn = dynamic(g, ["Heat", "Erode", "Unused", "Unused2"], (0, 0, 0, 0))
    shade = g.custom(
        "float d = saturate((Tex.r * Density - Erode) / max(1.0 - Erode, 0.05));\n"
        "Opacity = saturate(d * PC.a);\n"
        "Temperature = lerp(1000.0, 2100.0, saturate(Tex.g));\n"
        "Glow = Tex.g * Heat * HeatIntensity;\n"
        "return PC.rgb * lerp(1.0, 1.0 - ShadowStrength, Tex.b);",
        {"Tex": (tex, "RGBA"), "PC": (pc, "RGBA"), "Heat": dyn["Heat"], "Erode": dyn["Erode"],
         "Density": (g.scalar("Density", 1.0), ""), "ShadowStrength": (g.scalar("ShadowStrength", .45), ""),
         "HeatIntensity": (g.scalar("HeatIntensity", 300.0), "")},
        "float3", [("Opacity", "float1"), ("Temperature", "float1"), ("Glow", "float1")])
    fade = soft_fade(g, 80.0)
    opacity = g.custom("return Opacity * Fade;", {"Opacity": (shade, "Opacity"), "Fade": (fade, "")}, "float1")
    body = g.node(unreal.MaterialExpressionBlackBody)
    g.link(shade, "Temperature", body, "Temp")
    emissive = g.custom("return BB * Glow * Fade;", {"BB": (body, ""), "Glow": (shade, "Glow"), "Fade": (fade, "")})
    g.out(MP.MP_BASE_COLOR, shade)
    g.out(MP.MP_OPACITY, opacity)
    g.out(MP.MP_EMISSIVE_COLOR, emissive)
    g.out(MP.MP_ROUGHNESS, g.node(unreal.MaterialExpressionConstant, r=1.0))
    mats["SmokeLit"] = g.finish()

    # Flames: premultiplied (alpha composite) black-body emission over a little soot occlusion.
    g = Graph("M_SoraVFX_Fire", blend=BM.BLEND_ALPHA_COMPOSITE, shading=SM.MSM_UNLIT)
    tex = subuv(g, "Flipbook", "T_VFX_Fire")
    pc = g.node(unreal.MaterialExpressionParticleColor)
    dyn = dynamic(g, ["TempScale", "Unused", "Unused2", "Unused3"], (1, 0, 0, 0))
    fade = soft_fade(g, 40.0)
    temp = g.custom(
        "Heat = saturate(Tex.r);\n"
        "Cover = saturate(Tex.g * PC.a * OpacityScale) * Fade;\n"
        "return lerp(TempMin, TempMax, saturate(Heat * TempScale));",
        {"Tex": (tex, "RGBA"), "PC": (pc, "RGBA"), "TempScale": dyn["TempScale"], "Fade": (fade, ""),
         "TempMin": (g.scalar("TempMin", 900.0), ""), "TempMax": (g.scalar("TempMax", 1950.0), ""),
         "OpacityScale": (g.scalar("OpacityScale", .3), "")},
        "float1", [("Heat", "float1"), ("Cover", "float1")])
    body = g.node(unreal.MaterialExpressionBlackBody)
    g.link(temp, "", body, "Temp")
    emissive = g.custom("return BB * Intensity * PC.rgb * PC.a * smoothstep(0.0, 0.12, Heat) * Fade;",
                        {"BB": (body, ""), "Intensity": (g.scalar("Intensity", 250.0), ""), "PC": (pc, "RGBA"),
                         "Heat": (temp, "Heat"), "Fade": (fade, "")})
    g.out(MP.MP_EMISSIVE_COLOR, emissive)
    g.out(MP.MP_OPACITY, temp, "Cover")
    mats["Fire"] = g.finish()

    # Flash shapes (2x2 sheet), additive; bright cores whiten toward the luminance of the tint.
    # A flash is hundreds of cd/m2, so the sheet's 1-2/255 floor and the neighbouring cell that bilinear
    # filtering pulls in at a cell's border would both draw the quad: drop the floor and fade the outer 5 %
    # of the cell. This keeps 79-98 % of each cell's light; a radial mask kept 23 % of the ring and 55 % of the
    # side plume, and cut the plume off at the muzzle.
    g = Graph("M_SoraVFX_Flash", blend=BM.BLEND_ADDITIVE, shading=SM.MSM_UNLIT)
    tex = cell_sample(g, "T_VFX_Flash")
    pc = g.node(unreal.MaterialExpressionParticleColor)
    fade = soft_fade(g, 12.0)
    emissive = g.custom(
        "float2 q = abs(frac(UV) * 2.0 - 1.0);\n"
        "float t = saturate((Tex.r - 0.008) / 0.992) * saturate((1.0 - max(q.x, q.y)) * 10.0);\n"
        "float core = pow(saturate((t - 0.55) / 0.45), 3.0);\n"
        "float lum = dot(PC.rgb, float3(0.2126, 0.7152, 0.0722));\n"
        "return (PC.rgb * t + core * lum * CoreWhite) * PC.a * Fade;",
        {"Tex": (tex, "RGBA"), "UV": (g.node(unreal.MaterialExpressionTextureCoordinate), ""), "PC": (pc, "RGBA"),
         "Fade": (fade, ""), "CoreWhite": (g.scalar("CoreWhite", 2.5), "")})
    g.out(MP.MP_EMISSIVE_COLOR, emissive)
    mats["Flash"] = g.finish()

    # Procedural soft glow for sparks, embers and motes (sparks are stretched by velocity alignment).
    g = Graph("M_SoraVFX_Glow", blend=BM.BLEND_ADDITIVE, shading=SM.MSM_UNLIT)
    uv = g.node(unreal.MaterialExpressionTextureCoordinate)
    pc = g.node(unreal.MaterialExpressionParticleColor)
    fade = soft_fade(g, 6.0)
    emissive = g.custom(
        "float2 p = UV * 2.0 - 1.0;\n"
        "float d2 = dot(p, p);\n"
        "return PC.rgb * PC.a * exp(-d2 * Sharpness) * saturate(1.0 - d2) * Fade;",
        {"UV": (uv, ""), "PC": (pc, "RGBA"), "Fade": (fade, ""), "Sharpness": (g.scalar("Sharpness", 4.0), "")})
    g.out(MP.MP_EMISSIVE_COLOR, emissive)
    mats["Glow"] = g.finish()

    # Energy beams and bolt trails on ribbons: a hot core, a halo and a scrolling ripple.
    g = Graph("M_SoraVFX_Beam", blend=BM.BLEND_ADDITIVE, shading=SM.MSM_UNLIT, sprites=True, ribbons=True)
    uv = g.node(unreal.MaterialExpressionTextureCoordinate)
    time = g.node(unreal.MaterialExpressionTime)
    pc = g.node(unreal.MaterialExpressionParticleColor)
    noise_uv = g.custom("return float2(UV.x * NoiseScale - Time * Scroll, UV.y * 0.5);",
                        {"UV": (uv, ""), "Time": (time, ""), "NoiseScale": (g.scalar("NoiseScale", 3.0), ""),
                         "Scroll": (g.scalar("Scroll", 6.0), "")}, "float2")
    noise = g.node(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name="Noise",
                   texture=textures["T_VFX_Noise"], sampler_type=samplers["T_VFX_Noise"])
    g.link(noise_uv, "", noise, "UVs")
    emissive = g.custom(
        "float v = abs(UV.y * 2.0 - 1.0);\n"
        "float core = exp(-v * v * CoreSharpness);\n"
        "float halo = exp(-v * v * 3.0) * HaloAmount * lerp(1.0 - NoiseAmount, 1.0 + NoiseAmount, N.g);\n"
        "float ends = saturate(UV.x * EndFade) * saturate((1.0 - UV.x) * EndFade);\n"
        "return PC.rgb * PC.a * (core + halo) * ends;",
        {"UV": (uv, ""), "PC": (pc, "RGBA"), "N": (noise, "RGBA"), "CoreSharpness": (g.scalar("CoreSharpness", 18.0), ""),
         "HaloAmount": (g.scalar("HaloAmount", .35), ""), "NoiseAmount": (g.scalar("NoiseAmount", .6), ""),
         "EndFade": (g.scalar("EndFade", 12.0), "")})
    g.out(MP.MP_EMISSIVE_COLOR, emissive)
    mats["Beam"] = g.finish()

    # Blade trail: a faint translucent sheen of displaced air, strongest at the leading edge.
    g = Graph("M_SoraVFX_Trail", blend=BM.BLEND_TRANSLUCENT, shading=SM.MSM_UNLIT, sprites=False, ribbons=True)
    uv = g.node(unreal.MaterialExpressionTextureCoordinate)
    pc = g.node(unreal.MaterialExpressionParticleColor)
    noise = g.node(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name="Noise",
                   texture=textures["T_VFX_Noise"], sampler_type=samplers["T_VFX_Noise"])
    trail = g.custom(
        "float v = UV.y;\n"
        "float edge = smoothstep(0.0, 0.35, v) * smoothstep(1.0, 0.8, v);\n"
        "float tipBias = lerp(0.35, 1.0, v);\n"
        "float streak = lerp(0.55, 1.0, N.g);\n"
        "Opacity = saturate(PC.a * edge * tipBias * streak);\n"
        "return PC.rgb * edge * tipBias * streak * PC.a;",
        {"UV": (uv, ""), "PC": (pc, "RGBA"), "N": (noise, "RGBA")}, "float3", [("Opacity", "float1")])
    g.out(MP.MP_EMISSIVE_COLOR, trail)
    g.out(MP.MP_OPACITY, trail, "Opacity")
    mats["Trail"] = g.finish()

    # Water spray, sheets, foam and mist: lit, translucent, soft.
    g = Graph("M_SoraVFX_WaterLit", blend=BM.BLEND_TRANSLUCENT, shading=SM.MSM_DEFAULT_LIT,
              lighting=TLM.TLM_VOLUMETRIC_PER_VERTEX_DIRECTIONAL)
    tex = cell_sample(g, "T_VFX_Water")
    pc = g.node(unreal.MaterialExpressionParticleColor)
    fade = soft_fade(g, 30.0)
    water = g.custom(
        "float2 q = frac(UV) * 2.0 - 1.0;\n"
        "Opacity = saturate(Tex.r * PC.a) * Fade * saturate(1.5 * (1.0 - dot(q, q)));\n"
        "return PC.rgb * (0.8 + 0.6 * Tex.g) * lerp(1.0, 0.8, Tex.b);",
        {"Tex": (tex, "RGBA"), "UV": (g.node(unreal.MaterialExpressionTextureCoordinate), ""), "PC": (pc, "RGBA"),
         "Fade": (fade, "")}, "float3", [("Opacity", "float1")])
    g.out(MP.MP_BASE_COLOR, water)
    g.out(MP.MP_OPACITY, water, "Opacity")
    g.out(MP.MP_ROUGHNESS, g.node(unreal.MaterialExpressionConstant, r=.1))
    mats["WaterLit"] = g.finish()

    # Rain streaks: a thin lit line, stretched along velocity by the renderer.
    g = Graph("M_SoraVFX_Rain", blend=BM.BLEND_TRANSLUCENT, shading=SM.MSM_DEFAULT_LIT,
              lighting=TLM.TLM_VOLUMETRIC_PER_VERTEX_NON_DIRECTIONAL)
    uv = g.node(unreal.MaterialExpressionTextureCoordinate)
    pc = g.node(unreal.MaterialExpressionParticleColor)
    rain = g.custom(
        "float2 p = UV * 2.0 - 1.0;\n"
        "Opacity = exp(-p.x * p.x * 18.0) * saturate(1.0 - p.y * p.y) * PC.a;\n"
        "return PC.rgb;",
        {"UV": (uv, ""), "PC": (pc, "RGBA")}, "float3", [("Opacity", "float1")])
    g.out(MP.MP_BASE_COLOR, rain)
    g.out(MP.MP_OPACITY, rain, "Opacity")
    mats["Rain"] = g.finish()

    # Debris mesh particles: the environment's PBR surfaces at a random offset per chip.
    g = Graph("M_SoraVFX_DebrisLit", blend=BM.BLEND_OPAQUE, shading=SM.MSM_DEFAULT_LIT, sprites=False, meshes=True)
    uv = g.node(unreal.MaterialExpressionTextureCoordinate)
    rnd = g.node(unreal.MaterialExpressionParticleRandom)
    pc = g.node(unreal.MaterialExpressionParticleColor)
    chip_uv = g.custom("return UV * UVScale + Rand * float2(7.31, 3.17);",
                       {"UV": (uv, ""), "Rand": (rnd, ""), "UVScale": (g.scalar("UVScale", .12), "")}, "float2")
    env = {}
    for role, sampler, key in (("BaseColorMap", unreal.MaterialSamplerType.SAMPLERTYPE_COLOR, "Diffuse"),
                               ("NormalMap", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL, "nor_dx"),
                               ("ARMMap", unreal.MaterialSamplerType.SAMPLERTYPE_MASKS, "arm")):
        texture = assets.load_asset(f"{ENVIRONMENT}/T_Timber_{key}")
        if texture is None:
            raise RuntimeError(f"{ENVIRONMENT}/T_Timber_{key} is missing; run import_environment_palette.py first")
        env[role] = g.node(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name=role,
                           texture=texture, sampler_type=sampler)
        g.link(chip_uv, "", env[role], "UVs")
    color = g.custom("return Base.rgb * PC.rgb;", {"Base": (env["BaseColorMap"], "RGB"), "PC": (pc, "RGBA")})
    g.out(MP.MP_BASE_COLOR, color)
    g.out(MP.MP_NORMAL, env["NormalMap"], "RGB")
    g.out(MP.MP_AMBIENT_OCCLUSION, env["ARMMap"], "R")
    g.out(MP.MP_ROUGHNESS, env["ARMMap"], "G")
    g.out(MP.MP_METALLIC, env["ARMMap"], "B")
    mats["DebrisLit"] = g.finish()

    # Paper, leaves and ash: two-sided masked cards that catch light and cast shadows.
    g = Graph("M_SoraVFX_ScrapMasked", blend=BM.BLEND_MASKED, shading=SM.MSM_DEFAULT_LIT, two_sided=True)
    tex = subuv(g, "Sheet", "T_VFX_Scraps")
    tex.set_editor_property("blend", False)
    pc = g.node(unreal.MaterialExpressionParticleColor)
    scrap = g.custom("Mask = Tex.a * step(0.02, PC.a);\nreturn Tex.rgb * PC.rgb;",
                     {"Tex": (tex, "RGBA"), "PC": (pc, "RGBA")}, "float3", [("Mask", "float1")])
    g.out(MP.MP_BASE_COLOR, scrap)
    g.out(MP.MP_OPACITY_MASK, scrap, "Mask")
    g.out(MP.MP_ROUGHNESS, g.node(unreal.MaterialExpressionConstant, r=.85))
    mats["ScrapMasked"] = g.finish()

    # Shed fur: lit translucent locks tinted by the particle colour.
    g = Graph("M_SoraVFX_FurLit", blend=BM.BLEND_TRANSLUCENT, shading=SM.MSM_DEFAULT_LIT,
              lighting=TLM.TLM_VOLUMETRIC_PER_VERTEX_DIRECTIONAL, two_sided=True)
    tex = subuv(g, "Sheet", "T_VFX_Fur")
    tex.set_editor_property("blend", False)
    pc = g.node(unreal.MaterialExpressionParticleColor)
    fur = g.custom("Opacity = saturate(Tex.a * PC.a);\nreturn Tex.rgb * PC.rgb;",
                   {"Tex": (tex, "RGBA"), "PC": (pc, "RGBA")}, "float3", [("Opacity", "float1")])
    g.out(MP.MP_BASE_COLOR, fur)
    g.out(MP.MP_OPACITY, fur, "Opacity")
    mats["FurLit"] = g.finish()

    # Ground telegraphs: disc/ring (Shape 0), wedge (1) or lane (2), with a fill that tracks the windup.
    # A wedge of 360 degrees (HalfArc pi; above 3.13 even through the half-precision dynamic parameter) is an
    # area: it has no sides, so neither the angular cut nor the side outline may draw a seam along its back.
    g = Graph("M_SoraVFX_Telegraph", blend=BM.BLEND_TRANSLUCENT, shading=SM.MSM_UNLIT)
    uv = g.node(unreal.MaterialExpressionTextureCoordinate)
    pc = g.node(unreal.MaterialExpressionParticleColor)
    time = g.node(unreal.MaterialExpressionTime)
    dyn = dynamic(g, ["Fill", "HalfArc", "Pulse", "Unused"], (0, 1.57, 0, 0))
    tele = g.custom(
        "float2 p = float2(UV.x * 2.0 - 1.0, 1.0 - UV.y * 2.0);\n"
        "float r = length(p);\n"
        "float w = EdgeWidth;\n"
        "float inside, outline, filled;\n"
        "if (Shape < 0.5) {\n"
        "  inside = 1.0 - smoothstep(1.0 - w * 0.5, 1.0, r);\n"
        "  outline = inside * smoothstep(1.0 - w * 2.0, 1.0 - w, r);\n"
        "  filled = inside * (1.0 - smoothstep(Fill - w, Fill, r));\n"
        "} else if (Shape < 1.5) {\n"
        "  float a = abs(atan2(p.x, p.y));\n"
        "  float full = step(3.13, HalfArc);\n"
        "  float angular = max(full, 1.0 - smoothstep(HalfArc - 0.02, HalfArc, a));\n"
        "  inside = angular * (1.0 - smoothstep(1.0 - w * 0.5, 1.0, r));\n"
        "  float side = (1.0 - full) * smoothstep(HalfArc - 0.02 - w / max(r, 0.05), HalfArc - 0.02, a);\n"
        "  outline = inside * max(smoothstep(1.0 - w * 2.0, 1.0 - w, r), side);\n"
        "  filled = inside * (1.0 - smoothstep(Fill - w, Fill, r));\n"
        "} else {\n"
        "  float along = UV.y < 0.0 ? 0.0 : 1.0 - UV.y;\n"
        "  inside = 1.0 - smoothstep(1.0 - w, 1.0, abs(p.x));\n"
        "  outline = inside * max(smoothstep(1.0 - w * 3.0, 1.0 - w, abs(p.x)), smoothstep(1.0 - w, 1.0, along));\n"
        "  filled = inside * (1.0 - smoothstep(Fill - 0.01, Fill, along));\n"
        "}\n"
        "float pulse = 1.0 + Pulse * 0.5 * sin(Time * 9.0);\n"
        "Opacity = PC.a * saturate(outline * 0.95 + filled * FillOpacity + inside * 0.06);\n"
        "return PC.rgb * (outline * 1.4 + filled * 0.55 + inside * 0.08) * pulse;",
        {"UV": (uv, ""), "PC": (pc, "RGBA"), "Time": (time, ""), "Fill": dyn["Fill"], "HalfArc": dyn["HalfArc"],
         "Pulse": dyn["Pulse"], "Shape": (g.scalar("Shape", 0.0), ""), "EdgeWidth": (g.scalar("EdgeWidth", .035), ""),
         "FillOpacity": (g.scalar("FillOpacity", .32), "")},
        "float3", [("Opacity", "float1")])
    g.out(MP.MP_EMISSIVE_COLOR, tele)
    g.out(MP.MP_OPACITY, tele, "Opacity")
    mats["Telegraph"] = g.finish()

    t = textures
    mi = {
        "Smoke": instance("MI_SoraVFX_Smoke", mats["SmokeLit"]),
        "Fireball": instance("MI_SoraVFX_Fireball", mats["SmokeLit"], {"HeatIntensity": 500.0, "ShadowStrength": .55},
                             textures={"Flipbook": t["T_VFX_Fireball"]}),
        "Dust": instance("MI_SoraVFX_Dust", mats["SmokeLit"], {"ShadowStrength": .3, "Density": .85}),
        "Steam": instance("MI_SoraVFX_Steam", mats["SmokeLit"], {"ShadowStrength": .15, "Density": .75, "SoftDistance": 120.0}),
        "Fire": instance("MI_SoraVFX_Fire", mats["Fire"]),
        "FlashFace": instance("MI_SoraVFX_FlashPowderFace", mats["Flash"], {"Cell": 0.0}),
        "FlashSide": instance("MI_SoraVFX_FlashPowderSide", mats["Flash"], {"Cell": 1.0}),
        "FlashStar": instance("MI_SoraVFX_FlashEnergyStar", mats["Flash"], {"Cell": 2.0}),
        "FlashRing": instance("MI_SoraVFX_FlashRing", mats["Flash"], {"Cell": 3.0, "CoreWhite": 0.0}),
        "Spark": instance("MI_SoraVFX_Spark", mats["Glow"], {"Sharpness": 7.0}),
        "Glow": instance("MI_SoraVFX_Glow", mats["Glow"], {"Sharpness": 2.5, "SoftDistance": 40.0}),
        "Beam": instance("MI_SoraVFX_Beam", mats["Beam"]),
        "Trail": instance("MI_SoraVFX_BladeTrail", mats["Trail"]),
        "Spray": instance("MI_SoraVFX_WaterSpray", mats["WaterLit"], {"Cell": 0.0, "SoftDistance": 8.0}),
        "Sheet": instance("MI_SoraVFX_WaterSheet", mats["WaterLit"], {"Cell": 1.0, "SoftDistance": 15.0}),
        "Foam": instance("MI_SoraVFX_WaterFoam", mats["WaterLit"], {"Cell": 2.0, "SoftDistance": 10.0}),
        "Mist": instance("MI_SoraVFX_WaterMist", mats["WaterLit"], {"Cell": 3.0, "SoftDistance": 150.0}),
        "Rain": instance("MI_SoraVFX_Rain", mats["Rain"]),
        "Scrap": instance("MI_SoraVFX_Scrap", mats["ScrapMasked"]),
        "Fur": instance("MI_SoraVFX_Fur", mats["FurLit"]),
        "Ring": instance("MI_SoraVFX_TelegraphRing", mats["Telegraph"], {"Shape": 0.0}),
        "Wedge": instance("MI_SoraVFX_TelegraphWedge", mats["Telegraph"], {"Shape": 1.0}),
        "Lane": instance("MI_SoraVFX_TelegraphLane", mats["Telegraph"], {"Shape": 2.0, "EdgeWidth": .08}),
    }
    for role, surface in (("Wood", "Timber"), ("Stone", "Stone"), ("Soil", "Soil"), ("Plaster", "Plaster")):
        mi[role] = instance(f"MI_SoraVFX_Debris{role}", mats["DebrisLit"], {"UVScale": .1 if role != "Wood" else .06},
                            textures={"BaseColorMap": assets.load_asset(f"{ENVIRONMENT}/T_{surface}_Diffuse"),
                                      "NormalMap": assets.load_asset(f"{ENVIRONMENT}/T_{surface}_nor_dx"),
                                      "ARMMap": assets.load_asset(f"{ENVIRONMENT}/T_{surface}_arm")})
    log(f"built {len(mats)} materials and {len(mi)} instances")
    return mi


# ---------------------------------------------------------------- niagara authoring

class Expr(str):
    """A module input set to an HLSL expression (may read User.*, Particles.*, Engine.*)."""


class Link(str):
    """A module input read from a parameter."""


class Dyn:
    """A module input driven by a dynamic input script, with nested values."""

    def __init__(self, script, **nested):
        self.script, self.nested = script, nested


def path_of(asset):
    return asset.get_path_name()


EFFECT_TYPES = {
    # name: (update frequency, cull reaction, cull distance cm (0 = never), instance cap (0 = none))
    # One-shot weapon, impact and ability effects: decided at spawn, never spawned beyond 120 m.
    "ET_SoraVFX_Burst": ("SPAWN_ONLY", "DEACTIVATE", 12000.0, 64),
    # Loops placed in the world (fires, forge, steam, water, lanterns): sleep when far, resume when near.
    "ET_SoraVFX_Ambient": ("MEDIUM", "DEACTIVATE_RESUME", 9000.0, 0),
    # Telegraphs and trails the player must read: never culled.
    "ET_SoraVFX_Gameplay": ("SPAWN_ONLY", "DEACTIVATE", 0.0, 0),
}


def build_effect_types():
    """Scalability classes every system is assigned to (distance and instance culling)."""
    made = {}
    for name, (frequency, reaction, distance, cap) in EFFECT_TYPES.items():
        path = f"{DEST}/{name}"
        effect = assets.load_asset(path) if assets.does_asset_exist(path) else tools.create_asset(
            name, DEST, unreal.NiagaraEffectType, unreal.NiagaraEffectTypeFactoryNew())
        effect.set_editor_property("update_frequency", getattr(unreal.NiagaraScalabilityUpdateFrequency, frequency))
        effect.set_editor_property("cull_reaction", getattr(unreal.NiagaraCullReaction, reaction))
        settings = unreal.NiagaraSystemScalabilitySettings()
        settings.set_editor_property("cull_by_distance", distance > 0)
        settings.set_editor_property("max_distance", distance)
        settings.set_editor_property("cull_max_instance_count", cap > 0)
        settings.set_editor_property("max_instances", cap)
        group = unreal.NiagaraSystemScalabilitySettingsArray()
        group.set_editor_property("settings", [settings])
        effect.set_editor_property("system_scalability_settings", group)
        assets.save_loaded_asset(effect)
        made[name] = effect
    return made


class System:
    effect_types = {}

    def __init__(self, name, description, effect_type="ET_SoraVFX_Burst"):
        self.name, self.description = name, description
        path = f"{DEST}/{name}"
        if assets.does_asset_exist(path):
            self.asset = assets.load_asset(path)
            check(AUTHOR.reset_system(self.asset), f"{name}: reset")
        else:
            self.asset, error = AUTHOR.create_empty_system(DEST, name)
            check(error, f"{name}: create")
        self.emitters = []
        self.asset.set_editor_property("effect_type", System.effect_types[effect_type])
        assets.set_metadata_tag(self.asset, "SoraVFX.Description", description)
        # Every system takes User.FlashScale, so the game can pass the setting to any effect it spawns.
        self.user("FlashScale", 1.0, "1 = full brightness. The game lowers it (about 0.3) when the player reduces flashing; "
                  "it scales flashes, sparks and their counts, the lights of flashes, and the flicker or pulse amplitude "
                  "of steady lights and telegraphs. Steady lights and glows keep their brightness.")

    def user(self, name, value, description):
        what = f"{self.name}: User.{name}"
        if isinstance(value, bool):
            check(AUTHOR.add_user_bool(self.asset, name, value, description), what)
        elif isinstance(value, int):
            check(AUTHOR.add_user_int(self.asset, name, value, description), what)
        elif isinstance(value, float):
            check(AUTHOR.add_user_float(self.asset, name, value, description), what)
        elif isinstance(value, unreal.LinearColor):
            check(AUTHOR.add_user_color(self.asset, name, value, description), what)
        elif isinstance(value, unreal.Vector):
            check(AUTHOR.add_user_vector(self.asset, name, value, description), what)
        else:
            raise TypeError(f"{what}: unsupported default {value!r}")

    def emitter(self, name, template):
        check(AUTHOR.add_emitter(self.asset, unreal.load_asset(TEMPLATE + template), name), f"{self.name}: add {name}")
        emitter = Emitter(self, name)
        self.emitters.append(emitter)
        return emitter

    def compile(self):
        described = json.loads(AUTHOR.describe_system(self.asset))
        log(f"{self.name}: user {[u['name'] for u in described['user']]}")
        errors, report = AUTHOR.compile_system(self.asset)
        parsed = json.loads(report) if report else {}
        warnings = [line for line in parsed.get("stack_issues", []) if line.startswith("Warning")]
        warnings += [line for line in parsed.get("compile_events", []) if line.startswith("warning")]
        if errors:
            raise RuntimeError(f"{self.name} failed to compile:\n{errors}")
        assets.save_loaded_asset(self.asset)
        log(f"{self.name}: {len(self.emitters)} emitters, status {parsed.get('status')}, {len(warnings)} warnings")
        for line in warnings:
            log(f"  {self.name} {line[:300]}")
        return parsed


class Emitter:
    def __init__(self, system, name):
        self.system, self.name, self.asset = system, name, system.asset
        self._stacks = None
        self._random = None

    # stack discovery
    def stacks(self):
        if self._stacks is None:
            described = json.loads(AUTHOR.describe_system(self.asset))
            emitter = next(e for e in described["emitters"] if e["name"] == self.name)
            self._stacks = {script: [m["name"] for m in stack["modules"]] for script, stack in emitter["stacks"].items()}
            self._inputs = {m["name"]: {i["name"]: i for i in m["inputs"]}
                            for stack in emitter["stacks"].values() for m in stack["modules"]}
            self._renderers = [r["class"] for r in emitter["renderers"]]
        return self._stacks

    def inputs(self, module):
        """Input name -> {type, visible, editable, value} for a module, as the stack shows it now."""
        self.stacks()
        return self._inputs[module]

    def script_of(self, module):
        found = [script for script, modules in self.stacks().items() if module in modules]
        if len(found) != 1:
            raise RuntimeError(f"{self.system.name}/{self.name}: module {module} found in {found or 'no stack'}")
        return found[0]

    def where(self, what):
        return f"{self.system.name}/{self.name}: {what}"

    # module inputs
    def set(self, module, inputs, value, script=None):
        try:
            return self._set(module, inputs, value, script)
        except RuntimeError as error:
            self._stacks = None
            visible = {name: info.get("value", "")[:40] for name, info in self.inputs(module).items() if info["visible"]}
            raise RuntimeError(f"{error}\n  visible inputs of {module}: {visible}") from None

    def _set(self, module, inputs, value, script=None):
        script = script or self.script_of(module)
        path = [inputs] if isinstance(inputs, str) else list(inputs)
        args = (self.asset, self.name, script, module, path)
        what = self.where(f"{module}.{'/'.join(path)} = {value!r}"[:200])
        if script == PU and isinstance(value, Expr) and "rand(" in value:
            # Particle Update runs every tick, and rand() there is re-rolled on each evaluation (the CPU VM's
            # is unseeded, the GPU's is seeded by the tick counter): a spin rate becomes a jitter and a
            # temperature becomes per-frame noise. Draw per-particle values once, at spawn (particle_random).
            raise RuntimeError(f"{what}: rand() in a Particle Update input changes every tick; use particle_random()")
        known = self.inputs(module)
        if len(path) == 1 and path[0] not in known:
            visible = sorted(name for name, info in known.items() if info["visible"])
            raise RuntimeError(f"{what}: no input {path[0]!r}; visible inputs: {visible}")
        if isinstance(value, Expr):
            check(AUTHOR.set_input_expression(*args, str(value)), what)
        elif isinstance(value, Link):
            check(AUTHOR.set_input_linked(*args, str(value)), what)
        elif isinstance(value, Dyn):
            check(AUTHOR.set_input_dynamic(*args, unreal.load_asset(value.script)), what)
            for key, nested in value.nested.items():
                self._set(module, path + [key.replace("_", " ")], nested, script)
        elif isinstance(value, bool):
            check(AUTHOR.set_input_bool(*args, value), what)
        elif isinstance(value, int):
            check(AUTHOR.set_input_int(*args, value), what)
        elif isinstance(value, float):
            check(AUTHOR.set_input_float(*args, value), what)
        elif isinstance(value, str):
            check(AUTHOR.set_input_enum(*args, value), what)
        elif isinstance(value, unreal.LinearColor):
            check(AUTHOR.set_input_color(*args, value), what)
        elif isinstance(value, unreal.Vector):
            check(AUTHOR.set_input_vector(*args, value), what)
        elif isinstance(value, unreal.Vector2D):
            check(AUTHOR.set_input_vector2(*args, value), what)
        else:
            raise TypeError(what)
        self._stacks = None
        return self

    def many(self, module, values, script=None):
        """Set several inputs of one module in order (enums first so their inputs appear)."""
        for key, value in values.items():
            self.set(module, key, value, script)
        return self

    def add(self, module_path, script, before=None):
        """Add an engine module; forces and collision go before SolveForcesAndVelocity."""
        stack = self.stacks()[script]
        after = ""
        if before is not None and before in stack:
            index = stack.index(before)
            after = stack[index - 1] if index > 0 else ""
            if index == 0:
                raise RuntimeError(self.where(f"cannot insert before the first module {before}"))
        name = check(AUTHOR.add_module(self.asset, self.name, script, unreal.load_asset(MODULE + module_path), after),
                     self.where(f"add {module_path}"))
        self._stacks = None
        return str(name)

    def ensure(self, module_path, script, before=None):
        """The module named like module_path's last part, added when the stack lacks it."""
        name = module_path.rsplit("/", 1)[-1]
        if name in self.stacks()[script]:
            return name
        return self.add(module_path, script, before)

    def write(self, script, parameter, kind, expression, after=None):
        """A Set Parameters module writing `parameter` (e.g. Particles.Position) from an HLSL expression."""
        stack = self.stacks()[script]
        after_name = after if after is not None else (stack[-1] if stack else "")
        name = str(check(AUTHOR.add_set_parameter(self.asset, self.name, script, after_name, parameter, kind),
                         self.where(f"write {parameter}")))
        self._stacks = None
        inputs = self.inputs(name)
        target = parameter if parameter in inputs else next(iter(inputs))
        self.set(name, target, Expr(expression), script)
        return name

    def random(self):
        """Particles.SoraRandom: four uniform [0, 1) values drawn once per particle at spawn."""
        if self._random is None:
            self._random = self.write(PS, RANDOM, "vec4", "float4(rand(1.0), rand(1.0), rand(1.0), rand(1.0))")
        return RANDOM

    def force(self, module_path):
        """Forces, drag, collision and per-frame attribute writers run before the solver."""
        return self.ensure(module_path, PU, before="SolveForcesAndVelocity")

    def remove(self, module, script=None):
        check(AUTHOR.remove_module(self.asset, self.name, script or self.script_of(module), module),
              self.where(f"remove {module}"))
        self._stacks = None
        return self

    def disable(self, module, script=None):
        check(AUTHOR.set_module_enabled(self.asset, self.name, script or self.script_of(module), module, False),
              self.where(f"disable {module}"))
        return self

    # renderers and emitter properties
    def renderer_index(self, cls):
        self.stacks()
        return self._renderers.index(cls)

    def renderer(self, cls="NiagaraSpriteRendererProperties", **properties):
        props = {}
        for key, value in properties.items():
            props[key] = path_of(value) if isinstance(value, unreal.Object) else value
        check(AUTHOR.set_renderer_properties(self.asset, self.name, self.renderer_index(cls), json.dumps(props)),
              self.where(f"{cls} {sorted(props)}"))
        return self

    def add_renderer(self, cls):
        index = check(AUTHOR.add_renderer(self.asset, self.name, unreal.load_class(None, "/Script/Niagara." + cls)),
                      self.where(f"add {cls}"))
        self._stacks = None
        return index

    def props(self, **properties):
        check(AUTHOR.set_emitter_properties(self.asset, self.name, json.dumps(properties)), self.where(f"props {sorted(properties)}"))
        return self


# ---------------------------------------------------------------- shared recipes

def rgb(r, g, b, a=1.0):
    return unreal.LinearColor(r, g, b, a)


def vec(x, y, z):
    return unreal.Vector(x, y, z)


def hlsl_color(r, g, b, a=1.0, flash=False):
    scale = "User.FlashScale" if flash else "1.0"
    return Expr(f"float4({r:.4f} * {scale}, {g:.4f} * {scale}, {b:.4f} * {scale}, {a:.4f})")


def ss(edge0, edge1, x):
    """smoothstep for Niagara expressions: the CPU vector VM has no smoothstep."""
    t = f"saturate(({x} - ({edge0})) / (({edge1}) - ({edge0})))"
    return f"({t} * {t} * (3.0 - 2.0 * {t}))"


AGE = "Particles.NormalizedAge"


def fade_in_out(rise, power=1.0):
    """Alpha that rises over the first `rise` of life and falls to zero at the end."""
    return f"{ss(0.0, rise, AGE)} * pow(saturate(1.0 - {AGE}), {power:.2f})"


def rand_range(lo, hi):
    """lo..hi drawn at each evaluation: for spawn inputs only (the builder refuses rand() in Particle Update)."""
    return Expr(f"{lo:.4f} + rand({hi - lo:.4f})")


# Channels of Particles.SoraRandom, so that one particle's spin, drag and heat do not share a value.
RANDOM = "Particles.SoraRandom"
SPIN, DRAG, HEAT = "x", "y", "z"


def particle_random(e, channel, lo, hi):
    """lo..hi fixed per particle (drawn at spawn), for inputs of the Particle Update stack."""
    return Expr(f"({lo:.4f} + {hi - lo:.4f} * {e.random()}.{channel})")


def burst(e, count, time=0.0):
    e.set("SpawnBurst_Instantaneous", "Spawn Count", count if isinstance(count, (int, Expr)) else int(count))
    if time:
        e.set("SpawnBurst_Instantaneous", "Spawn Time", float(time))
    return e


def own_lifecycle(e):
    """Let the emitter run its own loop (templates driven by the system hide the loop inputs)."""
    if e.inputs("EmitterState")["Life Cycle Mode"]["value"] != "enum:Self":
        e.set("EmitterState", "Life Cycle Mode", "Self")
    return e


def once(e, duration):
    own_lifecycle(e)
    e.many("EmitterState", {"Loop Behavior": "Once", "Loop Duration Mode": "Fixed"})
    e.set("EmitterState", "Loop Duration", Expr(duration) if isinstance(duration, str) else float(duration))
    return e


def forever(e, loop=1.0):
    own_lifecycle(e)
    e.many("EmitterState", {"Loop Behavior": "Infinite"})
    if "Loop Duration Mode" in e.inputs("EmitterState") and e.inputs("EmitterState")["Loop Duration Mode"]["visible"]:
        e.set("EmitterState", "Loop Duration Mode", "Fixed")
    e.set("EmitterState", "Loop Duration", float(loop))
    return e


def lifetime(e, lo, hi=None):
    if hi is None:
        e.many("InitializeParticle", {"Lifetime Mode": "Direct Set", "Lifetime": float(lo)})
    else:
        e.many("InitializeParticle", {"Lifetime Mode": "Random", "Lifetime Min": float(lo), "Lifetime Max": float(hi)})
    return e


def color(e, value):
    e.many("InitializeParticle", {"Color Mode": "Direct Set", "Color": value})
    return e


def size(e, lo, hi=None):
    if hi is None:
        e.many("InitializeParticle", {"Sprite Size Mode": "Uniform", "Uniform Sprite Size": float(lo)})
    else:
        e.many("InitializeParticle", {"Sprite Size Mode": "Random Uniform", "Uniform Sprite Size Min": float(lo),
                                      "Uniform Sprite Size Max": float(hi)})
    return e


def size2(e, lo, hi):
    e.many("InitializeParticle", {"Sprite Size Mode": "Random Non-Uniform", "Sprite Size Min": unreal.Vector2D(*lo),
                                  "Sprite Size Max": unreal.Vector2D(*hi)})
    return e


def spin(e, rate_deg=None):
    e.many("InitializeParticle", {"Sprite Rotation Mode": "Random", "Sprite Rotation Angle Min": 0.0,
                                  "Sprite Rotation Angle Max": 360.0})
    if rate_deg:
        e.force("Update/Orientation/SpriteRotationRate")
        e.set("SpriteRotationRate", "Rotation Rate", particle_random(e, SPIN, -rate_deg, rate_deg))
    return e


def fade(e, alpha, rgb_expr=None):
    """ScaleColor over life: alpha (and optionally rgb) as expressions of Particles.NormalizedAge."""
    module = "ScaleColor"
    if module not in e.stacks()[PU]:
        e.add("Update/Color/ScaleColor", PU, before="SolveForcesAndVelocity")
    if e.inputs(module)["Scale Mode"]["type"].startswith("ENiagara"):
        e.set(module, "Scale Mode", "RGB and Alpha Separately")    # the templates' older ScaleColor
    e.set(module, "ScaleA", True)
    e.set(module, "Scale Alpha", Expr(alpha))
    if rgb_expr is not None:
        e.set(module, "ScaleRGB", True)
        e.set(module, "Scale RGB", Expr(rgb_expr))
    return e


def grow(e, expr):
    """Scale sprite size over life by a float expression of Particles.NormalizedAge."""
    e.force("Update/Size/ScaleSpriteSize")
    if "Scale Sprite Size Mode" in e.inputs("ScaleSpriteSize"):
        e.set("ScaleSpriteSize", "Scale Sprite Size Mode", "Uniform")
        e.set("ScaleSpriteSize", "Uniform Scale Factor", Expr(expr))
    else:
        e.set("ScaleSpriteSize", "Scale Factor", Expr(f"({expr}).xx"))
    return e


def dynamic_params(e, values):
    """Material dynamic parameter 0 (x..w) as expressions."""
    e.force("Update/Material/DynamicMaterialParameters")
    for index, value in enumerate(values):
        if value is None:
            e.set("DynamicMaterialParameters", f"Module.Index0Float{index}Write", False)
        else:
            e.set("DynamicMaterialParameters", f"Index 0 Param {index + 1}", Expr(value) if isinstance(value, str) else float(value))
    return e


def subuv(e, frames, blend):
    """SubUV animation with the sheet size stated here (the renderer-info data interface is left unbound)."""
    e.add("Update/SubUV/V2/SubUVAnimation", PU, before="SolveForcesAndVelocity")
    e.many("SubUVAnimation", {"Define SubUV Setup Manually": "Manual", "Manual SubImage Size": unreal.Vector2D(frames, frames),
                              "Is SubUV Blending Enabled On Renderer": blend})
    return e


def flipbook(e, material, frames=8, loop_seconds=None, sort="ViewDepth"):
    """Play an 8x8 flipbook over each particle's life, or loop it every loop_seconds from a random frame."""
    subuv(e, frames, True)
    if loop_seconds:
        e.many("SubUVAnimation", {"SubUV Animation Mode": "Infinite Loop", "Random Start Frame": True,
                                  "Playback Mode": "Loops Per Second", "Play Rate": 1.0 / loop_seconds})
    e.renderer(Material=material, SubImageSize={"x": frames, "y": frames}, bSubImageBlend=True, SortMode=sort)
    return e


def sheet_cell(e, material, first, last):
    """A random but fixed cell of a 2x2 sheet in [first, last]."""
    subuv(e, 2, False)
    e.many("SubUVAnimation", {"Random Start Frame": True, "SubUV Lookup Index Scale": 0.0, "UseStartFrame": True,
                              "Start Frame Range Override": first, "UseEndFrame": True, "End Frame Range Override": last})
    e.renderer(Material=material, SubImageSize={"x": 2, "y": 2}, bSubImageBlend=False)
    return e


def light(e, lumens, radius, color_rgb, flash=True, flicker=None, fade_expr=None, megalights=False):
    """Give an emitter a light renderer; lumens is converted to the engine's inverse-square units.

    lumens and radius may be HLSL (reading User.*); color_rgb is an (r, g, b) tuple or an HLSL float3.

    The renderer keeps its default bindings, Particles.Color and Particles.LightRadius, and the emitter
    writes both every frame with Set Parameters at the end of its update stack. Light_Attributes is not
    used: its output modes write Particles.Light_Attributes.Color and .LightRadius, which an unbound
    renderer never reads; the light then keeps the particle's white (about a thousandth of a lumen).
    """
    index = e.add_renderer("NiagaraLightRendererProperties")
    terms = [f"({lumens}) * {LUMEN_TO_LIGHT:.3f}" if isinstance(lumens, str) else f"{lumens * LUMEN_TO_LIGHT:.1f}"]
    if flash:
        terms.append("User.FlashScale")
    if flicker:
        terms.append(f"(1.0 + ({flicker}) * User.FlashScale * (0.55 * sin(Engine.Time * 11.3 + Particles.UniqueID)"
                     f" + 0.3 * sin(Engine.Time * 23.9) + 0.15 * sin(Engine.Time * 41.7)))")
    if fade_expr:
        terms.append(f"({fade_expr})")
    tint = color_rgb if isinstance(color_rgb, str) else "float3({:.4f}, {:.4f}, {:.4f})".format(*color_rgb)
    e.write(PU, "Particles.LightRadius", "float", radius if isinstance(radius, str) else f"{float(radius):.1f}")
    e.write(PU, "Particles.Color", "color", f"float4(({tint}) * ({' * '.join(terms)}), 1.0)")
    check(AUTHOR.set_renderer_properties(e.asset, e.name, index, json.dumps({
        "bUseInverseSquaredFalloff": True, "bAffectsTranslucency": True, "bAllowMegaLights": megalights,
        "RadiusScale": 1.0, "bAlphaScalesBrightness": False})), e.where("light renderer"))
    return e


# ---------------------------------------------------------------- systems

def muzzle_matchlock(mi):
    s = System("NS_SoraVFX_Muzzle_Matchlock", "Matchlock (teppo) discharge: black-powder flash, burning grains, pan flash and a dense white cloud.")
    s.user("PanOffset", vec(-95.0, 4.0, 3.0), "Flash pan (hizara) relative to the muzzle, local cm; set per weapon.")

    e = s.emitter("PlumeFlash", "SimpleSpriteBurst")
    once(e, .1); burst(e, 2); lifetime(e, .045, .07)
    color(e, hlsl_color(220.0, 100.0, 26.0, flash=True))
    size2(e, (26, 60), (34, 85))
    fade(e, "pow(saturate(1.0 - Particles.NormalizedAge), 1.5)")
    e.force("Update/Renderers/Sprite/SpriteFacingAndAlignment")
    e.many("SpriteFacingAndAlignment", {"WriteFacing": False, "WriteAlignment": True, "Sprite Alignment": vec(1, 0, 0)})
    e.renderer(Material=mi["FlashSide"], Alignment="CustomAlignment", FacingMode="FaceCameraPlane", PivotInUVSpace={"x": 0.5, "y": 1.0})
    e.props(bLocalSpace=True)

    e = s.emitter("FaceFlash", "SimpleSpriteBurst")
    once(e, .1); burst(e, 1); lifetime(e, .05)
    color(e, hlsl_color(260.0, 130.0, 35.0, flash=True))
    size(e, 48, 62); spin(e)
    fade(e, "pow(saturate(1.0 - Particles.NormalizedAge), 2.0)")
    e.renderer(Material=mi["FlashFace"])
    e.props(bLocalSpace=True)

    e = s.emitter("Grains", "DirectionalBurst")
    once(e, .6); burst(e, Expr("(int)(18 + 22 * User.FlashScale)")); lifetime(e, .12, .45)
    color(e, hlsl_color(120.0, 50.0, 10.0, flash=True))
    size2(e, (.7, 1.5), (1.2, 3.0))
    e.many("AddVelocity", {"Velocity Speed": rand_range(1200, 3600), "Cone Axis": vec(1, 0, 0), "Cone Angle": 11.0})
    drag(e, (1.5, 4.0))
    fade(e, "saturate(1.0 - Particles.NormalizedAge)", "lerp(float3(1,1,1), float3(0.55,0.25,0.08), Particles.NormalizedAge)")
    e.many("ScaleSpriteSizeBySpeed", {"Min Scale Factor": unreal.Vector2D(1, 1), "Max Scale Factor": unreal.Vector2D(1, 9),
                                      "Velocity Threshold": 2500.0})
    e.renderer(Material=mi["Spark"], Alignment="VelocityAligned")

    puffs(s, "Fireball", mi["Fireball"], count=5, life=(.16, .26), color_value=rgb(.35, .33, .3, .9), size_range=(22, 34),
          sphere=3.0, offset=(18, 0, 0), speed=(500, 1200), axis=(1, 0, 0), angle=10, drag_amount=9.0, grow_to=2.8,
          heat=f"pow(saturate(1.0 - {AGE} * 1.1), 1.2)", erode=.2, alpha=fade_in_out(.02, 1.0), spin_rate=90, local=True)

    e = s.emitter("Smoke", "OmnidirectionalBurst")
    once(e, 6.0); burst(e, 22); lifetime(e, 3.5, 6.0)
    color(e, rgb(.78, .77, .74, .9))
    size(e, 26, 46); spin(e, 25)
    gravity(e, 0.0)
    e.many("ShapeLocation", {"Sphere Radius": 6.0})
    e.many("AddVelocity", {"Velocity Mode": "In Cone", "Velocity Speed": rand_range(250, 1100), "Cone Axis": vec(1, 0, 0), "Cone Angle": 22.0})
    drag(e, (3.0, 5.5))
    e.force("Update/Forces/V2/CurlNoiseForce")
    e.many("CurlNoiseForce", {"Noise Strength": 60.0, "Noise Frequency": 180.0})
    e.force("Update/Forces/AccelerationForce")
    e.set("AccelerationForce", "Acceleration", vec(0, 0, 14))
    grow(e, "lerp(1.0, 6.5, 1.0 - pow(1.0 - Particles.NormalizedAge, 2.2))")
    fade(e, fade_in_out(.03, 1.3))
    dynamic_params(e, ["saturate(1.0 - Particles.Age * 12.0)", "Particles.NormalizedAge * 0.35", None, None])
    flipbook(e, mi["Smoke"])

    e = s.emitter("PanFlash", "SimpleSpriteBurst")
    once(e, .15); burst(e, 1, .0); lifetime(e, .06)
    color(e, hlsl_color(90.0, 42.0, 11.0, flash=True))
    size(e, 14, 18); spin(e)
    e.set("InitializeParticle", "UsePositionOffset", True).set("InitializeParticle", "Position Offset", Link("User.PanOffset"))
    fade(e, "pow(saturate(1.0 - Particles.NormalizedAge), 2.0)")
    e.renderer(Material=mi["FlashFace"])
    e.props(bLocalSpace=True)

    e = s.emitter("PanSmoke", "OmnidirectionalBurst")
    once(e, 3.0); burst(e, 5); lifetime(e, 1.5, 2.8)
    color(e, rgb(.78, .77, .74, .75))
    size(e, 6, 12); spin(e, 30)
    gravity(e, 0.0)     # the OmnidirectionalBurst template falls under its own gravity; hot smoke rises
    e.set("InitializeParticle", "UsePositionOffset", True).set("InitializeParticle", "Position Offset", Link("User.PanOffset"))
    e.many("ShapeLocation", {"Sphere Radius": 2.0})
    e.many("AddVelocity", {"Velocity Mode": "In Cone", "Velocity Speed": rand_range(40, 120), "Cone Axis": vec(0, 0, 1), "Cone Angle": 35.0})
    e.force("Update/Forces/Drag"); e.set("Drag", "Drag", 1.5)
    e.force("Update/Forces/AccelerationForce"); e.set("AccelerationForce", "Acceleration", vec(0, 0, 30))
    grow(e, "lerp(1.0, 4.0, 1.0 - pow(1.0 - Particles.NormalizedAge, 2.0))")
    fade(e, fade_in_out(.05))
    flipbook(e, mi["Smoke"])

    e = s.emitter("Light", "SingleLoopingParticle")
    once(e, .12); lifetime(e, .07)
    e.props(bLocalSpace=True)
    light(e, 5000, 650, (1.0, .55, .22), fade_expr="pow(saturate(1.0 - Particles.NormalizedAge), 1.5)")
    e.renderer(bIsEnabled=False)
    s.compile()
    return s


def muzzle_energy(mi):
    s = System("NS_SoraVFX_Muzzle_Energy", "Alien charged rifle discharge: plasma star, shock ring, ionised sparks and vapour.")
    s.user("Tint", rgb(.35, .78, 1.0), "Plasma colour (cyan by default).")

    e = s.emitter("Star", "SimpleSpriteBurst")
    once(e, .1); burst(e, 1); lifetime(e, .06)
    color(e, Expr("float4(User.Tint.rgb * 160.0 * User.FlashScale, 1.0)"))
    size(e, 42); spin(e)
    fade(e, "pow(saturate(1.0 - Particles.NormalizedAge), 2.0)")
    e.renderer(Material=mi["FlashStar"])
    e.props(bLocalSpace=True)

    e = s.emitter("Ring", "SimpleSpriteBurst")
    once(e, .25); burst(e, 1); lifetime(e, .16)
    color(e, Expr("float4(User.Tint.rgb * 30.0 * User.FlashScale, 1.0)"))
    size(e, 18)
    e.set("InitializeParticle", "UsePositionOffset", True).set("InitializeParticle", "Position Offset", vec(8, 0, 0))
    grow(e, "lerp(1.0, 4.0, 1.0 - pow(1.0 - Particles.NormalizedAge, 3.0))")
    fade(e, "pow(saturate(1.0 - Particles.NormalizedAge), 1.5)")
    e.force("Update/Renderers/Sprite/SpriteFacingAndAlignment")
    e.many("SpriteFacingAndAlignment", {"WriteFacing": True, "Sprite Facing": vec(1, 0, 0)})
    e.renderer(Material=mi["FlashRing"], FacingMode="CustomFacingVector")
    e.props(bLocalSpace=True)

    e = s.emitter("Sparks", "DirectionalBurst")
    once(e, .5); burst(e, Expr("(int)(10 + 16 * User.FlashScale)")); lifetime(e, .08, .25)
    color(e, Expr("float4(User.Tint.rgb * 90.0 * User.FlashScale, 1.0)"))
    size2(e, (.5, 1.2), (.9, 2.4))
    e.many("AddVelocity", {"Velocity Speed": rand_range(1500, 4000), "Cone Axis": vec(1, 0, 0), "Cone Angle": 28.0})
    e.set("GravityForce", "Gravity", vec(0, 0, -120))
    fade(e, "saturate(1.0 - Particles.NormalizedAge)")
    e.many("ScaleSpriteSizeBySpeed", {"Max Scale Factor": unreal.Vector2D(1, 10), "Velocity Threshold": 3000.0})
    e.renderer(Material=mi["Spark"], Alignment="VelocityAligned")

    e = s.emitter("Vapour", "OmnidirectionalBurst")
    once(e, 1.5); burst(e, 5); lifetime(e, .5, 1.1)
    color(e, rgb(.72, .82, .9, .35))
    size(e, 6, 12); spin(e, 40)
    gravity(e, 0.0)     # as the pan smoke: not the template's falling puffs
    e.many("ShapeLocation", {"Sphere Radius": 3.0})
    e.many("AddVelocity", {"Velocity Mode": "In Cone", "Velocity Speed": rand_range(150, 500), "Cone Axis": vec(1, 0, 0), "Cone Angle": 30.0})
    e.force("Update/Forces/Drag"); e.set("Drag", "Drag", 4.0)
    grow(e, "lerp(1.0, 5.0, sqrt(Particles.NormalizedAge))")
    fade(e, fade_in_out(.05))
    dynamic_params(e, [0.0, "Particles.NormalizedAge * 0.5", None, None])
    flipbook(e, mi["Steam"])

    e = s.emitter("Light", "SingleLoopingParticle")
    once(e, .1); lifetime(e, .06)
    e.props(bLocalSpace=True)
    light(e, 2500, 450, (.4, .78, 1.0), fade_expr="saturate(1.0 - Particles.NormalizedAge)")
    e.renderer(bIsEnabled=False)
    s.compile()
    return s


# ---------------------------------------------------------------- emitter recipes

def _vec(value):
    return value if isinstance(value, unreal.Vector) else vec(*value)


def _num(value):
    return value if isinstance(value, (Expr, Link)) else float(value)


def shape(e, sphere=None, box=None, disc=None, offset=None):
    """Where particles are born, in the emitter's local frame."""
    if sphere is not None:
        e.many("ShapeLocation", {"Shape Primitive": "Sphere", "Sphere Radius": _num(sphere)})
    elif box is not None:
        e.many("ShapeLocation", {"Shape Primitive": "Box / Plane", "Box Size": box if isinstance(box, (Expr, Link)) else _vec(box)})
    elif disc is not None:
        e.many("ShapeLocation", {"Shape Primitive": "Ring / Disc", "Ring Radius": _num(disc), "Disc Coverage": 1.0})
    if offset is not None:
        e.set("InitializeParticle", "UsePositionOffset", True)
        e.set("InitializeParticle", "Position Offset", offset if isinstance(offset, (Expr, Link)) else _vec(offset))
    return e


def cone(e, speed, axis=(1, 0, 0), angle=30.0, inner=None):
    e.set("AddVelocity", "Velocity Mode", "In Cone")
    e.set("AddVelocity", "Velocity Speed", rand_range(*speed) if isinstance(speed, tuple) else _num(speed))
    e.set("AddVelocity", "Cone Axis", _vec(axis))
    e.set("AddVelocity", "Cone Angle", float(angle))
    if inner is not None:
        e.set("AddVelocity", "Inner Cone Angle", float(inner))
    return e


def gravity(e, z):
    e.force("Update/Forces/GravityForce")
    e.set("GravityForce", "Gravity", vec(0, 0, z))
    return e


def drag(e, amount):
    """Drag, fixed per particle within a (lo, hi) range or one value for all."""
    e.force("Update/Forces/Drag")
    e.set("Drag", "Drag", particle_random(e, DRAG, *amount) if isinstance(amount, tuple) else float(amount))
    return e


def lift(e, z):
    e.force("Update/Forces/AccelerationForce")
    e.set("AccelerationForce", "Acceleration", _vec(z) if isinstance(z, tuple) else vec(0, 0, z))
    return e


def curl(e, strength, frequency):
    e.force("Update/Forces/V2/CurlNoiseForce")
    e.many("CurlNoiseForce", {"Noise Strength": float(strength), "Noise Frequency": float(frequency)})
    return e


def collide(e, restitution=.3, friction=.6, gpu=False, kill=False):
    e.force("Collision/Collision")
    if gpu:
        e.set("Collision", "GPU Collision Type", "GPU Depth Buffer")
    e.many("Collision", {"Restitution": float(restitution), "Friction": float(friction)})
    if kill:
        e.set("Collision", "KillOnCollision", True)
    return e


def face_up(e, alignment=None, space_local=True):
    """Sprites lying in the ground plane (facing +Z), optionally aligned to a local axis."""
    e.force("Update/Renderers/Sprite/SpriteFacingAndAlignment")
    e.many("SpriteFacingAndAlignment", {"WriteFacing": True, "Sprite Facing": vec(0, 0, 1)})
    if alignment is not None:
        e.many("SpriteFacingAndAlignment", {"WriteAlignment": True, "Sprite Alignment": _vec(alignment)})
    e.renderer(FacingMode="CustomFacingVector", Alignment="CustomAlignment" if alignment is not None else "Unaligned")
    return e


def upright(e):
    """Camera-facing sprites that keep their texture's up along world +Z (flames, plumes)."""
    e.force("Update/Renderers/Sprite/SpriteFacingAndAlignment")
    e.many("SpriteFacingAndAlignment", {"WriteFacing": False, "WriteAlignment": True, "Sprite Alignment": vec(0, 0, 1),
                                        "Alignment Coordinate Space": "World"})
    e.renderer(Alignment="CustomAlignment", FacingMode="FaceCameraPlane", PivotInUVSpace={"x": 0.5, "y": 0.85})
    return e


def puffs(s, name, material, *, life, color_value, size_range, count=None, rate=None, duration=None, delay=0.0,
          sphere=4.0, box=None, disc=None, offset=None, speed=(0.0, 0.0), axis=(1, 0, 0), angle=30.0, inner=None,
          drag_amount=2.0, rise=0.0, curl_amount=None, grow_to=3.0, alpha=None, heat=None, erode=.3, spin_rate=20.0,
          local=False, gravity_z=0.0, frames=8):
    """Billowing sprites: smoke, dust, steam, vapour and fireballs play an 8x8 flipbook.

    frames=None draws the whole quad instead, for materials that pick one cell of a 2x2 sheet themselves
    (the water cells): the sprite renderer maps a particle's UVs onto one sub-image of the flipbook, so an
    8x8 renderer would show such a material only a sixty-fourth of its cell.
    """
    burst_mode = count is not None
    e = s.emitter(name, "OmnidirectionalBurst" if burst_mode else "Fountain")
    if burst_mode:
        once(e, duration if duration is not None else life[-1] + delay + .1)
        burst(e, count, delay)
    else:
        forever(e)
        e.set("SpawnRate", "SpawnRate", _num(rate))
    lifetime(e, *life)
    color(e, color_value)
    size(e, *size_range)
    spin(e, spin_rate)
    shape(e, sphere=sphere if box is None and disc is None else None, box=box, disc=disc, offset=offset)
    cone(e, speed, axis, angle, inner)
    gravity(e, gravity_z)
    drag(e, drag_amount)
    if rise:
        lift(e, rise)
    if curl_amount:
        curl(e, *curl_amount)
    grow(e, f"lerp(1.0, {grow_to:.3f}, 1.0 - pow(1.0 - {AGE}, 2.2))")
    fade(e, alpha or fade_in_out(.05, 1.2))
    dynamic_params(e, [heat if heat is not None else 0.0, f"{AGE} * {erode:.3f}", None, None])
    if frames:
        flipbook(e, material, frames)
    else:
        e.renderer(Material=material, SubImageSize={"x": 1, "y": 1}, bSubImageBlend=False, SortMode="ViewDepth")
    if local:
        e.props(bLocalSpace=True)
    return e


def sparks(s, name, *, count=None, rate=None, life, color_value, speed, axis=(1, 0, 0), angle=30.0, width=(.5, 1.0),
           length=(1.2, 2.5), stretch=8.0, gravity_z=-980.0, drag_amount=(.5, 1.5), bounce=None, material=None, duration=None,
           cool=True, curl_amount=None, sphere=None, disc=None, box=None, offset=None):
    """Velocity-stretched glowing streaks: sparks, burning grains, embers."""
    e = s.emitter(name, "DirectionalBurst")
    if count is not None:
        once(e, duration if duration is not None else life[-1] + .1)
        burst(e, count)
    else:
        forever(e)
        e.remove("SpawnBurst_Instantaneous")
        e.add("Emitter/SpawnRate", EU)
        e.set("SpawnRate", "SpawnRate", _num(rate))
    lifetime(e, *life)
    color(e, color_value)
    size2(e, (width[0], length[0]), (width[1], length[1]))
    if sphere is not None or disc is not None or box is not None:
        e.add("Spawn/Location/V2/ShapeLocation", PS, before="AddVelocity")
        shape(e, sphere=sphere, disc=disc, box=box, offset=offset)
    elif offset is not None:
        shape(e, offset=offset)
    cone(e, speed, axis, angle)
    e.set("GravityForce", "Gravity", vec(0, 0, gravity_z))
    drag(e, drag_amount)
    if curl_amount:
        curl(e, *curl_amount)
    if bounce is not None:
        collide(e, restitution=bounce, friction=.4)
    cooling = "lerp(float3(1,1,1), float3(0.45, 0.16, 0.04), " + AGE + ")" if cool else None
    fade(e, f"pow(saturate(1.0 - {AGE}), 0.8)", cooling)
    e.many("ScaleSpriteSizeBySpeed", {"Min Scale Factor": unreal.Vector2D(1, 1), "Max Scale Factor": unreal.Vector2D(1, stretch),
                                      "Velocity Threshold": 1500.0})
    e.renderer(Material=material, Alignment="VelocityAligned")
    return e


def debris(s, name, material, *, count, life, speed, scale_min, scale_max, axis=(1, 0, 0), angle=40.0,
           mesh="/Engine/BasicShapes/Cube.Cube", tint=(1.0, 1.0, 1.0), bounce=.25, spin_rate=6.0):
    """Mesh chips and splinters with the environment's PBR surfaces, bouncing off the world."""
    e = s.emitter(name, "UpwardMeshBurst")
    once(e, life[-1] + .1)
    burst(e, count)
    lifetime(e, *life)
    color(e, rgb(*tint))
    e.many("InitializeParticle", {"Mesh Scale Mode": "Random Non-Uniform", "Mesh Scale Min": _vec(scale_min),
                                  "Mesh Scale Max": _vec(scale_max)})
    cone(e, speed, axis, angle)
    e.set("UpdateMeshOrientation", "Rotation Rate", float(spin_rate))
    e.set("Drag", "Drag", .4)
    collide(e, restitution=bounce, friction=.7)
    e.set("ScaleMeshSize", "Scale Factor", Expr(f"float3(1.0, 1.0, 1.0) * (1.0 - {ss(0.85, 1.0, AGE)})"))
    e.set("ScaleColor", "Scale Alpha", 1.0)
    e.renderer("NiagaraMeshRendererProperties", Meshes=[{"mesh": mesh}], bOverrideMaterials=True,
               OverrideMaterials=[{"explicitMat": path_of(material)}], bCastShadows=False)
    return e


def flash(s, name, material, *, size_value, color_value, life, offset=None, rotate=True, local=True, power=2.0):
    e = s.emitter(name, "SimpleSpriteBurst")
    once(e, life + .05)
    burst(e, 1)
    lifetime(e, life)
    color(e, color_value)
    size(e, *size_value) if isinstance(size_value, tuple) else size(e, size_value)
    if rotate:
        spin(e)
    if offset is not None:
        shape(e, offset=offset)
    fade(e, f"pow(saturate(1.0 - {AGE}), {power:.2f})")
    e.renderer(Material=material)
    if local:
        e.props(bLocalSpace=True)
    return e


def light_burst(s, name, *, lumens, radius, color_rgb, life, offset=None, power=1.5):
    e = s.emitter(name, "SingleLoopingParticle")
    once(e, life + .05)
    lifetime(e, life)
    if offset is not None:
        shape(e, offset=offset)
    e.props(bLocalSpace=True)
    light(e, lumens, radius, color_rgb, fade_expr=f"pow(saturate(1.0 - {AGE}), {power:.2f})")
    e.renderer(bIsEnabled=False)
    return e


def steady_light(s, name, *, lumens, radius, color_rgb, flicker, offset=None, megalights=True):
    """An always-on light from one particle renewed every second.

    It does not flash, so User.FlashScale leaves its brightness alone and scales only the flicker amplitude.
    """
    e = s.emitter(name, "SingleLoopingParticle")
    forever(e, 1.0)
    if offset is not None:
        shape(e, offset=offset)
    e.props(bLocalSpace=True)
    light(e, lumens, radius, color_rgb, flash=False, flicker=flicker, megalights=megalights)
    e.renderer(bIsEnabled=False)
    return e


# ---------------------------------------------------------------- beams and trails

def beam_energy(mi):
    s = System("NS_SoraVFX_Beam_Energy", "Energy beam or tracer from the component to User.BeamEnd (world space).")
    s.user("BeamEnd", vec(3000.0, 0.0, 0.0), "World-space end point (the hit).")
    s.user("Tint", rgb(.35, .78, 1.0), "Beam colour.")
    s.user("Width", 3.0, "Core width in cm; the halo is four times wider.")
    s.user("Duration", .09, "Seconds the beam lasts (a tracer ~0.09 s, a sustained boss beam longer).")
    for name, width, intensity in (("Core", "User.Width", 120.0), ("Halo", "User.Width * 4.0", 10.0)):
        e = s.emitter(name, "DynamicBeam")
        once(e, "User.Duration + 0.05")
        burst(e, 24)
        lifetime(e, .1)
        e.set("InitializeParticle", "Lifetime", Link("User.Duration"))
        e.many("BeamEmitterSetup", {"Absolute Beam Start": False, "Beam Start": vec(0, 0, 0), "Absolute Beam End": True,
                                    "Beam End": Link("User.BeamEnd")})
        e.set("BeamWidth", "Beam Width", Expr(width))
        e.set("Color", "Color", Expr(f"float4(User.Tint.rgb * {intensity:.1f} * User.FlashScale, 1.0)"))
        e.set("Color", "Scale Alpha", Expr(f"pow(saturate(1.0 - {AGE}), 0.7)"))
        e.renderer("NiagaraRibbonRendererProperties", Material=mi["Beam"], FacingMode="Screen",
                   UV0Settings={"distributionMode": "ScaledUniformly"})
    s.compile()
    return s


def trail_projectile(mi):
    s = System("NS_SoraVFX_Trail_Projectile", "Ribbon behind a moving projectile: a bright bolt trail or a faint arrow wake.", "ET_SoraVFX_Gameplay")
    s.user("Tint", rgb(.35, .78, 1.0), "Trail colour; use a pale grey with low Intensity for arrows.")
    s.user("Intensity", 40.0, "Emissive cd/m2 at the head (arrows about 1.5).")
    s.user("Width", 1.6, "Ribbon width in cm at the head.")
    e = s.emitter("Trail", "LocationBasedRibbon")
    forever(e)
    e.add("Emitter/SpawnRate", EU)
    e.set("SpawnRate", "SpawnRate", 120.0)
    lifetime(e, .22)
    color(e, Expr("float4(User.Tint.rgb * User.Intensity * User.FlashScale, 1.0)"))
    e.many("InitializeParticle", {"Ribbon Width Mode": "Direct Set", "Ribbon Width": Link("User.Width")})
    fade(e, f"pow(saturate(1.0 - {AGE}), 1.6)")
    e.renderer("NiagaraRibbonRendererProperties", Material=mi["Beam"], FacingMode="Screen",
               UV0Settings={"distributionMode": "ScaledUniformly"})
    s.compile()
    return s


def blade_trail(mi):
    s = System("NS_SoraVFX_BladeTrail", "A faint sheen of displaced air behind a swung blade; attach at the blade's middle, +X along the blade.", "ET_SoraVFX_Gameplay")
    s.user("Width", 72.0, "Length of the edge that sweeps, cm (a katana's ha about 70).")
    s.user("Tint", rgb(.78, .82, .86), "Sheen colour (cool steel).")
    s.user("Intensity", .9, "Emissive cd/m2 of the sheen; kept low so it reads as air, not a light.")
    e = s.emitter("Sheen", "LocationBasedRibbon")
    forever(e)
    e.add("Emitter/SpawnRate", EU)
    e.set("SpawnRate", "SpawnRate", 110.0)
    lifetime(e, .15)
    color(e, Expr("float4(User.Tint.rgb * User.Intensity, 0.32)"))
    e.many("InitializeParticle", {"Ribbon Width Mode": "Direct Set", "Ribbon Width": Link("User.Width"),
                                  "Ribbon Facing Mode": "Direct Set", "Ribbon Facing Vector": Link("Engine.Owner.SystemXAxis")})
    fade(e, f"pow(saturate(1.0 - {AGE}), 2.0)")
    e.renderer("NiagaraRibbonRendererProperties", Material=mi["Trail"], FacingMode="CustomSideVector",
               UV0Settings={"distributionMode": "ScaledUniformly"})
    s.compile()
    return s


# ---------------------------------------------------------------- impacts (+X is the surface normal)

def impact_wood(mi):
    s = System("NS_SoraVFX_Impact_Wood", "Ball or blade into timber: splinters, chips, wood dust.")
    debris(s, "Splinters", mi["Wood"], count=14, life=(1.4, 2.6), speed=(250, 750), angle=50,
           scale_min=(.018, .003, .002), scale_max=(.05, .007, .004), spin_rate=9.0)
    debris(s, "Chips", mi["Wood"], count=9, life=(1.2, 2.2), speed=(150, 500), angle=60,
           scale_min=(.006, .005, .003), scale_max=(.014, .011, .006))
    puffs(s, "Dust", mi["Dust"], count=7, life=(1.0, 1.8), color_value=rgb(.55, .46, .36, .75), size_range=(8, 16),
          speed=(80, 260), angle=35, drag_amount=5.0, grow_to=4.5, rise=15.0, erode=.4)
    sparks(s, "Motes", count=18, life=(.6, 1.4), color_value=rgb(.35, .29, .22, .8), speed=(100, 420), angle=55,
           width=(.25, .45), length=(.3, .6), stretch=2.0, gravity_z=-500.0, drag_amount=(2.0, 4.0), material=mi["Dust"], cool=False)
    s.compile()
    return s


def impact_stone(mi):
    s = System("NS_SoraVFX_Impact_Stone", "Hit on stone or plaster: chips, grit and grey dust, a few sparks from steel.")
    s.user("SparkAmount", .3, "0 for a lead ball or arrow, 1 for a steel edge striking stone.")
    debris(s, "Chips", mi["Stone"], count=12, life=(1.2, 2.4), speed=(250, 800), angle=45,
           scale_min=(.005, .004, .003), scale_max=(.016, .012, .009), bounce=.35)
    puffs(s, "Dust", mi["Dust"], count=6, life=(1.0, 1.9), color_value=rgb(.6, .6, .57, .6), size_range=(6, 14),
          speed=(90, 300), angle=35, drag_amount=5.0, grow_to=5.0, rise=10.0, erode=.4)
    sparks(s, "Sparks", count=Expr("(int)(8.0 * User.SparkAmount * User.FlashScale)"), life=(.15, .45),
           color_value=hlsl_color(220.0, 100.0, 22.0, flash=True), speed=(400, 1300), angle=55, bounce=.35,
           material=mi["Spark"])
    s.compile()
    return s


def impact_dirt(mi):
    s = System("NS_SoraVFX_Impact_Dirt", "Hit on earth: clods, a brown burst and dust rolling out along the ground.")
    debris(s, "Clods", mi["Soil"], count=10, life=(1.0, 1.8), speed=(200, 650), angle=35,
           mesh="/Engine/BasicShapes/Sphere.Sphere", scale_min=(.01, .008, .008), scale_max=(.025, .02, .018), bounce=.1)
    puffs(s, "Burst", mi["Dust"], count=6, life=(.8, 1.5), color_value=rgb(.42, .35, .27, .75), size_range=(10, 20),
          speed=(200, 520), angle=18, drag_amount=4.0, grow_to=4.0, gravity_z=-120.0, erode=.45)
    puffs(s, "Roll", mi["Dust"], count=8, life=(1.4, 2.4), color_value=rgb(.46, .39, .31, .45), size_range=(14, 24),
          speed=(150, 380), angle=88, inner=70, drag_amount=3.5, grow_to=5.0, rise=8.0, erode=.4)
    s.compile()
    return s


def impact_metal(mi):
    s = System("NS_SoraVFX_Impact_Metal", "Hit on iron or alien alloy: bouncing sparks, a pin flash, a wisp of smoke.")
    sparks(s, "Sparks", count=Expr("(int)(16 + 28 * User.FlashScale)"), life=(.2, .7),
           color_value=hlsl_color(300.0, 140.0, 32.0, flash=True), speed=(500, 1700), angle=65, bounce=.45,
           material=mi["Spark"])
    flash(s, "Flash", mi["FlashStar"], size_value=(8, 12), color_value=hlsl_color(60.0, 35.0, 14.0, flash=True), life=.04)
    puffs(s, "Wisp", mi["Smoke"], count=2, life=(.6, 1.0), color_value=rgb(.45, .44, .43, .35), size_range=(4, 7),
          speed=(40, 90), angle=20, drag_amount=3.0, grow_to=4.0, rise=25.0)
    light_burst(s, "Light", lumens=600, radius=220, color_rgb=(1.0, .62, .3), life=.06)
    s.compile()
    return s


def impact_fur(mi):
    s = System("NS_SoraVFX_Impact_Fur", "Hit on a cat (blood-free): a puff of shed fur and dander drifting down.")
    s.user("FurTint", rgb(.62, .58, .52), "Coat colour of the struck character.")
    e = s.emitter("Tufts", "DirectionalBurst")
    once(e, 2.6); burst(e, 12); lifetime(e, 1.4, 2.4)
    color(e, Expr("float4(User.FurTint.rgb, 1.0)"))
    size(e, 6.0, 11.0); spin(e, 140)
    cone(e, (90, 260), (1, 0, 0), 60)
    e.set("GravityForce", "Gravity", vec(0, 0, -160))
    drag(e, (3.0, 5.0))
    curl(e, 45.0, 90.0)
    fade(e, fade_in_out(.02, .8))
    e.many("ScaleSpriteSizeBySpeed", {"Min Scale Factor": unreal.Vector2D(1, 1), "Max Scale Factor": unreal.Vector2D(1, 1)})
    sheet_cell(e, mi["Fur"], 0, 3)
    puffs(s, "Dander", mi["Dust"], count=4, life=(.8, 1.4), color_value=rgb(.7, .67, .62, .55), size_range=(6, 12),
          speed=(60, 160), angle=35, drag_amount=4.0, grow_to=4.0, rise=10.0)
    s.compile()
    return s


# ---------------------------------------------------------------- combat

def parry_sparks(mi):
    s = System("NS_SoraVFX_ParrySparks", "Steel on steel: a spray of white-hot sparks off the contact, a pin flash and light.")
    sparks(s, "Sparks", count=Expr("(int)(24 + 36 * User.FlashScale)"), life=(.18, .6),
           color_value=hlsl_color(350.0, 200.0, 65.0, flash=True), speed=(500, 1600), angle=75, bounce=.4,
           width=(.35, .7), length=(1.0, 2.0), material=mi["Spark"])
    flash(s, "Flash", mi["FlashStar"], size_value=(12, 18), color_value=hlsl_color(70.0, 50.0, 30.0, flash=True), life=.045)
    light_burst(s, "Light", lumens=1500, radius=300, color_rgb=(1.0, .78, .5), life=.08)
    puffs(s, "Wisp", mi["Smoke"], count=2, life=(.5, .9), color_value=rgb(.5, .5, .5, .25), size_range=(3, 6),
          speed=(30, 80), angle=40, drag_amount=3.0, grow_to=4.0, rise=20.0)
    s.compile()
    return s


def explosion(mi):
    s = System("NS_SoraVFX_Explosion", "Hanabi grenade or rocket: flash, fireball rolling into smoke, debris, sparks, ground dust.")
    flash(s, "Flash", mi["FlashFace"], size_value=(260, 320), color_value=hlsl_color(300.0, 170.0, 55.0, flash=True), life=.08)
    light_burst(s, "Light", lumens=30000, radius=1600, color_rgb=(1.0, .6, .28), life=.35, offset=(60, 0, 0))
    puffs(s, "Fireball", mi["Fireball"], count=10, life=(.9, 1.4), color_value=rgb(.3, .28, .26, .95), size_range=(120, 180),
          sphere=40.0, speed=(250, 800), axis=(1, 0, 0), angle=70, drag_amount=3.0, rise=(160, 0, 0), grow_to=3.2,
          heat=f"pow(saturate(1.0 - {AGE} * 1.25), 1.5)", erode=.35, alpha=fade_in_out(.02, 1.0), spin_rate=35)
    puffs(s, "Smoke", mi["Smoke"], count=18, delay=.12, life=(4.0, 7.0), color_value=rgb(.2, .19, .18, 1.0), size_range=(130, 200),
          sphere=60.0, speed=(120, 420), angle=55, drag_amount=1.6, rise=(55, 0, 0), curl_amount=(70.0, 400.0), grow_to=4.5,
          heat=f"pow(saturate(1.0 - Particles.Age * 3.0), 2.0) * 0.4", erode=.4, alpha=fade_in_out(.06, 1.3))
    puffs(s, "GroundDust", mi["Dust"], count=12, life=(1.6, 3.0), color_value=rgb(.5, .45, .38, .6), size_range=(60, 110),
          speed=(700, 1300), angle=89, inner=80, drag_amount=4.5, grow_to=3.5, erode=.4)
    debris(s, "Debris", mi["Stone"], count=18, life=(1.8, 3.2), speed=(600, 1800), angle=65,
           scale_min=(.02, .015, .012), scale_max=(.07, .05, .04), bounce=.3, spin_rate=5.0)
    sparks(s, "Sparks", count=Expr("(int)(30 + 50 * User.FlashScale)"), life=(.4, 1.3),
           color_value=hlsl_color(180.0, 70.0, 15.0, flash=True), speed=(700, 2200), angle=75, bounce=.3,
           width=(.6, 1.2), length=(1.5, 3.0), material=mi["Spark"])
    sparks(s, "Embers", count=30, life=(1.5, 3.2), color_value=rgb(60.0, 18.0, 3.0), speed=(250, 800), angle=80,
           width=(.5, .9), length=(.5, .9), stretch=2.0, gravity_z=-180.0, drag_amount=(1.5, 3.0),
           curl_amount=(120.0, 300.0), material=mi["Spark"])
    s.compile()
    return s


def hanabi_fire_zone(mi):
    s = System("NS_SoraVFX_Hanabi_FireZone", "Area-denial fire on the ground within User.Radius; loops until deactivated.", "ET_SoraVFX_Gameplay")
    s.user("Radius", 300.0, "Radius of the burning area, cm (the kernel's zone radius).")
    e = s.emitter("Flames", "Fountain")
    forever(e)
    e.set("SpawnRate", "SpawnRate", Expr("min(max(User.Radius * User.Radius * 0.0006, 8.0), 150.0)"))
    lifetime(e, .55, 1.05)
    color(e, rgb(1.0, 1.0, 1.0, 1.0))
    size2(e, (70, 80), (120, 150))
    e.set("InitializeParticle", "Sprite Rotation Mode", "Unset")
    shape(e, disc=Link("User.Radius"))
    cone(e, (20, 70), (0, 0, 1), 12)
    e.set("GravityForce", "Gravity", vec(0, 0, 0))
    e.set("Drag", "Drag", 1.0)
    lift(e, 60.0)
    fade(e, fade_in_out(.12, 1.2))
    dynamic_params(e, [particle_random(e, HEAT, .85, 1.15), None, None, None])
    flipbook(e, mi["Fire"], loop_seconds=1.0, sort="ViewDepth")
    upright(e)
    sparks(s, "Embers", rate=Expr("min(max(User.Radius * 0.12, 8.0), 60.0)"), life=(1.0, 2.4), color_value=rgb(60.0, 18.0, 3.0),
           speed=(150, 420), axis=(0, 0, 1), angle=25, width=(.4, .8), length=(.5, 1.0), stretch=3.0, gravity_z=40.0,
           drag_amount=(1.0, 2.0), curl_amount=(160.0, 250.0), material=mi["Spark"], disc=Link("User.Radius"))
    puffs(s, "Smoke", mi["Smoke"], rate=Expr("min(max(User.Radius * 0.03, 3.0), 14.0)"), life=(3.0, 5.0),
          color_value=rgb(.19, .18, .17, .5), size_range=(70, 120), disc=Link("User.Radius"), offset=(0, 0, 120),
          speed=(60, 150), axis=(0, 0, 1), angle=15, drag_amount=1.0, rise=35.0, curl_amount=(40.0, 500.0), grow_to=3.5,
          heat="0.25 * pow(saturate(1.0 - Particles.Age * 1.5), 2.0)", erode=.45, alpha=fade_in_out(.15, 1.4))
    steady_light(s, "Light", lumens=2600, radius="User.Radius * 2.6", color_rgb=(1.0, .55, .22), flicker=.3, offset=(0, 0, 70))
    s.compile()
    return s


def kusushi_heal(mi):
    s = System("NS_SoraVFX_Kusushi_Heal", "Kusushi's healing pulse: jade-gold motes rising from a ring, a soft ground ring.")
    s.user("Radius", 120.0, "Ring radius, cm.")
    s.user("Tint", rgb(.55, 1.0, .62), "Mote colour (jade with a gold cast).")
    e = s.emitter("Motes", "Fountain")
    once(e, .5)
    lifetime(e, 1.0, 1.7)
    e.set("SpawnRate", "SpawnRate", 80.0)
    color(e, Expr("float4(User.Tint.rgb * 10.0, 1.0)"))
    size(e, 2.5, 5.5)
    shape(e, disc=Link("User.Radius"))
    cone(e, (60, 150), (0, 0, 1), 10)
    e.set("GravityForce", "Gravity", vec(0, 0, 0))
    e.set("Drag", "Drag", .6)
    e.force("Update/Forces/VortexForce")
    e.set("VortexForce", "Vortex Force Amount", 60.0)
    fade(e, fade_in_out(.15, 1.0))
    e.renderer(Material=mi["Glow"])
    e = s.emitter("Ring", "SimpleSpriteBurst")
    once(e, 1.0); burst(e, 1); lifetime(e, .9)
    color(e, Expr("float4(User.Tint.rgb * 3.0, 0.8)"))
    size(e, 2.0)
    e.set("InitializeParticle", "Uniform Sprite Size", Expr("User.Radius * 2.2"))
    shape(e, offset=(0, 0, 2))
    fade(e, fade_in_out(.1, 1.5))
    dynamic_params(e, [f"saturate({AGE} * 1.6)", 3.1416, 0.0, None])
    face_up(e)
    e.renderer(Material=mi["Ring"])
    e.props(bLocalSpace=True)
    light_burst(s, "Light", lumens=450, radius=350, color_rgb=(.55, 1.0, .62), life=1.0, offset=(0, 0, 60), power=1.0)
    s.compile()
    return s


def kusushi_ward(mi):
    s = System("NS_SoraVFX_Kusushi_Ward", "Kusushi's protective ward: talismans circling at User.Radius, drifting motes, faint light.", "ET_SoraVFX_Gameplay")
    s.user("Radius", 160.0, "Ward radius, cm.")
    s.user("Tint", rgb(.55, 1.0, .62), "Mote and light colour.")
    e = s.emitter("Talismans", "SimpleSpriteBurst")
    forever(e, 6.0)
    burst(e, 6)
    lifetime(e, 6.0)
    color(e, rgb(1.0, 1.0, 1.0))
    size2(e, (10, 28), (11, 30))
    spin(e)
    # Six talismans evenly spaced on the ward circle, turning slowly and bobbing (local space).
    phase = "((float)Particles.UniqueID * 1.0472 + Emitter.Age * 0.7)"
    e.write(PU, "Particles.Position", "position",
            f"float3(cos({phase}) * User.Radius, sin({phase}) * User.Radius, 110.0 + 10.0 * sin(Emitter.Age * 1.3 + (float)Particles.UniqueID))")
    fade(e, fade_in_out(.08, .3))
    sheet_cell(e, mi["Scrap"], 0, 1)
    e.props(bLocalSpace=True)
    e = s.emitter("Motes", "Fountain")
    forever(e)
    e.set("SpawnRate", "SpawnRate", 14.0)
    lifetime(e, 1.6, 2.6)
    color(e, Expr("float4(User.Tint.rgb * 8.0, 1.0)"))
    size(e, 1.5, 3.5)
    shape(e, disc=Link("User.Radius"))
    cone(e, (20, 60), (0, 0, 1), 15)
    e.set("GravityForce", "Gravity", vec(0, 0, 0))
    fade(e, fade_in_out(.2, 1.0))
    e.renderer(Material=mi["Glow"])
    steady_light(s, "Light", lumens=260, radius="User.Radius * 2.2", color_rgb="User.Tint.rgb", flicker=.08, offset=(0, 0, 90))
    s.compile()
    return s


def shinobi_decoy(mi):
    s = System("NS_SoraVFX_Shinobi_Decoy", "A shinobi decoy dispersing: a smoke-ball burst, talisman scraps and leaves fluttering down.")
    puffs(s, "Smoke", mi["Smoke"], count=16, life=(1.8, 3.2), color_value=rgb(.72, .72, .7, .85), size_range=(35, 60),
          sphere=30.0, offset=(0, 0, 90), speed=(250, 650), axis=(0, 0, 1), angle=100, drag_amount=5.0, rise=20.0,
          curl_amount=(50.0, 300.0), grow_to=4.0, erode=.45, alpha=fade_in_out(.03, 1.2))
    for name, first, last, count, tint in (("Talismans", 0, 1, 22, (1.0, 1.0, 1.0)), ("Leaves", 2, 2, 8, (1.0, .95, .9))):
        e = s.emitter(name, "DirectionalBurst")
        once(e, 4.5); burst(e, count); lifetime(e, 2.5, 4.2)
        color(e, rgb(*tint))
        size(e, 5.0, 9.0); spin(e, 220)
        e.add("Spawn/Location/V2/ShapeLocation", PS, before="AddVelocity")
        shape(e, sphere=35.0, offset=(0, 0, 100))
        cone(e, (250, 600), (0, 0, 1), 80)
        e.set("GravityForce", "Gravity", vec(0, 0, -260))
        drag(e, (2.5, 4.0))
        curl(e, 110.0, 150.0)
        fade(e, fade_in_out(.01, .4))
        e.many("ScaleSpriteSizeBySpeed", {"Min Scale Factor": unreal.Vector2D(1, 1), "Max Scale Factor": unreal.Vector2D(1, 1)})
        sheet_cell(e, mi["Scrap"], first, last)
    s.compile()
    return s


def karakuri_build_dust(mi):
    s = System("NS_SoraVFX_Karakuri_BuildDust", "Karakuri raising a barricade: dust and shavings along User.Width while building.", "ET_SoraVFX_Ambient")
    s.user("Width", 220.0, "Length of the barricade footprint along local Y, cm.")
    puffs(s, "Dust", mi["Dust"], rate=16.0, life=(1.2, 2.2), color_value=rgb(.6, .54, .45, .5), size_range=(25, 45),
          box=Expr("float3(40.0, User.Width, 4.0)"), speed=(40, 140), axis=(0, 0, 1), angle=60, drag_amount=3.0,
          grow_to=3.0, rise=10.0, erode=.4, alpha=fade_in_out(.1, 1.2))
    e = debris(s, "Shavings", mi["Wood"], count=1, life=(.8, 1.6), speed=(150, 420), axis=(0, 0, 1), angle=50,
               scale_min=(.012, .006, .001), scale_max=(.03, .012, .002), spin_rate=12.0)
    forever(e)
    e.remove("SpawnBurst_Instantaneous")
    e.add("Emitter/SpawnRate", EU)
    e.set("SpawnRate", "SpawnRate", 7.0)
    e.add("Spawn/Location/V2/ShapeLocation", PS, before="AddVelocity")
    shape(e, box=Expr("float3(30.0, User.Width, 2.0)"))
    sparks(s, "HammerSparks", rate=Expr("3.0 * User.FlashScale"), life=(.12, .35), color_value=hlsl_color(220.0, 100.0, 22.0, flash=True),
           speed=(250, 700), axis=(0, 0, 1), angle=60, material=mi["Spark"], box=Expr("float3(20.0, User.Width, 2.0)"),
           offset=(0, 0, 40))
    s.compile()
    return s


# ---------------------------------------------------------------- telegraphs (+X forward, lying on the ground)

def telegraph_beam(mi):
    s = System("NS_SoraVFX_Telegraph_Beam", "Boss beam windup: a lane along +X that fills over User.Duration and a charge glow.", "ET_SoraVFX_Gameplay")
    s.user("TelegraphColor", rgb(.1, .8, 1.0), "From the settings palette (cyan: a locked aim or beam).")
    s.user("Length", 2500.0, "Lane length, cm.")
    s.user("Width", 160.0, "Lane width, cm.")
    s.user("Duration", 1.2, "Windup seconds; the lane is full when the beam fires.")
    e = s.emitter("Lane", "SimpleSpriteBurst")
    once(e, "User.Duration + 0.1"); burst(e, 1)
    lifetime(e, 1.0)
    e.set("InitializeParticle", "Lifetime", Expr("User.Duration + 0.05"))
    color(e, Expr("float4(User.TelegraphColor.rgb * 6.0, 0.9)"))
    e.many("InitializeParticle", {"Sprite Size Mode": "Non-Uniform", "Sprite Size": Expr("float2(User.Width, User.Length)")})
    shape(e, offset=(0, 0, 3))
    fade(e, "1.0")
    dynamic_params(e, [f"saturate(Particles.Age / max(User.Duration, 0.01))", 0.0, "0.6 * User.FlashScale", None])
    face_up(e, alignment=(1, 0, 0))
    e.renderer(Material=mi["Lane"], PivotInUVSpace={"x": 0.5, "y": 1.0})
    e.props(bLocalSpace=True)
    e = s.emitter("Charge", "SimpleSpriteBurst")
    once(e, "User.Duration + 0.1"); burst(e, 1)
    e.set("InitializeParticle", "Lifetime", Expr("User.Duration + 0.05"))
    color(e, Expr("float4(User.TelegraphColor.rgb * 30.0 * User.FlashScale, 1.0)"))
    size(e, 20.0)
    shape(e, offset=(20, 0, 120))
    grow(e, f"lerp(0.4, 3.0, {AGE} * {AGE})")
    fade(e, ss(0.0, 0.2, AGE))
    e.renderer(Material=mi["Glow"])
    e.props(bLocalSpace=True)
    s.compile()
    return s


def telegraph_cleave(mi):
    s = System("NS_SoraVFX_Telegraph_Cleave", "Boss cleave or area windup: a wedge of User.ArcDegrees (360 = a disc) that fills over User.Duration.", "ET_SoraVFX_Gameplay")
    s.user("TelegraphColor", rgb(1.0, .62, .12), "From the settings palette (amber: a blow or an area).")
    s.user("Radius", 450.0, "Reach, cm.")
    s.user("ArcDegrees", 120.0, "Total arc; 360 for a full area.")
    s.user("Duration", 1.0, "Windup seconds; the wedge is full when the blow lands.")
    e = s.emitter("Wedge", "SimpleSpriteBurst")
    once(e, "User.Duration + 0.1"); burst(e, 1)
    e.set("InitializeParticle", "Lifetime", Expr("User.Duration + 0.05"))
    color(e, Expr("float4(User.TelegraphColor.rgb * 6.0, 0.9)"))
    size(e, 2.0)
    e.set("InitializeParticle", "Uniform Sprite Size", Expr("User.Radius * 2.0"))
    shape(e, offset=(0, 0, 3))
    fade(e, "1.0")
    dynamic_params(e, ["saturate(Particles.Age / max(User.Duration, 0.01))", "User.ArcDegrees * 0.0087266",
                       "0.6 * User.FlashScale", None])
    face_up(e, alignment=(1, 0, 0))
    e.renderer(Material=mi["Wedge"])
    e.props(bLocalSpace=True)
    s.compile()
    return s


# ---------------------------------------------------------------- water

def water_sluice_rise(mi):
    s = System("NS_SoraVFX_Water_SluiceRise", "Water surging through an opened sluice: foam, spray, crown splashes, mist; +X downstream.", "ET_SoraVFX_Ambient")
    s.user("Width", 400.0, "Gate width along local Y, cm.")
    s.user("Flow", 1.0, "0 closed .. 1 full surge; scales every emitter.")
    e = s.emitter("Foam", "Fountain")
    forever(e)
    e.set("SpawnRate", "SpawnRate", Expr("40.0 * User.Flow * User.Width / 400.0"))
    lifetime(e, 1.6, 3.0)
    color(e, rgb(.86, .9, .92, .85))
    size(e, 40, 90); spin(e, 15)
    shape(e, box=Expr("float3(60.0, User.Width, 1.0)"))
    cone(e, (60, 180), (1, 0, 0), 20)
    e.set("GravityForce", "Gravity", vec(0, 0, 0))
    e.set("Drag", "Drag", .8)
    grow(e, f"lerp(0.8, 1.8, {AGE})")
    fade(e, fade_in_out(.15, 1.0))
    face_up(e)
    e.renderer(Material=mi["Foam"], SortMode="ViewDepth")
    e = s.emitter("Spray", "Fountain")
    forever(e)
    e.set("SpawnRate", "SpawnRate", Expr("70.0 * User.Flow * User.Width / 400.0"))
    lifetime(e, .6, 1.2)
    color(e, rgb(.82, .88, .92, .75))
    size(e, 12, 30); spin(e, 40)
    shape(e, box=Expr("float3(30.0, User.Width, 1.0)"))
    cone(e, Expr("(180.0 + rand(300.0)) * User.Flow"), (1, 0, 1.2), 35)
    e.set("Drag", "Drag", .5)
    grow(e, f"lerp(0.7, 1.6, {AGE})")
    fade(e, fade_in_out(.05, 1.0))
    e.renderer(Material=mi["Spray"], SortMode="ViewDepth")
    e = s.emitter("Crowns", "Fountain")
    forever(e)
    e.set("SpawnRate", "SpawnRate", Expr("6.0 * User.Flow * User.Width / 400.0"))
    lifetime(e, .35, .65)
    color(e, rgb(.85, .9, .93, .8))
    size(e, 50, 110)
    shape(e, box=Expr("float3(80.0, User.Width, 1.0)"), offset=(40, 0, 0))
    cone(e, (0, 1), (0, 0, 1), 1)
    e.set("GravityForce", "Gravity", vec(0, 0, 0))
    grow(e, f"lerp(0.5, 1.3, sqrt({AGE}))")
    fade(e, f"pow(saturate(1.0 - {AGE}), 1.5)")
    upright(e)
    e.renderer(Material=mi["Sheet"])
    puffs(s, "Mist", mi["Mist"], rate=Expr("4.0 * User.Flow * User.Width / 400.0"), life=(3.0, 5.0),
          color_value=rgb(.8, .85, .88, .2), size_range=(150, 280), box=Expr("float3(120.0, User.Width, 10.0)"),
          offset=(60, 0, 40), speed=(20, 60), axis=(1, 0, .3), angle=30, drag_amount=.6, rise=8.0, grow_to=2.0,
          alpha=fade_in_out(.25, 1.0), spin_rate=8.0, frames=None)
    s.compile()
    return s


def water_splash(mi):
    s = System("NS_SoraVFX_Water_Splash", "Something striking water (+X up out of the surface): crown sheets, droplets, mist, a foam ring.")
    e = s.emitter("Crown", "SimpleSpriteBurst")
    once(e, .8); burst(e, 3); lifetime(e, .4, .7)
    color(e, rgb(.85, .9, .93, .85))
    size(e, 40, 70); spin(e)
    grow(e, f"lerp(0.4, 1.4, sqrt({AGE}))")
    fade(e, f"pow(saturate(1.0 - {AGE}), 1.4)")
    upright(e)
    e.renderer(Material=mi["Sheet"])
    e = s.emitter("Droplets", "DirectionalBurst")
    once(e, 1.4); burst(e, 50); lifetime(e, .6, 1.2)
    color(e, rgb(.8, .86, .9, .8))
    size(e, 2.0, 5.0)
    cone(e, (200, 600), (1, 0, 0), 40)
    e.set("Drag", "Drag", .4)
    fade(e, f"pow(saturate(1.0 - {AGE}), 0.7)")
    e.renderer(Material=mi["Spray"])
    puffs(s, "Mist", mi["Mist"], count=3, life=(1.0, 1.8), color_value=rgb(.82, .86, .9, .25), size_range=(50, 90),
          speed=(40, 120), angle=30, drag_amount=2.0, grow_to=2.2, alpha=fade_in_out(.1, 1.0), frames=None)
    e = s.emitter("FoamRing", "SimpleSpriteBurst")
    once(e, 2.2); burst(e, 1); lifetime(e, 2.0)
    color(e, rgb(.88, .92, .94, .8))
    size(e, 40.0)
    grow(e, f"lerp(0.6, 3.0, sqrt({AGE}))")
    fade(e, f"pow(saturate(1.0 - {AGE}), 1.2)")
    face_up(e)
    e.renderer(Material=mi["Foam"])
    s.compile()
    return s


# ---------------------------------------------------------------- forge and steam

def forge_fire(mi):
    s = System("NS_SoraVFX_Forge_Fire", "Tatara or forge fire: flames whose heat follows User.Temperature, sparks with the bellows, soot, light.", "ET_SoraVFX_Ambient")
    s.user("Temperature", .5, "0 red heat .. 0.5 yamabuki .. 1 white heat (the chapter's three gauge states).")
    s.user("Bellows", .5, "0 idle .. 1 full bellows; raises flame height, sparks and roar.")
    s.user("Radius", 22.0, "Radius of the fire bed, cm.")
    e = s.emitter("Flames", "Fountain")
    forever(e)
    e.set("SpawnRate", "SpawnRate", Expr("18.0 + 26.0 * User.Bellows"))
    lifetime(e, .35, .65)
    color(e, rgb(1.0, 1.0, 1.0, 1.0))
    size2(e, (26, 34), (40, 60))
    e.set("InitializeParticle", "Sprite Rotation Mode", "Unset")
    shape(e, disc=Link("User.Radius"))
    cone(e, Expr("20.0 + rand(40.0) + 90.0 * User.Bellows"), (0, 0, 1), 10)
    e.set("GravityForce", "Gravity", vec(0, 0, 0))
    e.set("Drag", "Drag", 1.2)
    lift(e, 50.0)
    fade(e, fade_in_out(.12, 1.2))
    dynamic_params(e, [f"lerp(0.8, 1.45, User.Temperature) * {particle_random(e, HEAT, .9, 1.1)}", None, None, None])
    flipbook(e, mi["Fire"], loop_seconds=1.0)
    upright(e)
    sparks(s, "Sparks", rate=Expr("(6.0 + 45.0 * User.Bellows) * User.FlashScale"), life=(.6, 1.8),
           color_value=Expr("float4(lerp(float3(40.0, 12.0, 2.0), float3(90.0, 60.0, 28.0), User.Temperature) * User.FlashScale, 1.0)"),
           speed=(200, 650), axis=(0, 0, 1), angle=25, width=(.3, .6), length=(.6, 1.2), stretch=4.0, gravity_z=-250.0,
           drag_amount=(.8, 1.6), curl_amount=(120.0, 200.0), material=mi["Spark"], disc=Link("User.Radius"))
    puffs(s, "Soot", mi["Smoke"], rate=6.0, life=(2.0, 3.5), color_value=rgb(.14, .13, .12, .4), size_range=(30, 55),
          disc=Link("User.Radius"), offset=(0, 0, 70), speed=(60, 140), axis=(0, 0, 1), angle=12, drag_amount=1.0, rise=40.0,
          curl_amount=(30.0, 300.0), grow_to=3.5, erode=.45, alpha=fade_in_out(.2, 1.4))
    steady_light(s, "Light", lumens="2400.0 + 1600.0 * User.Bellows", radius=700,
                 color_rgb="lerp(float3(1.0, 0.33, 0.08), float3(1.0, 0.86, 0.62), User.Temperature)", flicker=.22,
                 offset=(0, 0, 40))
    s.compile()
    return s


def steam(mi):
    s = System("NS_SoraVFX_Steam", "Steam rising from a pot, vent or quenched iron; loops.", "ET_SoraVFX_Ambient")
    s.user("Rate", 1.0, "0 .. 1 amount of steam.")
    puffs(s, "Steam", mi["Steam"], rate=Expr("16.0 * User.Rate"), life=(1.2, 2.4), color_value=rgb(.9, .92, .94, .45),
          size_range=(10, 20), sphere=6.0, speed=(60, 170), axis=(0, 0, 1), angle=15, drag_amount=1.0, rise=30.0,
          curl_amount=(40.0, 150.0), grow_to=6.0, erode=.55, alpha=fade_in_out(.1, 1.3))
    s.compile()
    return s


def steam_burst(mi):
    s = System("NS_SoraVFX_Steam_Burst", "A quench hiss: one violent burst of steam.")
    puffs(s, "Steam", mi["Steam"], count=14, life=(1.0, 2.2), color_value=rgb(.92, .93, .95, .6), size_range=(14, 26),
          sphere=10.0, speed=(200, 520), axis=(0, 0, 1), angle=35, drag_amount=3.0, rise=40.0, curl_amount=(60.0, 180.0),
          grow_to=5.5, erode=.55, alpha=fade_in_out(.04, 1.3))
    s.compile()
    return s


# ---------------------------------------------------------------- weather and light

def rain(mi):
    s = System("NS_SoraVFX_Rain", "Rain in a 30 m box above the component (put it at ground level under the player); GPU.", "ET_SoraVFX_Ambient")
    s.user("Intensity", 1.0, "0 .. 1 (1 about a heavy shower).")
    s.user("Wind", vec(120.0, 40.0, 0.0), "Horizontal wind, cm/s.")
    e = s.emitter("Streaks", "Fountain")
    e.props(SimTarget="GPUComputeSim", CalculateBoundsMode="Fixed",
            FixedBounds={"min": {"x": -1700, "y": -1700, "z": -100}, "max": {"x": 1700, "y": 1700, "z": 1700}})
    forever(e)
    e.set("SpawnRate", "SpawnRate", Expr("6000.0 * User.Intensity"))
    lifetime(e, 1.9)
    color(e, rgb(.62, .66, .7, .35))
    size2(e, (.22, 38), (.3, 52))
    shape(e, box=(3000, 3000, 10), offset=(0, 0, 1600))
    e.set("AddVelocity", "Velocity Mode", "Linear")
    e.set("AddVelocity", "Velocity", Expr("float3(User.Wind.x, User.Wind.y, -900.0 - rand(150.0))"))
    e.set("GravityForce", "Gravity", vec(0, 0, 0))
    e.set("Drag", "Drag", 0.0)
    collide(e, gpu=True, kill=True)
    fade(e, "1.0")
    e.renderer(Material=mi["Rain"], Alignment="VelocityAligned")
    e = s.emitter("Splashes", "Fountain")
    e.props(SimTarget="GPUComputeSim", CalculateBoundsMode="Fixed",
            FixedBounds={"min": {"x": -1700, "y": -1700, "z": -50}, "max": {"x": 1700, "y": 1700, "z": 60}})
    forever(e)
    e.set("SpawnRate", "SpawnRate", Expr("1400.0 * User.Intensity"))
    lifetime(e, .12, .2)
    color(e, rgb(.7, .74, .78, .5))
    size(e, 3.0, 7.0)
    shape(e, box=(3000, 3000, 1), offset=(0, 0, 1))
    cone(e, (0, 1), (0, 0, 1), 1)
    e.set("GravityForce", "Gravity", vec(0, 0, 0))
    grow(e, f"lerp(0.5, 1.5, {AGE})")
    fade(e, f"pow(saturate(1.0 - {AGE}), 1.0)")
    upright(e)
    e.renderer(Material=mi["Sheet"])
    s.compile()
    return s


def mist(mi):
    s = System("NS_SoraVFX_Mist", "Low ravine or river mist drifting through a box around the component; loops.", "ET_SoraVFX_Ambient")
    s.user("Extent", vec(3000.0, 3000.0, 250.0), "Box size, cm.")
    s.user("Wind", vec(40.0, 10.0, 0.0), "Drift, cm/s.")
    s.user("Density", .16, "Opacity of each bank.")
    puffs(s, "Banks", mi["Mist"], rate=3.0, life=(12.0, 20.0), color_value=Expr("float4(0.78, 0.82, 0.86, User.Density)"),
          size_range=(300, 600), box=Link("User.Extent"), offset=(0, 0, 90), speed=(0, 1), axis=(0, 0, 1), angle=1, drag_amount=.2,
          rise=0.0, grow_to=1.5, alpha=fade_in_out(.2, 1.0), spin_rate=4.0, frames=None)
    e = s.emitters[-1]
    e.ensure("Update/Forces/WindForce", PU, before="Drag")     # wind must precede the drag it relies on
    e.set("WindForce", "Wind Speed", Link("User.Wind"))
    s.compile()
    return s


def lantern(mi):
    s = System("NS_SoraVFX_Lantern", "A paper chochin or andon candle: flickering warm light and a soft halo; loops.", "ET_SoraVFX_Ambient")
    s.user("Lumens", 150.0, "Light output (the project's lanterns run 140-260).")
    s.user("Radius", 420.0, "Attenuation radius, cm.")
    s.user("LightColor", rgb(1.0, .62, .32), "Candle colour (about 1900 K).")
    steady_light(s, "Light", lumens="User.Lumens", radius="User.Radius", color_rgb="User.LightColor.rgb", flicker=.16)
    e = s.emitter("Halo", "SingleLoopingParticle")
    forever(e, 1.0)
    e.set("InitializeParticle", "Uniform Sprite Size", 24.0)
    color(e, Expr("float4(User.LightColor.rgb * 2.5, 0.35)"))
    # The flicker goes in the update stack: InitializeParticle's colour is evaluated once, at spawn.
    fade(e, "1.0", "(1.0 + 0.12 * User.FlashScale * sin(Engine.Time * 11.3)) * float3(1.0, 1.0, 1.0)")
    e.renderer(Material=mi["Glow"])
    e.props(bLocalSpace=True)
    s.compile()
    return s


SYSTEMS = [muzzle_matchlock, muzzle_energy, beam_energy, trail_projectile, blade_trail, impact_wood, impact_stone,
           impact_dirt, impact_metal, impact_fur, parry_sparks, explosion, hanabi_fire_zone, kusushi_heal, kusushi_ward,
           shinobi_decoy, karakuri_build_dust, telegraph_beam, telegraph_cleave, water_sluice_rise, water_splash,
           forge_fire, steam, steam_burst, rain, mist, lantern]


def build_systems(mi):
    System.effect_types = build_effect_types()
    built = []
    for builder in SYSTEMS:
        if ONLY and builder.__name__ not in ONLY:
            continue
        built.append(builder(mi).name)
    return built


MATERIAL_INSTANCES = {
    "Smoke": "MI_SoraVFX_Smoke", "Fireball": "MI_SoraVFX_Fireball", "Dust": "MI_SoraVFX_Dust", "Steam": "MI_SoraVFX_Steam",
    "Fire": "MI_SoraVFX_Fire", "FlashFace": "MI_SoraVFX_FlashPowderFace", "FlashSide": "MI_SoraVFX_FlashPowderSide",
    "FlashStar": "MI_SoraVFX_FlashEnergyStar", "FlashRing": "MI_SoraVFX_FlashRing", "Spark": "MI_SoraVFX_Spark",
    "Glow": "MI_SoraVFX_Glow", "Beam": "MI_SoraVFX_Beam", "Trail": "MI_SoraVFX_BladeTrail", "Spray": "MI_SoraVFX_WaterSpray",
    "Sheet": "MI_SoraVFX_WaterSheet", "Foam": "MI_SoraVFX_WaterFoam", "Mist": "MI_SoraVFX_WaterMist", "Rain": "MI_SoraVFX_Rain",
    "Scrap": "MI_SoraVFX_Scrap", "Fur": "MI_SoraVFX_Fur", "Ring": "MI_SoraVFX_TelegraphRing", "Wedge": "MI_SoraVFX_TelegraphWedge",
    "Lane": "MI_SoraVFX_TelegraphLane", "Wood": "MI_SoraVFX_DebrisWood", "Stone": "MI_SoraVFX_DebrisStone",
    "Soil": "MI_SoraVFX_DebrisSoil", "Plaster": "MI_SoraVFX_DebrisPlaster",
}


def main():
    unknown = sorted(ONLY - {builder.__name__ for builder in SYSTEMS})
    if unknown:
        raise RuntimeError(f"SORA_VFX_ONLY names no builder: {unknown}; the builders are {[b.__name__ for b in SYSTEMS]}")
    if REUSE_MATERIALS:
        mi = {role: assets.load_asset(f"{DEST}/Materials/{name}") for role, name in MATERIAL_INSTANCES.items()}
        missing = [name for role, name in MATERIAL_INSTANCES.items() if mi[role] is None]
        if missing:
            raise RuntimeError(f"SORA_VFX_REUSE_MATERIALS=1 but these are not built: {missing}")
    else:
        textures, samplers = import_textures()
        mi = build_materials(textures, samplers)
        if set(mi) != set(MATERIAL_INSTANCES):
            raise RuntimeError("MATERIAL_INSTANCES is out of step with build_materials")
    built = build_systems(mi)
    log(f"built {', '.join(built)}")
    if ONLY or REUSE_MATERIALS:
        # An iteration run: import-mac.sh accepts only the complete build's marker.
        unreal.log(f"SORA_VFX_PARTIAL: {len(built)} of {len(SYSTEMS)} systems rebuilt"
                   f"{', textures and materials reused' if REUSE_MATERIALS else ''}; not a complete build")
        return
    if len(built) != len(SYSTEMS):
        raise RuntimeError(f"built {len(built)} of {len(SYSTEMS)} systems")
    unreal.log(f"SORA_VFX_READY: {len(built)} systems")


main()
