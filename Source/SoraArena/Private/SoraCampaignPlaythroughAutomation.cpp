#include "SoraGameMode.h"
#include "SoraHelmAutomation.h"
#include "SoraRidgeAutomation.h"
#include "SoraClimbAutomation.h"
#include "SoraMoatAutomation.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "SoraAutomationWorld.h"
#include "SoraArmsRules.h"
#include "SoraBoss.h"
#include "SoraCampaignDirector.h"
#include "SoraCampaignRules.h"
#include "SoraCatalog.h"
#include "SoraDojoRules.h"
#include "SoraDojoAutomation.h"
#include "SoraMaaiAutomation.h"
#include "SoraArcheryAutomation.h"
#include "SoraRecoveryAutomation.h"
#include "SoraLiftAutomation.h"
#include "SoraFloodAutomation.h"
#include "SoraSpireAutomation.h"
#include "SoraSummitAutomation.h"
#include "SoraBulkheadAutomation.h"
#include "SoraCarryAutomation.h"
#include "SoraEnemy.h"
#include "SoraEnemyController.h"
#include "SoraEquipmentComponent.h"
#include "SoraFieldcraft.h"
#include "SoraGameEvents.h"
#include "SoraHorse.h"
#include "SoraInputStates.h"
#include "SoraPlayerCharacter.h"
#include "SoraSaveGame.h"
#include "SoraWorldBuilder.h"
#include "Camera/CameraActor.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/CapsuleComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/DamageType.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/AutomationTest.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "Templates/UniquePtr.h"
#include "Algo/AllOf.h"

// Plays every beat of all eight chapters' schema-4 data, the optional caches
// included, in real game worlds through the entry points the player's input
// reaches: BeginRound (Enter) opens chapters, skips cinematics (which play
// through their camera) and continues results; Interact (E) works each beat's
// points (objectives, crank turns in their rate band, pickups and deliveries,
// manufacturing strokes at each step's station), tacks up and mounts the horse
// from her right (the left is refused), picks up every loose collectible and
// opens every explore cache; the hero walks (is placed, or rides) onto points,
// into the volumes that release waves and beside an escorted party; the clock
// runs holds and survivals; lethal damage reaches OpponentDefeated; and the
// dojo forms are recorded. Every beat starts with the hero in its place (a
// travel cut), and every ride in the saddle.
// The disk save is read back at every checkpoint beat. In every chapter the
// first checkpoint of each task goal, and every boss and duel phase
// checkpoint, is restored in a fresh world (the old one torn down) and played
// on from there. A defeat, a lost sparring match, a lost defended target and a
// stealth alarm take their beats' failure paths; a hurried crank turn slips and
// an off-beat stroke restarts its rhythm. The 21 weapons and 19 mechanics must
// arrive in the order the chapters author them (bible §11); every arm Nyaakoto
// can hold is refused before its beat and equips in it; every collectible
// is kept through each reload and chapter advance; and the campaign ends
// liberated with everything. A second route enters the flagship without the
// skipped armory's phantom SMG, which the war council must grant. The
// director's telemetry for the run must record every beat completed once; its
// totals go to the log and to Saved/Telemetry/campaign_playthrough_totals.json.
// Combat balance is not under test here (see SoraArena.Campaign.CombatTrace):
// the hero is healed between actions so a long wave cannot end the run.
namespace SoraCampaignPlaythrough
{
constexpr int32 LastChapter = 7;
constexpr float FrameSeconds = 1.f / 60.f;
// Seconds per frame while no opponent stands: dialogue, holds and journeys.
constexpr float FastSeconds = .5f;
constexpr int32 MaxActionsPerBeat = 1000;
// The chapter the vault armory's phantom SMG (weapon 13) is granted in when
// the route skipped it.
constexpr int32 FlagshipChapter = 6;
constexpr int32 PhantomSmg = 13;

struct FState
{
    FString Slot = FSoraAutomationWorld::UniqueSaveSlot(TEXT("CampaignPlaythrough"));
    TUniquePtr<FSoraAutomationWorld> World;
    bool bAborted = false;
    int32 WorldsStarted = 0;
    int32 ChaptersCompleted = 0;
    int32 BeatsPlayed = 0;
    int32 CachesOpened = 0;
    // Caches whose opening saved a checkpoint, captured bosses, and whether a
    // fallen guard's patrol was seen to leave with it.
    int32 CacheCheckpoints = 0;
    int32 Captures = 0;
    bool bGuardForgotten = false;
    int32 PickupsFound = 0;
    int32 RidesRidden = 0;
    int32 CinematicShots = 0;
    int32 CheckpointsRead = 0;
    int32 LinesShown = 0;
    // Checkpoints restored in fresh worlds: at a beat's start, and at a later
    // boss or duel phase.
    int32 CheckpointReloads = 0;
    int32 PhaseReloads = 0;
    // Debt-bound conscripts knocked down, and those whose seal was cut.
    int32 ConscriptsDown = 0;
    int32 ConscriptsFreed = 0;
    // The escorted party's needs met by hand (cells opened, collars cut, the
    // downed raised) and parties sent on after hiding.
    int32 PartyTended = 0;
    int32 PartySentOn = 0;
    // Cook-fires relit by hand (ch03.b14), loads hoisted by a held hand
    // (ch03.b05) and objectives worked with Interact held (ch03.b10's charge
    // and fuse, ch06.b04's relay nodes, ch06.b11's presses).
    int32 FiresRelit = 0;
    int32 LoadsHoisted = 0;
    int32 ObjectivesHeld = 0;
    // Failures sent to the checkpoint, and matches retried in place.
    int32 Failures = 0;
    int32 InPlaceRetries = 0;
    // Holdable arms refused before their beat and equipped from it on; those
    // equipped in the very beat that hands them over, before it completes.
    int32 ArmsRefused = 0;
    int32 ArmsEquipped = 0;
    int32 ArmsInTheirBeat = 0;
    TSet<int32> ArmsLocked;
    TSet<int32> ArmsHeld;
    // Beats played per task goal (SoraBeatRules::EGoal).
    TMap<int32, int32> GoalsPlayed;
    // Chapter * 32 + goal of every checkpoint restored at a beat's start.
    TSet<int32> ReloadedGoals;
    // Unlocks seen so far, and each unlock as "id@beat" in the order it came.
    unsigned KnownWeapons = 0u;
    unsigned KnownMechanics = 0u;
    TArray<FString> WeaponOrder;
    TArray<FString> MechanicOrder;
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
ASoraPlayerCharacter* Player(const FState& State) { return State.World ? State.World->Player() : nullptr; }
USoraCampaignDirector* Campaign(const FState& State) { return Mode(State) ? Mode(State)->Campaign() : nullptr; }
const FSoraChapter& ChapterData(const FState& State) { return FSoraCatalog::Get().Chapter(Campaign(State)->ChapterId); }

TArray<ASoraEnemy*> LiveEnemies(const FState& State)
{
    TArray<ASoraEnemy*> Result;
    if (UWorld* World = State.World ? State.World->GetTestWorld() : nullptr)
        for (TActorIterator<ASoraEnemy> It(World); It; ++It)
            // Debt-bound conscripts fight beside a wave but never count toward it.
            if (It->IsEnemy() && It->IsAlive() && !It->IsNonlethal() && !It->IsActorBeingDestroyed())
                Result.Add(*It);
    return Result;
}

bool HasJapanese(const FString& Text)
{
    for (const TCHAR Character : Text)
        if (Character >= 0x3040 && Character <= 0x9FFF)
            return true;
    return false;
}

bool Paused(const FState& State)
{
    const UWorld* World = State.World ? State.World->GetTestWorld() : nullptr;
    return World && World->IsPaused();
}

FString Where(const FState& State)
{
    const USoraCampaignDirector* Director = Campaign(State);
    const FSoraBeat* Beat = Director ? Director->ActiveBeatData() : nullptr;
    return FString::Printf(TEXT("Chapter %d %s"), Director ? Director->ChapterId + 1 : 0, Beat ? *Beat->Id : TEXT("(no beat)"));
}

// Every collectible of every chapter, as the save keeps them.
unsigned long long AllCollectibles()
{
    unsigned long long Mask = 0ull;
    for (int32 Chapter = 0; Chapter <= LastChapter; ++Chapter)
        for (const FSoraCollectible& Item : FSoraCatalog::Get().Chapter(Chapter).Collectibles)
            Mask |= SoraCampaignRules::CollectibleBit(Chapter, Item.MaskBit);
    return Mask;
}

// A campaign arm Nyaakoto takes up in play: every one of the 21, each on its
// group key and the arms wheel (SoraArmsRules.h). In chapter one he trains
// with the bokken, so arms are gated from chapter two.
bool Holdable(int32 WeaponId)
{
    return WeaponId >= 0 && WeaponId < SoraArmsRules::ArmsCount;
}

// The unlocks as the chapters author them, in beat order (bible §11): each
// weapon or mechanic once, at the first beat that unlocks or grants it.
TArray<FString> AuthoredUnlocks(bool bWeapons)
{
    TArray<FString> Order;
    unsigned Seen = 0u;
    const int32 Count = bWeapons ? SoraBeatRules::WeaponCount : SoraBeatRules::MechanicCount;
    for (int32 Chapter = 0; Chapter <= LastChapter; ++Chapter)
    {
        const FSoraChapter& Data = FSoraCatalog::Get().Chapter(Chapter);
        for (int32 Index = 0; Index < Data.Rules.Num(); ++Index)
        {
            const SoraBeatRules::FBeat& Rule = Data.Rules[Index];
            const unsigned Mask = (bWeapons ? Rule.WeaponsMask | Rule.GrantsMask : Rule.MechanicsMask) & ~Seen;
            for (int32 Bit = 0; Bit < Count; ++Bit)
                if ((Mask & (1u << Bit)) != 0u)
                    Order.Add(FString::Printf(TEXT("%d@%s"), Bit, *Data.Beats[Index].Id));
            Seen |= Mask;
        }
    }
    return Order;
}

// The holdable arms unlocked after the dojo, each checked once on either side of its beat.
int32 GatedArms()
{
    int32 Count = 0;
    unsigned Seen = FSoraCatalog::Get().EarlierWeapons(1);
    for (int32 Chapter = 1; Chapter <= LastChapter; ++Chapter)
        for (const SoraBeatRules::FBeat& Rule : FSoraCatalog::Get().Chapter(Chapter).Rules)
        {
            const unsigned Mask = (Rule.WeaponsMask | Rule.GrantsMask) & ~Seen;
            for (int32 Id = 0; Id < SoraBeatRules::WeaponCount; ++Id)
                Count += (Mask & (1u << Id)) != 0u && Holdable(Id);
            Seen |= Mask;
        }
    return Count;
}

// Records the weapons and mechanics unlocked since the last look by the beat
// that just completed (Rule): exactly its own new ones, and none lost.
bool NoteUnlocks(FAutomationTestBase& Test, FState& State, const FString& BeatId, const SoraBeatRules::FBeat& Rule)
{
    const SoraBeatRules::FProgress& Progress = Campaign(State)->Progress();
    if (!Test.TestTrue(*(BeatId + TEXT(": no unlock is ever lost")), (Progress.WeaponsMask & State.KnownWeapons) == State.KnownWeapons &&
        (Progress.MechanicsMask & State.KnownMechanics) == State.KnownMechanics))
        return Fail(Test, State, BeatId + TEXT(" lost an unlock"));
    if (!Test.TestEqual(*(BeatId + TEXT(" unlocks exactly its own weapons")), Progress.WeaponsMask & ~State.KnownWeapons,
            (Rule.WeaponsMask | Rule.GrantsMask) & ~State.KnownWeapons) ||
        !Test.TestEqual(*(BeatId + TEXT(" unlocks exactly its own mechanics")), Progress.MechanicsMask & ~State.KnownMechanics,
            Rule.MechanicsMask & ~State.KnownMechanics))
        return Fail(Test, State, BeatId + TEXT(" unlocked what another beat gives"));
    for (int32 Id = 0; Id < SoraBeatRules::WeaponCount; ++Id)
        if ((Progress.WeaponsMask & ~State.KnownWeapons & (1u << Id)) != 0u)
            State.WeaponOrder.Add(FString::Printf(TEXT("%d@%s"), Id, *BeatId));
    for (int32 Bit = 0; Bit < SoraBeatRules::MechanicCount; ++Bit)
        if ((Progress.MechanicsMask & ~State.KnownMechanics & (1u << Bit)) != 0u)
            State.MechanicOrder.Add(FString::Printf(TEXT("%d@%s"), Bit, *BeatId));
    State.KnownWeapons = Progress.WeaponsMask;
    State.KnownMechanics = Progress.MechanicsMask;
    return true;
}

bool Advance(FAutomationTestBase& Test, FState& State, int32 Frames = 2, float DeltaSeconds = FrameSeconds)
{
    for (int32 Frame = 0; Frame < Frames; ++Frame)
    {
        if (!State.World->Tick(1, DeltaSeconds))
        {
            State.World->ForwardErrorMessages(&Test);
            return Fail(Test, State, TEXT("Campaign world failed to tick"));
        }
        ASoraPlayerCharacter* Hero = Player(State);
        if (!Mode(State) || !Hero)
            return Fail(Test, State, TEXT("Campaign world lost its game mode or player"));
        if (Mode(State)->bDefeated)
            return Fail(Test, State, Where(State) + TEXT(": the hero was defeated unexpectedly"));
        if (Hero->Health < Hero->MaxHealth * .5f)
            Hero->Heal(Hero->MaxHealth);
    }
    return true;
}

// Observe real blocking dialogue before the next gameplay action. Never clear
// or skip the queue: the director must release control within its authored cap.
bool WaitForDialogue(FAutomationTestBase& Test,FState& State)
{
    for(int32 Frame=0;Campaign(State)->IsDialogueBlocking()&&Frame<202;++Frame)
    {
        if(!Test.TestNotNull(TEXT("A blocking scene keeps its subtitle cue"),Campaign(State)->CurrentDialogueCue())||
            !Advance(Test,State,1,.1f)) return false;
        ++State.LinesShown;
    }
    return !Campaign(State)->IsDialogueBlocking()||Fail(Test,State,Where(State)+TEXT(": dialogue held control past twenty seconds"));
}

// Places the hero on the floor at Location; a mounted hero rides there (the
// horse is placed and carries him).
void MoveTo(FState& State, const FVector& Location)
{
    USoraCampaignDirector* Director = Campaign(State);
    if (Director && Director->IsMounted())
    {
        Director->Steed()->Place(FVector(Location.X, Location.Y, 0.f), Director->Steed()->GetActorRotation().Yaw);
        return;
    }
    ASoraPlayerCharacter* Hero = Player(State);
    Hero->GetCharacterMovement()->StopMovementImmediately();
    // Flat-floor fixture positioning. The spiral, lift and gallery stair
    // use ordinary movement helpers; summit combat stays at its real Z.
    const float Half = Hero->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    const auto* Beat=Director?Director->ActiveBeatData():nullptr;
    const float Floor=Beat&&Beat->Space.Summit.Enabled()?Beat->Space.HeightCm:0.f;
    Hero->SetActorLocation(FVector(Location.X, Location.Y, Floor+Half+2.f), false, nullptr, ETeleportType::TeleportPhysics);
}

// Every checkpoint beat writes the slot as it starts, and a long boss or duel
// at each later phase; read it back from disk.
bool ExpectCheckpoint(FAutomationTestBase& Test, FState& State)
{
    const USoraCampaignDirector* Director = Campaign(State);
    const USoraSaveGame* Saved = Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(State.Slot, 0));
    const FString Context = Where(State) + TEXT(" checkpoint");
    if (!Test.TestNotNull(*(Context + TEXT(": written to the isolated slot")), Saved))
        return Fail(Test, State, Context + TEXT(": no saved checkpoint"));
    const SoraBeatRules::FProgress& Progress = Director->Progress();
    const int32 Lessons = Director->ChapterId == 0 ? (1 << Director->DojoLessonStage()) - 1 : 0;
    bool bOk = Test.TestEqual(*(Context + TEXT(": schema")), Saved->SaveSchema, USoraSaveGame::Schema);
    bOk &= Test.TestEqual(*(Context + TEXT(": current chapter")), Saved->CurrentChapter, Director->ChapterId);
    bOk &= Test.TestEqual(*(Context + TEXT(": checkpoint chapter")), Saved->CheckpointChapter, Director->ChapterId);
    bOk &= Test.TestEqual(*(Context + TEXT(": beat")), Saved->CheckpointBeat, Director->ActiveBeat());
    bOk &= Test.TestEqual(*(Context + TEXT(": phase")), Saved->CheckpointPhase, Director->ActivePhase());
    bOk &= Test.TestEqual(*(Context + TEXT(": beats done")), Saved->CheckpointBeatsMask, static_cast<int32>(Progress.CompletedMask));
    bOk &= Test.TestEqual(*(Context + TEXT(": sites")), Saved->CheckpointSitesMask, static_cast<int32>(Progress.SitesMask));
    bOk &= Test.TestEqual(*(Context + TEXT(": weapons")), Saved->CheckpointWeapons, static_cast<int32>(Progress.WeaponsMask));
    bOk &= Test.TestEqual(*(Context + TEXT(": mechanics")), Saved->CheckpointMechanics, static_cast<int32>(Progress.MechanicsMask));
    bOk &= Test.TestEqual(*(Context + TEXT(": story flags")), Saved->CheckpointFlags, static_cast<int32>(Progress.FlagsMask));
    bOk &= Test.TestEqual(*(Context + TEXT(": dojo forms")), Saved->CheckpointDojoLessonMask, Lessons);
    bOk &= Test.TestEqual(*(Context + TEXT(": collectibles")), static_cast<uint64>(Saved->Collectibles), static_cast<uint64>(Director->CollectedMask()));
    bOk &= Test.TestEqual(*(Context + TEXT(": Nyaakoto remains the campaign class")), Saved->SelectedClass, 0);
    ++State.CheckpointsRead;
    return bOk || Fail(Test, State, Context + TEXT(" disagrees with the live beat"));
}

// Lethal damage from the hero goes through ASoraCharacterBase::TakeDamage and
// SoraDamage::Resolve to ASoraEnemy::OnDefeated, the only caller of
// OpponentDefeated in play.
bool DefeatOne(FAutomationTestBase& Test, FState& State)
{
    if(!WaitForDialogue(Test,State)) return false;
    ASoraPlayerCharacter* Hero = Player(State);
    const TArray<ASoraEnemy*> Enemies = LiveEnemies(State);
    if (Enemies.IsEmpty())
        return Fail(Test, State, Where(State) + FString::Printf(TEXT(" has no live opponent at %d/%d defeats"),
            Campaign(State)->Kills, Campaign(State)->KillsNeeded));
    ASoraEnemy* Target = Enemies[0];
    const int32 Before = Campaign(State)->Kills;
    const int32 Beat = Campaign(State)->ActiveBeat();
    UGameplayStatics::ApplyDamage(Target, Target->Health, Hero->GetController(), Hero, UDamageType::StaticClass());
    if (!Test.TestFalse(TEXT("A defeated opponent is no longer alive"), Target->IsAlive()) ||
        (Campaign(State)->ActiveBeat() == Beat && !Test.TestEqual(TEXT("OpponentDefeated records one defeat"), Campaign(State)->Kills, Before + 1)))
        return Fail(Test, State, Where(State) + TEXT(": a defeat was not recorded"));
    return Advance(Test, State);
}

// 活人剣: every debt-bound conscript on the field is knocked down, and once
// seal_cut is in play (from the beat that teaches it) its seal is cut with
// Interact held beside it, so none contests a hold or rises to fight again.
bool FreeConscripts(FAutomationTestBase& Test, FState& State)
{
    if(!WaitForDialogue(Test,State)) return false;
    const bool bLearned = Campaign(State)->IsMechanicInPlay(TEXT("seal_cut"));
    UWorld* World = State.World ? State.World->GetTestWorld() : nullptr;
    for (int32 Round = 0; World && Round < 16; ++Round)
    {
        ASoraEnemy* Conscript = nullptr;
        for (TActorIterator<ASoraEnemy> It(World); It && !Conscript; ++It)
            if (It->IsEnemy() && It->IsNonlethal() && !It->IsActorBeingDestroyed() && (It->IsAlive() || (bLearned && It->CanCutSeal())))
                Conscript = *It;
        if (!Conscript)
            return true;
        if (Conscript->IsAlive())
        {
            ASoraPlayerCharacter* Hero = Player(State);
            UGameplayStatics::ApplyDamage(Conscript, Conscript->Health, Hero->GetController(), Hero, UDamageType::StaticClass());
            if (!Test.TestTrue(TEXT("A lethal blow only knocks a conscript down"), Conscript->IsSubdued() && !Conscript->IsAlive()))
                return Fail(Test, State, Where(State) + TEXT(": a conscript was not knocked down"));
            ++State.ConscriptsDown;
        }
        if (!bLearned)
            continue;
        MoveTo(State, Conscript->GetActorLocation());
        State.World->InjectKey(EKeys::E, IE_Pressed);
        const bool bHeld = Advance(Test, State, 5, .4f);
        State.World->InjectKey(EKeys::E, IE_Released);
        if (!bHeld || !Advance(Test, State, 1))
            return false;
        if (!Test.TestTrue(TEXT("Interact held beside a knocked-down conscript cuts its seal"), Conscript->IsFreed()))
            return Fail(Test, State, Where(State) + TEXT(": a conscript's seal was not cut"));
        ++State.ConscriptsFreed;
    }
    return true;
}

// The escorted party (USoraFieldcraft) walks only whole: a cell door opened,
// a collar cut or a downed member raised, each with Interact held beside it,
// and a party that dropped at a patrol's alarm sent on with the signal.
bool TendParty(FAutomationTestBase& Test, FState& State)
{
    USoraFieldcraft* Fieldcraft = USoraFieldcraft::Get(Player(State));
    if (!Fieldcraft || !Fieldcraft->IsStaged()) return true;
    FVector Work;
    for (int32 Round = 0; Round < 32 && Fieldcraft->PartyWork(Work); ++Round)
    {
        MoveTo(State, Work);
        State.World->InjectKey(EKeys::E, IE_Pressed);
        const bool bHeld = Advance(Test, State, 16, .25f);
        State.World->InjectKey(EKeys::E, IE_Released);
        if (!bHeld || !Advance(Test, State, 1))
            return false;
        FVector After;
        if (!Test.TestTrue(TEXT("Interact held at the escorted party's need meets it"), !Fieldcraft->PartyWork(After) || After != Work))
            return Fail(Test, State, Where(State) + TEXT(": the party's need was not met by hand"));
        ++State.PartyTended;
    }
    if (Fieldcraft->Readout(*Player(State)).bPartyHidden)
    {
        if (!State.World->PressKey(EKeys::Q) || Fieldcraft->Readout(*Player(State)).bPartyHidden)
            return Fail(Test, State, Where(State) + TEXT(": the hidden party did not answer the signal"));
        ++State.PartySentOn;
    }
    return true;
}

// A guttered cook-fire (ch03.b14) stops the kitchen until Interact held at
// it relights it.
bool TendFires(FAutomationTestBase& Test, FState& State)
{
    USoraFieldcraft* Fieldcraft = USoraFieldcraft::Get(Player(State));
    if (!Fieldcraft || !Fieldcraft->IsStaged() || !Fieldcraft->Active()->bFires) return true;
    USoraCampaignDirector* Director = Campaign(State);
    for (int32 Fire = 0; Fire < Fieldcraft->Active()->Fires.Points.Num(); ++Fire)
    {
        if (Fieldcraft->IsFireLit(Fire)) continue;
        // The hold waits while the fire is out, the hero in it or not.
        const int32 Before = Director->TaskProgress().Progress;
        if (!Advance(Test, State, 4, .25f))
            return false;
        if (!Test.TestEqual(TEXT("The kitchen waits while a cook-fire is out"), Director->TaskProgress().Progress, Before))
            return Fail(Test, State, Where(State) + TEXT(": the hold filled with a fire out"));
        MoveTo(State, Fieldcraft->FireLocation(Fire));
        State.World->InjectKey(EKeys::E, IE_Pressed);
        const bool bHeld = Advance(Test, State, 12, .25f);
        State.World->InjectKey(EKeys::E, IE_Released);
        if (!bHeld || !Advance(Test, State, 1))
            return false;
        if (!Test.TestTrue(TEXT("Interact held at a guttered cook-fire relights it"), Fieldcraft->IsFireLit(Fire)))
            return Fail(Test, State, Where(State) + TEXT(": the cook-fire was not relit"));
        ++State.FiresRelit;
    }
    return true;
}

// A load hoisted at its pickup (ch03.b05's 釣瓶): Interact held there takes it.
bool HoistLoad(FAutomationTestBase& Test, FState& State)
{
    USoraCampaignDirector* Director = Campaign(State);
    // The patrol that watches the well is dealt with first; the hoist waits while it looks.
    for (int32 Action = 0; Action < MaxActionsPerBeat && !LiveEnemies(State).IsEmpty(); ++Action)
        if (!DefeatOne(Test, State))
            return false;
    // The well's debt-bound conscript is also a guard, but is deliberately
    // absent from LiveEnemies' lethal kill count. Subdue and, when taught,
    // free it through the same play path as the other guarded work.
    if (!FreeConscripts(Test, State))
        return false;
    FVector Anchor;
    if (!Director->ObjectiveAnchor(Anchor))
        return Fail(Test, State, Where(State) + TEXT(": no pickup to hoist at"));
    MoveTo(State, Anchor);
    if (!Advance(Test, State, 1))
        return false;
    State.World->InjectKey(EKeys::E, IE_Pressed);
    bool bHeld = Advance(Test, State, 1, FrameSeconds);
    const bool bStarted = Director->HeldWorkProgress() >= 0.f && !Director->TaskProgress().Carrying;
    bHeld = bHeld && Advance(Test, State, 14, .25f);
    State.World->InjectKey(EKeys::E, IE_Released);
    if (!bHeld || !Advance(Test, State, 1))
        return false;
    if (!Test.TestTrue(TEXT("A load is hoisted with Interact held, not at a press"), bStarted && Director->TaskProgress().Carrying))
        return Fail(Test, State, Where(State) + FString::Printf(TEXT(": the load was not hoisted (started=%d, carrying=%d, watched=%d, held=%.3f)"),
            bStarted, Director->TaskProgress().Carrying, Director->IsHeldWorkWatched(), Director->HeldWorkProgress()));
    ++State.LoadsHoisted;
    return true;
}

// A spot on the active beat's floor away from every point it works: its
// place's entry, or the arena's west lawn in the hub.
FVector FarAway(const FState& State)
{
    const FSoraBeatSpace* Space = Campaign(State)->ActiveSpace();
    return Space && Space->Zone != INDEX_NONE ? ASoraWorldBuilder::Floor(Space->Entry) : FVector(-2700, 1800, 0);
}

// Every live opponent falls, one lethal blow at a time, while Beat is active.
bool ClearField(FAutomationTestBase& Test, FState& State, int32 Beat)
{
    for (int32 Action = 0; Action < MaxActionsPerBeat; ++Action)
    {
        if (Campaign(State)->ActiveBeat() != Beat || Mode(State)->bChapterComplete || LiveEnemies(State).IsEmpty())
            return true;
        if (!DefeatOne(Test, State))
            return false;
    }
    return Fail(Test, State, Where(State) + TEXT(": the field never cleared"));
}

// Advances the beat clock by Milliseconds in frames of at most half a second.
bool Wait(FAutomationTestBase& Test, FState& State, int32 Milliseconds)
{
    const int32 Frames = FMath::Max(1, FMath::DivideAndRoundUp(Milliseconds, 500));
    return Advance(Test, State, Frames, Milliseconds / 1000.f / Frames);
}

// Walks (is placed) to the active objective and presses E there. An
// objective worked with Interact held (a charge planted, a relay node pulled)
// fills only while E stays down, so E is held until it is done.
bool WorkAtAnchor(FAutomationTestBase& Test, FState& State)
{
    if(!WaitForDialogue(Test,State)) return false;
    USoraCampaignDirector* Director = Campaign(State);
    FVector Anchor;
    if (!Director->ObjectiveAnchor(Anchor))
        return Fail(Test, State, Where(State) + TEXT(": no objective to work"));
    MoveTo(State, Anchor);
    if (!Advance(Test, State, 1))
        return false;
    if(Director->ActiveTask().AlternateTreads)
    {
        // The bellows wave nets the boy beside this station. Interact gives
        // that rescue priority, so finish its held cut before pumping again.
        // Leave the attacking wave alive: production still ends the beat.
        if(auto* Craft=USoraFieldcraft::Get(Player(State));
            Craft&&Craft->Readout(*Player(State)).HoldHere==FSoraFieldcraftReadout::EHold::NetCut)
        {
            const int32 NetsBefore=Craft->Readout(*Player(State)).NetsHeld;
            if(!State.World->InjectKey(EKeys::E,IE_Pressed)) return false;
            bool bHeld=true;
            for(int32 Frame=0;Frame<180&&bHeld&&Craft->Readout(*Player(State)).NetsHeld>=NetsBefore;++Frame)
                bHeld=Advance(Test,State,1);
            State.World->InjectKey(EKeys::E,IE_Released);
            if(!bHeld||!Test.TestTrue(TEXT("The bellows helper is released with a held net cut"),
                Craft->Readout(*Player(State)).NetsHeld<NetsBefore)||!Advance(Test,State,1)) return false;
            Test.AddInfo(TEXT("Cut the bellows helper's net through held input before resuming production."));
        }
        return State.World->InjectKey(EKeys::E,IE_Pressed)&&State.World->InjectKey(EKeys::A,IE_Pressed)&&
            State.World->InjectKey(EKeys::A,IE_Released)&&State.World->InjectKey(EKeys::D,IE_Pressed)&&
            State.World->InjectKey(EKeys::D,IE_Released)&&State.World->InjectKey(EKeys::E,IE_Released);
    }
    Mode(State)->Interact(Player(State));
    if (Director->HeldWorkProgress() < 0.f)
        return true;
    // Worked once its point is marked done, or the beat it finished has moved on.
    const int32 BeatBefore = Director->ActiveBeat();
    const unsigned Before = Director->TaskProgress().PointsMask;
    const int32 DeliveredBefore=Director->TaskProgress().Done;
    const auto Worked = [&]() { return Director->ActiveBeat() != BeatBefore || Director->TaskProgress().PointsMask != Before ||
        Director->TaskProgress().Done != DeliveredBefore; };
    State.World->InjectKey(EKeys::E, IE_Pressed);
    bool bHeld = true;
    for (int32 Quarter = 0; Quarter < 40 && bHeld && !Worked(); ++Quarter)
        bHeld = Advance(Test, State, 1, .25f);
    State.World->InjectKey(EKeys::E, IE_Released);
    if (!bHeld || !Advance(Test, State, 1))
        return false;
    if (!Test.TestTrue(TEXT("An objective with a hold is worked with Interact held"), Worked()))
        return Fail(Test, State, Where(State) + TEXT(": the held objective was not worked"));
    ++State.ObjectivesHeld;
    return true;
}

// Opens every explore cache the chapter offers now: its beat completes with
// its collectibles, weapons and story flags, none of them held before.
bool OpenCaches(FAutomationTestBase& Test, FState& State)
{
    USoraCampaignDirector* Director = Campaign(State);
    if (!Mode(State)->IsPlaying())
        return true;
    for (const int32 Cache : Director->AvailableCaches())
    {
        const FSoraChapter& Chapter = ChapterData(State);
        const FSoraBeat& Beat = Chapter.Beats[Cache];
        const SoraBeatRules::FBeat& Rule = Chapter.Rules[Cache];
        const uint64 Before = Director->CollectedMask();
        bool bOk = Test.TestTrue(*(Beat.Id + TEXT(": the cache's weapons and story flags wait for it")),
            (Director->Progress().WeaponsMask & Rule.WeaponsMask) == 0u && (Director->Progress().FlagsMask & Rule.FlagsMask) == 0u);
        MoveTo(State, Director->CacheLocation(Cache));
        Mode(State)->Interact(Player(State));
        bOk &= Test.TestTrue(*(Beat.Id + TEXT(" cache opened")), (Director->Progress().CompletedMask & SoraBeatRules::BeatBit(Cache)) != 0u);
        bOk &= Test.TestTrue(*(Beat.Id + TEXT(" cache weapons and story flags")),
            (Director->Progress().WeaponsMask & Rule.WeaponsMask) == Rule.WeaponsMask &&
            (Director->Progress().FlagsMask & Rule.FlagsMask) == Rule.FlagsMask);
        for (const int32 Item : Beat.Rewards)
            bOk &= Test.TestTrue(*FString::Printf(TEXT("%s holds %s"), *Beat.Id, *Chapter.Collectibles[Item].Id),
                (Director->CollectedMask() & SoraCampaignRules::CollectibleBit(Director->ChapterId, Chapter.Collectibles[Item].MaskBit)) != 0ull);
        bOk &= Test.TestTrue(TEXT("Opening a cache finds something new"), Director->CollectedMask() != Before || Rule.WeaponsMask != 0u);
        // The finds are kept at once. Where the active beat can be restored
        // from here, the cache's completion is a checkpoint too, so a
        // completist's detour never outruns the checkpoint spacing; otherwise
        // its completion reaches the next checkpoint.
        const USoraSaveGame* Saved = Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(State.Slot, 0));
        bOk &= Test.TestTrue(*(Beat.Id + TEXT(": its finds are saved at once")),
            Saved && static_cast<uint64>(Saved->Collectibles) == static_cast<uint64>(Director->CollectedMask()));
        const SoraBeatRules::FBeat& Active = Chapter.Rules[Director->ActiveBeat()];
        const int32 Phase = Director->ActivePhase();
        if (Rule.Checkpoint && (Phase == 0 ? Active.Checkpoint : Phase <= Active.PhaseCheckpoints))
        {
            bOk &= ExpectCheckpoint(Test, State);
            ++State.CacheCheckpoints;
        }
        else
            bOk &= Test.TestTrue(*(Beat.Id + TEXT(": no checkpoint is written where none restores")),
                Saved && (static_cast<unsigned>(Saved->CheckpointBeatsMask) & SoraBeatRules::BeatBit(Cache)) == 0u);
        if (!bOk)
            return Fail(Test, State, Beat.Id + TEXT(" cache did not open"));
        ++State.CachesOpened;
        ++State.GoalsPlayed.FindOrAdd(static_cast<int32>(SoraBeatRules::EGoal::Cache));
        if (!NoteUnlocks(Test, State, Beat.Id, Rule) || !Advance(Test, State))
            return false;
    }
    return true;
}

// Walks to every loose collectible and picks it up; each goes to the save.
bool PickUpAll(FAutomationTestBase& Test, FState& State,bool AlongMoatRoute=false)
{
    USoraCampaignDirector* Director = Campaign(State);
    const auto* Space=Director->ActiveSpace();
    const bool Moat=Space&&Space->Moat.bEnabled;
    if(Moat)SoraMoatAutomation::Sample(*State.World,TEXT("before aggregate pickup sweep"));
    if (!Mode(State)->IsPlaying() || Director->IsMounted())
        return true;
    // These physical routes must begin at their actual entry. The moat's
    // mark is reached during its gate approach; off-route chapter finds
    // stay loose until the later ordinary collection sweep after the climb.
    if((Moat&&!AlongMoatRoute)||(Space&&Space->Climb.bEnabled))return true;
    const FSoraChapter& Chapter = ChapterData(State);
    for (const int32 Pickup : Director->LoosePickups())
    {
        if(Moat&&Chapter.Space.Pickups[Pickup].Zone!=Space->Zone)continue;
        const FSoraCollectible& Item = Chapter.Collectibles[Chapter.Space.Pickups[Pickup].Collectible];
        if(Moat)
        {
            if(!SoraMoatAutomation::Swim(*State.World,Director->PickupLocation(Pickup)))
                return Fail(Test,State,TEXT("The moat mark must be reached by actual swimming"));
            SoraMoatAutomation::Sample(*State.World,TEXT("actual moat pickup approach"),Director->PickupLocation(Pickup));
            if(!State.World->PressKey(SoraMoatAutomation::Key(*Player(State),TEXT("Interact"))))return false;
        }
        else
        {
            MoveTo(State, Director->PickupLocation(Pickup));
            Mode(State)->Interact(Player(State));
        }
        const uint64 Bit = SoraCampaignRules::CollectibleBit(Director->ChapterId, Item.MaskBit);
        const USoraSaveGame* Saved = Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(State.Slot, 0));
        if (!Test.TestTrue(*(Item.Id + TEXT(" is picked up and kept at once")), (Director->CollectedMask() & Bit) != 0ull &&
            Saved && (static_cast<uint64>(Saved->Collectibles) & Bit) != 0ull && !Director->StoryNotices().IsEmpty()))
            return Fail(Test, State, Item.Id + TEXT(" could not be picked up"));
        ++State.PickupsFound;
        if (!Advance(Test, State))
            return false;
    }
    return true;
}

// The boss, or the duellist, of the active beat.
ASoraEnemy* PhasedOpponent(const FState& State)
{
    if (const ASoraBoss* Boss = Campaign(State)->CampaignBoss())
        return const_cast<ASoraBoss*>(Boss);
    const TArray<ASoraEnemy*> Enemies = LiveEnemies(State);
    return Enemies.IsEmpty() ? nullptr : Enemies[0];
}

// The lines an event's rows in Beat put in the dialogue queue.
bool ExpectLinesQueued(FAutomationTestBase& Test, FState& State, const FSoraChapter& Chapter, int32 Beat, const TCHAR* Event)
{
    const TArray<FSoraSubtitle> Queued = Campaign(State)->QueuedSubtitles();
    bool bOk = true;
    for (const FSoraDialogueTrigger& Row : Chapter.Triggers)
        if (Row.Beat == Beat && Row.On == Event)
            for (const int32 Line : Row.Lines)
                bOk &= Test.TestTrue(*FString::Printf(TEXT("%s plays on %s"), *Chapter.Dialogue[Line].Id, Event),
                    Queued.ContainsByPredicate([&](const FSoraSubtitle& Row) { return Row.LineId == Chapter.Dialogue[Line].Id; }));
    return bOk;
}

// A captured boss yields at zero health (bible §3.2: the final boss is
// captured, not killed): it kneels upright where it fell and stays past a
// fallen opponent's lifespan, and E from afar binds nothing. The final boss
// ends only after the hero walks to the spine and holds the draw-cut; the
// vault ends at its entry lever after a two-second held interaction.
bool CaptureYielded(FAutomationTestBase& Test, FState& State, const FSoraBeat& Beat)
{
    USoraCampaignDirector* Director = Campaign(State);
    ASoraEnemy* Captive = nullptr;
    if (UWorld* World = State.World->GetTestWorld())
        for (TActorIterator<ASoraEnemy> It(World); It; ++It)
            if (!It->IsAlive() && !It->IsActorBeingDestroyed() && Director->IsCaptive(**It))
                Captive = *It;
    const bool Spine=Beat.CaptureEvent==TEXT("interact:engine_spine");
    const bool Bulkhead=Beat.CaptureEvent==TEXT("interact:bulkhead_lever");
    FVector At;
    bool bOk = Test.TestNotNull(*(Beat.Id + TEXT(": the yielded boss stays where it fell")), Captive) &&
        Test.TestTrue(*(Beat.Id + TEXT(": the yielded boss kneels upright and does not leave")),
            FMath::Abs(Captive->GetActorRotation().Roll) < 1.f && Captive->GetLifeSpan() == 0.f) &&
        Test.TestTrue(*(Beat.Id + TEXT(": the authored capture interaction is the objective")),
            Director->ObjectiveAnchor(At) && Director->AnchorTakesInteract() && (Spine
                ?At.Equals(Mode(State)->Arena()->SummitSpinePoint(),1.f):
                Bulkhead&&At.Equals(Mode(State)->Arena()->BulkheadPoint(),1.f)));
    if (!bOk)
        return Fail(Test, State, Beat.Id + TEXT(": the captured boss did not yield"));
    // The bulkhead now stands beside the entry: that old "far away" point
    // is within reach. Keep the distant refusal case on clear hall floor.
    MoveTo(State, Bulkhead?Mode(State)->Arena()->BulkheadApproach()+FVector(600,0,0):FarAway(State));
    if (!Advance(Test, State, 150))
        return false;
    Mode(State)->Interact(Player(State));
    bOk &= Test.TestTrue(*(Beat.Id + TEXT(": E from afar binds nothing, and the captive waits")),
        Director->AwaitingCapture() && IsValid(Captive) && !Captive->IsActorBeingDestroyed());
    const int32 Index = Director->ActiveBeat();
    if(Spine)
    {
        if(!SoraSummitAutomation::CutSpine(*State.World)) return Fail(Test,State,TEXT("The held spine cut is unreachable or incomplete"));
    }
    else if(Bulkhead)
    {
        if(!SoraBulkheadAutomation::SealVault(*State.World)) return Fail(Test,State,TEXT("The held bulkhead lever is unreachable or incomplete"));
    }
    else return Fail(Test,State,TEXT("No authored held capture helper"));
    bOk &= Test.TestTrue(*(Beat.Id + TEXT(": the capture interaction ends the fight")),
        !Director->AwaitingCapture() && (Director->ActiveBeat() != Index || Mode(State)->bChapterComplete));
    bOk &= ExpectLinesQueued(Test, State, ChapterData(State), Index, *Beat.CaptureEvent);
    ++State.Captures;
    return (bOk || Fail(Test, State, Beat.Id + TEXT(": the yielded boss could not be captured"))) && Advance(Test, State, 1);
}

// Tacks up the ride's horse at her side (the bit refused until she has her
// barley), is refused from her left and mounts from her right.
bool MountUp(FAutomationTestBase& Test, FState& State, const FSoraBeat& Beat)
{
    USoraCampaignDirector* Director = Campaign(State);
    ASoraHorse* Horse = Director->Steed();
    if (!Test.TestNotNull(*(Beat.Id + TEXT(" has its horse")), Horse))
        return Fail(Test, State, Beat.Id + TEXT(" has no horse"));
    const FVector Right = Horse->GetActorLocation() + Horse->GetActorRightVector() * 120.f;
    const FVector Left = Horse->GetActorLocation() - Horse->GetActorRightVector() * 120.f;
    const TArray<FSoraTackStep>& Tack = Beat.Space.Mount.Tack;
    int32 Presses = 0;
    for (; Presses < 16 && Director->TackDone() < Tack.Num(); ++Presses)
    {
        MoveTo(State, Right);
        Mode(State)->Interact(Player(State));
    }
    int32 Refusals = 0;
    for (const FSoraTackStep& Step : Tack)
        Refusals += Step.Refusals;
    bool bOk = Test.TestEqual(*(Beat.Id + TEXT(": every piece of tack, the bit after its refusals")), Presses, Tack.Num() + Refusals);
    MoveTo(State, Left);
    Mode(State)->Interact(Player(State));
    bOk &= Test.TestTrue(*(Beat.Id + TEXT(": mounting from her left is refused")), !Director->IsMounted() && Mode(State)->NoticeTime > 0.f);
    MoveTo(State, Right);
    Mode(State)->Interact(Player(State));
    bOk &= Test.TestTrue(*(Beat.Id + TEXT(": the hero mounts from her right")), Director->IsMounted());
    return (bOk || Fail(Test, State, Beat.Id + TEXT(" could not be mounted"))) && Advance(Test, State);
}

bool RecordLessons(FAutomationTestBase& Test, FState& State, const FSoraBeat& Beat, bool bFirst)
{
    USoraCampaignDirector* Director = Campaign(State);
    using SoraDojoRules::EAction;
    bool bOk = true;
    if (bFirst)
    {
        // Pupils cannot be scored and forms cannot be skipped before they are taught.
        const TArray<ASoraEnemy*> Pupils = LiveEnemies(State);
        if (Pupils.IsEmpty())
            return Fail(Test, State, TEXT("The dojo has no sparring pupil"));
        UGameplayStatics::ApplyDamage(Pupils[0], Pupils[0]->Health, Player(State)->GetController(), Player(State), UDamageType::StaticClass());
        bOk &= Test.TestTrue(TEXT("An untrained strike leaves the pupil standing"), Pupils[0]->IsAlive() && Director->Kills == 0);
        bOk &= Test.TestFalse(TEXT("The guard form waits for its own duel"), Director->RecordDojoLesson(EAction::Guard, SoraDojoRules::GuardHoldMs));
        bOk &= Test.TestFalse(TEXT("A short stance is rejected"), Director->RecordDojoLesson(EAction::Stance, SoraDojoRules::StanceHoldMs - 1));
    }
    for (int32 Stage = 0; Stage < 4; ++Stage)
    {
        if ((Beat.Task.LessonMask & (1u << Stage)) == 0u)
            continue;
        switch (static_cast<EAction>(Stage))
        {
        case EAction::Stance:
            bOk &= Test.TestTrue(TEXT("Stance"), Director->RecordDojoLesson(EAction::Stance, SoraDojoRules::StanceHoldMs));
            break;
        case EAction::Guard:
            bOk &= Test.TestFalse(TEXT("Guard must face the attacker"), Director->RecordDojoLesson(EAction::Guard, SoraDojoRules::GuardHoldMs, false));
            bOk &= Test.TestTrue(TEXT("Guard"), Director->RecordDojoLesson(EAction::Guard, SoraDojoRules::GuardHoldMs));
            break;
        case EAction::Parry:
            bOk &= Test.TestFalse(TEXT("A late parry is rejected"), Director->RecordDojoLesson(EAction::Parry, SoraDojoRules::ParryWindowMs + 1));
            // awase ×2 (ch01.b03): each clean awase counts; the form is learned on the last.
            for (int32 Rep = 1; Rep <= Beat.Task.FormReps[Stage]; ++Rep)
            {
                bOk &= Test.TestTrue(TEXT("Parry"), Director->RecordDojoLesson(EAction::Parry, SoraDojoRules::ParryWindowMs));
                bOk &= Test.TestEqual(TEXT("The awase form is learned on its last repetition"), Director->DojoLessonStage(),
                    Rep < Beat.Task.FormReps[Stage] ? Stage : Stage + 1);
            }
            break;
        case EAction::Recovery:
            bOk &= Test.TestFalse(TEXT("Recovery needs a committed swing"), Director->RecordDojoLesson(EAction::Recovery, 500, true, 0));
            bOk &= Test.TestTrue(TEXT("Recovery"), Director->RecordDojoLesson(EAction::Recovery, 500, true, 450));
            break;
        }
    }
    if(Beat.Task.Maai.Count>0)
    {
        // The completist sweep visits loose collectibles in other zones.
        // Return to this beat's authored entrance before the real-input
        // lesson; never place the hero inside its measured distance band.
        MoveTo(State,ASoraWorldBuilder::Floor(Beat.Space.Entry));
        if(!Advance(Test,State,1)) return false;
        bOk &= Test.TestTrue(TEXT("The dojo entrance is outside the distance band"),Director->MaaiDistance()>Beat.Task.Maai.OuterCm);
        bOk &= Test.TestFalse(TEXT("Returning from collectibles grants no distance confirmation"),Director->TaskProgress().Maai.Acquired);
        bOk &= Test.TestTrue(TEXT("The distance lesson requires walking after every mentor step"),SoraMaaiAutomation::Walk(*State.World));
    }
    return bOk || Fail(Test, State, Beat.Id + TEXT(": Nyaagyushinkageryuu forms did not follow the dojo rules"));
}

// The hero's 転 as the combat lane reports it: a roll to the pupil's flank
// straight after an awase on it.
void RollToFlank(FState& State)
{
    const TArray<ASoraEnemy*> Pupils = LiveEnemies(State);
    if (USoraGameEvents* Events = USoraGameEvents::Get(Player(State)); Events && !Pupils.IsEmpty())
    {
        FSoraMarobashiEvent Rolled;
        Rolled.Hero = Player(State); Rolled.Opponent = Pupils[0]; Rolled.bAfterAwase = true;
        Events->OnMarobashi.Broadcast(Rolled);
    }
}

// A 転 lesson (ch01.b04) scores a bout only straight after a flank: an awase
// left without the step draws the master's "do not stop", and a bout won
// without the flank scores nothing and a fresh pupil steps in.
bool MissFlank(FAutomationTestBase& Test, FState& State, const FSoraBeat& Beat)
{
    USoraCampaignDirector* Director = Campaign(State);
    const TArray<ASoraEnemy*> Pupils = LiveEnemies(State);
    if (Pupils.IsEmpty())
        return Fail(Test, State, Beat.Id + TEXT(" has no pupil to meet"));
    if (!SoraDojoAutomation::MissFlank(Test,*State.World))
        return false;
    const int32 Index = Director->ActiveBeat();
    bool bOk = ExpectLinesQueued(Test, State, ChapterData(State), Index, TEXT("marobashi_miss"));
    UGameplayStatics::ApplyDamage(Pupils[0], Pupils[0]->Health, Player(State)->GetController(), Player(State), UDamageType::StaticClass());
    if (!Advance(Test, State))
        return false;
    bOk &= Test.TestTrue(*(Beat.Id + TEXT(": a bout won without the flank scores nothing, and a fresh pupil steps in")),
        Director->ActiveBeat() == Index && Director->TaskProgress().Done == 0 && !LiveEnemies(State).IsEmpty());
    return bOk || Fail(Test, State, Beat.Id + TEXT(": a bout scored without 転"));
}

// The sparring match (ch01.b11): a fallen hero is the rival's point, three
// of them lose the match, and a lost match starts over in place with its
// loss counted; then the hero wins it.
bool LoseMatch(FAutomationTestBase& Test, FState& State)
{
    USoraCampaignDirector* Director = Campaign(State);
    const int32 Beat = Director->ActiveBeat();
    const SoraBeatRules::FTask Rules = Director->ActiveTask();
    for (int32 Point = 0; Point < Rules.Count; ++Point)
    {
        const TArray<ASoraEnemy*> Rivals = LiveEnemies(State);
        ASoraPlayerCharacter* Hero = Player(State);
        UGameplayStatics::ApplyDamage(Hero, Hero->Health, nullptr, Rivals.IsEmpty() ? nullptr : Rivals[0], UDamageType::StaticClass());
        if (!Test.TestFalse(TEXT("A lost sparring bout is no defeat"), Mode(State)->bDefeated))
            return Fail(Test, State, TEXT("The sparring match treated a lost bout as a defeat"));
    }
    ++State.InPlaceRetries;
    const SoraBeatRules::FTaskState& After = Director->TaskProgress();
    bool bOk = Test.TestEqual(TEXT("The lost match restarts in place"), Director->ActiveBeat(), Beat);
    bOk &= Test.TestEqual(TEXT("The lost match is counted"), After.Losses, 1);
    bOk &= Test.TestTrue(TEXT("The restarted match has no points"), After.RivalPoints == 0 && After.Done == 0);
    bOk &= Test.TestTrue(TEXT("The hero stands to go again"), Player(State)->IsAlive() && Player(State)->Health == Player(State)->MaxHealth);
    bOk &= Test.TestFalse(TEXT("The rival is back on the floor"), LiveEnemies(State).IsEmpty());
    return (bOk || Fail(Test, State, TEXT("The lost sparring match did not retry in place"))) && Advance(Test, State);
}

// Plays the active beat to its completion through the entry points its task
// uses, then checks the beat's site, unlocks and the next beat's checkpoint.
bool PlayBeat(FAutomationTestBase& Test, FState& State)
{
    using SoraBeatRules::EGoal;
    ASoraGameMode* GameMode = Mode(State);
    USoraCampaignDirector* Director = Campaign(State);
    const FSoraChapter& Chapter = ChapterData(State);
    const int32 Index = Director->ActiveBeat();
    if (!Chapter.Beats.IsValidIndex(Index))
        return Fail(Test, State, Where(State) + TEXT(": no active beat"));
    const FSoraBeat& Beat = Chapter.Beats[Index];
    const SoraBeatRules::FBeat& Rule = Chapter.Rules[Index];
    // This beat's task, kept as the director moves on to the next beat.
    const SoraBeatRules::FTask Rules = Director->ActiveTask();
    const auto Active = [&]() { return Director->ActiveBeat() == Index && !GameMode->bChapterComplete; };
    FVector Anchor;
    bool bOk = true;
    if(Rules.Goal!=EGoal::Lines&&Rules.Goal!=EGoal::Elapsed&&!WaitForDialogue(Test,State)) return false;
    switch (Rules.Goal)
    {
    case EGoal::Elapsed:
    {
        bOk &= Test.TestTrue(*(Beat.Id + TEXT(" plays on the card")), GameMode->InputState() == SoraInput::Card &&
            GameMode->TitleCardChapter() == &Chapter && GameMode->TitleCardTime > 0.f && LiveEnemies(State).IsEmpty());
        bOk &= Test.TestTrue(*(Beat.Id + TEXT(" is skippable")), Rules.Skippable);
        // The shot blends in from the hero's eye to the cinematic's camera over its place.
        if (!Advance(Test, State, 1))
            return false;
        const APlayerController* Controller = Cast<APlayerController>(Player(State)->GetController());
        const AActor* Shot = Director->CinematicCamera();
        const auto Viewing = [&](const AActor* Target)
        {
            return Controller && Target && (Controller->GetViewTarget() == Target ||
                (Controller->PlayerCameraManager && Controller->PlayerCameraManager->PendingViewTarget.Target == Target));
        };
        bOk &= Test.TestTrue(*(Beat.Id + TEXT(" plays through its camera")), Viewing(Shot));
        GameMode->BeginRound();
        const FSoraBeat* After = Director->ActiveBeatData();
        if (!GameMode->bChapterComplete && After && !After->Is(SoraBeatRules::EType::Cinematic))
            bOk &= Test.TestTrue(*(Beat.Id + TEXT(": the view returns to the hero")), Viewing(Player(State)));
        ++State.CinematicShots;
        break;
    }
    case EGoal::Lines:
    {
        bool bStarted=Director->LinesStarted();
        if (Beat.LinesEvent != TEXT("beat_start"))
            bOk &= Test.TestFalse(*(Beat.Id + TEXT(" waits for its trigger")),bStarted);
        for (int32 Action = 0; Action < MaxActionsPerBeat && Active(); ++Action)
        {
            bStarted|=Director->LinesStarted();
            if (const FSoraDialogueCue* Line = Director->CurrentDialogueCue())
            {
                bOk &= Test.TestTrue(*(Line->Id + TEXT(" is bilingual")), HasJapanese(Line->Japanese) && !Line->English.IsEmpty() &&
                    FSoraCatalog::Get().DialogueSpeaker(Line->SpeakerId) != nullptr);
                const TArray<FSoraSubtitle> Queued = Director->QueuedSubtitles();
                bOk &= Test.TestTrue(*(Line->Id + TEXT(" heads the subtitle queue with its speaker")), !Queued.IsEmpty() &&
                    Queued[0].LineId == Line->Id && HasJapanese(Queued[0].Speaker) && !Queued[0].SpeakerEnglish.IsEmpty() &&
                    Queued[0].Seconds == Line->DurationSeconds);
                ++State.LinesShown;
            }
            if (Director->LinesQueued() == 0)
            {
                // The frame that releases a hold does not also advance the
                // task clock. Give its ordinary next step a chance to finish.
                if (!Advance(Test,State)) return false;
                if (!Active()) break;
                if (Director->LinesQueued()>0) continue;
                if (Director->ObjectiveAnchor(Anchor))
                {
                    MoveTo(State,Anchor);
                    if(!Advance(Test,State,1)) return false;
                    if(Director->AnchorTakesInteract()&&!State.World->PressKey(EKeys::E)) return false;
                    bStarted|=Director->LinesStarted();
                }
                else if (!Director->TaskProgress().LinesDone)
                    return Fail(Test,State,Beat.Id+TEXT(" is waiting for authored dialogue events without a tested world interaction"));
            }
            if (!Advance(Test, State, 1, FastSeconds))
                return false;
        }
        bOk &= Test.TestTrue(*(Beat.Id + TEXT(" begins on its authored trigger")),bStarted);
        break;
    }
    case EGoal::Points:
        if (!LoseMatch(Test, State))
            return false;
        for (int32 Action = 0; Action < MaxActionsPerBeat && Active(); ++Action)
            if (!DefeatOne(Test, State))
                return false;
        break;
    case EGoal::OpponentDown:
        for (int32 Action = 0; Action < MaxActionsPerBeat && Active(); ++Action)
        {
            if (Director->AwaitingCapture())
            {
                if (!CaptureYielded(Test, State, Beat))
                    return false;
                continue;
            }
            // The fight ends as the story says: a killed opponent falls, a
            // spared or captured one yields upright where it stands.
            const TWeakObjectPtr<ASoraEnemy> Opponent = PhasedOpponent(State);
            if (!DefeatOne(Test, State))
                return false;
            if (Opponent.IsValid() && !Opponent->IsAlive())
                bOk &= Test.TestEqual(*(Beat.Id + TEXT(": the opponent is spared, not felled")),
                    FMath::Abs(Opponent->GetActorRotation().Roll) < 1.f, Rules.Defeat != SoraBeatRules::EDefeat::Kill);
        }
        // Until Sequencer lands, a boss's outro plays its lines as the fight ends.
        if (Beat.Is(SoraBeatRules::EType::Boss))
            bOk &= ExpectLinesQueued(Test, State, Chapter, Index, TEXT("outro_cinematic"));
        break;
    case EGoal::Lessons:
    {
        if (!RecordLessons(Test, State, Beat, Index == 1 && Director->ChapterId == 0) ||
            (Rules.FlankBouts && !MissFlank(Test, State, Beat)))
            return false;
        // Bouts are numbered across the chapter's lesson duels (ch01.b04 scores bouts 3 and 4).
        int32 Offset = 0;
        for (int32 Earlier = 0; Earlier < Index; ++Earlier)
            if (Chapter.Beats[Earlier].Has(EGoal::Lessons))
                Offset += Chapter.Tasks[Earlier].Count;
        for (int32 Action = 0; Action < MaxActionsPerBeat && Active(); ++Action)
        {
            // Each bout of a 転 lesson opens on the hero's roll to the flank.
            if (Rules.FlankBouts)
                RollToFlank(State);
            const int32 Done = Director->TaskProgress().Done;
            if (!DefeatOne(Test, State))
                return false;
            bOk &= ExpectLinesQueued(Test, State, Chapter, Index, *FString::Printf(TEXT("bout_scored:%d"), Offset + Done + 1));
        }
        break;
    }
    case EGoal::WavesCleared:
    case EGoal::Survive:
        if(Beat.bArcheryLesson)
        {
            if(!SoraArcheryAutomation::Complete(Test,*State.World,true))
                return Fail(Test,State,TEXT("The range must complete through actual arrow impacts"));
            break;
        }
        // Fight what the waves send; walk into the volume that brings the next
        // one; let the clock run for timed waves and survivals.
        for (int32 Action = 0; Action < MaxActionsPerBeat * 4 && Active(); ++Action)
        {
            if (!LiveEnemies(State).IsEmpty()) { if (!DefeatOne(Test, State)) return false; continue; }
            if (Director->ObjectiveAnchor(Anchor) && Rules.Goal == EGoal::WavesCleared)
            {
                if(Beat.Space.Wind.Ridge())
                {
                    const bool AtExit=SoraBeatRules::TaskComplete(Director->TaskProgress(),Rules);
                    if(!SoraRidgeAutomation::Walk(*State.World,Beat.Space,Anchor.X-Beat.Space.Wind.Origin.X,Test,false,AtExit))
                        return Fail(Test,State,TEXT("The ridge requires real traversal and mapped vaults"));
                }
                else if(Beat.Space.Spire.Enabled())
                {
                    const bool AtL3=Player(State)->GetActorLocation().Z>1700.f;
                    if(!SoraSpireAutomation::Climb(*State.World,Beat.Space,AtL3?SoraSpireRules::Landing(2)+1:0,AtL3?SoraSpireRules::Landing(3):SoraSpireRules::Landing(2)))
                        return Fail(Test,State,TEXT("The spiral must be climbed through its physical route"));
                    if(AtL3&&!SoraLiftAutomation::Walk(*State.World,FVector(Beat.Space.Exit.Center,2700))) return false;
                }
                else MoveTo(State, Anchor);
            }
            if (!Advance(Test, State, 1, FastSeconds))
                return false;
        }
        break;
    case EGoal::Exit:
    case EGoal::Hold:
    case EGoal::Escort:
    {
        if(Beat.Space.Moat.bEnabled)
        {
            SoraMoatAutomation::Sample(*State.World,TEXT("aggregate route entry"));
            if(!SoraMoatAutomation::ToGate(*State.World)||!PickUpAll(Test,State,true)||
                !Test.TestTrue(TEXT("The moat requires real swimming and submerged gate passage"),SoraMoatAutomation::ThroughGate(*State.World)))
                return Fail(Test,State,TEXT("The moat traversal or its physical collectible approach failed"));
            break;
        }
        if(Beat.Space.Climb.bEnabled)
        {
            if(!Test.TestTrue(TEXT("The wall exit requires real holds and swept crawl input"),SoraClimbAutomation::Traverse(*State.World))) return false;
            break;
        }
        if(Beat.Space.Flood.bEnabled)
        {
            if(!Test.TestTrue(TEXT("The flood exit requires actual swimming, breathing and gate passage"),SoraFloodAutomation::Exit(*State.World))) return false;
            break;
        }
        if(Director->IsWoodExplore())
        {
            if(!SoraWoodAutomation::Poi(*State.World,SoraWoodRules::Stone)||
                !SoraWoodAutomation::Poi(*State.World,SoraWoodRules::Boundary)||
                !SoraWoodAutomation::Exit(*State.World)) return false;
            break;
        }
        // Rides are ridden: a horse to tack up is mounted from her right,
        // the others start in the saddle.
        if (Beat.Is(SoraBeatRules::EType::HorsebackRide))
        {
            if (!Director->IsMounted() && !MountUp(Test, State, Beat))
                return false;
            bOk &= Test.TestTrue(*(Beat.Id + TEXT(" is ridden")), Director->IsMounted());
            ++State.RidesRidden;
        }
        // A hold fills only with the hero in it.
        if (Rules.Goal == EGoal::Hold)
        {
            MoveTo(State, FarAway(State));
            if (!Advance(Test, State, 2, FastSeconds))
                return false;
            bOk &= Test.TestEqual(*(Beat.Id + TEXT(" holds nothing from afar")), Director->TaskProgress().Progress, 0);
        }
        // A ride's ambushes come as the rider passes their marks (ch02.b08's
        // drones, ch08.b02's charge), and reaching the destination ends the
        // ride with them still standing: the rider does not stop to fight.
        const bool bAmbush = Beat.Is(SoraBeatRules::EType::HorsebackRide) && Rules.WaveCount > 0;
        TArray<TWeakObjectPtr<ASoraEnemy>> Standing;
        if (bAmbush)
        {
            const FSoraZone& Road = Chapter.Space.Zones[Beat.Space.Zone];
            MoveTo(State, ASoraWorldBuilder::Floor(Road.PointAlong(Road.RouteLength * .8f)));
            if (!Advance(Test, State, 2))
                return false;
            bOk &= Test.TestTrue(*(Beat.Id + TEXT(": its ambush comes as the rider passes its marks")), !LiveEnemies(State).IsEmpty());
        }
        for (int32 Action = 0; Action < MaxActionsPerBeat * 4 && Active(); ++Action)
        {
            // Holds and escorts are fought for (an opponent in a hold contests it); rides and stealth exits are not.
            if (Rules.Goal != EGoal::Exit && !LiveEnemies(State).IsEmpty()) { if (!DefeatOne(Test, State)) return false; continue; }
            if (Rules.Goal != EGoal::Exit && !FreeConscripts(Test, State))
                return false;
            if (Rules.Goal == EGoal::Escort && !TendParty(Test, State))
                return false;
            if (Rules.Goal == EGoal::Hold && !TendFires(Test, State))
                return false;
            if(Director->HelmNeedsTrim()&&!SoraHelmAutomation::Correct(*State.World))
                return Fail(Test,State,TEXT("The helm requires its actual wheel correction"));
            Standing.Reset();
            for (ASoraEnemy* Enemy : LiveEnemies(State))
                Standing.Add(Enemy);
            if (Director->ObjectiveAnchor(Anchor))
            {
                if(Director->IsHelmHold()) { if(!SoraRecoveryAutomation::WalkTo(*State.World,Anchor)) return false; }
                else MoveTo(State,Anchor);
            }
            if (!Advance(Test, State, 1, FastSeconds))
                return false;
        }
        if (bAmbush)
            bOk &= Test.TestTrue(*(Beat.Id + TEXT(" ends at its destination with its ambush still standing, and none follows")),
                !Standing.IsEmpty() && !Active() && Algo::AllOf(Standing, [](const TWeakObjectPtr<ASoraEnemy>& Enemy)
                    { return !Enemy.IsValid() || Enemy->IsActorBeingDestroyed(); }));
        break;
    }
    case EGoal::Objectives:
    case EGoal::Deliveries:
    case EGoal::Turns:
    case EGoal::Steps:
    {
        if(Beat.Space.Lift.bEnabled)
        {
            if(!Test.TestTrue(TEXT("The full spire ride uses boarding and ordinary crank input"),SoraLiftAutomation::Ride(*State.World))||
                !Test.TestTrue(TEXT("The gallery can be searched and left by walking"),SoraLiftAutomation::Gallery(*State.World,true))) return false;
            ++State.CachesOpened;
            ++State.GoalsPlayed.FindOrAdd(static_cast<int32>(SoraBeatRules::EGoal::Cache));
            break;
        }
        // A cargo ride delivers from the saddle.
        if (Beat.Is(SoraBeatRules::EType::HorsebackRide))
        {
            bOk &= Test.TestTrue(*(Beat.Id + TEXT(" is ridden")), Director->IsMounted());
            ++State.RidesRidden;
        }
        MoveTo(State, FarAway(State));
        GameMode->Interact(Player(State));
        bOk &= Test.TestEqual(*(Beat.Id + TEXT(" cannot be worked from afar")), Director->TaskProgress().Done, 0);
        if(Rules.RecoveryWeapons!=0u)
        {
            // Deal with the patrol using the currently available wakizashi
            // before entering the rope. Recovery itself uses no state edits.
            for(int32 Action=0;Action<MaxActionsPerBeat&&!LiveEnemies(State).IsEmpty();++Action)
                if(!DefeatOne(Test,State)) return false;
            if(!FreeConscripts(Test,State)||!Test.TestTrue(TEXT("Dry-well equipment is recovered by real movement and held input"),
                SoraRecoveryAutomation::Recover(*State.World))) return false;
        }
        if(Rules.CarryGateMs>0)
        {
            if(!ClearField(Test,State,Index)||!FreeConscripts(Test,State)||
                !Test.TestTrue(TEXT("Granary seal is pried through real movement and held input"),SoraCarryAutomation::PrySeal(*State.World))) return false;
        }
        bool bSlipTested = false, bMissTested = false, bLoadTested = false;
        // A crank is turned, not fought over: it is done once full, whoever stands.
        TArray<TWeakObjectPtr<ASoraEnemy>> Standing;
        ASoraWorldBuilder* WorldBuilder = GameMode->Arena();
        const FName Kit = WorldBuilder->ActiveKit();
        const float GaugeBefore = WorldBuilder->KitGaugeHeight();
        bOk &= Test.TestTrue(*(Beat.Id + TEXT(" stages its task's kit")), Beat.Space.Work.IsNone() || Kit == Beat.Space.Work);
        for (int32 Action = 0; Action < MaxActionsPerBeat && Active(); ++Action)
        {
            const SoraBeatRules::FTaskState& Task = Director->TaskProgress();
            if (Rules.Goal == EGoal::Turns)
            {
                // A steady rhythm inside the band; one hurried turn slips first.
                if (!Wait(Test, State, (Rules.MinTurnMs + Rules.MaxTurnMs) / 2))
                    return false;
                Standing.Reset();
                for (ASoraEnemy* Enemy : LiveEnemies(State))
                    Standing.Add(Enemy);
                if (!WorkAtAnchor(Test, State))
                    return false;
                // The first turn in the band plays its ":first" rows (ch05.b06's "That golden yellow").
                if (Action == 0)
                    for (const FSoraDialogueTrigger& Row : Chapter.Triggers)
                        if (Row.Beat == Index && Row.On == TEXT("rate_band:in:first"))
                            for (const int32 Line : Row.Lines)
                                bOk &= Test.TestTrue(*(Chapter.Dialogue[Line].Id + TEXT(" plays on the first turn in the band")),
                                    Director->QueuedSubtitles().ContainsByPredicate([&](const FSoraSubtitle& Queued)
                                        { return Queued.LineId == Chapter.Dialogue[Line].Id; }));
                // The water rises in its channel and a lift climbs with the turns.
                if (Action == 0 && Active() && (Kit == TEXT("sluice") || Kit == TEXT("lift")))
                {
                    if (!Advance(Test, State, 1))
                        return false;
                    bOk &= Test.TestTrue(*(Beat.Id + TEXT(": the kit's gauge rises with the turns")), WorldBuilder->KitGaugeHeight() > GaugeBefore);
                }
                if (!bSlipTested && Task.Done == 1 && Active())
                {
                    bSlipTested = true;
                    if(Rules.AlternateTreads)
                    {
                        if(!WorkAtAnchor(Test,State)) return false;
                    }
                    else GameMode->Interact(Player(State));
                    bOk &= Test.TestEqual(*(Beat.Id + TEXT(": a hurried turn slips")), Director->TaskProgress().Done, 1);
                }
            }
            else if (Rules.Goal == EGoal::Steps)
            {
                const SoraBeatRules::FStep& Step = Rules.Steps[Task.Step];
                if(Step.PhraseStrikes>0)
                {
                    if(!SoraRhythmRules::Active(Director->RhythmState(),Task,Rules))
                    { if(!WorkAtAnchor(Test,State)) return false; }
                    const int32 Until=FMath::Max(0,Director->RhythmState().DueMs-Director->TaskProgress().ElapsedMs);
                    if(!Wait(Test,State,Until)||!WorkAtAnchor(Test,State)||!Wait(Test,State,Step.ToleranceMs+20)) return false;
                    continue;
                }
                const bool bRhythm = Step.BeatMs > 0 && Task.StepDone > 0;
                // One stroke off the beat restarts the rhythm step.
                const bool bMiss = bRhythm && !bMissTested && Task.StepDone == 1;
                if (!Wait(Test, State, bRhythm ? Step.BeatMs + (bMiss ? 3 * Step.ToleranceMs + 1 : 0) : 400) || !WorkAtAnchor(Test, State))
                    return false;
                if (bMiss)
                {
                    bMissTested = true;
                    bOk &= Test.TestEqual(*(Beat.Id + TEXT(": an off-beat stroke restarts the rhythm")), Director->TaskProgress().StepDone, 1);
                }
            }
            else if (Director->ObjectiveAnchor(Anchor))
            {
                const bool bHoist = Rules.Task == SoraBeatRules::ETask::Carry && Rules.PickupHoldMs > 0 && !Task.Carrying;
                if (bHoist ? !HoistLoad(Test, State) : !WorkAtAnchor(Test, State))
                    return false;
                // A load slows the hero, shows in his arms and leaves him at most the katana.
                if (!bLoadTested && Active() && Director->TaskProgress().Carrying && Rules.Task == SoraBeatRules::ETask::Carry)
                {
                    bLoadTested = true;
                    const float Pace = Rules.CarrySpeedPermille / 1000.f;
                    bOk &= Test.TestTrue(*(Beat.Id + TEXT(": the load slows the hero")),
                        FMath::IsNearlyEqual(Director->CarryPace(), Pace) && FMath::IsNearlyEqual(Player(State)->GetEquipment()->MoveScale(false), Pace) &&
                        WorldBuilder->IsCarryingLoad());
                    bOk &= Test.TestFalse(*(Beat.Id + TEXT(": the yumi cannot be drawn under a load")),
                        Player(State)->IsCampaignHero() && Player(State)->GetEquipment()->EquipCampaignWeapon(18));
                }
            }
            else if (!LiveEnemies(State).IsEmpty())
            {
                if (!DefeatOne(Test, State))
                    return false;
            }
            else if (!Advance(Test, State, 1, FastSeconds))
                return false;
            // The hero clears what the waves send between his work, as a player
            // would; the task never waits for it.
            if (Active() && Rules.WaveCount > 0 && Rules.Goal != EGoal::Turns && !LiveEnemies(State).IsEmpty() &&
                !ClearField(Test, State, Index))
                return false;
        }
        if(Active()&&Rules.Goal==EGoal::Turns)
        {
            FVector Point; Director->ObjectiveAnchor(Point);
            Test.AddError(FString::Printf(TEXT("%s crank stalled: progress=%d done=%d elapsed=%d last_action=%d working=%d stagger=%d guard=%.2f hero=%s anchor=%s enemies=%d"),
                *Beat.Id,Director->TaskProgress().Progress,Director->TaskProgress().Done,Director->TaskProgress().ElapsedMs,
                Director->TaskProgress().LastActionMs,Director->IsWorkingCrank(),Player(State)->GetEquipment()->IsStaggered(),
                Player(State)->GetEquipment()->GuardReserve(),*Player(State)->GetActorLocation().ToString(),*Point.ToString(),LiveEnemies(State).Num()));
        }
        // ch04.b06's shape: the crank turned full while its waves stand ends
        // the beat at once, and nothing slips back while they stand.
        if (Rules.Goal == EGoal::Turns && Rules.WaveCount > 0)
            bOk &= Test.TestTrue(*(Beat.Id + TEXT(" is done once the crank is full, its waves still standing")),
                !Active() && !Standing.IsEmpty() && Algo::AllOf(Standing, [](const TWeakObjectPtr<ASoraEnemy>& Enemy)
                    { return !Enemy.IsValid() || Enemy->IsActorBeingDestroyed(); }));
        break;
    }
    case EGoal::Cache:
    case EGoal::Found:
        return Fail(Test, State, Beat.Id + TEXT(": an optional beat became the active beat"));
    }
    const SoraBeatRules::FProgress& Progress = Director->Progress();
    bOk &= Test.TestTrue(*(Beat.Id + TEXT(" completes")), (Director->ActiveBeat() != Index || GameMode->bChapterComplete) &&
        (Progress.CompletedMask & SoraBeatRules::BeatBit(Index)) != 0u);
    if (Beat.Is(SoraBeatRules::EType::HorsebackRide))
        bOk &= Test.TestTrue(*(Beat.Id + TEXT(": the rider is down at the destination")),
            !Director->IsMounted() || (Director->ActiveBeatData() && Director->ActiveBeatData()->Space.bMount));
    bOk &= Test.TestTrue(*(Beat.Id + TEXT(" unlocks its weapons, mechanics and story flags")),
        (Progress.WeaponsMask & (Rule.WeaponsMask | Rule.GrantsMask)) == (Rule.WeaponsMask | Rule.GrantsMask) &&
        (Progress.MechanicsMask & Rule.MechanicsMask) == Rule.MechanicsMask && (Progress.FlagsMask & Rule.FlagsMask) == Rule.FlagsMask);
    if (Rule.Site >= 0)
        bOk &= Test.TestTrue(*(Beat.Id + TEXT(" restores its site")), (GameMode->Arena()->ActivatedMask() & (1 << Rule.Site)) != 0);
    if (!bOk)
        return Fail(Test, State, Beat.Id + TEXT(" did not play through"));
    ++State.BeatsPlayed;
    ++State.GoalsPlayed.FindOrAdd(static_cast<int32>(Rules.Goal));
    Player(State)->Heal(Player(State)->MaxHealth);
    return NoteUnlocks(Test, State, Beat.Id, Rule) && Advance(Test, State, 1);
}

// Nyaakoto holds only what the campaign has unlocked, and every arm it has
// unlocked he can take up with his own keys.
bool ExpectWeapon(FAutomationTestBase& Test, FState& State, int32 WeaponId, bool bUnlocked)
{
    ASoraPlayerCharacter* Hero = Player(State);
    USoraEquipmentComponent* Kit = Hero->GetEquipment();
    const int32 Held = Hero->WeaponId;
    // Chapter three begins with only the wakizashi. Its unlock is still
    // checked here, but returning from that check cannot equip the lost kit.
    const int32 ReturnWeapon = Campaign(State)->CanHold(0,false) ? 0 : Held;
    if (!Holdable(WeaponId))
        return Fail(Test, State, FString::Printf(TEXT("Weapon %d has no campaign slot"), WeaponId));
    const bool bEquipped = Kit->EquipCampaignWeapon(WeaponId);
    const FString What = FString::Printf(TEXT("%s: weapon %d %s"), *Where(State), WeaponId, bUnlocked ? TEXT("equips") : TEXT("stays locked"));
    bool bOk = Test.TestEqual(*What, bEquipped, bUnlocked) && Test.TestEqual(*(What + TEXT(" (held)")), Hero->WeaponId, bUnlocked ? WeaponId : Held);
    if (!bUnlocked)
        bOk &= Test.TestTrue(*(What + TEXT(" with a notice")), Mode(State)->NoticeTime > 0.f && !Mode(State)->NoticeEnglish.IsEmpty());
    // Back to the available weapon, after the equip delay.
    if (!Advance(Test, State, 20) || (bEquipped && !Kit->EquipCampaignWeapon(ReturnWeapon)))
        return Fail(Test, State, What + TEXT(": could not return to the available weapon"));
    // Every unlocked arm is in reach of the player's own keys: its group key,
    // pressed until it comes up, and a place on the arms wheel's ring.
    const int32 Group = SoraArmsRules::GroupOf(WeaponId);
    if (bUnlocked)
    {
        int32 Presses = 0;
        for (; Presses < SoraArmsRules::GroupStart[Group + 1] - SoraArmsRules::GroupStart[Group] && Hero->WeaponId != WeaponId; ++Presses)
            Hero->SelectArmsGroup(Group);
        bOk &= Test.TestEqual(*(What + TEXT(" on its group key")), Hero->WeaponId, WeaponId);
        bOk &= Test.TestTrue(*(What + TEXT(" on the arms wheel")), SoraArmsRules::Holds(Hero->HoldableArms(), WeaponId));
        if (!Advance(Test, State, 20) || !Kit->EquipCampaignWeapon(ReturnWeapon))
            return Fail(Test, State, What + TEXT(": could not return to the available weapon"));
    }
    else
        bOk &= Test.TestFalse(*(What + TEXT(" is not on the arms wheel")), SoraArmsRules::Holds(Hero->HoldableArms(), WeaponId));
    return (bOk || Fail(Test, State, What)) && Advance(Test, State, 20);
}

// Each holdable arm after the dojo is refused while the beat that hands it
// over is still ahead, and equips from that beat on (at the first moment the
// hero's paws are free: out of the saddle, with no load): the yari in
// ch02.b03 itself, before the beat completes and keeps it.
bool CheckArms(FAutomationTestBase& Test, FState& State)
{
    const USoraCampaignDirector* Director = Campaign(State);
    if (Director->ChapterId == 0 || Director->IsMounted() || Director->TaskProgress().Carrying)
        return true;
    unsigned Seen = FSoraCatalog::Get().EarlierWeapons(1);
    for (int32 Chapter = 1; Chapter <= LastChapter; ++Chapter)
        for (const SoraBeatRules::FBeat& Rule : FSoraCatalog::Get().Chapter(Chapter).Rules)
        {
            const unsigned Mask = (Rule.WeaponsMask | Rule.GrantsMask) & ~Seen;
            Seen |= Mask;
            for (int32 WeaponId = 0; WeaponId < SoraBeatRules::WeaponCount; ++WeaponId)
            {
                if ((Mask & (1u << WeaponId)) == 0u || !Holdable(WeaponId) || State.ArmsHeld.Contains(WeaponId))
                    continue;
                const bool bInPlay = Director->IsWeaponUnlocked(WeaponId);
                if (!bInPlay && !State.ArmsLocked.Contains(WeaponId))
                {
                    if (!ExpectWeapon(Test, State, WeaponId, false))
                        return false;
                    ++State.ArmsRefused;
                    State.ArmsLocked.Add(WeaponId);
                }
                else if (bInPlay && State.ArmsLocked.Contains(WeaponId))
                {
                    if (!ExpectWeapon(Test, State, WeaponId, true))
                        return false;
                    ++State.ArmsEquipped;
                    State.ArmsInTheirBeat += (Director->Progress().WeaponsMask & (1u << WeaponId)) == 0u;
                    State.ArmsHeld.Add(WeaponId);
                }
            }
        }
    return true;
}

bool StartWorld(FAutomationTestBase& Test, FState& State)
{
    State.World = MakeUnique<FSoraAutomationWorld>();
    ++State.WorldsStarted;
    // BeginPlay reads the save; the next tick runs ResetRound, which rebuilds
    // the chapter and restores the checkpoint. A local player's controller
    // then lets the cinematics take its view.
    if (!State.World->Start(State.Slot) || !State.World->Tick(1) || !State.World->EnableKeyInput())
    {
        State.World->ForwardErrorMessages(&Test);
        return Fail(Test, State, FString::Printf(TEXT("Campaign world %d did not start"), State.WorldsStarted));
    }
    const ASoraGameMode* GameMode = Mode(State);
    if (!GameMode || !GameMode->Arena() || !Player(State) || !FSoraCatalog::Get().IsReady())
        return Fail(Test, State, TEXT("Campaign world lacks its arena, player or catalog"));
    return (Test.TestTrue(TEXT("A loaded campaign opens in the menu"), GameMode->bMenu) &&
        Test.TestTrue(TEXT("The open menu pauses the world"), Paused(State))) ||
        Fail(Test, State, TEXT("Campaign world skipped its paused menu"));
}

bool StopWorld(FAutomationTestBase& Test, FState& State)
{
    const bool bDestroyed = State.World->DestroyTestWorld(true);
    State.World->ForwardErrorMessages(&Test);
    State.World.Reset();
    return Test.TestTrue(TEXT("Campaign world tears down"), bDestroyed) || Fail(Test, State, TEXT("World teardown failed"));
}

// Tears the world down and restores the saved checkpoint in a fresh one:
// the beat and phase, everything done, unlocked and restored, the dojo forms,
// every collectible, and the finds and caches still waiting.
bool Reload(FAutomationTestBase& Test, FState& State)
{
    const USoraCampaignDirector* Director = Campaign(State);
    const FString Context = TEXT("Reloaded ") + Where(State);
    const int32 Chapter = Director->ChapterId, Beat = Director->ActiveBeat(), Phase = Director->ActivePhase();
    const SoraBeatRules::FProgress Progress = Director->Progress();
    const int32 Sites = Mode(State)->Arena()->ActivatedMask();
    const int32 LessonStage = Director->DojoLessonStage();
    const bool bComplete = Mode(State)->bChapterComplete, bLiberated = Director->bCampaignComplete;
    const uint64 Collected = Director->CollectedMask();
    const TArray<int32> Loose = Director->LoosePickups(), Caches = Director->AvailableCaches();
    if (!StopWorld(Test, State) || !StartWorld(Test, State))
        return false;
    Director = Campaign(State);
    bool bOk = Test.TestEqual(*(Context + TEXT(": chapter")), Director->ChapterId, Chapter);
    bOk &= Test.TestEqual(*(Context + TEXT(": completion")), Mode(State)->bChapterComplete, bComplete);
    bOk &= Test.TestEqual(*(Context + TEXT(": liberation")), Director->bCampaignComplete, bLiberated);
    bOk &= Test.TestEqual(*(Context + TEXT(": collectibles")), Director->CollectedMask(), Collected);
    bOk &= Test.TestTrue(*(Context + TEXT(": the loose finds still lying")), Director->LoosePickups() == Loose);
    bOk &= Test.TestTrue(*(Context + TEXT(": the caches still waiting")), Director->AvailableCaches() == Caches);
    if (!bComplete)
    {
        bOk &= Test.TestEqual(*(Context + TEXT(": beat")), Director->ActiveBeat(), Beat);
        bOk &= Test.TestEqual(*(Context + TEXT(": phase")), Director->ActivePhase(), Phase);
        bOk &= Test.TestEqual(*(Context + TEXT(": beats done")), Director->Progress().CompletedMask, Progress.CompletedMask);
        bOk &= Test.TestEqual(*(Context + TEXT(": weapons")), Director->Progress().WeaponsMask, Progress.WeaponsMask);
        bOk &= Test.TestEqual(*(Context + TEXT(": mechanics")), Director->Progress().MechanicsMask, Progress.MechanicsMask);
        bOk &= Test.TestEqual(*(Context + TEXT(": story flags")), Director->Progress().FlagsMask, Progress.FlagsMask);
        bOk &= Test.TestEqual(*(Context + TEXT(": sites")), Mode(State)->Arena()->ActivatedMask(), Sites);
        bOk &= Test.TestEqual(*(Context + TEXT(": dojo forms")), Director->DojoLessonStage(), LessonStage);
        if (const FSoraBeatSpace* Space = Director->ActiveSpace())
            bOk &= Test.TestEqual(*(Context + TEXT(": the hero stands in the beat's place")), Director->HeroZone(), Space->Zone);
    }
    return bOk || Fail(Test, State, Context + TEXT(" did not match its checkpoint"));
}

// Enter from the menu returns to a restored checkpoint without the title card.
bool Resume(FAutomationTestBase& Test, FState& State)
{
    ASoraGameMode* GameMode = Mode(State);
    GameMode->BeginRound();
    const FSoraBeat* Beat = Campaign(State)->ActiveBeatData();
    bool bOk = Test.TestFalse(TEXT("Enter closes the menu"), GameMode->bMenu);
    bOk &= Test.TestFalse(TEXT("Closing the menu unpauses the world"), Paused(State));
    bOk &= Test.TestFalse(TEXT("A resumed checkpoint skips the title card"), Campaign(State)->IsChapterOpening());
    bOk &= Test.TestTrue(TEXT("A resumed checkpoint is in play, dialogue or its cinematic"),
        GameMode->IsPlaying() || GameMode->InputState()==SoraInput::Dialogue || (Beat && Beat->Is(SoraBeatRules::EType::Cinematic)));
    return (bOk || Fail(Test, State, TEXT("Resuming a checkpoint did not return to play"))) && Advance(Test, State);
}

// In every chapter the first checkpoint of each task goal past the opening is
// restored in a fresh world as its beat starts, and played on from there.
bool CheckpointReload(FAutomationTestBase& Test, FState& State)
{
    const USoraCampaignDirector* Director = Campaign(State);
    const FSoraChapter& Chapter = ChapterData(State);
    const int32 Beat = Director->ActiveBeat();
    if (Mode(State)->bChapterComplete || Beat <= 0 || !Chapter.Rules.IsValidIndex(Beat) || !Chapter.Rules[Beat].Checkpoint ||
        Director->ActivePhase() != 0)
        return true;
    const int32 Key = Director->ChapterId * 32 + static_cast<int32>(Chapter.Tasks[Beat].Goal);
    if (State.ReloadedGoals.Contains(Key))
        return true;
    State.ReloadedGoals.Add(Key);
    ++State.CheckpointReloads;
    return Reload(Test, State) && Resume(Test, State);
}

// A boss or duel saves at each later phase it names: the opponent is struck
// into the phase, the save is read back, and the phase is restored in a fresh
// world with the opponent at that phase's health.
bool PlayPhases(FAutomationTestBase& Test, FState& State)
{
    const FSoraChapter& Chapter = ChapterData(State);
    const int32 Index = Campaign(State)->ActiveBeat();
    const FSoraBeat& Beat = Chapter.Beats[Index];
    const SoraBeatRules::FTask& Rules = Chapter.Tasks[Index];
    for (int32 Phase = Campaign(State)->ActivePhase() + 1; Phase <= Chapter.Rules[Index].PhaseCheckpoints; ++Phase)
    {
        const FString Context = FString::Printf(TEXT("%s phase %d"), *Beat.Id, Phase + 1);
        ASoraEnemy* Opponent = PhasedOpponent(State);
        if (!Test.TestNotNull(*(Context + TEXT(": the opponent stands")), Opponent))
            return Fail(Test, State, Context + TEXT(" has no opponent"));
        const float Left = Opponent->MaxHealth * (SoraBeatRules::PhaseStartPermille(Rules, Phase) - 50) / 1000.f;
        UGameplayStatics::ApplyDamage(Opponent, Opponent->Health - Left, Player(State)->GetController(), Player(State), UDamageType::StaticClass());
        if (!Advance(Test, State))
            return false;
        if(Beat.Space.Summit.Enabled())
        {
            const auto* Boss=Cast<ASoraBoss>(Opponent);
            for(int32 Frame=0;Boss&&Frame<1800&&(Boss->PhaseIndex()!=Phase||Boss->IsPhaseTransitioning()||
                (Phase==1&&!Boss->IsOnSummitDais()));++Frame)
                if(!Advance(Test,State,1,FrameSeconds)) return false;
            if(!Advance(Test,State,2,FrameSeconds)) return false;
        }
        if (!Test.TestEqual(*(Context + TEXT(" begins")), Campaign(State)->ActivePhase(), Phase) || !ExpectCheckpoint(Test, State))
            return Fail(Test, State, Context + TEXT(" was not saved"));
        ++State.PhaseReloads;
        if (!Reload(Test, State) || !Resume(Test, State))
            return false;
        Opponent = PhasedOpponent(State);
        if (!Test.TestNotNull(*(Context + TEXT(": the restored phase puts the opponent back")), Opponent) ||
            // A bosses.json fight keeps whole health points (SoraBossRules::PhaseHealth).
            !Test.TestEqual(*(Context + TEXT(": the opponent returns at the phase's health")), Opponent->Health,
                Opponent->MaxHealth * (SoraBeatRules::PhaseStartPermille(Rules, Phase) / 1000.f), 1.f))
            return Fail(Test, State, Context + TEXT(" was not restored"));
    }
    return true;
}

// A fallen guard walks its patrol no more: its brain stops with it, and its
// body stays where it fell for the others to find.
bool ForgetFallenGuard(FAutomationTestBase& Test, FState& State)
{
    for (ASoraEnemy* Guard : LiveEnemies(State))
        if (const ASoraEnemyController* Brain = Cast<ASoraEnemyController>(Guard->GetController()); Brain && Brain->IsGuard())
        {
            UGameplayStatics::ApplyDamage(Guard, Guard->Health, Player(State)->GetController(), Player(State), UDamageType::StaticClass());
            State.bGuardForgotten = true;
            const TWeakObjectPtr<ASoraEnemy> Fallen = Guard;
            const FVector Fell = Guard->GetActorLocation();
            if (!Advance(Test, State, 30))
                return false;
            return Test.TestTrue(TEXT("A fallen guard stays down where it fell, off its patrol"), Fallen.IsValid() && Fallen->IsBody() &&
                FVector::Dist2D(Fallen->GetActorLocation(), Fell) < 1.f && Fallen->GetVelocity().IsNearlyZero()) ||
                Fail(Test, State, Where(State) + TEXT(": a fallen guard kept walking its patrol"));
        }
    return true;
}

// Plays beats until StopBeat is active (INDEX_NONE: until the chapter ends).
bool PlayUntil(FAutomationTestBase& Test, FState& State, int32 StopBeat = INDEX_NONE)
{
    for (int32 Round = 0; Round <= SoraBeatRules::MaxBeats; ++Round)
    {
        if (Mode(State)->bChapterComplete || Campaign(State)->ActiveBeat() == StopBeat)
            return true;
        const FSoraChapter& Chapter = ChapterData(State);
        const int32 Beat = Campaign(State)->ActiveBeat();
        // Every beat starts with the hero in its place, holding only what
        // the completed beats unlocked.
        if (const FSoraBeatSpace* Space = Campaign(State)->ActiveSpace();
            Space && !Test.TestEqual(*(Where(State) + TEXT(": the hero stands in the beat's place")), Campaign(State)->HeroZone(), Space->Zone))
            return Fail(Test, State, Where(State) + TEXT(" did not travel to its place"));
        if (!Test.TestTrue(*(Where(State) + TEXT(": nothing is unlocked before its beat completes")),
            Campaign(State)->Progress().WeaponsMask == State.KnownWeapons && Campaign(State)->Progress().MechanicsMask == State.KnownMechanics))
            return Fail(Test, State, Where(State) + TEXT(" holds an unlock no completed beat gave"));
        // A checkpoint beat saved as it started, before any cache is opened.
        if (Chapter.Rules.IsValidIndex(Beat) && Chapter.Rules[Beat].Checkpoint && Campaign(State)->ActivePhase() == 0 &&
            (!ExpectCheckpoint(Test, State) || !CheckpointReload(Test, State)))
            return false;
        // Until Sequencer lands, a boss's intro plays its lines as the fight opens.
        const FSoraBeat* Active = Campaign(State)->ActiveBeatData();
        if (Active && Active->Is(SoraBeatRules::EType::Boss) && Campaign(State)->ActivePhase() == 0 &&
            !ExpectLinesQueued(Test, State, Chapter, Beat, TEXT("intro_cinematic")))
            return Fail(Test, State, Where(State) + TEXT(": the boss's intro did not play"));
        if (Active && Active->Is(SoraBeatRules::EType::StealthZone) && !State.bGuardForgotten && !ForgetFallenGuard(Test, State))
            return false;
        if (!CheckArms(Test, State) || !OpenCaches(Test, State) || !PickUpAll(Test, State) || !PlayPhases(Test, State) ||
            !PlayBeat(Test, State))
            return false;
    }
    return Fail(Test, State, Where(State) + TEXT(": the chapter did not end"));
}

// A fresh chapter opens on its first cinematic with the title card: the
// chapter's Japanese and English title, narrative and objective. The card
// holds the round timer, combat and dialogue until Enter skips it.
bool ExpectOpening(FAutomationTestBase& Test, FState& State, int32 Chapter)
{
    const ASoraGameMode* GameMode = Mode(State);
    const USoraCampaignDirector* Director = Campaign(State);
    const FSoraChapter& Data = FSoraCatalog::Get().Chapter(Chapter);
    const FSoraChapter* Card = GameMode->TitleCardChapter();
    const FString Context = FString::Printf(TEXT("Chapter %d opening"), Chapter + 1);
    bool bOk = Test.TestEqual(*(Context + TEXT(": chapter")), Director->ChapterId, Chapter);
    bOk &= Test.TestEqual(*(Context + TEXT(": cataloged map")), GameMode->MapId, Data.Map);
    bOk &= Test.TestTrue(*(Context + TEXT(": the title card shows before play")), Card == &Data &&
        GameMode->InputState() == SoraInput::Card && Director->ActiveBeat() == 0 && Director->IsChapterOpening() &&
        Director->CinematicElapsed() < ASoraGameMode::TitleCardSeconds);
    bOk &= Test.TestTrue(*(Context + TEXT(": Japanese title, narrative and objective")),
        Card && HasJapanese(Card->Title) && HasJapanese(Card->Narrative) && HasJapanese(Card->Objective));
    bOk &= Test.TestTrue(*(Context + TEXT(": English title, narrative and objective")),
        Card && !Card->TitleEnglish.IsEmpty() && !Card->NarrativeEnglish.IsEmpty() && !Card->ObjectiveEnglish.IsEmpty() &&
        !HasJapanese(Card->TitleEnglish) && !HasJapanese(Card->ObjectiveEnglish));
    bOk &= Test.TestTrue(*(Context + TEXT(": English subtitles are on by default")), GameMode->bEnglishSubtitles);
    bOk &= Test.TestEqual(*(Context + TEXT(": round timer waits")), GameMode->RoundTime, 0.f);
    bOk &= Test.TestEqual(*(Context + TEXT(": no beat done")), static_cast<int32>(Director->Progress().CompletedMask), 0);
    bOk &= Test.TestEqual(*(Context + TEXT(": no site")), GameMode->Arena()->ActivatedMask(), 0);
    bOk &= Test.TestTrue(*(Context + TEXT(": no opponent")), LiveEnemies(State).IsEmpty());
    return bOk || Fail(Test, State, Context + TEXT(" did not open on its title card"));
}

// The chapter's result screen: every beat of it done, its optional cache too,
// and every find of it kept in the save. Enter saves the next chapter
// (entered with everything this route earned) and opens it, or liberates the
// campaign.
bool NextChapter(FAutomationTestBase& Test, FState& State)
{
    ASoraGameMode* GameMode = Mode(State);
    USoraCampaignDirector* Director = Campaign(State);
    const int32 Chapter = Director->ChapterId;
    const FSoraChapter& Data = ChapterData(State);
    const SoraBeatRules::FProgress Earned = Director->Progress();
    const USoraSaveGame* Saved = Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(State.Slot, 0));
    bool bOk = Test.TestTrue(*FString::Printf(TEXT("Chapter %d completes"), Chapter + 1),
        GameMode->bChapterComplete && GameMode->InputState() == SoraInput::Result && Earned.Complete);
    bOk &= Test.TestTrue(TEXT("The finished chapter waits at its result in the save"),
        Saved && Saved->CheckpointChapter == Chapter && Saved->CheckpointBeat == INDEX_NONE && Saved->CheckpointComplete);
    bOk &= Test.TestEqual(TEXT("The next chapter is reached"), Saved ? Saved->HighestChapter : -1, FMath::Min(LastChapter, Chapter + 1));
    unsigned Every = 0u;
    for (int32 Index = 0; Index < Data.Beats.Num(); ++Index)
        Every |= SoraBeatRules::BeatBit(Index);
    bOk &= Test.TestEqual(*FString::Printf(TEXT("Chapter %d: every beat is done, the optional cache too"), Chapter + 1), Earned.CompletedMask, Every);
    for (const FSoraCollectible& Item : Data.Collectibles)
    {
        const uint64 Bit = SoraCampaignRules::CollectibleBit(Chapter, Item.MaskBit);
        bOk &= Test.TestTrue(*(Item.Id + TEXT(" is found and saved by the chapter's end")),
            (Director->CollectedMask() & Bit) != 0ull && Saved && (static_cast<uint64>(Saved->Collectibles) & Bit) != 0ull);
    }
    if (!bOk)
        return Fail(Test, State, FString::Printf(TEXT("Chapter %d did not finish"), Chapter + 1));
    GameMode->BeginRound();
    ++State.ChaptersCompleted;
    Saved = Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(State.Slot, 0));
    if (!Test.TestNotNull(TEXT("The advance is saved"), Saved))
        return Fail(Test, State, TEXT("Chapter advance was not saved"));
    if (Chapter == LastChapter)
    {
        Test.TestEqual(TEXT("Liberation clears the chapter checkpoint"), Saved->CheckpointChapter, -1);
        bOk = Test.TestTrue(TEXT("The final Enter liberates the campaign"), Director->bCampaignComplete);
        bOk &= Test.TestTrue(TEXT("Liberation returns to the menu"), GameMode->bMenu);
        bOk &= Test.TestTrue(TEXT("The liberation menu pauses the world"), Paused(State));
        bOk &= Test.TestTrue(TEXT("Liberation is saved"), Saved->CampaignComplete);
        bOk &= Test.TestEqual(TEXT("The liberated campaign stays on the final chapter"), Saved->CurrentChapter, LastChapter);
        return bOk || Fail(Test, State, TEXT("Campaign liberation was not recorded"));
    }
    // The next chapter's opening cinematic takes the first checkpoint at once.
    bOk = Test.TestEqual(TEXT("Enter advances to the next chapter"), Director->ChapterId, Chapter + 1);
    bOk &= Test.TestTrue(TEXT("The next chapter's first checkpoint is its opening"),
        Saved->CheckpointChapter == Chapter + 1 && Saved->CheckpointBeat == 0 && Saved->CheckpointBeatsMask == 0);
    bOk &= Test.TestFalse(TEXT("The next chapter starts out of the menu"), GameMode->bMenu);
    bOk &= Test.TestEqual(TEXT("The next chapter is saved"), Saved->CurrentChapter, Chapter + 1);
    bOk &= Test.TestEqual(TEXT("It is entered with this route's weapons"), Saved->ChapterEntryWeapons, static_cast<int32>(Earned.WeaponsMask));
    bOk &= Test.TestEqual(TEXT("It is entered with this route's mechanics"), Saved->ChapterEntryMechanics, static_cast<int32>(Earned.MechanicsMask));
    bOk &= Test.TestEqual(TEXT("It is entered with this route's story flags"), Saved->ChapterEntryFlags, static_cast<int32>(Earned.FlagsMask));
    bOk &= Test.TestEqual(TEXT("The finds are carried into it"), static_cast<uint64>(Director->CollectedMask()), static_cast<uint64>(Saved->Collectibles));
    bOk &= Test.TestFalse(TEXT("The campaign is not liberated early"), Saved->CampaignComplete);
    return (bOk || Fail(Test, State, FString::Printf(TEXT("Chapter %d did not advance"), Chapter + 1))) && ExpectOpening(Test, State, Chapter + 1);
}

bool FinishChapter(FAutomationTestBase& Test, FState& State)
{
    return PlayUntil(Test, State) && NextChapter(Test, State);
}

bool DefeatAndRetry(FAutomationTestBase& Test, FState& State)
{
    ASoraGameMode* GameMode = Mode(State);
    USoraCampaignDirector* Director = Campaign(State);
    ASoraPlayerCharacter* Hero = Player(State);
    const TArray<ASoraEnemy*> Enemies = LiveEnemies(State);
    if (Enemies.IsEmpty())
        return Fail(Test, State, TEXT("No opponent is there to defeat the hero"));
    if (!DefeatOne(Test, State))
        return false;
    const int32 Beat = Director->ActiveBeat();
    const SoraBeatRules::FProgress Progress = Director->Progress();
    const int32 Sites = GameMode->Arena()->ActivatedMask();
    UGameplayStatics::ApplyDamage(Hero, Hero->Health, nullptr, LiveEnemies(State)[0], UDamageType::StaticClass());
    if (!Test.TestTrue(TEXT("Lethal damage defeats the hero"), GameMode->bDefeated && GameMode->InputState() == SoraInput::Result))
        return Fail(Test, State, TEXT("Hero defeat was not recorded"));
    ++State.Failures;
    GameMode->BeginRound();
    bool bOk = Test.TestFalse(TEXT("Enter retries after defeat"), GameMode->bDefeated);
    bOk &= Test.TestFalse(TEXT("A retry skips the title card"), Director->IsChapterOpening());
    bOk &= Test.TestEqual(TEXT("A retry returns to the beat's checkpoint"), Director->ActiveBeat(), Beat);
    bOk &= Test.TestEqual(TEXT("A retry keeps the beats done"), Director->Progress().CompletedMask, Progress.CompletedMask);
    bOk &= Test.TestEqual(TEXT("A retry keeps restored sites"), GameMode->Arena()->ActivatedMask(), Sites);
    bOk &= Test.TestEqual(TEXT("A retry starts the wave over"), Director->Kills, 0);
    bOk &= Test.TestTrue(TEXT("A retry restores the hero"), Hero->IsAlive() && Hero->Health == Hero->MaxHealth);
    bOk &= Test.TestFalse(TEXT("A retry respawns the opponents"), LiveEnemies(State).IsEmpty());
    return (bOk || Fail(Test, State, TEXT("Retry did not restore the checkpoint"))) && Advance(Test, State);
}

// A defended target lost (ch02.b06's pack horses): the beat fails to its
// checkpoint, and Enter plays it again with every target whole.
bool LoseDefendedTarget(FAutomationTestBase& Test, FState& State)
{
    USoraCampaignDirector* Director = Campaign(State);
    ASoraGameMode* GameMode = Mode(State);
    const int32 Beat = Director->ActiveBeat();
    const SoraBeatRules::FTask Rules = Director->ActiveTask();
    if (!Test.TestTrue(TEXT("The defence has targets to keep"), Rules.TargetCount > 0 &&
        (Rules.FailMask & SoraBeatRules::FailBit(SoraBeatRules::EFail::TargetDestroyed)) != 0u))
        return Fail(Test, State, Where(State) + TEXT(" keeps no target"));
    // An opponent standing at a target wears it down, a whole point at a time.
    const TArray<ASoraEnemy*> Foes = LiveEnemies(State);
    if (!Test.TestFalse(TEXT("The defence's first wave is on the field"), Foes.IsEmpty()))
        return Fail(Test, State, Where(State) + TEXT(" has no opponent to besiege its targets"));
    const FVector Target = ASoraWorldBuilder::Floor(Director->ActiveSpace()->Targets[0], 120.f);
    Foes[0]->SetActorLocation(Target + FVector(0, 250, 0), false, nullptr, ETeleportType::TeleportPhysics);
    Foes[0]->SetActorTickEnabled(false);
    const int32 Whole = Director->TaskProgress().TargetHp[0];
    if (!Advance(Test, State, 60))
        return false;
    bool bOk = Test.TestTrue(TEXT("An opponent at a target wears it down"), Director->TaskProgress().TargetHp[0] < Whole &&
        Director->TaskProgress().TargetHp[0] >= Whole - 2 * SoraBeatRules::SiegeHpPerSecond);
    Foes[0]->SetActorTickEnabled(true);
    UGameplayStatics::ApplyDamage(Foes[0], Foes[0]->Health, Player(State)->GetController(), Player(State), UDamageType::StaticClass());
    if (!Advance(Test, State))
        return false;
    // The siege is repaired back to whole at the defended position before the target is tested.
    FVector Position;
    if (!Director->ObjectiveAnchor(Position))
        return Fail(Test, State, Where(State) + TEXT(" has no defended position"));
    MoveTo(State, Position);
    if (!Advance(Test, State))
        return false;
    GameMode->Interact(Player(State));
    bOk &= Test.TestEqual(TEXT("A repair makes the besieged target whole"), Director->TaskProgress().TargetHp[0], Rules.TargetHp[0]);
    bOk &= Test.TestFalse(TEXT("A wounded target is no failure"), Director->DamageDefendedTarget(0, Rules.TargetHp[0] / 2));
    // A repair at the defended position mends a quarter of it.
    FVector Anchor;
    if (!Director->ObjectiveAnchor(Anchor))
        return Fail(Test, State, Where(State) + TEXT(" has no defended position"));
    MoveTo(State, Anchor);
    if (!Advance(Test, State))
        return false;
    GameMode->Interact(Player(State));
    bOk &= Test.TestEqual(TEXT("A repair mends the wounded target"), Director->TaskProgress().TargetHp[0],
        Rules.TargetHp[0] / 2 + Rules.TargetHp[0] / 4);
    bOk &= Test.TestTrue(TEXT("A destroyed target fails the defence"), Director->DamageDefendedTarget(0, Rules.TargetHp[0]) &&
        GameMode->bDefeated && GameMode->InputState() == SoraInput::Result);
    ++State.Failures;
    GameMode->BeginRound();
    bOk &= Test.TestFalse(TEXT("Enter retries the defence"), GameMode->bDefeated);
    bOk &= Test.TestEqual(TEXT("The retry returns to the defence's checkpoint"), Director->ActiveBeat(), Beat);
    bOk &= Test.TestEqual(TEXT("Every target is whole again"), Director->TaskProgress().TargetHp[0], Rules.TargetHp[0]);
    return (bOk || Fail(Test, State, TEXT("A lost defended target did not fail to the checkpoint"))) && Advance(Test, State);
}

// A guard's alarm in a stealth zone that reinforces on detection (ch05.b02):
// the reinforcement wave comes, and the zone still ends at its exit.
bool RaiseAlarm(FAutomationTestBase& Test, FState& State)
{
    USoraCampaignDirector* Director = Campaign(State);
    const SoraBeatRules::FTask Rules = Director->ActiveTask();
    if (!Test.TestTrue(TEXT("The zone reinforces on detection"), Rules.Type == SoraBeatRules::EType::StealthZone &&
        Rules.OnDetected == SoraBeatRules::EDetected::Reinforce))
        return Fail(Test, State, Where(State) + TEXT(" is no reinforcing stealth zone"));
    const int32 Before = LiveEnemies(State).Num();
    bool bOk = Test.TestFalse(TEXT("The alarm wave waits for an alarm"), SoraBeatRules::Released(Director->TaskProgress(), Rules.ReinforceWave));
    Director->RaiseBeatEvent(TEXT("alert_state:alert"));
    if (!Advance(Test, State))
        return false;
    bOk &= Test.TestTrue(TEXT("Detection calls the reinforcements"), SoraBeatRules::Released(Director->TaskProgress(), Rules.ReinforceWave) &&
        LiveEnemies(State).Num() > Before);
    bOk &= Test.TestFalse(TEXT("Detection with reinforcements is no defeat"), Mode(State)->bDefeated);
    return bOk || Fail(Test, State, TEXT("The alarm did not reinforce the zone"));
}

// The director's telemetry rows for this run's slot: every beat of the
// campaign completes exactly once, every required beat starts once, every
// cinematic was skipped with Enter, and each failure, in-place retry and
// restored checkpoint is on record. The totals are logged and written to
// Saved/Telemetry/campaign_playthrough_totals.json.
bool CheckTelemetry(FAutomationTestBase& Test, FState& State)
{
    const FString Path = FPaths::ProjectSavedDir() / TEXT("Telemetry/campaign_beats.jsonl");
    TArray<FString> Lines;
    if (!Test.TestTrue(TEXT("The beat telemetry is written"), FFileHelper::LoadFileToStringArray(Lines, *Path)))
        return Fail(Test, State, TEXT("No beat telemetry at ") + Path);
    TMap<FString, int32> Events, Completed;
    TMap<FString, int64> ClockMs;
    int32 Rows = 0;
    for (const FString& Line : Lines)
    {
        if (!Line.Contains(State.Slot))
            continue;
        TSharedPtr<FJsonObject> Row;
        const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Line);
        if (!FJsonSerializer::Deserialize(Reader, Row) || !Row.IsValid() ||
            Row->GetStringField(TEXT("slot")) != State.Slot)
            return Fail(Test, State, TEXT("Unreadable telemetry row: ") + Line);
        ++Rows;
        const FString Event = Row->GetStringField(TEXT("event"));
        ++Events.FindOrAdd(Event);
        if (Event == TEXT("complete"))
        {
            ++Completed.FindOrAdd(Row->GetStringField(TEXT("beat")));
            ClockMs.FindOrAdd(Row->GetStringField(TEXT("chapter"))) += static_cast<int64>(Row->GetNumberField(TEXT("beat_ms")));
        }
    }
    const auto Count = [&](const TCHAR* Event) { const int32* Found = Events.Find(Event); return Found ? *Found : 0; };
    const FSoraCatalog& Data = FSoraCatalog::Get();
    int32 Beats = 0, Required = 0;
    bool bOk = true;
    for (int32 Chapter = 0; Chapter <= LastChapter; ++Chapter)
        for (int32 Index = 0; Index < Data.Chapter(Chapter).Beats.Num(); ++Index)
        {
            const FString& Id = Data.Chapter(Chapter).Beats[Index].Id;
            const int32* Times = Completed.Find(Id);
            bOk &= Test.TestEqual(*(Id + TEXT(" completes once in the telemetry")), Times ? *Times : 0, 1);
            ++Beats;
            Required += !Data.Chapter(Chapter).Rules[Index].Optional||Data.Chapter(Chapter).Wood.Beat==Index;
        }
    bOk &= Test.TestEqual(TEXT("Telemetry: every required beat and the walkable wood starts once"), Count(TEXT("start")), Required);
    bOk &= Test.TestEqual(TEXT("Telemetry: every beat completes"), Count(TEXT("complete")), Beats);
    bOk &= Test.TestEqual(TEXT("Telemetry: every chapter completes"), Count(TEXT("chapter_complete")), LastChapter + 1);
    bOk &= Test.TestEqual(TEXT("Telemetry: every cinematic is skipped with Enter"), Count(TEXT("skip")), State.CinematicShots);
    bOk &= Test.TestEqual(TEXT("Telemetry: each failure is on record"), Count(TEXT("failed")), State.Failures);
    bOk &= Test.TestEqual(TEXT("Telemetry: the lost match is retried in place"), Count(TEXT("retry")), State.InPlaceRetries);
    bOk &= Test.TestEqual(TEXT("Telemetry: each restored checkpoint and failure resumes its beat"), Count(TEXT("resume")),
        State.CheckpointReloads + State.PhaseReloads + State.Failures);
    bOk &= Test.TestTrue(TEXT("Telemetry: a boss or duel phase is on record"), Count(TEXT("phase")) >= State.PhaseReloads);
    // The totals, events and each chapter's beat clock (the automation's
    // compressed time, not a pacing measurement).
    Events.KeySort(TLess<FString>());
    const TSharedRef<FJsonObject> Totals = MakeShared<FJsonObject>();
    const TSharedRef<FJsonObject> EventTotals = MakeShared<FJsonObject>();
    const TSharedRef<FJsonObject> Clock = MakeShared<FJsonObject>();
    FString EventText, ClockText;
    for (const TPair<FString, int32>& Pair : Events)
    {
        EventTotals->SetNumberField(Pair.Key, Pair.Value);
        EventText += FString::Printf(TEXT("%s%s=%d"), EventText.IsEmpty() ? TEXT("") : TEXT(","), *Pair.Key, Pair.Value);
    }
    for (int32 Chapter = 0; Chapter <= LastChapter; ++Chapter)
    {
        const int64* Ms = ClockMs.Find(Data.Chapter(Chapter).Id);
        const double Seconds = Ms ? *Ms / 1000.0 : 0.0;
        Clock->SetNumberField(Data.Chapter(Chapter).Id, Seconds);
        ClockText += FString::Printf(TEXT("%s%.1f"), ClockText.IsEmpty() ? TEXT("") : TEXT(","), Seconds);
    }
    Totals->SetStringField(TEXT("slot"), State.Slot);
    Totals->SetStringField(TEXT("utc"), FDateTime::UtcNow().ToIso8601());
    Totals->SetNumberField(TEXT("telemetry_rows"), Rows);
    Totals->SetObjectField(TEXT("events"), EventTotals);
    Totals->SetObjectField(TEXT("beat_clock_s"), Clock);
    Totals->SetNumberField(TEXT("chapters"), State.ChaptersCompleted);
    Totals->SetNumberField(TEXT("beats"), Beats);
    Totals->SetNumberField(TEXT("required_beats"), Required);
    Totals->SetNumberField(TEXT("caches"), State.CachesOpened);
    Totals->SetNumberField(TEXT("pickups"), State.PickupsFound);
    Totals->SetNumberField(TEXT("rides"), State.RidesRidden);
    Totals->SetNumberField(TEXT("cinematics"), State.CinematicShots);
    Totals->SetNumberField(TEXT("lines"), State.LinesShown);
    Totals->SetNumberField(TEXT("checkpoints_read"), State.CheckpointsRead);
    Totals->SetNumberField(TEXT("checkpoint_reloads"), State.CheckpointReloads);
    Totals->SetNumberField(TEXT("phase_reloads"), State.PhaseReloads);
    Totals->SetNumberField(TEXT("conscripts_down"), State.ConscriptsDown);
    Totals->SetNumberField(TEXT("conscripts_freed"), State.ConscriptsFreed);
    Totals->SetNumberField(TEXT("party_tended"), State.PartyTended);
    Totals->SetNumberField(TEXT("party_sent_on"), State.PartySentOn);
    Totals->SetNumberField(TEXT("fires_relit"), State.FiresRelit);
    Totals->SetNumberField(TEXT("loads_hoisted"), State.LoadsHoisted);
    Totals->SetNumberField(TEXT("objectives_held"), State.ObjectivesHeld);
    Totals->SetNumberField(TEXT("worlds"), State.WorldsStarted);
    FString Json;
    const TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Json);
    bOk &= Test.TestTrue(TEXT("The telemetry totals serialize"), FJsonSerializer::Serialize(Totals, Writer));
    bOk &= Test.TestTrue(TEXT("The telemetry totals are written"), FFileHelper::SaveStringToFile(Json,
        *(FPaths::ProjectSavedDir() / TEXT("Telemetry/campaign_playthrough_totals.json")), FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM));
    UE_LOG(LogTemp, Display, TEXT("SORA_CAMPAIGN_TELEMETRY: rows=%d beats=%d required=%d events=[%s] beat_clock_s=[%s]"),
        Rows, Beats, Required, *EventText, *ClockText);
    return bOk || Fail(Test, State, TEXT("The beat telemetry does not match the playthrough"));
}

// One blow through two phase thresholds (ch07.b13: health 1000, 600, 300):
// both phases play their lines in order and the later one saves; and a
// killing blow from full health plays every phase it passes before the fall,
// the disarmed gunslinger yielding upright (bible §8: knocked down, not killed).
bool PhaseCrossing(FAutomationTestBase& Test, FState& State)
{
    constexpr int32 Flagship = 6;
    const FSoraChapter& Data = FSoraCatalog::Get().Chapter(Flagship);
    const int32 Beat = Data.BeatIndex(TEXT("ch07.b13"));
    const SoraBeatRules::FTask& Rules = Data.Tasks[Beat];
    if (!Test.TestTrue(TEXT("ch07.b13 has three phases and spares its boss"), Rules.PhaseCount == 3 &&
        Rules.Defeat == SoraBeatRules::EDefeat::Spare && Data.Rules[Beat].PhaseCheckpoints == 2))
        return Fail(Test, State, TEXT("ch07.b13 is not the three-phase disarm this test needs"));
    for (const bool bLethal : {false, true})
    {
        // The old world goes first: its teardown collects garbage, which an
        // unreferenced save object made before it would not survive.
        if (!StopWorld(Test, State))
            return false;
        USoraSaveGame* Seeded = Cast<USoraSaveGame>(UGameplayStatics::CreateSaveGameObject(USoraSaveGame::StaticClass()));
        if (!Seeded || !USoraCampaignDirector::SeedCheckpoint(*Seeded, Flagship, Beat) ||
            !UGameplayStatics::SaveGameToSlot(Seeded, State.Slot, 0) || !StartWorld(Test, State) || !Resume(Test, State))
            return Fail(Test, State, TEXT("ch07.b13 could not be seeded"));
        USoraCampaignDirector* Director = Campaign(State);
        ASoraEnemy* Boss = PhasedOpponent(State);
        if (!Test.TestTrue(TEXT("The gunslinger stands at full health"), Boss && Director->ActiveBeat() == Beat && Director->ActivePhase() == 0))
            return Fail(Test, State, TEXT("ch07.b13 did not begin"));
        const float Left = bLethal ? 0.f : Boss->MaxHealth * (Rules.PhaseStart[2] - 50) / 1000.f;
        UGameplayStatics::ApplyDamage(Boss, Boss->Health - Left, Player(State)->GetController(), Player(State), UDamageType::StaticClass());
        const bool bUpright = FMath::Abs(Boss->GetActorRotation().Roll) < 1.f;
        if (!Advance(Test, State, 1))
            return false;
        const TArray<FSoraSubtitle> Queued = Director->QueuedSubtitles();
        const auto At = [&](const TCHAR* Event, bool bLast) -> int32
        {
            int32 Found = bLast ? INDEX_NONE : MAX_int32;
            for (const FSoraDialogueTrigger& Row : Data.Triggers)
                if (Row.Beat == Beat && Row.On == Event)
                    for (const int32 Line : Row.Lines)
                    {
                        const int32 Where = Queued.IndexOfByPredicate([&](const FSoraSubtitle& Sub) { return Sub.LineId == Data.Dialogue[Line].Id; });
                        Found = Where == INDEX_NONE ? INDEX_NONE : bLast ? FMath::Max(Found, Where) : FMath::Min(Found, Where);
                        if (Where == INDEX_NONE)
                            return INDEX_NONE;
                    }
            return Found;
        };
        const int32 SecondEnds = At(TEXT("boss_phase:2"), true), ThirdBegins = At(TEXT("boss_phase:3"), false);
        const FString Context = bLethal ? TEXT("ch07.b13, felled from full health in one blow") : TEXT("ch07.b13, struck past two thresholds");
        bool bOk = Test.TestTrue(*(Context + TEXT(": both phases play their lines, in order")),
            SecondEnds != INDEX_NONE && ThirdBegins != INDEX_NONE && ThirdBegins != MAX_int32 && SecondEnds < ThirdBegins);
        if (bLethal)
        {
            bOk &= Test.TestTrue(*(Context + TEXT(": the fight ends and the boss's fall plays")),
                Director->ActiveBeat() != Beat && At(TEXT("boss_defeated"), true) != INDEX_NONE);
            bOk &= Test.TestTrue(*(Context + TEXT(": the disarmed gunslinger yields upright")), bUpright);
        }
        else
        {
            const USoraSaveGame* Saved = Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(State.Slot, 0));
            bOk &= Test.TestTrue(*(Context + TEXT(": the last phase begins and saves")), Director->ActivePhase() == 2 &&
                Saved && Saved->CheckpointBeat == Beat && Saved->CheckpointPhase == 2);
        }
        if (!bOk)
            return Fail(Test, State, Context + TEXT(" skipped a phase"));
    }
    return true;
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
} // namespace SoraCampaignPlaythrough

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraCampaignPlaythroughTest,
    "SoraArena.Campaign.Playthrough",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraCampaignPlaythroughTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraCampaignPlaythrough;
    const FSoraCatalog& Catalog = FSoraCatalog::Get();
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()) ||
        !TestEqual(TEXT("Eight campaign chapters"), Catalog.Chapters.Num(), SoraCampaignPlaythrough::LastChapter + 1))
        return false;
    for (int32 Chapter = 0; Chapter <= SoraCampaignPlaythrough::LastChapter; ++Chapter)
        if (!TestEqual(*FString::Printf(TEXT("Chapter %d has three production sites"), Chapter + 1), Catalog.Chapter(Chapter).Sites.Num(), 3))
            return false;
    FSoraAutomationWorld::IgnoreMissingGeneratedArt(*this);
    const FStateRef State = MakeShared<FState>();
    FSoraAutomationWorld::IgnoreAbsentSaveSlot(*this, State->Slot);

    // The dojo from a new save, through the lesson duels to its smithy.
    Step(this, State, [](FAutomationTestBase& Test, FState& S)
    {
        if (!Test.TestFalse(TEXT("The isolated save slot starts empty"), UGameplayStatics::DoesSaveGameExist(S.Slot, 0)))
            return Fail(Test, S, TEXT("Automation save slot already exists"));
        if (!StartWorld(Test, S))
            return false;
        Mode(S)->BeginRound();
        if (!Test.TestFalse(TEXT("Closing the menu unpauses the world"), Paused(S)) || !ExpectOpening(Test, S, 0))
            return false;
        return PlayUntil(Test, S, 8);
    });
    // Mid-dojo: the forms, two sites and the yumi survive world teardown.
    Step(this, State, [](FAutomationTestBase& Test, FState& S)
    {
        const int32 Worlds = S.WorldsStarted;
        return CheckpointReload(Test, S) && Test.TestEqual(TEXT("The smithy's checkpoint is restored in a fresh world"), S.WorldsStarted, Worlds + 1) &&
            Test.TestTrue(TEXT("Restored pupils can be scored"), Campaign(S)->CanScoreDojoBout()) && FinishChapter(Test, S);
    });
    // The invasion: the dojo's yumi is carried in; a pack horse is lost to
    // its defence's checkpoint; Dunark's phases are restored in fresh worlds.
    Step(this, State, [](FAutomationTestBase& Test, FState& S)
    {
        return PlayUntil(Test, S, 1) && ExpectWeapon(Test, S, 18, true) && PlayUntil(Test, S, 5) && LoseDefendedTarget(Test, S) &&
            FinishChapter(Test, S);
    });
    // Occupied streets: a defeat is retried from the workshop fight's checkpoint.
    Step(this, State, [](FAutomationTestBase& Test, FState& S)
    {
        return PlayUntil(Test, S, 7) && DefeatAndRetry(Test, S) && FinishChapter(Test, S);
    });
    Step(this, State, [](FAutomationTestBase& Test, FState& S) { return FinishChapter(Test, S); });
    // The foundry: the kanna-nagashi zone is restored, then its guards raise the alarm.
    Step(this, State, [](FAutomationTestBase& Test, FState& S)
    {
        const int32 Worlds = S.WorldsStarted;
        return PlayUntil(Test, S, 1) && CheckpointReload(Test, S) &&
            Test.TestEqual(TEXT("The kanna-nagashi checkpoint is restored in a fresh world"), S.WorldsStarted, Worlds + 1) &&
            RaiseAlarm(Test, S) && FinishChapter(Test, S);
    });
    // The vault: the foundry's arc carbine is carried in, and the optional
    // armory's cache gives the phantom SMG.
    Step(this, State, [](FAutomationTestBase& Test, FState& S)
    {
        return PlayUntil(Test, S, 1) && ExpectWeapon(Test, S, 1, true) && FinishChapter(Test, S);
    });
    // The flagship: the armory's phantom SMG is carried in, so the war
    // council's grant adds nothing; the seized vault's cache holds the dojo's
    // name board, whose story flag the final chapter reads.
    Step(this, State, [](FAutomationTestBase& Test, FState& S)
    {
        if (!Test.TestTrue(TEXT("The vault armory's phantom SMG is carried into the flagship"), Campaign(S)->IsWeaponUnlocked(PhantomSmg)) ||
            !Test.TestFalse(TEXT("The name board is not yet marked"), Campaign(S)->IsStoryFlagSet(TEXT("nafudakake_marked"))))
            return Fail(Test, S, TEXT("The flagship was entered with the wrong unlocks"));
        if (!PlayUntil(Test, S) ||
            !Test.TestTrue(TEXT("Marking the name board sets its story flag"), Campaign(S)->IsStoryFlagSet(TEXT("nafudakake_marked"))))
            return Fail(Test, S, TEXT("The name board's story flag was not set"));
        return NextChapter(Test, S);
    });
    Step(this, State, [](FAutomationTestBase& Test, FState& S)
    {
        const USoraSaveGame* Saved = Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(S.Slot, 0));
        if (!Test.TestTrue(TEXT("The final chapter is entered with the name board's story flag"),
            Campaign(S)->IsStoryFlagSet(TEXT("nafudakake_marked")) && Saved && Saved->ChapterEntryFlags != 0))
            return Fail(Test, S, TEXT("The story flag did not reach the final chapter"));
        if (!PlayUntil(Test, S) || !Test.TestEqual(TEXT("Every weapon is unlocked"), Campaign(S)->Progress().WeaponsMask, SoraBeatRules::AllWeaponsMask) ||
            !Test.TestEqual(TEXT("Every mechanic is unlocked"), Campaign(S)->Progress().MechanicsMask, SoraBeatRules::AllMechanicsMask))
            return Fail(Test, S, TEXT("The final chapter did not end with every unlock"));
        return NextChapter(Test, S);
    });
    // Liberation is durable: a fresh world shows the freed city, not a new
    // battle, and every find of the campaign is still in the codex.
    Step(this, State, [](FAutomationTestBase& Test, FState& S)
    {
        if (!Reload(Test, S))
            return false;
        const ASoraGameMode* GameMode = Mode(S);
        const USoraSaveGame* Saved = Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(S.Slot, 0));
        bool bOk = Test.TestTrue(TEXT("The reloaded campaign is liberated"), Campaign(S)->bCampaignComplete && GameMode->bChapterComplete);
        bOk &= Test.TestEqual(TEXT("The liberated city shows every site"), GameMode->Arena()->ActivatedMask(), 7);
        bOk &= Test.TestTrue(TEXT("No opponent returns to the liberated city"), LiveEnemies(S).IsEmpty());
        bOk &= Test.TestEqual(TEXT("Every collectible of the campaign is kept"), static_cast<uint64>(Campaign(S)->CollectedMask()),
            static_cast<uint64>(AllCollectibles()));
        bOk &= Test.TestEqual(TEXT("Every collectible of the campaign is saved"), Saved ? static_cast<uint64>(Saved->Collectibles) : 0ull,
            static_cast<uint64>(AllCollectibles()));
        bOk &= Test.TestTrue(TEXT("No loose find is left lying"), Campaign(S)->LoosePickups().IsEmpty());
        int32 Loose = 0;
        for (int32 Chapter = 0; Chapter <= SoraCampaignPlaythrough::LastChapter; ++Chapter)
            Loose += FSoraCatalog::Get().Chapter(Chapter).Space.Pickups.Num();
        bOk &= Test.TestEqual(TEXT("Every loose find was picked up in its chapter"), S.PickupsFound, Loose);
        return bOk || Fail(Test, S, TEXT("Liberation did not survive reload"));
    });
    // The unlocks came in the authored order, and the telemetry agrees with the play.
    Step(this, State, [](FAutomationTestBase& Test, FState& S)
    {
        const TArray<FString> Weapons = AuthoredUnlocks(true), Mechanics = AuthoredUnlocks(false);
        bool bOk = Test.TestEqual(TEXT("21 weapons are authored"), Weapons.Num(), SoraBeatRules::WeaponCount);
        bOk &= Test.TestEqual(TEXT("19 mechanics are authored"), Mechanics.Num(), SoraBeatRules::MechanicCount);
        bOk &= Test.TestEqual(TEXT("The weapons unlock in the authored order"), FString::Join(S.WeaponOrder, TEXT(" ")), FString::Join(Weapons, TEXT(" ")));
        bOk &= Test.TestEqual(TEXT("The mechanics unlock in the authored order"), FString::Join(S.MechanicOrder, TEXT(" ")), FString::Join(Mechanics, TEXT(" ")));
        bOk &= Test.TestEqual(TEXT("Each holdable arm after the dojo is refused before its beat"), S.ArmsRefused, GatedArms());
        bOk &= Test.TestEqual(TEXT("Each holdable arm after the dojo equips from its beat on"), S.ArmsEquipped, GatedArms());
        bOk &= Test.TestTrue(TEXT("An arm is taken up in the beat that hands it over, before the beat completes"), S.ArmsInTheirBeat > 0);
        // Every beat was played, and every task goal the chapters author.
        const FSoraCatalog& Data = FSoraCatalog::Get();
        TSet<int32> Authored;
        int32 Beats = 0;
        for (int32 Chapter = 0; Chapter <= SoraCampaignPlaythrough::LastChapter; ++Chapter)
            for (const SoraBeatRules::FTask& Task : Data.Chapter(Chapter).Tasks)
            {
                Authored.Add(static_cast<int32>(Task.Goal));
                ++Beats;
            }
        bOk &= Test.TestEqual(TEXT("Every beat of the campaign was played"), S.BeatsPlayed + S.CachesOpened, Beats);
        // The two captures (ch06.b13's bulkhead, ch08.b14's engine spine), the
        // caches whose opening saved, and a fallen guard's patrol forgotten.
        int32 Captured = 0, SavingCaches = 0;
        for (int32 Chapter = 0; Chapter <= SoraCampaignPlaythrough::LastChapter; ++Chapter)
            for (int32 Index = 0; Index < Data.Chapter(Chapter).Beats.Num(); ++Index)
            {
                Captured += Data.Chapter(Chapter).Tasks[Index].Defeat == SoraBeatRules::EDefeat::Capture;
                SavingCaches += Data.Chapter(Chapter).Beats[Index].Has(SoraBeatRules::EGoal::Cache) && Data.Chapter(Chapter).Rules[Index].Checkpoint;
            }
        bOk &= Test.TestEqual(TEXT("Every captured boss was bound by hand"), S.Captures, Captured);
        bOk &= Test.TestEqual(TEXT("Every cache that saves wrote its checkpoint"), S.CacheCheckpoints, SavingCaches);
        bOk &= Test.TestTrue(TEXT("A fallen guard was seen to leave its patrol"), S.bGuardForgotten);
        FString Goals;
        for (int32 Goal = 0; Goal <= static_cast<int32>(SoraBeatRules::EGoal::Found); ++Goal)
        {
            const int32* Played = S.GoalsPlayed.Find(Goal);
            bOk &= Test.TestTrue(*FString::Printf(TEXT("Task goal %d was played"), Goal), !Authored.Contains(Goal) || (Played && *Played > 0));
            Goals += FString::Printf(TEXT("%s%d"), Goals.IsEmpty() ? TEXT("") : TEXT(","), Played ? *Played : 0);
        }
        if (!bOk || !CheckTelemetry(Test, S))
            return Fail(Test, S, TEXT("The playthrough's unlocks, beats or telemetry are wrong"));
        bOk &= Test.TestTrue(TEXT("Debt-bound conscripts were knocked down and freed"), S.ConscriptsDown > 0 && S.ConscriptsFreed > 0);
        // ch05.b03's six collars and ch08.b07's four cells were opened by hand.
        bOk &= Test.TestTrue(TEXT("The escorted parties' collars and cells were opened by hand"), S.PartyTended >= 10);
        // ch03.b14's three cook-fires gutter and are relit; ch03.b05's three crates are hoisted by hand.
        bOk &= Test.TestTrue(TEXT("Every guttered cook-fire was relit by hand"), S.FiresRelit >= 3);
        bOk &= Test.TestTrue(TEXT("Every hoisted load was held for"), S.LoadsHoisted >= 3);
        // ch03.b10's charge and fuse, ch06.b04's three relay nodes and ch06.b11's three presses.
        bOk &= Test.TestTrue(TEXT("Every objective with a hold was worked with Interact held"), S.ObjectivesHeld >= 8);
        UE_LOG(LogTemp, Display, TEXT("SORA_CAMPAIGN_PLAYTHROUGH_OK: chapters=%d beats=%d caches=%d pickups=%d rides=%d shots=%d checkpoints=%d reloads=%d phase_reloads=%d arms=%d lines=%d worlds=%d conscripts_down=%d conscripts_freed=%d party_tended=%d party_sent_on=%d fires_relit=%d loads_hoisted=%d objectives_held=%d goals=[%s]"),
            S.ChaptersCompleted, S.BeatsPlayed, S.CachesOpened, S.PickupsFound, S.RidesRidden, S.CinematicShots, S.CheckpointsRead,
            S.CheckpointReloads, S.PhaseReloads, S.ArmsEquipped, S.LinesShown, S.WorldsStarted, S.ConscriptsDown, S.ConscriptsFreed,
            S.PartyTended, S.PartySentOn, S.FiresRelit, S.LoadsHoisted, S.ObjectivesHeld, *Goals);
        return true;
    });
    // The route that skipped the vault armory: a save entering the flagship
    // without the phantom SMG (the only optional weapon before it) is
    // accepted, and the war council's opening grants it beside the repeater.
    Step(this, State, [](FAutomationTestBase& Test, FState& S)
    {
        const FSoraCatalog& Data = FSoraCatalog::Get();
        const unsigned Minimum = Data.RouteMinimumWeapons(FlagshipChapter);
        if (!Test.TestEqual(TEXT("Only the phantom SMG is optional before the flagship"), Data.EarlierWeapons(FlagshipChapter) & ~Minimum,
            1u << PhantomSmg) || !StopWorld(Test, S))
            return Fail(Test, S, TEXT("The skipped-armory route cannot be set up"));
        USoraSaveGame* Skipped = Cast<USoraSaveGame>(UGameplayStatics::CreateSaveGameObject(USoraSaveGame::StaticClass()));
        if (!Test.TestNotNull(TEXT("A save object for the skipped-armory route"), Skipped))
            return Fail(Test, S, TEXT("No save object"));
        Skipped->SaveSchema = USoraSaveGame::Schema;
        Skipped->CurrentChapter = FlagshipChapter;
        Skipped->HighestChapter = FlagshipChapter;
        Skipped->ChapterEntryWeapons = static_cast<int32>(Minimum);
        Skipped->ChapterEntryMechanics = static_cast<int32>(Data.EarlierMechanics(FlagshipChapter));
        if (!Test.TestTrue(TEXT("The skipped-armory save is written"), UGameplayStatics::SaveGameToSlot(Skipped, S.Slot, 0)) || !StartWorld(Test, S))
            return Fail(Test, S, TEXT("The skipped-armory route did not start"));
        Mode(S)->BeginRound();
        if (!ExpectOpening(Test, S, FlagshipChapter) ||
            !Test.TestFalse(TEXT("The skipped armory leaves the phantom SMG locked"), Campaign(S)->IsWeaponUnlocked(PhantomSmg)))
            return Fail(Test, S, TEXT("The skipped-armory route entered the flagship wrongly"));
        S.KnownWeapons = Minimum;
        S.KnownMechanics = Data.EarlierMechanics(FlagshipChapter);
        S.WeaponOrder.Reset();
        if (!PlayUntil(Test, S, 1))
            return false;
        // The council's own weapons and its grant arrive together, as one beat's unlocks.
        const SoraBeatRules::FBeat& Council = Data.Chapter(FlagshipChapter).Rules[0];
        TArray<FString> Granted;
        for (int32 Id = 0; Id < SoraBeatRules::WeaponCount; ++Id)
            if (((Council.WeaponsMask | Council.GrantsMask) & ~Minimum & (1u << Id)) != 0u)
                Granted.Add(FString::Printf(TEXT("%d@%s"), Id, *Data.Chapter(FlagshipChapter).Beats[0].Id));
        const FString Name = Data.Weapon(PhantomSmg).NameEnglish;
        bool bOk = Test.TestTrue(TEXT("The war council grants the phantom SMG"), Campaign(S)->IsWeaponUnlocked(PhantomSmg) &&
            (Council.GrantsMask & (1u << PhantomSmg)) != 0u);
        bOk &= Test.TestEqual(TEXT("The council's weapons and the granted phantom SMG arrive together"),
            FString::Join(S.WeaponOrder, TEXT(" ")), FString::Join(Granted, TEXT(" ")));
        bOk &= Test.TestTrue(TEXT("The grant is announced with the council's weapons"), Campaign(S)->StoryNotices().ContainsByPredicate(
            [&Name](const FSoraStoryNotice& Notice) { return Notice.Kind == FSoraStoryNotice::EKind::Weapon && Notice.English.Contains(Name); }));
        return bOk || Fail(Test, S, TEXT("The skipped armory's phantom SMG was not granted"));
    });
    Step(this, State, [](FAutomationTestBase& Test, FState& S) { return PhaseCrossing(Test, S); });
    Step(this, State, [](FAutomationTestBase& Test, FState& S)
    {
        if (!StopWorld(Test, S))
            return false;
        Test.TestEqual(TEXT("All eight chapters completed"), S.ChaptersCompleted, SoraCampaignPlaythrough::LastChapter + 1);
        FSoraAutomationWorld::DeleteSaveSlot(S.Slot);
        Test.TestFalse(TEXT("The isolated save slot is removed"), UGameplayStatics::DoesSaveGameExist(S.Slot, 0));
        return true;
    });
    return true;
}
#endif
