"""Import Nyaakoto's first-person bow paw into its own qualification namespace, and read it back.

Run (UE 5.8, headless, by the holder of the shared engine lane), after
create_nyaakoto_fp_paws.py has built the FBX:
  scripts/toolchain/run-editor-script.sh scripts/unreal/import_nyaakoto_fp_paws.py FP_PAWS_UE_READY [log] \
      [-- out=Saved/NyaakotoFPPaws/Unreal/<readback>.json]

It imports into /Game/Generated/Qualification/NyaakotoFPPaws/ only:
- **The mesh:** SM_NyaakotoFP_PawL_Yumi from Production/, checked against
  build_record.json, with its vertex colours (the tabby pattern) and UV0.
- **The textures:** the fur-card atlas, the paw-pad set and the hero fur
  and silk maps, each checked against its own manifest or record.
- **The materials, one per FBX slot:**
  - fur cards: masked and two-sided, shaded as two-sided foliage so
    back-lit fur glows, with the atlas multiplied by the tabby vertex colour
    and darkened toward the root;
  - fur skin and pads, on UV0;
  - the kote's silk, on UV0;
  - lacquer, as clear coat;
  - silk cord, and the mon's gold.
- **Usage flags:** none is used with a skeletal mesh. The paw is static and
  hangs from the bow's Grip_L socket.

It reads back to Saved/NyaakotoFPPaws/Unreal/readback.json (or the out= path,
relative to the project, written exclusively so a rerun never writes over
earlier evidence) the mesh's
triangles, slots, bounds, vertex-colour presence and each material's
compile statistics. Asset readback only: not a render or an admission.
"""

import hashlib
import json
import math
import sys
from pathlib import Path

import unreal

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sora_engine_pin import require_running_engine  # noqa: E402

require_running_engine("Nyaakoto first-person paw import")

ROOT = Path(unreal.Paths.project_dir()).resolve()
SRC = ROOT / "Content/SourceArt/Characters/NyaakotoFirstPersonPaws"
PROD = SRC / "Production"
FUR = SRC / "FurCards"
PADS = SRC / "Textures"
HERO = ROOT / "Content/SourceArt/Characters/Hero/PBR"
DEST = "/Game/Generated/Qualification/NyaakotoFPPaws"
OUT = ROOT / "Saved/NyaakotoFPPaws/Unreal"
OPTS = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
NAME = "SM_NyaakotoFP_PawL_Yumi"
SLOTS = ("M_NyaakotoFP_FurSkin", "M_NyaakotoFP_PawPad", "M_NyaakotoFP_FurCards", "M_NyaakotoFP_KoteSilk",
         "M_NyaakotoFP_KoteUrushi", "M_NyaakotoFP_CordVermilion", "M_NyaakotoFP_MonGold")

tools = unreal.AssetToolsHelpers.get_asset_tools()
assets = unreal.EditorAssetLibrary
lib = unreal.MaterialEditingLibrary
MP = unreal.MaterialProperty


def fail(message):
    raise RuntimeError("fp paws UE: " + message)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rel(path):
    return str(Path(path).resolve().relative_to(ROOT))


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


def texture(path, kind):
    """Import one map: kind is 'colour', 'normal' or 'linear'."""
    import_task(path, DEST + "/Textures", Path(path).stem)
    t = assets.load_asset(DEST + "/Textures/" + Path(path).stem)
    if not isinstance(t, unreal.Texture2D):
        fail(f"texture {Path(path).name} failed to import")
    t.set_editor_property("srgb", kind == "colour")
    if kind == "normal":
        t.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
        t.set_editor_property("flip_green_channel", False)          # DirectX already
    elif kind == "linear":
        t.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
    assets.save_loaded_asset(t)
    return t


# --- Inputs, by hash -------------------------------------------------------

record = json.loads((PROD / "build_record.json").read_text(encoding="utf-8"))
FBX = PROD / f"{NAME}.fbx"
want = record["exports"].get(rel(FBX))
if not want or sha256(FBX) != want["sha256"]:
    fail(f"{FBX.name} differs from its build record")
if list(record["material_slots"]) != list(SLOTS):
    fail(f"the build's slots {record['material_slots']} differ from {list(SLOTS)}")
if not record["checks"]["ok"]:
    fail(f"the build's own checks failed: {record['checks']}")
fur_rec = json.loads((FUR / "manifest.json").read_text(encoding="utf-8"))
for key, m in fur_rec["maps"].items():
    if sha256(FUR / m["file"]) != m["sha256"]:
        fail(f"fur map {m['file']} differs from its manifest")
for path_rel, digest in record["inputs"].items():
    p = ROOT / path_rel
    if p.suffix == ".png" and sha256(p) != digest:
        fail(f"{path_rel} differs from the paw build's inputs")

# A fresh import every run (the yumi rig's second import of 2026-10-25 found a
# reimport over existing assets unreliable). The namespace is this importer's own.
# delete_directory can remove every asset yet keep the folder, and then
# returns False (attempt 1 of 2026-10-25): what must hold is that no asset is left.
if assets.does_directory_exist(DEST):
    assets.delete_directory(DEST)
    for leftover in assets.list_assets(DEST, recursive=True, include_folder=False):
        assets.delete_asset(leftover)
    left = assets.list_assets(DEST, recursive=True, include_folder=False)
    if left:
        fail(f"could not clear {DEST}: {list(left)}")
assets.make_directory(DEST)
assets.make_directory(DEST + "/Textures")
tex = {
    "fur_albedo": texture(FUR / "T_NyaakotoFP_FurCards_Albedo.png", "colour"),
    "fur_normal": texture(FUR / "T_NyaakotoFP_FurCards_NormalDX.png", "normal"),
    "fur_masks": texture(FUR / "T_NyaakotoFP_FurCards_Masks.png", "linear"),
    "skin_albedo": texture(HERO / "T_Nyaakoto_fur_white_Albedo.png", "colour"),
    "skin_normal": texture(HERO / "T_Nyaakoto_fur_white_NormalDX.png", "normal"),
    "pad_albedo": texture(PADS / "T_Nyaakoto_PawPad_Albedo.png", "colour"),
    "pad_normal": texture(PADS / "T_Nyaakoto_PawPad_NormalDX.png", "normal"),
    "pad_orm": texture(PADS / "T_Nyaakoto_PawPad_ORM.png", "linear"),
    "silk_albedo": texture(HERO / "T_Nyaakoto_silk_indigo_Albedo.png", "colour"),
    "silk_normal": texture(HERO / "T_Nyaakoto_silk_indigo_NormalDX.png", "normal"),
    "silk_orm": texture(HERO / "T_Nyaakoto_silk_indigo_ORM.png", "linear"),
}


# --- Materials ---------------------------------------------------------------

def node(material, cls, x, y, **props):
    e = lib.create_material_expression(material, cls, x, y)
    for k, v in props.items():
        e.set_editor_property(k, v)
    return e


def link(a, out_name, b, in_name):
    if not lib.connect_material_expressions(a, out_name, b, in_name):
        fail(f"connection {out_name} -> {in_name} failed")


def out(e, out_name, prop):
    if not lib.connect_material_property(e, out_name, prop):
        fail(f"output {prop} failed")


def fresh(name):
    path = f"{DEST}/{name}"
    m = assets.load_asset(path) if assets.does_asset_exist(path) else tools.create_asset(
        name, DEST, unreal.Material, unreal.MaterialFactoryNew())
    for e in list(lib.get_material_expressions(m)):
        lib.delete_material_expression(m, e)
    return m


def sampler(m, t, x, y, tiling=1.0):
    s = node(m, unreal.MaterialExpressionTextureSample, x, y, texture=t)
    if tiling != 1.0:
        uv = node(m, unreal.MaterialExpressionTextureCoordinate, x - 250, y, u_tiling=tiling, v_tiling=tiling)
        link(uv, "", s, "UVs")
    return s


def mul(m, a, a_out, b, b_out, x, y):
    e = node(m, unreal.MaterialExpressionMultiply, x, y)
    link(a, a_out, e, "A")
    link(b, b_out, e, "B")
    return e


def finish(m):
    lib.layout_material_expressions(m)
    lib.recompile_material(m)
    assets.save_loaded_asset(m)
    return m


def mat_fur_cards():
    m = fresh("M_NyaakotoFP_FurCards")
    m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
    m.set_editor_property("two_sided", True)
    m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE)
    m.set_editor_property("opacity_mask_clip_value", 0.33)
    # v3: dithered coverage, resolved by TSR. Hard-clipped, the sub-pixel hairs
    # broke into dashes and their mips lost coverage, so the coat read as white
    # lace at gameplay distance (Saved/YumiFP/v2).
    m.set_editor_property("dither_opacity_mask", True)
    alb = sampler(m, tex["fur_albedo"], -900, -300)
    nrm = sampler(m, tex["fur_normal"], -900, 100)
    msk = sampler(m, tex["fur_masks"], -900, 400)
    vc = node(m, unreal.MaterialExpressionVertexColor, -900, -600)
    tinted = mul(m, alb, "RGB", vc, "", -600, -400)
    # occlusion between hairs: dark at the root, open by mid-length (Masks R)
    ao = node(m, unreal.MaterialExpressionLinearInterpolate, -600, -150)
    a_lo = node(m, unreal.MaterialExpressionConstant, -800, -200, r=0.70)   # v3: from 0.42 (dark flakes)
    a_hi = node(m, unreal.MaterialExpressionConstant, -800, -120, r=1.0)
    root = node(m, unreal.MaterialExpressionSaturate, -760, -40)
    scale = node(m, unreal.MaterialExpressionMultiply, -820, -40)
    link(msk, "R", scale, "A")
    two = node(m, unreal.MaterialExpressionConstant, -980, 0, r=1.7)
    link(two, "", scale, "B")
    link(scale, "", root, "")
    link(a_lo, "", ao, "A")
    link(a_hi, "", ao, "B")
    link(root, "", ao, "Alpha")
    base = mul(m, tinted, "", ao, "", -350, -300)
    out(base, "", MP.MP_BASE_COLOR)
    out(alb, "A", MP.MP_OPACITY_MASK)
    out(nrm, "RGB", MP.MP_NORMAL)
    rough = node(m, unreal.MaterialExpressionLinearInterpolate, -350, 300)
    link(node(m, unreal.MaterialExpressionConstant, -500, 250, r=0.50), "", rough, "A")   # v3: from 0.38-0.62
    link(node(m, unreal.MaterialExpressionConstant, -500, 330, r=0.70), "", rough, "B")
    link(msk, "G", rough, "Alpha")
    out(rough, "", MP.MP_ROUGHNESS)
    sss = mul(m, base, "", node(m, unreal.MaterialExpressionConstant3Vector, -500, 500,
                                constant=unreal.LinearColor(0.9, 0.82, 0.74, 1.0)), "", -300, 520)
    out(sss, "", MP.MP_SUBSURFACE_COLOR)
    return finish(m)


def mat_fur_skin():
    m = fresh("M_NyaakotoFP_FurSkin")
    alb = sampler(m, tex["skin_albedo"], -800, -200, tiling=6.0)
    nrm = sampler(m, tex["skin_normal"], -800, 150, tiling=6.0)
    vc = node(m, unreal.MaterialExpressionVertexColor, -800, -500)
    tinted = mul(m, alb, "RGB", vc, "", -500, -300)
    # v3: the undercoat at 0.82 (from 0.62), nearly as light as the guard hair:
    # at 0.62 every gap read as a grey fleck.
    under = mul(m, tinted, "", node(m, unreal.MaterialExpressionConstant, -650, -100, r=0.82), "", -300, -250)
    out(under, "", MP.MP_BASE_COLOR)
    out(nrm, "RGB", MP.MP_NORMAL)
    out(node(m, unreal.MaterialExpressionConstant, -300, 50, r=0.78), "", MP.MP_ROUGHNESS)
    return finish(m)


def mat_pad():
    m = fresh("M_NyaakotoFP_PawPad")
    m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_SUBSURFACE)
    alb = sampler(m, tex["pad_albedo"], -800, -200, tiling=4.0)
    nrm = sampler(m, tex["pad_normal"], -800, 150, tiling=4.0)
    orm = sampler(m, tex["pad_orm"], -800, 450, tiling=4.0)
    out(alb, "RGB", MP.MP_BASE_COLOR)
    out(nrm, "RGB", MP.MP_NORMAL)
    out(orm, "G", MP.MP_ROUGHNESS)
    out(orm, "R", MP.MP_AMBIENT_OCCLUSION)
    out(node(m, unreal.MaterialExpressionConstant3Vector, -400, 600,
             constant=unreal.LinearColor(0.75, 0.32, 0.30, 1.0)), "", MP.MP_SUBSURFACE_COLOR)
    return finish(m)


def mat_silk():
    m = fresh("M_NyaakotoFP_KoteSilk")
    m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_CLOTH)
    alb = sampler(m, tex["silk_albedo"], -800, -200, tiling=3.0)
    nrm = sampler(m, tex["silk_normal"], -800, 150, tiling=3.0)
    orm = sampler(m, tex["silk_orm"], -800, 450, tiling=3.0)
    # The hero's indigo on the undyed weave, as the Blender source has it
    # (create_nyaakoto_fp_paws.SILK_INDIGO); v1's lighter tint read white.
    tint = mul(m, alb, "RGB", node(m, unreal.MaterialExpressionConstant3Vector, -650, -450,
                                   constant=unreal.LinearColor(0.016, 0.023, 0.045, 1.0)), "", -450, -300)
    out(tint, "", MP.MP_BASE_COLOR)
    # v5 (root: "smooth sleeve", "glossy sleeve"): the weave's relief half again as strong (its tangent-space x and y
    # scaled, then renormalised), and rougher, 1.15 -> 1.35 of the map, as the Blender source.
    relief = mul(m, nrm, "RGB", node(m, unreal.MaterialExpressionConstant3Vector, -650, 250,
                                     constant=unreal.LinearColor(1.5, 1.5, 1.0, 1.0)), "", -450, 200)
    unit = node(m, unreal.MaterialExpressionNormalize, -300, 200)
    link(relief, "", unit, "")
    out(unit, "", MP.MP_NORMAL)
    # v3 (root: "broad glossy blue cloth"): a little rougher, and a fuzz colour
    # about twice the dyed base (it was six times), since the fuzz amount is
    # pinned at 1.0.
    rough = mul(m, orm, "G", node(m, unreal.MaterialExpressionConstant, -650, 380, r=1.35), "", -450, 400)
    sat = node(m, unreal.MaterialExpressionSaturate, -300, 400)
    link(rough, "", sat, "")
    out(sat, "", MP.MP_ROUGHNESS)
    out(node(m, unreal.MaterialExpressionConstant3Vector, -450, 600,
             constant=unreal.LinearColor(0.035, 0.045, 0.080, 1.0)), "", MP.MP_SUBSURFACE_COLOR)   # the cloth's fuzz colour
    # The fuzz amount is CustomData0, hidden from Python in UE 5.8 (SceneTypes.h:165): it
    # stays at the engine default, 1.0 (MaterialAttributeDefinitionMap.cpp:410).
    return finish(m)


def mat_constant(name, colour, rough, metallic=0.0, clear_coat=None):
    m = fresh(name)
    if clear_coat is not None:
        m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_CLEAR_COAT)
    out(node(m, unreal.MaterialExpressionConstant3Vector, -400, -200, constant=unreal.LinearColor(*colour, 1.0)), "",
        MP.MP_BASE_COLOR)
    out(node(m, unreal.MaterialExpressionConstant, -400, 0, r=rough), "", MP.MP_ROUGHNESS)
    out(node(m, unreal.MaterialExpressionConstant, -400, 100, r=metallic), "", MP.MP_METALLIC)
    # The coat's amount and roughness are CustomData0/1, hidden from Python in UE 5.8
    # (SceneTypes.h:165-166): they stay at the engine defaults, 1.0 and 0.1
    # (MaterialAttributeDefinitionMap.cpp:410-411). The source's lacquer asks
    # 0.65 and 0.10; the readback records which hold.
    return finish(m)


materials = {
    "M_NyaakotoFP_FurSkin": mat_fur_skin(),
    "M_NyaakotoFP_PawPad": mat_pad(),
    "M_NyaakotoFP_FurCards": mat_fur_cards(),
    "M_NyaakotoFP_KoteSilk": mat_silk(),
    # v3: one lobe at 0.25, as the Blender source now has it. The clear coat's
    # amount and roughness can't be set from Python (CustomData0/1 hidden), and
    # at the engine's defaults (1.0 at 0.1) the splints showed mirror highlights
    # (root's review of Saved/YumiFP/v2).
    "M_NyaakotoFP_KoteUrushi": mat_constant("M_NyaakotoFP_KoteUrushi", (0.010, 0.013, 0.030), 0.25),
    "M_NyaakotoFP_CordVermilion": mat_constant("M_NyaakotoFP_CordVermilion", (0.42, 0.035, 0.022), 0.52),
    "M_NyaakotoFP_MonGold": mat_constant("M_NyaakotoFP_MonGold", (1.0, 0.77, 0.36), 0.24, metallic=1.0),
}

# --- The mesh -------------------------------------------------------------------

options = unreal.FbxImportUI()
options.import_mesh = True
options.import_as_skeletal = False
options.import_animations = False
options.import_materials = False
options.import_textures = False
options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
sm = options.static_mesh_import_data
sm.set_editor_property("combine_meshes", True)
sm.set_editor_property("normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS)
sm.set_editor_property("vertex_color_import_option", unreal.VertexColorImportOption.REPLACE)
sm.set_editor_property("generate_lightmap_u_vs", False)
sm.set_editor_property("auto_generate_collision", False)
import_task(FBX, DEST, NAME, options)
mesh = assets.load_asset(f"{DEST}/{NAME}")
if not isinstance(mesh, unreal.StaticMesh):
    fail(f"{NAME} did not import as a static mesh")
bound = []
for index, slot in enumerate(mesh.get_editor_property("static_materials")):
    name = str(slot.get_editor_property("material_slot_name"))
    if name not in materials:
        fail(f"unexpected slot {name}")
    mesh.set_material(index, materials[name])
    bound.append(name)
if sorted(bound) != sorted(SLOTS):
    fail(f"slots {sorted(bound)} differ from {sorted(SLOTS)}")
assets.save_loaded_asset(mesh)
assets.save_directory(DEST, only_if_is_dirty=False, recursive=True)

# --- Readback -----------------------------------------------------------------------

stats = {}
for name, m in materials.items():
    s = lib.get_statistics(m)
    stats[name] = {"pixel_instructions": s.get_editor_property("num_pixel_shader_instructions"),
                   "samplers": s.get_editor_property("num_samplers")}
    if stats[name]["pixel_instructions"] <= 0:
        fail(f"{name} did not compile")
b = mesh.get_bounds()
# The build's socket-frame bounds through the import's axes, Unreal = 100 x (x, -y, z) cm:
# a unit or axis slip shows here before anything is drawn.
lo, hi = record["bounds_m"]["min"], record["bounds_m"]["max"]
want_origin = [50.0 * (lo[0] + hi[0]), -50.0 * (lo[1] + hi[1]), 50.0 * (lo[2] + hi[2])]
want_extent = [50.0 * (hi[i] - lo[i]) for i in range(3)]
got_origin, got_extent = [b.origin.x, b.origin.y, b.origin.z], [b.box_extent.x, b.box_extent.y, b.box_extent.z]
bounds_error = max(abs(g - w) for g, w in zip(got_origin + got_extent, want_origin + want_extent))
if bounds_error > 0.01:
    fail(f"bounds {got_origin} +- {got_extent} cm differ from the build's {want_origin} +- {want_extent} cm")


def card_normal_readback(sample_every=8):
    """The imported fur cards' normals against their own triangles, from the mesh's render data, every
    sample_every-th triangle: each corner normal's angle from its face, as create_nyaakoto_fp_paws.checks measures
    the built arrays and the FBX's round trip.

    v4 bends each card's normals toward the skin, so they sit a few degrees off their faces. A normal the import
    recomputed would sit on its face. The angle is taken from |cos|, so it does not depend on the winding
    convention; same_side_share records the convention."""
    sub = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    sections = [s for s in range(mesh.get_num_sections(0))
                if bound[sub.get_lod_material_slot(mesh, 0, s)] == "M_NyaakotoFP_FurCards"]
    if len(sections) != 1:
        fail(f"the fur cards have {len(sections)} sections in LOD 0")
    verts, tris, normals, _uvs, _tangents = unreal.ProceduralMeshLibrary.get_section_from_static_mesh(
        mesh, 0, sections[0])
    angles, same = [], 0
    for t in range(0, len(tris) // 3, sample_every):
        idx = (tris[3 * t], tris[3 * t + 1], tris[3 * t + 2])
        a, b, c = (verts[i] for i in idx)
        e1, e2 = (b.x - a.x, b.y - a.y, b.z - a.z), (c.x - a.x, c.y - a.y, c.z - a.z)
        fx, fy, fz = e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]
        area2 = math.sqrt(fx * fx + fy * fy + fz * fz)
        if area2 < 1e-12:                                   # cut strands leave degenerate quads
            continue
        for i in idx:
            n = normals[i]
            nn = math.sqrt(n.x * n.x + n.y * n.y + n.z * n.z) or 1.0
            cos = (fx * n.x + fy * n.y + fz * n.z) / (area2 * nn)
            same += cos > 0
            angles.append(math.degrees(math.acos(min(1.0, abs(cos)))))
    if not angles:
        fail("the fur cards' section has no triangle to read back")
    angles.sort()
    return {"section": sections[0], "triangles": len(tris) // 3, "sampled_corners": len(angles),
            "sample_every": sample_every, "mean": sum(angles) / len(angles),
            "p90": angles[int(0.9 * (len(angles) - 1))], "max": angles[-1], "same_side_share": same / len(angles)}


cards = card_normal_readback()
built = record["checks"].get("fbx_fur_corner_normal_from_face_deg")
if built is None:
    fail("build_record.json has no FBX measure of the card normals (a pre-v4 build)")
if abs(cards["mean"] - built["mean"]) > 1.0:
    fail(f"the imported card normals sit {cards['mean']:.2f} deg off their faces on average, the FBX's "
         f"{built['mean']:.2f}: the import did not keep them")


def mesh_query(name, *args):
    """A StaticMeshEditorSubsystem query (UE 5.x), else the older library; None if neither has it."""
    for owner in (unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem) if hasattr(
            unreal, "StaticMeshEditorSubsystem") else None, getattr(unreal, "EditorStaticMeshLibrary", None)):
        if owner is not None and hasattr(owner, name):
            return getattr(owner, name)(mesh, *args)
    return None


readback = {
    "schema_version": 1, "engine": unreal.SystemLibrary.get_engine_version(), "namespace": DEST,
    "source": {rel(FBX): sha256(FBX), rel(PROD / "build_record.json"): sha256(PROD / "build_record.json")},
    "vertices": mesh_query("get_number_verts", 0),
    "lods": mesh_query("get_lod_count"),
    "has_vertex_colours": mesh_query("has_vertex_colors"),
    "slots": bound, "bounds_cm": {"origin": [b.origin.x, b.origin.y, b.origin.z],
                                  "extent": [b.box_extent.x, b.box_extent.y, b.box_extent.z]},
    "bounds_error_cm": round(bounds_error, 6), "materials": stats,
    "fur_card_normals": {"unreal": cards, "fbx": built},
    "custom_data": "engine defaults: UE 5.8 hides CustomData0/1 from Python, so the silk's cloth fuzz is 1.0 "
                   "(asked 0.4; v3 lowers its fuzz colour instead). The kote's lacquer no longer uses clear coat: "
                   "one default-lit lobe at roughness 0.25, as the Blender source has it",
    "build_triangles": record["counts"]["export_triangles"],
    "scope": "asset readback in the editor: not a render, a capture or an admission",
}
if not readback["has_vertex_colours"]:
    fail("the tabby vertex colours did not import")
if "out" in OPTS:
    target = ROOT / OPTS["out"]
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "x", encoding="utf-8") as fh:
        fh.write(json.dumps(readback, indent=1) + "\n")
else:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "readback.json").write_text(json.dumps(readback, indent=1) + "\n")
unreal.log("FP_PAWS_UE_READY " + json.dumps({k: readback[k] for k in ("vertices", "has_vertex_colours", "slots")}))
