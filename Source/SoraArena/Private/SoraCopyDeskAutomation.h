#pragma once
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraRecoveryAutomation.h"
#include "SoraCatalog.h"
#include "SoraEnemy.h"
#include "Combat/SoraStealth.h"

namespace SoraCopyDeskAutomation
{
inline bool Copy(FSoraAutomationWorld& World,int32 Point)
{
    auto* Campaign=World.Mode()->Campaign();
    const auto* Space=Campaign->ActiveSpace();
    if(!Space||!Space->Objectives.IsValidIndex(Point)||Campaign->ActiveTask().HoldPointCount<=Point) return false;
    const int32 Beat=Campaign->ActiveBeat();
    const FVector Target(Space->Objectives[Point],Space->FloorAt(Space->Objectives[Point]));
    const FVector From=World.Player()->GetActorLocation();
    const auto Walk=[&](const FVector& To)
    {
        // FindPath requires a route with two points; there is no route to
        // request when this intermediate waypoint is already under the hero.
        return FVector::Dist2D(World.Player()->GetActorLocation(),To)<=30.f||SoraRecoveryAutomation::WalkTo(World,To);
    };
    bool Approached=false;
    if(Space->RegistryHall.bEnabled)
    {
        const FVector2D O=Space->RegistryHall.Origin;
        // Enter through the east doorway, then use the level south corridor.
        // The final approach walks up the physical 15/30 cm steps.
        const bool Entered=From.X<O.X+2200||Walk(FVector(O+FVector2D(2000,2500),0));
        Approached=Entered&&Walk(FVector(World.Player()->GetActorLocation().X,O.Y+2320,0))&&
            Walk(FVector(Target.X,O.Y+2320,0))&&Walk(Target);
    }
    else
    {
        const double AisleX=FMath::Min(From.X,Target.X-350.);
        Approached=Walk(FVector(AisleX,From.Y,Target.Z))&&Walk(FVector(AisleX,Target.Y,Target.Z))&&Walk(Target);
    }
    if(!Approached)
    {
        UE_LOG(LogTemp,Error,TEXT("Copy desk %d approach failed: from=%s at=%s target=%s input=%d movement=%d"),Point,
            *From.ToString(),*World.Player()->GetActorLocation().ToString(),*Target.ToString(),int32(World.Mode()->InputState()),
            int32(World.Player()->GetCharacterMovement()->MovementMode));
        return false;
    }
    FKey Use;
    for(const FKey& Key:World.Player()->GetActionKeys(TEXT("Interact"))) if(!Key.IsGamepadKey()) { Use=Key;break; }
    if(!Use.IsValid()) return false;
    // Interact beside a fallen auditor first takes hold of the body. The
    // assisted campaign defeats guards at their desks, so clear that body
    // through the ordinary drag input before attempting to write a copy.
    // Never remove it, disable its interaction, or fill work while dragging.
    auto* Stealth=USoraStealth::Get(World.Player());
    for(int32 Attempt=0;Stealth&&Stealth->DragTarget(*World.Player())&&Attempt<16;++Attempt)
    {
        auto* Body=Stealth->DragTarget(*World.Player());
        const FVector Before=Body->GetActorLocation();
        const int32 WorkBefore=Campaign->TaskProgress().HoldProgress[Point];
        if(!World.InjectKey(Use,IE_Pressed)||!World.Tick(1)) return false;
        if(!Stealth->IsDragging()||Campaign->IsCopying()) { World.InjectKey(Use,IE_Released);return false; }
        const FVector Drop=Space->RegistryHall.bEnabled
            ?FVector(Target.X,Space->RegistryHall.Origin.Y+2320,0):Target-FVector(0,450,0);
        const bool Moved=Walk(Drop);
        if(!World.InjectKey(Use,IE_Released)||!World.Tick(1)||!Moved||Stealth->IsDragging()||
            Campaign->TaskProgress().HoldProgress[Point]!=WorkBefore||
            FVector::Dist2D(Body->GetActorLocation(),Target)<=SoraStealthRules::DragReachCm) return false;
        UE_LOG(LogTemp,Display,TEXT("Copy desk %d cleared a fallen guard through held drag: body=%s from=%s to=%s copy_progress=%d"),
            Point,*Body->GetName(),*Before.ToString(),*Body->GetActorLocation().ToString(),WorkBefore);
        if(!Walk(Target)) return false;
    }
    if((Stealth&&Stealth->DragTarget(*World.Player()))||!World.InjectKey(Use,IE_Pressed)) return false;
    bool Ok=true;
    for(int Frame=0;Frame<3900&&Campaign->ActiveBeat()==Beat&&
        Campaign->TaskProgress().HoldProgress[Point]<Campaign->ActiveTask().HoldPointMs;++Frame)
        if(!World.Tick(1)) { Ok=false;break; }
    const bool Finished=Campaign->ActiveBeat()!=Beat||
        Campaign->TaskProgress().HoldProgress[Point]==Campaign->ActiveTask().HoldPointMs;
    if(!Finished)
        UE_LOG(LogTemp,Error,TEXT("Copy desk %d hold unfinished: progress=%d need=%d copying=%d held=%d watched=%d at=%s input=%d movement=%d dragging=%d"),
            Point,Campaign->TaskProgress().HoldProgress[Point],Campaign->ActiveTask().HoldPointMs,Campaign->IsCopying(),
            World.Player()->IsActionHeld(TEXT("Interact")),Campaign->IsHeldWorkWatched(),*World.Player()->GetActorLocation().ToString(),
            int32(World.Mode()->InputState()),int32(World.Player()->GetCharacterMovement()->MovementMode),Stealth&&Stealth->IsDragging());
    return World.InjectKey(Use,IE_Released)&&World.Tick(1)&&Ok&&Finished;
}
}
#endif
