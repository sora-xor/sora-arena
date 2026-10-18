#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraRecoveryAutomation.h"
#include "SoraCompanion.h"
#include "SoraEnemy.h"
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
bool Walk(FBeatWorld& W,const FVector& To) { return SoraRecoveryAutomation::WalkTo(*W.World,To); }
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
bool Turns(FBeatWorld& W,int32 Count,bool bFreeze=false)
{
    const int32 Frames=FMath::CeilToInt(W.Campaign()->ActiveTask().MinTurnMs*60.f/1000.f)+2;
    for(int32 Turn=0;Turn<Count;++Turn)
    {
        if(!W.Tick(Frames)||!W.Press(EKeys::E)) return false;
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
    if(!Ready(W)||!Turns(W,20,true)||!Walk(W,Anchor(W)+FVector(-650,0,0))) return false;
    const auto Crew=W.Fieldcraft()->PeopleInPlay();
    if(!TestEqual(TEXT("All three named crew members are staged"),Crew.Num(),3)) return false;
    const TArray<FString> Names={TEXT("tetsugoro"),TEXT("league_engineer_1"),TEXT("league_engineer_2")};
    for(int32 Index=0;Index<3;++Index)
        TestEqual(TEXT("Each helper has its authored identity"),Crew[Index]->CompanionId(),Names[Index]);
    // Exercise the existing companion-availability states. This does not
    // claim a new authored injury or net attack against the lift crew.
    for(int32 Available=0;Available<=3;++Available)
    {
        for(int32 Index=0;Index<3;++Index)
            Crew[Index]->Present(Index<Available?SoraFieldcraftRules::EState::Up:SoraFieldcraftRules::EState::Down);
        if(!W.Tick(2)) return false;
        TestEqual(TEXT("Only available crew at their bars contribute"),W.Campaign()->WorkingCrankHelpers(),Available);
        const int32 Before=W.Campaign()->TaskProgress().Progress,At=W.Campaign()->TaskProgress().ElapsedMs;
        if(!W.Tick(300)) return false;
        const int32 Delta=W.Campaign()->TaskProgress().ElapsedMs-At;
        TestTrue(TEXT("Per-person contribution retains full-goal decay with no perfect-hold waiver"),
            FMath::Abs(W.Campaign()->TaskProgress().Progress-Before-(Available*150-480)*Delta/1000)<=1);
        TestEqual(TEXT("The lift has no imported override ratchet"),W.Campaign()->TaskProgress().CrankFloor,0);
    }
    UGameplayStatics::ApplyDamage(W.Hero(),W.Hero()->Health+1000.f,nullptr,nullptr,UDamageType::StaticClass());
    if(!W.Tick(2)||!W.Mode()->bDefeated||!W.Press(EKeys::Enter)||!W.Tick(30)) return false;
    TestEqual(TEXT("Lift death retry resets partial work"),W.Campaign()->TaskProgress().Progress,0);
    W.Harden();
    if(!Walk(W,Anchor(W)+FVector(-180,0,0))||!Turns(W,2)) return false;
    W.Fieldcraft()->PeopleInPlay()[0]->Present(SoraFieldcraftRules::EState::Down);
    if(!Reload(W)) return false;
    TestEqual(TEXT("Fresh-world reload resets partial lift work"),W.Campaign()->TaskProgress().Progress,0);
    TestEqual(TEXT("Reload stages all three crew members"),W.Fieldcraft()->PeopleInPlay().Num(),3);
    for(const auto& Person:W.Fieldcraft()->PeopleInPlay())
        TestTrue(TEXT("Reload restores the crew's initial availability"),Person->Condition()==SoraFieldcraftRules::EState::Up);
    return !HasAnyErrors();
}
#endif
