#include "SoraCampaignDirector.h"
#include "Combat/SoraCombatEffects.h"
#include "Combat/SoraDamage.h"
#include "Game/SoraCampaignReach.h"
#include "SoraCampaignRules.h"
#include "SoraCatalog.h"
#include "SoraEnemy.h"
#include "SoraEquipmentComponent.h"
#include "SoraFieldcraft.h"
#include "SoraGameMode.h"
#include "SoraHorse.h"
#include "SoraMountRules.h"
#include "SoraPlayerCharacter.h"
#include "SoraSaveGame.h"
#include "SoraText.h"
#include "SoraWorldBuilder.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"

// The campaign director's world-facing play, in the chapter's space
// (FSoraSpace): the travel cut to a beat's place, its trigger volumes, where
// its objective stands and where opponents enter, the task kit it shows, the
// horse and pack horses of a ride, a siege on defended targets, the escorted
// party, a carried load, loose collectibles and the cinematic camera.

const FSoraBeatSpace* USoraCampaignDirector::ActiveSpace() const
{
    const FSoraBeat* Beat=ActiveBeatData();
    return Beat?&Beat->Space:nullptr;
}
int32 USoraCampaignDirector::HeroZone() const
{
    const FSoraChapter* Chapter=ActiveChapter();
    const ASoraPlayerCharacter* Hero=Mode().Hero();
    return Chapter&&Hero?Chapter->Space.ZoneAt(Hero->GetActorLocation()):-2;
}
bool USoraCampaignDirector::ObjectivePoint(FVector& Location,bool& bInteract) const
{
    const FSoraBeat* Beat=ActiveBeatData();
    if(!Beat||Mode().bChapterComplete) return false;
    if(IsToriiEpilogue()) return EpilogueObjective(Location,bInteract);
    const FSoraBeatSpace& Space=Beat->Space;
    const auto At=[&](const FVector2D& Point,bool bWorks) { Location=ASoraWorldBuilder::Floor(Point); bInteract=bWorks; return true; };
    const auto VolumeOf=[&](const FString& Event) { return Space.Volumes.FindByPredicate([&](const FSoraVolume& Volume) { return Volume.Event==Event; }); };
    if(Task.RecoveryWeapons!=0u&&(NeedsEquipmentRecovery()||AtRecoveryBottom()||IsClimbingRecoveryWell()))
    {
        Location=AtRecoveryBottom()?RecoveryBottom()-FVector(0,0,100):RecoveryApproach()-FVector(0,0,100);
        bInteract=true; return true;
    }
    switch(Task.Goal)
    {
    case SoraBeatRules::EGoal::Lines:
        // Walk-and-talk may have several required stops. Guide them in the
        // script's line order, including a stop before LinesEvent itself
        // (ch01.b10's north gate precedes the engawa conversation).
        for(const int32 Line:Beat->Lines)
        {
            if(FinishedLines.Contains(Line)) continue;
            for(int32 Index=0;Index<ActiveChapter()->Triggers.Num();++Index)
            {
                const FSoraDialogueTrigger& Trigger=ActiveChapter()->Triggers[Index];
                if(Trigger.Beat!=BeatIndex||!Trigger.Lines.Contains(Line)||!TriggerAllowed(Index)) continue;
                for(int32 Volume=0;Volume<Space.Volumes.Num();++Volume)
                    if(!VolumesEntered.Contains(Volume)&&Space.Volumes[Volume].Event==Trigger.On)
                        return At(Space.Volumes[Volume].Center,false);
            }
        }
        if(!bLinesStarted&&Beat->LinesEvent.StartsWith(TEXT("interact:"))) return At(Space.Anchor,true);
        if(!bLinesStarted&&Beat->LinesEvent.StartsWith(TEXT("volume_enter:")))
            if(const FSoraVolume* Volume=VolumeOf(Beat->LinesEvent)) return At(Volume->Center,false);
        return Task.AnchorAfterLines&&TaskState.LinesDone&&!TaskState.Reached&&At(Space.Closing,false);
    case SoraBeatRules::EGoal::WavesCleared:
        // Once the field is clear, the volume that brings the next wave.
        if(LiveWaveOpponents()>0||!Pending.IsEmpty()) return false;
        for(int32 Wave=0;Wave<Task.WaveCount;++Wave)
            if(Task.Waves[Wave].Trigger==SoraBeatRules::EWaveTrigger::Volume&&!SoraBeatRules::Released(TaskState,Wave))
                if(const FSoraVolume* Volume=VolumeOf(Beat->Waves[Wave].Event)) return At(Volume->Center,false);
        return false;
    case SoraBeatRules::EGoal::Objectives:
        for(int32 Objective=0;Objective<Space.Objectives.Num();++Objective)
            if((TaskState.PointsMask&(1u<<Objective))==0u) return At(Space.Objectives[Objective],true);
        return false;
    case SoraBeatRules::EGoal::Deliveries:
        if(Task.Task==SoraBeatRules::ETask::Carry&&!TaskState.Carrying)
        {
            for(int32 Point=0;Point<Space.Pickups.Num();++Point)
                if(Task.Pickups<Task.Count||(TaskState.PointsMask&(1u<<Point))==0u) return At(Space.Pickups[Point],true);
            return false;
        }
        for(int32 Point=0;Point<Space.Dropoffs.Num();++Point)
            if(TaskState.DropoffUses[Point]<SoraBeatRules::DropoffShare(Task)) return At(Space.Dropoffs[Point],true);
        return false;
    case SoraBeatRules::EGoal::Exit:
        return !TaskState.Reached&&At(Space.Exit.Center,false);
    case SoraBeatRules::EGoal::Hold:
        // A guttered cook-fire wants the hero's hand before the hold goes on.
        if(const USoraFieldcraft* Fieldcraft=USoraFieldcraft::Get(this); Fieldcraft&&Fieldcraft->FiresOut()>0)
            for(int32 Fire=0;Fire<Fieldcraft->Active()->Fires.Points.Num();++Fire)
                if(!Fieldcraft->IsFireLit(Fire)) return At(Fieldcraft->Active()->Fires.Points[Fire],true);
        return At(Space.Anchor,false);
    case SoraBeatRules::EGoal::Turns:
        return At(Space.Anchor,true);
    case SoraBeatRules::EGoal::Steps:
        return Space.StepStations.IsValidIndex(TaskState.Step)&&At(Space.Stations[Space.StepStations[TaskState.Step]],true);
    case SoraBeatRules::EGoal::Survive:
        return Task.Task==SoraBeatRules::ETask::Defend&&At(Space.Anchor,true);
    case SoraBeatRules::EGoal::Escort:
        // Before the party can go on the hero's hand is wanted: a cell to
        // open, a collar to cut, one of them to raise.
        if(const USoraFieldcraft* Fieldcraft=USoraFieldcraft::Get(this); Fieldcraft&&Fieldcraft->PartyWork(Location))
        {
            bInteract=true;
            return true;
        }
        Location=PartyLocation(); bInteract=false;
        return true;
    case SoraBeatRules::EGoal::OpponentDown:
        // A yielded boss waits where it knelt for the hero's hand.
        return SoraBeatRules::AwaitsCapture(TaskState,Task)&&At(CaptiveAt,true);
    default:
        return false;
    }
}
FVector USoraCampaignDirector::PartyLocation() const
{
    const FSoraChapter* Chapter=ActiveChapter();
    const FSoraBeatSpace* Space=ActiveSpace();
    if(!Chapter||!Space||!Space->bRoute) return FVector::ZeroVector;
    // The party walks the road from its margin, Progress thousandths of a cm along.
    const FSoraZone& Road=Chapter->Space.Zones[Space->Zone];
    return ASoraWorldBuilder::Floor(Road.PointAlong(Space->RouteMarginCm+TaskState.Progress/1000.f));
}
int32 USoraCampaignDirector::RoadPermille() const
{
    const FSoraChapter* Chapter=ActiveChapter();
    const FSoraBeatSpace* Space=ActiveSpace();
    const ASoraPlayerCharacter* Hero=Mode().Hero();
    if(!Chapter||!Space||!Hero) return 0;
    const FVector At=Hero->GetActorLocation();
    if(Space->bRoute)
    {
        const FSoraZone& Road=Chapter->Space.Zones[Space->Zone];
        return SoraBeatRules::Ratio(FMath::RoundToInt64(Road.ChainageOf(FVector2D(At))),FMath::RoundToInt64(Road.RouteLength));
    }
    // In a zone: the share of the way from the entry to the exit.
    const float Whole=FVector2D::Distance(Space->Entry,Space->Exit.Center);
    return Whole>1.f?FMath::FloorToInt32(1000.f*(1.f-FVector2D::Distance(FVector2D(At),Space->Exit.Center)/Whole)):0;
}
FVector USoraCampaignDirector::SpawnLocation(int32 Slot) const
{
    const FSoraChapter* Chapter=ActiveChapter();
    const FSoraBeatSpace* Space=ActiveSpace();
    const ASoraPlayerCharacter* Hero=Mode().Hero();
    if(!Space||Space->Spawns.IsEmpty()) return Mode().Arena()?Mode().Arena()->SpawnPoint(Slot):FVector::ZeroVector;
    if(Space->bRoute&&Chapter&&Hero)
    {
        // On a road, opponents come from the stretch just ahead of the hero.
        const FSoraZone& Road=Chapter->Space.Zones[Space->Zone];
        const float Here=Road.ChainageOf(FVector2D(Hero->GetActorLocation()));
        TArray<int32> Ahead;
        for(int32 Index=0;Index<Space->Spawns.Num();++Index)
        {
            const float There=Road.ChainageOf(Space->Spawns[Index]);
            if(There>=Here+SoraCampaignReach::RoadSpawnNear&&There<=Here+SoraCampaignReach::RoadSpawnFar) Ahead.Add(Index);
        }
        const int32 Pick=Ahead.IsEmpty()?Space->Spawns.Num()-1:Ahead[Slot%Ahead.Num()];
        return ASoraWorldBuilder::Floor(Space->Spawns[Pick],120.f);
    }
    return ASoraWorldBuilder::Floor(Space->Spawns[FMath::Abs(Slot)%Space->Spawns.Num()],120.f);
}
void USoraCampaignDirector::EnterBeatSpace(bool bResumed)
{
    ASoraGameMode& M=Mode();
    ASoraWorldBuilder* World=M.Arena();
    ASoraPlayerCharacter* Hero=M.Hero();
    const FSoraChapter* Chapter=ActiveChapter();
    const FSoraBeat* Beat=ActiveBeatData();
    if(!World||!Chapter||!Beat||!GetWorld()) return;
    const FSoraBeatSpace& Space=Beat->Space;
    // Travel: a beat in another place than the hero cuts to its entry.
    if(Hero&&Chapter->Space.ZoneAt(Hero->GetActorLocation())!=Space.Zone)
    {
        ClearHorses();
        Hero->GetCharacterMovement()->StopMovementImmediately();
        const FRotator Facing(0,Space.EntryYaw,0);
        Hero->SetActorLocationAndRotation(ASoraWorldBuilder::Floor(Space.Entry,120.f),Facing,false,nullptr,ETeleportType::TeleportPhysics);
        if(AController* Controller=Hero->GetController()) Controller->SetControlRotation(Facing);
        if(APlayerController* Player=Cast<APlayerController>(Hero->GetController()))
            if(Player->PlayerCameraManager&&!bResumed) Player->PlayerCameraManager->StartCameraFade(1.f,0.f,.6f,FLinearColor::Black);
    }
    World->StageKit(*Chapter,BeatIndex);
    LastEscortProgress=0;
    CarryChanged();
    if(Space.bMount&&Hero)
    {
        const FSoraMount& Mount=Space.Mount;
        const FSoraZone* Road=Space.bRoute?&Chapter->Space.Zones[Space.Zone]:nullptr;
        const float Start=Road?Road->ChainageOf(Mount.At):0.f;
        const float Yaw=Road?Road->HeadingAt(Start):Space.EntryYaw;
        FActorSpawnParameters Params; Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        ClearHorses();
        Horse=GetWorld()->SpawnActor<ASoraHorse>(ASoraWorldBuilder::Floor(Mount.At),FRotator(0,Yaw,0),Params);
        if(Horse)
        {
            Horse->Build(Mount.Coat,ASoraHorse::ETack::Riding);
            Horse->SetRide(Mount,Road);
            Horse->Place(ASoraWorldBuilder::Floor(Mount.At),Yaw);
            // A horse to tack up stands bare at the rail; the others come saddled.
            Horse->ShowTack(Mount.Tack.IsEmpty()?Horse->TackPieces():0);
            if(Mount.bMounted&&(Mount.UntilPhase==0||BeatPhase<Mount.UntilPhase)) Horse->Mount(*Hero);
            // A convoy walks the road ahead of the rider, its lead horse first; a
            // laden pack mare follows on a lead rope.
            ASoraHorse* Front=Horse;
            float Ahead=Start+900.f;
            for(int32 Index=Mount.Pack.Num()-1;Index>=0;--Index)
            {
                const FSoraPackHorse& Row=Mount.Pack[Index];
                if(Row.Follow==TEXT("convoy")&&Road)
                {
                    ASoraHorse* Beast=GetWorld()->SpawnActor<ASoraHorse>(ASoraWorldBuilder::Floor(Mount.At),FRotator(0,Yaw,0),Params);
                    if(!Beast) continue;
                    Beast->Build(TEXT("bay"),ASoraHorse::ETack::Pack);
                    Beast->PackId=Row.Id;
                    Beast->FollowRoad(Road,Ahead,Row.SpeedCmS);
                    Ahead+=Row.SpacingCm;
                    Pack.Add(Beast);
                }
            }
            for(const FSoraPackHorse& Row:Mount.Pack)
                if(Row.Follow==TEXT("lead"))
                {
                    const FVector Behind=ASoraWorldBuilder::Floor(Mount.At)-FRotator(0,Yaw,0).Vector()*Row.SpacingCm;
                    ASoraHorse* Beast=GetWorld()->SpawnActor<ASoraHorse>(Behind,FRotator(0,Yaw,0),Params);
                    if(!Beast) continue;
                    Beast->Build(TEXT("bay"),ASoraHorse::ETack::Pack);
                    Beast->Place(Behind,Yaw);
                    Beast->Lead(Front,Row.SpacingCm);
                    Front=Beast;
                    Pack.Add(Beast);
                }
        }
    }
    if(Beat->Is(SoraBeatRules::EType::Cinematic)) StartCinematicCamera();
    ShowKit();
}
void USoraCampaignDirector::LeaveBeatSpace()
{
    const FSoraBeat* Beat=ActiveBeatData();
    if(Beat&&Beat->Is(SoraBeatRules::EType::Cinematic)) EndCinematicCamera(.6f);
    // The beat's lamps, water, face and company leave with it.
    if(USoraFieldcraft* Fieldcraft=USoraFieldcraft::Get(this)) Fieldcraft->Clear();
    // A ride ends at its destination with the rider down on the ground.
    ClearHorses();
    if(ASoraWorldBuilder* World=Mode().Arena())
    {
        World->ClearKit();
        World->ShowCarried(Mode().Hero(),NAME_None);
    }
}
bool USoraCampaignDirector::IsMounted() const
{
    return Horse&&Horse->Rider()&&Horse->Rider()==Mode().Hero();
}
TArray<ASoraHorse*> USoraCampaignDirector::PackHorses() const
{
    TArray<ASoraHorse*> Result;
    for(const auto& Beast:Pack) if(IsValid(Beast)) Result.Add(Beast);
    return Result;
}
void USoraCampaignDirector::Dismount()
{
    if(IsMounted()) Horse->Dismount();
}
void USoraCampaignDirector::ClearHorses()
{
    Dismount();
    if(IsValid(Horse)) Horse->Destroy();
    for(const auto& Beast:Pack) if(IsValid(Beast)) Beast->Destroy();
    Horse=nullptr; Pack.Reset(); Frightening.Reset();
}
void USoraCampaignDirector::TickSpace(int32 DeltaMs)
{
    TickHorses();
    TickSiege(DeltaMs);
    if(ActiveBeatData()&&!Mode().bDefeated) ShowKit();
}
void USoraCampaignDirector::TickVolumes()
{
    const FSoraBeat* Beat=ActiveBeatData();
    const ASoraPlayerCharacter* Hero=Mode().Hero();
    if(!Beat||!Hero) return;
    const FSoraBeatSpace& Space=Beat->Space;
    const FVector At=Hero->GetActorLocation();
    for(int32 Index=0;Index<Space.Volumes.Num();++Index)
    {
        const FSoraVolume& Volume=Space.Volumes[Index];
        if(VolumesEntered.Contains(Index)||!Volume.Contains(At)) continue;
        VolumesEntered.Add(Index);
        // A dialogue waiting on the volume starts; its lines and the waves it
        // names follow the event.
        if(Task.Goal==SoraBeatRules::EGoal::Lines&&!bLinesStarted&&Beat->LinesEvent==Volume.Event) StartLines();
        Fire(Volume.Event);
        ReleaseEventWaves(Volume.Event);
        // A scripted spook on the road (a pheasant flushed from the verge).
        if(IsMounted()&&Space.bMount&&Space.Mount.Spooks.Contains(Volume.Event.RightChop(13)))
        {
            Horse->Spook();
            Fire(TEXT("horse_spooked"));
        }
    }
}
void USoraCampaignDirector::TickHorses()
{
    const FSoraBeatSpace* Space=ActiveSpace();
    const ASoraPlayerCharacter* Hero=Mode().Hero();
    if(!Space||!Hero) return;
    if(IsValid(Horse)&&Space->bMount)
    {
        const FSoraMount& Mount=Space->Mount;
        // A mounted fight's opening phases are ridden, its later ones on foot.
        if(Mount.UntilPhase>0&&BeatPhase>=Mount.UntilPhase&&IsMounted())
        {
            Dismount();
            Fire(TEXT("dismount"));
        }
        // The road's stretches and forced-gait volumes hold her to their gait.
        SoraMountRules::EGait Cap=SoraMountRules::EGait::Gallop;
        for(const FSoraGaitCap& Stretch:Mount.Caps)
            if(Horse->RoadChainage()>=Stretch.FromCm&&Horse->RoadChainage()<Stretch.ToCm) Cap=SoraMountRules::Slower(Cap,Stretch.Gait);
        for(const FSoraForcedGait& Forced:Mount.Forced)
            if(const FSoraVolume* Volume=Space->Volumes.FindByPredicate([&](const FSoraVolume& Row) { return Row.Event==TEXT("volume_enter:")+Forced.Volume; }))
                if(Volume->Contains(Horse->GetActorLocation())) Cap=SoraMountRules::Slower(Cap,Forced.Gait);
        Horse->Cap=Cap;
        // An opponent entering her fear radius spooks her once.
        if(Mount.FearRadiusCm>0)
            for(const auto& Enemy:Enemies)
            {
                if(!IsValid(Enemy)) continue;
                const TWeakObjectPtr<const ASoraEnemy> Key(Enemy.Get());
                const bool bClose=Enemy->IsAlive()&&FVector::Dist2D(Enemy->GetActorLocation(),Horse->GetActorLocation())<Mount.FearRadiusCm;
                if(bClose&&!Frightening.Contains(Key))
                {
                    Frightening.Add(Key);
                    if(IsMounted()) { Horse->Spook(); Fire(TEXT("horse_spooked")); }
                }
                else if(!bClose) Frightening.Remove(Key);
            }
    }
    // A net's lock on the rider throws him: the horse stumbles (horse_down)
    // and he goes on foot, or back to the checkpoint where the ride says so.
    if(IsMounted())
        if(const USoraCombatEffects* Effects=USoraCombatEffects::Get(this); Effects&&Effects->IsRooted(Hero))
        {
            ASoraPlayerCharacter* Rider=Mode().Hero();
            Dismount();
            FHitResult Trace; Trace.ImpactPoint=Rider->GetActorLocation(); Trace.Location=Trace.ImpactPoint;
            SoraDamage::Strike(Rider,SoraCampaignReach::ThrownHp,FSoraHit::Hazard(Rider->GetActorLocation()),FVector::UpVector,Trace,nullptr,nullptr);
            RaiseBeatEvent(TEXT("horse_down"));
            if(!ActiveBeatData()||Mode().bDefeated) return;
        }
    // She answers his whistle.
    if(WhistleAt>=0.0&&GetWorld()&&GetWorld()->GetTimeSeconds()>=WhistleAt&&IsValid(Horse)&&!IsMounted())
    {
        WhistleAt=-1.0;
        // At his left shoulder, facing his way, so he stands at her right to mount.
        const FRotator Facing(0.f,Hero->GetActorRotation().Yaw,0.f);
        Horse->Place(Hero->GetActorLocation()-FRotationMatrix(Facing).GetUnitAxis(EAxis::Y)*SoraMountRules::DismountSideCm,Facing.Yaw);
        Fire(TEXT("horse_returned"));
    }
    // A convoy waits for a rider who falls behind, and halts while any of its
    // string is netted or shies from a light.
    const USoraFieldcraft* Fieldcraft=USoraFieldcraft::Get(this);
    const bool bHalted=Fieldcraft&&Fieldcraft->QuarryHalted();
    for(const auto& Beast:Pack)
        if(IsValid(Beast)) Beast->SetWaiting(bHalted||FVector::Dist2D(Beast->GetActorLocation(),Hero->GetActorLocation())>SoraCampaignReach::ConvoyWait);
}
void USoraCampaignDirector::TickSiege(int32 DeltaMs)
{
    const FSoraBeatSpace* Space=ActiveSpace();
    if(!Space||Task.Task!=SoraBeatRules::ETask::Defend) return;
    for(int32 Target=0;Target<Task.TargetCount&&Target<Space->Targets.Num();++Target)
    {
        if(TaskState.TargetHp[Target]<=0) continue;
        const FVector Where=ASoraWorldBuilder::Floor(Space->Targets[Target]);
        // A seizure drone on its errand nets rather than wears a target down.
        const USoraFieldcraft* Fieldcraft=USoraFieldcraft::Get(this);
        int32 Attackers=0;
        for(const auto& Enemy:Enemies)
            if(IsValid(Enemy)&&Enemy->IsAlive()&&(!Fieldcraft||!Fieldcraft->IsOnErrand(*Enemy))&&
                FVector::Dist2D(Enemy->GetActorLocation(),Where)<SoraBeatRules::SiegeRadiusCm)
                ++Attackers;
        const int32 Damage=SoraBeatRules::SiegeDamage(TaskState,Task,Target,Attackers,DeltaMs);
        // A target lost fails the defence to its checkpoint.
        if(Damage>0&&DamageDefendedTarget(Target,Damage)) return;
    }
}
void USoraCampaignDirector::ShowKit()
{
    ASoraWorldBuilder* World=Mode().Arena();
    const FSoraChapter* Chapter=ActiveChapter();
    const FSoraBeatSpace* Space=ActiveSpace();
    if(!World||!Chapter||!Space) return;
    FSoraKitView View;
    View.ProgressPermille=SoraBeatRules::ProgressPermille(TaskState,Task);
    View.Step=TaskState.Step;
    View.Strokes=Task.Goal==SoraBeatRules::EGoal::Steps?TaskState.Done:0;
    for(int32 Target=0;Target<Task.TargetCount;++Target)
        View.TargetHealth.Add(Task.TargetHp[Target]>0?static_cast<float>(TaskState.TargetHp[Target])/Task.TargetHp[Target]:0.f);
    View.bCarrying=TaskState.Carrying;
    if(Task.Task==SoraBeatRules::ETask::Carry)
    {
        // Distinct goods leave their own pickups; a store empties load by load.
        if(Task.Pickups>=Task.Count)
            for(int32 Point=0;Point<Task.Pickups;++Point) View.PickupTaken.Add((TaskState.PointsMask&(1u<<Point))!=0u);
        else
            for(int32 Item=0;Item<Task.Count;++Item) View.PickupTaken.Add(Item<TaskState.Done+(TaskState.Carrying?1:0));
    }
    for(int32 Point=0;Point<Task.Dropoffs;++Point) View.Delivered.Add(TaskState.DropoffUses[Point]);
    View.bContested=Contested();
    View.bSlack=bCrankSlack;
    if(Task.Goal==SoraBeatRules::EGoal::Escort&&Space->bRoute)
    {
        // The party walks in file along the road, the leader where
        // PartyLocation is: its carts and horses first, then its people.
        const FSoraZone& Road=Chapter->Space.Zones[Space->Zone];
        const float Lead=Space->RouteMarginCm+TaskState.Progress/1000.f;
        const auto Slot=[&](int32 Member)
            { return ASoraWorldBuilder::Floor(Road.PointAlong(FMath::Max<float>(Space->RouteMarginCm*.5f,Lead-Member*SoraCampaignReach::PartySpacing))); };
        for(int32 Member=0;Member<Space->Party.Num();++Member) View.Party.Add(Slot(Member));
        View.PartyYaw=Road.HeadingAt(Lead);
        View.bPartyWalking=TaskState.Progress>LastEscortProgress;
        LastEscortProgress=TaskState.Progress;
        if(USoraFieldcraft* Fieldcraft=USoraFieldcraft::Get(this))
        {
            TArray<FVector> People;
            for(int32 Member=0;Member<Fieldcraft->PartyMembers().Num();++Member) People.Add(Slot(Space->Party.Num()+Member));
            Fieldcraft->PlaceParty(People,View.PartyYaw,static_cast<float>(Task.SpeedCmS));
        }
    }
    World->ShowKit(View);
}
TArray<int32> USoraCampaignDirector::LoosePickups() const
{
    TArray<int32> Loose;
    const FSoraChapter* Chapter=ActiveChapter();
    if(!Chapter||!Mode().bCampaign||!Save) return Loose;
    for(int32 Index=0;Index<Chapter->Space.Pickups.Num();++Index)
    {
        const FSoraCollectible& Item=Chapter->Collectibles[Chapter->Space.Pickups[Index].Collectible];
        if((CollectedMask()&SoraCampaignRules::CollectibleBit(ChapterId,Item.MaskBit))==0ull) Loose.Add(Index);
    }
    return Loose;
}
FVector USoraCampaignDirector::PickupLocation(int32 Pickup) const
{
    const FSoraChapter* Chapter=ActiveChapter();
    return Chapter&&Chapter->Space.Pickups.IsValidIndex(Pickup)?ASoraWorldBuilder::Floor(Chapter->Space.Pickups[Pickup].At):FVector::ZeroVector;
}
void USoraCampaignDirector::ShowPickups()
{
    const FSoraChapter* Chapter=ActiveChapter();
    if(ASoraWorldBuilder* World=Mode().Arena(); World&&Chapter&&Mode().bCampaign) World->ShowPickups(*Chapter,LoosePickups());
}
bool USoraCampaignDirector::PickUp()
{
    const FSoraChapter* Chapter=ActiveChapter();
    if(!Chapter||!Save) return false;
    // A loose collectible within reach goes to the codex, and the find is kept at once.
    for(const int32 Index:LoosePickups())
        if(Near(PickupLocation(Index),SoraCampaignReach::Interact))
        {
            const FSoraCollectible& Item=Chapter->Collectibles[Chapter->Space.Pickups[Index].Collectible];
            Save->Collectibles=static_cast<int64>(CollectedMask()|SoraCampaignRules::CollectibleBit(ChapterId,Item.MaskBit));
            for(const FSoraCollectibleCategory& Category:FSoraCatalog::Get().CollectibleCategories)
                if(Category.Id==Item.Category)
                {
                    const SoraText::FLine Found=SoraText::Format(NSLOCTEXT("SoraArena.Campaign","FoundCollectible","見つけた：{Category}"),
                        {{TEXT("Category"),SoraText::FLine{Category.Japanese,Category.English}}});
                    Tell(FSoraStoryNotice::EKind::Collectible,Found.Japanese,Found.English,Item.Codex,Item.CodexEnglish);
                }
            Fire(TEXT("collectible:")+Item.Id); Fire(TEXT("collectible_found:")+Item.Id);
            ShowPickups();
            SaveProgress();
            return true;
        }
    return false;
}
bool USoraCampaignDirector::InteractSpace(ASoraPlayerCharacter& Player)
{
    const FSoraBeatSpace* Space=ActiveSpace();
    if(!Space||!IsValid(Horse)||!Space->bMount) return false;
    if(IsMounted())
    {
        if(!Space->Mount.bDismount)
        {
            Notify(SoraText::Line(NSLOCTEXT("SoraArena.Campaign","CannotDismount","ここでは降りられない。")),3.f);
            return true;
        }
        Dismount();
        Fire(TEXT("dismount"));
        return true;
    }
    const FVector2D Local=Horse->LocalOf(Player.GetActorLocation());
    // Out of reach on a ride that lets him down, a whistle brings her to him.
    if(Local.Size()>SoraCampaignReach::Saddle)
    {
        if(!Space->Mount.bDismount||Space->Mount.Tack.Num()>TackSteps||WhistleAt>=0.0||!GetWorld()) return false;
        WhistleAt=GetWorld()->GetTimeSeconds()+SoraCampaignReach::WhistleSeconds;
        Fire(TEXT("whistle"));
        Notify(SoraText::Line(NSLOCTEXT("SoraArena.Campaign","WhistleKurimaru","指笛で栗丸を呼んだ。")),3.f);
        return true;
    }
    // Tack-up, piece by piece in order at her side; the bit is refused until
    // she is given what she wants.
    const TArray<FSoraTackStep>& Tack=Space->Mount.Tack;
    if(TackSteps<Tack.Num())
    {
        const FSoraTackStep& Step=Tack[TackSteps];
        if(TackRefused<Step.Refusals)
        {
            ++TackRefused;
            Fire(FString::Printf(TEXT("interact_refused:%s:%d"),*Step.Id,TackRefused));
            return true;
        }
        if(!Step.Gift.IsEmpty()) Fire(TEXT("item_given:")+Step.Gift);
        Fire(TEXT("interact:")+Step.Id);
        ++TackSteps; TackRefused=0;
        Horse->ShowTack(TackSteps);
        return true;
    }
    // A period rider mounts from her right (bible §4.5); the left is refused.
    if(SoraMountRules::CanMount(FMath::RoundToInt32(Local.X),FMath::RoundToInt32(Local.Y)))
    {
        Horse->Mount(Player);
        Fire(TEXT("mount"));
        return true;
    }
    Notify(SoraText::Line(NSLOCTEXT("SoraArena.Campaign","MountFromRight","馬には右側から乗る。右へ回り込もう。")),4.f);
    return true;
}
float USoraCampaignDirector::CarryPace() const
{
    return Mode().bCampaign&&TaskState.Carrying&&Task.Task==SoraBeatRules::ETask::Carry?Task.CarrySpeedPermille/1000.f:1.f;
}
bool USoraCampaignDirector::CanHold(int32 WeaponId,bool bNotify)
{
    if(!Mode().bCampaign||WeaponId<0||WeaponId>=SoraBeatRules::WeaponCount) return true;
    if(!SoraBeatRules::EquipmentAllows(TaskState,Task,WeaponId))
    {
        if(bNotify) Notify(SoraText::Line(NSLOCTEXT("SoraArena.Campaign","HiddenArms","刀と弓は空井戸の底に隠してある。今は脇差だけだ。")),3.f);
        return false;
    }
    if(TaskState.Carrying&&Task.Task==SoraBeatRules::ETask::Carry&&(Task.CarryWeaponsMask&(1u<<WeaponId))==0u)
    {
        if(bNotify) Notify(SoraText::Line(NSLOCTEXT("SoraArena.Campaign","ArmsFull","荷を抱えている。手にできるのは刀を片手で、が精一杯だ。")),3.f);
        return false;
    }
    if(IsMounted()&&(Horse->RideRules().WeaponsMask&(1u<<WeaponId))==0u)
    {
        if(bNotify) Notify(SoraText::Line(NSLOCTEXT("SoraArena.Campaign","NotFromSaddle","馬上ではこの武器は使えない。")),3.f);
        return false;
    }
    return true;
}
bool USoraCampaignDirector::ArmsReady(int32 WeaponId,float AimYaw,bool bNotify)
{
    if(!CanHold(WeaponId,bNotify)||IsClimbingRecoveryWell()||bStringingBow) return false;
    if(!IsMounted()||SoraMountRules::ArcAllows(Horse->RideRules(),WeaponId,FMath::RoundToInt32(AimYaw),
        FMath::RoundToInt32(Horse->GetActorRotation().Yaw)))
        return true;
    // Bible §4.2-4.3: the yumi to the left (弓手), the katana and yari to the right (馬手).
    if(bNotify)
        Notify(SoraText::Line(WeaponId==18?NSLOCTEXT("SoraArena.Campaign","SaddleYumiArc","馬上の弓は左手側へ射る。")
            :WeaponId==19?NSLOCTEXT("SoraArena.Campaign","SaddleYariArc","馬上の槍は前と右へ突く。")
            :NSLOCTEXT("SoraArena.Campaign","SaddleKatanaArc","馬上の刀は右手側へ斬る。")),3.f);
    return false;
}
void USoraCampaignDirector::CarryChanged()
{
    ASoraGameMode& M=Mode();
    ASoraPlayerCharacter* Hero=M.Hero();
    const FSoraBeatSpace* Space=ActiveSpace();
    if(!M.Arena()||!Hero) return;
    const bool bCarrying=Space&&TaskState.Carrying&&Task.Task==SoraBeatRules::ETask::Carry;
    M.Arena()->ShowCarried(Hero,bCarrying?Space->Item:NAME_None);
    // The load leaves only its own loadout in hand: the katana when it allows one.
    if(bCarrying&&!CanHold(Hero->WeaponId,false)&&CanHold(0,false)&&Hero->IsCampaignHero())
        Hero->GetEquipment()->EquipClassSlot(0);
}
void USoraCampaignDirector::Tell(FSoraStoryNotice::EKind Kind,const FString& Japanese,const FString& English,
    const FString& Detail,const FString& DetailEnglish)
{
    // At most four at once; the oldest makes way.
    if(Notices.Num()>=4) Notices.RemoveAt(0);
    FSoraStoryNotice& Notice=Notices.AddDefaulted_GetRef();
    Notice.Kind=Kind; Notice.Japanese=Japanese; Notice.English=English;
    Notice.Detail=Detail; Notice.DetailEnglish=DetailEnglish; Notice.Remaining=7.f;
}
void USoraCampaignDirector::StartCinematicCamera()
{
    const FSoraBeatSpace* Space=ActiveSpace();
    APlayerController* Player=UGameplayStatics::GetPlayerController(this,0);
    // Only a local player's view can change: a controller with no local
    // player (a headless test world) would pass the view back to itself.
    if(!Space||!Space->bCamera||!Player||!Player->IsLocalController()||!GetWorld()) return;
    if(!IsValid(ShotCamera))
    {
        FActorSpawnParameters Params; Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        ShotCamera=GetWorld()->SpawnActor<ACameraActor>(Space->CameraFrom,(Space->CameraLook-Space->CameraFrom).Rotation(),Params);
        if(!ShotCamera) return;
        ShotCamera->GetCameraComponent()->SetFieldOfView(58.f);
        ShotCamera->GetCameraComponent()->SetConstraintAspectRatio(false);
    }
    ShotCamera->SetActorLocationAndRotation(Space->CameraFrom,(Space->CameraLook-Space->CameraFrom).Rotation());
    // The shot blends in from the hero's eye behind the letterboxed card.
    Player->SetViewTargetWithBlend(ShotCamera,.8f,VTBlend_EaseInOut,2.f);
}
void USoraCampaignDirector::UpdateCinematicCamera()
{
    const FSoraBeatSpace* Space=ActiveSpace();
    APlayerController* Player=UGameplayStatics::GetPlayerController(this,0);
    if(!Space||!Space->bCamera||!Player||Task.DurationMs<=0) return;
    // A cinematic that began before the player's view could change takes it now.
    const APlayerCameraManager* Camera=Player->PlayerCameraManager;
    if(!IsValid(ShotCamera)||(Player->GetViewTarget()!=ShotCamera&&!(Camera&&Camera->PendingViewTarget.Target==ShotCamera)))
        StartCinematicCamera();
    if(!IsValid(ShotCamera)) return;
    // A slow dolly from its first mark to its second over the whole cinematic.
    const float Alpha=FMath::SmoothStep(0.f,1.f,FMath::Clamp(CinematicElapsed()*1000.f/Task.DurationMs,0.f,1.f));
    const FVector Location=FMath::Lerp(Space->CameraFrom,Space->CameraTo,Alpha);
    ShotCamera->SetActorLocationAndRotation(Location,(Space->CameraLook-Location).Rotation());
}
void USoraCampaignDirector::EndCinematicCamera(float BlendSeconds)
{
    APlayerController* Player=UGameplayStatics::GetPlayerController(this,0);
    if(!Player||!Player->IsLocalController()||!IsValid(ShotCamera)) return;
    // The shot may still be blending in when the cinematic is skipped.
    const APlayerCameraManager* Camera=Player->PlayerCameraManager;
    if(Player->GetViewTarget()!=ShotCamera&&!(Camera&&Camera->PendingViewTarget.Target==ShotCamera)) return;
    if(BlendSeconds>0.f) Player->SetViewTargetWithBlend(Player->GetPawn(),BlendSeconds,VTBlend_EaseInOut,2.f);
    else Player->SetViewTarget(Player->GetPawn());
}
