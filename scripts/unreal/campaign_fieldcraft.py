"""Fieldcraft: what a beat's stealth, traversal and company need in its space.

campaign_space.py calls ``derive_fieldcraft`` for every beat once its own
points are placed. From the chapter script's ``params`` and ``ext`` it lays
out, by rule and in the same integer centimetres as the rest of the space:

- lamps and fires the guards see by (``light_sources``, ``static_lights``):
  where they stand, how far they light, and how they go dark (Interact held,
  an arrow or round on a floodlight's cable junction, or never) and relight;
- floors that change footsteps (``noise_surfaces``): puddles, gravel, running
  water, tatami, drain boards, board roofs and grates, and the nightingale
  floor with its silent edge strip;
- water to swim and dive in (``traversal`` swim or wade_swim), with the reeds
  and lotus that hide a swimmer's head and the float lines that ring;
- a face to climb (``traversal`` climb): its holds, ledges, grip and falls,
  and the volumes on it the script names (its ledges and its top);
- tsubute (``lures``): how many stones are carried and where rubble refills them;
- a carried candle (``light_carried``);
- the escorted party (``escort``) as people: their health, how long the downed
  may be raised and when they die, collars to cut and cell doors to open
  before they walk, the hide spots along their road and whether they answer
  the hero's signal;
- allies (``allies``): who fights beside the hero, with what, where they
  stand, whether they can be downed, and the wave they join with;
- the people a defence protects (``defend`` targets that are people): each
  at its target, netted as its target is worn down, freed as it is mended;
- rotating volley ranks (``volley_command``): how many ranks of how many
  gunners answer the hero's order, how soon a rank fires, how long it takes
  to reload and how wide and far its ring reaches. Its gunners are the
  ``volley_rank`` allies, one row to a rank.

SoraCatalogSpace.cpp reads the block fail-closed and USoraFieldcraft plays it;
validate_campaign.py checks every point stands on its zone's floor.
"""
from __future__ import annotations

import math
import re

# The standard listener's footstep and crouch-step reach (SoraStealthRules::NoiseRadiusCm).
FOOTSTEP_CM = 450
CROUCH_STEP_CM = 180
# How far each kind of light reaches, in cm (its point light's attenuation radius).
LAMP_RADIUS = {"andon": 650, "lamp": 700, "brazier": 600, "floodlight": 1500, "strip": 450, "arch": 450}
# ch03.b02: "holding Interact for 1 s snuffs one".
SNUFF_MS = 1000
# Footstep loudness of a floor, x1 (the chapters' noise_surfaces mult where they give none).
SURFACE_MULT = {"puddle": 2.0, "gravel": 1.5, "running_water": 0.5, "tatami": 0.5, "board_roof": 1.5,
                "metal_grate": 1.5, "dobuita": 1.5}
PATCH_CM = {"puddle": (360, 360), "gravel": (520, 520), "running_water": (520, 360), "tatami": (600, 600)}
EDGE_STRIP_CM = 90
# A climbing face: its depth behind the face, and the hold spacing's floor.
CLIMB_DEPTH_CM = 640
CLIMB_HEIGHT_CM = 900
# The escorted party: ch03.b07's two-second hold to raise the downed.
REVIVE_HOLD_MS = 2000
HIDE_STEP_CM = 1000
HIDE_OFFSET_CM = 650
CELL_OFFSET_CM = 760
# Allies: what each role fights with (catalog weapon ids; -1: nothing).
ALLY_ROLES = {
    "hold_wicket_side": ("fighter", 0), "hold_north_side": ("fighter", 0), "kusarigama_melee": ("fighter", 2),
    "kusarigama": ("fighter", 2), "melee_naginata": ("fighter", 20), "flank_melee": ("fighter", 0),
    "melee_flank": ("fighter", 0), "hold_line": ("fighter", 19), "mantlet_bearer": ("fighter", 19),
    "meter_breaker": ("fighter", 8), "skirmisher": ("fighter", 4),
    "arc_carbine": ("shooter", 1), "coil_matchlock": ("shooter", 5), "suppress_ranged": ("shooter", 5),
    "volley_rank": ("rank", 5), "mortar_crew": ("shooter", 15),
    "instructor": ("bystander", -1), "kanteki_target_keeper": ("bystander", -1), "brace_gate_bar": ("bystander", -1),
    "noncombat": ("bystander", -1), "noncombat_follow": ("guide", -1), "beacon": ("bystander", -1),
    "gate_winch": ("bystander", -1), "lookout_roof": ("bystander", -1),
    "swim_lead": ("guide", -1), "climb_guide": ("guide", -1), "follow": ("guide", -1),
}
ALLY_HEALTH = 120
ALLY_REVIVE_MS = 3000
ALLY_STEP_CM = 240


def _i(value):
    return int(round(value))


def _frac(rect, fx, fy):
    x0, y0, x1, y1 = rect
    return (_i(x0 + (x1 - x0) * fx), _i(y0 + (y1 - y0) * fy))


def _clear(point, cover, margin):
    return all(abs(point[0] - cx) >= sx / 2 + margin or abs(point[1] - cy) >= sy / 2 + margin
               for cx, cy, sx, sy, _ in cover)


def _inside(rect, point, margin):
    x0, y0, x1, y1 = rect
    return x0 + margin <= point[0] <= x1 - margin and y0 + margin <= point[1] <= y1 - margin


def _whole(value, context, fail):
    number = _i(value)
    if abs(number - value) > 1e-6:
        fail(context, f"{value} is not a whole number here")
    return number


def _ms(seconds, context, fail):
    return _whole(seconds * 1000, context, fail)


def empty():
    return {"lamps": [], "surfaces": [], "water": None, "climb": None, "stones": None, "candle": None,
            "party": [], "signal": False, "hide_spots": [], "releases": [], "allies": [], "people": [], "volley": None}


def _people(beat, record):
    """The people a defence protects (ch04.b12's planters, ch05.b07's Kōzō):
    each stands at its target as a character, netted as its target is worn
    down and freed as the hero mends it."""
    params = beat["params"]
    if params.get("task") != "defend":
        return []
    people = []
    for index, target in enumerate(params["defend"]["targets"]):
        actor = target["actor"]
        if any(word in actor for word in ("pack_horse", "furnace", "forge")) or actor == "aid_station":
            continue
        people.append({"id": actor.split(":", 1)[-1], "target": index, "at": list(record["targets"][index])})
    return people


def owned_volumes(beat):
    """Volumes on a climbing face the fieldcraft raises itself as the climber
    reaches them (its ledges and its top): no floor band stands for them."""
    traversal = beat["ext"].get("traversal") or {}
    if traversal.get("mode") != "climb":
        return set()
    names = set(traversal.get("rest_ledges") or [])
    if isinstance(beat["ext"].get("exit"), str):
        names.add(beat["ext"]["exit"])
    return names


def _lamp(entry, fail, where):
    """One authored light: its id, kind, how it goes dark and relights."""
    if isinstance(entry, str):
        entry = {"id": entry}
    lamp_id = entry["id"]
    kind = entry.get("kind")
    kind = {"alien_floodlight": "floodlight", "cyan_ledger_strip": "strip", None: None}.get(kind, kind)
    if kind is None:
        kind = ("brazier" if lamp_id.startswith(("brazier", "kagaribi")) else
                "arch" if "arch" in lamp_id else
                "strip" if "glow" in lamp_id or "strip" in lamp_id else
                "andon" if "andon" in lamp_id else "lamp")
    if kind not in LAMP_RADIUS:
        fail(where, f"light {lamp_id} has an unknown kind {kind}")
    snuff, hold = "hold", SNUFF_MS
    extinguish = entry.get("extinguish")
    if isinstance(extinguish, str) and extinguish.startswith("interact_hold_s:"):
        hold = _ms(float(extinguish.split(":", 1)[1]), f"{where}.{lamp_id}", fail)
    elif isinstance(extinguish, str) and extinguish.startswith("arrow"):
        snuff = "shot"
    if "extinguishable" in entry:
        value = entry["extinguishable"]
        snuff = "none" if value is False else "shot" if value == "arrow" else snuff
    return {"id": lamp_id, "kind": kind, "radius_cm": LAMP_RADIUS[kind], "snuff": snuff,
            "hold_ms": hold if snuff == "hold" else 0,
            "relight_ms": _ms(entry.get("relight_s", 0), f"{where}.{lamp_id}", fail)}


class _Layout:
    """Where one beat's fieldcraft goes in its zone (or the hub)."""

    def __init__(self, beat, record, zone, rect, cover, allocator):
        self.beat, self.record, self.zone, self.rect, self.cover = beat, record, zone, rect, cover
        self.allocator = allocator
        self.placed = {volume["event"][len("volume_enter:"):]: volume for volume in record["volumes"]}
        params = beat["params"]
        zones = params.get("zone")
        self.whole = set(zones if isinstance(zones, list) else [zones]) | {params.get("bounds")}
        self.scatter = 0

    def patch(self, size):
        """A patch on the floor by a fixed golden-ratio scatter, clear of cover."""
        x0, y0, x1, y1 = self.rect
        for _ in range(64):
            self.scatter += 1
            fx = 0.2 + 0.6 * ((self.scatter * 0.6180339887) % 1.0)
            fy = 0.2 + 0.6 * ((self.scatter * 0.3819660113 + 0.5) % 1.0)
            center = _frac(self.rect, fx, fy)
            if _clear(center, self.cover, max(size) / 2 + 60) and _inside(self.rect, center, max(size) / 2 + 150):
                return {"center": list(center), "size": list(size)}
        return None

    def area(self, name, size):
        """A named area: its trigger band where one is placed, the whole
        floor for the beat's own zone, else a patch."""
        if name in self.placed:
            volume = self.placed[name]
            return {"center": list(volume["center"]), "size": list(volume["size"])}
        x0, y0, x1, y1 = self.rect
        if name in self.whole:
            return {"center": [(x0 + x1) // 2, (y0 + y1) // 2], "size": [x1 - x0 - 300, y1 - y0 - 300]}
        return self.patch(size)

    def spot(self):
        """A free work spot near the guards' routes, else anywhere clear."""
        patrols = [point for loop in self.record["patrols"] for point in loop]
        start = 0
        if patrols:
            key = lambda index: min(math.hypot(self.allocator.spots[index][0] - p[0],
                                               self.allocator.spots[index][1] - p[1]) for p in patrols)
            point = self.allocator.take(start, key)
        else:
            point = self.allocator.take(start)
        return point or (self.patch((120, 120)) or {}).get("center")


def _surfaces(beat, layout, fail):
    rows = []
    for number, entry in enumerate(beat["params"].get("noise_surfaces") or []):
        where = f"{beat['id']}.noise_surfaces[{number}]"
        kind = entry["kind"][2:] if entry["kind"].startswith("x_") else entry["kind"]
        if kind == "water_swim":
            continue
        names = entry.get("volumes") or [entry["volume"]]
        if kind == "nightingale_floor":
            step = _i(entry["walk_cm"] * 1000 / FOOTSTEP_CM)
            crouch = _i(entry["crouch_cm"] * 1000 / CROUCH_STEP_CM)
            edge = _i(entry["edge_crouch_cm"] * 1000 / CROUCH_STEP_CM)
        else:
            mult = entry.get("mult", SURFACE_MULT.get(kind))
            if mult is None:
                fail(where, f"no footstep loudness for {kind}")
            step = crouch = _i(mult * 1000)
            edge = 0 if entry.get("silent_edge") else None
        for name in names:
            area = layout.area(name, PATCH_CM.get(kind, (420, 420)))
            if area is None:
                fail(where, f"no room on the floor for {name}")
            rows.append({"kind": kind, **area, "step_permille": step, "crouch_permille": crouch})
            # The edge strip runs along the band's far side and is added after
            # it, so it wins where they meet (USoraStealth::SurfaceAt).
            if edge is not None:
                cx, cy = area["center"]
                sx, sy = area["size"]
                strip = [cx, _i(cy + sy / 2 - EDGE_STRIP_CM / 2)]
                rows.append({"kind": "edge_strip", "center": strip, "size": [sx, EDGE_STRIP_CM],
                             "step_permille": step, "crouch_permille": edge})
    return rows


def _water(beat, layout, fail):
    params, ext = beat["params"], beat["ext"]
    traversal = ext.get("traversal") or {}
    swims = [entry for entry in params.get("noise_surfaces") or [] if entry["kind"] == "water_swim"]
    if traversal.get("mode") not in ("swim", "wade_swim"):
        if swims:
            fail(beat["id"], "water to swim needs its traversal block")
        return None
    if len(swims) != 1:
        fail(beat["id"], "a swim needs exactly one water_swim surface")
    where = f"{beat['id']}.traversal"
    x0, y0, x1, y1 = layout.rect
    name = swims[0]["volume"]
    area = layout.area(name, (0, 0)) if name in layout.placed or name in layout.whole else \
        {"center": [_i(x0 + (x1 - x0) * 0.8), (y0 + y1) // 2], "size": [_i((x1 - x0) * 0.3), y1 - y0 - 300]}
    surface_noise = traversal.get("surface_noise_cm")
    step = _i(surface_noise * 1000 / FOOTSTEP_CM) if surface_noise is not None else _i(traversal.get("wade_noise_mult", 1.0) * 1000)
    water = {**area,
             "surface_cm_s": _whole(traversal.get("surface_speed_cm_s", 180), where, fail),
             "dive_cm_s": _whole(traversal.get("dive_speed_cm_s", 140), where, fail),
             "breath_ms": _ms(traversal["dive_max_s"], where, fail),
             "recover_ms": _ms(traversal.get("breath_recover_s", 3), where, fail),
             "drown_hp_s": _whole(traversal.get("drown_dps", 10), where, fail),
             "surface_step_permille": step, "cover": [], "lines": []}
    for name in ext.get("cover") or []:
        area = layout.area(name, (520, 420))
        if area is None:
            fail(where, f"no room for the cover {name}")
        water["cover"].append(area)
    for sensor in ext.get("sensors") or []:
        if sensor["kind"] == "float_line":
            area = layout.area(sensor["volume"], (300, 300))
            water["lines"].append({**area, "noise_cm": _whole(sensor["touch_noise_cm"], where, fail)})
    return water


def _climb(beat, layout, fail):
    traversal = beat["ext"].get("traversal") or {}
    if traversal.get("mode") != "climb":
        return None
    where = f"{beat['id']}.traversal"
    if layout.zone is None or layout.zone.form == "route":
        fail(where, "a climbing face needs a walled zone")
    x0, y0, x1, y1 = layout.rect
    holds = _whole(traversal["holds"], where, fail)
    ledges = traversal.get("rest_ledges") or []
    fall = traversal["fall_damage"]
    ledge_holds = [_i(holds * (number + 1) / (len(ledges) + 1)) for number in range(len(ledges))]
    top = beat["ext"].get("exit")
    # The face runs wall to wall across the zone in front of its exit, so the
    # only way to the exit is over the top.
    return {"at": [x1 - CLIMB_DEPTH_CM - 60, (y0 + y1) // 2], "yaw": 180, "width_cm": y1 - y0,
            "depth_cm": CLIMB_DEPTH_CM, "height_cm": CLIMB_HEIGHT_CM, "holds": holds,
            "grip_per_hold": _whole(traversal["grip_per_move"], where, fail),
            "regen_per_s": _whole(traversal["grip_regen_on_ledge_per_s"], where, fail),
            "ledges": ledge_holds, "ledge_events": [f"volume_enter:{name}" for name in ledges],
            "top_event": f"volume_enter:{top}" if isinstance(top, str) else None,
            "hurt_cm": _whole(fall["over_cm"], where, fail), "hurt_hp": _whole(fall["damage"], where, fail),
            "lethal_cm": _whole(fall["lethal_over_cm"], where, fail)}


def _stones(beat, layout, fail):
    lures = beat["params"].get("lures")
    block = lures.get("tsubute") if isinstance(lures, dict) else {} if isinstance(lures, list) and "tsubute" in lures else None
    if block is None:
        return None
    where = f"{beat['id']}.lures"
    piles = []
    for name in block.get("pickups") or []:
        area = layout.area(name, (160, 160))
        if area is None:
            fail(where, f"no room for the rubble {name}")
        piles.append(area["center"])
    carried_max = _whole(block.get("max_carried", 3), where, fail)
    return {"carried": 0 if piles else carried_max, "max": carried_max,
            "noise_cm": _whole(block.get("impact_noise_cm", 1400), where, fail),
            "investigate_ms": _ms(block.get("investigate_s", 8), where, fail), "piles": piles}


def _candle(beat, fail):
    light = beat["ext"].get("light_carried")
    if not light:
        return None
    where = f"{beat['id']}.light_carried"
    cupped = light["cupped"]
    return {"visibility_permille": _i(light["visibility_mult"] * 1000),
            "cupped_permille": _i(cupped["visibility_mult"] * 1000),
            "cupped_rate_permille": _i(cupped["progress_mult"] * 1000),
            "radius_cm": _whole(light["radius_cm"], where, fail)}


def _party(beat, record, zone, fail):
    params, ext = beat["params"], beat["ext"]
    if params.get("task") != "escort":
        return [], False, [], []
    escort = params["escort"]
    where = f"{beat['id']}.escort"
    members, groups = [], []
    for group, npc in enumerate(escort["npcs"]):
        if isinstance(npc, dict):
            count = _whole(npc.get("count", 1), where, fail)
            named = list(npc.get("includes") or [])
            for number in range(count):
                members.append(named[number] if number < len(named) else f"{npc['group']}_{number + 1}")
                groups.append(group)
        elif "ox_cart" not in npc and "pack_horse" not in npc:
            members.append(npc)
            groups.append(group)
    health = _whole(escort.get("npc_health", 100), where, fail)
    if "bleedout_s" in escort:
        revive, bleedout = _ms(escort["down_revive_s"], where, fail), _ms(escort["bleedout_s"], where, fail)
    else:
        revive = REVIVE_HOLD_MS
        bleedout = _ms(escort["down_revive_s"], where, fail) if escort.get("fail_on_npc_death") else 0
    lance = _ms(escort.get("healing_lance_revive_s", 0), where, fail)
    collars = {}
    pre = ext.get("pre_interacts") or {}
    if pre.get("kind") == "seal_cut":
        for target in pre["targets"]:
            collars[target[len("collar_"):]] = _ms(pre["interact_s"], where, fail)
    unknown = sorted(set(collars) - set(members))
    if unknown:
        fail(where, f"collars on people outside the party: {unknown}")
    route = zone.route
    length = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(route, route[1:]))
    middle = (zone.rect[1] + zone.rect[3]) // 2
    releases = []
    release = ext.get("release") or {}
    for number, point in enumerate(release.get("interact_points") or []):
        at = _point_along(route, 300 + 320 * number)
        releases.append({"id": point, "at": [at[0], middle + CELL_OFFSET_CM],
                         "hold_ms": _ms(release["per_point_s"], where, fail)})
    party = []
    for member, group in zip(members, groups):
        door = min(group, len(releases) - 1) if releases else -1
        party.append({"id": member, "health": health, "revive_ms": revive, "bleedout_ms": bleedout,
                      "lance_ms": lance, "free_ms": collars.get(member, releases[door]["hold_ms"] if door >= 0 else 0),
                      "release": door})
    hide = []
    if escort.get("hide_on_signal"):
        chainage, side = 800.0, 1
        while chainage < length - 800:
            at = _point_along(route, chainage)
            spot = [at[0], _i(at[1] + side * HIDE_OFFSET_CM)]
            if _clear(spot, zone.cover, 150) and _inside(zone.rect, spot, 200):
                hide.append(spot)
            chainage += HIDE_STEP_CM
            side = -side
    return party, bool(escort.get("hide_on_signal")), hide, releases


def _point_along(points, chainage):
    remaining = max(0.0, chainage)
    for a, b in zip(points, points[1:]):
        segment = math.hypot(b[0] - a[0], b[1] - a[1])
        if remaining <= segment and segment > 0:
            share = remaining / segment
            return (_i(a[0] + (b[0] - a[0]) * share), _i(a[1] + (b[1] - a[1]) * share))
        remaining -= segment
    return tuple(points[-1])


def _allies(beat, record, layout, fail):
    params, ext = beat["params"], beat["ext"]
    rows = list(params.get("allies") or []) + list(ext.get("allies") or [])
    joins = ext.get("allies_join") or {}
    allies = []
    entry = record["entry"]
    for number, row in enumerate(rows):
        where = f"{beat['id']}.allies[{number}]"
        if row["role"] not in ALLY_ROLES:
            fail(where, f"unknown ally role {row['role']}")
        kind, weapon = ALLY_ROLES[row["role"]]
        count = _whole(row.get("count", 1), where, fail)
        join = joins.get(row["npc"])
        if join is not None and not join.startswith("wave:"):
            fail(where, f"allies join with a wave, not {join}")
        # A volley rank's gunners are its row: league_teppo_rank_a is the first.
        volley_rank = -1
        if kind == "rank":
            letter = re.search(r"rank_([a-d])$", row["npc"])
            if not letter:
                fail(where, f"volley rank {row['npc']} does not name its rank")
            volley_rank = ord(letter.group(1)) - ord("a")
        for member in range(count):
            ally_id = row["npc"] if count == 1 else f"{row['npc']}_{member + 1}"
            allies.append({"id": ally_id, "role": kind, "weapon": weapon,
                           "health": ALLY_HEALTH, "downable": bool(row.get("downable", False)),
                           "revive_ms": _ms(row.get("revive_s", ALLY_REVIVE_MS / 1000), where, fail),
                           "detectable": bool(row.get("detectable", True)), "rank": volley_rank,
                           "joins": f"wave_start:{join[len('wave:'):]}" if join else None})
    # They stand in rows just inside the hero's entry, facing into the place:
    # each volley rank a row of its own, the rest in the rows behind them.
    def row_spots(row):
        for column in range(7):
            side = (column + 1) // 2 * (1 if column % 2 else -1)
            spot = (_i(entry[0] + 330 + row * ALLY_STEP_CM), _i(entry[1] + side * ALLY_STEP_CM))
            if _inside(layout.rect, spot, 200) and _clear(spot, layout.cover, 110):
                yield [spot[0], spot[1]]

    row = 0
    for rank in sorted({ally["rank"] for ally in allies if ally["rank"] >= 0}):
        gunners = [ally for ally in allies if ally["rank"] == rank]
        while len(spots := list(row_spots(row))) < len(gunners):
            row += 1
            if row > 12:
                fail(beat["id"], f"no room for volley rank {rank} by the entry")
        for ally, spot in zip(gunners, spots):
            ally["at"] = spot
        row += 1
    others = [ally for ally in allies if ally["rank"] < 0]
    first = row
    while others:
        if row > 12 + first:
            fail(beat["id"], "no room for its allies by the entry")
        for spot in row_spots(row):
            if not others:
                break
            others.pop(0)["at"] = spot
        row += 1
    return allies


def _volley(beat, allies, fail):
    """The rotating volley ranks the hero commands (ch08.b03, b06)."""
    rows = beat["ext"].get("volley_command")
    ranks = sorted({ally["rank"] for ally in allies if ally["rank"] >= 0})
    if not rows:
        if ranks:
            fail(beat["id"], "volley ranks with no volley_command")
        return None
    where = f"{beat['id']}.volley_command"
    volley = {"ranks": _whole(rows["ranks"], where, fail), "per_rank": _whole(rows["gunners_per_rank"], where, fail),
              "weapon": _whole(rows["weapon"], where, fail), "order_delay_ms": _whole(rows["order_delay_ms"], where, fail),
              "cycle_ms": _ms(rows["rank_cycle_s"], where, fail), "radius_cm": _whole(rows["target_radius_cm"], where, fail),
              "range_cm": _whole(rows["max_range_cm"], where, fail)}
    if ranks != list(range(volley["ranks"])) or any(
            sum(ally["rank"] == rank for ally in allies) != volley["per_rank"] for rank in ranks):
        fail(where, f"{volley['ranks']} ranks of {volley['per_rank']} gunners, not the allies' volley_rank rows")
    if any(ally["weapon"] != volley["weapon"] for ally in allies if ally["rank"] >= 0):
        fail(where, "the ranks carry the volley's arm")
    return volley


def derive_fieldcraft(beat, record, zone, rect, cover, allocator, fail):
    """The beat's fieldcraft block (see the module docstring)."""
    craft = empty()
    layout = _Layout(beat, record, zone, rect, cover, allocator)
    params, ext = beat["params"], beat["ext"]
    for entry in (params.get("light_sources") or []) + (ext.get("static_lights") or []):
        if isinstance(entry, dict) and entry.get("carried_by"):
            continue
        lamp = _lamp(entry, fail, beat["id"])
        point = layout.spot()
        if point is None:
            fail(beat["id"], f"no room for the light {lamp['id']}")
        craft["lamps"].append({**lamp, "at": list(point)})
    craft["surfaces"] = _surfaces(beat, layout, fail)
    craft["water"] = _water(beat, layout, fail)
    craft["climb"] = _climb(beat, layout, fail)
    craft["stones"] = _stones(beat, layout, fail)
    craft["candle"] = _candle(beat, fail)
    if zone is not None and zone.form == "route":
        craft["party"], craft["signal"], craft["hide_spots"], craft["releases"] = _party(beat, record, zone, fail)
    elif params.get("task") == "escort":
        fail(beat["id"], "an escort walks a road")
    craft["allies"] = _allies(beat, record, layout, fail)
    craft["people"] = _people(beat, record)
    craft["volley"] = _volley(beat, craft["allies"], fail)
    return craft
