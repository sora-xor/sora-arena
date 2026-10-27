#include "SoraEnemy.h"
#include "SoraCampaignDirector.h"
#include "SoraGameMode.h"
#include "SoraGameEvents.h"
#include "SoraProjectile.h"
#include "SoraWorldBuilder.h"
#include "Combat/SoraDamage.h"
#include "Combat/SoraEnemyCatalog.h"
#include "SoraSettings.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/World.h"

namespace ShellRules=SoraHorseShellRules;
void ASoraEnemy::BindHorseShell(USoraCampaignDirector& Director,uint64 Generation)
{
    CancelAttack(); bHorseShellBound=true; HorseShellDirector=&Director; HorseShellGeneration=Generation;
    HorseShellClock={}; HorseShellMilliseconds.Reset();
    HorseShellLastWorldSeconds=GetWorld()->GetTimeSeconds();
}
void ASoraEnemy::EndPlay(const EEndPlayReason::Type Reason)
{
    CancelAttack(); Super::EndPlay(Reason);
}
bool ASoraEnemy::TryHorseShell(AActor& Target,const FVector& Landing)
{
    AdvanceHorseShellClock();
    auto* Director=HorseShellDirector.Get();
    if(!bHorseShellBound||!Director||!Director->HorseShellSession(HorseShellGeneration)||!CanPlay()||
       !Kind||!AttackSet().IsValidIndex(0)||Phase!=EPhase::Idle||IsStaggered()||IsTurnLocked()||
       !IsValid(&Target)||Target.IsActorBeingDestroyed()||!ShellRules::CanBegin(HorseShellClock)) return false;
    const float Distance=FVector::Dist2D(GetActorLocation(),Landing);
    if(Distance<ShellRules::MinRangeCm||Distance>ShellRules::MaxRangeCm||SoraDamage::FacingMilli(*this,Landing)<0) return false;
    FActorSpawnParameters Params; Params.Owner=this;
    auto* Warning=GetWorld()->SpawnActor<AActor>(Params);
    if(!Warning) return false;
    auto* Root=NewObject<USceneComponent>(Warning,TEXT("HorseShellWarningRoot"));
    Warning->SetRootComponent(Root); Root->RegisterComponent(); Warning->AddInstanceComponent(Root);
    Warning->SetActorLocation(Landing); Warning->Tags.Add(TEXT("SoraHorseShellWarning"));
    const auto Color=SoraAccessibility::TelegraphColor(this,SoraAccessibility::ETelegraph::Cleave);
    constexpr int Segments=48;
    for(int I=0;I<Segments;++I)
    {
        const float Angle=2.f*PI*I/Segments;
        auto* Mark=ASoraWorldBuilder::Shape(Warning,Root,TEXT("ShellLandingRing"),TEXT("/Engine/BasicShapes/Cube.Cube"),
            FVector(FMath::Cos(Angle)*ShellRules::RadiusCm,FMath::Sin(Angle)*ShellRules::RadiusCm,6),
            FVector(.06f,.41f,.03f),Color);
        if(!Mark||!Mark->GetStaticMesh()) { Warning->Destroy(); return false; }
        Mark->SetRelativeRotation(FRotator(0,FMath::RadiansToDegrees(Angle),0));
        Mark->SetCollisionEnabled(ECollisionEnabled::NoCollision); Mark->SetCastShadow(false);
    }
    // No lifespan: menu/dialogue holds preserve the complete visible warning.
    // The fixed landing point is never dragged after the hero baits this shot.
    ShellWarning=Warning; HorseShellTarget=&Target; LockedPoint=Landing;
    ShellRules::Begin(HorseShellClock);
    Phase=EPhase::Windup; AttackIndex=0;
    GetCharacterMovement()->StopMovementImmediately();
    Announce(ESoraEnemyCue::AttackWindup,AttackSet()[0].Cue);
    return true;
}
void ASoraEnemy::AdvanceHorseShellClock()
{
    const double Time=GetWorld()->GetTimeSeconds();
    const float Elapsed=static_cast<float>(FMath::Max(0.,Time-HorseShellLastWorldSeconds));
    HorseShellLastWorldSeconds=Time;
    // The controller and pawn can both call this in one world tick. Charge
    // time once, so a warning created by the controller earns no prior frame.
    if(bHorseShellBound&&CanPlay()) ShellRules::Advance(HorseShellClock,HorseShellMilliseconds.Advance(Elapsed));
}
void ASoraEnemy::TickHorseShell()
{
    auto* Director=HorseShellDirector.Get();
    if(!Director||!Director->HorseShellSession(HorseShellGeneration)) { CancelAttack(); return; }
    const auto* Mode=Cast<ASoraGameMode>(GetWorld()->GetAuthGameMode());
    if(!Mode||!Mode->IsPlaying()||Mode->InputState()==SoraInput::Dialogue) return;
    AdvanceHorseShellClock();
    if(!HorseShellClock.Winding) return;
    auto* Target=HorseShellTarget.Get();
    const auto* Body=Cast<ASoraCharacterBase>(Target);
    if(IsStaggered()||IsTurnLocked()||!IsValid(Target)||Target->IsActorBeingDestroyed()||
       (Body&&!Body->IsAlive())||!ShellWarning.IsValid()||ShellWarning->IsActorBeingDestroyed())
    { CancelAttack(); return; }
    if(!ShellRules::Release(HorseShellClock)) return;
    // Spend before spawning/broadcasting. A callback cannot fire it twice.
    const FSoraEnemyAttack Attack=AttackSet()[0];
    AActor* Warning=ShellWarning.Get(); ShellWarning.Reset(); HorseShellTarget.Reset();
    Phase=EPhase::Idle; AttackIndex=INDEX_NONE;
    if(!LaunchShell(Attack,LockedPoint,Director,HorseShellGeneration,Warning)&&IsValid(Warning)) Warning->Destroy();
}
