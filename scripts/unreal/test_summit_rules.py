"""Native summit collision aperture, seizure masks, and exact state boundaries."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]

class SummitRulesTests(unittest.TestCase):
    def test_native_disc_and_tile_lifecycle(self):
        source=r'''
#include "SoraSummitRules.h"
#include <cassert>
#include <iostream>
#include <map>
using namespace SoraSummitRules;
int main() {
    double area=0; int count=0,full=0;
    std::map<std::pair<int,int>,FPolygon> tiles;
    for(int x=-GridRadius;x<GridRadius;++x) for(int y=-GridRadius;y<GridRadius;++y) {
        auto p=Tile(x,y); if(p.empty()) continue; ++count; tiles[{x,y}]=p;
        double a=0;
        for(unsigned n=0;n<p.size();++n) {
            const auto v=p[n],w=p[(n+1)%p.size()];
            assert(v.X>=x*TileCm-1e-5&&v.X<=(x+1)*TileCm+1e-5);
            assert(v.Y>=y*TileCm-1e-5&&v.Y<=(y+1)*TileCm+1e-5);
            assert(std::hypot(v.X,v.Y)<=RadiusCm+1e-5);
            assert(std::hypot(v.X-w.X,v.Y-w.Y)>.01);
            a+=v.X*w.Y-v.Y*w.X;
        }
        assert(a>1); a*=.5; area+=a; full+=std::abs(a-TileCm*TileCm)<.01;
    }
    const double disc=72*.5*RadiusCm*RadiusCm*std::sin(2*Pi/72);
    assert(std::abs(area-disc)<.01); // Every fragment, no overlaps or holes.
    assert(area>Pi*RadiusCm*RadiusCm*.998);
    assert(count>100&&count<144&&full>60);
    assert(Tile(20,20).empty());
    for(int warning:{1275,1500,1950}) {
        assert(Stage(-1,warning)==EStage::Intact);
        assert(Stage(0,warning)==EStage::Marked&&Solid(Stage(warning-1,warning)));
        assert(Stage(warning,warning)==EStage::Void&&!Solid(Stage(warning,warning)));
        assert(Stage(warning+VoidMs-1,warning)==EStage::Void);
        assert(Stage(warning+VoidMs,warning)==EStage::Restoring);
        assert(!Solid(Stage(warning+VoidMs+RestoreMs-1,warning)));
        assert(Stage(warning+VoidMs+RestoreMs,warning)==EStage::Intact);
        assert(Offset(warning+500,warning)<-100&&Offset(warning-1,warning)==0);
        assert(Offset(warning+VoidMs+RestoreMs,warning)==0);
        assert(warning+VoidMs+RestoreMs<CadenceMs);
    }
    for(int pattern=0;pattern<3;++pattern) {
        int marked=0,edge=0;
        for(const auto& entry:tiles) {
            const int x=entry.first.first,y=entry.first.second;
            const bool selected=Selected(pattern,x,y,2,-3); marked+=selected;
            if(pattern==1&&selected) {
                const double r=std::hypot((x+.5)*TileCm,(y+.5)*TileCm);
                assert(r>=800&&r<=1200);
            }
            if(!selected) for(const auto d:{std::pair<int,int>{1,0},{-1,0},{0,1},{0,-1}}) {
                const int nx=x+d.first,ny=y+d.second;
                if(!tiles.count({nx,ny})||Selected(pattern,nx,ny,2,-3)) { ++edge; break; }
            }
        }
        assert(marked>10&&marked<count/2&&edge>8);
    }
    assert(Selected(2,2,-3,2,-3)); // Tally locks all three lines through the marked hero cell.
    assert(Selected(2,2,1,2,-3)&&Selected(2,-2,-3,2,-3)&&Selected(2,3,-2,2,-3));
    for(int frame:{1,7,16,33,100,500}) {
        FCut distant;
        assert(!Begin(distant,false,true));
        assert(!TickCut(distant,2000,false,true,1500));
        assert(!Begin(distant,true,true)); // Walking in while E remains down cannot start.
        assert(!TickCut(distant,2000,true,true,1500));
        TickCut(distant,1,true,false,1500);
        assert(!Begin(distant,true,false));
        assert(Begin(distant,true,true));
        FCut cut; assert(Begin(cut,true,true));
        int elapsed=0; bool done=false;
        while(!done) { done=TickCut(cut,frame,true,true,1500); elapsed+=frame; assert(elapsed<=1500+frame); }
        assert(elapsed>=1500&&cut.NeedsRelease&&!cut.Active);
        assert(!Begin(cut,true,true));
        TickCut(cut,1,true,false,1500); assert(Begin(cut,true,true));
        assert(!TickCut(cut,700,true,true,1500));
        TickCut(cut,1,true,false,1500); assert(cut.HeldMs==0&&!cut.Active);
        assert(Begin(cut,true,true)); assert(!TickCut(cut,900,true,true,1500));
        TickCut(cut,1,false,true,1500); assert(cut.HeldMs==0&&cut.NeedsRelease);
        assert(!Begin(cut,true,true));
        TickCut(cut,1,true,false,1500); assert(Begin(cut,true,true));
        Interrupt(cut); assert(!TickCut(cut,1500,true,true,1500));
    }
    std::cout<<count<<" clipped tiles, "<<full<<" full squares, "<<area<<" cm2\n";
}
'''
        compiler=os.environ.get('CXX') or shutil.which('clang++') or shutil.which('c++')
        self.assertIsNotNone(compiler, 'Host C++ compiler is required')
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp); (path/'summit.cpp').write_text(source)
            subprocess.run([compiler,'-std=c++17','-I',str(ROOT/'Source/SoraArena/Public'),str(path/'summit.cpp'),'-o',str(path/'summit')],check=True,capture_output=True,text=True)
            result=subprocess.run([str(path/'summit')],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            print(result.stdout.strip())

if __name__=='__main__': unittest.main()
