#pragma once

// Optional gallery discoveries are durable lore, independent of the lift's
// checkpoint and the three collectible bits awarded by its existing cache.
namespace SoraGalleryRules
{
constexpr int Count=2;
constexpr int Toy=0,Mon=1;
constexpr int All=(1<<Count)-1;
constexpr double OffsetX=320.0;
constexpr double OffsetY[Count]={-650.0,700.0};
constexpr double ReachCm=260.0,FloorToleranceCm=20.0;
constexpr unsigned long long CacheFinds=7ull<<(7*6+2); // ch08.c03-c05
constexpr int ArrowWeapon=18,ArrowReward=12;
constexpr bool ClaimValid(bool Claimed,int HighestChapter,unsigned long long Finds)
{
    return !Claimed||(HighestChapter==7&&(Finds&CacheFinds)==CacheFinds);
}
constexpr int Bit(int Index) { return Index>=0&&Index<Count?1<<Index:0; }
constexpr bool Valid(int Mask,int HighestChapter)
{
    return Mask>=0&&(Mask&~All)==0&&(Mask==0||HighestChapter==7);
}
inline bool Record(int& Mask,int Index)
{
    const int Flag=Bit(Index);
    if(!Flag||(Mask&Flag)!=0) return false;
    Mask|=Flag;
    return true;
}
}
