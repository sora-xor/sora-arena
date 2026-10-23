"""Chapter-six corner climb: authored rules with provisional swept path geometry.

Points are local feet positions in whole centimetres, including the grounded
start. Fourteen corner moves and eight extrusion moves remain distinct. The
runtime owns the final mount, crawl aperture, sentry and physical collision.
"""
import math


CORNER_HEIGHTS = (0, 110, 220, 330, 440, 550, 680, 820, 960, 1100, 1200, 1300, 1400, 1500, 1600)
EXTRUSION_HEIGHTS = (0, 200, 400, 600, 800, 1000, 1200, 1400, 1600)
TRAVERSAL = {
    "mode": "climb", "route": "spl_climb_corner", "holds": 14,
    "alt_route": "spl_climb_extrusion", "alt_holds": 8,
    "rest_ledges": ["vol_rest_ledge_1", "vol_rest_ledge_2"], "grip_max": 100,
    "grip_per_move": 6, "grip_regen_on_ledge_per_s": 25,
    "fall_damage": {"over_cm": 400, "damage": 30, "lethal_over_cm": 800},
}


def exact(actual, expected):
    """JSON equality that does not mistake bools or floats for integer fields."""
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(exact(actual[k], v) for k, v in expected.items())
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(exact(a, b) for a, b in zip(actual, expected))
    return actual == expected


def route_points(heights, y):
    def face(z):
        return min(z, 600) / math.tan(math.radians(60)) + max(0, z - 600) / math.tan(math.radians(80))
    points = [[round(face(z)) - 70, y, z] for z in heights]
    if y == 70:
        # Provisional swept path: approach each solid rest shelf outside its
        # 130 cm lip, raise there, then move inward at the authored rest height.
        # Moving the preceding hold inward would put a standing capsule into
        # the shelf underside before the runtime can begin that transition.
        for hold in (4, 8):
            points[hold][0] = points[hold + 1][0] - 210
    return points


def contract(origin):
    return {
        "origin": list(origin), "height_cm": 1600,
        "corner": {"id": "spl_climb_corner", "points_cm": route_points(CORNER_HEIGHTS, 70),
                   "rest_holds": [5, 9], "step_ms": 1800, "exposed": False},
        "extrusion": {"id": "spl_climb_extrusion", "points_cm": route_points(EXTRUSION_HEIGHTS, -1000),
                      "rest_holds": [], "step_ms": 1800, "exposed": True},
        "lookdown": {"period_ms": 20000, "hold_ms": 4000, "guard_index": 0},
        "crawl": {"floor_cm": 1650, "height_cm": 60, "half_width_cm": 60,
                  "entry_x_cm": 1100, "exit_x_cm": 1400},
        "provisional_geometry": True,
    }


def authored_valid(beat):
    guard = {"id": "g_yagura_sentry", "type": "enforcer_rifle", "patrol": "spl_yagura_parapet",
             "lookdown": {"at": "ishiotoshi_1", "every_s": 20, "hold_s": 4},
             "sight": {"cone_deg": 60, "range_cm": 1800, "dark_range_cm": 900}, "hearing_cm": 1000}
    senses = {"type": "enforcer_rifle", "post": False, "scan_deg": 0, "scan_ms": 0, "turn_ms": 0,
              "sight_cm": 1800, "dark_sight_cm": 900, "view_deg": 60, "hearing_cm": 1000,
              "suspicion_permille": 0}
    return (exact(beat["ext"]["traversal"], TRAVERSAL) and beat["ext"]["exit"] == "vol_climb_top"
            and exact(beat["params"]["guards"], [guard]) and exact(beat["task"]["guards"], [senses])
            and beat["task"]["goal"] == "exit" and beat["task"]["on_detected"] == "combat"
            and exact(beat["fail"], [{"on": "player_died", "to": "checkpoint"}]))


def generic_face(origin):
    return {"at": list(origin), "yaw": 180, "width_cm": 5400, "depth_cm": 650,
            "height_cm": 1600, "holds": 14, "grip_per_hold": 6, "regen_per_s": 25,
            "ledges": [5, 9], "ledge_events": ["volume_enter:vol_rest_ledge_1", "volume_enter:vol_rest_ledge_2"],
            "top_event": "volume_enter:vol_climb_top", "hurt_cm": 400, "hurt_hp": 30, "lethal_cm": 800}


def place_climb(beats, records, zones, fail):
    if not any(b["id"] == "ch06.b03" for b in beats):
        return
    from campaign_space import Zone
    beat = next(b for b in beats if b["id"] == "ch06.b03")
    if not authored_valid(beat):
        fail(beat["id"], "climb requires authored 14/8 routes, grip/fall rules and 20s/4s sentry")
    record = next(r for r in records if r["beat"] == beat["id"])
    x = max(z.rect[2] for z in zones) + 20000
    zone = Zone("ch06_corner_climb", beat["place"], "citadel", "yard", (x - 1000, -4400, x + 2200, 1000), 360)
    zone.entry = (x - 400, 70, 0)
    record["zone"] = len(zones)
    zones.append(zone)
    record.update(entry=list(zone.entry), anchor=[x + 1700, 0], height_cm=0,
                  exit={"center": [x + 1700, 0], "size": [300, 300], "floor_cm": 1650},
                  spawns=[[x + 650, -3800]], patrols=[], climb_routes=contract([x, 0]),
                  volumes=[{"event": "volume_enter:vol_climb_start", "center": [x - 250, 70], "size": [400, 400]}])
    craft = record["fieldcraft"]
    craft["climb"] = generic_face([x, 0])
    for ally in craft["allies"]:
        ally["at"] = list(zone.entry[:2])
    for lamp in craft["lamps"]:
        lamp["at"] = [x + 350, -1000]


def climb_valid(chapter):
    """Reject absent, misplaced, mistyped, disconnected or altered contracts."""
    try:
        beats, records, zones = chapter["beats"], chapter["space"]["beats"], chapter["space"]["zones"]
        if [b["id"] for b in beats] != [r["beat"] for r in records]:
            return False
        for beat, record in zip(beats, records):
            if beat["id"] != "ch06.b03":
                if "climb_routes" in record:
                    return False
                continue
            if not authored_valid(beat):
                return False
            climb = record["climb_routes"]
            origin = climb["origin"]
            if type(origin) is not list or len(origin) != 2 or any(type(v) is not int for v in origin):
                return False
            x, y = origin
            if y != 0 or not -(2**31) + 1000 <= x <= 2**31 - 1 - 2200 or not exact(climb, contract(origin)):
                return False
            index = record["zone"]
            if type(index) is not int or not 0 <= index < len(zones):
                return False
            zone = zones[index]
            expected = {"entry": [x - 400, 70, 0], "anchor": [x + 1700, 0], "height_cm": 0,
                        "exit": {"center": [x + 1700, 0], "size": [300, 300], "floor_cm": 1650},
                        "spawns": [[x + 650, -3800]], "patrols": [],
                        "volumes": [{"event": "volume_enter:vol_climb_start", "center": [x - 250, 70], "size": [400, 400]}]}
            if any(not exact(record[k], v) for k, v in expected.items()):
                return False
            if (zone["id"] != "ch06_corner_climb" or zone["place"] != "pl_ishigaki" or
                    not exact(zone["rect"], [x - 1000, -4400, x + 2200, 1000]) or
                    not exact(zone["entry"], expected["entry"]) or zone["cover"] or zone["props"] or zone["route"]):
                return False
            craft = record["fieldcraft"]
            if not exact(craft["climb"], generic_face(origin)) or len(craft["allies"]) != 1 or len(craft["lamps"]) != 1:
                return False
            ally, lamp = craft["allies"][0], craft["lamps"][0]
            if (ally["id"] != "npc_kohagi" or ally["detectable"] is not False or ally["downable"] is not False or
                    not exact(ally["at"], expected["entry"][:2]) or lamp["id"] != "l_extrusion_strip" or
                    lamp["snuff"] != "none" or not exact(lamp["at"], [x + 350, -1000])):
                return False
        return True
    except (KeyError, TypeError, IndexError, ValueError):
        return False
