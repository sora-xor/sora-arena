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
DEFENSE_FIELDS = {"front_block_deg", "rim_opening_ms", "rear_weak_permille", "poise_ms"}
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
    yield edit("silent auditor", lambda d: by_id(d, "auditor")["perception"].__setitem__("alarmist", False))
    yield edit("unknown variant weapon", lambda d: by_id(d, "enforcer_rifle")["variants"][0]["barrier"]["weapon_permille"].__setitem__("99", 1000))


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
    return 0


if __name__ == "__main__":
    sys.exit(main())
