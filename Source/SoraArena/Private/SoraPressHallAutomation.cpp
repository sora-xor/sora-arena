#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraPressRules.h"
#include "SoraEnemy.h"
#include "SoraEnemyController.h"
#include "Combat/SoraEnemyCatalog.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"

namespace SoraPressAutomation
{
using SoraFieldcraftAutomation::FBeatWorld;
void FreezeGuards(FBeatWorld& W)
{
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
    {
        It->SetActorTickEnabled(false); It->SetActorEnableCollision(false);
        It->GetCharacterMovement()->StopMovementImmediately();
        It->GetCharacterMovement()->SetComponentTickEnabled(false);
        It->SetActorLocation(FVector(W.BeatData().Space.Entry+FVector2D(0,8000),90));
        if(auto* Brain=Cast<ASoraEnemyController>(It->GetController()))
        { Brain->BeginPatrol(FSoraPatrolRoute{}); Brain->SetActorTickEnabled(false); }
    }
}
bool MaskWindow(FBeatWorld& W)
{
    for(int I=0;I<110&&SoraPressRules::Phase(W.Fieldcraft()->PressClock())>=SoraPressRules::WindowMs;++I)
        if(!W.Tick(1)) return false;
    return SoraPressRules::Masking(W.Fieldcraft()->PressClock());
}
AActor* Block(FBeatWorld& W,const FVector& At,const FVector& Half)
{
    auto* Actor=W.World->GetTestWorld()->SpawnActor<AActor>();
    if(!Actor) return nullptr;
    auto* Box=NewObject<UBoxComponent>(Actor);
    Actor->SetRootComponent(Box); Actor->AddInstanceComponent(Box);
    Box->SetBoxExtent(Half); Box->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
    Box->SetCollisionResponseToAllChannels(ECR_Block); Box->RegisterComponent(); Actor->SetActorLocation(At);
    return Actor;
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraPressHallTest,"SoraArena.Campaign.PressHall",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraPressHallTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraPressAutomation;
    if(!FSoraCatalog::Get().Load()) return false;
    FBeatWorld W(*this,TEXT("PressHall"),5,10);
    if(!W.Start()) return false;
    W.Harden(); FreezeGuards(W);
    auto* Craft=W.Fieldcraft(); auto* C=W.Campaign(); const auto& Space=W.BeatData().Space;
    if(!TestTrue(TEXT("The authored press contract is loaded"),Space.PressHall.bEnabled)) return false;
    for(int I=0;I<8;++I) TestTrue(TEXT("All eight presses start running"),Craft->PressRunning(I));
    const FVector Center(Space.PressHall.Origin+FVector2D(1800,500),0);
    const FVector Boundary=Center+FVector(0,-800,80);
    if(!MaskWindow(W)) return false;
    TestEqual(TEXT("A stamp masks at exactly its 800 cm sphere"),Craft->PressNoisePermille(Boundary),200);
    TestEqual(TEXT("The source outside that sphere stays audible"),Craft->PressNoisePermille(Boundary+FVector(0,-1,0)),1000);
    TestEqual(TEXT("Overlapping presses do not compound the reduction"),Craft->PressNoisePermille(Center+FVector(0,350,80)),200);
    if(!W.Press(EKeys::Escape)) return false;
    const int64 Paused=Craft->PressClock();
    if(!W.Tick(120)) return false;
    TestEqual(TEXT("Pause freezes the stamp clock"),Craft->PressClock(),Paused);
    if(!TestTrue(TEXT("Interact can be rebound in the menu"),W.Hero()->RemapCombatAction(TEXT("Interact"),EKeys::G))||
        !W.Press(EKeys::Escape)) return false;
    const FVector Work(Space.Objectives[0],0); W.Stand(Work,90);
    if(!W.Tick(2)||!TestTrue(TEXT("The master handle is unobstructed and grounded"),Craft->CanWorkPress(0))) return false;
    if(!W.Hold(EKeys::E,270)) return false;
    TestEqual(TEXT("The old binding cannot jam a press"),C->TaskProgress().Done,0);
    if(!W.Hold(EKeys::G,120)) return false;
    TestTrue(TEXT("A released two-second attempt leaves the master running"),Craft->PressRunning(1)&&C->TaskProgress().Done==0);
    AActor* Wall=Block(W,Work+FVector(0,35,150),FVector(100,5,150));
    if(!TestNotNull(TEXT("The handle obstruction spawns"),Wall)||!W.Hold(EKeys::G,270)) return false;
    TestEqual(TEXT("A wall blocks the nearby handle"),C->TaskProgress().Done,0);
    Wall->Destroy();
    if(!W.World->InjectKey(EKeys::G,IE_Pressed)||!W.Tick(120)) return false;
    Wall=Block(W,Work+FVector(0,35,150),FVector(100,5,150));
    if(!TestNotNull(TEXT("The ongoing obstruction spawns"),Wall)||!W.Tick(180)) return false;
    Wall->Destroy();
    if(!W.Tick(180)) return false;
    TestEqual(TEXT("An obstruction cancels ongoing work; clearing it while held cannot resume"),C->TaskProgress().Done,0);
    if(!W.World->InjectKey(EKeys::G,IE_Released)||!W.Hold(EKeys::G,270)) return false;
    TestTrue(TEXT("A fresh mapped four-second hold jams only A2"),C->TaskProgress().Done==1&&!Craft->PressRunning(1)&&Craft->PressRunning(4));
    if(!MaskWindow(W)) return false;
    TestEqual(TEXT("The jammed master stops its own masking immediately"),Craft->PressNoisePermille(Boundary),1000);
    TestEqual(TEXT("An unjammed neighboring machine still masks"),Craft->PressNoisePermille(FVector(Space.PressHall.Origin+FVector2D(800,500),80)),200);
    FBeatWorld::Hurt(*W.Hero(),W.Hero()->Health+1000.f);
    if(!W.Tick(2)||!TestTrue(TEXT("Death ends the attempt"),W.Mode()->bDefeated)||!W.Press(EKeys::Enter)) return false;
    W.Harden(); FreezeGuards(W);
    TestTrue(TEXT("Checkpoint retry restarts the machine and objective state"),C->ActiveBeat()==10&&C->TaskProgress().Done==0&&Craft->PressRunning(1)&&!Craft->PressInspectionArrived(0));
    AddInfo(TEXT("Directed input/obstruction and stamp fixture. Guards frozen; ordinary encounter difficulty, catwalk, timing of authored patrols, art and audio remain unqualified."));
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraPressInspectionTest,"SoraArena.Campaign.PressInspection",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraPressInspectionTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraPressAutomation;
    if(!FSoraCatalog::Get().Load()) return false;
    FBeatWorld W(*this,TEXT("PressInspection"),5,10);
    if(!W.Start()) return false;
    W.Harden(); FreezeGuards(W);
    auto* Craft=W.Fieldcraft(); const FVector Work(W.BeatData().Space.Objectives[0],0);
    // A separate living auditor isolates path movement from detection. The
    // normal-input fixture above establishes the actual jam admission.
    FSoraEnemyTuning Tune; Tune.SightCm=1; Tune.DarkSightCm=0; Tune.HearingCm=0;
    FSoraPatrolRoute Route;
    auto* Auditor=ASoraEnemy::SpawnArchetype(*W.World->GetTestWorld(),TEXT("auditor"),0,Work+FVector(800,0,100),FRotator::ZeroRotator,&Route,&Tune);
    if(!TestNotNull(TEXT("The inspector fixture spawns a living auditor"),Auditor)) return false;
    auto* Brain=Cast<ASoraEnemyController>(Auditor->GetController());
    if(!TestNotNull(TEXT("The inspector has its real navigation controller"),Brain)) return false;
    W.Stand(FVector(W.BeatData().Space.Entry,0));
    AActor* Barrier=Block(W,Work+FVector(0,0,150),FVector(150,150,150));
    if(!TestNotNull(TEXT("The inspection path obstruction spawns"),Barrier)) return false;
    Craft->JamPress(0);
    if(!W.Tick(1260)) return false;
    TestFalse(TEXT("An unreachable station is not an inspection arrival"),Craft->PressInspectionArrived(0));
    TestTrue(TEXT("The missed twenty-second deadline remains visible"),Craft->PressInspectionOverdue(0));
    TestTrue(TEXT("The real inspector, not a timer, was assigned"),Craft->PressInspector(0)==Auditor);
    Barrier->Destroy();
    for(int I=0;I<1200&&!Craft->PressInspectionArrived(0);++I) if(!W.Tick(1)) return false;
    const FVector Feet=Auditor->GetActorLocation()-FVector(0,0,Auditor->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
    TestTrue(TEXT("Opening the path lets the living auditor actually reach the station"),Craft->PressInspectionArrived(0)&&FVector::Dist(Feet,Work)<=75.f);
    TestTrue(TEXT("A later arrival does not erase its missed deadline"),Craft->PressInspectionOverdue(0));
    AddInfo(TEXT("Directed auditor navigation with a blocking fixture and sight/hearing disabled for this inspector only; not ordinary stealth acceptance."));
    return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraPressNoiseTest,"SoraArena.Campaign.PressNoiseEmission",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraPressNoiseTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraPressAutomation;
    if(!FSoraCatalog::Get().Load()) return false;
    FBeatWorld W(*this,TEXT("PressNoise"),5,10);
    if(!W.Start()) return false;
    W.Harden(); FreezeGuards(W);
    auto* Craft=W.Fieldcraft();
    const FVector Origin(W.BeatData().Space.PressHall.Origin+FVector2D(1800,500),80);
    FSoraEnemyTuning Tune; Tune.SightCm=1; Tune.DarkSightCm=0; Tune.HearingCm=900;
    FSoraPatrolRoute Route;
    auto* Listener=ASoraEnemy::SpawnArchetype(*W.World->GetTestWorld(),TEXT("auditor"),0,
        Origin+FVector(1500,0,20),FRotator::ZeroRotator,&Route,&Tune);
    if(!TestNotNull(TEXT("The hearing fixture spawns"),Listener)) return false;
    auto* Brain=Cast<ASoraEnemyController>(Listener->GetController());
    if(!TestNotNull(TEXT("The hearing fixture has its normal brain"),Brain)) return false;
    Listener->GetCharacterMovement()->SetComponentTickEnabled(false);
    Brain->SetActorTickEnabled(false);
    if(!MaskWindow(W)) return false;
    Brain->HearNoise(SoraStealthRules::ENoise::Shot,Origin,Origin,W.Hero());
    for(int I=0;I<50&&SoraPressRules::Masking(Craft->PressClock());++I) if(!W.Tick(1)) return false;
    if(!TestFalse(TEXT("The quiet window ended before this sound was processed"),SoraPressRules::Masking(Craft->PressClock()))) return false;
    Brain->SetActorTickEnabled(true);
    if(!W.Tick(1)) return false;
    TestEqual(TEXT("A masked emission stays masked when processed after the stamp"),Brain->AwarenessPermille(),0);
    Brain->BeginPatrol(Route); Brain->SetActorTickEnabled(false);
    Brain->HearNoise(SoraStealthRules::ENoise::Shot,Origin,Origin,W.Hero());
    if(!MaskWindow(W)) return false;
    Brain->SetActorTickEnabled(true);
    if(!W.Tick(1)) return false;
    TestTrue(TEXT("An exposed emission stays audible when processed during the next stamp"),Brain->AwarenessPermille()>0);
    Brain->BeginPatrol(Route); Brain->SetActorTickEnabled(false);
    if(!MaskWindow(W)) return false;
    Brain->HearNoise(SoraStealthRules::ENoise::Shot,Origin,Origin,nullptr);
    Brain->SetActorTickEnabled(true);
    if(!W.Tick(1)) return false;
    TestTrue(TEXT("A non-player environmental sound is not reduced"),Brain->AwarenessPermille()>0);
    Brain->BeginPatrol(Route); Brain->HearAlarm(Origin);
    TestTrue(TEXT("An alarm remains an alarm inside a stamp window"),Brain->AwarenessPermille()>0);
    AddInfo(TEXT("Directed real perception test with sight disabled; source loudness is fixed at emission, separate from listener scheduling."));
    return true;
}
#endif
