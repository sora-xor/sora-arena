"""The third-person grip contract's slice A in Unreal (docs/art-direction/THIRD_PERSON_GRIP_CONTRACT.md 4.3, 4.4).

What it imports:
- **The body:** the rebuilt SK_NyaagyuSamurai, with its idle, walk and interim guard.
- **The sockets:** its grip and saya sockets.
- **The weapons:** the authored W00 katana and saya, with their own sockets.

Everything is read back.

Run it (UE 5.8, headless, by the holder of the shared engine lane) after rig_nyaakoto_runtime.py and
generate_nyaakoto_lods.py:
  scripts/toolchain/run-editor-script.sh scripts/unreal/import_nyaakoto_third_person.py NYAAKOTO_TP_UE_READY [log] \
      -- --readback Saved/NyaakotoThirdPerson/Unreal/<new name>.json

**The body:**
- SK_NyaagyuSamurai goes into /Game/Generated/Meshes as import_original_assets.py imports it. Its idle becomes
  A_NyaagyuSamurai_Idle; A_NyaagyuSamurai_Walk follows, then the authored LODs (import_nyaakoto_lods.py).
- A_NyaagyuSamurai_Guard goes into /Game/Generated/Animations.
- Every FBX is checked against runtime_skin_manifest.json, and that record's clearance gates must all have passed.

**The sockets:**
- hand_r_grip, hand_l_grip and gear_saya_l come from the record's "third_person" sockets.
- Each is placed on its bone from its component-space bind point and axes, through the bone's reference pose.
- UE 5.8 keeps a socket's name and bone read-only to scripts. So a socket is added, renamed and re-parented; one
  that already exists is moved instead.

**The weapons:**
- SM_Weapon_00 and SM_Weapon_00_Saya go into /Game/Generated/Weapons/Runtime/W00_Katana, each at LOD0.
- Their SOCKET_ empties become sockets, checked against build_record.json.
- Their four maps feed a master M_W00_Weapon and its instance.

The readback (a new file, never overwritten) records:
- each body socket's component transform at the reference pose, against the record: within 0.1 cm and 0.5 deg;
- each weapon socket against build_record.json: within 0.1 cm;
- the guard's grip sockets at its first frame against the interim stance's targets: within 1 cm and 2 deg.

This is an asset readback only: not a render, a capture or a gameplay admission.
"""

import hashlib
import json
import math
import runpy
import sys
from pathlib import Path

import unreal

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sora_engine_pin import require_running_engine  # noqa: E402

require_running_engine("Nyaakoto third-person import")

ROOT = Path(unreal.Paths.project_dir()).resolve()
SOURCE = ROOT / "Content/SourceArt"
HERO = SOURCE / "Characters/Hero"
W00 = SOURCE / "Weapons/Runtime/W00_Katana"
MESHES = "/Game/Generated/Meshes"
ANIMS = "/Game/Generated/Animations"
WEAPONS = "/Game/Generated/Weapons/Runtime/W00_Katana"
MARKER = "NYAAKOTO_TP_UE_READY"

tools = unreal.AssetToolsHelpers.get_asset_tools()
assets = unreal.EditorAssetLibrary
lib = unreal.MaterialEditingLibrary
M = unreal.MathLibrary


def fail(message):
    raise RuntimeError("nyaakoto third person UE: " + message)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def vec(v):
    return [round(v.x, 5), round(v.y, 5), round(v.z, 5)]


def require_api(owner, *names):
    missing = [n for n in names if not hasattr(owner, n)]
    if missing:
        fail(f"{getattr(owner, '__name__', owner)} lacks {missing}")


def finish_compilation():
    unreal.SystemLibrary.execute_console_command(
        unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world(),
        "Editor.AsyncAssetCompilationFinishAll")


def import_task(filename, destination, name, options=None):
    task = unreal.AssetImportTask()
    task.filename = str(filename)
    task.destination_path = destination
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = True
    if options is not None:
        task.options = options
    tools.import_asset_tasks([task])
    return task


def frame_transform(point, x_axis, z_axis):
    """A component transform from a point (cm) and its X and Z axes (Unreal axes)."""
    rot = M.make_rot_from_xz(unreal.Vector(*x_axis), unreal.Vector(*z_axis))
    return unreal.Transform(location=unreal.Vector(*point), rotation=rot, scale=unreal.Vector(1.0, 1.0, 1.0))


def angle_between(t1, t2):
    """Degrees between two transforms' rotations."""
    q1, q2 = t1.rotation, t2.rotation
    d = abs(q1.x * q2.x + q1.y * q2.y + q1.z * q2.z + q1.w * q2.w)
    return math.degrees(2.0 * math.acos(min(1.0, d)))


def distance(t1, t2):
    a, b = t1.translation, t2.translation
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2)


# --- Inputs, by hash ------------------------------------------------------------------------------------------------
args = sys.argv[1:]
if "--readback" not in args:
    fail("--readback <new path under Saved/NyaakotoThirdPerson/Unreal> is required")
READBACK = (ROOT / args[args.index("--readback") + 1]).resolve()
if READBACK.exists() or not READBACK.is_relative_to(ROOT / "Saved/NyaakotoThirdPerson/Unreal"):
    fail(f"the readback must be a new file under Saved/NyaakotoThirdPerson/Unreal: {READBACK}")
record = json.loads((HERO / "runtime_skin_manifest.json").read_text(encoding="utf-8"))
if record.get("schema_version") != 1 or record.get("generator") != "scripts/art/rig_nyaakoto_runtime.py":
    fail("runtime skin manifest identity changed")
for key in ("skeletal_fbx", "walk_fbx", "guard_fbx"):
    if sha256(SOURCE / record[key]) != record[key + "_sha256"]:
        fail(f"{record[key]} differs from runtime_skin_manifest.json")
tp = record["third_person"]
if not tp["clearance"]["calibration"]["ok"] or not all(
        ok for row in tp["clearance"]["passed"].values() for ok in row.values()):
    fail("the rig build's clearance gates did not all pass")
if set(tp["sockets"]) != {"hand_r_grip", "hand_l_grip", "gear_saya_l"}:
    fail(f"unexpected sockets in the record: {sorted(tp['sockets'])}")
build = json.loads((W00 / "build_record.json").read_text(encoding="utf-8"))
weapon_files = {"SM_Weapon_00": W00 / "SM_Weapon_00.fbx", "SM_Weapon_00_Saya": W00 / "SM_Weapon_00_Saya.fbx"}
for name, file in weapon_files.items():
    want = build["assets"][name]["lods"][0]
    if Path(want["file"]).name != file.name or sha256(file) != want["sha256"]:
        fail(f"{file.name} differs from build_record.json")
    if tp["weapons"][file.name]["sha256"] != want["sha256"]:
        fail(f"the rig build measured a different {file.name}")

# --- The body, as import_original_assets.py imports it, and the guard --------------------------------------------------
options = unreal.FbxImportUI()
options.import_mesh = True
options.import_as_skeletal = True
options.import_animations = True
options.import_materials = True
options.import_textures = False
options.create_physics_asset = False
options.mesh_type_to_import = unreal.FBXImportType.FBXIT_SKELETAL_MESH
options.skeletal_mesh_import_data.set_editor_property("vertex_color_import_option", unreal.VertexColorImportOption.REPLACE)
# The empty-fist shape keys (PawEmpty_R, PawEmpty_L) are morph targets. Unreal drops them unless asked.
options.skeletal_mesh_import_data.set_editor_property("import_morph_targets", True)
task = import_task(SOURCE / record["skeletal_fbx"], MESHES, "SK_NyaagyuSamurai", options)
mesh = assets.load_asset(f"{MESHES}/SK_NyaagyuSamurai")
if not isinstance(mesh, unreal.SkeletalMesh) or not mesh.has_vertex_colors():
    fail("SK_NyaagyuSamurai did not import as a skeletal mesh with its coat-blend colours")
skeleton = mesh.get_editor_property("skeleton")
clips = {}
idle_target = f"{ANIMS}/A_NyaagyuSamurai_Idle"
for path in task.imported_object_paths:
    if isinstance(assets.load_asset(path), unreal.AnimSequence):
        if assets.does_asset_exist(idle_target):
            assets.delete_asset(idle_target)
        if not assets.rename_asset(path, idle_target):
            fail(f"cannot name the idle {idle_target}")
for clip, key in (("Walk", "walk_fbx"), ("Guard", "guard_fbx")):
    anim_options = unreal.FbxImportUI()
    anim_options.import_mesh = False
    anim_options.import_as_skeletal = True
    anim_options.import_animations = True
    anim_options.mesh_type_to_import = unreal.FBXImportType.FBXIT_ANIMATION
    anim_options.skeleton = skeleton
    target = f"{ANIMS}/A_NyaagyuSamurai_{clip}"
    t = import_task(SOURCE / record[key], ANIMS, f"A_NyaagyuSamurai_{clip}", anim_options)
    if not assets.does_asset_exist(target):
        for path in t.imported_object_paths:
            if isinstance(assets.load_asset(path), unreal.AnimSequence):
                if not assets.rename_asset(path, target):
                    fail(f"cannot name {target}")
                break
    clips[clip] = assets.load_asset(target)
    if not isinstance(clips[clip], unreal.AnimSequence):
        fail(f"{target} did not import")
if not assets.does_asset_exist(idle_target):
    fail("the idle did not import")
runpy.run_path(str(ROOT / "scripts/unreal/import_nyaakoto_lods.py"), run_name="__main__")
mesh = assets.load_asset(f"{MESHES}/SK_NyaagyuSamurai")
finish_compilation()

# --- The body's sockets ---------------------------------------------------------------------------------------------
require_api(unreal.AnimPoseExtensions, "get_reference_pose", "get_ref_bone_pose", "get_anim_pose_at_time",
            "get_bone_pose")
require_api(unreal.SkeletalMeshSocket, "set_socket_parent")
require_api(unreal.SkeletalMeshEditorSubsystem, "rename_socket")
world = unreal.AnimPoseSpaces.WORLD
ref = unreal.AnimPoseExtensions.get_reference_pose(skeleton)
readback = {"inputs": {k: record[k + "_sha256"] for k in ("skeletal_fbx", "walk_fbx", "guard_fbx")},
            "sockets": {}, "weapons": {}, "guard": {}}
relative = {}
for name, s in tp["sockets"].items():
    bone = unreal.AnimPoseExtensions.get_ref_bone_pose(ref, s["bone"], world)
    want = frame_transform(s["component_cm"], s["x_axis"], s["z_axis"])
    rel = M.compose_transforms(want, M.invert_transform(bone))
    socket = mesh.find_socket(name)
    if socket is None:
        socket = unreal.SkeletalMeshSocket(mesh)
        mesh.add_socket(socket, False)
        placeholder = socket.get_editor_property("socket_name")
        if not unreal.SkeletalMeshEditorSubsystem.rename_socket(mesh, placeholder, name):
            fail(f"cannot rename socket {placeholder} to {name}")
    socket.set_socket_parent(mesh, s["bone"])
    socket.set_editor_property("relative_location", rel.translation)
    socket.set_editor_property("relative_rotation", rel.rotation.rotator())
    socket.set_editor_property("relative_scale", unreal.Vector(1.0, 1.0, 1.0))
    relative[name] = rel
assets.save_loaded_asset(mesh)
mesh = assets.load_asset(f"{MESHES}/SK_NyaagyuSamurai")
for name, s in tp["sockets"].items():
    got = mesh.find_socket(name)
    if got is None or str(got.get_editor_property("bone_name")) != s["bone"]:
        fail(f"socket {name} did not read back on {s['bone']}")
    rel = unreal.Transform(location=got.get_editor_property("relative_location"),
                           rotation=got.get_editor_property("relative_rotation"), scale=unreal.Vector(1.0, 1.0, 1.0))
    bone = unreal.AnimPoseExtensions.get_ref_bone_pose(ref, s["bone"], world)
    comp = M.compose_transforms(rel, bone)
    want = frame_transform(s["component_cm"], s["x_axis"], s["z_axis"])
    err_cm, err_deg = distance(comp, want), angle_between(comp, want)
    readback["sockets"][name] = {"bone": s["bone"], "component_cm": vec(comp.translation),
                                 "x_axis": vec(M.get_forward_vector(comp.rotation.rotator())),
                                 "z_axis": vec(M.get_up_vector(comp.rotation.rotator())),
                                 "error_cm": round(err_cm, 5), "error_deg": round(err_deg, 4)}
    if err_cm > 0.1 or err_deg > 0.5:
        fail(f"socket {name} reads back {err_cm:.4f} cm and {err_deg:.3f} deg from the record")

# The guard's first frame: its grip sockets on the interim stance's targets.
stance = tp["guard"]["stance"]
e, y = math.radians(stance["elevation_deg"]), math.radians(stance.get("yaw_deg", 0.0))
targets = {"hand_r_grip": frame_transform(stance["grip_r"], (math.cos(e) * math.cos(y), math.cos(e) * math.sin(y), math.sin(e)),
                                          (-math.sin(e) * math.cos(y), -math.sin(e) * math.sin(y), math.cos(e)))}
if "left_paw" in stance:
    targets["hand_l_grip"] = frame_transform(stance["left_paw"], (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
pose = unreal.AnimPoseExtensions.get_anim_pose_at_time(clips["Guard"], 0.0, unreal.AnimPoseEvaluationOptions())
for name, want in targets.items():
    bone = unreal.AnimPoseExtensions.get_bone_pose(pose, tp["sockets"][name]["bone"], world)
    comp = M.compose_transforms(relative[name], bone)
    err_cm, err_deg = distance(comp, want), angle_between(comp, want)
    readback["guard"][name] = {"component_cm": vec(comp.translation), "target_cm": vec(want.translation),
                               "error_cm": round(err_cm, 4), "error_deg": round(err_deg, 3)}
    if err_cm > 1.0 or err_deg > 2.0:
        fail(f"the guard's {name} is {err_cm:.3f} cm and {err_deg:.2f} deg from its target")

# --- The W00 katana and saya ----------------------------------------------------------------------------------------
assets.make_directory(WEAPONS)
assets.make_directory(WEAPONS + "/Textures")
textures = {}
for channel, entry in build["textures"].items():
    file = ROOT / entry["file"]
    if sha256(file) != entry["sha256"]:
        fail(f"{file.name} differs from build_record.json")
    import_task(file, WEAPONS + "/Textures", file.stem)
    texture = assets.load_asset(WEAPONS + "/Textures/" + file.stem)
    if not isinstance(texture, unreal.Texture2D):
        fail(f"texture {file.stem} failed to import")
    texture.set_editor_property("srgb", channel == "BaseColor")
    if channel == "Normal":
        texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
        texture.set_editor_property("flip_green_channel", False)          # DirectX: Unreal's own convention
    elif channel in ("ORM", "Mask"):
        texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
    assets.save_loaded_asset(texture)
    textures[channel] = texture
if set(textures) != {"BaseColor", "Normal", "ORM", "Mask"}:
    fail(f"W00 maps incomplete: {sorted(textures)}")


def node(material, expression_type, x, y_pos, **properties):
    expression = lib.create_material_expression(material, expression_type, x, y_pos)
    for key, value in properties.items():
        expression.set_editor_property(key, value)
    return expression


master_path = WEAPONS + "/M_W00_Weapon"
master = assets.load_asset(master_path) if assets.does_asset_exist(master_path) else tools.create_asset(
    "M_W00_Weapon", WEAPONS, unreal.Material, unreal.MaterialFactoryNew())
for old in list(lib.get_material_expressions(master)):
    lib.delete_material_expression(master, old)
base = node(master, unreal.MaterialExpressionTextureSampleParameter2D, -900, -400, parameter_name="BaseColorMap",
            texture=textures["BaseColor"])
normal = node(master, unreal.MaterialExpressionTextureSampleParameter2D, -900, -50, parameter_name="NormalMap",
              texture=textures["Normal"])
orm = node(master, unreal.MaterialExpressionTextureSampleParameter2D, -900, 260, parameter_name="ORMMap",
           texture=textures["ORM"])
mask = node(master, unreal.MaterialExpressionTextureSampleParameter2D, -900, 600, parameter_name="MaskMap",
            texture=textures["Mask"])
glow = node(master, unreal.MaterialExpressionScalarParameter, -560, 760, parameter_name="EmissiveStrength",
            default_value=0.0)
for expression, pin, prop in ((base, "RGB", unreal.MaterialProperty.MP_BASE_COLOR),
                              (normal, "RGB", unreal.MaterialProperty.MP_NORMAL),
                              (orm, "R", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION),
                              (orm, "G", unreal.MaterialProperty.MP_ROUGHNESS),
                              (orm, "B", unreal.MaterialProperty.MP_METALLIC)):
    if not lib.connect_material_property(expression, pin, prop):
        fail(f"material output failed: {prop}")
emissive = node(master, unreal.MaterialExpressionMultiply, -300, 680)
if not (lib.connect_material_expressions(mask, "R", emissive, "A")
        and lib.connect_material_expressions(glow, "", emissive, "B")
        and lib.connect_material_property(emissive, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)):
    fail("the W00 master's emissive did not connect")
lib.layout_material_expressions(master)
lib.recompile_material(master)
assets.save_loaded_asset(master)
mi_path = WEAPONS + "/MI_W00_Weapon"
mi = assets.load_asset(mi_path) if assets.does_asset_exist(mi_path) else tools.create_asset(
    "MI_W00_Weapon", WEAPONS, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
lib.set_material_instance_parent(mi, master)
lib.update_material_instance(mi)
assets.save_loaded_asset(mi)

for name, file in weapon_files.items():
    sm_options = unreal.FbxImportUI()
    sm_options.import_mesh = True
    sm_options.import_as_skeletal = False
    sm_options.import_animations = False
    sm_options.import_materials = False
    sm_options.import_textures = False
    sm_options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    data = sm_options.static_mesh_import_data
    data.set_editor_property("combine_meshes", True)
    data.set_editor_property("auto_generate_collision", False)
    data.set_editor_property("convert_scene", True)
    data.set_editor_property("convert_scene_unit", False)          # the FBX is centimetres (UnitScaleFactor 1)
    data.set_editor_property("force_front_x_axis", False)
    data.set_editor_property("import_uniform_scale", 1.0)
    data.set_editor_property("normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS)
    import_task(file, WEAPONS, name, sm_options)
    sm = assets.load_asset(f"{WEAPONS}/{name}")
    if not isinstance(sm, unreal.StaticMesh):
        fail(f"{name} did not import as a static mesh")
    for index in range(len(sm.get_editor_property("static_materials"))):
        sm.set_material(index, mi)
    assets.save_loaded_asset(sm)
    sockets = {}
    for socket_name, blender_m in build["assets"][name]["sockets"].items():
        socket = sm.find_socket(socket_name)
        if socket is None:
            fail(f"{name} lacks its {socket_name} socket")
        want = unreal.Vector(100.0 * blender_m[0], -100.0 * blender_m[1], 100.0 * blender_m[2])
        got = socket.get_editor_property("relative_location")
        err = math.sqrt((got.x - want.x) ** 2 + (got.y - want.y) ** 2 + (got.z - want.z) ** 2)
        rot = socket.get_editor_property("relative_rotation")
        sockets[socket_name] = {"relative_location": vec(got), "build_record_cm": vec(want), "error_cm": round(err, 5),
                                "relative_rotation_pyr": [round(rot.pitch, 4), round(rot.yaw, 4), round(rot.roll, 4)]}
        if err > 0.1:
            fail(f"{name} socket {socket_name} reads back {err:.4f} cm from build_record.json")
    readback["weapons"][name] = {"asset": f"{WEAPONS}/{name}", "sockets": sockets,
                                 "material_slots": len(sm.get_editor_property("static_materials"))}

READBACK.parent.mkdir(parents=True, exist_ok=True)
with open(READBACK, "x", encoding="utf-8") as fh:
    json.dump(readback, fh, indent=1)
print(MARKER, json.dumps({k: {n: v.get("error_cm") for n, v in readback[k].items()} for k in ("sockets", "guard")}))
