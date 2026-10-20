#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraEquipmentComponent.h"
#include "SoraGameMode.h"
#include "SoraFrontEnd.h"
#include "SoraPlayerCharacter.h"
#include "SoraWorldBuilder.h"

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
