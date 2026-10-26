#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraRecoveryAutomation.h"
#include "SoraLiftAutomation.h"
#include "SoraLedgerRules.h"
#include "SoraEnemy.h"
#include "SoraEnemyController.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Engine/PointLight.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraLedgerPatrolsTest,"SoraArena.Campaign.LedgerPatrols",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraLedgerPatrolsTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using SoraFieldcraftAutomation::FBeatWorld;
    namespace R=SoraLedgerRules;
    if(!FSoraCatalog::Get().Load()) return false;
    FBeatWorld W(*this,TEXT("LedgerPatrols"),5,5);
    if(!W.Start()) return false;
    W.Harden();
    const auto& Space=W.BeatData().Space;
    // The observation starts behind the annex wall. All authored guards
    // retain their actual senses, collisions, clocks and movement.
    W.Stand(FVector(Space.LedgerHall.Origin+FVector2D(-700,700),0));
    ASoraEnemy* Guards[R::GuardCount]={};int Count=0;
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
    {
        const int Slot=It->EnemySlot();
        if(!TestTrue(TEXT("Each ledger guard has a distinct authored slot"),Slot>=0&&Slot<R::GuardCount&&!Guards[Slot])) return false;
        Guards[Slot]=*It;++Count;
    }
    if(!TestEqual(TEXT("The combined ledger/palace encounter contains twelve guards"),Count,R::GuardCount)) return false;
    TArray<TWeakObjectPtr<APointLight>> Lamps;
    bool HasLamp[4]={};
    for(TActorIterator<APointLight> It(W.World->GetTestWorld());It;++It)
        if(It->Tags.Contains(TEXT("LedgerCarriedLamp")))
        {
            Lamps.Add(*It);
            const auto* Guard=Cast<ASoraEnemy>(It->GetAttachParentActor());
            if(!TestTrue(TEXT("Each carried lamp belongs to one of the four aisle auditors"),
                Guard&&Guard->EnemySlot()>=0&&Guard->EnemySlot()<4&&!HasLamp[Guard->EnemySlot()])) return false;
            HasLamp[Guard->EnemySlot()]=true;
        }
    if(!TestEqual(TEXT("The ledger owns four cold carried lamps"),Lamps.Num(),4)) return false;
    FVector Starts[R::GuardCount];float Travel[R::GuardCount]={};
    for(int I=0;I<R::GuardCount;++I)
    {
        Starts[I]=Guards[I]->GetActorLocation();
        if(!TestEqual(TEXT("Each slot retains its authored guard type"),Guards[I]->ArchetypeId(),W.BeatData().Guards[I].Type)) return false;
        if(I==4||I==5)
        {
            TestEqual(TEXT("Cross-aisle rifle sweep is ninety degrees"),Guards[I]->PostScanDegrees(),90);
            TestEqual(TEXT("Cross-aisle rifle sweep is eight seconds"),Guards[I]->PostScanMs(),8000);
        }
    }
    for(int Frame=0;Frame<2700;++Frame)
    {
        if(!W.Tick(1)) return false;
        for(const auto& Lamp:Lamps)
        {
            if(!TestTrue(TEXT("The current encounter retains each carried lamp"),Lamp.IsValid())) return false;
            const auto* Guard=Cast<ASoraEnemy>(Lamp->GetAttachParentActor());
            if(!TestTrue(TEXT("The live auditor's lit lamp follows its actual movement and turning"),
                Guard&&Lamp->PointLightComponent->IsVisible()&&
                Lamp->GetActorLocation().Equals(Guard->GetActorTransform().TransformPosition(FVector(20,-30,20)),.1f))) return false;
        }
        for(int I=0;I<R::GuardCount;++I)
        {
            const auto* Guard=Guards[I];
            const auto* Brain=Cast<ASoraEnemyController>(Guard->GetController());
            const FVector At=Guard->GetActorLocation();
            if(!TestTrue(TEXT("The observation leaves every authored guard calmly patrolling"),
                Brain&&Brain->State()==SoraStealthRules::EState::Unaware)) return false;
            Travel[I]=FMath::Max(Travel[I],static_cast<float>(FVector::Dist2D(At,Starts[I])));
            if(R::HeightCm[I]>0)
            {
                if(!TestTrue(TEXT("Ledger drones stay at their actual 5.5 metre flight layer"),FMath::IsNearlyEqual(At.Z,550.f,5.f))) return false;
                // Altitude alone must not pass a body that clips the ceiling.
                // Use this archetype's real scaled capsule, not the player's
                // dimensions or a hand-picked smaller probe.
                const auto* Capsule=Guard->GetCapsuleComponent();
                FCollisionQueryParams Query(SCENE_QUERY_STAT(LedgerDroneClearance),false,Guard);
                if(!TestFalse(TEXT("The full drone body clears the authored shelves and ceiling"),
                    W.World->GetTestWorld()->OverlapBlockingTestByChannel(At,FQuat::Identity,ECC_Pawn,
                        FCollisionShape::MakeCapsule(Capsule->GetScaledCapsuleRadius(),Capsule->GetScaledCapsuleHalfHeight()),Query))) return false;
            }
            else if(Frame>30&&!TestTrue(TEXT("Ledger and palace ground guards keep real floor support"),
                Guard->GetCharacterMovement()->IsMovingOnGround())) return false;
            if(R::IsPost(I)&&!TestTrue(TEXT("Posted guards turn without walking away"),Travel[I]<8.f)) return false;
        }
    }
    for(int I:{0,1,2,3,9,10})
        TestTrue(TEXT("Every pacing auditor/rifle physically travels its assigned corridor"),Travel[I]>500.f);
    for(int I:{6,7,10})
    {
        const auto* Brain=Cast<ASoraEnemyController>(Guards[I]->GetController());
        const auto& Timing=Brain->PatrolTiming();
        TestTrue(TEXT("Scheduled loop completes at the authored period without skipped arrivals"),
            Timing.Cycles>=1&&!Timing.Overdue&&FMath::Abs(Timing.LastCycleMs-R::PeriodMs[I])<=50);
        AddInfo(FString::Printf(TEXT("Ledger guard %d circuit: cycles=%d actual=%lld expected=%d overdue=%d travel=%.1f"),
            I,Timing.Cycles,Timing.LastCycleMs,R::PeriodMs[I],Timing.Overdue,Travel[I]));
    }
    if(!W.Press(EKeys::Escape)) return false;
    for(int I=0;I<R::GuardCount;++I) Starts[I]=Guards[I]->GetActorLocation();
    if(!W.Tick(300)) return false;
    for(int I=0;I<R::GuardCount;++I)
        TestTrue(TEXT("Menu pause holds all ledger and palace guards"),Guards[I]->GetActorLocation().Equals(Starts[I],1.f));
    if(!W.Press(EKeys::Escape)) return false;
    FBeatWorld::Hurt(*Guards[0],Guards[0]->Health+1000.f);
    if(!W.Tick(2)) return false;
    TestFalse(TEXT("A defeated auditor extinguishes its carried lamp"),W.Fieldcraft()->LedgerLampLit(0));
    FBeatWorld::Hurt(*W.Hero(),W.Hero()->Health+1000.f);
    if(!W.Tick(2)||!W.Press(EKeys::Enter)||!W.Tick(2)) return false;
    TestEqual(TEXT("Retry restores the combined ledger encounter"),W.Campaign()->ActiveBeat(),5);
    for(const auto& Lamp:Lamps) TestFalse(TEXT("Retry destroys the previous encounter's carried lamps"),Lamp.IsValid());
    for(int I=0;I<4;++I) TestTrue(TEXT("Retry creates a lit lamp for every restored aisle auditor"),W.Fieldcraft()->LedgerLampLit(I));
    AddInfo(TEXT("Actual-guard patrol/post/flight/lamp fixture, observed from the annex. Ordinary stealth difficulty, handheld lamp craft/animation, alarm shutter and final art remain separate acceptance work."));
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraLedgerRouteTest,"SoraArena.Campaign.LedgerRoute",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraLedgerRouteTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using SoraFieldcraftAutomation::FBeatWorld;
    if(!FSoraCatalog::Get().Load()) return false;
    FBeatWorld W(*this,TEXT("LedgerRoute"),5,5);
    if(!W.Start()) return false;
    W.Harden();
    // This fixture isolates real navigation/collision. The separate patrol
    // fixture leaves all twelve guards live; this one holds their AI while
    // retaining their bodies as obstacles. The hero always uses mapped W.
    SoraLiftAutomation::HoldThreats(*W.World);
    const FVector O(W.BeatData().Space.LedgerHall.Origin,0),P(W.BeatData().Space.LedgerHall.PalaceOrigin,0);
    int Shelves=0;
    for(TObjectIterator<UStaticMeshComponent> It;It;++It)
        if(It->GetWorld()==W.World->GetTestWorld()&&It->ComponentHasTag(TEXT("LedgerShelfBank"))) ++Shelves;
    TestEqual(TEXT("Six written-off niches split the actual shelf collision into thirty pieces"),Shelves,30);
    const auto Walk=[&](const FVector& Target)
    {
        const bool Arrived=FVector::Dist2D(W.Hero()->GetActorLocation(),Target)<=30.f||SoraRecoveryAutomation::WalkTo(*W.World,Target);
        if(!Arrived) AddError(FString::Printf(TEXT("Ledger route blocked: from=%s target=%s input=%d"),
            *W.Hero()->GetActorLocation().ToString(),*Target.ToString(),int32(W.Mode()->InputState())));
        return Arrived&&TestTrue(TEXT("Mapped corridor movement keeps the player on the floor"),
            W.Hero()->GetCharacterMovement()->IsMovingOnGround());
    };
    // Visit the annex through its doorway, then all four cross-aisles and
    // the north turn. No pawn teleport is used after checkpoint creation.
    for(const FVector At:{FVector(280,320,0),FVector(-150,320,0),FVector(-700,400,0),
        FVector(-150,320,0),FVector(280,320,0),FVector(280,1200,0),FVector(1160,1200,0),
        FVector(720,1200,0),FVector(720,2800,0),FVector(1600,2800,0),FVector(1600,4400,0),
        FVector(2040,4400,0),FVector(2040,6000,0),FVector(2100,6300,0),FVector(2100,6535,0)})
        if(!Walk(O+At)) return false;
    for(const FVector At:{FVector(-300,-135,0),FVector(250,-135,0),FVector(250,-670,0),
        FVector(2150,-670,0),FVector(2150,-135,0),FVector(2430,-135,0),FVector(2430,1900,0),FVector(2430,2250,0)})
        if(!Walk(P+At)) return false;
    TestTrue(TEXT("Crossing the hall alone does not complete the palace exit"),W.Campaign()->ActiveBeat()==5);
    // Stop when entry into the real vestibule exit advances the checkpoint;
    // do not chase a stale destination after the ordinary beat transition.
    for(int Frame=0;Frame<600&&W.Campaign()->ActiveBeat()==5;++Frame)
    {
        const FRotator Facing=(P+FVector(2540,2500,0)-W.Hero()->GetActorLocation()).GetSafeNormal2D().Rotation();
        W.Hero()->GetController()->SetControlRotation(Facing);W.Hero()->FaceRotation(Facing,0);
        if(!W.World->InjectKey(EKeys::W,IE_Pressed)||!W.Tick(1)) return false;
    }
    if(!W.World->InjectKey(EKeys::W,IE_Released)||!W.Tick(2)) return false;
    TestTrue(TEXT("Only the actual palace vestibule completes b06"),W.Campaign()->ActiveBeat()!=5&&
        (W.Campaign()->Progress().CompletedMask&SoraBeatRules::BeatBit(5))!=0u);
    AddInfo(TEXT("Mapped-input traversal with guards held. This proves the physical annex/hall/link/palace/quiet-room route only; it does not qualify ordinary stealth difficulty, sliding fusuma, silent edge access or final art."));
    return true;
}
#endif
