"""Host-only acceptance of the same chapter gates USoraCampaignDirector uses.

It complements, and cannot replace, the in-editor SoraArena.Campaign.Playthrough
automation test, which clears the campaign and reads every checkpoint from disk.
"""

import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
catalog = json.loads((ROOT / "Content/Data/catalog.json").read_text())
chapters = catalog["chapters"]
speakers = {entry["id"]: entry for entry in catalog["dialogue_speakers"]}
assert len(chapters) == 8
assert catalog["default_language"] == "ja"
assert catalog["english_subtitles_default"] is True
assert all(re.search(r"[\u3040-\u9fff]", speaker["ja"]) and speaker["en"].strip()
           for speaker in speakers.values())
for chapter in chapters:
    assert chapter["dialogue"]
    for cue in chapter["dialogue"]:
        assert cue["speaker"] in speakers
        assert re.search(r"[\u3040-\u9fff]", cue["ja"])
        assert cue["en"].strip()
    assert len(chapter["sites"]) == 3
assert chapters[-1]["kills"] == 18
assert chapters[-1]["sites"][-1]["requires_kills"] == 18
assert any(cue["speaker"] == "banker" for cue in chapters[-1]["dialogue"])
campaign = (ROOT / "Source/SoraArena/Private/Game/SoraCampaignDirector.cpp").read_text()
for gate in ("CheckpointValid", "RecordDefeat", "RestoreSite", "CompleteChapter",
             "CanSpawnFinalBoss", "AdvanceChapter", "CampaignLiberated"):
    assert f"SoraCampaignRules::{gate}" in campaign, f"The campaign director no longer uses tested {gate} gate"
for gate in ("Record", "CheckpointValid", "CanScoreBout"):
    assert f"SoraDojoRules::{gate}" in campaign, f"The campaign director no longer uses tested dojo {gate} gate"
# The hero records the stance and recovery lessons; his defense, the guard and parry lessons.
character = ((ROOT / "Source/SoraArena/Private/Characters/SoraPlayerCharacter.cpp").read_text() +
             (ROOT / "Source/SoraArena/Private/Combat/SoraDefense.cpp").read_text())
assert "SoraDojoRules::EAction::Stance" in character
assert "SoraDojoRules::EAction::Guard" in character
assert "SoraDojoRules::EAction::Parry" in character
assert "SoraDojoRules::EAction::Recovery" in character
save_header = (ROOT / "Source/SoraArena/Public/SoraSaveGame.h").read_text()
assert "UPROPERTY(SaveGame) int32 CheckpointDojoLessonMask" in save_header
assert "Save->SaveSchema=5" in campaign

lines = ["static constexpr FChapterFixture Chapters[] = {"]
for chapter in chapters:
    sites = []
    for site in chapter["sites"]:
        mask = sum(1 << prior for prior in site["requires_sites"])
        sites.append("{" + f'{site["requires_kills"]}, {mask}u' + "}")
    lines.append("    {" + f'{chapter["kills"]}, ' + "{" + ", ".join(sites) + "}},")
lines.append("};")

build_env = os.environ.copy()
compiler = shutil.which("clang++") or shutil.which("c++")
sdk_args = []
if platform.system() == "Darwin":
    pins = json.loads((ROOT / "scripts/toolchain/versions.json").read_text())
    build_env["DEVELOPER_DIR"] = (
        build_env.get("SORA_DEVELOPER_DIR")
        or build_env.get("DEVELOPER_DIR")
        or str(Path(pins["default_macos_xcode"]).expanduser())
    )
    compiler = subprocess.check_output(["xcrun", "--find", "clang++"], env=build_env, text=True).strip()
    sdk = subprocess.check_output(["xcrun", "--sdk", "macosx", "--show-sdk-path"],
                                  env=build_env, text=True).strip()
    build_env["SDKROOT"] = sdk
    sdk_args = ["-isysroot", sdk]
if compiler is None:
    raise SystemExit("A C++17 compiler is required for the campaign rules acceptance test")
with tempfile.TemporaryDirectory(prefix="sora-campaign-acceptance-") as directory:
    temporary = Path(directory)
    (temporary / "campaign_chapters.generated.inc").write_text("\n".join(lines) + "\n")
    binary = temporary / "campaign-progress"
    subprocess.run([
        compiler, "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror", "-pedantic", *sdk_args,
        "-I", str(ROOT / "Source/SoraArena/Public"), "-I", str(temporary),
        str(ROOT / "scripts/unreal/campaign_progression_driver.cpp"), "-o", str(binary),
    ], check=True, env=build_env)
    subprocess.run([str(binary)], check=True)

print(f"Japanese cues with English counterparts: {sum(len(chapter['dialogue']) for chapter in chapters)}")
