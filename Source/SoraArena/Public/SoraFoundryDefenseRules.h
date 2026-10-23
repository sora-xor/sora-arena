#pragma once

// ch05.b07 only. Milliseconds and fractional damage survive frame boundaries.
// Actor health remains authoritative; this state owns supplies and held work.
namespace SoraFoundryDefenseRules
{
constexpr int FurnaceHp=1500, KozoHp=300, RepairHp=150, RepairMs=3000;
constexpr int ReviveMs=4000, DownLimitMs=25000, NetCutMs=1000, DrainHpS=5;
constexpr int TubCount=3, CrewCount=2;
enum class EWork { None, Repair, Revive, Net };
struct FState
{
    unsigned Used=0;
    EWork Work=EWork::None;
    int Index=-1, HeldMs=0, DownMs=0, DrainRemainder=0;
    bool Failed=false;
};
struct FResult { int Repair=-1, Net=-1, Drain=0; bool Revive=false, Failed=false; };
constexpr int Need(EWork Work) { return Work==EWork::Repair?RepairMs:Work==EWork::Revive?ReviveMs:Work==EWork::Net?NetCutMs:0; }
constexpr void Cancel(FState& S) { S.Work=EWork::None; S.Index=-1; S.HeldMs=0; }
constexpr bool Available(const FState& S,int Tub) { return Tub>=0&&Tub<TubCount&&(S.Used&(1u<<Tub))==0; }
constexpr bool Begin(FState& S,EWork Work,int Index)
{
    if(S.Failed||Work==EWork::None||(Work==EWork::Repair&&!Available(S,Index))||
        (Work==EWork::Net&&(Index<0||Index>=CrewCount))||(Work==EWork::Revive&&Index!=0)) return false;
    if(S.Work!=Work||S.Index!=Index) { Cancel(S); S.Work=Work; S.Index=Index; }
    return true;
}
constexpr FResult Tick(FState& S,int DtMs,bool Held,bool Down,int Netted)
{
    FResult R;
    if(S.Failed||DtMs<=0) return R;
    if(!Held) Cancel(S);
    if(!Down) S.DownMs=0;
    const int WorkLeft=Need(S.Work)-S.HeldMs;
    const int LifeLeft=Down?DownLimitMs-S.DownMs:DownLimitMs;
    // A rescue must finish before the deadline; ties fail. Large frames may
    // not award a rescue that would have completed after the deadline.
    const bool Completes=Held&&S.Work!=EWork::None&&WorkLeft<=DtMs&&
        (S.Work!=EWork::Revive||(Down&&WorkLeft<LifeLeft));
    int LiveMs=DtMs;
    if(Down&&LifeLeft<=DtMs&&!(Completes&&S.Work==EWork::Revive))
    {
        LiveMs=LifeLeft>0?LifeLeft:0; S.DownMs=DownLimitMs; S.Failed=true; R.Failed=true; Cancel(S);
    }
    else
    {
        if(Down) S.DownMs+=DtMs;
        if(Completes)
        {
            if(S.Work==EWork::Repair) { R.Repair=S.Index; S.Used|=1u<<S.Index; }
            else if(S.Work==EWork::Net) R.Net=S.Index;
            else { R.Revive=true; S.DownMs=0; }
            Cancel(S);
        }
        else if(Held&&S.Work!=EWork::None) S.HeldMs+=DtMs;
    }
    if(Netted)
    {
        const long long Total=S.DrainRemainder+static_cast<long long>(R.Net>=0&&Netted==1?WorkLeft:LiveMs)*DrainHpS;
        R.Drain=static_cast<int>(Total/1000); S.DrainRemainder=static_cast<int>(Total%1000);
    }
    return R;
}
}
