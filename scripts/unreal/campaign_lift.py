"""The authored spire lift and its elevated arrival gallery, in world cm."""


def place_lift(beats, records, fail):
    for record in records:
        record["height_cm"] = 0
        record["lift"] = None
    by_id = {beat["id"]: beat for beat in beats}
    if "ch08.b11" not in by_id:
        return
    beat = by_id["ch08.b11"]
    raw = beat["params"]["crank"]["moving_platform"]
    expected_waves = [
        {"trigger": "progress_at:0.25", "enemies": [{"type": "drone", "count": 3, "spawn": "sp_lift_gantry_5575cm", "behavior": "cut_rope"}]},
        {"trigger": "progress_at:0.5", "enemies": [{"type": "enforcer_rifle", "count": 3, "spawn": "sp_lift_gantry_8450cm"}]},
        {"trigger": "progress_at:0.75", "enemies": [
            {"type": "shield_enforcer", "count": 1, "spawn": "sp_lift_gantry_11325cm", "behavior": "board_platform"},
            {"type": "blade_retainer", "count": 2, "spawn": "sp_lift_gantry_11325cm", "behavior": "board_platform"}]}]
    if beat["params"]["waves"] != expected_waves:
        fail(beat["id"], "lift waves require the physical gantry and behavior contract")
    expected = {"actor": "freight_lift_platform", "size_cm": [600, 600],
                "travel_cm": 11500, "from": "L4_27m", "to": "hall_142m"}
    if raw != expected:
        fail(beat["id"], "physical lift contract differs from authored platform")
    lift = next(row for row in records if row["beat"] == beat["id"])
    gallery = next(row for row in records if row["beat"] == "ch08.b12")
    x, y = lift["anchor"]
    lift["height_cm"] = 2700
    # The XY spawn footprint is shared by the three elevated gantries;
    # each wave uses its own height, rather than the beat floor's height.
    lift["spawns"] = [[x + 650, y + offset] for offset in (-150, 0, 150)]
    lift["patrols"] = []
    lift["exit"] = {"center": [x - 650, y], "size": [300, 300]}
    lift["entry"] = [x - 650, y, 0]
    lift["lift"] = {"size_cm": raw["size_cm"], "bottom_cm": 2700, "top_cm": 14200,
                    "gantry_cm": [5575, 8450, 11325],
                    "gallery_rect": [x + 300, y - 2000, x + 1300, y + 2000],
                    "gallery_exit": [x + 800, y + 1800]}
    gallery["height_cm"] = 14200
    gallery["entry"] = [x + 500, y, 90]
    gallery["anchor"] = [x + 800, y]
    gallery["cache"] = [x + 800, y - 1400]
    gallery["exit"] = {"center": [x + 800, y + 1800], "size": [600, 300]}
    gallery["spawns"], gallery["patrols"] = [], []
    for volume in gallery["volumes"]:
        volume["center"] = [x + 800, y]
        volume["size"] = [1000, 4000]
