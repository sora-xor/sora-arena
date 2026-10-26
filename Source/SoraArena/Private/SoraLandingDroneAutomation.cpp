#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraEnemy.h"
#include "SoraWorldBuilder.h"
#include "Combat/SoraCombatEffects.h"
#include "Combat/SoraEnemyCatalog.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"

namespace SoraLandingDroneTest
{
using SoraFieldcraftAutomation::FBeatWorld;
namespace R=SoraLandingDroneRules;
void Freeze(ASoraCharacterBase& Body)
{
    Body.SetActorTickEnabled(false);
    Body.GetCharacterMovement()->StopMovementImmediately();
    Body.GetCharacterMovement()->SetComponentTickEnabled(false);
    if(auto* Brain=Body.GetController()) Brain->SetActorTickEnabled(false);
}
ASoraEnemy* Ready(FBeatWorld& W)
{
    if(!FSoraCatalog::Get().Load()||!W.Start()) return nullptr;
    W.Harden();
    ASoraEnemy* Drone=nullptr; int Assigned=0;
    for(TActorIterator<ASoraCharacterBase> It(W.World->GetTestWorld());It;++It)
    {
        if(*It==W.Hero()) continue;
        Freeze(**It);
        if(auto* E=Cast<ASoraEnemy>(*It);E&&E->HasLandingDroneAssignment()) { Drone=E; ++Assigned; }
    }
    if(!W.Test.TestEqual(TEXT("Both actual ch03.b02 drones receive the encounter binding"),Assigned,2)||!Drone) return nullptr;
    for(int I=0;I<3000&&!W.Mode()->IsPlaying();++I) if(!W.Tick(1,.02f)) return nullptr;
    if(!W.Test.TestTrue(TEXT("Authored entry dialogue releases control"),W.Mode()->IsPlaying())) return nullptr;
    // Directed encounter fixture: the actual spawned guard, actual floor and
    // mapped player strike. Patrol motion and other combat are isolated.
    const FVector HeroAt=W.Hero()->GetActorLocation();
    const FVector Above=HeroAt+FVector(120,0,1000);
    FHitResult Floor;
    FCollisionObjectQueryParams Objects;
    Objects.AddObjectTypesToQuery(ECC_WorldStatic); Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
    const FCollisionQueryParams Query(SCENE_QUERY_STAT(LandingDroneFixtureFloor),false,Drone);
    if(!W.Test.TestTrue(TEXT("The fixture has a real supporting floor"),W.World->GetTestWorld()->LineTraceSingleByObjectType(
        Floor,Above,Above-FVector(0,0,3000),Objects,Query))) return nullptr;
    Drone->SetActorLocation(FVector(Above.X,Above.Y,Floor.ImpactPoint.Z+500),false,nullptr,ETeleportType::TeleportPhysics);
    Drone->SetActorRotation(FRotator(0,180,0));
    Drone->SetActorTickEnabled(true); Drone->GetCharacterMovement()->SetComponentTickEnabled(true);
    return Drone;
}
bool Begin(FBeatWorld& W,ASoraEnemy& Drone)
{
    Drone.SetActorRotation((W.Hero()->GetActorLocation()-Drone.GetActorLocation()).GetSafeNormal2D().Rotation());
    return W.Test.TestTrue(TEXT("Actual drone commits its landing attack"),
        Drone.TryAttack(*W.Hero(),FVector::Dist2D(Drone.GetActorLocation(),W.Hero()->GetActorLocation()))&&
        Drone.LandingDroneState().Stage==R::EStage::Mark&&IsValid(Drone.LandingDroneWarning()));
}
bool Low(FBeatWorld& W,ASoraEnemy& Drone)
{
    for(int I=0;I<150&&Drone.LandingDroneState().Stage!=R::EStage::Low;++I)
        if(!W.Tick(1,.02f)) return false;
    return W.Test.TestTrue(TEXT("Swept descent reaches the low exposure window"),Drone.LandingDroneState().Stage==R::EStage::Low);
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraLandingDroneStrikeTest,"SoraArena.Campaign.LandingDrone.TimingAndStrike",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraLandingDroneStrikeTest::RunTest(const FString& Parameters)
{
    (void)Parameters; using namespace SoraLandingDroneTest;
    FBeatWorld W(*this,TEXT("LandingDroneStrike"),2,1); auto* E=Ready(W); if(!E) return false;
    const FVector Home=E->GetActorLocation(); const float Before=W.Hero()->Health;
    FSoraHit Probe=FSoraHit::Melee(W.Hero()->GetActorLocation(),4); float Damage=39;
    TestTrue(TEXT("A high drone admits ordinary wakizashi damage without a lethal override"),E->AdmitDamage(Damage,Probe,W.Hero())&&Damage==39);
    if(!Begin(W,*E)) return false;
    TestTrue(TEXT("The active attack advertises the encounter's 900 ms lock, five damage and 1.5 s root"),
        E->CurrentAttack()->WindupMs==900&&E->CurrentAttack()->Damage==5&&E->CurrentAttack()->RootMs==1500);
    if(!W.Tick(20,.02f)||!W.Press(EKeys::Escape)) return false;
    const int Remaining=E->LandingDroneState().RemainingMs;
    const TWeakObjectPtr<AActor> Warning=E->LandingDroneWarning();
    if(!W.Tick(75,.02f)) return false;
    TestTrue(TEXT("Pause preserves the active warning and its remaining duration"),
        E->LandingDroneState().RemainingMs==Remaining&&E->LandingDroneWarning()==Warning.Get());
    TestTrue(TEXT("The body stays on its high plane during the lock"),E->GetActorLocation().Equals(Home,.01));
    if(!W.Press(EKeys::Escape)) return false;
    for(int I=0;I<80&&E->LandingDroneState().Stage==R::EStage::Mark;++I)
    {
        TestEqual(TEXT("No net is released while the warning is active"),E->LandingDroneState().Releases,0);
        if(!W.Tick(1,.02f)) return false;
    }
    TestEqual(TEXT("Mark completion starts descent instead of firing the net"),E->LandingDroneState().Releases,0);
    if(!Low(W,*E)) return false;
    TestTrue(TEXT("The disc's centre stops 2.5 m above its actual floor"),FMath::IsNearlyEqual(E->GetActorLocation().Z,Home.Z-250.,.05));
    TestEqual(TEXT("The first physical arrival releases exactly one net"),E->LandingDroneState().Releases,1);
    TestFalse(TEXT("Release removes the owned cyan marker"),Warning.IsValid());
    auto* Effects=USoraCombatEffects::Get(E);
    TestTrue(TEXT("The hero left inside the ring is rooted"),Effects&&Effects->IsRooted(W.Hero()));
    TestEqual(TEXT("The landed attack deals the chapter's five damage"),W.Hero()->Health,Before-5.f);
    if(!W.Tick(65,.02f)) return false;
    TestTrue(TEXT("The seizure still holds after 1.3 seconds"),Effects->IsRooted(W.Hero()));
    if(!W.Tick(15,.02f)) return false;
    TestFalse(TEXT("The seizure releases after 1.5 seconds"),Effects->IsRooted(W.Hero()));
    TestTrue(TEXT("The drone remains physically low and vulnerable during recovery"),E->IsLandingDroneLow());
    if(!W.World->TakeUpArm(4)) return false;
    W.LookAt(E->GetActorLocation());
    if(!W.Press(EKeys::LeftMouseButton)||!W.Tick(30,.02f)) return false;
    TestFalse(TEXT("One real mapped wakizashi strike cuts down the low drone"),E->IsAlive());
    TestEqual(TEXT("Defeat cancels the remaining landing attack"),int(E->LandingDroneState().Stage),int(R::EStage::Idle));
    AddInfo(TEXT("Directed actual-guard fixture; patrol shape, visual quality and ordinary full-beat completion remain separate."));
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraLandingDroneObstructionTest,"SoraArena.Campaign.LandingDrone.ObstructionAndReset",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraLandingDroneObstructionTest::RunTest(const FString& Parameters)
{
    (void)Parameters; using namespace SoraLandingDroneTest;
    FBeatWorld W(*this,TEXT("LandingDroneObstruction"),2,1); auto* E=Ready(W); if(!E||!Begin(W,*E)) return false;
    const float Health=W.Hero()->Health; const FVector Home=E->GetActorLocation();
    auto* Obstacle=W.World->GetTestWorld()->SpawnActor<AActor>();
    if(!TestNotNull(TEXT("Physical descent obstruction spawns"),Obstacle)) return false;
    auto* Mesh=ASoraWorldBuilder::Shape(Obstacle,nullptr,TEXT("LandingDroneTestShelf"),TEXT("/Engine/BasicShapes/Cube.Cube"),
        FVector::ZeroVector,FVector(2,2,.2f),FLinearColor(.2f,.2f,.2f));
    Obstacle->SetRootComponent(Mesh); Obstacle->SetActorLocation(Home-FVector(0,0,125));
    Mesh->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics); Mesh->SetCollisionObjectType(ECC_WorldStatic);
    Mesh->SetCollisionResponseToAllChannels(ECR_Block);
    const TWeakObjectPtr<AActor> Warning=E->LandingDroneWarning();
    if(!W.Tick(100,.02f)) return false;
    TestTrue(TEXT("Swept descent stops on the shelf instead of passing through it"),E->GetActorLocation().Z>Home.Z-100);
    TestTrue(TEXT("Blocked descent cancels its attack and warning"),!E->OwnsLandingDroneMotion()&&!Warning.IsValid());
    TestEqual(TEXT("The blocked attack never releases a net"),E->LandingDroneState().Releases,0);
    TestEqual(TEXT("The obstruction prevents all attack damage"),W.Hero()->Health,Health);
    TestFalse(TEXT("The obstruction prevents seizure"),USoraCombatEffects::Get(E)->IsRooted(W.Hero()));
    Obstacle->Destroy();
    if(!Begin(W,*E)||!W.Tick(10,.02f)) return false;
    const TWeakObjectPtr<AActor> Interrupted=E->LandingDroneWarning();
    E->Stagger(250);
    TestTrue(TEXT("A real stagger discards the unspent lock"),!E->OwnsLandingDroneMotion()&&!Interrupted.IsValid());
    if(!W.Tick(20,.02f)||!Begin(W,*E)) return false;
    const TWeakObjectPtr<ASoraEnemy> Old=E;
    const TWeakObjectPtr<AActor> OldWarning=E->LandingDroneWarning();
    W.Mode()->ResetRound();
    TestTrue(TEXT("Checkpoint retry retires the old drone and marker"),!Old.IsValid()&&!OldWarning.IsValid());
    int Fresh=0;
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
        if(It->HasLandingDroneAssignment())
        { ++Fresh; SoraLandingDroneTest::Freeze(**It); TestEqual(TEXT("Reloaded drones have no stale release"),It->LandingDroneState().Releases,0); }
    TestEqual(TEXT("Retry rebuilds both landing drones"),Fresh,2);
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraLandingDroneBaitTest,"SoraArena.Campaign.LandingDrone.BaitAndGenericIsolation",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraLandingDroneBaitTest::RunTest(const FString& Parameters)
{
    (void)Parameters; using namespace SoraLandingDroneTest;
    FBeatWorld W(*this,TEXT("LandingDroneBait"),2,1); auto* E=Ready(W); if(!E||!Begin(W,*E)) return false;
    const FVector Home=E->GetActorLocation(), Lock=E->LandingDroneWarning()->GetActorLocation();
    const float Health=W.Hero()->Health;
    W.Stand(W.Hero()->GetActorLocation()+FVector(0,400,0));
    if(!W.Tick(10,.02f)) return false;
    TestTrue(TEXT("Moving the hero cannot drag the locked ring"),E->LandingDroneWarning()->GetActorLocation().Equals(Lock,.01));
    if(!Low(W,*E)) return false;
    TestEqual(TEXT("A baited net misses the hero outside the ring"),W.Hero()->Health,Health);
    TestFalse(TEXT("A baited net does not root the hero"),USoraCombatEffects::Get(E)->IsRooted(W.Hero()));
    for(int I=0;I<350&&E->OwnsLandingDroneMotion();++I) if(!W.Tick(1,.02f)) return false;
    TestTrue(TEXT("Low recovery ends with a swept return to the original flight plane"),!E->OwnsLandingDroneMotion()&&E->GetActorLocation().Equals(Home,.01));
    TestEqual(TEXT("The complete attack fires only once"),E->LandingDroneState().Releases,1);
    auto* Generic=ASoraEnemy::SpawnArchetype(*W.World->GetTestWorld(),TEXT("drone"),99,Home+FVector(0,600,0),FRotator::ZeroRotator);
    if(!TestNotNull(TEXT("Unbound generic drone spawns"),Generic)) return false;
    SoraLandingDroneTest::Freeze(*Generic);
    Generic->SetActorRotation((W.Hero()->GetActorLocation()-Generic->GetActorLocation()).GetSafeNormal2D().Rotation());
    if(!TestTrue(TEXT("Generic drone can commit its normal attack"),Generic->TryAttack(*W.Hero(),600))) return false;
    TestTrue(TEXT("Other encounters retain 800 ms mark, zero damage and no landing assignment"),
        !Generic->HasLandingDroneAssignment()&&Generic->CurrentAttack()->WindupMs==800&&Generic->CurrentAttack()->Damage==0);
    Generic->Destroy();
    return !HasAnyErrors();
}
#endif
