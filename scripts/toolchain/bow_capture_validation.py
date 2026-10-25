"""Inspect original framebuffer pixels and their live HUD observations; never edit them."""
import math
import struct
import zlib

PHASES = ("steady", "positive", "negative", "released")


def rgb8(data):
    """Decode UE's non-interlaced RGB/RGBA8 screenshot after PNG CRC validation."""
    offset, packed = 8, bytearray()
    width = height = channels = 0
    while offset + 12 <= len(data):
        size = struct.unpack_from(">I", data, offset)[0]
        kind, payload = data[offset + 4:offset + 8], data[offset + 8:offset + 8 + size]
        if kind == b"IHDR":
            width, height, depth, color, compression, filtering, interlace = struct.unpack(">IIBBBBB", payload)
            if depth != 8 or color not in (2, 6) or compression or filtering or interlace:
                raise ValueError("bow capture requires the original RGB/RGBA8 non-interlaced framebuffer")
            channels = 3 if color == 2 else 4
        if kind == b"IDAT":
            packed.extend(payload)
        offset += size + 12
    stride = width * channels
    raw, rows, previous = zlib.decompress(packed), [], bytearray(stride)
    if not channels or len(raw) != (stride + 1) * height:
        raise ValueError("bow screenshot has incomplete pixels")
    for y in range(height):
        start = y * (stride + 1)
        mode, row = raw[start], bytearray(raw[start + 1:start + 1 + stride])
        for x in range(stride):
            a, b, c = (row[x - channels] if x >= channels else 0), previous[x], (previous[x - channels] if x >= channels else 0)
            if mode == 1:
                prediction = a
            elif mode == 2:
                prediction = b
            elif mode == 3:
                prediction = (a + b) // 2
            elif mode == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                prediction = a if pa <= pb and pa <= pc else b if pb <= pc else c
            elif mode == 0:
                prediction = 0
            else:
                raise ValueError("invalid bow PNG row filter")
            row[x] = (row[x] + prediction) & 255
        rows.append(row)
        previous = row
    return width, height, channels, rows


def crosshair_pixels(image):
    """Locate all four 4..10 px reticle arms independently near viewport center.

    This measures local line contrast, not color-perfect matches or a painted
    overlay. The target/world remains in the PNG. Ambiguous or invisible arms
    fail; a human still judges whether the small motion feels readable.
    """
    width, height, channels, rows = image
    def light(x, y):
        x0, y0 = math.floor(x), math.floor(y)
        dx, dy = x - x0, y - y0
        def at(px, py):
            r, g, b = rows[py][px * channels:px * channels + 3]
            return (.2126 * r + .7152 * g + .0722 * b) / 255
        return ((1 - dx) * at(x0, y0) + dx * at(x0 + 1, y0)) * (1 - dy) + ((1 - dx) * at(x0, y0 + 1) + dx * at(x0 + 1, y0 + 1)) * dy
    best = (-1, 0, 0, 0)
    for ix in range(-16, 17):
        for iy in range(-16, 17):
            cx, cy = width / 2 + ix / 2, height / 2 + iy / 2
            arms = []
            for vx, vy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                samples = []
                for distance in (5, 6, 7, 8, 9):
                    x, y = cx + vx * distance, cy + vy * distance
                    samples.append(light(x, y) - (light(x - 3 * vy, y + 3 * vx) + light(x + 3 * vy, y - 3 * vx)) / 2)
                arms.append(sum(samples) / len(samples))
            score = (sum(arms) / 4 + min(arms)) / 2
            if score > best[0]:
                best = score, cx, cy, min(arms)
    if best[0] < .04 or best[3] < .015:
        raise ValueError("bow PNG does not resolve all four reticle arms against the real background")
    return {"center": [best[1], best[2]], "contrast_score": best[0], "weakest_arm_contrast": best[3]}


def vector(meta, name, length):
    value = meta.get(name)
    if not isinstance(value, list) or len(value) != length or any(type(x) not in (int, float) or not math.isfinite(x) for x in value):
        raise ValueError(f"invalid bow observation {name}")
    return value


def verify_frame(meta, data, width, height):
    phase = meta.get("phase")
    if phase not in PHASES or vector(meta, "viewport", 2) != [width, height]:
        raise ValueError("bow phase/viewport mismatch")
    center, projected = vector(meta, "reticle", 2), vector(meta, "projected", 2)
    if math.dist(center, projected) > .25:
        raise ValueError("observed Canvas reticle differs from independent shared-ray projection")
    for name, count in (("camera", 3), ("rotation", 3), ("ray", 3), ("bow_quat", 4)):
        vector(meta, name, count)
    target = vector(meta, "target", 2)
    if not (20 < target[0] < width - 20 and 20 < target[1] < height - 20):
        raise ValueError("the actual range target is outside the captured viewport")
    age, wall, frame = meta.get("draw_age_s"), meta.get("wall_elapsed_s"), meta.get("frame")
    if any(type(x) not in (int, float) or not math.isfinite(x) or x < 0 for x in (age, wall, frame)) or age > wall + .25:
        raise ValueError("invalid/compressed live bow clock observation")
    pitch, yaw = vector(meta, "offset_degrees", 2)
    drawing = phase != "released"
    if (meta.get("presentation_schema_version") != 1 or meta.get("fallback_bow") is not True
            or meta.get("presentation_pose") != ("bow.drawn" if drawing else "bow")):
        raise ValueError("bow presentation observation is absent or has the wrong admission/state")
    presentation = vector(meta, "presentation_projected_direction", 3)
    if abs(math.hypot(*presentation) - 1) > 1e-5 or (drawing and math.dist(presentation, meta["ray"]) > 1e-5):
        raise ValueError("native first-person presentation direction differs from the current gameplay ray")
    for field in ("world_fov", "first_person_fov"):
        value = meta.get(field)
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 < value < 180:
            raise ValueError("bow presentation requires actual camera FOV observations")
    if meta.get("drawing") is not drawing or meta.get("attack_held") is not drawing or meta.get("ammo") != (12 if drawing else 11):
        raise ValueError("bow capture lost real held input or finite ammunition")
    valid = {"steady": .65 <= age < 4.65 and pitch == yaw == 0,
             "positive": age > 4.65 and pitch > 0 and yaw > 0,
             "negative": age > 4.65 and pitch < 0 and yaw < 0,
             "released": pitch == yaw == 0}[phase]
    if not valid:
        raise ValueError("bow PNG is not the declared observed sway phase")
    if phase == "negative":
        release = vector(meta, "release_ray", 3)
        if math.dist(vector(meta, "shot_ray", 3), release) > 1e-8:
            raise ValueError("released shot differs from the separately sampled release aim ray")
        times = [meta.get(key) for key in ("sample_world_s", "release_world_s", "release_delay_s", "release_wall_elapsed_s", "release_frame", "shot_world_s", "shot_frame")]
        if any(type(x) not in (int, float) or not math.isfinite(x) for x in times):
            raise ValueError("missing separate render/release timestamps")
        sample_time, release_time, delay, release_wall, release_frame, shot_time, shot_frame = times
        if delay < 0 or abs(release_time - sample_time - delay) > 1e-9 or release_wall < wall or release_frame < frame:
            raise ValueError("inconsistent separate render/release timestamps")
        if shot_time != release_time or shot_frame != release_frame:
            raise ValueError("emitted shot did not retain the observed release frame/time")
        same = math.dist(meta["shot_ray"], meta["ray"]) <= 1e-8
        if meta.get("shot_matches_render_sample") is not same:
            raise ValueError("shot/render equality claim contradicts the measured rays")
        projected_release = vector(meta, "release_projected", 2)
        if delay == 0 and (not same or math.dist(projected_release, projected) > .25):
            raise ValueError("same-time rendered and release aim disagree")
    image = rgb8(data)
    if image[:2] != (width, height):
        raise ValueError("bow pixel dimensions differ")
    result = crosshair_pixels(image)
    if math.dist(result["center"], center) > 1.5:
        raise ValueError("original PNG reticle pixels differ from observed Canvas coordinates")
    return result


def verify_sequence(frames):
    if len(frames) != 4 or {meta["phase"] for meta, _ in frames} != set(PHASES):
        raise ValueError("bow capture requires exactly steady/positive/negative/released original frames")
    ordered = sorted(frames, key=lambda pair: PHASES.index(pair[0]["phase"]))
    base, base_pixels = ordered[0]
    for index, (meta, pixels) in enumerate(ordered):
        if math.dist(meta["camera"], base["camera"]) > .1 or math.dist(meta["rotation"], base["rotation"]) > .001:
            raise ValueError("bow capture moved the fixed camera between phases")
        if any(abs(meta[key] - base[key]) > 1e-5 for key in ("world_fov", "first_person_fov")):
            raise ValueError("bow capture changed camera FOV between phases")
        if index and any(meta[key] <= ordered[index - 1][0][key] for key in ("frame", "draw_age_s", "wall_elapsed_s")):
            raise ValueError("bow frames did not advance through normal live time")
    positive, negative, released = (pair[1]["center"] for pair in ordered[1:])
    if positive[0] - negative[0] < 2 or negative[1] - positive[1] < 1:
        raise ValueError("positive/negative bow motion is not resolved in actual reticle pixels")
    if math.dist(released, base_pixels["center"]) > 1.5:
        raise ValueError("released bow reticle did not return to its steady pixels")
