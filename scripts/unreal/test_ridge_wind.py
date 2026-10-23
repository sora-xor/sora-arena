"""Authored wind clock, guarded external displacement and real ridge contract."""
from copy import deepcopy
from campaign_ridge import wind_valid
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]

class RidgeTests(unittest.TestCase):
    def test_generated_contract_preserves_authored_space_waves_and_wind(self):
        c=json.loads((ROOT/'Content/Data/campaign/chapter_07.json').read_text())
        w=c['ext']['chapter_systems']['ridge_wind']
        for index in (7,8,9):
            r=c['space']['beats'][index]; spec=r['wind'];z=c['space']['zones'][r['zone']]
            self.assertEqual(spec['base_mps'],w['base_mps'])
            self.assertEqual(spec['gust_mps'],w['gust_mps'])
            self.assertEqual(spec['gust_schedule_ms'],[n*1000 for n in w['gust_schedule_s']])
            self.assertEqual(spec['warning_ms'],w['gust_warn_ms'])
            self.assertEqual(spec['hold_ms'],w['gust_hold_s']*1000)
            self.assertEqual(spec['push_cm_s'],list(w['push_cm_s'].values()))
            self.assertEqual(spec['acceleration_cm_s2_per_mps'],w['projectile_drift']['lateral_accel_mps2_per_mps']*100)
            self.assertEqual(z['walls'],[])
            self.assertEqual(z['cover'],[])
            self.assertEqual(z['rect'][2]-z['rect'][0],18000 if index==9 else 8000)
            self.assertEqual(z['rect'][3]-z['rect'][1],2400 if index==9 else 4500)
        r=c['space']['beats'][9]; x=r['wind']['origin'][0]
        self.assertEqual(r['entry'],[x+200,0,0]);self.assertEqual(r['exit']['center'],[x+17800,0])
        self.assertEqual(r['exit']['floor_cm'],-198)
        self.assertEqual([v['center'][0]-x for v in r['volumes']],[9000,15000])
        self.assertEqual([v['floor_cm'] for v in r['volumes']],[-100,-167])
        self.assertEqual(c['beats'][9]['ext']['fall_respawn'],{'to':'last_brace_anchor','hp_cost':25,'max_per_checkpoint':3,'then':'checkpoint'})

    def test_rejects_malformed_or_repurposed_wind_contract(self):
        c=json.loads((ROOT/'Content/Data/campaign/chapter_07.json').read_text())
        self.assertTrue(wind_valid(c))
        for key,value in [('base_mps',True),('base_mps','8'),('gust_mps',8),('kind',None),
                          ('gust_schedule_ms',[11000,9000,14000,10000,'12000']),('push_cm_s',[120,60,False,0]),
                          ('warning_ms',0),('hold_ms',3500),('fall_cost',0),('recoveries',4),('origin',[True,0])]:
            bad=deepcopy(c);bad['space']['beats'][9]['wind'][key]=value
            self.assertFalse(wind_valid(bad),(key,value))
        bad=deepcopy(c);bad['space']['beats'][7].pop('wind');self.assertFalse(wind_valid(bad))
        bad=deepcopy(c);bad['space']['beats'][0]['wind']=deepcopy(bad['space']['beats'][9]['wind']);self.assertFalse(wind_valid(bad))
        bad=deepcopy(c);z=bad['space']['zones'][bad['space']['beats'][9]['zone']];z['rect'][2]-=10000;self.assertFalse(wind_valid(bad))

    def test_production_clock_geometry_and_external_guard(self):
        source=r'''#include "SoraRidgeRules.h"
#include <cassert>
#include <initializer_list>
#include <cmath>
using namespace SoraRidgeRules;
int main(){
 const int onset[]={11000,20000,34000,44000,56000,67000};
 for(int t:onset){assert(!At(t-1001).Warning);assert(At(t-1000).Warning);assert(At(t-1).Warning);
 assert(!At(t).Warning&&At(t).Gust&&At(t).Speed==18&&At(t).GustAgeMs==0);
 assert(At(t+2499).Gust);assert(!At(t+2500).Gust&&At(t+2500).Speed==8);}
 for(int step:{1,7,16,33,100,500}){int warnings=0,serial=0;for(int t=0;t<112000;t+=step){auto w=At(t);if(w.Warning&&w.Serial!=serial){++warnings;serial=w.Serial;}}assert(warnings==10);}
 assert(Height(0)==0&&Height(18000)==-200);assert(CrownHalf(0)*2==600&&CrownHalf(9000)*2==1400);
 for(int x:{300,6300,11700,12300,17700}){const double h=CrownHalf(x);assert(std::abs((Height(x,h)-Height(x,h+400))/400-std::tan(20*3.141592653589793/180))<1e-9);
 for(double y=-h-400;y<=h+400;y+=10){double next=y;for(int f=0;f<6000;++f)next+=GuardedPush(x,next,44,2);assert(next<=h+400-44||y>h+400-44);assert(next>=y);}}
 assert(Push(false,false,false)==120&&Push(true,false,false)==60&&Push(false,true,false)==0&&Push(false,false,true)==0);
 assert(Acceleration(8)==280&&Acceleration(18)==630);
 for(int x:{4500,5000,5500,9500,10000,10500,13500,14000,14500}){assert(Gap(x,1));assert(!Gap(x,-1));}
 for(int n=0;n<62;++n)assert(Cable(n)==!Gap(n/2*600,n%2?1:-1));
 // A deliberate 100 cm step is not put through GuardedPush. Only the wind
 // at a supported lip is clamped; there is no universal position clamp.
 assert(GuardedPush(3000,656,44,120)==0);assert(!Deck(3000,756));
 // Reference arrow flight at 65 m/s and 30 m: ~.30 m / .67 m drift.
 const double t=3000./6500.;assert(std::abs(.5*Acceleration(8)*t*t-29.822485)<1e-5);
 assert(std::abs(.5*Acceleration(18)*t*t-67.100592)<1e-5);
}'''
        compiler=os.environ.get('CXX') or shutil.which('clang++') or shutil.which('c++')
        self.assertIsNotNone(compiler)
        with tempfile.TemporaryDirectory() as d:
            cpp=Path(d)/'wind.cpp';cpp.write_text(source); binary=Path(d)/'wind'
            subprocess.run([compiler,'-std=c++17','-I',str(ROOT/'Source/SoraArena/Public'),str(cpp),'-o',str(binary)],check=True,capture_output=True,text=True)
            subprocess.run([str(binary)],check=True,capture_output=True,text=True)

if __name__=='__main__':unittest.main()
