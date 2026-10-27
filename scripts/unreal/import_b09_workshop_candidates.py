"""Import the b09 lantern workshop's candidate meshes (create_b09_workshop_craft.py) into Unreal, with candidate
materials, and read them back. These are separate candidate assets under /Game/Generated/Candidates/B09Workshop:
nothing is adopted or placed in a game level.

**Textures** (candidates, from sources already in the tree):
- wood: `wood_planks_dirt` (Poly Haven, CC0), its albedo, DirectX normal and ARM (as ORM);
- washi: `paper_0017` (the project's ShojiPaperArtReview), its colour, DirectX normal and roughness, and the
  translucency map. That map is an art estimate, **not a measured transmission**: chapter-03 section 5 still requires
  measuring it.

**Materials:**
- **The opaque slots:** instances of the project's M_Nyaakoto_PBR, with the wood or neutral maps, a tint, and
  roughness and metallic scales.
  - Placeholders: the bamboo, iron, ceramic, cord, shell and gauge colours are tints over the neutral maps.
- **The washi:** M_B09_WashiCandidate, built here: two-sided foliage (light through paper), masked, with paper maps
  and three parameters on UV1 (`Reveal`):
  - **PasteReveal:** shows the gore up to that height fraction;
  - **OilWet:** darkens and glosses from the top down;
  - **Glow:** emission through the paper, scaled by the translucency estimate.

**Meshes:**
- Each FBX becomes a static mesh, with no import collision and its SOCKET_ empties as sockets. Each slot is bound to
  its candidate instance by name.
- **Weapon 7 for review only:** this project has no imported copy, so the in-tree SM_Weapon_07.fbx (with its maps)
  comes in as `SM_B09_Weapon07_ReviewStandIn`, for the shell bench's capture. It is not the game's asset, and its
  Muzzle is read back to check its axes.

**Readback (a new file).** Per mesh, against the build's manifest:
- triangles and bounds (cm);
- the sockets' locations (within 0.05 cm), axes (forward and up within 0.001) and unit scale, which checks the
  Blender-to-Unreal axes end to end, socket rotations included (fbx_socket_export's convention; the weapon kit's -Y
  forward would turn each socket 180 deg about Y);
- two UV channels, no simple collision, and every slot bound.

Run (lane holder; materials compile with a renderer):
  scripts/toolchain/run-editor-script.sh --rhi scripts/unreal/import_b09_workshop_candidates.py B09_CANDIDATES_IMPORTED \\
      <log> -- --base B09Workshop_<run> --build Saved/B09Workshop/Candidates/<build> --readback Saved/B09Workshop/Unreal/<new>.json
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import unreal

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sora_engine_pin import require_running_engine  # noqa: E402

require_running_engine("b09 workshop candidates")

ROOT = Path(unreal.Paths.project_dir()).resolve()
ASSETS = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
LIB = unreal.MaterialEditingLibrary
SMES = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
CANDIDATES = "/Game/Generated/Candidates"
BASE = MESHES = MATS = TEX = None    # main(): CANDIDATES/<--base>, new for each run, so a failed run's assets stay
PBR = "/Game/Generated/Characters/Nyaakoto/M_Nyaakoto_PBR"
NEUTRAL = "/Game/Generated/Characters/Nyaakoto/Textures/T_Nyaakoto_neutral_{}"
MARKER = "B09_CANDIDATES_IMPORTED"
SOCKET_TOL_CM = 0.05
SOCKET_TOL_AXIS = 1e-3
W07 = "Content/SourceArt/Weapons/Runtime/W07_GrenadeLauncher"
PH = "Content/SourceArt/Environment/PolyHaven/wood_planks_dirt"
PAPER = "Content/SourceArt/Environment/ShojiPaperArtReview/Textures"
TEXTURES = {
    "T_B09_Wood_Albedo": (f"{PH}/wood_planks_dirt_diff_4k.jpg", "color"),
    "T_B09_Wood_NormalDX": (f"{PH}/wood_planks_dirt_nor_dx_4k.png", "normal"),
    "T_B09_Wood_ORM": (f"{PH}/wood_planks_dirt_arm_4k.png", "masks"),
    "T_B09_Washi_Albedo": (f"{PAPER}/paper_0017_color_2k.jpg", "color"),
    "T_B09_Washi_NormalDX": (f"{PAPER}/paper_0017_normal_directx_2k.png", "normal"),
    "T_B09_Washi_Roughness": (f"{PAPER}/paper_0017_roughness_2k.jpg", "linear"),
    "T_B09_Washi_TranslucencyEstimate": (f"{PAPER}/paper_0017_translucency_ART_ESTIMATE_2k.png", "linear"),
    "T_B09_W07_BaseColor": (f"{W07}/T_Weapon_07_BaseColor.png", "color"),
    "T_B09_W07_NormalDX": (f"{W07}/T_Weapon_07_NormalDX.png", "normal"),
    "T_B09_W07_ORM": (f"{W07}/T_Weapon_07_ORM.png", "masks"),
}
# slot: (maps, tint, roughness scale, metallic scale)
OPAQUE = {
    "M_B09_TimberBench": ("wood", (0.62, 0.48, 0.36), 1.0, 0.0),
    "M_B09_TimberForm": ("wood", (0.95, 0.80, 0.62), 0.9, 0.0),
    "M_B09_Bamboo": ("neutral", (0.78, 0.70, 0.43), 0.55, 0.0),
    "M_B09_RimLacquer": ("neutral", (0.05, 0.045, 0.045), 0.25, 0.0),
    "M_B09_Iron": ("neutral", (0.16, 0.16, 0.17), 0.6, 1.0),
    "M_B09_Ceramic": ("neutral", (0.30, 0.20, 0.14), 0.35, 0.0),
    "M_B09_Bristle": ("neutral", (0.62, 0.55, 0.42), 0.8, 0.0),
    "M_B09_Cord": ("neutral", (0.50, 0.42, 0.30), 0.9, 0.0),
    "M_B09_Twine": ("neutral", (0.52, 0.40, 0.25), 0.9, 0.0),
    "M_B09_ShellPaper": ("neutral", (0.72, 0.60, 0.45), 0.85, 0.0),
    "M_B09_ShellCore": ("neutral", (0.55, 0.45, 0.36), 0.9, 0.0),
    "M_B09_FuseCord": ("neutral", (0.20, 0.18, 0.16), 0.8, 0.0),
    "M_B09_GaugeFace": ("neutral", (0.86, 0.82, 0.70), 0.7, 0.0),
    "M_B09_GaugeBand": ("neutral", (0.16, 0.62, 0.30), 0.5, 0.0),
    "M_B09_GaugeMarks": ("neutral", (0.08, 0.07, 0.07), 0.6, 0.0),
    "M_B09_GaugeNeedle": ("neutral", (0.80, 0.20, 0.10), 0.35, 0.0),
}


def fail(message):
    raise RuntimeError("b09 candidates: " + message)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def arg(name):
    a = sys.argv[1:]
    if name not in a:
        fail(f"{name} is required")
    return a[a.index(name) + 1]


def import_task(filename, destination, name, options=None):
    task = unreal.AssetImportTask()
    task.filename = str(filename)
    task.destination_path = destination
    task.destination_name = name
    task.automated = True
    task.replace_existing = False
    task.save = True
    if options is not None:
        task.options = options
    TOOLS.import_asset_tasks([task])
    return task


def import_texture(name, source, kind):
    path = ROOT / source
    import_task(path, TEX, name)
    t = ASSETS.load_asset(f"{TEX}/{name}")
    if not isinstance(t, unreal.Texture2D):
        fail(f"{name} did not import")
    if kind != "color":
        t.set_editor_property("srgb", False)
    if kind == "normal":
        t.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
    elif kind in ("masks", "linear"):
        t.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
    ASSETS.save_loaded_asset(t)
    return t, sha256(path)


def rotator_axes(r):
    """An FRotator's unit forward (X) and up (Z) axes: rows 0 and 2 of FRotationMatrix."""
    sp, cp = math.sin(math.radians(r.pitch)), math.cos(math.radians(r.pitch))
    sy, cy = math.sin(math.radians(r.yaw)), math.cos(math.radians(r.yaw))
    sr, cr = math.sin(math.radians(r.roll)), math.cos(math.radians(r.roll))
    return [cp * cy, cp * sy, sp], [-(cr * sp * cy + sr * sy), cy * sr - cr * sp * sy, cr * cp]


def read_socket(mesh, name):
    """A static mesh's socket by name (find_socket; the Sockets array is protected from Python), or None."""
    s = mesh.find_socket(name)
    if s is None:
        return None
    loc, rot, scale = (s.get_editor_property(k) for k in ("relative_location", "relative_rotation", "relative_scale"))
    fwd, up = rotator_axes(rot)
    return {"cm": [loc.x, loc.y, loc.z], "rotation_deg": [rot.pitch, rot.yaw, rot.roll], "x": fwd, "z": up,
            "scale": [scale.x, scale.y, scale.z]}


def node(m, cls, x, y, **props):
    e = LIB.create_material_expression(m, cls, x, y)
    for k, v in props.items():
        e.set_editor_property(k, v)
    return e


def washi_master(tex):
    """M_B09_WashiCandidate (see the module's notes)."""
    m = TOOLS.create_asset("M_B09_WashiCandidate", MATS, unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property("two_sided", True)
    m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
    m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE)
    P = unreal.MaterialProperty
    albedo = node(m, unreal.MaterialExpressionTextureSampleParameter2D, -1400, -500, parameter_name="AlbedoMap", texture=tex["T_B09_Washi_Albedo"])
    normal = node(m, unreal.MaterialExpressionTextureSampleParameter2D, -1400, -150, parameter_name="NormalMap", texture=tex["T_B09_Washi_NormalDX"],
                  sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    rough = node(m, unreal.MaterialExpressionTextureSampleParameter2D, -1400, 150, parameter_name="RoughnessMap", texture=tex["T_B09_Washi_Roughness"],
                 sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
    trans = node(m, unreal.MaterialExpressionTextureSampleParameter2D, -1400, 450, parameter_name="TranslucencyMap",
                 texture=tex["T_B09_Washi_TranslucencyEstimate"], sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
    tint = node(m, unreal.MaterialExpressionVectorParameter, -1100, -650, parameter_name="Tint", default_value=unreal.LinearColor(0.93, 0.91, 0.85, 1))
    rscale = node(m, unreal.MaterialExpressionScalarParameter, -1100, 250, parameter_name="RoughnessScale", default_value=1.0)
    tscale = node(m, unreal.MaterialExpressionScalarParameter, -1100, 550, parameter_name="TransmissionScale", default_value=0.8)
    paste = node(m, unreal.MaterialExpressionScalarParameter, -1100, 800, parameter_name="PasteReveal", default_value=1.0)
    oil = node(m, unreal.MaterialExpressionScalarParameter, -1100, 950, parameter_name="OilWet", default_value=0.0)
    glow = node(m, unreal.MaterialExpressionScalarParameter, -1100, 1100, parameter_name="Glow", default_value=0.0)
    glow_c = node(m, unreal.MaterialExpressionVectorParameter, -1100, 1250, parameter_name="GlowColor", default_value=unreal.LinearColor(1.0, 0.55, 0.22, 1))
    uv1 = node(m, unreal.MaterialExpressionTextureCoordinate, -1400, 800, coordinate_index=1)
    h = node(m, unreal.MaterialExpressionComponentMask, -1250, 800, r=True, g=False, b=False, a=False)
    LIB.connect_material_expressions(uv1, "", h, "")
    # Paste mask: 1 where h <= PasteReveal.
    d1 = node(m, unreal.MaterialExpressionSubtract, -900, 800)
    LIB.connect_material_expressions(paste, "", d1, "A")
    LIB.connect_material_expressions(h, "", d1, "B")
    k1 = node(m, unreal.MaterialExpressionMultiply, -760, 800, const_b=1000.0)
    LIB.connect_material_expressions(d1, "", k1, "A")
    a1 = node(m, unreal.MaterialExpressionAdd, -620, 800, const_b=0.5)
    LIB.connect_material_expressions(k1, "", a1, "A")
    s1 = node(m, unreal.MaterialExpressionSaturate, -480, 800)
    LIB.connect_material_expressions(a1, "", s1, "")
    LIB.connect_material_property(s1, "", P.MP_OPACITY_MASK)
    # Oil mask: 1 where h >= 1 - OilWet.
    om = node(m, unreal.MaterialExpressionOneMinus, -900, 950)
    LIB.connect_material_expressions(oil, "", om, "")
    d2 = node(m, unreal.MaterialExpressionSubtract, -760, 950)
    LIB.connect_material_expressions(h, "", d2, "A")
    LIB.connect_material_expressions(om, "", d2, "B")
    k2 = node(m, unreal.MaterialExpressionMultiply, -620, 950, const_b=1000.0)
    LIB.connect_material_expressions(d2, "", k2, "A")
    a2 = node(m, unreal.MaterialExpressionAdd, -480, 950, const_b=0.5)
    LIB.connect_material_expressions(k2, "", a2, "A")
    oilm = node(m, unreal.MaterialExpressionSaturate, -340, 950)
    LIB.connect_material_expressions(a2, "", oilm, "")
    base = node(m, unreal.MaterialExpressionMultiply, -900, -550)
    LIB.connect_material_expressions(albedo, "RGB", base, "A")
    LIB.connect_material_expressions(tint, "", base, "B")
    dark = node(m, unreal.MaterialExpressionMultiply, -700, -450, const_b=0.72)
    LIB.connect_material_expressions(base, "", dark, "A")
    bc = node(m, unreal.MaterialExpressionLinearInterpolate, -500, -550)
    LIB.connect_material_expressions(base, "", bc, "A")
    LIB.connect_material_expressions(dark, "", bc, "B")
    LIB.connect_material_expressions(oilm, "", bc, "Alpha")
    LIB.connect_material_property(bc, "", P.MP_BASE_COLOR)
    LIB.connect_material_property(normal, "RGB", P.MP_NORMAL)
    rr = node(m, unreal.MaterialExpressionMultiply, -900, 150)
    LIB.connect_material_expressions(rough, "R", rr, "A")
    LIB.connect_material_expressions(rscale, "", rr, "B")
    rl = node(m, unreal.MaterialExpressionLinearInterpolate, -500, 150, const_b=0.3)
    LIB.connect_material_expressions(rr, "", rl, "A")
    LIB.connect_material_expressions(oilm, "", rl, "Alpha")
    LIB.connect_material_property(rl, "", P.MP_ROUGHNESS)
    tr = node(m, unreal.MaterialExpressionMultiply, -900, 450)
    LIB.connect_material_expressions(trans, "R", tr, "A")
    LIB.connect_material_expressions(tscale, "", tr, "B")
    sss = node(m, unreal.MaterialExpressionMultiply, -700, 450)
    LIB.connect_material_expressions(base, "", sss, "A")
    LIB.connect_material_expressions(tr, "", sss, "B")
    LIB.connect_material_property(sss, "", P.MP_SUBSURFACE_COLOR)
    em = node(m, unreal.MaterialExpressionMultiply, -700, 1150)
    LIB.connect_material_expressions(glow_c, "", em, "A")
    LIB.connect_material_expressions(glow, "", em, "B")
    em2 = node(m, unreal.MaterialExpressionMultiply, -500, 1150)
    LIB.connect_material_expressions(em, "", em2, "A")
    LIB.connect_material_expressions(tr, "", em2, "B")
    LIB.connect_material_property(em2, "", P.MP_EMISSIVE_COLOR)
    LIB.recompile_material(m)
    ASSETS.save_loaded_asset(m)
    return m


def instance(name, parent):
    mi = TOOLS.create_asset(name, MATS, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    LIB.set_material_instance_parent(mi, parent)
    return mi


def import_mesh(name, a, build, mats, rows, problems):
    """One candidate FBX as a static mesh, its slots bound, read back against the build's manifest into rows."""
    opts = unreal.FbxImportUI()
    opts.import_mesh = True
    opts.import_as_skeletal = False
    opts.import_materials = False
    opts.import_textures = False
    opts.import_animations = False
    opts.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    sm = opts.static_mesh_import_data
    sm.set_editor_property("combine_meshes", True)
    sm.set_editor_property("auto_generate_collision", False)
    sm.set_editor_property("generate_lightmap_u_vs", False)
    import_task(build / a["fbx"], MESHES, name, opts)
    mesh = ASSETS.load_asset(f"{MESHES}/{name}")
    if not isinstance(mesh, unreal.StaticMesh):
        problems.append(f"{name} did not import as a static mesh")
        return
    bound = []
    for i, sm_ in enumerate(mesh.get_editor_property("static_materials")):
        slot = str(sm_.get_editor_property("material_slot_name"))
        mi = mats.get(slot)
        if mi is None:
            problems.append(f"{name}: slot {slot} has no candidate material")
            continue
        mesh.set_material(i, mi)
        bound.append(slot)
    ASSETS.save_loaded_asset(mesh)
    box = mesh.get_bounding_box()
    lo, hi = [box.min.x, box.min.y, box.min.z], [box.max.x, box.max.y, box.max.z]
    socks = {}
    for sname, want in a["sockets"].items():
        got = read_socket(mesh, sname)          # StaticMesh.Sockets is protected from Python (s146): by name
        if got is None:
            problems.append(f"{name}: no socket {sname}")
            continue
        socks[sname] = got
        axes = a["socket_axes"][sname]
        if max(abs(g - w) for g, w in zip(got["cm"], want)) > SOCKET_TOL_CM:
            problems.append(f"{name}: socket {sname} at {got['cm']}, wants {want}")
        if max(abs(g - w) for g, w in zip(got["x"] + got["z"], axes["x"] + axes["z"])) > SOCKET_TOL_AXIS:
            problems.append(f"{name}: socket {sname} axes x {got['x']} z {got['z']}, want {axes}")
        if max(abs(c - 1.0) for c in got["scale"]) > 1e-4:
            problems.append(f"{name}: socket {sname} scale {got['scale']}")
    want_lo, want_hi = a["bounds_cm"]
    bounds_err = max(max(abs(g - w) for g, w in zip(lo, want_lo)), max(abs(g - w) for g, w in zip(hi, want_hi)))
    if bounds_err > 0.1:
        problems.append(f"{name}: bounds {lo} {hi}, want {want_lo} {want_hi}")
    uvs = SMES.get_num_uv_channels(mesh, 0)
    simple = SMES.get_simple_collision_count(mesh)
    tris = mesh.get_num_triangles(0)
    if uvs != 2 or simple != 0 or sorted(set(bound)) != sorted(set(a["slots"])):
        problems.append(f"{name}: uv channels {uvs}, simple collision {simple}, slots {bound} vs {a['slots']}")
    rows[name] = {"asset": f"{MESHES}/{name}", "triangles": tris, "triangles_built": a["triangles"], "bounds_cm": [lo, hi],
                  "bounds_err_cm": bounds_err, "sockets": socks, "uv_channels": uvs, "simple_collision": simple,
                  "slots": {s: mats[s].get_path_name() for s in bound}}


def import_weapon(tex, pbr, rows, problems):
    """Weapon 7's in-tree mesh as SM_B09_Weapon07_ReviewStandIn, with its maps; its sockets read back."""
    w_src = ROOT / W07 / "SM_Weapon_07.fbx"
    opts = unreal.FbxImportUI()
    opts.import_mesh, opts.import_as_skeletal, opts.import_materials, opts.import_textures = True, False, False, False
    opts.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    opts.static_mesh_import_data.set_editor_property("auto_generate_collision", False)
    import_task(w_src, MESHES, "SM_B09_Weapon07_ReviewStandIn", opts)
    weapon = ASSETS.load_asset(f"{MESHES}/SM_B09_Weapon07_ReviewStandIn")
    if not isinstance(weapon, unreal.StaticMesh):
        fail("weapon 7's stand-in did not import")
    wmi = instance("MI_B09_Weapon07_ReviewStandIn", pbr)
    for p_, t in (("AlbedoMap", tex["T_B09_W07_BaseColor"]), ("NormalMap", tex["T_B09_W07_NormalDX"]), ("ORMMap", tex["T_B09_W07_ORM"])):
        LIB.set_material_instance_texture_parameter_value(wmi, p_, t)
    LIB.set_material_instance_scalar_parameter_value(wmi, "CoatBlendEnabled", 0.0)
    ASSETS.save_loaded_asset(wmi)
    for i in range(len(weapon.get_editor_property("static_materials"))):
        weapon.set_material(i, wmi)
    ASSETS.save_loaded_asset(weapon)
    w_record = json.loads((ROOT / W07 / "build_record.json").read_text())["assets"]["SM_Weapon_07"]["sockets"]
    wsock = {n: read_socket(weapon, n) for n in sorted(w_record)}
    wbox = weapon.get_bounding_box()
    muzzle = (wsock.get("Muzzle") or {}).get("cm")
    if muzzle is None or abs(muzzle[0] - 64.0) > 0.5 or abs(muzzle[1]) > 0.5 or abs(muzzle[2]) > 0.5:
        problems.append(f"weapon 7's stand-in Muzzle reads {muzzle}, not (64, 0, 0)")
    rows["SM_B09_Weapon07_ReviewStandIn"] = {"asset": weapon.get_path_name(), "source": str(w_src.relative_to(ROOT)),
                                             "source_sha256": sha256(w_src), "review_stand_in": True, "sockets": wsock,
                                             "bounds_cm": [[wbox.min.x, wbox.min.y, wbox.min.z], [wbox.max.x, wbox.max.y, wbox.max.z]],
                                             "triangles": weapon.get_num_triangles(0), "triangles_built": weapon.get_num_triangles(0)}


def main():
    global BASE, MESHES, MATS, TEX
    base = arg("--base")
    if not base.startswith("B09Workshop") or "/" in base:
        fail(f"--base {base}: a new folder name under {CANDIDATES}, starting B09Workshop")
    BASE = f"{CANDIDATES}/{base}"
    MESHES, MATS, TEX = f"{BASE}/Meshes", f"{BASE}/Materials", f"{BASE}/Textures"
    build = (ROOT / arg("--build")).resolve()
    readback_path = (ROOT / arg("--readback")).resolve()
    if readback_path.exists() or not readback_path.is_relative_to(ROOT / "Saved/B09Workshop/Unreal"):
        fail(f"the readback must be a new file under Saved/B09Workshop/Unreal: {readback_path}")
    if ASSETS.does_directory_exist(BASE) and ASSETS.list_assets(BASE, recursive=True):
        fail(f"{BASE} exists: the candidates are new assets")
    man_bytes = (build / "manifest.json").read_bytes()
    man = json.loads(man_bytes.decode("utf-8"))
    for name, a in man["assets"].items():
        if sha256(build / a["fbx"]) != a["sha256"]:
            fail(f"{a['fbx']} is not the build's")
    pbr = unreal.load_asset(PBR)
    if pbr is None:
        fail(f"{PBR} is missing")
    for d in (MESHES, MATS, TEX):
        ASSETS.make_directory(d)
    tex, tex_src = {}, {}
    for name, (src, kind) in TEXTURES.items():
        tex[name], tex_src[name] = import_texture(name, src, kind)
    neutral = {k: unreal.load_asset(NEUTRAL.format(k)) for k in ("Albedo", "NormalDX", "ORM")}
    mats = {}
    for slot, (maps, tint, rough, metal) in OPAQUE.items():
        mi = instance("MI_" + slot[2:], pbr)
        a, n, o = ((tex["T_B09_Wood_Albedo"], tex["T_B09_Wood_NormalDX"], tex["T_B09_Wood_ORM"]) if maps == "wood"
                   else (neutral["Albedo"], neutral["NormalDX"], neutral["ORM"]))
        for p, t in (("AlbedoMap", a), ("NormalMap", n), ("ORMMap", o)):
            LIB.set_material_instance_texture_parameter_value(mi, p, t)
        LIB.set_material_instance_vector_parameter_value(mi, "Tint", unreal.LinearColor(*tint, 1.0))
        LIB.set_material_instance_scalar_parameter_value(mi, "RoughnessScale", rough)
        LIB.set_material_instance_scalar_parameter_value(mi, "MetallicScale", metal)
        LIB.set_material_instance_scalar_parameter_value(mi, "CoatBlendEnabled", 0.0)
        ASSETS.save_loaded_asset(mi)
        mats[slot] = mi
    rows, problems, washi = {}, [], None
    try:                                   # each part fails on its own: s146 lost the rest and the readback
        washi = washi_master(tex)
        mats["M_B09_Washi"] = instance("MI_B09_Washi", washi)
        ASSETS.save_loaded_asset(mats["M_B09_Washi"])
    except Exception as exc:
        problems.append(f"the washi master: {exc!r}")
    for name, a in sorted(man["assets"].items()):
        try:
            import_mesh(name, a, build, mats, rows, problems)
        except Exception as exc:
            problems.append(f"{name}: {exc!r}")
    try:                                   # weapon 7, a review stand-in for the shell bench's capture
        import_weapon(tex, pbr, rows, problems)
    except Exception as exc:
        problems.append(f"weapon 7's stand-in: {exc!r}")
    for name in rows:
        if abs(rows[name]["triangles"] - rows[name]["triangles_built"]) > 0:
            problems.append(f"{name}: {rows[name]['triangles']} triangles, built {rows[name]['triangles_built']}")
    readback = {"base": BASE, "build": str(build.relative_to(ROOT)), "build_manifest_sha256": hashlib.sha256(man_bytes).hexdigest(),
                "textures": {k: {"asset": f"{TEX}/{k}", "source": TEXTURES[k][0], "source_sha256": tex_src[k]} for k in TEXTURES},
                "translucency": "paper_0017_translucency_ART_ESTIMATE: an estimate, not a measured transmission",
                "materials": {s: m.get_path_name() for s, m in mats.items()}, "washi_master": washi.get_path_name() if washi is not None else None,
                "meshes": rows, "problems": problems,
                "inputs": {"scripts/unreal/import_b09_workshop_candidates.py": sha256(__file__)}}
    readback_path.parent.mkdir(parents=True, exist_ok=True)
    with open(readback_path, "x", encoding="utf-8") as fh:
        json.dump(readback, fh, indent=1)
    if problems:
        fail(f"{len(problems)} problems, first: {problems[:3]}")
    print(MARKER, json.dumps({"meshes": len(rows), "materials": len(mats), "textures": len(tex)}))


main()
