"""Acquisition must not erase later attribution history or claim a newer art build."""

from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts/art"))
import fetch_cat_base_v6_sources as F  # noqa: E402


class DerivativeHistoryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ledger = self.root / "ledger.json"
        self.current = json.loads(F.LEDGER_DOC.read_text())
        self.scan = next(r for r in self.current["records"] if r["asset_id"] == f"sketchfab-{F.CT_UID}")

    def baseline(self):
        rec = deepcopy(self.scan)
        rec["changes"] = F.SCAN_USE[F.CT_UID]["changes"]
        return rec

    def save_previous(self, record):
        self.ledger.write_text(json.dumps({"records": [record]}))

    def test_fresh_acquisition_does_not_claim_round_nine(self):
        rec = self.baseline()
        F.preserve_scan_derivative_changes({F.CT_UID: rec}, self.ledger)
        self.assertNotIn("Round 9", rec["changes"])
        self.assertEqual(rec["changes"], F.SCAN_USE[F.CT_UID]["changes"])

    def test_retains_both_recovered_derivative_histories(self):
        for uid in (F.CT_UID, "3ffbfcabc4c34b58b03d43fd4f445b54"):
            old = next(r for r in self.current["records"] if r["asset_id"] == f"sketchfab-{uid}")
            rec = deepcopy(old)
            rec["changes"] = F.SCAN_USE[uid]["changes"]
            self.save_previous(old)
            F.preserve_scan_derivative_changes({uid: rec}, self.ledger)
            self.assertEqual(rec["changes"], old["changes"])
            self.assertIn("Round 9", rec["changes"])
            self.assertIn("generator source only", rec["changes"])

    def test_new_source_statement_can_extend_old_history(self):
        old = self.baseline()
        rec = deepcopy(old)
        rec["changes"] += " Later explicitly reviewed derivative change."
        self.save_previous(old)
        F.preserve_scan_derivative_changes({F.CT_UID: rec}, self.ledger)
        self.assertTrue(rec["changes"].endswith("Later explicitly reviewed derivative change."))

    def test_changed_scan_bytes_refuse_inherited_attribution(self):
        rec = self.baseline()
        rec["files"][0]["sha256"] = "0" * 64
        self.save_previous(self.scan)
        with self.assertRaisesRegex(SystemExit, "source identity changed"):
            F.preserve_scan_derivative_changes({F.CT_UID: rec}, self.ledger)

    def test_divergent_history_requires_reconciliation(self):
        rec = self.baseline()
        rec["changes"] = "A different account of the derivative."
        self.save_previous(self.scan)
        with self.assertRaisesRegex(SystemExit, "conflicting derivative histories"):
            F.preserve_scan_derivative_changes({F.CT_UID: rec}, self.ledger)

    def test_manifest_writes_preserve_history_in_central_and_draft_records(self):
        raw = json.loads(F.MANIFEST.read_text())
        scan = next(s for s in raw["scans"] if s["asset_id"] == self.scan["asset_id"])
        private = {"scans": {F.CT_UID: scan}, "photos": {}, "mirror": self.current["mirror_license"]}
        self.save_previous(self.scan)
        draft = self.root / "draft.json"
        with patch.multiple(F, ROOT=self.root, LEDGER_DOC=self.ledger,
                            MANIFEST=draft, RESTRICTED_DOC=self.root / "restricted.json"):
            F.write_manifest(private)
            F.write_manifest(private)  # repeated acquisition must be idempotent
        central = json.loads(self.ledger.read_text())["records"][0]
        draft_scan = json.loads(draft.read_text())["scans"][0]
        self.assertEqual(central["changes"], self.scan["changes"])
        self.assertEqual(draft_scan["changes"], self.scan["changes"])


if __name__ == "__main__":
    unittest.main()
