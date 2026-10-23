#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraClimbAutomation.h"
#include "SoraClimbRules.h"
#include "SoraCatalogClimb.h"
#include "SoraEnemyController.h"
#include "SoraEquipmentComponent.h"
#include "Dom/JsonObject.h"
#include "GameFramework/DamageType.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

namespace SoraClimbTest
{
using FWorld=SoraFieldcraftAutomation::FBeatWorld;
bool Start(FWorld& W)
{
    if(!FSoraCatalog::Get().Load()||!W.Start()) return false;
    // Preserve the live sentry in traversal tests; health only isolates the
    // route from difficulty/aim balance, which this fixture does not accept.
    W.Harden();
    for(int32 F=0;F<600&&!W.Hero()->CanPlay();++F) if(!W.Tick(1)) return SoraClimbAutomation::Note(*W.World,TEXT("Fixture.Start.wait"),false);
    return SoraClimbAutomation::Note(*W.World,TEXT("Fixture.Start.ready"),W.Tick(30)&&W.Hero()->CanPlay());
}
ASoraEnemy* Sentry(FWorld& W)
{
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
        if(W.Fieldcraft()->IsClimbSentry(**It)) return *It;
    return nullptr;
}
ASoraCompanion* Guide(FWorld& W)
{
    for(TActorIterator<ASoraCompanion> It(W.World->GetTestWorld());It;++It)
        if(It->CompanionId()==TEXT("npc_kohagi")) return *It;
    return nullptr;
}
bool Support(FWorld& W,const FVector& Local,float Expected,const TCHAR* Label)
{
    const FVector O(W.BeatData().Space.Climb.Origin,0);FHitResult Hit;
    FCollisionQueryParams Q(SCENE_QUERY_STAT(ClimbSupportFixture),false,W.Hero());
    const bool Found=W.World->GetTestWorld()->LineTraceSingleByChannel(Hit,O+Local+FVector(0,0,20),O+Local-FVector(0,0,60),ECC_WorldStatic,Q);
    return W.Test.TestTrue(Label,Found&&!Hit.bStartPenetrating&&FMath::Abs(Hit.ImpactPoint.Z-Expected)<2&&Hit.ImpactNormal.Z>.9);
}
bool Reload(FWorld& W)
{
    W.Fieldcraft()->OnEvent.Remove(W.EventsHandle);
    W.World->DestroyTestWorld(true);W.World->ForwardErrorMessages(&W.Test);W.World.Reset();
    W.World=MakeUnique<FSoraAutomationWorld>();
    if(!W.World->Start(W.Slot)||!W.Tick(1)||!W.World->EnableKeyInput()) return false;
    for(int32 N=0;N<3;++N) if(!W.Press(EKeys::Enter)) return false;
    return W.Tick(30)&&W.Campaign()->ActiveBeat()==2;
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraClimbCornerTest,"SoraArena.Campaign.ClimbCorner",
 EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraClimbCornerTest::RunTest(const FString&)
{
    SoraClimbTest::FWorld W(*this,TEXT("ClimbCorner"),5,2);if(!SoraClimbTest::Start(W)) return false;
    auto* C=W.Fieldcraft();const auto& Contract=W.BeatData().Space.Climb;
    if(!TestNotNull(TEXT("The real sentry remains alive"),SoraClimbTest::Sentry(W))||!SoraClimbAutomation::Begin(*W.World)) return false;
    const int32 StartClock=C->ClimbClock();
    if(!SoraClimbAutomation::ToHold(*W.World,5)) return false;
    TestTrue(TEXT("Lower rest is physically at 5.5m and frees the arms"),C->IsClimbResting()&&!C->ArmsStowed()&&
        FMath::Abs(W.Hero()->GetActorLocation().Z-638)<2);
    SoraClimbTest::Support(W,Contract.Corner.Points[5],550,TEXT("Lower rest is real supporting collision"));
    const float Grip=C->Readout(*W.Hero()).Grip;
    if(!W.Tick(60)) return false;
    TestTrue(TEXT("Actual rest regenerates grip"),C->Readout(*W.Hero()).Grip>Grip);
    if(!TestTrue(TEXT("Mapped backward input clears the lower shelf before descending"),SoraClimbAutomation::DownToHold(*W.World,4))) return false;
    TestTrue(TEXT("Descending reaches the real prior hold outside the shelf"),
        (W.Hero()->GetActorLocation()-FVector(Contract.Origin,88)).Equals(Contract.Corner.Points[4],2));
    if(!TestTrue(TEXT("The lower approach reverses down before moving back under the shelf"),SoraClimbAutomation::DownToHold(*W.World,3))) return false;
    if(!SoraClimbAutomation::ToHold(*W.World,5)) return false;
    if(!SoraClimbAutomation::ToHold(*W.World,9)) return false;
    TestTrue(TEXT("Upper rest is at 11m"),C->IsClimbResting()&&FMath::Abs(W.Hero()->GetActorLocation().Z-1188)<2);
    SoraClimbTest::Support(W,Contract.Corner.Points[9],1100,TEXT("Upper rest is real supporting collision"));
    if(!W.Tick(240)) return false; // Real rest pays for the added retreat/re-ascent moves.
    if(!TestTrue(TEXT("The upper shelf and its approach also support downward retreat"),SoraClimbAutomation::DownToHold(*W.World,7))||
        !SoraClimbAutomation::ToHold(*W.World,14)) return false;
    const FVector LastHold=W.Hero()->GetActorLocation();
    if(!W.Hold(EKeys::W,30)) return false;
    TestTrue(TEXT("The final mount has physically begun"),W.Hero()->GetActorLocation().X>LastHold.X+20&&C->IsClimbing());
    if(!W.Hold(EKeys::S,30)) return false;
    TestTrue(TEXT("Reversing returns to the final hold without crediting the top"),
        C->IsClimbing()&&C->ClimbHoldIndex()==14&&W.Hero()->GetActorLocation().Equals(LastHold,2)&&!C->ClimbExitReady());
    if(!SoraClimbAutomation::Top(*W.World)) return false;
    TestTrue(TEXT("Fourteen holds and mounting consume their real provisional time"),C->ClimbClock()-StartClock>=14*1800);
    TestFalse(TEXT("Reaching the top alone cannot complete the crawl exit"),C->ClimbExitReady());
    if(!SoraClimbAutomation::Approach(*W.World)||!W.Hold(EKeys::W,180)) return false;
    const FVector Local=W.Hero()->GetActorLocation()-FVector(Contract.Origin,0);
    TestTrue(TEXT("A standing capsule is blocked by the actual 60cm aperture"),Local.X<1100&&W.Campaign()->ActiveBeat()==2&&!C->ClimbExitReady());
    if(!W.Press(EKeys::Escape)||!W.Hero()->RemapCombatAction(TEXT("Crouch"),EKeys::G)||!W.Press(EKeys::Escape)) return false;
    if(!W.Press(EKeys::C)) return false;
    TestFalse(TEXT("The old crouch key cannot enter the local crawl"),C->IsClimbCrawling());
    if(!TestTrue(TEXT("Rebound crouch and forward physically cross the gap and restore dimensions"),SoraClimbAutomation::Exit(*W.World))) return false;
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraClimbExtrusionTest,"SoraArena.Campaign.ClimbExtrusion",
 EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraClimbExtrusionTest::RunTest(const FString&)
{
    SoraClimbTest::FWorld W(*this,TEXT("ClimbExtrusion"),5,2);if(!SoraClimbTest::Start(W)) return false;
    if(!SoraClimbAutomation::Begin(*W.World,1,true)) return false;
    auto* C=W.Fieldcraft();const int32 Start=C->ClimbClock();
    if(!SoraClimbAutomation::Top(*W.World)) return false;
    const int32 Took=C->ClimbClock()-Start;
    TestEqual(TEXT("The selected alternate route reaches eight holds"),C->ClimbHoldIndex(),8);
    TestTrue(TEXT("Eight actual hold moves finish faster than fourteen at the same cadence"),Took>=8*1800&&Took<14*1800);
    TestTrue(TEXT("The traversal keeps its live sentry"),SoraClimbTest::Sentry(W)&&SoraClimbTest::Sentry(W)->IsAlive());
    // Approach while already in ordinary crouch. CMC must resize that
    // existing crouch, rather than waiting for a nonexistent stance change.
    if(!W.Press(SoraClimbAutomation::Key(*W.Hero(),TEXT("Crouch"),true))||!W.Tick(3)) return false;
    TestEqual(TEXT("Ordinary gamepad crouch is still 44cm half-height before the aperture"),W.Hero()->GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight(),44.f);
    return TestTrue(TEXT("An already-crouched gamepad approach resizes and crosses the real gap"),SoraClimbAutomation::Approach(*W.World)&&SoraClimbAutomation::Exit(*W.World,true))&&!HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraClimbSentryTest,"SoraArena.Campaign.ClimbSentry",
 EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraClimbSentryTest::RunTest(const FString&)
{
    SoraClimbTest::FWorld W(*this,TEXT("ClimbSentry"),5,2);if(!SoraClimbTest::Start(W)) return false;
    auto* C=W.Fieldcraft();auto* S=SoraClimbTest::Sentry(W);if(!TestNotNull(TEXT("Sentry staged"),S)) return false;
    const FVector O(W.BeatData().Space.Climb.Origin,0);
    float LowY=0,HighY=-5000;int32 FirstWatch=-1,WatchFrames=0;FVector FirstAim;
    while(C->ClimbClock()<24500)
    {
        if(!W.Tick(1)) return false;
        const FVector Local=S->GetActorLocation()-O;LowY=FMath::Min(LowY,float(Local.Y));HighY=FMath::Max(HighY,float(Local.Y));
        if(C->ClimbSentryWatching())
        {
            if(FirstWatch<0) { FirstWatch=C->ClimbClock();FirstAim=C->ClimbSentryAim(); }
            ++WatchFrames;
            TestTrue(TEXT("Look-down occurs only at the physically reached bay"),FVector::Dist2D(Local,FVector(360,-300,0))<55);
        }
    }
    UE_LOG(LogTemp,Display,TEXT("CLIMB_DIAGNOSTIC sentry_timing first_watch=%d watch_frames=%d low_y=%.4f high_y=%.4f first_aim=%s"),FirstWatch,WatchFrames,LowY,HighY,*FirstAim.ToString());
    SoraClimbAutomation::Note(*W.World,TEXT("Sentry.watch_end"),true);
    TestTrue(TEXT("First look-down begins at 20s within one editor frame"),FirstWatch>=20000&&FirstWatch<=20034);
    TestTrue(TEXT("The look-down lasts four seconds"),WatchFrames>=238&&WatchFrames<=242);
    TestTrue(TEXT("The actual patrol covers the full 30m parapet segment"),LowY<-3750&&HighY>-850);
    TestTrue(TEXT("The real aim sweeps across the upper routes"),FVector::Dist(FirstAim,C->ClimbSentryAim())>500);
    auto* Brain=Cast<ASoraEnemyController>(S->GetController());
    TestTrue(TEXT("The guarded base remains outside the downward view"),Brain&&!Brain->CanSee(*W.Hero()));
    // Now reach the upper corner with real input, wait in its exposed sight,
    // and observe actual visibility and rifle damage, not synthetic events.
    if(!SoraClimbAutomation::Begin(*W.World)||!SoraClimbAutomation::ToHold(*W.World,9)) return false;
    const float Before=W.Hero()->Health;bool Seen=false;const int32 End=C->ClimbClock()+25000;
    while(C->ClimbClock()<End)
    { if(!W.Tick(1)) return false;Seen|=Brain->CanSee(*W.Hero()); }
    TestTrue(TEXT("Actual downward cone and 3D traces see the exposed upper hold"),Seen);
    TestTrue(TEXT("The real sentry rifle resolves damage against the climber"),S->RangedShotsFired()>0&&W.Hero()->Health<Before);
    TestTrue(TEXT("The authored freeze call comes from the watch transition"),W.Raised(TEXT("ai_event:sentry_lookdown")));
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraClimbResetTest,"SoraArena.Campaign.ClimbPauseRetryReload",
 EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraClimbResetTest::RunTest(const FString&)
{
    SoraClimbTest::FWorld W(*this,TEXT("ClimbPauseRetryReload"),5,2);if(!SoraClimbTest::Start(W)) return false;
    if(!SoraClimbAutomation::Begin(*W.World)||!W.Hold(EKeys::W,60)) return false;
    auto* C=W.Fieldcraft();const FVector At=W.Hero()->GetActorLocation();const int32 Clock=C->ClimbClock();const float Grip=C->Readout(*W.Hero()).Grip;
    W.Mode()->SetMenuOpen(true);if(!W.Tick(180)) return false;
    TestEqual(TEXT("Menu freezes the climb/watch clock"),C->ClimbClock(),Clock);
    TestEqual(TEXT("Menu grants no grip or hold credit"),C->Readout(*W.Hero()).Grip,Grip);
    TestTrue(TEXT("Menu preserves the physical held point"),W.Hero()->GetActorLocation().Equals(At,.01f));
    W.Mode()->SetMenuOpen(false);
    if(!SoraClimbAutomation::Top(*W.World)||!SoraClimbAutomation::Approach(*W.World)||!W.Press(SoraClimbAutomation::Key(*W.Hero(),TEXT("Crouch")))) return false;
    if(!SoraLiftAutomation::Walk(*W.World,FVector(W.BeatData().Space.Climb.Origin,0)+FVector(1250,0,1650))) return false;
    if(!W.Press(SoraClimbAutomation::Key(*W.Hero(),TEXT("Crouch")))||!W.Tick(30)) return false;
    TestTrue(TEXT("Toggling crouch off inside stone cannot expand the capsule"),C->IsClimbCrawling()&&W.Hero()->IsCrouched()&&W.Hero()->GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight()==28);
    const FVector CrawlAt=W.Hero()->GetActorLocation();const int32 CrawlClock=C->ClimbClock();
    W.Mode()->SetMenuOpen(true);if(!W.Tick(120)) return false;
    TestTrue(TEXT("Active crawl pause preserves dimensions, pose and clock"),W.Hero()->GetActorLocation().Equals(CrawlAt,.01f)&&C->ClimbClock()==CrawlClock&&W.Hero()->GetCapsuleComponent()->GetUnscaledCapsuleRadius()==28);
    W.Mode()->SetMenuOpen(false);
    UGameplayStatics::ApplyDamage(W.Hero(),W.Hero()->Health+1000,nullptr,nullptr,UDamageType::StaticClass());
    if(!W.Tick(2)||!TestTrue(TEXT("Death reaches the ordinary result"),W.Mode()->bDefeated)||!W.Press(EKeys::Enter)||!W.Tick(30)) return false;
    TestTrue(TEXT("Retry restores the ordinary capsule and untouched checkpoint route"),!C->IsClimbCrawling()&&C->ClimbRouteIndex()==INDEX_NONE&&!C->ClimbExitReady()&&
        W.Hero()->GetCapsuleComponent()->GetUnscaledCapsuleRadius()==34&&W.Hero()->GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight()==88&&W.Campaign()->ActiveBeat()==2);
    if(!SoraClimbTest::Reload(W)) return false;
    C=W.Fieldcraft();TestTrue(TEXT("A fresh world cannot retain partial route or a small capsule"),!C->IsClimbCrawling()&&C->ClimbRouteIndex()==INDEX_NONE&&!C->ClimbExitReady()&&
        C->ClimbClock()<1000&&W.Hero()->GetCapsuleComponent()->GetUnscaledCapsuleRadius()==34&&W.Hero()->GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight()==88);
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraClimbLoaderTest,"SoraArena.Campaign.ClimbLoader",
 EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraClimbLoaderTest::RunTest(const FString&)
{
    if(!FSoraCatalog::Get().Load()) return false;
    FString Text;if(!FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("Data/campaign/chapter_06.json")))) return false;
    TSharedPtr<FJsonObject> Root;auto Reader=TJsonReaderFactory<>::Create(Text);
    if(!FJsonSerializer::Deserialize(Reader,Root)) return false;
    const auto Row=Root->GetObjectField(TEXT("space"))->GetArrayField(TEXT("beats"))[2]->AsObject();
    const auto& Chapter=FSoraCatalog::Get().Chapter(5);FSoraBeat B=Chapter.Beats[2];
    TestTrue(TEXT("Actual typed reader accepts the generated routes"),SoraCatalogClimb::Read(*Row,B,Chapter.Space));
    auto Routes=Row->GetObjectField(TEXT("climb_routes"));
    Routes->GetObjectField(TEXT("crawl"))->SetNumberField(TEXT("height_cm"),90);
    TestFalse(TEXT("The typed reader rejects silently enlarging the authored crawl"),SoraCatalogClimb::Read(*Row,B,Chapter.Space));
    Routes->GetObjectField(TEXT("crawl"))->SetNumberField(TEXT("height_cm"),60);
    Routes->GetObjectField(TEXT("lookdown"))->SetNumberField(TEXT("hold_ms"),5000);
    TestFalse(TEXT("The typed reader rejects changed watch timing"),SoraCatalogClimb::Read(*Row,B,Chapter.Space));
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraClimbHandsTest,"SoraArena.Campaign.ClimbHands",
 EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraClimbHandsTest::RunTest(const FString&)
{
    SoraClimbTest::FWorld W(*this,TEXT("ClimbHands"),5,2);if(!SoraClimbTest::Start(W)) return false;
    // Isolate equipment cancellation from incoming stagger; ClimbSentry and
    // both route fixtures retain the live sentry separately.
    SoraLiftAutomation::HoldThreats(*W.World);
    auto* Kit=W.Hero()->GetEquipment();auto* C=W.Fieldcraft();
    const FKey Fire=SoraClimbAutomation::Key(*W.Hero(),TEXT("Fire"));
    if(!W.Press(SoraClimbAutomation::Key(*W.Hero(),TEXT("WeaponThree")))||!W.Tick(30)||
        !TestEqual(TEXT("Ordinary weapon selection equips the unlocked bow"),W.Hero()->WeaponId,18)) return false;
    const int32 Ammo=Kit->Ammo;
    if(!W.World->InjectKey(Fire,IE_Pressed)||!W.Tick(50)||!TestTrue(TEXT("A ground draw is actually held"),Kit->IsBowDrawing())||
        !SoraClimbAutomation::Begin(*W.World)||!W.World->InjectKey(Fire,IE_Released)) return false;
    TestTrue(TEXT("Taking the first hold cancels the draw without firing"),!Kit->IsBowDrawing()&&!Kit->IsTriggerHeld()&&Kit->Ammo==Ammo);
    if(!SoraClimbAutomation::ToHold(*W.World,5)||!W.Hold(Fire,50)) return false;
    TestEqual(TEXT("A legitimate stationary-rest shot still consumes one arrow"),Kit->Ammo,Ammo-1);
    if(!W.Tick(90)||!W.World->InjectKey(Fire,IE_Pressed)||!W.Tick(50)||
        !TestTrue(TEXT("A second rest draw is actually held"),Kit->IsBowDrawing())||!W.Hold(EKeys::W,1)||
        !W.World->InjectKey(Fire,IE_Released)||!W.Tick(2)) return false;
    TestTrue(TEXT("Leaving the rest stows hands and refuses the held release"),C->ArmsStowed()&&!Kit->IsBowDrawing()&&!Kit->IsTriggerHeld()&&Kit->Ammo==Ammo-1);
    if(!SoraClimbAutomation::Top(*W.World)||!SoraClimbAutomation::Approach(*W.World)||
        !W.World->InjectKey(Fire,IE_Pressed)||!W.Tick(50)||!TestTrue(TEXT("The clear approach permits a real draw"),Kit->IsBowDrawing())||
        !W.Press(SoraClimbAutomation::Key(*W.Hero(),TEXT("Crouch")))||!W.World->InjectKey(Fire,IE_Released)||!W.Tick(3)) return false;
    TestTrue(TEXT("Entering the local crawl cancels the drawn bow without an arrow"),C->IsClimbCrawling()&&!Kit->IsBowDrawing()&&!Kit->IsTriggerHeld()&&Kit->Ammo==Ammo-1);
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraClimbFallTest,"SoraArena.Campaign.ClimbFalls",
 EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraClimbFallTest::RunTest(const FString&)
{
    SoraClimbTest::FWorld W(*this,TEXT("ClimbFalls"),5,2);if(!SoraClimbTest::Start(W)) return false;
    SoraLiftAutomation::HoldThreats(*W.World);
    if(!SoraClimbAutomation::Begin(*W.World)||!SoraClimbAutomation::ToHold(*W.World,9)) return false;
    TestTrue(TEXT("The lethal drop begins at the actual 11m rest"),FMath::Abs(W.Hero()->GetActorLocation().Z-1188)<2);
    if(!W.Press(SoraClimbAutomation::Key(*W.Hero(),TEXT("Jump")))) return false;
    // Air-control away from the wall clears the lower shelf. Landing on that
    // shelf would correctly count only the actual 5.5m drop, not the height
    // above the terrace; this check requires the full physical fall.
    if(!W.World->InjectKey(EKeys::S,IE_Pressed)) return false;
    for(int32 F=0;F<300&&!W.Mode()->bDefeated;++F) if(!W.Tick(1)) return false;
    if(!W.World->InjectKey(EKeys::S,IE_Released)) return false;
    TestTrue(TEXT("A real fall exceeding 8m is lethal even with fixture health"),W.Mode()->bDefeated&&!W.Hero()->IsAlive()&&W.Hero()->GetActorLocation().Z<100);
    if(!W.Press(EKeys::Enter)||!W.Tick(30)) return false;
    TestTrue(TEXT("The ordinary retry clears fall and route state"),!W.Mode()->bDefeated&&W.Hero()->IsAlive()&&
        W.Fieldcraft()->ClimbRouteIndex()==INDEX_NONE&&!W.Fieldcraft()->IsClimbing()&&!W.Fieldcraft()->ClimbExitReady());
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraClimbGuideTest,"SoraArena.Campaign.ClimbGuide",
 EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraClimbGuideTest::RunTest(const FString&)
{
    SoraClimbTest::FWorld W(*this,TEXT("ClimbGuide"),5,2);if(!SoraClimbTest::Start(W)) return false;
    auto* Guide=SoraClimbTest::Guide(W);auto* C=W.Fieldcraft();
    if(!TestNotNull(TEXT("The authored guide is staged"),Guide)) return false;
    const auto& Route=W.BeatData().Space.Climb.Corner;const FVector O(W.BeatData().Space.Climb.Origin,0);
    TestTrue(TEXT("Kohagi starts climbing before the waiting hero"),Guide->GetActorLocation().Z>W.Hero()->GetActorLocation().Z+20&&!C->IsClimbing());
    TestFalse(TEXT("The scripted guide remains nondetectable"),Guide->IsExposed(0));
    uint32 Reached=0;bool Paused=false;FVector Previous=Guide->GetActorLocation();
    for(int32 F=0;F<3600&&!C->ClimbGuideWaiting();++F)
    {
        if(!W.Tick(1)) return false;
        const FVector At=Guide->GetActorLocation(),Feet=At-O-FVector(0,0,Guide->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
        TestTrue(TEXT("Every guide movement remains bounded, with no relocation"),FVector::Dist(At,Previous)<=SoraClimbRules::GuideSpeed/60.f+3.f);
        Previous=At;
        for(int32 H=1;H<Route.Points.Num();++H) if(Feet.Equals(Route.Points[H],5)) Reached|=1u<<H;
        if(F%600==599)
        {
            UE_LOG(LogTemp,Display,TEXT("CLIMB_DIAGNOSTIC guide_progress reached_mask=%08x frame=%d"),Reached,F);
            SoraClimbAutomation::Note(*W.World,TEXT("Guide.progress"),true,FVector::ZeroVector,INDEX_NONE,F);
        }
        if(!Paused&&Feet.Z>300)
        {
            const int32 Clock=C->ClimbClock();W.Mode()->SetMenuOpen(true);
            if(!W.Tick(120)) return false;
            TestTrue(TEXT("Menu freezes the active guide and shared watch clock"),Guide->GetActorLocation().Equals(At,.01f)&&C->ClimbClock()==Clock);
            W.Mode()->SetMenuOpen(false);Paused=true;
        }
    }
    UE_LOG(LogTemp,Display,TEXT("CLIMB_DIAGNOSTIC guide_end reached_mask=%08x"),Reached);
    SoraClimbAutomation::Note(*W.World,TEXT("Guide.end"),Reached==0x7ffeu&&C->ClimbGuideWaiting());
    if(!TestTrue(TEXT("Kohagi physically reaches all fourteen corner holds and the roof"),Reached==0x7ffeu&&C->ClimbGuideWaiting())||!W.Tick(30)) return false;
    FHitResult Floor;FCollisionQueryParams Q(SCENE_QUERY_STAT(ClimbGuideRoofFixture),false,Guide);Q.AddIgnoredActor(W.Hero());
    const FVector Feet=Guide->GetActorLocation()-FVector(0,0,Guide->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
    const bool Supported=W.World->GetTestWorld()->LineTraceSingleByChannel(Floor,Feet+FVector(0,0,20),Feet-FVector(0,0,60),ECC_WorldStatic,Q);
    TestTrue(TEXT("The roof wait stands on real 24m support"),Supported&&!Floor.bStartPenetrating&&Floor.ImpactNormal.Z>.9&&
        FMath::Abs(Floor.ImpactPoint.Z-SoraClimbRules::GuideRoofHeight)<2&&Guide->GetCharacterMovement()->IsMovingOnGround());
    const FVector Waiting=Guide->GetActorLocation();if(!W.Tick(600)) return false;
    TestTrue(TEXT("The roof guide waits instead of falling back to generic following"),C->ClimbGuideWaiting()&&Guide->GetActorLocation().Equals(Waiting,2));
    TestFalse(TEXT("The guide cannot credit the player's crawl exit"),C->ClimbExitReady());
    UGameplayStatics::ApplyDamage(W.Hero(),W.Hero()->Health+1000,nullptr,nullptr,UDamageType::StaticClass());
    if(!W.Tick(2)||!W.Press(EKeys::Enter)||!W.Tick(30)) return false;
    Guide=SoraClimbTest::Guide(W);C=W.Fieldcraft();
    TestTrue(TEXT("Death retry restarts the guide at the lower route"),Guide&&!C->ClimbGuideWaiting()&&Guide->GetActorLocation().Z<500);
    if(!SoraClimbTest::Reload(W)) return false;
    Guide=SoraClimbTest::Guide(W);C=W.Fieldcraft();
    TestTrue(TEXT("A fresh checkpoint world cannot retain the previous roof wait"),Guide&&!C->ClimbGuideWaiting()&&Guide->GetActorLocation().Z<500);
    const TWeakObjectPtr<ASoraCompanion> OldGuide=Guide;W.Harden();
    if(!TestTrue(TEXT("The player's ordinary route still completes with the guide present"),SoraClimbAutomation::Traverse(*W.World))) return false;
    TestTrue(TEXT("Beat transition destroys the old scoped guide and clears the wait"),
        (!OldGuide.IsValid()||OldGuide->IsActorBeingDestroyed())&&!W.Fieldcraft()->ClimbGuideWaiting());
    return !HasAnyErrors();
}
#endif
