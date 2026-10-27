#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraEnemy.h"
#include "SoraEnemyController.h"
#include "SoraGameEvents.h"
#include "Components/CapsuleComponent.h"
#include "Misc/ScopeExit.h"

namespace SoraMoltenTest
{
using SoraFieldcraftAutomation::FBeatWorld;
// Directed mechanic fixture: checkpoint/health are seeded and hostile AI is
// frozen. Player approaches and jumps use real mappings, collision and clocks.
// The second test places real registered wave opponents onto the channels;
// it proves contact/credit, not autonomous lure AI or encounter difficulty.
void Freeze(FBeatWorld& W)
{
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
    {
        if(!It->IsAlive()) continue;
        It->SetActorTickEnabled(false);
        It->GetCharacterMovement()->StopMovementImmediately();
        if(auto* Brain=Cast<ASoraEnemyController>(It->GetController()))
        { Brain->StopMovement(); Brain->SetActorTickEnabled(false); }
        // Movement still ticks to settle the real capsule onto the floor.
    }
}
bool Tick(FBeatWorld& W,int Frames)
{
    for(int I=0;I<Frames;++I) { Freeze(W); if(!W.Tick(1)) return false; }
    return true;
}
bool Ready(FBeatWorld& W)
{
    if(!FSoraCatalog::Get().Load()||!W.Start()) return false;
    W.Harden();
    for(int I=0;I<1800&&!W.Mode()->IsPlaying();++I) if(!Tick(W,1)) return false;
    return W.Test.TestTrue(TEXT("Casting floor is in play with four typed channels"),
        W.Mode()->IsPlaying()&&W.Campaign()->ActiveBeat()==14&&W.BeatData().Space.Molten.Channels.Num()==4&&W.Fieldcraft()->IsStaged());
}
bool Clock(FBeatWorld& W,int Low,int High)
{
    for(int I=0;I<1500;++I)
    {
        const int Ms=W.Fieldcraft()->MoltenClock();
        if(Ms>=Low&&Ms<=High) return true;
        if(!Tick(W,1)) return false;
    }
    return W.Test.TestTrue(TEXT("Live casting cycle reaches requested interval"),false);
}
bool Walk(FBeatWorld& W,FVector2D At)
{
    for(int I=0;I<600&&FVector2D::Distance(FVector2D(W.Hero()->GetActorLocation()),At)>15;++I)
    {
        const FVector Delta=FVector(At,0)-W.Hero()->GetActorLocation();
        W.Look(Delta.GetSafeNormal2D().Rotation());
        if(!W.World->InjectKey(EKeys::W,IE_Pressed)||!Tick(W,1)) return false;
    }
    if(!W.World->InjectKey(EKeys::W,IE_Released)||!Tick(W,12)) return false;
    return W.Test.TestTrue(TEXT("Mapped walking reaches the open aisle with collision enabled"),
        FVector2D::Distance(FVector2D(W.Hero()->GetActorLocation()),At)<45&&W.Hero()->GetActorEnableCollision());
}
FKey Jump(FBeatWorld& W)
{
    for(const auto& Key:W.Hero()->GetActionKeys(TEXT("Jump"))) if(!Key.IsGamepadKey()) return Key;
    return FKey();
}
void Place(ASoraEnemy& Enemy,const FVector2D& At,float Feet=2.5f)
{
    Enemy.GetCharacterMovement()->StopMovementImmediately();
    Enemy.SetActorLocation(FVector(At,Feet+Enemy.GetCapsuleComponent()->GetScaledCapsuleHalfHeight()),false,nullptr,ETeleportType::TeleportPhysics);
    Enemy.GetCharacterMovement()->SetMovementMode(Feet>8?MOVE_Flying:MOVE_Falling);
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraMoltenPlayerTest,"SoraArena.Campaign.CastingChannelTraversal",
 EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraMoltenPlayerTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraMoltenTest;
    FBeatWorld W(*this,TEXT("CastingChannelTraversal"),4,14);
    if(!Ready(W)) return false;
    auto* Bus=USoraGameEvents::Get(W.Hero()); if(!TestNotNull(TEXT("Damage bus"),Bus)) return false;
    float Damage=0;int Deaths=0;
    const auto Hurt=Bus->OnDamaged.AddLambda([&](const FSoraDamagedEvent& E) { if(E.Victim==W.Hero()) Damage+=E.Amount; });
    const auto Died=Bus->OnDied.AddLambda([&](const FSoraDiedEvent& E) { if(E.Victim==W.Hero()) ++Deaths; });
    ON_SCOPE_EXIT { Bus->OnDamaged.Remove(Hurt); Bus->OnDied.Remove(Died); };
    if(!Walk(W,FVector2D(67050,0))||!Walk(W,FVector2D(67050,200))||!Clock(W,2500,2700)) return false;
    const float Before=Damage;
    W.Look(FRotator(0,90,0));
    if(!W.World->InjectKey(EKeys::W,IE_Pressed)||!W.World->InjectKey(Jump(W),IE_Pressed)) return false;
    bool CrossedInAir=false;float Peak=0;
    for(int Frame=0;Frame<180&&W.Hero()->GetActorLocation().Y<490;++Frame)
    {
        if(!Tick(W,1)) return false;
        const auto At=W.Hero()->GetActorLocation();
        const float Feet=At.Z-W.Hero()->GetCapsuleComponent()->GetScaledCapsuleHalfHeight(); Peak=FMath::Max(Peak,Feet);
        if(At.Y>=310&&At.Y<=390&&!W.Hero()->GetCharacterMovement()->IsMovingOnGround()&&Feet>8&&
           SoraMoltenRules::Phase(W.Fieldcraft()->MoltenClock())==SoraMoltenRules::EPhase::Flow) CrossedInAir=true;
    }
    if(!W.World->InjectKey(Jump(W),IE_Released)||!W.World->InjectKey(EKeys::W,IE_Released)||!Tick(W,90)) return false;
    TestTrue(TEXT("Mapped jump crosses a flowing strip airborne then lands safely"),CrossedInAir&&Peak>100&&
        W.Hero()->GetActorLocation().Y>430&&W.Hero()->GetCharacterMovement()->IsMovingOnGround());
    TestTrue(TEXT("Airborne traversal acquires no burn or damage"),Damage==Before&&W.Fieldcraft()->MoltenBurnLeft(*W.Hero())==0);
    if(!Walk(W,FVector2D(67050,350))||!Clock(W,2500,2700)) return false;
    const float ContactBefore=Damage;
    if(!Tick(W,60)) return false;
    TestTrue(TEXT("Grounded contact integrates exactly 35 HP/s within one integer HP"),FMath::Abs(Damage-ContactBefore-35)<=1);
    TestEqual(TEXT("Contact refreshes the one residual burn"),W.Fieldcraft()->MoltenBurnLeft(*W.Hero()),2000);
    if(!W.Press(EKeys::Escape)) return false;
    const int FrozenClock=W.Fieldcraft()->MoltenClock(),FrozenBurn=W.Fieldcraft()->MoltenBurnLeft(*W.Hero());const float FrozenDamage=Damage;
    if(!W.Tick(120)) return false;
    TestTrue(TEXT("Pause preserves both cycle and burn without dealing damage"),W.Mode()->bMenu&&
        W.Fieldcraft()->MoltenClock()==FrozenClock&&W.Fieldcraft()->MoltenBurnLeft(*W.Hero())==FrozenBurn&&Damage==FrozenDamage);
    if(!W.Press(EKeys::Escape)||!W.World->InjectKey(Jump(W),IE_Pressed)||!Tick(W,30)) return false;
    TestTrue(TEXT("Jumping after contact retains and consumes the existing burn"),!W.Hero()->GetCharacterMovement()->IsMovingOnGround()&&
        W.Fieldcraft()->MoltenBurnLeft(*W.Hero())>0&&W.Fieldcraft()->MoltenBurnLeft(*W.Hero())<2000&&Damage>FrozenDamage);
    if(!W.World->InjectKey(Jump(W),IE_Released)||!Tick(W,70)||!Walk(W,FVector2D(67050,550))||!Tick(W,180)) return false;
    TestEqual(TEXT("Residual burn expires outside the strip"),W.Fieldcraft()->MoltenBurnLeft(*W.Hero()),0);
    const float Cooled=Damage;if(!Tick(W,60)) return false;
    TestEqual(TEXT("Safe ground after expiration deals no damage"),Damage,Cooled);
    if(!Walk(W,FVector2D(67050,350))||!Clock(W,2500,2700)) return false;
    W.Hero()->Health=1; // Defeat boundary setup only; actual channel damage must kill.
    for(int I=0;I<120&&!W.Mode()->bDefeated;++I) if(!Tick(W,1)) return false;
    TestTrue(TEXT("Environmental player death uses ordinary defeat exactly once and clears burn"),
        W.Mode()->bDefeated&&Deaths==1&&W.Fieldcraft()->MoltenBurnLeft(*W.Hero())==0);
    if(!W.Tick(120)||!W.Press(EKeys::Enter)||!Tick(W,4)) return false;
    TestTrue(TEXT("Retry starts a fresh channel attempt without old burn"),!W.Mode()->bDefeated&&W.Campaign()->ActiveBeat()==14&&
        W.Fieldcraft()->IsStaged()&&W.Fieldcraft()->MoltenClock()<2000&&W.Fieldcraft()->MoltenBurnLeft(*W.Hero())==0);
    W.Fieldcraft()->Clear();const float End=Damage;
    if(!Tick(W,120)) return false;
    TestTrue(TEXT("Explicit encounter teardown leaves no ticking burn"),!W.Fieldcraft()->IsStaged()&&Damage==End);
    AddInfo(TEXT("Directed casting traversal: seeded b15 checkpoint, hardened health, frozen enemy AI; real mapped walking/jump, collision, world-time damage, pause, lethal contact and Enter retry. No visual-quality or difficulty acceptance."));
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraMoltenEnemyTest,"SoraArena.Campaign.CastingChannelEnemyCredit",
 EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraMoltenEnemyTest::RunTest(const FString& Parameters)
{
    (void)Parameters;using namespace SoraMoltenTest;
    FBeatWorld W(*this,TEXT("CastingChannelEnemyCredit"),4,14);if(!Ready(W)) return false;
    if(!Clock(W,10000,10200)) return false;
    ASoraEnemy* Automaton=nullptr;TArray<ASoraEnemy*> Rifles;
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
        if(It->IsAlive()) { if(It->ArchetypeId()==TEXT("loom_automaton")) Automaton=*It;else Rifles.Add(*It); }
    if(!TestNotNull(TEXT("Authored first-wave automaton"),Automaton)||!TestEqual(TEXT("Authored first-wave rifles"),Rifles.Num(),2)) return false;
    auto* Rifle=Rifles[0];auto* Airborne=Rifles[1];Rifle->Health=Rifle->MaxHealth=1000;
    Place(*Automaton,FVector2D(67050,-1000));Place(*Rifle,FVector2D(67200,-1000));Place(*Airborne,FVector2D(67100,1000),250);
    auto* Bus=USoraGameEvents::Get(W.Hero());if(!TestNotNull(TEXT("Damage bus"),Bus)) return false;
    int Deaths=0;float Damage=0,AirDamage=0;bool EnvironmentalKiller=false;
    const auto Hurt=Bus->OnDamaged.AddLambda([&](const FSoraDamagedEvent& E)
        { if(E.Victim==Rifle) Damage+=E.Amount;if(E.Victim==Airborne) AirDamage+=E.Amount; });
    const auto Died=Bus->OnDied.AddLambda([&](const FSoraDiedEvent& E)
        { if(E.Victim==Automaton) { ++Deaths;EnvironmentalKiller=E.Killer!=nullptr&&E.Killer!=W.Hero(); } });
    ON_SCOPE_EXIT { Bus->OnDamaged.Remove(Hurt);Bus->OnDied.Remove(Died); };
    const int Down=W.Campaign()->TaskProgress().Down[0];
    if(!Clock(W,1800,1900)) return false;
    TestTrue(TEXT("Cooling and amber warning cause no enemy damage"),Automaton->IsAlive()&&Damage==0&&AirDamage==0);
    if(!Clock(W,2200,2300)) return false;
    TestTrue(TEXT("Molten contact destroys the registered automaton through ordinary environmental death"),Deaths==1&&EnvironmentalKiller);
    TestTrue(TEXT("Only its registered wave receives one defeat"),W.Campaign()->TaskProgress().Down[0]==Down+1&&W.Campaign()->TaskProgress().Down[1]==0);
    Rifle->Stagger(2000);const float Before=Damage;
    if(!Tick(W,60)) return false;
    TestTrue(TEXT("Ordinary enemy rate remains 60 HP/s even while staggered"),FMath::Abs(Damage-Before-60)<=1);
    TestEqual(TEXT("Raised airborne enemy above the flowing strip takes no contact damage"),AirDamage,0.f);
    TestTrue(TEXT("The corpse cannot earn duplicate wave credit on later ticks"),Deaths==1&&W.Campaign()->TaskProgress().Down[0]==Down+1);
    Place(*Rifle,FVector2D(67200,-500));if(!Tick(W,2)) return false;const float Off=Damage;
    if(!Tick(W,120)) return false;
    TestEqual(TEXT("Ordinary enemies have no invented residual burn"),Damage,Off);
    AddInfo(TEXT("Directed casting enemy fixture: real first-wave actors placed onto channels, AI frozen, one rifle HP hardened and one flying control; real OnDamaged/OnDied and registered-wave credit, no task-counter edits or lure-AI acceptance."));
    return !HasAnyErrors();
}
#endif
