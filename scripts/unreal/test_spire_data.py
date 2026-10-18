"""Authored vertical encounter contract and a continuous walkable spiral."""
from copy import deepcopy
import json
import math
from pathlib import Path
import unittest
from build_campaign_data import BuildError, fail
from campaign_spire import place_spire
from campaign_space import Zone

ROOT = Path(__file__).resolve().parents[2]


class SpireDataTests(unittest.TestCase):
    def setUp(self):
        self.chapter = json.loads((ROOT/'Content/Data/campaign/chapter_08.json').read_text())
        self.record = self.chapter['space']['beats'][9]

    def test_continuous_ramp_and_floor_specific_wave_posts(self):
        s = self.record['spire']
        self.assertEqual((s['width_cm'],s['void_diameter_cm']),(400,1400))
        ramp = s['ramp']
        self.assertEqual(len(ramp),25)
        self.assertEqual([ramp[n][2] for n in (0,8,16,24)],[0,900,1800,2700])
        total = 0
        for a,b in zip(ramp,ramp[1:]):
            run=math.dist(a[:2],b[:2]); total+=run
            self.assertGreater(b[2],a[2])
            self.assertLess((b[2]-a[2])/run,1/11.9)
            self.assertGreater((b[2]-a[2])/run,1/12.5)
        self.assertAlmostEqual(total/2700,12.32,delta=.02)
        # Four turns have 6.75 m vertical clearance: no upper winding
        # intersects a standing character on the lower ramp.
        for n in range(19):
            self.assertEqual(ramp[n+6][:2],ramp[n][:2])
            self.assertEqual(ramp[n+6][2]-ramp[n][2],675)
        self.assertEqual([p[2] for p in s['spawns']],[900]*5+[1800]*4+[2100]*4+[2700]*3)
        self.assertEqual([p[:2] for p in s['spawns']],self.record['spawns'])
        v = {v['event']:v for v in self.record['volumes']}
        self.assertEqual(v['volume_enter:vol_spire_L3']['floor_cm'],1800)
        self.assertEqual(v['volume_enter:vol_spire_L3']['center'],ramp[16][:2])
        self.assertEqual(self.record['exit']['floor_cm'],2700)
        lift=self.chapter['space']['beats'][10]
        self.assertEqual(s['center'],lift['anchor'])
        self.assertEqual(ramp[-1][2],lift['height_cm'])

    def zones(self):
        return [Zone(z['id'],z['place'],z['style'],z['form'],z['rect'],z['wall_cm']) for z in self.chapter['space']['zones']]

    def test_preserves_task_and_checkpoint_semantics_and_is_deterministic(self):
        beats=deepcopy(self.chapter['beats']); rows=deepcopy(self.chapter['space']['beats'])
        original=deepcopy(beats)
        place_spire(beats,rows,self.zones(),fail)
        self.assertEqual(rows,self.chapter['space']['beats'])
        self.assertEqual(beats,original)
        task=beats[9]['task']
        self.assertEqual(task['goal'],'waves_cleared')
        self.assertEqual(beats[9]['target_s'],240)
        self.assertTrue(beats[9]['checkpoint'])
        self.assertTrue(beats[10]['checkpoint'])

    def test_rejects_wave_contract_drift(self):
        for key,value in [('spawn','ground'),('count',5),('type','drone')]:
            beats=deepcopy(self.chapter['beats'])
            beats[9]['params']['waves'][0]['enemies'][0][key]=value
            with self.subTest(key=key),self.assertRaises(BuildError):
                place_spire(beats,deepcopy(self.chapter['space']['beats']),self.zones(),fail)

if __name__=='__main__':
    unittest.main()
