"""An elevated disc, a walkable 18 m stair, and unchanged cinematic/boss rules."""
import json
import copy
from build_campaign_data import normalize_task, BuildError
import math
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]


class SummitDataTests(unittest.TestCase):
    def setUp(self):
        self.c=json.loads((ROOT/'Content/Data/campaign/chapter_08.json').read_text())
        self.rows=self.c['space']['beats']

    def test_stair_reaches_real_summit_before_gallery_exit(self):
        spec=self.rows[12]['summit']; stairs=spec['stairs']
        self.assertEqual((spec['height_cm'],spec['radius_cm'],spec['dais_cm']),(16000,1800,120))
        self.assertEqual(stairs[0][2],14200)
        self.assertEqual(stairs[-1][2]-stairs[0][2],1800)
        self.assertEqual(stairs[-1][:2],self.rows[12]['entry'][:2])
        self.assertEqual(self.rows[11]['exit']['center'],stairs[-1][:2])
        self.assertEqual(self.rows[11]['exit']['floor_cm'],16000)
        for index,(a,b) in enumerate(zip(stairs,stairs[1:]),1):
            rise=b[2]-a[2]; n=max(1,math.ceil(rise/18))
            self.assertGreaterEqual(rise,0)
            self.assertLessEqual(rise/n,18)
            run=math.dist(a[:2],b[:2])-(200 if index>1 else 0)-(200 if index<len(stairs)-1 else 0)
            self.assertGreaterEqual(run/n,45)
        self.assertEqual(spec['center'],self.rows[10]['anchor'])

    def test_capture_keeps_outcome_but_requires_the_authored_hold(self):
        beat=self.c['beats'][13]
        self.assertEqual(beat['task']['capture_event'],'interact:engine_spine')
        self.assertEqual(beat['task']['capture_hold_ms'],1500)
        self.assertEqual(beat['task']['defeat'],'capture')
        for value in (0,-1,None):
            bad=copy.deepcopy(beat); bad['ext']['post_defeat']['hold_s']=value
            with self.assertRaises((BuildError,ValueError,TypeError)):
                normalize_task(bad)
        for row in self.c['beats']:
            if row['id']!='ch08.b14': self.assertEqual(row['task']['capture_hold_ms'],0)

    def test_only_seizure_phase_owns_the_construct_group(self):
        bosses=json.loads((ROOT/'Content/Data/bosses.json').read_text())['bosses']
        boss=next(b for b in bosses if b['id']=='boss_val_amort')
        self.assertEqual([(g['id'],g['variant'],g['respawn_ms']) for g in boss['adds']],
                         [('constructs','collateral_construct',10000)])
        p1,p2,p3=boss['phases']
        self.assertEqual(p2['shield_while_adds'],'constructs')
        self.assertEqual(p2['summons'],[{'attack':'construct_spawn','at_permille':700},
                                        {'attack':'construct_spawn','at_permille':550}])
        self.assertEqual(p2['concurrent'],[{'attack':'amort_seizure_field','every_ms':9000,'first_ms':2000}])
        for phase in (p1,p3):
            self.assertEqual(phase['summons'],[])
            self.assertEqual(phase['shield_while_adds'],'')
        self.assertEqual(p3['concurrent'],[])
        self.assertEqual(set(p3['pattern']['attacks']),
                         {'amort_final_foreclosure','amort_cane_pair','amort_cane_thrust'})

    def test_foreclosure_memory_reuses_a_previously_heard_line(self):
        prompt=next(p for p in self.c['ui_prompts'] if p['id']=='ch08.b14.prompt.002')
        self.assertEqual(prompt['on'],'event:first_foreclosure')
        triggers=self.c['triggers']
        recall=next(t for t in triggers if t['beat']=='ch08.b14' and t['on']=='event:first_foreclosure')
        self.assertEqual(recall['mode'],'ambient')
        self.assertFalse(recall['repeatable'])
        self.assertEqual(recall['lines'],['ch08.b09.sekireisai.003'])
        self.assertTrue(any(t['beat']=='ch08.b09' and recall['lines'][0] in t['lines'] for t in triggers))
        # The memory requires explicit once-only replay; marking the original
        # line globally repeatable would change its earlier dialogue contract.
        line=next(l for l in self.c['lines'] if l['id']==recall['lines'][0])
        self.assertFalse(line['repeatable'])

    def test_overlapping_places_are_separated_by_height(self):
        a=self.c['space']['zones'][self.rows[9]['zone']]
        b=self.c['space']['zones'][self.rows[12]['zone']]
        self.assertEqual(a['z_bounds_cm'],[-500,15800])
        self.assertEqual(b['z_bounds_cm'],[15800,20000])
        self.assertLess(a['rect'][0],b['rect'][2])
        self.assertGreater(a['rect'][2],b['rect'][0])
        for row in self.rows[12:15]:
            self.assertEqual(row['height_cm'],16000)
            self.assertEqual(row['summit'],self.rows[12]['summit'])
            self.assertEqual(row['entry'][2],90)
            if row['camera']:
                self.assertTrue(all(row['camera'][i]>16000 for i in (2,5,8)))
        self.assertEqual([b['target_s'] for b in self.c['beats'][12:15]],[120,540,150])
        self.assertEqual(self.c['beats'][12]['requires'],['ch08.b11'])

if __name__=='__main__':
    unittest.main()
