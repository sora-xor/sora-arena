#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraHelmAutomation.h"
#include "SoraSettings.h"
#include "SoraWorldBuilder.h"
#include "Components/BoxComponent.h"
#include "GameFramework/DamageType.h"
#include "GameFramework/InputSettings.h"
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
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraHelmTrimTest,"SoraArena.Campaign.HelmTrim",
 EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraHelmTrimTest::RunTest(const FString& Parameters)
{
    (void)Parameters;using namespace SoraHelmTest;
    const auto Mappings=GetDefault<UInputSettings>()->GetActionMappings();FString ControlSlot;
    ON_SCOPE_EXIT { TestTrue(TEXT("Helm fixture restores global mappings"),Mappings==GetDefault<UInputSettings>()->GetActionMappings());
        TestFalse(TEXT("Helm fixture removes its control profile"),UGameplayStatics::DoesSaveGameExist(ControlSlot,0)); };
    FBeatWorld W(*this,TEXT("HelmTrim"),6,13);ControlSlot=FSoraAutomationWorld::ControlSlot(W.Slot);
    if(!Start(W)) return false;
    TArray<uint8> Before,After;if(!UGameplayStatics::LoadDataFromSlot(Before,W.Slot,0)) return false;
    auto* C=W.Campaign();const auto& H=W.BeatData().Space.Helm;
    TestEqual(TEXT("Normal deadline is authored"),C->HelmState().DeadlineMs,150000);
    if(!Walk(W,FVector(H.Hold.Center,0))||!Alarm(W)) return false;
    TestEqual(TEXT("Walking and holding releases first trim"),C->HelmState().Raised,1u);
    if(!W.Hold(EKeys::E,125)) return false;
    TestTrue(TEXT("Remote held interaction cannot correct the wheel"),C->HelmNeedsTrim());
    if(!Walk(W,C->HelmWheelPoint()+FVector(-190,0,0))||!TestTrue(TEXT("Wheel is physically reachable"),C->AtHelmWheel())) return false;
    // An actual intervening solid blocks interaction, even at valid 2D range.
    auto* Block=W.World->GetTestWorld()->SpawnActor<AActor>();
    auto* Box=NewObject<UBoxComponent>(Block);Block->SetRootComponent(Box);Box->SetBoxExtent(FVector(15,90,120));
    Box->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);Box->SetCollisionResponseToAllChannels(ECR_Block);Box->RegisterComponent();
    Block->SetActorLocation(C->HelmWheelPoint()+FVector(-90,0,120));
    TestFalse(TEXT("A blocked wheel is unreachable"),C->AtHelmWheel());Block->Destroy();if(!Tick(W,2)) return false;
    if(!W.Press(EKeys::SpaceBar)||!Tick(W,5)) return false;
    TestFalse(TEXT("An airborne hand cannot correct the wheel"),C->AtHelmWheel());
    if(!Tick(W,100)) return false;
    if(!W.Hold(EKeys::E,60)||!Tick(W,2)) return false;
    TestTrue(TEXT("Releasing early resets correction without clearing the alarm"),C->HelmNeedsTrim()&&!C->HelmState().Working&&C->HelmState().HeldMs==0);
    const int32 Clock=C->TaskProgress().ElapsedMs;
    if(!W.Press(EKeys::Escape)||!W.Hero()->RemapCombatAction(TEXT("Interact"),EKeys::G)||!Tick(W,20,.5f)) return false;
    TestEqual(TEXT("Pause freezes the deadline and grace"),C->TaskProgress().ElapsedMs,Clock);
    W.Mode()->ResumePlay();if(!Tick(W,2)||!W.Hold(EKeys::E,130)) return false;
    TestTrue(TEXT("Old binding does not correct the wheel"),C->HelmNeedsTrim());
    if(!SoraHelmAutomation::Correct(*W.World,EKeys::G)) return false;
    TestEqual(TEXT("Mapped G corrects the real wheel"),C->HelmState().Corrected,1u);
    if(!TestTrue(TEXT("Partial helm work does not rewrite its start checkpoint"),UGameplayStatics::LoadDataFromSlot(After,W.Slot,0)&&Before==After)) return false;
    if(!Reload(W)) return false;C=W.Campaign();
    TestTrue(TEXT("Fresh-world load restarts progress, trims and clock"),C->TaskProgress().Progress==0&&C->HelmState().Raised==0&&C->TaskProgress().ElapsedMs<1000);
    if(!Walk(W,FVector(W.BeatData().Space.Helm.Hold.Center,0))) return false;
    for(int Trim=0;Trim<3;++Trim)
    {
        if(!Alarm(W)) return false;
        FKey Use=EKeys::G;
        if(Trim==1) for(const FKey& Key:W.Hero()->GetActionKeys(TEXT("Interact"))) if(Key.IsGamepadKey()) { Use=Key;break; }
        if(!TestTrue(TEXT("A gamepad Interact binding exists"),Trim!=1||Use.IsGamepadKey())||!SoraHelmAutomation::Correct(*W.World,Use)) return false;
        TestEqual(TEXT("Each threshold is corrected once"),C->HelmState().Corrected,(1u<<(Trim+1))-1u);
        if(!Walk(W,FVector(W.BeatData().Space.Helm.Hold.Center,0))) return false;
    }
    for(int F=0;F<1200&&C->ActiveBeat()==13;++F) if(!Tick(W,1)) return false;
    TestTrue(TEXT("Ordinary hold and three mapped corrections complete the production site"),C->ActiveBeat()!=13&&!W.Mode()->bDefeated);
    return !HasAnyErrors();
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraHelmDeadlineTest,"SoraArena.Campaign.HelmDeadline",
 EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraHelmDeadlineTest::RunTest(const FString& Parameters)
{
    (void)Parameters;using namespace SoraHelmTest;FBeatWorld W(*this,TEXT("HelmDeadline"),6,13);
    if(!Start(W)) return false;auto* C=W.Campaign();
    if(!Walk(W,FVector(W.BeatData().Space.Helm.Hold.Center,0))||!Alarm(W)) return false;
    while(C->HelmState().GraceMs>0) if(!Tick(W,1)) return false;
    const int32 Progress=C->TaskProgress().Progress,Clock=C->TaskProgress().ElapsedMs;
    if(!Tick(W,120)) return false;
    const int32 Ms=C->TaskProgress().ElapsedMs-Clock;
    TestTrue(TEXT("Ignored trim decays by 2 percent of the whole hold each second"),FMath::Abs(Progress-C->TaskProgress().Progress-Ms*12/10)<=2);
    TestEqual(TEXT("Decay never rearms the threshold"),C->HelmState().Raised,1u);
    for(int Frame=0;Frame<400&&!W.Mode()->bDefeated;++Frame) if(!Tick(W,1,.5f)) return false;
    if(!TestTrue(TEXT("Ignoring the helm reaches a checkpoint failure"),W.Mode()->bDefeated)) return false;
    TestEqual(TEXT("Deadline expires at exactly 150 seconds"),C->TaskProgress().ElapsedMs,150000);
    if(!W.Press(EKeys::Enter)||!Tick(W,2)) return false;
    TestTrue(TEXT("Deadline retry resets helm state"),!W.Mode()->bDefeated&&C->HelmState().Raised==0&&C->TaskProgress().Progress==0);
    W.Harden();UGameplayStatics::ApplyDamage(W.Hero(),W.Hero()->Health+1000.f,nullptr,nullptr,UDamageType::StaticClass());
    if(!Tick(W,2)||!W.Press(EKeys::Enter)||!Tick(W,2)) return false;
    TestTrue(TEXT("Death retry also resets helm state"),!W.Mode()->bDefeated&&C->HelmState().Raised==0&&C->TaskProgress().Progress==0);
    return !HasAnyErrors();
}
#endif
