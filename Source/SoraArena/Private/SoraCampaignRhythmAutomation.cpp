#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraRecoveryAutomation.h"
#include "SoraEquipmentComponent.h"
#include "SoraSettings.h"
#include "SoraCaptions.h"
#include "SoraAudio.h"
#include "SoraWorldBuilder.h"
#include "Components/StaticMeshComponent.h"
#include "GameFramework/DamageType.h"
namespace SoraRhythmAutomation
{
using SoraFieldcraftAutomation::FBeatWorld;
bool Station(FBeatWorld& W)
{
    FVector Anchor;
    return W.Campaign()->ObjectiveAnchor(Anchor)&&SoraRecoveryAutomation::WalkTo(*W.World,Anchor+FVector(-180,0,0));
}
bool Ready(FBeatWorld& W)
{
    if(!W.Start()) return false;
    W.Harden();
    for(int32 F=0;F<1800&&!W.Mode()->IsPlaying();++F) if(!W.Tick(1)) return false;
    for(int32 Attempt=0;Attempt<8&&W.Campaign()->TaskProgress().Step==0;++Attempt)
        if(!Station(W)||!W.Press(EKeys::E)) return false;
    return W.Test.TestEqual(TEXT("The ordinary preparation reaches the rhythm step"),W.Campaign()->TaskProgress().Step,1)&&Station(W);
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
int32 Heard(const USoraAudioSubsystem& Audio,FName Cue)
{
    int32 Count=0;
    for(const auto& Play:Audio.Plays()) if(Play.Cue==Cue) ++Count;
    return Count;
}
UStaticMeshComponent* Tool(FBeatWorld& W,const TCHAR* Name)
{
    TArray<UStaticMeshComponent*> Parts; W.Mode()->Arena()->GetComponents(Parts);
    for(auto* Part:Parts) if(Part->GetName().Contains(Name)) return Part;
    return nullptr;
}
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraRhythmWorkshopTest,"SoraArena.Campaign.RhythmWorkshop",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraRhythmWorkshopTest::RunTest(const FString& Parameters)
{
    (void)Parameters; using namespace SoraRhythmAutomation;
    FBeatWorld W(*this,TEXT("RhythmWorkshop"),4,7);
    if(!Ready(W)) return false;
    auto* Audio=USoraAudioSubsystem::Get(W.Mode());
    if(!TestNotNull(TEXT("Workshop uses the real audio owner"),Audio)) return false;
    const int32 Music=W.Mode()->Settings()->BusVolume(ESoraAudioBus::Music);
    W.Mode()->Settings()->SetBusVolume(ESoraAudioBus::Music,0);
    Audio->ForgetPlays();
    if(!W.Press(EKeys::E)) return false;
    TestEqual(TEXT("The count-in produces one small hammer cue"),Heard(*Audio,TEXT("workshop.hammer.cue")),1);
    TestEqual(TEXT("The count-in is not a player strike"),Heard(*Audio,TEXT("workshop.hammer.hit")),0);
    auto* Hammer=Tool(W,TEXT("CueHammerHead"));
    if(!TestNotNull(TEXT("The station has its moving cue hammer"),Hammer)) return false;
    const float ContactZ=Hammer->GetRelativeLocation().Z;
    if(!W.Tick(12)) return false;
    TestTrue(TEXT("Cue hammer returns from the contact"),Hammer->GetRelativeLocation().Z>ContactZ+10.f);
    TestEqual(TEXT("Frames do not replay the same cue"),Heard(*Audio,TEXT("workshop.hammer.cue")),1);
    auto* C=W.Campaign(); const int32 Until=C->RhythmState().DueMs-C->TaskProgress().ElapsedMs;
    if(!W.Tick(FMath::CeilToInt(Until*60.f/1000.f))||!W.Press(EKeys::E)||!W.Press(EKeys::E)) return false;
    TestEqual(TEXT("An accepted strike sounds once despite a repeated press"),Heard(*Audio,TEXT("workshop.hammer.hit")),1);
    TestEqual(TEXT("Strike audio does not award an incomplete phrase"),C->TaskProgress().StepDone,0);
    for(const auto& Play:Audio->Plays())
        if(Play.Cue==TEXT("workshop.hammer.cue"))
        {
            TestEqual(TEXT("Music 0 leaves timing on the SFX telegraph bus"),Play.Bus,FName(TEXT("SFX_Telegraph")));
            TestTrue(TEXT("The cue resolves its cleared waveform"),Play.IsVoiced());
            TestTrue(TEXT("The cue is positioned at the station"),Play.bSpatial);
        }
    UGameplayStatics::ApplyDamage(W.Hero(),1.f,nullptr,nullptr,UDamageType::StaticClass());
    if(!W.Tick(2)) return false;
    const int32 AfterInterrupt=Heard(*Audio,TEXT("workshop.hammer.cue"));
    if(!W.Tick(60)) return false;
    TestEqual(TEXT("Combat interruption stops rhythm audio"),Heard(*Audio,TEXT("workshop.hammer.cue")),AfterInterrupt);
    W.Mode()->Settings()->SetBusVolume(ESoraAudioBus::Music,Music);
    return !HasAnyErrors();
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
    if(auto* Audio=USoraAudioSubsystem::Get(W.Mode()))
    {
        TestTrue(TEXT("The authored loom voice has an explicit cue contract"),Heard(*Audio,TEXT("workshop.loom.call"))>0);
        for(const auto& Play:Audio->Plays()) if(Play.Cue==TEXT("workshop.loom.call"))
            TestFalse(TEXT("No unrelated wave pretends to be Okinu's missing voice"),Play.IsVoiced());
    }
    TestNotNull(TEXT("The drawloom has a moving shuttle"),Tool(W,TEXT("Shuttle")));
    TestNotNull(TEXT("The drawloom has a figure cord marker"),Tool(W,TEXT("CordMarker")));
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
