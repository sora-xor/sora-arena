#include "SoraGameMode.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "Combat/SoraDamage.h"
#include "Combat/SoraStealth.h"
#include "SoraArmsRules.h"
#include "SoraAutomationWorld.h"
#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraCompanion.h"
#include "SoraEnemy.h"
#include "SoraEnemyController.h"
#include "SoraEnemyTestArena.h"
#include "SoraEquipmentComponent.h"
#include "SoraFieldcraft.h"
#include "SoraFieldcraftRules.h"
#include "SoraPlayerCharacter.h"
#include "SoraSaveGame.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/WorldSettings.h"
#include "InputCoreTypes.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/AutomationTest.h"
#include "Templates/UniquePtr.h"

// The campaign's arms and fieldcraft in real game worlds, through the
// player's keys where the player uses keys: every arm he holds on its group
// key, the mouse wheel and the arms wheel; lamps snuffed by hand, shot out
// and relit, and noisy floors; the look_at, npc_downed and blocking_end
// events and the prompts they show; the escorted party hidden and sent on by
// signal, downed, raised by hand and lost; cells opened, collars cut and the
// healing lance; allies who fight, go down, are raised and join with their
// wave; swimming, diving and drowning; climbing on grip with its ledges and
// falls; tsubute lures; the cupped candle; vaulting low cover; and the
// kusarigama's weighted chain.
namespace SoraFieldcraftAutomation
{
struct FBeatWorld
{
    FAutomationTestBase& Test;
    FString Slot;
    int32 Chapter = 0;
    int32 Beat = 0;
    TUniquePtr<FSoraAutomationWorld> World;
    TArray<FString> Events;
    FDelegateHandle EventsHandle;
    FBeatWorld(FAutomationTestBase& InTest, const TCHAR* Name, int32 InChapter, int32 InBeat)
        : Test(InTest), Slot(FSoraAutomationWorld::UniqueSaveSlot(Name)), Chapter(InChapter), Beat(InBeat)
    {
        FSoraAutomationWorld::IgnoreMissingGeneratedArt(Test);
        FSoraAutomationWorld::IgnoreAbsentSaveSlot(Test, Slot);
    }
    ~FBeatWorld()
    {
        if (World)
        {
            if (USoraFieldcraft* Craft = Fieldcraft()) Craft->OnEvent.Remove(EventsHandle);
            World->DestroyTestWorld(true);
            World->ForwardErrorMessages(&Test);
            World.Reset();
        }
        FSoraAutomationWorld::DeleteSaveSlot(Slot);
    }
    ASoraGameMode* Mode() const { return World->Mode(); }
    USoraCampaignDirector* Campaign() const { return Mode()->Campaign(); }
    USoraFieldcraft* Fieldcraft() const { return World ? USoraFieldcraft::Get(World->GetTestWorld()) : nullptr; }
    USoraStealth* Stealth() const { return USoraStealth::Get(World->GetTestWorld()); }
    ASoraPlayerCharacter* Hero() const { return World->Player(); }
    const FSoraBeat& BeatData() const { return Campaign()->ActiveChapter()->Beats[Beat]; }
    const FSoraFieldcraft& Craft() const { return BeatData().Space.Fieldcraft; }
    bool Start()
    {
        USoraSaveGame* Save = Cast<USoraSaveGame>(UGameplayStatics::CreateSaveGameObject(USoraSaveGame::StaticClass()));
        if (!Save || !USoraCampaignDirector::SeedCheckpoint(*Save, Chapter, Beat) || !UGameplayStatics::SaveGameToSlot(Save, Slot, 0))
            return Test.TestTrue(TEXT("The beat's checkpoint is seeded"), false);
        World = MakeUnique<FSoraAutomationWorld>();
        if (!World->Start(Slot) || !World->Tick(1) || !World->EnableKeyInput() || !World->PressKey(EKeys::Enter) ||
            !World->PressKey(EKeys::Enter) || !World->PressKey(EKeys::Enter))
        {
            World->ForwardErrorMessages(&Test);
            return Test.TestTrue(TEXT("The beat's world starts"), false);
        }
        if (USoraFieldcraft* Craft = Fieldcraft())
            EventsHandle = Craft->OnEvent.AddLambda([this](FName Event) { Events.Add(Event.ToString()); });
        return Test.TestTrue(TEXT("The beat is in play"), Mode()->IsPlaying() && Campaign()->ActiveBeat() == Beat);
    }
    bool Tick(int32 Frames, float DeltaSeconds = 1.f / 60.f)
    {
        if (World->Tick(Frames, DeltaSeconds))
            return true;
        World->ForwardErrorMessages(&Test);
        return Test.TestTrue(TEXT("The world ticks"), false);
    }
    bool Press(const FKey& Key)
    {
        return World->PressKey(Key) || Test.TestTrue(TEXT("A key press reaches the hero"), false);
    }
    // A key held down for Frames world frames, then let go.
    bool Hold(const FKey& Key, int32 Frames)
    {
        return World->InjectKey(Key, IE_Pressed) && Tick(Frames) && World->InjectKey(Key, IE_Released) && Tick(1);
    }
    void Harden() const
    {
        Hero()->MaxHealth = 100000.f;
        Hero()->Health = Hero()->MaxHealth;
    }
    void Stand(const FVector& At) const
    {
        ASoraPlayerCharacter* Player = Hero();
        Player->GetCharacterMovement()->StopMovementImmediately();
        Player->SetActorLocation(FVector(At.X, At.Y, Player->GetActorLocation().Z), false, nullptr, ETeleportType::TeleportPhysics);
    }
    void Stand(const FVector& At, float Yaw) const
    {
        Stand(At);
        Look(FRotator(0.f, Yaw, 0.f));
    }
    void Look(const FRotator& Rotation) const
    {
        if (AController* Controller = Hero()->GetController()) Controller->SetControlRotation(Rotation);
        Hero()->FaceRotation(Rotation, 0.f);
        // In play the camera manager turns the eye to the view, pitch and all
        // (UCameraComponent::bUsePawnControlRotation). This world's controller
        // has no local player, so APlayerCameraManager::UpdateCamera never runs
        // and the eye would keep the body's level gaze: it is set here as that
        // update sets it.
        Hero()->GetCamera()->SetWorldRotation(Rotation);
    }
    // The hero's eye turned on a point.
    void LookAt(const FVector& Point) const
    {
        Look((Point - Hero()->GetCamera()->GetComponentLocation()).Rotation());
    }
    bool Raised(const FString& Event) const { return Events.Contains(Event); }
    // The ways round a point the hero tries until one has nothing in between.
    static constexpr float Sides[] = {180.f, 0.f, 90.f, -90.f, 135.f, -135.f, 45.f, -45.f};
    // The hero's eye turned on Point from Distance away until Event is raised
    // (looks are checked ten times a second); false only if the world stops.
    bool LookUntil(const FString& Event, const FVector& Point, float Distance)
    {
        for (const float Side : Sides)
        {
            Stand(Point + FRotator(0.f, Side, 0.f).Vector() * Distance);
            for (int32 Frame = 0; Frame < 20 && !Raised(Event); ++Frame)
            {
                LookAt(Point);
                if (!Tick(1)) return false;
            }
            if (Raised(Event)) return true;
        }
        Test.AddInfo(FString::Printf(TEXT("%s was never raised; the eye last at %s, the point at %s"), *Event,
            *Hero()->GetCamera()->GetComponentLocation().ToString(), *Point.ToString()));
        return true;
    }
    // The hero stood Distance from Target, facing it, where his eye finds it first.
    bool ClearShot(const AActor& Target, float Distance)
    {
        const FVector Point = Target.GetActorLocation();
        for (const float Side : Sides)
        {
            Stand(Point + FRotator(0.f, Side, 0.f).Vector() * Distance);
            if (!Tick(1)) return false;
            LookAt(Point);
            if (!Tick(1)) return false;
            const UCameraComponent* Camera = Hero()->GetCamera();
            FHitResult Hit;
            const FCollisionQueryParams Query(SCENE_QUERY_STAT(SoraFieldcraftTestShot), false, Hero());
            if (World->GetTestWorld()->LineTraceSingleByChannel(Hit, Camera->GetComponentLocation(),
                Camera->GetComponentLocation() + Camera->GetForwardVector() * (Distance + 200.f), ECC_Visibility, Query) &&
                Hit.GetActor() == &Target)
                return true;
        }
        return Test.TestTrue(TEXT("The hero finds a clear shot"), false);
    }
    // The hero stood Distance from Point, his eye on it, where nothing but
    // the people about him stands between (a volley's ring is marked there).
    bool ClearView(const FVector& Point, float Distance)
    {
        for (const float Side : Sides)
        {
            Stand(Point + FRotator(0.f, Side, 0.f).Vector() * Distance);
            if (!Tick(1)) return false;
            LookAt(Point);
            if (!Tick(1)) return false;
            const UCameraComponent* Camera = Hero()->GetCamera();
            FCollisionQueryParams Query(SCENE_QUERY_STAT(SoraFieldcraftTestView), false, Hero());
            for (TActorIterator<ASoraCompanion> It(World->GetTestWorld()); It; ++It) Query.AddIgnoredActor(*It);
            FHitResult Hit;
            if (World->GetTestWorld()->LineTraceSingleByChannel(Hit, Camera->GetComponentLocation(),
                Camera->GetComponentLocation() + Camera->GetForwardVector() * (Distance + 400.f), ECC_Visibility, Query) &&
                FVector::Dist2D(Hit.ImpactPoint, Point) < 150.f)
                return true;
        }
        return Test.TestTrue(TEXT("The hero finds a clear view"), false);
    }
    int32 Count(const TCHAR* Event) const
    {
        return Events.FilterByPredicate([Event](const FString& Raised) { return Raised == Event; }).Num();
    }
    // A blow from nowhere (a hazard): what an opponent's strike does to a companion.
    static void Hurt(AActor& Victim, float Damage)
    {
        FHitResult Trace; Trace.ImpactPoint = Victim.GetActorLocation(); Trace.Location = Trace.ImpactPoint;
        SoraDamage::Strike(&Victim, Damage, FSoraHit::Hazard(Victim.GetActorLocation()), FVector::UpVector, Trace, nullptr, nullptr);
    }
    bool PromptOn(const TCHAR* Event) const
    {
        const FSoraPrompt* Prompt = Campaign()->CurrentPrompt();
        return Prompt && Prompt->On == Event;
    }
};

FVector Floor(const FVector2D& At) { return FVector(At.X, At.Y, 0.f); }
} // namespace SoraFieldcraftAutomation

using namespace SoraFieldcraftAutomation;

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraFieldcraftArmsTest,
    "SoraArena.Fieldcraft.ArmsSelection",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraFieldcraftArmsTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    // ch08.b03, on foot: every arm the campaign has handed over by then.
    FBeatWorld W(*this, TEXT("FieldcraftArms"), 7, 2);
    if (!W.Start())
        return false;
    W.Harden();
    ASoraPlayerCharacter* Hero = W.Hero();
    USoraCampaignDirector* Campaign = W.Campaign();
    unsigned Expected = 0u;
    for (int32 Id = 0; Id < SoraArmsRules::ArmsCount; ++Id)
        if (Campaign->IsWeaponUnlocked(Id) && Campaign->CanHold(Id, false)) Expected |= 1u << Id;
    TestEqual(TEXT("He can take up every arm the campaign has unlocked"), Hero->HoldableArms(), Expected);
    TestTrue(TEXT("By the final chapter that is nearly the whole armoury"), FMath::CountBits(Expected) >= 19);
    const auto Take = [&](const FKey& Key, int32 Wanted, const TCHAR* What)
    {
        const bool bPressed = W.Press(Key) && W.Tick(20);
        return TestTrue(What, bPressed && Hero->WeaponId == Wanted);
    };
    // Group keys: the group's first arm, then its next; another group; back to the remembered one.
    const int32 FirstGun = SoraArmsRules::Pick(Expected, 3, Hero->WeaponId, INDEX_NONE);
    Take(EKeys::Four, FirstGun, TEXT("4 takes up the first firearm"));
    const int32 SecondGun = SoraArmsRules::Pick(Expected, 3, FirstGun, INDEX_NONE);
    Take(EKeys::Four, SecondGun, TEXT("4 again steps to the next firearm"));
    Take(EKeys::One, 0, TEXT("1 takes up the katana"));
    Take(EKeys::Four, SecondGun, TEXT("4 returns to the firearm last held"));
    Take(EKeys::Gamepad_DPad_Down, SoraArmsRules::Pick(Expected, 1, SecondGun, INDEX_NONE), TEXT("The d-pad's down takes up a polearm"));
    const int32 Chain = SoraArmsRules::Pick(Expected, 4, Hero->WeaponId, INDEX_NONE);
    Take(EKeys::Five, Chain, TEXT("5 takes up the chain and striking arms"));
    // The mouse wheel and a tap on the wheel key step through the ring.
    const int32 After = SoraArmsRules::Next(Expected, Chain, 1);
    Take(EKeys::MouseScrollDown, After, TEXT("The mouse wheel steps to the next arm"));
    Take(EKeys::MouseScrollUp, Chain, TEXT("and back"));
    Take(EKeys::X, After, TEXT("A tap on the arms wheel key steps to the next arm"));
    // Held, the wheel opens and slows the world; the right stick chooses; release takes it up.
    AWorldSettings* Settings = W.World->GetTestWorld()->GetWorldSettings();
    if (!W.World->InjectKey(EKeys::X, IE_Pressed) || !W.Tick(20))
        return false;
    const ASoraPlayerCharacter::FArmsWheel& Wheel = Hero->ArmsWheel();
    TestTrue(TEXT("Holding the wheel key opens the arms wheel on every arm he holds"), Wheel.bOpen && Wheel.Arms.Num() == FMath::CountBits(Expected));
    TestTrue(TEXT("The open wheel slows the world"), FMath::IsNearlyEqual(Settings->CinematicTimeDilation, SoraArmsRules::WheelTimePermille / 1000.f));
    for (int32 Frame = 0; Frame < 4; ++Frame)
        if (!W.World->InjectAxis(EKeys::Gamepad_RightX, 1.f) || !W.World->InjectAxis(EKeys::Gamepad_RightY, 0.f) || !W.Tick(1))
            return false;
    const int32 Sector = SoraArmsRules::Sector(90000, Wheel.Arms.Num());
    TestEqual(TEXT("The stick pushed right points at the ring's right-hand arm"), Wheel.Choice, Sector);
    const int32 Chosen = Wheel.Arms.IsValidIndex(Sector) ? Wheel.Arms[Sector] : INDEX_NONE;
    if (!W.World->InjectAxis(EKeys::Gamepad_RightX, 0.f) || !W.World->InjectKey(EKeys::X, IE_Released) || !W.Tick(20))
        return false;
    TestTrue(TEXT("Releasing the key takes up the chosen arm and closes the wheel"), !Wheel.bOpen && Hero->WeaponId == Chosen);
    TestTrue(TEXT("The world's pace returns"), FMath::IsNearlyEqual(Settings->CinematicTimeDilation, 1.f));
    // Released with the cursor still at the centre, the wheel keeps the arm in hand.
    const int32 Kept = Hero->WeaponId;
    if (!W.World->InjectKey(EKeys::X, IE_Pressed) || !W.Tick(20) || !W.World->InjectKey(EKeys::X, IE_Released) || !W.Tick(2))
        return false;
    TestEqual(TEXT("A wheel closed without a choice changes nothing"), Hero->WeaponId, Kept);
    // The pause key closes the wheel untaken.
    if (!W.World->InjectKey(EKeys::X, IE_Pressed) || !W.Tick(20) || !TestTrue(TEXT("The wheel is open again"), Wheel.bOpen))
        return false;
    if (!W.World->InjectKey(EKeys::Escape, IE_Pressed) || !W.Tick(1))
        return false;
    TestTrue(TEXT("The pause menu opens"), W.Mode()->bMenu);
    TestFalse(TEXT("The pause menu closes the wheel"), Wheel.bOpen);
    TestTrue(TEXT("and restores the world's pace"), FMath::IsNearlyEqual(Settings->CinematicTimeDilation, 1.f));
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraFieldcraftLampsTest,
    "SoraArena.Fieldcraft.LampsAndFloors",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraFieldcraftLampsTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    // ch03.b02: three 行灯 to snuff and six rut puddles.
    FBeatWorld W(*this, TEXT("FieldcraftLamps"), 2, 1);
    if (!W.Start())
        return false;
    W.Harden();
    USoraFieldcraft* Fieldcraft = W.Fieldcraft();
    USoraStealth* Stealth = W.Stealth();
    const FSoraFieldcraft& Craft = W.Craft();
    if (!TestTrue(TEXT("The beat's fieldcraft is staged with its lamps"), Fieldcraft && Fieldcraft->IsStaged() &&
        Fieldcraft->Lamps().Num() == Craft.Lamps.Num() && Craft.Lamps.Num() == 3))
        return false;
    const FVector Lamp = Floor(Craft.Lamps[0].At) + FVector(0.f, 0.f, 50.f);
    const int32 Lit = Stealth->LightAt(Lamp);
    // A short hold snuffs nothing; a full one puts the lamp out and the place goes dark.
    W.Stand(Lamp + FVector(60.f, 0.f, 0.f));
    if (!W.Hold(EKeys::E, 20))
        return false;
    TestTrue(TEXT("A short hold leaves the lamp lit"), Fieldcraft->Lamps()[0]->IsLit());
    if (!W.Hold(EKeys::E, 75))
        return false;
    TestFalse(TEXT("Interact held for a second snuffs the lamp"), Fieldcraft->Lamps()[0]->IsLit());
    TestTrue(TEXT("and the beat hears it"), W.Raised(TEXT("lamp_out:") + Craft.Lamps[0].Id));
    TestTrue(TEXT("The spot beside it goes darker to the guards"), Stealth->LightAt(Lamp) < Lit);
    // The puddles sound under a step.
    const FSoraFloorPatch* Puddle = Craft.Floors.FindByPredicate([](const FSoraFloorPatch& Patch) { return Patch.Kind == TEXT("puddle"); });
    if (TestNotNull(TEXT("The beat has its puddles"), Puddle))
        TestEqual(TEXT("A rut puddle doubles a footstep"), Stealth->SurfaceAt(Floor(Puddle->Area.Center)).StepPermille, 2000);
    // Looking at a lit lamp raises look_at for it and its kind, and the snuff prompt shows.
    const FVector Other = Fieldcraft->Lamps()[1]->Glow();
    W.Stand(Other + FVector(-500.f, 0.f, 0.f));
    for (int32 Frame = 0; Frame < 20 && !W.Raised(TEXT("look_at:") + Craft.Lamps[1].Id); ++Frame)
    {
        W.LookAt(Other);
        if (!W.Tick(1)) return false;
    }
    TestTrue(TEXT("Looking at a lamp raises look_at:<its id>"), W.Raised(TEXT("look_at:") + Craft.Lamps[1].Id));
    TestTrue(TEXT("and look_at:andon"), W.Raised(TEXT("look_at:andon")));
    TestTrue(TEXT("which shows the snuff prompt"), W.PromptOn(TEXT("look_at:andon")));
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraFieldcraftFloodlightTest,
    "SoraArena.Fieldcraft.Floodlight",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraFieldcraftFloodlightTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    // ch05.b02: two 篝火 to smother and the floodlight whose cable an arrow cuts for 10 s.
    FBeatWorld W(*this, TEXT("FieldcraftFloodlight"), 4, 1);
    if (!W.Start())
        return false;
    W.Harden();
    USoraFieldcraft* Fieldcraft = W.Fieldcraft();
    const FSoraFieldcraft& Craft = W.Craft();
    for (TActorIterator<ASoraEnemy> It(W.World->GetTestWorld()); It; ++It) It->Destroy();
    const int32 Flood = Craft.Lamps.IndexOfByPredicate([](const FSoraLamp& Lamp) { return Lamp.Id == TEXT("flood_upper"); });
    const int32 Brazier = Craft.Lamps.IndexOfByPredicate([](const FSoraLamp& Lamp) { return Lamp.Id == TEXT("kagaribi_pond"); });
    if (!TestTrue(TEXT("The beat has its floodlight and brazier"), Flood != INDEX_NONE && Brazier != INDEX_NONE))
        return false;
    // Looking at each raises its look_at, which shows its prompt.
    for (const int32 Index : {Brazier, Flood})
        if (!W.LookUntil(TEXT("look_at:") + Craft.Lamps[Index].Id, Fieldcraft->Lamps()[Index]->Glow(), 600.f))
            return false;
    TestTrue(TEXT("look_at:kagaribi is raised"), W.Raised(TEXT("look_at:kagaribi")));
    TestTrue(TEXT("look_at:flood_upper is raised and shows its prompt"), W.Raised(TEXT("look_at:flood_upper")) && W.PromptOn(TEXT("look_at:flood_upper")));
    // The brazier is smothered by a held hand (1.5 s); the floodlight cannot be.
    W.Stand(Floor(Craft.Lamps[Brazier].At) + FVector(80.f, 0.f, 0.f));
    if (!W.Hold(EKeys::E, 100))
        return false;
    TestFalse(TEXT("A 1.5 s hold smothers the brazier"), Fieldcraft->Lamps()[Brazier]->IsLit());
    // A round on the floodlight's cable junction cuts it, and it comes back on after 10 s.
    ASoraLamp* Lamp = Fieldcraft->Lamps()[Flood];
    FHitResult Trace; Trace.ImpactPoint = Lamp->GetActorLocation(); Trace.Location = Trace.ImpactPoint;
    SoraDamage::Strike(Lamp, 10.f, FSoraHit::Ranged(W.Hero()->GetActorLocation(), 18), FVector::ForwardVector, Trace,
        W.Hero()->GetController(), W.Hero());
    TestFalse(TEXT("An arrow on the junction cuts the floodlight"), Lamp->IsLit());
    // World frames are capped at 0.4 s, so long waits go in quarter seconds.
    if (!W.Tick(44, .25f))
        return false;
    TestTrue(TEXT("It comes back on after ten seconds"), Lamp->IsLit() && W.Raised(TEXT("lamp_lit:flood_upper")));
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraFieldcraftEscortTest,
    "SoraArena.Fieldcraft.EscortParty",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraFieldcraftEscortTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    // ch03.b07: four craftspeople walked through back ways, hidden on the signal.
    FBeatWorld W(*this, TEXT("FieldcraftEscort"), 2, 6);
    if (!W.Start())
        return false;
    W.Harden();
    USoraFieldcraft* Fieldcraft = W.Fieldcraft();
    USoraCampaignDirector* Campaign = W.Campaign();
    // No opponent may reach the party while its rules are examined.
    for (TActorIterator<ASoraEnemy> It(W.World->GetTestWorld()); It; ++It) It->Destroy();
    const TArray<TObjectPtr<ASoraCompanion>>& Party = Fieldcraft->PartyMembers();
    if (!TestEqual(TEXT("The craftspeople walk as people"), Party.Num(), 4) || !TestTrue(TEXT("They are ready to go"), Fieldcraft->PartyReady()))
        return false;
    const auto Walk = [&](int32 Frames)
    {
        const int32 Before = Campaign->TaskProgress().Progress;
        for (int32 Frame = 0; Frame < Frames; ++Frame)
        {
            W.Stand(Campaign->PartyLocation());
            if (!W.Tick(1)) return -1;
        }
        return Campaign->TaskProgress().Progress - Before;
    };
    TestTrue(TEXT("With the hero beside them they walk"), Walk(60) > 0);
    TestTrue(TEXT("and walk as characters along the road"), FVector::Dist2D(Party[0]->GetActorLocation(), Campaign->PartyLocation()) < 600.f);
    // The signal: down, and they stop; again, and they go on.
    if (!W.Press(EKeys::Q))
        return false;
    TestTrue(TEXT("The signal hides them"), Party[0]->IsHiddenAway() && W.Raised(TEXT("signal:hide")) && !Fieldcraft->PartyReady());
    TestEqual(TEXT("Hidden, they do not walk"), Walk(60), 0);
    if (!W.Press(EKeys::Q))
        return false;
    TestTrue(TEXT("The next signal sends them on"), !Party[0]->IsHiddenAway() && W.Raised(TEXT("signal:go")) && Fieldcraft->PartyReady());
    // The hero's own round never hurts them.
    FHitResult Trace; Trace.ImpactPoint = Party[1]->GetActorLocation(); Trace.Location = Trace.ImpactPoint;
    TestEqual(TEXT("No friendly fire"), SoraDamage::Strike(Party[1], 50.f, FSoraHit::Ranged(W.Hero()->GetActorLocation(), 1),
        FVector::ForwardVector, Trace, W.Hero()->GetController(), W.Hero()), 0.f);
    // Downed: the party waits, the beat hears it, the downed are the objective.
    ASoraCompanion* Tokichi = Party[0];
    FBeatWorld::Hurt(*Tokichi, 500.f);
    TestTrue(TEXT("An emptied companion goes down"), Tokichi->IsDown() && !Fieldcraft->PartyReady());
    TestTrue(TEXT("npc_downed:<id> and npc_downed:any are raised"), W.Raised(TEXT("npc_downed:") + Tokichi->CompanionId()) &&
        W.Raised(TEXT("npc_downed:any")));
    TestTrue(TEXT("and the revive prompt shows"), W.PromptOn(TEXT("npc_downed:any")));
    FVector Anchor;
    TestTrue(TEXT("The downed member is the objective, worked with Interact"), Campaign->ObjectiveAnchor(Anchor) &&
        Campaign->AnchorTakesInteract() && FVector::Dist2D(Anchor, Tokichi->GetActorLocation()) < 1.f);
    TestEqual(TEXT("The party waits for them"), Walk(30), 0);
    W.Stand(Tokichi->GetActorLocation() + FVector(40.f, 0.f, 0.f));
    if (!W.Hold(EKeys::E, 135))
        return false;
    TestTrue(TEXT("Interact held two seconds raises them"), !Tokichi->IsDown() && W.Raised(TEXT("npc_revived:any")) && Fieldcraft->PartyReady());
    // Left down past their window, they die and the escort fails to its checkpoint.
    FBeatWorld::Hurt(*Tokichi, 500.f);
    if (!W.Tick(36, .25f))
        return false;
    TestTrue(TEXT("Unattended past eight seconds, the downed die"), Tokichi->IsDead() && W.Raised(TEXT("npc_died:") + Tokichi->CompanionId()));
    TestTrue(TEXT("and the escort fails to its checkpoint"), W.Mode()->bDefeated);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraFieldcraftCellsTest,
    "SoraArena.Fieldcraft.CellsAndLance",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraFieldcraftCellsTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    // ch08.b07: twelve prisoners behind four cell doors, and the healing lance.
    FBeatWorld W(*this, TEXT("FieldcraftCells"), 7, 6);
    if (!W.Start())
        return false;
    W.Harden();
    USoraFieldcraft* Fieldcraft = W.Fieldcraft();
    USoraCampaignDirector* Campaign = W.Campaign();
    for (TActorIterator<ASoraEnemy> It(W.World->GetTestWorld()); It; ++It) It->Destroy();
    const TArray<TObjectPtr<ASoraCompanion>>& Party = Fieldcraft->PartyMembers();
    const FSoraFieldcraft& Craft = W.Craft();
    TestEqual(TEXT("Twelve prisoners wait in their cells"), Party.Num(), 12);
    TestTrue(TEXT("Behind locked doors the party cannot go"), !Fieldcraft->PartyReady() && Party[0]->IsBound());
    for (int32 Door = 0; Door < Craft.Releases.Num(); ++Door)
    {
        FVector Anchor;
        TestTrue(*FString::Printf(TEXT("Cell door %d is the objective"), Door + 1), Campaign->ObjectiveAnchor(Anchor) &&
            Campaign->AnchorTakesInteract() && FVector::Dist2D(Anchor, Floor(Craft.Releases[Door].At)) < 1.f);
        W.Stand(Floor(Craft.Releases[Door].At));
        if (!W.Hold(EKeys::E, 135))
            return false;
        TestTrue(*FString::Printf(TEXT("Interact held opens cell door %d"), Door + 1),
            W.Raised(FString::Printf(TEXT("event:door_%d_open"), Door + 1)));
    }
    TestTrue(TEXT("Every door open, every prisoner free and the party ready"),
        Fieldcraft->PartyReady() && !Party.ContainsByPredicate([](const TObjectPtr<ASoraCompanion>& Member) { return Member->IsBound(); }));
    // The healing lance's round raises the downed a second later.
    ASoraCompanion* Down = Party[3];
    FBeatWorld::Hurt(*Down, 1000.f);
    if (!TestTrue(TEXT("A prisoner goes down"), Down->IsDown()))
        return false;
    ASoraPlayerCharacter* Hero = W.Hero();
    if (!TestTrue(TEXT("The healing lance is in hand"), Hero->GetEquipment()->EquipCampaignWeapon(17)) || !W.Tick(20))
        return false;
    // The freed stand close about their cells: a shot with none of them in the way.
    if (!W.ClearShot(*Down, 300.f) || !W.Press(EKeys::LeftMouseButton) || !W.Tick(70))
        return false;
    TestTrue(TEXT("A lance round raises the downed prisoner"), !Down->IsDown() && W.Raised(TEXT("npc_lanced:") + Down->CompanionId()));
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraFieldcraftCollarsTest,
    "SoraArena.Fieldcraft.Collars",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraFieldcraftCollarsTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    // ch05.b03: six captives in debt collars, cut before they can walk.
    FBeatWorld W(*this, TEXT("FieldcraftCollars"), 4, 2);
    if (!W.Start())
        return false;
    W.Harden();
    USoraFieldcraft* Fieldcraft = W.Fieldcraft();
    for (TActorIterator<ASoraEnemy> It(W.World->GetTestWorld()); It; ++It) It->Destroy();
    const TArray<TObjectPtr<ASoraCompanion>>& Party = Fieldcraft->PartyMembers();
    if (!TestEqual(TEXT("Six captives"), Party.Num(), 6) || !TestTrue(TEXT("collared"), Party[0]->IsBound() && !Fieldcraft->PartyReady()))
        return false;
    ASoraCompanion* Okinu = Party[0];
    if (!W.LookUntil(TEXT("look_at:collar"), Okinu->GetActorLocation() + FVector(0.f, 0.f, 50.f), 400.f))
        return false;
    TestTrue(TEXT("Looking at a collar raises look_at:collar"), W.Raised(TEXT("look_at:collar")) &&
        W.Raised(TEXT("look_at:collar_") + Okinu->CompanionId()));
    TestTrue(TEXT("which shows the collar prompt"), W.PromptOn(TEXT("look_at:collar")));
    for (ASoraCompanion* Captive : Party)
    {
        W.Stand(Captive->GetActorLocation() + FVector(40.f, 0.f, 0.f));
        if (!W.Hold(EKeys::E, 135))
            return false;
        TestTrue(*(Captive->CompanionId() + TEXT("'s collar is cut by a held hand")), !Captive->IsBound() &&
            W.Raised(TEXT("interact_done:collar_") + Captive->CompanionId()));
    }
    TestTrue(TEXT("Every collar cut, the party can walk"), Fieldcraft->PartyReady());
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraFieldcraftAlliesTest,
    "SoraArena.Fieldcraft.Allies",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraFieldcraftAlliesTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    {
        // ch02.b02: two pupils who hold the wicket and go down, and Baio at the bar.
        FBeatWorld W(*this, TEXT("FieldcraftAllies"), 1, 1);
        if (!W.Start())
            return false;
        W.Harden();
        USoraFieldcraft* Fieldcraft = W.Fieldcraft();
        const TArray<TObjectPtr<ASoraCompanion>>& Allies = Fieldcraft->AlliesInPlay();
        if (!TestEqual(TEXT("Three pupils stand with the hero"), Allies.Num(), 3))
            return false;
        ASoraCompanion* Matsukichi = Allies[0];
        ASoraCompanion* Baio = Allies[2];
        TestTrue(TEXT("The wicket's pupil fights with a blade"), Matsukichi->Role() == ASoraCompanion::ERole::Fighter && Matsukichi->WeaponId == 0);
        // An opponent at his post meets his blade.
        for (TActorIterator<ASoraEnemy> It(W.World->GetTestWorld()); It; ++It) It->Destroy();
        ASoraEnemy* Retainer = ASoraEnemy::SpawnArchetype(*W.World->GetTestWorld(), TEXT("blade_retainer"), 0,
            Matsukichi->GetActorLocation() + Matsukichi->GetActorForwardVector() * 150.f, FRotator::ZeroRotator);
        if (!TestNotNull(TEXT("An opponent comes to the wicket"), Retainer))
            return false;
        const float Full = Retainer->Health;
        for (int32 Frame = 0; Frame < 600 && Matsukichi->Strikes() == 0; ++Frame)
            if (!W.Tick(1)) return false;
        TestTrue(TEXT("The pupil strikes the opponent at his post"), Matsukichi->Strikes() > 0);
        AddInfo(FString::Printf(TEXT("The retainer's health after the pupil's blows: %.0f of %.0f"), Retainer->Health, Full));
        Retainer->Destroy();
        // Down, the beat hears it and shows the prompt; a held hand raises him.
        FBeatWorld::Hurt(*Matsukichi, 1000.f);
        TestTrue(TEXT("npc_downed:pupil_matsukichi and :any"), Matsukichi->IsDown() &&
            W.Raised(TEXT("npc_downed:pupil_matsukichi")) && W.Raised(TEXT("npc_downed:any")));
        TestTrue(TEXT("The help-up prompt shows"), W.PromptOn(TEXT("npc_downed:any")));
        W.Stand(Matsukichi->GetActorLocation() + FVector(40.f, 0.f, 0.f));
        if (!W.Hold(EKeys::E, 195))
            return false;
        TestTrue(TEXT("Interact held three seconds raises him"), !Matsukichi->IsDown() && W.Raised(TEXT("npc_revived:pupil_matsukichi")));
        FBeatWorld::Hurt(*Baio, 1000.f);
        TestTrue(TEXT("Baio at the gate bar cannot be downed"), !Baio->IsDown() && Baio->Health == Baio->MaxHealth);
    }
    {
        // ch05.b10: Otane and the League's gunners join with the third wave.
        FBeatWorld W(*this, TEXT("FieldcraftAlliesJoin"), 4, 9);
        if (!W.Start())
            return false;
        const TArray<TObjectPtr<ASoraCompanion>>& Allies = W.Fieldcraft()->AlliesInPlay();
        const auto Joined = [&](const TCHAR* Id)
        {
            const TObjectPtr<ASoraCompanion>* Found = Allies.FindByPredicate([&](const TObjectPtr<ASoraCompanion>& Ally) { return Ally->CompanionId() == Id; });
            return Found && (*Found)->IsJoined();
        };
        TestTrue(TEXT("Tetsugorō fights from the start"), Joined(TEXT("tetsugoro")));
        TestFalse(TEXT("Otane waits for the third wave"), Joined(TEXT("otane")));
        W.Campaign()->FireDialogueTrigger(TEXT("wave_start:3"));
        TestTrue(TEXT("and joins as it comes"), Joined(TEXT("otane")) && Joined(TEXT("league_teppo_a")));
    }
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraFieldcraftWaterTest,
    "SoraArena.Fieldcraft.Water",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraFieldcraftWaterTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    // ch06.b02: the moat, eight seconds of breath, reeds and the float line.
    FBeatWorld W(*this, TEXT("FieldcraftWater"), 5, 1);
    if (!W.Start())
        return false;
    USoraFieldcraft* Fieldcraft = W.Fieldcraft();
    ASoraPlayerCharacter* Hero = W.Hero();
    const FSoraWater& Water = W.Craft().Water;
    for (TActorIterator<ASoraEnemy> It(W.World->GetTestWorld()); It; ++It) It->Destroy();
    // Open water: clear of the reeds and the float line.
    FVector Open = FVector::ZeroVector;
    for (const FVector2D Fraction : {FVector2D(-.3f, .35f), FVector2D(.3f, -.35f), FVector2D(-.3f, -.35f), FVector2D(.3f, .35f)})
    {
        const FVector At = Floor(Water.Area.Center + Water.Area.Size * Fraction);
        const auto Near = [&](const FSoraVolume& Volume) { return Volume.Contains(At) || FVector::Dist2D(Floor(Volume.Center), At) < 600.f; };
        if (!Water.Cover.ContainsByPredicate(Near) && !Water.Lines.ContainsByPredicate(Near)) { Open = At; break; }
    }
    if (!TestFalse(TEXT("The moat has open water"), Open.IsZero()))
        return false;
    W.Stand(Open);
    if (!W.Tick(2))
        return false;
    TestTrue(TEXT("In the moat the hero swims at its pace"), Fieldcraft->IsSwimming() &&
        FMath::IsNearlyEqual(Fieldcraft->HeroPace(), static_cast<float>(Water.Rules.SurfaceCmS)) &&
        Hero->GetCharacterMovement()->MaxWalkSpeed <= Water.Rules.SurfaceCmS + .5f);
    TestEqual(TEXT("At the surface only his head shows"), Fieldcraft->HeroExposure(1000), 450);
    if (!W.Press(EKeys::C) || !W.Tick(2))
        return false;
    TestTrue(TEXT("Crouch dives"), Fieldcraft->IsDiving() && FMath::IsNearlyEqual(Fieldcraft->HeroPace(), static_cast<float>(Water.Rules.DiveCmS)));
    TestEqual(TEXT("Under the water nothing of him shows"), Fieldcraft->HeroExposure(1000), 0);
    const float Health = Hero->Health;
    if (!W.Tick(28, .25f))
        return false;
    TestEqual(TEXT("Seven seconds under costs nothing but breath"), Hero->Health, Health);
    if (!W.Tick(12, .25f))
        return false;
    TestTrue(TEXT("Past eight seconds he drowns"), Hero->Health < Health);
    // Surfaced, his breath comes back (in three seconds of world time; each
    // drowning blow's hit-stop slowed the world a moment before).
    if (!W.Press(EKeys::C))
        return false;
    for (int32 Frame = 0; Frame < 40 && Fieldcraft->Readout(*Hero).Breath < 1.f; ++Frame)
        if (!W.Tick(1, .25f)) return false;
    if (!TestTrue(TEXT("At the surface his breath comes back"), !Fieldcraft->IsDiving() && Fieldcraft->Readout(*Hero).Breath >= 1.f))
        AddInfo(FString::Printf(TEXT("Surfaced: alive %d, playing %d, crouched %d (wanted %d), swimming %d, diving %d, breath %.2f, health %.0f"),
            Hero->IsAlive(), W.Mode()->IsPlaying(), Hero->IsCrouched(), Hero->GetCharacterMovement()->bWantsToCrouch,
            Fieldcraft->IsSwimming(), Fieldcraft->IsDiving(), Fieldcraft->Readout(*Hero).Breath, Hero->Health));
    TestTrue(TEXT("No arm is used in the water"), Fieldcraft->ArmsStowed());
    // Brushing the float line at the surface rings it.
    if (TestTrue(TEXT("The moat has its float line"), Water.Lines.Num() > 0))
    {
        W.Stand(Floor(Water.Lines[0].Center));
        if (!W.Tick(2))
            return false;
        TestTrue(TEXT("The float line rings"), W.Raised(TEXT("ai_event:float_line")));
    }
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraFieldcraftClimbTest,
    "SoraArena.Fieldcraft.Climb",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraFieldcraftClimbTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    // ch06.b03: fourteen holds up the corner stones, two ledges, grip and falls.
    FBeatWorld W(*this, TEXT("FieldcraftClimb"), 5, 2);
    if (!W.Start())
        return false;
    USoraFieldcraft* Fieldcraft = W.Fieldcraft();
    ASoraPlayerCharacter* Hero = W.Hero();
    const FSoraClimbFace& Face = W.Craft().Climb;
    for (TActorIterator<ASoraEnemy> It(W.World->GetTestWorld()); It; ++It) It->Destroy();
    Hero->MaxHealth = 1000.f; Hero->Health = 1000.f;
    W.Stand(Floor(Face.At + FVector2D(-90.f, 0.f)), 0.f);
    if (!W.Tick(2) || !W.Press(EKeys::SpaceBar))
        return false;
    if (!TestTrue(TEXT("Jump at the face's foot reaches for the holds"), Fieldcraft->IsClimbing() && W.Raised(TEXT("climb_start"))))
        return false;
    // Up past the first ledge (3.2 m) to the second (5.8 m), then let go:
    // a fall of over four metres hurts.
    if (!TestEqual(TEXT("The face has its two ledges"), Face.LedgeEvents.Num(), 2) || !W.World->InjectKey(EKeys::W, IE_Pressed))
        return false;
    for (int32 Frame = 0; Frame < 600 && !W.Raised(Face.LedgeEvents[0]); ++Frame)
        if (!W.Tick(1)) return false;
    TestTrue(TEXT("The first ledge raises its volume's event"), W.Raised(Face.LedgeEvents[0]));
    TestTrue(TEXT("and shows its prompt"), W.PromptOn(*Face.LedgeEvents[0]));
    for (int32 Frame = 0; Frame < 600 && !W.Raised(Face.LedgeEvents[1]); ++Frame)
        if (!W.Tick(1)) return false;
    if (!W.World->InjectKey(EKeys::W, IE_Released) || !W.Tick(2))
        return false;
    TestTrue(TEXT("The second ledge raises its volume's event"), W.Raised(Face.LedgeEvents[1]));
    TestTrue(TEXT("Each hold spends grip"), Fieldcraft->Readout(*Hero).Grip < 1.f);
    const float Before = Hero->Health;
    if (!W.Press(EKeys::SpaceBar))
        return false;
    for (int32 Frame = 0; Frame < 240 && !Hero->GetCharacterMovement()->IsMovingOnGround(); ++Frame)
        if (!W.Tick(1)) return false;
    if (!W.Tick(2))
        return false;
    TestTrue(TEXT("Letting go from the ledge is a fall that hurts"), !Fieldcraft->IsClimbing() &&
        FMath::IsNearlyEqual(Before - Hero->Health, static_cast<float>(Face.Rules.HurtHp)));
    // All the way up: over the top is the zone's exit.
    W.Stand(Floor(Face.At + FVector2D(-90.f, 0.f)), 0.f);
    if (!W.Tick(2) || !W.Press(EKeys::SpaceBar) || !W.World->InjectKey(EKeys::W, IE_Pressed))
        return false;
    for (int32 Frame = 0; Frame < 1200 && W.Campaign()->ActiveBeat() == W.Beat; ++Frame)
        if (!W.Tick(1)) return false;
    W.World->InjectKey(EKeys::W, IE_Released);
    TestTrue(TEXT("Over the top the climb ends on the stones"), W.Raised(TEXT("climb_top")) && !Fieldcraft->IsClimbing());
    TestNotEqual(TEXT("and reaching the top is the stealth zone's exit"), W.Campaign()->ActiveBeat(), W.Beat);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraFieldcraftStonesTest,
    "SoraArena.Fieldcraft.Stones",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraFieldcraftStonesTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    // ch06.b06: tsubute from the rubble, thrown to draw a guard.
    FBeatWorld W(*this, TEXT("FieldcraftStones"), 5, 5);
    if (!W.Start())
        return false;
    W.Harden();
    USoraFieldcraft* Fieldcraft = W.Fieldcraft();
    const FSoraStones& Stones = W.Craft().Stones;
    TestEqual(TEXT("He enters without stones"), Fieldcraft->StonesCarried(), 0);
    if (!W.Press(EKeys::Q))
        return false;
    TestTrue(TEXT("With none to throw a notice says where to find them"), W.Mode()->NoticeTime > 0.f && !W.Mode()->NoticeEnglish.IsEmpty());
    W.Stand(Floor(Stones.Piles[0]));
    if (!W.Press(EKeys::E))
        return false;
    TestEqual(TEXT("Interact at the rubble takes up three stones"), Fieldcraft->StonesCarried(), Stones.Max);
    // One auditor, an alarmist, left unaware where the stone will land.
    ASoraEnemy* Guard = nullptr;
    for (TActorIterator<ASoraEnemy> It(W.World->GetTestWorld()); It; ++It)
        if (!Guard && It->IsAlive() && It->ArchetypeId() == TEXT("auditor")) Guard = *It; else It->Destroy();
    if (!TestNotNull(TEXT("An auditor stands in the zone"), Guard))
        return false;
    const ASoraEnemyController* Brain = Cast<ASoraEnemyController>(Guard->GetController());
    // Behind him, so he cannot see the thrower; the stone flies at his back.
    const FVector Back = -Guard->GetActorForwardVector().GetSafeNormal2D();
    W.Stand(Guard->GetActorLocation() + Back * 700.f);
    W.Look(FRotator(0.f, (Guard->GetActorLocation() - W.Hero()->GetActorLocation()).Rotation().Yaw, 0.f));
    if (!W.Tick(1) || !W.Press(EKeys::Q))
        return false;
    TestEqual(TEXT("A throw spends a stone"), Fieldcraft->StonesCarried(), Stones.Max - 1);
    for (int32 Frame = 0; Frame < 240 && !W.Raised(TEXT("lure_triggered")); ++Frame)
        if (!W.Tick(1)) return false;
    TestTrue(TEXT("The stone lands and the beat hears it"), W.Raised(TEXT("lure_triggered")));
    if (!W.Tick(10))
        return false;
    TestTrue(TEXT("The auditor in earshot goes to look"), Brain && Brain->State() == SoraStealthRules::EState::Suspicious);
    TestFalse(TEXT("but a stone never gives the hero away, even to an alarmist"), W.Stealth()->IsDetected());
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraFieldcraftCandleTest,
    "SoraArena.Fieldcraft.Candle",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraFieldcraftCandleTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    // ch06.b08: copying the totals by a carried candle, cupped to hide it.
    FBeatWorld W(*this, TEXT("FieldcraftCandle"), 5, 7);
    if (!W.Start())
        return false;
    W.Harden();
    USoraStealth* Stealth = W.Stealth();
    USoraCampaignDirector* Campaign = W.Campaign();
    const SoraFieldcraftRules::FCandle& Candle = W.Craft().Candle;
    for (TActorIterator<ASoraEnemy> It(W.World->GetTestWorld()); It; ++It) It->Destroy();
    if (!W.Tick(2))
        return false;
    TestEqual(TEXT("The lit candle gives him away"), Stealth->HeroVisibility(), Candle.VisibilityPermille);
    FVector Anchor;
    if (!TestTrue(TEXT("The desks are the objective"), Campaign->ObjectiveAnchor(Anchor)))
        return false;
    W.Stand(Anchor);
    if (!W.Tick(2))
        return false;
    int32 Before = Campaign->TaskProgress().Progress;
    if (!W.Tick(120))
        return false;
    const int32 Open = Campaign->TaskProgress().Progress - Before;
    if (!W.World->InjectKey(EKeys::LeftControl, IE_Pressed) || !W.Tick(2))
        return false;
    TestEqual(TEXT("Guard held cups the candle"), Stealth->HeroVisibility(), Candle.CuppedVisibilityPermille);
    Before = Campaign->TaskProgress().Progress;
    if (!W.Tick(120))
        return false;
    const int32 Cupped = Campaign->TaskProgress().Progress - Before;
    W.World->InjectKey(EKeys::LeftControl, IE_Released);
    TestTrue(TEXT("Cupped, the copying goes at half pace"), Open > 0 && FMath::Abs(Cupped * 2 - Open) <= 20);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraFieldcraftBlockingEndTest,
    "SoraArena.Fieldcraft.BlockingEnd",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraFieldcraftBlockingEndTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    // ch01.b12: Sekireisai's gift; when his blocking lines end, the sheathe prompt.
    FBeatWorld W(*this, TEXT("FieldcraftBlockingEnd"), 0, 11);
    if (!W.Start())
        return false;
    USoraCampaignDirector* Campaign = W.Campaign();
    FVector Anchor;
    if (!TestTrue(TEXT("The katana's stand is the objective"), Campaign->ObjectiveAnchor(Anchor)))
        return false;
    W.Stand(Anchor);
    if (!W.Tick(1) || !W.Press(EKeys::E))
        return false;
    bool bPrompted = false;
    for (int32 Frame = 0; Frame < 3600 && !bPrompted && Campaign->ActiveBeat() == W.Beat; ++Frame)
    {
        if (!W.Tick(1)) return false;
        bPrompted = W.PromptOn(TEXT("blocking_end"));
    }
    TestTrue(TEXT("The last blocking line's end raises blocking_end and shows its prompt"), bPrompted);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraFieldcraftVaultAndChainTest,
    "SoraArena.Fieldcraft.VaultAndChain",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraFieldcraftVaultAndChainTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    SoraEnemyTest::FArena Arena(*this, TEXT("FieldcraftVaultChain"));
    if (!Arena.Start())
        return false;
    ASoraPlayerCharacter* Hero = Arena.Hero();
    // Low cover in front: Jump carries him over it to its far side.
    Arena.PlaceHero(FVector(-540.f, 0.f, 0.f), 0.f);
    Arena.Wall(FVector(-450.f, 0.f, 60.f), FVector(60.f, 400.f, 120.f));
    if (!Arena.Tick(4) || !Arena.World->PressKey(EKeys::SpaceBar))
        return false;
    TestTrue(TEXT("Jump facing low cover vaults it"), Hero->IsVaulting());
    if (!Arena.Tick(40))
        return false;
    TestTrue(TEXT("and lands him beyond it"), !Hero->IsVaulting() && Hero->GetActorLocation().X > -420.f);
    // The kusarigama's weight flies at an opponent beyond the sickle's reach.
    USoraEquipmentComponent* Kit = Hero->GetEquipment();
    if (!TestTrue(TEXT("The kusarigama is in hand"), Kit->EquipCampaignWeapon(2)) || !Arena.Tick(20))
        return false;
    const auto CastAt = [&](const TCHAR* Archetype, float Distance) -> ASoraEnemy*
    {
        for (TActorIterator<ASoraEnemy> It(Arena.Get()); It; ++It) It->Destroy();
        Arena.PlaceHero(FVector::ZeroVector, 0.f);
        ASoraEnemy* Target = Arena.SpawnKind(Archetype, 0, FVector(Distance, 0.f, 0.f), 180.f);
        if (!Target || !Arena.Tick(1)) return nullptr;
        Arena.PlaceHero(FVector::ZeroVector, 0.f);
        if (!Arena.World->PressKey(EKeys::RightMouseButton)) return nullptr;
        TestTrue(FString::Printf(TEXT("The chain is cast at the %s"), Archetype), Kit->IsChainCast());
        return Arena.Tick(30) ? Target : nullptr;
    };
    const int32 Landed = Kit->ChainsLanded();
    ASoraEnemy* Blade = CastAt(TEXT("blade_retainer"), 450.f);
    TestTrue(TEXT("It binds a blade: the retainer staggers"), Blade && Blade->IsStaggered() && Kit->ChainsLanded() == Landed + 1);
    if (!Arena.Tick(60))
        return false;
    ASoraEnemy* Shield = CastAt(TEXT("shield_enforcer"), 500.f);
    TestTrue(TEXT("It pulls a shield's rim aside"), Shield && Shield->IsShieldOpen() && Kit->ChainsLanded() == Landed + 2);
    if (!Arena.Tick(60))
        return false;
    ASoraEnemy* Drone = CastAt(TEXT("drone"), 450.f);
    TestTrue(TEXT("It drags a drone down"), Drone && Drone->Health < Drone->MaxHealth && Kit->ChainsLanded() == Landed + 3);
    return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraFieldcraftVolleyTest,
    "SoraArena.Fieldcraft.Volley",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraFieldcraftVolleyTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    // ch08.b03: three ranks of four League gunners in the outer bailey, on the hero's order.
    FBeatWorld W(*this, TEXT("FieldcraftVolley"), 7, 2);
    if (!W.Start())
        return false;
    W.Harden();
    USoraFieldcraft* Fieldcraft = W.Fieldcraft();
    const FSoraFieldcraft& Craft = W.Craft();
    if (!TestTrue(TEXT("The beat has three volley ranks"), Craft.bVolley && Craft.Volley.Rules.Ranks == 3 && Craft.Volley.PerRank == 4))
        return false;
    int32 Gunners = 0;
    for (const TObjectPtr<ASoraCompanion>& Ally : Fieldcraft->AlliesInPlay())
    {
        if (Ally->VolleyRank() != INDEX_NONE) { ++Gunners; continue; }
        // The rest of the League holds still: only the volley touches the opponents here.
        Ally->SetActorTickEnabled(false);
    }
    TestEqual(TEXT("Twelve gunners stand in their ranks"), Gunners, 12);
    if (!W.Tick(2))
        return false;
    TestTrue(TEXT("The volley's lesson shows its prompt"), W.PromptOn(TEXT("event:volley_tutorial")));
    // Five riflemen in a line from the ring's centre and a shield enforcer, held still.
    for (TActorIterator<ASoraEnemy> It(W.World->GetTestWorld()); It; ++It) It->Destroy();
    const FVector Center = Floor(W.BeatData().Space.Spawns[0]);
    TArray<ASoraEnemy*> Riflemen;
    const auto Hold = [](ASoraEnemy* Enemy)
    {
        if (!Enemy) return;
        Enemy->SetActorTickEnabled(false);
        Enemy->GetCharacterMovement()->SetComponentTickEnabled(false);
        if (AController* Brain = Enemy->GetController()) Brain->SetActorTickEnabled(false);
    };
    for (int32 Index = 0; Index < 5; ++Index)
    {
        ASoraEnemy* Rifleman = ASoraEnemy::SpawnArchetype(*W.World->GetTestWorld(), TEXT("enforcer_rifle"), Index,
            Center + FVector(0.f, Index * 90.f, 120.f), FRotator::ZeroRotator);
        Hold(Rifleman);
        if (!TestNotNull(TEXT("A rifleman stands in the ring"), Rifleman))
            return false;
        Riflemen.Add(Rifleman);
    }
    ASoraEnemy* Shield = ASoraEnemy::SpawnArchetype(*W.World->GetTestWorld(), TEXT("shield_enforcer"), 5,
        Center + FVector(-150.f, 0.f, 120.f), FRotator::ZeroRotator);
    Hold(Shield);
    if (!TestNotNull(TEXT("A shield enforcer stands in the ring"), Shield) || !W.Tick(2))
        return false;
    TArray<float> Full;
    for (const ASoraEnemy* Rifleman : Riflemen) Full.Add(Rifleman->Health);
    const float ShieldFull = Shield->Health;
    // Held, the ring follows his eye; let go, the front rank is ordered.
    if (!W.ClearView(Center, 900.f) || !W.World->InjectKey(EKeys::Q, IE_Pressed) || !W.Tick(10))
        return false;
    const FSoraFieldcraftReadout Marked = Fieldcraft->Readout(*W.Hero());
    TestTrue(TEXT("Holding Ability marks a ring where he looks"), Fieldcraft->IsMarking() && Marked.bMarkValid &&
        FVector::Dist2D(Marked.MarkAt, Center) < 150.f && FMath::IsNearlyEqual(Marked.RingRadius, 400.f));
    if (!W.World->InjectKey(EKeys::Q, IE_Released) || !W.Tick(1))
        return false;
    TestTrue(TEXT("Letting go gives the order"), !Fieldcraft->IsMarking() && Fieldcraft->VolleysOrdered() == 1 &&
        W.Raised(TEXT("event:volley_ordered")));
    if (!W.Tick(30))
        return false;
    TestTrue(TEXT("The front rank fires 800 ms after the order, not before"), Fieldcraft->VolleysFired() == 0 && Riflemen[0]->Health == Full[0]);
    if (!W.Tick(30))
        return false;
    TestTrue(TEXT("and then it fires and files back"), Fieldcraft->VolleysFired() == 1 && W.Raised(TEXT("event:volley_rotate")));
    // 288 split across the nearest four unshielded: 72 each; the fifth untouched; the shield staggered.
    for (int32 Index = 0; Index < Riflemen.Num(); ++Index)
    {
        const float Taken = Full[Index] - (IsValid(Riflemen[Index]) ? FMath::Max(0.f, Riflemen[Index]->Health) : 0.f);
        const float Expected = Index < 4 ? FMath::Min(Full[Index], 72.f) : 0.f;
        TestEqual(*FString::Printf(TEXT("Rifleman %d takes his share of the volley"), Index + 1), Taken, Expected);
    }
    TestTrue(TEXT("The shield enforcer is staggered, not hurt"), Shield->IsStaggered() && Shield->Health == ShieldFull);
    // The next two ranks answer at once; the fourth order finds the first still loading.
    if (!W.Hold(EKeys::Q, 5) || !W.Hold(EKeys::Q, 5))
        return false;
    TestTrue(TEXT("Each rank in turn takes an order"), Fieldcraft->VolleysOrdered() == 3 && W.Raised(TEXT("event:volley_ordered_3")));
    const int32 ReadyCalls = W.Count(TEXT("event:volley_ready"));
    if (!W.Hold(EKeys::Q, 5))
        return false;
    TestTrue(TEXT("A rank still loading refuses the order and says so"), Fieldcraft->VolleysOrdered() == 3 &&
        W.Mode()->NoticeTime > 0.f && !W.Mode()->NoticeEnglish.IsEmpty());
    // Nine seconds on, the first rank stands loaded again and calls it.
    if (!W.Tick(36, .25f))
        return false;
    TestTrue(TEXT("The front rank calls when it stands loaded again"), W.Count(TEXT("event:volley_ready")) > ReadyCalls &&
        Fieldcraft->Readout(*W.Hero()).RankLoaded[0] >= 1.f);
    return true;
}
#endif
