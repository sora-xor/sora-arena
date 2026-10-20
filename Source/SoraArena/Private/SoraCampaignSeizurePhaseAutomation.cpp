#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraBoss.h"
#include "SoraGameEvents.h"
#include "SoraWorldBuilder.h"
#include "Combat/SoraBossCatalog.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/DamageType.h"

namespace SoraSeizurePhaseAutomation
{
struct FLog
{
    TWeakObjectPtr<USoraGameEvents> Bus;
    FDelegateHandle Handle;
    int32 MainWindups=0,MainStrikes=0,ShieldedWindups=0,ShieldedStrikes=0,ShieldedFields=0,CaneWindups=0,CaneSummons=0;
    TSet<int32> MainStrikeSerials;
    ~FLog() { Detach(); }
    void Detach() { if(Bus.IsValid()) Bus->OnBossPhase.Remove(Handle); Bus.Reset(); Handle.Reset(); }
    bool Attach(UWorld* World,ASoraBoss* Boss)
    {
        Detach(); Bus=USoraGameEvents::Get(World);
        if(!Bus.IsValid()) return false;
        Handle=Bus->OnBossPhase.AddLambda([this,Boss](const FSoraBossPhaseEvent& E)
        {
            if(E.Boss!=Boss) return;
            const bool Main=E.Detail==TEXT("amort_ledger_beam")||E.Detail==TEXT("amort_cleave");
            const bool Shielded=Boss->PhaseIndex()==1&&Boss->LiveAdds()>0;
            if(E.Phase==ESoraBossPhase::Windup)
            {
                MainWindups+=Main; ShieldedWindups+=Main&&Shielded;
                ShieldedFields+=E.Detail==TEXT("amort_seizure_field")&&Shielded;
                CaneWindups+=E.PhaseIndex==2&&E.Detail.ToString().StartsWith(TEXT("amort_"))&&!Main;
            }
            if(E.Phase==ESoraBossPhase::Strike&&Main)
            {
                ++MainStrikes; ShieldedStrikes+=Shielded; MainStrikeSerials.Add(E.Serial);
            }
            CaneSummons+=E.PhaseIndex==2&&E.Phase==ESoraBossPhase::Event&&E.Detail==TEXT("constructs");
        });
        return true;
    }
};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraCampaignSeizurePhaseTest,"SoraArena.Campaign.SeizurePhaseOwnership",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraCampaignSeizurePhaseTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    SoraFieldcraftAutomation::FBeatWorld W(*this,TEXT("SeizurePhaseOwnership"),7,13);
    if(!W.Start(0,INDEX_NONE,1)) return false;
    W.Harden();
    ASoraBoss* Boss=const_cast<ASoraBoss*>(W.Campaign()->CampaignBoss());
    if(!TestNotNull(TEXT("The actual summit checkpoint restores P2"),Boss)) return false;
    SoraSeizurePhaseAutomation::FLog Log;
    if(!TestTrue(TEXT("Boss phase events are observable"),Log.Attach(W.World->GetTestWorld(),Boss))) return false;
    // The north dais steps are solid throughout every tile pattern. The hero
    // is in normal beam/cleave range; boss AI and all boss clocks remain live.
    W.Hero()->SetBase(static_cast<FMovementBaseInterfaceData*>(nullptr));
    W.Hero()->GetCharacterMovement()->StopMovementImmediately();
    W.Hero()->SetActorLocation(FVector(W.BeatData().Space.Summit.Center,16000)+FVector(0,500,160),
        false,nullptr,ETeleportType::TeleportPhysics);
    W.LookAt(Boss->GetActorLocation());
    bool ShieldQuiescent=true;
    const auto Now=[&]() { return W.World->GetTestWorld()->GetTimeSeconds(); };
    const auto Tick=[&](int32 Frames)
    {
        for(int32 Frame=0;Frame<Frames;++Frame)
        {
            // Isolate phase scheduling from add/companion combat. Their real
            // live/dead accounting, collision and release callbacks remain.
            for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
                if(*It!=Boss)
                {
                    It->SetActorTickEnabled(false);
                    It->GetCharacterMovement()->StopMovementImmediately();
                    It->GetCharacterMovement()->DisableMovement();
                    if(auto* Brain=It->GetController()) Brain->SetActorTickEnabled(false);
                }
            for(TActorIterator<ASoraCompanion> It(W.World->GetTestWorld());It;++It)
            {
                It->SetActorTickEnabled(false);
                It->GetCharacterMovement()->StopMovementImmediately();
                It->GetCharacterMovement()->DisableMovement();
                if(auto* Brain=It->GetController()) Brain->SetActorTickEnabled(false);
            }
            if(!W.Tick(1)) return false;
            if(Boss->PhaseIndex()==1&&Boss->LiveAdds()>0)
                ShieldQuiescent&=Boss->BossAttackIndex()==INDEX_NONE;
        }
        return true;
    };
    const auto Until=[&](double Time)
    {
        for(int32 Frame=0;Now()<Time&&Frame<2400;++Frame) if(!Tick(1)) return false;
        return TestTrue(TEXT("The live game clock reaches the requested boundary"),Now()>=Time);
    };
    const auto Clear=[&]()
    {
        for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
            if(It->Summoner()==Boss&&It->IsAlive())
                UGameplayStatics::ApplyDamage(*It,It->Health,W.Hero()->GetController(),W.Hero(),UDamageType::StaticClass());
    };
    for(int32 Frame=0;Frame<180&&Boss->LiveAdds()<2;++Frame) if(!Tick(1)) return false;
    if(!TestEqual(TEXT("The first authored pair arrives"),Boss->LiveAdds(),2)) return false;
    if(!Until(Now()+5)) return false;
    TestTrue(TEXT("P2 remains at its physical dais behind the construct shield"),Boss->IsOnSummitDais()&&Boss->IsInvulnerable());
    TestTrue(TEXT("Seizure hazards still start while the main pattern is shielded"),Log.ShieldedFields>0);
    TestTrue(TEXT("The shield blocks main windups and strikes without freezing the boss clock"),
        ShieldQuiescent&&Log.ShieldedWindups==0&&Log.ShieldedStrikes==0);

    const double ExposedAt=Now();
    const int32 WindupsBefore=Log.MainWindups,StrikesBefore=Log.MainStrikes;
    Clear();
    if(!TestTrue(TEXT("Clearing the actual pair immediately exposes the collector"),Boss->LiveAdds()==0&&!Boss->IsInvulnerable())) return false;
    for(int32 Frame=0;Frame<300&&Log.MainStrikes==StrikesBefore;++Frame) if(!Tick(1)) return false;
    if(!TestTrue(TEXT("Normal AI resumes its ledger/cleave pattern during exposure"),
        Log.MainWindups>WindupsBefore&&Log.MainStrikes>StrikesBefore)) return false;
    Boss->Hold(120000);
    if(!Until(ExposedAt+8.9)) return false;
    if(!TestEqual(TEXT("The exposure lasts until the complete ten-second respawn delay"),Boss->LiveAdds(),0)) return false;
    // Commit a real late beam whose 1450 ms windup would cross the shield's
    // return. Only this boundary placement uses the existing forced cue hook.
    if(!TestTrue(TEXT("A late exposed beam can commit"),Boss->ForceAttack(TEXT("amort_ledger_beam")))) return false;
    for(int32 Frame=0;Frame<30&&Boss->BossAttackIndex()==INDEX_NONE;++Frame) if(!Tick(1)) return false;
    if(!TestTrue(TEXT("The late beam is still warning before constructs return"),
        Boss->IsBossTelegraphing()&&Boss->BossAttack()&&Boss->BossAttack()->Id==TEXT("amort_ledger_beam")&&Now()<ExposedAt+9.5)) return false;
    const int32 LateSerial=Boss->AttackSerial();
    for(int32 Frame=0;Frame<180&&Boss->LiveAdds()==0;++Frame) if(!Tick(1)) return false;
    if(!TestTrue(TEXT("The same P2 pair respawns after ten seconds"),
        Boss->LiveAdds()==2&&FMath::Abs(Now()-ExposedAt-10.0)<.05&&Boss->IsInvulnerable())) return false;
    if(!Until(Now()+2)) return false;
    TestTrue(TEXT("The returning shield cancels the old windup without a delayed strike"),
        ShieldQuiescent&&Boss->BossAttackIndex()==INDEX_NONE&&!Log.MainStrikeSerials.Contains(LateSerial)&&
        Log.ShieldedWindups==0&&Log.ShieldedStrikes==0);

    // Clear the respawned pair and cross the real health threshold before its
    // newly scheduled respawn is due. Keep this same boss/world into P3.
    const double LastClearAt=Now();
    Clear();
    UGameplayStatics::ApplyDamage(Boss,Boss->Health-Boss->MaxHealth*.39f,W.Hero()->GetController(),W.Hero(),UDamageType::StaticClass());
    Boss->Hold(0);
    if(!Tick(1)||!TestEqual(TEXT("The cleared P2 advances to the cane phase"),Boss->PhaseIndex(),2)) return false;
    if(!Until(LastClearAt+12)) return false;
    TestTrue(TEXT("An old seizure deadline never summons constructs into the cane duel"),
        Boss->LiveAdds()==0&&Log.CaneSummons==0);
    TestTrue(TEXT("The cane pattern remains active after the completed transition"),!Boss->IsPhaseTransitioning()&&Log.CaneWindups>0);
    TestEqual(TEXT("P3 leaves the physical seizure field off"),W.Mode()->Arena()->SeizurePattern(),-1);
    auto* Save=Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(W.Slot,0));
    if(!TestTrue(TEXT("The completed transition saves the real P3 checkpoint"),Save&&Save->CheckpointPhase==2)) return false;

    // Reload that actual saved slot without seeding another fixture state.
    Log.Detach();
    W.Fieldcraft()->OnEvent.Remove(W.EventsHandle);
    if(!W.World->DestroyTestWorld(true)) return false;
    W.World->ForwardErrorMessages(this); W.World.Reset(); W.EventsHandle.Reset();
    W.World=MakeUnique<FSoraAutomationWorld>();
    if(!W.World->Start(W.Slot)||!W.Tick(1)||!W.World->EnableKeyInput()||
        !W.Press(EKeys::Enter)||!W.Press(EKeys::Enter)||!W.Press(EKeys::Enter)) return false;
    Boss=const_cast<ASoraBoss*>(W.Campaign()->CampaignBoss()); W.Harden();
    if(!TestTrue(TEXT("The saved cane phase reloads"),Boss&&Boss->PhaseIndex()==2)) return false;
    if(!Until(Now()+11)) return false;
    TestTrue(TEXT("P3 reload restores no seizure respawn or live construct"),
        Boss->LiveAdds()==0&&!Boss->IsInvulnerable()&&W.Mode()->Arena()->SeizurePattern()==-1);
    return !HasAnyErrors();
}
#endif
