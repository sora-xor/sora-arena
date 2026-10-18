"""Host-only acceptance of the schema-4 beat rules in SoraBeatRules.h.

Reads the eight generated chapter files in Content/Data/campaign and writes a
temporary C++ fixture of every beat: its gates (requirements, production site,
weapon, mechanic and story-flag unlocks, auto-grants, checkpoints) and its
task, the integer block build_campaign_data.py derives from the bible's §12.2
parameters and SoraCatalog.cpp loads. It also writes the bible §11 weapon
unlock order. It then compiles campaign_progression_driver.cpp against
SoraBeatRules.h, SoraCampaignRules.h and SoraDojoRules.h. The driver runs every
beat type's completion, advance, failure, retry and checkpoint rules on
hand-made tasks, plays every authored task to completion and through its
failures, and plays every chapter on two routes (skipping or playing the
optional beats), checking the gates, checkpoints, forged saves, unlock order
and final unlocks. It also keeps the chapter-one dojo lesson test.

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
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "Content/Data"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_campaign import WEAPON_UNLOCKS  # noqa: E402  (bible §11, in unlock order)

catalog = json.loads((DATA / "catalog.json").read_text())
campaign = json.loads((DATA / "campaign/campaign.json").read_text())
chapters = [json.loads((DATA / entry["file"]).read_text()) for entry in campaign["chapters"]]
speakers = {entry["id"]: entry for entry in catalog["dialogue_speakers"]}
mechanic_bits = {row["id"]: bit for bit, row in enumerate(campaign["mechanics"])}
flag_bits = {name: bit for bit, name in enumerate(campaign["story_flags"])}
assert catalog["schema_version"] == 4 and campaign["schema_version"] == 4 and len(chapters) == 8
assert catalog["default_language"] == "ja"
assert catalog["english_subtitles_default"] is True
assert len(mechanic_bits) == 19 and len(flag_bits) <= 16
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
# same host-tested rules, and the chapter-one dojo lessons through SoraDojoRules.
director = (ROOT / "Source/SoraArena/Private/Game/SoraCampaignDirector.cpp").read_text()
for gate in ("Record", "CheckpointValid", "CanScoreBout"):
    assert f"SoraDojoRules::{gate}" in director, f"The campaign director no longer uses tested dojo {gate} gate"
for gate in ("CompleteBeat", "NextBeat", "FinishChapter", "ProgressValid", "CheckpointValid", "EntryValid",
             "CanStartBeat", "StartTask", "ReleaseWaves", "ReleaseWave", "Tick", "TaskComplete", "Skip",
             "FinishLines", "Reach", "Travel", "RecordDefeat", "ScorePoint", "RecordForms", "OpponentHealth", "WorkObjective",
             "Turn", "Pickup", "Deliver", "DropCarried", "Stroke", "DamageTarget", "RepairTarget", "OpenCache",
             "Fail", "RetryTask", "ProgressPermille", "CrankSlipping", "PhaseStartPermille", "RepeatForm", "RecordFlank",
             "AwaitsCapture", "Capture", "InPlayWeapons", "InPlayMechanics"):
    assert re.search(rf"SoraBeatRules::{gate}\b", director), f"The campaign director no longer uses tested beat {gate} rule"
for gate in ("AdvanceChapter", "CampaignLiberated", "CollectibleBit", "CollectiblesValid", "RecordArenaDefeat",
             "RestoreArenaSite", "FinishArena"):
    assert f"SoraCampaignRules::{gate}" in director, f"The campaign director no longer uses tested campaign {gate} gate"
catalog_loader = (ROOT / "Source/SoraArena/Private/SoraCatalog.cpp").read_text()
for gate in ("ChapterValid", "TasksValid"):
    assert f"SoraBeatRules::{gate}" in catalog_loader, f"The catalog loader no longer refuses chapters by {gate}"
# The world-facing director, the horse and the space loader run the same
# host-tested siege and horseback rules.
world = (ROOT / "Source/SoraArena/Private/Game/SoraCampaignDirectorWorld.cpp").read_text()
for gate in ("SoraBeatRules::SiegeDamage", "SoraMountRules::CanMount", "SoraMountRules::ArcAllows", "SoraMountRules::Slower"):
    assert gate in world, f"The campaign director no longer uses tested {gate}"
horse = (ROOT / "Source/SoraArena/Private/Characters/SoraHorse.cpp").read_text()
for gate in ("Step(Ride,Rules", "SoraMountRules::SpeedCmS", "TurnDegS"):
    assert gate in horse or gate.replace("SoraMountRules::", "") in horse, f"The horse no longer rides by tested {gate}"
space_loader = (ROOT / "Source/SoraArena/Private/SoraCatalogSpace.cpp").read_text()
assert "HorseValid(M.Rules)" in space_loader, "The space loader no longer refuses an invalid horse"
# The hero records the stance and recovery lessons; his defense, the guard and parry lessons.
character = ((ROOT / "Source/SoraArena/Private/Characters/SoraPlayerCharacter.cpp").read_text() +
             (ROOT / "Source/SoraArena/Private/Combat/SoraDefense.cpp").read_text())
for action in ("Stance", "Guard", "Parry", "Recovery"):
    assert f"SoraDojoRules::EAction::{action}" in character

TYPES = {"cinematic": "Cinematic", "dialogue": "Dialogue", "combat_wave": "CombatWave", "duel": "Duel",
         "stealth_zone": "StealthZone", "production_task": "ProductionTask", "horseback_ride": "HorsebackRide",
         "boss": "Boss", "explore_optional": "ExploreOptional", "collectible": "Collectible"}
TASKS = {None: "None", "hold": "Hold", "crank": "Crank", "escort": "Escort", "carry": "Carry",
         "manufacture": "Manufacture", "defend": "Defend"}
GOALS = {"elapsed": "Elapsed", "lines": "Lines", "waves_cleared": "WavesCleared", "objectives": "Objectives",
         "survive": "Survive", "points": "Points", "lessons": "Lessons", "opponent_down": "OpponentDown",
         "exit": "Exit", "hold": "Hold", "turns": "Turns", "escort": "Escort", "deliveries": "Deliveries",
         "steps": "Steps", "cache": "Cache", "found": "Found"}
TRIGGERS = {"start": "Start", "prev_cleared": "PrevCleared", "alive_below": "AliveBelow", "after_ms": "AfterMs",
            "progress_at": "ProgressAt", "volume": "Volume", "event": "Event"}
CONTESTS = {"none": "None", "pause": "Pause", "decay": "Decay"}
LOSSES = {"checkpoint": "Checkpoint", "retry": "Retry", "continue_after": "ContinueAfter"}
DETECTIONS = {"combat": "Combat", "restart": "Restart", "reinforce": "Reinforce"}
DEFEATS = {"kill": "Kill", "spare": "Spare", "capture": "Capture"}
FAILURES = {"player_died": "PlayerDied", "match_lost": "MatchLost", "target_destroyed": "TargetDestroyed",
            "escort_down": "EscortDown", "convoy_lost": "ConvoyLost", "detected": "Detected",
            "horse_down": "HorseDown", "boss_event": "BossEvent"}


def mask(bits):
    value = 0
    for bit in bits:
        assert 0 <= bit < 32 and not value & (1 << bit)
        value |= 1 << bit
    return value


def phase_checkpoints(chapter, beat):
    return sum(1 for row in chapter["checkpoints"] if row["beat"] == beat["id"] and row["phase"] > 0)


def flag(value):
    return "true" if value else "false"


def task_fields(task):
    """C++ assignments that set an FTask T to the authored task (defaults omitted)."""
    fields = [f"T.Type = EType::{TYPES[task['type']]};", f"T.Task = ETask::{TASKS[task['task']]};",
              f"T.Goal = EGoal::{GOALS[task['goal']]};"]
    scalars = (("Count", "count", 0), ("DurationMs", "duration_ms", 0), ("MaxAlive", "max_alive", 6),
               ("LossLimit", "loss_limit", 0), ("DecayPermille", "decay_permille", 0),
               ("MinTurnMs", "min_turn_ms", 0), ("MaxTurnMs", "max_turn_ms", 0), ("SpeedCmS", "speed_cm_s", 0),
               ("WaitCm", "wait_cm", 0), ("PathCm", "path_cm", 0), ("ReinforceWave", "reinforce_wave", -1),
               ("CarrySpeedPermille", "carry_speed_permille", 1000), ("TargetLossLimit", "target_loss_limit", 0), ("PickupHoldMs", "pickup_hold_ms", 0))
    for name, key, default in scalars:
        if task[key] != default:
            fields.append(f"T.{name} = {task[key]};")
    for name, key in (("Skippable", "skippable"), ("AnchorAfterLines", "anchor_after_lines"),
                      ("PauseWhenSeen", "pause_when_seen"), ("DropOnHit", "drop_on_hit"),
                      ("HorseDownRetries", "horse_down_retries"), ("FlankBouts", "flank_bouts")):
        if task[key]:
            fields.append(f"T.{name} = true;")
    if task["lesson_mask"]:
        fields.append(f"T.LessonMask = {task['lesson_mask']}u;")
    if task["equipment_weapons"] is not None:
        fields.append(f"T.EquipmentMask = {mask(task['equipment_weapons'])}u;")
    if recovery := task["recovery"]:
        fields.append(f"T.RecoveryWeapons = {mask(recovery['weapons'])}u;")
        for member, key in (("RecoveryDepthCm", "depth_cm"), ("RecoveryStringMs", "string_ms"), ("RecoveryQuiver", "quiver")):
            fields.append(f"T.{member} = {recovery[key]};")
    if maai := task["maai"]:
        for member, key in (("InnerCm", "inner_cm"), ("OuterCm", "outer_cm"), ("HoldMs", "hold_ms"),
                            ("FacingPermille", "facing_permille"), ("HintMs", "hint_ms")):
            fields.append(f"T.Maai.{member} = {maai[key]};")
        fields.append(f"T.Maai.Count = {len(maai['moves'])};")
        for index, move in enumerate(maai["moves"]):
            fields.append(f"T.Maai.Moves[{index}] = {{{move['forward_cm']}, {move['right_cm']}}};")
    for form, reps in enumerate(task["form_reps"]):
        if reps != 1:
            fields.append(f"T.FormReps[{form}] = {reps};")
    assert (task["defeat"] == "capture") == (task["capture_event"] is not None)
    fields.append(f"T.Defeat = EDefeat::{DEFEATS[task['defeat']]};")
    fields.append(f"T.Loss = ELoss::{LOSSES[task['loss']]}; T.Contest = EContest::{CONTESTS[task['contest']]};")
    fields.append(f"T.OnDetected = EDetected::{DETECTIONS[task['on_detected']]};")
    fields.append(f"T.WaveCount = {len(task['waves'])};")
    for index, wave in enumerate(task["waves"]):
        fields.append(f"T.Waves[{index}] = {{EWaveTrigger::{TRIGGERS[wave['trigger']]}, {wave['value']}, "
                      f"{wave['lethal']}, {wave['nonlethal']}}};")
    fields.append(f"T.PhaseCount = {len(task['phases'])};")
    for index, start in enumerate(task["phases"]):
        fields.append(f"T.PhaseStart[{index}] = {start};")
    fields.append(f"T.Pickups = {len(task['pickups'])}; T.Dropoffs = {len(task['dropoffs'])};")
    fields.append(f"T.StepCount = {len(task['steps'])};")
    for index, step in enumerate(task["steps"]):
        fields.append(f"T.Steps[{index}] = {{{step['count']}, {step['beat_ms']}, {step['tolerance_ms']}}};")
    fields.append(f"T.TargetCount = {len(task['targets'])};")
    for index, target in enumerate(task["targets"]):
        fields.append(f"T.TargetHp[{index}] = {target['hp']};")
    if task["carry_weapons"]:
        fields.append(f"T.CarryWeaponsMask = {mask(task['carry_weapons'])}u;")
    failures = " | ".join(f"FailBit(EFail::{FAILURES[name]})" for name in task["fail_checkpoint"]) or "0u"
    fields.append(f"T.FailMask = {failures};")
    return fields


lines = ["static constexpr FChapterFixture Chapters[] = {"]
tasks = []
beat_ids = []
for number, chapter in enumerate(chapters):
    index = {beat["id"]: position for position, beat in enumerate(chapter["beats"])}
    assert len(index) <= 32
    rows = []
    tasks.append(f"static void Chapter{number + 1}Tasks(FTask* Tasks)\n{{")
    for position, beat in enumerate(chapter["beats"]):
        unlocks = beat["unlocks"]
        fields = (
            f'{mask(index[prior] for prior in beat["requires"])}u',
            str(-1 if beat["site"] is None else beat["site"]),
            f'{mask(unlocks["weapons"])}u',
            f'{mask(unlocks["grants"])}u',
            f'{mask(mechanic_bits[name] for name in unlocks["mechanics"])}u',
            f'{mask(flag_bits[name] for name in unlocks["story_flags"])}u',
            flag(beat["optional"]),
            flag(beat["checkpoint"]),
            str(phase_checkpoints(chapter, beat)),
        )
        rows.append("        {" + ", ".join(fields) + "},  // " + beat["id"] + " " + beat["type"])
        tasks.append(f"    {{  // {beat['id']} {beat['type']}\n        FTask& T = Tasks[{position}];")
        tasks.extend("        " + field for field in task_fields(beat["task"]))
        tasks.append("    }")
    tasks.append("}")
    lines.append("    {" + str(len(rows)) + ", {")
    lines.extend(rows)
    lines.append("    }},")
    beat_ids.append("    {" + ", ".join(f'"{beat["id"]}"' for beat in chapter["beats"]) + "},")
lines.append("};")
lines.extend(tasks)
lines.append("static void (*const ChapterTasks[])(FTask*) = {" +
             ", ".join(f"Chapter{number + 1}Tasks" for number in range(len(chapters))) + "};")
lines.append("static const char* const BeatIds[][MaxBeats] = {")
lines.extend(beat_ids)
lines.append("};")
# §11: each weapon with the chapter and beat index that first unlocks it.
unlock_rows = []
for weapon, beat_id in WEAPON_UNLOCKS:
    chapter = int(beat_id[2:4]) - 1
    position = [beat["id"] for beat in chapters[chapter]["beats"]].index(beat_id)
    unlock_rows.append(f"{{{weapon}, {chapter}, {position}}}")
lines.append(f"static constexpr int UnlockOrder[][3] = {{{', '.join(unlock_rows)}}};")

# Every horse a ride or mounted boss puts under the hero (the space's mount
# blocks, campaign_space.py), with its route length and gait caps, so the
# driver can ride each one at its best pace.
GAIT_NAMES = ("halt", "walk", "trot", "canter", "gallop")
ride_rows = []
for chapter in chapters:
    zones = chapter["space"]["zones"]
    for beat, record in zip(chapter["beats"], chapter["space"]["beats"]):
        mount = record["mount"]
        if not mount:
            continue
        top = max(GAIT_NAMES.index(gait) for gait in mount["gaits"])
        per_s = mount["stamina"]["per_s"]
        slots = {0: 0, 18: 1, 19: 2}
        arc_min, arc_max = [0, 0, 0], [0, 0, 0]
        for weapon, arc in mount["arcs"].items():
            arc_min[slots[int(weapon)]], arc_max[slots[int(weapon)]] = arc
        horse = (f"{{EGait::{GAIT_NAMES[top].capitalize()}, {{0, {', '.join(map(str, mount['speeds_cm_s']))}}}, "
                 f"{{{per_s[0]}, {', '.join(map(str, per_s))}}}, {mount['stamina']['lockout']}, "
                 f"{mount['stamina']['recover']}, {mount['fear']['recover_ms'] if mount['fear'] else 0}, "
                 f"{mask(mount['weapons'])}u, {{{', '.join(map(str, arc_min))}}}, {{{', '.join(map(str, arc_max))}}}}}")
        length = 0
        if record["route"] is not None:
            route = zones[record["zone"]]["route"]
            length = round(sum(((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5 for a, b in zip(route, route[1:])))
        caps = [f"{{{cap['from_cm']}, {cap['to_cm']}, EGait::{cap['gait'].capitalize()}}}" for cap in mount["gait_caps"]]
        caps += ["{0, 0, EGait::Halt}"] * (4 - len(caps))
        assert len(caps) == 4
        ride_rows.append(f'    {{"{beat["id"]}", {horse}, {length}, {beat["target_s"] * 1000}, '
                         f'{len(mount["gait_caps"])}, {{{", ".join(caps)}}}, {"true" if mount["mounted"] else "false"}, '
                         f'{len(mount["tack"])}}},')
lines.append("static const FRideFixture Rides[] = {")
lines.extend(ride_rows)
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
