// USoraAudioSubsystem: what has no event of its own. The hero's and the
// practice players' weapon actions, footsteps, horses, loops that ride on
// opponents, and the Doppler shift of loops that move.
#include "SoraAudio.h"
#include "ArenaKernelSubsystem.h"
#include "Audio/SoraAudioData.h"
#include "Audio/SoraAudioMath.h"
#include "Combat/SoraStealth.h"
#include "Components/AudioComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/PrimitiveComponent.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "SoraCampaignDirector.h"
#include "SoraCharacterBase.h"
#include "SoraEnemy.h"
#include "SoraEquipmentComponent.h"
#include "SoraGameMode.h"
#include "SoraHorse.h"
#include "SoraPlayerCharacter.h"

using namespace SoraAudioData;

namespace
{
const TCHAR* const Paces[] = {TEXT("crouch"), TEXT("walk"), TEXT("run")};
const TCHAR* const Gaits[] = {TEXT("Halt"), TEXT("Walk"), TEXT("Trot"), TEXT("Canter"), TEXT("Gallop")};
const FName DefaultSurface(TEXT("earth"));
const FString RolePrefix(TEXT("MI_Nyaagyu_"));
// A step longer than this in one frame is a teleport, not a stride.
constexpr float TeleportCm = 300.f;
constexpr float AttachedScanSeconds = .5f;
}

void USoraAudioSubsystem::TickHero()
{
    ASoraGameMode* Game = Mode();
    ASoraPlayerCharacter* Hero = Game ? Game->Hero() : nullptr;
    USoraEquipmentComponent* Gear = Hero ? Hero->FindComponentByClass<USoraEquipmentComponent>() : nullptr;
    if (!Gear || Hero->IsKernelDriven() || !Game->IsPlaying())
    {
        HeroWeapon = FWeaponState();
        return;
    }
    FWeaponState Now;
    Now.WeaponId = Hero->WeaponId;
    Now.bReloading = Gear->bReloading;
    Now.bDrawing = Gear->IsBowDrawing();
    Now.bSheathed = Gear->IsSheathed();
    const bool bKnown = HeroWeapon.WeaponId != INDEX_NONE;
    const auto Act = [&](const TCHAR* Action)
    {
        FFacts Facts;
        Facts.Text(TEXT("Action"), Action).Int(TEXT("WeaponId"), Now.WeaponId).Flag(TEXT("IsHero"), true);
        FRequest Request;
        Request.Family = TEXT("Hero");
        Request.Location = Hero->GetActorLocation();
        Request.Source = Hero;
        Request.bHero = true;
        Request.bAttach = true;
        Dispatch(Request.Family, Facts, Request);
    };
    if (bKnown && Now.bReloading && !HeroWeapon.bReloading)
        Act(TEXT("ReloadStarted"));
    if (bKnown && Now.bDrawing && !HeroWeapon.bDrawing)
        Act(TEXT("BowDrawn"));
    if (bKnown && HeroWeapon.WeaponId == Now.WeaponId && Now.bSheathed != HeroWeapon.bSheathed)
        Act(Now.bSheathed ? TEXT("Sheathed") : TEXT("Drawn"));
    HeroWeapon = Now;
}

void USoraAudioSubsystem::TickKernel()
{
    const ASoraGameMode* Game = Mode();
    const UArenaKernelSubsystem* Kernel = Game && Game->bDeterministicPractice ? Game->Kernel() : nullptr;
    if (!Kernel)
    {
        for (int32 Slot = 0; Slot < KernelWeapons.Num(); ++Slot)
            StopLoop(FString::Printf(TEXT("charge:%d"), Slot), .1f);
        KernelWeapons.Reset();
        return;
    }
    const int32 Count = Kernel->PracticePlayers.Num();
    for (int32 Slot = Count; Slot < KernelWeapons.Num(); ++Slot)
        StopLoop(FString::Printf(TEXT("charge:%d"), Slot), .1f);
    KernelWeapons.SetNum(Count);
    for (int32 Slot = 0; Slot < Count; ++Slot)
    {
        const FSoraPracticePlayer& Player = Kernel->PracticePlayers[Slot];
        FWeaponState& Was = KernelWeapons[Slot];
        FWeaponState Now;
        Now.WeaponId = Player.WeaponId;
        Now.bReloading = Player.ReloadTicks > 0;
        Now.bCharging = Player.ChargeTicks > 0;
        Now.bHeld = Player.ChargeRequired > 0 && Player.ChargeTicks >= Player.ChargeRequired;
        const FString ChargeKey = FString::Printf(TEXT("charge:%d"), Slot);
        AActor* Pawn = KernelPawn(Slot);
        const auto Act = [&](const TCHAR* Action, const FString& LoopKey)
        {
            FFacts Facts;
            Facts.Text(TEXT("Action"), Action).Int(TEXT("WeaponId"), Player.WeaponId).Flag(TEXT("IsHero"), Slot == 0);
            FRequest Request;
            Request.Family = TEXT("Hero");
            Request.Location = Pawn ? Pawn->GetActorLocation() : Player.Feet;
            Request.Source = Pawn;
            Request.bHero = Slot == 0;
            Request.bAttach = Pawn != nullptr;
            Request.LoopKey = LoopKey;
            Dispatch(Request.Family, Facts, Request);
        };
        const bool bKnown = Was.WeaponId != INDEX_NONE;
        if (bKnown && Now.bReloading && !Was.bReloading)
            Act(TEXT("ReloadStarted"), FString());
        if (bKnown && Now.bCharging && !Was.bCharging)
            Act(TEXT("ChargeStarted"), FString());
        if (bKnown && Now.bHeld && !Was.bHeld)
            Act(TEXT("ChargeHeld"), ChargeKey);
        if (!Now.bHeld && Was.bHeld)
            StopLoop(ChargeKey, .1f);
        Was = Now;
    }
}

FName USoraAudioSubsystem::SurfaceUnder(const AActor& Walker, const FVector& Feet) const
{
    const FData* D = FData::Get();
    // A nightingale floor is a stealth floor, whatever it is made of.
    if (const USoraStealth* Stealth = USoraStealth::Get(this))
        if (Stealth->IsZoneActive() && Stealth->SurfaceAt(Feet).StepPermille >= D->NightingalePermille)
            return TEXT("nightingale_floor");
    FHitResult Hit;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(SoraFootstep), false, &Walker);
    if (GetWorld()->LineTraceSingleByChannel(Hit, Feet + FVector(0.f, 0.f, 40.f), Feet - FVector(0.f, 0.f, 60.f), ECC_Visibility, Query))
        if (const UPrimitiveComponent* Floor = Hit.GetComponent())
            if (const UMaterialInterface* Material = Floor->GetMaterial(0))
            {
                // The environment palette's roles: MI_Nyaagyu_<Role>, or a
                // dynamic instance of one.
                const UMaterialInstanceDynamic* Dynamic = Cast<UMaterialInstanceDynamic>(Material);
                const UMaterialInterface* Base = Dynamic && Dynamic->Parent ? Dynamic->Parent.Get() : Material;
                FString Role = Base->GetName();
                if (Role.RemoveFromStart(RolePrefix))
                    if (const FName* Surface = D->Materials.Find(Role))
                        return *Surface;
            }
    const FPlace* Place = WantedPlace();
    return Place && !Place->Surface.IsNone() ? Place->Surface : DefaultSurface;
}

void USoraAudioSubsystem::TickFootsteps(float DeltaTime)
{
    const FData* D = FData::Get();
    ASoraGameMode* Game = Mode();
    UWorld* World = GetWorld();
    if (!Game || !World || DeltaTime <= 0.f || !Game->IsPlaying())
    {
        Strides.Reset();
        return;
    }
    const FVector Ear = Listener();
    const bool bRiding = Game->Campaign() && Game->Campaign()->IsMounted();
    TSet<TWeakObjectPtr<AActor>> Seen;
    for (TActorIterator<ASoraCharacterBase> It(World); It; ++It)
    {
        ASoraCharacterBase* Walker = *It;
        const bool bHero = IsHero(Walker);
        // Riding, the horse's hooves speak for her rider.
        if (!Walker->IsAlive() || (bHero && bRiding) ||
            (!bHero && FVector::DistSquared(Walker->GetActorLocation(), Ear) > FMath::Square(D->FootstepRangeCm)))
            continue;
        Seen.Add(Walker);
        const UCapsuleComponent* Capsule = Walker->GetCapsuleComponent();
        const FVector Feet = Walker->GetActorLocation() - FVector(0.f, 0.f, Capsule ? Capsule->GetScaledCapsuleHalfHeight() : 0.f);
        FStride* Stride = Strides.Find(Walker);
        if (!Stride)
        {
            Strides.Add(Walker, {Feet, 0.f});
            continue;
        }
        const float Moved = FVector::Dist2D(Feet, Stride->Last);
        Stride->Last = Feet;
        const UCharacterMovementComponent* Movement = Walker->GetCharacterMovement();
        if (Moved > TeleportCm || (Movement && Movement->IsFalling()) || Moved / DeltaTime < D->MinSpeedCmS)
            continue;
        const int32 Pace = Walker->bIsCrouched ? 0 : Moved / DeltaTime >= D->RunSpeedCmS ? 2 : 1;
        Stride->Distance += Moved;
        if (Stride->Distance < D->StrideCm[Pace])
            continue;
        Stride->Distance = FMath::Fmod(Stride->Distance, D->StrideCm[Pace]);
        FFacts Facts;
        Facts.Text(TEXT("Surface"), SurfaceUnder(*Walker, Feet).ToString()).Text(TEXT("Pace"), Paces[Pace]).Flag(TEXT("IsHero"), bHero);
        FRequest Request;
        Request.Family = TEXT("Footstep");
        Request.Location = Feet;
        Request.Source = Walker;
        Request.bHero = bHero;
        Request.ExtraDb = D->PaceDb[Pace];
        Dispatch(Request.Family, Facts, Request);
    }
    for (auto It = Strides.CreateIterator(); It; ++It)
        if (!Seen.Contains(It.Key()))
            It.RemoveCurrent();
}

void USoraAudioSubsystem::TickHorses(float DeltaTime)
{
    const FData* D = FData::Get();
    UWorld* World = GetWorld();
    if (!World || DeltaTime <= 0.f)
        return;
    const FVector Ear = Listener();
    TSet<TWeakObjectPtr<AActor>> Seen;
    for (TActorIterator<ASoraHorse> It(World); It; ++It)
    {
        ASoraHorse* Horse = *It;
        const FVector At = Horse->GetActorLocation();
        if (FVector::DistSquared(At, Ear) > FMath::Square(D->HorseRangeCm))
            continue;
        Seen.Add(Horse);
        FHoof* Hoof = Hooves.Find(Horse);
        if (!Hoof)
        {
            FHoof& Fresh = Hooves.Add(Horse);
            Fresh.Last = At;
            Fresh.bSpooked = Horse->IsSpooked();
            Fresh.Rider = Horse->Rider();
            continue;
        }
        const float Speed = FVector::Dist2D(At, Hoof->Last) / DeltaTime;
        Hoof->Last = At;
        int32 Gait = static_cast<int32>(Horse->Gait());
        // A led or road horse keeps her gait in her pace.
        if (Gait == 0 && Speed > 30.f)
            Gait = Speed < 250.f ? 1 : Speed < 450.f ? 2 : Speed < 700.f ? 3 : 4;
        const auto Act = [&](const TCHAR* Action)
        {
            FFacts Facts;
            Facts.Text(TEXT("Action"), Action).Text(TEXT("Gait"), Gaits[Gait]);
            FRequest Request;
            Request.Family = TEXT("Horse");
            Request.Location = At;
            Request.Source = Horse;
            Dispatch(Request.Family, Facts, Request);
        };
        if (Gait > 0 && Speed > 1.f)
        {
            Hoof->Beats += D->HoofbeatsPerSecond.FindRef(Gaits[Gait]) * DeltaTime;
            for (; Hoof->Beats >= 1.f; Hoof->Beats -= 1.f)
                Act(TEXT("Hoof"));
        }
        else
            Hoof->Beats = 0.f;
        if (Horse->IsSpooked() && !Hoof->bSpooked)
            Act(TEXT("Spooked"));
        Hoof->bSpooked = Horse->IsSpooked();
        AActor* Rider = Horse->Rider();
        if (Rider != Hoof->Rider.Get())
            Act(Rider ? TEXT("Mounted") : TEXT("Dismounted"));
        Hoof->Rider = Rider;
    }
    for (auto It = Hooves.CreateIterator(); It; ++It)
        if (!Seen.Contains(It.Key()))
            It.RemoveCurrent();
}

void USoraAudioSubsystem::TickAttached(double Now)
{
    const FData* D = FData::Get();
    UWorld* World = GetWorld();
    if (!World || Now < NextAttachedScan)
        return;
    NextAttachedScan = Now + AttachedScanSeconds;
    const FVector Ear = Listener();
    TSet<TWeakObjectPtr<AActor>> Seen;
    for (TActorIterator<ASoraEnemy> It(World); It; ++It)
    {
        ASoraEnemy* Enemy = *It;
        const FName* Cue = D->Attached.Find(Enemy->ArchetypeId());
        const FCue* Data = Cue ? D->Cue(*Cue) : nullptr;
        const FAttenuation* Preset = Data ? D->Attenuation.Find(Data->Attenuation) : nullptr;
        if (!Data || !Enemy->IsAlive() ||
            (Preset && FVector::DistSquared(Enemy->GetActorLocation(), Ear) > FMath::Square(Preset->InnerCm + Preset->FalloffCm)))
            continue;
        Seen.Add(Enemy);
        if (AttachedLoops.Contains(Enemy))
            continue;
        const FString Key = TEXT("attached:") + Enemy->GetPathName();
        FRequest Request;
        Request.Family = TEXT("Attached");
        Request.Location = Enemy->GetActorLocation();
        Request.Source = Enemy;
        Request.bAttach = true;
        Request.LoopKey = Key;
        Play(*Cue, Request);
        AttachedLoops.Add(Enemy, Key);
    }
    for (auto It = AttachedLoops.CreateIterator(); It; ++It)
        if (!Seen.Contains(It.Key()))
        {
            StopLoop(It.Value(), .5f);
            It.RemoveCurrent();
        }
}

void USoraAudioSubsystem::TickDoppler(float DeltaTime)
{
    if (DeltaTime <= 0.f)
        return;
    const FVector Ear = Listener();
    for (auto& Pair : Loops)
    {
        FLoop& Loop = Pair.Value;
        const AActor* Mover = Loop.Attach.Get();
        if (!Loop.bDoppler || !Mover)
            continue;
        const FVector At = Mover->GetActorLocation();
        // Positive while the source closes on the listener.
        const float Closing = FVector::DotProduct((At - Loop.LastLocation) / DeltaTime, (Ear - At).GetSafeNormal());
        Loop.LastLocation = At;
        if (UAudioComponent* Component = Loop.Component.Get())
            Component->SetPitchMultiplier(FMath::Clamp(SoraAudioMath::SpeedOfSoundCmS /
                FMath::Max(SoraAudioMath::SpeedOfSoundCmS - Closing, 1.f), .8f, 1.25f));
    }
}
