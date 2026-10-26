"""Actual compiled workshop solids, capsule paths and generated-data rejection.

These are source geometry tests. CharacterMovement step-up, combat and visual
acceptance require Unreal runs and are deliberately not inferred here.
"""
import copy
import json
import math
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import unittest
import campaign_lantern_workshop as workshop
import test_tenements as tenement_geometry

ROOT=Path(__file__).resolve().parents[2]


class LanternWorkshopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.chapter=json.loads((ROOT/'Content/Data/campaign/chapter_03.json').read_text())
        env=os.environ.copy();flags=[]
        compiler=shutil.which('clang++') or shutil.which('c++')
        if platform.system()=='Darwin':
            pins=json.loads((ROOT/'scripts/toolchain/versions.json').read_text())
            env['DEVELOPER_DIR']=env.get('SORA_DEVELOPER_DIR') or str(Path(pins['default_macos_xcode']).expanduser())
            compiler=subprocess.check_output(['xcrun','--find','clang++'],env=env,text=True).strip()
            sdk=subprocess.check_output(['xcrun','--sdk','macosx','--show-sdk-path'],env=env,text=True).strip()
            flags=['-isysroot',sdk]
        if not compiler:raise RuntimeError('A C++ compiler is required')
        with tempfile.TemporaryDirectory(prefix='sora-lantern-workshop-') as directory:
            binary=Path(directory)/'workshop'
            subprocess.run([compiler,'-std=c++20','-UNDEBUG','-Wall','-Wextra','-Werror',
                '-fsanitize=undefined','-fsanitize-trap=undefined',*flags,'-I',str(ROOT/'Source/SoraArena/Public'),
                str(ROOT/'scripts/unreal/lantern_workshop_rules_driver.cpp'),'-o',str(binary)],check=True,env=env)
            cls.native=json.loads(subprocess.check_output([str(binary)],text=True,env=env))
        cls.solids=cls.native['solids']
        cls.benches=[[x,y,z+40,120,80,80,0,1] for x,y,z in cls.native['stations']]

    def clear(self,points,benches=False):
        for point in tenement_geometry.TenementTests.sample(points):
            for index,box in enumerate(self.solids+(self.benches if benches else [])):
                self.assertFalse(tenement_geometry.TenementTests.hits(box,point),(point,index,box))

    def test_generated_contract(self):
        self.assertTrue(workshop.workshop_valid(self.chapter))
        self.assertEqual([p[:2] for p in self.native['stations']],workshop.STATIONS)
        self.assertEqual([p[2] for p in self.native['stations']],[45,45,45,0])

    def test_oil_duration_and_damage_are_frame_partition_independent(self):
        rows=self.native['burn_partitions']
        self.assertEqual([r[0] for r in rows],[1,7,16,17,33,100,1000,5999,6000,7000,2147483647])
        self.assertEqual([r[1] for r in rows],[72]*len(rows))
        self.assertIs(self.native['hazard_boundary_assertions'],True)

    def test_authored_combat_spawns_and_group_mapping(self):
        self.assertEqual([p[:2] for p in self.native['combat_spawns']],workshop.COMBAT_SPAWNS)
        self.assertEqual([p[2] for p in self.native['combat_spawns']],[0]*7+[650])
        self.assertIs(self.native['entry_boundary_assertions'],True)
        for p in self.native['combat_spawns']:self.clear([[p[0],p[1],p[2]+2.15]])
        c=copy.deepcopy(self.chapter)
        b=next(r for r in c['space']['beats'] if r['beat']=='ch03.b08')
        b['spawns']=copy.deepcopy(workshop.SPAWNS)
        self.assertFalse(workshop.workshop_valid(c))

    def test_street_and_canal_entry_routes_clear_real_solids_and_cover(self):
        self.assertEqual(len(self.native['entry_routes']),5)
        for route in self.native['entry_routes']:
            self.clear(route)
            for p in tenement_geometry.TenementTests.sample(route):
                for box in self.native['hazard_solids']:
                    self.assertFalse(tenement_geometry.TenementTests.hits(box,p),(p,box))

    def test_vault_trajectory_clears_fence_and_lands_in_yard(self):
        vx,vz=self.native['vault_speed'];flight=2*vz/980
        for x,y,z in self.native['combat_spawns'][3:5]:
            points=[[x+vx*t,y,z+2.15+vz*t-490*t*t] for t in [flight*i/400 for i in range(401)]]
            self.clear(points)
            for p in points:
                for box in self.native['hazard_solids']:
                    self.assertFalse(tenement_geometry.TenementTests.hits(box,p),(p,box))
            self.assertLess(points[-1][0],3350)

    def test_hazard_proxies_preserve_yard_routes_and_shell_bench_clearance(self):
        hazards=self.native['hazard_solids']
        self.assertEqual(len(hazards),4)
        self.assertEqual(hazards[0],[2360,-1200,55,48,48,110,0,1])
        for point in tenement_geometry.TenementTests.sample(
                [[2000,-1800,2.15],[2440,-1800,2.15],[2440,-1030,2.15],[3480,-1030,2.15]]):
            for box in hazards:self.assertFalse(tenement_geometry.TenementTests.hits(box,point),(point,box))
        self.assertGreater(hazards[0][0]-hazards[0][3]/2,2326)
        self.assertGreater(math.dist(hazards[0][:2],self.native['stations'][3][:2]),180+140)

    def test_soft_cover_has_no_solid_building_or_well_overlap(self):
        for a in self.native['hazard_solids']:
            for b in self.solids:
                # Ground contact is intentional, penetration into another
                # collision box is not. All three dimensions must overlap.
                self.assertFalse(all(abs(a[i]-b[i])<(a[i+3]+b[i+3])/2-.01 for i in range(3)),(a,b))

    def test_rejects_changed_floor_door_station_route_and_collectible(self):
        for kind in ('floor','door','station','steps','zone','spawn','pickup','extra'):
            c=copy.deepcopy(self.chapter)
            b=next(r for r in c['space']['beats'] if r['beat']=='ch03.b09')
            if kind=='floor':b['lantern_workshop']['plank_cm'][-1]=0
            elif kind=='door':b['lantern_workshop']['back_door_cm'][-1]=60
            elif kind=='station':b['stations'][3]=[2100,-1300]
            elif kind=='steps':b['step_stations'][4]=2
            elif kind=='zone':c['space']['zones'][b['zone']]['rect'][0]-=1
            elif kind=='spawn':b['spawns'][0]=[3150,-1900]
            elif kind=='pickup':next(p for p in c['space']['pickups'] if p['collectible']=='ch03.c04')['at']=[3150,-200]
            else:c['space']['beats'][0]['lantern_workshop']=workshop.contract()
            self.assertFalse(workshop.workshop_valid(c),kind)

    def test_other_chapters_cannot_opt_into_workshop_geometry(self):
        for i in (1,2,4,5,6,7,8):
            c=json.loads((ROOT/f'Content/Data/campaign/chapter_{i:02}.json').read_text())
            self.assertTrue(workshop.workshop_valid(c))
            c['space']['beats'][0]['lantern_workshop']=workshop.contract()
            self.assertFalse(workshop.workshop_valid(c))

    def test_street_to_yard_and_canal_gate_are_clear(self):
        self.clear([[3000,0,2.15],[3480,0,2.15],[3480,-1030,2.15],
                    [3280,-1030,2.15],[2440,-1030,2.15],[2440,-1660,2.15],
                    [2000,-1800,2.15],[2000,-2420,2.15]],True)

    def test_storehouse_collectible_has_a_ground_floor_route_around_shell_bench(self):
        self.clear([[2000,-1800,2.15],[2650,-1800,2.15],[2650,-1900,2.15],
                    [3150,-1900,2.15],[3150,-2000,2.15]],True)
        self.assertIn([3150,-1900,0],self.native['floor_samples'])
        self.assertIn([3150,-2000,0],self.native['floor_samples'])

    def test_station_approaches_clear_benches_at_their_actual_floor_heights(self):
        self.clear([[1900,-1450,47.15],[1900,-620,47.15]],True)
        for x,y,z in self.native['stations']:
            self.clear([[x-150,y,z+2.15],[x-100,y,z+2.15]],True)
            self.assertLessEqual(math.dist([x-100,y],[x,y]),140)
        self.clear([[2650,-1900,2.15],[2650,-2050,2.15],[2690,-2050,2.15]],True)

    def test_earth_passage_and_half_height_steps_match_the_floor_query(self):
        self.clear([[1655,-1400,2.15],[1655,-500,2.15]],True)
        self.assertEqual(self.native['floor_samples'][:4],
                         [[1655,-950,0],[1745,-950,22.5],[1900,-1535,22.5],[1900,-1490,45]])
        for x,y,z in self.native['floor_samples'][:4]:
            self.clear([[x,y,z+2.15],[x,y,z+2.15]],True)
        step_tops=sorted({b[2]+b[5]/2 for b in self.solids if b[5]<=45 and b[7]==1})
        self.assertIn(22.5,step_tops);self.assertIn(45,step_tops)
        self.assertLessEqual(45-22.5,22.5)

    def test_roof_perch_is_supported_and_clear(self):
        self.assertTrue(any(b[2]+b[5]/2==650 and abs(3150-b[0])<=b[3]/2 and
                            abs(-1900-b[1])<=b[4]/2 for b in self.solids))
        self.clear([[3150,-1900,652.15],[3150,-1900,652.15]])

    def test_back_door_and_storehouse_openings_detect_filled_or_narrowed_geometry(self):
        for box,point in [([1900,-1500,150,140,12,300,0,1],[1900,-1500,47.15]),
                          ([2900,-1900,125,16,180,250,0,2],[2900,-1900,2.15]),
                          ([1900,-1500,150,80,12,300,0,1],[1900,-1500,47.15])]:
            self.assertTrue(tenement_geometry.TenementTests.hits(box,point))
        self.clear([[1900,-1500,47.15],[1900,-1450,47.15]])
        self.clear([[2850,-1900,2.15],[2950,-1900,2.15]],True)

    def test_craftspeople_shelter_inside_with_station_clearance(self):
        self.assertEqual(len(self.native['craft_routes']),4)
        for route in self.native['craft_routes']:
            self.clear(route,True)
            for x,y,z in route:
                self.assertTrue(1780<x<2320 and -1500<y<-400)
                self.assertEqual(z,47.15)

    def test_seal_needs_yard_side_grounded_reach(self):
        self.assertEqual(self.native['seal_reach'],[1,1,0,0,0,0,0])

    def test_seal_requires_uninterrupted_two_second_hold(self):
        # The common held-interaction rule consumes and clears a completed hold.
        self.assertEqual(self.native['hold_ms'],0)

    def test_seal_notice_waits_for_physical_cut(self):
        lines={'ch03.b08.system.001','ch03.b08.nyaakoto.002','ch03.b08.tokichi.003'}
        rows=[t for t in self.chapter['triggers'] if lines.intersection(t['lines'])]
        self.assertTrue(rows)
        self.assertEqual({line for t in rows for line in t['lines']},lines)
        self.assertTrue(all(t['beat']=='ch03.b08' and t['on'].startswith('workshop_seal_cut') for t in rows))

    def test_staging_spawns_have_standing_clearance(self):
        for x,y in workshop.SPAWNS:self.clear([[x,y,2.15],[x,y,2.15]],True)


if __name__=='__main__':unittest.main()
