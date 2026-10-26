"""Compiled scanner/scheduler and physical layout checks; UE motion is separate."""
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
import campaign_ward_gate as ward

ROOT=Path(__file__).resolve().parents[2]


class WardGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.chapter=json.loads((ROOT/'Content/Data/campaign/chapter_03.json').read_text())
        cls.enemies={e['id']:e for e in json.loads((ROOT/'Content/Data/enemies.json').read_text())['archetypes']}
        env=os.environ.copy();flags=[]
        compiler=shutil.which('clang++') or shutil.which('c++')
        if platform.system()=='Darwin':
            pins=json.loads((ROOT/'scripts/toolchain/versions.json').read_text())
            env['DEVELOPER_DIR']=env.get('SORA_DEVELOPER_DIR') or str(Path(pins['default_macos_xcode']).expanduser())
            compiler=subprocess.check_output(['xcrun','--find','clang++'],env=env,text=True).strip()
            sdk=subprocess.check_output(['xcrun','--sdk','macosx','--show-sdk-path'],env=env,text=True).strip()
            flags=['-isysroot',sdk]
        if not compiler:raise RuntimeError('A C++ compiler is required')
        with tempfile.TemporaryDirectory(prefix='sora-ward-gate-') as directory:
            binary=Path(directory)/'ward-gate'
            subprocess.run([compiler,'-std=c++20','-UNDEBUG','-Wall','-Wextra','-Werror',
                '-fsanitize=undefined','-fsanitize-trap=undefined',*flags,'-I',str(ROOT/'Source/SoraArena/Public'),
                str(ROOT/'scripts/unreal/ward_gate_rules_driver.cpp'),'-o',str(binary)],check=True,env=env)
            cls.native=json.loads(subprocess.check_output([str(binary)],text=True,env=env))

    @staticmethod
    def record(chapter):return next(r for r in chapter['space']['beats'] if r['beat']=='ch03.b03')

    def solids(self):
        walls=self.native['landing_walls']+ward.walls()
        return self.native['solids']+[['boundary',x,y,h/2,w,d,h] for x,y,w,d,h in walls]

    @staticmethod
    def sample(points,step=5):
        for a,b in zip(points,points[1:]):
            n=max(1,math.ceil(math.dist(a,b)/step))
            for i in range(n+1):yield [a[j]+(b[j]-a[j])*i/n for j in range(2)]

    @staticmethod
    def capsule_hits(solid,point,feet=2,radius=34,height=176):
        _,x,y,z,w,d,h=solid
        # Distance from the capsule's vertical spine to the box. This tests
        # its rounded caps too, rather than inflating all corners into cubes.
        dx=max(abs(point[0]-x)-w/2,0);dy=max(abs(point[1]-y)-d/2,0)
        dz=max(z-h/2-(feet+height-radius),(feet+radius)-(z+h/2),0)
        return dx*dx+dy*dy+dz*dz<radius*radius-1e-6

    def floor_at(self,p):
        heights=[top for _,x0,y0,x1,y1,top in self.native['ground'] if x0<=p[0]<=x1 and y0<=p[1]<=y1]
        if -22000<=p[0]<=-7600 and -2800<=p[1]<=-660:heights.append(0)
        return max(heights,default=None)

    def test_native_routes_and_periods_match_generated_contract(self):
        r=self.record(self.chapter)
        self.assertTrue(ward.ward_gate_valid(self.chapter))
        self.assertEqual([x['points'] for x in self.native['routes']],r['patrols'])
        self.assertEqual([x['period'] for x in self.native['routes']],r['ward_gate']['periods_ms'])
        self.assertEqual(r['ward_gate']['periods_ms'],[0,40000,0,0,50000])

    def test_patrol_capsules_clear_solids_and_stationary_guards(self):
        routes=self.native['routes'];solids=self.solids()
        posts=[route['points'][0] for route in routes if route['period']==0]
        for index in (1,4):
            route=routes[index]['points']
            for point in self.sample(route+route[:1]):
                self.assertEqual(self.floor_at(point),0,(index,point,'unsupported patrol'))
                for solid in solids:self.assertFalse(self.capsule_hits(solid,point),(index,point,solid[0]))
                for post in posts:self.assertGreater(math.dist(point,post),68,(index,point,post))
            # The scheduler varies input pace against the real catalog speed.
            # Arrival remains a physics test; deadlines cannot skip it.
            speed=self.enemies['bound_conscript' if index==1 else 'enforcer_rifle']['speed_cm_s']
            self.assertLess(max(math.dist(a,b) for a,b in zip(route,route[1:]+route[:1])),
                            speed*routes[index]['period']/len(route)/1000)
        # These patrols must not be parallel only 50 cm apart, or even their
        # initial bodies overlap. Their complete paths stay a body-width apart.
        a=routes[1]['points'];b=routes[4]['points']
        for p in self.sample(a+a[:1],20):
            for q in self.sample(b+b[:1],20):self.assertGreater(math.dist(p,q),68,(p,q))

    def test_entrance_is_open_and_does_not_double_layer_the_landing(self):
        for point in self.sample([[-7820,-1150],[-7820,-550],[-7000,-550]]):
            self.assertEqual(self.floor_at(point),0)
            for solid in self.solids():self.assertFalse(self.capsule_hits(solid,point),(point,solid[0]))
        for name,x0,y0,x1,y1,_ in self.native['ground']:
            self.assertFalse(max(x0,-8000)<min(x1,-7600) and max(y0,-1000)<min(y1,-660),name)

    def test_culvert_is_authored_size_and_stair_descent_clears_hut(self):
        r=self.record(self.chapter)['ward_gate']
        self.assertEqual(r['culvert_cm'],[-6200,-650,-90,300,100,90])
        samples=[([-6390,-875],0),([-6390,-825],-30),([-6390,-775],-60),([-6390,-725],-90),
                 ([-6390,-650],-90),([-6200,-650],-90),([-6025,-650],-90),([-5975,-650],-60),([-5925,-650],-30),([-5875,-650],0)]
        for point,height in samples:
            self.assertEqual(self.floor_at(point),height,point)
            # Geometric crouch clearance only. UE's floor hover and movement
            # into a 90 cm tunnel still need a mapped-input runtime fixture.
            for solid in self.solids():self.assertFalse(self.capsule_hits(solid,point,feet=height+1,height=88),(point,solid[0]))
        roof=next(s for s in self.native['solids'] if s[0]=='WardCulvertRoof')
        self.assertTrue(self.capsule_hits(roof,[-6200,-650],feet=-89,height=176))

    def test_wicket_gap_and_roof_firewall_exist(self):
        solids=self.solids()
        for point in self.sample([[-6300,135],[-6100,135]]):
            for solid in solids:self.assertFalse(self.capsule_hits(solid,point,height=88),(point,solid[0]))
        lintel=next(s for s in solids if s[0]=='WardWicketLintel')
        self.assertTrue(self.capsule_hits(lintel,[-6200,135]))
        wall=next(s for s in solids if s[0]=='WardUdatsu')
        self.assertEqual(wall[3]-wall[6]/2,320)
        self.assertEqual(wall[6],40)

    def test_fixed_bindings_reject_geometry_sensor_and_guard_mutations(self):
        r=self.record(self.chapter)
        for key,value in [('fence_height_cm',200),('culvert_cm',[-6200,-650,-90,200,100,90]),
                          ('scanner_cm',[-6200,-45,0,20,360,240]),('shared_landing_cm',[-8000,-1000,-7500,-660]),
                          ('periods_ms',[0,40000,0,0,40000]),('guard_ids',list(reversed(ward.IDS))),('extra',1)]:
            with self.subTest(key=key):
                c=copy.deepcopy(self.chapter);self.record(c)['ward_gate'][key]=value
                self.assertFalse(ward.ward_gate_valid(c))
        for mutate in [lambda r,z:r['patrols'][1][3].__setitem__(1,-650),
                       lambda r,z:r['fieldcraft']['surfaces'][3].__setitem__('height_cm',0),
                       lambda r,z:r['fieldcraft']['lamps'][2].__setitem__('snuff','shot'),
                       lambda r,z:z['walls'][2].__setitem__(2,2400),lambda r,z:r['fieldcraft']['ladders'].clear()]:
            c=copy.deepcopy(self.chapter);r=self.record(c);mutate(r,c['space']['zones'][r['zone']])
            self.assertFalse(ward.ward_gate_valid(c))

    def test_shared_entrance_exception_is_exact_and_cannot_move_to_other_places(self):
        zones=self.chapter['space']['zones'];a=next(z for z in zones if z['place']=='pl_horiwari');b=next(z for z in zones if z['place']=='pl_kido')
        self.assertTrue(ward.shared_approach(self.chapter,a,b));self.assertTrue(ward.shared_approach(self.chapter,b,a))
        moved=copy.deepcopy(b);moved['rect'][0]-=1
        self.assertFalse(ward.shared_approach(self.chapter,a,moved))
        for zone in zones:
            if zone not in (a,b):self.assertFalse(ward.shared_approach(self.chapter,a,zone))

    def test_binding_is_required_once_and_isolated_from_other_chapters(self):
        c=copy.deepcopy(self.chapter);del self.record(c)['ward_gate']
        self.assertFalse(ward.ward_gate_valid(c))
        for path in sorted((ROOT/'Content/Data/campaign').glob('chapter_*.json')):
            if path.name=='chapter_03.json':continue
            c=json.loads(path.read_text());self.assertTrue(ward.ward_gate_valid(c))
            c['space']['beats'][0]['ward_gate']=ward.contract();self.assertFalse(ward.ward_gate_valid(c))


if __name__=='__main__':unittest.main()
