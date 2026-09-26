#include "SoraCaptions.h"
#include "SoraGameEvents.h"
#include "SoraText.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "Kismet/GameplayStatics.h"

USoraCaptions* USoraCaptions::Get(const UObject* WorldContext)
{
    const UWorld* World = WorldContext ? WorldContext->GetWorld() : nullptr;
    return World ? World->GetSubsystem<USoraCaptions>() : nullptr;
}

bool USoraCaptions::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
    return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

void USoraCaptions::OnWorldBeginPlay(UWorld& InWorld)
{
    Super::OnWorldBeginPlay(InWorld);
    USoraGameEvents* Events = USoraGameEvents::Get(&InWorld);
    if (!Events)
        return;
    Events->OnWeaponFired.AddUObject(this, &USoraCaptions::WeaponFired);
    Events->OnMeleeCommitted.AddUObject(this, &USoraCaptions::MeleeCommitted);
    Events->OnGuarded.AddUObject(this, &USoraCaptions::Guarded);
    Events->OnParried.AddUObject(this, &USoraCaptions::Parried);
    Events->OnDetonated.AddUObject(this, &USoraCaptions::Detonated);
    Events->OnBossPhase.AddUObject(this, &USoraCaptions::BossPhase);
}

float USoraCaptions::Now() const
{
    const UWorld* World = GetWorld();
    return World ? World->GetTimeSeconds() : 0.f;
}

bool USoraCaptions::IsHero(const AActor* Actor) const
{
    return Actor && Actor == UGameplayStatics::GetPlayerPawn(this, 0);
}

void USoraCaptions::Show(const FText& Text, const FVector* Source, float Seconds)
{
    const SoraText::FLine Line = SoraText::Line(Text);
    const FString& Japanese = Line.Japanese;
    const float Time = Now();
    Captions.RemoveAll([Time](const FSoraCaption& Caption) { return Caption.Expires <= Time; });
    if (FSoraCaption* Same = Captions.FindByPredicate([&Japanese](const FSoraCaption& Caption) { return Caption.Japanese == Japanese; }))
    {
        Same->Expires = Time + Seconds;
        Same->Count += 1;
        Same->bHasSource = Source != nullptr;
        Same->Source = Source ? *Source : FVector::ZeroVector;
        return;
    }
    if (Captions.Num() >= MaxLive)
        Captions.RemoveAt(0);
    FSoraCaption& Caption = Captions.AddDefaulted_GetRef();
    Caption.Japanese = Japanese;
    Caption.English = Line.English;
    Caption.bHasSource = Source != nullptr;
    Caption.Source = Source ? *Source : FVector::ZeroVector;
    Caption.Expires = Time + Seconds;
}

TArray<FSoraCaption> USoraCaptions::Live() const
{
    const float Time = Now();
    return Captions.FilterByPredicate([Time](const FSoraCaption& Caption) { return Caption.Expires > Time; });
}

void USoraCaptions::WeaponFired(const FSoraWeaponFiredEvent& Event)
{
    if (IsHero(Event.Shooter))
        return;
    switch (Event.Kind)
    {
    case ESoraShotKind::Hitscan: Show(NSLOCTEXT("SoraArena.Captions", "Gunfire", "銃声"), &Event.Origin); return;
    case ESoraShotKind::Shell: Show(NSLOCTEXT("SoraArena.Captions", "ShellLaunched", "砲弾の発射音"), &Event.Origin); return;
    case ESoraShotKind::Arrow: Show(NSLOCTEXT("SoraArena.Captions", "ArrowLoosed", "矢を放つ音"), &Event.Origin); return;
    case ESoraShotKind::Beam: Show(NSLOCTEXT("SoraArena.Captions", "BeamHum", "光線の唸り"), &Event.Origin); return;
    }
}

void USoraCaptions::MeleeCommitted(const FSoraMeleeCommittedEvent& Event)
{
    if (IsHero(Event.Attacker) || !Event.Attacker)
        return;
    const FVector From = Event.Attacker->GetActorLocation();
    Show(NSLOCTEXT("SoraArena.Captions", "BladeDrawnBack", "刃を振りかぶる音"), &From, 2.f);
}

void USoraCaptions::Guarded(const FSoraDefenseEvent& Event)
{
    if (!Event.Defender)
        return;
    const FVector At = Event.Defender->GetActorLocation();
    if (Event.bDojo)
        Show(NSLOCTEXT("SoraArena.Captions", "WoodenSwordsKnock", "木刀の打ち合う音"), &At, 2.f);
    else
        Show(NSLOCTEXT("SoraArena.Captions", "BladeBlocked", "刃を受け止める音"), &At, 2.f);
}

void USoraCaptions::Parried(const FSoraDefenseEvent& Event)
{
    if (!Event.Defender)
        return;
    const FVector At = Event.Defender->GetActorLocation();
    Show(NSLOCTEXT("SoraArena.Captions", "BladesClash", "刃の打ち合う音"), &At, 2.f);
}

void USoraCaptions::Detonated(const FSoraDetonatedEvent& Event)
{
    Show(NSLOCTEXT("SoraArena.Captions", "Explosion", "爆発"), &Event.Location);
}

void USoraCaptions::BossPhase(const FSoraBossPhaseEvent& Event)
{
    const FVector At = Event.Boss ? Event.Boss->GetActorLocation() : FVector::ZeroVector;
    const FVector* Source = Event.Boss ? &At : nullptr;
    switch (Event.Phase)
    {
    case ESoraBossPhase::Arrived: Show(NSLOCTEXT("SoraArena.Captions", "CollectorArrives", "徴収官の重い足音"), Source, 4.f); return;
    case ESoraBossPhase::Windup:
        if (Event.bBeam)
            Show(NSLOCTEXT("SoraArena.Captions", "CollectorBeamWindup", "徴収官が光線を溜める唸り"), Source, 2.f);
        else
            Show(NSLOCTEXT("SoraArena.Captions", "CollectorCleaveWindup", "徴収官が振りかぶる音"), Source, 2.f);
        return;
    case ESoraBossPhase::Defeated: Show(NSLOCTEXT("SoraArena.Captions", "CollectorCollapses", "徴収官が崩れ落ちる音"), Source, 4.f); return;
    case ESoraBossPhase::Strike:
    case ESoraBossPhase::Recovery: return;
    }
}
