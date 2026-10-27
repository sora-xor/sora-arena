#include "SoraCampaignDirector.h"
#include "SoraCampaignLift.h"
#include "SoraCatalog.h"
#include "SoraGameMode.h"
#include "SoraEnemy.h"
#include "SoraPlayerCharacter.h"
#include "SoraWorldBuilder.h"
#include "Game/SoraCampaignReach.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"

ASoraEnemy* USoraCampaignDirector::SpawnLiftOpponent(FName Type,int32 Wave,int32 Slot)
{
    auto* Lift=Mode().Arena()?Mode().Arena()->CampaignLift():nullptr;
    if(!Lift||!GetWorld()) return nullptr;
    auto* Enemy=ASoraEnemy::SpawnArchetype(*GetWorld(),Type,Slot,Lift->WaveSpawn(Wave,Slot%3),FRotator(0,180,0));
    if(Enemy) Lift->Assign(*Enemy,Wave);
    return Enemy;
}
int32 USoraCampaignDirector::LiftDecayMultiplier() const
{
    const auto* Lift=Mode().Arena()?Mode().Arena()->CampaignLift():nullptr;
    return Lift&&Lift->CutterTouching()?3:1;
}

FVector USoraCampaignDirector::WorkAnchor() const
{
    const auto* Space=ActiveSpace();
    if(!Space) return FVector::ZeroVector;
    const auto* Lift=Mode().Arena()?Mode().Arena()->CampaignLift():nullptr;
    return ASoraWorldBuilder::Floor(Space->Anchor,Lift?Lift->Height():Space->HeightCm);
}
bool USoraCampaignDirector::NearFloor(const FVector& Location,float Radius) const
{
    return Near(Location,Radius)&&Mode().Hero()&&FMath::Abs(Mode().Hero()->GetActorLocation().Z-Location.Z)<180.f;
}
bool USoraCampaignDirector::AtWorkAnchor(float Radius) const
{
    const auto* Lift=Mode().Arena()?Mode().Arena()->CampaignLift():nullptr;
    return Lift?NearFloor(WorkAnchor(),Radius)&&Mode().Hero()&&Lift->Aboard(*Mode().Hero()):Near(WorkAnchor(),Radius);
}
bool USoraCampaignDirector::LiftReadyToComplete() const
{
    if(!ActiveSpace()||!ActiveSpace()->Lift.bEnabled) return true;
    const auto* Lift=Mode().Arena()?Mode().Arena()->CampaignLift():nullptr;
    return Lift&&Lift->Arrived();
}
bool USoraCampaignDirector::LiftExitPoint(FVector& Point) const
{
    const auto* Lift=Mode().Arena()?Mode().Arena()->CampaignLift():nullptr;
    if(!Lift) return false;
    if(const auto* Chapter=ActiveChapter())
        for(const auto& Beat:Chapter->Beats)
            if(Beat.Space.Summit.Enabled())
            {
                Point=Beat.Space.Summit.Stairs[FMath::Clamp(GalleryStairNode,0,Beat.Space.Summit.Stairs.Num()-1)];
                return true;
            }
    Point=Lift->GalleryExit(); return true;
}
bool USoraCampaignDirector::BeginLiftGallery()
{
    if(!ActiveSpace()||!ActiveSpace()->Lift.bEnabled) return false;
    bLiftGallery=true; GalleryStairNode=0;
    GalleryClock.Reset();
    IdleMs=0;
    if(auto* Arena=Mode().Arena()) Arena->ShowGalleryPois(GalleryPoiMask());
    // Completion and its bark fire only once, before this phase. Its cache
    // is now unlocked, while the saved checkpoint remains the lift's start.
    UpdateObjective();
    return true;
}
bool USoraCampaignDirector::TickLiftGallery(float DeltaSeconds)
{
    if(!bLiftGallery) return false;
    FVector Exit;
    if(!LiftExitPoint(Exit)||!Mode().Hero()) return true;
    const auto* Chapter=ActiveChapter();
    if(NearFloor(Exit,100.f)&&GalleryStairNode<5) { ++GalleryStairNode; UpdateObjective(); }
    bool bAtExit=false;
    IdleMs+=FMath::Min(GalleryClock.Advance(DeltaSeconds),SoraBeatRules::MaxClockMs-IdleMs);
    for(int32 Index=0;Index<Chapter->Beats.Num();++Index)
    {
        const auto& Optional=Chapter->Beats[Index];
        if(Optional.Id==TEXT("ch08.b12"))
            bAtExit=Optional.Space.Exit.Contains(Mode().Hero()->GetActorLocation());
        if(Optional.Id==TEXT("ch08.b12")&&IdleMs>=60000&&!BeatEvents.Contains(TEXT("gallery_exit_hint")))
        {
            BeatEvents.Add(TEXT("gallery_exit_hint")); Fire(TEXT("idle_s:60"),Index);
        }
        if(Optional.Id==TEXT("ch08.b12")&&
            Optional.Space.Volumes.ContainsByPredicate([&](const FSoraVolume& V) {
                return V.Contains(Mode().Hero()->GetActorLocation())&&
                    FMath::Abs(Mode().Hero()->GetActorLocation().Z-Optional.Space.HeightCm)<180.f; }))
        {
            const FString Event=TEXT("volume_enter:vol_heirloom_hall");
            if(!BeatEvents.Contains(Event)) { BeatEvents.Add(Event); Fire(Event,Index); }
        }
    }
    TickGalleryPois();
    if(!bAtExit) return true;
    bLiftGallery=false;
    const int32 Next=SoraBeatRules::NextBeat(BeatState,Chapter->Rules.GetData(),Chapter->Rules.Num());
    LeaveBeatSpace();
    if(Next==INDEX_NONE) FinishChapter(); else BeginBeat(Next,0,false);
    return true;
}

bool USoraCampaignDirector::SpireReadyToComplete() const
{
    const auto* S=ActiveSpace();
    if(!S||!S->Spire.Enabled()) return true;
    const auto* Hero=Mode().Hero();
    return Hero&&S->Exit.Contains(Hero->GetActorLocation())&&Hero->GetCharacterMovement()->IsMovingOnGround()&&
        FMath::Abs(Hero->GetActorLocation().Z-Hero->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()-S->Exit.FloorCm)<10.f;
}
