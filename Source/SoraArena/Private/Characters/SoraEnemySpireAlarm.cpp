#include "SoraEnemyController.h"
#include "SoraEnemy.h"
#include "SoraGameEvents.h"
#include "SoraGameMode.h"
#include "SoraWorldBuilder.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"

bool ASoraEnemyController::DriveSpireAlarm(ASoraEnemy& Enemy,float Dt,int32 NowMs)
{
    auto* Mode=GetWorld()?GetWorld()->GetAuthGameMode<ASoraGameMode>():nullptr;
    auto* Arena=Mode?Mode->Arena():nullptr;
    FVector Goal;
    if(!bHunting||!Arena||!Arena->SpireAlarmGoal(Enemy,Goal)) return false;
    // The spire errand takes priority over combat searching. Ordinary ch06
    // guards still use AlarmRun and the stealth zone's lecterns unchanged.
    WalkTo(Enemy,Goal,.75f,30.f,NowMs);
    Face(Enemy,Heading,Dt,5.f);
    if(Arena->TrySpireAlarm(Enemy))
    {
        if(auto* Bus=USoraGameEvents::Get(this))
        {
            FSoraEnemyCueEvent Event;
            Event.Enemy=&Enemy; Event.Archetype=Enemy.ArchetypeId();
            Event.Cue=ESoraEnemyCue::Alarm; Event.Detail=TEXT("spire_panel");
            Bus->OnEnemyCue.Broadcast(Event);
        }
    }
    return true;
}
