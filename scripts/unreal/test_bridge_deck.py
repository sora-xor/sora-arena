import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from campaign_bridge import place_bridge
from build_campaign_data import BuildError, fail

ROOT = Path(__file__).resolve().parents[2]


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT/'Content/Data/campaign/chapter_07.json').read_text())

    def rebuild(self, data):
        place_bridge(data['beats'], data['space']['beats'], data['space']['zones'], fail)

    def test_current_data_is_exactly_reproducible(self):
        data = copy.deepcopy(self.data)
        self.rebuild(data)
        self.assertEqual(data, self.data)
        bridge = data['space']['beats'][12]['bridge']
        self.assertEqual(bridge, dict(center=[79400, 0], list_deg=10, uphill_permille=850,
                                     downhill_permille=1100, every_ms=6000, warning_ms=700,
                                     damage=30, stagger_ms=600, chairs=6, pods=4, port=[0, -1]))

    def test_only_boss_bridge_owns_motion(self):
        for index, record in enumerate(self.data['space']['beats']):
            self.assertEqual('bridge' in record, index == 12)
        boss, helm = self.data['space']['beats'][12:14]
        self.assertEqual(boss['zone'], helm['zone'])
        self.assertEqual(helm['helm']['wheel'], [81600, -500])
        self.assertEqual(helm['exit'], dict(center=[81800, 0], size=[500, 3360]))

    def test_binds_geometry_to_current_zone_not_hardcoded_world_position(self):
        data = copy.deepcopy(self.data)
        zone = data['space']['zones'][data['space']['beats'][12]['zone']]
        zone['rect'] = [value+10000 if index % 2 == 0 else value for index, value in enumerate(zone['rect'])]
        self.rebuild(data)
        self.assertEqual(data['space']['beats'][12]['bridge']['center'], [89400, 0])

    def test_malformed_authored_mechanics_are_rejected(self):
        for group, key, value in [('arena', 'list_deg', True), ('arena', 'list_deg', 0),
                                  ('arena', 'uphill_speed_mult', .8), ('arena', 'downhill_speed_mult', float('nan')),
                                  ('slide', 'windup_ms', 699), ('slide', 'damage', 0), ('slide', 'every_s', 5),
                                  ('slide', 'knockdown_s', .5), ('slide', 'direction', 'starboard'),
                                  ('slide', 'telegraph', 'none')]:
            data = copy.deepcopy(self.data)
            p2 = data['beats'][12]['ext']['pattern_tables']['collatera_p2_margin_call']
            target = p2['arena'] if group == 'arena' else next(a for a in p2['attacks'] if a['id'] == 'slide_props')
            target[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(BuildError):
                self.rebuild(data)

    def test_wrong_zone_and_phase_three_reset_are_rejected(self):
        for mode in ('zone', 'p3', 'duplicate', 'small_hall'):
            data = copy.deepcopy(self.data)
            tables = data['beats'][12]['ext']['pattern_tables']
            if mode == 'zone':
                data['space']['beats'][12]['zone'] = 6
            elif mode == 'small_hall':
                data['space']['zones'][data['space']['beats'][12]['zone']]['rect'][2] -= 1000
            elif mode == 'p3':
                tables['collatera_p3_sabre']['arena']['list_deg'] = 0
            else:
                tables['collatera_p2_margin_call']['attacks'].append(dict(id='slide_props'))
            with self.subTest(mode=mode), self.assertRaises(BuildError):
                self.rebuild(data)

    def test_boss_scheduler_and_slide_damage_match_the_contract(self):
        bosses = json.loads((ROOT/'Content/Data/bosses.json').read_text())
        boss = next(b for b in bosses['bosses'] if b['id'] == 'boss_collatera')
        attack = next(a for a in boss['attacks'] if a['id'] == 'slide_props')
        self.assertEqual((attack['windup_ms'], attack['damage'], attack['zone']['stagger_ms']), (700, 30, 600))
        timer = next(t for t in boss['phases'][1]['concurrent'] if t['attack'] == 'slide_props')
        self.assertEqual(timer['every_ms'], 6000)

    def test_actual_production_rules(self):
        with tempfile.TemporaryDirectory() as temporary:
            binary = Path(temporary)/'bridge'
            subprocess.run(['c++', '-std=c++17', '-Wall', '-Wextra', '-Werror', '-pedantic',
                            '-I', str(ROOT/'Source/SoraArena/Public'),
                            str(ROOT/'scripts/unreal/bridge_rules_driver.cpp'), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True)


if __name__ == '__main__':
    unittest.main()
