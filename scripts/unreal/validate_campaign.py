"""Validate the schema-4 offline campaign against the story bible's rules.

Reads Content/Data/catalog.json (speakers), Content/Data/campaign/campaign.json
(the hand-authored chapter index, title cards and site labels) and the eight
generated chapter files, and checks the bible's §12.3 rules:

1. pacing: each chapter's beat target_s within ±5% of its §10 minutes, and the
   campaign total within 21,600-28,800 s;
2. production sites 0-2 each restored once per chapter, in the order the
   beats' requires chain enforces;
3. weapons 0-20 each unlocked exactly once, at the §11 beat, in §11 order;
4. boss ids from §8 (and bosses.json when that file exists), and mutō-dori
   attacks only in fights whose defeat or finisher allows mutō-dori;
5. mounted weapons within {0, 18, 19}, and registry entries only on production
   tasks and cargo rides;
6. every line bilingual, spoken by a catalog speaker, at most 17 EN
   characters per second and within the §18 two-line subtitle limits;
7. nonlethal enemies never counted toward a defeat count;
8. at most 360 target seconds between the checkpoints the runtime writes, on
   a route that skips the explore caches and one that opens each of them
   (checkpoint_saves models SoraCampaignDirector).

Every trigger row naming an event the director raises must name one it can
raise in its beat (director_event_error), so no authored line waits on an
event that never comes.

Each chapter's ``space`` (campaign_space.py) must be buildable: zones and
route corridors never overlap each other or the arena, every beat's points,
spawns, patrols, stations, targets, caches, horses and collectible pickups
stand on their zone's floor clear of its walls and cover, every volume a
beat's events name exists inside its zone, rides and escorts run on routes
at least as long as their scripts ask, and an escort walks its whole route.
Every mechanic, manufacturing step and defended target has a bilingual label.

It also checks line references both ways (every scheduled line exists, every
line is scheduled), and that the 25 cues of catalog schema 3, frozen in
scripts/unreal/fixtures/campaign_legacy_lines.json, survive verbatim.

The self-test runs first and must reject known-bad data, so a broken check
cannot pass silently.
"""
from __future__ import annotations

import copy
import json
import math
import re
import textwrap
from pathlib import Path

from campaign_space import arena_blockers

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "Content/Data"
LEGACY_LINES = ROOT / "scripts/unreal/fixtures/campaign_legacy_lines.json"

# Story bible §10: target minutes per chapter.
CHAPTER_TARGET_S = (2400, 2700, 3300, 3600, 3600, 3300, 3000, 3300)
CAMPAIGN_TARGET_RANGE_S = (21600, 28800)
# Story bible §11, in unlock (beat) order.
WEAPON_UNLOCKS = (
    (18, "ch01.b07"), (0, "ch01.b12"), (19, "ch02.b03"), (4, "ch03.b01"), (7, "ch03.b09"),
    (2, "ch04.b03"), (5, "ch04.b03"), (20, "ch05.b04"), (8, "ch05.b08"), (1, "ch05.b09"),
    (3, "ch06.b05"), (13, "ch06.b07"), (10, "ch06.b10"), (9, "ch07.b01"), (11, "ch07.b06"),
    (14, "ch07.b08"), (16, "ch07.b11"), (12, "ch08.b01"), (17, "ch08.b01"), (15, "ch08.b03"),
    (6, "ch08.b06"),
)
# Story bible §12.1 mechanic flags, each unlocked once.
MECHANICS = ("kamae", "maai_ring", "awase", "marobashi", "yumi", "mount", "mounted_archery", "yari", "carry",
             "stealth", "takedown", "seal_cut", "hayago_reload", "crank", "manufacture", "tsubute", "muto_dori",
             "shield_break", "volley_command")
BOSSES = ("boss_dunark", "boss_penalta", "boss_hakari", "boss_tarifa", "boss_eskro", "boss_collatera",
          "boss_val_amort")
ENEMIES = ("enforcer_rifle", "blade_retainer", "shield_enforcer", "grenadier", "marksman", "drone",
           "bound_conscript", "auditor", "loom_automaton", "seizure_walker")
TRAINING_TARGETS = ("mato_kinteki", "mato_tsuri")
MOUNTED_WEAPONS = {0, 18, 19}
GAITS = ("walk", "trot", "canter", "gallop")
# The arena's floor inside its perimeter walls (SoraWorldBuilder.cpp).
ARENA_RECT = (-3150, -2550, 3150, 2550)
# Clearance a point keeps from a zone's walls and cover, and between the
# distinct points of one beat (cm).
WALL_CLEAR = 150
COVER_CLEAR = 60
POINT_SPACING = 250
ZONE_GAP = 2000
SITE_KINDS = {"training", "debt_seal", "irrigation", "workshop", "foundry", "ledger", "power", "supplies"}
MUTO_DEFEATS = ("disarm", "capture")
EN_MAX_CPS = 17
EN_LINE_CHARS, JA_LINE_CHARS, SUBTITLE_LINES = 42, 16, 2
MIN_LINE_S = 1.0
BLOCKING_MAX_S = 20.0
CHECKPOINT_GAP_S = 360
# Event families SoraCampaignDirector raises; rows naming them must name an
# event it can raise in their beat (director_event_error).
DIRECTOR_FAMILIES = ("rate_band", "boss_phase", "duel_phase", "duel_event", "intro_cinematic", "outro_cinematic",
                     "boss_defeated", "duel_won", "bout_scored", "bout_start", "wave_start", "wave_spawned",
                     "awase_success", "awase_fail", "marobashi_miss", "gate_complete", "gate_start", "step_start",
                     "step_failed", "step_complete", "item_picked", "item_delivered", "crank_released",
                     "output_complete", "exit_reached", "site_restored", "point", "match_lost", "loss_continue",
                     "collectible", "collectible_found")
# Scripted proposals in those families that nothing raises yet, each listed
# under "What the offline runtime does not do yet" in offline-acceptance.md.
UNRAISED_PROPOSALS = {
    "x_item_picked:sword_bundle": "ch03.b05's sword-bundle pickup and the loadout locked until it",
}
JAPANESE = re.compile(r"[぀-ヿ㐀-鿿]")


class CampaignError(AssertionError):
    pass


def require(condition, message):
    if not condition:
        raise CampaignError(message)


def load():
    catalog = json.loads((DATA / "catalog.json").read_text())
    campaign = json.loads((DATA / "campaign/campaign.json").read_text())
    chapters = [json.loads((DATA / entry["file"]).read_text()) for entry in campaign["chapters"]]
    legacy = json.loads(LEGACY_LINES.read_text())["lines"]
    bosses_path = DATA / "bosses.json"
    bosses = json.loads(bosses_path.read_text()) if bosses_path.is_file() else None
    return catalog, campaign, chapters, legacy, bosses


def boss_ids(bosses):
    """bosses.json is L3's file; accept a list of rows or an id-keyed map under `bosses`."""
    rows = bosses.get("bosses", bosses) if isinstance(bosses, dict) else bosses
    return set(rows) if isinstance(rows, dict) else {row["id"] for row in rows}


def requires_closure(beats):
    """beat id -> every beat it transitively requires."""
    closure = {}
    for beat in beats:
        found = set()
        for prior in beat["requires"]:
            found |= {prior} | closure[prior]
        closure[beat["id"]] = found
    return closure


def muto_hits(node, path, hits):
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "muto_eligible" and value:
                hits.append(path)
            muto_hits(value, path + [key], hits)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            muto_hits(value, path + [value.get("id", index) if isinstance(value, dict) else index], hits)


def pattern_tables(beat):
    tables = set()
    params, ext = beat["params"], beat["ext"]
    for phase in params.get("phases", []):
        tables.add(phase["pattern_table"])
    for entry in ext.get("pattern_tables", []) or []:
        tables.add(entry["table"] if isinstance(entry, dict) else entry)
    for key in ("opponent_pattern", "pattern_table"):
        value = ext.get(key)
        if isinstance(value, dict):
            tables.add(value["id"])
        elif isinstance(value, str):
            tables.add(value)
    return tables


def checkpoint_saves(beats, rows, explore):
    """Target times (cs) of the checkpoints SoraCampaignDirector writes on one route.

    Required beats play in order. A checkpoint beat saves as it begins, right
    after the required beat before it, and a boss or duel again at each later
    phase it saves at (its rows' offsets into the beat). An optional beat
    never begins: the route that opens the caches opens each at the first
    beat in play (not a cinematic) once the cache's requirements are met,
    spending the cache's target time there, and opening it saves again when
    the cache checkpoints and the active beat can be restored from its start
    (CompleteOptional). The chapter's end closes the last gap."""
    starts, elapsed = {}, 0
    for beat in beats:
        starts[beat["id"]] = elapsed * 100
        elapsed += beat["target_s"]
    saves, done, time = [], set(), 0
    for beat in beats:
        if beat["optional"]:
            continue
        if beat["checkpoint"]:
            saves.append(time)
        if explore and beat["type"] != "cinematic":
            for cache in beats:
                if cache["optional"] and cache["id"] not in done and set(cache["requires"]) <= done:
                    time += cache["target_s"] * 100
                    done.add(cache["id"])
                    if cache["checkpoint"] and beat["checkpoint"]:
                        saves.append(time)
        saves += [time + row["at_cs"] - starts[beat["id"]] for row in rows
                  if row["beat"] == beat["id"] and row["phase"] > 0]
        time += beat["target_s"] * 100
        done.add(beat["id"])
    return sorted(saves + [time])


def director_event_error(row, beat, offset, chapter):
    """Why SoraCampaignDirector can never raise a beat row's event, or None.

    Only the families the director raises are checked; events the AI lane or
    the world raise (pattern:, ai:, alert_state:, npc_downed:, ...) and
    free-form interact: and volume_enter: names are theirs. Any event may end
    in ":first", which plays on its first raise in the beat."""
    event = row["on"][:-6] if row["on"].endswith(":first") else row["on"]
    family, _, rest = event.partition(":")
    task, params = beat["task"], beat["params"]
    number = int(rest) if rest.isdigit() else None
    if event in UNRAISED_PROPOSALS:
        return None
    if re.fullmatch(r"(intro|outro)@[\d.]+", event) or family.startswith("x_") and family[2:] in DIRECTOR_FAMILIES:
        return "a scripted name the director never raises"
    if family == "rate_band":
        return None if task["goal"] == "turns" and rest in ("in", "above", "below") else "no such crank rate band"
    if family in ("boss_phase", "duel_phase"):
        kind = "boss" if family == "boss_phase" else "duel"
        ok = beat["type"] == kind and task["goal"] == "opponent_down" and number and number <= len(task["phases"])
        return None if ok else "no such phase"
    if family == "duel_event":
        return None if rest in task["phase_events"] else "no such duel event"
    if family in ("intro_cinematic", "outro_cinematic", "boss_defeated"):
        return None if beat["type"] == "boss" and not rest else "raised only in a boss fight"
    if family == "duel_won":
        return None if beat["type"] == "duel" and not rest else "raised only in a duel"
    if family in ("bout_scored", "bout_start"):
        first = offset if task["goal"] == "lessons" else 0
        ok = task["goal"] in ("lessons", "points") and number and first < number <= first + task["count"]
        return None if ok else f"bouts here run {first + 1}-{first + task['count']}"
    if family in ("wave_start", "wave_spawned") and rest:
        ids = {wave["id"] for wave in task["waves"]}
        return None if (number and number <= len(task["waves"])) or rest in ids else "no such wave"
    if family in ("awase_success", "awase_fail"):
        taught = task["goal"] == "lessons" and task["lesson_mask"] & 4
        ok = taught and (rest in ("early", "late") if family == "awase_fail" else number and number <= task["form_reps"][2])
        return None if ok else "no such awase"
    if family == "marobashi_miss":
        return None if task["flank_bouts"] else "raised only in a 転 lesson"
    if family in ("gate_complete", "gate_start"):
        gates = {gate["gate"] for gate in params.get("lesson_gates", [])}
        return None if rest in gates else "no such lesson gate"
    if family in ("step_start", "step_failed", "step_complete"):
        kind, _, count = rest.partition(":")
        kinds = [step["kind"] for step in task["steps"]]
        ok = kind in kinds and (family != "step_complete" or (count.isdigit() and 1 <= int(count) <= max(
            step["count"] for step in task["steps"] if step["kind"] == kind)))
        return None if ok else "no such manufacturing step"
    if family in ("item_picked", "item_delivered"):
        points = task["pickups"] if family == "item_picked" else task["dropoffs"]
        load = re.fullmatch(r"load_(\d\d)", rest) if family == "item_delivered" else None
        ok = rest in points or rest == task["carry_item"] or (load and 1 <= int(load[1]) <= task["count"])
        return None if ok else "no such pickup, drop-off, carried item or load"
    if family in ("crank_released", "output_complete", "exit_reached"):
        goal = {"crank_released": "turns", "output_complete": "steps", "exit_reached": "exit"}[family]
        return None if task["goal"] == goal else f"raised only on a {goal} task"
    if family == "site_restored":
        return None if number is not None and number == beat["site"] else "the beat restores no such site"
    if family == "point":
        return None if task["goal"] == "points" and rest in ("player", "rival") else "no such point"
    if family in ("match_lost", "loss_continue"):
        return None if task["goal"] == "points" else "raised only in a sparring match"
    if family in ("collectible", "collectible_found"):
        return None if rest in {item["id"] for item in chapter["collectibles"]} else "no such collectible"
    if event.startswith("event:crank_turn_"):
        turn = event[len("event:crank_turn_"):]
        return None if task["goal"] == "turns" and turn.isdigit() and 1 <= int(turn) <= task["count"] else "no such turn"
    return None


def allows_muto(beat):
    params = beat["params"]
    return params.get("finisher") == "muto_dori" or params.get("defeat") in MUTO_DEFEATS


def check_line(line, speakers, context):
    require(line["speaker"] in speakers, f"{context}: speaker {line['speaker']!r} is not in dialogue_speakers")
    require(line["ja"].strip() and JAPANESE.search(line["ja"]), f"{context}: Japanese text missing")
    require(line["en"].strip(), f"{context}: English subtitle missing")
    duration = line["duration_s"]
    require(isinstance(duration, (int, float)) and duration >= MIN_LINE_S,
            f"{context}: {duration} s is under the {MIN_LINE_S} s subtitle minimum")
    # Exact in tenths of a second: the scripts author durations to 0.1 s.
    tenths = round(duration * 10)
    require(abs(duration * 10 - tenths) < 1e-6, f"{context}: duration {duration} is not in tenths of a second")
    require(len(line["en"]) * 10 <= EN_MAX_CPS * tenths,
            f"{context}: {len(line['en'])} EN characters in {duration} s exceed {EN_MAX_CPS} cps")
    require(len(textwrap.wrap(line["en"], EN_LINE_CHARS)) <= SUBTITLE_LINES,
            f"{context}: EN subtitle needs more than {SUBTITLE_LINES} lines of {EN_LINE_CHARS}")
    require(len(line["ja"]) <= JA_LINE_CHARS * SUBTITLE_LINES,
            f"{context}: JA caption exceeds {SUBTITLE_LINES} lines of {JA_LINE_CHARS}")
    require("!" not in line["ja"] and "?" not in line["ja"], f"{context}: JA uses ASCII ! or ? (§18)")
    require("..." not in line["en"], f"{context}: EN ellipsis must be the single character … (§18)")


def _inside(rect, point, margin):
    x0, y0, x1, y1 = rect
    return x0 + margin <= point[0] <= x1 - margin and y0 + margin <= point[1] <= y1 - margin


def _clear_of_cover(cover, point, margin):
    return all(abs(point[0] - cx) >= sx / 2 + margin or abs(point[1] - cy) >= sy / 2 + margin
               for cx, cy, sx, sy, _ in cover)


def _length(points):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(points, points[1:]))


def _volume_events(beat, chapter):
    task = beat["task"]
    events = {task[key] for key in ("lines_event", "closing_event", "exit_event")}
    events |= {wave["event"] for wave in task["waves"]}
    events |= {row["on"] for row in chapter["triggers"] if row["beat"] == beat["id"]}
    return {event for event in events if event and event.startswith("volume_enter:")}


def check_space(chapter, beats, rewards, labels, where):
    """The chapter's space is one the world builder can build and the hero can play."""
    space = chapter["space"]
    zones = space["zones"]
    rects = [tuple(zone["rect"]) for zone in zones] + ([ARENA_RECT] if space["hub"] is not None else [])
    require(space["hub"] in (None, chapter["map"]), f"{where}: the hub is not the chapter's arena")
    for number, a in enumerate(rects):
        require(a[0] < a[2] and a[1] < a[3], f"{where}: zone {number} has an empty floor")
        for b in rects[number + 1:]:
            apart = a[2] + ZONE_GAP <= b[0] or b[2] + ZONE_GAP <= a[0] or a[3] + ZONE_GAP <= b[1] or b[3] + ZONE_GAP <= a[1]
            require(apart, f"{where}: zones {a} and {b} overlap or touch")
    for zone in zones:
        rect, cover = zone["rect"], zone["cover"]
        require(zone["style"] in ("estate", "ward", "foundry", "citadel") and
                zone["form"] in ("hall", "yard", "field", "route"), f"{where}: zone {zone['id']} style or form")
        require(len(zone["walls"]) == 4 and zone["wall_cm"] >= 200, f"{where}: zone {zone['id']} must be walled in")
        for piece in cover:
            require(_inside(rect, piece, max(piece[2], piece[3]) / 2 + WALL_CLEAR),
                    f"{where}: cover {piece[:2]} of {zone['id']} leaves no way past the wall")
        require(_inside(rect, zone["entry"], WALL_CLEAR) and _clear_of_cover(cover, zone["entry"], COVER_CLEAR),
                f"{where}: zone {zone['id']} entry")
        require((zone["form"] == "route") == bool(zone["route"]), f"{where}: zone {zone['id']} route")
        for point in zone["route"]:
            require(_inside(rect, point, 600), f"{where}: road {zone['id']} leaves its corridor at {point}")

    # The hub's buildings, cover, lantern poles and torii posts stand in for its cover.
    hub_blockers = [[(x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0, 0]
                    for x0, y0, x1, y1 in arena_blockers(space["hub"])] if space["hub"] is not None else []

    def zone_of(index):
        return (tuple(zones[index]["rect"]), zones[index]["cover"]) if index >= 0 else (ARENA_RECT, hub_blockers)

    def on_floor(index, point, what, cover_margin=COVER_CLEAR):
        rect, cover = zone_of(index)
        require(_inside(rect, point, WALL_CLEAR) and _clear_of_cover(cover, point, cover_margin),
                f"{what} at {point[:2]} is off its floor or inside a wall or cover")

    records = space["beats"]
    require([record["beat"] for record in records] == [beat["id"] for beat in beats], f"{where}: one space per beat")
    require(space["start"] == records[0]["entry"], f"{where}: the chapter starts at its first beat")
    for site, point in enumerate(space["sites"]):
        owner = next(beat for beat in beats if beat["site"] == site)
        index = records[beats.index(owner)]["zone"]
        # The hub's sites are the arena's own (SoraWorldBuilder.cpp); a zone's
        # site keeps clear of the zone's cover.
        if index < 0:
            require(_inside(ARENA_RECT, point, WALL_CLEAR), f"{where} site {site} is off the arena floor")
        else:
            on_floor(index, point, f"{where} site {site}", 150)
    for beat, record in zip(beats, records):
        task, index, what = beat["task"], record["zone"], beat["id"]
        routed = beat["type"] == "horseback_ride" or task["goal"] == "escort"
        require(routed == (record["route"] is not None) and
                (not routed or zones[index]["form"] == "route"), f"{what}: rides and escorts run on a route")
        on_floor(index, record["entry"], f"{what} entry")
        on_floor(index, record["anchor"], f"{what} anchor", 0)
        for key, count in (("objectives", len(task["objectives"])), ("pickups", len(task["pickups"])),
                           ("dropoffs", len(task["dropoffs"])), ("targets", len(task["targets"]))):
            require(len(record[key]) == count, f"{what}: {count} {key} in the task, {len(record[key])} placed")
        distinct = [record["anchor"]] + record["objectives"] + record["pickups"] + record["dropoffs"] + record["targets"]
        for key in ("objectives", "pickups", "dropoffs", "targets", "stations", "spawns"):
            for point in record[key]:
                on_floor(index, point, f"{what} {key}")
        if not routed:
            for number, a in enumerate(distinct):
                for b in distinct[number + 1:]:
                    require(math.hypot(a[0] - b[0], a[1] - b[1]) >= POINT_SPACING, f"{what}: points {a} and {b} coincide")
        for loop in record["patrols"]:
            for point in loop:
                on_floor(index, point, f"{what} patrol")
        require(record["spawns"] or not task["waves"] and beat["type"] not in ("duel", "boss", "stealth_zone"),
                f"{what}: opponents need spawns")
        if task["steps"]:
            require(record["stations"] and len(record["step_stations"]) == len(task["steps"]) and
                    all(0 <= station < len(record["stations"]) for station in record["step_stations"]),
                    f"{what}: every manufacturing step needs its station")
            for step in task["steps"]:
                require(step["kind"] in labels["step_kinds"], f"{what}: step {step['kind']} has no label")
        for target in task["targets"]:
            require(target["id"] in labels["targets"], f"{what}: target {target['id']} has no label")
        rect = zone_of(index)[0]
        placed = {volume["event"] for volume in record["volumes"]}
        named = _volume_events(beat, chapter)
        if record["mount"]:
            named |= {f"volume_enter:{name}" for name in record["mount"]["spooks"]}
            named |= {f"volume_enter:{entry['volume']}" for entry in record["mount"]["forced"]}
        require(placed == named, f"{what}: volumes {sorted(placed)} differ from its events {sorted(named)}")
        for volume in record["volumes"] + [record["exit"]]:
            require(_inside(rect, volume["center"], 0) and min(volume["size"]) >= 300, f"{what}: volume {volume}")
        if task["anchor_after_lines"]:
            require(record["closing"] is not None, f"{what}: a dialogue that ends at an anchor needs one")
            on_floor(index, record["closing"], f"{what} closing anchor", 0)
        if beat["type"] == "explore_optional":
            require(record["cache"] is not None, f"{what}: an explore beat needs its cache")
            on_floor(index, record["cache"], f"{what} cache")
        require((record["camera"] is not None) == (beat["type"] == "cinematic"), f"{what}: cinematic camera")
        kit = record["kit"]
        require(len(kit["targets"]) == len(task["targets"]) and len(kit["pickups"]) == len(task["pickups"]) and
                (beat["type"] == "horseback_ride" or len(kit["dropoffs"]) == len(task["dropoffs"])),
                f"{what}: kit kinds per point")
        if task["goal"] == "deliveries" and beat["type"] == "production_task":
            require(0 < task["carry_speed_permille"] <= 1000 and set(task["carry_weapons"]) <= {0},
                    f"{what}: carry pace and loadout")
        if routed:
            route = zones[index]["route"]
            length = _length(route)
            wanted = beat["ext"].get("route_length_m") or (beat["params"].get("escort") or {}).get("path_length_m")
            require(wanted is None or abs(length - wanted * 100) <= 2, f"{what}: route {length:.0f} cm, script {wanted} m")
            if task["goal"] == "escort":
                margin = record["route"]["margin_cm"]
                require(task["path_cm"] == round(length) - 2 * margin and task["path_cm"] > 0,
                        f"{what}: the escort walks {task['path_cm']} cm of a {length:.0f} cm route")
        mount = record["mount"]
        require((mount is not None) == (beat["type"] == "horseback_ride" or any(
            "mount" in phase for phase in beat["params"].get("phases", []))), f"{what}: horse")
        if mount:
            require(set(mount["weapons"]) <= MOUNTED_WEAPONS, f"{what}: mounted weapons {mount['weapons']}")
            require(set(mount["gaits"]) <= set(GAITS) and mount["gaits"], f"{what}: gaits {mount['gaits']}")
            speeds = mount["speeds_cm_s"]
            require(all(0 < a < b for a, b in zip(speeds, speeds[1:])), f"{what}: gait speeds must rise")
            require(set(mount["arcs"]) == {str(weapon) for weapon in mount["weapons"]} and
                    all(-180 <= arc[0] < arc[1] <= 180 for arc in mount["arcs"].values()), f"{what}: mounted arcs")
            require(not mount["arcs"].get("18") or mount["arcs"]["18"][1] <= 15,
                    f"{what}: the yumi shoots to the left from the saddle (bible §4.2)")
            require(not mount["tack"] or not mount["mounted"], f"{what}: a horse to tack up starts unmounted")
            on_floor(index, mount["at"], f"{what} horse")
            for spook in mount["spooks"]:
                require(f"volume_enter:{spook}" in placed, f"{what}: spook volume {spook} is not placed")
    found = [pickup["collectible"] for pickup in space["pickups"]]
    loose = [item["id"] for item in chapter["collectibles"] if item["id"] not in rewards]
    require(sorted(found) == sorted(loose), f"{where}: pickups {sorted(found)} for loose collectibles {sorted(loose)}")
    for pickup in space["pickups"]:
        on_floor(pickup["zone"], pickup["at"], f"{where} pickup {pickup['collectible']}")


def validate(catalog, campaign, chapters, legacy, bosses=None):
    speakers = {speaker["id"] for speaker in catalog["dialogue_speakers"]}
    require(catalog["schema_version"] == 4 and "chapters" not in catalog,
            "catalog.json must be schema 4 without the schema-3 chapter list")
    require(campaign["schema_version"] == 4, "campaign.json must be schema 4")
    require(len(campaign["chapters"]) == 8 == len(chapters), "the campaign has eight chapters")
    require(tuple(row["id"] for row in campaign["mechanics"]) == MECHANICS,
            "campaign mechanics must list the §12.1 flags in order")
    for group in ("mechanics", "step_kinds", "targets"):
        ids = [row["id"] for row in campaign[group]]
        require(len(ids) == len(set(ids)), f"campaign {group} repeat an id")
        for row in campaign[group]:
            require(JAPANESE.search(row["ja"]) and row["en"].strip() and not JAPANESE.search(row["en"]),
                    f"campaign {group} {row['id']}: bilingual label")
    labels = {group: {row["id"] for row in campaign[group]} for group in ("step_kinds", "targets")}
    categories = {row["id"]: row for row in campaign["collectible_categories"]}
    known_bosses = set(BOSSES) if bosses is None else set(BOSSES) & boss_ids(bosses)
    require(known_bosses == set(BOSSES), f"bosses.json lacks {sorted(set(BOSSES) - known_bosses)}")

    # Story flags: set once each by a beat, read by a later chapter's conditional lines.
    flags = campaign["story_flags"]
    require(isinstance(flags, list) and len(flags) == len(set(flags)) and len(flags) <= 16 and
            all(re.fullmatch(r"[a-z_]+", str(flag)) for flag in flags), "campaign story_flags must be unique names")
    flags_set, collectibles_seen = {}, set()
    campaign_total, unlocks, mechanics, line_ids = 0, [], [], set()
    optional_unlocks, grants = {}, {}
    category_counts = {name: 0 for name in categories}
    for index, (entry, chapter) in enumerate(zip(campaign["chapters"], chapters)):
        prefix = f"ch{index + 1:02d}"
        where = entry["id"]
        require(entry["file"] == f"campaign/chapter_{index + 1:02d}.json", f"{where}: file name")
        require(chapter["schema_version"] == 4 and chapter["index"] == index and chapter["id"] == entry["id"],
                f"{where}: chapter file id, index or schema")
        require(chapter["id"].startswith(prefix + "_"), f"{where}: id must start with {prefix}_")
        require(0 <= chapter["map"] < len(catalog["maps"]) and
                all(0 <= value < len(catalog["maps"]) for value in chapter["secondary_maps"]), f"{where}: map index")
        for field in ("title", "narrative", "objective"):
            source = chapter if field == "title" else entry
            require(JAPANESE.search(source[f"{field}_ja"]) and source[f"{field}_en"].strip(),
                    f"{where}: bilingual {field}")
        if "objective_ja" in chapter["ext"]:
            require((chapter["ext"]["objective_ja"], chapter["ext"]["objective_en"]) ==
                    (entry["objective_ja"], entry["objective_en"]), f"{where}: title-card objective differs from the script")
        beats = chapter["beats"]
        ids = [beat["id"] for beat in beats]
        require(ids == [f"{prefix}.b{number:02d}" for number in range(1, len(beats) + 1)],
                f"{where}: beat ids must run {prefix}.b01, b02, …")
        by_id = {beat["id"]: beat for beat in beats}
        closure = requires_closure(beats) if all(
            all(prior in ids[:position] for prior in beat["requires"]) for position, beat in enumerate(beats)) else None
        require(closure is not None, f"{where}: a beat requires a later or unknown beat")
        for beat in beats:
            require(not beat["optional"] or beat["type"] == "explore_optional",
                    f"{beat['id']}: only explore_optional beats may be optional")
            if not beat["optional"]:
                require(not any(by_id[prior]["optional"] for prior in closure[beat["id"]]),
                        f"{beat['id']}: a required beat depends on an optional one")
            require(beat["place"] in {place["id"] for place in chapter["places"]}, f"{beat['id']}: unknown place")

        # Rule 1: pacing.
        beat_total = sum(beat["target_s"] for beat in beats)
        target = CHAPTER_TARGET_S[index]
        require(chapter["target_s"] == target, f"{where}: target_s {chapter['target_s']} is not §10's {target}")
        require(abs(beat_total - target) * 20 <= target, f"{where}: beats total {beat_total} s, not within 5% of {target}")
        campaign_total += beat_total

        # Rule 2: sites.
        site_beats = [beat for beat in beats if beat["site"] is not None]
        require(sorted(beat["site"] for beat in site_beats) == [0, 1, 2], f"{where}: sites 0-2 must each be used once")
        require(all(not beat["optional"] for beat in site_beats), f"{where}: an optional beat restores a site")
        for earlier, later in zip(site_beats, site_beats[1:]):
            require(earlier["id"] in closure[later["id"]],
                    f"{where}: {later['id']} (site {later['site']}) does not require {earlier['id']} (site {earlier['site']})")
        expected_sites = [{"index": beat["site"], "beat": beat["id"],
                           "requires_sites": [site_beats[position - 1]["site"]] if position else []}
                          for position, beat in sorted(enumerate(site_beats), key=lambda item: item[1]["site"])]
        require(chapter["sites"] == expected_sites, f"{where}: site table disagrees with the beat chain")
        require(len(entry["sites"]) == 3, f"{where}: campaign.json needs three site labels")
        for site in entry["sites"]:
            require(site["kind"] in SITE_KINDS, f"{where}: site kind {site['kind']!r}")
            require(all(site[field].strip() for field in ("name_ja", "name_en", "restored_ja", "restored_en")) and
                    JAPANESE.search(site["name_ja"]) and JAPANESE.search(site["restored_ja"]), f"{where}: site label")

        # Rules 3 and 5, mechanics, bosses, enemies and rule 7.
        for beat in beats:
            unlocks += [(weapon, beat["id"]) for weapon in beat["unlocks"]["weapons"]]
            mechanics += beat["unlocks"]["mechanics"]
            if beat["optional"] and (beat["unlocks"]["weapons"] or beat["unlocks"]["mechanics"]):
                require(not beat["unlocks"]["mechanics"], f"{beat['id']}: an optional beat unlocks a mechanic")
                optional_unlocks[beat["id"]] = (set(beat["unlocks"]["weapons"]), beat["ext"].get("auto_grant_if_missed"))
            if beat["unlocks"]["grants"]:
                grants[beat["id"]] = set(beat["unlocks"]["grants"])
            for flag in beat["unlocks"]["story_flags"]:
                require(flag in flags and flag not in flags_set, f"{beat['id']}: story flag {flag!r} unknown or set twice")
                flags_set[flag] = beat["id"]
            params = beat["params"]
            if beat["registry"] is not None:
                require(beat["type"] == "production_task" or
                        (beat["type"] == "horseback_ride" and params["mode"] == "cargo"),
                        f"{beat['id']}: only production tasks and cargo rides write the registry")
            if beat["type"] == "horseback_ride":
                require(set(params["weapons"]) <= MOUNTED_WEAPONS, f"{beat['id']}: mounted weapons {params['weapons']}")
            if beat["type"] == "boss":
                require(params["boss"] in known_bosses, f"{beat['id']}: unknown boss {params['boss']!r}")
            waves = params.get("waves", [])
            lethal = 0
            for wave in waves:
                for enemy in wave["enemies"]:
                    kind = enemy["type"]
                    if kind in TRAINING_TARGETS:
                        require(params.get("target_kind") == "mato", f"{beat['id']}: training target outside the range")
                    else:
                        require(kind in ENEMIES, f"{beat['id']}: unknown enemy type {kind!r}")
                    if kind == "bound_conscript":
                        require(kind in params["nonlethal_types"], f"{beat['id']}: conscripts must be nonlethal")
                    if kind not in params.get("nonlethal_types", []):
                        lethal += enemy["count"]
            task = beat["task"]
            require(task["type"] == beat["type"] and task["goal"] is not None, f"{beat['id']}: the task has no goal")
            require(sum(wave["lethal"] for wave in task["waves"]) == lethal,
                    f"{beat['id']}: the task counts {sum(wave['lethal'] for wave in task['waves'])} lethal opponents, "
                    f"its waves {lethal}")
            complete = params.get("complete") or {}
            if complete.get("kind") == "defeat_count":
                require(complete["count"] <= lethal,
                        f"{beat['id']}: defeat_count {complete['count']} needs nonlethal enemies ({lethal} lethal)")

        # Rule 4: mutō-dori attacks only where the fight allows it.
        references = {}
        for beat in beats:
            for table in pattern_tables(beat):
                references.setdefault(table, []).append(beat)
        hits = []
        muto_hits(chapter["ext"], ["ext"], hits)
        for beat in beats:
            muto_hits(beat["ext"], [beat["id"], "ext"], hits)
            muto_hits(beat["params"], [beat["id"], "params"], hits)
        for path in hits:
            tables = [part for part in path if part in references]
            require(tables, f"{where}: mutō-dori attack at {path} belongs to no fight's pattern table")
            for table in tables:
                for beat in references[table]:
                    require(allows_muto(beat), f"{beat['id']}: table {table} has a mutō-dori attack, "
                                               "but the fight's defeat and finisher do not allow it")

        # Rule 8: checkpoint spacing, including the chapter's end, where the
        # runtime writes its saves, on the route that skips the explore beats
        # and on the one that opens every cache.
        positions = sorted(row["at_cs"] for row in chapter["checkpoints"])
        require(positions and positions[0] == 0, f"{where}: the first beat must checkpoint")
        for explore in (False, True):
            saves = checkpoint_saves(beats, chapter["checkpoints"], explore)
            gap = max(b - a for a, b in zip(saves, saves[1:]))
            require(gap <= CHECKPOINT_GAP_S * 100,
                    f"{where}: {gap / 100:g} target seconds between checkpoints "
                    f"({'opening' if explore else 'skipping'} the caches)")

        # Rule 6 and line references.
        lines = {}
        for line in chapter["lines"]:
            require(line["id"] not in lines and line["id"] not in line_ids, f"{line['id']}: line id used twice")
            require(line["beat"] is None or line["beat"] in by_id, f"{line['id']}: unknown beat")
            check_line(line, speakers, line["id"])
            lines[line["id"]] = line
        line_ids |= set(lines)
        scheduled = set()
        # Lesson bouts are numbered across the chapter's lesson duels.
        offsets, bouts = {}, 0
        for beat in beats:
            offsets[beat["id"]] = bouts
            if beat["task"]["goal"] == "lessons":
                bouts += beat["task"]["count"]
        for row in chapter["triggers"]:
            context = f"{where} trigger {row['beat']} {row['on']}"
            require(row["beat"] is None or row["beat"] in by_id, f"{context}: unknown beat")
            if row["beat"] is not None:
                problem = director_event_error(row, by_id[row["beat"]], offsets[row["beat"]], chapter)
                require(problem is None, f"{context}: {problem}")
            require(row["lines"], f"{context}: no lines")
            missing = [line for line in row["lines"] if line not in lines]
            require(not missing, f"{context}: references missing lines {missing}")
            scheduled.update(row["lines"])
            if row["mode"] == "blocking":
                total = sum(lines[line]["duration_s"] for line in row["lines"])
                require(total <= BLOCKING_MAX_S, f"{context}: blocking dialogue runs {total:g} s")
            condition = row["requires_flag"]
            if condition is not None:
                kind, _, name = condition.partition(":")
                known = {prefix + ".c%02d" % number for number in range(1, 7)} | collectibles_seen \
                    if kind == "collectible" else set(flags_set)
                require(name in known, f"{context}: requires {condition!r}, which no earlier beat or find provides")
            if row["at_ms"] is not None:
                beat = by_id[row["beat"]]
                require(beat["type"] == "cinematic" and 0 <= row["at_ms"] <= beat["params"]["duration_s"] * 1000,
                        f"{context}: subtitle time outside its cinematic")
        unscheduled = sorted(set(lines) - scheduled)
        require(not unscheduled, f"{where}: lines no trigger plays: {unscheduled}")

        # Collectibles and HUD prompts.
        collectibles = chapter["collectibles"]
        require([item["id"] for item in collectibles] == [f"{prefix}.c{number:02d}" for number in range(1, 7)],
                f"{where}: six collectibles {prefix}.c01-c06")
        require(sorted(item["mask_bit"] for item in collectibles) == list(range(6)), f"{where}: collectible mask bits")
        for item in collectibles:
            require(item["category"] in categories, f"{item['id']}: category")
            category_counts[item["category"]] += 1
            require(item["place"] in {place["id"] for place in chapter["places"]}, f"{item['id']}: unknown place")
            require(all(beat in by_id for beat in item["beats"]), f"{item['id']}: unknown beat")
            require(JAPANESE.search(item["codex"]["ja"]) and item["codex"]["en"].strip(), f"{item['id']}: codex")
        collectibles_seen |= {item["id"] for item in collectibles}
        rewards = {reward for beat in beats if beat["type"] == "explore_optional"
                   for reward in beat["params"].get("rewards", []) if re.fullmatch(r"ch\d\d\.c\d\d", str(reward))}
        require(rewards <= {item["id"] for item in collectibles}, f"{where}: explore rewards name unknown collectibles")
        check_space(chapter, beats, rewards, labels, where)
        prompt_ids = [prompt["id"] for prompt in chapter["ui_prompts"]]
        require(len(prompt_ids) == len(set(prompt_ids)), f"{where}: HUD prompt ids repeat")
        for prompt in chapter["ui_prompts"]:
            require(all(beat in by_id for beat in prompt["beats"]), f"{prompt['id']}: unknown beat")
            require(JAPANESE.search(prompt["ja"]) and prompt["en"].strip(), f"{prompt['id']}: bilingual prompt")

    require(CAMPAIGN_TARGET_RANGE_S[0] <= campaign_total <= CAMPAIGN_TARGET_RANGE_S[1],
            f"campaign total {campaign_total} s is outside {CAMPAIGN_TARGET_RANGE_S}")
    require(category_counts == {name: row["count"] for name, row in categories.items()},
            f"collectible categories {category_counts}")
    # Rule 3: each weapon once, at its §11 beat, in §11 order.
    weapons = [weapon for weapon, _ in unlocks]
    require(sorted(weapons) == list(range(21)), f"weapons 0-20 must each unlock once, got {sorted(weapons)}")
    require(dict(unlocks) == dict(WEAPON_UNLOCKS), "weapon unlock beats differ from bible §11")
    order = [beat for _, beat in unlocks]
    require(order == sorted(order) and [beat for _, beat in WEAPON_UNLOCKS] == sorted(order),
            "weapon unlocks are out of §11 order")
    require(sorted(mechanics) == sorted(MECHANICS), f"mechanic flags must each unlock once: {sorted(mechanics)}")
    require(set(flags_set) == set(flags), f"story flags no beat sets: {sorted(set(flags) - set(flags_set))}")
    # A missed optional pickup is granted at a later beat, so every route ends
    # with the same mask; the grant is not a second unlock.
    covered = {}
    for beat_id, (weapons_here, grant_beat) in optional_unlocks.items():
        require(grant_beat is not None and grant_beat > beat_id and weapons_here <= grants.get(grant_beat, set()),
                f"{beat_id}: optional weapons {sorted(weapons_here)} need a later auto-grant")
        covered.setdefault(grant_beat, set()).update(weapons_here)
    require(covered == grants, f"auto-grants {grants} must restore exactly the optional pickups {covered}")

    # The 25 schema-3 cues, verbatim.
    by_line = {line["id"]: (chapter["id"], line) for chapter in chapters for line in chapter["lines"]}
    require(len(legacy) == 25, "the schema-3 fixture holds 25 cues")
    for cue in legacy:
        found = by_line.get(cue["line"])
        require(found is not None, f"schema-3 cue {cue['chapter']} line {cue['index']} is missing ({cue['line']})")
        chapter_id, line = found
        require(chapter_id == cue["chapter"] and line["ja"] == cue["ja"] and line["en"] == cue["en"] and
                line["speaker"] == cue["speaker"],
                f"schema-3 cue {cue['chapter']} line {cue['index']} changed ({cue['line']})")
    return {"beats": sum(len(chapter["beats"]) for chapter in chapters), "lines": len(line_ids),
            "triggers": sum(len(chapter["triggers"]) for chapter in chapters), "target_s": campaign_total,
            "checkpoints": sum(len(chapter["checkpoints"]) for chapter in chapters)}


def self_test(catalog, campaign, chapters, legacy):
    """Every mutation below breaks one rule; the validator must reject each."""
    def beat(data, beat_id):
        chapter = data[2][int(beat_id[2:4]) - 1]
        return next(item for item in chapter["beats"] if item["id"] == beat_id)

    def line(data, line_id):
        chapter = data[2][int(line_id[2:4]) - 1]
        return next(item for item in chapter["lines"] if item["id"] == line_id)

    def swap_unlock(data):
        beat(data, "ch01.b07")["unlocks"]["weapons"] = [0]
        beat(data, "ch01.b12")["unlocks"]["weapons"] = [18]

    def fast_line(data):
        line(data, "ch01.b01.sekireisai.001")["en"] = "Stop. " * 5

    def long_gap(data):
        beat(data, "ch01.b11")["checkpoint"] = False
        data[2][0]["checkpoints"] = [row for row in data[2][0]["checkpoints"] if row["beat"] != "ch01.b11"]

    def cache_without_save(data):
        # Opening ch01.b08's cache no longer saves: the completist's detour
        # through the wood runs 510 s between checkpoints.
        beat(data, "ch01.b08")["checkpoint"] = False
        data[2][0]["checkpoints"] = [row for row in data[2][0]["checkpoints"] if row["beat"] != "ch01.b08"]

    def gun_on_horse(data):
        beat(data, "ch02.b08")["params"]["weapons"].append(5)

    def site_table_mismatch(data):
        beat(data, "ch01.b02")["site"], beat(data, "ch01.b09")["site"] = 2, 0

    def site_chain_broken(data):
        beat(data, "ch01.b09")["requires"] = ["ch01.b01"]

    def orphan_line(data):
        data[2][0]["triggers"] = [row for row in data[2][0]["triggers"]
                                  if "ch01.b01.sekireisai.001" not in row["lines"]]

    def dangling_line(data):
        data[2][0]["triggers"][0]["lines"].append("ch01.b01.sekireisai.999")

    def unknown_speaker(data):
        line(data, "ch01.b01.sekireisai.001")["speaker"] = "narrator"

    def legacy_edit(data):
        line(data, "ch04.b01.taemon.001")["en"] += " Again."

    def muto_everywhere(data):
        beat(data, "ch06.b09")["params"]["finisher"] = "none"

    def conscript_quota(data):
        target = beat(data, "ch03.b08")
        count = sum(enemy["count"] for wave in target["params"]["waves"] for enemy in wave["enemies"]
                    if enemy["type"] not in target["params"]["nonlethal_types"])
        target["params"]["complete"] = {"kind": "defeat_count", "count": count + 1}

    def pacing(data):
        beat(data, "ch05.b16")["target_s"] += 600

    def registry_on_combat(data):
        beat(data, "ch02.b02")["registry"] = dict(beat(data, "ch02.b05")["registry"])

    def lost_pickup(data):
        beat(data, "ch07.b01")["unlocks"]["grants"] = []

    def unknown_boss(data):
        beat(data, "ch02.b15")["params"]["boss"] = "boss_nobody"

    def optional_site(data):
        beat(data, "ch01.b08")["site"], beat(data, "ch01.b09")["site"] = 2, None

    def story_flag_twice(data):
        beat(data, "ch07.b06")["unlocks"]["story_flags"] = ["nafudakake_marked"]

    def unmet_condition(data):
        next(row for row in data[2][7]["triggers"] if row["requires_flag"])["requires_flag"] = "story:festival_lit"

    def blocking_speech(data):
        row = next(row for row in data[2][1]["triggers"] if row["mode"] == "blocking")
        row["lines"] = [line["id"] for line in data[2][1]["lines"][:12]]

    def space(data, number, beat_id):
        return next(record for record in data[2][number]["space"]["beats"] if record["beat"] == beat_id)

    def anchor_in_wall(data):
        record = space(data, 3, "ch04.b06")
        record["anchor"] = [data[2][3]["space"]["zones"][record["zone"]]["rect"][0] - 50, 0]

    def short_route(data):
        zone = next(zone for zone in data[2][7]["space"]["zones"] if zone["id"] == "route:ch08.b02")
        zone["route"] = zone["route"][:-3]

    def missing_volume(data):
        space(data, 0, "ch01.b05")["volumes"].pop()

    def zones_collide(data):
        data[2][4]["space"]["zones"][1]["rect"] = list(data[2][4]["space"]["zones"][0]["rect"])

    def lost_collectible(data):
        data[2][0]["space"]["pickups"].pop()

    def unlabelled_step(data):
        data[1]["step_kinds"] = [row for row in data[1]["step_kinds"] if row["id"] != "quench"]

    def yumi_to_the_right(data):
        space(data, 1, "ch02.b08")["mount"]["arcs"]["18"] = [-15, 170]

    def spawn_in_building(data):
        space(data, 2, "ch03.b16")["spawns"][0] = [1850, 1100]

    def trigger(data, beat_id, event):
        chapter = data[2][int(beat_id[2:4]) - 1]
        return next(row for row in chapter["triggers"] if row["beat"] == beat_id and row["on"] == event)

    def boss_cue_time(data):
        trigger(data, "ch02.b15", "intro_cinematic")["on"] = "intro@6.0"

    def unraised_rate_band(data):
        trigger(data, "ch05.b06", "rate_band:in:first")["on"] = "rate_band:inside:first"

    def bout_numbered_per_beat(data):
        trigger(data, "ch01.b04", "bout_scored:3")["on"] = "bout_scored:1"

    def short_escort(data):
        next(beat for beat in data[2][7]["beats"] if beat["id"] == "ch08.b07")["task"]["path_cm"] -= 400

    validate(*copy.deepcopy((catalog, campaign, chapters, legacy)))
    mutations = (anchor_in_wall, short_route, missing_volume, zones_collide, lost_collectible, unlabelled_step,
                 yumi_to_the_right, short_escort, spawn_in_building, swap_unlock, fast_line, long_gap, cache_without_save,
                 boss_cue_time, unraised_rate_band, bout_numbered_per_beat,
                 gun_on_horse, site_table_mismatch, site_chain_broken, orphan_line, dangling_line,
                 unknown_speaker, legacy_edit, muto_everywhere, conscript_quota, pacing, registry_on_combat,
                 lost_pickup, unknown_boss, optional_site, blocking_speech, story_flag_twice, unmet_condition)
    for mutate in mutations:
        data = copy.deepcopy((catalog, campaign, chapters, legacy))
        mutate(data)
        try:
            validate(*data)
        except CampaignError:
            continue
        raise CampaignError(f"self-test: the validator accepted the {mutate.__name__} mutation")
    return len(mutations)


def check_project():
    catalog, campaign, chapters, legacy, bosses = load()
    summary = validate(catalog, campaign, chapters, legacy, bosses)
    rejected = self_test(catalog, campaign, chapters, legacy)
    return (f"Campaign schema 4 passed the bible's eight rules: {summary['beats']} beats, {summary['lines']} "
            f"bilingual lines on {summary['triggers']} triggers, {summary['checkpoints']} checkpoints, "
            f"{summary['target_s']} target seconds, 21 weapon unlocks in §11 order, 25 schema-3 cues verbatim; "
            f"self-test rejected {rejected} bad variants")


if __name__ == "__main__":
    print(check_project())
