"""Authored final-scene conditions and reachable interaction staging."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


class EpilogueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.chapter = json.loads((ROOT / 'Content/Data/campaign/chapter_08.json').read_text())
        cls.beat = next(b for b in cls.chapter['beats'] if b['id'] == 'ch08.b17')
        cls.space = next(s for s in cls.chapter['space']['beats'] if s['beat'] == 'ch08.b17')

    def test_optional_heirloom_and_bounded_promotion(self):
        rows = {r['on']: r for r in self.chapter['triggers'] if r['beat'] == self.beat['id']}
        sword = rows['event:washio_sword_return']
        self.assertEqual(sword['requires_flag'], 'collectible:ch08.c03')
        self.assertEqual(sword['mode'], 'ambient')
        self.assertEqual(len(sword['lines']), 3)
        plaque = rows['event:plaque_rehang']
        self.assertIsNone(plaque['requires_flag'])
        self.assertEqual(plaque['mode'], 'blocking')
        self.assertEqual(len(plaque['lines']), 4)
        durations = {line['id']: line['duration_s'] for line in self.chapter['lines']}
        self.assertLessEqual(sum(durations[line] for line in plaque['lines']), self.beat['ext']['blocking_max_s'])
        self.assertEqual(self.beat['task']['closing_event'], 'event:plaque_rehang_done')
        self.assertFalse(self.beat['task']['skippable'])

    def test_board_is_beside_gate_and_interactions_are_distinct(self):
        zone = self.chapter['space']['zones'][self.space['zone']]
        gate = next(p['at'] for p in zone['props'] if p['mesh'] == 'torii')
        self.assertEqual(self.space['closing'], [gate[0] - 300, gate[1] - 235])
        self.assertEqual(self.space['anchor'], [gate[0] - 100, gate[1] + 500])
        self.assertGreater(sum((a-b)**2 for a, b in zip(self.space['anchor'], self.space['closing'])), (2*260)**2)
        volume = self.space['volumes'][0]
        self.assertEqual(volume['event'], 'volume_enter:vol_torii')
        for point in (self.space['anchor'], self.space['closing']):
            self.assertTrue(all(abs(p-c) <= s/2 for p, c, s in zip(point, volume['center'], volume['size'])))
            self.assertTrue(zone['rect'][0] + 100 < point[0] < zone['rect'][2] - 100)
            self.assertTrue(zone['rect'][1] + 100 < point[1] < zone['rect'][3] - 100)
        ending = next(s for s in self.chapter['space']['beats'] if s['beat'] == 'ch08.b18')
        self.assertEqual(ending['anchor'], self.space['anchor'])
        # The cinematic reuses the board's staging, not the interaction task.
        self.assertIsNone(ending['closing'])
        self.assertFalse(next(b for b in self.chapter['beats'] if b['id'] == 'ch08.b18')['task']['anchor_after_lines'])
        # This scene keeps its authored checkpoint policy; final completion
        # is persisted by the existing campaign-complete checkpoint.
        self.assertFalse(self.beat['checkpoint'])


if __name__ == '__main__':
    unittest.main()
