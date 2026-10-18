#include "SoraFieldcraft.h"
#include "Game/SoraFieldcraftLayout.h"
#include "Combat/SoraStealth.h"
#include "SoraBeatRules.h"
#include "SoraCampaignDirector.h"
#include "SoraCompanion.h"
#include "SoraEnemy.h"
#include "SoraEnemyController.h"
#include "SoraGameMode.h"
#include "SoraHorse.h"
#include "SoraPlayerCharacter.h"
#include "SoraWorldBuilder.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SpotLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"

// What watches and what the hero works in a beat's place beyond its lamps:
// the alarm lecterns an auditor runs to; searchlights that sweep the moat
// (ch06.b02) or a stretch of road (ch02.b08's ship light); the one-shot
// temple bell a stone can ring (ch07.b04); the cook-fires a hold keeps lit
// (ch03.b14); and the ladders onto the board roofs (ch03.b03, b10), the
// roofs themselves and the straw that softens a drop from them.

namespace Craft = SoraFieldcraftRules;
namespace Layout = SoraFieldcraftLayout;

namespace SoraFieldcraftLayout
{
// A road's searchlight shines down from a ship this high.
constexpr float ShipHeightCm = 3000.f;
// Guards this near a spot look toward it; a spot this near a horse frightens her.
constexpr float LightWatchCm = 6000.f;
// A guard walks to the bell at about this pace, then looks it over.
constexpr float BellWalkCmS = 200.f;
// Where Jump takes the ladder: its foot, or its top at the roof's edge.
constexpr float LadderReachCm = 110.f;
constexpr float RoofSlabCm = 20.f;
constexpr float RoofPostCm = 20.f;
}

void USoraFieldcraft::StageWatch()
{
    const FSoraFieldcraft& F = *Staged;
    USoraStealth* Stealth = USoraStealth::Get(this);
    // Alarm lecterns: an auditor that knows of the hero runs to the nearest.
    for (int32 Index = 0; Index < F.Alarms.Num(); ++Index)
    {
        const FVector At = FVector(F.Alarms[Index].At, 0.f);
        if (Stealth && Stealth->IsZoneActive()) Stealth->AddAlarmPoint(At + FVector(0.f, 0.f, 90.f));
        Piece(TEXT("AlarmLectern_") + F.Alarms[Index].Id, Layout::Cube, At + FVector(0.f, 0.f, 55.f), FVector(.4f, .4f, 1.1f),
            FLinearColor(.36f, .38f, .42f), false, Layout::Metal);
        Piece(TEXT("AlarmLens_") + F.Alarms[Index].Id, Layout::Cube, At + FVector(0.f, 0.f, 114.f), FVector(.3f, .3f, .06f), FLinearColor(.15f, .85f, .95f));
    }
    // Searchlights: a wall light's housing on its bracket, and its lamp and spot.
    for (int32 Index = 0; Index < F.Searchlights.Num(); ++Index)
    {
        const FSoraSearchlight& Row = F.Searchlights[Index];
        FLightState& State = LightStates.AddDefaulted_GetRef();
        State.bOn = Row.ActiveOn.IsEmpty();
        const FVector Mount = Row.IsRoad() ? FVector::ZeroVector : FVector(Row.At, Row.HeightCm);
        if (!Row.IsRoad())
        {
            Piece(TEXT("SearchlightPost_") + Row.Id, Layout::Cylinder, FVector(Row.At, Row.HeightCm * .5f), FVector(.25f, .25f, Row.HeightCm / 100.f),
                FLinearColor(.38f, .38f, .4f), true, Layout::Metal);
            Piece(TEXT("SearchlightHousing_") + Row.Id, Layout::Cylinder, Mount + FVector(0.f, 0.f, 40.f), FVector(.9f, .9f, .7f),
                FLinearColor(.34f, .38f, .42f), false, Layout::Metal);
        }
        USpotLightComponent* Lamp = NewObject<USpotLightComponent>(Props, *(TEXT("Searchlight_") + Row.Id));
        Lamp->SetupAttachment(Props->GetRootComponent());
        Lamp->SetMobility(EComponentMobility::Movable);
        Lamp->SetIntensity(60000.f);
        Lamp->SetLightColor(FLinearColor(.8f, .9f, 1.f));
        Lamp->SetAttenuationRadius(8000.f);
        Lamp->SetInnerConeAngle(3.f);
        Lamp->SetOuterConeAngle(6.f);
        Lamp->SetCastShadows(true);
        Lamp->RegisterComponent();
        Props->AddInstanceComponent(Lamp);
        State.Lamp = Lamp;
        UStaticMeshComponent* Spot = Piece(TEXT("SearchlightSpot_") + Row.Id, Layout::Cylinder, FVector::ZeroVector,
            FVector(Row.Rules.SpotCm / 100.f, Row.Rules.SpotCm / 100.f, .01f), FLinearColor(.85f, .92f, 1.f));
        State.Spot = Spot;
        Lamp->SetVisibility(State.bOn);
        Spot->SetVisibility(State.bOn);
    }
    // The temple bell on its gantry hook: a stone that strikes it rings it once.
    if (F.bBell)
    {
        BellUses = F.Bell.Rules.Uses;
        bBellStaged = true;
        const FVector At(F.Bell.At, F.Bell.HeightCm);
        Piece(TEXT("BellGantry"), Layout::Cube, FVector(F.Bell.At, F.Bell.HeightCm + 110.f), FVector(.2f, 2.4f, .2f), FLinearColor(.4f, .42f, .46f),
            false, Layout::Metal);
        Piece(TEXT("BellHook"), Layout::Cylinder, At + FVector(0.f, 0.f, 80.f), FVector(.05f, .05f, .5f), FLinearColor(.3f, .3f, .32f), false,
            Layout::Metal);
        // A bronze 梵鐘, green with age.
        UStaticMeshComponent* Bell = Piece(TEXT("Bonsho"), Layout::Cylinder, At, FVector(1.2f, 1.2f, 1.2f), FLinearColor(.5f, .56f, .42f), true,
            Layout::Metal);
        Bell->SetCanEverAffectNavigation(false);
    }
    // Cook-fires, lit: each a clay 竈 whose fire the guards see by.
    if (F.bFires)
    {
        FActorSpawnParameters Params;
        Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        for (int32 Index = 0; Index < F.Fires.Points.Num(); ++Index)
        {
            FSoraLamp Kamado;
            Kamado.Id = F.Fires.Ids[Index];
            Kamado.Kind = TEXT("kamado");
            Kamado.At = F.Fires.Points[Index];
            Kamado.RadiusCm = 450.f;
            Kamado.Snuff = FSoraLamp::ESnuff::None;
            ASoraLamp* Fire = GetWorld()->SpawnActor<ASoraLamp>(FVector(Kamado.At, 0.f), FRotator::ZeroRotator, Params);
            if (Fire) Fire->Build(Kamado, INDEX_NONE);
            FireActors.Add(Fire);
            FiresLit.Add(true);
        }
    }
    // Board roofs on their posts, each with a ladder at its edge and, where
    // the script lays one, a straw pile beside it. The roof is a floor.
    for (int32 Index = 0; Index < F.Ladders.Num(); ++Index)
    {
        const FSoraLadder& Ladder = F.Ladders[Index];
        const FVector2D Half = Ladder.Roof.Size * .5f;
        Piece(TEXT("Roof_") + Ladder.Id, Layout::Cube, FVector(Ladder.Roof.Center, Ladder.HeightCm - Layout::RoofSlabCm * .5f),
            FVector(Ladder.Roof.Size.X / 100.f, Ladder.Roof.Size.Y / 100.f, Layout::RoofSlabCm / 100.f), FLinearColor(.66f, .55f, .43f), true,
            Layout::Timber);
        for (const FVector2D Corner : {FVector2D(-1, -1), FVector2D(-1, 1), FVector2D(1, -1), FVector2D(1, 1)})
            Piece(TEXT("RoofPost_") + Ladder.Id, Layout::Cube,
                FVector(Ladder.Roof.Center + (Half - FVector2D(Layout::RoofPostCm)) * Corner, (Ladder.HeightCm - Layout::RoofSlabCm) * .5f),
                FVector(Layout::RoofPostCm / 100.f, Layout::RoofPostCm / 100.f, (Ladder.HeightCm - Layout::RoofSlabCm) / 100.f),
                FLinearColor(.5f, .4f, .31f), true, Layout::Timber);
        // Two rails and the rungs between them, leaning on the roof's edge.
        const FVector Foot(Ladder.Foot, 0.f);
        const FRotator Facing(0.f, Ladder.Yaw, 0.f);
        for (const float Side : {-24.f, 24.f})
            Piece(TEXT("LadderRail_") + Ladder.Id, Layout::Cube, Foot + FRotator(0.f, Ladder.Yaw + 90.f, 0.f).Vector() * Side + Facing.Vector() * 35.f +
                FVector(0.f, 0.f, Ladder.HeightCm * .5f), FVector(.05f, .05f, Ladder.HeightCm / 100.f), FLinearColor(.8f, .68f, .52f), false,
                Layout::Timber);
        for (float Rung = 30.f; Rung < Ladder.HeightCm; Rung += 35.f)
            Piece(TEXT("LadderRung_") + Ladder.Id, Layout::Cube, Foot + Facing.Vector() * 35.f + FVector(0.f, 0.f, Rung),
                FRotator(0.f, Ladder.Yaw + 90.f, 0.f).Vector().GetAbs() * .5f + FVector(.04f, .04f, .03f), FLinearColor(.8f, .68f, .52f), false,
                Layout::Timber);
        if (Ladder.bStraw)
            Piece(TEXT("Straw_") + Ladder.Id, Layout::Cube, FVector(Ladder.Straw.Center, 22.f),
                FVector(Ladder.Straw.Size.X / 100.f, Ladder.Straw.Size.Y / 100.f, .44f), FLinearColor(.72f, .62f, .34f));
    }
}

bool USoraFieldcraft::IsLightOn(int32 Light) const
{
    return LightStates.IsValidIndex(Light) && LightStates[Light].bOn;
}

FVector USoraFieldcraft::SpotOf(int32 Light) const
{
    const USpotLightComponent* Lamp = LightStates.IsValidIndex(Light) ? LightStates[Light].Lamp.Get() : nullptr;
    const UStaticMeshComponent* Spot = LightStates.IsValidIndex(Light) ? LightStates[Light].Spot.Get() : nullptr;
    return Lamp && Spot ? Spot->GetComponentLocation() : FVector::ZeroVector;
}

void USoraFieldcraft::TickSearchlights(int32 DtMs)
{
    if (LightStates.IsEmpty()) return;
    LightClockMs += DtMs;
    const auto* Mode = Cast<ASoraGameMode>(GetWorld()->GetAuthGameMode());
    USoraCampaignDirector* Campaign = Mode ? Mode->Campaign() : nullptr;
    const FSoraChapter* Chapter = Campaign ? Campaign->ActiveChapter() : nullptr;
    const FSoraBeatSpace* Space = Campaign ? Campaign->ActiveSpace() : nullptr;
    ASoraPlayerCharacter* Player = Hero();
    USoraStealth* Stealth = USoraStealth::Get(this);
    for (int32 Index = 0; Index < LightStates.Num(); ++Index)
    {
        FLightState& State = LightStates[Index];
        const FSoraSearchlight& Row = Staged->Searchlights[Index];
        USpotLightComponent* Lamp = State.Lamp.Get();
        UStaticMeshComponent* Spot = State.Spot.Get();
        if (!Lamp || !Spot) continue;
        Lamp->SetVisibility(State.bOn);
        Spot->SetVisibility(State.bOn);
        if (!State.bOn) continue;
        // Where the spot falls now: a wall light's sweep across its arc (each
        // light half a period apart), locked on the last place seen after a
        // detection; a ship's light back and forth along its stretch of road.
        FVector At;
        FVector From;
        if (Row.IsRoad())
        {
            if (!Chapter || !Space || !Space->bRoute) continue;
            const FSoraZone& Road = Chapter->Space.Zones[Space->Zone];
            const int32 Period = Row.Rules.PeriodMs, Half = Period / 2, Time = LightClockMs % Period;
            const float Along = static_cast<float>(Time <= Half ? Time : Period - Time) / Half;
            At = FVector(Road.PointAlong(Row.RoadFromCm + (Row.RoadToCm - Row.RoadFromCm) * Along), 2.f);
            From = At + FVector(-900.f, 0.f, Layout::ShipHeightCm);
        }
        else
        {
            State.LockedMs = FMath::Max(0, State.LockedMs - DtMs);
            const float Bearing = Row.Yaw + Craft::BeamMilliDeg(Row.Rules, LightClockMs, Index * (Row.Rules.PeriodMs / 2)) / 1000.f;
            At = State.LockedMs > 0 ? State.LockedAt : FVector(Row.At, 0.f) + FRotator(0.f, Bearing, 0.f).Vector() * Row.ReachCm;
            At.Z = (Staged->bWater && Staged->Water.Area.Contains(At) ? Layout::WaterLevel : 0.f) + 2.f;
            From = FVector(Row.At, Row.HeightCm);
        }
        Spot->SetWorldLocation(At);
        Lamp->SetWorldLocationAndRotation(From, (At - From).Rotation());
        Lamp->SetOuterConeAngle(FMath::RadiansToDegrees(FMath::Atan2(Row.Rules.SpotCm * .5f, FVector::Dist(From, At))) + .5f);
        Lamp->SetInnerConeAngle(Lamp->OuterConeAngle * .7f);
        if (!Player) continue;
        if (Row.IsRoad())
        {
            // The spot frightens the horses near it: Kurimaru shies and the string halts.
            const FSoraBeat* Beat = Campaign ? Campaign->ActiveBeatData() : nullptr;
            const float Fear = Beat && Beat->Space.bMount ? static_cast<float>(Beat->Space.Mount.FearRadiusCm) : 0.f;
            bool bNear = false;
            if (ASoraHorse* Steed = Campaign ? Campaign->Steed() : nullptr; Steed && Campaign->IsMounted() &&
                FVector::Dist2D(Steed->GetActorLocation(), At) < Fear)
            {
                bNear = true;
                if (!State.bSpookedHorses)
                {
                    Steed->Spook();
                    Raise(TEXT("horse_spooked"));
                    Raise(TEXT("ai:horse_spooked:kurimaru"));
                }
            }
            if (Campaign && Beat)
                for (const ASoraHorse* Beast : Campaign->PackHorses())
                    if (FVector::Dist2D(Beast->GetActorLocation(), At) < Fear)
                    {
                        bNear = true;
                        StringShyMs = FMath::Max(StringShyMs, Beat->Space.Mount.Rules.FearRecoverMs);
                        if (!State.bSpookedHorses) Raise(TEXT("ai:horse_spooked:convoy"));
                    }
            State.bSpookedHorses = bNear;
            continue;
        }
        // A head in the spot, above the water, not under the reeds' and
        // lotus' leaves (ch06.b02), and in a clear line from the lamp.
        const FVector Head = Player->GetCamera()->GetComponentLocation();
        bool bInSpot = !IsDiving() && !UnderCover(Player->GetActorLocation()) && FVector::Dist2D(Head, At) <= Row.Rules.SpotCm * .5f;
        if (bInSpot)
        {
            FCollisionQueryParams Query(SCENE_QUERY_STAT(SoraSearchlight), false, Player);
            Query.AddIgnoredActor(Props);
            for (const auto* List : {&Party, &Allies, &People})
                for (const auto& Companion : *List)
                    if (IsValid(Companion)) Query.AddIgnoredActor(Companion);
            FHitResult Hit;
            bInSpot = !GetWorld()->LineTraceSingleByChannel(Hit, From + (Head - From).GetSafeNormal() * 100.f, Head, ECC_Visibility, Query);
        }
        const Craft::ESpotted Seen = Craft::Spotted(State.InSpotMs, bInSpot, DtMs, Row.Rules);
        if (Seen == Craft::ESpotted::None || !Stealth || !Stealth->IsZoneActive()) continue;
        // The guards on the wall see what the light shows them.
        ASoraEnemy* Nearest = nullptr;
        float Best = MAX_flt;
        for (TActorIterator<ASoraEnemyController> It(GetWorld()); It; ++It)
        {
            auto* Guard = Cast<ASoraEnemy>(It->GetPawn());
            if (!Guard || !Guard->IsAlive() || !It->IsGuard()) continue;
            const float Distance = FVector::Dist2D(Guard->GetActorLocation(), At);
            if (Distance > Layout::LightWatchCm) continue;
            if (Distance < Best) { Best = Distance; Nearest = Guard; }
            if (Seen == Craft::ESpotted::Suspicious)
                It->HearNoise(SoraStealthRules::ENoise::Lure, Guard->GetActorLocation(), Head, nullptr);
        }
        Raise(Seen == Craft::ESpotted::Suspicious ? TEXT("ai_event:searchlight_suspicious") : TEXT("ai_event:searchlight_alert"));
        if (Seen == Craft::ESpotted::Alert && Nearest)
            Stealth->RaiseAlarm(*Nearest, Player->GetActorLocation());
    }
}

void USoraFieldcraft::BellStruck()
{
    if (!Staged || !Staged->bBell || !Craft::RingBell(BellUses)) return;
    const FSoraBell& Bell = Staged->Bell;
    const FVector Floor(Bell.At, 0.f);
    Raise(TEXT("lure_triggered:") + Bell.Id);
    // Every guard in earshot that has not placed the hero goes to it and looks it over.
    for (TActorIterator<ASoraEnemyController> It(GetWorld()); It; ++It)
    {
        const auto* Guard = Cast<ASoraEnemy>(It->GetPawn());
        if (!Guard || !Guard->IsAlive() || !It->IsGuard() || Guard->IsBody() ||
            (It->State() != SoraStealthRules::EState::Unaware && It->State() != SoraStealthRules::EState::Suspicious))
            continue;
        const float Distance = FVector::Dist2D(Guard->GetActorLocation(), Floor);
        if (Distance > Bell.Rules.RadiusCm) continue;
        // Round the bell by slot so they do not stand in one another.
        const FVector Goal = Floor + FRotator(0.f, It->GetUniqueID() % 8 * 45.f, 0.f).Vector() * 220.f;
        It->SetErrand(Goal, Floor - Goal, .42f, Bell.Rules.HoldMs + FMath::RoundToInt32(Distance * 1000.f / Layout::BellWalkCmS), true);
    }
}

FVector USoraFieldcraft::BellLocation() const
{
    return Staged && Staged->bBell ? FVector(Staged->Bell.At, Staged->Bell.HeightCm) : FVector::ZeroVector;
}

int32 USoraFieldcraft::FiresOut() const
{
    int32 Out = 0;
    for (const bool bLit : FiresLit) Out += !bLit;
    return Out;
}

FVector USoraFieldcraft::FireLocation(int32 Fire) const
{
    return Staged && Staged->bFires && Staged->Fires.Points.IsValidIndex(Fire) ? FVector(Staged->Fires.Points[Fire], 0.f) : FVector::ZeroVector;
}

void USoraFieldcraft::TickFires()
{
    if (!Staged->bFires) return;
    const auto* Mode = Cast<ASoraGameMode>(GetWorld()->GetAuthGameMode());
    const USoraCampaignDirector* Campaign = Mode ? Mode->Campaign() : nullptr;
    if (!Campaign) return;
    // At each fire_out mark the next fire gutters; the hold waits for it (WorkRatePermille).
    const int32 Progress = SoraBeatRules::ProgressPermille(Campaign->TaskProgress(), Campaign->ActiveTask());
    const int32 Crossed = Craft::MarksCrossed(Staged->Fires.OutAt.GetData(), Staged->Fires.OutAt.Num(), LastProgress, Progress);
    LastProgress = Progress;
    for (int32 Mark = 0; Mark < Crossed; ++Mark)
    {
        const int32 Fire = Craft::GutteringFire(FireMarks++, FiresLit.Num());
        if (!FiresLit.IsValidIndex(Fire) || !FiresLit[Fire]) continue;
        FiresLit[Fire] = false;
        if (IsValid(FireActors[Fire])) FireActors[Fire]->SetLit(false);
        Raise(TEXT("fire_out"));
        Raise(TEXT("fire_out:") + Staged->Fires.Ids[Fire]);
    }
}

int32 USoraFieldcraft::RoofAt(const FVector& Location) const
{
    if (!Staged) return INDEX_NONE;
    return Staged->Ladders.IndexOfByPredicate([&](const FSoraLadder& Ladder)
        { return Ladder.Roof.Contains(Location) && Location.Z > Ladder.HeightCm; });
}

bool USoraFieldcraft::IsOnRoof(const FVector& Location) const
{
    return RoofAt(Location) != INDEX_NONE;
}

bool USoraFieldcraft::LadderJump(ASoraPlayerCharacter& Player)
{
    if (!Staged || Staged->Ladders.IsEmpty() || LadderClimb != INDEX_NONE) return false;
    const FVector At = Player.GetActorLocation();
    const FVector Forward = Player.GetActorForwardVector().GetSafeNormal2D();
    for (int32 Index = 0; Index < Staged->Ladders.Num(); ++Index)
    {
        const FSoraLadder& Ladder = Staged->Ladders[Index];
        const FVector Facing = FRotator(0.f, Ladder.Yaw, 0.f).Vector();
        const FVector Foot(Ladder.Foot, At.Z);
        const FVector Top = Foot + Facing * 140.f;
        // At the foot, facing the roof: up. On the roof at its top, facing out: down.
        const bool bUp = !IsOnRoof(At) && FVector::Dist2D(At, Foot) < Layout::LadderReachCm && FVector::DotProduct(Forward, Facing) > .5f &&
            Player.GetCharacterMovement()->IsMovingOnGround();
        const bool bDown = IsOnRoof(At) && FVector::Dist2D(At, Top) < Layout::LadderReachCm && FVector::DotProduct(Forward, Facing) < -.5f;
        if (!bUp && !bDown) continue;
        LadderClimb = Index;
        bLadderUp = bUp;
        LadderAlong = 0.f;
        Player.StopSprint();
        UCharacterMovementComponent* Movement = Player.GetCharacterMovement();
        Movement->StopMovementImmediately();
        Movement->SetMovementMode(MOVE_Flying);
        Raise(bUp ? TEXT("ladder_up:") + Ladder.Id : TEXT("ladder_down:") + Ladder.Id);
        return true;
    }
    return false;
}

void USoraFieldcraft::TickLadders(float DeltaTime)
{
    ASoraPlayerCharacter* Player = Hero();
    if (Staged->Ladders.IsEmpty() || !Player) return;
    UCharacterMovementComponent* Movement = Player->GetCharacterMovement();
    const float HalfHeight = Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    if (LadderClimb != INDEX_NONE)
    {
        // Up or down the rungs at the ladder's pace; off at the top onto the roof, or at the foot.
        const FSoraLadder& Ladder = Staged->Ladders[LadderClimb];
        const FVector Facing = FRotator(0.f, Ladder.Yaw, 0.f).Vector();
        LadderAlong = FMath::Min(LadderAlong + Craft::LadderCmS * DeltaTime, Ladder.HeightCm);
        const float Height = bLadderUp ? LadderAlong : Ladder.HeightCm - LadderAlong;
        Movement->Velocity = FVector::ZeroVector;
        Player->SetActorLocation(FVector(Ladder.Foot, 0.f) + FVector(0.f, 0.f, Height + HalfHeight + 2.f), false, nullptr,
            ETeleportType::TeleportPhysics);
        if (LadderAlong < Ladder.HeightCm) return;
        const FVector Off = bLadderUp ? FVector(Ladder.Foot, Ladder.HeightCm + HalfHeight + 4.f) + Facing * 150.f
                                      : FVector(Ladder.Foot, HalfHeight + 4.f);
        Player->SetActorLocation(Off, false, nullptr, ETeleportType::TeleportPhysics);
        Movement->SetMovementMode(MOVE_Walking);
        Raise(bLadderUp ? TEXT("roof_reached:") + Ladder.Id : TEXT("ladder_foot:") + Ladder.Id);
        LadderClimb = INDEX_NONE;
        return;
    }
    // A drop off a roof he last stood on: where he lands, and whether the
    // straw took it quietly.
    const FVector At = Player->GetActorLocation();
    if (Movement->IsFalling() && RoofStood != INDEX_NONE && RoofFall == INDEX_NONE)
    {
        RoofFall = RoofStood;
        RoofFallZ = RoofStandZ;
    }
    if (!Movement->IsMovingOnGround()) return;
    RoofStood = RoofAt(At);
    RoofStandZ = At.Z;
    if (RoofFall != INDEX_NONE)
    {
        const FSoraLadder& From = Staged->Ladders[RoofFall];
        RoofFall = INDEX_NONE;
        const int32 Drop = FMath::RoundToInt32(RoofFallZ - At.Z);
        const bool bStraw = Staged->Ladders.ContainsByPredicate([&](const FSoraLadder& Ladder)
            { return Ladder.bStraw && Ladder.Straw.Contains(At); });
        if (Craft::LandingHeard(Drop, bStraw))
        {
            // Heard as far as the roof's script says (drop_noise_cm): the
            // landing's loudness scaled to that reach.
            const FVector Feet = At - FVector(0.f, 0.f, HalfHeight);
            const int32 Loudness = From.DropNoiseCm * 1000 / SoraStealthRules::NoiseRadiusCm(SoraStealthRules::ENoise::Landing);
            if (const USoraStealth* Stealth = USoraStealth::Get(this))
                Stealth->MakeNoise(SoraStealthRules::ENoise::Landing, Feet, Feet, Player, Loudness);
            Raise(TEXT("roof_drop"));
        }
        else if (Drop > Craft::DropNoiseOverCm) Raise(TEXT("roof_drop:straw"));
    }
}
