#include "SoraCampaignDirector.h"
#include "SoraBoss.h"
#include "SoraCampaignRules.h"
#include "SoraCatalog.h"
#include "SoraEnemy.h"
#include "SoraGameEvents.h"
#include "SoraGameMode.h"
#include "SoraPlayerCharacter.h"
#include "SoraProjectile.h"
#include "SoraSaveGame.h"
#include "SoraWorldBuilder.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/Controller.h"
#include "Kismet/GameplayStatics.h"

USoraCampaignDirector::USoraCampaignDirector()
{
    // ASoraGameMode drives the director from its own tick and commands.
    PrimaryComponentTick.bCanEverTick=false;
}
ASoraGameMode& USoraCampaignDirector::Mode() const { return *CastChecked<ASoraGameMode>(GetOwner()); }
bool USoraCampaignDirector::LoadSave()
{
    ASoraGameMode& M=Mode();
    Save=Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(M.SaveSlotName,0));
    if(!Save||Save->SaveSchema!=5)
    {
        Save=Cast<USoraSaveGame>(UGameplayStatics::CreateSaveGameObject(USoraSaveGame::StaticClass()));
        if(!Save) return false;
        Save->SaveSchema=5;
    }
    ChapterId=FMath::Clamp(Save->CurrentChapter,0,7); M.SelectedClass=FMath::Clamp(Save->SelectedClass,0,5);
    M.bEnglishSubtitles=Save->EnglishSubtitles;
    bCampaignComplete=Save->CampaignComplete; M.MapId=FSoraCatalog::Get().Chapter(ChapterId).Map;
    return true;
}
void USoraCampaignDirector::ResetRound()
{
    ASoraGameMode& M=Mode();
    ASoraWorldBuilder* WorldBuilder=M.Arena();
    const bool bCampaign=M.bCampaign;
    // A shell fired before death or chapter advance must never damage the
    // restored encounter or score a kill against its freshly spawned enemies.
    ClearOfflineProjectiles();
    for(const auto& E:Enemies) if(IsValid(E)) E->Destroy();
    Enemies.Reset(); BossActor=nullptr;
    Kills=0; Spawned=0; M.RoundTime=0; M.bDefeated=false; M.bChapterComplete=false;
    DojoLessonMask=0u;
    KillsNeeded=bCampaign?FSoraCatalog::Get().Chapter(ChapterId).Kills:12;
    WorldBuilder->Build(M.MapId,bCampaign?&FSoraCatalog::Get().Chapter(ChapterId):nullptr);
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
            M.bChapterComplete=Save->CheckpointComplete&&Kills==KillsNeeded&&WorldBuilder->ActiveNodes()==3;
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
        M.bChapterComplete=true;
    }
    if(ASoraPlayerCharacter* Player=M.Hero())
    {
        Player->GetCharacterMovement()->StopMovementImmediately();
        Player->SetActorLocation(WorldBuilder->PlayerStart(),false,nullptr,ETeleportType::TeleportPhysics);
        Player->SetActorRotation(FRotator::ZeroRotator); if(Player->GetController()) Player->GetController()->SetControlRotation(FRotator::ZeroRotator);
        // The campaign follows Nyaakoto. The six-class selection is for Arena
        // practice and cannot rewrite the offline protagonist's loadout.
        Player->ApplyClass(bCampaign?0:M.SelectedClass);
        Player->SetDojoTraining(bCampaign&&ChapterId==0);
        Player->SetCampaignHeroLoadout(bCampaign&&ChapterId>0);
    }
    if(!M.bChapterComplete) for(int32 I=0;I<FMath::Min(4,KillsNeeded-Kills);++I) SpawnEnemy();
    const bool bResumed=bRestoredVictory||(bHasCheckpoint&&(Kills>0||WorldBuilder->ActiveNodes()>0||M.bChapterComplete||DojoLessonMask!=0u));
    // Dialogue is presentation only. A resumed objective checkpoint does not replay
    // the chapter opening, and no cue cursor is written into the campaign save.
    bPlayChapterDialogue=bCampaign&&!bResumed;
    M.TitleCardTime=bPlayChapterDialogue?ASoraGameMode::TitleCardSeconds:0.f;
    M.NoticeTime=12.f;
    if(bRestoredVictory)
    {
        M.Notice=TEXT("猫柳生は自由だ。生み出す力は、民の手にある。");
        M.NoticeEnglish=TEXT("Nyaagyu is free. Production belongs to its people.");
    }
    else if(bResumed)
    {
        M.Notice=bCampaign&&ChapterId==7&&Kills==KillsNeeded-1?TEXT("最後の徴収官との決戦から再開した。構えを見て、刃をかわそう。")
            :M.bChapterComplete?TEXT("出口の封印は解かれた。Enter で物語を進めよう。")
            :bCampaign&&ChapterId==0?TEXT("稽古の記録から再開した。残る立合いと道場の仕事を確かめよう。")
            :TEXT("復旧記録から再開した。残る拠点と侵略者を確認しよう。");
        M.NoticeEnglish=bCampaign&&ChapterId==7&&Kills==KillsNeeded-1?TEXT("The final collector awaits. Watch the telegraph and evade the strike.")
            :M.bChapterComplete?TEXT("The exit is open. Press Enter to continue the story.")
            :bCampaign&&ChapterId==0?TEXT("Training checkpoint restored. Check the remaining bouts and dojo tasks.")
            :TEXT("Checkpoint restored. Check the remaining sites and invaders.");
    }
    else if(bCampaign)
    {
        // The title card carries the chapter narrative and objective, so no
        // notice competes with it or with the opening dialogue.
        M.Notice.Empty(); M.NoticeEnglish.Empty(); M.NoticeTime=0.f;
    }
    else
    {
        M.Notice=TEXT("稽古場です。特殊武器を自由に試せます。XOR や NFT は預けません。");
        M.NoticeEnglish=TEXT("Training arena. All special weapons are available for practice; no assets are bonded.");
    }
    if(bCampaign)
        if(auto* Events=USoraGameEvents::Get(this))
        {
            FSoraChapterEvent Started;
            Started.ChapterId=ChapterId; Started.bResumed=bResumed; Started.bLiberated=bRestoredVictory;
            Events->OnChapterStarted.Broadcast(Started);
        }
}
void USoraCampaignDirector::ClearEncounter()
{
    for(const auto& Enemy:Enemies) if(IsValid(Enemy)) Enemy->Destroy(); Enemies.Reset();
    ClearOfflineProjectiles();
    Kills=0;
}
void USoraCampaignDirector::SpawnEnemy()
{
    ASoraGameMode& M=Mode();
    ASoraWorldBuilder* WorldBuilder=M.Arena();
    if(!WorldBuilder||Spawned>=KillsNeeded) return;
    const bool bFinalBoss=M.bCampaign&&SoraCampaignRules::IsFinalBossSlot(ChapterId,Spawned,KillsNeeded);
    // The collector arrives only after all seventeen guards have fallen. A
    // restored checkpoint at that milestone follows the same spawn path.
    if(bFinalBoss&&!SoraCampaignRules::CanSpawnFinalBoss(ChapterId,Kills,Spawned,KillsNeeded)) return;
    FActorSpawnParameters Params; Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButAlwaysSpawn;
    ASoraEnemy* Enemy=nullptr;
    if(bFinalBoss)
    {
        // The collector is High Collector Val Amort (Content/Data/bosses.json).
        auto* Boss=ASoraBoss::SpawnBoss(*GetWorld(),TEXT("boss_val_amort"),Spawned,WorldBuilder->SpawnPoint(Spawned),FRotator(0,180,0));
        if(!Boss) return;
        BossActor=Boss;
        M.Notice=TEXT("徴収官『この街の息さえ、利子として差し押さえる』");
        M.NoticeEnglish=TEXT("Collector: Even this city's breath is collateral for interest.");
        M.NoticeTime=7.f;
        Enemy=Boss;
    }
    else
    {
        Enemy=GetWorld()->SpawnActor<ASoraEnemy>(WorldBuilder->SpawnPoint(Spawned),FRotator(0,180,0),Params);
        if(!Enemy) return;
        if(M.bCampaign&&ChapterId==0) Enemy->InitDojoPupil(Spawned);
        else Enemy->InitInvader(Spawned);
    }
    Enemies.Add(Enemy); ++Spawned;
}
const ASoraBoss* USoraCampaignDirector::CampaignBoss() const
{
    return IsValid(BossActor)&&BossActor->IsAlive() ? BossActor.Get() : nullptr;
}
const FSoraDialogueCue* USoraCampaignDirector::CurrentDialogueCue() const
{
    const ASoraGameMode& M=Mode();
    if(!M.bCampaign||!bPlayChapterDialogue||!M.IsPlaying()||!FSoraCatalog::Get().IsReady()) return nullptr;
    for(const auto& Cue:FSoraCatalog::Get().Chapter(ChapterId).Dialogue)
        if(M.RoundTime>=Cue.StartSeconds&&M.RoundTime<Cue.StartSeconds+Cue.DurationSeconds) return &Cue;
    return nullptr;
}
bool USoraCampaignDirector::AdvanceChapter()
{
    ASoraGameMode& M=Mode();
    const int32 NextChapter=SoraCampaignRules::AdvanceChapter(ChapterId,7,M.bChapterComplete);
    if(M.bCampaign&&NextChapter!=ChapterId) { ChapterId=NextChapter; M.MapId=FSoraCatalog::Get().Chapter(ChapterId).Map; ClearCheckpoint(); SaveProgress(); }
    else if(M.bCampaign) { bCampaignComplete=SoraCampaignRules::CampaignLiberated(ChapterId,7,M.bChapterComplete); ClearCheckpoint(); SaveProgress(); M.SetMenuOpen(true); return false; }
    return true;
}
void USoraCampaignDirector::StartOver()
{
    bCampaignComplete=false; ChapterId=0;
    DojoLessonMask=0u;
    if(Save) Save->HighestChapter=0;
    ClearCheckpoint();
    SaveProgress();
}
void USoraCampaignDirector::ResumeSavedChapter()
{
    ChapterId=FMath::Clamp(Save->CurrentChapter,0,7);
    bCampaignComplete=Save->CampaignComplete; Mode().MapId=FSoraCatalog::Get().Chapter(ChapterId).Map;
}
int32 USoraCampaignDirector::HighestChapter() const { return Save?FMath::Clamp(Save->HighestChapter,0,7):0; }
bool USoraCampaignDirector::SelectChapter(int32 Chapter)
{
    if(!Save||!FSoraCatalog::Get().IsReady()||Chapter<0||Chapter>HighestChapter()) return false;
    // Replaying reopens the story from that chapter, so a liberated campaign
    // fights its final chapter again rather than restoring the liberated city.
    ChapterId=Chapter; bCampaignComplete=false; DojoLessonMask=0u;
    Mode().MapId=FSoraCatalog::Get().Chapter(ChapterId).Map;
    ClearCheckpoint();
    SaveProgress();
    return true;
}
bool USoraCampaignDirector::HasProgress() const
{
    return Save&&(Save->CurrentChapter>0||Save->HighestChapter>0||Save->CheckpointChapter>=0||Save->CampaignComplete);
}
void USoraCampaignDirector::SuspendDojo(bool bIncludeHero)
{
    if(ChapterId!=0) return;
    if(bIncludeHero)
    {
        if(ASoraPlayerCharacter* Player=Mode().Hero()) Player->SuspendDojoAction();
    }
    for(const auto& Enemy:Enemies) if(IsValid(Enemy)) Enemy->SuspendDojoAction();
}
void USoraCampaignDirector::Interact(ASoraPlayerCharacter& Player)
{
    ASoraGameMode& M=Mode();
    ASoraWorldBuilder* WorldBuilder=M.Arena();
    const bool bCampaign=M.bCampaign;
    const int32 SiteId=WorldBuilder->NearestInactiveNode(Player.GetActorLocation());
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
                M.Notice=Dependency.Name+TEXT("を先に復旧しよう。");
                M.NoticeEnglish=TEXT("Restore ")+Dependency.NameEnglish+TEXT(" first.");
                M.NoticeTime=5.f; return;
            }
            if(!SoraCampaignRules::CanRestoreSite(Kills,static_cast<unsigned>(WorldBuilder->ActivatedMask()),
                {Site.RequiredKills,static_cast<unsigned>(Site.RequiredSitesMask)}))
            {
                M.Notice=bCampaign&&ChapterId==0
                    ?FString::Printf(TEXT("%sの前に、門弟とあと %d 回立ち合おう。"),*Site.Name,Site.RequiredKills-Kills)
                    :FString::Printf(TEXT("%sはまだ敵に守られている。侵略者をあと %d 体退けよう。"),*Site.Name,Site.RequiredKills-Kills);
                M.NoticeEnglish=bCampaign&&ChapterId==0
                    ?FString::Printf(TEXT("Complete %d more sparring bouts before %s."),Site.RequiredKills-Kills,*Site.NameEnglish)
                    :FString::Printf(TEXT("%s is still guarded. Defeat %d more invaders."),*Site.NameEnglish,Site.RequiredKills-Kills);
                M.NoticeTime=5.f; return;
            }
        }
        SoraCampaignRules::FCheckpoint SiteProgress{Kills,static_cast<unsigned>(WorldBuilder->ActivatedMask()),M.bChapterComplete};
        const bool bAllowed=!bCampaign||SoraCampaignRules::RestoreSite(SiteProgress,SiteId,
            {FSoraCatalog::Get().Chapter(ChapterId).Sites[SiteId].RequiredKills,
             static_cast<unsigned>(FSoraCatalog::Get().Chapter(ChapterId).Sites[SiteId].RequiredSitesMask)},3);
        if(bAllowed&&WorldBuilder->ActivateNearest(Player.GetActorLocation()))
        {
            Player.Heal(22.f);
            if(bCampaign)
            {
                const auto& Site=FSoraCatalog::Get().Chapter(ChapterId).Sites[SiteId];
                M.Notice=Site.Restored; M.NoticeEnglish=Site.RestoredEnglish;
                SaveCheckpoint();
            }
            else
            {
                M.Notice=TEXT("生産を再開した。この工房は、再び民のものだ。");
                M.NoticeEnglish=TEXT("Production restored. The community now controls this workshop.");
            }
            M.NoticeTime=7.f;
            if(auto* Events=USoraGameEvents::Get(this))
            {
                FSoraSiteRestoredEvent Restored;
                Restored.ChapterId=ChapterId; Restored.SiteIndex=SiteId; Restored.bCampaign=bCampaign;
                Restored.Kind=bCampaign?FSoraCatalog::Get().Chapter(ChapterId).Sites[SiteId].Kind:FString(TEXT("workshop"));
                Events->OnSiteRestored.Broadcast(Restored);
            }
        }
        return;
    }
    if(FVector::Dist2D(Player.GetActorLocation(),WorldBuilder->ExitPoint())<270.f)
    {
        if(bCampaign&&ChapterId==0&&!CanScoreDojoBout())
        {
            M.Notice=TEXT("師の稽古を終えてから、鳥居へ向かおう。");
            M.NoticeEnglish=TEXT("Finish the master's four lessons before leaving the dojo.");
            M.NoticeTime=5.f; return;
        }
        SoraCampaignRules::FCheckpoint ExitProgress{Kills,static_cast<unsigned>(WorldBuilder->ActivatedMask()),M.bChapterComplete};
        if(SoraCampaignRules::CompleteChapter(ExitProgress,KillsNeeded,3))
        {
            M.bChapterComplete=ExitProgress.Complete;
            if(bCampaign) { Save->HighestChapter=FMath::Max(Save->HighestChapter,FMath::Min(7,ChapterId+1)); if(SoraCampaignRules::CampaignLiberated(ChapterId,7,M.bChapterComplete)) bCampaignComplete=true; }
            M.Notice=ChapterId==7&&bCampaign?TEXT("猫柳生は自由だ。生み出す力は、民の手にある。")
                :bCampaign&&ChapterId==0?TEXT("道場の修行を終えた。Enter で物語を進めよう。")
                :TEXT("街区を解放した。Enter で次の戦いへ。");
            M.NoticeEnglish=ChapterId==7&&bCampaign?TEXT("Nyaagyu is free. Production belongs to its people.")
                :bCampaign&&ChapterId==0?TEXT("Dojo training complete. Press Enter to continue the story.")
                :TEXT("District liberated. Press Enter to continue.");
            if(bCampaign)
            {
                SaveCheckpoint();
                if(auto* Events=USoraGameEvents::Get(this))
                {
                    FSoraChapterEvent Completed;
                    Completed.ChapterId=ChapterId; Completed.bLiberated=SoraCampaignRules::CampaignLiberated(ChapterId,7,M.bChapterComplete);
                    Events->OnChapterCompleted.Broadcast(Completed);
                }
            }
        }
        else
        {
            M.Notice=bCampaign&&ChapterId==7&&CampaignBoss()?TEXT("徴収官を退け、最後の記録台を民に返そう。")
                :bCampaign&&ChapterId==0?TEXT("残る立合いと道場の仕事を終えよう。")
                :TEXT("残る拠点の仕事を終え、侵略者を退けよう。");
            M.NoticeEnglish=bCampaign&&ChapterId==7&&CampaignBoss()?TEXT("Defeat the collector and return the final ledger to the people.")
                :bCampaign&&ChapterId==0?TEXT("Finish the remaining sparring and dojo tasks first.")
                :TEXT("Finish the remaining site tasks and defeat the invaders first.");
            M.NoticeTime=5.f;
        }
    }
}
void USoraCampaignDirector::OpponentDefeated(ASoraEnemy* Opponent)
{
    ASoraGameMode& M=Mode();
    if(M.bDeterministicPractice) return;
    if(M.bCampaign&&ChapterId==0&&!CanScoreDojoBout()) return;
    SoraCampaignRules::FCheckpoint Progress{Kills,
        M.Arena()?static_cast<unsigned>(M.Arena()->ActivatedMask()):0u,M.bChapterComplete};
    if(!SoraCampaignRules::RecordDefeat(Progress,KillsNeeded)) return;
    const bool bDefeatedBoss=Opponent&&Opponent->IsA<ASoraBoss>();
    if(bDefeatedBoss) BossActor=nullptr;
    Kills=Progress.Kills; if(ASoraPlayerCharacter* Player=M.Hero()) Player->Heal(8.f);
    if(Spawned<KillsNeeded) SpawnEnemy();
    if(Kills>=KillsNeeded)
    {
        M.Notice=bDefeatedBoss?TEXT("侍『帳簿を閉じろ。田畑も工房も、働く者の手に戻す』")
            :M.bCampaign&&ChapterId==0?TEXT("門弟との立合いを終えた。道場の鍛冶場を直し、東の鳥居へ向かおう。")
            :TEXT("侵略者を退けた。残る生産拠点を取り戻し、東の鳥居へ向かおう。");
        M.NoticeEnglish=bDefeatedBoss?TEXT("Samurai: Close the ledger. Fields and workshops return to those who work them.")
            :M.bCampaign&&ChapterId==0?TEXT("Sparring complete. Restore the dojo smithy, then reach the eastern torii gate.")
            :TEXT("Invaders cleared. Restore the remaining production sites, then reach the eastern torii gate.");
        M.NoticeTime=7.f;
    }
    if(M.bCampaign) SaveCheckpoint();
}
bool USoraCampaignDirector::CanScoreDojoBout() const
{
    return Mode().bCampaign&&ChapterId==0&&SoraDojoRules::CanScoreBout({DojoLessonMask});
}
int32 USoraCampaignDirector::DojoLessonStage() const
{
    return Mode().bCampaign&&ChapterId==0?SoraDojoRules::NextLesson({DojoLessonMask}):4;
}
bool USoraCampaignDirector::RecordDojoLesson(SoraDojoRules::EAction Action,int32 DurationMs,bool bFacingAttacker,int32 RecoveryMs)
{
    ASoraGameMode& M=Mode();
    if(!M.bCampaign||ChapterId!=0||!M.IsPlaying()) return false;
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
    M.Notice=Japanese[Completed]; M.NoticeEnglish=English[Completed]; M.NoticeTime=8.f;
    SaveCheckpoint();
    return true;
}
void USoraCampaignDirector::PlayerKilled()
{
    ASoraGameMode& M=Mode();
    if(M.bDeterministicPractice) return;
    M.bDefeated=true;
    M.Notice=M.bCampaign&&ChapterId==0?TEXT("立合いはここまで。Enter で稽古をやり直そう。")
        :TEXT("仲間は、あなたを待っている。Enter で最後の復旧記録から再開する。");
    M.NoticeEnglish=M.bCampaign&&ChapterId==0?TEXT("The sparring bout has ended. Press Enter to resume training.")
        :TEXT("The resistance remembers. Press Enter to retry from the latest checkpoint.");
}
void USoraCampaignDirector::SaveCheckpoint()
{
    ASoraGameMode& M=Mode();
    if(!M.bCampaign||!Save||!M.Arena()) return;
    Save->CheckpointChapter=ChapterId;
    Save->CheckpointKills=FMath::Clamp(Kills,0,KillsNeeded);
    Save->CheckpointNodesMask=M.Arena()->ActivatedMask();
    Save->CheckpointComplete=M.bChapterComplete;
    Save->CheckpointDojoLessonMask=M.bCampaign&&ChapterId==0?static_cast<int32>(DojoLessonMask):0;
    SaveProgress();
}
void USoraCampaignDirector::ClearCheckpoint()
{
    if(!Save) return;
    Save->CheckpointChapter=-1;
    Save->CheckpointKills=0;
    Save->CheckpointNodesMask=0;
    Save->CheckpointComplete=false;
    Save->CheckpointDojoLessonMask=0;
}
void USoraCampaignDirector::SaveProgress()
{
    if(!Save) return;
    ASoraGameMode& M=Mode();
    Save->CurrentChapter=ChapterId; Save->SelectedClass=M.SelectedClass; Save->CampaignComplete=bCampaignComplete;
    Save->EnglishSubtitles=M.bEnglishSubtitles;
    if(!UGameplayStatics::SaveGameToSlot(Save,M.SaveSlotName,0)) { M.Notice=TEXT("進行を保存できませんでした。今回の起動中は続けられます。"); M.NoticeEnglish=TEXT("Unable to write campaign save. Progress remains available this session."); M.NoticeTime=6.f; }
}
void USoraCampaignDirector::ClearOfflineProjectiles()
{
    TArray<AActor*> Projectiles;
    UGameplayStatics::GetAllActorsOfClass(this,ASoraProjectile::StaticClass(),Projectiles);
    for(auto* Projectile:Projectiles) if(IsValid(Projectile)) Projectile->Destroy();
}
FString USoraCampaignDirector::ObjectiveText() const
{
    const ASoraGameMode& M=Mode();
    const ASoraWorldBuilder* WorldBuilder=M.Arena();
    if(M.bCampaign)
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
FString USoraCampaignDirector::ObjectiveTextEnglish() const
{
    const ASoraGameMode& M=Mode();
    const ASoraWorldBuilder* WorldBuilder=M.Arena();
    if(M.bCampaign)
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
FString USoraCampaignDirector::DojoLessonText(bool bEnglish) const
{
    if(!Mode().bCampaign||ChapterId!=0||DojoLessonStage()>=4) return FString();
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
