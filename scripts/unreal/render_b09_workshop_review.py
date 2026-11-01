"""Socket-pose review captures of the b09 workshop candidates in Unreal: their actual framing at the hero's 94 deg, in
the candidate materials, from the work stands and the working side. Each state mesh stands at its socket in the pose
the state contract names; nothing holds it. These are editor review originals of candidates: not runtime
first-person hand contact (paws, grips, strip and brush contact stay production work), not the game's lighting or
post-process, and not an adoption.

**The level** (new each run, in its own folder /Game/ArtReview/B09Workshop/<out>/L_B09Review):
- the workshop's room and yard solids (the spec's copy of SoraLanternWorkshopRules::Solids) as cubes over a ground
  slab, in plain review materials;
- the candidate station meshes at their station points, and the drying poles and hooks;
- two paper-lamp lights over the plank floor, a hearth glow by the passage, a lamp under the storehouse eaves, and a
  real-time-capture sky light (as render_sora_lookdev.py's night), in one of two light sets (LIGHT_SETS, light=):
  neutral (6500 K, for material colour) or night (the intended oil-lamp look);
- manual exposure, metered at the work points: EV100 = log2(E / 2.5), E the median of the stations' inverse-square
  illuminance from the lamps (unoccluded, as render_nyaakoto_tp_review meters the sun).

**The shots** set each station's state as root's FView would (b09_workshop_craft.STATES), so the state meshes stand
at their sockets:

| Station | Shots |
|---|---|
| rib form | mid-bend (Committed 3, HeldMs 640: the fourth strip at flex 0.75 and the needle at the band's edge); a split strip; all six hoops |
| paste bench | half a seam (Committed 2, HeldMs 750; the frame turned for panel 3 on its tilted cradle); the rims seated |
| oil rack | half oiled (HeldMs 750) |
| shell bench | two shells seated and one core in the tray; all three seated, before the inspection |
| rafters | the suggested 24 craftspeople's lanterns; all 40; all 40 with Glow (a material demonstration, not a b09 state) |

**Cameras:**
- at the hero's standing eye over each work stand (the stand + (4, 0, 152) cm), looking at the station's work point,
  at the world's 94 deg, 1920x1080;
- the rib form's mid-bend also at 2520x1080 (21:9: 94 deg across, less height), and from two approach positions
  (1.5 m back, 0.9 m to either side);
- the rafters from the passage end of the room, and from under the poles.
A camera stands where a player could; none is a cinematic camera forced on play.

Writes Saved/B09Workshop/Review/<out>/<shot>.png and manifest.json: every file's SHA-256, the cameras, states and
placed meshes, the lights, the exposure, console variables, and the inputs' SHA-256. If the run fails,
manifest.partial.json records what was done.

Run (lane holder, full editor):
  scripts/toolchain/run-editor-script.sh --editor scripts/unreal/render_b09_workshop_review.py B09_REVIEW_COMPLETE <log> -- \\
      out=<new folder> readback=Saved/B09Workshop/Unreal/<the import's readback>.json light=neutral|night \\
      [review=<its host review>.json]
A readback with problems is drawn only with a host review (review_b09_import_readback.py) that explains every one.
"""
from __future__ import annotations

import hashlib
import json
import math
import statistics
import sys
import time
from pathlib import Path

import unreal

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sora_engine_pin import require_running_engine  # noqa: E402

require_running_engine("b09 workshop review")

ROOT = Path(unreal.Paths.project_dir()).resolve()
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LEVELS = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
ASSETS = unreal.EditorAssetLibrary
M = unreal.MathLibrary
SPEC = ROOT / "docs/art-direction/data/b09_workshop_craft_spec.json"
MESHES = MATS = None                # main(): the import readback's base (a new folder for each import run)
CANDIDATE_MATS = {}                 # main(): slot -> its candidate material, from the readback
STATES = {}                         # review_state's instances: (slot, scalars) -> MaterialInstanceConstant
BINDINGS = {}                       # mesh: the material each slot draws in this fresh editor, before any instance
# main(): each run's own review folder, named for its out=, refused if it exists. s151 shared one folder with s148:
# create_asset returned None for s148's review instances, and the shared M_B09R_Wood was rebuilt in place.
FOLDER = LEVEL = None
MARKER = "B09_REVIEW_COMPLETE"
HFOV = 94.0
EYE_CM = (4.0, 0.0, 152.0)          # the standing eye over the stand: capsule centre (floor + 88) + (4, 0, 64)
# (world cm, lumens, role): two paper lamps over the plank floor, a hearth glow by the passage, the eaves lamp
LAMPS = (((2000.0, -780.0, 235.0), 1200.0, "lamp"), ((2000.0, -1120.0, 235.0), 1200.0, "lamp"),
         ((1690.0, -950.0, 60.0), 600.0, "hearth"), ((2760.0, -1980.0, 230.0), 1500.0, "lamp"))
# The light sets (light=). The editor's white balance stays at 6500 K: no working script sets post-process white
# balance, so a set's colour lives in its lamps' temperature.
# - neutral: 6500 K, exposure as metered, to judge material colour.
# - night: the intended look, warm oil-lamp light (about 2200 K) as a camera balanced for tungsten (about 3400 K)
#   would show it. That is a warm shift of 1e6/2200 - 1e6/3400 = 160 mireds, which from the 6500 K balance is a
#   3200 K lamp. Exposure 0.7 EV under metered, for night. s148's 1900 K lamps were a 372-mired shift, which turned
#   every material orange.
LIGHT_SETS = {"neutral": {"lamp_kelvin": 6500.0, "hearth_kelvin": 6500.0, "ev_offset": 0.0},
              "night": {"lamp_kelvin": 3200.0, "hearth_kelvin": 2900.0, "ev_offset": -0.7}}
SKY = {"intensity": 1.0, "real_time_capture": True}    # as render_sora_lookdev.py's night: Lumen carries the bounce
# Plain review colours for the room, by root's ESurface (spec room.surfaces); the floor slabs and ceilings apart.
REVIEW = {"Floor": ((0.30, 0.20, 0.12), 0.7), "Wood": ((0.26, 0.18, 0.11), 0.8), "Stone": ((0.33, 0.32, 0.30), 0.85),
          "Ceiling": ((0.10, 0.07, 0.05), 0.8), "Soil": ((0.12, 0.10, 0.08), 0.9)}
CVARS = ("r.ScreenPercentage", "r.AntiAliasingMethod", "r.TSR.History.SampleCount", "r.HighResScreenshotDelay",
         "r.TextureStreaming", "r.DynamicGlobalIlluminationMethod", "r.ReflectionMethod", "r.Shadow.Virtual.Enable")
RUNUP_PER_HISTORY_SAMPLE = 2
SETTLE, FIRST_SETTLE = 150, 400     # editor frames before a shot, and before the first (render_nyaakoto_tp_review's)
STATION_MESH = {0: "SM_B09_RibFormStation", 1: "SM_B09_PasteStation", 2: "SM_B09_OilStation", 3: "SM_B09_ShellStation"}


def fail(message):
    raise RuntimeError("b09 review: " + message)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# --- Editor helpers, as render_nyaakoto_tp_review's ----------------------------------------------------------------
def load(path):
    asset = unreal.load_asset(path)
    if asset is None:
        fail(f"missing asset {path}")
    return asset


def spawn(cls, loc=(0.0, 0.0, 0.0), rot=None):
    return ACTORS.spawn_actor_from_class(cls, unreal.Vector(*loc), rot if rot is not None else unreal.Rotator(roll=0.0, pitch=0.0, yaw=0.0))


def world():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


def cvar(name):
    return unreal.SystemLibrary.get_console_variable_float_value(name)


def plain_material(name, colour, rough):
    """A constant-albedo review material in the level's folder, rebuilt each run."""
    folder = FOLDER
    path = f"{folder}/{name}"
    lib = unreal.MaterialEditingLibrary
    if ASSETS.does_asset_exist(path):
        m = unreal.load_asset(path)
        for e in list(lib.get_material_expressions(m)):
            lib.delete_material_expression(m, e)
    else:
        m = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())
    c = lib.create_material_expression(m, unreal.MaterialExpressionConstant3Vector, -300, 0)
    c.set_editor_property("constant", unreal.LinearColor(*colour, 1.0))
    lib.connect_material_property(c, "", unreal.MaterialProperty.MP_BASE_COLOR)
    r = lib.create_material_expression(m, unreal.MaterialExpressionConstant, -300, 200)
    r.set_editor_property("r", rough)
    lib.connect_material_property(r, "", unreal.MaterialProperty.MP_ROUGHNESS)
    lib.recompile_material(m)
    ASSETS.save_loaded_asset(m)
    return m


def exposure(ev100, offset=0.0):
    volume = spawn(unreal.PostProcessVolume)
    volume.set_editor_property("unbound", True)
    s = volume.get_editor_property("settings")
    for key, value in (("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL),
                       ("auto_exposure_apply_physical_camera_exposure", False),
                       ("auto_exposure_bias", -ev100 + 1.0 + offset), ("bloom_intensity", 0.675), ("vignette_intensity", 0.4),
                       ("motion_blur_amount", 0.0)):
        s.set_editor_property(f"override_{key}", True)
        s.set_editor_property(key, value)
    volume.set_editor_property("settings", s)
    return volume


def highres_runup():
    """r.HighResScreenshotDelay from TSR's history (two frames per history sample), read back."""
    samples = cvar("r.TSR.History.SampleCount")
    if not samples >= 8.0:
        fail(f"r.TSR.History.SampleCount reads {samples!r}")
    frames = int(math.ceil(RUNUP_PER_HISTORY_SAMPLE * samples))
    unreal.SystemLibrary.execute_console_command(world(), f"r.HighResScreenshotDelay {frames}")
    got = unreal.SystemLibrary.get_console_variable_int_value("r.HighResScreenshotDelay")
    if got != frames:
        fail(f"r.HighResScreenshotDelay reads {got}, not the {frames} set")
    return {"r.TSR.History.SampleCount": samples, "r.HighResScreenshotDelay": frames}


def spawn_camera(loc, target, width, height):
    rot = M.find_look_at_rotation(unreal.Vector(*loc), unreal.Vector(*target))
    cam = spawn(unreal.CameraActor, loc, rot)
    cc = cam.camera_component
    cc.set_editor_property("field_of_view", HFOV)
    cc.set_editor_property("aspect_ratio", width / height)
    cc.set_editor_property("constrain_aspect_ratio", True)
    l, r = cam.get_actor_location(), cam.get_actor_rotation()
    return cam, {"location_cm": [l.x, l.y, l.z], "rotation_deg": [r.pitch, r.yaw, r.roll], "target_cm": list(target),
                 "field_of_view_deg": cc.get_editor_property("field_of_view"),
                 "aspect_ratio": cc.get_editor_property("aspect_ratio"), "resolution": [width, height]}


# --- The scene ------------------------------------------------------------------------------------------------------
def gauge_angle(spec, ms):
    """b09_workshop_craft.gauge_angle: -90 deg at 0 ms to +90 at the gauge's full 960."""
    a0, a1 = spec["gauge"]["angles_deg"]
    return a0 + (a1 - a0) * min(max(ms, 0), spec["gauge"]["full_ms"]) / spec["gauge"]["full_ms"]


def yaw(deg):
    return unreal.Rotator(roll=0.0, pitch=0.0, yaw=deg)


def rot_xz(x, z):
    return M.make_rot_from_xz(unreal.Vector(*x), unreal.Vector(*z))


def yawed(p, centre, deg):
    """p turned by deg about the vertical through centre (+X toward +Y, as an Unreal yaw)."""
    a = math.radians(deg)
    dx, dy = p[0] - centre[0], p[1] - centre[1]
    return [centre[0] + dx * math.cos(a) - dy * math.sin(a), centre[1] + dx * math.sin(a) + dy * math.cos(a), p[2]]


def review_state(slot, scalars):
    """A review instance of a slot's candidate material with these scalar values (a MaterialInstanceConstant in the
    review folder, made through MaterialEditingLibrary as the import makes its own), made once."""
    key = (slot, tuple(sorted(scalars.items())))
    if key not in STATES:
        folder = FOLDER
        name = "MI_B09R_" + slot[len("M_B09_"):] + "".join(f"_{k}{v:g}".replace(".", "p") for k, v in key[1])
        lib = unreal.MaterialEditingLibrary
        mi = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, unreal.MaterialInstanceConstant,
                                                                     unreal.MaterialInstanceConstantFactoryNew())
        if mi is None:
            fail(f"could not create {folder}/{name}")
        lib.set_material_instance_parent(mi, load(CANDIDATE_MATS[slot]))
        for k, v in key[1]:
            lib.set_material_instance_scalar_parameter_value(mi, k, v)
        ASSETS.save_loaded_asset(mi)
        STATES[key] = mi
    return STATES[key]


def slot_index(mesh, slot):
    for i, m in enumerate(mesh.get_editor_property("static_materials")):
        if str(m.get_editor_property("material_slot_name")) == slot:
            return i
    fail(f"{mesh.get_name()} has no slot {slot}")


def place(name, loc, rot=None, params=None):
    """A candidate mesh at a world location (the candidates carry no collision). params {slot: {scalar: value}} draw
    that slot with a review instance of its candidate material (review_state)."""
    mesh = load(f"{MESHES}/{name}.{name}")
    a = spawn(unreal.StaticMeshActor, tuple(loc), rot)
    smc = a.static_mesh_component
    smc.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
    smc.set_static_mesh(mesh)
    if name not in BINDINGS:            # the import's binding, proved in this editor (package bytes are not proof)
        drawn = [smc.get_material(i) for i in range(smc.get_num_materials())]
        BINDINGS[name] = [m.get_path_name() if m is not None else None for m in drawn]
        if not drawn or any(m is None or not m.get_path_name().startswith(MATS + "/") for m in drawn):
            fail(f"{name} draws {BINDINGS[name]}, not its candidate materials")
    for slot, scalars in (params or {}).items():
        smc.set_material(slot_index(mesh, slot), review_state(slot, scalars))
    return a


def world_of(st, local):
    """A station-frame point in world cm (the station frame has the world's axes; its origin is on its floor)."""
    return [st["world_cm"][0] + local[0], st["world_cm"][1] + local[1], st["floor_cm"] + local[2]]


def metered_ev100(spec):
    """EV100 = log2(E / 2.5) at the median station work point, E from the lamps by the inverse-square law."""
    lux = []
    for st in spec["stations"]:
        w = world_of(st, st["work_point_cm"])
        e = 0.0
        for (x, y, z), lumens, _role in LAMPS:
            d2 = ((x - w[0]) ** 2 + (y - w[1]) ** 2 + (z - w[2]) ** 2) / 1e4          # m^2
            e += lumens / (4.0 * math.pi) / d2
        lux.append(e)
    return math.log2(statistics.median(lux) / 2.5), lux


def build(spec, ev100, light):
    ASSETS.make_directory(FOLDER)
    if not LEVELS.new_level(LEVEL):
        fail("could not create the level")
    cube = load("/Engine/BasicShapes/Cube.Cube")
    mats = {k: plain_material(f"M_B09R_{k}", c, r) for k, (c, r) in REVIEW.items()}
    ground = spawn(unreal.StaticMeshActor, (2575.0, -1150.0, -5.0))                  # a 10 cm slab, its top at z = 0
    ground.static_mesh_component.set_static_mesh(cube)
    ground.static_mesh_component.set_material(0, mats["Soil"])
    ground.set_actor_scale3d(unreal.Vector(22.5, 27.0, 0.1))
    room = spec["room"]
    for k, (cx, cy, cz, sx, sy, sz) in enumerate(room["solids_cm"]):
        a = spawn(unreal.StaticMeshActor, (cx, cy, cz))
        a.static_mesh_component.set_static_mesh(cube)
        kind = "Floor" if k in room["floor_slabs"] else "Ceiling" if k in room["ceilings"] else room["surfaces"][k]
        a.static_mesh_component.set_material(0, mats[kind])
        a.set_actor_scale3d(unreal.Vector(sx / 100.0, sy / 100.0, sz / 100.0))
    for (x, y, z), lumens, role in LAMPS:
        kelvin = LIGHT_SETS[light]["hearth_kelvin" if role == "hearth" else "lamp_kelvin"]
        lamp = spawn(unreal.PointLight, (x, y, z))
        lc = lamp.point_light_component
        lc.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
        lc.set_editor_property("intensity_units", unreal.LightUnits.LUMENS)
        lc.set_intensity(lumens)
        lc.set_use_temperature(True)
        lc.set_temperature(kelvin)
        lc.set_attenuation_radius(900.0)
        lc.set_editor_property("source_radius", 4.0)
    sky = spawn(unreal.SkyLight, (2500.0, -1000.0, 700.0))
    sky.light_component.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
    sky.light_component.set_editor_property("real_time_capture", SKY["real_time_capture"])
    sky.light_component.set_intensity(SKY["intensity"])
    exposure(ev100, LIGHT_SETS[light]["ev_offset"])
    for i, st in enumerate(spec["stations"]):
        place(STATION_MESH[i], (st["world_cm"][0], st["world_cm"][1], st["floor_cm"]))
    place("SM_B09_DryingPoles", (0.0, 0.0, 0.0))
    place("SM_B09_SlotHooks", (0.0, 0.0, 0.0))
    for command, name, want in (("r.TextureStreaming 0", "r.TextureStreaming", 0.0),
                                ("r.ScreenPercentage 100", "r.ScreenPercentage", 100.0)):
        unreal.SystemLibrary.execute_console_command(world(), command)
        if abs(cvar(name) - want) > 1e-6:
            fail(f"{name} reads {cvar(name)}, not the {want} set")


def shots(spec):
    """[{name, station, items [(mesh, loc, rot, params)], eye, target, size, state}] in capture order."""
    S = spec["stations"]
    hang = spec["lantern"]["hang_point_cm"]
    out = []

    def shot(name, station, items, eye, target, state, size=(1920, 1080)):
        out.append({"name": name, "station": station, "items": items, "eye": eye, "target": target, "size": size, "state": state})

    def stand_eye(st):
        return world_of(st, [st["work_stand"]["local_cm"][0] + EYE_CM[0], st["work_stand"]["local_cm"][1] + EYE_CM[1], EYE_CM[2]])

    def sock(st, n):
        return world_of(st, st["sockets"][n]["cm"])

    def sock_rot(st, n):
        s = st["sockets"][n]
        return rot_xz(s.get("x_axis", (1.0, 0.0, 0.0)), s.get("z_axis", (0.0, 0.0, 1.0)))

    # Bristles' tip on the work, the handle back toward the hero and up 30 deg, the flat across the seam or stroke.
    brush_rot = rot_xz((0.0, 1.0, 0.0), (0.5, 0.0, 0.866))

    # The rib form (step 0).
    st = S[0]
    lc, work = sock(st, "LanternCentre"), world_of(st, st["work_point_cm"])
    stages = spec["lantern"]["flex_stages"]
    for label, committed, ms, failed in (("rib_midbend", 3, 640, False), ("rib_split", 2, -1, True), ("rib_six", 6, -1, False)):
        # The form turns on its spindle as each strip winds on (one-ended winding): the form and its hoops, in the
        # form's frame, at LanternCentre, turned by wind_deg * (Committed[0] + the flex stage of HeldMs).
        flex = stages[int(round(min(max(ms, 0) / spec["recipe"]["bend_ms"][0], 1.0) * (len(stages) - 1)))] if ms >= 0 else 0.0
        turn = spec["lantern"]["wind_deg"] * (committed + flex)
        items = [("SM_B09_RibForm", lc, yaw(turn), None)]
        items += [(f"SM_B09_Hoop{k}", lc, yaw(turn), None) for k in range(1, committed + 1)]
        if ms >= 0:
            items.append((f"SM_B09_Hoop{committed + 1}_Flex{int(round(flex * 100)):03d}", lc, yaw(turn), None))
        needle = gauge_angle(spec, ms if ms >= 0 else 0)
        items.append(("SM_B09_GaugeNeedle", sock(st, "GaugePivot"), unreal.Rotator(roll=needle, pitch=0.0, yaw=0.0), None))
        if failed:
            items.append(("SM_B09_SplitStrip", sock(st, "SplitStripRest"), sock_rot(st, "SplitStripRest"), None))
        state = {"Committed": [committed, 0, 0, 0, 0, 0], "HeldStep": 0 if ms >= 0 else -1, "HeldMs": max(ms, 0),
                 "FailedStripAgeMs": 300 if failed else -1, "needle_roll_deg": needle, "form_yaw_deg": turn}
        shot(label, 0, items, stand_eye(st), work, state)
        if label == "rib_midbend":
            shot(label + "_21x9", 0, items, stand_eye(st), work, state, (2520, 1080))
            for side, dy in (("approach_left", -90.0), ("approach_right", 90.0)):
                shot(f"{label}_{side}", 0, items, world_of(st, [-150.0, dy, EYE_CM[2]]), work, state)
    # The paste bench (steps 1 and 2): the frame on its tilted cradle (LanternCentre's axes), turned about its own axis
    # by panel_turn_deg for the panel being laid, so that panel's seam stays at the cradle's Seam_0..8 facing the hero;
    # the gores go on in paste_order.
    st = S[1]
    lc, work = sock(st, "LanternCentre"), world_of(st, st["work_point_cm"])
    ax_x, ax_z = st["sockets"]["LanternCentre"]["x_axis"], st["sockets"]["LanternCentre"]["z_axis"]
    ax_y = [ax_z[1] * ax_x[2] - ax_z[2] * ax_x[1], ax_z[2] * ax_x[0] - ax_z[0] * ax_x[2], ax_z[0] * ax_x[1] - ax_z[1] * ax_x[0]]

    def frame_rot(turn):
        a = math.radians(turn)
        return rot_xz([math.cos(a) * ax_x[k] + math.sin(a) * ax_y[k] for k in range(3)], ax_z)

    order = st["paste_order"]
    for label, n, ms, rims in (("paste_halfseam", 2, 750, False), ("paste_rims", 4, -1, True)):
        panel = min(n + 1, 4)
        turn = st["panel_turn_deg"][panel - 1]
        items = [("SM_B09_PasteFrame", lc, frame_rot(turn), None)]
        items += [(f"SM_B09_Washi{k}", lc, frame_rot(turn), None) for k in order[:n]]
        if ms >= 0:
            items.append((f"SM_B09_Washi{order[n]}", lc, frame_rot(turn), {"M_B09_Washi": {"PasteReveal": ms / spec["recipe"]["paste_ms"]}}))
            items.append(("SM_B09_PasteBrush", sock(st, "Seam_4"), brush_rot, None))
            rail = range(n + 2, 5)                         # the sheet being pasted has left the rail
        else:
            items.append(("SM_B09_PasteBrush", sock(st, "BrushRest"), sock_rot(st, "BrushRest"), None))
            rail = range(n + 1, 5)
        items += [(f"SM_B09_WashiSheet{j}", sock(st, f"WashiSheet{j}"), sock_rot(st, f"WashiSheet{j}"), None) for j in rail]
        for which in ("Bottom", "Top"):
            items.append((f"SM_B09_Rim{which}", sock(st, f"Rim{which}{'Seat' if rims or which == 'Bottom' else 'Rest'}"), None, None))
        state = {"Committed": [6, n, 1 if rims else 0, 0, 0, 0], "HeldStep": 1 if ms >= 0 else -1, "HeldMs": max(ms, 0),
                 "panel_turn_deg": turn}
        shot(label, 1, items, stand_eye(st), work, state)
    # The oil rack (step 3): the finished lantern hangs from its hang point on LanternHang.
    st = S[2]
    h = sock(st, "LanternHang")
    centre = [h[0] - hang[0], h[1] - hang[1], h[2] - hang[2]]
    items = [("SM_B09_LanternFinished", centre, None, {"M_B09_Washi": {"OilWet": 750 / spec["recipe"]["paste_ms"]}}),
             ("SM_B09_OilBrush", sock(st, "OilSwath_4"), brush_rot, None)]
    shot("oil_half", 2, items, stand_eye(st), world_of(st, st["work_point_cm"]),
         {"Committed": [6, 4, 1, 0, 0, 0], "HeldStep": 3, "HeldMs": 750})
    # The shell bench (steps 4 and 5), weapon 7's in-tree mesh as a review stand-in on its rest.
    st = S[3]
    weapon = ("SM_B09_Weapon07_ReviewStandIn", sock(st, "WeaponRest"), sock_rot(st, "WeaponRest"), None)
    for label, n in (("shell_two", 2), ("shell_three", 3)):
        items = [weapon] + [("SM_B09_ShellWrapped", sock(st, f"ShellSeat{k}"), None, None) for k in range(1, n + 1)]
        items += [("SM_B09_ShellCore", sock(st, f"ShellCore{k}"), None, None) for k in range(n + 1, 4)]
        shot(label, 3, items, stand_eye(st), world_of(st, st["work_point_cm"]),
             {"Committed": [6, 4, 1, 1, n, 0], "HeldStep": -1, "HeldMs": 0})
    # The rafters: the lanterns hang from their hang points on the hooks.
    slots = spec["hanging_output"]["slots"]

    def lanterns(count, glow):
        rows = []
        for s in slots[:count]:
            p = s["hook_cm"]
            rows.append(("SM_B09_LanternFinished", [p[0] - hang[0], p[1] - hang[1], p[2] - hang[2]], yaw(s["yaw_deg"]),
                         {"M_B09_Washi": {"Glow": glow}} if glow else None))
        return rows

    passage = ([2050.0, -470.0, 45.0 + EYE_CM[2]], [2050.0, -1150.0, 330.0])
    below = ([1980.0, -1000.0, 45.0 + EYE_CM[2]], [2060.0, -950.0, 360.0])
    shot("rafters_24", None, lanterns(24, 0.0), *passage, {"slots_filled": 24, "RecipeComplete": False})
    shot("rafters_40", None, lanterns(40, 0.0), *passage, {"slots_filled": 40, "RecipeComplete": True})
    shot("rafters_40_below", None, lanterns(40, 0.0), *below, {"slots_filled": 40, "RecipeComplete": True})
    shot("rafters_40_glow_demo", None, lanterns(40, 5.0), *passage,
         {"slots_filled": 40, "Glow": 5.0, "note": "a material demonstration (about a candle's 5 cd/m2 through the paper), not a b09 state"})
    return out


def main():
    opts = {"out": "", "readback": "", "review": "", "light": ""}
    for a in sys.argv[1:]:
        if "=" in a:
            k, v = a.split("=", 1)
            opts[k] = v
    if not opts["out"] or not opts["readback"] or opts["light"] not in LIGHT_SETS:
        fail(f"out=<new folder>, readback=<the import's readback> and light={'|'.join(LIGHT_SETS)} are required")
    out = ROOT / "Saved/B09Workshop/Review" / opts["out"]
    if out.exists():
        fail(f"{out} exists: originals go to a new folder")
    global FOLDER, LEVEL
    if not all(c.isalnum() or c == "_" for c in opts["out"]):
        fail(f"out={opts['out']!r}: letters, digits and _ only (it names the review folder)")
    FOLDER = f"/Game/ArtReview/B09Workshop/{opts['out']}"
    LEVEL = f"{FOLDER}/L_B09Review"
    if ASSETS.does_directory_exist(FOLDER) and ASSETS.list_assets(FOLDER, recursive=True):
        fail(f"{FOLDER} exists: each run's review assets are its own")
    global MESHES, MATS, CANDIDATE_MATS
    rb_bytes = (ROOT / opts["readback"]).read_bytes()
    rb = json.loads(rb_bytes.decode("utf-8"))
    review_bytes = None
    if rb["problems"]:                  # only with a host review that explains every one (review_b09_import_readback.py)
        if not opts["review"]:
            fail("the import's readback has problems and no host review explains them")
        review_bytes = (ROOT / opts["review"]).read_bytes()
        review = json.loads(review_bytes.decode("utf-8"))
        if review["readback_sha256"] != hashlib.sha256(rb_bytes).hexdigest() or review["unexplained"] or \
                sorted(review["explained"]) != sorted(rb["problems"]):
            fail("the host review does not explain every problem of this readback")
    MESHES, MATS = f"{rb['base']}/Meshes", f"{rb['base']}/Materials"
    CANDIDATE_MATS = dict(rb["materials"])
    spec_bytes = SPEC.read_bytes()
    spec = json.loads(spec_bytes.decode("utf-8"))
    queue = shots(spec)
    ev100, lux = metered_ev100(spec)
    out.mkdir(parents=True)
    build(spec, ev100, opts["light"])
    for s in queue:                     # every review instance the shots draw, made before the first frame
        for mesh, loc, rot, params in s["items"]:
            for slot, scalars in (params or {}).items():
                review_state(slot, scalars)
    runup = highres_runup()
    unreal.SystemLibrary.execute_console_command(world(), "Editor.AsyncAssetCompilationFinishAll")
    record = {"level": LEVEL, "engine": unreal.SystemLibrary.get_engine_version(), "candidates": rb["base"], "hfov_deg": HFOV,
              "eye_over_stand_cm": EYE_CM,
              "ev100": ev100, "exposure_bias": 1.0 - ev100, "work_point_lux": dict(zip([s["id"] for s in spec["stations"]], lux)),
              "light": dict(LIGHT_SETS[opts["light"]], name=opts["light"]),
              "lamps": [{"cm": list(p), "lumens": l, "role": r} for p, l, r in LAMPS], "sky": SKY, "review_materials": REVIEW,
              "highres_runup": runup, "shots_requested": [s["name"] for s in queue],
              "inputs": {str(SPEC.relative_to(ROOT)): hashlib.sha256(spec_bytes).hexdigest(),
                         opts["readback"]: hashlib.sha256(rb_bytes).hexdigest(),
                         **({opts["review"]: hashlib.sha256(review_bytes).hexdigest()} if review_bytes else {}),
                         "scripts/unreal/render_b09_workshop_review.py": sha256(__file__)},
              "status": ("a diagnostic capture of a failed import candidate: its readback problems stand. A host review "
                         "explains them; it does not pass them" if rb["problems"] else "a review capture of a passed import"),
              "readback_problems": rb["problems"],
              "shots": {}, "files": {}, "bindings": BINDINGS,
              "review_states": {f"{slot} {dict(sc)}": STATES[(slot, sc)].get_path_name() for slot, sc in STATES},
              "scope": "socket-pose review captures of the b09 candidates at the hero's 94 deg (editor originals): each "
                       "state mesh at its socket, held by nothing. Not runtime first-person hand contact (paws, grips, "
                       "strip and brush contact stay production work), not the game's lighting or post-process, and "
                       "not an adoption"}
    status = {"frames": 0, "phase": "state", "count": 0, "actors": []}

    def write(name):
        record["cvars"] = {k: cvar(k) for k in CVARS}
        (out / name).write_text(json.dumps(record, indent=1) + "\n")

    def finish(message, error=False):
        # As render_nyaakoto_tp_review.finish: release the keep-alive and let -ExecutePythonScript's executor defer
        # QUIT_EDITOR (never quit_editor from a Slate callback: the exit hang, EDITOR_EXIT_HANG.md).
        unreal.unregister_slate_post_tick_callback(handle)
        (unreal.log_error if error else unreal.log)(message)
        unreal.EditorPythonScripting.set_keep_python_script_alive(False)

    def tick(delta):
        try:
            step()
        except Exception as exc:  # never spin on a failing callback
            try:
                write("manifest.partial.json")
            except Exception:
                pass
            finish(f"B09_REVIEW_FAILED: {exc!r}", error=True)

    def step():
        status["frames"] += 1
        LEVELS.editor_invalidate_viewports()
        if status["frames"] < 30:
            return
        if status["phase"] == "state":
            for a in status["actors"]:
                ACTORS.destroy_actor(a)
            status["actors"] = []
            if not queue:
                write("manifest.json")
                finish(f"{MARKER}: {len(record['files'])} captures in {out}")
                return
            s = queue[0]
            for mesh, loc, rot, params in s["items"]:
                status["actors"].append(place(mesh, loc, rot, params))
            w, h = s["size"]
            cam, got = spawn_camera(s["eye"], s["target"], w, h)
            status["actors"].append(cam)
            record["shots"][s["name"]] = {"station": s["station"], "state": s["state"], "camera": got,
                                          "items": [{"mesh": m, "cm": [round(c, 3) for c in loc],
                                                     "rotation_deg": None if rot is None else [rot.pitch, rot.yaw, rot.roll],
                                                     "params": p} for m, loc, rot, p in s["items"]]}
            LEVELS.pilot_level_actor(cam)
            LEVELS.editor_set_game_view(True)
            status.update(phase="light", count=0, shot=s)
            return
        if status["phase"] == "light":
            status["count"] += 1
            # Lumen, TSR and exposure settle; the first shot also waits out the shaders and the scene's first capture.
            if status["count"] < (FIRST_SETTLE if not record["files"] else SETTLE):
                return
            s = status["shot"]
            path = out / f"{s['name']}.png"
            w, h = s["size"]
            status.update(phase="shot", path=path, started=time.time(), count=0)
            unreal.SystemLibrary.execute_console_command(world(), f'HighResShot {w}x{h} filename="{path}"')
            return
        if status["phase"] == "shot":
            p = status["path"]
            if not p.is_file() or p.stat().st_mtime < status["started"]:
                status["count"] += 1
                if status["count"] > 6000:
                    fail(f"{p} was not written")
                return
            record["files"][p.name] = sha256(p)
            queue.pop(0)
            status["phase"] = "state"

    handle = unreal.register_slate_post_tick_callback(tick)
    unreal.EditorPythonScripting.set_keep_python_script_alive(True)


if __name__ == "__main__":
    main()
