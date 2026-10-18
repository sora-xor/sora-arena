#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraRecoveryAutomation.h"
#include "SoraEquipmentComponent.h"
#include "SoraSettings.h"
#include "SoraCaptions.h"
#include "GameFramework/DamageType.h"
namespace SoraRhythmAutomation
{
using SoraFieldcraftAutomation::FBeatWorld;
bool Station(FBeatWorld& W)
{
    FVector Anchor;
    return W.Campaign()->ObjectiveAnchor(Anchor)&&SoraRecoveryAutomation::WalkTo(*W.World,Anchor);
}
bool Ready(FBeatWorld& W)
{
    if(!W.Start()) return false;
    W.Harden();
    for(int32 F=0;F<1800&&!W.Mode()->IsPlaying();++F) if(!W.Tick(1)) return false;
    while(W.Campaign()->TaskProgress().Step==0)
        if(!Station(W)||!W.Press(EKeys::E)) return false;
    return Station(W);
}
bool Phrase(FBeatWorld& W,int32 Hits)
{
    auto* C=W.Campaign(); const auto Step=C->ActiveTask().Steps[1];
    for(int32 N=0;N<Step.PhraseStrikes;++N)
    {
        const int32 Until=C->RhythmState().DueMs-C->TaskProgress().ElapsedMs;
        if(Until>0&&!W.Tick(FMath::CeilToInt(Until*60.f/1000.f))) return false;
        if(N<Hits&&!W.Press(EKeys::E)) return false;
        if(!W.Tick(FMath::CeilToInt((Step.ToleranceMs+1)*60.f/1000.f))) return false;
        if(N<Step.PhraseStrikes-1&&!W.Test.TestEqual(TEXT("A phrase waits for all eight windows"),C->TaskProgress().StepDone,0)) return false;
    }
    return true;
}
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraRhythmPhraseTest,"SoraArena.Campaign.RhythmPhrases",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraRhythmPhraseTest::RunTest(const FString& Parameters)
{
    (void)Parameters; using namespace SoraRhythmAutomation;
    FBeatWorld W(*this,TEXT("RhythmPhrases"),4,7);
    if(!Ready(W)||!W.Press(EKeys::E)||!Phrase(W,6)) return false;
    auto* C=W.Campaign();
    TestEqual(TEXT("Six of all eight windows earns one hammer phrase"),C->TaskProgress().StepDone,1);
    const auto Step=C->ActiveTask().Steps[1];
    for(int32 N=0;N<8;++N)
    {
        const int32 Until=C->RhythmState().DueMs-C->TaskProgress().ElapsedMs;
        if(Until>0&&!W.Tick(FMath::CeilToInt(Until*60.f/1000.f))) return false;
        if(N<5&&!W.Press(EKeys::E)) return false;
        if(!W.Tick(FMath::CeilToInt((Step.ToleranceMs+1)*60.f/1000.f))) return false;
    }
    TestEqual(TEXT("A five-hit failed phrase preserves the first completed phrase"),C->TaskProgress().StepDone,1);
    TestEqual(TEXT("The failed phrase starts with zero attempted windows"),C->RhythmState().Attempts,0);
    TestTrue(TEXT("The real cue supplies a caption"),!USoraCaptions::Get(W.Mode())->Live().IsEmpty());
    return !HasAnyErrors();
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraRhythmAssistTest,"SoraArena.Campaign.RhythmAssist",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraRhythmAssistTest::RunTest(const FString& Parameters)
{
    (void)Parameters; using namespace SoraRhythmAutomation;
    FBeatWorld W(*this,TEXT("RhythmAssist"),4,10);
    if(!Ready(W)) return false;
    auto* C=W.Campaign();
    TestFalse(TEXT("Rhythm assist defaults off"),W.Mode()->Settings()->RhythmAssist());
    if(!W.Hold(EKeys::E,180)) return false;
    TestEqual(TEXT("Default held input does not manufacture picks"),C->TaskProgress().StepDone,0);
    UGameplayStatics::ApplyDamage(W.Hero(),1.f,nullptr,nullptr,UDamageType::StaticClass());
    W.World->InjectKey(EKeys::E,IE_Released); // fresh cue after interrupting ordinary practice
    W.Mode()->Settings()->SetRhythmAssist(true);
    if(!W.World->InjectKey(EKeys::E,IE_Pressed)||!W.Tick(458)) return false; // 7.633 s, ten complete 750 ms windows
    TestEqual(TEXT("Ten on-beat assisted picks earn seven units"),C->TaskProgress().StepDone,7);
    if(!W.World->InjectKey(EKeys::E,IE_Released)||!W.Tick(120)) return false;
    TestEqual(TEXT("Release stops assisted work"),C->TaskProgress().StepDone,7);
    if(!W.World->InjectKey(EKeys::E,IE_Pressed)||!W.Tick(20)) return false;
    UGameplayStatics::ApplyDamage(W.Hero(),1.f,nullptr,nullptr,UDamageType::StaticClass());
    if(!W.Tick(120)) return false;
    TestEqual(TEXT("A hit stops work until a fresh press"),C->TaskProgress().StepDone,7);
    TestFalse(TEXT("A hit clears the active assisted cue"),C->RhythmAssistActive());
    W.World->InjectKey(EKeys::E,IE_Released);
    return !HasAnyErrors();
}
#endif
