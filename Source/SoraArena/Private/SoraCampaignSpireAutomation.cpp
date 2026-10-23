#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraSpireAutomation.h"
#include "World/SoraNavigation.h"
#include "GameFramework/DamageType.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraCampaignSpireTest,"SoraArena.Campaign.SpireTraversal",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraCampaignSpireTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    SoraFieldcraftAutomation::FBeatWorld W(*this,TEXT("SpireTraversal"),7,9);
    if(!W.Start()||!W.Tick(30)) return false;
    W.Harden();
    const auto Space=W.Campaign()->ActiveBeatData()->Space;
    if(!TestTrue(TEXT("Both gantry landings leave incoming and outgoing capsules clear"),SoraSpireAutomation::GantryClearance(*W.World,Space))) return false;
    const int32 L2=SoraSpireRules::Landing(1),L3=SoraSpireRules::Landing(2),L4=SoraSpireRules::Landing(3);
    const int32 LowerL3=L3%(6*SoraSpireRules::Subdivisions);
    const auto ClearCombat=[&]()
    {
        for(int32 Pass=0;Pass<20;++Pass)
        {
            ASoraEnemy* Enemy=nullptr;
            for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It&&!Enemy;++It) if(It->IsAlive()) Enemy=*It;
            if(!Enemy) return true;
            UGameplayStatics::ApplyDamage(Enemy,Enemy->Health,W.Hero()->GetController(),W.Hero(),UDamageType::StaticClass());
            if(!W.Tick(1)) return false;
        }
        return false;
    };
    if(!ClearCombat()) return false;
    TestEqual(TEXT("The first two waves keep their nine authored enemies"),W.Campaign()->Kills,9);
    // The lower winding has the L3 trigger's XY; entering there must not
    // release wave three. The route is walked by ordinary key input.
    if(!TestTrue(TEXT("The lower winding is physically reachable"),SoraSpireAutomation::Climb(*W.World,Space,0,LowerL3))) return false;
    TestEqual(TEXT("Matching XY on a lower winding cannot release the L3 wave"),W.Campaign()->KillsNeeded,16);
    TestFalse(TEXT("The L3 wave stays unreleased below its floor"),SoraBeatRules::Released(W.Campaign()->TaskProgress(),2));
    auto* Nav=USoraNavigation::Get(W.Mode());
    TArray<FVector> Route;
    const bool FullRoute=Nav&&Nav->Settle()&&
        Nav->FindPath(W.Hero()->GetActorLocation(),Space.Spire.Ramp.Last()+FVector(0,0,90),*W.Hero(),Route)&&
        !Route.IsEmpty()&&FMath::Abs(Route.Last().Z-2700)<100.f;
    if(!FullRoute)
    {
        AddInfo(FString::Printf(TEXT("Spire nav incomplete: hero=%s goal=%s points=%d end=%s"),
            *W.Hero()->GetActorLocation().ToString(),*Space.Spire.Ramp.Last().ToString(),Route.Num(),
            Route.IsEmpty()?TEXT("none"):*Route.Last().ToString()));
        // Keep full-route failure intact, but identify which local section
        // disconnects. A returned partial route is never a successful section.
        for(int32 N=1;N<Space.Spire.Ramp.Num();++N)
        {
            TArray<FVector> Section;
            const FVector A=Space.Spire.Ramp[N-1],B=Space.Spire.Ramp[N];
            const bool Found=Nav&&Nav->FindPath(A+FVector(0,0,90),B+FVector(0,0,90),*W.Hero(),Section);
            if(!Found||Section.IsEmpty()||FVector::Dist2D(Section.Last(),B)>80||FMath::Abs(Section.Last().Z-B.Z)>100)
                AddInfo(FString::Printf(TEXT("Spire nav section %d..%d incomplete: start=%s goal=%s points=%d end=%s"),
                    N-1,N,*A.ToString(),*B.ToString(),Section.Num(),Section.IsEmpty()?TEXT("none"):*Section.Last().ToString()));
        }
    }
    TestTrue(TEXT("Navigation sees a continuous route from the lower ramp to L4"),FullRoute);
    if(!TestTrue(TEXT("L2 is reached by walking the ramp"),SoraSpireAutomation::Climb(*W.World,Space,LowerL3+1,L2))) return false;
    if(!TestTrue(TEXT("The two-metre L2 gantry reaches its far marksman post"),
        SoraLiftAutomation::Walk(*W.World,Space.Spire.Spawns[4])&&FMath::Abs(W.Hero()->GetActorLocation().Z-990)<10.f&&
        SoraLiftAutomation::Walk(*W.World,Space.Spire.Ramp[L2]))) return false;
    if(!TestTrue(TEXT("L3 is reached by walking the ramp"),SoraSpireAutomation::Climb(*W.World,Space,L2+1,L3))) return false;
    TestTrue(TEXT("Only physical L3 arrival releases wave three"),SoraBeatRules::Released(W.Campaign()->TaskProgress(),2));
    int32 Drones=0;
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
        if(It->IsAlive()&&It->IsFlying()) { ++Drones; TestTrue(TEXT("Spire drones spawn in the upper void"),It->GetActorLocation().Z>1800.f); }
    TestEqual(TEXT("The final wave has four airborne drones"),Drones,4);
    if(!ClearCombat()||!W.Tick(60)) return false;
    TestEqual(TEXT("Clearing all sixteen enemies from L3 does not skip L4 traversal"),W.Campaign()->ActiveBeat(),9);
    auto* Save=Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(W.Slot,0));
    TestTrue(TEXT("There is no partial spiral checkpoint"),Save&&Save->CheckpointBeat==9);
    if(!TestTrue(TEXT("The final winding reaches L4 without a teleport"),SoraSpireAutomation::Climb(*W.World,Space,L3+1,L4))) return false;
    TestEqual(TEXT("The ramp endpoint alone does not skip the flat L4 landing"),W.Campaign()->ActiveBeat(),9);
    if(!SoraLiftAutomation::Walk(*W.World,FVector(Space.Exit.Center,2700))||!W.Tick(2)) return false;
    TestEqual(TEXT("L4 arrival advances to the lift"),W.Campaign()->ActiveBeat(),10);
    TestTrue(TEXT("The hero stays at L4 through staging"),FMath::Abs(W.Hero()->GetActorLocation().Z-2790)<10.f);
    Save=Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(W.Slot,0));
    TestTrue(TEXT("The authored lift-start boundary is now saved"),Save&&Save->CheckpointBeat==10);
    TestTrue(TEXT("The fixed L4 landing opens toward the spiral and the moving deck"),SoraLiftAutomation::Board(*W.World));
    return !HasAnyErrors();
}
#endif
