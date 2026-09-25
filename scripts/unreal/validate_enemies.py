"""Validate Content/Data/enemies.json, the campaign's opponent archetypes.

Checks, mirroring the strict loader in Source/SoraArena/Private/Combat/SoraEnemyCatalog.cpp:
  1. the schema and every documented field, its type and its range;
  2. the roster: exactly the story bible's §7 table, in its order, with the
     bible's Japanese name, reading, English name and first chapter;
  3. bilingual text: Japanese names contain Japanese, English names do not;
  4. telegraphs: every attack warns for at least 300 ms, and the bible's
     stated warnings (the retainer's 420 ms, the marksman's 900 ms) hold;
  5. 活人剣: exactly the debt-bound are nonlethal, and they carry a subdue window;
  6. guards: a parryable blow staggers its attacker, a chip never exceeds its blow;
  7. shells: a lob's minimum range clears its own blast, and its arming
     distance is the kernel grenade launcher's (crates/arena-core/src/catalog.rs);
  8. chapter data: every enemy type and variant a chapter beat names exists.

It then validates Content/Data/bosses.json, mirroring the strict loader in
Source/SoraArena/Private/Combat/SoraBossCatalog.cpp:
  9. the schema, every field, its type, range and unknown-field rejection;
 10. the story bible §8 roster and order, the cast table's names, its phase
     thresholds and its stated windups, and the two Toranosuke duels;
 11. the chapter scripts: each fight's pattern tables and thresholds, every
     voice line (spoken by the boss itself, and every bible §8 voice
     telegraph among them), every pattern a chapter barks on, and the
     beat's telegraph floor;
 12. telegraphs: every blow's windup, after each phase's overrides, meets
     its fight's floor; mutō-dori only where the fight may end in it;
 13. health: every phase start and floor lands on whole health on every difficulty;
 14. adds name enemies.json archetypes and variants; every attack is reachable.
A mutation self-test then confirms each check rejects a broken copy.
"""
import copy
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
JAPANESE = re.compile(r"[぀-ヿ㐀-鿿]")
LOWER_ID = re.compile(r"^[a-z][a-z0-9_]*$")
BEHAVIORS = {"blade", "rifle", "shield", "grenadier", "marksman", "drone", "conscript", "auditor", "automaton", "walker"}
BODIES = {"alien", "local", "drone", "machine", "walker"}
FACTIONS = {"credit_house", "debt_bound"}
KINDS = {"melee", "burst", "lock_shot", "lob", "beam", "net"}
TELEGRAPHS = {"amber", "cyan"}
MELEE_BEHAVIORS = {"blade", "shield", "conscript", "automaton"}
TRAINING_TARGETS = {"mato_kinteki", "mato_tsuri"}
MINIMUM_WINDUP_MS = 300
TOP_FIELDS = {"schema_version", "source", "archetypes"}
ARCHETYPE_FIELDS = {"id", "name_ja", "reading", "name_en", "weapon_ja", "weapon_en", "faction", "body", "behavior",
                    "first_chapter", "health", "speed_cm_s", "turn_deg_s", "scale_permille", "lethal", "perception",
                    "defense", "tactics", "attacks", "variants"}
PERCEPTION_FIELDS = {"sight_cm", "dark_sight_cm", "view_deg", "hearing_cm", "suspicion_permille", "alarmist"}
DEFENSE_FIELDS = {"front_block_deg", "rim_opening_ms", "rear_weak_permille", "poise_ms", "rear_takedown"}
# A rear takedown needs a nape to strike: cats, alien or local, never a machine.
TAKEDOWN_BODIES = {"alien", "local"}
TACTICS_FIELDS = {"keep_distance_cm", "relocate_after_shots", "hover_cm", "alarm_radius_cm", "static"}
ATTACK_FIELDS = {"id", "cue", "name_ja", "name_en", "kind", "telegraph", "damage", "windup_ms", "recovery_ms",
                 "cooldown_ms", "range_cm"}
KIND_FIELDS = {
    "melee": {"arc_deg", "knockback_cm", "hero_stagger_ms", "guard"},
    "burst": {"rounds", "interval_ms"},
    "lock_shot": set(),
    "lob": {"radius_cm", "flight_ms", "arming_cm"},
    "beam": {"width_cm"},
    "net": {"radius_cm", "root_ms"},
}
GUARD_FIELDS = {"parry", "chip", "stamina", "parry_stagger_ms", "breaks"}
SUBDUE_FIELDS = {"window_ms", "seal_cut_hold_ms", "rise_health_permille"}
BARRIER_FIELDS = {"health", "regen_delay_ms", "regen_per_s", "break_stagger_ms", "melee_permille", "weapon_permille",
                  "bypass_weapons"}


def whole(value, low, high):
    return isinstance(value, int) and not isinstance(value, bool) and low <= value <= high


def bible_roster():
    """(id, ja, reading, en, first chapter) rows of the story bible's §7 enemies table."""
    text = (ROOT / "docs/campaign/story-bible.md").read_text()
    section = text[text.index("## 7. Enemies"):text.index("## 8. Bosses")]
    rows = []
    for line in section.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == 7 and cells[0].startswith("`") and cells[0].endswith("`"):
            chapter = re.match(r"ch0(\d)\b", cells[6])
            assert chapter, f"bible §7 first-seen cell {cells[6]!r}"
            rows.append({"id": cells[0].strip("`"), "ja": cells[1], "reading": cells[2],
                         "en": cells[3].replace('"', ""), "first": int(chapter.group(1)), "behavior": cells[5]})
    assert len(rows) >= 10, f"bible §7 table has {len(rows)} rows"
    return rows


def kernel_grenade_arming_cm():
    source = (ROOT / "crates/arena-core/src/catalog.rs").read_text()
    table = source[source.index("pub const WEAPONS"):]
    for call in re.finditer(r"\bw\(\s*(.*?)\)\s*,", table, re.S):
        fields = [field.strip() for field in call.group(1).split(",") if field.strip()]
        if len(fields) == 13 and fields[0] == "7":
            return int(fields[9]) // 10
    raise AssertionError("kernel weapon 7 not found")


def beat_types():
    """The beat types of the story bible's §12.2 table; chapter data also types beats and tasks with them."""
    text = (ROOT / "docs/campaign/story-bible.md").read_text()
    section = text[text.index("### 12.2 Type-specific parameters"):text.index("### 12.3")]
    types = set(re.findall(r"^\| `([a-z_]+)`", section, re.M))
    assert "combat_wave" in types and "boss" in types, f"bible §12.2 beat types {sorted(types)}"
    return types


def chapter_references():
    """(file, enemy type, variant or None) for every opponent chapter data names.

    Chapter data types its beats, tasks and opponents with one field; any
    identifier that is not a beat type names an opponent, wherever the chapter
    lists it (waves, stealth guards, escort members, boss adds).
    """
    beats = beat_types()
    references = []
    for path in sorted((ROOT / "Content/Data/campaign").glob("chapter_*.json")):
        def walk(node):
            if isinstance(node, dict):
                kind = node.get("type")
                if isinstance(kind, str) and LOWER_ID.match(kind) and kind not in beats:
                    references.append((path.name, kind, node.get("variant") or node.get("x_variant")))
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)
        walk(json.loads(path.read_text()))
    return references


def validate(data, roster, grenade_arming_cm, references):
    errors = []

    def require(condition, message):
        if not condition:
            errors.append(message)
        return condition

    if not require(isinstance(data, dict) and set(data) == TOP_FIELDS, f"top-level fields must be {sorted(TOP_FIELDS)}"):
        return errors
    require(data["schema_version"] == 1, "schema_version must be 1")
    require(isinstance(data["source"], str) and data["source"].strip(), "source must name the design documents")
    archetypes = data["archetypes"]
    if not require(isinstance(archetypes, list) and archetypes, "archetypes must be a non-empty list"):
        return errors
    ids = [a.get("id") for a in archetypes if isinstance(a, dict)]
    require(ids == [row["id"] for row in roster], f"archetypes must be the bible §7 roster in order, found {ids}")
    bible = {row["id"]: row for row in roster}
    variants = {}
    for a in archetypes:
        where = a.get("id", "?") if isinstance(a, dict) else "?"
        if not require(isinstance(a, dict) and set(a) - {"subdue"} == ARCHETYPE_FIELDS,
                       f"{where}: fields must be {sorted(ARCHETYPE_FIELDS)} (and subdue when nonlethal)"):
            continue
        require(isinstance(a["id"], str) and LOWER_ID.match(a["id"]), f"{where}: id must be lower_snake_case")
        for field in ("name_ja", "reading", "weapon_ja"):
            require(isinstance(a[field], str) and JAPANESE.search(a[field]), f"{where}: {field} must be Japanese")
        for field in ("name_en", "weapon_en"):
            require(isinstance(a[field], str) and a[field].strip() and not JAPANESE.search(a[field]),
                    f"{where}: {field} must be English")
        row = bible.get(a["id"])
        if row:
            require(a["name_ja"] == row["ja"], f"{where}: name_ja {a['name_ja']!r} is not the bible's {row['ja']!r}")
            require(a["reading"] == row["reading"], f"{where}: reading is not the bible's {row['reading']!r}")
            require(a["name_en"] == row["en"], f"{where}: name_en {a['name_en']!r} is not the bible's {row['en']!r}")
            require(a["first_chapter"] == row["first"], f"{where}: first_chapter is not the bible's ch0{row['first']}")
        require(a["faction"] in FACTIONS, f"{where}: faction must be one of {sorted(FACTIONS)}")
        require(a["body"] in BODIES, f"{where}: body must be one of {sorted(BODIES)}")
        require(a["behavior"] in BEHAVIORS, f"{where}: behavior must be one of {sorted(BEHAVIORS)}")
        require(whole(a["first_chapter"], 1, 8), f"{where}: first_chapter must be 1-8")
        require(whole(a["health"], 1, 100000), f"{where}: health must be a positive whole number")
        require(whole(a["speed_cm_s"], 0, 2000), f"{where}: speed_cm_s out of range")
        require(whole(a["turn_deg_s"], 10, 720), f"{where}: turn_deg_s out of range")
        require(whole(a["scale_permille"], 300, 4000), f"{where}: scale_permille out of range")
        require(isinstance(a["lethal"], bool), f"{where}: lethal must be true or false")
        # 活人剣: the debt-bound, and only they, are subdued instead of killed.
        require((a["faction"] == "debt_bound") == (a["lethal"] is False), f"{where}: exactly the debt-bound are nonlethal")
        if a["lethal"] is False:
            subdue = a.get("subdue")
            if require(isinstance(subdue, dict) and set(subdue) == SUBDUE_FIELDS, f"{where}: a nonlethal archetype needs subdue"):
                require(whole(subdue["window_ms"], 1000, 60000), f"{where}: subdue window out of range")
                require(whole(subdue["seal_cut_hold_ms"], 100, subdue["window_ms"]) if whole(subdue["window_ms"], 1000, 60000)
                        else False, f"{where}: a collar must be cuttable inside the window")
                require(whole(subdue["rise_health_permille"], 1, 1000), f"{where}: rise_health_permille out of range")
        else:
            require("subdue" not in a, f"{where}: only a nonlethal archetype is subdued")
        p = a["perception"]
        if require(isinstance(p, dict) and set(p) == PERCEPTION_FIELDS, f"{where}: perception fields"):
            require(whole(p["sight_cm"], 100, 10000), f"{where}: sight_cm out of range")
            require(whole(p["dark_sight_cm"], 0, p["sight_cm"] if whole(p["sight_cm"], 100, 10000) else 0),
                    f"{where}: dark_sight_cm must not exceed sight_cm")
            require(whole(p["view_deg"], 10, 360), f"{where}: view_deg out of range")
            require(whole(p["hearing_cm"], 0, 10000), f"{where}: hearing_cm out of range")
            require(whole(p["suspicion_permille"], 100, 2000), f"{where}: suspicion_permille out of range")
            require(isinstance(p["alarmist"], bool), f"{where}: alarmist must be true or false")
            require(p["alarmist"] == (a["behavior"] == "auditor"), f"{where}: only the auditor raises alarms")
        d = a["defense"]
        if require(isinstance(d, dict) and set(d) == DEFENSE_FIELDS, f"{where}: defense fields"):
            require(whole(d["front_block_deg"], 0, 360), f"{where}: front_block_deg out of range")
            require(whole(d["rim_opening_ms"], 0, 5000), f"{where}: rim_opening_ms out of range")
            require((d["front_block_deg"] > 0) == (d["rim_opening_ms"] > 0), f"{where}: a shield turns on its rim, and only a shield")
            require((d["front_block_deg"] > 0) == (a["behavior"] == "shield"), f"{where}: only a shield enforcer carries a tower shield")
            require(whole(d["rear_weak_permille"], 1000, 5000), f"{where}: rear_weak_permille out of range")
            require(whole(d["poise_ms"], 0, 10000), f"{where}: poise_ms out of range")
            require(isinstance(d["rear_takedown"], bool), f"{where}: rear_takedown must be true or false")
            require(d["rear_takedown"] == (a["body"] in TAKEDOWN_BODIES),
                    f"{where}: cats, and only cats, can be taken down from behind")
        t = a["tactics"]
        if require(isinstance(t, dict) and set(t) == TACTICS_FIELDS, f"{where}: tactics fields"):
            for field in ("keep_distance_cm", "relocate_after_shots", "hover_cm", "alarm_radius_cm"):
                require(whole(t[field], 0, 10000), f"{where}: tactics.{field} out of range")
            require(isinstance(t["static"], bool), f"{where}: tactics.static must be true or false")
            require((t["hover_cm"] > 0) == (a["behavior"] == "drone"), f"{where}: drones, and only drones, hover")
            require(t["static"] == (a["speed_cm_s"] == 0), f"{where}: a static archetype has no speed, and only it")
            require((t["alarm_radius_cm"] > 0) == (a["behavior"] == "auditor"), f"{where}: only the auditor's alarm carries")
        attacks = a["attacks"]
        if not require(isinstance(attacks, list), f"{where}: attacks must be a list"):
            continue
        require(bool(attacks) == (a["behavior"] != "auditor"), f"{where}: every archetype but the auditor attacks")
        seen = set()
        for x in attacks:
            at = f"{where}.{x.get('id', '?') if isinstance(x, dict) else '?'}"
            kind = x.get("kind") if isinstance(x, dict) else None
            if not require(kind in KINDS and set(x) == ATTACK_FIELDS | KIND_FIELDS[kind],
                           f"{at}: fields must be {sorted(ATTACK_FIELDS | KIND_FIELDS.get(kind, set()))}"):
                continue
            require(isinstance(x["id"], str) and LOWER_ID.match(x["id"]) and x["id"] not in seen, f"{at}: id must be a unique lower_snake_case name")
            seen.add(x["id"])
            require(isinstance(x["cue"], str) and LOWER_ID.match(x["cue"]), f"{at}: cue must be lower_snake_case")
            require(isinstance(x["name_ja"], str) and JAPANESE.search(x["name_ja"]), f"{at}: name_ja must be Japanese")
            require(isinstance(x["name_en"], str) and x["name_en"].strip() and not JAPANESE.search(x["name_en"]), f"{at}: name_en must be English")
            require(x["telegraph"] in TELEGRAPHS, f"{at}: telegraph must be amber or cyan")
            # Every telegraph precedes its damage by at least its windup (bible §8).
            require(whole(x["windup_ms"], MINIMUM_WINDUP_MS, 5000), f"{at}: windup_ms must warn for at least {MINIMUM_WINDUP_MS} ms")
            require(whole(x["recovery_ms"], 0, 20000) and whole(x["cooldown_ms"], 0, 60000), f"{at}: recovery or cooldown out of range")
            require(whole(x["damage"], 0 if kind == "net" else 1, 1000), f"{at}: damage out of range")
            r = x["range_cm"]
            require(isinstance(r, list) and len(r) == 2 and whole(r[0], 0, 10000) and whole(r[1], 1, 10000) and r[0] < r[1],
                    f"{at}: range_cm must be [minimum, maximum]")
            if kind in ("beam", "lock_shot"):
                require(x["telegraph"] == "cyan", f"{at}: a locked aim or beam telegraphs in cyan")
            if kind == "melee":
                g = x["guard"]
                require(whole(x["arc_deg"], 10, 360) and whole(x["knockback_cm"], 0, 1000) and whole(x["hero_stagger_ms"], 0, 5000),
                        f"{at}: melee arc, knockback or stagger out of range")
                if require(isinstance(g, dict) and set(g) == GUARD_FIELDS, f"{at}: guard fields"):
                    require(isinstance(g["parry"], bool) and isinstance(g["breaks"], bool), f"{at}: guard flags must be true or false")
                    require(whole(g["chip"], 0, max(x["damage"] - 1, 0)), f"{at}: a guard's chip must be less than the blow")
                    require(whole(g["stamina"], 0, 100), f"{at}: guard stamina out of range")
                    require(whole(g["parry_stagger_ms"], 0, 5000) and (g["parry"] is True) == (g["parry_stagger_ms"] > 0),
                            f"{at}: a parryable blow staggers its attacker; an unparryable one cannot")
                require(a["behavior"] in MELEE_BEHAVIORS, f"{at}: only close-quarters archetypes strike in melee")
            elif kind == "burst":
                require(whole(x["rounds"], 1, 10) and whole(x["interval_ms"], 50, 2000), f"{at}: burst rounds or interval out of range")
            elif kind == "lob":
                require(whole(x["radius_cm"], 50, 2000) and whole(x["flight_ms"], 300, 5000), f"{at}: lob radius or flight out of range")
                require(isinstance(r, list) and len(r) == 2 and whole(r[0], 0, 10000) and r[0] > x["radius_cm"],
                        f"{at}: a lob's minimum range must clear its own blast")
                require(x["arming_cm"] == grenade_arming_cm, f"{at}: arming_cm must be the kernel grenade's {grenade_arming_cm}")
            elif kind == "beam":
                require(whole(x["width_cm"], 10, 2000), f"{at}: beam width out of range")
            elif kind == "net":
                require(whole(x["radius_cm"], 50, 1000) and whole(x["root_ms"], 100, 10000), f"{at}: net ring or hold out of range")
        # The bible's stated warnings (§7): the retainer's cut and the marksman's glint.
        stated = re.search(r"(\d+) ms", bible[a["id"]]["behavior"]) if a["id"] in bible else None
        if stated and attacks:
            require(any(isinstance(x, dict) and x.get("windup_ms") == int(stated.group(1)) for x in attacks),
                    f"{where}: the bible's {stated.group(1)} ms warning is not an attack's windup")
        names = set()
        vs = a["variants"]
        if not require(isinstance(vs, list), f"{where}: variants must be a list"):
            continue
        for v in vs:
            vat = f"{where}~{v.get('id', '?') if isinstance(v, dict) else '?'}"
            if not require(isinstance(v, dict) and {"id", "name_ja", "name_en", "health"} <= set(v) <=
                           {"id", "name_ja", "name_en", "health", "perception", "barrier"}, f"{vat}: variant fields"):
                continue
            require(isinstance(v["id"], str) and LOWER_ID.match(v["id"]) and v["id"] not in names, f"{vat}: id must be unique lower_snake_case")
            names.add(v["id"])
            require(isinstance(v["name_ja"], str) and JAPANESE.search(v["name_ja"]), f"{vat}: name_ja must be Japanese")
            require(isinstance(v["name_en"], str) and v["name_en"].strip() and not JAPANESE.search(v["name_en"]), f"{vat}: name_en must be English")
            require(whole(v["health"], 0, 100000), f"{vat}: health out of range")
            require(v["health"] > 0 or "perception" in v or "barrier" in v, f"{vat}: a variant must change something")
            if "perception" in v:
                vp = v["perception"]
                require(isinstance(vp, dict) and set(vp) == {"sight_cm", "dark_sight_cm", "view_deg"} and
                        whole(vp["sight_cm"], 100, 10000) and whole(vp["dark_sight_cm"], 0, vp["sight_cm"]) and
                        whole(vp["view_deg"], 10, 360), f"{vat}: variant perception")
            if "barrier" in v:
                b = v["barrier"]
                if require(isinstance(b, dict) and set(b) == BARRIER_FIELDS, f"{vat}: barrier fields"):
                    for field in ("health", "regen_delay_ms", "regen_per_s", "break_stagger_ms", "melee_permille"):
                        require(whole(b[field], 1 if field == "health" else 0, 60000), f"{vat}: barrier {field} out of range")
                    require(isinstance(b["weapon_permille"], dict) and all(
                        re.fullmatch(r"\d{1,2}", key) and int(key) <= 20 and whole(value, 0, 10000)
                        for key, value in b["weapon_permille"].items()), f"{vat}: weapon_permille must map catalog weapon ids")
                    require(isinstance(b["bypass_weapons"], list) and all(whole(w, 0, 20) for w in b["bypass_weapons"]),
                            f"{vat}: bypass_weapons must list catalog weapon ids")
        variants[a["id"]] = names
    # Chapter data may name only these archetypes and their variants.
    for file, kind, variant in references:
        if kind in TRAINING_TARGETS:
            continue
        if require(kind in variants, f"{file}: unknown enemy type {kind!r}") and variant is not None:
            require(variant in variants[kind], f"{file}: {kind} has no variant {variant!r}")
    return errors


def mutations(data):
    """Broken copies of the data, each of which one check must reject."""
    def edit(label, change):
        broken = copy.deepcopy(data)
        change(broken)
        return label, broken
    by_id = lambda d, i: next(a for a in d["archetypes"] if a["id"] == i)
    yield edit("roster order", lambda d: d["archetypes"].reverse())
    yield edit("missing archetype", lambda d: d["archetypes"].pop())
    yield edit("bible name", lambda d: by_id(d, "grenadier").__setitem__("name_ja", "爆弾兵"))
    yield edit("English in Japanese", lambda d: by_id(d, "drone").__setitem__("name_ja", "Drone"))
    yield edit("lethal conscript", lambda d: by_id(d, "bound_conscript").__setitem__("lethal", True))
    yield edit("nonlethal enforcer", lambda d: by_id(d, "enforcer_rifle").__setitem__("lethal", False))
    yield edit("short telegraph", lambda d: by_id(d, "blade_retainer")["attacks"][0].__setitem__("windup_ms", 120))
    yield edit("bible warning", lambda d: by_id(d, "marksman")["attacks"][0].__setitem__("windup_ms", 800))
    yield edit("parry without stagger", lambda d: by_id(d, "blade_retainer")["attacks"][0]["guard"].__setitem__("parry_stagger_ms", 0))
    yield edit("chip beyond blow", lambda d: by_id(d, "blade_retainer")["attacks"][0]["guard"].__setitem__("chip", 99))
    yield edit("self-blast lob", lambda d: by_id(d, "grenadier")["attacks"][0].__setitem__("range_cm", [100, 2500]))
    yield edit("arming", lambda d: by_id(d, "grenadier")["attacks"][0].__setitem__("arming_cm", 50))
    yield edit("amber beam", lambda d: by_id(d, "seizure_walker")["attacks"][0].__setitem__("telegraph", "amber"))
    yield edit("unknown field", lambda d: by_id(d, "drone").__setitem__("colour", "cyan"))
    yield edit("shield without rim", lambda d: by_id(d, "shield_enforcer")["defense"].__setitem__("rim_opening_ms", 0))
    yield edit("drone takedown", lambda d: by_id(d, "drone")["defense"].__setitem__("rear_takedown", True))
    yield edit("untakeable retainer", lambda d: by_id(d, "blade_retainer")["defense"].__setitem__("rear_takedown", False))
    yield edit("silent auditor", lambda d: by_id(d, "auditor")["perception"].__setitem__("alarmist", False))
    yield edit("unknown variant weapon", lambda d: by_id(d, "enforcer_rifle")["variants"][0]["barrier"]["weapon_permille"].__setitem__("99", 1000))


# ---------------------------------------------------------------- bosses.json
BOSS_TOP = {"schema_version", "difficulty", "bosses", "duels"}
BOSS_FIELDS = {"id", "chapter", "beat", "opponent", "name_ja", "reading", "name_en", "style_ja", "style_en", "body",
               "held_weapon", "sparring_weapon", "scale_permille", "health", "lethal", "defeat", "finisher",
               "floor_permille", "poise_ms", "rear_permille", "flank_permille", "body_permille", "arena_radius_cm",
               "transition_ms", "telegraph_min_ms", "deflect_idle_front_deg", "front_blocked_hint", "senses", "hearing",
               "shield", "barrier", "mantle", "weak_points", "wards", "adds", "barks", "phases", "attacks"}
BOSS_ATTACK_FIELDS = {"id", "kind", "name_ja", "name_en", "tell_ja", "tell_en", "telegraph", "bark", "bark_once",
                      "bark_cooldown_ms", "windup_ms", "active_ms", "recovery_ms", "cooldown_ms", "range_cm", "damage",
                      "repeat", "repeat_gap_ms"}
BOSS_KINDS = {
    "cut": {"arc_deg", "hits", "gap_ms", "lunge_cm", "pull_cm", "knockback_cm", "hero_stagger_ms", "guard",
            "marobashi_ms", "muto", "on_parry", "if_guard_held_ms"},
    "thrust": {"width_cm", "hits", "gap_ms", "lunge_cm", "pull_cm", "knockback_cm", "hero_stagger_ms", "guard",
               "marobashi_ms", "muto", "on_parry", "if_guard_held_ms"},
    "feint": {"hold_ms", "then"},
    "charge": {"radius_cm", "width_cm", "target", "miss_recovery_ms", "knockback_cm", "guard"},
    "area": {"radius_cm", "inner_radius_cm", "edge_damage", "arc_deg", "hits", "gap_ms", "knockback_cm",
             "hero_stagger_ms", "guard", "opens", "opens_ms"},
    "beam": {"width_cm", "track_ms", "sweep_deg", "height_cm"},
    "volley": {"rounds", "interval_ms", "lock_cm", "dash_cm"},
    "zone": {"at", "anchor", "count", "spread_cm", "radius_cm", "arm_ms", "life_ms", "tick_ms", "root_ms",
             "stagger_ms", "fragile", "max_active", "void", "breaks_mantle"},
    "summon": {"group"},
    "pulse": {"radius_cm", "expand_ms", "reveal_cm_s"},
    "expose": {"opens", "rotate", "barrier_offline", "interrupt_damage", "interrupt_stagger_ms", "event", "event_limit"},
    "step": {"lunge_cm"},
}
BOSS_GUARD_FIELDS = {"guardable", "chip", "stamina", "breaks", "parry", "parry_hit", "parry_stagger_ms"}
PHASE_FIELDS = {"table", "from_permille", "bark", "move", "pattern", "reactions", "concurrent", "on_enter", "summons",
                "once_below", "at_floor", "ward", "shield", "barrier", "mantle", "shield_while_adds", "floor_permille",
                "hearing_permille", "overrides", "late"}
BARK_EVENTS = {"stagger", "shield_broken", "barrier_broken", "mantle_down", "countered", "missed", "weakpoint_destroyed",
               "seal", "defeated", "muto_dori"}
MUTO_DEFEATS = {"disarm", "capture"}
LINE_ID = re.compile(r"^ch0[1-8]\.b\d\d\.[a-z0-9_]+\.\d{3}$")
# Who may voice a fight's barks: the boss itself (the collector is the cast's
# `banker`, the walker's voice its pilot Margina), or the rival.
VOICES = {"boss_dunark": {"boss_dunark"}, "boss_penalta": {"boss_penalta"}, "boss_hakari": {"boss_margina"},
          "boss_tarifa": {"boss_tarifa"}, "boss_eskro": {"boss_eskro"}, "boss_collatera": {"boss_collatera"},
          "boss_val_amort": {"banker"}, "duel_toranosuke_fukuro": {"rival"}, "duel_toranosuke_steel": {"rival"}}
CAST = {"boss_val_amort": "banker", "duel_toranosuke_fukuro": "rival", "duel_toranosuke_steel": "rival"}
DUELS = [("duel_toranosuke_fukuro", "ch01.b11", ["tora_fukuro"]),
         ("duel_toranosuke_steel", "ch06.b09", ["toranosuke_steel_p1", "toranosuke_steel_p2"])]
# Windups the story bible §8 states outright (Normal).
BIBLE_WINDUPS = {("boss_dunark", "quick_cut"): 500, ("boss_dunark", "heavy_overhead"): 900, ("boss_dunark", "thrust"): 700,
                 ("boss_penalta", "shield_bash"): 600, ("boss_penalta", "hammer_slam"): 1000,
                 ("boss_penalta", "hammer_spin"): 1200, ("boss_hakari", "seizure_net"): 800,
                 ("boss_hakari", "sweep_beam"): 1100, ("boss_tarifa", "tether_lash"): 700,
                 ("boss_tarifa", "steam_burst"): 900, ("boss_eskro", "reconcile_pulse"): 700,
                 ("boss_eskro", "pounce"): 600, ("boss_collatera", "twin_burst"): 400,
                 ("boss_collatera", "margin_call"): 1500, ("boss_val_amort", "amort_final_foreclosure"): 1000}


def chapter_text(chapter):
    return (ROOT / f"docs/campaign/chapter-{chapter:02d}.md").read_text()


def bible_bosses():
    """(id, beat, [phase starts in permille], [quoted voice telegraphs]) rows of the story bible's §8 table."""
    text = (ROOT / "docs/campaign/story-bible.md").read_text()
    section = text[text.index("## 8. Bosses"):text.index("## 9. Story by chapter")]
    rows = []
    for line in section.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == 8 and cells[0].startswith("`boss_"):
            starts = [int(start) * 10 for start in re.findall(r"P\d[^/]*?(\d+)–\d+", cells[3])]
            rows.append({"id": cells[0].strip("`"), "beat": cells[1].split(" ")[0], "starts": starts,
                         "voices": re.findall(r"「([^」]+)」", cells[6])})
    assert len(rows) == 7, f"bible §8 lists {len(rows)} bosses"
    return rows


def bible_cast():
    """Cast-table names by id (bible §6)."""
    text = (ROOT / "docs/campaign/story-bible.md").read_text()
    cast = {}
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 4 and cells[0].startswith("`") and cells[0].endswith("`") and JAPANESE.search(cells[1]):
            cast.setdefault(cells[0].strip("`"), {"ja": cells[1], "reading": cells[2], "en": cells[3]})
    return cast


def line_record(text, line):
    """The speaker and Japanese of a chapter script's line record, or None."""
    found = re.search(r"\bid:\s*\"?" + re.escape(line) + r"\"?[,\s}]", text)
    if not found:
        return None
    rest = text[found.end():]
    following = re.search(r"\bid:\s", rest)
    chunk = rest[:following.start()] if following else rest[:600]
    speaker = re.search(r"\bspeaker:\s*\"?([a-z_]+)", chunk)
    japanese = re.search(r"\bja:\s*\"?([^\"\n,}]+)", chunk)
    return (speaker.group(1) if speaker else None, japanese.group(1).strip() if japanese else None)


def chapter_boss_beat(text, beat):
    """The beat's pattern tables with their starts, its telegraph floor and the patterns its lines bark on."""
    at = text.index(f"id: {beat}\n") if f"id: {beat}\n" in text else text.index(f'id: "{beat}"')
    block = text[at:at + 4000]
    end = re.search(r"\n  - id: ", block[10:])
    block = block[:end.start() + 10] if end else block
    phases = [(int(start) * 10, table) for start, table in
              re.findall(r"hp_pct_start:\s*(\d+)[^}]*?pattern_table:\s*\"?([a-z0-9_]+)", block, re.S)]
    phases += [(int(start) * 10, table) for table, start in
               re.findall(r"from_hp_pct:\s*(\d+)[^}]*?table:\s*\"?([a-z0-9_]+)", block, re.S)][:0]
    for start, table in re.findall(r"from_hp_pct:\s*(\d+),\s*table:\s*\"([a-z0-9_]+)", block):
        phases.append((int(start) * 10, table))
    single = re.search(r"x_pattern_table:\s*([a-z0-9_]+)", block)
    if single:
        phases.append((1000, single.group(1)))
    floor = re.search(r"min_windup_ms:\s*(\d+)", block)
    patterns = set()
    for line in text.splitlines():
        if beat in line:
            patterns |= set(re.findall(r"pattern:([a-z0-9_]+)", line))
    return phases, int(floor.group(1)) if floor else None, patterns


def boss_references(fight):
    """Every line id a fight names, with where."""
    lines = [(f"attack {a['id']}", a["bark"]) for a in fight["attacks"] if a.get("bark")]
    lines += [(f"phase {p['table']}", p["bark"]) for p in fight["phases"] if p.get("bark")]
    lines += [(f"ward {w['id']}", w["bark"]) for w in fight["wards"] if w.get("bark")]
    lines += [(f"bark {b['on']}", b["line"]) for b in fight["barks"]]
    return lines


def validate_bosses(data, enemies):
    errors = []

    def require(condition, message):
        if not condition:
            errors.append(message)
        return condition

    if not require(isinstance(data, dict) and set(data) == BOSS_TOP, f"bosses.json top-level fields must be {sorted(BOSS_TOP)}"):
        return errors
    require(data["schema_version"] == 1, "bosses.json schema_version must be 1")
    difficulty = data["difficulty"]
    require(difficulty == {"easy_windup_permille": 1300, "hard_windup_permille": 850},
            "difficulty: Easy windups +30% and Hard -15% (bible §8)")
    bible = bible_bosses()
    cast = bible_cast()
    require([b["id"] for b in data["bosses"]] == [row["id"] for row in bible], "bosses: the bible §8 roster, in its order")
    require([d["id"] for d in data["duels"]] == [d for d, _, _ in DUELS], "duels: the two Toranosuke duels (ch01, ch06)")
    archetypes = {a["id"]: {v["id"] for v in a["variants"]} for a in enemies["archetypes"]}
    rows = {row["id"]: row for row in bible}
    duel_rows = {d: (beat, tables) for d, beat, tables in DUELS}
    for fight in data["bosses"] + data["duels"]:
        where = fight.get("id", "?")
        if not require(set(fight) == BOSS_FIELDS, f"{where}: fields must be {sorted(BOSS_FIELDS)}"):
            continue
        bDuel = fight in data["duels"]
        require(LOWER_ID.match(where) and where.startswith("duel_" if bDuel else "boss_"), f"{where}: id prefix")
        require((fight["opponent"] == where) != bDuel, f"{where}: a boss is its own opponent; a duel names its npc")
        name = cast.get(CAST.get(where, where))
        if where == "boss_hakari":
            require(fight["name_ja"] == "査定機「秤」", f"{where}: the ch04 name 査定機「秤」")
        elif require(name is not None, f"{where}: not in the bible cast table"):
            require((fight["name_ja"], fight["reading"], fight["name_en"]) == (name["ja"], name["reading"], name["en"]),
                    f"{where}: names must match the bible cast table")
        for field in ("name_ja", "style_ja"):
            require(bool(JAPANESE.search(fight[field])), f"{where}: {field} must be Japanese")
        for field in ("name_en", "style_en"):
            require(fight[field].strip() and not JAPANESE.search(fight[field]), f"{where}: {field} must be English")
        health = fight["health"]
        require(set(health) == {"easy", "normal", "hard"} and all(whole(v, 100, 20000) for v in health.values()),
                f"{where}: health by difficulty")
        require(fight["defeat"] in {"kill", "disarm", "capture", "destroy_weakpoints", "points"}, f"{where}: defeat")
        require(fight["finisher"] in {"none", "muto_dori"}, f"{where}: finisher")
        require(fight["lethal"] == (fight["defeat"] == "kill"), f"{where}: only a kill is lethal")
        require((fight["defeat"] == "destroy_weakpoints") == (fight["body_permille"] == 0),
                f"{where}: an armoured body falls only by its weak points")
        muto_fight = fight["finisher"] == "muto_dori" or fight["defeat"] in MUTO_DEFEATS
        if fight["finisher"] == "muto_dori":
            require(fight["defeat"] in MUTO_DEFEATS, f"{where}: mutō-dori ends only a fight that disarms or captures")
        require((fight["senses"] == "hearing") == (fight["hearing"] is not None), f"{where}: a hearing hunter lists its hearing")
        attacks = {a.get("id"): a for a in fight["attacks"]}
        require(len(attacks) == len(fight["attacks"]), f"{where}: duplicate attack ids")
        adds = {g["id"]: g for g in fight["adds"]}
        wards = {w["id"] for w in fight["wards"]}
        points = {w["id"] for w in fight["weak_points"]}
        for group in fight["adds"]:
            if require(group["archetype"] in archetypes, f"{where}: add {group['id']} names no enemies.json archetype"):
                require(not group["variant"] or group["variant"] in archetypes[group["archetype"]],
                        f"{where}: add {group['id']} names no variant {group['variant']!r}")
        for bark in fight["barks"]:
            require(bark["on"] in BARK_EVENTS, f"{where}: unknown bark event {bark['on']!r}")
        # Attacks.
        reached = set()
        for attack in fight["attacks"]:
            aid = attack.get("id", "?")
            kind = attack.get("kind")
            if not require(kind in BOSS_KINDS and set(attack) == BOSS_ATTACK_FIELDS | {kind},
                           f"{where}.{aid}: fields must be the common set plus one {kind!r} block"):
                continue
            spec = attack[kind]
            require(set(spec) == BOSS_KINDS[kind], f"{where}.{aid}: {kind} fields must be {sorted(BOSS_KINDS[kind])}")
            require(JAPANESE.search(attack["name_ja"]) and JAPANESE.search(attack["tell_ja"]),
                    f"{where}.{aid}: Japanese name and tell")
            require(attack["name_en"].strip() and attack["tell_en"].strip() and not JAPANESE.search(attack["name_en"] + attack["tell_en"]),
                    f"{where}.{aid}: English name and tell")
            require(attack["telegraph"] in {"amber", "cyan", "none"}, f"{where}.{aid}: telegraph")
            hurts = attack["damage"] > 0 or (kind == "zone" and spec["root_ms"] > 0)
            require(not hurts or attack["windup_ms"] >= fight["telegraph_min_ms"],
                    f"{where}.{aid}: windup {attack['windup_ms']} below the fight's {fight['telegraph_min_ms']} ms floor")
            require(not hurts or attack["telegraph"] != "none", f"{where}.{aid}: a hurting attack is telegraphed in colour")
            if kind == "beam" or (kind == "volley"):
                require(attack["telegraph"] == "cyan", f"{where}.{aid}: locked aims and beams are cyan")
            if kind in ("area", "charge"):
                require(attack["telegraph"] == "amber", f"{where}.{aid}: areas and charges are amber")
            expected = BIBLE_WINDUPS.get((where, aid))
            require(expected is None or attack["windup_ms"] == expected, f"{where}.{aid}: bible §8 windup {expected} ms")
            if "guard" in spec:
                g = spec["guard"]
                if require(set(g) == BOSS_GUARD_FIELDS, f"{where}.{aid}: guard fields"):
                    require(0 <= g["chip"] <= attack["damage"], f"{where}.{aid}: chip beyond blow")
                    require(g["guardable"] or (g["chip"] == attack["damage"] and g["stamina"] == 0 and not g["breaks"]),
                            f"{where}.{aid}: an unguardable blow lets all of itself through")
                    require(g["parry"] or (g["parry_hit"] == 0 and g["parry_stagger_ms"] == 0),
                            f"{where}.{aid}: an unparryable blow has no parried hit")
                    if kind in ("cut", "thrust"):
                        require(not g["parry"] or g["parry_stagger_ms"] > 0 or spec["on_parry"] != "none" or spec["marobashi_ms"] > 0,
                                f"{where}.{aid}: a parry staggers or answers, or 転 answers the blow (marobashi_ms)")
                    else:
                        require(not g["parry"], f"{where}.{aid}: only blows are parried")
            if kind in ("cut", "thrust"):
                require(0 <= spec["marobashi_ms"] <= attack["windup_ms"], f"{where}.{aid}: the 転 stretch is the end of the windup")
                require(not spec["muto"] or (muto_fight and kind == "cut" and spec["guard"]["parry"]),
                        f"{where}.{aid}: mutō-dori only on a parryable cut in a fight it may end (rule 4)")
                require((spec["hits"] > 1) == (spec["gap_ms"] > 0), f"{where}.{aid}: multi-hit gaps")
            if kind == "feint":
                reached.add(spec["then"])
                require(spec["then"] in attacks and attacks[spec["then"]]["kind"] in ("cut", "thrust"),
                        f"{where}.{aid}: a feint turns into a blow")
            if kind in ("area", "expose"):
                require(set(spec["opens"]) <= points, f"{where}.{aid}: opens unknown weak points")
            if kind == "summon":
                require(spec["group"] in adds, f"{where}.{aid}: unknown add group")
            if kind == "zone":
                require((spec["at"] in ("anchor", "anchor_or_target")) == bool(spec["anchor"]), f"{where}.{aid}: anchor kind")
            if kind == "volley":
                require(attack["active_ms"] == (spec["rounds"] - 1) * spec["interval_ms"], f"{where}.{aid}: volley timing")
            if kind == "beam":
                require(spec["sweep_deg"] == 0 or attack["active_ms"] > 0, f"{where}.{aid}: a sweep takes its active time")
                require(spec["track_ms"] <= attack["windup_ms"], f"{where}.{aid}: a beam tracks only within its windup")
            if kind in ("pulse",) or (kind == "charge" and spec["target"] == "noise"):
                require(fight["senses"] == "hearing", f"{where}.{aid}: only a blind hunter hunts noises")
            if attack["bark"]:
                require(LINE_ID.match(attack["bark"]), f"{where}.{aid}: bark is not a line id")
        # Phases.
        previous = 1001
        maxima = list(health.values())
        tables = []
        for phase in fight["phases"]:
            if not require(set(phase) == PHASE_FIELDS, f"{where}: phase fields must be {sorted(PHASE_FIELDS)}"):
                continue
            tables.append((phase["from_permille"], phase["table"]))
            require(phase["from_permille"] < previous, f"{where}: phases descend")
            previous = phase["from_permille"]
            for maximum in maxima:
                require(maximum * phase["from_permille"] % 1000 == 0 and maximum * phase["floor_permille"] % 1000 == 0 and
                        maximum * fight["floor_permille"] % 1000 == 0,
                        f"{where}.{phase['table']}: health {maximum} times its starts and floors must be whole")
            pattern = phase["pattern"]
            named = list(pattern["attacks"]) + list(phase["reactions"]) + list(phase["on_enter"]) + \
                [c["attack"] for c in phase["concurrent"]] + [s["attack"] for s in phase["summons"]] + \
                [s["attack"] for s in phase["once_below"]] + ([pattern["fallback"]] if pattern["fallback"] else []) + \
                ([phase["at_floor"]["attack"]] if phase["at_floor"] else [])
            for habit in pattern["habits"]:
                named += list(habit["weights"])
            for aid in named:
                require(aid in attacks, f"{where}.{phase['table']}: names unknown attack {aid!r}")
            reached |= set(named)
            require(not phase["ward"] or phase["ward"] in wards, f"{where}.{phase['table']}: unknown ward")
            require(not phase["shield_while_adds"] or phase["shield_while_adds"] in adds, f"{where}.{phase['table']}: unknown add group")
            # Every telegraph after this phase's changes still meets the floor.
            for group in [phase["overrides"]] + ([phase["late"]["overrides"]] if phase["late"] else []):
                for aid, change in group.items():
                    if require(aid in attacks, f"{where}.{phase['table']}: overrides unknown attack {aid!r}") and "windup_ms" in change:
                        base = attacks[aid]
                        hurts = base["damage"] > 0 or (base["kind"] == "zone" and base["zone"]["root_ms"] > 0)
                        require(not hurts or change["windup_ms"] >= fight["telegraph_min_ms"],
                                f"{where}.{phase['table']}: {aid}'s overridden windup below the floor")
        require(tables and tables[0][0] == 1000, f"{where}: the first phase starts at 1000")
        for aid in attacks:
            require(aid in reached, f"{where}: attack {aid} is in no phase")
        # The story bible and the chapter scripts.
        chapter = chapter_text(fight["chapter"])
        if bDuel:
            beat, duel_tables = duel_rows.get(where, (None, []))
            require(fight["beat"] == beat, f"{where}: beat {beat}")
            require([t for _, t in tables] == duel_tables, f"{where}: pattern tables {duel_tables}")
        else:
            row = rows.get(where)
            if require(row is not None, f"{where}: not in bible §8"):
                require(fight["beat"] == row["beat"], f"{where}: bible §8 beat {row['beat']}")
                require([start for start, _ in tables] == row["starts"], f"{where}: bible §8 phases {row['starts']}")
                chapter_phases, floor, patterns = chapter_boss_beat(chapter, fight["beat"])
                require(chapter_phases == tables, f"{where}: chapter pattern tables {chapter_phases} != {tables}")
                require(floor is None or floor == fight["telegraph_min_ms"], f"{where}: chapter telegraph floor {floor}")
                known = set(attacks) | wards | {"stagger", "pounce_miss"}
                for barked in patterns:
                    require(barked in known, f"{where}: the chapter barks on pattern:{barked}, which the boss lacks")
                voiced = set()
                for _, line in boss_references(fight):
                    record = line_record(chapter, line)
                    if record and record[1]:
                        voiced.add(record[1].strip("「」"))
                for voice in row["voices"]:
                    require(voice in voiced, f"{where}: bible §8 voice telegraph 「{voice}」 is not among its barks")
        for context, line in boss_references(fight):
            if not require(LINE_ID.match(line) and line.startswith(fight["beat"] + "."),
                           f"{where}: {context} line {line} is not a {fight['beat']} line"):
                continue
            record = line_record(chapter, line)
            if require(record is not None, f"{where}: {context} line {line} is not in chapter-{fight['chapter']:02d}.md"):
                require(record[0] in VOICES[where], f"{where}: {context} line {line} is spoken by {record[0]}, not the boss")
    return errors


def boss_mutations(data):
    """Broken copies of bosses.json, each of which one check must reject."""
    def edit(label, change):
        broken = copy.deepcopy(data)
        change(broken)
        return label, broken
    boss = lambda d, i: next(b for b in d["bosses"] + d["duels"] if b["id"] == i)
    attack = lambda d, b, a: next(x for x in boss(d, b)["attacks"] if x["id"] == a)
    yield edit("boss order", lambda d: d["bosses"].reverse())
    yield edit("missing duel", lambda d: d["duels"].pop())
    yield edit("bible threshold", lambda d: boss(d, "boss_dunark")["phases"][1].__setitem__("from_permille", 650))
    yield edit("chapter table", lambda d: boss(d, "boss_penalta")["phases"][1].__setitem__("table", "penalta_phase2"))
    yield edit("bible windup", lambda d: attack(d, "boss_dunark", "heavy_overhead").__setitem__("windup_ms", 800))
    yield edit("short telegraph", lambda d: attack(d, "boss_collatera", "offhand_shot").__setitem__("windup_ms", 300))
    yield edit("short override", lambda d: boss(d, "boss_hakari")["phases"][1]["late"]["overrides"]["claw_sweep"].__setitem__("windup_ms", 700))
    yield edit("English tell", lambda d: attack(d, "boss_eskro", "pounce").__setitem__("tell_ja", "POUNCE"))
    yield edit("missing line", lambda d: attack(d, "boss_tarifa", "rod_sweep").__setitem__("bark", "ch05.b16.tarifa.099"))
    yield edit("wrong speaker", lambda d: attack(d, "boss_tarifa", "rod_sweep").__setitem__("bark", "ch05.b16.kozo.008"))
    yield edit("lost voice telegraph", lambda d: attack(d, "boss_penalta", "hammer_slam").__setitem__("bark", "ch03.b17.penalta.003"))
    yield edit("muto outside its fights", lambda d: attack(d, "boss_dunark", "heavy_overhead")["cut"].__setitem__("muto", True))
    yield edit("転 beyond the windup", lambda d: attack(d, "boss_dunark", "thrust")["thrust"].__setitem__("marobashi_ms", 701))
    yield edit("idle parry", lambda d: attack(d, "boss_penalta", "shield_bash")["cut"].__setitem__("marobashi_ms", 0))
    yield edit("unknown add", lambda d: boss(d, "boss_tarifa")["adds"][0].__setitem__("archetype", "oni"))
    yield edit("uneven health", lambda d: boss(d, "boss_eskro")["health"].__setitem__("hard", 1999))
    yield edit("unreachable attack", lambda d: boss(d, "boss_penalta")["phases"][0]["pattern"]["attacks"].remove("shield_bash"))
    yield edit("unguardable stamina", lambda d: attack(d, "boss_val_amort", "amort_final_foreclosure")["cut"]["guard"].__setitem__("stamina", 20))
    yield edit("unknown field", lambda d: attack(d, "boss_hakari", "sweep_beam").__setitem__("colour", "cyan"))
    yield edit("amber beam", lambda d: attack(d, "boss_val_amort", "amort_ledger_beam").__setitem__("telegraph", "amber"))
    yield edit("pattern barked", lambda d: boss(d, "boss_dunark")["attacks"].remove(attack(d, "boss_dunark", "thrust")))


def main():
    data = json.loads((ROOT / "Content/Data/enemies.json").read_text())
    roster = bible_roster()
    arming = kernel_grenade_arming_cm()
    references = chapter_references()
    errors = validate(data, roster, arming, references)
    if errors:
        print("enemies.json is invalid:", *errors, sep="\n  ")
        return 1
    missed = [label for label, broken in mutations(data) if not validate(broken, roster, arming, references)]
    missed += ["chapter reference"] if not validate(data, roster, arming, [("chapter_test.json", "oni", None)]) else []
    missed += ["chapter variant"] if not validate(data, roster, arming, [("chapter_test.json", "drone", "shielded")]) else []
    if missed:
        print("The validator accepted broken data:", *missed, sep="\n  ")
        return 1
    attacks = sum(len(a["attacks"]) for a in data["archetypes"])
    print(f"enemies.json is valid: {len(data['archetypes'])} archetypes of the bible §7 roster, {attacks} attacks, "
          f"{sum(len(a['variants']) for a in data['archetypes'])} variants, {len(references)} chapter references; "
          f"self-test rejected {len(list(mutations(data))) + 2} broken copies")
    bosses = json.loads((ROOT / "Content/Data/bosses.json").read_text())
    errors = validate_bosses(bosses, data)
    if errors:
        print("bosses.json is invalid:", *errors, sep="\n  ")
        return 1
    missed = [label for label, broken in boss_mutations(bosses) if not validate_bosses(broken, data)]
    if missed:
        print("The boss validator accepted broken data:", *missed, sep="\n  ")
        return 1
    fights = bosses["bosses"] + bosses["duels"]
    print(f"bosses.json is valid: {len(bosses['bosses'])} bosses of the bible §8 roster and {len(bosses['duels'])} duels, "
          f"{sum(len(f['attacks']) for f in fights)} attacks in {sum(len(f['phases']) for f in fights)} phases, "
          f"{sum(len(boss_references(f)) for f in fights)} chapter-script voice lines; "
          f"self-test rejected {len(list(boss_mutations(bosses)))} broken copies")
    return 0


if __name__ == "__main__":
    sys.exit(main())
