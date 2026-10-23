#include "SoraCampaignDirector.h"
#include "Game/SoraCampaignReach.h"
#include "SoraCompanion.h"
#include "SoraEnemy.h"
#include "SoraFieldcraft.h"
#include "SoraWorldBuilder.h"
#include "SoraCampaignLift.h"
#include "SoraGameMode.h"
#include "EngineUtils.h"
#include "SoraPlayerCharacter.h"
#include "SoraEquipmentComponent.h"
#include "SoraSettings.h"
#include "SoraViewmodelComponent.h"

int32 USoraCampaignDirector::CrankHelpers()
{
    ActiveCrankHelpers=0;
    bCrankHelperRetreating=false;
    const FSoraBeat* Beat=ActiveBeatData();
    USoraFieldcraft* Craft=USoraFieldcraft::Get(this);
    if(!Beat||!Craft||Beat->CrankNpcs.IsEmpty()||Task.Goal!=SoraBeatRules::EGoal::Turns) return 0;
    for(const FString& Npc:Beat->CrankNpcs)
    {
        const FSoraDefendedPerson* Spec=Beat->Space.Fieldcraft.People.FindByPredicate(
            [&](const FSoraDefendedPerson& Person) { return Person.Id==Npc; });
        if(!Spec) continue;
        ASoraCompanion* Helper=nullptr;
        for(const auto& Person:Craft->PeopleInPlay())
            if(IsValid(Person)&&Person->CompanionId()==Npc) { Helper=Person; break; }
        if(!Helper||Helper->Condition()!=SoraFieldcraftRules::EState::Up||!Helper->IsJoined()) continue;
        const auto* Lift=Mode().Arena()?Mode().Arena()->CampaignLift():nullptr;
        if(Lift&&!Lift->Aboard(*Helper)) continue;
        const FVector Work=ASoraWorldBuilder::Floor(Spec->At,Helper->GetActorLocation().Z);
        bool bRetreat=false;
        if(Task.CoopRetreatCm>0)
            for(TActorIterator<ASoraEnemy> It(GetWorld());It;++It)
                if(It->IsEnemy()&&It->IsAlive()&&
                    (FVector::Dist2D(It->GetActorLocation(),Helper->GetActorLocation())<=Task.CoopRetreatCm||
                     FVector::Dist2D(It->GetActorLocation(),Work)<=Task.CoopRetreatCm))
                { bRetreat=true; break; }
        bCrankHelperRetreating|=bRetreat;
        // Do not send her back into the same threat at the wheel. This also
        // prevents oscillation as the cover itself puts her beyond five metres.
        const FVector Goal=bRetreat?ASoraWorldBuilder::Floor(Spec->Cover,Work.Z):Work;
        Helper->SetGoal(Goal,(ASoraWorldBuilder::Floor(Beat->Space.Anchor)-Work).Rotation().Yaw,180.f);
        if(!bRetreat&&FVector::Dist2D(Helper->GetActorLocation(),Work)<=40.f&&
            TaskState.LastActionMs>=0&&!AtWorkAnchor(SoraCampaignReach::Interact))
            ++ActiveCrankHelpers;
    }
    return ActiveCrankHelpers;
}

bool USoraCampaignDirector::PlayerCrankEligible() const
{
    const auto& M=Mode();
    const auto* Hero=M.Hero();
    return ActiveBeatData()&&M.bCampaign&&M.IsPlaying()&&!bDialogueHeld&&Hero&&
        Task.Goal==SoraBeatRules::EGoal::Turns&&!SoraBeatRules::GoalMet(TaskState,Task)&&
        !Hero->GetEquipment()->IsStaggered()&&!Hero->GetEquipment()->bReloading&&AtWorkAnchor(SoraCampaignReach::Interact);
}
bool USoraCampaignDirector::IsWorkingCrank() const
{
    return CrankInput.Active&&PlayerCrankEligible()&&Mode().Hero()->IsActionHeld(TEXT("Interact"));
}
void USoraCampaignDirector::StopPlayerCrank(bool bWaitForRelease)
{
    StopPlayerRhythm(bWaitForRelease);
    CrankInput={};
    BellowsTreads={};
    if(bWaitForRelease) SoraCrankInputRules::Stop(CrankInput);
    if(auto* Hero=Mode().Hero()) Hero->GetViewmodel()->SetHiddenInGame(HelmOccupiesHands(),true);
}
bool USoraCampaignDirector::TurnPlayerCrank(bool bBegin)
{
    using SoraBeatRules::ETurn;
    if(!PlayerCrankEligible()) { StopPlayerCrank(); return false; }
    if(bBegin&&!SoraCrankInputRules::Begin(CrankInput,true)) return false;
    if(bBegin&&Task.AlternateTreads)
    {
        BellowsCueStarted=TaskState.ElapsedMs; RhythmCueShown=-1;
        SoraCrankInputRules::BeginTreads(BellowsTreads,FMath::RoundToInt(Mode().Hero()->GetInputAxisValue(TEXT("MoveRight"))*1000.f));
        return false; // Interact engages the station; only a completed L+R pair turns it.
    }
    auto* Kit=Mode().Hero()->GetEquipment();
    const int32 DoneBefore=TaskState.Done;
    const int32 Credit=Task.AlternateTreads&&Mode().Settings()&&Mode().Settings()->RhythmAssist()?700:1000;
    const auto Turned=SoraBeatRules::PlayerTurn(TaskState,Task,FMath::FloorToInt32(Kit->GuardReserve()),Credit);
    if(Turned.Result==ETurn::Exhausted)
    {
        StopPlayerCrank();
        Notify(TEXT("体力が足りない。手を離して息を整えよう。"),TEXT("Not enough stamina. Release the crank and recover."),3.f);
        return false;
    }
    if(Turned.Result==ETurn::Refused) { StopPlayerCrank(); return false; }
    Kit->SpendGuard(Turned.Cost);
    if(Task.CrankTwoHanded)
    {
        Kit->Halt(); Kit->DropStance();
        Mode().Hero()->GetViewmodel()->SetHiddenInGame(CrankOccupiesHands()||HelmOccupiesHands(),true);
    }
    const bool bWorked=Turned.Result==ETurn::InBand||Turned.Result==ETurn::Slow;
    Fire(Turned.Result==ETurn::TooFast?TEXT("rate_band:above"):Turned.Result==ETurn::Slow?TEXT("rate_band:below"):TEXT("rate_band:in"));
    if(Turned.Result==ETurn::TooFast)
        Notify(TEXT("急ぎすぎだ。一定の調子で回せ。"),TEXT("Too fast: the crank slips. Keep a steady rhythm."),3.f);
    if(bWorked&&TaskState.Done>DoneBefore) Fire(FString::Printf(TEXT("event:crank_turn_%d"),TaskState.Done));
    if(SoraBeatRules::GoalMet(TaskState,Task)) StopPlayerCrank();
    return bWorked;
}
bool USoraCampaignDirector::PlayerBellowsAxis(float Axis)
{
    if(!Task.AlternateTreads||!IsWorkingCrank()) return false;
    if(Mode().Settings()&&Mode().Settings()->RhythmAssist()) return true;
    if(SoraCrankInputRules::Tread(BellowsTreads,FMath::RoundToInt(Axis*1000.f)))
    {
        const int32 Before=SoraBeatRules::ProgressPermille(TaskState,Task);
        const int32 DoneBefore=TaskState.Done;
        if(TurnPlayerCrank(false))
        {
            if(DoneBefore==0&&TaskState.Done>0) Fire(TEXT("interact_start"));
            UpdateObjective(); Progressed(Before);
        }
    }
    return true;
}
void USoraCampaignDirector::TickPlayerCrank(int32 DeltaMs)
{
    const auto& M=Mode();
    const auto* Hero=M.Hero();
    const int32 Rate=Task.AlternateTreads&&M.Settings()&&M.Settings()->RhythmAssist()?1000:
        M.Settings()&&M.Settings()->HoldToCrank()?Task.HoldMilliTurnsS:0;
    if(SoraCrankInputRules::Tick(CrankInput,DeltaMs,Hero&&Hero->IsActionHeld(TEXT("Interact")),PlayerCrankEligible(),Rate))
    {
        const int32 ProgressBefore=TaskState.Progress;
        if(TurnPlayerCrank(false)&&ProgressBefore==0&&TaskState.Progress>0)
            Fire(TEXT("interact_start"));
        // TickBeat owns UpdateObjective/Progressed and the completion/wave edge.
    }
    if(Task.AlternateTreads&&IsWorkingCrank()) PresentRhythmCue();
    if(Hero) Hero->GetViewmodel()->SetHiddenInGame(CrankOccupiesHands()||HelmOccupiesHands(),true);
}
