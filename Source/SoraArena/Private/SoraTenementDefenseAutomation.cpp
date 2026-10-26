#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraRecoveryAutomation.h"
#include "SoraEnemyController.h"
#include "SoraTenementDefenseRules.h"
#include "Combat/SoraCombatEffects.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/DamageType.h"

namespace SoraTenementDefenseAutomation
{
using SoraFieldcraftAutomation::FBeatWorld;
bool Start(FBeatWorld& W)
{
    if(!W.Start())return false;
    W.Harden();
    for(int I=0;I<3000&&!W.Mode()->IsPlaying();++I)if(!W.Tick(1))return false;
    return W.Test.TestTrue(TEXT("Kitchen checkpoint releases normal controls"),W.Mode()->IsPlaying());
}
TArray<ASoraEnemy*> Wave(FBeatWorld& W,int Number)
{
    TArray<ASoraEnemy*> Result;
    const FName Tag(*FString::Printf(TEXT("TenementWave%d"),Number));
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
        if(It->Tags.Contains(Tag)&&It->IsEnemy()&&It->IsAlive())Result.Add(*It);
    Result.Sort([](const ASoraEnemy& A,const ASoraEnemy& B){return A.EnemySlot()<B.EnemySlot();});
    return Result;
}
void Hold(ASoraEnemy& E)
{
    E.SetActorTickEnabled(false);E.GetCharacterMovement()->StopMovementImmediately();
    E.GetCharacterMovement()->SetComponentTickEnabled(false);
    if(auto* C=E.GetController())C->SetActorTickEnabled(false);
}
void Remove(FBeatWorld& W,const TArray<ASoraEnemy*>& Enemies)
{
    // This fixture checks entry/timing/flight, not combat difficulty. Real
    // damage and seal-cut interfaces settle the opponents before cleanup.
    for(auto* E:Enemies)
    {
        UGameplayStatics::ApplyDamage(E,E->Health+1000,W.Hero()->GetController(),W.Hero(),UDamageType::StaticClass());
        if(E->CanCutSeal())E->CutSeal(W.Hero());
        E->Destroy();
    }
}
bool Relight(FBeatWorld& W,int Index)
{
    const FVector Fire=W.Fieldcraft()->FireLocation(Index);
    if(!SoraRecoveryAutomation::WalkTo(*W.World,Fire+FVector(80,0,90.15)))return false;
    W.LookAt(Fire+FVector(0,0,35));
    const int Before=W.Campaign()->TaskProgress().Progress;
    if(!W.Hold(EKeys::E,90))return false;
    if(!W.Test.TestEqual(TEXT("A short relight hold keeps progress paused"),W.Campaign()->TaskProgress().Progress,Before)||
       !W.Test.TestEqual(TEXT("Releasing before two seconds leaves the fire out"),W.Fieldcraft()->FiresOut(),1))return false;
    if(!W.Hold(EKeys::E,125)||!W.Test.TestEqual(TEXT("A fresh two-second hold relights the cookfire"),W.Fieldcraft()->FiresOut(),0))return false;
    return SoraRecoveryAutomation::WalkTo(*W.World,FVector(-3220,3250,90.15));
}
bool UntilWave(FBeatWorld& W,int Number,int& Relit)
{
    for(int Frame=0;Frame<9000;++Frame)
    {
        if(!Wave(W,Number).IsEmpty())return true;
        if(W.Fieldcraft()->FiresOut()>0)
        {
            const int Before=W.Campaign()->TaskProgress().Progress;
            if(!W.Tick(60)||!W.Test.TestEqual(TEXT("A guttered fire suspends the real beat clock"),W.Campaign()->TaskProgress().Progress,Before))return false;
            if(!Relight(W,Relit++))return false;
        }
        if(!W.Tick(1))return false;
    }
    return W.Test.TestTrue(TEXT("The authored progress threshold releases its wave"),false);
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraTenementKitchenVolumeTest,"SoraArena.Campaign.Tenements.KitchenVolume",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraTenementKitchenVolumeTest::RunTest(const FString&)
{
    using namespace SoraTenementDefenseAutomation;
    if(!FSoraCatalog::Get().Load())return false;
    FBeatWorld W(*this,TEXT("KitchenVolume"),2,13);if(!Start(W))return false;
    for(const FVector2D P:{FVector2D(-2300,3350),FVector2D(-2800,2300)})
    {
        W.Stand(FVector(P,0));if(!W.Tick(5))return false;
        const int Before=W.Campaign()->TaskProgress().Progress;
        if(!W.Tick(60))return false;
        TestTrue(TEXT("The east court and last six metres of alley both support work"),W.Campaign()->TaskProgress().Progress>Before);
    }
    W.Stand(FVector(-2800,2100,0));if(!W.Tick(5))return false;
    const int Outside=W.Campaign()->TaskProgress().Progress;
    if(!W.Tick(60))return false;
    TestEqual(TEXT("The lower alley is outside the defense volume"),W.Campaign()->TaskProgress().Progress,Outside);
    if(!W.Press(EKeys::Escape)||!W.Tick(60))return false;
    TestEqual(TEXT("Menu pause cannot advance kitchen work"),W.Campaign()->TaskProgress().Progress,Outside);
    AddInfo(TEXT("Directed placement isolates hold-volume and pause semantics; this is not an ordinary-play completion test."));
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraTenementDefenseWavesTest,"SoraArena.Campaign.Tenements.DefenseWaves",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraTenementDefenseWavesTest::RunTest(const FString&)
{
    using namespace SoraTenementDefenseAutomation;
    namespace R=SoraTenementDefenseRules;
    if(!FSoraCatalog::Get().Load())return false;
    FBeatWorld W(*this,TEXT("KitchenDefenseWaves"),2,13);if(!Start(W))return false;
    W.Stand(FVector(-3220,3250,0));int Relit=0;
    if(!UntilWave(W,1,Relit))return false;
    auto First=Wave(W,1);
    if(!TestEqual(TEXT("First wave includes both rifles and both conscripts"),First.Num(),4))return false;
    TSet<int> Positions;
    for(auto* E:First)
    {
        const FVector P=E->GetActorLocation();Hold(*E);
        TestTrue(TEXT("The first wave enters in the alley mouth"),E->Tags.Contains(TEXT("sp_b14_alley_mouth"))&&FMath::Abs(P.X+2800)<20&&FMath::Abs(P.Z-90.15)<5);
        const int Index=FMath::RoundToInt((P.Y-450)/120);Positions.Add(Index);
        TestTrue(TEXT("Each group member has its own entry position"),Index>=0&&Index<4&&FMath::Abs(P.Y-(450+Index*120))<20);
    }
    TestEqual(TEXT("No first-wave bodies share a spawn"),Positions.Num(),4);
    // The far east court is beyond the former 9 m anchor test. The west
    // exterior is close to that anchor but outside the authored volume.
    auto* Probe=First[0];Probe->SetActorLocation(FVector(-2300,3350,90.15));
    if(!W.Tick(2))return false;const int Contested=W.Campaign()->TaskProgress().Progress;
    if(!W.Tick(60))return false;
    TestEqual(TEXT("An enemy in the far court pauses work"),W.Campaign()->TaskProgress().Progress,Contested);
    Probe->SetActorLocation(FVector(-3500,3300,90.15));
    if(!W.Tick(60))return false;
    TestTrue(TEXT("An enemy outside the west fence does not contest the kitchen"),W.Campaign()->TaskProgress().Progress>Contested);
    Remove(W,First);
    if(!UntilWave(W,2,Relit))return false;
    auto Air=Wave(W,2);
    if(!TestEqual(TEXT("Second wave has exactly two inventory drones"),Air.Num(),2))return false;
    for(int I=0;I<2;++I)
    {
        R::FPoint P;R::Spawn(1,0,I,P);
        auto* Brain=Cast<ASoraEnemyController>(Air[I]->GetController());
        TestTrue(TEXT("Each drone starts at its named six-metre west-fence entry"),
            Air[I]->Tags.Contains(TEXT("sp_b14_backfence_air"))&&FVector::Dist(Air[I]->GetActorLocation(),FVector(P.X,P.Y,P.Z))<20&&Brain&&Brain->HasTenementDefenseFlight());
    }
    bool Netted=false;
    auto* Effects=USoraCombatEffects::Get(W.Hero());
    if(!TestNotNull(TEXT("The runtime combat-effect subsystem exists"),Effects))return false;
    for(int Frame=0;Frame<600;++Frame)
    {
        const FVector Before[]={Air[0]->GetActorLocation(),Air[1]->GetActorLocation()};
        if(!W.Tick(1))return false;
        Netted=Netted||Effects->IsRooted(W.Hero());
        for(int I=0;I<2;++I)
        {
            TestTrue(TEXT("Flight uses bounded movement rather than a teleport"),FVector::Dist(Before[I],Air[I]->GetActorLocation())<=12);
            TestTrue(TEXT("The approach retains its authored six-metre plane"),FMath::Abs(Air[I]->GetActorLocation().Z-600)<5);
        }
    }
    for(int I=0;I<2;++I)
    {
        const auto P=R::FlightPoint(I,1);
        TestTrue(TEXT("The live drone reaches its queue-facing station"),FVector::Dist(Air[I]->GetActorLocation(),FVector(P.X,P.Y,P.Z))<45);
        Hold(*Air[I]);
    }
    TestTrue(TEXT("The live net attack actually roots its target"),Netted);
    if(!W.Tick(120)||!TestFalse(TEXT("Root expires before isolating aerial contest"),Effects->IsRooted(W.Hero()))||
       !TestTrue(TEXT("The hero is standing for the contest check"),W.Hero()->GetCharacterMovement()->IsMovingOnGround()))return false;
    const int AirHold=W.Campaign()->TaskProgress().Progress;
    if(!W.Tick(60))return false;
    TestEqual(TEXT("Drones on the upper face contest the kitchen"),W.Campaign()->TaskProgress().Progress,AirHold);
    Remove(W,Air);
    if(!UntilWave(W,3,Relit))return false;
    auto Last=Wave(W,3);
    if(!TestEqual(TEXT("Third wave contains a retainer and rifle"),Last.Num(),2))return false;
    for(int I=0;I<2;++I)
    {
        const FVector P=Last[I]->GetActorLocation();Hold(*Last[I]);
        TestTrue(TEXT("Late infantry reuse the alley entry rather than old drone slots"),
            Last[I]->Tags.Contains(TEXT("sp_b14_alley_mouth"))&&FMath::Abs(P.X+2800)<20&&FMath::Abs(P.Y-(450+I*120))<20&&FMath::Abs(P.Z-90.15)<5);
    }
    if(!W.Tick(2))return false;
    if(W.Fieldcraft()->FiresOut()>0&&!Relight(W,Relit++))return false;
    TestEqual(TEXT("All three authored cookfire interruptions were exercised"),Relit,3);
    AddInfo(TEXT("Real beat time, held relighting and live drone flight/attacks; fixture hardens the hero, holds/repositions one probe and removes completed enemy groups. Ordinary combat balance and release acceptance remain unqualified."));
    return !HasAnyErrors();
}
#endif
