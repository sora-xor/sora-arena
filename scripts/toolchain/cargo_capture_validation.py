"""Authenticate an assisted cargo capture's observations and original sequence.

These gates do not establish visible rope/stock/HUD quality. Review the archived
original PNGs; no pixels are transformed or inferred from component getters.
"""
import math

PHASES = ("remaining-30", "remaining-20", "remaining-10", "remaining-0")
SCHEMA = "sora-arena.cargo-capture.v2"
SCOPE = ("prepared cargo checkpoint/positions/camera and frozen AI; mapped active-time unloads; "
         "paused original frames; not playthrough or art acceptance")


def number(row, key, integer=False):
    value = row.get(key)
    try:
        valid = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid or (integer and (value < 0 or value > 2**53 - 1 or value != int(value))):
        raise ValueError(f"invalid cargo observation: {key}")
    return value


def vector(value, size=3):
    if not isinstance(value, list) or len(value) != size:
        raise ValueError("invalid cargo vector")
    for part in value:
        number({"part": part}, "part")
    return value


def stock(row, done, rope=True):
    if not isinstance(row, dict):
        raise ValueError("missing actual cargo stock observation")
    remaining = 30 - 10 * done
    if (number(row, "deliveries", True) != done or number(row, "pack_quantity", True) != remaining
            or number(row, "stand_count", True) != 3):
        raise ValueError("cargo stock disagrees with accepted deliveries")
    stands = vector(row.get("stand_quantities"))
    if stands != [10 if i < done else 0 for i in range(3)]:
        raise ValueError("cargo destination quantities disagree with unique deliveries")
    for key, expected in (("objective_ja", f"麦 残り {remaining}束"),
                          ("objective_en", f"Barley: {remaining} sheaves left")):
        if not isinstance(row.get(key), str) or expected not in row[key]:
            raise ValueError("cargo objective does not expose the actual remaining quantity")
    if not rope:
        return
    if number(row, "rope_segments", True) != 12 or row.get("rope_collision") is not False:
        raise ValueError("cargo rope must have twelve visible noncolliding segments")
    for anchor, rendered in (("halter", "rendered_halter"), ("tie", "rendered_tie")):
        a, b = vector(row.get(anchor)), vector(row.get(rendered))
        if any(abs(x - y) > .01 for x, y in zip(a, b)):
            raise ValueError("cargo rendered rope endpoints differ from animated anchors")
    if math.dist(row["halter"], row["tie"]) <= .01:
        raise ValueError("cargo rope endpoints coincide")


def verify_sequence(metadata, filenames, width, height):
    if not isinstance(metadata, dict) or metadata.get("schema") != SCHEMA:
        raise ValueError("invalid cargo capture schema")
    if metadata.get("scope") != SCOPE:
        raise ValueError("cargo capture lost its explicit assisted scope")
    for key in ("passed", "prepared_checkpoint", "frozen_ai", "mapped_start_dismount", "ordinary_clock",
                "profiles_preserved", "mappings_preserved", "inputs_released", "temporary_slot_deleted"):
        if metadata.get(key) is not True:
            raise ValueError(f"cargo capture did not establish {key}")
    if vector(metadata.get("viewport"), 2) != [width, height] or (width, height) not in ((1280, 720), (1920, 1080)):
        raise ValueError("cargo viewport mismatch")
    expected_files = [phase + ".png" for phase in PHASES]
    rows = metadata.get("frames")
    if filenames != expected_files or not isinstance(rows, list) or len(rows) != 4:
        raise ValueError("cargo capture requires four unique original phases in order")
    holds, preparations = metadata.get("holds"), metadata.get("preparations")
    if not isinstance(holds, list) or len(holds) != 3 or not isinstance(preparations, list) or len(preparations) != 3:
        raise ValueError("cargo requires three ordinary holds and explicit preparations")
    previous_frame = previous_world = previous_wall = -1
    for index, (phase, row) in enumerate(zip(PHASES, rows)):
        if not isinstance(row, dict) or row.get("name") != phase or row.get("file") != expected_files[index]:
            raise ValueError("cargo phase/filename mismatch")
        for key in ("paused", "english", "hud_drawn"):
            if row.get(key) is not True:
                raise ValueError("cargo frame must observe the paused real bilingual HUD")
        if row.get("interact_held") is not False:
            raise ValueError("cargo screenshot cannot hold Interact")
        request, processed = number(row, "request_frame", True), number(row, "screenshot_processed_frame", True)
        world, wall = number(row, "world_s"), number(row, "wall_s")
        if request <= previous_frame or processed != request or world <= previous_world or wall <= previous_wall:
            raise ValueError("cargo HUD sample and original screenshot ordering disagree")
        previous_frame, previous_world, previous_wall = processed, world, wall
        if number(row, "beat", True) != (13 if index < 3 else 15) or number(row, "destination", True) != max(0, index - 1):
            raise ValueError("cargo frame comes from the wrong destination or beat")
        vector(row.get("camera"))
        if index < 3:
            if row.get("dialogue_active") is not False or number(row, "queued_lines", True) != 0:
                raise ValueError("cargo stock frame froze a live delivery dialogue")
            stock(row.get("stock"), index)
            subjects = row.get("projected_subjects")
            if not isinstance(subjects, list) or len(subjects) != 5:
                raise ValueError("cargo lacks projected horses, stand and rope endpoints")
            for subject in subjects:
                x, y = vector(subject, 2)
                if not 40 <= x <= width - 40 or not 80 <= y <= height - 100:
                    raise ValueError("cargo subject falls outside its prepared frame")
            horses, hud = row.get("horse_screen_bounds"), row.get("upper_hud_bounds")
            if not isinstance(horses, list) or len(horses) != 2 or not isinstance(hud, list) or not hud:
                raise ValueError("cargo lacks whole-horse/HUD framing observations")
            for box in hud:
                left, top, right, bottom = vector(box, 4)
                if not 0 <= left < right <= width or not 0 <= top < bottom <= height:
                    raise ValueError("invalid cargo HUD obstacle bounds")
            for box in horses:
                left, top, right, bottom = vector(box, 4)
                if not 40 <= left < right <= width - 40 or not 80 <= top < bottom <= height - 100:
                    raise ValueError("whole cargo horse is outside its prepared frame")
                if any(left < r and l < right and top < b and t < bottom for l, t, r, b in hud):
                    raise ValueError("cargo horse is obscured by an upper HUD panel")
        else:
            if row.get("notice_title_retained") is not True:
                raise ValueError("cargo zero title is not retained in the drawn notice layout")
            if "stock" in row or number(row, "pack_count", True) != 0 or number(row, "stand_count", True) != 0:
                raise ValueError("final cargo frame must acknowledge natural prop teardown")
            for key, text in (("notice_ja", "麦 残り 0束"), ("notice_en", "Barley: 0 sheaves left")):
                if not isinstance(row.get(key), str) or text not in row[key]:
                    raise ValueError("cargo final zero Registry feedback is absent")
            if number(row, "notice_count", True) != 1 or not 0 < number(row, "notice_remaining_s") <= 7:
                raise ValueError("cargo final feedback has expired or extended lifetime")
    for index, (hold, prep) in enumerate(zip(holds, preparations)):
        if not isinstance(hold, dict) or not isinstance(prep, dict):
            raise ValueError("cargo hold/preparation must be objects")
        if (number(hold, "destination", True) != index or number(prep, "destination", True) != index
                or number(hold, "before", True) != index or number(hold, "after", True) != index + 1):
            raise ValueError("cargo hold does not identify one unique accepted destination")
        if hold.get("mapped_interact") is not True or hold.get("paused_during_hold") is not False:
            raise ValueError("cargo hold must use mapped input and active world time")
        for clock, minimum in (("world", 2.999), ("wall", 2.9)):
            start, end = number(hold, f"start_{clock}_s"), number(hold, f"end_{clock}_s")
            elapsed = number(hold, f"{clock}_elapsed_s")
            # The request can enter just before the next world tick. Millisecond
            # and frame quantization are explicit; no fixed or accelerated clock.
            if not minimum <= elapsed <= 8 or abs(end - start - elapsed) > .0001:
                raise ValueError("cargo hold did not observe three ordinary active seconds")
            if start < number(rows[index], f"{clock}_s") or end > number(rows[index + 1], f"{clock}_s"):
                raise ValueError("cargo hold lies outside its before/after original frames")
        for name in ("dropoff", "hero", "steed", "pack", "camera"):
            vector(prep.get(name))
        if math.dist(prep["hero"][:2], prep["dropoff"][:2]) > 260:
            raise ValueError("cargo prepared hero is outside ordinary unload reach")
        if math.dist(prep["hero"][:2], prep["steed"][:2]) <= 420:
            raise ValueError("cargo preparation could consume Interact as a remount")
    stock(metadata.get("terminal_before_teardown"), 3, rope=False)
    if number(metadata, "cargo_completions", True) != 1 or number(metadata, "cinematic_elapsed_ms", True) != 90000:
        raise ValueError("cargo completion or full cinematic was not observed")
    for clock, minimum in (("world", 89.9), ("wall", 89.5)):
        elapsed = number(metadata, f"cinematic_{clock}_s")
        end = number(metadata, f"cinematic_end_{clock}_s")
        start = number(metadata, f"cinematic_start_{clock}_s")
        if abs(end - start - elapsed) > .0001 or not number(holds[-1], f"start_{clock}_s") <= start <= number(holds[-1], f"end_{clock}_s"):
            raise ValueError("cargo cinematic is not bound to the final accepted transfer")
        if elapsed < minimum or elapsed > 100 or end < number(holds[-1], f"end_{clock}_s"):
            raise ValueError("cargo requires the full unskipped 90-second cinematic")
        if end > number(rows[-1], f"{clock}_s") or number(rows[-1], f"{clock}_s") - end > (1 if clock == "world" else 15):
            raise ValueError("cargo zero frame does not follow the natural cinematic end")
    return {phase: row for phase, row in zip(PHASES, rows)}
