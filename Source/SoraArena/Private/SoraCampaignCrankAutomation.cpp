#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraRecoveryAutomation.h"
#include "SoraLiftAutomation.h"
#include "SoraCompanion.h"
#include "SoraEnemy.h"
#include "SoraEquipmentComponent.h"
#include "SoraSettings.h"
#include "SoraViewmodelComponent.h"
#include "Components/StaticMeshComponent.h"
#include "EngineUtils.h"
#include "GameFramework/DamageType.h"
#include "Misc/AutomationTest.h"

namespace SoraCrankAutomation
{
using SoraFieldcraftAutomation::FBeatWorld;
ASoraCompanion* Helper(const FBeatWorld& W)
{
    for(const auto& Person:W.Fieldcraft()->PeopleInPlay())
        if(IsValid(Person)&&Person->CompanionId()==W.BeatData().CrankNpcs[0]) return Person;
    return nullptr;
}
FVector Anchor(const FBeatWorld& W) { return FVector(W.BeatData().Space.Anchor,W.Hero()->GetActorLocation().Z); }
bool Walk(FBeatWorld& W,const FVector& To)
{
    return W.Mode()->Arena()->CampaignLift()?SoraLiftAutomation::Walk(*W.World,To):SoraRecoveryAutomation::WalkTo(*W.World,To);
}
bool Ready(FBeatWorld& W)
{
    if(!W.Test.TestTrue(TEXT("The offline catalog loads before seeding a checkpoint"),FSoraCatalog::Get().Load())) return false;
    const auto& Chapter=FSoraCatalog::Get().Chapter(W.Chapter);
    if(!W.Test.TestTrue(TEXT("The crank starts at its authored checkpoint"),
        Chapter.Rules.IsValidIndex(W.Beat)&&Chapter.Rules[W.Beat].Checkpoint)) return false;
    if(!W.Start()) return false;
    W.Harden();
    for(int32 Frame=0;Frame<1800&&!W.Mode()->IsPlaying();++Frame) if(!W.Tick(1)) return false;
    return W.Mode()->IsPlaying()&&Walk(W,Anchor(W)+FVector(-180,0,0));
}
void Freeze(ASoraEnemy& Enemy)
{
    Enemy.SetActorTickEnabled(false);
    Enemy.GetCharacterMovement()->StopMovementImmediately();
    Enemy.GetCharacterMovement()->SetComponentTickEnabled(false);
    if(AController* Brain=Enemy.GetController()) Brain->SetActorTickEnabled(false);
}
bool PlayerTurn(FBeatWorld& W)
{
    if(!W.Campaign()->ActiveTask().AlternateTreads)
        return W.World->InjectKey(EKeys::E,IE_Pressed)&&W.World->InjectKey(EKeys::E,IE_Released);
    return W.World->InjectKey(EKeys::E,IE_Pressed)&&W.World->InjectKey(EKeys::A,IE_Pressed)&&
        W.World->InjectKey(EKeys::A,IE_Released)&&W.World->InjectKey(EKeys::D,IE_Pressed)&&
        W.World->InjectKey(EKeys::D,IE_Released)&&W.World->InjectKey(EKeys::E,IE_Released);
}
bool Turns(FBeatWorld& W,int32 Count,bool bFreeze=false)
{
    const int32 Frames=FMath::CeilToInt(W.Campaign()->ActiveTask().MinTurnMs*60.f/1000.f)+2;
    for(int32 Turn=0;Turn<Count;++Turn)
    {
        if(!W.Tick(Frames)||!PlayerTurn(W)) return false;
        if(bFreeze) for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It) SoraCrankAutomation::Freeze(**It);
    }
    return true;
}
bool Reload(FBeatWorld& W)
{
    W.Fieldcraft()->OnEvent.Remove(W.EventsHandle);
    W.World->DestroyTestWorld(true); W.World->ForwardErrorMessages(&W.Test); W.World.Reset();
    W.World=MakeUnique<FSoraAutomationWorld>();
    if(!W.World->Start(W.Slot)||!W.World->Tick(1)||!W.World->EnableKeyInput()||
        !W.Press(EKeys::Enter)||!W.Press(EKeys::Enter)||!W.Press(EKeys::Enter)) return false;
    W.EventsHandle=W.Fieldcraft()->OnEvent.AddLambda([&W](FName Event) { W.Events.Add(Event.ToString()); });
    for(int32 Frame=0;Frame<1800&&!W.Mode()->IsPlaying();++Frame) if(!W.Tick(1)) return false;
    W.Harden();
    return W.Mode()->IsPlaying();
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraCrankCooperationTest,"SoraArena.Campaign.CrankCooperation",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraCrankCooperationTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraCrankAutomation;
    FBeatWorld W(*this,TEXT("CrankOtane"),3,5);
    if(!Ready(W)||!TestNotNull(TEXT("Otane stands at the winch"),Helper(W))) return false;
    if(!W.Tick(120)) return false;
    TestEqual(TEXT("The helper does not start untouched work"),W.Campaign()->TaskProgress().Progress,0);
    if(!Turns(W,1)||!Walk(W,Anchor(W)+FVector(-650,0,0))) return false;
    TestEqual(TEXT("Leaving the winch gives Otane its work"),W.Campaign()->WorkingCrankHelpers(),1);
    const int32 Before=W.Campaign()->TaskProgress().Progress;
    const int32 At=W.Campaign()->TaskProgress().ElapsedMs;
    if(!W.Tick(300)) return false;
    const int32 Delta=W.Campaign()->TaskProgress().ElapsedMs-At;
    TestTrue(TEXT("Otane adds 0.2 turns per second and suspends idle loss"),
        FMath::Abs(W.Campaign()->TaskProgress().Progress-Before-Delta/5)<=1);
    for(int32 Frame=0;Frame<900&&!SoraBeatRules::Released(W.Campaign()->TaskProgress(),0);++Frame)
        if(!W.Tick(1)) return false;
    TestTrue(TEXT("Helper progress releases the authored quarter wave"),SoraBeatRules::Released(W.Campaign()->TaskProgress(),0));
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It) SoraCrankAutomation::Freeze(**It);
    if(!Walk(W,Anchor(W)+FVector(-180,0,0))) return false;
    TestEqual(TEXT("Returning to the wheel stops simultaneous helper credit"),W.Campaign()->WorkingCrankHelpers(),0);
    const int32 Idle=W.Campaign()->TaskProgress().Progress;
    if(!W.Tick(120)) return false;
    TestTrue(TEXT("An idle wheel with no working helper decays"),W.Campaign()->TaskProgress().Progress<Idle);
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraCrankRatchetTest,"SoraArena.Campaign.CrankRatchets",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraCrankRatchetTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraCrankAutomation;
    FBeatWorld W(*this,TEXT("CrankKohagi"),6,6);
    if(!Ready(W)||!Turns(W,5,true)) return false;
    auto* Campaign=W.Campaign();
    ASoraCompanion* Kohagi=Helper(W);
    if(!TestNotNull(TEXT("Kohagi stands at her wheel"),Kohagi)) return false;
    TestEqual(TEXT("The first quarter latches"),Campaign->TaskProgress().CrankFloor,4000);
    const auto& Person=W.Craft().People[0];
    const FVector Work(Person.At,Kohagi->GetActorLocation().Z),Cover(Person.Cover,Kohagi->GetActorLocation().Z);
    ASoraEnemy* Threat=nullptr;
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
    {
        SoraCrankAutomation::Freeze(**It); It->SetActorLocation(Anchor(W)+FVector(-2000,0,300));
        if(!Threat) Threat=*It;
    }
    if(!TestNotNull(TEXT("The quarter wave supplies a real opponent"),Threat)||!Walk(W,Anchor(W)+FVector(-650,0,0))) return false;
    Threat->SetActorLocation(Work+FVector(-501,0,300));
    if(!W.Tick(2)) return false;
    TestFalse(TEXT("An enemy outside five metres does not force retreat"),Campaign->CrankHelperRetreating());
    TestEqual(TEXT("Kohagi works while the player is away"),Campaign->WorkingCrankHelpers(),1);
    Threat->SetActorLocation(Work+FVector(-500,0,300));
    if(!W.Tick(2)) return false;
    TestTrue(TEXT("An enemy at five metres makes Kohagi retreat"),Campaign->CrankHelperRetreating());
    TestEqual(TEXT("Retreat stops cooperation immediately"),Campaign->WorkingCrankHelpers(),0);
    for(int32 Frame=0;Frame<600&&FVector::Dist2D(Kohagi->GetActorLocation(),Cover)>25.f;++Frame)
    {
        const FVector Before=Kohagi->GetActorLocation();
        if(!W.Tick(1)) return false;
        if(!TestTrue(TEXT("Retreat uses walking steps"),FVector::Dist2D(Before,Kohagi->GetActorLocation())<4.f)) return false;
    }
    TestTrue(TEXT("Kohagi reaches existing cover"),FVector::Dist2D(Kohagi->GetActorLocation(),Cover)<=25.f);
    if(!W.Tick(600)) return false;
    TestEqual(TEXT("Abandoned progress stops at the latched quarter"),Campaign->TaskProgress().Progress,4000);
    Threat->SetActorLocation(Anchor(W)+FVector(-2000,0,300));
    for(int32 Frame=0;Frame<600&&Campaign->WorkingCrankHelpers()==0;++Frame) if(!W.Tick(1)) return false;
    TestEqual(TEXT("Defending her lets Kohagi return to work"),Campaign->WorkingCrankHelpers(),1);
    const int32 Before=Campaign->TaskProgress().Progress,At=Campaign->TaskProgress().ElapsedMs;
    if(!W.Tick(300)) return false;
    TestTrue(TEXT("Kohagi contributes 0.15 turns per second with decay suspended"),
        FMath::Abs(Campaign->TaskProgress().Progress-Before-(Campaign->TaskProgress().ElapsedMs-At)*15/100)<=1);
    UGameplayStatics::ApplyDamage(W.Hero(),W.Hero()->Health+1000.f,nullptr,nullptr,UDamageType::StaticClass());
    if(!W.Tick(2)||!W.Mode()->bDefeated||!W.Press(EKeys::Enter)||!W.Tick(30)) return false;
    TestEqual(TEXT("Death retry releases the ratchet and work"),Campaign->TaskProgress().CrankFloor+Campaign->TaskProgress().Progress,0);
    W.Harden();
    if(!Walk(W,Anchor(W)+FVector(-180,0,0))||!Turns(W,4,true)||!Reload(W)) return false;
    TestEqual(TEXT("Fresh-world checkpoint reload releases partial work and ratchets"),W.Campaign()->TaskProgress().Progress+W.Campaign()->TaskProgress().CrankFloor,0);
    TestNotNull(TEXT("Reload creates a fresh helper"),Helper(W));
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraCrankNetTest,"SoraArena.Campaign.CrankNets",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraCrankNetTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraCrankAutomation;
    FBeatWorld W(*this,TEXT("CrankBellows"),4,5);
    if(!Ready(W)||!Turns(W,54)||!Walk(W,Anchor(W)+FVector(-650,0,0))) return false;
    ASoraCompanion* Boy=Helper(W);
    if(!TestNotNull(TEXT("The bellows boy is present"),Boy)) return false;
    for(int32 Frame=0;Frame<2400&&!Boy->IsBound();++Frame) if(!W.Tick(1)) return false;
    if(!TestTrue(TEXT("The authored vent drone nets the boy"),Boy->IsBound())) return false;
    if(!W.Tick(2)) return false;
    TestEqual(TEXT("A netted helper contributes nothing"),W.Campaign()->WorkingCrankHelpers(),0);
    const int32 Before=W.Campaign()->TaskProgress().Progress;
    if(!W.Tick(120)) return false;
    TestTrue(TEXT("Idle bellows still lose progress while the boy is netted"),W.Campaign()->TaskProgress().Progress<Before);
    if(!Walk(W,Boy->GetActorLocation()+FVector(100,0,0))||!W.Hold(EKeys::E,80)) return false;
    TestFalse(TEXT("Held Interact cuts the boy free"),Boy->IsBound());
    if(!Walk(W,Anchor(W)+FVector(-650,0,0))) return false;
    TestEqual(TEXT("The freed boy resumes cooperation"),W.Campaign()->WorkingCrankHelpers(),1);
    const int32 After=W.Campaign()->TaskProgress().Progress,At=W.Campaign()->TaskProgress().ElapsedMs;
    if(!W.Tick(120)) return false;
    TestTrue(TEXT("His credited 0.2 turns/s slows the authored 0.9 turns/s idle loss"),
        FMath::Abs(W.Campaign()->TaskProgress().Progress-After+(W.Campaign()->TaskProgress().ElapsedMs-At)*7/10)<=1);
    return !HasAnyErrors();
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraCrankLiftCrewTest,"SoraArena.Campaign.CrankLiftCrew",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraCrankLiftCrewTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraCrankAutomation;
    FBeatWorld W(*this,TEXT("CrankLiftCrew"),7,10);
    if(!Ready(W)||!Turns(W,20,true)||!Walk(W,Anchor(W)+FVector(-210,-210,0))) return false;
    const auto Crew=W.Fieldcraft()->PeopleInPlay();
    if(!TestEqual(TEXT("All three named crew members are staged"),Crew.Num(),3)) return false;
    const TArray<FString> Names={TEXT("tetsugoro"),TEXT("league_engineer_1"),TEXT("league_engineer_2")};
    for(int32 Index=0;Index<3;++Index)
        TestEqual(TEXT("Each helper has its authored identity"),Crew[Index]->CompanionId(),Names[Index]);
    // Walking out of reach can finish before the authored 2.5-second
    // minimum cadence expires. Measure steady idle decay only after that
    // exact grace period; no decay is due during its remaining fraction.
    for(int32 Frame=0;Frame<180&&!SoraBeatRules::CrankSlipping(W.Campaign()->TaskProgress(),W.Campaign()->ActiveTask());++Frame)
        if(!W.Tick(1)) return false;
    if(!TestTrue(TEXT("The last player turn's cadence window expires before measuring idle rates"),
        SoraBeatRules::CrankSlipping(W.Campaign()->TaskProgress(),W.Campaign()->ActiveTask()))) return false;
    // Exercise the existing companion-availability states. This does not
    // claim a new authored injury or net attack against the lift crew.
    // Bound keeps ordinary character movement active on the moving floor;
    // this fixture measures availability, not a lying-body simulation.
    for(int32 Available=0;Available<=3;++Available)
    {
        for(int32 Index=0;Index<3;++Index)
            Crew[Index]->Present(Index<Available?SoraFieldcraftRules::EState::Up:SoraFieldcraftRules::EState::Bound);
        if(!W.Tick(2)) return false;
        TestEqual(TEXT("Only available crew at their bars contribute"),W.Campaign()->WorkingCrankHelpers(),Available);
        const int32 Before=W.Campaign()->TaskProgress().Progress,At=W.Campaign()->TaskProgress().ElapsedMs;
        const int32 CarryBefore=W.Campaign()->TaskProgress().CrankCarry;
        if(!W.Tick(300)) return false;
        const int32 Delta=W.Campaign()->TaskProgress().ElapsedMs-At;
        AddInfo(FString::Printf(TEXT("Lift idle rate: available=%d actual=%d before=%d after=%d delta_ms=%d carry_before=%d carry_after=%d"),
            Available,W.Campaign()->WorkingCrankHelpers(),Before,W.Campaign()->TaskProgress().Progress,Delta,
            CarryBefore,W.Campaign()->TaskProgress().CrankCarry));
        TestTrue(TEXT("Per-person contribution retains full-goal decay with no perfect-hold waiver"),
            FMath::Abs(W.Campaign()->TaskProgress().Progress-Before-(Available*150-480)*Delta/1000)<=1);
        TestEqual(TEXT("The lift has no imported override ratchet"),W.Campaign()->TaskProgress().CrankFloor,0);
    }
    UGameplayStatics::ApplyDamage(W.Hero(),W.Hero()->Health+1000.f,nullptr,nullptr,UDamageType::StaticClass());
    if(!W.Tick(2)||!W.Mode()->bDefeated||!W.Press(EKeys::Enter)||!W.Tick(30)) return false;
    TestEqual(TEXT("Lift death retry resets partial work"),W.Campaign()->TaskProgress().Progress,0);
    W.Harden();
    if(!Walk(W,Anchor(W)+FVector(-180,0,0))||!Turns(W,2)) return false;
    W.Fieldcraft()->PeopleInPlay()[0]->Present(SoraFieldcraftRules::EState::Bound);
    if(!Reload(W)) return false;
    TestEqual(TEXT("Fresh-world reload resets partial lift work"),W.Campaign()->TaskProgress().Progress,0);
    TestEqual(TEXT("Reload stages all three crew members"),W.Fieldcraft()->PeopleInPlay().Num(),3);
    for(const auto& Person:W.Fieldcraft()->PeopleInPlay())
        TestTrue(TEXT("Reload restores the crew's initial availability"),Person->Condition()==SoraFieldcraftRules::EState::Up);
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraCrankPlayerCostTest,"SoraArena.Campaign.CrankPlayerCosts",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraCrankPlayerCostTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraCrankAutomation;
    for(const int32 Chapter:{3,4,6,7})
    {
        FBeatWorld W(*this,*FString::Printf(TEXT("CrankEffort%d"),Chapter),Chapter,Chapter==6?6:Chapter==7?10:5);
        if(!Ready(W)) return false;
        auto* C=W.Campaign(); auto* Kit=W.Hero()->GetEquipment();
        const int32 Cost=C->ActiveTask().StaminaPerTurn;
        Kit->SpendGuard(100.f);
        if(!PlayerTurn(W)) return false;
        TestEqual(TEXT("Exhausted input makes no progress"),C->TaskProgress().Progress,0);
        TestEqual(TEXT("Exhausted input does not start the rhythm"),C->TaskProgress().LastActionMs,-1);
        TestFalse(TEXT("Exhaustion leaves the hands free"),C->IsWorkingCrank());
        if(!W.Tick(60)) return false;
        Kit->SpendGuard(Kit->GuardReserve()-Cost);
        if(!PlayerTurn(W)) return false;
        TestEqual(TEXT("One accepted turn advances one physical turn"),C->TaskProgress().Progress,1000);
        TestTrue(TEXT("The exact authored cost spends the existing resource"),FMath::IsNearlyZero(Kit->GuardReserve()));
        const int32 Last=C->TaskProgress().LastActionMs;
        if(!PlayerTurn(W)) return false;
        TestEqual(TEXT("Overspeed never gains progress"),C->TaskProgress().Progress,1000);
        TestEqual(TEXT("An immediate overspeed does not move the clock"),C->TaskProgress().LastActionMs,Last);
        if(!W.Tick(15)) return false;
        const float Reserve=Kit->GuardReserve();
        if(!PlayerTurn(W)) return false;
        TestTrue(TEXT("Only bellows overspeed has the authored double charge"),
            FMath::IsNearlyEqual(Reserve-Kit->GuardReserve(),Cost*C->ActiveTask().OverspeedCostMultiplier));
        TestEqual(TEXT("Paid or free overspeed still adds no work"),C->TaskProgress().Progress,1000);
        // The option cannot invent a held cadence on another authored crank.
        if(Chapter!=6)
        {
            W.Mode()->Settings()->SetHoldToCrank(true);
            if(!W.Tick(180)||!W.World->InjectKey(EKeys::E,IE_Pressed)) return false;
            const int32 AfterPress=C->TaskProgress().Done;
            if(!W.Tick(90)||!W.World->InjectKey(EKeys::E,IE_Released)||!W.Tick(1)) return false;
            TestTrue(TEXT("Un-authored assist adds no repeated turns"),C->TaskProgress().Done<=AfterPress);
        }
    }
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraBellowsTreadTest,"SoraArena.Campaign.BellowsTreads",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraBellowsTreadTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraCrankAutomation;
    FBeatWorld W(*this,TEXT("BellowsTreads"),4,5);
    if(!Ready(W)) return false;
    auto* C=W.Campaign();
    const auto Visible=[&](FName Tag)
    {
        TArray<UStaticMeshComponent*> Meshes; W.Mode()->Arena()->GetComponents(Meshes);
        int32 Count=0; for(auto* Mesh:Meshes) if(Mesh->ComponentHasTag(Tag)&&Mesh->IsVisible()) ++Count;
        return Count;
    };
    if(!W.World->InjectKey(EKeys::E,IE_Pressed)||!W.Tick(90)) return false;
    TestEqual(TEXT("Interact alone cannot pump the bellows"),C->TaskProgress().Progress,0);
    TestEqual(TEXT("An idle furnace shows one physical notch"),Visible(TEXT("BellowsFlameNotch")),1);
    if(!W.Press(EKeys::D)||!W.World->InjectKey(EKeys::A,IE_Pressed)||!W.Tick(60)) return false;
    TestEqual(TEXT("A right-first or held left tread adds no cycle"),C->TaskProgress().Progress,0);
    if(!W.World->InjectKey(EKeys::A,IE_Released)||!W.Press(EKeys::D)) return false;
    TestEqual(TEXT("The completed left-right pair makes one cycle"),C->TaskProgress().Progress,1000);
    TestEqual(TEXT("The in-band flame has two physical notches"),Visible(TEXT("BellowsFlameNotch")),2);
    if(!W.Press(EKeys::A)||!W.Press(EKeys::D)) return false;
    TestEqual(TEXT("Overspeed makes no production"),C->TaskProgress().Progress,1000);
    TestEqual(TEXT("Overspeed flame has three notches"),Visible(TEXT("BellowsFlameNotch")),3);
    TestEqual(TEXT("White flame uses a capped eight-spark pool"),Visible(TEXT("BellowsFlameSpark")),8);
    if(!W.Tick(90)) return false;
    TestEqual(TEXT("An idle gauge cools before production is complete"),Visible(TEXT("BellowsFlameNotch")),1);
    if(!W.Press(EKeys::A)) return false;
    UGameplayStatics::ApplyDamage(W.Hero(),1.f,nullptr,nullptr,UDamageType::StaticClass());
    const int32 Before=C->TaskProgress().Done;
    if(!W.Press(EKeys::D)) return false;
    TestTrue(TEXT("Damage discards the half-cycle"),C->TaskProgress().Done<=Before);
    if(!W.World->InjectKey(EKeys::E,IE_Released)||!W.Tick(120)||!W.World->InjectKey(EKeys::Gamepad_FaceButton_Top,IE_Pressed)) return false;
    const int32 PadBefore=C->TaskProgress().Progress;
    if(!W.World->InjectAxis(EKeys::Gamepad_LeftX,-1.f)||!W.World->InjectAxis(EKeys::Gamepad_LeftX,0.f)||
       !W.World->InjectAxis(EKeys::Gamepad_LeftX,1.f)||!W.World->InjectAxis(EKeys::Gamepad_LeftX,0.f)) return false;
    TestEqual(TEXT("Pad stick uses the same neutral-separated pair"),C->TaskProgress().Progress,PadBefore+1000);
    W.World->InjectKey(EKeys::Gamepad_FaceButton_Top,IE_Released);
    if(!Reload(W)) return false;
    TestEqual(TEXT("Reload resets production and tread engagement"),C->TaskProgress().Progress,0);
    TestFalse(TEXT("Checkpoint never restores an active tread"),C->IsWorkingCrank());
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraCrankHeldInputTest,"SoraArena.Campaign.CrankHeldInput",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraCrankHeldInputTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraCrankAutomation;
    FBeatWorld W(*this,TEXT("CrankHeldInput"),6,6);
    if(!Ready(W)) return false;
    auto* C=W.Campaign(); auto* Kit=W.Hero()->GetEquipment();
    const int32 Weapon=W.Hero()->WeaponId;
    TestFalse(TEXT("Held assist defaults off"),W.Mode()->Settings()->HoldToCrank());
    if(!W.World->InjectKey(EKeys::E,IE_Pressed)||!W.Tick(120)) return false;
    TestEqual(TEXT("Ordinary held input makes only its initial turn"),C->TaskProgress().Progress,1000);
    TestTrue(TEXT("Two hands work only while Interact is held"),C->IsWorkingCrank()&&C->CrankOccupiesHands());
    TestFalse(TEXT("The working wheel denies weapon actions"),C->ArmsReady(Weapon,0,false));
    TestTrue(TEXT("The held weapon is hidden without changing its identity"),W.Hero()->GetViewmodel()->bHiddenInGame);
    TestEqual(TEXT("Working never mutates the selected inventory weapon"),W.Hero()->WeaponId,Weapon);
    Kit->GuardDown(false,true);
    TestFalse(TEXT("Two hands cannot simultaneously guard"),Kit->IsGuardHeld());
    if(!W.World->InjectKey(EKeys::E,IE_Released)||!W.Tick(1)) return false;
    TestTrue(TEXT("Release restores weapon permission"),C->ArmsReady(Weapon,0,false));
    TestFalse(TEXT("Release restores the viewmodel"),W.Hero()->GetViewmodel()->bHiddenInGame);
    if(!W.Tick(60)) return false;
    W.Mode()->Settings()->SetHoldToCrank(true);
    if(!W.World->InjectKey(EKeys::E,IE_Pressed)||!W.Tick(120)) return false;
    TestEqual(TEXT("Two seconds of assist add the initial turn and one timed turn"),C->TaskProgress().Progress,3000);
    UGameplayStatics::ApplyDamage(W.Hero(),1.f,nullptr,nullptr,UDamageType::StaticClass());
    TestTrue(TEXT("A real hit immediately restores weapon permission"),C->ArmsReady(Weapon,0,false));
    const int32 AfterHit=C->TaskProgress().Progress;
    if(!W.Tick(120)) return false;
    TestTrue(TEXT("Keeping the key down after a hit cannot resume work"),C->TaskProgress().Progress<=AfterHit);
    if(!W.World->InjectKey(EKeys::E,IE_Released)||!W.Tick(1)||!W.World->InjectKey(EKeys::E,IE_Pressed)) return false;
    TestTrue(TEXT("A fresh press resumes work"),C->IsWorkingCrank());
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It) SoraCrankAutomation::Freeze(**It);
    Kit->Stagger(.5f);
    TestFalse(TEXT("Stagger immediately releases two-handed permission"),C->CrankOccupiesHands());
    if(!W.Tick(60)) return false;
    TestFalse(TEXT("Recovering from stagger while held cannot resume work"),C->IsWorkingCrank());
    if(!W.World->InjectKey(EKeys::E,IE_Released)||!W.Tick(1)||!W.World->InjectKey(EKeys::E,IE_Pressed)) return false;
    Kit->Reload();
    TestFalse(TEXT("Reload input cancels active wheel work"),C->IsWorkingCrank());
    TestTrue(TEXT("Reload input restores weapon permission"),C->ArmsReady(Weapon,0,false));
    if(!W.World->InjectKey(EKeys::E,IE_Released)||!W.Tick(90)||!W.World->InjectKey(EKeys::E,IE_Pressed)) return false;
    if(!Walk(W,Anchor(W)+FVector(-650,0,0))) return false;
    TestFalse(TEXT("Walking away frees both hands"),C->CrankOccupiesHands());
    if(!Walk(W,Anchor(W)+FVector(-180,0,0))) return false;
    TestFalse(TEXT("Returning with the key held does not restart the wheel"),C->IsWorkingCrank());
    if(!W.World->InjectKey(EKeys::E,IE_Released)||!W.Tick(1)||!W.World->InjectKey(EKeys::E,IE_Pressed)) return false;
    W.Mode()->OpenPauseMenu();
    TestFalse(TEXT("Menu cancels work"),C->CrankOccupiesHands());
    W.Mode()->ResumePlay();
    if(!W.Tick(1)) return false;
    TestFalse(TEXT("Closing the menu cannot resume a held key"),C->IsWorkingCrank());
    if(!Reload(W)) return false;
    TestFalse(TEXT("A fresh-world reload discards held work"),W.Campaign()->IsWorkingCrank());
    TestEqual(TEXT("Reload retains inventory availability"),W.Hero()->WeaponId,Weapon);
    TestTrue(TEXT("Reload retains the opted-in accessibility setting"),W.Mode()->Settings()->HoldToCrank());
    TestEqual(TEXT("Reload resets unfinished crank work"),W.Campaign()->TaskProgress().Progress,0);
    return !HasAnyErrors();
}
#endif
