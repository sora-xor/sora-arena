#pragma once
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraSaveGame.h"

namespace SoraRegistryTesting
{
// A completed-save UI fixture, not evidence of a played campaign. Only the
// review chapters are supported; every field passes ordinary save validation.
inline bool CompletedFixture(USoraSaveGame& Save,int32 ChapterIndex)
{
    if((ChapterIndex!=3&&ChapterIndex!=4&&ChapterIndex!=6)||
        !USoraCampaignDirector::SeedCheckpoint(Save,ChapterIndex,0)) return false;
    const FSoraChapter& Chapter=FSoraCatalog::Get().Chapter(ChapterIndex);
    SoraBeatRules::FProgress State{0u,0u,static_cast<unsigned>(Save.ChapterEntryWeapons),
        static_cast<unsigned>(Save.ChapterEntryMechanics),static_cast<unsigned>(Save.ChapterEntryFlags),false};
    for(int32 Index=0;Index<Chapter.Rules.Num();++Index)
        if(!Chapter.Rules[Index].Optional&&!SoraBeatRules::CompleteBeat(State,Chapter.Rules.GetData(),Chapter.Rules.Num(),Index)) return false;
    if(!SoraBeatRules::FinishChapter(State,Chapter.Rules.GetData(),Chapter.Rules.Num())||
        !SoraBeatRules::ProgressValid(State,Chapter.Rules.GetData(),Chapter.Rules.Num(),Save.ChapterEntryWeapons,
            Save.ChapterEntryMechanics,Save.ChapterEntryFlags)) return false;
    Save.HighestChapter=ChapterIndex+1;
    Save.CheckpointBeat=INDEX_NONE; Save.CheckpointPhase=0; Save.CheckpointComplete=true;
    Save.CheckpointBeatsMask=static_cast<int32>(State.CompletedMask); Save.CheckpointSitesMask=static_cast<int32>(State.SitesMask);
    Save.CheckpointWeapons=static_cast<int32>(State.WeaponsMask); Save.CheckpointMechanics=static_cast<int32>(State.MechanicsMask);
    Save.CheckpointFlags=static_cast<int32>(State.FlagsMask);
    return true;
}
}
#endif
