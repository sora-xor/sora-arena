"""Host contract/time tests. Combat collision, input and AI require the UE fixtures."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from campaign_foundry_defense import foundry_valid, contract, TUBS, CREW

ROOT = Path(__file__).resolve().parents[2]

class FoundryDefenseTests(unittest.TestCase):
    def setUp(self):
        self.chapter = json.loads((ROOT/'Content/Data/campaign/chapter_05.json').read_text())
        self.beat = self.chapter['beats'][6]
        self.record = self.chapter['space']['beats'][6]

    def test_authored_contract_and_existing_bellows_are_distinct(self):
        self.assertTrue(foundry_valid(self.chapter))
        row = self.record['foundry_defense']
        self.assertEqual([r['id'] for r in row['tubs']], TUBS)
        self.assertEqual([r['id'] for r in row['crew']], CREW)
        self.assertEqual([r['index'] for r in self.record['fieldcraft']['nets']['quarry']], [1, 2])
        self.assertEqual(self.chapter['space']['beats'][5]['fieldcraft']['nets']['quarry'][0]['index'], 0)
        self.assertNotIn('foundry_defense', self.chapter['space']['beats'][5])
        self.assertEqual(self.beat['task']['duration_ms'], 180000)
        self.assertTrue(row['provisional_placement'])

    def test_authored_values_are_typed_and_not_silently_reinterpreted(self):
        paths = [('params','defend','repair_interact','uses_each'), ('params','defend','repair_interact','hold_s'),
                 ('params','defend','repair_interact','heal'), ('params','defend','duration_s'),
                 ('ext','kozo','downable'), ('ext','kozo','revive_s'), ('ext','kozo','fail_after_down_s'),
                 ('ext','grenadier_target_priority'), ('ext','drone_behavior')]
        for path in paths:
            for wrong in (None, 1.0, True, False, '3', [], 0):
                b = copy.deepcopy(self.beat); p = b
                for key in path[:-1]: p = p[key]
                if type(p[path[-1]]) is type(wrong) and p[path[-1]] == wrong: continue
                p[path[-1]] = wrong
                with self.subTest(path=path, wrong=wrong):
                    with self.assertRaises((ValueError, TypeError)): contract(b, self.record)

    def test_missing_or_corrupted_runtime_contract_is_rejected(self):
        for field in ('furnace_target','kozo_target','repair_ms','repair_hp','revive_ms','down_limit_ms','crew_drain_hp_s'):
            for wrong in (None, True, False, '150', [], 0, 1.5):
                expected = self.record['foundry_defense'][field]
                if type(expected) is type(wrong) and expected == wrong: continue
                c = copy.deepcopy(self.chapter); c['space']['beats'][6]['foundry_defense'][field] = wrong
                with self.subTest(field=field, wrong=wrong): self.assertFalse(foundry_valid(c))
        for mutation in (
            lambda r: r.pop('foundry_defense'),
            lambda r: r['foundry_defense']['tubs'].pop(),
            lambda r: r['foundry_defense']['crew'][0].update(at=[0,0]),
            lambda r: r['fieldcraft']['people'][0].update(target=0),
            lambda r: r['fieldcraft']['nets'].update(haul_ms=1000),
            lambda r: r['fieldcraft']['nets'].update(net_waves=[0]),
            lambda r: r['fieldcraft']['nets']['quarry'][0].update(index=0),
            lambda r: r.update(height_cm=100)):
            c = copy.deepcopy(self.chapter); mutation(c['space']['beats'][6]); self.assertFalse(foundry_valid(c))
        c = copy.deepcopy(self.chapter); c['space']['beats'][5]['foundry_defense'] = self.record['foundry_defense']
        self.assertFalse(foundry_valid(c))

    def test_actual_cpp_transactions_deadlines_and_fractional_pressure(self):
        code = r'''
#include "SoraFoundryDefenseRules.h"
#include <cassert>
using namespace SoraFoundryDefenseRules;
int main() {
    static_assert(FurnaceHp==1500&&KozoHp==300&&RepairHp==150&&RepairMs==3000);
    static_assert(ReviveMs==4000&&DownLimitMs==25000&&NetCutMs==1000&&DrainHpS==5);
    FState s;
    assert(!Begin(s,EWork::Repair,-1)&&!Begin(s,EWork::Repair,3));
    for(int i=0;i<3;++i) {
        assert(Begin(s,EWork::Repair,i));
        assert(Tick(s,2999,true,false,0).Repair==-1&&s.Used==((1u<<i)-1));
        assert(Tick(s,1,true,false,0).Repair==i&&s.Work==EWork::None);
        assert(!Available(s,i)&&!Begin(s,EWork::Repair,i));
    }
    assert(s.Used==7); Cancel(s); assert(s.Used==7); // Pause/release preserves supply.
    s={}; assert(Available(s,0)); // Retry/reload starts a new attempt.
    assert(Begin(s,EWork::Repair,0)); Tick(s,2500,true,false,0); Cancel(s);
    assert(Begin(s,EWork::Repair,0)); assert(Tick(s,500,true,false,0).Repair==-1&&s.HeldMs==500);
    Tick(s,4000,false,false,0); assert(s.Used==0&&s.HeldMs==0);
    assert(Begin(s,EWork::Repair,0)); Tick(s,2000,true,false,0);
    assert(Begin(s,EWork::Repair,1)&&s.HeldMs==0); // Changing target never transfers credit.
    s={}; Tick(s,21000,false,true,0); assert(Begin(s,EWork::Revive,0));
    assert(Tick(s,4000,true,true,0).Failed&&!Tick(s,1,true,true,0).Revive); // Tie fails.
    s={}; Tick(s,20999,false,true,0); Begin(s,EWork::Revive,0);
    auto r=Tick(s,5000,true,true,0); assert(r.Revive&&!r.Failed&&s.DownMs==0); // Completion precedes deadline.
    Tick(s,1,false,false,0); Tick(s,24999,false,true,0); assert(!s.Failed);
    assert(Tick(s,1,false,true,0).Failed); // Every subsequent down gets its own 25 s.
    s={}; Begin(s,EWork::Revive,0); Tick(s,3000,true,true,0); Tick(s,1,false,true,0);
    Begin(s,EWork::Revive,0); assert(!Tick(s,1000,true,true,0).Revive&&s.HeldMs==1000);
    s={}; int damage=0; for(int i=0;i<1000;++i) damage+=Tick(s,1,false,false,2).Drain;
    assert(damage==5&&s.DrainRemainder==0); // Two netted crew still cost 5 total HP/s.
    Tick(s,199,false,false,1); assert(s.DrainRemainder==995);
    assert(Tick(s,8000,false,false,0).Drain==0&&s.DrainRemainder==995);
    assert(Tick(s,1,false,false,1).Drain==1);
    s={}; Begin(s,EWork::Net,0); r=Tick(s,1500,true,false,1);
    assert(r.Net==0&&r.Drain==5); // Last net freed at 1 s, not end of a long frame.
    s={}; Begin(s,EWork::Net,0); r=Tick(s,1500,true,false,2);
    assert(r.Net==0&&r.Drain==7&&s.DrainRemainder==500); // Other net keeps pressure.
    s={}; Tick(s,24900,false,true,1); r=Tick(s,5000,false,true,1);
    assert(r.Failed&&r.Drain==1); // No pressure after the failure boundary.
}
'''
        compiler = os.environ.get('CXX') or shutil.which('clang++') or shutil.which('c++')
        self.assertIsNotNone(compiler)
        with tempfile.TemporaryDirectory(prefix='sora-foundry-') as directory:
            cpp, binary = Path(directory)/'foundry.cpp', Path(directory)/'foundry'
            cpp.write_text(code)
            subprocess.run([compiler,'-std=c++17','-UNDEBUG','-O2','-Wall','-Wextra','-Werror',
                            '-fsanitize=undefined','-fsanitize-trap=undefined','-I',str(ROOT/'Source/SoraArena/Public'),
                            str(cpp),'-o',str(binary)],check=True,capture_output=True,text=True)
            result = subprocess.run([str(binary)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

if __name__ == '__main__': unittest.main()
