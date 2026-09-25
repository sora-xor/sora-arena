"""Host-only acceptance of the schema-4 chapter beat gates in SoraBeatRules.h.

Reads the eight generated chapter files in Content/Data/campaign, writes a
temporary C++ fixture of each chapter's beats (requirements, production site,
weapon and mechanic unlocks, auto-grants, checkpoints) and compiles
campaign_progression_driver.cpp against SoraBeatRules.h. The driver plays
every chapter on two routes, skipping or playing the optional beats, and
checks the gates, checkpoints, forged saves and final unlocks. It also keeps
the chapter-one dojo lesson test of SoraDojoRules.h.

It complements, and cannot replace, the in-editor SoraArena.Campaign.Playthrough
automation test, which plays the campaign in a real world and reads every
checkpoint from disk.
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
DATA = ROOT / "Content/Data"
catalog = json.loads((DATA / "catalog.json").read_text())
campaign = json.loads((DATA / "campaign/campaign.json").read_text())
chapters = [json.loads((DATA / entry["file"]).read_text()) for entry in campaign["chapters"]]
speakers = {entry["id"]: entry for entry in catalog["dialogue_speakers"]}
mechanic_bits = {name: bit for bit, name in enumerate(campaign["mechanics"])}
assert catalog["schema_version"] == 4 and campaign["schema_version"] == 4 and len(chapters) == 8
assert catalog["default_language"] == "ja"
assert catalog["english_subtitles_default"] is True
assert len(mechanic_bits) == 19
assert all(re.search(r"[぀-鿿]", speaker["ja"]) and speaker["en"].strip()
           for speaker in speakers.values())
for chapter in chapters:
    assert chapter["lines"] and chapter["triggers"]
    for line in chapter["lines"]:
        assert line["speaker"] in speakers
        assert re.search(r"[぀-鿿]", line["ja"])
        assert line["en"].strip()
assert chapters[-1]["beats"][-1]["id"] == "ch08.b18"
assert any(line["speaker"] == "banker" for line in chapters[-1]["lines"])
assert any(beat["type"] == "boss" and beat["params"]["boss"] == "boss_val_amort" for beat in chapters[-1]["beats"])
# The Unreal director runs the beats, saves and chapter advance through the
# same host-tested gates, and the chapter-one dojo lessons through SoraDojoRules.
director = (ROOT / "Source/SoraArena/Private/Game/SoraCampaignDirector.cpp").read_text()
for gate in ("Record", "CheckpointValid", "CanScoreBout"):
    assert f"SoraDojoRules::{gate}" in director, f"The campaign director no longer uses tested dojo {gate} gate"
for gate in ("CompleteBeat", "NextBeat", "FinishChapter", "ProgressValid", "CheckpointValid", "EntryValid", "CanStartBeat"):
    assert f"SoraBeatRules::{gate}" in director, f"The campaign director no longer uses tested beat {gate} gate"
for gate in ("AdvanceChapter", "CampaignLiberated", "CollectibleBit", "CollectiblesValid", "RecordArenaDefeat",
             "RestoreArenaSite", "FinishArena"):
    assert f"SoraCampaignRules::{gate}" in director, f"The campaign director no longer uses tested campaign {gate} gate"
catalog_loader = (ROOT / "Source/SoraArena/Private/SoraCatalog.cpp").read_text()
assert "SoraBeatRules::ChapterValid" in catalog_loader, "The catalog loader no longer refuses invalid chapters"
character = (ROOT / "Source/SoraArena/Private/Characters/SoraPlayerCharacter.cpp").read_text()
for action in ("Stance", "Guard", "Parry", "Recovery"):
    assert f"SoraDojoRules::EAction::{action}" in character


def mask(bits):
    value = 0
    for bit in bits:
        assert 0 <= bit < 32 and not value & (1 << bit)
        value |= 1 << bit
    return value


def phase_checkpoints(chapter, beat):
    return sum(1 for row in chapter["checkpoints"] if row["beat"] == beat["id"] and row["phase"] > 0)


lines = ["static constexpr FChapterFixture Chapters[] = {"]
for chapter in chapters:
    index = {beat["id"]: position for position, beat in enumerate(chapter["beats"])}
    assert len(index) <= 32
    rows = []
    for beat in chapter["beats"]:
        unlocks = beat["unlocks"]
        fields = (
            f'{mask(index[prior] for prior in beat["requires"])}u',
            str(-1 if beat["site"] is None else beat["site"]),
            f'{mask(unlocks["weapons"])}u',
            f'{mask(unlocks["grants"])}u',
            f'{mask(mechanic_bits[name] for name in unlocks["mechanics"])}u',
            "true" if beat["optional"] else "false",
            "true" if beat["checkpoint"] else "false",
            str(phase_checkpoints(chapter, beat)),
        )
        rows.append("        {" + ", ".join(fields) + "},  // " + beat["id"] + " " + beat["type"])
    lines.append("    {" + str(len(rows)) + ", {")
    lines.extend(rows)
    lines.append("    }},")
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

print(f"Bilingual lines with speakers: {sum(len(chapter['lines']) for chapter in chapters)}; "
      f"beats: {sum(len(chapter['beats']) for chapter in chapters)}")
