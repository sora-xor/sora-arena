#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraEnemy.h"
#include "SoraEnemyController.h"
#include "SoraGameMode.h"
#include "SoraPlayerCharacter.h"
#include "Game/SoraCampaignReach.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"

bool USoraCampaignDirector::IsRelayRoom() const
{ const auto* Space=ActiveSpace();return Space&&Space->RelayRoom.bEnabled; }
bool USoraCampaignDirector::RelayOffline() const
{ return ChapterId==5&&(BeatState.CompletedMask&SoraBeatRules::BeatBit(3))!=0; }
FVector USoraCampaignDirector::RelayNodeLocation(int32 Node) const
{
    if(!IsRelayRoom()||!SoraRelayRules::ValidNode(Node)) return FVector::ZeroVector;
    const auto P=SoraRelayRules::Nodes[Node];return FVector(ActiveSpace()->RelayRoom.Origin,0)+FVector(P.X,P.Y,P.Z);
}
FVector USoraCampaignDirector::RelayWorkLocation(int32 Node) const
{
    if(!IsRelayRoom()||Node<0||Node>3) return FVector::ZeroVector;
    const auto P=Node==3?SoraRelayRules::FPoint{1850,500,0}:SoraRelayRules::Work[Node];
    return FVector(ActiveSpace()->RelayRoom.Origin,0)+FVector(P.X,P.Y,P.Z);
}
bool USoraCampaignDirector::CanReachRelay(int32 Objective) const
{
    const auto* Player=Mode().Hero();
    if(!IsRelayRoom()||Objective<0||Objective>3||!Player||!Player->IsAlive()||
        !Player->GetCharacterMovement()->IsMovingOnGround()) return false;
    const FVector Work=RelayWorkLocation(Objective);
    const float Feet=Player->GetActorLocation().Z-Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    if(FMath::Abs(Feet-Work.Z)>45.f||FVector::Dist2D(Player->GetActorLocation(),Work)>SoraCampaignReach::Interact) return false;
    if(Objective==3) return Relay.AllDisabled();
    if(FVector::Dist(Player->GetCamera()->GetComponentLocation(),RelayNodeLocation(Objective))>SoraCampaignReach::Interact) return false;
    // End just in front of the column, without ignoring it or the gallery.
    const FVector Outward=Objective==0?FVector(-1,0,0):Objective==1?FVector(1,0,0):FVector(0,1,0);
    FHitResult Hit;FCollisionQueryParams Q(SCENE_QUERY_STAT(RelayControl),false,Player);
    return !GetWorld()->LineTraceSingleByChannel(Hit,Player->GetCamera()->GetComponentLocation(),
        RelayNodeLocation(Objective)+Outward*8.f,ECC_Visibility,Q);
}
void USoraCampaignDirector::RelayCaught(int32 AgeMs)
{
    auto* Player=Mode().Hero();if(!Player) return;
    ASoraEnemyController* Nearest=nullptr;float Best=MAX_flt;
    for(TActorIterator<ASoraEnemyController> It(GetWorld());It;++It)
    {
        auto* Guard=Cast<ASoraEnemy>(It->GetPawn());
        if(!Guard||!Guard->IsAlive()||!It->IsGuard()) continue;
        const float D=FVector::DistSquared(Guard->GetActorLocation(),Player->GetActorLocation());
        if(D<Best) { Best=D;Nearest=*It; }
    }
    // NoteState can synchronously trigger StealthDetected. Account for the
    // part of a long frame after the sensor caught the incomplete pull.
    RelayCatchAgeMs=AgeMs;
    if(Nearest) Nearest->SensorEvidence(Player->GetActorLocation(),SoraRelayRules::CaughtSuspicionPermille);
    RelayCatchAgeMs=0;
    Fire(TEXT("ai_event:relay_scan_caught"));
}
bool USoraCampaignDirector::InteractRelay()
{
    int32 Objective=INDEX_NONE;float Best=MAX_flt;
    for(int I=0;I<4;++I)
        if(!(TaskState.PointsMask&(1u<<I))&&CanReachRelay(I))
        {
            const float D=FVector::DistSquared(Mode().Hero()->GetActorLocation(),RelayWorkLocation(I));
            if(D<Best) { Best=D;Objective=I; }
        }
    if(Objective==3) return WorkObjectiveAt(3);
    if(Objective==INDEX_NONE) return false;
    const auto Result=Relay.Begin(Objective);
    if(Result==SoraRelayRules::EBegin::Caught) RelayCaught();
    if(Result==SoraRelayRules::EBegin::Started)
    {
        HeldWork=EHeldWork::Objective;HeldPoint=Objective;HeldMs=0;
        Fire(TEXT("interact_start:")+ActiveBeatData()->Objectives[Objective]);
    }
    return false;
}
void USoraCampaignDirector::TickRelay(float DeltaSeconds)
{
    if(!IsRelayRoom()) return;
    const int Dt=RelayClock.Advance(DeltaSeconds);
    const auto* Player=Mode().Hero();
    const bool Valid=Player&&Player->IsActionHeld(TEXT("Interact"))&&CanReachRelay(Relay.HeldNode);
    const auto Result=Relay.Advance(Dt,Valid);
    HeldPoint=Relay.HeldNode;HeldMs=Relay.HeldMs;
    HeldWork=HeldPoint>=0?EHeldWork::Objective:EHeldWork::None;
    if(Result.Caught>=0) RelayCaught(Dt-Result.EventAtMs);
    if(Result.Completed>=0)
    {
        const int Before=SoraBeatRules::ProgressPermille(TaskState,Task);
        if(WorkObjectiveAt(Result.Completed)) { UpdateObjective();Progressed(Before); }
    }
}
