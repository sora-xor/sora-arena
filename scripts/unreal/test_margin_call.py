import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from build_campaign_data import BuildError, fail
from campaign_bridge import place_bridge

ROOT = Path(__file__).resolve().parents[2]


class MarginTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT/'Content/Data/campaign/chapter_07.json').read_text())
        self.record = self.data['space']['beats'][12]
        self.zone = self.data['space']['zones'][self.record['zone']]

    def test_authored_contract_and_reproducible_fifteen_bodies(self):
        self.assertEqual(self.record['bridge']['margin'], dict(consoles=15, hits_to_destroy=2, max_destroyed=6,
            targets=3, every_ms=7000, warning_ms=1500, radius_cm=250, damage=60, linger_ms=6000))
        self.assertEqual(len(self.zone['cover']), 15)
        self.assertEqual(len({tuple(c[:2]) for c in self.zone['cover']}), 15)
        self.assertTrue(all(c[2:] == [80, 300, 110] for c in self.zone['cover']))
        original = copy.deepcopy(self.data)
        place_bridge(self.data['beats'], self.data['space']['beats'], self.data['space']['zones'], fail)
        self.assertEqual(original, self.data)

    def test_entry_exit_centre_slide_and_helm_lanes_remain_clear(self):
        center = self.record['bridge']['center']
        # The existing centre walk has 34 cm capsule radius plus clearance;
        # both outer sliding lanes retain their original 35/55 cm bodies.
        for x, y, sx, sy, _ in self.zone['cover']:
            self.assertGreater(abs(y-center[1])-sy/2, 100)
            for lane in (center[0]-1600, center[0]+1600):
                self.assertGreater(abs(x-lane)-sx/2, 65)
            for point in [self.record['entry'][:2], self.record['exit']['center'],
                          self.data['space']['beats'][13]['helm']['wheel'],
                          self.data['space']['beats'][13]['helm']['beacon']]:
                self.assertTrue(abs(x-point[0]) > sx/2+100 or abs(y-point[1]) > sy/2+100)
        # All ten loose bodies start outside console collision, including the
        # inner lane that can legitimately hit a console after its warning.
        for n in range(10):
            x, y = center[0]-1600+(n//2)*800, center[1]+(600 if n%2 else -600)
            hx, hy = (35, 35) if n < 6 else (55, 50)
            for cx, cy, sx, sy, _ in self.zone['cover']:
                self.assertTrue(abs(x-cx) > hx+sx/2 or abs(y-cy) > hy+sy/2)

    def test_existing_linger_bark_and_boss_clock_bindings(self):
        rows = [t for t in self.data['triggers'] if t['beat'] == 'ch07.b13' and t['on'] == 'idle_in_cover_s:6']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['lines'], ['ch07.b13.collatera.009'])
        bosses = json.loads((ROOT/'Content/Data/bosses.json').read_text())
        boss = next(b for b in bosses['bosses'] if b['id'] == 'boss_collatera')
        attack = next(a for a in boss['attacks'] if a['id'] == 'margin_call')
        self.assertEqual((attack['windup_ms'], attack['damage'], attack['zone']['radius_cm'], attack['zone']['count']), (1500, 60, 250, 3))
        timer = next(t for t in boss['phases'][1]['concurrent'] if t['attack'] == 'margin_call')
        self.assertEqual(timer['every_ms'], 7000)
        self.assertFalse(any(t['attack'] == 'margin_call' for t in boss['phases'][2]['concurrent']))

    def test_malformed_authored_margin_values_are_rejected(self):
        for key, value in [('every_s', 6), ('windup_ms', 1499), ('targets', True), ('targets', 4),
                           ('damage', 0), ('cover_hits_to_destroy', 1), ('max_cover_destroyed', 7),
                           ('targeting', 'player only'), ('telegraph', 'none')]:
            data = copy.deepcopy(self.data)
            attacks = data['beats'][12]['ext']['pattern_tables']['collatera_p2_margin_call']['attacks']
            next(a for a in attacks if a['id'] == 'margin_call')[key] = value
            with self.subTest(key=key), self.assertRaises(BuildError):
                place_bridge(data['beats'], data['space']['beats'], data['space']['zones'], fail)

    def test_actual_production_rules(self):
        with tempfile.TemporaryDirectory() as temporary:
            binary = Path(temporary)/'margin'
            subprocess.run(['c++', '-std=c++17', '-Wall', '-Wextra', '-Werror', '-pedantic', '-UNDEBUG',
                            '-I', str(ROOT/'Source/SoraArena/Public'), str(ROOT/'scripts/unreal/margin_rules_driver.cpp'),
                            '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True)


if __name__ == '__main__':
    unittest.main()
