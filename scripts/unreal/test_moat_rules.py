"""Host contract and production pure-rule checks; real collision is a UE gate."""
import copy
import json
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from campaign_moat import moat_valid

ROOT=Path(__file__).resolve().parents[2]

class MoatTests(unittest.TestCase):
    def setUp(self):
        self.chapter=json.loads((ROOT/'Content/Data/campaign/chapter_06.json').read_text())

    def test_authored_frame_and_depth(self):
        self.assertTrue(moat_valid(self.chapter))
        r=self.chapter['space']['beats'][1]
        self.assertEqual(r['moat']['gate_top_cm']-r['moat']['gate_bottom_cm'],60)
        self.assertEqual(r['moat']['bed_cm'],-240)
        self.assertEqual(r['moat']['gate_bed_cm'],-300)
        self.assertGreater(r['zone'],self.chapter['space']['beats'][2]['zone'])
        self.assertGreater(r['zone'],self.chapter['space']['beats'][13]['zone'])

    def test_absent_misplaced_mistyped_contract_rejected(self):
        for mutate in (lambda c:c['space']['beats'][1].pop('moat'),
                       lambda c:c['space']['beats'][2].update(moat=c['space']['beats'][1]['moat']),
                       lambda c:c['space']['beats'][1].update(zone=-1),
                       lambda c:c['space']['beats'][1]['moat'].update(extra=1),
                       lambda c:c['space']['beats'][1]['moat'].update(origin=[2**40,0])):
            c=copy.deepcopy(self.chapter);mutate(c);self.assertFalse(moat_valid(c))
        for key in ('bed_cm','gate_top_cm','float_clear_depth_cm','hitscan_clear_depth_cm','swim_half_height_cm'):
            for value in (True,None,'80',80.0,999):
                c=copy.deepcopy(self.chapter);c['space']['beats'][1]['moat'][key]=value
                self.assertFalse(moat_valid(c),(key,value))

    def test_route_sensor_and_support_mutations_rejected(self):
        edits=(lambda r:r['patrols'][2][0].__setitem__(1,90000),
               lambda r:r['exit']['center'].__setitem__(0,0),
               lambda r:r['fieldcraft']['water'].update(breath_ms=8001),
               lambda r:r['fieldcraft']['searchlights'][0].update(spot_cm=400),
               lambda r:r['fieldcraft']['allies'][0].update(detectable=True),
               lambda r:r['spawns'].pop())
        for edit in edits:
            c=copy.deepcopy(self.chapter);edit(c['space']['beats'][1]);self.assertFalse(moat_valid(c))

    def test_existing_climb_and_flood_records_unchanged(self):
        # Exact integration baseline: appending the moat must not move either
        # previously accepted physical space or any of its markers.
        expected={2: 'e8470d0989642190ba6e6622dbc63bb3fae447b833215cd15a6fbd84a14011de', 13: 'cb454b17736c53657a2fd790a0eb373886fbf4039baa73b1bb2690164c26633b'}
        for index,digest in expected.items():
            record=self.chapter['space']['beats'][index]
            value=[record,self.chapter['space']['zones'][record['zone']]]
            actual=hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
            self.assertEqual(actual,digest)

    def test_production_thresholds_gate_sweep_breath_and_bank_geometry(self):
        compiler=os.environ.get('CXX') or shutil.which('clang++') or shutil.which('g++')
        self.assertIsNotNone(compiler)
        source=r'''
#include "SoraMoatRules.h"
#include "SoraFieldcraftRules.h"
#include <cassert>
#include <initializer_list>
#include <cmath>
int main(){using namespace SoraMoatRules;
 assert(!Submerged(-18)&&Submerged(-18.001));
 assert(!ClearsFloat(-98)&&ClearsFloat(-98.001));
 assert(!ExcludesHitscan(-118)&&ExcludesHitscan(-118.001));
 assert(GateFits(20800,-150));assert(!GateFits(20800,-150,34,44));
 assert(!GateFits(20627,-150));assert(!GateFits(20800,-147.99));
 assert(GateCrossed(20800,3599,-150,20800,3601,-150,2,1./60));
 assert(!GateCrossed(20800,3599,-150,20800,3800,-150,201,1./60));
 assert(!GateCrossed(20800,3599,-6,20800,3601,-6,2,1./60));
 assert(Floor(1000,1000)==-240&&Floor(20800,3400)==-300);
 const auto R=BankRamp();const double A=R.RollDegrees*std::acos(-1.)/180.;
 // UE positive roll maps local Y down and local Z toward positive Y.
 for(int Sign:{-1,1}) {const double Y=R.CenterY+Sign*R.Length*.5*std::cos(A)+20*std::sin(A);
 const double Z=R.CenterZ-Sign*R.Length*.5*std::sin(A)+20*std::cos(A);
 assert(std::abs(Y-(Sign<0?-400:0))<1e-9);assert(std::abs(Z-(Sign<0?100:-240))<1e-9);}
 using namespace SoraFieldcraftRules;const FWaterRules W={180,140,8000,3000,10};
 auto B=FullBreath(W);assert(Breathe(B,W,true,8000)==0);assert(Breathe(B,W,true,1000)==10);
 assert(Breathe(B,W,false,2999)==0&&B.BreathMs<8000);assert(Breathe(B,W,false,1)==0&&B.BreathMs==8000);
 // Gate approach (1.5m descent at70cm/s + 2.5m traversal at140cm/s)
 // fits the real8s breath window, with3s recovery possible on either side.
 assert((144./70.+250./140.)*1000<8000);
}
'''
        with tempfile.TemporaryDirectory(prefix='sora-moat-') as folder:
            p=Path(folder);(p/'test.cpp').write_text(source)
            subprocess.run([compiler,'-std=c++17','-Wall','-Wextra','-Werror','-Wshadow','-I',str(ROOT/'Source/SoraArena/Public'),str(p/'test.cpp'),'-o',str(p/'test')],check=True)
            subprocess.run([str(p/'test')],check=True)

if __name__=='__main__':unittest.main()
