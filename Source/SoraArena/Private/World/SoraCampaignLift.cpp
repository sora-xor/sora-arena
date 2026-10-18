#include "SoraCampaignLift.h"
#include "SoraLiftRules.h"
#include "SoraGameMode.h"
#include "SoraEnemy.h"
#include "SoraEnemyController.h"
#include "SoraPlayerCharacter.h"
#include "SoraWorldBuilder.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/DamageType.h"
#include "Kismet/GameplayStatics.h"

ASoraCampaignLift::ASoraCampaignLift()
{
    PrimaryActorTick.bCanEverTick=true;
    PrimaryActorTick.TickGroup=TG_PrePhysics;
    Scene=CreateDefaultSubobject<USceneComponent>(TEXT("LiftScene")); SetRootComponent(Scene);
    Deck=CreateDefaultSubobject<UBoxComponent>(TEXT("MovingDeck")); Deck->SetupAttachment(Scene);
    Deck->SetBoxExtent(FVector(300,300,20)); Deck->SetRelativeLocation(FVector(0,0,2680));
    Deck->SetMobility(EComponentMobility::Movable);
    Deck->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
    Deck->SetCollisionObjectType(ECC_WorldDynamic); Deck->SetCollisionResponseToAllChannels(ECR_Block);
    Deck->SetCanEverAffectNavigation(false); Deck->SetGenerateOverlapEvents(false);
}
UStaticMeshComponent* ASoraCampaignLift::Box(const TCHAR* Name,USceneComponent* Parent,FVector At,FVector Size,bool Collision)
{
    auto* Shape=ASoraWorldBuilder::Shape(this,Parent,Name,TEXT("/Engine/BasicShapes/Cube.Cube"),At,Size/100.f,
        FLinearColor(.22f,.19f,.15f),Collision);
    Shape->SetMobility(EComponentMobility::Movable); Shape->SetCanEverAffectNavigation(false);
    return Shape;
}
void ASoraCampaignLift::Landing(const TCHAR* Name,FVector Center,FVector2D Size,bool WestOpening)
{
    Box(Name,Scene,Center-FVector(0,0,20),FVector(Size,40),true);
    for(int32 Side:{-1,1})
        Box(TEXT("LandingSideRail"),Scene,Center+FVector(0,Side*(Size.Y*.5f-8),65),FVector(Size.X,16,130),true);
    const float WallX=(WestOpening?1.f:-1.f)*(Size.X*.5f-8);
    Box(TEXT("LandingEndRail"),Scene,Center+FVector(WallX,0,65),FVector(16,Size.Y,130),true);
    // The near edge has a 200 cm opening, flush with the deck's gate.
    for(int32 Side:{-1,1})
        Box(TEXT("LandingGatePost"),Scene,Center+FVector(-WallX,Side*(Size.Y*.25f+50),65),
            FVector(16,Size.Y*.5f-100,130),true);
}
void ASoraCampaignLift::Build(FVector2D Center,int32 Turns,int32 MinTurnMs)
{
    SetActorLocation(FVector(Center,0));
    Goal=FMath::Max(1,Turns)*1000;
    SpeedCmS=SoraLiftRules::Speed(Turns,MinTurnMs);
    Box(TEXT("TimberDeck"),Deck,FVector::ZeroVector,FVector(600,600,40),false);
    for(int32 Side:{-1,1})
    {
        Box(TEXT("DeckRail"),Deck,FVector(0,Side*292,85),FVector(600,16,130),true);
        for(int32 End:{-1,1})
            Box(TEXT("DeckEndRail"),Deck,FVector(End*292,Side*200,85),FVector(16,200,130),true);
    }
    WestGate=Box(TEXT("BoardingGate"),Deck,FVector(-292,0,85),FVector(16,200,130),true);
    EastGate=Box(TEXT("GalleryGate"),Deck,FVector(292,0,85),FVector(16,200,130),true);
    // Clear crank bars: helpers stand at their authored positions around it.
    Wheel=Box(TEXT("Capstan"),Deck,FVector(0,0,80),FVector(55,55,120),true);
    Box(TEXT("CapstanBar"),Deck,FVector(0,0,140),FVector(180,12,12),false);
    Hawser=ASoraWorldBuilder::Shape(this,Scene,TEXT("LiftHawser"),TEXT("/Engine/BasicShapes/Cylinder.Cylinder"),
        FVector(-220,220,0),FVector(.12,.12,1),FLinearColor(.3,.22,.12),false);
    Landing(TEXT("L4Landing"),FVector(-600,0,SoraLiftRules::BottomCm),FVector2D(600,600),false);
    Landing(TEXT("HeirloomGallery"),FVector(800,0,SoraLiftRules::TopCm),FVector2D(1000,4000),true);
    // Gantry thresholds are .25/.5/.75 of the exact 115 m travel.
    for(int32 Quarter=1;Quarter<=3;++Quarter)
        Landing(TEXT("SpireGantry"),FVector(650,0,SoraLiftRules::Gantry(Quarter)),FVector2D(700,600),true);
    Gates();
}
void ASoraCampaignLift::SetWork(int32 Milliturns)
{
    TargetCm=SoraLiftRules::Height(Milliturns,Goal);
    if(Wheel) Wheel->SetRelativeRotation(FRotator(0,360.f*Milliturns/1000.f,0));
}
UBoxComponent* ASoraCampaignLift::FloorBase() const { return Deck; }
float ASoraCampaignLift::Height() const { return Deck->GetComponentLocation().Z+20.f; }
bool ASoraCampaignLift::Arrived() const { return SoraLiftRules::At(Height(),SoraLiftRules::TopCm); }
bool ASoraCampaignLift::Aboard(const ACharacter& Rider) const
{
    const auto* Base=Rider.GetMovementBase();
    return Base&&(Base==Deck.Get()||Base->IsAttachedTo(Deck.Get()));
}
FVector ASoraCampaignLift::BoardingPoint() const { return GetActorLocation()+FVector(-650,0,SoraLiftRules::BottomCm); }
FVector ASoraCampaignLift::GalleryExit() const { return GetActorLocation()+FVector(800,1800,SoraLiftRules::TopCm); }
FVector ASoraCampaignLift::GalleryCache() const { return GetActorLocation()+FVector(800,-1400,SoraLiftRules::TopCm); }
FVector ASoraCampaignLift::WaveSpawn(int32 Wave,int32 Member) const
{
    return GetActorLocation()+FVector(650,(Member%3-1)*150,SoraLiftRules::Gantry(Wave+1)+(Wave==0?350:120));
}
FVector ASoraCampaignLift::HawserPoint(float HeightCm) const
{
    return GetActorLocation()+FVector(-220,220,HeightCm);
}
FVector ASoraCampaignLift::CutterGoal(int32 Member) const
{
    const float Angle=Member*120.f;
    return HawserPoint(Height()+400+Member*100)-FRotator(0,Angle,0).Vector()*90.f;
}
void ASoraCampaignLift::Assign(ASoraEnemy& Enemy,int32 Wave)
{
    if(auto* Brain=Cast<ASoraEnemyController>(Enemy.GetController())) Brain->AssignLift(*this,Wave);
    if(Wave==0)
    {
        // A visible collision-free cutter proxy. Contact uses its tip's
        // actual world transform against the physical hawser segment.
        auto* Cutter=ASoraWorldBuilder::Shape(&Enemy,Enemy.GetRootComponent(),TEXT("HawserCutter"),
            TEXT("/Engine/BasicShapes/Cube.Cube"),FVector(70/Enemy.GetActorScale3D().X,0,0),FVector(.4,.08,.08),FLinearColor(.7,.3,.12),false);
        Cutter->SetAbsolute(false,false,true);
        Cutters.Add(Cutter);
    }
}
bool ASoraCampaignLift::CutterTouching() const
{
    const FVector A=HawserPoint(Height()+140),B=HawserPoint(SoraLiftRules::TopCm+600);
    for(const auto& Weak:Cutters)
        if(const auto* Cutter=Weak.Get())
        {
            const auto* Enemy=Cast<ASoraEnemy>(Cutter->GetOwner());
            if(!Enemy||!Enemy->IsAlive()||!Enemy->IsFlying()||Enemy->IsStaggered()) continue;
            const FVector Tip=Cutter->GetComponentTransform().TransformPosition(FVector(50,0,0));
            if(FVector::Dist(Tip,FMath::ClosestPointOnSegment(Tip,A,B))<=18.f) return true;
        }
    return false;
}
void ASoraCampaignLift::Gates()
{
    const auto Gate=[](UStaticMeshComponent* Part,bool Open)
    {
        if(!Part) return;
        Part->SetVisibility(!Open); Part->SetCollisionEnabled(Open?ECollisionEnabled::NoCollision:ECollisionEnabled::QueryAndPhysics);
    };
    Gate(WestGate,SoraLiftRules::At(Height(),SoraLiftRules::BottomCm));
    Gate(EastGate,Arrived());
}
void ASoraCampaignLift::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    const auto* Mode=GetWorld()?GetWorld()->GetAuthGameMode<ASoraGameMode>():nullptr;
    if(!Mode||!Mode->IsPlaying()) return;
    // Leaving the 115 m shaft's protected floor is a player death, routed
    // through the existing beat-start checkpoint. It cannot strand a live
    // player on the obsolete ground-level blockout below the lift.
    if(auto* Hero=Mode->Hero();Hero&&Hero->GetActorLocation().Z<Height()-600.f)
        UGameplayStatics::ApplyDamage(Hero,Hero->Health+1.f,nullptr,this,UDamageType::StaticClass());
    const double Next=SoraLiftRules::Advance(Height(),TargetCm,SpeedCmS,DeltaSeconds);
    // Only the floor moves. CharacterMovement updates the based capsule and
    // performs its own sweep, including when the rider walks on the deck.
    Deck->SetRelativeLocation(FVector(0,0,Next-20.0));
    if(Hawser)
    {
        const double Bottom=Next+140,Top=SoraLiftRules::TopCm+600;
        Hawser->SetRelativeLocation(FVector(-220,220,(Bottom+Top)*.5));
        Hawser->SetRelativeScale3D(FVector(.12,.12,(Top-Bottom)/100.0));
    }
    Gates();
}
void ASoraCampaignLift::EndPlay(const EEndPlayReason::Type Reason)
{
    if(GetWorld())
        for(TActorIterator<ACharacter> It(GetWorld());It;++It)
            if(It->GetMovementBase()&&It->GetMovementBase()->GetOwner()==this) It->SetBase(nullptr);
    Super::EndPlay(Reason);
}
