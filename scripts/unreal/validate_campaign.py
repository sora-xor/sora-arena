"""Validate the schema-4 offline campaign against the story bible's rules.

Reads Content/Data/catalog.json (speakers), Content/Data/campaign/campaign.json
(the hand-authored chapter index, title cards and site labels) and the eight
generated chapter files, and checks the bible's §12.3 rules:

1. pacing: each chapter's beat target_s within ±5% of its §10 minutes, and the
   campaign total within 21,600-28,800 s;
2. production sites 0-2 each restored once per chapter, in the order the
   beats' requires chain enforces;
3. weapons 0-20 each unlocked exactly once, at the §11 beat, in §11 order;
4. boss ids from §8, each staged by its bosses.json fight at that beat, the
   rival duels bosses.json stages at theirs, wave and guard enemy types from
   enemies.json (whose roster is the bible's §7), guards posted in every
   stealth zone and every production task under guard (its patrolling wave
   members and x_guards) and nowhere else, and mutō-dori attacks only in
   fights whose defeat or finisher allows mutō-dori;
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
event that never comes. Every HUD prompt names its keys only as {Action}
tokens for input actions in Config/DefaultInput.ini, the same in both
languages, which the HUD replaces with the player's own keys; a bracketed
control name ([Guard], ［調べる］) is refused.

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
from campaign_registry import validate_registry
from campaign_crank import player_work

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "Content/Data"
LEGACY_LINES = ROOT / "scripts/unreal/fixtures/campaign_legacy_lines.json"
INPUT = ROOT / "Config/DefaultInput.ini"

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
                     "collectible", "collectible_found", "maai_step_ok", "gate_retry")
# Scripted proposals in those families that nothing raises yet, each listed
# under "What the offline runtime does not do yet" in offline-acceptance.md.
UNRAISED_PROPOSALS = {}
JAPANESE = re.compile(r"[぀-ヿ㐀-鿿]")
# A HUD prompt's key token, and a control named in brackets instead.
KEY_TOKEN = re.compile(r"\{([^{}]*)\}")
BRACKETED_CONTROL = re.compile(r"[\[［【][^\]］】]*[\]］】]")


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
    # The AI lane's fights and archetypes (validate_enemies.py checks their own
    # rules), and the input actions a HUD prompt may name.
    roster = {"bosses": json.loads((DATA / "bosses.json").read_text()), "enemies": json.loads((DATA / "enemies.json").read_text()),
              "actions": sorted(set(re.findall(r'^\+ActionMappings=\(ActionName="(\w+)"', INPUT.read_text(), re.MULTILINE)))}
    return catalog, campaign, chapters, legacy, roster


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
    event = re.sub(r"\+[0-9]+(?:\.[0-9]+)?s$", "", event)
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
    if family == "maai_step_ok" or family == "gate_retry" and rest == "maai_step":
        return None if task["maai"] else "raised only in a measured maai lesson"
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
        recovery = task.get("recovery")
        ok = rest in points or rest == task["carry_item"] or (family == "item_picked" and recovery and rest == recovery["item"]) or (load and 1 <= int(load[1]) <= task["count"])
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
    """The volumes a beat's events name: its task's, its lines' and its HUD
    prompts', but those on a climbing face, which its fieldcraft raises."""
    task = beat["task"]
    events = {task[key] for key in ("lines_event", "closing_event", "exit_event")}
    events |= {wave["event"] for wave in task["waves"]}
    events |= {row["on"] for row in chapter["triggers"] if row["beat"] == beat["id"]}
    events |= {row["on"] for row in chapter["ui_prompts"] if beat["id"] in row["beats"]}
    # A ride's road objectives (ch08.b02's seal stakes) stand in their volumes.
    if beat["type"] == "horseback_ride":
        events |= {f"volume_enter:{row['volume']}" for row in beat["params"].get("objectives") or [] if row.get("volume")}
    record = next(row for row in chapter["space"]["beats"] if row["beat"] == beat["id"])
    climb = record["fieldcraft"]["climb"]
    owned = set(climb["ledge_events"]) | {climb["top_event"]} if climb else set()
    return {event for event in events if event and event.startswith("volume_enter:") and event not in owned}


def check_space(chapter, beats, rewards, labels, where):
    """The chapter's space is one the world builder can build and the hero can play."""
    from campaign_ridge import wind_valid
    require(wind_valid(chapter), f"{where}: exposed ridge/wind contract")
    from campaign_wood import wood_valid
    require(wood_valid(chapter), f"{where}: optional wood physical/reward contract")
    space = chapter["space"]
    zones = space["zones"]
    rects = [tuple(zone["rect"]) for zone in zones] + ([ARENA_RECT] if space["hub"] is not None else [])
    require(space["hub"] in (None, chapter["map"]), f"{where}: the hub is not the chapter's arena")
    for number, a in enumerate(rects):
        require(a[0] < a[2] and a[1] < a[3], f"{where}: zone {number} has an empty floor")
        for other,b in enumerate(rects[number + 1:],number+1):
            apart = a[2] + ZONE_GAP <= b[0] or b[2] + ZONE_GAP <= a[0] or a[3] + ZONE_GAP <= b[1] or b[3] + ZONE_GAP <= a[1]
            if not apart and number<len(zones) and other<len(zones):
                za,zb=zones[number].get('z_bounds_cm'),zones[other].get('z_bounds_cm')
                apart=bool(za and zb and (za[1]<=zb[0] or zb[1]<=za[0]))
            require(apart, f"{where}: zones {a} and {b} overlap or touch")
    for zone in zones:
        expected_z = [-500,15800] if chapter["id"].startswith("ch08_") and zone["place"]=="pl_ledger_spire" else [15800,20000] if chapter["id"].startswith("ch08_") and zone["place"]=="pl_ledger_engine" else [-2000,2500] if chapter["id"].startswith("ch07_") and zone["place"]=="pl_hull_ridge" else None
        require(zone.get("z_bounds_cm")==expected_z,f"{where}: authored vertical place {zone['id']}")
        rect, cover = zone["rect"], zone["cover"]
        require(zone["style"] in ("estate", "ward", "foundry", "citadel") and
                zone["form"] in ("hall", "yard", "field", "route"), f"{where}: zone {zone['id']} style or form")
        wood_counts = {"pl_matoba": 5, "pl_issoseki_wood": 0, "pl_dojo_smithy": 5} if chapter["id"].startswith("ch01_") else {}
        if chapter["id"].startswith("ch07_"): wood_counts.update(pl_hull_ridge=0,pl_hangar=0)
        require(len(zone["walls"]) == wood_counts.get(zone["place"], 4) and zone["wall_cm"] >= 200,
                f"{where}: zone {zone['id']} wall/door contract")
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

    elevated_rect = None
    def on_floor(index, point, what, cover_margin=COVER_CLEAR):
        rect, cover = (elevated_rect, []) if elevated_rect is not None else zone_of(index)
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
        elevated_rect = None
        if what == "ch08.b12":
            elevated_rect = next(row["lift"]["gallery_rect"] for row in records if row["beat"] == "ch08.b11")
        require(record["height_cm"] == (2700 if what == "ch08.b11" else 14200 if what == "ch08.b12" else 16000 if record.get("summit") else 0),
                f"{what}: authored floor height")
        routed = beat["type"] == "horseback_ride" or task["goal"] == "escort"
        require(routed == (record["route"] is not None) and
                (not routed or zones[index]["form"] == "route"), f"{what}: rides and escorts run on a route")
        on_floor(index, record["entry"], f"{what} entry")
        on_floor(index, record["anchor"], f"{what} anchor", 0)
        for key, count in (("objectives", len(task["objectives"])), ("pickups", len(task["pickups"])),
                           ("dropoffs", len(task["dropoffs"])), ("targets", len(task["targets"]))):
            require(len(record[key]) == count, f"{what}: {count} {key} in the task, {len(record[key])} placed")
        distinct = [record["anchor"]] + record["objectives"] + record["pickups"] + record["dropoffs"] + record["targets"]
        require((record.get("recovery") is not None) == (task.get("recovery") is not None), f"{what}: recovery requires a well")
        if task.get("recovery"):
            on_floor(index, record["recovery"], f"{what} recovery well", 350)
            distinct.append(record["recovery"])
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
        rect = elevated_rect if elevated_rect is not None else zone_of(index)[0]
        placed = {volume["event"] for volume in record["volumes"]}
        named = _volume_events(beat, chapter)
        if record["mount"]:
            named |= {f"volume_enter:{name}" for name in record["mount"]["spooks"]}
            named |= {f"volume_enter:{entry['volume']}" for entry in record["mount"]["forced"]}
        require(placed == named, f"{what}: volumes {sorted(placed)} differ from its events {sorted(named)}")
        for volume in record["volumes"] + [record["exit"]]:
            volume_rect = zones[next(r["zone"] for r in records if r["beat"]=="ch08.b13")]["rect"] if what=="ch08.b12" and volume.get("floor_cm")==16000 else rect
            require(_inside(volume_rect, volume["center"], 0) and min(volume["size"]) >= 300, f"{what}: volume {volume}")
        # Match SoraCatalogSpace's presence checks in both directions: a
        # cinematic cannot acquire an interaction anchor just for set dressing.
        require((record["closing"] is not None) == task["anchor_after_lines"], f"{what}: closing anchor must match its task")
        if task["anchor_after_lines"]:
            on_floor(index, record["closing"], f"{what} closing anchor", 0)
        require((record["cache"] is not None) == (task["goal"] == "cache"), f"{what}: optional cache must match its task")
        if task["goal"] == "cache":
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
        check_fieldcraft(beat, record, index, zones, zone_of, on_floor)
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
    elevated_rect = None
    found = [pickup["collectible"] for pickup in space["pickups"]]
    loose = [item["id"] for item in chapter["collectibles"] if item["id"] not in rewards]
    require(sorted(found) == sorted(loose), f"{where}: pickups {sorted(found)} for loose collectibles {sorted(loose)}")
    for pickup in space["pickups"]:
        on_floor(pickup["zone"], pickup["at"], f"{where} pickup {pickup['collectible']}")


GUARD_KEYS = {"type", "sight_cm", "dark_sight_cm", "view_deg", "hearing_cm", "suspicion_permille", "post", "scan_deg",
              "scan_ms", "turn_ms"}
STEALTH_KEYS = {"rate_permille", "suspicious_at_permille", "search_ms", "wary_permille", "rear_takedowns",
                "lethal_default", "bodies", "drag", "carryover_to"}
FIELDCRAFT_KEYS = {"lamps", "surfaces", "water", "climb", "stones", "candle", "party", "signal", "hide_spots",
                   "releases", "allies", "people", "volley", "alarms", "nets", "searchlights", "bell", "fires", "ladders",
                   "charge"}
NET_KEYS = {"quarry", "windup_ms", "haul_ms", "cut_ms", "saddle_weapon", "saddle_side", "tether", "halts", "net_waves",
            "nets_per_wave", "scout_waves", "cross_wave", "cross_at_cm", "lost_event"}
LIGHT_KEYS = {"id", "at", "height_cm", "yaw", "reach_cm", "road_from_cm", "road_to_cm", "sweep_deg", "period_ms", "spot_cm",
              "suspicious_ms", "alert_ms", "lock_ms", "active_on", "spooks"}
# SoraStealthRules::NoiseRadiusCm(ENoise::Landing): the thud of a drop off a roof.
LANDING_NOISE_CM = 900
# The hold's reach round its anchor (SoraCampaignReach::Hold): a cook-fire is relit without leaving the hold.
HOLD_REACH_CM = 420
ALLY_KINDS = {"fighter", "shooter", "rank", "guide", "bystander"}
VOLLEY_KEYS = {"ranks", "per_rank", "weapon", "order_delay_ms", "cycle_ms", "radius_cm", "range_cm", "smoke_ms", "auto_order"}


def check_fieldcraft(beat, record, index, zones, zone_of, on_floor):
    """The beat's fieldcraft (campaign_fieldcraft.py) is one USoraFieldcraft can play."""
    craft, what = record["fieldcraft"], beat["id"]
    rect, _ = zone_of(index)
    require(set(craft) == FIELDCRAFT_KEYS, f"{what}: fieldcraft keys {sorted(craft)}")

    def area(row, label):
        require(_inside(rect, row["center"], 0) and min(row["size"]) > 0, f"{what}: {label} {row} is off its floor")

    for lamp in craft["lamps"]:
        require(lamp["snuff"] in ("hold", "shot", "none") and lamp["radius_cm"] > 0 and lamp["relight_ms"] >= 0 and
                (lamp["snuff"] == "hold") == (lamp["hold_ms"] > 0), f"{what}: lamp {lamp['id']} rules")
        on_floor(index, lamp["at"], f"{what} lamp {lamp['id']}")
    roofs = {ladder["height_cm"] for ladder in craft["ladders"]}
    for surface in craft["surfaces"]:
        area(surface, f"{surface['kind']} floor")
        require(0 <= surface["crouch_permille"] <= 10000 and 0 < surface["step_permille"] <= 10000 and
                (surface["height_cm"] == 0 or surface["height_cm"] in roofs), f"{what}: {surface['kind']} floor loudness")
    water = craft["water"]
    if water:
        area(water, "water")
        require(min(water[key] for key in ("surface_cm_s", "dive_cm_s", "breath_ms", "recover_ms")) > 0 and
                water["drown_hp_s"] >= 0 and water["surface_step_permille"] > 0, f"{what}: swimming rules")
        for row in water["cover"] + water["lines"]:
            area(row, "water cover or float line")
    climb = craft["climb"]
    if climb:
        require(zones[index]["form"] != "route" and climb["holds"] > 0 and climb["holds"] < 32 and
                0 < climb["grip_per_hold"] * climb["holds"] <= 100 and climb["regen_per_s"] >= 0 and
                all(0 < hold < climb["holds"] for hold in climb["ledges"]) and
                len(climb["ledges"]) == len(climb["ledge_events"]) and 0 < climb["hurt_cm"] < climb["lethal_cm"],
                f"{what}: climbing rules")
        x0, y0, x1, y1 = rect
        require(climb["width_cm"] == y1 - y0 and climb["at"][0] + climb["depth_cm"] < x1 and
                record["entry"][0] < climb["at"][0] and climb["at"][0] < record["exit"]["center"][0],
                f"{what}: the climbing face must bar the way to the exit wall to wall, with the entry before it")
    stones = craft["stones"]
    if stones:
        require(stones["max"] > 0 and 0 <= stones["carried"] <= stones["max"] and stones["noise_cm"] > 0 and
                stones["investigate_ms"] > 0 and (stones["carried"] > 0 or stones["piles"]), f"{what}: tsubute")
        for pile in stones["piles"]:
            on_floor(index, pile, f"{what} rubble", 0)
    candle = craft["candle"]
    if candle:
        require(candle["visibility_permille"] > candle["cupped_permille"] >= 1000 and
                0 < candle["cupped_rate_permille"] < 1000 and candle["radius_cm"] > 0, f"{what}: candle")
    escort = beat["task"]["goal"] == "escort"
    ids = [member["id"] for member in craft["party"]]
    require(len(ids) == len(set(ids)) and (not escort or ids), f"{what}: the escorted party")
    require(not craft["party"] or escort, f"{what}: only an escort has a party")
    for member in craft["party"]:
        require(member["health"] > 0 and member["revive_ms"] > 0 and member["bleedout_ms"] >= 0 and
                member["lance_ms"] >= 0 and -1 <= member["release"] < len(craft["releases"]) and
                (member["release"] < 0 or member["free_ms"] == craft["releases"][member["release"]]["hold_ms"]),
                f"{what}: party member {member['id']}")
    require(craft["signal"] == bool(craft["hide_spots"]) and (not craft["signal"] or escort), f"{what}: hide on signal")
    for spot in craft["hide_spots"]:
        on_floor(index, spot, f"{what} hide spot")
    for release in craft["releases"]:
        require(release["hold_ms"] > 0, f"{what}: cell door {release['id']}")
        on_floor(index, release["at"], f"{what} cell door {release['id']}")
    ally_ids = [ally["id"] for ally in craft["allies"]]
    require(len(ally_ids) == len(set(ally_ids)) and not set(ally_ids) & set(ids), f"{what}: allies repeat an id")
    for ally in craft["allies"]:
        require(ally["role"] in ALLY_KINDS and ally["health"] > 0 and ally["revive_ms"] > 0 and
                (ally["weapon"] == -1) == (ally["role"] in ("guide", "bystander")) and -1 <= ally["weapon"] <= 20 and
                (ally["rank"] >= 0) == (ally["role"] == "rank") and ally["rank"] < 4 and
                (ally["joins"] is None or re.fullmatch(r"wave_start:\d+", ally["joins"]) and
                 int(ally["joins"].split(":")[1]) <= len(beat["task"]["waves"])), f"{what}: ally {ally['id']}")
        on_floor(index, ally["at"], f"{what} ally {ally['id']}")
    # SoraFieldcraftRules::FVolleyRules: up to four ranks, each a full row of gunners with the volley's arm.
    volley = craft["volley"]
    gunners = [ally for ally in craft["allies"] if ally["role"] == "rank"]
    require(bool(volley) == bool(gunners), f"{what}: volley ranks without a volley, or a volley without ranks")
    if volley:
        require(set(volley) == VOLLEY_KEYS and 0 < volley["ranks"] <= 4 and volley["per_rank"] > 0 and
                volley["order_delay_ms"] >= 0 and min(volley["cycle_ms"], volley["radius_cm"], volley["range_cm"]) > 0 and
                sorted({ally["rank"] for ally in gunners}) == list(range(volley["ranks"])) and
                all(sum(ally["rank"] == rank for ally in gunners) == volley["per_rank"] for rank in range(volley["ranks"])) and
                all(ally["weapon"] == volley["weapon"] and ally["joins"] is None for ally in gunners),
                f"{what}: volley ranks")
    check_fieldcraft_sets(beat, record, index, zones, craft, area, on_floor)
    defended = [person for person in craft["people"] if person["target"] != -1]
    people = [person["target"] for person in defended]
    kinds = record["kit"]["targets"]
    require(len(people) == len(set(people)) and people == [index for index, kind in enumerate(kinds) if kind == "person"] and
            all(person["at"] == record["targets"][person["target"]] for person in defended),
            f"{what}: every defended person stands at its target")
    helpers = [person for person in craft["people"] if person["target"] == -1]
    coop = beat["task"]["crank_coop"]
    require(len(helpers) == (len(coop["npcs"]) if coop else 0), f"{what}: exactly the authored crank helper is staged")
    require([helper["id"] for helper in helpers] == (coop["npcs"] if coop else []), f"{what}: helper identities and order")
    for helper in helpers:
        require(set(helper) == {"id", "target", "at", "cover"} and helper["id"] in coop["npcs"], f"{what}: crank helper identity")
        on_floor(index, helper["at"], f"{what}: crank helper work")
        on_floor(index, helper["cover"], f"{what}: crank helper cover")


def check_fieldcraft_sets(beat, record, index, zones, craft, area, on_floor):
    """Alarm lecterns, seizure nets, searchlights, the bell, cook-fires,
    ladders and the League's charge (campaign_fieldcraft.py)."""
    what, task, params = beat["id"], beat["task"], beat["params"]
    for alarm in craft["alarms"]:
        on_floor(index, alarm["at"], f"{what} alarm {alarm['id']}")
    nets = craft["nets"]
    if nets:
        require(set(nets) == NET_KEYS and nets["windup_ms"] > 0 and nets["haul_ms"] >= 0 and nets["cut_ms"] > 0 and
                nets["quarry"] and not set(nets["net_waves"]) & set(nets["scout_waves"]), f"{what}: seizure nets")
        kinds = {row["kind"] for row in nets["quarry"]}
        require(len(kinds) == 1, f"{what}: one kind of quarry a beat")
        kind = kinds.pop()
        ids = [row["id"] for row in nets["quarry"]]
        if kind == "pack_horse":
            require(beat["type"] == "horseback_ride" and ids == [row["id"] for row in record["mount"]["pack"]] and
                    nets["lost_event"] == "convoy_member_seized" and nets["haul_ms"] > 0 and
                    nets["saddle_weapon"] in record["mount"]["weapons"] and nets["saddle_side"] in (-1, 1),
                    f"{what}: a convoy's nets fall on its pack horses and a load seized loses it")
        elif kind == "cart":
            require(task["goal"] == "escort" and nets["halts"] and ids[0] in params["escort"]["npcs"] and
                    nets["quarry"][0]["hp"] > 0, f"{what}: an escort's nets fall on its cart")
        elif task["goal"] == "turns":
            require(what == "ch05.b06" and kind == "person" and ids == task["crank_coop"]["npcs"] == [person["id"] for person in craft["people"]] and
                    nets["haul_ms"] == 0 and nets["cut_ms"] == 1000 and nets["windup_ms"] == 800 and
                    [row["index"] for row in nets["quarry"]] == [0], f"{what}: bellows boy's net/free contract")
        else:
            require(kind == "person" and ids == [target["id"] for target in task["targets"]] and nets["haul_ms"] > 0 and
                    [row["index"] for row in nets["quarry"]] == list(range(len(ids))), f"{what}: a defence's nets")
        waves = params.get("waves") or []
        for wave in nets["net_waves"]:
            require(0 <= wave < len(waves) and any(enemy["type"] == "drone" for enemy in waves[wave]["enemies"]),
                    f"{what}: net wave {wave} sends no drone")
        # Each net wave nets with one to all of its drones (the rest scout).
        require(len(nets["nets_per_wave"]) == len(nets["net_waves"]) and
                all(1 <= count <= sum(enemy["count"] for enemy in waves[wave]["enemies"] if enemy["type"] == "drone")
                    for wave, count in zip(nets["net_waves"], nets["nets_per_wave"])), f"{what}: drones that net per wave")
        # One drone of a net wave may cross the road at a mark on it.
        if nets["cross_wave"] == -1:
            require(nets["cross_at_cm"] == 0, f"{what}: a crossing without its wave")
        else:
            require(nets["cross_wave"] in nets["net_waves"] and zones[index]["route"] and
                    0 < nets["cross_at_cm"] <= _length(zones[index]["route"]), f"{what}: a drone crosses the road on it")
    lights = craft["searchlights"]
    for light in lights:
        require(set(light) == LIGHT_KEYS and light["period_ms"] >= 2 and light["spot_cm"] > 0, f"{what}: searchlight {light['id']}")
        if light["road_to_cm"]:
            route = zones[index]["route"]
            require(0 <= light["road_from_cm"] < light["road_to_cm"] <= _length(route) and light["spooks"] and
                    re.fullmatch(r"wave_start:\d+", light["active_on"] or ""), f"{what}: a road searchlight's stretch")
        else:
            require(0 < light["sweep_deg"] <= 180 and 0 < light["suspicious_ms"] < light["alert_ms"] and light["reach_cm"] > 0 and
                    light["height_cm"] > 0 and light["lock_ms"] >= 0, f"{what}: searchlight {light['id']} rules")
            on_floor(index, light["at"], f"{what} searchlight {light['id']}", 0)
    bell = craft["bell"]
    if bell:
        require(bell["radius_cm"] > 0 and bell["uses"] > 0 and bell["hold_ms"] > 0 and bell["height_cm"] > 0,
                f"{what}: the bell")
        on_floor(index, bell["at"], f"{what} bell", 0)
    fires = craft["fires"]
    if fires:
        require(task["goal"] == "hold" and fires["relight_ms"] > 0 and fires["out_at"] == sorted(fires["out_at"]) and
                all(0 < mark < 1000 for mark in fires["out_at"]), f"{what}: cook-fires")
        for fire in fires["points"]:
            on_floor(index, fire["at"], f"{what} cook-fire {fire['id']}")
            require(math.hypot(fire["at"][0] - record["anchor"][0], fire["at"][1] - record["anchor"][1]) <= HOLD_REACH_CM,
                    f"{what}: cook-fire {fire['id']} stands outside the hold")
    for ladder in craft["ladders"]:
        area(ladder["roof"], f"roof of {ladder['id']}")
        on_floor(index, ladder["foot"], f"{what} ladder {ladder['id']}", 0)
        if ladder["straw"]:
            on_floor(index, ladder["straw"]["center"], f"{what} straw by {ladder['id']}", 0)
        guards = params.get("guards") or []
        # A drop is heard as far as the script says: a landing's thud
        # (SoraStealthRules::NoiseRadiusCm(ENoise::Landing)) made that loud,
        # at most the ten times the rules allow.
        require(ladder["height_cm"] > 0 and 0 < ladder["drop_noise_cm"] <= 10 * LANDING_NOISE_CM and
                all(0 <= guard < len(guards) for guard in ladder["guards"]), f"{what}: ladder {ladder['id']}")
    charge = craft["charge"]
    if charge:
        route = zones[index]["route"]
        require(beat["type"] == "horseback_ride" and charge["riders"] > 0 and 0 < charge["catch_up_cm_s"] < charge["pace_cm_s"] and
                charge["stake_break_ms"] > 0 and charge["stakes"], f"{what}: the charge")
        chainages = []
        for stake in charge["stakes"]:
            on_floor(index, stake["at"], f"{what} stake {stake['id']}", 0)
            chainages.append(min(range(len(route) - 1), key=lambda n: math.hypot(route[n][0] - stake["at"][0], route[n][1] - stake["at"][1])))
        require(chainages == sorted(chainages), f"{what}: the stakes stand along the road in order")


def check_crank_player(beat):
    def crank_fail(where, message):
        require(False, f"{where}: {message}")
    require("crank_player" in beat["task"] and beat["task"]["crank_player"] == player_work(beat, crank_fail),
            f"{beat['id']}: exact authored player crank contract")


def check_rhythm_steps(beat):
    # Compare normalized phrase sizes, passing thresholds and cue timing with
    # the authored source; a hand-edited catalog cannot erase the contract.
    from build_campaign_data import normalize_task, BuildError
    try:
        expected = normalize_task(beat)["steps"]
    except BuildError as error:
        raise CampaignError(str(error)) from error
    require(beat["task"]["steps"] == expected, f"{beat['id']}: exact authored manufacturing rhythm contract")


def check_dropoff_capacity(beat):
    task, where = beat["task"], beat["id"]
    require("dropoff_capacity" in task, f"{where}: missing drop-off capacity field")
    capacities = task["dropoff_capacity"]
    carry = beat["type"] == "production_task" and task["task"] == "carry"
    source = beat["params"].get("carry", {})
    if not carry or "x_dropoff_capacity" not in source:
        require(capacities is None, f"{where}: only an authored carry may name capacities")
        return
    names, count = task["dropoffs"], task["count"]
    require(isinstance(capacities, dict) and capacities == source["x_dropoff_capacity"],
            f"{where}: normalized capacities must preserve the authored map")
    require(1 <= len(names) <= 8 and all(isinstance(name, str) and name for name in names) and
            len(set(names)) == len(names) and set(capacities) == set(names),
            f"{where}: capacity keys must exactly match the named drop-offs")
    require(type(count) is int and 1 <= count <= 99 and
            all(type(value) is int and 1 <= value <= 99 for value in capacities.values()) and
            sum(capacities.values()) >= count, f"{where}: invalid or insufficient drop-off capacities")


def validate(catalog, campaign, chapters, legacy, roster):
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
    fights = {row["beat"]: row for row in roster["bosses"]["bosses"] + roster["bosses"]["duels"]}
    known_bosses = set(BOSSES) & {row["id"] for row in roster["bosses"]["bosses"]}
    require(known_bosses == set(BOSSES), f"bosses.json lacks {sorted(set(BOSSES) - known_bosses)}")
    archetypes = {row["id"] for row in roster["enemies"]["archetypes"]}
    # A defence's nets lock for as long as the drone's own seizure net winds up.
    drone_net = next(attack["windup_ms"] for row in roster["enemies"]["archetypes"] if row["id"] == "drone"
                     for attack in row["attacks"] if attack["id"] == "seizure_net")
    for chapter in chapters:
        for record in chapter["space"]["beats"]:
            nets = record["fieldcraft"]["nets"]
            require(not nets or nets["quarry"][0]["kind"] != "person" or nets["windup_ms"] == drone_net,
                    f"{record['beat']}: the planters' nets lock as long as the drone's seizure net winds up")
    require(archetypes == set(ENEMIES), f"enemies.json's roster {sorted(archetypes)} is not the bible's §7")

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
            check_dropoff_capacity(beat)
            check_crank_player(beat)
            check_rhythm_steps(beat)
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
            try:
                validate_registry(beat["registry"], beat["type"], params, beat["ext"])
            except ValueError as error:
                raise CampaignError(f"{beat['id']}: {error}") from error
            if beat["type"] == "horseback_ride":
                require(set(params["weapons"]) <= MOUNTED_WEAPONS, f"{beat['id']}: mounted weapons {params['weapons']}")
            if beat["type"] == "boss":
                require(params["boss"] in known_bosses, f"{beat['id']}: unknown boss {params['boss']!r}")
                require(fights.get(beat["id"], {}).get("id") == params["boss"],
                        f"{beat['id']}: bosses.json does not stage {params['boss']} at this beat")
            # A rival duel bosses.json stages here is fought against its opponent.
            if beat["id"] in fights and fights[beat["id"]]["id"].startswith("duel_"):
                require(beat["type"] == "duel" and beat["task"]["opponent"] == fights[beat["id"]]["opponent"],
                        f"{beat['id']}: bosses.json stages {fights[beat['id']]['id']} against another opponent")
            for guard in beat["task"]["guards"]:
                require(guard["type"] in archetypes, f"{beat['id']}: unknown guard type {guard['type']!r}")
                # 0 (or -1 for dark sight and hearing) keeps the archetype's sense.
                require(set(guard) == GUARD_KEYS and guard["sight_cm"] >= 0 and guard["dark_sight_cm"] >= -1 and
                        0 <= guard["view_deg"] <= 360 and guard["hearing_cm"] >= -1 and
                        0 <= guard["suspicion_permille"] <= 1000 and
                        (guard["dark_sight_cm"] < 0 or guard["sight_cm"] == 0 or guard["dark_sight_cm"] <= guard["sight_cm"]) and
                        0 <= guard["scan_deg"] <= 360 and (guard["scan_deg"] > 0) == (guard["scan_ms"] > 0) and guard["turn_ms"] >= 0 and
                        (guard["post"] or not (guard["scan_deg"] or guard["turn_ms"])), f"{beat['id']}: guard senses {guard}")
            # Somebody watches every stealth zone and all work under guard: the
            # zone's guards, or the task's patrolling wave members and x_guards.
            guarded = beat["type"] == "production_task" and beat["task"]["pause_when_seen"]
            if beat["type"] == "stealth_zone":
                posted = [guard["type"] for guard in params["guards"]]
            elif guarded:
                posted = [enemy["type"] for wave in params.get("waves", []) for enemy in wave["enemies"]
                          if "patrol" in enemy for _ in range(enemy["count"])]
                posted += [guard["type"] for guard in beat["ext"].get("guards") or [] for _ in range(guard.get("count", 1))]
            else:
                posted = []
            types = sorted(guard["type"] for guard in beat["task"]["guards"])
            require(types == sorted(posted) and (posted or beat["type"] != "stealth_zone" and not guarded),
                    f"{beat['id']}: guards {types} are not the {sorted(posted)} it posts")
            # The zone's authored rules travel with every zone and all work under guard.
            stealth = beat["task"]["stealth"]
            watched = beat["type"] == "stealth_zone" or guarded
            require((stealth is not None) == watched, f"{beat['id']}: stealth rules without a zone, or a zone without them")
            if stealth:
                require(set(stealth) == STEALTH_KEYS and 100 <= stealth["rate_permille"] <= 4000 and
                        50 <= stealth["suspicious_at_permille"] <= 950 and 1000 <= stealth["search_ms"] <= 120000 and
                        1000 <= stealth["wary_permille"] <= 4000, f"{beat['id']}: stealth rules {stealth}")
                later = [row["id"] for row in chapter["beats"] if row["type"] == "stealth_zone"]
                require(stealth["carryover_to"] is None or (stealth["carryover_to"] in later and
                        later.index(stealth["carryover_to"]) > later.index(beat["id"])),
                        f"{beat['id']}: detection carries over to {stealth['carryover_to']}, not a later zone")
            waves = params.get("waves", [])
            lethal = 0
            for wave in waves:
                for enemy in wave["enemies"]:
                    # Work under guard posts its patrolling members instead of sending them.
                    if guarded and "patrol" in enemy:
                        continue
                    kind = enemy["type"]
                    if kind in TRAINING_TARGETS:
                        require(params.get("target_kind") == "mato", f"{beat['id']}: training target outside the range")
                    else:
                        require(kind in archetypes, f"{beat['id']}: enemies.json has no {kind!r}")
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
            # Keys only as {Action} tokens the HUD resolves to the player's own keys.
            tokens = [sorted(KEY_TOKEN.findall(prompt[language])) for language in ("ja", "en")]
            require(tokens[0] == tokens[1] and set(tokens[0]) <= set(roster["actions"]),
                    f"{prompt['id']}: key tokens {tokens} must be input actions, the same in both languages")
            require(not any(BRACKETED_CONTROL.search(prompt[language]) or "{" in KEY_TOKEN.sub("", prompt[language]) or
                            "}" in KEY_TOKEN.sub("", prompt[language]) for language in ("ja", "en")),
                    f"{prompt['id']}: names a control outside an {{Action}} token")

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


def self_test(catalog, campaign, chapters, legacy, roster):
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

    def boss_at_the_wrong_beat(data):
        next(row for row in data[4]["bosses"]["bosses"] if row["id"] == "boss_dunark")["beat"] = "ch02.b14"

    def duel_against_another(data):
        next(row for row in data[4]["bosses"]["duels"] if row["beat"] == "ch06.b09")["opponent"] = "npc_sekireisai"

    def unknown_archetype(data):
        wave = beat(data, "ch02.b02")["params"]["waves"][0]
        wave["enemies"][0]["type"] = "enforcer_musket"

    def guard_without_archetype(data):
        # Posted as authored, so only the archetype check can refuse it.
        target = beat(data, "ch03.b02")
        target["params"]["guards"][0]["type"] = target["task"]["guards"][0]["type"] = "drone_sentinel"

    def unguarded_work(data):
        beat(data, "ch06.b08")["task"]["guards"] = []

    def guard_outside_stealth(data):
        beat(data, "ch02.b02")["task"]["guards"] = [dict(beat(data, "ch03.b03")["task"]["guards"][3])]

    def guard_sees_in_the_dark(data):
        guard = beat(data, "ch06.b02")["task"]["guards"][0]
        guard["dark_sight_cm"] = guard["sight_cm"] + 100

    def zone_without_rules(data):
        beat(data, "ch06.b06")["task"]["stealth"] = None

    def carryover_backwards(data):
        beat(data, "ch03.b03")["task"]["stealth"]["carryover_to"] = "ch03.b02"

    def prompt(data, prompt_id):
        chapter = data[2][int(prompt_id[2:4]) - 1]
        return next(row for row in chapter["ui_prompts"] if row["id"] == prompt_id)

    def unbound_key_token(data):
        row = prompt(data, "ch02.b03.tut.002")
        row["ja"], row["en"] = "槍を得た。{Polearm}で持ち替え。", "Yari acquired. Press {Polearm} to switch."

    def bracketed_control(data):
        row = prompt(data, "ch01.b06.prompt.04")
        row["ja"], row["en"] = "前進で常歩、［速歩］で速歩", "Move forward to walk. Press [Trot] to trot."

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

    def cinematic_with_closing_anchor(data):
        space(data, 7, "ch08.b18")["closing"] = list(space(data, 7, "ch08.b17")["closing"])

    def dialogue_without_closing_anchor(data):
        space(data, 7, "ch08.b17")["closing"] = None

    def cinematic_with_cache(data):
        record = space(data, 7, "ch08.b18")
        record["cache"] = list(record["anchor"])

    def explore_without_cache(data):
        space(data, 0, "ch01.b08")["cache"] = [0, 0]

    def cinematic_without_camera(data):
        space(data, 7, "ch08.b18")["camera"] = None

    def dialogue_with_camera(data):
        space(data, 7, "ch08.b17")["camera"] = list(space(data, 7, "ch08.b18")["camera"])

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

    def lamp_in_wall(data):
        record = space(data, 2, "ch03.b02")
        record["fieldcraft"]["lamps"][0]["at"] = [data[2][2]["space"]["zones"][record["zone"]]["rect"][0] - 50, 0]

    def climb_around_the_face(data):
        space(data, 5, "ch06.b03")["fieldcraft"]["climb"]["width_cm"] -= 400

    def ally_joins_no_wave(data):
        space(data, 4, "ch05.b10")["fieldcraft"]["allies"][2]["joins"] = "wave_start:9"

    def volley_rank_short(data):
        allies = space(data, 7, "ch08.b03")["fieldcraft"]["allies"]
        allies.remove(next(ally for ally in allies if ally["rank"] == 1))

    def net_wave_without_drones(data):
        space(data, 3, "ch04.b10")["fieldcraft"]["nets"]["net_waves"] = [0]

    def netters_beyond_the_wave(data):
        space(data, 1, "ch02.b08")["fieldcraft"]["nets"]["nets_per_wave"][0] = 4

    def crossing_off_the_road(data):
        nets = space(data, 1, "ch02.b08")["fieldcraft"]["nets"]
        nets["cross_at_cm"] = 10_000_000

    def drop_heard_past_the_rules(data):
        space(data, 2, "ch03.b03")["fieldcraft"]["ladders"][0]["drop_noise_cm"] = 10 * LANDING_NOISE_CM + 1

    def fire_outside_the_hold(data):
        fire = space(data, 2, "ch03.b14")["fieldcraft"]["fires"]["points"][0]
        fire["at"] = [fire["at"][0] - 600, fire["at"][1]]

    def stakes_out_of_order(data):
        stakes = space(data, 7, "ch08.b02")["fieldcraft"]["charge"]["stakes"]
        stakes[0]["at"], stakes[2]["at"] = stakes[2]["at"], stakes[0]["at"]

    def party_without_escort(data):
        space(data, 1, "ch02.b02")["fieldcraft"]["party"] = [dict(space(data, 2, "ch03.b07")["fieldcraft"]["party"][0])]

    validate(*copy.deepcopy((catalog, campaign, chapters, legacy, roster)))
    mutations = (anchor_in_wall, short_route, missing_volume, zones_collide, lost_collectible, unlabelled_step,
                 cinematic_with_closing_anchor, dialogue_without_closing_anchor, cinematic_with_cache,
                 explore_without_cache, cinematic_without_camera, dialogue_with_camera,
                 yumi_to_the_right, short_escort, spawn_in_building, swap_unlock, fast_line, long_gap, cache_without_save,
                 boss_cue_time, unraised_rate_band, bout_numbered_per_beat,
                 gun_on_horse, site_table_mismatch, site_chain_broken, orphan_line, dangling_line,
                 unknown_speaker, legacy_edit, muto_everywhere, conscript_quota, pacing, registry_on_combat,
                 lost_pickup, unknown_boss, optional_site, blocking_speech, story_flag_twice, unmet_condition,
                 boss_at_the_wrong_beat, duel_against_another, unknown_archetype, guard_without_archetype,
                 unguarded_work, guard_outside_stealth, guard_sees_in_the_dark, zone_without_rules, carryover_backwards,
                 unbound_key_token, bracketed_control,
                 lamp_in_wall, climb_around_the_face, ally_joins_no_wave, party_without_escort, volley_rank_short,
                 net_wave_without_drones, netters_beyond_the_wave, crossing_off_the_road, drop_heard_past_the_rules,
                 fire_outside_the_hold, stakes_out_of_order)
    for mutate in mutations:
        data = copy.deepcopy((catalog, campaign, chapters, legacy, roster))
        mutate(data)
        try:
            validate(*data)
        except CampaignError:
            continue
        raise CampaignError(f"self-test: the validator accepted the {mutate.__name__} mutation")
    return len(mutations)


def check_project():
    catalog, campaign, chapters, legacy, roster = load()
    summary = validate(catalog, campaign, chapters, legacy, roster)
    rejected = self_test(catalog, campaign, chapters, legacy, roster)
    return (f"Campaign schema 4 passed the bible's eight rules: {summary['beats']} beats, {summary['lines']} "
            f"bilingual lines on {summary['triggers']} triggers, {summary['checkpoints']} checkpoints, "
            f"{summary['target_s']} target seconds, 21 weapon unlocks in §11 order, 25 schema-3 cues verbatim; "
            f"self-test rejected {rejected} bad variants")


if __name__ == "__main__":
    print(check_project())
