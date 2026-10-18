#include "SoraHorse.h"
#include "SoraCatalog.h"
#include "SoraGameMode.h"
#include "SoraSettings.h"
#include "SoraPlayerCharacter.h"
#include "SoraWorldBuilder.h"
#include "Camera/CameraComponent.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"

namespace
{
// Her frame box rides this far above the ground, clear of every floor.
constexpr float HorseFrameZ = 90.f;
const TCHAR* const HorseCube = TEXT("/Engine/BasicShapes/Cube.Cube");
const TCHAR* const HorseCylinder = TEXT("/Engine/BasicShapes/Cylinder.Cylinder");
const TCHAR* const HorseSphere = TEXT("/Engine/BasicShapes/Sphere.Sphere");
const TCHAR* const HorseCone = TEXT("/Engine/BasicShapes/Cone.Cone");
// 栗毛 chestnut, 鹿毛 bay and 黒鹿毛 black-bay; bay coats have black points.
FLinearColor HorseCoatColor(FName Coat)
{
    return Coat==TEXT("chestnut")?FLinearColor(.47f,.21f,.09f):Coat==TEXT("black_bay")?FLinearColor(.13f,.08f,.06f):FLinearColor(.38f,.2f,.1f);
}
FLinearColor HorsePointsColor(FName Coat)
{
    return Coat==TEXT("chestnut")?FLinearColor(.4f,.18f,.08f):FLinearColor(.04f,.03f,.03f);
}
// Stride, leg swing and back movement per gait, and each leg's place in the
// footfall (left fore, right fore, left hind, right hind): a lateral walk, a
// diagonal trot, a three-beat canter and a four-beat gallop.
constexpr float HorseStrideCm[SoraMountRules::GaitCount] = {150.f, 150.f, 200.f, 280.f, 380.f};
constexpr float HorseSwingDeg[SoraMountRules::GaitCount] = {0.f, 18.f, 26.f, 32.f, 38.f};
constexpr float HorseBobCm[SoraMountRules::GaitCount] = {0.f, 1.5f, 3.5f, 5.f, 6.f};
constexpr float HorseFootfall[SoraMountRules::GaitCount][4] = {
    {0.f, 0.f, 0.f, 0.f}, {.25f, .75f, 0.f, .5f}, {0.f, .5f, .5f, 0.f}, {.33f, .66f, 0.f, .33f}, {.5f, .65f, 0.f, .15f}};
SoraMountRules::EGait HorseGaitForPace(float PaceCmS)
{
    using SoraMountRules::EGait;
    return PaceCmS<=1.f?EGait::Halt:PaceCmS<=220.f?EGait::Walk:PaceCmS<=460.f?EGait::Trot:PaceCmS<=650.f?EGait::Canter:EGait::Gallop;
}
}

ASoraHorse::ASoraHorse()
{
    PrimaryActorTick.bCanEverTick=true;
    Frame=CreateDefaultSubobject<UBoxComponent>(TEXT("Frame"));
    Frame->SetBoxExtent(FVector(100.f,32.f,60.f));
    Frame->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    Frame->SetCollisionObjectType(ECC_WorldDynamic);
    Frame->SetCollisionResponseToAllChannels(ECR_Ignore);
    Frame->SetCollisionResponseToChannel(ECC_WorldStatic,ECR_Block);
    Frame->SetCollisionResponseToChannel(ECC_WorldDynamic,ECR_Block);
    Frame->SetGenerateOverlapEvents(false);
    RootComponent=Frame;
    Body=CreateDefaultSubobject<USceneComponent>(TEXT("Body"));
    Body->SetupAttachment(Frame);
    Body->SetRelativeLocation(FVector(0,0,-HorseFrameZ));
}
UStaticMeshComponent* ASoraHorse::Part(USceneComponent* Parent,const FString& Name,const TCHAR* Shape,FVector Location,FVector Scale,FLinearColor Color,FRotator Rotation)
{
    auto* Mesh=ASoraWorldBuilder::Shape(this,Parent,Name,Shape,Location,Scale,Color);
    Mesh->SetRelativeRotation(Rotation);
    Mesh->SetCastShadow(true);
    Parts.Add(Mesh);
    return Mesh;
}
USceneComponent* ASoraHorse::Joint(USceneComponent* Parent,const FString& Name,FVector Location)
{
    auto* Point=NewObject<USceneComponent>(this,MakeUniqueObjectName(this,USceneComponent::StaticClass(),FName(*Name)));
    Point->SetupAttachment(Parent); Point->SetRelativeLocation(Location);
    Point->RegisterComponent(); AddInstanceComponent(Point);
    return Point;
}
void ASoraHorse::Build(FName Coat,ETack Tack)
{
    for(const auto& Mesh:Parts) if(Mesh) Mesh->DestroyComponent();
    for(const auto& Hip:Hips) if(Hip) Hip->DestroyComponent();
    if(Head) Head->DestroyComponent();
    Parts.Reset(); TackParts.Reset(); Hips.Reset();
    const FLinearColor Hide=HorseCoatColor(Coat),Points=HorsePointsColor(Coat),Mane=Coat==TEXT("chestnut")?FLinearColor(.55f,.3f,.13f):Points;
    // A native horse's proportions: a deep barrel on short legs, 130 cm at the withers.
    Part(Body,TEXT("Barrel"),HorseCylinder,FVector(0,0,100),FVector(.72f,.62f,1.45f),Hide,FRotator(90,0,0));
    Part(Body,TEXT("Chest"),HorseSphere,FVector(62,0,106),FVector(.72f,.64f,.82f),Hide);
    Part(Body,TEXT("Haunch"),HorseSphere,FVector(-62,0,110),FVector(.78f,.66f,.8f),Hide);
    Part(Body,TEXT("Withers"),HorseSphere,FVector(40,0,126),FVector(.5f,.4f,.3f),Hide);
    Part(Body,TEXT("Neck"),HorseCylinder,FVector(100,0,152),FVector(.42f,.34f,.85f),Hide,FRotator(-45,0,0));
    Part(Body,TEXT("Mane"),HorseCube,FVector(95,0,170),FVector(.9f,.07f,.16f),Mane,FRotator(-45,0,0));
    Part(Body,TEXT("Tail"),HorseCylinder,FVector(-106,0,86),FVector(.14f,.14f,.75f),Mane,FRotator(24,0,0));
    Head=Joint(Body,TEXT("Head"),FVector(128,0,184));
    Part(Head,TEXT("Skull"),HorseCube,FVector(16,0,-14),FVector(.56f,.24f,.27f),Hide,FRotator(-50,0,0));
    Part(Head,TEXT("Muzzle"),HorseSphere,FVector(33,0,-36),FVector(.24f,.2f,.2f),Points);
    Part(Head,TEXT("Forelock"),HorseCube,FVector(2,0,6),FVector(.2f,.14f,.1f),Mane);
    for(int32 Side:{-1,1})
    {
        Part(Head,FString::Printf(TEXT("Ear%d"),Side),HorseCone,FVector(-6,Side*8,16),FVector(.08f,.08f,.15f),Hide);
        Part(Head,FString::Printf(TEXT("Eye%d"),Side),HorseSphere,FVector(8,Side*12,-4),FVector(.05f,.03f,.05f),FLinearColor(.02f,.015f,.01f));
    }
    // Hips and shoulders swing the legs; bay points darken the lower legs.
    const FVector LegRoots[4]={FVector(56,-22,88),FVector(56,22,88),FVector(-58,-22,90),FVector(-58,22,90)};
    for(int32 Leg=0;Leg<4;++Leg)
    {
        USceneComponent* Hip=Joint(Body,FString::Printf(TEXT("Hip%d"),Leg),LegRoots[Leg]);
        Hips.Add(Hip);
        Part(Hip,FString::Printf(TEXT("Forearm%d"),Leg),HorseCylinder,FVector(0,0,-22),FVector(.17f,.17f,.45f),Hide);
        Part(Hip,FString::Printf(TEXT("Cannon%d"),Leg),HorseCylinder,FVector(0,0,-64),FVector(.11f,.11f,.42f),Points);
        Part(Hip,FString::Printf(TEXT("Hoof%d"),Leg),HorseCylinder,FVector(3,0,-86),FVector(.14f,.14f,.08f),FLinearColor(.08f,.07f,.06f));
    }
    if(Tack==ETack::Riding) BuildRidingTack();
    else if(Tack==ETack::Pack) BuildPackSaddle();
}
void ASoraHorse::BuildRidingTack()
{
    const FLinearColor Lacquer(.32f,.06f,.04f),Leather(.25f,.14f,.08f),Iron(.06f,.05f,.05f),Mon(.8f,.1f,.06f),Indigo(.08f,.12f,.3f);
    auto Tack=[&](const FString& Name,USceneComponent* Parent,const TCHAR* Shape,FVector Location,FVector Scale,FLinearColor Color,FRotator Rotation=FRotator::ZeroRotator)
    {
        auto* Mesh=Part(Parent,Name,Shape,Location,Scale,Color,Rotation);
        TackParts.Add(Mesh);
        return Mesh;
    };
    // Group 0, 鞍 kura: under-pad, 障泥 aori flaps, 前輪 and 後輪 arches and the 居木 seat.
    Tack(TEXT("Shitagura"),Body,HorseCube,FVector(0,0,131),FVector(.62f,.66f,.03f),FLinearColor(.12f,.1f,.14f));
    for(int32 Side:{-1,1}) Tack(FString::Printf(TEXT("Aori%d"),Side),Body,HorseCube,FVector(0,Side*35,112),FVector(.5f,.02f,.4f),FLinearColor(.18f,.1f,.06f));
    Tack(TEXT("Maewa"),Body,HorseCube,FVector(22,0,145),FVector(.07f,.5f,.22f),Lacquer);
    Tack(TEXT("Shizuwa"),Body,HorseCube,FVector(-20,0,143),FVector(.07f,.5f,.18f),Lacquer);
    Tack(TEXT("Igi"),Body,HorseCube,FVector(1,0,137),FVector(.42f,.36f,.05f),Leather);
    const int32 Kura=TackParts.Num();
    // Group 1, 腹帯 haruobi: the girth around the barrel.
    Tack(TEXT("Haruobi"),Body,HorseCylinder,FVector(8,0,100),FVector(.74f,.64f,.07f),FLinearColor(.55f,.45f,.3f),FRotator(90,0,0));
    // Group 2, 力革 and broad-toed 鐙 abumi on both sides, the SORA mon on each front plate.
    for(int32 Side:{-1,1})
    {
        Tack(FString::Printf(TEXT("Chikaragawa%d"),Side),Body,HorseCube,FVector(4,Side*38,118),FVector(.03f,.02f,.36f),Leather);
        Tack(FString::Printf(TEXT("Abumi%d"),Side),Body,HorseCube,FVector(8,Side*42,80),FVector(.26f,.12f,.07f),Iron);
        Tack(FString::Printf(TEXT("AbumiMon%d"),Side),Body,HorseCylinder,FVector(21,Side*42,83),FVector(.06f,.06f,.012f),Mon,FRotator(90,0,0));
    }
    // Group 3, 轡 kutsuwa and 面繋 headstall, cloth 手綱 tazuna and the 鞦 crupper.
    for(int32 Side:{-1,1})
    {
        Tack(FString::Printf(TEXT("Kutsuwa%d"),Side),Head,HorseCylinder,FVector(30,Side*11,-34),FVector(.06f,.06f,.02f),Iron,FRotator(0,0,90));
        const FVector Bit(158,Side*11.f,150),Hand(24,Side*14.f,146);
        const FVector Span=Bit-Hand;
        Tack(FString::Printf(TEXT("Tazuna%d"),Side),Body,HorseCube,(Bit+Hand)*.5f,FVector(Span.Size()/100.f,.03f,.012f),Indigo,
            FRotator(FMath::RadiansToDegrees(FMath::Atan2(Span.Z,Span.X)),0,0));
    }
    Tack(TEXT("Omogai"),Head,HorseCube,FVector(10,0,-12),FVector(.04f,.26f,.3f),Leather,FRotator(-50,0,0));
    Tack(TEXT("Shirigai"),Body,HorseCube,FVector(-62,0,130),FVector(.8f,.04f,.03f),Lacquer,FRotator(-16,0,0));
    // Tack-up shows the kura, girth, abumi and bit groups in order.
    for(int32 Index=0;Index<TackParts.Num();++Index)
        TackParts[Index]->ComponentTags.Add(FName(*FString::FromInt(Index<Kura?0:Index==Kura?1:Index<Kura+7?2:3)));
}
void ASoraHorse::BuildPackSaddle()
{
    // 荷鞍 with a 振り分け load: two bales slung either side and roped over.
    Part(Body,TEXT("Niguraa"),HorseCube,FVector(0,0,138),FVector(.6f,.62f,.18f),FLinearColor(.45f,.32f,.18f));
    for(int32 Side:{-1,1})
        Part(Body,FString::Printf(TEXT("Load%d"),Side),HorseCylinder,FVector(0,Side*44,118),FVector(.4f,.4f,.62f),FLinearColor(.72f,.6f,.33f),FRotator(90,0,0));
    Part(Body,TEXT("LoadRope"),HorseCube,FVector(0,0,150),FVector(.04f,1.f,.03f),FLinearColor(.55f,.45f,.3f));
}
void ASoraHorse::ShowTack(int32 Pieces)
{
    for(const auto& Mesh:TackParts)
        if(Mesh) Mesh->SetVisibility(!Mesh->ComponentTags.IsEmpty()&&FCString::Atoi(*Mesh->ComponentTags[0].ToString())<Pieces);
}
void ASoraHorse::SetRide(const FSoraMount& Mount,const FSoraZone* InRoad)
{
    Rules=Mount.Rules;
    Road=InRoad&&InRoad->IsRoute()?InRoad:nullptr;
    bAutoSteer=Mount.bAutoSteer&&Road!=nullptr;
    Chainage=Road?Road->ChainageOf(FVector2D(GetActorLocation())):0.f;
    Ride=SoraMountRules::FRide();
}
void ASoraHorse::Place(const FVector& Location,float Yaw)
{
    SetActorLocationAndRotation(FVector(Location.X,Location.Y,HorseFrameZ),FRotator(0,Yaw,0),false,nullptr,ETeleportType::TeleportPhysics);
    Ride.Gait=SoraMountRules::EGait::Halt;
    if(Road) Chainage=Road->ChainageOf(FVector2D(Location));
}
FVector2D ASoraHorse::LocalOf(const FVector& Location) const
{
    const FVector Offset=Location-GetActorLocation();
    return FVector2D(FVector::DotProduct(Offset,GetActorForwardVector()),FVector::DotProduct(Offset,GetActorRightVector()));
}
bool ASoraHorse::Mount(ASoraPlayerCharacter& Rider)
{
    if(RiderPawn.IsValid()) return false;
    UCharacterMovementComponent* Movement=Rider.GetCharacterMovement();
    Movement->StopMovementImmediately();
    Movement->DisableMovement();
    // The rider sits in the kura with his eye RiderEyeCm above the ground.
    Rider.AttachToComponent(Body,FAttachmentTransformRules::KeepWorldTransform);
    const float EyeZ=Rider.GetCamera()?Rider.GetCamera()->GetRelativeLocation().Z:64.f;
    Rider.SetActorRelativeLocation(FVector(-6.f,0.f,RiderEyeCm-EyeZ));
    RiderPawn=&Rider;
    Ride.UrgeMs=Ride.ReinMs=Ride.EaseMs=0;
    return true;
}
void ASoraHorse::Dismount()
{
    ASoraPlayerCharacter* Rider=RiderPawn.Get();
    RiderPawn=nullptr;
    if(!Rider) return;
    Rider->DetachFromActor(FDetachmentTransformRules::KeepWorldTransform);
    const float Half=Rider->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    const FVector Ground(GetActorLocation().X,GetActorLocation().Y,0.f);
    // Down on her right, as a period rider dismounts; her left only when a wall is there.
    for(const float Side:{1.f,-1.f})
        if(Rider->TeleportTo(Ground+GetActorRightVector()*(Side*SoraMountRules::DismountSideCm)+FVector(0,0,Half+2.f),Rider->GetActorRotation()))
            break;
    Rider->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
}
void ASoraHorse::FollowRoad(const FSoraZone* InRoad,float StartChainage,int32 InPace)
{
    Road=InRoad&&InRoad->IsRoute()?InRoad:nullptr;
    Chainage=StartChainage; PaceCmS=InPace; Leader=nullptr;
    if(Road) Place(ASoraWorldBuilder::Floor(Road->PointAlong(Chainage)),Road->HeadingAt(Chainage));
}
void ASoraHorse::Lead(ASoraHorse* InLeader,float SpacingCm)
{
    Leader=InLeader; LeadSpacing=SpacingCm; Road=nullptr; PaceCmS=0;
}
void ASoraHorse::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    const ASoraGameMode* Mode=Cast<ASoraGameMode>(GetWorld()->GetAuthGameMode());
    if(Mode&&Mode->InputState()==SoraInput::Dialogue) return;
    // The rules' clock counts whole milliseconds; the fraction carries over.
    ClockCarryMs+=DeltaSeconds*1000.f;
    const int32 DeltaMs=FMath::FloorToInt32(ClockCarryMs);
    ClockCarryMs-=DeltaMs;
    if(RiderPawn.IsValid()) TickRidden(DeltaMs,DeltaSeconds);
    else if(Leader.IsValid()) TickLed(DeltaMs,DeltaSeconds);
    else if(Road&&PaceCmS>0) TickRoad(DeltaMs,DeltaSeconds);
    else SoraMountRules::Step(Ride,Rules,{DeltaMs});
    Animate(DeltaSeconds);
}
void ASoraHorse::TickRidden(int32 DeltaMs,float DeltaSeconds)
{
    using namespace SoraMountRules;
    ASoraPlayerCharacter* Rider=RiderPawn.Get();
    // The rider's hands act only in live play; otherwise she eases down.
    const bool bHands=Rider->CanPlay();
    const float Legs=bHands?Rider->GetInputAxisValue(TEXT("MoveForward")):0.f;
    const float Steer=bHands?FMath::Clamp(Rider->GetInputAxisValue(TEXT("MoveRight")),-1.f,1.f):0.f;
    FControl Control;
    Control.DeltaMs=DeltaMs;
    Control.Forward=Legs>.5f;
    Control.Urge=Control.Forward&&Rider->IsSprinting();
    Control.Rein=Legs<-.5f;
    Control.Cap=Cap;
    Control.Spook=bSpookPending;
    bSpookPending=false;
    Step(Ride,Rules,Control);
    float Yaw=GetActorRotation().Yaw;
    const float Turn=TurnDegS[Index(Ride.Gait)];
    // A ride that allows it (every chapter ride's auto_steer: setting) steers
    // itself while the player's auto-steer setting is on.
    const ASoraGameMode* Mode=Cast<ASoraGameMode>(GetWorld()->GetAuthGameMode());
    const bool bSteered=bAutoSteer&&Road&&Mode&&Mode->Settings()&&Mode->Settings()->AutoSteer();
    if(FMath::Abs(Steer)>.2f||!bSteered) Yaw+=Steer*Turn*DeltaSeconds;
    else if(Ride.Gait!=EGait::Halt)
    {
        // Auto-steer (accessibility): she keeps to the road a little ahead of her.
        const FVector2D Ahead=Road->PointAlong(Chainage+300.f+SpeedCmS()*.8f);
        const float Wanted=FMath::RadiansToDegrees(FMath::Atan2(Ahead.Y-GetActorLocation().Y,Ahead.X-GetActorLocation().X));
        Yaw+=FMath::Clamp(FRotator::NormalizeAxis(Wanted-Yaw),-Turn*DeltaSeconds,Turn*DeltaSeconds);
    }
    Move(FRotator(0,Yaw,0).Vector()*SpeedCmS()*DeltaSeconds,Yaw);
}
void ASoraHorse::TickLed(int32,float DeltaSeconds)
{
    // On a lead rope she trails her leader at the rope's length.
    const ASoraHorse* Front=Leader.Get();
    const FVector Wanted=Front->GetActorLocation()-Front->GetActorForwardVector()*LeadSpacing;
    FVector Offset=Wanted-GetActorLocation(); Offset.Z=0.f;
    const float Pace=FMath::Min(Offset.Size()/FMath::Max(DeltaSeconds,1e-3f),Front->SpeedCmS()+120.f);
    const float Yaw=Offset.Size()>20.f?Offset.Rotation().Yaw:GetActorRotation().Yaw;
    // Led and convoy horses carry no wind; their gait only shows their pace.
    Ride.Gait=HorseGaitForPace(Offset.Size()>20.f?Pace:0.f);
    Move(Offset.GetSafeNormal()*Pace*DeltaSeconds,Yaw);
}
void ASoraHorse::TickRoad(int32,float DeltaSeconds)
{
    // A convoy walks its road at its pace, and waits when told; a League
    // horse keeps its lane.
    if(!bWaiting) Chainage=FMath::Min(Chainage+PaceCmS*DeltaSeconds,Road->RouteLength);
    const bool bMoving=!bWaiting&&Chainage<Road->RouteLength;
    Ride.Gait=HorseGaitForPace(bMoving?PaceCmS:0.f);
    const float Yaw=Road->HeadingAt(Chainage);
    const FVector Lane=FRotator(0,Yaw+90.f,0).Vector()*LaneCm;
    SetActorLocationAndRotation(ASoraWorldBuilder::Floor(Road->PointAlong(Chainage),HorseFrameZ)+Lane,FRotator(0,Yaw,0));
}
void ASoraHorse::SetRoadChainage(float InChainage)
{
    if(!Road) return;
    Chainage=FMath::Clamp(InChainage,0.f,Road->RouteLength);
    const float Yaw=Road->HeadingAt(Chainage);
    SetActorLocationAndRotation(ASoraWorldBuilder::Floor(Road->PointAlong(Chainage),HorseFrameZ)+FRotator(0,Yaw+90.f,0).Vector()*LaneCm,
        FRotator(0,Yaw,0));
}
void ASoraHorse::SeatRider(bool bRival)
{
    // The charge places its riders; they sweep against nothing.
    Frame->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    // A League rider (a proxy until the rider rig lands): 陣笠 or the rival's
    // kabuto, 当世具足 in the League's indigo, a yari couched forward and a
    // sashimono with the SORA mon at his back.
    const FLinearColor Armour=bRival?FLinearColor(.05f,.05f,.07f):FLinearColor(.08f,.12f,.3f);
    const FLinearColor Lacing=bRival?FLinearColor(.45f,.08f,.05f):FLinearColor(.55f,.45f,.3f);
    const FLinearColor Fur(.42f,.4f,.37f),Haft(.28f,.17f,.08f),Steel(.62f,.64f,.66f),Banner(.92f,.9f,.84f),Mon(.8f,.1f,.06f);
    Part(Body,TEXT("RiderSeat"),HorseCube,FVector(0,0,140),FVector(.36f,.4f,.06f),Armour);
    Part(Body,TEXT("RiderHips"),HorseCylinder,FVector(-2,0,152),FVector(.34f,.34f,.24f),Armour);
    Part(Body,TEXT("RiderTorso"),HorseCylinder,FVector(2,0,184),FVector(.34f,.3f,.44f),Armour);
    Part(Body,TEXT("RiderOdoshi"),HorseCylinder,FVector(2,0,172),FVector(.36f,.32f,.06f),Lacing);
    Part(Body,TEXT("RiderHead"),HorseSphere,FVector(6,0,222),FVector(.24f,.22f,.24f),Fur);
    for(int32 Side:{-1,1})
    {
        Part(Body,FString::Printf(TEXT("RiderEar%d"),Side),HorseCone,FVector(4,Side*8,238),FVector(.06f,.06f,.08f),Fur);
        Part(Body,FString::Printf(TEXT("RiderThigh%d"),Side),HorseCylinder,FVector(8,Side*24,136),FVector(.14f,.14f,.36f),Armour,FRotator(0,0,Side*18));
    }
    if(bRival)
    {
        Part(Body,TEXT("RiderKabuto"),HorseSphere,FVector(6,0,232),FVector(.3f,.3f,.2f),Armour);
        Part(Body,TEXT("RiderKuwagata"),HorseCube,FVector(18,0,246),FVector(.02f,.3f,.16f),FLinearColor(.75f,.6f,.2f));
    }
    else Part(Body,TEXT("RiderJingasa"),HorseCone,FVector(6,0,236),FVector(.46f,.46f,.1f),FLinearColor(.1f,.07f,.05f));
    Part(Body,TEXT("RiderYari"),HorseCylinder,FVector(90,18,178),FVector(.035f,.035f,2.4f),Haft,FRotator(-80,0,0));
    Part(Body,TEXT("RiderYariHead"),HorseCone,FVector(208,18,199),FVector(.05f,.05f,.2f),Steel,FRotator(-80,0,0));
    Part(Body,TEXT("RiderSashimonoPole"),HorseCylinder,FVector(-22,0,236),FVector(.02f,.02f,1.1f),Haft);
    Part(Body,TEXT("RiderSashimono"),HorseCube,FVector(-22,-18,262),FVector(.01f,.36f,.5f),Banner);
    Part(Body,TEXT("RiderSashimonoMon"),HorseCylinder,FVector(-23,-18,266),FVector(.16f,.16f,.012f),Mon,FRotator(90,0,0));
}
void ASoraHorse::Move(const FVector& Delta,float Yaw)
{
    FHitResult Hit;
    SetActorLocationAndRotation(GetActorLocation()+Delta,FRotator(0,Yaw,0),true,&Hit);
    if(Hit.bBlockingHit)
    {
        // Slide along the wall; a horse meeting a wall head-on pulls up to a walk.
        const FVector Rest=FVector::VectorPlaneProject(Delta*(1.f-Hit.Time),Hit.Normal);
        SetActorLocation(GetActorLocation()+FVector(Rest.X,Rest.Y,0.f),true);
        if(FVector::DotProduct(Delta.GetSafeNormal(),Hit.Normal)<-.7f&&SoraMountRules::Index(Ride.Gait)>SoraMountRules::Index(SoraMountRules::EGait::Walk))
            Ride.Gait=SoraMountRules::EGait::Walk;
    }
    if(Road) Chainage=Road->ChainageOf(FVector2D(GetActorLocation()));
}
void ASoraHorse::Animate(float DeltaSeconds)
{
    const int32 G=SoraMountRules::Index(Ride.Gait);
    const float Pace=RiderPawn.IsValid()||Leader.IsValid()||Road?static_cast<float>(SpeedCmS()):0.f;
    LegPhase=FMath::Fmod(LegPhase+DeltaSeconds*Pace/HorseStrideCm[G],1.f);
    for(int32 Leg=0;Leg<Hips.Num();++Leg)
        if(Hips[Leg]) Hips[Leg]->SetRelativeRotation(FRotator(FMath::Sin(2.f*PI*(LegPhase+HorseFootfall[G][Leg]))*HorseSwingDeg[G],0,0));
    Body->SetRelativeLocation(FVector(0,0,-HorseFrameZ+FMath::Abs(FMath::Sin(2.f*PI*LegPhase))*HorseBobCm[G]));
    if(Head) Head->SetRelativeRotation(FRotator(FMath::Sin(2.f*PI*LegPhase)*HorseBobCm[G],0,0));
}
