#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraCatalogDojo.h"
#include "SoraCatalogJson.h"
#include "SoraDojoAutomation.h"
#include "SoraFieldcraftTestWorld.h"
#include "SoraSettings.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraPupilTimingTest,"SoraArena.Campaign.PupilTiming",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraPupilTimingTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using SoraFieldcraftAutomation::FBeatWorld;
    using namespace SoraDojoAutomation;
    if(!TestTrue(TEXT("Catalog loads with both authored pupil patterns"),FSoraCatalog::Get().Load())) return false;
    const auto& Chapter=FSoraCatalog::Get().Chapter(0);
    TestEqual(TEXT("Men loads the authored 550 ms windup"),Chapter.Beats[2].PupilTiming.WindupMs,550);
    TestEqual(TEXT("Men's 1.45 s repeat is an onset interval"),Chapter.Beats[2].PupilTiming.RepeatMs,1450);
    TestEqual(TEXT("Men does not add another post-contact repeat"),Chapter.Beats[2].PupilTiming.RecoveryMs,0);
    TestEqual(TEXT("Kesa loads the authored 600 ms windup"),Chapter.Beats[3].PupilTiming.WindupMs,600);
    TestEqual(TEXT("Kesa has the authored 1 s recovery"),Chapter.Beats[3].PupilTiming.RecoveryMs,1000);
    TestEqual(TEXT("Kesa has no onset-repeat override"),Chapter.Beats[3].PupilTiming.RepeatMs,0);

    // Exercise the real loader without changing any file or singleton state.
    FString Json;
    TSharedPtr<FJsonObject> Root;
    if(!TestTrue(TEXT("Authored chapter JSON loads"),FFileHelper::LoadFileToString(Json,
        *(FPaths::ProjectContentDir()/TEXT("Data/campaign/chapter_01.json")))&&
        FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Root))) return false;
    const auto* Beats=SoraCatalogJson::Rows(*Root,TEXT("beats"));
    if(!TestNotNull(TEXT("The chapter has beat rows"),Beats)) return false;
    auto Men=(*Beats)[2]->AsObject(),Kesa=(*Beats)[3]->AsObject();
    auto MenPattern=SoraCatalogJson::Child(*SoraCatalogJson::Child(*Men,TEXT("ext")),TEXT("opponent_pattern"));
    auto KesaPattern=SoraCatalogJson::Child(*SoraCatalogJson::Child(*Kesa,TEXT("ext")),TEXT("opponent_pattern"));
    FSoraBeat Probe=Chapter.Beats[2];
    MenPattern->SetNumberField(TEXT("repeat_s"),.6);
    TestFalse(TEXT("A cadence shorter than the Easy windup is rejected"),SoraCatalogDojo::Read(*Men,Probe));
    MenPattern->SetNumberField(TEXT("repeat_s"),1.45);
    MenPattern->SetNumberField(TEXT("recovery_ms"),1450);
    TestFalse(TEXT("Conflicting repeat and recovery are rejected"),SoraCatalogDojo::Read(*Men,Probe));
    MenPattern->RemoveField(TEXT("recovery_ms"));
    TestTrue(TEXT("The unmodified men pattern is valid"),SoraCatalogDojo::Read(*Men,Probe));
    Probe=Chapter.Beats[3];
    KesaPattern->SetNumberField(TEXT("recovery_ms"),-1);
    TestFalse(TEXT("A negative kesa recovery is rejected"),SoraCatalogDojo::Read(*Kesa,Probe));
    KesaPattern->SetNumberField(TEXT("recovery_ms"),1000);
    KesaPattern->SetStringField(TEXT("id"),TEXT("pupil_men"));
    TestFalse(TEXT("A swapped lesson pattern is rejected"),SoraCatalogDojo::Read(*Kesa,Probe));
    KesaPattern->SetStringField(TEXT("id"),TEXT("pupil_kesa"));
    for(const int32 BeatIndex:{2,3})
    {
        const auto Object=(*Beats)[BeatIndex]->AsObject();
        const auto Pattern=SoraCatalogJson::Child(*SoraCatalogJson::Child(*Object,TEXT("ext")),TEXT("opponent_pattern"));
        const TArray<FString> Fields=BeatIndex==2
            ? TArray<FString>{TEXT("windup_ms"),TEXT("repeat_s"),TEXT("stagger_on_awase_s")}
            : TArray<FString>{TEXT("windup_ms"),TEXT("recovery_ms")};
        FSoraBeat TypedProbe=Chapter.Beats[BeatIndex];
        for(const FString& Field:Fields)
        {
            const auto Original=Pattern->TryGetField(Field);
            double Number=0;
            if(!TestTrue(TEXT("The original timing field is numeric"),Original&&Original->TryGetNumber(Number))) return false;
            Pattern->SetBoolField(Field,true);
            TestFalse(FString::Printf(TEXT("Boolean %s is not a timing number"),*Field),SoraCatalogDojo::Read(*Object,TypedProbe));
            Pattern->SetStringField(Field,FString::SanitizeFloat(Number));
            TestFalse(FString::Printf(TEXT("Numeric string %s is not a timing number"),*Field),SoraCatalogDojo::Read(*Object,TypedProbe));
            Pattern->SetField(Field,MakeShared<FJsonValueNull>());
            TestFalse(FString::Printf(TEXT("Null %s is not a timing number"),*Field),SoraCatalogDojo::Read(*Object,TypedProbe));
            Pattern->SetField(Field,Original);
            TestTrue(TEXT("Restoring the numeric field restores valid timing"),SoraCatalogDojo::Read(*Object,TypedProbe));
        }
    }
    const auto Maai=(*Beats)[1]->AsObject();
    const auto MaaiExt=SoraCatalogJson::Child(*Maai,TEXT("ext"));
    FSoraBeat MaaiProbe=Chapter.Beats[1];
    const TArray<TSharedPtr<FJsonValue>> WrongPatterns={MakeShared<FJsonValueBoolean>(false),
        MakeShared<FJsonValueNull>(),MakeShared<FJsonValueString>(TEXT("pupil_men"))};
    for(const auto& WrongPattern:WrongPatterns)
    {
        MaaiExt->SetField(TEXT("opponent_pattern"),WrongPattern);
        TestFalse(TEXT("A malformed pattern is not silently absent outside attack lessons"),SoraCatalogDojo::Read(*Maai,MaaiProbe));
    }
    MaaiExt->RemoveField(TEXT("opponent_pattern"));
    TestTrue(TEXT("Maai remains valid without an attack pattern"),SoraCatalogDojo::Read(*Maai,MaaiProbe));

    constexpr int32 MenWindups[]={715,550,468},KesaWindups[]={780,600,510};
    constexpr float FrameSeconds=1.f/60.f,Tolerance=.035f;
    for(const int32 Beat:{2,3}) for(int32 Difficulty=0;Difficulty<3;++Difficulty)
    {
        FBeatWorld W(*this,TEXT("PupilTiming"),0,Beat);
        if(!W.Start()) return false;
        W.Mode()->Settings()->SetCampaignDifficulty(static_cast<SoraAccessibility::EDifficulty>(Difficulty));
        auto* Events=USoraGameEvents::Get(W.World->GetTestWorld());
        if(!TestNotNull(TEXT("The ordinary combat event bus exists"),Events)) return false;
        TWeakObjectPtr<ASoraEnemy> Enemy;
        TArray<float> Starts,Windups,Contacts,Telegraphs;
        TArray<int32> GuardHolds;
        float ParriedAt=-1.f;
        const auto Committed=Events->OnMeleeCommitted.AddLambda([&](const FSoraMeleeCommittedEvent& E) {
            auto* P=Cast<ASoraEnemy>(E.Attacker);
            if(!P||!P->IsDojoPupil()) return;
            Enemy=P;
            Starts.Add(W.World->GetTestWorld()->GetTimeSeconds()); Windups.Add(E.WindupSeconds);
            // The visible telegraph must live for the same scaled windup the
            // actual contact observes, not the old hard-coded 550 ms.
            const FVector Center=P->GetActorLocation()+FVector(0,0,50)+E.Direction*100.f;
            float Life=-1.f;
            for(TActorIterator<AActor> It(W.World->GetTestWorld());It;++It)
                if(It->GetRootComponent()&&It->GetRootComponent()->GetName().StartsWith(TEXT("Tracer"))&&
                    FVector::Dist(It->GetActorLocation(),Center)<1.f)
                    Life=FMath::Max(Life,It->GetLifeSpan());
            Telegraphs.Add(Life);
        });
        const auto Resolved=Events->OnStrikeResolved.AddLambda([&](const FSoraStrikeResolvedEvent& E) {
            if(E.Attacker==Enemy.Get())
            {
                TestTrue(TEXT("The timed strike actually contacts the hero"),E.Target==W.Hero());
                Contacts.Add(W.World->GetTestWorld()->GetTimeSeconds());
            }
        });
        const auto Guarded=Events->OnGuarded.AddLambda([&](const FSoraDefenseEvent& E) {
            if(E.bDojo&&E.Attacker==Enemy.Get()&&E.Defender==W.Hero())
            {
                GuardHolds.Add(E.HeldMs);
                UE_LOG(LogTemp,Display,TEXT("Pupil actual guard beat=%d difficulty=%d held_ms=%d"),Beat,Difficulty,E.HeldMs);
            }
        });
        const auto Parried=Events->OnParried.AddLambda([&](const FSoraDefenseEvent& E) {
            if(E.bDojo&&E.Attacker==Enemy.Get()&&E.Defender==W.Hero())
            {
                TestTrue(TEXT("The real awase remains within its authored window"),E.HeldMs>=0&&E.HeldMs<=260);
                ParriedAt=W.World->GetTestWorld()->GetTimeSeconds();
                UE_LOG(LogTemp,Display,TEXT("Pupil actual awase beat=%d difficulty=%d held_ms=%d at=%.6f"),Beat,Difficulty,E.HeldMs,ParriedAt);
            }
        });
        ON_SCOPE_EXIT {
            Events->OnMeleeCommitted.Remove(Committed); Events->OnStrikeResolved.Remove(Resolved);
            Events->OnGuarded.Remove(Guarded); Events->OnParried.Remove(Parried);
        };
        bool Raised=false,Released=false,Met=false;
        for(int32 Frame=0;Frame<1800&&Starts.Num()<4;++Frame)
        {
            auto* P=Pupil(*W.World);
            if(P)
            {
                Face(*W.World,*P);
                const bool Close=FVector::Dist2D(P->GetActorLocation(),W.Hero()->GetActorLocation())<=170.f;
                if(!W.World->InjectKey(EKeys::W,Close||P->IsPupilWindup()?IE_Released:IE_Pressed)) return false;
            }
            if(!Raised&&Starts.Num()>0)
            {
                if(!W.World->InjectKey(EKeys::LeftControl,IE_Pressed)) return false;
                Raised=true;
            }
            if(!Released&&Contacts.Num()>=2)
            {
                if(!W.World->InjectKey(EKeys::LeftControl,IE_Released)) return false;
                Released=true;
            }
            if(Released&&!Met&&Starts.Num()==3&&
                Starts[2]+Windups[2]-W.World->GetTestWorld()->GetTimeSeconds()<=.16f)
            {
                if(!W.World->InjectKey(EKeys::LeftControl,IE_Pressed)) return false;
                Met=true;
            }
            if(!W.Tick(1,FrameSeconds)) return false;
        }
        if(!W.World->InjectKey(EKeys::W,IE_Released)||!W.World->InjectKey(EKeys::LeftControl,IE_Released)) return false;
        UE_LOG(LogTemp,Display,TEXT("Pupil timing beat=%d difficulty=%d starts=%d contacts=%d guards=%d parry=%.6f hero=%s pupil=%s input=%d"),
            Beat,Difficulty,Starts.Num(),Contacts.Num(),GuardHolds.Num(),ParriedAt,*W.Hero()->GetActorLocation().ToString(),
            Enemy.IsValid()?*Enemy->GetActorLocation().ToString():TEXT("none"),int32(W.Mode()->InputState()));
        if(!TestEqual(TEXT("Ordinary ticks produce four real pupil windups"),Starts.Num(),4)||
            !TestEqual(TEXT("The first three real strikes resolve"),Contacts.Num(),3)||
            !TestEqual(TEXT("Two early mapped guards actually block contact"),GuardHolds.Num(),2)||
            !TestTrue(TEXT("The third mapped guard produces an actual awase"),ParriedAt>=0.f)) return false;
        TestTrue(TEXT("Even Hard leaves at least 350 ms for the early guard lesson"),GuardHolds[0]>=350);
        const float ExpectedWindup=(Beat==2?MenWindups[Difficulty]:KesaWindups[Difficulty])/1000.f;
        for(int32 Strike=0;Strike<3;++Strike)
        {
            const float Actual=Contacts[Strike]-Starts[Strike];
            UE_LOG(LogTemp,Display,TEXT("Pupil measured beat=%d difficulty=%d strike=%d start=%.6f contact=%.6f windup=%.6f telegraph=%.6f"),
                Beat,Difficulty,Strike,Starts[Strike],Contacts[Strike],Actual,Telegraphs[Strike]);
            TestTrue(TEXT("The commitment announces the authored scaled windup"),FMath::IsNearlyEqual(Windups[Strike],ExpectedWindup,.0001f));
            TestTrue(TEXT("The real telegraph retains that complete windup"),FMath::IsNearlyEqual(Telegraphs[Strike],ExpectedWindup,Tolerance));
            TestTrue(TEXT("Contact never precedes the windup and resolves on the next normal tick"),Actual+.0001f>=ExpectedWindup&&Actual<=ExpectedWindup+Tolerance);
        }
        for(int32 Strike=1;Strike<3;++Strike)
        {
            const float Interval=Beat==2?Starts[Strike]-Starts[Strike-1]:Starts[Strike]-Contacts[Strike-1];
            const float Expected=Beat==2?1.45f:1.f;
            TestTrue(TEXT("Unparried attacks preserve authored onset or recovery cadence"),Interval+.0001f>=Expected&&Interval<=Expected+Tolerance);
        }
        TestTrue(TEXT("A real 1.2 s stagger defers even an expired cadence"),Starts[3]>=ParriedAt+1.2f-.0001f&&Starts[3]<=ParriedAt+1.2f+Tolerance);
        TestEqual(TEXT("Timing observations alone award no points"),W.Campaign()->TaskProgress().Done,0);
    }
    return !HasAnyErrors();
}
#endif
