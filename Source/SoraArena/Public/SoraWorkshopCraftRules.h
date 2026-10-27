#pragma once
#include <algorithm>

namespace SoraWorkshopCraftRules
{
constexpr int BendMs=800,BendToleranceMs=160,PasteMs=1500;
constexpr int ActionPresentationMs=1200;
enum class EResult { None,Passed,Missed,Cancelled };
struct FState { int Step=-1,ElapsedMs=0;bool WaitRelease=false; };
// Latest credited unit, never an animation queue or a source of progress.
// Step is zero-based; Unit is one-based within that step. Age uses active
// gameplay time and saturates at ActionPresentationMs (the clip is then over).
// A reset/reload clears the record; presentation must also reset its cursor.
struct FAction { unsigned Serial=0;int Step=-1,Unit=0,AgeMs=-1; };
// Read-only scene/HUD state. Animation consumes these values; it must never
// advance a hold, credit a step or award the workshop's output.
struct FView
{
    bool Active=false,RecipeComplete=false,Assist=false;
    int Step=-1,Committed[6]={},HeldStep=-1,HeldMs=0;
    unsigned FailedStripSerial=0;
    int FailedStripAgeMs=-1;
    FAction LastAction;
};
constexpr bool Timed(int Step){return Step==0||Step==1||Step==3;}
constexpr bool Begin(FState& S,int Step)
{
    if(!Timed(Step)||S.Step>=0||S.WaitRelease)return false;
    S={Step,0,false};return true;
}
constexpr void Cancel(FState& S,bool WaitRelease=true){S={-1,0,WaitRelease};}
constexpr EResult Tick(FState& S,int DeltaMs,bool Eligible,bool Assist=false)
{
    if(S.Step<0)return EResult::None;
    if(!Eligible){Cancel(S);return EResult::Cancelled;}
    const int Limit=S.Step==0?(Assist?BendMs:BendMs+BendToleranceMs+1):PasteMs;
    S.ElapsedMs+=std::clamp(DeltaMs,0,std::max(0,Limit-S.ElapsedMs));
    if(S.ElapsedMs<Limit)return EResult::None;
    const auto Result=S.Step==0&&!Assist?EResult::Missed:EResult::Passed;Cancel(S);return Result;
}
constexpr EResult Release(FState& S,bool Eligible)
{
    EResult Result=EResult::None;
    if(S.Step>=0)
        Result=!Eligible||S.Step!=0?EResult::Cancelled:
            S.ElapsedMs>=BendMs-BendToleranceMs&&S.ElapsedMs<=BendMs+BendToleranceMs?EResult::Passed:EResult::Missed;
    Cancel(S,false);return Result;
}
}
