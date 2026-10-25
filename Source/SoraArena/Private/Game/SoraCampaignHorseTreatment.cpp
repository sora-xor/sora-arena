#include "SoraCampaignDirector.h"
#include "SoraHorse.h"
#include "SoraGameMode.h"
#include "SoraPlayerCharacter.h"
#include "SoraEquipmentComponent.h"
#include "SoraViewmodelComponent.h"
#include "SoraWorldBuilder.h"
#include "SoraFrontEnd.h"
#include "SoraCampaignReach.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/World.h"
namespace TreatmentRules=SoraHorseTreatmentRules;
bool USoraCampaignDirector::IsHorseTreatment() const
{ return Mode().bCampaign&&ActiveSpace()&&ActiveSpace()->bHorseTreatment; }
ASoraHorse* USoraCampaignDirector::TreatmentHorse(int32 Index) const
{ return IsHorseTreatment()&&Mode().Arena()?Mode().Arena()->DefendedHorse(Index):nullptr; }
bool USoraCampaignDirector::HorseTreatmentEligible(int32 Index) const
{
    const auto* Hero=Mode().Hero(); const auto* Horse=TreatmentHorse(Index);
    const auto* Kit=Hero?Hero->GetEquipment():nullptr;
    if(!IsValid(Horse)||Horse->IsHidden()||!Hero||!Hero->CanPlay()||!Kit||
        !Hero->GetCharacterMovement()->IsMovingOnGround()||Kit->IsStaggered()||Kit->IsCommittedStrike()||Kit->IsStepping()||Kit->bReloading||
        Index<0||Index>=TreatmentRules::Horses||!TreatmentRules::Eligible(Treatment,Index,TaskState.TargetHp[Index])) return false;
    const FVector At=Horse->GetActorLocation(),Here=Hero->GetActorLocation();
    if(FVector::Dist2D(Here,At)>SoraCampaignReach::Interact||FMath::Abs(Here.Z-At.Z)>60) return false;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(SoraHorseTreatment),false,Hero);
    Query.AddIgnoredActor(Horse); // The target's own body is the destination, never an obstruction.
    FHitResult Hit;
    return !GetWorld()->LineTraceSingleByChannel(Hit,Hero->GetEye()->GetComponentLocation(),At,ECC_Visibility,Query);
}
void USoraCampaignDirector::CancelHorseTreatment()
{
    const bool Working=Treatment.Index>=0; TreatmentRules::Cancel(Treatment);
    if(Working&&Mode().Hero()) Mode().Hero()->GetViewmodel()->SetHiddenInGame(HelmOccupiesHands()||CrankOccupiesHands()||FoundryOccupiesHands(),true);
}
void USoraCampaignDirector::ResetHorseTreatment()
{ CancelHorseTreatment(); Treatment={}; }
bool USoraCampaignDirector::InteractHorseTreatment(ASoraPlayerCharacter& Hero)
{
    if(!IsHorseTreatment()) return false;
    if(HorseTreatmentOccupiesHands()) return true;
    int32 Nearest=INDEX_NONE; double Distance=MAX_dbl;
    for(int32 Index=0;Index<TreatmentRules::Horses;++Index)
        if(HorseTreatmentEligible(Index))
        {
            const double D=FVector::DistSquared2D(Hero.GetActorLocation(),TreatmentHorse(Index)->GetActorLocation());
            if(D<Distance) { Nearest=Index; Distance=D; }
        }
    if(Nearest!=INDEX_NONE&&TreatmentRules::Begin(Treatment,Nearest,TaskState.TargetHp[Nearest]))
    {
        Hero.GetEquipment()->Halt(); Hero.GetEquipment()->DropStance(); Hero.StopSprint();
        Hero.GetViewmodel()->SetHiddenInGame(true,true);
    }
    // This beat never falls through to an instant repair from the anchor.
    return true;
}
void USoraCampaignDirector::TickHorseTreatment(int32 DeltaMs)
{
    if(!IsHorseTreatment()) return;
    auto* Hero=Mode().Hero();
    const bool Held=Hero&&Hero->IsActionHeld(TEXT("Interact"))&&HorseTreatmentEligible(Treatment.Index);
    if(!Held) CancelHorseTreatment();
    const int32 Completed=TreatmentRules::Tick(Treatment,DeltaMs,Held);
    if(Completed==INDEX_NONE) return;
    SoraBeatRules::RepairTarget(TaskState,Task,Completed,TreatmentRules::HealHp);
    if(Hero) Hero->GetViewmodel()->SetHiddenInGame(false,true);
    ShowKit();
    Notify(TEXT("荷馬の傷を手当てした。"),TEXT("The pack horse's wounds are treated."),3.f);
}
FString USoraCampaignDirector::HorseTreatmentText(bool English) const
{
    const auto Key=SoraUI::ActionKey(this,TEXT("Interact"));
    FString Text=English?FString::Printf(TEXT("Protect the pack horses %d / 150 s | Hold %s for 2 s to treat +60 HP"),TaskState.Progress/1000,*Key.English):
        FString::Printf(TEXT("荷馬を守る %d / 150 秒 | %s を2秒長押しで手当て（体力＋60）"),TaskState.Progress/1000,*Key.Japanese);
    for(int32 Index=0;Index<TreatmentRules::Horses;++Index)
    {
        const int32 Wait=FMath::DivideAndRoundUp(Treatment.Cooldown[Index],1000);
        Text+=English?FString::Printf(TEXT(" | Horse %d: %d/400 HP%s"),Index+1,TaskState.TargetHp[Index],
            Wait>0?*FString::Printf(TEXT(" (%d s until treatment)"),Wait):TEXT("")):
            FString::Printf(TEXT(" | 荷馬%d：体力%d/400%s"),Index+1,TaskState.TargetHp[Index],
            Wait>0?*FString::Printf(TEXT("（再手当てまで%d秒）"),Wait):TEXT(""));
    }
    if(HorseTreatmentOccupiesHands()) Text+=English?FString::Printf(TEXT(" | Treating horse %d: %d%%"),Treatment.Index+1,Treatment.HeldMs*100/TreatmentRules::HoldMs):
        FString::Printf(TEXT(" | 荷馬%dを手当て中：%d%%"),Treatment.Index+1,Treatment.HeldMs*100/TreatmentRules::HoldMs);
    return Text;
}
