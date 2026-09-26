#include "SoraGameMode.h"
#include "ArenaKernelSubsystem.h"
#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraFrontEnd.h"
#include "SoraHUD.h"
#include "SoraPlayerCharacter.h"
#include "SoraPracticeDirector.h"
#include "SoraPracticeLobby.h"
#include "SoraSettings.h"
#include "SoraText.h"
#include "SoraWorldBuilder.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Kismet/KismetSystemLibrary.h"
#include "TimerManager.h"

namespace
{
FText PreparingText() { return NSLOCTEXT("SoraArena.HUD", "Objective.Preparing", "舞台を準備しています……"); }
}

ASoraGameMode::ASoraGameMode()
{
    PrimaryActorTick.bCanEverTick=true;
    DefaultPawnClass=ASoraPlayerCharacter::StaticClass(); HUDClass=ASoraHUD::StaticClass();
    CampaignDirector=CreateDefaultSubobject<USoraCampaignDirector>(TEXT("CampaignDirector"));
    PracticeDirector=CreateDefaultSubobject<USoraPracticeDirector>(TEXT("PracticeDirector"));
    FrontEndState=CreateDefaultSubobject<USoraFrontEnd>(TEXT("FrontEnd"));
    SettingsState=CreateDefaultSubobject<USoraSettings>(TEXT("Settings"));
}
void ASoraGameMode::BeginPlay()
{
    Super::BeginPlay();
    // The game opens on the title screen. ASoraHUD's Slate front end takes
    // keyboard and pad focus while any screen is open and returns it to play.
    FrontEndState->ShowTitle();
    const bool bCatalog=FSoraCatalog::Get().Load();
    const bool bCampaignSave=bCatalog&&CampaignDirector->LoadSave();
    // The settings load after the campaign save, which still carries an old
    // copy of the subtitle switch; the settings own it.
    SettingsState->Load(SettingsSlotName,bAttachSettingsToEngine);
    if(!bCatalog)
    {
        Notice=FSoraCatalog::Get().Error;
        // The loader's reason is developer English, so it follows the English line.
        const SoraText::FLine Missing=SoraText::Line(NSLOCTEXT("SoraArena.Menu","Banner.ContentMissing","ゲームの内容を読み込めない。インストールを確かめてほしい。"));
        FrontEndState->ShowMain(Missing.Japanese,Missing.English+TEXT(" ")+Notice);
        return;
    }
    if(!bCampaignSave) return;
    WorldBuilder=GetWorld()->SpawnActor<ASoraWorldBuilder>();
    GetWorldTimerManager().SetTimerForNextTick(this,&ASoraGameMode::ResetRound);
}
UArenaKernelSubsystem* ASoraGameMode::Kernel() const
{
    return GetGameInstance()?GetGameInstance()->GetSubsystem<UArenaKernelSubsystem>():nullptr;
}
ASoraPlayerCharacter* ASoraGameMode::Hero() const
{
    return Cast<ASoraPlayerCharacter>(UGameplayStatics::GetPlayerPawn(this,0));
}
void ASoraGameMode::ResetRound()
{
    if(bDeterministicPractice) { PracticeDirector->Reset(); return; }
    PracticeDirector->Clear();
    if(!WorldBuilder||!FSoraCatalog::Get().IsReady()) return;
    CampaignDirector->ResetRound();
    bRoundPrepared=true; SyncMenuPause();
}
void ASoraGameMode::Tick(float Dt)
{
    Super::Tick(Dt); if(bMenu||bDefeated||bChapterComplete) { PracticeDirector->ResetClock(); return; }
    // The chapter title card holds the round timer, so dialogue starts after it.
    if(TitleCardTime>0.f) { TitleCardTime=FMath::Max(0.f,TitleCardTime-Dt); return; }
    if(bDeterministicPractice) { PracticeDirector->Step(Dt); return; }
    RoundTime+=Dt; NoticeTime=FMath::Max(0.f,NoticeTime-Dt);
}
void ASoraGameMode::BeginRound()
{
    if(!FSoraCatalog::Get().IsReady()) return;
    // Enter on the chapter title card or a cinematic skips it; the campaign
    // director starts the next beat at once.
    if(InputState()==SoraInput::Card) { CampaignDirector->SkipCinematic(); return; }
    if(bDeterministicPractice)
    {
        auto* K=Kernel();
        if(!K||!K->PracticeActive()||bChapterComplete||!K->PracticeError.IsEmpty()) if(!PracticeDirector->Reset()) return;
        SetMenuOpen(false); return;
    }
    if(bChapterComplete)
    {
        // Liberating the campaign returns to the menu instead of a new round.
        if(!CampaignDirector->AdvanceChapter()) return;
        ResetRound();
    }
    else if(bDefeated) ResetRound();
    if(bMenu&&bCampaign) CampaignDirector->SuspendDojo(false);
    SetMenuOpen(false);
}
void ASoraGameMode::OpenPauseMenu()
{
    if(bMenu) return;
    FrontEndState->ShowPause();
    SetMenuOpen(true);
    if(bCampaign) CampaignDirector->SuspendDojo(true);
}
void ASoraGameMode::ResumePlay()
{
    if(!bMenu) return;
    SetMenuOpen(false);
    if(bCampaign) CampaignDirector->SuspendDojo(false);
}
void ASoraGameMode::SetMenuOpen(bool bOpen)
{
    bMenu=bOpen;
    if(bOpen)
    {
        // Menu time is discarded; practice resumes on a fresh 60 Hz step.
        PracticeDirector->ResetClock();
        // A director that stops play (liberation, a refused practice step)
        // lands on the main menu with its notice.
        if(!FrontEndState->IsOpen()) FrontEndState->ShowMain(Notice,NoticeEnglish);
    }
    else FrontEndState->Hide();
    SyncMenuPause();
}
void ASoraGameMode::SyncMenuPause()
{
    // The open menu pauses the world: actors, timers and the practice clock
    // stop, while the HUD and the Slate front end still draw and take input.
    // The first round is built by a next-tick timer, so pausing waits for it.
    APlayerController* Controller=UGameplayStatics::GetPlayerController(this,0);
    if(!bRoundPrepared||!Controller) return;
    if(bMenu&&!IsPaused()) SetPause(Controller);
    else if(!bMenu&&IsPaused()) ClearPause();
}
SoraInput::EState ASoraGameMode::InputState() const
{
    if(bMenu) return SoraInput::Menu;
    if(bDefeated||bChapterComplete) return SoraInput::Result;
    return TitleCardTime>0.f?SoraInput::Card:SoraInput::Play;
}
const FSoraChapter* ASoraGameMode::TitleCardChapter() const
{
    return bCampaign&&InputState()==SoraInput::Card&&FSoraCatalog::Get().IsReady()
        ?&FSoraCatalog::Get().Chapter(CampaignDirector->ChapterId):nullptr;
}
bool ASoraGameMode::CampaignHasProgress() const { return CampaignDirector->HasProgress(); }
bool ASoraGameMode::CanContinueCampaign() const
{
    // A liberated campaign has no chapter left to continue; chapter select
    // replays it.
    return FSoraCatalog::Get().IsReady()&&CampaignDirector->HasSave()&&!CampaignDirector->bCampaignComplete&&CampaignHasProgress();
}
bool ASoraGameMode::ContinueCampaign()
{
    if(!bMenu||!WorldBuilder||!CanContinueCampaign()) return false;
    if(bDeterministicPractice||!bCampaign)
    {
        bDeterministicPractice=false; bCampaign=true;
        CampaignDirector->ResumeSavedChapter();
        ResetRound();
    }
    BeginRound();
    return !bMenu;
}
void ASoraGameMode::StartNewCampaign()
{
    if(!bMenu||!WorldBuilder||!FSoraCatalog::Get().IsReady()) return;
    // A fresh save already has the dojo prepared behind the title. Anything
    // else is erased (the front end confirmed it) and the dojo rebuilt.
    if(CampaignHasProgress()||bDeterministicPractice||!bCampaign||CampaignDirector->ChapterId!=0)
    {
        bDeterministicPractice=false; bCampaign=true;
        CampaignDirector->StartOver();
        MapId=FSoraCatalog::Get().Chapter(0).Map;
        ResetRound();
    }
    BeginRound();
}
int32 ASoraGameMode::HighestChapterReached() const { return CampaignDirector->HighestChapter(); }
bool ASoraGameMode::StartChapter(int32 Chapter)
{
    if(!bMenu||!WorldBuilder||!FSoraCatalog::Get().IsReady()) return false;
    bDeterministicPractice=false; bCampaign=true;
    if(!CampaignDirector->SelectChapter(Chapter)) return false;
    ResetRound();
    BeginRound();
    return !bMenu;
}
bool ASoraGameMode::StartPracticeFromLobby(const FSoraPracticeLobbySelection& Selection)
{
    if(!bMenu) return false;
    FText Why;
    if(!WorldBuilder||!SoraPracticeLobby::IsValid(Selection,&Why))
    {
        const SoraText::FLine Refused=SoraText::Format(NSLOCTEXT("SoraArena.Menu","Notice.PracticeRefused","この設定では稽古を始められません（{Reason}）。"),
            {{TEXT("Reason"),SoraText::Line(WorldBuilder?Why:NSLOCTEXT("SoraArena.Menu","Notice.ArenaNotBuilt","舞台がまだ組まれていない"))}});
        Notice=Refused.Japanese; NoticeEnglish=Refused.English;
        return false;
    }
    // The lobby's six fields are the practice config's, one for one.
    FSoraPracticeConfig Config;
    Config.Mode=Selection.Mode; Config.PlayerCount=Selection.PlayerCount; Config.MapId=Selection.MapId;
    Config.ClassId=Selection.ClassId; Config.SpecialWeaponId=Selection.SpecialWeaponId; Config.Difficulty=Selection.Difficulty;
    if(!PracticeDirector->StartPractice(Config))
    {
        // A choice the kernel refuses changes nothing. A match that failed
        // to build has already switched to practice: the saved chapter
        // returns behind the lobby. Either way the lobby shows the reason.
        if(bDeterministicPractice&&!(Kernel()&&Kernel()->PracticeActive()))
        {
            const FString Reason=Notice,ReasonEnglish=NoticeEnglish;
            bDeterministicPractice=false; bCampaign=true;
            CampaignDirector->ResumeSavedChapter();
            ResetRound();
            Notice=Reason; NoticeEnglish=ReasonEnglish;
        }
        return false;
    }
    CampaignDirector->SaveProgress();
    SetMenuOpen(false);
    return true;
}
bool ASoraGameMode::RestartRound()
{
    if(!bMenu||!WorldBuilder) return false;
    if(bDeterministicPractice) { if(!PracticeDirector->Reset()) return false; }
    else ResetRound();
    SetMenuOpen(false);
    return true;
}
void ASoraGameMode::ReturnToTitle()
{
    if(!bMenu) return;
    if(bDeterministicPractice||!bCampaign)
    {
        bDeterministicPractice=false; bCampaign=true;
        CampaignDirector->ResumeSavedChapter();
    }
    // Continue resumes from the last checkpoint, as after a restart.
    ResetRound();
    FrontEndState->ShowMain();
}
void ASoraGameMode::QuitGame()
{
    UKismetSystemLibrary::QuitGame(this,UGameplayStatics::GetPlayerController(this,0),EQuitPreference::Quit,false);
}
void ASoraGameMode::ToggleSubtitles() { SettingsState->SetEnglishSubtitles(!bEnglishSubtitles); }
void ASoraGameMode::Interact(ASoraPlayerCharacter* Player)
{
    if(bDeterministicPractice) return;
    if(!WorldBuilder||!Player) return;
    CampaignDirector->Interact(*Player);
}
void ASoraGameMode::DeterministicPractice()
{
    if(!bMenu) return;
    if(!WorldBuilder||!FSoraCatalog::Get().IsReady())
    {
        const SoraText::FLine Unready=SoraText::Line(NSLOCTEXT("SoraArena.Menu","Notice.PracticeUnready","稽古の舞台またはコンテンツを準備できません。"));
        Notice=Unready.Japanese; NoticeEnglish=Unready.English; return;
    }
    bDeterministicPractice=true; bCampaign=false; PracticeDirector->Reset();
}
FString ASoraGameMode::ObjectiveText() const
{
    if(bDeterministicPractice) return PracticeDirector->ObjectiveText();
    if(!WorldBuilder) return SoraText::Line(PreparingText()).Japanese;
    return CampaignDirector->ObjectiveText();
}
FString ASoraGameMode::ObjectiveTextEnglish() const
{
    if(bDeterministicPractice) return PracticeDirector->ObjectiveTextEnglish();
    if(!WorldBuilder) return SoraText::Line(PreparingText()).English;
    return CampaignDirector->ObjectiveTextEnglish();
}
