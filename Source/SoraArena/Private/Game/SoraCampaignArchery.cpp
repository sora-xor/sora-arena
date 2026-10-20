#include "SoraCampaignDirector.h"
#include "SoraArcheryTarget.h"
#include "SoraCatalog.h"
#include "SoraEquipmentComponent.h"
#include "SoraGameMode.h"
#include "SoraFrontEnd.h"
#include "SoraPlayerCharacter.h"
#include "SoraProjectile.h"
#include "SoraSettings.h"
#include "SoraWorldBuilder.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"

bool USoraCampaignDirector::UsesDojoQuiver() const
{
    return Mode().bCampaign&&!Mode().bDeterministicPractice&&ChapterId==0;
}
bool USoraCampaignDirector::IsArcheryLesson() const
{
    return UsesDojoQuiver()&&ActiveBeatData()&&ActiveBeatData()->bArcheryLesson;
}
bool USoraCampaignDirector::CanLooseArcheryArrow() const
{
    return !IsArcheryLesson()||SoraArcheryRules::CanLoose(Archery);
}
FVector USoraCampaignDirector::ArcheryLine() const
{
    const auto* Space=ActiveSpace();
    // 4.2 m beyond the range entry, clear of both instructors. Rest distances
    // are measured horizontally from this line in the existing 72 m range.
    return Space?FVector(Space->Entry.X+420,Space->Entry.Y,Space->HeightCm):FVector::ZeroVector;
}
bool USoraCampaignDirector::AtArcheryLine() const
{
    const auto* Hero=Mode().Hero();
    if(!IsArcheryLesson()||!Hero||!Hero->CanPlay()||!Hero->GetCharacterMovement()->IsMovingOnGround()) return false;
    const FVector Feet=Hero->GetActorLocation()-FVector(0,0,Hero->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
    const FVector Delta=Feet-ArcheryLine();
    return FMath::Abs(Delta.X)<=60&&FMath::Abs(Delta.Y)<=220&&FMath::Abs(Delta.Z)<=20;
}
ASoraArcheryTarget* USoraCampaignDirector::ArcheryTarget(int32 Index) const
{
    return ArcheryTargets.IsValidIndex(Index)?ArcheryTargets[Index].Get():nullptr;
}
void USoraCampaignDirector::SetDojoArrows(int32 Count)
{
    auto* Hero=Mode().Hero();
    auto* Kit=Hero?Hero->GetEquipment():nullptr;
    if(!Kit||!Kit->AmmoByWeapon.IsValidIndex(18)) return;
    Kit->AmmoByWeapon[18]=FMath::Clamp(Count,0,SoraArcheryRules::Quiver);
    if(Hero->WeaponId==18) Kit->Ammo=Kit->AmmoByWeapon[18];
}
void USoraCampaignDirector::RestoreDojoQuiver()
{
    if(UsesDojoQuiver()) SetDojoArrows(SoraArcheryRules::Usable(BeatState.CompletedMask));
}
void USoraCampaignDirector::ClearArchery()
{
    // Invalidate pending identities before actor cleanup or checkpoint retry.
    // NextArcheryShot deliberately never resets within this director.
    Archery={}; ArcheryMs=0;
    for(ASoraArcheryTarget* Target:ArcheryTargets) if(IsValid(Target)) Target->Destroy();
    ArcheryTargets.Reset();
    if(IsValid(ArcheryLineMarker)) ArcheryLineMarker->Destroy();
    ArcheryLineMarker=nullptr;
}
void USoraCampaignDirector::BeginArchery()
{
    if(!IsArcheryLesson()||!GetWorld()) return;
    const int32 Difficulty=static_cast<int32>(SoraAccessibility::CampaignDifficulty(this));
    const FVector Line=ArcheryLine();
    ArcheryTargets.SetNum(4);
    for(int32 I=0;I<4;++I)
    {
        auto* Target=GetWorld()->SpawnActor<ASoraArcheryTarget>();
        if(!Target) continue;
        // Lanes separate the frames and their full ±150 cm swing. Target
        // centers are 40 cm above the floor, as the near mato specification.
        const double Distance=I?SoraArcheryRules::HangingCm[I-1]:SoraArcheryRules::NearCm;
        const double Lateral=I?SoraArcheryRules::HangingLaneCm[I-1]:0;
        const FVector Center=Line+FVector(FMath::Sqrt(Distance*Distance-Lateral*Lateral),Lateral,40);
        Target->Configure(I,Center,I?22.5f:SoraArcheryRules::HitRadius[Difficulty],I?45.f:36.f);
        ArcheryTargets[I]=Target;
    }
    ArcheryLineMarker=GetWorld()->SpawnActor<AActor>();
    if(ArcheryLineMarker)
    {
        auto* Mark=ASoraWorldBuilder::Shape(ArcheryLineMarker,nullptr,TEXT("ShajoShootingLine"),
            TEXT("/Engine/BasicShapes/Cube.Cube"),FVector::ZeroVector,FVector(.08f,4.4f,.02f),FLinearColor(.82f,.68f,.36f));
        ArcheryLineMarker->SetRootComponent(Mark);
        ArcheryLineMarker->SetActorLocation(Line+FVector(0,0,2));
    }
    StageArcheryTargets();
}
void USoraCampaignDirector::StageArcheryTargets()
{
    for(ASoraArcheryTarget* Target:ArcheryTargets)
    {
        if(!IsValid(Target)) continue;
        const int32 I=Target->TargetIndex();
        const bool Visible=Archery.Stage==SoraArcheryRules::EStage::Near?I==0:
            Archery.Stage==SoraArcheryRules::EStage::Hanging&&I>0&&(Archery.HangingHits&(1u<<(I-1)))==0;
        Target->SetAvailable(Visible&&Archery.FetchRemainingMs==0);
        Target->MoveForClock(ArcheryMs);
    }
}
unsigned long long USoraCampaignDirector::RegisterArcheryArrow(ASoraProjectile& Arrow)
{
    if(!IsArcheryLesson()||!Mode().Hero()||Arrow.GetOwner()!=Mode().Hero()||!Arrow.bArrow||Arrow.WeaponId!=18||
        !SoraArcheryRules::CanLoose(Archery)||NextArcheryShot==MAX_uint64) return 0;
    const auto Id=++NextArcheryShot;
    if(!SoraArcheryRules::Issue(Archery,Id,AtArcheryLine())) return 0;
    return Id;
}
void USoraCampaignDirector::ResolveArcheryArrow(ASoraProjectile& Arrow,const FHitResult* Impact)
{
    const auto Id=Arrow.ArcheryShotId;
    Arrow.ArcheryShotId=0; // Impact and EndPlay share exactly one resolution.
    if(!IsArcheryLesson()||Arrow.GetOwner()!=Mode().Hero()||!Arrow.bArrow||Arrow.WeaponId!=18) return;
    int32 TargetIndex=INDEX_NONE;
    const auto* Target=Impact?Cast<ASoraArcheryTarget>(Impact->GetActor()):nullptr;
    if(Target&&ArcheryTarget(Target->TargetIndex())==Target&&!Target->IsHidden()&&Target->ContainsImpact(*Impact))
        TargetIndex=Target->TargetIndex();
    const unsigned Hanging=Archery.HangingHits;
    const auto Result=SoraArcheryRules::Resolve(Archery,Id,TargetIndex);
    if(Result==SoraArcheryRules::EResult::Ignored) return;
    Fire(Archery.LastHit?TEXT("mato_hit"):TEXT("mato_miss"));
    if(Result==SoraArcheryRules::EResult::FailedSet) Fire(TEXT("set_failed"));
    if(Result==SoraArcheryRules::EResult::NearComplete)
    {
        SoraBeatRules::RecordDefeat(TaskState,Task,0);
        QueueWaves(SoraBeatRules::ReleaseWaves(TaskState,Task));
    }
    else if(Archery.HangingHits!=Hanging) SoraBeatRules::RecordDefeat(TaskState,Task,1);
    StageArcheryTargets();
    UpdateObjective();
}
void USoraCampaignDirector::TickArchery(int32 DeltaMs)
{
    if(!IsArcheryLesson()) return;
    ArcheryMs=(ArcheryMs+DeltaMs)%SoraArcheryRules::PeriodMs;
    const auto* Hero=Mode().Hero();
    const auto* Kit=Hero?Hero->GetEquipment():nullptr;
    const int32 Ammo=Kit?(Hero->WeaponId==18?Kit->Ammo:Kit->AmmoByWeapon[18]):0;
    if(SoraArcheryRules::FetchExhausted(Archery,Ammo)) Fire(TEXT("archery_fetch_exhausted"));
    // Count a newly requested fetch starting on the next frame, never grant
    // arrows from R or from an unfinished projectile.
    else if(SoraArcheryRules::TickFetch(Archery,DeltaMs))
    {
        SetDojoArrows(SoraArcheryRules::Quiver);
        Fire(TEXT("archery_arrows_fetched"));
    }
    StageArcheryTargets();
}
void USoraCampaignDirector::ExplainDojoQuiver()
{
    Notify(TEXT("矢は有限だ。的場では矢取りを待ち、曲がった矢は鍛冶場で直す。"),
        TEXT("Arrows are finite. At the range, wait for retrieval; repair bent arrows at the smithy."),5.f);
}
FString USoraCampaignDirector::ArcheryText(bool English) const
{
    if(Archery.FetchRemainingMs>0)
        return English?FString::Printf(TEXT("Arrow retrieval: %d s"),FMath::DivideAndRoundUp(Archery.FetchRemainingMs,1000)):
            FString::Printf(TEXT("矢取り：残り %d 秒"),FMath::DivideAndRoundUp(Archery.FetchRemainingMs,1000));
    if(Mode().Hero()&&Mode().Hero()->WeaponId!=18)
    {
        const auto Key=SoraUI::ActionKey(this,TEXT("WeaponThree"));
        return English?FString::Printf(TEXT("Select the yumi with %s, then stand on the gold shooting line."),*Key.English):
            FString::Printf(TEXT("%s で弓を選び、金色の射位に立つ。"),*Key.Japanese);
    }
    if(!AtArcheryLine()) return English?TEXT("Stand on the gold shooting line; select Bow, hold Attack, then release."):
        TEXT("金色の射位に立つ。弓を選び、攻撃を長押しして放す。");
    if(Archery.Stage==SoraArcheryRules::EStage::Near)
        return English?FString::Printf(TEXT("Near target: %d / 6 arrows resolved, %d / 4 hits"),Archery.Resolved,Archery.Hits):
            FString::Printf(TEXT("近的：六射中 %d 射、四中まで %d 中"),Archery.Resolved,Archery.Hits);
    return English?FString::Printf(TEXT("Hanging targets: %d / 3 — lead the swing and arrow drop"),SoraBeatRules::Defeated(TaskState,Task)-1):
        FString::Printf(TEXT("吊り的：%d / 3 — 揺れと矢の落下を読む"),SoraBeatRules::Defeated(TaskState,Task)-1);
}
