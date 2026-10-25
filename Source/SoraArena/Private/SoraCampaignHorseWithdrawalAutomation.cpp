#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraEnemy.h"
#include "SoraEnemyController.h"
#include "SoraGameEvents.h"
#include "SoraHorseWithdrawalRules.h"
#include "SoraWorldBuilder.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Misc/ScopeExit.h"

namespace SoraHorseWithdrawalTest
{
using SoraFieldcraftAutomation::FBeatWorld;
namespace R=SoraHorseWithdrawalRules;
void FreezeBody(ASoraEnemy& Enemy,bool Frozen)
{
    Enemy.SetActorTickEnabled(!Frozen);
    Enemy.GetCharacterMovement()->StopMovementImmediately();
    Enemy.GetCharacterMovement()->SetComponentTickEnabled(!Frozen);
    if(auto* Brain=Enemy.GetController()) Brain->SetActorTickEnabled(!Frozen);
}
TArray<TWeakObjectPtr<ASoraEnemy>> Living(FBeatWorld& W)
{
    TArray<TWeakObjectPtr<ASoraEnemy>> Result;
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
        if(It->IsAlive()&&!It->IsActorBeingDestroyed()) Result.Add(*It);
    return Result;
}
bool Ready(FBeatWorld& W)
{
    if(!FSoraCatalog::Get().Load()||!W.Start()) return false;
    W.Harden();
    // Preserve actual arrivals and the real 150-second clock. Combat is
    // deliberately frozen; no task fields, positions or completion are edited.
    for(int I=0;I<9000&&!W.Campaign()->HorseWithdrawalActive();++I)
    {
        for(const auto& Enemy:Living(W)) if(Enemy.IsValid()) FreezeBody(*Enemy.Get(),true);
        if(!W.Tick(1,.02f)) return false;
    }
    return W.Test.TestTrue(TEXT("Actual 150-second task begins a surviving-enemy outro before changing beat"),
        W.Campaign()->HorseWithdrawalActive()&&W.Campaign()->TaskProgress().ElapsedMs>=150000&&W.Campaign()->ActiveBeat()==5);
}
bool AtMuster(const ASoraEnemy& Enemy)
{
    const auto At=Enemy.GetActorLocation();
    return Enemy.GetCharacterMovement()->IsMovingOnGround()&&
        FMath::Abs(At.Z-Enemy.GetCapsuleComponent()->GetScaledCapsuleHalfHeight()-R::GoalZ)<=R::FloorToleranceCm&&
        FVector::DistSquared2D(At,FVector(R::GoalX,R::GoalY,R::GoalZ))<=FMath::Square(double(R::ArrivalCm));
}
int Down(USoraCampaignDirector& C)
{ const auto& S=C.TaskProgress(); return S.Down[0]+S.Down[1]+S.Down[2]; }
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraHorseWithdrawalMovementTest,"SoraArena.Campaign.HorseWithdrawalMovement",
 EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraHorseWithdrawalMovementTest::RunTest(const FString& Parameters)
{
    (void)Parameters; using namespace SoraHorseWithdrawalTest;
    FBeatWorld W(*this,TEXT("HorseWithdrawalMovement"),1,5);
    if(!Ready(W)) return false;
    auto* C=W.Campaign(); const auto Survivors=Living(W);
    if(!TestEqual(TEXT("Six real survivors leave the capped third pod unspawned"),Survivors.Num(),6)) return false;
    TestEqual(TEXT("One authored withdrawal event"),W.Events.FilterByPredicate([](const FString& E)
        { return E==TEXT("event:horse_defense_withdrawal"); }).Num(),1);
    const int BeforeDown=Down(*C); const int DefenseMs=C->TaskProgress().ElapsedMs;
    for(int I=0;I<3;++I) TestFalse(TEXT("No old pod warning survives the won task"),IsValid(C->PodWarning(I)));
    for(const auto& Weak:Survivors)
    {
        auto* E=Weak.Get(); auto* Brain=Cast<ASoraEnemyController>(E->GetController());
        TestTrue(TEXT("Actual survivors receive noncombat navigation errands"),E->IsCampaignWithdrawing()&&Brain&&Brain->HasErrand());
        TestFalse(TEXT("A retreating survivor cannot begin a new attack"),E->TryAttack(*W.Hero(),500));
    }
    FActorSpawnParameters Params; Params.Owner=W.Mode();
    auto* Barrier=W.World->GetTestWorld()->SpawnActor<AActor>(Params);
    if(!Barrier) return false;
    auto* Root=NewObject<USceneComponent>(Barrier); Barrier->SetRootComponent(Root); Root->RegisterComponent(); Barrier->AddInstanceComponent(Root);
    auto* Wall=ASoraWorldBuilder::Shape(Barrier,Root,TEXT("WithdrawalPhysicalBlock"),TEXT("/Engine/BasicShapes/Cube.Cube"),
        FVector(-1700,0,350),FVector(.5,54,8),FLinearColor::Gray);
    if(!Wall) return false;
    Wall->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics); Wall->SetCollisionResponseToAllChannels(ECR_Block);
    Wall->SetCanEverAffectNavigation(true);
    ON_SCOPE_EXIT { if(IsValid(Barrier)&&!Barrier->IsActorBeingDestroyed()) Barrier->Destroy(); };
    for(const auto& E:Survivors) FreezeBody(*E.Get(),false);
    int Fired=0,Completed=0; bool ArrivedAtComplete=false,NoCreditAtComplete=false;
    auto* Bus=USoraGameEvents::Get(W.Hero());
    const auto ShotHandle=Bus->OnWeaponFired.AddLambda([&](const FSoraWeaponFiredEvent& E)
    { if(Survivors.ContainsByPredicate([&](const auto& Weak){return Weak.Get()==E.Shooter.Get();})) ++Fired; });
    const auto CompleteHandle=Bus->OnBeatCompleted.AddLambda([&](const FSoraBeatEvent& E)
    {
        if(E.BeatId!=TEXT("ch02.b06")) return;
        ++Completed; ArrivedAtComplete=true;
        for(const auto& Weak:Survivors) ArrivedAtComplete&=Weak.IsValid()&&Weak->IsAlive()&&AtMuster(*Weak.Get());
        NoCreditAtComplete=Down(*C)==BeforeDown;
    });
    ON_SCOPE_EXIT { Bus->OnWeaponFired.Remove(ShotHandle); Bus->OnBeatCompleted.Remove(CompleteHandle); };
    if(!W.Tick(400,.02f)) return false;
    TestTrue(TEXT("Physical obstruction cannot be accepted as completed withdrawal"),C->HorseWithdrawalActive()&&C->ActiveBeat()==5&&Completed==0);
    for(const auto& E:Survivors) TestTrue(TEXT("No survivor is teleported through the physical wall"),E.IsValid()&&E->GetActorLocation().X>-1740);
    TestEqual(TEXT("The defense clock remains won at its existing value"),C->TaskProgress().ElapsedMs,DefenseMs);
    if(!W.Press(EKeys::Escape)) return false;
    TArray<FVector> Paused; for(const auto& E:Survivors) Paused.Add(E->GetActorLocation());
    if(!W.Tick(40,.02f)) return false;
    for(int I=0;I<Survivors.Num();++I) TestTrue(TEXT("Mapped menu holds retreat movement"),Survivors[I]->GetActorLocation().Equals(Paused[I],.1));
    if(!W.Press(EKeys::Escape)) return false;
    Barrier->Destroy();
    double Walked=0;
    for(int Step=0;Step<4500&&C->ActiveBeat()==5;++Step)
    {
        TArray<FVector> Before; for(const auto& E:Survivors) Before.Add(E.IsValid()?E->GetActorLocation():FVector::ZeroVector);
        if(!W.Tick(1,.02f)) return false;
        if(C->ActiveBeat()!=5) break;
        for(int I=0;I<Survivors.Num();++I)
        {
            if(!Survivors[I].IsValid()) return TestTrue(TEXT("Living survivors remain until the transition"),false);
            const double Distance=FVector::Dist2D(Before[I],Survivors[I]->GetActorLocation());
            if(!TestTrue(TEXT("Retreat consists of normal walking steps"),Distance<20)) return false;
            Walked+=Distance;
        }
    }
    TestEqual(TEXT("All survivors reaching the approach advances to the real back-gate scene"),C->ActiveBeat(),6);
    TestEqual(TEXT("Exactly one completion event"),Completed,1);
    TestTrue(TEXT("Completion observes real surviving actors at the approach without kill credit"),ArrivedAtComplete&&NoCreditAtComplete);
    TestTrue(TEXT("The physical route was actually walked"),Walked>1000);
    TestEqual(TEXT("No survivor fires during withdrawal"),Fired,0);
    const auto* Cue=C->CurrentDialogueCue();
    TestTrue(TEXT("Kohagi's back-gate-clear line follows the finished retreat bark"),Cue&&Cue->Id==TEXT("ch02.b06.kohagi.006"));
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraHorseWithdrawalRetryTest,"SoraArena.Campaign.HorseWithdrawalRetry",
 EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraHorseWithdrawalRetryTest::RunTest(const FString& Parameters)
{
    (void)Parameters; using namespace SoraHorseWithdrawalTest;
    FBeatWorld W(*this,TEXT("HorseWithdrawalRetry"),1,5);
    if(!Ready(W)) return false;
    auto* C=W.Campaign(); const auto Old=Living(W);
    if(Old.IsEmpty()) return false;
    const int BeforeDown=Down(*C);
    SoraDamage::Strike(Old[0].Get(),100000,FSoraHit::Hazard(Old[0]->GetActorLocation()),FVector::ZeroVector,FHitResult(),W.Hero()->GetController(),W.Hero());
    if(!W.Tick(1,.02f)) return false;
    TestEqual(TEXT("A real defeat during retreat still receives ordinary wave credit"),Down(*C),BeforeDown+1);
    TestEqual(TEXT("The freed cap slot does not spawn a pending pod member after the defense"),Living(W).Num(),Old.Num()-1);
    W.Hero()->Health=1;
    SoraDamage::Strike(W.Hero(),100,FSoraHit::Hazard(W.Hero()->GetActorLocation()),FVector::ZeroVector,FHitResult(),nullptr,nullptr);
    TestTrue(TEXT("Real player defeat cancels the outro"),W.Mode()->bDefeated&&!C->HorseWithdrawalActive());
    for(const auto& E:Old) if(E.IsValid()) TestFalse(TEXT("Cancelled survivors retain no withdrawal assignment"),E->IsCampaignWithdrawing());
    if(!W.Press(EKeys::Enter)) return false;
    for(int I=0;I<1500&&!W.Mode()->IsPlaying();++I) if(!W.Tick(1,.02f)) return false;
    TestTrue(TEXT("Retry restarts the defense and full pod warning, without old completion"),
        C->ActiveBeat()==5&&!C->HorseWithdrawalActive()&&C->TaskProgress().ElapsedMs<1000&&C->PodArrival(0).Active);
    for(const auto& E:Old) TestTrue(TEXT("No old survivor remains in the replacement encounter"),!E.IsValid()||E->IsActorBeingDestroyed());
    return true;
}
#endif
