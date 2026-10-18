#pragma once
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraAutomationWorld.h"
#include "SoraCampaignDirector.h"
#include "SoraCampaignLift.h"
#include "SoraGameMode.h"
#include "SoraPlayerCharacter.h"
#include "SoraWorldBuilder.h"
#include "SoraEnemy.h"
#include "EngineUtils.h"
#include "GameFramework/Controller.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "InputCoreTypes.h"

namespace SoraLiftAutomation
{
// Known clear deck/gallery segments use normal W input and swept capsule
// movement. No floor-Z reset, pawn teleport, task mutation or SetBase call.
inline bool Walk(FSoraAutomationWorld& W,const FVector& Point)
{
    auto* Hero=W.Player();
    for(int32 Frame=0;Frame<1800&&FVector::Dist2D(Hero->GetActorLocation(),Point)>20.f;++Frame)
    {
        const FRotator Facing=(Point-Hero->GetActorLocation()).GetSafeNormal2D().Rotation();
        Hero->GetController()->SetControlRotation(Facing); Hero->FaceRotation(Facing,0.f);
        if(!W.InjectKey(EKeys::W,IE_Pressed)||!W.Tick(1)) return false;
    }
    if(!W.InjectKey(EKeys::W,IE_Released)||!W.Tick(4)) return false;
    return FVector::Dist2D(Hero->GetActorLocation(),Point)<=30.f;
}
inline bool Board(FSoraAutomationWorld& W)
{
    auto* Lift=W.Mode()->Arena()->CampaignLift();
    return Lift&&W.Tick(30)&&Walk(W,Lift->GetActorLocation()+FVector(-180,0,Lift->Height()))&&Lift->Aboard(*W.Player());
}
inline void HoldThreats(FSoraAutomationWorld& W)
{
    // Ride/gallery fixtures isolate traversal. LiftEncounters separately
    // leaves every drone, rifle and boarder live to check their behavior.
    for(TActorIterator<ASoraEnemy> It(W.GetTestWorld());It;++It)
    {
        It->SetActorTickEnabled(false);
        It->GetCharacterMovement()->StopMovementImmediately();
        It->GetCharacterMovement()->SetComponentTickEnabled(false);
        if(auto* Brain=It->GetController()) Brain->SetActorTickEnabled(false);
    }
}
inline bool Ride(FSoraAutomationWorld& W)
{
    auto* Director=W.Mode()->Campaign();
    if(!Board(W)) return false;
    for(int32 Turn=0;Turn<60&&!Director->InLiftGallery();++Turn)
    {
        if(!W.Tick(66)||!W.PressKey(EKeys::E)) return false;
        HoldThreats(W);
    }
    return Director->InLiftGallery()&&W.Mode()->Arena()->CampaignLift()->Arrived();
}
inline bool GalleryFloor(FSoraAutomationWorld& W)
{
    auto* Director=W.Mode()->Campaign();
    auto* Lift=W.Mode()->Arena()->CampaignLift();
    if(!Lift||!Director->InLiftGallery()) return false;
    const FVector Center=Lift->GetActorLocation()+FVector(0,0,Lift->Height());
    // Pass the capstan and the crew, then the 200 cm gate, on foot.
    for(const FVector Offset:{FVector(-180,120,0),FVector(180,120,0),FVector(180,0,0),FVector(500,0,0)})
        if(!Walk(W,Center+Offset)) return false;
    return true;
}
inline bool Gallery(FSoraAutomationWorld& W,bool OpenCache)
{
    auto* Director=W.Mode()->Campaign();
    auto* Lift=W.Mode()->Arena()->CampaignLift();
    if(!GalleryFloor(W)) return false;
    if(OpenCache)
        if(!Walk(W,Lift->GalleryCache()+FVector(-150,0,0))||!W.PressKey(EKeys::E)) return false;
    const FVector Exit=Lift->GalleryExit();
    // Stop after the ordinary exit volume takes over with its travel cut.
    for(int32 Frame=0;Frame<1800&&Director->InLiftGallery();++Frame)
    {
        auto* Hero=W.Player();
        const FRotator Facing=(Exit-Hero->GetActorLocation()).GetSafeNormal2D().Rotation();
        Hero->GetController()->SetControlRotation(Facing); Hero->FaceRotation(Facing,0.f);
        if(!W.InjectKey(EKeys::W,IE_Pressed)||!W.Tick(1)) return false;
    }
    return W.InjectKey(EKeys::W,IE_Released)&&W.Tick(1)&&Director->ActiveBeat()==12;
}
}
#endif
