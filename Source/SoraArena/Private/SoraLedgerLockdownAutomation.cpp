#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraLiftAutomation.h"
#include "SoraRecoveryAutomation.h"
#include "SoraEnemy.h"
#include "Components/StaticMeshComponent.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraLedgerLockdownTest,"SoraArena.Campaign.LedgerLockdown",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraLedgerLockdownTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using SoraFieldcraftAutomation::FBeatWorld;
    namespace R=SoraLedgerRules;
    if(!FSoraCatalog::Get().Load()) return false;
    FBeatWorld W(*this,TEXT("LedgerLockdown"),5,5);
    if(!W.Start()) return false;
    W.Harden();SoraLiftAutomation::HoldThreats(*W.World);
    const FVector O(W.BeatData().Space.LedgerHall.Origin,0);
    const auto Reinforcements=[&]()
    {
        TArray<ASoraEnemy*> Result;
        for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
            if(It->Tags.Contains(TEXT("LedgerReinforcement"))) Result.Add(*It);
        return Result;
    };
    UStaticMeshComponent* Shutter=nullptr;UStaticMeshComponent* SouthDoor=nullptr;
    ASoraEnemy* Auditor=nullptr;
    for(TObjectIterator<UStaticMeshComponent> It;It;++It)
        if(It->GetWorld()==W.World->GetTestWorld())
        {
            if(It->ComponentHasTag(TEXT("LedgerC3Shutter"))) Shutter=*It;
            if(It->ComponentHasTag(TEXT("LedgerSouthDoor"))) SouthDoor=*It;
        }
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
        if(It->EnemySlot()==0) Auditor=*It;
    if(!Shutter||!SouthDoor||!Auditor) { AddError(TEXT("Missing actual ledger shutter, south door or auditor"));return false; }
    const auto State=[&]() -> const R::FLockdown& { return W.Fieldcraft()->LedgerLockdownState(); };
    const auto SightBlocked=[&]()
    {
        FHitResult Hit;FCollisionQueryParams Query(SCENE_QUERY_STAT(LedgerShutterSight),false,W.Hero());
        return W.World->GetTestWorld()->LineTraceSingleByChannel(Hit,O+FVector(1160,4200,110),
            O+FVector(1160,4600,110),ECC_Visibility,Query)&&Hit.GetComponent()==Shutter;
    };
    W.Stand(O+FVector(1160,4400,0));
    W.Campaign()->RaiseBeatEvent(TEXT("alert_state:alert"));
    if(!W.Tick(120)) return false;
    if(!TestEqual(TEXT("Detection alone releases no alarm reinforcements"),Reinforcements().Num(),0)||
        !TestTrue(TEXT("Detection alone leaves C3 open"),State().Phase==R::ELockdown::Dormant&&!SightBlocked())) return false;
    // Use the actual stealth alarm delegate. Original patrol AI is held to
    // isolate the response; the four arriving riflemen retain their live AI.
    W.Stealth()->RaiseAlarm(*Auditor,W.Hero()->GetActorLocation());
    auto Arrivals=Reinforcements();
    if(!TestEqual(TEXT("The alarm releases exactly four actual riflemen"),Arrivals.Num(),4)) return false;
    bool Claimed[4]={};bool Entered[4]={};
    for(int I=0;I<4;++I)
    {
        const auto* Enemy=Arrivals[I];
        TestEqual(TEXT("Every reinforcement is the authored rifle archetype"),Enemy->ArchetypeId(),FName(TEXT("enforcer_rifle")));
        int Match=INDEX_NONE;
        for(int J=0;J<4;++J)
            if(FVector::Dist2D(Enemy->GetActorLocation(),O+FVector(R::Reinforcement[J].X,R::Reinforcement[J].Y,0))<.1f) Match=J;
        if(!TestTrue(TEXT("Each rifleman starts at a distinct supported entrance position"),Match!=INDEX_NONE&&!Claimed[Match])) return false;
        Claimed[Match]=true;
        TestTrue(TEXT("The spawned body retains its authored north or south entrance identity"),
            Enemy->Tags.Contains(Match<2?TEXT("sp_aisle_north_door"):TEXT("sp_aisle_south_door")));
    }
    for(int Frame=0;Frame<900;++Frame)
    {
        if(!W.Tick(1)) return false;
        bool All=true;
        for(int I=0;I<4;++I)
        {
            const auto* Enemy=Arrivals[I];const float Y=Enemy->GetActorLocation().Y-O.Y;
            Entered[I]|=Enemy->GetCharacterMovement()->IsMovingOnGround()&&
                (Enemy->Tags.Contains(TEXT("sp_aisle_north_door"))?Y<6350:Y>50);
            All&=Entered[I];
        }
        if(All) break;
    }
    for(int I=0;I<4;++I)
        if(!TestTrue(TEXT("Each live rifleman physically walks through its real entrance"),Entered[I]))
        { AddInfo(Arrivals[I]->GetActorLocation().ToString());return false; }
    SoraLiftAutomation::HoldThreats(*W.World);
    W.Stand(O+FVector(1160,4400,0));
    const FVector Obstruction=W.Hero()->GetActorLocation();
    if(!W.Tick(2100)) return false;
    TestTrue(TEXT("A pawn under C3 stops the descending shutter without starting its closed timer"),
        W.Fieldcraft()->LedgerShutterBlocked()&&State().Phase==R::ELockdown::Closing&&State().HeldMs==0);
    TestTrue(TEXT("The shutter never shoves the obstructing player"),W.Hero()->GetActorLocation().Equals(Obstruction,1.f));
    W.Stand(O+FVector(1160,4200,0),90);
    for(int I=0;I<120&&State().Phase==R::ELockdown::Closing;++I) if(!W.Tick(1)) return false;
    if(!TestTrue(TEXT("Clearing the path closes the actual six-metre shutter"),
        State().Phase==R::ELockdown::Holding&&SightBlocked()&&
        FMath::IsNearlyEqual(Shutter->Bounds.BoxExtent.Z*2,600.f,.1f))) return false;
    if(!W.Hold(EKeys::W,60)) return false;
    TestTrue(TEXT("Mapped walking cannot cross the closed shutter"),W.Hero()->GetActorLocation().Y<O.Y+4360);
    const int HeldBeforePause=State().HeldMs;
    if(!W.Press(EKeys::Escape)) return false;
    const int Paused=State().HeldMs;
    if(!W.Tick(2100)) return false;
    TestEqual(TEXT("Menu pause does not spend the shutter's thirty seconds"),State().HeldMs,Paused);
    TestTrue(TEXT("Pause was entered while the shutter still held closed"),Paused>=HeldBeforePause&&SightBlocked());
    if(!W.Press(EKeys::Escape)) return false;
    W.Campaign()->RaiseBeatEvent(TEXT("ai_event:alarm_raised"));
    TestEqual(TEXT("A repeated alarm cannot duplicate the four reinforcements"),Reinforcements().Num(),4);
    for(int I=0;I<2000&&State().Phase==R::ELockdown::Holding;++I)
    {
        if(!TestTrue(TEXT("The leaf remains physically closed throughout its hold"),SightBlocked())||!W.Tick(1)) return false;
    }
    if(!TestTrue(TEXT("Opening starts only after thirty active seconds fully closed"),
        State().Phase==R::ELockdown::Opening&&State().HeldMs==30000)||!W.Tick(120)) return false;
    TestTrue(TEXT("The entire shutter retracts and restores the original C3 sightline"),
        State().Phase==R::ELockdown::Finished&&!SightBlocked());
    if(!SoraRecoveryAutomation::WalkTo(*W.World,O+FVector(1160,4600,0))) return false;
    TestEqual(TEXT("The shutter closes once"),W.Count(TEXT("ledger_shutter:closed")),1);
    TestEqual(TEXT("The shutter reopens once"),W.Count(TEXT("ledger_shutter:opened")),1);
    const TWeakObjectPtr<UStaticMeshComponent> OldShutter=Shutter,OldDoor=SouthDoor;
    FBeatWorld::Hurt(*W.Hero(),W.Hero()->Health+1000.f);
    if(!W.Tick(2)||!W.Press(EKeys::Enter)||!W.Tick(2)) return false;
    TestFalse(TEXT("Retry destroys the old shutter"),OldShutter.IsValid());
    TestFalse(TEXT("Retry destroys the old service door"),OldDoor.IsValid());
    TestTrue(TEXT("Retry restores an inactive alarm and open C3"),State().Phase==R::ELockdown::Dormant);
    TestEqual(TEXT("Retry clears the prior alarm wave"),Reinforcements().Num(),0);
    AddInfo(TEXT("Alarm response fixture: initial patrol AI held; four reinforcements initially live through entry, then held for shutter collision/clock/pause/retry isolation. Final shutter craft, motor/alarm audio and ordinary stealth difficulty are not qualified by this test."));
    return true;
}
#endif
