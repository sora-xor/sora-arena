"""Validate authored offline content and actual source-asset readiness without UE."""
from pathlib import Path
import json
import hashlib
import math
import re
import struct

ROOT = Path(__file__).resolve().parents[2]
content = ROOT / "Content"
catalog = json.loads((content / "Data/catalog.json").read_text())
assert catalog["schema_version"] == 3
assert catalog["default_language"] == "ja" and catalog["english_subtitles_default"] is True
speakers = catalog["dialogue_speakers"]
speaker_ids = {speaker["id"] for speaker in speakers}
assert len(speakers) >= 2 and len(speaker_ids) == len(speakers)
assert catalog["hero"] == {"name_ja": "ニャーコト", "name_en": "Nyaakoto",
                            "katana_id": 0, "yumi_id": 18, "quiver_arrows": 12}
assert next(speaker for speaker in speakers if speaker["id"] == "samurai")["ja"] == catalog["hero"]["name_ja"]
for speaker in speakers:
    assert re.fullmatch(r"[a-z][a-z0-9_]*", speaker["id"])
    assert re.search(r"[\u3040-\u9fff]", speaker["ja"])
    assert speaker["en"].strip()
game_config = (ROOT / "Config/DefaultGame.ini").read_text()
assert "[Internationalization]\nCulture=ja" in game_config
assert "InternationalizationPreset=EFIGSCJK" in game_config
assert "!CulturesToStage=ClearArray" in game_config
assert set(re.findall(r"^\+CulturesToStage=(\S+)$", game_config, re.MULTILINE)) == {"ja", "en"}
from native_japanese_localization import validate_source, expected_meta, expected_resource, META, RESOURCE
validate_source()
assert META.read_bytes() == expected_meta()
assert RESOURCE.read_bytes() == expected_resource()
assert len(catalog["classes"]) == 6 and len(catalog["weapons"]) == 18
assert [arm["id"] for arm in catalog["campaign_weapons"]] == [18, 19, 20]
assert [(arm["name_en"], arm["kind"]) for arm in catalog["campaign_weapons"]] == [
    ("Yumi", "bow"), ("Yari", "melee"), ("Naginata", "melee")]
assert all(arm["class"] == 0 and arm["special"] is False and arm["blast_radius"] == 0
           for arm in catalog["campaign_weapons"])
assert catalog["campaign_weapons"][0]["projectile_speed"] > 0
assert all(arm["projectile_speed"] == 0 for arm in catalog["campaign_weapons"][1:])
assert len(catalog["chapters"]) == 8 and len(catalog["maps"]) == 4
assert [w["id"] for w in catalog["weapons"]] == list(range(18))
assert [c["id"] for c in catalog["classes"]] == list(range(6))
for c in catalog["classes"]:
    assert c["weapons"] == [2*c["id"],2*c["id"]+1,12+c["id"]]
    assert c["health"] > 0 and c["speed"] > 0
    assert re.search(r"[\u3040-\u9fff]",c["name"])
    assert all(catalog["weapons"][i]["class"] == c["id"] for i in c["weapons"])
for w in catalog["weapons"]:
    assert w["damage"] > 0 and w["cooldown"] > 0 and w["range"] > 0
    assert w["magazine"] > 0 and w["reload"] > 0
    assert w["special"] == (w["id"] >= 12)
    assert w["kind"] in ("melee","hitscan","explosive","healing")
    if w["kind"] == "explosive": assert w["blast_radius"] > 0 and w["projectile_speed"] > 0
site_kinds = {"training", "debt_seal", "irrigation", "workshop", "foundry", "ledger", "power", "supplies"}
for chapter in catalog["chapters"]:
    assert 0 <= chapter["map"] < 4 and chapter["kills"] > 0
    assert chapter["narrative_en"] and chapter["title_en"] and chapter["objective_en"]
    assert re.search(r"[\u3040-\u9fff]",chapter["narrative"])
    assert len(chapter["sites"]) == 3
    for index, site in enumerate(chapter["sites"]):
        assert site["kind"] in site_kinds
        assert 0 <= site["requires_kills"] <= chapter["kills"]
        assert site["requires_sites"] == sorted(set(site["requires_sites"]))
        assert all(isinstance(prior, int) and not isinstance(prior, bool) and 0 <= prior < index for prior in site["requires_sites"])
        assert all(site[field].strip() for field in ("name", "name_en", "restored", "restored_en"))
        assert all(re.search(r"[\u3040-\u9fff]",site[field]) for field in ("name", "restored"))
    assert chapter["sites"][0]["requires_sites"] == []
    assert chapter["sites"][-1]["requires_kills"] == chapter["kills"]
    assert len(chapter["dialogue"]) >= 2
    previous_end = 0.0
    for cue in chapter["dialogue"]:
        start, duration = cue["start_s"], cue["duration_s"]
        assert cue["speaker"] in speaker_ids
        assert all(isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) for value in (start, duration))
        assert previous_end <= start and 1.5 <= duration <= 8 and start + duration <= 45
        assert re.search(r"[\u3040-\u9fff]", cue["ja"]) and len(cue["ja"]) <= 64
        assert cue["en"].strip() and len(cue["en"]) <= 110
        previous_end = start + duration
assert "猫柳生新陰流" in catalog["chapters"][0]["narrative"]
manifest = json.loads((content / "SourceArt/manifest.json").read_text())
assert len(manifest["characters"]) == 2 and len(manifest["weapons"]) == 18
hero = manifest["hero_katana"]
assert hero["name"] == "SM_Nyaagyu_HeroKatana"
assert hero["fbx"] == hero["name"] + ".fbx"
assert hero["generator"] == "scripts/art/create_hero_katana.py"
assert hero["license"] == "Original project-owned artwork; no purchased assets"
hero_fbx = content / "SourceArt" / hero["fbx"]
assert hashlib.sha256(hero_fbx.read_bytes()).hexdigest() == hero["fbx_sha256"]
for file in (hero["source_blend"], hero["preview"], hero["detail_preview"]):
    assert (content / "SourceArt" / file).stat().st_size > 1000
for name in manifest["characters"] + manifest["weapons"] + manifest.get("skeletal_characters",[]) + manifest.get("walk_animations",[]) + [hero["name"]]:
    path = content / "SourceArt" / (name+".fbx")
    assert path.stat().st_size > 1000 and path.read_bytes().startswith(b"Kaydara FBX Binary")
bokken_root = content / "SourceArt/Weapons/Original"
bokken = json.loads((bokken_root / "manifest.json").read_text())
assert bokken["schema_version"] == 1
assert bokken["name"] == "SM_Nyaagyu_DojoBokken"
assert bokken["fbx"] == bokken["name"] + ".fbx"
assert bokken["generator"] == "scripts/art/create_dojo_bokken.py"
assert bokken["license"] == "Original project-owned artwork; no purchased assets"
assert bokken["unreal_asset"] == "/Game/Generated/Meshes/SM_Nyaagyu_DojoBokken.SM_Nyaagyu_DojoBokken"
assert 3500 < bokken["source_triangles"] < 10000
assert 1.0 < bokken["length_m"] < 1.1
for name, key in ((bokken["fbx"], "fbx_sha256"),
                  (bokken["source_blend"], "blend_sha256"),
                  (bokken["preview"], "preview_sha256")):
    path = bokken_root / name
    assert path.stat().st_size > 1000
    assert hashlib.sha256(path.read_bytes()).hexdigest() == bokken[key]
assert (bokken_root / bokken["fbx"]).read_bytes().startswith(b"Kaydara FBX Binary")
assert b"/Users/" not in (bokken_root / bokken["fbx"]).read_bytes()
assert bokken["unreal_asset"] in (ROOT / "Source/SoraArena/Private/SoraCharacter.cpp").read_text()
assert bokken["name"] in (ROOT / "scripts/unreal/import_original_assets.py").read_text()
arc = json.loads((bokken_root / "arc_carbine_manifest.json").read_text())
assert arc["schema_version"] == 1 and arc["name"] == "SM_Nyaagyu_ArcCarbine"
assert arc["generator"] == "scripts/art/create_arc_carbine.py"
assert arc["fbx"] == arc["name"] + ".fbx"
assert arc["unreal_asset"] == "/Game/Generated/Meshes/SM_Nyaagyu_ArcCarbine.SM_Nyaagyu_ArcCarbine"
assert catalog["weapons"][1]["id"] == 1 and catalog["weapons"][1]["name_en"] == "Arc Carbine"
assert catalog["weapons"][1]["special"] is False
assert arc["mesh_origin_m"] == [0, 0, 0] and arc["local_forward"] == "+X toward muzzle; +Z up"
assert arc["grip_web_m"] == [-.11, 0, -.05] and arc["grip_palm_center_m"] == [-.11, 0, -.12]
assert 3000 < arc["source_triangles"] < 30000 and arc["source_parts"] >= 50
assert .90 < arc["bounds_m"]["max"][0] - arc["bounds_m"]["min"][0] < 1.05
assert -.23 < arc["bounds_m"]["min"][2] < -.20
assert .5 < arc["muzzle_center_m"][0] < .54
assert "Original project-owned geometry" in arc["license"] and "CC0 Poly Haven" in arc["license"]
palette_root = content / "SourceArt/Environment/PolyHaven"
assert hashlib.sha256((palette_root / "manifest.json").read_bytes()).hexdigest() == arc["palette_manifest_sha256"]
assert arc["palette_asset_ids"] == ["wood_planks_dirt", "rusty_metal_02"]
for name, digest in ((arc["source_blend"], "blend_sha256"),
                     (arc["fbx"], "fbx_sha256"),
                     (arc["preview"], "preview_sha256")):
    path = bokken_root / name
    assert path.stat().st_size > 1000
    assert hashlib.sha256(path.read_bytes()).hexdigest() == arc[digest]
arc_fbx = (bokken_root / arc["fbx"]).read_bytes()
assert arc_fbx.startswith(b"Kaydara FBX Binary") and b"/Users/" not in arc_fbx
assert arc["name"] in (ROOT / "scripts/unreal/import_original_assets.py").read_text()
assert arc["unreal_asset"] in (ROOT / "Source/SoraArena/Private/SoraCharacter.cpp").read_text()
naginata_root = content / "SourceArt/Weapons/MonofilamentNaginata"
naginata = json.loads((naginata_root / "manifest.json").read_text())
assert naginata["schema_version"] == 1 and naginata["name"] == "SM_Nyaagyu_MonofilamentNaginata"
assert naginata["weapon_id"] == 12 and catalog["weapons"][12]["name_en"] == "Monofilament Naginata"
assert catalog["weapons"][12]["special"] is True
assert naginata["generator"] == "scripts/art/create_monofilament_naginata.py"
assert naginata["validator"] == "scripts/art/validate_monofilament_naginata.py"
assert naginata["unreal_asset"] == "/Game/ArtReview/Weapons/SM_Nyaagyu_MonofilamentNaginata.SM_Nyaagyu_MonofilamentNaginata"
assert naginata["muzzle_center_m"] is None and naginata["local_forward"] == "+X toward blade tip; +Z up"
assert 2.2 < naginata["length_m"] < 2.4 and naginata["external_images"] == []
assert "Original project-owned" in naginata["license"]
for filename, key in ((naginata["source_blend"], "blend_sha256"),
                      (naginata["fbx"], "fbx_sha256"),
                      (naginata["preview"], "preview_sha256"),
                      (naginata["detail_preview"], "detail_preview_sha256")):
    path = naginata_root / filename
    assert path.stat().st_size > 1000
    assert hashlib.sha256(path.read_bytes()).hexdigest() == naginata[key]
assert (naginata_root / naginata["fbx"]).read_bytes().startswith(b"Kaydara FBX Binary")
assert naginata["name"] in (ROOT / "scripts/unreal/import_original_assets.py").read_text()
assert naginata["name"] not in (ROOT / "Source/SoraArena/Private/SoraCharacter.cpp").read_text()
hero_character_root = content / "SourceArt/Characters/Hero"
hero_character = json.loads((hero_character_root / "manifest.json").read_text())
runtime_skin = json.loads((hero_character_root / "runtime_skin_manifest.json").read_text())
assert runtime_skin["schema_version"] == 1
assert runtime_skin["generator"] == "scripts/art/rig_nyaakoto_runtime.py"
assert runtime_skin["source_blend_sha256"] == hero_character["blend_sha256"]
assert runtime_skin["sora_kamon_svg_sha256"] == hero_character["insignia_sha256"]
assert runtime_skin["sora_kamon_placements"] == hero_character["sora_kamon_placements"]
assert len(runtime_skin["skeleton_bones"]) == 20
for filename, digest in ((runtime_skin["runtime_blend"], "runtime_blend_sha256"),
                         (runtime_skin["runtime_preview"], "runtime_preview_sha256")):
    path = hero_character_root / filename
    assert path.stat().st_size > 1000
    assert hashlib.sha256(path.read_bytes()).hexdigest() == runtime_skin[digest]
for filename, digest in ((runtime_skin["skeletal_fbx"], "skeletal_fbx_sha256"),
                         (runtime_skin["walk_fbx"], "walk_fbx_sha256")):
    path = content / "SourceArt" / filename
    assert path.stat().st_size > 1000
    assert hashlib.sha256(path.read_bytes()).hexdigest() == runtime_skin[digest]
pbr_root = hero_character_root / "PBR"
pbr = json.loads((pbr_root / "manifest.json").read_text())
assert pbr["schema_version"] == 1
assert pbr["generator"] == "scripts/art/create_nyaakoto_pbr_textures.py"
assert pbr["source_license"] == (
    "Project-owned OpenAI image-generation output and procedural PBR conversion; "
    "no external stock texture. Output ownership is assigned to the user under "
    "the OpenAI Terms of Use, subject to those terms.")
assert [source["surface"] for source in pbr["fur_sources"]] == [
    "fur_grey", "fur_white", "fur_charcoal"]
for source in pbr["fur_sources"]:
    filename = f"Source/Nyaakoto_{source['surface'].split('_')[1].capitalize()}Fur_ImageGen_v1.png"
    assert source["file"] == filename
    assert hashlib.sha256((pbr_root / filename).read_bytes()).hexdigest() == source["sha256"]
    assert source["origin"].startswith("Built-in OpenAI image_gen.imagegen, text-only prompt")
    assert re.fullmatch(r"exec-[0-9a-f-]{36}", source["origin_output_id"])
    assert source["source_url"] is None and len(source["prompt"]) > 200
    assert source["rights_url"] == "https://openai.com/policies/row-terms-of-use/"
assert [group["name"] for group in pbr["maps"]] == [
    "fur_grey", "fur_white", "fur_charcoal", "silk_indigo", "lacquer_oxblood", "neutral"]
for group in pbr["maps"]:
    assert group["resolution"] == ([4, 4] if group["name"] == "neutral" else [2048, 2048])
    assert [item["channel"] for item in group["maps"]] == ["Albedo", "NormalDX", "ORM"]
    for item in group["maps"]:
        assert item["file"] == f'T_Nyaakoto_{group["name"]}_{item["channel"]}.png'
        data = (pbr_root / item["file"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == item["sha256"]
        assert data[:16] == b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        assert list(struct.unpack(">II", data[16:24])) == group["resolution"]
        assert data[24:26] == b"\x08\x02"  # 8-bit RGB source texture
assert len(pbr["material_slots"]) == 23
assert "M_Hero_GreyTabbyFur" in pbr["material_slots"]
assert "M_Hero_SORAResistanceRed" in pbr["material_slots"]
for slot, surface in pbr["material_slots"].items():
    assert re.fullmatch(r"M_Hero_[A-Za-z0-9]+", slot)
    assert surface["surface"] in {group["name"] for group in pbr["maps"]}
    assert len(surface["tint"]) == 3 and all(0 <= value <= 1 for value in surface["tint"])
    assert 0 < surface["roughness_scale"] <= 2
    assert 0 <= surface["metallic_scale"] <= 1
assert "MI_Nyaakoto_" in (ROOT / "Source/SoraArena/Private/SoraCharacter.cpp").read_text()
assert hero_character["schema_version"] == 2
assert hero_character["name"] == "SM_Nyaagyu_HeroCharacter"
assert hero_character["character_name_ja"] == "ニャーコト"
assert hero_character["character_name_en"] == "Nyaakoto"
assert hero_character["user_design_reference_embedded"] is False
assert hero_character["user_design_reference_sha256"] == "c9f7a4bbe6ba529b2bbdb629db3ba09858c11b563c334e31593876455a550801"
assert hero_character["sora_kamon_placements"] == ["chest", "waist", "sode_-1", "sode_1"]
assert hero_character["generator"] == "scripts/art/create_nyaagyu_hero_character.py"
assert hero_character["validator"] == "scripts/art/validate_nyaagyu_hero_character.py"
assert hero_character["fbx"] == hero_character["name"] + ".fbx"
assert hero_character["unreal_asset"] == "/Game/ArtReview/Characters/SM_Nyaagyu_HeroCharacter.SM_Nyaagyu_HeroCharacter"
assert hero_character["world_origin_m"] == [0, 0, 0]
assert hero_character["local_forward"] == "+X face-forward; +Z up"
assert hero_character["rigged"] is False and hero_character["external_images"] == []
assert hero_character["source_parts"] >= 390 and 100000 <= hero_character["source_triangles"] < 130000
assert hero_character["bounds_m"]["min"][2] < .01
assert 2.15 < hero_character["bounds_m"]["max"][2] < 2.22
assert "Original project-owned character geometry" in hero_character["license"]
assert "user-supplied SORA insignia" in hero_character["license"]
for name, digest in ((hero_character["source_blend"], "blend_sha256"),
                     (hero_character["fbx"], "fbx_sha256"),
                     (hero_character["preview"], "preview_sha256"),
                     (hero_character["detail_preview"], "detail_preview_sha256")):
    path = hero_character_root / name
    assert path.stat().st_size > 1000
    assert hashlib.sha256(path.read_bytes()).hexdigest() == hero_character[digest]
hero_character_fbx = (hero_character_root / hero_character["fbx"]).read_bytes()
assert hero_character_fbx.startswith(b"Kaydara FBX Binary")
assert b"/Users/" not in hero_character_fbx
assert hero_character["name"] in (ROOT / "scripts/unreal/import_original_assets.py").read_text()
horse_root = content / "SourceArt/Horses/Nyaagyu"
horse = json.loads((horse_root / "manifest.json").read_text())
assert horse["schema_version"] == 1
assert horse["name"] == "SM_Nyaagyu_HorseAndTack"
assert horse["generator"] == "scripts/art/create_nyaagyu_horse_tack.py"
assert horse["validator"] == "scripts/art/validate_nyaagyu_horse_tack.py"
assert horse["fbx"] == horse["name"] + ".fbx"
assert horse["unreal_asset"] == "/Game/ArtReview/Horses/SM_Nyaagyu_HorseAndTack.SM_Nyaagyu_HorseAndTack"
assert horse["local_forward"] == "+X horse-forward; +Z up"
assert horse["world_origin_m"] == [0, 0, 0] and horse["units"] == "meters"
assert horse["rigged"] is False and horse["external_images"] == []
assert horse["source_parts"] >= 100 and 50000 <= horse["source_triangles"] < 100000
assert 1.7 < horse["bounds_m"]["max"][2] < 1.9
assert "Original project-owned horse/tack geometry" in horse["license"]
assert horse["insignia_sha256"] == hero_character["insignia_sha256"]
assert (horse_root / horse["insignia_source"]).resolve() == (content / "SourceArt/UI/sora_logo_NOtext2.svg").resolve()
for name, digest in ((horse["source_blend"], "blend_sha256"),
                     (horse["fbx"], "fbx_sha256"),
                     (horse["preview"], "preview_sha256")):
    path = horse_root / name
    assert path.stat().st_size > 1000
    assert hashlib.sha256(path.read_bytes()).hexdigest() == horse[digest]
horse_fbx = (horse_root / horse["fbx"]).read_bytes()
assert horse_fbx.startswith(b"Kaydara FBX Binary") and b"/Users/" not in horse_fbx
anchors = horse["anchors_m"]
assert set(anchors) == {"Horse_Root", "Saddle_RiderSeat", "Tazuna_LeftGrip", "Tazuna_RightGrip", "Abumi_LeftFoot", "Abumi_RightFoot"}
assert anchors["Tazuna_LeftGrip"][0] == anchors["Tazuna_RightGrip"][0]
assert anchors["Tazuna_LeftGrip"][1] == -anchors["Tazuna_RightGrip"][1]
assert anchors["Abumi_LeftFoot"][1] == -anchors["Abumi_RightFoot"][1]
assert horse["name"] in (ROOT / "scripts/unreal/import_original_assets.py").read_text()
concept_root = content / "SourceArt/Concepts"
concept = json.loads((concept_root / "nyaagyu_photoreal_character_target.json").read_text())
assert concept["schema_version"] == 1 and concept["generator"] == "OpenAI built-in image_gen"
assert concept["input_images"] == [] and "concept only" in concept["purpose"]
concept_bytes = (concept_root / concept["asset"]).read_bytes()
assert hashlib.sha256(concept_bytes).hexdigest() == concept["sha256"]
assert concept_bytes[:16] == b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
assert list(struct.unpack(">II", concept_bytes[16:24])) == concept["dimensions_px"]
environment_root = content / "SourceArt/Environment/Original"
environment = json.loads((environment_root / "manifest.json").read_text())
assert environment["schema_version"] == 2
assert environment["generator"] == "scripts/art/create_edo_environment_props.py"
assert environment["sora_kamon_svg_sha256"] == hero_character["insignia_sha256"]
assert environment["lantern_light_local_z_m"] == 2.52
assert "Original project-owned geometry" in environment["license"]
assert "CC0 Poly Haven" in environment["license"]
for name in (environment["source_blend"], environment["preview"], environment["detail_preview"]):
    assert (environment_root / name).stat().st_size > 1000
environment_names = ["SM_Edo_LanternPost", "SM_Nyaagyu_ToriiGate", "SM_Alien_DebtKiosk"]
assert [entry["name"] for entry in environment["assets"]] == environment_names
world_builder = (ROOT / "Source/SoraArena/Private/SoraWorldBuilder.cpp").read_text()
import_script = (ROOT / "scripts/unreal/import_original_assets.py").read_text()
assert all(name in world_builder and name in import_script for name in environment_names)
assert "Yaw+90.f" in world_builder and "HasAuthoredLantern?252.f:350.f" in world_builder
assert 'SM_Alien_DebtKiosk"),NodePositions[1]+FVector(315,0,0),FRotator(0,90,0)' in world_builder
assert "SORA authored environment prop" in world_builder
assert "ImportedProp" not in world_builder.split("void ASoraWorldBuilder::BuildPractice", 1)[1].split("void ASoraWorldBuilder::Build(", 1)[0]
for entry in environment["assets"]:
    fbx = environment_root / entry["fbx"]
    assert entry["fbx"] == entry["name"] + ".fbx"
    assert fbx.stat().st_size > 1000 and fbx.read_bytes().startswith(b"Kaydara FBX Binary")
    assert b"/Users/" not in fbx.read_bytes()
    assert hashlib.sha256(fbx.read_bytes()).hexdigest() == entry["fbx_sha256"]
    assert entry["source_triangles"] >= 3000 and entry["source_triangles"] < 50000
    assert entry["collision_boxes"] in (1, 3)
    assert entry["world_builder_yaw_offset_deg"] == (0 if "Lantern" in entry["name"] else 90)
    assert len(entry["bounds_m"]["min"]) == len(entry["bounds_m"]["max"]) == 3
    assert entry["bounds_m"]["min"][2] >= -0.01
    assert entry["bounds_m"]["max"][2] >= 2.2
torii_pbr_root = content / "SourceArt/Environment/ToriiLacquer"
torii_pbr = json.loads((torii_pbr_root / "manifest.json").read_text())
assert torii_pbr["schema_version"] == 1
assert torii_pbr["generator"] == "scripts/art/create_torii_lacquer_pbr.py"
assert torii_pbr["material_slot"] == "M_Env_VermilionLacquer"
assert torii_pbr["unreal_instance"] == "/Game/Generated/Environment/MI_Nyaagyu_ToriiLacquer.MI_Nyaagyu_ToriiLacquer"
assert torii_pbr["tile_size_cm"] == 120.0
assert torii_pbr["license"] == "Original project-owned procedural texture; no third-party input image"
assert set(torii_pbr["maps"]) == {"Albedo", "NormalDX", "ORM"}
for channel, entry in torii_pbr["maps"].items():
    path = torii_pbr_root / entry["file"]
    assert path.name == f"T_Nyaagyu_ToriiLacquer_{channel}.png"
    assert entry["resolution"] == [2048, 2048]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]
assert "import_torii_lacquer_pbr.py" in (ROOT / "scripts/unreal/import_environment_palette.py").read_text()
assert "import_nyaagyu_cargo_stack.py" in import_script
assert 'if(MapId==0 && ImportedProp(TEXT("SM_Nyaagyu_CargoStack")' in world_builder
assert "Cover->SetVisibility(false)" in world_builder
assert "SM_Nyaagyu_CargoStack" not in world_builder.split(
    "void ASoraWorldBuilder::BuildPractice", 1)[1].split("void ASoraWorldBuilder::Build(", 1)[0]
terrain_root = content / "SourceArt/Environment/NyaagyuTerrain"
terrain = json.loads((terrain_root / "manifest.json").read_text())
assert terrain["schema_version"] == 1
assert terrain["generator"] == "scripts/art/create_nyaagyu_mesh_terrain.py"
assert terrain["validator"] == "scripts/art/validate_nyaagyu_mesh_terrain.py"
assert terrain["world_xy_cm"] == [-3200, -2600, 3200, 2600]
assert terrain["tile_layout"] == [4, 4] and terrain["tile_size_cm"] == [1600, 1300]
assert terrain["max_visual_collision_delta_cm"] <= 5
assert terrain["material_slots"] == ["M_Terrain_Soil_PolyHaven", "M_Terrain_Stone_PolyHaven"]
assert terrain["palette_license"] == "CC0-1.0; https://polyhaven.com/license"
assert len(terrain["tiles"]) == 32
assert [(entry["role"], entry["channel"]) for entry in terrain["palette_files"]] == [
    ("soil", "diffuse"), ("soil", "normal"), ("soil", "arm"),
    ("stone", "diffuse"), ("stone", "normal"), ("stone", "arm"),
    ("stone", "displacement")]
assert "if(MapId==0) NyaagyuTerrain();" in world_builder
assert "NyaagyuTerrain()" not in world_builder.split("void ASoraWorldBuilder::BuildPractice", 1)[1].split("void ASoraWorldBuilder::Build(", 1)[0]
assert "SetCollisionEnabled(ECollisionEnabled::NoCollision)" in world_builder
for name, digest in ((terrain["source_blend"], terrain["source_blend_sha256"]),
                     (terrain["preview"], terrain["preview_sha256"])):
    path = terrain_root / name
    assert path.stat().st_size > 1000
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
for entry in terrain["palette_files"]:
    path = ROOT / entry["path"]
    assert path.stat().st_size == entry["bytes"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]
for tier in ("hi", "mac"):
    for y in range(4):
        for x in range(4):
            records = [record for record in terrain["tiles"]
                       if record["tier"] == tier and record["index"] == [x, y]]
            assert len(records) == 1
            record = records[0]
            name = f"SM_NyaagyuTerrain_{tier.upper()}_X{x}_Y{y}"
            assert record["name"] == name and record["fbx"] == name + ".fbx"
            assert record["placement_center_cm"] == [-2400 + 1600*x, -1950 + 1300*y, 0]
            assert max(record["z_range_cm"]) <= terrain["max_visual_collision_delta_cm"]
            fbx = terrain_root / record["fbx"]
            assert fbx.read_bytes().startswith(b"Kaydara FBX Binary")
            assert b"/Users/" not in fbx.read_bytes()
            assert hashlib.sha256(fbx.read_bytes()).hexdigest() == record["fbx_sha256"]
tree_root = content / "SourceArt/Environment/PolyHaven/TreeSmall02"
tree = json.loads((tree_root / "manifest.json").read_text())
assert tree["schema_version"] == 1 and tree["asset_id"] == "tree_small_02"
assert tree["license"] == "CC0-1.0; https://polyhaven.com/license"
assert tree["gameplay_collision"] is False and tree["instances_in_nyaagyu_estate"] == 10
assert len(tree["upstream_files"]) == 11 and len(tree["texture_files"]) == 10
assert [(record["tier"], record["nanite"]) for record in tree["meshes"]] == [("hi", True), ("mac", False)]
assert "NyaagyuTree(P+FVector(450,-S*250,0)" in world_builder
assert "Bloom%d%d%d" not in world_builder
assert "NyaagyuTree(" not in world_builder.split("void ASoraWorldBuilder::BuildPractice", 1)[1].split("void ASoraWorldBuilder::Build(", 1)[0]
pine_root = content / "SourceArt/Environment/PolyHaven/PineSaplingSmall"
pine = json.loads((pine_root / "manifest.json").read_text())
assert pine["schema_version"] == 1 and pine["asset_id"] == "pine_sapling_small"
assert pine["license"] == "CC0-1.0; https://polyhaven.com/license"
assert pine["gameplay_collision"] is False and pine["instances_in_nyaagyu_estate"] == 9
assert len(pine["upstream_files"]) == 8 and len(pine["texture_files"]) == 8
assert len(pine["meshes"]) == 6
assert "NyaagyuPine(FVector(X,Y,0)" in world_builder
assert "NyaagyuPine(" not in world_builder.split("void ASoraWorldBuilder::BuildPractice", 1)[1].split("void ASoraWorldBuilder::Build(", 1)[0]
for record in tree["upstream_files"] + tree["texture_files"]:
    path = tree_root / record["path"]
    assert path.stat().st_size == record["bytes"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == record["sha256"]
for record in tree["meshes"]:
    path = tree_root / record["fbx"]
    assert path.read_bytes().startswith(b"Kaydara FBX Binary")
    assert b"/Users/" not in path.read_bytes()
    assert hashlib.sha256(path.read_bytes()).hexdigest() == record["fbx_sha256"]
street_root = content / "SourceArt/Environment/StreetDebtTerminal"
street = json.loads((street_root / "manifest.json").read_text())
assert street["schema_version"] == 1
assert street["name"] == "SM_Alien_StreetDebtTerminal"
assert street["generator"] == "scripts/art/create_street_debt_terminal.py"
assert street["unreal_asset"] == "/Game/Generated/Environment/Props/SM_Alien_StreetDebtTerminal.SM_Alien_StreetDebtTerminal"
assert street["fbx"] == street["name"] + ".fbx"
assert street["source_parts"] == 31 and 3000 < street["source_triangles"] < 5000
assert street["collision_boxes"] == 1
assert "Original project-owned geometry" in street["license"] and "CC0 Poly Haven" in street["license"]
assert street["bounds_m"]["min"][2] == 0 and 2.2 < street["bounds_m"]["max"][2] < 2.5
for name, digest in ((street["source_blend"], "blend_sha256"),
                     (street["fbx"], "fbx_sha256"),
                     (street["preview"], "preview_sha256")):
    path = street_root / name
    assert path.stat().st_size > 1000
    assert hashlib.sha256(path.read_bytes()).hexdigest() == street[digest]
street_fbx = (street_root / street["fbx"]).read_bytes()
assert street_fbx.startswith(b"Kaydara FBX Binary") and b"/Users/" not in street_fbx
assert street["name"] in world_builder and street["name"] in import_script
assert 'if(MapId==1)' in world_builder and 'StreetDebtTerminalCollision' in world_builder
assert "ImportedProp" not in world_builder.split("void ASoraWorldBuilder::BuildPractice", 1)[1].split("void ASoraWorldBuilder::Build(", 1)[0]
sluice_root = content / "SourceArt/Environment/NyaagyuSluice"
sluice = json.loads((sluice_root / "manifest.json").read_text())
assert sluice["schema_version"] == 1
assert sluice["name"] == "SM_Nyaagyu_IrrigationSluice"
assert sluice["generator"] == "scripts/art/create_nyaagyu_sluice.py"
assert sluice["unreal_asset"] == "/Game/Generated/Environment/Props/SM_Nyaagyu_IrrigationSluice.SM_Nyaagyu_IrrigationSluice"
assert 5000 <= sluice["source_triangles"] < 50000 and sluice["collision_boxes"] == 3
assert "Original project-owned geometry" in sluice["license"] and "CC0 Poly Haven" in sluice["license"]
for name, digest in ((sluice["source_blend"], "blend_sha256"),
                     (sluice["fbx"], "fbx_sha256"),
                     (sluice["preview"], "preview_sha256")):
    path = sluice_root / name
    assert path.stat().st_size > 1000
    assert hashlib.sha256(path.read_bytes()).hexdigest() == sluice[digest]
assert sluice["name"] in world_builder and sluice["name"] in import_script
assert 'if(MapId==0) ImportedProp(TEXT("SM_Nyaagyu_IrrigationSluice")' in world_builder
assert "ImportedProp" not in world_builder.split("void ASoraWorldBuilder::BuildPractice", 1)[1].split("void ASoraWorldBuilder::Build(", 1)[0]
loom_root = content / "SourceArt/Environment/SilkFoundryLoom"
loom = json.loads((loom_root / "manifest.json").read_text())
assert loom["schema_version"] == 1
assert loom["name"] == "SM_SilkFoundry_LevyLoom"
assert loom["generator"] == "scripts/art/create_silk_foundry_loom.py"
assert loom["unreal_asset"] == "/Game/Generated/Environment/Props/SM_SilkFoundry_LevyLoom.SM_SilkFoundry_LevyLoom"
assert loom["fbx"] == loom["name"] + ".fbx"
assert loom["source_parts"] >= 250 and 15000 <= loom["source_triangles"] < 50000
assert loom["collision_boxes"] == 4
assert "Original project-owned geometry" in loom["license"] and "CC0 Poly Haven" in loom["license"]
assert loom["bounds_m"]["min"][2] == 0 and 2.2 < loom["bounds_m"]["max"][2] < 2.4
for name, digest in ((loom["source_blend"], "blend_sha256"),
                     (loom["fbx"], "fbx_sha256"),
                     (loom["preview"], "preview_sha256")):
    path = loom_root / name
    assert path.stat().st_size > 1000
    assert hashlib.sha256(path.read_bytes()).hexdigest() == loom[digest]
loom_fbx = (loom_root / loom["fbx"]).read_bytes()
assert loom_fbx.startswith(b"Kaydara FBX Binary") and b"/Users/" not in loom_fbx
assert loom["name"] in world_builder and loom["name"] in import_script
assert "ImportedProp" not in world_builder.split("void ASoraWorldBuilder::BuildPractice", 1)[1].split("void ASoraWorldBuilder::Build(", 1)[0]
dojo_root = content / "SourceArt/Environment/NyaagyuDojo"
dojo = json.loads((dojo_root / "manifest.json").read_text())
assert dojo["schema_version"] == 1
assert dojo["name"] == "SM_Nyaagyu_EstateDojo"
assert dojo["generator"] == "scripts/art/create_nyaagyu_dojo.py"
assert dojo["unreal_asset"] == "/Game/Generated/Environment/Props/SM_Nyaagyu_EstateDojo.SM_Nyaagyu_EstateDojo"
assert dojo["fbx"] == dojo["name"] + ".fbx"
assert 300 <= dojo["source_parts"] <= 600 and 45000 <= dojo["source_triangles"] < 120000
assert dojo["shoji_bays"] == 4 and dojo["roof_tile_count"] == 748 and dojo["collision_boxes"] == 3
assert dojo["sora_kamon_svg_sha256"] == hero_character["insignia_sha256"]
assert "Original project-owned geometry" in dojo["license"] and "CC0 Poly Haven" in dojo["license"]
for name, digest in ((dojo["source_blend"], "blend_sha256"),
                     (dojo["fbx"], "fbx_sha256"),
                     (dojo["preview"], "preview_sha256")):
    path = dojo_root / name
    assert path.stat().st_size > 1000
    assert hashlib.sha256(path.read_bytes()).hexdigest() == dojo[digest]
dojo_fbx = (dojo_root / dojo["fbx"]).read_bytes()
assert dojo_fbx.startswith(b"Kaydara FBX Binary") and b"/Users/" not in dojo_fbx
assert dojo["name"] in world_builder and dojo["name"] in import_script
assert "SetVisibility(false)" in world_builder
kura_root = content / "SourceArt/Environment/NyaagyuKura"
kura = json.loads((kura_root / "manifest.json").read_text())
assert kura["schema_version"] == 1
assert kura["name"] == "SM_Nyaagyu_ProvisionKura"
assert kura["generator"] == "scripts/art/create_nyaagyu_kura.py"
assert kura["unreal_asset"] == "/Game/Generated/Environment/Props/SM_Nyaagyu_ProvisionKura.SM_Nyaagyu_ProvisionKura"
assert kura["fbx"] == kura["name"] + ".fbx"
assert 300 <= kura["source_parts"] <= 500 and 45000 <= kura["source_triangles"] < 100000
assert kura["roof_tile_count"] == 600 and kura["shutter_count"] == 4 and kura["collision_boxes"] == 3
assert kura["palette_asset_ids"] == ["wood_planks_dirt", "stone_floor", "grey_roof_tiles", "white_plaster_02"]
assert kura["sora_kamon_svg_sha256"] == hero_character["insignia_sha256"]
assert "Original project-owned geometry" in kura["license"] and "CC0 Poly Haven" in kura["license"]
for name, digest in ((kura["source_blend"], "blend_sha256"),
                     (kura["fbx"], "fbx_sha256"),
                     (kura["preview"], "preview_sha256")):
    path = kura_root / name
    assert path.stat().st_size > 1000
    assert hashlib.sha256(path.read_bytes()).hexdigest() == kura[digest]
kura_fbx = (kura_root / kura["fbx"]).read_bytes()
assert kura_fbx.startswith(b"Kaydara FBX Binary") and b"/Users/" not in kura_fbx
assert kura["name"] in world_builder and kura["name"] in import_script
assert "(I==1||I==3)" in world_builder
roof_root = content / "SourceArt/Environment/PolyHaven/GreyRoofTiles"
roof = json.loads((roof_root / "manifest.json").read_text())
assert roof["schema_version"] == 1 and roof["asset_id"] == "grey_roof_tiles"
assert roof["role"] == "kawara" and roof["license"] == "CC0-1.0"
assert roof["asset_url"] == "https://polyhaven.com/a/grey_roof_tiles"
assert roof["authors"] == {"Rob Tuytel": "All"}
assert roof["source_dimensions_mm"] == [3000, 3000] and roof["tile_size_cm"] == 300.0
assert roof["unreal_instance"] == "/Game/Generated/Environment/MI_Nyaagyu_Kawara.MI_Nyaagyu_Kawara"
assert [item["channel"] for item in roof["files"]] == ["Diffuse", "nor_dx", "arm"]
for item in roof["files"]:
    data = (roof_root / item["file"]).read_bytes()
    assert len(data) == item["bytes"]
    assert hashlib.sha256(data).hexdigest() == item["sha256"]
assert 'Role=TEXT("Kawara"); TileSizeCm=300.f;' in world_builder
assert "MI_Nyaagyu_Kawara" in (ROOT / "scripts/unreal/validate_imported_assets.py").read_text()
plaster_root = content / "SourceArt/Environment/PolyHaven/WhitePlaster02"
plaster = json.loads((plaster_root / "manifest.json").read_text())
assert plaster["schema_version"] == 1 and plaster["asset_id"] == "white_plaster_02"
assert plaster["role"] == "plaster" and plaster["license"] == "CC0-1.0"
assert plaster["asset_url"] == "https://polyhaven.com/a/white_plaster_02"
assert plaster["authors"] == {"Rob Tuytel": "All"}
assert plaster["source_dimensions_mm"] == [1000, 1000] and plaster["tile_size_cm"] == 100.0
assert plaster["unreal_instance"] == "/Game/Generated/Environment/MI_Nyaagyu_Plaster.MI_Nyaagyu_Plaster"
assert [item["channel"] for item in plaster["files"]] == ["Diffuse", "nor_dx", "arm"]
assert hashlib.sha256((plaster_root / "manifest.json").read_bytes()).hexdigest() == kura["plaster_manifest_sha256"]
for item in plaster["files"]:
    data = (plaster_root / item["file"]).read_bytes()
    assert len(data) == item["bytes"]
    assert hashlib.sha256(data).hexdigest() == item["sha256"]
assert 'Role=TEXT("Plaster"); TileSizeCm=100.f;' in world_builder
assert "MI_Nyaagyu_Plaster" in (ROOT / "scripts/unreal/validate_imported_assets.py").read_text()
assert "ImportedProp" not in world_builder.split("void ASoraWorldBuilder::BuildPractice", 1)[1].split("void ASoraWorldBuilder::Build(", 1)[0]
font = content / "SourceArt/Fonts/NotoSansCJKjp-Regular.otf"
logo_manifest = json.loads((content / "SourceArt/UI/sora_logo_manifest.json").read_text())
assert hero_character["insignia_sha256"] == logo_manifest["source_sha256"]
assert (hero_character_root / hero_character["insignia_source"]).resolve() == (content / "SourceArt/UI/sora_logo_NOtext2.svg").resolve()
assert logo_manifest["source_svg"] == "sora_logo_NOtext2.svg"
assert logo_manifest["runtime_png"] == "SORA_Resistance_Logo.png"
assert logo_manifest["unreal_asset"] == "/Game/Generated/UI/T_SoraResistanceLogo.T_SoraResistanceLogo"
for name, digest in (("source_svg", "source_sha256"), ("runtime_png", "runtime_sha256")):
    logo_file = content / "SourceArt/UI" / logo_manifest[name]
    assert hashlib.sha256(logo_file.read_bytes()).hexdigest() == logo_manifest[digest]
logo_png = (content / "SourceArt/UI" / logo_manifest["runtime_png"]).read_bytes()
assert logo_png[:16] == b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
assert struct.unpack(">II", logo_png[16:24]) == (1024, 1024)
assert logo_png[24:26] == b"\x08\x06"  # 8-bit RGBA; the full bytes are hash-pinned above.
assert "T_SoraResistanceLogo.T_SoraResistanceLogo" in (ROOT / "Source/SoraArena/Private/SoraHUD.cpp").read_text()
assert hashlib.sha256(font.read_bytes()).hexdigest() == "68a3fc98800b2a27b371f2fb79991daf3633bd89309d4ffaa6946fd587f375b5"
assert hashlib.sha256(font.read_bytes()).hexdigest() == street["font_sha256"]
assert "SIL OPEN FONT LICENSE" in (font.parent / "OFL.txt").read_text()
from fontTools.ttLib import TTFont
cmap = TTFont(font).getBestCmap()
text = json.dumps(catalog,ensure_ascii=False)
text += "".join(p.read_text() for p in (ROOT / "Source/SoraArena").rglob("*.cpp"))
absent = sorted({ch for ch in text if ord(ch)>127 and ord(ch) not in cmap})
assert not absent, f"Bundled font lacks glyphs: {absent}"
cue_count = sum(len(chapter["dialogue"]) for chapter in catalog["chapters"])
fbx_count = sum(1 for _ in (content / "SourceArt").rglob("*.fbx"))
print(f"Content validation passed: 6 classes, 18 weapons, 8 Japanese chapters with 24 authored production sites and {cue_count} timed bilingual dialogue cues, 4 maps, {fbx_count} FBX source assets including a dojo bokken, Arc carbine, Samurai special naginata, feline hero character, Edo horse/tack study, 32 modular terrain tiles and 8 original environment props, 18 hash-pinned Nyaakoto PBR maps for 23 runtime materials, licensed Japanese font, hash-verified SORA logo.")
