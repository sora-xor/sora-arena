#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraEnemy.h"
#include "SoraEnemyController.h"
#include "Components/PointLightComponent.h"
#include "Engine/PointLight.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraRegistryPatrolTest,"SoraArena.Campaign.RegistryPatrols",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraRegistryPatrolTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using SoraFieldcraftAutomation::FBeatWorld;
    if(!FSoraCatalog::Get().Load()) return false;
    FBeatWorld W(*this,TEXT("RegistryPatrols"),5,7);
    if(!W.Start()) return false;
    W.Harden();
    const auto& Space=W.BeatData().Space;
    // Observe real authored guards from behind the registry's solid south
    // wall. No replacement patrols, disabled senses or frozen opponents.
    W.Stand(FVector(Space.RegistryHall.Origin+FVector2D(1200,600),0));
    auto* Craft=W.Fieldcraft();
    for(int I=0;I<3;++I)
        if(!TestNotNull(TEXT("The authored auditor is assigned to its desk"),Craft->RegistryAuditor(I))) return false;
    ASoraEnemy *Rifle=nullptr,*Drone=nullptr;
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
    {
        if(It->ArchetypeId()==TEXT("enforcer_rifle")) Rifle=*It;
        if(It->ArchetypeId()==TEXT("drone")) Drone=*It;
    }
    auto* RifleBrain=Rifle?Cast<ASoraEnemyController>(Rifle->GetController()):nullptr;
    auto* DroneBrain=Drone?Cast<ASoraEnemyController>(Drone->GetController()):nullptr;
    if(!TestNotNull(TEXT("The authored perimeter rifle guard is present"),RifleBrain)||
        !TestNotNull(TEXT("The authored four-metre drone is present"),DroneBrain)) return false;
    const auto AllLit=[&]() { return Craft->RegistryLampLit(0)&&Craft->RegistryLampLit(1)&&Craft->RegistryLampLit(2); };
    for(int Frame=0;Frame<120&&!AllLit();++Frame) if(!W.Tick(1)) return false;
    if(!TestTrue(TEXT("All three auditors begin a real desk visit"),AllLit())) return false;
    TArray<TWeakObjectPtr<APointLight>> OriginalLights;
    for(TActorIterator<APointLight> It(W.World->GetTestWorld());It;++It)
        if(It->Tags.Contains(TEXT("RegistryDeskLamp")))
        {
            OriginalLights.Add(*It);
            TestTrue(TEXT("Registry lamps use cold light"),It->PointLightComponent->LightColor.B>It->PointLightComponent->LightColor.R);
        }
    TestEqual(TEXT("The registry owns exactly three desk lamps"),OriginalLights.Num(),3);
    if(!W.Tick(60)||!W.Press(EKeys::Escape)) return false;
    FVector Paused[3];for(int I=0;I<3;++I) Paused[I]=Craft->RegistryAuditor(I)->GetActorLocation();
    if(!W.Tick(300)) return false;
    TestTrue(TEXT("Opening the menu keeps the current desk lights"),AllLit());
    for(int I=0;I<3;++I)
        TestTrue(TEXT("Menu pause holds the auditor in place"),Craft->RegistryAuditor(I)->GetActorLocation().Equals(Paused[I],1.f));
    if(!W.Press(EKeys::Escape)) return false;
    float FirstDeparture[3]={-1,-1,-1};bool Returned[3]={false,false,false};
    for(int Frame=1;Frame<=5400;++Frame)
    {
        if(!W.Tick(1)) return false;
        if(!TestTrue(TEXT("The drone follows its actual four-metre flight layer"),FMath::IsNearlyEqual(Drone->GetActorLocation().Z,400.f,5.f))||
            !TestTrue(TEXT("The perimeter patrol stays grounded"),Rifle->GetCharacterMovement()->IsMovingOnGround())) return false;
        for(int I=0;I<3;++I)
        {
            auto* Guard=Craft->RegistryAuditor(I);
            const auto* Brain=Guard?Cast<ASoraEnemyController>(Guard->GetController()):nullptr;
            if(!TestTrue(TEXT("The observation leaves each authored auditor calmly patrolling"),
                Guard&&Brain&&Brain->State()==SoraStealthRules::EState::Unaware)) return false;
            const bool Lit=Craft->RegistryLampLit(I);
            if(Lit)
                TestTrue(TEXT("A lit desk has its auditor physically present and stopped"),Brain->IsPatrolPausedAt(0)&&
                    FVector::Dist2D(Guard->GetActorLocation(),FVector(Space.Objectives[I],0))<=80.f);
            if(!Lit&&FirstDeparture[I]<0) FirstDeparture[I]=1.f+float(Frame)/60.f;
            if(Lit&&FirstDeparture[I]>=0) Returned[I]=true;
        }
        if(Returned[0]&&Returned[1]&&Returned[2]&&RifleBrain->PatrolTiming().Cycles>=1&&DroneBrain->PatrolTiming().Cycles>=2) break;
    }
    for(const auto& Patrol:{TPair<ASoraEnemyController*,int32>(RifleBrain,60000),TPair<ASoraEnemyController*,int32>(DroneBrain,30000)})
    {
        const auto& Timing=Patrol.Key->PatrolTiming();
        TestTrue(TEXT("The authored circuit finishes at its actual scheduled period without skipped arrivals"),
            Timing.Cycles>=1&&!Timing.Overdue&&FMath::Abs(Timing.LastCycleMs-Patrol.Value)<=50);
        AddInfo(FString::Printf(TEXT("Registry circuit %d ms: cycles=%d actual=%lld overdue=%d"),
            Patrol.Value,Timing.Cycles,Timing.LastCycleMs,Timing.Overdue));
    }
    for(int I=0;I<3;++I)
    {
        TestTrue(FString::Printf(TEXT("Auditor %d stays at its desk for the authored %d ms"),I,SoraRegistryRules::AuditorDwellMs(I)),
            FMath::Abs(FirstDeparture[I]-SoraRegistryRules::AuditorDwellMs(I)/1000.f)<=.25f);
        TestTrue(TEXT("The auditor walks its circuit and lights the desk again on return"),Returned[I]);
        AddInfo(FString::Printf(TEXT("Registry auditor %d initial lit visit %.3f s, returned=%d"),I,FirstDeparture[I],Returned[I]));
    }
    auto* Guard=Craft->RegistryAuditor(0);
    FBeatWorld::Hurt(*Guard,Guard->Health+1000.f);
    if(!W.Tick(2)) return false;
    TestFalse(TEXT("A defeated auditor cannot leave its desk lamp on"),Craft->RegistryLampLit(0));
    FBeatWorld::Hurt(*W.Hero(),W.Hero()->Health+1000.f);
    if(!W.Tick(2)||!W.Press(EKeys::Enter)||!W.Tick(2)) return false;
    TestEqual(TEXT("Retry restarts the registry encounter"),W.Campaign()->ActiveBeat(),7);
    for(const auto& Light:OriginalLights)
        TestFalse(TEXT("Retry destroys the previous encounter's desk lights"),Light.IsValid());
    int Count=0;
    for(TActorIterator<APointLight> It(W.World->GetTestWorld());It;++It)
        Count+=It->Tags.Contains(TEXT("RegistryDeskLamp"))?1:0;
    TestEqual(TEXT("Retry creates exactly one new lamp per desk"),Count,3);
    AddInfo(TEXT("Directed actual-guard dwell/light/retry fixture. The hero is deliberately behind the room wall; this does not establish ordinary stealth difficulty or final art."));
    return true;
}
#endif
