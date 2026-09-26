"""Import the first-slice CC0 environment library into /Game/Generated/Environment/CC0.

Run by ``scripts/toolchain/import-mac.sh`` after the Nyaagyu palette import, in
the pinned headless editor. ``cc0_environment_library.build_plan`` checks the
schema-2 ledgers, every source SHA-256 and the period-accuracy policy before
any package is written; ``pack_cc0_environment.py`` must have packed the ARM
maps first. The script then

* imports the texture sets with their colour space, DirectX normals (the one
  OpenGL-only glTF normal is flipped on import), ``TC_Masks`` ARM packing and
  streaming virtual textures for the 4K hero sets;
* imports the HDRIs as lighting-only cubemaps and each scanned glTF node as
  its own Nanite static mesh;
* builds ``MPC_EnvironmentWeather`` and seven master materials: opaque PBR
  (world-aligned or mesh UVs, detail normal, macro variation), a two-layer
  height blend, two-sided foliage, cloth, and emissive lantern paper, all
  sharing one wetness/puddle response driven by the collection;
* creates the place-named and evaluation material instances, tagged with
  their sources, period risk and photoreal status, and binds each scan's
  instance to its meshes.

A source whose recorded SHA-256 is unchanged is not imported again, and a
master whose graph digest is unchanged is not rebuilt (a rebuild recompiles
all of its shaders).
"""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import sys

import unreal

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sora_engine_pin import require_running_engine  # noqa: E402
import cc0_environment_library as library  # noqa: E402

require_running_engine("CC0 environment library import")

ASSETS = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
LIB = unreal.MaterialEditingLibrary
MP = unreal.MaterialProperty
SOURCE_TAG = "SoraSourceSha256"
GRAPH_TAG = "SoraGraphSha256"
require = library.require


# --- Textures -------------------------------------------------------------------

def split(object_path: str) -> tuple[str, str]:
    package = object_path.split(".", 1)[0]
    folder, name = package.rsplit("/", 1)
    return folder, name


def import_file(source: Path, object_path: str, options=None):
    folder, name = split(object_path)
    ASSETS.make_directory(folder)
    task = unreal.AssetImportTask()
    task.filename = str(source)
    task.destination_path = folder
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = False
    if options is not None:
        task.options = options
    TOOLS.import_asset_tasks([task])
    asset = ASSETS.load_asset(object_path)
    require(asset is not None, f"Unreal import failed: {source} -> {object_path}")
    return asset


def current(object_path: str, digest: str, cls):
    """The existing package when it was imported from exactly these bytes."""
    if not ASSETS.does_asset_exist(object_path.split(".", 1)[0]):
        return None
    asset = ASSETS.load_asset(object_path)
    if isinstance(asset, cls) and ASSETS.get_metadata_tag(asset, SOURCE_TAG) == digest:
        return asset
    return None


def texture_settings(channel: library.Channel, texture_set: library.TextureSet, size: tuple) -> dict:
    expected = library.texture_expectations(channel, texture_set, size)
    return {key: getattr(getattr(unreal, library.ENUM_SETTINGS[key]), value) if key in library.ENUM_SETTINGS
            else value for key, value in expected.items()}


def configure(asset, settings: dict):
    changed = {key: value for key, value in settings.items() if asset.get_editor_property(key) != value}
    if changed:
        asset.set_editor_properties(changed)  # one PreEditChange/PostEditChange, one rebuild
    for key, value in settings.items():
        require(asset.get_editor_property(key) == value, f"{asset.get_path_name()}: {key} did not apply")


def import_textures(plan: library.Plan, packed: dict) -> tuple[dict, int]:
    textures, imported = {}, 0
    for texture_set in plan.sets.values():
        for role, channel in texture_set.channels.items():
            if not texture_set.imported:
                texture = ASSETS.load_asset(channel.package)
                require(isinstance(texture, unreal.Texture2D),
                        f"Palette texture {channel.package} is missing; run import_environment_palette.py first")
                textures[channel.package] = texture
                continue
            digest = packed[channel.file]["sha256"] if channel.root == "packed" else channel.sha256
            texture = current(channel.package, digest, unreal.Texture2D)
            if texture is None:
                texture = import_file(plan.source_path(channel), channel.package)
                require(isinstance(texture, unreal.Texture2D), f"{channel.package} did not import as Texture2D")
                imported += 1
            # The imported source size (the platform size ignores stretching until it is built).
            size = (texture.blueprint_get_size_x(), texture.blueprint_get_size_y())
            configure(texture, texture_settings(channel, texture_set, size))
            ASSETS.set_metadata_tag(texture, SOURCE_TAG, digest)
            ASSETS.set_metadata_tag(texture, "SoraSources", texture_set.origin)
            require(ASSETS.save_loaded_asset(texture, False), f"Could not save {channel.package}")
            textures[channel.package] = texture
    return textures, imported


def import_hdris(plan: library.Plan) -> int:
    imported = 0
    for record, object_path in plan.hdris:
        entry = record.file("hdri")
        cube = current(object_path, entry["sha256"], unreal.TextureCube)
        if cube is None:
            cube = import_file(plan.storage / entry["path"], object_path)
            require(isinstance(cube, unreal.TextureCube), f"{object_path} must import as a TextureCube")
            imported += 1
        ASSETS.set_metadata_tag(cube, SOURCE_TAG, entry["sha256"])
        ASSETS.set_metadata_tag(cube, "SoraSources", record.key)
        ASSETS.set_metadata_tag(cube, "SoraPeriodNotes", " | ".join(record.flags) or "none")
        require(ASSETS.save_loaded_asset(cube, False), f"Could not save {object_path}")
    return imported


# --- Meshes ---------------------------------------------------------------------

def single_node_gltf(plan: library.Plan, mesh: library.MeshImport, node_name: str, asset_name: str) -> str:
    """One glTF node as a self-contained glTF: its mesh, its scale/rotation and one named slot.

    Poly Haven sets lay several scans out with node translations; dropping the
    translation keeps each scan's own pivot, and the node's scale is kept so a
    scaled scan stays at its measured size.
    """
    gltf_path = plan.storage / mesh.gltf
    gltf = json.loads(gltf_path.read_text(encoding="utf-8"))
    node = next(item for item in gltf["nodes"] if item.get("name") == node_name)
    require(len(gltf["buffers"]) == 1, f"{mesh.gltf}: expected one buffer")
    binary = (gltf_path.parent / gltf["buffers"][0]["uri"]).read_bytes()
    views, accessors, blob = {}, {}, bytearray()

    def accessor(index):
        if index not in accessors:
            source = dict(gltf["accessors"][index])
            require("sparse" not in source, f"{mesh.gltf}: sparse accessors are not supported")
            view_index = source["bufferView"]
            if view_index not in views:
                view = dict(gltf["bufferViews"][view_index])
                start = view.get("byteOffset", 0)
                blob.extend(b"\0" * (-len(blob) % 4))
                view["byteOffset"] = len(blob)
                view["buffer"] = 0
                blob.extend(binary[start:start + view["byteLength"]])
                views[view_index] = (len(views), view)
            source["bufferView"] = views[view_index][0]
            accessors[index] = (len(accessors), source)
        return accessors[index][0]

    primitives = []
    for primitive in gltf["meshes"][node["mesh"]]["primitives"]:
        result = {"attributes": {key: accessor(value) for key, value in primitive["attributes"].items()}}
        if "indices" in primitive:
            result["indices"] = accessor(primitive["indices"])
        if "mode" in primitive:
            result["mode"] = primitive["mode"]
        primitives.append(result)
    for primitive in primitives:  # one named slot for the library instance, no glTF material
        primitive["material"] = 0
    out_node = {"name": asset_name, "mesh": 0}
    for key in ("rotation", "scale"):
        if key in node:
            out_node[key] = node[key]
    document = {
        "asset": {"version": "2.0", "generator": "scripts/unreal/import_cc0_environment.py"},
        "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [out_node],
        "meshes": [{"name": asset_name, "primitives": primitives}],
        "materials": [{"name": mesh.instance}],
        "accessors": [item for _, item in sorted(accessors.values(), key=lambda pair: pair[0])],
        "bufferViews": [item for _, item in sorted(views.values(), key=lambda pair: pair[0])],
        "buffers": [{"byteLength": len(blob),
                     "uri": "data:application/octet-stream;base64," + base64.b64encode(bytes(blob)).decode()}],
    }
    return json.dumps(document, sort_keys=True, separators=(",", ":"))


def mesh_pipeline():
    pipeline = unreal.InterchangeGenericAssetsPipeline()
    pipeline.set_editor_property("use_source_name_for_asset", True)
    meshes = pipeline.get_editor_property("mesh_pipeline")
    meshes.set_editor_property("import_static_meshes", True)
    meshes.set_editor_property("import_skeletal_meshes", False)
    meshes.set_editor_property("build_nanite", True)
    common = pipeline.get_editor_property("common_meshes_properties")
    common.set_editor_property("force_all_mesh_as_type", unreal.InterchangeForceMeshType.IFMT_STATIC_MESH)
    common.set_editor_property("bake_meshes", True)
    common.set_editor_property("recompute_normals", False)   # keep the scanned normals
    common.set_editor_property("recompute_tangents", True)   # glTF ships none; MikkTSpace as baked
    common.set_editor_property("use_mikk_t_space", True)
    materials = pipeline.get_editor_property("material_pipeline")
    materials.set_editor_property("import_materials", False)
    materials.get_editor_property("texture_pipeline").set_editor_property("import_textures", False)
    stack = unreal.InterchangePipelineStackOverride()
    stack.add_pipeline(pipeline)
    return stack


def import_meshes(plan: library.Plan, instances: dict) -> int:
    imported = 0
    derived_root = plan.project_root / "Saved/CC0Environment/Gltf"
    for mesh in plan.meshes:
        material = instances[mesh.instance]
        for node_name, asset_name in mesh.assets:
            object_path = f"{mesh.folder}/{asset_name}.{asset_name}"
            text = single_node_gltf(plan, mesh, node_name, asset_name)
            digest = hashlib.sha256(text.encode()).hexdigest()
            static_mesh = current(object_path, digest, unreal.StaticMesh)
            if static_mesh is None:
                derived = derived_root / mesh.record.asset_id / f"{asset_name}.gltf"
                derived.parent.mkdir(parents=True, exist_ok=True)
                derived.write_text(text, encoding="utf-8")
                static_mesh = import_file(derived, object_path, mesh_pipeline())
                require(isinstance(static_mesh, unreal.StaticMesh), f"{object_path} did not import as a StaticMesh")
                imported += 1
            slots = static_mesh.get_editor_property("static_materials")
            require(len(slots) == 1, f"{object_path}: expected one material slot, found {len(slots)}")
            static_mesh.set_material(0, material)
            nanite = static_mesh.get_editor_property("nanite_settings")
            require(bool(nanite.get_editor_property("enabled")) == mesh.nanite, f"{object_path}: Nanite state")
            ASSETS.set_metadata_tag(static_mesh, SOURCE_TAG, digest)
            ASSETS.set_metadata_tag(static_mesh, "SoraSources", mesh.record.key)
            ASSETS.set_metadata_tag(static_mesh, "SoraPeriodNotes", " | ".join(mesh.record.flags) or "none")
            ASSETS.set_metadata_tag(static_mesh, "SoraPhotorealGate", library.NOT_ADMITTED)
            require(ASSETS.save_loaded_asset(static_mesh, False), f"Could not save {object_path}")
    return imported


# --- Material graphs ------------------------------------------------------------

# Dominant-axis planar projection of the world position in centimetres: one
# texture fetch per map, oriented so text/grain reads upright on walls.
HLSL_PROJECT = """
float3 a = abs(N);
if (a.z >= a.x && a.z >= a.y) return float2(P.x, -P.y);
if (a.x >= a.y) return float2((N.x >= 0.0 ? -1.0 : 1.0) * P.y, -P.z);
return float2((N.y >= 0.0 ? 1.0 : -1.0) * P.x, -P.z);
"""

# The DirectX tangent-space normal in the same projection frame, re-orthogonalised
# against the geometric normal so slopes keep their shading. +R is +U, +G is +V.
HLSL_PROJECTED_NORMAL = """
float3 g = normalize(N);
float3 a = abs(g);
float3 tu = float3(1.0, 0.0, 0.0);
float3 tv = float3(0.0, -1.0, 0.0);
if (!(a.z >= a.x && a.z >= a.y)) {
    tv = float3(0.0, 0.0, -1.0);
    if (a.x >= a.y) tu = float3(0.0, g.x >= 0.0 ? -1.0 : 1.0, 0.0);
    else tu = float3(g.y >= 0.0 ? 1.0 : -1.0, 0.0, 0.0);
}
tu = normalize(tu - g * dot(g, tu));
tv = normalize(tv - g * dot(g, tv));
return normalize(NormalTS.x * tu + NormalTS.y * tv + NormalTS.z * g);
"""

HLSL_DETAIL = """
return normalize(float3(Base.xy + Detail.xy * Strength, Base.z));
"""

# Height blend of layer B over layer A: the ARM occlusion of A is the height
# proxy (crevices first when HeightFromCrevices is 1), vertex red paints coverage.
HLSL_BLEND = """
float coverage = saturate(Coverage * lerp(1.0, VertexR, VertexColorBlend) + TopFacingBias * saturate(Nz));
float h = lerp(ArmA.r, 1.0 - ArmA.r, HeightFromCrevices);
float alpha = saturate((h + 2.0 * coverage - 1.5) * Contrast + 0.5);
float roughA = lerp(RoughMinA, RoughMaxA, ArmA.g);
float roughB = lerp(RoughMinB, RoughMaxB, ArmB.g);
NormalOut = normalize(lerp(NormalA, NormalB, alpha));
ArmOut = float3(lerp(ArmA.r, ArmB.r, alpha), lerp(roughA, roughB, alpha), lerp(ArmA.b, ArmB.b, alpha));
return lerp(ColorA, ColorB * TintB, alpha);
"""

# Grading, macro variation and the shared rain response. Wet surfaces darken by
# WetDarkening and lose roughness toward WetRoughness (story bible 15.1: wet
# timber 0.2-0.35, albedo -25-35%); puddles gather on flat, low, macro-dark
# ground when PuddleAmount rises.
HLSL_FINISH = """
float lum = dot(Albedo, float3(0.2126, 0.7152, 0.0722));
float3 albedo = lerp(Albedo, lum.xxx, Desaturation) * Tint;
float macro = saturate(0.5 * (MacroA + MacroB));
float signedMacro = macro * 2.0 - 1.0;
albedo *= 1.0 + MacroStrength * signedMacro;
float rough = saturate(lerp(RoughMin, RoughMax, Arm.g) * (1.0 + MacroRoughness * signedMacro));
float ao = lerp(1.0, Arm.r, AOStrength);
float metal = saturate(Arm.b * MetallicScale);
float3 n = float3(NormalTS.xy * NormalStrength, NormalTS.z);
float exposure = lerp(0.65, 1.0, saturate(Nz));
float wet = saturate(max(BaseWetness, Wetness * WetnessResponse)) * exposure;
float lowness = 0.5 * (1.0 - Arm.r) + 0.5 * (1.0 - macro);
float flatness = saturate((Nz - 0.85) * 6.67);
float puddle = saturate((PuddleAmount * PuddleResponse * 1.2 - (1.0 - lowness)) * 8.0) * flatness;
wet = max(wet, puddle);
albedo *= 1.0 - WetDarkening * wet;
rough = lerp(rough, min(rough, WetRoughness), wet);
rough = lerp(rough, 0.04, puddle);
metal *= 1.0 - puddle;
RoughnessOut = rough;
MetallicOut = metal;
AOOut = ao;
NormalOut = normalize(lerp(n, float3(0.0, 0.0, 1.0), puddle));
return max(albedo, 0.0);
"""

# Emissive washi: blackbody colour at unit luminance, fibre-thickness
# transmission and a per-object flicker phase.
HLSL_LANTERN = """
float3 colour = BlackBody / pow(0.0004 * TemperatureK, 4.0);
float transmission = lerp(TransmissionMax, TransmissionMin, saturate(Thickness));
float phase = dot(ObjectPosition, float3(0.0131, 0.0173, 0.0113));
float t = Time * FlickerSpeed;
float flicker = 1.0 + FlickerAmount * (0.6 * sin(t * 7.3 + phase) + 0.4 * sin(t * 13.1 + phase * 1.9));
return colour * Intensity * GlobalIntensity * transmission * flicker;
"""


class Graph:
    """Small helper around MaterialEditingLibrary for one master material."""

    def __init__(self, material, mpc):
        self.material, self.mpc, self.row, self.attributes = material, mpc, 0, None

    def use_attributes(self):
        """Route outputs through MakeMaterialAttributes (Python cannot reach the CustomData0 pin)."""
        self.material.set_editor_property("use_material_attributes", True)
        self.attributes = self.node(unreal.MaterialExpressionMakeMaterialAttributes)
        require(LIB.connect_material_property(self.attributes, "", MP.MP_MATERIAL_ATTRIBUTES),
                f"{self.material.get_name()}: material attributes output failed")

    def node(self, cls, **properties):
        self.row += 1
        expression = LIB.create_material_expression(self.material, cls, -1600, self.row * 140)
        require(expression is not None, f"Could not create {cls.__name__}")
        if properties:
            expression.set_editor_properties(properties)
        return expression

    def link(self, source, output, target, pin):
        require(LIB.connect_material_expressions(source, output, target, pin),
                f"{self.material.get_name()}: link {output!r} -> {pin!r} failed")

    def out(self, source, output, prop):
        if self.attributes is None:
            require(LIB.connect_material_property(source, output, prop),
                    f"{self.material.get_name()}: output {prop} failed")
            return
        pins = LIB.get_material_expression_input_names(self.attributes)
        wanted = ATTRIBUTE_PINS[prop] if prop in ATTRIBUTE_PINS else prop
        pin = next((name for name in wanted if name in pins), None)
        require(pin is not None, f"{self.material.get_name()}: no attributes pin for {prop} in {list(pins)}")
        self.link(source, output, self.attributes, pin)

    def scalar(self, name, default, group):
        return self.node(unreal.MaterialExpressionScalarParameter, parameter_name=name,
                         default_value=float(default), group=group), ""

    def vector(self, name, default, group):
        return self.node(unreal.MaterialExpressionVectorParameter, parameter_name=name,
                         default_value=unreal.LinearColor(*default), group=group), "RGB"

    def mask(self, pin, channels):
        expression = self.node(unreal.MaterialExpressionComponentMask,
                               r="r" in channels, g="g" in channels, b="b" in channels, a="a" in channels)
        self.link(*pin, expression, "")
        return expression, ""

    def binary(self, cls, a, b):
        expression = self.node(cls)
        self.link(*a, expression, "A")
        self.link(*b, expression, "B")
        return expression, ""

    def texture(self, name, texture, uv, group):
        expression = self.node(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name=name,
                               texture=texture, sampler_type=sampler_type(texture),
                               sampler_source=unreal.SamplerSourceMode.SSM_WRAP_WORLD_GROUP_SETTINGS,
                               group=group)
        self.link(*uv, expression, "UVs")
        return expression

    def collection(self, name):
        expression = self.node(unreal.MaterialExpressionCollectionParameter, collection=self.mpc)
        expression.set_editor_property("parameter_name", name)
        return expression, ""

    def custom(self, description, code, output_type, inputs: dict, outputs: dict | None = None):
        expression = self.node(unreal.MaterialExpressionCustom, code=code.strip(), description=description,
                               output_type=output_type)
        pins = []
        for name in inputs:
            item = unreal.CustomInput()
            item.set_editor_property("input_name", name)
            pins.append(item)
        expression.set_editor_property("inputs", pins)
        extra = []
        for name, kind in (outputs or {}).items():
            item = unreal.CustomOutput()
            item.set_editor_property("output_name", name)
            item.set_editor_property("output_type", kind)
            extra.append(item)
        expression.set_editor_property("additional_outputs", extra)
        for name, pin in inputs.items():
            self.link(*pin, expression, name)
        return expression

    def switch(self, name, default, true_pin, false_pin, group):
        expression = self.node(unreal.MaterialExpressionStaticSwitchParameter, parameter_name=name,
                               default_value=default, group=group)
        self.link(*true_pin, expression, "True")
        self.link(*false_pin, expression, "False")
        return expression, ""


ATTRIBUTE_PINS = {
    MP.MP_BASE_COLOR: ("BaseColor",), MP.MP_METALLIC: ("Metallic",), MP.MP_ROUGHNESS: ("Roughness",),
    MP.MP_AMBIENT_OCCLUSION: ("AmbientOcclusion",), MP.MP_NORMAL: ("Normal",),
    MP.MP_SUBSURFACE_COLOR: ("SubsurfaceColor",), MP.MP_OPACITY_MASK: ("OpacityMask",),
    MP.MP_EMISSIVE_COLOR: ("EmissiveColor",),
}
CLOTH_PIN = ("ClearCoat", "CustomData0", "Custom Data 0", "Cloth")  # the cloth amount is CustomData0


def sampler_type(texture):
    kind = unreal.MaterialSamplerType
    compression = texture.get_editor_property("compression_settings")
    settings = unreal.TextureCompressionSettings
    if compression == settings.TC_NORMALMAP:
        name = "NORMAL"
    elif compression == settings.TC_MASKS:
        name = "MASKS"
    elif compression == settings.TC_GRAYSCALE:
        name = "GRAYSCALE" if texture.get_editor_property("srgb") else "LINEAR_GRAYSCALE"
    else:
        name = "COLOR" if texture.get_editor_property("srgb") else "LINEAR_COLOR"
    virtual = isinstance(texture, unreal.Texture2D) and texture.get_editor_property("virtual_texture_streaming")
    return getattr(kind, f"SAMPLERTYPE_{'VIRTUAL_' if virtual else ''}{name}")


F1, F2, F3 = (unreal.CustomMaterialOutputType.CMOT_FLOAT1, unreal.CustomMaterialOutputType.CMOT_FLOAT2,
              unreal.CustomMaterialOutputType.CMOT_FLOAT3)


def finish_inputs(g: Graph, albedo, normal, arm, macro_a, macro_b, nz, *, remap=True, puddles=True,
                  metal=True, wet=(0.0, 0.3, 0.25)):
    """Wire the grading, macro and wetness parameters into HLSL_FINISH."""
    grade, weather = "Surface Grade", "Weather"
    one, zero = g.node(unreal.MaterialExpressionConstant, r=1.0), g.node(unreal.MaterialExpressionConstant, r=0.0)
    inputs = {
        "Albedo": albedo, "NormalTS": normal, "Arm": arm, "MacroA": macro_a, "MacroB": macro_b, "Nz": nz,
        "Tint": g.vector("BaseColorTint", (1, 1, 1, 1), grade),
        "Desaturation": g.scalar("Desaturation", 0.0, grade),
        "RoughMin": g.scalar("RoughnessMin", 0.0, grade) if remap else (zero, ""),
        "RoughMax": g.scalar("RoughnessMax", 1.0, grade) if remap else (one, ""),
        "AOStrength": g.scalar("AOStrength", 1.0, grade),
        "NormalStrength": g.scalar("NormalStrength", 1.0, grade),
        "MetallicScale": g.scalar("MetallicScale", 1.0, grade) if metal else (zero, ""),
        "MacroStrength": g.scalar("MacroStrength", 0.08, "Macro Variation"),
        "MacroRoughness": g.scalar("MacroRoughness", 0.05, "Macro Variation"),
        "Wetness": g.collection("Wetness"),
        "PuddleAmount": g.collection("PuddleAmount"),
        "WetnessResponse": g.scalar("WetnessResponse", wet[0], weather),
        "BaseWetness": g.scalar("BaseWetness", 0.0, weather),
        "WetDarkening": g.scalar("WetDarkening", wet[1], weather),
        "WetRoughness": g.scalar("WetRoughness", wet[2], weather),
        "PuddleResponse": g.scalar("PuddleResponse", 0.0, weather) if puddles else (zero, ""),
    }
    return g.custom("SORA environment finish", HLSL_FINISH, F3, inputs,
                    {"RoughnessOut": F1, "MetallicOut": F1, "AOOut": F1, "NormalOut": F3})


def build_master(master: library.Master, mpc, defaults: dict, digest: str):
    """The master's graph, rebuilt only when ``digest`` (library.master_graph_digest) changed.

    ``defaults`` maps each texture parameter to the placeholder texture its first
    instance binds, so the sampler types match what the instances bind.
    """
    path = library.master_path(master.name)
    folder, name = split(path)
    if ASSETS.does_asset_exist(path.split(".")[0]):
        material = ASSETS.load_asset(path)
        if ASSETS.get_metadata_tag(material, GRAPH_TAG) == digest:
            return material, False
    else:
        material = TOOLS.create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())
    for expression in list(LIB.get_material_expressions(material)):
        LIB.delete_material_expression(material, expression)
    require(LIB.get_num_material_expressions(material) == 0, f"{name} kept stale expressions")
    family = master.family
    g = Graph(material, mpc)
    material.set_editor_property("use_material_attributes", False)

    # Material-wide settings per family.
    properties = {"used_with_nanite": True, "used_with_instanced_static_meshes": True,
                  "blend_mode": unreal.BlendMode.BLEND_OPAQUE, "two_sided": False,
                  "shading_model": unreal.MaterialShadingModel.MSM_DEFAULT_LIT,
                  "tangent_space_normal": family not in library.WORLD_ALIGNED_FAMILIES}
    if family in library.WORLD_ALIGNED_FAMILIES:
        properties["used_with_spline_meshes"] = True
    if family == "foliage":
        properties.update(blend_mode=unreal.BlendMode.BLEND_MASKED, two_sided=True, opacity_mask_clip_value=0.33,
                          shading_model=unreal.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE,
                          dithered_lod_transition=True)
    elif family == "cloth":
        properties.update(two_sided=True, shading_model=unreal.MaterialShadingModel.MSM_CLOTH,
                          used_with_skeletal_mesh=True, opacity_mask_clip_value=0.4)
    elif family == "lantern":
        properties.update(two_sided=True)
    material.set_editor_properties(properties)
    if family == "cloth":
        g.use_attributes()

    # Placeholder textures (``defaults``): the instance binds the real maps.
    position = g.node(unreal.MaterialExpressionWorldPosition), ""
    vertex_normal = g.node(unreal.MaterialExpressionVertexNormalWS), ""
    nz = g.mask(vertex_normal, "b")
    coords = g.custom("SORA world projection (cm)", HLSL_PROJECT, F2, {"P": position, "N": vertex_normal}), ""
    texcoord = g.node(unreal.MaterialExpressionTextureCoordinate, coordinate_index=0), ""

    def uv_for(prefix, tile_default):
        """Mesh UVs times UVScale, or (world-aligned families) a switch to projected cm / TileSizeCm."""
        mesh_uv = g.binary(unreal.MaterialExpressionMultiply, texcoord,
                           g.mask(g.vector(f"{prefix}UVScale", (1, 1, 0, 0), "UV"), "rg"))
        if family not in library.WORLD_ALIGNED_FAMILIES:
            return mesh_uv
        world_uv = g.binary(unreal.MaterialExpressionDivide, coords,
                            g.mask(g.vector(f"{prefix}TileSizeCm", tile_default, "UV"), "rg"))
        return g.switch("WorldAlignedUV", True, world_uv, mesh_uv, "UV")

    uvs = {"": uv_for("", (200, 200, 0, 0))}
    if family == "heightblend":
        uvs["LayerB"] = uv_for("LayerB", (150, 150, 0, 0))
    params = library.TEXTURE_PARAMS[family]
    samples = {}
    for param in params:
        uv = uvs["LayerB" if param.startswith("LayerB") else ""]
        samples[param] = g.texture(param, defaults[param], uv, "Layer B" if param.startswith("LayerB") else "Maps")

    if family in ("surface", "heightblend", "foliage", "cloth"):
        macro_texture = ASSETS.load_asset(library.MACRO_VARIATION)
        require(macro_texture is not None, "Engine macro-variation texture is missing")
        macro_a = g.texture("MacroVariation", macro_texture,
                            g.binary(unreal.MaterialExpressionDivide, coords,
                                     g.scalar("MacroScaleACm", 1300.0, "Macro Variation")), "Macro Variation")
        macro_b = g.node(unreal.MaterialExpressionTextureSample, texture=macro_texture,
                         sampler_type=sampler_type(macro_texture),
                         sampler_source=unreal.SamplerSourceMode.SSM_WRAP_WORLD_GROUP_SETTINGS)
        g.link(*g.binary(unreal.MaterialExpressionDivide, coords,
                         g.scalar("MacroScaleBCm", 4700.0, "Macro Variation")), macro_b, "UVs")
        macro_pins = ((macro_a, "R"), (macro_b, "G"))
    else:
        half = g.node(unreal.MaterialExpressionConstant, r=0.5), ""
        macro_pins = (half, half)

    if family == "heightblend":
        blend = g.custom("SORA height blend", HLSL_BLEND, F3, {
            "ColorA": (samples["BaseColor"], "RGB"), "NormalA": (samples["Normal"], "RGB"),
            "ArmA": (samples["ARM"], "RGB"),
            "ColorB": (samples["LayerBBaseColor"], "RGB"), "NormalB": (samples["LayerBNormal"], "RGB"),
            "ArmB": (samples["LayerBARM"], "RGB"),
            "VertexR": (g.node(unreal.MaterialExpressionVertexColor), "R"), "Nz": nz,
            "Coverage": g.scalar("LayerBCoverage", 0.3, "Height Blend"),
            "VertexColorBlend": g.scalar("VertexColorBlend", 0.0, "Height Blend"),
            "TopFacingBias": g.scalar("TopFacingBias", 0.0, "Height Blend"),
            "HeightFromCrevices": g.scalar("HeightFromCrevices", 1.0, "Height Blend"),
            "Contrast": g.scalar("BlendContrast", 4.0, "Height Blend"),
            "TintB": g.vector("LayerBTint", (1, 1, 1, 1), "Layer B"),
            "RoughMinA": g.scalar("RoughnessMin", 0.0, "Surface Grade"),
            "RoughMaxA": g.scalar("RoughnessMax", 1.0, "Surface Grade"),
            "RoughMinB": g.scalar("LayerBRoughnessMin", 0.0, "Layer B"),
            "RoughMaxB": g.scalar("LayerBRoughnessMax", 1.0, "Layer B"),
        }, {"NormalOut": F3, "ArmOut": F3})
        albedo, normal, arm = (blend, ""), (blend, "NormalOut"), (blend, "ArmOut")
    else:
        albedo, normal, arm = (samples["BaseColor"], "RGB"), (samples["Normal"], "RGB"), (samples["ARM"], "RGB")

    if family in library.WORLD_ALIGNED_FAMILIES:
        # Same virtual-texture state as layer A, so an instance may reuse its own normal as detail.
        detail_sample = g.texture("DetailNormal", defaults["Normal"],
                                  g.binary(unreal.MaterialExpressionMultiply, uvs[""],
                                           g.scalar("DetailTiling", 4.0, "Detail")), "Detail")
        detailed = g.custom("SORA detail normal", HLSL_DETAIL, F3, {
            "Base": normal, "Detail": (detail_sample, "RGB"),
            "Strength": g.scalar("DetailNormalStrength", 0.5, "Detail")})
        normal = g.switch("UseDetailNormal", False, (detailed, ""), normal, "Detail")

    wet_defaults = {"foliage": (0.5, 0.1, 0.3), "cloth": (0.0, 0.35, 0.4), "lantern": (0.2, 0.15, 0.3)}
    finish = finish_inputs(g, albedo, normal, arm, *macro_pins, nz,
                           remap=family != "heightblend", puddles=family in library.WORLD_ALIGNED_FAMILIES,
                           metal=family in library.WORLD_ALIGNED_FAMILIES,
                           wet=wet_defaults.get(family, (0.0, 0.3, 0.25)))
    g.out(finish, "", MP.MP_BASE_COLOR)
    g.out(finish, "RoughnessOut", MP.MP_ROUGHNESS)
    g.out(finish, "MetallicOut", MP.MP_METALLIC)
    g.out(finish, "AOOut", MP.MP_AMBIENT_OCCLUSION)
    if family in library.WORLD_ALIGNED_FAMILIES:
        projected = g.custom("SORA projected normal to world", HLSL_PROJECTED_NORMAL, F3,
                             {"NormalTS": (finish, "NormalOut"), "N": vertex_normal})
        tangent = g.node(unreal.MaterialExpressionTransform,
                         transform_source_type=unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_TANGENT,
                         transform_type=unreal.MaterialVectorCoordTransform.TRANSFORM_WORLD)
        g.link(finish, "NormalOut", tangent, "")
        world_normal = g.switch("WorldAlignedUV", True, (projected, ""), (tangent, ""), "UV")
        g.out(*world_normal, MP.MP_NORMAL)
    else:
        g.out(finish, "NormalOut", MP.MP_NORMAL)

    if family == "foliage":
        subsurface = g.binary(unreal.MaterialExpressionMultiply, (finish, ""),
                              g.vector("SubsurfaceTint", (0.6, 0.8, 0.3, 1), "Foliage"))
        subsurface = g.binary(unreal.MaterialExpressionMultiply, subsurface,
                              g.scalar("Transmission", 0.5, "Foliage"))
        g.out(*subsurface, MP.MP_SUBSURFACE_COLOR)
        g.out(samples["ARM"], "A", MP.MP_OPACITY_MASK)
    elif family == "cloth":
        g.out(*g.vector("FuzzColor", (0.3, 0.3, 0.3, 1), "Cloth"), MP.MP_SUBSURFACE_COLOR)
        g.out(*g.scalar("ClothAmount", 0.6, "Cloth"), CLOTH_PIN)
        g.out(samples["ARM"], "A", MP.MP_OPACITY_MASK)
    elif family == "lantern":
        blackbody = g.node(unreal.MaterialExpressionBlackBody)
        temperature = g.scalar("ColorTemperatureK", 2000.0, "Lantern")
        g.link(*temperature, blackbody, "Temp")
        emissive = g.custom("SORA lantern paper emission", HLSL_LANTERN, F3, {
            "BlackBody": (blackbody, ""), "TemperatureK": temperature,
            "Thickness": (samples["Thickness"], "R"),
            "TransmissionMin": g.scalar("TransmissionMin", 0.25, "Lantern"),
            "TransmissionMax": g.scalar("TransmissionMax", 0.9, "Lantern"),
            "ObjectPosition": (g.node(unreal.MaterialExpressionObjectPositionWS), ""),
            "Time": (g.node(unreal.MaterialExpressionTime), ""),
            "FlickerSpeed": g.scalar("FlickerSpeed", 1.0, "Lantern"),
            "FlickerAmount": g.scalar("FlickerAmount", 0.06, "Lantern"),
            "Intensity": g.scalar("EmissiveIntensity", 12.0, "Lantern"),
            "GlobalIntensity": g.collection("LanternIntensity"),
        })
        g.out(emissive, "", MP.MP_EMISSIVE_COLOR)

    LIB.layout_material_expressions(material)
    errors = LIB.recompile_material(material)
    require(not errors, f"{name} failed to compile: {errors}")
    ASSETS.set_metadata_tag(material, "SoraLibrary", f"cc0-environment v{library.LIBRARY_VERSION}")
    ASSETS.set_metadata_tag(material, GRAPH_TAG, digest)
    require(ASSETS.save_loaded_asset(material, False), f"Could not save {name}")
    return material, True


def build_mpc():
    path = library.mpc_path()
    folder, name = split(path)
    mpc = (ASSETS.load_asset(path) if ASSETS.does_asset_exist(path.split(".")[0])
           else TOOLS.create_asset(name, folder, unreal.MaterialParameterCollection,
                                   unreal.MaterialParameterCollectionFactoryNew()))
    existing = {str(item.get_editor_property("parameter_name")): item
                for item in mpc.get_editor_property("scalar_parameters")}
    if (list(existing) == list(library.MPC_SCALARS) and not mpc.get_editor_property("vector_parameters")
            and all(existing[key].get_editor_property("default_value") == value
                    for key, value in library.MPC_SCALARS.items())):
        return mpc  # unchanged: editing it would recompile every material that reads it
    parameters = []
    for parameter_name, default in library.MPC_SCALARS.items():
        item = existing.get(parameter_name) or unreal.CollectionScalarParameter()
        item.set_editor_property("parameter_name", parameter_name)
        item.set_editor_property("default_value", default)
        parameters.append(item)
    mpc.set_editor_properties({"scalar_parameters": parameters, "vector_parameters": []})
    require(ASSETS.save_loaded_asset(mpc, False), f"Could not save {name}")
    return mpc


# --- Instances ------------------------------------------------------------------

def bound_textures(plan: library.Plan, instance: library.Instance, textures: dict) -> dict:
    return {param: textures[package] for param, package in library.bound_packages(plan, instance).items()}


def build_instance(plan: library.Plan, instance: library.Instance, parent, textures: dict):
    path = library.instance_path(instance)
    folder, name = split(path)
    ASSETS.make_directory(folder)
    mi = (ASSETS.load_asset(path) if ASSETS.does_asset_exist(path.split(".")[0])
          else TOOLS.create_asset(name, folder, unreal.MaterialInstanceConstant,
                                  unreal.MaterialInstanceConstantFactoryNew()))
    LIB.set_material_instance_parent(mi, parent)
    LIB.clear_all_material_instance_parameters(mi)
    # The library setters always return False; read every value back instead.
    names = {kind: {str(item) for item in getter(parent)} for kind, getter in (
        ("switch", LIB.get_static_switch_parameter_names), ("scalar", LIB.get_scalar_parameter_names),
        ("vector", LIB.get_vector_parameter_names), ("texture", LIB.get_texture_parameter_names))}

    def known(kind, parameter):
        require(parameter in names[kind], f"{name}: {parent.get_name()} has no {kind} parameter {parameter}")

    for switch, value in library.resolved_switches(instance).items():
        known("switch", switch)
        LIB.set_material_instance_static_switch_parameter_value(mi, switch, value)
        require(LIB.get_material_instance_static_switch_parameter_value(mi, switch) == value,
                f"{name}: static switch {switch} did not bind")
    for scalar, value in instance.scalars.items():
        known("scalar", scalar)
        LIB.set_material_instance_scalar_parameter_value(mi, scalar, float(value))
        require(abs(LIB.get_material_instance_scalar_parameter_value(mi, scalar) - value) < 1e-4,
                f"{name}: scalar {scalar} did not bind")
    for vector, value in library.resolved_vectors(plan, instance).items():
        known("vector", vector)
        LIB.set_material_instance_vector_parameter_value(mi, vector, unreal.LinearColor(*value))
        actual = LIB.get_material_instance_vector_parameter_value(mi, vector)
        require(all(abs(getattr(actual, c) - v) < 1e-4 for c, v in zip("rgba", value)),
                f"{name}: vector {vector} did not bind")
    textures_bound = bound_textures(plan, instance, textures)
    if instance.detail:  # the layer's own normal at a non-integer DetailTiling breaks up repetition
        textures_bound["DetailNormal"] = textures[plan.layers_of(instance)[0].channels["Normal"].package]
    for param, texture in textures_bound.items():
        known("texture", param)
        LIB.set_material_instance_texture_parameter_value(mi, param, texture)
        actual = LIB.get_material_instance_texture_parameter_value(mi, param)
        require(actual is not None and actual.get_path_name() == texture.get_path_name(),
                f"{name}: texture {param} did not bind")
    overrides = mi.get_editor_property("base_property_overrides")
    overrides.set_editor_property("override_blend_mode", instance.blend_mode is not None)
    if instance.blend_mode is not None:
        overrides.set_editor_property("blend_mode", {"opaque": unreal.BlendMode.BLEND_OPAQUE,
                                                     "masked": unreal.BlendMode.BLEND_MASKED}[instance.blend_mode])
    mi.set_editor_property("base_property_overrides", overrides)
    LIB.update_material_instance(mi)
    for tag, value in library.metadata(plan, instance).items():
        ASSETS.set_metadata_tag(mi, tag, value)
    require(ASSETS.save_loaded_asset(mi, False), f"Could not save {name}")
    return mi


def main():
    project_root = Path(unreal.Paths.project_dir()).resolve()
    plan = library.build_plan(project_root)
    library.verify_packed(plan)
    packed = library.read_packed_manifest(project_root)["outputs"]
    textures, imported_textures = import_textures(plan, packed)
    imported_hdris = import_hdris(plan)
    mpc = build_mpc()
    defaults = library.master_defaults(plan)
    built = {name: build_master(master, mpc, {param: textures[package] for param, package in defaults[name].items()},
                                library.master_graph_digest(plan, name, defaults[name]))
             for name, master in library.MASTERS.items()}
    masters = {name: material for name, (material, _) in built.items()}
    rebuilt = sum(changed for _, changed in built.values())
    instances = {instance.name: build_instance(plan, instance, masters[instance.master], textures)
                 for instance in plan.instances}
    imported_meshes = import_meshes(plan, instances)
    ASSETS.save_directory(library.PACKAGE_ROOT, only_if_is_dirty=True, recursive=True)
    missing = [path for path in plan.expected if not ASSETS.does_asset_exist(path.split(".")[0])]
    require(not missing, f"Expected packages missing after import: {missing[:5]}")
    unreal.log(f"SORA_CC0_ENVIRONMENT_READY: {len(plan.expected)} packages "
               f"({imported_textures} textures, {imported_hdris} HDRIs, {imported_meshes} meshes imported; "
               f"{len(masters)} masters ({rebuilt} rebuilt), {len(instances)} instances)")


main()
