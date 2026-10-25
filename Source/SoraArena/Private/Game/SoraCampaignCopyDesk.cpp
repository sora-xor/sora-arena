#include "SoraCampaignDirector.h"
#include "SoraCampaignReach.h"
#include "SoraCatalog.h"
#include "SoraEnemy.h"
#include "SoraEquipmentComponent.h"
#include "SoraGameMode.h"
#include "SoraPlayerCharacter.h"
#include "SoraViewmodelComponent.h"
#include "SoraWorldBuilder.h"
#include "Camera/CameraComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"

bool USoraCampaignDirector::AtCopyDesk(int32 Index) const
{
    const auto* Space=ActiveSpace();
    const auto* Hero=Mode().Hero();
    if(!Space||!Hero||Index<0||Index>=Task.HoldPointCount||!Space->Objectives.IsValidIndex(Index)||
        !Hero->GetCharacterMovement()->IsMovingOnGround()||
        FMath::Abs(Hero->GetActorLocation().Z-Space->HeightCm)>=180.f||
        !Near(ASoraWorldBuilder::Floor(Space->Objectives[Index],Space->HeightCm),SoraCampaignReach::Interact)) return false;
    // End just above the ledger, not inside the writing desk's collision.
    // A wall or closed door must block both admission and ongoing copying.
    const FVector Page=ASoraWorldBuilder::Floor(Space->Objectives[Index],Space->HeightCm)+FVector(0,102,80);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(CopyDesk),false,Hero);
    FHitResult Hit;
    return !GetWorld()->LineTraceSingleByChannel(Hit,Hero->GetEye()->GetComponentLocation(),Page,ECC_Visibility,Query);
}
void USoraCampaignDirector::CancelCopying()
{
    const bool WasCopying=IsCopying();
    CopyDesk=INDEX_NONE;
    if(WasCopying)
    {
        bHeldWatched=false;
        if(auto* Hero=Mode().Hero()) Hero->GetViewmodel()->SetHiddenInGame(false,true);
    }
}
bool USoraCampaignDirector::InteractCopyDesk(ASoraPlayerCharacter& Player)
{
    if(Task.HoldPointCount<=0||!Mode().IsPlaying()||!Player.CanPlay()) return false;
    int32 Nearest=INDEX_NONE;
    double Distance=TNumericLimits<double>::Max();
    for(int32 Point=0;Point<Task.HoldPointCount;++Point)
    {
        if(TaskState.HoldProgress[Point]>=Task.HoldPointMs||!AtCopyDesk(Point)) continue;
        const double ThisDistance=FVector2D::Distance(FVector2D(Player.GetActorLocation()),ActiveSpace()->Objectives[Point]);
        if(ThisDistance<Distance) { Nearest=Point;Distance=ThisDistance; }
    }
    if(Nearest!=INDEX_NONE)
    {
        // Admission comes from the player's current mapped Interact press.
        // Calling Interact directly without a held key cannot begin work.
        if(!Player.IsActionHeld(TEXT("Interact"))) return true;
        auto* Kit=Player.GetEquipment();
        if(Kit->IsStaggered()||Kit->IsCommittedStrike()||Kit->IsStepping()||Kit->bReloading) return true;
        if(!IsCopying())
        {
            Kit->Halt(); Kit->DropStance(); Player.StopSprint();
            CopyDesk=Nearest;
            Player.GetViewmodel()->SetHiddenInGame(true,true);
            Fire(TEXT("interact:")+ActiveBeatData()->Objectives[Nearest]);
        }
        return true;
    }
    return false;
}
bool USoraCampaignDirector::CopyDeskContested() const
{
    const auto* Space=ActiveSpace();
    if(!Space||!Space->Objectives.IsValidIndex(CopyDesk)) return false;
    const FVector At=ASoraWorldBuilder::Floor(Space->Objectives[CopyDesk],Space->HeightCm);
    for(const auto& Enemy:Enemies)
        if(IsValid(Enemy)&&Enemy->IsEnemy()&&Enemy->IsAlive()&&
            FVector::Dist2D(Enemy->GetActorLocation(),At)<SoraCampaignReach::Interact&&
            FMath::Abs(Enemy->GetActorLocation().Z-At.Z)<180.f) return true;
    return false;
}
bool USoraCampaignDirector::TickCopyDesk(SoraBeatRules::FTick Step)
{
    if(Task.HoldPointCount<=0) return false;
    const auto* Hero=Mode().Hero();
    if(!Hero||!Hero->CanPlay()||!Hero->IsActionHeld(TEXT("Interact"))||!AtCopyDesk(CopyDesk)) CancelCopying();
    Step.HoldPoint=CopyDesk;
    Step.AtTask=IsCopying();
    bHeldWatched=IsCopying()&&(Step.Seen||Step.Contested);
    const int32 Point=CopyDesk;
    SoraBeatRules::Tick(TaskState,Task,Step);
    if(Point>=0&&TaskState.HoldProgress[Point]>=Task.HoldPointMs)
    {
        CancelCopying();
        Fire(TEXT("event:objective_done_")+ActiveBeatData()->Objectives[Point]);
        UpdateObjective();
    }
    return true;
}
FString USoraCampaignDirector::CopyDeskText(bool English) const
{
    FString Text=English?FString::Printf(TEXT("Copy the totals: %d of %d desks"),TaskState.Done,Task.HoldPointCount):
        FString::Printf(TEXT("総高を写す：帳台 %d / %d"),TaskState.Done,Task.HoldPointCount);
    if(IsCopying()) Text+=English?FString::Printf(TEXT("  |  Desk %d: %d of %d s"),CopyDesk+1,TaskState.HoldProgress[CopyDesk]/1000,Task.HoldPointMs/1000):
        FString::Printf(TEXT("  |  帳台 %d：%d / %d 秒"),CopyDesk+1,TaskState.HoldProgress[CopyDesk]/1000,Task.HoldPointMs/1000);
    return Text;
}
