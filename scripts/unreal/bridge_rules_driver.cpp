#include "SoraBridgeRules.h"
#include <cassert>
#include <iostream>
namespace R=SoraBridgeRules;
int main()
{
    assert(R::Pace(-1,true,true)==.85&&R::Pace(1,true,true)==1.1);
    assert(R::Pace(0,true,true)==1&&R::Pace(1,false,true)==1&&R::Pace(-1,true,false)==1);
    assert(R::ListAt(0,0,true)==0&&R::ListAt(0,1,true)==10&&R::ListAt(10,1,false)==0);
    assert(R::ListAt(0,10,true)==10&&R::ListAt(10,10,false)==0);
    assert(R::MovingSeconds(0,699)==0&&R::MovingSeconds(699,700)==0);
    assert(std::abs(R::MovingSeconds(690,710)-.01)<1e-9);
    assert(std::abs(R::MovingSeconds(0,7000)-5.3)<1e-9);
    assert(R::MovingSeconds(6000,8000)==0);
    assert(R::MovingSeconds(700,800,840)==0); // Existing easy difficulty warning stays authoritative.
    assert(std::abs(R::MovingSeconds(620,650,630)-.02)<1e-9);
    double Speed=0;
    assert(R::SlideStep(Speed,1,0)==0&&Speed==0);
    // Independently integrate gravity along the ten-degree plane. Different
    // frame partitions must agree, including the 500 cm/s tuning cap.
    const double A=980*std::sin(10*std::acos(-1)/180),ToCap=500/A;
    for(double Time:{.1,1.0,2.5,5.3})
    {
        const double T=std::min(Time,ToCap),Expected=.5*A*T*T+500*(Time-T);
        for(int Count:{1,17,318})
        {
            Speed=0; double Distance=0;
            for(int N=0;N<Count;++N) Distance+=R::SlideStep(Speed,Time/Count,10);
            assert(std::abs(Distance-Expected)<1e-7);
            assert(std::abs(Speed-std::min(500.0,A*Time))<1e-7);
        }
    }
    // Collision stops are external sweep outcomes; the next impulse starts
    // from zero velocity at the retained position, not at the spawn point.
    Speed=0; const double First=R::SlideStep(Speed,.02,10); Speed=0;
    assert(std::abs(R::SlideStep(Speed,.02,10)-First)<1e-9);
    std::cout<<"bridge rules: pace, tilt bounds, warning boundaries and 12 frame partitions passed\n";
}
