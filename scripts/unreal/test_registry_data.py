"""Narrative registry contracts, including returns and malformed authored data."""
import copy
import json
from pathlib import Path
import unittest

from campaign_registry import validate_registry
from build_campaign_data import BuildError, normalize_beat

ROOT = Path(__file__).resolve().parents[2]
ENTRY = {"item_ja": "鏃", "item_en": "Arrowheads", "qty": 24, "unit_ja": "本", "unit_en": "pieces"}


class RegistryTests(unittest.TestCase):
    def test_authored_entries_and_no_duplicate_deliveries(self):
        chapters = [json.loads((ROOT / f"Content/Data/campaign/chapter_{n:02}.json").read_text()) for n in range(1, 9)]
        self.assertEqual([sum(b['registry'] is not None for b in c['beats']) for c in chapters], [1, 2, 2, 4, 3, 1, 1, 2])
        by_id = {b['id']: b for c in chapters for b in c['beats']}
        for beat in by_id.values():
            validate_registry(beat['registry'], beat['type'], beat['params'], beat['ext'])
        self.assertEqual(by_id['ch05.b08']['registry'], ENTRY)
        self.assertEqual(by_id['ch07.b07']['registry'], {
            'item_ja': '押収品の返還', 'item_en': 'Seized goods returned', 'qty': 430,
            'unit_ja': '駄', 'unit_en': 'horse-loads'})
        self.assertEqual(by_id['ch07.b07']['ext']['registry_mode'], 'record_only')
        self.assertIsNone(by_id['ch05.b12']['registry'])  # inspection adds no goods
        self.assertIsNone(by_id['ch05.b17']['registry'])  # delivering the same goods
        self.assertIsNone(by_id['ch08.b16']['registry'])  # posting the same registry

    def test_strict_fields_counts_modes_and_task_kinds(self):
        for qty in (0, -1, True, 1.5, '24', 2**31):
            with self.subTest(qty=qty), self.assertRaises(ValueError):
                validate_registry({**ENTRY, 'qty': qty}, 'production_task', {}, {})
        for field in ('item_ja', 'item_en', 'unit_ja', 'unit_en'):
            for value in ('', '  ', 12, None):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    validate_registry({**ENTRY, field: value}, 'production_task', {}, {})
        for entry in ({k: v for k, v in ENTRY.items() if k != 'unit_en'}, {**ENTRY, 'balance': 24}, []):
            with self.subTest(entry=entry), self.assertRaises(ValueError):
                validate_registry(entry, 'production_task', {}, {})
        for mode in (None, 'production', 'balance', 1):
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                validate_registry(ENTRY, 'production_task', {}, {'registry_mode': mode})
        for kind, params in (('combat_wave', {}), ('dialogue', {}), ('cinematic', {}), ('horseback_ride', {'mode': 'travel'})):
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                validate_registry(ENTRY, kind, params, {})
        with self.assertRaises(ValueError):
            validate_registry(None, 'production_task', {}, {'registry_mode': 'record_only'})
        validate_registry(ENTRY, 'production_task', {}, {})
        validate_registry(ENTRY, 'production_task', {}, {'registry_mode': 'record_only'})
        validate_registry(ENTRY, 'horseback_ride', {'mode': 'cargo'}, {})
        validate_registry(None, 'cinematic', {}, {})

    def test_importer_rejects_registry_that_would_be_dropped(self):
        opening = {'id': 'ch01.b01', 'type': 'cinematic', 'place': 'pl_estate_day',
                   'title_ja': '序', 'title_en': 'Opening', 'target_s': 60,
                   'sequence': 'LS', 'duration_s': 60, 'skippable': True, 'subtitles': []}
        for patch in ({'registry': ENTRY}, {'x_registry_mode': 'record_only'}, {'x_registry_mode': 'balance'}):
            with self.subTest(patch=patch), self.assertRaises(BuildError):
                normalize_beat({**copy.deepcopy(opening), **patch}, None, 'ch01', 1, [], [])


if __name__ == '__main__':
    unittest.main()
