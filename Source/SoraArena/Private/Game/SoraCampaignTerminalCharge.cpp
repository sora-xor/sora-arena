#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraGameMode.h"
#include "SoraPlayerCharacter.h"
#include "SoraEquipmentComponent.h"
#include "SoraWorldBuilder.h"
#include "SoraFieldcraft.h"
#include "SoraCampaignReach.h"
#include "Combat/SoraDamage.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/World.h"

namespace TC=SoraTerminalChargeRules;
bool USoraCampaignDirector::IsTerminalCharge() const
{return ActiveBeatData()&&ActiveBeatData()->Id==TEXT("ch03.b10");}
void USoraCampaignDirector::CancelTerminalWork(bool Release)
{TC::Cancel(TerminalCharge,!Release);TerminalWorkClock.Reset();}
bool USoraCampaignDirector::AtTerminalPanel() const
{
    const auto* Hero=Mode().Hero();
    if(!IsTerminalCharge()||!Hero||!Hero->CanPlay())return false;
    const auto* Kit=Hero->GetEquipment();
    if(!Kit||Kit->IsStaggered()||Kit->IsCommittedStrike()||Kit->IsStepping()||Kit->bReloading)return false;
    const FVector P=Hero->GetActorLocation();
    const float Feet=P.Z-Hero->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    // Both holds require the north service face, not the screen or roof.
    if(!Hero->GetCharacterMovement()->IsMovingOnGround()||FMath::Abs(Feet)>8||P.Y<531||
       FVector::Dist2D(P,FVector(TC::PanelX,TC::PanelY,0))>=SoraCampaignReach::Interact)return false;
    FHitResult Hit;FCollisionQueryParams Q(SCENE_QUERY_STAT(TerminalPanel),false,Hero);
    return !GetWorld()->LineTraceSingleByChannel(Hit,P,FVector(TC::PanelX,TC::PanelY,110),ECC_Visibility,Q);
}
bool USoraCampaignDirector::TerminalSafe() const
{
    const auto* Hero=Mode().Hero();if(!Hero)return false;
    const FVector P=Hero->GetActorLocation();
    const float Feet=P.Z-Hero->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    FHitResult Hit;FCollisionQueryParams Q(SCENE_QUERY_STAT(TerminalCover),false,Hero);
    // Start above the terminal itself so its own collision cannot masquerade as cover.
    const bool Hidden=GetWorld()->LineTraceSingleByChannel(Hit,FVector(TC::TerminalX,TC::TerminalY,260),P,ECC_Visibility,Q);
    return TC::Safe(P.X,P.Y,Feet,Hero->GetCharacterMovement()->IsMovingOnGround(),Hidden);
}
bool USoraCampaignDirector::InteractTerminal()
{
    if(!IsTerminalCharge())return false;
    if(AtTerminalPanel()&&TC::Begin(TerminalCharge))
    {
        TerminalWorkClock.Reset();auto* Hero=Mode().Hero();
        Hero->GetEquipment()->Halt();Hero->GetEquipment()->DropStance();Hero->StopSprint();
        const int Index=TerminalCharge.Stage==TC::EStage::Empty?0:1;
        Fire(TEXT("interact_start:")+ActiveBeatData()->Objectives[Index]);
    }
    return true;
}
void USoraCampaignDirector::TickTerminalCharge(float DeltaSeconds)
{
    if(!IsTerminalCharge())return;
    // Fuse first. A hold which ignites in this frame starts at exactly zero.
    if(TerminalCharge.Stage==TC::EStage::Burning&&
       TC::Fuse(TerminalCharge,TerminalFuseClock.Advance(DeltaSeconds))==TC::EEvent::Detonated)
    {
        const bool Safe=TerminalSafe();
        if(auto* Arena=Mode().Arena())Arena->SetTerminalDestroyed(true);
        if(auto* Craft=USoraFieldcraft::Get(this))
            for(int I=0;I<ActiveSpace()->Fieldcraft.Lamps.Num();++I)
                if(ActiveSpace()->Fieldcraft.Lamps[I].Id==TEXT("terminal_glow_b10")&&Craft->Lamps().IsValidIndex(I))
                    Craft->Lamps()[I]->SetLit(false);
        Fire(TEXT("terminal_detonated"));
        if(!IsTerminalCharge()||Mode().bDefeated)return;
        const FVector Origin(TC::TerminalX,TC::TerminalY+50,110);
        SoraDamage::Ring(GetWorld(),Origin,TC::BlastRadius,FLinearColor(1.f,.68f,.2f),.5f);
        SoraDamage::Blast(*GetWorld(),TC::Damage,TC::BlastRadius,FSoraHit::Blast(Origin,7),
            Mode().Hero()->GetController(),Mode().Hero(),[this]{return IsTerminalCharge()&&!Mode().bDefeated;});
        if(!IsTerminalCharge()||Mode().bDefeated)return;
        if(!Safe)
        {
            Fire(TEXT("terminal_escape_missed"));
            HandleFailure(SoraBeatRules::ERetry::Checkpoint,TEXT("terminal_escape_missed"));
            Notify(TEXT("爆発までに北の路地の物陰へ。Enter でやり直す。"),
                   TEXT("Reach cover in the north alley before the blast. Press Enter to retry."),0.f);
            return;
        }
        WorkObjectiveAt(2);UpdateObjective();return;
    }
    if(!TerminalCharge.Working)return;
    const auto* Hero=Mode().Hero();
    const auto Result=TC::Work(TerminalCharge,TerminalWorkClock.Advance(DeltaSeconds),
        Hero&&Hero->IsActionHeld(TEXT("Interact"))&&AtTerminalPanel());
    if(!TerminalCharge.Working)TerminalWorkClock.Reset();
    if(Result==TC::EEvent::Planted||Result==TC::EEvent::Ignited)
    {
        TerminalFuseClock.Reset();
        WorkObjectiveAt(Result==TC::EEvent::Planted?0:1);UpdateObjective();
    }
}
