"""Gallery lore is optional, durable and independent of collectible rewards."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class GalleryRulesTests(unittest.TestCase):
    def test_authored_identities_dialogue_and_collectibles_are_unchanged(self):
        data = json.loads((ROOT / "Content/Data/campaign/chapter_08.json").read_text())
        beat = data["beats"][11]
        self.assertTrue(beat["optional"])
        self.assertFalse(beat["checkpoint"])
        self.assertEqual(beat["requires"], ["ch08.b11"])
        pois = {poi["id"]: poi for poi in beat["params"]["pois"]}
        self.assertEqual(len(pois), 6)
        self.assertEqual(pois["poi_child_toy"], {"id": "poi_child_toy", "kind": "lore"})
        self.assertEqual(pois["poi_covered_mon"]["interact"],
                         "tear the seizure label off the Nyaagyu 陣羽織")
        self.assertEqual([pois[name]["collectible"] for name in (
            "poi_washio_sword", "poi_tamakichi_mortar", "poi_scroll_case")],
            ["ch08.c03", "ch08.c04", "ch08.c05"])
        self.assertEqual(beat["params"]["rewards"], ["ch08.c03", "ch08.c04", "ch08.c05", "arrows_12"])
        # These lines must come from the authored event mapping, never a new
        # hard-coded paraphrase or an unrelated active b11 dialogue trigger.
        dialogue = data["lines"]
        self.assertTrue(any(line["id"] == "ch08.b12.nyaakoto.002" and
                            line["ja"] == "……子どもの張子に、三文か。" and
                            line["en"] == "…A child's paper toy. Three coppers."
                            for line in dialogue))
        self.assertTrue(any(row["on"] == "event:poi_child_toy" and
                            row["lines"] == ["ch08.b12.nyaakoto.002"]
                            for row in data["triggers"]))
        self.assertEqual(data["space"]["beats"][11]["height_cm"], 14200)
        self.assertEqual(data["space"]["beats"][11]["exit"]["floor_cm"], 16000)

    def test_native_lore_mask_and_actual_gallery_clearance(self):
        source = r'''
#include "SoraGalleryRules.h"
#include <cassert>
#include <cmath>
int main() {
    using namespace SoraGalleryRules;
    for(int highest=0;highest<8;++highest)
        for(int mask=-16;mask<32;++mask)
            assert(Valid(mask,highest)==(mask==0||(highest==7&&mask>0&&mask<=3)));
    for(int first=0;first<Count;++first) {
        int mask=0;
        assert(Record(mask,first)&&mask==Bit(first));
        for(int n=0;n<10;++n) assert(!Record(mask,first)&&mask==Bit(first));
        // The other object remains independent of discovery order.
        assert(Record(mask,1-first)&&mask==All);
        assert(!Record(mask,-1)&&!Record(mask,Count)&&mask==All);
        const int loaded=mask;
        assert(Valid(loaded,7)); // Also valid while replaying an earlier chapter.
        mask=0; // New Campaign explicitly discards optional discoveries.
        assert(Valid(mask,0));
    }
    // Runtime gallery is 1,000 x 4,000 cm, centre (800,0) relative to lift.
    // Proxies sit by the east edge, clear of the existing x=500..800 path,
    // cache at (800,-1400), and the north stair's 300 cm opening.
    constexpr double HalfPlinthX=60,HalfPlinthY=75,Capsule=34;
    for(int n=0;n<Count;++n) {
        assert(OffsetX+HalfPlinthX<500-16);
        assert(std::abs(OffsetY[n])+HalfPlinthY<2000-16);
        assert(OffsetX-HalfPlinthX>Capsule+2*19); // clearance from x=800
        const double cacheDistance=std::hypot(OffsetX,OffsetY[n]+1400);
        assert(cacheDistance>2*ReachCm); // one press never reaches cache + lore
        assert(OffsetX-190+Capsule<OffsetX-HalfPlinthX);
    }
    assert(std::abs(OffsetY[0]-OffsetY[1])>2*ReachCm);
}
'''
        compiler = os.environ.get("CXX") or shutil.which("clang++") or shutil.which("c++")
        self.assertIsNotNone(compiler, "Host C++ compiler is required")
        with tempfile.TemporaryDirectory() as tmp:
            cpp, binary = Path(tmp) / "gallery.cpp", Path(tmp) / "gallery"
            cpp.write_text(source)
            subprocess.run([compiler, "-std=c++17", "-I", str(ROOT / "Source/SoraArena/Public"),
                            str(cpp), "-o", str(binary)], check=True, capture_output=True, text=True)
            result = subprocess.run([str(binary)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
