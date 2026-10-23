#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraHelmAutomation.h"
#include "SoraSettings.h"
#include "SoraWorldBuilder.h"
#include "SoraViewmodelComponent.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "GameFramework/DamageType.h"
#include "GameFramework/InputSettings.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PlayerInput.h"
#include "HAL/IConsoleManager.h"
#include "Misc/ScopeExit.h"
namespace SoraHelmTest
{
using SoraFieldcraftAutomation::FBeatWorld;
// These directed fixtures isolate the wheel/clock, not encounter difficulty.
void Freeze(FBeatWorld& W)
{
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
        if(It->IsActorTickEnabled())
        {
            It->SetActorTickEnabled(false);It->SetActorEnableCollision(false);
            It->GetCharacterMovement()->StopMovementImmediately();It->GetCharacterMovement()->SetComponentTickEnabled(false);
            if(It->GetController()) It->GetController()->SetActorTickEnabled(false);
            It->SetActorLocation(FVector(W.BeatData().Space.Entry+FVector2D(600,1500),100));
        }
}
bool Tick(FBeatWorld& W,int Frames,float Dt=1.f/60.f)
{
    for(int F=0;F<Frames;++F) { Freeze(W);if(!W.Tick(1,Dt)) return false; } return true;
}
bool Start(FBeatWorld& W)
{
    if(!FSoraCatalog::Get().Load()||!W.Start()) return false;
    W.Harden();Freeze(W);
    return W.Campaign()->IsHelmHold();
}
bool Walk(FBeatWorld& W,const FVector& P) { Freeze(W);return SoraRecoveryAutomation::WalkTo(*W.World,P); }
FKey Action(FBeatWorld& W,const TCHAR* Name)
{
    for(const FKey& Key:W.Hero()->GetActionKeys(Name)) if(!Key.IsGamepadKey()) return Key;
    return FKey();
}
bool Alarm(FBeatWorld& W)
{
    for(int F=0;F<1200&&!W.Campaign()->HelmNeedsTrim();++F) if(!Tick(W,1)) return false;
    Freeze(W);return W.Campaign()->HelmNeedsTrim();
}
bool Reload(FBeatWorld& W)
{
    W.Fieldcraft()->OnEvent.Remove(W.EventsHandle);
    W.World->DestroyTestWorld(true);W.World->ForwardErrorMessages(&W.Test);W.World.Reset();
    W.World=MakeUnique<FSoraAutomationWorld>();
    if(!W.World->Start(W.Slot)||!W.World->Tick(1)||!W.World->EnableKeyInput()) return false;
    for(int N=0;N<3&&!W.Mode()->IsPlaying();++N) if(!W.Press(EKeys::Enter)) return false;
    W.EventsHandle=W.Fieldcraft()->OnEvent.AddLambda([&W](FName Event) { W.Events.Add(Event.ToString()); });
    W.Harden();Freeze(W);return W.Mode()->IsPlaying();
}
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraHelmHandsTest,"SoraArena.Campaign.HelmHandsAndFloor",
 EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraHelmHandsTest::RunTest(const FString& Parameters)
{
    (void)Parameters;SoraHelmTest::FBeatWorld W(*this,TEXT("HelmHandsAndFloor"),6,13);
    if(!SoraHelmTest::Start(W)) return false;
    auto* C=W.Campaign();auto* Kit=W.Hero()->GetEquipment();const auto& H=W.BeatData().Space.Helm;
    TArray<UStaticMeshComponent*> Pieces;W.Mode()->Arena()->GetComponents(Pieces);
    UStaticMeshComponent* Floor=nullptr;UStaticMeshComponent* Fill=nullptr;
    for(auto* Piece:Pieces)
    {
        TestFalse(TEXT("Helm never displays the generic circular hold boundary"),Piece->GetName().Contains(TEXT("KitHoldRing"))||Piece->GetName().Contains(TEXT("KitHoldPost")));
        if(Piece->ComponentHasTag(TEXT("HelmHoldFloor"))) { TestNull(TEXT("One helm floor"),Floor);Floor=Piece; }
        if(Piece->ComponentHasTag(TEXT("HelmHoldFill"))) { TestNull(TEXT("One helm fill"),Fill);Fill=Piece; }
    }
    if(!TestNotNull(TEXT("The authored hold has a rendered floor"),Floor)||!TestNotNull(TEXT("The authored hold has a rendered fill"),Fill)) return false;
    const FBox Bounds=Floor->CalcBounds(Floor->GetComponentTransform()).GetBox();
    TestTrue(TEXT("Visible floor bounds match the actual 6 by 16 metre hold"),
        FMath::IsNearlyEqual(Bounds.GetSize().X,H.Hold.Size.X,1.)&&FMath::IsNearlyEqual(Bounds.GetSize().Y,H.Hold.Size.Y,1.)&&
        FVector::Dist2D(Bounds.GetCenter(),FVector(H.Hold.Center,0))<1.);
    if(!SoraHelmTest::Walk(W,FVector(H.Hold.Center+FVector2D(350,0),0))) return false;
    int32 Progress=C->TaskProgress().Progress;if(!SoraHelmTest::Tick(W,60)) return false;
    TestEqual(TEXT("Outside the rectangle earns no progress, even inside the old circle"),C->TaskProgress().Progress,Progress);
    if(!SoraHelmTest::Walk(W,FVector(H.Hold.Center+FVector2D(-200,-650),0))) return false;
    Progress=C->TaskProgress().Progress;if(!SoraHelmTest::Tick(W,60)) return false;
    TestTrue(TEXT("The long end of the rectangle earns progress outside the old circle"),C->TaskProgress().Progress-Progress>=999);
    const FBox Filled=Fill->CalcBounds(Fill->GetComponentTransform()).GetBox();
    TestTrue(TEXT("The progress fill stays inside the hold and spans its full width"),
        Filled.Min.X>=Bounds.Min.X-1.&&Filled.Max.X<=Bounds.Max.X+1.&&
        FMath::IsNearlyEqual(Filled.Min.Y,Bounds.Min.Y,1.)&&FMath::IsNearlyEqual(Filled.Max.Y,Bounds.Max.Y,1.));
    if(!SoraHelmTest::Alarm(W)||!SoraHelmTest::Walk(W,C->HelmWheelPoint()+FVector(-190,0,0))) return false;
    // Select through the ordinary arm-group actions, not direct equipment writes.
    if(!W.Press(SoraHelmTest::Action(W,TEXT("WeaponThree")))||!W.Press(SoraHelmTest::Action(W,TEXT("WeaponOne")))||!SoraHelmTest::Tick(W,30)) return false;
    if(!TestTrue(TEXT("A drawn blade is selected"),SoraHistoricalArms::IsMelee(W.Hero()->WeaponId)&&!Kit->IsSheathing())) return false;
    const FKey Use=SoraHelmTest::Action(W,TEXT("Interact")),Sheathe=SoraHelmTest::Action(W,TEXT("Sheathe"));
    if(!W.Hold(Use,125)) return false;
    TestTrue(TEXT("A drawn blade cannot work the helm"),C->HelmNeedsTrim()&&!C->HelmOccupiesHands()&&C->HelmState().HeldMs==0);
    if(!W.Press(Sheathe)||!W.World->InjectKey(Use,IE_Pressed)||!SoraHelmTest::Tick(W,10)) return false;
    TestTrue(TEXT("Correction cannot bypass the existing sheathing duration"),Kit->IsSheathing()&&!Kit->IsSheathed()&&!C->HelmOccupiesHands());
    if(!SoraHelmTest::Tick(W,45)||!W.World->InjectKey(Use,IE_Released)||!SoraHelmTest::Tick(W,1)||!W.World->InjectKey(Use,IE_Pressed)||!SoraHelmTest::Tick(W,30)) return false;
    if(!TestTrue(TEXT("The stowed blade leaves both hands on the wheel"),Kit->IsSheathed()&&C->HelmOccupiesHands()&&W.Hero()->GetViewmodel()->bHiddenInGame)) return false;
    const int32 Weapon=W.Hero()->WeaponId;
    for(const TCHAR* Name:{TEXT("Fire"),TEXT("Melee"),TEXT("Block"),TEXT("Reload"),TEXT("Sheathe"),TEXT("WeaponThree")})
        if(!W.Press(SoraHelmTest::Action(W,Name))) return false;
    TestTrue(TEXT("Weapon inputs cannot draw, attack, guard, reload or change arms during correction"),
        C->HelmOccupiesHands()&&Kit->IsSheathed()&&!Kit->IsCommittedStrike()&&!Kit->IsGuardHeld()&&!Kit->bReloading&&W.Hero()->WeaponId==Weapon);
    UGameplayStatics::ApplyDamage(W.Hero(),1.f,nullptr,nullptr,UDamageType::StaticClass());
    TestTrue(TEXT("Damage immediately frees the hands and discards partial work"),!C->HelmOccupiesHands()&&C->HelmState().HeldMs==0&&!W.Hero()->GetViewmodel()->bHiddenInGame);
    if(!SoraHelmTest::Tick(W,125)) return false;
    TestEqual(TEXT("Held input cannot resume correction after a hit"),C->HelmState().Corrected,0u);
    if(!W.World->InjectKey(Use,IE_Released)||!SoraHelmTest::Tick(W,1)||!SoraHelmAutomation::Correct(*W.World,Use)) return false;
    TestTrue(TEXT("Correction restores the selected sheathed blade without consuming inventory"),C->HelmState().Corrected==1u&&Kit->IsSheathed()&&W.Hero()->WeaponId==Weapon&&!W.Hero()->GetViewmodel()->bHiddenInGame);
    if(!W.Press(SoraHelmTest::Action(W,TEXT("WeaponThree")))||!SoraHelmTest::Tick(W,30)||!SoraHelmTest::Alarm(W)||!SoraHelmTest::Walk(W,C->HelmWheelPoint()+FVector(-190,0,0))) return false;
    if(!TestEqual(TEXT("The ordinary bow selection succeeds after work"),W.Hero()->WeaponId,18)) return false;
    const FKey Fire=SoraHelmTest::Action(W,TEXT("Fire"));const int32 Ammo=Kit->Ammo;
    if(!W.World->InjectKey(Fire,IE_Pressed)||!SoraHelmTest::Tick(W,50)||!TestTrue(TEXT("The bow is actually drawn"),Kit->IsBowDrawing())) return false;
    if(!W.World->InjectKey(Use,IE_Pressed)||!SoraHelmTest::Tick(W,20)||!W.World->InjectKey(Fire,IE_Released)||!SoraHelmTest::Tick(W,2)) return false;
    TestTrue(TEXT("Taking the wheel puts the drawn bow aside without firing"),C->HelmOccupiesHands()&&!Kit->IsBowDrawing()&&Kit->Ammo==Ammo&&W.Hero()->GetViewmodel()->bHiddenInGame);
    for(const TCHAR* Name:{TEXT("Fire"),TEXT("Melee"),TEXT("Reload"),TEXT("Block"),TEXT("WeaponOne")})
        if(!W.Press(SoraHelmTest::Action(W,Name))) return false;
    TestTrue(TEXT("The stowed bow cannot fire, reload, guard or switch while hands are occupied"),C->HelmOccupiesHands()&&!Kit->IsBowDrawing()&&!Kit->IsCommittedStrike()&&!Kit->bReloading&&!Kit->IsGuardHeld()&&Kit->Ammo==Ammo&&W.Hero()->WeaponId==18);
    if(!W.World->InjectKey(Use,IE_Released)) return false;
    TestTrue(TEXT("Release frees hands immediately, before the next world tick"),!C->HelmOccupiesHands()&&C->HelmState().HeldMs==0&&!W.Hero()->GetViewmodel()->bHiddenInGame);
    if(!SoraHelmTest::Tick(W,2)||!W.Hold(Fire,50)) return false;
    TestEqual(TEXT("Normal firing works again after releasing the helm"),Kit->Ammo,Ammo-1);
    if(!SoraHelmAutomation::Correct(*W.World,Use)) return false;
    TestEqual(TEXT("The ranged loadout can complete the same real correction"),C->HelmState().Corrected,3u);
    if(!W.Press(SoraHelmTest::Action(W,TEXT("WeaponFour")))||!SoraHelmTest::Tick(W,45)||!W.Press(Fire)) return false;
    const int32 GunAmmo=Kit->Ammo,Gun=W.Hero()->WeaponId;
    if(!TestTrue(TEXT("A normal firearm shot leaves room in the magazine"),Gun!=18&&!SoraHistoricalArms::IsMelee(Gun)&&GunAmmo<FSoraCatalog::Get().Weapon(Gun).Magazine)) return false;
    if(!SoraHelmTest::Alarm(W)||!SoraHelmTest::Walk(W,C->HelmWheelPoint()+FVector(-190,0,0))||!W.World->InjectKey(Use,IE_Pressed)||!SoraHelmTest::Tick(W,20)) return false;
    if(!W.Press(SoraHelmTest::Action(W,TEXT("Reload")))||!W.Press(Fire)) return false;
    TestTrue(TEXT("A partially empty firearm cannot reload or fire with both hands on the wheel"),C->HelmOccupiesHands()&&!Kit->bReloading&&Kit->Ammo==GunAmmo);
    if(!W.World->InjectKey(Use,IE_Released)||!SoraHelmTest::Tick(W,2)||!W.Press(SoraHelmTest::Action(W,TEXT("Reload")))) return false;
    if(!TestTrue(TEXT("Normal reload begins after releasing the wheel"),Kit->bReloading)||!W.Press(Use)) return false;
    TestTrue(TEXT("Reloading refuses helm admission without cancelling or crediting either action"),Kit->bReloading&&!C->HelmOccupiesHands()&&C->HelmState().HeldMs==0);
    for(int Frame=0;Frame<600&&Kit->bReloading;++Frame) if(!SoraHelmTest::Tick(W,1)) return false;
    if(!TestFalse(TEXT("The ordinary reload completes"),Kit->bReloading)||!SoraHelmAutomation::Correct(*W.World,Use)) return false;
    TestEqual(TEXT("All three corrections preserve the currently selected ranged arm"),W.Hero()->WeaponId,Gun);
    TestTrue(TEXT("All three heading corrections are earned"),(C->ActiveBeat()==13&&C->HelmState().Corrected==7u)||(C->ActiveBeat()==14&&!W.Mode()->bDefeated));
    return !HasAnyErrors();
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraHelmTrimTest,"SoraArena.Campaign.HelmTrim",
 EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraHelmTrimTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    const auto Mappings=GetDefault<UInputSettings>()->GetActionMappings();FString ControlSlot;
    ON_SCOPE_EXIT { TestTrue(TEXT("Helm fixture restores global mappings"),Mappings==GetDefault<UInputSettings>()->GetActionMappings());
        TestFalse(TEXT("Helm fixture removes its control profile"),UGameplayStatics::DoesSaveGameExist(ControlSlot,0)); };
    SoraHelmTest::FBeatWorld W(*this,TEXT("HelmTrim"),6,13);ControlSlot=FSoraAutomationWorld::ControlSlot(W.Slot);
    if(!SoraHelmTest::Start(W)) return false;
    TArray<uint8> Before,After;if(!UGameplayStatics::LoadDataFromSlot(Before,W.Slot,0)) return false;
    auto* C=W.Campaign();const auto& H=W.BeatData().Space.Helm;
    TestEqual(TEXT("Normal deadline is authored"),C->HelmState().DeadlineMs,150000);
    if(!SoraHelmTest::Walk(W,FVector(H.Hold.Center,0))||!SoraHelmTest::Alarm(W)) return false;
    TestEqual(TEXT("Walking and holding releases first trim"),C->HelmState().Raised,1u);
    if(!W.Hold(EKeys::E,125)) return false;
    TestTrue(TEXT("Remote held interaction cannot correct the wheel"),C->HelmNeedsTrim());
    if(!SoraHelmTest::Walk(W,C->HelmWheelPoint()+FVector(-190,0,0))||!TestTrue(TEXT("Wheel is physically reachable"),C->AtHelmWheel())) return false;
    // An actual intervening solid blocks interaction, even at valid 2D range.
    auto* Block=W.World->GetTestWorld()->SpawnActor<AActor>();
    auto* Box=NewObject<UBoxComponent>(Block);Block->SetRootComponent(Box);Box->SetBoxExtent(FVector(15,90,120));
    Box->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);Box->SetCollisionResponseToAllChannels(ECR_Block);Box->RegisterComponent();
    Block->SetActorLocation(C->HelmWheelPoint()+FVector(-90,0,120));
    TestFalse(TEXT("A blocked wheel is unreachable"),C->AtHelmWheel());Block->Destroy();if(!SoraHelmTest::Tick(W,2)) return false;
    if(!W.Press(EKeys::SpaceBar)||!SoraHelmTest::Tick(W,5)) return false;
    TestFalse(TEXT("An airborne hand cannot correct the wheel"),C->AtHelmWheel());
    if(!SoraHelmTest::Tick(W,100)) return false;
    if(!SoraHelmAutomation::Stow(*W.World)||!W.Hold(EKeys::E,60)||!SoraHelmTest::Tick(W,2)) return false;
    TestTrue(TEXT("Releasing early resets correction without clearing the alarm"),C->HelmNeedsTrim()&&!C->HelmState().Working&&C->HelmState().HeldMs==0);
    const int32 Clock=C->TaskProgress().ElapsedMs;
    if(!W.Press(EKeys::Escape)||!W.Hero()->RemapCombatAction(TEXT("Interact"),EKeys::G)||!SoraHelmTest::Tick(W,20,.5f)) return false;
    TestEqual(TEXT("Pause freezes the elapsed deadline clock"),C->TaskProgress().ElapsedMs,Clock);
    W.Mode()->ResumePlay();if(!SoraHelmTest::Tick(W,2)||!W.Hold(EKeys::E,130)) return false;
    TestTrue(TEXT("Old binding does not correct the wheel"),C->HelmNeedsTrim());
    if(!SoraHelmAutomation::Correct(*W.World,EKeys::G)) return false;
    TestEqual(TEXT("Mapped G corrects the real wheel"),C->HelmState().Corrected,1u);
    if(!TestTrue(TEXT("Partial helm work does not rewrite its start checkpoint"),UGameplayStatics::LoadDataFromSlot(After,W.Slot,0)&&Before==After)) return false;
    if(!SoraHelmTest::Reload(W)) return false;C=W.Campaign();
    TestTrue(TEXT("Fresh-world load restarts progress, trims and clock"),C->TaskProgress().Progress==0&&C->HelmState().Raised==0&&C->TaskProgress().ElapsedMs<1000);
    if(!SoraHelmTest::Walk(W,FVector(W.BeatData().Space.Helm.Hold.Center,0))) return false;
    for(int Trim=0;Trim<3;++Trim)
    {
        if(!SoraHelmTest::Alarm(W)) return false;
        FKey Use=EKeys::G;
        if(Trim==1) for(const FKey& Key:W.Hero()->GetActionKeys(TEXT("Interact"))) if(Key.IsGamepadKey()) { Use=Key;break; }
        if(!TestTrue(TEXT("A gamepad Interact binding exists"),Trim!=1||Use.IsGamepadKey())||!SoraHelmAutomation::Correct(*W.World,Use)) return false;
        TestEqual(TEXT("Each threshold is corrected once"),C->HelmState().Corrected,(1u<<(Trim+1))-1u);
        if(!SoraHelmTest::Walk(W,FVector(W.BeatData().Space.Helm.Hold.Center,0))) return false;
    }
    for(int F=0;F<1200&&C->ActiveBeat()==13;++F) if(!SoraHelmTest::Tick(W,1)) return false;
    TestTrue(TEXT("Ordinary hold and three mapped corrections complete the production site"),C->ActiveBeat()!=13&&!W.Mode()->bDefeated);
    return !HasAnyErrors();
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraHelmPauseTest,"SoraArena.Campaign.HelmActiveHoldPause",
 EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraHelmPauseTest::RunTest(const FString& Parameters)
{
    (void)Parameters;SoraHelmTest::FBeatWorld W(*this,TEXT("HelmActiveHoldPause"),6,13);
    if(!SoraHelmTest::Start(W)) return false;
    auto* C=W.Campaign();auto* Kit=W.Hero()->GetEquipment();
    if(!SoraHelmTest::Walk(W,C->HelmWheelPoint()+FVector(-190,0,0))||!SoraHelmAutomation::Stow(*W.World)) return false;
    auto* Controller=Cast<APlayerController>(W.Hero()->GetController());
    const auto* Reconcile=IConsoleManager::Get().FindConsoleVariable(TEXT("Input.AutoReconcilePressedEventsOnFirstRepeat"));
    if(!TestTrue(TEXT("The real input stack and repeat policy are available"),Controller&&Controller->PlayerInput&&Reconcile)) return false;
    const bool ReconcilesRepeat=Reconcile->GetBool();
    AddInfo(FString::Printf(TEXT("Helm pause input repeat reconciliation enabled=%d"),ReconcilesRepeat));
    const FKey Use=SoraHelmTest::Action(W,TEXT("Interact"));
    const int32 Weapon=W.Hero()->WeaponId,Ammo=Kit->Ammo;
    const bool Sheathed=Kit->IsSheathed();
    // Exercise both physical release while paused and a key kept down across
    // resume. UE may reconcile its repeat into a new press after the HUD flush;
    // any accepted event must start an entirely new correction.
    for(bool ReleaseWhilePaused:{true,false})
    {
        if(!SoraHelmTest::Alarm(W)) return false;
        const int32 WorkClock=C->TaskProgress().ElapsedMs;
        if(!W.World->InjectKey(Use,IE_Pressed)||!SoraHelmTest::Tick(W,60)) return false;
        const auto Before=C->HelmState();
        const int32 Clock=C->TaskProgress().ElapsedMs,Progress=C->TaskProgress().Progress;
        if(!TestTrue(TEXT("Pause starts during real partial wheel work, with grace remaining"),
            C->HelmOccupiesHands()&&Before.HeldMs>0&&Before.HeldMs<W.BeatData().Space.Helm.Contract.WorkMs&&
            Before.GraceMs>0&&W.Hero()->GetViewmodel()->bHiddenInGame)) return false;
        TestEqual(TEXT("Partial correction accounts for exactly the active held time"),Before.HeldMs,Clock-WorkClock);
        // Observe menu cleanup before a world tick or an Interact release can
        // hide a missing cancellation behind normal TickHelm processing.
        if(!W.World->InjectKey(EKeys::Escape,IE_Pressed)) return false;
        if(!TestTrue(TEXT("Opening pause immediately frees helm hands and discards partial work"),
            W.Mode()->bMenu&&W.World->GetTestWorld()->IsPaused()&&!C->HelmOccupiesHands()&&
            !C->HelmState().Working&&C->HelmState().HeldMs==0&&!W.Hero()->GetViewmodel()->bHiddenInGame)) return false;
        TestEqual(TEXT("Opening pause does not advance the deadline"),C->TaskProgress().ElapsedMs,Clock);
        TestEqual(TEXT("Opening pause does not spend grace"),C->HelmState().GraceMs,Before.GraceMs);
        // This headless world lacks the Slate HUD's focus callback. Use its
        // actual engine flush here, after observing explicit menu cleanup.
        Controller->PlayerInput->FlushPressedKeys();
        if(!W.World->InjectKey(EKeys::Escape,IE_Released)||
            (ReleaseWhilePaused&&!W.World->InjectKey(Use,IE_Released))||!SoraHelmTest::Tick(W,20,.5f)) return false;
        TestEqual(TEXT("Ten paused seconds leave the elapsed deadline exact"),C->TaskProgress().ElapsedMs,Clock);
        TestEqual(TEXT("Ten paused seconds leave grace exact"),C->HelmState().GraceMs,Before.GraceMs);
        TestEqual(TEXT("Pause preserves the authored deadline"),C->HelmState().DeadlineMs,Before.DeadlineMs);
        TestEqual(TEXT("Pause grants no hold progress"),C->TaskProgress().Progress,Progress);
        TestEqual(TEXT("Pause preserves the pending heading alarm"),C->HelmState().Pending,Before.Pending);
        TestEqual(TEXT("Pause does not raise another heading alarm"),C->HelmState().Raised,Before.Raised);
        TestEqual(TEXT("Pause credits no correction"),C->HelmState().Corrected,Before.Corrected);
        TestTrue(TEXT("Partial work remains cancelled throughout pause"),!C->HelmState().Working&&C->HelmState().HeldMs==0);
        if(!W.Press(EKeys::Escape)) return false;
        Controller->PlayerInput->FlushPressedKeys(); // HUD also flushes on close.
        if(!SoraHelmTest::Tick(W,30)) return false;
        const int32 ResumedMs=C->TaskProgress().ElapsedMs-Clock;
        TestTrue(TEXT("Mapped resume restarts the ordinary campaign clock"),!W.Mode()->bMenu&&!W.World->GetTestWorld()->IsPaused()&&ResumedMs>0);
        TestEqual(TEXT("Grace spends only actual resumed time"),C->HelmState().GraceMs,FMath::Max(0,Before.GraceMs-ResumedMs));
        TestTrue(TEXT("Resume alone without an accepted Interact event cannot restart or complete work"),
            !C->HelmOccupiesHands()&&!C->HelmState().Working&&C->HelmState().HeldMs==0&&C->HelmState().Corrected==Before.Corrected);
        TestTrue(TEXT("Menu cancellation restores the selected weapon without changing its state"),
            !W.Hero()->GetViewmodel()->bHiddenInGame&&W.Hero()->WeaponId==Weapon&&Kit->Ammo==Ammo&&Kit->IsSheathed()==Sheathed);
        if(ReleaseWhilePaused)
        {
            if(!W.World->InjectKey(Use,IE_Pressed)) return false;
        }
        else
        {
            const auto* KeyState=Controller->PlayerInput->GetKeyState(Use);
            if(!TestTrue(TEXT("The held-repeat case reaches the actual post-flush engine path"),KeyState&&KeyState->bWasJustFlushed)) return false;
            // Send a held OS-style repeat at full depression through the same
            // controller/input stack as FSoraAutomationWorld's key helper.
            Controller->InputKey(FInputKeyEventArgs::CreateSimulated(Use,IE_Repeat,1.f,1));
            const TArray<UInputComponent*> Stack={W.Hero()->InputComponent};
            Controller->PlayerInput->ProcessInputStack(Stack,1.f/60.f,false);
            if(!TestEqual(TEXT("Repeat admission follows the engine's current reconciliation policy"),C->HelmOccupiesHands(),ReconcilesRepeat)) return false;
            if(!ReconcilesRepeat)
            {
                // Respect a configured policy that refuses repeat admission;
                // a real release/press then begins the same new correction.
                if(!W.World->InjectKey(Use,IE_Released)||!W.World->InjectKey(Use,IE_Pressed)) return false;
            }
        }
        if(!TestTrue(TEXT("An accepted post-resume event starts with zero old work credit"),C->HelmOccupiesHands()&&C->HelmState().HeldMs==0)) return false;
        const int32 RestartClock=C->TaskProgress().ElapsedMs;
        if(!SoraHelmTest::Tick(W,60)) return false;
        TestEqual(TEXT("Restarted work counts only newly elapsed held time"),C->HelmState().HeldMs,C->TaskProgress().ElapsedMs-RestartClock);
        TestTrue(TEXT("A new half correction cannot reuse the discarded pre-pause half"),
            C->HelmOccupiesHands()&&C->HelmState().HeldMs>0&&C->HelmState().HeldMs<W.BeatData().Space.Helm.Contract.WorkMs&&C->HelmState().Corrected==Before.Corrected);
        if(!SoraHelmTest::Tick(W,65)||!W.World->InjectKey(Use,IE_Released)) return false;
        TestTrue(TEXT("A full new correction restores the selected weapon and credits only its pending alarm"),
            C->HelmState().Corrected==(Before.Corrected|(1u<<Before.Pending))&&!C->HelmNeedsTrim()&&!C->HelmOccupiesHands()&&C->HelmState().HeldMs==0&&
            !W.Hero()->GetViewmodel()->bHiddenInGame&&W.Hero()->WeaponId==Weapon&&Kit->Ammo==Ammo&&Kit->IsSheathed()==Sheathed);
    }
    return !HasAnyErrors();
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraHelmDeadlineTest,"SoraArena.Campaign.HelmDeadline",
 EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraHelmDeadlineTest::RunTest(const FString& Parameters)
{
    (void)Parameters;SoraHelmTest::FBeatWorld W(*this,TEXT("HelmDeadline"),6,13);
    if(!SoraHelmTest::Start(W)) return false;auto* C=W.Campaign();
    if(!SoraHelmTest::Walk(W,FVector(W.BeatData().Space.Helm.Hold.Center,0))||!SoraHelmTest::Alarm(W)) return false;
    while(C->HelmState().GraceMs>0) if(!SoraHelmTest::Tick(W,1)) return false;
    const int32 Progress=C->TaskProgress().Progress,Clock=C->TaskProgress().ElapsedMs;
    if(!SoraHelmTest::Tick(W,120)) return false;
    const int32 Ms=C->TaskProgress().ElapsedMs-Clock;
    TestTrue(TEXT("Ignored trim decays by 2 percent of the whole hold each second"),FMath::Abs(Progress-C->TaskProgress().Progress-Ms*12/10)<=2);
    TestEqual(TEXT("Decay never rearms the threshold"),C->HelmState().Raised,1u);
    for(int Frame=0;Frame<400&&!W.Mode()->bDefeated;++Frame) if(!SoraHelmTest::Tick(W,1,.5f)) return false;
    if(!TestTrue(TEXT("Ignoring the helm reaches a checkpoint failure"),W.Mode()->bDefeated)) return false;
    TestEqual(TEXT("Deadline expires at exactly 150 seconds"),C->TaskProgress().ElapsedMs,150000);
    if(!W.Press(EKeys::Enter)||!SoraHelmTest::Tick(W,2)) return false;
    TestTrue(TEXT("Deadline retry resets helm state"),!W.Mode()->bDefeated&&C->HelmState().Raised==0&&C->TaskProgress().Progress==0);
    W.Harden();UGameplayStatics::ApplyDamage(W.Hero(),W.Hero()->Health+1000.f,nullptr,nullptr,UDamageType::StaticClass());
    if(!SoraHelmTest::Tick(W,2)||!W.Press(EKeys::Enter)||!SoraHelmTest::Tick(W,2)) return false;
    TestTrue(TEXT("Death retry also resets helm state"),!W.Mode()->bDefeated&&C->HelmState().Raised==0&&C->TaskProgress().Progress==0);
    return !HasAnyErrors();
}
#endif
