"""An elevated disc, a walkable 18 m stair, and unchanged cinematic/boss rules."""
import json
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
