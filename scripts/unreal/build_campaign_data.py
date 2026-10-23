"""Build the offline campaign's chapter files from the chapter scripts.

Each docs/campaign/chapter-0N.md carries exactly one ```yaml block written to
the story bible's beat taxonomy (§12.1, §12.2) and chapter-YAML conventions
(§12.5). This importer turns block N into Content/Data/campaign/chapter_0N.json,
catalog schema 4:

- ``beats``: the §12.1 common fields, always present with fixed JSON types
  (defaults materialized), the §12.2 type-specific fields under ``params``,
  and every ``x_`` proposal, without its prefix, under ``ext``.
- ``lines``: every voiced line once, with speaker id, duration, and the
  register mapped to its §18 family (the alias's delivery note is kept).
- ``triggers``: the one table that schedules lines. Beat dialogue entries,
  dialogue beats, boss and duel barks, cinematic subtitles and the chapter
  bark pools all become ``{beat, on, mode, lines}`` rows keyed by event.
- ``collectibles``, ``ui_prompts``, ``checkpoints``, ``unlocks``, ``places``
  (from the bible's §14 table) and ``layout`` (volumes, points, splines and
  patrols in integer centimetres, in the frame the chapter authored).
- ``space``: the playable layout campaign_space.py derives from the places,
  beats and tasks (zones, route corridors, sites, and every beat's points,
  volumes, spawns, patrols, camera and horse) in one world frame.

The chapter title card and the production-site labels are not in the scripts;
they live in the hand-authored Content/Data/campaign/campaign.json.
``validate_content.py`` applies the bible's §12.3 rules to the output and
checks that the committed files equal a fresh build.

Usage: ``python3 scripts/unreal/build_campaign_data.py`` writes the files;
``--check`` exits nonzero when a committed file differs from a fresh build.
Requires PyYAML (pinned in scripts/requirements.txt).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml
from campaign_crank import cooperation, player_work

from campaign_space import derive_space, ride_mount
from campaign_registry import validate_registry

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs/campaign"
BIBLE = DOCS / "story-bible.md"
OUTPUT = ROOT / "Content/Data/campaign"
SCHEMA_VERSION = 4
CHAPTER_COUNT = 8

BEAT_TYPES = ("combat_wave", "duel", "stealth_zone", "production_task", "horseback_ride",
              "boss", "dialogue", "explore_optional", "collectible", "cinematic")
COMMON_KEYS = ("id", "type", "place", "title_ja", "title_en", "target_s", "checkpoint", "requires",
               "optional", "unlocks", "site", "registry", "dialogue", "music", "fail")
# §12.2 required and optional parameters per beat type. The wave companions
# (max_alive, allies, nonlethal_types) travel with any beat that spawns waves,
# and a production task run under stealth takes the stealth detection fields.
WAVE_COMPANIONS = ("waves", "max_alive", "allies", "nonlethal_types")
PARAMS = {
    "combat_wave": (("bounds", "waves", "complete"),
                    ("max_alive", "allies", "nonlethal_types", "target_kind")),
    "duel": (("opponent", "weapons", "lethal", "scoring", "ring"),
             ("lesson_gates", "finisher", "events", "loss_policy", "checkpoint_per_phase", "barks")),
    "stealth_zone": (("zone", "guards", "on_detected", "complete"),
                     ("detection", "takedowns", "light_sources", "noise_surfaces", "lures",
                      "objectives") + WAVE_COMPANIONS),
    "production_task": (("task",), ("stealth", "detection", "takedowns") + WAVE_COMPANIONS),
    "horseback_ride": (("horse", "mode", "route"),
                       ("complete", "gaits", "weapons", "convoy", "fear", "horse_stamina", "auto_steer",
                        "dismount_allowed", "on_horse_down", "cargo", "objectives") + WAVE_COMPANIONS),
    "boss": (("boss", "arena", "phases", "defeat"),
             ("intro_cinematic", "outro_cinematic", "checkpoint_per_phase", "telegraph", "barks",
              "trigger", "finisher")),
    "dialogue": (("lines", "trigger", "mode"), ("priority", "interrupt", "camera", "volume", "complete")),
    "explore_optional": (("volume", "pois"), ("rewards", "exit_hint_after_s")),
    "cinematic": (("sequence", "duration_s", "skippable", "subtitles"), ("fallback", "end_state")),
}
TASKS = {
    "hold": ("volume", "contest"),
    "escort": ("npcs", "path", "speed_cm_s", "wait_for_player_cm", "fail_on_npc_death"),
    "carry": ("item", "count", "pickups", "dropoffs"),
    "manufacture": ("recipe", "stations", "steps", "output"),
    "defend": ("targets", "fail_on_target_destroyed"),
    "crank": ("actor", "turns_required", "turn_rate_band", "progress_decay_per_s", "stamina_per_turn"),
}
HORSES = ("kurimaru", "arashi", "pack_horse")
RIDE_MODES = ("travel", "escort_convoy", "chase", "charge", "cargo")
DEFEATS = ("kill", "disarm", "destroy_weakpoints", "capture")
# How each boss defeat ends in SoraBeatRules::EDefeat: the machine whose weak
# points break falls; a disarmed boss is spared; a captured one is bound.
BOSS_DEFEATS = {"kill": "kill", "destroy_weakpoints": "kill", "disarm": "spare", "capture": "capture"}
SCORING = ("points", "hp", "lesson_gates")
FINISHERS = ("none", "muto_dori")
TRIGGER_MODES = ("ambient", "blocking", "radio", "bark", "cinematic")
DIALOGUE_BEAT_MODES = ("ambient", "blocking", "radio")
COLLECTIBLE_CATEGORIES = ("scroll_fragment", "seizure_notice", "league_mark", "heirloom", "registry_page")
DEFAULT_NONLETHAL = ["bound_conscript"]
DEFAULT_FAIL = [{"on": "player_died", "to": "checkpoint"}]
# Top-level keys that only document the proposal itself.
DOC_ONLY_KEYS = ("schema", "schema_note", "schema_target", "schema_proposal")
SPEAKER_LIST_KEYS = ("speakers", "speakers_new", "speakers_proposed")

# §18 register families. Every register the scripts use maps to one family; the
# rest of an alias is kept as a delivery note for casting. An unknown register
# stops the build, so each new one gets an explicit decision here.
REGISTER_FAMILIES = (
    "archaic_samurai", "samurai_restrained", "brash_samurai", "humbled_samurai", "young_samurai",
    "elder_samurai", "business_keigo", "terse", "manual_keigo", "kyoto_soft", "kamigata_bright",
    "kamigata_cheerful", "kamigata_commoner", "yamato_elder", "yamato_gruff", "yamato_rural",
    "blunt_artisan", "artisan_gentle", "alien_corporate_keigo", "alien_device", "alien_device_pa",
    "announcement_keigo", "inscription", "proclamation", "child", "work_song",
    # Voices §18 does not name: townsfolk and conscripts, League ashigaru, Okuzu.
    "townsfolk", "ashigaru", "calm_maternal",
)
REGISTER_ALIASES = {
    "mentor_archaic": ("archaic_samurai", None),
    "archaic_memory": ("archaic_samurai", "memory"),
    "jidaigeki_restrained": ("samurai_restrained", None),
    "samurai_plain": ("samurai_restrained", "plain"),
    "samurai_polite": ("samurai_restrained", "polite"),
    "samurai_formal": ("samurai_restrained", "formal"),
    "jidaigeki_plain": ("samurai_restrained", "plain"),
    "jidaigeki_polite": ("samurai_restrained", "polite"),
    "jidaigeki_formal": ("samurai_restrained", "formal"),
    "jidaigeki_raised": ("samurai_restrained", "raised"),
    "jidaigeki_plain_whisper": ("samurai_restrained", "whisper"),
    "samurai_bark": ("samurai_restrained", "bark"),
    "combat_bark": ("samurai_restrained", "bark"),
    "effort_bark": ("samurai_restrained", "effort"),
    "rival_brash": ("brash_samurai", None),
    "rival_clipped": ("brash_samurai", "clipped"),
    "formal_samurai": ("brash_samurai", "formal"),
    "rival_humbled": ("humbled_samurai", None),
    "samurai_brash_humbled": ("humbled_samurai", None),
    "terse_report": ("terse", "report"),
    "scout_terse": ("terse", None),
    "plain_to_crowd": ("business_keigo", "plain"),
    "kyoto_formal": ("kyoto_soft", "formal"),
    "kyoto_raised": ("kyoto_soft", "raised"),
    "kyoto_soft_grief": ("kyoto_soft", "grief"),
    "kyoto_plain_steel": ("kyoto_soft", "plain"),
    "kamigata": ("kamigata_bright", None),
    "kamigata_formal": ("kamigata_bright", "formal"),
    "kamigata_artisan": ("kamigata_commoner", "artisan"),
    "kamigata_townsfolk": ("kamigata_commoner", None),
    "yamato_commoner": ("yamato_rural", None),
    "yamato_rural_distressed": ("yamato_rural", "distressed"),
    "yamato_rural_weak": ("yamato_rural", "weak"),
    "yamato_whisper": ("yamato_rural", "whisper"),
    "gruff_yamato": ("yamato_gruff", None),
    "yamato_gruff_formal": ("yamato_gruff", "formal"),
    "yamato_gruff_quiet": ("yamato_gruff", "quiet"),
    "yamato_gruff_raised": ("yamato_gruff", "raised"),
    "yamato_gruff_strained": ("yamato_gruff", "strained"),
    "kansai_blunt": ("blunt_artisan", None),
    "kansai_blunt_raised": ("blunt_artisan", "raised"),
    "artisan_blunt": ("blunt_artisan", None),
    "artisan_gruff": ("blunt_artisan", "gruff"),
    "blunt": ("blunt_artisan", None),
    "gentle_artisan": ("artisan_gentle", None),
    "alien_corporate": ("alien_corporate_keigo", None),
    "corporate_keigo": ("alien_corporate_keigo", None),
    "alien_corporate_bark": ("alien_corporate_keigo", "bark"),
    "corporate_keigo_bark": ("alien_corporate_keigo", "bark"),
    "alien_corporate_boss": ("alien_corporate_keigo", "boss"),
    "alien_corporate_grenadier": ("alien_corporate_keigo", "grenadier"),
    "alien_corporate_marksman": ("alien_corporate_keigo", "marksman"),
    "alien_corporate_keigo_failing": ("alien_corporate_keigo", "failing"),
    # The two plain-form canon lines staged as register breaks (§18).
    "alien_corporate_plain": ("alien_corporate_keigo", "plain"),
    "plain_condescending": ("alien_corporate_keigo", "plain"),
    "alien_machine": ("alien_device", None),
    "local_colloquial": ("townsfolk", None),
    "local_colloquial_strained": ("townsfolk", "strained"),
    "local_colloquial_whisper": ("townsfolk", "whisper"),
    "townsfolk_compelled": ("townsfolk", "compelled"),
    "townsfolk_elder": ("townsfolk", "elder"),
    "townsfolk_elder_f": ("townsfolk", "elder_f"),
    "townsfolk_elder_m": ("townsfolk", "elder_m"),
    "townsfolk_f": ("townsfolk", "f"),
    "townsfolk_m": ("townsfolk", "m"),
    "townsfolk_mother": ("townsfolk", "mother"),
    "ashigaru_shout": ("ashigaru", "shout"),
    "rough_plain": ("ashigaru", None),
    "calm": ("calm_maternal", None),
}
LINE_KEYS = ("id", "speaker", "ja", "en", "register", "duration_s")
# Line-level scheduling duplicates the beat's dialogue entries (§12.5) and is dropped.
LINE_SCHEDULE_KEYS = ("beat", "on", "trigger")
# Lesson gates that name a dojo form, in SoraDojoRules order.
LESSON_FORMS = {"stance_hold": 0, "front_guard_survive": 1, "awase": 2, "recovery_complete": 3}
# `fail` events and the SoraBeatRules::EFail each one raises.
FAIL_EVENTS = (
    (r"player_died", "player_died"), (r"match_lost", "match_lost"), (r"target_destroyed", "target_destroyed"),
    (r"npc_died:\w+", "escort_down"), (r"convoy_member_(seized|hp0)", "convoy_lost"),
    (r"boss_event:\w+", "boss_event"),
)
# A boss's intro or outro cue timed inside its sequence (ch02.b15).
BOSS_CUE = re.compile(r"(intro|outro)@(\d+(?:\.\d+)?)")
# Proposed events (ch03's x_ names) the runtime raises under its own name:
# a wave's start, the boss's fall and an objective worked (the director); the
# hero's signal to an escorted party, a downed member raised, one freed, and a
# searching guard giving up (USoraFieldcraft and the guards' cues).
RAISED_PROPOSALS = {"x_wave_start": "wave_start", "x_boss_defeated": "boss_defeated", "x_objective": "interact",
                    "x_signal": "signal", "x_npc_revived": "npc_revived", "x_npc_freed": "npc_freed",
                    "x_alert_state": "alert_state", "x_fire_out": "fire_out", "x_item_picked": "item_picked"}
# A dialogue trigger may wait for a collectible found or a story flag set.
REQUIRES_FLAG = re.compile(r"(collectible:ch0[1-8]\.c0[1-6]|story:[a-z_]+)")


class BuildError(ValueError):
    pass


def fail(context, message):
    raise BuildError(f"{context}: {message}")


class StrictLoader(yaml.SafeLoader):
    """PyYAML's safe loader, rejecting duplicate mapping keys instead of keeping the last."""


def _strict_mapping(loader, node, deep=False):
    keys = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in keys:
            raise BuildError(f"duplicate YAML key {key!r} at line {key_node.start_mark.line + 1}")
        keys.add(key)
    return loader.construct_mapping(node, deep=deep)


StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _strict_mapping)


def check_json_value(value, context):
    """Allow only JSON types with string keys: no YAML dates, no boolean keys from a bare `on`."""
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                fail(context, f"non-string key {key!r} (quote YAML keys such as \"on\")")
            check_json_value(item, f"{context}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            check_json_value(item, f"{context}[{index}]")
    elif isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            fail(context, "non-finite number")
    elif not isinstance(value, (str, int, type(None))):
        fail(context, f"unsupported YAML value {value!r}")


def load_chapter_yaml(number):
    path = DOCS / f"chapter-{number:02d}.md"
    blocks = re.findall(r"^```yaml\n(.*?)^```", path.read_text(), re.S | re.M)
    if len(blocks) != 1:
        fail(path.name, f"expected one yaml block, found {len(blocks)}")
    document = yaml.load(blocks[0], Loader=StrictLoader)
    if not isinstance(document, dict):
        fail(path.name, "the yaml block is not a mapping")
    check_json_value(document, path.name)
    return document


def load_places():
    """The bible's §14 place table: id -> {ja, reading, en, arena, source}."""
    places = {}
    row = re.compile(r"^\| ([1-8]) \| (pl_[a-z_]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \|[^|]*\|$")
    for line in BIBLE.read_text().splitlines():
        match = row.match(line)
        if not match:
            continue
        chapter, place, japanese, english, source = (part.strip() for part in match.groups())
        reading = re.fullmatch(r"(.+?) \((.+)\)", japanese)
        arena = re.search(r"Arena (\d)", source)
        if place in places:
            fail("story-bible §14", f"place {place} listed twice")
        places[place] = {
            "id": place,
            "chapter": int(chapter),
            "ja": reading.group(1) if reading else japanese,
            "reading": reading.group(2) if reading else None,
            "en": english,
            "arena": int(arena.group(1)) if arena else None,
            # A bold "**Arena N**" row is the arena itself, not a space beside it.
            "hub": source.startswith("**Arena "),
            "source": source.replace("**", "").replace("`", ""),
        }
    table = BIBLE.read_text().split("## 14. Places and levels", 1)[1].split("\n## ", 1)[0]
    listed = len(re.findall(r"^\| [1-8] \| pl_", table, re.M))
    if len(places) != listed:
        fail("story-bible §14", f"parsed {len(places)} of {listed} place rows")
    return places


def expect(value, kinds, context):
    if isinstance(value, bool) and bool not in kinds:
        fail(context, f"expected {kinds}, got a boolean")
    if not isinstance(value, kinds):
        fail(context, f"expected {kinds}, got {value!r}")
    return value


def expect_int(value, context, minimum=None):
    expect(value, (int,), context)
    if minimum is not None and value < minimum:
        fail(context, f"{value} is below {minimum}")
    return value


def expect_enum(value, options, context):
    if value not in options:
        fail(context, f"{value!r} is not one of {options}")
    return value


def expect_ids(value, context):
    expect(value, (list,), context)
    for item in value:
        expect(item, (str,), context)
    return value


def strip_ext(raw, context):
    """Beat or chapter proposals: x_key -> key, plus ch05's grouped x_ext block."""
    ext = {}
    for key, value in raw.items():
        if key == "x_ext":
            expect(value, (dict,), f"{context}.x_ext")
            for inner, item in value.items():
                if inner in ext:
                    fail(context, f"proposal {inner} given twice")
                ext[inner] = item
        elif key.startswith("x_"):
            name = key[2:]
            if name in ext:
                fail(context, f"proposal {name} given twice")
            ext[name] = value
    return ext


def event_list(value, context):
    """`on` fields: an event string, `a|b` alternatives split in authored order."""
    expect(value, (str,), context)
    events = value.split("|")
    if any(not event or event != event.strip() for event in events):
        fail(context, f"malformed event {value!r}")
    return events


def normalize_fail(value, context):
    if value is None:
        return [dict(entry) for entry in DEFAULT_FAIL]
    entries = value if isinstance(value, list) else [value]
    result = []
    for index, entry in enumerate(entries):
        where = f"{context}[{index}]"
        expect(entry, (dict,), where)
        if set(entry) != {"on", "to"}:
            fail(where, f"fail entries take on and to, got {sorted(entry)}")
        expect(entry["to"], (str,), where)
        if entry["on"] == "none":
            if entry["to"] != "none" or len(entries) != 1:
                fail(where, "`none` must be the only fail entry and go nowhere")
            return []
        for event in event_list(entry["on"], where):
            result.append({"on": event, "to": entry["to"]})
    return result


def normalize_complete(value, context, beat_type, params):
    """Beat completion as {kind, ...}."""
    if value is None:
        if beat_type == "horseback_ride" and params.get("mode") == "cargo":
            return {"kind": "cargo_delivered"}
        fail(context, "completion is required")
    if isinstance(value, str):
        if value == "all_waves_cleared":
            return {"kind": "all_waves_cleared"}
        if value == "exit_reached":
            return {"kind": "exit_reached", "volume": None}
        if value == "objectives":
            if "objectives" not in params:
                fail(context, "completion by objectives lists none")
            return {"kind": "objectives"}
        kind, _, argument = value.partition(":")
        if kind == "volume_enter" and argument:
            return {"kind": "volume_enter", "volume": argument}
        if kind == "event" and argument:
            return {"kind": "event", "event": argument}
        fail(context, f"unknown completion {value!r}")
    expect(value, (dict,), context)
    if set(value) == {"reach", "dismount"}:
        return {"kind": "reach", "volume": expect(value["reach"], (str,), context),
                "dismount": expect(value["dismount"], (bool,), context)}
    if set(value) == {"volume_enter"}:
        return {"kind": "volume_enter", "volume": expect(value["volume_enter"], (str,), context)}
    if set(value) == {"exit_reached"}:
        return {"kind": "exit_reached", "volume": expect(value["exit_reached"], (str,), context)}
    if set(value) == {"objectives"}:
        expect(value["objectives"], (list,), context)
        return {"kind": "objectives", "objectives": value["objectives"]}
    if set(value) == {"survive_s"}:
        return {"kind": "survive_s", "seconds": expect_int(value["survive_s"], context, 1)}
    if set(value) == {"defeat_count"}:
        return {"kind": "defeat_count", "count": expect_int(value["defeat_count"], context, 1)}
    fail(context, f"unknown completion {value!r}")


def normalize_waves(waves, context):
    expect(waves, (list,), context)
    for index, wave in enumerate(waves):
        where = f"{context}[{index}]"
        expect(wave, (dict,), where)
        expect(wave.get("trigger"), (str,), f"{where}.trigger")
        expect(wave.get("enemies"), (list,), f"{where}.enemies")
        for enemy_index, enemy in enumerate(wave["enemies"]):
            spot = f"{where}.enemies[{enemy_index}]"
            expect(enemy, (dict,), spot)
            expect(enemy.get("type"), (str,), f"{spot}.type")
            expect_int(enemy.get("count"), f"{spot}.count", 1)
            expect(enemy.get("spawn"), (str,), f"{spot}.spawn")
    return waves


def normalize_production(raw, context):
    """Return (task, block) with the task's §12.2 block checked."""
    task = expect_enum(raw["task"], tuple(TASKS), f"{context}.task")
    block = raw.get(task)
    if block is None:
        # ch01.b09 wrote its manufacture block flat on the beat.
        block = {key: raw[key] for key in TASKS[task] if key in raw}
        extra = [key for key in raw if key in TASKS[task]]
        if len(extra) != len(TASKS[task]):
            fail(context, f"{task} block missing")
        for key in extra:
            del raw[key]
    elif isinstance(block, dict):
        del raw[task]
    else:
        fail(context, f"{task} block must be a mapping")
    missing = [key for key in TASKS[task] if key not in block]
    if missing:
        fail(context, f"{task} block lacks {missing}")
    if task == "hold":
        if "hold_s" not in block and not ("interact_points" in block and "per_point_s" in block):
            fail(context, "hold needs hold_s or interact_points with per_point_s")
        expect_enum(block["contest"], ("pause", "decay"), f"{context}.hold.contest")
        if block["contest"] == "decay" and "decay_per_s" not in block:
            fail(context, "decaying hold needs decay_per_s")
    if task == "defend" and "duration_s" not in block and "waves" not in raw:
        fail(context, "defend needs duration_s or waves")
    if task == "crank":
        band = expect(block["turn_rate_band"], (list,), f"{context}.crank.turn_rate_band")
        if len(band) != 2 or not 0 < band[0] < band[1]:
            fail(context, f"turn_rate_band {band} must be [min, max] turns/s")
        expect_int(block["turns_required"], f"{context}.crank.turns_required", 1)
    if task == "carry":
        expect_int(block["count"], f"{context}.carry.count", 1)
    return task, block


def whole_ms(seconds, context):
    """Seconds to integer milliseconds, refusing sub-millisecond data."""
    expect(seconds, (int, float), context)
    value = round(seconds * 1000)
    if seconds < 0 or abs(seconds * 1000 - value) > 1e-6:
        fail(context, f"{seconds!r} s is not a whole number of milliseconds")
    return value


def permille(fraction, context):
    """A 0-1 fraction to integer permille, refusing finer data."""
    expect(fraction, (int, float), context)
    value = round(fraction * 1000)
    if not 0 <= fraction <= 1 or abs(fraction * 1000 - value) > 1e-6:
        fail(context, f"{fraction!r} is not a fraction in whole permille")
    return value


def task_wave(wave, nonlethal, context):
    """A wave as SoraBeatRules reads it: trigger, value, and its spawn groups in order."""
    trigger = wave["trigger"]
    kind, _, argument = trigger.partition(":")
    value, event = 0, None
    if trigger in ("start", "prev_cleared"):
        kind = trigger
    elif kind == "alive_below" and argument.isdigit():
        value = expect_int(int(argument), f"{context}.trigger", 1)
    elif kind == "after_s" and argument:
        value = whole_ms(float(argument), f"{context}.trigger")
        kind = "after_ms"
    elif kind == "progress_at" and argument:
        value = permille(float(argument), f"{context}.trigger")
    elif kind == "volume_enter" and argument:
        kind, event = "volume", trigger
    else:
        # Alarms, detection and scripted events: a reinforcement that may never come.
        kind, event = "event", trigger
    # A scripted opponent the wave marks invulnerable (ch08.b02's sweep-only walkers).
    members = [{"type": enemy["type"], "count": enemy["count"], "lethal": enemy["type"] not in nonlethal,
                "invulnerable": expect(enemy.get("invulnerable", False), (bool,), f"{context}.invulnerable")}
               for enemy in wave["enemies"]]
    return {"id": wave.get("id"), "trigger": kind, "value": value, "event": event, "members": members,
            "lethal": sum(member["count"] for member in members if member["lethal"]),
            "nonlethal": sum(member["count"] for member in members if not member["lethal"])}


STATIC_SCAN = re.compile(r"static:\w+:scan_(\d+)deg_(\d+)s")


def guard_row(guard, count_context):
    """A guard as the zone posts it: its archetype, the senses the script
    authors for it (sight {range_cm, dark_range_cm, cone_deg}, hearing_cm and
    x_suspicion_mult; 0 (sight, cone, suspicion) or -1 (dark sight, hearing)
    keeps the archetype's own, Content/Data/enemies.json), and how it watches:
    a post it keeps (a static patrol or a post) rather than a round, the arc
    it sweeps there and how long a sweep takes (x_scan_arc_deg and
    x_scan_period_s, scan {sweep_deg, every_s}, a static patrol's
    scan_<deg>deg_<s>s), or how often it turns about (x_turn_every_s)."""
    sight = expect(guard.get("sight") or {}, (dict,), f"{count_context}.sight")
    mult = guard.get("x_suspicion_mult")
    patrol = guard.get("patrol") if isinstance(guard.get("patrol"), str) else ""
    scan = expect(guard.get("scan") or {}, (dict,), f"{count_context}.scan")
    static = STATIC_SCAN.fullmatch(patrol)
    arc = guard.get("x_scan_arc_deg", scan.get("sweep_deg", int(static.group(1)) if static else 0))
    period = guard.get("x_scan_period_s", scan.get("every_s", int(static.group(2)) if static else 0))
    watch = {"post": patrol.startswith("static:") or "post" in guard,
             "scan_deg": expect_int(arc, f"{count_context}.scan arc", 0),
             "scan_ms": whole_ms(period, f"{count_context}.scan period"),
             "turn_ms": whole_ms(guard.get("x_turn_every_s", 0), f"{count_context}.x_turn_every_s")}
    if (watch["scan_deg"] > 0) != (watch["scan_ms"] > 0) or ((watch["scan_deg"] or watch["turn_ms"]) and not watch["post"]):
        fail(count_context, f"a guard sweeps or turns only at its post: {watch}")
    return {"type": expect(guard["type"], (str,), count_context), **watch,
            "sight_cm": expect_int(sight.get("range_cm", 0), f"{count_context}.sight.range_cm", 0),
            "dark_sight_cm": expect_int(sight.get("dark_range_cm", -1), f"{count_context}.sight.dark_range_cm", -1),
            "view_deg": expect_int(sight.get("cone_deg", 0), f"{count_context}.sight.cone_deg", 0),
            "hearing_cm": expect_int(guard.get("hearing_cm", -1), f"{count_context}.hearing_cm", -1),
            "suspicion_permille": 0 if mult is None else permille(mult, f"{count_context}.x_suspicion_mult")}


def stealth_block(beat, where):
    """A stealth zone's, or guarded work's, authored rules (bible §12.2):
    detection {suspicion_rate, suspicious_at, search_s, wary_after_search},
    takedowns {rear, lethal_default}, x_bodies {discoverable, drag} and
    x_on_detected_carryover, with the defaults SoraStealthRules::Watchful()
    names where the script gives none."""
    params, ext = beat["params"], beat["ext"]
    detection = expect(params.get("detection") or {}, (dict,), f"{where}.detection")
    takedowns = expect(params.get("takedowns") or {}, (dict,), f"{where}.takedowns")
    bodies = expect(ext.get("bodies") or {}, (dict,), f"{where}.x_bodies")
    if detection.get("alert_threshold", 1.0) != 1.0:
        fail(where, "a guard is alert only at the full meter (alert_threshold 1.0)")
    if bodies.get("drag_speed_mult", 0.5) != 0.5:
        fail(where, "a body is dragged at half pace (SoraStealthRules::DragSpeedPermille)")
    wary = (detection.get("wary_after_search") or {}).get("suspicion_rate_mult", 1.2)
    expect(wary, (int, float), f"{where}.detection.wary_after_search")
    if not 1 <= wary <= 4 or abs(wary * 1000 - round(wary * 1000)) > 1e-6:
        fail(where, f"wary_after_search {wary} is not a whole-permille multiplier from 1 to 4")
    rate = expect(detection.get("suspicion_rate", 1.0), (int, float), f"{where}.detection.suspicion_rate")
    if not 0.1 <= rate <= 4 or abs(rate * 1000 - round(rate * 1000)) > 1e-6:
        fail(where, f"suspicion_rate {rate} is not a whole-permille rate from 0.1 to 4")
    carry = ext.get("on_detected_carryover")
    if carry is not None and (carry.get("start_state") != "suspicious" or not isinstance(carry.get("beat"), str)):
        fail(where, f"on_detected_carryover {carry} must start a later beat's guards suspicious")
    return {"rate_permille": round(rate * 1000),
            "suspicious_at_permille": permille(detection.get("suspicious_at", 0.25), f"{where}.detection.suspicious_at"),
            "search_ms": whole_ms(detection.get("search_s", 12), f"{where}.detection.search_s"),
            "wary_permille": round(wary * 1000),
            "rear_takedowns": expect(takedowns.get("rear", True), (bool,), f"{where}.takedowns.rear"),
            "lethal_default": expect(takedowns.get("lethal_default", False), (bool,), f"{where}.takedowns.lethal_default"),
            "bodies": expect(bodies.get("discoverable", True), (bool,), f"{where}.x_bodies.discoverable"),
            "drag": expect(bodies.get("drag", True), (bool,), f"{where}.x_bodies.drag"),
            "carryover_to": carry["beat"] if carry else None}


def ids_of(rows, context):
    """Point ids from a list of ids or of {id: ...} rows."""
    result = []
    for index, row in enumerate(expect(rows, (list,), context)):
        result.append(expect(row["id"] if isinstance(row, dict) else row, (str,), f"{context}[{index}]"))
    if len(set(result)) != len(result):
        fail(context, f"duplicate ids {result}")
    return result


def volume_event(volume):
    return None if volume is None else f"volume_enter:{volume}"


def maai_lesson(raw, count, where):
    """Integer runtime parameters for the authored distance-and-facing lesson."""
    raw = expect(raw, (dict,), where)
    keys = {"weapon_range_cm", "ring_inner_cm", "ring_outer_cm", "hold_ms", "facing_dot_min", "hint_after_s", "mentor_moves"}
    if set(raw) != keys or not 1 <= count <= 8:
        fail(where, "maai requires its complete distance, timing and mentor-step contract")
    inner = expect_int(raw["ring_inner_cm"], where, 1)
    outer = expect_int(raw["ring_outer_cm"], where, 1)
    reach = expect_int(raw["weapon_range_cm"], where, 1)
    hold = expect_int(raw["hold_ms"], where, 1)
    facing = permille(raw["facing_dot_min"], where)
    hint = whole_ms(raw["hint_after_s"], where)
    if not inner < reach < outer <= 1000 or not 1 <= hold <= 10000 or not 1 <= facing <= 1000 or not 1 <= hint <= 60000:
        fail(where, "invalid maai distance, facing or timing")
    moves = expect(raw["mentor_moves"], (list,), where)
    if len(moves) != count:
        fail(where, "each maai confirmation needs its own mentor step")
    result = []
    directions = {"back": (-1, 0), "forward": (1, 0), "left": (0, -1), "right": (0, 1)}
    for index, move in enumerate(moves):
        expect(move, (dict,), where)
        if set(move) != {"step", "move", "cm"}:
            fail(where, "mentor step requires step, move and cm")
        if expect_int(move["step"], where, 1) != index + 1 or expect(move["move"], (str,), where) not in directions:
            fail(where, "mentor steps must be consecutive and have a known direction")
        cm = expect_int(move["cm"], where, 1)
        if cm > 500:
            fail(where, "mentor step exceeds the lesson space")
        forward, right = directions[move["move"]]
        result.append({"forward_cm": forward * cm, "right_cm": right * cm})
    return {"inner_cm": inner, "outer_cm": outer, "hold_ms": hold, "facing_permille": facing, "hint_ms": hint, "moves": result}


def carry_drop_policy(value, where):
    """Preserve all authored difficulty values, including uniform booleans."""
    names = ("easy", "normal", "hard")
    if isinstance(value, bool):
        return dict.fromkeys(names, value)
    expect(value, (dict,), where)
    if set(value) != set(names):
        fail(where, "drop_on_hit requires exactly easy, normal and hard")
    return {name: expect(value[name], (bool,), f"{where}.{name}") for name in names}


def carry_dropoff_capacity(raw, names, count, where):
    """Preserve an authored name-to-capacity map, never dictionary order."""
    expect(raw, (dict,), where)
    expect_int(count, f"{where}.count", 1)
    if count > 99 or not 1 <= len(names) <= 8 or any(not name for name in names) or len(set(names)) != len(names):
        fail(where, "carry count must be 1-99 with 1-8 unique drop-offs")
    if set(raw) != set(names):
        fail(where, "capacity keys must exactly match the named drop-offs")
    capacities = {name: expect_int(raw[name], f"{where}.{name}", 1) for name in names}
    if any(value > 99 for value in capacities.values()) or sum(capacities.values()) < count:
        fail(where, "capacities must be 1-99 and hold all required goods")
    return capacities


def carry_gate(raw, where):
    if raw is None:
        return None
    expect(raw, (dict,), where)
    points = ids_of(raw.get("interact_points"), where)
    if len(points) != 1 or raw.get("contest") != "pause" or raw.get("tool") != "yari_ishizuki":
        fail(where, "carry gate requires one seal, pause on hit and the yari iron butt")
    hold = whole_ms(raw.get("per_point_s"), where)
    if hold <= 0:
        fail(where, "carry gate hold must be positive")
    return {"point": points[0], "hold_ms": hold, "contest": "pause", "tool": "yari_ishizuki"}


def normalize_task(beat):
    """The beat's task in the integer units SoraBeatRules.h runs (§12.2).

    Every beat gets the same keys; its goal says which of them matter. Times
    are milliseconds, fractions permille and distances centimetres. The loader
    in SoraCatalog.cpp reads this block and the host driver plays it."""
    where, kind, params = beat["id"], beat["type"], beat["params"]
    complete = params.get("complete") or {}
    task = {
        "type": kind, "task": params.get("task"), "goal": None, "count": 0, "duration_ms": 0, "skippable": False,
        "anchor_after_lines": False, "pause_when_seen": params.get("stealth") is True,
        "max_alive": params.get("max_alive", 6), "waves": [], "phases": [1000], "defeat": "kill",
        "capture_event": None, "capture_hold_ms": 0, "lesson_mask": 0, "form_reps": [1, 1, 1, 1], "maai": None, "flank_bouts": False,
        "loss": "checkpoint", "loss_limit": 0, "contest": "none", "decay_permille": 0, "min_turn_ms": 0,
        "max_turn_ms": 0, "crank_coop": None, "crank_player": None, "speed_cm_s": 0, "wait_cm": 0, "path_cm": 0, "pickups": [], "dropoffs": [],
        "dropoff_capacity": None, "drop_on_hit": carry_drop_policy(False, where), "carry_gate": None, "steps": [], "targets": [], "target_loss_limit": 0, "on_detected": "combat",
        "reinforce_wave": -1,
        "horse_down_retries": False, "fail_checkpoint": [], "fail_events": {}, "objectives": [],
        "lines_event": None, "closing_event": None, "exit_event": None, "guards": [], "stealth": None, "opponent": None,
        "sparring": False, "phase_events": [], "carry_item": None, "carry_speed_permille": 1000, "carry_weapons": [],
        "pickup_hold_ms": 0, "unload_hold_ms": 0, "objective_hold_ms": [], "equipment_weapons": None, "recovery": None,
    }
    nonlethal = params.get("nonlethal_types", DEFAULT_NONLETHAL)
    # Waves are what a beat throws at the hero. Only a fight to clear them
    # (all_waves_cleared) waits for them to fall; any other goal completes its
    # beat with whoever still stands withdrawing (chapter-02 b06, chapter-06's
    # "Kill requirement: None", chapter-08 b02's charge). Work under guard
    # (a production task with stealth: true) is watched rather than attacked:
    # the wave members authored on a patrol, and its x_guards, are posted as
    # the zone's guards (one per head), and a wave left empty is dropped.
    guarded = kind == "production_task" and task["pause_when_seen"]
    for index, wave in enumerate(params.get("waves") or []):
        if guarded:
            for enemy in wave["enemies"]:
                if "patrol" in enemy:
                    task["guards"] += [guard_row(enemy, f"{where}.waves[{index}]")] * \
                        expect_int(enemy["count"], f"{where}.waves[{index}].count", 1)
            wave = {**wave, "enemies": [enemy for enemy in wave["enemies"] if "patrol" not in enemy]}
            if not wave["enemies"]:
                continue
        task["waves"].append(task_wave(wave, nonlethal, f"{where}.waves[{index}]"))
    if guarded:
        for index, guard in enumerate(beat["ext"].get("guards") or []):
            task["guards"] += [guard_row(guard, f"{where}.x_guards[{index}]")] * \
                expect_int(guard.get("count", 1), f"{where}.x_guards[{index}].count", 1)
        task["stealth"] = stealth_block(beat, where)

    def objectives(*sources):
        for source in sources:
            if source:
                # An objective worked with Interact held (hold_s, interact_s),
                # or at a press (0).
                task["objective_hold_ms"] = [whole_ms(row.get("hold_s", row.get("interact_s", 0)), f"{where}.objectives")
                                             if isinstance(row, dict) else 0 for row in source]
                return ids_of(source, f"{where}.objectives")
        fail(where, "completion by objectives lists none")

    if kind == "cinematic":
        task.update(goal="elapsed", duration_ms=whole_ms(params["duration_s"], f"{where}.duration_s"),
                    skippable=params["skippable"])
    elif kind == "dialogue":
        task.update(goal="lines", count=len(params["lines"]), lines_event=params["trigger"])
        if not re.fullmatch(r"beat_start|(volume_enter|interact):\w+", params["trigger"]):
            fail(where, f"dialogue trigger {params['trigger']!r}")
        if complete:
            closing = {"volume_enter": volume_event(complete.get("volume")),
                       "event": f"event:{complete.get('event')}"}.get(complete["kind"])
            if closing is None:
                fail(where, f"dialogue completion {complete['kind']!r}")
            task.update(anchor_after_lines=True, closing_event=closing)
    elif kind == "combat_wave":
        goals = {"all_waves_cleared": "waves_cleared", "objectives": "objectives", "survive_s": "survive"}
        if complete["kind"] not in goals:
            fail(where, f"combat completion {complete['kind']!r} has no runtime goal")
        task["goal"] = goals[complete["kind"]]
        if task["goal"] == "objectives":
            task["objectives"] = objectives(complete.get("objectives"), params.get("objectives"))
            task["count"] = len(task["objectives"])
        if task["goal"] == "survive":
            task["duration_ms"] = complete["seconds"] * 1000
        task["sparring"] = params["target_kind"] != "enemy"
    elif kind == "duel":
        scoring, arms, loss = params["scoring"], params["weapons"], params["loss_policy"]
        task.update(opponent=params["opponent"], sparring=arms.get("player") in ("bokuto", "fukuro_shinai"),
                    loss="retry" if loss == "retry" else "continue_after",
                    loss_limit=0 if loss == "retry" else int(loss.partition(":")[2]))
        if scoring["mode"] == "points":
            task.update(goal="points", count=scoring["first_to"])
        elif scoring["mode"] == "lesson_gates":
            task["goal"] = "lessons"
            flanks = 0
            for gate in expect(params.get("lesson_gates"), (list,), f"{where}.lesson_gates"):
                name = gate["gate"]
                if name in LESSON_FORMS:
                    # A form learned once it has its clean repetitions (awase ×2).
                    form = LESSON_FORMS[name]
                    task["lesson_mask"] |= 1 << form
                    task["form_reps"][form] = expect_int(gate.get("count", 1), f"{where}.{name}.count", 1)
                elif name == "marobashi_flank":
                    # Each of the lesson's bouts scores only straight after a 転 flank.
                    flanks = expect_int(gate.get("count"), f"{where}.marobashi_flank", 1)
                    task["flank_bouts"] = True
                elif name == "maai_step":
                    if task["maai"] is not None:
                        fail(where, "duplicate maai gate")
                    task["maai"] = maai_lesson(beat["ext"].get("maai"), expect_int(gate.get("count"), where, 1), where)
                else:
                    fail(where, f"lesson gate {name!r}")
            # The lesson's scored bouts (x_scored_bouts); a 転 lesson scores one per flank.
            bouts = beat["ext"].get("scored_bouts")
            task["count"] = expect_int(bouts.get("count"), f"{where}.scored_bouts", 1) if bouts else flanks
            if flanks and flanks != task["count"]:
                fail(where, f"{flanks} 転 flanks for {task['count']} scored bouts")
            if task["maai"] and (task["lesson_mask"] != 1 or task["count"]):
                fail(where, "maai follows stance in its own non-attacking lesson")
            if not task["lesson_mask"] and not task["count"]:
                fail(where, "a lesson duel teaches nothing the runtime measures")
        else:
            task["goal"] = "opponent_down"
            # A duel not to the death (lethal: false, or a mutō-dori finish) spares its opponent.
            task["defeat"] = "spare" if not params["lethal"] or params["finisher"] == "muto_dori" else "kill"
            for index, event in enumerate(params.get("events") or []):
                task["phases"].append(permille(event["at_hp_pct"] / 100, f"{where}.events[{index}]"))
                task["phase_events"].append(expect(event["id"], (str,), f"{where}.events[{index}].id"))
    elif kind == "stealth_zone":
        task["guards"] = [guard_row(guard, f"{where}.guards[{index}]") for index, guard in enumerate(params["guards"])]
        task["stealth"] = stealth_block(beat, where)
        if complete["kind"] == "exit_reached":
            task.update(goal="exit", exit_event=volume_event(complete.get("volume")))
        elif complete["kind"] == "objectives":
            task["objectives"] = objectives(complete.get("objectives"), params.get("objectives"))
            task.update(goal="objectives", count=len(task["objectives"]))
        else:
            fail(where, f"stealth completion {complete['kind']!r}")
        detected = params["on_detected"]
        if detected == "restart_checkpoint":
            task["on_detected"] = "restart"
        elif detected.startswith("reinforce:"):
            wave_ids = [wave["id"] for wave in task["waves"]]
            if detected[10:] not in wave_ids:
                fail(where, f"on_detected names no wave {detected[10:]!r}")
            task.update(on_detected="reinforce", reinforce_wave=wave_ids.index(detected[10:]))
    elif kind == "production_task":
        name = params["task"]
        block = params[name]
        if name == "hold":
            points = block.get("interact_points") or []
            seconds = block["hold_s"] if "hold_s" in block else len(points) * block["per_point_s"]
            task.update(goal="hold", duration_ms=whole_ms(seconds, f"{where}.hold"), contest=block["contest"],
                        decay_permille=permille(block.get("decay_per_s", 0), f"{where}.hold.decay_per_s"))
        elif name == "crank":
            task["crank_coop"] = cooperation(beat, fail)
            task["crank_player"] = player_work(beat, fail)
            slowest, fastest = block["turn_rate_band"]
            task.update(goal="turns", count=block["turns_required"], min_turn_ms=round(1000 / fastest),
                        max_turn_ms=round(1000 / slowest),
                        decay_permille=permille(block["progress_decay_per_s"], f"{where}.crank.progress_decay_per_s"))
        elif name == "escort":
            task.update(goal="escort", speed_cm_s=expect_int(block["speed_cm_s"], f"{where}.escort.speed_cm_s", 1),
                        wait_cm=expect_int(block["wait_for_player_cm"], f"{where}.escort.wait_for_player_cm", 1),
                        path_cm=round(block["path_length_m"] * 100) if "path_length_m" in block else 0)
            if expect(block["fail_on_npc_death"], (bool,), f"{where}.escort.fail_on_npc_death"):
                task["fail_checkpoint"].append("escort_down")
        elif name == "carry":
            task["carry_gate"] = carry_gate(beat["ext"].get("gate_interact"), f"{where}.carry_gate")
            task.update(goal="deliveries", count=block["count"], pickups=ids_of(block["pickups"], f"{where}.pickups"),
                        carry_item=expect(block["item"], (str,), f"{where}.carry.item"),
                        dropoffs=ids_of(block["dropoffs"], f"{where}.dropoffs"),
                        drop_on_hit=carry_drop_policy(block.get("drop_on_hit", False), f"{where}.carry.drop_on_hit"))
            expect_int(task["count"], f"{where}.carry.count", 1)
            if task["count"] > 99:
                fail(where, "carry count exceeds the runtime limit of 99")
            if "x_dropoff_capacity" in block:
                task["dropoff_capacity"] = carry_dropoff_capacity(block["x_dropoff_capacity"], task["dropoffs"],
                                                                 task["count"], f"{where}.carry.x_dropoff_capacity")
            # The load slows the hero and leaves at most the katana in one paw.
            task["carry_speed_permille"] = permille(block.get("move_speed_mult", 1), f"{where}.carry.move_speed_mult")
            loadout = expect(block.get("loadout_while_carrying", []), (list,), f"{where}.carry.loadout_while_carrying")
            if set(loadout) - {"katana_one_hand"}:
                fail(where, f"carry loadout {loadout} has no runtime meaning")
            task["carry_weapons"] = [0] if loadout else []
            # A load hoisted at its pickup (ch03.b05's 釣瓶, x_hoist) is an
            # Interact held there; under guard it waits while a guard watches.
            hoist = beat["ext"].get("hoist")
            if hoist:
                if hoist.get("per_item") is not True or hoist.get("interact") is None:
                    fail(where, "a hoist lifts each load at its pickup")
                task["pickup_hold_ms"] = whole_ms(hoist["hold_s"], f"{where}.x_hoist.hold_s")
        elif name == "manufacture":
            for index, step in enumerate(block["steps"]):
                timing = step.get("timing") or {}
                spot = f"{where}.steps[{index}]"
                phrase_strikes, phrase_pass = 0, 0
                if beat["id"] == "ch05.b08" and step["kind"] == "hammer_rhythm":
                    phrase = beat["ext"].get("hammer_rhythm_phrase")
                    if (beat["id"] != "ch05.b08" or phrase != {"strikes": 8, "pass_ratio": .75,
                            "cue": "kozo_kozuchi_tap", "cue_to_strike_ms": 600} or
                            timing != {"beat_ms": 600, "tolerance_ms": 90} or step["count"] != 4):
                        fail(spot, "hammer rhythm requires four eight-strike phrases, six hits, and the authored cue timing")
                    phrase_strikes, phrase_pass = 8, 6
                elif beat["id"] == "ch05.b11" and step["kind"] == "weave_rhythm":
                    if beat["id"] != "ch05.b11" or timing != {"beat_ms": 750, "tolerance_ms": 120} or step["count"] != 24:
                        fail(spot, "weave rhythm requires twenty-four individual picks and the authored cue timing")
                    phrase_strikes, phrase_pass = 1, 1
                task["steps"].append({
                    "kind": expect(step["kind"], (str,), f"{spot}.kind"),
                    "count": expect_int(step["count"], f"{spot}.count", 1),
                    "beat_ms": expect_int(timing.get("beat_ms", 0), f"{spot}.beat_ms", 0),
                    "tolerance_ms": expect_int(timing.get("tolerance_ms", 0), f"{spot}.tolerance_ms", 0),
                    "phrase_strikes": phrase_strikes, "phrase_pass": phrase_pass})
            task["goal"] = "steps"
        elif name == "defend":
            task["targets"] = [{"id": expect(target["actor"], (str,), f"{where}.targets"),
                                "hp": expect_int(target["hp"], f"{where}.targets", 1)} for target in block["targets"]]
            if "duration_s" in block:
                task.update(goal="survive", duration_ms=whole_ms(block["duration_s"], f"{where}.defend.duration_s"))
            else:
                task["goal"] = "waves_cleared"
            if expect(block["fail_on_target_destroyed"], (bool,), f"{where}.defend.fail_on_target_destroyed"):
                task["fail_checkpoint"].append("target_destroyed")
                # Some targets may be lost before the defence fails (ch04.b12: the third planter taken).
                limit = expect_int(block.get("fail_after_targets_lost", 0), f"{where}.defend.fail_after_targets_lost", 0)
                if limit > len(task["targets"]):
                    fail(where, f"fails after {limit} of {len(task['targets'])} targets lost")
                task["target_loss_limit"] = limit
    elif kind == "horseback_ride":
        task["horse_down_retries"] = expect_enum(params.get("on_horse_down"), ("checkpoint", "dismount_continue"),
                                                 f"{where}.on_horse_down") == "checkpoint"
        if complete["kind"] in ("reach", "volume_enter"):
            task.update(goal="exit", exit_event=volume_event(complete["volume"]))
        elif complete["kind"] == "cargo_delivered":
            task["dropoffs"] = ids_of(params["cargo"]["dropoffs"], f"{where}.cargo.dropoffs")
            seconds = expect(params["cargo"].get("unload_hold_s"), (int, float), f"{where}.cargo.unload_hold_s")
            if not 0 < seconds <= (1 << 30) / 1000:
                fail(where, "cargo unload hold must be positive and fit the task clock")
            duration = whole_ms(seconds, f"{where}.cargo.unload_hold_s")
            if duration < 1:
                fail(where, "cargo unload hold must span at least one whole millisecond")
            task.update(goal="deliveries", count=len(task["dropoffs"]), unload_hold_ms=duration)
        else:
            fail(where, f"ride completion {complete['kind']!r}")
    elif kind == "boss":
        task.update(goal="opponent_down", opponent=params["boss"], defeat=BOSS_DEFEATS[params["defeat"]],
                    phases=[permille(phase["hp_pct_start"] / 100, f"{where}.phases") for phase in params["phases"]])
        if task["defeat"] == "capture":
            # The hand that binds a yielded boss: ch06's bulkhead lever, ch08's engine spine.
            ext = beat["ext"]
            binding = (ext.get("defeat_interact") or {}).get("id") or (ext.get("post_defeat") or {}).get("interact")
            if not isinstance(binding, str) or not re.fullmatch(r"\w+", binding):
                fail(where, "a capture names no interaction that binds the boss")
            task["capture_event"] = f"interact:{binding}"
            if binding == "engine_spine":
                task["capture_hold_ms"] = whole_ms((ext.get("post_defeat") or {}).get("hold_s"), f"{where}.post_defeat.hold_s")
                if task["capture_hold_ms"] <= 0:
                    fail(where, "the engine spine needs a positive held draw-cut")
    elif kind == "explore_optional":
        task["goal"] = "cache"
        if beat["id"] == "ch01.b08":
            completion = beat["ext"].get("complete", {})
            if completion != {"volume_enter": "vol_ch01_wood_exit"}:
                fail(where, "wood completes only at its authored exit")
            task.update(goal="exit", exit_event="volume_enter:vol_ch01_wood_exit")
            # Chapter §3.5 places these finds separately; the YAML reward list
            # is an association, not a single cache claim.
            for poi in beat["params"]["pois"]:
                item = {"poi_ch01_issoseki": "ch01.c01", "poi_ch01_sakaiishi": "ch01.c02"}.get(poi["id"])
                if item:
                    poi["collectible"] = item

    for entry in beat["fail"]:
        failure = next((name for pattern, name in FAIL_EVENTS if re.fullmatch(pattern, entry["on"])), None)
        if failure is None or entry["to"] not in ("checkpoint", "phase_checkpoint", "retry") or \
                (entry["to"] == "retry") != (failure == "match_lost"):
            fail(where, f"fail {entry['on']} -> {entry['to']} has no runtime meaning")
        task["fail_events"][entry["on"]] = failure
        if entry["to"] != "retry" and failure not in task["fail_checkpoint"]:
            task["fail_checkpoint"].append(failure)
    if (beat["ext"].get("maai") is not None) != (task["maai"] is not None):
        fail(where, "maai parameters require a measured maai lesson gate")
    if (beat["ext"].get("gate_interact") is not None) != (task["carry_gate"] is not None):
        fail(where, "gate_interact requires a carry task")
    return task


def normalize_subtitles(subtitles, context):
    rows = []
    for index, entry in enumerate(expect(subtitles, (list,), context)):
        where = f"{context}[{index}]"
        if isinstance(entry, str):
            rows.append((entry, None))
            continue
        expect(entry, (dict,), where)
        time_keys = [key for key in ("t_s", "at_s", "t") if key in entry]
        if set(entry) != {"line", *time_keys} or len(time_keys) != 1:
            fail(where, f"subtitle takes line and one time, got {sorted(entry)}")
        seconds = expect(entry[time_keys[0]], (int, float), where)
        rows.append((expect(entry["line"], (str,), where), round(seconds * 1000)))
    return rows


def place_subtitles(rows, lines, duration_s, context):
    """Times on a cinematic's own clock. A script that times none of its
    subtitles (ch05-ch07) plays them in script order, spread evenly over the
    cinematic and never overlapping; a script that times some must time all."""
    if all(at_ms is not None for _, at_ms in rows):
        return [(line, at_ms, False) for line, at_ms in rows]
    if any(at_ms is not None for _, at_ms in rows):
        fail(context, "subtitles mix timed and untimed lines")
    durations = {line["id"]: line["duration_s"] for line in lines}
    total = round(duration_s * 1000)
    placed, free = [], 0
    for index, (line, _) in enumerate(rows):
        if line not in durations:
            fail(context, f"subtitle {line} is not a line of this chapter")
        at_ms = max(round(index * total / len(rows)), free)
        free = at_ms + round(durations[line] * 1000)
        if free > total:
            fail(context, f"subtitle {line} runs past the end of the cinematic")
        placed.append((line, at_ms, True))
    return placed


def normalize_line(raw, context, chapter_prefix):
    expect(raw, (dict,), context)
    missing = [key for key in LINE_KEYS if key not in raw]
    if missing:
        fail(context, f"line lacks {missing}")
    line_id = expect(raw["id"], (str,), context)
    match = re.fullmatch(rf"({re.escape(chapter_prefix)})\.b(\d\d)\.[a-z]+\.\d{{3}}", line_id)
    if not match:
        fail(context, f"line id {line_id!r} is not {chapter_prefix}.bMM.<token>.<nnn>")
    beat = None if match.group(2) == "00" else f"{chapter_prefix}.b{match.group(2)}"
    if raw.get("beat") not in (None, beat):
        fail(line_id, f"line names beat {raw['beat']} but its id places it in {beat}")
    register = expect(raw["register"], (str,), f"{line_id}.register")
    if register in REGISTER_FAMILIES:
        family, delivery = register, None
    elif register in REGISTER_ALIASES:
        family, delivery = REGISTER_ALIASES[register]
    else:
        fail(line_id, f"register {register!r} has no §18 family")
    readings = raw.get("readings", raw.get("reading"))
    if "readings" in raw and "reading" in raw:
        fail(line_id, "reading given twice")
    if raw.get("audio") is not None:
        fail(line_id, "voice-over is not recorded; audio must be null")
    ext = {}
    for key, value in raw.items():
        if key in LINE_KEYS or key in LINE_SCHEDULE_KEYS or key in (
                "mode", "repeatable", "readings", "reading", "voice_variant", "audio"):
            continue
        ext[key[2:] if key.startswith("x_") else key] = value
    duration = expect(raw["duration_s"], (int, float), f"{line_id}.duration_s")
    return {
        "id": line_id,
        "beat": beat,
        "speaker": expect(raw["speaker"], (str,), f"{line_id}.speaker"),
        "ja": expect(raw["ja"], (str,), f"{line_id}.ja"),
        "en": expect(raw["en"], (str,), f"{line_id}.en"),
        "duration_s": float(duration),
        "register": family,
        "delivery": delivery,
        "mode": expect_enum(raw["mode"], TRIGGER_MODES, f"{line_id}.mode") if raw.get("mode") is not None else None,
        "repeatable": expect(raw.get("repeatable", False), (bool,), f"{line_id}.repeatable"),
        "readings": expect(readings, (str, type(None)), f"{line_id}.readings"),
        "voice_variant": expect(raw.get("voice_variant"), (str, type(None)), f"{line_id}.voice_variant"),
        "ext": ext,
    }


def trigger_row(beat, event, mode, lines, source, context, repeatable=False, cooldown_s=None, at_ms=None, ext=None):
    ext = dict(ext or {})
    if "delay_s" in ext:
        delay = whole_ms(ext["delay_s"], context + ".delay_s")
        if delay <= 0 or delay > 120000 or "+" in event:
            fail(context, "a delayed trigger needs one positive delay of at most 120 seconds")
        event = f"{event}+{delay / 1000:g}s"
    # A conditional line (ch08.b17's returned sword) names what must be found or set first.
    requires = ext.pop("requires_flag", None)
    if requires is not None and not REQUIRES_FLAG.fullmatch(expect(requires, (str,), f"{context}.requires_flag")):
        fail(context, f"requires_flag {requires!r} is neither collectible:<id> nor story:<flag>")
    return {
        "beat": beat,
        "on": expect(event, (str,), f"{context}.on"),
        "mode": expect_enum(mode, TRIGGER_MODES, f"{context}.mode"),
        "lines": expect_ids(lines, f"{context}.lines"),
        "source": source,
        "repeatable": expect(repeatable, (bool,), f"{context}.repeatable"),
        "cooldown_s": expect(cooldown_s, (int, float, type(None)), f"{context}.cooldown_s"),
        "at_ms": at_ms,
        "requires_flag": requires,
        "ext": ext,
    }


def raised_event(event):
    """A script's event as the runtime raises it, and what the rename keeps.

    A boss's intro or outro cue (ch02's ``intro@6.0``) plays in order as the
    fight opens or closes, under ``intro_cinematic`` or ``outro_cinematic``
    like ch05's, keeping its time for Sequencer. A proposed name (ch03's
    ``x_wave_start:1``) the director now raises is spelled as it raises it."""
    cue = BOSS_CUE.fullmatch(event)
    if cue:
        return f"{cue[1]}_cinematic", {"at_s": float(cue[2])}
    name, colon, rest = event.partition(":")
    if name in RAISED_PROPOSALS:
        return RAISED_PROPOSALS[name] + colon + rest, {"proposed": event}
    return event, {}


def normalize_beat(raw, previous, chapter_prefix, number, lines, triggers):
    context = raw.get("id", f"{chapter_prefix} beat {number}")
    expect(raw, (dict,), context)
    raw = dict(raw)
    beat_id = expect(raw.get("id"), (str,), context)
    if beat_id != f"{chapter_prefix}.b{number:02d}":
        fail(beat_id, f"expected id {chapter_prefix}.b{number:02d}")
    beat_type = expect_enum(raw.get("type"), BEAT_TYPES, f"{beat_id}.type")
    if beat_type == "collectible":
        fail(beat_id, "collectibles are registered per chapter, not sequenced")
    required, optional = PARAMS[beat_type]
    ext = strip_ext(raw, beat_id)
    # A ride's proposed waves (ch02.b08's drone groups) are the waves the
    # runtime plays on every ride (ch08.b02 writes them unprefixed).
    if beat_type == "horseback_ride" and "waves" in ext:
        if "waves" in raw:
            fail(beat_id, "waves given twice")
        raw["waves"] = ext.pop("waves")
    # A production task's own block, nested under the task name or (ch01.b09) flat.
    task_keys = (raw.get("task"), *TASKS.get(raw.get("task"), ())) if beat_type == "production_task" else ()
    unknown = [key for key in raw if not key.startswith("x_") and key not in COMMON_KEYS
               and key not in required and key not in optional and key not in task_keys]
    if unknown:
        fail(beat_id, f"keys outside the §12 contract without an x_ prefix: {unknown}")
    missing = [key for key in required if key not in raw]
    if beat_type == "horseback_ride" and "route" in missing and "open" in raw:
        missing.remove("route")
    if missing:
        fail(beat_id, f"{beat_type} lacks {missing}")

    requires = raw.get("requires")
    if requires is None:
        requires = [previous] if previous else []
    expect_ids(requires, f"{beat_id}.requires")
    optional_beat = expect(raw.get("optional", False), (bool,), f"{beat_id}.optional")
    if optional_beat and beat_type not in ("explore_optional", "collectible"):
        fail(beat_id, "only explore_optional and collectible beats may be optional")
    unlocks = raw.get("unlocks") or {}
    expect(unlocks, (dict,), f"{beat_id}.unlocks")
    if set(unlocks) - {"weapons", "mechanics"}:
        fail(beat_id, f"unlocks takes weapons and mechanics, got {sorted(unlocks)}")
    weapons = unlocks.get("weapons") or []
    mechanics = unlocks.get("mechanics") or []
    for weapon in expect(weapons, (list,), f"{beat_id}.unlocks.weapons"):
        expect_int(weapon, f"{beat_id}.unlocks.weapons", 0)
    expect_ids(mechanics, f"{beat_id}.unlocks.mechanics")
    # An optional pickup missed earlier is granted here if still missing (§11);
    # it is not a second unlock.
    grants = ext.pop("auto_grant_if_missing", [])
    for weapon in expect(grants, (list,), f"{beat_id}.auto_grant_if_missing"):
        expect_int(weapon, f"{beat_id}.auto_grant_if_missing", 0)
    # A story flag the beat sets for a later chapter to read (ch07.b05's name board).
    story_flags = []
    story = ext.pop("story_flag", None)
    if story is not None:
        expect(story, (dict,), f"{beat_id}.story_flag")
        if set(story) != {"set", "effect"}:
            fail(beat_id, f"story_flag takes set and effect, got {sorted(story)}")
        story_flags.append(expect(story["set"], (str,), f"{beat_id}.story_flag.set"))
        ext["story_flag_effect"] = expect(story["effect"], (str,), f"{beat_id}.story_flag.effect")
    site = raw.get("site")
    if site is not None:
        expect_enum(expect_int(site, f"{beat_id}.site"), (0, 1, 2), f"{beat_id}.site")
    registry = raw.get("registry")
    try:
        validate_registry(registry, beat_type, raw, ext)
    except ValueError as error:
        fail(beat_id, str(error))
    beat = {
        "id": beat_id,
        "type": beat_type,
        "place": expect(raw.get("place"), (str,), f"{beat_id}.place"),
        "title_ja": expect(raw.get("title_ja"), (str,), f"{beat_id}.title_ja"),
        "title_en": expect(raw.get("title_en"), (str,), f"{beat_id}.title_en"),
        "target_s": expect_int(raw.get("target_s"), f"{beat_id}.target_s", 1),
        "checkpoint": expect(raw.get("checkpoint", True), (bool,), f"{beat_id}.checkpoint"),
        "requires": list(requires),
        "optional": optional_beat,
        "site": site,
        "unlocks": {"weapons": list(weapons), "mechanics": list(mechanics), "grants": list(grants),
                    "story_flags": story_flags},
        "registry": registry,
        "music": expect(raw.get("music"), (str, type(None)), f"{beat_id}.music"),
        "fail": normalize_fail(raw.get("fail"), f"{beat_id}.fail"),
        "params": {},
        "ext": ext,
    }
    params = beat["params"]
    if beat_type == "production_task":
        task, block = normalize_production(raw, beat_id)
        params.update({"task": task, task: block})
    for key in required + optional:
        if key in raw and key not in params:
            params[key] = raw[key]
    if beat_type == "horseback_ride" and "open" in raw:
        params["open"] = raw["open"]

    # Typed parameters.
    if "waves" in params:
        normalize_waves(params["waves"], f"{beat_id}.waves")
    if "waves" in params or beat_type == "combat_wave":
        params["nonlethal_types"] = expect_ids(params.get("nonlethal_types", list(DEFAULT_NONLETHAL)),
                                               f"{beat_id}.nonlethal_types")
        if "max_alive" in params:
            expect_int(params["max_alive"], f"{beat_id}.max_alive", 1)
    if beat_type == "combat_wave":
        params["target_kind"] = expect_enum(params.get("target_kind", "enemy"), ("enemy", "mato", "pupil"),
                                            f"{beat_id}.target_kind")
    if beat_type == "duel":
        scoring = expect(params["scoring"], (dict,), f"{beat_id}.scoring")
        expect_enum(scoring.get("mode"), SCORING, f"{beat_id}.scoring.mode")
        if scoring["mode"] == "points":
            expect_int(scoring.get("first_to"), f"{beat_id}.scoring.first_to", 1)
        params["finisher"] = expect_enum(params.get("finisher") or "none", FINISHERS, f"{beat_id}.finisher")
        expect(params["lethal"], (bool,), f"{beat_id}.lethal")
        loss = params.setdefault("loss_policy", "retry")
        if loss != "retry" and not re.fullmatch(r"continue_after:[1-9]\d*", loss):
            fail(beat_id, f"loss_policy {loss!r}")
        params["checkpoint_per_phase"] = expect(params.get("checkpoint_per_phase", False), (bool,),
                                                f"{beat_id}.checkpoint_per_phase")
    if beat_type == "stealth_zone":
        detected = expect(params["on_detected"], (str,), f"{beat_id}.on_detected")
        if detected not in ("combat", "restart_checkpoint") and not re.fullmatch(r"reinforce:\w+", detected):
            fail(beat_id, f"on_detected {detected!r}")
    if beat_type == "horseback_ride":
        expect_enum(params["horse"], HORSES, f"{beat_id}.horse")
        expect_enum(params["mode"], RIDE_MODES, f"{beat_id}.mode")
        params["weapons"] = [expect_int(weapon, f"{beat_id}.weapons", 0)
                             for weapon in expect(params.get("weapons", []), (list,), f"{beat_id}.weapons")]
    if beat_type == "boss":
        expect_enum(params["defeat"], DEFEATS, f"{beat_id}.defeat")
        params["finisher"] = expect_enum(params.get("finisher") or "none", FINISHERS, f"{beat_id}.finisher")
        params["checkpoint_per_phase"] = expect(params.get("checkpoint_per_phase", False), (bool,),
                                                f"{beat_id}.checkpoint_per_phase")
        phases = expect(params["phases"], (list,), f"{beat_id}.phases")
        starts = [expect_int(phase.get("hp_pct_start"), f"{beat_id}.phases", 1) for phase in phases]
        if not starts or starts[0] != 100 or any(a <= b for a, b in zip(starts, starts[1:])):
            fail(beat_id, f"phase hp_pct_start must begin at 100 and fall, got {starts}")
    if beat_type == "cinematic":
        expect(params["skippable"], (bool,), f"{beat_id}.skippable")
        expect(params["duration_s"], (int, float), f"{beat_id}.duration_s")
    if beat_type == "dialogue":
        expect_enum(params["mode"], DIALOGUE_BEAT_MODES, f"{beat_id}.mode")
        expect(params["trigger"], (str,), f"{beat_id}.trigger")
    if "complete" in params or beat_type in ("combat_wave", "stealth_zone", "horseback_ride"):
        params["complete"] = normalize_complete(params.get("complete"), f"{beat_id}.complete", beat_type, params)

    # Every way the beat schedules a line becomes a trigger row.
    for index, entry in enumerate(raw.get("dialogue") or []):
        where = f"{beat_id}.dialogue[{index}]"
        expect(entry, (dict,), where)
        extra = {(key[2:] if key.startswith("x_") else key): value for key, value in entry.items()
                 if key not in ("on", "lines", "mode", "repeatable", "cooldown_s")}
        for event in event_list(entry.get("on"), f"{where}.on"):
            event, cue = raised_event(event)
            triggers.append(trigger_row(beat_id, event, entry.get("mode"), entry.get("lines"), "dialogue", where,
                                        entry.get("repeatable", False), entry.get("cooldown_s"),
                                        ext={**extra, **cue}))
    if beat_type == "dialogue":
        ids = []
        for index, entry in enumerate(params.pop("lines")):
            if isinstance(entry, dict):
                lines.append(normalize_line(entry, f"{beat_id}.lines[{index}]", chapter_prefix))
                ids.append(entry["id"])
            else:
                ids.append(expect(entry, (str,), f"{beat_id}.lines[{index}]"))
        # The beat's own lines play on its trigger, except those its dialogue
        # entries already place (ch01 splits a conversation across volumes).
        scheduled = {line for row in triggers if row["beat"] == beat_id for line in row["lines"]}
        remaining = [line for line in ids if line not in scheduled]
        if remaining:
            triggers.append(trigger_row(beat_id, params["trigger"], params["mode"], remaining, "dialogue_beat", beat_id))
        params["lines"] = ids
    for index, bark in enumerate(params.pop("barks", None) or []):
        where = f"{beat_id}.barks[{index}]"
        expect(bark, (dict,), where)
        if set(bark) != {"on", "line"}:
            fail(where, f"barks take on and line, got {sorted(bark)}")
        event, cue = raised_event(bark["on"])
        triggers.append(trigger_row(beat_id, event, "bark", [bark["line"]], "bark", where, ext=cue))
    if beat_type == "cinematic":
        rows = normalize_subtitles(params.pop("subtitles"), f"{beat_id}.subtitles")
        for line, at_ms, spread in place_subtitles(rows, lines, params["duration_s"], f"{beat_id}.subtitles"):
            triggers.append(trigger_row(beat_id, "subtitle", "cinematic", [line], "subtitle", beat_id, at_ms=at_ms,
                                        ext={"at_ms_spread": True} if spread else None))
    for key, event in (("intro_subtitles", "intro_cinematic"), ("outro_subtitles", "outro_cinematic")):
        if key in ext:
            triggers.append(trigger_row(beat_id, event, "cinematic", ext.pop(key), key, beat_id))
    task = normalize_task(beat)
    return {**{key: value for key, value in beat.items() if key != "ext"}, "task": task, "ext": beat["ext"]}


def to_cm(value, scale, context):
    """Metres or centimetres to integer centimetres, refusing sub-centimetre data."""
    if isinstance(value, list):
        return [to_cm(item, scale, context) for item in value]
    expect(value, (int, float), context)
    centimetres = value * scale
    if abs(centimetres - round(centimetres)) > 1e-6:
        fail(context, f"{value} is not a whole centimetre")
    return int(round(centimetres))


def layout_point(point_id, frame, place, value, scale, context, yaw=None):
    if isinstance(value, dict):
        if set(value) - {"chainage_m", "offset_m"}:
            fail(context, f"point {point_id} has {sorted(value)}")
        return {"id": point_id, "frame": frame, "place": place, "positions_cm": None, "yaw_deg": yaw,
                "chainage_m": value.get("chainage_m"), "offset_m": value.get("offset_m")}
    expect(value, (list,), context)
    positions = value if value and isinstance(value[0], list) else [value]
    for position in positions:
        if len(position) not in (2, 3):
            fail(context, f"point {point_id} position {position}")
    return {"id": point_id, "frame": frame, "place": place, "positions_cm": to_cm(positions, scale, context),
            "yaw_deg": yaw, "chainage_m": None, "offset_m": None}


def layout_volume(volume_id, frame, place, value, scale, context):
    shape = {"id": volume_id, "frame": frame, "place": place, "shape": None}
    extra = {}
    if "center" in value or "center_cm" in value:
        unit = 1 if "center_cm" in value else scale
        center = value.get("center_cm", value.get("center"))
        shape["center_cm"] = to_cm(center, unit, context)
        if "size" in value or "size_cm" in value:
            shape["shape"] = "box"
            shape["size_cm"] = to_cm(value.get("size_cm", value.get("size")), unit, context)
        elif "radius" in value:
            shape["shape"] = "cylinder"
            shape["radius_cm"] = to_cm(value["radius"], unit, context)
            shape["height_cm"] = to_cm(value["height"], unit, context) if "height" in value else None
        else:
            fail(context, f"volume {volume_id} has a centre but no size or radius")
        used = {"center", "center_cm", "size", "size_cm", "radius", "height", "place"}
    elif "min" in value and "max" in value:
        low, high = to_cm(value["min"], scale, context), to_cm(value["max"], scale, context)
        if any(a >= b for a, b in zip(low, high)):
            fail(context, f"volume {volume_id} min {low} is not below max {high}")
        shape["shape"] = "box"
        # An odd extent puts the centre on a half centimetre.
        shape["center_cm"] = [(a + b) // 2 if (a + b) % 2 == 0 else (a + b) / 2 for a, b in zip(low, high)]
        shape["size_cm"] = [b - a for a, b in zip(low, high)]
        used = {"min", "max"}
    elif "spline" in value:
        shape["shape"] = "spline_band"
        shape["spline"] = value["spline"]
        shape["from_m"], shape["to_m"] = value["from_m"], value["to_m"]
        shape["width_cm"] = to_cm(value["width"], scale, context)
        used = {"spline", "from_m", "to_m", "width", "place"}
    elif "chainage_m" in value:
        shape["shape"] = "chainage"
        shape["chainage_m"] = value["chainage_m"]
        used = {"chainage_m"}
    else:
        shape["shape"] = "unplaced"
        used = set()
    for key, item in value.items():
        if key not in used and key != "id":
            extra[key] = item
    shape["ext"] = extra
    return shape


def normalize_layout(document, chapter_prefix):
    """Chapter layout proposals in one container: every coordinate in integer cm.

    Frames are kept as authored (ch01: metres about the Arena 0 centre; ch02: one
    frame per place; ch03: Arena 1 centimetres). Chapters that authored no layout
    yet get an empty container; C3/C4 own those spaces."""
    layout = {"frames": [], "volumes": [], "points": [], "splines": [], "patrols": [], "ext": {}}
    if "layout" in document and "x_layout" in document:
        fail(chapter_prefix, "layout given twice")
    source = document.get("layout", document.get("x_layout"))
    if source is None:
        return layout
    expect(source, (dict,), f"{chapter_prefix}.layout")
    if "frame" in source:  # ch01: one metric frame with typed lists.
        frame = chapter_prefix
        layout["frames"].append({"id": frame, "place": None, "text": source["frame"], "source_units": "m"})
        for volume in source.get("volumes", []):
            layout["volumes"].append(layout_volume(volume["id"], frame, volume.get("place"), volume, 100,
                                                   f"{chapter_prefix}.layout.{volume['id']}"))
        for point in source.get("points", []):
            if set(point) - {"id", "pos", "yaw_deg"}:
                fail(chapter_prefix, f"point {point['id']} has {sorted(point)}")
            layout["points"].append(layout_point(point["id"], frame, None, point["pos"], 100,
                                                 f"{chapter_prefix}.layout.{point['id']}", point.get("yaw_deg")))
        for spline in source.get("splines", []):
            layout["splines"].append({"id": spline["id"], "frame": frame, "place": None,
                                      "nodes_cm": to_cm(spline["nodes"], 100, spline["id"]),
                                      "length_m": spline.get("length_m"), "ext": {}})
        for key in source:
            if key not in ("frame", "volumes", "points", "splines"):
                layout["ext"][key] = source[key]
        return layout
    if "origin" in source:  # ch03: one centimetre frame with id-keyed maps.
        frame = chapter_prefix
        layout["frames"].append({"id": frame, "place": None, "text": source["origin"], "source_units": "cm"})
        blocks = {frame: (None, source)}
    else:  # ch02: one frame per place.
        blocks = {}
        for place, block in source.items():
            expect(block, (dict,), f"{chapter_prefix}.layout.{place}")
            layout["frames"].append({"id": place, "place": place, "text": block.get("source"), "source_units": "cm"})
            blocks[place] = (place, block)
    for frame, (place, block) in blocks.items():
        for volume_id, value in (block.get("volumes") or {}).items():
            where = f"{chapter_prefix}.layout.{volume_id}"
            if isinstance(value, list):  # a start point filed among ch02's volumes
                layout["points"].append(layout_point(volume_id, frame, place, value, 1, where))
            else:
                layout["volumes"].append(layout_volume(volume_id, frame, place, expect(value, (dict,), where), 1, where))
        for point_id, value in (block.get("spawns") or {}).items():
            layout["points"].append(layout_point(point_id, frame, place, value, 1,
                                                 f"{chapter_prefix}.layout.{point_id}"))
        for spline_id, value in (block.get("splines") or {}).items():
            spline = {"id": spline_id, "frame": frame, "place": place, "nodes_cm": None, "length_m": None, "ext": {}}
            if isinstance(value, list):
                spline["nodes_cm"] = to_cm(value, 1, spline_id)
            else:
                expect(value, (dict,), spline_id)
                spline["length_m"] = value.get("length_m")
                spline["ext"] = {key: item for key, item in value.items() if key != "length_m"}
            layout["splines"].append(spline)
        for patrol_id, value in (block.get("patrols") or {}).items():
            expect(value, (dict,), patrol_id)
            if set(value) - {"loop_s", "alt_cm", "points", "circle"} or ("points" in value) == ("circle" in value):
                fail(patrol_id, f"patrol takes loop_s, alt_cm and points or circle, got {sorted(value)}")
            circle = value.get("circle")
            if circle is not None and set(circle) != {"centre", "radius"}:
                fail(patrol_id, f"circle takes centre and radius, got {sorted(circle)}")
            layout["patrols"].append({
                "id": patrol_id, "frame": frame, "loop_s": expect_int(value["loop_s"], patrol_id, 1),
                "alt_cm": value.get("alt_cm"),
                "points_cm": to_cm(value["points"], 1, patrol_id) if "points" in value else None,
                "circle_cm": {"center": to_cm(circle["centre"], 1, patrol_id),
                              "radius": to_cm(circle["radius"], 1, patrol_id)} if circle else None})
        extras = {key: item for key, item in block.items()
                  if key not in ("volumes", "spawns", "splines", "patrols", "source", "origin")}
        if extras:
            layout["ext"][frame] = extras
    # ch02 notes a volume shared by two places in both; keep the one with geometry.
    placed = {volume["id"] for volume in layout["volumes"] if volume["shape"] != "unplaced"}
    layout["volumes"] = [volume for volume in layout["volumes"]
                         if volume["shape"] != "unplaced" or volume["id"] not in placed]
    ids = [item["id"] for group in ("volumes", "points", "splines", "patrols") for item in layout[group]]
    duplicates = sorted({item for item in ids if ids.count(item) > 1})
    if duplicates:
        fail(chapter_prefix, f"layout ids used twice: {duplicates}")
    return layout


def normalize_collectible(raw, chapter_prefix, index):
    context = f"{chapter_prefix} collectible {index}"
    expect(raw, (dict,), context)
    collectible_id = expect(raw.get("collectible_id"), (str,), context)
    if raw.get("id", collectible_id) != collectible_id or raw.get("type", "collectible") != "collectible":
        fail(collectible_id, "id and type must agree with collectible_id")
    codex = expect(raw.get("codex"), (dict,), f"{collectible_id}.codex")
    if set(codex) != {"ja", "en"}:
        fail(collectible_id, f"codex takes ja and en, got {sorted(codex)}")
    beats = raw.get("found_in", raw.get("beat_hint", raw.get("x_available")))
    beats = [beats] if isinstance(beats, str) else beats
    known = {"id", "type", "collectible_id", "category", "place", "mask_bit", "codex", "found_in", "beat_hint",
             "x_available", "title_ja", "title_en", "target_s", "volume", "actor", "sets_flag", "x_location"}
    unknown = sorted(set(raw) - known)
    if unknown:
        fail(collectible_id, f"unknown collectible keys {unknown}")
    if raw.get("target_s", 0) != 0:
        fail(collectible_id, "collectibles are passive and take no pacing time")
    return {
        "id": collectible_id,
        "category": expect_enum(raw.get("category"), COLLECTIBLE_CATEGORIES, f"{collectible_id}.category"),
        "place": expect(raw.get("place"), (str,), f"{collectible_id}.place"),
        "mask_bit": expect_int(raw.get("mask_bit"), f"{collectible_id}.mask_bit", 0),
        "beats": expect_ids(beats or [], f"{collectible_id}.beats"),
        "title_ja": expect(raw.get("title_ja"), (str, type(None)), f"{collectible_id}.title_ja"),
        "title_en": expect(raw.get("title_en"), (str, type(None)), f"{collectible_id}.title_en"),
        "codex": {"ja": expect(codex["ja"], (str,), collectible_id), "en": expect(codex["en"], (str,), collectible_id)},
        "volume": raw.get("volume"),
        "actor": raw.get("actor"),
        "sets_flag": raw.get("sets_flag"),
        "location_en": raw.get("x_location"),
    }


def normalize_prompt(raw, chapter_prefix, index):
    context = f"{chapter_prefix} ui_prompt {index}"
    expect(raw, (dict,), context)
    prompt_id = expect(raw.get("id"), (str,), context)
    unknown = sorted(set(raw) - {"id", "beat", "on", "ja", "en", "x_shown", "x_also_beats"})
    if unknown:
        fail(prompt_id, f"unknown prompt keys {unknown}")
    beats = [expect(raw.get("beat"), (str,), f"{prompt_id}.beat")] + expect_ids(raw.get("x_also_beats", []), prompt_id)
    return {
        "id": prompt_id,
        "beats": beats,
        "on": expect(raw.get("on"), (str, type(None)), f"{prompt_id}.on"),
        "ja": expect(raw.get("ja"), (str,), f"{prompt_id}.ja"),
        "en": expect(raw.get("en"), (str,), f"{prompt_id}.en"),
        "shown_en": raw.get("x_shown"),
    }


def bark_pool_triggers(document, chapter_prefix, beats, triggers):
    """ch05's chapter-wide pool and ch06's named sets become trigger rows."""
    for index, entry in enumerate(document.get("x_bark_pool") or []):
        where = f"{chapter_prefix}.bark_pool[{index}]"
        expect(entry, (dict,), where)
        if set(entry) - {"id", "speaker", "on", "repeatable"}:
            fail(where, f"bark pool entries take id, speaker, on, repeatable, got {sorted(entry)}")
        triggers.append(trigger_row(None, entry["on"], "bark", [entry["id"]], "bark_pool", where,
                                    entry.get("repeatable", False)))
    sets = document.get("x_bark_sets") or {}
    expect(sets, (dict,), f"{chapter_prefix}.bark_sets")
    used = set()
    for beat in beats:
        for name in beat["ext"].pop("bark_sets", []):
            if name not in sets:
                fail(beat["id"], f"unknown bark set {name}")
            used.add(name)
            for index, entry in enumerate(sets[name]):
                where = f"{chapter_prefix}.bark_sets.{name}[{index}]"
                if set(entry) != {"on", "line"}:
                    fail(where, f"bark set entries take on and line, got {sorted(entry)}")
                triggers.append(trigger_row(beat["id"], entry["on"], "bark", [entry["line"]], "bark_set", where,
                                            True, ext={"set": name}))
    if set(sets) - used:
        fail(chapter_prefix, f"bark sets no beat uses: {sorted(set(sets) - used)}")


def equipment_recovery(beats):
    """Carry the chapter's explicit temporary loadout to its authored recovery beat.

    Checkpoints restart a beat: earlier beats stay restricted, a restarted
    recovery repeats the retrieval, and later beats have the recovered gear.
    """
    pending = None
    for beat in beats:
        ext, where = beat["ext"], beat["id"]
        if "loadout" in ext:
            raw = expect(ext["loadout"], (dict,), where + ".x_loadout")
            if pending or set(raw) != {"equipped", "locked_slots", "until"}:
                fail(where, "loadout needs equipped, locked_slots and one recovery event")
            if raw["locked_slots"] != ["hip", "back", "polearm", "firearm"]:
                fail(where, "unrecognized temporary equipment slots")
            weapons = [expect_int(w, where + ".equipped", 0) for w in expect(raw["equipped"], (list,), where + ".equipped")]
            if weapons != [4] or raw["until"] != "x_item_picked:sword_bundle":
                fail(where, "dry-well restriction must leave only the wakizashi")
            pending = raw
        if pending:
            beat["task"]["equipment_weapons"] = pending["equipped"][:]
        if "pre_step" not in ext:
            continue
        raw = expect(ext["pre_step"], (dict,), where + ".x_pre_step")
        if not pending or set(raw) != {"interact", "descend_cm", "pickup", "restores", "string_bow_s"}:
            fail(where, "equipment pre-step needs a matching temporary loadout and complete recovery")
        restored = expect(raw["restores"], (dict,), where + ".restores")
        if (beat["task"]["task"] != "carry" or raw["pickup"] != "sword_bundle" or
                raw["interact"] != "act_b05_dry_well_rope" or
                set(restored) != {"equipped", "quiver"} or restored["equipped"] != [0, 4, 18]):
            fail(where, "unsupported equipment recovery contract")
        for weapon in restored["equipped"]:
            expect_int(weapon, where + ".restores.equipped", 0)
        depth = expect_int(raw["descend_cm"], where + ".descend_cm", 1)
        arrows = expect_int(restored["quiver"], where + ".quiver", 1)
        duration = whole_ms(raw["string_bow_s"], where + ".string_bow_s")
        if depth != 700 or arrows != 12 or duration != 3000:
            fail(where, "the dry well requires 700 cm, twelve arrows and three seconds to string the bow")
        beat["task"]["recovery"] = {"interact": raw["interact"], "item": raw["pickup"],
            "depth_cm": depth, "string_ms": duration, "weapons": restored["equipped"], "quiver": arrows}
        pending = None
    if pending:
        fail("equipment", "temporary loadout has no recovery pickup")


def checkpoints(beats):
    """Checkpoint positions in target time (centiseconds from chapter start).

    A beat checkpoints at its start. A boss or duel with checkpoint_per_phase
    also checkpoints at each later phase: after the earlier phases' own
    target_s where the script gives them all, otherwise in proportion to the
    HP the phase starts at (a duel's phases are its events)."""
    rows, elapsed = [], 0
    for beat in beats:
        if beat["checkpoint"]:
            rows.append({"beat": beat["id"], "phase": 0, "at_cs": elapsed * 100})
        params = beat["params"]
        if params.get("checkpoint_per_phase"):
            if beat["type"] == "boss":
                phases = params["phases"]
                starts = [phase["hp_pct_start"] for phase in phases]
                timed = [phase.get("target_s") for phase in phases]
            else:
                starts = [100] + [event["at_hp_pct"] for event in params.get("events", [])
                                  if event.get("checkpoint", True)]
                timed = [None]
            if all(isinstance(seconds, int) for seconds in timed):
                if sum(timed) != beat["target_s"]:
                    fail(beat["id"], f"phase target_s {timed} does not sum to {beat['target_s']}")
                offsets = [sum(timed[:phase]) * 100 for phase in range(1, len(timed))]
            elif any(seconds is not None for seconds in timed):
                fail(beat["id"], "give every phase a target_s or none")
            else:
                offsets = [beat["target_s"] * (100 - start) for start in starts[1:]]
            for phase, offset in enumerate(offsets, 1):
                rows.append({"beat": beat["id"], "phase": phase, "at_cs": elapsed * 100 + offset})
        elapsed += beat["target_s"]
    return rows


def build_chapter(number, places):
    document = load_chapter_yaml(number)
    prefix = f"ch{number:02d}"
    required = ("chapter", "title_ja", "title_en", "map", "target_s", "beats", "collectibles", "lines")
    missing = [key for key in required if key not in document]
    if missing:
        fail(prefix, f"chapter lacks {missing}")
    chapter_id = expect(document["chapter"], (str,), f"{prefix}.chapter")
    if not re.fullmatch(rf"{prefix}_[a-z_]+", chapter_id):
        fail(prefix, f"chapter id {chapter_id!r} must start with {prefix}_")
    lines = [normalize_line(line, f"{prefix}.lines[{index}]", prefix) for index, line in enumerate(document["lines"])]
    triggers, beats, previous = [], [], None
    for number_in_chapter, raw in enumerate(document["beats"], 1):
        beat = normalize_beat(raw, previous, prefix, number_in_chapter, lines, triggers)
        beats.append(beat)
        previous = beat["id"]
    equipment_recovery(beats)
    bark_pool_triggers(document, prefix, beats, triggers)
    order = {beat["id"]: index for index, beat in enumerate(beats)}
    # Authored order within a beat; the chapter-wide b00 pool last.
    lines.sort(key=lambda line: len(beats) if line["beat"] is None else order[line["beat"]])
    triggers.sort(key=lambda row: len(beats) if row["beat"] is None else order[row["beat"]])

    used_places = [beat["place"] for beat in beats]
    used_places += [collectible["place"] for collectible in document["collectibles"]]
    for entry in document.get("places") or []:
        used_places.append(entry["id"] if isinstance(entry, dict) else entry)
    unknown_places = sorted({place for place in used_places if place not in places})
    if unknown_places:
        fail(prefix, f"places missing from the bible's §14 table: {unknown_places}")
    chapter_places = [dict(places[place]) for place in places if place in set(used_places)]

    consumed = set(required) | {"ui_prompts", "places", "layout", "x_layout", "x_bark_pool", "x_bark_sets",
                                "sites", "catalog_anchor_lines", *DOC_ONLY_KEYS, *SPEAKER_LIST_KEYS}
    ext = {}
    for key, value in document.items():
        if key in consumed:
            continue
        name = key[2:] if key.startswith("x_") else key
        if name in ext:
            fail(prefix, f"chapter proposal {name} given twice")
        ext[name] = value
    secondary_maps = sorted({value for key in ("maps_also", "epilogue_map") if key in document
                             for value in (document[key] if isinstance(document[key], list) else [document[key]])})
    for key in ("maps_also", "epilogue_map"):
        ext.pop(key, None)
    collectibles = [normalize_collectible(item, prefix, index)
                    for index, item in enumerate(expect(document["collectibles"], (list,), prefix))]
    layout = normalize_layout(document, prefix)
    chapter_map = expect_int(document["map"], f"{prefix}.map", 0)
    # A HUD prompt keyed by a volume needs that volume placed, as a line does.
    prompted = [{"beat": beat_id, "on": row.get("on")} for row in document.get("ui_prompts") or []
                for beat_id in [row.get("beat")] + list(row.get("x_also_beats") or [])]
    space = derive_space({"prefix": prefix, "map": chapter_map}, beats, places, collectibles, triggers + prompted,
                         layout, fail)
    return {
        "schema_version": SCHEMA_VERSION,
        "id": chapter_id,
        "index": number - 1,
        "source": f"docs/campaign/chapter-{number:02d}.md",
        "title_ja": expect(document["title_ja"], (str,), f"{prefix}.title_ja"),
        "title_en": expect(document["title_en"], (str,), f"{prefix}.title_en"),
        "map": chapter_map,
        "secondary_maps": secondary_maps,
        "target_s": expect_int(document["target_s"], f"{prefix}.target_s", 1),
        "sites": production_sites(document, beats),
        "checkpoints": checkpoints(beats),
        "unlocks": [{"beat": beat["id"], **beat["unlocks"]} for beat in beats if any(beat["unlocks"].values())],
        "beats": beats,
        "lines": lines,
        "triggers": triggers,
        "collectibles": collectibles,
        "ui_prompts": [normalize_prompt(item, prefix, index)
                       for index, item in enumerate(document.get("ui_prompts") or [])],
        "places": chapter_places,
        "layout": layout,
        "space": space,
        "ext": ext,
    }


def production_sites(document, beats):
    """The chapter's three production sites in index order.

    A site is restored by the beat that names it. Sites restore in beat order,
    so each requires the one restored before it (ch08 restores site 1 first).
    Where a script also states the table outright, it must agree."""
    chapter = document["chapter"]
    ordered = [beat for beat in beats if beat["site"] is not None]
    rows = {}
    for position, beat in enumerate(ordered):
        if beat["site"] in rows:
            fail(chapter, f"site {beat['site']} is restored by two beats")
        rows[beat["site"]] = {"index": beat["site"], "beat": beat["id"],
                              "requires_sites": [ordered[position - 1]["site"]] if position else []}
    stated = document.get("sites")
    meta = (document.get("x_chapter_meta") or {}).get("sites")
    if stated is not None and meta is not None:
        fail(chapter, "sites given twice")
    stated = stated if stated is not None else meta
    if isinstance(stated, dict):
        stated = [{"site": int(index), "beat": beat} for index, beat in stated.items()]
    for entry in stated or []:
        row = rows.get(entry["site"])
        if row is None or row["beat"] != entry["beat"]:
            fail(chapter, f"stated site {entry['site']} -> {entry['beat']} disagrees with the beats")
        if "requires_sites" in entry and entry["requires_sites"] != row["requires_sites"]:
            fail(chapter, f"stated site {entry['site']} requires {entry['requires_sites']}, "
                          f"beat order gives {row['requires_sites']}")
    return [rows[index] for index in sorted(rows)]


def self_test():
    """The importer must refuse the ways a chapter script can silently go wrong."""
    def rejects(action):
        try:
            action()
        except BuildError:
            return True
        return False

    def parse(text):
        document = yaml.load(text, Loader=StrictLoader)
        check_json_value(document, "self-test")

    beat = {"id": "ch01.b01", "type": "cinematic", "place": "pl_estate_day", "title_ja": "序", "title_en": "Opening",
            "target_s": 60, "sequence": "LS", "duration_s": 60, "skippable": True, "subtitles": []}
    line = {"id": "ch01.b01.nyaakoto.001", "speaker": "samurai", "ja": "参る。", "en": "Here I come.",
            "register": "samurai_restrained", "duration_s": 1.5}
    ride = {"id": "ch01.b06", "type": "horseback_ride", "unlocks": {"mechanics": []}, "ext": {},
            "params": {"horse": "kurimaru", "gaits": ["walk", "trot"], "weapons": [0, 18]}}
    capture = {"id": "ch08.b14", "type": "boss", "fail": [], "ext": {"defeat_interact": {"id": "bulkhead_lever"}},
               "params": {"boss": "boss_val_amort", "defeat": "capture", "phases": [{"hp_pct_start": 100}]}}
    lesson = {"id": "ch01.b04", "type": "duel", "fail": [], "ext": {"scored_bouts": {"count": 2}},
              "params": {"opponent": "npc_matsukichi", "weapons": {"player": "bokuto"}, "loss_policy": "retry",
                         "scoring": {"mode": "lesson_gates"}, "lesson_gates": [{"gate": "marobashi_flank", "count": 2}]}}
    cases = {
        "duplicate key": lambda: parse("a: 1\na: 2\n"),
        "bare on key": lambda: parse("dialogue:\n  - {on: beat_start}\n"),
        "unprefixed proposal": lambda: normalize_beat({**beat, "camera_shake": 1}, None, "ch01", 1, [], []),
        "wrong beat number": lambda: normalize_beat(beat, None, "ch01", 2, [], []),
        "unknown register": lambda: normalize_line({**line, "register": "pirate"}, "self-test", "ch01"),
        "line without duration": lambda: normalize_line(
            {key: value for key, value in line.items() if key != "duration_s"}, "self-test", "ch01"),
        "recorded audio": lambda: normalize_line({**line, "audio": "vo.wav"}, "self-test", "ch01"),
        "sub-centimetre layout": lambda: to_cm(0.001, 100, "self-test"),
        "mixed subtitle timing": lambda: place_subtitles(
            [(line["id"], 0), ("ch01.b01.nyaakoto.002", None)], [line, {**line, "id": "ch01.b01.nyaakoto.002"}], 60, "self-test"),
        "subtitle past its cinematic": lambda: place_subtitles(
            [(line["id"], None), ("ch01.b01.nyaakoto.002", None)], [line, {**line, "id": "ch01.b01.nyaakoto.002"}], 2, "self-test"),
        "sub-millisecond cinematic": lambda: normalize_beat({**beat, "duration_s": 60.0004}, None, "ch01", 1, [], []),
        "fail without a runtime meaning": lambda: normalize_beat(
            {**beat, "fail": {"on": "lantern_lit", "to": "checkpoint"}}, None, "ch01", 1, [], []),
        "unknown dialogue condition": lambda: trigger_row(
            "ch01.b01", "beat_start", "ambient", [line["id"]], "dialogue", "self-test", ext={"requires_flag": "moon:full"}),
        "mounting from the left": lambda: ride_mount(
            {**ride, "ext": {"tack_up": {"mount_side": "left", "interact_points": []}}}, fail),
        "a matchlock in the saddle": lambda: ride_mount({**ride, "params": {**ride["params"], "weapons": [0, 5]}}, fail),
        "a capture that binds nothing": lambda: normalize_task({**capture, "ext": {}}),
        "転 flanks that miss their bouts": lambda: normalize_task({**lesson, "ext": {"scored_bouts": {"count": 3}}}),
    }
    accepted = [name for name, action in cases.items() if not rejects(action)]
    valid = (lambda: normalize_beat(beat, None, "ch01", 1, [], []), lambda: ride_mount(ride, fail),
             lambda: normalize_task(capture), lambda: normalize_task(lesson))
    if accepted or any(rejects(action) for action in valid):
        raise BuildError(f"importer self-test failed: accepted {accepted} or rejected a valid beat")
    return len(cases)


def encode(document):
    return (json.dumps(document, ensure_ascii=False, indent=1) + "\n").encode()


def build():
    """Return {path relative to ROOT: bytes} for every generated chapter file."""
    places = load_places()
    return {f"Content/Data/campaign/chapter_{number:02d}.json": encode(build_chapter(number, places))
            for number in range(1, CHAPTER_COUNT + 1)}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="fail if a committed file differs from a fresh build")
    arguments = parser.parse_args()
    try:
        self_test()
        outputs = build()
    except BuildError as error:
        print(f"Campaign data build failed: {error}", file=sys.stderr)
        return 1
    stale = [path for path, data in outputs.items()
             if not (ROOT / path).is_file() or (ROOT / path).read_bytes() != data]
    if arguments.check:
        if stale:
            print("Campaign data is stale; run scripts/unreal/build_campaign_data.py: " + ", ".join(stale),
                  file=sys.stderr)
            return 1
        print(f"Campaign data is current: {len(outputs)} chapter files")
        return 0
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for path in stale:
        (ROOT / path).write_bytes(outputs[path])
    print(f"Wrote {len(stale)} of {len(outputs)} chapter files to {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
