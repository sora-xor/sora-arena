#pragma once
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraArcheryTarget.h"
#include "SoraAutomationWorld.h"
#include "SoraCampaignDirector.h"
#include "SoraEquipmentComponent.h"
#include "SoraGameMode.h"
#include "SoraLiftAutomation.h"
#include "SoraPlayerCharacter.h"
#include "SoraProjectile.h"
#include "Camera/CameraComponent.h"
#include "EngineUtils.h"
#include "GameFramework/Controller.h"
#include "Misc/AutomationTest.h"

// Real normal-rate movement/equip/draw/release. No score, task, ammo or actor
// transform writes. Shared with the aggregate playthrough after integration.
namespace SoraArcheryAutomation
{
inline void Look(FSoraAutomationWorld& W,const FRotator& Rotation)
{
    auto* Hero=W.Player();
    Hero->GetController()->SetControlRotation(Rotation); Hero->FaceRotation(Rotation,0.f);
    // Test worlds have no local camera manager; mirror its view rotation.
    Hero->GetCamera()->SetWorldRotation(Rotation);
}
inline bool EnterLine(FSoraAutomationWorld& W,const FKey& Bow=EKeys::Three)
{
    auto* C=W.Mode()->Campaign();
    const FVector Line=C->ArcheryLine();
    // Walk around the actual instructor capsules, not through their center.
    if(!W.Tick(30)||!SoraLiftAutomation::Walk(W,FVector(W.Player()->GetActorLocation().X,Line.Y-350,Line.Z))||
        !SoraLiftAutomation::Walk(W,Line+FVector(0,-350,0))||!SoraLiftAutomation::Walk(W,Line)||
        !W.PressKey(Bow)||!W.Tick(20)) return false;
    return C->AtArcheryLine()&&W.Player()->WeaponId==18;
}
inline bool Loose(FAutomationTestBase& Test,FSoraAutomationWorld& W,int32 TargetIndex,
    const FKey& Fire=EKeys::LeftMouseButton)
{
    auto* C=W.Mode()->Campaign(); auto* Hero=W.Player(); auto* Kit=Hero->GetEquipment();
    // The catalog keeps 1.1 s recovery after release. Wait it in real world
    // frames before asking to begin another 650 ms draw.
    if(!C->IsArcheryLesson()||!W.Tick(70)) return false;
    const int32 Before=Kit->Ammo;
    if(!W.InjectKey(Fire,IE_Pressed)||!W.Tick(42)||
        !Test.TestTrue(TEXT("Mapped Attack establishes a complete real yumi draw"),Kit->IsBowDrawing()&&Kit->BowDrawProgress()>=1.f))
        return false;
    FRotator Aim(75,0,0); // A deliberate flight-expiry miss, above all walls.
    if(auto* Target=C->ArcheryTarget(TargetIndex))
    {
        // Lead the independently moving target and compensate the projectile's
        // actual semi-implicit gravity integration, at normal 60 Hz.
        const FVector Eye=Hero->GetCamera()->GetComponentLocation();
        FVector Origin=Eye;
        float Time=FVector::Dist2D(Target->GetActorLocation(),Eye)/6500.f;
        for(int32 Pass=0;Pass<8;++Pass)
        {
            const FVector At=Target->CenterAt(C->ArcheryClockMs()+FMath::RoundToInt32(Time*1000));
            const FVector Compensated=At+FVector(0,0,.5f*980.f*Time*(Time+1.f/60.f));
            Aim=(Compensated-Origin).Rotation();
            Origin=Eye+Aim.Vector()*65.f;
            Time=FVector::Dist2D(At,Origin)/(6500.f*FMath::Cos(FMath::DegreesToRadians(Aim.Pitch)));
        }
    }
    Look(W,Aim);
    if(!W.InjectKey(Fire,IE_Released)) return false;
    if(!Test.TestEqual(TEXT("Only an actual full release spends one arrow"),Kit->Ammo,Before-1)) return false;
    TWeakObjectPtr<ASoraProjectile> Flight;
    for(TActorIterator<ASoraProjectile> It(W.GetTestWorld());It;++It)
        if(It->GetOwner()==Hero&&It->ArcheryShotId) Flight=*It;
    if(!Test.TestTrue(TEXT("The released arrow has a unique live resolution identity"),Flight.IsValid())) return false;
    const auto Id=Flight->ArcheryShotId;
    const FVector Origin=Flight->GetActorLocation();
    FVector Last=Origin;
    for(int32 Frame=0;Frame<180&&Flight.IsValid()&&!Flight->IsActorBeingDestroyed();++Frame)
    {
        Last=Flight->GetActorLocation();
        if(!W.Tick(1)) return false;
    }
    const bool Resolved=!Flight.IsValid()||Flight->IsActorBeingDestroyed()||Flight->ArcheryShotId==0;
    if(!Resolved)
        Test.AddError(FString::Printf(TEXT("Unresolved arrow id=%llu target=%d origin=%s now=%s velocity=%s stage=%d issued=%d resolved=%d"),
            Id,TargetIndex,*Origin.ToString(),*Flight->GetActorLocation().ToString(),*Flight->Velocity.ToString(),
            int32(C->ArcheryProgress().Stage),C->ArcheryProgress().Issued,C->ArcheryProgress().Resolved));
    if(!W.Tick(1)) return false;
    UE_LOG(LogTemp,Display,TEXT("Archery actual shot id=%llu aimed_target=%d origin=%s last_flight=%s hero=%s beat=%d stage=%d issued=%d resolved=%d hits=%d hanging=%u ammo=%d"),
        Id,TargetIndex,*Origin.ToString(),*Last.ToString(),*Hero->GetActorLocation().ToString(),C->ActiveBeat(),
        int32(C->ArcheryProgress().Stage),C->ArcheryProgress().Issued,C->ArcheryProgress().Resolved,C->ArcheryProgress().Hits,
        C->ArcheryProgress().HangingHits,Kit->Ammo);
    return Test.TestTrue(TEXT("The actual projectile resolves once through impact or flight expiry"),Resolved);
}
inline bool Complete(FAutomationTestBase& Test,FSoraAutomationWorld& W)
{
    auto* C=W.Mode()->Campaign();
    if(!EnterLine(W)) return Test.TestTrue(TEXT("Normal walking and key 3 reach the archery line with the yumi"),false);
    for(int32 Shot=0;Shot<6;++Shot)
        if(!Loose(Test,W,0)||!Test.TestEqual(TEXT("Each aimed near arrow really hits"),C->ArcheryProgress().LastHit,true)) return false;
    if(!Test.TestTrue(TEXT("Six resolved near shots open the hanging targets"),C->ArcheryProgress().Stage==SoraArcheryRules::EStage::Hanging)) return false;
    for(int32 Target=1;Target<=3;++Target)
        if(!Loose(Test,W,Target)) return false;
    return Test.TestEqual(TEXT("Three real hanging impacts complete b07"),C->ActiveBeat(),8);
}
}
#endif
