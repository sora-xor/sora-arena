#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraSpireAutomation.h"
#include "Components/BoxComponent.h"
#include "GameFramework/DamageType.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraSpireCompanionsTest,"SoraArena.Fieldcraft.SpireCompanions",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraSpireCompanionsTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    SoraFieldcraftAutomation::FBeatWorld W(*this,TEXT("SpireCompanions"),7,9);
    if(!W.Start()||!W.Tick(2)) return false;
    W.Harden();
    const auto Space=W.Campaign()->ActiveBeatData()->Space;
    const auto Allies=W.Fieldcraft()->AlliesInPlay();
    if(!TestEqual(TEXT("Two fighters and three guides join the spire"),Allies.Num(),5)) return false;
    const auto ClearCombat=[&](bool LeaveDrones=false)
    {
        for(int32 Pass=0;Pass<20;++Pass)
        {
            ASoraEnemy* Enemy=nullptr;
            for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It&&!Enemy;++It) if(It->IsAlive()&&(!LeaveDrones||!It->IsFlying())) Enemy=*It;
            if(!Enemy) return true;
            UGameplayStatics::ApplyDamage(Enemy,Enemy->Health,W.Hero()->GetController(),W.Hero(),UDamageType::StaticClass());
            if(!W.Tick(1)) return false;
        }
        return false;
    };
    const auto Gathered=[&]()
    {
        for(const ASoraCompanion* Ally:Allies)
            if(!Ally||Ally->IsDown()||FVector::Dist(Ally->GetActorLocation(),W.Hero()->GetActorLocation())>500.f||
                FMath::Abs(Ally->GetActorLocation().Z-W.Hero()->GetActorLocation().Z)>100.f) return false;
        return true;
    };
    // The hero walks the whole route with ordinary input; every companion
    // follows through swept movement and navigation, with no placement calls.
    if(!TestTrue(TEXT("The fixture clears all prior combat"),ClearCombat())) return false;
    for(int32 Level=1;Level<4;++Level)
    {
        const int32 From=Level==1?0:SoraSpireRules::Landing(Level-1)+1;
        if(!SoraSpireAutomation::Climb(*W.World,Space,From,SoraSpireRules::Landing(Level))) return false;
        SoraLiftAutomation::HoldThreats(*W.World);
        // Keep the airborne final-wave foes alive until all allies gather.
        // Fighters ignore them; the combat gate keeps staging stable at L4.
        if(!TestTrue(TEXT("The fixture clears ground combat while preserving airborne gate holders"),ClearCombat(Level>=2))) return false;
        for(int32 Frame=0;Frame<1800&&!Gathered();++Frame) if(!W.Tick(1)) return false;
        if(!Gathered())
            for(const ASoraCompanion* Ally:Allies)
                AddInfo(FString::Printf(TEXT("L%d gather: hero=%s ally=%s position=%s down=%d"),Level+1,
                    *W.Hero()->GetActorLocation().ToString(),*GetNameSafe(Ally),Ally?*Ally->GetActorLocation().ToString():TEXT("missing"),Ally&&Ally->IsDown()));
        if(!TestTrue(*FString::Printf(TEXT("All five allies physically reach L%d"),Level+1),Gathered())) return false;
    }
    TestEqual(TEXT("Following alone does not cross the L4 exit checkpoint"),W.Campaign()->ActiveBeat(),9);
    // Contact setup is deliberately separate from the traversal above. Hold
    // bodies fixed so only vertical reach and the actual wall decide a hit.
    ASoraCompanion* Fighter=nullptr;
    for(ASoraCompanion* Ally:Allies)
    {
        if(Ally->Role()==ASoraCompanion::ERole::Fighter&&Ally->WeaponId==0) Fighter=Ally;
        Ally->SetActorTickEnabled(false);
    }
    if(!TestNotNull(TEXT("Toranosuke carries the melee blade"),Fighter)) return false;
    const int32 L2=SoraSpireRules::Landing(1),Above=L2+6*SoraSpireRules::Subdivisions;
    const FVector Low=Space.Spire.Ramp[L2]+FVector(0,0,90);
    W.Hero()->GetCharacterMovement()->StopMovementImmediately();
    W.Hero()->SetActorLocation(Low+FVector(0,200,0),false,nullptr,ETeleportType::TeleportPhysics);
    if(!TestTrue(TEXT("The fixture clears all prior combat"),ClearCombat())) return false;
    Fighter->GetCharacterMovement()->StopMovementImmediately();
    Fighter->GetCharacterMovement()->SetComponentTickEnabled(false);
    Fighter->SetActorLocation(Low,false,nullptr,ETeleportType::TeleportPhysics);
    Fighter->SetActorTickEnabled(true);
    auto* Target=ASoraEnemy::SpawnArchetype(*W.World->GetTestWorld(),TEXT("blade_retainer"),0,
        Space.Spire.Ramp[Above]+FVector(0,0,90),FRotator::ZeroRotator);
    if(!TestNotNull(TEXT("An opponent occupies the winding directly above"),Target)) return false;
    Target->MaxHealth=10000.f; Target->Health=10000.f;
    SoraLiftAutomation::HoldThreats(*W.World);
    const int32 Before=Fighter->Strikes();
    if(!W.Tick(180)) return false;
    TestEqual(TEXT("Matching XY on a higher winding never lands a melee hit"),Fighter->Strikes(),Before);
    TestEqual(TEXT("The higher-floor opponent keeps its health"),Target->Health,10000.f);
    Target->SetActorLocation(Low+FVector(100,0,0),false,nullptr,ETeleportType::TeleportPhysics);
    AActor* Wall=W.World->GetTestWorld()->SpawnActor<AActor>();
    auto* Box=NewObject<UBoxComponent>(Wall,TEXT("SpireContactWall"));
    Wall->SetRootComponent(Box);
    Box->SetBoxExtent(FVector(10,100,150));
    Box->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
    Box->SetCollisionObjectType(ECC_WorldStatic);
    Box->SetCollisionResponseToAllChannels(ECR_Block);
    Box->SetCanEverAffectNavigation(false);
    Box->RegisterComponent();
    Wall->SetActorLocation(Low+FVector(50,0,0));
    if(!W.Tick(180)) return false;
    TestEqual(TEXT("A solid obstacle blocks a same-floor committed hit"),Fighter->Strikes(),Before);
    TestEqual(TEXT("The opponent behind the obstacle keeps its health"),Target->Health,10000.f);
    Wall->Destroy();
    for(int32 Frame=0;Frame<300&&Fighter->Strikes()==Before;++Frame) if(!W.Tick(1)) return false;
    TestTrue(TEXT("Clear same-floor blade contact still damages the opponent"),Fighter->Strikes()>Before&&Target->Health<10000.f);
    return !HasAnyErrors();
}
#endif
