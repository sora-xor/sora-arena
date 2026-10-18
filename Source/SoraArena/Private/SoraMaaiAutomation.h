#pragma once
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraAutomationWorld.h"
#include "SoraCampaignDirector.h"
#include "SoraEnemy.h"
#include "SoraGameMode.h"
#include "SoraPlayerCharacter.h"
#include "GameFramework/Controller.h"

namespace SoraMaaiAutomation
{
// Real movement keys and view rotation only: no teleport, task-state write,
// synthetic gate event or defeated mentor can satisfy this lesson.
inline bool Steer(FSoraAutomationWorld& World)
{
    USoraCampaignDirector* Campaign=World.Mode()->Campaign();
    ASoraPlayerCharacter* Hero=World.Player();
    ASoraEnemy* Mentor=Campaign->MaaiMentor();
    if(!Hero||!Mentor||!Hero->GetController()) return false;
    const FRotator Facing=(Mentor->GetActorLocation()-Hero->GetActorLocation()).GetSafeNormal2D().Rotation();
    Hero->GetController()->SetControlRotation(Facing);
    // Headless worlds have no viewport to call UpdateRotation/FaceRotation.
    Hero->FaceRotation(Facing,0.f);
    const float Distance=Campaign->MaaiDistance();
    return World.InjectKey(EKeys::W,Distance>205.f?IE_Pressed:IE_Released)&&
        World.InjectKey(EKeys::S,Distance<185.f?IE_Pressed:IE_Released);
}
inline bool Walk(FSoraAutomationWorld& World,int32 Steps=3)
{
    USoraCampaignDirector* Campaign=World.Mode()->Campaign();
    int32 Frames=0;
    for(;Frames<1800&&Campaign->IsMaaiLesson()&&Campaign->TaskProgress().Maai.Done<Steps;++Frames)
        if(!Steer(World)||!World.Tick(1)) return false;
    const bool bReleased=World.InjectKey(EKeys::W,IE_Released)&&World.InjectKey(EKeys::S,IE_Released);
    return bReleased&&Frames<1800&&(!Campaign->IsMaaiLesson()||Campaign->TaskProgress().Maai.Done>=Steps);
}
}
#endif
