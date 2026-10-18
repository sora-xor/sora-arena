#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraEnemy.h"
#include "SoraGameMode.h"
#include "SoraPlayerCharacter.h"
#include "SoraWorldBuilder.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/Controller.h"

bool USoraCampaignDirector::IsMaaiLesson() const
{
    return Mode().bCampaign && ActiveBeatData() && Task.Maai.Count > 0;
}
bool USoraCampaignDirector::MaaiReady() const
{
    return IsMaaiLesson() && (TaskState.Forms & Task.LessonMask) == Task.LessonMask;
}
ASoraEnemy* USoraCampaignDirector::MaaiMentor() const
{
    if(IsMaaiLesson()) for(ASoraEnemy* Enemy:Enemies)
        if(IsValid(Enemy) && Enemy->IsAlive()) return Enemy;
    return nullptr;
}
float USoraCampaignDirector::MaaiDistance() const
{
    const ASoraEnemy* Mentor=MaaiMentor();
    const ASoraPlayerCharacter* Hero=Mode().Hero();
    return Mentor&&Hero?FVector::Dist2D(Mentor->GetActorLocation(),Hero->GetActorLocation()):-1.f;
}
bool USoraCampaignDirector::MaaiInBand() const
{
    return MaaiReady() && !bMaaiMoving && TaskState.Maai.InBand;
}
bool USoraCampaignDirector::MaaiNeedsHelp() const
{
    return MaaiReady() && !bMaaiMoving && SoraMaaiRules::Hint(TaskState.Maai,Task.Maai);
}
void USoraCampaignDirector::ResetMaai()
{
    bMaaiMoving=false; bMaaiTooClose=false; bMaaiObstructionReported=false;
    if(ASoraEnemy* Mentor=MaaiMentor())
    {
        // The lesson's anchor is in the clear central floor, with room for
        // all three measured steps. The ordinary sparring AI is held here.
        Mentor->GetCharacterMovement()->StopMovementImmediately();
        if(const FSoraBeatSpace* Space=ActiveSpace())
            Mentor->SetActorLocation(ASoraWorldBuilder::Floor(Space->Anchor,Mentor->GetActorLocation().Z),false,nullptr,ETeleportType::TeleportPhysics);
        MaaiTarget=Mentor->GetActorLocation();
        if(const ASoraPlayerCharacter* Hero=Mode().Hero())
            Mentor->SetActorRotation((Hero->GetActorLocation()-MaaiTarget).GetSafeNormal2D().Rotation());
    }
}
void USoraCampaignDirector::TickMaai(int32 DeltaMs)
{
    ASoraEnemy* Mentor=MaaiMentor();
    const ASoraPlayerCharacter* Hero=Mode().Hero();
    if(!Mentor||!Hero||!MaaiReady()) return;
    Mentor->GetCharacterMovement()->StopMovementImmediately();
    Mentor->SetActorRotation((Hero->GetActorLocation()-Mentor->GetActorLocation()).GetSafeNormal2D().Rotation());
    if(bMaaiMoving)
    {
        // A visible, swept step, not a teleport or a count granted by a timer.
        MaaiTarget.Z=Mentor->GetActorLocation().Z;
        const FVector Next=FMath::VInterpConstantTo(Mentor->GetActorLocation(),MaaiTarget,DeltaMs/1000.f,120.f);
        FHitResult Hit;
        Mentor->SetActorLocation(Next,true,&Hit);
        if(Hit.bBlockingHit&&!bMaaiObstructionReported)
        {
            bMaaiObstructionReported=true;
            UE_LOG(LogTemp,Warning,TEXT("Maai step obstructed: mentor=%s target=%s actor=%s component=%s normal=%s penetration=%d depth=%.3f mode=%d"),
                *Mentor->GetActorLocation().ToString(),*MaaiTarget.ToString(),*GetNameSafe(Hit.GetActor()),
                *GetNameSafe(Hit.GetComponent()),*Hit.Normal.ToString(),Hit.bStartPenetrating,Hit.PenetrationDepth,
                static_cast<int32>(Mentor->GetCharacterMovement()->MovementMode));
        }
        bMaaiMoving=FVector::DistSquared2D(Mentor->GetActorLocation(),MaaiTarget)>.01f;
        TaskState.Maai.HeldMs=0; TaskState.Maai.InBand=false;
        return;
    }
    const FVector Toward=(Mentor->GetActorLocation()-Hero->GetActorLocation()).GetSafeNormal2D();
    const FVector Facing=Hero->GetControlRotation().Vector().GetSafeNormal2D();
    const float Distance=MaaiDistance();
    const bool bTooClose=Distance<Task.Maai.InnerCm;
    if(bTooClose&&!bMaaiTooClose) Fire(TEXT("gate_retry:maai_step"));
    bMaaiTooClose=bTooClose;
    const int32 Before=SoraBeatRules::ProgressPermille(TaskState,Task);
    const SoraMaaiRules::EResult Result=SoraMaaiRules::Tick(TaskState.Maai,Task.Maai,DeltaMs,Distance,FVector::DotProduct(Facing,Toward),true);
    if(Result==SoraMaaiRules::EResult::None) return;
    if(Result==SoraMaaiRules::EResult::Complete) Fire(TEXT("gate_complete:maai_step"));
    else
    {
        if(Result==SoraMaaiRules::EResult::Acquired) MaaiForward=-Toward;
        else Fire(TEXT("maai_step_ok"));
        const auto& Move=Task.Maai.Moves[TaskState.Maai.Done];
        const FVector Right=FVector::CrossProduct(FVector::UpVector,MaaiForward);
        MaaiTarget=Mentor->GetActorLocation()+MaaiForward*Move.ForwardCm+Right*Move.RightCm;
        bMaaiMoving=true; bMaaiObstructionReported=false;
    }
    Progressed(Before);
}
