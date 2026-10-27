#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraCharacterBase.h"
#include "SoraGameMode.h"
#include "SoraHorse.h"
#include "SoraWorldBuilder.h"
#include "Combat/SoraDamage.h"
#include "Components/CapsuleComponent.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"

namespace Pod=SoraPodRules;
void USoraCampaignDirector::EndPlay(const EEndPlayReason::Type Reason)
{
    ResetArchiveReveal(); ResetPods(); Super::EndPlay(Reason);
}
void USoraCampaignDirector::ResetPods()
{
    ++PodGeneration; PodQueued=0;
    const auto Warnings=MoveTemp(PodWarnings); PodWarnings.Reset();
    for(int I=0;I<Pod::Count;++I) { PodState[I]={}; PodClocks[I].Reset(); }
    ResetHorseWithdrawal();
    ResetHorseShells();
    // All old state is detached before Destroy can reenter and start a new session.
    for(const auto& Warning:Warnings) if(IsValid(Warning)) Warning->Destroy();
}
void USoraCampaignDirector::ActivatePod(int32 Wave)
{
    const auto* Space=ActiveSpace();
    if(!Space||!Space->PodArrivals.IsValidIndex(Wave)||PodState[Wave].Active||PodState[Wave].Impacted||!GetWorld()) return;
    // A failed warning cannot silently release a wave without its full warning.
    FActorSpawnParameters Params; Params.Owner=GetOwner();
    auto* Warning=GetWorld()->SpawnActor<AActor>(Params);
    if(!Warning) { UE_LOG(LogTemp,Error,TEXT("SORA pod %d: warning actor could not spawn"),Wave); return; }
    auto* Root=NewObject<USceneComponent>(Warning,TEXT("PodWarningRoot"));
    Warning->SetRootComponent(Root); Root->RegisterComponent(); Warning->AddInstanceComponent(Root);
    Warning->SetActorLocation(Space->PodArrivals[Wave].Floor); Warning->Tags.Add(TEXT("SoraPodWarning"));
    constexpr int Segments=48;
    for(int Segment=0;Segment<Segments;++Segment)
    {
        const float Angle=2.f*PI*Segment/Segments;
        auto* Mark=ASoraWorldBuilder::Shape(Warning,Root,TEXT("AmberPodRing"),TEXT("/Engine/BasicShapes/Cube.Cube"),
            FVector(FMath::Cos(Angle)*Pod::RadiusCm,FMath::Sin(Angle)*Pod::RadiusCm,6),
            FVector(.09f,.48f,.04f),FLinearColor(1.f,.43f,.025f));
        if(!Mark||!Mark->GetStaticMesh())
        {
            Warning->Destroy();
            UE_LOG(LogTemp,Error,TEXT("SORA pod %d: warning mesh unavailable"),Wave);
            return;
        }
        Mark->SetRelativeRotation(FRotator(0,FMath::RadiansToDegrees(Angle),0));
        Mark->SetCollisionEnabled(ECollisionEnabled::NoCollision); Mark->SetCastShadow(false);
    }
    if(PodWarnings.Num()!=Pod::Count) PodWarnings.SetNum(Pod::Count);
    PodWarnings[Wave]=Warning;
    PodClocks[Wave].Reset(); Pod::Begin(PodState[Wave]);
    // First-launch tutorial and repeatable bark share the real activation event.
    Fire(TEXT("ai:drop_pod_launch"));
}
void USoraCampaignDirector::TickPods(float DeltaSeconds)
{
    const auto* Beat=ActiveBeatData();
    if(!Beat||Beat->Space.PodArrivals.IsEmpty()) return;
    const uint64 Generation=PodGeneration;
    for(int Wave=0;Wave<Pod::Count;++Wave)
    {
        if(!(PodQueued&(1u<<Wave))||PodState[Wave].Impacted) continue;
        if(!PodState[Wave].Active)
        {
            ActivatePod(Wave);
            if(PodGeneration!=Generation||ActiveBeatData()!=Beat||Mode().bDefeated) return;
            continue; // Never charge the frame preceding actual warning activation.
        }
        if(!IsValid(PodWarnings[Wave])||PodWarnings[Wave]->IsActorBeingDestroyed())
        {
            // External warning removal must earn a new complete visible warning.
            PodState[Wave]={}; PodClocks[Wave].Reset();
            continue;
        }
        if(Pod::Tick(PodState[Wave],PodClocks[Wave].Advance(DeltaSeconds)))
            if(!ImpactPod(Wave)) return;
    }
}
bool USoraCampaignDirector::ImpactPod(int32 Wave)
{
    const auto* Beat=ActiveBeatData(); const uint64 Generation=PodGeneration;
    const FVector At=Beat->Space.PodArrivals[Wave].Floor;
    TWeakObjectPtr<AActor> Warning=PodWarnings[Wave];
    const auto Current=[&] { return PodGeneration==Generation&&ActiveBeatData()==Beat&&!Mode().bDefeated&&
        IsValid(GetOwner())&&!GetOwner()->IsActorBeingDestroyed()&&Warning.IsValid()&&!Warning->IsActorBeingDestroyed(); };
    // Foot-center cylinder, inclusive edge and [-20,+80] cm floor band. This
    // ground impact ignores horizontal cover and faction; ordinary Hazard
    // admission, invulnerability, nonlethal defeat and vulnerability still apply.
    TArray<TWeakObjectPtr<ASoraCharacterBase>> Victims;
    for(TActorIterator<ASoraCharacterBase> It(GetWorld());It;++It)
    {
        if(!It->IsAlive()||It->IsActorBeingDestroyed()) continue;
        const FVector Point=It->GetActorLocation()-At;
        const double Feet=Point.Z-It->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
        if(Pod::Contains(Point.X,Point.Y,Feet)) Victims.Add(*It);
    }
    TWeakObjectPtr<ASoraHorse> Horses[2]={TreatmentHorse(0),TreatmentHorse(1)};
    for(const auto& Weak:Victims)
    {
        if(!Current()) return false;
        auto* Victim=Weak.Get();
        if(!IsValid(Victim)||Victim->IsActorBeingDestroyed()||!Victim->IsAlive()) continue;
        ++PodState[Wave].Contacts;
        FHitResult Hit; Hit.Location=Hit.ImpactPoint=Victim->GetActorLocation();
        const float Applied=SoraDamage::Strike(Victim,Pod::Damage,FSoraHit::Hazard(At),-FVector::UpVector,Hit,nullptr,Warning.Get());
        if(!Current()) return false;
        PodState[Wave].AppliedDamage+=Applied;
    }
    for(int Index=0;Index<2;++Index)
    {
        if(!Current()) return false;
        const auto* HorseActor=Horses[Index].Get();
        if(!IsValid(HorseActor)||HorseActor->IsActorBeingDestroyed()||TaskState.TargetHp[Index]<=0||TreatmentHorse(Index)!=HorseActor) continue;
        const FVector Point=HorseActor->GetActorLocation()-At;
        if(!Pod::Contains(Point.X,Point.Y,Point.Z-90)) continue; // Actual horse frame sits 90 cm above its feet.
        ++PodState[Wave].Contacts;
        const int Before=TaskState.TargetHp[Index];
        DamageDefendedTarget(Index,Pod::Damage);
        if(!Current()) return false;
        PodState[Wave].AppliedDamage+=Before-TaskState.TargetHp[Index];
    }
    UE_LOG(LogTemp,Display,TEXT("SORA_POD_IMPACT wave=%d active_ms=%d contacts=%d applied=%.3f"),
        Wave,PodState[Wave].ElapsedMs,PodState[Wave].Contacts,PodState[Wave].AppliedDamage);
    Warning->Destroy(); PodWarnings[Wave]=nullptr;
    // SpawnPending runs afterwards through the original six-opponent cap.
    return true;
}
