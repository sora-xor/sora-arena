#include "SoraCharacterBase.h"
#include "ArenaKernelSubsystem.h"
#include "Combat/SoraDamage.h"
#include "SoraCatalog.h"
#include "SoraGameMode.h"
#include "SoraViewmodelComponent.h"
#include "SoraWorldBuilder.h"
#include "Animation/AnimationAsset.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInterface.h"

const FName ASoraCharacterBase::EyeComponentName(TEXT("Eye"));

ASoraCharacterBase::ASoraCharacterBase(const FObjectInitializer& ObjectInitializer)
    : Super(ObjectInitializer)
{
    PrimaryActorTick.bCanEverTick=true;
    GetCapsuleComponent()->InitCapsuleSize(34,88);
    GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);
    GetCharacterMovement()->JumpZVelocity=510.f;
    GetCharacterMovement()->AirControl=.25f;
    GetCharacterMovement()->BrakingDecelerationWalking=1800.f;
    GetCharacterMovement()->bRunPhysicsWithNoController=true;
    Eye=CreateDefaultSubobject<USceneComponent>(EyeComponentName);
    Eye->SetupAttachment(GetCapsuleComponent()); Eye->SetRelativeLocation(FVector(4,0,64));
    Viewmodel=CreateDefaultSubobject<USoraViewmodelComponent>(TEXT("WeaponRoot"));
    Viewmodel->SetupAttachment(Eye); Viewmodel->SetRelativeLocation(USoraViewmodelComponent::RestLocation());
    bUseControllerRotationYaw=true;
}
void ASoraCharacterBase::BeginPlay()
{
    Super::BeginPlay(); if(!FSoraCatalog::Get().Load()) return;
    ApplyClass(ClassId); BuildCat();
}
void ASoraCharacterBase::ApplyClass(int32 Id)
{
    if(!FSoraCatalog::Get().IsReady()) return;
    ClassId=FMath::Clamp(Id,0,5); const auto& C=FSoraCatalog::Get().Class(ClassId);
    MaxHealth=C.Health; Health=MaxHealth; GetCharacterMovement()->MaxWalkSpeed=C.Speed;
    WeaponId=C.Weapons[1];
    ResetLoadout();
    RebuildWeapon();
}
void ASoraCharacterBase::RebuildWeapon()
{
    Viewmodel->Build(WeaponId,WieldsDojoBokken(),IsFirstPersonHero());
}
bool ASoraCharacterBase::CanPlay() const
{
    const auto* GM=Cast<ASoraGameMode>(UGameplayStatics::GetGameMode(this));
    return IsAlive()&&GM&&GM->IsPlaying();
}
void ASoraCharacterBase::Tick(float Dt)
{
    Super::Tick(Dt); LifeTime+=Dt; DamageFlash=FMath::Max(0.f,DamageFlash-Dt); HitMarkerTime=FMath::Max(0.f,HitMarkerTime-Dt);
    if(bKernelDriven) return;
    if(!FSoraCatalog::Get().IsReady()) return;
    if(!CanPlay()) { HaltActions(); return; }
    TickPlay(Dt);
}
void ASoraCharacterBase::Heal(float Amount) { if(!bKernelDriven) Health=FMath::Min(MaxHealth,Health+FMath::Max(0.f,Amount)); }
float ASoraCharacterBase::TakeDamage(float Damage,const FDamageEvent& Event,AController* InstigatorController,AActor* Causer)
{
    return SoraDamage::Resolve(*this,Damage,Causer);
}
void ASoraCharacterBase::SetKernelDriven(bool Enabled,const FSoraPracticeMap* Map)
{
    bKernelDriven=Enabled;
    GetCharacterMovement()->StopMovementImmediately();
    GetCharacterMovement()->SetComponentTickEnabled(!Enabled);
    if(Enabled)
    {
        GetCharacterMovement()->DisableMovement(); bUseControllerRotationYaw=false;
        if(Map)
        {
            GetCapsuleComponent()->SetCapsuleSize(Map->PlayerRadius,Map->PlayerHalfHeight);
            Eye->SetRelativeLocation(FVector(0,0,Map->EyeHeight-Map->PlayerHalfHeight));
            GetMesh()->SetRelativeLocation(FVector(0,0,-Map->PlayerHalfHeight));
        }
        GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    }
    else
    {
        GetCapsuleComponent()->SetCapsuleSize(34,88); GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
        Eye->SetRelativeLocation(FVector(4,0,64)); GetMesh()->SetRelativeLocation(FVector(0,0,-88));
        GetCharacterMovement()->SetMovementMode(MOVE_Walking); bUseControllerRotationYaw=!IsEnemy();
        SetActorHiddenInGame(false);
    }
}
void ASoraCharacterBase::ApplyKernelPlayer(const FSoraPracticePlayer& State)
{
    if(!bKernelDriven) return;
    const bool ChangedWeapon=WeaponId!=State.WeaponId;
    Health=State.Health; MaxHealth=State.MaxHealth; ClassId=State.ClassId; WeaponId=State.WeaponId;
    const bool bReloadingPose=State.ReloadTicks>0;
    const float Speed=(State.Feet-KernelPreviousFeet).Size2D()*60.f;
    KernelPreviousFeet=State.Feet;
    SetActorLocation(State.Feet+FVector(0,0,GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight()),false,nullptr,ETeleportType::TeleportPhysics);
    SetActorRotation(FRotator(0,State.Aim.Yaw,0));
    GetCapsuleComponent()->SetCollisionEnabled(State.Alive?ECollisionEnabled::QueryOnly:ECollisionEnabled::NoCollision);
    if(ChangedWeapon) RebuildWeapon();
    // The same authoritative charge snapshot lifts every practice pawn's weapon,
    // so local and opposing players see commitment before the strike event.
    const float Windup=State.Alive&&State.ChargeRequired>0
        ? FMath::Clamp(static_cast<float>(State.ChargeTicks)/State.ChargeRequired,0.f,1.f)
        : 0.f;
    Viewmodel->KernelPose(Windup,bReloadingPose);
    const bool Moving=State.Alive&&Speed>5.f;
    UpdateLocomotion(Moving,Moving?FMath::Clamp(Speed/180.f,.65f,2.5f):1.f);
    OnKernelSnapshot(State);
}
void ASoraCharacterBase::UpdateLocomotion(bool Moving,float RateScale)
{
    if(!bSkeletalVisual) return;
    GetMesh()->GlobalAnimRateScale=RateScale;
    if(Moving!=bWalkingVisual)
    {
        UAnimationAsset* Animation=Moving?WalkAnimation.Get():IdleAnimation.Get();
        if(Animation) GetMesh()->PlayAnimation(Animation,true);
        bWalkingVisual=Moving;
    }
}
void ASoraCharacterBase::BuildCat()
{
    for(const auto& P:BodyParts) if(P) P->DestroyComponent(); BodyParts.Reset();
    OnBodyRebuilt();
    bSkeletalVisual=false; GetMesh()->SetSkeletalMesh(nullptr);
    const bool bAlien=UsesAlienBody();
    const bool bOwnerHidden=IsFirstPersonHero();
    const FString CatName=bAlien?TEXT("AlienBanker"):TEXT("NyaagyuSamurai");
    const FString RigPath=FString::Printf(TEXT("/Game/Generated/Meshes/SK_%s.SK_%s"),*CatName,*CatName);
    if(auto* RigMesh=LoadObject<USkeletalMesh>(nullptr,*RigPath))
    {
        GetMesh()->SetSkeletalMesh(RigMesh); GetMesh()->SetRelativeLocation(FVector(0,0,-88));
        GetMesh()->SetCollisionEnabled(ECollisionEnabled::NoCollision); GetMesh()->SetOwnerNoSee(bOwnerHidden);
        if(!bAlien)
        {
            const TArray<FSkeletalMaterial>& Slots=RigMesh->GetMaterials();
            for(int32 Index=0;Index<Slots.Num();++Index)
            {
                const FString Slot=Slots[Index].MaterialSlotName.ToString();
                if(!Slot.StartsWith(TEXT("M_Hero_"))) continue;
                const FString Name=TEXT("MI_Nyaakoto_")+Slot.RightChop(7);
                const FString Path=FString::Printf(TEXT("/Game/Generated/Characters/Nyaakoto/%s.%s"),*Name,*Name);
                if(auto* Material=LoadObject<UMaterialInterface>(nullptr,*Path,nullptr,LOAD_NoWarn))
                    GetMesh()->SetMaterial(Index,Material);
                else
                    UE_LOG(LogTemp,Error,TEXT("Nyaakoto PBR material is missing: %s"),*Path);
            }
        }
        IdleAnimation=LoadObject<UAnimationAsset>(nullptr,*FString::Printf(TEXT("/Game/Generated/Animations/A_%s_Idle.A_%s_Idle"),*CatName,*CatName));
        WalkAnimation=LoadObject<UAnimationAsset>(nullptr,*FString::Printf(TEXT("/Game/Generated/Animations/A_%s_Walk.A_%s_Walk"),*CatName,*CatName));
        if(IdleAnimation) GetMesh()->PlayAnimation(IdleAnimation,true);
        bSkeletalVisual=true; bWalkingVisual=false; return;
    }
    const TCHAR* Asset=bAlien?TEXT("/Game/Generated/Meshes/SM_AlienBanker.SM_AlienBanker"):TEXT("/Game/Generated/Meshes/SM_NyaagyuSamurai.SM_NyaagyuSamurai");
    if(auto* AuthoredMesh=LoadObject<UStaticMesh>(nullptr,Asset))
    {
        auto* Mesh=NewObject<UStaticMeshComponent>(this,MakeUniqueObjectName(this,UStaticMeshComponent::StaticClass(),TEXT("OriginalCatMesh")));
        Mesh->SetStaticMesh(AuthoredMesh); Mesh->SetupAttachment(GetCapsuleComponent());
        Mesh->SetRelativeLocation(FVector(0,0,-88)); Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Mesh->SetOwnerNoSee(bOwnerHidden); Mesh->RegisterComponent(); AddInstanceComponent(Mesh); BodyParts.Add(Mesh);
        return;
    }
    const FLinearColor Fur=bAlien?FLinearColor(.3,.34,.42):FLinearColor(.65,.4,.20);
    const FLinearColor Cloth=bAlien?FLinearColor(.17,.055,.26):FLinearColor(.04,.18,.24);
    auto Add=[&](FString Name,const TCHAR* Mesh,FVector L,FVector S,FLinearColor Color)
    {
        auto* M=ASoraWorldBuilder::Shape(this,GetCapsuleComponent(),Name,Mesh,L,S,Color);
        M->SetOwnerNoSee(bOwnerHidden); BodyParts.Add(M); return M;
    };
    const TCHAR* Sphere=TEXT("/Engine/BasicShapes/Sphere.Sphere");
    Add(TEXT("Haori"),Sphere,FVector(0,0,-10),FVector(.68,.75,1.02),Cloth);
    Add(TEXT("CatHead"),Sphere,FVector(0,0,56),FVector(.67,.61,.6),Fur);
    for(int32 S:{-1,1})
    {
        auto* Ear=Add(FString::Printf(TEXT("Ear%d"),S),TEXT("/Engine/BasicShapes/Cone.Cone"),FVector(0,S*21,86),FVector(.26,.26,.37),Fur);
        Ear->SetRelativeRotation(FRotator(0,0,S*14.f));
        Add(FString::Printf(TEXT("Eye%d"),S),Sphere,FVector(29,S*13,61),FVector(.07,.075,.11),FLinearColor(.9,.66,.12));
        Add(FString::Printf(TEXT("Sleeve%d"),S),Sphere,FVector(0,S*36,-4),FVector(.25,.3,.75),Cloth);
        Add(FString::Printf(TEXT("Leg%d"),S),Sphere,FVector(0,S*17,-61),FVector(.29,.3,.52),Cloth);
        Add(FString::Printf(TEXT("Paw%d"),S),Sphere,FVector(10,S*17,-83),FVector(.4,.29,.17),Fur);
        Add(FString::Printf(TEXT("Muzzle%d"),S),Sphere,FVector(28,S*8,44),FVector(.2,.19,.17),FLinearColor(.75,.69,.58));
    }
    Add(TEXT("Nose"),Sphere,FVector(37,0,49),FVector(.07,.09,.07),FLinearColor(.12,.07,.09));
    for(int32 I=0;I<5;++I) Add(FString::Printf(TEXT("Tail%d"),I),Sphere,FVector(-22-I*9,0,-38+I*11),FVector(.22,.20,.28),Fur);
    Add(TEXT("Obi"),TEXT("/Engine/BasicShapes/Cylinder.Cylinder"),FVector(0,0,-28),FVector(.71,.74,.15),FLinearColor(.5,.15,.045));
}
