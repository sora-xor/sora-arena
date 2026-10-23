"""Optional wood discovery, physical choices and the separate arrow-only ledger."""
import copy
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from campaign_wood import wood_valid

ROOT = Path(__file__).resolve().parents[2]


class WoodTests(unittest.TestCase):
    def setUp(self):
        self.chapter = json.loads((ROOT / "Content/Data/campaign/chapter_01.json").read_text())
        self.wood = self.chapter["space"]["wood"]

    def test_authored_locations_exit_and_independent_required_route(self):
        self.assertTrue(wood_valid(self.chapter))
        b = self.chapter["beats"]
        self.assertEqual(b[7]["requires"], ["ch01.b07"])
        self.assertEqual(b[8]["requires"], ["ch01.b07"])
        self.assertEqual(b[7]["params"]["rewards"], ["ch01.c01", "ch01.c02"])
        self.assertEqual(b[7]["ext"]["complete"], {"volume_enter":"vol_ch01_wood_exit"})
        self.assertEqual(b[7]["params"]["exit_hint_after_s"], 180)
        # Preserve the authored polyline even though its prose says ~170 m.
        distance = sum(math.dist(a,b) for a,b in zip(self.wood["trail"],self.wood["trail"][1:]))
        self.assertEqual(round(distance), 14292)
        self.assertEqual(self.wood["trail_polyline_cm"], round(distance))
        self.assertEqual(math.dist(self.wood["pois"][1]["at"]+[150],self.wood["naruko"]), 4500)
        self.assertEqual(self.chapter["space"]["beats"][7]["cache"], None)

    def test_malformed_and_disconnected_contracts_are_rejected(self):
        for field in ("distance_cm","face_cm","entry","naruko","trail","pois","arrival","bridge"):
            for value in (True,False,None,"4500",{},0):
                c=copy.deepcopy(self.chapter);c["space"]["wood"][field]=value
                with self.subTest(field=field,value=value): self.assertFalse(wood_valid(c))
        for field in ("entry","arrival","naruko","face_cm"):
            for value in (True,1.5,"3",None):
                c=copy.deepcopy(self.chapter);c["space"]["wood"][field][0]=value
                self.assertFalse(wood_valid(c))
        for field in ("approach","trail","terrace","bridge"):
            c=copy.deepcopy(self.chapter);c["space"]["wood"][field][-1][0]+=1
            self.assertFalse(wood_valid(c))
        for i in range(4):
            c=copy.deepcopy(self.chapter);c["space"]["wood"]["pois"][i]["at"][1]+=1
            self.assertFalse(wood_valid(c))
        for mut in (lambda c:c["beats"][8].update(requires=["ch01.b08"]),
                    lambda c:c["beats"][7]["task"].update(goal="cache"),
                    lambda c:c["beats"][7]["params"]["pois"][0].update(collectible="ch01.c02"),
                    lambda c:c["beats"][7]["ext"]["challenge"].update(distance_m=True)):
            c=copy.deepcopy(self.chapter);mut(c);self.assertFalse(wood_valid(c))

    def test_real_door_clearance_and_separate_terrace(self):
        zones=self.chapter["space"]["zones"]
        wood=zones[self.chapter["space"]["beats"][7]["zone"]]["rect"]
        # A standing capsule can traverse every continuous route, including
        # the opened range/smithy walls, without collision with a wall/cover.
        blockers=[b for z in zones for b in z["walls"]+z["cover"]]
        for route in ("approach","terrace","bridge","trail"):
            for a,b in zip(self.wood[route],self.wood[route][1:]):
                n=max(1,math.ceil(math.dist(a,b)/20))
                for i in range(n+1):
                    p=[a[k]+(b[k]-a[k])*i/n for k in range(2)]
                    for x,y,w,h,_ in blockers:
                        self.assertFalse(abs(p[0]-x)<w/2+34 and abs(p[1]-y)<h/2+34,(route,p,[x,y,w,h]))
                    if route=="terrace":
                        self.assertFalse(wood[0]-34<p[0]<wood[2]+34 and wood[1]-34<p[1]<wood[3]+34)
        # Clapper is across a real floorless gap, not on the wood floor or
        # anywhere on the terrace where Interact might become a substitute.
        target=self.wood["naruko"]
        self.assertLess(target[1],wood[1]-3000)
        for p in self.wood["terrace"]:
            self.assertGreater(math.dist(p,target[:2]),3000)
        # Each discovery's 190 cm reach remains independent of every other.
        for i,a in enumerate(self.wood["pois"]):
            for b in self.wood["pois"][i+1:]: self.assertGreater(math.dist(a["at"],b["at"]),380)

    def test_native_ledger_and_junction_validation(self):
        source=r'''
#include "SoraWoodRules.h"
#include <cassert>
using namespace SoraWoodRules;
int main() {
    for(int mask=-64;mask<128;++mask) for(unsigned items=0;items<64;++items) {
        const bool expected=mask>=0&&mask<=31&&(!(mask&1)||(items&1))&&(!(mask&4)||(items&2));
        assert(LedgerValid(mask,items)==expected);
    }
    for(int first=0;first<Count;++first) {
        int mask=0; assert(Record(mask,first)); assert(mask==Bit(first));
        const int loaded=mask; // Tagged save round-trip retains each bit.
        for(int retry=0;retry<10;++retry) assert(!Record(mask,first)&&mask==loaded);
        for(int next=0;next<Count;++next) if(next!=first) assert(Record(mask,next));
        assert(mask==All); assert(!Record(mask,-1)&&!Record(mask,Count));
        mask=0; assert(Valid(mask)); // New Campaign, not checkpoint retry.
    }
    for(int chapter=0;chapter<8;++chapter) for(int beat=-1;beat<20;++beat) for(unsigned done=0;done<1024;++done) {
        assert(JunctionValid(false,chapter,beat,done)); // Legacy saves.
        assert(JunctionValid(true,chapter,beat,done)==(chapter==0&&beat==8&&done==127));
    }
}
'''
        compiler=os.environ.get("CXX") or shutil.which("clang++") or shutil.which("c++")
        self.assertIsNotNone(compiler)
        with tempfile.TemporaryDirectory() as d:
            cpp,binary=Path(d)/"wood.cpp",Path(d)/"wood"
            cpp.write_text(source)
            subprocess.run([compiler,"-std=c++17","-UNDEBUG","-Wall","-Werror","-I",
                            str(ROOT/"Source/SoraArena/Public"),str(cpp),"-o",str(binary)],check=True,capture_output=True,text=True)
            r=subprocess.run([str(binary)],capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)


if __name__=="__main__": unittest.main()
