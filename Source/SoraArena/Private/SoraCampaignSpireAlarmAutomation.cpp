#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraSpireAutomation.h"
#include "SoraEnemyController.h"
#include "SoraGameEvents.h"
#include "World/SoraNavigation.h"
#include "GameFramework/DamageType.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraSpireAlarmTest,"SoraArena.Campaign.SpireAuditorShutter",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraSpireAlarmTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    SoraFieldcraftAutomation::FBeatWorld W(*this,TEXT("SpireAuditorShutter"),7,9);
    if(!W.Start()||!W.Tick(2)) return false;
    W.Harden();
    const auto Space=W.Campaign()->ActiveBeatData()->Space;
    const int32 First=SoraSpireRules::ShortcutStart,Last=SoraSpireRules::ShortcutEnd;
    const FVector A=Space.Spire.Ramp[First],B=Space.Spire.Ramp[Last],Along=(B-A).GetSafeNormal2D();
    const auto SetHero=[&](const FVector& Floor)
    {
        // Fixture setup only. Every tested crossing below uses normal input.
        W.Hero()->GetCharacterMovement()->StopMovementImmediately();
        W.Hero()->SetBase(static_cast<FMovementBaseInterfaceData*>(nullptr));
        W.Hero()->SetActorLocation(Floor+FVector(0,0,90),false,nullptr,ETeleportType::TeleportPhysics);
    };
    const auto Kill=[&](ASoraEnemy& Enemy)
    {
        UGameplayStatics::ApplyDamage(&Enemy,Enemy.Health+1000.f,W.Hero()->GetController(),W.Hero(),UDamageType::StaticClass());
    };
    const auto Resume=[&](ASoraEnemy& Enemy)
    {
        Enemy.SetActorTickEnabled(true);
        Enemy.GetCharacterMovement()->SetComponentTickEnabled(true);
        if(auto* Brain=Enemy.GetController()) Brain->SetActorTickEnabled(true);
    };
    // The full companion climb has its own fixture. Keep companions from
    // fighting the two auditors while this test measures their arrival.
    for(ASoraCompanion* Ally:W.Fieldcraft()->AlliesInPlay())
    {
        Ally->SetActorTickEnabled(false); Ally->SetActorEnableCollision(false);
        Ally->GetCharacterMovement()->StopMovementImmediately();
        Ally->GetCharacterMovement()->SetComponentTickEnabled(false);
    }
    for(int32 Pass=0;Pass<20;++Pass)
    {
        ASoraEnemy* Enemy=nullptr;
        for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It&&!Enemy;++It) if(It->IsAlive()) Enemy=*It;
        if(!Enemy) break;
        Kill(*Enemy);
        if(!W.Tick(1)) return false;
    }
    TestEqual(TEXT("Setup clears only the first two authored waves"),W.Campaign()->Kills,9);
    SetHero(A);
    if(!W.Tick(2)) return false;
    SoraLiftAutomation::HoldThreats(*W.World);
    TArray<ASoraEnemy*> Auditors;
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
        if(It->IsAlive()&&It->ArchetypeId()==TEXT("auditor")) Auditors.Add(*It);
    if(!TestEqual(TEXT("The L3 wave supplies two real L4 auditors"),Auditors.Num(),2)) return false;
    auto* Arena=W.Mode()->Arena();
    ASoraEnemy* Stopped=Auditors[0];
    const FVector Start=Stopped->GetActorLocation();
    Resume(*Stopped);
    if(!W.Tick(12)) return false;
    TestTrue(TEXT("A hunting auditor actually starts descending toward the L3 panel"),
        FVector::Dist2D(Start,Stopped->GetActorLocation())>20);
    FVector Goal;
    if(!TestTrue(TEXT("The active spire provides a panel approach"),Arena->SpireAlarmGoal(*Stopped,Goal))) return false;
    TestTrue(TEXT("The intercepted auditor has not reached its panel"),FVector::Dist2D(Goal,Stopped->GetActorLocation())>100);
    Kill(*Stopped);
    TestFalse(TEXT("A dead auditor cannot operate a panel"),Arena->TrySpireAlarm(*Stopped));
    if(!W.Tick(120)) return false;
    TestFalse(TEXT("Killing the runner before arrival leaves the shortcut open"),Arena->SpireShortcutClosed()||Arena->SpireAlarmPending());

    ASoraEnemy* Runner=Auditors[1];
    const FVector RunnerStart=Runner->GetActorLocation();
    if(!TestTrue(TEXT("The second auditor has an L3 goal"),Arena->SpireAlarmGoal(*Runner,Goal))) return false;
    TestEqual(TEXT("The alarm goal follows the authored 18 m landing"),Goal.Z,1800.0);
    // Exact XY on a lower floor cannot substitute for physical arrival.
    Runner->SetActorLocation(Goal+FVector(0,0,Runner->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()-900),
        false,nullptr,ETeleportType::TeleportPhysics);
    Runner->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
    TestFalse(TEXT("A grounded lower-floor auditor cannot close the upper panel"),Arena->TrySpireAlarm(*Runner));
    Runner->SetActorLocation(RunnerStart,false,nullptr,ETeleportType::TeleportPhysics);
    if(auto* Bus=USoraGameEvents::Get(W.Mode()))
    {
        FSoraEnemyCueEvent Shout;
        Shout.Enemy=Runner; Shout.Archetype=TEXT("auditor"); Shout.Cue=ESoraEnemyCue::Alarm;
        Bus->OnEnemyCue.Broadcast(Shout);
    }
    TestFalse(TEXT("A generic alarm shout never closes this physical shutter"),Arena->SpireShortcutClosed()||Arena->SpireAlarmPending());
    auto* Nav=USoraNavigation::Get(W.Mode());
    const auto PathLength=[&](double& Length)
    {
        TArray<FVector> Path;
        if(!Nav||!Nav->Settle()||!Nav->FindPath(A+FVector(0,0,90),B+FVector(0,0,90),*W.Hero(),Path)||
            Path.Num()<2||FVector::Dist2D(Path.Last(),B)>60||FMath::Abs(Path.Last().Z-B.Z)>60) return false;
        Length=0;
        for(int32 N=1;N<Path.Num();++N) Length+=FVector::Dist(Path[N-1],Path[N]);
        return true;
    };
    double OpenLength=0;
    if(!TestTrue(TEXT("Navigation sees the complete open shortcut"),PathLength(OpenLength))) return false;
    TestTrue(TEXT("Open navigation chooses the shorter chord"),OpenLength<1900);
    if(!TestTrue(TEXT("The hero walks the shortcut uphill"),SoraLiftAutomation::Walk(*W.World,B)&&
        FMath::Abs(W.Hero()->GetActorLocation().Z-B.Z-90)<40)) return false;
    FHitResult CornerHit;
    const auto Body=FCollisionShape::MakeCapsule(W.Hero()->GetCapsuleComponent()->GetScaledCapsuleRadius(),
        W.Hero()->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
    FCollisionObjectQueryParams Solid(ECC_WorldStatic);
    // Builder boxes inherit UStaticMeshComponent's BlockAllDynamic profile.
    // Pawns are excluded, but both kinds of physical world geometry count.
    Solid.AddObjectTypesToQuery(ECC_WorldDynamic);
    const FCollisionQueryParams CornerQuery(SCENE_QUERY_STAT(SpirePadCornerFixture),false,W.Hero());
    const bool CornerBlocked=W.World->GetTestWorld()->SweepSingleByObjectType(CornerHit,B+FVector(0,0,150),B+FVector(-350,-300,150),
        FQuat::Identity,Solid,Body,CornerQuery);
    AddInfo(FString::Printf(TEXT("Shortcut corner: blocked=%d start_penetrating=%d actor=%s component=%s impact=%s"),
        CornerBlocked,CornerHit.bStartPenetrating,*GetNameSafe(CornerHit.GetActor()),*GetNameSafe(CornerHit.GetComponent()),
        *CornerHit.ImpactPoint.ToString()));
    TestTrue(TEXT("The new pad's exposed corner has a real capsule guard rail"),CornerBlocked&&CornerHit.GetComponent()&&
            CornerHit.GetComponent()->GetName().StartsWith(TEXT("SpireShortcutPadRail")));
    if(!TestTrue(TEXT("The shortcut is also walkable downhill"),SoraLiftAutomation::Walk(*W.World,A)&&
        FMath::Abs(W.Hero()->GetActorLocation().Z-A.Z-90)<40)) return false;
    const FVector Door=Arena->SpireShutterFloor();
    // Wait off the descending runner's route on the upper pad, then follow
    // after it passes the door. Standing in the narrow door beforehand
    // would physically stop the auditor, rather than test deferred closure.
    if(!SoraLiftAutomation::Walk(*W.World,B)||!SoraLiftAutomation::Walk(*W.World,B+FVector(90,80,0))) return false;
    Resume(*Runner);
    bool PassedDoor=false;
    for(int32 Frame=0;Frame<4500&&!PassedDoor&&!Arena->SpireAlarmPending()&&!Arena->SpireShortcutClosed();++Frame)
    {
        if(!W.Tick(1)) return false;
        const FVector Here=Runner->GetActorLocation();
        const float Feet=Here.Z-Runner->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
        PassedDoor=Feet<1900&&FVector::DotProduct(Here-Door,Along)<-90&&FVector::Dist2D(Here,Door)<600;
    }
    AddInfo(FString::Printf(TEXT("Auditor descent: start=%s now=%s goal=%s passed=%d alarm=%d closed=%d hero=%s"),
        *RunnerStart.ToString(),*Runner->GetActorLocation().ToString(),*Goal.ToString(),PassedDoor,
        Arena->SpireAlarmPending(),Arena->SpireShortcutClosed(),*W.Hero()->GetActorLocation().ToString()));
    if(!TestTrue(TEXT("The auditor descends from L4 to the lower side of the shortcut"),PassedDoor)) return false;
    if(!TestTrue(TEXT("The hero follows the runner into the still-open doorway"),SoraLiftAutomation::Walk(*W.World,Door))) return false;
    for(int32 Frame=0;Frame<900&&!Arena->SpireAlarmPending()&&!Arena->SpireShortcutClosed();++Frame)
        if(!W.Tick(1)) return false;
    const float RunnerFeet=Runner->GetActorLocation().Z-Runner->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    AddInfo(FString::Printf(TEXT("Auditor arrival: start=%s now=%s goal=%s feet=%.2f pending=%d closed=%d hero=%s"),
        *RunnerStart.ToString(),*Runner->GetActorLocation().ToString(),*Goal.ToString(),RunnerFeet,
        Arena->SpireAlarmPending(),Arena->SpireShortcutClosed(),*W.Hero()->GetActorLocation().ToString()));
    TestTrue(TEXT("The surviving auditor reaches its L3 panel with actual descent"),FVector::Dist2D(RunnerStart,Runner->GetActorLocation())>1000&&
        FVector::Dist2D(Runner->GetActorLocation(),Goal)<=60&&FMath::Abs(RunnerFeet-1800)<20);
    if(!TestTrue(TEXT("An occupied doorway defers the real panel alarm"),Arena->SpireAlarmPending()&&!Arena->SpireShortcutClosed())) return false;
    if(!W.Tick(120)) return false;
    TestFalse(TEXT("Waiting cannot materialize solid geometry through the hero"),Arena->SpireShortcutClosed());
    if(!TestTrue(TEXT("The hero can leave the pending shutter normally"),SoraLiftAutomation::Walk(*W.World,A))) return false;
    if(!W.Tick(2)) return false;
    TestTrue(TEXT("The shutter closes once every pawn clears its doorway"),Arena->SpireShortcutClosed()&&!Arena->SpireAlarmPending());
    const auto DoorBlocks=[&]()
    {
        FHitResult Hit;
        const FCollisionQueryParams Query(SCENE_QUERY_STAT(SpireShutterFixture),false,W.Hero());
        const auto Capsule=FCollisionShape::MakeCapsule(W.Hero()->GetCapsuleComponent()->GetScaledCapsuleRadius(),
            W.Hero()->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
        const bool HitDoor=W.World->GetTestWorld()->SweepSingleByObjectType(Hit,Door-Along*100+FVector(0,0,150),
            Door+Along*100+FVector(0,0,150),FQuat::Identity,Solid,Capsule,Query);
        return HitDoor&&Hit.GetComponent()&&Hit.GetComponent()->GetName().StartsWith(TEXT("SpireShortcutShutter"));
    };
    TestTrue(TEXT("The closed shortcut has real capsule-blocking collision"),DoorBlocks());
    double ClosedLength=0;
    if(!TestTrue(TEXT("Dynamic navigation retains a complete route around the closed shortcut"),PathLength(ClosedLength))) return false;
    TestTrue(TEXT("The alarm forces the longer route"),ClosedLength>OpenLength+200);
    AddInfo(FString::Printf(TEXT("Spire route lengths: open=%.2f closed=%.2f"),OpenLength,ClosedLength));
    if(!TestTrue(TEXT("The full original spiral is walkable after closure"),SoraSpireAutomation::Climb(*W.World,Space,First+1,Last))) return false;
    TestEqual(TEXT("The alarm never fails or advances the combat beat"),W.Campaign()->ActiveBeat(),9);
    TestFalse(TEXT("The longer route is not a defeat"),W.Mode()->bDefeated);
    UGameplayStatics::ApplyDamage(W.Hero(),W.Hero()->Health+1000.f,nullptr,nullptr,UDamageType::StaticClass());
    if(!W.Tick(2)||!TestTrue(TEXT("The ordinary death/retry path is entered"),W.Mode()->bDefeated)||
        !W.Press(EKeys::Enter)||!W.Tick(30)) return false;
    Arena=W.Mode()->Arena();
    TestEqual(TEXT("Retry retains the authored L1 checkpoint"),W.Campaign()->ActiveBeat(),9);
    TestFalse(TEXT("Retry resets both the alarm and the shutter"),Arena->SpireShortcutClosed()||Arena->SpireAlarmPending());
    TestFalse(TEXT("Retry removes the actual shutter collision"),DoorBlocks());
    return !HasAnyErrors();
}
#endif
