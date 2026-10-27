#include "SoraCampaignDirector.h"
#include "Game/SoraCampaignReach.h"
#include "SoraCatalog.h"
#include "SoraEquipmentComponent.h"
#include "SoraGameMode.h"
#include "SoraPlayerCharacter.h"
#include "SoraWorldBuilder.h"
#include "SoraText.h"
#include "SoraTenementRules.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"

FVector USoraCampaignDirector::RecoveryApproach() const
{
    const auto* Space=ActiveSpace();
    const auto* Hero=Mode().Hero();
    // MOVE_Walking snaps a capsule to the midpoint of UE's floor-distance
    // band. Target that same height so ending a swept climb adds no snap to
    // its last movement step (and both landings remain exactly 700 cm apart).
    const float FloorGap=(UCharacterMovementComponent::MIN_FLOOR_DIST+UCharacterMovementComponent::MAX_FLOOR_DIST)*.5f;
    const float Height=Hero?Hero->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+FloorGap:100.f;
    return Space?FVector(Space->Recovery.X+(Space->bTenements?130.f:270.f),
        Space->Recovery.Y+(Space->bTenements?0.f:110.f),Height):FVector::ZeroVector;
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
            // The lining scroll shares this narrow shaft. The interaction
            // at its actual height can take the find as the ascent begins.
            if(ActiveSpace()->bTenements)PickUp();
            RecoveryClimb=ERecoveryClimb::Up;
            Hero.GetCharacterMovement()->SetMovementMode(MOVE_None);
        }
        return true;
    }
    if(FVector::Dist(Hero.GetActorLocation(),RecoveryApproach())<160.f)
    {
        RecoveryClimb=ActiveSpace()->bTenements?ERecoveryClimb::Align:ERecoveryClimb::Enter;
        Hero.GetEquipment()->Halt();
        Hero.GetCharacterMovement()->StopMovementImmediately();
        Hero.GetCharacterMovement()->SetMovementMode(MOVE_None);
        Notify(SoraText::Line(NSLOCTEXT("SoraArena.Campaign","RopeDown","縄をつかんだ。操作を長押しして下りる。離せばその場で止まる。")),5.f);
        return true;
    }
    if(NeedsEquipmentRecovery())
        if(const FSoraBeatSpace* Space=ActiveSpace())
            for(const FVector2D& Pickup:Space->Pickups)
                if(Near(ASoraWorldBuilder::Floor(Pickup),SoraCampaignReach::Interact))
                {
                    // Recovery gates the hoist, not unrelated caches,
                    // collectibles or other interactions elsewhere.
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
        const float RimClear=ActiveSpace()->bTenements?SoraTenementRules::Curb+5.f:0.f;
        FVector Target=RecoveryBottom()+FVector(0,0,Task.RecoveryDepthCm+RimClear);
        if(RecoveryClimb==ERecoveryClimb::Align||RecoveryClimb==ERecoveryClimb::Lower)Target=RecoveryApproach();
        else if(RecoveryClimb==ERecoveryClimb::Rise||RecoveryClimb==ERecoveryClimb::Exit)
            Target=RecoveryApproach()+FVector(0,0,RimClear);
        else if(RecoveryClimb==ERecoveryClimb::Down) Target=RecoveryBottom();
        const FVector Next=FMath::VInterpConstantTo(Hero->GetActorLocation(),Target,DeltaMs/1000.f,140.f);
        FHitResult Hit;
        Hero->SetActorLocation(Next,true,&Hit,ETeleportType::None);
        if(FVector::Dist(Hero->GetActorLocation(),Target)>1.f) return;
        if(RecoveryClimb==ERecoveryClimb::Align) RecoveryClimb=ERecoveryClimb::Rise;
        else if(RecoveryClimb==ERecoveryClimb::Rise) RecoveryClimb=ERecoveryClimb::Enter;
        else if(RecoveryClimb==ERecoveryClimb::Enter) RecoveryClimb=ERecoveryClimb::Down;
        else if(RecoveryClimb==ERecoveryClimb::Up) RecoveryClimb=ERecoveryClimb::Exit;
        else if(RecoveryClimb==ERecoveryClimb::Exit&&ActiveSpace()->bTenements)RecoveryClimb=ERecoveryClimb::Lower;
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
