#include "SoraGameMode.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "SoraAutomationWorld.h"
#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraPlayerCharacter.h"
#include "SoraSaveGame.h"
#include "SoraWorldBuilder.h"
#include "SoraLiftRules.h"
#include "Algo/AllOf.h"
#include "Components/PrimitiveComponent.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/AutomationTest.h"
#include "Templates/UniquePtr.h"

// Builds every chapter's space (FSoraSpace) in a real game world and checks
// that it can be played: a floor under every zone's and road's entry, and
// under every point a beat uses (its entry, anchor, objectives, pickups,
// drop-offs, defended targets, stations, spawns, patrol posts, trigger
// volumes, exit, cache and horse) and every loose collectible, each with room
// for a standing cat (no wall, cover, lantern pole or building overlaps a
// capsule there); production sites stand on their bases where their beats
// restore them; and the hero begins the chapter at its first beat's entry.
namespace SoraCampaignSpace
{
constexpr float CapsuleRadius = 34.f;
constexpr float CapsuleHalfHeight = 88.f;

struct FProbe
{
    FAutomationTestBase& Test;
    UWorld& World;
    const AActor* Hero;
    int32 Points = 0;
    bool bOk = true;
    float HeightCm = 0.f;
    // A trace down meets the beat's authored floor, including the spire.
    bool Floor(const FVector2D& Point, const FString& What)
    {
        FHitResult Hit;
        FCollisionQueryParams Params(SCENE_QUERY_STAT(SpaceFloor), false, Hero);
        const bool bTraced = World.LineTraceSingleByChannel(Hit, FVector(Point.X, Point.Y, HeightCm+60.f), FVector(Point.X, Point.Y, HeightCm-200.f),
            ECC_Visibility, Params);
        const bool bHit = bTraced && FMath::IsNearlyEqual(Hit.ImpactPoint.Z,HeightCm,2.f);
        if (!bHit)
            Test.AddInfo(FString::Printf(TEXT("SORA_SPACE_FLOOR: %s xy=(%.3f,%.3f) expected_z=%.3f traced=%d blocking=%d start_penetrating=%d actor=%s component=%s impact=%s normal=%s"),
                *What, Point.X, Point.Y, HeightCm, bTraced, Hit.bBlockingHit, Hit.bStartPenetrating,
                *GetNameSafe(Hit.GetActor()), *GetNameSafe(Hit.GetComponent()),
                *Hit.ImpactPoint.ToString(), *Hit.ImpactNormal.ToString()));
        ++Points;
        return bHit || (bOk = Test.TestTrue(*(What + TEXT(" stands on a floor")), false));
    }
    // A floor, and room for a standing cat there.
    bool Stand(const FVector2D& Point, const FString& What)
    {
        if (!Floor(Point, What))
            return false;
        FCollisionQueryParams Params(SCENE_QUERY_STAT(SpaceRoom), false, Hero);
        const bool bBlocked = World.OverlapBlockingTestByChannel(FVector(Point.X, Point.Y, HeightCm+CapsuleHalfHeight + 4.f), FQuat::Identity,
            ECC_Pawn, FCollisionShape::MakeCapsule(CapsuleRadius, CapsuleHalfHeight), Params);
        return !bBlocked || (bOk = Test.TestFalse(*(What + TEXT(" has room to stand")), true));
    }
};

bool CheckChapter(FAutomationTestBase& Test, int32 Chapter)
{
    const FString Slot = FSoraAutomationWorld::UniqueSaveSlot(TEXT("CampaignSpace"));
    USoraSaveGame* Save = Cast<USoraSaveGame>(UGameplayStatics::CreateSaveGameObject(USoraSaveGame::StaticClass()));
    if (!Save || !USoraCampaignDirector::SeedCheckpoint(*Save, Chapter, 0) || !UGameplayStatics::SaveGameToSlot(Save, Slot, 0))
        return Test.TestTrue(TEXT("The chapter's opening is seeded"), false);
    FSoraAutomationWorld World;
    const bool bStarted = World.Start(Slot) && World.Tick(1);
    const FSoraChapter& Data = FSoraCatalog::Get().Chapter(Chapter);
    ASoraPlayerCharacter* Hero = World.Player();
    bool bOk = Test.TestTrue(*FString::Printf(TEXT("Chapter %d's world starts"), Chapter + 1), bStarted && Hero && World.Mode());
    if (bOk)
    {
        FProbe Probe{Test, *World.GetTestWorld(), Hero};
        const FString Name = Data.Id;
        bOk &= Test.TestTrue(*(Name + TEXT(": the hero begins at the first beat's entry")),
            FVector2D::Distance(FVector2D(Hero->GetActorLocation()), Data.Space.Start) < 50.f);
        for (const FSoraZone& Zone : Data.Space.Zones)
        {
            Probe.HeightCm=Zone.bHeightBounds&&Zone.MinZ>0?16000:0;
            Probe.Stand(Zone.Entry, Name + TEXT(" ") + Zone.Id + TEXT(" entry"));
            for (const FVector2D& Node : Zone.Route)
                Probe.Floor(Node, Name + TEXT(" ") + Zone.Id + TEXT(" road"));
        }
        Probe.HeightCm=0;
        for (int32 Site = 0; Site < Data.Space.Sites.Num(); ++Site)
        {
            // A trace down meets the site's base above the floor.
            FHitResult Hit;
            const FVector2D At = Data.Space.Sites[Site];
            bOk &= Test.TestTrue(*FString::Printf(TEXT("%s site %d stands on its base"), *Name, Site),
                World.GetTestWorld()->LineTraceSingleByChannel(Hit, FVector(At.X, At.Y, 600.f), FVector(At.X, At.Y, -100.f), ECC_Visibility) &&
                Hit.ImpactPoint.Z > 50.f && World.Mode()->Arena()->NodePositions.IsValidIndex(Site) &&
                FVector2D::Distance(FVector2D(World.Mode()->Arena()->NodePositions[Site]), At) < 1.f);
        }
        for (const FSoraBeat& Beat : Data.Beats)
        {
            const FSoraBeatSpace& Space = Beat.Space;
            const FString What = Beat.Id;
            if(Space.Spire.Enabled()) World.Mode()->Arena()->StageKit(Data,9);
            if(Space.HeightCm>0&&!Space.Summit.Enabled()&&!World.Mode()->Arena()->CampaignLift()) World.Mode()->Arena()->StageKit(Data,10);
            if(Space.HeightCm==0&&World.Mode()->Arena()->CampaignLift()) World.Mode()->Arena()->ClearKit();
            if(Space.Summit.Enabled()) World.Mode()->Arena()->ClearKit();
            Probe.HeightCm=Space.HeightCm;
            Probe.Stand(Space.Entry, What + TEXT(" entry"));
            // A beat that restores a site is worked at the site's own base.
            if (!Data.Space.Sites.Contains(Space.Anchor))
                // The capstan occupies the anchor; its bars are worked from
                // this clear deck position, as LiftMotion boards by input.
                Probe.Stand(Space.Anchor+(Space.Lift.bEnabled?FVector2D(-180,0):FVector2D::ZeroVector), What + TEXT(" anchor"));
            for (const TArray<FVector2D>* Points : {&Space.Objectives, &Space.Pickups, &Space.Dropoffs, &Space.Targets, &Space.Stations})
                for (const FVector2D& Point : *Points)
                    Probe.Stand(Point, What + TEXT(" point"));
            for(int32 Landing=0;Landing<(Space.Lift.bEnabled?3:1);++Landing)
            {
                Probe.HeightCm=Space.Lift.bEnabled?SoraLiftRules::Gantry(Landing+1):Space.HeightCm;
                for(int32 Spawn=0;Spawn<Space.Spawns.Num();++Spawn)
                {
                    if(Space.Spire.Enabled())
                    {
                        if(Spawn>=9&&Spawn<=12) continue; // Drones occupy real air, checked in SpireTraversal.
                        Probe.HeightCm=Space.Spire.Spawns[Spawn].Z;
                    }
                    Probe.Stand(Space.Spawns[Spawn],FString::Printf(TEXT("%s spawn %d landing %d"),*What,Spawn,Landing));
                }
            }
            Probe.HeightCm=Space.HeightCm;
            for (const TArray<FVector2D>& Loop : Space.Patrols)
                for (const FVector2D& Post : Loop)
                    Probe.Stand(Post, What + TEXT(" patrol post"));
            for (const FSoraVolume& Volume : Space.Volumes)
            {
                Probe.HeightCm=Volume.bHeight?Volume.FloorCm:Space.HeightCm;
                Probe.Floor(Volume.Center, What + TEXT(" ") + Volume.Event);
            }
            Probe.HeightCm=Space.Exit.bHeight?Space.Exit.FloorCm:Space.HeightCm;
            Probe.Floor(Space.Exit.Center, What + TEXT(" exit"));
            Probe.HeightCm=Space.HeightCm;
            if (Space.bClosing)
                Probe.Floor(Space.Closing, What + TEXT(" closing anchor"));
            if (Space.bCache)
                Probe.Stand(Space.Cache, What + TEXT(" cache"));
            if (Space.bMount)
                Probe.Floor(Space.Mount.At, What + TEXT(" horse"));
        }
        Probe.HeightCm=0;
        for (const FSoraPickup& Pickup : Data.Space.Pickups)
            Probe.Stand(Pickup.At, Name + TEXT(" ") + Data.Collectibles[Pickup.Collectible].Id);
        bOk &= Probe.bOk;
        // Explore caches stand still while the objective refreshes (many times
        // a second as a hold fills): the same caches again leave the same
        // chest and glow, and caches no longer offered leave.
        TArray<FVector> Caches;
        for (const FSoraBeat& Beat : Data.Beats)
            if (Beat.Space.bCache)
                Caches.Add(ASoraWorldBuilder::Floor(Beat.Space.Cache,Beat.Space.HeightCm));
        if (!Caches.IsEmpty())
        {
            ASoraWorldBuilder* Builder = World.Mode()->Arena();
            Builder->ShowCaches(Caches);
            const TArray<TObjectPtr<AActor>> Glows = Builder->CacheGlows();
            for (int32 Refresh = 0; Refresh < 8; ++Refresh)
                Builder->ShowCaches(Caches);
            bOk &= Test.TestTrue(*(Name + TEXT(": standing caches are not rebuilt as the objective refreshes")),
                Glows.Num() == Caches.Num() && Builder->CacheGlows() == Glows &&
                Algo::AllOf(Glows, [](const TObjectPtr<AActor>& Glow) { return IsValid(Glow); }));
            Builder->ShowCaches({});
            bOk &= Test.TestTrue(*(Name + TEXT(": caches no longer offered leave")), Builder->CacheGlows().IsEmpty() &&
                Algo::AllOf(Glows, [](const TObjectPtr<AActor>& Glow) { return !IsValid(Glow) || Glow->IsActorBeingDestroyed(); }));
        }
        UE_LOG(LogTemp, Display, TEXT("SORA_CAMPAIGN_SPACE: %s zones=%d points=%d"), *Name, Data.Space.Zones.Num(), Probe.Points);
    }
    World.DestroyTestWorld(true);
    World.ForwardErrorMessages(&Test);
    FSoraAutomationWorld::DeleteSaveSlot(Slot);
    return bOk;
}
} // namespace SoraCampaignSpace

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraCampaignSpaceTest,
    "SoraArena.Campaign.Spaces",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraCampaignSpaceTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    FSoraAutomationWorld::IgnoreMissingGeneratedArt(*this);
    AddExpectedMessage(TEXT("SoraArenaAutomation_CampaignSpace_"), ELogVerbosity::Warning, EAutomationExpectedMessageFlags::Contains, -1);
    bool bOk = true;
    for (int32 Chapter = 0; Chapter < FSoraCatalog::ChapterCount; ++Chapter)
        bOk &= SoraCampaignSpace::CheckChapter(*this, Chapter);
    if (bOk)
        UE_LOG(LogTemp, Display, TEXT("SORA_CAMPAIGN_SPACES_OK: eight chapters built and every beat point stands on a floor with room"));
    return bOk;
}
#endif
