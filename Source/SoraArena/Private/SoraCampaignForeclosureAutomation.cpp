#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraBoss.h"
#include "SoraEquipmentComponent.h"
#include "SoraGameEvents.h"
#include "SoraSettings.h"
#include "Combat/SoraBossCatalog.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/DamageType.h"
#include "Misc/ScopeExit.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraCampaignForeclosureTest,"SoraArena.Campaign.CollectorCapture",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraCampaignForeclosureTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    SoraFieldcraftAutomation::FBeatWorld W(*this,TEXT("CollectorCapture"),7,13);
    if(!W.Start(0,INDEX_NONE,2)) return false;
    W.Harden();
    W.Mode()->Settings()->SetCampaignDifficulty(SoraAccessibility::EDifficulty::Normal);
    ASoraBoss* Boss=const_cast<ASoraBoss*>(W.Campaign()->CampaignBoss());
    if(!TestNotNull(TEXT("The summit restores its cane-phase collector"),Boss)) return false;
    Boss->Hold(120000);
    USoraGameEvents* Bus=USoraGameEvents::Get(W.World->GetTestWorld());
    if(!TestNotNull(TEXT("Real damage and boss cues are observable"),Bus)) return false;

    // Setup only: hear the existing b09 line through the real dialogue queue
    // without replaying b09-to-b14 traversal in this bounded combat fixture.
    // The cloned trigger is local to this test and removed on every exit.
    FSoraChapter& Chapter=FSoraCatalog::Get().Chapters[7];
    const int32 OriginalTriggers=Chapter.Triggers.Num();
    const auto* MemoryTrigger=Chapter.Triggers.FindByPredicate([](const FSoraDialogueTrigger& T)
        { return T.Beat==13&&T.On==TEXT("event:first_foreclosure"); });
    if(!TestNotNull(TEXT("The authored first-foreclosure memory exists"),MemoryTrigger)) return false;
    FSoraDialogueTrigger Prior=*MemoryTrigger; Prior.On=TEXT("event:fixture_prior_memory");
    Chapter.Triggers.Add(Prior);
    ON_SCOPE_EXIT { Chapter.Triggers.SetNum(OriginalTriggers,EAllowShrinking::No); };

    const FString Memory=TEXT("ch08.b09.sekireisai.003");
    const auto MemoryQueued=[&]()
    {
        return W.Campaign()->QueuedSubtitles().FilterByPredicate([&](const FSoraSubtitle& S) { return S.LineId==Memory; }).Num();
    };
    int32 MemoryStarts=0,Foreclosures=0;
    FString LastLine;
    float DamageFromBoss=0.f;
    const FDelegateHandle Damaged=Bus->OnDamaged.AddLambda([&](const FSoraDamagedEvent& E)
        { if(E.Victim==W.Hero()&&E.Causer==Boss) DamageFromBoss+=E.Amount; });
    const FDelegateHandle Cued=Bus->OnBossPhase.AddLambda([&](const FSoraBossPhaseEvent& E)
    {
        if(E.Boss==Boss&&E.Phase==ESoraBossPhase::Windup&&E.Detail==TEXT("amort_final_foreclosure")) ++Foreclosures;
    });
    ON_SCOPE_EXIT { Bus->OnDamaged.Remove(Damaged); Bus->OnBossPhase.Remove(Cued); };
    const auto Now=[&]() { return W.World->GetTestWorld()->GetTimeSeconds(); };
    const auto Tick=[&](int32 Frames)
    {
        for(int32 Frame=0;Frame<Frames;++Frame)
        {
            if(!W.Tick(1)) return false;
            const auto* Cue=W.Campaign()->CurrentDialogueCue();
            const FString Id=Cue?Cue->Id:FString();
            if(Id==Memory&&LastLine!=Memory) ++MemoryStarts;
            LastLine=Id;
        }
        return true;
    };
    const auto Until=[&](double Time)
    {
        for(int32 Frame=0;Now()<Time&&Frame<2400;++Frame) if(!Tick(1)) return false;
        return TestTrue(TEXT("The live game clock reaches the fixture boundary"),Now()>=Time);
    };
    W.Campaign()->FireDialogueTrigger(TEXT("event:fixture_prior_memory"));
    if(!TestEqual(TEXT("The earlier mentor line is genuinely queued"),MemoryQueued(),1)) return false;
    for(int32 Frame=0;Frame<1200&&W.Campaign()->LinesQueued()>0;++Frame) if(!Tick(1)) return false;
    if(!TestTrue(TEXT("The earlier line finishes and remains heard"),MemoryStarts==1&&W.Campaign()->LinesQueued()==0)) return false;
    W.Campaign()->FireDialogueTrigger(TEXT("event:fixture_prior_memory"));
    TestEqual(TEXT("Ordinary once-only dialogue still does not replay"),MemoryQueued(),0);
    TestFalse(TEXT("Hearing the old line alone does not show the capture prompt"),W.PromptOn(TEXT("event:first_foreclosure")));

    // Another actor's identically named cue must not trigger this encounter.
    FSoraBossPhaseEvent Foreign;
    Foreign.Boss=W.Hero(); Foreign.BossId=TEXT("boss_val_amort"); Foreign.PhaseIndex=2;
    Foreign.Phase=ESoraBossPhase::Windup; Foreign.Detail=TEXT("amort_final_foreclosure");
    Bus->OnBossPhase.Broadcast(Foreign);
    TestTrue(TEXT("A foreign actor cannot produce the Collector tutorial"),
        MemoryQueued()==0&&!W.PromptOn(TEXT("event:first_foreclosure")));

    const auto Ready=[&](int32 Weapon)
    {
        for(int32 Frame=0;Frame<300&&(Boss->BossAttackIndex()!=INDEX_NONE||Boss->IsStaggered());++Frame)
            if(!Tick(1)) return false;
        if(!TestTrue(TEXT("The collector is ready for a new ordinary attack"),Boss->BossAttackIndex()==INDEX_NONE)) return false;
        if(!W.World->TakeUpArm(Weapon)||!TestEqual(TEXT("Mapped arms input equips the intended weapon"),W.Hero()->WeaponId,Weapon)) return false;
        if(!W.Hero()->GetEquipment()->IsSheathing()&&!W.Press(EKeys::V)) return false;
        for(int32 Frame=0;Frame<120&&!W.Hero()->GetEquipment()->IsSheathed();++Frame) if(!Tick(1)) return false;
        if(!TestTrue(TEXT("Mapped Sheathe input completes its existing timing"),W.Hero()->GetEquipment()->IsSheathed())) return false;
        // The boss begins north of the dais. This fixed same-floor stand is
        // clear of its solid spine; the real attack still traces its contact.
        const FVector At=Boss->GetActorLocation();
        const float Floor=At.Z-Boss->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
        W.Hero()->SetBase(static_cast<FMovementBaseInterfaceData*>(nullptr));
        W.Hero()->GetCharacterMovement()->StopMovementImmediately();
        W.Hero()->SetActorLocation(FVector(At.X+220,At.Y,Floor+W.Hero()->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+2),
            false,nullptr,ETeleportType::TeleportPhysics);
        W.LookAt(Boss->GetActorLocation());
        return Tick(2);
    };
    const auto Begin=[&]()
    {
        const int32 Before=Foreclosures;
        if(!TestTrue(TEXT("The real foreclosure can be requested"),Boss->ForceAttack(TEXT("amort_final_foreclosure")))) return false;
        for(int32 Frame=0;Frame<180&&Foreclosures==Before;++Frame) if(!Tick(1)) return false;
        if(!TestTrue(TEXT("The real attack begins its full windup"),
            Foreclosures==Before+1&&Boss->IsBossTelegraphing()&&Boss->BossWarningSeconds()>.8f)) return false;
        return true;
    };
    const auto Meet=[&](bool Capture)
    {
        const float Before=DamageFromBoss;
        for(int32 Frame=0;Frame<180&&Boss->IsBossTelegraphing()&&Boss->BossWarningSeconds()>.10f;++Frame)
            if(!Tick(1)) return false;
        if(!TestTrue(TEXT("Guard is pressed in the last tenth-second of a real eligible cut"),
            Boss->IsBossTelegraphing()&&Boss->BossWarningSeconds()>0&&Boss->BossWarningSeconds()<=.10f)) return false;
        AddInfo(FString::Printf(TEXT("Foreclosure guard: weapon=%d game=%.3f warning=%.3f sheathed=%d boss_health=%.1f hero=%s boss=%s"),
            W.Hero()->WeaponId,Now(),Boss->BossWarningSeconds(),W.Hero()->GetEquipment()->IsSheathed(),Boss->Health,
            *W.Hero()->GetActorLocation().ToString(),*Boss->GetActorLocation().ToString()));
        W.LookAt(Boss->GetActorLocation());
        if(!W.World->InjectKey(EKeys::LeftControl,IE_Pressed)) return false;
        for(int32 Frame=0;Frame<180&&Boss->IsAlive()&&!Boss->IsRecovering();++Frame) if(!Tick(1)) return false;
        if(!W.World->InjectKey(EKeys::LeftControl,IE_Released)) return false;
        AddInfo(FString::Printf(TEXT("Foreclosure result: weapon=%d damage=%.1f alive=%d captive=%d memory_starts=%d"),
            W.Hero()->WeaponId,DamageFromBoss-Before,Boss->IsAlive(),W.Campaign()->AwaitingCapture(),MemoryStarts));
        if(Capture)
            return TestTrue(TEXT("The sheathed katana takes the blade without damage"),
                !Boss->IsAlive()&&DamageFromBoss==Before&&W.Campaign()->AwaitingCapture()&&W.Campaign()->IsCaptive(*Boss));
        return TestTrue(TEXT("A different sheathed arm takes all 45 damage and cannot capture"),
            Boss->IsAlive()&&!W.Campaign()->AwaitingCapture()&&DamageFromBoss-Before==45.f);
    };
    double FirstAt=0;
    for(int32 Weapon:{8,6,4}) // Hammer, kanabo, and another blade.
    {
        if(!Ready(Weapon)||!Begin()) return false;
        if(Weapon==8)
        {
            FirstAt=Now();
            TestTrue(TEXT("The actual first windup shows the authored capture prompt"),W.PromptOn(TEXT("event:first_foreclosure")));
            TestEqual(TEXT("The previously heard mentor memory is replayed exactly once"),MemoryQueued(),1);
            TestTrue(TEXT("The memory remains ambient during the attack"),W.Mode()->IsPlaying()&&!W.Campaign()->IsDialogueBlocking());
        }
        if(!Meet(false)) return false;
    }
    if(!Until(FirstAt+9)) return false;
    TestTrue(TEXT("Only the earlier reading and the first-windup memory have played"),MemoryStarts==2&&MemoryQueued()==0);
    TestFalse(TEXT("The normal tutorial prompt expires instead of refreshing on every attack"),W.PromptOn(TEXT("event:first_foreclosure")));
    if(!Ready(8)||!Begin()) return false;
    TestTrue(TEXT("Later non-floor foreclosures do not replay the tutorial or memory"),
        !W.PromptOn(TEXT("event:first_foreclosure"))&&MemoryQueued()==0);
    if(!Meet(false)) return false;

    // The native floor still cannot be killed by an ordinary finisher. At
    // that floor the authored reminder returns, without another memory read.
    UGameplayStatics::ApplyDamage(Boss,Boss->Health-Boss->MaxHealth*.01f,W.Hero()->GetController(),W.Hero(),UDamageType::StaticClass());
    if(!Ready(8)||!Begin()) return false;
    TestTrue(TEXT("The 1% foreclosure refreshes only the capture reminder"),
        W.PromptOn(TEXT("event:first_foreclosure"))&&MemoryQueued()==0&&MemoryStarts==2);
    if(!Meet(false)||!Ready(0)||!Begin()||!Meet(true)) return false;
    auto* Saved=Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(W.Slot,0));
    TestTrue(TEXT("Capture still waits for the separate held spine cut before saving"),
        W.Campaign()->ActiveBeat()==13&&Saved&&Saved->CheckpointBeat==13&&Saved->CheckpointPhase==2);
    return !HasAnyErrors();
}
#endif
