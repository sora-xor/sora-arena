#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraLiftAutomation.h"
#include "SoraEquipmentComponent.h"
#include "SoraCampaignRules.h"
#include "GameFramework/DamageType.h"
#include "GameFramework/InputSettings.h"
#include "Misc/ScopeExit.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraCacheArrowsTest,"SoraArena.Campaign.CacheArrows",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraCacheArrowsTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    const auto GlobalActions=GetDefault<UInputSettings>()->GetActionMappings();
    const auto GlobalAxes=GetDefault<UInputSettings>()->GetAxisMappings();
    TArray<FString> ControlSlots;
    ON_SCOPE_EXIT
    {
        TestTrue(TEXT("Cache fixture preserves global action mappings"),GetDefault<UInputSettings>()->GetActionMappings()==GlobalActions);
        TestTrue(TEXT("Cache fixture preserves global axes"),GetDefault<UInputSettings>()->GetAxisMappings()==GlobalAxes);
        for(const auto& Slot:ControlSlots)
            TestFalse(TEXT("Cache fixture deletes its isolated profile"),UGameplayStatics::DoesSaveGameExist(Slot,0));
    };
    // Every target cache: actually issued reward, stowed bow, full quiver,
    // and a restored already-collected cache. Placement and frozen threats
    // isolate reward delivery; this is not ordinary campaign traversal.
    struct FCase { int32 Chapter,Cache,Amount; bool Refill; };
    const FCase Caches[]={{1,13,12,true},{3,8,6,false},{4,12,12,false},{5,6,6,false},{6,4,12,false}};
    for(const auto& Row:Caches) for(int32 Case=0;Case<4;++Case)
    {
        const auto& Chapter=FSoraCatalog::Get().Chapter(Row.Chapter);
        const auto& Cache=Chapter.Beats[Row.Cache];
        AddInfo(FString::Printf(TEXT("Cache arrow case: %s, inventory case %d"),*Cache.Id,Case));
        TestEqual(TEXT("Catalog preserves arrow amount"),Cache.CacheArrows.Amount,Row.Amount);
        TestEqual(TEXT("Catalog distinguishes refill from additions"),Cache.CacheArrows.Refill,Row.Refill);
        unsigned long long Finds=0;
        for(const int32 Item:Cache.Rewards)
            Finds|=SoraCampaignRules::CollectibleBit(Row.Chapter,Chapter.Collectibles[Item].MaskBit);
        if(!TestTrue(TEXT("The cache has exclusive durable finds"),Finds!=0)) return false;
        SoraFieldcraftAutomation::FBeatWorld W(*this,TEXT("CacheArrows"),Row.Chapter,Row.Cache+1);
        ControlSlots.Add(FSoraAutomationWorld::ControlSlot(W.Slot));
        if(!W.Start(Case==3?static_cast<int64>(Finds):0)) return false;
        const auto Settle=[&]()
        {
            W.Harden();
            for(int32 Frame=0;Frame<1800;++Frame)
            {
                SoraLiftAutomation::HoldThreats(*W.World);
                if(W.Hero()->CanPlay()) return W.Tick(30);
                if(W.Mode()->InputState()==SoraInput::Card)
                {
                    if(!W.Press(EKeys::Enter)) return false;
                }
                else if(!W.Tick(1)) return false;
            }
            return TestTrue(TEXT("Authored card/dialogue releases ordinary input"),false);
        };
        if(!Settle()) return false;
        auto* Kit=W.Hero()->GetEquipment();
        const bool Stowed=Case==1;
        if(!Kit->EquipCampaignWeapon(Stowed?0:18)||!W.Tick(30)) return false;
        if(Stowed)
        {
            Kit->Sheathe(true);
            if(!W.Tick(100)||!TestTrue(TEXT("Stowed reward preserves a sheathed katana"),Kit->IsSheathed())) return false;
        }
        const int32 Initial=Case==2?12:Case==0?1:2;
        Kit->AmmoByWeapon[18]=Stowed?Initial:12; // stale copy after held-bow spending
        if(!Stowed) Kit->Ammo=Initial;
        Kit->AmmoByWeapon[1]=1; // unrelated ammunition must not be replenished
        const FVector CacheAt=W.Campaign()->CacheLocation(Row.Cache);
        W.Stand(CacheAt+FVector(600,0,0));
        if(!W.Tick(4)||!W.Press(EKeys::E)) return false;
        TestEqual(TEXT("Distant input cannot complete a cache"),W.Campaign()->Progress().CompletedMask&SoraBeatRules::BeatBit(Row.Cache),0u);
        TestEqual(TEXT("Distant input cannot grant arrows"),Stowed?Kit->AmmoByWeapon[18]:Kit->Ammo,Initial);
        W.Stand(CacheAt+FVector(180,0,0));
        if(!W.Tick(4)) return false;
        FKey Use=EKeys::E;
        if(Case==0)
        {
            if(!W.Press(EKeys::Escape)||!W.Hero()->RemapCombatAction(TEXT("Interact"),EKeys::G)||!W.Press(EKeys::G)) return false;
            TestEqual(TEXT("Menu input leaves the cache uncollected"),W.Campaign()->CollectedMask(),uint64(0));
            W.Mode()->ResumePlay(); Use=EKeys::G;
            if(!W.Tick(3)||!W.Press(EKeys::E)) return false;
            TestEqual(TEXT("The former binding cannot collect the cache"),W.Campaign()->CollectedMask(),uint64(0));
            if(!W.World->InjectKey(EKeys::LeftMouseButton,IE_Pressed)||!W.Tick(10)||
                !TestTrue(TEXT("Mapped Fire begins a real draw"),Kit->IsBowDrawing())||!W.Press(Use)) return false;
            TestTrue(TEXT("Busy reward refusal preserves draw and inventory"),Kit->IsBowDrawing()&&Kit->Ammo==1);
            TestEqual(TEXT("Busy refusal cannot collect finds"),W.Campaign()->CollectedMask(),uint64(0));
            TestEqual(TEXT("Busy refusal cannot complete exploration"),W.Campaign()->Progress().CompletedMask&SoraBeatRules::BeatBit(Row.Cache),0u);
            if(!W.Tick(40)||!W.World->InjectKey(EKeys::LeftMouseButton,IE_Released)||!W.Tick(90)||
                !TestEqual(TEXT("Actual release spends the held arrow"),Kit->Ammo,0)) return false;
        }
        const int32 Before=Stowed?Kit->AmmoByWeapon[18]:Kit->Ammo;
        const int32 Expected=Case==3?Before:Row.Refill?FMath::Max(Before,Row.Amount):FMath::Min(12,Before+Row.Amount);
        const int32 Held=W.Hero()->WeaponId,Live=Kit->Ammo;
        const auto Inventory=Kit->AmmoByWeapon;
        const unsigned Weapons=W.Campaign()->Progress().WeaponsMask;
        if(!W.Press(Use)) return false;
        TestEqual(TEXT("Mapped Interact awards exactly the authored arrow reward"),Stowed?Kit->AmmoByWeapon[18]:Kit->Ammo,Expected);
        TestEqual(TEXT("The finite reward changes no held weapon"),W.Hero()->WeaponId,Held);
        TestEqual(TEXT("A stowed reward preserves held ammunition"),Kit->Ammo,Stowed?Live:Expected);
        for(int32 Id=0;Id<Inventory.Num();++Id)
            if(Id!=18) TestEqual(TEXT("Other ammunition remains unchanged"),Kit->AmmoByWeapon[Id],Inventory[Id]);
        if(Stowed) TestTrue(TEXT("The katana remains sheathed"),Kit->IsSheathed());
        const unsigned ExpectedWeapons=Weapons|Chapter.Rules[Row.Cache].WeaponsMask;
        TestEqual(TEXT("Only the cache's preexisting weapon unlock is granted"),W.Campaign()->Progress().WeaponsMask,ExpectedWeapons);
        TestTrue(TEXT("The optional cache completes once"),(W.Campaign()->Progress().CompletedMask&SoraBeatRules::BeatBit(Row.Cache))!=0);
        TestEqual(TEXT("Finds persist at the reward acceptance point"),W.Campaign()->CollectedMask(),uint64(Finds));
        auto* Saved=Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(W.Slot,0));
        if(!TestNotNull(TEXT("The accepted cache saves immediately"),Saved)) return false;
        TestEqual(TEXT("Disk retains the same finite claim through its existing finds"),uint64(Saved->Collectibles),uint64(Finds));
        if(Stowed) Kit->AmmoByWeapon[18]=1; else Kit->Ammo=1;
        if(!W.Press(Use)) return false;
        TestEqual(TEXT("Repeated input never replenishes a consumed bundle"),Stowed?Kit->AmmoByWeapon[18]:Kit->Ammo,1);
        if(Case!=0) continue;
        UGameplayStatics::ApplyDamage(W.Hero(),W.Hero()->Health+1000.f,nullptr,nullptr,UDamageType::StaticClass());
        if(!W.Tick(2)||!TestTrue(TEXT("Death offers retry"),W.Mode()->bDefeated)||!W.Press(EKeys::Enter)||!Settle()) return false;
        TestEqual(TEXT("Retry retains the existing durable claim"),W.Campaign()->CollectedMask(),uint64(Finds));
        Kit=W.Hero()->GetEquipment();
        TestEqual(TEXT("Retry keeps the existing full-quiver checkpoint contract"),Kit->AmmoByWeapon[18],12);
        if(!Kit->EquipCampaignWeapon(18)||!W.Tick(30)) return false;
        Kit->Ammo=2; W.Stand(CacheAt+FVector(180,0,0));
        if(!W.Tick(4)||!W.Press(Use)) return false;
        TestEqual(TEXT("Retry cannot issue a second bundle"),Kit->Ammo,2);
        W.Fieldcraft()->OnEvent.Remove(W.EventsHandle);
        if(!W.World->DestroyTestWorld(true)) return false;
        W.World->ForwardErrorMessages(this); W.World.Reset();
        W.EventsHandle.Reset();
        W.World=MakeUnique<FSoraAutomationWorld>();
        if(!W.World->Start(W.Slot)||!W.Tick(1)||!W.World->EnableKeyInput()||
            !W.Press(EKeys::Enter)||!W.Press(EKeys::Enter)||!W.Press(EKeys::Enter)||!Settle()) return false;
        TestEqual(TEXT("Fresh-world load retains the finite claim"),W.Campaign()->CollectedMask(),uint64(Finds));
        Kit=W.Hero()->GetEquipment();
        TestEqual(TEXT("Fresh-world load keeps the existing full-quiver reset"),Kit->AmmoByWeapon[18],12);
        if(!Kit->EquipCampaignWeapon(18)||!W.Tick(30)) return false;
        Kit->Ammo=3; W.Stand(CacheAt+FVector(180,0,0));
        if(!W.Tick(4)||!W.Press(Use)) return false;
        TestEqual(TEXT("Fresh-world input cannot regrant arrows"),Kit->Ammo,3);
        if(!TestTrue(TEXT("Chapter replay remains available"),W.Campaign()->SelectChapter(0))) return false;
        TestEqual(TEXT("Chapter replay retains the durable cache finds"),W.Campaign()->CollectedMask(),uint64(Finds));
        W.Campaign()->StartOver();
        TestEqual(TEXT("New Campaign resets the same canonical finds"),W.Campaign()->CollectedMask(),uint64(0));
        Saved=Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(W.Slot,0));
        if(!TestNotNull(TEXT("New Campaign writes its reset"),Saved)) return false;
        TestEqual(TEXT("No separate arrow claim survives New Campaign"),Saved->Collectibles,int64(0));
    }
    return !HasAnyErrors();
}
#endif
