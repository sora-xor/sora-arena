"""Import the SORA craft props (lacquer, raden, maki-e, silk) into the pinned editor.

Run: UnrealEditor-Cmd SoraArena.uproject -nullrhi \
  -ExecutePythonScript=scripts/unreal/import_sora_craft.py [-- <PropKey> ...]

For every Content/SourceArt/Environment/SoraCraft/<Key>/build_record.json this
checks each recorded FBX/texture hash, imports the four baked maps, the LOD0
mesh into /Game/Generated/Environment/Props/<asset> (where the world builder
loads authored props) with its authored LOD1/LOD2, and binds a per-prop
instance of M_SoraCraft. The master evaluates raden (mother-of-pearl) as a
thin aragonite film per pixel: Mask R is raden coverage, B its relative
thickness (260-720 nm), so the colour shifts with the view angle the way
nacre does. Gold coverage (Mask G) is already metallic in ORM.
Nanite stays off: the Mac preset renders these conventional LODs, and the
same LOD chain is used on Windows until a Nanite comparison is measured.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import unreal

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sora_engine_pin import require_running_engine  # noqa: E402

require_running_engine("SORA craft import")
ROOT = Path(unreal.Paths.project_dir()).resolve()
SOURCE = ROOT / "Content/SourceArt/Environment/SoraCraft"
DEST = "/Game/Generated/Environment/SoraCraft"
PROPS = "/Game/Generated/Environment/Props"
MASTER = f"{DEST}/M_SoraCraft"
SORA_SVG_SHA256 = "d66413a71b70e25dcb8b2f118dcfe846a6446ed1db3de53ce88fc70c16ac0910"

tools = unreal.AssetToolsHelpers.get_asset_tools()
assets = unreal.EditorAssetLibrary
lib = unreal.MaterialEditingLibrary
meshes = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(f"SORA craft import: {message}")


def node(material, cls, x, y, **properties):
    expression = lib.create_material_expression(material, cls, x, y)
    for key, value in properties.items():
        expression.set_editor_property(key, value)
    return expression


def link(left, output, right, pin):
    require(lib.connect_material_expressions(left, output, right, pin), f"connection {output}->{pin}")


def out(expression, output_name, prop):
    require(lib.connect_material_property(expression, output_name, prop), f"output {prop}")


THIN_FILM_HLSL = r"""
// Two-beam thin-film interference of an aragonite platelet stack (n = 1.53).
// Film: relative thickness 0..1 -> 260..720 nm. Returns linear RGB reflectance
// weights at 650/532/460 nm for the current view angle.
float d = lerp(260.0, 720.0, saturate(Film));
float n = 1.53;
float cosI = saturate(abs(NdotV));
float sinT = sqrt(saturate(1.0 - cosI * cosI)) / n;
float cosT = sqrt(saturate(1.0 - sinT * sinT));
float3 lambda = float3(650.0, 532.0, 460.0);
float3 phase = 12.566370614 * n * d * cosT / lambda;
return 0.5 - 0.5 * cos(phase);
"""


def build_master(defaults):
    """``defaults``: textures of the first prop, so each parameter's default
    matches its sampler type (a Color default under a Normal/Masks sampler
    fails the material on every platform)."""
    master = assets.load_asset(MASTER) if assets.does_asset_exist(MASTER) else tools.create_asset(
        "M_SoraCraft", DEST, unreal.Material, unreal.MaterialFactoryNew())
    for old in list(lib.get_material_expressions(master)):
        lib.delete_material_expression(master, old)
    require(lib.get_num_material_expressions(master) == 0, "master kept old expressions")
    bc = node(master, unreal.MaterialExpressionTextureSampleParameter2D, -1400, -500, parameter_name="BaseColorMap",
              texture=defaults["BaseColor"])
    nm = node(master, unreal.MaterialExpressionTextureSampleParameter2D, -1400, -150, parameter_name="NormalMap",
              sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL, texture=defaults["Normal"])
    orm = node(master, unreal.MaterialExpressionTextureSampleParameter2D, -1400, 200, parameter_name="ORMMap",
               sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_MASKS, texture=defaults["ORM"])
    mask = node(master, unreal.MaterialExpressionTextureSampleParameter2D, -1400, 550, parameter_name="MaskMap",
                sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_MASKS, texture=defaults["Mask"])
    # View-angle term from the per-pixel normal (normal map applied).
    pn = node(master, unreal.MaterialExpressionPixelNormalWS, -1100, 900)
    cam = node(master, unreal.MaterialExpressionCameraVectorWS, -1100, 1000)
    ndv = node(master, unreal.MaterialExpressionDotProduct, -900, 950)
    link(pn, "", ndv, "A")
    link(cam, "", ndv, "B")
    film_mask = node(master, unreal.MaterialExpressionComponentMask, -1000, 700, r=False, g=False, b=True, a=False)
    link(mask, "RGB", film_mask, "")
    custom = node(master, unreal.MaterialExpressionCustom, -700, 800, code=THIN_FILM_HLSL,
                  output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT3, description="RadenThinFilm")
    inputs = []
    for name in ("Film", "NdotV"):
        ci = unreal.CustomInput()
        ci.set_editor_property("input_name", name)
        inputs.append(ci)
    custom.set_editor_property("inputs", inputs)
    link(film_mask, "", custom, "Film")
    link(ndv, "", custom, "NdotV")
    # Nacre body: pale shell under the interference colour.
    body = node(master, unreal.MaterialExpressionVectorParameter, -700, 600, parameter_name="RadenBody",
                default_value=unreal.LinearColor(0.78, 0.77, 0.76, 1))
    irid_gain = node(master, unreal.MaterialExpressionScalarParameter, -700, 1000, parameter_name="RadenIridescence",
                     default_value=0.85)
    irid_scaled = node(master, unreal.MaterialExpressionMultiply, -480, 900)
    link(custom, "", irid_scaled, "A")
    link(irid_gain, "", irid_scaled, "B")
    nacre = node(master, unreal.MaterialExpressionLinearInterpolate, -300, 700)
    link(body, "RGB", nacre, "A")
    link(irid_scaled, "", nacre, "B")
    nacre_mix = node(master, unreal.MaterialExpressionScalarParameter, -480, 760, parameter_name="RadenColourMix",
                     default_value=0.55)
    link(nacre_mix, "", nacre, "Alpha")
    raden = node(master, unreal.MaterialExpressionComponentMask, -1000, 600, r=True, g=False, b=False, a=False)
    link(mask, "RGB", raden, "")
    base = node(master, unreal.MaterialExpressionLinearInterpolate, -100, -450)
    link(bc, "RGB", base, "A")
    link(nacre, "", base, "B")
    link(raden, "", base, "Alpha")
    out(base, "", unreal.MaterialProperty.MP_BASE_COLOR)
    out(nm, "RGB", unreal.MaterialProperty.MP_NORMAL)
    for axis, prop, y in (("R", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION, 100),
                          ("G", unreal.MaterialProperty.MP_ROUGHNESS, 250)):
        m = node(master, unreal.MaterialExpressionComponentMask, -1000, y, r=axis == "R", g=axis == "G", b=False, a=False)
        link(orm, "RGB", m, "")
        out(m, "", prop)
    metal_src = node(master, unreal.MaterialExpressionComponentMask, -1000, 400, r=False, g=False, b=True, a=False)
    link(orm, "RGB", metal_src, "")
    raden_metal = node(master, unreal.MaterialExpressionScalarParameter, -700, 450, parameter_name="RadenMetallic",
                       default_value=0.45)
    metal = node(master, unreal.MaterialExpressionLinearInterpolate, -300, 400)
    link(metal_src, "", metal, "A")
    link(raden_metal, "", metal, "B")
    link(raden, "", metal, "Alpha")
    out(metal, "", unreal.MaterialProperty.MP_METALLIC)
    lib.layout_material_expressions(master)
    lib.recompile_material(master)
    assets.save_loaded_asset(master)
    names = {str(n) for n in lib.get_texture_parameter_names(master)}
    require(names == {"BaseColorMap", "NormalMap", "ORMMap", "MaskMap"}, f"master parameters {names}")
    return master


def import_texture(path: Path, folder: str, kind: str):
    task = unreal.AssetImportTask()
    task.filename = str(path)
    task.destination_path = folder
    task.destination_name = path.stem
    task.automated = True
    task.replace_existing = True
    task.save = True
    tools.import_asset_tasks([task])
    texture = assets.load_asset(f"{folder}/{path.stem}")
    require(isinstance(texture, unreal.Texture2D), f"texture failed: {path.name}")
    texture.set_editor_property("srgb", kind == "BaseColor")
    if kind == "Normal":
        texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
        texture.set_editor_property("flip_green_channel", False)
    elif kind in ("ORM", "Mask"):
        texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
    texture.set_editor_property("lod_group", unreal.TextureGroup.TEXTUREGROUP_WORLD)
    assets.save_loaded_asset(texture)
    return texture


def fbx_options():
    options = unreal.FbxImportUI()
    options.import_mesh = True
    options.import_materials = False
    options.import_textures = False
    options.import_as_skeletal = False
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    data = options.static_mesh_import_data
    data.combine_meshes = True
    data.generate_lightmap_u_vs = False
    data.auto_generate_collision = False
    data.set_editor_property("build_nanite", False)
    data.set_editor_property("normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS)
    return options


_MASTER = {}


def import_prop(folder: Path):
    record = json.loads((folder / "build_record.json").read_text(encoding="utf-8"))
    require(record.get("sora_mark", {}).get("sha256") == SORA_SVG_SHA256, f"{folder.name}: SORA mark pin")
    (asset_name, info), = record["assets"].items()
    lods = info["lods"]
    for lod in lods:
        path = ROOT / lod["file"]
        require(path.is_file() and sha(path) == lod["sha256"], f"{asset_name}: {lod['file']} changed")
    textures = {}
    tex_folder = f"{DEST}/{record['key']}/Textures"
    assets.make_directory(tex_folder)
    for kind, entry in record["textures"].items():
        path = ROOT / entry["file"]
        require(path.is_file() and sha(path) == entry["sha256"], f"{asset_name}: {entry['file']} changed")
        textures[kind] = import_texture(path, tex_folder, kind)
    require(set(textures) >= {"BaseColor", "ORM", "Mask", "Normal"}, f"{asset_name}: texture set {set(textures)}")
    if "master" not in _MASTER:
        _MASTER["master"] = build_master(textures)
    master = _MASTER["master"]
    task = unreal.AssetImportTask()
    task.filename = str(ROOT / lods[0]["file"])
    task.destination_path = PROPS
    task.destination_name = asset_name
    task.automated = True
    task.replace_existing = True
    task.save = True
    task.options = fbx_options()
    tools.import_asset_tasks([task])
    mesh = assets.load_asset(f"{PROPS}/{asset_name}")
    require(isinstance(mesh, unreal.StaticMesh), f"{asset_name}: static mesh import failed")
    # LODs from Unreal's own reducer, which keeps UV seams (Blender's collapse
    # decimation smears the baked atlas across them). LOD0 is the authored mesh.
    options = unreal.EditorScriptingMeshReductionOptions()
    options.set_editor_property("auto_compute_lod_screen_size", False)
    settings = []
    for percent, screen in ((1.0, 1.0), (0.45, 0.30), (0.18, 0.10)):
        s = unreal.EditorScriptingMeshReductionSettings()
        s.set_editor_property("percent_triangles", percent)
        s.set_editor_property("screen_size", screen)
        settings.append(s)
    options.set_editor_property("reduction_settings", settings)
    got = meshes.set_lods(mesh, options)
    require(got == 3, f"{asset_name}: set_lods returned {got}")
    require(meshes.get_lod_count(mesh) == 3, f"{asset_name}: LOD count {meshes.get_lod_count(mesh)}")
    instance_name = f"MI_{asset_name.removeprefix('SM_')}"
    instance_path = f"{DEST}/{record['key']}/{instance_name}"
    instance = assets.load_asset(instance_path) if assets.does_asset_exist(instance_path) else tools.create_asset(
        instance_name, f"{DEST}/{record['key']}", unreal.MaterialInstanceConstant,
        unreal.MaterialInstanceConstantFactoryNew())
    lib.set_material_instance_parent(instance, master)
    for param, kind in (("BaseColorMap", "BaseColor"), ("NormalMap", "Normal"), ("ORMMap", "ORM"),
                        ("MaskMap", "Mask")):
        lib.set_material_instance_texture_parameter_value(instance, param, textures[kind])
        bound = lib.get_material_instance_texture_parameter_value(instance, param)
        require(bound and bound.get_path_name() == textures[kind].get_path_name(), f"{instance_name}: {param}")
    assets.save_loaded_asset(instance)
    for index in range(len(mesh.get_editor_property("static_materials"))):
        mesh.set_material(index, instance)
    assets.save_loaded_asset(mesh)
    tris = [meshes.get_number_verts(mesh, i) for i in range(meshes.get_lod_count(mesh))]
    unreal.log(f"SORA_CRAFT_PROP_READY: {asset_name} LOD verts {tris} -> {instance_name}")
    return asset_name


def main():
    argv = sys.argv[1:]
    wanted = set(argv[argv.index("--") + 1:]) if "--" in argv else set()
    assets.make_directory(DEST)
    assets.make_directory(PROPS)
    done = []
    for folder in sorted(p for p in SOURCE.iterdir() if (p / "build_record.json").is_file()):
        if wanted and folder.name not in wanted:
            continue
        done.append(import_prop(folder))
    require(done, "no SORA craft props found")
    assets.save_directory(DEST, only_if_is_dirty=False, recursive=True)
    assets.save_directory(PROPS, only_if_is_dirty=False, recursive=True)
    unreal.log(f"SORA_CRAFT_IMPORT_COMPLETE: {len(done)} props: {', '.join(done)}")


main()
