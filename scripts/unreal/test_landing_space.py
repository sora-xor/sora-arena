"""Authored landing contract and compiled patrol scheduler; UE physics is separate."""
import copy
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import unittest
import campaign_landing as landing

ROOT=Path(__file__).resolve().parents[2]


class LandingSpaceTests(unittest.TestCase):
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
        with tempfile.TemporaryDirectory(prefix='sora-landing-space-') as directory:
            binary=Path(directory)/'landing-space'
            subprocess.run([compiler,'-std=c++20','-UNDEBUG','-Wall','-Wextra','-Werror',
                '-fsanitize=undefined','-fsanitize-trap=undefined',*flags,'-I',str(ROOT/'Source/SoraArena/Public'),
                str(ROOT/'scripts/unreal/landing_space_driver.cpp'),'-o',str(binary)],check=True,env=env)
            cls.native=json.loads(subprocess.check_output([str(binary)],text=True,env=env))

    @staticmethod
    def record(chapter,name='ch03.b02'):
        return next(r for r in chapter['space']['beats'] if r['beat']==name)

    def test_compiled_routes_match_generated_data(self):
        record=self.record(self.chapter)
        for i,route in enumerate(self.native['routes']):
            self.assertEqual(route['points'],record['patrols'][i])
            self.assertEqual(route['height'],record['landing']['altitudes_cm'][i])
            self.assertEqual(route['period'],record['landing']['periods_ms'][i])
        self.assertEqual(self.native['walls'],self.chapter['space']['zones'][record['zone']]['walls'])
        self.assertEqual(self.native['puddles'],[p['center'] for p in record['fieldcraft']['surfaces']])
        for key in ('canal_cm','water_z_cm','bed_z_cm','bridge_cm'):
            self.assertEqual(self.native[key],record['landing'][key])

    def test_authored_dimensions_and_timing(self):
        r=self.record(self.chapter);self.assertTrue(landing.landing_valid(self.chapter))
        self.assertEqual(r['landing']['yard_cm'],[-12000,-2800,-7600,-1200])
        self.assertEqual(r['landing']['periods_ms'],[40000,30000])
        self.assertEqual(r['landing']['altitudes_cm'],[500,400])
        self.assertEqual(r['patrols'][1],[[-11800,-2700],[-7800,-2700]])
        self.assertEqual(r['entry'],[-11300,-2700,0])
        self.assertEqual(r['exit'],{'center':[-7820,-850],'size':[360,300]})

    def test_yard_route_crosses_twice_with_opposite_lobes(self):
        route=self.record(self.chapter)['patrols'][0]
        self.assertEqual([i for i,p in enumerate(route) if p==[-10200,-2000]],[0,8])
        def area(points):
            return sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(points,points[1:]+points[:1]))
        self.assertLess(area(route[:9])*area(route[8:]+route[:1]),0)
        self.assertEqual([min(p[0] for p in route),max(p[0] for p in route)],[-11400,-9000])
        self.assertEqual([min(p[1] for p in route),max(p[1] for p in route)],[-2500,-1500])

    def test_changed_route_contracts_are_rejected(self):
        for beat in ('ch03.b01','ch03.b02'):
            for field,value in [('periods_ms',[39000,30000]),('altitudes_cm',[500,500]),
                                ('figure_eight',False),('canal_ping_pong',False),('extra',True),
                                ('water_z_cm',0),('bed_z_cm',-500),('bridge_cm',[-16000,200]),
                                ('canal_cm',[-22000,-3400,-7600,-2800])]:
                with self.subTest(beat=beat,field=field):
                    c=copy.deepcopy(self.chapter);self.record(c,beat)['landing'][field]=value
                    self.assertFalse(landing.landing_valid(c))
            c=copy.deepcopy(self.chapter);self.record(c,beat)['patrols'][0][0][0]+=1
            self.assertFalse(landing.landing_valid(c))

    def test_geometry_and_fieldcraft_mutations_are_rejected(self):
        mutations=[lambda r,z:z['walls'][2].__setitem__(4,0),lambda r,z:z.__setitem__('wall_cm',0),
            lambda r,z:z['cover'].pop(),lambda r,z:r['volumes'][1]['size'].__setitem__(0,1),
            lambda r,z:r['fieldcraft']['lamps'][0].__setitem__('hold_ms',1),
            lambda r,z:r['fieldcraft']['lamps'][1].__setitem__('relight_ms',100),
            lambda r,z:r['fieldcraft']['surfaces'][0].__setitem__('step_permille',1000),
            lambda r,z:r['fieldcraft']['surfaces'][1].__setitem__('crouch_permille',1000),
            lambda r,z:r['fieldcraft']['surfaces'][2].__setitem__('size',[1,1])]
        for i,mutate in enumerate(mutations):
            with self.subTest(mutation=i):
                c=copy.deepcopy(self.chapter);r=self.record(c);mutate(r,c['space']['zones'][r['zone']])
                self.assertFalse(landing.landing_valid(c))

    def test_landing_cannot_bind_another_beat_or_chapter(self):
        c=copy.deepcopy(self.chapter);self.record(c,'ch03.b03')['landing']=landing.contract()
        self.assertFalse(landing.landing_valid(c))
        for path in sorted((ROOT/'Content/Data/campaign').glob('chapter_*.json')):
            if path.name=='chapter_03.json':continue
            c=json.loads(path.read_text());self.assertTrue(landing.landing_valid(c))
            c['space']['beats'][0]['landing']=landing.contract()
            self.assertFalse(landing.landing_valid(c))

    def test_canal_and_bridge_have_authored_clearances(self):
        r=self.record(self.chapter)['landing']
        self.assertEqual(r['canal_cm'],[-22000,-3800,-7600,-2800])
        self.assertEqual(r['canal_cm'][3]-r['canal_cm'][1],1000)
        self.assertEqual(-r['water_z_cm'],160)
        self.assertEqual(r['bridge_cm'],[-16000,240])
        # Forty-centimetre wading is an implementation choice, not a source
        # requirement. It keeps the sixth step reachable with a 45 cm step.
        self.assertGreater(r['water_z_cm']-r['bed_z_cm'],0)
        self.assertLessEqual(r['water_z_cm']-r['bed_z_cm'],45)

    def test_opening_camera_crosses_below_bridge(self):
        shot=self.record(self.chapter,'ch03.b01')['camera']
        start,end=shot[:3],shot[3:6];r=self.record(self.chapter)['landing']
        x,clearance=r['bridge_cm'];fraction=(x-start[0])/(end[0]-start[0])
        self.assertGreater(fraction,0);self.assertLess(fraction,1)
        z=start[2]+fraction*(end[2]-start[2]);y=start[1]+fraction*(end[1]-start[1])
        self.assertLess(z+10,r['water_z_cm']+clearance)
        self.assertGreater(z-10,r['water_z_cm'])
        self.assertTrue(r['canal_cm'][1]+10<y<r['canal_cm'][3]-10)
        c=copy.deepcopy(self.chapter);self.record(c,'ch03.b01')['camera'][2]=300
        self.assertFalse(landing.landing_valid(c))


if __name__=='__main__':unittest.main()
