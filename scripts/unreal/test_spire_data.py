"""Authored vertical encounter contract and a continuous walkable spiral."""
from copy import deepcopy
import json
import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
import unittest
from build_campaign_data import BuildError, fail
from campaign_spire import place_spire, route, LANDINGS, SIDES, SUBDIVISIONS
from campaign_space import Zone

ROOT = Path(__file__).resolve().parents[2]


class SpireDataTests(unittest.TestCase):
    def setUp(self):
        self.chapter = json.loads((ROOT/'Content/Data/campaign/chapter_08.json').read_text())
        self.record = self.chapter['space']['beats'][9]

    def test_continuous_ramp_and_floor_specific_wave_posts(self):
        s = self.record['spire']
        self.assertEqual((s['width_cm'],s['void_diameter_cm']),(400,1400))
        ramp = s['ramp']
        self.assertEqual(len(ramp),SIDES*SUBDIVISIONS+1)
        self.assertEqual(s['landing_nodes'],LANDINGS)
        self.assertEqual([ramp[n][2] for n in LANDINGS],[0,900,1800,2700])
        total = 0
        for a,b in zip(ramp,ramp[1:]):
            run=math.dist(a[:2],b[:2]); total+=run
            self.assertGreater(b[2],a[2])
            self.assertLess((b[2]-a[2])/run,1/11.5)
            self.assertGreater((b[2]-a[2])/run,1/12.5)
            # Measure the actual polygon's inner edge; a metadata-only
            # diameter check missed the original 20 m aperture regression.
            ax,ay=a[0]-s['center'][0],a[1]-s['center'][1]
            dx,dy=b[0]-a[0],b[1]-a[1]
            apothem=abs(ax*dy-ay*dx)/run
            self.assertAlmostEqual(2*apothem-s['width_cm'],s['void_diameter_cm'],delta=2)
        self.assertAlmostEqual(total/2700,12,delta=.1)
        # A full winding leaves over 5 m between its floor surfaces.
        loop=6*SUBDIVISIONS
        for n in range(len(ramp)-loop):
            self.assertEqual(ramp[n+loop][:2],ramp[n][:2])
            self.assertGreaterEqual(ramp[n+loop][2]-ramp[n][2],522)
        self.assertEqual([p[2] for p in s['spawns']],[900]*5+[1800]*4+[2100]*4+[2700]*3)
        self.assertEqual([p[:2] for p in s['spawns']],self.record['spawns'])
        v = {v['event']:v for v in self.record['volumes']}
        self.assertEqual(v['volume_enter:vol_spire_L3']['floor_cm'],1800)
        self.assertEqual(v['volume_enter:vol_spire_L3']['center'],ramp[LANDINGS[2]][:2])
        self.assertEqual(self.record['exit']['floor_cm'],2700)
        lift=self.chapter['space']['beats'][10]
        self.assertEqual(s['center'],lift['anchor'])
        self.assertEqual(ramp[-1][2],lift['height_cm'])

    def test_native_geometry_matches_generated_route(self):
        compiler=os.environ.get('CXX') or shutil.which('clang++') or shutil.which('c++')
        self.assertIsNotNone(compiler, 'Host C++ compiler is required for geometry parity')
        source = r'''#include "SoraSpireRules.h"
#include <iostream>
int main() {
    for(int l=0;l<4;++l) std::cout<<SoraSpireRules::Landing(l)<<" ";
    std::cout<<"\n";
    for(int n=0;n<SoraSpireRules::NodeCount;++n) {
        const auto p=SoraSpireRules::Point(n);
        std::cout<<p.X<<" "<<p.Y<<" "<<p.Z<<"\n";
    }
}'''
        with tempfile.TemporaryDirectory() as tmp:
            cpp=Path(tmp)/'spire.cpp'; binary=Path(tmp)/'spire'
            cpp.write_text(source)
            subprocess.run([compiler,'-std=c++17','-I',str(ROOT/'Source/SoraArena/Public'),str(cpp),'-o',str(binary)],check=True,capture_output=True,text=True)
            rows=subprocess.check_output([str(binary)],text=True).splitlines()
        self.assertEqual([int(n) for n in rows[0].split()],LANDINGS)
        self.assertEqual([[int(n) for n in row.split()] for row in rows[1:]],route())

    def zones(self):
        return [Zone(z['id'],z['place'],z['style'],z['form'],z['rect'],z['wall_cm']) for z in self.chapter['space']['zones']]

    def test_gantry_rails_clear_incoming_and_outgoing_capsules(self):
        # Exercise the production inset and the full rail OBB, including its
        # longitudinal overlap. The original untrimmed L2 rail intersected
        # the outgoing ramp even though the gantry itself remained walkable.
        source = r'''#include "SoraSpireRules.h"
#include <algorithm>
#include <cassert>
#include <iostream>
using namespace SoraSpireRules;
double distance(FPoint p,FPoint a,FPoint b,int sign,double insetA,double insetB,double width=GantryWidthCm,double overlap=RailOverlapCm) {
    const double length=std::hypot(b.X-a.X,b.Y-a.Y);
    const double dx=(b.X-a.X)/length,dy=(b.Y-a.Y)/length;
    const double along=(p.X-a.X)*dx+(p.Y-a.Y)*dy;
    const double side=-(p.X-a.X)*dy+(p.Y-a.Y)*dx-sign*(width*.5-10);
    const double x=std::max({insetA-overlap*.5-along,along-(length-insetB+overlap*.5),0.0});
    const double y=std::max(std::abs(side)-10,0.0);
    return std::hypot(x,y);
}
int main() {
    bool originalObstructed=false;
    for(int level:{1,3}) {
        const int node=Landing(level); const auto a=Point(node);
        const FPoint b=level==1?FPoint{-a.X,-a.Y,a.Z}:FPoint{-300,0,a.Z};
        const double ia=GantryRailInset(b.X-a.X,b.Y-a.Y,LandingHalfCm);
        const double ib=GantryRailInset(b.X-a.X,b.Y-a.Y,level==1?MarksmanHalfCm:0);
        assert(ia+ib<std::hypot(b.X-a.X,b.Y-a.Y));
        for(int neighbour:{node-1,node+1}) {
            if(neighbour>=NodeCount) continue;
            const auto end=Point(neighbour);
            for(int n=0;n<=1000;++n) {
                const double t=n/1000.0;
                const FPoint p{a.X+(end.X-a.X)*t,a.Y+(end.Y-a.Y)*t,a.Z+(end.Z-a.Z)*t};
                for(int sign:{-1,1}) {
                    if(level==1&&distance(p,a,b,sign,0,0)<RouteRadiusCm) originalObstructed=true;
                    assert(distance(p,a,b,sign,ia,ib)>RouteRadiusCm);
                }
            }
        }
        // The opening retains the complete two-metre bridge path in both
        // directions and onto the far post / parked lift approach.
        for(int n=0;n<=1000;++n) {
            const double t=n/1000.0;
            const FPoint p{a.X+(b.X-a.X)*t,a.Y+(b.Y-a.Y)*t,a.Z};
            for(int sign:{-1,1}) assert(distance(p,a,b,sign,ia,ib)>RouteRadiusCm);
        }
    }
    assert(originalObstructed);
    const auto a=Point(ShortcutStart),b=Point(ShortcutEnd);
    for(int panel=0;panel<2;++panel) {
        const auto goal=AlarmApproach(panel);
        assert(goal.Z==1800);
        assert(std::abs(goal.X-a.X)<LandingHalfCm-RouteRadiusCm);
        assert(std::abs(goal.Y-a.Y)<WidthCm*.5-RouteRadiusCm-20);
        const auto rails=ShortcutPadRails(ShortcutStart);
        for(int n=0;n<=1000;++n) {
            const double t=n/1000.0;
            const FPoint p{a.X+(goal.X-a.X)*t,a.Y+(goal.Y-a.Y)*t,0};
            for(int r=0;r<rails.Count;++r)
                assert(distance(p,rails.Lines[r].A,rails.Lines[r].B,0,0,0,20,0)>RouteRadiusCm);
        }
    }
    const double chord=std::hypot(b.X-a.X,b.Y-a.Y);
    assert(ShortcutStart==Landing(2)&&ShortcutEnd<Landing(3));
    assert(IsAccessPad(ShortcutStart)&&IsAccessPad(ShortcutEnd));
    assert((b.Z-a.Z)/chord<.15); // ordinary walkable shortcut grade
    double spiral=0;
    for(int n=ShortcutStart+1;n<=ShortcutEnd;++n) {
        const auto p=Point(n-1),q=Point(n);
        spiral+=std::hypot(q.X-p.X,q.Y-p.Y);
    }
    assert(chord+200<spiral); // actually shortens the physical route
    const double inset=GantryRailInset(b.X-a.X,b.Y-a.Y,LandingHalfCm);
    assert(2*inset<chord);
    for(int node:{ShortcutStart,ShortcutEnd}) {
        const auto pad=Point(node);
        const auto guards=ShortcutPadRails(node);
        assert(guards.Count>0&&guards.Count<=16);
        // A square pad reaches beyond the nearest node on a diagonal.
        // Test both full adjacent ramp spans, with two Recast 19 cm cells
        // beyond the capsule radius, not only capsule fit at that node.
        for(int edge=node-1;edge<=node+2;++edge) {
            const auto from=Point(edge-1),to=Point(edge);
            for(int n=0;n<=1000;++n) {
                const double t=n/1000.0;
                const FPoint p{from.X+(to.X-from.X)*t,from.Y+(to.Y-from.Y)*t,0};
                for(int r=0;r<guards.Count;++r)
                    assert(distance(p,guards.Lines[r].A,guards.Lines[r].B,0,0,0,20,0)>RouteRadiusCm+38);
            }
        }
        for(int neighbour:{node-1,node+1,node==ShortcutStart?ShortcutEnd:ShortcutStart}) {
            const auto end=Point(neighbour);
            for(int n=0;n<=1000;++n) {
                const double t=n/1000.0;
                const FPoint p{pad.X+(end.X-pad.X)*t,pad.Y+(end.Y-pad.Y)*t,0};
                for(int r=0;r<guards.Count;++r)
                    assert(distance(p,guards.Lines[r].A,guards.Lines[r].B,0,0,0,20,0)>RouteRadiusCm);
            }
        }
        if(node==ShortcutEnd) {
            // Regression: this previously unguarded pad corner points into
            // the void, away from all three connected walking corridors.
            const FPoint outside{pad.X-350,pad.Y-300,0};
            bool stopped=false;
            for(int n=0;n<=1000;++n) {
                const double t=n/1000.0;
                const FPoint p{pad.X+(outside.X-pad.X)*t,pad.Y+(outside.Y-pad.Y)*t,0};
                for(int r=0;r<guards.Count;++r)
                    stopped|=distance(p,guards.Lines[r].A,guards.Lines[r].B,0,0,0,20,0)<RouteRadiusCm;
            }
            assert(stopped);
        }
        for(int neighbour:{node-1,node+1}) {
            const auto end=Point(neighbour);
            for(int n=0;n<=1000;++n) {
                const double t=n/1000.0;
                const FPoint p{pad.X+(end.X-pad.X)*t,pad.Y+(end.Y-pad.Y)*t,0};
                for(int sign:{-1,1}) assert(distance(p,a,b,sign,inset,inset)>RouteRadiusCm);
            }
        }
    }
    // The ramp's own rails must also admit the shortcut from either pad.
    // Limit to adjacent rails at the two endpoints: other windings have
    // over five metres of vertical separation.
    for(int n=0;n<=1000;++n) {
        const double t=n/1000.0;
        const FPoint p{a.X+(b.X-a.X)*t,a.Y+(b.Y-a.Y)*t,0};
        for(int node:{ShortcutStart,ShortcutEnd})
            for(int edge:{node,node+1}) {
                const auto r=Point(edge-1),s=Point(edge);
                for(int sign:{-1,1}) {
                    const double from=sign>0?InnerRailInset(edge-1):0;
                    const double to=sign>0?InnerRailInset(edge):0;
                    assert(distance(p,r,s,sign,from,to,WidthCm)>RouteRadiusCm);
                }
            }
    }
    std::cout<<"L2 and L4 incoming, outgoing and gantry capsule routes clear\n";
}'''
        compiler=os.environ.get('CXX') or shutil.which('clang++') or shutil.which('c++')
        self.assertIsNotNone(compiler, 'Host C++ compiler is required for collision geometry')
        with tempfile.TemporaryDirectory() as tmp:
            cpp=Path(tmp)/'clearance.cpp'; binary=Path(tmp)/'clearance'
            cpp.write_text(source)
            subprocess.run([compiler,'-std=c++17','-I',str(ROOT/'Source/SoraArena/Public'),str(cpp),'-o',str(binary)],check=True,capture_output=True,text=True)
            result=subprocess.run([str(binary)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_preserves_task_and_checkpoint_semantics_and_is_deterministic(self):
        beats=deepcopy(self.chapter['beats']); rows=deepcopy(self.chapter['space']['beats'])
        original=deepcopy(beats)
        place_spire(beats,rows,self.zones(),fail)
        self.assertEqual(rows,self.chapter['space']['beats'])
        self.assertEqual(beats,original)
        task=beats[9]['task']
        self.assertEqual(task['goal'],'waves_cleared')
        self.assertEqual(beats[9]['target_s'],240)
        self.assertTrue(beats[9]['checkpoint'])
        self.assertTrue(beats[10]['checkpoint'])

    def test_rejects_wave_contract_drift(self):
        for key,value in [('spawn','ground'),('count',5),('type','drone')]:
            beats=deepcopy(self.chapter['beats'])
            beats[9]['params']['waves'][0]['enemies'][0][key]=value
            with self.subTest(key=key),self.assertRaises(BuildError):
                place_spire(beats,deepcopy(self.chapter['space']['beats']),self.zones(),fail)

if __name__=='__main__':
    unittest.main()
