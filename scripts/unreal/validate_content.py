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
for speaker in speakers:
    assert re.fullmatch(r"[a-z][a-z0-9_]*", speaker["id"])
    assert re.search(r"[\u3040-\u9fff]", speaker["ja"])
    assert speaker["en"].strip()
game_config = (ROOT / "Config/DefaultGame.ini").read_text()
assert "[Internationalization]\nCulture=ja" in game_config
assert "InternationalizationPreset=EFIGSCJK" in game_config
assert "!CulturesToStage=ClearArray" in game_config
assert set(re.findall(r"^\+CulturesToStage=(\S+)$", game_config, re.MULTILINE)) == {"ja", "en"}
assert len(catalog["classes"]) == 6 and len(catalog["weapons"]) == 18
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
hero_character_root = content / "SourceArt/Characters/Hero"
hero_character = json.loads((hero_character_root / "manifest.json").read_text())
assert hero_character["schema_version"] == 1
assert hero_character["name"] == "SM_Nyaagyu_HeroCharacter"
assert hero_character["generator"] == "scripts/art/create_nyaagyu_hero_character.py"
assert hero_character["validator"] == "scripts/art/validate_nyaagyu_hero_character.py"
assert hero_character["fbx"] == hero_character["name"] + ".fbx"
assert hero_character["unreal_asset"] == "/Game/Generated/Meshes/SM_Nyaagyu_HeroCharacter.SM_Nyaagyu_HeroCharacter"
assert hero_character["world_origin_m"] == [0, 0, 0]
assert hero_character["local_forward"] == "+X face-forward; +Z up"
assert hero_character["rigged"] is False and hero_character["external_images"] == []
assert hero_character["source_parts"] >= 250 and 40000 <= hero_character["source_triangles"] < 100000
assert hero_character["bounds_m"]["min"][2] < .01
assert 1.83 < hero_character["bounds_m"]["max"][2] < 1.90
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
assert environment["schema_version"] == 1
assert environment["generator"] == "scripts/art/create_edo_environment_props.py"
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
print(f"Content validation passed: 6 classes, 18 weapons, 8 Japanese chapters with 24 authored production sites and {cue_count} timed bilingual dialogue cues, 4 maps, 34 FBX source assets including a dojo bokken, Arc carbine, feline hero character and 6 original environment props, licensed Japanese font, hash-verified SORA logo.")
