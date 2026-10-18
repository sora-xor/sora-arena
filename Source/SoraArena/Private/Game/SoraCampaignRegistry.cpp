#include "SoraRegistry.h"
#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraGameMode.h"

FString FSoraRegistryEntry::Japanese() const
{
    return FString::Printf(TEXT("%s %d%s"), *ItemJapanese, Quantity, *UnitJapanese);
}
FString FSoraRegistryEntry::English() const
{
    return FString::Printf(TEXT("%s: %d %s"), *ItemEnglish, Quantity, *UnitEnglish);
}
TArray<FSoraRegistryRow> SoraRegistry::Completed(const FSoraChapter& Chapter, int32 ChapterIndex, unsigned CompletedMask)
{
    TArray<FSoraRegistryRow> Rows;
    const int32 FirstTally = Chapter.BeatIndex(TEXT("ch05.b12"));
    const bool bInspected = ChapterIndex > 4 || (ChapterIndex == 4 && FirstTally != INDEX_NONE &&
        (CompletedMask & SoraBeatRules::BeatBit(FirstTally)) != 0u);
    for (int32 Index = 0; Index < Chapter.Beats.Num(); ++Index)
    {
        const FSoraBeat& Beat = Chapter.Beats[Index];
        if (!Beat.Registry.IsSet() || (CompletedMask & SoraBeatRules::BeatBit(Index)) == 0u) continue;
        FSoraRegistryRow& Row = Rows.AddDefaulted_GetRef();
        Row.BeatId = Beat.Id;
        Row.Entry = Beat.Registry.GetValue();
        Row.State = Row.Entry.Mode == ESoraRegistryMode::RecordOnly ? ESoraRegistryState::Returned :
            bInspected ? ESoraRegistryState::Inspected : ESoraRegistryState::Recorded;
    }
    return Rows;
}
TArray<FSoraRegistryRow> USoraCampaignDirector::RegistryRows() const
{
    const FSoraChapter* Chapter = ActiveChapter();
    return Chapter && Mode().bCampaign && !Mode().bDeterministicPractice ?
        SoraRegistry::Completed(*Chapter, ChapterId, BeatState.CompletedMask) : TArray<FSoraRegistryRow>();
}
