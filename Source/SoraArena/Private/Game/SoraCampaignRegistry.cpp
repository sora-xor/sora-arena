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
SoraText::FLine SoraRegistry::Status(ESoraRegistryState State)
{
    if(State==ESoraRegistryState::Returned)
        return SoraText::Line(NSLOCTEXT("SoraArena.Registry","Returned","返還のみ記帳・札は切らず"));
    if(State==ESoraRegistryState::Inspected)
        return SoraText::Line(NSLOCTEXT("SoraArena.Registry","Inspected","三者改め・割符"));
    return SoraText::Line(NSLOCTEXT("SoraArena.Registry","Recorded","記帳済み"));
}
void USoraCampaignDirector::TellRegistry(int32 CompletedBeat)
{
    const FSoraChapter* Chapter=ActiveChapter();
    if(!Chapter||!Chapter->Beats.IsValidIndex(CompletedBeat)) return;
    const FString& Id=Chapter->Beats[CompletedBeat].Id;
    for(const FSoraRegistryRow& Row:RegistryRows())
    {
        // The first inspection changes three existing entries; it creates no
        // goods. A later delivery or posting with no registry writes nothing.
        if(Row.BeatId!=Id&&Id!=TEXT("ch05.b12")) continue;
        SoraText::FLine Heading=SoraText::Format(NSLOCTEXT("SoraArena.Registry","Notice","生産改帳：{Goods}"),
            {{TEXT("Goods"),{Row.Entry.Japanese(),Row.Entry.English()}}});
        const FSoraBeat& Completed=Chapter->Beats[CompletedBeat];
        if(Row.BeatId==Id&&Completed.Cargo.Total>0)
        {
            // The last transfer immediately enters a cinematic. Registry
            // notices retain their visible duration through that card, so
            // the authored zero count is still shown when the HUD returns.
            const int32 Left=SoraCargoRules::Remaining(Completed.Cargo,Completed.Task.Count,TaskState.Done);
            Heading.Japanese+=FString::Printf(TEXT("  |  麦 残り %d束"),Left);
            Heading.English+=FString::Printf(TEXT(" / Barley: %d sheaves left"),Left);
        }
        const SoraText::FLine Detail=SoraRegistry::Status(Row.State);
        Tell(FSoraStoryNotice::EKind::Registry,Heading.Japanese,Heading.English,Detail.Japanese,Detail.English);
    }
}
