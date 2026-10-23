#include "SoraLeadRopeComponent.h"
#include "SoraLeadRopeRules.h"
#include "SoraWorldBuilder.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"

USoraLeadRopeComponent::USoraLeadRopeComponent()
{
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.bStartWithTickEnabled=false;
    // Read both actors after movement and head/body animation. Do not add
    // prerequisites to, or change the tick group of, either gameplay actor.
    PrimaryComponentTick.TickGroup=TG_PostUpdateWork;
}
void USoraLeadRopeComponent::AttachLead(USceneComponent* Halter,USceneComponent* Tie,float NominalLengthCm)
{
    ClearLead();
    if(!IsValid(Halter)||!IsValid(Tie)||Halter==Tie||!FMath::IsFinite(NominalLengthCm)||NominalLengthCm<=0) return;
    HalterAnchor=Halter; TieAnchor=Tie; LengthCm=NominalLengthCm;
    for(int32 N=0;N<SoraLeadRopeRules::Segments;++N)
    {
        auto* Mesh=ASoraWorldBuilder::Shape(GetOwner(),GetOwner()->GetRootComponent(),
            FString::Printf(TEXT("LeadRope%d"),N),TEXT("/Engine/BasicShapes/Cylinder.Cylinder"),
            FVector::ZeroVector,FVector::OneVector,FLinearColor(.55f,.45f,.3f));
        Mesh->SetAbsolute(true,true,true);
        Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Mesh->SetGenerateOverlapEvents(false);
        Mesh->SetCastShadow(true);
        Segments.Add(Mesh);
    }
    SetComponentTickEnabled(true);
    UpdateLead();
}
void USoraLeadRopeComponent::ClearLead()
{
    SetComponentTickEnabled(false);
    for(const auto& Mesh:Segments) if(Mesh) Mesh->DestroyComponent();
    Segments.Reset(); HalterAnchor.Reset(); TieAnchor.Reset(); LengthCm=0;
}
void USoraLeadRopeComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    ClearLead();
    Super::EndPlay(Reason);
}
bool USoraLeadRopeComponent::Anchors(FVector& Halter,FVector& Tie) const
{
    if(!HalterAnchor.IsValid()||!TieAnchor.IsValid()||
        !IsValid(HalterAnchor->GetOwner())||!IsValid(TieAnchor->GetOwner())||
        HalterAnchor->GetOwner()->IsActorBeingDestroyed()||TieAnchor->GetOwner()->IsActorBeingDestroyed()) return false;
    Halter=HalterAnchor->GetComponentLocation(); Tie=TieAnchor->GetComponentLocation();
    return true;
}
void USoraLeadRopeComponent::UpdateLead()
{
    FVector Start,End;
    if(!Anchors(Start,End)) { ClearLead(); return; }
    const auto Line=SoraLeadRopeRules::Curve({Start.X,Start.Y,Start.Z},{End.X,End.Y,End.Z},LengthCm);
    for(int32 N=0;N<Segments.Num();++N)
    {
        auto* Mesh=Segments[N].Get();
        Mesh->SetVisibility(Line.Visible);
        if(!Line.Visible) continue;
        const auto& A=Line.Points[N]; const auto& B=Line.Points[N+1];
        const FVector From(A.X,A.Y,A.Z),To(B.X,B.Y,B.Z),Span=To-From;
        if(Span.IsNearlyZero()) { Mesh->SetVisibility(false); continue; }
        Mesh->SetWorldLocationAndRotation((From+To)*.5,FQuat::FindBetweenNormals(FVector::UpVector,Span.GetSafeNormal()));
        Mesh->SetWorldScale3D(FVector(.015,.015,Span.Size()/100.f));
    }
}
void USoraLeadRopeComponent::TickComponent(float DeltaTime,ELevelTick TickType,FActorComponentTickFunction* ThisTickFunction)
{
    Super::TickComponent(DeltaTime,TickType,ThisTickFunction);
    UpdateLead();
}
bool USoraLeadRopeComponent::RenderedEndpoints(FVector& Halter,FVector& Tie) const
{
    if(Segments.IsEmpty()||!Segments[0]||!Segments.Last()||!Segments[0]->IsVisible()||!Segments.Last()->IsVisible()) return false;
    // Inspect actual component transforms, not cached desired endpoints.
    Halter=Segments[0]->GetComponentTransform().TransformPosition(FVector(0,0,-50));
    Tie=Segments.Last()->GetComponentTransform().TransformPosition(FVector(0,0,50));
    return true;
}
int32 USoraLeadRopeComponent::VisibleSegments() const
{
    int32 Count=0;
    for(const auto& Mesh:Segments) if(Mesh&&Mesh->IsVisible()) ++Count;
    return Count;
}
bool USoraLeadRopeComponent::HasCollision() const
{
    for(const auto& Mesh:Segments) if(Mesh&&Mesh->GetCollisionEnabled()!=ECollisionEnabled::NoCollision) return true;
    return false;
}
