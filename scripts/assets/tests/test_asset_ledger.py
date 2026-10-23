"""Unit tests for the asset ledger validator, restricted checker and notices generator.

Run: python3 -m unittest discover -s scripts/assets/tests -v
Every test works in a throwaway git repository under a temp directory; the real
repository is never staged, modified or read for its index.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import asset_ledger as L  # noqa: E402
import check_restricted  # noqa: E402
import generate_asset_notices  # noqa: E402
import validate_asset_ledger  # noqa: E402

SNAPSHOT = {"url": "https://example.test/license", "path": "Local/ThirdPartyRaw/_licenses/x.html",
            "sha256": "a" * 64, "retrieved_at_utc": "2026-09-25T00:00:00+00:00", "via": "direct"}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def record(asset_id: str, files, tier="PUB-CC0", license_id="CC0-1.0", storage="repo-lfs", **extra) -> dict:
    base = {
        "asset_id": asset_id, "name": asset_id, "tier": tier, "license": license_id,
        "license_url": "https://example.test/license", "origin_url": f"https://example.test/a/{asset_id}",
        "mirror_url": None, "commercial_use": True, "redistribution": "unrestricted", "derivatives": True,
        "platform_restriction": None, "ai_terms": "none", "agent_handling": "allowed", "attribution_text": None,
        "changes": None, "license_snapshot": SNAPSHOT, "access": "api", "acquired_at_utc": "2026-09-25T00:00:00+00:00",
        "acquired_by": "agent", "storage": storage, "used_by": [], "fallback": None, "files": files,
    }
    base.update(extra)
    return base


class RepoCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="ledger-test-"))
        subprocess.run(["git", "init", "-q", str(self.tmp)], check=True)
        (self.tmp / ".gitignore").write_text("/Local/\n/Content/ThirdPartyRestricted/\n/Content/Fab/\n")
        self.add(".gitignore")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)  # temp directory created by this test only

    def write(self, rel: str, data: bytes) -> Path:
        path = self.tmp / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def add(self, *rels: str, force: bool = False) -> None:
        subprocess.run(["git", "-C", str(self.tmp), "add"] + (["-f"] if force else []) + list(rels), check=True)

    def ledger(self, name: str, records, restricted: bool = False, **extra) -> Path:
        doc = {"schema_version": 2, "kind": "restricted-manifest" if restricted else "asset-ledger",
               "source": name, "records": records}
        doc.update(extra)
        folder = "scripts/assets/restricted" if restricted else "scripts/assets/manifests"
        return self.write(f"{folder}/{name}.json", json.dumps(doc, indent=1).encode())

    def validate(self, **kwargs):
        return validate_asset_ledger.validate(self.tmp, **kwargs)

    def restricted(self, **kwargs):
        out = io.StringIO()
        with redirect_stdout(out):
            code = check_restricted.check(self.tmp, **kwargs)
        return code, out.getvalue()


class RecordRules(unittest.TestCase):
    def test_good_cc0_record_passes(self):
        self.assertEqual(L.check_record(record("a", [{"path": "Content/SourceArt/a.png", "sha256": "b" * 64}])), [])

    def test_noncommercial_and_sharealike_rejected(self):
        for bad in ("CC-BY-NC-4.0", "CC-BY-SA-4.0", "CC-BY-ND-4.0", "GPL-3.0"):
            errors = L.check_record(record("a", [], tier="PUB-BY", license_id=bad, attribution_text="x", changes="y"))
            self.assertTrue(any("rejected" in e for e in errors), (bad, errors))

    def test_pub_by_needs_attribution_and_changes(self):
        errors = L.check_record(record("a", [], tier="PUB-BY", license_id="CC-BY-4.0"))
        self.assertTrue(any("attribution_text" in e for e in errors))
        self.assertTrue(any("'changes'" in e for e in errors))

    def test_rst_needs_fallback_and_private_paths(self):
        errors = L.check_record(record("a", [{"path": "Content/SourceArt/a.wav", "sha256": "c" * 64}],
                                       tier="RST", license_id="Sonniss GDC", storage="local-private"))
        self.assertTrue(any("fallback" in e for e in errors))
        self.assertTrue(any("must live under Local/" in e for e in errors))

    def test_font_license_only_for_fonts(self):
        font = record("f", [], tier="PUB-BY", license_id="OFL-1.1", attribution_text="x", changes="none", kind="font")
        self.assertEqual(L.check_record(font), [])
        not_font = record("f", [], tier="PUB-BY", license_id="OFL-1.1", attribution_text="x", changes="none")
        self.assertTrue(L.check_record(not_font))

    def test_missing_schema_keys_reported(self):
        errors = L.check_record({"asset_id": "x", "tier": "PUB-CC0", "license": "CC0-1.0"})
        self.assertTrue(any("license_snapshot" in e for e in errors))
        self.assertTrue(any("'files'" in e for e in errors))

    def test_local_raw_storage_must_stay_in_local(self):
        errors = L.check_record(record("a", [{"path": "Content/SourceArt/a.png", "sha256": "d" * 64}], storage="local-raw"))
        self.assertTrue(any("outside Local/" in e for e in errors))


class ValidatorRepo(RepoCase):
    def good_repo(self):
        data = b"\x89PNG fake texture"
        self.write("Content/SourceArt/Env/Foo/tex.png", data)
        self.ledger("foo", [record("tex", [{"path": "Content/SourceArt/Env/Foo/tex.png", "sha256": sha(data), "bytes": len(data)}])])
        self.add("Content/SourceArt/Env/Foo/tex.png", "scripts")
        return data

    def test_clean_repo_passes(self):
        self.good_repo()
        report = self.validate()
        self.assertEqual(report.errors, [])
        self.assertEqual(report.stats.get("schema2_covered"), 1)

    def test_planted_restricted_file_in_tracked_path_fails(self):
        self.good_repo()
        self.write("Content/ThirdPartyRestricted/Fab/Sample.uasset", b"restricted")
        self.add("Content/ThirdPartyRestricted/Fab/Sample.uasset", force=True)
        report = self.validate()
        self.assertTrue(any("never-commit root" in e for e in report.errors), report.errors)
        code, out = self.restricted()
        self.assertEqual(code, 1)
        self.assertIn("tracked restricted/local path", out)

    def test_renamed_copy_of_restricted_content_fails_by_hash(self):
        self.good_repo()
        secret = b"RIFF restricted sonniss audio"
        self.write("Local/ThirdPartyRaw/sonniss/hit.wav", secret)
        self.ledger("sonniss", [record("hit", [{"path": "Local/ThirdPartyRaw/sonniss/hit.wav", "sha256": sha(secret)}],
                                       tier="RST", license_id="Sonniss GDC Game Audio Bundle", storage="local-private",
                                       fallback="own-hit", listing_url="https://example.test/sonniss",
                                       entitlement_owner="user", redistribution="no-standalone")], restricted=True)
        self.write("Content/SourceArt/Audio/innocent.wav", secret)
        self.write("Content/SourceArt/Audio/README.md", b"innocent.wav: our foley")
        self.add("Content/SourceArt/Audio", "scripts")
        report = self.validate()
        self.assertTrue(any("content of restricted item" in e for e in report.errors), report.errors)
        code, out = self.restricted()
        self.assertEqual(code, 1)
        self.assertIn("has the content of restricted item", out)

    def test_unrecorded_binary_fails_and_legacy_record_is_strict_only(self):
        self.good_repo()
        self.write("Content/SourceArt/Env/Bar/render.png", b"png")
        self.add("Content/SourceArt/Env/Bar/render.png")
        self.assertTrue(any("no ledger record" in e for e in self.validate().errors))
        self.write("Content/SourceArt/Env/Bar/README.md", b"`render.png` is our Blender render.")
        self.add("Content/SourceArt/Env/Bar/README.md")
        self.assertEqual(self.validate().errors, [])
        self.assertTrue(any("strict mode" in e for e in self.validate(strict=True).errors))

    def test_hash_mismatch_fails(self):
        self.good_repo()
        self.write("Content/SourceArt/Env/Foo/tex.png", b"\x89PNG edited!!!!!!")
        self.assertTrue(any("SHA-256 does not match" in e for e in self.validate().errors))

    def test_missing_local_raw_only_fails_when_required(self):
        self.good_repo()
        self.ledger("raw", [record("raw", [{"path": "Local/ThirdPartyRaw/cc0/x/a.jpg", "sha256": "e" * 64}], storage="local-raw")])
        self.add("scripts")
        self.assertEqual(self.validate().errors, [])
        self.assertTrue(self.validate(require_local=True).errors)

    def test_fab_folder_and_archives_fail(self):
        self.good_repo()
        self.write("Content/Fab/Megaplants/Thing.uasset", b"x")
        self.write("Content/SourceArt/pack.zip", b"PK")
        self.add("Content/SourceArt/pack.zip")
        errors = self.validate().errors
        self.assertTrue(any("Fab content found" in e for e in errors), errors)
        self.assertTrue(any("archive or video" in e for e in errors), errors)

    def test_forbidden_agent_handling_referenced_by_script_fails(self):
        self.good_repo()
        self.ledger("fab", [record("cypress", [{"path": "Content/ThirdPartyRestricted/Fab/Cypress/SM_Cypress.uasset", "sha256": "f" * 64}],
                                   tier="RST", license_id="Fab Standard License", storage="ue-restricted", fallback="own-hinoki",
                                   agent_handling="forbidden", used_by=["/Game/ThirdPartyRestricted/Fab/Cypress/SM_Cypress"],
                                   listing_url="https://example.test/fab", entitlement_owner="user")], restricted=True)
        self.write("scripts/unreal/import_trees.py", b"load('/Game/ThirdPartyRestricted/Fab/Cypress/SM_Cypress')\n")
        self.add("scripts")
        self.assertTrue(any("agent_handling:forbidden" in e for e in self.validate().errors))

    def test_audio_lane_convention_is_validated(self):
        """Manifests that name the list "assets", files by "file" and evidence by license_evidence."""
        data = b"OggS audio"
        self.write("Local/ThirdPartyRaw/audio/kenney/a.ogg", data)
        rec = record("kenney/ui", [{"file": "Local/ThirdPartyRaw/audio/kenney/a.ogg", "sha256": sha(data), "bytes": len(data)}],
                     storage="local-private")
        del rec["license_snapshot"]
        rec["license_evidence"] = {"page_snapshot": {"path": "Local/ThirdPartyRaw/_licenses/k.html", "sha256": "1" * 64}}
        doc = {"schema_version": 2, "source": "Kenney", "assets": [rec]}
        self.write("scripts/assets/manifests/audio_kenney.json", json.dumps(doc).encode())
        self.add("scripts")
        report = self.validate()
        self.assertEqual(report.errors, [])
        self.assertEqual(report.stats.get("verified_files"), 1)
        self.write("Local/ThirdPartyRaw/audio/kenney/a.ogg", b"OggS changed")
        self.assertTrue(any("ledger says" in e or "SHA-256" in e for e in self.validate().errors))
        rec["license_evidence"] = {"page_license_field": "CC0"}
        self.write("scripts/assets/manifests/audio_kenney.json", json.dumps(doc).encode())
        self.assertTrue(any("license_snapshot" in e for e in self.validate().errors))

    def test_extension_must_keep_base_bytes_and_historical_hashes(self):
        data = b"\x89PNG palette"
        self.write("Content/SourceArt/PH/a.png", data)
        base = {"schema_version": 1, "assets": [{"asset_id": "a", "files": [{"file": "a.png", "sha256": sha(data)}]}]}
        base_bytes = json.dumps(base).encode()
        self.write("Content/SourceArt/PH/manifest.json", base_bytes)
        ext = {"schema_version": 2, "kind": "asset-ledger", "source": "polyhaven",
               "extends": [{"manifest": "Content/SourceArt/PH/manifest.json", "sha256": sha(base_bytes)}],
               "records": [record("a", [{"path": "Content/SourceArt/PH/a.png", "sha256": sha(data),
                                         "hash_source": "Content/SourceArt/PH/manifest.json"}])]}
        self.write("Content/SourceArt/PH/manifest.ledger.json", json.dumps(ext).encode())
        self.add("Content/SourceArt/PH")
        self.assertEqual(self.validate().errors, [])
        ext["records"][0]["files"][0]["sha256"] = "0" * 64
        self.write("Content/SourceArt/PH/manifest.ledger.json", json.dumps(ext).encode())
        self.assertTrue(any("historical hash" in e for e in self.validate().errors))
        self.write("Content/SourceArt/PH/manifest.json", base_bytes + b" ")
        self.assertTrue(any("changed (sha256" in e for e in self.validate().errors))


class LaneIntegration(RepoCase):
    def test_blender_backup_is_binary_and_never_committed(self):
        self.assertTrue(L.is_binary("Content/SourceArt/Cat/Cat.blend1"))
        self.assertTrue(L.is_blender_backup("a/b.blend12"))
        self.assertFalse(L.is_blender_backup("a/b.blend"))
        self.write("Content/SourceArt/Cat/Cat.blend1", b"BLENDER backup")
        self.write("Content/SourceArt/Cat/README.md", b"Cat.blend1 is a backup")
        self.add("Content")
        errors = validate_asset_ledger.validate(self.tmp).errors
        self.assertTrue(any("Blender backup" in e for e in errors), errors)

    def test_document_level_own_manifest_is_a_record(self):
        data = b"RIFF own wav"
        self.write("Content/SourceArt/Audio/Original/UI/click.wav", data)
        own = {"schema_version": 2, "tier": "OWN", "license": "Project-owned", "generator_scripts": ["scripts/audio/synth/build_sfx.py"],
               "generated_at_utc": "2026-09-25T00:00:00+00:00",
               "files": [{"file": "Content/SourceArt/Audio/Original/UI/click.wav", "bytes": len(data), "sha256": sha(data)}]}
        self.write("Content/SourceArt/Audio/Original/manifest.json", json.dumps(own).encode())
        # An art manifest with its own "schema_version 2" and no tier is not a ledger document.
        self.write("Content/SourceArt/Env/Props/manifest.json", json.dumps({"schema_version": 2, "assets": [{"name": "x"}]}).encode())
        self.add("Content")
        report = self.validate(strict=True)
        self.assertEqual(report.errors, [])
        self.assertEqual(report.stats.get("schema2_covered"), 1)
        text = generate_asset_notices.render(self.tmp)
        self.assertIn("`Content/SourceArt/Audio/Original/UI`: 1 files", text)
        self.write("Content/SourceArt/Audio/Original/UI/click.wav", b"RIFF edited wav")
        self.assertTrue(any("SHA-256" in e or "bytes" in e for e in self.validate().errors))

    def test_lane_draft_must_match_ledger(self):
        photo = b"jpeg reference"
        self.write("Local/ThirdPartyRaw/reference/cat.jpg", photo)
        draft = {"schema": "2-draft", "photos": [{"asset_id": "commons-1", "tier": "REF",
                                                   "file": "Local/ThirdPartyRaw/reference/cat.jpg", "sha256": sha(photo)}]}
        self.write("Content/SourceArt/Characters/Cat/sources_manifest.json", json.dumps(draft).encode())
        errors = self.validate().errors
        self.assertTrue(any("not recorded in the ledger" in e for e in errors), errors)
        ref = record("commons-1", [{"path": "Local/ThirdPartyRaw/reference/cat.jpg", "sha256": sha(photo)}],
                     tier="PUB-BY", license_id="CC-BY-4.0", storage="local-private", attribution_text="x", changes="none")
        self.ledger("cat", [ref])
        errors = self.validate().errors
        self.assertTrue(any("tier REF in the draft but PUB-BY" in e for e in errors), errors)
        ref.update(tier="REF", license="CC-BY-2.0", listing_url="https://example.test/p", entitlement_owner="none")
        self.write("scripts/assets/manifests/cat.json", b"{}")
        self.ledger("cat", [ref], restricted=True)
        self.assertEqual(self.validate().errors, [])

    def test_downloads_and_archives_are_hash_checked(self):
        data = b"fLaC direct download"
        self.write("Local/ThirdPartyRaw/audio/oga/w.flac", data)
        rec = record("oga/w", [], storage="local-private")
        rec["downloads"] = [{"file": "Local/ThirdPartyRaw/audio/oga/w.flac", "sha256": sha(data), "bytes": len(data)}]
        self.ledger("oga", [rec])
        self.assertEqual(self.validate().stats.get("verified_files"), 1)
        self.write("Local/ThirdPartyRaw/audio/oga/w.flac", b"fLaC DIRECT download")
        self.assertTrue(any("SHA-256 does not match" in e for e in self.validate().errors))


class RestrictedChecker(RepoCase):
    def manifest(self, **extra):
        rec = record("hooves", [{"path": "Local/ThirdPartyRaw/sonniss/hooves.wav", "sha256": sha(b"hooves")}],
                     tier="RST", license_id="Sonniss GDC Game Audio Bundle", storage="local-private", fallback="own-hooves",
                     listing_url="https://example.test/sonniss", entitlement_owner="user", user_step="U6",
                     redistribution="no-standalone", **extra)
        self.ledger("sonniss", [rec], restricted=True)

    def test_missing_file_prints_manual_step(self):
        self.manifest()
        code, out = self.restricted()
        self.assertEqual(code, 0)
        self.assertIn("MISSING", out)
        self.assertIn("manual step U6", out)
        self.assertEqual(self.restricted(require_present=True)[0], 1)

    def test_present_file_verified(self):
        self.manifest()
        self.write("Local/ThirdPartyRaw/sonniss/hooves.wav", b"hooves")
        code, out = self.restricted(require_present=True)
        self.assertEqual(code, 0, out)
        self.assertIn("OK", out)

    def test_wrong_hash_fails(self):
        self.manifest()
        self.write("Local/ThirdPartyRaw/sonniss/hooves.wav", b"other bytes")
        self.assertEqual(self.restricted()[0], 1)

    def test_embedded_content_rejected(self):
        self.manifest(data="UklGRi4uLg==")
        code, out = self.restricted()
        self.assertEqual(code, 1)
        self.assertIn("embeds file content", out)


class Notices(RepoCase):
    def test_own_generator_lists_and_source_objects_read_as_paths(self):
        self.ledger("project", [
            record("crafted", [], tier="OWN", license_id="project-owned",
                   generator=["scripts/art/craft.py", "scripts/art/mark.py"],
                   derived_from=[{"path": "Content/SourceArt/UI/mark.svg", "sha256": "b" * 64}, "wood_planks"]),
            record("legacy", [], tier="OWN", license_id="project-owned", generator="scripts/art/legacy.py"),
            record("fallback", [], tier="OWN", license_id="project-owned", origin_url="scripts/art/fallback.py")])
        self.add("scripts")
        text = generate_asset_notices.render(self.tmp)
        self.assertIn("generator `scripts/art/craft.py`, `scripts/art/mark.py`, derived from `Content/SourceArt/UI/mark.svg`, `wood_planks`", text)
        self.assertIn("generator `scripts/art/legacy.py`, derived from -", text)
        self.assertIn("generator `scripts/art/fallback.py`, derived from -", text)
        self.assertNotIn("['", text)
        self.assertNotIn("{'path'", text)


    def test_render_lists_credit_attribution_and_check(self):
        data = b"jpg"
        self.write("Content/SourceArt/Env/a.jpg", data)
        self.ledger("polyhaven", [record("hinoki_planks", [{"path": "Content/SourceArt/Env/a.jpg", "sha256": sha(data)}],
                                         authors={"Charlotte Baglioni": "All"})],
                    credit="Powered by Poly Haven - https://polyhaven.com")
        self.ledger("scans", [record("cat_ct", [], tier="PUB-BY", license_id="CC-BY-4.0",
                                     attribution_text='"Cat CT" by Brian Mather, https://example.test/cat',
                                     changes="Decimated and retopologised", name="Cat CT", authors=["Open.Ed"],
                                     license_url="https://creativecommons.org/licenses/by/4.0/",
                                     mirror_url="https://example.test/mirror/cat.glb",
                                     mirror_license={"dataset": "allenai/objaverse", "license": "ODC-By-1.0",
                                                     "license_url": "https://opendatacommons.org/licenses/by/1-0/"},
                                     derived_art=["Content/SourceArt/Characters/Cat"])],
                    credits=["Scans from the Objaverse 1.0 dataset, ODC-By 1.0"])
        self.ledger("ref", [record("taiko", [], tier="REF", license_id="CC0-1.0", storage="local-private",
                                   reason="uncleared composition", listing_url="https://example.test/t",
                                   entitlement_owner="none")], restricted=True)
        self.add("Content", "scripts")
        text = generate_asset_notices.render(self.tmp)
        self.assertIn("Powered by Poly Haven", text)
        self.assertIn("hinoki_planks", text)
        self.assertIn('"Cat CT" by Open.Ed, <https://example.test/a/cat_ct>, CC BY 4.0', text)
        self.assertIn('Credit: "Cat CT" by Brian Mather', text)
        self.assertIn("Changes: Decimated and retopologised", text)
        self.assertIn("Downloaded from: <https://example.test/mirror/cat.glb> (allenai/objaverse, ODC-By-1.0", text)
        self.assertIn("Used in: `Content/SourceArt/Characters/Cat`", text)
        self.assertIn("Scans from the Objaverse 1.0 dataset, ODC-By 1.0", text)
        self.assertIn("`taiko` (REF, CC0 1.0)", text)
        self.assertIn("uncleared composition", text)
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(generate_asset_notices.main(["--root", str(self.tmp), "--check"]), 1)
            self.assertEqual(generate_asset_notices.main(["--root", str(self.tmp)]), 0)
            self.assertEqual(generate_asset_notices.main(["--root", str(self.tmp), "--check"]), 0)


if __name__ == "__main__":
    unittest.main()
