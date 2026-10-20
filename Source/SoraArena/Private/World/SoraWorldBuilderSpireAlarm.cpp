#include "SoraWorldBuilder.h"
#include "SoraEnemy.h"
#include "SoraGameMode.h"
#include "Combat/SoraEnemyCatalog.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"

void ASoraWorldBuilder::ResetSpireAlarm(bool Active)
{
    bSpireActive=Active&&SpireShutter;
    bSpireClosed=false; bSpireAlarmPending=false;
    if(SpireShutter)
    {
        SpireShutter->SetVisibility(false);
        SpireShutter->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    }
    for(UStaticMeshComponent* Panel:SpirePanels) if(Panel) Tint(Panel,FLinearColor(.12f,.35f,.40f));
}

bool ASoraWorldBuilder::SpireAlarmGoal(const ASoraEnemy& Auditor,FVector& Out) const
{
    if(!bSpireActive||SpirePanelGoals.IsEmpty()||!Auditor.IsAlive()||!Auditor.Archetype()||
        Auditor.Archetype()->Behavior!=ESoraEnemyBehavior::Auditor) return false;
    // Keep a runner's destination stable while it winds around the shaft;
    // nearest-XY selection would alternate panels on each half-turn.
    Out=SpirePanelGoals[FMath::Abs(Auditor.EnemySlot())%SpirePanelGoals.Num()];
    return true;
}

bool ASoraWorldBuilder::TrySpireAlarm(const ASoraEnemy& Auditor)
{
    FVector Goal;
    if(bSpireClosed||bSpireAlarmPending||!SpireAlarmGoal(Auditor,Goal)||
        !Auditor.GetCharacterMovement()->IsMovingOnGround()) return false;
    const FVector Here=Auditor.GetActorLocation();
    const float Feet=Here.Z-Auditor.GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    if(FVector::Dist2D(Here,Goal)>60||FMath::Abs(Feet-Goal.Z)>20) return false;
    bSpireAlarmPending=true;
    for(UStaticMeshComponent* Panel:SpirePanels) if(Panel) Tint(Panel,FLinearColor(.9f,.23f,.04f));
    TickSpireAlarm();
    return true;
}

void ASoraWorldBuilder::TickSpireAlarm()
{
    const auto* Mode=GetWorld()?GetWorld()->GetAuthGameMode<ASoraGameMode>():nullptr;
    if(!bSpireActive||!bSpireAlarmPending||bSpireClosed||!SpireShutter||!Mode||!Mode->IsPlaying()) return;
    // Query the complete future door plus clearance. An occupied doorway
    // remains open until every pawn leaves, including a companion or enemy.
    const FCollisionObjectQueryParams Pawns(ECC_Pawn);
    const FCollisionQueryParams Query(SCENE_QUERY_STAT(SpireShutterClear),false,this);
    if(GetWorld()->OverlapAnyTestByObjectType(SpireShutterAt,SpireShutterRotation.Quaternion(),Pawns,
        FCollisionShape::MakeBox(FVector(30,120,190)),Query)) return;
    SpireShutter->SetVisibility(true);
    SpireShutter->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
    bSpireClosed=true; bSpireAlarmPending=false;
}
