#include "SoraFieldcraft.h"
#include "Game/SoraFieldcraftLayout.h"
#include "Combat/SoraDamage.h"
#include "Combat/SoraStealth.h"
#include "Game/SoraCampaignReach.h"
#include "SoraCampaignDirector.h"
#include "SoraCompanion.h"
#include "SoraEnemy.h"
#include "SoraEnemyController.h"
#include "SoraGameEvents.h"
#include "SoraGameMode.h"
#include "SoraHorse.h"
#include "SoraPlayerCharacter.h"
#include "SoraSettings.h"
#include "SoraText.h"
#include "SoraWorldBuilder.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/SphereComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/PointLight.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"

namespace Craft = SoraFieldcraftRules;
namespace Layout = SoraFieldcraftLayout;

namespace SoraFieldcraftLayout
{
// The climber hangs this far off the face, clear of its ledges.
constexpr float ClimbOffset = 70.f;
constexpr float ClimbSpeed = 120.f;
constexpr float ClimbSideSpeed = 80.f;
constexpr float LedgeDepth = 36.f;
// Work within reach, and how far a look reaches for a look_at event.
constexpr float WorkReach = SoraCampaignReach::Interact;
constexpr float PileReach = 200.f;
constexpr float LookReach = 1600.f;
constexpr float LookSeconds = .1f;
constexpr float StoneSpeed = 1500.f;
constexpr float StoneLift = 380.f;
constexpr float StoneGravity = 980.f;
constexpr float EscortHidePace = 240.f;
// A volley's smoke bank rises this high over its ring.
constexpr float SmokeHeightCm = 300.f;

FVector Floor(const FVector2D& Point, float Height = 0.f) { return FVector(Point.X, Point.Y, Height); }

// The part of an id before its first '_' or digit run: kagaribi_pond ->
// kagaribi, andon_b02_w1 -> andon, collar_okinu -> collar.
FString Family(const FString& Id)
{
    int32 Cut = INDEX_NONE;
    Id.FindChar(TEXT('_'), Cut);
    return Cut == INDEX_NONE ? Id : Id.Left(Cut);
}

// "teppo_3" -> "teppo_*", for a script's npc_downed:teppo_*.
FString Wildcard(const FString& Id)
{
    int32 Cut = INDEX_NONE;
    if (!Id.FindLastChar(TEXT('_'), Cut) || Cut + 1 >= Id.Len()) return FString();
    for (int32 At = Cut + 1; At < Id.Len(); ++At)
        if (!FChar::IsDigit(Id[At])) return FString();
    return Id.Left(Cut) + TEXT("_*");
}

// A floor patch of Kind: the palette surface it wears (nullptr: none) and its
// colour, flat or as that surface's tint.
const TCHAR* FloorLook(FName Kind, FLinearColor& Color)
{
    if (Kind == TEXT("gravel")) { Color = FLinearColor(.82f, .8f, .76f); return Stone; }
    if (Kind == TEXT("nightingale_floor") || Kind == TEXT("dobuita") || Kind == TEXT("board_roof"))
    {
        Color = FLinearColor(.75f, .62f, .48f);
        return Timber;
    }
    if (Kind == TEXT("edge_strip")) { Color = FLinearColor(.45f, .36f, .28f); return Timber; }
    if (Kind == TEXT("metal_grate")) { Color = FLinearColor(.45f, .45f, .48f); return Metal; }
    Color = Kind == TEXT("puddle") ? FLinearColor(.035f, .05f, .06f) : Kind == TEXT("running_water") ? FLinearColor(.05f, .16f, .22f)
        : Kind == TEXT("tatami") ? FLinearColor(.55f, .5f, .3f) : FLinearColor(.3f, .3f, .3f);
    return nullptr;
}
}

// ---------------------------------------------------------------------------
// ASoraLamp
// ---------------------------------------------------------------------------
ASoraLamp::ASoraLamp()
{
    USceneComponent* Root = CreateDefaultSubobject<USceneComponent>(TEXT("LampRoot"));
    RootComponent = Root;
}

void ASoraLamp::Destroyed()
{
    if (IsValid(Light)) Light->Destroy();
    Super::Destroyed();
}

void ASoraLamp::Build(const FSoraLamp& Data, int32 InIndex)
{
    Index = InIndex;
    const bool bFlood = Data.Kind == TEXT("floodlight");
    const bool bBrazier = Data.Kind == TEXT("brazier");
    const bool bKamado = Data.Kind == TEXT("kamado");
    const bool bStrip = Data.Kind == TEXT("strip") || Data.Kind == TEXT("arch");
    GlowHeight = bFlood ? 520.f : bBrazier ? 95.f : bKamado ? 40.f : bStrip ? 230.f : 160.f;
    Intensity = bFlood ? 9000.f : bBrazier || bKamado ? 5200.f : bStrip ? 1800.f : 3200.f;
    // Warm 行灯 and fires at about 1900 K; the Credit House's lamps cold.
    const FLinearColor LightColor = bFlood ? FLinearColor(.78f, .9f, 1.f) : bStrip ? FLinearColor(.2f, .9f, 1.f) : FLinearColor(1.f, .62f, .3f);
    FActorSpawnParameters Params;
    Params.Owner = this;
    Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    Light = GetWorld()->SpawnActor<APointLight>(GetActorLocation() + FVector(0.f, 0.f, GlowHeight), FRotator::ZeroRotator, Params);
    if (Light)
    {
        UPointLightComponent* Lamp = Light->PointLightComponent;
        Light->SetMobility(EComponentMobility::Movable);
        Lamp->SetAttenuationRadius(Data.RadiusCm);
        Lamp->SetIntensity(Intensity);
        Lamp->SetLightColor(LightColor);
        Lamp->SetCastShadows(bFlood);
    }
    USceneComponent* Root = GetRootComponent();
    // A part in a flat colour, or dressed in a palette surface tinted by it.
    const auto Add = [&](const TCHAR* Name, const TCHAR* Mesh, const FVector& At, const FVector& Scale, const FLinearColor& Color,
        const TCHAR* Surface = nullptr)
    {
        UStaticMeshComponent* Part = ASoraWorldBuilder::Shape(this, Root, Name, Mesh, At, Scale, Color);
        if (Surface) ASoraWorldBuilder::Surface(Part, Surface, Color);
        Pieces.Add(Part);
        return Part;
    };
    // The lamp's body stands on the floor under its light.
    const FVector Base = FVector::ZeroVector;
    if (bBrazier)
    {
        Add(TEXT("BrazierLegs"), Layout::Cylinder, Base + FVector(0, 0, 35), FVector(.5f, .5f, .7f), FLinearColor(.3f, .28f, .27f), Layout::Metal);
        Add(TEXT("BrazierBowl"), Layout::Cylinder, Base + FVector(0, 0, 78), FVector(.8f, .8f, .18f), FLinearColor(.34f, .32f, .3f), Layout::Metal);
        Flame = Add(TEXT("BrazierFire"), Layout::Sphere, Base + FVector(0, 0, 95), FVector(.55f, .55f, .35f), FLinearColor(1.f, .45f, .1f));
    }
    else if (bFlood)
    {
        Add(TEXT("FloodPole"), Layout::Cylinder, Base + FVector(0, 0, 260), FVector(.12f, .12f, 5.2f), FLinearColor(.36f, .38f, .42f), Layout::Metal);
        Flame = Add(TEXT("FloodLens"), Layout::Cube, Base + FVector(0, 0, 520), FVector(.45f, .6f, .35f), FLinearColor(.8f, .92f, 1.f));
        // The cable junction at the pole's foot takes an arrow or a round.
        UStaticMeshComponent* Junction = Add(TEXT("FloodJunction"), Layout::Cube, Base + FVector(18, 0, 60), FVector(.3f, .3f, .4f),
            FLinearColor(.05f, .7f, .8f));
        Junction->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
        Junction->SetCollisionResponseToAllChannels(ECR_Block);
        Junction->SetCanEverAffectNavigation(false);
    }
    else if (bKamado)
    {
        // A clay 竈 with its fire mouth and the rice pot on top.
        Add(TEXT("KamadoBody"), Layout::Cube, Base + FVector(0, 0, 32), FVector(.9f, .7f, .64f), FLinearColor(.78f, .6f, .45f), Layout::Plaster);
        Add(TEXT("KamadoPot"), Layout::Cylinder, Base + FVector(0, 0, 76), FVector(.5f, .5f, .26f), FLinearColor(.3f, .28f, .27f), Layout::Metal);
        Flame = Add(TEXT("KamadoFire"), Layout::Cube, Base + FVector(36, 0, 24), FVector(.06f, .34f, .24f), FLinearColor(1.f, .45f, .1f));
    }
    else if (bStrip)
        Flame = Add(TEXT("LedgerStrip"), Layout::Cube, Base + FVector(0, 0, 230), FVector(.1f, 1.4f, .08f), FLinearColor(.15f, .85f, .95f));
    else
    {
        // A 行灯 on its post: the paper box and its frame.
        Add(TEXT("AndonPost"), Layout::Cylinder, Base + FVector(0, 0, 60), FVector(.08f, .08f, 1.2f), FLinearColor(.55f, .42f, .3f), Layout::Timber);
        Flame = Add(TEXT("AndonPaper"), Layout::Cube, Base + FVector(0, 0, 150), FVector(.32f, .32f, .42f), FLinearColor(.95f, .78f, .5f));
        Add(TEXT("AndonCap"), Layout::Cube, Base + FVector(0, 0, 175), FVector(.38f, .38f, .05f), FLinearColor(.4f, .3f, .22f), Layout::Timber);
    }
    bShootable = Data.Snuff == FSoraLamp::ESnuff::Shot;
    SetLit(true);
}

float ASoraLamp::TakeDamage(float Damage, const FDamageEvent& Event, AController* Instigator, AActor* Causer)
{
    // Only the cable junction takes a shot; the rest of the lamp shrugs it off.
    if (bShootable && IsLit())
        if (USoraFieldcraft* Fieldcraft = USoraFieldcraft::Get(this)) Fieldcraft->LampShot(Index);
    return 0.f;
}

void ASoraLamp::SetLit(bool bLit)
{
    if (IsValid(Light)) Light->PointLightComponent->SetVisibility(bLit);
    if (Flame) ASoraWorldBuilder::Tint(Flame, bLit ? FLinearColor(1.f, .62f, .25f) : FLinearColor(.06f, .05f, .05f));
}

bool ASoraLamp::IsLit() const
{
    return IsValid(Light) && Light->PointLightComponent->IsVisible();
}

FVector ASoraLamp::Glow() const
{
    return GetActorLocation() + FVector(0.f, 0.f, GlowHeight);
}

// ---------------------------------------------------------------------------
// ASoraThrownStone
// ---------------------------------------------------------------------------
ASoraThrownStone::ASoraThrownStone()
{
    PrimaryActorTick.bCanEverTick = true;
    Collision = CreateDefaultSubobject<USphereComponent>(TEXT("StoneCollision"));
    RootComponent = Collision;
    Collision->InitSphereRadius(4.f);
    Collision->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    Collision->SetCollisionResponseToAllChannels(ECR_Block);
    Collision->SetCollisionResponseToChannel(ECC_Pawn, ECR_Ignore);
    Collision->SetCollisionObjectType(ECC_WorldDynamic);
    Collision->SetCanEverAffectNavigation(false);
}

void ASoraThrownStone::Tick(float Dt)
{
    Super::Tick(Dt);
    const auto* Mode=GetWorld()?Cast<ASoraGameMode>(GetWorld()->GetAuthGameMode()):nullptr;
    if(Mode&&Mode->InputState()==SoraInput::Dialogue) return;
    if (Age == 0.f)
        ASoraWorldBuilder::Shape(this, RootComponent, TEXT("Tsubute"), Layout::Sphere, FVector::ZeroVector, FVector(.07f), FLinearColor(.36f, .35f, .33f));
    Age += Dt;
    Velocity.Z -= Layout::StoneGravity * Dt;
    FHitResult Hit;
    AddActorWorldOffset(Velocity * Dt, true, &Hit);
    if (Hit.bBlockingHit || Age > 3.f || GetActorLocation().Z < -50.f) Land();
}

void ASoraThrownStone::Land()
{
    // Where it lands the guards hear it and go to look; the hero is not there.
    const FVector At = GetActorLocation();
    if (const USoraStealth* Stealth = USoraStealth::Get(this))
        Stealth->MakeNoise(SoraStealthRules::ENoise::Lure, At, At, this);
    if (USoraFieldcraft* Fieldcraft = USoraFieldcraft::Get(this)) Fieldcraft->StoneLanded(At, NoiseCm);
    Destroy();
}

// ---------------------------------------------------------------------------
// USoraFieldcraft
// ---------------------------------------------------------------------------
USoraFieldcraft* USoraFieldcraft::Get(const UObject* WorldContext)
{
    const UWorld* World = WorldContext ? WorldContext->GetWorld() : nullptr;
    return World ? World->GetSubsystem<USoraFieldcraft>() : nullptr;
}

bool USoraFieldcraft::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
    return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

TStatId USoraFieldcraft::GetStatId() const
{
    RETURN_QUICK_DECLARE_CYCLE_STAT(USoraFieldcraft, STATGROUP_Tickables);
}

void USoraFieldcraft::OnWorldEndPlay(UWorld& InWorld)
{
    // Release the beat's owned actors while the world still has its context.
    // Subsystem deinitialization can run after that context is removed.
    Clear();
    Super::OnWorldEndPlay(InWorld);
}

void USoraFieldcraft::Deinitialize()
{
    Clear();
    Super::Deinitialize();
}

ASoraPlayerCharacter* USoraFieldcraft::Hero() const
{
    const auto* Mode = GetWorld() ? Cast<ASoraGameMode>(GetWorld()->GetAuthGameMode()) : nullptr;
    return Mode ? Mode->Hero() : nullptr;
}

void USoraFieldcraft::Raise(const FString& Event)
{
    if (!Event.IsEmpty()) OnEvent.Broadcast(FName(*Event));
}

UStaticMeshComponent* USoraFieldcraft::Piece(const FString& Name, const TCHAR* Mesh, const FVector& At, const FVector& Scale,
    const FLinearColor& Color, bool bCollision, const TCHAR* Surface)
{
    UStaticMeshComponent* Part = ASoraWorldBuilder::Shape(Props, Props->GetRootComponent(), Name, Mesh, At, Scale, Color, bCollision);
    if (Surface) ASoraWorldBuilder::Surface(Part, Surface, Color);
    if (!bCollision) Part->SetCanEverAffectNavigation(false);
    return Part;
}

void USoraFieldcraft::Clear()
{
    ASoraPlayerCharacter* Player = Hero();
    if (bClimbing && Player) LetGo(*Player, false);
    // Off a ladder he was on, as off the wall: the flying the ladder held him
    // in ends and he drops from where he was (a reset then stands him at the
    // checkpoint).
    if (LadderClimb != INDEX_NONE && Player) Player->GetCharacterMovement()->SetMovementMode(MOVE_Falling);
    for (const auto& Companion : Party) if (IsValid(Companion)) Companion->Destroy();
    for (const auto& Companion : Allies) if (IsValid(Companion)) Companion->Destroy();
    for (const auto& Companion : People) if (IsValid(Companion)) Companion->Destroy();
    for (const auto& Lamp : LampActors) if (IsValid(Lamp)) Lamp->Destroy();
    for (const auto& Fire : FireActors) if (IsValid(Fire)) Fire->Destroy();
    for (const auto& Rider : Riders) if (IsValid(Rider)) Rider->Destroy();
    for (const auto& Stake : Stakes) if (IsValid(Stake)) Stake->Destroy();
    for (const auto& Weak : Netters) if (auto* Brain = Weak.IsValid() ? Cast<ASoraEnemyController>(Weak->GetController()) : nullptr) Brain->ClearErrand();
    for (const auto& Weak : Scouts) if (auto* Brain = Weak.IsValid() ? Cast<ASoraEnemyController>(Weak->GetController()) : nullptr) Brain->ClearErrand();
    if (MeleeHandle.IsValid())
        if (USoraGameEvents* Events = USoraGameEvents::Get(this)) Events->OnMeleeCommitted.Remove(MeleeHandle);
    MeleeHandle.Reset();
    if (IsValid(Props)) Props->Destroy();
    if (IsValid(CandleLight)) CandleLight->DestroyComponent();
    if (Staged && Staged->bCandle)
        if (USoraStealth* Stealth = USoraStealth::Get(this); Stealth && Stealth->IsZoneActive()) Stealth->SetHeroVisibility(1000);
    Party.Reset(); Allies.Reset(); People.Reset(); LampActors.Reset(); Doors.Reset(); Props = nullptr; CandleLight = nullptr;
    LampStates.Reset(); LampHeldMs.Reset(); DoorsOpen.Reset(); HideSpotOf.Reset();
    Holding = FHold();
    Staged = nullptr; BeatId.Reset(); ClockCarryMs = 0.f;
    bSwimming = false; bDiving = false; Breath = {0, 0, 0}; LinesTouched.Reset();
    bClimbing = false; Grip = {0, 0}; ClimbHeight = 0.f; bFalling = false; LedgesReached.Reset();
    Stones = 0; bCupped = false; LookedAt.Reset(); NextLookAt = 0.f; bPartyHidden = false; bFirstSignal = true;
    VolleyState = Craft::StartVolley(); VolleyClockMs = 0; bMarking = false; bMarkValid = false; MarkAt = FVector::ZeroVector;
    bFrontReady = false; bVolleyTaught = false; PendingVolleys.Reset(); VolleysFiredCount = 0; Smoke.Reset();
    QuarryStates.Reset(); Netters.Reset(); NettersJoined.Reset(); Scouts.Reset(); NetRearm.Reset(); Crossers.Reset(); Crosser.Reset();
    bDroneCrossed = false; StringShyMs = 0;
    LightStates.Reset(); LightClockMs = 0; bBellStaged = false; BellUses = 0;
    FiresLit.Reset(); FireActors.Reset(); FireMarks = 0; LastProgress = 0;
    LadderClimb = INDEX_NONE; bLadderUp = true; LadderAlong = 0.f; RoofFall = INDEX_NONE; RoofFallZ = 0.f; RoofStood = INDEX_NONE; RoofStandZ = 0.f;
    Riders.Reset(); Stakes.Reset(); StakeArrows.Reset(); StakeHeldMs.Reset(); StakeChainage.Reset(); PackChainage = 0.f;
    RiderClockMs = 0; RiderStrikeCount = 0;
}

void USoraFieldcraft::Stage(const FSoraBeat& Beat)
{
    Clear();
    if (Beat.Space.Fieldcraft.IsEmpty() || !GetWorld()) return;
    Staged = &Beat.Space.Fieldcraft;
    BeatId = Beat.Id;
    FActorSpawnParameters Params;
    Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    Props = GetWorld()->SpawnActor<AActor>(FVector::ZeroVector, FRotator::ZeroRotator, Params);
    USceneComponent* Root = NewObject<USceneComponent>(Props, TEXT("FieldcraftRoot"));
    Props->SetRootComponent(Root);
    Root->RegisterComponent();
    Props->AddInstanceComponent(Root);
    StageWorld(Beat);
    StageCompanions(Beat);
    StageNets();
    StageWatch();
    StageCharge();
}

void USoraFieldcraft::StageWorld(const FSoraBeat& Beat)
{
    const FSoraFieldcraft& F = *Staged;
    USoraStealth* Stealth = USoraStealth::Get(this);
    const bool bZone = Stealth && Stealth->IsZoneActive();
    FActorSpawnParameters Params;
    Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    for (int32 Index = 0; Index < F.Lamps.Num(); ++Index)
    {
        ASoraLamp* Lamp = GetWorld()->SpawnActor<ASoraLamp>(Layout::Floor(F.Lamps[Index].At), FRotator::ZeroRotator, Params);
        if (Lamp) Lamp->Build(F.Lamps[Index], Index);
        LampActors.Add(Lamp);
        LampStates.Add({true, 0});
        LampHeldMs.Add(0);
    }
    // Floors that change footsteps join the stealth zone; each reads on the
    // ground as what it is. A nightingale floor's edge strip comes after it.
    for (int32 Index = 0; Index < F.Floors.Num(); ++Index)
    {
        const FSoraFloorPatch& Patch = F.Floors[Index];
        const FVector2D Half = Patch.Area.Size * .5f;
        // A roof's boards are its own floor, up where it stands.
        const float Height = static_cast<float>(Patch.HeightCm);
        if (bZone)
            Stealth->AddSurface(FBox(FVector(Patch.Area.Center - Half, Height - 50.f), FVector(Patch.Area.Center + Half, Height + 250.f)),
                {Patch.StepPermille, Patch.CrouchPermille});
        FLinearColor Color;
        const TCHAR* Surface = Layout::FloorLook(Patch.Kind, Color);
        Piece(FString::Printf(TEXT("Floor%d"), Index), Layout::Cube, Layout::Floor(Patch.Area.Center, Height + 1.f + Index * .1f),
            FVector(Patch.Area.Size.X / 100.f, Patch.Area.Size.Y / 100.f, .015f), Color, false, Surface);
    }
    if (F.bWater)
    {
        const FSoraWater& Water = F.Water;
        bDiving = false;
        Breath = Craft::FullBreath(Water.Rules);
        // A swimmer's strokes are heard at the surface; under it he is silent.
        if (bZone)
        {
            const FVector2D Half = Water.Area.Size * .5f;
            Stealth->AddSurface(FBox(FVector(Water.Area.Center - Half, -50.f), FVector(Water.Area.Center + Half, 250.f)),
                {Water.SurfaceStepPermille, 0});
        }
        Piece(TEXT("WaterSurface"), Layout::Cube, Layout::Floor(Water.Area.Center, Layout::WaterLevel),
            FVector(Water.Area.Size.X / 100.f, Water.Area.Size.Y / 100.f, .02f), FLinearColor(.02f, .09f, .12f));
        for (int32 Index = 0; Index < Water.Cover.Num(); ++Index)
            Piece(FString::Printf(TEXT("Reeds%d"), Index), Layout::Cylinder, Layout::Floor(Water.Cover[Index].Center, Layout::WaterLevel + 3.f),
                FVector(Water.Cover[Index].Size.X / 100.f, Water.Cover[Index].Size.Y / 100.f, .04f), FLinearColor(.1f, .24f, .08f));
        for (int32 Line = 0; Line < Water.Lines.Num(); ++Line)
        {
            const FSoraVolume& Band = Water.Lines[Line];
            // The float line runs across the band's long side on the water.
            const bool bAcross = Band.Size.Y >= Band.Size.X;
            const float Length = bAcross ? Band.Size.Y : Band.Size.X;
            for (float Along = -Length * .5f; Along <= Length * .5f; Along += 120.f)
                Piece(FString::Printf(TEXT("Float%d"), Line), Layout::Sphere,
                    Layout::Floor(Band.Center + (bAcross ? FVector2D(0.f, Along) : FVector2D(Along, 0.f)), Layout::WaterLevel + 4.f),
                    FVector(.12f), FLinearColor(.85f, .25f, .08f));
        }
    }
    if (F.bClimb)
    {
        // Stone courses from the floor to the top, wall to wall; hold nubs on
        // its face and a shelf at each ledge. The only way on is up.
        const FSoraClimbFace& Face = F.Climb;
        const float Height = static_cast<float>(Face.Rules.HeightCm);
        const FVector2D Middle = Face.At + FVector2D(Face.DepthCm * .5f, 0.f);
        Piece(TEXT("ClimbFace"), Layout::Cube, Layout::Floor(Middle, Height * .5f), FVector(Face.DepthCm / 100.f, Face.WidthCm / 100.f, Height / 100.f),
            FLinearColor(.78f, .76f, .72f), true, Layout::Stone);
        for (int32 Hold = 1; Hold < Face.Rules.Holds; ++Hold)
            for (float Across = -Face.WidthCm * .5f + 150.f; Across < Face.WidthCm * .5f; Across += 300.f)
                Piece(TEXT("ClimbHold"), Layout::Cube, Layout::Floor(Face.At + FVector2D(-8.f, Across + (Hold % 2 ? 40.f : -40.f)),
                    Craft::HoldHeightCm(Face.Rules, Hold)), FVector(.16f, .3f, .1f), FLinearColor(.86f, .84f, .8f), false, Layout::Stone);
        for (int32 Hold = 1; Hold < Face.Rules.Holds; ++Hold)
            if ((Face.Rules.LedgeMask & (1u << Hold)) != 0u)
                Piece(TEXT("ClimbLedge"), Layout::Cube, Layout::Floor(Face.At + FVector2D(-Layout::LedgeDepth * .5f, 0.f), Craft::HoldHeightCm(Face.Rules, Hold) - 6.f),
                    FVector(Layout::LedgeDepth / 100.f, Face.WidthCm / 100.f, .12f), FLinearColor(.7f, .68f, .64f), false, Layout::Stone);
    }
    if (F.bStones)
    {
        Stones = F.Stones.Carried;
        for (int32 Pile = 0; Pile < F.Stones.Piles.Num(); ++Pile)
            for (int32 Stone = 0; Stone < 6; ++Stone)
                Piece(FString::Printf(TEXT("Rubble%d"), Pile), Layout::Sphere,
                    Layout::Floor(F.Stones.Piles[Pile] + FVector2D(FMath::Cos(Stone * 1.1f) * 30.f, FMath::Sin(Stone * 1.1f) * 30.f), 8.f),
                    FVector(.14f + Stone % 3 * .04f), FLinearColor(.84f, .8f, .74f), false, Layout::Stone);
    }
    for (int32 Door = 0; Door < F.Releases.Num(); ++Door)
    {
        Doors.Add(Piece(FString::Printf(TEXT("CellDoor%d"), Door), Layout::Cube, Layout::Floor(F.Releases[Door].At, 105.f),
            FVector(1.8f, .12f, 2.1f), FLinearColor(.5f, .4f, .32f), false, Layout::Timber));
        DoorsOpen.Add(false);
    }
    if (F.bCandle)
        if (ASoraPlayerCharacter* Player = Hero())
        {
            CandleLight = NewObject<UPointLightComponent>(Player, TEXT("TeshokuCandle"));
            CandleLight->SetupAttachment(Player->GetRootComponent());
            CandleLight->SetRelativeLocation(FVector(35.f, 20.f, 30.f));
            CandleLight->SetAttenuationRadius(F.CandleRadiusCm);
            CandleLight->SetLightColor(FLinearColor(1.f, .58f, .25f));
            CandleLight->SetIntensity(900.f);
            CandleLight->SetCastShadows(false);
            CandleLight->RegisterComponent();
        }
}

void USoraFieldcraft::StageCompanions(const FSoraBeat& Beat)
{
    const FSoraFieldcraft& F = *Staged;
    FActorSpawnParameters Params;
    Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    const FVector Start = Layout::Floor(Beat.Space.Entry, 90.f);
    for (int32 Member = 0; Member < F.Party.Num(); ++Member)
    {
        const FSoraCompanionSpec& Spec = F.Party[Member];
        // A member behind a cell door waits there; the rest start at the road's start in file.
        const FVector At = Spec.Release != INDEX_NONE ? Layout::Floor(F.Releases[Spec.Release].At + FVector2D(-60.f + 40.f * (Member % 4), 110.f), 90.f)
            : Start + FVector(-SoraCampaignReach::PartySpacing * Member, 60.f, 0.f);
        ASoraCompanion* Companion = GetWorld()->SpawnActor<ASoraCompanion>(At, FRotator(0.f, Beat.Space.EntryYaw, 0.f), Params);
        if (!Companion) continue;
        Companion->Init(Spec, Member);
        Party.Add(Companion);
        HideSpotOf.Add(INDEX_NONE);
    }
    // The people a defence protects stand at their targets, at their work.
    for (int32 Index = 0; Index < F.People.Num(); ++Index)
    {
        FSoraCompanionSpec Spec;
        Spec.Id = F.People[Index].Id;
        Spec.Role = TEXT("bystander");
        Spec.bDetectable = false;
        Spec.Rules = {100, false, 3000, 0, 0, false, 0};
        ASoraCompanion* Companion = GetWorld()->SpawnActor<ASoraCompanion>(Layout::Floor(F.People[Index].At, 90.f),
            FRotator(0.f, Index * 45.f, 0.f), Params);
        if (!Companion) continue;
        Companion->Init(Spec, Index);
        People.Add(Companion);
    }
    for (int32 Index = 0; Index < F.Allies.Num(); ++Index)
    {
        const FSoraCompanionSpec& Spec = F.Allies[Index];
        ASoraCompanion* Companion = GetWorld()->SpawnActor<ASoraCompanion>(Layout::Floor(Spec.At, 90.f), FRotator(0.f, Beat.Space.EntryYaw, 0.f), Params);
        if (!Companion) continue;
        Companion->Init(Spec, Index);
        Allies.Add(Companion);
    }
}

int32 USoraFieldcraft::StepMs(float DeltaTime)
{
    ClockCarryMs += DeltaTime * 1000.f;
    const int32 Ms = FMath::FloorToInt32(ClockCarryMs);
    ClockCarryMs -= Ms;
    return Ms;
}

void USoraFieldcraft::Tick(float DeltaTime)
{
    Super::Tick(DeltaTime);
    const auto* Mode = GetWorld() ? Cast<ASoraGameMode>(GetWorld()->GetAuthGameMode()) : nullptr;
    if (!Staged || !Mode || !Mode->IsPlaying() || Mode->bDeterministicPractice) return;
    const int32 DtMs = StepMs(DeltaTime);
    // An event one step raises may end the chapter, and with it the stage,
    // under the steps after it.
    TickHolds(DtMs);
    if (Staged) TickCompanions(DtMs);
    if (Staged) TickNets(DtMs);
    if (Staged) TickVolley(DtMs);
    if (Staged) TickSmoke(DtMs);
    if (Staged) TickLamps(DtMs);
    if (Staged) TickFires();
    if (Staged) TickSearchlights(DtMs);
    if (Staged) TickWater(DtMs);
    if (Staged) TickClimb(DeltaTime, DtMs);
    if (Staged) TickLadders(DeltaTime);
    if (Staged) TickCharge(DeltaTime, DtMs);
    if (Staged) TickCandle();
    if (Staged) TickLooks();
}

// ---------------------------------------------------------------------------
// The hero's hand: held work at a point.
// ---------------------------------------------------------------------------
USoraFieldcraft::FHold USoraFieldcraft::WorkAt(const FVector& Where) const
{
    FHold Best;
    float BestDistance = Layout::WorkReach;
    const auto Consider = [&](const FVector& At, EHoldKind Kind, int32 Index, ASoraCompanion* Companion, int32 NeedMs)
    {
        const float Distance = FVector::Dist2D(At, Where);
        if (Distance >= BestDistance) return;
        BestDistance = Distance;
        Best.Kind = Kind; Best.Index = Index; Best.Companion = Companion; Best.NeedMs = NeedMs; Best.HeldMs = 0;
    };
    for (const auto& List : {&Party, &Allies})
        for (const auto& Companion : *List)
        {
            if (!IsValid(Companion) || !Companion->IsJoined()) continue;
            // The downed are raised by hand; a collared member is freed by
            // hand (a caged one by opening its cell).
            if (Companion->IsDown()) Consider(Companion->GetActorLocation(), EHoldKind::Companion, INDEX_NONE, Companion, Companion->Rules().ReviveMs);
            else if (Companion->IsBound() && !Staged->Party.ContainsByPredicate([&](const FSoraCompanionSpec& Spec)
                { return Spec.Id == Companion->CompanionId() && Spec.Release != INDEX_NONE; }))
                Consider(Companion->GetActorLocation(), EHoldKind::Companion, INDEX_NONE, Companion, Companion->Rules().FreeMs);
        }
    for (int32 Door = 0; Door < DoorsOpen.Num(); ++Door)
        if (!DoorsOpen[Door]) Consider(Layout::Floor(Staged->Releases[Door].At), EHoldKind::Release, Door, nullptr, Staged->Releases[Door].HoldMs);
    for (int32 Lamp = 0; Lamp < LampStates.Num(); ++Lamp)
        if (LampStates[Lamp].Lit && Staged->Lamps[Lamp].Snuff == FSoraLamp::ESnuff::Hold)
            Consider(Layout::Floor(Staged->Lamps[Lamp].At), EHoldKind::Snuff, Lamp, nullptr, Staged->Lamps[Lamp].HoldMs);
    // A net to cut by hand (not from the saddle), and a guttered cook-fire to relight.
    const auto* Mode = GetWorld() ? Cast<ASoraGameMode>(GetWorld()->GetAuthGameMode()) : nullptr;
    const bool bMounted = Mode && Mode->Campaign() && Mode->Campaign()->IsMounted();
    for (int32 Quarry = 0; Quarry < QuarryStates.Num() && !bMounted; ++Quarry)
        if (QuarryStates[Quarry].Net.State == Craft::ENet::Netted)
            Consider(QuarryLocation(Quarry), EHoldKind::NetCut, Quarry, nullptr, Staged->Nets.Rules.CutMs);
    for (int32 Fire = 0; Fire < FiresLit.Num(); ++Fire)
        if (!FiresLit[Fire]) Consider(FireLocation(Fire), EHoldKind::Relight, Fire, nullptr, Staged->Fires.RelightMs);
    return Best;
}

bool USoraFieldcraft::Interact(ASoraPlayerCharacter& Player)
{
    if (!Staged) return false;
    const FVector Where = Player.GetActorLocation();
    // Stones are taken up at a rubble pile.
    if (Staged->bStones && Stones < Staged->Stones.Max)
        for (const FVector2D& Pile : Staged->Stones.Piles)
            if (FVector::Dist2D(Layout::Floor(Pile), Where) < Layout::PileReach)
            {
                Stones = Craft::Refill(Stones, Staged->Stones.Max);
                Raise(TEXT("pickup:tsubute"));
                return true;
            }
    const FHold Work = WorkAt(Where);
    if (Work.Kind == EHoldKind::None) return false;
    Holding = Work;
    return true;
}

void USoraFieldcraft::CancelHeldInteraction()
{
    Holding=FHold();
}

void USoraFieldcraft::TickHolds(int32 DtMs)
{
    if (Holding.Kind == EHoldKind::None) return;
    ASoraPlayerCharacter* Player = Hero();
    FVector At = FVector::ZeroVector;
    if (Holding.Kind == EHoldKind::Companion) At = Holding.Companion.IsValid() ? Holding.Companion->GetActorLocation() : FVector(MAX_flt);
    else if (Holding.Kind == EHoldKind::Release) At = Layout::Floor(Staged->Releases[Holding.Index].At);
    else if (Holding.Kind == EHoldKind::NetCut) At = QuarryLocation(Holding.Index);
    else if (Holding.Kind == EHoldKind::Relight) At = FireLocation(Holding.Index);
    else At = Layout::Floor(Staged->Lamps[Holding.Index].At);
    // The work holds only while Interact stays down beside it.
    const bool bHeld = Player && Player->IsActionHeld(TEXT("Interact")) &&
        FVector::Dist2D(At, Player->GetActorLocation()) < Layout::WorkReach + 60.f;
    if (!bHeld) { Holding = FHold(); return; }
    // A companion counts the hand on it in its own rules (TickCompanions), a net in its own (TickNets).
    if (Holding.Kind == EHoldKind::Companion || Holding.Kind == EHoldKind::NetCut) return;
    if (!Craft::Hold(Holding.HeldMs, true, DtMs, Holding.NeedMs)) return;
    const FHold Done = Holding;
    Holding = FHold();
    if (Done.Kind == EHoldKind::Snuff) SnuffLamp(Done.Index);
    else if (Done.Kind == EHoldKind::Relight)
    {
        // The cook-fire burns again and the hold goes on.
        FiresLit[Done.Index] = true;
        if (IsValid(FireActors[Done.Index])) FireActors[Done.Index]->SetLit(true);
        Raise(TEXT("fire_lit:") + Staged->Fires.Ids[Done.Index]);
    }
    else
    {
        // A cell door opens and those behind it are free.
        DoorsOpen[Done.Index] = true;
        if (Doors.IsValidIndex(Done.Index) && Doors[Done.Index]) Doors[Done.Index]->SetVisibility(false);
        for (int32 Member = 0; Member < Party.Num(); ++Member)
            if (IsValid(Party[Member]) && Staged->Party[Member].Release == Done.Index && Party[Member]->IsBound())
                Party[Member]->Step(Party[Member]->Rules().FreeMs, true);
        Raise(TEXT("interact:") + Staged->Releases[Done.Index].Id);
        Raise(FString::Printf(TEXT("event:door_%d_open"), Done.Index + 1));
    }
}

void USoraFieldcraft::TickCompanions(int32 DtMs)
{
    for (const auto& List : {&Party, &Allies})
        for (const auto& Companion : *List)
        {
            if (!IsValid(Companion)) continue;
            const bool bHeld = Holding.Kind == EHoldKind::Companion && Holding.Companion.Get() == Companion;
            const Craft::EChange Change = Companion->Step(DtMs, bHeld);
            if (Change == Craft::EChange::None) continue;
            if (bHeld) Holding = FHold();
            CompanionChanged(*Companion, Change);
        }
}

void USoraFieldcraft::RaiseDowned(const ASoraCompanion& Companion)
{
    const FString& Id = Companion.CompanionId();
    Raise(TEXT("npc_downed:") + Id);
    if (const FString Any = Layout::Wildcard(Id); !Any.IsEmpty()) Raise(TEXT("npc_downed:") + Any);
    Raise(TEXT("npc_downed:any"));
}

void USoraFieldcraft::CompanionChanged(ASoraCompanion& Companion, Craft::EChange Change)
{
    const FString& Id = Companion.CompanionId();
    switch (Change)
    {
    case Craft::EChange::Downed:
        if (Holding.Companion.Get() == &Companion) Holding = FHold();
        RaiseDowned(Companion);
        return;
    case Craft::EChange::Revived:
        Raise(TEXT("npc_revived:") + Id);
        Raise(TEXT("npc_revived:any"));
        return;
    case Craft::EChange::Freed:
        // A collar cut (ch05.b03's pre-interacts) or a cell opened.
        Raise(TEXT("interact_done:collar_") + Id);
        Raise(TEXT("npc_freed:") + Id);
        return;
    case Craft::EChange::Died:
        // An escort lost fails the beat to its checkpoint (the beat's fail rows).
        Raise(TEXT("npc_died:") + Id);
        if (Companion.Role() == ASoraCompanion::ERole::Escort) Raise(TEXT("npc_died:any_escort"));
        return;
    case Craft::EChange::None:
        return;
    }
}

void USoraFieldcraft::LanceHit(AActor* Target)
{
    auto* Companion = Cast<ASoraCompanion>(Target);
    if (Companion && Companion->Lance()) Raise(TEXT("npc_lanced:") + Companion->CompanionId());
}

void USoraFieldcraft::TargetChanged(int32 Target, int32 HealthPermille)
{
    if (!Staged) return;
    for (int32 Index = 0; Index < Staged->People.Num() && Index < People.Num(); ++Index)
    {
        ASoraCompanion* Person = People[Index];
        if (Staged->People[Index].Target != Target || !IsValid(Person)) continue;
        // Where drones net the people (ch04.b12's seizure nets) their nets
        // decide it (TickNets); elsewhere (ch05.b07's Kōzō) a person worn below
        // half its target's health is netted, mended past it freed, and lost
        // with it taken.
        if (Staged->bNets && Staged->Nets.Kind == FSoraNets::EKind::Person && HealthPermille > 0) return;
        const Craft::EState Wanted = HealthPermille <= 0 ? Craft::EState::Dead :
            HealthPermille < Craft::Permille / 2 ? Craft::EState::Bound : Craft::EState::Up;
        const Craft::EState Before = Person->Condition();
        if (Wanted == Before || Before == Craft::EState::Dead) return;
        Person->Present(Wanted);
        if (Wanted == Craft::EState::Bound) RaiseDowned(*Person);
        else if (Wanted == Craft::EState::Up) Raise(TEXT("npc_freed:") + Person->CompanionId());
        return;
    }
}

void USoraFieldcraft::NoteBeatEvent(const FString& Event)
{
    // A road's searchlight comes on with its wave. Wall lights receive the
    // known detection point separately; generic alarm barks carry no position.
    for (int32 Light = 0; Light < LightStates.Num() && Staged; ++Light)
    {
        const FSoraSearchlight& Row = Staged->Searchlights[Light];
        if (!Row.ActiveOn.IsEmpty() && Row.ActiveOn == Event) LightStates[Light].bOn = true;
    }
    for (const auto& Ally : Allies)
        if (IsValid(Ally) && !Ally->IsJoined() && Staged)
            for (const FSoraCompanionSpec& Spec : Staged->Allies)
                if (Spec.Id == Ally->CompanionId() && Spec.Joins == Event) Ally->Join();
}

void USoraFieldcraft::StoneLanded(const FVector& At, int32 NoiseCm)
{
    if (!Staged) return;
    Raise(TEXT("lure_triggered"));
    // A stone that strikes the bell rings it (once).
    if (Staged->bBell && BellUses > 0 && FVector::Dist(At, BellLocation()) <= Craft::BellStrikeCm) BellStruck();
    // A guard's bark when it hears one (ai_event:lure_heard).
    for (TActorIterator<ASoraEnemy> It(GetWorld()); It; ++It)
        if (It->IsAlive() && It->IsEnemy() && FVector::Dist(It->GetActorLocation(), At) <= NoiseCm)
        {
            Raise(TEXT("ai_event:lure_heard"));
            return;
        }
}

// ---------------------------------------------------------------------------
// Lamps.
// ---------------------------------------------------------------------------
bool USoraFieldcraft::SnuffLamp(int32 Index)
{
    if (!Staged || !LampStates.IsValidIndex(Index) ||
        !Craft::Snuff(LampStates[Index], Staged->Lamps[Index].Snuff != FSoraLamp::ESnuff::None))
        return false;
    if (IsValid(LampActors[Index])) LampActors[Index]->SetLit(false);
    Raise(TEXT("lamp_out:") + Staged->Lamps[Index].Id);
    return true;
}

void USoraFieldcraft::LampShot(int32 Index)
{
    if (Staged && Staged->Lamps.IsValidIndex(Index) && Staged->Lamps[Index].Snuff == FSoraLamp::ESnuff::Shot) SnuffLamp(Index);
}

void USoraFieldcraft::TickLamps(int32 DtMs)
{
    for (int32 Index = 0; Index < LampStates.Num(); ++Index)
        if (Craft::LampTick(LampStates[Index], Staged->Lamps[Index].RelightMs, DtMs))
        {
            if (IsValid(LampActors[Index])) LampActors[Index]->SetLit(true);
            Raise(TEXT("lamp_lit:") + Staged->Lamps[Index].Id);
        }
}

// ---------------------------------------------------------------------------
// Water.
// ---------------------------------------------------------------------------
float USoraFieldcraft::HeroPace() const
{
    return bSwimming && Staged ? static_cast<float>(bDiving ? Staged->Water.Rules.DiveCmS : Staged->Water.Rules.SurfaceCmS) : 0.f;
}

int32 USoraFieldcraft::HeroExposure(int32 ExposurePermille) const
{
    if (!bSwimming || !Staged) return ExposurePermille;
    if (bDiving) return 0;
    // At the surface only a head shows; among reeds and lotus barely that.
    const ASoraPlayerCharacter* Player = Hero();
    return ExposurePermille * (Player && UnderCover(Player->GetActorLocation()) ? 150 : 450) / 1000;
}

bool USoraFieldcraft::UnderCover(const FVector& Location) const
{
    return bSwimming && !bDiving && Staged && Staged->bWater &&
        Staged->Water.Cover.ContainsByPredicate([&](const FSoraVolume& Cover) { return Cover.Contains(Location); });
}

void USoraFieldcraft::TickWater(int32 DtMs)
{
    ASoraPlayerCharacter* Player = Hero();
    if (!Staged->bWater || !Player) return;
    const FSoraWater& Water = Staged->Water;
    const bool bWasSwimming = bSwimming;
    bSwimming = Water.Area.Contains(Player->GetActorLocation());
    // A crouch in the water is a dive: the eye goes under the surface. The
    // wish, not the stance, decides it: he surfaces as he means to even where
    // something overhead keeps his body low.
    bDiving = bSwimming && Player->GetCharacterMovement()->bWantsToCrouch;
    if (bSwimming != bWasSwimming) Raise(bSwimming ? TEXT("water_enter") : TEXT("water_leave"));
    if (bSwimming)
    {
        const int32 Damage = Craft::Breathe(Breath, Water.Rules, bDiving, DtMs);
        if (Damage > 0)
        {
            FHitResult Trace; Trace.ImpactPoint = Player->GetActorLocation(); Trace.Location = Trace.ImpactPoint;
            SoraDamage::Strike(Player, static_cast<float>(Damage), FSoraHit::Hazard(Player->GetActorLocation()), FVector::UpVector, Trace, nullptr, nullptr);
        }
    }
    else Breath = Craft::FullBreath(Water.Rules);
    // The float line rings when a swimmer brushes it at the surface; passing
    // under it in a dive is silent.
    for (int32 Line = 0; Line < Water.Lines.Num(); ++Line)
    {
        const bool bIn = bSwimming && Water.Lines[Line].Contains(Player->GetActorLocation());
        if (bIn && !bDiving && !LinesTouched.Contains(Line))
        {
            LinesTouched.Add(Line);
            if (const USoraStealth* Stealth = USoraStealth::Get(this))
                Stealth->MakeNoise(SoraStealthRules::ENoise::Lure, Player->GetActorLocation(), Player->GetActorLocation(), Player);
            Raise(TEXT("ai_event:float_line"));
        }
        else if (!bIn) LinesTouched.Remove(Line);
    }
}

// ---------------------------------------------------------------------------
// Climbing.
// ---------------------------------------------------------------------------
bool USoraFieldcraft::AtFace(const ASoraPlayerCharacter& Player) const
{
    if (!Staged || !Staged->bClimb) return false;
    const FSoraClimbFace& Face = Staged->Climb;
    const FVector At = Player.GetActorLocation();
    const float Before = Face.At.X - At.X;
    const FVector Forward = Player.GetActorForwardVector().GetSafeNormal2D();
    return Before > 0.f && Before < 130.f && FMath::Abs(At.Y - Face.At.Y) < Face.WidthCm * .5f - 40.f &&
        Forward.X > .5f && Player.GetCharacterMovement()->IsMovingOnGround();
}

bool USoraFieldcraft::Jump(ASoraPlayerCharacter& Player)
{
    if (!Staged) return false;
    // At a ladder's foot, or its top on the roof, Jump takes the ladder.
    if (LadderJump(Player)) return true;
    if (bClimbing)
    {
        LetGo(Player, false);
        return true;
    }
    if (!AtFace(Player)) return false;
    // Hands on the lowest holds: the wall carries him from here.
    bClimbing = true;
    Grip = Craft::StartClimb();
    ClimbHeight = 0.f;
    Player.StopSprint();
    UCharacterMovementComponent* Movement = Player.GetCharacterMovement();
    Movement->StopMovementImmediately();
    Movement->SetMovementMode(MOVE_Flying);
    Raise(TEXT("climb_start"));
    return true;
}

void USoraFieldcraft::LetGo(ASoraPlayerCharacter& Player, bool bFell)
{
    if (!bClimbing) return;
    bClimbing = false;
    bFalling = true;
    FallFromZ = Player.GetActorLocation().Z;
    UCharacterMovementComponent* Movement = Player.GetCharacterMovement();
    Movement->StopMovementImmediately();
    Movement->SetMovementMode(MOVE_Falling);
    // Pushed off the face so he falls clear of its ledges.
    Player.AddActorWorldOffset(FVector(-Layout::ClimbOffset * .5f, 0.f, 0.f), true);
    Raise(bFell ? TEXT("climb_fell") : TEXT("climb_let_go"));
}

void USoraFieldcraft::TickClimb(float DeltaTime, int32 DtMs)
{
    ASoraPlayerCharacter* Player = Hero();
    if (!Staged->bClimb || !Player) return;
    const FSoraClimbFace& Face = Staged->Climb;
    const Craft::FClimbRules& Rules = Face.Rules;
    UCharacterMovementComponent* Movement = Player->GetCharacterMovement();
    if (bFalling && !bClimbing && Movement->IsMovingOnGround())
    {
        // A fall's damage is its height (SoraFieldcraftRules::FallDamage).
        bFalling = false;
        const int32 Damage = Craft::FallDamage(Rules, FMath::RoundToInt32(FallFromZ - Player->GetActorLocation().Z));
        if (Damage != 0)
        {
            FHitResult Trace; Trace.ImpactPoint = Player->GetActorLocation(); Trace.Location = Trace.ImpactPoint;
            SoraDamage::Strike(Player, Damage < 0 ? Player->Health + 1000.f : static_cast<float>(Damage),
                FSoraHit::Hazard(Player->GetActorLocation()), FVector::UpVector, Trace, nullptr, nullptr);
        }
    }
    if (!bClimbing) return;
    const float Up = FMath::Clamp(Player->GetInputAxisValue(TEXT("MoveForward")), -1.f, 1.f);
    const float Side = FMath::Clamp(Player->GetInputAxisValue(TEXT("MoveRight")), -1.f, 1.f);
    // Each hold reached spends grip; resting still at a ledge gives it back.
    const float Next = static_cast<float>(Craft::HoldHeightCm(Rules, Grip.Hold + 1));
    const float Below = static_cast<float>(Craft::HoldHeightCm(Rules, Grip.Hold - 1));
    ClimbHeight = FMath::Clamp(ClimbHeight + Up * Layout::ClimbSpeed * DeltaTime, 0.f, static_cast<float>(Rules.HeightCm));
    Craft::EReach Reached = Craft::EReach::Moved;
    bool bReached = false;
    if (Up > .2f && ClimbHeight >= Next && Grip.Hold < Rules.Holds) { Reached = Craft::Reach(Grip, Rules, 1); bReached = true; }
    else if (Up < -.2f && ClimbHeight <= Below && Grip.Hold > 0) { Reached = Craft::Reach(Grip, Rules, -1); bReached = true; }
    else if (FMath::Abs(Up) < .2f) Craft::Rest(Grip, Rules, DtMs);
    // Never past a hold not yet reached.
    ClimbHeight = FMath::Clamp(ClimbHeight, static_cast<float>(Craft::HoldHeightCm(Rules, Grip.Hold - 1)),
        static_cast<float>(Craft::HoldHeightCm(Rules, Grip.Hold + 1)));
    if (bReached && Reached == Craft::EReach::Fell)
    {
        LetGo(*Player, true);
        return;
    }
    if (bReached && Craft::AtLedge(Rules, Grip))
    {
        int32 Ledge = 0;
        for (int32 Hold = 1; Hold < Grip.Hold; ++Hold) Ledge += (Rules.LedgeMask & (1u << Hold)) != 0u;
        if (!LedgesReached.Contains(Ledge) && Face.LedgeEvents.IsValidIndex(Ledge))
        {
            LedgesReached.Add(Ledge);
            Raise(Face.LedgeEvents[Ledge]);
        }
    }
    const float HalfHeight = Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    if (bReached && Reached == Craft::EReach::Top)
    {
        // Over the top: onto the stones behind the face.
        bClimbing = false;
        Player->SetActorLocation(FVector(Face.At.X + 160.f, Player->GetActorLocation().Y, Rules.HeightCm + HalfHeight + 5.f), false,
            nullptr, ETeleportType::TeleportPhysics);
        Movement->SetMovementMode(MOVE_Walking);
        Raise(TEXT("climb_top"));
        Raise(Face.TopEvent);
        return;
    }
    if (bReached && Reached == Craft::EReach::Ground)
    {
        bClimbing = false;
        Movement->SetMovementMode(MOVE_Walking);
        return;
    }
    const float Y = FMath::Clamp(Player->GetActorLocation().Y + Side * Layout::ClimbSideSpeed * DeltaTime,
        Face.At.Y - Face.WidthCm * .5f + 60.f, Face.At.Y + Face.WidthCm * .5f - 60.f);
    Movement->Velocity = FVector::ZeroVector;
    Player->SetActorLocation(FVector(Face.At.X - Player->GetCapsuleComponent()->GetScaledCapsuleRadius() - Layout::ClimbOffset * .5f, Y,
        ClimbHeight + HalfHeight), false, nullptr, ETeleportType::TeleportPhysics);
}

// ---------------------------------------------------------------------------
// Stones, the candle, signals and looks.
// ---------------------------------------------------------------------------
bool USoraFieldcraft::Ability(ASoraPlayerCharacter& Player)
{
    if (!Staged) return false;
    // The escorted party answers the hero's signal: down, or on.
    if (Staged->bSignal && !Party.IsEmpty())
    {
        bool bAnyUp = false, bAnyHidden = false;
        for (const auto& Member : Party)
            if (IsValid(Member)) { bAnyUp |= Member->Condition() == Craft::EState::Up; bAnyHidden |= Member->IsHiddenAway(); }
        const bool bHide = bAnyUp;
        if (!bAnyUp && !bAnyHidden) return false;
        TSet<int32> Taken;
        for (int32 Member = 0; Member < Party.Num(); ++Member)
        {
            if (!IsValid(Party[Member]) || !Party[Member]->Signal(bHide)) continue;
            if (!bHide) { HideSpotOf[Member] = INDEX_NONE; continue; }
            // Each goes to the nearest hide spot nobody else took.
            int32 Best = INDEX_NONE;
            float BestDistance = MAX_flt;
            for (int32 Spot = 0; Spot < Staged->HideSpots.Num(); ++Spot)
            {
                const float Distance = FVector::Dist2D(Layout::Floor(Staged->HideSpots[Spot]), Party[Member]->GetActorLocation());
                if (!Taken.Contains(Spot) && Distance < BestDistance) { Best = Spot; BestDistance = Distance; }
            }
            HideSpotOf[Member] = Best;
            if (Best != INDEX_NONE)
            {
                Taken.Add(Best);
                Party[Member]->SetGoal(Layout::Floor(Staged->HideSpots[Best], Party[Member]->GetActorLocation().Z), Party[Member]->GetActorRotation().Yaw,
                    Layout::EscortHidePace);
            }
        }
        bPartyHidden = bHide;
        Raise(bHide ? TEXT("signal:hide") : TEXT("signal:go"));
        if (bHide && bFirstSignal) Raise(TEXT("event:first_hide_signal"));
        bFirstSignal &= !bHide;
        Raise(TEXT("player_signal"));
        return true;
    }
    auto* Mode = Cast<ASoraGameMode>(GetWorld()->GetAuthGameMode());
    // Held, the volley ranks' ring follows his eye; let go, it is the order (TickVolley).
    if (Staged->bVolley && Mode && Mode->Campaign()->IsMechanicInPlay(TEXT("volley_command")))
    {
        bMarking = true;
        bMarkValid = AimMark(Player, MarkAt);
        return true;
    }
    if (!Staged->bStones) return false;
    if (!Mode || !Mode->Campaign()->IsMechanicInPlay(TEXT("tsubute"))) return false;
    if (Stones <= 0)
    {
        const SoraText::FLine None = SoraText::Line(NSLOCTEXT("SoraArena.Fieldcraft", "NoStones", "礫がない。崩れた石垣で拾おう。"));
        Mode->Notice = None.Japanese; Mode->NoticeEnglish = None.English; Mode->NoticeTime = 3.f;
        return true;
    }
    ThrowStone(Player);
    return true;
}

void USoraFieldcraft::ThrowStone(ASoraPlayerCharacter& Player)
{
    if (!Craft::Throw(Stones)) return;
    // A short overhand throw on an arc.
    const UCameraComponent* Camera = Player.GetCamera();
    const FVector Direction = Camera->GetForwardVector();
    FActorSpawnParameters Params;
    Params.Owner = &Player; Params.Instigator = &Player;
    Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    ASoraThrownStone* Stone = GetWorld()->SpawnActor<ASoraThrownStone>(Camera->GetComponentLocation() + Direction * 60.f,
        FRotator::ZeroRotator, Params);
    if (!Stone) return;
    Stone->Velocity = Direction * Layout::StoneSpeed + FVector(0.f, 0.f, Layout::StoneLift);
    Stone->NoiseCm = Staged->Stones.NoiseCm;
    Raise(TEXT("tsubute_thrown"));
}

// ---------------------------------------------------------------------------
// Volley ranks (輪番撃ち).
// ---------------------------------------------------------------------------
bool USoraFieldcraft::AimMark(const ASoraPlayerCharacter& Player, FVector& At) const
{
    const UCameraComponent* Camera = Player.GetCamera();
    const float Range = static_cast<float>(Staged->Volley.Rules.RangeCm);
    const FVector Eye = Camera->GetComponentLocation();
    FCollisionQueryParams Query(SCENE_QUERY_STAT(SoraVolleyMark), false, &Player);
    for (const auto* List : {&Party, &Allies, &People})
        for (const auto& Companion : *List)
            if (IsValid(Companion)) Query.AddIgnoredActor(Companion);
    FHitResult Hit;
    if (!GetWorld()->LineTraceSingleByChannel(Hit, Eye, Eye + Camera->GetForwardVector() * (Range + 1000.f), ECC_Visibility, Query))
        return false;
    At = Hit.ImpactPoint;
    return FVector::Dist2D(At, Player.GetActorLocation()) <= Range;
}

void USoraFieldcraft::TickVolley(int32 DtMs)
{
    if (!Staged->bVolley) return;
    VolleyClockMs += DtMs;
    if (!bVolleyTaught)
    {
        bVolleyTaught = true;
        Raise(TEXT("event:volley_tutorial"));
    }
    // The ring follows the hero's eye while Ability is held; let go, it is the order.
    if (bMarking)
    {
        ASoraPlayerCharacter* Player = Hero();
        if (!Player || !Player->CanPlay()) bMarking = false;
        else
        {
            bMarkValid = AimMark(*Player, MarkAt);
            if (!Player->IsActionHeld(TEXT("Ability")))
            {
                bMarking = false;
                OrderVolley();
            }
        }
    }
    // Each order fires after its delay, in the order given.
    while (!PendingVolleys.IsEmpty() && VolleyClockMs >= PendingVolleys[0].FireAtMs)
    {
        const FPendingVolley Due = PendingVolleys[0];
        PendingVolleys.RemoveAt(0);
        FireVolley(Due.Rank, Due.At);
    }
    // The front rank calls when it stands loaded.
    const bool bReady = VolleyClockMs >= VolleyState.ReadyAtMs[VolleyState.Front];
    if (bReady && !bFrontReady) Raise(TEXT("event:volley_ready"));
    bFrontReady = bReady;
    // On Easy the ranks may order themselves (ch08 easy_auto_order).
    if (bReady && PendingVolleys.IsEmpty() && AutoOrdering()) AutoOrder();
    // A rank ordered stays in front until it fires; then it files back to load.
    const int32 Front = PendingVolleys.IsEmpty() ? VolleyState.Front : PendingVolleys[0].Rank;
    for (const auto& Ally : Allies)
        if (IsValid(Ally) && Ally->VolleyRank() != INDEX_NONE) Ally->StepUp(Ally->VolleyRank() == Front);
}

void USoraFieldcraft::OrderVolley()
{
    auto* Mode = Cast<ASoraGameMode>(GetWorld()->GetAuthGameMode());
    const auto Notice = [Mode](const SoraText::FLine& Line)
    {
        if (!Mode) return;
        Mode->Notice = Line.Japanese; Mode->NoticeEnglish = Line.English; Mode->NoticeTime = 2.5f;
    };
    const Craft::FVolleyRules& Rules = Staged->Volley.Rules;
    if (!bMarkValid)
    {
        Notice(SoraText::Format(NSLOCTEXT("SoraArena.Fieldcraft", "VolleyOutOfReach", "的が遠い。{Range} m 以内の地面を示せ。"),
            {{TEXT("Range"), Rules.RangeCm / 100}}));
        return;
    }
    const int32 Rank = Craft::Order(VolleyState, Rules, VolleyClockMs);
    if (Rank < 0)
    {
        Notice(SoraText::Line(NSLOCTEXT("SoraArena.Fieldcraft", "VolleyLoading", "次の組はまだ込めている。")));
        return;
    }
    PendingVolleys.Add({Rank, MarkAt, VolleyClockMs + Rules.OrderDelayMs});
    Raise(TEXT("event:volley_ordered"));
    Raise(FString::Printf(TEXT("event:volley_ordered_%d"), VolleyState.Orders));
}

void USoraFieldcraft::FireVolley(int32 Rank, const FVector& At)
{
    const FSoraVolley& Volley = Staged->Volley;
    int32 Standing = 0;
    FVector From = FVector::ZeroVector;
    for (const auto& Ally : Allies)
        if (IsValid(Ally) && Ally->VolleyRank() == Rank && Ally->CanVolley())
        {
            Ally->Volley(At);
            From += Ally->GetActorLocation();
            ++Standing;
        }
    ++VolleysFiredCount;
    Raise(TEXT("event:volley_rotate"));
    if (Standing == 0) return;
    From /= Standing;
    // The white smoke bank it leaves hides that lane for both sides (ch08
    // smoke_obscure_s): it blocks sight (SmokeBetween), never what is shot or
    // swung through it, so it has no collision.
    if (Volley.SmokeMs > 0)
    {
        const float Radius = static_cast<float>(Volley.Rules.RadiusCm);
        UStaticMeshComponent* Bank = Piece(TEXT("VolleySmoke"), Layout::Cylinder, FVector(At.X, At.Y, At.Z + Layout::SmokeHeightCm * .5f),
            FVector(Radius / 50.f, Radius / 50.f, Layout::SmokeHeightCm / 100.f), FLinearColor(.86f, .86f, .84f));
        Bank->SetCastShadow(false);
        Smoke.Add({Bank, Volley.SmokeMs, At, Radius, At.Z + Layout::SmokeHeightCm});
        Raise(TEXT("event:volley_smoke"));
    }
    // Everyone in the ring, nearest its centre first (then by spawn order):
    // shields are staggered, a walker struck in the legs, and the volley's
    // weight split across the nearest unshielded. Nothing misses.
    struct FInRing { ASoraEnemy* Enemy; float Distance; };
    TArray<FInRing> InRing;
    for (TActorIterator<ASoraEnemy> It(GetWorld()); It; ++It)
    {
        ASoraEnemy* Enemy = *It;
        if (!Enemy->IsEnemy() || !Enemy->IsAlive() || Enemy->IsSubdued() || Enemy->IsHidden()) continue;
        const float Distance = FVector::Dist2D(Enemy->GetActorLocation(), At);
        if (Distance <= Volley.Rules.RadiusCm) InRing.Add({Enemy, Distance});
    }
    InRing.Sort([](const FInRing& A, const FInRing& B)
        { return A.Distance != B.Distance ? A.Distance < B.Distance : A.Enemy->GetUniqueID() < B.Enemy->GetUniqueID(); });
    ASoraPlayerCharacter* Player = Hero();
    const auto Strike = [&](ASoraEnemy& Enemy, float Damage)
    {
        FHitResult Trace; Trace.ImpactPoint = Enemy.GetActorLocation(); Trace.Location = Trace.ImpactPoint;
        // The hero's order: what the volley fells is his.
        SoraDamage::Strike(&Enemy, Damage, FSoraHit::Ranged(From, Volley.WeaponId), (Enemy.GetActorLocation() - From).GetSafeNormal(),
            Trace, Player ? Player->GetController() : nullptr, Player);
    };
    TArray<ASoraEnemy*> Open;
    for (const FInRing& In : InRing)
    {
        if (In.Enemy->HasShield()) In.Enemy->Stagger(Craft::ShieldStaggerMs);
        else if (In.Enemy->ArchetypeId() == TEXT("seizure_walker"))
        {
            Strike(*In.Enemy, In.Enemy->MaxHealth * Craft::WalkerPermille / 1000.f);
            In.Enemy->Stagger(Craft::WalkerStaggerMs);
        }
        else Open.Add(In.Enemy);
    }
    for (int32 Index = 0; Index < Open.Num(); ++Index)
        if (const int32 Share = Craft::VolleyShare(Open.Num(), Standing, Volley.PerRank, Index); Share > 0)
            Strike(*Open[Index], static_cast<float>(Share));
}

bool USoraFieldcraft::AutoOrdering() const
{
    const auto* Mode = GetWorld() ? Cast<ASoraGameMode>(GetWorld()->GetAuthGameMode()) : nullptr;
    return Staged && Staged->bVolley && Staged->Volley.bAutoOrder && Mode && Mode->Settings() &&
        SoraAccessibility::CampaignDifficulty(this) == SoraAccessibility::EDifficulty::Easy && Mode->Settings()->VolleyAutoOrder();
}

void USoraFieldcraft::AutoOrder()
{
    // The ring on the opponent nearest the hero within the ranks' reach.
    const ASoraPlayerCharacter* Player = Hero();
    if (!Player || bMarking) return;
    const float Range = static_cast<float>(Staged->Volley.Rules.RangeCm);
    const ASoraEnemy* Target = nullptr;
    float Best = Range;
    for (TActorIterator<ASoraEnemy> It(GetWorld()); It; ++It)
    {
        if (!It->IsEnemy() || !It->IsAlive() || It->IsSubdued() || It->IsHidden()) continue;
        const float Distance = FVector::Dist2D(It->GetActorLocation(), Player->GetActorLocation());
        if (Distance < Best || (Distance == Best && Target && It->GetUniqueID() < Target->GetUniqueID())) { Best = Distance; Target = *It; }
    }
    if (!Craft::AutoOrders(true, true, true, bMarking, Target != nullptr)) return;
    MarkAt = Target->GetActorLocation() - FVector(0.f, 0.f, Target->GetSimpleCollisionHalfHeight());
    bMarkValid = true;
    Raise(TEXT("event:volley_auto_order"));
    OrderVolley();
}

bool USoraFieldcraft::SmokeBetween(const FVector& From, const FVector& To) const
{
    for (const FSmoke& Bank : Smoke)
    {
        // The part of the segment inside the bank's circle (seen from above),
        // then whether it is inside the bank's height anywhere along that part.
        const FVector2D A(From - Bank.Foot), D(To - From);
        const float R2 = Bank.RadiusCm * Bank.RadiusCm;
        const float DD = D.SizeSquared(), AD = FVector2D::DotProduct(A, D), AA = A.SizeSquared();
        float Enter = 0.f, Leave = 1.f;
        if (DD <= KINDA_SMALL_NUMBER)
        {
            if (AA > R2) continue;
        }
        else
        {
            const float Disc = AD * AD - DD * (AA - R2);
            if (Disc < 0.f) continue;
            const float Root = FMath::Sqrt(Disc);
            Enter = FMath::Max(0.f, (-AD - Root) / DD);
            Leave = FMath::Min(1.f, (-AD + Root) / DD);
            if (Enter > Leave) continue;
        }
        const float ZEnter = FMath::Lerp(From.Z, To.Z, Enter), ZLeave = FMath::Lerp(From.Z, To.Z, Leave);
        if (FMath::Max(ZEnter, ZLeave) >= Bank.Foot.Z && FMath::Min(ZEnter, ZLeave) <= Bank.TopCm) return true;
    }
    return false;
}

void USoraFieldcraft::TickSmoke(int32 DtMs)
{
    for (int32 Index = Smoke.Num() - 1; Index >= 0; --Index)
    {
        Smoke[Index].LeftMs -= DtMs;
        if (Smoke[Index].LeftMs > 0 && Smoke[Index].Bank.IsValid()) continue;
        if (UStaticMeshComponent* Bank = Smoke[Index].Bank.Get()) Bank->DestroyComponent();
        Smoke.RemoveAt(Index);
    }
}

int32 USoraFieldcraft::WorkRatePermille() const
{
    // A guttered cook-fire stops the kitchen until it is relit.
    if (Staged && Staged->bFires && FiresOut() > 0) return 0;
    return Staged && Staged->bCandle ? Craft::WorkRatePermille(Staged->Candle, bCupped) : Craft::Permille;
}

void USoraFieldcraft::TickCandle()
{
    if (!Staged->bCandle) return;
    const ASoraPlayerCharacter* Player = Hero();
    // Guard held cups the flame in the paw: harder to see, slower to copy by.
    bCupped = Player && Player->IsActionHeld(TEXT("Block"));
    if (USoraStealth* Stealth = USoraStealth::Get(this); Stealth && Stealth->IsZoneActive())
        Stealth->SetHeroVisibility(Craft::CandleVisibility(Staged->Candle, bCupped));
    if (IsValid(CandleLight)) CandleLight->SetIntensity(bCupped ? 250.f : 900.f);
}

void USoraFieldcraft::PartyDetected()
{
    if (!Staged || !Staged->bSignal) return;
    // A patrol that finds the group engages; the escorted drop where they stand.
    for (const auto& Member : Party)
        if (IsValid(Member)) Member->Signal(true);
    bPartyHidden = true;
}

bool USoraFieldcraft::PartyReady() const
{
    bool bHidden = false, bDown = false, bBound = false;
    for (const auto& Member : Party)
    {
        if (!IsValid(Member)) continue;
        bHidden |= Member->IsHiddenAway();
        bDown |= Member->IsDown() || Member->IsDead();
        bBound |= Member->IsBound();
    }
    return Craft::PartyWalks(true, bHidden, bDown, bBound);
}

void USoraFieldcraft::PlaceParty(const TArray<FVector>& Slots, float Yaw, float PaceCmS)
{
    for (int32 Member = 0; Member < Party.Num(); ++Member)
    {
        ASoraCompanion* Companion = Party[Member];
        if (!IsValid(Companion) || Companion->IsBound() || Companion->IsDown() || Companion->IsDead() ||
            Companion->IsHiddenAway() || !Slots.IsValidIndex(Member))
            continue;
        Companion->SetGoal(Slots[Member] + FVector(0.f, 0.f, 90.f), Yaw, PaceCmS);
    }
}

bool USoraFieldcraft::PartyWork(FVector& Location) const
{
    if (!Staged) return false;
    for (int32 Door = 0; Door < DoorsOpen.Num(); ++Door)
        if (!DoorsOpen[Door]) { Location = Layout::Floor(Staged->Releases[Door].At); return true; }
    for (const auto& Member : Party)
        if (IsValid(Member) && (Member->IsBound() || Member->IsDown()))
        {
            Location = Member->GetActorLocation() - FVector(0.f, 0.f, Member->GetActorLocation().Z);
            return true;
        }
    return false;
}

void USoraFieldcraft::TickLooks()
{
    ASoraPlayerCharacter* Player = Hero();
    const float Time = GetWorld()->GetTimeSeconds();
    if (!Player || Time < NextLookAt) return;
    NextLookAt = Time + Layout::LookSeconds;
    const FVector Eye = Player->GetCamera()->GetComponentLocation();
    const FVector Forward = Player->GetCamera()->GetForwardVector();
    const auto Looks = [&](const FVector& At, const AActor* Owner, const FString& Id)
    {
        if (LookedAt.Contains(Id)) return;
        const FVector Delta = At - Eye;
        const float Distance = Delta.Size();
        if (Distance > Layout::LookReach || Distance < 1.f) return;
        // Within a few degrees of the view's centre, and in plain sight.
        const float Aim = FMath::Max(FMath::Cos(FMath::DegreesToRadians(5.f)), FMath::Cos(FMath::Atan(80.f / Distance)));
        if (FVector::DotProduct(Forward, Delta / Distance) < FMath::Min(Aim, .9985f)) return;
        FHitResult Hit;
        FCollisionQueryParams Query(SCENE_QUERY_STAT(SoraLookAt), false, Player);
        if (Owner) Query.AddIgnoredActor(Owner);
        if (Props) Query.AddIgnoredActor(Props);
        // The people about him never hide what he looks at (a collar in a file of captives).
        for (const auto* List : {&Party, &Allies, &People})
            for (const auto& Companion : *List)
                if (IsValid(Companion)) Query.AddIgnoredActor(Companion);
        if (GetWorld()->LineTraceSingleByChannel(Hit, Eye, At, ECC_Visibility, Query)) return;
        LookedAt.Add(Id);
        Raise(TEXT("look_at:") + Id);
        const FString Kin = Layout::Family(Id);
        if (Kin != Id && !LookedAt.Contains(Kin))
        {
            LookedAt.Add(Kin);
            Raise(TEXT("look_at:") + Kin);
        }
    };
    for (int32 Lamp = 0; Lamp < LampActors.Num(); ++Lamp)
        if (IsValid(LampActors[Lamp]) && LampStates[Lamp].Lit) Looks(LampActors[Lamp]->Glow(), LampActors[Lamp], Staged->Lamps[Lamp].Id);
    for (const auto& Member : Party)
        if (IsValid(Member) && Member->IsBound()) Looks(Member->GetActorLocation() + FVector(0.f, 0.f, 50.f), Member, TEXT("collar_") + Member->CompanionId());
    for (int32 Door = 0; Door < DoorsOpen.Num(); ++Door)
        if (!DoorsOpen[Door]) Looks(Layout::Floor(Staged->Releases[Door].At, 120.f), nullptr, Staged->Releases[Door].Id);
}

FSoraFieldcraftReadout USoraFieldcraft::Readout(const ASoraPlayerCharacter& Player) const
{
    FSoraFieldcraftReadout Out;
    if (!Staged) return Out;
    Out.bActive = true;
    Out.bSwimming = bSwimming;
    Out.bDiving = bSwimming && bDiving;
    Out.Breath = Staged->bWater ? static_cast<float>(Breath.BreathMs) / FMath::Max(1, Staged->Water.Rules.BreathMs) : 1.f;
    Out.bClimbing = bClimbing;
    Out.Grip = static_cast<float>(Grip.GripMilli) / (Craft::GripMax * 1000.f);
    Out.bLedge = bClimbing && Craft::AtLedge(Staged->Climb.Rules, Grip);
    Out.bAtFace = !bClimbing && AtFace(Player);
    Out.bStones = Staged->bStones;
    Out.Stones = Stones;
    Out.StonesMax = Staged->bStones ? Staged->Stones.Max : 0;
    for (const FVector2D& Pile : Staged->Stones.Piles)
        Out.bAtPile |= Staged->bStones && Stones < Staged->Stones.Max && FVector::Dist2D(Layout::Floor(Pile), Player.GetActorLocation()) < Layout::PileReach;
    Out.bCandle = Staged->bCandle;
    Out.bCupped = bCupped;
    const auto Kind = [&](const FHold& Work)
    {
        switch (Work.Kind)
        {
        case EHoldKind::Snuff: return FSoraFieldcraftReadout::EHold::Snuff;
        case EHoldKind::Release: return FSoraFieldcraftReadout::EHold::Release;
        case EHoldKind::NetCut: return FSoraFieldcraftReadout::EHold::NetCut;
        case EHoldKind::Relight: return FSoraFieldcraftReadout::EHold::Relight;
        case EHoldKind::Companion:
            return Work.Companion.IsValid() && Work.Companion->IsBound() ? FSoraFieldcraftReadout::EHold::Free : FSoraFieldcraftReadout::EHold::Revive;
        case EHoldKind::None: break;
        }
        return FSoraFieldcraftReadout::EHold::None;
    };
    Out.HoldHere = Kind(WorkAt(Player.GetActorLocation()));
    Out.Holding = Kind(Holding);
    if (Holding.Kind == EHoldKind::Companion && Holding.Companion.IsValid())
        Out.HoldProgress = static_cast<float>(Holding.Companion->State().HeldMs) / FMath::Max(1, Holding.NeedMs);
    else if (Holding.Kind == EHoldKind::NetCut && QuarryStates.IsValidIndex(Holding.Index))
        Out.HoldProgress = static_cast<float>(QuarryStates[Holding.Index].Net.HeldMs) / FMath::Max(1, Holding.NeedMs);
    else if (Holding.Kind != EHoldKind::None)
        Out.HoldProgress = static_cast<float>(Holding.HeldMs) / FMath::Max(1, Holding.NeedMs);
    Out.bSignal = Staged->bSignal && !Party.IsEmpty();
    Out.bPartyHidden = bPartyHidden;
    for (const auto& List : {&Party, &Allies})
        for (const auto& Companion : *List)
            if (IsValid(Companion) && Companion->IsDown()) Out.Downed.Add(Companion->GetActorLocation());
    for (const auto& Member : Party)
        if (IsValid(Member)) { Out.PartyDown += Member->IsDown(); Out.PartyBound += Member->IsBound(); }
    Out.bVolley = Staged->bVolley;
    if (Staged->bVolley)
    {
        const Craft::FVolleyRules& Rules = Staged->Volley.Rules;
        Out.bMarking = bMarking;
        Out.bMarkValid = bMarkValid;
        Out.MarkAt = MarkAt;
        Out.RingRadius = static_cast<float>(Rules.RadiusCm);
        Out.Ranks = Rules.Ranks;
        Out.FrontRank = VolleyState.Front;
        for (int32 Rank = 0; Rank < Rules.Ranks; ++Rank)
            Out.RankLoaded[Rank] = FMath::Clamp(1.f - static_cast<float>(VolleyState.ReadyAtMs[Rank] - VolleyClockMs) / Rules.CycleMs, 0.f, 1.f);
        for (const auto& Ally : Allies)
            if (IsValid(Ally) && Ally->VolleyRank() != INDEX_NONE && Ally->CanVolley()) ++Out.RankStanding[Ally->VolleyRank()];
        Out.bAutoOrder = AutoOrdering();
    }
    for (const FQuarryState& State : QuarryStates)
    {
        Out.NetsLocking += State.Net.State == Craft::ENet::Locking;
        Out.NetsHeld += State.Net.State == Craft::ENet::Netted;
        if (State.Net.State == Craft::ENet::Netted && Staged->Nets.Rules.HaulMs > 0)
            Out.HaulLeft = FMath::Min(Out.HaulLeft, 1.f - static_cast<float>(State.Net.Ms) / Staged->Nets.Rules.HaulMs);
    }
    for (int32 Light = 0; Light < LightStates.Num(); ++Light)
        if (!Staged->Searchlights[Light].IsRoad() && LightStates[Light].bSeesHero)
        {
            Out.bInLight = true;
            Out.LightExposure = FMath::Max(Out.LightExposure,
                static_cast<float>(LightStates[Light].InSpotMs) / FMath::Max(1, Staged->Searchlights[Light].Rules.AlertMs));
        }
    Out.FiresOut = FiresOut();
    Out.bOnLadder = LadderClimb != INDEX_NONE;
    for (const FSoraLadder& Ladder : Staged->Ladders)
    {
        const FVector Foot(Ladder.Foot, Player.GetActorLocation().Z);
        const FVector Top = Foot + FRotator(0.f, Ladder.Yaw, 0.f).Vector() * 140.f;
        Out.bAtLadder |= !Out.bOnLadder && (FVector::Dist2D(Player.GetActorLocation(), IsOnRoof(Player.GetActorLocation()) ? Top : Foot) < 110.f);
    }
    for (const auto& Rider : Riders) Out.Riders += IsValid(Rider);
    for (int32 Stake = 0; Stake < Stakes.Num(); ++Stake) Out.StakesStanding += IsStakeStanding(Stake);
    return Out;
}
