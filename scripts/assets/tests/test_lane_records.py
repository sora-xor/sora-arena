"""Unit tests for the record rules in the audio and CatBaseV6 fetchers (no network, no files written).

Run: python3 -m unittest discover -s scripts/assets/tests -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts/audio"))
sys.path.insert(0, str(REPO / "scripts/art"))

import fetch_cat_base_v6_sources as cat  # noqa: E402
import fetch_cc0_audio as audio  # noqa: E402

OGA_AUTHOR = ('<div class="field field-name-author-submitter field-type-ds field-label-above"><div class="field-label">'
              'Author:&nbsp;</div><div class="field-items"><div class="field-item even"><span class=\'username\'>'
              '<a href=\'http://www.freesound.org/people/transitking/\'>transitking</a></span><br/>(Submitted by '
              '<strong><a href="/users/qubodup">qubodup</a></strong>)</div></div></div>')


class AudioRecords(unittest.TestCase):
    def test_oga_author_has_no_markup_debris(self):
        self.assertEqual(audio.parse_oga(OGA_AUTHOR)["author"], "transitking")

    def test_freesound_is_read_only(self):
        with self.assertRaises(RuntimeError):
            audio.check_host("https://freesound.org/people/transitking/sounds/11505/")
        audio.check_host("https://freesound.org/people/transitking/sounds/11505/", frozenset(audio.LICENSE_PAGE_HOSTS))

    def test_reference_fields_are_ref(self):
        fields = audio.reference_fields("wikimedia/File:x.oga", "https://example.test/x", "reference-only: test")
        self.assertEqual(fields["tier"], "REF")
        self.assertFalse(fields["commercial_use"])
        self.assertTrue(fields["listing_url"] and fields["entitlement_owner"])

    def test_upstream_items_are_known(self):
        for asset_id, (_site, url, authors, snap) in audio.UPSTREAM.items():
            self.assertTrue(url.startswith("https://freesound.org/"), asset_id)
            self.assertTrue(authors and snap)


class CatRecords(unittest.TestCase):
    def test_commons_allowlist_matches_the_plan(self):
        self.assertEqual(cat.commons_license("CC0"), ("CC0-1.0", "PUB-CC0"))
        self.assertEqual(cat.commons_license("CC BY 4.0"), ("CC-BY-4.0", "PUB-BY"))
        self.assertEqual(cat.commons_license("CC BY 3.0"), ("CC-BY-3.0", "PUB-BY"))
        self.assertEqual(cat.commons_license("CC BY 2.0"), ("CC-BY-2.0", "REF"))
        self.assertEqual(cat.commons_license("CC BY 4.0", reference_only=True), ("CC-BY-4.0", "REF"))
        for bad in ("CC BY-SA 4.0", "Public domain", "GFDL"):
            with self.assertRaises(SystemExit):
                cat.commons_license(bad)
        self.assertFalse("cc by 2.0".startswith(cat.ALLOWED_COMMONS_PREFIX))
        self.assertTrue("cc by 2.0".startswith(cat.REF_ONLY_COMMONS_PREFIX))

    def test_user_agent_carries_no_contact_address(self):
        self.assertNotIn("@", cat.UA)
        self.assertNotIn("@", audio.UA)


if __name__ == "__main__":
    unittest.main()
