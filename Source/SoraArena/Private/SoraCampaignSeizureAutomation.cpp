#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraBoss.h"
#include "SoraWorldBuilder.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/DamageType.h"

// The pure host checks establish polygon coverage and exact state boundaries.
// This fixture tests the resulting collision, gravity and existing boss timers.
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraCampaignSeizureTest,"SoraArena.Campaign.SeizureTiles",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraCampaignSeizureTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    SoraFieldcraftAutomation::FBeatWorld W(*this,TEXT("SeizureTiles"),7,13);
    if(!W.Start(0,INDEX_NONE,1)) return false;
    W.Harden();
    auto* Boss=const_cast<ASoraBoss*>(W.Campaign()->CampaignBoss());
    auto* Arena=W.Mode()->Arena();
    if(!TestNotNull(TEXT("The seizure checkpoint restores its boss"),Boss)||!TestNotNull(TEXT("The summit exists"),Arena)) return false;
    TestEqual(TEXT("The checkpoint restores P2"),Boss->PhaseIndex(),1);
    const FVector Center(W.BeatData().Space.Summit.Center,16000);
    const float Half=W.Hero()->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    const auto Stand=[&](FVector At)
    {
        W.Hero()->SetBase(static_cast<FMovementBaseInterfaceData*>(nullptr));
        W.Hero()->GetCharacterMovement()->StopMovementImmediately();
        W.Hero()->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
        W.Hero()->SetActorLocation(At,false,nullptr,ETeleportType::TeleportPhysics);
    };
    const auto Refuge=[&]() { Stand(Center+FVector(0,-320,120+Half+4)); };
    // Suppress ordinary combat decisions, retaining TickPlay's real concurrent
    // timer and phase changes. Constructs remain alive so the shield is real.
    const auto Tick=[&](int32 Frames)
    {
        for(int32 N=0;N<Frames;++N)
        {
            for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
            {
                if(auto* Controller=It->GetController()) Controller->SetActorTickEnabled(false);
                It->GetCharacterMovement()->StopMovementImmediately();
                if(*It!=Boss) { It->SetActorTickEnabled(false); It->GetCharacterMovement()->DisableMovement(); }
            }
            if(!W.Tick(1)) return false;
        }
        return true;
    };
    const auto Now=[&]() { return W.World->GetTestWorld()->GetTimeSeconds(); };
    const auto FloorAt=[&](int32 X,int32 Y)
    {
        const FVector At=Center+FVector((X+.5f)*300,(Y+.5f)*300,0);
        FHitResult Hit; FCollisionObjectQueryParams Solid; Solid.AddObjectTypesToQuery(ECC_WorldStatic);
        return W.World->GetTestWorld()->LineTraceSingleByObjectType(Hit,At+FVector(0,0,20),At-FVector(0,0,60),Solid)&&
            FMath::Abs(Hit.ImpactPoint.Z-Center.Z)<2;
    };
    const auto Until=[&](double Time)
    {
        for(int32 Limit=0;Now()<Time&&Limit<1200;++Limit) if(!Tick(1)) return false;
        return TestTrue(TEXT("The world reaches the timing sample"),Now()>=Time);
    };
    Refuge();
    TestEqual(TEXT("Reload has no persisted partial tile cycle"),Arena->SeizurePattern(),-1);
    for(int32 Frame=0;Frame<360&&Arena->SeizurePattern()<0;++Frame) if(!Tick(1)) return false;
    if(!TestEqual(TEXT("The real concurrent attack begins with checker thirds"),Arena->SeizurePattern(),0)) return false;
    const double FirstMark=Now();
    TestTrue(TEXT("Marked tile collision remains solid"),FloorAt(3,0));
    Stand(Center+FVector(1050,150,Half+4));
    if(!Until(FirstMark+1.40)) return false;
    TestTrue(TEXT("Warning remains traversable until its full 1.5 seconds"),FloorAt(3,0));
    if(!Until(FirstMark+1.60)) return false;
    TestFalse(TEXT("The marked tile becomes a real hole"),FloorAt(3,0));
    TestTrue(TEXT("An unselected neighboring tile remains solid"),FloorAt(3,1));
    const float Before=W.Hero()->Health;
    FVector ExpectedRecovery; bool bRecoveryFound=false;
    for(int32 Frame=0;Frame<120&&W.Hero()->Health==Before;++Frame)
    {
        bRecoveryFound=Arena->SummitSafePoint(W.Hero()->GetActorLocation(),*W.Hero(),ExpectedRecovery);
        if(!Tick(1)) return false;
    }
    TestEqual(TEXT("Gravity through the hole deals 25 damage once"),Before-W.Hero()->Health,25.f);
    TestTrue(TEXT("The hero recovers at the nearest clear intact edge tile"),bRecoveryFound&&
        FVector::Dist2D(W.Hero()->GetActorLocation(),ExpectedRecovery)<5&&W.Hero()->GetActorLocation().Z>16000);
    const float RecoveredHealth=W.Hero()->Health;
    SoraFieldcraftAutomation::FBeatWorld::Hurt(*W.Hero(),10);
    TestEqual(TEXT("Recovery grants one second of damage immunity"),W.Hero()->Health,RecoveredHealth);
    if(!Tick(63)) return false;
    SoraFieldcraftAutomation::FBeatWorld::Hurt(*W.Hero(),10);
    TestEqual(TEXT("Damage works again after immunity expires"),RecoveredHealth-W.Hero()->Health,10.f);
    Refuge();
    if(!Until(FirstMark+6.40)) return false;
    TestFalse(TEXT("The hole lasts the full five seconds after warning"),FloorAt(3,0));
    if(!Until(FirstMark+6.60)) return false;
    TestFalse(TEXT("A rising tile stays noncolliding during restoration"),FloorAt(3,0));
    if(!Until(FirstMark+7.60)) return false;
    TestTrue(TEXT("The tile becomes solid after its one second restore"),FloorAt(3,0));
    TestEqual(TEXT("Physical fields do not also spawn generic damaging zones"),Boss->LiveZones(),0);
    double PreviousMark=FirstMark;
    for(int32 Pattern=1;Pattern<=2;++Pattern)
    {
        for(int32 Frame=0;Frame<600&&Arena->SeizurePattern()!=Pattern;++Frame) if(!Tick(1)) return false;
        if(!TestEqual(TEXT("The fixed pattern order advances"),Arena->SeizurePattern(),Pattern)) return false;
        const double Mark=Now();
        TestTrue(TEXT("The existing boss scheduler retains nine second cadence"),FMath::Abs(Mark-PreviousMark-9.0)<.05);
        PreviousMark=Mark;
        // Tally lines locked at (0,-2) on the dais: (3,1) is its diagonal;
        // moving away during the warning cannot drag those lines with us.
        if(Pattern==2) Stand(Center+FVector(1050,-750,Half+4));
        if(!Until(Mark+1.60)) return false;
        if(Pattern==1)
        {
            TestFalse(TEXT("The 8-12 metre ring band falls"),FloorAt(3,0));
            TestTrue(TEXT("The outside of the ring remains"),FloorAt(4,1));
        }
        else
        {
            TestFalse(TEXT("The third tally diagonal uses the marked player cell"),FloorAt(3,1));
            TestTrue(TEXT("Moving the player does not retarget the tally field"),FloorAt(3,-3));
        }
        Refuge();
        if(Pattern==1&&!Until(Mark+7.60)) return false;
    }
    ASoraEnemy* FallingConstruct=nullptr;
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
        if(It->Summoner()==Boss&&It->IsAlive()) { FallingConstruct=*It; break; }
    if(!TestNotNull(TEXT("P2 has a live collateral construct"),FallingConstruct)) return false;
    const float ConstructHealth=FallingConstruct->Health;
    FallingConstruct->SetActorLocation(Center+FVector(1050,450,-200),false,nullptr,ETeleportType::TeleportPhysics);
    if(!Tick(1)) return false;
    TestTrue(TEXT("A fallen construct cannot strand the shield on a lower floor"),FallingConstruct->GetActorLocation().Z>16000);
    TestEqual(TEXT("Construct recovery preserves its health"),FallingConstruct->Health,ConstructHealth);
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
        if(It->Summoner()==Boss&&It->IsAlive())
            UGameplayStatics::ApplyDamage(*It,It->Health,W.Hero()->GetController(),W.Hero(),UDamageType::StaticClass());
    if(!Tick(2)) return false;
    TestFalse(TEXT("Clearing the real constructs exposes the boss"),Boss->IsInvulnerable());
    UGameplayStatics::ApplyDamage(Boss,Boss->Health-Boss->MaxHealth*.39f,W.Hero()->GetController(),W.Hero(),UDamageType::StaticClass());
    if(!Tick(2)) return false;
    TestEqual(TEXT("Damage enters the real cane phase"),Boss->PhaseIndex(),2);
    TestEqual(TEXT("P3 immediately shuts off the physical field"),Arena->SeizurePattern(),-1);
    TestTrue(TEXT("Phase change restores missing collision immediately"),FloorAt(3,1)&&FloorAt(3,0));
    auto* Save=Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(W.Slot,0));
    TestTrue(TEXT("Tile state never replaces the boss phase checkpoint"),Save&&Save->CheckpointBeat==13&&Save->CheckpointPhase==2);
    return !HasAnyErrors();
}
#endif
