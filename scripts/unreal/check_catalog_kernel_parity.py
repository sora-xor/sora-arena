"""Time-to-kill tables for the offline catalog and the multiplayer kernel, and their parity.

The offline campaign and training arena resolve weapons in Unreal from
Content/Data/catalog.json against the opponents in Content/Data/enemies.json;
multiplayer resolves the same eighteen weapons in the Rust kernel from
crates/arena-core/src/catalog.rs against the six classes. The two rule sets are
tuned separately, so their numbers differ. This script builds both
time-to-kill tables (a body shot from the front: no rear, flank, stagger or
shield) and fails when:

  1. the shared identity drifts: weapon ids, class ownership (the kernel's
     weapon_allowed), the special flag, the melee arms
     (SoraHistoricalArms::IsMelee against the kernel's Melee kind), which
     weapons are shells, and the shells' arming distances
     (SoraCombatRules::ArmingCm against arming_mm);
  2. a multiplayer body-shot engagement leaves the plan's target, "around
     0.8-1.5 seconds, with stronger attacks requiring visible commitment or
     charge time": each uncharged weapon's median over the six classes must
     lie in 0.8-1.5 s, a charged weapon's may run on to 2.0 s, and no class
     may fall below 0.5 s or above 2.0 s;
  3. a shared weapon's offline median over the ordinary opponents (the bible
     §7 roster's first six; the heavy automaton and walker are not ordinary)
     drifts more than 0.5 s from its kernel median, or leaves 0.5-2.0 s.
     The healing lance is excepted: offline it is a support arm whose damage
     its catalog tradeoff reduces.

The campaign's own historical arms (yumi, yari, naginata) and the opponents'
damage against the unguarded hero are printed for reading: the plan sets no
engagement target for them, so their balance is the playtest's (B7).

Kernel time runs in 60 Hz ticks: a charged weapon charges after its
cooldown, so its shots come every cooldown plus charge. Offline, a committed
melee arm lands after its windup and then every windup plus recovery
(SoraHistoricalArms.h), the yumi after its 0.65 s draw and then every
cooldown plus draw, and every other weapon at once and then every cooldown.
"""
import copy
import json
import math
from pathlib import Path
import re
import statistics
import sys

ROOT = Path(__file__).resolve().parents[2]
TICKS = 60
TARGET = (0.8, 1.5)
EXTREMES = (0.5, 2.0)
PARITY_S = 0.5
# The bible §7 roster's ordinary opponents; the automaton and walker are heavies.
ORDINARY = ["enforcer_rifle", "blade_retainer", "shield_enforcer", "grenadier", "marksman", "drone"]
SUPPORT = {17}
HISTORICAL = {18, 19, 20}
BOW_DRAW_S = 0.65


def kernel_catalog():
    """The kernel's frozen weapon and class tables."""
    source = (ROOT / "crates/arena-core/src/catalog.rs").read_text()
    table = source[source.index("pub const WEAPONS"):source.index("pub struct Class")]
    weapons = {}
    for call in re.finditer(r"\bw\(\s*(.*?)\)\s*,", table, re.S):
        fields = [field.strip() for field in call.group(1).split(",") if field.strip()]
        if len(fields) != 13:
            continue
        (wid, name, kind, damage, range_mm, cooldown, stamina, velocity, blast, arming, charge, magazine,
         reload_ticks) = fields
        weapons[int(wid)] = {"name": name.strip('"'), "kind": {"M": "melee", "H": "hitscan", "P": "projectile"}[kind],
                             "damage": int(damage), "cooldown": int(cooldown), "arming_mm": int(arming),
                             "charge": int(charge), "magazine": int(magazine), "reload": int(reload_ticks)}
    classes = [{"name": name, "health": int(health)} for name, health in
               re.findall(r'name: "([^"]+)",\s*health: (\d+),', source[source.index("pub const CLASSES"):])]
    allowed = source[source.index("pub fn weapon_allowed"):]
    allowed = allowed[:allowed.index("\n}")]
    return weapons, classes, allowed


def historical_arms():
    """SoraHistoricalArms.h: each form's windup and recovery, the melee ids and their forms."""
    header = (ROOT / "Source/SoraArena/Public/SoraHistoricalArms.h").read_text()
    profiles = {form: (float(windup), float(recovery)) for form, windup, recovery in
                re.findall(r"case EForm::(\w+): return \{[\d.]+f, [\d.]+f, ([\d.]+)f, ([\d.]+)f,", header)}
    melee_body = header[header.index("constexpr bool IsMelee"):header.index("constexpr EForm FormFor")]
    melee = {int(wid) for wid in re.findall(r"WeaponId == (\d+)", melee_body)}
    form_body = header[header.index("constexpr EForm FormFor"):header.index("constexpr bool CanStrike")]
    forms = {int(wid): form for wid, form in re.findall(r"case (\d+): return EForm::(\w+);", form_body)}
    default = re.search(r"default: return EForm::(\w+);", form_body).group(1)
    return profiles, melee, {wid: forms.get(wid, default) for wid in melee}


def arming_cm():
    """SoraCombatRules::ArmingCm for the two shells."""
    header = (ROOT / "Source/SoraArena/Public/SoraCombatRules.h").read_text()
    grenade = int(re.search(r"GrenadeLauncherArmingCm = (\d+);", header).group(1))
    mortar = int(re.search(r"MicroMortarArmingCm = (\d+);", header).group(1))
    return {7: grenade, 15: mortar}


def kernel_ttk(weapon, health):
    """Seconds from the first press to the killing hit in the kernel."""
    hits = math.ceil(health / weapon["damage"])
    interval = weapon["cooldown"] + weapon["charge"]
    reloads = (hits - 1) // weapon["magazine"] if weapon["magazine"] else 0
    return (weapon["charge"] + (hits - 1) * interval + reloads * weapon["reload"]) / TICKS


def offline_ttk(weapon, health, profiles, forms):
    """Seconds from the first press to the killing hit offline."""
    hits = math.ceil(health / weapon["damage"])
    if weapon["id"] in forms:
        windup, recovery = profiles[forms[weapon["id"]]]
        first, interval = windup, windup + recovery
    elif weapon["kind"] == "bow":
        first, interval = BOW_DRAW_S, weapon["cooldown"] + BOW_DRAW_S
    else:
        first, interval = 0.0, weapon["cooldown"]
    magazine = weapon["magazine"] if weapon["kind"] != "melee" else 0
    reloads = (hits - 1) // magazine if magazine else 0
    return first + (hits - 1) * interval + reloads * weapon["reload"]


def opponent_ttk(attack, health):
    """Seconds an archetype's attack takes to bring the unguarded hero from full to none."""
    rounds = attack.get("rounds", 1)
    # One aimed round in three misses (SoraCombatRules::RoundMisses).
    landing = rounds - rounds // 3 if attack["kind"] == "burst" else 1
    per_cycle = attack["damage"] * landing
    if per_cycle <= 0:
        return None
    cycle = (attack["windup_ms"] + (rounds - 1) * attack.get("interval_ms", 0) + attack["recovery_ms"] +
             attack["cooldown_ms"]) / 1000.0
    cycles = math.ceil(health / per_cycle)
    return attack["windup_ms"] / 1000.0 + (cycles - 1) * cycle


def table(title, rows, columns):
    print(title)
    width = max(len(name) for name, _ in rows)
    print("  " + " " * width + "  " + " ".join(f"{column[:8]:>8}" for column in columns) + "   median")
    for name, values in rows:
        cells = " ".join(f"{value:8.2f}" if value is not None else f"{'-':>8}" for value in values)
        present = [value for value in values if value is not None]
        print(f"  {name:<{width}}  {cells}   {statistics.median(present):6.2f}")


def check(data, report):
    """Every problem with the tables in data; prints the tables when report is set."""
    errors = []
    require = lambda holds, message: holds or errors.append(message)
    show = table if report else (lambda *_: None)
    catalog, enemies = data["catalog"], data["enemies"]
    kernel, kernel_classes, allowed = data["kernel"], data["classes"], data["allowed"]
    profiles, melee_ids, forms, arming = data["profiles"], data["melee"], data["forms"], data["arming"]
    shared = {w["id"]: w for w in catalog["weapons"]}
    offline = dict(shared)
    offline.update({w["id"]: w for w in catalog["campaign_weapons"]})

    # 1. Shared identity.
    require(sorted(shared) == list(range(18)) and sorted(kernel) == list(range(18)),
            f"weapons 0-17 in both tables (catalog {sorted(shared)}, kernel {sorted(kernel)})")
    require(len(kernel_classes) == 6 and len(catalog["classes"]) == 6, "six classes in both tables")
    for clause in ("weapon == class * 2", "weapon == class * 2 + 1", "weapon == 12 + class"):
        require(clause in allowed, f"kernel weapon_allowed no longer reads '{clause}'")
    for wid, weapon in shared.items():
        owner = wid - 12 if wid >= 12 else wid // 2
        require(weapon["class"] == owner, f"weapon {wid}: catalog class {weapon['class']}, kernel ownership {owner}")
        require(weapon["special"] == (wid >= 12), f"weapon {wid}: special flag differs from the kernel's ids 12-17")
        if wid in kernel:
            require((weapon["kind"] == "melee") == (kernel[wid]["kind"] == "melee"), f"weapon {wid}: melee in one table only")
            require((weapon["kind"] == "explosive") == (kernel[wid]["arming_mm"] > 0),
                    f"weapon {wid}: a shell in one table only")
    for cid, cls in enumerate(catalog["classes"]):
        require(cls["weapons"] == [2 * cid, 2 * cid + 1, 12 + cid], f"class {cid}: catalog weapons {cls['weapons']}")
    kernel_melee = {wid for wid, weapon in kernel.items() if weapon["kind"] == "melee"}
    require(melee_ids == kernel_melee | (HISTORICAL - {18}),
            f"SoraHistoricalArms::IsMelee {sorted(melee_ids)} is not the kernel's melee {sorted(kernel_melee)} with the yari and naginata")
    for wid, cm in arming.items():
        require(wid in kernel and cm * 10 == kernel[wid]["arming_mm"],
                f"weapon {wid}: offline arms at {cm} cm, the kernel at {kernel.get(wid, {}).get('arming_mm')} mm")
    for wid, form in forms.items():
        windup, recovery = profiles[form]
        require(abs(windup + recovery - offline[wid]["cooldown"]) < 1e-6,
                f"weapon {wid}: {form} windup plus recovery {windup + recovery:.2f} s is not its catalog cooldown {offline[wid]['cooldown']}")
    if errors:
        return errors

    # 2. Multiplayer, the kernel against the six classes.
    kernel_rows = []
    kernel_median = {}
    for wid in range(18):
        values = [kernel_ttk(kernel[wid], cls["health"]) for cls in kernel_classes]
        kernel_rows.append((f"{wid:2d} {kernel[wid]['name']}", values))
        kernel_median[wid] = statistics.median(values)
        ceiling = EXTREMES[1] if kernel[wid]["charge"] > 0 else TARGET[1]
        require(TARGET[0] <= kernel_median[wid] <= ceiling,
                f"kernel weapon {wid}: median body-shot time-to-kill {kernel_median[wid]:.2f} s is outside {TARGET[0]}-{ceiling} s")
        for cls, value in zip(kernel_classes, values):
            require(EXTREMES[0] <= value <= EXTREMES[1],
                    f"kernel weapon {wid} against {cls['name']}: {value:.2f} s is outside {EXTREMES[0]}-{EXTREMES[1]} s")
    show("Multiplayer (crates/arena-core/src/catalog.rs), seconds to kill each class with body shots:",
         kernel_rows, [cls["name"] for cls in kernel_classes])

    # 3. Offline, the catalog against the ordinary opponents, and its parity.
    offline_rows = []
    offline_median = {}
    for wid in sorted(offline):
        values = [offline_ttk(offline[wid], enemies[aid]["health"], profiles, forms) for aid in ORDINARY]
        offline_rows.append((f"{wid:2d} {offline[wid]['name_en']}", values))
        offline_median[wid] = statistics.median(values)
        if wid not in SUPPORT and wid not in HISTORICAL:
            require(EXTREMES[0] <= offline_median[wid] <= EXTREMES[1],
                    f"offline weapon {wid}: median body-shot time-to-kill {offline_median[wid]:.2f} s is outside {EXTREMES[0]}-{EXTREMES[1]} s")
    show("Offline (Content/Data/catalog.json against enemies.json), seconds to kill each ordinary opponent with body shots:",
         offline_rows, ORDINARY)
    outside = [f"{wid} {offline_median[wid]:.2f} s" for wid in sorted(HISTORICAL | SUPPORT)
               if not TARGET[0] <= offline_median[wid] <= TARGET[1]]
    if report and outside:
        print(f"  Outside {TARGET[0]}-{TARGET[1]} s, with no plan target (campaign historical arms and the support lance): "
              + ", ".join(outside))
    drift = []
    for wid in range(18):
        gap = offline_median[wid] - kernel_median[wid]
        drift.append((wid, gap))
        if wid not in SUPPORT:
            require(abs(gap) <= PARITY_S,
                    f"weapon {wid}: offline median {offline_median[wid]:.2f} s drifts {gap:+.2f} s from the kernel's {kernel_median[wid]:.2f} s")
    if report:
        print("Offline median minus kernel median, seconds:", " ".join(f"{wid}:{gap:+.2f}" for wid, gap in drift))

    # The opponents against the hero, for reading.
    hero = catalog["classes"][0]["health"]
    rows = []
    for aid, archetype in enemies.items():
        for attack in archetype["attacks"]:
            value = opponent_ttk(attack, hero)
            if value is not None:
                rows.append((f"{aid}.{attack['id']}", [value]))
    show(f"Campaign opponents against the unguarded hero ({hero} health), seconds (no plan target):", rows, ["alone"])
    return errors


def mutations(data):
    """Broken copies of the tables, each of which one check must reject."""
    def edit(label, change):
        broken = copy.deepcopy(data)
        change(broken)
        return label, broken
    weapon = lambda d, wid: next(w for w in d["catalog"]["weapons"] if w["id"] == wid)
    yield edit("class ownership", lambda d: weapon(d, 3).__setitem__("class", 2))
    yield edit("special flag", lambda d: weapon(d, 12).__setitem__("special", False))
    yield edit("melee in one table", lambda d: d["kernel"][4].__setitem__("kind", "hitscan"))
    yield edit("shell in one table", lambda d: weapon(d, 16).__setitem__("kind", "explosive"))
    yield edit("arming drift", lambda d: d["arming"].__setitem__(7, 250))
    yield edit("melee arms", lambda d: d["melee"].discard(20))
    yield edit("windup and cooldown", lambda d: d["profiles"].__setitem__("Katana", (.3, .55)))
    yield edit("ownership rule", lambda d: d.__setitem__("allowed", d["allowed"].replace("12 + class", "11 + class")))
    yield edit("instant kernel kill", lambda d: d["kernel"][0].__setitem__("damage", 200))
    yield edit("slow kernel weapon", lambda d: d["kernel"][1].__setitem__("cooldown", 30))
    yield edit("uncharged past the target", lambda d: d["kernel"][13].__setitem__("cooldown", 12))
    yield edit("offline drift", lambda d: weapon(d, 9).__setitem__("cooldown", .4))
    yield edit("tough opponents", lambda d: [d["enemies"][aid].__setitem__("health", 400) for aid in ORDINARY])


def main():
    catalog = json.loads((ROOT / "Content/Data/catalog.json").read_text())
    enemies = {a["id"]: a for a in json.loads((ROOT / "Content/Data/enemies.json").read_text())["archetypes"]}
    kernel, classes, allowed = kernel_catalog()
    profiles, melee, forms = historical_arms()
    data = {"catalog": catalog, "enemies": enemies, "kernel": kernel, "classes": classes, "allowed": allowed,
            "profiles": profiles, "melee": melee, "forms": forms, "arming": arming_cm()}
    errors = check(data, True)
    if errors:
        print("Catalog and kernel parity fails:", *errors, sep="\n  ")
        return 1
    accepted = [label for label, broken in mutations(data) if not check(broken, False)]
    if accepted:
        print("The parity check accepted broken tables:", *accepted, sep="\n  ")
        return 1
    print(f"Catalog and kernel parity passes: identity of weapons 0-17, {len(classes)} classes and "
          f"{len(melee)} melee arms; multiplayer medians within {TARGET[0]}-{TARGET[1]} s (charged weapons to "
          f"{EXTREMES[1]} s); offline medians within {PARITY_S} s of the kernel's; "
          f"self-test rejected {len(list(mutations(data)))} broken copies")
    return 0


if __name__ == "__main__":
    sys.exit(main())
