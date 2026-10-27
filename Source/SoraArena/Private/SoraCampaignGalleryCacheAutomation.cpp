#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraGalleryRules.h"
#include "SoraLiftAutomation.h"
#include "SoraEquipmentComponent.h"
#include "GameFramework/DamageType.h"
#include "GameFramework/InputSettings.h"
#include "Misc/ScopeExit.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraGalleryCacheTest,"SoraArena.Campaign.GalleryCache",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraGalleryCacheTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    const auto& Gallery=FSoraCatalog::Get().Chapter(7).Beats[11];
    TestEqual(TEXT("The catalog retains the declared twelve-arrow pickup"),Gallery.GalleryArrowReward,12);
    const auto GlobalActions=GetDefault<UInputSettings>()->GetActionMappings();
    FString Controls;
    ON_SCOPE_EXIT
    {
        TestTrue(TEXT("Cache fixture preserves global action mappings"),GetDefault<UInputSettings>()->GetActionMappings()==GlobalActions);
        if(!Controls.IsEmpty()) TestFalse(TEXT("Cache fixture deletes its rebound profile"),UGameplayStatics::DoesSaveGameExist(Controls,0));
    };
    // Empty held quiver; legacy finds with a partly spent stowed quiver;
    // fully stocked held quiver. Every claim uses actual mapped Interact.
    for(int32 Case=0;Case<3;++Case)
    {
        SoraFieldcraftAutomation::FBeatWorld W(*this,TEXT("GalleryCache"),7,10);
        Controls=FSoraAutomationWorld::ControlSlot(W.Slot);
        const bool Legacy=Case==1;
        if(!W.Start(Legacy?SoraGalleryRules::CacheFinds:0)||!W.Tick(30)) return false;
        W.Harden();
        if(!TestTrue(TEXT("Normal capstan input reaches the gallery"),SoraLiftAutomation::Ride(*W.World)&&
            SoraLiftAutomation::GalleryFloor(*W.World))) return false;
        auto* Kit=W.Hero()->GetEquipment();
        if(!Kit->EquipCampaignWeapon(Legacy?0:18)||!W.Tick(30)) return false;
        if(Legacy)
        {
            Kit->Sheathe(true);
            if(!W.Tick(100)||!TestTrue(TEXT("The stowed-bow case holds a fully sheathed katana"),Kit->IsSheathed())) return false;
            Kit->AmmoByWeapon[18]=4;
        }
        else Kit->Ammo=Case==0?1:12;
        // An unrelated weapon is spent so an accidental whole-loadout refill
        // cannot pass merely because all other magazines began full.
        Kit->AmmoByWeapon[1]=1;
        const FVector Approach=W.Mode()->Arena()->CampaignLift()->GalleryCache()+FVector(-150,0,0);
        if(!TestTrue(TEXT("Normal walking reaches the cache"),SoraLiftAutomation::Walk(*W.World,Approach))) return false;
        const auto Lines=[&](const TCHAR* Id)
        {
            return W.Campaign()->QueuedSubtitles().FilterByPredicate(
                [&](const FSoraSubtitle& Line) { return Line.LineId==Id; }).Num();
        };
        const auto ExpectLines=[&](int32 Count)
        {
            TestEqual(TEXT("Exact Washio return line count"),Lines(TEXT("ch08.b12.nyaakoto.003")),Count);
            TestEqual(TEXT("Exact Sekireisai life-giving-sword memory count"),Lines(TEXT("ch08.b12.sekireisai.004")),Count);
        };
        TestFalse(TEXT("Arrival never claims the bundle"),W.Campaign()->GalleryArrowsClaimed());
        ExpectLines(0);
        FKey Use=EKeys::E;
        if(Case==0)
        {
            if(!W.Press(EKeys::Escape)||!W.Hero()->RemapCombatAction(TEXT("Interact"),EKeys::G)||
                !W.Press(EKeys::G)||!TestFalse(TEXT("Menu input cannot claim arrows"),W.Campaign()->GalleryArrowsClaimed())) return false;
            W.Mode()->ResumePlay(); Use=EKeys::G;
            if(!W.Tick(3)||!W.Press(EKeys::E)||!TestFalse(TEXT("The former Interact binding cannot open the cache"),
                W.Campaign()->GalleryArrowsClaimed())) return false;
            if(!W.World->InjectKey(EKeys::LeftMouseButton,IE_Pressed)||!W.Tick(10)||
                !TestTrue(TEXT("Mapped Fire starts a real bow draw"),Kit->IsBowDrawing())||!W.Press(Use)) return false;
            TestTrue(TEXT("Busy interaction preserves the live draw and leaves the cache unclaimed"),
                Kit->IsBowDrawing()&&Kit->Ammo==1&&!W.Campaign()->GalleryArrowsClaimed()&&
                (W.Campaign()->Progress().CompletedMask&SoraBeatRules::BeatBit(11))==0);
            TestEqual(TEXT("Busy input does not grant collectibles"),W.Campaign()->CollectedMask(),uint64(0));
            ExpectLines(0);
            if(!W.Tick(40)||!TestEqual(TEXT("The held shot reaches the authored full draw"),Kit->BowDrawProgress(),1.f)||
                !W.World->InjectKey(EKeys::LeftMouseButton,IE_Released)||!W.Tick(90)||
                !TestEqual(TEXT("The real shot spends the final arrow"),Kit->Ammo,0)) return false;
            Kit->AmmoByWeapon[18]=12; // held Ammo is authoritative after shooting
        }
        const auto Before=W.Campaign()->Progress();
        const auto Inventory=Kit->AmmoByWeapon;
        const int32 Held=W.Hero()->WeaponId,LiveAmmo=Kit->Ammo;
        const float Health=W.Hero()->Health;
        if(!W.Press(Use)||!TestTrue(TEXT("Mapped input claims the authored bundle"),W.Campaign()->GalleryArrowsClaimed())) return false;
        TestEqual(TEXT("Only the bow magazine receives twelve capped arrows"),Kit->AmmoByWeapon[18],12);
        TestEqual(TEXT("The held count changes only when holding the bow"),Kit->Ammo,Held==18?12:LiveAmmo);
        for(int32 Id=0;Id<Inventory.Num();++Id)
            if(Id!=18) TestEqual(*FString::Printf(TEXT("Other inventory slot %d is preserved"),Id),Kit->AmmoByWeapon[Id],Inventory[Id]);
        TestEqual(TEXT("The held weapon is unchanged"),W.Hero()->WeaponId,Held);
        TestEqual(TEXT("The pickup grants no healing"),W.Hero()->Health,Health);
        TestEqual(TEXT("The pickup grants no weapon unlock"),W.Campaign()->Progress().WeaponsMask,Before.WeaponsMask);
        TestEqual(TEXT("The cache grants precisely its three collectibles"),W.Campaign()->CollectedMask(),uint64(SoraGalleryRules::CacheFinds));
        TestEqual(TEXT("Cache input never discovers either independent lore object"),W.Campaign()->GalleryPoiMask(),0);
        if(Legacy) TestTrue(TEXT("A stowed refill preserves the fully sheathed katana"),Kit->IsSheathed());
        ExpectLines(Legacy?0:1);
        auto* Saved=Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(W.Slot,0));
        if(!TestNotNull(TEXT("The bundle claim reaches disk immediately"),Saved)) return false;
        TestTrue(TEXT("The claim and finds save together without moving the lift checkpoint"),
            Saved->GalleryArrowsClaimed&&uint64(Saved->Collectibles)==SoraGalleryRules::CacheFinds&&
            Saved->CheckpointBeat==10&&(Saved->CheckpointBeatsMask&SoraBeatRules::BeatBit(11))==0);
        // Spending after a claim must not turn this finite bundle into the
        // separate unlimited L1 supply point, even when first used at full.
        if(Held==18) Kit->Ammo=5; else Kit->AmmoByWeapon[18]=5;
        if(!W.Press(Use)) return false;
        TestEqual(TEXT("Repeated input cannot replenish a spent quiver"),Held==18?Kit->Ammo:Kit->AmmoByWeapon[18],5);
        ExpectLines(Legacy?0:1);
        if(Case!=0) continue;
        UGameplayStatics::ApplyDamage(W.Hero(),W.Hero()->Health+1000.f,nullptr,nullptr,UDamageType::StaticClass());
        if(!W.Tick(2)||!TestTrue(TEXT("Death offers ordinary retry"),W.Mode()->bDefeated)||!W.Press(EKeys::Enter)||!W.Tick(30)) return false;
        TestTrue(TEXT("Retry retains the claim while restoring the lower lift checkpoint"),
            W.Campaign()->GalleryArrowsClaimed()&&W.Campaign()->ActiveBeat()==10&&!W.Campaign()->InLiftGallery());
        TestEqual(TEXT("Retry keeps the exact three finds"),W.Campaign()->CollectedMask(),uint64(SoraGalleryRules::CacheFinds));
        ExpectLines(0);
        W.Fieldcraft()->OnEvent.Remove(W.EventsHandle);
        if(!W.World->DestroyTestWorld(true)) return false;
        W.World->ForwardErrorMessages(this); W.World.Reset();
        W.World=MakeUnique<FSoraAutomationWorld>();
        if(!W.World->Start(W.Slot)||!W.Tick(1)||!W.World->EnableKeyInput()||
            !W.Press(EKeys::Enter)||!W.Press(EKeys::Enter)||!W.Press(EKeys::Enter)||!W.Tick(30)) return false;
        W.Harden();
        if(!TestTrue(TEXT("Fresh-world load preserves the saved claim"),W.Campaign()->GalleryArrowsClaimed())||
            !SoraLiftAutomation::Ride(*W.World,Use)||!SoraLiftAutomation::GalleryFloor(*W.World)) return false;
        Kit=W.Hero()->GetEquipment();
        if(!Kit->EquipCampaignWeapon(18)||!W.Tick(30)||!SoraLiftAutomation::Walk(*W.World,Approach)) return false;
        Kit->Ammo=3;
        if(!W.Press(Use)) return false;
        TestEqual(TEXT("Reopening after load does not award the finite arrows again"),Kit->Ammo,3);
        TestTrue(TEXT("Reopening after load can still complete optional exploration"),
            (W.Campaign()->Progress().CompletedMask&SoraBeatRules::BeatBit(11))!=0);
        ExpectLines(0);
        if(!TestTrue(TEXT("Earlier chapter replay remains available"),W.Campaign()->SelectChapter(0))) return false;
        TestTrue(TEXT("Replay retains the claimed bundle"),W.Campaign()->GalleryArrowsClaimed());
        W.Campaign()->StartOver();
        TestFalse(TEXT("New Campaign clears the claim"),W.Campaign()->GalleryArrowsClaimed());
        Saved=Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(W.Slot,0));
        if(!TestNotNull(TEXT("New Campaign writes its reset"),Saved)) return false;
        TestTrue(TEXT("The reset clears both claim and finds on disk"),!Saved->GalleryArrowsClaimed&&Saved->Collectibles==0);
    }
    return !HasAnyErrors();
}
#endif
