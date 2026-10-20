#include "SoraEquipmentComponent.h"
#include "SoraBeatRules.h"
#include "SoraCatalog.h"
#include "SoraHistoricalArms.h"
#include "SoraPlayerCharacter.h"
#include "SoraSupplyRules.h"
#include "Engine/World.h"

int32 USoraEquipmentComponent::RestockUnlocked(unsigned Weapons)
{
    // A cache cannot cancel a reload, strike, draw, guard, step, stagger or
    // weapon cooldown. A fully sheathed blade remains exactly as it was.
    if(!Hero()->CanPlay()||bReloading||bCommittedStrike||bHistoricalRecovery||bBowDrawing||
        bFireHeld||bGuardHeld||bStepping||IsStaggered()||(bSheathed&&!IsSheathed())||
        GetWorld()->GetTimeSeconds()<NextShot) return -1;
    constexpr int32 Count=SoraBeatRules::WeaponCount;
    if(AmmoByWeapon.Num()!=Count) return -1;
    int Caps[Count]{};
    for(int32 Id=0;Id<Count;++Id)
        if(!SoraHistoricalArms::IsMelee(Id)) Caps[Id]=FSoraCatalog::Get().Weapon(Id).Magazine;
    return SoraSupplyRules::Restock(AmmoByWeapon.GetData(),Caps,Count,Weapons,Hero()->WeaponId,Ammo);
}
