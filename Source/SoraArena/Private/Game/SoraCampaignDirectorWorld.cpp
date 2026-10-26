#include "SoraCampaignDirector.h"
#include "Combat/SoraCombatEffects.h"
#include "Combat/SoraDamage.h"
#include "Game/SoraCampaignReach.h"
#include "SoraCampaignRules.h"
#include "SoraCatalog.h"
#include "SoraEnemy.h"
#include "SoraEquipmentComponent.h"
#include "SoraFieldcraft.h"
#include "SoraPressRules.h"
#include "SoraGameMode.h"
#include "SoraHorse.h"
#include "SoraMountRules.h"
#include "SoraPlayerCharacter.h"
#include "SoraSaveGame.h"
#include "SoraText.h"
#include "SoraWorldBuilder.h"
#include "SoraCampaignLift.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/CapsuleComponent.h"
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
    if(!Beat||Mode().bChapterComplete||bWoodTransit) return false;
    if(HelmNeedsTrim()) { Location=HelmWheelPoint(); bInteract=true; return true; }
    if(IsToriiEpilogue()) return EpilogueObjective(Location,bInteract);
    if(IsRelayRoom())
        for(int I=0;I<4;++I) if(!(TaskState.PointsMask&(1u<<I)))
        { Location=RelayWorkLocation(I);bInteract=true;return true; }
    if(IsArcheryLesson()) { Location=ArcheryLine(); bInteract=false; return !AtArcheryLine(); }
    if(bLiftGallery) { bInteract=false; return LiftExitPoint(Location); }
    if(Beat->Space.Moat.bEnabled)
        if(const auto* Craft=USoraFieldcraft::Get(this);Craft&&Craft->MoatObjective(Location)) { bInteract=false;return true; }
    if(Beat->Space.Flood.bEnabled)
        if(const auto* Craft=USoraFieldcraft::Get(this);Craft&&Craft->FloodObjective(Location)) { bInteract=false; return true; }
    const FSoraBeatSpace& Space=Beat->Space;
    const auto At=[&](const FVector2D& Point,bool bWorks) { Location=ASoraWorldBuilder::Floor(Point,Space.FloorAt(Point)); bInteract=bWorks; return true; };
    const auto VolumeOf=[&](const FString& Event) { return Space.Volumes.FindByPredicate([&](const FSoraVolume& Volume) { return Volume.Event==Event; }); };
    if(Task.RecoveryWeapons!=0u&&(NeedsEquipmentRecovery()||AtRecoveryBottom()||IsClimbingRecoveryWell()))
    {
        Location=AtRecoveryBottom()?RecoveryBottom()-FVector(0,0,100):RecoveryApproach()-FVector(0,0,100);
        bInteract=true; return true;
    }
    if(NeedsCarryGate()) return At(Space.CarryGate,true);
    if(Space.Climb.bEnabled)
        if(const auto* Craft=USoraFieldcraft::Get(this);Craft&&Craft->ClimbObjective(Location)) { bInteract=false;return true; }
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
        if(Task.AnchorAfterLines&&TaskState.LinesDone&&!TaskState.Reached)
        {
            const auto* Closing=VolumeOf(Beat->ClosingEvent);
            Location=ASoraWorldBuilder::Floor(Space.Closing,Closing&&Closing->bHeight?Closing->FloorCm:Space.HeightCm);
            bInteract=false;return true;
        }
        return false;
    case SoraBeatRules::EGoal::WavesCleared:
        // Once the field is clear, the volume that brings the next wave.
        if(LiveWaveOpponents()>0||!Pending.IsEmpty()) return false;
        for(int32 Wave=0;Wave<Task.WaveCount;++Wave)
            if(Task.Waves[Wave].Trigger==SoraBeatRules::EWaveTrigger::Volume&&!SoraBeatRules::Released(TaskState,Wave))
                if(const FSoraVolume* Volume=VolumeOf(Beat->Waves[Wave].Event)) { Location=ASoraWorldBuilder::Floor(Volume->Center,Volume->bHeight?Volume->FloorCm:Space.HeightCm); bInteract=false; return true; }
        if((Space.Spire.Enabled()||Space.Wind.Ridge())&&SoraBeatRules::TaskComplete(TaskState,Task))
            { Location=ASoraWorldBuilder::Floor(Space.Exit.Center,Space.Exit.FloorCm); bInteract=false; return true; }
        return false;
    case SoraBeatRules::EGoal::Objectives:
        for(int32 Objective=0;Objective<Space.Objectives.Num();++Objective)
            if((TaskState.PointsMask&(1u<<Objective))==0u) return At(Space.Objectives[Objective],true);
        return false;
    case SoraBeatRules::EGoal::Deliveries:
        if(Task.Task==SoraBeatRules::ETask::Carry&&!TaskState.Carrying)
        {
            for(int32 Slot=0;Slot<SoraBeatRules::MaxPoints;++Slot)
                if((TaskState.LooseLoads&(1u<<Slot))!=0u) { Location=LooseLoadAt[Slot]; bInteract=true; return true; }
            for(int32 Point=0;Point<Space.Pickups.Num();++Point)
                if(Task.Pickups<Task.Count||(TaskState.PointsMask&(1u<<Point))==0u) return At(Space.Pickups[Point],true);
            return false;
        }
        for(int32 Point=0;Point<Space.Dropoffs.Num();++Point)
            if(SoraBeatRules::DropoffHasRoom(TaskState,Task,Point)) return At(Space.Dropoffs[Point],true);
        return false;
    case SoraBeatRules::EGoal::Exit:
        return !TaskState.Reached&&At(Space.Exit.Center,false);
    case SoraBeatRules::EGoal::Hold:
        if(Task.HoldPointCount>0)
        {
            if(IsCopying()) return At(Space.Objectives[CopyDesk],true);
            int32 Nearest=INDEX_NONE;
            double Distance=TNumericLimits<double>::Max();
            for(int32 Point=0;Point<Task.HoldPointCount;++Point)
                if(TaskState.HoldProgress[Point]<Task.HoldPointMs)
                {
                    const double D=Mode().Hero()?FVector::DistSquared2D(Mode().Hero()->GetActorLocation(),FVector(Space.Objectives[Point],0)):Point;
                    if(D<Distance) { Nearest=Point;Distance=D; }
                }
            return Nearest!=INDEX_NONE&&At(Space.Objectives[Nearest],true);
        }
        // A guttered cook-fire wants the hero's hand before the hold goes on.
        if(const USoraFieldcraft* Fieldcraft=USoraFieldcraft::Get(this); Fieldcraft&&Fieldcraft->FiresOut()>0)
            for(int32 Fire=0;Fire<Fieldcraft->Active()->Fires.Points.Num();++Fire)
                if(!Fieldcraft->IsFireLit(Fire)) return At(Fieldcraft->Active()->Fires.Points[Fire],true);
        return At(Space.Anchor,false);
    case SoraBeatRules::EGoal::Turns:
        Location=WorkAnchor(); bInteract=true; return true;
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
        if(IsSpineCapture()&&SoraBeatRules::AwaitsCapture(TaskState,Task)&&Mode().Arena())
        { Location=Mode().Arena()->SummitSpinePoint(); bInteract=true; return true; }
        if(IsBulkheadCapture()&&SoraBeatRules::AwaitsCapture(TaskState,Task)&&Mode().Arena())
        { Location=Mode().Arena()->BulkheadPoint(); bInteract=true; return true; }
        return false;
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
    if(Space->Wind.Kind==TEXT("hangar"))
    {
        // The authored forward group point lies inside shuttle 3's solid
        // proxy. Use its clear forward aisle until the shuttle has interiors;
        // never rely on spawn depenetration to choose the fighting position.
        FVector P(7600,1900,120);
        if(Slot==3) P=FVector(4000,200,920);
        else if(Slot==4||Slot==5) P=FVector(4000+(Slot-4)*180,3500,120);
        else if(Slot==8) P=FVector(6600,200,920);
        else if(Slot==9||Slot==10) P=FVector(4000+(Slot-9)*180,5200,600);
        else P.Y+=(Slot<3?Slot:Slot-3)*300;
        return FVector(Space->Wind.Origin,0)+P;
    }
    if(Space->Wind.Ridge())
    {
        const int32 Group=Slot<2?0:Slot<5?1:2;
        const int32 Member=Slot-(Group==0?0:Group==1?2:5);
        // The authored point locates a group. Separate its capsules along
        // the hull so members never begin intersecting one another.
        return FVector(Space->Wind.Origin,0)+FVector((Group==0?2000:Group==1?9000:16000)+Member*120,Group==0?-2500:Group==1?0:2000,Group==0?600:Group==1?1500:800);
    }
    if(Space->Moat.bEnabled)return FVector(Space->Spawns[FMath::Abs(Slot)%Space->Spawns.Num()],1840.f);
    if(Space->Flood.bEnabled)
    {
        const int32 Pick=FMath::Abs(Slot)%Space->Spawns.Num();
        return FVector(Space->Spawns[Pick],Pick<3?320.f:Pick==3?380.f:216.f);
    }
    if(Space->Spire.Enabled()) return Space->Spire.Spawns[FMath::Abs(Slot)%Space->Spire.Spawns.Num()]+FVector(0,0,120);
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
    return ASoraWorldBuilder::Floor(Space->Spawns[FMath::Abs(Slot)%Space->Spawns.Num()],Space->HeightCm+120.f);
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
    World->StageKit(*Chapter,BeatIndex);
    World->ShowArchivePage(*Beat,BeatPhase);
    World->ShowGalleryPois(GalleryPoiMask());
    // Fresh checkpoint entry may need a cut to L4. Normal spiral traversal
    // reaches the same landing on foot and continues onto the lift.
    const bool NeedsLiftEntry=Space.Lift.bEnabled&&Hero&&FMath::Abs(Hero->GetActorLocation().Z-Space.HeightCm)>180.f;
    const bool NeedsSummitEntry=Space.Summit.Enabled()&&Beat->Is(SoraBeatRules::EType::Boss);
    const FVector Feet=Hero?Hero->GetActorLocation()-FVector(0,0,Hero->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()):FVector::ZeroVector;
    const bool NeedsPressEntry=Space.PressHall.bEnabled&&(bResumed||
        FVector2D::Distance(FVector2D(Feet),Space.Entry)>180.f||FMath::Abs(Feet.Z-SoraPressRules::CatwalkHeightCm)>20.f);
    if(Hero&&(NeedsLiftEntry||NeedsSummitEntry||NeedsPressEntry||Chapter->Space.ZoneAt(Hero->GetActorLocation())!=Space.Zone))
    {
        ClearHorses();
        Hero->SetBase(static_cast<FMovementBaseInterfaceData*>(nullptr));
        Hero->GetCharacterMovement()->StopMovementImmediately();
        const FRotator Facing(0,Space.EntryYaw,0);
        const float EntryHeight=Space.PressHall.bEnabled?float(SoraPressRules::CatwalkHeightCm):float(Space.HeightCm);
        Hero->SetActorLocationAndRotation(ASoraWorldBuilder::Floor(Space.Entry,EntryHeight+120.f),Facing,false,nullptr,ETeleportType::TeleportPhysics);
        if(AController* Controller=Hero->GetController()) Controller->SetControlRotation(Facing);
        if(APlayerController* Player=Cast<APlayerController>(Hero->GetController()))
            if(Player->PlayerCameraManager&&!bResumed) Player->PlayerCameraManager->StartCameraFade(1.f,0.f,.6f,FLinearColor::Black);
    }
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
                    Beast->PackId=Row.Id;
                    Beast->Lead(Front,Row.SpacingCm,Mount.Rules.FearRecoverMs);
                    if(Beat->Cargo.Total>0) Beast->ConfigureCargo(Task.Count,Beat->Cargo.PerDropoff);
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
    ResetPods();
    ResetFoundry();
    ResetHorseTreatment();
    ResetWind();
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
        if(VolumesEntered.Contains(Index)||!Volume.Contains(At)||(IsWoodExplore()&&!AtWoodExit())) continue;
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
        // The laden mare has her own fear geometry. A cyan threat behind
        // Bunta can pull Kurimaru's reins while outside Kurimaru's radius.
        const USoraFieldcraft* Craft=USoraFieldcraft::Get(this);
        for(const auto& Beast:Pack)
            if(IsValid(Beast)&&Beast->IsLed())
            {
                bool bNear=false;
                if(Mount.FearRadiusCm>0)
                {
                    for(const auto& Enemy:Enemies)
                        bNear|=IsValid(Enemy)&&Enemy->IsAlive()&&FVector::Dist2D(Enemy->GetActorLocation(),Beast->GetActorLocation())<Mount.FearRadiusCm;
                    if(Craft)
                        for(int32 Light=0;Light<Craft->LightCount();++Light)
                            bNear|=Craft->IsLightOn(Light)&&FVector::Dist2D(Craft->SpotOf(Light),Beast->GetActorLocation())<Mount.FearRadiusCm;
                }
                if(Beast->ObserveLeadThreat(bNear)) Fire(TEXT("horse_spooked"));
            }
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
    const bool bSpookOnset=IsValid(Horse)&&Horse->ConsumeSpookOnset();
    if(IsMounted())
    {
        if(const USoraCombatEffects* Effects=USoraCombatEffects::Get(this); Effects&&Effects->IsRooted(Hero))
        {
            ASoraPlayerCharacter* Rider=Mode().Hero();
            Dismount();
            FHitResult Trace; Trace.ImpactPoint=Rider->GetActorLocation(); Trace.Location=Trace.ImpactPoint;
            SoraDamage::Strike(Rider,SoraCampaignReach::ThrownHp,FSoraHit::Hazard(Rider->GetActorLocation()),FVector::UpVector,Trace,nullptr,nullptr);
            RaiseBeatEvent(TEXT("horse_down"));
            if(!ActiveBeatData()||Mode().bDefeated) return;
        }
        else if(Space->bMount&&Space->Mount.bDismountOnSpook&&bSpookOnset)
        {
            // Pure fright dismounts without the net's thrown damage. The
            // rooted case above keeps priority when both happen together.
            Dismount();
            Fire(TEXT("dismount"));
            RaiseBeatEvent(TEXT("horse_down"));
            if(!ActiveBeatData()||Mode().bDefeated) return;
        }
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
    bool bHalted=Fieldcraft&&Fieldcraft->QuarryHalted();
    // These horses are tied nose-to-tail. If the rider leaves any member
    // behind, stop the entire string; individual distance stops let the
    // following horses catch up and occupy the same point as the first.
    for(const auto& Beast:Pack)
        if(IsValid(Beast)&&!Beast->IsLed())
            bHalted|=FVector::Dist2D(Beast->GetActorLocation(),Hero->GetActorLocation())>SoraCampaignReach::ConvoyWait;
    for(const auto& Beast:Pack)
        if(IsValid(Beast)) Beast->SetWaiting(bHalted);
}
void USoraCampaignDirector::TickSiege(int32 DeltaMs)
{
    if(IsFoundryDefense()||IsHorseShellDefense()) return; // Actual projectiles and arrivals own these encounters' pressure.
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
    const FSoraBeat* Beat=ActiveBeatData();
    if(Beat&&Beat->Cargo.Total>0)
        for(const auto& Beast:Pack)
            if(IsValid(Beast)&&Beast->PackId==TEXT("pack_horse_cargo"))
                Beast->ShowCargo(SoraCargoRules::Remaining(Beat->Cargo,Task.Count,TaskState.Done)/Beat->Cargo.PerDropoff);
    FSoraKitView View;
    View.ProgressPermille=SoraBeatRules::ProgressPermille(TaskState,Task);
    View.Step=TaskState.Step;
    for(int32 Point=0;Point<Task.HoldPointCount;++Point)
        View.HoldProgressPermille.Add(SoraBeatRules::Ratio(TaskState.HoldProgress[Point],Task.HoldPointMs));
    View.BellowsNotches=SoraBeatRules::CrankFlameNotches(TaskState,Task);
    View.BellowsFoot=IsWorkingCrank()?BellowsTreads.LatchedSide:0;
    View.Strokes=Task.Goal==SoraBeatRules::EGoal::Steps?TaskState.Done:0;
    if(SoraRhythmRules::Active(RhythmClock,TaskState,Task))
    {
        View.RhythmStep=TaskState.Step;
        View.RhythmElapsedMs=TaskState.ElapsedMs-RhythmClock.StartedMs;
        View.RhythmPeriodMs=Task.Steps[TaskState.Step].BeatMs;
        View.RhythmHitAgeMs=RhythmStrikeMs>=0?TaskState.ElapsedMs-RhythmStrikeMs:-1;
    }
    for(int32 Target=0;Target<Task.TargetCount;++Target)
        View.TargetHealth.Add(Task.TargetHp[Target]>0?static_cast<float>(TaskState.TargetHp[Target])/Task.TargetHp[Target]:0.f);
    View.bCarrying=TaskState.Carrying;
    if(Task.Task==SoraBeatRules::ETask::Carry)
    {
        // Distinct goods leave their own pickups; a store empties load by load.
        if(Task.Pickups>=Task.Count)
            for(int32 Point=0;Point<Task.Pickups;++Point) View.PickupTaken.Add((TaskState.PointsMask&(1u<<Point))!=0u);
        else
            for(int32 Item=0;Item<Task.Count;++Item) View.PickupTaken.Add(Item<TaskState.Done+(TaskState.Carrying?1:0)+SoraBeatRules::Bits(TaskState.LooseLoads));
        View.LooseMask=TaskState.LooseLoads;
        for(int32 Slot=0;Slot<SoraBeatRules::MaxPoints;++Slot) View.LooseLoads.Add(LooseLoadAt[Slot]);
        View.bCarryGateOpen=SoraBeatRules::CarryGateReady(TaskState,Task);
    }
    for(int32 Point=0;Point<Task.Dropoffs;++Point) View.Delivered.Add(TaskState.DropoffUses[Point]);
    View.bContested=Contested();
    View.bSlack=bCrankSlack&&!(ActiveCrankHelpers>0&&Task.CoopSuspendsDecay)&&TaskState.Progress>TaskState.CrankFloor;
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
    if(auto* Lift=World->CampaignLift()) Lift->SetWork(TaskState.Progress);
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
    return Chapter&&Chapter->Space.Pickups.IsValidIndex(Pickup)?ASoraWorldBuilder::Floor(
        Chapter->Space.Pickups[Pickup].At,Chapter->Space.Pickups[Pickup].HeightCm):FVector::ZeroVector;
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
        if(NearFloor(PickupLocation(Index),SoraCampaignReach::Interact))
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
    if(HelmOccupiesHands()||CrankOccupiesHands()||FoundryOccupiesHands()||HorseTreatmentOccupiesHands()||IsCopying())
    {
        if(bNotify)
        {
            if(FoundryOccupiesHands()||HorseTreatmentOccupiesHands()||IsCopying()) Notify(SoraText::Line(NSLOCTEXT("SoraArena.Campaign","FoundryHands","作業中は両手を使う。手を離せば武器を使える。")),3.f);
            else Notify(SoraText::Line(NSLOCTEXT("SoraArena.Campaign","CrankHands","両手で輪を回している。手を離せば武器を使える。")),3.f);
        }
        return false;
    }
    if(UsesDojoQuiver()&&ActiveBeatData()&&ActiveBeatData()->bSparring&&
        Task.Type==SoraBeatRules::EType::Duel&&WeaponId!=0)
    {
        if(bNotify) Notify(SoraText::Line(NSLOCTEXT("SoraArena.Archery","TrainingOnly","この立合いは稽古刀で行う。")),3.f);
        return false;
    }
    if(!SoraBeatRules::EquipmentAllows(TaskState,Task,WeaponId))
    {
        if(bNotify)
        {
            if(ChapterId==2&&Task.EquipmentMask==(1u<<4)&&!TaskState.EquipmentRecovered) Notify(SoraText::Line(NSLOCTEXT("SoraArena.Campaign","HiddenArms","刀と弓は空井戸の底に隠してある。今は脇差だけだ。")),3.f);
            else if(ChapterId==5&&WeaponId==18) Notify(SoraText::Line(NSLOCTEXT("SoraArena.Campaign","UnstrungInfiltrationBow","弓の弦はまだ張っていない。水門を抜けてから張ろう。")),3.f);
            else Notify(SoraText::Line(NSLOCTEXT("SoraArena.Campaign","MissionArms","この武器は持ってきていない。手元の武器を使おう。")),3.f);
        }
        return false;
    }
    if(WeaponId==19&&ActiveBeatData()&&ActiveBeatData()->SupplyPoint==TEXT("vol_b14_supply")&&
       !BeatEvents.Contains(TEXT("supply_equipment_ready:vol_b14_supply")))
    {
        if(bNotify) Notify(TEXT("槍は同盟の補給箱で受け取ろう。"),TEXT("Collect the yari at the League supply cache."),3.f);
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
    if(!CanHold(WeaponId,bNotify)||IsClimbingRecoveryWell()||bStringingBow||bPryingCarryGate) return false;
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
