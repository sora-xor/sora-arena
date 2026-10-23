"""Exact chapter-five phrase/pick contracts; other manufacture stays unchanged."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from build_campaign_data import normalize_task, BuildError
from validate_campaign import check_rhythm_steps, CampaignError
ROOT=Path(__file__).resolve().parents[2]
class RhythmDataTests(unittest.TestCase):
    def setUp(self):
        self.beats=json.loads((ROOT/"Content/Data/campaign/chapter_05.json").read_text())["beats"]
    def test_exact_phrase_and_pick_units(self):
        for index,count,strikes,hits,ms,tolerance in ((7,4,8,6,600,90),(10,24,1,1,750,120)):
            beat=self.beats[index]
            self.assertEqual(normalize_task(beat),beat["task"])
            step=beat["task"]["steps"][1]
            self.assertEqual((step["count"],step["phrase_strikes"],step["phrase_pass"],step["beat_ms"],step["tolerance_ms"]),(count,strikes,hits,ms,tolerance))
    def test_malformed_phrase_fails_closed(self):
        for key,value in (("strikes",6),("pass_ratio",1),("cue_to_strike_ms",700),("cue","silent")):
            beat=deepcopy(self.beats[7]);beat["ext"]["hammer_rhythm_phrase"][key]=value
            with self.subTest(key=key),self.assertRaises(BuildError): normalize_task(beat)
        for index in (7,10):
            for key,value in (("beat_ms",0),("tolerance_ms",1)):
                beat=deepcopy(self.beats[index]);beat["params"]["manufacture"]["steps"][1]["timing"][key]=value
                with self.subTest(index=index,key=key),self.assertRaises(BuildError):normalize_task(beat)
    def test_normalized_contract_cannot_drop_phrase_rules(self):
        for key,value in (("phrase_strikes",6),("phrase_pass",1),("phrase_strikes",0),("count",32)):
            beat=deepcopy(self.beats[7]);beat["task"]["steps"][1][key]=value
            with self.subTest(key=key,value=value),self.assertRaises(CampaignError):check_rhythm_steps(beat)
    def test_other_chapters_keep_ordinary_manufacturing(self):
        for path in (ROOT/"Content/Data/campaign").glob("chapter_*.json"):
            for beat in json.loads(path.read_text())["beats"]:
                for step in beat["task"]["steps"]:
                    if beat["id"] not in ("ch05.b08","ch05.b11"):
                        self.assertEqual((step["phrase_strikes"],step["phrase_pass"]),(0,0))
if __name__=="__main__": unittest.main()
