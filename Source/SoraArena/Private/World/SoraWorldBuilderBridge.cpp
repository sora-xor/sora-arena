#include "SoraWorldBuilder.h"
#include "SoraBridgeProp.h"
#include "SoraBridgeRules.h"
#include "SoraBoss.h"
#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraGameMode.h"
#include "Combat/SoraBossCatalog.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "World/SoraNavigation.h"

void ASoraWorldBuilder::BuildBridge(const FSoraZone& Zone,int32 Index,const FSoraBeat& Beat)
{
    // Capture exactly this zone's pieces; never the approach, another zone,
    // objective markers or the following beat's independent helm kit.
    const int32 First=Pieces.Num(),FirstActor=DecorActors.Num();
    BuildZone(Zone,Index);
    BridgeCeilingCm=Zone.WallHeight;
    BridgeRoot=NewObject<USceneComponent>(this,MakeUniqueObjectName(this,USceneComponent::StaticClass(),TEXT("BridgeDeck")));
    BridgeRoot->SetMobility(EComponentMobility::Movable); BridgeRoot->SetupAttachment(RootComponent);
    BridgeRoot->SetRelativeLocation(FVector(Beat.Space.Bridge.Center,0));
    BridgeRoot->RegisterComponent(); AddInstanceComponent(BridgeRoot);
    for(int32 N=First;N<Pieces.Num();++N)
    {
        auto* Piece=Pieces[N].Get(); Piece->SetMobility(EComponentMobility::Movable);
        Piece->AttachToComponent(BridgeRoot,FAttachmentTransformRules::KeepWorldTransform);
        // Dynamic mobility, but still a floor for the boss's WorldStatic ground trace.
        Piece->SetCollisionObjectType(ECC_WorldStatic);
        if(Piece->GetName().Contains(TEXT("Cover")))
        { Piece->ComponentTags.Add(TEXT("BridgeCover")); MarginConsoles.Add(Piece); }
    }
    for(int32 N=FirstActor;N<DecorActors.Num();++N)
        if(auto* Actor=DecorActors[N].Get();Actor&&Actor->GetRootComponent())
        {
            Actor->GetRootComponent()->SetMobility(EComponentMobility::Movable);
            Actor->AttachToComponent(BridgeRoot,FAttachmentTransformRules::KeepWorldTransform);
        }
}
void ASoraWorldBuilder::StageBridge(bool Active)
{
    for(auto& Rider:BridgeRiders) if(auto* Body=Rider.Get()) Body->GetCharacterMovement()->RemoveTickPrerequisiteActor(this);
    BridgeRiders.Reset();
    for(ASoraBridgeProp* Prop:BridgeProps) if(IsValid(Prop)) Prop->Destroy();
    BridgeProps.Reset(); bBridgeActive=Active&&BridgeRoot!=nullptr; BridgeDegrees=0;
    // Beat teardown/checkpoint reset occurs before the next beat's placement.
    // During combat all motion is the moving base plus swept prop movement.
    if(BridgeRoot) BridgeRoot->SetRelativeRotation(FRotator::ZeroRotator);
    StageMargin(bBridgeActive);
    if(!bBridgeActive) return;
    for(int32 N=0;N<SoraBridgeRules::Chairs+SoraBridgeRules::Pods;++N)
    {
        const FVector Local(-1600+(N/2)*800,N%2?600:-600,57);
        FActorSpawnParameters Params; Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        auto* Prop=GetWorld()->SpawnActor<ASoraBridgeProp>(BridgeRoot->GetComponentTransform().TransformPosition(Local),FRotator::ZeroRotator,Params);
        if(!Prop) { UE_LOG(LogTemp,Error,TEXT("SORA bridge could not spawn loose prop %d"),N); continue; }
        Prop->Build(N>=SoraBridgeRules::Chairs);
        Prop->AttachToComponent(BridgeRoot,FAttachmentTransformRules::KeepWorldTransform);
        BridgeProps.Add(Prop);
    }
}
void ASoraWorldBuilder::ClearBridge()
{
    StageBridge(false);
    if(BridgeRoot) BridgeRoot->DestroyComponent();
    BridgeRoot=nullptr; MarginConsoles.Reset(); MarginState={};
}
bool ASoraWorldBuilder::BeginBridgeSlide(ASoraBoss& Boss,int32 Attack,int32 Serial)
{
    if(!HasBridgeDeck()||Boss.BossId()!=TEXT("boss_collatera")||Boss.PhaseIndex()!=1||Boss.IsDefeated()) return false;
    if(!Boss.Data()||!Boss.Data()->Attacks.IsValidIndex(Attack)||Boss.Data()->Attacks[Attack].Id!=TEXT("slide_props")) return false;
    bool Announce=true;
    for(ASoraBridgeProp* Prop:BridgeProps) if(IsValid(Prop)) { Prop->Warn(Boss,Attack,Serial,Announce); Announce=false; }
    return true;
}
float ASoraWorldBuilder::BridgeMoveScale(const ACharacter& Body,const FVector& Intent) const
{
    const auto* Base=Cast<USceneComponent>(Body.GetMovementBaseObject());
    const bool Based=Base&&BridgeRoot&&(Base==BridgeRoot||Base->IsAttachedTo(BridgeRoot));
    const FVector Down=BridgeRoot?BridgeRoot->GetComponentTransform().TransformVectorNoScale(FVector(0,-1,0)):FVector::ZeroVector;
    return SoraBridgeRules::Pace(FVector::DotProduct(Intent.GetSafeNormal2D(),Down.GetSafeNormal2D()),
        Based&&Body.GetCharacterMovement()->IsMovingOnGround(),bBridgeActive&&BridgeDegrees>0);
}
void ASoraWorldBuilder::TickBridge(float DeltaSeconds)
{
    if(!HasBridgeDeck()) return;
    const auto* Mode=GetWorld()->GetAuthGameMode<ASoraGameMode>();
    if(!Mode||!Mode->IsPlaying()) return;
    const auto* Boss=Mode->Campaign()->CampaignBoss();
    TickMargin(DeltaSeconds,Boss);
    if(!Boss||Boss->BossId()!=TEXT("boss_collatera")) return;
    // CharacterMovement's normal swept based movement transports feet and
    // keeps upright capsules. New adds need the same ordering as the hero.
    for(TActorIterator<ACharacter> It(GetWorld());It;++It)
        if(!BridgeRiders.Contains(*It))
        {
            It->GetCharacterMovement()->AddTickPrerequisiteActor(this);
            BridgeRiders.Add(*It);
        }
    const float Before=BridgeDegrees;
    BridgeDegrees=SoraBridgeRules::ListAt(BridgeDegrees,DeltaSeconds,Boss->PhaseIndex()>=1);
    // UE's positive Roll lowers +Y; port is -Y in this bridge frame.
    BridgeRoot->SetRelativeRotation(FRotator(0,0,-BridgeDegrees));
    for(ASoraBridgeProp* Prop:BridgeProps) if(IsValid(Prop)) Prop->Advance(DeltaSeconds,BridgeDegrees);
    if(Before!=BridgeDegrees&&BridgeDegrees==SoraBridgeRules::ListDegrees)
        if(auto* Nav=USoraNavigation::Get(this);Nav&&!Nav->Settle())
            UE_LOG(LogTemp,Error,TEXT("SORA bridge navigation did not settle after deck listing"));
}
