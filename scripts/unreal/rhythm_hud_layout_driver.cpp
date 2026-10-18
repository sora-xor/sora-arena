#include "SoraRhythmHUDLayout.h"
#include <cassert>
#include <initializer_list>
#include <cstdio>
int main()
{
    using namespace SoraRhythmHUDLayout;
    int Cases=0;
    for(int H:{720,1080})
    {
        const float W=H==720?1280.f:1920.f,S=H/1000.f;
        // Sweeps bound both Japanese-only and bilingual input labels, with
        // short keyboard keys through long rebound/gamepad names and large
        // glyph boxes. Actual font metrics are checked by the UE fixture.
        for(float PW:{120.f,240.f,360.f,480.f})
        for(float PH:{22.f,30.f,40.f})
        for(float Top:{H*.52f,H*.65f,H*.82f})
        {
            const auto L=Place(W,H,S,PW,PH,Top);
            assert(Fits(L,W,H,PW,PH,Top));
            for(float R:{22.f,37.f,52.f})
                assert(L.CenterX+R+Stroke+Gap<=L.PromptX+.01f);
            ++Cases;
        }
        // An overlap at the old center is rejected, rather than the test
        // merely agreeing with a new constant.
        FLayout Old{W*.5f-75.f*S,H*.5f+60.f*S,W*.5f,H*.5f+105.f*S};
        assert(!Fits(Old,W,H,240.f,30.f,H*.82f));
        const auto L=Place(W,H,S,240.f,30.f,H*.82f);
        std::printf("%dx%d prompt=(%.1f,%.1f) ring=(%.1f,%.1f) gap=%.0fpx\n",
            static_cast<int>(W),H,L.PromptX,L.PromptY,L.CenterX,L.CenterY,Gap);
    }
    std::printf("PASS %d computed layouts and both old-overlap regressions\n",Cases);
}
