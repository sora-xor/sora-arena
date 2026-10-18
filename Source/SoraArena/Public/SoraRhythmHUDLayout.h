#pragma once
// Pixel bounds shared by the live canvas and host/capture checks. The full
// metronome sweep (including its stroke) stays beside the measured prompt.
namespace SoraRhythmHUDLayout
{
constexpr float Radius=52.f, Stroke=2.f, Gap=12.f;
struct FLayout
{
    float PromptX=0.f, PromptY=0.f, CenterX=0.f, CenterY=0.f;
};
inline FLayout Place(float Width,float Height,float Scale,float PromptWidth,float PromptHeight,float StoryTop)
{
    FLayout L;
    L.PromptX=Width*.5f-75.f*Scale;
    if(L.PromptX+PromptWidth>Width-Gap) L.PromptX=Width-Gap-PromptWidth;
    L.PromptY=Height*.5f+60.f*Scale;
    L.CenterX=L.PromptX-Gap-Radius-Stroke;
    L.CenterY=L.PromptY+PromptHeight*.5f;
    const float RingBottom=L.CenterY+Radius+Stroke;
    const float TextBottom=L.PromptY+PromptHeight;
    const float Bottom=RingBottom>TextBottom?RingBottom:TextBottom;
    if(Bottom>StoryTop-Gap)
    {
        const float Shift=Bottom-(StoryTop-Gap);
        L.PromptY-=Shift; L.CenterY-=Shift;
    }
    return L;
}
inline bool Fits(const FLayout& L,float Width,float Height,float PromptWidth,float PromptHeight,float StoryTop)
{
    const float R=Radius+Stroke;
    return L.CenterX-R>=0.f&&L.CenterY-R>=0.f&&L.CenterX+R+Gap<=L.PromptX+.01f&&
        L.PromptX+PromptWidth<=Width&&L.PromptY>=0.f&&L.PromptY+PromptHeight<=Height&&
        L.CenterY+R<=StoryTop-Gap+.01f&&L.PromptY+PromptHeight<=StoryTop-Gap+.01f;
}
}
