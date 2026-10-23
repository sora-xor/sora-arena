#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraLiftAutomation.h"
#include "SoraFrontEnd.h"
#include "SoraHorse.h"
#include "SoraGameEvents.h"
#include "SoraRecoveryAutomation.h"
#include "SoraSettings.h"
#include "SoraWorldBuilder.h"
#include "GameFramework/InputSettings.h"
#include "Misc/ScopeExit.h"

namespace SoraCargoTest
{
using FWorld=SoraFieldcraftAutomation::FBeatWorld;
// This fixture isolates unload controls. The mounted combat fixture owns
// live threats; freeze them here without changing HP, collisions or damage.
bool Tick(FWorld& W,int32 Frames,float Dt=1.f/60.f)
{
    for(int32 Frame=0;Frame<Frames;++Frame)
    {
        SoraLiftAutomation::HoldThreats(*W.World);
        if(!W.Tick(1,Dt)) return false;
    }
    return true;
}
bool MenuAction(FWorld& W,SoraUI::EAction Action)
{
    auto* Menu=W.Mode()->FrontEnd();
    for(int32 Press=0;Press<12;++Press)
    {
        const auto& Rows=Menu->Rows();
        if(Rows.IsValidIndex(Menu->Focus())&&Rows[Menu->Focus()].Action==Action) return W.Press(EKeys::Enter);
        if(!W.Press(EKeys::Down)) return false;
    }
    return false;
}
bool Restart(FWorld& W)
{
    return W.Press(EKeys::Escape)&&MenuAction(W,SoraUI::EAction::Restart)&&
        MenuAction(W,SoraUI::EAction::ConfirmYes)&&Tick(W,30);
}
bool CargoShown(FWorld& W,int32 Delivered)
{
    auto* C=W.Campaign();
    auto* Kit=W.Mode()->Arena();
    if(!W.Test.TestTrue(TEXT("The cargo display has one pack mare and three authored drying stands"),
        C->PackHorses().Num()==1&&IsValid(C->PackHorses()[0])&&Kit&&Kit->CargoStandCount()==3)) return false;
    bool Okay=W.Test.TestEqual(TEXT("Visible pack load matches accepted unique deliveries"),
        C->PackHorses()[0]->CargoQuantityShown(),30-10*Delivered);
    int32 Total=C->PackHorses()[0]->CargoQuantityShown();
    for(int32 Point=0;Point<3;++Point)
    {
        const int32 Shown=Kit->CargoQuantityShownAt(Point);
        Okay=W.Test.TestEqual(FString::Printf(TEXT("Hamlet %d displays only its completed ten-sheaf share"),Point),
            Shown,Point<Delivered?10:0)&&Okay;
        Total+=Shown;
    }
    return W.Test.TestEqual(TEXT("All thirty sheaves remain on the mare or accepted drying stands"),Total,30)&&Okay;
}
bool AtFirstHamlet(FWorld& W,float Offset)
{
    // Fixture setup once per checkpoint attempt. Subsequent travel to Naka
    // and Shimo uses the ordinary reins and the authored auto-steer road.
    auto* C=W.Campaign();
    if(!W.Test.TestTrue(FString::Printf(TEXT("Cargo hamlet setup requires its mounted checkpoint: beat=%d mounted=%d offset=%.1f"),
        C->ActiveBeat(),C->IsMounted(),Offset),C->IsMounted()&&C->ActiveBeat()==13)) return false;
    const auto& Road=C->ActiveChapter()->Space.Zones[C->ActiveSpace()->Zone];
    const FVector2D Point=C->ActiveSpace()->Dropoffs[0];
    const float Along=Road.ChainageOf(Point);
    C->Steed()->Place(FVector(Road.PointAlong(Along+Offset),0),Road.HeadingAt(Along));
    return Tick(W,4);
}
bool RideTo(FWorld& W,int32 Point)
{
    const FVector Destination(W.Campaign()->ActiveSpace()->Dropoffs[Point],0);
    if(!W.World->InjectKey(EKeys::W,IE_Pressed)||!W.World->InjectKey(EKeys::LeftShift,IE_Pressed)) return false;
    for(int32 Frame=0;Frame<6000&&FVector::Dist2D(W.Hero()->GetActorLocation(),Destination)>320.f;++Frame)
    {
        if(!Tick(W,1)) return false;
        auto* C=W.Campaign();
        if(!C->IsMounted())
        {
            // Frozen opponents still frighten Kurimaru. Honor that real
            // dismount, then use this fixture's rebound Interact to remount.
            // No threat, fear policy, damage or collision is disabled.
            if(!W.Test.TestTrue(FString::Printf(TEXT("Cargo travel interruption is an authored spook: destination=%d frame=%d beat=%d spooked=%d distance=%.3f health=%.1f"),
                Point,Frame,C->ActiveBeat(),C->Steed()&&C->Steed()->IsSpooked(),
                FVector::Dist2D(W.Hero()->GetActorLocation(),Destination),W.Hero()->Health),
                C->ActiveBeat()==13&&C->Steed()&&C->Steed()->IsSpooked()&&!W.Mode()->bDefeated)) return false;
            W.Test.AddInfo(FString::Printf(TEXT("Cargo travel remount after spook: destination=%d frame=%d"),Point,Frame));
            if(!W.Press(EKeys::G)||!W.Test.TestTrue(TEXT("Rebound Interact remounts beside the frightened horse"),C->IsMounted())) return false;
        }
    }
    if(!W.World->InjectKey(EKeys::W,IE_Released)||!W.World->InjectKey(EKeys::LeftShift,IE_Released)||
        !W.World->InjectKey(EKeys::S,IE_Pressed)||!Tick(W,55)||!W.World->InjectKey(EKeys::S,IE_Released)) return false;
    return W.Test.TestTrue(TEXT("Ordinary reins stop within the named hamlet's saddle reach"),
        FVector::Dist2D(W.Hero()->GetActorLocation(),Destination)<420.f&&W.Campaign()->Steed()->SpeedCmS()==0);
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraCargoUnloadTest,"SoraArena.Campaign.CargoUnload",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraCargoUnloadTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraCargoTest;
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    const auto Actions=GetDefault<UInputSettings>()->GetActionMappings();
    FString Controls;
    ON_SCOPE_EXIT
    {
        TestTrue(TEXT("Cargo fixture preserves global action mappings"),GetDefault<UInputSettings>()->GetActionMappings()==Actions);
        if(!Controls.IsEmpty()) TestFalse(TEXT("Cargo fixture deletes its rebound controls"),UGameplayStatics::DoesSaveGameExist(Controls,0));
    };
    FWorld W(*this,TEXT("CargoUnload"),3,13);
    Controls=FSoraAutomationWorld::ControlSlot(W.Slot);
    if(!W.Start()||!Tick(W,30)||!W.Press(EKeys::Escape)||
        !W.Hero()->RemapCombatAction(TEXT("Interact"),EKeys::G)||!W.Press(EKeys::Escape)) return false;
    W.Mode()->Settings()->SetAutoSteer(true);
    auto* C=W.Campaign();
    auto* Events=USoraGameEvents::Get(W.World->GetTestWorld());
    if(!TestNotNull(TEXT("The completed beat can be observed before its kit is removed"),Events)) return false;
    int32 CargoCompletions=0;
    const FDelegateHandle Completed=Events->OnBeatCompleted.AddLambda([&](const FSoraBeatEvent& Event)
    {
        if(Event.BeatId!=TEXT("ch04.b14")) return;
        ++CargoCompletions;
        TestEqual(TEXT("Final delivery has three accepted shares before teardown"),C->TaskProgress().Done,3);
        CargoShown(W,3);
    });
    ON_SCOPE_EXIT { Events->OnBeatCompleted.Remove(Completed); };
    TestEqual(TEXT("The loader retains the authored three-second unload"),C->ActiveTask().UnloadHoldMs,3000);
    TestTrue(TEXT("The ride retains its mounted hero and one loaded pack mare"),C->IsMounted()&&C->PackHorses().Num()==1);
    if(!CargoShown(W,0)) return false;
    if(!AtFirstHamlet(W,300)||!W.Hold(EKeys::E,185)) return false;
    TestTrue(TEXT("The old Interact key cannot start unloading"),!C->IsUnloadingCargo()&&C->TaskProgress().Done==0);
    if(!W.World->InjectKey(EKeys::G,IE_Pressed)||!Tick(W,60)) return false;
    const float Partial=C->HeldWorkProgress();
    TestTrue(TEXT("Mapped Interact starts a partial hold without delivery or Naka ambush"),
        C->IsUnloadingCargo()&&Partial>0&&Partial<.4f&&C->TaskProgress().Done==0&&!SoraBeatRules::Released(C->TaskProgress(),1));
    if(!CargoShown(W,0)) return false;
    if(!W.World->InjectKey(EKeys::G,IE_Released)) return false;
    TestTrue(TEXT("Release cancels before another gameplay tick"),!C->IsUnloadingCargo()&&C->HeldWorkProgress()<0);
    if(!CargoShown(W,0)) return false;
    if(!W.World->InjectKey(EKeys::G,IE_Pressed)||!Tick(W,20)) return false;
    TestTrue(TEXT("Release and re-press between ticks cannot bank the old hold"),C->HeldWorkProgress()>0&&C->HeldWorkProgress()<Partial);
    if(!W.Press(EKeys::Escape)) return false;
    const float Paused=C->HeldWorkProgress();
    const int32 Clock=C->TaskProgress().ElapsedMs;
    const unsigned Waves=C->TaskProgress().Released;
    if(!Tick(W,300)) return false;
    TestTrue(TEXT("The real pause menu freezes work, delivery and ambush release"),W.Mode()->bMenu&&
        C->HeldWorkProgress()==Paused&&C->TaskProgress().ElapsedMs==Clock&&C->TaskProgress().Done==0&&C->TaskProgress().Released==Waves);
    if(!CargoShown(W,0)) return false;
    if(!W.World->InjectKeyPastFrontEnd(EKeys::G,IE_Released)||!Tick(W,1)||!W.Press(EKeys::Escape)||!Tick(W,185)) return false;
    TestTrue(TEXT("A real release while paused cannot resume partial cargo work"),!C->IsUnloadingCargo()&&C->TaskProgress().Done==0);
    if(!W.World->InjectKey(EKeys::G,IE_Pressed)||!Tick(W,20)||!W.World->InjectKey(EKeys::W,IE_Pressed)||!Tick(W,90)) return false;
    TestTrue(TEXT("Riding away while Interact remains down cancels partial unloading"),!C->IsUnloadingCargo()&&C->TaskProgress().Done==0);
    if(!CargoShown(W,0)) return false;
    if(!W.World->InjectKey(EKeys::G,IE_Released)||!W.World->InjectKey(EKeys::W,IE_Released)||!Restart(W)) return false;
    if(!AtFirstHamlet(W,-100)||!W.World->InjectKey(EKeys::G,IE_Pressed)||!Tick(W,60)) return false;
    if(!TestTrue(TEXT("Retry begins with actual partial work"),C->IsUnloadingCargo()&&C->HeldWorkProgress()>0)) return false;
    if(!Restart(W)||!W.World->InjectKey(EKeys::G,IE_Released)) return false;
    TestTrue(TEXT("Checkpoint retry clears partial work and all destination credit"),C->ActiveBeat()==13&&
        C->TaskProgress().Done==0&&!C->IsUnloadingCargo()&&C->HeldWorkProgress()<0&&C->TaskProgress().Released==0);
    if(!CargoShown(W,0)) return false;
    // A completed transfer on foot is also reconstructed from checkpoint
    // state. Keep both horses behind; unloading adds no pack-proximity gate.
    if(!AtFirstHamlet(W,-900)||!W.Press(EKeys::G)||!TestFalse(TEXT("Interact outside the hamlet dismounts normally"),C->IsMounted())) return false;
    const FVector Kami(C->ActiveSpace()->Dropoffs[0],0);
    if(!SoraRecoveryAutomation::WalkTo(*W.World,Kami)||!W.World->InjectKey(EKeys::G,IE_Pressed)||!Tick(W,185)||
        !W.World->InjectKey(EKeys::G,IE_Released)||!CargoShown(W,1)) return false;
    TestTrue(TEXT("On-foot cargo work transfers one share with the pack mare left behind"),
        !C->IsMounted()&&C->TaskProgress().Done==1&&FVector::Dist2D(C->PackHorses()[0]->GetActorLocation(),Kami)>420.f);
    if(!Restart(W)||!CargoShown(W,0)) return false;
    if(!AtFirstHamlet(W,-100)) return false;
    // All three deliveries now occur in one attempt. No direct task/event
    // calls or witness progress mutations are used to finish a destination.
    for(int32 Point=0;Point<3;++Point)
    {
        if(Point>0&&!RideTo(W,Point)) return false;
        if(Point==1&&!TestFalse(TEXT("Arriving at Naka alone cannot release its delivery ambush"),
            SoraBeatRules::Released(C->TaskProgress(),1))) return false;
        if(!W.World->InjectKey(EKeys::G,IE_Pressed)||!Tick(W,149,.02f)) return false;
        TestTrue(TEXT("2.98 seconds cannot complete a fresh cargo unload"),C->ActiveBeat()==13&&C->TaskProgress().Done==Point&&C->IsUnloadingCargo());
        if(!CargoShown(W,Point)) return false;
        if(Point==1) TestFalse(TEXT("A short Naka hold cannot release its ambush"),SoraBeatRules::Released(C->TaskProgress(),1));
        if(!Tick(W,2,.02f)) return false;
        if(Point<2)
        {
            TestEqual(TEXT("The complete hold delivers exactly one share"),C->TaskProgress().Done,Point+1);
            TestEqual(TEXT("The named destination receives exactly once"),C->TaskProgress().DropoffUses[Point],1);
            if(!CargoShown(W,Point+1)) return false;
            if(Point==1) TestTrue(TEXT("Only completed Naka unloading releases its ambush"),SoraBeatRules::Released(C->TaskProgress(),1));
            if(!Tick(W,185)) return false;
            TestEqual(TEXT("Continuing to hold cannot deliver twice"),C->TaskProgress().Done,Point+1);
            if(!CargoShown(W,Point+1)) return false;
        }
        if(!W.World->InjectKey(EKeys::G,IE_Released)||!Tick(W,2)) return false;
    }
    TestTrue(TEXT("All three completed shares advance to the authored next beat once"),
        C->ActiveBeat()==14&&(C->Progress().CompletedMask&SoraBeatRules::BeatBit(13))!=0);
    TestEqual(TEXT("Cargo completed exactly once"),CargoCompletions,1);
    TestEqual(TEXT("The next beat removes the cargo destination display"),W.Mode()->Arena()->CargoStandCount(),0);
    if(!HasAnyErrors()) UE_LOG(LogTemp,Display,TEXT("SORA_CARGO_UNLOAD_OK: mapped hold=3000ms, short hold refused, release/leave cancel, menu frozen, retry reset, three unique deliveries, Naka event gated, visible load 30->20->10->0, each stand 0->10, completed on-foot transfer resets on retry"));
    return !HasAnyErrors();
}
#endif
