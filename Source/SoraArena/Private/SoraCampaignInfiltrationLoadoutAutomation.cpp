#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraLiftAutomation.h"
#include "SoraEquipmentComponent.h"
#include "GameFramework/DamageType.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraInfiltrationLoadoutTest,"SoraArena.Campaign.InfiltrationLoadout",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraInfiltrationLoadoutTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    // Seeded beat checkpoints and frozen threats isolate carrying permission.
    // Moat/Climb automation separately tests real swimming and traversal.
    for(const int32 Beat:{0,1,2,4,7,9})
    {
        SoraFieldcraftAutomation::FBeatWorld W(*this,TEXT("InfiltrationLoadout"),5,Beat);
        if(!W.Start()) return false;
        W.Harden(); SoraLiftAutomation::HoldThreats(*W.World);
        auto* C=W.Campaign(); auto* Kit=W.Hero()->GetEquipment();
        TestTrue(TEXT("Earlier firearm and yari remain unlocked in inventory"),C->IsWeaponUnlocked(1)&&C->IsWeaponUnlocked(19));
        unsigned Allowed=(1u<<0)|(1u<<4);
        if(Beat>=2) Allowed|=1u<<18;
        if(Beat>=4) Allowed|=1u<<3;
        if(Beat>=6) Allowed|=1u<<13;
        if(Beat>=9) Allowed|=1u<<10;
        for(int32 Id=0;Id<SoraBeatRules::WeaponCount;++Id)
            TestEqual(*FString::Printf(TEXT("Beat %d permission for weapon %d"),Beat+1,Id),C->CanHold(Id,false),(Allowed&(1u<<Id))!=0u);
        TestFalse(TEXT("Earlier rifle cannot be selected on infiltration"),Kit->EquipCampaignWeapon(1));
        TestFalse(TEXT("Earlier yari cannot be selected on infiltration"),Kit->EquipCampaignWeapon(19));
        TestEqual(TEXT("Bow can be selected from b03 without a stringing input hold"),Kit->EquipCampaignWeapon(18),Beat>=2);
        TestFalse(TEXT("This chapter does not create a dry-well recovery"),C->NeedsEquipmentRecovery());
        if(Beat==2)
        {
            TestTrue(TEXT("The b03 bow is immediately ready before traversal"),C->ArmsReady(18,0.f,false));
            UGameplayStatics::ApplyDamage(W.Hero(),W.Hero()->Health+1000.f,nullptr,nullptr,UDamageType::StaticClass());
            if(!W.Tick(2)||!TestTrue(TEXT("Death offers retry"),W.Mode()->bDefeated)||!W.Press(EKeys::Enter)||!W.Tick(2)) return false;
            C=W.Campaign(); Kit=W.Hero()->GetEquipment();
            TestEqual(TEXT("Retry restores the b03 checkpoint"),C->ActiveBeat(),2);
            TestTrue(TEXT("Retry keeps the bow available without a new hold"),C->ArmsReady(18,0.f,false)&&Kit->EquipCampaignWeapon(18));
            TestFalse(TEXT("Retry does not reintroduce earlier firearms"),Kit->EquipCampaignWeapon(1));
        }
        if(Beat==4)
        {
            TestTrue(TEXT("Required b05 teaches the Needle during its handoff"),C->IsWeaponUnlocked(3)&&Kit->EquipCampaignWeapon(3));
            TestFalse(TEXT("The optional Phantom is not part of the Needle handoff"),C->IsWeaponUnlocked(13));
        }
        if(Beat==7)
        {
            TestTrue(TEXT("The mission may carry a found Phantom"),C->CanHold(13,false));
            TestFalse(TEXT("Permission does not grant the skipped optional cache"),C->IsWeaponUnlocked(13)||Kit->EquipCampaignWeapon(13));
            const auto Settle=[&]()
            {
                for(int32 Frame=0;Frame<1800;++Frame)
                {
                    SoraLiftAutomation::HoldThreats(*W.World);
                    if(W.Hero()->CanPlay()) return true;
                    if(W.Mode()->InputState()==SoraInput::Card)
                    { if(!W.Press(EKeys::Enter)) return false; }
                    else if(!W.Tick(1)) return false;
                }
                return TestTrue(TEXT("Authored dialogue releases normal input"),false);
            };
            if(!Settle()||!TestTrue(TEXT("The skipped b07 cache remains reachable"),C->AvailableCaches().Contains(6))) return false;
            W.Stand(C->CacheLocation(6)+FVector(180,0,0));
            if(!W.Tick(4)||!W.Press(EKeys::E)) return false;
            TestTrue(TEXT("Ordinary Interact completes the optional cache"),(C->Progress().CompletedMask&SoraBeatRules::BeatBit(6))!=0u);
            TestTrue(TEXT("Opening the cache unlocks and permits its Phantom"),C->IsWeaponUnlocked(13)&&Kit->EquipCampaignWeapon(13));
            TestTrue(TEXT("Replay chapter selection is available"),C->SelectChapter(5));
            W.Mode()->ResetRound();
            C=W.Campaign(); Kit=W.Hero()->GetEquipment();
            TestEqual(TEXT("Chapter selection returns to b01"),C->ActiveBeat(),0);
            TestEqual(TEXT("A forbidden held weapon is replaced by the mission katana"),W.Hero()->WeaponId,0);
            TestFalse(TEXT("Chapter selection restores the unstrung bow restriction"),C->CanHold(18,false)||Kit->EquipCampaignWeapon(18));
            TestFalse(TEXT("Chapter selection does not grant the future optional SMG"),C->IsWeaponUnlocked(13)||Kit->EquipCampaignWeapon(13));
        }
        if(Beat==9)
            TestTrue(TEXT("The b10 pledge permits the authored tanto"),C->IsWeaponUnlocked(10)&&Kit->EquipCampaignWeapon(10));
    }
    return !HasAnyErrors();
}
#endif
