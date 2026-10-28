#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraEnemy.h"
#include "SoraGameEvents.h"

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
#endif
