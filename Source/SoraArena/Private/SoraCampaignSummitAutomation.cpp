#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraLiftAutomation.h"
#include "SoraBoss.h"
#include "SoraWorldBuilder.h"
#include "World/SoraNavigation.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraCampaignSummitTest,"SoraArena.Campaign.SummitTraversal",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraCampaignSummitTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    SoraFieldcraftAutomation::FBeatWorld W(*this,TEXT("SummitTraversal"),7,12);
    if(!W.Start()||!W.Tick(30)) return false;
    W.Harden();
    const auto S=W.Campaign()->ActiveBeatData()->Space;
    TestTrue(TEXT("The summit checkpoint enters on its 160 metre floor"),FMath::Abs(W.Hero()->GetActorLocation().Z-16090)<10.f);
    TestEqual(TEXT("Height resolves the summit above the overlapping spire"),W.Campaign()->ActiveChapter()->Space.ZoneAt(W.Hero()->GetActorLocation()),S.Zone);
    if(!W.Press(EKeys::Enter)||!W.Tick(2)) return false;
    TestEqual(TEXT("Skipping the authored cinematic still starts its boss"),W.Campaign()->ActiveBeat(),13);
    auto* Boss=W.Campaign()->CampaignBoss();
    if(!TestNotNull(TEXT("Val Amort spawns on the summit"),Boss)) return false;
    TestTrue(TEXT("The boss is on the elevated floor"),Boss->GetActorLocation().Z>16000);
    TestTrue(TEXT("Its arena is centered on the disc"),FVector::Dist2D(Boss->ArenaCenter(),FVector(S.Summit.Center,0))<1.f);
    SoraLiftAutomation::HoldThreats(*W.World);
    const FVector Center(S.Summit.Center,16000);
    if(!SoraLiftAutomation::Walk(*W.World,Center+FVector(600,0,0))||
       !SoraLiftAutomation::Walk(*W.World,Center+FVector(350,0,120))) return false;
    TestTrue(TEXT("Ordinary movement climbs the 1.2 metre dais steps"),FMath::Abs(W.Hero()->GetActorLocation().Z-16210)<10.f);
    if(!SoraLiftAutomation::Walk(*W.World,Center+FVector(1200,0,0))) return false;
    const float Before=W.Hero()->Health;
    W.Look(FRotator::ZeroRotator);
    FVector ExpectedRecovery;
    bool bRecoveryFound=false;
    for(int32 Frame=0;Frame<600&&W.Hero()->Health==Before;++Frame)
    {
        bRecoveryFound=W.Mode()->Arena()->SummitSafePoint(W.Hero()->GetActorLocation(),*W.Hero(),ExpectedRecovery);
        if(!W.World->InjectKey(EKeys::W,IE_Pressed)||!W.Tick(1)) return false;
    }
    if(!W.World->InjectKey(EKeys::W,IE_Released)||!W.Tick(2)) return false;
    TestEqual(TEXT("A real edge fall applies exactly 25 damage"),Before-W.Hero()->Health,25.f);
    TestTrue(TEXT("A surviving fall returns to firm floor in the same boss phase"),
        !W.Mode()->bDefeated&&W.Campaign()->ActiveBeat()==13&&bRecoveryFound&&FVector::Dist2D(W.Hero()->GetActorLocation(),ExpectedRecovery)<50&&
        FMath::Abs(W.Hero()->GetActorLocation().Z-16090)<10.f);
    auto* Save=Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(W.Slot,0));
    TestTrue(TEXT("Fall recovery preserves the authored boss checkpoint"),Save&&Save->CheckpointBeat==13);
    return !HasAnyErrors();
}
#endif
