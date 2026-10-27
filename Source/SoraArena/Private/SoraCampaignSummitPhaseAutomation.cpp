#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraBoss.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/DamageType.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraSummitPhasesTest,"SoraArena.Campaign.SummitPhases",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraSummitPhasesTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    SoraFieldcraftAutomation::FBeatWorld W(*this,TEXT("SummitPhases"),7,13);
    if(!W.Start()) return false;
    W.Harden();
    auto* Boss=const_cast<ASoraBoss*>(W.Campaign()->CampaignBoss());
    if(!TestNotNull(TEXT("The collector begins in P1"),Boss)) return false;
    Boss->Hold(120000);
    const FVector Center(W.BeatData().Space.Summit.Center,16000);
    const auto Tick=[&](int32 Frames)
    {
        for(int32 N=0;N<Frames;++N)
        {
            for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
                if(*It!=Boss)
                {
                    It->SetActorTickEnabled(false);
                    It->GetCharacterMovement()->StopMovementImmediately();
                    It->GetCharacterMovement()->DisableMovement();
                    if(auto* Controller=It->GetController()) Controller->SetActorTickEnabled(false);
                }
            if(!W.Tick(1)) return false;
        }
        return true;
    };
    if(!Tick(30)) return false;
    const auto SavedPhase=[&]()
    {
        const auto* Save=Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(W.Slot,0));
        return Save?Save->CheckpointPhase:INDEX_NONE;
    };
    // A real wall blocks the short north approach. It deliberately does not
    // enter navigation, so a stale route cannot make the capsule pass it.
    auto* Wall=W.World->GetTestWorld()->SpawnActor<AActor>();
    auto* Barrier=NewObject<UBoxComponent>(Wall); Wall->SetRootComponent(Barrier);
    Barrier->SetBoxExtent(FVector(1000,10,250)); Barrier->SetCollisionProfileName(TEXT("BlockAll"));
    Barrier->SetCanEverAffectNavigation(false); Barrier->RegisterComponent(); Wall->AddInstanceComponent(Barrier);
    Wall->SetActorLocation(Center+FVector(0,600,150));
    const FVector Before=Boss->GetActorLocation();
    UGameplayStatics::ApplyDamage(Boss,Boss->Health-Boss->MaxHealth*.69f,W.Hero()->GetController(),W.Hero(),UDamageType::StaticClass());
    if(!Tick(135)) return false;
    TestEqual(TEXT("The native health threshold enters P2"),Boss->PhaseIndex(),1);
    TestTrue(TEXT("A solid wall keeps the retreat pending past two seconds"),Boss->IsPhaseTransitioning()&&!Boss->IsOnSummitDais());
    TestTrue(TEXT("The capsule remains on the near side of the wall"),Boss->GetActorLocation().Y>Center.Y+600);
    TestEqual(TEXT("A blocked retreat preserves the P1 save"),SavedPhase(),0);
    TestEqual(TEXT("Constructs cannot spawn before physical arrival"),Boss->LiveAdds(),0);
    Wall->Destroy();
    FVector Previous=Boss->GetActorLocation();
    bool Swept=true,ClearOfSpine=true;
    for(int32 Frame=0;Frame<1200&&Boss->IsPhaseTransitioning();++Frame)
    {
        if(!Tick(1)) return false;
        const FVector At=Boss->GetActorLocation();
        Swept&=FVector::Dist(At,Previous)<45;
        ClearOfSpine&=FVector::Dist2D(At,Center)>=200+Boss->GetCapsuleComponent()->GetScaledCapsuleRadius()-2;
        Previous=At;
    }
    if(!Boss->IsOnSummitDais()) AddInfo(FString::Printf(TEXT("Retreat failed: before=%s after=%s mode=%d base=%s"),
        *Before.ToString(),*Boss->GetActorLocation().ToString(),int32(Boss->GetCharacterMovement()->MovementMode),*GetNameSafe(Boss->GetMovementBaseObject())));
    if(!TestTrue(TEXT("After the wall is removed, the boss walks onto the raised dais"),Boss->IsOnSummitDais()&&!Boss->IsPhaseTransitioning())) return false;
    TestTrue(TEXT("Every retreat step uses continuous capsule movement outside the spine"),Swept&&ClearOfSpine&&FVector::Dist2D(Before,Boss->GetActorLocation())>300);
    if(!Tick(2)) return false;
    TestEqual(TEXT("P2 saves only after minimum timing and physical arrival"),SavedPhase(),1);
    TestEqual(TEXT("The summon still honors its windup after arrival"),Boss->LiveAdds(),0);
    for(int32 Frame=0;Frame<90&&Boss->LiveAdds()<2;++Frame)
        if(!Tick(1)) return false;
    TestEqual(TEXT("The authored first pair of constructs arrives after its windup"),Boss->LiveAdds(),2);
    const FVector Stand=Boss->GetActorLocation();
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
        if(It->Summoner()==Boss&&It->IsAlive()) UGameplayStatics::ApplyDamage(*It,It->Health,W.Hero()->GetController(),W.Hero(),UDamageType::StaticClass());
    if(!Tick(90)) return false;
    TestTrue(TEXT("The exposed collector holds the dais instead of pursuing the hero"),Boss->IsOnSummitDais()&&FVector::Dist(Stand,Boss->GetActorLocation())<5);
    UGameplayStatics::ApplyDamage(Boss,Boss->Health-Boss->MaxHealth*.39f,W.Hero()->GetController(),W.Hero(),UDamageType::StaticClass());
    if(!Tick(120)) return false;
    TestTrue(TEXT("The cane draw retains its full 2.5 second interval"),Boss->PhaseIndex()==2&&Boss->IsPhaseTransitioning());
    TestEqual(TEXT("P3 does not save during the draw interval"),SavedPhase(),1);
    if(!Tick(40)) return false;
    TestFalse(TEXT("The cane phase becomes playable after its interval"),Boss->IsPhaseTransitioning());
    TestEqual(TEXT("P3 saves at the completed transition"),SavedPhase(),2);
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraSummitPhaseReloadTest,"SoraArena.Campaign.SummitPhaseReload",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraSummitPhaseReloadTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    SoraFieldcraftAutomation::FBeatWorld W(*this,TEXT("SummitPhaseReload"),7,13);
    if(!W.Start(0,INDEX_NONE,1)||!W.Tick(30)) return false;
    const auto* Boss=W.Campaign()->CampaignBoss();
    TestTrue(TEXT("The completed P2 checkpoint resumes on the dais without replaying a retreat"),
        Boss&&Boss->PhaseIndex()==1&&Boss->IsOnSummitDais()&&!Boss->IsPhaseTransitioning());
    return !HasAnyErrors();
}
#endif
