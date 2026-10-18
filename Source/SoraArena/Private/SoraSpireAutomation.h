#pragma once
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraLiftAutomation.h"
#include "SoraCatalog.h"

namespace SoraSpireAutomation
{
inline bool Climb(FSoraAutomationWorld& W,const FSoraBeatSpace& Space,int32 From,int32 To)
{
    for(int32 N=From;N<=To;++N)
    {
        if(!SoraLiftAutomation::Walk(W,Space.Spire.Ramp[N])) return false;
        // A point with matching XY on another winding is not arrival.
        if(FMath::Abs(W.Player()->GetActorLocation().Z-Space.Spire.Ramp[N].Z-90.f)>55.f) return false;
    }
    return true;
}
}
#endif
