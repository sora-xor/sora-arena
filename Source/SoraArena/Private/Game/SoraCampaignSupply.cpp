#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraEquipmentComponent.h"
#include "SoraGameMode.h"
#include "SoraFrontEnd.h"
#include "SoraPlayerCharacter.h"
#include "SoraSaveGame.h"
#include "SoraWorldBuilder.h"
#include "SoraCampaignRules.h"

bool USoraCampaignDirector::ClaimCacheArrows(int32 Index)
{
    const auto* Chapter=ActiveChapter();
    if(!Save||!Chapter||!Chapter->Beats.IsValidIndex(Index)) return false;
    const auto& Cache=Chapter->Beats[Index];
    if(!Cache.CacheArrows.Enabled()) return true;
    unsigned long long Finds=0;
    for(const int32 Item:Cache.Rewards)
        Finds|=SoraCampaignRules::CollectibleBit(ChapterId,Chapter->Collectibles[Item].MaskBit);
    if(!Finds) return false;
    if(!SoraCacheRewardRules::Unclaimed(Finds,CollectedMask())) return true;
    auto* Hero=Mode().Hero();
    auto* Equipment=Hero?Hero->GetEquipment():nullptr;
    // None of these five caches precedes the authored yumi unlock. Taking
    // supplies must not manufacture a weapon entitlement.
    const unsigned Weapons=IsWeaponUnlocked(18)?1u<<18:0u;
    if(!Equipment||Equipment->GrantArrows(Cache.CacheArrows.Amount,Weapons,Cache.CacheArrows.Refill)<0) return false;
    // CompleteOptional immediately collects the exclusive finds and saves
    // them with cache completion. Refusal above changes neither inventory nor
    // finds. Existing checkpoint reload still restores the ordinary loadout.
    return true;
}

void USoraCampaignDirector::TickSupplyHint()
{
    const auto* Beat=ActiveBeatData();
    const auto* Hero=Mode().Hero();
    const auto* Arena=Mode().Arena();
    if(!Beat||Beat->SupplyPoint.IsEmpty()||!Hero||!Arena||!Mode().IsPlaying()) return;
    const FString Event=TEXT("supply_hint:")+Beat->SupplyPoint;
    if(BeatEvents.Contains(Event)||!Arena->CanReachSupply(Beat->SupplyPoint,*Hero)) return;
    const auto Key=SoraUI::ActionKey(this,TEXT("Interact"));
    Notify(FString::Printf(TEXT("同盟の補給箱：%s で矢と弾を補充。"),*Key.Japanese),
        FString::Printf(TEXT("League supply cache: %s replenishes arrows and ammunition."),*Key.English),6.f);
    Fire(Event);
}

bool USoraCampaignDirector::InteractSupply(ASoraPlayerCharacter& Player)
{
    const FSoraBeat* Beat=ActiveBeatData();
    const auto* Arena=Mode().Arena();
    if(!Beat||!Mode().IsPlaying()||!Player.CanPlay()||!Arena||
        !Arena->CanReachSupply(Beat->SupplyPoint,Player)) return false;
    unsigned Unlocked=0;
    for(int32 Id=0;Id<SoraBeatRules::WeaponCount;++Id) if(IsWeaponUnlocked(Id)) Unlocked|=1u<<Id;
    const int32 Refilled=Player.GetEquipment()->RestockUnlocked(Unlocked);
    if(Refilled<0)
        Notify(TEXT("動作を終えてから補給しよう。"),TEXT("Finish your current action before taking supplies."),3.f);
    else if(Refilled==0)
        Notify(TEXT("矢と弾は満杯だ。"),TEXT("Your arrows and ammunition are already full."),3.f);
    else
    {
        Notify(TEXT("同盟の補給箱から矢と弾を補充した。"),TEXT("Arrows and ammunition replenished from the League cache."),4.f);
        Fire(TEXT("supply_restocked:")+Beat->SupplyPoint);
    }
    return true;
}
