"""Strict authored outro binding; navigation/contacts/pauses run in Unreal."""
import copy
import json
from pathlib import Path
import unittest
from campaign_horse_withdrawal import horse_withdrawal_valid, EVENT

ROOT = Path(__file__).resolve().parents[2]

class HorseWithdrawalTests(unittest.TestCase):
    def setUp(self):
        self.chapter=json.loads((ROOT/'Content/Data/campaign/chapter_02.json').read_text())

    def test_current_contract_and_other_chapters(self):
        for path in sorted((ROOT/'Content/Data/campaign').glob('chapter_*.json')):
            with self.subTest(path=path): self.assertTrue(horse_withdrawal_valid(json.loads(path.read_text())))

    def test_missing_foreign_extra_type_and_order_drift(self):
        row=self.chapter['space']['beats'][5]['horse_withdrawal']
        for key in row:
            for value in (None,False,0,'220',[],{},220.0):
                c=copy.deepcopy(self.chapter);c['space']['beats'][5]['horse_withdrawal'][key]=value
                with self.subTest(key=key,value=value):self.assertFalse(horse_withdrawal_valid(c))
        for mutate in (lambda c:c['space']['beats'][5].pop('horse_withdrawal'),
                       lambda c:c['space']['beats'][4].update(horse_withdrawal=row),
                       lambda c:c['space']['beats'][5]['horse_withdrawal'].update(extra=0),
                       lambda c:c['space']['beats'].reverse(),
                       lambda c:c['space']['beats'].pop(),
                       lambda c:c['beats'][5]['task'].update(duration_ms=150001),
                       lambda c:c['beats'][5]['ext']['withdrawal'].update(muster='sp_gate_leaves')):
            c=copy.deepcopy(self.chapter);mutate(c);self.assertFalse(horse_withdrawal_valid(c))

    def test_named_floor_and_actual_bark_binding_required(self):
        for mutate in (lambda c:next(p for p in c['layout']['points'] if p['id']=='ps_gate_yard_start').update(positions_cm=[[-3450,0,0]]),
                       lambda c:c['triggers'].extend([next(t for t in c['triggers'] if t['on']==EVENT)]),
                       lambda c:next(t for t in c['triggers'] if t['on']==EVENT).update(lines=[]),
                       lambda c:next(t for t in c['triggers'] if t['on']==EVENT).update(mode='blocking'),
                       lambda c:next(t for t in c['triggers'] if t['on']==EVENT).update(repeatable=True)):
            c=copy.deepcopy(self.chapter);mutate(c);self.assertFalse(horse_withdrawal_valid(c))

if __name__=='__main__':unittest.main()
