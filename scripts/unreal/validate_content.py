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
assert catalog["schema_version"] == 2
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
for chapter in catalog["chapters"]:
    assert 0 <= chapter["map"] < 4 and chapter["kills"] > 0
    assert chapter["narrative_en"] and chapter["title_en"] and chapter["objective_en"]
    assert re.search(r"[\u3040-\u9fff]",chapter["narrative"])
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
font = content / "SourceArt/Fonts/NotoSansCJKjp-Regular.otf"
logo_manifest = json.loads((content / "SourceArt/UI/sora_logo_manifest.json").read_text())
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
assert "SIL OPEN FONT LICENSE" in (font.parent / "OFL.txt").read_text()
from fontTools.ttLib import TTFont
cmap = TTFont(font).getBestCmap()
text = json.dumps(catalog,ensure_ascii=False)
text += "".join(p.read_text() for p in (ROOT / "Source/SoraArena").rglob("*.cpp"))
absent = sorted({ch for ch in text if ord(ch)>127 and ord(ch) not in cmap})
assert not absent, f"Bundled font lacks glyphs: {absent}"
cue_count = sum(len(chapter["dialogue"]) for chapter in catalog["chapters"])
print(f"Content validation passed: 6 classes, 18 weapons, 8 Japanese chapters with {cue_count} timed bilingual dialogue cues, 4 maps, 25 FBX assets including hero katana and prototype rigs, licensed Japanese font, hash-verified SORA logo.")
