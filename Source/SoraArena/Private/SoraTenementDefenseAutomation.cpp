#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraRecoveryAutomation.h"
#include "SoraEnemyController.h"
#include "SoraEquipmentComponent.h"
#include "SoraWorldBuilder.h"
#include "SoraTenementDefenseRules.h"
#include "SoraTenementQueueRules.h"
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
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraTenementKitchenSupplyTest,"SoraArena.Campaign.Tenements.KitchenSupply",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraTenementKitchenSupplyTest::RunTest(const FString&)
{
    using namespace SoraTenementDefenseAutomation;
    if(!FSoraCatalog::Get().Load())return false;
    FBeatWorld W(*this,TEXT("KitchenSupply"),2,13);if(!Start(W))return false;
    auto* Arena=W.Mode()->Arena();auto* Kit=W.Hero()->GetEquipment();
    FVector Crate;const FString Id=TEXT("vol_b14_supply");
    if(!TestTrue(TEXT("The kitchen's own supply crate is staged"),Arena->SupplyFloor(Id,Crate)))return false;
    const auto P=SoraTenementDefenseRules::SupplyAt;
    TestTrue(TEXT("The crate is on earth beside the manager door, clear of both stairs"),Crate.Equals(FVector(P.X,P.Y,P.Z)));
    FVector Other;TestFalse(TEXT("The spire's supply identity is not active here"),Arena->SupplyFloor(TEXT("sp_spire_base"),Other));
    if(!Kit->EquipCampaignWeapon(18)||!W.Tick(40))return false;
    const int Cap=FSoraCatalog::Get().Weapon(18).Magazine;
    if(!TestEqual(TEXT("The restored yumi starts with twelve arrows"),Kit->Ammo,12))return false;
    W.Look(FRotator(35,0,0));
    if(!W.Hold(EKeys::LeftMouseButton,50)||!W.Tick(90))return false;
    if(!TestEqual(TEXT("A mapped bow release really spends an arrow"),Kit->Ammo,Cap-1))return false;
    if(!W.Press(EKeys::E))return false;
    TestEqual(TEXT("Distant kitchen input does not restock"),Kit->Ammo,Cap-1);
    const unsigned Weapons=W.Campaign()->Progress().WeaponsMask,Completed=W.Campaign()->Progress().CompletedMask;
    W.Hero()->Health-=25.f;const float Health=W.Hero()->Health;
    // Walk from the actual kitchen checkpoint, around the crate to the
    // manager's east step. No hero placement or task-state injection.
    if(!SoraRecoveryAutomation::WalkTo(*W.World,FVector(-2800,3350,90.15))||
       !SoraRecoveryAutomation::WalkTo(*W.World,FVector(-2250,3400,90.15))||
       !SoraRecoveryAutomation::WalkTo(*W.World,FVector(-2250,3660,90.15)))return false;
    W.LookAt(Crate+FVector(0,0,55));
    TestFalse(TEXT("The nearby court outside the 200 cm supply volume cannot refill"),Arena->CanReachSupply(Id,*W.Hero()));
    if(!W.Press(EKeys::E)||!TestEqual(TEXT("Walking nearby never refills automatically"),Kit->Ammo,Cap-1))return false;
    if(!SoraRecoveryAutomation::WalkTo(*W.World,FVector(-2365,3660,112.65)))return false;
    const double Feet=W.Hero()->GetActorLocation().Z-W.Hero()->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    TestTrue(TEXT("Ordinary movement climbed a real doorway step"),Feet>10&&Feet<50);
    W.LookAt(Crate+FVector(0,0,55));
    if(!TestTrue(TEXT("The door's raised approach has a clear line to its supply crate"),Arena->CanReachSupply(Id,*W.Hero())))return false;
    if(!W.Press(EKeys::Escape)||!W.Press(EKeys::E))return false;
    TestEqual(TEXT("Menu input cannot restock"),Kit->Ammo,Cap-1);
    W.Mode()->ResumePlay();if(!W.Tick(3)||!W.Press(EKeys::E))return false;
    TestEqual(TEXT("Normal Interact refills the spent held quiver"),Kit->Ammo,Cap);
    TestEqual(TEXT("Supply keeps the yumi equipped"),W.Hero()->WeaponId,18);
    TestEqual(TEXT("Supply grants no health"),W.Hero()->Health,Health);
    TestEqual(TEXT("Supply grants no weapons"),W.Campaign()->Progress().WeaponsMask,Weapons);
    TestEqual(TEXT("Supply completes no campaign beat"),W.Campaign()->Progress().CompletedMask,Completed);
    if(!W.Press(EKeys::E))return false;
    TestEqual(TEXT("A full quiver cannot overfill"),Kit->Ammo,Cap);
    TestEqual(TEXT("The kitchen defense remains active"),W.Campaign()->ActiveBeat(),13);
    AddInfo(TEXT("The hero walks from the real kitchen spawn and fires/replenishes through mapped input. Health is hardened and then wounded by the fixture; this is a supply-route test, not combat balance or final art acceptance."));
    return !HasAnyErrors();
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraTenementKitchenQueueTest,"SoraArena.Campaign.Tenements.KitchenQueue",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraTenementKitchenQueueTest::RunTest(const FString&)
{
    using namespace SoraTenementDefenseAutomation;
    namespace R=SoraTenementQueueRules;
    if(!FSoraCatalog::Get().Load())return false;
    FBeatWorld W(*this,TEXT("KitchenQueue"),2,13);if(!Start(W))return false;
    auto Residents=W.Fieldcraft()->KitchenResidents();
    if(!TestEqual(TEXT("Six residents queue for the kitchen"),Residents.Num(),R::Count))return false;
    for(int I=0;I<R::Count;++I)
    {
        auto* Resident=Residents[I].Get();
        if(!TestNotNull(TEXT("Every queue place has a real resident"),Resident))return false;
        const auto P=R::Queue(I);
        TestTrue(TEXT("Each resident starts in its own queue place"),FVector::Dist2D(Resident->GetActorLocation(),FVector(P.X,P.Y,0))<2);
        TestFalse(TEXT("Residents cannot be selected by enemy perception, even at contact"),Resident->IsExposed(0));
        const float Health=Resident->Health;
        UGameplayStatics::ApplyDamage(Resident,1000,nullptr,nullptr,UDamageType::StaticClass());
        TestEqual(TEXT("Incidental damage cannot injure a queued resident"),Resident->Health,Health);
        FHitResult Hit;FCollisionQueryParams Query;Query.AddIgnoredActor(W.Hero());
        const FVector Eye=Resident->GetActorLocation()+FVector(0,0,45);
        TestFalse(TEXT("Residents do not intercept a bullet or interaction trace"),
            W.World->GetTestWorld()->LineTraceSingleByChannel(Hit,Eye-FVector(40,0,0),Eye+FVector(40,0,0),ECC_Visibility,Query));
        TestTrue(TEXT("Their capsule still collides with the world"),
            Resident->GetCapsuleComponent()->GetCollisionResponseToChannel(ECC_WorldStatic)==ECR_Block);
    }
    W.Stand(FVector(-3220,3250,0));int Relit=0;
    if(!UntilWave(W,1,Relit))return false;
    auto First=Wave(W,1);for(auto* Enemy:First)Hold(*Enemy);
    if(!TestEqual(TEXT("The fixture uses the real first defense wave"),First.Num(),4))return false;
    auto* Probe=First[0];Probe->SetActorLocation(FVector(-3500,3300,90.15));
    if(!W.Tick(60))return false;
    for(int I=0;I<R::Count;++I)
    {
        const auto P=R::Queue(I);
        TestTrue(TEXT("Enemies outside the volume leave the queue in place"),
            FVector::Dist2D(Residents[I]->GetActorLocation(),FVector(P.X,P.Y,0))<2);
    }
    Probe->SetActorLocation(FVector(-2300,3350,90.15));
    if(!W.Tick(20))return false;
    TestTrue(TEXT("A real enemy entering the court starts the scatter"),
        FVector::Dist2D(Residents[0]->GetActorLocation(),FVector(R::Queue(0).X,R::Queue(0).Y,0))>10);
    if(!W.Press(EKeys::Escape)||!W.Tick(3))return false;
    TArray<FVector> Paused;for(const auto& Resident:Residents)Paused.Add(Resident->GetActorLocation());
    if(!W.Tick(60))return false;
    for(int I=0;I<R::Count;++I)
        TestTrue(TEXT("Menu pause suspends the residents' walk"),Residents[I]->GetActorLocation().Equals(Paused[I],1.f));
    W.Mode()->ResumePlay();
    for(int Frame=0;Frame<600;++Frame)
    {
        TArray<FVector> Before;for(const auto& Resident:Residents)Before.Add(Resident->GetActorLocation());
        if(!W.Tick(1))return false;
        for(int I=0;I<R::Count;++I)
            if(!TestTrue(TEXT("Scatter uses bounded walking and threshold steps, never a warp"),
                FVector::Dist(Before[I],Residents[I]->GetActorLocation())<20))return false;
    }
    for(int I=0;I<R::Count;++I)
    {
        const auto P=R::Home(I);const auto* Resident=Residents[I].Get();
        TestTrue(TEXT("Each resident walks into its own home through the doorway"),
            FVector::Dist2D(Resident->GetActorLocation(),FVector(P.X,P.Y,0))<12&&
            FMath::Abs(Resident->GetActorLocation().Z-105.15)<3&&Resident->GetCharacterMovement()->IsMovingOnGround());
        TestFalse(TEXT("Sheltering does not hide or delete the resident"),Resident->IsHidden());
    }
    UGameplayStatics::ApplyDamage(W.Hero(),W.Hero()->Health,nullptr,nullptr,UDamageType::StaticClass());
    if(!TestTrue(TEXT("Lethal damage reaches the real retry screen"),W.Mode()->bDefeated)||!W.Press(EKeys::Enter))return false;
    for(int I=0;I<3000&&!W.Mode()->IsPlaying();++I)if(!W.Tick(1))return false;
    if(!W.Tick(30)||!TestTrue(TEXT("Retry returns normal controls"),W.Mode()->IsPlaying()))return false;
    const auto Fresh=W.Fieldcraft()->KitchenResidents();
    if(!TestEqual(TEXT("Retry recreates exactly one fresh queue"),Fresh.Num(),R::Count))return false;
    for(int I=0;I<R::Count;++I)
    {
        const auto P=R::Queue(I);
        TestFalse(TEXT("Retry destroys each old resident"),IsValid(Residents[I]));
        if(!TestNotNull(TEXT("Retry creates the new resident"),Fresh[I].Get()))return false;
        TestTrue(TEXT("Retry clears the scattered state"),FVector::Dist2D(Fresh[I]->GetActorLocation(),FVector(P.X,P.Y,0))<2);
    }
    W.Fieldcraft()->Clear();
    TestTrue(TEXT("Beat cleanup releases the whole queue"),W.Fieldcraft()->KitchenResidents().IsEmpty());
    for(const auto& Resident:Fresh)TestFalse(TEXT("No resident survives beat cleanup"),IsValid(Resident));
    AddInfo(TEXT("Directed damage, enemy placement and hardened hero isolate queue behavior. Residents move using real CharacterMovement; ordinary combat and civilian art remain separate."));
    return !HasAnyErrors();
}
#endif
