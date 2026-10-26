#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraGameMode.h"
#include "SoraPlayerCharacter.h"
#include "SoraCampaignReach.h"
#include "SoraWorldBuilder.h"
#include "SoraEquipmentComponent.h"
#include "SoraSettings.h"
#include "SoraViewmodelComponent.h"
#include "Engine/World.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"

bool USoraCampaignDirector::IsWorkshopCraft() const
{return ActiveBeatData()&&ActiveBeatData()->Id==TEXT("ch03.b09");}
bool USoraCampaignDirector::AtWorkshopStation() const
{
    const auto* Hero=Mode().Hero();const auto* Space=ActiveSpace();
    if(!IsWorkshopCraft()||!Hero||!Hero->CanPlay()||!Space||
       !Space->StepStations.IsValidIndex(TaskState.Step))return false;
    const auto* Kit=Hero->GetEquipment();
    if(!Kit||Kit->IsStaggered()||Kit->IsCommittedStrike()||Kit->IsStepping()||Kit->bReloading)return false;
    const int Station=Space->StepStations[TaskState.Step];if(!Space->Stations.IsValidIndex(Station))return false;
    const auto P=Space->Stations[Station];const FVector At=Hero->GetActorLocation();
    if(!Hero->GetCharacterMovement()->IsMovingOnGround()||
       FMath::Abs(At.Z-Hero->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()-Space->FloorAt(P))>8||
       FVector::Dist2D(At,FVector(P.X,P.Y,0))>=SoraCampaignReach::Interact)return false;
    // The shell bench sits beside the storehouse wall. Distance alone would
    // let a player work through that wall from inside the storehouse.
    FHitResult Hit;FCollisionQueryParams Query(SCENE_QUERY_STAT(WorkshopStation),false,Hero);
    return !GetWorld()->LineTraceSingleByChannel(Hit,At,FVector(P.X,P.Y,Space->FloorAt(P)+110),ECC_Visibility,Query);
}
void USoraCampaignDirector::CancelWorkshopCraft()
{
    if(WorkshopCraftOccupiesHands())
    {
        if(Mode().Hero())Mode().Hero()->GetViewmodel()->SetHiddenInGame(false,true);
        SoraWorkshopCraftRules::Cancel(WorkshopCraft);
    }
    WorkshopCraftClock.Reset();
}
bool USoraCampaignDirector::BeginWorkshopCraft()
{
    namespace R=SoraWorkshopCraftRules;
    if(!IsWorkshopCraft())return false;
    if(WorkshopCraft.WaitRelease)return true;
    if(!R::Timed(TaskState.Step))return false;
    if(AtWorkshopStation()&&R::Begin(WorkshopCraft,TaskState.Step))
    {
        WorkshopCraftClock.Reset();auto* Hero=Mode().Hero();
        Hero->GetEquipment()->Halt();Hero->GetEquipment()->DropStance();Hero->StopSprint();
        Hero->GetViewmodel()->SetHiddenInGame(true,true);
    }
    return true;
}
void USoraCampaignDirector::ReleaseWorkshopCraft()
{
    const int Step=WorkshopCraft.Step;
    const auto Result=SoraWorkshopCraftRules::Release(WorkshopCraft,Mode().IsPlaying()&&AtWorkshopStation());
    if(Step>=0&&Mode().Hero())Mode().Hero()->GetViewmodel()->SetHiddenInGame(false,true);
    WorkshopCraftClock.Reset();ResolveWorkshopCraft(Step,Result);
}
void USoraCampaignDirector::TickWorkshopCraft(float DeltaSeconds)
{
    if(WorkshopCraft.Step<0)return;
    const int Step=WorkshopCraft.Step;const auto* Hero=Mode().Hero();
    const auto Result=SoraWorkshopCraftRules::Tick(WorkshopCraft,WorkshopCraftClock.Advance(DeltaSeconds),
        Step==TaskState.Step&&AtWorkshopStation()&&Hero&&Hero->IsActionHeld(TEXT("Interact")),
        Mode().Settings()&&Mode().Settings()->RhythmAssist());
    if(Result!=SoraWorkshopCraftRules::EResult::None)
    {
        WorkshopCraftClock.Reset();
        if(Mode().Hero())Mode().Hero()->GetViewmodel()->SetHiddenInGame(false,true);
    }
    ResolveWorkshopCraft(Step,Result,true);
}
void USoraCampaignDirector::ResolveWorkshopCraft(int32 Step,SoraWorkshopCraftRules::EResult Result,bool bFromTick)
{
    namespace R=SoraWorkshopCraftRules;using SoraBeatRules::EStroke;
    const auto* Beat=ActiveBeatData();
    if(!IsWorkshopCraft()||!Beat||Step!=TaskState.Step||!Beat->StepKinds.IsValidIndex(Step))return;
    const FString Kind=Beat->StepKinds[Step],Id=Beat->Id;
    if(Result==R::EResult::Missed)
    {
        Fire(TEXT("step_failed:")+Kind);
        Notify(TEXT("竹が割れた。新しい一本で、緑の帯に合わせて離そう。"),
            TEXT("The strip split. Take a fresh strip and release in the green band."),3.f);
        return;
    }
    if(Result!=R::EResult::Passed)return;
    const int Before=SoraBeatRules::ProgressPermille(TaskState,Task),DoneBefore=TaskState.Done;
    const auto Struck=SoraBeatRules::CreditStroke(TaskState,Task);if(Struck==EStroke::Refused)return;
    Fire(FString::Printf(TEXT("step_complete:%s:%d"),*Kind,Struck==EStroke::Counted?TaskState.StepDone:Task.Steps[Step].Count));
    if(!ActiveBeatData()||ActiveBeatData()->Id!=Id)return;
    if(Struck==EStroke::StepDone)Fire(TEXT("step_start:")+Beat->StepKinds[TaskState.Step]);
    if(Struck==EStroke::Finished)Fire(TEXT("output_complete"));
    if(!ActiveBeatData()||ActiveBeatData()->Id!=Id)return;
    if(DoneBefore==0)Fire(TEXT("interact_start"));
    if(!ActiveBeatData()||ActiveBeatData()->Id!=Id)return;
    UpdateObjective();
    // TickBeat publishes the frame's progress once at its end. A key release
    // happens outside that frame update and must publish immediately.
    if(!bFromTick)Progressed(Before);
}
