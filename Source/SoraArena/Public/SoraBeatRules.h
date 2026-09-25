#pragma once

// Offline chapter beat gates for catalog schema 4, shared by the Unreal
// campaign director and a host-compiled acceptance driver. A chapter is an
// ordered list of at most 32 beats. A beat starts once the earlier beats it
// requires are complete; completing it may restore one of the chapter's three
// production sites and unlock weapons (IDs 0-20) and mechanic flags. Optional
// beats never gate a required one, and a later beat grants any optional
// weapon the player skipped, so every route ends with the same unlocks.
// No wallet, network, or Unreal headers belong here.
namespace SoraBeatRules
{
constexpr int MaxBeats = 32;
constexpr int SiteCount = 3;
constexpr int WeaponCount = 21;
constexpr int MechanicCount = 19;
constexpr unsigned AllSitesMask = (1u << SiteCount) - 1u;
constexpr unsigned AllWeaponsMask = (1u << WeaponCount) - 1u;
constexpr unsigned AllMechanicsMask = (1u << MechanicCount) - 1u;

struct FBeat
{
    unsigned RequiresMask;   // earlier beats that must be complete first
    int Site;                // production site restored on completion, or -1
    unsigned WeaponsMask;    // weapons unlocked on completion
    unsigned GrantsMask;     // skipped optional weapons granted on completion
    unsigned MechanicsMask;  // mechanic flags unlocked on completion
    bool Optional;
    bool Checkpoint;         // saves at the beat's start
    int PhaseCheckpoints;    // further saves inside a boss or duel, one per later phase
};

// Chapter progress as a checkpoint saves it. The weapon and mechanic masks are
// cumulative across the campaign; Entry* are their values when the chapter began.
struct FProgress
{
    unsigned CompletedMask;
    unsigned SitesMask;
    unsigned WeaponsMask;
    unsigned MechanicsMask;
    bool Complete;
};

constexpr unsigned BeatBit(int Index)
{
    return Index >= 0 && Index < MaxBeats ? 1u << Index : 0u;
}

constexpr unsigned AllBeatsMask(int Count)
{
    return Count <= 0 || Count > MaxBeats ? 0u : Count == MaxBeats ? ~0u : (1u << Count) - 1u;
}

constexpr unsigned SiteBit(int Site)
{
    return Site >= 0 && Site < SiteCount ? 1u << Site : 0u;
}

constexpr unsigned RequiredBeatsMask(const FBeat* Beats, int Count)
{
    unsigned Mask = 0u;
    for (int Index = 0; Beats && Index < Count && Index < MaxBeats; ++Index)
        if (!Beats[Index].Optional)
            Mask |= BeatBit(Index);
    return Mask;
}

// Unlocks a chapter can add: every beat's when IncludeOptional, else only
// those every route completes (required beats' unlocks and grants).
constexpr unsigned ChapterWeapons(const FBeat* Beats, int Count, bool IncludeOptional)
{
    unsigned Mask = 0u;
    for (int Index = 0; Beats && Index < Count && Index < MaxBeats; ++Index)
        if (IncludeOptional || !Beats[Index].Optional)
            Mask |= Beats[Index].WeaponsMask | Beats[Index].GrantsMask;
    return Mask;
}

constexpr unsigned ChapterMechanics(const FBeat* Beats, int Count)
{
    unsigned Mask = 0u;
    for (int Index = 0; Beats && Index < Count && Index < MaxBeats; ++Index)
        Mask |= Beats[Index].MechanicsMask;
    return Mask;
}

constexpr bool ChapterValid(const FBeat* Beats, int Count)
{
    if (!Beats || Count <= 0 || Count > MaxBeats || Beats[0].RequiresMask != 0u)
        return false;
    const unsigned Required = RequiredBeatsMask(Beats, Count);
    unsigned Sites = 0u, Weapons = 0u, Mechanics = 0u;
    for (int Index = 0; Index < Count; ++Index)
    {
        const FBeat& Beat = Beats[Index];
        const unsigned Site = SiteBit(Beat.Site);
        if ((Beat.RequiresMask & ~AllBeatsMask(Index)) != 0u || (Beat.Site != -1 && Site == 0u) ||
            (Sites & Site) != 0u || (Beat.WeaponsMask & ~AllWeaponsMask) != 0u ||
            (Beat.GrantsMask & ~AllWeaponsMask) != 0u || (Beat.MechanicsMask & ~AllMechanicsMask) != 0u ||
            (Weapons & Beat.WeaponsMask) != 0u || (Mechanics & Beat.MechanicsMask) != 0u ||
            (Beat.WeaponsMask & Beat.GrantsMask) != 0u || Beat.PhaseCheckpoints < 0)
            return false;
        // Optional beats restore no site, unlock no mechanic and gate no required beat.
        if (Beat.Optional && (Site != 0u || Beat.MechanicsMask != 0u))
            return false;
        if (!Beat.Optional && (Beat.RequiresMask & ~Required) != 0u)
            return false;
        Sites |= Site;
        Weapons |= Beat.WeaponsMask;
        Mechanics |= Beat.MechanicsMask;
    }
    return Sites == AllSitesMask;
}

constexpr bool CanStartBeat(FProgress State, const FBeat* Beats, int Count, int Index)
{
    return Beats && !State.Complete && Index >= 0 && Index < Count && Index < MaxBeats &&
        (State.CompletedMask & BeatBit(Index)) == 0u &&
        (State.CompletedMask & Beats[Index].RequiresMask) == Beats[Index].RequiresMask;
}

constexpr bool CompleteBeat(FProgress& State, const FBeat* Beats, int Count, int Index)
{
    if (!CanStartBeat(State, Beats, Count, Index))
        return false;
    State.CompletedMask |= BeatBit(Index);
    State.SitesMask |= SiteBit(Beats[Index].Site);
    State.WeaponsMask |= Beats[Index].WeaponsMask | Beats[Index].GrantsMask;
    State.MechanicsMask |= Beats[Index].MechanicsMask;
    return true;
}

constexpr bool CanFinishChapter(FProgress State, const FBeat* Beats, int Count)
{
    const unsigned Required = RequiredBeatsMask(Beats, Count);
    return Beats && Required != 0u && (State.CompletedMask & Required) == Required &&
        State.SitesMask == AllSitesMask;
}

constexpr bool FinishChapter(FProgress& State, const FBeat* Beats, int Count)
{
    if (State.Complete || !CanFinishChapter(State, Beats, Count))
        return false;
    State.Complete = true;
    return true;
}

// The first required beat still to play, or -1 once every one is complete.
constexpr int NextBeat(FProgress State, const FBeat* Beats, int Count)
{
    for (int Index = 0; Beats && Index < Count && Index < MaxBeats; ++Index)
        if (!Beats[Index].Optional && (State.CompletedMask & BeatBit(Index)) == 0u)
            return CanStartBeat(State, Beats, Count, Index) ? Index : -1;
    return -1;
}

// A saved state is exactly what completing its beats from the entry masks yields.
constexpr bool ProgressValid(FProgress State, const FBeat* Beats, int Count,
    unsigned EntryWeapons, unsigned EntryMechanics)
{
    if (!Beats || Count <= 0 || Count > MaxBeats || (State.CompletedMask & ~AllBeatsMask(Count)) != 0u ||
        (EntryWeapons & ~AllWeaponsMask) != 0u || (EntryMechanics & ~AllMechanicsMask) != 0u)
        return false;
    unsigned Sites = 0u, Weapons = EntryWeapons, Mechanics = EntryMechanics;
    for (int Index = 0; Index < Count; ++Index)
    {
        if ((State.CompletedMask & BeatBit(Index)) == 0u)
            continue;
        const FBeat& Beat = Beats[Index];
        if ((State.CompletedMask & Beat.RequiresMask) != Beat.RequiresMask)
            return false;
        Sites |= SiteBit(Beat.Site);
        Weapons |= Beat.WeaponsMask | Beat.GrantsMask;
        Mechanics |= Beat.MechanicsMask;
    }
    return State.SitesMask == Sites && State.WeaponsMask == Weapons && State.MechanicsMask == Mechanics &&
        (!State.Complete || CanFinishChapter(State, Beats, Count));
}

// A checkpoint is taken at the start of a checkpoint beat (phase 0) or at a
// later phase of a boss or duel that saves per phase, before that beat completes.
constexpr bool CheckpointValid(FProgress State, const FBeat* Beats, int Count,
    unsigned EntryWeapons, unsigned EntryMechanics, int Beat, int Phase)
{
    return ProgressValid(State, Beats, Count, EntryWeapons, EntryMechanics) &&
        CanStartBeat(State, Beats, Count, Beat) && Phase >= 0 &&
        (Phase == 0 ? Beats[Beat].Checkpoint : Phase <= Beats[Beat].PhaseCheckpoints);
}

// Entry masks a chapter accepts: at least every route's unlocks from the
// earlier chapters, at most all of them (chapter select grants the latter).
constexpr bool EntryValid(unsigned Entry, unsigned RouteMinimum, unsigned AllEarlier)
{
    return (RouteMinimum & ~Entry) == 0u && (Entry & ~AllEarlier) == 0u;
}
} // namespace SoraBeatRules
