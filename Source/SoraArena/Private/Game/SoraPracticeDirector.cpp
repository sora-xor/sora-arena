#include "SoraPracticeDirector.h"
#include "ArenaKernelSubsystem.h"
#include "Combat/SoraDamage.h"
#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraGameEvents.h"
#include "SoraGameMode.h"
#include "SoraPlayerCharacter.h"
#include "SoraPracticeActors.h"
#include "SoraPracticePawn.h"
#include "SoraWorldBuilder.h"
#include "HUD/SoraPracticeText.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/Controller.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PlayerInput.h"
#include "arena.h"

namespace
{
// A kernel state farther than this from the last one is a respawn or other
// jump, not motion: it is shown at once rather than slid across the arena.
// A Shinobi dash covers 200 cm in one tick and is still drawn as motion.
constexpr float TeleportCentimetres = 260.f;
constexpr int32 FeedLength = 8;
FString MatchClock(uint32 Ticks)
{
    const int32 Seconds=static_cast<int32>(Ticks+59)/60;
    return FString::Printf(TEXT("%02d:%02d"),Seconds/60,Seconds%60);
}
float LerpYaw(float From,float To,float Alpha)
{
    return From+FMath::FindDeltaAngleDegrees(From,To)*Alpha;
}
}

USoraPracticeDirector::USoraPracticeDirector()
{
    // ASoraGameMode steps the kernel from its own tick; this component's
    // tick only drives the spectator camera, which also runs after the match.
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.bStartWithTickEnabled=true;
}
ASoraGameMode& USoraPracticeDirector::Mode() const { return *CastChecked<ASoraGameMode>(GetOwner()); }
ASoraCharacterBase* USoraPracticeDirector::Participant(int32 Slot) const { return Pawns.IsValidIndex(Slot)?Pawns[Slot].Get():nullptr; }
int32 USoraPracticeDirector::LoadoutWeapon(int32 ClassId,int32 LoadoutIndex)
{
    if(ClassId<0||ClassId>=SoraPractice::ClassCount) return INDEX_NONE;
    return LoadoutIndex==0?2*ClassId+1:LoadoutIndex==1?2*ClassId:LoadoutIndex==2?SoraPractice::SpecialOf(ClassId):INDEX_NONE;
}
int32 USoraPracticeDirector::LoadoutIndexOf(int32 ClassId,int32 WeaponId)
{
    for(int32 Index=0;Index<3;++Index) if(LoadoutWeapon(ClassId,Index)==WeaponId) return Index;
    return INDEX_NONE;
}
bool USoraPracticeDirector::IsSoraSide(int32 Slot) const
{
    const auto* K=Mode().Kernel();
    if(SoraPractice::IsTeamMode(Config.Mode)) return K&&K->PracticePlayers.IsValidIndex(Slot)?K->PracticePlayers[Slot].Team==0:Slot%2==0;
    return Slot==0;
}
bool USoraPracticeDirector::UsesAlienBody(int32 Slot) const
{
    // Team modes pit the Sora League against the Stellar Credit House; in a
    // free-for-all every other seat is an invader.
    return SoraPractice::IsTeamMode(Config.Mode)?!IsSoraSide(Slot):Slot%2==1;
}
FLinearColor USoraPracticeDirector::ParticipantColor(int32 Slot) const
{
    if(SoraPractice::IsTeamMode(Config.Mode)) return SoraPracticeArt::TeamColor(IsSoraSide(Slot)?0:1);
    return SoraPracticeArt::SlotColor(Slot);
}
FLinearColor USoraPracticeDirector::TracerColor(int32 Slot) const
{
    // Every shot in its shooter's colour: the League's vermillion for the
    // player's side, never the Credit House's cyan.
    return ParticipantColor(Slot);
}
bool USoraPracticeDirector::ShowsScoreboard() const
{
    const auto* K=Mode().Kernel();
    const ASoraPlayerCharacter* Player=Mode().Hero();
    return K&&K->PracticeActive()&&!K->PracticeTerminal&&Player&&Player->IsScoreboardHeld();
}
void USoraPracticeDirector::Clear()
{
    ASoraGameMode& M=Mode();
    if(auto* K=M.Kernel()) K->StopPractice();
    for(int32 I=1;I<Pawns.Num();++I) if(IsValid(Pawns[I])) Pawns[I]->Destroy();
    Pawns.Reset();
    for(auto& Item:ProjectileActors) if(IsValid(Item.Value)) Item.Value->Destroy();
    for(auto& Item:Entities) if(IsValid(Item.Value)) Item.Value->Destroy();
    ProjectileActors.Reset(); Entities.Reset(); ProjectilePrevious.Reset(); ProjectileCurrent.Reset();
    for(AActor* Actor:{static_cast<AActor*>(ControlActor.Get()),static_cast<AActor*>(PayloadActor.Get()),Dressing.Get()}) if(IsValid(Actor)) Actor->Destroy();
    ControlActor=nullptr; PayloadActor=nullptr; Dressing=nullptr;
    // The hero outlives the match: every banner component goes, scene roots too.
    for(const auto& Part:HeroBanner) if(IsValid(Part)) Part->DestroyComponent();
    HeroBanner.Reset(); Previous.Reset(); Current.Reset(); FeedEntries.Reset(); FinalResults=FSoraPracticeResults();
    Clock.Reset();
    ASoraPlayerCharacter* Player=M.Hero();
    if(bSpectating&&Player)
        if(auto* Controller=Cast<APlayerController>(Player->GetController())) Controller->SetViewTarget(Player);
    bSpectating=false; SpectatorTarget=INDEX_NONE; LastKiller=INDEX_NONE;
    if(IsValid(Spectator)) Spectator->Destroy();
    Spectator=nullptr;
    if(Player) Player->SetKernelDriven(false);
}
bool USoraPracticeDirector::StartPractice(const FSoraPracticeConfig& NewConfig)
{
    ASoraGameMode& M=Mode();
    auto* K=M.Kernel();
    FString Why,WhyEnglish;
    if(!K||!K->ValidatePractice(NewConfig,&Why,&WhyEnglish))
    {
        M.Notice=K?Why:TEXT("戦闘カーネルを利用できません。");
        M.NoticeEnglish=K?WhyEnglish:TEXT("The combat kernel is unavailable.");
        M.NoticeTime=8.f;
        return false;
    }
    Config=NewConfig;
    M.SelectedClass=Config.ClassId; M.MapId=Config.MapId;
    M.bDeterministicPractice=true; M.bCampaign=false;
    return Reset();
}
bool USoraPracticeDirector::Reset()
{
    ASoraGameMode& M=Mode();
    ASoraWorldBuilder* WorldBuilder=M.Arena();
    if(!WorldBuilder||!FSoraCatalog::Get().IsReady())
    {
        M.Notice=TEXT("稽古の舞台またはコンテンツを準備できません。");
        M.NoticeEnglish=TEXT("Practice needs the content catalog and an initialized arena."); M.SetMenuOpen(true); return false;
    }
    M.bConfirmNewCampaign=false; M.TitleCardTime=0.f;
    Clear();
    auto* K=M.Kernel();
    // The menu's class and arena choice follow the game mode; a special stays
    // the chosen class's own, and Melee drops one that is not a blade.
    Config.ClassId=FMath::Clamp(M.SelectedClass,0,SoraPractice::ClassCount-1);
    Config.MapId=FMath::Clamp(M.MapId,0,SoraPractice::MapCount-1);
    if(Config.SpecialWeaponId!=INDEX_NONE)
    {
        Config.SpecialWeaponId=SoraPractice::SpecialOf(Config.ClassId);
        if(K&&!K->ValidatePractice(Config)) Config.SpecialWeaponId=INDEX_NONE;
    }
    if(!K||!K->StartPractice(Config))
    {
        M.Notice=K?K->PracticeError:TEXT("戦闘カーネルを利用できません。");
        M.NoticeEnglish=K&&!K->PracticeErrorEnglish.IsEmpty()?K->PracticeErrorEnglish:TEXT("The real Rust library must be staged and validated before practice can start.");
        M.SetMenuOpen(true); return false;
    }
    M.Campaign()->ClearEncounter();
    M.bDefeated=false; M.bChapterComplete=false; M.RoundTime=0; bSlowed=false;
    WorldBuilder->BuildPractice(Config.MapId,K->PracticeMap);
    ASoraPlayerCharacter* Player=M.Hero();
    if(!Player) { K->StopPractice(); M.Notice=TEXT("稽古のプレイヤーを作成できません。"); M.NoticeEnglish=TEXT("The practice player could not be created."); M.SetMenuOpen(true); return false; }
    // The campaign round that ran before may have left chapter one's bokken or
    // Nyaakoto's loadout on the hero; practice holds the kernel's weapon.
    Player->SetDojoTraining(false); Player->SetCampaignHeroLoadout(false);
    Player->ApplyClass(Config.ClassId); Player->SetKernelDriven(true,&K->PracticeMap); Pawns.Add(Player);
    // Others see the hero's banner; the hero never does.
    TArray<USceneComponent*> Banner;
    SoraPracticeArt::Sashimono(Player,Player->GetCapsuleComponent(),K->PracticeMap.PlayerHalfHeight,ParticipantColor(0),true,true,&Banner);
    for(USceneComponent* Part:Banner) HeroBanner.Add(Part);
    for(int32 Slot=1;Slot<K->PracticePlayers.Num();++Slot)
    {
        FActorSpawnParameters Params; Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        auto* Pawn=GetWorld()->SpawnActor<ASoraPracticePawn>(K->PracticePlayers[Slot].Feet,FRotator::ZeroRotator,Params);
        Pawn->InitParticipant(Slot,K->PracticeMap,ParticipantColor(Slot),IsSoraSide(Slot),UsesAlienBody(Slot));
        Pawns.Add(Pawn);
    }
    BuildModeDressing();
    if(Config.Mode==SoraPractice::Control)
    {
        ControlActor=GetWorld()->SpawnActor<ASoraPracticeControlPoint>();
        ControlActor->Build(K->PracticeMap);
    }
    else if(Config.Mode==SoraPractice::Payload)
    {
        PayloadActor=GetWorld()->SpawnActor<ASoraPracticePayload>();
        PayloadActor->Build(K->PracticeMap);
    }
    Current=K->PracticePlayers; Previous=Current;
    PayloadCurrent=PayloadPrevious=K->PracticeObjective.PayloadPosition;
    RespawnClass=Config.ClassId;
    RespawnLoadout=FMath::Max(0,LoadoutIndexOf(Config.ClassId,K->PracticePlayers[0].WeaponId));
    bRespawnChoiceMade=false;
    UpdatePresentation(); UpdateEntities(); UpdateObjective(); PresentFrame();
    if(Player->GetController()) Player->GetController()->SetControlRotation(K->PracticePlayers[0].Aim);
    const SoraPracticeText::FLine Name=SoraPracticeText::ModeName(Config.Mode);
    M.Notice=FString::Printf(TEXT("武芸稽古「%s」%d 人。左クリック射撃、右クリック近接、R 装填、Ctrl 防御、Q 技、Space 跳躍、Tab 戦況表。倒れたら 1・2・3 で武器、Q・E で流儀を選べます。XOR は預けません。"),
        *Name.Japanese,Config.PlayerCount);
    M.NoticeEnglish=FString::Printf(TEXT("Offline practice, %s with %d players: fire, melee, R reload, Ctrl block, Q ability, Space jump, Tab scoreboard. While down, 1/2/3 choose a weapon and Q/E a class. No XOR is bonded."),
        *Name.English,Config.PlayerCount);
    M.NoticeTime=12.f;
    return true;
}
void USoraPracticeDirector::BuildModeDressing()
{
    // Spawn pads for this mode, flat on the floor: each team's six pads in
    // its colour with its kamon, or the free-for-all stones.
    const auto* K=Mode().Kernel();
    Dressing=GetWorld()->SpawnActor<AActor>();
    auto* Root=NewObject<USceneComponent>(Dressing,TEXT("PracticeModeDressing"));
    Dressing->SetRootComponent(Root); Root->RegisterComponent(); Dressing->AddInstanceComponent(Root);
    const FSoraPracticeMap& Map=K->PracticeMap;
    if(SoraPractice::IsTeamMode(Config.Mode))
        for(int32 Team=0;Team<2;++Team)
            for(int32 Index=0;Index<Map.TeamSpawns[Team].Num();++Index)
            {
                const FSoraPracticeSpawn& Spawn=Map.TeamSpawns[Team][Index];
                const FString Name=FString::Printf(TEXT("SpawnPad%d_%d"),Team,Index);
                SoraPracticeArt::Surface(SoraPracticeArt::Part(Dressing,Root,Name,SoraPracticeArt::Cube,Spawn.Feet+FVector(0,0,.8f),FVector(1.5f,1.5f,.016f),FRotator(0,Spawn.Yaw,0)),
                    TEXT("Stone"),SoraPracticeArt::TeamColor(Team)*.9f+FLinearColor(.25f,.25f,.25f));
                SoraPracticeArt::Kamon(Dressing,Root,Name+TEXT("Kamon"),Spawn.Feet+FVector(0,0,1.7f),FRotator(90,Spawn.Yaw,0),70.f,1.2f,Team==0,
                    Team==0?FLinearColor(.93f,.9f,.84f):FLinearColor(.035f,.038f,.045f));
            }
    else
        for(int32 Index=0;Index<Map.FreeForAllSpawns.Num();++Index)
        {
            const FSoraPracticeSpawn& Spawn=Map.FreeForAllSpawns[Index];
            SoraPracticeArt::Surface(SoraPracticeArt::Part(Dressing,Root,FString::Printf(TEXT("SpawnStone%d"),Index),SoraPracticeArt::Cylinder,Spawn.Feet+FVector(0,0,.8f),FVector(1.2f,1.2f,.016f)),
                TEXT("Stone"),FLinearColor(.72f,.7f,.66f));
        }
}
void USoraPracticeDirector::TickComponent(float DeltaSeconds,ELevelTick TickType,FActorComponentTickFunction* ThisTickFunction)
{
    Super::TickComponent(DeltaSeconds,TickType,ThisTickFunction);
    const auto* K=Mode().Kernel();
    if(K&&K->PracticeActive()&&Mode().bDeterministicPractice&&Pawns.Num()>0) UpdateSpectator(DeltaSeconds);
}
void USoraPracticeDirector::Step(float Dt)
{
    ASoraGameMode& M=Mode();
    auto* K=M.Kernel(); ASoraPlayerCharacter* Player=M.Hero();
    if(!K||!K->PracticeActive()||!Player) { M.SetMenuOpen(true); return; }
    PollRespawnInput();
    const int32 Steps=Clock.Advance(Dt); bSlowed=Clock.Slowed;
    for(int32 Count=0;Count<Steps;++Count)
    {
        // A refused tick has already ended the kernel session, so closing the
        // menu cannot resume it; Enter starts a fresh match.
        if(!K->StepPractice(PlayerInput()))
        {
            M.Notice=K->PracticeError.IsEmpty()?TEXT("戦闘カーネルが稽古の更新を拒否しました。処理を停止しました。"):K->PracticeError;
            M.NoticeEnglish=K->PracticeErrorEnglish.IsEmpty()?TEXT("The reference kernel rejected the practice update. Simulation stopped."):K->PracticeErrorEnglish;
            M.SetMenuOpen(true); return;
        }
        UpdatePresentation(); UpdateEntities(); UpdateObjective(); PresentEvents();
        if(K->PracticeTerminal)
        {
            CaptureResults();
            M.bChapterComplete=true; M.Notice=TEXT("稽古の決着がつきました。Enter でもう一度。");
            M.NoticeEnglish=TEXT("The practice match is decided. Press Enter to play again."); M.NoticeTime=0.f; break;
        }
    }
    PresentFrame();
    M.RoundTime=K->PracticeTick/60.f; M.NoticeTime=FMath::Max(0.f,M.NoticeTime-Dt);
}
FSoraPracticeInput USoraPracticeDirector::PlayerInput()
{
    auto* K=Mode().Kernel();
    FSoraPracticeInput Input=Mode().Hero()->ConsumeKernelInput();
    if(!K->PracticePlayers.IsValidIndex(0)) return Input;
    const FSoraPracticePlayer& Me=K->PracticePlayers[0];
    if(Me.Alive||Me.Exhausted||!bRespawnChoiceMade) return Input;
    // Down: the chosen loadout rides on the LOADOUT bit until the kernel holds it.
    const int32 Weapon=LoadoutWeapon(RespawnClass,RespawnLoadout);
    const bool bHeld=Me.PendingClass==RespawnClass&&Me.PendingWeapon==Weapon;
    const bool bAlready=Me.PendingClass==INDEX_NONE&&Me.ClassId==RespawnClass&&Me.WeaponId==Weapon;
    if(!bHeld&&!bAlready&&CanSelectLoadout(RespawnClass,RespawnLoadout))
    {
        Input.Buttons=ARENA_BUTTON_LOADOUT; Input.Forward=static_cast<int16>(RespawnClass); Input.Right=static_cast<int16>(RespawnLoadout);
    }
    return Input;
}
bool USoraPracticeDirector::CanSelectLoadout(int32 ClassId,int32 LoadoutIndex) const
{
    const auto* K=Mode().Kernel();
    if(!K||K->PracticePlayers.IsEmpty()||ClassId<0||ClassId>=SoraPractice::ClassCount||LoadoutIndex<0||LoadoutIndex>2) return false;
    // combat-rules §10: the special only if admitted for this class; Melee only blades.
    if(LoadoutIndex==2&&K->PracticePlayers[0].AdmittedSpecial!=SoraPractice::SpecialOf(ClassId)) return false;
    if(Config.Mode==SoraPractice::Melee&&LoadoutIndex==0) return false;
    return true;
}
bool USoraPracticeDirector::SelectRespawnLoadout(int32 ClassId,int32 LoadoutIndex)
{
    if(!CanSelectLoadout(ClassId,LoadoutIndex)) return false;
    RespawnClass=ClassId; RespawnLoadout=LoadoutIndex; bRespawnChoiceMade=true;
    return true;
}
void USoraPracticeDirector::PollRespawnInput()
{
    const auto* K=Mode().Kernel();
    ASoraPlayerCharacter* Player=Mode().Hero();
    auto* Controller=Player?Cast<APlayerController>(Player->GetController()):nullptr;
    // The player's own bindings for these actions, read directly while the
    // body is down and its combat handlers ignore them. A press counts once,
    // when a bound key goes down between two polls.
    static const TCHAR* const Actions[]={TEXT("WeaponOne"),TEXT("WeaponTwo"),TEXT("WeaponThree"),TEXT("Ability"),TEXT("Interact"),
        TEXT("CampaignWeaponNext"),TEXT("Fire"),TEXT("Block")};
    uint32 Held=0;
    if(Controller&&Controller->PlayerInput)
        for(int32 Index=0;Index<UE_ARRAY_COUNT(Actions);++Index)
            for(const FInputActionKeyMapping& Mapping:Controller->PlayerInput->GetKeysForAction(Actions[Index]))
                if(Controller->PlayerInput->IsPressed(Mapping.Key)) Held|=1u<<Index;
    const uint32 Pressed=Held&~HeldActions;
    HeldActions=Held;
    if(!Pressed||K->PracticePlayers.IsEmpty()||K->PracticePlayers[0].Alive) return;
    for(int32 Index=0;Index<3;++Index) if(Pressed&(1u<<Index)) SelectRespawnLoadout(RespawnClass,Index);
    const int32 Turn=(Pressed&(1u<<3))?-1:(Pressed&((1u<<4)|(1u<<5)))?1:0;
    if(Turn!=0)
    {
        const int32 Class=(RespawnClass+Turn+SoraPractice::ClassCount)%SoraPractice::ClassCount;
        // Keep the loadout if the new class can hold it; else its first allowed one.
        if(!SelectRespawnLoadout(Class,RespawnLoadout)&&!SelectRespawnLoadout(Class,0)) SelectRespawnLoadout(Class,1);
    }
    if(Pressed&(1u<<6)) CycleSpectator(1);
    if(Pressed&(1u<<7)) CycleSpectator(-1);
}
void USoraPracticeDirector::UpdatePresentation()
{
    auto* K=Mode().Kernel(); if(!K) return;
    Previous=Current; Current=K->PracticePlayers;
    if(Previous.Num()!=Current.Num()) Previous=Current;
    for(int32 Slot=0;Slot<Current.Num();++Slot)
    {
        // A respawn or other jump is shown at once, not slid across the arena.
        if(Previous[Slot].Alive!=Current[Slot].Alive||FVector::Dist(Previous[Slot].Feet,Current[Slot].Feet)>TeleportCentimetres)
            Previous[Slot]=Current[Slot];
        if(Pawns.IsValidIndex(Slot)&&IsValid(Pawns[Slot])) Pawns[Slot]->ApplyKernelPlayer(Current[Slot]);
    }
    ProjectilePrevious=MoveTemp(ProjectileCurrent); ProjectileCurrent.Reset();
    for(const auto& P:K->PracticeProjectiles)
    {
        ProjectileCurrent.Add(P.Id,P.Position);
        auto* Actor=ProjectileActors.FindRef(P.Id).Get();
        if(!IsValid(Actor))
        {
            Actor=GetWorld()->SpawnActor<AActor>();
            auto* Mesh=ASoraWorldBuilder::Shape(Actor,nullptr,TEXT("KernelProjectile"),TEXT("/Engine/BasicShapes/Sphere.Sphere"),FVector::ZeroVector,FVector(.15),FLinearColor(1,.35,.07));
            Actor->SetRootComponent(Mesh); ProjectileActors.Add(P.Id,Actor);
            ProjectilePrevious.Add(P.Id,P.Position);
        }
    }
    for(auto It=ProjectileActors.CreateIterator();It;++It) if(!ProjectileCurrent.Contains(It.Key()))
    {
        if(IsValid(It.Value())) It.Value()->Destroy(); It.RemoveCurrent();
    }
    PayloadPrevious=PayloadCurrent; PayloadCurrent=K->PracticeObjective.PayloadPosition;
    if(FVector::Dist(PayloadPrevious,PayloadCurrent)>TeleportCentimetres) PayloadPrevious=PayloadCurrent;
}
void USoraPracticeDirector::UpdateEntities()
{
    auto* K=Mode().Kernel(); if(!K) return;
    TSet<uint32> Live;
    for(const FSoraPracticeEntity& Entity:K->PracticeEntities)
    {
        Live.Add(Entity.Id);
        ASoraPracticeEntityActor* Actor=Entities.FindRef(Entity.Id).Get();
        if(!IsValid(Actor))
        {
            FActorSpawnParameters Params; Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
            Actor=GetWorld()->SpawnActor<ASoraPracticeEntityActor>(Entity.Position,FRotator::ZeroRotator,Params);
            Entities.Add(Entity.Id,Actor);
        }
        const FSoraPracticePlayer* Owner=K->PracticePlayers.IsValidIndex(Entity.Owner)?&K->PracticePlayers[Entity.Owner]:nullptr;
        Actor->Present(Entity,ParticipantColor(Entity.Owner),IsSoraSide(Entity.Owner),Owner,UsesAlienBody(Entity.Owner),K->PracticeMap);
    }
    for(auto It=Entities.CreateIterator();It;++It) if(!Live.Contains(It.Key()))
    {
        if(IsValid(It.Value())) It.Value()->Destroy(); It.RemoveCurrent();
    }
}
void USoraPracticeDirector::UpdateObjective()
{
    const auto* K=Mode().Kernel(); if(!K) return;
    if(ControlActor) ControlActor->Present(K->PracticeObjective,K->PracticeTick);
}
float USoraPracticeDirector::InterpolationAlpha() const
{
    return FMath::Clamp(static_cast<float>(Clock.Accumulator/FSoraPracticeClock::StepSeconds),0.f,1.f);
}
FVector USoraPracticeDirector::PresentedFeet(int32 Slot) const
{
    if(!Current.IsValidIndex(Slot)) return FVector::ZeroVector;
    if(!Previous.IsValidIndex(Slot)) return Current[Slot].Feet;
    return FMath::Lerp(Previous[Slot].Feet,Current[Slot].Feet,InterpolationAlpha());
}
void USoraPracticeDirector::PresentFrame()
{
    const auto* K=Mode().Kernel(); if(!K) return;
    // The kernel steps at 60 Hz; the screen may run faster or slower. Each
    // frame draws bodies, projectiles and the cart between the last two states.
    const float Alpha=InterpolationAlpha();
    for(int32 Slot=0;Slot<Current.Num()&&Slot<Pawns.Num();++Slot)
    {
        ASoraCharacterBase* Pawn=Pawns[Slot];
        if(!IsValid(Pawn)||!Previous.IsValidIndex(Slot)) continue;
        const FVector Feet=FMath::Lerp(Previous[Slot].Feet,Current[Slot].Feet,Alpha);
        const float Yaw=LerpYaw(Previous[Slot].Aim.Yaw,Current[Slot].Aim.Yaw,Alpha);
        Pawn->SetActorLocationAndRotation(Feet+FVector(0,0,Pawn->GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight()),FRotator(0,Yaw,0),false,nullptr,ETeleportType::TeleportPhysics);
    }
    for(auto& Item:ProjectileActors)
        if(IsValid(Item.Value))
        {
            const FVector* From=ProjectilePrevious.Find(Item.Key); const FVector* To=ProjectileCurrent.Find(Item.Key);
            if(To) Item.Value->SetActorLocation(From?FMath::Lerp(*From,*To,Alpha):*To);
        }
    if(PayloadActor) PayloadActor->Present(K->PracticeObjective,FMath::Lerp(PayloadPrevious,PayloadCurrent,Alpha));
}
void USoraPracticeDirector::AddFeed(const FSoraPracticeFeedEntry& Entry)
{
    FeedEntries.Add(Entry);
    if(FeedEntries.Num()>FeedLength) FeedEntries.RemoveAt(0,FeedEntries.Num()-FeedLength);
}
void USoraPracticeDirector::PresentEvents()
{
    ASoraGameMode& M=Mode();
    auto* K=M.Kernel(); if(!K) return;
    USoraGameEvents* Events=USoraGameEvents::Get(this);
    TSet<int32> Scorched;
    for(const auto& Event:K->PracticeEvents)
    {
        FSoraPracticeFeedEntry Feed; Feed.Tick=K->PracticeTick; Feed.Actor=Event.Actor; Feed.Target=Event.Target; Feed.WeaponId=Event.WeaponId;
        switch(Event.Kind)
        {
        case ARENA_EVENT_SHOT:
            if(Event.WeaponKind!=2)
            {
                FCollisionQueryParams Query(SCENE_QUERY_STAT(KernelVisualRay),false);
                if(Pawns.IsValidIndex(Event.Actor)) Query.AddIgnoredActor(Pawns[Event.Actor]);
                FHitResult Hit; GetWorld()->LineTraceSingleByChannel(Hit,Event.From,Event.To,ECC_Visibility,Query);
                // Cosmetic clipping only. Damage/hit markers are driven by kernel damage events.
                SoraDamage::Beam(GetWorld(),Event.From,Hit.bBlockingHit?Hit.ImpactPoint:Event.To,TracerColor(Event.Actor),1.3f,.065f);
            }
            break;
        case ARENA_EVENT_DAMAGE:
            if(Pawns.Num()>0)
            {
                if(Event.Actor==0) Pawns[0]->HitMarkerTime=.14f;
                if(Event.Target==0) Pawns[0]->DamageFlash=.3f;
            }
            break;
        case ARENA_EVENT_HAZARD_DAMAGE:
            Scorched.Add(Event.Target);
            if(Event.Target==0&&Pawns.Num()>0) Pawns[0]->DamageFlash=.3f;
            break;
        case ARENA_EVENT_DEATH:
            Feed.Kind=Event.Actor!=INDEX_NONE?FSoraPracticeFeedEntry::Kill:Scorched.Contains(Event.Target)?FSoraPracticeFeedEntry::Hazard:FSoraPracticeFeedEntry::Fall;
            // The kernel's death event names no weapon; a kill shows the one
            // the killer held on this tick, which changes only at respawn.
            Feed.WeaponId=Event.Actor!=INDEX_NONE&&K->PracticePlayers.IsValidIndex(Event.Actor)?K->PracticePlayers[Event.Actor].WeaponId:INDEX_NONE;
            AddFeed(Feed);
            if(Event.Target==0)
            {
                LastKiller=Event.Actor;
                RespawnClass=K->PracticePlayers[0].ClassId;
                RespawnLoadout=FMath::Max(0,LoadoutIndexOf(RespawnClass,K->PracticePlayers[0].WeaponId));
                bRespawnChoiceMade=false;
            }
            break;
        case ARENA_EVENT_RESPAWN:
            if(Event.Target==0)
            {
                M.Notice=TEXT("復帰しました。稽古を続けましょう。"); M.NoticeEnglish=TEXT("Respawned. Practice continues."); M.NoticeTime=3.f;
            }
            break;
        case ARENA_EVENT_OBJECTIVE_CAPTURED:
            Feed.Kind=FSoraPracticeFeedEntry::Captured; Feed.Detail=Event.Detail; AddFeed(Feed);
            break;
        case ARENA_EVENT_OVERTIME:
            Feed.Kind=FSoraPracticeFeedEntry::Overtime; AddFeed(Feed);
            break;
        case ARENA_EVENT_CHECKPOINT:
            Feed.Kind=FSoraPracticeFeedEntry::Checkpoint; Feed.Detail=Event.Detail; AddFeed(Feed);
            break;
        case ARENA_EVENT_MATCH_WINNER:
            Feed.Kind=FSoraPracticeFeedEntry::Winner; Feed.Detail=Event.Detail; Feed.Actor=Event.Value; AddFeed(Feed);
            break;
        default: break;
        }
        if(Events) Events->OnKernelEvent.Broadcast(Event,K->PracticeTick);
    }
}
void USoraPracticeDirector::CaptureResults()
{
    const auto* K=Mode().Kernel(); if(!K) return;
    FSoraPracticeResults& R=FinalResults;
    const FSoraPracticeObjective& O=K->PracticeObjective;
    R.bValid=true; R.Tick=K->PracticeTick; R.Mode=Config.Mode; R.WinnerKind=O.WinnerKind; R.WinnerValue=O.WinnerValue;
    R.Score[0]=O.Score[0]; R.Score[1]=O.Score[1]; R.ScoreTarget=O.ScoreTarget; R.Checkpoints=O.PayloadCheckpoints;
    R.PayloadProgress=O.PayloadProgress; R.PayloadLength=O.PayloadLength;
    R.Players=K->PracticePlayers; R.Deposited=K->PracticeDeposited; R.Remaining=K->PracticeRemaining; R.Earnings=K->PracticeEarnings;
    R.bConserved=R.Deposited==R.Remaining+R.Earnings&&R.Deposited==0;
    for(const FSoraPracticePlayer& Player:R.Players)
        R.bConserved&=Player.InitialBond==0&&Player.RemainingBond==0&&Player.Earnings==0;
}
void USoraPracticeDirector::CycleSpectator(int32 Direction)
{
    const auto* K=Mode().Kernel();
    if(!K) return;
    const int32 Count=K->PracticePlayers.Num();
    int32 Slot=SpectatorTarget;
    for(int32 Tries=0;Tries<Count;++Tries)
    {
        Slot=((Slot<0?0:Slot)+(Direction>=0?1:-1)+Count)%Count;
        if(Slot!=0&&K->PracticePlayers[Slot].Alive) { SpectatorTarget=Slot; return; }
    }
}
void USoraPracticeDirector::UpdateSpectator(float DeltaSeconds)
{
    const auto* K=Mode().Kernel();
    ASoraPlayerCharacter* Player=Mode().Hero();
    auto* Controller=Player?Cast<APlayerController>(Player->GetController()):nullptr;
    if(!K||!Controller||K->PracticePlayers.IsEmpty()) return;
    const FSoraPracticePlayer& Me=K->PracticePlayers[0];
    const bool bOver=K->PracticeTerminal;
    const bool bWant=bOver||!Me.Alive||Me.Exhausted;
    if(bWant!=bSpectating)
    {
        bSpectating=bWant;
        if(bWant)
        {
            if(!IsValid(Spectator))
            {
                Spectator=GetWorld()->SpawnActor<ACameraActor>(Player->GetActorLocation()+FVector(0,0,K->PracticeMap.EyeHeight),Controller->GetControlRotation());
                Spectator->GetCameraComponent()->bConstrainAspectRatio=false;
                Spectator->GetCameraComponent()->SetFieldOfView(90.f);
            }
            // First the one who struck the player down, if still standing.
            SpectatorTarget=K->PracticePlayers.IsValidIndex(LastKiller)&&LastKiller!=0&&K->PracticePlayers[LastKiller].Alive?LastKiller:INDEX_NONE;
            if(SpectatorTarget==INDEX_NONE) CycleSpectator(1);
            Controller->SetViewTarget(Spectator);
        }
        else
        {
            SpectatorTarget=INDEX_NONE;
            Controller->SetViewTarget(Player);
            Controller->SetControlRotation(Me.Aim);
        }
    }
    if(!bSpectating||!IsValid(Spectator)) return;
    FVector Location; FRotator Rotation;
    if(bOver)
    {
        // The match is over: circle the arena above the objective.
        SpectatorOrbit=FMath::Fmod(SpectatorOrbit+DeltaSeconds*6.f,360.f);
        const FVector Center=Config.Mode==SoraPractice::Payload?PayloadCurrent:K->PracticeMap.ControlCenter;
        const float Reach=.42f*FMath::Min(K->PracticeMap.Maximum.X-K->PracticeMap.Minimum.X,K->PracticeMap.Maximum.Y-K->PracticeMap.Minimum.Y);
        Location=Center+FRotator(0,SpectatorOrbit,0).Vector()*Reach+FVector(0,0,1100.f);
        Rotation=(Center-Location).Rotation();
    }
    else
    {
        if(!K->PracticePlayers.IsValidIndex(SpectatorTarget)||!K->PracticePlayers[SpectatorTarget].Alive) CycleSpectator(1);
        if(!K->PracticePlayers.IsValidIndex(SpectatorTarget)||!K->PracticePlayers[SpectatorTarget].Alive) return;
        // Over the followed participant's shoulder, pulled in by walls.
        const FVector Eye=PresentedFeet(SpectatorTarget)+FVector(0,0,K->PracticeMap.EyeHeight);
        const FRotator Aim(0,Current.IsValidIndex(SpectatorTarget)?Current[SpectatorTarget].Aim.Yaw:0.f,0);
        const FVector Desired=Eye-Aim.Vector()*280.f+FVector(0,0,70.f);
        FCollisionQueryParams Query(SCENE_QUERY_STAT(PracticeSpectator),false);
        for(const auto& Pawn:Pawns) if(IsValid(Pawn)) Query.AddIgnoredActor(Pawn);
        FHitResult Hit;
        Location=GetWorld()->LineTraceSingleByChannel(Hit,Eye,Desired,ECC_Visibility,Query)?Hit.Location+(Eye-Desired).GetSafeNormal()*20.f:Desired;
        Rotation=(Eye+Aim.Vector()*500.f-Location).Rotation();
    }
    const float Blend=FMath::Clamp(DeltaSeconds*8.f,0.f,1.f);
    Spectator->SetActorLocationAndRotation(FMath::Lerp(Spectator->GetActorLocation(),Location,Blend),FMath::Lerp(Spectator->GetActorRotation(),Rotation,Blend));
}
FString USoraPracticeDirector::ObjectiveText() const
{
    const auto* K=Mode().Kernel();
    if(!K||K->PracticePlayers.IsEmpty()) return TEXT("武芸稽古を準備しています…");
    const auto& P=K->PracticePlayers[0];
    const FString Left=MatchClock(SoraPractice::MatchTicks-FMath::Min(K->PracticeTick,SoraPractice::MatchTicks));
    const FSoraPracticeObjective& O=K->PracticeObjective;
    switch(Config.Mode)
    {
    case SoraPractice::Control:
        return FString::Printf(TEXT("拠点制圧 / 味方 %s  敵 %s（目標 %s）%s/ 残り %s"),*MatchClock(O.Score[0]),*MatchClock(O.Score[1]),*MatchClock(O.ScoreTarget),O.Overtime?TEXT(" 延長戦 "):TEXT(" "),*Left);
    case SoraPractice::Payload:
        return FString::Printf(TEXT("護送 / 進み %d%%  関所 %d / 3 / 残り %s"),FMath::RoundToInt(100.f*O.PayloadProgress/FMath::Max(1.f,O.PayloadLength)),O.PayloadCheckpoints,*Left);
    default:
        return FString::Printf(TEXT("%s / 撃破 %d  戦死 %d / 残り %s"),*SoraPracticeText::ModeName(Config.Mode).Japanese,P.Kills,P.Deaths,*Left);
    }
}
FString USoraPracticeDirector::ObjectiveTextEnglish() const
{
    const auto* K=Mode().Kernel();
    if(!K||K->PracticePlayers.IsEmpty()) return TEXT("Preparing practice...");
    const auto& P=K->PracticePlayers[0];
    const FString Left=MatchClock(SoraPractice::MatchTicks-FMath::Min(K->PracticeTick,SoraPractice::MatchTicks));
    const FSoraPracticeObjective& O=K->PracticeObjective;
    switch(Config.Mode)
    {
    case SoraPractice::Control:
        return FString::Printf(TEXT("Control / Allies %s  Enemies %s (target %s)%s/ %s left"),*MatchClock(O.Score[0]),*MatchClock(O.Score[1]),*MatchClock(O.ScoreTarget),O.Overtime?TEXT(" OVERTIME "):TEXT(" "),*Left);
    case SoraPractice::Payload:
        return FString::Printf(TEXT("Payload / %d%% pushed  Checkpoints %d / 3 / %s left"),FMath::RoundToInt(100.f*O.PayloadProgress/FMath::Max(1.f,O.PayloadLength)),O.PayloadCheckpoints,*Left);
    default:
        return FString::Printf(TEXT("%s / Kills %d  Deaths %d / %s left"),*SoraPracticeText::ModeName(Config.Mode).English,P.Kills,P.Deaths,*Left);
    }
}
