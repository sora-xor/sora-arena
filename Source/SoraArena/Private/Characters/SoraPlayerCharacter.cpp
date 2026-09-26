#include "SoraPlayerCharacter.h"
#include "ArenaKernelSubsystem.h"
#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraControlSaveGame.h"
#include "Combat/SoraDefense.h"
#include "Combat/SoraStealth.h"
#include "SoraEquipmentComponent.h"
#include "SoraGameEvents.h"
#include "SoraGameMode.h"
#include "SoraHistoricalArms.h"
#include "SoraInputStates.h"
#include "SoraSettings.h"
#include "SoraViewmodelComponent.h"
#include "SoraWorldBuilder.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/InputComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PlayerInput.h"
#include "Kismet/GameplayStatics.h"

namespace
{
ASoraGameMode* PlayerGameMode(const UObject* Context) { return Cast<ASoraGameMode>(UGameplayStatics::GetGameMode(Context)); }
// The eye above the capsule's centre standing and crouched; a crouched
// capsule of 88 cm passes the ch03 culvert.
constexpr float StandingEyeZ=64.f, CrouchedEyeZ=40.f, CrouchedHalfHeight=44.f;
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
    GetCharacterMovement()->GetNavAgentPropertiesRef().bCanCrouch=true;
    GetCharacterMovement()->SetCrouchedHalfHeight(CrouchedHalfHeight);
    GetCharacterMovement()->bCanWalkOffLedgesWhenCrouching=true;
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
    // Kernel practice has no crouch.
    if(IsCrouched()) UnCrouch();
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
    const USoraStealth* Stealth=USoraStealth::Get(this);
    GetCharacterMovement()->MaxWalkSpeed=FSoraCatalog::Get().Class(ClassId).Speed*Equipment->MoveScale(bSprint)*(Stealth?Stealth->HeroMoveScale():1.f);
    GetCharacterMovement()->MaxWalkSpeedCrouched=GetCharacterMovement()->MaxWalkSpeed*SoraStealthRules::CrouchSpeedPermille/1000.f;
    // A sprint stands the hero up; the eye settles to his stance.
    if(bSprint&&GetCharacterMovement()->bWantsToCrouch) UnCrouch();
    Eye->SetRelativeLocation(FVector(4.f,0.f,FMath::FInterpTo(Eye->GetRelativeLocation().Z,IsCrouched()?CrouchedEyeZ:StandingEyeZ,Dt,12.f)));
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
bool ASoraPlayerCharacter::AdmitDamage(float& Damage,FSoraHit& Hit,AActor* Causer)
{
    return SoraDefense::AdmitHero(*this,Damage,Hit,Causer);
}
void ASoraPlayerCharacter::OnStartCrouch(float HalfHeightAdjust,float ScaledHalfHeightAdjust)
{
    Super::OnStartCrouch(HalfHeightAdjust,ScaledHalfHeightAdjust);
    // The capsule's centre drops: the body keeps its feet on the floor and the
    // eye starts where it was before TickPlay settles it lower.
    GetMesh()->SetRelativeLocation(FVector(0.f,0.f,-88.f+HalfHeightAdjust));
    Eye->AddRelativeLocation(FVector(0.f,0.f,HalfHeightAdjust));
}
void ASoraPlayerCharacter::OnEndCrouch(float HalfHeightAdjust,float ScaledHalfHeightAdjust)
{
    Super::OnEndCrouch(HalfHeightAdjust,ScaledHalfHeightAdjust);
    GetMesh()->SetRelativeLocation(FVector(0.f,0.f,-88.f));
    Eye->AddRelativeLocation(FVector(0.f,0.f,-HalfHeightAdjust));
}
void ASoraPlayerCharacter::OnDefeated(AActor* Causer)
{
    if(bDojoTraining) Health=1.f;
    Equipment->ReleaseTrigger();
    if(auto* G=PlayerGameMode(this)) G->Campaign()->PlayerKilled();
}
void ASoraPlayerCharacter::Forward(float V) { if(bKernelDriven) { InputForward=V; return; } if(CanPlay()) AddMovementInput(GetActorForwardVector(),V); }
void ASoraPlayerCharacter::Strafe(float V) { if(bKernelDriven) { InputRight=V; return; } if(CanPlay()) AddMovementInput(GetActorRightVector(),V); }
void ASoraPlayerCharacter::Yaw(float V) { if(CanPlay()) AddControllerYawInput(V*MouseSensitivity); }
void ASoraPlayerCharacter::Pitch(float V) { if(CanPlay()) AddControllerPitchInput((bInvertedLook?-V:V)*MouseSensitivity); }
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
    if(const USoraStealth* Stealth=USoraStealth::Get(this); Stealth&&Stealth->IsHeroBusy()) return;
    // A held sprint blocks the trigger until released; a toggled one ends here.
    if(TogglesSprint()) bSprint=false;
    Equipment->TriggerDown();
}
void ASoraPlayerCharacter::FireUp() { KernelHeldButtons&=~1u; Equipment->TriggerUp(); }
void ASoraPlayerCharacter::SprintDown()
{
    // With the toggle setting, a second press ends the sprint.
    if(TogglesSprint()&&bSprint) { bSprint=false; return; }
    if(CanPlay()&&!Equipment->IsCommittedStrike()&&!Equipment->IsBowDrawing()) bSprint=true;
}
void ASoraPlayerCharacter::SprintUp() { bSprint=false; }
void ASoraPlayerCharacter::SprintReleased() { if(!TogglesSprint()) SprintUp(); }
void ASoraPlayerCharacter::JumpDown()
{
    if(bKernelDriven) { if(CanPlay()) KernelQueuedButtons|=8; return; }
    // Left or Right with Jump inside a 転 window rolls to the opponent's flank instead.
    if(CanPlay()&&SoraDefense::Marobashi(*this,GetInputAxisValue(TEXT("MoveRight")))) return;
    if(CanPlay()&&!Equipment->IsCommittedStrike()&&!Equipment->IsBowDrawing()&&!Equipment->IsStepping()) Jump();
}
void ASoraPlayerCharacter::JumpUp() { StopJumping(); }
void ASoraPlayerCharacter::Melee()
{
    if(bKernelDriven) { if(CanPlay()) KernelHeldButtons|=2; return; }
    // Behind an unsuspecting guard the press is a rear takedown instead of a strike.
    if(USoraStealth* Stealth=USoraStealth::Get(this); Stealth&&Stealth->BeginTakedown(*this)) return;
    Equipment->Melee();
}
void ASoraPlayerCharacter::Reload()
{
    if(bKernelDriven) { if(CanPlay()) KernelQueuedButtons|=32; return; }
    Equipment->Reload();
}
void ASoraPlayerCharacter::Interact()
{
    if(!CanPlay()) return;
    // Held at a body in a stealth zone, Interact drags it.
    if(USoraStealth* Stealth=USoraStealth::Get(this); Stealth&&Stealth->BeginDrag(*this)) return;
    if(auto* G=PlayerGameMode(this)) G->Interact(this);
}
void ASoraPlayerCharacter::InteractUp() { if(USoraStealth* Stealth=USoraStealth::Get(this)) Stealth->EndDrag(); }
void ASoraPlayerCharacter::CrouchPressed()
{
    if(bKernelDriven||!CanPlay()) return;
    // The wish, not the stance: under a low ceiling the stand waits for headroom.
    if(GetCharacterMovement()->bWantsToCrouch) { UnCrouch(); return; }
    bSprint=false; Crouch();
}
void ASoraPlayerCharacter::SheathePressed()
{
    if(bKernelDriven||!CanPlay()) return;
    if(const USoraStealth* Stealth=USoraStealth::Get(this); Stealth&&Stealth->IsHeroBusy()) return;
    Equipment->Sheathe(!Equipment->IsSheathing());
}
void ASoraPlayerCharacter::Menu()
{
    if(auto* G=PlayerGameMode(this))
    {
        G->OpenPauseMenu();
        // The front end now holds input, so no held action outlives the pause.
        if(G->bMenu) { FireUp(); MeleeUp(); BlockUp(); SprintUp(); JumpUp(); }
    }
}
void ASoraPlayerCharacter::Enter() { if(auto* G=PlayerGameMode(this)) G->BeginRound(); }
void ASoraPlayerCharacter::BlockDown()
{
    if(!CanPlay()) return;
    // With the toggle setting, a second press lowers the guard.
    if(TogglesGuard()&&IsGuarding()) { BlockUp(); return; }
    if(bKernelDriven) { KernelHeldButtons|=4; return; }
    Equipment->GuardDown(bDojoTraining,bCampaignHero);
}
void ASoraPlayerCharacter::BlockUp() { KernelHeldButtons&=~4u; Equipment->GuardUp(); }
void ASoraPlayerCharacter::BlockReleased() { if(!TogglesGuard()) BlockUp(); }
bool ASoraPlayerCharacter::IsGuarding() const { return bKernelDriven?(KernelHeldButtons&4u)!=0:Equipment->IsGuardHeld(); }
bool ASoraPlayerCharacter::TogglesGuard() const
{
    const auto* G=PlayerGameMode(this);
    return G&&G->Settings()&&G->Settings()->ToggleGuard();
}
bool ASoraPlayerCharacter::TogglesSprint() const
{
    const auto* G=PlayerGameMode(this);
    return G&&G->Settings()&&G->Settings()->ToggleSprint();
}
void ASoraPlayerCharacter::Ability() { if(bKernelDriven&&CanPlay()) KernelQueuedButtons|=16; }
void ASoraPlayerCharacter::MeleeUp()
{
    KernelHeldButtons&=~2u;
    // A takedown decided by a tap rather than a hold.
    if(USoraStealth* Stealth=USoraStealth::Get(this)) Stealth->ReleaseTakedown();
}
void ASoraPlayerCharacter::Subtitles() { if(auto* G=PlayerGameMode(this)) G->ToggleSubtitles(); }
void ASoraPlayerCharacter::ScoreboardDown() { bScoreboardHeld=true; }
void ASoraPlayerCharacter::ScoreboardUp() { bScoreboardHeld=false; }
void ASoraPlayerCharacter::Equip(int32 Slot)
{
    // Practice enters with the loadout chosen in the lobby; the kernel holds it.
    if(bKernelDriven||!CanPlay()) return;
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
TArray<FKey> ASoraPlayerCharacter::GetActionKeys(FName ActionName) const
{
    TArray<FKey> Keys;
    const auto* PC=Cast<APlayerController>(GetController());
    if(!PC||!PC->PlayerInput) return Keys;
    for(const FInputActionKeyMapping& Mapping:PC->PlayerInput->GetKeysForAction(ActionName)) Keys.AddUnique(Mapping.Key);
    return Keys;
}
namespace
{
// A stick pushed in a direction also reports as a button, but its axes
// already move and aim.
bool IsStickDirection(const FKey& Key)
{
    return Key==EKeys::Gamepad_LeftStick_Up||Key==EKeys::Gamepad_LeftStick_Down||Key==EKeys::Gamepad_LeftStick_Left||
        Key==EKeys::Gamepad_LeftStick_Right||Key==EKeys::Gamepad_RightStick_Up||Key==EKeys::Gamepad_RightStick_Down||
        Key==EKeys::Gamepad_RightStick_Left||Key==EKeys::Gamepad_RightStick_Right;
}
int32 AxisDirection(const FInputAxisKeyMapping& Mapping) { return Mapping.Scale>0.f?1:Mapping.Scale<0.f?-1:0; }
bool IsControlMapping(const SoraInput::FRemappable& Control,const FInputAxisKeyMapping& Mapping)
{
    return Control.Axis!=0&&Mapping.AxisName==FName(Control.Name)&&AxisDirection(Mapping)==Control.Axis;
}
// The remap's own checks, before any other control is consulted: a button
// or key in the control's slot. Movement halves take keyboard keys only.
ESoraRemapResult CheckKey(const SoraInput::FRemappable& Control,const FKey& Key)
{
    if(!Key.IsValid()||!Key.IsBindableToActions()||Key==EKeys::AnyKey||Key.IsAxis1D()||Key.IsAxis2D()||Key.IsAxis3D()||
        Key.IsTouch()||Key.IsGesture()||IsStickDirection(Key))
        return ESoraRemapResult::Unbindable;
    if(Control.Axis!=0&&(Key.IsGamepadKey()||Key.IsMouseButton())) return ESoraRemapResult::WrongDevice;
    return ESoraRemapResult::Done;
}
// Another mapping on Key that can act in one of the control's states. Keys
// shared only across disjoint states (pad A: Enter on cards and results,
// Jump in play) are allowed, as check_input_conflicts.py allows them.
bool FindConflict(const UPlayerInput& Input,const SoraInput::FRemappable& Control,const FKey& Key,FName& Other,int32& OtherAxis)
{
    const FName Name(Control.Name);
    const uint8 States=SoraInput::StatesFor(Control.Name);
    for(const FInputActionKeyMapping& Mapping:Input.ActionMappings)
        if(Mapping.Key==Key&&!(Control.Axis==0&&Mapping.ActionName==Name)&&(SoraInput::StatesFor(*Mapping.ActionName.ToString())&States)!=0)
        { Other=Mapping.ActionName; OtherAxis=0; return true; }
    for(const FInputAxisKeyMapping& Mapping:Input.AxisMappings)
        if(Mapping.Key==Key&&!IsControlMapping(Control,Mapping)&&(SoraInput::StatesFor(*Mapping.AxisName.ToString())&States)!=0)
        { Other=Mapping.AxisName; OtherAxis=AxisDirection(Mapping); return true; }
    return false;
}
// Replaces the control's key in NewKey's slot, without any check.
void BindSlot(UPlayerInput& Input,const SoraInput::FRemappable& Control,const FKey& NewKey)
{
    const FName Name(Control.Name);
    const bool bPad=NewKey.IsGamepadKey();
    if(Control.Axis==0)
    {
        const TArray<FInputActionKeyMapping> Existing=Input.GetKeysForAction(Name);
        for(const FInputActionKeyMapping& Mapping:Existing)
            if(Mapping.Key.IsGamepadKey()==bPad) Input.RemoveActionMapping(Mapping);
        Input.AddActionMapping(FInputActionKeyMapping(Name,NewKey));
        return;
    }
    const TArray<FInputAxisKeyMapping> Existing=Input.AxisMappings;
    for(const FInputAxisKeyMapping& Mapping:Existing)
        if(IsControlMapping(Control,Mapping)&&!Mapping.Key.IsGamepadKey()) Input.RemoveAxisMapping(Mapping);
    Input.AddAxisMapping(FInputAxisKeyMapping(Name,NewKey,static_cast<float>(Control.Axis)));
}
}
bool ASoraPlayerCharacter::RemapCombatAction(FName ActionName,FKey NewKey)
{
    const int32 Index=SoraInput::FindRemappable(*ActionName.ToString(),0);
    return Index!=INDEX_NONE&&RemapControl(Index,NewKey)==ESoraRemapResult::Done;
}
ESoraRemapResult ASoraPlayerCharacter::RemapControl(int32 Index,const FKey& NewKey,FName* TakenBy,int32* TakenAxis)
{
    const ESoraRemapResult Result=ApplyControlMapping(Index,NewKey,true,TakenBy,TakenAxis);
    if(Result!=ESoraRemapResult::Done||!ControlProfile) return Result;
    const SoraInput::FRemappable& Control=SoraInput::Remappable[Index];
    const bool bPad=NewKey.IsGamepadKey();
    ControlProfile->Bindings.RemoveAll([&](const FSoraControlBinding& Binding)
    {
        return Binding.ActionName==FName(Control.Name)&&Binding.Axis==Control.Axis&&Binding.Key.IsGamepadKey()==bPad;
    });
    FSoraControlBinding Binding;
    Binding.ActionName=Control.Name; Binding.Axis=Control.Axis; Binding.Key=NewKey;
    ControlProfile->Bindings.Add(Binding);
    SaveControlProfile();
    return Result;
}
ESoraRemapResult ASoraPlayerCharacter::ApplyControlMapping(int32 Index,const FKey& NewKey,bool bRequireMenu,FName* TakenBy,int32* TakenAxis)
{
    // Only the Remappable table's controls: never wallet, menu or campaign commands.
    if(Index<0||Index>=SoraInput::RemappableCount) return ESoraRemapResult::NoControl;
    const SoraInput::FRemappable& Control=SoraInput::Remappable[Index];
    const auto* G=PlayerGameMode(this);
    auto* PC=Cast<APlayerController>(GetController());
    if(bRequireMenu&&(!G||!G->bMenu)) return ESoraRemapResult::NotInMenu;
    if(!PC||!PC->PlayerInput) return ESoraRemapResult::NoControl;
    if(const ESoraRemapResult Key=CheckKey(Control,NewKey); Key!=ESoraRemapResult::Done) return Key;
    UPlayerInput& PlayerInput=*PC->PlayerInput;
    FName Other; int32 OtherAxis=0;
    if(FindConflict(PlayerInput,Control,NewKey,Other,OtherAxis))
    {
        if(TakenBy) *TakenBy=Other;
        if(TakenAxis) *TakenAxis=OtherAxis;
        return ESoraRemapResult::Taken;
    }
    BindSlot(PlayerInput,Control,NewKey);
    PlayerInput.FlushPressedKeys();
    PlayerInput.ForceRebuildingKeyMaps(false);
    FireUp(); MeleeUp(); BlockUp(); SprintUp(); JumpUp();
    return ESoraRemapResult::Done;
}
FKey ASoraPlayerCharacter::ControlKey(int32 Index,bool bPad) const
{
    const auto* PC=Cast<APlayerController>(GetController());
    if(Index<0||Index>=SoraInput::RemappableCount||!PC||!PC->PlayerInput) return EKeys::Invalid;
    const SoraInput::FRemappable& Control=SoraInput::Remappable[Index];
    if(Control.Axis==0)
    {
        for(const FInputActionKeyMapping& Mapping:PC->PlayerInput->ActionMappings)
            if(Mapping.ActionName==FName(Control.Name)&&Mapping.Key.IsGamepadKey()==bPad) return Mapping.Key;
    }
    else if(!bPad)
    {
        for(const FInputAxisKeyMapping& Mapping:PC->PlayerInput->AxisMappings)
            if(IsControlMapping(Control,Mapping)&&!Mapping.Key.IsGamepadKey()) return Mapping.Key;
    }
    return EKeys::Invalid;
}
void ASoraPlayerCharacter::ResetControls()
{
    const auto* G=PlayerGameMode(this);
    auto* PC=Cast<APlayerController>(GetController());
    if(!G||!G->bMenu||!PC||!PC->PlayerInput) return;
    // Restores DefaultInput.ini's mappings and axis properties; the player's
    // dead zones then go back on.
    PC->PlayerInput->ForceRebuildingKeyMaps(true);
    SetGamepadDeadZones(GamepadMoveDeadZone,GamepadLookDeadZone);
    PC->PlayerInput->FlushPressedKeys();
    FireUp(); MeleeUp(); BlockUp(); SprintUp(); JumpUp();
    if(ControlProfile) { ControlProfile->Bindings.Reset(); SaveControlProfile(); }
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
void ASoraPlayerCharacter::SetMouseSensitivity(float Sensitivity)
{
    if(!FMath::IsFinite(Sensitivity)) return;
    MouseSensitivity=FMath::Clamp(Sensitivity,.25f,3.f);
    if(ControlProfile&&!bRestoringControlProfile)
    {
        ControlProfile->MouseSensitivity=MouseSensitivity;
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
    if(!ControlProfile||ControlProfile->SaveSchema!=USoraControlSaveGame::Schema)
        ControlProfile=USoraControlSaveGame::New();
    if(!ControlProfile) return;
    bRestoringControlProfile=true;
    SetGamepadDeadZones(FMath::IsFinite(ControlProfile->MoveDeadZone)?ControlProfile->MoveDeadZone:.18f,
        FMath::IsFinite(ControlProfile->LookDeadZone)?ControlProfile->LookDeadZone:.12f);
    SetGamepadLookSensitivity(FMath::IsFinite(ControlProfile->LookSensitivity)?ControlProfile->LookSensitivity:1.f);
    SetMouseSensitivity(FMath::IsFinite(ControlProfile->MouseSensitivity)?ControlProfile->MouseSensitivity:1.f);
    SetInvertedLook(ControlProfile->InvertedLook);
    RestoreBindings();
    bRestoringControlProfile=false;
}
void ASoraPlayerCharacter::RestoreBindings()
{
    auto* PC=Cast<APlayerController>(GetController());
    if(!PC||!PC->PlayerInput) return;
    UPlayerInput& PlayerInput=*PC->PlayerInput;
    const TArray<FSoraControlBinding> Stored=ControlProfile->Bindings;
    // The saved layout is replayed as a whole, because a swap made through a
    // free key only fits once every binding is in place. Each control has at
    // most one key per slot; anything malformed, or a layout with a conflict,
    // restores DefaultInput.ini instead.
    bool bValid=Stored.Num()<=2*SoraInput::RemappableCount;
    TSet<TPair<int32,bool>> Slots;
    TArray<int32> Indices;
    for(const FSoraControlBinding& Binding:Stored)
    {
        const int32 Index=SoraInput::FindRemappable(*Binding.ActionName.ToString(),Binding.Axis);
        bool bSeen=false;
        if(Index!=INDEX_NONE) Slots.Add(TPair<int32,bool>(Index,Binding.Key.IsGamepadKey()),&bSeen);
        bValid&=Index!=INDEX_NONE&&!bSeen&&CheckKey(SoraInput::Remappable[Index],Binding.Key)==ESoraRemapResult::Done;
        Indices.Add(Index);
    }
    if(bValid)
        for(int32 Entry=0;Entry<Stored.Num();++Entry) BindSlot(PlayerInput,SoraInput::Remappable[Indices[Entry]],Stored[Entry].Key);
    FName Other; int32 OtherAxis=0;
    for(int32 Entry=0;bValid&&Entry<Stored.Num();++Entry)
        bValid&=!FindConflict(PlayerInput,SoraInput::Remappable[Indices[Entry]],Stored[Entry].Key,Other,OtherAxis);
    if(!bValid&&Stored.Num()>0)
    {
        UE_LOG(LogTemp,Warning,TEXT("SORA control profile %s has an unusable key layout; the default keys apply"),*ControlSlot);
        PlayerInput.ForceRebuildingKeyMaps(true);
        SetGamepadDeadZones(GamepadMoveDeadZone,GamepadLookDeadZone);
        ControlProfile->Bindings.Reset();
    }
    PlayerInput.ForceRebuildingKeyMaps(false);
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
    // An action that acts in Menu must keep working while the menu pauses the world.
    Binding.bExecuteWhenPaused=(States&SoraInput::Menu)!=0;
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
    BindPress(I,TEXT("Block"),&ASoraPlayerCharacter::BlockDown); BindRelease(I,TEXT("Block"),&ASoraPlayerCharacter::BlockReleased);
    BindPress(I,TEXT("Ability"),&ASoraPlayerCharacter::Ability);
    BindPress(I,TEXT("Sprint"),&ASoraPlayerCharacter::SprintDown); BindRelease(I,TEXT("Sprint"),&ASoraPlayerCharacter::SprintReleased);
    BindPress(I,TEXT("Reload"),&ASoraPlayerCharacter::Reload); BindPress(I,TEXT("Interact"),&ASoraPlayerCharacter::Interact);
    BindRelease(I,TEXT("Interact"),&ASoraPlayerCharacter::InteractUp); BindPress(I,TEXT("Crouch"),&ASoraPlayerCharacter::CrouchPressed);
    BindPress(I,TEXT("Sheathe"),&ASoraPlayerCharacter::SheathePressed);
    BindPress(I,TEXT("Menu"),&ASoraPlayerCharacter::Menu); BindPress(I,TEXT("Enter"),&ASoraPlayerCharacter::Enter);
    BindPress(I,TEXT("Subtitles"),&ASoraPlayerCharacter::Subtitles);
    BindPress(I,TEXT("Scoreboard"),&ASoraPlayerCharacter::ScoreboardDown); BindRelease(I,TEXT("Scoreboard"),&ASoraPlayerCharacter::ScoreboardUp);
    BindPress(I,TEXT("WeaponOne"),&ASoraPlayerCharacter::WeaponOne); BindPress(I,TEXT("WeaponTwo"),&ASoraPlayerCharacter::WeaponTwo); BindPress(I,TEXT("WeaponThree"),&ASoraPlayerCharacter::WeaponThree);
    BindPress(I,TEXT("WeaponFour"),&ASoraPlayerCharacter::WeaponFour); BindPress(I,TEXT("WeaponFive"),&ASoraPlayerCharacter::WeaponFive); BindPress(I,TEXT("WeaponSix"),&ASoraPlayerCharacter::WeaponSix);
    BindPress(I,TEXT("CampaignWeaponNext"),&ASoraPlayerCharacter::CampaignWeaponNext);
}
