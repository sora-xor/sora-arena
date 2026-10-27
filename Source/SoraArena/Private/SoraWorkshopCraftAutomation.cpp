#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraCatalogLanternWorkshop.h"
#include "SoraEquipmentComponent.h"
#include "SoraGameEvents.h"
#include "SoraSettings.h"
#include "SoraLiftAutomation.h"
#include "SoraWorldBuilder.h"
#include "SoraViewmodelComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/PointLight.h"
#include "Dom/JsonObject.h"
#include "GameFramework/DamageType.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/ScopeExit.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

namespace SoraWorkshopCraftTest
{
using FWorld=SoraFieldcraftAutomation::FBeatWorld;
bool Ready(FWorld& W)
{
    if(!FSoraCatalog::Get().Load()||!W.Start())return false;
    for(int I=0;I<3000&&!W.Mode()->IsPlaying();++I)if(!W.Tick(1))return false;
    W.Harden();W.Mode()->Settings()->SetRhythmAssist(false);
    return W.Test.TestTrue(TEXT("The workshop checkpoint releases normal controls"),W.Mode()->IsPlaying());
}
// These directed work tests place the hero beside a bench. The separate
// LanternWorkshop.Routes case traverses the real steps using mapped walking.
bool Station(FWorld& W)
{
    FVector P;if(!W.Campaign()->ObjectiveAnchor(P))return false;P.X-=140;
    W.Hero()->GetCharacterMovement()->StopMovementImmediately();
    W.Hero()->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
    W.Hero()->SetActorLocation(P+FVector(0,0,W.Hero()->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+2),
        false,nullptr,ETeleportType::TeleportPhysics);
    return W.Tick(8)&&W.Test.TestTrue(TEXT("The work probe is supported beside the current bench"),
        W.Hero()->GetCharacterMovement()->IsMovingOnGround());
}
bool Milliseconds(FWorld& W,int Ms)
{
    while(Ms>0){const int D=FMath::Min(Ms,50);if(!W.Tick(1,D/1000.f))return false;Ms-=D;}
    return true;
}
bool Hold(FWorld& W,int Ms)
{
    if(!W.World->InjectKey(EKeys::E,IE_Pressed))return false;
    const bool Held=Milliseconds(W,Ms),Released=W.World->InjectKey(EKeys::E,IE_Released);
    return Held&&Released&&W.Tick(1);
}
bool SixRibs(FWorld& W)
{
    if(!Station(W))return false;
    for(int I=0;I<6;++I)if(!Hold(W,800))return false;
    return W.Test.TestEqual(TEXT("Six timed releases reach the paste bench"),W.Campaign()->TaskProgress().Step,1);
}
bool Windows(FWorld& W,bool Warm)
{
    TArray<UStaticMeshComponent*> Parts;W.Mode()->Arena()->GetComponents(Parts);int Panes=0,Lights=0;
    for(auto* Part:Parts)if(Part->ComponentHasTag(TEXT("WorkshopWarmWindow")))
    {
        ++Panes;W.Test.TestEqual(TEXT("The window pane reflects restored production"),Part->IsVisible(),Warm);
        W.Test.TestEqual(TEXT("The restored window adds no collision"),Part->GetCollisionEnabled(),ECollisionEnabled::NoCollision);
    }
    for(TActorIterator<APointLight> It(W.World->GetTestWorld());It;++It)if(It->ActorHasTag(TEXT("WorkshopWindowLight")))
    {
        ++Lights;W.Test.TestEqual(TEXT("Actual warm lights follow the saved production state"),It->PointLightComponent->IsVisible(),Warm);
        W.Test.TestEqual(TEXT("Window lights have warm colour temperature"),It->PointLightComponent->Temperature,2700.f);
    }
    return W.Test.TestEqual(TEXT("The workshop has two window panes"),Panes,2)&&
        W.Test.TestEqual(TEXT("The workshop has two local window lights"),Lights,2);
}
bool Action(FWorld& W,unsigned Serial,int Step,int Unit)
{
    const auto A=W.Campaign()->WorkshopCraftView().LastAction;
    return W.Test.TestEqual(TEXT("Exactly one presentation serial per credited unit"),A.Serial,Serial)&&
        W.Test.TestEqual(TEXT("The action identifies the step that was credited"),A.Step,Step)&&
        W.Test.TestEqual(TEXT("The action identifies its one-based unit within the step"),A.Unit,Unit)&&
        W.Test.TestTrue(TEXT("The action has a bounded active-time age"),
            A.AgeMs>=0&&A.AgeMs<=SoraWorkshopCraftRules::ActionPresentationMs);
}
bool Registry(FWorld& W,bool RecentInspection=false)
{
    const auto V=W.Campaign()->WorkshopCraftView();
    W.Test.TestTrue(TEXT("The saved output presents a complete recipe without a stale held strip"),
        !V.Active&&V.RecipeComplete&&V.HeldStep==-1&&V.HeldMs==0&&V.FailedStripSerial==0&&V.FailedStripAgeMs==-1);
    if(RecentInspection)Action(W,16,5,1);
    else W.Test.TestTrue(TEXT("Restoring completed production does not replay a craft action"),
        V.LastAction.Serial==0&&V.LastAction.Step==-1&&V.LastAction.Unit==0&&V.LastAction.AgeMs==-1);
    const int Counts[]={6,4,1,1,3,1};
    for(int I=0;I<6;++I)W.Test.TestEqual(TEXT("Saved recipe presentation retains each completed station's count"),V.Committed[I],Counts[I]);
    TArray<UStaticMeshComponent*> Parts;W.Mode()->Arena()->GetComponents(Parts);
    int Benches=0;for(const auto* P:Parts)if(P->ComponentHasTag(TEXT("LanternWorkshopBench")))
    {
        ++Benches;W.Test.TestTrue(TEXT("The completed workshop still owns solid registered stations"),
            P->IsRegistered()&&P->GetCollisionEnabled()==ECollisionEnabled::QueryAndPhysics);
    }
    W.Test.TestEqual(TEXT("The restored chapter has exactly four workshop benches"),Benches,4);
    int Rows=0;for(const auto& R:W.Campaign()->RegistryRows())if(R.BeatId==TEXT("ch03.b09"))
    {++Rows;W.Test.TestEqual(TEXT("The registry records the workshop's forty lanterns"),R.Entry.Quantity,40);}
    return W.Test.TestEqual(TEXT("The workshop is recorded once"),Rows,1)&&
        W.Test.TestTrue(TEXT("The finished recipe grants the firework tube"),W.Campaign()->IsWeaponUnlocked(7))&&Windows(W,true);
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraWorkshopCraftReleaseTest,"SoraArena.Campaign.LanternWorkshop.CraftRelease",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraWorkshopCraftReleaseTest::RunTest(const FString&)
{
    using namespace SoraWorkshopCraftTest;
    FWorld W(*this,TEXT("WorkshopCraftRelease"),2,8);if(!SoraWorkshopCraftTest::Ready(W)||!Station(W))return false;
    auto* C=W.Campaign();
    const auto Initial=C->WorkshopCraftView();
    TestTrue(TEXT("A fresh workshop has no old progress or failure animation"),Initial.Active&&!Initial.RecipeComplete&&
        Initial.Step==0&&Initial.Committed[0]==0&&Initial.HeldStep==-1&&Initial.FailedStripSerial==0&&Initial.FailedStripAgeMs==-1);
    TestTrue(TEXT("A fresh workshop has no committed action to replay"),Initial.LastAction.Serial==0&&
        Initial.LastAction.Step==-1&&Initial.LastAction.Unit==0&&Initial.LastAction.AgeMs==-1);
    if(!Hold(W,639))return false;
    TestEqual(TEXT("An early release splits the strip without adding a hoop"),C->TaskProgress().Done,0);
    const auto Missed=C->WorkshopCraftView();
    TestTrue(TEXT("A split is published once with active-time age and no held work"),Missed.FailedStripSerial==1&&
        Missed.FailedStripAgeMs>=0&&Missed.Committed[0]==0&&Missed.HeldStep==-1);
    TestEqual(TEXT("A split publishes no successful action"),Missed.LastAction.Serial,0u);
    if(!Hold(W,640))return false;
    TestEqual(TEXT("The first millisecond in the green band accepts a hoop"),C->TaskProgress().Done,1);
    const auto Passed=C->WorkshopCraftView();
    TestTrue(TEXT("A fresh successful strip clears the old split pose and shows one committed hoop"),
        Passed.Committed[0]==1&&Passed.Committed[1]==0&&Passed.FailedStripSerial==1&&Passed.FailedStripAgeMs==-1);
    if(!Action(W,1,0,1))return false;
    if(!Hold(W,800))return false;
    TestEqual(TEXT("The authored beat accepts a second hoop"),C->TaskProgress().Done,2);
    if(!Hold(W,961))return false;
    TestEqual(TEXT("A late release preserves the two finished hoops"),C->TaskProgress().StepDone,2);
    if(!Hold(W,960))return false;
    TestEqual(TEXT("The last millisecond in the green band accepts a third hoop"),C->TaskProgress().Done,3);
    if(!W.World->InjectKey(EKeys::E,IE_Pressed)||!Milliseconds(W,3000))return false;
    TestEqual(TEXT("Holding through several beats never retries or credits automatically"),C->TaskProgress().Done,3);
    TestFalse(TEXT("A failed strip frees the hands"),C->WorkshopCraftOccupiesHands());
    if(!W.World->InjectKey(EKeys::E,IE_Released)||!Hold(W,0))return false;
    TestEqual(TEXT("A same-frame press and release is not a bend"),C->TaskProgress().Done,3);
    W.Mode()->Settings()->SetRhythmAssist(true);
    if(!W.World->InjectKey(EKeys::E,IE_Pressed)||!Milliseconds(W,799))return false;
    TestEqual(TEXT("Assistance still waits for the authored beat"),C->TaskProgress().Done,3);
    const auto Held=C->WorkshopCraftView();
    TestTrue(TEXT("The scene receives the same held milliseconds and assistance as the controls"),Held.Assist&&
        Held.HeldStep==0&&Held.HeldMs==799&&Held.Committed[0]==3&&Held.FailedStripAgeMs==-1);
    for(int I=0;I<100;++I)(void)C->WorkshopCraftView();
    TestEqual(TEXT("Reading presentation never advances the hold clock"),C->WorkshopCraftState().ElapsedMs,799);
    if(!Milliseconds(W,1))return false;
    TestEqual(TEXT("Assistance completes the held bend at 800 ms"),C->TaskProgress().Done,4);
    if(!Milliseconds(W,2400))return false;
    TestEqual(TEXT("Assistance never repeats a held press"),C->TaskProgress().Done,4);
    if(!Action(W,4,0,4))return false;
    if(!W.World->InjectKey(EKeys::E,IE_Released))return false;
    AddInfo(TEXT("Mapped input and active world time at seeded b09. This is mechanical coverage, not a visual or ordinary-play acceptance."));
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraWorkshopCraftInterruptTest,"SoraArena.Campaign.LanternWorkshop.CraftInterruptions",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraWorkshopCraftInterruptTest::RunTest(const FString&)
{
    using namespace SoraWorkshopCraftTest;
    FWorld W(*this,TEXT("WorkshopCraftInterrupt"),2,8);if(!SoraWorkshopCraftTest::Ready(W)||!Station(W)||!Hold(W,800))return false;
    auto* C=W.Campaign();
    if(!W.World->InjectKey(EKeys::E,IE_Pressed)||!Milliseconds(W,800))return false;
    TestFalse(TEXT("Work reserves both hands against weapon selection"),W.Hero()->GetEquipment()->EquipCampaignWeapon(0));
    if(!W.Press(EKeys::Escape)||!W.Tick(120))return false;
    TestFalse(TEXT("The menu cancels a bend inside its valid release band"),C->WorkshopCraftOccupiesHands());
    const auto Paused=C->WorkshopCraftView();
    TestTrue(TEXT("Menu cancellation publishes no stale held or failed strip"),Paused.HeldStep==-1&&Paused.HeldMs==0&&
        Paused.Committed[0]==1&&Paused.FailedStripAgeMs==-1);
    W.World->InjectKey(EKeys::E,IE_Released);W.Mode()->ResumePlay();if(!W.Tick(3))return false;
    TestEqual(TEXT("Menu input flushing cannot turn a bend into a successful release"),C->TaskProgress().Done,1);
    if(!W.World->InjectKey(EKeys::E,IE_Pressed)||!Milliseconds(W,800))return false;
    UGameplayStatics::ApplyDamage(W.Hero(),1.f,nullptr,nullptr,UDamageType::StaticClass());
    W.World->InjectKey(EKeys::E,IE_Released);if(!W.Tick(3))return false;
    TestEqual(TEXT("Damage discards only the current strip"),C->TaskProgress().Done,1);
    if(!W.World->InjectKey(EKeys::E,IE_Pressed)||!Milliseconds(W,700))return false;
    W.Stand(FVector(1960,-950,0));if(!W.Tick(1))return false;
    TestFalse(TEXT("Leaving the rib form cancels the held bend"),C->WorkshopCraftOccupiesHands());
    W.World->InjectKey(EKeys::E,IE_Released);if(!Station(W))return false;
    if(!W.World->InjectKey(EKeys::E,IE_Pressed)||!Milliseconds(W,700))return false;
    W.Hero()->SetActorLocation(W.Hero()->GetActorLocation()+FVector(0,0,50),false,nullptr,ETeleportType::TeleportPhysics);
    W.Hero()->GetCharacterMovement()->SetMovementMode(MOVE_Falling);
    if(!W.Tick(1))return false;
    W.World->InjectKey(EKeys::E,IE_Released);
    TestEqual(TEXT("An airborne release cannot credit the bend"),C->TaskProgress().Done,1);
    if(!Station(W))return false;
    for(int I=0;I<5;++I)if(!Hold(W,800))return false;
    if(!TestEqual(TEXT("Fresh attempts retain earlier progress"),C->TaskProgress().Step,1)||!Station(W))return false;
    if(!Hold(W,1499))return false;
    TestEqual(TEXT("A released 1499 ms application does not paste a panel"),C->TaskProgress().StepDone,0);
    if(!W.World->InjectKey(EKeys::E,IE_Pressed)||!Milliseconds(W,1499))return false;
    const auto Paste=C->WorkshopCraftView();
    TestTrue(TEXT("Paste presentation retains all six hoops and shows the current seam's hold"),
        Paste.Committed[0]==6&&Paste.Committed[1]==0&&Paste.HeldStep==1&&Paste.HeldMs==1499);
    TestTrue(TEXT("The HUD receives continuous paste progress"),C->HeldWorkProgress()>.99f&&C->HeldWorkProgress()<1.f);
    if(!Milliseconds(W,1))return false;
    TestEqual(TEXT("A continuous 1500 ms hold pastes one panel"),C->TaskProgress().StepDone,1);
    if(!Milliseconds(W,5000))return false;
    TestEqual(TEXT("Holding after a finished seam cannot paste the next panel"),C->TaskProgress().StepDone,1);
    W.World->InjectKey(EKeys::E,IE_Released);
    if(!W.World->InjectKey(EKeys::E,IE_Pressed)||!Milliseconds(W,1000)||!W.Press(EKeys::Escape))return false;
    W.World->InjectKey(EKeys::E,IE_Released);W.Mode()->ResumePlay();if(!W.Tick(3)||!Hold(W,500))return false;
    TestEqual(TEXT("A paused seam cannot carry partial time into a new press"),C->TaskProgress().StepDone,1);
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraWorkshopCraftStanceTest,"SoraArena.Campaign.LanternWorkshop.CraftStandingReach",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraWorkshopCraftStanceTest::RunTest(const FString&)
{
    using namespace SoraWorkshopCraftTest;
    FWorld W(*this,TEXT("WorkshopCraftStandingReach"),2,8);if(!SoraWorkshopCraftTest::Ready(W))return false;
    auto* C=W.Campaign();auto* Movement=W.Hero()->GetCharacterMovement();
    const int Counts[]={6,4,1,1,3,1};
    for(int Step=0;Step<6;++Step)
    {
        if(!TestEqual(TEXT("The stance probe reaches the next authored recipe step"),C->TaskProgress().Step,Step)||!Station(W))return false;
        const int Before=C->TaskProgress().Done;
        const auto Serial=C->WorkshopCraftView().LastAction.Serial;
        // A crouch wish is effective before the capsule's next movement tick.
        if(!W.World->InjectKey(EKeys::C,IE_Pressed)||!W.World->InjectKey(EKeys::C,IE_Released))return false;
        TestTrue(TEXT("Mapped crouch requests a lower working stance"),Movement->bWantsToCrouch);
        if(!W.World->InjectKey(EKeys::E,IE_Pressed))return false;
        TestFalse(TEXT("Crouch intent refuses a hold before the movement tick"),C->WorkshopCraftOccupiesHands());
        if(!W.World->InjectKey(EKeys::E,IE_Released)||!W.Tick(8))return false;
        if(!TestTrue(TEXT("The stance probe actually crouches on the authored floor"),W.Hero()->IsCrouched())||!Hold(W,1600))return false;
        TestEqual(TEXT("Crouched work cannot credit a timed or instant recipe step"),C->TaskProgress().Done,Before);
        TestEqual(TEXT("Refused crouched work publishes no completed action"),C->WorkshopCraftView().LastAction.Serial,Serial);
        // Standing intent does not grant reach until the actual capsule rises.
        if(!W.World->InjectKey(EKeys::C,IE_Pressed)||!W.World->InjectKey(EKeys::C,IE_Released)||
           !W.World->InjectKey(EKeys::E,IE_Pressed)||!W.World->InjectKey(EKeys::E,IE_Released))return false;
        TestEqual(TEXT("An unprocessed stand request cannot credit work"),C->TaskProgress().Done,Before);
        if(!W.Tick(8)||!TestFalse(TEXT("The worker returns to standing"),W.Hero()->IsCrouched()))return false;
        if(SoraWorkshopCraftRules::Timed(Step))
        {
            // Crouch in the bend's valid release band, or partway through paste/oil.
            if(!W.World->InjectKey(EKeys::E,IE_Pressed)||!Milliseconds(W,800)||
               !TestTrue(TEXT("A standing timed action occupies the hands"),C->WorkshopCraftOccupiesHands())||
               !W.World->InjectKey(EKeys::C,IE_Pressed)||!W.World->InjectKey(EKeys::C,IE_Released))return false;
            TestFalse(TEXT("The crouch input immediately frees both hands"),C->WorkshopCraftOccupiesHands());
            TestFalse(TEXT("Cancellation restores the normal held-weapon presentation"),W.Hero()->GetViewmodel()->bHiddenInGame);
            TestTrue(TEXT("Cancellation requires release before another attempt"),C->WorkshopCraftState().WaitRelease);
            TestEqual(TEXT("Crouching preserves completed work and discards the current unit"),C->TaskProgress().Done,Before);
            if(!W.Tick(8)||!W.Press(EKeys::C)||!W.Tick(8)||!Milliseconds(W,1800))return false;
            TestFalse(TEXT("Standing with Interact still held does not restart work"),C->WorkshopCraftOccupiesHands());
            TestEqual(TEXT("No held time is banked while crouched or standing again"),C->TaskProgress().Done,Before);
            if(!W.World->InjectKey(EKeys::E,IE_Released)||!W.Tick(1))return false;
            TestEqual(TEXT("Releasing the cancelled attempt cannot award a unit"),C->TaskProgress().Done,Before);
            TestEqual(TEXT("Cancellation publishes no successful action clip"),C->WorkshopCraftView().LastAction.Serial,Serial);
        }
        for(int Unit=0;Unit<Counts[Step];++Unit)
        {
            if(SoraWorkshopCraftRules::Timed(Step)) { if(!Hold(W,Step==0?800:1500))return false; }
            else if(!W.Press(EKeys::E))return false;
        }
    }
    TestEqual(TEXT("Fresh standing interactions complete the full recipe"),C->ActiveBeat(),9);
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraWorkshopCraftRecipeTest,"SoraArena.Campaign.LanternWorkshop.CraftRecipePersistence",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraWorkshopCraftRecipeTest::RunTest(const FString&)
{
    using namespace SoraWorkshopCraftTest;
    {
        FWorld W(*this,TEXT("WorkshopCraftRecipe"),2,8);if(!SoraWorkshopCraftTest::Ready(W)||!Windows(W,false))return false;
        TArray<UStaticMeshComponent*> Parts;W.Mode()->Arena()->GetComponents(Parts);
        TArray<TWeakObjectPtr<UStaticMeshComponent>> Benches;
        for(auto* P:Parts)if(P->ComponentHasTag(TEXT("LanternWorkshopBench")))Benches.Add(P);
        if(!TestEqual(TEXT("The recipe starts at four chapter-owned benches"),Benches.Num(),4))return false;
        auto* Events=USoraGameEvents::Get(W.Mode());if(!TestNotNull(TEXT("Production events exist"),Events))return false;
        int Restored=0;const auto Handle=Events->OnSiteRestored.AddLambda([&](const FSoraSiteRestoredEvent& E)
            {if(E.bCampaign&&E.ChapterId==2&&E.SiteIndex==1)++Restored;});
        ON_SCOPE_EXIT{Events->OnSiteRestored.Remove(Handle);};
        if(!SixRibs(W)||!Station(W))return false;
        if(!Action(W,6,0,6))return false;
        for(int I=0;I<4;++I)if(!Hold(W,1500)||!Action(W,7+I,1,I+1))return false;
        if(!TestEqual(TEXT("Four pasted panels lead to rim assembly"),W.Campaign()->TaskProgress().Step,2)||!W.Press(EKeys::E))return false;
        if(!Action(W,11,2,1))return false;
        const auto Rim=W.Campaign()->WorkshopCraftView().LastAction;
        for(int I=0;I<100;++I)(void)W.Campaign()->WorkshopCraftView();
        TestEqual(TEXT("Reading the action cannot age its presentation"),W.Campaign()->WorkshopCraftView().LastAction.AgeMs,Rim.AgeMs);
        TestEqual(TEXT("Reading the action cannot credit another unit"),W.Campaign()->TaskProgress().Done,11);
        if(!W.Press(EKeys::Escape))return false;
        const int PausedAge=W.Campaign()->WorkshopCraftView().LastAction.AgeMs;
        if(!W.Tick(120))return false;
        TestEqual(TEXT("The menu freezes the successful action's age"),W.Campaign()->WorkshopCraftView().LastAction.AgeMs,PausedAge);
        W.Mode()->ResumePlay();
        if(!Milliseconds(W,2400))return false;
        TestEqual(TEXT("An old action saturates at the clip limit"),W.Campaign()->WorkshopCraftView().LastAction.AgeMs,
            SoraWorkshopCraftRules::ActionPresentationMs);
        TestEqual(TEXT("Finishing a presentation never credits work"),W.Campaign()->TaskProgress().Done,11);
        if(!TestEqual(TEXT("Rims lead to the oil rack"),W.Campaign()->TaskProgress().Step,3)||!Station(W)||!Hold(W,1500))return false;
        if(!Action(W,12,3,1))return false;
        if(!TestEqual(TEXT("Oil leads to the separate shell bench"),W.Campaign()->TaskProgress().Step,4))return false;
        // The storehouse wall is within interaction radius of this bench.
        // A same-height inside placement must still fail its visibility ray.
        W.Hero()->SetActorLocation(FVector(2930,-2050,90.15),false,nullptr,ETeleportType::TeleportPhysics);
        if(!W.Tick(8)||!W.Press(EKeys::E))return false;
        TestEqual(TEXT("The shell bench cannot be worked through the storehouse wall"),W.Campaign()->TaskProgress().StepDone,0);
        if(!Action(W,12,3,1))return false;
        if(!Station(W))return false;
        for(int I=0;I<3;++I)if(!W.Press(EKeys::E)||!Action(W,13+I,4,I+1))return false;
        if(!TestEqual(TEXT("Three shells lead to fuse inspection"),W.Campaign()->TaskProgress().Step,5))return false;
        const FVector InspectionAt=W.Hero()->GetActorLocation();
        const FRotator InspectionLook=W.Hero()->GetControlRotation();
        if(!W.Press(EKeys::E))return false;
        if(!TestEqual(TEXT("The full recipe enters the next beat"),W.Campaign()->ActiveBeat(),9)||!Registry(W,true))return false;
        TestTrue(TEXT("Finishing inspection preserves the player's physical place"),W.Hero()->GetActorLocation().Equals(InspectionAt,.1));
        TestTrue(TEXT("Finishing inspection preserves the player-controlled camera"),W.Hero()->GetControlRotation().Equals(InspectionLook,.01));
        for(const auto& P:Benches)TestTrue(TEXT("The same station component survives the task transition"),P.IsValid()&&P->IsRegistered());
        TestEqual(TEXT("Completion emits one site restoration event"),Restored,1);
        for(int I=0;I<3000&&!W.Mode()->IsPlaying();++I)if(!W.Tick(1))return false;
        // Isolate physical exit from stealth balance. These are actual mapped
        // walking segments, with the new square's opponents held in place.
        for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)if(It->IsEnemy()&&It->IsAlive())
        {
            It->SetActorTickEnabled(false);It->GetCharacterMovement()->StopMovementImmediately();
            It->GetCharacterMovement()->SetComponentTickEnabled(false);
            if(auto* C=It->GetController())C->SetActorTickEnabled(false);
        }
        for(const FVector P:{FVector(2650,-1900,0),FVector(2650,-1800,0),FVector(2440,-1800,0),
            FVector(2440,-1030,0),FVector(3280,-1030,0),FVector(3480,-1030,0),FVector(3480,0,0),
            FVector(3000,0,0),FVector(1100,0,0)})
            if(!TestTrue(TEXT("The completed workshop has a continuous walked exit to the square"),SoraLiftAutomation::Walk(*W.World,P)))return false;
        TestEqual(TEXT("Walking to the square does not skip its charge encounter"),W.Campaign()->ActiveBeat(),9);
        UGameplayStatics::ApplyDamage(W.Hero(),W.Hero()->Health,nullptr,nullptr,UDamageType::StaticClass());
        if(!TestTrue(TEXT("The next checkpoint is retried through real defeat"),W.Mode()->bDefeated)||!W.Press(EKeys::Enter))return false;
        for(int I=0;I<3000&&!W.Mode()->IsPlaying();++I)if(!W.Tick(1))return false;
        if(!Registry(W))return false;
        TestTrue(TEXT("A retry still restores the square's checkpoint entry"),FVector::Dist2D(W.Hero()->GetActorLocation(),
            FVector(W.Campaign()->ActiveSpace()->Entry,0))<30.);
        for(const auto& P:Benches)TestTrue(TEXT("Retry removes the old chapter's station components"),!P.IsValid()||!P->IsRegistered());
        TestEqual(TEXT("Retry does not replay the production award"),Restored,1);
    }
    {
        FWorld W(*this,TEXT("WorkshopCraftLater"),2,15);if(!SoraWorkshopCraftTest::Ready(W)||!Registry(W))return false;
    }
    AddInfo(TEXT("The recipe uses mapped keys from a seeded checkpoint; station placement is assisted. Later checkpoint, real lights and registry are checked without claiming rendered or ordinary-play acceptance."));
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraWorkshopCraftLoaderTest,"SoraArena.Campaign.LanternWorkshop.CraftLoader",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraWorkshopCraftLoaderTest::RunTest(const FString&)
{
    if(!FSoraCatalog::Get().Load())return false;FString Text;
    if(!FFileHelper::LoadFileToString(Text,*FPaths::Combine(FPaths::ProjectContentDir(),TEXT("Data/campaign/chapter_03.json"))))return false;
    for(int Case=0;Case<9;++Case)
    {
        TSharedPtr<FJsonObject> Data;if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Data))return false;
        auto O=Data->GetObjectField(TEXT("space"))->GetArrayField(TEXT("beats"))[8]->AsObject();
        if(Case==1)O->RemoveField(TEXT("workshop_craft"));
        if(Case==2)O->SetBoolField(TEXT("workshop_craft"),true);
        if(Case==3)O->GetObjectField(TEXT("workshop_craft"))->SetArrayField(TEXT("bend_release_ms"),{MakeShared<FJsonValueNumber>(799),MakeShared<FJsonValueNumber>(160)});
        if(Case==4)O->GetObjectField(TEXT("workshop_craft"))->SetArrayField(TEXT("paste_hold_ms"),{MakeShared<FJsonValueNumber>(1499)});
        FSoraChapter Copy=FSoraCatalog::Get().Chapter(2);
        if(Case==5)Copy.Beats[8].Id=TEXT("ch03.b08");
        if(Case==6)Copy.Beats[8].Task.Steps[0].Count=7;
        if(Case==7)Copy.Beats[8].StepKinds[0]=TEXT("paste");
        if(Case==8)Copy.Beats[8].Task.Steps[0].BeatMs=799;
        TestEqual(TEXT("The native catalog binds the authored crafting controls"),
            SoraCatalogLanternWorkshop::Read(*O,Copy.Beats[8],Copy.Space),Case==0);
    }
    return !HasAnyErrors();
}
#endif
