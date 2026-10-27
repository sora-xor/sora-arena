#include "SoraCampaignDirector.h"
#include "SoraCampaignRules.h"
#include "SoraCatalog.h"
#include "SoraFrontEnd.h"
#include "SoraGameMode.h"
#include "SoraPlayerCharacter.h"
#include "SoraSaveGame.h"
#include "SoraWorldBuilder.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"

namespace
{
const TCHAR* const FindIds[]={TEXT("poi_chalk"),TEXT("poi_balance_door")};
}
int32 USoraCampaignDirector::TenementExploreBeat() const
{
    const auto* Chapter=ActiveChapter();const auto* Space=ActiveSpace();
    if(!Chapter||!Save||!Mode().bCampaign||!Space||!Space->bTenements||Mode().bChapterComplete)return INDEX_NONE;
    const int32 Index=Chapter->BeatIndex(TEXT("ch03.b04"));
    if(Index==INDEX_NONE)return INDEX_NONE;
    const bool Available=(BeatState.CompletedMask&SoraBeatRules::BeatBit(Index))!=0u||
        SoraBeatRules::CanStartBeat(BeatState,Chapter->Rules.GetData(),Chapter->Rules.Num(),Index);
    return Available?Index:INDEX_NONE;
}
void USoraCampaignDirector::TickTenementFinds()
{
    const int32 Index=TenementExploreBeat();auto* Hero=Mode().Hero();auto* Arena=Mode().Arena();
    if(Index==INDEX_NONE||!Hero||!Arena||!Mode().IsPlaying())return;
    const auto& Explore=ActiveChapter()->Beats[Index];
    // b04 runs beside the required carry objective. Its ambient volumes
    // cannot rely on b04 becoming the active task, which never happens.
    if(ActiveBeatData()->Id==TEXT("ch03.b05")||ActiveBeatData()->Id==TEXT("ch03.b06"))
    {
        const double Feet=Hero->GetActorLocation().Z-Hero->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
        if(Hero->GetCharacterMovement()->IsMovingOnGround()&&FMath::Abs(Feet)<8.)
            for(const auto& Volume:Explore.Space.Volumes)
            {
                const FString Key=TEXT("tenement:")+Volume.Event;
                if(BeatEvents.Contains(Key)||!Volume.Contains(Hero->GetActorLocation()))continue;
                BeatEvents.Add(Key);Fire(Volume.Event,Index);
            }
    }
    for(int I=0;I<2;++I)
    {
        const auto* Poi=Explore.Pois.FindByPredicate([&](const FSoraExplorePoi& P){return P.Id==FindIds[I];});
        if(!Poi||!ActiveChapter()->Collectibles.IsValidIndex(Poi->Collectible)||!Arena->CanReachTenementFind(I,*Hero))continue;
        const auto& Item=ActiveChapter()->Collectibles[Poi->Collectible];
        const FString Event=TEXT("tenement_hint:")+Item.Id;
        if((CollectedMask()&SoraCampaignRules::CollectibleBit(ChapterId,Item.MaskBit))!=0ull||BeatEvents.Contains(Event))continue;
        const auto Key=SoraUI::ActionKey(this,TEXT("Interact"));
        const FString Japanese=I==0?FString::Printf(TEXT("白墨の空紋：%s で調べる。"),*Key.Japanese):
            FString::Printf(TEXT("差押状：%s で読む。"),*Key.Japanese);
        const FString English=I==0?FString::Printf(TEXT("Chalk sky crest: %s to inspect."),*Key.English):
            FString::Printf(TEXT("Seizure notice: %s to read."),*Key.English);
        Notify(Japanese,English,6.f);
        BeatEvents.Add(Event);return;
    }
}
bool USoraCampaignDirector::InteractTenementFind(ASoraPlayerCharacter& Player)
{
    const int32 Index=TenementExploreBeat();auto* Arena=Mode().Arena();
    if(Index==INDEX_NONE||!Arena||!Mode().IsPlaying()||!Player.CanPlay())return false;
    const auto& Chapter=*ActiveChapter();const auto& Explore=Chapter.Beats[Index];
    for(int I=0;I<2;++I)
    {
        if(!Arena->CanReachTenementFind(I,Player))continue;
        const auto* Poi=Explore.Pois.FindByPredicate([&](const FSoraExplorePoi& P){return P.Id==FindIds[I];});
        if(!Poi||!Chapter.Collectibles.IsValidIndex(Poi->Collectible))return false;
        const auto& Item=Chapter.Collectibles[Poi->Collectible];
        const uint64 Bit=SoraCampaignRules::CollectibleBit(ChapterId,Item.MaskBit);
        if((CollectedMask()&Bit)==0ull)
        {
            Save->Collectibles=static_cast<int64>(CollectedMask()|Bit);IdleMs=0;
            for(const auto& Category:FSoraCatalog::Get().CollectibleCategories)
                if(Category.Id==Item.Category)
                    Tell(FSoraStoryNotice::EKind::Collectible,TEXT("見つけた：")+Category.Japanese,
                        TEXT("Found: ")+Category.English,Item.Codex,Item.CodexEnglish);
            Fire(TEXT("collectible:")+Item.Id,Index);Fire(TEXT("collectible_found:")+Item.Id,Index);
            Fire(TEXT("event:collectible_")+Item.Id.Replace(TEXT("."),TEXT("_")),Index);
            // Each discovery survives death or quit, independently of the
            // other find and of the mandatory weapon-retrieval objective.
            SaveProgress();
        }
        bool All=!Explore.Rewards.IsEmpty();
        for(const int32 Reward:Explore.Rewards)
            All=All&&(CollectedMask()&SoraCampaignRules::CollectibleBit(ChapterId,Chapter.Collectibles[Reward].MaskBit))!=0ull;
        if(All&&(BeatState.CompletedMask&SoraBeatRules::BeatBit(Index))==0u)CompleteOptional(Index);
        return true;
    }
    return false;
}
