#include "SoraEnemy.h"
#include "SoraBoss.h"
#include "SoraConstructRules.h"
#include "SoraGameMode.h"
#include "SoraSettings.h"
#include "SoraViewmodelComponent.h"
#include "SoraWorldBuilder.h"
#include "Combat/SoraDamage.h"
#include "Combat/SoraEnemyCatalog.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"

namespace Construct = SoraConstructRules;

const TArray<FSoraEnemyAttack>& ASoraEnemy::AttackSet() const
{
    static const TArray<FSoraEnemyAttack> ClimbShot=[] {
        FSoraEnemyAttack A;A.Id=TEXT("yagura_sentry_shot");A.Cue=A.Id;
        A.Kind=ESoraEnemyAttackKind::LockShot;A.Damage=12;A.WindupMs=200;A.RecoveryMs=1000;A.MaxRangeCm=1800;
        return TArray<FSoraEnemyAttack>{A};
    }();
    static const TArray<FSoraEnemyAttack> Slam = [] {
        FSoraEnemyAttack A;
        A.Id=TEXT("collateral_slam"); A.Cue=TEXT("collateral_slam");
        A.NameJapanese=TEXT("担保の叩きつけ"); A.NameEnglish=TEXT("Collateral slam");
        A.Damage=Construct::Damage; A.WindupMs=Construct::WindupMs; A.RecoveryMs=Construct::RecoveryMs;
        A.MaxRangeCm=Construct::RadiusCm; A.RadiusCm=Construct::RadiusCm; A.ArcMilli=-1000;
        // Uses the shared melee guard rule; the authored area slam is not parryable.
        A.GuardChip=-1; A.GuardStamina=-1;
        return TArray<FSoraEnemyAttack>{A};
    }();
    static const TArray<FSoraEnemyAttack> Empty;
    return bClimbSentry?ClimbShot:bCollateralConstruct?Slam:Kind?Kind->Attacks:Empty;
}

void ASoraEnemy::ResetConstruct()
{
    if(ConstructCore) ConstructCore->DestroyComponent();
    for(UStaticMeshComponent* Part:ConstructGoods) if(Part) Part->DestroyComponent();
    ConstructCore=nullptr; ConstructGoods.Reset(); GoodsAssembled.Reset();
    GoodsReleaseFrom.Reset(); GoodsReleaseTo.Reset();
    bCollateralConstruct=false; bConstructSlamReleased=false; bGoodsReleased=false; bCoreWasOpen=false;
    GoodsReleaseSeconds=0.f;
    if(Viewmodel) Viewmodel->SetVisibility(true,true);
}

void ASoraEnemy::EnableCollateralConstruct()
{
    if(bCollateralConstruct||ArchetypeId()!=TEXT("loom_automaton")||Variant!=TEXT("collateral_construct")||!Summoner()) return;
    bCollateralConstruct=true; Health=MaxHealth=Construct::Health;
    CancelAttack(); AttackReadyAt.Init(0.f,AttackSet().Num());
    // Explicit functional proxies: final rice, lacquer, farming tool, loom
    // and cart assets and their assembly/release animation belong to art.
    for(UStaticMeshComponent* Part:BodyParts) if(Part) Part->SetVisibility(false,true);
    GetMesh()->SetVisibility(false,true); Viewmodel->SetVisibility(false,true);
    const FVector Positions[]={FVector(-20,-38,30),FVector(-20,38,35),FVector(0,-45,-42),FVector(0,45,-40),FVector(-28,0,75)};
    const FVector Sizes[]={FVector(.70,.45,.40),FVector(.60,.45,.40),FVector(.95,.15,.22),FVector(.75,.22,.65),FVector(.50,.20,.50)};
    const TCHAR* Names[]={TEXT("RiceBaleProxy"),TEXT("LacquerChestProxy"),TEXT("PloughProxy"),TEXT("LoomFrameProxy"),TEXT("CartWheelProxy")};
    for(int32 N=0;N<5;++N)
    {
        ConstructGoods.Add(ASoraWorldBuilder::Shape(this,GetRootComponent(),Names[N],TEXT("/Engine/BasicShapes/Cube.Cube"),
            Positions[N],Sizes[N],N==1?FLinearColor(.08f,.025f,.02f):FLinearColor(.45f,.31f,.16f)));
        GoodsAssembled.Add(Positions[N]);
    }
    // The visible core protrudes beyond the capsule, so a real weapon trace
    // can reach its component. The capsule still blocks ordinary body shots.
    ConstructCore=ASoraWorldBuilder::Shape(this,GetRootComponent(),TEXT("CollateralCoreProxy"),
        TEXT("/Engine/BasicShapes/Sphere.Sphere"),FVector(65,0,25),FVector(.44f),FLinearColor(.12f,.16f,.18f));
    ConstructCore->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    ConstructCore->SetCollisionResponseToAllChannels(ECR_Ignore);
    ConstructCore->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);
    // Historical melee sweeps ECC_Pawn. An overlap reports this protruding
    // part before the blocking capsule, without adding a movement obstacle.
    ConstructCore->SetCollisionResponseToChannel(ECC_Pawn,ECR_Overlap);
    ConstructCore->SetCanEverAffectNavigation(false);
}

bool ASoraEnemy::IsConstructCoreOpen() const
{
    return bCollateralConstruct&&Construct::Open(IsAlive(),bConstructSlamReleased,Phase==EPhase::Recovery,
        FMath::CeilToInt((PhaseEndsAt-Now())*1000.f));
}
FVector ASoraEnemy::ConstructCorePoint() const
{
    return ConstructCore?ConstructCore->GetComponentLocation():GetActorLocation();
}
bool ASoraEnemy::CanReachConstructCore(const ASoraCharacterBase& By) const
{
    if(!IsConstructCoreOpen()||!ConstructCore||!By.IsAlive()||!By.GetCharacterMovement()->IsMovingOnGround()) return false;
    const FVector From=By.GetEye()->GetComponentLocation(),To=ConstructCorePoint();
    if(FVector::Dist(From,To)>220.f||FMath::Abs(Feet(By).Z-Feet(*this).Z)>60.f) return false;
    if(FVector::DotProduct(By.GetActorForwardVector(),(To-From).GetSafeNormal2D())<.7f) return false;
    FHitResult Hit;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(CollateralCoreReach),false,&By);
    return GetWorld()->LineTraceSingleByChannel(Hit,From,To,ECC_Visibility,Query)&&Hit.GetComponent()==ConstructCore;
}
bool ASoraEnemy::AdmitConstructDamage(float& Damage,FSoraHit& Hit)
{
    // Story/test scripted damage keeps its existing contract. Gameplay hits
    // must contact the exposed core with a real heavy arm; no rear multiplier.
    if(Hit.Kind==SoraCombatRules::EHit::Scripted) return true;
    Damage=Construct::CoreDamage(IsConstructCoreOpen(),Hit.Part.Get()==ConstructCore,
        Hit.Kind,Hit.WeaponId,Hit.StaggerMs);
    if(Damage<=0) Hit.Defense=SoraCombatRules::EDefense::Guard;
    return Damage>0;
}
void ASoraEnemy::ConstructSlam(const FSoraEnemyAttack& Attack)
{
    // The authored radius reaches every opposing body on this floor, not
    // merely the enemy's chosen target. StrikeMelee retains its real LOS test.
    for(TActorIterator<ASoraCharacterBase> It(GetWorld());It;++It)
        if(It->IsAlive()&&!It->IsEnemy()&&FVector::Dist2D(It->GetActorLocation(),GetActorLocation())<=Construct::RadiusCm&&
            FMath::Abs(Feet(**It).Z-Feet(*this).Z)<=60.f) StrikeMelee(Attack,**It);
}
void ASoraEnemy::ReleaseConstructGoods()
{
    if(bGoodsReleased) return;
    bGoodsReleased=true; GoodsReleaseSeconds=0.f;
    GetCharacterMovement()->StopMovementImmediately(); GetCharacterMovement()->DisableMovement();
    SetActorEnableCollision(false); ConstructCore->SetVisibility(false);
    // Keep the actor upright and the goods intact. A proxy follows a smooth
    // collision-queried descent; no destructive roll, impulse or expiry.
    FCollisionQueryParams Query(SCENE_QUERY_STAT(CollateralGoodsFloor),false,this);
    for(TActorIterator<ASoraCharacterBase> It(GetWorld());It;++It) Query.AddIgnoredActor(*It);
    for(int32 N=0;N<ConstructGoods.Num();++N)
    {
        UStaticMeshComponent* Part=ConstructGoods[N];
        const FVector From=Part->GetComponentLocation();
        const FVector Around=GetActorLocation()+GetActorRotation().RotateVector(FVector((N-2)*65.f,(N%2?1.f:-1.f)*120.f,0));
        FVector To=From;
        bool Found=false;
        // A seizure may remove the floor directly below. Search adjacent
        // intact floor first; never settle a prop through an absent tile.
        for(int32 Probe=0;Probe<25;++Probe)
        {
            const float Angle=Probe*2.39996323f;
            const float Radius=Probe?75.f*FMath::Sqrt(float(Probe)):0.f;
            const FVector P=Around+FVector(FMath::Cos(Angle)*Radius,FMath::Sin(Angle)*Radius,0);
            FHitResult Floor;
            if(GetWorld()->LineTraceSingleByChannel(Floor,P+FVector(0,0,250),P-FVector(0,0,800),ECC_Visibility,Query)&&Floor.ImpactNormal.Z>.8f)
            {
                To=Floor.ImpactPoint+FVector(0,0,Part->Bounds.BoxExtent.Z+2.f);
                Found=true;
                break;
            }
        }
        // An assembly at the edge of a larger missing pattern can use the
        // same intact-tile search as a falling character, then trace the
        // actual floor for the prop's own height.
        if(!Found)
        {
            const auto* Mode=Cast<ASoraGameMode>(UGameplayStatics::GetGameMode(this));
            FVector Safe;
            FHitResult Floor;
            if(Mode&&Mode->Arena()&&Mode->Arena()->SummitSafePoint(From,*this,Safe)&&
                GetWorld()->LineTraceSingleByChannel(Floor,Safe+FVector(0,0,250),Safe-FVector(0,0,800),ECC_Visibility,Query))
                To=Floor.ImpactPoint+FVector(0,0,Part->Bounds.BoxExtent.Z+2.f);
        }
        GoodsReleaseFrom.Add(From); GoodsReleaseTo.Add(To);
    }
}
void ASoraEnemy::TickConstruct(float Dt)
{
    if(bGoodsReleased)
    {
        const auto* Mode=Cast<ASoraGameMode>(UGameplayStatics::GetGameMode(this));
        if(!Mode||!Mode->IsPlaying()) return;
        GoodsReleaseSeconds+=Dt;
        const float T=Construct::Settle(FMath::FloorToInt(GoodsReleaseSeconds*1000.f));
        for(int32 N=0;N<ConstructGoods.Num();++N)
            ConstructGoods[N]->SetWorldLocation(FMath::Lerp(GoodsReleaseFrom[N],GoodsReleaseTo[N],T));
        return;
    }
    const bool Open=IsConstructCoreOpen();
    if(Open!=bCoreWasOpen)
    {
        ASoraWorldBuilder::Tint(ConstructCore,Open?SoraAccessibility::TelegraphColor(this,SoraAccessibility::ETelegraph::Lock):FLinearColor(.12f,.16f,.18f));
        bCoreWasOpen=Open;
    }
    const float Lift=IsWindingUp()?WindupProgress()*35.f:0.f;
    for(int32 N=0;N<ConstructGoods.Num();++N)
        ConstructGoods[N]->SetRelativeLocation(GoodsAssembled[N]+FVector(0,0,Lift));
}
