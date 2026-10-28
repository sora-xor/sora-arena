#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraEnemyController.h"
#include "SoraWorldBuilder.h"
#include "Components/CapsuleComponent.h"

namespace SoraNoticeEncounterTest
{
// A directed, full-encounter route from the actual saved start. The fixture
// never moves actors, changes health/senses or pauses any guard. Facing is
// supplied as the test world's camera update; actions use the input mappings.
struct FRoute
{
    SoraFieldcraftAutomation::FBeatWorld W;
    bool Pad=false,AllowDetection=false,Detected=false;
    float Seconds=0,StartingHealth=0;
    int32 PeakMeter=0,MostEnemies=0;
    FString Step=TEXT("checkpoint"),Detector;
    FDelegateHandle Detection;
    TArray<TWeakObjectPtr<ASoraEnemy>> InitialGuards;
    FRoute(FAutomationTestBase& Test,const FString& Name,bool Controller)
        :W(Test,*Name,2,9),Pad(Controller){}
    ~FRoute(){if(W.World)W.Stealth()->OnDetected.Remove(Detection);}
    FVector Feet()const
    {return W.Hero()->GetActorLocation()-FVector(0,0,W.Hero()->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());}
    bool Check(bool Ok,const TCHAR* Why)
    {
        if(Ok)return true;
        W.Test.AddInfo(FString::Printf(TEXT("Encounter failure at %s, %.3fs: %s; feet=%s hp=%.2f/%.2f detected=%d by=%s meter_peak=%d beat=%d input=%d charge=%d held=%d fuse=%d"),
            *Step,Seconds,Why,*Feet().ToString(),W.Hero()->Health,W.Hero()->MaxHealth,Detected,*Detector,PeakMeter,
            W.Campaign()->ActiveBeat(),int(W.Mode()->InputState()),int(W.Campaign()->TerminalState().Stage),
            W.Campaign()->TerminalState().HeldMs,W.Campaign()->TerminalState().FuseAgeMs));
        for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
        {
            const auto* Brain=Cast<ASoraEnemyController>(It->GetController());
            W.Test.AddInfo(FString::Printf(TEXT("Guard %s type=%s at=%s yaw=%.2f alive=%d state=%d sees=%d meter=%d"),
                *It->GetName(),*It->ArchetypeId().ToString(),*It->GetActorLocation().ToString(),It->GetActorRotation().Yaw,
                It->IsAlive(),Brain?int(Brain->State()):-1,Brain&&Brain->SeesHero(),Brain?Brain->MeterPermille():-1));
        }
        return W.Test.TestTrue(Why,false);
    }
    bool Tick(int Frames=1)
    {
        for(int I=0;I<Frames;++I)
        {
            if(!W.Tick(1))return false;
            Seconds+=1.f/60.f;
            PeakMeter=FMath::Max(PeakMeter,W.Stealth()->Readout(*W.Hero()).MeterPermille);
            int Count=0;for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)++Count;
            MostEnemies=FMath::Max(MostEnemies,Count);
            if(!Check(!W.Mode()->bDefeated&&W.Hero()->IsAlive(),TEXT("The unmodified hero survives the route"))||
               !Check(AllowDetection||!Detected,TEXT("The approach remains undetected before lighting the fuse")))return false;
        }
        return true;
    }
    bool Press(const FKey& Key)
    {
        return W.World->InjectKey(Key,IE_Pressed)&&Tick()&&W.World->InjectKey(Key,IE_Released)&&Tick();
    }
    bool Crouch(bool Want)
    {
        if(W.Hero()->IsCrouched()!=Want&&!Press(Pad?EKeys::Gamepad_RightThumbstick:EKeys::C))return false;
        return Tick(3)&&Check(W.Hero()->IsCrouched()==Want,TEXT("The mapped stance change succeeds"));
    }
    bool Start()
    {
        if(!FSoraCatalog::Get().Load()||!W.Start())return false;
        Detection=W.Stealth()->OnDetected.AddLambda([this](const FSoraStealthDetection& D)
        {Detected=true;Detector=GetNameSafe(D.By.Get());});
        for(int I=0;I<3000&&!W.Mode()->IsPlaying();++I)if(!Tick())return false;
        StartingHealth=W.Hero()->Health;
        for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
        {
            InitialGuards.Add(*It);
            const auto* Brain=Cast<ASoraEnemyController>(It->GetController());
            if(!Check(It->IsAlive()&&It->IsActorTickEnabled()&&Brain&&Brain->IsActorTickEnabled(),TEXT("Every encounter guard and brain starts live")))return false;
        }
        W.Test.AddInfo(FString::Printf(TEXT("Saved start feet=%s health=%.2f max=%.2f guards=%d"),*Feet().ToString(),StartingHealth,W.Hero()->MaxHealth,InitialGuards.Num()));
        return Check(W.Mode()->IsPlaying()&&InitialGuards.Num()==7,TEXT("The saved encounter releases control with all seven guards"))&&
            Check(FVector2D::Distance(FVector2D(Feet()),W.BeatData().Space.Entry)<10,TEXT("The route begins at the authored checkpoint entry"))&&
            Check(W.Stealth()->Zone().Difficulty==SoraStealthRules::EDifficulty::Normal,TEXT("The full encounter uses Normal difficulty"));
    }
    bool Move(FVector2D To,bool Low)
    {
        Step=FString::Printf(TEXT("walk to %s"),*To.ToString());
        if(!Crouch(Low))return false;
        float Largest=0;
        for(int I=0;I<1800&&FVector2D::Distance(FVector2D(Feet()),To)>12;++I)
        {
            W.Look((FVector(To,0)-W.Hero()->GetActorLocation()).GetSafeNormal2D().Rotation());
            const FVector Before=W.Hero()->GetActorLocation();
            if(!(Pad?W.World->InjectAxis(EKeys::Gamepad_LeftY,1):W.World->InjectKey(EKeys::W,IE_Pressed))||!Tick())return false;
            Largest=FMath::Max(Largest,float(FVector::Dist(Before,W.Hero()->GetActorLocation())));
            if(!Check(W.Hero()->GetCharacterMovement()->IsMovingOnGround()&&Largest<15,TEXT("The route walks continuously on real floor support")))return false;
        }
        if(!(Pad?W.World->InjectAxis(EKeys::Gamepad_LeftY,0):W.World->InjectKey(EKeys::W,IE_Released))||!Tick(4))return false;
        W.Test.AddInfo(FString::Printf(TEXT("%s reached at %.3fs; feet=%s crouch=%d peak_meter=%d health=%.2f"),*Step,Seconds,*Feet().ToString(),Low,PeakMeter,W.Hero()->Health));
        return Check(FVector2D::Distance(FVector2D(Feet()),To)<30,TEXT("The physical walking segment reaches its endpoint"));
    }
    bool Flight(const FSoraLadder& Ladder,bool Up)
    {
        Step=Ladder.Id+(Up?TEXT(" up"):TEXT(" down"));
        if(!Crouch(false))return false;
        W.Look(FRotator(0,Ladder.Yaw+(Up?0:180),0));
        if(!Check(W.Fieldcraft()->Readout(*W.Hero()).bAtLadder,TEXT("The ordinary approach reaches a usable ladder end"))||
           !Press(Pad?EKeys::Gamepad_FaceButton_Bottom:EKeys::SpaceBar)||
           !Check(W.Fieldcraft()->IsOnLadder(),TEXT("Mapped jump begins the climb")))return false;
        float Largest=0;
        for(int I=0;I<600&&W.Fieldcraft()->IsOnLadder();++I)
        {
            const FVector Before=W.Hero()->GetActorLocation();if(!Tick())return false;
            Largest=FMath::Max(Largest,float(FVector::Dist(Before,W.Hero()->GetActorLocation())));
        }
        W.Test.AddInfo(FString::Printf(TEXT("%s at %.3fs feet=%s max_step=%.3f"),*Step,Seconds,*Feet().ToString(),Largest));
        return Tick(4)&&Check(!W.Fieldcraft()->IsOnLadder()&&W.Hero()->GetCharacterMovement()->IsMovingOnGround()&&Largest<=2.6,
            TEXT("Both real ladder flights finish supported at the authored pace"));
    }
    bool AlleyWindow()
    {
        // The 1.2 m passage is closed along its east side until y=760.
        // Wait behind that real wall for the drone's northward pass, then
        // use the opening. This fixed rehearsal timing is not evidence of
        // first-time player discoverability or arbitrary entry phases.
        if(!Move(FVector2D(-1000,950),true))return false;
        Step=TEXT("wait behind alley wall for drone pass");
        const float Phase=FMath::Fmod(Seconds,36.f);
        const float Delay=Phase<=18.f?18.f-Phase:54.f-Phase;
        if(!Tick(FMath::CeilToInt(Delay*60)))return false;
        W.Test.AddInfo(FString::Printf(TEXT("Alley patrol window at %.3fs; feet=%s peak_meter=%d"),Seconds,*Feet().ToString(),PeakMeter));
        return true;
    }
    bool Roof()
    {
        if(!AlleyWindow())return false;
        for(FVector2D P:{FVector2D(-1000,700),FVector2D(-350,700),FVector2D(-350,1800),FVector2D(350,1800),FVector2D(500,1750),FVector2D(500,1600)})if(!Move(P,true))return false;
        const auto A=W.Craft().Ladders[0],B=W.Craft().Ladders[1];
        if(!Flight(A,true)||!Move(B.Foot,true)||!Flight(B,true))return false;
        for(FVector2D P:{FVector2D(1100,1000),FVector2D(1100,800),FVector2D(1010,800)})if(!Move(P,true))return false;
        ASoraEnemy* Mark=nullptr;
        for(auto& Guard:InitialGuards)if(Guard.IsValid()&&Guard->ArchetypeId()==TEXT("marksman"))Mark=Guard.Get();
        if(!Check(Mark&&Mark->IsAlive(),TEXT("The original ridge marksman remains live")))return false;
        Step=TEXT("ridge takedown");W.LookAt(Mark->GetActorLocation());
        if(!Check(W.Stealth()->TakedownTarget(*W.Hero())==Mark,TEXT("The actual rear approach offers a takedown"))||
           !Press(Pad?EKeys::Gamepad_FaceButton_Right:EKeys::RightMouseButton)||!Tick(180)||
           !Check(Mark->IsBody()&&!Mark->IsUnconscious(),TEXT("Mapped melee defeats only the ridge marksman")))return false;
        for(FVector2D P:{FVector2D(1100,800),FVector2D(1100,1000),FVector2D(650,1250)})if(!Move(P,true))return false;
        if(!Flight(B,false)||!Move(FVector2D(500,1450),true)||!Flight(A,false))return false;
        for(FVector2D P:{FVector2D(500,1750),FVector2D(350,1800),FVector2D(-350,1800),FVector2D(-350,700),FVector2D(-1000,700),FVector2D(-1000,950)})if(!Move(P,true))return false;
        return true;
    }
    bool Hold(SoraTerminalChargeRules::EStage Target)
    {
        Step=Target==SoraTerminalChargeRules::EStage::Planted?TEXT("plant charge"):TEXT("light fuse");
        const FKey Key=Pad?EKeys::Gamepad_FaceButton_Top:EKeys::E;
        W.LookAt(FVector(-730,560,110));
        if(!W.World->InjectKey(Key,IE_Pressed))return false;
        for(int I=0;I<360&&W.Campaign()->TerminalState().Stage!=Target;++I)if(!Tick())return false;
        return W.World->InjectKey(Key,IE_Released)&&Tick()&&Check(W.Campaign()->TerminalState().Stage==Target,TEXT("The live encounter permits the complete physical work hold"));
    }
    bool Charge()
    {
        using SoraTerminalChargeRules::EStage;
        if(!AlleyWindow()||!Move(FVector2D(-1000,548),true)||!Move(FVector2D(-730,548),true)||!Hold(EStage::Planted)||!Hold(EStage::Burning))return false;
        // Running after ignition is legitimate: detection may call the
        // authored reinforcement wave, but the ordinary hero must escape it.
        AllowDetection=true;
        for(FVector2D P:{FVector2D(-1000,548),FVector2D(-1000,3000),FVector2D(-1600,3000)})if(!Move(P,false))return false;
        Step=TEXT("wait in blast cover");
        if(!Check(W.Campaign()->TerminalSafe()&&W.Campaign()->TaskProgress().Done==2,TEXT("The hero reaches real safe cover before detonation")))return false;
        const int SafeMs=W.Campaign()->TerminalState().FuseAgeMs;
        for(int I=0;I<1300&&W.Campaign()->IsTerminalCharge();++I)if(!Tick())return false;
        W.Test.AddInfo(FString::Printf(TEXT("Encounter completed in %.3fs, safe_fuse_ms=%d health=%.2f/%.2f peak_meter=%d detected=%d by=%s max_enemies=%d"),
            Seconds,SafeMs,W.Hero()->Health,StartingHealth,PeakMeter,Detected,*Detector,MostEnemies));
        return Check(W.Campaign()->ActiveBeat()==10&&W.Mode()->Arena()->IsTerminalDestroyed(),TEXT("Actual detonation advances to blackout with the normal hero alive"));
    }
};
}

IMPLEMENT_COMPLEX_AUTOMATION_TEST(FSoraNoticeEncounterTest,"SoraArena.Campaign.NoticeSquare.Encounter",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
void FSoraNoticeEncounterTest::GetTests(TArray<FString>& Names,TArray<FString>& Commands)const
{
    for(const TCHAR* Route:{TEXT("NorthAlley"),TEXT("Roof")})for(const TCHAR* Input:{TEXT("Keyboard"),TEXT("Controller")})
    {const FString Name=FString(Route)+TEXT(".")+Input;Names.Add(Name);Commands.Add(Name);}
}
bool FSoraNoticeEncounterTest::RunTest(const FString& Parameters)
{
    SoraNoticeEncounterTest::FRoute Route(*this,TEXT("NoticeEncounter")+Parameters,Parameters.EndsWith(TEXT("Controller")));
    if(!Route.Start())return false;
    if(Parameters.StartsWith(TEXT("Roof"))&&!Route.Roof())return false;
    return Route.Charge()&&!HasAnyErrors();
}
#endif
