#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraEnemy.h"
#include "SoraEnemyController.h"
#include "SoraGameMode.h"
#include "SoraHorseWithdrawalRules.h"
#include "SoraWorldBuilder.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"

namespace R=SoraHorseWithdrawalRules;
void USoraCampaignDirector::ResetHorseWithdrawal()
{
    bHorseWithdrawal=false; bHorseWithdrawalReady=false; bHorseGateClearQueued=false;
    HorseWithdrawalBark=INDEX_NONE; HorseGateClearBark=INDEX_NONE;
    const auto Retiring=MoveTemp(HorseWithdrawalEnemies); HorseWithdrawalEnemies.Reset();
    for(const auto& Weak:Retiring)
        if(auto* Enemy=Weak.Get(); IsValid(Enemy)&&!Enemy->IsActorBeingDestroyed())
        {
            Enemy->SetCampaignWithdrawal(false);
            if(auto* Brain=Cast<ASoraEnemyController>(Enemy->GetController())) Brain->ClearErrand();
        }
}
bool USoraCampaignDirector::HorseWithdrawalReady()
{
    const auto* Beat=ActiveBeatData();
    if(!Beat||!Beat->Space.bHorseWithdrawal||bHorseWithdrawalReady) return true;
    if(bHorseWithdrawal||!SoraBeatRules::TaskComplete(TaskState,Task)) return false;
    // The task is already won at 150 seconds. This visible outro is not a
    // new wave/kill goal: only the living, actually registered wave members go.
    TArray<TWeakObjectPtr<ASoraEnemy>> Survivors;
    for(const auto& Enemy:Enemies)
        if(IsValid(Enemy)&&!Enemy->IsActorBeingDestroyed()&&Enemy->IsAlive())
            if(const auto* Wave=EnemyWaves.Find(TWeakObjectPtr<const ASoraEnemy>(Enemy.Get())); Wave&&*Wave!=INDEX_NONE)
                Survivors.Add(Enemy.Get());
    if(Survivors.Num()>R::Slots)
    { UE_LOG(LogTemp,Error,TEXT("SORA horse withdrawal: more survivors than the authored six-enemy cap")); return false; }
    const int32 Bark=ActiveChapter()->Dialogue.IndexOfByPredicate([](const FSoraDialogueCue& Cue)
        { return Cue.Id==TEXT("ch02.b02.enforcer.009"); });
    const int32 ClearBark=ActiveChapter()->Dialogue.IndexOfByPredicate([](const FSoraDialogueCue& Cue)
        { return Cue.Id==TEXT("ch02.b06.kohagi.006"); });
    if(Bark==INDEX_NONE||ClearBark==INDEX_NONE)
    {
        UE_LOG(LogTemp,Error,TEXT("SORA horse withdrawal: authored retreat or gate-clear bark missing"));
        return false;
    }
    // Retire warning/projectile generations before any outro events can call
    // back into the director. Capped, unspawned pod members never emerge here.
    const uint64 ExpectedGeneration=PodGeneration+1;
    ResetPods();
    if(PodGeneration!=ExpectedGeneration||ActiveBeatData()!=Beat||Mode().bDefeated||
        !IsValid(GetOwner())||GetOwner()->IsActorBeingDestroyed()) return false;
    Pending.Reset(); CancelHorseTreatment();
    bHorseWithdrawal=true; HorseWithdrawalBark=Survivors.IsEmpty()?INDEX_NONE:Bark;
    HorseGateClearBark=ClearBark; HorseWithdrawalEnemies=MoveTemp(Survivors);
    FinishedLines.Remove(Bark); FinishedLines.Remove(ClearBark);
    const auto Walking=HorseWithdrawalEnemies;
    int32 Slot=0;
    for(const auto& Weak:Walking)
        if(auto* Enemy=Weak.Get(); IsValid(Enemy)&&!Enemy->IsActorBeingDestroyed()&&Enemy->IsAlive())
        {
            Enemy->SetCampaignWithdrawal(true);
            if(PodGeneration!=ExpectedGeneration||!bHorseWithdrawal||ActiveBeatData()!=Beat) return false;
            if(auto* Brain=Cast<ASoraEnemyController>(Enemy->GetController()))
                // Separate stations let later survivors pass the front rank;
                // a common large acceptance circle can form an impassable queue.
                Brain->SetErrand(FVector(R::GoalX+R::Offsets[Slot][0],R::GoalY+R::Offsets[Slot][1],
                    R::GoalZ+Enemy->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()),
                    FVector(-1,0,0),R::PacePermille/1000.f,0,false,false,R::SlotAcceptanceCm);
            ++Slot;
        }
    if(auto* Arena=Mode().Arena()) Arena->ShowObjective(nullptr);
    if(HorseWithdrawalBark!=INDEX_NONE) Fire(TEXT("event:horse_defense_withdrawal"),INDEX_NONE,true);
    return false;
}
bool USoraCampaignDirector::TickHorseWithdrawal(float DeltaSeconds)
{
    if(!bHorseWithdrawal) return false;
    if(Mode().bDefeated||!Mode().IsPlaying()) return true;
    // The won defense clock stays fixed, but ordinary held treatment remains
    // usable during the retreat; reuse its fractional active-time accumulator.
    ClockCarryMs+=DeltaSeconds*1000.f;
    const int32 DeltaMs=FMath::FloorToInt32(ClockCarryMs); ClockCarryMs-=DeltaMs;
    TickHorseTreatment(DeltaMs);
    // A blocked/partial navigation path is not arrival. Observe real feet at
    // the named courtyard approach, never ErrandReached's broader stop flag.
    for(const auto& Weak:HorseWithdrawalEnemies)
    {
        const auto* Enemy=Weak.Get();
        if(!IsValid(Enemy)||Enemy->IsActorBeingDestroyed()||!Enemy->IsAlive()) continue;
        const FVector At=Enemy->GetActorLocation();
        const double Feet=At.Z-Enemy->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
        if(!Enemy->GetCharacterMovement()->IsMovingOnGround()||FMath::Abs(Feet-R::GoalZ)>R::FloorToleranceCm||
           FVector::DistSquared2D(At,FVector(R::GoalX,R::GoalY,R::GoalZ))>FMath::Square(double(R::ArrivalCm))) return true;
    }
    if(HorseWithdrawalBark!=INDEX_NONE&&!FinishedLines.Contains(HorseWithdrawalBark)) return true;
    if(!bHorseGateClearQueued)
    {
        // The task is won, but its completion line must play before the next
        // cinematic takes over the subtitle display. Fire only the authored
        // dialogue trigger here; progress/save/completion broadcast remain below.
        // FiredTriggers prevents CompleteActiveBeat from queuing it a second time.
        bHorseGateClearQueued=true;
        Fire(TEXT("beat_complete"),INDEX_NONE,true);
        return true;
    }
    if(!FinishedLines.Contains(HorseGateClearBark)) return true;
    bHorseWithdrawalReady=true;
    CompleteActiveBeat();
    return true;
}
