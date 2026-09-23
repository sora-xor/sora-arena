#pragma once

// Offline chapter gates shared by the Unreal GameMode and a host-compiled
// acceptance driver. No wallet, network, or Unreal headers belong here.
namespace SoraCampaignRules
{
struct FSite
{
    int RequiredKills;
    unsigned RequiredSitesMask;
};

struct FCheckpoint
{
    int Kills;
    unsigned NodesMask;
    bool Complete;
};

constexpr unsigned AllSitesMask(int SiteCount)
{
    return SiteCount > 0 && SiteCount <= 3 ? (1u << SiteCount) - 1u : 0u;
}

constexpr bool CanRestoreSite(int Kills, unsigned ActiveMask, FSite Site)
{
    return Kills >= Site.RequiredKills &&
        (ActiveMask & Site.RequiredSitesMask) == Site.RequiredSitesMask;
}

constexpr bool CanFinishChapter(int Kills, int KillsNeeded, unsigned ActiveMask, int SiteCount)
{
    return AllSitesMask(SiteCount) != 0u && KillsNeeded > 0 && Kills >= KillsNeeded &&
        ActiveMask == AllSitesMask(SiteCount);
}

constexpr bool CheckpointValid(FCheckpoint State, int KillsNeeded, const FSite* Sites, int SiteCount)
{
    const unsigned AllMask = AllSitesMask(SiteCount);
    if (!Sites || !AllMask || KillsNeeded <= 0 || State.Kills < 0 ||
        State.Kills > KillsNeeded || (State.NodesMask & ~AllMask) != 0)
        return false;
    for (int Index = 0; Index < SiteCount; ++Index)
        if ((State.NodesMask & (1u << Index)) != 0 &&
            !CanRestoreSite(State.Kills, State.NodesMask, Sites[Index]))
            return false;
    return !State.Complete || CanFinishChapter(State.Kills, KillsNeeded, State.NodesMask, SiteCount);
}

constexpr bool RecordDefeat(FCheckpoint& State, int KillsNeeded)
{
    if (State.Complete || State.Kills < 0 || State.Kills >= KillsNeeded)
        return false;
    ++State.Kills;
    return true;
}

constexpr bool RestoreSite(FCheckpoint& State, int Index, FSite Site, int SiteCount)
{
    if (State.Complete || AllSitesMask(SiteCount) == 0u || Index < 0 || Index >= SiteCount ||
        (State.NodesMask & (1u << Index)) != 0 ||
        !CanRestoreSite(State.Kills, State.NodesMask, Site))
        return false;
    State.NodesMask |= 1u << Index;
    return true;
}

constexpr bool CompleteChapter(FCheckpoint& State, int KillsNeeded, int SiteCount)
{
    if (State.Complete || !CanFinishChapter(State.Kills, KillsNeeded, State.NodesMask, SiteCount))
        return false;
    State.Complete = true;
    return true;
}

constexpr bool IsFinalBossSlot(int ChapterId, int Spawned, int KillsNeeded)
{
    return ChapterId == 7 && KillsNeeded > 0 && Spawned == KillsNeeded - 1;
}

constexpr bool CanSpawnFinalBoss(int ChapterId, int Kills, int Spawned, int KillsNeeded)
{
    return IsFinalBossSlot(ChapterId, Spawned, KillsNeeded) && Kills == KillsNeeded - 1;
}

constexpr int AdvanceChapter(int ChapterId, int LastChapterId, bool Complete)
{
    return Complete && ChapterId >= 0 && ChapterId < LastChapterId ? ChapterId + 1 : ChapterId;
}

constexpr bool CampaignLiberated(int ChapterId, int LastChapterId, bool Complete)
{
    return Complete && ChapterId == LastChapterId;
}
} // namespace SoraCampaignRules
