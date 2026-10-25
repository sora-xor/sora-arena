"""Import the dojo halls' timber columns: one Nanite log per placement, a baked SM5 pool.

Run: scripts/toolchain/run-editor-script.sh scripts/unreal/import_nyaagyu_dojo_timbers.py NYAAGYU_DOJO_TIMBERS_READY

Reads Content/SourceArt/Environment/NyaagyuDojoTimbers/manifest.json (written by
scripts/art/create_nyaagyu_dojo_timbers.py) and the local evidence that the
dense meshes in Local/ArtCache/NyaagyuDojoTimbers were rebuilt to the
manifest's canonical geometry digests (the generator's build or --verify run).
Without matching evidence nothing is imported. Nor without a current
campaign_binding.json (scripts/art/bind_dojo_timbers.py): the placements are
named from the estate halls in Content/Data/campaign, so a chapter file that
changed since the binding stops the import until the binder reruns and
confirms no built log went stale.

* Placements (SM6): each dense FBX becomes SM_DojoTimberColumn_<rect>_S<side>_B<bay>
  with Nanite on and Unreal's generated fallback, bound to an instance of
  M_SoraTimberNanite (ring field, vertex masks). HallInterior draws them where
  Nanite runs.
* Pool (SM5, MAC tier): each committed fallback FBX becomes
  SM_DojoTimberColumn_MAC_<Wall|Open>_NN, a conventional mesh (Nanite off), with
  its baked T_*_NormalDX and T_*_Masks on UV1 through an instance of
  M_SoraTimber.

Both import with full-precision UVs (the log frame in UV2 needs sub-millimetre
steps), vertex colours replaced and degenerate removal off (check walls).

Both masters compute growth rings from the log frame (UV2: offset from the pith
in metres; UV3: height along the pith and a per-log seed), the same model as
scripts/art/sora_timber_lookdev.py: ring widths wander over a few rings (the
shared T_TimberRingNoise), earlywood grades into a latewood band set in over a
tenth of the ring, the next year starts abruptly, and each year has its own
strength (T_TimberRingRandom). Contrast fades where rings fall below a pixel.
The normal is perturbed by the ring ridge and fibre height with screen-space
derivatives (Mikkelsen's surface-gradient bump), over the baked normal on the
fallback and the geometric normal on Nanite. Clear coat is the fuki-urushi.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys

import unreal

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sora_engine_pin import require_running_engine  # noqa: E402

require_running_engine("Nyaagyu dojo timbers import")
ROOT = Path(unreal.Paths.project_dir()).resolve()
KIT = ROOT / "Content/SourceArt/Environment/NyaagyuDojoTimbers"
CACHE = Path(os.environ.get("SORA_ART_CACHE", str(ROOT / "Local/ArtCache"))) / "NyaagyuDojoTimbers"
DEST = "/Game/Generated/Environment/DojoTimbers"
TEX = f"{DEST}/Textures"

tools = unreal.AssetToolsHelpers.get_asset_tools()
assets = unreal.EditorAssetLibrary
lib = unreal.MaterialEditingLibrary
meshes = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)

# Surface-gradient bump (Mikkelsen 2010): world normal from a height in cm and
# the screen-space derivatives of position and height.
BUMP_HLSL = """float3 dpx = ddx(P); float3 dpy = ddy(P);
float dhx = ddx(H); float dhy = ddy(H);
float3 r1 = cross(dpy, N); float3 r2 = cross(N, dpx);
float det = dot(dpx, r1);
float3 g = sign(det) * (dhx * r1 + dhy * r2);
return normalize(abs(det) * N - g);"""


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(f"Dojo timbers import: {message}")


class Graph:
    """Material graph helper: expressions laid out on a coarse grid."""

    def __init__(self, material):
        self.m = material
        self.x = -2600
        self.y = -1200

    def n(self, cls, **props):
        e = lib.create_material_expression(self.m, cls, self.x, self.y)
        self.y += 110
        if self.y > 1400:
            self.y = -1200
            self.x += 260
        for k, v in props.items():
            e.set_editor_property(k, v)
        return e

    def link(self, a, b, pin="", out=""):
        require(lib.connect_material_expressions(a, out, b, pin), f"link {a.get_name()}.{out} -> {b.get_name()}.{pin}")

    def op(self, cls, a, b=None, a_out="", b_out=""):
        e = self.n(cls)
        self.link(a, e, "A", a_out)
        if b is not None:
            if isinstance(b, (int, float)):
                e.set_editor_property("const_b", float(b))
            else:
                self.link(b, e, "B", b_out)
        return e

    def one(self, cls, a, a_out=""):
        e = self.n(cls)
        self.link(a, e, "", a_out)
        return e

    def const(self, v):
        return self.n(unreal.MaterialExpressionConstant, r=float(v))

    def scalar(self, name, v):
        return self.n(unreal.MaterialExpressionScalarParameter, parameter_name=name, default_value=float(v))

    def color(self, name, rgb):
        return self.n(unreal.MaterialExpressionVectorParameter, parameter_name=name,
                      default_value=unreal.LinearColor(*rgb, 1.0))

    def mask(self, a, channels, a_out=""):
        e = self.n(unreal.MaterialExpressionComponentMask, r="r" in channels, g="g" in channels,
                   b="b" in channels, a="a" in channels)
        self.link(a, e, "", a_out)
        return e

    def lerp(self, a, b, t, a_out="", b_out="", t_out=""):
        e = self.n(unreal.MaterialExpressionLinearInterpolate)
        self.link(a, e, "A", a_out)
        self.link(b, e, "B", b_out)
        self.link(t, e, "Alpha", t_out)
        return e

    def smooth(self, lo, hi, v):
        e = self.n(unreal.MaterialExpressionSmoothStep)
        self.link(lo, e, "Min")
        self.link(hi, e, "Max")
        self.link(v, e, "Value")
        return e

    def append(self, a, b):
        e = self.n(unreal.MaterialExpressionAppendVector)
        self.link(a, e, "A")
        self.link(b, e, "B")
        return e

    def sample(self, tex, uv, sampler=unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR, name=None):
        cls = unreal.MaterialExpressionTextureSampleParameter2D if name else unreal.MaterialExpressionTextureSample
        props = {"texture": tex, "sampler_type": sampler}
        if name:
            props["parameter_name"] = name
        e = self.n(cls, **props)
        self.link(uv, e, "UVs")
        return e


def import_texture(path: Path, name: str, kind: str):
    task = unreal.AssetImportTask()
    task.filename = str(path)
    task.destination_path = TEX
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = True
    tools.import_asset_tasks([task])
    tex = assets.load_asset(f"{TEX}/{name}")
    require(isinstance(tex, unreal.Texture2D), f"texture {path.name}")
    tex.set_editor_property("srgb", False)
    if kind == "Normal":
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
        tex.set_editor_property("flip_green_channel", False)
    elif kind == "Masks":
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
    elif kind == "Data":
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_GRAYSCALE)
        tex.set_editor_property("mip_gen_settings", unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
        tex.set_editor_property("filter", unreal.TextureFilter.TF_BILINEAR)
    elif kind == "Random":
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_GRAYSCALE)
        tex.set_editor_property("mip_gen_settings", unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
        tex.set_editor_property("filter", unreal.TextureFilter.TF_NEAREST)
    tex.set_editor_property("lod_group", unreal.TextureGroup.TEXTUREGROUP_WORLD)
    assets.save_loaded_asset(tex)
    return tex


def timber_master(name, shared, fallback: bool):
    """M_SoraTimber (fallback: baked NormalDX + Masks on UV1) or M_SoraTimberNanite."""
    path = f"{DEST}/{name}"
    m = assets.load_asset(path) if assets.does_asset_exist(path) else tools.create_asset(
        name, DEST, unreal.Material, unreal.MaterialFactoryNew())
    for old in list(lib.get_material_expressions(m)):
        lib.delete_material_expression(m, old)
    m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_CLEAR_COAT)
    m.set_editor_property("tangent_space_normal", False)
    m.set_editor_property("used_with_nanite", True)
    m.set_editor_property("used_with_instanced_static_meshes", True)
    g = Graph(m)
    uvq = g.n(unreal.MaterialExpressionTextureCoordinate, coordinate_index=2)
    uvz = g.n(unreal.MaterialExpressionTextureCoordinate, coordinate_index=3)
    seed = g.mask(uvz, "g")
    # Fibres (R), streaks (G) and drift (B) from T_TimberFibre on UV0 (metres).
    uv0 = g.n(unreal.MaterialExpressionTextureCoordinate, coordinate_index=0)
    tile = g.scalar("FibreTileMeters", 0.25)
    fibre = g.sample(shared["Fibre"], g.op(unreal.MaterialExpressionDivide, uv0, tile))
    fib = g.mask(fibre, "r")
    streak = g.mask(fibre, "g")
    drift = g.mask(g.sample(shared["Fibre"], g.op(unreal.MaterialExpressionMultiply, uv0, 0.11)), "b")
    # Fibres deviate: the ring radius wanders by a quarter millimetre.
    r = g.op(unreal.MaterialExpressionAdd, g.one(unreal.MaterialExpressionLength, uvq),
             g.op(unreal.MaterialExpressionMultiply, g.op(unreal.MaterialExpressionSubtract, streak, 0.5), 0.00025))
    w = g.scalar("RingWidth", 0.0019)
    lwf = g.scalar("Latewood", 0.24)
    # Ring-width wander: T_TimberRingNoise row per log, ~6 rings per texel span.
    six_w = g.op(unreal.MaterialExpressionMultiply, w, 6.0)
    nu = g.op(unreal.MaterialExpressionAdd, g.op(unreal.MaterialExpressionDivide, r, six_w),
              g.op(unreal.MaterialExpressionMultiply, seed, 37.0))
    nv = g.one(unreal.MaterialExpressionFrac, g.op(unreal.MaterialExpressionMultiply, seed, 7.31))
    var = g.mask(g.sample(shared["RingNoise"], g.append(nu, nv)), "r")
    phase = g.op(unreal.MaterialExpressionAdd, g.op(unreal.MaterialExpressionDivide, r, w),
                 g.op(unreal.MaterialExpressionMultiply, g.op(unreal.MaterialExpressionSubtract, var, 0.5), 3.0))
    f = g.one(unreal.MaterialExpressionFrac, phase)
    ring = g.one(unreal.MaterialExpressionFloor, phase)
    yu = g.op(unreal.MaterialExpressionDivide, g.op(unreal.MaterialExpressionAdd, ring,
                                                     g.op(unreal.MaterialExpressionMultiply, seed, 101.0)), 256.0)
    yv = g.one(unreal.MaterialExpressionFrac, g.op(unreal.MaterialExpressionMultiply, seed, 3.7))
    year = g.mask(g.sample(shared["RingRandom"], g.append(yu, yv)), "r")
    one = g.const(1.0)
    onset = g.op(unreal.MaterialExpressionSubtract, one, lwf)
    late = g.smooth(g.op(unreal.MaterialExpressionSubtract, onset, 0.07), g.op(unreal.MaterialExpressionAdd, onset, 0.03), f)
    lw = g.op(unreal.MaterialExpressionMultiply, late,
              g.op(unreal.MaterialExpressionAdd, g.op(unreal.MaterialExpressionMultiply, year, 0.4), 0.6))
    ridge = g.op(unreal.MaterialExpressionMultiply,
                 g.smooth(g.op(unreal.MaterialExpressionSubtract, onset, 0.25), g.op(unreal.MaterialExpressionAdd, onset, 0.05), f),
                 g.op(unreal.MaterialExpressionSubtract, one, g.smooth(g.const(0.82), g.const(1.0), f)))
    # Antialiasing: rings below about a pixel fade to their mean.
    fw = g.op(unreal.MaterialExpressionAdd, g.one(unreal.MaterialExpressionAbs, g.one(unreal.MaterialExpressionDDX, phase)),
              g.one(unreal.MaterialExpressionAbs, g.one(unreal.MaterialExpressionDDY, phase)))
    fade = g.op(unreal.MaterialExpressionSubtract, one, g.one(unreal.MaterialExpressionSaturate,
                g.op(unreal.MaterialExpressionDivide, g.op(unreal.MaterialExpressionSubtract, fw, 0.3), 0.7)))
    lw = g.lerp(g.const(0.14), lw, fade)
    ridge = g.lerp(g.const(0.12), ridge, fade)
    early_c = g.color("EarlyColor", (0.066, 0.035, 0.020))
    late_c = g.color("LateColor", (0.040, 0.020, 0.012))
    early = g.lerp(early_c, g.op(unreal.MaterialExpressionMultiply, early_c, 0.88), g.op(unreal.MaterialExpressionMultiply, f, 0.5))
    base = g.lerp(early, late_c, lw)
    tone = g.op(unreal.MaterialExpressionAdd, g.const(0.68),
                g.op(unreal.MaterialExpressionAdd,
                     g.op(unreal.MaterialExpressionAdd, g.op(unreal.MaterialExpressionMultiply, year, 0.12),
                          g.op(unreal.MaterialExpressionMultiply, fib, 0.12)),
                     g.op(unreal.MaterialExpressionAdd, g.op(unreal.MaterialExpressionMultiply, streak, 0.12),
                          g.op(unreal.MaterialExpressionMultiply, drift, 0.34))))
    base = g.op(unreal.MaterialExpressionMultiply, base, tone)
    # Masks: baked (fallback, UV1) or vertex colours (Nanite).
    if fallback:
        uv1 = g.n(unreal.MaterialExpressionTextureCoordinate, coordinate_index=1)
        msk = g.sample(shared["DefaultMasks"], uv1, unreal.MaterialSamplerType.SAMPLERTYPE_MASKS, name="MasksMap")
        cav, wear, soot, knot = (g.mask(msk, c) for c in ("r", "g", "b", "a"))
    else:
        vc = g.n(unreal.MaterialExpressionVertexColor)
        cav, wear, soot, knot = (g.mask(vc, c) for c in ("r", "g", "b", "a"))
    # Wear: below 0.5 the hand's grime and polish (darker, glossier), above
    # 0.5 the lacquer rubbed through on the arris (lighter, bare wood).
    grime = g.one(unreal.MaterialExpressionSaturate, g.op(unreal.MaterialExpressionMultiply, wear, 2.0))
    edge = g.one(unreal.MaterialExpressionSaturate,
                 g.op(unreal.MaterialExpressionSubtract, g.op(unreal.MaterialExpressionMultiply, wear, 2.0), 1.0))
    base = g.lerp(base, g.color("KnotColor", (0.016, 0.008, 0.005)), g.op(unreal.MaterialExpressionMultiply, knot, 0.92))
    base = g.lerp(base, g.color("SootColor", (0.012, 0.010, 0.009)),
                  g.op(unreal.MaterialExpressionMultiply, soot, g.scalar("SootAmount", 0.55)))
    base = g.lerp(base, g.op(unreal.MaterialExpressionMultiply, early_c, 0.62),
                  g.op(unreal.MaterialExpressionMultiply, grime, 0.55))
    base = g.lerp(base, g.color("WornColor", (0.15, 0.09, 0.05)),
                  g.op(unreal.MaterialExpressionMultiply, edge, g.scalar("WearColorAmount", 0.45)))
    base = g.lerp(base, g.const(0.0), g.op(unreal.MaterialExpressionMultiply, cav, 0.65))
    lib.connect_material_property(base, "", unreal.MaterialProperty.MP_BASE_COLOR)
    rough = g.op(unreal.MaterialExpressionAdd, g.scalar("Roughness", 0.55),
                 g.op(unreal.MaterialExpressionAdd,
                      g.op(unreal.MaterialExpressionAdd, g.op(unreal.MaterialExpressionMultiply, lw, 0.06),
                           g.op(unreal.MaterialExpressionMultiply, soot, 0.15)),
                      g.op(unreal.MaterialExpressionAdd, g.op(unreal.MaterialExpressionMultiply, edge, -0.12),
                           g.op(unreal.MaterialExpressionMultiply, g.op(unreal.MaterialExpressionSubtract, fib, 0.5), 0.12))))
    lib.connect_material_property(g.one(unreal.MaterialExpressionSaturate, rough), "", unreal.MaterialProperty.MP_ROUGHNESS)
    lib.connect_material_property(g.scalar("ClearCoat", 1.0), "", unreal.MaterialProperty.MP_CUSTOM_DATA0)
    ccr = g.op(unreal.MaterialExpressionAdd, g.scalar("ClearCoatRoughness", 0.17),
               g.op(unreal.MaterialExpressionAdd,
                    g.op(unreal.MaterialExpressionAdd, g.op(unreal.MaterialExpressionMultiply, soot, 0.16),
                         g.op(unreal.MaterialExpressionMultiply, grime, -0.08)),
                    g.op(unreal.MaterialExpressionMultiply, g.op(unreal.MaterialExpressionSubtract, streak, 0.5), 0.10)))
    lib.connect_material_property(g.one(unreal.MaterialExpressionSaturate, ccr), "", unreal.MaterialProperty.MP_CUSTOM_DATA1)
    # Normal: ridge + fibre height (metres -> cm) as a surface-gradient bump.
    height_m = g.op(unreal.MaterialExpressionAdd, g.op(unreal.MaterialExpressionMultiply, ridge, g.scalar("RaiseMeters", 0.00002)),
                    g.op(unreal.MaterialExpressionMultiply, fib, g.scalar("FibreMeters", 0.000012)))
    height_cm = g.op(unreal.MaterialExpressionMultiply, height_m, 100.0)
    if fallback:
        nmap = g.sample(shared["DefaultNormal"], g.n(unreal.MaterialExpressionTextureCoordinate, coordinate_index=1),
                        unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL, name="NormalMap")
        nws = g.n(unreal.MaterialExpressionTransform, transform_source_type=unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_TANGENT,
                  transform_type=unreal.MaterialVectorCoordTransform.TRANSFORM_WORLD)
        g.link(nmap, nws, "", "RGB")
        normal_in = g.one(unreal.MaterialExpressionNormalize, nws)
    else:
        normal_in = g.n(unreal.MaterialExpressionVertexNormalWS)
    pos = g.n(unreal.MaterialExpressionWorldPosition,
              world_position_shader_offset=unreal.WorldPositionIncludedOffsets.WPT_CAMERA_RELATIVE_NO_OFFSETS)
    bump = g.n(unreal.MaterialExpressionCustom, code=BUMP_HLSL, output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT3,
               description="SurfaceGradientBump",
               inputs=[unreal.CustomInput(input_name="P"), unreal.CustomInput(input_name="H"),
                       unreal.CustomInput(input_name="N")])
    g.link(pos, bump, "P")
    g.link(height_cm, bump, "H")
    g.link(normal_in, bump, "N")
    lib.connect_material_property(bump, "", unreal.MaterialProperty.MP_NORMAL)
    lib.layout_material_expressions(m)
    lib.recompile_material(m)
    assets.save_loaded_asset(m)
    return m


# Finishes, mirroring scripts/art/sora_timber_lookdev.py PRESETS (keep in step).
PRESETS = {
    "column_fukiurushi": dict(EarlyColor=(0.066, 0.035, 0.020), LateColor=(0.040, 0.020, 0.012),
                              KnotColor=(0.016, 0.008, 0.005), SootColor=(0.012, 0.010, 0.009),
                              WornColor=(0.15, 0.090, 0.050), Roughness=0.55, ClearCoat=1.0, ClearCoatRoughness=0.17,
                              RaiseMeters=0.00002, FibreMeters=0.000012, SootAmount=0.55, WearColorAmount=0.45),
    "floor_hinoki": dict(EarlyColor=(0.42, 0.29, 0.17), LateColor=(0.25, 0.15, 0.080), KnotColor=(0.12, 0.060, 0.030),
                         SootColor=(0.20, 0.14, 0.09), WornColor=(0.50, 0.37, 0.24), Roughness=0.45, ClearCoat=0.65,
                         ClearCoatRoughness=0.09, RaiseMeters=0.00022, FibreMeters=0.00002, SootAmount=0.25,
                         WearColorAmount=0.35),
}


def apply_preset(mi, preset):
    for key, value in PRESETS[preset].items():
        if isinstance(value, tuple):
            lib.set_material_instance_vector_parameter_value(mi, key, unreal.LinearColor(*value, 1.0))
        else:
            lib.set_material_instance_scalar_parameter_value(mi, key, value)


def instance(name, parent):
    path = f"{DEST}/{name}"
    mi = assets.load_asset(path) if assets.does_asset_exist(path) else tools.create_asset(
        name, DEST, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    lib.set_material_instance_parent(mi, parent)
    return mi


def fbx_options(nanite: bool):
    options = unreal.FbxImportUI()
    options.import_mesh = True
    options.import_materials = False
    options.import_textures = False
    options.import_as_skeletal = False
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    data = options.static_mesh_import_data
    data.combine_meshes = True
    data.generate_lightmap_u_vs = False
    data.auto_generate_collision = False
    data.remove_degenerates = False
    data.vertex_color_import_option = unreal.VertexColorImportOption.REPLACE
    data.normal_import_method = unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    data.set_editor_property("build_nanite", nanite)
    return options


def verified(path: Path, digest: str, evidence: dict, label: str):
    """The file is the one the generator's build/--verify run wrote for ``digest``."""
    rel = path.relative_to(ROOT).as_posix()
    entry = evidence["fbx"].get(rel)
    require(entry is not None, f"{label}: no rebuild evidence for {rel} (run the generator, or its --verify)")
    require(entry["digest"] == digest, f"{label}: rebuilt geometry digest differs from the manifest")
    require(path.is_file() and sha(path) == entry["sha256"], f"{label}: {rel} is not the file that run wrote")


def import_mesh(fbx: Path, name: str, nanite: bool):
    task = unreal.AssetImportTask()
    task.filename = str(fbx)
    task.destination_path = DEST
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = True
    task.options = fbx_options(nanite)
    tools.import_asset_tasks([task])
    mesh = assets.load_asset(f"{DEST}/{name}")
    require(isinstance(mesh, unreal.StaticMesh), f"{name}: import failed")
    build = meshes.get_lod_build_settings(mesh, 0)
    build.set_editor_property("use_full_precision_u_vs", True)
    build.set_editor_property("remove_degenerates", False)
    build.set_editor_property("generate_lightmap_u_vs", False)
    build.set_editor_property("recompute_normals", False)
    build.set_editor_property("recompute_tangents", True)
    build.set_editor_property("use_mikk_t_space", True)
    meshes.set_lod_build_settings(mesh, 0, build)
    settings = mesh.get_editor_property("nanite_settings")
    settings.set_editor_property("enabled", nanite)
    if nanite:
        # Unreal's fallback for the rare non-Nanite pass; SM5 draws the pool.
        settings.set_editor_property("fallback_target", unreal.NaniteFallbackTarget.RELATIVE_ERROR)
        settings.set_editor_property("fallback_relative_error", 1.0)
    mesh.set_editor_property("nanite_settings", settings)
    return mesh


def import_placement(rec, parent, evidence, preset="column_fukiurushi"):
    name = rec["asset"]
    fbx = ROOT / rec["cache_fbx"]
    verified(fbx, rec["digest"], evidence, name)
    mesh = import_mesh(fbx, name, True)
    mi = instance(f"MI_{name}", parent)
    apply_preset(mi, preset)
    lib.set_material_instance_scalar_parameter_value(mi, "RingWidth", rec["ring_width_m"])
    assets.save_loaded_asset(mi)
    mesh.set_material(0, mi)
    assets.save_loaded_asset(mesh)
    return name, rec["triangles"]


def import_pool(rec, parent, evidence, preset="column_fukiurushi"):
    name = rec["asset"]
    fbx = ROOT / rec["fallback_fbx"]
    require(fbx.is_file() and sha(fbx) == rec["fallback_fbx_sha256"], f"{name}: committed fallback FBX changed")
    verified(fbx, rec["digest"], evidence, name)
    mesh = import_mesh(fbx, name, False)
    maps = {}
    for kind in ("NormalDX", "Masks"):
        path = ROOT / rec["fallback_maps"][kind]["file"]
        require(path.is_file() and sha(path) == rec["fallback_maps"][kind]["sha256"], f"{name}: {kind} changed")
        maps[kind] = import_texture(path, path.stem, "Normal" if kind == "NormalDX" else "Masks")
    mi = instance(f"MI_{name}", parent)
    apply_preset(mi, preset)
    lib.set_material_instance_scalar_parameter_value(mi, "RingWidth", rec["ring_width_m"])
    lib.set_material_instance_texture_parameter_value(mi, "NormalMap", maps["NormalDX"])
    lib.set_material_instance_texture_parameter_value(mi, "MasksMap", maps["Masks"])
    assets.save_loaded_asset(mi)
    mesh.set_material(0, mi)
    assets.save_loaded_asset(mesh)
    return name, rec["fallback_triangles"]


def load_binding(manifests):
    """The campaign binding: the chapter files and manifests the placements were checked against."""
    path = KIT / "campaign_binding.json"
    require(path.is_file(), "no campaign_binding.json (run python3 scripts/art/bind_dojo_timbers.py)")
    binding = json.loads(path.read_text())
    require(binding.get("schema") == "sora-dojo-timber-campaign-binding-v1", "unknown campaign binding schema")
    require(sha(ROOT / binding["binder"]) == binding["binder_sha256"], "the binder changed since the binding")
    require(sorted(binding["manifests"]) == sorted(manifests), "the binding covers other manifests")
    for rel, digest in binding["manifests"].items():
        require(sha(ROOT / rel) == digest, f"{rel} changed since the binding")
    chapters = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "Content/Data/campaign").glob("chapter_*.json"))
    require(chapters == sorted(binding["campaign"]), "the chapter files are not the ones bound")
    for rel, digest in binding["campaign"].items():
        require(sha(ROOT / rel) == digest,
                f"{rel} changed since the binding (rerun python3 scripts/art/bind_dojo_timbers.py)")
    return binding


def load_kit(folder: Path, cache: Path):
    """A kit manifest whose generator and inputs are unchanged, with clean rebuild evidence."""
    manifest = json.loads((folder / "manifest.json").read_text())
    require(manifest["generator_sha256"] == sha(ROOT / manifest["generator"]), f"{folder.name}: generator changed")
    for rel, digest in manifest["inputs"].items():
        require(sha(ROOT / rel) == digest, f"{folder.name}: generator input {rel} changed since the build")
    evidence = json.loads((cache / "evidence.json").read_text())
    require(not evidence.get("digest_mismatches"), f"{folder.name}: rebuild evidence reports mismatches")
    return manifest, evidence


def main():
    manifest, evidence = load_kit(KIT, CACHE)
    binding = load_binding(["Content/SourceArt/Environment/NyaagyuDojoTimbers/manifest.json",
                            "Content/SourceArt/Environment/NyaagyuDojoTimbers/Rails/manifest.json"])
    coverage = binding["coverage"]
    assets.make_directory(TEX)
    shared = {}
    for kind, entry in manifest["shared_textures"].items():
        path = ROOT / entry["file"]
        require(path.is_file() and sha(path) == entry["sha256"], f"shared texture {kind} changed")
        shared[kind] = import_texture(path, path.stem, entry["kind"])
    shared["DefaultNormal"] = assets.load_asset("/Engine/EngineMaterials/DefaultNormal")
    shared["DefaultMasks"] = assets.load_asset("/Engine/EngineResources/Black")
    base = timber_master("M_SoraTimber", shared, True)
    nanite = timber_master("M_SoraTimberNanite", shared, False)
    pool = [import_pool(rec, base, evidence) for rec in manifest["pool"]]
    placed = [import_placement(rec, nanite, evidence) for rec in manifest["placements"]]
    report = [f"columns: {len(placed)} placement logs ({coverage['columns_with_own_log']} of "
              f"{coverage['columns']} estate placements), {len(pool)} pool"]
    triangles = sum(t for _, t in placed)
    # The bay rails (create_nyaagyu_dojo_rails.py), when built: same two sets.
    if (KIT / "Rails/manifest.json").is_file():
        rails, rail_evidence = load_kit(KIT / "Rails", CACHE / "Rails")
        rail_pool = [import_pool(rec, base, rail_evidence) for rec in rails["pool"]]
        rail_placed = [import_placement(rec, nanite, rail_evidence) for rec in rails["placements"]]
        triangles += sum(t for _, t in rail_placed)
        report.append(f"rails: {len(rail_placed)} placement logs ({coverage['rails_with_own_log']} of "
                      f"{coverage['rails']}), {len(rail_pool)} pool")
    # The floor tiles (create_nyaagyu_dojo_floor.py): boards unique within a tile.
    if (KIT / "Floor/manifest.json").is_file():
        floor, floor_evidence = load_kit(KIT / "Floor", CACHE / "Floor")
        floor_pool = [import_pool(rec, base, floor_evidence, "floor_hinoki") for rec in floor["pool"]]
        floor_tiles = [import_placement(rec, nanite, floor_evidence, "floor_hinoki") for rec in floor["tiles"]]
        triangles += sum(t for _, t in floor_tiles)
        report.append(f"floor: {len(floor_tiles)} Nanite tiles, {len(floor_pool)} pool")
    assets.save_directory(DEST, only_if_is_dirty=False, recursive=True)
    unreal.log(f"NYAAGYU_DOJO_TIMBERS_READY: {'; '.join(report)}; {triangles} Nanite source triangles")


main()
