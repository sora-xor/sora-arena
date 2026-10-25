"""Authenticate isolated timber originals; CPU resources never prove a draw.

The existing production Nanite pixel classifier is reused without changing its
schema, asset inventory or placement validation. These tests are diagnostics,
not photorealism, M1, production placement or performance qualification.
"""
import hashlib
import importlib.util
import math
from pathlib import Path
import re
import subprocess

SPEC = importlib.util.spec_from_file_location("probe_nanite_pixels", Path(__file__).with_name("nanite_capture_validation.py"))
PIXELS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PIXELS)
SCHEMA = "sora-arena.timber-probe.v1"
SCOPE = "nine saved timber probe assets in an isolated fixture; not production placement, art or platform acceptance"
ROOT = "/Game/Generated/Qualification/DojoTimberProbe/"
NAMES = (
    "SM_DojoTimberColumn_8000_m1300_11600_1300_S0_B18",
    "SM_DojoTimberRail_Cornice_8000_m1300_11600_1300_S1_B01",
    "SM_DojoTimberRail_Koshi_8000_m1300_11600_1300_S2_B15",
    "SM_DojoTimberRail_Nageshi_8000_m1300_11600_1300_S1_B00",
    "SM_DojoTimberRail_Nuki_8000_m1300_11600_1300_S3_B13",
    "SM_DojoTimberColumn_MAC_Wall_09", "SM_DojoTimberColumn_MAC_Open_02",
    "SM_DojoTimberRail_MAC_Nageshi_01", "SM_DojoTimberRail_MAC_Nuki_01")
INPUTS = ("Source/SoraArena/Private/SoraTimberProbeCapture.cpp",
          "scripts/unreal/import_nyaagyu_dojo_timbers.py",
          "scripts/unreal/dojo_timber_admission.py", "scripts/unreal/dojo_nanite.py")
TEXTURES = tuple("Textures/T_" + n.removeprefix("SM_") + "_" + suffix
                 for n in NAMES[5:] for suffix in ("Masks", "NormalDX")) + tuple(
    "Textures/T_Timber" + n for n in ("Fibre", "RingNoise", "RingRandom"))
PACKAGES = NAMES + tuple("MI_" + n for n in NAMES) + ("M_SoraTimber", "M_SoraTimberNanite") + TEXTURES
FINAL_POST_PROCESS = {"AutoExposureMethod": 2, "AutoExposureApplyPhysicalCameraExposure": 1, "AutoExposureBias": 0,
                      "CameraISO": 100, "CameraShutterSpeed": 60, "DepthOfFieldFstop": 2.8,
                      "DynamicGlobalIlluminationMethod": 0, "ReflectionMethod": 0, "ScreenSpaceReflectionIntensity": 0,
                      "BloomIntensity": 0, "LensFlareIntensity": 0, "VignetteIntensity": 0, "AmbientOcclusionIntensity": 0,
                      "WhiteTemp": 6500, "WhiteTint": 0,
                      "ColorSaturation": [1]*4, "ColorContrast": [1]*4, "ColorGamma": [1]*4, "ColorGain": [1]*4, "ColorOffset": [0]*4}
EXCLUDED_SHOW_FLAGS = ("DirectionalLights", "Fog", "Atmosphere", "SkyLighting", "GlobalIllumination",
                       "LumenGlobalIllumination", "ReflectionEnvironment", "ScreenSpaceReflections", "LumenReflections")


def object_path(name):
    return ROOT + name + "." + name.rsplit("/", 1)[-1]


def require(value, reason):
    if not value:
        raise ValueError(reason)


def finite_vector(value, length):
    return isinstance(value, list) and len(value) == length and all(
        type(v) in (int, float) and math.isfinite(v) for v in value)


def identities(meta, project, commit):
    """Compare recorded loose packages and source pins, retaining SHA256 results.

    Source commit identifies capture/importer code, not when an ignored package
    was generated. Exact package digests must also match the prior import/reopen
    receipt for any baseline-versus-corrected-material comparison.
    """
    require(re.fullmatch(r"[0-9a-f]{40}", commit or ""), "probe requires exact capture source commit")
    project = project.resolve()
    package_root = project / "Content/Generated/Qualification/DojoTimberProbe"
    expected = {package_root / (n + ".uasset") for n in PACKAGES}
    seen, records = set(), []
    for row in meta.get("asset_files", []):
        path = Path(row["path"])
        require(path.is_absolute() and path == path.resolve() and path not in seen,
                "duplicate, relative or linked probe package")
        require(path.suffix in (".uasset", ".uexp", ".ubulk") and path.with_suffix(".uasset") in expected,
                "unexpected package outside the fixed 31-package probe")
        raw = path.read_bytes()
        require(len(raw) == row["bytes"] and hashlib.md5(raw).hexdigest() == row["md5"], "probe package changed after capture")
        seen.add(path)
        records.append({"path": str(path.relative_to(project)), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
    require({p for p in seen if p.suffix == ".uasset"} == expected, "incomplete 31-package probe inventory")
    actual = {p.resolve() for p in package_root.rglob("*") if p.suffix in (".uasset", ".uexp", ".ubulk")}
    require(actual == seen, "probe package files added or omitted")
    inputs = meta.get("source_inputs", [])
    require([r.get("path") for r in inputs] == list(INPUTS), "capture/importer input inventory differs")
    source = []
    for row in inputs:
        name = row["path"]
        saved = subprocess.run(["git", "-C", str(project), "show", f"{commit}:{name}"], capture_output=True, check=True).stdout
        current = (project / name).read_bytes()
        require(current == saved and len(saved) == row["bytes"] and hashlib.md5(saved).hexdigest() == row["md5"],
                "probe capture/importer provenance differs from committed source")
        source.append({"path": name, "sha256": hashlib.sha256(saved).hexdigest()})
    return {"source_commit": commit, "source_inputs": source, "packages": records,
            "package_origin": "match exact SHA256 values to prior import/reopen receipt; capture source alone does not date generated assets"}


def validate_metadata(meta, names, width, height):
    require(isinstance(meta, dict) and meta.get("schema") == SCHEMA and meta.get("scope") == SCOPE, "unexpected probe schema/scope")
    require(all(meta.get(k) is True for k in ("passed", "restored", "packages_unchanged")), "probe failed or did not restore unchanged packages/session")
    sm6 = meta.get("sm6_requested")
    require(type(sm6) is bool and meta.get("nanite_eligible") is sm6, "requested/capable shader model mismatch")
    require(meta.get("rhi") == "Metal" and meta.get("null_rhi") is False and meta.get("shader_platform") == ("METAL_SM6" if sm6 else "METAL_SM5"), "not the requested actual Metal shader platform")
    require(bool(meta.get("adapter")) and meta.get("viewport") == [width, height] and meta.get("fixture_origin") == [1000000]*3, "missing actual device/fixture identity")
    meshes = meta.get("meshes", [])
    require([m.get("name") for m in meshes] == list(NAMES), "probe must observe exactly five dense and four authored conventional meshes")
    for i, mesh in enumerate(meshes):
        name, dense = NAMES[i], i < 5
        require(mesh.get("mesh") == object_path(name) and mesh.get("kind") == ("dense_nanite_source" if dense else "authored_conventional_pool"), "mesh identity/kind differs")
        require(mesh.get("has_nanite_data") is dense and mesh.get("authoring_nanite_enabled") is dense and mesh.get("disallow_nanite") is False and mesh.get("force_disable_nanite") is False,
                "mesh resource/configuration differs; resources alone never prove a draw")
        if dense and not sm6:
            require(mesh.get("has_platform_fallback") is True, "dense asset has no generated fallback on actual SM5 platform")
        require(type(mesh.get("nanite_input_triangles")) in (int, float) and (mesh["nanite_input_triangles"] > 0 if dense else mesh["nanite_input_triangles"] == 0), "unexpected Nanite CPU input count")
        require(mesh.get("source_triangles", 0) > 0 and mesh.get("lod0_render_triangles", 0) > 0 and mesh.get("uv_channels", 0) >= 4, "missing CPU source/fallback/UV observations")
        require(finite_vector(mesh.get("bounds_origin"), 3) and max(abs(a-1000000) for a in mesh["bounds_origin"]) < .1 and
                finite_vector(mesh.get("bounds_extent"), 3) and all(v > 0 for v in mesh["bounds_extent"]), "invalid isolated fixture bounds")
        mats = mesh.get("materials", [])
        require(len(mats) == 1 and mats[0].get("material") == object_path("MI_" + name) and mats[0].get("parent") == object_path("M_SoraTimberNanite" if dense else "M_SoraTimber"), "loaded material/parent differs from saved reviewed probe")
        require(isinstance(mats[0].get("textures"), dict) and isinstance(mats[0].get("scalars"), dict), "missing actual material parameters")
        if not dense:
            for parameter, suffix in (("NormalMap", "NormalDX"), ("MasksMap", "Masks")):
                require(mats[0]["textures"].get(parameter) == object_path("Textures/T_" + name.removeprefix("SM_") + "_" + suffix), "authored pool texture link differs")
        uvs = mesh.get("uv_observations", [])
        require([u.get("channel") for u in uvs] == [2, 3], "saved UV2/UV3 missing")
        for uv in uvs:
            require(0 < uv.get("scanned_vertex_instances", 0) <= 3000000 and finite_vector(uv.get("min"), 2) and finite_vector(uv.get("max"), 2) and
                    all(a <= b for a, b in zip(uv["min"], uv["max"])), "invalid saved UV range/count")
            samples = uv.get("samples", [])
            require(0 < len(samples) <= 8 and len({s.get("vertex_instance") for s in samples}) == len(samples), "UV samples absent, duplicated or unbounded")
            for sample in samples:
                require(finite_vector(sample.get("uv"), 2) and all(lo <= v <= hi for lo, v, hi in zip(uv["min"], sample["uv"], uv["max"])), "UV sample outside saved range")
    expected = [(n, view, mode) for n in NAMES for view, mode in
                ([("full", m) for m in ("Lit", "Mask", "Triangles")] if sm6 else [("full", "Lit")]) + [("detail", "Lit")]]
    frames = meta.get("frames", [])
    require(len(frames) == meta.get("frame_count") == len(expected), "wrong bounded original frame count")
    require(len(names) == len(set(names)) == len(expected), "duplicate or missing original images")
    require([(f.get("mesh_name"), f.get("view"), f.get("mode")) for f in frames] == expected and
            names == ["-".join(row) + ".png" for row in expected], "probe original sequence order differs")
    observed, previous, full_cameras = set(), -1, {}
    for frame in frames:
        identity = (frame.get("mesh_name"), frame.get("view"), frame.get("mode"))
        require(identity in expected and identity not in observed, "unexpected or duplicate mesh/view/mode")
        observed.add(identity)
        name = "-".join(identity)
        require(frame.get("name") == name and frame.get("file") == name + ".png" and frame["file"] in names, "frame-to-original association differs")
        require(frame.get("paused") is True and frame.get("hud_hidden") is True and frame.get("visible_fixture_meshes") == 1 and frame.get("settle_seconds", 0) >= 3, "fixture not isolated, paused, hidden or settled")
        shader = frame.get("material_render_readback", {})
        require(all(shader.get(k) is True for k in ("proxy_present", "shader_map_valid", "shader_map_complete")) and
                all(shader.get(k) is False for k in ("used_fallback_proxy", "default_material")) and bool(shader.get("resource_asset")),
                "render-thread base material resolved absent, incomplete or fallback shader")
        require(finite_vector(frame.get("camera"), 3) and finite_vector(frame.get("rotation"), 3) and abs(frame.get("fov", 0)-35) < .01, "missing actual camera")
        require(type(frame.get("request_frame")) in (int, float) and previous < frame["request_frame"] <= frame.get("screenshot_processed_frame", -1), "invalid screenshot frame chronology")
        previous = frame["screenshot_processed_frame"]
        require(frame.get("final_view_observations") == 1 and type(frame.get("final_view_frame")) in (int, float) and
                frame["request_frame"] <= frame["final_view_frame"] <= previous, "final blended settings are not bound to exactly one screenshot view")
        final = frame.get("final_post_process", {})
        for key, expected_value in FINAL_POST_PROCESS.items():
            actual_value = final.get(key)
            if isinstance(expected_value, list):
                require(finite_vector(actual_value, 4) and all(abs(a-b) < 1e-5 for a, b in zip(actual_value, expected_value)), "nonneutral final post-process " + key)
            else:
                require(type(actual_value) in (int, float) and math.isfinite(actual_value) and abs(actual_value-expected_value) < 1e-5, "unexpected final post-process " + key)
        flags = frame.get("final_show_flags", {})
        require(all(flags.get(key) is False for key in EXCLUDED_SHOW_FLAGS), "production sun/GI/reflections or atmosphere leak into fixture view")
        if identity[1] == "full":
            camera = frame["camera"] + frame["rotation"] + [frame["fov"]]
            require(full_cameras.setdefault(identity[0], camera) == camera, "paired visualization cameras moved")
        diagnostic = identity[2] != "Lit"
        require(frame.get("active_visualization") == (identity[2] if diagnostic else "None") and frame.get("show_visualize_nanite") is diagnostic and
                (frame.get("active_mode_id", -1) >= 0 if diagnostic else frame.get("active_mode_id") == -1), "actual renderer visualization mismatch")
        cvars = frame.get("cvars", {})
        values = {"r.Nanite.Visualize": identity[2] if diagnostic else "off", "r.Nanite.Visualize.Composite": "1", "r.Nanite.Visualize.EdgeDetect": "0", "r.Nanite.Visualize.DebugShading": "0", "r.Nanite.ProxyRenderMode": "0", "r.ScreenPercentage": "100"}
        if sm6:
            values["r.Nanite"] = "1"
        require(all(cvars.get(k) == v for k, v in values.items()), "capture visualization/render settings differ")
    return sm6


def inspect(meta, images, width, height, decode):
    sm6 = validate_metadata(meta, list(images), width, height)
    decoded = {name: decode(raw) for name, raw in images.items()}
    require(all(value[:2] == (width, height) for value in decoded.values()), "original dimensions differ")
    result = {"schema": "sora-arena.timber-probe-pixels.v1", "scope": SCOPE, "actual_shader_platform": meta["shader_platform"],
              "adapter": meta["adapter"], "nanite_draw_evidence": False, "hardware_m1_qualified": False,
              "release_qualified": False, "human_geometry_material_review_required": True, "errors": [], "meshes": {}}
    for i, name in enumerate(NAMES):
        dense = i < 5
        observation = {"kind": "dense_nanite_source" if dense else "authored_conventional_pool",
                       "render_path": ("Nanite candidate" if dense else "authored conventional control") if sm6 else
                                      ("generated dense-asset fallback" if dense else "authored conventional pool")}
        if sm6:
            metric = PIXELS.pixel_evidence(*(decoded[f"{name}-full-{m}.png"] for m in ("Lit", "Mask", "Triangles")))
            observation["pixels"] = metric
            valid = metric["nonzero_candidate_coverage"] if dense else metric["mask_red_candidates"] >= 24 and metric["mask_green_candidates"] == 0
            observation["expected_visible_path_observed"] = valid
            if not valid:
                result["errors"].append(name + (": no attributable Mask/Triangles Nanite evidence" if dense else ": conventional control lacks red coverage or has unexpected green coverage"))
        result["meshes"][name] = observation
    result["nanite_draw_evidence"] = sm6 and not result["errors"]
    result["qualification_limit"] = "pixel candidates require original-image human attribution; not exact GPU counters, visual quality or performance; SM5 originals alone do not prove M1 hardware"
    return result
