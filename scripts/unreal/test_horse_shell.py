"""Actual clock rules and strict catalog binding; swept-world cases run in UE."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from campaign_horse_shell import horse_shell_valid

ROOT = Path(__file__).resolve().parents[2]


class HorseShellTests(unittest.TestCase):
    def setUp(self):
        self.chapter = json.loads((ROOT/'Content/Data/campaign/chapter_02.json').read_text())
        self.enemies = json.loads((ROOT/'Content/Data/enemies.json').read_text())

    def test_current_contract(self):
        self.assertTrue(horse_shell_valid(self.chapter, self.enemies))
        self.assertEqual(self.chapter['space']['beats'][5]['horse_shell']['warning_ms'], 1400)

    def test_rejects_missing_foreign_reordered_and_typed_contract_drift(self):
        row = self.chapter['space']['beats'][5]['horse_shell']
        for key in row:
            for value in (None, False, 0, '1400', [], {}, 1400.0):
                c=copy.deepcopy(self.chapter); c['space']['beats'][5]['horse_shell'][key]=value
                with self.subTest(key=key,value=value): self.assertFalse(horse_shell_valid(c,self.enemies))
        for mutate in (lambda c:c['space']['beats'][5].pop('horse_shell'),
                       lambda c:c['space']['beats'][4].update(horse_shell=row),
                       lambda c:c['space']['beats'][5]['horse_shell'].update(extra=0),
                       lambda c:c['space']['beats'].reverse(),
                       lambda c:c['space']['beats'].pop(),
                       lambda c:c['beats'][5]['task']['waves'][1]['members'][1].update(type='marksman')):
            c=copy.deepcopy(self.chapter); mutate(c); self.assertFalse(horse_shell_valid(c,self.enemies))

    def test_real_shared_projectile_catalog_drift_is_not_silently_overridden(self):
        for key in ('id','kind','damage','radius_cm','flight_ms','arming_cm','range_cm'):
            for value in (None, False, 0, '35', [], 35.0):
                e=copy.deepcopy(self.enemies)
                next(k for k in e['archetypes'] if k['id']=='grenadier')['attacks'][0][key]=value
                with self.subTest(key=key,value=value): self.assertFalse(horse_shell_valid(self.chapter,e))

    def test_actual_cpp_warning_cadence_pause_interruption_and_late_frame(self):
        code=r'''
#include "SoraHorseShellRules.h"
#include <cassert>
#include <initializer_list>
namespace R=SoraHorseShellRules;
int main() {
    static_assert(R::WarningMs==1400&&R::IntervalMs==6000&&R::FlightMs==1400);
    static_assert(R::Damage==35&&R::RadiusCm==300&&R::ArmingCm==200);
    R::FState s;
    assert(R::Begin(s)&&!R::Begin(s));
    R::Advance(s,1399);assert(!R::Release(s));
    R::Advance(s,0);R::Advance(s,-10);assert(s.ClockMs==1399&&!R::Release(s));
    R::Advance(s,1);assert(R::Release(s)&&s.Releases==1&&!R::Release(s));
    R::Advance(s,4599);assert(!R::Begin(s));
    R::Advance(s,1);assert(R::Begin(s));
    R::Advance(s,1399);assert(!R::Release(s));
    R::Advance(s,1);assert(R::Release(s)&&s.ClockMs==7400&&s.Releases==2);
    // Any interrupted warning must earn a fresh complete visible warning.
    for(int stop:{0,1,700,1399}) {
        s={};assert(R::Begin(s));R::Advance(s,stop);R::Cancel(s);
        R::Advance(s,6000);assert(!R::Release(s)&&s.Releases==0);
        assert(R::Begin(s));R::Advance(s,1399);assert(!R::Release(s));
        R::Advance(s,1);assert(R::Release(s)&&s.Releases==1);
    }
    // Cancelling the next warning cannot shorten the preceding release interval.
    s={};R::Begin(s);R::Advance(s,1400);R::Release(s);R::Advance(s,4600);
    R::Begin(s);R::Advance(s,500);R::Cancel(s);assert(R::Begin(s));
    R::Advance(s,1399);assert(!R::Release(s));R::Advance(s,1);assert(R::Release(s)&&s.ClockMs==7900);
    for(int step:{1,7,16,20,33,250,25000}) {
        s={};int released=0;long long previous=-1;
        for(int tick=0;tick<20000&&released<4;++tick) {
            if(R::CanBegin(s)) R::Begin(s);
            R::Advance(s,step);
            if(R::Release(s)) {
                assert(s.ClockMs-s.WarningStartedMs>=1400);
                assert(previous<0||s.ClockMs-previous>=6000);
                previous=s.ClockMs;++released;assert(!R::Release(s));
            }
        }
        assert(released==4&&s.Releases==4);
    }
    s={};assert(s.Releases==0&&R::CanBegin(s)); // A new session is canonical.
}
'''
        with tempfile.TemporaryDirectory(prefix='sora-horse-shell-') as directory:
            source,binary=Path(directory)/'clock.cpp',Path(directory)/'clock'
            source.write_text(code)
            subprocess.run(['c++','-std=c++17','-UNDEBUG','-Wall','-Wextra','-Werror',
                '-fsanitize=undefined','-fsanitize-trap=undefined','-I',str(ROOT/'Source/SoraArena/Public'),
                str(source),'-o',str(binary)],check=True)
            subprocess.run([str(binary)],check=True)


if __name__=='__main__': unittest.main()
