#include "SoraAudio.h"
#include "Audio/SoraAudioData.h"
#include "GameFramework/Actor.h"

bool USoraAudioSubsystem::StartAmbientEmitter(AActor* Owner, FName Name, const FVector& Location)
{
    const auto* Data = SoraAudioData::FData::Get();
    const FName* CueId = Data ? Data->Emitters.Find(Name) : nullptr;
    const auto* Cue = CueId ? Data->Cue(*CueId) : nullptr;
    if (!IsValid(Owner) || Owner->IsActorBeingDestroyed() || Owner->GetWorld() != GetWorld() ||
        Name.IsNone() || Location.ContainsNaN() || !Cue || !Cue->bLoop || !Cue->bSpatial || Cue->Bus != TEXT("Ambience"))
        return false;
    const FString Key = TEXT("ambient:") + Owner->GetPathName() + TEXT("|") + Name.ToString();
    if (const FLoop* Loop = Loops.Find(Key))
    {
        if (Loop->Cue == *CueId && Loop->LastLocation.Equals(Location))
            return true;
        StopLoop(Key, .15f);
    }
    FRequest Request;
    Request.Family = TEXT("AmbientEmitter");
    Request.Source = Owner;
    Request.Location = Location;
    Request.LoopKey = Key;
    Request.FadeInSeconds = .5f;
    Play(*CueId, Request);
    if (!IsLooping(Key))
    {
        AmbientOwners.Remove(Key);
        return false;
    }
    AmbientOwners.Add(Key, Owner);
    return true;
}

void USoraAudioSubsystem::StopAmbientEmitters(const AActor* Owner)
{
    if (!Owner)
        return;
    for (auto It = AmbientOwners.CreateIterator(); It; ++It)
        if (It.Value().Get() == Owner)
        {
            StopLoop(It.Key(), .25f);
            It.RemoveCurrent();
        }
}

void USoraAudioSubsystem::TickAmbientEmitters()
{
    // Also reap on paused ticks: clearing a scene must not leave a water
    // loop waiting to resume after its source was destroyed.
    for (auto It = AmbientOwners.CreateIterator(); It; ++It)
    {
        const AActor* Owner = It.Value().Get();
        if (!IsValid(Owner) || Owner->IsActorBeingDestroyed())
        {
            StopLoop(It.Key(), .25f);
            It.RemoveCurrent();
        }
    }
}
