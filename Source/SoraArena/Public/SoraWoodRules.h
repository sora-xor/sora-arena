#pragma once

// Durable discovery ledger, independent of optional traversal completion.
namespace SoraWoodRules
{
constexpr int Stone=0, Vista=1, Boundary=2, Shrine=3, Toshiya=4;
constexpr int Count=5, All=(1<<Count)-1;
constexpr int ReachCm=190, FloorToleranceCm=25, ShotOriginRadiusCm=150;
constexpr int DistanceCm=4500;
constexpr int Bit(int Index) { return Index>=0&&Index<Count?1<<Index:0; }
constexpr bool Valid(int Mask) { return Mask>=0&&(Mask&~All)==0; }
constexpr bool Record(int& Mask,int Index)
{
    const int Flag=Bit(Index);
    if(!Valid(Mask)||!Flag||(Mask&Flag)) return false;
    Mask|=Flag; return true;
}
constexpr bool JunctionValid(bool Junction,int Chapter,int Beat,unsigned Completed)
{ return !Junction||(Chapter==0&&Beat==8&&Completed==127u); }
constexpr bool LedgerValid(int Mask,unsigned long long Collectibles)
{
    return Valid(Mask)&&(!(Mask&Bit(Stone))||(Collectibles&1ull))&&
        (!(Mask&Bit(Boundary))||(Collectibles&2ull));
}
}
