"""Host contract/rules checks; swept UE collision and input need Flood* automation."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from campaign_flood import flood_valid

ROOT=Path(__file__).resolve().parents[2]

class FloodTests(unittest.TestCase):
    def setUp(self):
        self.chapter=json.loads((ROOT/'Content/Data/campaign/chapter_06.json').read_text())

    def test_authoring_preserves_hazard_and_adds_explicit_air_solution(self):
        self.assertTrue(flood_valid(self.chapter))
        beat=self.chapter['beats'][13]
        self.assertEqual(beat['ext']['hazard'],{'kind':'rising_water','from_cm':40,'to_cm':160,'over_s':150,'deep_volume':'vol_ankyo_deep'})
        self.assertEqual(beat['ext']['traversal']['dive_max_s'],8)
        self.assertEqual(beat['task']['goal'],'exit')
        self.assertEqual(beat['fail'],[{'on':'player_died','to':'checkpoint'}])
        f=self.chapter['space']['beats'][13]['flood']
        self.assertTrue(f['provisional_air_shaft'])
        # The authored 15 m is retained. Two 6.5 m submerged legs and a
        # 2 m shaft explicitly solve 1500/140 > 8, without changing breath.
        self.assertEqual(f['length_cm']-f['deep_start_cm'],1500)
        self.assertEqual(f['air_shaft_cm'],[8150,8350])
        self.assertGreater(1500/140,8)
        self.assertLess(650/140+2*180/180,8)

    def test_malformed_and_spatially_disconnected_contracts_fail(self):
        fields=('length_cm','width_cm','height_cm','deep_start_cm','deep_floor_cm','deep_roof_cm','from_cm','to_cm','rise_ms')
        for field in fields:
            for value in (True,False,None,'40',{},1.5,0):
                c=copy.deepcopy(self.chapter);c['space']['beats'][13]['flood'][field]=value
                with self.subTest(field=field,value=value): self.assertFalse(flood_valid(c))
        mutations=(lambda r:r.pop('flood'),lambda r:r['flood'].update(air_shaft_cm=[8000,8400]),
            lambda r:r['spawns'][0].__setitem__(0,1),lambda r:r['volumes'][2]['size'].__setitem__(1,300),
            lambda r:r['fieldcraft']['water'].update(dive_cm_s=63),lambda r:r['fieldcraft']['water'].update(breath_ms=11000),
            lambda r:r['fieldcraft']['allies'][1].update(detectable=True),lambda r:r['fieldcraft'].update(searchlights=[]),
            lambda r:r['exit'].update(floor_cm=0))
        for mutate in mutations:
            c=copy.deepcopy(self.chapter);mutate(c['space']['beats'][13]);self.assertFalse(flood_valid(c))
        c=copy.deepcopy(self.chapter);c['space']['beats'][2]['flood']=c['space']['beats'][13]['flood'];self.assertFalse(flood_valid(c))

    def test_actual_cpp_water_breath_and_route_rules(self):
        source=r'''
#include "SoraFloodRules.h"
#include <cassert>
#include <cmath>
#include <initializer_list>
#include <utility>
using namespace SoraFloodRules;
int main() {
    static_assert(Surface(-1)==40&&Surface(0)==40&&Surface(75000)==100&&Surface(150000)==160&&Surface(999999)==160);
    static_assert(Floor(7300)==0&&Floor(7400)==-100&&Floor(7500)==-200);
    static_assert(RoofedDeep(7800)&&!RoofedDeep(8250)&&RoofedDeep(8600));
    static_assert(Immersed(10,40)&&!Immersed(50,40));
    // Transform the actual production slab's upper corners using UE's roll
    // convention: its support surface must meet the existing moat and bank.
    const auto ramp=BankRamp();
    const double angle=ramp.RollDegrees*std::acos(-1.0)/180.0;
    const double sin=std::sin(angle),cos=std::cos(angle);
    const auto top=[&](double y) {
        return std::pair<double,double>{ramp.CenterY+y*cos+BankRampThickness*.5*sin,
            ramp.CenterZ-y*sin+BankRampThickness*.5*cos};
    };
    const auto water=top(ramp.Length*.5),bank=top(-ramp.Length*.5);
    assert(std::abs(water.first-BankWaterY)<1e-8&&std::abs(water.second-DeepFloor)<1e-8);
    assert(std::abs(bank.first-BankEdgeY)<1e-8&&std::abs(bank.second-BankTop)<1e-8);
    assert(ramp.RollDegrees>0&&ramp.RollDegrees<44.0);
    assert(cos>std::cos(44.0*std::acos(-1.0)/180.0));
    for(int dt:{8,16,17,33,50}) {
        FRoute r; float x=7499;
        for(;x<8250;) { float p=x;x+=140*dt/1000.f;Travel(r,p,x,0,true,x-p,dt); }
        assert(r.Stage==2&&!Ready(r));
        // Actual air in the shaft is permitted, but remaining underwater
        // there spends breath: location alone is never a breath reset.
        auto breath=SoraFieldcraftRules::FullBreath({180,140,8000,3000,10});
        SoraFieldcraftRules::Breathe(breath,{180,140,8000,3000,10},true,5000);
        assert(breath.BreathMs==3000);
        assert(SoraFieldcraftRules::Breathe(breath,{180,140,8000,3000,10},true,4000)==10);
        SoraFieldcraftRules::Breathe(breath,{180,140,8000,3000,10},false,2999);
        assert(breath.BreathMs<8000);
        SoraFieldcraftRules::Breathe(breath,{180,140,8000,3000,10},false,1);
        assert(breath.BreathMs==8000);
        for(;x<9010;) { float p=x;x+=140*dt/1000.f;Travel(r,p,x,0,true,x-p,dt); }
        assert(r.Stage==4&&!Ready(r));r.Gate=true;assert(Ready(r));
        Travel(r,9000,9500,0,true,500,dt);assert(r.Stage==0&&!Ready(r));
    }
    FRoute r;
    Travel(r,7490,7501,0,false,11,100);assert(r.Stage==0);
    Travel(r,7490,7501,0,true,11,100);assert(r.Stage==1);
    Travel(r,7501,7502,0,false,1,100);assert(r.Stage==0);
    Travel(r,7400,8200,0,true,800,17);assert(r.Stage==0);
    Travel(r,7490,7501,0,true,11,100);Travel(r,7501,7502,121,true,1,100);assert(r.Stage==0);
    Travel(r,7490,7501,0,true,11,100);Travel(r,7501,7490,0,true,11,100);assert(r.Stage==0);
}
'''
        compiler=os.environ.get('CXX') or shutil.which('clang++') or shutil.which('c++')
        self.assertIsNotNone(compiler)
        with tempfile.TemporaryDirectory(prefix='sora-flood-rules-') as d:
            cpp,binary=Path(d)/'flood.cpp',Path(d)/'flood';cpp.write_text(source)
            subprocess.run([compiler,'-std=c++17','-UNDEBUG','-O2','-Wall','-Werror','-fsanitize=undefined','-fsanitize-trap=undefined',
                '-I',str(ROOT/'Source/SoraArena/Public'),str(cpp),'-o',str(binary)],check=True,capture_output=True,text=True)
            result=subprocess.run([str(binary)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

if __name__=='__main__': unittest.main()
