"""Tests for the scoped runtime-weapon record (record_runtime_weapon), on throwaway runtime trees.

Run: python3 -m unittest scripts/art/test_record_runtime_weapon.py

Root's decision (Codex, 2026-10-25): record W18 only; never re-record every
weapon, or clear unrelated errors by refreshing their hashes. The fixture's
other weapon has deliberately stale entries, and they must stay exactly as
they were.
"""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import record_runtime_weapon as R  # noqa: E402

RT = R.RUNTIME_REL
SRC = "Local/ThirdPartyRaw/cc0/ambientcg/Leather014/Leather014_2K-JPG_Color.jpg"
GENS = ["scripts/art/create_runtime_weapon_yumi.py", "scripts/art/create_runtime_weapon_lib.py",
        "scripts/art/yumi_nigiri.py", "scripts/art/yumi_ya.py"]


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def put(root: Path, path: str, data: bytes):
    p = root / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    return {"file": path, "bytes": len(data), "sha256": sha(data)}


def stale(path: str):
    return {"file": path, "bytes": 1, "sha256": "f" * 64}


def tree(root: Path):
    """A runtime tree after a W18 rebuild, and its manifest from before it."""
    record = {"id": 18, "key": "W18_Yumi", "builder": GENS[0], "library": GENS[1], "textures": {}, "renders": [],
              "sources": [SRC]}
    put(root, f"{RT}/W18_Yumi/SM_Weapon_18.fbx", b"new bow")
    put(root, f"{RT}/W18_Yumi/SM_Weapon_18_Ya.fbx", b"new arrow")
    put(root, f"{RT}/W18_Yumi/build_record.json", json.dumps(record).encode())
    put(root, f"{RT}/W18_Yumi/Rig/SK_Weapon_18.fbx", b"rig")
    put(root, f"{RT}/W18_Yumi/Rig/manifest.ledger.json", b"{}")          # the rig keeps its own ledger
    put(root, f"{RT}/W18_Yumi/SM_Weapon_18.blend1", b"backup")
    put(root, f"{RT}/Renders/SM_Weapon_18_Profile.png", b"new render")
    put(root, f"{RT}/Renders/SM_Weapon_18_Ya_Profile.png", b"arrow render")
    put(root, f"{RT}/Renders/SM_Weapon_01_Profile.png", b"other render, rebuilt elsewhere")
    put(root, f"{RT}/W01_Arc/SM_Weapon_01.fbx", b"other weapon, rebuilt elsewhere")
    put(root, f"{RT}/W19_Yari/SM_Weapon_19.fbx", b"a weapon after W18")
    put(root, SRC, b"leather scan")
    for g in GENS:
        put(root, g, f"# {g}".encode())
    files = [stale(f"{RT}/README.md"), stale(f"{RT}/Renders/SM_Weapon_01_Profile.png"),
             stale(f"{RT}/Renders/SM_Weapon_18_Profile.png"), stale(f"{RT}/W01_Arc/SM_Weapon_01.fbx"),
             stale(f"{RT}/W18_Yumi/SM_Weapon_18.fbx"), stale(f"{RT}/W18_Yumi/removed_old_map.png"),
             stale(f"{RT}/W18_Yumi/build_record.json"), stale(f"{RT}/W19_Yari/SM_Weapon_19.fbx")]
    manifest = {"schema_version": 2, "tier": "OWN", "asset_id": "runtime-weapons", "name": "fixture",
                "license": "project-owned", "generator_scripts": GENS[:2], "regenerate": "build_all",
                "generated_at_utc": "2026-09-26T11:52:51+00:00", "storage": "repo-lfs",
                "weapons": [{"id": 1, "key": "W01_Arc", "assets": ["SM_Weapon_01"]},
                            {"id": 18, "key": "W18_Yumi", "assets": ["SM_Weapon_18", "SM_Weapon_18_Ya"]}],
                "admission": "Source art only.", "files": files}
    (root / RT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n")
    sources = {"schema": "lane", "inputs": [{"file": SRC, "sha256": sha(b"leather scan"), "tier": "PUB-CC0"}]}
    (root / RT / "sources_manifest.json").write_text(json.dumps(sources, ensure_ascii=False, indent=1) + "\n")
    return manifest


def is_w18(path: str) -> bool:
    return "/W18_Yumi/" in path or "/Renders/SM_Weapon_18" in path


class RecordFixture(unittest.TestCase):
    """A throwaway runtime tree per test (tree()), and the record call. No tests here."""

    ASSETS = ["SM_Weapon_18", "SM_Weapon_18_Ya"]

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.before = tree(self.root)
        self.before_text = (self.root / RT / "manifest.json").read_text()

    def tearDown(self):
        self._tmp.cleanup()

    def run_record(self, **kw):
        return R.record(self.root, 18, "W18_Yumi", self.ASSETS, kw.pop("generators", GENS),
                        now="2026-10-25T17:00:00+00:00", **kw)

    def after(self):
        return json.loads((self.root / RT / "manifest.json").read_text())


class Record(RecordFixture):
    def test_every_unrelated_entry_is_kept_exactly_and_in_place(self):
        self.run_record()
        old = [e for e in self.before["files"] if not is_w18(e["file"])]
        new = [e for e in self.after()["files"] if not is_w18(e["file"])]
        self.assertEqual(new, old)                                   # stale ones stay stale: no refreshed hash
        self.assertEqual(new[1]["sha256"], "f" * 64)                 # W01's render: stale, and kept so
        text = (self.root / RT / "manifest.json").read_text()
        for e in old:                                                # and serialized byte for byte as before
            block = json.dumps(e, ensure_ascii=False, indent=1).replace("\n", "\n  ")
            self.assertIn(block, text)
            self.assertIn(block, self.before_text)

    def test_the_w18_scope_is_exactly_the_files_on_disk(self):
        self.run_record()
        w18 = {e["file"]: e for e in self.after()["files"] if is_w18(e["file"])}
        self.assertEqual(sorted(w18), sorted([
            f"{RT}/Renders/SM_Weapon_18_Profile.png", f"{RT}/Renders/SM_Weapon_18_Ya_Profile.png",
            f"{RT}/W18_Yumi/SM_Weapon_18.fbx", f"{RT}/W18_Yumi/SM_Weapon_18_Ya.fbx",
            f"{RT}/W18_Yumi/build_record.json"]))
        for path, e in w18.items():
            data = (self.root / path).read_bytes()
            self.assertEqual((e["bytes"], e["sha256"]), (len(data), sha(data)))
        self.assertNotIn(f"{RT}/W18_Yumi/removed_old_map.png", w18)  # gone from disk, gone from the record

    def test_the_rig_and_blender_backups_stay_out_of_the_runtime_record(self):
        self.run_record()
        paths = [e["file"] for e in self.after()["files"]]
        self.assertFalse([p for p in paths if "/Rig/" in p or p.endswith(".blend1")])

    def test_entries_stay_sorted_with_the_scope_in_its_place(self):
        self.run_record()
        paths = [e["file"] for e in self.after()["files"]]
        self.assertEqual(paths, sorted(paths))

    def test_the_documents_other_fields_are_unchanged(self):
        self.run_record()
        a = self.after()
        for k, v in self.before.items():
            if k not in ("files", "generator_scripts"):
                self.assertEqual(a[k], v, k)
        self.assertEqual(a["generator_scripts"], sorted(set(self.before["generator_scripts"]) | set(GENS)))

    def test_the_scoped_update_names_provenance_not_admission(self):
        self.run_record()
        (u,) = self.after()["scoped_updates"]
        self.assertEqual((u["weapon"], u["key"]), (18, "W18_Yumi"))
        self.assertIn("not geometric or visual admission", u["scope"].lower())
        self.assertEqual([g["path"] for g in u["generators"]], GENS)
        self.assertTrue(all(len(g["sha256"]) == 64 for g in u["generators"]))
        self.assertEqual(u["derived_from"], [{"path": SRC, "sha256": sha(b"leather scan")}])
        self.assertEqual(u["own_ledgers_kept_apart"], [f"{RT}/W18_Yumi/Rig"])

    def test_check_reports_then_recording_settles_it_and_a_rerun_adds_nothing(self):
        changed, _ = self.run_record(check=True)
        self.assertTrue(changed)
        self.assertEqual((self.root / RT / "manifest.json").read_text(), self.before_text)   # check writes nothing
        self.run_record()
        text = (self.root / RT / "manifest.json").read_text()
        changed, _ = self.run_record(check=True)
        self.assertFalse(changed)
        changed, _ = self.run_record()
        self.assertFalse(changed)
        self.assertEqual((self.root / RT / "manifest.json").read_text(), text)             # no second scoped entry

    def test_a_derived_input_not_listed_at_its_hash_fails(self):
        (self.root / SRC).write_bytes(b"a different leather scan")
        with self.assertRaises(R.RecordError):
            self.run_record()
        self.assertEqual((self.root / RT / "manifest.json").read_text(), self.before_text)

    def test_a_geometry_only_build_record_fails(self):
        rec = json.loads((self.root / RT / "W18_Yumi/build_record.json").read_text())
        del rec["textures"]
        (self.root / RT / "W18_Yumi/build_record.json").write_text(json.dumps(rec))
        with self.assertRaises(R.RecordError):
            self.run_record()

    def test_preflight_finds_missing_and_changed_inputs(self):
        table = {SRC: (sha(b"leather scan"), "PUB-CC0", "Leather014", "ledger", "CC0-1.0")}
        self.assertEqual(R.preflight(self.root, "W18_Yumi", table), [])
        (self.root / SRC).write_bytes(b"changed")
        self.assertTrue(any("differs" in p for p in R.preflight(self.root, "W18_Yumi", table)))
        (self.root / SRC).unlink()
        self.assertTrue(any("missing" in p for p in R.preflight(self.root, "W18_Yumi", table)))

    def test_a_shorter_asset_name_never_captures_another_weapons_renders(self):
        self.assertFalse(R.in_scope(f"{RT}/Renders/SM_Weapon_18_Profile.png", "W01_Arc", ["SM_Weapon_1"], []))
        self.assertTrue(R.in_scope(f"{RT}/Renders/SM_Weapon_18_Ya_Profile.png", "W18_Yumi", ["SM_Weapon_18"], []))


class Provenance(RecordFixture):
    """Root's adversarial probes of a5a966c (art-a5a966c-host-review/adversarial-probes.json): a missing
    input still recorded, and a changed input or generator still "matched". Provenance is now validated
    first, in both modes, and a check matches only the latest scoped record's exact hashes."""

    def text(self):
        return (self.root / RT / "manifest.json").read_text()

    def unrelated_kept(self):
        old = [e for e in self.before["files"] if not is_w18(e["file"])]
        self.assertEqual([e for e in self.after()["files"] if not is_w18(e["file"])], old)

    def relist(self, data: bytes):
        path = self.root / RT / "sources_manifest.json"
        src = json.loads(path.read_text())
        src["inputs"][0]["sha256"] = sha(data)
        path.write_text(json.dumps(src, ensure_ascii=False, indent=1) + "\n")

    def test_a_missing_input_fails_before_any_record_and_writes_nothing(self):
        (self.root / SRC).unlink()
        for check in (False, True):
            with self.assertRaises(R.RecordError) as ctx:
                self.run_record(check=check)
            self.assertIn(f"{SRC}: missing", str(ctx.exception))
        self.assertEqual(self.text(), self.before_text)

    def test_a_changed_input_after_recording_never_matches(self):
        self.run_record()
        recorded = self.text()
        (self.root / SRC).write_bytes(b"leather scan, changed")
        for check in (True, False):
            with self.assertRaises(R.RecordError) as ctx:
                self.run_record(check=check)
            self.assertIn("differs from its sources_manifest.json hash", str(ctx.exception))
        self.assertEqual(self.text(), recorded)

    def test_a_relisted_input_is_new_provenance_not_a_match(self):
        self.run_record()
        newer = b"a newer leather scan"
        (self.root / SRC).write_bytes(newer)
        self.relist(newer)
        changed, _ = self.run_record(check=True)
        self.assertTrue(changed)
        self.run_record()
        ups = self.after()["scoped_updates"]
        self.assertEqual(len(ups), 2)
        self.assertEqual(ups[-1]["derived_from"], [{"path": SRC, "sha256": sha(newer)}])
        self.unrelated_kept()
        self.assertFalse(self.run_record(check=True)[0])

    def test_a_changed_generator_after_recording_is_reported_then_recorded(self):
        self.run_record()
        first = self.after()
        put(self.root, GENS[0], b"# the builder, changed")
        changed, _ = self.run_record(check=True)
        self.assertTrue(changed)
        self.run_record()
        a = self.after()
        self.assertEqual(len(a["scoped_updates"]), 2)
        self.assertEqual(a["scoped_updates"][-1]["generators"][0],
                         {"path": GENS[0], "sha256": sha(b"# the builder, changed")})
        self.assertEqual(a["files"], first["files"])                 # the outputs did not change
        self.unrelated_kept()
        self.assertFalse(self.run_record(check=True)[0])

    def test_a_missing_generator_fails_in_both_modes(self):
        (self.root / GENS[2]).unlink()
        for check in (True, False):
            with self.assertRaises(R.RecordError) as ctx:
                self.run_record(check=check)
            self.assertIn(f"generator {GENS[2]}: missing", str(ctx.exception))
        self.assertEqual(self.text(), self.before_text)

    def test_absent_provenance_never_matches(self):
        self.run_record()
        doc = self.after()
        del doc["scoped_updates"]                                    # files and generators all current
        (self.root / RT / "manifest.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
        self.assertTrue(self.run_record(check=True)[0])

    def test_another_weapons_provenance_is_not_w18s(self):
        self.run_record()
        doc = self.after()
        doc["scoped_updates"][0]["weapon"] = 1
        (self.root / RT / "manifest.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
        self.assertTrue(self.run_record(check=True)[0])


if __name__ == "__main__":
    unittest.main()
