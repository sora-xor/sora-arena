"""Persistent-reader content contract; UE tests exercise input, saves and Slate."""
from collections import Counter
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "Content/Data/campaign"


class CodexDataTests(unittest.TestCase):
    def test_all_saved_bits_have_full_bilingual_lore_and_unique_identity(self):
        index = json.loads((DATA / "campaign.json").read_text())
        categories = {row["id"]: row for row in index["collectible_categories"]}
        found, ids, counts = set(), set(), Counter()
        for chapter in range(8):
            rows = json.loads((DATA / f"chapter_{chapter + 1:02}.json").read_text())["collectibles"]
            self.assertEqual(len(rows), 6)
            for item in rows:
                self.assertIn(item["category"], categories)
                self.assertNotIn(item["id"], ids)
                ids.add(item["id"])
                self.assertIn(item["mask_bit"], range(6))
                bit = chapter * 6 + item["mask_bit"]
                self.assertNotIn(bit, found)
                found.add(bit)
                counts[item["category"]] += 1
                for language in ("ja", "en"):
                    self.assertIsInstance(item["codex"][language], str)
                    self.assertTrue(item["codex"][language].strip())
                # The normalized shape distinguishes absent titles from empty
                # titles and mismatched languages. The UE loader separately
                # rejects JSON values of another type, including coercible ones.
                ja, en = item["title_ja"], item["title_en"]
                if ja is None:
                    self.assertIsNone(en)
                else:
                    self.assertIsInstance(ja, str)
                    self.assertIsInstance(en, str)
                    self.assertTrue(ja.strip() and en.strip())
            self.assertEqual({row["mask_bit"] for row in rows}, set(range(6)))
        self.assertEqual(found, set(range(48)))
        self.assertEqual(counts, Counter({key: row["count"] for key, row in categories.items()}))
        self.assertNotIn("codex_toshiya", ids)

    def test_existing_authored_titles_are_not_rewritten_or_invented(self):
        first = json.loads((DATA / "chapter_01.json").read_text())["collectibles"]
        self.assertEqual(first[0]["title_ja"], "伝書の断簡 其の一")
        self.assertEqual(first[0]["title_en"], "Scroll fragment I")
        self.assertEqual(first[0]["codex"]["en"],
                         "Distance is not the length of the sword. It is how far the mind reaches. —Sekireisai")
        self.assertEqual(first[5]["title_en"], "League mark II")
        for chapter in range(2, 9):
            for item in json.loads((DATA / f"chapter_{chapter:02}.json").read_text())["collectibles"]:
                self.assertIsNone(item["title_ja"])
                self.assertIsNone(item["title_en"])
        model = (ROOT / "Source/SoraArena/Private/UI/SoraFrontEndCodex.cpp").read_text()
        self.assertIn("Item.Codex, Item.CodexEnglish", model)
        self.assertIn("Campaign->ToshiyaCodex(false), Campaign->ToshiyaCodex(true)", model)
        self.assertNotIn("GalleryPoiMask", model)
        for forbidden in ("SaveProgress(", "SaveCheckpoint(", "SaveGameToSlot(", "CollectAt(", "CompleteOptional("):
            self.assertNotIn(forbidden, model, "The reader must not manufacture rewards or mutate saves")

    def test_new_ui_labels_are_native_and_translated(self):
        import native_japanese_localization as loc
        entries = loc.parse_po(loc.TRANSLATIONS.read_text())
        codex = {key: entry for (namespace, key), entry in entries.items() if namespace == "SoraArena.Codex"}
        self.assertEqual(set(codex), {"Title", "OpenHint", "Context", "Untitled", "Toshiya", "Challenge",
                                    "Summary", "Empty", "ScrollUp", "ScrollDown"})
        self.assertFalse(loc.translation_problems({("SoraArena.Codex", key): entry for key, entry in codex.items()}))
        self.assertEqual(codex["Summary"].english,
                         "Collectibles {Count} / 48\nSelect a discovered record to read.")


if __name__ == "__main__":
    unittest.main()
