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
        "meshes": [{"component": "/Engine/Entry.WorldBuilder.Hall", "mesh": "/Game/Generated/Environment/DojoKit/SM_DojoCeiling.SM_DojoCeiling",
            "has_nanite_data": True, "disallow_nanite": False, "force_disable_nanite": False,
            "bounds_origin": [9500, 0, 700], "bounds_extent": [1000, 800, 30], "instances": 30, "materials": ["M_Arch"]}]}


def originals(meta):
    modes = {"Lit": "lit", "Mask": "mask", "Triangles": "triangle"}
    return {frame["file"]: png(modes[frame["mode"]]) for frame in meta["frames"]}


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
