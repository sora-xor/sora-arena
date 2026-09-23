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
    base_path = f"{PALETTE}/M_Nyaagyu_PBR.M_Nyaagyu_PBR"
    for role in ("Timber", "Stone", "Soil", "Metal"):
        path = f"{PALETTE}/MI_Nyaagyu_{role}.MI_Nyaagyu_{role}"
        parent = asset_library.load_asset(path).get_editor_property("parent")
        require(parent is not None and parent.get_path_name() == base_path,
                f"Palette instance has the wrong PBR parent: {path}")
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
