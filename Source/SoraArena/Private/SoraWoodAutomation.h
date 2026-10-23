#pragma once
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraLiftAutomation.h"
#include "SoraEquipmentComponent.h"
#include "SoraProjectile.h"
#include "Camera/CameraComponent.h"
#include "SoraWoodRules.h"

namespace SoraWoodAutomation
{
inline bool Walk(FSoraAutomationWorld& W,const FVector2D& Target)
{
    const FVector2D Start(W.Player()->GetActorLocation());
    const int32 Steps=FMath::Max(1,FMath::CeilToInt((Target-Start).Size()/1000));
    for(int32 I=1;I<=Steps;++I)
        if(!SoraLiftAutomation::Walk(W,FVector(FMath::Lerp(Start,Target,double(I)/Steps),0))) return false;
    return true;
}
inline bool Path(FSoraAutomationWorld& W,const TArray<FVector2D>& Points)
{
    for(const auto& P:Points) if(!Walk(W,P)) return false;
    return true;
}
inline bool Terrace(FSoraAutomationWorld& W)
{
    auto* C=W.Mode()->Campaign(); const auto& Wood=C->ActiveChapter()->Wood;
    return C->IsWoodTransit()&&Walk(W,Wood.Approach[0])&&Walk(W,Wood.Approach[1])&&Path(W,Wood.Terrace)&&C->ActiveBeat()==8;
}
inline bool Enter(FSoraAutomationWorld& W)
{
    auto* C=W.Mode()->Campaign();
    return C->IsWoodTransit()&&Path(W,C->ActiveChapter()->Wood.Approach)&&C->IsWoodExplore();
}
inline bool Poi(FSoraAutomationWorld& W,int32 Index)
{
    auto* C=W.Mode()->Campaign();
    const FVector2D At=C->ActiveChapter()->Wood.Pois[Index];
    if(!Walk(W,At+FVector2D(-130,0))||!W.Tick(240)) return false;
    return W.PressKey(EKeys::E)&&W.Tick(1)&&(C->WoodPoiMask()&SoraWoodRules::Bit(Index))!=0;
}
inline bool Exit(FSoraAutomationWorld& W)
{
    auto* C=W.Mode()->Campaign(); const auto& Wood=C->ActiveChapter()->Wood;
    return Path(W,Wood.Trail)&&C->IsWoodTransit()&&Path(W,Wood.Bridge)&&C->ActiveBeat()==8;
}
inline bool Explore(FSoraAutomationWorld& W)
{
    return Enter(W)&&Poi(W,SoraWoodRules::Stone)&&Poi(W,SoraWoodRules::Boundary)&&Exit(W);
}
inline bool Arrow(FAutomationTestBase& Test,FSoraAutomationWorld& W,bool HitTarget=true,bool AtVista=true)
{
    auto* C=W.Mode()->Campaign(); auto* Hero=W.Player(); auto* Kit=Hero->GetEquipment();
    const auto& Wood=C->ActiveChapter()->Wood;
    if((AtVista&&!Walk(W,Wood.Pois[SoraWoodRules::Vista]))||!W.Tick(240)||!W.PressKey(EKeys::Three)||!W.Tick(70)) return false;
    const int32 Before=Kit->Ammo;
    const bool ExpectIssued=AtVista&&!C->HasToshiyaCodex();
    if(!W.InjectKey(EKeys::LeftMouseButton,IE_Pressed)||!W.Tick(42)||!Kit->IsBowDrawing()) return false;
    const FVector Eye=Hero->GetCamera()->GetComponentLocation();
    FVector Origin=Eye; float Time=4500.f/6500.f; FRotator Aim;
    for(int32 Pass=0;Pass<8;++Pass)
    {
        const FVector At=Wood.Naruko+FVector(HitTarget?0:300,0,0);
        Aim=(At+FVector(0,0,.5f*980.f*Time*(Time+1.f/60.f))-Origin).Rotation();
        Origin=Eye+Aim.Vector()*65.f;
        Time=FVector::Dist2D(At,Origin)/(6500.f*FMath::Cos(FMath::DegreesToRadians(Aim.Pitch)));
    }
    Hero->GetController()->SetControlRotation(Aim); Hero->FaceRotation(Aim,0);
    Hero->GetCamera()->SetWorldRotation(Aim);
    if(!W.InjectKey(EKeys::LeftMouseButton,IE_Released)) return false;
    if(!Test.TestEqual(TEXT("Naruko attempt spends a real released arrow"),Kit->Ammo,Before-1)) return false;
    bool Issued=false;
    for(TActorIterator<ASoraProjectile> It(W.GetTestWorld());It;++It)
        if(It->GetOwner()==Hero&&It->WoodShotId) Issued=true;
    if(!Test.TestEqual(TEXT("Arrow is issued only from the physical vista"),Issued,ExpectIssued)) return false;
    return W.Tick(150);
}
}
#endif
