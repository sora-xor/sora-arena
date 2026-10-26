"""Authored ledger/palace geometry and encounter contracts, without Unreal.

These tests establish source coordinates and supported corridors. The real
collision, movement, patrol timing and stealth routes need Unreal evidence.
"""
import copy
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import campaign_ledger as ledger
from campaign_palace import palace_valid

ROOT = Path(__file__).resolve().parents[2]


class LedgerContract(unittest.TestCase):
    def setUp(self):
        self.chapter=json.loads((ROOT/'Content/Data/campaign/chapter_06.json').read_text())
        self.annex,self.record=self.chapter['space']['beats'][4:6]
        self.guards=self.chapter['beats'][5]['task']['guards']
        self.zone=self.chapter['space']['zones'][self.record['zone']]
        self.origin=self.record['ledger_hall']['origin_cm']
        self.palace=self.record['ledger_hall']['palace_origin_cm']

    def test_authored_hall_annex_and_north_link_share_real_floor(self):
        self.assertTrue(ledger.ledger_valid(self.chapter))
        self.assertTrue(palace_valid(self.chapter))
        self.assertEqual(self.origin,[25800,-8235])
        self.assertEqual(self.palace,[28800,-1565])
        floors=ledger.floor_rects(self.origin)
        self.assertEqual([floors[0][2]-floors[0][0],floors[0][3]-floors[0][1]],[2400,6400])
        self.assertEqual([floors[1][2]-floors[1][0],floors[1][3]-floors[1][1]],[1000,800])
        self.assertEqual(self.zone['wall_cm'],600)
        self.assertEqual(ledger.SHELF_X,(0,440,880,1320,1760,2200))
        for left,right in zip(ledger.SHELF_X,ledger.SHELF_X[1:]):
            self.assertEqual(right-left-120,320)
        self.assertEqual(ledger.CROSS_AISLES,(1200,2800,4400,6000))
        rects=floors+ledger.palace_floors(self.palace)
        # Shared seams support the whole capsule; an enclosing zone rectangle
        # must not invent floor in the west void beside the long hall.
        for x,y in ((0,320),(2100,6400),(2400,6535)):
            self.assertTrue(ledger.union_supports(rects,ledger.p(self.origin,x,y),42))
        self.assertFalse(ledger.union_supports(rects,ledger.p(self.origin,-500,2000),42))
        self.assertFalse(ledger.union_supports(rects,ledger.p(self.origin,1800,6500),42))
        self.assertFalse(ledger.union_supports(rects,ledger.p(self.origin,1965,6670),42))

    def test_five_aisles_cross_aisles_and_six_hiding_niches_clear_capsule(self):
        shelves=ledger.shelf_rects((0,0))
        self.assertEqual(len(shelves),30)
        def free(point):
            return not any(ledger.inside([a-34,b-34,c+34,d+34],point) for a,b,c,d in shelves)
        for x in (280,720,1160,1600,2040):
            for y in range(300,6301,25):
                self.assertTrue(free((x,y)),(x,y))
        for y in (1200,2800,4400,6000):
            for x in range(160,2161,25):
                self.assertTrue(free((x,y)),(x,y))
        for bank,y in ledger.NICHES:
            self.assertTrue(free((ledger.SHELF_X[bank]+60,y)))
            self.assertFalse(free((ledger.SHELF_X[bank]+60,y-100)))

    def test_reinforcements_have_two_supported_distinct_capsules_behind_each_door(self):
        floors=ledger.floor_rects((0,0));shelves=ledger.shelf_rects((0,0))
        for i,at in enumerate(ledger.REINFORCEMENTS):
            self.assertTrue(ledger.union_supports(floors,at,42))
            self.assertFalse(any(ledger.inside([a-42,b-42,c+42,d+42],at) for a,b,c,d in shelves))
            target=(at[0],6300 if i<2 else 200)
            for step in range(51):
                point=[at[j]+(target[j]-at[j])*step/50 for j in range(2)]
                self.assertTrue(ledger.union_supports(floors,point,42),point)
            self.assertGreaterEqual(math.dist(at,ledger.REINFORCEMENTS[i^1]),84)

    def test_lockdown_clock_waits_for_clearance_and_holds_closed_for_thirty_active_seconds(self):
        source=r'''
#include "SoraLedgerRules.h"
#include <cassert>
int main() {
    using namespace SoraLedgerRules;
    FLockdown s;
    TickLockdown(s,1000,false);assert(s.Phase==ELockdown::Dormant);
    assert(BeginLockdown(s));assert(!BeginLockdown(s));
    TickLockdown(s,500,false);assert(s.TravelMs==500);
    for(int i=0;i<4000;++i) TickLockdown(s,10,true);
    assert(s.TravelMs==500&&s.HeldMs==0&&s.EntranceMs==1000);
    TickLockdown(s,1000,false);assert(s.Phase==ELockdown::Holding&&s.HeldMs==0);
    TickLockdown(s,29999,false);assert(s.Phase==ELockdown::Holding);
    TickLockdown(s,0,false);assert(s.HeldMs==29999);
    TickLockdown(s,1,false);assert(s.Phase==ELockdown::Opening);
    TickLockdown(s,1499,false);assert(s.TravelMs==1);
    TickLockdown(s,1,false);assert(s.Phase==ELockdown::Finished&&s.TravelMs==0);
    assert(!BeginLockdown(s));s={};assert(BeginLockdown(s));
    assert(ShutterY==4400&&ShutterTop==600&&ShutterHoldMs==30000);
}
'''
        compiler=os.environ.get('CXX') or shutil.which('clang++') or shutil.which('c++')
        self.assertIsNotNone(compiler,'Host C++ compiler is required')
        with tempfile.TemporaryDirectory() as tmp:
            cpp,binary=Path(tmp)/'lockdown.cpp',Path(tmp)/'lockdown'
            cpp.write_text(source)
            subprocess.run([compiler,'-std=c++17','-I',str(ROOT/'Source/SoraArena/Public'),str(cpp),'-o',str(binary)],
                           check=True,capture_output=True,text=True)
            subprocess.run([str(binary)],check=True,capture_output=True,text=True)

    def test_continuous_annex_to_vestibule_route_includes_both_quiet_rooms(self):
        floor=ledger.floor_rects(self.origin)+ledger.palace_floors(self.palace)
        shelves=ledger.shelf_rects(self.origin)
        path=[ledger.p(self.origin,*v) for v in ((-700,400),(-150,400),(-150,320),(280,320),
              (280,1200),(2040,1200),(2040,6300),(2100,6300),(2100,6535))]
        path += [ledger.p(self.palace,*v) for v in ((-300,-135),(250,-135),(250,-670),
                 (2150,-670),(2150,-135),(2535,-135),(2535,1900),(2540,2500))]
        for a,b in zip(path,path[1:]):
            n=max(1,math.ceil(math.dist(a,b)/25))
            for i in range(n+1):
                p=[a[j]+(b[j]-a[j])*i/n for j in range(2)]
                self.assertTrue(ledger.union_supports(floor,p,34),p)
                self.assertFalse(any(ledger.inside([x-34,y-34,x1+34,y1+34],p)
                                     for x,y,x1,y1 in shelves),p)
        self.assertEqual(self.record['exit']['center'],path[-1])
        self.assertEqual(self.record['exit']['size'],[500,400])

    def test_guard_identity_posts_scans_and_patrol_assignment_cannot_cycle_by_modulo(self):
        self.assertEqual(len(self.guards),12)
        self.assertEqual(len(self.record['patrols']),12)
        self.assertEqual([g['type'] for g in self.guards],
                         ['auditor']*4+['enforcer_rifle']*2+['drone']*2+['auditor']*2+['enforcer_rifle']*2)
        for i,g in enumerate(self.guards):
            self.assertEqual(g['post'],i in (4,5,8,11))
            self.assertEqual(self.record['spawns'][i],self.record['patrols'][i][0])
        for i in (4,5):
            self.assertEqual((self.guards[i]['scan_deg'],self.guards[i]['scan_ms']),(90,8000))
        for i in range(4):
            x=self.origin[0]+(280,720,1600,2040)[i]
            self.assertTrue(all(p[0]==x for p in self.record['patrols'][i]))
        self.assertEqual(ledger.PERIODS[6:8],(35000,35000))
        self.assertEqual(ledger.HEIGHTS[6:8],(550,550))
        self.assertEqual(ledger.PERIODS[10],40000)
        self.assertEqual(ledger.YAWS[8],90)
        self.assertEqual(ledger.YAWS[11],-90)

    def test_noise_rectangles_include_two_legs_three_puddles_two_rooms_and_20cm_edges(self):
        patches=self.record['fieldcraft']['surfaces']
        self.assertEqual([p['kind'] for p in patches],['nightingale_floor']*2+['gravel']+['tatami']*2+['puddle']*3+['edge_strip']*2)
        self.assertEqual(patches[0]['size'],[3000,270])
        self.assertEqual(patches[1]['size'],[270,2470])
        self.assertEqual([p['size'] for p in patches[5:8]],[[200,200]]*3)
        self.assertEqual([p['size'] for p in patches[-2:]],[[3000,20],[20,2200]])
        self.assertEqual([p['crouch_permille'] for p in patches[-2:]],[0,0])
        self.assertEqual([a['at'] for a in self.record['fieldcraft']['alarms']],
                         [ledger.p(self.origin,280,2800),ledger.p(self.origin,2040,4400)])
        self.assertEqual(self.record['fieldcraft']['stones']['piles'],
                         [ledger.p(self.origin,1160,1200),ledger.p(self.origin,720,4400),ledger.p(self.origin,1600,6000)])

    def test_missing_or_changed_spatial_encounter_contract_is_rejected(self):
        changes=(
            lambda c:c['space']['beats'][5].pop('ledger_hall'),
            lambda c:c['space']['beats'][4]['ledger_hall'].update(extra=1),
            lambda c:c['space']['beats'][0].update(ledger_hall=self.record['ledger_hall']),
            lambda c:c['space']['beats'][5]['ledger_hall']['origin_cm'].__setitem__(0,0),
            lambda c:c['space']['beats'][5]['patrols'].pop(),
            lambda c:c['space']['beats'][5]['patrols'].__setitem__(1,c['space']['beats'][5]['patrols'][0]),
            lambda c:c['space']['beats'][5]['spawns'][11].__setitem__(1,0),
            lambda c:c['space']['beats'][5]['exit'].update(center=self.record['entry'][:2]),
            lambda c:c['space']['beats'][4]['exit'].update(center=[0,0]),
            lambda c:c['space']['beats'][5]['fieldcraft']['surfaces'].pop(),
            lambda c:c['space']['beats'][5]['fieldcraft']['surfaces'][-1].update(size=[200,2200]),
            lambda c:c['space']['beats'][5]['fieldcraft']['stones']['piles'][0].__setitem__(0,0),
            lambda c:c['space']['beats'][5]['fieldcraft']['alarms'][0].update(at=[0,0]),
            lambda c:c['space']['beats'][5]['volumes'].pop(),
            lambda c:c['beats'][5]['task']['guards'][0].update(type='drone'),
            lambda c:c['beats'][5]['task']['guards'][4].update(scan_ms=4000),
            lambda c:c['beats'][5]['task']['guards'][11].update(post=False),
            lambda c:c['space']['zones'][self.record['zone']]['cover'].append([0,0,100,100,100]),
            lambda c:c['space']['zones'][self.record['zone']].update(wall_cm=450),
            lambda c:c['beats'][5]['params']['waves'][0]['enemies'][1].update(spawn='sp_aisle_north_door'),
            lambda c:c['beats'][5]['params']['waves'][0]['enemies'][0].update(count=3),
            lambda c:c['beats'][5]['params']['waves'][0].update(effects=[]),
            lambda c:c['beats'][5]['task']['waves'][0].update(event='alert_state:alert'),
        )
        for i,change in enumerate(changes):
            with self.subTest(mutation=i):
                chapter=copy.deepcopy(self.chapter);change(chapter)
                self.assertFalse(ledger.ledger_valid(chapter))

    def test_cpp_routes_periods_flight_layers_posts_and_geometry_match_generated_data(self):
        source=r'''
#include "SoraLedgerRules.h"
#include <iostream>
int main() {
    using namespace SoraLedgerRules;
    std::cout<<HallWidth<<' '<<HallLength<<' '<<HallHeight<<' '<<ShelfWidth<<' '<<ShelfHeight<<'\n';
    for(int i=0;i<GuardCount;++i) {
        std::cout<<PeriodMs[i]<<' '<<HeightCm[i]<<' '<<Yaw[i]<<' '<<IsPost(i);
        for(int j=0;j<PointCount(i);++j) std::cout<<' '<<Points[i][j].X<<' '<<Points[i][j].Y;
        std::cout<<'\n';
    }
    for(int i=0;i<6;++i) std::cout<<ShelfX[i]<<' '<<NicheY[i]<<'\n';
    for(auto p:ShelfY) std::cout<<p.X<<' '<<p.Y<<'\n';
    for(auto p:Reinforcement) std::cout<<p.X<<' '<<p.Y<<'\n';
}
'''
        compiler=os.environ.get('CXX') or shutil.which('clang++') or shutil.which('c++')
        self.assertIsNotNone(compiler,'Host C++ compiler is required')
        with tempfile.TemporaryDirectory() as tmp:
            cpp,binary=Path(tmp)/'ledger.cpp',Path(tmp)/'ledger'
            cpp.write_text(source)
            subprocess.run([compiler,'-std=c++17','-I',str(ROOT/'Source/SoraArena/Public'),str(cpp),'-o',str(binary)],
                           check=True,capture_output=True,text=True)
            result=subprocess.run([str(binary)],check=True,capture_output=True,text=True)
        rows=[list(map(int,row.split())) for row in result.stdout.splitlines()]
        self.assertEqual(rows[0],[2400,6400,600,120,450])
        for i,row in enumerate(rows[1:13]):
            self.assertEqual(row[:4],[ledger.PERIODS[i],ledger.HEIGHTS[i],ledger.YAWS[i],int(i in ledger.POSTS)])
            local=list(zip(row[4::2],row[5::2]));origin=self.origin if i<8 else self.palace
            self.assertEqual([ledger.p(origin,*p) for p in local],self.record['patrols'][i])
        self.assertEqual(rows[13:19],[[x,y] for x,(_,y) in zip(ledger.SHELF_X,ledger.NICHES)])
        self.assertEqual(rows[19:23],[list(p) for p in ledger.SHELF_Y])
        self.assertEqual(rows[23:27],[list(p) for p in ledger.REINFORCEMENTS])


if __name__=='__main__':
    unittest.main()
