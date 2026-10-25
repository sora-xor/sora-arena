"""Regression tests for the dojo timber importer's host-side admission checks.

Run: python3 -m unittest scripts/unreal/test_dojo_timber_admission.py

No Unreal: dojo_timber_admission.py is the pure part of
scripts/unreal/import_nyaagyu_dojo_timbers.py.
"""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dojo_timber_admission as A  # noqa: E402

KEY = "Local/ArtCache/NyaagyuDojoTimbers/Unique/SM_DojoTimberColumn_8000_m1300_11600_1300_S0_B00.fbx"
POOL_KEY = "Content/SourceArt/Environment/NyaagyuDojoTimbers/FBX/SM_DojoTimberColumn_MAC_Wall_00.fbx"
MANIFESTS = ["Content/SourceArt/Environment/NyaagyuDojoTimbers/manifest.json",
             "Content/SourceArt/Environment/NyaagyuDojoTimbers/Rails/manifest.json"]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write(path: Path, data: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


class CacheEvidence(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.root, self.moved = base / "project", base / "elsewhere"
        self.root.mkdir()
        self.data = b"dense log"
        self.evidence = {"fbx": {KEY: {"digest": "g1", "sha256": digest(self.data)},
                                 POOL_KEY: {"digest": "g2", "sha256": digest(b"pool")}}}

    def tearDown(self):
        self.tmp.cleanup()

    def test_default_cache_is_the_projects(self):
        cache = A.cache_root(self.root, {})
        self.assertEqual(cache, self.root / "Local/ArtCache")
        write(self.root / KEY, self.data)
        self.assertEqual(A.check_evidence(self.root, cache, KEY, "g1", self.evidence, "col"), self.root / KEY)

    def test_moved_cache_governs_the_dense_fbx(self):
        # The reproduction: evidence and FBX live only in the moved cache, keyed canonically.
        cache = A.cache_root(self.root, {"SORA_ART_CACHE": str(self.moved)})
        moved_file = write(self.moved / KEY.removeprefix("Local/ArtCache/"), self.data)
        self.assertEqual(A.check_evidence(self.root, cache, KEY, "g1", self.evidence, "col"), moved_file)

    def test_moved_cache_never_falls_back_to_the_project_copy(self):
        cache = A.cache_root(self.root, {"SORA_ART_CACHE": str(self.moved)})
        write(self.root / KEY, self.data)
        with self.assertRaisesRegex(A.AdmissionError, "missing"):
            A.check_evidence(self.root, cache, KEY, "g1", self.evidence, "col")

    def test_committed_keys_stay_in_the_project(self):
        cache = A.cache_root(self.root, {"SORA_ART_CACHE": str(self.moved)})
        pool = write(self.root / POOL_KEY, b"pool")
        self.assertEqual(A.check_evidence(self.root, cache, POOL_KEY, "g2", self.evidence, "pool"), pool)

    def test_rejections(self):
        cache = A.cache_root(self.root, {"SORA_ART_CACHE": str(self.moved)})
        target = write(self.moved / KEY.removeprefix("Local/ArtCache/"), self.data)
        with self.assertRaisesRegex(A.AdmissionError, "digest differs"):
            A.check_evidence(self.root, cache, KEY, "other", self.evidence, "col")
        with self.assertRaisesRegex(A.AdmissionError, "no rebuild evidence"):
            A.check_evidence(self.root, cache, KEY, "g1", {"fbx": {}}, "col")
        target.write_bytes(b"edited")
        with self.assertRaisesRegex(A.AdmissionError, "not the file"):
            A.check_evidence(self.root, cache, KEY, "g1", self.evidence, "col")


class Binding(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        files = {"scripts/art/bind_dojo_timbers.py": b"binder", MANIFESTS[0]: b"columns", MANIFESTS[1]: b"rails",
                 "Content/Data/campaign/chapter_01.json": b"{}", "Content/Data/campaign/chapter_02.json": b"[]"}
        for rel, data in files.items():
            write(self.root / rel, data)
        self.binding = {
            "schema": A.BINDING_SCHEMA,
            "binder": "scripts/art/bind_dojo_timbers.py", "binder_sha256": digest(b"binder"),
            "manifests": {MANIFESTS[0]: digest(b"columns"), MANIFESTS[1]: digest(b"rails")},
            "campaign": {"Content/Data/campaign/chapter_01.json": digest(b"{}"),
                         "Content/Data/campaign/chapter_02.json": digest(b"[]")},
        }

    def tearDown(self):
        self.tmp.cleanup()

    def check(self, binding=None):
        return A.check_binding(self.root, json.loads(json.dumps(binding or self.binding)), MANIFESTS)

    def test_current_binding_passes(self):
        self.assertEqual(self.check()["schema"], A.BINDING_SCHEMA)

    def test_changed_chapter_rejects(self):
        write(self.root / "Content/Data/campaign/chapter_02.json", b'["moved hall"]')
        with self.assertRaisesRegex(A.AdmissionError, "chapter_02.json changed"):
            self.check()

    def test_added_and_missing_chapters_reject(self):
        write(self.root / "Content/Data/campaign/chapter_03.json", b"{}")
        with self.assertRaisesRegex(A.AdmissionError, "not the ones bound"):
            self.check()
        (self.root / "Content/Data/campaign/chapter_03.json").unlink()
        (self.root / "Content/Data/campaign/chapter_02.json").unlink()
        with self.assertRaisesRegex(A.AdmissionError, "not the ones bound"):
            self.check()

    def test_changed_manifest_binder_or_schema_rejects(self):
        write(self.root / MANIFESTS[1], b"rails, rebuilt")
        with self.assertRaisesRegex(A.AdmissionError, "Rails/manifest.json changed"):
            self.check()
        write(self.root / MANIFESTS[1], b"rails")
        write(self.root / "scripts/art/bind_dojo_timbers.py", b"binder, edited")
        with self.assertRaisesRegex(A.AdmissionError, "binder changed"):
            self.check()
        with self.assertRaisesRegex(A.AdmissionError, "schema"):
            self.check({**self.binding, "schema": "v0"})

    def test_other_manifests_reject(self):
        with self.assertRaisesRegex(A.AdmissionError, "other manifests"):
            self.check({**self.binding, "manifests": {MANIFESTS[0]: digest(b"columns")}})


if __name__ == "__main__":
    unittest.main()
