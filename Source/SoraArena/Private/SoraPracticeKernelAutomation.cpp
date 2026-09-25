#include "ArenaKernelSubsystem.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "SoraAutomationWorld.h"
#include "SoraGameMode.h"
#include "SoraPlayerCharacter.h"
#include "SoraViewmodelComponent.h"
#include "Components/InputComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "InputCoreTypes.h"
#include "Misc/AutomationTest.h"
#include "Templates/UniquePtr.h"

// Runs deterministic practice in two independent game worlds, each with its own
// game instance and kernel handle. The same scripted player input goes through
// the pawn's real input bindings and the GameMode's 60 Hz practice clock. Both
// runs must produce identical kernel state hashes and presentation, and every
// kill, death and respawn reported by events must match the kernel counters.
namespace SoraPracticeKernel
{
constexpr int32 Ticks = 3600;
constexpr int32 TicksPerUpdate = 300;
constexpr int32 Slots = 6;

struct FRun
{
    FString DiagnosticHash;
    TArray<FString> Hashes;
    TArray<FSoraPracticePlayer> Final;
    FVector Start = FVector::ZeroVector;
    int32 Shots[Slots] = {};
    int32 Damage[Slots] = {};
    int32 Deaths[Slots] = {};
    int32 Kills[Slots] = {};
    int32 Respawns[Slots] = {};
    int32 UnattributedDeaths = 0;
    int32 PeakProjectiles = 0;
};

struct FState
{
    FString Slot = FSoraAutomationWorld::UniqueSaveSlot(TEXT("PracticeKernel"));
    TUniquePtr<FSoraAutomationWorld> World;
    FRun Runs[2];
    int32 Tick = 0;
    bool bAborted = false;
    ~FState()
    {
        World.Reset();
        FSoraAutomationWorld::DeleteSaveSlot(Slot);
    }
};
using FStateRef = TSharedRef<FState>;

bool Fail(FAutomationTestBase& Test, FState& State, const FString& Message)
{
    Test.AddError(Message);
    State.bAborted = true;
    return false;
}

UArenaKernelSubsystem* Kernel(const FState& State)
{
    const ASoraGameMode* Mode = State.World ? State.World->Mode() : nullptr;
    return Mode ? Mode->Kernel() : nullptr;
}

bool Press(UInputComponent& Input, FName Action, EInputEvent Event)
{
    for (int32 Index = 0; Index < Input.GetNumActionBindings(); ++Index)
    {
        const FInputActionBinding& Binding = Input.GetActionBinding(Index);
        if (Binding.GetActionName() == Action && Binding.KeyEvent == Event)
        {
            Binding.ActionDelegate.Execute(EKeys::Invalid);
            return true;
        }
    }
    return false;
}

bool Axis(UInputComponent& Input, FName Name, float Value)
{
    for (const FInputAxisBinding& Binding : Input.AxisBindings)
        if (Binding.AxisName == Name)
        {
            Binding.AxisDelegate.Execute(Value);
            return true;
        }
    return false;
}

// A fixed schedule of movement, aim, fire, melee, guard, reload, ability and
// jump. It only calls the handlers bound to the player's input actions.
bool Script(UInputComponent& Input, APlayerController& Controller, int32 Tick)
{
    bool bBound = Axis(Input, TEXT("MoveForward"), Tick % 240 < 90 ? 1.f : Tick % 240 < 150 ? 0.f : -.6f);
    bBound &= Axis(Input, TEXT("MoveRight"), (Tick / 150) % 2 ? .5f : -.5f);
    Controller.SetControlRotation(FRotator(static_cast<float>((Tick / 120) % 3 - 1) * 4.f, static_cast<float>(Tick % 288) * 1.25f, 0.f));
    if (Tick % 45 == 0) bBound &= Press(Input, TEXT("Fire"), IE_Pressed);
    if (Tick % 45 == 30) bBound &= Press(Input, TEXT("Fire"), IE_Released);
    if (Tick % 210 == 100) bBound &= Press(Input, TEXT("Melee"), IE_Pressed);
    if (Tick % 210 == 112) bBound &= Press(Input, TEXT("Melee"), IE_Released);
    if (Tick % 330 == 200) bBound &= Press(Input, TEXT("Block"), IE_Pressed);
    if (Tick % 330 == 240) bBound &= Press(Input, TEXT("Block"), IE_Released);
    if (Tick % 500 == 480) bBound &= Press(Input, TEXT("Reload"), IE_Pressed);
    if (Tick % 600 == 300) bBound &= Press(Input, TEXT("Ability"), IE_Pressed);
    if (Tick % 260 == 130) bBound &= Press(Input, TEXT("Jump"), IE_Pressed);
    if (Tick % 260 == 131) bBound &= Press(Input, TEXT("Jump"), IE_Released);
    return bBound;
}

bool StartRun(FAutomationTestBase& Test, FState& State, FRun& Run)
{
    State.World = MakeUnique<FSoraAutomationWorld>();
    State.Tick = 0;
    if (!State.World->Start(State.Slot) || !State.World->Tick(1))
    {
        State.World->ForwardErrorMessages(&Test);
        return Fail(Test, State, TEXT("Practice world did not start"));
    }
    ASoraGameMode* Mode = State.World->Mode();
    UArenaKernelSubsystem* K = Kernel(State);
    if (!Mode || !K)
        return Fail(Test, State, TEXT("Practice world lacks its game mode or kernel subsystem"));
    if (!Test.TestTrue(TEXT("Staged Rust kernel passed its ABI and zero-deposit diagnostic"), K->Available))
        return Fail(Test, State, FString::Printf(TEXT("Kernel unavailable (%s); build it with cargo build --release -p arena-ffi and run python3 scripts/unreal/stage_kernel.py"), *K->StatusText));
    Run.DiagnosticHash = K->OfflineStateHash;
    // The menu's P action, then Enter.
    Mode->DeterministicPractice();
    if (!Test.TestTrue(TEXT("Deterministic practice starts from the menu"), Mode->bDeterministicPractice && K->PracticeActive()))
        return Fail(Test, State, FString::Printf(TEXT("Practice did not start: %s"), *K->PracticeError));
    Mode->BeginRound();
    UInputComponent* Input = State.World->BindPlayerInput();
    bool bOk = Test.TestFalse(TEXT("Enter resumes practice"), Mode->bMenu);
    bOk &= Test.TestFalse(TEXT("Practice is not campaign progress"), Mode->bCampaign);
    bOk &= Test.TestEqual(TEXT("Six practice participants"), K->PracticePlayers.Num(), Slots);
    bOk &= Test.TestEqual(TEXT("Practice starts at tick zero"), static_cast<int32>(K->PracticeTick), 0);
    bOk &= Test.TestNotNull(TEXT("Player has bound input"), Input);
    // A fresh save builds chapter one's dojo round before the menu's P, so the
    // hero arrives holding the bokken; practice must present the kernel weapon.
    const ASoraPlayerCharacter* Player = State.World->Player();
    bOk &= Test.TestTrue(TEXT("Practice hero has left dojo training and the campaign loadout"),
        Player && !Player->IsDojoTraining() && !Player->IsSparring() && !Player->IsCampaignHero());
    TArray<USceneComponent*> Held;
    if (Player)
        Player->GetViewmodel()->GetChildrenComponents(true, Held);
    bool bBokken = false;
    for (const USceneComponent* Part : Held)
        if (const auto* Mesh = Cast<UStaticMeshComponent>(Part))
            bBokken |= Mesh->GetStaticMesh() && Mesh->GetStaticMesh()->GetName() == TEXT("SM_Nyaagyu_DojoBokken");
    bOk &= Test.TestFalse(TEXT("Practice hero does not hold the dojo bokken"), bBokken);
    if (!bOk)
        return Fail(Test, State, TEXT("Practice session was not ready"));
    Run.Start = K->PracticePlayers[0].Feet;
    return true;
}

bool Record(FAutomationTestBase& Test, FState& State, FRun& Run)
{
    const UArenaKernelSubsystem* K = Kernel(State);
    const ASoraGameMode* Mode = State.World->Mode();
    if (!K || !Mode)
        return Fail(Test, State, TEXT("Practice world lost its game mode or kernel subsystem"));
    // A rejected step or a nonzero deposit, balance or earning stops practice
    // and reopens the menu; zero-stake conservation is checked on every step.
    if (Mode->bMenu || !K->PracticeError.IsEmpty())
        return Fail(Test, State, FString::Printf(TEXT("Kernel practice stopped at tick %d: %s"), State.Tick, *K->PracticeError));
    // One 1/60 s frame advances the practice clock by exactly one input tick.
    if (static_cast<int32>(K->PracticeTick) != State.Tick)
        return Fail(Test, State, FString::Printf(TEXT("Frame %d advanced the kernel to tick %u"), State.Tick, K->PracticeTick));
    if (K->PracticeTerminal)
        return Fail(Test, State, TEXT("Practice reached its terminal tick early"));
    for (const FSoraPracticeEvent& Event : K->PracticeEvents)
    {
        const bool bActor = Event.Actor >= 0 && Event.Actor < Slots;
        const bool bTarget = Event.Target >= 0 && Event.Target < Slots;
        const bool bKnown = (Event.Kind == 1 && bActor) || (Event.Kind == 2 && bTarget) ||
            ((Event.Kind == 3 || Event.Kind == 4) && bTarget && (bActor || Event.Actor == INDEX_NONE));
        if (!bKnown)
            return Fail(Test, State, FString::Printf(TEXT("Unexpected practice event kind %u actor %d target %d at tick %d"),
                Event.Kind, Event.Actor, Event.Target, State.Tick));
        if (Event.Kind == 1) ++Run.Shots[Event.Actor];
        else if (Event.Kind == 2 && bActor) ++Run.Damage[Event.Actor];
        else if (Event.Kind == 3)
        {
            ++Run.Deaths[Event.Target];
            if (bActor)
            {
                if (Event.Actor == Event.Target)
                    return Fail(Test, State, TEXT("Kernel credited a player for its own death"));
                ++Run.Kills[Event.Actor];
            }
            else ++Run.UnattributedDeaths;
        }
        else if (Event.Kind == 4) ++Run.Respawns[Event.Target];
    }
    for (const FSoraPracticePlayer& Player : K->PracticePlayers)
        if (Player.Health < 0 || Player.Health > Player.MaxHealth || Player.Alive != (Player.Health > 0))
            return Fail(Test, State, FString::Printf(TEXT("Slot %d health %d/%d alive=%d at tick %d"),
                Player.Slot, Player.Health, Player.MaxHealth, Player.Alive, State.Tick));
    Run.PeakProjectiles = FMath::Max(Run.PeakProjectiles, K->PracticeProjectiles.Num());
    if (State.Tick % 60 == 0)
        Run.Hashes.Add(K->PracticeHash);
    return true;
}

bool Play(FAutomationTestBase& Test, FState& State, FRun& Run)
{
    ASoraPlayerCharacter* Player = State.World->Player();
    APlayerController* Controller = Player ? Cast<APlayerController>(Player->GetController()) : nullptr;
    if (!Controller || !Player->InputComponent)
        return Fail(Test, State, TEXT("Practice player lost its controller or input"));
    for (int32 Count = 0; Count < TicksPerUpdate && State.Tick < Ticks; ++Count)
    {
        if (!Script(*Player->InputComponent, *Controller, State.Tick))
            return Fail(Test, State, FString::Printf(TEXT("A scripted input action is not bound at tick %d"), State.Tick));
        if (!State.World->Tick(1))
        {
            State.World->ForwardErrorMessages(&Test);
            return Fail(Test, State, TEXT("Practice world failed to tick"));
        }
        ++State.Tick;
        if (!Record(Test, State, Run))
            return false;
    }
    return true;
}

bool FinishRun(FAutomationTestBase& Test, FState& State, FRun& Run, int32 Index)
{
    const UArenaKernelSubsystem* K = Kernel(State);
    Run.Final = K->PracticePlayers;
    const FString Context = FString::Printf(TEXT("Run %d"), Index + 1);
    bool bOk = Test.TestEqual(*(Context + TEXT(": one state hash per second")), Run.Hashes.Num(), Ticks / 60);
    int32 Kills = 0, Deaths = 0;
    for (int32 Slot = 0; Slot < Slots; ++Slot)
    {
        const FSoraPracticePlayer& Player = Run.Final[Slot];
        bOk &= Test.TestEqual(*FString::Printf(TEXT("%s: slot %d deaths match death events"), *Context, Slot), Player.Deaths, Run.Deaths[Slot]);
        bOk &= Test.TestEqual(*FString::Printf(TEXT("%s: slot %d kills match credited deaths"), *Context, Slot), Player.Kills, Run.Kills[Slot]);
        bOk &= Test.TestTrue(*FString::Printf(TEXT("%s: slot %d respawns only after deaths"), *Context, Slot),
            Run.Respawns[Slot] <= Run.Deaths[Slot] && Run.Deaths[Slot] - Run.Respawns[Slot] <= 1);
        Kills += Player.Kills;
        Deaths += Player.Deaths;
    }
    bOk &= Test.TestEqual(*(Context + TEXT(": every death is credited or unattributed")), Kills + Run.UnattributedDeaths, Deaths);
    bOk &= Test.TestTrue(*(Context + TEXT(": combat produced deaths")), Deaths > 0);
    bOk &= Test.TestTrue(*(Context + TEXT(": scripted fire reached the kernel")), Run.Shots[0] > 0);
    bOk &= Test.TestTrue(*(Context + TEXT(": scripted movement reached the kernel")),
        !Run.Final[0].Feet.Equals(Run.Start, 1.0) || Run.Deaths[0] > 0);
    UE_LOG(LogTemp, Display, TEXT("SORA_PRACTICE_KERNEL_RUN: run=%d ticks=%d hash=%s deaths=%d kills=%d unattributed=%d player_shots=%d peak_projectiles=%d"),
        Index + 1, State.Tick, *K->PracticeHash, Deaths, Kills, Run.UnattributedDeaths, Run.Shots[0], Run.PeakProjectiles);
    const bool bDestroyed = State.World->DestroyTestWorld(true);
    State.World->ForwardErrorMessages(&Test);
    State.World.Reset();
    bOk &= Test.TestTrue(*(Context + TEXT(": practice world tears down")), bDestroyed);
    return bOk || Fail(Test, State, Context + TEXT(" violated practice conservation"));
}

bool Compare(FAutomationTestBase& Test, FState& State)
{
    const FRun& A = State.Runs[0];
    const FRun& B = State.Runs[1];
    bool bOk = Test.TestEqual(TEXT("Independent kernels agree on the startup diagnostic"), A.DiagnosticHash, B.DiagnosticHash);
    if (A.Hashes.Num() != B.Hashes.Num())
        return Fail(Test, State, TEXT("Runs sampled different numbers of state hashes"));
    for (int32 Second = 0; Second < A.Hashes.Num(); ++Second)
        if (A.Hashes[Second] != B.Hashes[Second])
            return Fail(Test, State, FString::Printf(TEXT("State hashes diverge at tick %d: %s vs %s"),
                (Second + 1) * 60, *A.Hashes[Second], *B.Hashes[Second]));
    TSet<FString> Distinct(A.Hashes);
    bOk &= Test.TestTrue(TEXT("State hash changes as the match advances"), Distinct.Num() > 1);
    for (int32 Slot = 0; Slot < Slots; ++Slot)
    {
        const FSoraPracticePlayer& P = A.Final[Slot];
        const FSoraPracticePlayer& Q = B.Final[Slot];
        const bool bSame = P.Feet.Equals(Q.Feet, 0.0) && P.Aim.Equals(Q.Aim, 0.0) && P.Health == Q.Health &&
            P.Kills == Q.Kills && P.Deaths == Q.Deaths && P.Ammo == Q.Ammo && P.WeaponId == Q.WeaponId &&
            P.Stamina == Q.Stamina && P.Alive == Q.Alive && P.RespawnTicks == Q.RespawnTicks;
        bOk &= Test.TestTrue(*FString::Printf(TEXT("Slot %d final presentation is identical"), Slot), bSame);
        bOk &= Test.TestTrue(*FString::Printf(TEXT("Slot %d event counts are identical"), Slot),
            A.Shots[Slot] == B.Shots[Slot] && A.Damage[Slot] == B.Damage[Slot] && A.Deaths[Slot] == B.Deaths[Slot] &&
            A.Kills[Slot] == B.Kills[Slot] && A.Respawns[Slot] == B.Respawns[Slot]);
    }
    if (bOk)
        UE_LOG(LogTemp, Display, TEXT("SORA_PRACTICE_KERNEL_OK: ticks=%d hashes=%d final_hash=%s"), Ticks, A.Hashes.Num(), *A.Hashes.Last());
    return bOk || Fail(Test, State, TEXT("Independent practice runs diverged"));
}

void Step(FAutomationTestBase* Test, const FStateRef& State, TFunction<bool(FAutomationTestBase&, FState&)> Body)
{
    ADD_LATENT_AUTOMATION_COMMAND(FFunctionLatentCommand([Test, State, Body = MoveTemp(Body)]()
    {
        if (!State->bAborted)
            Body(*Test, *State);
        return true;
    }));
}
} // namespace SoraPracticeKernel

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraPracticeKernelDeterminismTest,
    "SoraArena.Practice.KernelDeterminism",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraPracticeKernelDeterminismTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraPracticeKernel;
    FSoraAutomationWorld::IgnoreMissingGeneratedArt(*this);
    const FStateRef State = MakeShared<FState>();
    FSoraAutomationWorld::IgnoreAbsentSaveSlot(*this, State->Slot);
    for (int32 Index = 0; Index < 2; ++Index)
    {
        Step(this, State, [Index](FAutomationTestBase& Test, FState& S) { return StartRun(Test, S, S.Runs[Index]); });
        for (int32 Update = 0; Update < Ticks / TicksPerUpdate; ++Update)
            Step(this, State, [Index](FAutomationTestBase& Test, FState& S) { return Play(Test, S, S.Runs[Index]); });
        Step(this, State, [Index](FAutomationTestBase& Test, FState& S) { return FinishRun(Test, S, S.Runs[Index], Index); });
    }
    Step(this, State, [](FAutomationTestBase& Test, FState& S)
    {
        const bool bOk = Compare(Test, S);
        FSoraAutomationWorld::DeleteSaveSlot(S.Slot);
        return bOk;
    });
    return true;
}
#endif
