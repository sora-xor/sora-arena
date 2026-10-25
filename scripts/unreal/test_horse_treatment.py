"""Treatment contract and actual state rules; physical/input checks run in UE."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from campaign_horse_treatment import contract, horse_treatment_valid

ROOT = Path(__file__).resolve().parents[2]


class HorseTreatmentTests(unittest.TestCase):
    def setUp(self):
        self.chapter = json.loads((ROOT/'Content/Data/campaign/chapter_02.json').read_text())
        self.beat = self.chapter['beats'][5]
        self.record = self.chapter['space']['beats'][5]

    def test_exact_authored_contract_and_two_actual_horses(self):
        self.assertTrue(horse_treatment_valid(self.chapter))
        self.assertEqual(self.record['horse_treatment'], dict(targets=['pack_horse_a', 'pack_horse_b'],
            hold_ms=2000, heal_hp=60, cooldown_ms=20000, cooldown_scope='per_horse'))
        self.assertEqual(self.record['kit']['targets'], ['horse', 'horse'])
        self.assertNotEqual(*self.record['targets'])
        self.assertEqual([t['hp'] for t in self.beat['task']['targets']], [400, 400])

    def test_invalid_authored_values_fail_closed(self):
        for key in ('kind', 'hold_s', 'heal', 'cooldown_s'):
            for value in (True, None, 0, '2', [], 1.5):
                b = copy.deepcopy(self.beat); b['params']['defend']['repair_interact'][key] = value
                with self.subTest(key=key, value=value), self.assertRaises((ValueError, TypeError)):
                    contract(b, self.record)
        for mutate in (lambda b: b['params']['defend']['targets'].reverse(),
                       lambda b: b['params']['defend'].update(duration_s=151),
                       lambda b: b['params']['defend'].update(fail_on_target_destroyed=False),
                       lambda b: b['task']['targets'][0].update(hp=401)):
            b = copy.deepcopy(self.beat); mutate(b)
            with self.assertRaises(ValueError): contract(b, self.record)

    def test_missing_wrongly_typed_or_foreign_runtime_contract_is_rejected(self):
        for key in ('hold_ms', 'heal_hp', 'cooldown_ms', 'cooldown_scope', 'targets'):
            for value in (None, True, 0, 60.0, '2000', []):
                c = copy.deepcopy(self.chapter); c['space']['beats'][5]['horse_treatment'][key] = value
                with self.subTest(key=key, value=value): self.assertFalse(horse_treatment_valid(c))
        for mutate in (lambda r: r.pop('horse_treatment'),
                       lambda r: r['horse_treatment'].update(extra=0),
                       lambda r: r['kit']['targets'].__setitem__(1, 'person'),
                       lambda r: r['targets'].pop()):
            c = copy.deepcopy(self.chapter); mutate(c['space']['beats'][5]); self.assertFalse(horse_treatment_valid(c))
        c = copy.deepcopy(self.chapter); c['space']['beats'][4]['horse_treatment'] = self.record['horse_treatment']
        self.assertFalse(horse_treatment_valid(c))

    def test_actual_cpp_hold_health_cooldown_and_interruption_rules(self):
        code = r'''
#include "SoraHorseTreatmentRules.h"
#include "SoraBeatRules.h"
#include <cassert>
#include <initializer_list>
namespace R=SoraHorseTreatmentRules;
int main() {
    static_assert(R::HoldMs==2000&&R::HealHp==60&&R::CooldownMs==20000);
    R::FState s;
    SoraBeatRules::FTask task; task.TargetCount=2; task.TargetHp[0]=task.TargetHp[1]=400;
    SoraBeatRules::FTaskState hp; hp.TargetHp[0]=100;hp.TargetHp[1]=390;
    assert(!R::Begin(s,-1,100)&&!R::Begin(s,2,100)&&!R::Begin(s,0,0)&&!R::Begin(s,0,400));
    for(int i=0;i<2;++i) {
        assert(R::Begin(s,i,hp.TargetHp[i]));
        assert(!R::Begin(s,1-i,hp.TargetHp[1-i])); // No retargeting or transferring partial work.
        assert(R::Tick(s,1999,true)==-1&&s.HeldMs==1999&&s.Cooldown[i]==0);
        assert(R::Tick(s,1,true)==i&&s.Cooldown[i]==20000&&s.Index==-1);
        assert(SoraBeatRules::RepairTarget(hp,task,i,R::HealHp));
        assert(hp.TargetHp[i]==(i==0?160:400)); // Actual shared health repair and cap.
        assert(!R::Begin(s,i,100));
    }
    assert(s.Cooldown[0]==18000&&s.Cooldown[1]==20000); // Per-horse clocks.
    R::Cancel(s); assert(s.Cooldown[0]==18000);
    assert(R::Tick(s,0,false)==-1&&s.Cooldown[0]==18000); // Pause earns nothing.
    R::Tick(s,17999,false); assert(!R::Eligible(s,0,100));
    R::Tick(s,1,false); assert(R::Eligible(s,0,100)&&!R::Eligible(s,1,100));
    R::Tick(s,2000,false); assert(R::Eligible(s,1,100));
    for(int i=0;i<2;++i) for(int stop:{0,1,999,1999}) {
        s={}; assert(R::Begin(s,i,100)); R::Tick(s,stop,true); R::Cancel(s);
        assert(s.HeldMs==0&&s.Index==-1&&s.Cooldown[i]==0);
        assert(R::Tick(s,3000,true)==-1); // A still-held key cannot restart after interruption.
        assert(R::Begin(s,i,100)&&R::Tick(s,1999,true)==-1&&R::Tick(s,1,true)==i);
    }
    for(int step:{1,7,16,33,250,2500}) {
        s={};R::Begin(s,0,100);int awards=0;
        for(int elapsed=0;elapsed<5000;elapsed+=step) awards+=R::Tick(s,step,true)>=0;
        assert(awards==1&&s.Index==-1);
    }
    s={};R::Begin(s,0,100);assert(R::Tick(s,2500,true)==0&&s.Cooldown[0]==19500);
    s={}; assert(R::Eligible(s,0,100)&&R::Eligible(s,1,100)&&s.HeldMs==0); // Canonical retry/load.
}
'''
        with tempfile.TemporaryDirectory(prefix='sora-treatment-') as directory:
            source, binary = Path(directory)/'treatment.cpp', Path(directory)/'treatment'
            source.write_text(code)
            subprocess.run(['c++','-std=c++17','-UNDEBUG','-Wall','-Wextra','-Werror',
                '-fsanitize=undefined','-fsanitize-trap=undefined','-I',str(ROOT/'Source/SoraArena/Public'),
                str(source),'-o',str(binary)],check=True)
            subprocess.run([str(binary)],check=True)


if __name__ == '__main__': unittest.main()
