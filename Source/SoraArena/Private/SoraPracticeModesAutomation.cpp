#include "ArenaKernelSubsystem.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "arena.h"
#include "EngineUtils.h"
#include "SoraAutomationWorld.h"
#include "SoraCatalog.h"
#include "SoraGameMode.h"
#include "SoraPlayerCharacter.h"
#include "SoraPracticeActors.h"
#include "SoraPracticeDirector.h"
#include "SoraPracticePawn.h"
#include "SoraWorldBuilder.h"
#include "HUD/SoraPracticeText.h"
#include "Camera/CameraActor.h"
#include "Components/CapsuleComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "InputCoreTypes.h"
#include "Misc/AutomationTest.h"
#include "StaticMeshResources.h"
#include "Templates/UniquePtr.h"

// Offline practice in every mode on every arena, through the real game mode,
// director and Rust kernel in a disposable game world. Every check compares
// the Unreal presentation with the kernel state it was built from.
namespace SoraPracticeModes
{
struct FState
{
    FString Slot = FSoraAutomationWorld::UniqueSaveSlot(TEXT("PracticeModes"));
    TUniquePtr<FSoraAutomationWorld> World;
    bool bAborted = false;
    int32 Case = 0;
    // Kernel event kinds and ability entity kinds seen across the test.
    int32 Kinds[ARENA_EVENT_MATCH_WINNER + 1] = {};
    int32 EntityKinds[SoraPractice::Ward + 1] = {};
    int32 Marks = 0;
    // Per match: shots, credited kills and unattributed deaths by events.
    int32 Shots = 0, Kills = 0, Deaths = 0, Unattributed = 0;
    // The hero's component count per class after its first start: a restart
    // must leave it as it was.
    TMap<int32, int32> HeroComponents;
    // The kernel's players before the frame being checked, kept by the test
    // itself so bodies are checked against the kernel, not the director.
    TArray<FSoraPracticePlayer> Before;
    // The one who struck the player down on the last frame, for the
    // spectator check on the next; how often the camera followed that
    // killer, and how often that was a choice (another living seat came first).
    int32 PendingKiller = INDEX_NONE, PlayerKiller = INDEX_NONE;
    int32 KillerFollows = 0, KillerChoices = 0;
    // Kill lines checked for the killer's weapon in both languages.
    int32 FeedWeapons = 0;
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
ASoraGameMode* Mode(const FState& State) { return State.World ? State.World->Mode() : nullptr; }
UArenaKernelSubsystem* Kernel(const FState& State) { return Mode(State) ? Mode(State)->Kernel() : nullptr; }
USoraPracticeDirector* Director(const FState& State) { return Mode(State) ? Mode(State)->Practice() : nullptr; }
FString Describe(const FSoraPracticeConfig& Config)
{
    static const TCHAR* Modes[] = {TEXT("ffa"), TEXT("control"), TEXT("payload"), TEXT("melee")};
    return FString::Printf(TEXT("%s map %d, %d players, class %d, special %d, tier %d"), Modes[Config.Mode], Config.MapId,
        Config.PlayerCount, Config.ClassId, Config.SpecialWeaponId, Config.Difficulty);
}

bool Open(FAutomationTestBase& Test, FState& State)
{
    State.World = MakeUnique<FSoraAutomationWorld>();
    if (!State.World->Start(State.Slot) || !State.World->Tick(1))
    {
        State.World->ForwardErrorMessages(&Test);
        return Fail(Test, State, TEXT("Practice world did not start"));
    }
    const UArenaKernelSubsystem* K = Kernel(State);
    if (!K || !K->Available)
        return Fail(Test, State, FString::Printf(TEXT("Kernel unavailable (%s); build it with cargo build --release -p arena-ffi and run python3 scripts/unreal/stage_kernel.py"),
            K ? *K->StatusText : TEXT("no subsystem")));
    return true;
}

bool Close(FAutomationTestBase& Test, FState& State)
{
    if (!State.World)
        return true;
    const bool bDestroyed = State.World->DestroyTestWorld(true);
    State.World->ForwardErrorMessages(&Test);
    State.World.Reset();
    return Test.TestTrue(TEXT("Practice world tears down"), bDestroyed);
}

template <typename T> int32 Count(UWorld* World)
{
    int32 Result = 0;
    for (TActorIterator<T> It(World); It; ++It)
        if (IsValid(*It))
            ++Result;
    return Result;
}

// Starts Config through the director, then Enter as the player would.
bool Begin(FAutomationTestBase& Test, FState& State, const FSoraPracticeConfig& Config, bool bAutopilot)
{
    ASoraGameMode* M = Mode(State);
    UArenaKernelSubsystem* K = Kernel(State);
    USoraPracticeDirector* D = Director(State);
    if (!M || !K || !D)
        return Fail(Test, State, TEXT("Practice world lacks its game mode, kernel or director"));
    State.Shots = State.Kills = State.Deaths = State.Unattributed = 0;
    if (!D->StartPractice(Config))
        return Fail(Test, State, FString::Printf(TEXT("%s refused: %s / %s"), *Describe(Config), *M->Notice, *M->NoticeEnglish));
    K->bPracticeAutopilot = bAutopilot;
    M->BeginRound();
    const FString Context = Describe(Config);
    bool bOk = Test.TestFalse(*(Context + TEXT(": Enter closes the menu into practice")), M->bMenu);
    bOk &= Test.TestTrue(*(Context + TEXT(": practice mode, not campaign")), M->bDeterministicPractice && !M->bCampaign);
    bOk &= Test.TestTrue(*(Context + TEXT(": the kernel took the whole choice")), K->PracticeConfig == Config && D->Config == Config);
    bOk &= Test.TestEqual(*(Context + TEXT(": kernel seats")), K->PracticePlayers.Num(), Config.PlayerCount);
    bOk &= Test.TestEqual(*(Context + TEXT(": one presented body per seat")), D->ParticipantCount(), Config.PlayerCount);
    bOk &= Test.TestEqual(*(Context + TEXT(": starts at tick zero")), static_cast<int32>(K->PracticeTick), 0);
    UWorld* World = State.World->GetTestWorld();
    // A fresh match leaves nothing behind from the one before.
    bOk &= Test.TestEqual(*(Context + TEXT(": practice pawns")), Count<ASoraPracticePawn>(World), Config.PlayerCount - 1);
    bOk &= Test.TestEqual(*(Context + TEXT(": no entity actors yet")), Count<ASoraPracticeEntityActor>(World), 0);
    bOk &= Test.TestEqual(*(Context + TEXT(": Control point actors")), Count<ASoraPracticeControlPoint>(World), Config.Mode == SoraPractice::Control ? 1 : 0);
    bOk &= Test.TestEqual(*(Context + TEXT(": payload actors")), Count<ASoraPracticePayload>(World), Config.Mode == SoraPractice::Payload ? 1 : 0);
    // Slot 0 is the player on team 0, and the teams are even.
    int32 Teams[2] = {0, 0};
    for (const FSoraPracticePlayer& P : K->PracticePlayers)
        ++Teams[P.Team];
    bOk &= Test.TestEqual(*(Context + TEXT(": player on team 0")), K->PracticePlayers[0].Team, 0);
    if (SoraPractice::IsTeamMode(Config.Mode))
        bOk &= Test.TestEqual(*(Context + TEXT(": even teams")), Teams[0], Teams[1]);
    const int32 Entry = Config.SpecialWeaponId != INDEX_NONE ? Config.SpecialWeaponId
        : Config.Mode == SoraPractice::Melee ? 2 * Config.ClassId : 2 * Config.ClassId + 1;
    bOk &= Test.TestEqual(*(Context + TEXT(": player enters with the chosen loadout")), K->PracticePlayers[0].WeaponId, Entry);
    bOk &= Test.TestEqual(*(Context + TEXT(": the menu names the kernel's entry weapon")), SoraPractice::EntryWeapon(Config.Mode, Config.ClassId, Config.SpecialWeaponId), Entry);
    bOk &= Test.TestEqual(*(Context + TEXT(": admitted special")), K->PracticePlayers[0].AdmittedSpecial, Config.SpecialWeaponId);
    // The hero outlives every match: a restart leaves exactly one banner on it
    // and no component behind.
    TInlineComponentArray<UActorComponent*> HeroParts(M->Hero());
    int32 KamonRoots = 0;
    for (const UActorComponent* Part : HeroParts)
        KamonRoots += Part->GetName().StartsWith(TEXT("SashimonoKamonRoot")) ? 1 : 0;
    bOk &= Test.TestEqual(*(Context + TEXT(": one sashimono mark on the hero")), KamonRoots, 1);
    const int32 Known = State.HeroComponents.FindOrAdd(Config.ClassId, HeroParts.Num());
    bOk &= Test.TestEqual(*(Context + TEXT(": a restart leaves the hero's components as they were")), HeroParts.Num(), Known);
    State.Before = K->PracticePlayers;
    State.PendingKiller = INDEX_NONE;
    if (Config.Mode == SoraPractice::Melee)
        for (const FSoraPracticePlayer& P : K->PracticePlayers)
            bOk &= Test.TestTrue(*(Context + TEXT(": Melee seats only blades")), (P.WeaponId % 2 == 0 && P.WeaponId < 12) || P.WeaponId == 12);
    return bOk || Fail(Test, State, Context + TEXT(" did not start as chosen"));
}

// The presentation matches the kernel state it was built from.
bool CheckPresentation(FAutomationTestBase& Test, FState& State, const FString& Context)
{
    const UArenaKernelSubsystem* K = Kernel(State);
    const USoraPracticeDirector* D = Director(State);
    const FSoraPracticeMap& Map = K->PracticeMap;
    const float Alpha = D->InterpolationAlpha();
    if (Alpha < 0.f || Alpha > 1.f)
        return Fail(Test, State, FString::Printf(TEXT("%s: interpolation fraction %f outside a tick"), *Context, Alpha));
    for (int32 Slot = 0; Slot < K->PracticePlayers.Num(); ++Slot)
    {
        const FSoraPracticePlayer& P = K->PracticePlayers[Slot];
        const ASoraCharacterBase* Pawn = D->Participant(Slot);
        if (!Pawn)
            return Fail(Test, State, FString::Printf(TEXT("%s: slot %d has no body at tick %u"), *Context, Slot, K->PracticeTick));
        // The body carries this tick's kernel state...
        if (FMath::RoundToInt(Pawn->Health) != P.Health || Pawn->ClassId != P.ClassId || Pawn->WeaponId != P.WeaponId)
            return Fail(Test, State, FString::Printf(TEXT("%s: slot %d holds health %.0f, class %d, weapon %d; the kernel has %d, %d, %d at tick %u"), *Context, Slot,
                Pawn->Health, Pawn->ClassId, Pawn->WeaponId, P.Health, P.ClassId, P.WeaponId, K->PracticeTick));
        // ...and stands between the kernel's last two states, as this test
        // recorded them; a respawn or a jump of more than 260 cm shows at once.
        const FSoraPracticePlayer* Prior = State.Before.IsValidIndex(Slot) ? &State.Before[Slot] : nullptr;
        const bool bJump = !Prior || Prior->Alive != P.Alive || FVector::Dist(Prior->Feet, P.Feet) > 260.0;
        const FVector Expected = (bJump ? P.Feet : FMath::Lerp(Prior->Feet, P.Feet, static_cast<double>(Alpha))) +
            FVector(0, 0, Pawn->GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight());
        if (!Pawn->GetActorLocation().Equals(Expected, .5))
            return Fail(Test, State, FString::Printf(TEXT("%s: slot %d drawn at %s, expected %s at tick %u"), *Context, Slot,
                *Pawn->GetActorLocation().ToString(), *Expected.ToString(), K->PracticeTick));
        if (Slot > 0 && Pawn->IsHidden() == P.Alive)
            return Fail(Test, State, FString::Printf(TEXT("%s: slot %d visibility disagrees with alive=%d at tick %u"), *Context, Slot, P.Alive, K->PracticeTick));
        if (Slot > 0 && P.Alive && P.MarkedTicks > 0)
        {
            ++State.Marks;
            if (!CastChecked<ASoraPracticePawn>(Pawn)->IsShowingMark())
                return Fail(Test, State, FString::Printf(TEXT("%s: marked slot %d shows no mark"), *Context, Slot));
        }
    }
    if (D->EntityActors().Num() != K->PracticeEntities.Num())
        return Fail(Test, State, FString::Printf(TEXT("%s: %d entity actors for %d kernel entities at tick %u"), *Context,
            D->EntityActors().Num(), K->PracticeEntities.Num(), K->PracticeTick));
    for (const FSoraPracticeEntity& E : K->PracticeEntities)
    {
        const ASoraPracticeEntityActor* Actor = D->EntityActors().FindRef(E.Id).Get();
        if (!Actor || Actor->State().Kind != E.Kind || !Actor->GetActorLocation().Equals(E.Position, .01))
            return Fail(Test, State, FString::Printf(TEXT("%s: entity %u (kind %d) is not presented where the kernel has it"), *Context, E.Id, E.Kind));
        ++State.EntityKinds[FMath::Clamp(E.Kind, 0, static_cast<int32>(SoraPractice::Ward))];
        if (E.Kind == SoraPractice::Barricade)
        {
            // The barricade's trace box is exactly the kernel's box.
            const FBox Box = Actor->Blocker()->Bounds.GetBox();
            const FBox Kernel(E.Position - FVector(E.Extent.X, E.Extent.Y, 0), E.Position + E.Extent);
            if (!Box.Min.Equals(Kernel.Min, .05) || !Box.Max.Equals(Kernel.Max, .05) || Actor->Blocker()->GetCollisionEnabled() != ECollisionEnabled::QueryOnly)
                return Fail(Test, State, FString::Printf(TEXT("%s: barricade %u box %s differs from the kernel's %s"), *Context, E.Id, *Box.ToString(), *Kernel.ToString()));
        }
        if (E.Kind == SoraPractice::Decoy && !Actor->DecoyBody())
            return Fail(Test, State, FString::Printf(TEXT("%s: decoy %u has no body"), *Context, E.Id));
    }
    const FSoraPracticeObjective& O = K->PracticeObjective;
    if (D->Config.Mode == SoraPractice::Control)
    {
        const ASoraPracticeControlPoint* Point = D->ControlPoint();
        if (!Point || !Point->GetActorLocation().Equals(Map.ControlCenter, .01))
            return Fail(Test, State, Context + TEXT(": the Control point is missing or misplaced"));
        const int32 Lit = FMath::Clamp(FMath::RoundToInt(FMath::Abs(O.ControlProgress) * 48.f / O.ControlCapture), 0, 48);
        if (K->PracticeTick >= O.UnlockTick && (Point->LitSegments() != Lit || Point->OwnerTeam() != O.ControlOwner))
            return Fail(Test, State, FString::Printf(TEXT("%s: the ring shows %d lamps and owner %d for progress %d and owner %d"), *Context,
                Point->LitSegments(), Point->OwnerTeam(), O.ControlProgress, O.ControlOwner));
    }
    if (D->Config.Mode == SoraPractice::Payload)
    {
        const ASoraPracticePayload* Payload = D->Payload();
        // The cart is drawn at most one kernel step (10 mm) behind the payload.
        if (!Payload || FVector::Dist(Payload->Cart()->GetComponentLocation(), O.PayloadPosition) > 1.5 || Payload->ReachedCheckpoints() != O.PayloadCheckpoints)
            return Fail(Test, State, FString::Printf(TEXT("%s: the cart is not where the kernel's payload is at tick %u"), *Context, K->PracticeTick));
    }
    return true;
}

// Advances one 60 Hz frame and records the tick.
bool Advance(FAutomationTestBase& Test, FState& State, const FString& Context)
{
    const UArenaKernelSubsystem* K = Kernel(State);
    const USoraPracticeDirector* D = Director(State);
    const uint32 Before = K->PracticeTick;
    // The player went down on the last frame: now the spectator camera
    // follows the killer while that killer stands.
    const int32 Killer = State.PendingKiller;
    State.PendingKiller = INDEX_NONE;
    if (!State.World->Tick(1))
    {
        State.World->ForwardErrorMessages(&Test);
        return Fail(Test, State, Context + TEXT(": world failed to tick"));
    }
    const ASoraGameMode* M = Mode(State);
    if (M->bMenu || !K->PracticeError.IsEmpty())
        return Fail(Test, State, FString::Printf(TEXT("%s: practice stopped at tick %u: %s"), *Context, K->PracticeTick, *K->PracticeError));
    if (K->PracticeTick != Before + 1)
        return Fail(Test, State, FString::Printf(TEXT("%s: one frame moved the kernel from %u to %u"), *Context, Before, K->PracticeTick));
    // Zero stake on every tick: nothing deposited, held or earned.
    if (K->PracticeDeposited || K->PracticeRemaining || K->PracticeEarnings)
        return Fail(Test, State, Context + TEXT(": practice ledger is not zero"));
    for (const FSoraPracticeEvent& Event : K->PracticeEvents)
    {
        if (Event.Kind < ARENA_EVENT_SHOT || Event.Kind > ARENA_EVENT_MATCH_WINNER)
            return Fail(Test, State, FString::Printf(TEXT("%s: unknown event kind %u"), *Context, Event.Kind));
        ++State.Kinds[Event.Kind];
        State.Shots += Event.Kind == ARENA_EVENT_SHOT ? 1 : 0;
        if (Event.Kind == ARENA_EVENT_DEATH)
        {
            ++State.Deaths;
            if (Event.Actor == INDEX_NONE) ++State.Unattributed;
            else if (Event.Actor == Event.Target) return Fail(Test, State, Context + TEXT(": the kernel credited a player for its own death"));
            else
            {
                ++State.Kills;
                // The feed names the weapon the killer held, in both languages.
                const FSoraPracticeFeedEntry* Line = D->Feed().FindByPredicate([&](const FSoraPracticeFeedEntry& Entry)
                    { return Entry.Kind == FSoraPracticeFeedEntry::Kill && Entry.Tick == K->PracticeTick && Entry.Actor == Event.Actor && Entry.Target == Event.Target; });
                const int32 Held = K->PracticePlayers[Event.Actor].WeaponId;
                const FSoraWeapon& Weapon = FSoraCatalog::Get().Weapon(Held);
                const SoraPracticeText::FLine Text = Line ? SoraPracticeText::FeedLine(*K, *Line) : SoraPracticeText::FLine();
                if (!Line || Line->WeaponId != Held || !Text.Japanese.Contains(Weapon.Name) || !Text.English.Contains(Weapon.NameEnglish))
                    return Fail(Test, State, FString::Printf(TEXT("%s: the kill of slot %d by slot %d at tick %u does not name weapon %d: \"%s\" / \"%s\""), *Context,
                        Event.Target, Event.Actor, K->PracticeTick, Held, *Text.Japanese, *Text.English));
                ++State.FeedWeapons;
            }
            if (Event.Target == 0) State.PendingKiller = State.PlayerKiller = Event.Actor;
        }
    }
    if (Killer != INDEX_NONE && K->PracticePlayers.IsValidIndex(Killer) && K->PracticePlayers[Killer].Alive && !K->PracticeTerminal)
    {
        if (!D->IsSpectating() || D->SpectatedSlot() != Killer)
            return Fail(Test, State, FString::Printf(TEXT("%s: down at tick %u, the camera shows slot %d, not the killer %d"), *Context, K->PracticeTick, D->SpectatedSlot(), Killer));
        ++State.KillerFollows;
        // Following the killer was a choice when another living seat comes
        // first in the cycling order.
        for (int32 Slot = 1; Slot < Killer; ++Slot)
            if (K->PracticePlayers[Slot].Alive) { ++State.KillerChoices; break; }
    }
    const bool bOk = CheckPresentation(Test, State, Context);
    State.Before = K->PracticePlayers;
    return bOk;
}

// Every rule of World/SoraPracticeArena.h, for the arena just built.
bool CheckArena(FAutomationTestBase& Test, FState& State)
{
    const UArenaKernelSubsystem* K = Kernel(State);
    const ASoraWorldBuilder* Builder = Mode(State)->Arena();
    const FSoraPracticeMap& Map = K->PracticeMap;
    const FString Context = FString::Printf(TEXT("Arena %d (%s)"), Map.MapId, *Map.Slug);
    constexpr double Tolerance = .6, FlatHeight = 8.01;
    const UStaticMesh* Cube = LoadObject<UStaticMesh>(nullptr, SoraPracticeArt::Cube);
    TArray<UStaticMeshComponent*> Components;
    Builder->GetComponents(Components);
    // The boxes that dress each kernel wall.
    TArray<TArray<FBox>> Fill;
    Fill.SetNum(Map.Walls.Num());
    TArray<bool> Matched;
    Matched.SetNumZeroed(Map.Walls.Num());
    int32 Grounds = 0, Pieces = 0, Flat = 0, Hazard = 0, Outside = 0;
    const auto Inside = [](const FBox& Box, const FVector& Min, const FVector& Max)
    {
        return Box.Min.X >= Min.X - Tolerance && Box.Min.Y >= Min.Y - Tolerance && Box.Min.Z >= Min.Z - Tolerance &&
            Box.Max.X <= Max.X + Tolerance && Box.Max.Y <= Max.Y + Tolerance && Box.Max.Z <= Max.Z + Tolerance;
    };
    // Places one visible piece: a box of a wall's dressing inside that wall,
    // or anything flat, inside a hazard or outside the bounds.
    const auto Classify = [&](const FBox& Box, bool bWallBox, const FString& Name)
    {
        ++Pieces;
        for (int32 Index = 0; Index < Map.Walls.Num(); ++Index)
            if (Inside(Box, Map.Walls[Index].Minimum, Map.Walls[Index].Maximum))
            {
                // Only an axis-aligned box can be checked against the kernel's
                // box; any other mesh there could hide invisible collision.
                if (!bWallBox)
                    return Fail(Test, State, FString::Printf(TEXT("%s: %s inside wall %d (%s) is not a box piece of its dressing"), *Context, *Name, Index, *Map.Walls[Index].Label));
                Fill[Index].Add(Box);
                return true;
            }
        if (bWallBox)
            return Fail(Test, State, FString::Printf(TEXT("%s: wall dressing %s leaves every kernel wall at %s"), *Context, *Name, *Box.ToString()));
        if (Box.Max.Z <= Map.Minimum.Z + FlatHeight) { ++Flat; return true; }
        for (const FSoraPracticeHazard& H : Map.Hazards)
            if (Inside(Box, H.Minimum - FVector(.4), H.Maximum + FVector(.4))) { ++Hazard; return true; }
        if (Box.Min.X >= Map.Maximum.X || Box.Max.X <= Map.Minimum.X || Box.Min.Y >= Map.Maximum.Y || Box.Max.Y <= Map.Minimum.Y) { ++Outside; return true; }
        return Fail(Test, State, FString::Printf(TEXT("%s: visual piece %s stands in the playable space at %s"), *Context, *Name, *Box.ToString()));
    };
    int32 Batches = 0;
    for (const UStaticMeshComponent* Component : Components)
    {
        if (!Component->IsRegistered() || !Component->GetStaticMesh())
            continue;
        const FBox Box = Component->Bounds.GetBox();
        const bool bCollides = Component->GetCollisionEnabled() != ECollisionEnabled::NoCollision;
        if (Component->ComponentHasTag(TEXT("KernelWall")))
        {
            int32 Found = INDEX_NONE;
            for (int32 Wall = 0; Wall < Map.Walls.Num(); ++Wall)
                if (!Matched[Wall] && Box.Min.Equals(Map.Walls[Wall].Minimum, .01) && Box.Max.Equals(Map.Walls[Wall].Maximum, .01)) { Found = Wall; break; }
            if (Found == INDEX_NONE || !bCollides || Component->IsVisible())
                return Fail(Test, State, FString::Printf(TEXT("%s: collision box %s is not exactly one hidden kernel wall"), *Context, *Box.ToString()));
            Matched[Found] = true;
            continue;
        }
        if (Component->ComponentHasTag(TEXT("KernelGround")))
        {
            ++Grounds;
            if (!bCollides || FMath::Abs(Box.Max.Z - Map.Minimum.Z) > .01)
                return Fail(Test, State, Context + TEXT(": the ground's top is not the kernel floor"));
            continue;
        }
        if (bCollides)
            return Fail(Test, State, FString::Printf(TEXT("%s: dressing %s collides"), *Context, *Component->GetName()));
        if (!Component->IsVisible() || Component->GetName().Contains(TEXT("OvercastSky")))
            continue;
        if (const auto* Batch = Cast<UInstancedStaticMeshComponent>(Component))
        {
            ++Batches;
            const FBox Local = Batch->GetStaticMesh()->GetBoundingBox();
            const bool bWallBox = Batch->ComponentHasTag(TEXT("PracticeWallPiece")) && Batch->GetStaticMesh() == Cube;
            for (int32 Instance = 0; Instance < Batch->GetInstanceCount(); ++Instance)
            {
                FTransform Transform;
                Batch->GetInstanceTransform(Instance, Transform, true);
                // A box stays a box only when it is turned by whole quarter turns.
                const FRotator Turn = Transform.Rotator();
                const double Quarter = FMath::Fmod(FMath::Abs(Turn.Yaw), 90.0);
                const bool bAligned = (Quarter < .01 || Quarter > 89.99) && FMath::IsNearlyZero(Turn.Pitch, .01) && FMath::IsNearlyZero(Turn.Roll, .01);
                if (!Classify(Local.TransformBy(Transform), bWallBox && bAligned, FString::Printf(TEXT("%s[%d]"), *Batch->GetName(), Instance)))
                    return false;
            }
            continue;
        }
        if (!Classify(Box, false, Component->GetName()))
            return false;
    }
    bool bOk = Test.TestEqual(*(Context + TEXT(": one ground slab")), Grounds, 1);
    int64 Samples = 0;
    for (int32 Wall = 0; Wall < Map.Walls.Num(); ++Wall)
    {
        const FSoraPracticeWall& W = Map.Walls[Wall];
        const FBox Kernel(W.Minimum, W.Maximum);
        const FString Name = FString::Printf(TEXT("%s: wall %d (%s)"), *Context, Wall, *W.Label);
        bOk &= Test.TestTrue(*(Name + TEXT(" has its hidden kernel box")), Matched[Wall]);
        // The boxes tile the wall: they do not overlap, and together they
        // have its volume...
        double Filled = 0, Overlap = 0;
        const TArray<FBox>& Boxes = Fill[Wall];
        for (int32 A = 0; A < Boxes.Num(); ++A)
        {
            Filled += Boxes[A].GetVolume();
            for (int32 B = A + 1; B < Boxes.Num(); ++B)
                if (Boxes[A].Intersect(Boxes[B])) Overlap += Boxes[A].Overlap(Boxes[B]).GetVolume();
        }
        bOk &= Test.TestTrue(*FString::Printf(TEXT("%s's dressing does not overlap (%.1f cm3)"), *Name, Overlap), Overlap <= Kernel.GetVolume() * 1e-5);
        bOk &= Test.TestTrue(*FString::Printf(TEXT("%s is dressed to its exact volume (%.0f of %.0f cm3)"), *Name, Filled, Kernel.GetVolume()),
            FMath::Abs(Filled - Kernel.GetVolume()) <= Kernel.GetVolume() * .003);
        // ...and every face a player or a shot can meet is visible exactly on
        // the kernel's face: points 5 mm inside each side and the top, every
        // 10 cm, all lie in a dressing box.
        int32 Holes = 0;
        FVector FirstHole = FVector::ZeroVector;
        const auto Covered = [&Boxes](const FVector& Point)
        {
            for (const FBox& Box : Boxes)
                if (Box.IsInsideOrOn(Point)) return true;
            return false;
        };
        const FVector Min = Kernel.Min, Max = Kernel.Max;
        for (int32 Face = 0; Face < 5; ++Face)
        {
            // Faces: -X, +X, -Y, +Y, top. U and V run across the face.
            const int32 Axis = Face < 2 ? 0 : Face < 4 ? 1 : 2;
            const double Depth = Face == 0 || Face == 2 ? Min[Axis] + .5 : Max[Axis] - .5;
            const int32 UAxis = Axis == 0 ? 1 : 0, VAxis = Axis == 2 ? 1 : 2;
            const int32 USteps = FMath::Max(1, FMath::CeilToInt((Max[UAxis] - Min[UAxis]) / 10.0));
            const int32 VSteps = FMath::Max(1, FMath::CeilToInt((Max[VAxis] - Min[VAxis]) / 10.0));
            for (int32 U = 0; U <= USteps; ++U)
                for (int32 V = 0; V <= VSteps; ++V)
                {
                    FVector Point;
                    Point[Axis] = Depth;
                    Point[UAxis] = FMath::Lerp(Min[UAxis] + .5, Max[UAxis] - .5, static_cast<double>(U) / USteps);
                    Point[VAxis] = FMath::Lerp(Min[VAxis] + .5, Max[VAxis] - .5, static_cast<double>(V) / VSteps);
                    ++Samples;
                    if (!Covered(Point)) { if (Holes++ == 0) FirstHole = Point; }
                }
        }
        bOk &= Test.TestEqual(*FString::Printf(TEXT("%s shows every face of its kernel box (first gap at %s)"), *Name, *FirstHole.ToString()), Holes, 0);
    }
    UE_LOG(LogTemp, Display, TEXT("SORA_PRACTICE_ARENA_OK: map=%d slug=%s walls=%d pieces=%d batches=%d components=%d face_samples=%lld flat=%d hazard=%d backdrop=%d"),
        Map.MapId, *Map.Slug, Map.Walls.Num(), Pieces, Batches, Components.Num(), Samples, Flat, Hazard, Outside);
    // Spawn pads, the Control plaza and the payload track lie flat too.
    TArray<const AActor*> ModeActors = {Director(State)->ModeDressing(), Director(State)->ControlPoint()};
    for (const AActor* Actor : ModeActors)
    {
        if (!Actor) continue;
        TArray<UStaticMeshComponent*> Parts;
        Actor->GetComponents(Parts);
        for (const UStaticMeshComponent* Part : Parts)
            if (Part->IsVisible() && Part->Bounds.GetBox().Max.Z > Map.Minimum.Z + FlatHeight)
                return Fail(Test, State, FString::Printf(TEXT("%s: mode piece %s rises off the floor"), *Context, *Part->GetName()));
    }
    return bOk || Fail(Test, State, Context + TEXT(" breaks the dressing rules"));
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
// Runs Body over successive latent frames until it reports done.
void Repeat(FAutomationTestBase* Test, const FStateRef& State, TFunction<bool(FAutomationTestBase&, FState&, bool&)> Body)
{
    ADD_LATENT_AUTOMATION_COMMAND(FFunctionLatentCommand([Test, State, Body = MoveTemp(Body)]()
    {
        if (State->bAborted)
            return true;
        bool bDone = false;
        if (!Body(*Test, *State, bDone))
            return true;
        return bDone;
    }));
}
void Prepare(FAutomationTestBase& Test, const FStateRef& State)
{
    FSoraAutomationWorld::IgnoreMissingGeneratedArt(Test);
    FSoraAutomationWorld::IgnoreAbsentSaveSlot(Test, State->Slot);
}
} // namespace SoraPracticeModes

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraPracticeArenaDressingTest,
    "SoraArena.Practice.ArenaDressing",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraPracticeArenaDressingTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraPracticeModes;
    const FStateRef State = MakeShared<FState>();
    Prepare(*this, State);
    Step(this, State, [](FAutomationTestBase& Test, FState& S) { return Open(Test, S); });
    for (int32 Map = 0; Map < SoraPractice::MapCount; ++Map)
        Step(this, State, [Map](FAutomationTestBase& Test, FState& S)
        {
            FSoraPracticeConfig Config;
            Config.MapId = Map; Config.PlayerCount = 2; Config.Difficulty = SoraPractice::BotNovice;
            return Begin(Test, S, Config, false) && CheckArena(Test, S);
        });
    Step(this, State, [](FAutomationTestBase& Test, FState& S) { return Close(Test, S); });
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraPracticeModeSmokeTest,
    "SoraArena.Practice.ModeSmoke",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraPracticeModeSmokeTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraPracticeModes;
    // Every mode on every arena for 900 ticks: past the objectives' unlock at
    // 600, with a spread of seat counts, classes, specials and tiers.
    constexpr int32 Ticks = 900;
    static const int32 Seats[SoraPractice::ModeCount][SoraPractice::MapCount] = {{8, 6, 4, 8}, {12, 8, 4, 12}, {12, 10, 6, 12}, {8, 6, 3, 8}};
    const FStateRef State = MakeShared<FState>();
    Prepare(*this, State);
    Step(this, State, [](FAutomationTestBase& Test, FState& S) { return Open(Test, S); });
    for (int32 Mode = 0; Mode < SoraPractice::ModeCount; ++Mode)
        for (int32 Map = 0; Map < SoraPractice::MapCount; ++Map)
        {
            FSoraPracticeConfig Config;
            Config.Mode = Mode; Config.MapId = Map; Config.PlayerCount = Seats[Mode][Map];
            Config.ClassId = (Mode * 2 + Map) % SoraPractice::ClassCount;
            // Specials on odd arenas, where the mode admits the class's one.
            const bool bBladeSpecial = Config.ClassId == 0;
            if (Map % 2 == 1 && (Mode != SoraPractice::Melee || bBladeSpecial)) Config.SpecialWeaponId = SoraPractice::SpecialOf(Config.ClassId);
            Config.Difficulty = (Mode + Map) % SoraPractice::BotCount;
            Step(this, State, [Config](FAutomationTestBase& Test, FState& S) { return Begin(Test, S, Config, true); });
            Repeat(this, State, [Config](FAutomationTestBase& Test, FState& S, bool& bDone)
            {
                const FString Context = Describe(Config);
                for (int32 Frame = 0; Frame < 300 && static_cast<int32>(Kernel(S)->PracticeTick) < Ticks; ++Frame)
                    if (!Advance(Test, S, Context)) return false;
                bDone = static_cast<int32>(Kernel(S)->PracticeTick) >= Ticks;
                return true;
            });
            Step(this, State, [Config, Map](FAutomationTestBase& Test, FState& S)
            {
                const FString Context = Describe(Config);
                const UArenaKernelSubsystem* K = Kernel(S);
                bool bOk = Test.TestFalse(*(Context + TEXT(": no terminal in 15 seconds")), K->PracticeTerminal);
                bOk &= Test.TestEqual(*(Context + TEXT(": objective mode")), K->PracticeObjective.Mode, Config.Mode);
                bOk &= Test.TestTrue(*(Context + TEXT(": this match saw shots")), S.Shots > 0);
                if (Map == 0 && Config.Mode == SoraPractice::FreeForAll)
                {
                    // Half a kernel step: bodies stand halfway between the last two states.
                    USoraPracticeDirector* D = Director(S);
                    int32 Moving = INDEX_NONE;
                    TArray<FVector> Before;
                    for (const FSoraPracticePlayer& P : K->PracticePlayers) Before.Add(P.Feet);
                    if (!Advance(Test, S, Context)) return false;
                    for (int32 Slot = 1; Slot < K->PracticePlayers.Num() && Moving == INDEX_NONE; ++Slot)
                        if (K->PracticePlayers[Slot].Alive && FVector::Dist(Before[Slot], K->PracticePlayers[Slot].Feet) > 1.0 && FVector::Dist(Before[Slot], K->PracticePlayers[Slot].Feet) < 200.0)
                            Moving = Slot;
                    bOk &= Test.TestTrue(*(Context + TEXT(": a bot is moving")), Moving != INDEX_NONE);
                    if (Moving != INDEX_NONE)
                    {
                        S.World->Tick(1, 1.f / 120.f);
                        const FVector Half = FMath::Lerp(Before[Moving], K->PracticePlayers[Moving].Feet, .5);
                        bOk &= Test.TestEqual(TEXT("A half-tick frame advances no kernel step"), static_cast<int32>(K->PracticeTick), Ticks + 1);
                        bOk &= Test.TestTrue(TEXT("A half-tick frame presents the body halfway between kernel states"), D->PresentedFeet(Moving).Equals(Half, .05));
                        bOk &= Test.TestTrue(TEXT("The body is drawn at the presented place"),
                            D->Participant(Moving)->GetActorLocation().Equals(Half + FVector(0, 0, D->Participant(Moving)->GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight()), .05));
                        S.World->Tick(1, 1.f / 120.f);
                    }
                }
                UE_LOG(LogTemp, Display, TEXT("SORA_PRACTICE_SMOKE: %s ticks=%u shots=%d deaths=%d entities=%d hash=%s"), *Context, K->PracticeTick, S.Shots, S.Deaths, K->PracticeEntities.Num(), *K->PracticeHash);
                return bOk || Fail(Test, S, Context + TEXT(" smoke run failed"));
            });
        }
    Step(this, State, [](FAutomationTestBase& Test, FState& S)
    {
        FString Kinds;
        for (int32 Kind = ARENA_EVENT_SHOT; Kind <= ARENA_EVENT_MATCH_WINNER; ++Kind)
            Kinds += FString::Printf(TEXT("%s%d:%d"), Kind == ARENA_EVENT_SHOT ? TEXT("") : TEXT(","), Kind, S.Kinds[Kind]);
        UE_LOG(LogTemp, Display, TEXT("SORA_PRACTICE_SMOKE_OK: runs=16 kinds=%s entities=decoy:%d,barricade:%d,fire:%d,ward:%d marks=%d"), *Kinds,
            S.EntityKinds[1], S.EntityKinds[2], S.EntityKinds[3], S.EntityKinds[4], S.Marks);
        return Close(Test, S);
    });
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraPracticeFullMatchTest,
    "SoraArena.Practice.FullMatches",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraPracticeFullMatchTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraPracticeModes;
    // One whole match per mode, the player seat also on the Rust bot policy,
    // played to the kernel's terminal tick through the game mode's clock.
    FSoraPracticeConfig Configs[SoraPractice::ModeCount];
    Configs[0].Mode = SoraPractice::FreeForAll; Configs[0].PlayerCount = 8; Configs[0].MapId = 0; Configs[0].ClassId = 2; Configs[0].Difficulty = SoraPractice::BotStandard;
    Configs[1].Mode = SoraPractice::Control; Configs[1].PlayerCount = 12; Configs[1].MapId = 1; Configs[1].ClassId = 0; Configs[1].SpecialWeaponId = 12; Configs[1].Difficulty = SoraPractice::BotVeteran;
    Configs[2].Mode = SoraPractice::Payload; Configs[2].PlayerCount = 12; Configs[2].MapId = 2; Configs[2].ClassId = 5; Configs[2].SpecialWeaponId = 17; Configs[2].Difficulty = SoraPractice::BotVeteran;
    Configs[3].Mode = SoraPractice::Melee; Configs[3].PlayerCount = 6; Configs[3].MapId = 3; Configs[3].ClassId = 1; Configs[3].Difficulty = SoraPractice::BotMaster;
    const FStateRef State = MakeShared<FState>();
    Prepare(*this, State);
    Step(this, State, [](FAutomationTestBase& Test, FState& S) { return Open(Test, S); });
    for (const FSoraPracticeConfig& Config : Configs)
    {
        Step(this, State, [Config](FAutomationTestBase& Test, FState& S) { return Begin(Test, S, Config, true); });
        Repeat(this, State, [Config](FAutomationTestBase& Test, FState& S, bool& bDone)
        {
            const FString Context = Describe(Config);
            for (int32 Frame = 0; Frame < 1200 && !Kernel(S)->PracticeTerminal; ++Frame)
                if (!Advance(Test, S, Context)) return false;
            bDone = Kernel(S)->PracticeTerminal;
            return true;
        });
        Step(this, State, [Config](FAutomationTestBase& Test, FState& S)
        {
            const FString Context = Describe(Config);
            ASoraGameMode* M = Mode(S);
            UArenaKernelSubsystem* K = Kernel(S);
            USoraPracticeDirector* D = Director(S);
            const FSoraPracticeObjective& O = K->PracticeObjective;
            const FSoraPracticeResults& R = D->Results();
            bool bOk = Test.TestTrue(*(Context + TEXT(": terminal within ten minutes")), K->PracticeTerminal && K->PracticeTick <= SoraPractice::MatchTicks);
            bOk &= Test.TestTrue(*(Context + TEXT(": a winner, not a draw")), O.WinnerKind == (SoraPractice::IsTeamMode(Config.Mode) ? SoraPractice::WinnerTeam : SoraPractice::WinnerSlot));
            bOk &= Test.TestTrue(*(Context + TEXT(": the winner is a team or a seat")),
                O.WinnerKind == SoraPractice::WinnerTeam ? O.WinnerValue <= 1 : O.WinnerValue < Config.PlayerCount);
            // Zero-stake conservation, as the results screen states it.
            bOk &= Test.TestTrue(*(Context + TEXT(": results captured")), R.bValid && R.Tick == K->PracticeTick && R.WinnerKind == O.WinnerKind && R.WinnerValue == O.WinnerValue);
            bOk &= Test.TestTrue(*(Context + TEXT(": deposited equals reserves plus earnings, all zero")), R.bConserved && R.Deposited == 0 && R.Deposited == R.Remaining + R.Earnings);
            int32 Kills = 0, Deaths = 0;
            for (int32 Slot = 0; Slot < R.Players.Num(); ++Slot)
            {
                Kills += R.Players[Slot].Kills; Deaths += R.Players[Slot].Deaths;
                bOk &= Test.TestTrue(*FString::Printf(TEXT("%s: slot %d result row matches the kernel"), *Context, Slot),
                    R.Players[Slot].Kills == K->PracticePlayers[Slot].Kills && R.Players[Slot].Deaths == K->PracticePlayers[Slot].Deaths && R.Players[Slot].InitialBond == 0);
            }
            bOk &= Test.TestEqual(*(Context + TEXT(": kills match credited death events")), Kills, S.Kills);
            bOk &= Test.TestEqual(*(Context + TEXT(": deaths match death events")), Deaths, S.Deaths);
            bOk &= Test.TestEqual(*(Context + TEXT(": every death is credited or unattributed")), Kills + S.Unattributed, Deaths);
            if (Config.Mode == SoraPractice::FreeForAll || Config.Mode == SoraPractice::Melee)
            {
                // §8.3: most kills, then fewest deaths.
                const FSoraPracticePlayer& Winner = K->PracticePlayers[O.WinnerValue];
                for (const FSoraPracticePlayer& P : K->PracticePlayers)
                    bOk &= Test.TestTrue(*(Context + TEXT(": the winner leads on kills, then deaths")),
                        P.Slot == Winner.Slot || P.Kills < Winner.Kills || (P.Kills == Winner.Kills && P.Deaths > Winner.Deaths));
            }
            bool bWinnerLine = false;
            for (const FSoraPracticeFeedEntry& Entry : D->Feed()) bWinnerLine |= Entry.Kind == FSoraPracticeFeedEntry::Winner;
            bOk &= Test.TestTrue(*(Context + TEXT(": the feed announces the result")), bWinnerLine);
            bOk &= Test.TestTrue(*(Context + TEXT(": the match ends on the result screen")), M->bChapterComplete && M->InputState() == SoraInput::Result);
            // After the terminal tick nothing steps; the spectator circles the arena.
            const uint32 Final = K->PracticeTick;
            S.World->Tick(30);
            const APlayerController* Controller = Cast<APlayerController>(S.World->Player()->GetController());
            bOk &= Test.TestEqual(*(Context + TEXT(": no step after the terminal tick")), static_cast<int32>(K->PracticeTick), static_cast<int32>(Final));
            bOk &= Test.TestTrue(*(Context + TEXT(": the spectator camera shows the finished arena")),
                D->IsSpectating() && D->SpectatorCamera() && Controller && Controller->GetViewTarget() == D->SpectatorCamera());
            UE_LOG(LogTemp, Display, TEXT("SORA_PRACTICE_MATCH_OK: %s ticks=%u winner_kind=%d winner=%d score=%d:%d checkpoints=%d kills=%d deaths=%d unattributed=%d hash=%s"),
                *Context, K->PracticeTick, O.WinnerKind, O.WinnerValue, O.Score[0], O.Score[1], O.PayloadCheckpoints, Kills, Deaths, S.Unattributed, *K->PracticeHash);
            // Enter plays the same match again from its first tick.
            M->BeginRound();
            bOk &= Test.TestTrue(*(Context + TEXT(": Enter starts a fresh match")), K->PracticeActive() && K->PracticeTick == 0 && !K->PracticeTerminal && !M->bChapterComplete && !M->bMenu);
            S.World->Tick(2);
            bOk &= Test.TestTrue(*(Context + TEXT(": the player's own view returns")), !D->IsSpectating() && Controller->GetViewTarget() == S.World->Player());
            return bOk || Fail(Test, S, Context + TEXT(" did not finish correctly"));
        });
    }
    Step(this, State, [](FAutomationTestBase& Test, FState& S)
    {
        // The long matches present every ability entity and the Teppo mark.
        bool bOk = true;
        for (int32 Kind = SoraPractice::Decoy; Kind <= SoraPractice::Ward; ++Kind)
            bOk &= Test.TestTrue(*FString::Printf(TEXT("Entity kind %d was presented and checked"), Kind), S.EntityKinds[Kind] > 0);
        bOk &= Test.TestTrue(TEXT("A Teppo mark was shown over a marked player"), S.Marks > 0);
        // Every death of the player moved the camera to a standing killer, and
        // at least once another living seat came first in the cycling order.
        bOk &= Test.TestTrue(TEXT("The spectator camera followed the player's killers"), S.KillerFollows > 0);
        bOk &= Test.TestTrue(TEXT("Following the killer was a choice at least once"), S.KillerChoices > 0);
        bOk &= Test.TestTrue(TEXT("Kill lines named the killers' weapons"), S.FeedWeapons > 0);
        FString Kinds;
        for (int32 Kind = ARENA_EVENT_SHOT; Kind <= ARENA_EVENT_MATCH_WINNER; ++Kind)
            Kinds += FString::Printf(TEXT("%s%d:%d"), Kind == ARENA_EVENT_SHOT ? TEXT("") : TEXT(","), Kind, S.Kinds[Kind]);
        UE_LOG(LogTemp, Display, TEXT("SORA_PRACTICE_MATCHES_OK: kinds=%s entities=decoy:%d,barricade:%d,fire:%d,ward:%d marks=%d killer_follows=%d killer_choices=%d feed_weapons=%d"), *Kinds,
            S.EntityKinds[1], S.EntityKinds[2], S.EntityKinds[3], S.EntityKinds[4], S.Marks, S.KillerFollows, S.KillerChoices, S.FeedWeapons);
        return Close(Test, S) && bOk;
    });
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraPracticeRespawnLoadoutTest,
    "SoraArena.Practice.RespawnLoadout",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraPracticeRespawnLoadoutTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraPracticeModes;
    // A Samurai admitted with the naginata stands still among three Veteran
    // bots until struck down, then chooses a new class and weapon while the
    // spectator camera follows the one who struck, and returns with that
    // loadout.
    FSoraPracticeConfig Config;
    Config.PlayerCount = 4; Config.MapId = 0; Config.ClassId = 0; Config.SpecialWeaponId = 12; Config.Difficulty = SoraPractice::BotVeteran;
    const FStateRef State = MakeShared<FState>();
    Prepare(*this, State);
    Step(this, State, [](FAutomationTestBase& Test, FState& S) { return Open(Test, S) && S.World->EnableKeyInput(); });
    Step(this, State, [Config](FAutomationTestBase& Test, FState& S) { return Begin(Test, S, Config, false); });
    Repeat(this, State, [Config](FAutomationTestBase& Test, FState& S, bool& bDone)
    {
        const UArenaKernelSubsystem* K = Kernel(S);
        for (int32 Frame = 0; Frame < 600 && K->PracticePlayers[0].Alive; ++Frame)
            if (!Advance(Test, S, Describe(Config))) return false;
        if (!K->PracticePlayers[0].Alive) { bDone = true; return true; }
        if (K->PracticeTick >= 7200) return Fail(Test, S, TEXT("No Veteran bot struck down the still player in two minutes"));
        return true;
    });
    Step(this, State, [Config](FAutomationTestBase& Test, FState& S)
    {
        const FString Context = Describe(Config);
        UArenaKernelSubsystem* K = Kernel(S);
        USoraPracticeDirector* D = Director(S);
        if (!Advance(Test, S, Context)) return false;
        const APlayerController* Controller = Cast<APlayerController>(S.World->Player()->GetController());
        bool bOk = Test.TestTrue(TEXT("Down: the spectator camera takes the view"), D->IsSpectating() && Controller->GetViewTarget() == D->SpectatorCamera());
        // Advance checks on every frame that the camera follows the kernel's
        // recorded killer while that killer stands.
        bOk &= Test.TestTrue(TEXT("Down: a bot struck the player"), S.PlayerKiller > 0);
        if (K->PracticePlayers.IsValidIndex(S.PlayerKiller) && K->PracticePlayers[S.PlayerKiller].Alive)
            bOk &= Test.TestEqual(TEXT("Down: the camera follows the one who struck"), D->SpectatedSlot(), S.PlayerKiller);
        bOk &= Test.TestEqual(TEXT("Down: the choice starts at the current class"), D->DesiredClass(), 0);
        // The kernel's rules for the choice (combat-rules §10).
        bOk &= Test.TestTrue(TEXT("The admitted naginata is selectable for the Samurai"), D->CanSelectLoadout(0, 2));
        bOk &= Test.TestFalse(TEXT("Another class's special was not admitted"), D->CanSelectLoadout(2, 2));
        bOk &= Test.TestFalse(TEXT("Out-of-range choices are refused"), D->CanSelectLoadout(6, 0) || D->CanSelectLoadout(0, 3));
        // E turns to the next class and 2 picks its blade, through the player's own bindings.
        for (const FKey& Key : {EKeys::E, EKeys::Two})
        {
            S.World->InjectKey(Key, IE_Pressed);
            if (!Advance(Test, S, Context)) return false;
            S.World->InjectKey(Key, IE_Released);
            if (!Advance(Test, S, Context)) return false;
        }
        bOk &= Test.TestEqual(TEXT("E turns to the Shinobi"), D->DesiredClass(), 1);
        bOk &= Test.TestEqual(TEXT("2 picks the blade"), D->DesiredLoadout(), 1);
        bOk &= Test.TestTrue(TEXT("The kernel holds the Shinobi's kusarigama"), K->PracticePlayers[0].PendingClass == 1 && K->PracticePlayers[0].PendingWeapon == 2);
        // A later choice replaces it: the Teppo's wakizashi.
        bOk &= Test.TestTrue(TEXT("Teppo with the wakizashi is a valid choice"), D->SelectRespawnLoadout(2, 1));
        for (int32 Frame = 0; Frame < 3; ++Frame)
            if (!Advance(Test, S, Context)) return false;
        bOk &= Test.TestTrue(TEXT("The kernel holds the new choice"), K->PracticePlayers[0].PendingClass == 2 && K->PracticePlayers[0].PendingWeapon == 4);
        // Cycling moves to another standing bot whenever there is one.
        int32 Standing = 0;
        for (int32 Slot = 1; Slot < K->PracticePlayers.Num(); ++Slot) Standing += K->PracticePlayers[Slot].Alive ? 1 : 0;
        const int32 Watched = D->SpectatedSlot();
        D->CycleSpectator(1);
        const int32 Next = D->SpectatedSlot();
        bOk &= Test.TestTrue(TEXT("Cycling the camera stays among the living bots"), Next > 0 && K->PracticePlayers[Next].Alive);
        bOk &= Test.TestTrue(TEXT("Cycling the camera moves when another bot stands"), Standing < 2 || Next != Watched);
        D->CycleSpectator(-1);
        bOk &= Test.TestTrue(TEXT("Cycling back returns to the same bot"), Standing < 2 || D->SpectatedSlot() == Watched);
        return bOk || Fail(Test, S, Context + TEXT(": the respawn choice failed"));
    });
    Repeat(this, State, [Config](FAutomationTestBase& Test, FState& S, bool& bDone)
    {
        const UArenaKernelSubsystem* K = Kernel(S);
        for (int32 Frame = 0; Frame < 600 && !K->PracticePlayers[0].Alive; ++Frame)
            if (!Advance(Test, S, Describe(Config))) return false;
        bDone = K->PracticePlayers[0].Alive;
        return bDone || Fail(Test, S, TEXT("The player did not respawn within the kernel's 480 ticks"));
    });
    Step(this, State, [Config](FAutomationTestBase& Test, FState& S)
    {
        const UArenaKernelSubsystem* K = Kernel(S);
        const USoraPracticeDirector* D = Director(S);
        if (!Advance(Test, S, Describe(Config))) return false;
        const ASoraPlayerCharacter* Player = S.World->Player();
        const APlayerController* Controller = Cast<APlayerController>(Player->GetController());
        bool bOk = Test.TestTrue(TEXT("Returns as a Teppo with the wakizashi"), K->PracticePlayers[0].ClassId == 2 && K->PracticePlayers[0].WeaponId == 4);
        bOk &= Test.TestTrue(TEXT("The hero holds the kernel's new weapon"), Player->WeaponId == 4 && Player->ClassId == 2);
        bOk &= Test.TestTrue(TEXT("The pending choice is spent"), K->PracticePlayers[0].PendingClass == INDEX_NONE);
        bOk &= Test.TestTrue(TEXT("The player's own view returns"), !D->IsSpectating() && Controller->GetViewTarget() == Player);
        UE_LOG(LogTemp, Display, TEXT("SORA_PRACTICE_RESPAWN_OK: tick=%u class=%d weapon=%d"), K->PracticeTick, K->PracticePlayers[0].ClassId, K->PracticePlayers[0].WeaponId);
        return (Close(Test, S) && bOk) || Fail(Test, S, TEXT("The respawn loadout did not apply"));
    });
    return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraPracticeRefusedStepTest,
    "SoraArena.Practice.RefusedStepStops",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraPracticeRefusedStepTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraPracticeModes;
    // A tick the kernel refuses ends the session: closing the menu cannot
    // step on from an unverified state, and only Enter starts again.
    FSoraPracticeConfig Config;
    Config.PlayerCount = 4; Config.Difficulty = SoraPractice::BotStandard;
    const FStateRef State = MakeShared<FState>();
    Prepare(*this, State);
    Step(this, State, [](FAutomationTestBase& Test, FState& S) { return Open(Test, S); });
    Step(this, State, [Config](FAutomationTestBase& Test, FState& S)
    {
        if (!Begin(Test, S, Config, false)) return false;
        for (int32 Frame = 0; Frame < 30; ++Frame)
            if (!Advance(Test, S, Describe(Config))) return false;
        return true;
    });
    Step(this, State, [Config](FAutomationTestBase& Test, FState& S)
    {
        ASoraGameMode* M = Mode(S);
        UArenaKernelSubsystem* K = Kernel(S);
        // Button bit 10 is outside the canonical input (combat-rules §2.2).
        FSoraPracticeInput Bad;
        Bad.Buttons = 1u << 10;
        bool bOk = Test.TestFalse(TEXT("The kernel refuses a non-canonical input"), K->StepPractice(Bad));
        bOk &= Test.TestFalse(TEXT("A refused tick ends the session"), K->PracticeActive());
        bOk &= Test.TestTrue(TEXT("The refusal keeps its reason in both languages"), !K->PracticeError.IsEmpty() && !K->PracticeErrorEnglish.IsEmpty());
        bOk &= Test.TestTrue(TEXT("No state survives the refusal"), K->PracticeTick == 0 && K->PracticePlayers.IsEmpty());
        bOk &= Test.TestFalse(TEXT("The next step is refused too"), K->StepPractice(FSoraPracticeInput()));
        // As the director leaves it: the menu open with the reason. Resume
        // then closes the menu, and the frames after it must reopen it untouched.
        M->SetMenuOpen(true);
        M->ResumePlay();
        bOk &= Test.TestFalse(TEXT("Resume closes the menu"), M->bMenu);
        if (!S.World->Tick(3)) return Fail(Test, S, TEXT("The world failed to tick after the refusal"));
        bOk &= Test.TestTrue(TEXT("Closing the menu cannot resume a refused session"), M->bMenu && !K->PracticeActive() && K->PracticeTick == 0 && !K->PracticeError.IsEmpty());
        // Enter starts a fresh match, which plays on.
        M->BeginRound();
        bOk &= Test.TestTrue(TEXT("Enter starts a fresh match after a refusal"), K->PracticeActive() && K->PracticeTick == 0 && K->PracticeError.IsEmpty() && !M->bMenu);
        S.Before = K->PracticePlayers;
        for (int32 Frame = 0; Frame < 10; ++Frame)
            if (!Advance(Test, S, Describe(Config))) return false;
        UE_LOG(LogTemp, Display, TEXT("SORA_PRACTICE_REFUSAL_OK: tick=%u"), K->PracticeTick);
        return (Close(Test, S) && bOk) || Fail(Test, S, TEXT("A refused tick did not stop practice"));
    });
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraPracticeMarksTextTest,
    "SoraArena.Practice.MarksTextScoreboard",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraPracticeMarksTextTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraPracticeModes;
    // A 6-against-6 Control match at the Master tier: each side's marks, the
    // League's colours, every practice line in both languages, and the held
    // scoreboard.
    FSoraPracticeConfig Config;
    Config.Mode = SoraPractice::Control; Config.PlayerCount = 12; Config.MapId = 2; Config.ClassId = 4; Config.Difficulty = SoraPractice::BotMaster;
    const FStateRef State = MakeShared<FState>();
    Prepare(*this, State);
    Step(this, State, [](FAutomationTestBase& Test, FState& S) { return Open(Test, S) && S.World->EnableKeyInput(); });
    Step(this, State, [Config](FAutomationTestBase& Test, FState& S) { return Begin(Test, S, Config, false); });
    Step(this, State, [Config](FAutomationTestBase& Test, FState& S)
    {
        ASoraGameMode* M = Mode(S);
        const UArenaKernelSubsystem* K = Kernel(S);
        const USoraPracticeDirector* D = Director(S);
        // The imported SORA mon: one metre across, 1 cm thick, facing +X.
        const UStaticMesh* Mon = LoadObject<UStaticMesh>(nullptr, SoraPracticeArt::SoraMon);
        if (!Mon) return Fail(Test, S, TEXT("The SORA mon mesh is not imported; run scripts/unreal/import_sora_kamon_mon.py"));
        const FVector MonSize = Mon->GetBoundingBox().GetSize();
        bool bOk = Test.TestTrue(TEXT("The mon is imported at its authored size and facing"), MonSize.Equals(FVector(1, 100, 100), .05));
        // Upright: the ends of its top bar stand above the centre, as in the SVG.
        // A cooked game releases vertex positions after upload unless the mesh
        // allows CPU access, as the import makes the mon do; reading released
        // positions would read freed memory.
        bOk &= Test.TestTrue(TEXT("The mon keeps CPU-readable vertices, as imported"), Mon->bAllowCPUAccess);
        const FStaticMeshLODResources& Lod = Mon->GetRenderData()->LODResources[0];
        bool bBarEnd = false;
        for (uint32 Index = 0; Mon->bAllowCPUAccess && Index < Lod.VertexBuffers.PositionVertexBuffer.GetNumVertices() && !bBarEnd; ++Index)
        {
            const FVector3f P = Lod.VertexBuffers.PositionVertexBuffer.VertexPosition(Index);
            bBarEnd = FMath::IsNearlyEqual(FMath::Abs(P.Y), 30.56f, .1f) && FMath::IsNearlyEqual(P.Z, 24.92f, .1f);
        }
        bOk &= Test.TestTrue(TEXT("The mon stands upright with its bars above the centre"), bBarEnd);
        // Counts one actor's marks: SORA mons and ledger sigils.
        const auto Marks = [Mon](const AActor* Actor, int32& Mons, int32& Sigils, int32& Strokes)
        {
            Mons = Sigils = Strokes = 0;
            TInlineComponentArray<UActorComponent*> Parts(Actor);
            for (const UActorComponent* Part : Parts)
            {
                const auto* Mesh = Cast<UStaticMeshComponent>(Part);
                if (const auto* Tally = Cast<UInstancedStaticMeshComponent>(Part))
                    Sigils += Tally->GetName().Contains(TEXT("SigilTally")) && Tally->GetInstanceCount() == 70 ? 1 : 0;
                else if (Mesh && Mesh->GetStaticMesh() == Mon)
                    ++Mons;
                Strokes += Part->GetName().Contains(TEXT("Stroke")) ? 1 : 0;
            }
        };
        int32 Mons = 0, Sigils = 0, Strokes = 0;
        for (int32 Slot = 1; Slot < K->PracticePlayers.Num(); ++Slot)
        {
            const bool bLeague = D->IsSoraSide(Slot);
            Marks(D->Participant(Slot), Mons, Sigils, Strokes);
            bOk &= Test.TestTrue(*FString::Printf(TEXT("Slot %d (team %d) carries its side's mark and no redrawn strokes"), Slot, K->PracticePlayers[Slot].Team),
                Mons == (bLeague ? 1 : 0) && Sigils == (bLeague ? 0 : 1) && Strokes == 0 && bLeague == (K->PracticePlayers[Slot].Team == 0));
        }
        Marks(M->Hero(), Mons, Sigils, Strokes);
        bOk &= Test.TestTrue(TEXT("The hero's own banner carries one SORA mon"), Mons == 1 && Sigils == 0 && Strokes == 0);
        Marks(D->ControlPoint(), Mons, Sigils, Strokes);
        bOk &= Test.TestTrue(TEXT("The Control point holds one mon and one sigil for its owner"), Mons == 1 && Sigils == 1 && Strokes == 0);
        Marks(D->ModeDressing(), Mons, Sigils, Strokes);
        bOk &= Test.TestTrue(TEXT("Each League spawn pad carries the mon, each Credit House pad the sigil"),
            Mons == K->PracticeMap.TeamSpawns[0].Num() && Sigils == K->PracticeMap.TeamSpawns[1].Num() && Strokes == 0);
        // Cyan never marks the League: its colour and its tracers are vermillion.
        for (int32 Slot = 0; Slot < K->PracticePlayers.Num(); ++Slot)
            if (D->IsSoraSide(Slot))
            {
                const FLinearColor Tracer = D->TracerColor(Slot);
                bOk &= Test.TestTrue(*FString::Printf(TEXT("League slot %d fires vermillion, not cyan"), Slot), Tracer.R > 2.f * Tracer.B && Tracer.R > 2.f * Tracer.G);
            }
        bOk &= Test.TestTrue(TEXT("The ledger sigil is the Credit House's cyan"), SoraPracticeArt::LedgerCyan.B > 2.f * SoraPracticeArt::LedgerCyan.R);

        // Names: the lobby's modes and the story bible's sides.
        const auto Same = [&Test](const SoraPracticeText::FLine& Line, const TCHAR* Japanese, const TCHAR* English)
        {
            return Test.TestTrue(*FString::Printf(TEXT("%s is %s / %s"), *Line.Japanese, Japanese, English), Line.Japanese == Japanese && Line.English == English);
        };
        bOk &= Same(SoraPracticeText::ModeName(SoraPractice::FreeForAll), TEXT("乱戦"), TEXT("Free-for-all"));
        bOk &= Same(SoraPracticeText::ModeName(SoraPractice::Control), TEXT("拠点制圧"), TEXT("Control"));
        bOk &= Same(SoraPracticeText::ModeName(SoraPractice::Payload), TEXT("護送"), TEXT("Payload"));
        bOk &= Same(SoraPracticeText::ModeName(SoraPractice::Melee), TEXT("近接のみ"), TEXT("Melee only"));
        bOk &= Same(SoraPracticeText::SideName(0), TEXT("空紋一揆"), TEXT("The Sora League"));
        bOk &= Same(SoraPracticeText::SideName(1), TEXT("恒星信用院"), TEXT("The Stellar Credit House"));
        bOk &= Test.TestTrue(TEXT("The start notice names the mode in both languages"), M->Notice.Contains(TEXT("拠点制圧")) && M->NoticeEnglish.Contains(TEXT("Control")));
        // Every line has both languages, and the English carries no Japanese.
        int32 Lines = 0;
        const auto Bilingual = [&Test, &Lines](const SoraPracticeText::FLine& Line, const FString& What)
        {
            ++Lines;
            bool bJapaneseInEnglish = false;
            for (const TCHAR Char : Line.English) bJapaneseInEnglish |= (Char >= 0x3000 && Char < 0xA000) || (Char >= 0xFF00 && Char <= 0xFFEF);
            return Test.TestTrue(*FString::Printf(TEXT("%s: \"%s\" / \"%s\" is bilingual"), *What, *Line.Japanese, *Line.English),
                !Line.Japanese.IsEmpty() && !Line.English.IsEmpty() && !bJapaneseInEnglish);
        };
        for (int32 Slot = 0; Slot < K->PracticePlayers.Num(); ++Slot)
        {
            const FSoraPracticePlayer& P = K->PracticePlayers[Slot];
            bOk &= Bilingual(SoraPracticeText::Participant(*K, Slot), TEXT("Participant"));
            for (const bool bTeams : {true, false}) bOk &= Bilingual(SoraPracticeText::SeatSide(P, Slot, bTeams), TEXT("Side"));
            FSoraPracticePlayer Down = P;
            Down.Alive = false; Down.RespawnTicks = 300;
            bOk &= Bilingual(SoraPracticeText::SeatStatus(P), TEXT("Standing")) & Bilingual(SoraPracticeText::SeatStatus(Down), TEXT("Down"));
        }
        for (int32 Kind = FSoraPracticeFeedEntry::Kill; Kind <= FSoraPracticeFeedEntry::Winner; ++Kind)
            for (const int32 Weapon : {static_cast<int32>(INDEX_NONE), 5})
            {
                FSoraPracticeFeedEntry Entry;
                Entry.Kind = static_cast<FSoraPracticeFeedEntry::EKind>(Kind); Entry.Actor = 3; Entry.Target = 0; Entry.WeaponId = Weapon; Entry.Detail = 1;
                bOk &= Bilingual(SoraPracticeText::FeedLine(*K, Entry), FString::Printf(TEXT("Feed kind %d"), Kind));
            }
        for (int32 Class = 0; Class < SoraPractice::ClassCount; ++Class)
            for (int32 Index = 0; Index < 3; ++Index)
            {
                const SoraPracticeText::FLine Cell = SoraPracticeText::LoadoutCell(*D, Class, Index);
                bOk &= Bilingual(Cell, FString::Printf(TEXT("Loadout %d/%d"), Class, Index));
                // A refused choice says why in both languages.
                if (!D->CanSelectLoadout(Class, Index))
                    bOk &= Test.TestTrue(*FString::Printf(TEXT("Loadout %d/%d gives its reason"), Class, Index), Cell.Japanese.Contains(TEXT("（")) && Cell.English.Contains(TEXT("(")));
            }
        // The lobby's four tiers are the kernel's four; a fifth is refused.
        FSoraPracticeConfig Beyond = Config;
        Beyond.Difficulty = SoraPractice::BotCount;
        FString Why, WhyEnglish;
        bOk &= Test.TestEqual(TEXT("Four bot tiers"), static_cast<int32>(SoraPractice::BotCount), 4);
        bOk &= Test.TestTrue(TEXT("The Master tier is admitted"), K->ValidatePractice(Config));
        bOk &= Test.TestTrue(TEXT("A fifth tier is refused with its reason"), !K->ValidatePractice(Beyond, &Why, &WhyEnglish) && !Why.IsEmpty() && !WhyEnglish.IsEmpty());

        // The scoreboard shows while Tab (or the pad's View) is held.
        ASoraPlayerCharacter* Hero = S.World->Player();
        bOk &= Test.TestFalse(TEXT("No scoreboard until it is held"), D->ShowsScoreboard());
        for (const FKey& Key : {EKeys::Tab, EKeys::Gamepad_Special_Left})
        {
            S.World->InjectKey(Key, IE_Pressed);
            bOk &= Test.TestTrue(*(Key.ToString() + TEXT(" held shows the scoreboard")), Hero->IsScoreboardHeld() && D->ShowsScoreboard());
            S.World->InjectKey(Key, IE_Released);
            bOk &= Test.TestFalse(*(Key.ToString() + TEXT(" released hides it")), Hero->IsScoreboardHeld() || D->ShowsScoreboard());
        }
        // Its rows: every seat once, the League first, each team by kills then deaths.
        const TArray<int32> Order = SoraPracticeText::TableOrder(K->PracticePlayers, true);
        TSet<int32> Seen(Order);
        bOk &= Test.TestTrue(TEXT("The scoreboard lists every seat once"), Order.Num() == K->PracticePlayers.Num() && Seen.Num() == Order.Num());
        for (int32 Row = 1; Row < Order.Num(); ++Row)
        {
            const FSoraPracticePlayer& A = K->PracticePlayers[Order[Row - 1]];
            const FSoraPracticePlayer& B = K->PracticePlayers[Order[Row]];
            bOk &= Test.TestTrue(TEXT("Scoreboard rows run by team, kills, deaths"),
                A.Team < B.Team || (A.Team == B.Team && (A.Kills > B.Kills || (A.Kills == B.Kills && A.Deaths <= B.Deaths))));
        }
        UE_LOG(LogTemp, Display, TEXT("SORA_PRACTICE_MARKS_TEXT_OK: mon_vertices=%u lines=%d seats=%d"), Lod.GetNumVertices(), Lines, Order.Num());
        return (Close(Test, S) && bOk) || Fail(Test, S, TEXT("Marks, text or scoreboard failed"));
    });
    return true;
}
#endif
