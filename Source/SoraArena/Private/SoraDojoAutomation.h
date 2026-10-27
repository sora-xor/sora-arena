#pragma once
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraAutomationWorld.h"
#include "SoraCampaignDirector.h"
#include "SoraCombatRules.h"
#include "SoraEnemy.h"
#include "SoraEquipmentComponent.h"
#include "SoraGameEvents.h"
#include "SoraGameMode.h"
#include "SoraPlayerCharacter.h"
#include "Camera/CameraComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Controller.h"
#include "InputCoreTypes.h"
#include "Misc/AutomationTest.h"
#include "Misc/ScopeExit.h"

// Actual pupil windup, capsule movement and mapped guard/step/attack input.
// No synthesized combat events, damage, transform writes or shortened clocks.
namespace SoraDojoAutomation
{
struct FMeeting
{
    TWeakObjectPtr<ASoraEnemy> Pupil;
    int32 HeldMs=-1,BeatMs=0;
};
inline ASoraEnemy* Pupil(FSoraAutomationWorld& W)
{
    for(TActorIterator<ASoraEnemy> It(W.GetTestWorld());It;++It)
        if(It->IsDojoPupil()&&It->IsAlive()) return *It;
    return nullptr;
}
inline void Face(FSoraAutomationWorld& W,const ASoraEnemy& Opponent)
{
    auto* Hero=W.Player();
    const FRotator View=(Opponent.GetActorLocation()+FVector(0,0,30)-Hero->GetCamera()->GetComponentLocation()).Rotation();
    Hero->GetController()->SetControlRotation(View); Hero->FaceRotation(View,0.f);
    // This test world has no local camera manager.
    Hero->GetCamera()->SetWorldRotation(View);
}
inline int32 HintCount(const USoraCampaignDirector& C)
{
    int32 Count=0;
    for(const auto& Line:C.QueuedSubtitles()) Count+=Line.LineId==TEXT("ch01.b04.sekireisai.003");
    return Count;
}
inline bool Meet(FAutomationTestBase& Test,FSoraAutomationWorld& W,bool Parry,FMeeting& Result,
    const FKey& Guard=EKeys::LeftControl)
{
    auto* Events=USoraGameEvents::Get(W.GetTestWorld());
    if(!Test.TestNotNull(TEXT("The live combat event bus exists"),Events)) return false;
    TWeakObjectPtr<ASoraEnemy> Attacker;
    float LandsAt=-1.f;
    bool Received=false,Raised=false;
    const auto Windup=Events->OnMeleeCommitted.AddLambda([&](const FSoraMeleeCommittedEvent& E) {
        if(auto* Enemy=Cast<ASoraEnemy>(E.Attacker); Enemy&&Enemy->IsDojoPupil()&&Enemy->IsAlive())
        { Attacker=Enemy; LandsAt=W.GetTestWorld()->GetTimeSeconds()+E.WindupSeconds; }
    });
    auto& Defense=Parry?Events->OnParried:Events->OnGuarded;
    const auto Met=Defense.AddLambda([&](const FSoraDefenseEvent& E) {
        if(E.Defender==W.Player()&&E.bDojo&&E.Attacker==Attacker.Get())
        {
            Received=true; Result.Pupil=Attacker; Result.HeldMs=E.HeldMs;
            Result.BeatMs=W.Mode()->Campaign()->TaskProgress().ElapsedMs;
        }
    });
    ON_SCOPE_EXIT { Events->OnMeleeCommitted.Remove(Windup); Defense.Remove(Met); };
    if(!W.InjectKey(Guard,IE_Released)||!W.Tick(1)) return false;
    for(int32 Frame=0;Frame<1800&&!Received;++Frame)
    {
        auto* Enemy=Pupil(W);
        if(!Enemy) break;
        Face(W,*Enemy);
        const bool Close=FVector::Dist2D(Enemy->GetActorLocation(),W.Player()->GetActorLocation())<=170.f;
        if(!W.InjectKey(EKeys::W,Close||Enemy->IsPupilWindup()?IE_Released:IE_Pressed)) return false;
        const float Remaining=LandsAt-W.GetTestWorld()->GetTimeSeconds();
        if(!Raised&&Attacker.IsValid()&&Remaining>0.f&&(!Parry||Remaining<=.16f))
        {
            if(!W.InjectKey(Guard,IE_Pressed)) return false;
            Raised=true;
        }
        if(!W.Tick(1)) return false;
    }
    if(!W.InjectKey(EKeys::W,IE_Released)) return false;
    if(!Received)
        Test.AddError(FString::Printf(TEXT("Pupil defense never resolved: parry=%d raised=%d beat=%d input=%d hero=%s pupil=%s guard=%d stamina=%.3f due=%.3f now=%.3f"),
            Parry,Raised,W.Mode()->Campaign()->ActiveBeat(),int32(W.Mode()->InputState()),*W.Player()->GetActorLocation().ToString(),
            *GetNameSafe(Attacker.Get()),W.Player()->GetEquipment()->IsGuardHeld(),W.Player()->GetEquipment()->GuardReserve(),
            LandsAt,W.GetTestWorld()->GetTimeSeconds()));
    else
        UE_LOG(LogTemp,Display,TEXT("Dojo actual %s: held_ms=%d beat_ms=%d hero=%s pupil=%s"),
            Parry?TEXT("awase"):TEXT("guard"),Result.HeldMs,Result.BeatMs,*W.Player()->GetActorLocation().ToString(),
            *Result.Pupil->GetActorLocation().ToString());
    return Received&&Test.TestTrue(TEXT("The live pupil contact uses the authored guard/awase timing"),
        Parry?Result.HeldMs>=0&&Result.HeldMs<=SoraDojoRules::ParryWindowMs:Result.HeldMs>=SoraDojoRules::GuardHoldMs);
}
inline bool MissFlank(FAutomationTestBase& Test,FSoraAutomationWorld& W)
{
    FMeeting Met;
    if(!Meet(Test,W,true,Met)) return false;
    auto* C=W.Mode()->Campaign();
    for(int32 Frame=0;Frame<90&&C->TaskProgress().ElapsedMs-Met.BeatMs<=SoraCombatRules::MarobashiWindowMs;++Frame)
        if(!W.Tick(1)) return false;
    return Test.TestTrue(TEXT("A real awase left without Step raises the authored do-not-stop line"),HintCount(*C)>0);
}
inline bool Step(FAutomationTestBase& Test,FSoraAutomationWorld& W)
{
    const FVector Before=W.Player()->GetActorLocation();
    if(!W.InjectKey(EKeys::D,IE_Pressed)||!W.Tick(1)||!W.InjectKey(EKeys::SpaceBar,IE_Pressed)) return false;
    const bool Began=W.Player()->GetEquipment()->IsStepping();
    if(!W.InjectKey(EKeys::SpaceBar,IE_Released)||!W.InjectKey(EKeys::D,IE_Released)||
        !W.InjectKey(EKeys::LeftControl,IE_Released)||!W.Tick(24)) return false;
    return Test.TestTrue(TEXT("Right plus mapped Step performs a real swept marobashi"),
        Began&&W.Mode()->Campaign()->TaskProgress().Flanked&&FVector::Dist2D(Before,W.Player()->GetActorLocation())>50.f);
}
inline bool StrikePupil(FAutomationTestBase& Test,FSoraAutomationWorld& W)
{
    TWeakObjectPtr<ASoraEnemy> Enemy=Pupil(W);
    if(!Test.TestTrue(TEXT("A live pupil is available for the actual bout"),Enemy.IsValid())) return false;
    const float Before=Enemy->Health;
    for(int32 Cut=0;Cut<8&&Enemy.IsValid()&&Enemy->IsAlive();++Cut)
    {
        // Receive each real cut, then strike during its real 1.2 s stagger.
        // Holding through the first 0.7 s also spends the learned guard's
        // ordinary stamina before a point can restore any of it.
        FMeeting Met;
        if(!Meet(Test,W,true,Met)) return false;
        for(int32 Frame=0;Frame<90&&W.Mode()->Campaign()->TaskProgress().ElapsedMs-Met.BeatMs<700;++Frame)
            if(!W.Tick(1)) return false;
        if(!Test.TestTrue(TEXT("The return cut reaches an actually staggered pupil"),Enemy.IsValid()&&Enemy->IsStaggered())) return false;
        Face(W,*Enemy);
        if(!W.PressKey(EKeys::LeftMouseButton)) return false;
    }
    if(!W.InjectKey(EKeys::W,IE_Released)) return false;
    const bool Down=!Enemy.IsValid()||!Enemy->IsAlive();
    if(!Down) Test.AddError(FString::Printf(TEXT("Actual pupil cuts did not finish: health %.3f -> %.3f hero=%s pupil=%s input=%d"),
        Before,Enemy->Health,*W.Player()->GetActorLocation().ToString(),*Enemy->GetActorLocation().ToString(),int32(W.Mode()->InputState())));
    return Down;
}
}
#endif
