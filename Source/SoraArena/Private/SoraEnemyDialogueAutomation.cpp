#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraEnemy.h"
#include "SoraGameEvents.h"
#include "SoraCatalogDialogue.h"

IMPLEMENT_COMPLEX_AUTOMATION_TEST(FSoraEnemyDialogueSourceTest,"SoraArena.Campaign.Dialogue.EnemySources",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
void FSoraEnemyDialogueSourceTest::GetTests(TArray<FString>& Names,TArray<FString>& Commands)const
{
    for(const TCHAR* Source:{TEXT("marksman"),TEXT("bound_conscript"),TEXT("enforcer_rifle"),TEXT("blade_retainer"),TEXT("drone")})
    {Names.Add(Source);Commands.Add(Source);}
}
bool FSoraEnemyDialogueSourceTest::RunTest(const FString& Parameters)
{
    using namespace SoraFieldcraftAutomation;
    if(!FSoraCatalog::Get().Load())return false;
    FBeatWorld W(*this,*(TEXT("EnemyDialogue")+Parameters),2,9);
    if(!W.Start())return false;
    for(int I=0;I<120&&(!W.Mode()->IsPlaying()||W.Campaign()->LinesQueued());++I)if(!W.Tick(1,.1f))return false;
    if(!TestTrue(TEXT("The real checkpoint's opening radio finishes with control available"),W.Mode()->IsPlaying()&&W.Campaign()->LinesQueued()==0))return false;
    ASoraEnemy* Guard=nullptr;
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
        if(It->ArchetypeId()==FName(*Parameters)){Guard=*It;break;}
    if(!TestNotNull(TEXT("The source is an actual authored encounter guard"),Guard))return false;
    // Directed routing test through the production bus. It does not claim
    // that this manually emitted state was produced by a perception change.
    FSoraEnemyCueEvent Cue;Cue.Enemy=Guard;Cue.Archetype=Guard->ArchetypeId();
    Cue.Cue=ESoraEnemyCue::AlertState;Cue.Detail=TEXT("suspicious");
    USoraGameEvents::Get(Guard)->OnEnemyCue.Broadcast(Cue);
    const auto Rows=W.Campaign()->QueuedSubtitles();
    for(const auto& Row:Rows)AddInfo(TEXT("Queued guard line: ")+Row.LineId);
    const FString Expected=Parameters==TEXT("marksman")?TEXT("ch03.b10.marksman.005"):
        Parameters==TEXT("bound_conscript")?TEXT("ch03.b03.conscript.004"):
        Parameters==TEXT("drone")?TEXT("ch03.b02.drone.005"):TEXT("ch03.b03.enforcer.007");
    return TestEqual(TEXT("One reacting guard queues only its authored source-specific line"),Rows.Num(),1)&&
        TestEqual(TEXT("The queued line belongs to the reacting archetype"),Rows[0].LineId,Expected)&&
        TestTrue(TEXT("A bark alone neither detects the hero nor captures movement"),!W.Stealth()->IsDetected()&&W.Mode()->IsPlaying());
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraEnemyDialogueMetadataTest,"SoraArena.Campaign.Dialogue.EnemySourceMetadata",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraEnemyDialogueMetadataTest::RunTest(const FString& Parameters)
{
    if(!FSoraCatalog::Get().Load())return false;
    const auto& Chapter=FSoraCatalog::Get().Chapter(2);
    const auto* Trigger=Chapter.Triggers.FindByPredicate([&](const FSoraDialogueTrigger& T)
        {return T.Beat==9&&T.Lines.Num()==1&&Chapter.Dialogue[T.Lines[0]].Id==TEXT("ch03.b10.marksman.005");});
    if(!TestTrue(TEXT("The real chapter retains its marksman source restriction"),Trigger&&Trigger->EnemySources==TArray<FName>{TEXT("marksman")}))return false;
    for(const TCHAR* Sources:{TEXT("null"),TEXT("[]"),TEXT("\"marksman\""),TEXT("[4]"),TEXT("[{}]"),
        TEXT("[\"marksman\",\"marksman\"]"),TEXT("[\"enforcer_musket\"]"),TEXT("[\"Marksman\"]")})
    {
        TSharedPtr<FJsonObject> Row;TArray<FName> Parsed;
        const FString Json=FString::Printf(TEXT("{\"ext\":{\"source\":%s}}"),Sources);
        if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Row))return false;
        TestFalse(*FString::Printf(TEXT("Malformed/unknown source fails closed: %s"),Sources),SoraCatalogDialogue::ReadSources(*Row,Parsed));
    }
    TSharedPtr<FJsonObject> Generic;TArray<FName> Parsed;
    FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(FString(TEXT("{\"ext\":{}}"))),Generic);
    return TestTrue(TEXT("An unrestricted authored row still loads"),Generic&&SoraCatalogDialogue::ReadSources(*Generic,Parsed)&&Parsed.IsEmpty())&&!HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraEnemyDialogueContextTest,"SoraArena.Campaign.Dialogue.EnemySourceContext",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraEnemyDialogueContextTest::RunTest(const FString& Parameters)
{
    if(!FSoraCatalog::Get().Load())return false;
    auto& Chapter=FSoraCatalog::Get().Chapters[2];
    // Temporary trigger rows exercise scheduling/once semantics; restore the
    // shared catalog after the isolated world is destroyed, even on failure.
    struct FRestore { FSoraChapter& Chapter;TArray<FSoraDialogueTrigger> Triggers;
        ~FRestore(){Chapter.Triggers=MoveTemp(Triggers);} } Restore{Chapter,Chapter.Triggers};
    SoraFieldcraftAutomation::FBeatWorld W(*this,TEXT("EnemyDialogueContext"),2,9);
    if(!W.Start())return false;
    const auto Drain=[&]()
    {
        for(int I=0;I<160&&(!W.Mode()->IsPlaying()||W.Campaign()->LinesQueued());++I)if(!W.Tick(1,.1f))return false;
        return TestTrue(TEXT("The current dialogue drains without capturing play"),W.Mode()->IsPlaying()&&W.Campaign()->LinesQueued()==0);
    };
    if(!Drain())return false;
    const auto Emit=[&](FName Source,ESoraEnemyCue Kind,FName Detail)
    {
        ASoraEnemy* Guard=nullptr;
        for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)if(It->ArchetypeId()==Source){Guard=*It;break;}
        if(!TestNotNull(TEXT("The routed cue retains its actual encounter actor"),Guard))return false;
        FSoraEnemyCueEvent Cue;Cue.Enemy=Guard;Cue.Archetype=Source;Cue.Cue=Kind;Cue.Detail=Detail;
        USoraGameEvents::Get(Guard)->OnEnemyCue.Broadcast(Cue);return true;
    };
    const auto One=[&](const TCHAR* Id)
    {
        const auto Rows=W.Campaign()->QueuedSubtitles();
        return TestEqual(TEXT("Exactly one source-qualified line is queued"),Rows.Num(),1)&&
            TestEqual(TEXT("The queued line has the correct speaker/source contract"),Rows[0].LineId,FString(Id));
    };
    W.Campaign()->FireDialogueTrigger(TEXT("alert_state:suspicious"));
    if(!TestEqual(TEXT("An unsourced mission event cannot impersonate a guard"),W.Campaign()->LinesQueued(),0))return false;
    if(!Emit(TEXT("marksman"),ESoraEnemyCue::AlertState,TEXT("combat"))||!One(TEXT("ch03.b10.marksman.006")))return false;
    W.Campaign()->FireDialogueTrigger(TEXT("alert_state:alert"));
    if(!One(TEXT("ch03.b10.marksman.006"))||!Drain())return false;
    if(!Emit(TEXT("marksman"),ESoraEnemyCue::AlertState,TEXT("unaware"))||
       !Emit(TEXT("marksman"),ESoraEnemyCue::AlertState,TEXT("alert"))||
       !Emit(TEXT("marksman"),ESoraEnemyCue::AlertState,TEXT("combat"))||!One(TEXT("ch03.b10.marksman.006"))||!Drain())return false;
    if(!Emit(TEXT("enforcer_rifle"),ESoraEnemyCue::AlertState,TEXT("retreat"))||!One(TEXT("ch03.b08.enforcer.006"))||!Drain())return false;
    if(!Emit(TEXT("bound_conscript"),ESoraEnemyCue::AlertState,TEXT("search"))||
       !Emit(TEXT("bound_conscript"),ESoraEnemyCue::AlertState,TEXT("unaware"))||!One(TEXT("ch03.b03.conscript.006"))||!Drain())return false;
    const auto* Original=Chapter.Triggers.FindByPredicate([&](const FSoraDialogueTrigger& T)
        {return T.Beat==9&&T.Lines.Num()==1&&Chapter.Dialogue[T.Lines[0]].Id==TEXT("ch03.b10.marksman.005");});
    if(!TestNotNull(TEXT("The fixture reuses the actual source-qualified marksman row"),Original))return false;
    FSoraDialogueTrigger Once=*Original;Once.On=TEXT("ai:source_once_probe");Once.bRepeatable=false;
    Chapter.Triggers.Add(Once);
    if(!Emit(TEXT("drone"),ESoraEnemyCue::AttackWindup,TEXT("source_once_probe"))||
       !TestEqual(TEXT("The wrong source does not consume a one-shot row"),W.Campaign()->LinesQueued(),0)||
       !Emit(TEXT("marksman"),ESoraEnemyCue::AttackWindup,TEXT("source_once_probe"))||
       !Emit(TEXT("marksman"),ESoraEnemyCue::AttackWindup,TEXT("source_once_probe"))||!One(TEXT("ch03.b10.marksman.005"))||!Drain())return false;
    Once.On=TEXT("ai:source_delay_probe+0.2s");Chapter.Triggers.Add(Once);
    if(!Emit(TEXT("drone"),ESoraEnemyCue::AttackWindup,TEXT("source_delay_probe"))||!W.Tick(3,.1f)||
       !TestEqual(TEXT("A mismatched source cannot schedule the delayed bark"),W.Campaign()->LinesQueued(),0)||
       !Emit(TEXT("marksman"),ESoraEnemyCue::AttackWindup,TEXT("source_delay_probe"))||!W.Tick(3,.1f)||!One(TEXT("ch03.b10.marksman.005")))return false;
    return TestTrue(TEXT("Routing and aliases do not themselves trigger detection or a blocking scene"),!W.Stealth()->IsDetected()&&W.Mode()->IsPlaying());
}
#endif
