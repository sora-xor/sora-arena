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

namespace SoraFloodTest
{
using FWorld=SoraFieldcraftAutomation::FBeatWorld;
void Sample(FWorld& W,const TCHAR* Label)
{
    const FVector Origin(W.BeatData().Space.Flood.Origin,0);
    const auto* Hero=W.Hero();const auto* Move=Hero->GetCharacterMovement();
    const auto* Capsule=Hero->GetCapsuleComponent();const auto* Craft=W.Fieldcraft();
    const FVector At=Hero->GetActorLocation(),Eye=Hero->GetCamera()->GetComponentLocation();
    FCollisionQueryParams Query(SCENE_QUERY_STAT(FloodFixtureSample),false,Hero);
    for(const auto& Ally:Craft->AlliesInPlay()) if(IsValid(Ally)) Query.AddIgnoredActor(Ally);
    FHitResult Floor,Roof;
    const bool HasFloor=W.World->GetTestWorld()->LineTraceSingleByChannel(Floor,At,At-FVector(0,0,1000),ECC_WorldStatic,Query);
    const bool HasRoof=W.World->GetTestWorld()->LineTraceSingleByChannel(Roof,At,At+FVector(0,0,1000),ECC_WorldStatic,Query);
    W.Test.AddInfo(FString::Printf(TEXT("Flood sample %s local=%s eye=%s velocity=%s mode=%d crouched=%d wants_crouch=%d half=%.2f radius=%.2f collision=%d static_response=%d clock=%d water=%d swim=%d dive=%d breath=%.4f stage=%d gate=%d floor=%d/%s/%s roof=%d/%s/%s"),
        Label,*(At-Origin).ToString(),*(Eye-Origin).ToString(),*Move->Velocity.ToString(),int32(Move->MovementMode),
        Hero->IsCrouched(),Move->bWantsToCrouch,Capsule->GetScaledCapsuleHalfHeight(),Capsule->GetScaledCapsuleRadius(),
        int32(Capsule->GetCollisionEnabled()),int32(Capsule->GetCollisionResponseToChannel(ECC_WorldStatic)),
        Craft->FloodElapsedMs(),SoraFloodRules::Surface(Craft->FloodElapsedMs()),Craft->IsSwimming(),Craft->IsDiving(),
        Craft->Readout(*Hero).Breath,Craft->FloodPassageStage(),Craft->FloodExitReady(),
        HasFloor,*GetNameSafe(Floor.GetComponent()),*(Floor.ImpactPoint-Origin).ToString(),
        HasRoof,*GetNameSafe(Roof.GetComponent()),*(Roof.ImpactPoint-Origin).ToString()));
    for(const auto& Ally:Craft->AlliesInPlay()) if(IsValid(Ally))
    {
        const FVector Position=Ally->GetActorLocation();const auto* Movement=Ally->GetCharacterMovement();
        const auto* Body=Ally->GetCapsuleComponent();FHitResult Support,Ceiling;
        const bool HasSupport=W.World->GetTestWorld()->LineTraceSingleByChannel(Support,Position,Position-FVector(0,0,1000),ECC_WorldStatic,Query);
        const bool HasCeiling=W.World->GetTestWorld()->LineTraceSingleByChannel(Ceiling,Position,Position+FVector(0,0,1000),ECC_WorldStatic,Query);
        W.Test.AddInfo(FString::Printf(TEXT("Flood companion %s id=%s local=%s velocity=%s mode=%d crouched=%d wants_crouch=%d half=%.2f gravity=%.2f move_tick=%d actor_tick=%d parent=%s support=%d/%s/%s ceiling=%d/%s/%s"),
            Label,*Ally->CompanionId(),*(Position-Origin).ToString(),*Movement->Velocity.ToString(),
            int32(Movement->MovementMode),Ally->IsCrouched(),Movement->bWantsToCrouch,Body->GetScaledCapsuleHalfHeight(),
            Movement->GravityScale,Movement->IsComponentTickEnabled(),Ally->IsActorTickEnabled(),*GetNameSafe(Ally->GetAttachParentActor()),
            HasSupport,*GetNameSafe(Support.GetComponent()),*(Support.ImpactPoint-Origin).ToString(),
            HasCeiling,*GetNameSafe(Ceiling.GetComponent()),*(Ceiling.ImpactPoint-Origin).ToString()));
    }
}
bool Walk(FWorld& W,const FVector& Local)
{
    const FVector Goal=FVector(W.BeatData().Space.Flood.Origin,0)+Local;
    const FVector Start=W.Hero()->GetActorLocation();
    const int32 Steps=FMath::Max(1,FMath::CeilToInt(FVector::Dist2D(Start,Goal)/1000));
    for(int32 I=1;I<=Steps;++I)
        if(!SoraLiftAutomation::Walk(*W.World,FMath::Lerp(Start,Goal,float(I)/Steps)))
        {
            Sample(W,*FString::Printf(TEXT("Walk failed target=%s segment=%d/%d"),*Local.ToString(),I,Steps));
            return false;
        }
    return true;
}
bool BankLayout(FWorld& W)
{
    const FVector O(W.BeatData().Space.Flood.Origin,0);
    FCollisionQueryParams Q(SCENE_QUERY_STAT(FloodBankLayout),false,W.Hero());
    // Probe below the ceiling on both sides of the old floor gap and the
    // descent joins. XY-only arrival cannot establish supported traversal.
    for(const FVector2D Point:{FVector2D(7199,0),FVector2D(7201,0),FVector2D(7299,0),
        FVector2D(7301,-1),FVector2D(7400,-100),FVector2D(7499,-199),FVector2D(7501,-200)})
    {
        FHitResult Hit;
        if(!W.Test.TestTrue(TEXT("The wading floor and descent have continuous production collision"),
            W.World->GetTestWorld()->LineTraceSingleByChannel(Hit,O+FVector(Point.X,0,Point.Y+20),
                O+FVector(Point.X,0,Point.Y-50),ECC_WorldStatic,Q)&&
            FMath::Abs(Hit.ImpactPoint.Z-Point.Y)<2.f&&Hit.ImpactNormal.Z>.7f)) return false;
    }
    // Trace the production collision on both sides of each join, rather than
    // merely asserting the ramp's configured angle or a coordinate volume.
    for(const FVector2D Point:{FVector2D(-3599,-200),FVector2D(-3601,-199.333),
        FVector2D(-3900,0),FVector2D(-4199,199.333),FVector2D(-4201,200),FVector2D(-4300,200)})
    {
        FHitResult Hit;
        if(!W.Test.TestTrue(TEXT("The moat, bank ramp and bank have continuous walkable collision"),
            W.World->GetTestWorld()->LineTraceSingleByChannel(Hit,O+FVector(9200,Point.X,1000),
                O+FVector(9200,Point.X,-1000),ECC_WorldStatic,Q)&&
            FMath::Abs(Hit.ImpactPoint.Z-Point.Y)<2.f&&
            Hit.ImpactNormal.Z>=W.Hero()->GetCharacterMovement()->GetWalkableFloorZ())) return false;
    }
    FHitResult Hit;
    W.Test.TestTrue(TEXT("The embankment closes the former opening beside the gate"),
        W.World->GetTestWorld()->LineTraceSingleByChannel(Hit,O+FVector(9150,-300,100),O+FVector(9150,-500,100),ECC_WorldStatic,Q));
    return W.Test.TestFalse(TEXT("The half-open gate retains real swimming clearance"),
        W.World->GetTestWorld()->LineTraceSingleByChannel(Hit,O+FVector(9500,-300,100),O+FVector(9500,-500,100),ECC_WorldStatic,Q));
}
bool OnBank(const ACharacter& Character,const FVector& Origin)
{
    const FVector At=Character.GetActorLocation()-Origin;
    const float Feet=At.Z-Character.GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    return At.Y<-4200&&FMath::Abs(Feet-SoraFloodRules::BankTop)<5.f&&Character.GetCharacterMovement()->IsMovingOnGround();
}
bool Cross(FWorld& W,const FKey& Dive,bool Late)
{
    auto* Craft=W.Fieldcraft();
    W.Harden();
    if(!BankLayout(W)) return false;
    auto* Bus=USoraGameEvents::Get(W.Hero());
    float Drowning=0;
    const auto Handle=Bus->OnDamaged.AddLambda([&](const FSoraDamagedEvent& E)
        { if(E.Victim==W.Hero()&&!E.Causer) Drowning+=E.Amount; });
    ON_SCOPE_EXIT { Bus->OnDamaged.Remove(Handle); };
    if(Late&&!W.Tick(9100)) return false;
    if(!W.Test.TestEqual(TEXT("Early wading becomes late surface swimming"),Craft->Readout(*W.Hero()).bSwimming,Late)) return false;
    if(!Walk(W,FVector(7400,0,0))) return false;
    Sample(W,TEXT("approach"));
    W.Look(FRotator::ZeroRotator);
    if(!W.Hold(EKeys::W,90)) return false;
    Sample(W,TEXT("after surfaced W hold"));
    W.Test.TestTrue(TEXT("A surfaced capsule cannot pass the real submerged roof"),
        W.Hero()->GetActorLocation().X-W.BeatData().Space.Flood.Origin.X<7500);
    if(!W.Press(Dive)||!Walk(W,FVector(8250,0,0))) return false;
    Sample(W,TEXT("shaft submerged arrival"));
    W.Test.TestEqual(TEXT("Normal input crossed the first submerged leg"),Craft->FloodPassageStage(),2);
    const float Before=Craft->Readout(*W.Hero()).Breath;
    if(!W.Tick(6)) return false;
    Sample(W,TEXT("shaft after underwater wait"));
    W.Test.TestTrue(TEXT("Being inside the shaft underwater does not restore breath"),Craft->Readout(*W.Hero()).Breath<Before);
    if(!W.Press(Dive)||!W.Tick(240)) return false;
    Sample(W,TEXT("shaft after surface recovery"));
    W.Test.TestFalse(TEXT("The actual head rises into air"),Craft->IsDiving());
    W.Test.TestTrue(TEXT("Three seconds of real air restores breath"),Craft->Readout(*W.Hero()).Breath>.99f);
    const int32 Clock=Craft->FloodElapsedMs();
    const FVector Position=W.Hero()->GetActorLocation();
    if(!W.Press(EKeys::Escape)||!W.Tick(180)) return false;
    W.Test.TestTrue(TEXT("Pause freezes the water and body"),Craft->FloodElapsedMs()<=Clock+34&&
        FVector::Dist(Position,W.Hero()->GetActorLocation())<2);
    // Clear the roof by more than the capsule radius plus Walk's tolerance.
    if(!W.Press(EKeys::Escape)||!W.Press(Dive)||!Walk(W,FVector(9100,0,0))||!W.Press(Dive)||!W.Tick(70)) return false;
    Sample(W,TEXT("culvert emergence"));
    W.Test.TestEqual(TEXT("Normal input crossed the second submerged leg"),Craft->FloodPassageStage(),4);
    W.Test.TestFalse(TEXT("Emerging from the culvert alone does not authorize exit"),Craft->FloodExitReady());
    W.Test.TestTrue(TEXT("Toranosuke physically carries Iota"),Craft->FloodCarriesIota());
    W.Test.TestEqual(TEXT("A careful route incurs no drowning damage"),Drowning,0.f);
    if(!Walk(W,FVector(9150,0,0))) return false;
    W.Look(FRotator(0,-90,0));
    if(!W.Hold(EKeys::W,120)) return false;
    Sample(W,TEXT("former gap after W hold"));
    W.Test.TestTrue(TEXT("Ordinary strokes cannot leave through the former gap beside the gate"),
        W.Hero()->GetActorLocation().Y-W.BeatData().Space.Flood.Origin.Y>-400&&!Craft->FloodExitReady());
    if(!Walk(W,FVector(9150,0,0))) return false;
    if(!Walk(W,FVector(9500,0,0))||!Walk(W,FVector(9500,-600,0))) return false;
    Sample(W,TEXT("gate crossing"));
    W.Test.TestTrue(TEXT("Actual movement crosses the half-open gate"),Craft->FloodExitReady());
    // Ascend outside the exit's X bounds first. Completion cannot hide an
    // unwalkable join, a floating body or guides stranded below the bank.
    if(!Walk(W,FVector(9200,-3900,0))||!Walk(W,FVector(9200,-4550,0))) return false;
    Sample(W,TEXT("outer bank arrival"));
    const FVector O(W.BeatData().Space.Flood.Origin,0);
    if(!W.Test.TestTrue(TEXT("Normal movement reaches the supported outer bank before entering the exit"),
        W.Campaign()->ActiveBeat()==13&&OnBank(*W.Hero(),O))) return false;
    ASoraCompanion* Carrier=nullptr;ASoraCompanion* Iota=nullptr;
    for(const auto& Ally:Craft->AlliesInPlay()) if(IsValid(Ally))
    {
        if(Ally->CompanionId()==TEXT("npc_toranosuke")) Carrier=Ally;
        if(Ally->CompanionId()==TEXT("npc_iota")) Iota=Ally;
    }
    if(!W.Test.TestNotNull(TEXT("Toranosuke remains in play"),Carrier)||!W.Test.TestNotNull(TEXT("Iota remains in play"),Iota)) return false;
    Sample(W,TEXT("carrier wait begin"));
    for(int32 Frame=0;Frame<600&&!OnBank(*Carrier,O);++Frame) if(!W.Tick(1)) return false;
    Sample(W,TEXT("carrier wait end"));
    if(!W.Test.TestTrue(TEXT("The carrier walks onto bank support with Iota still attached"),
        OnBank(*Carrier,O)&&Iota->GetAttachParentActor()==Carrier)) return false;
    W.Test.TestEqual(TEXT("Both submerged legs, the moat and bank ascent incur no drowning damage"),Drowning,0.f);
    if(!Walk(W,FVector(9200,-4300,0))) return false;
    W.Look(FRotator::ZeroRotator);
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
    SoraFloodTest::FWorld W(*this,TEXT("FloodTraversal"),5,13);
    if(!W.Start()||!W.Tick(30)||!W.Press(EKeys::Escape)||!W.Hero()->RemapCombatAction(TEXT("Crouch"),EKeys::G)||!W.Press(EKeys::Escape)) return false;
    if(!W.Press(EKeys::C)) return false;
    TestFalse(TEXT("The old crouch key cannot substitute for the rebound dive"),W.Hero()->GetCharacterMovement()->bWantsToCrouch);
    return SoraFloodTest::Cross(W,EKeys::G,false)&&!HasAnyErrors();
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraFloodLateWaterTest,"SoraArena.Campaign.FloodLateWater",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraFloodLateWaterTest::RunTest(const FString&)
{
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    SoraFloodTest::FWorld W(*this,TEXT("FloodLateWater"),5,13);
    return W.Start()&&W.Tick(30)&&SoraFloodTest::Cross(W,EKeys::Gamepad_RightThumbstick,true)&&!HasAnyErrors();
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraFloodRetryTest,"SoraArena.Campaign.FloodRetryReload",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraFloodRetryTest::RunTest(const FString&)
{
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    SoraFloodTest::FWorld W(*this,TEXT("FloodRetryReload"),5,13);
    if(!W.Start()||!W.Tick(30)) return false;
    W.Harden();
    if(!SoraFloodTest::Walk(W,FVector(7400,0,0))||!W.Press(EKeys::C)||!SoraFloodTest::Walk(W,FVector(7800,0,0))) return false;
    SoraFloodTest::Sample(W,TEXT("retry submerged approach"));
    const float Before=W.Fieldcraft()->Readout(*W.Hero()).Breath;
    if(!W.Press(EKeys::C)||!W.Tick(12)) return false;
    SoraFloodTest::Sample(W,TEXT("retry uncrouch under stone"));
    TestTrue(TEXT("An uncrouch wish under stone cannot create air"),W.Fieldcraft()->IsDiving()&&W.Fieldcraft()->Readout(*W.Hero()).Breath<Before);
    UGameplayStatics::ApplyDamage(W.Hero(),W.Hero()->Health+1000,nullptr,nullptr,UDamageType::StaticClass());
    if(!W.Tick(2)||!TestTrue(TEXT("Death opens retry"),W.Mode()->bDefeated)||!W.Press(EKeys::Enter)||!W.Tick(30)) return false;
    TestTrue(TEXT("Death retry resets water and traversal"),W.Fieldcraft()->FloodElapsedMs()<1000&&W.Fieldcraft()->FloodPassageStage()==0);
    TestFalse(TEXT("Death retry releases Iota and swimming mode"),W.Fieldcraft()->FloodCarriesIota()||W.Fieldcraft()->Readout(*W.Hero()).bSwimming);
    TestTrue(TEXT("Death retry restores normal gravity"),W.Hero()->GetCharacterMovement()->GravityScale>0);
    if(!W.Tick(300)||!SoraFloodTest::Reload(W)) return false;
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
    SoraFloodTest::FWorld W(*this,TEXT("FloodSenses"),5,13);
    if(!W.Start()||!W.Tick(30)) return false;
    W.Harden();
    TestTrue(TEXT("Hand lamps still search after the relay has been sabotaged"),W.Campaign()->RelayOffline());
    if(!SoraFloodTest::Walk(W,FVector(1700,0,0))) return false;
    bool HeardWithoutSight=false;
    for(TActorIterator<ASoraEnemyController> It(W.World->GetTestWorld());It;++It)
        HeardWithoutSight|=It->IsGuard()&&It->AwarenessPermille()>0&&!It->CanSee(*W.Hero());
    TestTrue(TEXT("Actual wading alerts a guard through sound while the stone roof occludes sight"),HeardWithoutSight);
    if(!SoraFloodTest::Walk(W,FVector(2000,0,0))||!W.Tick(100)) return false;
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
    TSharedPtr<FJsonObject> Data;
    if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Data)) return false;
    const auto O=Data->GetObjectField(TEXT("space"))->GetArrayField(TEXT("beats"))[13]->AsObject();
    for(int32 Case=0;Case<5;++Case)
    {
        FSoraChapter Copy=FSoraCatalog::Get().Chapter(5);
        auto& Lights=Copy.Beats[13].Space.Fieldcraft.Searchlights;
        if(Case==0) Lights.Pop();
        if(Case==1) Lights[3].Id=TEXT("grate_lamp_4");
        if(Case==2) Lights[3].At.X+=100;
        if(Case==3) Lights[3].Rules.LockMs=0;
        if(Case==4) Lights[3].HeightCm=210;
        TestFalse(TEXT("The production loader rejects a missing or altered moat tower"),SoraCatalogFlood::Read(*O,Copy.Beats[13],Copy.Space));
    }
    return !HasAnyErrors();
}
#endif
