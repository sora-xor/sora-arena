#include "SoraPracticeDirector.h"
#include "ArenaKernelSubsystem.h"
#include "Combat/SoraDamage.h"
#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraGameEvents.h"
#include "SoraGameMode.h"
#include "SoraPlayerCharacter.h"
#include "SoraPracticePawn.h"
#include "SoraWorldBuilder.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/Controller.h"

USoraPracticeDirector::USoraPracticeDirector()
{
    // ASoraGameMode steps practice from its own tick.
    PrimaryComponentTick.bCanEverTick=false;
}
ASoraGameMode& USoraPracticeDirector::Mode() const { return *CastChecked<ASoraGameMode>(GetOwner()); }
void USoraPracticeDirector::Clear()
{
    ASoraGameMode& M=Mode();
    if(auto* K=M.Kernel()) K->StopPractice();
    for(int32 I=1;I<Pawns.Num();++I) if(IsValid(Pawns[I])) Pawns[I]->Destroy();
    Pawns.Reset();
    for(auto& Item:ProjectileActors) if(IsValid(Item.Value)) Item.Value->Destroy();
    ProjectileActors.Reset(); Clock.Reset();
    if(ASoraPlayerCharacter* Player=M.Hero()) Player->SetKernelDriven(false);
}
bool USoraPracticeDirector::Reset()
{
    ASoraGameMode& M=Mode();
    ASoraWorldBuilder* WorldBuilder=M.Arena();
    if(!WorldBuilder||!FSoraCatalog::Get().IsReady())
    { M.Notice=TEXT("稽古の舞台またはコンテンツを準備できません。"); M.SetMenuOpen(true); return false; }
    M.bConfirmNewCampaign=false; M.TitleCardTime=0.f;
    Clear();
    auto* K=M.Kernel();
    if(!K||!K->StartPractice(M.SelectedClass,WeaponSlot,M.MapId))
    {
        M.Notice=K?K->PracticeError:TEXT("戦闘カーネルを利用できません。");
        M.NoticeEnglish=TEXT("The real Rust library must be staged and validated before practice can start."); M.SetMenuOpen(true); return false;
    }
    M.Campaign()->ClearEncounter();
    M.bDefeated=false; M.bChapterComplete=false; M.RoundTime=0; bSlowed=false;
    WorldBuilder->BuildPractice(M.MapId,K->PracticeMap);
    ASoraPlayerCharacter* Player=M.Hero();
    if(!Player) { K->StopPractice(); M.Notice=TEXT("稽古のプレイヤーを作成できません。"); M.SetMenuOpen(true); return false; }
    // The campaign round that ran before may have left chapter one's bokken or
    // Nyaakoto's loadout on the hero; practice holds the kernel's weapon.
    Player->SetDojoTraining(false); Player->SetCampaignHeroLoadout(false);
    Player->ApplyClass(M.SelectedClass); Player->SetKernelDriven(true,&K->PracticeMap); Pawns.Add(Player);
    for(int32 Slot=1;Slot<K->PracticePlayers.Num();++Slot)
    {
        FActorSpawnParameters Params; Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        auto* Pawn=GetWorld()->SpawnActor<ASoraPracticePawn>(FVector::ZeroVector,FRotator::ZeroRotator,Params);
        Pawn->InitParticipant(Slot); Pawn->SetKernelDriven(true,&K->PracticeMap); Pawns.Add(Pawn);
    }
    UpdatePresentation();
    if(Player->GetController()) Player->GetController()->SetControlRotation(K->PracticePlayers[0].Aim);
    M.Notice=TEXT("武芸稽古。左クリック射撃、右クリック近接、R 装填、Ctrl 防御、Q 技、Space 跳躍。死亡後は自動で復帰します。");
    M.NoticeEnglish=TEXT("Offline practice: fire, melee, R reload, Ctrl block, Q ability, Space jump. Defeated players respawn automatically. No assets are bonded."); M.NoticeTime=12.f;
    return true;
}
void USoraPracticeDirector::Step(float Dt)
{
    ASoraGameMode& M=Mode();
    auto* K=M.Kernel(); ASoraPlayerCharacter* Player=M.Hero();
    if(!K||!K->PracticeActive()||!Player) { M.SetMenuOpen(true); return; }
    const int32 Steps=Clock.Advance(Dt); bSlowed=Clock.Slowed;
    for(int32 Count=0;Count<Steps;++Count)
    {
        if(!K->StepPractice(Player->ConsumeKernelInput()))
        {
            M.Notice=K->PracticeError; M.NoticeEnglish=TEXT("The reference kernel rejected the practice update. Simulation stopped.");
            M.SetMenuOpen(true); return;
        }
        UpdatePresentation(); PresentEvents();
        if(K->PracticeTerminal)
        {
            M.bChapterComplete=true; M.Notice=TEXT("十分間の稽古が終わりました。Enter でもう一度。");
            M.NoticeEnglish=TEXT("Ten-minute practice complete. Press Enter to restart."); break;
        }
    }
    M.RoundTime=K->PracticeTick/60.f; M.NoticeTime=FMath::Max(0.f,M.NoticeTime-Dt);
}
void USoraPracticeDirector::UpdatePresentation()
{
    auto* K=Mode().Kernel(); if(!K) return;
    for(int32 Slot=0;Slot<K->PracticePlayers.Num();++Slot)
        if(Pawns.IsValidIndex(Slot)&&IsValid(Pawns[Slot])) Pawns[Slot]->ApplyKernelPlayer(K->PracticePlayers[Slot]);
    TSet<uint32> Live;
    for(const auto& P:K->PracticeProjectiles)
    {
        Live.Add(P.Id);
        auto* Actor=ProjectileActors.FindRef(P.Id).Get();
        if(!IsValid(Actor))
        {
            Actor=GetWorld()->SpawnActor<AActor>();
            auto* Mesh=ASoraWorldBuilder::Shape(Actor,nullptr,TEXT("KernelProjectile"),TEXT("/Engine/BasicShapes/Sphere.Sphere"),FVector::ZeroVector,FVector(.15),FLinearColor(1,.35,.07));
            Actor->SetRootComponent(Mesh); ProjectileActors.Add(P.Id,Actor);
        }
        Actor->SetActorLocation(P.Position);
    }
    for(auto It=ProjectileActors.CreateIterator();It;++It) if(!Live.Contains(It.Key()))
    {
        if(IsValid(It.Value())) It.Value()->Destroy(); It.RemoveCurrent();
    }
}
void USoraPracticeDirector::PresentEvents()
{
    ASoraGameMode& M=Mode();
    auto* K=M.Kernel(); if(!K) return;
    USoraGameEvents* Events=USoraGameEvents::Get(this);
    for(const auto& Event:K->PracticeEvents)
    {
        if(Event.Kind==1&&Event.WeaponKind!=2)
        {
            FCollisionQueryParams Query(SCENE_QUERY_STAT(KernelVisualRay),false);
            if(Pawns.IsValidIndex(Event.Actor)) Query.AddIgnoredActor(Pawns[Event.Actor]);
            FHitResult Hit; GetWorld()->LineTraceSingleByChannel(Hit,Event.From,Event.To,ECC_Visibility,Query);
            // Cosmetic clipping only. Damage/hit markers are driven by kernel damage events.
            SoraDamage::Beam(GetWorld(),Event.From,Hit.bBlockingHit?Hit.ImpactPoint:Event.To,Event.Actor==0?FLinearColor(.15,.8,1):FLinearColor(1,.2,.13),1.3f,.065f);
        }
        else if(Event.Kind==2&&Pawns.Num()>0)
        {
            if(Event.Actor==0) Pawns[0]->HitMarkerTime=.14f;
            if(Event.Target==0) Pawns[0]->DamageFlash=.3f;
        }
        else if(Event.Kind==4&&Event.Target==0)
        {
            M.Notice=TEXT("復帰しました。稽古を続けましょう。"); M.NoticeEnglish=TEXT("Respawned. Practice continues."); M.NoticeTime=3.f;
        }
        if(Events) Events->OnKernelEvent.Broadcast(Event,K->PracticeTick);
    }
}
FString USoraPracticeDirector::ObjectiveText() const
{
    const auto* K=Mode().Kernel();
    if(K&&K->PracticePlayers.Num()>0)
    {
        const auto& P=K->PracticePlayers[0];
        const int32 Seconds=FMath::Max(0,36000-static_cast<int32>(K->PracticeTick)+59)/60;
        return FString::Printf(TEXT("武芸稽古 / 撃破 %d  戦死 %d / 残り %02d:%02d"),P.Kills,P.Deaths,Seconds/60,Seconds%60);
    }
    return TEXT("武芸稽古を準備しています…");
}
FString USoraPracticeDirector::ObjectiveTextEnglish() const
{
    const auto* K=Mode().Kernel();
    if(K&&K->PracticePlayers.Num()>0)
    {
        const auto& P=K->PracticePlayers[0];
        const int32 Seconds=FMath::Max(0,36000-static_cast<int32>(K->PracticeTick)+59)/60;
        return FString::Printf(TEXT("Practice / Kills %d  Deaths %d / %02d:%02d left"),
            P.Kills,P.Deaths,Seconds/60,Seconds%60);
    }
    return TEXT("Preparing practice...");
}
