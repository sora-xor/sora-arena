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
HERO_KATANA = "/Game/Generated/Weapons/HeroKatana"
CARGO = "/Game/Generated/Environment/CargoStack"
WALL = "/Game/Generated/Environment/EstateWall"
ROADSIDE = "/Game/Generated/Environment/Roadside"


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
            "Project-owned OpenAI image-generation output and procedural PBR conversion; "
            "no external stock texture. Output ownership is assigned to the user under "
            "the OpenAI Terms of Use, subject to those terms."
            and [source.get("surface") for source in record.get("fur_sources", [])] ==
            ["fur_grey", "fur_white", "fur_charcoal"]
            and [group.get("name") for group in record.get("maps", [])] ==
            ["fur_grey", "fur_white", "fur_charcoal", "silk_indigo", "lacquer_oxblood", "neutral"]
            and len(record.get("material_slots", {})) == 23,
            "The Nyaakoto PBR source identity changed")
    for source in record["fur_sources"]:
        fur_name = source["surface"].split("_", 1)[1].capitalize()
        filename = f"Source/Nyaakoto_{fur_name}Fur_ImageGen_v1.png"
        path = source_file(art_root, filename)
        require(source.get("file") == filename
                and hashlib.sha256(path.read_bytes()).hexdigest() == source.get("sha256")
                and source.get("origin", "").startswith(
                    "Built-in OpenAI image_gen.imagegen, text-only prompt")
                and re.fullmatch(r"exec-[0-9a-f-]{36}", source.get("origin_output_id", "")) is not None
                and source.get("source_url") is None
                and len(source.get("prompt", "")) > 200
                and source.get("rights_url") == "https://openai.com/policies/row-terms-of-use/",
                f"Nyaakoto fur source provenance changed: {filename}")
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


def hero_katana_pbr_source(source_root):
    art_root = source_root / "Weapons/HeroKatana/PBR"
    record = read_manifest(art_root / "manifest.json")
    require(record.get("schema_version") == 1
            and record.get("generator") == "scripts/art/create_hero_katana_pbr_textures.py"
            and record.get("license") ==
            "Original project-owned procedural surface maps; no third-party texture data"
            and [group.get("name") for group in record.get("maps", [])] ==
            ["forged_steel", "patinated_metal", "woven_silk", "ray_skin", "urushi", "neutral"]
            and len(record.get("material_slots", {})) == 12,
            "The hero katana PBR source identity changed")
    groups = {group["name"]: group for group in record["maps"]}
    for name, group in groups.items():
        require(group.get("resolution") == ([4, 4] if name == "neutral" else [2048, 2048])
                and [item.get("channel") for item in group.get("maps", [])] ==
                ["Albedo", "NormalDX", "ORM"],
                f"Hero katana PBR texture channels changed: {name}")
        for item in group["maps"]:
            filename = f"T_HeroKatana_{name}_{item['channel']}.png"
            require(item.get("file") == filename,
                    f"Hero katana PBR texture identity changed: {name}")
            path = source_file(art_root, filename)
            data = path.read_bytes()
            require(hashlib.sha256(data).hexdigest() == item.get("sha256")
                    and data[:16] == b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR",
                    f"Hero katana PBR source map changed: {path}")
    for slot, values in record["material_slots"].items():
        require(re.fullmatch(r"M_HK_[A-Za-z0-9_]+", slot) is not None
                and values.get("surface") in groups
                and len(values.get("tint", [])) == 3
                and all(0 <= value <= 1 for value in values["tint"])
                and 0 < values.get("roughness_scale", 0) <= 2
                and 0 <= values.get("metallic_scale", -1) <= 1,
                f"Hero katana PBR material slot changed: {slot}")
    return record


def torii_lacquer_source(source_root):
    art_root = source_root / "Environment/ToriiLacquer"
    record = read_manifest(art_root / "manifest.json")
    require(record.get("schema_version") == 1
            and record.get("generator") == "scripts/art/create_torii_lacquer_pbr.py"
            and record.get("material_slot") == "M_Env_VermilionLacquer"
            and record.get("unreal_instance") ==
            f"{PALETTE}/MI_Nyaagyu_ToriiLacquer.MI_Nyaagyu_ToriiLacquer"
            and record.get("tile_size_cm") == 120.0
            and record.get("license") ==
            "Original project-owned procedural texture; no third-party input image"
            and set(record.get("maps", {})) == {"Albedo", "NormalDX", "ORM"},
            "The original torii lacquer source identity changed")
    for channel, entry in record["maps"].items():
        file = source_file(art_root, entry["file"])
        require(file.name == f"T_Nyaagyu_ToriiLacquer_{channel}.png"
                and entry.get("resolution") == [2048, 2048]
                and hashlib.sha256(file.read_bytes()).hexdigest() == entry["sha256"],
                f"The torii lacquer {channel} source changed")
    return record


def cargo_stack_source(project_root, source_root):
    art_root = source_root / "Environment/NyaagyuCargoStack"
    record = read_manifest(art_root / "manifest.json")
    pbr_path = source_file(art_root, "PBR/manifest.json")
    pbr = read_manifest(pbr_path)
    require(record.get("schema_version") == 1
            and record.get("name") == "SM_Nyaagyu_CargoStack"
            and record.get("generator") == "scripts/art/create_nyaagyu_cargo_stack.py"
            and record.get("unreal_asset") ==
            f"{PROPS}/SM_Nyaagyu_CargoStack.SM_Nyaagyu_CargoStack"
            and record.get("collision_envelope_m") == [2.3, 1.8, 1.4]
            and record.get("collision", "").startswith("Visual only")
            and record.get("pbr_manifest_sha256") ==
            hashlib.sha256(pbr_path.read_bytes()).hexdigest()
            and pbr.get("schema_version") == 1
            and pbr.get("generator") == "scripts/art/create_nyaagyu_cargo_pbr.py"
            and pbr.get("origin") ==
            "Original project-authored deterministic procedural pixels; no external texture inputs"
            and [group.get("name") for group in pbr.get("sets", [])] ==
            ["Wood", "Straw", "IndigoCloth"],
            "The authored cargo stack or PBR provenance changed")
    fbx = source_file(art_root, record["fbx"])
    require(hashlib.sha256(fbx.read_bytes()).hexdigest() == record["fbx_sha256"],
            "The authored cargo mesh changed")
    logo = (art_root / record["insignia_source"]).resolve()
    require(logo.is_relative_to(source_root.resolve())
            and logo.is_file()
            and hashlib.sha256(logo.read_bytes()).hexdigest() ==
            record["insignia_sha256"]
            and len(record.get("exact_sora_kamon_objects", [])) == 2,
            "Cargo kamon must use the exact supplied SORA SVG")
    lower = record.get("bounds_m", {}).get("min", [-9, -9, -1])
    upper = record.get("bounds_m", {}).get("max", [9, 9, 9])
    require(len(lower) == len(upper) == 3
            and lower[0] >= -1.15 and upper[0] <= 1.15
            and lower[1] >= -0.9 and upper[1] <= 0.9
            and lower[2] >= 0 and upper[2] <= 1.4
            and record.get("source_triangles", 0) >= 20_000,
            "Cargo art escaped the retained combat cover volume")
    expected_slots = {"M_Cargo_AgedTimber", "M_Cargo_BlackIron", "M_Cargo_DarkInterior",
                      "M_Cargo_HempRope", "M_Cargo_IndigoCloth", "M_Cargo_SORA_Red",
                      "M_Cargo_StrawWrap", "M_Cargo_WornEdge"}
    require(set(record.get("material_slots", [])) == expected_slots
            and set(pbr.get("material_slots", {})) ==
            expected_slots - {"M_Cargo_BlackIron", "M_Cargo_SORA_Red"},
            "Cargo FBX material slots changed")
    generator = source_file(project_root, pbr["generator"])
    require(hashlib.sha256(generator.read_bytes()).hexdigest() == pbr["generator_sha256"],
            "Cargo procedural texture generator changed")
    for group in pbr["sets"]:
        require(group.get("resolution") == [2048, 2048]
                and [item.get("channel") for item in group.get("maps", [])] ==
                ["Albedo", "NormalDX", "ORM"],
                f"Cargo {group.get('name')} PBR set is incomplete")
        for item in group["maps"]:
            path = source_file(art_root / "PBR", item["file"])
            require(hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"],
                    f"Cargo PBR map changed: {path}")
    return record, pbr


def estate_wall_source(project_root, source_root):
    art_root = source_root / "Environment/NyaagyuEstateWall"
    record = read_manifest(art_root / "manifest.json")
    name = "SM_Nyaagyu_EstateWall_4m"
    expected_slots = {"M_Wall_CharredTimber", "M_Wall_EarthenScar", "M_Wall_Kawara",
                      "M_Wall_LimePlaster", "M_Wall_StoneDark", "M_Wall_StoneFoundation"}
    require(record.get("schema_version") == 1 and record.get("name") == name
            and record.get("generator") == "scripts/art/create_nyaagyu_estate_wall.py"
            and record.get("unreal_asset") == f"{PROPS}/{name}.{name}"
            and record.get("module_length_m") == 4.0
            and record.get("collision_envelope_m") == [1.0, 4.0, 5.4]
            and record.get("collision", "").startswith("Visual-only")
            and record.get("nanite_windows") is True
            and record.get("mac_conventional_fallback", {}).get(
                "fallback_percent_triangles") == 1.0
            and set(record.get("material_slots", [])) == expected_slots
            and set(record.get("slot_definitions", {})) == expected_slots
            and set(record.get("dependencies", {})) == {"Stone", "Plaster", "Timber", "Kawara"},
            "Estate perimeter wall identity or collision policy changed")
    for key, digest in (("fbx", "fbx_sha256"), ("source_blend", "blend_sha256")):
        path = source_file(art_root, record[key])
        require(hashlib.sha256(path.read_bytes()).hexdigest() == record[digest],
                f"Estate wall source changed: {path}")
    generator = source_file(project_root, record["generator"])
    require(hashlib.sha256(generator.read_bytes()).hexdigest() == record["generator_sha256"],
            "Estate wall geometry generator changed")
    scan_manifest = source_file(art_root, "ScanRock01/manifest.json")
    require(hashlib.sha256(scan_manifest.read_bytes()).hexdigest() ==
            record["scan_manifest_sha256"], "Estate wall rock scan provenance changed")
    lower = record["bounds_m"]["min"]
    upper = record["bounds_m"]["max"]
    require(len(lower) == len(upper) == 3
            and lower[0] >= -0.5 and upper[0] <= 0.5
            and lower[1] >= -2 and upper[1] <= 2
            and lower[2] >= -2.7 and upper[2] <= 2.7
            and record.get("source_triangles", 0) >= 10_000,
            "Estate wall visual escaped the retained collision envelope")
    for surface, dependency in record["dependencies"].items():
        require(dependency.get("license") == "CC0-1.0"
                and dependency.get("source_url", "").startswith("https://polyhaven.com/a/")
                and set(dependency.get("files", {})) == {"Albedo", "NormalDX", "ORM"},
                f"Estate wall scan provenance changed: {surface}")
        for channel, file in dependency["files"].items():
            path = source_file(project_root, file["repo_path"])
            require(hashlib.sha256(path.read_bytes()).hexdigest() == file["sha256"],
                    f"Estate wall {surface} {channel} scan changed")
    return record


def roadside_source(project_root, source_root):
    art_root = source_root / "Environment/NyaagyuGroundDressing"
    record = read_manifest(art_root / "manifest.json")
    name = "SM_Nyaagyu_RoadsideLeafSilt_4m"
    slots = {"M_Ground_DampSilt", "M_Ground_LeafOchre", "M_Ground_LeafUmber",
             "M_Ground_Moss", "M_Ground_RiverStone", "M_Ground_WetStone"}
    require(record.get("schema_version") == 1 and record.get("name") == name
            and record.get("generator") == "scripts/art/create_nyaagyu_ground_dressing.py"
            and record.get("unreal_asset") == f"{PROPS}/{name}.{name}"
            and record.get("nominal_road_length_m") == 4.0
            and record.get("collision", "").startswith("Visual only")
            and record.get("nanite_windows") is True
            and record.get("mac_conventional_fallback", {}).get(
                "fallback_percent_triangles") == 1.0
            and set(record.get("material_slots", [])) == slots
            and set(record.get("slot_definitions", {})) == slots
            and set(record.get("dependencies", {})) ==
            {"DampSilt", "ForestLitter", "RiverStone"},
            "Roadside ground-dressing identity or collision policy changed")
    for key, digest in (("fbx", "fbx_sha256"), ("source_blend", "blend_sha256"),
                        ("review", "review_sha256"),
                        ("scatter_review", "scatter_review_sha256")):
        path = source_file(art_root, record[key])
        require(hashlib.sha256(path.read_bytes()).hexdigest() == record[digest],
                f"Roadside source changed: {path}")
    generator = source_file(project_root, record["generator"])
    require(hashlib.sha256(generator.read_bytes()).hexdigest() == record["generator_sha256"],
            "Roadside geometry generator changed")
    scan = source_file(art_root, "ScanForestLeaves02/manifest.json")
    require(hashlib.sha256(scan.read_bytes()).hexdigest() ==
            record["new_scan_manifest_sha256"], "Roadside forest scan provenance changed")
    lower = record["bounds_m"]["min"]
    upper = record["bounds_m"]["max"]
    require(len(lower) == len(upper) == 3
            and lower[0] >= -2.2 and upper[0] <= 2.2
            and lower[1] >= -1.3 and upper[1] <= 1.3
            and lower[2] >= -.02 and upper[2] <= .2
            and record.get("source_triangles", 0) >= 12_000,
            "Roadside dressing escaped its shallow four-metre footprint")
    for surface, dependency in record["dependencies"].items():
        require(dependency.get("license") == "CC0-1.0"
                and dependency.get("source_url", "").startswith("https://polyhaven.com/a/")
                and set(dependency.get("files", {})) == {"Albedo", "NormalDX", "ORM"},
                f"Roadside {surface} scan provenance changed")
        for channel, file in dependency["files"].items():
            path = source_file(project_root, file["repo_path"])
            require(hashlib.sha256(path.read_bytes()).hexdigest() == file["sha256"],
                    f"Roadside {surface} {channel} scan changed")
    return record


def validate_hero_katana_loaded(unreal, asset_library):
    record = hero_katana_pbr_source(Path(unreal.Paths.project_dir()).resolve() / "Content/SourceArt")
    material_lib = unreal.MaterialEditingLibrary
    master_path = f"{HERO_KATANA}/M_HeroKatana_PBR.M_HeroKatana_PBR"
    master = asset_library.load_asset(master_path)
    require({str(name) for name in material_lib.get_texture_parameter_names(master)} ==
            {"AlbedoMap", "NormalMap", "ORMMap"},
            "Hero katana PBR master lost a texture parameter")
    for group in record["maps"]:
        for item in group["maps"]:
            name = Path(item["file"]).stem
            texture = asset_library.load_asset(f"{HERO_KATANA}/Textures/{name}.{name}")
            require(bool(texture.get_editor_property("srgb")) == (item["channel"] == "Albedo"),
                    f"Hero katana texture color space changed: {name}")
            if item["channel"] == "NormalDX":
                require(texture.get_editor_property("compression_settings") ==
                        unreal.TextureCompressionSettings.TC_NORMALMAP
                        and not bool(texture.get_editor_property("flip_green_channel")),
                        f"Hero katana tangent normal import changed: {name}")
            elif item["channel"] == "ORM":
                require(texture.get_editor_property("compression_settings") ==
                        unreal.TextureCompressionSettings.TC_MASKS,
                        f"Hero katana ORM compression changed: {name}")
    instances = {}
    for slot, surface in record["material_slots"].items():
        name = "MI_HK_" + slot.removeprefix("M_HK_")
        path = f"{HERO_KATANA}/{name}.{name}"
        instance = asset_library.load_asset(path)
        parent = instance.get_editor_property("parent")
        require(parent is not None and parent.get_path_name() == master_path,
                f"Hero katana instance has the wrong PBR parent: {path}")
        for parameter, channel in (("AlbedoMap", "Albedo"),
                                   ("NormalMap", "NormalDX"), ("ORMMap", "ORM")):
            texture_name = f"T_HeroKatana_{surface['surface']}_{channel}"
            expected = f"{HERO_KATANA}/Textures/{texture_name}.{texture_name}"
            actual = material_lib.get_material_instance_texture_parameter_value(instance, parameter)
            require(actual is not None and actual.get_path_name() == expected,
                    f"Hero katana material lost its {parameter}: {name}")
        for parameter, value in (("RoughnessScale", surface["roughness_scale"]),
                                 ("MetallicScale", surface["metallic_scale"])):
            actual = material_lib.get_material_instance_scalar_parameter_value(instance, parameter)
            require(abs(actual - value) < 1e-5,
                    f"Hero katana material changed its {parameter}: {name}")
        tint = material_lib.get_material_instance_vector_parameter_value(instance, "Tint")
        require(all(abs(getattr(tint, channel) - value) < 1e-5
                    for channel, value in zip("rgb", surface["tint"])),
                f"Hero katana material changed its tint: {name}")
        instances[slot] = instance
    bound = set()
    for mesh_name, expected_count in (("SM_Nyaagyu_HeroKatana", 9),
                                      ("SM_Nyaagyu_HeroSaya", 4)):
        mesh = asset_library.load_asset(f"{MESHES}/{mesh_name}.{mesh_name}")
        slots = mesh.get_editor_property("static_materials")
        require(len(slots) == expected_count,
                f"Hero katana/saya slot count changed: {mesh_name}")
        local = set()
        for slot in slots:
            name = str(slot.get_editor_property("material_slot_name"))
            material = slot.get_editor_property("material_interface")
            require(name in instances and name not in local and material is not None
                    and material.get_path_name() == instances[name].get_path_name(),
                    f"Hero katana/saya PBR binding changed: {mesh_name} {name}")
            local.add(name)
        bound.update(local)
    require(bound == set(instances), "A hero katana/saya material is not bound to an imported mesh")


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


def nyaakoto_iris_source(source_root):
    """Resolve the one painted iris map from Nyaakoto's hashed source art."""
    hero_root = source_root / "Characters/Hero"
    record = read_manifest(hero_root / "manifest.json")
    entries = record.get("generated_textures", [])
    require(record.get("schema_version") == 2
            and len(entries) == 1
            and entries[0].get("path") == "EyeStudy/T_Nyaakoto_Iris_Albedo.png",
            "The Nyaakoto painted iris identity changed")
    path = source_file(hero_root, entries[0]["path"])
    data = path.read_bytes()
    require(hashlib.sha256(data).hexdigest() == entries[0].get("sha256")
            and data[:16] == b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
            and tuple(int.from_bytes(data[offset:offset + 4], "big")
                      for offset in (16, 20)) == (1024, 1024),
            "The Nyaakoto painted iris source changed")
    return path.stem


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
            and hero.get("fbx") == "SM_Nyaagyu_HeroKatana.fbx"
            and hero.get("saya_name") == "SM_Nyaagyu_HeroSaya"
            and hero.get("saya_fbx") == "SM_Nyaagyu_HeroSaya.fbx",
            "The hero katana identity changed")
    for filename, digest in ((hero["fbx"], hero["fbx_sha256"]),
                             (hero["saya_fbx"], hero["saya_fbx_sha256"])):
        path = source_file(source_root, filename)
        require(hashlib.sha256(path.read_bytes()).hexdigest() == digest,
                f"The katana or saya FBX source changed: {filename}")

    specs = {}
    for name in characters + weapons + [hero["name"], hero["saya_name"]]:
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
    iris_name = nyaakoto_iris_source(source_root)
    require(pbr["material_slots"]["M_Hero_BlueEye"]["tint"] == [1, 1, 1],
            "The painted iris must retain its neutral Unreal tint")
    add(specs, f"{NYAAKOTO}/Textures/{iris_name}.{iris_name}", "Texture2D")
    add(specs, f"{NYAAKOTO}/M_Nyaakoto_PBR.M_Nyaakoto_PBR", "Material")
    for slot in pbr["material_slots"]:
        name = "MI_Nyaakoto_" + slot.removeprefix("M_Hero_")
        add(specs, f"{NYAAKOTO}/{name}.{name}", "MaterialInstanceConstant")

    katana_pbr = hero_katana_pbr_source(source_root)
    for group in katana_pbr["maps"]:
        for item in group["maps"]:
            name = Path(item["file"]).stem
            add(specs, f"{HERO_KATANA}/Textures/{name}.{name}", "Texture2D")
    add(specs, f"{HERO_KATANA}/M_HeroKatana_PBR.M_HeroKatana_PBR", "Material")
    for slot in katana_pbr["material_slots"]:
        name = "MI_HK_" + slot.removeprefix("M_HK_")
        add(specs, f"{HERO_KATANA}/{name}.{name}", "MaterialInstanceConstant")

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
    cargo, cargo_pbr = cargo_stack_source(project_root, source_root)
    add(specs, cargo["unreal_asset"], "StaticMesh")
    for group in cargo_pbr["sets"]:
        for item in group["maps"]:
            name = Path(item["file"]).stem
            add(specs, f"{CARGO}/Textures/{name}.{name}", "Texture2D")
    for name in ("M_NyaagyuCargo_PBR", "M_NyaagyuCargo_FlatPBR"):
        add(specs, f"{CARGO}/{name}.{name}", "Material")
    for slot in cargo["material_slots"]:
        name = "MI_NyaagyuCargo_" + slot.removeprefix("M_Cargo_")
        add(specs, f"{CARGO}/{name}.{name}", "MaterialInstanceConstant")
    wall = estate_wall_source(project_root, source_root)
    add(specs, wall["unreal_asset"], "StaticMesh")
    for surface in wall["dependencies"]:
        for channel in ("Albedo", "NormalDX", "ORM"):
            name = f"T_EstateWall_{surface}_{channel}"
            add(specs, f"{WALL}/Textures/{name}.{name}", "Texture2D")
    add(specs, f"{WALL}/M_NyaagyuEstateWall_PBR.M_NyaagyuEstateWall_PBR", "Material")
    for slot in wall["material_slots"]:
        name = "MI_NyaagyuEstateWall_" + slot.removeprefix("M_Wall_")
        add(specs, f"{WALL}/{name}.{name}", "MaterialInstanceConstant")
    roadside = roadside_source(project_root, source_root)
    add(specs, roadside["unreal_asset"], "StaticMesh")
    for surface in roadside["dependencies"]:
        for channel in ("Albedo", "NormalDX", "ORM"):
            name = f"T_Roadside_{surface}_{channel}"
            add(specs, f"{ROADSIDE}/Textures/{name}.{name}", "Texture2D")
    for name in ("M_NyaagyuRoadside_OpaquePBR", "M_NyaagyuRoadside_FeatheredPBR"):
        add(specs, f"{ROADSIDE}/{name}.{name}", "Material")
    for slot in roadside["material_slots"]:
        name = "MI_NyaagyuRoadside_" + slot.removeprefix("M_Ground_")
        add(specs, f"{ROADSIDE}/{name}.{name}", "MaterialInstanceConstant")
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
            and terrain.get("macro_tint", {}).get("vertex_color_attribute") == "EstateMacroTint"
            and len(terrain.get("tiles", [])) == 32,
            "The modular estate terrain identity changed")
    require([(item.get("role"), item.get("channel"))
             for item in terrain.get("palette_files", [])] ==
            [("soil", "diffuse"), ("soil", "normal"), ("soil", "arm")],
            "The estate soil palette source changed")
    for item in terrain["palette_files"]:
        source = source_file(project_root, item["path"])
        require(hashlib.sha256(source.read_bytes()).hexdigest() == item["sha256"],
                f"Estate terrain palette source changed: {source}")
    pathway = terrain.get("stone_pathway_scan", {})
    require(pathway.get("asset_id") == "grey_stone_path"
            and pathway.get("source_url") == "https://polyhaven.com/a/grey_stone_path"
            and pathway.get("license") == "CC0-1.0"
            and pathway.get("tile_size_cm") == 180
            and [entry.get("channel") for entry in pathway.get("files", [])] ==
            ["Diffuse", "nor_dx", "arm", "disp"],
            "Estate terrain-only stone scan identity changed")
    for entry in pathway["files"]:
        scan_file = source_file(terrain_root, entry["file"])
        require(hashlib.sha256(scan_file.read_bytes()).hexdigest() == entry.get("sha256"),
                f"Estate terrain-only stone scan changed: {scan_file}")
        name = "T_TerrainGreyStonePath_" + entry["channel"]
        add(specs, f"{PALETTE}/Textures/{name}.{name}", "Texture2D")
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
    for role in ("Soil", "Stone"):
        name = f"MI_Nyaagyu_Terrain{role}"
        add(specs, f"{PALETTE}/{name}.{name}", "MaterialInstanceConstant")

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

    pine_root = source_root / "Environment/PolyHaven/PineSaplingSmall"
    pine = read_manifest(pine_root / "manifest.json")
    require(pine.get("schema_version") == 1
            and pine.get("asset_id") == "pine_sapling_small"
            and pine.get("upstream_page") == "https://polyhaven.com/a/pine_sapling_small"
            and pine.get("license") == "CC0-1.0; https://polyhaven.com/license"
            and pine.get("generator") == "scripts/art/create_nyaagyu_pine_saplings.py"
            and pine.get("material_slots") == ["M_NyaagyuPine_Bark", "M_NyaagyuPine_Needles"]
            and pine.get("gameplay_collision") is False
            and pine.get("instances_in_nyaagyu_estate") == 9
            and len(pine.get("upstream_files", [])) == 8
            and len(pine.get("texture_files", [])) == 8
            and len(pine.get("meshes", [])) == 6,
            "The pinned Nyaagyu CC0 pine identity changed")
    for file in pine["upstream_files"] + pine["texture_files"]:
        path = source_file(pine_root, file["path"])
        require(path.stat().st_size == file["bytes"]
                and hashlib.sha256(path.read_bytes()).hexdigest() == file["sha256"],
                f"Pinned pine source changed: {path}")
    for name, key in ((pine["source_blend"], "source_blend_sha256"),
                      (pine["preview"], "preview_sha256")):
        path = source_file(pine_root, name)
        require(hashlib.sha256(path.read_bytes()).hexdigest() == pine[key],
                f"Nyaagyu pine source review changed: {path}")
    for variant in "abc":
        for tier in ("hi", "mac"):
            matches = [item for item in pine["meshes"]
                       if item.get("variant") == variant and item.get("tier") == tier]
            require(len(matches) == 1, f"Missing or duplicate pine {variant}/{tier} tier")
            record = matches[0]
            name = f"SM_NyaagyuPine_{variant.upper()}_{tier.upper()}"
            require(record.get("name") == name and record.get("fbx") == name + ".fbx"
                    and record.get("unreal_asset") == f"{FOLIAGE}/{name}.{name}"
                    and record.get("nanite") == (tier == "hi")
                    and record.get("material_slots") == pine["material_slots"]
                    and record.get("source_triangles", 0) > (70000 if tier == "hi" else 20000),
                    f"The Nyaagyu pine {variant}/{tier} mesh identity changed")
            file = source_file(pine_root, record["fbx"])
            require(hashlib.sha256(file.read_bytes()).hexdigest() == record["fbx_sha256"],
                    f"Nyaagyu pine FBX changed: {file}")
            add(specs, record["unreal_asset"], "StaticMesh")
    for role in ("Bark", "Needles"):
        name = f"M_NyaagyuPine_{role}"
        add(specs, f"{FOLIAGE}/{name}.{name}", "Material")
    for file in pine["texture_files"]:
        channel = Path(file["path"]).stem.removeprefix("pine_sapling_small_").removesuffix("_2k")
        name = f"T_NyaagyuPine_{channel}"
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
    torii = torii_lacquer_source(source_root)
    for item in torii["maps"].values():
        name = Path(item["file"]).stem
        add(specs, f"{PALETTE}/Textures/{name}.{name}", "Texture2D")
    add(specs, torii["unreal_instance"], "MaterialInstanceConstant")
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
    validate_hero_katana_loaded(unreal, asset_library)
    pbr = nyaakoto_pbr_source(Path(unreal.Paths.project_dir()).resolve() / "Content/SourceArt")
    iris_name = nyaakoto_iris_source(Path(unreal.Paths.project_dir()).resolve() / "Content/SourceArt")
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
    require(bool(master.get_editor_property("used_with_skeletal_mesh")),
            "Nyaakoto PBR master must compile a skeletal-mesh shader permutation")
    require({str(name) for name in material_lib.get_texture_parameter_names(master)} ==
            {"AlbedoMap", "NormalMap", "ORMMap", "WhiteFurAlbedoMap",
             "WhiteFurNormalMap", "WhiteFurORMMap"},
            "Nyaakoto PBR master lost a coat-blend texture parameter")
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
    iris_path = f"{NYAAKOTO}/Textures/{iris_name}.{iris_name}"
    iris_texture = asset_library.load_asset(iris_path)
    require(bool(iris_texture.get_editor_property("srgb"))
            and iris_texture.get_editor_property("max_texture_size") == 1024,
            "Nyaakoto painted iris color space or size changed")
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
            if slot == "M_Hero_BlueEye" and parameter == "AlbedoMap":
                expected_path = iris_path
            bound = material_lib.get_material_instance_texture_parameter_value(instance, parameter)
            require(bound is not None and bound.get_path_name() == expected_path,
                    f"Nyaakoto material {name} lost its {parameter} map binding")
        coat_enabled = float(slot == "M_Hero_GreyTabbyFur")
        actual_coat_enabled = material_lib.get_material_instance_scalar_parameter_value(
            instance, "CoatBlendEnabled")
        require(abs(actual_coat_enabled - coat_enabled) < 1e-5,
                f"Nyaakoto material {name} changed its coat-mask selector")
        if coat_enabled:
            for parameter, channel in (("WhiteFurAlbedoMap", "Albedo"),
                                       ("WhiteFurNormalMap", "NormalDX"),
                                       ("WhiteFurORMMap", "ORM")):
                texture_name = f"T_Nyaakoto_fur_white_{channel}"
                expected_path = f"{NYAAKOTO}/Textures/{texture_name}.{texture_name}"
                bound = material_lib.get_material_instance_texture_parameter_value(
                    instance, parameter)
                require(bound is not None and bound.get_path_name() == expected_path,
                        f"Nyaakoto material {name} lost its {parameter} coat map")
            expected_tint = pbr["material_slots"]["M_Hero_WhiteFur"]["tint"]
            white_tint = material_lib.get_material_instance_vector_parameter_value(
                instance, "WhiteFurTint")
            require(all(abs(getattr(white_tint, channel) - value) < 1e-5
                        for channel, value in zip("rgb", expected_tint)),
                    "Nyaakoto grey-fur instance changed its white-coat tint")
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
    torii = torii_lacquer_source(Path(unreal.Paths.project_dir()).resolve() / "Content/SourceArt")
    lacquer = asset_library.load_asset(torii["unreal_instance"])
    parent = lacquer.get_editor_property("parent")
    require(parent is not None and parent.get_path_name() == base_path,
            "Torii lacquer lost the world-aligned PBR master")
    for parameter, channel in (("AlbedoMap", "Albedo"),
                               ("NormalMap", "NormalDX"), ("ARMMap", "ORM")):
        name = Path(torii["maps"][channel]["file"]).stem
        expected = f"{PALETTE}/Textures/{name}.{name}"
        texture = asset_library.load_asset(expected)
        actual = material_lib.get_material_instance_texture_parameter_value(lacquer, parameter)
        require(actual is not None and actual.get_path_name() == expected,
                f"Torii lacquer lost its {parameter} source map")
        require(bool(texture.get_editor_property("srgb")) == (channel == "Albedo"),
                f"Torii lacquer {channel} color-space import changed")
        if channel == "NormalDX":
            require(texture.get_editor_property("compression_settings") ==
                    unreal.TextureCompressionSettings.TC_NORMALMAP
                    and not bool(texture.get_editor_property("flip_green_channel")),
                    "Torii lacquer DirectX normal import changed")
        if channel == "ORM":
            require(texture.get_editor_property("compression_settings") ==
                    unreal.TextureCompressionSettings.TC_MASKS,
                    "Torii lacquer ORM compression changed")
    lacquer_tile = material_lib.get_material_instance_vector_parameter_value(lacquer, "TileSize")
    require(all(abs(getattr(lacquer_tile, channel) - 120.0) < 1e-5 for channel in "rgb"),
            "Torii lacquer lost its 120 cm world projection")
    gate = asset_library.load_asset(f"{PROPS}/SM_Nyaagyu_ToriiGate.SM_Nyaagyu_ToriiGate")
    bound = [slot.get_editor_property("material_interface") for slot in gate.get_editor_property("static_materials")
             if str(slot.get_editor_property("material_slot_name")) == torii["material_slot"]]
    require(len(bound) == 1 and bound[0] is not None
            and bound[0].get_path_name() == torii["unreal_instance"],
            "Torii lacquer is not bound to the imported gate slot")
    cargo, cargo_pbr = cargo_stack_source(
        Path(unreal.Paths.project_dir()).resolve(),
        Path(unreal.Paths.project_dir()).resolve() / "Content/SourceArt")
    cargo_mesh = asset_library.load_asset(cargo["unreal_asset"])
    require(bool(cargo_mesh.get_editor_property("nanite_settings").get_editor_property("enabled")),
            "Cargo art lost its Windows Nanite data")
    cargo_slots = cargo_mesh.get_editor_property("static_materials")
    require({str(slot.get_editor_property("material_slot_name")) for slot in cargo_slots} ==
            set(cargo["material_slots"]),
            "Cargo FBX material zones disappeared")
    for slot in cargo_slots:
        slot_name = str(slot.get_editor_property("material_slot_name"))
        name = "MI_NyaagyuCargo_" + slot_name.removeprefix("M_Cargo_")
        instance_path = f"{CARGO}/{name}.{name}"
        bound = slot.get_editor_property("material_interface")
        require(bound is not None and bound.get_path_name() == instance_path,
                f"Cargo mesh lost material {slot_name}")
        instance = asset_library.load_asset(instance_path)
        textured = slot_name in cargo_pbr["material_slots"]
        parent_name = "M_NyaagyuCargo_PBR" if textured else "M_NyaagyuCargo_FlatPBR"
        parent = instance.get_editor_property("parent")
        require(parent is not None and parent.get_path_name() ==
                f"{CARGO}/{parent_name}.{parent_name}",
                f"Cargo {slot_name} material parent changed")
        if textured:
            surface = cargo_pbr["material_slots"][slot_name]["surface"]
            for parameter, channel in (("AlbedoMap", "Albedo"),
                                       ("NormalMap", "NormalDX"), ("ORMMap", "ORM")):
                texture_name = f"T_NyaagyuCargo_{surface}_{channel}"
                texture_path = f"{CARGO}/Textures/{texture_name}.{texture_name}"
                texture = asset_library.load_asset(texture_path)
                actual = material_lib.get_material_instance_texture_parameter_value(instance, parameter)
                require(actual is not None and actual.get_path_name() == texture_path,
                        f"Cargo {slot_name} lost {parameter}")
                require(bool(texture.get_editor_property("srgb")) == (channel == "Albedo"),
                        f"Cargo {surface} {channel} color space changed")
                if channel == "NormalDX":
                    require(texture.get_editor_property("compression_settings") ==
                            unreal.TextureCompressionSettings.TC_NORMALMAP
                            and not bool(texture.get_editor_property("flip_green_channel")),
                            f"Cargo {surface} DirectX normal settings changed")
                if channel == "ORM":
                    require(texture.get_editor_property("compression_settings") ==
                            unreal.TextureCompressionSettings.TC_MASKS,
                            f"Cargo {surface} ORM compression changed")
    wall = estate_wall_source(
        Path(unreal.Paths.project_dir()).resolve(),
        Path(unreal.Paths.project_dir()).resolve() / "Content/SourceArt")
    wall_mesh = asset_library.load_asset(wall["unreal_asset"])
    settings = wall_mesh.get_editor_property("nanite_settings")
    require(bool(settings.get_editor_property("enabled"))
            and settings.get_editor_property("fallback_percent_triangles") >= .999
            and settings.get_editor_property("fallback_target") ==
            unreal.NaniteFallbackTarget.PERCENT_TRIANGLES
            and settings.get_editor_property("generate_fallback") ==
            unreal.NaniteGenerateFallback.ENABLED,
            "Estate wall lost its Nanite data or full Mac fallback")
    wall_slots = wall_mesh.get_editor_property("static_materials")
    require({str(item.get_editor_property("material_slot_name")) for item in wall_slots} ==
            set(wall["material_slots"]), "Estate wall FBX material zones disappeared")
    master_path = f"{WALL}/M_NyaagyuEstateWall_PBR.M_NyaagyuEstateWall_PBR"
    for item in wall_slots:
        slot = str(item.get_editor_property("material_slot_name"))
        name = "MI_NyaagyuEstateWall_" + slot.removeprefix("M_Wall_")
        instance_path = f"{WALL}/{name}.{name}"
        bound = item.get_editor_property("material_interface")
        require(bound is not None and bound.get_path_name() == instance_path,
                f"Estate wall mesh lost material {slot}")
        instance = asset_library.load_asset(instance_path)
        parent = instance.get_editor_property("parent")
        require(parent is not None and parent.get_path_name() == master_path,
                f"Estate wall {slot} PBR parent changed")
        surface = wall["slot_definitions"][slot]["source"]
        for parameter, channel in (("AlbedoMap", "Albedo"),
                                   ("NormalMap", "NormalDX"), ("ORMMap", "ORM")):
            texture_name = f"T_EstateWall_{surface}_{channel}"
            texture_path = f"{WALL}/Textures/{texture_name}.{texture_name}"
            texture = asset_library.load_asset(texture_path)
            actual = material_lib.get_material_instance_texture_parameter_value(instance, parameter)
            require(actual is not None and actual.get_path_name() == texture_path,
                    f"Estate wall {slot} lost {parameter}")
            require(bool(texture.get_editor_property("srgb")) == (channel == "Albedo"),
                    f"Estate wall {surface} {channel} color space changed")
            if channel == "NormalDX":
                require(texture.get_editor_property("compression_settings") ==
                        unreal.TextureCompressionSettings.TC_NORMALMAP
                        and not bool(texture.get_editor_property("flip_green_channel")),
                        f"Estate wall {surface} DirectX normal settings changed")
            if channel == "ORM":
                require(texture.get_editor_property("compression_settings") ==
                        unreal.TextureCompressionSettings.TC_MASKS,
                        f"Estate wall {surface} ORM compression changed")
    roadside = roadside_source(
        Path(unreal.Paths.project_dir()).resolve(),
        Path(unreal.Paths.project_dir()).resolve() / "Content/SourceArt")
    roadside_mesh = asset_library.load_asset(roadside["unreal_asset"])
    settings = roadside_mesh.get_editor_property("nanite_settings")
    require(bool(settings.get_editor_property("enabled"))
            and settings.get_editor_property("fallback_percent_triangles") >= .999
            and settings.get_editor_property("fallback_target") ==
            unreal.NaniteFallbackTarget.PERCENT_TRIANGLES
            and settings.get_editor_property("generate_fallback") ==
            unreal.NaniteGenerateFallback.ENABLED,
            "Roadside dressing lost Nanite data or full Mac fallback")
    roadside_slots = roadside_mesh.get_editor_property("static_materials")
    require({str(item.get_editor_property("material_slot_name")) for item in roadside_slots} ==
            set(roadside["material_slots"]), "Roadside material zones disappeared")
    feather_path = f"{ROADSIDE}/M_NyaagyuRoadside_FeatheredPBR.M_NyaagyuRoadside_FeatheredPBR"
    opaque_path = f"{ROADSIDE}/M_NyaagyuRoadside_OpaquePBR.M_NyaagyuRoadside_OpaquePBR"
    feather = asset_library.load_asset(feather_path)
    opaque = asset_library.load_asset(opaque_path)
    require(feather.get_editor_property("blend_mode") == unreal.BlendMode.BLEND_MASKED
            and opaque.get_editor_property("blend_mode") == unreal.BlendMode.BLEND_OPAQUE,
            "Roadside feathered/opaque material blending changed")
    for item in roadside_slots:
        slot = str(item.get_editor_property("material_slot_name"))
        name = "MI_NyaagyuRoadside_" + slot.removeprefix("M_Ground_")
        instance_path = f"{ROADSIDE}/{name}.{name}"
        bound = item.get_editor_property("material_interface")
        require(bound is not None and bound.get_path_name() == instance_path,
                f"Roadside mesh lost material {slot}")
        instance = asset_library.load_asset(instance_path)
        parent = instance.get_editor_property("parent")
        expect_parent = feather_path if slot in {"M_Ground_DampSilt", "M_Ground_Moss"} else opaque_path
        require(parent is not None and parent.get_path_name() == expect_parent,
                f"Roadside {slot} PBR parent changed")
        surface = roadside["slot_definitions"][slot]["source"]
        for parameter, channel in (("AlbedoMap", "Albedo"),
                                   ("NormalMap", "NormalDX"), ("ORMMap", "ORM")):
            texture_name = f"T_Roadside_{surface}_{channel}"
            texture_path = f"{ROADSIDE}/Textures/{texture_name}.{texture_name}"
            texture = asset_library.load_asset(texture_path)
            actual = material_lib.get_material_instance_texture_parameter_value(instance, parameter)
            require(actual is not None and actual.get_path_name() == texture_path,
                    f"Roadside {slot} lost {parameter}")
            require(bool(texture.get_editor_property("srgb")) == (channel == "Albedo"),
                    f"Roadside {surface} {channel} color space changed")
            if channel == "NormalDX":
                require(texture.get_editor_property("compression_settings") ==
                        unreal.TextureCompressionSettings.TC_NORMALMAP
                        and not bool(texture.get_editor_property("flip_green_channel")),
                        f"Roadside {surface} DirectX normal settings changed")
            if channel == "ORM":
                require(texture.get_editor_property("compression_settings") ==
                        unreal.TextureCompressionSettings.TC_MASKS,
                        f"Roadside {surface} ORM compression changed")
    for role in ("Soil", "Stone"):
        path = f"{PALETTE}/MI_Nyaagyu_Terrain{role}.MI_Nyaagyu_Terrain{role}"
        instance = asset_library.load_asset(path)
        parent = instance.get_editor_property("parent")
        require(parent is not None and parent.get_path_name() ==
                f"{PALETTE}/MI_Nyaagyu_{role}.MI_Nyaagyu_{role}"
                and abs(material_lib.get_material_instance_scalar_parameter_value(
                    instance, "TerrainVertexTint") - 1.0) < 1e-5,
                f"Estate terrain instance lost its vertex macro-tint binding: {path}")
        require(abs(material_lib.get_material_instance_scalar_parameter_value(
                    instance, "TerrainDampRoughness") - .30) < 1e-5,
                f"Estate terrain instance lost its vertex-alpha dampness binding: {path}")
    terrain_stone = asset_library.load_asset(
        f"{PALETTE}/MI_Nyaagyu_TerrainStone.MI_Nyaagyu_TerrainStone")
    for parameter, channel in (("AlbedoMap", "Diffuse"),
                               ("NormalMap", "nor_dx"), ("ARMMap", "arm")):
        expected = (f"{PALETTE}/Textures/T_TerrainGreyStonePath_{channel}."
                    f"T_TerrainGreyStonePath_{channel}")
        actual = material_lib.get_material_instance_texture_parameter_value(
            terrain_stone, parameter)
        require(actual is not None and actual.get_path_name() == expected,
                f"Estate terrain stone lost its dedicated {parameter} scan")
    for channel in ("Diffuse", "nor_dx", "arm", "disp"):
        name = "T_TerrainGreyStonePath_" + channel
        texture = asset_library.load_asset(f"{PALETTE}/Textures/{name}.{name}")
        require(bool(texture.get_editor_property("srgb")) == (channel == "Diffuse"),
                f"Estate pathway {channel} color space changed")
        if channel == "nor_dx":
            require(texture.get_editor_property("compression_settings") ==
                    unreal.TextureCompressionSettings.TC_NORMALMAP
                    and not bool(texture.get_editor_property("flip_green_channel")),
                    "Estate pathway DirectX normal settings changed")
        if channel == "arm":
            require(texture.get_editor_property("compression_settings") ==
                    unreal.TextureCompressionSettings.TC_MASKS,
                    "Estate pathway ARM texture settings changed")
    pathway_size = material_lib.get_material_instance_vector_parameter_value(
        terrain_stone, "TileSize")
    require(all(abs(getattr(pathway_size, channel) - 180.0) < 1e-5
                for channel in "rgb"),
            "Estate pathway projection lost its measured 1.8-metre scale")
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
                slots = sorted(str(entry.get_editor_property("material_slot_name"))
                               for entry in mesh.get_editor_property("static_materials"))
                expected_slots = (["M_Terrain_Soil_PolyHaven", "M_Terrain_Stone_PolyHaven"]
                                  if y in (1, 2) else ["M_Terrain_Soil_PolyHaven"])
                require(slots == expected_slots,
                        f"Estate stone-road material zone missing from imported tile: {path}: {slots}")
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
    for variant in "ABC":
        for tier in ("HI", "MAC"):
            name = f"SM_NyaagyuPine_{variant}_{tier}"
            mesh = asset_library.load_asset(f"{FOLIAGE}/{name}.{name}")
            require(bool(mesh.get_editor_property("nanite_settings").get_editor_property("enabled")) == (tier == "HI"),
                    f"Nyaagyu pine Nanite tier mismatch: {name}")
            slots = [str(item.get_editor_property("material_slot_name"))
                     for item in mesh.get_editor_property("static_materials")]
            require(sorted(slots) == ["M_NyaagyuPine_Bark", "M_NyaagyuPine_Needles"],
                    f"Nyaagyu pine material zones missing: {name}")
    needles = asset_library.load_asset(f"{FOLIAGE}/M_NyaagyuPine_Needles.M_NyaagyuPine_Needles")
    require(needles.get_editor_property("blend_mode") == unreal.BlendMode.BLEND_MASKED
            and bool(needles.get_editor_property("two_sided")),
            "Nyaagyu pine needles lost their two-sided cutout material")
    mask = asset_library.load_asset(
        f"{FOLIAGE}/Textures/T_NyaagyuPine_twig_mask.T_NyaagyuPine_twig_mask")
    require(mask.get_editor_property("compression_settings") == unreal.TextureCompressionSettings.TC_MASKS
            and not bool(mask.get_editor_property("srgb")),
            "Nyaagyu pine needle mask color space or compression changed")
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
