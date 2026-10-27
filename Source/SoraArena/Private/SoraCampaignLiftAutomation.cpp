#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraLiftAutomation.h"
#include "SoraLiftRules.h"
#include "SoraEnemy.h"
#include "Components/BoxComponent.h"
#include "GameFramework/DamageType.h"
#include "Misc/AutomationTest.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraCampaignLiftMotionTest,"SoraArena.Campaign.LiftMotion",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraCampaignLiftMotionTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    SoraFieldcraftAutomation::FBeatWorld W(*this,TEXT("LiftMotion"),7,10);
    if(!W.Start()||!W.Tick(30)) return false;
    W.Harden();
    auto* Lift=W.Mode()->Arena()->CampaignLift();
    if(!TestNotNull(TEXT("The authored lift is physically staged"),Lift)) return false;
    TestEqual(TEXT("Deck surface starts at L4, 27 metres"),Lift->Height(),2700.f);
    TestFalse(TEXT("The player starts on the fixed boarding landing"),Lift->Aboard(*W.Hero()));
    if(!W.Press(EKeys::E)) return false;
    TestEqual(TEXT("The capstan cannot be operated from the landing"),W.Campaign()->TaskProgress().Progress,0);
    if(!TestTrue(TEXT("Walking boards the actual deck"),SoraLiftAutomation::Board(*W.World))) return false;
    const float Before=Lift->Height(),RiderOffset=W.Hero()->GetActorLocation().Z-Before;
    if(!W.Press(EKeys::E)) return false;
    TestTrue(TEXT("One turn does not teleport the deck to its new height"),Lift->Height()<Before+20.f);
    for(int32 Frame=0;Frame<64;++Frame)
    {
        const float Previous=Lift->Height();
        if(!W.Tick(1)) return false;
        TestTrue(TEXT("A frame of floor motion stays within the fastest authored cadence"),FMath::Abs(Lift->Height()-Previous)<=4.1f);
        TestTrue(TEXT("CharacterMovement carries the player's capsule on its base"),
            Lift->Aboard(*W.Hero())&&FMath::Abs(W.Hero()->GetActorLocation().Z-Lift->Height()-RiderOffset)<3.f);
        for(const auto& Person:W.Fieldcraft()->PeopleInPlay())
            TestTrue(TEXT("Crew movement bases follow the same moving deck"),Lift->Aboard(*Person)&&FMath::Abs(Person->GetActorLocation().Z-Lift->Height()-90.f)<5.f);
    }
    TestTrue(TEXT("A turn physically raises the deck by one forty-eighth of travel"),
        FMath::IsNearlyEqual(Lift->Height(),static_cast<float>(SoraLiftRules::Height(1000,48000)),.1f));
    if(!W.Tick(180)) return false;
    TestTrue(TEXT("Leaving the wheel idle physically lowers the lift"),Lift->Height()<SoraLiftRules::Height(1000,48000));
    UGameplayStatics::ApplyDamage(W.Hero(),W.Hero()->Health+1000.f,nullptr,nullptr,UDamageType::StaticClass());
    TWeakObjectPtr<ASoraCampaignLift> Old=Lift;
    if(!W.Tick(2)||!W.Mode()->bDefeated||!W.Press(EKeys::Enter)||!W.Tick(30)) return false;
    Lift=W.Mode()->Arena()->CampaignLift();
    TestTrue(TEXT("Retry discards the old lift actor"),!Old.IsValid()||Old->IsActorBeingDestroyed());
    const auto* RetryBase=Cast<UPrimitiveComponent>(W.Hero()->GetMovementBaseObject());
    TestTrue(TEXT("Retry clears any stale movement base"),RetryBase&&RetryBase->GetOwner()==Lift);
    TestEqual(TEXT("Retry builds at the real L4 landing"),Lift->Height(),2700.f);
    TestEqual(TEXT("Retry discards partial turns"),W.Campaign()->TaskProgress().Progress,0);
    TWeakObjectPtr<ASoraCampaignLift> Last=Lift;
    TWeakObjectPtr<ASoraPlayerCharacter> LastHero=W.Hero();
    if(!W.World->EndPlayInTestWorld()) return false;
    TestTrue(TEXT("End-play releases the physical stage"),!Last.IsValid()||!Last->HasActorBegunPlay());
    const auto* LastBase=LastHero.IsValid()?Cast<UPrimitiveComponent>(LastHero->GetMovementBaseObject()):nullptr;
    TestTrue(TEXT("End-play leaves no base owned by the released stage"),!LastBase||LastBase->GetOwner()!=Last.Get());
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraCampaignLiftReloadTest,"SoraArena.Campaign.LiftReload",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraCampaignLiftReloadTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    SoraFieldcraftAutomation::FBeatWorld W(*this,TEXT("LiftReload"),7,10);
    if(!W.Start()) return false;
    W.Harden();
    if(!SoraLiftAutomation::Ride(*W.World)||!SoraLiftAutomation::GalleryFloor(*W.World)) return false;
    auto* Lift=W.Mode()->Arena()->CampaignLift();
    if(!SoraLiftAutomation::Walk(*W.World,Lift->GalleryCache()+FVector(-150,0,0))||!W.Press(EKeys::E)) return false;
    const uint64 Finds=W.Campaign()->CollectedMask();
    TestTrue(TEXT("The gallery is searched before restarting"),(W.Campaign()->Progress().CompletedMask&SoraBeatRules::BeatBit(11))!=0);
    W.Fieldcraft()->OnEvent.Remove(W.EventsHandle);
    if(!W.World->DestroyTestWorld(true)) return false;
    W.World->ForwardErrorMessages(this); W.World.Reset();
    W.World=MakeUnique<FSoraAutomationWorld>();
    if(!W.World->Start(W.Slot)||!W.Tick(1)||!W.World->EnableKeyInput()||
        !W.Press(EKeys::Enter)||!W.Press(EKeys::Enter)||!W.Press(EKeys::Enter)||!W.Tick(30)) return false;
    W.Harden();
    TestEqual(TEXT("Fresh-world reload restores the lift-start checkpoint"),W.Campaign()->ActiveBeat(),10);
    TestFalse(TEXT("Fresh-world reload does not restore a stale gallery phase"),W.Campaign()->InLiftGallery());
    TestEqual(TEXT("Fresh-world reload keeps gallery collectibles"),W.Campaign()->CollectedMask(),Finds);
    TestEqual(TEXT("Fresh-world reload resets physical travel"),W.Mode()->Arena()->CampaignLift()->Height(),2700.f);
    TestEqual(TEXT("Fresh-world reload resets work"),W.Campaign()->TaskProgress().Progress,0);
    if(!SoraLiftAutomation::Ride(*W.World)||!SoraLiftAutomation::Gallery(*W.World,true)) return false;
    TestEqual(TEXT("Reopening the restored gallery creates no additional finds"),W.Campaign()->CollectedMask(),Finds);
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraCampaignLiftEncountersTest,"SoraArena.Campaign.LiftEncounters",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraCampaignLiftEncountersTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    SoraFieldcraftAutomation::FBeatWorld W(*this,TEXT("LiftEncounters"),7,10);
    if(!W.Start()) return false;
    W.Harden();
    auto* Lift=W.Mode()->Arena()->CampaignLift();
    if(!TestTrue(TEXT("The live encounter is boarded through normal movement"),SoraLiftAutomation::Board(*W.World))) return false;
    for(int32 Turn=0;Turn<12;++Turn) if(!W.Tick(66)||!W.Press(EKeys::E)) return false;
    int32 Drones=0;
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
        if(It->IsAlive()&&It->IsFlying())
        {
            ++Drones;
            TestTrue(TEXT("Cutters enter at the first elevated gantry"),It->GetActorLocation().Z>5000.f);
        }
    TestEqual(TEXT("The first wave stages all three real drones"),Drones,3);
    for(int32 Frame=0;Frame<900&&!Lift->CutterTouching();++Frame) if(!W.Tick(1)) return false;
    if(!TestTrue(TEXT("A live 3D flight brings the cutter tip into the hawser"),Lift->CutterTouching())) return false;
    // Wait out the last turn's grace period before measuring physical loss.
    for(int32 Frame=0;Frame<180&&!SoraBeatRules::CrankSlipping(W.Campaign()->TaskProgress(),W.Campaign()->ActiveTask());++Frame)
        if(!W.Tick(1)) return false;
    const int32 Before=W.Campaign()->TaskProgress().Progress;
    if(!W.Tick(120)) return false;
    TestTrue(TEXT("Live cutter contact loses more work than ordinary two-second idle decay"),Before-W.Campaign()->TaskProgress().Progress>960);
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
        if(It->IsAlive()&&It->IsFlying()) SoraFieldcraftAutomation::FBeatWorld::Hurt(**It,1000000.f);
    TestFalse(TEXT("Defeating the cutters clears the physical hazard immediately"),Lift->CutterTouching());
    for(int32 Turn=0;Turn<60&&W.Campaign()->TaskProgress().Progress<36000;++Turn)
        if(!W.Tick(66)||!W.Press(EKeys::E)) return false;
    int32 Boarded=0;
    for(int32 Frame=0;Frame<360;++Frame)
    {
        if(!W.Tick(1)) return false;
        Boarded=0;
        for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
            if(It->IsAlive()&&(It->ArchetypeId()==TEXT("shield_enforcer")||It->ArchetypeId()==TEXT("blade_retainer"))&&Lift->Aboard(**It)) ++Boarded;
        if(Boarded==3) break;
    }
    TestEqual(TEXT("The shield and both retainers jump onto the real moving floor"),Boarded,3);
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraCampaignLiftGalleryTest,"SoraArena.Campaign.LiftGallery",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraCampaignLiftGalleryTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    for(bool Loot:{false,true})
    {
        SoraFieldcraftAutomation::FBeatWorld W(*this,Loot?TEXT("LiftGalleryLoot"):TEXT("LiftGallerySkip"),7,10);
        if(!W.Start()) return false;
        W.Harden();
        TestFalse(TEXT("Gallery cache is unavailable before lift completion"),W.Campaign()->AvailableCaches().Contains(11));
        if(!TestTrue(TEXT("Ordinary input completes the physical 115 metre ride"),SoraLiftAutomation::Ride(*W.World))) return false;
        TestTrue(TEXT("Completion waits for the deck to reach 142 metres"),W.Mode()->Arena()->CampaignLift()->Arrived());
        TestTrue(TEXT("Completed lift unlocks the gallery cache"),W.Campaign()->AvailableCaches().Contains(11));
        const auto Completed=W.Campaign()->Progress().CompletedMask;
        if(!W.Tick(120)) return false;
        TestEqual(TEXT("Waiting in the gallery does not duplicate completion"),W.Campaign()->Progress().CompletedMask,Completed);
        auto* Save=Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(W.Slot,0));
        if(!TestNotNull(TEXT("The lift-start checkpoint remains readable"),Save)) return false;
        TestEqual(TEXT("Arrival does not create a partial-lift save"),Save->CheckpointBeat,10);
        const uint64 Finds=W.Campaign()->CollectedMask();
        if(!TestTrue(TEXT("The optional gallery is traversed through normal movement"),SoraLiftAutomation::Gallery(*W.World,Loot))) return false;
        TestEqual(TEXT("The stair exit starts the summit once"),W.Campaign()->ActiveBeat(),12);
        TestEqual(TEXT("Only searching awards the gallery finds"),W.Campaign()->CollectedMask()!=Finds,Loot);
        Save=Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(W.Slot,0));
        if(!TestNotNull(TEXT("The next authored checkpoint is saved"),Save)) return false;
        TestEqual(TEXT("Walking out starts the summit checkpoint"),Save->CheckpointBeat,12);
        TestEqual(TEXT("Gallery finds persist"),static_cast<uint64>(Save->Collectibles),W.Campaign()->CollectedMask());
    }
    return !HasAnyErrors();
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraCampaignLiftGalleryTimingTest,"SoraArena.Campaign.LiftGalleryTiming",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraCampaignLiftGalleryTimingTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    SoraFieldcraftAutomation::FBeatWorld W(*this,TEXT("LiftGalleryTiming"),7,10);
    if(!W.Start()) return false;
    auto* const Director=W.Campaign();
    constexpr auto Hint=TEXT("ch08.b12.iota.005");
    for(int32 Entry=0;Entry<2;++Entry)
    {
        if(Entry)
        {
            UGameplayStatics::ApplyDamage(W.Hero(),W.Hero()->Health+1000.f,nullptr,nullptr,UDamageType::StaticClass());
            if(!W.Tick(2)||!TestTrue(TEXT("Death opens the ordinary retry flow"),W.Mode()->bDefeated)||
                !W.Press(EKeys::Enter)||!W.Tick(30)) return false;
            if(!TestTrue(TEXT("Retry reuses the director with a fresh lift phase"),W.Campaign()==Director&&
                Director->ActiveBeat()==10&&!Director->InLiftGallery())) return false;
        }
        W.Harden();
        const float DeltaSeconds=Entry?1.f/120.f:1.f/60.f;
        double ActiveSeconds=0.,EntryWorldSeconds=-1.,HintSeconds=-1.;
        int32 HintEntries=0;
        bool bHintQueued=false,bHintShown=false;
        // Observe every world step, including the last turn's arrival. The
        // clock starts at the real gallery transition, never at Ride's return.
        const auto Tick=[&](int32 Frames,float Delta)
        {
            for(int32 Frame=0;Frame<Frames;++Frame)
            {
                const bool bGallery=Director->InLiftGallery();
                const bool bActive=bGallery&&W.Mode()->IsPlaying();
                const double Before=W.World->GetTestWorld()->GetTimeSeconds();
                if(bGallery&&EntryWorldSeconds<0.) EntryWorldSeconds=Before;
                if(!W.Tick(1,Delta)) return false;
                const double Now=W.World->GetTestWorld()->GetTimeSeconds();
                if(bActive) ActiveSeconds+=Now-Before;
                if(!bGallery&&Director->InLiftGallery()) EntryWorldSeconds=Now;
                if(bGallery&&!Director->InLiftGallery())
                    return TestTrue(TEXT("Idle timing remains in the physical gallery"),false);
                const bool bQueued=Director->QueuedSubtitles().ContainsByPredicate([&](const FSoraSubtitle& Line)
                    { return Line.LineId==Hint; });
                if(bQueued&&!bHintQueued)
                {
                    ++HintEntries;
                    if(HintSeconds<0.) HintSeconds=ActiveSeconds;
                }
                bHintQueued=bQueued;
                const auto* Cue=Director->CurrentDialogueCue();
                bHintShown|=Cue&&Cue->Id==Hint;
            }
            return true;
        };
        const auto Press=[&](const FKey& Key,float Delta)
        {
            return W.World->InjectKey(Key,IE_Pressed)&&Tick(1,Delta)&&
                W.World->InjectKey(Key,IE_Released)&&Tick(1,Delta);
        };
        if(!SoraLiftAutomation::Board(*W.World)) return false;
        for(int32 Turn=0;Turn<60&&!Director->InLiftGallery();++Turn)
        {
            if(!Tick(66,1.f/60.f)) return false;
            // Arrival can occur during the wait. Another E would reset
            // production IdleMs, so stop turning once the gallery opens.
            if(Director->InLiftGallery()) break;
            if(!Press(EKeys::E,1.f/60.f)) return false;
            SoraLiftAutomation::HoldThreats(*W.World);
        }
        if(!TestTrue(TEXT("Mapped capstan turns enter the actual gallery"),Director->InLiftGallery()&&
            W.Mode()->Arena()->CampaignLift()->Arrived()&&EntryWorldSeconds>=0.)) return false;
        const double RideTailSeconds=ActiveSeconds;
        TestEqual(TEXT("A fresh gallery has not inherited the previous exit hint"),HintEntries,0);
        for(int32 Frame=0;Frame<(Entry?3602:1802)&&ActiveSeconds<30.;++Frame)
            if(!Tick(1,DeltaSeconds)) return false;
        if(!TestTrue(TEXT("The gallery retains ordinary play for thirty active seconds before its hint"),
            W.Mode()->IsPlaying()&&ActiveSeconds>=30.)) return false;
        if(!Press(EKeys::Escape,DeltaSeconds)) return false;
        if(!TestTrue(TEXT("Mapped Escape pauses the gallery world"),W.Mode()->bMenu&&W.World->GetTestWorld()->IsPaused())) return false;
        const double PausedWorldSeconds=W.World->GetTestWorld()->GetTimeSeconds(),PausedActiveSeconds=ActiveSeconds;
        // Longer than the entire authored delay: neither paused ticks nor
        // a wall-time catch-up on resume may produce the hint.
        const int32 PauseFrames=Entry?7800:3900;
        if(!Tick(PauseFrames,DeltaSeconds)) return false;
        const double PauseWorldDelta=W.World->GetTestWorld()->GetTimeSeconds()-PausedWorldSeconds;
        TestEqual(TEXT("The gallery world stays frozen throughout pause"),W.World->GetTestWorld()->GetTimeSeconds(),PausedWorldSeconds);
        TestEqual(TEXT("Paused frames contribute no gallery active time"),ActiveSeconds,PausedActiveSeconds);
        TestEqual(TEXT("No idle hint is queued under the pause menu"),HintEntries,0);
        if(!Press(EKeys::Escape,DeltaSeconds)) return false;
        TestTrue(TEXT("Mapped resume restores ordinary gallery play"),W.Mode()->IsPlaying()&&!W.World->GetTestWorld()->IsPaused());
        TestEqual(TEXT("Resume does not catch up the paused interval"),HintEntries,0);
        for(int32 Frame=0;Frame<(Entry?3602:1802)&&HintSeconds<0.&&ActiveSeconds<=60.+DeltaSeconds+.001;++Frame)
            if(!Tick(1,DeltaSeconds)) return false;
        TestTrue(TEXT("The observed exit hint starts at sixty active seconds within one world step"),
            HintSeconds>=60.-.001&&HintSeconds<=60.+DeltaSeconds+.001);
        if(!Tick(Entry?1200:600,DeltaSeconds)) return false;
        TestTrue(TEXT("The authored exit hint reaches the displayed dialogue cue"),bHintShown);
        TestEqual(TEXT("The idle hint is queued exactly once per gallery entry"),HintEntries,1);
        AddInfo(FString::Printf(TEXT("SORA_GALLERY_IDLE: entry=%d fps=%d cue=%s entry_world_seconds=%.6f ride_tail_active_seconds=%.6f hint_active_seconds=%.6f pause_requested_seconds=%.6f pause_world_delta=%.6f hint_entries=%d displayed=%d"),
            Entry+1,Entry?120:60,Hint,EntryWorldSeconds,RideTailSeconds,HintSeconds,PauseFrames*static_cast<double>(DeltaSeconds),
            PauseWorldDelta,HintEntries,bHintShown));
    }
    return !HasAnyErrors();
}
#endif
