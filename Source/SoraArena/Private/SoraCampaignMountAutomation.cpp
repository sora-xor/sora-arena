#include "SoraGameMode.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "SoraAutomationWorld.h"
#include "SoraBoss.h"
#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraEnemy.h"
#include "SoraEquipmentComponent.h"
#include "SoraHorse.h"
#include "SoraMountRules.h"
#include "SoraPlayerCharacter.h"
#include "SoraSaveGame.h"
#include "SoraWorldBuilder.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/DamageType.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/AutomationTest.h"
#include "Templates/UniquePtr.h"

// Rides in real game worlds through the player's own keys: Kurimaru tacked
// up at her side (the bit refused twice until she has her barley), refused
// from her left and mounted from her right (bible §4.5, chapter-01 §6.3);
// W walks her on, Shift urges her through the ride's gaits and no further,
// the road's walk-only stretch holds her to a walk, releasing the reins eases
// her to a halt, and a pheasant on the verge spooks her. From the saddle the
// yumi draws only to the left, the katana cuts only to the right and a
// matchlock cannot be held; a convoy walks the road at its pace and waits
// for a rider who rides away from it; the road's drones come as the rider
// passes their marks; the gallop winds her out; a mounted
// fight's rider comes down when its later phase begins; a laden pack mare
// follows on her lead rope; and a ride ends with the rider on the ground at
// the next beat's place.
namespace SoraCampaignMount
{
using SoraMountRules::EGait;

struct FRide
{
    FAutomationTestBase& Test;
    FString Slot = FSoraAutomationWorld::UniqueSaveSlot(TEXT("CampaignMount"));
    TUniquePtr<FSoraAutomationWorld> World;
    explicit FRide(FAutomationTestBase& InTest) : Test(InTest) {}
    ~FRide()
    {
        if (World)
        {
            World->DestroyTestWorld(true);
            World->ForwardErrorMessages(&Test);
            World.Reset();
        }
        FSoraAutomationWorld::DeleteSaveSlot(Slot);
    }
    ASoraGameMode* Mode() const { return World->Mode(); }
    ASoraPlayerCharacter* Hero() const { return World->Player(); }
    USoraCampaignDirector* Campaign() const { return Mode()->Campaign(); }
    ASoraHorse* Horse() const { return Campaign()->Steed(); }
    // A checkpoint at Beat (or its Phase) of Chapter: Enter leaves the title
    // screen, and Enter on the main menu's Continue opens it.
    bool Start(int32 Chapter, int32 Beat, int32 Phase = 0)
    {
        USoraSaveGame* Save = Cast<USoraSaveGame>(UGameplayStatics::CreateSaveGameObject(USoraSaveGame::StaticClass()));
        if (!Save || !USoraCampaignDirector::SeedCheckpoint(*Save, Chapter, Beat, Phase) || !UGameplayStatics::SaveGameToSlot(Save, Slot, 0))
            return Test.TestTrue(TEXT("The ride's checkpoint is seeded"), false);
        World = MakeUnique<FSoraAutomationWorld>();
        if (!World->Start(Slot) || !World->Tick(1) || !World->EnableKeyInput() || !Key(EKeys::Enter) || !Key(EKeys::Enter))
        {
            World->ForwardErrorMessages(&Test);
            return Test.TestTrue(TEXT("The ride's world starts in play"), false);
        }
        return Test.TestTrue(TEXT("The ride's beat is in play"), Mode()->IsPlaying() && Campaign()->ActiveBeat() == Beat);
    }
    bool Key(const FKey& Pressed) { return World->PressKey(Pressed); }
    bool Down(const FKey& Held) { return World->InjectKey(Held, IE_Pressed); }
    bool Up(const FKey& Held) { return World->InjectKey(Held, IE_Released); }
    bool Frames(int32 Count) { return World->Tick(Count); }
    // The hero on the ground beside the horse, in her frame (x toward her head, y to her right).
    void StandAt(float LocalX, float LocalY)
    {
        const ASoraHorse* Beast = Horse();
        const FVector Spot = Beast->GetActorLocation() + Beast->GetActorForwardVector() * LocalX + Beast->GetActorRightVector() * LocalY;
        Hero()->GetCharacterMovement()->StopMovementImmediately();
        Hero()->SetActorLocation(FVector(Spot.X, Spot.Y, Hero()->GetCapsuleComponent()->GetScaledCapsuleHalfHeight() + 2.f),
            false, nullptr, ETeleportType::TeleportPhysics);
    }
    // The rider aims Degrees off her heading (negative: to her left).
    void Aim(float Degrees)
    {
        const FRotator Aim(0, Horse()->GetActorRotation().Yaw + Degrees, 0);
        Hero()->GetController()->SetControlRotation(Aim);
    }
    // The rider's arrows find every opponent standing, so no ambush comes
    // within the horse's fear; returns how many fell.
    int32 ShootDown()
    {
        int32 Fallen = 0;
        for (TActorIterator<ASoraEnemy> It(World->GetTestWorld()); It; ++It)
            if (It->IsAlive() && !It->IsActorBeingDestroyed())
            {
                UGameplayStatics::ApplyDamage(*It, It->Health, Hero()->GetController(), Hero(), UDamageType::StaticClass());
                ++Fallen;
            }
        return Fallen;
    }
    // The ridden horse placed on her road Chainage cm from its start, facing along it.
    void PlaceOnRoad(float Chainage)
    {
        const FSoraChapter& Chapter = *Campaign()->ActiveChapter();
        const FSoraZone& Road = Chapter.Space.Zones[Campaign()->ActiveSpace()->Zone];
        Horse()->Place(ASoraWorldBuilder::Floor(Road.PointAlong(Chainage)), Road.HeadingAt(Chainage));
    }
};

// ch01.b06: tack-up, the right side, walk and trot in their stretches, easing
// down, the pheasant, no weapon in the saddle, and the rider down at the range.
bool TackUpAndFirstRide(FAutomationTestBase& Test)
{
    FRide Ride(Test);
    if (!Ride.Start(0, 5))
        return false;
    USoraCampaignDirector* Campaign = Ride.Campaign();
    const FSoraBeat& Beat = *Campaign->ActiveBeatData();
    bool bOk = Test.TestTrue(TEXT("Kurimaru waits bare at the rail, the hero on foot in the stable lane"),
        Ride.Horse() && !Campaign->IsMounted() && Campaign->TackDone() == 0 && Campaign->HeroZone() == Beat.Space.Zone);
    if (!bOk)
        return false;
    // Tack-up at her right side: kura, girth, abumi, then the bit twice refused
    // until she is given her ear of barley.
    const int32 Pieces = Beat.Space.Mount.Tack.Num();
    int32 Presses = 0;
    for (; Presses < 12 && Campaign->TackDone() < Pieces; ++Presses)
    {
        Ride.StandAt(0.f, 120.f);
        if (!Ride.Key(EKeys::E))
            return false;
    }
    bOk &= Test.TestEqual(TEXT("Four pieces of tack take six presses: the bit is refused twice"), Presses, 6);
    // Her two refusals, the barley and the bit are voiced in that order.
    const TArray<FSoraSubtitle> Lines = Campaign->QueuedSubtitles();
    const auto Queued = [&](const TCHAR* Id) { return Lines.IndexOfByPredicate([&](const FSoraSubtitle& Line) { return Line.LineId == Id; }); };
    const int32 First = Queued(TEXT("ch01.b06.nyaakoto.005")), Second = Queued(TEXT("ch01.b06.takemaru.006"));
    const int32 Barley = Queued(TEXT("ch01.b06.takemaru.007")), Bit = Queued(TEXT("ch01.b06.takemaru.008"));
    bOk &= Test.TestTrue(TEXT("The bit is refused twice and taken after the barley"),
        First != INDEX_NONE && Second > First && Barley > Second && Bit > Barley);
    // A period rider mounts from her right; from her left he is refused.
    Ride.StandAt(0.f, -120.f);
    if (!Ride.Key(EKeys::E))
        return false;
    bOk &= Test.TestTrue(TEXT("Mounting from her left is refused with a notice"),
        !Campaign->IsMounted() && Ride.Mode()->NoticeEnglish.Contains(TEXT("right")));
    Ride.StandAt(0.f, 120.f);
    if (!Ride.Key(EKeys::E))
        return false;
    ASoraPlayerCharacter* Hero = Ride.Hero();
    bOk &= Test.TestTrue(TEXT("Mounting from her right puts the hero in the saddle"),
        Campaign->IsMounted() && Hero->GetAttachParentActor() == Ride.Horse() && Campaign->CurrentPrompt() != nullptr);
    bOk &= Test.TestTrue(TEXT("The rider's eye sits above her back"),
        FMath::IsNearlyEqual(Hero->GetCamera()->GetComponentLocation().Z, ASoraHorse::RiderEyeCm, 12.f));
    // Legs on: she walks on at the lane's 160 cm/s and keeps to the road.
    if (!Ride.Down(EKeys::W) || !Ride.Frames(60))
        return false;
    const FSoraZone& Road = Campaign->ActiveChapter()->Space.Zones[Beat.Space.Zone];
    bOk &= Test.TestTrue(TEXT("W walks her on"), Ride.Horse()->Gait() == EGait::Walk && Ride.Horse()->SpeedCmS() == 160);
    // Shift urges her, but the first 70 m of the lane are ridden at a walk.
    if (!Ride.Down(EKeys::LeftShift) || !Ride.Frames(90))
        return false;
    bOk &= Test.TestEqual(TEXT("The walk-only stretch holds her to a walk"), Ride.Horse()->Gait(), EGait::Walk);
    Ride.PlaceOnRoad(10000.f);
    if (!Ride.Frames(90))
        return false;
    bOk &= Test.TestTrue(TEXT("Urged on the trotting stretch she trots at 360 cm/s"),
        Ride.Horse()->Gait() == EGait::Trot && Ride.Horse()->SpeedCmS() == 360);
    if (!Ride.Frames(120))
        return false;
    bOk &= Test.TestEqual(TEXT("She is never urged past the lane's trot"), Ride.Horse()->Gait(), EGait::Trot);
    const FVector2D Ground(Ride.Horse()->GetActorLocation());
    bOk &= Test.TestTrue(TEXT("Auto-steer keeps her on the road"),
        FVector2D::Distance(Ground, Road.PointAlong(Road.ChainageOf(Ground))) < 300.f);
    // Reins left alone, she eases down a gait each second and a half.
    if (!Ride.Up(EKeys::LeftShift) || !Ride.Up(EKeys::W) || !Ride.Frames(100))
        return false;
    bOk &= Test.TestEqual(TEXT("Left alone she eases to a walk"), Ride.Horse()->Gait(), EGait::Walk);
    if (!Ride.Frames(100))
        return false;
    bOk &= Test.TestEqual(TEXT("Left alone she halts"), Ride.Horse()->Gait(), EGait::Halt);
    // The pheasant flushed from the verge spooks her to a walk.
    Ride.PlaceOnRoad(14000.f);
    if (!Ride.Down(EKeys::W) || !Ride.Down(EKeys::LeftShift) || !Ride.Frames(150))
        return false;
    bOk &= Test.TestTrue(TEXT("The pheasant spooks her"), Ride.Horse()->IsSpooked() && Ride.Horse()->Gait() == EGait::Walk &&
        Campaign->CurrentPrompt() && Campaign->CurrentPrompt()->On == TEXT("horse_spooked"));
    if (!Ride.Up(EKeys::LeftShift) || !Ride.Up(EKeys::W))
        return false;
    // The lane is ridden without arms: the bokuto stays on its rack.
    if (!Ride.Key(EKeys::LeftMouseButton))
        return false;
    bOk &= Test.TestTrue(TEXT("No weapon acts from the saddle on this ride"), Ride.Mode()->NoticeEnglish.Contains(TEXT("saddle")));
    // At the range the ride ends; the rider is down at the next beat's place.
    Ride.PlaceOnRoad(Road.RouteLength - 300.f);
    if (!Ride.Frames(5))
        return false;
    const FSoraBeat* Next = Campaign->ActiveBeatData();
    bOk &= Test.TestTrue(TEXT("Reaching the range ends the ride"), Campaign->ActiveBeat() == 6 && !Campaign->IsMounted() && !Campaign->Steed());
    bOk &= Test.TestTrue(TEXT("The rider is on the ground at the range"), Next && Campaign->HeroZone() == Next->Space.Zone &&
        !Hero->GetAttachParentActor() && Hero->GetCharacterMovement()->MovementMode == MOVE_Walking);
    return bOk;
}

// ch02.b08: mounted archery to the left, the katana to the right, the convoy
// walking ahead and waiting, and the gallop winding her out.
bool MountedArcsConvoyAndWind(FAutomationTestBase& Test)
{
    FRide Ride(Test);
    if (!Ride.Start(1, 7))
        return false;
    USoraCampaignDirector* Campaign = Ride.Campaign();
    USoraEquipmentComponent* Kit = Ride.Hero()->GetEquipment();
    bool bOk = Test.TestTrue(TEXT("The escort ride starts in the saddle with three pack horses"),
        Campaign->IsMounted() && Campaign->PackHorses().Num() == 3);
    // The yumi draws to the left (弓手) and is refused to the right.
    if (!Ride.Key(EKeys::Four) || !Ride.Frames(20))
        return false;
    bOk &= Test.TestEqual(TEXT("The yumi is taken up in the saddle"), Ride.Hero()->WeaponId, 18);
    Ride.Aim(90.f);
    if (!Ride.Down(EKeys::LeftMouseButton) || !Ride.Frames(2))
        return false;
    bOk &= Test.TestTrue(TEXT("The yumi is refused to the right"), !Kit->IsBowDrawing() && Ride.Mode()->NoticeEnglish.Contains(TEXT("left")));
    if (!Ride.Up(EKeys::LeftMouseButton))
        return false;
    Ride.Aim(-90.f);
    if (!Ride.Down(EKeys::LeftMouseButton) || !Ride.Frames(2))
        return false;
    bOk &= Test.TestTrue(TEXT("The yumi draws to the left"), Kit->IsBowDrawing());
    if (!Ride.Up(EKeys::LeftMouseButton) || !Ride.Frames(30))
        return false;
    // The katana cuts to the right (馬手) and is refused to the left.
    if (!Ride.Key(EKeys::Two) || !Ride.Frames(20))
        return false;
    Ride.Aim(-90.f);
    if (!Ride.Key(EKeys::RightMouseButton))
        return false;
    bOk &= Test.TestTrue(TEXT("The katana is refused to the left"), !Kit->IsCommittedStrike() && Ride.Mode()->NoticeEnglish.Contains(TEXT("right")));
    Ride.Aim(90.f);
    if (!Ride.Down(EKeys::RightMouseButton) || !Ride.Frames(1))
        return false;
    bOk &= Test.TestTrue(TEXT("The katana cuts to the right"), Kit->IsCommittedStrike());
    if (!Ride.Up(EKeys::RightMouseButton) || !Ride.Frames(90))
        return false;
    // The convoy walks at its 450 cm/s while the rider keeps up, and waits
    // when he rides away from it.
    TArray<ASoraHorse*> Convoy = Campaign->PackHorses();
    Ride.PlaceOnRoad(Convoy[0]->RoadChainage() - 800.f);
    const float Before = Convoy[0]->RoadChainage();
    if (!Ride.Frames(60))
        return false;
    bOk &= Test.TestTrue(TEXT("The convoy walks at its pace"), FMath::IsNearlyEqual(Convoy[0]->RoadChainage() - Before, 450.f, 30.f));
    // Once the director has seen the rider ride away, the convoy stands.
    Ride.PlaceOnRoad(Convoy[0]->RoadChainage() + 9000.f);
    if (!Ride.Frames(2))
        return false;
    const float Waiting = Convoy[0]->RoadChainage();
    if (!Ride.Frames(60))
        return false;
    bOk &= Test.TestTrue(TEXT("The convoy waits for a rider far ahead"), FMath::IsNearlyEqual(Convoy[0]->RoadChainage(), Waiting, 1.f));
    // Urged to the gallop she runs at 850 cm/s until winded below 20, then
    // canters. The road's drones come as the rider passes their marks, and
    // his arrows bring each down before it can frighten her.
    if (!Ride.Down(EKeys::W) || !Ride.Down(EKeys::LeftShift))
        return false;
    int32 Drones = 0;
    for (int32 Frame = 0; Frame < 200; ++Frame)
    {
        if (!Ride.Frames(1))
            return false;
        Drones += Ride.ShootDown();
    }
    bOk &= Test.TestTrue(TEXT("Urged on she gallops at 850 cm/s"), Ride.Horse()->Gait() == EGait::Gallop && Ride.Horse()->SpeedCmS() == 850);
    for (int32 Frame = 0; Frame < 900 && !Ride.Horse()->IsWinded(); ++Frame)
    {
        if (!Ride.Frames(1))
            return false;
        Drones += Ride.ShootDown();
    }
    bOk &= Test.TestTrue(TEXT("The gallop winds her into a canter"), Ride.Horse()->IsWinded() && Ride.Horse()->Gait() == EGait::Canter &&
        Ride.Horse()->StaminaPoints() < 20);
    bOk &= Test.TestTrue(TEXT("The convoy road's drones come as the rider passes their marks"), Drones > 0);
    return bOk && Ride.Up(EKeys::LeftShift) && Ride.Up(EKeys::W);
}

// ch08.b02: a matchlock is never held in the saddle; the yari thrusts forward.
bool NoFirearmsInTheSaddle(FAutomationTestBase& Test)
{
    FRide Ride(Test);
    if (!Ride.Start(7, 1))
        return false;
    USoraCampaignDirector* Campaign = Ride.Campaign();
    bool bOk = Test.TestTrue(TEXT("The charge starts in the saddle"), Campaign->IsMounted() && Campaign->IsWeaponUnlocked(1));
    const int32 Held = Ride.Hero()->WeaponId;
    if (!Ride.Key(EKeys::One) || !Ride.Frames(20))
        return false;
    bOk &= Test.TestTrue(TEXT("The arc carbine cannot be held in the saddle"),
        Ride.Hero()->WeaponId == Held && Ride.Mode()->NoticeEnglish.Contains(TEXT("saddle")));
    if (!Ride.Key(EKeys::Five) || !Ride.Frames(20))
        return false;
    Ride.Aim(0.f);
    if (!Ride.Down(EKeys::RightMouseButton) || !Ride.Frames(1))
        return false;
    bOk &= Test.TestTrue(TEXT("The yari thrusts forward from the saddle"), Ride.Hero()->WeaponId == 19 &&
        Ride.Hero()->GetEquipment()->IsCommittedStrike());
    return bOk && Ride.Up(EKeys::RightMouseButton);
}

// ch04.b14 and b16: the laden pack mare follows on her rope; the mounted
// fight's rider comes down as its later phase begins.
bool PackMareAndMountedFight(FAutomationTestBase& Test)
{
    bool bOk = true;
    {
        FRide Ride(Test);
        if (!Ride.Start(3, 13))
            return false;
        USoraCampaignDirector* Campaign = Ride.Campaign();
        bOk &= Test.TestTrue(TEXT("The cargo ride leads Bunta on a rope"), Campaign->IsMounted() && Campaign->PackHorses().Num() == 1);
        if (!Ride.Down(EKeys::W) || !Ride.Frames(180) || !Ride.Up(EKeys::W))
            return false;
        const float Rope = FVector::Dist2D(Campaign->PackHorses()[0]->GetActorLocation(), Ride.Horse()->GetActorLocation());
        bOk &= Test.TestTrue(TEXT("Bunta follows at her rope's length"), Rope > 200.f && Rope < 600.f);
    }
    FRide Fight(Test);
    if (!Fight.Start(3, 15))
        return false;
    USoraCampaignDirector* Campaign = Fight.Campaign();
    bOk &= Test.TestTrue(TEXT("The assessor engine is fought from the saddle"), Campaign->IsMounted() && Campaign->CampaignBoss());
    ASoraBoss* Boss = const_cast<ASoraBoss*>(Campaign->CampaignBoss());
    const float Damage = Boss->MaxHealth * .5f;
    UGameplayStatics::ApplyDamage(Boss, Damage, Fight.Hero()->GetController(), Fight.Hero(), UDamageType::StaticClass());
    if (!Fight.Frames(3))
        return false;
    bOk &= Test.TestTrue(TEXT("Its second phase is fought on foot"), Campaign->ActivePhase() == 1 && !Campaign->IsMounted() &&
        Fight.Hero()->GetCharacterMovement()->MovementMode == MOVE_Walking);
    return bOk;
}
} // namespace SoraCampaignMount

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraCampaignMountTest,
    "SoraArena.Campaign.Mount",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraCampaignMountTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraCampaignMount;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    FSoraAutomationWorld::IgnoreMissingGeneratedArt(*this);
    // Each ride's world reads its own isolated slot.
    AddExpectedMessage(TEXT("SoraArenaAutomation_CampaignMount_"), ELogVerbosity::Warning, EAutomationExpectedMessageFlags::Contains, -1);
    const bool bTack = TackUpAndFirstRide(*this);
    const bool bArcs = MountedArcsConvoyAndWind(*this);
    const bool bArms = NoFirearmsInTheSaddle(*this);
    const bool bPack = PackMareAndMountedFight(*this);
    if (bTack && bArcs && bArms && bPack)
        UE_LOG(LogTemp, Display, TEXT("SORA_CAMPAIGN_MOUNT_OK: tack-up, right-side mount, gaits and caps, spook, arcs, convoy, wind, pack mare, mounted fight"));
    return bTack && bArcs && bArms && bPack;
}
#endif
