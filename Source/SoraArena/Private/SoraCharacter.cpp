#include "SoraCharacter.h"
#include "SoraCatalog.h"
#include "SoraGameMode.h"
#include "SoraWorldBuilder.h"
#include "SoraProjectile.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/InputComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Components/StaticMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PlayerInput.h"
#include "Kismet/GameplayStatics.h"
#include "GameFramework/DamageType.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "ArenaWalletSubsystem.h"
#include "Engine/GameInstance.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Animation/AnimationAsset.h"
#include "ArenaKernelSubsystem.h"
#include "SoraControlSaveGame.h"
#include "SoraHistoricalArms.h"

ASoraCharacter::ASoraCharacter()
{
    PrimaryActorTick.bCanEverTick=true;
    GetCapsuleComponent()->InitCapsuleSize(34,88);
    GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);
    GetCharacterMovement()->JumpZVelocity=510.f;
    GetCharacterMovement()->AirControl=.25f;
    GetCharacterMovement()->BrakingDecelerationWalking=1800.f;
    GetCharacterMovement()->bRunPhysicsWithNoController=true;
    Camera=CreateDefaultSubobject<UCameraComponent>(TEXT("FirstPersonCamera"));
    Camera->SetupAttachment(GetCapsuleComponent()); Camera->SetRelativeLocation(FVector(4,0,64));
    Camera->bUsePawnControlRotation=true; Camera->FieldOfView=94.f;
    // UE 5.8's native viewmodel projection keeps a readable weapon silhouette
    // while shrinking the actual primitive away from nearby world geometry.
    Camera->bEnableFirstPersonFieldOfView=true;
    Camera->bEnableFirstPersonScale=true;
    Camera->FirstPersonFieldOfView=70.f;
    Camera->FirstPersonScale=.6f;
    WeaponRoot=CreateDefaultSubobject<USceneComponent>(TEXT("WeaponRoot"));
    WeaponRoot->SetupAttachment(Camera); WeaponRoot->SetRelativeLocation(FVector(40,18,-18));
    bUseControllerRotationYaw=true;
}
void ASoraCharacter::BeginPlay()
{
    Super::BeginPlay(); if(!FSoraCatalog::Get().Load()) return;
    ApplyClass(ClassId); BuildCat();
}
void ASoraCharacter::ApplyClass(int32 Id)
{
    if(!FSoraCatalog::Get().IsReady()) return;
    ClassId=FMath::Clamp(Id,0,5); const auto& C=FSoraCatalog::Get().Class(ClassId);
    MaxHealth=C.Health; Health=MaxHealth; GetCharacterMovement()->MaxWalkSpeed=C.Speed;
    WeaponId=C.Weapons[1]; Ammo=FSoraCatalog::Get().Weapon(WeaponId).Magazine;
    AmmoByWeapon.SetNum(21); for(int32 I=0;I<21;++I) AmmoByWeapon[I]=FSoraCatalog::Get().Weapon(I).Magazine;
    bReloading=false; NextShot=0; bFireHeld=false; bBowDrawing=false;
    bCommittedStrike=false; bHistoricalRecovery=false; CommittedWeaponId=INDEX_NONE; BuildWeapon();
}
void ASoraCharacter::MakeEnemy(int32 Id)
{
    bEnemy=true; bDojoPupil=false; bDojoTraining=false; bCampaignBoss=false; EnemyIndex=Id; bUseControllerRotationYaw=false;
    GetCharacterMovement()->bOrientRotationToMovement=false;
    ApplyClass(Id%6); BuildCat();
}
void ASoraCharacter::MakeCampaignBoss(int32 Id)
{
    // The final chapter reuses the alien banker cat prototype. This encounter
    // is entirely local; it never enters the multiplayer combat kernel.
    MakeEnemy(Id);
    bCampaignBoss=true;
    MaxHealth=300.f; Health=MaxHealth;
    GetCharacterMovement()->MaxWalkSpeed=280.f;
    SetActorScale3D(FVector(1.25f));
    bBossWindup=false; bBossRecovery=false; bBossBeam=true;
    BossAttackNumber=0; BossPhaseTimer=0.f; BossVisualTimer=0.f;
}
void ASoraCharacter::SetDojoTraining(bool Enabled)
{
    const bool bChanged=bDojoTraining!=Enabled;
    bDojoTraining=Enabled;
    bOfflineGuardHeld=false; bDojoRecoveryPending=false;
    bBowDrawing=false; bCommittedStrike=false; bHistoricalRecovery=false;
    if(Enabled&&FSoraCatalog::Get().IsReady())
    {
        WeaponId=FSoraCatalog::Get().Class(0).Weapons[0];
        Ammo=FSoraCatalog::Get().Weapon(WeaponId).Magazine;
        BuildWeapon();
    }
    else if(bChanged) BuildWeapon();
}
void ASoraCharacter::SetCampaignHeroLoadout(bool Enabled)
{
    if(!FSoraCatalog::Get().IsReady()) return;
    const bool bChanged=bCampaignHero!=Enabled;
    bCampaignHero=Enabled;
    if(!Enabled)
    {
        for(const auto& Piece:QuiverParts) if(Piece) { BodyParts.Remove(Piece); Piece->DestroyComponent(); }
        QuiverParts.Reset();
        return;
    }
    const auto& Hero=FSoraCatalog::Get().Hero();
    WeaponId=Hero.KatanaId;
    Ammo=FSoraCatalog::Get().Weapon(WeaponId).Magazine;
    AmmoByWeapon[Hero.YumiId]=Hero.QuiverArrows;
    BuildWeapon();
    if(bChanged) BuildHeroQuiver();
}
void ASoraCharacter::SuspendDojoAction()
{
    if(bDojoTraining)
    {
        bOfflineGuardHeld=false;
        bDojoRecoveryPending=false;
    }
    if(bDojoPupil)
    {
        bPupilWindup=false;
        NextEnemyShot=GetWorld()->GetTimeSeconds()+.8f;
    }
}
void ASoraCharacter::MakeDojoPupil(int32 Id)
{
    bEnemy=true; bDojoPupil=true; EnemyIndex=Id; bUseControllerRotationYaw=false;
    bPupilWindup=false; NextEnemyShot=GetWorld()->GetTimeSeconds()+1.4f+Id*.35f;
    GetCharacterMovement()->bOrientRotationToMovement=false;
    ApplyClass(0); SetDojoTraining(true); BuildCat();
}
void ASoraCharacter::SetKernelDriven(bool Enabled,const FSoraPracticeMap* Map)
{
    bKernelDriven=Enabled; KernelHeldButtons=0; KernelQueuedButtons=0; InputForward=0; InputRight=0;
    bFireHeld=false; bReloading=false; bSprint=false;
    GetCharacterMovement()->StopMovementImmediately();
    GetCharacterMovement()->SetComponentTickEnabled(!Enabled);
    if(Enabled)
    {
        GetCharacterMovement()->DisableMovement(); bUseControllerRotationYaw=false;
        if(Map)
        {
            GetCapsuleComponent()->SetCapsuleSize(Map->PlayerRadius,Map->PlayerHalfHeight);
            Camera->SetRelativeLocation(FVector(0,0,Map->EyeHeight-Map->PlayerHalfHeight));
            GetMesh()->SetRelativeLocation(FVector(0,0,-Map->PlayerHalfHeight));
        }
        GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    }
    else
    {
        GetCapsuleComponent()->SetCapsuleSize(34,88); GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
        Camera->SetRelativeLocation(FVector(4,0,64)); GetMesh()->SetRelativeLocation(FVector(0,0,-88));
        GetCharacterMovement()->SetMovementMode(MOVE_Walking); bUseControllerRotationYaw=!bEnemy;
        SetActorHiddenInGame(false);
    }
}
FSoraPracticeInput ASoraCharacter::ConsumeKernelInput()
{
    FSoraPracticeInput Input;
    const FRotator Aim=GetControlRotation();
    Input.Yaw=static_cast<uint16>(FMath::RoundToInt(FRotator::ClampAxis(Aim.Yaw)*65536.f/360.f)&65535);
    Input.Pitch=static_cast<int16>(FMath::Clamp(FMath::RoundToInt(FRotator::NormalizeAxis(Aim.Pitch)*16384.f/90.f),-16384,16384));
    if(CanPlay())
    {
        Input.Forward=static_cast<int16>(FMath::Clamp(FMath::RoundToInt(InputForward*127),-127,127));
        Input.Right=static_cast<int16>(FMath::Clamp(FMath::RoundToInt(InputRight*127),-127,127));
        Input.Buttons=KernelHeldButtons|KernelQueuedButtons;
    }
    KernelQueuedButtons=0;
    return Input;
}
void ASoraCharacter::ApplyKernelPlayer(const FSoraPracticePlayer& State)
{
    if(!bKernelDriven) return;
    const bool ChangedWeapon=WeaponId!=State.WeaponId;
    Health=State.Health; MaxHealth=State.MaxHealth; ClassId=State.ClassId; WeaponId=State.WeaponId;
    Ammo=State.Ammo; bReloading=State.ReloadTicks>0;
    const float Speed=(State.Feet-KernelPreviousFeet).Size2D()*60.f;
    KernelPreviousFeet=State.Feet;
    SetActorLocation(State.Feet+FVector(0,0,GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight()),false,nullptr,ETeleportType::TeleportPhysics);
    SetActorRotation(FRotator(0,State.Aim.Yaw,0));
    GetCapsuleComponent()->SetCollisionEnabled(State.Alive?ECollisionEnabled::QueryOnly:ECollisionEnabled::NoCollision);
    if(bEnemy) SetActorHiddenInGame(!State.Alive);
    if(ChangedWeapon) BuildWeapon();
    // The same authoritative charge snapshot lifts every practice pawn's weapon,
    // so local and opposing players see commitment before the strike event.
    const float Windup=State.Alive&&State.ChargeRequired>0
        ? FMath::Clamp(static_cast<float>(State.ChargeTicks)/State.ChargeRequired,0.f,1.f)
        : 0.f;
    WeaponRoot->SetRelativeLocation(FVector(40,18,-18+8.f*Windup));
    WeaponRoot->SetRelativeRotation(FRotator(bReloading?-30.f:28.f*Windup,0,0));
    if(bSkeletalVisual)
    {
        const bool Moving=State.Alive&&Speed>5.f;
        GetMesh()->GlobalAnimRateScale=Moving?FMath::Clamp(Speed/180.f,.65f,2.5f):1.f;
        if(Moving!=bWalkingVisual)
        {
            UAnimationAsset* Animation=Moving?WalkAnimation.Get():IdleAnimation.Get();
            if(Animation) GetMesh()->PlayAnimation(Animation,true);
            bWalkingVisual=Moving;
        }
    }
}
void ASoraCharacter::BuildCat()
{
    for(const auto& P:BodyParts) if(P) P->DestroyComponent(); BodyParts.Reset();
    QuiverParts.Reset();
    bSkeletalVisual=false; GetMesh()->SetSkeletalMesh(nullptr);
    const bool bAlien=bEnemy&&!bDojoPupil;
    const FString CatName=bAlien?TEXT("AlienBanker"):TEXT("NyaagyuSamurai");
    const FString RigPath=FString::Printf(TEXT("/Game/Generated/Meshes/SK_%s.SK_%s"),*CatName,*CatName);
    if(auto* RigMesh=LoadObject<USkeletalMesh>(nullptr,*RigPath))
    {
        GetMesh()->SetSkeletalMesh(RigMesh); GetMesh()->SetRelativeLocation(FVector(0,0,-88));
        GetMesh()->SetCollisionEnabled(ECollisionEnabled::NoCollision); GetMesh()->SetOwnerNoSee(!bEnemy);
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
        Mesh->SetOwnerNoSee(!bEnemy); Mesh->RegisterComponent(); AddInstanceComponent(Mesh); BodyParts.Add(Mesh);
        return;
    }
    const FLinearColor Fur=bAlien?FLinearColor(.3,.34,.42):FLinearColor(.65,.4,.20);
    const FLinearColor Cloth=bAlien?FLinearColor(.17,.055,.26):FLinearColor(.04,.18,.24);
    auto Add=[&](FString Name,const TCHAR* Mesh,FVector L,FVector S,FLinearColor Color)
    {
        auto* M=ASoraWorldBuilder::Shape(this,GetCapsuleComponent(),Name,Mesh,L,S,Color);
        M->SetOwnerNoSee(!bEnemy); BodyParts.Add(M); return M;
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
void ASoraCharacter::BuildHeroQuiver()
{
    // Nyaakoto's red-fletched quiver is visible on the world model, while
    // first-person arms and the camera remain clear of the back-mounted prop.
    if(!bCampaignHero||bEnemy) return;
    auto Add=[&](const TCHAR* Name,const TCHAR* Mesh,FVector Location,FVector Scale,FLinearColor Color)
    {
        auto* Piece=ASoraWorldBuilder::Shape(this,GetCapsuleComponent(),Name,Mesh,Location,Scale,Color);
        Piece->SetOwnerNoSee(true); BodyParts.Add(Piece); QuiverParts.Add(Piece); return Piece;
    };
    Add(TEXT("NyaakotoQuiver"),TEXT("/Engine/BasicShapes/Cylinder.Cylinder"),
        FVector(-23,25,28),FVector(.13f,.13f,.53f),FLinearColor(.18f,.08f,.045f))->SetRelativeRotation(FRotator(-14,0,0));
    Add(TEXT("NyaakotoQuiverRim"),TEXT("/Engine/BasicShapes/Cylinder.Cylinder"),
        FVector(-12,25,58),FVector(.145f,.145f,.05f),FLinearColor(.37f,.24f,.11f));
    for(int32 Index=0;Index<5;++Index)
    {
        const float Lateral=17.f+Index*4.f;
        Add(*FString::Printf(TEXT("NyaakotoArrow%d"),Index),TEXT("/Engine/BasicShapes/Cylinder.Cylinder"),
            FVector(-10+Index%2*3,Lateral,77),FVector(.008f,.008f,.46f),FLinearColor(.45f,.23f,.09f));
        Add(*FString::Printf(TEXT("NyaakotoFletching%d"),Index),TEXT("/Engine/BasicShapes/Cone.Cone"),
            FVector(-10+Index%2*3,Lateral,98),FVector(.035f,.035f,.10f),FLinearColor(.70f,.095f,.055f));
    }
}
void ASoraCharacter::BuildWeapon()
{
    for(const auto& P:WeaponParts) if(P) P->DestroyComponent(); WeaponParts.Reset();
    if(!FSoraCatalog::Get().IsReady()) return;
    const auto& W=FSoraCatalog::Get().Weapon(WeaponId);
    // Chapter-one sparring uses the original bokken. The first two ordinary
    // weapons use authored meshes; all of these change presentation only.
    UStaticMesh* AuthoredMesh=nullptr;
    if(bDojoTraining)
        AuthoredMesh=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/Generated/Meshes/SM_Nyaagyu_DojoBokken.SM_Nyaagyu_DojoBokken"));
    else if(WeaponId==0)
        AuthoredMesh=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/Generated/Meshes/SM_Nyaagyu_HeroKatana.SM_Nyaagyu_HeroKatana"));
    else if(WeaponId==1)
        AuthoredMesh=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/Generated/Meshes/SM_Nyaagyu_ArcCarbine.SM_Nyaagyu_ArcCarbine"));
    if(!AuthoredMesh&&!bDojoTraining&&WeaponId<18)
    {
        const FString Asset=FString::Printf(TEXT("/Game/Generated/Meshes/SM_Weapon_%02d.SM_Weapon_%02d"),WeaponId,WeaponId);
        AuthoredMesh=LoadObject<UStaticMesh>(nullptr,*Asset);
    }
    if(AuthoredMesh)
    {
        auto* Mesh=NewObject<UStaticMeshComponent>(this,MakeUniqueObjectName(this,UStaticMeshComponent::StaticClass(),TEXT("OriginalWeaponMesh"))); Mesh->SetStaticMesh(AuthoredMesh);
        Mesh->SetupAttachment(WeaponRoot); Mesh->SetRelativeScale3D(FVector(.75)); Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        if(!bEnemy) Mesh->SetFirstPersonPrimitiveType(EFirstPersonPrimitiveType::FirstPerson);
        Mesh->SetOnlyOwnerSee(!bEnemy); Mesh->SetVisibility(true); Mesh->RegisterComponent(); AddInstanceComponent(Mesh); WeaponParts.Add(Mesh);
        return;
    }
    auto Add=[&](FString N,FVector L,FVector S,FLinearColor C)
    {
        auto* M=ASoraWorldBuilder::Shape(this,WeaponRoot,N,TEXT("/Engine/BasicShapes/Cube.Cube"),L,S,C);
        if(!bEnemy) M->SetFirstPersonPrimitiveType(EFirstPersonPrimitiveType::FirstPerson);
        M->SetOnlyOwnerSee(!bEnemy); M->SetVisibility(true); WeaponParts.Add(M); return M;
    };
    if(WeaponId==18)
    {
        // Yumi: an asymmetric stave, with the grip below its midpoint. This
        // source-only silhouette is awaiting a rigged, material-finished bow.
        const FLinearColor Wood(.31f,.14f,.055f), String(.79f,.72f,.55f);
        Add(TEXT("YumiLower"),FVector(5,0,-39),FVector(.045,.045,.75),Wood)->SetRelativeRotation(FRotator(-6,0,0));
        Add(TEXT("YumiUpper"),FVector(12,0,72),FVector(.045,.045,1.45),Wood)->SetRelativeRotation(FRotator(5,0,0));
        Add(TEXT("YumiGrip"),FVector(7,0,-5),FVector(.09,.07,.22),FLinearColor(.09f,.055f,.03f));
        Add(TEXT("YumiString"),FVector(-13,0,34),FVector(.008,.008,2.15),String);
        Add(TEXT("NockedArrow"),FVector(34,0,2),FVector(.48,.012,.012),FLinearColor(.64f,.38f,.13f));
        Add(TEXT("Arrowhead"),FVector(83,0,2),FVector(.055,.025,.025),FLinearColor(.66f,.70f,.74f));
    }
    else if(WeaponId==19 || WeaponId==20)
    {
        const bool bYari=WeaponId==19;
        Add(TEXT("LacqueredShaft"),FVector(50,0,2),FVector(2.f,.035f,.035f),FLinearColor(.19f,.095f,.035f));
        Add(TEXT("IronFerrule"),FVector(145,0,2),FVector(.085f,.045f,.045f),FLinearColor(.35f,.38f,.40f));
        auto* Blade=Add(bYari?TEXT("StraightSpearhead"):TEXT("CurvedNaginataBlade"),
            FVector(bYari?172:178,0,bYari?2:7),FVector(bYari?.30f:.42f,.02f,bYari?.035f:.065f),
            FLinearColor(.68f,.75f,.79f));
        if(!bYari) Blade->SetRelativeRotation(FRotator(0,-10.f,0));
    }
    else if(W.Kind==TEXT("melee"))
    {
        Add(TEXT("Blade"),FVector(30,0,10),FVector(.9,.025,.07),bDojoTraining?FLinearColor(.46,.27,.11):FLinearColor(.72,.80,.84));
        Add(TEXT("Tsuka"),FVector(-24,0,10),FVector(.22,.055,.075),FLinearColor(.15,.06,.025));
        Add(TEXT("Tsuba"),FVector(-10,0,10),FVector(.025,.16,.20),bDojoTraining?FLinearColor(.31,.16,.06):FLinearColor(.52,.32,.08));
    }
    else
    {
        Add(TEXT("Receiver"),FVector(5,0,0),FVector(.5,.1,.14),FLinearColor(.14,.16,.18));
        Add(TEXT("Barrel"),FVector(43,0,1),FVector(.42,.045,.045),W.Special?FLinearColor(.07,.67,.67):FLinearColor(.20,.23,.25));
        Add(TEXT("Stock"),FVector(-26,0,-1),FVector(.3,.08,.13),FLinearColor(.29,.13,.035));
        Add(TEXT("Magazine"),FVector(3,0,-12),FVector(.1,.08,.22),FLinearColor(.25,.25,.23));
        Add(TEXT("Sight"),FVector(22,0,10),FVector(.08,.065,.06),FLinearColor(.65,.39,.08));
    }
    Add(TEXT("FurPaw"),FVector(-13,-2,-10),FVector(.13,.15,.13),FLinearColor(.69,.47,.25));
}
bool ASoraCharacter::CanPlay() const
{
    const auto* GM=Cast<ASoraGameMode>(UGameplayStatics::GetGameMode(this));
    return IsAlive()&&GM&&!GM->bMenu&&!GM->bDefeated&&!GM->bChapterComplete;
}
float ASoraCharacter::BowDrawProgress() const
{
    return bBowDrawing&&GetWorld()?FMath::Clamp((GetWorld()->GetTimeSeconds()-BowDrawStartedAt)/.65f,0.f,1.f):0.f;
}
float ASoraCharacter::StrikeWindupProgress() const
{
    if(!bCommittedStrike||!GetWorld()||CommittedWeaponId==INDEX_NONE) return 0.f;
    const auto Form=CommittedWeaponId==19?SoraHistoricalArms::EForm::Yari:
        CommittedWeaponId==20?SoraHistoricalArms::EForm::Naginata:SoraHistoricalArms::EForm::Katana;
    const float Windup=SoraHistoricalArms::Profile(Form).WindupSeconds;
    return FMath::Clamp(1.f-(CommittedStrikeAt-GetWorld()->GetTimeSeconds())/Windup,0.f,1.f);
}
void ASoraCharacter::Tick(float Dt)
{
    Super::Tick(Dt); LifeTime+=Dt; DamageFlash=FMath::Max(0.f,DamageFlash-Dt); HitMarkerTime=FMath::Max(0.f,HitMarkerTime-Dt);
    if(bKernelDriven) return;
    if(!FSoraCatalog::Get().IsReady()||!CanPlay()) return;
    if(bEnemy) { BotTick(Dt); return; }
    if(bDojoTraining)
    {
        if(auto* G=Cast<ASoraGameMode>(UGameplayStatics::GetGameMode(this)))
        {
            const float Now=GetWorld()->GetTimeSeconds();
            if(bOfflineGuardHeld&&G->DojoLessonStage()==0)
                G->RecordDojoLesson(SoraDojoRules::EAction::Stance,
                    FMath::RoundToInt((Now-OfflineGuardPressedAt)*1000.f));
            if(bDojoRecoveryPending&&Now>=DojoRecoveryEndsAt&&!bFireHeld)
            {
                if(G->RecordDojoLesson(SoraDojoRules::EAction::Recovery,
                    FMath::RoundToInt((Now-DojoRecoveryStartedAt)*1000.f),true,DojoRecoveryRequiredMs))
                    bDojoRecoveryPending=false;
            }
        }
    }
    const float Now=GetWorld()->GetTimeSeconds();
    if(bCommittedStrike&&Now>=CommittedStrikeAt) ResolveCommittedStrike();
    if(bHistoricalRecovery&&Now>=NextShot) bHistoricalRecovery=false;
    if(bReloading&&Now>=ReloadEnd) { Ammo=FSoraCatalog::Get().Weapon(WeaponId).Magazine; bReloading=false; }
    if(bFireHeld) Fire();
    GetCharacterMovement()->MaxWalkSpeed=FSoraCatalog::Get().Class(ClassId).Speed*
        (bCommittedStrike?.35f:bHistoricalRecovery?.65f:bBowDrawing?.55f:bSprint?1.35f:1.f);
    const float Moving=FMath::Clamp(GetVelocity().Size2D()/500.f,0.f,1.f);
    WeaponRoot->SetRelativeLocation(FVector(40,18+FMath::Sin(LifeTime*8)*Moving*.7,-18+FMath::Cos(LifeTime*16)*Moving*.6));
    WeaponRoot->SetRelativeRotation(FRotator(bReloading?-30.f:bCommittedStrike?25.f:bBowDrawing?-15.f:0.f,0,bSprint?-15.f:0.f));
}
void ASoraCharacter::Forward(float V) { if(bKernelDriven) { InputForward=V; return; } if(CanPlay()) AddMovementInput(GetActorForwardVector(),V); }
void ASoraCharacter::Strafe(float V) { if(bKernelDriven) { InputRight=V; return; } if(CanPlay()) AddMovementInput(GetActorRightVector(),V); }
void ASoraCharacter::Yaw(float V) { if(CanPlay()) AddControllerYawInput(V); }
void ASoraCharacter::Pitch(float V) { if(CanPlay()) AddControllerPitchInput(bInvertedLook?-V:V); }
void ASoraCharacter::GamepadYaw(float V)
{
    if(CanPlay()) AddControllerYawInput(FMath::Clamp(V,-1.f,1.f)*90.f*GamepadLookSensitivity*GetWorld()->GetDeltaSeconds());
}
void ASoraCharacter::GamepadPitch(float V)
{
    if(CanPlay()) AddControllerPitchInput(FMath::Clamp(V,-1.f,1.f)*70.f*GamepadLookSensitivity*GetWorld()->GetDeltaSeconds()*(bInvertedLook?-1.f:1.f));
}
void ASoraCharacter::FireDown()
{
    // Input can arrive while the title/menu is open. Never carry a held trigger
    // into resumed combat if it was first pressed outside gameplay.
    if(!CanPlay()) return;
    if(bKernelDriven) { KernelHeldButtons|=1; return; }
    const auto& W=FSoraCatalog::Get().Weapon(WeaponId);
    if(W.Kind==TEXT("bow"))
    {
        if(!bBowDrawing&&!bReloading&&!bSprint&&Ammo>0&&GetWorld()->GetTimeSeconds()>=NextShot)
        { bBowDrawing=true; BowDrawStartedAt=GetWorld()->GetTimeSeconds(); }
        return;
    }
    if(!bDojoTraining&&(WeaponId==0||WeaponId==19||WeaponId==20)) { Fire(); return; }
    bFireHeld=true; Fire();
}
void ASoraCharacter::FireUp() { bFireHeld=false; KernelHeldButtons&=~1u; if(bBowDrawing) ReleaseBow(); }
void ASoraCharacter::SprintDown() { if(CanPlay()&&!bCommittedStrike&&!bBowDrawing) bSprint=true; } void ASoraCharacter::SprintUp() { bSprint=false; }
void ASoraCharacter::JumpDown() { if(bKernelDriven) { if(CanPlay()) KernelQueuedButtons|=8; return; } if(CanPlay()&&!bCommittedStrike&&!bBowDrawing) Jump(); }
void ASoraCharacter::JumpUp() { StopJumping(); }
void ASoraCharacter::Beam(UWorld* World,FVector A,FVector B,FLinearColor Color,float Radius,float Life)
{
    auto* Effect=World->SpawnActor<AActor>();
    auto* Mesh=ASoraWorldBuilder::Shape(Effect,nullptr,TEXT("Tracer"),TEXT("/Engine/BasicShapes/Cylinder.Cylinder"),FVector::ZeroVector,FVector(Radius/50,Radius/50,FVector::Distance(A,B)/100),Color);
    Effect->SetRootComponent(Mesh); Effect->SetActorLocation((A+B)*.5f); Effect->SetActorRotation(FRotationMatrix::MakeFromZ(B-A).Rotator()); Effect->SetLifeSpan(Life);
}
void ASoraCharacter::Fire()
{
    if(bKernelDriven) return;
    if(!CanPlay()||bReloading||bSprint||bBowDrawing||bCommittedStrike||GetWorld()->GetTimeSeconds()<NextShot) return;
    const auto& W=FSoraCatalog::Get().Weapon(WeaponId);
    if(W.Kind==TEXT("melee")) { Melee(); return; }
    if(W.Kind==TEXT("bow")) return;
    if(Ammo<=0) { Reload(); return; }
    --Ammo; NextShot=GetWorld()->GetTimeSeconds()+W.Cooldown;
    const FVector Start=Camera->GetComponentLocation(); const FVector Dir=Camera->GetForwardVector();
    if(W.Kind==TEXT("explosive"))
    {
        FActorSpawnParameters P; P.Owner=this; P.Instigator=this; P.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        auto* Shell=GetWorld()->SpawnActor<ASoraProjectile>(Start+Dir*70,Dir.Rotation(),P);
        Shell->Velocity=Dir*W.ProjectileSpeed; Shell->Damage=W.Damage; Shell->Radius=W.BlastRadius;
    }
    else
    {
        FHitResult Hit; FCollisionQueryParams Params(SCENE_QUERY_STAT(PlayerShot),false,this);
        const FVector End=Start+Dir*W.Range; GetWorld()->LineTraceSingleByChannel(Hit,Start,End,ECC_Visibility,Params);
        Beam(GetWorld(),Start+Dir*65+Camera->GetRightVector()*17-Camera->GetUpVector()*12,Hit.bBlockingHit?Hit.ImpactPoint:End,W.Special?FLinearColor(.08,.9,.9):FLinearColor(1,.68,.15));
        if(Hit.GetActor())
        {
            UGameplayStatics::ApplyPointDamage(Hit.GetActor(),W.Damage,Dir,Hit,GetController(),this,UDamageType::StaticClass());
            if(auto* Victim=Cast<ASoraCharacter>(Hit.GetActor())) if(Victim->IsEnemy()) HitMarkerTime=.14f;
        }
        if(W.Kind==TEXT("healing")) Heal(5.f);
    }
    AddControllerPitchInput(-.3f);
}
void ASoraCharacter::Melee()
{
    if(bKernelDriven) { if(CanPlay()) KernelHeldButtons|=2; return; }
    if(!CanPlay()||GetWorld()->GetTimeSeconds()<NextShot||bReloading||bCommittedStrike||bBowDrawing) return;
    const int32 MeleeId=FSoraCatalog::Get().Weapon(WeaponId).Kind==TEXT("melee")?WeaponId:FSoraCatalog::Get().Class(ClassId).Weapons[0];
    const auto& W=FSoraCatalog::Get().Weapon(MeleeId);
    if(!bDojoTraining&&(MeleeId==0||MeleeId==19||MeleeId==20))
    {
        const auto Form=MeleeId==19?SoraHistoricalArms::EForm::Yari:
            MeleeId==20?SoraHistoricalArms::EForm::Naginata:SoraHistoricalArms::EForm::Katana;
        const auto Profile=SoraHistoricalArms::Profile(Form);
        const float Now=GetWorld()->GetTimeSeconds();
        bCommittedStrike=true; bHistoricalRecovery=true; bSprint=false;
        CommittedWeaponId=MeleeId; CommittedDirection=Camera->GetForwardVector();
        CommittedStrikeAt=Now+Profile.WindupSeconds;
        NextShot=CommittedStrikeAt+Profile.RecoverySeconds;
        return;
    }
    NextShot=GetWorld()->GetTimeSeconds()+W.Cooldown;
    if(bDojoTraining)
    {
        if(const auto* G=Cast<ASoraGameMode>(UGameplayStatics::GetGameMode(this)))
        {
            if(G->DojoLessonStage()==3)
            {
                bDojoRecoveryPending=true;
                DojoRecoveryStartedAt=GetWorld()->GetTimeSeconds();
                DojoRecoveryEndsAt=NextShot;
                DojoRecoveryRequiredMs=FMath::CeilToInt(W.Cooldown*1000.f);
            }
        }
    }
    const FVector Start=Camera->GetComponentLocation(); const FVector Dir=Camera->GetForwardVector();
    FCollisionQueryParams Params(SCENE_QUERY_STAT(Melee),false,this); TArray<FHitResult> Hits;
    GetWorld()->SweepMultiByChannel(Hits,Start,Start+Dir*W.Range,FQuat::Identity,ECC_Pawn,FCollisionShape::MakeSphere(45),Params);
    TSet<AActor*> Damaged;
    for(const auto& H:Hits) if(H.GetActor()&&!Damaged.Contains(H.GetActor()))
    {
        FHitResult Block; GetWorld()->LineTraceSingleByChannel(Block,Start,H.ImpactPoint,ECC_Visibility,Params);
        if(Block.GetActor()&&Block.GetActor()!=H.GetActor()) continue;
        Damaged.Add(H.GetActor());
        const float Applied=UGameplayStatics::ApplyPointDamage(H.GetActor(),W.Damage,Dir,H,GetController(),this,UDamageType::StaticClass());
        if(Applied>0&&Cast<ASoraCharacter>(H.GetActor())) HitMarkerTime=.18f;
    }
    Beam(GetWorld(),Start+Dir*50-Camera->GetRightVector()*40,Start+Dir*125+Camera->GetRightVector()*55,FLinearColor(.55,.9,1),2.5,.12);
}
void ASoraCharacter::ResolveCommittedStrike()
{
    bCommittedStrike=false;
    if(!CanPlay()||CommittedWeaponId==INDEX_NONE) return;
    const int32 StrikeWeapon=CommittedWeaponId;
    CommittedWeaponId=INDEX_NONE;
    const auto Form=StrikeWeapon==19?SoraHistoricalArms::EForm::Yari:
        StrikeWeapon==20?SoraHistoricalArms::EForm::Naginata:SoraHistoricalArms::EForm::Katana;
    const auto Profile=SoraHistoricalArms::Profile(Form);
    // The attack direction is fixed at commitment. A turn cannot turn a
    // threatened cut into an instantaneous hit behind the defender.
    if(FVector::DotProduct(Camera->GetForwardVector(),CommittedDirection)<.70f) return;
    const FVector Start=Camera->GetComponentLocation();
    const FVector End=Start+CommittedDirection*Profile.MaximumDistanceCm;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(HistoricalMelee),false,this);
    TArray<FHitResult> Hits;
    GetWorld()->SweepMultiByChannel(Hits,Start,End,FQuat::Identity,ECC_Pawn,
        FCollisionShape::MakeSphere(StrikeWeapon==19?16.f:36.f),Params);
    AActor* TargetActor=nullptr;
    FHitResult TargetHit;
    float BestDistance=MAX_flt;
    for(const FHitResult& Hit:Hits)
    {
        AActor* Candidate=Hit.GetActor();
        if(!Candidate||Candidate==this) continue;
        const FVector Delta=Candidate->GetActorLocation()-GetActorLocation();
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
        const float Applied=UGameplayStatics::ApplyPointDamage(TargetActor,
            FSoraCatalog::Get().Weapon(StrikeWeapon).Damage,CommittedDirection,TargetHit,
            GetController(),this,UDamageType::StaticClass());
        if(Applied>0&&Cast<ASoraCharacter>(TargetActor)) HitMarkerTime=.18f;
    }
    Beam(GetWorld(),Start+CommittedDirection*40.f,End,
        StrikeWeapon==19?FLinearColor(.73f,.78f,.82f):FLinearColor(.55f,.75f,.82f),1.4f,.11f);
}
void ASoraCharacter::ReleaseBow()
{
    bBowDrawing=false;
    if(!CanPlay()||WeaponId!=18||bReloading||bSprint||Ammo<=0||
        GetWorld()->GetTimeSeconds()-BowDrawStartedAt<.65f) return;
    const auto& W=FSoraCatalog::Get().Weapon(18);
    const FVector Direction=Camera->GetForwardVector();
    const FVector Origin=Camera->GetComponentLocation()+Direction*65.f;
    FActorSpawnParameters Params; Params.Owner=this; Params.Instigator=this;
    auto* Arrow=GetWorld()->SpawnActorDeferred<ASoraProjectile>(ASoraProjectile::StaticClass(),
        FTransform(Direction.Rotation(),Origin),this,this,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
    if(!Arrow) return;
    Arrow->bArrow=true; Arrow->Damage=W.Damage; Arrow->Velocity=Direction*W.ProjectileSpeed;
    UGameplayStatics::FinishSpawningActor(Arrow,Arrow->GetActorTransform());
    --Ammo; NextShot=GetWorld()->GetTimeSeconds()+W.Cooldown;
}
void ASoraCharacter::Reload()
{
    if(bKernelDriven) { if(CanPlay()) KernelQueuedButtons|=32; return; }
    if(!CanPlay()||bReloading) return; const auto& W=FSoraCatalog::Get().Weapon(WeaponId);
    if(W.Kind==TEXT("melee")||Ammo>=W.Magazine) return; bReloading=true; ReloadEnd=GetWorld()->GetTimeSeconds()+W.Reload;
}
void ASoraCharacter::Heal(float Amount) { if(!bKernelDriven) Health=FMath::Min(MaxHealth,Health+FMath::Max(0.f,Amount)); }
float ASoraCharacter::TakeDamage(float Damage,const FDamageEvent& Event,AController* InstigatorController,AActor* Causer)
{
    if(bKernelDriven) return 0;
    if(!CanPlay()||Damage<=0) return 0;
    if(const auto* Other=Cast<ASoraCharacter>(Causer)) if(Other->bEnemy&&bEnemy) return 0;
    if(bDojoPupil)
    {
        const auto* G=Cast<ASoraGameMode>(UGameplayStatics::GetGameMode(this));
        if(!G||!G->CanScoreDojoBout()) return 0;
    }
    if(bDojoTraining&&bOfflineGuardHeld)
    {
        if(const auto* Pupil=Cast<ASoraCharacter>(Causer)) if(Pupil->bDojoPupil)
        {
            const FVector ToAttacker=(Pupil->GetActorLocation()-GetActorLocation()).GetSafeNormal2D();
            const bool bFacing=FVector::DotProduct(GetActorForwardVector(),ToAttacker)>=.25f;
            if(bFacing)
            {
                if(auto* G=Cast<ASoraGameMode>(UGameplayStatics::GetGameMode(this)))
                {
                    const int32 HeldMs=FMath::RoundToInt((GetWorld()->GetTimeSeconds()-OfflineGuardPressedAt)*1000.f);
                    if(G->DojoLessonStage()==2)
                        G->RecordDojoLesson(SoraDojoRules::EAction::Parry,HeldMs,true);
                    else if(G->DojoLessonStage()==1)
                        G->RecordDojoLesson(SoraDojoRules::EAction::Guard,HeldMs,true);
                }
                return 0.f;
            }
        }
    }
    const float Applied=FMath::Min(Health,Damage); Health-=Applied; DamageFlash=.3f;
    if(Health<=0)
    {
        auto* GM=Cast<ASoraGameMode>(UGameplayStatics::GetGameMode(this));
        if(bEnemy)
        {
            // Zero here means the sparring pupil has yielded, not died; the
            // actor stands for a moment and cannot be scored a second time.
            GM->OpponentDefeated(this); SetActorEnableCollision(false);
            if(bDojoPupil) SetActorTickEnabled(false);
            else SetActorRotation(FRotator(0,GetActorRotation().Yaw,85));
            SetLifeSpan(2.f);
        }
        else
        {
            if(bDojoTraining) Health=1.f;
            bFireHeld=false; GM->PlayerKilled();
        }
    }
    return Applied;
}
void ASoraCharacter::BotTick(float Dt)
{
    if(bSkeletalVisual)
    {
        const bool Moving=GetVelocity().Size2D()>5.f;
        GetMesh()->GlobalAnimRateScale=Moving?FMath::Clamp(GetVelocity().Size2D()/180.f,.65f,2.5f):1.f;
        if(Moving!=bWalkingVisual)
        {
            UAnimationAsset* Animation=Moving?WalkAnimation.Get():IdleAnimation.Get();
            if(Animation) GetMesh()->PlayAnimation(Animation,true);
            bWalkingVisual=Moving;
        }
    }
    auto* Target=Cast<ASoraCharacter>(UGameplayStatics::GetPlayerPawn(this,0)); if(!Target||!Target->IsAlive()) return;
    if(bCampaignBoss) { BossTick(Dt,Target); return; }
    FVector Delta=Target->GetActorLocation()-GetActorLocation(); const float Dist=Delta.Size2D(); Delta.Z=0;
    SetActorRotation(FMath::RInterpTo(GetActorRotation(),Delta.Rotation(),Dt,4.f));
    FVector Move=Delta.GetSafeNormal();
    FHitResult Ahead; FCollisionQueryParams P(SCENE_QUERY_STAT(BotNavigation),false,this);
    if(GetWorld()->LineTraceSingleByChannel(Ahead,GetActorLocation(),GetActorLocation()+Move*180,ECC_Visibility,P)&&Ahead.GetActor()!=Target)
        Move=FVector(-Move.Y,Move.X,0)*(EnemyIndex%2?1:-1);
    if(!bDojoPupil||!bPupilWindup)
    {
        if(Dist>(bDojoPupil?160.f:650.f)) AddMovementInput(Move,.55f);
        else AddMovementInput(GetActorRightVector(),FMath::Sin(LifeTime+EnemyIndex)*.2f);
    }
    if(bDojoPupil)
    {
        const float Now=GetWorld()->GetTimeSeconds();
        const FVector From=GetActorLocation()+FVector(0,0,50);
        if(bPupilWindup)
        {
            if(Now<PupilWindupEndsAt) return;
            bPupilWindup=false;
            FHitResult Hit; FCollisionQueryParams PupilTrace(SCENE_QUERY_STAT(DojoSpar),false,this);
            const FVector To=From+PupilLockedDirection*200.f;
            GetWorld()->LineTraceSingleByChannel(Hit,From,To,ECC_Visibility,PupilTrace);
            Beam(GetWorld(),From,Hit.bBlockingHit?Hit.ImpactPoint:To,FLinearColor(.83f,.92f,1.f),2.5f,.14f);
            if(Hit.GetActor()==Target)
                UGameplayStatics::ApplyPointDamage(Target,4.f,PupilLockedDirection,Hit,GetController(),this,UDamageType::StaticClass());
            return;
        }
        if(Now<NextEnemyShot||Dist>190.f) return;
        bPupilWindup=true; PupilWindupEndsAt=Now+.55f; NextEnemyShot=PupilWindupEndsAt+1.45f;
        PupilLockedDirection=(Target->GetActorLocation()+FVector(0,0,50)-From).GetSafeNormal();
        Beam(GetWorld(),From,From+PupilLockedDirection*200.f,FLinearColor(1.f,.68f,.16f),2.f,.55f);
        return;
    }
    if(GetWorld()->GetTimeSeconds()<NextEnemyShot||Dist>2100) return;
    NextEnemyShot=GetWorld()->GetTimeSeconds()+1.3f+EnemyIndex%3*.2f;
    FVector From=GetActorLocation()+FVector(0,0,50); FVector To=Target->GetActorLocation()+FVector(0,0,35);
    FHitResult Hit; GetWorld()->LineTraceSingleByChannel(Hit,From,To,ECC_Visibility,P);
    if(Hit.GetActor()==Target)
    {
        const bool bMiss=FMath::FRand()<.32f;
        Beam(GetWorld(),From,To+(bMiss?FVector(0,80,60):FVector::ZeroVector),FLinearColor(1,.12,.3),1.7);
        if(!bMiss) UGameplayStatics::ApplyPointDamage(Target,7.f,(To-From).GetSafeNormal(),Hit,GetController(),this,UDamageType::StaticClass());
    }
}
void ASoraCharacter::BossTelegraph()
{
    const FVector From=GetActorLocation()+FVector(0,0,55);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(BossWarning),false,this);
    if(bBossBeam)
    {
        const FVector End=From+BossLockedDirection*1500.f;
        FHitResult Hit;
        GetWorld()->LineTraceSingleByChannel(Hit,From,End,ECC_Visibility,Query);
        Beam(GetWorld(),From,Hit.bBlockingHit?Hit.ImpactPoint:End,FLinearColor(.04f,.85f,.95f),3.f,.18f);
    }
    else
    {
        for(int32 Side:{-1,1})
            Beam(GetWorld(),From,From+BossLockedDirection.RotateAngleAxis(Side*28.f,FVector::UpVector)*330.f,
                FLinearColor(1.f,.52f,.08f),3.5f,.18f);
    }
}
void ASoraCharacter::BossStrike(ASoraCharacter* Target)
{
    const FVector From=GetActorLocation()+FVector(0,0,55);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(BossStrike),false,this);
    FHitResult Hit;
    if(bBossBeam)
    {
        const FVector End=From+BossLockedDirection*1500.f;
        GetWorld()->LineTraceSingleByChannel(Hit,From,End,ECC_Visibility,Query);
        Beam(GetWorld(),From,Hit.bBlockingHit?Hit.ImpactPoint:End,FLinearColor(.12f,1.f,1.f),8.f,.22f);
        if(Hit.GetActor()==Target)
            UGameplayStatics::ApplyPointDamage(Target,22.f,BossLockedDirection,Hit,GetController(),this,UDamageType::StaticClass());
    }
    else
    {
        const FVector To=Target->GetActorLocation()+FVector(0,0,35);
        const FVector Delta=To-From;
        GetWorld()->LineTraceSingleByChannel(Hit,From,To,ECC_Visibility,Query);
        for(int32 Side:{-1,1})
            Beam(GetWorld(),From,From+BossLockedDirection.RotateAngleAxis(Side*28.f,FVector::UpVector)*330.f,
                FLinearColor(1.f,.80f,.24f),8.f,.22f);
        if(Delta.Size2D()<=330.f && FVector::DotProduct(Delta.GetSafeNormal2D(),BossLockedDirection)>=.88f && Hit.GetActor()==Target)
            UGameplayStatics::ApplyPointDamage(Target,30.f,BossLockedDirection,Hit,GetController(),this,UDamageType::StaticClass());
    }
}
void ASoraCharacter::BossTick(float Dt,ASoraCharacter* Target)
{
    // Fixed attack order, locked aim, explicit warning, and recovery make the
    // offline encounter readable. No random damage or hidden hit timestamp.
    if(bBossWindup)
    {
        BossPhaseTimer=FMath::Max(0.f,BossPhaseTimer-Dt);
        BossVisualTimer-=Dt;
        if(BossVisualTimer<=0.f) { BossTelegraph(); BossVisualTimer=.13f; }
        if(BossPhaseTimer<=0.f)
        {
            BossStrike(Target);
            bBossWindup=false; bBossRecovery=true;
            BossPhaseTimer=Health<=MaxHealth*.5f ? .90f : 1.15f;
        }
        return;
    }
    if(bBossRecovery)
    {
        BossPhaseTimer=FMath::Max(0.f,BossPhaseTimer-Dt);
        if(BossPhaseTimer<=0.f) bBossRecovery=false;
        return;
    }
    FVector Delta=Target->GetActorLocation()-GetActorLocation(); Delta.Z=0.f;
    const float Distance=Delta.Size2D();
    if(Distance>740.f)
    {
        const FVector Move=Delta.GetSafeNormal2D();
        SetActorRotation(FMath::RInterpTo(GetActorRotation(),Move.Rotation(),Dt,3.f));
        AddMovementInput(Move,.72f);
        return;
    }
    bBossBeam=Distance>340.f||(BossAttackNumber%2)==0;
    ++BossAttackNumber;
    BossLockedDirection=Delta.GetSafeNormal2D();
    if(BossLockedDirection.IsNearlyZero()) BossLockedDirection=GetActorForwardVector().GetSafeNormal2D();
    SetActorRotation(BossLockedDirection.Rotation());
    GetCharacterMovement()->StopMovementImmediately();
    bBossWindup=true;
    BossWindupDuration=bBossBeam?1.45f:1.2f;
    BossPhaseTimer=BossWindupDuration;
    BossVisualTimer=0.f;
}
void ASoraCharacter::Interact() { if(CanPlay()) if(auto* G=Cast<ASoraGameMode>(UGameplayStatics::GetGameMode(this))) G->Interact(this); }
void ASoraCharacter::Menu()
{
    if(auto* G=Cast<ASoraGameMode>(UGameplayStatics::GetGameMode(this)))
    {
        G->ToggleMenu();
        if(G->bMenu) { FireUp(); MeleeUp(); BlockUp(); SprintUp(); JumpUp(); }
    }
}
void ASoraCharacter::Enter() { if(auto* G=Cast<ASoraGameMode>(UGameplayStatics::GetGameMode(this))) G->BeginRound(); }
void ASoraCharacter::NextMap() { if(auto* G=Cast<ASoraGameMode>(UGameplayStatics::GetGameMode(this))) G->NextMap(); }
void ASoraCharacter::NewCampaign() { if(auto* G=Cast<ASoraGameMode>(UGameplayStatics::GetGameMode(this))) G->NewCampaign(); }
void ASoraCharacter::ReturnCampaign() { if(auto* G=Cast<ASoraGameMode>(UGameplayStatics::GetGameMode(this))) G->ReturnCampaign(); }
void ASoraCharacter::Practice() { if(auto* G=Cast<ASoraGameMode>(UGameplayStatics::GetGameMode(this))) G->DeterministicPractice(); }
void ASoraCharacter::BlockDown()
{
    if(!CanPlay()) return;
    if(bKernelDriven) { KernelHeldButtons|=4; return; }
    if(bDojoTraining&&!bOfflineGuardHeld)
    {
        bOfflineGuardHeld=true;
        OfflineGuardPressedAt=GetWorld()->GetTimeSeconds();
    }
}
void ASoraCharacter::BlockUp() { KernelHeldButtons&=~4u; bOfflineGuardHeld=false; }
void ASoraCharacter::Ability() { if(bKernelDriven&&CanPlay()) KernelQueuedButtons|=16; }
void ASoraCharacter::MeleeUp() { KernelHeldButtons&=~2u; }
void ASoraCharacter::Subtitles() { if(auto* G=Cast<ASoraGameMode>(UGameplayStatics::GetGameMode(this))) G->ToggleSubtitles(); }
void ASoraCharacter::PairWallet()
{
    const auto* G=Cast<ASoraGameMode>(UGameplayStatics::GetGameMode(this)); if(!G||!G->bMenu) return;
    if(auto* Wallet=GetGameInstance()->GetSubsystem<UArenaWalletSubsystem>())
        if(Wallet->State==EArenaWalletState::Idle||Wallet->State==EArenaWalletState::Disconnected||Wallet->State==EArenaWalletState::Unavailable||Wallet->State==EArenaWalletState::Error)
            Wallet->BeginPairingFromConfig();
}
void ASoraCharacter::OpenWallet()
{
    const auto* G=Cast<ASoraGameMode>(UGameplayStatics::GetGameMode(this)); if(!G||!G->bMenu) return;
    if(auto* Wallet=GetGameInstance()->GetSubsystem<UArenaWalletSubsystem>()) if(Wallet->State==EArenaWalletState::AwaitingApproval) Wallet->LaunchWallet();
}
void ASoraCharacter::DisconnectWallet()
{
    const auto* G=Cast<ASoraGameMode>(UGameplayStatics::GetGameMode(this)); if(!G||!G->bMenu) return;
    if(auto* Wallet=GetGameInstance()->GetSubsystem<UArenaWalletSubsystem>()) Wallet->DisconnectWallet();
}
void ASoraCharacter::ChooseClass(int32 Id) { if(auto* G=Cast<ASoraGameMode>(UGameplayStatics::GetGameMode(this))) G->SelectClass(Id); }
void ASoraCharacter::Equip(int32 Slot)
{
    if(bKernelDriven) { if(auto* G=Cast<ASoraGameMode>(UGameplayStatics::GetGameMode(this))) G->SelectPracticeWeapon(Slot); return; }
    if(!CanPlay()||bReloading||bCommittedStrike||
        (bHistoricalRecovery&&GetWorld()->GetTimeSeconds()<NextShot)||
        (bDojoTraining&&Slot!=0)) return;
    bBowDrawing=false; bFireHeld=false;
    AmmoByWeapon[WeaponId]=Ammo; WeaponId=FSoraCatalog::Get().Class(ClassId).Weapons[Slot];
    Ammo=AmmoByWeapon[WeaponId]; NextShot=GetWorld()->GetTimeSeconds()+.25f; BuildWeapon();
}
void ASoraCharacter::WeaponOne(){Equip(1);} void ASoraCharacter::WeaponTwo(){Equip(0);} void ASoraCharacter::WeaponThree(){Equip(2);}
void ASoraCharacter::EquipCampaignWeapon(int32 NewWeaponId)
{
    const auto* G=Cast<ASoraGameMode>(UGameplayStatics::GetGameMode(this));
    if(!G||!G->bCampaign||G->ChapterId==0||bKernelDriven||bDojoTraining||
        !CanPlay()||bReloading||bCommittedStrike||
        (bHistoricalRecovery&&GetWorld()->GetTimeSeconds()<NextShot)||
        NewWeaponId<18||NewWeaponId>20||ClassId!=0) return;
    bBowDrawing=false; bFireHeld=false;
    AmmoByWeapon[WeaponId]=Ammo;
    WeaponId=NewWeaponId; Ammo=AmmoByWeapon[WeaponId];
    NextShot=GetWorld()->GetTimeSeconds()+.25f; BuildWeapon();
}
void ASoraCharacter::WeaponFour(){EquipCampaignWeapon(18);}
void ASoraCharacter::WeaponFive(){EquipCampaignWeapon(19);}
void ASoraCharacter::WeaponSix(){EquipCampaignWeapon(20);}
void ASoraCharacter::CampaignWeaponNext()
{
    EquipCampaignWeapon(WeaponId>=18&&WeaponId<20?WeaponId+1:18);
}
void ASoraCharacter::ClassOne(){ChooseClass(0);} void ASoraCharacter::ClassTwo(){ChooseClass(1);} void ASoraCharacter::ClassThree(){ChooseClass(2);}
void ASoraCharacter::ClassFour(){ChooseClass(3);} void ASoraCharacter::ClassFive(){ChooseClass(4);} void ASoraCharacter::ClassSix(){ChooseClass(5);}
void ASoraCharacter::ClassPrevious()
{
    if(auto* G=Cast<ASoraGameMode>(UGameplayStatics::GetGameMode(this))) if(G->bMenu) ChooseClass((G->SelectedClass+5)%6);
}
void ASoraCharacter::ClassNext()
{
    if(auto* G=Cast<ASoraGameMode>(UGameplayStatics::GetGameMode(this))) if(G->bMenu) ChooseClass((G->SelectedClass+1)%6);
}
TArray<FKey> ASoraCharacter::GetActionKeys(FName ActionName) const
{
    TArray<FKey> Keys;
    const auto* PC=Cast<APlayerController>(GetController());
    if(!PC||!PC->PlayerInput) return Keys;
    for(const FInputActionKeyMapping& Mapping:PC->PlayerInput->GetKeysForAction(ActionName)) Keys.AddUnique(Mapping.Key);
    return Keys;
}
bool ASoraCharacter::RemapCombatAction(FName ActionName,FKey NewKey)
{
    if(!ApplyCombatActionMapping(ActionName,NewKey,true)) return false;
    if(ControlProfile)
    {
        const bool bGamepad=NewKey.IsGamepadKey(),bMouse=NewKey.IsMouseButton();
        ControlProfile->Bindings.RemoveAll([&](const FSoraControlBinding& Binding)
        {
            return Binding.ActionName==ActionName&&Binding.Key.IsGamepadKey()==bGamepad&&Binding.Key.IsMouseButton()==bMouse;
        });
        FSoraControlBinding Binding;
        Binding.ActionName=ActionName; Binding.Key=NewKey;
        ControlProfile->Bindings.Add(Binding);
        SaveControlProfile();
    }
    return true;
}
bool ASoraCharacter::ApplyCombatActionMapping(FName ActionName,FKey NewKey,bool bRequireMenu)
{
    // Never permit wallet, menu, or campaign commands to be rebound by combat UI.
    static const TSet<FName> Allowed={
        TEXT("Fire"),TEXT("Melee"),TEXT("Jump"),TEXT("Sprint"),TEXT("Reload"),TEXT("Interact"),
        TEXT("Block"),TEXT("Ability"),TEXT("WeaponOne"),TEXT("WeaponTwo"),TEXT("WeaponThree"),
        TEXT("WeaponFour"),TEXT("WeaponFive"),TEXT("WeaponSix"),TEXT("CampaignWeaponNext")};
    const auto* G=Cast<ASoraGameMode>(UGameplayStatics::GetGameMode(this));
    auto* PC=Cast<APlayerController>(GetController());
    if((bRequireMenu&&(!G||!G->bMenu))||!Allowed.Contains(ActionName)||!NewKey.IsValid()||!NewKey.IsBindableToActions()||!PC||!PC->PlayerInput) return false;
    UPlayerInput* PlayerInput=PC->PlayerInput;
    for(const FInputActionKeyMapping& Mapping:PlayerInput->ActionMappings)
    {
        if(Mapping.ActionName==ActionName&&Mapping.Key==NewKey) return true;
        if(Mapping.ActionName!=ActionName&&Mapping.Key==NewKey) return false;
    }
    const bool bGamepad=NewKey.IsGamepadKey(),bMouse=NewKey.IsMouseButton();
    const TArray<FInputActionKeyMapping> Existing=PlayerInput->GetKeysForAction(ActionName);
    for(const FInputActionKeyMapping& Mapping:Existing)
        if(Mapping.Key.IsGamepadKey()==bGamepad&&Mapping.Key.IsMouseButton()==bMouse)
            PlayerInput->RemoveActionMapping(Mapping);
    FInputActionKeyMapping Replacement;
    Replacement.ActionName=ActionName;
    Replacement.Key=NewKey;
    PlayerInput->AddActionMapping(Replacement);
    PlayerInput->FlushPressedKeys();
    PlayerInput->ForceRebuildingKeyMaps(false);
    FireUp(); MeleeUp(); BlockUp(); SprintUp(); JumpUp();
    return true;
}
void ASoraCharacter::SetGamepadDeadZones(float MoveDeadZone,float LookDeadZone)
{
    if(!FMath::IsFinite(MoveDeadZone)||!FMath::IsFinite(LookDeadZone)) return;
    GamepadMoveDeadZone=FMath::Clamp(MoveDeadZone,0.f,.5f);
    GamepadLookDeadZone=FMath::Clamp(LookDeadZone,0.f,.5f);
    if(ControlProfile&&!bRestoringControlProfile)
    {
        ControlProfile->MoveDeadZone=GamepadMoveDeadZone;
        ControlProfile->LookDeadZone=GamepadLookDeadZone;
        SaveControlProfile();
    }
    auto* PC=Cast<APlayerController>(GetController());
    if(!PC||!PC->PlayerInput) return;
    UPlayerInput* PlayerInput=PC->PlayerInput;
    for(const FKey& Key:{EKeys::Gamepad_LeftX,EKeys::Gamepad_LeftY,EKeys::Gamepad_RightX,EKeys::Gamepad_RightY})
    {
        FInputAxisProperties Properties;
        PlayerInput->GetAxisProperties(Key,Properties);
        Properties.Sensitivity=1.f;
        Properties.Exponent=Key==EKeys::Gamepad_RightX||Key==EKeys::Gamepad_RightY?1.4f:1.f;
        Properties.DeadZone=Key==EKeys::Gamepad_LeftX||Key==EKeys::Gamepad_LeftY?GamepadMoveDeadZone:GamepadLookDeadZone;
        PlayerInput->SetAxisProperties(Key,Properties);
    }
}
void ASoraCharacter::SetGamepadLookSensitivity(float Sensitivity)
{
    if(!FMath::IsFinite(Sensitivity)) return;
    GamepadLookSensitivity=FMath::Clamp(Sensitivity,.25f,3.f);
    if(ControlProfile&&!bRestoringControlProfile)
    {
        ControlProfile->LookSensitivity=GamepadLookSensitivity;
        SaveControlProfile();
    }
}
void ASoraCharacter::SetInvertedLook(bool Enabled)
{
    bInvertedLook=Enabled;
    if(ControlProfile&&!bRestoringControlProfile)
    {
        ControlProfile->InvertedLook=Enabled;
        SaveControlProfile();
    }
}
void ASoraCharacter::LoadControlProfile()
{
    ControlProfile=Cast<USoraControlSaveGame>(UGameplayStatics::LoadGameFromSlot(TEXT("SoraControlsV1"),0));
    if(!ControlProfile||ControlProfile->SaveSchema!=1)
        ControlProfile=Cast<USoraControlSaveGame>(UGameplayStatics::CreateSaveGameObject(USoraControlSaveGame::StaticClass()));
    if(!ControlProfile) return;
    bRestoringControlProfile=true;
    SetGamepadDeadZones(FMath::IsFinite(ControlProfile->MoveDeadZone)?ControlProfile->MoveDeadZone:.18f,
        FMath::IsFinite(ControlProfile->LookDeadZone)?ControlProfile->LookDeadZone:.12f);
    SetGamepadLookSensitivity(FMath::IsFinite(ControlProfile->LookSensitivity)?ControlProfile->LookSensitivity:1.f);
    SetInvertedLook(ControlProfile->InvertedLook);
    const TArray<FSoraControlBinding> StoredBindings=ControlProfile->Bindings;
    ControlProfile->Bindings.Reset();
    // Fifteen approved combat actions can each have one keyboard, mouse, and pad key.
    // A malformed local save cannot replay an unbounded series of key-map edits.
    if(StoredBindings.Num()<=45) for(const FSoraControlBinding& Binding:StoredBindings)
    {
        if(ApplyCombatActionMapping(Binding.ActionName,Binding.Key,false))
            ControlProfile->Bindings.Add(Binding);
    }
    bRestoringControlProfile=false;
}
void ASoraCharacter::SaveControlProfile()
{
    if(ControlProfile&&!UGameplayStatics::SaveGameToSlot(ControlProfile,TEXT("SoraControlsV1"),0))
        UE_LOG(LogTemp,Warning,TEXT("SORA local control preferences could not be saved"));
}
void ASoraCharacter::SetupPlayerInputComponent(UInputComponent* I)
{
    Super::SetupPlayerInputComponent(I);
    LoadControlProfile();
    I->BindAxis(TEXT("MoveForward"),this,&ASoraCharacter::Forward); I->BindAxis(TEXT("MoveRight"),this,&ASoraCharacter::Strafe);
    I->BindAxis(TEXT("LookYaw"),this,&ASoraCharacter::Yaw); I->BindAxis(TEXT("LookPitch"),this,&ASoraCharacter::Pitch);
    I->BindAxis(TEXT("GamepadLookYaw"),this,&ASoraCharacter::GamepadYaw); I->BindAxis(TEXT("GamepadLookPitch"),this,&ASoraCharacter::GamepadPitch);
    I->BindAction(TEXT("Fire"),IE_Pressed,this,&ASoraCharacter::FireDown); I->BindAction(TEXT("Fire"),IE_Released,this,&ASoraCharacter::FireUp);
    I->BindAction(TEXT("Melee"),IE_Pressed,this,&ASoraCharacter::Melee); I->BindAction(TEXT("Jump"),IE_Pressed,this,&ASoraCharacter::JumpDown);
    I->BindAction(TEXT("Melee"),IE_Released,this,&ASoraCharacter::MeleeUp);
    I->BindAction(TEXT("Block"),IE_Pressed,this,&ASoraCharacter::BlockDown); I->BindAction(TEXT("Block"),IE_Released,this,&ASoraCharacter::BlockUp);
    I->BindAction(TEXT("Ability"),IE_Pressed,this,&ASoraCharacter::Ability);
    I->BindAction(TEXT("Jump"),IE_Released,this,&ASoraCharacter::JumpUp);
    I->BindAction(TEXT("Sprint"),IE_Pressed,this,&ASoraCharacter::SprintDown); I->BindAction(TEXT("Sprint"),IE_Released,this,&ASoraCharacter::SprintUp);
    I->BindAction(TEXT("Reload"),IE_Pressed,this,&ASoraCharacter::Reload); I->BindAction(TEXT("Interact"),IE_Pressed,this,&ASoraCharacter::Interact);
    I->BindAction(TEXT("Menu"),IE_Pressed,this,&ASoraCharacter::Menu); I->BindAction(TEXT("Enter"),IE_Pressed,this,&ASoraCharacter::Enter);
    I->BindAction(TEXT("Map"),IE_Pressed,this,&ASoraCharacter::NextMap); I->BindAction(TEXT("NewCampaign"),IE_Pressed,this,&ASoraCharacter::NewCampaign);
    I->BindAction(TEXT("ReturnCampaign"),IE_Pressed,this,&ASoraCharacter::ReturnCampaign);
    I->BindAction(TEXT("DeterministicPractice"),IE_Pressed,this,&ASoraCharacter::Practice);
    I->BindAction(TEXT("Subtitles"),IE_Pressed,this,&ASoraCharacter::Subtitles);
    I->BindAction(TEXT("PairWallet"),IE_Pressed,this,&ASoraCharacter::PairWallet); I->BindAction(TEXT("OpenWallet"),IE_Pressed,this,&ASoraCharacter::OpenWallet); I->BindAction(TEXT("DisconnectWallet"),IE_Pressed,this,&ASoraCharacter::DisconnectWallet);
    I->BindAction(TEXT("WeaponOne"),IE_Pressed,this,&ASoraCharacter::WeaponOne); I->BindAction(TEXT("WeaponTwo"),IE_Pressed,this,&ASoraCharacter::WeaponTwo); I->BindAction(TEXT("WeaponThree"),IE_Pressed,this,&ASoraCharacter::WeaponThree);
    I->BindAction(TEXT("WeaponFour"),IE_Pressed,this,&ASoraCharacter::WeaponFour); I->BindAction(TEXT("WeaponFive"),IE_Pressed,this,&ASoraCharacter::WeaponFive); I->BindAction(TEXT("WeaponSix"),IE_Pressed,this,&ASoraCharacter::WeaponSix);
    I->BindAction(TEXT("CampaignWeaponNext"),IE_Pressed,this,&ASoraCharacter::CampaignWeaponNext);
    I->BindAction(TEXT("ClassOne"),IE_Pressed,this,&ASoraCharacter::ClassOne); I->BindAction(TEXT("ClassTwo"),IE_Pressed,this,&ASoraCharacter::ClassTwo); I->BindAction(TEXT("ClassThree"),IE_Pressed,this,&ASoraCharacter::ClassThree);
    I->BindAction(TEXT("ClassFour"),IE_Pressed,this,&ASoraCharacter::ClassFour); I->BindAction(TEXT("ClassFive"),IE_Pressed,this,&ASoraCharacter::ClassFive); I->BindAction(TEXT("ClassSix"),IE_Pressed,this,&ASoraCharacter::ClassSix);
    I->BindAction(TEXT("ClassPrevious"),IE_Pressed,this,&ASoraCharacter::ClassPrevious); I->BindAction(TEXT("ClassNext"),IE_Pressed,this,&ASoraCharacter::ClassNext);
}
