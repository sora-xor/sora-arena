#include "SoraGameMode.h"
#include "ArenaKernelSubsystem.h"
#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraHUD.h"
#include "SoraPlayerCharacter.h"
#include "SoraPracticeDirector.h"
#include "SoraWorldBuilder.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "TimerManager.h"

ASoraGameMode::ASoraGameMode()
{
    PrimaryActorTick.bCanEverTick=true;
    DefaultPawnClass=ASoraPlayerCharacter::StaticClass(); HUDClass=ASoraHUD::StaticClass();
    CampaignDirector=CreateDefaultSubobject<USoraCampaignDirector>(TEXT("CampaignDirector"));
    PracticeDirector=CreateDefaultSubobject<USoraPracticeDirector>(TEXT("PracticeDirector"));
}
void ASoraGameMode::BeginPlay()
{
    Super::BeginPlay();
    if(!FSoraCatalog::Get().Load()) { Notice=FSoraCatalog::Get().Error; return; }
    if(!CampaignDirector->LoadSave()) return;
    WorldBuilder=GetWorld()->SpawnActor<ASoraWorldBuilder>();
    GetWorldTimerManager().SetTimerForNextTick(this,&ASoraGameMode::ResetRound);
    if(auto* PC=UGameplayStatics::GetPlayerController(this,0)) { PC->SetInputMode(FInputModeGameOnly()); PC->bShowMouseCursor=false; }
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
    bConfirmNewCampaign=false;
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
    // Enter on the chapter title card skips it; the round timer and dialogue
    // then begin from zero.
    if(InputState()==SoraInput::Card) { TitleCardTime=0.f; return; }
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
void ASoraGameMode::ToggleMenu()
{
    // Esc/Start withdraws a pending New Campaign prompt; the menu stays open.
    if(bMenu&&bConfirmNewCampaign) { bConfirmNewCampaign=false; return; }
    SetMenuOpen(!bMenu);
    if(bCampaign) CampaignDirector->SuspendDojo(bMenu);
}
void ASoraGameMode::NextMap()
{
    if(!bMenu) return; bCampaign=false; MapId=(MapId+1)%4; ResetRound();
}
void ASoraGameMode::SetMenuOpen(bool bOpen)
{
    bMenu=bOpen; bConfirmNewCampaign=false;
    // Menu time is discarded; practice resumes on a fresh 60 Hz step.
    if(bOpen) PracticeDirector->ResetClock();
    SyncMenuPause();
}
void ASoraGameMode::SyncMenuPause()
{
    // The open menu pauses the world: actors, timers and the practice clock
    // stop, while the HUD still draws and menu bindings run when paused. The
    // first round is built by a next-tick timer, so pausing waits for it.
    APlayerController* Controller=UGameplayStatics::GetPlayerController(this,0);
    if(!bRoundPrepared||!Controller) return;
    if(bMenu&&!IsPaused()) SetPause(Controller);
    else if(!bMenu&&IsPaused()) ClearPause();
}
SoraInput::EState ASoraGameMode::InputState() const
{
    if(bMenu) return bConfirmNewCampaign?SoraInput::Confirm:SoraInput::Menu;
    if(bDefeated||bChapterComplete) return SoraInput::Result;
    return TitleCardTime>0.f?SoraInput::Card:SoraInput::Play;
}
const FSoraChapter* ASoraGameMode::TitleCardChapter() const
{
    return bCampaign&&InputState()==SoraInput::Card&&FSoraCatalog::Get().IsReady()
        ?&FSoraCatalog::Get().Chapter(CampaignDirector->ChapterId):nullptr;
}
void ASoraGameMode::NewCampaign()
{
    if(!bMenu) return;
    // Starting over erases the saved chapter, checkpoint and highest chapter.
    // The first press only asks; a second press confirms, Esc/Start withdraws.
    if(!bConfirmNewCampaign) { bConfirmNewCampaign=true; return; }
    bConfirmNewCampaign=false; bDeterministicPractice=false; bCampaign=true; MapId=0;
    CampaignDirector->StartOver();
    ResetRound();
}
void ASoraGameMode::ReturnCampaign()
{
    if(!bMenu||!CampaignDirector->HasSave()||!FSoraCatalog::Get().IsReady()) return;
    bDeterministicPractice=false; bCampaign=true;
    CampaignDirector->ResumeSavedChapter();
    ResetRound();
}
void ASoraGameMode::SelectClass(int32 Id)
{
    if(!bMenu||!FSoraCatalog::Get().IsReady()) return;
    if(bCampaign) return;
    SelectedClass=FMath::Clamp(Id,0,5); CampaignDirector->SaveProgress(); ResetRound();
}
void ASoraGameMode::ToggleSubtitles() { bEnglishSubtitles=!bEnglishSubtitles; CampaignDirector->SaveProgress(); }
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
    { Notice=TEXT("稽古の舞台またはコンテンツを準備できません。"); NoticeEnglish=TEXT("Practice requires the staged content catalog and an initialized arena."); return; }
    bDeterministicPractice=true; bCampaign=false; PracticeDirector->Reset();
}
void ASoraGameMode::SelectPracticeWeapon(int32 Slot)
{
    // 1 enters with the standard loadout and 3 admits the class special; the
    // blade is chosen at respawn, as the kernel allows.
    if(!bMenu||!bDeterministicPractice||(Slot!=0&&Slot!=2)) return;
    PracticeDirector->Config.SpecialWeaponId=Slot==2?SoraPractice::SpecialOf(SelectedClass):INDEX_NONE; PracticeDirector->Reset();
}
FString ASoraGameMode::ObjectiveText() const
{
    if(bDeterministicPractice) return PracticeDirector->ObjectiveText();
    if(!WorldBuilder) return TEXT("舞台を準備しています…");
    return CampaignDirector->ObjectiveText();
}
FString ASoraGameMode::ObjectiveTextEnglish() const
{
    if(bDeterministicPractice) return PracticeDirector->ObjectiveTextEnglish();
    if(!WorldBuilder) return TEXT("Preparing the stage...");
    return CampaignDirector->ObjectiveTextEnglish();
}
