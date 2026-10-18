#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraEquipmentComponent.h"
#include "SoraGameMode.h"
#include "SoraPlayerCharacter.h"
#include "SoraWorldBuilder.h"
#include "SoraText.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"

FVector USoraCampaignDirector::RecoveryApproach() const
{
    const auto* Space=ActiveSpace();
    const auto* Hero=Mode().Hero();
    const float Height=Hero?Hero->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+4.f:100.f;
    return Space?FVector(Space->Recovery.X+270.f,Space->Recovery.Y+110.f,Height):FVector::ZeroVector;
}
FVector USoraCampaignDirector::RecoveryBottom() const
{
    const auto* Space=ActiveSpace();
    FVector P=RecoveryApproach();
    if(Space) { P.X=Space->Recovery.X; P.Y=Space->Recovery.Y; P.Z-=Task.RecoveryDepthCm; }
    return P;
}
bool USoraCampaignDirector::AtRecoveryBottom() const
{
    const auto* Hero=Mode().Hero();
    return Task.RecoveryWeapons!=0u&&Hero&&FVector::Dist(Hero->GetActorLocation(),RecoveryBottom())<145.f;
}
void USoraCampaignDirector::EndRecoveryClimb()
{
    if(RecoveryClimb!=ERecoveryClimb::None)
        if(auto* Hero=Mode().Hero())
        {
            Hero->GetCharacterMovement()->StopMovementImmediately();
            Hero->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
        }
    RecoveryClimb=ERecoveryClimb::None;
    bStringingBow=false;
}
void USoraCampaignDirector::ResetEquipmentRecovery()
{
    bStringingBow=false;
    auto* Hero=Mode().Hero();
    if(!Hero) return;
    Hero->SetCampaignGearVisible(SoraBeatRules::EquipmentAllows(TaskState,Task,0));
    // The chapter's restriction applies even when chapter select or an
    // earlier chapter unlocked more weapons. A checkpoint restarts the
    // current beat; only the next checkpoint preserves this retrieval.
    if(!SoraBeatRules::EquipmentAllows(TaskState,Task,Hero->WeaponId))
    {
        auto* Kit=Hero->GetEquipment();
        Kit->Halt(); Kit->DropStance();
        for(int32 Id=0;Id<SoraBeatRules::WeaponCount;++Id)
            if(SoraBeatRules::EquipmentAllows(TaskState,Task,Id))
            {
                Kit->Hold(Id); Hero->RebuildWeapon(); break;
            }
    }
}
bool USoraCampaignDirector::InteractRecovery(ASoraPlayerCharacter& Hero)
{
    if(Task.RecoveryWeapons==0u) return false;
    if(IsClimbingRecoveryWell()||bStringingBow) return true;
    if(AtRecoveryBottom())
    {
        Hero.GetEquipment()->Halt();
        if(NeedsEquipmentRecovery())
        {
            bStringingBow=true; TaskState.RecoveryHeldMs=0;
            Fire(TEXT("interact:")+ActiveBeatData()->RecoveryInteract);
        }
        else
        {
            RecoveryClimb=ERecoveryClimb::Up;
            Hero.GetCharacterMovement()->SetMovementMode(MOVE_None);
        }
        return true;
    }
    if(FVector::Dist(Hero.GetActorLocation(),RecoveryApproach())<160.f)
    {
        RecoveryClimb=ERecoveryClimb::Enter;
        Hero.GetEquipment()->Halt();
        Hero.GetCharacterMovement()->StopMovementImmediately();
        Hero.GetCharacterMovement()->SetMovementMode(MOVE_None);
        Notify(SoraText::Line(NSLOCTEXT("SoraArena.Campaign","RopeDown","縄をつかんだ。操作を長押しして下りる。離せばその場で止まる。")),5.f);
        return true;
    }
    if(NeedsEquipmentRecovery())
    {
        Notify(SoraText::Line(NSLOCTEXT("SoraArena.Campaign","FindBundleFirst","先に空井戸の底から刀と弓を取り戻そう。")),3.f);
        return true;
    }
    return false;
}
void USoraCampaignDirector::TickEquipmentRecovery(int32 DeltaMs)
{
    if(Task.RecoveryWeapons==0u) return;
    auto* Hero=Mode().Hero();
    if(!Hero) return;
    const bool Held=Hero->IsActionHeld(TEXT("Interact"));
    if(IsClimbingRecoveryWell())
    {
        auto* Movement=Hero->GetCharacterMovement();
        Movement->StopMovementImmediately();
        // Ordinary input begins and holds traversal. Each step sweeps the
        // real capsule, so blocked ropes cannot grant pickup or teleport.
        if(!Held) return;
        FVector Target=RecoveryBottom()+FVector(0,0,Task.RecoveryDepthCm);
        if(RecoveryClimb==ERecoveryClimb::Down) Target=RecoveryBottom();
        else if(RecoveryClimb==ERecoveryClimb::Exit) Target=RecoveryApproach();
        const FVector Next=FMath::VInterpConstantTo(Hero->GetActorLocation(),Target,DeltaMs/1000.f,140.f);
        FHitResult Hit;
        Hero->SetActorLocation(Next,true,&Hit,ETeleportType::None);
        if(FVector::Dist(Hero->GetActorLocation(),Target)>1.f) return;
        if(RecoveryClimb==ERecoveryClimb::Enter) RecoveryClimb=ERecoveryClimb::Down;
        else if(RecoveryClimb==ERecoveryClimb::Up) RecoveryClimb=ERecoveryClimb::Exit;
        else
        {
            const bool Bottom=RecoveryClimb==ERecoveryClimb::Down;
            EndRecoveryClimb();
            Notify(SoraText::Line(Bottom?NSLOCTEXT("SoraArena.Campaign","BundleAtBottom","井戸の底だ。操作を離し、包みの前でもう一度長押しして弓に弦を張る。"):
                NSLOCTEXT("SoraArena.Campaign","RopeOut","井戸から上がった。釣瓶で道具の箱を引き上げよう。")),6.f);
            UpdateObjective();
        }
        return;
    }
    if(!bStringingBow) return;
    if(SoraBeatRules::RecoverEquipment(TaskState,Task,DeltaMs,AtRecoveryBottom(),Held))
    {
        bStringingBow=false;
        auto* Kit=Hero->GetEquipment();
        Kit->Halt(); Kit->DropStance();
        Kit->AmmoByWeapon[18]=Task.RecoveryQuiver;
        Kit->Hold(0); Hero->RebuildWeapon();
        Hero->SetCampaignGearVisible(true);
        if(auto* World=Mode().Arena()) World->ShowRecoveryBundle(false);
        Fire(TEXT("item_picked:")+ActiveBeatData()->RecoveryItem);
        Notify(SoraText::Line(NSLOCTEXT("SoraArena.Campaign","ArmsRecovered","刀と脇差、弓、矢十二本を取り戻した。縄で操作を長押しして上がる。")),6.f);
        UpdateObjective();
    }
    else if(!Held||!AtRecoveryBottom()) bStringingBow=false;
}
