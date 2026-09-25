#include "SoraEquipmentComponent.h"
#include "Combat/SoraDamage.h"
#include "SoraCatalog.h"
#include "SoraCombatRules.h"
#include "SoraGameEvents.h"
#include "SoraHistoricalArms.h"
#include "SoraPlayerCharacter.h"
#include "SoraProjectile.h"
#include "Camera/CameraComponent.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"


USoraEquipmentComponent::USoraEquipmentComponent()
{
    // The hero's tick drives this component so its order within a frame is fixed.
    PrimaryComponentTick.bCanEverTick=false;
}
ASoraPlayerCharacter* USoraEquipmentComponent::Hero() const { return CastChecked<ASoraPlayerCharacter>(GetOwner()); }
void USoraEquipmentComponent::ResetForClass()
{
    const int32 WeaponId=Hero()->WeaponId;
    Ammo=FSoraCatalog::Get().Weapon(WeaponId).Magazine;
    AmmoByWeapon.SetNum(21); for(int32 I=0;I<21;++I) AmmoByWeapon[I]=FSoraCatalog::Get().Weapon(I).Magazine;
    bReloading=false; NextShot=0; bFireHeld=false; bBowDrawing=false; GuardStamina=100.f;
    bCommittedStrike=false; bHistoricalRecovery=false; CommittedWeaponId=INDEX_NONE;
}
void USoraEquipmentComponent::Hold(int32 WeaponId)
{
    bSheathed=false;
    Hero()->WeaponId=WeaponId;
    Ammo=FSoraCatalog::Get().Weapon(WeaponId).Magazine;
}
void USoraEquipmentComponent::DropStance()
{
    bGuardHeld=false; bBowDrawing=false; bCommittedStrike=false; bHistoricalRecovery=false;
}
void USoraEquipmentComponent::Halt()
{
    bBowDrawing=false; bCommittedStrike=false; bFireHeld=false; bGuardHeld=false;
}
float USoraEquipmentComponent::BowDrawProgress() const
{
    return bBowDrawing&&GetWorld()?FMath::Clamp((GetWorld()->GetTimeSeconds()-BowDrawStartedAt)/.65f,0.f,1.f):0.f;
}
float USoraEquipmentComponent::StrikeWindupProgress() const
{
    if(!bCommittedStrike||!GetWorld()||CommittedWeaponId==INDEX_NONE) return 0.f;
    const float Windup=SoraHistoricalArms::Profile(SoraHistoricalArms::FormFor(CommittedWeaponId)).WindupSeconds;
    return FMath::Clamp(1.f-(CommittedStrikeAt-GetWorld()->GetTimeSeconds())/Windup,0.f,1.f);
}
float USoraEquipmentComponent::MoveScale(bool bSprinting) const
{
    return bCommittedStrike?.35f:bHistoricalRecovery?.65f:bBowDrawing?.55f:bGuardHeld?.50f:bSprinting?1.35f:1.f;
}
void USoraEquipmentComponent::Stagger(float Seconds)
{
    const float Until=GetWorld()->GetTimeSeconds()+Seconds;
    StaggeredUntil=FMath::Max(StaggeredUntil,Until);
    bGuardHeld=false; bBowDrawing=false; bFireHeld=false;
    bCommittedStrike=false; CommittedWeaponId=INDEX_NONE;
    NextShot=FMath::Max(NextShot,StaggeredUntil);
}
bool USoraEquipmentComponent::IsStaggered() const { return GetWorld()&&GetWorld()->GetTimeSeconds()<StaggeredUntil; }
void USoraEquipmentComponent::Sheathe(bool bSheathe)
{
    if(bSheathe==bSheathed) return;
    if(bSheathe&&(!SoraHistoricalArms::IsMelee(Hero()->WeaponId)||bCommittedStrike||bReloading)) return;
    bSheathed=bSheathe; SheathedAt=GetWorld()->GetTimeSeconds();
    bGuardHeld=false; bBowDrawing=false; bFireHeld=false;
}
bool USoraEquipmentComponent::IsSheathed() const
{
    return bSheathed&&GetWorld()&&(GetWorld()->GetTimeSeconds()-SheathedAt)*1000.f>=SoraCombatRules::SheatheMs;
}
void USoraEquipmentComponent::TickGuard(float Dt)
{
    GuardStamina=FMath::Clamp(GuardStamina+(bGuardHeld?-28.f:21.f)*Dt,0.f,100.f);
    if(GuardStamina<SoraCombatRules::MinimumGuardStamina) bGuardHeld=false;
}
void USoraEquipmentComponent::TickWeapon()
{
    const float Now=GetWorld()->GetTimeSeconds();
    if(bCommittedStrike&&Now>=CommittedStrikeAt) ResolveCommittedStrike();
    if(bHistoricalRecovery&&Now>=NextShot) bHistoricalRecovery=false;
    if(bReloading&&Now>=ReloadEnd) { Ammo=FSoraCatalog::Get().Weapon(Hero()->WeaponId).Magazine; bReloading=false; }
    if(bFireHeld) Fire();
}
void USoraEquipmentComponent::TriggerDown()
{
    ASoraPlayerCharacter* H=Hero();
    const int32 WeaponId=H->WeaponId;
    const auto& W=FSoraCatalog::Get().Weapon(WeaponId);
    if(IsStaggered()||bSheathed) return;
    if(W.Kind==TEXT("bow"))
    {
        if(!bBowDrawing&&!bReloading&&!H->IsSprinting()&&Ammo>0&&GetWorld()->GetTimeSeconds()>=NextShot)
        { bBowDrawing=true; BowDrawStartedAt=GetWorld()->GetTimeSeconds(); }
        return;
    }
    if(!H->IsDojoTraining()&&SoraHistoricalArms::IsMelee(WeaponId)) { Fire(); return; }
    bFireHeld=true; Fire();
}
void USoraEquipmentComponent::TriggerUp() { bFireHeld=false; if(bBowDrawing) ReleaseBow(); }
void USoraEquipmentComponent::Fire()
{
    ASoraPlayerCharacter* H=Hero();
    if(H->IsKernelDriven()) return;
    if(!H->CanPlay()||bReloading||H->IsSprinting()||bBowDrawing||bCommittedStrike||GetWorld()->GetTimeSeconds()<NextShot) return;
    const auto& W=FSoraCatalog::Get().Weapon(H->WeaponId);
    if(W.Kind==TEXT("melee")) { Melee(); return; }
    if(W.Kind==TEXT("bow")) return;
    if(Ammo<=0) { Reload(); return; }
    --Ammo; NextShot=GetWorld()->GetTimeSeconds()+W.Cooldown;
    const UCameraComponent* Camera=H->GetCamera();
    const FVector Start=Camera->GetComponentLocation(); const FVector Dir=Camera->GetForwardVector();
    FSoraWeaponFiredEvent Fired;
    Fired.Shooter=H; Fired.WeaponId=H->WeaponId; Fired.Direction=Dir;
    if(W.Kind==TEXT("explosive"))
    {
        FActorSpawnParameters P; P.Owner=H; P.Instigator=H; P.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        auto* Shell=GetWorld()->SpawnActor<ASoraProjectile>(Start+Dir*70,Dir.Rotation(),P);
        Shell->Velocity=Dir*W.ProjectileSpeed; Shell->Damage=W.Damage; Shell->Radius=W.BlastRadius;
        Shell->WeaponId=H->WeaponId; Shell->ArmingCm=SoraCombatRules::ArmingCm(H->WeaponId);
        Fired.Kind=ESoraShotKind::Shell; Fired.Origin=Start+Dir*70; Fired.End=Fired.Origin;
        if(auto* Events=USoraGameEvents::Get(this)) Events->OnWeaponFired.Broadcast(Fired);
    }
    else
    {
        FHitResult Hit; FCollisionQueryParams Params(SCENE_QUERY_STAT(PlayerShot),false,H);
        const FVector End=Start+Dir*W.Range; GetWorld()->LineTraceSingleByChannel(Hit,Start,End,ECC_Visibility,Params);
        SoraDamage::Beam(GetWorld(),Start+Dir*65+Camera->GetRightVector()*17-Camera->GetUpVector()*12,Hit.bBlockingHit?Hit.ImpactPoint:End,W.Special?FLinearColor(.08,.9,.9):FLinearColor(1,.68,.15));
        Fired.Kind=ESoraShotKind::Hitscan; Fired.Origin=Start; Fired.End=Hit.bBlockingHit?FVector(Hit.ImpactPoint):End;
        if(auto* Events=USoraGameEvents::Get(this)) Events->OnWeaponFired.Broadcast(Fired);
        if(Hit.GetActor())
        {
            SoraDamage::Strike(Hit.GetActor(),W.Damage,FSoraHit::Ranged(Start,H->WeaponId),Dir,Hit,H->GetController(),H);
            if(auto* Victim=Cast<ASoraCharacterBase>(Hit.GetActor())) if(Victim->IsEnemy()) H->HitMarkerTime=.14f;
        }
        if(W.Kind==TEXT("healing")) H->Heal(5.f);
    }
    H->AddControllerPitchInput(-.3f);
}
void USoraEquipmentComponent::Melee()
{
    ASoraPlayerCharacter* H=Hero();
    if(!H->CanPlay()||GetWorld()->GetTimeSeconds()<NextShot||bReloading||bCommittedStrike||bBowDrawing||IsStaggered()||bSheathed||
        (bGuardHeld&&!H->IsDojoTraining())) return;
    const int32 MeleeId=FSoraCatalog::Get().Weapon(H->WeaponId).Kind==TEXT("melee")?H->WeaponId:FSoraCatalog::Get().Class(H->ClassId).Weapons[0];
    const auto& W=FSoraCatalog::Get().Weapon(MeleeId);
    const UCameraComponent* Camera=H->GetCamera();
    USoraGameEvents* Events=USoraGameEvents::Get(this);
    // Every melee arm strikes with commitment: a windup along a fixed line, one
    // contact, then recovery. Only the dojo bokken's lesson swing is swept.
    if(!H->IsDojoTraining()&&SoraHistoricalArms::IsMelee(MeleeId))
    {
        const auto Profile=SoraHistoricalArms::Profile(SoraHistoricalArms::FormFor(MeleeId));
        const float Now=GetWorld()->GetTimeSeconds();
        bCommittedStrike=true; bHistoricalRecovery=true; H->StopSprint();
        CommittedWeaponId=MeleeId; CommittedDirection=Camera->GetForwardVector();
        CommittedStrikeAt=Now+Profile.WindupSeconds;
        NextShot=CommittedStrikeAt+Profile.RecoverySeconds;
        if(Events)
        {
            FSoraMeleeCommittedEvent Committed;
            Committed.Attacker=H; Committed.WeaponId=MeleeId; Committed.Direction=CommittedDirection; Committed.WindupSeconds=Profile.WindupSeconds;
            Events->OnMeleeCommitted.Broadcast(Committed);
        }
        return;
    }
    NextShot=GetWorld()->GetTimeSeconds()+W.Cooldown;
    if(H->IsDojoTraining()) H->NoteDojoSwing(GetWorld()->GetTimeSeconds(),NextShot,W.Cooldown);
    const FVector Start=Camera->GetComponentLocation(); const FVector Dir=Camera->GetForwardVector();
    if(Events)
    {
        FSoraMeleeCommittedEvent Committed;
        Committed.Attacker=H; Committed.WeaponId=MeleeId; Committed.Direction=Dir;
        Events->OnMeleeCommitted.Broadcast(Committed);
    }
    FCollisionQueryParams Params(SCENE_QUERY_STAT(Melee),false,H); TArray<FHitResult> Hits;
    GetWorld()->SweepMultiByChannel(Hits,Start,Start+Dir*W.Range,FQuat::Identity,ECC_Pawn,FCollisionShape::MakeSphere(45),Params);
    TSet<AActor*> Damaged;
    bool bStruck=false;
    for(const auto& Hit:Hits) if(Hit.GetActor()&&!Damaged.Contains(Hit.GetActor()))
    {
        FHitResult Block; GetWorld()->LineTraceSingleByChannel(Block,Start,Hit.ImpactPoint,ECC_Visibility,Params);
        if(Block.GetActor()&&Block.GetActor()!=Hit.GetActor()) continue;
        Damaged.Add(Hit.GetActor());
        const float Applied=SoraDamage::Strike(Hit.GetActor(),W.Damage,FSoraHit::Melee(Start,MeleeId),Dir,Hit,H->GetController(),H);
        if(Applied>0&&Cast<ASoraCharacterBase>(Hit.GetActor())) H->HitMarkerTime=.18f;
        if(Events&&Cast<ASoraCharacterBase>(Hit.GetActor()))
        {
            FSoraStrikeResolvedEvent Resolved;
            Resolved.Attacker=H; Resolved.Target=Hit.GetActor(); Resolved.WeaponId=MeleeId; Resolved.Damage=Applied; Resolved.bHit=Applied>0;
            Events->OnStrikeResolved.Broadcast(Resolved);
            bStruck=true;
        }
    }
    if(Events&&!bStruck)
    {
        FSoraStrikeResolvedEvent Resolved;
        Resolved.Attacker=H; Resolved.WeaponId=MeleeId;
        Events->OnStrikeResolved.Broadcast(Resolved);
    }
    SoraDamage::Beam(GetWorld(),Start+Dir*50-Camera->GetRightVector()*40,Start+Dir*125+Camera->GetRightVector()*55,FLinearColor(.55,.9,1),2.5,.12);
}
void USoraEquipmentComponent::ResolveCommittedStrike()
{
    ASoraPlayerCharacter* H=Hero();
    bCommittedStrike=false;
    if(!H->CanPlay()||CommittedWeaponId==INDEX_NONE) return;
    const int32 StrikeWeapon=CommittedWeaponId;
    CommittedWeaponId=INDEX_NONE;
    const auto Form=SoraHistoricalArms::FormFor(StrikeWeapon);
    const auto Profile=SoraHistoricalArms::Profile(Form);
    const UCameraComponent* Camera=H->GetCamera();
    USoraGameEvents* Events=USoraGameEvents::Get(this);
    FSoraStrikeResolvedEvent Resolved;
    Resolved.Attacker=H; Resolved.WeaponId=StrikeWeapon;
    // The attack direction is fixed at commitment. A turn cannot turn a
    // threatened cut into an instantaneous hit behind the defender.
    if(FVector::DotProduct(Camera->GetForwardVector(),CommittedDirection)<.70f)
    {
        if(Events) Events->OnStrikeResolved.Broadcast(Resolved);
        return;
    }
    const FVector Start=Camera->GetComponentLocation();
    const FVector End=Start+CommittedDirection*Profile.MaximumDistanceCm;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(HistoricalMelee),false,H);
    TArray<FHitResult> Hits;
    GetWorld()->SweepMultiByChannel(Hits,Start,End,FQuat::Identity,ECC_Pawn,
        FCollisionShape::MakeSphere(StrikeWeapon==19?16.f:36.f),Params);
    AActor* TargetActor=nullptr;
    FHitResult TargetHit;
    float BestDistance=MAX_flt;
    for(const FHitResult& Hit:Hits)
    {
        AActor* Candidate=Hit.GetActor();
        if(!Candidate||Candidate==H) continue;
        const FVector Delta=Candidate->GetActorLocation()-H->GetActorLocation();
        const float Distance=Delta.Size2D();
        const float Facing=FVector::DotProduct(CommittedDirection.GetSafeNormal2D(),Delta.GetSafeNormal2D());
        if(!SoraHistoricalArms::CanStrike(Form,Distance,Facing)||Distance>=BestDistance) continue;
        FHitResult Visibility;
        GetWorld()->LineTraceSingleByChannel(Visibility,Start,Hit.ImpactPoint,ECC_Visibility,Params);
        if(Visibility.bBlockingHit&&Visibility.GetActor()!=Candidate) continue;
        BestDistance=Distance; TargetActor=Candidate; TargetHit=Hit;
    }
    // One intentional contact, followed by recovery, instead of a full-body
    // multi-hit spin. Yari remains a narrow thrust; naginata has a wider cut.
    if(TargetActor)
    {
        FSoraHit Strike=FSoraHit::Melee(Start,StrikeWeapon);
        Strike.StaggerMs=Profile.StaggerMs;
        const float Applied=SoraDamage::Strike(TargetActor,
            FSoraCatalog::Get().Weapon(StrikeWeapon).Damage,Strike,CommittedDirection,TargetHit,
            H->GetController(),H);
        if(Applied>0&&Cast<ASoraCharacterBase>(TargetActor)) H->HitMarkerTime=.18f;
        Resolved.Target=TargetActor; Resolved.Damage=Applied; Resolved.bHit=Applied>0&&Cast<ASoraCharacterBase>(TargetActor);
    }
    if(Events) Events->OnStrikeResolved.Broadcast(Resolved);
    SoraDamage::Beam(GetWorld(),Start+CommittedDirection*40.f,End,
        StrikeWeapon==19?FLinearColor(.73f,.78f,.82f):FLinearColor(.55f,.75f,.82f),1.4f,.11f);
}
void USoraEquipmentComponent::ReleaseBow()
{
    ASoraPlayerCharacter* H=Hero();
    bBowDrawing=false;
    if(!H->CanPlay()||H->WeaponId!=18||bReloading||H->IsSprinting()||Ammo<=0||
        GetWorld()->GetTimeSeconds()-BowDrawStartedAt<.65f) return;
    const auto& W=FSoraCatalog::Get().Weapon(18);
    const FVector Direction=H->GetCamera()->GetForwardVector();
    const FVector Origin=H->GetCamera()->GetComponentLocation()+Direction*65.f;
    auto* Arrow=GetWorld()->SpawnActorDeferred<ASoraProjectile>(ASoraProjectile::StaticClass(),
        FTransform(Direction.Rotation(),Origin),H,H,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
    if(!Arrow) return;
    Arrow->bArrow=true; Arrow->Damage=W.Damage; Arrow->Velocity=Direction*W.ProjectileSpeed; Arrow->WeaponId=18;
    UGameplayStatics::FinishSpawningActor(Arrow,Arrow->GetActorTransform());
    --Ammo; NextShot=GetWorld()->GetTimeSeconds()+W.Cooldown;
    if(auto* Events=USoraGameEvents::Get(this))
    {
        FSoraWeaponFiredEvent Fired;
        Fired.Shooter=H; Fired.WeaponId=18; Fired.Kind=ESoraShotKind::Arrow; Fired.Origin=Origin; Fired.Direction=Direction; Fired.End=Origin;
        Events->OnWeaponFired.Broadcast(Fired);
    }
}
void USoraEquipmentComponent::Reload()
{
    ASoraPlayerCharacter* H=Hero();
    if(!H->CanPlay()||bReloading) return; const auto& W=FSoraCatalog::Get().Weapon(H->WeaponId);
    if(W.Kind==TEXT("melee")||Ammo>=W.Magazine) return; bReloading=true; ReloadEnd=GetWorld()->GetTimeSeconds()+W.Reload;
}
void USoraEquipmentComponent::GuardDown(bool bDojo,bool bCampaignHero)
{
    const bool bCampaignBlade=bCampaignHero&&SoraHistoricalArms::IsMelee(Hero()->WeaponId)&&
        !bCommittedStrike&&!(bHistoricalRecovery&&GetWorld()->GetTimeSeconds()<NextShot)&&!IsStaggered()&&
        GuardStamina>=SoraCombatRules::MinimumGuardStamina;
    if((bDojo||bCampaignBlade)&&!bGuardHeld)
    {
        bGuardHeld=true;
        GuardPressedTime=GetWorld()->GetTimeSeconds();
    }
}
bool USoraEquipmentComponent::EquipClassSlot(int32 Slot)
{
    ASoraPlayerCharacter* H=Hero();
    if(bReloading||bCommittedStrike||
        (bHistoricalRecovery&&GetWorld()->GetTimeSeconds()<NextShot)||
        (H->IsDojoTraining()&&Slot!=0)) return false;
    bBowDrawing=false; bFireHeld=false; bGuardHeld=false; bSheathed=false;
    AmmoByWeapon[H->WeaponId]=Ammo; H->WeaponId=FSoraCatalog::Get().Class(H->ClassId).Weapons[Slot];
    Ammo=AmmoByWeapon[H->WeaponId]; NextShot=GetWorld()->GetTimeSeconds()+.25f; H->RebuildWeapon();
    return true;
}
bool USoraEquipmentComponent::EquipCampaignWeapon(int32 NewWeaponId)
{
    ASoraPlayerCharacter* H=Hero();
    if(bReloading||bCommittedStrike||
        (bHistoricalRecovery&&GetWorld()->GetTimeSeconds()<NextShot)) return false;
    bBowDrawing=false; bFireHeld=false; bGuardHeld=false; bSheathed=false;
    AmmoByWeapon[H->WeaponId]=Ammo;
    H->WeaponId=NewWeaponId; Ammo=AmmoByWeapon[H->WeaponId];
    NextShot=GetWorld()->GetTimeSeconds()+.25f; H->RebuildWeapon();
    return true;
}
