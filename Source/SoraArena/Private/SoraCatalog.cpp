#include "SoraCatalog.h"
#include "SoraCampaignRules.h"
#include "SoraCatalogJson.h"
#include "SoraCatalogRegistry.h"

namespace
{
using namespace SoraCatalogJson;

// A beat's task block (build_campaign_data.py normalize_task): the goal and
// its integer parameters for SoraBeatRules, and the names the director uses.
// Every key is required; SoraBeatRules::TaskValid then checks the numbers.
bool ReadTask(const FJsonObject& O, const FString& TypeName, FSoraBeat& Beat)
{
    using namespace SoraBeatRules;
    static const TMap<FString, EType> Types = {
        {TEXT("cinematic"), EType::Cinematic}, {TEXT("dialogue"), EType::Dialogue}, {TEXT("combat_wave"), EType::CombatWave},
        {TEXT("duel"), EType::Duel}, {TEXT("stealth_zone"), EType::StealthZone}, {TEXT("production_task"), EType::ProductionTask},
        {TEXT("horseback_ride"), EType::HorsebackRide}, {TEXT("boss"), EType::Boss},
        {TEXT("explore_optional"), EType::ExploreOptional}, {TEXT("collectible"), EType::Collectible}};
    static const TMap<FString, ETask> Tasks = {
        {TEXT("hold"), ETask::Hold}, {TEXT("crank"), ETask::Crank}, {TEXT("escort"), ETask::Escort},
        {TEXT("carry"), ETask::Carry}, {TEXT("manufacture"), ETask::Manufacture}, {TEXT("defend"), ETask::Defend}};
    static const TMap<FString, EGoal> Goals = {
        {TEXT("elapsed"), EGoal::Elapsed}, {TEXT("lines"), EGoal::Lines}, {TEXT("waves_cleared"), EGoal::WavesCleared},
        {TEXT("objectives"), EGoal::Objectives}, {TEXT("survive"), EGoal::Survive}, {TEXT("points"), EGoal::Points},
        {TEXT("lessons"), EGoal::Lessons}, {TEXT("opponent_down"), EGoal::OpponentDown}, {TEXT("exit"), EGoal::Exit},
        {TEXT("hold"), EGoal::Hold}, {TEXT("turns"), EGoal::Turns}, {TEXT("escort"), EGoal::Escort},
        {TEXT("deliveries"), EGoal::Deliveries}, {TEXT("steps"), EGoal::Steps}, {TEXT("cache"), EGoal::Cache},
        {TEXT("found"), EGoal::Found}};
    static const TMap<FString, EWaveTrigger> Triggers = {
        {TEXT("start"), EWaveTrigger::Start}, {TEXT("prev_cleared"), EWaveTrigger::PrevCleared},
        {TEXT("alive_below"), EWaveTrigger::AliveBelow}, {TEXT("after_ms"), EWaveTrigger::AfterMs},
        {TEXT("progress_at"), EWaveTrigger::ProgressAt}, {TEXT("volume"), EWaveTrigger::Volume}, {TEXT("event"), EWaveTrigger::Event}};
    static const TMap<FString, EContest> Contests = {
        {TEXT("none"), EContest::None}, {TEXT("pause"), EContest::Pause}, {TEXT("decay"), EContest::Decay}};
    static const TMap<FString, ELoss> Losses = {
        {TEXT("checkpoint"), ELoss::Checkpoint}, {TEXT("retry"), ELoss::Retry}, {TEXT("continue_after"), ELoss::ContinueAfter}};
    static const TMap<FString, EDefeat> Defeats = {
        {TEXT("kill"), EDefeat::Kill}, {TEXT("spare"), EDefeat::Spare}, {TEXT("capture"), EDefeat::Capture}};
    static const TMap<FString, EDetected> Detections = {
        {TEXT("combat"), EDetected::Combat}, {TEXT("restart"), EDetected::Restart}, {TEXT("reinforce"), EDetected::Reinforce}};
    static const TMap<FString, EFail> Failures = {
        {TEXT("player_died"), EFail::PlayerDied}, {TEXT("match_lost"), EFail::MatchLost},
        {TEXT("target_destroyed"), EFail::TargetDestroyed}, {TEXT("escort_down"), EFail::EscortDown},
        {TEXT("convoy_lost"), EFail::ConvoyLost}, {TEXT("detected"), EFail::Detected},
        {TEXT("horse_down"), EFail::HorseDown}, {TEXT("boss_event"), EFail::BossEvent}};
    FTask& T = Beat.Task;
    FString Kind, TaskName, Opponent;
    int32 LessonMask = 0;
    if (!Str(O, TEXT("type"), Kind) || Kind != TypeName || !Named(O, TEXT("type"), Types, T.Type) ||
        !Nullable(O, TEXT("task"), TaskName) || !Named(O, TEXT("goal"), Goals, T.Goal) ||
        !Int(O, TEXT("count"), T.Count) || !Int(O, TEXT("duration_ms"), T.DurationMs) ||
        !O.TryGetBoolField(TEXT("skippable"), T.Skippable) || !O.TryGetBoolField(TEXT("anchor_after_lines"), T.AnchorAfterLines) ||
        !O.TryGetBoolField(TEXT("pause_when_seen"), T.PauseWhenSeen) ||
        !Int(O, TEXT("max_alive"), T.MaxAlive) || !Int(O, TEXT("lesson_mask"), LessonMask) || LessonMask < 0 ||
        !O.TryGetBoolField(TEXT("flank_bouts"), T.FlankBouts) || !Named(O, TEXT("defeat"), Defeats, T.Defeat) ||
        !Nullable(O, TEXT("capture_event"), Beat.CaptureEvent) ||
        !Int(O,TEXT("capture_hold_ms"),Beat.CaptureHoldMs) || Beat.CaptureHoldMs<0 || !Nullable(O, TEXT("carry_item"), Beat.CarryItem) ||
        !Named(O, TEXT("loss"), Losses, T.Loss) || !Int(O, TEXT("loss_limit"), T.LossLimit) ||
        !Named(O, TEXT("contest"), Contests, T.Contest) || !Int(O, TEXT("decay_permille"), T.DecayPermille) ||
        !Int(O, TEXT("min_turn_ms"), T.MinTurnMs) || !Int(O, TEXT("max_turn_ms"), T.MaxTurnMs) ||
        !Int(O, TEXT("speed_cm_s"), T.SpeedCmS) || !Int(O, TEXT("wait_cm"), T.WaitCm) || !Int(O, TEXT("path_cm"), T.PathCm) ||
        !Named(O, TEXT("on_detected"), Detections, T.OnDetected) ||
        !Int(O, TEXT("reinforce_wave"), T.ReinforceWave) || !O.TryGetBoolField(TEXT("horse_down_retries"), T.HorseDownRetries) ||
        !Points(O, TEXT("objectives"), Beat.Objectives) || !Points(O, TEXT("pickups"), Beat.Pickups) ||
        !Points(O, TEXT("dropoffs"), Beat.Dropoffs) || !Nullable(O, TEXT("lines_event"), Beat.LinesEvent) ||
        !Nullable(O, TEXT("closing_event"), Beat.ClosingEvent) || !Nullable(O, TEXT("exit_event"), Beat.ExitEvent) ||
        !Nullable(O, TEXT("opponent"), Opponent) || !O.TryGetBoolField(TEXT("sparring"), Beat.bSparring) ||
        !Strings(Rows(O, TEXT("phase_events")), Beat.PhaseEvents) ||
        !Int(O, TEXT("carry_speed_permille"), T.CarrySpeedPermille) || !Int(O, TEXT("target_loss_limit"), T.TargetLossLimit) ||
        !Int(O, TEXT("pickup_hold_ms"), T.PickupHoldMs) || T.PickupHoldMs < 0 ||
        !WeaponMask(Rows(O, TEXT("carry_weapons")), T.CarryWeaponsMask))
        return false;
    const auto PlayerValue = O.TryGetField(TEXT("crank_player"));
    if (!PlayerValue.IsValid()) return false;
    if (PlayerValue->Type != EJson::Null)
    {
        const auto Player = PlayerValue->Type == EJson::Object ? PlayerValue->AsObject() : nullptr;
        if (!Player || Player->Values.Num() != 5 ||
            !Int(*Player, TEXT("stamina_per_turn"), T.StaminaPerTurn) ||
            !Int(*Player, TEXT("overspeed_cost_multiplier"), T.OverspeedCostMultiplier) ||
            !Player->TryGetBoolField(TEXT("two_handed"), T.CrankTwoHanded) ||
            !Player->TryGetBoolField(TEXT("alternate_treads"), T.AlternateTreads) ||
            !Int(*Player, TEXT("hold_milliturns_s"), T.HoldMilliTurnsS)) return false;
    }
    const auto CoopValue = O.TryGetField(TEXT("crank_coop"));
    if (!CoopValue.IsValid()) return false;
    if (CoopValue->Type != EJson::Null)
    {
        const auto Coop = CoopValue->Type == EJson::Object ? CoopValue->AsObject() : nullptr;
        const FJsonRows* Locks = Coop ? Rows(*Coop, TEXT("ratchets_permille")) : nullptr;
        if (!Coop || Coop->Values.Num() != 6 || !Locks || Locks->Num() > 3 ||
            !Points(*Coop, TEXT("npcs"), Beat.CrankNpcs) || Beat.CrankNpcs.IsEmpty() || Beat.CrankNpcs.Num()>3 ||
            !Int(*Coop, TEXT("per_npc_milliturns_s"), T.CoopMilliTurnsS) || T.CoopMilliTurnsS <= 0 ||
            !Int(*Coop, TEXT("progress_permille"), T.CoopProgressPermille) ||
            !Coop->TryGetBoolField(TEXT("suspends_decay"), T.CoopSuspendsDecay) ||
            !Int(*Coop, TEXT("retreat_cm"), T.CoopRetreatCm)) return false;
        for (int32 Index = 0; Index < Beat.CrankNpcs.Num(); ++Index)
            if (Beat.CrankNpcs.Find(Beat.CrankNpcs[Index]) != Index) return false;
        T.CoopCount = Beat.CrankNpcs.Num();
        T.RatchetCount = Locks->Num();
        for (int32 Index = 0; Index < Locks->Num(); ++Index)
        {
            double Number = 0;
            if (!(*Locks)[Index].IsValid() || !(*Locks)[Index]->TryGetNumber(Number) || Number != FMath::FloorToDouble(Number) || Number <= 0 || Number >= 1000) return false;
            T.Ratchets[Index] = static_cast<int>(Number);
        }
    }
    const auto DropPolicy = Child(O, TEXT("drop_on_hit"));
    const TCHAR* DifficultyNames[] = {TEXT("easy"), TEXT("normal"), TEXT("hard")};
    if (!DropPolicy || DropPolicy->Values.Num() != 3) return false;
    for (int32 Difficulty = 0; Difficulty < 3; ++Difficulty)
    {
        const auto Value = DropPolicy->TryGetField(DifficultyNames[Difficulty]);
        if (!Value.IsValid() || Value->Type != EJson::Boolean || !Value->TryGetBool(T.DropOnHitByDifficulty[Difficulty])) return false;
    }
    ApplyCarryDifficulty(T, 1);
    const auto CarryGate = O.TryGetField(TEXT("carry_gate"));
    if (!CarryGate.IsValid()) return false;
    if (CarryGate->Type != EJson::Null)
    {
        const auto Gate = CarryGate->Type == EJson::Object ? CarryGate->AsObject() : nullptr;
        FString Contest, Tool;
        if (!Gate || Gate->Values.Num()!=4 || !Str(*Gate,TEXT("point"),Beat.CarryGatePoint) ||
            !Int(*Gate,TEXT("hold_ms"),T.CarryGateMs) || T.CarryGateMs<=0 ||
            !Str(*Gate,TEXT("contest"),Contest) || Contest!=TEXT("pause") ||
            !Str(*Gate,TEXT("tool"),Tool) || Tool!=TEXT("yari_ishizuki")) return false;
    }
    if (!TaskName.IsEmpty() && !Tasks.Contains(TaskName)) return false;
    T.Task = TaskName.IsEmpty() ? ETask::None : Tasks[TaskName];
    // A capture names the interaction that binds its boss, and a carry what
    // it moves; nothing else does.
    if ((T.Defeat == EDefeat::Capture) == Beat.CaptureEvent.IsEmpty() ||
        (Beat.CaptureEvent==TEXT("interact:engine_spine"))!=(Beat.CaptureHoldMs>0) ||
        (T.Task == ETask::Carry) == Beat.CarryItem.IsEmpty() || (T.PickupHoldMs > 0 && T.Task != ETask::Carry))
        return false;
    const FJsonRows* RepRows = Rows(O, TEXT("form_reps"));
    if (!RepRows || RepRows->Num() != 4) return false;
    for (int32 Form = 0; Form < 4; ++Form)
    {
        double Number = 0;
        if (!(*RepRows)[Form].IsValid() || !(*RepRows)[Form]->TryGetNumber(Number) || !Whole(Number, T.FormReps[Form]))
            return false;
    }
    T.LessonMask = static_cast<unsigned>(LessonMask);
    const TSharedPtr<FJsonValue> MaaiValue = O.TryGetField(TEXT("maai"));
    if (!MaaiValue.IsValid()) return false;
    if (MaaiValue->Type != EJson::Null)
    {
        const auto M = MaaiValue->Type == EJson::Object ? MaaiValue->AsObject() : nullptr;
        const FJsonRows* Moves = M ? Rows(*M,TEXT("moves")) : nullptr;
        if (!M || !Moves || Moves->IsEmpty() || Moves->Num() > SoraMaaiRules::MaxSteps ||
            !Int(*M,TEXT("inner_cm"),T.Maai.InnerCm) || !Int(*M,TEXT("outer_cm"),T.Maai.OuterCm) ||
            !Int(*M,TEXT("hold_ms"),T.Maai.HoldMs) || !Int(*M,TEXT("facing_permille"),T.Maai.FacingPermille) ||
            !Int(*M,TEXT("hint_ms"),T.Maai.HintMs)) return false;
        T.Maai.Count = Moves->Num();
        for (int32 Index=0;Index<Moves->Num();++Index)
        {
            const auto Move = (*Moves)[Index].IsValid() && (*Moves)[Index]->Type == EJson::Object ? (*Moves)[Index]->AsObject() : nullptr;
            if (!Move || !Int(*Move,TEXT("forward_cm"),T.Maai.Moves[Index].ForwardCm) ||
                !Int(*Move,TEXT("right_cm"),T.Maai.Moves[Index].RightCm)) return false;
        }
    }
    const auto Equipment = O.TryGetField(TEXT("equipment_weapons"));
    const auto Recovery = O.TryGetField(TEXT("recovery"));
    if (!Equipment.IsValid() || !Recovery.IsValid()) return false;
    if (Equipment->Type != EJson::Null)
    {
        T.EquipmentMask=0u;
        if (!WeaponMask(Rows(O,TEXT("equipment_weapons")),T.EquipmentMask)) return false;
    }
    if (Recovery->Type != EJson::Null)
    {
        const auto R = Recovery->Type == EJson::Object ? Recovery->AsObject() : nullptr;
        if (!R || !Str(*R,TEXT("item"),Beat.RecoveryItem) || Beat.RecoveryItem != TEXT("sword_bundle") ||
            !Str(*R,TEXT("interact"),Beat.RecoveryInteract) || Beat.RecoveryInteract != TEXT("act_b05_dry_well_rope") ||
            !Int(*R,TEXT("depth_cm"),T.RecoveryDepthCm) || !Int(*R,TEXT("string_ms"),T.RecoveryStringMs) ||
            !Int(*R,TEXT("quiver"),T.RecoveryQuiver) || !WeaponMask(Rows(*R,TEXT("weapons")),T.RecoveryWeapons)) return false;
    }
    T.Pickups = Beat.Pickups.Num(); T.Dropoffs = Beat.Dropoffs.Num();
    if (T.Dropoffs > MaxPoints) return false; // Bound fixed capacity storage before indexing it.
    const auto CapacityValue = O.TryGetField(TEXT("dropoff_capacity"));
    if (!CapacityValue.IsValid()) return false;
    if (CapacityValue->Type != EJson::Null)
    {
        const auto Capacities = CapacityValue->Type == EJson::Object ? CapacityValue->AsObject() : nullptr;
        if (!Capacities || T.Task != ETask::Carry || T.Dropoffs < 1 || Capacities->Values.Num() != T.Dropoffs) return false;
        T.DropoffCapacityCount = T.Dropoffs;
        for (int32 Index = 0; Index < T.Dropoffs; ++Index)
        {
            const FString& Name = Beat.Dropoffs[Index];
            const auto Value = Capacities->TryGetField(Name);
            double Number = 0;
            if (Beat.Dropoffs.Find(Name) != Index || !Value.IsValid() || Value->Type != EJson::Number ||
                !Value->TryGetNumber(Number) || !Whole(Number, T.DropoffCapacities[Index])) return false;
            Beat.DropoffCapacities.Add(Name, T.DropoffCapacities[Index]);
        }
    }
    if (!DropoffCapacitiesValid(T)) return false;
    Beat.Opponent = Opponent.IsEmpty() ? NAME_None : FName(*Opponent);
    const FJsonRows* HoldRows = Rows(O, TEXT("objective_hold_ms"));
    if (!HoldRows || HoldRows->Num() != Beat.Objectives.Num()) return false;
    for (const auto& Row : *HoldRows)
    {
        double Number = 0; int32 Hold = 0;
        if (!Row.IsValid() || !Row->TryGetNumber(Number) || !Whole(Number, Hold) || Hold < 0) return false;
        Beat.ObjectiveHoldMs.Add(Hold);
    }
    const FJsonRows* GuardRows = Rows(O, TEXT("guards"));
    if (!GuardRows) return false;
    for (const auto& Row : *GuardRows)
    {
        const auto G = Row.IsValid() ? Row->AsObject() : nullptr;
        FSoraGuard Guard; FString Type;
        if (!G || !Str(*G, TEXT("type"), Type) || !Int(*G, TEXT("sight_cm"), Guard.SightCm) || Guard.SightCm < 0 ||
            !Int(*G, TEXT("dark_sight_cm"), Guard.DarkSightCm) || Guard.DarkSightCm < -1 ||
            !Int(*G, TEXT("view_deg"), Guard.ViewDegrees) || Guard.ViewDegrees < 0 || Guard.ViewDegrees > 360 ||
            !Int(*G, TEXT("hearing_cm"), Guard.HearingCm) || Guard.HearingCm < -1 ||
            !Int(*G, TEXT("suspicion_permille"), Guard.SuspicionPermille) || Guard.SuspicionPermille < 0 ||
            Guard.SuspicionPermille > 1000 || !G->TryGetBoolField(TEXT("post"), Guard.bPost) ||
            !Int(*G, TEXT("scan_deg"), Guard.ScanDegrees) || Guard.ScanDegrees < 0 || Guard.ScanDegrees > 360 ||
            !Int(*G, TEXT("scan_ms"), Guard.ScanMs) || (Guard.ScanDegrees > 0) != (Guard.ScanMs > 0) ||
            !Int(*G, TEXT("turn_ms"), Guard.TurnMs) || Guard.TurnMs < 0 || ((Guard.ScanDegrees > 0 || Guard.TurnMs > 0) && !Guard.bPost))
            return false;
        Guard.Type = FName(*Type);
        Beat.Guards.Add(Guard);
    }
    // A zone's (or guarded work's) authored rules; null elsewhere.
    const TSharedPtr<FJsonValue> StealthValue = O.TryGetField(TEXT("stealth"));
    if (!StealthValue.IsValid()) return false;
    Beat.bStealth = StealthValue->Type != EJson::Null;
    if (Beat.bStealth)
    {
        const auto S = StealthValue->Type == EJson::Object ? StealthValue->AsObject() : nullptr;
        FSoraStealthRulesData& Z = Beat.Stealth;
        if (!S || !Int(*S, TEXT("rate_permille"), Z.RatePermille) || Z.RatePermille < 100 || Z.RatePermille > 4000 ||
            !Int(*S, TEXT("suspicious_at_permille"), Z.SuspiciousAtPermille) || Z.SuspiciousAtPermille < 50 ||
            Z.SuspiciousAtPermille > 950 || !Int(*S, TEXT("search_ms"), Z.SearchMs) || Z.SearchMs < 1000 ||
            Z.SearchMs > 120000 || !Int(*S, TEXT("wary_permille"), Z.WaryPermille) || Z.WaryPermille < 1000 ||
            Z.WaryPermille > 4000 || !S->TryGetBoolField(TEXT("rear_takedowns"), Z.bRearTakedowns) ||
            !S->TryGetBoolField(TEXT("lethal_default"), Z.bLethalDefault) || !S->TryGetBoolField(TEXT("bodies"), Z.bBodies) ||
            !S->TryGetBoolField(TEXT("drag"), Z.bDrag) || !Nullable(*S, TEXT("carryover_to"), Z.CarryoverTo))
            return false;
    }
    // Every stealth zone and all work under guard carry their rules; nothing else does.
    if (Beat.bStealth != (T.Type == EType::StealthZone || T.PauseWhenSeen)) return false;

    const FJsonRows* WaveRows = Rows(O, TEXT("waves"));
    if (!WaveRows || WaveRows->Num() > MaxWaves) return false;
    T.WaveCount = WaveRows->Num();
    for (int32 Index = 0; Index < WaveRows->Num(); ++Index)
    {
        const auto W = (*WaveRows)[Index].IsValid() ? (*WaveRows)[Index]->AsObject() : nullptr;
        const FJsonRows* Groups = W ? Rows(*W, TEXT("members")) : nullptr;
        FSoraWave Wave; FWave& Rule = T.Waves[Index];
        if (!W || !Groups || !Nullable(*W, TEXT("id"), Wave.Id) || !Named(*W, TEXT("trigger"), Triggers, Rule.Trigger) ||
            !Int(*W, TEXT("value"), Rule.Value) || !Nullable(*W, TEXT("event"), Wave.Event) ||
            !Int(*W, TEXT("lethal"), Rule.Lethal) || !Int(*W, TEXT("nonlethal"), Rule.Nonlethal))
            return false;
        // Volume and event waves are released by their event; the others by the rules alone.
        const bool bByEvent = Rule.Trigger == EWaveTrigger::Volume || Rule.Trigger == EWaveTrigger::Event;
        if (bByEvent == Wave.Event.IsEmpty()) return false;
        int32 Lethal = 0, Nonlethal = 0;
        for (const auto& Row : *Groups)
        {
            const auto G = Row.IsValid() ? Row->AsObject() : nullptr;
            FSoraWaveGroup Group; FString Type;
            if (!G || !Str(*G, TEXT("type"), Type) || !Int(*G, TEXT("count"), Group.Count) || Group.Count < 1 ||
                !G->TryGetBoolField(TEXT("lethal"), Group.bLethal) || !G->TryGetBoolField(TEXT("invulnerable"), Group.bInvulnerable))
                return false;
            Group.Type = FName(*Type);
            (Group.bLethal ? Lethal : Nonlethal) += Group.Count;
            Wave.Groups.Add(Group);
        }
        if (Lethal != Rule.Lethal || Nonlethal != Rule.Nonlethal) return false;
        Beat.Waves.Add(MoveTemp(Wave));
    }
    const FJsonRows* PhaseRows = Rows(O, TEXT("phases"));
    if (!PhaseRows || PhaseRows->IsEmpty() || PhaseRows->Num() > MaxPhases) return false;
    T.PhaseCount = PhaseRows->Num();
    for (int32 Index = 0; Index < PhaseRows->Num(); ++Index)
    {
        double Number = 0;
        if (!(*PhaseRows)[Index].IsValid() || !(*PhaseRows)[Index]->TryGetNumber(Number) || !Whole(Number, T.PhaseStart[Index]))
            return false;
    }
    const FJsonRows* StepRows = Rows(O, TEXT("steps"));
    if (!StepRows || StepRows->Num() > MaxSteps) return false;
    T.StepCount = StepRows->Num();
    for (int32 Index = 0; Index < StepRows->Num(); ++Index)
    {
        const auto S = (*StepRows)[Index].IsValid() ? (*StepRows)[Index]->AsObject() : nullptr;
        FString StepKind; FStep& Step = T.Steps[Index];
        if (!S || !Str(*S, TEXT("kind"), StepKind) || !Int(*S, TEXT("count"), Step.Count) ||
            !Int(*S, TEXT("beat_ms"), Step.BeatMs) || !Int(*S, TEXT("tolerance_ms"), Step.ToleranceMs) ||
            !Int(*S, TEXT("phrase_strikes"), Step.PhraseStrikes) || !Int(*S, TEXT("phrase_pass"), Step.PhrasePass))
            return false;
        Beat.StepKinds.Add(StepKind);
    }
    const FJsonRows* TargetRows = Rows(O, TEXT("targets"));
    if (!TargetRows || TargetRows->Num() > MaxPoints) return false;
    T.TargetCount = TargetRows->Num();
    for (int32 Index = 0; Index < TargetRows->Num(); ++Index)
    {
        const auto R = (*TargetRows)[Index].IsValid() ? (*TargetRows)[Index]->AsObject() : nullptr;
        FString Target;
        if (!R || !Str(*R, TEXT("id"), Target) || !Int(*R, TEXT("hp"), T.TargetHp[Index])) return false;
        Beat.Targets.Add(Target);
    }
    TArray<FString> Checkpointed;
    if (!Strings(Rows(O, TEXT("fail_checkpoint")), Checkpointed)) return false;
    for (const FString& Name : Checkpointed)
    {
        const EFail* Failure = Failures.Find(Name);
        if (!Failure) return false;
        T.FailMask |= FailBit(*Failure);
    }
    const TSharedPtr<FJsonObject> FailEvents = Child(O, TEXT("fail_events"));
    if (!FailEvents) return false;
    for (const auto& Pair : FailEvents->Values)
    {
        FString Name;
        const EFail* Failure = Pair.Value.IsValid() && Pair.Value->TryGetString(Name) ? Failures.Find(Name) : nullptr;
        if (Pair.Key.IsEmpty() || !Failure) return false;
        Beat.FailEvents.Add(FString(Pair.Key.ToView()), *Failure);
    }
    return true;
}
}

int32 FSoraChapter::BeatIndex(const FString& BeatId) const
{
    return Beats.IndexOfByPredicate([&](const FSoraBeat& Beat) { return Beat.Id == BeatId; });
}
int32 FSoraChapter::LineIndex(const FString& LineId) const
{
    return Dialogue.IndexOfByPredicate([&](const FSoraDialogueCue& Line) { return Line.Id == LineId; });
}

FSoraCatalog& FSoraCatalog::Get() { static FSoraCatalog Catalog; return Catalog; }
bool FSoraCatalog::Fail(const FString& Message)
{
    Error = Message;
    UE_LOG(LogTemp, Error, TEXT("SORA catalog: %s"), *Error);
    return false;
}
bool FSoraCatalog::Load()
{
    if (bReady) return true;
    TSharedPtr<FJsonObject> Root;
    if (!ReadJson(TEXT("catalog.json"), Root)) return Fail(TEXT("Cannot load Content/Data/catalog.json"));
    int32 SchemaVersion = 0;
    if (!Int(*Root, TEXT("schema_version"), SchemaVersion) || SchemaVersion != 4 || Root->HasField(TEXT("chapters")))
        return Fail(TEXT("Unsupported offline catalog schema"));
    Weapons.Reset(); CampaignWeapons.Reset(); Classes.Reset(); Chapters.Reset(); Maps.Reset(); DialogueSpeakers.Reset();
    Mechanics.Reset(); MechanicLabels.Reset(); StoryFlags.Reset(); CollectibleCategories.Reset();
    StepLabels.Reset(); TargetLabels.Reset();
    const FJsonRows* Rows = nullptr;
    if (!Root->TryGetArrayField(TEXT("dialogue_speakers"), Rows)) return Fail(TEXT("Catalog lacks dialogue speakers"));
    for (const auto& Row : *Rows)
    {
        const auto O = Row->AsObject(); if (!O.IsValid()) return Fail(TEXT("Invalid dialogue speaker"));
        FString Id; FSoraDialogueSpeaker Speaker;
        if (!O->TryGetStringField(TEXT("id"), Id) || !O->TryGetStringField(TEXT("ja"), Speaker.Japanese) ||
            !O->TryGetStringField(TEXT("en"), Speaker.English) || Id.IsEmpty() || Speaker.Japanese.IsEmpty() ||
            Speaker.English.IsEmpty() || DialogueSpeakers.Contains(Id))
            return Fail(TEXT("Invalid dialogue speaker"));
        DialogueSpeakers.Add(Id, MoveTemp(Speaker));
    }
    if (DialogueSpeakers.IsEmpty()) return Fail(TEXT("Catalog lacks dialogue speakers"));
    const FSoraDialogueSpeaker* HeroSpeaker = DialogueSpeakers.Find(TEXT("samurai"));
    const TSharedPtr<FJsonObject>* HeroObject = nullptr;
    if (!HeroSpeaker || !Root->TryGetObjectField(TEXT("hero"), HeroObject) || !HeroObject || !HeroObject->IsValid() ||
        !(*HeroObject)->TryGetStringField(TEXT("name_ja"), HeroData.NameJapanese) ||
        !(*HeroObject)->TryGetStringField(TEXT("name_en"), HeroData.NameEnglish) ||
        !(*HeroObject)->TryGetNumberField(TEXT("katana_id"), HeroData.KatanaId) ||
        !(*HeroObject)->TryGetNumberField(TEXT("yumi_id"), HeroData.YumiId) ||
        !(*HeroObject)->TryGetNumberField(TEXT("quiver_arrows"), HeroData.QuiverArrows) ||
        HeroData.NameJapanese.IsEmpty() || HeroData.NameEnglish.IsEmpty() ||
        HeroData.KatanaId != 0 || HeroData.YumiId != 18 || HeroData.QuiverArrows != 12 ||
        HeroSpeaker->Japanese != HeroData.NameJapanese ||
        HeroSpeaker->English != HeroData.NameEnglish)
        return Fail(TEXT("Invalid Nyaakoto hero identity or initial arms"));
    if (!Root->TryGetArrayField(TEXT("weapons"), Rows)) return Fail(TEXT("Catalog lacks weapons"));
    for (const auto& Row : *Rows)
    {
        const auto O = Row->AsObject(); if (!O.IsValid()) return Fail(TEXT("Invalid weapon catalog"));
        FSoraWeapon W;
        W.Id = O->GetIntegerField(TEXT("id")); W.ClassId = O->GetIntegerField(TEXT("class"));
        W.Name = O->GetStringField(TEXT("name")); W.Kind = O->GetStringField(TEXT("kind")); W.Tradeoff = O->GetStringField(TEXT("tradeoff"));
        W.Damage = O->GetNumberField(TEXT("damage")); W.Cooldown = O->GetNumberField(TEXT("cooldown"));
        W.Range = O->GetNumberField(TEXT("range")); W.Reload = O->GetNumberField(TEXT("reload"));
        W.Magazine = O->GetIntegerField(TEXT("magazine")); W.BlastRadius = O->GetNumberField(TEXT("blast_radius"));
        W.ProjectileSpeed = O->GetNumberField(TEXT("projectile_speed")); W.Special = O->GetBoolField(TEXT("special"));
        if (W.Id != Weapons.Num() || W.ClassId < 0 || W.ClassId >= 6 || W.Cooldown <= 0 || W.Magazine < 1 || W.Damage <= 0) return Fail(TEXT("Invalid weapon catalog"));
        if (!O->TryGetStringField(TEXT("name_en"), W.NameEnglish) || W.NameEnglish.IsEmpty()) return Fail(TEXT("Weapon lacks its English name"));
        Weapons.Add(W);
    }
    // These three arms exist only in the offline campaign. Arena admission and
    // its compiled 18-weapon rules profile cannot select their IDs.
    if (!Root->TryGetArrayField(TEXT("campaign_weapons"), Rows) || Rows->Num() != 3)
        return Fail(TEXT("Catalog needs three campaign-only historical arms"));
    static const TCHAR* HistoricalKinds[] = { TEXT("bow"), TEXT("melee"), TEXT("melee") };
    for (const auto& Row : *Rows)
    {
        const auto O = Row->AsObject(); if (!O.IsValid()) return Fail(TEXT("Invalid campaign-only arm"));
        FSoraWeapon W;
        if (!O->TryGetStringField(TEXT("name"), W.Name) || !O->TryGetStringField(TEXT("name_en"), W.NameEnglish) ||
            !O->TryGetStringField(TEXT("kind"), W.Kind) || !O->TryGetStringField(TEXT("tradeoff"), W.Tradeoff))
            return Fail(TEXT("Invalid campaign-only arm"));
        W.Id = O->GetIntegerField(TEXT("id")); W.ClassId = O->GetIntegerField(TEXT("class"));
        W.Damage = O->GetNumberField(TEXT("damage")); W.Cooldown = O->GetNumberField(TEXT("cooldown"));
        W.Range = O->GetNumberField(TEXT("range")); W.Reload = O->GetNumberField(TEXT("reload"));
        W.Magazine = O->GetIntegerField(TEXT("magazine")); W.BlastRadius = O->GetNumberField(TEXT("blast_radius"));
        W.ProjectileSpeed = O->GetNumberField(TEXT("projectile_speed")); W.Special = O->GetBoolField(TEXT("special"));
        const int32 Index = CampaignWeapons.Num();
        if (W.Id != 18 + Index || W.ClassId != 0 || W.Kind != HistoricalKinds[Index] ||
            W.Name.IsEmpty() || W.NameEnglish.IsEmpty() || W.Tradeoff.IsEmpty() || W.Special ||
            W.Damage <= 0 || W.Cooldown <= 0 || W.Range <= 0 || W.Reload <= 0 || W.Magazine < 1 ||
            W.BlastRadius != 0 || (Index == 0 && W.ProjectileSpeed <= 0) ||
            (Index > 0 && W.ProjectileSpeed != 0))
            return Fail(TEXT("Invalid campaign-only arm"));
        CampaignWeapons.Add(MoveTemp(W));
    }
    if (!Root->TryGetArrayField(TEXT("classes"), Rows)) return Fail(TEXT("Catalog lacks classes"));
    for (const auto& Row : *Rows)
    {
        const auto O = Row->AsObject(); if (!O.IsValid()) return Fail(TEXT("Invalid class"));
        FSoraClass C; C.Id = O->GetIntegerField(TEXT("id")); C.Name = O->GetStringField(TEXT("name")); C.Role = O->GetStringField(TEXT("role"));
        C.Health = O->GetNumberField(TEXT("health")); C.Speed = O->GetNumberField(TEXT("speed"));
        if (!O->TryGetStringField(TEXT("name_en"), C.NameEnglish) || !O->TryGetStringField(TEXT("role_en"), C.RoleEnglish) ||
            C.NameEnglish.IsEmpty() || C.RoleEnglish.IsEmpty())
            return Fail(TEXT("Class lacks its English name or role"));
        for (const auto& V : O->GetArrayField(TEXT("weapons")))
        {
            const int32 Id = V->AsNumber();
            if (!Weapons.IsValidIndex(Id) || Weapons[Id].ClassId != C.Id) return Fail(TEXT("Invalid class weapon"));
            C.Weapons.Add(Id);
        }
        if (C.Id != Classes.Num() || C.Weapons.Num() != 3 || C.Health <= 0 || C.Speed <= 0) return Fail(TEXT("Invalid class"));
        Classes.Add(C);
    }
    if (!Root->TryGetArrayField(TEXT("maps"), Rows)) return Fail(TEXT("Catalog lacks maps"));
    for (const auto& Row : *Rows)
    {
        const auto O = Row->AsObject(); if (!O.IsValid()) return Fail(TEXT("Invalid map"));
        FSoraMap M; M.Name = O->GetStringField(TEXT("name")); const auto& A = O->GetArrayField(TEXT("accent"));
        if (A.Num() != 3) return Fail(TEXT("Map accent needs three channels"));
        if (!O->TryGetStringField(TEXT("name_en"), M.NameEnglish) || M.Name.IsEmpty() || M.NameEnglish.IsEmpty())
            return Fail(TEXT("Map lacks its English name"));
        M.Accent = FLinearColor(A[0]->AsNumber(), A[1]->AsNumber(), A[2]->AsNumber()); Maps.Add(M);
    }
    if (Weapons.Num() != 18 || CampaignWeapons.Num() != 3 || Classes.Num() != 6 || Maps.Num() != 4)
        return Fail(TEXT("Catalog must contain 6 classes, 18 weapons, 3 campaign arms and 4 maps"));
    if (!LoadCampaign()) return false;
    bReady = true;
    return true;
}

bool FSoraCatalog::LoadCampaign()
{
    TSharedPtr<FJsonObject> Campaign;
    int32 SchemaVersion = 0;
    if (!ReadJson(TEXT("campaign/campaign.json"), Campaign) || !Int(*Campaign, TEXT("schema_version"), SchemaVersion) || SchemaVersion != 4)
        return Fail(TEXT("Cannot load Content/Data/campaign/campaign.json (schema 4)"));
    // Bilingual labels by id: the mechanic flags in bit order, manufacturing
    // steps and defended targets.
    const auto Labels = [&](const TCHAR* Key, TArray<FString>* Ids, TArray<FSoraLabel>* Ordered, TMap<FString, FSoraLabel>* ById)
    {
        const FJsonRows* LabelRows = Rows(*Campaign, Key);
        if (!LabelRows || LabelRows->IsEmpty()) return false;
        for (const auto& Row : *LabelRows)
        {
            const auto O = Row.IsValid() ? Row->AsObject() : nullptr;
            FString Id; FSoraLabel Label;
            if (!O || !Str(*O, TEXT("id"), Id) || !Str(*O, TEXT("ja"), Label.Japanese) || !Str(*O, TEXT("en"), Label.English) ||
                (Ids && Ids->Contains(Id)) || (ById && ById->Contains(Id)))
                return false;
            if (Ids) Ids->Add(Id);
            if (Ordered) Ordered->Add(Label);
            if (ById) ById->Add(Id, MoveTemp(Label));
        }
        return true;
    };
    if (!Labels(TEXT("mechanics"), &Mechanics, &MechanicLabels, nullptr) || Mechanics.Num() != SoraBeatRules::MechanicCount)
        return Fail(TEXT("Campaign needs its nineteen labelled mechanic flags"));
    if (!Labels(TEXT("step_kinds"), nullptr, nullptr, &StepLabels) || !Labels(TEXT("targets"), nullptr, nullptr, &TargetLabels))
        return Fail(TEXT("Campaign needs bilingual labels for manufacturing steps and defended targets"));
    if (!Strings(Rows(*Campaign, TEXT("story_flags")), StoryFlags) || StoryFlags.Num() > SoraBeatRules::MaxStoryFlags)
        return Fail(TEXT("Campaign story flags must be a list of at most sixteen names"));
    for (int32 Index = 0; Index < StoryFlags.Num(); ++Index)
        if (StoryFlags.Find(StoryFlags[Index]) != Index) return Fail(TEXT("Duplicate campaign story flag"));
    const FJsonRows* CategoryRows = Rows(*Campaign, TEXT("collectible_categories"));
    if (!CategoryRows) return Fail(TEXT("Campaign lacks collectible categories"));
    for (const auto& Row : *CategoryRows)
    {
        const auto O = Row.IsValid() ? Row->AsObject() : nullptr;
        FSoraCollectibleCategory Category;
        if (!O || !Str(*O, TEXT("id"), Category.Id) || !Str(*O, TEXT("ja"), Category.Japanese) ||
            !Str(*O, TEXT("en"), Category.English) || !Int(*O, TEXT("count"), Category.Count) || Category.Count < 1)
            return Fail(TEXT("Invalid collectible category"));
        CollectibleCategories.Add(MoveTemp(Category));
    }
    const FJsonRows* ChapterRows = Rows(*Campaign, TEXT("chapters"));
    if (!ChapterRows || ChapterRows->Num() != ChapterCount) return Fail(TEXT("Campaign needs eight chapters"));
    static const TSet<FString> SiteKinds = {
        TEXT("training"), TEXT("debt_seal"), TEXT("irrigation"), TEXT("workshop"),
        TEXT("foundry"), TEXT("ledger"), TEXT("power"), TEXT("supplies")};
    // Collectibles found so far across the campaign, for conditional lines.
    TMap<FString, unsigned long long> FoundBits;
    for (int32 ChapterIndex = 0; ChapterIndex < ChapterCount; ++ChapterIndex)
    {
        const auto Entry = (*ChapterRows)[ChapterIndex].IsValid() ? (*ChapterRows)[ChapterIndex]->AsObject() : nullptr;
        FSoraChapter C; FString File;
        if (!Entry || !Str(*Entry, TEXT("id"), C.Id) || !Str(*Entry, TEXT("file"), File) ||
            !Str(*Entry, TEXT("narrative_ja"), C.Narrative) || !Str(*Entry, TEXT("narrative_en"), C.NarrativeEnglish) ||
            !Str(*Entry, TEXT("objective_ja"), C.Objective) || !Str(*Entry, TEXT("objective_en"), C.ObjectiveEnglish))
            return Fail(FString::Printf(TEXT("Chapter %d lacks its bilingual narrative or objective"), ChapterIndex + 1));
        const FJsonRows* SiteLabels = Rows(*Entry, TEXT("sites"));
        if (!SiteLabels || SiteLabels->Num() != SoraBeatRules::SiteCount)
            return Fail(FString::Printf(TEXT("%s needs three production sites"), *C.Id));
        for (const auto& Label : *SiteLabels)
        {
            const auto O = Label.IsValid() ? Label->AsObject() : nullptr;
            FSoraProductionSite Site;
            if (!O || !Str(*O, TEXT("kind"), Site.Kind) || !Str(*O, TEXT("name_ja"), Site.Name) ||
                !Str(*O, TEXT("name_en"), Site.NameEnglish) || !Str(*O, TEXT("restored_ja"), Site.Restored) ||
                !Str(*O, TEXT("restored_en"), Site.RestoredEnglish) || !SiteKinds.Contains(Site.Kind))
                return Fail(FString::Printf(TEXT("%s has an invalid production site label"), *C.Id));
            C.Sites.Add(MoveTemp(Site));
        }
        TSharedPtr<FJsonObject> Data;
        int32 FileSchema = 0, FileIndex = -1;
        FString FileId;
        if (!ReadJson(File, Data) || !Int(*Data, TEXT("schema_version"), FileSchema) || FileSchema != 4 ||
            !Str(*Data, TEXT("id"), FileId) || FileId != C.Id || !Int(*Data, TEXT("index"), FileIndex) || FileIndex != ChapterIndex ||
            !Str(*Data, TEXT("title_ja"), C.Title) || !Str(*Data, TEXT("title_en"), C.TitleEnglish) ||
            !Int(*Data, TEXT("map"), C.Map) || !Maps.IsValidIndex(C.Map) || !Int(*Data, TEXT("target_s"), C.TargetSeconds))
            return Fail(FString::Printf(TEXT("Cannot load %s for %s"), *File, *C.Id));
        const FString Where = C.Id;
        auto Bad = [&](const FString& What) { return Fail(FString::Printf(TEXT("%s: %s"), *Where, *What)); };

        // Beat ids first: lines, collectibles and prompts refer to beats by id.
        const FJsonRows* BeatRows = Rows(*Data, TEXT("beats"));
        if (!BeatRows || BeatRows->IsEmpty() || BeatRows->Num() > SoraBeatRules::MaxBeats) return Bad(TEXT("needs 1-32 beats"));
        TMap<FString, int32> BeatIds;
        for (const auto& Row : *BeatRows)
        {
            const auto O = Row.IsValid() ? Row->AsObject() : nullptr;
            FString Id;
            if (!O || !Str(*O, TEXT("id"), Id) || BeatIds.Contains(Id)) return Bad(TEXT("invalid or duplicate beat id"));
            BeatIds.Add(Id, BeatIds.Num());
        }
        const auto BeatRef = [&](const FJsonObject& O, int32& Out)
        {
            FString Id;
            if (IsNull(O, TEXT("beat"))) { Out = INDEX_NONE; return true; }
            if (!Str(O, TEXT("beat"), Id) || !BeatIds.Contains(Id)) return false;
            Out = BeatIds[Id];
            return true;
        };
        const FJsonRows* LineRows = Rows(*Data, TEXT("lines"));
        if (!LineRows || LineRows->IsEmpty()) return Bad(TEXT("has no lines"));
        TMap<FString, int32> LineIds;
        for (const auto& Row : *LineRows)
        {
            const auto O = Row.IsValid() ? Row->AsObject() : nullptr;
            FSoraDialogueCue Line; double Duration = 0;
            if (!O || !Str(*O, TEXT("id"), Line.Id) || LineIds.Contains(Line.Id) || !BeatRef(*O, Line.Beat) ||
                !Str(*O, TEXT("speaker"), Line.SpeakerId) || !DialogueSpeakers.Contains(Line.SpeakerId) ||
                !Str(*O, TEXT("ja"), Line.Japanese) || !Str(*O, TEXT("en"), Line.English) ||
                !Num(*O, TEXT("duration_s"), Duration) || Duration < 1.0 || Duration > 20.0 ||
                !O->TryGetBoolField(TEXT("repeatable"), Line.bRepeatable))
                return Bad(FString::Printf(TEXT("invalid line %s"), *Line.Id));
            Line.DurationSeconds = static_cast<float>(Duration);
            if (!IsNull(*O, TEXT("mode")) &&
                (!Str(*O, TEXT("mode"), Line.Mode) ||
                 (Line.Mode != TEXT("blocking") && Line.Mode != TEXT("ambient") &&
                  Line.Mode != TEXT("radio") && Line.Mode != TEXT("bark") && Line.Mode != TEXT("cinematic"))))
                return Bad(FString::Printf(TEXT("invalid dialogue mode for %s"), *Line.Id));
            LineIds.Add(Line.Id, C.Dialogue.Num());
            C.Dialogue.Add(MoveTemp(Line));
        }
        const auto LineRefs = [&](const FJsonRows* Values, TArray<int32>& Out)
        {
            TArray<FString> Ids;
            if (!Strings(Values, Ids) || Ids.IsEmpty()) return false;
            for (const FString& Id : Ids)
            {
                if (!LineIds.Contains(Id)) return false;
                Out.Add(LineIds[Id]);
            }
            return true;
        };
        const FJsonRows* CollectibleRows = Rows(*Data, TEXT("collectibles"));
        if (!CollectibleRows || CollectibleRows->Num() != CollectiblesPerChapter) return Bad(TEXT("needs six collectibles"));
        unsigned CollectibleBits = 0u;
        for (const auto& Row : *CollectibleRows)
        {
            const auto O = Row.IsValid() ? Row->AsObject() : nullptr;
            const TSharedPtr<FJsonObject> Codex = O ? Child(*O, TEXT("codex")) : nullptr;
            FSoraCollectible Item; TArray<FString> Beats;
            if (!O || !Codex || !Str(*O, TEXT("id"), Item.Id) || !Str(*O, TEXT("category"), Item.Category) ||
                !CollectibleCategories.ContainsByPredicate([&](const FSoraCollectibleCategory& Category) { return Category.Id == Item.Category; }) ||
                !Int(*O, TEXT("mask_bit"), Item.MaskBit) || Item.MaskBit < 0 || Item.MaskBit >= CollectiblesPerChapter ||
                (CollectibleBits & (1u << Item.MaskBit)) != 0u || !Strings(Rows(*O, TEXT("beats")), Beats) ||
                !Str(*O, TEXT("place"), Item.Place) || !Str(*Codex, TEXT("ja"), Item.Codex) || !Str(*Codex, TEXT("en"), Item.CodexEnglish))
                return Bad(FString::Printf(TEXT("invalid collectible %s"), *Item.Id));
            for (const FString& Beat : Beats)
            {
                if (!BeatIds.Contains(Beat)) return Bad(FString::Printf(TEXT("collectible %s names an unknown beat"), *Item.Id));
                Item.Beats.Add(BeatIds[Beat]);
            }
            CollectibleBits |= 1u << Item.MaskBit;
            FoundBits.Add(Item.Id, SoraCampaignRules::CollectibleBit(ChapterIndex, Item.MaskBit));
            C.Collectibles.Add(MoveTemp(Item));
        }

        // Phase checkpoints per beat; phase 0 rows must match the beats' own flag.
        TArray<int32> PhaseCheckpoints; PhaseCheckpoints.Init(0, BeatIds.Num());
        TArray<bool> StartCheckpoints; StartCheckpoints.Init(false, BeatIds.Num());
        const FJsonRows* CheckpointRows = Rows(*Data, TEXT("checkpoints"));
        if (!CheckpointRows) return Bad(TEXT("lacks checkpoints"));
        for (const auto& Row : *CheckpointRows)
        {
            const auto O = Row.IsValid() ? Row->AsObject() : nullptr;
            int32 Beat = INDEX_NONE, Phase = -1;
            if (!O || !BeatRef(*O, Beat) || Beat == INDEX_NONE || !Int(*O, TEXT("phase"), Phase) || Phase < 0)
                return Bad(TEXT("invalid checkpoint row"));
            if (Phase == 0)
            {
                if (StartCheckpoints[Beat]) return Bad(TEXT("duplicate checkpoint"));
                StartCheckpoints[Beat] = true;
            }
            else if (Phase != PhaseCheckpoints[Beat] + 1) return Bad(TEXT("phase checkpoints out of order"));
            else PhaseCheckpoints[Beat] = Phase;
        }

        for (int32 BeatIndex = 0; BeatIndex < BeatRows->Num(); ++BeatIndex)
        {
            const auto O = (*BeatRows)[BeatIndex]->AsObject();
            FSoraBeat Beat; FString TypeName;
            SoraBeatRules::FBeat Rule{0u, -1, 0u, 0u, 0u, 0u, false, false, 0};
            const TSharedPtr<FJsonObject> Unlocks = Child(*O, TEXT("unlocks"));
            const TSharedPtr<FJsonObject> Params = Child(*O, TEXT("params"));
            const TSharedPtr<FJsonObject> Task = Child(*O, TEXT("task"));
            TArray<FString> Requires, MechanicNames, FlagNames;
            if (!Str(*O, TEXT("id"), Beat.Id) || !Str(*O, TEXT("type"), TypeName) || !Str(*O, TEXT("place"), Beat.Place) ||
                !Str(*O, TEXT("title_ja"), Beat.Title) || !Str(*O, TEXT("title_en"), Beat.TitleEnglish) ||
                !Int(*O, TEXT("target_s"), Beat.TargetSeconds) || Beat.TargetSeconds <= 0 ||
                !O->TryGetBoolField(TEXT("checkpoint"), Rule.Checkpoint) || !O->TryGetBoolField(TEXT("optional"), Rule.Optional) ||
                !Strings(Rows(*O, TEXT("requires")), Requires) || !Unlocks || !Params || !Task ||
                !WeaponMask(Rows(*Unlocks, TEXT("weapons")), Rule.WeaponsMask) ||
                !WeaponMask(Rows(*Unlocks, TEXT("grants")), Rule.GrantsMask) ||
                !Strings(Rows(*Unlocks, TEXT("mechanics")), MechanicNames) ||
                !Strings(Rows(*Unlocks, TEXT("story_flags")), FlagNames))
                return Bad(FString::Printf(TEXT("beat %s lacks a required field"), *Beat.Id));
            for (const FString& Prior : Requires)
            {
                if (!BeatIds.Contains(Prior) || BeatIds[Prior] >= BeatIndex) return Bad(FString::Printf(TEXT("beat %s requires a later beat"), *Beat.Id));
                Rule.RequiresMask |= SoraBeatRules::BeatBit(BeatIds[Prior]);
            }
            for (const FString& Name : MechanicNames)
            {
                const int32 Bit = Mechanics.Find(Name);
                if (Bit == INDEX_NONE) return Bad(FString::Printf(TEXT("beat %s unlocks unknown mechanic %s"), *Beat.Id, *Name));
                Rule.MechanicsMask |= 1u << Bit;
            }
            for (const FString& Name : FlagNames)
            {
                const int32 Bit = StoryFlags.Find(Name);
                if (Bit == INDEX_NONE) return Bad(FString::Printf(TEXT("beat %s sets unknown story flag %s"), *Beat.Id, *Name));
                Rule.FlagsMask |= 1u << Bit;
            }
            if (!IsNull(*O, TEXT("site")) && (!Int(*O, TEXT("site"), Rule.Site) || Rule.Site < 0 || Rule.Site >= SoraBeatRules::SiteCount))
                return Bad(FString::Printf(TEXT("beat %s has an invalid site"), *Beat.Id));
            if (StartCheckpoints[BeatIndex] != Rule.Checkpoint) return Bad(FString::Printf(TEXT("beat %s disagrees with its checkpoint rows"), *Beat.Id));
            Rule.PhaseCheckpoints = PhaseCheckpoints[BeatIndex];
            if (!ReadTask(*Task, TypeName, Beat) || !SoraBeatRules::TaskValid(Beat.Task))
                return Bad(FString::Printf(TEXT("beat %s has an invalid %s task"), *Beat.Id, *TypeName));
            if (!SoraCatalogRegistry::Read(*O, Beat))
                return Bad(FString::Printf(TEXT("beat %s has an invalid production registry entry"), *Beat.Id));
            for (const FString& Kind : Beat.StepKinds)
                if (!StepLabels.Contains(Kind)) return Bad(FString::Printf(TEXT("beat %s has an unlabelled step %s"), *Beat.Id, *Kind));
            for (const FString& Target : Beat.Targets)
                if (!TargetLabels.Contains(Target)) return Bad(FString::Printf(TEXT("beat %s has an unlabelled target %s"), *Beat.Id, *Target));
            // A dialogue beat's lines, and an explore beat's rewards, stay in its parameters.
            if (Beat.Is(SoraBeatRules::EType::Dialogue) &&
                (!LineRefs(Rows(*Params, TEXT("lines")), Beat.Lines) || Beat.Lines.Num() != Beat.Task.Count || Beat.LinesEvent.IsEmpty()))
                return Bad(FString::Printf(TEXT("beat %s has invalid dialogue lines"), *Beat.Id));
            // Blocking lines are some of the dialogue's own lines.
            if (const TSharedPtr<FJsonObject> Ext = Child(*O, TEXT("ext")); Ext && Ext->HasField(TEXT("supply_point")))
            {
                // Chapter three names an object with slots/refill metadata;
                // later chapters use a bare station id. Preserve both forms.
                const TSharedPtr<FJsonObject> Supply = Child(*Ext, TEXT("supply_point"));
                const bool Named = Supply ? Supply->TryGetStringField(TEXT("id"), Beat.SupplyPoint)
                    : Ext->TryGetStringField(TEXT("supply_point"), Beat.SupplyPoint);
                if (!Named || Beat.SupplyPoint.IsEmpty())
                    return Bad(FString::Printf(TEXT("beat %s has an invalid supply point"), *Beat.Id));
            }
            if (const TSharedPtr<FJsonObject> Ext = Child(*O, TEXT("ext")); Ext && Ext->HasField(TEXT("blocking_lines")) &&
                (!LineRefs(Rows(*Ext, TEXT("blocking_lines")), Beat.BlockingLines) ||
                 Beat.BlockingLines.ContainsByPredicate([&](int32 Line) { return !Beat.Lines.Contains(Line); })))
                return Bad(FString::Printf(TEXT("beat %s has invalid blocking lines"), *Beat.Id));
            if (Beat.Is(SoraBeatRules::EType::ExploreOptional))
            {
                if (Params->HasField(TEXT("pois")))
                {
                    const auto* Pois=Rows(*Params,TEXT("pois"));
                    if(!Pois) return Bad(FString::Printf(TEXT("beat %s has invalid points of interest"),*Beat.Id));
                    for(const auto& Value:*Pois)
                    {
                        const auto Poi=Value->AsObject();
                        FSoraExplorePoi Point;
                        if(!Poi||!Str(*Poi,TEXT("id"),Point.Id)||Point.Id.IsEmpty()||
                            !Str(*Poi,TEXT("kind"),Point.Kind)||Point.Kind.IsEmpty()||
                            Beat.Pois.ContainsByPredicate([&](const FSoraExplorePoi& P) { return P.Id==Point.Id; }))
                            return Bad(FString::Printf(TEXT("beat %s has an invalid or repeated point of interest"),*Beat.Id));
                        if(Poi->HasField(TEXT("interact"))&&!Str(*Poi,TEXT("interact"),Point.Interaction))
                            return Bad(FString::Printf(TEXT("point %s has an invalid interaction"),*Point.Id));
                        if(Poi->HasField(TEXT("collectible")))
                        {
                            FString Id;
                            if(!Str(*Poi,TEXT("collectible"),Id)) return Bad(TEXT("invalid point collectible"));
                            Point.Collectible=C.Collectibles.IndexOfByPredicate([&](const FSoraCollectible& Item) { return Item.Id==Id; });
                            if(Point.Collectible==INDEX_NONE) return Bad(FString::Printf(TEXT("point %s names an unknown collectible"),*Point.Id));
                        }
                        Beat.Pois.Add(MoveTemp(Point));
                    }
                }
                TArray<FString> Rewards;
                if (!Strings(Rows(*Params, TEXT("rewards")), Rewards)) return Bad(FString::Printf(TEXT("beat %s has invalid rewards"), *Beat.Id));
                // Arrows and other pickups refill at the cache; collectibles enter the codex.
                for (const FString& Reward : Rewards)
                {
                    const int32 Item = C.Collectibles.IndexOfByPredicate([&](const FSoraCollectible& Candidate) { return Candidate.Id == Reward; });
                    if (Item != INDEX_NONE) Beat.Rewards.Add(Item);
                }
            }
            C.Rules.Add(Rule);
            C.Tasks.Add(Beat.Task);
            C.Beats.Add(MoveTemp(Beat));
        }
        if (!SoraBeatRules::ChapterValid(C.Rules.GetData(), C.Rules.Num())) return Bad(TEXT("beats violate the chapter gates"));
        // Every task valid, the chapter opens on a cinematic (its title card),
        // only explore beats are optional and only bosses and duels save per phase.
        if (!SoraBeatRules::TasksValid(C.Rules.GetData(), C.Tasks.GetData(), C.Rules.Num())) return Bad(TEXT("beat tasks violate SoraBeatRules"));
        // A collectible lies in an explore beat's cache or loose in the world
        // at its pickup (read with the space); the script's beats only hint
        // at when it is found.
        for (int32 Item = 0; Item < C.Collectibles.Num(); ++Item)
        {
            FSoraCollectible& Collectible = C.Collectibles[Item];
            Collectible.Beats.Reset();
            for (int32 Beat = 0; Beat < C.Beats.Num(); ++Beat)
                if (C.Beats[Beat].Rewards.Contains(Item)) Collectible.Beats.Add(Beat);
        }
        const TSharedPtr<FJsonObject> Space = Child(*Data, TEXT("space"));
        if (!Space || !LoadSpace(*Space, C)) return false;
        for (const FSoraCollectible& Collectible : C.Collectibles)
            if (Collectible.Beats.IsEmpty() == (Collectible.Pickup == INDEX_NONE))
                return Bad(FString::Printf(TEXT("collectible %s must lie in one cache or at one pickup"), *Collectible.Id));

        const FJsonRows* SiteRows = Rows(*Data, TEXT("sites"));
        if (!SiteRows || SiteRows->Num() != SoraBeatRules::SiteCount) return Bad(TEXT("needs three site rows"));
        for (const auto& Row : *SiteRows)
        {
            const auto O = Row.IsValid() ? Row->AsObject() : nullptr;
            int32 Index = -1, Beat = INDEX_NONE;
            const FJsonRows* Prerequisites = O ? Rows(*O, TEXT("requires_sites")) : nullptr;
            if (!O || !Int(*O, TEXT("index"), Index) || !C.Sites.IsValidIndex(Index) || C.Sites[Index].Beat != INDEX_NONE ||
                !BeatRef(*O, Beat) || Beat == INDEX_NONE || C.Rules[Beat].Site != Index || !Prerequisites)
                return Bad(TEXT("site row disagrees with its beat"));
            for (const auto& Prerequisite : *Prerequisites)
            {
                double Number = 0; int32 Prior = -1;
                if (!Prerequisite.IsValid() || !Prerequisite->TryGetNumber(Number) || !Whole(Number, Prior) ||
                    Prior < 0 || Prior >= SoraBeatRules::SiteCount || Prior == Index)
                    return Bad(TEXT("invalid site prerequisite"));
                C.Sites[Index].RequiredSitesMask |= 1 << Prior;
            }
            C.Sites[Index].Beat = Beat;
        }

        const FJsonRows* TriggerRows = Rows(*Data, TEXT("triggers"));
        if (!TriggerRows) return Bad(TEXT("lacks its trigger table"));
        for (const auto& Row : *TriggerRows)
        {
            const auto O = Row.IsValid() ? Row->AsObject() : nullptr;
            FSoraDialogueTrigger Trigger; FString Condition; double Cooldown = 0;
            if (!O || !BeatRef(*O, Trigger.Beat) || !Str(*O, TEXT("on"), Trigger.On) || !LineRefs(Rows(*O, TEXT("lines")), Trigger.Lines) ||
                !Str(*O, TEXT("mode"), Trigger.Mode) || !O->TryGetBoolField(TEXT("repeatable"), Trigger.bRepeatable) ||
                (!IsNull(*O, TEXT("cooldown_s")) && (!Num(*O, TEXT("cooldown_s"), Cooldown) || Cooldown < 0)) ||
                !Nullable(*O, TEXT("requires_flag"), Condition) ||
                (!IsNull(*O, TEXT("at_ms")) && (!Int(*O, TEXT("at_ms"), Trigger.AtMs) || Trigger.AtMs < 0)))
                return Bad(TEXT("invalid trigger row"));
            Trigger.CooldownSeconds = static_cast<float>(Cooldown);
            // A conditional line waits for a collectible found here or earlier, or a story flag.
            if (Condition.StartsWith(TEXT("collectible:")))
            {
                const unsigned long long* Bit = FoundBits.Find(Condition.RightChop(12));
                if (!Bit) return Bad(FString::Printf(TEXT("trigger requires unknown %s"), *Condition));
                Trigger.RequiresCollectible = *Bit;
            }
            else if (Condition.StartsWith(TEXT("story:")))
            {
                const int32 Bit = StoryFlags.Find(Condition.RightChop(6));
                if (Bit == INDEX_NONE) return Bad(FString::Printf(TEXT("trigger requires unknown %s"), *Condition));
                Trigger.RequiresFlags = 1u << Bit;
            }
            else if (!Condition.IsEmpty()) return Bad(FString::Printf(TEXT("trigger requires %s"), *Condition));
            // A cinematic subtitle is placed on the cinematic's own clock.
            if (Trigger.On == TEXT("subtitle") &&
                (Trigger.AtMs < 0 || Trigger.Beat == INDEX_NONE || !C.Beats[Trigger.Beat].Is(SoraBeatRules::EType::Cinematic)))
                return Bad(TEXT("subtitle outside a cinematic"));
            C.Triggers.Add(MoveTemp(Trigger));
        }
        const FJsonRows* PromptRows = Rows(*Data, TEXT("ui_prompts"));
        if (!PromptRows) return Bad(TEXT("lacks its HUD prompts"));
        for (const auto& Row : *PromptRows)
        {
            const auto O = Row.IsValid() ? Row->AsObject() : nullptr;
            FSoraPrompt Prompt; TArray<FString> Beats;
            if (!O || !Str(*O, TEXT("ja"), Prompt.Japanese) || !Str(*O, TEXT("en"), Prompt.English) ||
                !Strings(Rows(*O, TEXT("beats")), Beats) || (!IsNull(*O, TEXT("on")) && !Str(*O, TEXT("on"), Prompt.On)))
                return Bad(TEXT("invalid HUD prompt"));
            for (const FString& Beat : Beats)
            {
                if (!BeatIds.Contains(Beat)) return Bad(TEXT("HUD prompt names an unknown beat"));
                Prompt.Beats.Add(BeatIds[Beat]);
            }
            C.Prompts.Add(MoveTemp(Prompt));
        }
        Chapters.Add(MoveTemp(C));
    }
    // Every route through the campaign ends holding all 21 weapons and every mechanic.
    if (RouteMinimumWeapons(ChapterCount) != SoraBeatRules::AllWeaponsMask ||
        EarlierWeapons(ChapterCount) != SoraBeatRules::AllWeaponsMask ||
        EarlierMechanics(ChapterCount) != SoraBeatRules::AllMechanicsMask)
        return Fail(TEXT("The campaign does not unlock every weapon and mechanic on every route"));
    return true;
}

unsigned FSoraCatalog::RouteMinimumWeapons(int32 Chapter) const
{
    unsigned Mask = 0u;
    for (int32 Index = 0; Index < Chapter && Chapters.IsValidIndex(Index); ++Index)
        Mask |= SoraBeatRules::ChapterWeapons(Chapters[Index].Rules.GetData(), Chapters[Index].Rules.Num(), false);
    return Mask;
}
unsigned FSoraCatalog::EarlierWeapons(int32 Chapter) const
{
    unsigned Mask = 0u;
    for (int32 Index = 0; Index < Chapter && Chapters.IsValidIndex(Index); ++Index)
        Mask |= SoraBeatRules::ChapterWeapons(Chapters[Index].Rules.GetData(), Chapters[Index].Rules.Num(), true);
    return Mask;
}
unsigned FSoraCatalog::EarlierFlags(int32 Chapter) const
{
    unsigned Mask = 0u;
    for (int32 Index = 0; Index < Chapter && Chapters.IsValidIndex(Index); ++Index)
        Mask |= SoraBeatRules::ChapterFlags(Chapters[Index].Rules.GetData(), Chapters[Index].Rules.Num());
    return Mask;
}
unsigned FSoraCatalog::EarlierMechanics(int32 Chapter) const
{
    unsigned Mask = 0u;
    for (int32 Index = 0; Index < Chapter && Chapters.IsValidIndex(Index); ++Index)
        Mask |= SoraBeatRules::ChapterMechanics(Chapters[Index].Rules.GetData(), Chapters[Index].Rules.Num());
    return Mask;
}
const FSoraWeapon& FSoraCatalog::Weapon(int32 Id) const
{
    check(bReady);
    if (Id >= 18 && Id < 18 + CampaignWeapons.Num()) return CampaignWeapons[Id - 18];
    check(Weapons.IsValidIndex(Id));
    return Weapons[Id];
}
const FSoraClass& FSoraCatalog::Class(int32 Id) const { check(bReady); return Classes[FMath::Clamp(Id,0,Classes.Num()-1)]; }
const FSoraChapter& FSoraCatalog::Chapter(int32 Id) const { check(bReady); return Chapters[FMath::Clamp(Id,0,Chapters.Num()-1)]; }
const FSoraDialogueSpeaker* FSoraCatalog::DialogueSpeaker(const FString& Id) const { return DialogueSpeakers.Find(Id); }
const FSoraMap& FSoraCatalog::Map(int32 Id) const { check(bReady); return Maps[FMath::Clamp(Id,0,Maps.Num()-1)]; }
