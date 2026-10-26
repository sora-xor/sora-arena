"""The chapter-three temporary loadout and pickup remain authored and reachable."""
import copy
import json
from pathlib import Path
import unittest

from build_campaign_data import BuildError, equipment_recovery, trigger_row
from validate_campaign import director_event_error

ROOT = Path(__file__).resolve().parents[2]


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.chapter = json.loads((ROOT / 'Content/Data/campaign/chapter_03.json').read_text())
        self.beats = copy.deepcopy(self.chapter['beats'])
        self.recovery = self.beats[4]

    def test_restriction_and_release(self):
        equipment_recovery(self.beats)
        self.assertTrue(all(b['task']['equipment_weapons'] == [4] for b in self.beats[:5]))
        self.assertTrue(all(b['task']['equipment_weapons'] == [0,4,18] for b in self.beats[5:8]))
        self.assertTrue(all(b['task']['equipment_weapons'] == [0,4,7,18] for b in self.beats[8:13]))
        self.assertTrue(all(b['task']['equipment_weapons'] == [0,4,7,18,19] for b in self.beats[13:]))
        self.assertEqual(self.recovery['task']['recovery'], {
            'interact': 'act_b05_dry_well_rope', 'item': 'sword_bundle', 'depth_cm': 700,
            'string_ms': 3000, 'weapons': [0, 4, 18], 'quiver': 12})
        self.assertIsNotNone(self.chapter['space']['beats'][4]['recovery'])
        self.assertTrue(all(row['recovery'] is None for i, row in enumerate(self.chapter['space']['beats']) if i != 4))

    def test_recovery_contract_fails_closed(self):
        for key,value in [('id','wrong_supply'),('slots',{'side':[4],'polearm':[1],'firearm':[7]}),
                          ('slots',{'side':[4],'polearm':[19.0],'firearm':[7]}),
                          ('refill',['shells'])]:
            beats=copy.deepcopy(self.beats)
            beats[13]['ext']['supply_point'][key]=value
            with self.subTest(supply=key),self.assertRaises(BuildError):equipment_recovery(beats)
        beats=copy.deepcopy(self.beats);beats[8]['unlocks']['weapons']=[1]
        with self.assertRaises(BuildError):equipment_recovery(beats)
        for path, value in [('descend_cm', 0), ('descend_cm', 699), ('descend_cm', True),
                            ('string_bow_s', 0), ('string_bow_s', 2.99), ('pickup', 'tools'),
                            ('restores', {'equipped': [0, 18], 'quiver': 12}),
                            ('restores', {'equipped': [False, 4, 18], 'quiver': 12}),
                            ('restores', {'equipped': [0.0, 4, 18], 'quiver': 12}),
                            ('restores', {'equipped': [0, 4, 18], 'quiver': 13})]:
            with self.subTest(path=path, value=value):
                beats = copy.deepcopy(self.beats)
                beats[4]['ext']['pre_step'][path] = value
                with self.assertRaises(BuildError):
                    equipment_recovery(beats)
        for bad in ([4.0], [True], [0, 4], []):
            beats = copy.deepcopy(self.beats)
            beats[0]['ext']['loadout']['equipped'] = bad
            with self.assertRaises(BuildError):
                equipment_recovery(beats)
        for missing in ('loadout', 'pre_step'):
            beats = copy.deepcopy(self.beats)
            del beats[0 if missing == 'loadout' else 4]['ext'][missing]
            with self.assertRaises(BuildError):
                equipment_recovery(beats)

    def test_both_lines_are_real_events_and_delay_is_preserved(self):
        rows = [r for r in self.chapter['triggers'] if 'ch03.b05.nyaakoto.002' in r['lines'] or 'ch03.b05.kohagi.003' in r['lines']]
        self.assertEqual([r['on'] for r in rows], ['item_picked:sword_bundle', 'item_picked:sword_bundle+4s'])
        for row in rows:
            self.assertIsNone(director_event_error(row, self.recovery, 0, self.chapter))
            missing = copy.deepcopy(self.recovery)
            missing['task']['recovery'] = None
            self.assertIsNotNone(director_event_error(row, missing, 0, self.chapter))
        for bad in (-1, 0, True, '4', 121):
            with self.subTest(delay=bad), self.assertRaises(BuildError):
                trigger_row('ch03.b05', 'item_picked:sword_bundle', 'radio', ['ch03.b05.kohagi.003'],
                            'dialogue', 'test', ext={'delay_s': bad})


if __name__ == '__main__':
    unittest.main()
