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


def named_mesh(source_root, specs, folder, manifest_name, expected_name, package):
    art_root = source_root / folder
    record = read_manifest(art_root / manifest_name)
    path = f"{package}/{expected_name}.{expected_name}"
    require(record.get("schema_version") == 1
            and record.get("name") == expected_name
            and record.get("fbx") == f"{expected_name}.fbx"
            and record.get("unreal_asset") == path,
            f"Unexpected original mesh identity: {art_root / manifest_name}")
    source_file(art_root, record["fbx"])
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
               "SM_Nyaagyu_HeroCharacter", "/Game/ArtReview/Characters")
    named_mesh(source_root, specs, "Weapons/MonofilamentNaginata", "manifest.json",
               "SM_Nyaagyu_MonofilamentNaginata", "/Game/ArtReview/Weapons")

    original = read_manifest(source_root / "Environment/Original/manifest.json")
    require(original.get("schema_version") == 1
            and [entry.get("name") for entry in original.get("assets", [])] ==
            ["SM_Edo_LanternPost", "SM_Nyaagyu_ToriiGate", "SM_Alien_DebtKiosk"],
            "The original environment prop manifest changed")
    for entry in original["assets"]:
        name = entry["name"]
        require(entry.get("fbx") == f"{name}.fbx", f"Invalid prop FBX: {name}")
        source_file(source_root / "Environment/Original", entry["fbx"])
        add(specs, f"{PROPS}/{name}.{name}", "StaticMesh")
    for folder, name in (
        ("StreetDebtTerminal", "SM_Alien_StreetDebtTerminal"),
        ("NyaagyuSluice", "SM_Nyaagyu_IrrigationSluice"),
        ("SilkFoundryLoom", "SM_SilkFoundry_LevyLoom"),
    ):
        named_mesh(source_root, specs, f"Environment/{folder}", "manifest.json",
                   name, PROPS)

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
