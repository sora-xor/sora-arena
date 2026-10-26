#include "SoraTerminalChargeAutomation.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraGameMode.h"
#include "SoraFieldcraftTestWorld.h"
#include "SoraEnemy.h"
#include "SoraWorldBuilder.h"
#include "SoraEquipmentComponent.h"
#include "SoraCatalogTerminalCharge.h"
#include "SoraCatalogJson.h"
#include "GameFramework/DamageType.h"

namespace SoraTerminalTest
{
using FWorld=SoraFieldcraftAutomation::FBeatWorld;
bool Ready(FWorld& W)
{
    if(!FSoraCatalog::Get().Load()||!W.Start())return false;
    for(int I=0;I<3000&&!W.Mode()->IsPlaying();++I)if(!W.Tick(1))return false;
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)It->Destroy();
    return W.Tick(4)&&W.Mode()->IsPlaying();
}
bool Panel(FWorld& W)
{W.Stand(FVector(-730,560,0));return W.Tick(8)&&W.Hero()->GetCharacterMovement()->IsMovingOnGround();}
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraTerminalEscapeTest,"SoraArena.Campaign.NoticeSquare.ChargeEscape",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraTerminalEscapeTest::RunTest(const FString&)
{
    SoraTerminalTest::FWorld W(*this,TEXT("TerminalEscape"),2,9);
    if(!SoraTerminalTest::Ready(W))return false;
    TestEqual(TEXT("The shared alley belongs to the active notice encounter"),W.Campaign()->HeroZone(),W.BeatData().Space.Zone);
    TestFalse(TEXT("Checkpoint begins with an intact terminal"),W.Mode()->Arena()->IsTerminalDestroyed());
    if(!TestTrue(TEXT("Walk to the actual service panel, hold both stages and escape through the real north passage"),
        SoraTerminalChargeAutomation::Escape(*W.World)))return false;
    TestTrue(TEXT("Only the real detonation advances to blackout"),W.Mode()->Arena()->IsTerminalDestroyed());
    W.Mode()->Campaign()->ResetRound();
    TestTrue(TEXT("The next saved checkpoint restores the destroyed terminal"),W.Mode()->Arena()->IsTerminalDestroyed());
    return !HasAnyErrors();
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraTerminalInterruptTest,"SoraArena.Campaign.NoticeSquare.ChargeInterruptions",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraTerminalInterruptTest::RunTest(const FString&)
{
    using namespace SoraTerminalChargeRules;
    SoraTerminalTest::FWorld W(*this,TEXT("TerminalInterrupt"),2,9);
    if(!SoraTerminalTest::Ready(W)||!SoraTerminalTest::Panel(W))return false;
    auto* C=W.Campaign();
    if(!W.Hold(EKeys::E,60))return false;
    TestTrue(TEXT("Releasing an unfinished plant loses all progress"),C->TerminalState().Stage==EStage::Empty&&!C->TerminalOccupiesHands()&&C->TerminalState().HeldMs==0);
    if(!W.World->InjectKey(EKeys::E,IE_Pressed)||!W.Tick(60))return false;
    W.Hero()->TakeDamage(1,FDamageEvent(),nullptr,nullptr);
    TestFalse(TEXT("Damage cancels work synchronously"),C->TerminalOccupiesHands());
    W.World->InjectKey(EKeys::E,IE_Released);
    if(!W.Tick(100)||!SoraTerminalChargeAutomation::HoldTo(*W.World,EStage::Planted))return false;
    // A hand cannot light the fuse through the terminal screen.
    W.Stand(FVector(-730,350,0));if(!W.Tick(6)||!W.Hold(EKeys::E,90))return false;
    TestTrue(TEXT("South screen cannot ignite the north fuse"),C->TerminalState().Stage==EStage::Planted);
    if(!SoraTerminalTest::Panel(W)||!SoraTerminalChargeAutomation::HoldTo(*W.World,EStage::Burning))return false;
    const int Before=C->TerminalState().FuseAgeMs;
    W.Mode()->SetMenuOpen(true);if(!W.Tick(100))return false;
    TestEqual(TEXT("Menu pauses the burning fuse"),C->TerminalState().FuseAgeMs,Before);
    W.Mode()->SetMenuOpen(false);if(!W.Tick(4))return false;
    TestTrue(TEXT("The same fuse resumes after closing the menu"),C->TerminalState().FuseAgeMs>Before);
    return !HasAnyErrors();
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraTerminalBlastTest,"SoraArena.Campaign.NoticeSquare.ChargeBlastRetry",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraTerminalBlastTest::RunTest(const FString&)
{
    using namespace SoraTerminalChargeRules;
    for(bool Lethal:{false,true})
    {
        SoraTerminalTest::FWorld W(*this,Lethal?TEXT("TerminalLethal"):TEXT("TerminalSurvive"),2,9);
        if(!SoraTerminalTest::Ready(W)||!SoraTerminalTest::Panel(W))return false;
        if(!SoraTerminalChargeAutomation::HoldTo(*W.World,EStage::Planted)||
           !SoraTerminalChargeAutomation::HoldTo(*W.World,EStage::Burning))return false;
        W.Hero()->Health=Lethal?1.f:10000.f;const float Before=W.Hero()->Health;
        for(int I=0;I<1400&&!W.Mode()->bDefeated;++I)if(!W.Tick(1))return false;
        TestTrue(TEXT("The actual eight-metre self blast damages the player"),W.Hero()->Health<Before);
        TestTrue(TEXT("Death or missing the escape deadline offers checkpoint retry"),W.Mode()->bDefeated);
        TestEqual(TEXT("A missed escape never starts blackout"),W.Campaign()->ActiveBeat(),9);
        W.Campaign()->ResetRound();
        TestTrue(TEXT("Retry discards charge progress"),W.Campaign()->TerminalState().Stage==EStage::Empty);
        TestFalse(TEXT("Retry restores the intact terminal"),W.Mode()->Arena()->IsTerminalDestroyed());
    }
    return !HasAnyErrors();
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraTerminalLoaderTest,"SoraArena.Campaign.NoticeSquare.ChargeLoader",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraTerminalLoaderTest::RunTest(const FString&)
{
    if(!FSoraCatalog::Get().Load())return false;
    for(int Case=0;Case<12;++Case)
    {
        TSharedPtr<FJsonObject> Data;if(!SoraCatalogJson::ReadJson(TEXT("campaign/chapter_03.json"),Data))return false;
        auto O=Data->GetObjectField(TEXT("space"))->GetArrayField(TEXT("beats"))[9]->AsObject();
        if(Case==1)O->RemoveField(TEXT("terminal_charge"));
        if(Case==2)O->SetBoolField(TEXT("terminal_charge"),true);
        if(Case==3)O->GetObjectField(TEXT("terminal_charge"))->SetArrayField(TEXT("fuse_ms"),{MakeShared<FJsonValueNumber>(19999)});
        if(Case==4)O->GetObjectField(TEXT("terminal_charge"))->SetArrayField(TEXT("holds_ms"),{MakeShared<FJsonValueNumber>(3999),MakeShared<FJsonValueNumber>(1000)});
        FSoraChapter Copy=FSoraCatalog::Get().Chapter(2);
        if(Case==5)Copy.Beats[9].Id=TEXT("ch03.b09");
        if(Case==6)Copy.Beats[9].Space.Objectives[2]=FVector2D::ZeroVector;
        if(Case==7)Copy.Beats[9].ObjectiveHoldMs[1]=0;
        if(Case==8)Copy.Beats[9].Task.Count=2;
        auto& Zone=Copy.Space.Zones[Copy.Beats[9].Space.Zone];
        if(Case==9)Zone.Place=TEXT("pl_ura_nagaya");
        if(Case==10)Zone.Rect.Max.X+=1;
        if(Case==11)Zone.Walls.AddDefaulted();
        TestEqual(TEXT("The native catalog binds the charge and real escape location"),
            SoraCatalogTerminalCharge::Read(*O,Copy.Beats[9],Copy.Space),Case==0);
    }
    return !HasAnyErrors();
}
#endif
