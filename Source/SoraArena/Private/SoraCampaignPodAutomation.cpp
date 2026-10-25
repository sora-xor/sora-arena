#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraEnemy.h"
#include "SoraHorse.h"
#include "SoraGameEvents.h"
#include "SoraWorldBuilder.h"
#include "Components/CapsuleComponent.h"
#include "Misc/ScopeExit.h"

namespace SoraPodTest
{
using SoraFieldcraftAutomation::FBeatWorld;
void Freeze(ASoraCharacterBase& Body)
{
    Body.SetActorTickEnabled(false);
    Body.GetCharacterMovement()->StopMovementImmediately();
    Body.GetCharacterMovement()->SetComponentTickEnabled(false);
    if(auto* Brain=Body.GetController()) Brain->SetActorTickEnabled(false);
}
void Isolate(FBeatWorld& W)
{
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It) Freeze(*It);
}
bool Tick(FBeatWorld& W,float Delta=.02f)
{ Isolate(W); return W.Tick(1,Delta); }
bool Until(FBeatWorld& W,double Deadline)
{
    // Use the world's observed game clock, never assume a large requested
    // delta survives UWorld's clamp. Every request is at most 20 ms.
    int Steps=0;
    while(W.World->GetTestWorld()->GetTimeSeconds()<Deadline-.00001&&++Steps<20000)
    {
        const double Left=Deadline-W.World->GetTestWorld()->GetTimeSeconds();
        if(!Tick(W,float(FMath::Min(.02,Left)))) return false;
    }
    return W.Test.TestTrue(TEXT("Observed game clock reaches the bounded-step deadline"),
        W.World->GetTestWorld()->GetTimeSeconds()>=Deadline-.0001);
}
bool PodTime(FBeatWorld& W,int Wave,int Milliseconds)
{
    const double Start=W.World->GetTestWorld()->GetTimeSeconds();
    const int Before=W.Campaign()->PodArrival(Wave).ElapsedMs;
    if(!W.Test.TestTrue(TEXT("Requested warning boundary is still ahead"),Before<Milliseconds)) return false;
    if(!Until(W,Start+(Milliseconds-Before)/1000.0)) return false;
    const int After=W.Campaign()->PodArrival(Wave).ElapsedMs;
    return W.Test.TestTrue(TEXT("Pod active time agrees with observed world time within 2 ms"),
        After>=Milliseconds-2&&After<=Milliseconds+1);
}
bool Ready(FBeatWorld& W)
{
    if(!FSoraCatalog::Get().Load()||!W.Start()) return false;
    W.Harden();
    for(int I=0;I<1500&&!W.Mode()->IsPlaying();++I) if(!Tick(W)) return false;
    return W.Test.TestTrue(TEXT("Authored defense and initial visible warning are active"),
        W.Campaign()->ActiveBeat()==5&&W.Mode()->IsPlaying()&&W.Campaign()->PodArrival(0).Active&&W.Campaign()->PodWarning(0));
}
TArray<ASoraEnemy*> Living(FBeatWorld& W)
{
    TArray<ASoraEnemy*> Result;
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
        if(It->IsAlive()&&!It->IsActorBeingDestroyed()) Result.Add(*It);
    return Result;
}
ASoraEnemy* Target(FBeatWorld& W,const FVector& At,bool Invulnerable=false)
{
    FSoraEnemyTuning Tuning; Tuning.bInvulnerable=Invulnerable;
    auto* Enemy=ASoraEnemy::SpawnArchetype(*W.World->GetTestWorld(),TEXT("enforcer_rifle"),20,At,
        (W.BeatData().Space.PodArrivals[0].Floor-At).Rotation(),nullptr,&Tuning);
    if(Enemy) { Enemy->MaxHealth=Enemy->Health=1000; Freeze(*Enemy); }
    return Enemy;
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraPodClockTest,"SoraArena.Campaign.PodArrivalsClockAndCap",
 EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraPodClockTest::RunTest(const FString& Parameters)
{
    (void)Parameters; using namespace SoraPodTest;
    FBeatWorld W(*this,TEXT("PodClockCap"),1,5);
    if(!Ready(W)) return false;
    auto* C=W.Campaign();
    TestTrue(TEXT("Horse A uses its original named position"),C->TreatmentHorse(0)->GetActorLocation().Equals(FVector(800,-1050,90),.01));
    TestTrue(TEXT("Horse B uses its original named position"),C->TreatmentHorse(1)->GetActorLocation().Equals(FVector(1200,-1050,90),.01));
    if(!PodTime(W,0,900)) return false;
    const int BeforeMenu=C->PodArrival(0).ElapsedMs;
    if(!W.Press(EKeys::Escape)||!W.Tick(30,.02f)) return false;
    TestEqual(TEXT("Mapped menu pause earns no warning time"),C->PodArrival(0).ElapsedMs,BeforeMenu);
    if(!W.Press(EKeys::Escape)||!PodTime(W,0,2498)) return false;
    TestEqual(TEXT("No impact before the observed 2.5-second warning boundary"),C->PodArrival(0).Impacts,0);
    TestEqual(TEXT("No member emerges before impact"),Living(W).Num(),0);
    if(!Tick(W,.019f)) return false;
    TestEqual(TEXT("Crossing the deadline resolves exactly one impact"),C->PodArrival(0).Impacts,1);
    TestEqual(TEXT("Three first-wave members emerge after their own impact"),Living(W).Num(),3);
    TestFalse(TEXT("Completed warning is removed"),IsValid(C->PodWarning(0)));
    for(auto* Enemy:Living(W)) TestEqual(TEXT("New arrivals did not take their own impact"),Enemy->Health,Enemy->MaxHealth);
    // Ordinary enemies are frozen at their real arrival positions. This
    // isolates timing/cap from combat difficulty and provisional siege pressure.
    for(int Wave=1;Wave<3;++Wave)
    {
        const int Release=Wave==1?45000:95000;
        for(int I=0;I<6000&&!C->PodArrival(Wave).Active;++I) if(!Tick(W)) return false;
        TestTrue(TEXT("Wave activates no earlier than its existing task release"),C->TaskProgress().ElapsedMs>=Release&&C->PodArrival(Wave).Active);
        TestTrue(TEXT("Late frame does not backdate the new warning"),C->PodArrival(Wave).ElapsedMs<=20);
        if(!PodTime(W,Wave,2498)||!Tick(W,.019f)) return false;
        TestEqual(TEXT("Each released arrival impacts exactly once"),C->PodArrival(Wave).Impacts,1);
        TestEqual(TEXT("The original six-opponent cap remains enforced"),Living(W).Num(),6);
    }
    auto LivingBefore=Living(W); if(LivingBefore.IsEmpty()) return false;
    auto* Victim=LivingBefore[0];
    SoraDamage::Strike(Victim,100000,FSoraHit::Hazard(Victim->GetActorLocation()),FVector::ZeroVector,FHitResult(),W.Hero()->GetController(),W.Hero());
    if(!Tick(W)) return false;
    TestEqual(TEXT("A cap slot admits one waiting third-pod member"),Living(W).Num(),6);
    TestEqual(TEXT("Delayed emergence cannot replay the third impact"),C->PodArrival(2).Impacts,1);
    TestEqual(TEXT("Canonical wave state records exactly one real defeat"),C->TaskProgress().Down[0]+C->TaskProgress().Down[1]+C->TaskProgress().Down[2],1);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraPodContactsTest,"SoraArena.Campaign.PodImpactContacts",
 EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraPodContactsTest::RunTest(const FString& Parameters)
{
    (void)Parameters; using namespace SoraPodTest;
    FBeatWorld W(*this,TEXT("PodContacts"),1,5);
    if(!Ready(W)) return false;
    auto* C=W.Campaign(); const FVector At=W.BeatData().Space.PodArrivals[0].Floor;
    W.Hero()->SetActorLocation(At+FVector(-150,0,100),false,nullptr,ETeleportType::TeleportPhysics);
    W.Hero()->GetCharacterMovement()->StopMovementImmediately(); W.Hero()->GetCharacterMovement()->SetComponentTickEnabled(false);
    const float HeroBefore=W.Hero()->Health;
    C->TreatmentHorse(0)->Place(At+FVector(100,100,0),0); // Contact fixture assistance; named production positions are tested above.
    auto* Inside=Target(W,At+FVector(150,0,120));
    auto* Outside=Target(W,At+FVector(351,0,120));
    auto* Above=Target(W,At+FVector(0,150,250));
    auto* Immune=Target(W,At+FVector(-100,160,120),true);
    FActorSpawnParameters Params; Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto* Ally=W.World->GetTestWorld()->SpawnActor<ASoraCompanion>(At+FVector(0,-150,100),FRotator::ZeroRotator,Params);
    if(!Inside||!Outside||!Above||!Immune||!Ally) return TestTrue(TEXT("Real contact actors spawn"),false);
    FSoraCompanionSpec Spec; Spec.Id=TEXT("pod_contact_fixture"); Spec.Role=TEXT("bystander"); Spec.Rules.Health=1000; Spec.Rules.Downable=true;
    Ally->Init(Spec,0); Freeze(*Ally);
    if(!PodTime(W,0,2498)||!Tick(W,.019f)) return false;
    TestEqual(TEXT("Ordinary Hazard reaches the hero"),HeroBefore-W.Hero()->Health,60.f);
    TestEqual(TEXT("Environmental impact reaches an actual damageable ally"),Ally->Health,940.f);
    TestEqual(TEXT("Front-facing existing enemy receives the base impact"),Inside->Health,940.f);
    TestEqual(TEXT("Outside foot center is excluded"),Outside->Health,1000.f);
    TestEqual(TEXT("Feet above the declared vertical band are excluded"),Above->Health,1000.f);
    TestEqual(TEXT("Existing invulnerability remains authoritative"),Immune->Health,1000.f);
    TestEqual(TEXT("Real horse contact changes canonical target HP once"),C->TaskProgress().TargetHp[0],340);
    TestEqual(TEXT("Untouched authored horse keeps canonical HP"),C->TaskProgress().TargetHp[1],400);
    TestEqual(TEXT("One discrete impact is retained"),C->PodArrival(0).Impacts,1);
    const float After=Inside->Health;
    if(!Until(W,W.World->GetTestWorld()->GetTimeSeconds()+.2)) return false;
    TestEqual(TEXT("Lingering in a spent footprint does not repeat damage"),Inside->Health,After);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraPodCancelTest,"SoraArena.Campaign.PodCancellationRetry",
 EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraPodCancelTest::RunTest(const FString& Parameters)
{
    (void)Parameters; using namespace SoraPodTest;
    FBeatWorld W(*this,TEXT("PodCancelRetry"),1,5);
    if(!Ready(W)||!PodTime(W,0,900)) return false;
    auto* C=W.Campaign(); TWeakObjectPtr<AActor> OldWarning=C->PodWarning(0);
    W.Hero()->Health=1;
    SoraDamage::Strike(W.Hero(),100,FSoraHit::Hazard(W.Hero()->GetActorLocation()),FVector::ZeroVector,FHitResult(),nullptr,nullptr);
    TestTrue(TEXT("Actual defeat cancels its warning immediately"),W.Mode()->bDefeated&&(!OldWarning.IsValid()||OldWarning->IsActorBeingDestroyed()));
    if(!W.Press(EKeys::Enter)) return false;
    for(int I=0;I<1500&&!W.Mode()->IsPlaying();++I) if(!Tick(W)) return false;
    W.Harden();
    TestTrue(TEXT("Enter creates a fresh full warning for the same checkpoint"),C->PodArrival(0).Active&&C->PodArrival(0).ElapsedMs<200&&C->PodWarning(0)!=OldWarning.Get());
    // A real damage callback clears the encounter. No later weak victim or
    // replacement horse may receive the old arrival, and no member may spawn.
    W.Hero()->SetActorLocation(W.BeatData().Space.PodArrivals[0].Floor+FVector(0,0,100),false,nullptr,ETeleportType::TeleportPhysics);
    W.Hero()->GetCharacterMovement()->SetComponentTickEnabled(false);
    auto* Bus=USoraGameEvents::Get(W.Hero()); bool Cancelled=false;
    const auto Handle=Bus->OnDamaged.AddLambda([&](const FSoraDamagedEvent& E)
    { if(E.Victim==W.Hero()&&!Cancelled) { Cancelled=true; C->ClearEncounter(); } });
    ON_SCOPE_EXIT { Bus->OnDamaged.Remove(Handle); };
    if(!PodTime(W,0,2498)||!Tick(W,.019f)) return false;
    TestTrue(TEXT("Actual impact callback ran teardown"),Cancelled);
    TestEqual(TEXT("Teardown discarded pending members"),Living(W).Num(),0);
    for(int I=0;I<3;++I) TestFalse(TEXT("Every old warning was removed"),IsValid(C->PodWarning(I)));
    // The owner remains alive in this fixture; explicit leave/reset cancellation
    // is observed here. EndPlay owner destruction is additionally source-bound.
    return true;
}
#endif
