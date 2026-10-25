#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraPressRules.h"
#include "SoraEnemy.h"
#include "SoraEnemyController.h"
#include "SoraProjectile.h"
#include "Combat/SoraEnemyCatalog.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"

namespace SoraPressAutomation
{
using SoraFieldcraftAutomation::FBeatWorld;
FVector Feet(const ASoraCharacterBase& Body)
{ return Body.GetActorLocation()-FVector(0,0,Body.GetCapsuleComponent()->GetScaledCapsuleHalfHeight()); }
void FloorFixture(FBeatWorld& W,const FVector& At,float Yaw=0)
{
    // Deliberate placement for isolated handle/inspection tests. Traversal
    // from the actual elevated entry is exercised by PressCatwalk below.
    W.Hero()->GetCharacterMovement()->StopMovementImmediately();
    W.Hero()->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
    W.Hero()->SetActorLocation(FVector(At.X,At.Y,W.Hero()->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+2),false,nullptr,ETeleportType::TeleportPhysics);
    W.Look(FRotator(0,Yaw,0));
}
bool WaitForPressDialogue(FBeatWorld& W)
{
    for(int I=0;I<1800&&W.Campaign()->IsDialogueBlocking();++I)
        if(!W.Tick(1)) return false;
    return W.Test.TestFalse(TEXT("Authored press dialogue releases control without being skipped"),W.Campaign()->IsDialogueBlocking());
}
ASoraEnemy* SpawnPatrolFixture(FBeatWorld& W,int GuardIndex)
{
    namespace Press=SoraPressRules;
    const FVector Origin(W.BeatData().Space.PressHall.Origin,0);
    FSoraPatrolRoute Route;
    for(int I=0;I<Press::PatrolCount(GuardIndex);++I)
    {
        const auto P=Press::PatrolPoint(GuardIndex,I);
        Route.Points.Add(Origin+FVector(P.X,P.Y,Press::PatrolFloor(GuardIndex)+90));
    }
    Route.PeriodMs=Press::PatrolPeriod(GuardIndex); Route.PauseMs=Press::PatrolDwell(GuardIndex);
    Route.bThreeDimensional=true; if(GuardIndex<2) Route.PauseFacing=FVector(0,1,0);
    FSoraEnemyTuning Tune; Tune.SightCm=1; Tune.DarkSightCm=0; Tune.HearingCm=0;
    auto* Guard=ASoraEnemy::SpawnArchetype(*W.World->GetTestWorld(),GuardIndex<2?TEXT("auditor"):GuardIndex==5?TEXT("drone"):TEXT("enforcer_rifle"),GuardIndex,
        Route.Points[0],FRotator::ZeroRotator,&Route,&Tune);
    if(!Guard) return nullptr;
    for(auto& Point:Route.Points)
        Point.Z=Press::PatrolFloor(GuardIndex)+Guard->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+2.f;
    Guard->SetActorLocation(Route.Points[0]);
    if(auto* Brain=Cast<ASoraEnemyController>(Guard->GetController())) Brain->BeginPatrol(Route);
    return Guard;
}
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
bool ArrowAtLamp(FBeatWorld& W,int Index)
{
    auto* Lamp=W.Fieldcraft()->Lamps().IsValidIndex(Index)?W.Fieldcraft()->Lamps()[Index].Get():nullptr;
    if(!W.Test.TestNotNull(TEXT("The arrow has a die-lamp target"),Lamp)) return false;
    const FTransform Launch(FRotator(0,90,0),Lamp->Glow()+FVector(0,-100,0));
    auto* Arrow=W.World->GetTestWorld()->SpawnActorDeferred<ASoraProjectile>(ASoraProjectile::StaticClass(),Launch,
        W.Hero(),W.Hero(),ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
    if(!W.Test.TestNotNull(TEXT("A real arrow is released toward the lens"),Arrow)) return false;
    Arrow->bArrow=true; Arrow->WeaponId=18; Arrow->Velocity=FVector(0,1000,49);
    Arrow->FinishSpawning(Launch);
    for(int I=0;I<20&&Lamp->IsLit();++I) if(!W.Tick(1)) return false;
    return W.Test.TestFalse(TEXT("The swept arrow impact extinguishes the lens"),Lamp->IsLit());
}
bool Reload(FBeatWorld& W)
{
    W.Fieldcraft()->OnEvent.Remove(W.EventsHandle);
    W.World->DestroyTestWorld(true); W.World->ForwardErrorMessages(&W.Test); W.World.Reset();
    W.World=MakeUnique<FSoraAutomationWorld>();
    if(!W.World->Start(W.Slot)||!W.World->Tick(1)||!W.World->EnableKeyInput()||
        !W.Press(EKeys::Enter)||!W.Press(EKeys::Enter)||!W.Press(EKeys::Enter)) return false;
    W.Events.Reset();
    W.EventsHandle=W.Fieldcraft()->OnEvent.AddLambda([&W](FName Event) { W.Events.Add(Event.ToString()); });
    return W.Test.TestTrue(TEXT("The saved press checkpoint opens in a fresh world"),
        W.Campaign()->ActiveBeat()==10&&W.Fieldcraft()->PressRunning(1));
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
    const FVector Work(Space.Objectives[0],0); FloorFixture(W,Work,90);
    if(!W.Tick(2)||!WaitForPressDialogue(W)||!TestTrue(TEXT("The master handle is unobstructed and grounded"),Craft->CanWorkPress(0))) return false;
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
    FloorFixture(W,FVector(W.BeatData().Space.Entry,0));
    if(!W.Tick(2)||!WaitForPressDialogue(W)) return false;
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
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraPressLampTest,"SoraArena.Campaign.PressDieLamps",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraPressLampTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraPressAutomation;
    if(!FSoraCatalog::Get().Load()) return false;
    FBeatWorld W(*this,TEXT("PressDieLamps"),5,10);
    if(!W.Start()) return false;
    W.Harden(); FreezeGuards(W);
    auto* Craft=W.Fieldcraft();
    if(!TestEqual(TEXT("Each master has its own die lamp"),Craft->Lamps().Num(),3)) return false;
    auto* Lamp=Craft->Lamps()[0].Get();
    if(!TestNotNull(TEXT("The first die lamp exists"),Lamp)) return false;
    TestTrue(TEXT("The die lens hangs above the press crown"),FMath::IsNearlyEqual(Lamp->Glow().Z,420.f));
    FSoraEnemyTuning Tune; Tune.SightCm=1; Tune.DarkSightCm=0; Tune.HearingCm=0;
    FSoraPatrolRoute Route;
    auto* Near=ASoraEnemy::SpawnArchetype(*W.World->GetTestWorld(),TEXT("auditor"),0,
        Lamp->GetActorLocation()+FVector(0,-700,100),FRotator::ZeroRotator,&Route,&Tune);
    auto* Far=ASoraEnemy::SpawnArchetype(*W.World->GetTestWorld(),TEXT("auditor"),1,
        Lamp->GetActorLocation()+FVector(0,1000,100),FRotator::ZeroRotator,&Route,&Tune);
    if(!TestNotNull(TEXT("The nearest auditor spawns"),Near)||!TestNotNull(TEXT("The second auditor spawns"),Far)) return false;
    auto* NearBrain=Cast<ASoraEnemyController>(Near->GetController());
    auto* FarBrain=Cast<ASoraEnemyController>(Far->GetController());
    if(!TestNotNull(TEXT("Nearest auditor brain"),NearBrain)||!TestNotNull(TEXT("Second auditor brain"),FarBrain)) return false;
    Near->GetCharacterMovement()->SetComponentTickEnabled(false);
    Far->GetCharacterMovement()->SetComponentTickEnabled(false);
    // Contact restrictions are checked separately from actual arrow travel.
    FHitResult Contact; Contact.ImpactPoint=Lamp->Glow();
    auto Bullet=FSoraHit::Ranged(W.Hero()->GetActorLocation(),1); Bullet.bHitscan=true;
    for(auto Hit:{FSoraHit::Melee(W.Hero()->GetActorLocation(),0),Bullet,
                 FSoraHit::Blast(Lamp->Glow(),1)})
        SoraDamage::Strike(Lamp,100,Hit,FVector::ForwardVector,Contact,W.Hero()->GetController(),W.Hero());
    TestTrue(TEXT("Melee, a bullet and a blast leave the die lamp lit"),Lamp->IsLit());
    if(!ArrowAtLamp(W,0)) return false;
    const int64 OutAt=Craft->PressClock();
    if(!W.Tick(120)) return false;
    TestTrue(TEXT("Neither guard becomes suspicious before five seconds"),
        NearBrain->State()==SoraStealthRules::EState::Unaware&&FarBrain->State()==SoraStealthRules::EState::Unaware);
    if(!W.Press(EKeys::Escape)) return false;
    const int64 Paused=Craft->PressClock();
    if(!W.Tick(360)) return false;
    TestEqual(TEXT("Pause freezes the pending lamp notice"),Craft->PressClock(),Paused);
    TestTrue(TEXT("A paused wait cannot deliver the notice"),NearBrain->State()==SoraStealthRules::EState::Unaware);
    if(!W.Press(EKeys::Escape)) return false;
    while(Craft->PressClock()-OutAt<4950) if(!W.Tick(1)) return false;
    TestTrue(TEXT("The nearest guard is still unaware just before the deadline"),NearBrain->State()==SoraStealthRules::EState::Unaware);
    if(!W.Tick(5)) return false;
    TestTrue(TEXT("The nearest auditor becomes suspicious, without alarming"),NearBrain->State()==SoraStealthRules::EState::Suspicious);
    TestTrue(TEXT("The farther guard is not informed"),FarBrain->State()==SoraStealthRules::EState::Unaware);
    TestTrue(TEXT("The evidence is the lamp, not the hero's hidden position"),NearBrain->LastKnownLocation().Equals(Lamp->Glow(),.01f));
    NearBrain->Rouse(Lamp->Glow()); NearBrain->NoticeTampering(Lamp->Glow());
    TestTrue(TEXT("A broken light never downgrades an alert"),NearBrain->State()==SoraStealthRules::EState::Alert);
    FBeatWorld::Hurt(*W.Hero(),W.Hero()->Health+1000.f);
    if(!W.Tick(2)||!W.Press(EKeys::Enter)) return false;
    W.Harden(); FreezeGuards(W);
    TestTrue(TEXT("Retry restores all three lamps"),Craft->Lamps().Num()==3&&
        Craft->Lamps()[0]->IsLit()&&Craft->Lamps()[1]->IsLit()&&Craft->Lamps()[2]->IsLit());
    if(!W.Tick(360)) return false;
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
        if(auto* Brain=Cast<ASoraEnemyController>(It->GetController()))
            TestTrue(TEXT("Retry discards the previous lamp notice"),Brain->State()==SoraStealthRules::EState::Unaware);
    AddInfo(TEXT("Directed collision and delay fixture with sight/hearing isolated. It does not qualify ordinary bow aiming, art or encounter difficulty."));
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraPressReloadTest,"SoraArena.Campaign.PressCheckpointReload",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraPressReloadTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraPressAutomation;
    if(!FSoraCatalog::Get().Load()) return false;
    FBeatWorld W(*this,TEXT("PressCheckpointReload"),5,10);
    if(!W.Start()) return false;
    W.Harden(); FreezeGuards(W);
    if(!W.Press(EKeys::Escape)||!TestTrue(TEXT("The menu rebinds Interact"),W.Hero()->RemapCombatAction(TEXT("Interact"),EKeys::G))||
        !W.Press(EKeys::Escape)) return false;
    FloorFixture(W,FVector(W.BeatData().Space.Objectives[0],0),90);
    if(!W.Tick(2)||!WaitForPressDialogue(W)||!W.Hold(EKeys::G,270)||!WaitForPressDialogue(W)) return false;
    if(!TestTrue(TEXT("The original world has one jam and an unfinished inspection"),
        W.Campaign()->TaskProgress().Done==1&&!W.Fieldcraft()->PressRunning(1)&&
        !W.Fieldcraft()->PressInspectionArrived(0))) return false;
    if(!ArrowAtLamp(W,0)) return false;
    W.Campaign()->SaveProgress();
    if(!Reload(W)) return false;
    W.Harden(); FreezeGuards(W);
    auto* Craft=W.Fieldcraft();
    TestEqual(TEXT("Fresh checkpoint load starts with no completed jams"),W.Campaign()->TaskProgress().Done,0);
    for(int I=0;I<8;++I) TestTrue(TEXT("Fresh checkpoint load starts every press"),Craft->PressRunning(I));
    for(int I=0;I<3;++I)
    {
        TestTrue(TEXT("Fresh checkpoint restores each die lamp"),Craft->Lamps()[I]->IsLit());
        TestFalse(TEXT("Fresh checkpoint has no old inspection arrival"),Craft->PressInspectionArrived(I));
        TestFalse(TEXT("Fresh checkpoint has no old missed deadline"),Craft->PressInspectionOverdue(I));
    }
    const int64 Start=Craft->PressClock();
    if(!W.Tick(360)) return false;
    TestTrue(TEXT("The new world advances one clock for six seconds"),FMath::Abs(Craft->PressClock()-Start-6000)<=1);
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
        if(auto* Brain=Cast<ASoraEnemyController>(It->GetController()))
            TestTrue(TEXT("No old-world lamp notice reaches fresh guards"),Brain->State()==SoraStealthRules::EState::Unaware);
    TestFalse(TEXT("No old silent-machine errand survives world destruction"),W.Events.Contains(TEXT("ai_event:press_silent")));
    AddInfo(TEXT("Actual save and world recreation; checkpoint semantics restart this beat. Directed fixture, with guards frozen."));
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraPressCatwalkTest,"SoraArena.Campaign.PressCatwalk",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraPressCatwalkTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraPressAutomation;
    namespace Press=SoraPressRules;
    if(!FSoraCatalog::Get().Load()) return false;
    FBeatWorld W(*this,TEXT("PressCatwalk"),5,10);
    if(!W.Start()) return false;
    W.Harden();
    int Elevated=0;
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
        if(It->ArchetypeId()==TEXT("enforcer_rifle")&&Feet(**It).Z>350) ++Elevated;
    TestEqual(TEXT("Exactly one authored rifle enforcer starts above the floor"),Elevated,1);
    FreezeGuards(W);
    auto* Craft=W.Fieldcraft(); auto* Player=W.Hero();
    const FVector Origin(W.BeatData().Space.PressHall.Origin,0);
    const FVector Foot=Origin+FVector(Press::LadderFoot.X,Press::LadderFoot.Y,0);
    const FVector Top=Origin+FVector(Press::LadderTop.X,Press::LadderTop.Y,Press::CatwalkHeightCm);
    if(!W.Tick(60)||!TestTrue(TEXT("Checkpoint entry settles onto the NW catwalk"),FVector::Dist(Feet(*Player),Top)<5.f)) return false;
    for(const auto& Point:Press::CatwalkRoute)
    {
        FHitResult Hit; const FVector Above=Origin+FVector(Point.X,Point.Y,450);
        FCollisionQueryParams Q(SCENE_QUERY_STAT(PressWalkSupport),false,Player);
        TestTrue(TEXT("Every catwalk corner has real support at four metres"),
            W.World->GetTestWorld()->LineTraceSingleByChannel(Hit,Above,Above-FVector(0,0,100),ECC_Visibility,Q)&&
            FMath::IsNearlyEqual(Hit.ImpactPoint.Z,400.f,1.f));
    }
    if(!W.Press(EKeys::Escape)||!TestTrue(TEXT("Jump can be rebound"),Player->RemapCombatAction(TEXT("Jump"),EKeys::J))||
        !W.Press(EKeys::Escape)||!W.Hold(EKeys::SpaceBar,30)) return false;
    TestFalse(TEXT("The former Jump binding cannot take the ladder"),Craft->IsOnLadder());
    W.Look(FRotator(0,-90,0));
    AActor* Barrier=Block(W,Foot+FVector(0,0,260),FVector(90,90,10));
    if(!TestNotNull(TEXT("The ladder obstruction spawns"),Barrier)||!W.Press(EKeys::J)||
        !TestTrue(TEXT("Mapped Jump starts descending with arms stowed"),Craft->IsOnLadder()&&Craft->ArmsStowed())||!W.Tick(240)) return false;
    TestTrue(TEXT("The swept capsule stops above the obstruction"),Craft->IsOnLadder()&&Feet(*Player).Z>=269.f);
    const FVector Blocked=Player->GetActorLocation();
    if(!W.Tick(120)) return false;
    TestTrue(TEXT("Time alone cannot move through the obstacle"),Player->GetActorLocation().Equals(Blocked,.1f));
    if(!W.Press(EKeys::Escape)) return false;
    const FVector Paused=Player->GetActorLocation();
    if(!W.Tick(120)) return false;
    TestTrue(TEXT("Pause freezes the held ladder position"),Player->GetActorLocation().Equals(Paused,.1f));
    if(!W.Press(EKeys::Escape)||!W.Press(EKeys::J)) return false;
    TestFalse(TEXT("Jump again releases even an obstructed ladder"),Craft->IsOnLadder());
    TestFalse(TEXT("Release restores gravity"),Player->GetCharacterMovement()->IsFlying());
    Barrier->Destroy();
    if(!W.Tick(90)||!WaitForPressDialogue(W)||!TestTrue(TEXT("The released hero lands at the ladder foot"),FVector::Dist(Feet(*Player),Foot)<5.f)) return false;
    W.Look(FRotator(0,90,0));
    if(!W.Press(EKeys::J)||!TestTrue(TEXT("The floor endpoint admits the upward climb"),Craft->IsOnLadder())) return false;
    float LargestStep=0;
    for(int Frame=0;Frame<360&&Craft->IsOnLadder();++Frame)
    {
        const FVector Before=Player->GetActorLocation();
        if(!W.Tick(1)) return false;
        LargestStep=FMath::Max(LargestStep,float(FVector::Dist(Before,Player->GetActorLocation())));
    }
    if(!W.Tick(5)) return false;
    AddInfo(FString::Printf(TEXT("Largest ascent step: %.6f cm"),LargestStep));
    TestTrue(TEXT("The full ascent and step onto the deck remain bounded by 150 cm/s"),LargestStep<=2.6f);
    TestTrue(TEXT("Ascent ends on the supported catwalk with ordinary movement restored"),
        !Craft->IsOnLadder()&&Player->GetCharacterMovement()->IsMovingOnGround()&&FVector::Dist(Feet(*Player),Top)<5.f&&W.Raised(TEXT("roof_reached:press_nw")));
    W.Look(FRotator(0,-90,0));
    if(!W.Press(EKeys::J)) return false;
    for(int Frame=0;Frame<360&&Craft->IsOnLadder();++Frame) if(!W.Tick(1)) return false;
    if(!W.Tick(5)) return false;
    TestTrue(TEXT("The unobstructed return reaches the floor through the same ladder"),
        !Craft->IsOnLadder()&&FVector::Dist(Feet(*Player),Foot)<5.f&&W.Raised(TEXT("ladder_foot:press_nw")));
    if(!WaitForPressDialogue(W)) return false;
    W.Look(FRotator(0,90,0));
    if(!W.Press(EKeys::J)||!W.Tick(90)) return false;
    FBeatWorld::Hurt(*Player,Player->Health+1000.f);
    if(!W.Tick(2)||!W.Press(EKeys::Enter)||!W.Tick(60)) return false;
    Player=W.Hero();
    TestTrue(TEXT("Death during a climb clears the old ladder and returns to elevated entry"),
        !Craft->IsOnLadder()&&!Craft->HoldsHero()&&!Player->GetCharacterMovement()->IsFlying()&&FVector::Dist(Feet(*Player),Top)<5.f);
    AddInfo(TEXT("Directed mapped-input traversal, swept collision, pause/release and retry. Guards frozen after checking the authored elevated spawn; not ordinary encounter acceptance."));
    return !HasAnyErrors();
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraPressCatwalkPatrolTest,"SoraArena.Campaign.PressCatwalkPatrol",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraPressCatwalkPatrolTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraPressAutomation;
    namespace Press=SoraPressRules;
    if(!FSoraCatalog::Get().Load()) return false;
    FBeatWorld W(*this,TEXT("PressCatwalkPatrol"),5,10);
    if(!W.Start()) return false;
    W.Harden(); FreezeGuards(W);
    const FVector Origin(W.BeatData().Space.PressHall.Origin,0);
    // The companion traversal fixture checks the authored elevated spawn.
    // This living enforcer isolates the same route's real navigation from
    // sight/hearing, so a blocked corner cannot pass as a timed patrol.
    FloorFixture(W,Origin+FVector(300,2140,0));
    if(!W.Tick(120)) return false;
    FSoraPatrolRoute Route;
    for(const auto& Point:Press::CatwalkRoute)
        Route.Points.Add(Origin+FVector(Point.X,Point.Y,490));
    auto* Guard=SpawnPatrolFixture(W,Press::CatwalkGuard);
    if(!TestNotNull(TEXT("The route fixture has a living rifle enforcer"),Guard)||!W.Tick(60)) return false;
    bool Reached[4]={}; bool Supported=true;
    for(int Frame=0;Frame<9000;++Frame)
    {
        if(!W.Tick(1)) return false;
        const FVector At=Feet(*Guard);
        Supported&=FMath::Abs(At.Z-400.f)<15.f;
        for(int I=0;I<4;++I)
            Reached[I]|=FVector::Dist2D(At,Route.Points[I])<=110.f;
        if(Reached[0]&&Reached[1]&&Reached[2]&&Reached[3]) break;
    }
    AddInfo(FString::Printf(TEXT("Catwalk patrol local feet %s; reached corners %d/%d/%d/%d; velocity %s"),
        *(Feet(*Guard)-Origin).ToString(),Reached[0],Reached[1],Reached[2],Reached[3],*Guard->GetVelocity().ToString()));
    TestTrue(TEXT("The real patrol reaches all four sides instead of skipping blocked goals"),Reached[0]&&Reached[1]&&Reached[2]&&Reached[3]);
    TestTrue(TEXT("The walker remains supported at catwalk height throughout the circuit"),Supported);
    AddInfo(TEXT("Directed real navigation with this enforcer's sight/hearing disabled. This does not qualify authored auditor/drone cadence or ordinary combat."));
    return !HasAnyErrors();
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraPressExitTest,"SoraArena.Campaign.PressExit",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraPressExitTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraPressAutomation;
    if(!FSoraCatalog::Get().Load()) return false;
    FBeatWorld W(*this,TEXT("PressExit"),5,10);
    if(!W.Start()) return false;
    W.Harden(); FreezeGuards(W);
    const auto& Space=W.BeatData().Space;
    auto* Craft=W.Fieldcraft(); auto* C=W.Campaign();
    const FVector Exit(Space.Objectives[3],0);
    if(!W.Press(EKeys::Escape)||!TestTrue(TEXT("The menu rebinds Interact"),W.Hero()->RemapCombatAction(TEXT("Interact"),EKeys::G))||
        !W.Press(EKeys::Escape)) return false;
    FloorFixture(W,Exit);
    if(!W.Tick(5)||!WaitForPressDialogue(W)||!W.Press(EKeys::G)) return false;
    TestEqual(TEXT("Visiting the lift early cannot pre-credit the exit"),C->TaskProgress().Done,0);
    for(int I=0;I<3;++I)
    {
        FloorFixture(W,FVector(Space.Objectives[I],0),90);
        if(!W.Tick(5)||!WaitForPressDialogue(W)||!W.Hold(EKeys::G,270)||!WaitForPressDialogue(W)) return false;
        if(!TestEqual(TEXT("Each real held jam counts once before exit"),C->TaskProgress().Done,I+1)) return false;
    }
    // Deliberate negative-fixture placement on the south deck above the lift.
    // PressCatwalk separately establishes actual input traversal to the deck.
    auto* Player=W.Hero();
    Player->GetCharacterMovement()->StopMovementImmediately();
    Player->SetActorLocation(Exit+FVector(0,-140,402+Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()));
    W.Look(FRotator(0,90,0));
    if(!W.Tick(5)||!TestTrue(TEXT("The negative fixture is supported on the deck above the lift"),FMath::Abs(Feet(*Player).Z-400.f)<5.f)||
        !W.Press(EKeys::G)) return false;
    TestTrue(TEXT("All jams done still cannot exit from the catwalk above the lift"),C->ActiveBeat()==10&&C->TaskProgress().Done==3&&!Craft->CanWorkPress(3));
    TestFalse(TEXT("The lift exit volume excludes the catwalk"),Space.Exit.Contains(Player->GetActorLocation()));
    for(const auto& Volume:Space.Volumes)
        TestFalse(TEXT("Floor dialogue volumes exclude the catwalk layer"),Volume.Contains(FVector(Volume.Center,488)));
    FloorFixture(W,Exit);
    if(!W.Tick(5)||!WaitForPressDialogue(W)||!W.Press(EKeys::G)||!W.Tick(2)) return false;
    TestTrue(TEXT("Returning to the actual floor lift completes the beat"),C->ActiveBeat()!=10||W.Mode()->bChapterComplete);
    AddInfo(TEXT("Directed real input for early-exit refusal, three holds, elevated refusal and floor exit. Positioning is assisted and guards frozen; not ordinary traversal or difficulty acceptance."));
    return !HasAnyErrors();
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraPressPatrolTest,"SoraArena.Campaign.PressPatrolCadence",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraPressPatrolTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraPressAutomation;
    if(!FSoraCatalog::Get().Load()) return false;
    FBeatWorld W(*this,TEXT("PressPatrolCadence"),5,10);
    if(!W.Start()) return false;
    W.Harden(); FreezeGuards(W);
    FloorFixture(W,FVector(W.BeatData().Space.PressHall.Origin+FVector2D(3900,250),0));
    if(!W.Tick(120)||!WaitForPressDialogue(W)) return false;
    ASoraEnemy* Guards[3]={}; ASoraEnemyController* Brains[3]={};
    const int Indices[]={0,1,5};
    for(int I=0;I<3;++I)
    {
        Guards[I]=SpawnPatrolFixture(W,Indices[I]);
        if(!TestNotNull(TEXT("The scheduled patrol fixture spawns"),Guards[I])) return false;
        Brains[I]=Cast<ASoraEnemyController>(Guards[I]->GetController());
        if(!TestNotNull(TEXT("The scheduled patrol has its production brain"),Brains[I])) return false;
    }
    if(!W.Tick(600)||!W.Press(EKeys::Escape)) return false;
    SoraPatrolRules::FLoop Paused[3];
    for(int I=0;I<3;++I) Paused[I]=Brains[I]->PatrolTiming();
    if(!W.Tick(180)) return false;
    for(int I=0;I<3;++I)
        TestTrue(TEXT("Pause does not advance a patrol's clock or physical visits"),
            Brains[I]->PatrolTiming().ElapsedMs==Paused[I].ElapsedMs&&Brains[I]->PatrolTiming().Visited==Paused[I].Visited);
    if(!W.Press(EKeys::Escape)) return false;
    bool Height=true;
    for(int Frame=0;Frame<3600;++Frame)
    {
        if(!W.Tick(1)) return false;
        Height&=FMath::Abs(Feet(*Guards[0]).Z)<15.f&&FMath::Abs(Feet(*Guards[1]).Z)<15.f&&
            FMath::Abs(Feet(*Guards[2]).Z-450.f)<15.f;
    }
    for(int I=0;I<3;++I)
    {
        const auto& Loop=Brains[I]->PatrolTiming(); const int Period=I==2?30000:45000;
        TestTrue(TEXT("A real circuit completes at its authored period"),Loop.Cycles>0&&Loop.LastCycleMs>=Period&&Loop.LastCycleMs<=Period+34);
        TestEqual(TEXT("Every required station was physically visited"),Loop.Visited,I==2?15u:255u);
        TestFalse(TEXT("No missed station deadline is hidden"),Loop.Overdue);
    }
    TestTrue(TEXT("Auditors remain on the floor and the drone stays over the presses"),Height);
    // A jam-inspection errand has priority. Its time is not quietly counted
    // as uninterrupted patrol time, and normal perception remains enabled.
    const auto Before=Brains[0]->PatrolTiming();
    Brains[0]->SetErrand(Guards[0]->GetActorLocation(),FVector(0,1,0),1,0,true,true,70);
    if(!W.Tick(120)) return false;
    TestEqual(TEXT("A competing inspection pauses the regular patrol clock"),Brains[0]->PatrolTiming().ElapsedMs,Before.ElapsedMs);
    Brains[0]->ClearErrand();
    if(!W.Tick(2)) return false;
    TestTrue(TEXT("Regular patrol resumes after the inspection"),Brains[0]->PatrolTiming().ElapsedMs>Before.ElapsedMs);
    AddInfo(TEXT("Actual collision/navigation for two auditors and one drone, with sight/hearing isolated. Periods measure uninterrupted active patrol time; ordinary stealth remains unqualified."));
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraPressPatrolBlockedTest,"SoraArena.Campaign.PressPatrolBlocked",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraPressPatrolBlockedTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraPressAutomation;
    if(!FSoraCatalog::Get().Load()) return false;
    FBeatWorld W(*this,TEXT("PressPatrolBlocked"),5,10);
    if(!W.Start()) return false;
    W.Harden(); FreezeGuards(W);
    FloorFixture(W,FVector(W.BeatData().Space.PressHall.Origin+FVector2D(3900,250),0));
    if(!W.Tick(120)||!WaitForPressDialogue(W)) return false;
    auto* Guard=SpawnPatrolFixture(W,0);
    if(!TestNotNull(TEXT("The obstructed auditor spawns"),Guard)) return false;
    auto* Brain=Cast<ASoraEnemyController>(Guard->GetController());
    if(!TestNotNull(TEXT("The obstructed auditor has its production brain"),Brain)) return false;
    const FVector Goal(W.BeatData().Space.PressHall.Origin+FVector2D(1800,260),0);
    auto* Barrier=Block(W,Goal+FVector(0,0,150),FVector(100,100,150));
    if(!TestNotNull(TEXT("The scheduled station is physically blocked"),Barrier)||!W.Tick(3000)) return false;
    const auto Stopped=Brain->PatrolTiming();
    TestTrue(TEXT("Fifty seconds cannot turn a blocked first leg into a lap"),Stopped.Cycles==0&&Stopped.Legs==0&&Stopped.Visited==0&&Stopped.Overdue);
    Barrier->Destroy();
    for(int Frame=0;Frame<900&&Brain->PatrolTiming().Legs==0;++Frame) if(!W.Tick(1)) return false;
    TestTrue(TEXT("Clearing the obstacle permits exactly the next physical visit"),
        Brain->PatrolTiming().Legs==1&&Brain->PatrolTiming().Visited==2&&FVector::Dist(Feet(*Guard),Goal)<75.f);
    TestTrue(TEXT("A delayed arrival retains the missed-deadline evidence"),Brain->PatrolTiming().Overdue&&Brain->PatrolTiming().Cycles==0);
    AddInfo(TEXT("Directed actual-navigation obstruction; sight/hearing isolated. A clock alone cannot report a completed patrol."));
    return !HasAnyErrors();
}
#endif
