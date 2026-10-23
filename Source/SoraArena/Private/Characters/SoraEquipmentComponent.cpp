#include "SoraEquipmentComponent.h"
#include "Combat/SoraDamage.h"
#include "SoraCampaignDirector.h"
#include "SoraBowRules.h"
#include "SoraCatalog.h"
#include "SoraCombatRules.h"
#include "SoraCompanion.h"
#include "SoraEnemy.h"
#include "SoraFieldcraft.h"
#include "SoraFieldcraftRules.h"
#include "SoraGameMode.h"
#include "SoraGameEvents.h"
#include "SoraHistoricalArms.h"
#include "SoraPlayerCharacter.h"
#include "SoraProjectile.h"
#include "Camera/CameraComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"

namespace
{
// Nyaakoto carries only the arms the campaign has unlocked (saved in schema 6);
// a locked choice is refused with a notice. The training arena lends every arm.
bool CampaignUnlocked(const ASoraPlayerCharacter& Hero,int32 WeaponId)
{
    auto* G=Cast<ASoraGameMode>(UGameplayStatics::GetGameMode(&Hero));
    if(!G||!G->bCampaign||!Hero.IsCampaignHero()||G->Campaign()->IsWeaponUnlocked(WeaponId)) return true;
    const FSoraWeapon& Weapon=FSoraCatalog::Get().Weapon(WeaponId);
    G->Notice=FString::Printf(TEXT("%sはまだ手にしていない。"),*Weapon.Name);
    G->NoticeEnglish=FString::Printf(TEXT("%s is not yet unlocked in the campaign."),*Weapon.NameEnglish);
    G->NoticeTime=4.f;
    return false;
}
USoraCampaignDirector* HeroCampaign(const ASoraPlayerCharacter& Hero)
{
    auto* G=Cast<ASoraGameMode>(UGameplayStatics::GetGameMode(&Hero));
    return G&&G->bCampaign?G->Campaign():nullptr;
}
// In the saddle a weapon acts only in its mounted arc, and under a carried
// load only if the load leaves it in hand; a refusal raises a notice.
bool ArmsReady(const ASoraPlayerCharacter& Hero,int32 WeaponId)
{
    USoraCampaignDirector* Campaign=HeroCampaign(Hero);
    return !Campaign||Campaign->ArmsReady(WeaponId,Hero.GetControlRotation().Yaw,true);
}
bool CanHold(const ASoraPlayerCharacter& Hero,int32 WeaponId)
{
    USoraCampaignDirector* Campaign=HeroCampaign(Hero);
    return !Campaign||Campaign->CanHold(WeaponId,true);
}
}

void USoraEquipmentComponent::RaiseBeatEvent(const FString& Event) const
{
    if (USoraCampaignDirector* Campaign = HeroCampaign(*Hero())) Campaign->FireDialogueTrigger(FName(*Event));
}
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
    bChainCast=false; ChainTarget.Reset();
    bSheathed=false; bStepping=false; Awased.Reset(); bZanshinDue=false; ZanshinAt=-1000.f;
}
void USoraEquipmentComponent::Hold(int32 WeaponId)
{
    bSheathed=false;
    Hero()->WeaponId=WeaponId;
    Ammo=FSoraCatalog::Get().Weapon(WeaponId).Magazine;
}
void USoraEquipmentComponent::DropStance()
{
    bGuardHeld=false; bBowDrawing=false; bCommittedStrike=false; bHistoricalRecovery=false; bChainCast=false;
}
void USoraEquipmentComponent::Halt()
{
    bBowDrawing=false; bCommittedStrike=false; bFireHeld=false; bGuardHeld=false; bStepping=false; bChainCast=false;
}
float USoraEquipmentComponent::BowDrawProgress() const
{
    return bBowDrawing&&GetWorld()?FMath::Clamp((GetWorld()->GetTimeSeconds()-BowDrawStartedAt)*1000.0/SoraBowRules::DrawMs,0.0,1.0):0.f;
}
FRotator USoraEquipmentComponent::BowAimOffset() const
{
    if(!bBowDrawing||Hero()->WeaponId!=18||!Hero()->CanPlay()) return FRotator::ZeroRotator;
    const auto Aim=SoraBowRules::AimSway(GetWorld()->GetTimeSeconds()-BowDrawStartedAt);
    return FRotator(Aim.Pitch,Aim.Yaw,0);
}
FVector USoraEquipmentComponent::BowAimDirection() const
{
    return Hero()->GetCamera()->GetComponentQuat().RotateVector(BowAimOffset().Vector());
}
float USoraEquipmentComponent::StrikeWindupProgress() const
{
    if(!bCommittedStrike||!GetWorld()||CommittedWeaponId==INDEX_NONE) return 0.f;
    const float Windup=SoraHistoricalArms::Profile(SoraHistoricalArms::FormFor(CommittedWeaponId)).WindupSeconds;
    return FMath::Clamp(1.f-(CommittedStrikeAt-GetWorld()->GetTimeSeconds())/Windup,0.f,1.f);
}
float USoraEquipmentComponent::MoveScale(bool bSprinting) const
{
    // The 転 step carries the hero itself; walking adds nothing to it. A
    // carried load slows every other pace and allows no sprint.
    if(bStepping) return 0.f;
    const USoraCampaignDirector* Campaign=HeroCampaign(*Hero());
    const float Load=Campaign?Campaign->CarryPace():1.f;
    return (bCommittedStrike?.35f:bHistoricalRecovery?.65f:bBowDrawing?.55f:bGuardHeld?.50f:bSprinting&&Load>=1.f?1.35f:1.f)*Load;
}
void USoraEquipmentComponent::Stagger(float Seconds)
{
    if(auto* Campaign=HeroCampaign(*Hero())) Campaign->StopPlayerCrank();
    const float Until=GetWorld()->GetTimeSeconds()+Seconds;
    StaggeredUntil=FMath::Max(StaggeredUntil,Until);
    bGuardHeld=false; bBowDrawing=false; bFireHeld=false;
    bCommittedStrike=false; CommittedWeaponId=INDEX_NONE; bChainCast=false;
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
void USoraEquipmentComponent::NoteAwase(ASoraEnemy* Opponent)
{
    Awased=Opponent; AwaseAt=GetWorld()->GetTimeSeconds();
}
ASoraEnemy* USoraEquipmentComponent::AwaseOpponent(int32& SinceMs) const
{
    SinceMs=FMath::FloorToInt32((GetWorld()->GetTimeSeconds()-AwaseAt)*1000.f);
    return Awased.Get();
}
void USoraEquipmentComponent::BeginStep(const FVector& Center,const FVector& Radius,float ArcDegrees)
{
    ASoraPlayerCharacter* H=Hero();
    bStepping=true; StepStartedAt=GetWorld()->GetTimeSeconds();
    StepCenter=Center; StepRadius=Radius; StepArc=ArcDegrees; StepTurned=0.f;
    bGuardHeld=false; bBowDrawing=false; bFireHeld=false;
    H->StopSprint();
    H->GetCharacterMovement()->StopMovementImmediately();
}
void USoraEquipmentComponent::TickStep()
{
    if(!bStepping) return;
    ASoraPlayerCharacter* H=Hero();
    // Round the opponent at the distance the step began from, turning with
    // it so the opponent stays where the hero was looking.
    const float Alpha=FMath::Clamp((GetWorld()->GetTimeSeconds()-StepStartedAt)*1000.f/SoraCombatRules::MarobashiStepMs,0.f,1.f);
    FVector Next=StepCenter+StepRadius.RotateAngleAxis(StepArc*Alpha,FVector::UpVector);
    Next.Z=H->GetActorLocation().Z;
    H->SetActorLocation(Next,true);
    const float Turn=StepArc*Alpha-StepTurned;
    StepTurned+=Turn;
    if(AController* Controller=H->GetController())
    {
        FRotator View=Controller->GetControlRotation();
        View.Yaw+=Turn;
        Controller->SetControlRotation(View);
        H->FaceRotation(View,0.f);
    }
    if(Alpha>=1.f) bStepping=false;
}
void USoraEquipmentComponent::NoteDefeat()
{
    DefeatAt=GetWorld()->GetTimeSeconds(); bZanshinDue=true;
}
bool USoraEquipmentComponent::InMaai() const
{
    const ASoraPlayerCharacter* H=Hero();
    if(!GetWorld()||!SoraHistoricalArms::IsMelee(H->WeaponId)||bSheathed||!H->CanPlay()) return false;
    const auto Profile=SoraHistoricalArms::Profile(SoraHistoricalArms::FormFor(H->WeaponId));
    const FVector Forward=H->GetCamera()->GetForwardVector().GetSafeNormal2D();
    // The opponent the blade points at: the nearest one inside its facing.
    float Nearest=MAX_flt;
    for(TActorIterator<ASoraEnemy> It(GetWorld());It;++It)
    {
        if(!It->IsEnemy()||!It->IsAlive()) continue;
        const FVector Delta=It->GetActorLocation()-H->GetActorLocation();
        if(FVector::DotProduct(Forward,Delta.GetSafeNormal2D())<Profile.MinimumFacingDot) continue;
        Nearest=FMath::Min(Nearest,static_cast<float>(Delta.Size2D()));
    }
    return Nearest<MAX_flt&&SoraCombatRules::InMaai(FMath::RoundToInt32(Nearest),FMath::RoundToInt32(Profile.MaximumDistanceCm));
}
void USoraEquipmentComponent::TickGuard(float Dt)
{
    // 残心: after a defeat the held guard costs nothing until the half
    // second completes, then gives back its share.
    const float Now=GetWorld()->GetTimeSeconds();
    const bool bLingering=bZanshinDue&&bGuardHeld;
    GuardStamina=FMath::Clamp(GuardStamina+(bLingering?0.f:bGuardHeld?-28.f:21.f)*Dt,0.f,100.f);
    if(bZanshinDue)
    {
        const int32 SinceMs=FMath::FloorToInt32((Now-DefeatAt)*1000.f);
        const int32 HeldMs=bGuardHeld?FMath::FloorToInt32((Now-FMath::Max(DefeatAt,GuardPressedTime))*1000.f):-1;
        if(SoraCombatRules::Zanshin(SinceMs,HeldMs))
        {
            GuardStamina=FMath::Min(100.f,GuardStamina+SoraCombatRules::ZanshinStamina);
            bZanshinDue=false; ZanshinAt=Now;
        }
        else if(SinceMs>SoraCombatRules::ZanshinWindowMs) bZanshinDue=false;
    }
    if(GuardStamina<SoraCombatRules::MinimumGuardStamina) bGuardHeld=false;
}
void USoraEquipmentComponent::TickWeapon()
{
    TickStep();
    const float Now=GetWorld()->GetTimeSeconds();
    if(bCommittedStrike&&Now>=CommittedStrikeAt) { if(bChainCast) ResolveChain(); else ResolveCommittedStrike(); }
    // 会: the yumi at full draw.
    if(bBowDrawing&&!bDrawCompleteRaised&&BowDrawProgress()>=1.f) { bDrawCompleteRaised=true; RaiseBeatEvent(TEXT("draw_complete")); }
    if(bHistoricalRecovery&&Now>=NextShot) bHistoricalRecovery=false;
    if(bReloading&&Now>=ReloadEnd) { Ammo=FSoraCatalog::Get().Weapon(Hero()->WeaponId).Magazine; bReloading=false; }
    if(bFireHeld) Fire();
}
void USoraEquipmentComponent::TriggerDown()
{
    ASoraPlayerCharacter* H=Hero();
    const int32 WeaponId=H->WeaponId;
    const auto& W=FSoraCatalog::Get().Weapon(WeaponId);
    if(IsStaggered()||bStepping) return;
    // 抜刀: a sheathed hand's first press draws the blade and strikes nothing.
    if(bSheathed) { Sheathe(false); return; }
    if(!ArmsReady(*H,WeaponId)) return;
    if(W.Kind==TEXT("bow"))
    {
        if(const auto* Campaign=HeroCampaign(*H); Campaign&&!Campaign->CanLooseArcheryArrow()) return;
        if(!bBowDrawing&&!bReloading&&!H->IsSprinting()&&Ammo>0&&GetWorld()->GetTimeSeconds()>=NextShot)
        { bBowDrawing=true; bDrawCompleteRaised=false; BowDrawStartedAt=GetWorld()->GetTimeSeconds(); }
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
    RaiseBeatEvent(FString::Printf(TEXT("fired:%d"),H->WeaponId));
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
        // The healing lance's round raises a downed companion (ch08.b07).
        if(W.Kind==TEXT("healing")&&Cast<ASoraCompanion>(Hit.GetActor()))
            if(USoraFieldcraft* Fieldcraft=USoraFieldcraft::Get(this)) Fieldcraft->LanceHit(Hit.GetActor());
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
    if(H->CanPlay()&&bSheathed&&!IsStaggered()) { Sheathe(false); return; }
    if(!H->CanPlay()||GetWorld()->GetTimeSeconds()<NextShot||bReloading||bCommittedStrike||bBowDrawing||IsStaggered()||bSheathed||
        bStepping||(bGuardHeld&&!H->IsDojoTraining())) return;
    const int32 MeleeId=FSoraCatalog::Get().Weapon(H->WeaponId).Kind==TEXT("melee")?H->WeaponId:FSoraCatalog::Get().Class(H->ClassId).Weapons[0];
    if(!ArmsReady(*H,MeleeId)) return;
    const auto& W=FSoraCatalog::Get().Weapon(MeleeId);
    const UCameraComponent* Camera=H->GetCamera();
    USoraGameEvents* Events=USoraGameEvents::Get(this);
    // Every melee arm strikes with commitment: a windup along a fixed line, one
    // contact, then recovery. Only the dojo bokken's lesson swing is swept.
    // The kusarigama casts its weight at an opponent beyond the sickle's reach.
    if(!H->IsDojoTraining()&&MeleeId==2)
        if(ASoraEnemy* Quarry=ChainQuarry())
        {
            const float Now=GetWorld()->GetTimeSeconds();
            bCommittedStrike=true; bChainCast=true; bHistoricalRecovery=true; H->StopSprint();
            CommittedWeaponId=MeleeId; CommittedDirection=Camera->GetForwardVector(); ChainTarget=Quarry;
            CommittedStrikeAt=Now+SoraFieldcraftRules::ChainWindupMs/1000.f;
            NextShot=CommittedStrikeAt+SoraFieldcraftRules::ChainRecoveryMs/1000.f;
            ++ChainCasts;
            if(Events)
            {
                FSoraMeleeCommittedEvent Committed;
                Committed.Attacker=H; Committed.WeaponId=MeleeId; Committed.Direction=CommittedDirection;
                Committed.WindupSeconds=SoraFieldcraftRules::ChainWindupMs/1000.f;
                Events->OnMeleeCommitted.Broadcast(Committed);
            }
            return;
        }
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
ASoraEnemy* USoraEquipmentComponent::ChainQuarry() const
{
    const ASoraPlayerCharacter* H=Hero();
    const FVector Eye=H->GetCamera()->GetComponentLocation();
    const FVector Forward=H->GetCamera()->GetForwardVector().GetSafeNormal2D();
    const int32 Sickle=FMath::RoundToInt32(SoraHistoricalArms::Profile(SoraHistoricalArms::EForm::Kusarigama).MaximumDistanceCm);
    ASoraEnemy* Best=nullptr;
    float BestDistance=SoraFieldcraftRules::ChainReachCm+1.f;
    for(TActorIterator<ASoraEnemy> It(GetWorld());It;++It)
    {
        if(!It->IsEnemy()||!It->IsAlive()||It->IsSubdued()) continue;
        const FVector Delta=It->GetActorLocation()-H->GetActorLocation();
        const float Distance=Delta.Size2D();
        if(Distance>=BestDistance||FVector::DotProduct(Forward,Delta.GetSafeNormal2D())<.85f||
            SoraFieldcraftRules::Snare(FMath::RoundToInt32(Distance),Sickle,It->IsFlying(),It->HasShield())==SoraFieldcraftRules::ESnare::None)
            continue;
        FHitResult Line; FCollisionQueryParams Query(SCENE_QUERY_STAT(SoraChain),false,H);
        GetWorld()->LineTraceSingleByChannel(Line,Eye,It->GetActorLocation(),ECC_Visibility,Query);
        if(Line.bBlockingHit&&Line.GetActor()!=*It) continue;
        Best=*It; BestDistance=Distance;
    }
    return Best;
}
void USoraEquipmentComponent::ResolveChain()
{
    ASoraPlayerCharacter* H=Hero();
    bCommittedStrike=false; bChainCast=false; CommittedWeaponId=INDEX_NONE;
    ASoraEnemy* Target=ChainTarget.Get();
    ChainTarget.Reset();
    if(!H->CanPlay()||!Target||!Target->IsAlive()) return;
    const FVector Start=H->GetCamera()->GetComponentLocation();
    const FVector Delta=Target->GetActorLocation()-H->GetActorLocation();
    const int32 Sickle=FMath::RoundToInt32(SoraHistoricalArms::Profile(SoraHistoricalArms::EForm::Kusarigama).MaximumDistanceCm);
    // The weight flies along the line it was cast on; a target that left it goes free.
    const SoraFieldcraftRules::ESnare Snare=FVector::DotProduct(CommittedDirection.GetSafeNormal2D(),Delta.GetSafeNormal2D())<.7f
        ?SoraFieldcraftRules::ESnare::None
        :SoraFieldcraftRules::Snare(FMath::RoundToInt32(Delta.Size2D()),Sickle,Target->IsFlying(),Target->HasShield());
    SoraDamage::Beam(GetWorld(),Start+CommittedDirection*40.f,Target->GetActorLocation(),FLinearColor(.5f,.52f,.55f),1.2f,.2f);
    if(Snare==SoraFieldcraftRules::ESnare::None) return;
    Target->Snared(Snare,H);
    ++ChainHits;
    RaiseBeatEvent(Snare==SoraFieldcraftRules::ESnare::Drone?TEXT("snare:drone"):Snare==SoraFieldcraftRules::ESnare::Shield
        ?TEXT("snare:shield"):TEXT("snare:blade"));
}
void USoraEquipmentComponent::ReleaseBow()
{
    ASoraPlayerCharacter* H=Hero();
    // Sample the visible aim before ending this draw, including releases
    // between world ticks. Ending it first would silently recenter the shot.
    const FVector Direction=BowAimDirection();
    bBowDrawing=false;
    if(!H->CanPlay()||H->WeaponId!=18||bReloading||H->IsSprinting()||Ammo<=0||
        GetWorld()->GetTimeSeconds()-BowDrawStartedAt<SoraBowRules::DrawMs/1000.0||!ArmsReady(*H,18)) return;
    auto* Campaign=HeroCampaign(*H);
    if(Campaign&&!Campaign->CanLooseArcheryArrow()) return;
    const auto& W=FSoraCatalog::Get().Weapon(18);
    const FVector Origin=H->GetCamera()->GetComponentLocation()+Direction*65.f;
    auto* Arrow=GetWorld()->SpawnActorDeferred<ASoraProjectile>(ASoraProjectile::StaticClass(),
        FTransform(Direction.Rotation(),Origin),H,H,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
    if(!Arrow) return;
    Arrow->bArrow=true; Arrow->Damage=W.Damage; Arrow->Velocity=Direction*W.ProjectileSpeed; Arrow->WeaponId=18;
    if(Campaign)
    {
        // Both the range lesson and the optional wood challenge observe the
        // actual released projectile. Only the lesson requires a range-shot ID.
        Arrow->ArcheryShotId=Campaign->RegisterArcheryArrow(*Arrow);
        if(Campaign->IsArcheryLesson()&&!Arrow->ArcheryShotId) { Arrow->Destroy(); return; }
    }
    UGameplayStatics::FinishSpawningActor(Arrow,Arrow->GetActorTransform());
    --Ammo; NextShot=GetWorld()->GetTimeSeconds()+W.Cooldown;
    // The loose, and a quiver running low (ch02.b08's event:arrows_below:4).
    RaiseBeatEvent(TEXT("release")); RaiseBeatEvent(TEXT("fired:18"));
    RaiseBeatEvent(FString::Printf(TEXT("event:arrows_below:%d"),Ammo+1));
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
    if(auto* Campaign=HeroCampaign(*H)) Campaign->StopPlayerCrank();
    if(!H->CanPlay()||bReloading) return; const auto& W=FSoraCatalog::Get().Weapon(H->WeaponId);
    if(H->WeaponId==18) if(auto* Campaign=HeroCampaign(*H); Campaign&&Campaign->UsesDojoQuiver())
    {
        Campaign->ExplainDojoQuiver(); return;
    }
    if(W.Kind==TEXT("melee")||Ammo>=W.Magazine) return; bReloading=true; ReloadEnd=GetWorld()->GetTimeSeconds()+W.Reload;
}
void USoraEquipmentComponent::GuardDown(bool bDojo,bool bCampaignHero)
{
    if(auto* Campaign=HeroCampaign(*Hero()); Campaign&&Campaign->CrankOccupiesHands()) return;
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
        (H->IsDojoTraining()&&Slot!=0)||
        !CampaignUnlocked(*H,FSoraCatalog::Get().Class(H->ClassId).Weapons[Slot])||
        !CanHold(*H,FSoraCatalog::Get().Class(H->ClassId).Weapons[Slot])) return false;
    bBowDrawing=false; bFireHeld=false; bGuardHeld=false; bSheathed=false;
    AmmoByWeapon[H->WeaponId]=Ammo; H->WeaponId=FSoraCatalog::Get().Class(H->ClassId).Weapons[Slot];
    Ammo=AmmoByWeapon[H->WeaponId]; NextShot=GetWorld()->GetTimeSeconds()+.25f; H->RebuildWeapon();
    RaiseBeatEvent(FString::Printf(TEXT("equip:%d"),H->WeaponId));
    return true;
}
bool USoraEquipmentComponent::EquipCampaignWeapon(int32 NewWeaponId)
{
    ASoraPlayerCharacter* H=Hero();
    if(bReloading||bCommittedStrike||
        (bHistoricalRecovery&&GetWorld()->GetTimeSeconds()<NextShot)||
        !CampaignUnlocked(*H,NewWeaponId)||!CanHold(*H,NewWeaponId)) return false;
    bBowDrawing=false; bFireHeld=false; bGuardHeld=false; bSheathed=false;
    AmmoByWeapon[H->WeaponId]=Ammo;
    H->WeaponId=NewWeaponId; Ammo=AmmoByWeapon[H->WeaponId];
    NextShot=GetWorld()->GetTimeSeconds()+.25f; H->RebuildWeapon();
    RaiseBeatEvent(FString::Printf(TEXT("equip:%d"),NewWeaponId));
    return true;
}
