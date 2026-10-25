"""Host-only authored press contract checks; no compiler or engine launch."""
import copy
import json
from pathlib import Path
import unittest
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))

from campaign_press import contract, press_hall_valid

ROOT = Path(__file__).resolve().parents[2]


class PressContract(unittest.TestCase):
    def setUp(self):
        self.chapter = json.loads((ROOT/'Content/Data/campaign/chapter_06.json').read_text())
        self.beat = next(b for b in self.chapter['beats'] if b['id']=='ch06.b11')
        self.record = next(b for b in self.chapter['space']['beats'] if b['beat']=='ch06.b11')
        self.hall = self.record['press_hall']

    def test_eight_authored_machines_and_three_distinct_master_holds(self):
        self.assertTrue(press_hall_valid(self.chapter))
        self.assertEqual([p['id'] for p in self.hall['presses']],
                         ['press_a1','press_a2','press_a3','press_b1','press_b2','press_b3','press_c1','press_c2'])
        self.assertEqual([p['objective'] for p in self.hall['presses']],[-1,0,-1,-1,1,-1,2,-1])
        self.assertEqual(self.beat['task']['objective_hold_ms'],[4000,4000,4000,0])

    def test_numeric_drift_missing_keys_and_extra_keys_are_rejected(self):
        for field in ('period_ms','window_ms','radius_cm','noise_permille','inspection_ms'):
            for value in (None,True,0,-1,'1600',self.hall[field]+1):
                with self.subTest(field=field,value=value):
                    saved=self.hall[field]; self.hall[field]=value
                    self.assertFalse(press_hall_valid(self.chapter));self.hall[field]=saved
        for key in tuple(self.hall):
            saved=self.hall.pop(key);self.assertFalse(press_hall_valid(self.chapter));self.hall[key]=saved
        self.hall['legacy_noise_radius']=800
        self.assertFalse(press_hall_valid(self.chapter))

    def test_reordered_duplicate_moved_and_remapped_machines_fail(self):
        original=copy.deepcopy(self.hall['presses'])
        for change in ('order','duplicate','moved','work','objective','bool'):
            rows=copy.deepcopy(original)
            if change=='order': rows[0],rows[1]=rows[1],rows[0]
            elif change=='duplicate': rows[1]=rows[0]
            elif change=='moved': rows[4]['center_cm'][0]+=1
            elif change=='work': rows[4]['work_cm'][1]+=1
            elif change=='objective': rows[4]['objective']=0
            else: rows[1]['objective']=False
            self.hall['presses']=rows
            self.assertFalse(press_hall_valid(self.chapter),change)
        self.hall['presses']=original

    def test_missing_or_unrelated_beat_contract_fails(self):
        other=self.chapter['space']['beats'][0]
        other['press_hall']=copy.deepcopy(self.hall)
        self.assertFalse(press_hall_valid(self.chapter))
        del other['press_hall'];del self.record['press_hall']
        self.assertFalse(press_hall_valid(self.chapter))

    def test_authored_rules_cannot_silently_normalize_to_old_defaults(self):
        for field,value in [('noise_mask',{'source':'press_stamp','period_ms':1600,'window_ms':501,'radius_cm':800,'player_noise_mult':0.2}),
                            ('press_silent_inspection',{'auditor_investigates_within_s':21})]:
            original=self.beat['ext'][field];self.beat['ext'][field]=value
            with self.assertRaises(ValueError):contract(self.beat,self.hall['origin_cm'])
            self.beat['ext'][field]=original

    def test_work_and_patrol_points_clear_every_machine_footprint(self):
        # A normal-size capsule can stand at every handle and patrol waypoint.
        points=self.record['objectives']+self.record['spawns']+[p for r in self.record['patrols'] for p in r]
        for point in points:
            for press in self.hall['presses']:
                x,y=press['center_cm']
                self.assertTrue(abs(point[0]-x)>=242 or abs(point[1]-y)>=192,(point,press['id']))


if __name__=='__main__':unittest.main()
