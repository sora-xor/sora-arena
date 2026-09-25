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
8. at most 360 target seconds between checkpoints.

It also checks line references both ways (every scheduled line exists, every
line is scheduled), and that the 25 cues of catalog schema 3, frozen in
scripts/unreal/fixtures/campaign_legacy_lines.json, survive verbatim.

The self-test runs first and must reject known-bad data, so a broken check
cannot pass silently.
"""
from __future__ import annotations

import copy
import json
import re
import textwrap
from pathlib import Path

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
SITE_KINDS = {"training", "debt_seal", "irrigation", "workshop", "foundry", "ledger", "power", "supplies"}
MUTO_DEFEATS = ("disarm", "capture")
EN_MAX_CPS = 17
EN_LINE_CHARS, JA_LINE_CHARS, SUBTITLE_LINES = 42, 16, 2
MIN_LINE_S = 1.0
BLOCKING_MAX_S = 20.0
CHECKPOINT_GAP_S = 360
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


def validate(catalog, campaign, chapters, legacy, bosses=None):
    speakers = {speaker["id"] for speaker in catalog["dialogue_speakers"]}
    require(catalog["schema_version"] == 4 and "chapters" not in catalog,
            "catalog.json must be schema 4 without the schema-3 chapter list")
    require(campaign["schema_version"] == 4, "campaign.json must be schema 4")
    require(len(campaign["chapters"]) == 8 == len(chapters), "the campaign has eight chapters")
    require(tuple(campaign["mechanics"]) == MECHANICS, "campaign mechanics must list the §12.1 flags in order")
    categories = {row["id"]: row for row in campaign["collectible_categories"]}
    known_bosses = set(BOSSES) if bosses is None else set(BOSSES) & boss_ids(bosses)
    require(known_bosses == set(BOSSES), f"bosses.json lacks {sorted(set(BOSSES) - known_bosses)}")

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

        # Rule 8: checkpoint spacing, including the chapter's end.
        positions = sorted(row["at_cs"] for row in chapter["checkpoints"])
        require(positions and positions[0] == 0, f"{where}: the first beat must checkpoint")
        positions.append(beat_total * 100)
        gap = max(b - a for a, b in zip(positions, positions[1:]))
        require(gap <= CHECKPOINT_GAP_S * 100, f"{where}: {gap / 100:g} target seconds between checkpoints")

        # Rule 6 and line references.
        lines = {}
        for line in chapter["lines"]:
            require(line["id"] not in lines and line["id"] not in line_ids, f"{line['id']}: line id used twice")
            require(line["beat"] is None or line["beat"] in by_id, f"{line['id']}: unknown beat")
            check_line(line, speakers, line["id"])
            lines[line["id"]] = line
        line_ids |= set(lines)
        scheduled = set()
        for row in chapter["triggers"]:
            context = f"{where} trigger {row['beat']} {row['on']}"
            require(row["beat"] is None or row["beat"] in by_id, f"{context}: unknown beat")
            require(row["lines"], f"{context}: no lines")
            missing = [line for line in row["lines"] if line not in lines]
            require(not missing, f"{context}: references missing lines {missing}")
            scheduled.update(row["lines"])
            if row["mode"] == "blocking":
                total = sum(lines[line]["duration_s"] for line in row["lines"])
                require(total <= BLOCKING_MAX_S, f"{context}: blocking dialogue runs {total:g} s")
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
        rewards = {reward for beat in beats if beat["type"] == "explore_optional"
                   for reward in beat["params"].get("rewards", []) if re.fullmatch(r"ch\d\d\.c\d\d", str(reward))}
        require(rewards <= {item["id"] for item in collectibles}, f"{where}: explore rewards name unknown collectibles")
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
        for row in data[2][0]["checkpoints"]:
            if row["beat"] in ("ch01.b12", "ch01.b13"):
                row["at_cs"] = 0

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

    def blocking_speech(data):
        row = next(row for row in data[2][1]["triggers"] if row["mode"] == "blocking")
        row["lines"] = [line["id"] for line in data[2][1]["lines"][:12]]

    validate(*copy.deepcopy((catalog, campaign, chapters, legacy)))
    mutations = (swap_unlock, fast_line, long_gap, gun_on_horse, site_table_mismatch, site_chain_broken, orphan_line, dangling_line,
                 unknown_speaker, legacy_edit, muto_everywhere, conscript_quota, pacing, registry_on_combat,
                 lost_pickup, unknown_boss, optional_site, blocking_speech)
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
