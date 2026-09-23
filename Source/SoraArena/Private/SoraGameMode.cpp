#include "SoraGameMode.h"
#include "SoraCampaignRules.h"
#include "SoraCharacter.h"
#include "SoraCatalog.h"
#include "SoraWorldBuilder.h"
#include "SoraSaveGame.h"
#include "SoraHUD.h"
#include "Kismet/GameplayStatics.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "TimerManager.h"
#include "Engine/World.h"
#include "Engine/GameInstance.h"
#include "Components/StaticMeshComponent.h"
#include "ArenaKernelSubsystem.h"
#include "SoraProjectile.h"

ASoraGameMode::ASoraGameMode()
{
    PrimaryActorTick.bCanEverTick=true;
    DefaultPawnClass=ASoraCharacter::StaticClass(); HUDClass=ASoraHUD::StaticClass();
}
void ASoraGameMode::BeginPlay()
{
    Super::BeginPlay();
    if(!FSoraCatalog::Get().Load()) { Notice=FSoraCatalog::Get().Error; return; }
    Save=Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(TEXT("SoraSoloCampaign"),0));
    if(!Save||Save->SaveSchema!=5)
    {
        Save=Cast<USoraSaveGame>(UGameplayStatics::CreateSaveGameObject(USoraSaveGame::StaticClass()));
        if(!Save) return;
        Save->SaveSchema=5;
    }
    ChapterId=FMath::Clamp(Save->CurrentChapter,0,7); SelectedClass=FMath::Clamp(Save->SelectedClass,0,5);
    bEnglishSubtitles=Save->EnglishSubtitles;
    bCampaignComplete=Save->CampaignComplete; MapId=FSoraCatalog::Get().Chapter(ChapterId).Map;
    WorldBuilder=GetWorld()->SpawnActor<ASoraWorldBuilder>();
    GetWorldTimerManager().SetTimerForNextTick(this,&ASoraGameMode::ResetRound);
    if(auto* PC=UGameplayStatics::GetPlayerController(this,0)) { PC->SetInputMode(FInputModeGameOnly()); PC->bShowMouseCursor=false; }
}
void ASoraGameMode::ResetRound()
{
    if(bDeterministicPractice) { ResetPractice(); return; }
    ClearPractice();
    if(!WorldBuilder||!FSoraCatalog::Get().IsReady()) return;
    // A shell fired before death or chapter advance must never damage the
    // restored encounter or score a kill against its freshly spawned enemies.
    ClearOfflineProjectiles();
    for(const auto& E:Enemies) if(IsValid(E)) E->Destroy();
    Enemies.Reset(); BossActor=nullptr;
    Kills=0; Spawned=0; RoundTime=0; bDefeated=false; bChapterComplete=false;
    DojoLessonMask=0u;
    KillsNeeded=bCampaign?FSoraCatalog::Get().Chapter(ChapterId).Kills:12;
    WorldBuilder->Build(MapId,bCampaign?&FSoraCatalog::Get().Chapter(ChapterId):nullptr);
    const bool bHasCheckpoint=bCampaign&&Save&&Save->CheckpointChapter==ChapterId;
    if(bHasCheckpoint)
    {
        const int32 Mask=Save->CheckpointNodesMask;
        const auto& Sites=FSoraCatalog::Get().Chapter(ChapterId).Sites;
        SoraCampaignRules::FSite SiteRules[3];
        for(int32 I=0;I<FMath::Min(Sites.Num(),3);++I)
            SiteRules[I]={Sites[I].RequiredKills,static_cast<unsigned>(Sites[I].RequiredSitesMask)};
        const SoraCampaignRules::FCheckpoint Checkpoint{
            Save->CheckpointKills,static_cast<unsigned>(Mask),Save->CheckpointComplete};
        const unsigned SavedDojoMask=static_cast<unsigned>(Save->CheckpointDojoLessonMask);
        const bool bValid=Sites.Num()==3&&SoraCampaignRules::CheckpointValid(Checkpoint,KillsNeeded,SiteRules,Sites.Num())&&
            (ChapterId==0?SoraDojoRules::CheckpointValid({SavedDojoMask},Checkpoint.Kills,Checkpoint.NodesMask)
                         :SavedDojoMask==0u);
        if(bValid)
        {
            Kills=Save->CheckpointKills;
            if(ChapterId==0) DojoLessonMask=SavedDojoMask;
            WorldBuilder->RestoreActivatedMask(Mask);
            bChapterComplete=Save->CheckpointComplete&&Kills==KillsNeeded&&WorldBuilder->ActiveNodes()==3;
            // At seventeen final-chapter defeats, restoring a checkpoint
            // respawns the unique boss at full health. Partial boss damage is
            // never saved as a completed objective.
            Spawned=Kills;
        }
        else ClearCheckpoint();
    }
    // Completion is durable even after the terminal checkpoint has been cleared.
    // Reopening a finished campaign must show its liberated state, not restart
    // the final battle simply because there is no longer an active checkpoint.
    const bool bRestoredVictory=bCampaign&&bCampaignComplete&&ChapterId==7;
    if(bRestoredVictory)
    {
        Kills=KillsNeeded;
        Spawned=KillsNeeded;
        WorldBuilder->RestoreActivatedMask(7);
        bChapterComplete=true;
    }
    if(auto* Player=Cast<ASoraCharacter>(UGameplayStatics::GetPlayerPawn(this,0)))
    {
        Player->GetCharacterMovement()->StopMovementImmediately();
        Player->SetActorLocation(WorldBuilder->PlayerStart(),false,nullptr,ETeleportType::TeleportPhysics);
        Player->SetActorRotation(FRotator::ZeroRotator); if(Player->GetController()) Player->GetController()->SetControlRotation(FRotator::ZeroRotator);
        // The campaign follows one Nyaagyu samurai. The six-class selection is
        // for arena practice and does not rewrite the story protagonist.
        Player->ApplyClass(bCampaign?0:SelectedClass);
        Player->SetDojoTraining(bCampaign&&ChapterId==0);
    }
    if(!bChapterComplete) for(int32 I=0;I<FMath::Min(4,KillsNeeded-Kills);++I) SpawnEnemy();
    const bool bResumed=bRestoredVictory||(bHasCheckpoint&&(Kills>0||WorldBuilder->ActiveNodes()>0||bChapterComplete||DojoLessonMask!=0u));
    // Dialogue is presentation only. A resumed objective checkpoint does not replay
    // the chapter opening, and no cue cursor is written into the campaign save.
    bPlayChapterDialogue=bCampaign&&!bResumed;
    if(bRestoredVictory)
    {
        Notice=TEXT("猫柳生は自由だ。生み出す力は、民の手にある。");
        NoticeEnglish=TEXT("Nyaagyu is free. Production belongs to its people.");
    }
    else if(bResumed)
    {
        Notice=bCampaign&&ChapterId==7&&Kills==KillsNeeded-1?TEXT("最後の徴収官との決戦から再開した。構えを見て、刃をかわそう。")
            :bChapterComplete?TEXT("出口の封印は解かれた。Enter で物語を進めよう。")
            :bCampaign&&ChapterId==0?TEXT("稽古の記録から再開した。残る立合いと道場の仕事を確かめよう。")
            :TEXT("復旧記録から再開した。残る拠点と侵略者を確認しよう。");
        NoticeEnglish=bCampaign&&ChapterId==7&&Kills==KillsNeeded-1?TEXT("The final collector awaits. Watch the telegraph and evade the strike.")
            :bChapterComplete?TEXT("The exit is open. Press Enter to continue the story.")
            :bCampaign&&ChapterId==0?TEXT("Training checkpoint restored. Check the remaining bouts and dojo tasks.")
            :TEXT("Checkpoint restored. Check the remaining sites and invaders.");
    }
    else
    {
        Notice=bCampaign?FSoraCatalog::Get().Chapter(ChapterId).Narrative:TEXT("稽古場です。特殊武器を自由に試せます。XOR や NFT は預けません。");
        NoticeEnglish=bCampaign?FSoraCatalog::Get().Chapter(ChapterId).NarrativeEnglish:TEXT("Training arena. All special weapons are available for practice; no assets are bonded.");
    }
    NoticeTime=12.f;
}
void ASoraGameMode::SpawnEnemy()
{
    if(!WorldBuilder||Spawned>=KillsNeeded) return;
    const bool bFinalBoss=bCampaign&&SoraCampaignRules::IsFinalBossSlot(ChapterId,Spawned,KillsNeeded);
    // The collector arrives only after all seventeen guards have fallen. A
    // restored checkpoint at that milestone follows the same spawn path.
    if(bFinalBoss&&!SoraCampaignRules::CanSpawnFinalBoss(ChapterId,Kills,Spawned,KillsNeeded)) return;
    FActorSpawnParameters Params; Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButAlwaysSpawn;
    auto* Enemy=GetWorld()->SpawnActor<ASoraCharacter>(WorldBuilder->SpawnPoint(Spawned),FRotator(0,180,0),Params);
    if(!Enemy) return;
    if(bCampaign&&ChapterId==0) Enemy->MakeDojoPupil(Spawned);
    else if(bFinalBoss)
    {
        Enemy->MakeCampaignBoss(Spawned);
        BossActor=Enemy;
        Notice=TEXT("徴収官『この街の息さえ、利子として差し押さえる』");
        NoticeEnglish=TEXT("Collector: Even this city's breath is collateral for interest.");
        NoticeTime=7.f;
    }
    else Enemy->MakeEnemy(Spawned);
    Enemies.Add(Enemy); ++Spawned;
}
const ASoraCharacter* ASoraGameMode::CampaignBoss() const
{
    return IsValid(BossActor)&&BossActor->IsAlive() ? BossActor.Get() : nullptr;
}
void ASoraGameMode::Tick(float Dt)
{
    Super::Tick(Dt); if(bMenu||bDefeated||bChapterComplete) { PracticeClock.Reset(); return; }
    if(bDeterministicPractice)
    {
        auto* K=Kernel(); auto* Player=Cast<ASoraCharacter>(UGameplayStatics::GetPlayerPawn(this,0));
        if(!K||!K->PracticeActive()||!Player) { bMenu=true; return; }
        const int32 Steps=PracticeClock.Advance(Dt); bPracticeSlowed=PracticeClock.Slowed;
        for(int32 Count=0;Count<Steps;++Count)
        {
            if(!K->StepPractice(Player->ConsumeKernelInput()))
            {
                Notice=K->PracticeError; NoticeEnglish=TEXT("The reference kernel rejected the practice update. Simulation stopped.");
                bMenu=true; PracticeClock.Reset(); return;
            }
            UpdatePracticePresentation(); PresentPracticeEvents();
            if(K->PracticeTerminal)
            {
                bChapterComplete=true; Notice=TEXT("十分間の稽古が終わりました。Enter でもう一度。");
                NoticeEnglish=TEXT("Ten-minute practice complete. Press Enter to restart."); break;
            }
        }
        RoundTime=K->PracticeTick/60.f; NoticeTime=FMath::Max(0.f,NoticeTime-Dt); return;
    }
    RoundTime+=Dt; NoticeTime=FMath::Max(0.f,NoticeTime-Dt);
}
const FSoraDialogueCue* ASoraGameMode::CurrentDialogueCue() const
{
    if(!bCampaign||!bPlayChapterDialogue||bMenu||bDefeated||bChapterComplete||!FSoraCatalog::Get().IsReady()) return nullptr;
    for(const auto& Cue:FSoraCatalog::Get().Chapter(ChapterId).Dialogue)
        if(RoundTime>=Cue.StartSeconds&&RoundTime<Cue.StartSeconds+Cue.DurationSeconds) return &Cue;
    return nullptr;
}
void ASoraGameMode::BeginRound()
{
    if(!FSoraCatalog::Get().IsReady()) return;
    if(bDeterministicPractice)
    {
        auto* K=Kernel();
        if(!K||!K->PracticeActive()||bChapterComplete||!K->PracticeError.IsEmpty()) if(!ResetPractice()) return;
        bMenu=false; return;
    }
    if(bChapterComplete)
    {
        const int32 NextChapter=SoraCampaignRules::AdvanceChapter(ChapterId,7,bChapterComplete);
        if(bCampaign&&NextChapter!=ChapterId) { ChapterId=NextChapter; MapId=FSoraCatalog::Get().Chapter(ChapterId).Map; ClearCheckpoint(); SaveProgress(); }
        else if(bCampaign) { bCampaignComplete=SoraCampaignRules::CampaignLiberated(ChapterId,7,bChapterComplete); ClearCheckpoint(); SaveProgress(); bMenu=true; return; }
        ResetRound();
    }
    else if(bDefeated) ResetRound();
    if(bMenu&&bCampaign&&ChapterId==0)
        for(const auto& Enemy:Enemies) if(IsValid(Enemy)) Enemy->SuspendDojoAction();
    bMenu=false;
}
void ASoraGameMode::ToggleMenu()
{
    bMenu=!bMenu;
    if(bCampaign&&ChapterId==0)
    {
        if(bMenu)
        {
            if(auto* Player=Cast<ASoraCharacter>(UGameplayStatics::GetPlayerPawn(this,0))) Player->SuspendDojoAction();
        }
        for(const auto& Enemy:Enemies) if(IsValid(Enemy)) Enemy->SuspendDojoAction();
    }
}
void ASoraGameMode::NextMap()
{
    if(!bMenu) return; bCampaign=false; MapId=(MapId+1)%4; ResetRound();
}
void ASoraGameMode::NewCampaign()
{
    if(!bMenu) return; bDeterministicPractice=false; bCampaign=true; bCampaignComplete=false; ChapterId=0; MapId=0;
    DojoLessonMask=0u;
    if(Save) Save->HighestChapter=0;
    ClearCheckpoint();
    SaveProgress(); ResetRound();
}
void ASoraGameMode::ReturnCampaign()
{
    if(!bMenu||!Save||!FSoraCatalog::Get().IsReady()) return;
    bDeterministicPractice=false; bCampaign=true; ChapterId=FMath::Clamp(Save->CurrentChapter,0,7);
    bCampaignComplete=Save->CampaignComplete; MapId=FSoraCatalog::Get().Chapter(ChapterId).Map;
    ResetRound();
}
void ASoraGameMode::SelectClass(int32 Id)
{
    if(!bMenu||!FSoraCatalog::Get().IsReady()) return;
    if(bCampaign) return;
    SelectedClass=FMath::Clamp(Id,0,5); SaveProgress(); ResetRound();
}
void ASoraGameMode::Interact(ASoraCharacter* Player)
{
    if(bDeterministicPractice) return;
    if(!WorldBuilder||!Player) return;
    const int32 SiteId=WorldBuilder->NearestInactiveNode(Player->GetActorLocation());
    if(SiteId!=INDEX_NONE)
    {
        if(bCampaign)
        {
            const auto& Site=FSoraCatalog::Get().Chapter(ChapterId).Sites[SiteId];
            const int32 Missing=Site.RequiredSitesMask&~WorldBuilder->ActivatedMask();
            if(Missing!=0)
            {
                int32 Prior=0;
                while((Missing&(1<<Prior))==0) ++Prior;
                const auto& Dependency=FSoraCatalog::Get().Chapter(ChapterId).Sites[Prior];
                Notice=Dependency.Name+TEXT("を先に復旧しよう。");
                NoticeEnglish=TEXT("Restore ")+Dependency.NameEnglish+TEXT(" first.");
                NoticeTime=5.f; return;
            }
            if(!SoraCampaignRules::CanRestoreSite(Kills,static_cast<unsigned>(WorldBuilder->ActivatedMask()),
                {Site.RequiredKills,static_cast<unsigned>(Site.RequiredSitesMask)}))
            {
                Notice=bCampaign&&ChapterId==0
                    ?FString::Printf(TEXT("%sの前に、門弟とあと %d 回立ち合おう。"),*Site.Name,Site.RequiredKills-Kills)
                    :FString::Printf(TEXT("%sはまだ敵に守られている。侵略者をあと %d 体退けよう。"),*Site.Name,Site.RequiredKills-Kills);
                NoticeEnglish=bCampaign&&ChapterId==0
                    ?FString::Printf(TEXT("Complete %d more sparring bouts before %s."),Site.RequiredKills-Kills,*Site.NameEnglish)
                    :FString::Printf(TEXT("%s is still guarded. Defeat %d more invaders."),*Site.NameEnglish,Site.RequiredKills-Kills);
                NoticeTime=5.f; return;
            }
        }
        SoraCampaignRules::FCheckpoint SiteProgress{Kills,static_cast<unsigned>(WorldBuilder->ActivatedMask()),bChapterComplete};
        const bool bAllowed=!bCampaign||SoraCampaignRules::RestoreSite(SiteProgress,SiteId,
            {FSoraCatalog::Get().Chapter(ChapterId).Sites[SiteId].RequiredKills,
             static_cast<unsigned>(FSoraCatalog::Get().Chapter(ChapterId).Sites[SiteId].RequiredSitesMask)},3);
        if(bAllowed&&WorldBuilder->ActivateNearest(Player->GetActorLocation()))
        {
            Player->Heal(22.f);
            if(bCampaign)
            {
                const auto& Site=FSoraCatalog::Get().Chapter(ChapterId).Sites[SiteId];
                Notice=Site.Restored; NoticeEnglish=Site.RestoredEnglish;
                SaveCheckpoint();
            }
            else
            {
                Notice=TEXT("生産を再開した。この工房は、再び民のものだ。");
                NoticeEnglish=TEXT("Production restored. The community now controls this workshop.");
            }
            NoticeTime=7.f;
        }
        return;
    }
    if(FVector::Dist2D(Player->GetActorLocation(),WorldBuilder->ExitPoint())<270.f)
    {
        if(bCampaign&&ChapterId==0&&!CanScoreDojoBout())
        {
            Notice=TEXT("師の稽古を終えてから、鳥居へ向かおう。");
            NoticeEnglish=TEXT("Finish the master's four lessons before leaving the dojo.");
            NoticeTime=5.f; return;
        }
        SoraCampaignRules::FCheckpoint ExitProgress{Kills,static_cast<unsigned>(WorldBuilder->ActivatedMask()),bChapterComplete};
        if(SoraCampaignRules::CompleteChapter(ExitProgress,KillsNeeded,3))
        {
            bChapterComplete=ExitProgress.Complete;
            if(bCampaign) { Save->HighestChapter=FMath::Max(Save->HighestChapter,FMath::Min(7,ChapterId+1)); if(SoraCampaignRules::CampaignLiberated(ChapterId,7,bChapterComplete)) bCampaignComplete=true; }
            Notice=ChapterId==7&&bCampaign?TEXT("猫柳生は自由だ。生み出す力は、民の手にある。")
                :bCampaign&&ChapterId==0?TEXT("道場の修行を終えた。Enter で物語を進めよう。")
                :TEXT("街区を解放した。Enter で次の戦いへ。");
            NoticeEnglish=ChapterId==7&&bCampaign?TEXT("Nyaagyu is free. Production belongs to its people.")
                :bCampaign&&ChapterId==0?TEXT("Dojo training complete. Press Enter to continue the story.")
                :TEXT("District liberated. Press Enter to continue.");
            if(bCampaign) SaveCheckpoint();
        }
        else
        {
            Notice=bCampaign&&ChapterId==7&&CampaignBoss()?TEXT("徴収官を退け、最後の記録台を民に返そう。")
                :bCampaign&&ChapterId==0?TEXT("残る立合いと道場の仕事を終えよう。")
                :TEXT("残る拠点の仕事を終え、侵略者を退けよう。");
            NoticeEnglish=bCampaign&&ChapterId==7&&CampaignBoss()?TEXT("Defeat the collector and return the final ledger to the people.")
                :bCampaign&&ChapterId==0?TEXT("Finish the remaining sparring and dojo tasks first.")
                :TEXT("Finish the remaining site tasks and defeat the invaders first.");
            NoticeTime=5.f;
        }
    }
}
void ASoraGameMode::OpponentDefeated(ASoraCharacter* Opponent)
{
    if(bDeterministicPractice) return;
    if(bCampaign&&ChapterId==0&&!CanScoreDojoBout()) return;
    SoraCampaignRules::FCheckpoint Progress{Kills,
        WorldBuilder?static_cast<unsigned>(WorldBuilder->ActivatedMask()):0u,bChapterComplete};
    if(!SoraCampaignRules::RecordDefeat(Progress,KillsNeeded)) return;
    const bool bDefeatedBoss=Opponent&&Opponent->IsCampaignBoss();
    if(bDefeatedBoss) BossActor=nullptr;
    Kills=Progress.Kills; if(auto* Player=Cast<ASoraCharacter>(UGameplayStatics::GetPlayerPawn(this,0))) Player->Heal(8.f);
    if(Spawned<KillsNeeded) SpawnEnemy();
    if(Kills>=KillsNeeded)
    {
        Notice=bDefeatedBoss?TEXT("侍『帳簿を閉じろ。田畑も工房も、働く者の手に戻す』")
            :bCampaign&&ChapterId==0?TEXT("門弟との立合いを終えた。道場の鍛冶場を直し、東の鳥居へ向かおう。")
            :TEXT("侵略者を退けた。残る生産拠点を取り戻し、東の鳥居へ向かおう。");
        NoticeEnglish=bDefeatedBoss?TEXT("Samurai: Close the ledger. Fields and workshops return to those who work them.")
            :bCampaign&&ChapterId==0?TEXT("Sparring complete. Restore the dojo smithy, then reach the eastern torii gate.")
            :TEXT("Invaders cleared. Restore the remaining production sites, then reach the eastern torii gate.");
        NoticeTime=7.f;
    }
    if(bCampaign) SaveCheckpoint();
}
bool ASoraGameMode::CanScoreDojoBout() const
{
    return bCampaign&&ChapterId==0&&SoraDojoRules::CanScoreBout({DojoLessonMask});
}
int32 ASoraGameMode::DojoLessonStage() const
{
    return bCampaign&&ChapterId==0?SoraDojoRules::NextLesson({DojoLessonMask}):4;
}
bool ASoraGameMode::RecordDojoLesson(SoraDojoRules::EAction Action,int32 DurationMs,bool bFacingAttacker,int32 RecoveryMs)
{
    if(!bCampaign||ChapterId!=0||bMenu||bDefeated||bChapterComplete) return false;
    SoraDojoRules::FProgress Progress{DojoLessonMask};
    if(!SoraDojoRules::Record(Progress,Action,DurationMs,bFacingAttacker,RecoveryMs)) return false;
    DojoLessonMask=Progress.CompletedMask;
    static const TCHAR* Japanese[]={
        TEXT("壱の型・構え。守りを保った。次は門弟の一撃を受けよう。"),
        TEXT("弐の型・受け。刃を正面で受けた。次は予兆に合わせて防御を押そう。"),
        TEXT("参の型・捌き。打ち込みを見切った。次は木刀を振り、刃が戻るまで待とう。"),
        TEXT("肆の型・残心。打った後も構えを崩さない。これより門弟との立合いだ。")};
    static const TCHAR* English[]={
        TEXT("Form one: stance held. Now face and guard a pupil's strike."),
        TEXT("Form two: guarded. Release defense, then press it during the golden warning to parry."),
        TEXT("Form three: parried. Swing your wooden sword, then let it fully recover."),
        TEXT("Form four: recovery mastered. You may now score the sparring bouts.")};
    const int32 Completed=DojoLessonStage()-1;
    Notice=Japanese[Completed]; NoticeEnglish=English[Completed]; NoticeTime=8.f;
    SaveCheckpoint();
    return true;
}
void ASoraGameMode::PlayerKilled()
{
    if(bDeterministicPractice) return;
    bDefeated=true;
    Notice=bCampaign&&ChapterId==0?TEXT("立合いはここまで。Enter で稽古をやり直そう。")
        :TEXT("仲間は、あなたを待っている。Enter で最後の復旧記録から再開する。");
    NoticeEnglish=bCampaign&&ChapterId==0?TEXT("The sparring bout has ended. Press Enter to resume training.")
        :TEXT("The resistance remembers. Press Enter to retry from the latest checkpoint.");
}
void ASoraGameMode::ToggleSubtitles() { bEnglishSubtitles=!bEnglishSubtitles; SaveProgress(); }
void ASoraGameMode::SaveCheckpoint()
{
    if(!bCampaign||!Save||!WorldBuilder) return;
    Save->CheckpointChapter=ChapterId;
    Save->CheckpointKills=FMath::Clamp(Kills,0,KillsNeeded);
    Save->CheckpointNodesMask=WorldBuilder->ActivatedMask();
    Save->CheckpointComplete=bChapterComplete;
    Save->CheckpointDojoLessonMask=bCampaign&&ChapterId==0?static_cast<int32>(DojoLessonMask):0;
    SaveProgress();
}
void ASoraGameMode::ClearCheckpoint()
{
    if(!Save) return;
    Save->CheckpointChapter=-1;
    Save->CheckpointKills=0;
    Save->CheckpointNodesMask=0;
    Save->CheckpointComplete=false;
    Save->CheckpointDojoLessonMask=0;
}
void ASoraGameMode::SaveProgress()
{
    if(!Save) return;
    Save->CurrentChapter=ChapterId; Save->SelectedClass=SelectedClass; Save->CampaignComplete=bCampaignComplete;
    Save->EnglishSubtitles=bEnglishSubtitles;
    if(!UGameplayStatics::SaveGameToSlot(Save,TEXT("SoraSoloCampaign"),0)) { Notice=TEXT("進行を保存できませんでした。今回の起動中は続けられます。"); NoticeEnglish=TEXT("Unable to write campaign save. Progress remains available this session."); NoticeTime=6.f; }
}
FString ASoraGameMode::ObjectiveText() const
{
    if(bDeterministicPractice)
    {
        const auto* K=Kernel();
        if(K&&K->PracticePlayers.Num()>0)
        {
            const auto& P=K->PracticePlayers[0];
            const int32 Seconds=FMath::Max(0,36000-static_cast<int32>(K->PracticeTick)+59)/60;
            return FString::Printf(TEXT("武芸稽古 / 撃破 %d  戦死 %d / 残り %02d:%02d"),P.Kills,P.Deaths,Seconds/60,Seconds%60);
        }
        return TEXT("武芸稽古を準備しています…");
    }
    if(!WorldBuilder) return TEXT("舞台を準備しています…");
    if(bCampaign)
    {
        const auto& Chapter=FSoraCatalog::Get().Chapter(ChapterId);
        if(ChapterId==0&&DojoLessonStage()<4)
            return FString::Printf(TEXT("猫柳生新陰流  |  型 %d / 4"),DojoLessonStage()+1);
        FString Next=TEXT("東の鳥居へ");
        for(int32 I=0;I<Chapter.Sites.Num();++I)
            if((WorldBuilder->ActivatedMask()&(1<<I))==0) { Next=Chapter.Sites[I].Name; break; }
        if(ChapterId==0)
            return FString::Printf(TEXT("%s  |  稽古場 %d / 3  |  立合い %d / %d"),*Next,WorldBuilder->ActiveNodes(),Kills,KillsNeeded);
        return FString::Printf(TEXT("%s  |  拠点 %d / 3  |  侵略者 %d / %d"),*Next,WorldBuilder->ActiveNodes(),Kills,KillsNeeded);
    }
    return FString::Printf(TEXT("生産の復旧 %d / 3    |    侵略者 %d / %d    |    出口：東の鳥居"),WorldBuilder->ActiveNodes(),Kills,KillsNeeded);
}
FString ASoraGameMode::ObjectiveTextEnglish() const
{
    if(bDeterministicPractice)
    {
        const auto* K=Kernel();
        if(K&&K->PracticePlayers.Num()>0)
        {
            const auto& P=K->PracticePlayers[0];
            const int32 Seconds=FMath::Max(0,36000-static_cast<int32>(K->PracticeTick)+59)/60;
            return FString::Printf(TEXT("Practice / Kills %d  Deaths %d / %02d:%02d left"),
                P.Kills,P.Deaths,Seconds/60,Seconds%60);
        }
        return TEXT("Preparing practice...");
    }
    if(!WorldBuilder) return TEXT("Preparing the stage...");
    if(bCampaign)
    {
        const auto& Chapter=FSoraCatalog::Get().Chapter(ChapterId);
        if(ChapterId==0&&DojoLessonStage()<4)
            return FString::Printf(TEXT("Nyaagyushinkageryuu / Form %d of 4"),DojoLessonStage()+1);
        FString Next=TEXT("Eastern torii gate");
        for(int32 I=0;I<Chapter.Sites.Num();++I)
            if((WorldBuilder->ActivatedMask()&(1<<I))==0) { Next=Chapter.Sites[I].NameEnglish; break; }
        if(ChapterId==0)
            return FString::Printf(TEXT("%s / Dojo sites %d of 3 / Sparring bouts %d of %d"),
                *Next,WorldBuilder->ActiveNodes(),Kills,KillsNeeded);
        return FString::Printf(TEXT("%s / Sites %d of 3 / Invaders %d of %d"),
            *Next,WorldBuilder->ActiveNodes(),Kills,KillsNeeded);
    }
    return FString::Printf(TEXT("Production sites %d of 3 / Invaders %d of %d / Exit: eastern torii gate"),
        WorldBuilder->ActiveNodes(),Kills,KillsNeeded);
}
FString ASoraGameMode::DojoLessonText(bool bEnglish) const
{
    if(!bCampaign||ChapterId!=0||DojoLessonStage()>=4) return FString();
    static const TCHAR* Japanese[]={
        TEXT("壱・構え：防御を 0.6 秒保つ"),
        TEXT("弐・受け：相手に向き、防御を保って一撃を受ける"),
        TEXT("参・捌き：金色の予兆に合わせて防御を押す"),
        TEXT("肆・残心：木刀を振り、攻撃を止めて刃の戻りを待つ")};
    static const TCHAR* English[]={
        TEXT("STANCE: hold Guard for 0.6 seconds."),
        TEXT("GUARD: face a pupil and hold Guard through its strike."),
        TEXT("PARRY: release, then press Guard during the golden warning."),
        TEXT("RECOVERY: swing once, release attack, and wait for the blade to return.")};
    return bEnglish?English[DojoLessonStage()]:Japanese[DojoLessonStage()];
}
UArenaKernelSubsystem* ASoraGameMode::Kernel() const
{
    return GetGameInstance()?GetGameInstance()->GetSubsystem<UArenaKernelSubsystem>():nullptr;
}
void ASoraGameMode::ClearPractice()
{
    if(auto* K=Kernel()) K->StopPractice();
    for(int32 I=1;I<PracticePawns.Num();++I) if(IsValid(PracticePawns[I])) PracticePawns[I]->Destroy();
    PracticePawns.Reset();
    for(auto& Item:PracticeProjectileActors) if(IsValid(Item.Value)) Item.Value->Destroy();
    PracticeProjectileActors.Reset(); PracticeClock.Reset();
    if(auto* Player=Cast<ASoraCharacter>(UGameplayStatics::GetPlayerPawn(this,0))) Player->SetKernelDriven(false);
}
void ASoraGameMode::ClearOfflineProjectiles()
{
    TArray<AActor*> Projectiles;
    UGameplayStatics::GetAllActorsOfClass(this,ASoraProjectile::StaticClass(),Projectiles);
    for(auto* Projectile:Projectiles) if(IsValid(Projectile)) Projectile->Destroy();
}
bool ASoraGameMode::ResetPractice()
{
    if(!WorldBuilder||!FSoraCatalog::Get().IsReady())
    { Notice=TEXT("稽古の舞台またはコンテンツを準備できません。"); bMenu=true; return false; }
    ClearPractice();
    auto* K=Kernel();
    if(!K||!K->StartPractice(SelectedClass,PracticeWeaponSlot,MapId))
    {
        Notice=K?K->PracticeError:TEXT("戦闘カーネルを利用できません。");
        NoticeEnglish=TEXT("The real Rust library must be staged and validated before practice can start."); bMenu=true; return false;
    }
    for(const auto& Enemy:Enemies) if(IsValid(Enemy)) Enemy->Destroy(); Enemies.Reset();
    ClearOfflineProjectiles();
    bDefeated=false; bChapterComplete=false; Kills=0; RoundTime=0; bPracticeSlowed=false;
    WorldBuilder->BuildPractice(MapId,K->PracticeMap);
    auto* Player=Cast<ASoraCharacter>(UGameplayStatics::GetPlayerPawn(this,0));
    if(!Player) { K->StopPractice(); Notice=TEXT("稽古のプレイヤーを作成できません。"); bMenu=true; return false; }
    Player->ApplyClass(SelectedClass); Player->SetKernelDriven(true,&K->PracticeMap); PracticePawns.Add(Player);
    for(int32 Slot=1;Slot<K->PracticePlayers.Num();++Slot)
    {
        FActorSpawnParameters Params; Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        auto* Pawn=GetWorld()->SpawnActor<ASoraCharacter>(FVector::ZeroVector,FRotator::ZeroRotator,Params);
        Pawn->MakeEnemy(Slot); Pawn->SetKernelDriven(true,&K->PracticeMap); PracticePawns.Add(Pawn);
    }
    UpdatePracticePresentation();
    if(Player->GetController()) Player->GetController()->SetControlRotation(K->PracticePlayers[0].Aim);
    Notice=TEXT("武芸稽古。左クリック射撃、右クリック近接、R 装填、Ctrl 防御、Q 技、Space 跳躍。死亡後は自動で復帰します。");
    NoticeEnglish=TEXT("Offline practice: fire, melee, R reload, Ctrl block, Q ability, Space jump. Defeated players respawn automatically. No assets are bonded."); NoticeTime=12.f;
    return true;
}
void ASoraGameMode::DeterministicPractice()
{
    if(!bMenu) return;
    if(!WorldBuilder||!FSoraCatalog::Get().IsReady())
    { Notice=TEXT("稽古の舞台またはコンテンツを準備できません。"); NoticeEnglish=TEXT("Practice requires the staged content catalog and an initialized arena."); return; }
    bDeterministicPractice=true; bCampaign=false; ResetPractice();
}
void ASoraGameMode::SelectPracticeWeapon(int32 Slot)
{
    if(!bMenu||!bDeterministicPractice||Slot<0||Slot>2) return;
    PracticeWeaponSlot=Slot; ResetPractice();
}
void ASoraGameMode::UpdatePracticePresentation()
{
    auto* K=Kernel(); if(!K) return;
    for(int32 Slot=0;Slot<K->PracticePlayers.Num();++Slot)
        if(PracticePawns.IsValidIndex(Slot)&&IsValid(PracticePawns[Slot])) PracticePawns[Slot]->ApplyKernelPlayer(K->PracticePlayers[Slot]);
    TSet<uint32> Live;
    for(const auto& P:K->PracticeProjectiles)
    {
        Live.Add(P.Id);
        auto* Actor=PracticeProjectileActors.FindRef(P.Id).Get();
        if(!IsValid(Actor))
        {
            Actor=GetWorld()->SpawnActor<AActor>();
            auto* Mesh=ASoraWorldBuilder::Shape(Actor,nullptr,TEXT("KernelProjectile"),TEXT("/Engine/BasicShapes/Sphere.Sphere"),FVector::ZeroVector,FVector(.15),FLinearColor(1,.35,.07));
            Actor->SetRootComponent(Mesh); PracticeProjectileActors.Add(P.Id,Actor);
        }
        Actor->SetActorLocation(P.Position);
    }
    for(auto It=PracticeProjectileActors.CreateIterator();It;++It) if(!Live.Contains(It.Key()))
    {
        if(IsValid(It.Value())) It.Value()->Destroy(); It.RemoveCurrent();
    }
}
void ASoraGameMode::PresentPracticeEvents()
{
    auto* K=Kernel(); if(!K) return;
    for(const auto& Event:K->PracticeEvents)
    {
        if(Event.Kind==1&&Event.WeaponKind!=2)
        {
            FCollisionQueryParams Query(SCENE_QUERY_STAT(KernelVisualRay),false);
            if(PracticePawns.IsValidIndex(Event.Actor)) Query.AddIgnoredActor(PracticePawns[Event.Actor]);
            FHitResult Hit; GetWorld()->LineTraceSingleByChannel(Hit,Event.From,Event.To,ECC_Visibility,Query);
            // Cosmetic clipping only. Damage/hit markers are driven by kernel damage events.
            ASoraCharacter::Beam(GetWorld(),Event.From,Hit.bBlockingHit?Hit.ImpactPoint:Event.To,Event.Actor==0?FLinearColor(.15,.8,1):FLinearColor(1,.2,.13),1.3f,.065f);
        }
        else if(Event.Kind==2&&PracticePawns.Num()>0)
        {
            if(Event.Actor==0) PracticePawns[0]->HitMarkerTime=.14f;
            if(Event.Target==0) PracticePawns[0]->DamageFlash=.3f;
        }
        else if(Event.Kind==4&&Event.Target==0)
        {
            Notice=TEXT("復帰しました。稽古を続けましょう。"); NoticeEnglish=TEXT("Respawned. Practice continues."); NoticeTime=3.f;
        }
    }
}
