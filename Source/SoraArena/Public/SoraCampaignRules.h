#pragma once

// Offline campaign rules above the chapter beats (SoraBeatRules.h): chapter
// advance and liberation, the collectibles mask, and the training arena's
// defeat and site gates. Shared by the Unreal campaign director and a
// host-compiled acceptance driver. No wallet, network, or Unreal headers
// belong here.
namespace SoraCampaignRules
{
constexpr int ChapterCount = 8;
constexpr int CollectiblesPerChapter = 6;

constexpr int AdvanceChapter(int ChapterId, int LastChapterId, bool Complete)
{
    return Complete && ChapterId >= 0 && ChapterId < LastChapterId ? ChapterId + 1 : ChapterId;
}

constexpr bool CampaignLiberated(int ChapterId, int LastChapterId, bool Complete)
{
    return Complete && ChapterId == LastChapterId;
}

// Collectibles are one campaign-wide mask, bit chapter * 6 + the chapter's mask_bit.
constexpr unsigned long long CollectibleBit(int ChapterId, int MaskBit)
{
    return ChapterId >= 0 && ChapterId < ChapterCount && MaskBit >= 0 && MaskBit < CollectiblesPerChapter
        ? 1ull << (ChapterId * CollectiblesPerChapter + MaskBit) : 0ull;
}

// Only chapters already reached can have been searched.
constexpr bool CollectiblesValid(unsigned long long Mask, int HighestChapter)
{
    if (HighestChapter < 0 || HighestChapter >= ChapterCount)
        return false;
    const int Bits = (HighestChapter + 1) * CollectiblesPerChapter;
    return (Mask & ~((1ull << Bits) - 1ull)) == 0ull;
}

// The training arena: twelve defeats and three workshops in any order, then the exit.
struct FArena
{
    int Kills;
    unsigned SitesMask;
    bool Complete;
};
constexpr int ArenaDefeats = 12;
constexpr unsigned ArenaSitesMask = 7u;

constexpr bool RecordArenaDefeat(FArena& State)
{
    if (State.Complete || State.Kills < 0 || State.Kills >= ArenaDefeats)
        return false;
    ++State.Kills;
    return true;
}

constexpr bool RestoreArenaSite(FArena& State, int Index)
{
    if (State.Complete || Index < 0 || Index >= 3 || (State.SitesMask & (1u << Index)) != 0u)
        return false;
    State.SitesMask |= 1u << Index;
    return true;
}

constexpr bool FinishArena(FArena& State)
{
    if (State.Complete || State.Kills != ArenaDefeats || State.SitesMask != ArenaSitesMask)
        return false;
    State.Complete = true;
    return true;
}
} // namespace SoraCampaignRules
