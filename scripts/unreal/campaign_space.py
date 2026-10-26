"""Campaign spaces: where every beat of a chapter happens in the world.

The chapter scripts name a place for each beat (bible §14) and the points its
task uses (pickups, drop-offs, stations, defended targets, trigger volumes),
but ch04-ch08 author no coordinates and ch01-ch03 author theirs in per-place
frames. ``derive_space`` lays out one playable chapter by rule, in integer
centimetres in the Unreal world frame (origin at the arena centre, every floor
at z 0):

- the hub: the chapter's own arena, built by SoraWorldBuilder's shared layout,
  when one of the chapter's places *is* that arena (a bold "**Arena N**" row
  whose N is the chapter's map). Its points reuse the arena's clear road,
  production sites, caches and spawns, mirrored here from SoraWorldBuilder.cpp;
- a walled zone for every other place, sized by its form (yard, hall, field)
  and whether it hosts a boss, in a row beyond the arena;
- a walled route corridor for every ride and escort, as long as the script
  says (or as its pace and target time imply), in rows beyond the zones. The
  road meanders inside straight walls, so no corner leaves a gap;
- per beat: where a travel cut places the hero, its anchor, objectives,
  pickups, drop-offs, manufacturing stations, defended targets, the trigger
  volumes its events name, opponent spawns, guard patrols, an explore cache,
  a cinematic camera and, for rides and mounted fights, the horse;
- a pickup for every collectible that no explore cache holds.

SoraWorldBuilderLayout.cpp builds exactly this. validate_campaign.py checks
that every point stands on its zone's floor, clear of walls and cover, and
that routes are as long as the script asks. The authored ch01-ch03 layout
frames stay in the chapter file's ``layout`` block for the level artists.
"""
from __future__ import annotations
from campaign_lift import place_lift
from campaign_flood import place_flood
from campaign_climb import place_climb
from campaign_moat import place_moat
from campaign_spire import place_spire
from campaign_summit import place_summit
from campaign_wood import connect_wood
from campaign_ridge import place_wind

import math
import re

from campaign_fieldcraft import derive_fieldcraft, owned_volumes

# Mirrors of the arena build (SoraWorldBuilder.cpp) for hub beats: the floor
# inside the perimeter walls, the gate where the hero starts, the east torii,
# the central road clear of lantern posts and cover, the three production
# sites, the gaps between building rows used for caches, the invader spawns,
# and nooks beside the road for collectibles.
ARENA_RECT = (-3150, -2550, 3150, 2550)
ARENA_ENTRY = (-2700, 0, 0)
ARENA_SPOTS = ((-1650, 220), (-1250, -220), (-850, 220), (-400, -220), (0, 220),
               (400, -220), (850, 220), (1250, -220), (1650, 220), (2050, -220))
ARENA_SITES = ((-1250, -700), (0, 1000), (1250, -800))
ARENA_CACHES = ((-1500, 1100), (500, -1100), (1500, 1100), (-500, -1100))
# Every spawn clears the building rows of all four arenas (Lantern Ward's
# stand closer to the road).
ARENA_SPAWNS = ((2700, -1100), (2700, 1100), (500, 1800), (-500, -1850), (2100, 450), (500, -1400))
ARENA_NOOKS = ((-1850, 700), (-1850, -700), (-50, -700), (850, 700), (1750, -700), (-50, 700))
ARENA_PATROLS = (((-1650, -330), (1650, -330), (1650, 330), (-1650, 330)),
                 ((-900, -330), (900, -330), (900, 330), (-900, 330)))
ARENA_EXIT = ((2000, 0), (500, 900))
ARENA_CAMERA = (-2950, -600, 520, -2450, 300, 470, 0, 0, 180)



def arena_blockers(map_id):
    """The arena's collision boxes as (x0, y0, x1, y1): its building rows
    (with their foundations), cover, lantern poles, torii posts and Lantern
    Ward's street terminal (SoraWorldBuilder.cpp, SoraMapLanternWard.cpp)."""
    rects = []
    row = 1200 if map_id == 1 else 1800
    for side in (-1, 1):
        for index in range(5):
            x = -2000 + index * 1000
            rects.append((x - 342, side * row - 367, x + 342, side * row + 367))
    for index in range(12):
        x, y = -2300 + (index % 6) * 900, (-1 if index < 6 else 1) * (680 + (index % 2) * 200)
        rects.append((x - 115, y - 90, x + 115, y + 90))
    for index in range(10):
        x, y = -2250 + (index % 5) * 1125, (-1 if index < 5 else 1) * 470
        rects.append((x - 7, y - 7, x + 7, y + 7))
    for x in (-2250, 2300):
        for side in (-1, 1):
            rects.append((x - 22, side * 240 - 22, x + 22, side * 240 + 22))
    if map_id == 1:
        rects.append((-730 - 70, 460 - 37, -730 + 70, 460 + 37))
    return rects


STYLES = ("estate", "ward", "foundry", "citadel")
# Bible §14 places by form. Halls are interiors and kit rooms; fields are open
# country; every other place is a walled yard.
HALLS = {
    "pl_tsumagizaka_dojo", "pl_umaya", "pl_dojo_smithy", "pl_bugugura", "pl_chochin_kobo", "pl_itotoriba",
    "pl_hataba", "pl_takadono", "pl_okaji", "pl_aratamejo", "pl_sumigoya", "pl_toritategura", "pl_imonoba",
    "pl_relay_room", "pl_ledger_corridors", "pl_uguisu_hall", "pl_archive", "pl_press_hall", "pl_vault_core",
    "pl_cargo_hold", "pl_seized_vault", "pl_reckoning_engine", "pl_hangar", "pl_bridge_approach", "pl_bridge",
    "pl_collateral_cells", "pl_ledger_spire", "pl_ledger_engine", "pl_shoya_yashiki", "pl_gogura",
    "pl_suisha_goya",
}
FIELDS = {"pl_shimomura", "pl_tanada", "pl_kakuredani", "pl_kanna_nagashi", "pl_otameike", "pl_kayanohara",
          "pl_matoba", "pl_issoseki_wood", "pl_hull_ridge"}
# Floor size and wall height by form; a zone that hosts a boss is at least BOSS_SIZE.
FORMS = {"hall": (3600, 2600, 700), "yard": (4400, 3200, 360), "field": (7200, 5200, 220)}
BOSS_SIZE = (5600, 4200)
ZONE_GAP = 3000
ZONE_ROW_X = 8000
ROUTE_ROW_Y = -12000
ROUTE_ROW_STEP = 5000
ROUTE_HALF_WIDTH = 1200
ROUTE_WALL = 200
ROUTE_PAD = 1400
ROUTE_STEP = 4000
ROUTE_SWAY = 450
WALL_THICKNESS = 60
FLOOR_EDGE = 150
COVER_SIZE = (230, 180, 140)
# Fractions of a zone's floor: work spots in three middle rows, cover by the
# walls, spawns at the edges, nooks for pickups and caches, patrol loops.
SPOT_X = (0.22, 0.38, 0.54, 0.70)
SPOT_Y = (0.36, 0.5, 0.64)
COVER_X = (0.30, 0.46, 0.62, 0.78)
COVER_Y = (0.2, 0.8)
SPAWN_AT = ((0.94, 0.07), (0.94, 0.93), (0.78, 0.07), (0.78, 0.93), (0.5, 0.07), (0.5, 0.93))
NOOK_AT = ((0.1, 0.88), (0.3, 0.07), (0.3, 0.93), (0.1, 0.36), (0.62, 0.07), (0.62, 0.93))
CACHE_AT = (0.1, 0.12)
PATROL_AT = (((0.3, 0.3), (0.75, 0.3), (0.75, 0.7), (0.3, 0.7)),
             ((0.45, 0.4), (0.62, 0.4), (0.62, 0.6), (0.45, 0.6)))
SITE_X = 0.86
SITE_Y = {1: (0.5,), 2: (0.3, 0.7), 3: (0.25, 0.5, 0.75)}
SITE_CLEAR = 450
STATION_STEP = 320
# Ride pacing (chapter-04 §6.5, all rides): speeds in cm/s and wind per second
# for walk, trot, canter and gallop; the gallop locks out below 20 until 50.
GAITS = ("walk", "trot", "canter", "gallop")
GAIT_SPEEDS = (170, 350, 550, 800)
STAMINA_PER_S = (8, 8, 0, -12)
STAMINA_LOCKOUT = (20, 50)
# Bible §4.2-4.3 mounted arcs, degrees from the horse's heading (negative = left).
ARCS = {0: (30, 150), 18: (-170, 15), 19: (-10, 60)}
HORSE_COATS = {"kurimaru": "chestnut", "arashi": "black_bay", "pack_horse": "bay"}
# Length a ride or escort gets when the script gives none: the share of its
# target time spent moving at its pace, within these bounds (cm).
ROUTE_MOVING_SHARE = 0.5
ESCORT_MOVING_SHARE = 0.6
ROUTE_BOUNDS = (20000, 180000)
ESCORT_BOUNDS = (6000, 40000)


def _i(value):
    return int(round(value))


def _frac(rect, fx, fy):
    x0, y0, x1, y1 = rect
    return (_i(x0 + (x1 - x0) * fx), _i(y0 + (y1 - y0) * fy))


def _dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def place_style(place, chapter_map):
    arena = place.get("arena")
    return STYLES[arena if arena is not None else chapter_map]


def place_form(place_id):
    return "hall" if place_id in HALLS else "field" if place_id in FIELDS else "yard"


def is_hub(place, chapter_map):
    """A bold "**Arena N**" row is the arena itself; other rows only borrow its look."""
    return place.get("arena") == chapter_map and place.get("hub", False)


def box(center, size, height):
    return [center[0], center[1], size[0], size[1], height]


def _walls(rect, height):
    x0, y0, x1, y1 = rect
    w, h, t = x1 - x0, y1 - y0, WALL_THICKNESS
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    return [box((x0 - t // 2, cy), (t, h + 2 * t), height), box((x1 + t // 2, cy), (t, h + 2 * t), height),
            box((cx, y0 - t // 2), (w, t), height), box((cx, y1 + t // 2), (w, t), height)]


def _route_polyline(start, length):
    """A road from start along +X that sways by ROUTE_SWAY, exactly length cm long."""
    points, total, step = [start], 0.0, 1
    pattern = (0, ROUTE_SWAY, 0, -ROUTE_SWAY)
    while total < length:
        previous = points[-1]
        target = (start[0] + ROUTE_STEP * step, start[1] + pattern[step % 4])
        segment = _dist(previous, target)
        if total + segment >= length:
            share = (length - total) / segment
            points.append((_i(previous[0] + (target[0] - previous[0]) * share),
                           _i(previous[1] + (target[1] - previous[1]) * share)))
            break
        points.append(target)
        total += segment
        step += 1
    return points


def polyline_length(points):
    return sum(_dist(a, b) for a, b in zip(points, points[1:]))


def point_along(points, chainage):
    """The point chainage cm along a polyline, clamped to its ends."""
    remaining = max(0.0, chainage)
    for a, b in zip(points, points[1:]):
        segment = _dist(a, b)
        if remaining <= segment and segment > 0:
            share = remaining / segment
            return (_i(a[0] + (b[0] - a[0]) * share), _i(a[1] + (b[1] - a[1]) * share))
        remaining -= segment
    return tuple(points[-1])


class Zone:
    def __init__(self, zone_id, place, style, form, rect, wall):
        self.id, self.place, self.style, self.form, self.rect, self.wall = zone_id, place, style, form, rect, wall
        self.sites = []
        self.route = []
        self.cover = []
        self.props = []
        x0, y0, x1, y1 = rect
        self.entry = (x0 + 280, (y0 + y1) // 2, 0)

    def record(self):
        return {"id": self.id, "place": self.place, "style": self.style, "form": self.form,
                "rect": list(self.rect), "wall_cm": self.wall, "entry": list(self.entry),
                "walls": getattr(self, "walls", _walls(self.rect, self.wall)), "cover": self.cover, "props": self.props,
                "route": [list(point) for point in self.route],
                **({"z_bounds_cm": list(self.z_bounds)} if hasattr(self,"z_bounds") else {})}


def _referenced_volumes(beat, triggers):
    """Every volume the beat's events name, in the order they are first named,
    but those on a climbing face, which its fieldcraft raises itself."""
    names = []
    owned = owned_volumes(beat)

    def add(event):
        if event and event.startswith("volume_enter:"):
            name = event.split(":", 1)[1]
            if name not in names and name not in owned:
                names.append(name)
    task = beat["task"]
    for key in ("lines_event", "closing_event", "exit_event"):
        add(task[key])
    for wave in task["waves"]:
        add(wave.get("event"))
    for row in triggers:
        if row["beat"] == beat["id"]:
            add(row["on"])
    ext = beat["ext"]
    spook = ext.get("scripted_spook") or {}
    add(f"volume_enter:{spook['volume']}" if spook.get("volume") else None)
    for forced in ext.get("forced_gait_volumes") or []:
        add(f"volume_enter:{forced['volume']}")
    # A ride's objectives on the road (ch08.b02's seal stakes) stand in their volumes.
    if beat["type"] == "horseback_ride":
        for objective in beat["params"].get("objectives") or []:
            add(f"volume_enter:{objective['volume']}" if objective.get("volume") else None)
    return names


def _item_kind(item):
    if item in ("tanemomi_hyo", "kamasu_rice", "barley_load", "barley_sheaf"):
        return "bale"
    if item == "ration_bundle":
        return "bundle"
    if item == "public_registry_box":
        return "box"
    return "crate"


def _point_kind(name):
    return "horse" if "pack_horse" in name else "depot"


def _target_kind(actor):
    """A defended target's kit: a pack horse, a furnace, the aid tent; a
    person is the fieldcraft's own character (campaign_fieldcraft.py)."""
    if "pack_horse" in actor:
        return "horse"
    if "furnace" in actor or "forge" in actor:
        return "furnace"
    if actor == "aid_station":
        return "tent"
    return "person"


def _party(npcs):
    """The escort's carts and horses, which the kit builds; its people are
    the fieldcraft's party (campaign_fieldcraft.py)."""
    kinds = []
    for npc in npcs:
        if isinstance(npc, str) and "ox_cart" in npc:
            kinds.append("cart")
        elif isinstance(npc, str) and "pack_horse" in npc:
            kinds.append("horse")
    return kinds[:6]


def _crank_work(actor):
    if "sluice" in actor or "weir" in actor:
        return "sluice"
    if "bellows" in actor:
        return "bellows"
    return "lift"


def _ride_length(beat):
    params, ext = beat["params"], beat["ext"]
    for source in (ext.get("route_length_m"), (params.get("escort") or {}).get("path_length_m")):
        if source is not None:
            return _i(source * 100)
    if beat["type"] == "horseback_ride":
        gaits = params.get("gaits") or ["walk", "trot"]
        # The pace of the second-slowest gait it may use, for its moving share.
        pace = GAIT_SPEEDS[min(GAITS.index(gaits[-1]), 1)]
        return max(ROUTE_BOUNDS[0], min(ROUTE_BOUNDS[1], _i(pace * beat["target_s"] * ROUTE_MOVING_SHARE)))
    escort = params["escort"]
    return max(ESCORT_BOUNDS[0], min(ESCORT_BOUNDS[1],
                                     _i(escort["speed_cm_s"] * beat["target_s"] * ESCORT_MOVING_SHARE)))


def _authored_spline_length(beat, layout):
    route = beat["params"].get("route")
    for spline in layout["splines"]:
        if spline["id"] == route and spline.get("length_m"):
            return _i(spline["length_m"] * 100)
    return None


def _gait_speeds(beat):
    speeds = list(GAIT_SPEEDS)
    authored = beat["ext"].get("speeds_cm_s") or beat["ext"].get("gait_speeds_cm_s") or {}
    for name, value in authored.items():
        speeds[GAITS.index(name)] = int(value)
    return speeds


def _stamina(stamina, fail, where):
    """Wind per second for walk, trot, canter and gallop from a script's horse_stamina."""
    per_s = list(STAMINA_PER_S)
    if stamina:
        known = {"max", "gallop_drain_per_s", "canter_drain_per_s", "recover_per_s", "canter_regen_per_s",
                 "trot_regen_per_s"}
        if set(stamina) - known:
            fail(where, f"horse_stamina keys {sorted(set(stamina) - known)}")
        if stamina.get("max", 100) != 100:
            fail(where, "horse stamina is out of 100")
        if "recover_per_s" in stamina:
            per_s[0] = per_s[1] = int(stamina["recover_per_s"])
        if "trot_regen_per_s" in stamina:
            per_s[0] = per_s[1] = int(stamina["trot_regen_per_s"])
        if "canter_drain_per_s" in stamina:
            per_s[2] = -int(stamina["canter_drain_per_s"])
        if "canter_regen_per_s" in stamina:
            per_s[2] = int(stamina["canter_regen_per_s"])
        per_s[3] = -int(stamina["gallop_drain_per_s"])
    return {"max": 100, "per_s": per_s, "lockout": STAMINA_LOCKOUT[0], "recover": STAMINA_LOCKOUT[1]}


def spook_dismount(beat, fail):
    """An explicit cargo policy, independent of the ordinary horse-down rule."""
    params = beat["params"]
    response = params.get("on_spook", "shy")
    if type(response) is not str or response not in ("shy", "dismount_continue"):
        fail(beat["id"], "on_spook must be shy or dismount_continue")
    if response == "shy":
        return False
    fear = params.get("fear")
    if (beat["type"] != "horseback_ride" or params.get("mode") != "cargo" or
            params.get("dismount_allowed") is not True or params.get("on_horse_down") != "dismount_continue" or
            not isinstance(params.get("cargo"), dict) or params["cargo"].get("carrier") != "pack_horse" or
            not isinstance(fear, dict) or any(type(fear.get(key)) not in (int, float) or
                not math.isfinite(fear[key]) or fear[key] <= 0 for key in ("spook_radius_cm", "recover_s"))):
        fail(beat["id"], "spook dismount requires a fearful cargo mount, a led pack horse and foot continuation")
    return True


def _mount(beat, ride, fail):
    """The horse a ride or a mounted boss phase puts under the hero."""
    where = beat["id"]
    dismount_on_spook = spook_dismount(beat, fail)
    from campaign_cargo import cargo_manifest
    manifest = cargo_manifest(beat, fail)
    if beat["type"] == "boss":
        mounted = [(index, phase["mount"]) for index, phase in enumerate(beat["params"]["phases"]) if "mount" in phase]
        if not mounted:
            return None
        if [index for index, _ in mounted] != list(range(len(mounted))):
            fail(where, "only a boss's opening phases may be mounted")
        params, until_phase = mounted[0][1], len(mounted)
    else:
        params, until_phase = beat["params"], 0
    horse = params["horse"]
    gaits = params.get("gaits") or ["walk", "trot"]
    for gait in gaits:
        if gait not in GAITS:
            fail(where, f"gait {gait!r}")
    weapons = [int(weapon) for weapon in params.get("weapons") or []]
    if set(weapons) - {0, 18, 19}:
        fail(where, f"mounted weapons {weapons} outside the katana, yumi and yari")
    arcs = {weapon: list(ARCS[weapon]) for weapon in weapons}
    for weapon, arc in (beat["ext"].get("arcs_deg") or {}).items():
        if int(weapon) in arcs:
            arcs[int(weapon)] = [int(arc[0]), int(arc[1])]
    fear = params.get("fear")
    tack = []
    tack_up = beat["ext"].get("tack_up")
    if tack_up:
        if tack_up.get("mount_side") != "right":
            fail(where, "a period rider mounts from the horse's right (bible §4.5, chapter-01 §6.3)")
        for point in tack_up["interact_points"]:
            tack.append({"id": point["id"], "part": point["part"], "refusals": int(point.get("refusals", 0)),
                         "gift": point.get("unlock_item")})
    caps = []
    for zone in beat["ext"].get("gait_zones") or []:
        caps.append({"from_cm": _i(zone["from_m"] * 100), "to_cm": _i(zone["to_m"] * 100), "gait": zone["gait"]})
    forced = [{"volume": entry["volume"], "gait": entry["gait"]}
              for entry in beat["ext"].get("forced_gait_volumes") or []]
    spook = (beat["ext"].get("scripted_spook") or {}).get("volume")
    pack = []
    convoy = params.get("convoy") or {}
    for index, npc in enumerate(convoy.get("npcs") or []):
        pack.append({"id": npc, "follow": "convoy", "speed_cm_s": int(convoy.get("speed_cm_s", 250)),
                     "spacing_cm": int(convoy.get("spacing_cm", 450)), "hp": int(convoy.get("hp", 400))})
    cargo = params.get("cargo") or {}
    if cargo.get("carrier") == "pack_horse":
        pack.append({"id": "pack_horse_cargo", "follow": "lead", "speed_cm_s": 0, "spacing_cm": 300, "hp": 0})
    return {
        "horse": horse, "coat": HORSE_COATS[horse], "mounted": not tack and "mount" not in beat["unlocks"]["mechanics"],
        "tack": tack, "gaits": gaits, "speeds_cm_s": _gait_speeds(beat),
        "stamina": _stamina(params.get("horse_stamina"), fail, where),
        "fear": {"radius_cm": int(fear["spook_radius_cm"]), "recover_ms": _i(fear["recover_s"] * 1000)} if fear else None,
        "spooks": [spook] if spook else [], "gait_caps": caps, "forced": forced,
        "weapons": weapons, "arcs": {str(weapon): arc for weapon, arc in sorted(arcs.items())},
        "dismount": bool(params.get("dismount_allowed", until_phase > 0)), "auto_steer": ride,
        "spook_dismount": dismount_on_spook,
        "until_phase": until_phase, "pack": pack, "cargo": manifest,
    }


def ride_mount(beat, fail):
    """A ride's horse, as the chapter file carries it (for the importer's self-test)."""
    return _mount(beat, True, fail)


def _clear_of(point, others, radius):
    return all(_dist(point, other) >= radius for other in others)


class Allocator:
    """Distinct work spots for one beat, spread from where the last beat stood."""

    def __init__(self, spots, avoid):
        self.spots = [spot for spot in spots if _clear_of(spot, avoid, SITE_CLEAR)]
        self.used = set()

    def take(self, start, key=None):
        order = sorted(range(len(self.spots)), key=key) if key else \
            [(start + offset) % len(self.spots) for offset in range(len(self.spots))]
        for index in order:
            if index not in self.used:
                self.used.add(index)
                return self.spots[index]
        return None


def derive_space(chapter, beats, places, collectibles, triggers, layout, fail):
    """The chapter's space; also fills each escort's path_cm from its route."""
    prefix = chapter["prefix"]
    chapter_map = chapter["map"]
    used = []
    for beat in beats:
        if beat["place"] not in used:
            used.append(beat["place"])
    for item in collectibles:
        if item["place"] not in used:
            used.append(item["place"])
    hub_places = [place for place in used if is_hub(places[place], chapter_map)]
    if len(hub_places) > 1:
        fail(prefix, f"two places claim arena {chapter_map}: {hub_places}")
    hub = hub_places[0] if hub_places else None
    zones, zone_of = [], {}
    x = ZONE_ROW_X
    hosts_boss = {beat["place"] for beat in beats if beat["type"] == "boss"}
    routed = [beat for beat in beats if beat["type"] == "horseback_ride" or
              (beat["type"] == "production_task" and beat["params"]["task"] == "escort")]
    for place_id in used:
        if place_id == hub:
            continue
        # A place only a route passes through needs no zone.
        if all(beat in routed for beat in beats if beat["place"] == place_id) and \
                not any(item["place"] == place_id for item in collectibles):
            continue
        form = place_form(place_id)
        width, height, wall = FORMS[form]
        zone_gap = ZONE_GAP
        if prefix == "ch01" and place_id == "pl_issoseki_wood":
            width, height = 11000, 8500
        if prefix == "ch07" and place_id == "pl_hull_ridge":
            width, height = 18000, 2400
        if prefix == "ch07" and place_id == "pl_hangar":
            width, height = 8000, 4500
        if prefix == "ch06" and place_id == "pl_press_hall":
            # Extend into the existing gap, preserving every later zone and
            # marker, including the accepted flood encounter.
            zone_gap -= 4200 - width
            width, height, wall = 4200, 2400, 900
        if prefix == "ch06" and place_id == "pl_relay_room":
            zone_gap += width - 2000
            width, height, wall = 2000, 1000, 800
        if prefix == "ch06" and place_id == "pl_uguisu_hall":
            # Use the existing gap so later validated zones do not move.
            zone_gap -= 5000 - width
            width, height, wall = 5000, 4470, 500
        if prefix == "ch06" and place_id == "pl_archive":
            zone_gap += width - 2600
            width, height, wall = 2600, 1800, 600
        if place_id in hosts_boss:
            width, height = max(width, BOSS_SIZE[0]), max(height, BOSS_SIZE[1])
        zone_x = x - 400 if prefix == "ch06" and place_id == "pl_uguisu_hall" else x
        rect = (zone_x, -height // 2, zone_x + width, height // 2)
        if prefix == "ch06" and place_id == "pl_uguisu_hall":
            # Extend south for the two quiet tatami rooms, keeping the garden
            # origin, registry desks and every later place at their old coordinates.
            rect = (zone_x, -2635, zone_x + width, 1835)
        zone = Zone(place_id, place_id, place_style(places[place_id], chapter_map), form, rect, wall)
        zone_of[place_id] = len(zones)
        zones.append(zone)
        x += width + zone_gap
    route_of = {}
    for number, beat in enumerate(routed):
        length = _authored_spline_length(beat, layout) or _ride_length(beat)
        y = ROUTE_ROW_Y - number * ROUTE_ROW_STEP
        polyline = _route_polyline((ZONE_ROW_X + ROUTE_PAD, y), length)
        end_x = max(point[0] for point in polyline)
        rect = (ZONE_ROW_X, y - ROUTE_HALF_WIDTH, end_x + ROUTE_PAD, y + ROUTE_HALF_WIDTH)
        zone = Zone(f"route:{beat['id']}", beat["place"], place_style(places[beat["place"]], chapter_map),
                    "route", rect, ROUTE_WALL)
        zone.route = polyline
        route_of[beat["id"]] = len(zones)
        zones.append(zone)

    # Production sites: at their restoring beat's zone (the far column of a
    # zone, the end of a route, the arena's own site in the hub).
    site_at = {}
    for beat in beats:
        if beat["site"] is not None:
            site_at[beat["site"]] = beat
    by_zone = {}
    for site, beat in sorted(site_at.items()):
        index = route_of.get(beat["id"], zone_of.get(beat["place"], -1))
        by_zone.setdefault(index, []).append(site)
    sites = [None, None, None]
    for index, members in by_zone.items():
        if index == -1:
            for site in members:
                sites[site] = list(ARENA_SITES[site])
            continue
        zone = zones[index]
        if zone.form == "route":
            for offset, site in enumerate(members):
                end = zone.route[-1]
                sites[site] = [end[0] - 300 - offset * 700, end[1] + 800]
            continue
        for site, fy in zip(members, SITE_Y[len(members)]):
            sites[site] = list(_frac(zone.rect, SITE_X, fy))
            zone.sites.append(site)
    if any(site is None for site in sites):
        fail(prefix, f"production sites without a place: {sites}")

    # Cover and props: every zone gets its style's dressing; zones and routes
    # where a fight happens (or guards stand watch) get cover by the walls.
    fights = {"combat_wave", "boss", "duel", "stealth_zone"}
    for index, zone in enumerate(zones):
        hosted = [beat for beat in beats if route_of.get(beat["id"], zone_of.get(beat["place"])) == index]
        combat = any(beat["type"] in fights or beat["task"]["waves"] or beat["task"]["guards"] for beat in hosted)
        if zone.form == "route":
            _dress_route(zone, combat)
        else:
            _dress_zone(zone, combat, [tuple(sites[site]) for site in zone.sites])

    records = []
    order_in_zone = {}
    hub_cover = [box(((x0 + x1) // 2, (y0 + y1) // 2), (x1 - x0, y1 - y0), 0)
                 for x0, y0, x1, y1 in arena_blockers(chapter_map)] if hub else []
    for position, beat in enumerate(beats):
        index = route_of.get(beat["id"], zone_of.get(beat["place"], -1))
        records.append(_beat_space(beat, index, zones, sites, triggers, order_in_zone, hub_cover, fail))
        if beat["id"] in route_of and beat["task"]["goal"] == "escort":
            route = zones[index].route
            beat["task"]["path_cm"] = _i(polyline_length(route)) - 2 * ESCORT_MARGIN
    first = records[0]
    pickups = []
    nook_use = {}
    rewards = {item for beat in beats if beat["type"] == "explore_optional"
               for item in beat["params"].get("rewards") or []}
    for item in collectibles:
        if item["id"] in rewards:
            continue
        index = zone_of.get(item["place"], -1)
        if item["place"] != hub and item["place"] not in zone_of:
            # A place the hero only passes through: beside the road, near the start.
            ride = next(beat for beat in routed if beat["place"] == item["place"])
            index = route_of[ride["id"]]
            taken = nook_use.get(index, 0)
            nook_use[index] = taken + 1
            at = point_along(zones[index].route, 900 + 1500 * taken)
            middle = (zones[index].rect[1] + zones[index].rect[3]) // 2
            pickups.append({"collectible": item["id"], "zone": index, "at": [at[0], middle + 800]})
            continue
        taken = nook_use.get(index, 0)
        nook_use[index] = taken + 1
        if index == -1:
            if taken >= len(ARENA_NOOKS):
                fail(item["id"], "the hub has no nook left for this collectible")
            at = ARENA_NOOKS[taken]
        else:
            if taken >= len(NOOK_AT):
                fail(item["id"], f"zone {item['place']} has no nook left")
            at = _frac(zones[index].rect, *NOOK_AT[taken])
        pickups.append({"collectible": item["id"], "zone": index, "at": list(at)})
    from campaign_bridge import place_bridge
    place_bridge(beats, records, [zone.record() for zone in zones], fail)
    from campaign_helm import place_helm
    place_helm(beats, records, [zone.record() for zone in zones], fail)
    place_wind(beats, records, zones, fail)
    place_lift(beats, records, fail)
    from campaign_canisters import place_canisters
    place_canisters(beats, records, fail)
    place_flood(beats, records, zones, fail)
    from campaign_horse_treatment import place_horse_treatment
    place_horse_treatment(beats, records, fail)
    from campaign_pods import place_pods
    place_pods(beats, records, layout, fail)
    from campaign_horse_shell import place_horse_shell
    place_horse_shell(beats, records, fail)
    from campaign_horse_withdrawal import place_horse_withdrawal
    place_horse_withdrawal(beats, records, layout, fail)
    from campaign_foundry_defense import place_foundry_defense
    place_foundry_defense(beats, records, fail)
    from campaign_molten import place_molten
    place_molten(beats, records, fail)
    place_spire(beats, records, zones, fail)
    place_summit(beats, records, zones, fail)
    place_climb(beats, records, zones, fail)
    place_moat(beats, records, zones, pickups, fail)
    from campaign_press import place_press_hall
    place_press_hall(beats, records, zones, pickups, fail)
    from campaign_relay import place_relay
    place_relay(beats, records, zones, pickups, fail)
    from campaign_archive import place_archive
    place_archive(beats, records, zones, fail)
    from campaign_palace import place_palace
    place_palace(beats, records, zones, sites, pickups, fail)
    from campaign_ledger import place_ledger
    place_ledger(beats, records, zones, pickups, fail)
    for beat, record in zip(beats, records):
        if beat["id"] == "ch06.b13":
            # Chapter 6 §3 L8 puts the bulkhead lever beside the freight-lift
            # entry. This is its functional placement in the current hall
            # blockout, not a claim to the unbuilt circular chamber/lift art.
            if beat["place"] != "pl_vault_core" or record["entry"][2] != 0:
                fail(beat["id"], "bulkhead lever needs the vault's entry frame")
            record["bulkhead"] = [record["entry"][0], record["entry"][1] + 180]
    result = {
        "frame": "Unreal world cm; origin at the arena centre; per-beat height_cm overrides floor z 0",
        "hub": chapter_map if hub else None,
        "hub_place": hub,
        "start": list(first["entry"]),
        "zones": [zone.record() for zone in zones],
        "sites": sites,
        "beats": records,
        "pickups": pickups,
    }
    connect_wood(result, beats, layout)
    return result


ESCORT_MARGIN = 500


def _dress_zone(zone, combat, site_points):
    """Cover by the walls where a fight happens, lantern posts in the corners,
    and the style's buildings and trees as a backdrop outside the walls, so no
    visual-only prop ever stands over a work spot."""
    if zone.place == 'pl_relay_room':
        return  # The authored runtime room supplies its own cover and gallery.
    rect = zone.rect
    if combat:
        for fx in COVER_X:
            for fy in COVER_Y:
                center = _frac(rect, fx, fy)
                if _clear_of(center, site_points, SITE_CLEAR):
                    zone.cover.append(box(center, COVER_SIZE[:2], COVER_SIZE[2]))
    for fx, fy in ((0.04, 0.06), (0.04, 0.94), (0.97, 0.06), (0.97, 0.94)):
        zone.props.append({"mesh": "SM_Edo_LanternPost", "at": list(_frac(rect, fx, fy)) + [0]})
    if zone.form == "hall":
        return
    x0, y0, x1, y1 = rect
    if zone.place == "pl_higashi_torii":
        zone.props.append({"mesh": "torii", "at": [x1 - 900, 0, 0]})
    if zone.style == "estate":
        zone.props.append({"mesh": "SM_Nyaagyu_ProvisionKura", "at": [_i(x0 + (x1 - x0) * 0.3), y0 - 700, 0]})
        zone.props.append({"mesh": "SM_Nyaagyu_EstateDojo", "at": [_i(x0 + (x1 - x0) * 0.68), y1 + 750, 180]})
        x = x0 + 600
        while x < x1:
            zone.props.append({"mesh": "pine", "at": [x, y1 + 300, (x * 7) % 360]})
            zone.props.append({"mesh": "tree", "at": [x + 700, y0 - 300, (x * 11) % 360]})
            x += 1800
        return
    kind = "building" if zone.style == "ward" else "building_hightech"
    x = x0 + 500
    while x + 650 < x1:
        for side, y in ((-1, y0 - 450), (1, y1 + 450)):
            zone.props.append({"mesh": kind, "at": [x + 325, y, 0 if side < 0 else 180]})
        x += 1100


def _dress_route(zone, combat):
    """Lantern posts by the road, cover by the walls where a fight happens,
    and the style's trees or buildings beyond the walls."""
    route = zone.route
    length = polyline_length(route)
    x0, y0, x1, y1 = zone.rect
    chainage, side = 2000.0, 1
    while chainage < length - 1000:
        at = point_along(route, chainage)
        zone.props.append({"mesh": "SM_Edo_LanternPost", "at": [at[0], _i(at[1] + side * 520), 0]})
        if combat:
            cover = (at[0] + 1200, y0 + 420 if side > 0 else y1 - 420)
            zone.cover.append(box(cover, COVER_SIZE[:2], COVER_SIZE[2]))
        chainage += 4000
        side = -side
    x = x0 + 800
    while x < x1:
        if zone.style == "estate":
            zone.props.append({"mesh": "pine", "at": [x, y0 - 350, (x * 7) % 360]})
            zone.props.append({"mesh": "tree", "at": [x + 1500, y1 + 350, (x * 11) % 360]})
            x += 3000
        else:
            kind = "building" if zone.style == "ward" else "building_hightech"
            zone.props.append({"mesh": kind, "at": [x, y0 - 450, 0]})
            zone.props.append({"mesh": kind, "at": [x + 550, y1 + 450, 180]})
            x += 2200


def _zone_spots(zone):
    return [_frac(zone.rect, fx, fy) for fx in SPOT_X for fy in SPOT_Y]


def _beat_space(beat, index, zones, sites, triggers, order_in_zone, hub_cover, fail):
    task = beat["task"]
    record = {"beat": beat["id"], "zone": index}
    count = order_in_zone.get(index, 0)
    order_in_zone[index] = count + 1
    zone = zones[index] if index >= 0 else None
    volumes = _referenced_volumes(beat, triggers)
    site = sites[beat["site"]] if beat["site"] is not None else None
    if zone is not None and zone.form == "route":
        route = zone.route
        length = polyline_length(route)
        start = point_along(route, 300)
        record["entry"] = [start[0], start[1], 0]
        record["anchor"] = list(route[-1])
        exit_center = point_along(route, length - 300)
        placed = []
        for number, name in enumerate(volumes):
            event = f"volume_enter:{name}"
            if event in (task["exit_event"], task["closing_event"]):
                center, size = exit_center, (1000, 2 * ROUTE_HALF_WIDTH)
            else:
                chainage = _volume_chainage(beat, name, number, len(volumes), length)
                center, size = point_along(route, chainage), (800, 2 * ROUTE_HALF_WIDTH)
            placed.append({"event": event, "center": list(center), "size": list(size)})
        record["volumes"] = placed
        record["exit"] = {"center": list(exit_center), "size": [1000, 2 * ROUTE_HALF_WIDTH]}
        spawns = []
        chainage, side = 2500.0, 1
        middle = (zone.rect[1] + zone.rect[3]) // 2
        while chainage < length - 500:
            at = point_along(route, chainage)
            spawns.append([at[0], middle + side * (ROUTE_HALF_WIDTH - 250)])
            chainage += 2500
            side = -side
        record["spawns"] = spawns
        record["dropoffs"] = [list(point_along(route, length * (number + 1) / (len(task["dropoffs"]) + 1)))
                              for number in range(len(task["dropoffs"]))]
        if site is not None:
            record["anchor"] = list(route[-1])
        record["route"] = {"zone": index, "margin_cm": ESCORT_MARGIN}
        allocator = Allocator([], [])
    else:
        rect = zone.rect if zone else ARENA_RECT
        entry = zone.entry if zone else ARENA_ENTRY
        record["entry"] = list(entry)
        spots = _zone_spots(zone) if zone else list(ARENA_SPOTS)
        avoid = [tuple(point) for point in sites if point and (not site or tuple(point) != tuple(site))]
        allocator = Allocator(spots, avoid if zone else [])
        start = (count * 5) % len(allocator.spots) if zone else (beat_index(beat) * 3) % len(allocator.spots)
        anchor = tuple(site) if site else allocator.take(start)
        if task["maai"]:
            # The restored training site has a raised collision base, core
            # and sword racks. The mentor's measured steps belong on the
            # clear dojo floor, independently of that restoration marker.
            anchor = ((rect[0] + rect[2]) // 2, (rect[1] + rect[3]) // 2)
        record["anchor"] = list(anchor)
        west = lambda i: allocator.spots[i][0]
        east = lambda i: -allocator.spots[i][0]
        near = lambda i: _dist(allocator.spots[i], anchor)
        objectives = [allocator.take(start, near) for _ in task["objectives"]]
        pickups = [allocator.take(start, west) for _ in task["pickups"]]
        dropoffs = [allocator.take(start, east) for _ in task["dropoffs"]]
        targets = [allocator.take(start, near) for _ in task["targets"]]
        if any(point is None for point in objectives + pickups + dropoffs + targets):
            fail(beat["id"], "its place has too few clear spots for its points")
        record.update(objectives=[list(point) for point in objectives], pickups=[list(point) for point in pickups],
                      dropoffs=[list(point) for point in dropoffs], targets=[list(point) for point in targets])
        if task["steps"]:
            stations = beat["params"]["manufacture"].get("stations") or ["station"]
            step_station = [step.get("station") for step in beat["params"]["manufacture"]["steps"]]
            count_stations = len(stations)
            base = (anchor[0] - (400 if site else 0), anchor[1])
            record["stations"] = [[_i(base[0]), _i(base[1] + (number - (count_stations - 1) / 2) * STATION_STEP)]
                                  for number in range(count_stations)]
            record["step_stations"] = [stations.index(name) if name in stations else min(number, count_stations - 1)
                                       for number, name in enumerate(step_station)]
        x0, y0, x1, y1 = rect
        middle = (y0 + y1) // 2
        placed = []
        for number, name in enumerate(volumes):
            event = f"volume_enter:{name}"
            if event in (task["exit_event"], task["closing_event"]):
                center, size = ARENA_EXIT if zone is None else ((x1 - 400, middle), (500, _i((y1 - y0) * 0.8)))
            else:
                share = 0.3 + 0.5 * (number + 1) / (len(volumes) + 1)
                center = (_i(-1800 + 3600 * (share - 0.3) / 0.5), 0) if zone is None else \
                    (_i(x0 + (x1 - x0) * share), middle)
                size = (400, 1100) if zone is None else (400, _i((y1 - y0) * 0.8))
            placed.append({"event": event, "center": list(center), "size": list(size)})
        record["volumes"] = placed
        exit_center, exit_size = ARENA_EXIT if zone is None else ((x1 - 400, middle), (500, _i((y1 - y0) * 0.8)))
        record["exit"] = {"center": list(exit_center), "size": list(exit_size)}
        closing = next((volume["center"] for volume in placed if volume["event"] == task["closing_event"]), None)
        if task["anchor_after_lines"] and closing is None:
            closing = list(exit_center)
        record["closing"] = closing
        record["spawns"] = [list(point) for point in ARENA_SPAWNS] if zone is None else \
            [list(_frac(rect, fx, fy)) for fx, fy in SPAWN_AT]
        record["patrols"] = [[list(point) for point in loop] for loop in ARENA_PATROLS] if zone is None else \
            [[list(_frac(rect, fx, fy)) for fx, fy in loop] for loop in PATROL_AT]
        if beat["task"]["goal"] == "cache":
            record["cache"] = list(ARENA_CACHES[beat_index(beat) % len(ARENA_CACHES)] if zone is None else
                                   _frac(rect, *CACHE_AT))
        if beat["type"] == "cinematic":
            if zone is None:
                record["camera"] = list(ARENA_CAMERA)
            else:
                focus = tuple(site) if site else _frac(rect, 0.6, 0.5)
                record["camera"] = [x0 + 350, _i(y0 + (y1 - y0) * 0.22), 480, x0 + 900, _i(y0 + (y1 - y0) * 0.34),
                                    420, focus[0], focus[1], 180]
    if beat["id"] in ("ch08.b17", "ch08.b18"):
        # +X follows the approach north, +Y is east. The board is 3 m
        # south of the west pillar (235 cm off the shrine axis).
        gate_x = rect[2] - 900
        record["anchor"] = [gate_x - 100, 500]  # Toranosuke and the sword
        if beat["id"] == "ch08.b17":
            record["closing"] = [gate_x - 300, -235]  # freestanding name board
            record["volumes"] = [{"event": "volume_enter:vol_torii",
                                  "center": [gate_x - 500, 0], "size": [1000, 2000]}]
    record.setdefault("objectives", [])
    record.setdefault("pickups", [])
    record.setdefault("targets", [])
    record.setdefault("stations", [])
    record.setdefault("step_stations", [])
    record.setdefault("closing", None)
    record.setdefault("patrols", [])
    record.setdefault("cache", None)
    record.setdefault("camera", None)
    record.setdefault("route", None)
    record.setdefault("dropoffs", [])
    record["recovery"] = None
    record["carry_gate"] = list(record["pickups"][0]) if task["carry_gate"] else None
    if task["carry_gate"]:
        for volume in record["volumes"]:
            if volume["event"] == "volume_enter:vol_kura_sw_door":
                volume["center"] = list(record["carry_gate"])
                volume["size"] = [400, 400]
    if task["recovery"]:
        if zone is None or zone.form == "route":
            fail(beat["id"], "a dry well needs its own clear courtyard")
        # Reserve an unused clear work spot: the 340 cm opening and its
        # east-side rope approach fit within the same allocator clearance.
        point = allocator.take(start)
        if point is None:
            fail(beat["id"], "no clear spot for the recovery well")
        record["recovery"] = list(point)
    record["kit"] = _kit(beat)
    ride = beat["type"] == "horseback_ride"
    record["mount"] = _mount(beat, ride, fail) if ride or beat["type"] == "boss" else None
    if record["mount"]:
        at = record["entry"]
        record["mount"]["at"] = [at[0] + (200 if zone and zone.form == "route" else 300), at[1], 0]
    record["fieldcraft"] = derive_fieldcraft(beat, record, zone, zone.rect if zone else ARENA_RECT,
                                             zone.cover if zone else hub_cover, allocator, fail)
    return record


def beat_index(beat):
    return int(beat["id"].rsplit(".b", 1)[1]) - 1


def _volume_chainage(beat, name, number, count, length):
    ext = beat["ext"]
    # A ride's road objectives (ch08.b02's three seal stakes) stand evenly
    # between the barricade groups: at 23%, 50% and 77% of the road.
    stakes = [row["volume"] for row in beat["params"].get("objectives") or [] if row.get("volume")] \
        if beat["type"] == "horseback_ride" else []
    if name in stakes:
        return length * (0.1 + 0.8 * (stakes.index(name) + 0.5) / len(stakes))
    spook = ext.get("scripted_spook") or {}
    if spook.get("volume") == name and spook.get("at_m") is not None:
        return min(length - 600, _i(spook["at_m"] * 100))
    return length * (0.15 + 0.7 * (number + 1) / (count + 1))


def _kit(beat):
    """What the world builds for the beat's task, by kind."""
    params = beat["params"]
    kit = {"work": None, "item": None, "pickups": [], "dropoffs": [], "targets": [], "party": []}
    if beat["type"] == "horseback_ride" and params.get("mode") == "cargo":
        kit.update(work="cargo", item="bale", dropoffs=["drying_stand"] * len(params["cargo"]["dropoffs"]))
        return kit
    if beat["type"] != "production_task":
        return kit
    name = params["task"]
    block = params[name]
    if name == "crank":
        kit["work"] = _crank_work(block["actor"])
    elif name == "hold":
        kit["work"] = "hold"
    elif name == "manufacture":
        kit["work"] = "stations"
    elif name == "carry":
        kit.update(work="carry", item=_item_kind(block["item"]),
                   pickups=[_point_kind(point) for point in block["pickups"]],
                   dropoffs=[_point_kind(point) for point in block["dropoffs"]])
    elif name == "defend":
        kit.update(work="defend", targets=[_target_kind(target["actor"]) for target in block["targets"]])
    elif name == "escort":
        kit.update(work="escort", party=_party(block["npcs"]))
    return kit
