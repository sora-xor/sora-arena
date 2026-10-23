#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraLiftAutomation.h"
#include "SoraGameEvents.h"
#include "SoraEnemyController.h"
#include "SoraCatalogFlood.h"
#include "Components/CapsuleComponent.h"
#include "Dom/JsonObject.h"
#include "GameFramework/DamageType.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/ScopeExit.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

namespace
{
using FWorld=SoraFieldcraftAutomation::FBeatWorld;
bool Walk(FWorld& W,const FVector& Local)
{
    const FVector Goal=FVector(W.BeatData().Space.Flood.Origin,0)+Local;
    const FVector Start=W.Hero()->GetActorLocation();
    const int32 Steps=FMath::Max(1,FMath::CeilToInt(FVector::Dist2D(Start,Goal)/1000));
    for(int32 I=1;I<=Steps;++I)
        if(!SoraLiftAutomation::Walk(*W.World,FMath::Lerp(Start,Goal,float(I)/Steps))) return false;
    return true;
}
bool Cross(FWorld& W,const FKey& Dive,bool Late)
{
    auto* Craft=W.Fieldcraft();
    W.Harden();
    auto* Bus=USoraGameEvents::Get(W.Hero());
    float Drowning=0;
    const auto Handle=Bus->OnDamaged.AddLambda([&](const FSoraDamagedEvent& E)
        { if(E.Victim==W.Hero()&&!E.Causer) Drowning+=E.Amount; });
    ON_SCOPE_EXIT { Bus->OnDamaged.Remove(Handle); };
    if(Late&&!W.Tick(9100)) return false;
    if(!W.Test.TestEqual(TEXT("Early wading becomes late surface swimming"),Craft->Readout(*W.Hero()).bSwimming,Late)) return false;
    if(!Walk(W,FVector(7400,0,0))) return false;
    W.Look(FRotator::ZeroRotator);
    if(!W.Hold(EKeys::W,90)) return false;
    W.Test.TestTrue(TEXT("A surfaced capsule cannot pass the real submerged roof"),
        W.Hero()->GetActorLocation().X-W.BeatData().Space.Flood.Origin.X<7500);
    if(!W.Press(Dive)||!Walk(W,FVector(8250,0,0))) return false;
    W.Test.TestEqual(TEXT("Normal input crossed the first submerged leg"),Craft->FloodPassageStage(),2);
    const float Before=Craft->Readout(*W.Hero()).Breath;
    if(!W.Tick(6)) return false;
    W.Test.TestTrue(TEXT("Being inside the shaft underwater does not restore breath"),Craft->Readout(*W.Hero()).Breath<Before);
    if(!W.Press(Dive)||!W.Tick(240)) return false;
    W.Test.TestFalse(TEXT("The actual head rises into air"),Craft->IsDiving());
    W.Test.TestTrue(TEXT("Three seconds of real air restores breath"),Craft->Readout(*W.Hero()).Breath>.99f);
    const int32 Clock=Craft->FloodElapsedMs();
    const FVector Position=W.Hero()->GetActorLocation();
    if(!W.Press(EKeys::Escape)||!W.Tick(180)) return false;
    W.Test.TestTrue(TEXT("Pause freezes the water and body"),Craft->FloodElapsedMs()<=Clock+34&&
        FVector::Dist(Position,W.Hero()->GetActorLocation())<2);
    if(!W.Press(EKeys::Escape)||!W.Press(Dive)||!Walk(W,FVector(9050,0,0))||!W.Press(Dive)||!W.Tick(70)) return false;
    W.Test.TestEqual(TEXT("Normal input crossed the second submerged leg"),Craft->FloodPassageStage(),4);
    W.Test.TestFalse(TEXT("Emerging from the culvert alone does not authorize exit"),Craft->FloodExitReady());
    W.Test.TestTrue(TEXT("Toranosuke physically carries Iota"),Craft->FloodCarriesIota());
    W.Test.TestEqual(TEXT("A careful route incurs no drowning damage"),Drowning,0.f);
    if(!Walk(W,FVector(9500,0,0))||!Walk(W,FVector(9500,-600,0))) return false;
    W.Test.TestTrue(TEXT("Actual movement crosses the half-open gate"),Craft->FloodExitReady());
    if(!Walk(W,FVector(9500,-3900,0))) return false;
    W.Look(FRotator(0,-90,0));
    for(int32 I=0;I<500&&W.Campaign()->ActiveBeat()==13;++I)
        if(!W.World->InjectKey(EKeys::W,IE_Pressed)||!W.Tick(1)) return false;
    if(!W.World->InjectKey(EKeys::W,IE_Released)||!W.Tick(1)) return false;
    return W.Test.TestEqual(TEXT("Swimming and walking onto the outer bank completes b14"),W.Campaign()->ActiveBeat(),14);
}
bool Reload(FWorld& W)
{
    W.Fieldcraft()->OnEvent.Remove(W.EventsHandle);
    if(!W.World->DestroyTestWorld(true)) return false;
    W.World->ForwardErrorMessages(&W.Test);W.World.Reset();W.Events.Reset();
    W.World=MakeUnique<FSoraAutomationWorld>();
    return W.World->Start(W.Slot)&&W.Tick(1)&&W.World->EnableKeyInput()&&
        W.Press(EKeys::Enter)&&W.Press(EKeys::Enter)&&W.Press(EKeys::Enter)&&W.Tick(30);
}
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraFloodTraversalTest,"SoraArena.Campaign.FloodTraversal",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraFloodTraversalTest::RunTest(const FString&)
{
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    FWorld W(*this,TEXT("FloodTraversal"),5,13);
    if(!W.Start()||!W.Tick(30)||!W.Press(EKeys::Escape)||!W.Hero()->RemapCombatAction(TEXT("Crouch"),EKeys::G)||!W.Press(EKeys::Escape)) return false;
    if(!W.Press(EKeys::C)) return false;
    TestFalse(TEXT("The old crouch key cannot substitute for the rebound dive"),W.Hero()->GetCharacterMovement()->bWantsToCrouch);
    return Cross(W,EKeys::G,false)&&!HasAnyErrors();
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraFloodLateWaterTest,"SoraArena.Campaign.FloodLateWater",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraFloodLateWaterTest::RunTest(const FString&)
{
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    FWorld W(*this,TEXT("FloodLateWater"),5,13);
    return W.Start()&&W.Tick(30)&&Cross(W,EKeys::Gamepad_RightThumbstick,true)&&!HasAnyErrors();
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraFloodRetryTest,"SoraArena.Campaign.FloodRetryReload",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraFloodRetryTest::RunTest(const FString&)
{
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    FWorld W(*this,TEXT("FloodRetryReload"),5,13);
    if(!W.Start()||!W.Tick(30)) return false;
    W.Harden();
    if(!Walk(W,FVector(7400,0,0))||!W.Press(EKeys::C)||!Walk(W,FVector(7800,0,0))) return false;
    const float Before=W.Fieldcraft()->Readout(*W.Hero()).Breath;
    if(!W.Press(EKeys::C)||!W.Tick(12)) return false;
    TestTrue(TEXT("An uncrouch wish under stone cannot create air"),W.Fieldcraft()->IsDiving()&&W.Fieldcraft()->Readout(*W.Hero()).Breath<Before);
    UGameplayStatics::ApplyDamage(W.Hero(),W.Hero()->Health+1000,nullptr,nullptr,UDamageType::StaticClass());
    if(!W.Tick(2)||!TestTrue(TEXT("Death opens retry"),W.Mode()->bDefeated)||!W.Press(EKeys::Enter)||!W.Tick(30)) return false;
    TestTrue(TEXT("Death retry resets water and traversal"),W.Fieldcraft()->FloodElapsedMs()<1000&&W.Fieldcraft()->FloodPassageStage()==0);
    TestFalse(TEXT("Death retry releases Iota and swimming mode"),W.Fieldcraft()->FloodCarriesIota()||W.Fieldcraft()->Readout(*W.Hero()).bSwimming);
    TestTrue(TEXT("Death retry restores normal gravity"),W.Hero()->GetCharacterMovement()->GravityScale>0);
    if(!W.Tick(300)||!Reload(W)) return false;
    TestTrue(TEXT("Fresh save load starts the authored checkpoint, not partial water progress"),
        W.Campaign()->ActiveBeat()==13&&W.Fieldcraft()->FloodElapsedMs()<1000&&W.Fieldcraft()->FloodPassageStage()==0);
    // Negative test only: a teleport directly to the bank cannot manufacture
    // either submerged traversal or a physical gate crossing.
    const auto& Exit=W.BeatData().Space.Exit;
    W.Hero()->SetActorLocation(FVector(Exit.Center,290),false,nullptr,ETeleportType::TeleportPhysics);
    if(!W.Tick(30)) return false;
    TestEqual(TEXT("An exit teleport is rejected"),W.Campaign()->ActiveBeat(),13);
    return !HasAnyErrors();
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraFloodSensesTest,"SoraArena.Campaign.FloodSenses",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraFloodSensesTest::RunTest(const FString&)
{
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    FWorld W(*this,TEXT("FloodSenses"),5,13);
    if(!W.Start()||!W.Tick(30)) return false;
    W.Harden();
    if(!Walk(W,FVector(1700,0,0))) return false;
    bool HeardWithoutSight=false;
    for(TActorIterator<ASoraEnemyController> It(W.World->GetTestWorld());It;++It)
        HeardWithoutSight|=It->IsGuard()&&It->AwarenessPermille()>0&&!It->CanSee(*W.Hero());
    TestTrue(TEXT("Actual wading alerts a guard through sound while the stone roof occludes sight"),HeardWithoutSight);
    if(!Walk(W,FVector(2000,0,0))||!W.Tick(100)) return false;
    TestTrue(TEXT("Standing in a grate's lamp raises the production alert event"),W.Raised(TEXT("ai_event:searchlight_alert")));
    if(!W.Tick(9100)||!W.Press(EKeys::Gamepad_RightThumbstick)||!W.Tick(60)) return false;
    TestTrue(TEXT("The real camera dives below the risen water"),W.Fieldcraft()->IsDiving());
    TestFalse(TEXT("A physically submerged head is not in the lamp detection"),W.Fieldcraft()->Readout(*W.Hero()).bInLight);
    const FVector Feet=W.Hero()->GetActorLocation()-FVector(0,0,W.Hero()->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
    TestEqual(TEXT("Underwater strokes feed zero noise to the production senses"),W.Stealth()->SurfaceAt(Feet).StepPermille,0);
    return !HasAnyErrors();
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraFloodLoaderTest,"SoraArena.Campaign.FloodLoader",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraFloodLoaderTest::RunTest(const FString&)
{
    if(!FSoraCatalog::Get().Load()) return false;
    FString Text;
    if(!FFileHelper::LoadFileToString(Text,*FPaths::Combine(FPaths::ProjectContentDir(),TEXT("Data/campaign/chapter_06.json")))) return false;
    const auto Check=[&](const TCHAR* Key,bool Boolean)
    {
        TSharedPtr<FJsonObject> Data;
        if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Data)) return false;
        auto O=Data->GetObjectField(TEXT("space"))->GetArrayField(TEXT("beats"))[13]->AsObject();
        if(Key) { if(Boolean) O->GetObjectField(TEXT("flood"))->SetBoolField(Key,true); else O->GetObjectField(TEXT("flood"))->RemoveField(Key); }
        FSoraChapter Copy=FSoraCatalog::Get().Chapter(5); Copy.Beats[13].Space.Flood={};
        return TestEqual(TEXT("Production reader rejects malformed flood data"),SoraCatalogFlood::Read(*O,Copy.Beats[13],Copy.Space),Key==nullptr);
    };
    Check(nullptr,false);
    for(const TCHAR* Key:{TEXT("origin"),TEXT("length_cm"),TEXT("air_shaft_cm"),TEXT("deep_roof_cm"),TEXT("rise_ms")})
        { Check(Key,true); Check(Key,false); }
    return !HasAnyErrors();
}
#endif
