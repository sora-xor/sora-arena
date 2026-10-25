#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraEnemy.h"
#include "SoraHorse.h"
#include "SoraProjectile.h"
#include "SoraGameEvents.h"
#include "SoraWorldBuilder.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Misc/ScopeExit.h"

namespace SoraHorseShellTest
{
using SoraFieldcraftAutomation::FBeatWorld;
void FreezeBody(ASoraCharacterBase& Body)
{
    Body.SetActorTickEnabled(false); Body.GetCharacterMovement()->StopMovementImmediately();
    Body.GetCharacterMovement()->SetComponentTickEnabled(false);
    if(auto* Brain=Body.GetController()) Brain->SetActorTickEnabled(false);
}
bool Tick(FBeatWorld& W,ASoraEnemy* Active=nullptr,int Frames=1)
{
    for(int I=0;I<Frames;++I)
    {
        for(TActorIterator<ASoraCharacterBase> It(W.World->GetTestWorld());It;++It)
            if(*It!=W.Hero()&&*It!=Active) FreezeBody(**It);
        if(!W.Tick(1,.02f)) return false;
    }
    return true;
}
ASoraEnemy* Ready(FBeatWorld& W)
{
    if(!FSoraCatalog::Get().Load()||!W.Start()) return nullptr;
    W.Harden();
    for(int I=0;I<5000;++I)
    {
        for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
            if(It->HasHorseShellAssignment())
            {
                auto* E=*It; E->CancelHorseShell(); FreezeBody(*E);
                // Directed combat fixture: the real pod-B opponent and real
                // horses remain; only poses and unrelated combat are isolated.
                E->SetActorLocation(FVector(-1200,-1050,E->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+2.5f),false,nullptr,ETeleportType::TeleportPhysics);
                E->SetActorRotation(FRotator::ZeroRotator);
                W.Stand(FVector(-2700,0,0));
                E->SetActorTickEnabled(true); E->GetCharacterMovement()->SetComponentTickEnabled(true);
                E->GetCharacterMovement()->SetMovementMode(MOVE_Falling);
                if(auto* Brain=E->GetController()) Brain->SetActorTickEnabled(true);
                W.Test.TestEqual(TEXT("The actual second pod has impacted before its grenadier arrives"),W.Campaign()->PodArrival(1).Impacts,1);
                return E;
            }
        if(!Tick(W)) return nullptr;
    }
    W.Test.AddError(TEXT("The registered pod-B grenadier never arrived")); return nullptr;
}
bool Warning(FBeatWorld& W,ASoraEnemy& E)
{
    for(int I=0;I<600&&!E.IsWindingUp();++I) if(!Tick(W,&E)) return false;
    return W.Test.TestTrue(TEXT("Real controller commits a visible shell warning"),E.IsWindingUp()&&IsValid(E.HorseShellWarning()));
}
ASoraProjectile* Release(FBeatWorld& W,ASoraEnemy& E)
{
    const int Before=E.HorseShellState().Releases;
    for(int I=0;I<400&&E.HorseShellState().Releases==Before;++I) if(!Tick(W,&E)) return nullptr;
    for(TActorIterator<ASoraProjectile> It(W.World->GetTestWorld());It;++It)
        if(It->GetOwner()==&E&&It->HorseShellCurrent()) return *It;
    W.Test.AddError(TEXT("A real swept shell was not released")); return nullptr;
}
bool Land(FBeatWorld& W,ASoraEnemy* E,TWeakObjectPtr<ASoraProjectile> Shot)
{
    for(int I=0;I<250&&Shot.IsValid()&&!Shot->IsActorBeingDestroyed();++I) if(!Tick(W,E)) return false;
    return W.Test.TestTrue(TEXT("The real projectile reaches a terminal contact"),!Shot.IsValid()||Shot->IsActorBeingDestroyed());
}
AActor* Wall(FBeatWorld& W,float X)
{
    auto* Actor=W.World->GetTestWorld()->SpawnActor<AActor>();
    if(!Actor) return nullptr;
    auto* Mesh=ASoraWorldBuilder::Shape(Actor,nullptr,TEXT("ShellTestCover"),TEXT("/Engine/BasicShapes/Cube.Cube"),
        FVector::ZeroVector,FVector(.3f,5.f,4.f),FLinearColor(.2f,.2f,.2f));
    Actor->SetRootComponent(Mesh); Actor->SetActorLocation(FVector(X,-1050,200));
    Mesh->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
    Mesh->SetCollisionObjectType(ECC_WorldStatic); Mesh->SetCollisionResponseToAllChannels(ECR_Block);
    Mesh->SetCanEverAffectNavigation(false);
    return Actor;
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraHorseShellClockTest,"SoraArena.Campaign.HorseShellClockAndImpact",
 EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraHorseShellClockTest::RunTest(const FString& Parameters)
{
    (void)Parameters; using namespace SoraHorseShellTest;
    FBeatWorld W(*this,TEXT("HorseShellClock"),1,5); auto* E=Ready(W); if(!E||!Warning(W,*E)) return false;
    auto* C=W.Campaign(); auto* Bus=USoraGameEvents::Get(E);
    TArray<int64> Releases;
    const auto Fired=Bus->OnWeaponFired.AddLambda([&](const FSoraWeaponFiredEvent& Event)
    { if(Event.Shooter==E&&Event.Kind==ESoraShotKind::Shell) Releases.Add(E->HorseShellState().ClockMs); });
    ON_SCOPE_EXIT { Bus->OnWeaponFired.Remove(Fired); };
    const TWeakObjectPtr<AActor> Mark=E->HorseShellWarning();
    if(!Tick(W,E,30)||!W.Press(EKeys::Escape)) return false;
    const auto Paused=E->HorseShellState().ClockMs;
    if(!W.Tick(30,.02f)) return false;
    TestTrue(TEXT("Menu holds both the warning clock and the same visible marker"),
        E->HorseShellState().ClockMs==Paused&&E->HorseShellWarning()==Mark.Get());
    if(!W.Press(EKeys::Escape)) return false;
    E->Stagger(1000);
    TestTrue(TEXT("A real stagger cancels the unspent warning"),!E->IsWindingUp()&&!Mark.IsValid());
    TestEqual(TEXT("An interrupted warning fired nothing"),E->HorseShellState().Releases,0);
    if(!Warning(W,*E)) return false;
    const auto Started=E->HorseShellState().WarningStartedMs;
    if(!Tick(W,E,60)) return false;
    TestEqual(TEXT("No release during the first 1.2 seconds of the fresh warning"),E->HorseShellState().Releases,0);
    TestEqual(TEXT("No synthetic proximity damage to the horse"),C->TaskProgress().TargetHp[0],400);
    auto* Shot=Release(W,*E); if(!Shot) return false;
    TestTrue(TEXT("Observed active warning lasts at least 1400 ms before release"),E->HorseShellState().ClockMs-Started>=1400);
    if(!Land(W,E,Shot)) return false;
    TestEqual(TEXT("A real armed shell deals the canonical 35 horse damage"),C->TaskProgress().TargetHp[0],365);
    TestEqual(TEXT("The farther horse remains outside this blast"),C->TaskProgress().TargetHp[1],400);
    if(!Warning(W,*E)) return false;
    Shot=Release(W,*E); if(!Shot) return false;
    TestTrue(TEXT("Continuous valid aim releases at six active seconds within one 20 ms tick"),
        Releases.Num()==2&&Releases[1]-Releases[0]>=6000&&Releases[1]-Releases[0]<=6020);
    auto* Ally=ASoraEnemy::SpawnArchetype(*W.World->GetTestWorld(),TEXT("enforcer_rifle"),30,FVector(800,-850,100),FRotator::ZeroRotator);
    if(!TestNotNull(TEXT("Live enemy beside the landing point"),Ally)) return false;
    FreezeBody(*Ally); const float AllyHp=Ally->Health;
    // Destroying the shooter clears the engine instigator pointer; launch
    // faction must still prevent this released shell hurting fellow enemies.
    E->Destroy();
    if(!Land(W,nullptr,Shot)) return false;
    TestEqual(TEXT("A released shell survives its shooter's removal"),C->TaskProgress().TargetHp[0],330);
    TestEqual(TEXT("The shell retains its original faction after shooter removal"),Ally->Health,AllyHp);
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraHorseShellBaitTest,"SoraArena.Campaign.HorseShellBaitAndCancellation",
 EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraHorseShellBaitTest::RunTest(const FString& Parameters)
{
    (void)Parameters; using namespace SoraHorseShellTest;
    FBeatWorld W(*this,TEXT("HorseShellBait"),1,5); auto* E=Ready(W); if(!E) return false;
    W.Stand(FVector(-300,-1050,0));
    if(!Warning(W,*E)) return false;
    const FVector Mark=E->HorseShellWarning()->GetActorLocation();
    TestTrue(TEXT("A clearly nearer visible hero baits the shell away from the horse"),FVector::Dist2D(Mark,W.Hero()->GetActorLocation())<1);
    W.Stand(FVector(-2700,0,0));
    if(!Tick(W,E,10)) return false;
    TestTrue(TEXT("Moving away cannot drag the committed landing marker"),E->HorseShellWarning()->GetActorLocation().Equals(Mark,.01));
    auto* Shot=Release(W,*E); if(!Shot||!Land(W,E,Shot)) return false;
    TestEqual(TEXT("The baited shot misses both horses"),W.Campaign()->TaskProgress().TargetHp[0]+W.Campaign()->TaskProgress().TargetHp[1],800);
    if(!Warning(W,*E)) return false;
    Shot=Release(W,*E); if(!Shot) return false;
    const TWeakObjectPtr<ASoraProjectile> WeakShot=Shot;
    auto* Bus=USoraGameEvents::Get(E); bool Cancelled=false;
    const auto Detonated=Bus->OnDetonated.AddLambda([&](const FSoraDetonatedEvent& Event)
    { if(Event.Instigator==E) { Cancelled=true; W.Campaign()->ClearEncounter(); } });
    ON_SCOPE_EXIT { Bus->OnDetonated.Remove(Detonated); };
    if(!Land(W,E,Shot)) return false;
    TestTrue(TEXT("Real detonation callback retired the encounter and its projectile"),Cancelled&&!WeakShot.IsValid());
    TestEqual(TEXT("A retired detonation applies no stale horse damage"),W.Campaign()->TaskProgress().TargetHp[0],400);
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraHorseShellCoverTest,"SoraArena.Campaign.HorseShellCoverAndDud",
 EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraHorseShellCoverTest::RunTest(const FString& Parameters)
{
    (void)Parameters; using namespace SoraHorseShellTest;
    FBeatWorld W(*this,TEXT("HorseShellCover"),1,5); auto* E=Ready(W); if(!E) return false;
    auto* Bus=USoraGameEvents::Get(E); int Bursts=0; FVector BlastPoint;
    const auto Event=Bus->OnDetonated.AddLambda([&](const FSoraDetonatedEvent& D)
    { if(D.Instigator==E) { ++Bursts; BlastPoint=D.Location; } });
    ON_SCOPE_EXIT { Bus->OnDetonated.Remove(Event); };
    if(!Warning(W,*E)) return false;
    auto* Cover=Wall(W,650); if(!TestNotNull(TEXT("Physical cover after aim is locked"),Cover)) return false;
    auto* Shot=Release(W,*E); if(!Shot||!Land(W,E,Shot)) return false;
    TestTrue(TEXT("A real armed contact detonated within horse blast range"),Bursts==1&&
        FVector::Dist(BlastPoint,W.Campaign()->TreatmentHorse(0)->GetActorLocation())<300);
    TestEqual(TEXT("Physical cover blocks horse blast damage"),W.Campaign()->TaskProgress().TargetHp[0],400);
    Cover->Destroy();
    if(!Warning(W,*E)) return false;
    Cover=Wall(W,-1030); if(!Cover) return false;
    Shot=Release(W,*E); if(!Shot||!Land(W,E,Shot)) return false;
    TestEqual(TEXT("The shell stopped before 200 cm never broadcasts a detonation"),Bursts,1);
    TestEqual(TEXT("The dud deals no horse damage"),W.Campaign()->TaskProgress().TargetHp[0],400);
    Cover->Destroy();
    return !HasAnyErrors();
}
#endif
