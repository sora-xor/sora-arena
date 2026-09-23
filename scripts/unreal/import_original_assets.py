"""UE 5.8.2 editor script: import source art and build original surface material.

Run with the compiled project: UnrealEditor-Cmd <project> -ExecutePythonScript=<this>
The script intentionally requires the requested engine version. It never downloads
assets or substitutes an older engine. Re-run after editing the Blender sources.
"""
from pathlib import Path
import hashlib
import json
import runpy
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
arc_carbine = json.loads((bokken_root / "arc_carbine_manifest.json").read_text())
if (arc_carbine["schema_version"] != 1
        or arc_carbine["name"] != "SM_Nyaagyu_ArcCarbine"
        or arc_carbine["generator"] != "scripts/art/create_arc_carbine.py"
        or arc_carbine["fbx"] != arc_carbine["name"] + ".fbx"
        or arc_carbine["unreal_asset"] != "/Game/Generated/Meshes/SM_Nyaagyu_ArcCarbine.SM_Nyaagyu_ArcCarbine"):
    raise RuntimeError("The original Arc carbine runtime identity changed")
arc_fbx = bokken_root / arc_carbine["fbx"]
if not arc_fbx.is_file() or hashlib.sha256(arc_fbx.read_bytes()).hexdigest() != arc_carbine["fbx_sha256"]:
    raise RuntimeError("The original Arc carbine is missing or changed")
hero_character_root = source / "Characters/Hero"
hero_character = json.loads((hero_character_root / "manifest.json").read_text())
hero_character_name = "SM_Nyaagyu_HeroCharacter"
if (hero_character["schema_version"] != 2
        or hero_character["name"] != hero_character_name
        or hero_character["generator"] != "scripts/art/create_nyaagyu_hero_character.py"
        or hero_character["fbx"] != hero_character_name + ".fbx"
        or hero_character["unreal_asset"] != f"/Game/ArtReview/Characters/{hero_character_name}.{hero_character_name}"
        or hero_character["rigged"] is not False):
    raise RuntimeError("The original feline hero character asset identity changed")
hero_character_fbx = hero_character_root / hero_character["fbx"]
if (not hero_character_fbx.is_file()
        or hashlib.sha256(hero_character_fbx.read_bytes()).hexdigest() != hero_character["fbx_sha256"]):
    raise RuntimeError("The original feline hero character FBX is missing or changed")
insignia = (hero_character_root / hero_character["insignia_source"]).resolve()
if (not insignia.is_file()
        or hashlib.sha256(insignia.read_bytes()).hexdigest() != hero_character["insignia_sha256"]):
    raise RuntimeError("The user-supplied SORA hero insignia source is missing or changed")
horse_root = source / "Horses/Nyaagyu"
horse = json.loads((horse_root / "manifest.json").read_text())
horse_name = "SM_Nyaagyu_HorseAndTack"
if (horse["schema_version"] != 1
        or horse["name"] != horse_name
        or horse["generator"] != "scripts/art/create_nyaagyu_horse_tack.py"
        or horse["fbx"] != horse_name + ".fbx"
        or horse["unreal_asset"] != f"/Game/ArtReview/Horses/{horse_name}.{horse_name}"
        or horse["rigged"] is not False):
    raise RuntimeError("The Edo horse/tack asset identity changed")
horse_fbx = horse_root / horse["fbx"]
if (not horse_fbx.is_file()
        or hashlib.sha256(horse_fbx.read_bytes()).hexdigest() != horse["fbx_sha256"]):
    raise RuntimeError("The Edo horse/tack FBX is missing or changed")
horse_insignia = (horse_root / horse["insignia_source"]).resolve()
if (not horse_insignia.is_file()
        or hashlib.sha256(horse_insignia.read_bytes()).hexdigest() != horse["insignia_sha256"]):
    raise RuntimeError("The horse/tack kamon does not match the supplied SORA logo")
naginata_root = source / "Weapons/MonofilamentNaginata"
naginata = json.loads((naginata_root / "manifest.json").read_text())
naginata_name = "SM_Nyaagyu_MonofilamentNaginata"
if (naginata["schema_version"] != 1
        or naginata["weapon_id"] != 12
        or naginata["name"] != naginata_name
        or naginata["generator"] != "scripts/art/create_monofilament_naginata.py"
        or naginata["fbx"] != naginata_name + ".fbx"
        or naginata["unreal_asset"] != f"/Game/ArtReview/Weapons/{naginata_name}.{naginata_name}"):
    raise RuntimeError("The Samurai special naginata must remain an art-review source")
naginata_fbx = naginata_root / naginata["fbx"]
if (not naginata_fbx.is_file()
        or hashlib.sha256(naginata_fbx.read_bytes()).hexdigest() != naginata["fbx_sha256"]):
    raise RuntimeError("The original naginata FBX is missing or changed")
mesh_names = manifest["characters"] + manifest["weapons"] + [hero_katana["name"]]
tasks = []
runtime_destination = "/Game/Generated/Meshes"
review_destination = "/Game/ArtReview/Characters"
review_weapon_destination = "/Game/ArtReview/Weapons"
review_horse_destination = "/Game/ArtReview/Horses"
assets.make_directory(review_destination)
assets.make_directory(review_weapon_destination)
assets.make_directory(review_horse_destination)
for name, path, destination in [(name, source / f"{name}.fbx", runtime_destination) for name in mesh_names] + [
        (bokken["name"], bokken_fbx, runtime_destination),
        (arc_carbine["name"], arc_fbx, runtime_destination),
        (hero_character_name, hero_character_fbx, review_destination),
        (horse_name, horse_fbx, review_horse_destination),
        (naginata_name, naginata_fbx, review_weapon_destination)]:
    if not path.is_file():
        raise RuntimeError(f"Required original mesh is missing: {path}")
    task = unreal.AssetImportTask()
    task.filename = str(path)
    task.destination_path = destination
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
for name in mesh_names + [bokken["name"], arc_carbine["name"]]:
    if not assets.does_asset_exist(f"/Game/Generated/Meshes/{name}"):
        raise RuntimeError(f"Unreal import did not create {name}")
if not assets.does_asset_exist(f"{review_destination}/{hero_character_name}"):
    raise RuntimeError("Unreal review import did not create the feline concept mesh")
if not assets.does_asset_exist(f"{review_horse_destination}/{horse_name}"):
    raise RuntimeError("Unreal review import did not create the Edo horse/tack study")
if not assets.does_asset_exist(f"{review_weapon_destination}/{naginata_name}"):
    raise RuntimeError("Unreal review import did not create the special naginata mesh")

# Source-authored environment heroes have one render mesh and explicit UCX
# convex collision boxes. Their linked Poly Haven source textures are verified
# separately by import_environment_palette.py and bound to slots at runtime.
environment_source = source / "Environment/Original"
environment_manifest = json.loads((environment_source / "manifest.json").read_text())
environment_names = ["SM_Edo_LanternPost", "SM_Nyaagyu_ToriiGate", "SM_Alien_DebtKiosk"]
if ([entry["name"] for entry in environment_manifest["assets"]] != environment_names
        or environment_manifest["generator"] != "scripts/art/create_edo_environment_props.py"):
    raise RuntimeError("The original environment prop identities changed")
street_source = source / "Environment/StreetDebtTerminal"
street_terminal = json.loads((street_source / "manifest.json").read_text())
street_name = "SM_Alien_StreetDebtTerminal"
if (street_terminal["schema_version"] != 1 or street_terminal["name"] != street_name
        or street_terminal["generator"] != "scripts/art/create_street_debt_terminal.py"
        or street_terminal["unreal_asset"] != f"/Game/Generated/Environment/Props/{street_name}.{street_name}"):
    raise RuntimeError("The original street debt terminal identity changed")
sluice_source = source / "Environment/NyaagyuSluice"
sluice = json.loads((sluice_source / "manifest.json").read_text())
sluice_name = "SM_Nyaagyu_IrrigationSluice"
if (sluice["schema_version"] != 1 or sluice["name"] != sluice_name
        or sluice["generator"] != "scripts/art/create_nyaagyu_sluice.py"
        or sluice["unreal_asset"] != f"/Game/Generated/Environment/Props/{sluice_name}.{sluice_name}"):
    raise RuntimeError("The original Nyaagyu irrigation sluice identity changed")
loom_source = source / "Environment/SilkFoundryLoom"
loom = json.loads((loom_source / "manifest.json").read_text())
loom_name = "SM_SilkFoundry_LevyLoom"
if (loom["schema_version"] != 1 or loom["name"] != loom_name
        or loom["generator"] != "scripts/art/create_silk_foundry_loom.py"
        or loom["unreal_asset"] != f"/Game/Generated/Environment/Props/{loom_name}.{loom_name}"
        or loom["collision_boxes"] != 4):
    raise RuntimeError("The original Silk Foundry loom identity changed")
dojo_source = source / "Environment/NyaagyuDojo"
dojo = json.loads((dojo_source / "manifest.json").read_text())
dojo_name = "SM_Nyaagyu_EstateDojo"
if (dojo["schema_version"] != 1 or dojo["name"] != dojo_name
        or dojo["generator"] != "scripts/art/create_nyaagyu_dojo.py"
        or dojo["unreal_asset"] != f"/Game/Generated/Environment/Props/{dojo_name}.{dojo_name}"
        or dojo["sora_kamon_svg_sha256"] != logo_manifest["source_sha256"]
        or dojo["collision_boxes"] != 3):
    raise RuntimeError("The original Nyaagyu Estate dojo identity changed")
assets.make_directory("/Game/Generated/Environment/Props")
environment_tasks = []
environment_entries = ([(environment_source, entry) for entry in environment_manifest["assets"]]
                       + [(street_source, street_terminal), (sluice_source, sluice),
                          (loom_source, loom), (dojo_source, dojo)])
for entry_root, entry in environment_entries:
    fbx = entry_root / entry["fbx"]
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
    options.static_mesh_import_data.set_editor_property("build_nanite", entry["name"] == dojo_name)
    task.options = options
    environment_tasks.append(task)
tools.import_asset_tasks(environment_tasks)
for name in environment_names + [street_name, sluice_name, loom_name, dojo_name]:
    mesh = assets.load_asset(f"/Game/Generated/Environment/Props/{name}")
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError(f"Unreal import did not create the original environment prop: {name}")
    if name == dojo_name and not mesh.get_editor_property("nanite_settings").get_editor_property("enabled"):
        raise RuntimeError("The authored Estate dojo did not build its Windows Nanite data")

# Modular estate relief is campaign presentation only. The HI tiles build
# Nanite data for supported Windows GPUs; MAC tiles are independent conventional
# meshes for the M1 path. Neither changes the kernel's collision surface.
terrain_root = source / "Environment/NyaagyuTerrain"
terrain = json.loads((terrain_root / "manifest.json").read_text())
if (terrain["schema_version"] != 1
        or terrain["generator"] != "scripts/art/create_nyaagyu_mesh_terrain.py"
        or terrain["tile_layout"] != [4, 4]
        or terrain["tile_size_cm"] != [1600, 1300]
        or terrain["world_xy_cm"] != [-3200, -2600, 3200, 2600]
        or terrain["max_visual_collision_delta_cm"] > 5
        or terrain["material_slots"] != ["M_Terrain_Soil_PolyHaven", "M_Terrain_Stone_PolyHaven"]
        or len(terrain["tiles"]) != 32):
    raise RuntimeError("The source-authored estate terrain identity or collision tolerance changed")
assets.make_directory("/Game/Generated/Environment/Terrain")
terrain_tasks = []
for tier in ("hi", "mac"):
    for y in range(4):
        for x in range(4):
            record = next((tile for tile in terrain["tiles"]
                           if tile["tier"] == tier and tile["index"] == [x, y]), None)
            name = f"SM_NyaagyuTerrain_{tier.upper()}_X{x}_Y{y}"
            if (record is None or record["name"] != name
                    or record["fbx"] != name + ".fbx"
                    or record["placement_center_cm"] != [-2400 + 1600*x, -1950 + 1300*y, 0]):
                raise RuntimeError(f"Estate terrain tile identity changed: {name}")
            fbx = terrain_root / record["fbx"]
            if (not fbx.is_file()
                    or hashlib.sha256(fbx.read_bytes()).hexdigest() != record["fbx_sha256"]):
                raise RuntimeError(f"Estate terrain tile is missing or changed: {fbx}")
            task = unreal.AssetImportTask()
            task.filename = str(fbx)
            task.destination_path = "/Game/Generated/Environment/Terrain"
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
            options.static_mesh_import_data.set_editor_property("build_nanite", tier == "hi")
            task.options = options
            terrain_tasks.append(task)
tools.import_asset_tasks(terrain_tasks)
for task in terrain_tasks:
    path = f"{task.destination_path}/{task.destination_name}"
    mesh = assets.load_asset(path)
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError(f"Unreal import did not create estate terrain: {path}")
    nanite_enabled = bool(mesh.get_editor_property("nanite_settings").get_editor_property("enabled"))
    if nanite_enabled != ("_HI_" in task.destination_name):
        raise RuntimeError(f"Unreal terrain Nanite setting did not match its tier: {path}")

# The Estate's photographed broadleaf tree replaces its primitive pink
# canopies. The authored two-tier meshes are decorative and retain no combat
# collision; masked leaves and 2K PBR maps are imported explicitly so FBX
# material guesses cannot silently turn the canopy into opaque cards.
tree_root = source / "Environment/PolyHaven/TreeSmall02"
tree = json.loads((tree_root / "manifest.json").read_text())
foliage_root = "/Game/Generated/Environment/Foliage"
foliage_textures = foliage_root + "/Textures"
if (tree["schema_version"] != 1 or tree["asset_id"] != "tree_small_02"
        or tree["license"] != "CC0-1.0; https://polyhaven.com/license"
        or tree["generator"] != "scripts/art/create_nyaagyu_photoreal_tree.py"
        or tree["material_slots"] != ["M_NyaagyuTree_Branches", "M_NyaagyuTree_Leaves", "M_NyaagyuTree_Trunk"]
        or tree["instances_in_nyaagyu_estate"] != 10 or tree["gameplay_collision"] is not False
        or len(tree["meshes"]) != 2 or len(tree["texture_files"]) != 10):
    raise RuntimeError("The pinned Nyaagyu foliage source identity changed")
for file in tree["upstream_files"] + tree["texture_files"]:
    path = tree_root / file["path"]
    if (not path.is_file() or path.stat().st_size != file["bytes"]
            or hashlib.sha256(path.read_bytes()).hexdigest() != file["sha256"]):
        raise RuntimeError(f"Pinned CC0 tree file missing or changed: {path}")
assets.make_directory(foliage_root)
assets.make_directory(foliage_textures)
tree_tasks = []
for tier, record in zip(("hi", "mac"), tree["meshes"]):
    name = f"SM_NyaagyuTree_{tier.upper()}"
    fbx = tree_root / record["fbx"]
    if (record["tier"] != tier or record["name"] != name or record["fbx"] != name + ".fbx"
            or record["unreal_asset"] != f"{foliage_root}/{name}.{name}"
            or record["nanite"] != (tier == "hi") or not fbx.is_file()
            or hashlib.sha256(fbx.read_bytes()).hexdigest() != record["fbx_sha256"]):
        raise RuntimeError(f"Nyaagyu foliage LOD missing or changed: {name}")
    task = unreal.AssetImportTask()
    task.filename = str(fbx)
    task.destination_path = foliage_root
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = True
    options = unreal.FbxImportUI()
    options.import_mesh = True
    options.import_materials = False
    options.import_textures = False
    options.import_as_skeletal = False
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    options.static_mesh_import_data.combine_meshes = True
    options.static_mesh_import_data.generate_lightmap_u_vs = False
    options.static_mesh_import_data.auto_generate_collision = False
    options.static_mesh_import_data.set_editor_property("build_nanite", tier == "hi")
    task.options = options
    tree_tasks.append(task)
tools.import_asset_tasks(tree_tasks)

tree_textures = {}
for file in tree["texture_files"]:
    path = tree_root / file["path"]
    channel = path.stem.removeprefix("tree_small_02_").removesuffix("_2k")
    name = "T_NyaagyuTree_" + channel
    task = unreal.AssetImportTask()
    task.filename = str(path)
    task.destination_path = foliage_textures
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = True
    tools.import_asset_tasks([task])
    texture = assets.load_asset(f"{foliage_textures}/{name}")
    if not isinstance(texture, unreal.Texture2D) or channel in tree_textures:
        raise RuntimeError(f"Nyaagyu foliage texture import failed: {name}")
    texture.set_editor_property("srgb", channel.endswith("diff"))
    if channel.endswith("nor_dx"):
        texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
        texture.set_editor_property("flip_green_channel", False)
    elif channel.endswith("arm") or channel.endswith("alpha"):
        texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
    texture.set_editor_property("max_texture_size", 2048)
    assets.save_loaded_asset(texture)
    tree_textures[channel] = texture

tree_materials = {}
material_lib = unreal.MaterialEditingLibrary
for role, prefix in (("Branches", "branch_"), ("Leaves", "leaves_"), ("Trunk", "")):
    name = "M_NyaagyuTree_" + role
    object_path = f"{foliage_root}/{name}"
    material = (assets.load_asset(object_path) if assets.does_asset_exist(object_path)
                else tools.create_asset(name, foliage_root, unreal.Material, unreal.MaterialFactoryNew()))
    material_lib.delete_all_material_expressions(material)
    material.set_editor_property("two_sided", True)
    if role == "Leaves":
        material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
    for parameter, channel, property_name, y in (
        ("AlbedoMap", prefix + "diff", unreal.MaterialProperty.MP_BASE_COLOR, -250),
        ("NormalMap", prefix + "nor_dx", unreal.MaterialProperty.MP_NORMAL, 0)):
        texture = material_lib.create_material_expression(material, unreal.MaterialExpressionTextureSampleParameter2D, -600, y)
        texture.set_editor_property("parameter_name", parameter)
        texture.set_editor_property("texture", tree_textures[channel])
        if not material_lib.connect_material_property(texture, "RGB", property_name):
            raise RuntimeError(f"Could not bind Nyaagyu foliage {role} {parameter}")
    arm = material_lib.create_material_expression(material, unreal.MaterialExpressionTextureSampleParameter2D, -600, 250)
    arm.set_editor_property("parameter_name", "ARMMap")
    arm.set_editor_property("texture", tree_textures[prefix + "arm"])
    for channel, property_name in (("R", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION),
                                   ("G", unreal.MaterialProperty.MP_ROUGHNESS),
                                   ("B", unreal.MaterialProperty.MP_METALLIC)):
        if not material_lib.connect_material_property(arm, channel, property_name):
            raise RuntimeError(f"Could not bind Nyaagyu foliage {role} ARM {channel}")
    if role == "Leaves":
        alpha = material_lib.create_material_expression(material, unreal.MaterialExpressionTextureSampleParameter2D, -600, 500)
        alpha.set_editor_property("parameter_name", "AlphaMap")
        alpha.set_editor_property("texture", tree_textures["leaves_alpha"])
        if not material_lib.connect_material_property(alpha, "R", unreal.MaterialProperty.MP_OPACITY_MASK):
            raise RuntimeError("Could not bind masked Nyaagyu foliage alpha")
    material_lib.layout_material_expressions(material)
    material_lib.recompile_material(material)
    assets.save_loaded_asset(material)
    tree_materials[name] = material

for record in tree["meshes"]:
    mesh = assets.load_asset(f"{foliage_root}/{record['name']}")
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError(f"Unreal did not import Nyaagyu foliage: {record['name']}")
    actual_slots = [str(entry.get_editor_property("material_slot_name"))
                    for entry in mesh.get_editor_property("static_materials")]
    if sorted(actual_slots) != sorted(tree["material_slots"]):
        raise RuntimeError(f"Nyaagyu foliage material zones lost on FBX import: {actual_slots}")
    for index, slot in enumerate(actual_slots):
        mesh.set_material(index, tree_materials[slot])
    if bool(mesh.get_editor_property("nanite_settings").get_editor_property("enabled")) != record["nanite"]:
        raise RuntimeError(f"Nyaagyu foliage Nanite tier mismatch: {record['name']}")
    assets.save_loaded_asset(mesh)

runtime_skin = json.loads((source / "Characters/Hero/runtime_skin_manifest.json").read_text())
if (runtime_skin.get("schema_version") != 1
        or runtime_skin.get("generator") != "scripts/art/rig_nyaakoto_runtime.py"
        or runtime_skin.get("skeletal_fbx") != "SK_NyaagyuSamurai.fbx"
        or runtime_skin.get("walk_fbx") != "A_NyaagyuSamurai_Walk.fbx"):
    raise RuntimeError("Nyaakoto runtime skin identity changed")
for filename_key, hash_key in (("skeletal_fbx", "skeletal_fbx_sha256"),
                               ("walk_fbx", "walk_fbx_sha256")):
    path = source / runtime_skin[filename_key]
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != runtime_skin[hash_key]:
        raise RuntimeError(f"Pinned Nyaakoto runtime mesh or animation changed: {path}")

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

runpy.run_path(str(root / "scripts/unreal/import_nyaakoto_lods.py"), run_name="__main__")

path = "/Game/Generated/Materials/M_ArenaSurface"
material = assets.load_asset(path) if assets.does_asset_exist(path) else tools.create_asset(
    "M_ArenaSurface", "/Game/Generated/Materials", unreal.Material, unreal.MaterialFactoryNew())
lib = unreal.MaterialEditingLibrary
lib.delete_all_material_expressions(material)
color = lib.create_material_expression(material, unreal.MaterialExpressionVectorParameter, -600, -200)
color.set_editor_property("parameter_name", "BaseColor")
color.set_editor_property("default_value", unreal.LinearColor(.35,.4,.4,1))
roughness = lib.create_material_expression(material, unreal.MaterialExpressionScalarParameter,-400,250)
roughness.set_editor_property("parameter_name", "Roughness")
roughness.set_editor_property("default_value", .72)
metallic = lib.create_material_expression(material, unreal.MaterialExpressionScalarParameter,-400,350)
metallic.set_editor_property("parameter_name", "Metallic")
metallic.set_editor_property("default_value", 0)
lib.connect_material_property(color, "", unreal.MaterialProperty.MP_BASE_COLOR)
lib.connect_material_property(roughness, "", unreal.MaterialProperty.MP_ROUGHNESS)
lib.connect_material_property(metallic, "", unreal.MaterialProperty.MP_METALLIC)
lib.recompile_material(material)
assets.save_asset(path)

font = source / "Fonts/NotoSansCJKjp-Regular.otf"
if not font.is_file() or not (source / "Fonts/OFL.txt").is_file():
    raise RuntimeError("Japanese runtime font and its redistribution license are required")

runpy.run_path(str(root / "scripts/unreal/import_nyaakoto_pbr.py"), run_name="__main__")
assets.save_directory("/Game/Generated", only_if_is_dirty=False, recursive=True)
unreal.log(f"SORA_ASSET_IMPORT_COMPLETE: {len(tasks)} character/weapon/horse meshes, {len(environment_tasks)} source-authored environment props, {len(terrain_tasks)} mesh terrain tiles, {len(tree_tasks)} CC0 foliage LODs; Japanese font staged separately")
