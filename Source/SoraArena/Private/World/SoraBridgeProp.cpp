#include "SoraBridgeProp.h"
#include "SoraBridgeRules.h"
#include "SoraBoss.h"
#include "SoraEquipmentComponent.h"
#include "SoraPlayerCharacter.h"
#include "SoraWorldBuilder.h"
#include "Combat/SoraBossCatalog.h"
#include "Combat/SoraDamage.h"
#include "Components/BoxComponent.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"

ASoraBridgeProp::ASoraBridgeProp()
{
    PrimaryActorTick.bCanEverTick=false; // The deck orders tilt, then prop sweeps, then rider movement.
    Body=CreateDefaultSubobject<UBoxComponent>(TEXT("SlidingBody")); RootComponent=Body;
    Body->SetMobility(EComponentMobility::Movable);
    Body->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
    Body->SetCollisionObjectType(ECC_WorldDynamic); Body->SetCollisionResponseToAllChannels(ECR_Block);
    Body->SetGenerateOverlapEvents(false); Body->SetCanEverAffectNavigation(true);
    Visual=CreateDefaultSubobject<USceneComponent>(TEXT("Wobble")); Visual->SetupAttachment(Body);
}
void ASoraBridgeProp::Build(bool Pod)
{
    Body->SetBoxExtent(Pod?FVector(55,50,55):FVector(35,35,55));
    const auto Part=[&](const TCHAR* Name,FVector At,FVector Size)
    { return ASoraWorldBuilder::Shape(this,Visual,Name,TEXT("/Engine/BasicShapes/Cube.Cube"),At,Size/100,FLinearColor(.18f,.23f,.25f)); };
    if(Pod) Part(TEXT("Pod"),FVector::ZeroVector,FVector(110,100,110));
    else
    {
        Part(TEXT("Seat"),FVector(0,0,-10),FVector(70,70,10));
        Part(TEXT("Back"),FVector(28,0,20),FVector(14,70,70));
        for(int X:{-1,1}) for(int Y:{-1,1})
            Part(TEXT("Leg"),FVector(X*24,Y*24,-35),FVector(10,10,40));
    }
}
void ASoraBridgeProp::Warn(ASoraBoss& Boss,int32 Attack,int32 Serial,bool Announce)
{
    Keeper=&Boss; AttackIndex=Attack; AttackSerial=Serial; ElapsedMs=0; Speed=0;
    WarningMs=Boss.WindupFor(Attack);
    bBlocked=false; bHitHero=false; bAnnounced=!Announce;
}
void ASoraBridgeProp::Cancel()
{
    ElapsedMs=-1; Speed=0; Keeper.Reset(); Visual->SetRelativeRotation(FRotator::ZeroRotator);
}
void ASoraBridgeProp::Advance(float DeltaSeconds,float Degrees)
{
    auto* Boss=Keeper.Get();
    if(ElapsedMs<0) return;
    if(!Boss||Boss->IsDefeated()||Boss->PhaseIndex()!=1) { Cancel(); return; }
    const double Before=ElapsedMs; ElapsedMs+=FMath::Max(0.f,DeltaSeconds)*1000.0;
    if(ElapsedMs<WarningMs)
    {
        Visual->SetRelativeRotation(FRotator(0,0,2.0*FMath::Sin(ElapsedMs*.045)));
        return;
    }
    Visual->SetRelativeRotation(FRotator::ZeroRotator);
    if(!bAnnounced) { Boss->AnnounceStrike(AttackIndex,AttackSerial); bAnnounced=true; }
    double Remaining=SoraBridgeRules::MovingSeconds(Before,ElapsedMs,WarningMs);
    // Bounded substeps plus a swept root prevent tunnelling at low frame rates.
    // A blocked body retains its position for the next wave: no teleport or reset.
    while(Remaining>0&&!bBlocked)
    {
        const double Dt=FMath::Min(Remaining,.02); Remaining-=Dt;
        const double Distance=SoraBridgeRules::SlideStep(Speed,Dt,Degrees);
        if(Distance<=0) break;
        const FVector Down=GetAttachParentActor()?GetRootComponent()->GetAttachParent()->GetComponentTransform().TransformVectorNoScale(FVector(0,-1,0)):FVector(0,-1,0);
        FHitResult Contact;
        SetActorLocation(GetActorLocation()+Down*Distance,true,&Contact,ETeleportType::None);
        if(!Contact.bBlockingHit) continue;
        bBlocked=true; Speed=0;
        if(auto* Hero=Cast<ASoraPlayerCharacter>(Contact.GetActor());Hero&&!bHitHero)
        {
            bHitHero=true;
            FSoraHit Hit=FSoraHit::Hazard(GetActorLocation()); Hit.AttackId=TEXT("slide_props");
            SoraDamage::Strike(Hero,SoraBridgeRules::Damage,Hit,Down.GetSafeNormal2D(),Contact,Boss->GetController(),Boss);
            Hero->GetEquipment()->Stagger(SoraBridgeRules::StaggerMs/1000.f);
        }
    }
}
