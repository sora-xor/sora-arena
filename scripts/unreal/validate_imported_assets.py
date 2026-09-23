"""Validate the authored UE asset packages after both import scripts have run.

Run in UE 5.8.2 with ``-ExecutePythonScript=<this file>``. For a host-only
manifest check, run ``python3 scripts/unreal/validate_imported_assets.py
--source-only``. The host check cannot establish that Unreal packages exist.
"""

import hashlib
import json
from pathlib import Path
import re
import sys


RELEASE_VERSION = "5.8.2"
MESHES = "/Game/Generated/Meshes"
PROPS = "/Game/Generated/Environment/Props"
PALETTE = "/Game/Generated/Environment"
TERRAIN = "/Game/Generated/Environment/Terrain"
FOLIAGE = "/Game/Generated/Environment/Foliage"
NYAAKOTO = "/Game/Generated/Characters/Nyaakoto"


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def read_manifest(path):
    require(path.is_file(), f"Missing source manifest: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def source_file(source_root, relative):
    path = (source_root / relative).resolve()
    require(path.is_relative_to(source_root.resolve()) and path.is_file(),
            f"Missing or out-of-tree source art: {path}")
    return path


def add(specs, object_path, class_name):
    require(object_path.startswith("/Game/") and "." in object_path,
            f"Invalid Unreal object path: {object_path}")
    require(object_path not in specs, f"Duplicate Unreal asset: {object_path}")
    specs[object_path] = class_name


def named_mesh(source_root, specs, folder, manifest_name, expected_name, package,
               *, schema_version=1, rigged=None):
    art_root = source_root / folder
    record = read_manifest(art_root / manifest_name)
    path = f"{package}/{expected_name}.{expected_name}"
    require(record.get("schema_version") == schema_version
            and record.get("name") == expected_name
            and record.get("fbx") == f"{expected_name}.fbx"
            and record.get("unreal_asset") == path,
            f"Unexpected original mesh identity: {art_root / manifest_name}")
    if rigged is not None:
        require(record.get("rigged") is rigged,
                f"Unexpected rig state: {art_root / manifest_name}")
    fbx = source_file(art_root, record["fbx"])
    require(hashlib.sha256(fbx.read_bytes()).hexdigest() == record.get("fbx_sha256"),
            f"Original mesh hash changed: {fbx}")
    add(specs, path, "StaticMesh")


def nyaakoto_pbr_source(source_root):
    """Check source map identity before trusting generated material packages."""
    art_root = source_root / "Characters/Hero/PBR"
    record = read_manifest(art_root / "manifest.json")
    require(record.get("schema_version") == 1
            and record.get("generator") == "scripts/art/create_nyaakoto_pbr_textures.py"
            and record.get("source_license") ==
            "Project-owned procedurally authored maps; no external texture asset"
            and [group.get("name") for group in record.get("maps", [])] ==
            ["fur_grey", "fur_white", "fur_charcoal", "silk_indigo", "lacquer_oxblood", "neutral"]
            and len(record.get("material_slots", {})) == 23,
            "The Nyaakoto PBR source identity changed")
    groups = {group["name"]: group for group in record["maps"]}
    for name, group in groups.items():
        require(group.get("resolution") == ([4, 4] if name == "neutral" else [2048, 2048])
                and [item.get("channel") for item in group.get("maps", [])] ==
                ["Albedo", "NormalDX", "ORM"],
                f"Nyaakoto PBR texture channels changed: {name}")
        for item in group["maps"]:
            filename = f"T_Nyaakoto_{name}_{item['channel']}.png"
            require(item.get("file") == filename,
                    f"Nyaakoto PBR texture identity changed: {name}")
            path = source_file(art_root, filename)
            data = path.read_bytes()
            require(hashlib.sha256(data).hexdigest() == item.get("sha256")
                    and data[:16] == b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR",
                    f"Nyaakoto PBR source map changed: {path}")
    for slot, values in record["material_slots"].items():
        require(re.fullmatch(r"M_Hero_[A-Za-z0-9]+", slot) is not None
                and values.get("surface") in groups
                and len(values.get("tint", [])) == 3
                and all(0 <= value <= 1 for value in values["tint"])
                and 0 < values.get("roughness_scale", 0) <= 2
                and 0 <= values.get("metallic_scale", -1) <= 1,
                f"Nyaakoto PBR material slot changed: {slot}")
    return record


def nyaakoto_lod_source(source_root):
    """Validate the two authored FBXs; they live inside one skeletal package."""
    hero = source_root / "Characters/Hero"
    record = read_manifest(hero / "LOD/manifest.json")
    runtime = read_manifest(hero / "runtime_skin_manifest.json")
    pbr = read_manifest(hero / "PBR/manifest.json")
    require(record.get("schema_version") == 1
            and record.get("generator") == "scripts/art/generate_nyaakoto_lods.py"
            and record.get("source_blend_sha256") == runtime.get("runtime_blend_sha256")
            and record.get("lod0_fbx_sha256") == runtime.get("skeletal_fbx_sha256")
            and record.get("sora_kamon_svg_sha256") == runtime.get("sora_kamon_svg_sha256")
            and [entry.get("level") for entry in record.get("lods", [])] == [1, 2],
            "The Nyaakoto LOD source identities changed")
    last_vertices = runtime["source_vertices"]
    for entry in record["lods"]:
        file = source_file(hero / "LOD", entry["fbx"])
        require(hashlib.sha256(file.read_bytes()).hexdigest() == entry["sha256"]
                and set(entry["material_slots"]) == set(pbr["material_slots"])
                and set(entry["bone_names"]) == set(runtime["skeleton_bones"])
                and 0 < entry["vertices"] < last_vertices * .7,
                f"Nyaakoto LOD{entry['level']} is missing, changed or insufficiently reduced")
        last_vertices = entry["vertices"]
    return record


def expected_assets(project_root):
    """Return exact package/class expectations from the pinned source manifests."""
    source_root = project_root / "Content/SourceArt"
    manifest = read_manifest(source_root / "manifest.json")
    characters = ["SM_NyaagyuSamurai", "SM_AlienBanker"]
    weapons = [f"SM_Weapon_{index:02d}" for index in range(18)]
    skeletal = ["SK_NyaagyuSamurai", "SK_AlienBanker"]
    require(manifest.get("characters") == characters
            and manifest.get("weapons") == weapons
            and manifest.get("skeletal_characters") == skeletal
            and manifest.get("walk_animations") ==
            ["A_NyaagyuSamurai_Walk", "A_AlienBanker_Walk"],
            "The original character, weapon or animation manifest changed")
    hero = manifest.get("hero_katana", {})
    require(hero.get("name") == "SM_Nyaagyu_HeroKatana"
            and hero.get("fbx") == "SM_Nyaagyu_HeroKatana.fbx",
            "The hero katana identity changed")

    specs = {}
    for name in characters + weapons + [hero["name"]]:
        source_file(source_root, f"{name}.fbx")
        add(specs, f"{MESHES}/{name}.{name}", "StaticMesh")
    for name in skeletal:
        source_file(source_root, f"{name}.fbx")
        add(specs, f"{MESHES}/{name}.{name}", "SkeletalMesh")
        short_name = name.removeprefix("SK_")
        for action in ("Idle", "Walk"):
            animation = f"A_{short_name}_{action}"
            if action == "Walk":
                source_file(source_root, f"{animation}.fbx")
            add(specs, f"/Game/Generated/Animations/{animation}.{animation}", "AnimSequence")

    pbr = nyaakoto_pbr_source(source_root)
    nyaakoto_lod_source(source_root)
    for group in pbr["maps"]:
        for item in group["maps"]:
            name = Path(item["file"]).stem
            add(specs, f"{NYAAKOTO}/Textures/{name}.{name}", "Texture2D")
    add(specs, f"{NYAAKOTO}/M_Nyaakoto_PBR.M_Nyaakoto_PBR", "Material")
    for slot in pbr["material_slots"]:
        name = "MI_Nyaakoto_" + slot.removeprefix("M_Hero_")
        add(specs, f"{NYAAKOTO}/{name}.{name}", "MaterialInstanceConstant")

    named_mesh(source_root, specs, "Weapons/Original", "manifest.json",
               "SM_Nyaagyu_DojoBokken", MESHES)
    named_mesh(source_root, specs, "Weapons/Original", "arc_carbine_manifest.json",
               "SM_Nyaagyu_ArcCarbine", MESHES)
    named_mesh(source_root, specs, "Characters/Hero", "manifest.json",
               "SM_Nyaagyu_HeroCharacter", "/Game/ArtReview/Characters",
               schema_version=2, rigged=False)
    named_mesh(source_root, specs, "Horses/Nyaagyu", "manifest.json",
               "SM_Nyaagyu_HorseAndTack", "/Game/ArtReview/Horses",
               rigged=False)
    named_mesh(source_root, specs, "Weapons/MonofilamentNaginata", "manifest.json",
               "SM_Nyaagyu_MonofilamentNaginata", "/Game/ArtReview/Weapons")

    original = read_manifest(source_root / "Environment/Original/manifest.json")
    require(original.get("schema_version") == 2
            and [entry.get("name") for entry in original.get("assets", [])] ==
            ["SM_Edo_LanternPost", "SM_Nyaagyu_ToriiGate", "SM_Alien_DebtKiosk"],
            "The original environment prop manifest changed")
    logo_svg = source_file(source_root / "UI", "sora_logo_NOtext2.svg")
    require(hashlib.sha256(logo_svg.read_bytes()).hexdigest() ==
            original.get("sora_kamon_svg_sha256"),
            "The gate kamon does not match the supplied SORA logo")
    for entry in original["assets"]:
        name = entry["name"]
        require(entry.get("fbx") == f"{name}.fbx", f"Invalid prop FBX: {name}")
        fbx = source_file(source_root / "Environment/Original", entry["fbx"])
        require(hashlib.sha256(fbx.read_bytes()).hexdigest() == entry.get("fbx_sha256"),
                f"Original environment mesh hash changed: {fbx}")
        add(specs, f"{PROPS}/{name}.{name}", "StaticMesh")
    for folder, name in (
        ("StreetDebtTerminal", "SM_Alien_StreetDebtTerminal"),
        ("NyaagyuSluice", "SM_Nyaagyu_IrrigationSluice"),
        ("SilkFoundryLoom", "SM_SilkFoundry_LevyLoom"),
        ("NyaagyuDojo", "SM_Nyaagyu_EstateDojo"),
        ("NyaagyuKura", "SM_Nyaagyu_ProvisionKura"),
    ):
        named_mesh(source_root, specs, f"Environment/{folder}", "manifest.json",
                   name, PROPS)
    dojo_root = source_root / "Environment/NyaagyuDojo"
    dojo = read_manifest(dojo_root / "manifest.json")
    require(dojo.get("generator") == "scripts/art/create_nyaagyu_dojo.py"
            and dojo.get("collision_boxes") == 3
            and dojo.get("shoji_bays") == 4
            and dojo.get("roof_tile_count") == 748
            and dojo.get("sora_kamon_svg_sha256") ==
            hashlib.sha256(logo_svg.read_bytes()).hexdigest(),
            "The original Nyaagyu dojo source identity changed")
    kura = read_manifest(source_root / "Environment/NyaagyuKura/manifest.json")
    require(kura.get("generator") == "scripts/art/create_nyaagyu_kura.py"
            and kura.get("collision_boxes") == 3
            and kura.get("roof_tile_count") == 600
            and kura.get("shutter_count") == 4
            and kura.get("palette_asset_ids") ==
            ["wood_planks_dirt", "stone_floor", "grey_roof_tiles", "white_plaster_02"]
            and kura.get("sora_kamon_svg_sha256") ==
            hashlib.sha256(logo_svg.read_bytes()).hexdigest(),
            "The original Nyaagyu provision storehouse source identity changed")

    terrain_root = source_root / "Environment/NyaagyuTerrain"
    terrain = read_manifest(terrain_root / "manifest.json")
    require(terrain.get("schema_version") == 1
            and terrain.get("generator") == "scripts/art/create_nyaagyu_mesh_terrain.py"
            and terrain.get("tile_layout") == [4, 4]
            and terrain.get("tile_size_cm") == [1600, 1300]
            and terrain.get("world_xy_cm") == [-3200, -2600, 3200, 2600]
            and terrain.get("max_visual_collision_delta_cm", 100) <= 5
            and terrain.get("material_slots") ==
            ["M_Terrain_Soil_PolyHaven", "M_Terrain_Stone_PolyHaven"]
            and len(terrain.get("tiles", [])) == 32,
            "The modular estate terrain identity changed")
    for tier in ("hi", "mac"):
        for y in range(4):
            for x in range(4):
                matching = [tile for tile in terrain["tiles"]
                            if tile.get("tier") == tier and tile.get("index") == [x, y]]
                require(len(matching) == 1, f"Missing or duplicate terrain tile: {tier} {x},{y}")
                tile = matching[0]
                name = f"SM_NyaagyuTerrain_{tier.upper()}_X{x}_Y{y}"
                require(tile.get("name") == name
                        and tile.get("fbx") == f"{name}.fbx"
                        and tile.get("placement_center_cm") ==
                        [-2400 + 1600*x, -1950 + 1300*y, 0],
                        f"Estate terrain tile identity changed: {name}")
                fbx = source_file(terrain_root, tile["fbx"])
                require(hashlib.sha256(fbx.read_bytes()).hexdigest() == tile.get("fbx_sha256"),
                        f"Estate terrain source changed: {fbx}")
                add(specs, f"{TERRAIN}/{name}.{name}", "StaticMesh")

    tree_root = source_root / "Environment/PolyHaven/TreeSmall02"
    tree = read_manifest(tree_root / "manifest.json")
    require(tree.get("schema_version") == 1
            and tree.get("asset_id") == "tree_small_02"
            and tree.get("license") == "CC0-1.0; https://polyhaven.com/license"
            and tree.get("generator") == "scripts/art/create_nyaagyu_photoreal_tree.py"
            and tree.get("material_slots") == ["M_NyaagyuTree_Branches", "M_NyaagyuTree_Leaves", "M_NyaagyuTree_Trunk"]
            and tree.get("gameplay_collision") is False
            and tree.get("instances_in_nyaagyu_estate") == 10
            and len(tree.get("upstream_files", [])) == 11
            and len(tree.get("texture_files", [])) == 10
            and len(tree.get("meshes", [])) == 2,
            "The pinned Nyaagyu CC0 tree identity changed")
    for file in tree["upstream_files"] + tree["texture_files"]:
        path = source_file(tree_root, file["path"])
        require(path.stat().st_size == file["bytes"]
                and hashlib.sha256(path.read_bytes()).hexdigest() == file["sha256"],
                f"Pinned tree source changed: {path}")
    for name, digest in ((tree["source_blend"], tree["source_blend_sha256"]),
                         (tree["preview"], tree["preview_sha256"])):
        path = source_file(tree_root, name)
        require(hashlib.sha256(path.read_bytes()).hexdigest() == digest,
                f"Nyaagyu tree source review changed: {path}")
    for tier, record in zip(("hi", "mac"), tree["meshes"]):
        name = f"SM_NyaagyuTree_{tier.upper()}"
        require(record.get("tier") == tier and record.get("name") == name
                and record.get("fbx") == name + ".fbx"
                and record.get("unreal_asset") == f"{FOLIAGE}/{name}.{name}"
                and record.get("nanite") == (tier == "hi")
                and 60000 <= record.get("source_triangles", 0) <= 400000,
                f"The Nyaagyu tree {tier} LOD changed")
        path = source_file(tree_root, record["fbx"])
        require(hashlib.sha256(path.read_bytes()).hexdigest() == record["fbx_sha256"],
                f"Nyaagyu tree FBX changed: {path}")
        add(specs, record["unreal_asset"], "StaticMesh")
    for role in ("Branches", "Leaves", "Trunk"):
        name = f"M_NyaagyuTree_{role}"
        add(specs, f"{FOLIAGE}/{name}.{name}", "Material")
    for file in tree["texture_files"]:
        channel = Path(file["path"]).stem.removeprefix("tree_small_02_").removesuffix("_2k")
        name = f"T_NyaagyuTree_{channel}"
        add(specs, f"{FOLIAGE}/Textures/{name}.{name}", "Texture2D")

    logo_root = source_root / "UI"
    logo = read_manifest(logo_root / "sora_logo_manifest.json")
    require(logo.get("unreal_asset") ==
            "/Game/Generated/UI/T_SoraResistanceLogo.T_SoraResistanceLogo",
            "The SORA resistance insignia identity changed")
    for name_key, hash_key in (("source_svg", "source_sha256"),
                               ("runtime_png", "runtime_sha256")):
        logo_file = source_file(logo_root, logo[name_key])
        require(hashlib.sha256(logo_file.read_bytes()).hexdigest() == logo[hash_key],
                f"SORA logo source hash changed: {logo_file}")
    add(specs, logo["unreal_asset"], "Texture2D")
    if (logo_root / "Nyaagyu_Title_KeyArt.png").is_file():
        add(specs, "/Game/Generated/UI/T_NyaagyuTitle.T_NyaagyuTitle", "Texture2D")

    add(specs, "/Game/Generated/Materials/M_ArenaSurface.M_ArenaSurface", "Material")
    add(specs, f"{PALETTE}/M_Nyaagyu_PBR.M_Nyaagyu_PBR", "Material")
    add(specs, f"{PALETTE}/M_Nyaagyu_Sky.M_Nyaagyu_Sky", "Material")
    palette_root = source_root / "Environment/PolyHaven"
    palette = read_manifest(palette_root / "manifest.json")
    require(palette.get("schema_version") == 1
            and palette.get("asset_license") == "CC0-1.0"
            and [record.get("role") for record in palette.get("assets", [])] ==
            ["timber", "stone", "soil", "metal", "sky"],
            "The pinned environment palette changed")
    for record in palette["assets"]:
        role = record["role"]
        channels = [file.get("channel") for file in record.get("files", [])]
        require(channels == (["hdri"] if role == "sky" else
                             ["Diffuse", "nor_dx", "arm"]),
                f"Invalid palette channels for {role}")
        for file in record["files"]:
            source_file(palette_root, file["file"])
            name = ("T_NyaagyuOvercast" if role == "sky" else
                    f"T_{role.title()}_{file['channel']}")
            kind = "TextureCube" if role == "sky" else "Texture2D"
            add(specs, f"{PALETTE}/Textures/{name}.{name}", kind)
        if role != "sky":
            name = f"MI_Nyaagyu_{role.title()}"
            add(specs, f"{PALETTE}/{name}.{name}", "MaterialInstanceConstant")
    roof = read_manifest(palette_root / "GreyRoofTiles/manifest.json")
    require(roof.get("schema_version") == 1
            and roof.get("asset_id") == "grey_roof_tiles"
            and roof.get("role") == "kawara"
            and roof.get("license") == "CC0-1.0"
            and roof.get("source_dimensions_mm") == [3000, 3000]
            and roof.get("tile_size_cm") == 300.0
            and roof.get("unreal_instance") ==
            f"{PALETTE}/MI_Nyaagyu_Kawara.MI_Nyaagyu_Kawara"
            and [item.get("channel") for item in roof.get("files", [])] ==
            ["Diffuse", "nor_dx", "arm"],
            "The pinned CC0 ceramic kawara surface changed")
    for item in roof["files"]:
        source = source_file(palette_root / "GreyRoofTiles", item["file"])
        require(hashlib.sha256(source.read_bytes()).hexdigest() == item["sha256"],
                f"Kawara source map changed: {source}")
        name = f"T_Kawara_{item['channel']}"
        add(specs, f"{PALETTE}/Textures/{name}.{name}", "Texture2D")
    add(specs, roof["unreal_instance"], "MaterialInstanceConstant")
    plaster = read_manifest(palette_root / "WhitePlaster02/manifest.json")
    require(plaster.get("schema_version") == 1
            and plaster.get("asset_id") == "white_plaster_02"
            and plaster.get("role") == "plaster"
            and plaster.get("license") == "CC0-1.0"
            and plaster.get("source_dimensions_mm") == [1000, 1000]
            and plaster.get("tile_size_cm") == 100.0
            and plaster.get("unreal_instance") ==
            f"{PALETTE}/MI_Nyaagyu_Plaster.MI_Nyaagyu_Plaster"
            and [item.get("channel") for item in plaster.get("files", [])] ==
            ["Diffuse", "nor_dx", "arm"],
            "The pinned CC0 white plaster surface changed")
    for item in plaster["files"]:
        source = source_file(palette_root / "WhitePlaster02", item["file"])
        require(hashlib.sha256(source.read_bytes()).hexdigest() == item["sha256"],
                f"White plaster source map changed: {source}")
        name = f"T_Plaster_{item['channel']}"
        add(specs, f"{PALETTE}/Textures/{name}.{name}", "Texture2D")
    add(specs, plaster["unreal_instance"], "MaterialInstanceConstant")
    return specs


def validate_loaded_assets(unreal, specs):
    """Fail on absent packages and class mismatches; return the checked count."""
    asset_library = unreal.EditorAssetLibrary
    for path, class_name in specs.items():
        expected_class = getattr(unreal, class_name)
        asset = asset_library.load_asset(path)
        require(asset is not None, f"Missing imported Unreal asset: {path}")
        require(isinstance(asset, expected_class),
                f"Wrong Unreal class for {path}: expected {class_name}, "
                f"got {type(asset).__name__}")
    pbr = nyaakoto_pbr_source(Path(unreal.Paths.project_dir()).resolve() / "Content/SourceArt")
    hero = asset_library.load_asset(f"{MESHES}/SK_NyaagyuSamurai.SK_NyaagyuSamurai")
    slots = [str(entry.get_editor_property("material_slot_name"))
             for entry in hero.get_editor_property("materials")]
    require(len(slots) == len(set(slots)) == 23 and set(slots) == set(pbr["material_slots"]),
            f"Nyaakoto skeletal mesh slots do not match its authored PBR materials: {slots}")
    subsystem = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
    require(subsystem.get_lod_count(hero) == 3,
            "Nyaakoto authored LOD1/LOD2 were not imported into the runtime mesh")
    counts = [subsystem.get_num_verts(hero, index) for index in range(3)]
    require(counts[0] > 0 and 0 < counts[1] < counts[0] * .7
            and 0 < counts[2] < counts[1] * .7,
            f"Nyaakoto authored LODs did not reduce rendered vertices: {counts}")
    material_lib = unreal.MaterialEditingLibrary
    master_path = f"{NYAAKOTO}/M_Nyaakoto_PBR.M_Nyaakoto_PBR"
    master = asset_library.load_asset(master_path)
    require({str(name) for name in material_lib.get_texture_parameter_names(master)} ==
            {"AlbedoMap", "NormalMap", "ORMMap"},
            "Nyaakoto PBR master lost its three texture parameters")
    for group in pbr["maps"]:
        for item in group["maps"]:
            name = Path(item["file"]).stem
            texture = asset_library.load_asset(f"{NYAAKOTO}/Textures/{name}.{name}")
            require(bool(texture.get_editor_property("srgb")) == (item["channel"] == "Albedo"),
                    f"Nyaakoto texture color space changed: {name}")
            if item["channel"] == "NormalDX":
                require(texture.get_editor_property("compression_settings") ==
                        unreal.TextureCompressionSettings.TC_NORMALMAP
                        and not bool(texture.get_editor_property("flip_green_channel")),
                        f"Nyaakoto tangent normal import changed: {name}")
            elif item["channel"] == "ORM":
                require(texture.get_editor_property("compression_settings") ==
                        unreal.TextureCompressionSettings.TC_MASKS,
                        f"Nyaakoto ORM mask compression changed: {name}")
    for slot, surface in pbr["material_slots"].items():
        name = "MI_Nyaakoto_" + slot.removeprefix("M_Hero_")
        path = f"{NYAAKOTO}/{name}.{name}"
        instance = asset_library.load_asset(path)
        parent = instance.get_editor_property("parent")
        require(parent is not None and parent.get_path_name() == master_path,
                f"Nyaakoto instance has the wrong PBR parent: {path}")
        for parameter, channel in (("AlbedoMap", "Albedo"),
                                   ("NormalMap", "NormalDX"), ("ORMMap", "ORM")):
            texture_name = f"T_Nyaakoto_{surface['surface']}_{channel}"
            expected_path = f"{NYAAKOTO}/Textures/{texture_name}.{texture_name}"
            bound = material_lib.get_material_instance_texture_parameter_value(instance, parameter)
            require(bound is not None and bound.get_path_name() == expected_path,
                    f"Nyaakoto material {name} lost its {parameter} map binding")
        for parameter, value in (("RoughnessScale", surface["roughness_scale"]),
                                 ("MetallicScale", surface["metallic_scale"])):
            bound = material_lib.get_material_instance_scalar_parameter_value(instance, parameter)
            require(abs(bound - value) < 1e-5,
                    f"Nyaakoto material {name} changed its {parameter}")
        tint = material_lib.get_material_instance_vector_parameter_value(instance, "Tint")
        require(all(abs(getattr(tint, channel) - value) < 1e-5
                    for channel, value in zip("rgb", surface["tint"])),
                f"Nyaakoto material {name} changed its tint")
    base_path = f"{PALETTE}/M_Nyaagyu_PBR.M_Nyaagyu_PBR"
    for role in ("Timber", "Stone", "Soil", "Metal", "Kawara", "Plaster"):
        path = f"{PALETTE}/MI_Nyaagyu_{role}.MI_Nyaagyu_{role}"
        parent = asset_library.load_asset(path).get_editor_property("parent")
        require(parent is not None and parent.get_path_name() == base_path,
                f"Palette instance has the wrong PBR parent: {path}")
    roof_instance = asset_library.load_asset(f"{PALETTE}/MI_Nyaagyu_Kawara.MI_Nyaagyu_Kawara")
    for parameter, channel in (("AlbedoMap", "Diffuse"),
                               ("NormalMap", "nor_dx"), ("ARMMap", "arm")):
        expected = f"{PALETTE}/Textures/T_Kawara_{channel}.T_Kawara_{channel}"
        actual = material_lib.get_material_instance_texture_parameter_value(roof_instance, parameter)
        require(actual is not None and actual.get_path_name() == expected,
                f"Kawara instance lost its {parameter} scanned ceramic map")
        texture = asset_library.load_asset(expected)
        require(bool(texture.get_editor_property("srgb")) == (channel == "Diffuse"),
                f"Kawara {channel} texture color space changed")
        if channel == "nor_dx":
            require(texture.get_editor_property("compression_settings") ==
                    unreal.TextureCompressionSettings.TC_NORMALMAP
                    and not bool(texture.get_editor_property("flip_green_channel")),
                    "Kawara DX normal map import changed")
        if channel == "arm":
            require(texture.get_editor_property("compression_settings") ==
                    unreal.TextureCompressionSettings.TC_MASKS,
                    "Kawara AO/roughness/metallic map import changed")
    tile = material_lib.get_material_instance_vector_parameter_value(roof_instance, "TileSize")
    require(all(abs(getattr(tile, channel) - 300.0) < 1e-5 for channel in "rgb"),
            "Kawara projection lost its measured three-metre scale")
    plaster_instance = asset_library.load_asset(f"{PALETTE}/MI_Nyaagyu_Plaster.MI_Nyaagyu_Plaster")
    for parameter, channel in (("AlbedoMap", "Diffuse"),
                               ("NormalMap", "nor_dx"), ("ARMMap", "arm")):
        expected = f"{PALETTE}/Textures/T_Plaster_{channel}.T_Plaster_{channel}"
        actual = material_lib.get_material_instance_texture_parameter_value(plaster_instance, parameter)
        require(actual is not None and actual.get_path_name() == expected,
                f"Plaster instance lost its {parameter} scan map")
        texture = asset_library.load_asset(expected)
        require(bool(texture.get_editor_property("srgb")) == (channel == "Diffuse"),
                f"Plaster {channel} texture color space changed")
        if channel == "nor_dx":
            require(texture.get_editor_property("compression_settings") ==
                    unreal.TextureCompressionSettings.TC_NORMALMAP
                    and not bool(texture.get_editor_property("flip_green_channel")),
                    "Plaster DX normal import changed")
        if channel == "arm":
            require(texture.get_editor_property("compression_settings") ==
                    unreal.TextureCompressionSettings.TC_MASKS,
                    "Plaster AO/roughness/metallic import changed")
    plaster_tile = material_lib.get_material_instance_vector_parameter_value(plaster_instance, "TileSize")
    require(all(abs(getattr(plaster_tile, channel) - 100.0) < 1e-5 for channel in "rgb"),
            "Plaster projection lost its measured one-metre scale")
    for name in ("SM_Nyaagyu_EstateDojo", "SM_Nyaagyu_ProvisionKura"):
        path = f"{PROPS}/{name}.{name}"
        mesh = asset_library.load_asset(path)
        require(bool(mesh.get_editor_property("nanite_settings").get_editor_property("enabled")),
                f"Estate building lost its Windows Nanite data: {path}")
    for tier in ("HI", "MAC"):
        for y in range(4):
            for x in range(4):
                name = f"SM_NyaagyuTerrain_{tier}_X{x}_Y{y}"
                path = f"{TERRAIN}/{name}.{name}"
                mesh = asset_library.load_asset(path)
                settings = mesh.get_editor_property("nanite_settings")
                require(bool(settings.get_editor_property("enabled")) == (tier == "HI"),
                        f"Estate terrain Nanite tier mismatch: {path}")
    for tier in ("HI", "MAC"):
        name = f"SM_NyaagyuTree_{tier}"
        mesh = asset_library.load_asset(f"{FOLIAGE}/{name}.{name}")
        require(bool(mesh.get_editor_property("nanite_settings").get_editor_property("enabled")) == (tier == "HI"),
                f"Nyaagyu tree Nanite tier mismatch: {name}")
        slots = [str(entry.get_editor_property("material_slot_name"))
                 for entry in mesh.get_editor_property("static_materials")]
        require(sorted(slots) == ["M_NyaagyuTree_Branches", "M_NyaagyuTree_Leaves", "M_NyaagyuTree_Trunk"],
                f"Nyaagyu tree material zones missing: {name}")
    leaves = asset_library.load_asset(f"{FOLIAGE}/M_NyaagyuTree_Leaves.M_NyaagyuTree_Leaves")
    require(leaves.get_editor_property("blend_mode") == unreal.BlendMode.BLEND_MASKED,
            "The Nyaagyu tree leaves lost their alpha cutout")
    return len(specs)


def main():
    if "--source-only" in sys.argv:
        root = Path(__file__).resolve().parents[2]
        specs = expected_assets(root)
        print(f"SORA_ASSET_SOURCE_CHECK_COMPLETE: {len(specs)} expected Unreal packages")
        return

    import unreal

    version = unreal.SystemLibrary.get_engine_version()
    require(re.match(r"^" + re.escape(RELEASE_VERSION) + r"(?:-|$)", version) is not None,
            f"SORA asset validation requires release UE {RELEASE_VERSION}; got {version}")
    project_root = Path(unreal.Paths.project_dir()).resolve()
    specs = expected_assets(project_root)
    count = validate_loaded_assets(unreal, specs)
    unreal.log(f"SORA_ASSET_VALIDATION_COMPLETE: {count} packages loaded with expected types")


main()
