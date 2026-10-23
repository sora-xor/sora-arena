#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraCompanion.h"
#include "SoraFieldcraft.h"
#include "SoraFoundryFurnace.h"
#include "SoraGameMode.h"
#include "SoraPlayerCharacter.h"
#include "SoraEquipmentComponent.h"
#include "SoraViewmodelComponent.h"
#include "SoraWorldBuilder.h"
#include "SoraSettings.h"
#include "SoraFrontEnd.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
namespace FoundryRules=SoraFoundryDefenseRules;
bool USoraCampaignDirector::IsFoundryDefense() const
{
    return Mode().bCampaign&&ActiveSpace()&&ActiveSpace()->FoundryDefense.bEnabled;
}
ASoraFoundryFurnace* USoraCampaignDirector::FoundryFurnace() const
{
    return IsFoundryDefense()&&Mode().Arena()?Mode().Arena()->FoundryTarget():nullptr;
}
ASoraCompanion* USoraCampaignDirector::FoundryKozo() const
{
    const auto* Craft=USoraFieldcraft::Get(this);
    return IsFoundryDefense()&&Craft&&Craft->PeopleInPlay().IsValidIndex(0)?Craft->PeopleInPlay()[0].Get():nullptr;
}
void USoraCampaignDirector::CancelFoundryWork()
{
    const bool Working=Foundry.Work!=FoundryRules::EWork::None;
    FoundryRules::Cancel(Foundry);
    if(Working&&Mode().Hero()) Mode().Hero()->GetViewmodel()->SetHiddenInGame(HelmOccupiesHands()||CrankOccupiesHands(),true);
}
void USoraCampaignDirector::ResetFoundry()
{
    CancelFoundryWork(); Foundry={};
}
FVector USoraCampaignDirector::FoundryWorkPoint(FoundryRules::EWork Work,int32 Index) const
{
    if(!IsFoundryDefense()) return FVector::ZeroVector;
    if(Work==FoundryRules::EWork::Repair&&ActiveSpace()->FoundryDefense.Tubs.IsValidIndex(Index))
        return FVector(ActiveSpace()->FoundryDefense.Tubs[Index],55);
    if(Work==FoundryRules::EWork::Revive&&FoundryKozo()) return FoundryKozo()->GetActorLocation();
    if(Work==FoundryRules::EWork::Net)
        if(const auto* Craft=USoraFieldcraft::Get(this); Craft&&Index>=0&&Index<2) return Craft->QuarryLocation(Index)+FVector(0,0,55);
    return FVector::ZeroVector;
}
bool USoraCampaignDirector::FoundryWorkEligible(FoundryRules::EWork Work,int32 Index) const
{
    const auto* Hero=Mode().Hero(); const auto* Kit=Hero?Hero->GetEquipment():nullptr;
    if(!IsFoundryDefense()||!Hero||!Hero->CanPlay()||Kit->IsStaggered()||Kit->IsCommittedStrike()||Kit->IsStepping()||Kit->bReloading) return false;
    const auto* Craft=USoraFieldcraft::Get(this);
    if(Work==FoundryRules::EWork::Repair&&(!FoundryRules::Available(Foundry,Index)||TaskState.TargetHp[0]<=0||TaskState.TargetHp[0]>=FoundryRules::FurnaceHp)) return false;
    if(Work==FoundryRules::EWork::Revive&&(Index!=0||!FoundryKozo()||!FoundryKozo()->IsDown())) return false;
    if(Work==FoundryRules::EWork::Net&&(!Craft||Index<0||Index>=2||Craft->NetOf(Index)!=SoraFieldcraftRules::ENet::Netted)) return false;
    if(Work==FoundryRules::EWork::None) return false;
    const FVector At=FoundryWorkPoint(Work,Index),Here=Hero->GetActorLocation();
    if(FVector::Dist2D(Here,At)>190||FMath::Abs(Here.Z-Hero->GetCapsuleComponent()->GetScaledCapsuleHalfHeight())>60) return false;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(FoundryWork),false,Hero);
    if(Work==FoundryRules::EWork::Revive) Query.AddIgnoredActor(FoundryKozo());
    if(Work==FoundryRules::EWork::Net&&Craft->PeopleInPlay().IsValidIndex(Index+1)) Query.AddIgnoredActor(Craft->PeopleInPlay()[Index+1]);
    FHitResult Hit;
    // The final 35 cm ends above the tub/cloth, not inside its collision.
    return !GetWorld()->LineTraceSingleByChannel(Hit,Hero->GetEye()->GetComponentLocation(),At+FVector(0,0,35),ECC_Visibility,Query);
}
bool USoraCampaignDirector::InteractFoundry(ASoraPlayerCharacter& Hero)
{
    if(!IsFoundryDefense()) return false;
    if(FoundryOccupiesHands()) return true;
    const auto Begin=[&](FoundryRules::EWork Work,int Index)
    {
        if(!FoundryWorkEligible(Work,Index)||!FoundryRules::Begin(Foundry,Work,Index)) return false;
        Hero.GetEquipment()->Halt(); Hero.GetEquipment()->DropStance(); Hero.StopSprint();
        Hero.GetViewmodel()->SetHiddenInGame(true,true); return true;
    };
    if(Begin(FoundryRules::EWork::Revive,0)) return true;
    for(int I=0;I<2;++I) if(Begin(FoundryRules::EWork::Net,I)) return true;
    for(int I=0;I<3;++I) if(Begin(FoundryRules::EWork::Repair,I)) return true;
    // Consume E throughout this beat so the old unbounded instant repair
    // and generic net hold cannot compete with these authored transactions.
    return true;
}
bool USoraCampaignDirector::FoundryReadyToComplete() const
{
    return !IsFoundryDefense()||(!Foundry.Failed&&FoundryKozo()&&!FoundryKozo()->IsDown()&&FoundryKozo()->IsAlive()&&TaskState.TargetHp[0]>0);
}
void USoraCampaignDirector::TickFoundry(int32 DeltaMs)
{
    if(!IsFoundryDefense()) return;
    const FSoraBeat* Beat=ActiveBeatData();
    auto* Kozo=FoundryKozo(); auto* Craft=USoraFieldcraft::Get(this); auto* Hero=Mode().Hero();
    if(!Kozo||!Craft||!FoundryFurnace()) return;
    TaskState.TargetHp[1]=FMath::RoundToInt32(Kozo->Health);
    const bool Held=Hero&&Hero->IsActionHeld(TEXT("Interact"))&&FoundryWorkEligible(Foundry.Work,Foundry.Index);
    if(!Held) CancelFoundryWork();
    const bool Working=FoundryOccupiesHands();
    int Netted=0; for(int I=0;I<2;++I) Netted+=Craft->NetOf(I)==SoraFieldcraftRules::ENet::Netted;
    const auto Result=FoundryRules::Tick(Foundry,DeltaMs,Held,Kozo->IsDown(),Netted);
    if(Working&&!FoundryOccupiesHands()&&Hero) Hero->GetViewmodel()->SetHiddenInGame(false,true);
    if(Result.Failed)
    {
        HandleFailure(SoraBeatRules::ERetry::Checkpoint,TEXT("kozo_rescue_expired")); return;
    }
    if(Result.Repair>=0)
    {
        TaskState.TargetHp[0]=FMath::Min(FoundryRules::FurnaceHp,TaskState.TargetHp[0]+FoundryRules::RepairHp);
        FoundryFurnace()->Health=TaskState.TargetHp[0];
        Fire(TEXT("interact_done:")+FString(Result.Repair==0?TEXT("clay_tub_w"):Result.Repair==1?TEXT("clay_tub_e"):TEXT("clay_tub_n")));
        Notify(TEXT("粘土で炉を補修した。"),TEXT("Clay applied to the furnace."),3);
    }
    if(Result.Drain>0) DamageDefendedTarget(0,Result.Drain);
    if(ActiveBeatData()!=Beat||Mode().bDefeated) return;
    if(Result.Net>=0) Craft->FinishFoundryNetCut(Result.Net);
    if(ActiveBeatData()!=Beat||Mode().bDefeated) return;
    if(Result.Revive)
    {
        const auto Change=Kozo->Step(FoundryRules::ReviveMs,true);
        TaskState.TargetHp[1]=FMath::RoundToInt32(Kozo->Health);
        Craft->CompanionChanged(*Kozo,Change);
        if(ActiveBeatData()!=Beat||Mode().bDefeated) return;
    }
    unsigned NetMask=0; for(int I=0;I<2;++I) if(Craft->NetOf(I)==SoraFieldcraftRules::ENet::Netted) NetMask|=1u<<I;
    if(Mode().Arena()) Mode().Arena()->ShowFoundrySupplies(Foundry.Used,NetMask);
}
FString USoraCampaignDirector::FoundryText(bool English) const
{
    const int Left=3-((Foundry.Used&1)!=0)-((Foundry.Used&2)!=0)-((Foundry.Used&4)!=0);
    const auto Key=SoraUI::ActionKey(this,TEXT("Interact"));
    FString Text=English?FString::Printf(TEXT("Protect the furnace %d / 180 s | Furnace %d HP | Clay %d (hold %s 3 s)"),TaskState.Progress/1000,TaskState.TargetHp[0],Left,*Key.English):
        FString::Printf(TEXT("炉を守る %d / 180 秒 | 炉 %d HP | 粘土 %d（%s を3秒長押し）"),TaskState.Progress/1000,TaskState.TargetHp[0],Left,*Key.Japanese);
    if(FoundryKozo()&&FoundryKozo()->IsDown()) Text+=English?
        FString::Printf(TEXT(" | Kōzō down: revive 4 s, %d s left"),FMath::DivideAndRoundUp(25000-Foundry.DownMs,1000)):
        FString::Printf(TEXT(" | 鋼蔵を4秒で蘇生：残り%d秒"),FMath::DivideAndRoundUp(25000-Foundry.DownMs,1000));
    if(const auto* C=USoraFieldcraft::Get(this); C&&(C->NetOf(0)==SoraFieldcraftRules::ENet::Netted||C->NetOf(1)==SoraFieldcraftRules::ENet::Netted))
        Text+=English?FString::Printf(TEXT(" | Bellows netted: −5 HP/s; hold %s 1 s to free"),*Key.English):
            FString::Printf(TEXT(" | 鞴の仲間が捕縛中：炉 −5 HP/秒、%s を1秒長押しで解放"),*Key.Japanese);
    return Text;
}
