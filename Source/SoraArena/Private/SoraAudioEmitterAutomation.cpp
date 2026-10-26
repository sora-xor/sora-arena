#include "SoraAudio.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "Components/AudioComponent.h"
#include "UI/SoraFrontEndTesting.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraAudioEmitterLifetimeTest,
    "SoraArena.Audio.PositionedEmitterLifetime",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraAudioEmitterLifetimeTest::RunTest(const FString&)
{
    using namespace SoraFrontEndTests;
    if (!FSoraCatalog::Get().Load()) return false;
    FScope Scope(*this, TEXT("AudioEmitter"));
    if (!Scope.Start()) return false;
    Scope.Key(EKeys::Enter); Scope.Key(EKeys::Enter); Scope.Key(EKeys::Enter);
    if (!TestTrue(TEXT("The world is playing"), Scope.Mode()->IsPlaying())) return false;
    UWorld* World = Scope.World->GetTestWorld();
    auto* Audio = USoraAudioSubsystem::Get(World);
    if (!TestNotNull(TEXT("Audio subsystem"), Audio)) return false;
    AActor* Owner = World->SpawnActor<AActor>();
    AActor* Other = World->SpawnActor<AActor>();
    if (!Owner || !Other) return false;
    const FVector At = UGameplayStatics::GetPlayerPawn(World, 0)->GetActorLocation() + FVector(100, 0, 0);
    const auto Count = [&]()
    {
        return Audio->LiveLoops().FilterByPredicate([](FName Cue) { return Cue == TEXT("amb.stream"); }).Num();
    };
    Audio->ForgetPlays();
    TestFalse(TEXT("An absent owner cannot start a loop"), Audio->StartAmbientEmitter(nullptr, TEXT("ward_culvert"), At));
    TestFalse(TEXT("An unknown emitter cannot start a loop"), Audio->StartAmbientEmitter(Owner, TEXT("unknown"), At));
    TestTrue(TEXT("An authored source starts"), Audio->StartAmbientEmitter(Owner, TEXT("ward_culvert"), At));
    TestTrue(TEXT("The repeated request keeps its voice"), Audio->StartAmbientEmitter(Owner, TEXT("ward_culvert"), At));
    if (!TestEqual(TEXT("One cue was requested"), Audio->Plays().Num(), 1)) return false;
    const FSoraAudioPlay Play = Audio->Plays()[0];
    TestTrue(TEXT("The mono water cue uses the authored world point, not its owner's origin"),
        Play.Cue == TEXT("amb.stream") && Play.IsVoiced() && Play.bLoop && Play.bSpatial &&
        Play.Location.Equals(At) && Play.Source.Get() == Owner && Play.Attenuation == TEXT("ambient_emitter"));
    if (Audio->HasDevice())
    {
        const auto* Component = Play.Component.Get();
        TestTrue(TEXT("The imported source is spatial and follows world pause"),
            Component && Component->IsPlaying() && Component->bAllowSpatialization && !Component->bIsUISound &&
            Component->GetComponentLocation().Equals(At));
    }
    TestEqual(TEXT("Repeated requests do not stack"), Count(), 1);
    TestTrue(TEXT("Another owner has its own emitter"), Audio->StartAmbientEmitter(Other, TEXT("ward_culvert"), At));
    TestEqual(TEXT("Both owners have a loop"), Count(), 2);
    Audio->StopAmbientEmitters(Owner);
    TestEqual(TEXT("Clearing one owner leaves the other"), Count(), 1);
    Audio->StopAmbientEmitters(Owner);
    TestEqual(TEXT("Clear is idempotent"), Count(), 1);
    UGameplayStatics::SetGamePaused(World, true);
    Other->Destroy();
    Scope.World->Tick(2);
    TestEqual(TEXT("A destroyed owner is reaped even while paused"), Count(), 0);
    UGameplayStatics::SetGamePaused(World, false);
    Scope.World->Tick(20);
    TestEqual(TEXT("Resuming cannot resurrect an orphaned loop"), Count(), 0);
    TestTrue(TEXT("Restaging the surviving owner starts one fresh loop"), Audio->StartAmbientEmitter(Owner, TEXT("ward_culvert"), At));
    TestTrue(TEXT("Moving an emitter replaces its world position"), Audio->StartAmbientEmitter(Owner, TEXT("ward_culvert"), At + FVector(25, 0, 0)));
    TestEqual(TEXT("Moving keeps one logical emitter"), Count(), 1);
    TestTrue(TEXT("The replacement records the new position"), Audio->Plays().Last().Location.Equals(At + FVector(25, 0, 0)));
    Audio->StopAmbientEmitters(Owner);
    Owner->Destroy();
    return !HasAnyErrors();
}
#endif
