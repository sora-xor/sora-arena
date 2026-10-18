#include "SoraCampaignDirector.h"
#include "Game/SoraCampaignReach.h"
#include "SoraCampaignRules.h"
#include "SoraCatalog.h"
#include "SoraGameMode.h"
#include "SoraPlayerCharacter.h"
#include "SoraWorldBuilder.h"

bool USoraCampaignDirector::IsToriiEpilogue() const
{
    const FSoraBeat* Beat=ActiveBeatData();
    return Mode().bCampaign&&Beat&&Beat->Id==TEXT("ch08.b17");
}
bool USoraCampaignDirector::HasWashioSword() const
{
    const FSoraChapter* Chapter=ActiveChapter();
    if(!Chapter||ChapterId!=7) return false;
    for(const FSoraCollectible& Item:Chapter->Collectibles)
        if(Item.Id==TEXT("ch08.c03")) return (CollectedMask()&SoraCampaignRules::CollectibleBit(ChapterId,Item.MaskBit))!=0;
    return false;
}
bool USoraCampaignDirector::HasReturnedWashioSword() const
{
    return IsToriiEpilogue()&&BeatEvents.Contains(TEXT("event:washio_sword_return"));
}
bool USoraCampaignDirector::HasRehungPlaques() const
{
    return IsToriiEpilogue()&&BeatEvents.Contains(TEXT("event:plaque_rehang_done"));
}
bool USoraCampaignDirector::EpilogueObjective(FVector& Location,bool& bInteract) const
{
    const FSoraBeatSpace* Space=ActiveSpace();
    if(!IsToriiEpilogue()||!Space||HasRehungPlaques()) return false;
    if(!BeatEvents.Contains(TEXT("volume_enter:vol_torii")))
    {
        const FSoraVolume* Torii=Space->Volumes.FindByPredicate([](const FSoraVolume& V) { return V.Event==TEXT("volume_enter:vol_torii"); });
        if(!Torii) return false;
        Location=ASoraWorldBuilder::Floor(Torii->Center); bInteract=false; return true;
    }
    // Keep the next destination visible during walk-and-talk. Its interaction
    // waits for the current exchange, so the two conversations cannot overlap.
    Location=ASoraWorldBuilder::Floor(HasWashioSword()&&!HasReturnedWashioSword()?Space->Anchor:Space->Closing);
    bInteract=true;
    return !BeatEvents.Contains(TEXT("event:plaque_rehang"));
}
FString USoraCampaignDirector::EpilogueObjectiveText(bool bEnglish) const
{
    if(!BeatEvents.Contains(TEXT("volume_enter:vol_torii")))
        return bEnglish?TEXT("Walk to the Eastern Torii"):TEXT("東の鳥居へ歩く");
    if(BeatEvents.Contains(TEXT("event:plaque_rehang")))
        return bEnglish?TEXT("Sekireisai rehangs the pupils' plaques"):TEXT("石鈴斎が門人の名札を掛け直す");
    if(HasWashioSword()&&!HasReturnedWashioSword())
        return bEnglish?TEXT("Interact beside Toranosuke to return the Washio sword"):TEXT("虎之介のそばで操作し、鷲尾家の刀を返す");
    return bEnglish?TEXT("Interact at Sekireisai's freestanding name board"):TEXT("石鈴斎の名札掛けの前で操作する");
}
bool USoraCampaignDirector::InteractEpilogue(ASoraPlayerCharacter& Player)
{
    if(!IsToriiEpilogue()) return false;
    if(!Mode().IsPlaying()||!Queue.IsEmpty()||!BeatEvents.Contains(TEXT("volume_enter:vol_torii"))) return true;
    FVector At; bool bInteract=false;
    if(!EpilogueObjective(At,bInteract)||!bInteract||FVector::Dist2D(At,Player.GetActorLocation())>SoraCampaignReach::Interact||
        FMath::Abs(Player.GetActorLocation().Z-At.Z)>200.f) return true;
    Fire(HasWashioSword()&&!HasReturnedWashioSword()?TEXT("event:washio_sword_return"):TEXT("event:plaque_rehang"));
    ShowEpilogue();
    UpdateObjective();
    return true;
}
void USoraCampaignDirector::EpilogueLineFinished(const FString& Id)
{
    if(!IsToriiEpilogue()) return;
    if(Id==TEXT("ch08.b17.sekireisai.009")&&BeatEvents.Contains(TEXT("event:plaque_rehang")))
        Fire(TEXT("event:plaque_rehang_done"));
    ShowEpilogue();
    UpdateObjective();
}
void USoraCampaignDirector::ShowEpilogue()
{
    const FSoraBeat* Beat=ActiveBeatData();
    ASoraWorldBuilder* World=Mode().Arena();
    if(!Beat||!World||(Beat->Id!=TEXT("ch08.b17")&&Beat->Id!=TEXT("ch08.b18"))) return;
    const bool bAfter=Beat->Id==TEXT("ch08.b18");
    int32 Plaques=bAfter?2:0;
    if(!bAfter)
        for(const int32 Line:FinishedLines)
        {
            const FString& Id=ActiveChapter()->Dialogue[Line].Id;
            if(Id==TEXT("ch08.b17.sekireisai.006")) Plaques=FMath::Max(Plaques,1);
            if(Id==TEXT("ch08.b17.sekireisai.007")) Plaques=2;
        }
    World->ShowEpilogue(HasWashioSword(),HasWashioSword()&&(bAfter||HasReturnedWashioSword()),Plaques);
}
