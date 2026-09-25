#include "SoraPlayerCharacter.h"
#include "ArenaKernelSubsystem.h"
#include "ArenaWalletSubsystem.h"
#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraControlSaveGame.h"
#include "SoraEnemy.h"
#include "SoraEquipmentComponent.h"
#include "SoraGameEvents.h"
#include "SoraGameMode.h"
#include "SoraHistoricalArms.h"
#include "SoraInputStates.h"
#include "SoraViewmodelComponent.h"
#include "SoraWorldBuilder.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/InputComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PlayerInput.h"
#include "Kismet/GameplayStatics.h"

namespace
{
ASoraGameMode* PlayerGameMode(const UObject* Context) { return Cast<ASoraGameMode>(UGameplayStatics::GetGameMode(Context)); }
}

ASoraPlayerCharacter::ASoraPlayerCharacter(const FObjectInitializer& ObjectInitializer)
    : Super(ObjectInitializer.SetDefaultSubobjectClass<UCameraComponent>(ASoraCharacterBase::EyeComponentName))
{
    Camera=CastChecked<UCameraComponent>(GetEye());
    Camera->bUsePawnControlRotation=true; Camera->FieldOfView=94.f;
    // UE 5.8's native viewmodel projection keeps a readable weapon silhouette
    // while shrinking the actual primitive away from nearby world geometry.
    Camera->bEnableFirstPersonFieldOfView=true;
    Camera->bEnableFirstPersonScale=true;
    Camera->FirstPersonFieldOfView=70.f;
    Camera->FirstPersonScale=.6f;
    Equipment=CreateDefaultSubobject<USoraEquipmentComponent>(TEXT("Equipment"));
}
void ASoraPlayerCharacter::ResetLoadout() { Equipment->ResetForClass(); }
void ASoraPlayerCharacter::OnBodyRebuilt() { QuiverParts.Reset(); }
void ASoraPlayerCharacter::HaltActions() { Equipment->Halt(); }
void ASoraPlayerCharacter::SetDojoTraining(bool Enabled)
{
    const bool bChanged=bDojoTraining!=Enabled;
    bDojoTraining=Enabled;
    bDojoRecoveryPending=false;
    Equipment->DropStance();
    if(Enabled&&FSoraCatalog::Get().IsReady())
    {
        Equipment->Hold(FSoraCatalog::Get().Class(0).Weapons[0]);
        RebuildWeapon();
    }
    else if(bChanged) RebuildWeapon();
}
void ASoraPlayerCharacter::SetCampaignHeroLoadout(bool Enabled)
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
    Equipment->Hold(Hero.KatanaId);
    Equipment->AmmoByWeapon[Hero.YumiId]=Hero.QuiverArrows;
    RebuildWeapon();
    if(bChanged) { BuildHeroQuiver(); BuildHeroSaya(); }
}
void ASoraPlayerCharacter::SuspendDojoAction()
{
    if(bDojoTraining)
    {
        Equipment->GuardUp();
        bDojoRecoveryPending=false;
    }
}
void ASoraPlayerCharacter::SetKernelDriven(bool Enabled,const FSoraPracticeMap* Map)
{
    KernelHeldButtons=0; KernelQueuedButtons=0; InputForward=0; InputRight=0;
    Equipment->ReleaseTrigger(); Equipment->bReloading=false; bSprint=false;
    Super::SetKernelDriven(Enabled,Map);
}
void ASoraPlayerCharacter::OnKernelSnapshot(const FSoraPracticePlayer& State)
{
    Equipment->Ammo=State.Ammo; Equipment->bReloading=State.ReloadTicks>0;
}
FSoraPracticeInput ASoraPlayerCharacter::ConsumeKernelInput()
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
void ASoraPlayerCharacter::BuildHeroQuiver()
{
    // Nyaakoto's red-fletched quiver is visible on the world model, while
    // first-person arms and the camera remain clear of the back-mounted prop.
    // The authored Nyaakoto skeletal mesh carries its own open ebira and
    // red-fletched arrows. Keep the primitive quiver only as a missing-asset
    // fallback so a successful import does not draw a second one through it.
    if(!bCampaignHero||bSkeletalVisual) return;
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
void ASoraPlayerCharacter::BuildHeroSaya()
{
    if(!bCampaignHero) return;
    // The drawn first-person sword and its scabbard are separate static meshes.
    // Place the koiguchi forward at Nyaakoto's left hip, tip trailing behind;
    // the owner's first-person view sees only the unsheathed blade.
    UStaticMesh* Saya=LoadObject<UStaticMesh>(nullptr,
        TEXT("/Game/Generated/Meshes/SM_Nyaagyu_HeroSaya.SM_Nyaagyu_HeroSaya"));
    if(!Saya) return;
    auto* Mesh=NewObject<UStaticMeshComponent>(this,MakeUniqueObjectName(
        this,UStaticMeshComponent::StaticClass(),TEXT("NyaakotoHeroSaya")));
    Mesh->SetStaticMesh(Saya);
    Mesh->SetupAttachment(GetMesh());
    Mesh->SetRelativeLocation(FVector(17,-25,95));
    Mesh->SetRelativeRotation(FRotator(0,180,0));
    Mesh->SetRelativeScale3D(FVector(.90));
    Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Mesh->SetOwnerNoSee(true);
    Mesh->RegisterComponent(); AddInstanceComponent(Mesh);
    BodyParts.Add(Mesh); QuiverParts.Add(Mesh);
}
void ASoraPlayerCharacter::TickPlay(float Dt)
{
    if(!bDojoTraining) Equipment->TickGuard(Dt);
    if(bDojoTraining) TickDojoLessons();
    Equipment->TickWeapon();
    GetCharacterMovement()->MaxWalkSpeed=FSoraCatalog::Get().Class(ClassId).Speed*Equipment->MoveScale(bSprint);
    const float Moving=FMath::Clamp(GetVelocity().Size2D()/500.f,0.f,1.f);
    Viewmodel->Sway(LifeTime,Moving,
        Equipment->bReloading?-30.f:Equipment->IsCommittedStrike()?25.f:Equipment->IsBowDrawing()?-15.f:0.f,
        bSprint?-15.f:0.f);
}
void ASoraPlayerCharacter::TickDojoLessons()
{
    auto* G=PlayerGameMode(this);
    if(!G) return;
    USoraCampaignDirector* Campaign=G->Campaign();
    const float Now=GetWorld()->GetTimeSeconds();
    if(Equipment->IsGuardHeld()&&Campaign->DojoLessonStage()==0)
        Campaign->RecordDojoLesson(SoraDojoRules::EAction::Stance,
            FMath::RoundToInt((Now-Equipment->GuardPressedAt())*1000.f));
    if(bDojoRecoveryPending&&Now>=DojoRecoveryEndsAt&&!Equipment->IsTriggerHeld())
    {
        if(Campaign->RecordDojoLesson(SoraDojoRules::EAction::Recovery,
            FMath::RoundToInt((Now-DojoRecoveryStartedAt)*1000.f),true,DojoRecoveryRequiredMs))
            bDojoRecoveryPending=false;
    }
}
void ASoraPlayerCharacter::NoteDojoSwing(float StartedAt,float RecoveredAt,float CooldownSeconds)
{
    if(const auto* G=PlayerGameMode(this))
    {
        if(G->Campaign()->DojoLessonStage()==3)
        {
            bDojoRecoveryPending=true;
            DojoRecoveryStartedAt=StartedAt;
            DojoRecoveryEndsAt=RecoveredAt;
            DojoRecoveryRequiredMs=FMath::CeilToInt(CooldownSeconds*1000.f);
        }
    }
}
bool ASoraPlayerCharacter::AdmitDamage(float& Damage,AActor* Causer)
{
    USoraGameEvents* Events=USoraGameEvents::Get(this);
    const int32 WeaponInHand=WeaponId;
    if(bDojoTraining&&Equipment->IsGuardHeld())
    {
        if(const auto* Pupil=Cast<ASoraEnemy>(Causer)) if(Pupil->IsDojoPupil())
        {
            const FVector ToAttacker=(Pupil->GetActorLocation()-GetActorLocation()).GetSafeNormal2D();
            const bool bFacing=FVector::DotProduct(GetActorForwardVector(),ToAttacker)>=.25f;
            if(bFacing)
            {
                const int32 HeldMs=FMath::RoundToInt((GetWorld()->GetTimeSeconds()-Equipment->GuardPressedAt())*1000.f);
                if(auto* G=PlayerGameMode(this))
                {
                    if(G->Campaign()->DojoLessonStage()==2)
                        G->Campaign()->RecordDojoLesson(SoraDojoRules::EAction::Parry,HeldMs,true);
                    else if(G->Campaign()->DojoLessonStage()==1)
                        G->Campaign()->RecordDojoLesson(SoraDojoRules::EAction::Guard,HeldMs,true);
                }
                if(Events)
                {
                    FSoraDefenseEvent Guarded;
                    Guarded.Defender=this; Guarded.Attacker=Causer; Guarded.HeldMs=HeldMs; Guarded.bDojo=true;
                    Events->OnGuarded.Broadcast(Guarded);
                }
                return false;
            }
        }
    }
    if(!bDojoTraining&&bCampaignHero&&Equipment->IsGuardHeld()&&!Equipment->IsCommittedStrike()&&
        (WeaponInHand==0||WeaponInHand==19||WeaponInHand==20))
    {
        if(auto* Retainer=Cast<ASoraEnemy>(Causer); Retainer&&Retainer->IsBladeRetainer())
        {
            const FVector ToAttacker=(Retainer->GetActorLocation()-GetActorLocation()).GetSafeNormal2D();
            const float Facing=FVector::DotProduct(GetActorForwardVector(),ToAttacker);
            const int32 HeldMs=FMath::RoundToInt((GetWorld()->GetTimeSeconds()-Equipment->GuardPressedAt())*1000.f);
            FSoraDefenseEvent Defense;
            Defense.Defender=this; Defense.Attacker=Causer; Defense.HeldMs=HeldMs;
            switch(SoraHistoricalArms::DefendBlade(true,Facing,HeldMs,Equipment->GuardReserve()))
            {
            case SoraHistoricalArms::EDefense::Parry:
                Equipment->SpendGuard(18.f);
                Retainer->DelayNextAttack(.65f);
                if(Events) Events->OnParried.Broadcast(Defense);
                return false;
            case SoraHistoricalArms::EDefense::Guard:
                Equipment->SpendGuard(30.f);
                Damage*=.25f;
                Defense.Damage=Damage;
                if(Events) Events->OnGuarded.Broadcast(Defense);
                break;
            case SoraHistoricalArms::EDefense::Exposed: break;
            }
        }
    }
    return true;
}
void ASoraPlayerCharacter::OnDefeated(AActor* Causer)
{
    if(bDojoTraining) Health=1.f;
    Equipment->ReleaseTrigger();
    if(auto* G=PlayerGameMode(this)) G->Campaign()->PlayerKilled();
}
void ASoraPlayerCharacter::Forward(float V) { if(bKernelDriven) { InputForward=V; return; } if(CanPlay()) AddMovementInput(GetActorForwardVector(),V); }
void ASoraPlayerCharacter::Strafe(float V) { if(bKernelDriven) { InputRight=V; return; } if(CanPlay()) AddMovementInput(GetActorRightVector(),V); }
void ASoraPlayerCharacter::Yaw(float V) { if(CanPlay()) AddControllerYawInput(V); }
void ASoraPlayerCharacter::Pitch(float V) { if(CanPlay()) AddControllerPitchInput(bInvertedLook?-V:V); }
void ASoraPlayerCharacter::GamepadYaw(float V)
{
    if(CanPlay()) AddControllerYawInput(FMath::Clamp(V,-1.f,1.f)*90.f*GamepadLookSensitivity*GetWorld()->GetDeltaSeconds());
}
void ASoraPlayerCharacter::GamepadPitch(float V)
{
    if(CanPlay()) AddControllerPitchInput(FMath::Clamp(V,-1.f,1.f)*70.f*GamepadLookSensitivity*GetWorld()->GetDeltaSeconds()*(bInvertedLook?-1.f:1.f));
}
void ASoraPlayerCharacter::FireDown()
{
    // Input can arrive while the title/menu is open. Never carry a held trigger
    // into resumed combat if it was first pressed outside gameplay.
    if(!CanPlay()) return;
    if(bKernelDriven) { KernelHeldButtons|=1; return; }
    Equipment->TriggerDown();
}
void ASoraPlayerCharacter::FireUp() { KernelHeldButtons&=~1u; Equipment->TriggerUp(); }
void ASoraPlayerCharacter::SprintDown() { if(CanPlay()&&!Equipment->IsCommittedStrike()&&!Equipment->IsBowDrawing()) bSprint=true; }
void ASoraPlayerCharacter::SprintUp() { bSprint=false; }
void ASoraPlayerCharacter::JumpDown()
{
    if(bKernelDriven) { if(CanPlay()) KernelQueuedButtons|=8; return; }
    if(CanPlay()&&!Equipment->IsCommittedStrike()&&!Equipment->IsBowDrawing()) Jump();
}
void ASoraPlayerCharacter::JumpUp() { StopJumping(); }
void ASoraPlayerCharacter::Melee()
{
    if(bKernelDriven) { if(CanPlay()) KernelHeldButtons|=2; return; }
    Equipment->Melee();
}
void ASoraPlayerCharacter::Reload()
{
    if(bKernelDriven) { if(CanPlay()) KernelQueuedButtons|=32; return; }
    Equipment->Reload();
}
void ASoraPlayerCharacter::Interact() { if(CanPlay()) if(auto* G=PlayerGameMode(this)) G->Interact(this); }
void ASoraPlayerCharacter::Menu()
{
    if(auto* G=PlayerGameMode(this))
    {
        G->ToggleMenu();
        if(G->bMenu) { FireUp(); MeleeUp(); BlockUp(); SprintUp(); JumpUp(); }
    }
}
void ASoraPlayerCharacter::Enter() { if(auto* G=PlayerGameMode(this)) G->BeginRound(); }
void ASoraPlayerCharacter::NextMap() { if(auto* G=PlayerGameMode(this)) G->NextMap(); }
void ASoraPlayerCharacter::NewCampaign() { if(auto* G=PlayerGameMode(this)) G->NewCampaign(); }
void ASoraPlayerCharacter::ReturnCampaign() { if(auto* G=PlayerGameMode(this)) G->ReturnCampaign(); }
void ASoraPlayerCharacter::Practice() { if(auto* G=PlayerGameMode(this)) G->DeterministicPractice(); }
void ASoraPlayerCharacter::BlockDown()
{
    if(!CanPlay()) return;
    if(bKernelDriven) { KernelHeldButtons|=4; return; }
    Equipment->GuardDown(bDojoTraining,bCampaignHero);
}
void ASoraPlayerCharacter::BlockUp() { KernelHeldButtons&=~4u; Equipment->GuardUp(); }
void ASoraPlayerCharacter::Ability() { if(bKernelDriven&&CanPlay()) KernelQueuedButtons|=16; }
void ASoraPlayerCharacter::MeleeUp() { KernelHeldButtons&=~2u; }
void ASoraPlayerCharacter::Subtitles() { if(auto* G=PlayerGameMode(this)) G->ToggleSubtitles(); }
void ASoraPlayerCharacter::PairWallet()
{
    const auto* G=PlayerGameMode(this); if(!G||!G->bMenu) return;
    if(auto* Wallet=GetGameInstance()->GetSubsystem<UArenaWalletSubsystem>())
        if(Wallet->State==EArenaWalletState::Idle||Wallet->State==EArenaWalletState::Disconnected||Wallet->State==EArenaWalletState::Unavailable||Wallet->State==EArenaWalletState::Error)
            Wallet->BeginPairingFromConfig();
}
void ASoraPlayerCharacter::OpenWallet()
{
    const auto* G=PlayerGameMode(this); if(!G||!G->bMenu) return;
    if(auto* Wallet=GetGameInstance()->GetSubsystem<UArenaWalletSubsystem>()) if(Wallet->State==EArenaWalletState::AwaitingApproval) Wallet->LaunchWallet();
}
void ASoraPlayerCharacter::DisconnectWallet()
{
    const auto* G=PlayerGameMode(this); if(!G||!G->bMenu) return;
    if(auto* Wallet=GetGameInstance()->GetSubsystem<UArenaWalletSubsystem>()) Wallet->DisconnectWallet();
}
void ASoraPlayerCharacter::ChooseClass(int32 Id) { if(auto* G=PlayerGameMode(this)) G->SelectClass(Id); }
void ASoraPlayerCharacter::Equip(int32 Slot)
{
    if(bKernelDriven) { if(auto* G=PlayerGameMode(this)) G->SelectPracticeWeapon(Slot); return; }
    if(!CanPlay()) return;
    Equipment->EquipClassSlot(Slot);
}
void ASoraPlayerCharacter::WeaponOne(){Equip(1);} void ASoraPlayerCharacter::WeaponTwo(){Equip(0);} void ASoraPlayerCharacter::WeaponThree(){Equip(2);}
void ASoraPlayerCharacter::EquipCampaignWeapon(int32 NewWeaponId)
{
    const auto* G=PlayerGameMode(this);
    if(!G||!G->bCampaign||G->Campaign()->ChapterId==0||bKernelDriven||bDojoTraining||
        !CanPlay()||NewWeaponId<18||NewWeaponId>20||ClassId!=0) return;
    Equipment->EquipCampaignWeapon(NewWeaponId);
}
void ASoraPlayerCharacter::WeaponFour(){EquipCampaignWeapon(18);}
void ASoraPlayerCharacter::WeaponFive(){EquipCampaignWeapon(19);}
void ASoraPlayerCharacter::WeaponSix(){EquipCampaignWeapon(20);}
void ASoraPlayerCharacter::CampaignWeaponNext()
{
    EquipCampaignWeapon(WeaponId>=18&&WeaponId<20?WeaponId+1:18);
}
void ASoraPlayerCharacter::ClassOne(){ChooseClass(0);} void ASoraPlayerCharacter::ClassTwo(){ChooseClass(1);} void ASoraPlayerCharacter::ClassThree(){ChooseClass(2);}
void ASoraPlayerCharacter::ClassFour(){ChooseClass(3);} void ASoraPlayerCharacter::ClassFive(){ChooseClass(4);} void ASoraPlayerCharacter::ClassSix(){ChooseClass(5);}
void ASoraPlayerCharacter::ClassPrevious()
{
    if(auto* G=PlayerGameMode(this)) if(G->bMenu) ChooseClass((G->SelectedClass+5)%6);
}
void ASoraPlayerCharacter::ClassNext()
{
    if(auto* G=PlayerGameMode(this)) if(G->bMenu) ChooseClass((G->SelectedClass+1)%6);
}
TArray<FKey> ASoraPlayerCharacter::GetActionKeys(FName ActionName) const
{
    TArray<FKey> Keys;
    const auto* PC=Cast<APlayerController>(GetController());
    if(!PC||!PC->PlayerInput) return Keys;
    for(const FInputActionKeyMapping& Mapping:PC->PlayerInput->GetKeysForAction(ActionName)) Keys.AddUnique(Mapping.Key);
    return Keys;
}
bool ASoraPlayerCharacter::RemapCombatAction(FName ActionName,FKey NewKey)
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
bool ASoraPlayerCharacter::ApplyCombatActionMapping(FName ActionName,FKey NewKey,bool bRequireMenu)
{
    // Never permit wallet, menu, or campaign commands to be rebound by combat UI.
    static const TSet<FName> Allowed={
        TEXT("Fire"),TEXT("Melee"),TEXT("Jump"),TEXT("Sprint"),TEXT("Reload"),TEXT("Interact"),
        TEXT("Block"),TEXT("Ability"),TEXT("WeaponOne"),TEXT("WeaponTwo"),TEXT("WeaponThree"),
        TEXT("WeaponFour"),TEXT("WeaponFive"),TEXT("WeaponSix"),TEXT("CampaignWeaponNext")};
    const auto* G=PlayerGameMode(this);
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
void ASoraPlayerCharacter::SetGamepadDeadZones(float MoveDeadZone,float LookDeadZone)
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
void ASoraPlayerCharacter::SetGamepadLookSensitivity(float Sensitivity)
{
    if(!FMath::IsFinite(Sensitivity)) return;
    GamepadLookSensitivity=FMath::Clamp(Sensitivity,.25f,3.f);
    if(ControlProfile&&!bRestoringControlProfile)
    {
        ControlProfile->LookSensitivity=GamepadLookSensitivity;
        SaveControlProfile();
    }
}
void ASoraPlayerCharacter::SetInvertedLook(bool Enabled)
{
    bInvertedLook=Enabled;
    if(ControlProfile&&!bRestoringControlProfile)
    {
        ControlProfile->InvertedLook=Enabled;
        SaveControlProfile();
    }
}
void ASoraPlayerCharacter::LoadControlProfile()
{
    // The game mode names the slot. Without one the defaults apply and nothing is saved.
    const auto* G=PlayerGameMode(this);
    ControlSlot=G?G->ControlSlotName:FString();
    ControlProfile=ControlSlot.IsEmpty()?nullptr:Cast<USoraControlSaveGame>(UGameplayStatics::LoadGameFromSlot(ControlSlot,0));
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
void ASoraPlayerCharacter::SaveControlProfile()
{
    if(ControlProfile&&!ControlSlot.IsEmpty()&&!UGameplayStatics::SaveGameToSlot(ControlProfile,ControlSlot,0))
        UE_LOG(LogTemp,Warning,TEXT("SORA local control preferences could not be saved"));
}
bool ASoraPlayerCharacter::AcceptsInput(uint8 States)
{
    const auto* G=PlayerGameMode(this);
    if(!G) return false;
    // Every press in one input frame is judged by the state that frame began
    // in, so the key that closes the menu or title card never also acts in play.
    if(InputFrame!=GFrameCounter) { InputFrame=GFrameCounter; InputFrameState=G->InputState(); }
    return (States&InputFrameState)!=0;
}
void ASoraPlayerCharacter::BindPress(UInputComponent* Input,const TCHAR* Action,void (ASoraPlayerCharacter::*Handler)())
{
    const uint8 States=SoraInput::StatesFor(Action);
    FInputActionBinding Binding(Action,IE_Pressed);
    // Menu actions must keep working while the open menu pauses the world.
    Binding.bExecuteWhenPaused=(States&(SoraInput::Menu|SoraInput::Confirm))!=0;
    Binding.ActionDelegate.GetDelegateForManualSet().BindWeakLambda(this,[this,States,Handler]()
    {
        if(AcceptsInput(States)) (this->*Handler)();
    });
    Input->AddActionBinding(MoveTemp(Binding));
}
void ASoraPlayerCharacter::BindRelease(UInputComponent* Input,const TCHAR* Action,void (ASoraPlayerCharacter::*Handler)())
{
    // A release only clears held state, so it is honoured in every state.
    FInputActionBinding Binding(Action,IE_Released);
    Binding.bExecuteWhenPaused=true;
    Binding.ActionDelegate.BindDelegate(this,Handler);
    Input->AddActionBinding(MoveTemp(Binding));
}
void ASoraPlayerCharacter::SetupPlayerInputComponent(UInputComponent* I)
{
    Super::SetupPlayerInputComponent(I);
    LoadControlProfile();
    I->BindAxis(TEXT("MoveForward"),this,&ASoraPlayerCharacter::Forward); I->BindAxis(TEXT("MoveRight"),this,&ASoraPlayerCharacter::Strafe);
    I->BindAxis(TEXT("LookYaw"),this,&ASoraPlayerCharacter::Yaw); I->BindAxis(TEXT("LookPitch"),this,&ASoraPlayerCharacter::Pitch);
    I->BindAxis(TEXT("GamepadLookYaw"),this,&ASoraPlayerCharacter::GamepadYaw); I->BindAxis(TEXT("GamepadLookPitch"),this,&ASoraPlayerCharacter::GamepadPitch);
    // Presses act only in the states SoraInputStates.h lists for them, so keys
    // shared by a menu action and a combat action never trigger both.
    BindPress(I,TEXT("Fire"),&ASoraPlayerCharacter::FireDown); BindRelease(I,TEXT("Fire"),&ASoraPlayerCharacter::FireUp);
    BindPress(I,TEXT("Melee"),&ASoraPlayerCharacter::Melee); BindRelease(I,TEXT("Melee"),&ASoraPlayerCharacter::MeleeUp);
    BindPress(I,TEXT("Jump"),&ASoraPlayerCharacter::JumpDown); BindRelease(I,TEXT("Jump"),&ASoraPlayerCharacter::JumpUp);
    BindPress(I,TEXT("Block"),&ASoraPlayerCharacter::BlockDown); BindRelease(I,TEXT("Block"),&ASoraPlayerCharacter::BlockUp);
    BindPress(I,TEXT("Ability"),&ASoraPlayerCharacter::Ability);
    BindPress(I,TEXT("Sprint"),&ASoraPlayerCharacter::SprintDown); BindRelease(I,TEXT("Sprint"),&ASoraPlayerCharacter::SprintUp);
    BindPress(I,TEXT("Reload"),&ASoraPlayerCharacter::Reload); BindPress(I,TEXT("Interact"),&ASoraPlayerCharacter::Interact);
    BindPress(I,TEXT("Menu"),&ASoraPlayerCharacter::Menu); BindPress(I,TEXT("Enter"),&ASoraPlayerCharacter::Enter);
    BindPress(I,TEXT("Map"),&ASoraPlayerCharacter::NextMap); BindPress(I,TEXT("NewCampaign"),&ASoraPlayerCharacter::NewCampaign);
    BindPress(I,TEXT("ReturnCampaign"),&ASoraPlayerCharacter::ReturnCampaign);
    BindPress(I,TEXT("DeterministicPractice"),&ASoraPlayerCharacter::Practice);
    BindPress(I,TEXT("Subtitles"),&ASoraPlayerCharacter::Subtitles);
    BindPress(I,TEXT("PairWallet"),&ASoraPlayerCharacter::PairWallet); BindPress(I,TEXT("OpenWallet"),&ASoraPlayerCharacter::OpenWallet); BindPress(I,TEXT("DisconnectWallet"),&ASoraPlayerCharacter::DisconnectWallet);
    BindPress(I,TEXT("WeaponOne"),&ASoraPlayerCharacter::WeaponOne); BindPress(I,TEXT("WeaponTwo"),&ASoraPlayerCharacter::WeaponTwo); BindPress(I,TEXT("WeaponThree"),&ASoraPlayerCharacter::WeaponThree);
    BindPress(I,TEXT("WeaponFour"),&ASoraPlayerCharacter::WeaponFour); BindPress(I,TEXT("WeaponFive"),&ASoraPlayerCharacter::WeaponFive); BindPress(I,TEXT("WeaponSix"),&ASoraPlayerCharacter::WeaponSix);
    BindPress(I,TEXT("CampaignWeaponNext"),&ASoraPlayerCharacter::CampaignWeaponNext);
    BindPress(I,TEXT("ClassOne"),&ASoraPlayerCharacter::ClassOne); BindPress(I,TEXT("ClassTwo"),&ASoraPlayerCharacter::ClassTwo); BindPress(I,TEXT("ClassThree"),&ASoraPlayerCharacter::ClassThree);
    BindPress(I,TEXT("ClassFour"),&ASoraPlayerCharacter::ClassFour); BindPress(I,TEXT("ClassFive"),&ASoraPlayerCharacter::ClassFive); BindPress(I,TEXT("ClassSix"),&ASoraPlayerCharacter::ClassSix);
    BindPress(I,TEXT("ClassPrevious"),&ASoraPlayerCharacter::ClassPrevious); BindPress(I,TEXT("ClassNext"),&ASoraPlayerCharacter::ClassNext);
}
