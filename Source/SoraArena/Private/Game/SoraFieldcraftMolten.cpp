#include "SoraFieldcraft.h"
#include "Game/SoraFieldcraftLayout.h"
#include "Combat/SoraDamage.h"
#include "SoraCharacterBase.h"
#include "SoraEnemy.h"
#include "SoraGameMode.h"
#include "SoraPlayerCharacter.h"
#include "SoraWorldBuilder.h"
#include "Components/CapsuleComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Materials/MaterialInstanceDynamic.h"

namespace Molten=SoraMoltenRules;
namespace
{
void ChannelColor(UStaticMeshComponent* Surface,const FLinearColor& Color)
{
    if(!IsValid(Surface)) return;
    // Piece creates the one MID. Updating parameters must not allocate four
    // replacement materials each frame for the whole encounter.
    if(auto* Material=Cast<UMaterialInstanceDynamic>(Surface->GetMaterial(0)))
    {
        Material->SetVectorParameterValue(TEXT("BaseColor"),Color);
        Material->SetVectorParameterValue(TEXT("Color"),Color);
    }
}
}
void USoraFieldcraft::StageMolten(const FSoraBeat& Beat)
{
    if(!Beat.Space.Molten.bEnabled) return;
    MoltenSpace=&Beat.Space.Molten;
    // Synchronized warning begins at beat admission (not application uptime).
    for(int32 I=0;I<MoltenSpace->Channels.Num();++I)
    {
        const auto& Strip=MoltenSpace->Channels[I];
        auto* Surface=Piece(FString::Printf(TEXT("CastingChannel%d"),I),SoraFieldcraftLayout::Cube,
            FVector(Strip.Center,1),FVector(Strip.Size.X/100,Strip.Size.Y/100,.02f),FLinearColor(.18f,.06f,.015f));
        Surface->SetMobility(EComponentMobility::Movable);
        MoltenSurfaces.Add(Surface);
        // Owned lights make the warning visible on nearby floor and bodies;
        // no production light or material asset is modified by this beat.
        auto* Light=NewObject<UPointLightComponent>(Props,*FString::Printf(TEXT("CastingGlow%d"),I));
        Props->AddInstanceComponent(Light); Light->SetupAttachment(Props->GetRootComponent());
        Light->SetMobility(EComponentMobility::Movable);
        Light->SetRelativeLocation(FVector(Strip.Center,35));
        Light->SetAttenuationRadius(1500); Light->SetIntensity(0); Light->SetCastShadows(false);
        Light->RegisterComponent(); MoltenLights.Add(Light);
    }
}
void USoraFieldcraft::ClearMolten()
{
    // The owning Props actor removes the nonblocking surfaces in Clear().
    for(auto& Surface:MoltenSurfaces) ChannelColor(Surface,FLinearColor(.045f,.025f,.02f));
    for(auto& Light:MoltenLights) if(IsValid(Light)) Light->SetIntensity(0);
    ++MoltenGeneration;
    MoltenSpace=nullptr; MoltenClockMs=0; MoltenBodies.Reset(); MoltenSurfaces.Reset(); MoltenLights.Reset();
}
int32 USoraFieldcraft::MoltenBurnLeft(const ASoraCharacterBase& Body) const
{
    const auto* State=MoltenBodies.Find(TWeakObjectPtr<ASoraCharacterBase>(const_cast<ASoraCharacterBase*>(&Body)));
    return State?State->Exposure.BurnLeftMs:0;
}
void USoraFieldcraft::TickMolten(int32 DtMs)
{
    if(!MoltenSpace||DtMs<=0) return;
    const auto* Space=MoltenSpace;
    const uint32 Generation=MoltenGeneration;
    struct FPending { TWeakObjectPtr<ASoraCharacterBase> Body; float Damage; };
    TArray<FPending> Pending;
    TSet<TWeakObjectPtr<ASoraCharacterBase>> Seen;
    for(TActorIterator<ASoraCharacterBase> It(GetWorld());It;++It)
    {
        auto* Body=*It; auto* Enemy=Cast<ASoraEnemy>(Body);
        if((Body!=Hero()&&!Enemy)||!Body->IsAlive()) continue;
        Seen.Add(Body);
        const FVector At=Body->GetActorLocation();
        const float Feet=At.Z-Body->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
        // A bridge, jump, fall or flying body above these strips cannot make
        // new floor contact. A previously acquired burn still runs in air.
        const bool Grounded=Body->GetCharacterMovement()->IsMovingOnGround()&&FMath::Abs(Feet)<=8.f;
        auto* Previous=MoltenBodies.Find(Body);
        if(!Previous) MoltenBodies.Add(Body,FMoltenBody{{},At,Grounded});
        auto& State=MoltenBodies.FindChecked(Body);
        Molten::FSpan Spans[Molten::Channels]; int Count=0;
        if(Grounded&&State.bGrounded)
            for(const auto& Strip:Space->Channels)
            {
                const auto Min=Strip.Center-Strip.Size*.5,Max=Strip.Center+Strip.Size*.5;
                Molten::FSpan Span;
                if(Molten::Cross(State.Last.X,State.Last.Y,At.X,At.Y,Min.X,Min.Y,Max.X,Max.Y,DtMs,Span)) Spans[Count++]=Span;
            }
        const auto Kind=!Enemy?Molten::EBody::Player:
            Enemy->ArchetypeId()==TEXT("loom_automaton")?Molten::EBody::Automaton:Molten::EBody::Enemy;
        const auto Result=Molten::Tick(State.Exposure,Kind,MoltenClockMs,DtMs,Spans,Count);
        State.Last=At; State.bGrounded=Grounded;
        if(Result.Destroy||Result.Damage>0) Pending.Add({Body,Result.Destroy?FMath::CeilToFloat(Body->Health):float(Result.Damage)});
    }
    for(auto It=MoltenBodies.CreateIterator();It;++It) if(!Seen.Contains(It.Key())) It.RemoveCurrent();
    MoltenClockMs=int32((int64(MoltenClockMs)+DtMs)%Molten::CycleMs);
    const auto Phase=Molten::Phase(MoltenClockMs);
    const float Ramp=MoltenClockMs/float(Molten::WarningMs);
    const auto Color=Phase==Molten::EPhase::Flow?FLinearColor(1.f,.36f,.025f):Phase==Molten::EPhase::Warning?
        FMath::Lerp(FLinearColor(.18f,.06f,.015f),FLinearColor(1.f,.58f,.045f),Ramp):FLinearColor(.045f,.025f,.02f);
    for(auto& Surface:MoltenSurfaces) ChannelColor(Surface,Color);
    for(auto& Light:MoltenLights) if(IsValid(Light))
    {
        Light->SetLightColor(Color);
        Light->SetIntensity(Phase==Molten::EPhase::Flow?6000.f:Phase==Molten::EPhase::Warning?3500.f*Ramp:0.f);
    }
    // Ordinary TakeDamage -> OnDied/Subdue -> OpponentDefeated grants the
    // registered wave its credit exactly once. Never edit task counters here.
    // A defeat can clear/re-stage this subsystem synchronously: no map refs or
    // pending damage from the old encounter may survive that callback.
    for(const auto& Hit:Pending)
    {
        if(MoltenGeneration!=Generation||MoltenSpace!=Space||!Staged) break;
        auto* Body=Hit.Body.Get(); if(!Body||!Body->IsAlive()) continue;
        const FVector At=Body->GetActorLocation(); FHitResult Trace; Trace.ImpactPoint=At;
        auto Damage=FSoraHit::Hazard(At); Damage.EnvironmentalRate=SoraCombatRules::EEnvironmentalRate::MoltenChannel;
        SoraDamage::Strike(Body,Hit.Damage,Damage,FVector::UpVector,Trace,nullptr,Props);
        if(!Body->IsAlive()) MoltenBodies.Remove(Body);
        if(const auto* Mode=Cast<ASoraGameMode>(GetWorld()->GetAuthGameMode());Mode&&Mode->bDefeated)
        { ClearMolten(); break; }
    }
}
