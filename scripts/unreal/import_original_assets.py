"""UE 5.8.2 editor script: import source art and build original surface material.

Run with the compiled project: UnrealEditor-Cmd <project> -ExecutePythonScript=<this>
The script intentionally requires the requested engine version. It never downloads
assets or substitutes an older engine. Re-run after editing the Blender sources.
"""
from pathlib import Path
import hashlib
import json
import unreal

version = unreal.SystemLibrary.get_engine_version()
if not version.startswith("5.8.2"):
    raise RuntimeError(f"SORA Arena requires Unreal Engine 5.8.2; got {version}")

root = Path(unreal.Paths.project_dir()).resolve()
source = root / "Content/SourceArt"
manifest = json.loads((source / "manifest.json").read_text())
tools = unreal.AssetToolsHelpers.get_asset_tools()
assets = unreal.EditorAssetLibrary
assets.make_directory("/Game/Generated/Meshes")
assets.make_directory("/Game/Generated/Materials")
assets.make_directory("/Game/Generated/Animations")
assets.make_directory("/Game/Generated/UI")

title_art = source / "UI/Nyaagyu_Title_KeyArt.png"
if title_art.is_file():
    title_task = unreal.AssetImportTask()
    title_task.filename = str(title_art)
    title_task.destination_path = "/Game/Generated/UI"
    title_task.destination_name = "T_NyaagyuTitle"
    title_task.automated = True
    title_task.replace_existing = True
    title_task.save = True
    tools.import_asset_tasks([title_task])
    title_texture = assets.load_asset("/Game/Generated/UI/T_NyaagyuTitle")
    if not isinstance(title_texture, unreal.Texture2D):
        raise RuntimeError("Generated title art did not import as a 2D texture")
    title_texture.set_editor_property("srgb", True)
    title_texture.set_editor_property("lod_group", unreal.TextureGroup.TEXTUREGROUP_UI)
    assets.save_loaded_asset(title_texture)

# Keep the user-supplied SORA mark separate from generated key art. Its source
# and lossless transparent UI raster are checked before either is imported.
logo_manifest = json.loads((source / "UI/sora_logo_manifest.json").read_text())
for name, digest_key in (("source_svg", "source_sha256"), ("runtime_png", "runtime_sha256")):
    logo_file = source / "UI" / logo_manifest[name]
    if not logo_file.is_file() or hashlib.sha256(logo_file.read_bytes()).hexdigest() != logo_manifest[digest_key]:
        raise RuntimeError(f"The user-supplied SORA logo is missing or changed: {logo_file}")
logo_path = "/Game/Generated/UI/T_SoraResistanceLogo"
if logo_manifest["unreal_asset"] != f"{logo_path}.T_SoraResistanceLogo":
    raise RuntimeError("The SORA logo runtime identity must match the campaign HUD")
logo_task = unreal.AssetImportTask()
logo_task.filename = str(source / "UI" / logo_manifest["runtime_png"])
logo_task.destination_path = "/Game/Generated/UI"
logo_task.destination_name = "T_SoraResistanceLogo"
logo_task.automated = True
logo_task.replace_existing = True
logo_task.save = True
tools.import_asset_tasks([logo_task])
logo_texture = assets.load_asset(logo_path)
if not isinstance(logo_texture, unreal.Texture2D):
    raise RuntimeError("The SORA resistance insignia did not import as a 2D texture")
logo_texture.set_editor_property("srgb", True)
logo_texture.set_editor_property("lod_group", unreal.TextureGroup.TEXTUREGROUP_UI)
assets.save_loaded_asset(logo_texture)

hero_katana = manifest["hero_katana"]
if hero_katana["name"] != "SM_Nyaagyu_HeroKatana" or hero_katana["fbx"] != "SM_Nyaagyu_HeroKatana.fbx":
    raise RuntimeError("The authored hero katana must keep its runtime asset identity")
hero_source = source / hero_katana["fbx"]
if not hero_source.is_file() or hashlib.sha256(hero_source.read_bytes()).hexdigest() != hero_katana["fbx_sha256"]:
    raise RuntimeError("The hero katana source does not match its authored manifest hash")
bokken_root = source / "Weapons/Original"
bokken = json.loads((bokken_root / "manifest.json").read_text())
if (bokken["name"] != "SM_Nyaagyu_DojoBokken"
        or bokken["fbx"] != bokken["name"] + ".fbx"
        or bokken["unreal_asset"] != "/Game/Generated/Meshes/SM_Nyaagyu_DojoBokken.SM_Nyaagyu_DojoBokken"):
    raise RuntimeError("The original dojo bokken runtime identity changed")
bokken_fbx = bokken_root / bokken["fbx"]
if not bokken_fbx.is_file() or hashlib.sha256(bokken_fbx.read_bytes()).hexdigest() != bokken["fbx_sha256"]:
    raise RuntimeError("The original dojo bokken is missing or changed")
mesh_names = manifest["characters"] + manifest["weapons"] + [hero_katana["name"]]
tasks = []
for name, path in [(name, source / f"{name}.fbx") for name in mesh_names] + [(bokken["name"], bokken_fbx)]:
    if not path.is_file():
        raise RuntimeError(f"Required original mesh is missing: {path}")
    task = unreal.AssetImportTask()
    task.filename = str(path)
    task.destination_path = "/Game/Generated/Meshes"
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = True
    options = unreal.FbxImportUI()
    options.import_mesh = True
    options.import_materials = True
    options.import_textures = False
    options.import_as_skeletal = False
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    options.static_mesh_import_data.combine_meshes = True
    options.static_mesh_import_data.generate_lightmap_u_vs = False
    options.static_mesh_import_data.auto_generate_collision = False
    task.options = options
    tasks.append(task)
tools.import_asset_tasks(tasks)
for name in mesh_names + [bokken["name"]]:
    if not assets.does_asset_exist(f"/Game/Generated/Meshes/{name}"):
        raise RuntimeError(f"Unreal import did not create {name}")

# Source-authored environment heroes have one render mesh and explicit UCX
# convex collision boxes. Their linked Poly Haven source textures are verified
# separately by import_environment_palette.py and bound to slots at runtime.
environment_source = source / "Environment/Original"
environment_manifest = json.loads((environment_source / "manifest.json").read_text())
environment_names = ["SM_Edo_LanternPost", "SM_Nyaagyu_ToriiGate", "SM_Alien_DebtKiosk"]
if ([entry["name"] for entry in environment_manifest["assets"]] != environment_names
        or environment_manifest["generator"] != "scripts/art/create_edo_environment_props.py"):
    raise RuntimeError("The original environment prop identities changed")
assets.make_directory("/Game/Generated/Environment/Props")
environment_tasks = []
for entry in environment_manifest["assets"]:
    fbx = environment_source / entry["fbx"]
    if (entry["fbx"] != entry["name"] + ".fbx" or not fbx.is_file()
            or hashlib.sha256(fbx.read_bytes()).hexdigest() != entry["fbx_sha256"]):
        raise RuntimeError(f"The original environment prop is missing or changed: {fbx}")
    task = unreal.AssetImportTask()
    task.filename = str(fbx)
    task.destination_path = "/Game/Generated/Environment/Props"
    task.destination_name = entry["name"]
    task.automated = True
    task.replace_existing = True
    task.save = True
    options = unreal.FbxImportUI()
    options.import_mesh = True
    options.import_materials = True
    options.import_textures = False
    options.import_as_skeletal = False
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    options.static_mesh_import_data.combine_meshes = False
    options.static_mesh_import_data.generate_lightmap_u_vs = True
    options.static_mesh_import_data.auto_generate_collision = False
    task.options = options
    environment_tasks.append(task)
tools.import_asset_tasks(environment_tasks)
for name in environment_names:
    mesh = assets.load_asset(f"/Game/Generated/Environment/Props/{name}")
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError(f"Unreal import did not create the original environment prop: {name}")

for name in manifest.get("skeletal_characters", []):
    short=name.removeprefix("SK_")
    task=unreal.AssetImportTask()
    task.filename=str(source/(name+".fbx"))
    task.destination_path="/Game/Generated/Meshes"
    task.destination_name=name
    task.automated=True;task.replace_existing=True;task.save=True
    options=unreal.FbxImportUI()
    options.import_mesh=True;options.import_as_skeletal=True;options.import_animations=True
    options.import_materials=True;options.import_textures=False;options.create_physics_asset=False
    options.mesh_type_to_import=unreal.FBXImportType.FBXIT_SKELETAL_MESH
    task.options=options;tools.import_asset_tasks([task])
    mesh=assets.load_asset(f"/Game/Generated/Meshes/{name}")
    if not isinstance(mesh,unreal.SkeletalMesh):raise RuntimeError(f"Missing skeletal mesh {name}")
    idle_target=f"/Game/Generated/Animations/A_{short}_Idle"
    for path in task.imported_object_paths:
        if isinstance(assets.load_asset(path),unreal.AnimSequence):
            if assets.does_asset_exist(idle_target):assets.delete_asset(idle_target)
            if not assets.rename_asset(path,idle_target):raise RuntimeError(f"Cannot name idle animation {idle_target}")
    walk=unreal.AssetImportTask()
    walk.filename=str(source/(f"A_{short}_Walk.fbx"));walk.destination_path="/Game/Generated/Animations"
    walk.destination_name=f"A_{short}_Walk";walk.automated=True;walk.replace_existing=True;walk.save=True
    walk_options=unreal.FbxImportUI()
    walk_options.import_mesh=False;walk_options.import_as_skeletal=True;walk_options.import_animations=True
    walk_options.mesh_type_to_import=unreal.FBXImportType.FBXIT_ANIMATION
    walk_options.skeleton=mesh.get_editor_property("skeleton")
    walk.options=walk_options;tools.import_asset_tasks([walk])
    walk_target=f"/Game/Generated/Animations/A_{short}_Walk"
    if not assets.does_asset_exist(walk_target):
        for path in walk.imported_object_paths:
            if isinstance(assets.load_asset(path),unreal.AnimSequence):
                if not assets.rename_asset(path,walk_target):raise RuntimeError(f"Cannot name walk animation {walk_target}")
                break
    if not assets.does_asset_exist(idle_target) or not assets.does_asset_exist(walk_target):
        raise RuntimeError(f"Required animation was not imported for {name}")

path = "/Game/Generated/Materials/M_ArenaSurface"
material = assets.load_asset(path) if assets.does_asset_exist(path) else tools.create_asset(
    "M_ArenaSurface", "/Game/Generated/Materials", unreal.Material, unreal.MaterialFactoryNew())
lib = unreal.MaterialEditingLibrary
lib.delete_all_material_expressions(material)
color = lib.create_material_expression(material, unreal.MaterialExpressionVectorParameter, -600, -200)
color.parameter_name = "BaseColor"
color.default_value = unreal.LinearColor(.35,.4,.4,1)
roughness = lib.create_material_expression(material, unreal.MaterialExpressionScalarParameter,-400,250)
roughness.parameter_name = "Roughness"
roughness.default_value = .72
metallic = lib.create_material_expression(material, unreal.MaterialExpressionScalarParameter,-400,350)
metallic.parameter_name = "Metallic"
metallic.default_value = 0
lib.connect_material_property(color, "", unreal.MaterialProperty.MP_BASE_COLOR)
lib.connect_material_property(roughness, "", unreal.MaterialProperty.MP_ROUGHNESS)
lib.connect_material_property(metallic, "", unreal.MaterialProperty.MP_METALLIC)
lib.recompile_material(material)
assets.save_asset(path)

font = source / "Fonts/NotoSansCJKjp-Regular.otf"
if not font.is_file() or not (source / "Fonts/OFL.txt").is_file():
    raise RuntimeError("Japanese runtime font and its redistribution license are required")

assets.save_directory("/Game/Generated", only_if_is_dirty=False, recursive=True)
unreal.log(f"SORA_ASSET_IMPORT_COMPLETE: {len(tasks)} character/weapon meshes, {len(environment_tasks)} source-authored environment props; Japanese font staged separately")
