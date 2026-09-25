#include "SoraEnemy.h"
#include "SoraBoss.h"
#include "Combat/SoraCombatEffects.h"
#include "Combat/SoraDamage.h"
#include "Combat/SoraEnemyCatalog.h"
#include "Combat/SoraStealth.h"
#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraEnemyController.h"
#include "SoraGameEvents.h"
#include "SoraGameMode.h"
#include "SoraProjectile.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"

namespace Rules = SoraCombatRules;

namespace SoraEnemyBody
{
// Attacks leave from this height above the capsule's centre, scaled with the
// body, and strike the hero at his chest.
constexpr float EyeHeight = 50.f;
constexpr float ChestHeight = 35.f;
// A lobbed shell falls at full gravity so its arc reads against the sky.
constexpr float ShellGravity = 980.f;
// A squad's bursts are offset by slot so it never fires in unison.
constexpr float SlotRecoverySeconds = .2f;
const FLinearColor Amber(1.f, .68f, .16f);
const FLinearColor Cyan(.04f, .85f, .95f);

// The catalog weapon each body carries until its own kit exists: a visual only.
int32 HeldWeapon(ESoraEnemyBehavior Behavior)
{
    switch (Behavior)
    {
    case ESoraEnemyBehavior::Blade: return 0;
    case ESoraEnemyBehavior::Rifle: return 1;
    case ESoraEnemyBehavior::Shield: return 6;
    case ESoraEnemyBehavior::Grenadier: return 7;
    case ESoraEnemyBehavior::Marksman: return 14;
    case ESoraEnemyBehavior::Drone: return 16;
    case ESoraEnemyBehavior::Conscript: return 19;
    case ESoraEnemyBehavior::Auditor: return 17;
    case ESoraEnemyBehavior::Automaton: return 8;
    case ESoraEnemyBehavior::Walker: return 16;
    }
    return 1;
}

int32 HalfArcMilli(int32 Degrees)
{
    return FMath::RoundToInt32(FMath::Cos(FMath::DegreesToRadians(Degrees * .5)) * 1000.0);
}

int32 Milliseconds(float Seconds)
{
    return FMath::FloorToInt32(Seconds * 1000.f);
}
}

ASoraEnemy::ASoraEnemy(const FObjectInitializer& ObjectInitializer)
    : Super(ObjectInitializer)
{
    // Each opponent spawns with its own AI controller, which drives it.
    AIControllerClass=ASoraEnemyController::StaticClass();
    AutoPossessAI=EAutoPossessAI::PlacedInWorldOrSpawned;
    bUseControllerRotationYaw=false;
    GetCharacterMovement()->bOrientRotationToMovement=false;
}
float ASoraEnemy::Now() const { return GetWorld()->GetTimeSeconds(); }
FVector ASoraEnemy::Eye() const { return GetActorLocation()+FVector(0.f,0.f,SoraEnemyBody::EyeHeight*GetActorScale3D().Z); }
FVector ASoraEnemy::Feet(const ASoraCharacterBase& Body) const
{
    return Body.GetActorLocation()-FVector(0.f,0.f,Body.GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
}
FName ASoraEnemy::WaveArchetype(int32 Slot)
{
    return Slot%6==0?FName(TEXT("blade_retainer")):FName(TEXT("enforcer_rifle"));
}
bool ASoraEnemy::InitArchetype(FName ArchetypeName,int32 Slot,const FSoraPatrolRoute* Patrol,const FSoraEnemyTuning* Tuning)
{
    FSoraEnemyCatalog& Catalog=FSoraEnemyCatalog::Get();
    const FSoraEnemyArchetype* Found=Catalog.Load()?Catalog.Find(ArchetypeName):nullptr;
    const FName VariantName=Tuning?Tuning->Variant:NAME_None;
    const FSoraEnemyVariant* Chosen=Found&&!VariantName.IsNone()?Found->Variant(VariantName):nullptr;
    if(!Found||(!VariantName.IsNone()&&!Chosen))
    {
        UE_LOG(LogTemp,Error,TEXT("No opponent archetype %s (variant %s): %s"),*ArchetypeName.ToString(),*VariantName.ToString(),
            Catalog.IsReady()?TEXT("not in Content/Data/enemies.json"):*Catalog.Error);
        return false;
    }
    Kind=Found; Variant=VariantName; VariantData=Chosen;
    bDojoPupil=false; EnemyIndex=Slot; RangedShots=0; ShotsSinceRelocation=0;
    // Perception: the archetype's, then its variant's, then the beat's.
    Senses=Kind->Perception;
    if(Chosen&&Chosen->SightCm>0)
    {
        Senses.SightRangeCm=Chosen->SightCm; Senses.DarkSightRangeCm=Chosen->DarkSightCm;
        Senses.ViewConeMilli=SoraEnemyBody::HalfArcMilli(Chosen->ViewDegrees);
    }
    if(Tuning)
    {
        if(Tuning->SightCm>0) Senses.SightRangeCm=Tuning->SightCm;
        if(Tuning->DarkSightCm>=0) Senses.DarkSightRangeCm=Tuning->DarkSightCm;
        if(Tuning->ViewDegrees>0) Senses.ViewConeMilli=SoraEnemyBody::HalfArcMilli(Tuning->ViewDegrees);
        if(Tuning->HearingCm>=0) Senses.HearingCm=Tuning->HearingCm;
    }
    Senses.DarkSightRangeCm=FMath::Min(Senses.DarkSightRangeCm,Senses.SightRangeCm);
    Senses.FocusConeMilli=FMath::Max(Senses.ViewConeMilli,SoraStealthRules::FocusConeMilli);
    bInvulnerable=Tuning&&Tuning->bInvulnerable;
    MaxHealth=Tuning&&Tuning->Health>0?Tuning->Health:Chosen&&Chosen->Health>0?Chosen->Health:Kind->Health;
    Health=MaxHealth;
    BarrierMaxMilli=Chosen?Chosen->Barrier.Health*1000:0;
    BarrierMilli=BarrierMaxMilli; BarrierAtLastHitMilli=BarrierMaxMilli; LastHitAt=-1000.f;
    Phase=EPhase::Idle; AttackIndex=INDEX_NONE; AttackTarget=nullptr; NextAttackAt=0.f;
    AttackReadyAt.Init(0.f,Kind->Attacks.Num());
    StaggerUntil=-1.f; StrikeStaggerImmuneUntil=-1.f; ShieldOpenUntil=-1.f;
    Conscript=Rules::EConscript::Standing; bUnconscious=false; bSeized=false;
    SetActorScale3D(FVector(Kind->ScalePermille/1000.f));
    UCharacterMovementComponent* Movement=GetCharacterMovement();
    Movement->MaxWalkSpeed=Kind->SpeedCmPerSecond; Movement->MaxFlySpeed=Kind->SpeedCmPerSecond;
    Movement->SetMovementMode(IsFlying()?MOVE_Flying:MOVE_Walking);
    WeaponId=SoraEnemyBody::HeldWeapon(Kind->Behavior); RebuildWeapon();
    BuildCat();
    if(auto* Brain=Cast<ASoraEnemyController>(GetController()))
    {
        if(Patrol) Brain->BeginPatrol(*Patrol);
        else Brain->BeginHunt();
    }
    return true;
}
ASoraEnemy* ASoraEnemy::SpawnArchetype(UWorld& World,FName ArchetypeName,int32 Slot,const FVector& Location,const FRotator& Rotation,
    const FSoraPatrolRoute* Patrol,const FSoraEnemyTuning* Tuning)
{
    FActorSpawnParameters Params; Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButAlwaysSpawn;
    ASoraEnemy* Enemy=World.SpawnActor<ASoraEnemy>(Location,Rotation,Params);
    if(Enemy&&!Enemy->InitArchetype(ArchetypeName,Slot,Patrol,Tuning))
    {
        Enemy->Destroy();
        return nullptr;
    }
    return Enemy;
}
void ASoraEnemy::InitInvader(int32 Id,const FSoraPatrolRoute* Patrol)
{
    if(!InitArchetype(WaveArchetype(Id),Id,Patrol)) Destroy();
}
ASoraEnemy* ASoraEnemy::SpawnInvader(UWorld& World,int32 Id,const FVector& Location,const FRotator& Rotation,const FSoraPatrolRoute* Patrol)
{
    return SpawnArchetype(World,WaveArchetype(Id),Id,Location,Rotation,Patrol);
}
void ASoraEnemy::InitScripted(int32 Id)
{
    Kind=nullptr; Variant=NAME_None; VariantData=nullptr;
    bDojoPupil=false; EnemyIndex=Id; RangedShots=0;
    Phase=EPhase::Idle; AttackIndex=INDEX_NONE; StaggerUntil=-1.f; StrikeStaggerImmuneUntil=-1.f;
    BarrierMilli=0; BarrierMaxMilli=0;
    ApplyClass(Id%6);
    BuildCat();
}
void ASoraEnemy::InitDojoPupil(int32 Id)
{
    Kind=nullptr; Variant=NAME_None; VariantData=nullptr;
    bDojoPupil=true; EnemyIndex=Id;
    StaggerUntil=-1.f; StrikeStaggerImmuneUntil=-1.f; BarrierMilli=0; BarrierMaxMilli=0;
    bPupilWindup=false; NextPupilStrike=Now()+1.4f+Id*.35f;
    ApplyClass(0);
    WeaponId=FSoraCatalog::Get().Class(0).Weapons[0]; RebuildWeapon();
    BuildCat();
}
void ASoraEnemy::SuspendDojoAction()
{
    if(bDojoPupil)
    {
        bPupilWindup=false;
        NextPupilStrike=Now()+.8f;
    }
}
FName ASoraEnemy::ArchetypeId() const { return Kind?Kind->Id:NAME_None; }
void ASoraEnemy::SetSummoner(ASoraBoss* Boss) { SummonedBy=Boss; }
ASoraBoss* ASoraEnemy::Summoner() const { return SummonedBy.Get(); }
bool ASoraEnemy::IsBladeRetainer() const { return Kind&&Kind->Behavior==ESoraEnemyBehavior::Blade; }
bool ASoraEnemy::IsFlying() const { return Kind&&Kind->Behavior==ESoraEnemyBehavior::Drone; }
bool ASoraEnemy::IsNonlethal() const { return Kind&&!Kind->bLethal; }
bool ASoraEnemy::UsesAlienBody() const { return Kind?Kind->Body!=ESoraEnemyBody::Local:!bDojoPupil; }
bool ASoraEnemy::RangedShotMisses(int32 Slot,int32 Shot) { return Rules::RoundMisses(Slot,Shot); }
int32 ASoraEnemy::AttackDamage(int32 Index) const { return Kind&&Kind->Attacks.IsValidIndex(Index)?Kind->Attacks[Index].Damage:0; }
int32 ASoraEnemy::SealCutHoldMs() const { return Kind?Kind->SealCutHoldMs:0; }
bool ASoraEnemy::IsBody() const { return Kind&&!IsAlive()&&!IsFreed()&&!IsActorBeingDestroyed(); }
bool ASoraEnemy::CanBeTakenDown() const
{
    return Kind&&Kind->bRearTakedown&&IsAlive()&&!bInvulnerable&&!IsFreed()&&!bSeized&&!bKernelDriven;
}
bool ASoraEnemy::IsStaggered() const { return GetWorld()&&Now()<StaggerUntil; }
bool ASoraEnemy::IsShieldOpen() const { return Kind&&Kind->bShield&&(Now()<ShieldOpenUntil||IsStaggered()); }
const FSoraEnemyAttack* ASoraEnemy::CurrentAttack() const
{
    return Kind&&Phase!=EPhase::Idle&&Kind->Attacks.IsValidIndex(AttackIndex)?&Kind->Attacks[AttackIndex]:nullptr;
}
float ASoraEnemy::WindupProgress() const
{
    if(Phase!=EPhase::Windup||PhaseEndsAt<=PhaseStartedAt) return 0.f;
    return FMath::Clamp((Now()-PhaseStartedAt)/(PhaseEndsAt-PhaseStartedAt),0.f,1.f);
}
float ASoraEnemy::MeleeReachCm() const
{
    float Reach=0.f;
    if(Kind) for(const FSoraEnemyAttack& Attack:Kind->Attacks)
        if(Attack.Kind==ESoraEnemyAttackKind::Melee) Reach=FMath::Max(Reach,static_cast<float>(Attack.MaxRangeCm));
    return Reach;
}
void ASoraEnemy::Announce(ESoraEnemyCue Cue,FName Detail) const
{
    if(USoraGameEvents* Events=USoraGameEvents::Get(this))
    {
        FSoraEnemyCueEvent Event;
        Event.Enemy=const_cast<ASoraEnemy*>(this); Event.Archetype=ArchetypeId(); Event.Cue=Cue; Event.Detail=Detail;
        Events->OnEnemyCue.Broadcast(Event);
    }
}
void ASoraEnemy::Tick(float Dt)
{
    Super::Tick(Dt);
    // A knocked-down conscript cannot play, so its collar's pull is timed here.
    if(IsSubdued()&&Kind&&!bKernelDriven)
    {
        const auto* Mode=Cast<ASoraGameMode>(UGameplayStatics::GetGameMode(this));
        if(Mode&&Mode->IsPlaying()&&Rules::Rises(Conscript,SoraEnemyBody::Milliseconds(Now()-DownAt),Kind->SubdueWindowMs)) Rise();
    }
}
void ASoraEnemy::TickPlay(float Dt)
{
    AdvanceAttack();
    if(BarrierMaxMilli>0&&VariantData)
    {
        const Rules::FBarrier Next=Rules::RegeneratedBarrier({BarrierAtLastHitMilli,BarrierMaxMilli},
            SoraEnemyBody::Milliseconds(Now()-LastHitAt),VariantData->Barrier.RegenDelayMs,VariantData->Barrier.RegenPerSecond);
        BarrierMilli=Next.HealthMilli;
    }
    const bool Moving=GetVelocity().Size2D()>5.f;
    UpdateLocomotion(Moving,Moving?FMath::Clamp(GetVelocity().Size2D()/180.f,.65f,2.5f):1.f);
}
void ASoraEnemy::HaltActions()
{
    CancelAttack();
}
bool ASoraEnemy::TryAttack(ASoraCharacterBase& Target,float Distance)
{
    if(!Kind||Phase!=EPhase::Idle||IsStaggered()||!Target.IsAlive()||Now()<NextAttackAt) return false;
    const int32 Facing=SoraDamage::FacingMilli(*this,Target.GetActorLocation());
    for(int32 Index=0;Index<Kind->Attacks.Num();++Index)
    {
        const FSoraEnemyAttack& Attack=Kind->Attacks[Index];
        if(Now()<AttackReadyAt[Index]||Distance<Attack.MinRangeCm||Distance>Attack.MaxRangeCm) continue;
        // A committed blow starts only toward what is inside its arc; every
        // other attack at least toward the front.
        const bool bAround=Attack.Kind==ESoraEnemyAttackKind::Melee&&Attack.ArcMilli<=-1000;
        const int32 Needed=Attack.Kind==ESoraEnemyAttackKind::Melee?FMath::Max(Attack.ArcMilli,0):0;
        if(!bAround&&Facing<Needed) continue;
        Commit(Index,Target);
        return true;
    }
    return false;
}
void ASoraEnemy::Commit(int32 Index,ASoraCharacterBase& Target)
{
    const FSoraEnemyAttack& Attack=Kind->Attacks[Index];
    const float Time=Now();
    AttackIndex=Index; AttackTarget=&Target; Phase=EPhase::Windup;
    PhaseStartedAt=Time; PhaseEndsAt=Time+Attack.WindupMs/1000.f; NextLaserAt=Time;
    LockedDirection=(Target.GetActorLocation()+FVector(0.f,0.f,SoraEnemyBody::ChestHeight)-Eye()).GetSafeNormal();
    LockedPoint=Feet(Target);
    Telegraph(Attack,Attack.WindupMs/1000.f);
    if(Attack.Kind==ESoraEnemyAttackKind::Melee) if(USoraGameEvents* Events=USoraGameEvents::Get(this))
    {
        FSoraMeleeCommittedEvent Committed;
        Committed.Attacker=this; Committed.WeaponId=WeaponId; Committed.Direction=LockedDirection;
        Committed.WindupSeconds=Attack.WindupMs/1000.f;
        Events->OnMeleeCommitted.Broadcast(Committed);
    }
    Announce(ESoraEnemyCue::AttackWindup,Attack.Cue);
}
void ASoraEnemy::Telegraph(const FSoraEnemyAttack& Attack,float Life)
{
    UWorld* World=GetWorld();
    const FVector From=Eye();
    const FVector Ground=Feet(*this)+FVector(0.f,0.f,3.f);
    const FVector Flat=LockedDirection.GetSafeNormal2D();
    switch(Attack.Kind)
    {
    case ESoraEnemyAttackKind::Melee:
        if(Attack.ArcMilli<=-1000) SoraDamage::Ring(World,Ground,Attack.MaxRangeCm,SoraEnemyBody::Amber,Life);
        else SoraDamage::Beam(World,From,From+LockedDirection*Attack.MaxRangeCm,SoraEnemyBody::Amber,2.f,Life);
        return;
    case ESoraEnemyAttackKind::Burst:
        // The raised stock: a short line along the aim.
        SoraDamage::Beam(World,From,From+LockedDirection*160.f,SoraEnemyBody::Amber,1.2f,Life);
        return;
    case ESoraEnemyAttackKind::LockShot:
        // The glint's laser tracks the target (AdvanceAttack).
        return;
    case ESoraEnemyAttackKind::Lob:
        // The launcher is raised; the landing ring shows for the whole flight.
        SoraDamage::Beam(World,From,From+FVector(0.f,0.f,120.f),SoraEnemyBody::Amber,1.5f,Life);
        return;
    case ESoraEnemyAttackKind::Beam:
        SoraDamage::Beam(World,Ground,Ground+Flat*Attack.MaxRangeCm,SoraEnemyBody::Cyan,3.f,Life);
        return;
    case ESoraEnemyAttackKind::Net:
        SoraDamage::Ring(World,LockedPoint+FVector(0.f,0.f,3.f),Attack.RadiusCm,SoraEnemyBody::Cyan,Life);
        return;
    }
}
void ASoraEnemy::AdvanceAttack()
{
    if(Phase==EPhase::Idle) return;
    if(!Kind||!Kind->Attacks.IsValidIndex(AttackIndex)) { CancelAttack(); return; }
    const FSoraEnemyAttack& Attack=Kind->Attacks[AttackIndex];
    ASoraCharacterBase* Target=AttackTarget.Get();
    const float Time=Now();
    if(Phase!=EPhase::Recovery&&(!Target||!Target->IsAlive()))
    {
        Recover(Attack);
        return;
    }
    switch(Phase)
    {
    case EPhase::Windup:
        if(Attack.Kind==ESoraEnemyAttackKind::LockShot&&Time>=NextLaserAt)
        {
            const FVector Chest=Target->GetActorLocation()+FVector(0.f,0.f,SoraEnemyBody::ChestHeight);
            LockedDirection=(Chest-Eye()).GetSafeNormal();
            SoraDamage::Beam(GetWorld(),Eye(),Chest,SoraEnemyBody::Cyan,.8f,.12f);
            NextLaserAt=Time+.1f;
        }
        if(Time>=PhaseEndsAt) Release(Attack,*Target);
        return;
    case EPhase::Firing:
        while(Phase==EPhase::Firing&&Time>=NextRoundAt)
        {
            FireRound(Attack,*Target,true);
            // A round's resolution may stagger this opponent and end the burst.
            if(Phase!=EPhase::Firing) return;
            NextRoundAt+=Attack.IntervalMs/1000.f;
            if(--RoundsLeft<=0) Recover(Attack);
        }
        return;
    case EPhase::Recovery:
        if(Time>=PhaseEndsAt) CancelAttack();
        return;
    case EPhase::Idle:
        return;
    }
}
void ASoraEnemy::Release(const FSoraEnemyAttack& Attack,ASoraCharacterBase& Target)
{
    if(Attack.Kind==ESoraEnemyAttackKind::Burst)
    {
        Phase=EPhase::Firing; RoundsLeft=Attack.Rounds; NextRoundAt=Now();
        AdvanceAttack();
        return;
    }
    // The attack is out: its recovery starts before it resolves, so a parry's
    // stagger lands on that recovery instead of cancelling a spent windup.
    Recover(Attack);
    switch(Attack.Kind)
    {
    case ESoraEnemyAttackKind::Melee: StrikeMelee(Attack,Target); return;
    case ESoraEnemyAttackKind::LockShot: FireRound(Attack,Target,false); return;
    case ESoraEnemyAttackKind::Lob: Lob(Attack,Target); return;
    case ESoraEnemyAttackKind::Beam: FireBeam(Attack,Target); return;
    case ESoraEnemyAttackKind::Net: CastNet(Attack,Target); return;
    case ESoraEnemyAttackKind::Burst: return;
    }
}
void ASoraEnemy::Recover(const FSoraEnemyAttack& Attack)
{
    const float Time=Now();
    const bool bRanged=Attack.Kind==ESoraEnemyAttackKind::Burst||Attack.Kind==ESoraEnemyAttackKind::LockShot||
        Attack.Kind==ESoraEnemyAttackKind::Lob;
    Phase=EPhase::Recovery; PhaseStartedAt=Time;
    PhaseEndsAt=Time+Attack.RecoveryMs/1000.f+(bRanged?EnemyIndex%3*SoraEnemyBody::SlotRecoverySeconds:0.f);
    NextAttackAt=PhaseEndsAt;
    AttackReadyAt[AttackIndex]=FMath::Max(PhaseEndsAt,Time+Attack.CooldownMs/1000.f);
}
void ASoraEnemy::CancelAttack()
{
    Phase=EPhase::Idle; AttackIndex=INDEX_NONE; AttackTarget=nullptr; RoundsLeft=0;
}
void ASoraEnemy::StrikeMelee(const FSoraEnemyAttack& Attack,ASoraCharacterBase& Target)
{
    const FVector From=Eye();
    const FVector Delta=Target.GetActorLocation()-GetActorLocation();
    const float Distance=Delta.Size2D();
    const bool bAround=Attack.ArcMilli<=-1000;
    const int32 Facing=FMath::RoundToInt32(FVector::DotProduct(LockedDirection.GetSafeNormal2D(),Delta.GetSafeNormal2D())*1000.f);
    FHitResult Trace;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(SoraEnemyStrike),false,this);
    GetWorld()->LineTraceSingleByChannel(Trace,From,Target.GetActorLocation()+FVector(0.f,0.f,SoraEnemyBody::ChestHeight),ECC_Visibility,Query);
    // The committed line (or ring) must still hold the target, in reach and in the open.
    const bool bReach=Distance>=Attack.MinRangeCm&&Distance<=Attack.MaxRangeCm&&(bAround||Facing>=Attack.ArcMilli)&&
        Trace.GetActor()==&Target;
    if(bAround) SoraDamage::Ring(GetWorld(),Feet(*this)+FVector(0.f,0.f,3.f),Attack.MaxRangeCm,FLinearColor(1.f,.80f,.24f),.13f);
    else SoraDamage::Beam(GetWorld(),From,From+LockedDirection*Attack.MaxRangeCm,FLinearColor(.75f,.82f,.87f),2.f,.13f);
    FSoraStrikeResolvedEvent Resolved;
    Resolved.Attacker=this; Resolved.WeaponId=WeaponId;
    if(bReach)
    {
        FSoraHit Hit=FSoraHit::Melee(From,INDEX_NONE);
        Hit.AttackId=Attack.Id; Hit.bParryable=Attack.bParryable; Hit.GuardChip=Attack.GuardChip; Hit.GuardStamina=Attack.GuardStamina;
        Hit.ParryStaggerMs=Attack.ParryStaggerMs; Hit.bBreaksGuard=Attack.bBreaksGuard;
        Hit.KnockbackCm=Attack.KnockbackCm; Hit.HeroStaggerMs=Attack.HeroStaggerMs;
        Resolved.Target=&Target;
        Resolved.Damage=SoraDamage::Strike(&Target,Attack.Damage,Hit,LockedDirection,Trace,GetController(),this);
        Resolved.bHit=Resolved.Damage>0;
    }
    if(USoraGameEvents* Events=USoraGameEvents::Get(this)) Events->OnStrikeResolved.Broadcast(Resolved);
}
void ASoraEnemy::FireRound(const FSoraEnemyAttack& Attack,ASoraCharacterBase& Target,bool bPattern)
{
    const FVector From=Eye();
    const FVector To=Target.GetActorLocation()+FVector(0.f,0.f,SoraEnemyBody::ChestHeight);
    FHitResult Trace;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(BotNavigation),false,this);
    GetWorld()->LineTraceSingleByChannel(Trace,From,To,ECC_Visibility,Query);
    // Without a clear line the round is held.
    if(Trace.GetActor()!=&Target) return;
    const bool bMiss=bPattern&&RangedShotMisses(EnemyIndex,RangedShots);
    ++RangedShots; ++ShotsSinceRelocation;
    const FVector Direction=(To-From).GetSafeNormal();
    const FVector End=To+(bMiss?FVector(0,80,60):FVector::ZeroVector);
    SoraDamage::Beam(GetWorld(),From,End,Attack.bCyanTelegraph?SoraEnemyBody::Cyan:FLinearColor(1,.12,.3),1.7f);
    if(USoraGameEvents* Events=USoraGameEvents::Get(this))
    {
        FSoraWeaponFiredEvent Fired;
        Fired.Shooter=this; Fired.WeaponId=WeaponId; Fired.Origin=From; Fired.Direction=Direction; Fired.End=End;
        Events->OnWeaponFired.Broadcast(Fired);
    }
    if(bMiss) return;
    FSoraHit Hit=FSoraHit::Ranged(From,INDEX_NONE);
    Hit.AttackId=Attack.Id;
    SoraDamage::Strike(&Target,Attack.Damage,Hit,Direction,Trace,GetController(),this);
}
void ASoraEnemy::Lob(const FSoraEnemyAttack& Attack,ASoraCharacterBase& Target)
{
    const FVector Origin=Eye()+GetActorForwardVector()*60.f*GetActorScale3D().X;
    const FVector Landing=Feet(Target);
    const float Flight=Attack.FlightMs/1000.f;
    // The launch that lands on the ring after exactly its flight time.
    FVector Velocity=(Landing-Origin)/Flight;
    Velocity.Z+=.5f*SoraEnemyBody::ShellGravity*Flight;
    auto* Shell=GetWorld()->SpawnActorDeferred<ASoraProjectile>(ASoraProjectile::StaticClass(),
        FTransform(Velocity.Rotation(),Origin),this,this,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
    if(!Shell) return;
    Shell->Velocity=Velocity; Shell->Gravity=SoraEnemyBody::ShellGravity;
    Shell->Damage=Attack.Damage; Shell->Radius=Attack.RadiusCm; Shell->ArmingCm=Attack.ArmingCm;
    UGameplayStatics::FinishSpawningActor(Shell,Shell->GetActorTransform());
    ++ShotsSinceRelocation;
    SoraDamage::Ring(GetWorld(),Landing+FVector(0.f,0.f,3.f),Attack.RadiusCm,SoraEnemyBody::Amber,Flight);
    if(USoraGameEvents* Events=USoraGameEvents::Get(this))
    {
        FSoraWeaponFiredEvent Fired;
        Fired.Shooter=this; Fired.WeaponId=WeaponId; Fired.Kind=ESoraShotKind::Shell;
        Fired.Origin=Origin; Fired.Direction=Velocity.GetSafeNormal(); Fired.End=Landing;
        Events->OnWeaponFired.Broadcast(Fired);
    }
}
void ASoraEnemy::FireBeam(const FSoraEnemyAttack& Attack,ASoraCharacterBase& Target)
{
    const FVector From=Eye();
    const FVector Flat=LockedDirection.GetSafeNormal2D();
    const FVector There=Target.GetActorLocation();
    const float Along=FVector::DotProduct(There-From,Flat);
    const float Across=FVector::Dist2D(There,From+Flat*Along);
    // Walls stop the beam; bodies do not.
    FCollisionObjectQueryParams Solid;
    Solid.AddObjectTypesToQuery(ECC_WorldStatic);
    Solid.AddObjectTypesToQuery(ECC_WorldDynamic);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(SoraEnemyBeam),false,this);
    Query.AddIgnoredActor(&Target);
    const bool bClear=!GetWorld()->LineTraceTestByObjectType(From,There,Solid,Query);
    const bool bHit=Along>=0.f&&Along<=Attack.MaxRangeCm&&Across<=Attack.WidthCm*.5f&&bClear;
    const FVector End=From+Flat*Attack.MaxRangeCm;
    SoraDamage::Beam(GetWorld(),From,End,FLinearColor(.12f,1.f,1.f),8.f,.22f);
    if(USoraGameEvents* Events=USoraGameEvents::Get(this))
    {
        FSoraWeaponFiredEvent Fired;
        Fired.Shooter=this; Fired.WeaponId=WeaponId; Fired.Kind=ESoraShotKind::Beam; Fired.Origin=From; Fired.Direction=Flat; Fired.End=End;
        Events->OnWeaponFired.Broadcast(Fired);
    }
    if(!bHit) return;
    FSoraHit Hit=FSoraHit::Beam(From);
    Hit.AttackId=Attack.Id;
    FHitResult Trace; Trace.ImpactPoint=There; Trace.Location=There;
    SoraDamage::Strike(&Target,Attack.Damage,Hit,Flat,Trace,GetController(),this);
}
void ASoraEnemy::CastNet(const FSoraEnemyAttack& Attack,ASoraCharacterBase& Target)
{
    SoraDamage::Ring(GetWorld(),LockedPoint+FVector(0.f,0.f,3.f),Attack.RadiusCm,FLinearColor(.12f,1.f,1.f),.25f);
    // Only a target still inside the lock ring is caught.
    if(FVector::Dist2D(Feet(Target),LockedPoint)>Attack.RadiusCm) return;
    if(USoraCombatEffects* Effects=USoraCombatEffects::Get(this)) Effects->Root(Target,Attack.RootMs);
    if(Attack.Damage>0)
    {
        FSoraHit Hit=FSoraHit::Ranged(Eye(),INDEX_NONE);
        Hit.AttackId=Attack.Id;
        FHitResult Trace; Trace.ImpactPoint=Target.GetActorLocation(); Trace.Location=Trace.ImpactPoint;
        SoraDamage::Strike(&Target,Attack.Damage,Hit,-FVector::UpVector,Trace,GetController(),this);
    }
}
void ASoraEnemy::Stagger(int32 Ms)
{
    if(Ms<=0||!IsAlive()) return;
    const float Until=Now()+Ms/1000.f;
    if(Until<=StaggerUntil) return;
    StaggerUntil=Until;
    if(Phase==EPhase::Windup||Phase==EPhase::Firing) CancelAttack();
    NextAttackAt=FMath::Max(NextAttackAt,StaggerUntil);
    if(bDojoPupil) { bPupilWindup=false; NextPupilStrike=FMath::Max(NextPupilStrike,StaggerUntil); }
    if(!bKernelDriven) GetCharacterMovement()->StopMovementImmediately();
    Announce(ESoraEnemyCue::Staggered,NAME_None);
}
bool ASoraEnemy::AdmitDamage(float& Damage,FSoraHit& Hit,AActor* Causer)
{
    // A pupil cannot be scored until the four dojo forms are complete.
    if(bDojoPupil)
    {
        const auto* G=Cast<ASoraGameMode>(UGameplayStatics::GetGameMode(this));
        if(!G||!G->Campaign()->CanScoreDojoBout()) return false;
    }
    if(bInvulnerable||IsFreed()) return false;
    const float Time=Now();
    const int32 Facing=Hit.bHasOrigin?SoraDamage::FacingMilli(*this,Hit.Origin):-1000;
    // A squared tower shield stops the hit; a yari thrust on its rim turns it aside.
    if(Kind&&Kind->bShield&&Rules::ShieldStops(Hit.Kind,Facing,Kind->ShieldHalfArcMilli,IsShieldOpen()))
    {
        Hit.Defense=Rules::EDefense::Guard;
        if(Hit.Kind==Rules::EHit::Melee&&Hit.WeaponId==19)
        {
            ShieldOpenUntil=Time+Kind->RimOpeningMs/1000.f;
            Announce(ESoraEnemyCue::ShieldTurned,NAME_None);
        }
        if(USoraGameEvents* Events=USoraGameEvents::Get(this))
        {
            FSoraDefenseEvent Guarded;
            Guarded.Defender=this; Guarded.Attacker=Causer;
            Events->OnGuarded.Broadcast(Guarded);
        }
        return false;
    }
    int32 Amount=FMath::RoundToInt32(Damage);
    // A personal barrier soaks everything but scripted damage and its bypass weapons.
    if(BarrierMaxMilli>0&&VariantData&&Hit.Kind!=Rules::EHit::Scripted)
    {
        const FSoraEnemyBarrier& Spec=VariantData->Barrier;
        const Rules::FBarrierHit Soaked=Rules::SoakBarrier({BarrierMilli,BarrierMaxMilli},Amount,
            Spec.PermilleFor(Hit.WeaponId,Hit.Kind==Rules::EHit::Melee),Spec.BypassWeapons.Contains(Hit.WeaponId));
        BarrierMilli=Soaked.Barrier.HealthMilli; BarrierAtLastHitMilli=BarrierMilli; LastHitAt=Time;
        if(Soaked.Broke)
        {
            Stagger(Spec.BreakStaggerMs);
            Announce(ESoraEnemyCue::BarrierBroken,NAME_None);
        }
        Amount=Soaked.Damage;
        if(Amount<=0)
        {
            Hit.Defense=Rules::EDefense::Guard;
            return false;
        }
    }
    Amount=Rules::StaggeredDamage(Amount,IsStaggered());
    if(Kind) Amount=Rules::RearDamage(Amount,Facing,Kind->RearWeakPermille);
    // A landed strike staggers when it outweighs the opponent's poise, but a
    // chain of cuts cannot hold it still.
    if(Kind&&Hit.Kind==Rules::EHit::Melee)
    {
        const int32 Ms=Rules::StrikeStaggerMs(Hit.StaggerMs,Kind->PoiseMs,Time<StrikeStaggerImmuneUntil);
        if(Ms>0)
        {
            Stagger(Ms);
            StrikeStaggerImmuneUntil=Time+Rules::StaggerImmunityMs/1000.f;
        }
    }
    Damage=Amount;
    return Amount>0;
}
void ASoraEnemy::OnDefeated(AActor* Causer)
{
    // Zero here means the sparring pupil has yielded, not died; the
    // actor stands for a moment and cannot be scored a second time.
    CancelAttack();
    // A boss's add answers to the boss; the beat counts only its own opponents.
    if(ASoraBoss* Boss=SummonedBy.Get()) Boss->AddDefeated(*this);
    else if(auto* G=Cast<ASoraGameMode>(UGameplayStatics::GetGameMode(this))) G->Campaign()->OpponentDefeated(this);
    // A guard's body stays where it fell for the others to find; a combat
    // wave's fallen clear away.
    const auto* Brain=Cast<ASoraEnemyController>(GetController());
    if(Kind&&Brain&&Brain->IsGuard())
    {
        LieDown(true);
        return;
    }
    SetActorEnableCollision(false);
    if(bDojoPupil) SetActorTickEnabled(false);
    else SetActorRotation(FRotator(0,GetActorRotation().Yaw,85));
    SetLifeSpan(2.f);
}
void ASoraEnemy::Subdue(AActor* Causer)
{
    // 峰打ち: down, not dead. It stays where it fell until its collar drags it
    // up; a guard's comrades may find it meanwhile.
    Conscript=Rules::EConscript::Down; DownAt=Now(); Health=0.f; bSeized=false;
    LieDown(false);
    const auto* Brain=Cast<ASoraEnemyController>(GetController());
    if(USoraStealth* Stealth=USoraStealth::Get(this); Stealth&&Brain&&Brain->IsGuard()) Stealth->AddBody(*this);
    Announce(ESoraEnemyCue::Subdued,NAME_None);
}
void ASoraEnemy::LieDown(bool bBody)
{
    CancelAttack();
    GetCharacterMovement()->StopMovementImmediately();
    GetCharacterMovement()->DisableMovement();
    GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Pawn,ECR_Ignore);
    SetActorRotation(FRotator(0,GetActorRotation().Yaw,85));
    if(!bBody) return;
    UCapsuleComponent* Capsule=GetCapsuleComponent();
    Capsule->SetCollisionResponseToChannel(ECC_Visibility,ECR_Ignore);
    AddActorWorldOffset(FVector(0.f,0.f,Capsule->GetScaledCapsuleRadius()-Capsule->GetScaledCapsuleHalfHeight()));
    if(USoraStealth* Stealth=USoraStealth::Get(this)) Stealth->AddBody(*this);
}
void ASoraEnemy::KnockOut(AActor* By)
{
    if(!Kind||!IsAlive()) return;
    bSeized=false; bUnconscious=true; Health=0.f;
    LieDown(true);
    Announce(ESoraEnemyCue::KnockedOut,NAME_None);
    if(auto* G=Cast<ASoraGameMode>(UGameplayStatics::GetGameMode(this))) G->Campaign()->OpponentDefeated(this);
}
void ASoraEnemy::Seize(bool bHeld)
{
    bSeized=bHeld;
    if(!bHeld) return;
    CancelAttack();
    GetCharacterMovement()->StopMovementImmediately();
}
bool ASoraEnemy::CanCutSeal() const
{
    return Kind&&Rules::CanCutSeal(Conscript,SoraEnemyBody::Milliseconds(Now()-DownAt),Kind->SubdueWindowMs);
}
bool ASoraEnemy::CutSeal(AActor* By)
{
    if(!CanCutSeal()) return false;
    Conscript=Rules::EConscript::Freed; Health=MaxHealth;
    GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Pawn,ECR_Block);
    GetCharacterMovement()->SetMovementMode(MOVE_Walking);
    SetActorRotation(FRotator(0,GetActorRotation().Yaw,0));
    Announce(ESoraEnemyCue::Freed,NAME_None);
    return true;
}
void ASoraEnemy::Rise()
{
    // The collar drags it back up, hurt, and it knows where the hero is.
    Conscript=Rules::EConscript::Standing;
    Health=Rules::RisenHealth(FMath::RoundToInt32(MaxHealth),Kind->RiseHealthPermille);
    GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Pawn,ECR_Block);
    GetCharacterMovement()->SetMovementMode(MOVE_Walking);
    SetActorRotation(FRotator(0,GetActorRotation().Yaw,0));
    Announce(ESoraEnemyCue::Risen,NAME_None);
    if(auto* Brain=Cast<ASoraEnemyController>(GetController()))
        if(const APawn* Hero=UGameplayStatics::GetPlayerPawn(this,0)) Brain->Rouse(Hero->GetActorLocation());
}
void ASoraEnemy::PupilAttack(ASoraCharacterBase& Target,float Dist)
{
    if(IsStaggered()) return;
    const float Time=Now();
    const FVector From=GetActorLocation()+FVector(0,0,50);
    USoraGameEvents* Events=USoraGameEvents::Get(this);
    if(bPupilWindup)
    {
        if(Time<PupilWindupEndsAt) return;
        bPupilWindup=false;
        FHitResult Hit; FCollisionQueryParams PupilTrace(SCENE_QUERY_STAT(DojoSpar),false,this);
        const FVector To=From+PupilLockedDirection*200.f;
        GetWorld()->LineTraceSingleByChannel(Hit,From,To,ECC_Visibility,PupilTrace);
        SoraDamage::Beam(GetWorld(),From,Hit.bBlockingHit?Hit.ImpactPoint:To,FLinearColor(.83f,.92f,1.f),2.5f,.14f);
        FSoraStrikeResolvedEvent Resolved;
        Resolved.Attacker=this; Resolved.WeaponId=WeaponId;
        if(Hit.GetActor()==&Target)
        {
            // A sparring cut: the dojo's guard lessons take it whole, and a
            // fresh guard meets it and staggers the pupil (合わせ).
            FSoraHit Spar=FSoraHit::Melee(From,WeaponId);
            Spar.bParryable=true;
            Resolved.Target=&Target;
            Resolved.Damage=SoraDamage::Strike(&Target,4.f,Spar,PupilLockedDirection,Hit,GetController(),this);
            Resolved.bHit=Resolved.Damage>0;
        }
        if(Events) Events->OnStrikeResolved.Broadcast(Resolved);
        return;
    }
    if(Time<NextPupilStrike||Dist>190.f) return;
    bPupilWindup=true; PupilWindupEndsAt=Time+.55f; NextPupilStrike=PupilWindupEndsAt+1.45f;
    PupilLockedDirection=(Target.GetActorLocation()+FVector(0,0,50)-From).GetSafeNormal();
    SoraDamage::Beam(GetWorld(),From,From+PupilLockedDirection*200.f,FLinearColor(1.f,.68f,.16f),2.f,.55f);
    if(Events)
    {
        FSoraMeleeCommittedEvent Committed;
        Committed.Attacker=this; Committed.WeaponId=WeaponId; Committed.Direction=PupilLockedDirection; Committed.WindupSeconds=.55f;
        Events->OnMeleeCommitted.Broadcast(Committed);
    }
}
