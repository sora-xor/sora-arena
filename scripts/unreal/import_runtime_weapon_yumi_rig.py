"""Import the continuous yumi rig into its own qualification namespace, and read it back.

Run (UE 5.8, headless, by the holder of the shared engine lane):
  scripts/toolchain/run-editor-script.sh scripts/unreal/import_runtime_weapon_yumi_rig.py YUMI_RIG_UE_READY [log]

It imports into /Game/Generated/Qualification/W18YumiRig/ only, never the
runtime /Game/Generated/Meshes:
- **The rig:** SK_Weapon_18 and its skeleton, from Rig/SK_Weapon_18.fbx.
  That file is in centimetres, and its header says so (the rig record's
  "fbx"). It imports with no unit conversion and no import scale, and every
  bone must come in at scale 1. Unreal folds the armature node into the root
  bone, so any factor on a node, or on the import, became every bone's scale:
  imports 2-6 of 2026-10-25 gave 100 and 10000.
  The take A_Weapon_18_Draw comes in at its own 10 fps, with no resampling
  and no key reduction. Between keys Unreal blends the keys themselves;
  resampling would bake in the FBX's Euler curves instead.
- **The arrow:** SM_Weapon_18_Ya, with the Nock and Tip sockets its FBX
  carries (SOCKET_Nock, SOCKET_Tip), checked against build_record.json.
- **The material:** the four W18 maps, checked against build_record.json, a
  master M_W18_Weapon (masked, BaseColor alpha) and its instances. The vanes'
  instance is two-sided.
- **The sockets:** the rig record's (schema 3) on SK_Weapon_18, each on its
  bone. Each is placed from its mesh-frame point through the import's axes,
  Unreal = 100 x (x, -y, z) cm from Blender metres (viewmodels.json
  socket_frame), and keeps the mesh frame's axes.

It reads back, to Saved/YumiRig/Unreal/W18_rig_unreal_readback.json:
- the skeleton's bones and reference pose, against the rig record's heads;
- the take's length, frame count and rate, and its compression codec and
  the settings that bound its error;
- every bone's component-space transform (translation, rotation, scale) at
  the take's keys, quarter points and midpoints, from the raw and from the
  compressed animation, which test_yumi_draw compares with yumi_draw's
  interpolation. Compilation is finished first: without compressed data
  Unreal would silently evaluate the raw data instead;
- the sockets' component-space points at those times.

Asset readback only: not a render, a capture or a gameplay admission.
"""

import hashlib
import json
import math
import sys
from pathlib import Path

import unreal

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sora_engine_pin import require_running_engine  # noqa: E402

require_running_engine("Yumi rig import")

ROOT = Path(unreal.Paths.project_dir()).resolve()
SRC = ROOT / "Content/SourceArt/Weapons/Runtime/W18_Yumi"
RIG = SRC / "Rig"
DEST = "/Game/Generated/Qualification/W18YumiRig"
OUT = ROOT / "Saved/YumiRig/Unreal"
RIG_SCHEMA = "sora-yumi-rig-check-v3"           # yumi_draw.RIG_SCHEMA
TAKE_FPS = 10
QUARTERS = (0.0, 0.25, 0.5, 0.75)
SCALE_TOL = 1e-5            # a bone's scale off 1 beyond float32 noise (1.2e-7); a unit factor gives 100
# The settings that bound a codec's error, read back where the codec has them.
CODEC_SETTINGS = {"error_threshold": "ErrorThreshold", "default_virtual_vertex_distance": "DefaultVirtualVertexDistance",
                  "safe_virtual_vertex_distance": "SafeVirtualVertexDistance", "compression_level": "CompressionLevel",
                  "keyframe_stripping_proportion": "KeyframeStrippingProportion",
                  "keyframe_stripping_threshold": "KeyframeStrippingThreshold"}
# W18 bakes every part into one atlas material, one slot per mesh (the first
# import's readback, 2026-10-25: "M_Weapon_18"). The arrow's slot takes the
# two-sided instance for its alpha-cut vanes; the bow's is one-sided.
BOW_SLOTS = {"M_Weapon_18"}
ARROW_SLOTS = {"M_Weapon_18"}

tools = unreal.AssetToolsHelpers.get_asset_tools()
assets = unreal.EditorAssetLibrary
lib = unreal.MaterialEditingLibrary


def fail(message):
    raise RuntimeError("yumi rig UE: " + message)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rel(path):
    return str(Path(path).resolve().relative_to(ROOT))


def ue_point(p):
    """Blender metres (+Y the wielder's left) to Unreal centimetres: the FBX import flips Y."""
    return unreal.Vector(100.0 * p[0], -100.0 * p[1], 100.0 * p[2])


def vec(v):
    return [round(v.x, 6), round(v.y, 6), round(v.z, 6)]


def row(transform):
    """[x, y, z, qx, qy, qz, qw, sx, sy, sz] of a transform, as read back."""
    s = transform.scale3d
    return vec(transform.translation) + [round(c, 9) for c in quat_of(transform)] + [
        round(s.x, 9), round(s.y, 9), round(s.z, 9)]


def quat_rotate(q, v):
    """Rotate (x, y, z) by the unit quaternion q = (x, y, z, w)."""
    qx, qy, qz, qw = q
    tx = 2.0 * (qy * v[2] - qz * v[1])
    ty = 2.0 * (qz * v[0] - qx * v[2])
    tz = 2.0 * (qx * v[1] - qy * v[0])
    return (v[0] + qw * tx + (qy * tz - qz * ty),
            v[1] + qw * ty + (qz * tx - qx * tz),
            v[2] + qw * tz + (qx * ty - qy * tx))


def quat_of(transform):
    r = transform.rotation
    return (r.x, r.y, r.z, r.w)


def inverse_point(transform, p):
    """transform^-1 applied to a component-space point (uniform unit scale required)."""
    s = transform.scale3d
    if max(abs(s.x - 1.0), abs(s.y - 1.0), abs(s.z - 1.0)) > 1e-5:
        fail(f"a bone's reference transform has scale {vec(s)}")
    t = transform.translation
    qx, qy, qz, qw = quat_of(transform)
    return quat_rotate((-qx, -qy, -qz, qw), (p.x - t.x, p.y - t.y, p.z - t.z))


def require_api(owner, *names):
    missing = [n for n in names if not hasattr(owner, n)]
    if missing:
        fail(f"{getattr(owner, '__name__', owner)} lacks {missing}")


def finish_compilation():
    """Wait for every async asset build (skeletal meshes build asynchronously in UE 5.8)."""
    unreal.SystemLibrary.execute_console_command(
        unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world(),
        "Editor.AsyncAssetCompilationFinishAll")


def bound_materials(skeletal_mesh):
    """Each bow slot's bound material, by path (None if unbound)."""
    out = {}
    for slot in skeletal_mesh.get_editor_property("materials"):
        mi = slot.get_editor_property("material_interface")
        out[str(slot.get_editor_property("material_slot_name"))] = mi.get_path_name() if mi else None
    return out


def package_file(path_name):
    """The .uasset holding a content object, from its package path ("/Plugin/..." or "/Game/...")."""
    root, _, rest = path_name.split(".")[0].lstrip("/").partition("/")
    if root == "Game":
        return ROOT / "Content" / (rest + ".uasset")
    for base in (unreal.Paths.project_plugins_dir(), unreal.Paths.engine_plugins_dir()):
        for plugin in Path(unreal.Paths.convert_relative_path_to_full(base)).rglob(root + ".uplugin"):
            return plugin.parent / "Content" / (rest + ".uasset")
    return None


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


# --- Inputs, by hash -------------------------------------------------------

record = json.loads((RIG / "rig_record.json").read_text(encoding="utf-8"))
build = json.loads((SRC / "build_record.json").read_text(encoding="utf-8"))
if record.get("schema_version") != 3 or record.get("check_geometry_schema") != RIG_SCHEMA:
    fail(f"the rig record is not schema 3 / {RIG_SCHEMA}; rebuild the rig with create_runtime_weapon_yumi_rig.py")
FBX = RIG / "SK_Weapon_18.fbx"
want = record["exports"].get(rel(FBX))
if not want or sha256(FBX) != want["sha256"] or FBX.stat().st_size != want["bytes"]:
    fail("SK_Weapon_18.fbx differs from its rig record")
fbx_units = record.get("fbx", {})
if fbx_units.get("units") != "centimetres" or fbx_units.get("read_back", {}).get("unit_scale_factor") != 1.0:
    fail("the rig record does not declare a centimetre FBX (unit 1); rebuild with create_runtime_weapon_yumi_rig.py")
ARROW_FBX = SRC / "SM_Weapon_18_Ya.fbx"
if sha256(ARROW_FBX) != record["inputs"].get(rel(ARROW_FBX)):
    fail("SM_Weapon_18_Ya.fbx differs from the rig record's input")
for name in ("Grip_L", "Muzzle", "Grip_R", "String_Upper", "String_Lower"):
    s = record["sockets"].get(name, {})
    if not {"bone", "mesh_frame_m", "bone_local_m", "bone_bind_matrix"} <= set(s):
        fail(f"socket {name} lacks its frames in the rig record")

# A fresh import every run: over an existing SK_Weapon_18, replace_existing
# reimports the mesh and skips the take (the second run of 2026-10-25 found
# no animation). The namespace is this importer's own and git-ignored.
if assets.does_directory_exist(DEST):
    if not assets.delete_directory(DEST):
        fail(f"could not clear {DEST}")
assets.make_directory(DEST)
assets.make_directory(DEST + "/Textures")

# --- Textures and material -------------------------------------------------

textures = {}
for channel, entry in build["textures"].items():
    file = ROOT / entry["file"]
    if sha256(file) != entry["sha256"]:
        fail(f"{file.name} differs from build_record.json")
    import_task(file, DEST + "/Textures", file.stem)
    texture = assets.load_asset(DEST + "/Textures/" + file.stem)
    if not isinstance(texture, unreal.Texture2D):
        fail(f"texture {file.stem} failed to import")
    texture.set_editor_property("srgb", channel == "BaseColor")
    if channel == "Normal":
        texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
        texture.set_editor_property("flip_green_channel", False)        # DirectX: Unreal's own convention
    elif channel in ("ORM", "Mask"):
        texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
    assets.save_loaded_asset(texture)
    textures[channel] = texture
if set(textures) != {"BaseColor", "Normal", "ORM", "Mask"}:
    fail(f"W18 maps incomplete: {sorted(textures)}")


def node(material, expression_type, x, y, **properties):
    expression = lib.create_material_expression(material, expression_type, x, y)
    for name, value in properties.items():
        expression.set_editor_property(name, value)
    return expression


def link(a, output, b, pin):
    if not lib.connect_material_expressions(a, output, b, pin):
        fail(f"material connection failed: {output} -> {pin}")


def output(expression, name, prop):
    if not lib.connect_material_property(expression, name, prop):
        fail(f"material output failed: {prop}")


master_name = "M_W18_Weapon"
master_path = DEST + "/" + master_name
master = assets.load_asset(master_path) if assets.does_asset_exist(master_path) else tools.create_asset(
    master_name, DEST, unreal.Material, unreal.MaterialFactoryNew())
for old in list(lib.get_material_expressions(master)):
    lib.delete_material_expression(master, old)
master.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
master.set_editor_property("opacity_mask_clip_value", 0.5)
master.set_editor_property("used_with_skeletal_mesh", True)
base = node(master, unreal.MaterialExpressionTextureSampleParameter2D, -900, -400,
            parameter_name="BaseColorMap", texture=textures["BaseColor"])
normal = node(master, unreal.MaterialExpressionTextureSampleParameter2D, -900, -50,
              parameter_name="NormalMap", texture=textures["Normal"])
orm = node(master, unreal.MaterialExpressionTextureSampleParameter2D, -900, 260,
           parameter_name="ORMMap", texture=textures["ORM"])
mask = node(master, unreal.MaterialExpressionTextureSampleParameter2D, -900, 600,
            parameter_name="MaskMap", texture=textures["Mask"])
glow = node(master, unreal.MaterialExpressionScalarParameter, -560, 760, parameter_name="EmissiveStrength",
            default_value=0.0)
output(base, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
output(base, "A", unreal.MaterialProperty.MP_OPACITY_MASK)
output(normal, "RGB", unreal.MaterialProperty.MP_NORMAL)
output(orm, "R", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
output(orm, "G", unreal.MaterialProperty.MP_ROUGHNESS)
output(orm, "B", unreal.MaterialProperty.MP_METALLIC)
emissive = node(master, unreal.MaterialExpressionMultiply, -300, 680)
link(mask, "R", emissive, "A")
link(glow, "", emissive, "B")
output(emissive, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
lib.layout_material_expressions(master)
lib.recompile_material(master)
assets.save_loaded_asset(master)
if {str(n) for n in lib.get_texture_parameter_names(master)} != {"BaseColorMap", "NormalMap", "ORMMap", "MaskMap"}:
    fail("the W18 master lost a map parameter")

instances = {}
for name, two_sided in (("MI_W18_Weapon", False), ("MI_W18_Hane", True)):
    path = DEST + "/" + name
    mi = assets.load_asset(path) if assets.does_asset_exist(path) else tools.create_asset(
        name, DEST, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    lib.set_material_instance_parent(mi, master)
    overrides = mi.get_editor_property("base_property_overrides")
    overrides.set_editor_property("override_two_sided", two_sided)
    overrides.set_editor_property("two_sided", two_sided)
    mi.set_editor_property("base_property_overrides", overrides)
    lib.update_material_instance(mi)
    assets.save_loaded_asset(mi)
    instances[name] = mi


def instance_for(slot, arrow=False):
    return instances["MI_W18_Hane" if arrow else "MI_W18_Weapon"]


# --- The rig and its take ---------------------------------------------------

options = unreal.FbxImportUI()
options.import_mesh = True
options.import_as_skeletal = True
options.import_animations = True
options.import_materials = False
options.import_textures = False
options.create_physics_asset = False
options.mesh_type_to_import = unreal.FBXImportType.FBXIT_SKELETAL_MESH
sk_data = options.skeletal_mesh_import_data
sk_data.set_editor_property("import_morph_targets", False)
sk_data.set_editor_property("use_t0_as_ref_pose", False)
sk_data.set_editor_property("convert_scene", True)
# The FBX is centimetres already, so nothing is converted or scaled. A unit
# conversion lands on the root node, and import_uniform_scale multiplies the
# root bone too (FbxSkeletalMeshImport.cpp:1406-1415 in UE 5.8.3), so either
# would scale every bone (imports 2-6 of 2026-10-25).
sk_data.set_editor_property("convert_scene_unit", False)
sk_data.set_editor_property("force_front_x_axis", False)
sk_data.set_editor_property("import_uniform_scale", 1.0)
sk_data.set_editor_property("normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS)
anim_data = options.anim_sequence_import_data
anim_data.set_editor_property("animation_length", unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
anim_data.set_editor_property("use_default_sample_rate", False)
anim_data.set_editor_property("custom_sample_rate", TAKE_FPS)
anim_data.set_editor_property("remove_redundant_keys", False)
anim_data.set_editor_property("import_bone_tracks", True)
anim_data.set_editor_property("convert_scene_unit", False)
anim_data.set_editor_property("import_uniform_scale", 1.0)
task = import_task(FBX, DEST, "SK_Weapon_18", options)
mesh = assets.load_asset(DEST + "/SK_Weapon_18")
if not isinstance(mesh, unreal.SkeletalMesh):
    fail("SK_Weapon_18 did not import as a skeletal mesh")
skeleton = mesh.get_editor_property("skeleton")
anim_target = DEST + "/A_Weapon_18_Draw"
imported_anims = [p for p in task.imported_object_paths if isinstance(assets.load_asset(p), unreal.AnimSequence)]
if len(imported_anims) != 1:
    fail(f"expected one take, got {imported_anims}")
if imported_anims[0].split(".")[0] != anim_target:
    if assets.does_asset_exist(anim_target):
        assets.delete_asset(anim_target)
    if not assets.rename_asset(imported_anims[0], anim_target):
        fail("cannot name the take A_Weapon_18_Draw")
anim = assets.load_asset(anim_target)

# The bow's slots go through SetMaterials (SkeletalMesh.h:951-952), once the
# mesh's async build has finished. The Materials array is transient and
# serialized by hand (SkeletalMesh.cpp:2058), and its setter first waits for
# the async build to release it (SkeletalMesh.cpp:733-740). The first imports
# wrote it with set_editor_property while the build ran, and the saved package
# bound the slot to /Engine/EngineMaterials/WorldGridMaterial and never
# referenced MI_W18_Weapon. First-person capture attempt 2 (Saved/YumiFP/v2)
# drew the bow in that grey grid.
require_api(unreal.SkeletalMesh, "set_materials")
finish_compilation()
slots = mesh.get_editor_property("materials")
slot_names = []
for slot in slots:
    name = str(slot.get_editor_property("material_slot_name"))
    if name not in BOW_SLOTS:
        fail(f"unexpected bow material slot {name}")
    slot.set_editor_property("material_interface", instance_for(name))
    slot_names.append(name)
mesh.set_materials(slots)
if set(slot_names) != BOW_SLOTS:
    fail(f"bow slots {sorted(slot_names)} differ from {sorted(BOW_SLOTS)}")
WANT_BOW_MATERIALS = {name: instance_for(name).get_path_name() for name in BOW_SLOTS}
if bound_materials(mesh) != WANT_BOW_MATERIALS:
    fail(f"bow slots bound {bound_materials(mesh)} after SetMaterials, not {WANT_BOW_MATERIALS}")

# --- Sockets, from the reference pose ---------------------------------------

require_api(unreal.AnimPoseExtensions, "get_reference_pose", "get_ref_bone_pose", "get_anim_pose_at_time",
            "get_bone_pose", "get_bone_names")
ref = unreal.AnimPoseExtensions.get_reference_pose(skeleton)
names = [str(n) for n in unreal.AnimPoseExtensions.get_bone_names(ref)]
want_names = [b["name"] for b in record["bones"]]
if sorted(names) != sorted(want_names):
    fail(f"skeleton bones {names} differ from the rig record's {want_names}")
world = unreal.AnimPoseSpaces.WORLD
ref_bones = {n: unreal.AnimPoseExtensions.get_ref_bone_pose(ref, n, world) for n in names}
# Every bone's reference transform in both spaces, and the mesh's bounds,
# written before any check can fail, so a failing import still explains itself.
_local = unreal.AnimPoseSpaces.LOCAL
_bounds = mesh.get_bounds()
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "reference_diagnostic.json").write_text(json.dumps({
    "bones": {n: {"world_t": vec(ref_bones[n].translation), "world_s": vec(ref_bones[n].scale3d),
                  "local_t": vec(unreal.AnimPoseExtensions.get_ref_bone_pose(ref, n, _local).translation),
                  "local_s": vec(unreal.AnimPoseExtensions.get_ref_bone_pose(ref, n, _local).scale3d)}
              for n in names},
    "mesh_bounds_cm": {"origin": vec(_bounds.origin), "extent": vec(_bounds.box_extent)}}, indent=1) + "\n")
# Every bone at scale 1, in both spaces, before anything is measured from them.
scale_dev, scale_bone = max(
    (max(abs(c - 1.0) for c in (T.scale3d.x, T.scale3d.y, T.scale3d.z)), n)
    for n in names for T in (ref_bones[n], unreal.AnimPoseExtensions.get_ref_bone_pose(ref, n, _local)))
if scale_dev > SCALE_TOL:
    fail(f"bone {scale_bone}'s reference scale is {scale_dev:.3g} off 1; every bone must import at scale 1")
head_error = max(math.dist(vec(ref_bones[b["name"]].translation), vec(ue_point(b["head"]))) for b in record["bones"])
if head_error > 1e-3:
    fail(f"reference bone heads are {head_error:.2e} cm from the rig record through 100 x (x, -y, z)")
for existing in [mesh.get_socket_by_index(i) for i in range(mesh.num_sockets())] if hasattr(mesh, "num_sockets") else []:
    if existing and str(existing.get_editor_property("socket_name")) in record["sockets"]:
        fail("SK_Weapon_18 already has sockets; reimport replaced the mesh, so this cannot happen")
# UE 5.8 keeps a mesh socket's name and bone read-only to scripts (import 7 of
# 2026-10-25): add_socket names a fresh socket ("Socket"), then rename_socket
# and set_socket_parent set them. Each socket is read back from the mesh.
require_api(unreal.SkeletalMeshSocket, "set_socket_parent")
require_api(unreal.SkeletalMeshEditorSubsystem, "rename_socket")
sockets = {}
for name, s in record["sockets"].items():
    bone_ref = ref_bones[s["bone"]]
    p = ue_point(s["mesh_frame_m"])
    local = inverse_point(bone_ref, p)
    qx, qy, qz, qw = quat_of(bone_ref)
    socket = unreal.SkeletalMeshSocket(mesh)
    mesh.add_socket(socket, False)
    placeholder = socket.get_editor_property("socket_name")
    if not unreal.SkeletalMeshEditorSubsystem.rename_socket(mesh, placeholder, name):
        fail(f"cannot rename socket {placeholder} to {name}")
    socket.set_socket_parent(mesh, s["bone"])
    socket.set_editor_property("relative_location", unreal.Vector(*local))
    socket.set_editor_property("relative_rotation", unreal.Quat(-qx, -qy, -qz, qw).rotator())
    socket.set_editor_property("relative_scale", unreal.Vector(1.0, 1.0, 1.0))
    got = mesh.find_socket(name)
    if (got is None or str(got.get_editor_property("bone_name")) != s["bone"]
            or math.dist(vec(got.get_editor_property("relative_location")), vec(unreal.Vector(*local))) > 1e-4):
        fail(f"socket {name} did not read back on {s['bone']} at {[round(c, 6) for c in local]}")
    sockets[name] = {"bone": str(got.get_editor_property("bone_name")),
                     "relative_location_cm": vec(got.get_editor_property("relative_location")),
                     "relative_rotation": str(got.get_editor_property("relative_rotation")),
                     "component_cm": vec(p), "mesh_frame_m": s["mesh_frame_m"]}
finish_compilation()
if bound_materials(mesh) != WANT_BOW_MATERIALS:
    fail(f"bow slots bound {bound_materials(mesh)} after the sockets, not {WANT_BOW_MATERIALS}")
assets.save_loaded_asset(mesh)
# The package on disk must name the instance and no longer the engine's default.
_package = package_file(mesh.get_path_name())
_bytes = _package.read_bytes()
bow_package_binds = {"package": rel(_package), "names_instance": all(
    v.split(".")[0].encode() in _bytes for v in WANT_BOW_MATERIALS.values()),
    "names_world_grid": b"/Engine/EngineMaterials/WorldGridMaterial" in _bytes}
if not bow_package_binds["names_instance"] or bow_package_binds["names_world_grid"]:
    fail(f"the saved SK_Weapon_18 package does not bind MI_W18_Weapon: {bow_package_binds}")

# --- The arrow ---------------------------------------------------------------

arrow_options = unreal.FbxImportUI()
arrow_options.import_mesh = True
arrow_options.import_as_skeletal = False
arrow_options.import_animations = False
arrow_options.import_materials = False
arrow_options.import_textures = False
arrow_options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
arrow_options.static_mesh_import_data.set_editor_property("combine_meshes", True)
arrow_options.static_mesh_import_data.set_editor_property(
    "normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS)
import_task(ARROW_FBX, DEST, "SM_Weapon_18_Ya", arrow_options)
arrow = assets.load_asset(DEST + "/SM_Weapon_18_Ya")
if not isinstance(arrow, unreal.StaticMesh):
    fail("SM_Weapon_18_Ya did not import")
arrow_slots = []
for index, slot in enumerate(arrow.get_editor_property("static_materials")):
    name = str(slot.get_editor_property("material_slot_name"))
    if name not in ARROW_SLOTS:
        fail(f"unexpected arrow material slot {name}")
    arrow.set_material(index, instance_for(name, arrow=True))
    arrow_slots.append(name)
# The arrow's FBX carries its sockets as SOCKET_Nock and SOCKET_Tip, which the
# static mesh import makes into sockets (a socket's name is read-only to
# scripts in UE 5.8). Each must sit where the build record puts it.
arrow_sockets = {}
for name, p in build["assets"]["SM_Weapon_18_Ya"]["sockets"].items():
    socket = arrow.find_socket(name)
    if socket is None:
        fail(f"the arrow's socket {name} (SOCKET_{name} in its FBX) did not import")
    got = vec(socket.get_editor_property("relative_location"))
    if math.dist(got, vec(ue_point(p))) > 1e-3:
        fail(f"the arrow's socket {name} imported at {got} cm, the build record's {vec(ue_point(p))}")
    arrow_sockets[name] = got
assets.save_loaded_asset(arrow)
assets.save_directory(DEST, only_if_is_dirty=False, recursive=True)

# --- Readback and playback -------------------------------------------------------

times = [k / TAKE_FPS + q / TAKE_FPS for k in range(TAKE_FPS) for q in QUARTERS] + [1.0]
# Compressed data first: UAnimSequence::ShouldUseRawDataForPoseExtraction
# evaluates the raw data, silently, while the compressed data is missing.
finish_compilation()
samples = {}
for label in ("RAW", "COMPRESSED"):
    if not hasattr(unreal.AnimDataEvalType, label):
        samples[label] = None
        continue
    opts = unreal.AnimPoseEvaluationOptions()
    opts.set_editor_property("evaluation_type", getattr(unreal.AnimDataEvalType, label))
    rows = []
    for t in times:
        pose = unreal.AnimPoseExtensions.get_anim_pose_at_time(anim, t, opts)
        rows.append({"t": t, "bones": {n: row(unreal.AnimPoseExtensions.get_bone_pose(pose, n, world))
                                       for n in want_names}})
    samples[label] = rows


def setting(value):
    """A codec setting as JSON: numbers as they are, per-platform values by their default."""
    if isinstance(value, (bool, int, float)):
        return value
    try:
        return value.get_editor_property("default")
    except Exception:
        return str(value)


def compression_info():
    """The bone compression settings and each codec with the settings that bound its error.

    A setting Python cannot read is recorded with its error, never skipped. The
    settings asset's package is also searched for each setting's property name:
    a package that serializes none of them leaves every codec setting at its
    class default (tagged properties are written only when they differ)."""
    settings = unreal.AnimationLibrary.get_bone_compression_settings(anim)
    codecs = []
    for codec in settings.get_editor_property("codecs"):
        entry = {"class": codec.get_class().get_name(), "path": codec.get_path_name(),
                 "python_type": type(codec).__name__}
        for name in CODEC_SETTINGS:
            try:
                entry[name] = setting(codec.get_editor_property(name))
            except Exception as error:
                entry[name] = f"unreadable: {error}"
        codecs.append(entry)
    package = package_file(settings.get_path_name())
    serialized = None
    if package is not None and package.is_file():
        data = package.read_bytes()
        serialized = {"file": str(package), "sha256": hashlib.sha256(data).hexdigest(),
                      "settings_serialized": sorted(prop for prop in CODEC_SETTINGS.values() if prop.encode() in data)}
    return {"settings": settings.get_path_name(), "codecs": codecs, "package": serialized}


def anim_info():
    """The take as imported. UE 5.8 exposes no frame-rate getter (the probe of
    2026-10-25): the rate is the frame count over the sequence length."""
    info = {}
    for key, call in (("length_s", lambda: unreal.AnimationLibrary.get_sequence_length(anim)),
                      ("frames", lambda: unreal.AnimationLibrary.get_num_frames(anim)),
                      ("keys", lambda: unreal.AnimationLibrary.get_num_keys(anim)),
                      ("compression", compression_info),
                      ("interpolation", lambda: str(anim.get_editor_property("interpolation")))):
        try:
            info[key] = call()
        except Exception as error:                                      # recorded, not hidden
            info[key] = f"unavailable: {error}"
    if isinstance(info.get("length_s"), float) and isinstance(info.get("frames"), int) and info["length_s"] > 0:
        info["frames_per_s"] = round(info["frames"] / info["length_s"], 6)
    return info


readback = {
    "schema_version": 1, "engine": unreal.SystemLibrary.get_engine_version(), "namespace": DEST,
    "sources": {rel(FBX): sha256(FBX), rel(ARROW_FBX): sha256(ARROW_FBX), rel(RIG / "rig_record.json"):
                sha256(RIG / "rig_record.json")},
    "axes": "Unreal = 100 x (x, -y, z) cm from Blender metres (viewmodels.json socket_frame); verified on the "
            "bone heads' x and z, which all have y = 0, so the y sign is the contract's",
    "reference_head_error_cm": round(head_error, 7), "reference_scale_max_dev": scale_dev, "scale_tolerance": SCALE_TOL,
    "fbx_units": fbx_units.get("units"),
    "bones": want_names, "skeleton_bones": names,
    "rows": "[x, y, z, qx, qy, qz, qw, sx, sy, sz], component space (cm)",
    "reference_cm": {n: row(ref_bones[n]) for n in names},
    "bow_slots": slot_names, "bow_materials": bound_materials(mesh), "bow_package_binds": bow_package_binds,
    "arrow_slots": arrow_slots, "sockets": sockets, "arrow_sockets_cm": arrow_sockets,
    "take": anim_info(), "times_s": times, "samples": samples,
    "scope": "asset readback in the editor (-nullrhi): not a render, a capture or a gameplay admission",
}
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "W18_rig_unreal_readback.json").write_text(json.dumps(readback, indent=1) + "\n")
unreal.log("YUMI_RIG_UE_READY " + json.dumps({"bones": len(names), "sockets": len(sockets), "arrow_sockets":
                                               len(arrow_sockets), "times": len(times),
                                               "evaluations": [k for k, v in samples.items() if v],
                                               "take": readback["take"], "head_error_cm": round(head_error, 7)}))
