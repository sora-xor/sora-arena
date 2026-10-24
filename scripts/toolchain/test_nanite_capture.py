"""Synthetic analytic/negative tests of evidence transport, not renderer proof."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

SPEC = importlib.util.spec_from_file_location("capture_report", Path(__file__).with_name("verify-capture-report.py"))
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)
N = VERIFY.nanite_capture_validation
WIDTH, HEIGHT = 64, 48
SOURCE_BYTES = b"synthetic current chapter data; never authored placement evidence"


def png(kind):
    def chunk(name, data):
        return struct.pack(">I", len(data)) + name + data + struct.pack(">I", zlib.crc32(name + data))
    colors = [(220, 70, 80), (60, 200, 230), (210, 180, 50), (170, 60, 200)]
    rows = []
    for y in range(HEIGHT):
        row = bytearray([0])
        for x in range(WIDTH):
            if kind == "lit": color = (110, 90, 60)
            elif kind == "green-material": color = (60, 220, 50)
            elif kind == "mask": color = (55, 172, 30) if x < WIDTH // 2 else (182, 45, 30)
            elif kind == "red": color = (182, 45, 30)
            elif kind == "triangle": color = colors[(x // 3 + y // 3) % len(colors)]
            else: color = (0, 0, 0)
            row.extend(color)
        rows.append(row)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", WIDTH, HEIGHT, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"".join(rows))) + chunk(b"IEND", b""))


def metadata(sm6=True):
    frames = []
    for ci, cam in enumerate(N.CAMERAS):
        for mode in (N.MODES if sm6 else ("Lit",)):
            frames.append({"name": f"{cam}-{mode}", "file": f"{cam}-{mode}.png", "camera_id": cam, "mode": mode,
                "camera": N.LOCATIONS[ci][:], "rotation": N.ROTATIONS[ci][:], "fov": 94,
                "request_frame": len(frames) * 200 + 10, "screenshot_processed_frame": len(frames) * 200 + 11,
                "settle_seconds": 3.1, "active_visualization": mode if mode != "Lit" else "None",
                "active_mode_id": 1 if mode != "Lit" else -1, "show_visualize_nanite": mode != "Lit",
                "paused": True, "hud_hidden": True,
                "cvars": {"r.Nanite": "1", "r.Nanite.ProxyRenderMode": "0", "r.ScreenPercentage": "100",
                    "r.AntiAliasingMethod": "4", "sora.HallInstanced": "1", "r.Nanite.Visualize": mode if mode != "Lit" else "off",
                    "r.Nanite.Visualize.Composite": "1", "r.Nanite.Visualize.EdgeDetect": "0", "r.Nanite.Visualize.DebugShading": "0"}})
    return {"schema": N.SCHEMA, "scope": N.SCOPE, "passed": True, "restored": True, "null_rhi": False,
        "sm6_requested": sm6, "nanite_eligible": sm6, "shader_platform": "METAL_SM6" if sm6 else "METAL_SM5", "rhi": "Metal",
        "adapter": "Synthetic M2 fixture (not hardware evidence)", "viewport": [WIDTH, HEIGHT], "frames": frames, "frame_count": len(frames),
        "timber_placement_coverage": dict(N.COVERAGE_PENDING),
        "coverage_inputs": [{"path": path, "exists": True, "bytes": len(SOURCE_BYTES), "md5": hashlib.md5(SOURCE_BYTES).hexdigest()}
                            if index < 8 else {"path": path, "exists": False} for index, path in enumerate(N.COVERAGE_INPUTS)],
        "meshes": [{"component": "/Engine/Entry.WorldBuilder.Hall", "mesh": "/Game/Generated/Environment/DojoKit/SM_DojoCeiling.SM_DojoCeiling",
            "asset_family": "DojoKit",
            "has_nanite_data": True, "disallow_nanite": False, "force_disable_nanite": False,
            "bounds_origin": [9500, 0, 700], "bounds_extent": [1000, 800, 30], "instances": 30, "materials": ["M_Arch"]}]}


def originals(meta):
    modes = {"Lit": "lit", "Mask": "mask", "Triangles": "triangle"}
    return {frame["file"]: png(modes[frame["mode"]]) for frame in meta["frames"]}


def add_timber(meta, name="SM_DojoTimberColumn_8000_m1300_11600_1300_S0_B00"):
    mesh = copy.deepcopy(meta["meshes"][0])
    mesh.update(component=f"/Engine/Entry.WorldBuilder.{name}", asset_family="DojoTimbers",
                mesh=f"/Game/Generated/Environment/DojoTimbers/{name}.{name}", instances=1)
    mesh.pop("package_file", None)
    meta["meshes"].append(mesh)
    return mesh


class NanitePixels(unittest.TestCase):
    def inspect(self, meta=None, images=None):
        meta = metadata() if meta is None else meta
        images = originals(meta) if images is None else images
        for data in images.values(): self.assertEqual(VERIFY.png_dimensions(data), (WIDTH, HEIGHT))
        return N.inspect(meta, images, WIDTH, HEIGHT, VERIFY.bow_capture_validation.rgb8)

    def test_shader_derived_green_red_and_triangle_changes_are_observed_separately(self):
        result = self.inspect()
        self.assertTrue(result["nanite_draw_evidence"])
        self.assertTrue(result["human_geometry_review_required"])
        self.assertFalse(result["release_qualified"])
        for camera in result["cameras"].values():
            self.assertGreater(camera["mask_green_candidates"], 24)
            self.assertGreater(camera["mask_red_candidates"], 24)
            self.assertGreaterEqual(camera["triangle_color_bins_at_green"], 4)

    def test_capability_and_resource_flags_cannot_pass_lit_copied_into_all_modes(self):
        meta = metadata()
        result = self.inspect(meta, {f["file"]: png("lit") for f in meta["frames"]})
        self.assertFalse(result["nanite_draw_evidence"])
        self.assertEqual(len(result["errors"]), 2)

    def test_conventional_red_diagnostic_is_preserved_as_failed_draw_evidence(self):
        meta = metadata()
        images = originals(meta)
        for cam in N.CAMERAS: images[f"{cam}-Mask.png"] = png("red")
        result = self.inspect(meta, images)
        self.assertFalse(result["nanite_draw_evidence"])
        self.assertGreater(result["cameras"]["ceiling"]["mask_red_candidates"], 0)

    def test_ordinary_green_material_alone_is_not_nanite_coverage(self):
        meta = metadata()
        result = self.inspect(meta, {f["file"]: png("green-material") for f in meta["frames"]})
        self.assertFalse(result["nanite_draw_evidence"])
        self.assertEqual(result["cameras"]["entry"]["mask_green_candidates"], 0)

    def test_nanite_geometry_resource_absence_or_component_disable_cannot_pass(self):
        for key, value in (("has_nanite_data", False), ("disallow_nanite", True), ("force_disable_nanite", True)):
            with self.subTest(key=key):
                meta = metadata(); meta["meshes"][0][key] = value
                self.assertFalse(self.inspect(meta)["nanite_draw_evidence"])

    def test_mask_alone_cannot_pass_without_resolved_triangles(self):
        meta = metadata(); images = originals(meta)
        for cam in N.CAMERAS: images[f"{cam}-Triangles.png"] = images[f"{cam}-Lit.png"]
        self.assertFalse(self.inspect(meta, images)["nanite_draw_evidence"])

    def test_sm5_is_only_conventional_evidence_and_never_m1_qualification(self):
        result = self.inspect(metadata(False))
        self.assertEqual(result["errors"], [])
        self.assertFalse(result["nanite_draw_evidence"])
        self.assertFalse(result["hardware_m1_qualified"])
        self.assertIn("not M1 hardware proof", result["evidence"])

    def test_one_drawn_timber_cannot_stand_in_for_expected_placement_coverage(self):
        for sm6 in (True, False):
            meta = metadata(sm6); add_timber(meta)
            result = self.inspect(meta)
            self.assertFalse(result["nanite_draw_evidence"])
            self.assertFalse(result["timber_placement_coverage"]["qualified"])
            self.assertEqual(result["observed_families"]["DojoTimbers"]["instances"], 1)
            self.assertEqual(result["timber_placement_coverage"]["observed_kinds"], {"column_placement": 1})
            self.assertIn("manifest contract required", result["errors"][0])

    def test_all_known_timber_classes_remain_observations_not_admission(self):
        meta = metadata()
        for name in ("SM_DojoTimberRail_Nuki_8000_m1300_11600_1300_S2_B13", "SM_DojoTimberFloor_01",
                     "SM_DojoTimberColumn_MAC_Wall_02", "SM_DojoTimberRail_MAC_Cornice_03", "SM_DojoTimberFloor_MAC_00"):
            add_timber(meta, name)
        result = self.inspect(meta)
        self.assertEqual(len(result["timber_placement_coverage"]["observed_kinds"]), 5)
        self.assertFalse(result["nanite_draw_evidence"])
        self.assertEqual(result["observed_families"]["DojoKit"]["components"], 1)

    def test_duplicate_unique_placements_unknown_classes_and_wrong_family_fail(self):
        for mutation in ("instances", "duplicate", "unknown", "family", "object"):
            with self.subTest(mutation=mutation):
                meta = metadata(); mesh = add_timber(meta)
                if mutation == "instances": mesh["instances"] = 2
                elif mutation == "duplicate":
                    duplicate = copy.deepcopy(mesh); duplicate["component"] += "Duplicate"; meta["meshes"].append(duplicate)
                elif mutation == "unknown": mesh["mesh"] = "/Game/Generated/Environment/DojoTimbers/Random.Random"
                elif mutation == "family": mesh["asset_family"] = "DojoKit"
                else: mesh["mesh"] += "DifferentObject"
                with self.assertRaises(ValueError): self.inspect(meta)

    def test_missing_duplicated_unexpected_or_forged_coverage_contract_fails(self):
        for mutation in ("missing", "duplicate", "unexpected", "chapter", "forged", "empty_expected", "numeric_false"):
            with self.subTest(mutation=mutation):
                meta = metadata()
                if mutation == "missing": meta["coverage_inputs"].pop()
                elif mutation == "duplicate": meta["coverage_inputs"][-1] = meta["coverage_inputs"][0]
                elif mutation == "unexpected": meta["coverage_inputs"][0]["path"] = "Content/Data/campaign/old.json"
                elif mutation == "chapter": meta["coverage_inputs"][0] = {"path": N.COVERAGE_INPUTS[0], "exists": False}
                elif mutation == "forged": meta["timber_placement_coverage"]["qualified"] = True
                elif mutation == "numeric_false": meta["timber_placement_coverage"]["qualified"] = 0
                else: meta["timber_placement_coverage"]["expected_placements"] = []
                with self.assertRaises(ValueError): self.inspect(meta)

    def test_timber_sources_with_only_old_kit_loaded_do_not_pass_as_complete(self):
        meta = metadata()
        meta["coverage_inputs"][8].update(exists=True, bytes=len(SOURCE_BYTES), md5=hashlib.md5(SOURCE_BYTES).hexdigest())
        result = self.inspect(meta)
        self.assertFalse(result["nanite_draw_evidence"])
        self.assertEqual(result["observed_families"]["DojoTimbers"]["instances"], 0)
        self.assertIn("coverage is incomplete", result["errors"][0])

    def test_changed_camera_cvars_wrong_modes_and_partial_sequences_fail(self):
        changes = (("camera", [8421, 0, 154]), ("rotation", [4, 1, 0]), ("fov", 90), ("settle_seconds", 2.9),
                   ("paused", False), ("hud_hidden", False), ("active_visualization", "Lit"),
                   ("show_visualize_nanite", False), ("request_frame", 0), ("screenshot_processed_frame", 2))
        for key, value in changes:
            with self.subTest(key=key):
                meta = metadata(); meta["frames"][1][key] = value
                with self.assertRaises(ValueError): self.inspect(meta)
        meta = metadata(); meta["frames"][1]["cvars"]["r.ScreenPercentage"] = "50"
        with self.assertRaises(ValueError): self.inspect(meta)
        meta = metadata(); images = originals(meta); images.pop("ceiling-Triangles.png")
        with self.assertRaises(ValueError): self.inspect(meta, images)

    def test_invalid_platform_scope_restore_types_and_identity_fail(self):
        for key, value in (("passed", 1), ("restored", False), ("scope", "qualified"), ("shader_platform", "METAL_SM5"),
                           ("rhi", "Null"), ("null_rhi", True), ("frame_count", True), ("sm6_requested", 1)):
            with self.subTest(key=key):
                meta = metadata(); meta[key] = value
                with self.assertRaises(ValueError): self.inspect(meta)
        for key, value in (("camera", [float("nan"), 0, 154]), ("request_frame", True)):
            meta = metadata(); meta["frames"][0][key] = value
            with self.assertRaises(ValueError): self.inspect(meta)
        meta = metadata(); meta["meshes"][0]["mesh"] = "/Engine/BasicShapes/Cube"
        with self.assertRaises(ValueError): self.inspect(meta)


class NaniteArchive(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)
        self.folder = self.project / "Saved/Screenshots/SoraNaniteDraw/run"
        self.folder.mkdir(parents=True)
        self.output = self.project / "archive"
        self.meta = metadata(); self.images = originals(self.meta)
        asset = self.project / "Content/Generated/Environment/DojoKit/SM_DojoCeiling.uasset"
        asset.parent.mkdir(parents=True); asset.write_bytes(b"synthetic package bytes, never engine evidence")
        self.asset = asset
        self.meta["meshes"][0]["package_file"] = str(asset)
        self.meta["asset_files"] = [{"path": str(asset), "bytes": asset.stat().st_size, "md5": hashlib.md5(asset.read_bytes()).hexdigest()}]
        for record in self.meta["coverage_inputs"]:
            if record["exists"]:
                path = self.project / record["path"]; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(SOURCE_BYTES)
        self.report = {"tests": [{"fullTestPath": "SoraCapture.NaniteDraw.DojoSM6"}], "devices": [{"renderMode": "SM6"}]}
        self.write()

    def write(self):
        for name, data in self.images.items(): (self.folder / name).write_bytes(data)
        self.raw = json.dumps(self.meta).encode()
        (self.folder / "capture.json").write_bytes(self.raw)
        self.log = "\n".join(f"LogTemp: Display: SORA_NANITE_DRAW_FRAME {self.folder / name}" for name in self.images)

    def archive(self):
        return VERIFY.archive_frames(self.log, self.report, self.project, self.project, self.output, 1, WIDTH, HEIGHT)

    def test_original_png_json_hashes_and_actual_package_binding_are_retained(self):
        frames = self.archive()
        self.assertEqual(len(frames), 6)
        for f in frames:
            self.assertEqual((self.output / f["path"]).read_bytes(), self.images[Path(f["source"]).name])
            self.assertEqual((self.output / f["observations"]).read_bytes(), self.raw)
        review = json.loads((self.output / frames[0]["pixel_review"]).read_text())
        self.assertEqual(review["asset_files"][0]["sha256"], hashlib.sha256(self.asset.read_bytes()).hexdigest())
        source = next(item for item in review["asset_files"] if item.get("role") == "unqualified_placement_coverage_input" and item["exists"])
        self.assertEqual(source["sha256"], hashlib.sha256(SOURCE_BYTES).hexdigest())

    def test_timber_package_and_failed_coverage_keep_every_original(self):
        mesh = add_timber(self.meta)
        name = mesh["mesh"].split("/")[-1].split(".")[0]
        asset = self.project / "Content/Generated/Environment/DojoTimbers" / (name + ".uasset")
        asset.parent.mkdir(parents=True); asset.write_bytes(b"synthetic timber package")
        mesh["package_file"] = str(asset)
        self.meta["asset_files"].append({"path": str(asset), "bytes": asset.stat().st_size, "md5": hashlib.md5(asset.read_bytes()).hexdigest()})
        self.write()
        with self.assertRaisesRegex(VERIFY.NaniteDrawEvidenceError, "timber placement coverage") as failure: self.archive()
        self.assertEqual(len(failure.exception.frames), 6)
        saved = self.output / "frames/SoraNaniteDraw/run"
        self.assertEqual((saved / "capture.json").read_bytes(), self.raw)
        review = json.loads((saved / "pixel-review.json").read_text())
        self.assertTrue(any(item["sha256"] == hashlib.sha256(asset.read_bytes()).hexdigest()
                            for item in review["asset_files"] if "sha256" in item))
        self.assertFalse(review["timber_placement_coverage"]["qualified"])

    def test_stale_missing_or_newly_present_coverage_inputs_fail(self):
        for mutation in ("changed", "missing", "appeared"):
            with self.subTest(mutation=mutation):
                if mutation == "appeared":
                    path = self.project / N.COVERAGE_INPUTS[8]; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(SOURCE_BYTES)
                else:
                    path = self.project / N.COVERAGE_INPUTS[0]
                    if mutation == "changed": path.write_bytes(b"different chapter layout")
                    else: path.unlink()
                with self.assertRaisesRegex(ValueError, "coverage input.*changed since runtime"):
                    N.asset_identities(self.meta, self.project)
                if mutation == "appeared": path.unlink()
                else: path.write_bytes(SOURCE_BYTES)

    def test_cross_family_and_orphan_package_records_fail(self):
        for mutation in ("cross-family", "orphan"):
            meta = copy.deepcopy(self.meta)
            path = self.project / "Content/Generated/Environment/DojoTimbers/SM_DojoCeiling.uasset"
            path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(self.asset.read_bytes())
            record = {"path": str(path), "bytes": path.stat().st_size, "md5": hashlib.md5(path.read_bytes()).hexdigest()}
            if mutation == "cross-family":
                meta["meshes"][0]["package_file"] = str(path); meta["asset_files"] = [record]
            else: meta["asset_files"].append(record)
            with self.assertRaises(ValueError): N.asset_identities(meta, self.project)

    def test_zero_coverage_failure_keeps_originals_metadata_and_analysis(self):
        self.meta["meshes"][0]["has_nanite_data"] = False
        self.images = {name: png("lit") for name in self.images}; self.write()
        with self.assertRaisesRegex(VERIFY.NaniteDrawEvidenceError, "Nanite draw evidence") as failure: self.archive()
        self.assertEqual(len(failure.exception.frames), 6)
        for frame in failure.exception.frames:
            self.assertEqual(frame["sha256"], hashlib.sha256((self.output / frame["path"]).read_bytes()).hexdigest())
        saved = self.output / "frames/SoraNaniteDraw/run"
        self.assertEqual((saved / "capture.json").read_bytes(), self.raw)
        self.assertEqual((saved / "entry-Mask.png").read_bytes(), self.images["entry-Mask.png"])
        review = json.loads((saved / "pixel-review.json").read_text())
        self.assertFalse(review["nanite_draw_evidence"])
        self.assertEqual(len(review["errors"]), 3)

    def test_no_frames_or_replayed_acknowledgements_cannot_pass(self):
        self.log = ""
        with self.assertRaisesRegex(ValueError, "no screenshot"): self.archive()
        self.log = f"LogAutomationController: Display: SORA_NANITE_DRAW_FRAME {self.folder / 'entry-Lit.png'} [log]"
        with self.assertRaisesRegex(ValueError, "no screenshot"): self.archive()

    def test_duplicate_missing_stale_and_wrong_test_metadata_fail(self):
        self.log += "\n" + self.log.splitlines()[0]
        with self.assertRaisesRegex(ValueError, "duplicate"): self.archive()
        self.output = self.project / "archive2"; self.write(); (self.folder / "capture.json").unlink()
        with self.assertRaises(FileNotFoundError): self.archive()
        self.output = self.project / "archive3"; self.write(); os.utime(self.folder / "capture.json", ns=(0, 0))
        with self.assertRaisesRegex(ValueError, "stale"): self.archive()
        self.output = self.project / "archive4"; self.write()
        self.report["tests"][0]["fullTestPath"] = "SoraCapture.NaniteDraw.DojoSM5"
        with self.assertRaisesRegex(ValueError, "requested SM6/SM5"): self.archive()

    def test_modified_missing_or_external_generated_package_fails(self):
        self.asset.write_bytes(b"modified after runtime")
        with self.assertRaisesRegex(ValueError, "changed since"): self.archive()
        self.asset.unlink(); self.output = self.project / "archive2"
        with self.assertRaises(FileNotFoundError): self.archive()
        self.output = self.project / "archive3"; self.meta["asset_files"][0]["path"] = "/tmp/foreign.uasset"; self.write()
        with self.assertRaises(ValueError): self.archive()

    def test_source_has_engine_only_modes_fixed_cameras_and_restoration(self):
        root = Path(__file__).resolve().parents[2]
        source = (root / "Source/SoraArena/Private/SoraNaniteDrawCapture.cpp").read_text()
        for text in (N.SCHEMA, N.SCOPE, "SORA_NANITE_DRAW_FRAME", "Mesh->HasValidNaniteData()", "FMD5Hash::HashFile", "V->Restore()",
                     "UGameplayStatics::SaveDataToSlot(Profile[I]", "UGameplayStatics::DeleteGameInSlot(Slots[I]", "OldFlags", "OldScreen", "HUD->bShowHUD=ShowHUD"):
            self.assertIn(text, source)
        self.assertNotIn("SetNaniteSettings", source)
        self.assertNotIn("SetMaterial(", source)
        self.assertNotIn("r.Nanite\").Set", source)
        self.assertIn('const TCHAR* Modes[]={TEXT("Lit"),TEXT("Mask"),TEXT("Triangles")};', source)


if __name__ == "__main__":
    unittest.main()
