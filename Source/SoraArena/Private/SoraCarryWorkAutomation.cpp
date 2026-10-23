#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraCarryAutomation.h"
#include "SoraEnemy.h"
#include "SoraEquipmentComponent.h"
#include "SoraSaveGame.h"
#include "SoraSettings.h"
#include "SoraWorldBuilder.h"
#include "EngineUtils.h"
#include "GameFramework/DamageType.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/AutomationTest.h"
#include "Misc/ScopeExit.h"
#include "Templates/UniquePtr.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraCarryWorkTest,"SoraArena.Campaign.CarrySealAndSetDown",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraCarryWorkTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    const FString Slot=FSoraAutomationWorld::UniqueSaveSlot(TEXT("CarryWork"));
    FSoraAutomationWorld::IgnoreMissingGeneratedArt(*this);
    FSoraAutomationWorld::IgnoreAbsentSaveSlot(*this,Slot);
    TUniquePtr<FSoraAutomationWorld> World;
    const auto Destroy=[&]() { if(World) { World->DestroyTestWorld(true); World->ForwardErrorMessages(this); World.Reset(); } };
    ON_SCOPE_EXIT { Destroy(); FSoraAutomationWorld::DeleteSaveSlot(Slot); };
    const auto HoldOpponents=[&]() {
        for(TActorIterator<ASoraEnemy> It(World->GetTestWorld());It;++It)
        {
            It->SetActorTickEnabled(false); It->GetCharacterMovement()->SetComponentTickEnabled(false);
            if(auto* Brain=It->GetController()) Brain->SetActorTickEnabled(false);
        }
    };
    const auto Start=[&]() {
        World=MakeUnique<FSoraAutomationWorld>();
        if(!World->Start(Slot)) return false;
        World->Mode()->Settings()->SetCampaignDifficulty(SoraAccessibility::EDifficulty::Hard);
        if(!World->Tick(1)||!World->EnableKeyInput()||!World->PressKey(EKeys::Enter)||!World->PressKey(EKeys::Enter)||!World->Mode()->IsPlaying()) return false;
        HoldOpponents(); return World->Mode()->Campaign()->ActiveBeat()==4;
    };
    auto* Save=NewObject<USoraSaveGame>();
    if(!USoraCampaignDirector::SeedCheckpoint(*Save,1,4)||!UGameplayStatics::SaveGameToSlot(Save,Slot,0)||!Start()) return false;
    auto* Campaign=World->Mode()->Campaign();
    auto* Hero=World->Player();
    const FVector Store(Campaign->ActiveSpace()->Pickups[0],Hero->GetActorLocation().Z);
    const auto Walk=[&](FVector At) { At.Z=World->Player()->GetActorLocation().Z;
        return FVector::Dist2D(World->Player()->GetActorLocation(),At)<=30.f||SoraRecoveryAutomation::WalkTo(*World,At); };
    if(!TestTrue(TEXT("Normal movement reaches the sealed store"),Walk(Store))||!World->InjectKey(EKeys::E,IE_Pressed)||!World->Tick(80)) return false;
    TestTrue(TEXT("Holding Interact starts the seal pry"),Campaign->IsPryingCarryGate());
    TestEqual(TEXT("The yari is used to pry its seal"),Hero->WeaponId,19);
    TestFalse(TEXT("A partial pry cannot pick up rice"),Campaign->TaskProgress().Carrying);
    TestFalse(TEXT("Prying occupies the weapon"),Campaign->ArmsReady(19,0,false));
    TestTrue(TEXT("First contact raises the authored notice bark"),Campaign->QueuedSubtitles().ContainsByPredicate(
        [](const FSoraSubtitle& S) { return S.LineId==TEXT("ch02.b05.system.002"); }));
    const int32 BeforeHit=Campaign->TaskProgress().CarryGateHeldMs;
    const float BeforeHealth=Hero->Health;
    UGameplayStatics::ApplyDamage(Hero,10.f,nullptr,nullptr,UDamageType::StaticClass());
    if(!World->Tick(1)) return false;
    TestTrue(TEXT("The pry is interrupted by real damage"),Hero->Health<BeforeHealth);
    TestEqual(TEXT("Hit pauses without erasing seal work"),Campaign->TaskProgress().CarryGateHeldMs,BeforeHit);
    if(!World->InjectKey(EKeys::E,IE_Released)||!World->Tick(2)) return false;
    const int32 Paused=Campaign->TaskProgress().CarryGateHeldMs;
    if(!Walk(Store+FVector(500,0,0))||!World->Tick(60)) return false;
    TestEqual(TEXT("Releasing and leaving preserve partial seal work"),Campaign->TaskProgress().CarryGateHeldMs,Paused);
    if(!TestTrue(TEXT("Returning and holding finishes the three-second pry"),SoraCarryAutomation::PrySeal(*World))) return false;
    TestEqual(TEXT("Exactly the authored work duration opens the seal"),Campaign->TaskProgress().CarryGateHeldMs,3000);
    TestFalse(TEXT("Finishing the pry does not silently pick up rice"),Campaign->TaskProgress().Carrying);
    if(!World->PressKey(EKeys::E)||!TestTrue(TEXT("A new Interact picks up a bale"),Campaign->TaskProgress().Carrying)) return false;
    const FVector First=Store+FVector(500,0,0);
    if(!Walk(First)||!World->PressKey(EKeys::E)||!World->Tick(2)) return false;
    TestFalse(TEXT("Manual set-down frees the player's hands"),Campaign->TaskProgress().Carrying);
    TestTrue(TEXT("Setting down restores bow availability"),Campaign->CanHold(18,false));
    TestEqual(TEXT("Set-down does not deliver"),Campaign->TaskProgress().Done,0);
    TestEqual(TEXT("A loose bale is visible on the floor"),World->Mode()->Arena()->LooseLoadVisualCount(),1);
    TestTrue(TEXT("The loose bale remains where the player set it down"),FVector::Dist2D(Campaign->LooseLoadLocation(0),Hero->GetActorLocation())<1.f);
    if(!World->PressKey(EKeys::E)||!TestTrue(TEXT("The same loose bale can be recovered"),Campaign->TaskProgress().Carrying)) return false;
    UGameplayStatics::ApplyDamage(Hero,10.f,nullptr,nullptr,UDamageType::StaticClass());
    if(!World->Tick(2)) return false;
    TestFalse(TEXT("A recovered loose bale still drops on a Hard hit"),Campaign->TaskProgress().Carrying);
    TestEqual(TEXT("Losing a recovered bale leaves no duplicate floor visual"),World->Mode()->Arena()->LooseLoadVisualCount(),0);
    // Take every remaining physical bale from the store, leaving each at a
    // separate reachable point. The fifth source pickup must be refused.
    for(int32 Load=0;Load<4;++Load)
    {
        if(!Walk(Store)||!World->PressKey(EKeys::E)||!TestTrue(TEXT("Undelivered stock remains available"),Campaign->TaskProgress().Carrying)||
            !Walk(Store+FVector(500*(Load+1),0,0))||!World->PressKey(EKeys::E)||!World->Tick(2)) return false;
        TestEqual(TEXT("Each set-down conserves exactly one bale"),SoraBeatRules::Bits(Campaign->TaskProgress().LooseLoads),Load+1);
    }
    if(!Walk(Store)||!World->PressKey(EKeys::E)) return false;
    TestFalse(TEXT("Four loose bales exhaust the store"),Campaign->TaskProgress().Carrying);
    TestEqual(TEXT("Only four loose bales are drawn"),World->Mode()->Arena()->LooseLoadVisualCount(),4);
    if(!Walk(First)||!World->PressKey(EKeys::E)||!Walk(FVector(Campaign->ActiveSpace()->Dropoffs[0],Hero->GetActorLocation().Z))||
        !World->PressKey(EKeys::E)||!World->Tick(2)) return false;
    TestEqual(TEXT("A recovered bale delivers once at the horse"),Campaign->TaskProgress().Done,1);
    TestEqual(TEXT("The remaining loose bales are still present"),SoraBeatRules::Bits(Campaign->TaskProgress().LooseLoads),3);
    if(!Walk(Store)||!World->PressKey(EKeys::E)) return false;
    TestFalse(TEXT("A delivery does not create replacement stock"),Campaign->TaskProgress().Carrying);
    UGameplayStatics::ApplyDamage(Hero,Hero->Health+1000.f,nullptr,nullptr,UDamageType::StaticClass());
    if(!World->Tick(2)||!World->Mode()->bDefeated||!World->PressKey(EKeys::Enter)||!World->Tick(30)) return false;
    HoldOpponents();
    TestTrue(TEXT("Death retry seals the store again"),Campaign->NeedsCarryGate());
    TestEqual(TEXT("Retry clears partial seal work"),Campaign->TaskProgress().CarryGateHeldMs,0);
    TestEqual(TEXT("Retry clears delivered and loose cargo"),Campaign->TaskProgress().Done+SoraBeatRules::Bits(Campaign->TaskProgress().LooseLoads),0);
    TestEqual(TEXT("Retry removes old loose visuals"),World->Mode()->Arena()->LooseLoadVisualCount(),0);
    if(!SoraCarryAutomation::PrySeal(*World)||!World->PressKey(EKeys::E)||!Walk(First)||!World->PressKey(EKeys::E)) return false;
    TestEqual(TEXT("Reload fixture contains a real loose bale"),SoraBeatRules::Bits(Campaign->TaskProgress().LooseLoads),1);
    Destroy();
    if(!Start()) return false;
    Campaign=World->Mode()->Campaign();
    TestTrue(TEXT("Fresh-world checkpoint reload seals the store again"),Campaign->NeedsCarryGate());
    TestEqual(TEXT("Reload restores zero partial or delivered cargo"),Campaign->TaskProgress().Done+SoraBeatRules::Bits(Campaign->TaskProgress().LooseLoads),0);
    TestFalse(TEXT("Reload is not carrying an old bale"),Campaign->TaskProgress().Carrying);
    return !HasAnyErrors();
}
#endif
