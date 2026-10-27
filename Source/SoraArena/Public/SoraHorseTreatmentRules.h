#pragma once

// ch02.b06. Health remains in the campaign task; this owns only held work
// and two independent active-play cooldowns, never a second health store.
namespace SoraHorseTreatmentRules
{
constexpr int Horses=2,FullHp=400,HealHp=60,HoldMs=2000,CooldownMs=20000;
struct FState { int Index=-1,HeldMs=0,Cooldown[Horses]={}; };
constexpr void Cancel(FState& S) { S.Index=-1; S.HeldMs=0; }
constexpr bool Eligible(const FState& S,int Index,int Hp)
{ return Index>=0&&Index<Horses&&Hp>0&&Hp<FullHp&&S.Cooldown[Index]==0; }
constexpr bool Begin(FState& S,int Index,int Hp)
{
    if(S.Index>=0||!Eligible(S,Index,Hp)) return false;
    S.Index=Index; S.HeldMs=0; return true;
}
// A completion is returned once. Cooldown begins at its actual boundary,
// including any remainder of a long frame; another heal needs a fresh press.
constexpr int Tick(FState& S,int DtMs,bool Held)
{
    if(!Held) Cancel(S);
    if(DtMs<=0) return -1;
    for(int& Left:S.Cooldown) Left=Left>DtMs?Left-DtMs:0;
    if(S.Index<0) return -1;
    const int Need=HoldMs-S.HeldMs;
    if(DtMs<Need) { S.HeldMs+=DtMs; return -1; }
    const int Index=S.Index,After=DtMs-Need;
    S.Cooldown[Index]=After<CooldownMs?CooldownMs-After:0;
    Cancel(S); return Index;
}
}
