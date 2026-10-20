#include "SoraBoss.h"
#include "SoraSummitRules.h"
#include "Combat/SoraBossCatalog.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"

bool ASoraBoss::CanRespawnAddGroup(int32 Group) const
{
    // The summit's constructs belong to its seizure phase. Other bosses
    // retain their existing encounter-wide add/respawn contracts.
    const auto* Phase=CurrentPhase();
    return !Setup.bSummit||(Phase&&Phase->ShieldWhileAdds==Group);
}
bool ASoraBoss::IsSummitSeizureShielded() const
{
    const auto* Phase=CurrentPhase();
    return Setup.bSummit&&Phase&&Phase->ShieldWhileAdds!=INDEX_NONE&&LiveAdds(Phase->ShieldWhileAdds)>0;
}
bool ASoraBoss::IsOnSummitDais() const
{
    if(!Setup.bSummit||!GetCharacterMovement()->IsMovingOnGround()) return false;
    const FVector Here=GetActorLocation();
    const double Feet=Here.Z-GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    return FVector::Dist2D(Here,Setup.SummitDaisFloor)<=20&&FMath::Abs(Feet-Setup.SummitDaisFloor.Z)<10;
}
bool ASoraBoss::DriveSummit(FSoraBossIntent& Intent,const ASoraCharacterBase& Target) const
{
    if(!Setup.bSummit) return false;
    const bool Retreat=PhaseNow==1&&Run.Attack==INDEX_NONE&&!IsOnSummitDais();
    if(!bSummitTransition&&!Retreat) return false;
    const FVector Here=GetActorLocation();
    Intent.bMove=Retreat;
    Intent.Goal=Setup.SummitDaisFloor+FVector(0,0,GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+2);
    Intent.AcceptanceCm=10;
    Intent.bFace=true;
    Intent.Facing=(Retreat?Intent.Goal:Target.GetActorLocation())-Here;
    Intent.TurnDegreesPerSecond=Info->Phases[PhaseNow].TurnDegreesPerSecond;
    return true;
}
bool ASoraBoss::TickSummitTransition()
{
    if(!bSummitTransition) return false;
    const int32 Now=NowMs();
    if(!SoraSummitRules::PhaseTransitionReady(PhaseNow,Now-PhaseStartedMs,IsOnSummitDais())) return true;
    bSummitTransition=false;
    // A retreat longer than its minimum blend never lets expired timers
    // dump attacks at arrival. Concurrent work starts from this boundary.
    const auto& Current=Info->Phases[PhaseNow];
    for(int32 N=0;N<Current.Concurrent.Num();++N) TimedDueMs[N]=Now+Current.Concurrent[N].FirstMs;
    NextStartMs=Now;
    return false;
}
