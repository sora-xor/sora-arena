"""Source binding and current collision clearance; clock/contact execution is in UE fixtures."""
import copy
import json
from pathlib import Path
import unittest
from campaign_pods import PODS, HORSES, OFFSETS, contract, pods_valid
from campaign_space import arena_blockers

ROOT = Path(__file__).resolve().parents[2]


class PodArrivals(unittest.TestCase):
    def setUp(self):
        self.chapter = json.loads((ROOT/'Content/Data/campaign/chapter_02.json').read_text())

    def test_binds_original_named_points_and_three_existing_waves(self):
        self.assertTrue(pods_valid(self.chapter))
        row = self.chapter['space']['beats'][5]
        self.assertEqual(row['targets'], [[800, -1050], [1200, -1050]])
        self.assertEqual([a['release_ms'] for a in row['pod_arrivals']['arrivals']], [0, 45000, 95000])
        self.assertEqual(row['pod_arrivals'], contract(self.chapter['beats'][5], row, self.chapter['layout']))

    def test_stale_missing_duplicate_foreign_or_moved_source_fails(self):
        mutations = [
            lambda c: c['space']['beats'][5].pop('pod_arrivals'),
            lambda c: c['space']['beats'][5]['pod_arrivals']['arrivals'].pop(),
            lambda c: c['space']['beats'][5]['pod_arrivals']['arrivals'][1].update(wave=0),
            lambda c: c['space']['beats'][5]['pod_arrivals']['arrivals'][0].update(release_ms=1),
            lambda c: c['space']['beats'][5]['pod_arrivals'].update(floor_band_cm=[-20, 800]),
            lambda c: c['space']['beats'][5]['pod_arrivals'].update(hits_allies=False),
            lambda c: c['space']['beats'][5]['pod_arrivals']['spawn_offsets_cm'][0].__setitem__(0, -111),
            lambda c: c['space']['beats'][5]['targets'].__setitem__(0, [0, 220]),
            lambda c: c['space']['beats'][4].update(pod_arrivals=c['space']['beats'][5]['pod_arrivals']),
            lambda c: c['layout']['points'].append(copy.deepcopy(next(p for p in c['layout']['points'] if p['id']==PODS[0][0]))),
            lambda c: next(p for p in c['layout']['points'] if p['id']==PODS[0][0]).update(frame='other'),
            lambda c: next(p for p in c['layout']['points'] if p['id']==HORSES[0][0]).update(positions_cm=[[800,-1051,0]]),
            lambda c: c['beats'][5]['params']['waves'][1].update(trigger='after_s:46'),
            lambda c: c['beats'][5]['task']['waves'][2]['members'][0].update(type='grenadier'),
            lambda c: c['beats'][5]['task']['waves'][0]['members'][0].update(count=3.0),
            lambda c: c['beats'][5]['task'].update(max_alive=7),
            lambda c: c['space']['beats'].pop(),
        ]
        for i, mutate in enumerate(mutations):
            with self.subTest(mutation=i):
                c=copy.deepcopy(self.chapter); mutate(c); self.assertFalse(pods_valid(c))

    def test_authored_hazard_drift_rejected(self):
        for key in ('kind','telegraph','radius_cm','windup_ms','damage','hits_allies'):
            for value in (None,False,0,60.0,'60',[],{}):
                c=copy.deepcopy(self.chapter); c['beats'][5]['ext']['hazards'][0][key]=value
                with self.subTest(key=key,value=value): self.assertFalse(pods_valid(c))

    def test_current_horse_boxes_treatment_approaches_and_spawn_capsules_clear_collision(self):
        blockers=arena_blockers(0)
        def clear(x,y,hx,hy):
            self.assertGreater(x-hx,-3100);self.assertLess(x+hx,3100)
            self.assertGreater(y-hy,-2500);self.assertLess(y+hy,2500)
            self.assertFalse(any(x+hx>=x0 and x-hx<=x1 and y+hy>=y0 and y-hy<=y1
                                 for x0,y0,x1,y1 in blockers),(x,y,hx,hy))
        for _,(x,y,_) in HORSES:
            clear(x,y,32,100) # The real Frame box, yaw 90 degrees.
            clear(x-180,y,42,42) # Existing treatment fixture's approach, within 260 cm.
        for _,(x,y,_),_ in PODS:
            clear(x,y,42,42)
            for dx,dy in OFFSETS: clear(x+dx,y+dy,42,42)
        for a in range(3):
            for b in range(a):
                self.assertGreater(sum((OFFSETS[a][i]-OFFSETS[b][i])**2 for i in range(2)),84**2)
        for _,horse in HORSES:
            for _,pod,_ in PODS:
                self.assertGreater(sum((horse[i]-pod[i])**2 for i in range(2)),350**2)


if __name__ == '__main__': unittest.main()
