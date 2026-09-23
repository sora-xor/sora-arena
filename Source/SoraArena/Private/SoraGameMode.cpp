#include "SoraGameMode.h"
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
    if(!Save) Save=Cast<USoraSaveGame>(UGameplayStatics::CreateSaveGameObject(USoraSaveGame::StaticClass()));
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
    for(const auto& E:Enemies) if(IsValid(E)) E->Destroy(); Enemies.Reset();
    Kills=0; Spawned=0; RoundTime=0; bDefeated=false; bChapterComplete=false;
    KillsNeeded=bCampaign?FSoraCatalog::Get().Chapter(ChapterId).Kills:12;
    WorldBuilder->Build(MapId);
    const bool bHasCheckpoint=bCampaign&&Save&&Save->CheckpointChapter==ChapterId;
    if(bHasCheckpoint)
    {
        Kills=FMath::Clamp(Save->CheckpointKills,0,KillsNeeded);
        WorldBuilder->RestoreActivatedMask(Save->CheckpointNodesMask);
        bChapterComplete=Save->CheckpointComplete&&Kills==KillsNeeded&&WorldBuilder->ActiveNodes()==3;
        Spawned=Kills;
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
    }
    if(!bChapterComplete) for(int32 I=0;I<FMath::Min(4,KillsNeeded-Kills);++I) SpawnEnemy();
    const bool bResumed=bRestoredVictory||(bHasCheckpoint&&(Kills>0||WorldBuilder->ActiveNodes()>0||bChapterComplete));
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
        Notice=bChapterComplete?TEXT("出口の封印は解かれた。Enter で物語を進めよう。"):TEXT("復旧記録から再開した。残る拠点と侵略者を確認しよう。");
        NoticeEnglish=bChapterComplete?TEXT("The exit is open. Press Enter to continue the story."):TEXT("Checkpoint restored. Check the remaining sites and invaders.");
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
    FActorSpawnParameters Params; Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButAlwaysSpawn;
    auto* Enemy=GetWorld()->SpawnActor<ASoraCharacter>(WorldBuilder->SpawnPoint(Spawned),FRotator(0,180,0),Params);
    Enemy->MakeEnemy(Spawned); Enemies.Add(Enemy); ++Spawned;
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
        if(bCampaign&&ChapterId<7) { ++ChapterId; MapId=FSoraCatalog::Get().Chapter(ChapterId).Map; ClearCheckpoint(); SaveProgress(); }
        else if(bCampaign) { bCampaignComplete=true; ClearCheckpoint(); SaveProgress(); bMenu=true; return; }
        ResetRound();
    }
    else if(bDefeated) ResetRound();
    bMenu=false;
}
void ASoraGameMode::ToggleMenu() { bMenu=!bMenu; }
void ASoraGameMode::NextMap()
{
    if(!bMenu) return; bCampaign=false; MapId=(MapId+1)%4; ResetRound();
}
void ASoraGameMode::NewCampaign()
{
    if(!bMenu) return; bDeterministicPractice=false; bCampaign=true; bCampaignComplete=false; ChapterId=0; MapId=0;
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
    if(WorldBuilder->ActivateNearest(Player->GetActorLocation()))
    {
        Player->Heal(22.f);
        Notice=TEXT("生産を再開した。この工房は、再び民のものだ。");
        NoticeEnglish=TEXT("Production restored. The community now controls this workshop."); NoticeTime=5.f;
        if(bCampaign) SaveCheckpoint();
        return;
    }
    if(FVector::Dist2D(Player->GetActorLocation(),WorldBuilder->ExitPoint())<270.f)
    {
        if(Kills>=KillsNeeded&&WorldBuilder->ActiveNodes()==3)
        {
            bChapterComplete=true;
            if(bCampaign) { Save->HighestChapter=FMath::Max(Save->HighestChapter,FMath::Min(7,ChapterId+1)); if(ChapterId==7) bCampaignComplete=true; }
            Notice=ChapterId==7&&bCampaign?TEXT("猫柳生は自由だ。生み出す力は、民の手にある。"):TEXT("街区を解放した。Enter で次の戦いへ。");
            NoticeEnglish=ChapterId==7&&bCampaign?TEXT("Nyaagyu is free. Production belongs to its people."):TEXT("District liberated. Press Enter to continue.");
            if(bCampaign) SaveCheckpoint();
        }
        else { Notice=TEXT("三つの生産拠点を直し、残る侵略者を退けよう。"); NoticeEnglish=TEXT("Restore all three production sites and defeat the remaining invaders first."); NoticeTime=5.f; }
    }
}
void ASoraGameMode::EnemyKilled(ASoraCharacter* Enemy)
{
    if(bDeterministicPractice) return;
    ++Kills; if(auto* Player=Cast<ASoraCharacter>(UGameplayStatics::GetPlayerPawn(this,0))) Player->Heal(8.f);
    if(Spawned<KillsNeeded) SpawnEnemy();
    if(Kills>=KillsNeeded) { Notice=TEXT("侵略者を退けた。工房を取り戻し、東の鳥居へ向かおう。"); NoticeEnglish=TEXT("Invaders cleared. Restore the workshops, then return to the eastern torii gate."); NoticeTime=7.f; }
    if(bCampaign) SaveCheckpoint();
}
void ASoraGameMode::PlayerKilled() { if(bDeterministicPractice) return; bDefeated=true; Notice=TEXT("仲間は、あなたを待っている。Enter で最後の復旧記録から再開する。"); NoticeEnglish=TEXT("The resistance remembers. Press Enter to retry from the latest checkpoint."); }
void ASoraGameMode::ToggleSubtitles() { bEnglishSubtitles=!bEnglishSubtitles; SaveProgress(); }
void ASoraGameMode::SaveCheckpoint()
{
    if(!bCampaign||!Save||!WorldBuilder) return;
    Save->CheckpointChapter=ChapterId;
    Save->CheckpointKills=FMath::Clamp(Kills,0,KillsNeeded);
    Save->CheckpointNodesMask=WorldBuilder->ActivatedMask();
    Save->CheckpointComplete=bChapterComplete;
    SaveProgress();
}
void ASoraGameMode::ClearCheckpoint()
{
    if(!Save) return;
    Save->CheckpointChapter=-1;
    Save->CheckpointKills=0;
    Save->CheckpointNodesMask=0;
    Save->CheckpointComplete=false;
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
    return FString::Printf(TEXT("生産の復旧 %d / 3    |    侵略者 %d / %d    |    出口：東の鳥居"),WorldBuilder->ActiveNodes(),Kills,KillsNeeded);
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
    TArray<AActor*> OldProjectiles; UGameplayStatics::GetAllActorsOfClass(this,ASoraProjectile::StaticClass(),OldProjectiles);
    for(auto* Projectile:OldProjectiles) Projectile->Destroy();
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
