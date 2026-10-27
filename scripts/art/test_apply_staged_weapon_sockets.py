"""Source-only mutation and interrupted-write tests; no Blender or Unreal."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import apply_staged_weapon_sockets as A


class StagedInstall(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.asset = "SM_Weapon_02"
        self.kit = "W02_Kusarigama"
        self.folder = f"{A.RUNTIME}/{self.kit}"
        self.file = f"{self.folder}/{self.asset}.fbx"
        self.record_file = f"{self.folder}/build_record.json"
        self.manifest_file = f"{A.RUNTIME}/manifest.json"
        def file(name, data):
            path = f"{self.folder}/{name}"
            self.write(path, data)
            return {"file": path, "sha256": A.digest(data)}
        lod0 = file(self.asset + ".fbx", b"old-fbx")
        self.record = {"assets": {self.asset: {"lods": [lod0, file("LOD1.fbx", b"lod1")],
                       "sockets": {s: [0, 0, 0] for s in A.G.ADMISSION}}},
                       "blend": file("source.blend", b"source"), "textures": {"Normal": file("normal.png", b"map")}}
        self.write(self.record_file, A.encode(self.record))
        self.manifest = {"files": [{"file": f, "bytes": len((self.root / f).read_bytes()),
                                    "sha256": A.digest((self.root / f).read_bytes())}
                                   for f in (self.file, self.record_file)], "held_back_blockout": ["W11_PulseCarbine"]}
        self.write(self.manifest_file, A.encode(self.manifest))
        self.staged = self.write("Saved/stage/corrected.fbx", b"new-probed-fbx")
        sockets = {s: {"position": [0, 0, 0], "scale": [1, 1, 1], "forward": [1, 0, 0],
                       "right": [0, 1, 0], "up": [0, 0, 1]} for s in A.G.ADMISSION}
        predicted = {s: {"position_cm" if k == "position" else k: v for k, v in row.items()}
                     for s, row in sockets.items()}
        self.stage = {"mode": "stage", "convention": A.X.SOCKET_FBX, "source": {"head": "fixture"}, "files": [{
            "asset": self.asset, "kit": self.kit, "file": self.file, "provenance": {"head": "fixture"},
            "original_sha256": A.digest(b"old-fbx"), "new_sha256": A.digest(b"new-probed-fbx"),
            "new_path": str(self.staged), "record_sockets": self.record["assets"][self.asset]["sockets"],
            "socket_axes": {s: {"x": [1, 0, 0], "z": [0, 0, 1]} for s in sockets},
            "predicted_original": predicted, "sockets_in_unreal": predicted}]}
        measured = {"sockets": sockets, "materials": [["M"]], "collision": {"convex": 0, "other_simple": 0}}
        self.probe = {"saved_packages": False, "engine": "5.8.3-58210709+++UE5+Release-5.8", "imports": {
            self.asset: {"kit": self.kit, "provenance": {"head": "fixture"}, "same_import_failures": [],
                         "original": {**copy.deepcopy(measured), "sha256": A.digest(b"old-fbx")},
                         "corrected": {**copy.deepcopy(measured), "sha256": A.digest(b"new-probed-fbx")}}}}
        self.save_evidence()

    def write(self, relative, data):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def save_evidence(self):
        self.stage_path = self.write("Saved/stage/report.json", A.encode(self.stage))
        self.probe["stage_reports"] = [{"sha256": A.digest(self.stage_path.read_bytes()), "source": self.stage["source"]}]
        self.receipt = self.write(A.RECEIPT, A.encode({"readback": self.probe, "readback_of": "fixture"}))

    def plan(self):
        return A.prepare(self.root, self.receipt, [self.stage_path], [self.asset], "2026-10-26T00:00:00Z")

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes() for p in (self.root / "Content").rglob("*") if p.is_file()}

    def test_dry_run_writes_nothing_and_install_uses_exact_bytes(self):
        original = self.snapshot()
        plan = self.plan()
        self.assertEqual(self.snapshot(), original)
        archive = self.root / "Saved/apply"
        result = A.install(plan, archive)
        self.assertEqual(result["state"], "installed")
        self.assertEqual((self.root / self.file).read_bytes(), self.staged.read_bytes())
        self.assertEqual((archive / "original" / self.file).read_bytes(), b"old-fbx")
        for path, data in original.items():
            if path not in plan.after:
                self.assertEqual((self.root / path).read_bytes(), data)
        record = A.decode((self.root / self.record_file).read_bytes())
        self.assertEqual(record["assets"][self.asset]["lods"][0]["sha256"], A.digest(b"new-probed-fbx"))
        self.assertEqual(record["blend"], self.record["blend"])
        manifest = A.decode((self.root / self.manifest_file).read_bytes())
        self.assertEqual(manifest["held_back_blockout"], ["W11_PulseCarbine"])
        self.assertFalse(result["runtime_adopted"])

    def test_unprobed_or_mutated_stage_is_refused_before_writes(self):
        original = self.snapshot()
        self.staged.write_bytes(b"different")
        with self.assertRaisesRegex(ValueError, "staged bytes changed"):
            self.plan()
        self.assertEqual(self.snapshot(), original)

    def test_changed_report_cannot_reuse_signed_probe(self):
        self.stage_path.write_bytes(self.stage_path.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "unprobed"):
            self.plan()

    def test_failed_geometry_comparison_is_not_overridden_by_good_sockets(self):
        self.probe["imports"][self.asset]["same_import_failures"] = ["2 degenerate corners"]
        self.save_evidence()
        with self.assertRaisesRegex(ValueError, "comparison failed"):
            self.plan()

    def test_bad_socket_is_regated_not_trusted_from_report_verdict(self):
        self.probe["imports"][self.asset]["corrected"]["sockets"]["Muzzle"]["scale"] = [100, 100, 100]
        self.save_evidence()
        with self.assertRaises(ValueError):
            self.plan()

    def test_unlisted_asset_is_refused(self):
        self.manifest["files"] = [r for r in self.manifest["files"] if r["file"] != self.file]
        self.write(self.manifest_file, A.encode(self.manifest))
        with self.assertRaisesRegex(ValueError, "held/unlisted"):
            self.plan()

    def test_changed_original_is_refused(self):
        self.write(self.file, b"unintegrated-rebuild")
        with self.assertRaisesRegex(ValueError, "changed input"):
            self.plan()

    def test_map_or_lod_changes_after_plan_prevent_install(self):
        for name in ("normal.png", "LOD1.fbx"):
            with self.subTest(name=name):
                path = self.root / self.folder / name
                before = path.read_bytes()
                plan = self.plan()
                path.write_bytes(b"changed")
                archive = self.root / "Saved/apply"
                with self.assertRaisesRegex(ValueError, "input changed after planning"):
                    A.install(plan, archive)
                self.assertFalse(archive.exists())
                path.write_bytes(before)

    def test_partial_write_failure_restores_all_destinations(self):
        original = self.snapshot()
        replace = A.os.replace
        count = 0
        def fail_second(source, dest):
            nonlocal count
            count += 1
            if count == 2:
                raise OSError("simulated disk failure")
            return replace(source, dest)
        archive = self.root / "Saved/apply"
        with patch.object(A.os, "replace", fail_second):
            with self.assertRaisesRegex(OSError, "simulated disk failure"):
                A.install(self.plan(), archive)
        self.assertEqual(self.snapshot(), original)
        self.assertEqual(A.decode((archive / "transaction.json").read_bytes())["state"], "rolled_back")

    def test_receipt_rejects_nonfinite_overflow_and_duplicate_keys(self):
        for raw in (b'{"x":NaN}', b'{"x":Infinity}', b'{"x":1e999}', b'{"x":1,"x":2}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                A.decode(raw)

    def test_symlink_destination_is_refused(self):
        path = self.root / self.file
        duplicate = self.write("Saved/outside.fbx", path.read_bytes())
        path.unlink()
        path.symlink_to(duplicate)
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.plan()


if __name__ == "__main__":
    unittest.main()
