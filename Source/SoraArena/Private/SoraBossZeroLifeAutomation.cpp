#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraEnemyTestArena.h"
#include "SoraBoss.h"
#include "SoraCatalog.h"
#include "SoraGameEvents.h"
#include "Combat/SoraBossCatalog.h"
#include "Combat/SoraBossHazard.h"
#include "Combat/SoraCombatEffects.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Misc/ScopeExit.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraBossZeroLifeTest,"SoraArena.Boss.ZeroLifeSeizureNet",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraBossZeroLifeTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if(!FSoraCatalog::Get().Load()||!FSoraBossCatalog::Get().Load()) return false;
    SoraEnemyTest::FArena Arena(*this,TEXT("ZeroLifeSeizureNet"));
    if(!Arena.Start()||!Arena.Tick(20)) return false;
    auto* Hero=Arena.Hero();
    const FVector Feet=Hero->GetActorLocation()-FVector(0,0,Hero->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
    auto* Boss=ASoraBoss::SpawnBoss(*Arena.Get(),TEXT("boss_hakari"),0,Feet+FVector(800,0,120),FRotator(0,180,0));
    if(!TestNotNull(TEXT("Actual Hakari data spawns"),Boss)) return false;
    Boss->SetActorTickEnabled(false);
    if(auto* Brain=Boss->GetController()) Brain->SetActorTickEnabled(false);
    Boss->GetCharacterMovement()->StopMovementImmediately();
    const int32 Attack=Boss->Data()->AttackIndex(TEXT("seizure_net"));
    if(!TestTrue(TEXT("The authored net is a zero-life root"),Attack!=INDEX_NONE&&
        Boss->Data()->Attacks[Attack].LifeMs==0&&Boss->RootFor(Attack)>0)) return false;
    const int32 Warning=Boss->WindupFor(Attack),RootMs=Boss->RootFor(Attack);
    auto* Effects=USoraCombatEffects::Get(Arena.Get());
    auto* Events=USoraGameEvents::Get(Arena.Get());
    if(!Effects||!Events) return false;
    int32 Strikes=0;
    const auto Handle=Events->OnBossPhase.AddLambda([&](const FSoraBossPhaseEvent& E)
    { if(E.Boss==Boss&&E.Phase==ESoraBossPhase::Strike&&E.Detail==TEXT("seizure_net")) ++Strikes; });
    ON_SCOPE_EXIT { Events->OnBossPhase.Remove(Handle); };
    const auto MakeNet=[&](FVector At,int32 Serial)
    {
        FActorSpawnParameters Params; Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        auto* Net=Arena.Get()->SpawnActor<ASoraBossHazard>(At,FRotator::ZeroRotator,Params);
        if(Net) Net->BeginZone(*Boss,Attack,Serial,Warning,RootMs);
        return Net;
    };
    auto* Net=MakeNet(Feet,7001);
    if(!TestNotNull(TEXT("Actual hazard actor owns the net"),Net)) return false;
    if(!Arena.World->Tick(1,(Warning-2)/1000.f)) return false;
    TestFalse(TEXT("No root before the warning deadline"),Effects->IsRooted(Hero));
    TestEqual(TEXT("No early strike announcement"),Strikes,0);
    // Deliberately miss the exact one-millisecond Armed sample. No Expire or
    // direct Tick call is used; the world observes the deadline normally.
    if(!Arena.World->Tick(1,.019f)) return false;
    TestTrue(TEXT("Crossing roots the hero despite skipping the narrow sample"),Effects->IsRooted(Hero)&&Hero->GetCharacterMovement()->MovementMode==MOVE_None);
    TestEqual(TEXT("Exactly one net strike"),Strikes,1);
    const TWeakObjectPtr<ASoraBossHazard> Spent=Net;
    if(!Arena.World->Tick(2,.001f)) return false;
    TestTrue(TEXT("The released zero-life net is spent and removed"),!Spent.IsValid()||Spent->IsSpent());
    TestEqual(TEXT("Later observations never repeat the strike"),Strikes,1);
    if(!Arena.World->Tick(1,(RootMs-100)/1000.f)) return false;
    TestTrue(TEXT("The authored root lifetime is retained"),Effects->IsRooted(Hero));
    if(!Arena.World->Tick(1,.2f)) return false;
    TestFalse(TEXT("The ordinary effect timer releases movement"),Effects->IsRooted(Hero));
    auto* Cancelled=MakeNet(Feet,7002);
    if(!Cancelled) return false;
    Cancelled->Destroy();
    if(!Arena.World->Tick(1,(Warning+50)/1000.f)) return false;
    TestTrue(TEXT("A cancelled warning never releases"),Strikes==1&&!Effects->IsRooted(Hero));
    auto* Miss=MakeNet(Feet+FVector(2000,0,0),7003);
    if(!Miss||!Arena.World->Tick(1,(Warning+50)/1000.f)||!Arena.Tick(1)) return false;
    TestTrue(TEXT("An out-of-range net expires without rooting the hero"),Strikes==1&&!Effects->IsRooted(Hero));
    auto* Orphan=MakeNet(Feet,7004);
    if(!Orphan) return false;
    Boss->Destroy();
    if(!Arena.World->Tick(1,(Warning+50)/1000.f)) return false;
    TestTrue(TEXT("Losing the keeper cancels the pending release"),Strikes==1&&!Effects->IsRooted(Hero));
    return !HasAnyErrors();
}
#endif
