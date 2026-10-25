#pragma once

// These five authored caches collect their exclusive codex finds atomically.
// The durable finds, not a second ammunition ledger, also exhaust the bundle.
// Chapter eight keeps its separately qualified gallery claim contract.
namespace SoraCacheRewardRules
{
struct FArrows
{
    int Amount=0;
    bool Refill=false;
    constexpr bool Enabled() const { return Amount>0; }
};
struct FContract
{
    const char* Beat;
    const char* Token;
    FArrows Arrows;
};
inline constexpr FContract Contracts[]={
    {"ch02.b14","arrows_refill_12",{12,true}},
    {"ch04.b09","arrows:6",{6,false}},
    {"ch05.b13","arrows:12",{12,false}},
    {"ch06.b07","arrows:6",{6,false}},
    {"ch07.b05","arrows_12",{12,false}},
};
template<typename Char> constexpr bool Equal(const Char* Value,const char* Expected)
{
    if(!Value) return false;
    while(*Expected&&*Value==*Expected) { ++Value; ++Expected; }
    return *Value==0&&*Expected==0;
}
template<typename Char> constexpr const FContract* Find(const Char* Beat)
{
    for(const auto& Contract:Contracts) if(Equal(Beat,Contract.Beat)) return &Contract;
    return nullptr;
}
template<typename Char> constexpr bool ArrowToken(const Char* Value)
{
    if(!Value) return false;
    for(const char* Prefix="arrow";*Prefix;++Prefix,++Value)
    {
        const auto Letter=*Value>='A'&&*Value<='Z'?*Value+('a'-'A'):*Value;
        if(Letter!=*Prefix) return false;
    }
    return true;
}
template<typename Char> bool Read(const Char* Beat,const Char* const* Tokens,int Count,FArrows& Out)
{
    Out={};
    const auto* Contract=Find(Beat);
    if(!Contract) return true;
    if(!Tokens||Count<1) return false;
    int Matches=0;
    for(int Index=0;Index<Count;++Index)
    {
        if(Equal(Tokens[Index],Contract->Token)) ++Matches;
        else if(ArrowToken(Tokens[Index])) return false;
    }
    if(Matches!=1) return false;
    Out=Contract->Arrows;
    return true;
}
constexpr bool Unclaimed(unsigned long long Finds,unsigned long long Collected)
{
    // Normal cache collection sets all its exclusive finds in one operation.
    // A restored partial set also cannot be used to mint another bundle.
    return Finds!=0&&(Finds&Collected)==0;
}
}
