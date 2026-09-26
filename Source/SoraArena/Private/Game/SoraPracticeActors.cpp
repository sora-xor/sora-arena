#include "SoraPracticeActors.h"
#include "SoraPracticePawn.h"
#include "Components/PointLightComponent.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"

const TCHAR* const SoraPracticeArt::Cube=TEXT("/Engine/BasicShapes/Cube.Cube");
const TCHAR* const SoraPracticeArt::Cylinder=TEXT("/Engine/BasicShapes/Cylinder.Cylinder");
const TCHAR* const SoraPracticeArt::Cone=TEXT("/Engine/BasicShapes/Cone.Cone");
const TCHAR* const SoraPracticeArt::Sphere=TEXT("/Engine/BasicShapes/Sphere.Sphere");

namespace
{
// Loaded once per session; a weak pointer so a garbage-collected asset reloads.
UMaterialInterface* CachedMaterial(TWeakObjectPtr<UMaterialInterface>& Cache,const TCHAR* Path)
{
    if(!Cache.IsValid()) Cache=LoadObject<UMaterialInterface>(nullptr,Path,nullptr,LOAD_NoWarn);
    return Cache.Get();
}
UMaterialInterface* SurfaceMaterial()
{
    static TWeakObjectPtr<UMaterialInterface> Cache;
    if(UMaterialInterface* Material=CachedMaterial(Cache,TEXT("/Game/Generated/Materials/M_ArenaSurface.M_ArenaSurface"))) return Material;
    static TWeakObjectPtr<UMaterialInterface> Fallback;
    return CachedMaterial(Fallback,TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"));
}
// The engine's additive emissive mesh material takes its colour from "Color".
UMaterialInterface* GlowMaterial()
{
    static TWeakObjectPtr<UMaterialInterface> Cache;
    static bool bChecked=false, bUsable=false;
    UMaterialInterface* Material=CachedMaterial(Cache,TEXT("/Engine/EngineMaterials/EmissiveMeshMaterial.EmissiveMeshMaterial"));
    if(Material&&!bChecked)
    {
        FLinearColor Probe;
        bUsable=Material->GetVectorParameterValue(FHashedMaterialParameterInfo(TEXT("Color")),Probe);
        bChecked=true;
    }
    return bUsable?Material:nullptr;
}
// The SORA mark in the 1024-pixel logo's coordinates: two bars, the stem
// between them and the two legs that run to the rim.
struct FMarkStroke { float X, Y, Width, Height, DirX, DirY; };
constexpr FMarkStroke SoraStrokes[]={
    {512.f,299.f,626.f,84.f,0.f,1.f},
    {512.f,384.f,84.f,86.f,0.f,1.f},
    {512.f,469.f,626.f,84.f,0.f,1.f},
    {368.2f,737.4f,84.f,489.f,-.5585f,.8296f},
    {655.8f,737.4f,84.f,489.f,.5585f,.8296f},
};
}

UStaticMeshComponent* SoraPracticeArt::Part(AActor* Owner,USceneComponent* Parent,const FString& Name,const TCHAR* Shape,FVector Location,FVector Scale,FRotator Rotation)
{
    auto* Mesh=NewObject<UStaticMeshComponent>(Owner,MakeUniqueObjectName(Owner,UStaticMeshComponent::StaticClass(),FName(*Name)));
    Mesh->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,Shape));
    if(Parent) Mesh->SetupAttachment(Parent);
    Mesh->SetRelativeLocation(Location); Mesh->SetRelativeRotation(Rotation); Mesh->SetRelativeScale3D(Scale);
    Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Mesh->SetGenerateOverlapEvents(false);
    Mesh->SetCanEverAffectNavigation(false);
    Mesh->RegisterComponent(); Owner->AddInstanceComponent(Mesh);
    return Mesh;
}
void SoraPracticeArt::Paint(UStaticMeshComponent* Mesh,FLinearColor Color,float Roughness,float Metallic)
{
    if(UMaterialInterface* Base=SurfaceMaterial())
    {
        auto* Material=UMaterialInstanceDynamic::Create(Base,Mesh);
        Material->SetVectorParameterValue(TEXT("BaseColor"),Color);
        Material->SetVectorParameterValue(TEXT("Color"),Color);
        Material->SetScalarParameterValue(TEXT("Roughness"),Roughness);
        Material->SetScalarParameterValue(TEXT("Metallic"),Metallic);
        Mesh->SetMaterial(0,Material);
    }
}
void SoraPracticeArt::Surface(UStaticMeshComponent* Mesh,const TCHAR* Role,FLinearColor Tint)
{
    const FString Path=FString::Printf(TEXT("/Game/Generated/Environment/MI_Nyaagyu_%s.MI_Nyaagyu_%s"),Role,Role);
    if(auto* Material=LoadObject<UMaterialInterface>(nullptr,*Path,nullptr,LOAD_NoWarn))
    {
        auto* Instance=UMaterialInstanceDynamic::Create(Material,Mesh);
        Instance->SetVectorParameterValue(TEXT("Tint"),Tint);
        Mesh->SetMaterial(0,Instance);
        return;
    }
    // Without the imported surfaces, a flat colour close to the role.
    Paint(Mesh,Tint*.45f,.8f,FCString::Strcmp(Role,TEXT("Metal"))==0?.8f:0.f);
}
void SoraPracticeArt::Glow(UStaticMeshComponent* Mesh,FLinearColor Color,float Strength)
{
    Mesh->SetCastShadow(false);
    if(UMaterialInterface* Base=GlowMaterial())
    {
        auto* Material=Cast<UMaterialInstanceDynamic>(Mesh->GetMaterial(0));
        if(!Material||Material->Parent!=Base) { Material=UMaterialInstanceDynamic::Create(Base,Mesh); Mesh->SetMaterial(0,Material); }
        Material->SetVectorParameterValue(TEXT("Color"),Color*Strength);
        return;
    }
    Paint(Mesh,Color,.3f);
}
UPointLightComponent* SoraPracticeArt::Light(AActor* Owner,USceneComponent* Parent,const FString& Name,FVector Location,FLinearColor Color,float Lumens,float Radius,bool bShadows)
{
    auto* Lamp=NewObject<UPointLightComponent>(Owner,MakeUniqueObjectName(Owner,UPointLightComponent::StaticClass(),FName(*Name)));
    if(Parent) Lamp->SetupAttachment(Parent);
    Lamp->SetRelativeLocation(Location);
    Lamp->SetIntensityUnits(ELightUnits::Lumens); Lamp->SetIntensity(Lumens);
    Lamp->SetAttenuationRadius(Radius); Lamp->SetLightColor(Color); Lamp->SetSourceRadius(8.f);
    Lamp->SetCastShadows(bShadows);
    Lamp->RegisterComponent(); Owner->AddInstanceComponent(Lamp);
    return Lamp;
}
void SoraPracticeArt::Kamon(AActor* Owner,USceneComponent* Parent,const FString& Name,FVector Location,FRotator Rotation,float Diameter,float Thickness,bool bSora,FLinearColor Field,FLinearColor Mark,TArray<UStaticMeshComponent*>* Out)
{
    // A scene root turns the whole mark; parts are laid out facing +X.
    auto* Root=NewObject<USceneComponent>(Owner,MakeUniqueObjectName(Owner,USceneComponent::StaticClass(),FName(*(Name+TEXT("Root")))));
    Root->SetupAttachment(Parent); Root->SetRelativeLocation(Location); Root->SetRelativeRotation(Rotation);
    Root->RegisterComponent(); Owner->AddInstanceComponent(Root);
    const auto Add=[&](UStaticMeshComponent* Mesh) { if(Out) Out->Add(Mesh); return Mesh; };
    Paint(Add(Part(Owner,Root,Name+TEXT("Field"),Cylinder,FVector::ZeroVector,FVector(Diameter/100.f,Diameter/100.f,Thickness/100.f),FRotator(90,0,0))),Field,.55f);
    // Mark strokes pass through the disc so both faces carry them, as on cloth.
    const float MarkDepth=Thickness*1.3f/100.f;
    const float Unit=Diameter/1024.f;
    if(bSora)
    {
        for(int32 Index=0;Index<UE_ARRAY_COUNT(SoraStrokes);++Index)
        {
            const FMarkStroke& S=SoraStrokes[Index];
            const FVector Center(0,(S.X-512.f)*Unit,-(S.Y-512.f)*Unit);
            // Image Y runs down; the stroke's long axis follows its direction.
            const FRotator Along=FRotationMatrix::MakeFromXZ(FVector::ForwardVector,FVector(0,S.DirX,-S.DirY)).Rotator();
            Paint(Add(Part(Owner,Root,FString::Printf(TEXT("%sStroke%d"),*Name,Index),Cube,Center,FVector(MarkDepth,S.Width*Unit/100.f,S.Height*Unit/100.f),Along)),Mark,.5f);
        }
        return;
    }
    // The invaders' mark: a debt coin with its square hole and four seals.
    Paint(Add(Part(Owner,Root,Name+TEXT("Hole"),Cube,FVector::ZeroVector,FVector(MarkDepth,Diameter*.28f/100.f,Diameter*.28f/100.f))),Mark,.4f,.3f);
    for(int32 Seal=0;Seal<4;++Seal)
    {
        const float Angle=Seal*PI*.5f;
        const FVector Center(0,FMath::Sin(Angle)*Diameter*.33f,FMath::Cos(Angle)*Diameter*.33f);
        const bool bVertical=Seal%2==0;
        Paint(Add(Part(Owner,Root,FString::Printf(TEXT("%sSeal%d"),*Name,Seal),Cube,Center,
            FVector(MarkDepth,(bVertical?.07f:.13f)*Diameter/100.f,(bVertical?.13f:.07f)*Diameter/100.f))),Mark,.4f,.3f);
    }
}
void SoraPracticeArt::Sashimono(AActor* Owner,USceneComponent* Parent,float HalfHeight,FLinearColor Color,bool bSora,bool bOwnerNoSee,TArray<UStaticMeshComponent*>* Out)
{
    TArray<UStaticMeshComponent*> Parts;
    const float Back=-24.f, Bottom=HalfHeight*.3f, Top=HalfHeight+48.f;
    const FLinearColor Lacquer(.05f,.035f,.03f), Cloth=Color*.85f;
    Paint(Parts.Add_GetRef(Part(Owner,Parent,TEXT("SashimonoPole"),Cylinder,FVector(Back,0,(Bottom+Top)*.5f),FVector(.028f,.028f,(Top-Bottom)/100.f))),Lacquer,.35f);
    Paint(Parts.Add_GetRef(Part(Owner,Parent,TEXT("SashimonoYard"),Cylinder,FVector(Back,0,Top-2.f),FVector(.022f,.022f,.36f),FRotator(0,0,90))),Lacquer,.35f);
    // The flag hangs below the yard, flat across the wearer's back.
    Paint(Parts.Add_GetRef(Part(Owner,Parent,TEXT("SashimonoFlag"),Cube,FVector(Back-2.f,0,Top-40.f),FVector(.012f,.32f,.72f))),Cloth,.88f);
    Kamon(Owner,Parent,TEXT("SashimonoKamon"),FVector(Back-2.f,0,Top-38.f),FRotator::ZeroRotator,23.f,1.6f,bSora,
        bSora?FLinearColor(.72f,.05f,.06f):FLinearColor(.72f,.74f,.70f),bSora?FLinearColor(.92f,.90f,.84f):FLinearColor(.05f,.06f,.07f),&Parts);
    for(UStaticMeshComponent* Mesh:Parts)
    {
        Mesh->SetOwnerNoSee(bOwnerNoSee);
        if(Out) Out->Add(Mesh);
    }
}
FLinearColor SoraPracticeArt::TeamColor(int32 Team)
{
    return Team==0?FLinearColor(.80f,.08f,.07f):FLinearColor(.06f,.55f,.78f);
}
FLinearColor SoraPracticeArt::SlotColor(int32 Slot)
{
    static const FLinearColor Palette[]={
        FLinearColor(.80f,.08f,.07f),FLinearColor(.06f,.55f,.78f),FLinearColor(.90f,.62f,.10f),FLinearColor(.48f,.20f,.72f),
        FLinearColor(.18f,.62f,.25f),FLinearColor(.86f,.84f,.76f),FLinearColor(.92f,.36f,.08f),FLinearColor(.12f,.24f,.72f)};
    return Palette[FMath::Abs(Slot)%UE_ARRAY_COUNT(Palette)];
}

ASoraPracticeEntityActor::ASoraPracticeEntityActor()
{
    PrimaryActorTick.bCanEverTick=true;
    RootComponent=CreateDefaultSubobject<USceneComponent>(TEXT("EntityRoot"));
}
void ASoraPracticeEntityActor::Present(const FSoraPracticeEntity& Entity,FLinearColor Color,bool bSora,const FSoraPracticePlayer* Owner,bool bAlienBody,const FSoraPracticeMap& Map)
{
    if(!bBuilt) Build(Entity,Color,bSora,Owner,bAlienBody,Map);
    Current=Entity;
}
void ASoraPracticeEntityActor::Build(const FSoraPracticeEntity& Entity,FLinearColor Color,bool bSora,const FSoraPracticePlayer* Owner,bool bAlienBody,const FSoraPracticeMap& Map)
{
    using namespace SoraPracticeArt;
    bBuilt=true; Current=Entity;
    SetActorLocation(Entity.Position);
    const float R=FMath::Max(Entity.Extent.X,1.f);
    switch(Entity.Kind)
    {
    case SoraPractice::Barricade:
    {
        // Exactly the kernel's box: a base plate, lacquered timber bays
        // between iron ribs along the long side, and a brass cap.
        const FVector Half(Entity.Extent.X,Entity.Extent.Y,0);
        const float H=Entity.Extent.Z;
        Box=Part(this,RootComponent,TEXT("BarricadeBlocker"),Cube,FVector(0,0,H*.5f),FVector(2*Half.X,2*Half.Y,H)/100.f);
        // Hidden: it only stops the cosmetic tracers where the kernel stops rays.
        Box->SetCollisionEnabled(ECollisionEnabled::QueryOnly); Box->SetCollisionResponseToAllChannels(ECR_Block);
        Box->SetVisibility(false);
        const float BaseH=FMath::Min(15.f,H*.1f), CapH=FMath::Min(12.f,H*.08f);
        Surface(Part(this,RootComponent,TEXT("BarricadeBase"),Cube,FVector(0,0,BaseH*.5f),FVector(2*Half.X,2*Half.Y,BaseH)/100.f),TEXT("Metal"),FLinearColor(.35f,.36f,.38f));
        Paint(Part(this,RootComponent,TEXT("BarricadeCap"),Cube,FVector(0,0,H-CapH*.5f),FVector(2*Half.X,2*Half.Y,CapH)/100.f),FLinearColor(.55f,.38f,.13f),.35f,.9f);
        const bool bAlongX=Half.X>=Half.Y;
        const float Long=2*(bAlongX?Half.X:Half.Y), BodyH=H-BaseH-CapH, Rib=8.f;
        const int32 Bays=FMath::Max(1,FMath::RoundToInt((Long-Rib)/70.f));
        const float Bay=(Long-Rib*(Bays+1))/Bays;
        float At=-Long*.5f;
        for(int32 Index=0;Index<=Bays;++Index)
        {
            const auto Piece=[&](const TCHAR* Name,float Start,float Length,bool bRib)
            {
                const float Mid=Start+Length*.5f;
                const FVector Center=bAlongX?FVector(Mid,0,BaseH+BodyH*.5f):FVector(0,Mid,BaseH+BodyH*.5f);
                const FVector Size=bAlongX?FVector(Length,2*Half.Y,BodyH):FVector(2*Half.X,Length,BodyH);
                auto* Mesh=Part(this,RootComponent,FString::Printf(TEXT("%s%d"),Name,Index),Cube,Center,Size/100.f);
                if(bRib) Surface(Mesh,TEXT("Metal"),FLinearColor(.28f,.29f,.3f)); else Surface(Mesh,TEXT("Timber"),FLinearColor(.55f,.22f,.14f));
            };
            Piece(TEXT("BarricadeRib"),At,Rib,true); At+=Rib;
            if(Index<Bays) { Piece(TEXT("BarricadeBay"),At,Bay,false); At+=Bay; }
        }
        // The owner's kamon on both long faces, sunk into the face.
        const float Diameter=FMath::Min(55.f,BodyH*.6f);
        for(int32 Side:{-1,1})
        {
            const FVector Face=bAlongX?FVector(0,Side*Half.Y,BaseH+BodyH*.55f):FVector(Side*Half.X,0,BaseH+BodyH*.55f);
            Kamon(this,RootComponent,FString::Printf(TEXT("BarricadeKamon%d"),Side),Face,FRotator(0,bAlongX?90.f:0.f,0),Diameter,.4f,bSora,Color,FLinearColor(.93f,.90f,.84f));
        }
        break;
    }
    case SoraPractice::FireZone:
    {
        // Hanabi's burning pitch: an ember bed of the kernel's radius and
        // tongues of flame that flicker; it damages players only.
        Glow(Part(this,RootComponent,TEXT("EmberBed"),Cylinder,FVector(0,0,1),FVector(2*R/100.f,2*R/100.f,.02f)),FLinearColor(1.f,.28f,.04f),.5f);
        for(int32 Index=0;Index<14;++Index)
        {
            const float Angle=Index*2.39996f, Reach=R*(.18f+.62f*((Index*37)%100)/100.f);
            auto* Flame=Part(this,RootComponent,FString::Printf(TEXT("Flame%d"),Index),Cone,FVector(FMath::Cos(Angle)*Reach,FMath::Sin(Angle)*Reach,24.f),FVector(.28f,.28f,.5f));
            Glow(Flame,FLinearColor(1.f,.42f,.08f),1.6f);
            Flames.Add(Flame);
        }
        Lamp=Light(this,RootComponent,TEXT("FireLight"),FVector(0,0,90),FLinearColor(1.f,.48f,.18f),2600.f,R*2.6f);
        break;
    }
    case SoraPractice::Ward:
    {
        // Kusushi's ward: a ring of the owner's colour at the kernel's radius
        // and a paper talisman turning high above head height.
        const int32 Count=40;
        for(int32 Index=0;Index<Count;++Index)
        {
            const float Angle=Index*2*PI/Count;
            Glow(Part(this,RootComponent,FString::Printf(TEXT("WardRing%d"),Index),Cube,FVector(FMath::Cos(Angle)*R,FMath::Sin(Angle)*R,1.5f),
                FVector(2*PI*R/Count*.7f/100.f,.06f,.03f),FRotator(0,FMath::RadiansToDegrees(Angle)+90.f,0)),Color,.9f);
        }
        Glow(Part(this,RootComponent,TEXT("WardFloor"),Cylinder,FVector(0,0,.6f),FVector(2*R/100.f,2*R/100.f,.01f)),Color,.05f);
        Talisman=NewObject<USceneComponent>(this,TEXT("WardTalisman"));
        Talisman->SetupAttachment(RootComponent); Talisman->SetRelativeLocation(FVector(0,0,245)); Talisman->RegisterComponent(); AddInstanceComponent(Talisman);
        Paint(Part(this,Talisman,TEXT("WardOfuda"),Cube,FVector::ZeroVector,FVector(.03f,.14f,.34f)),FLinearColor(.92f,.88f,.76f),.9f);
        Kamon(this,Talisman,TEXT("WardSeal"),FVector(0,0,8.f),FRotator::ZeroRotator,10.f,4.f,bSora,Color,FLinearColor(.95f,.93f,.86f));
        Lamp=Light(this,RootComponent,TEXT("WardLight"),FVector(0,0,210),Color,1400.f,R*1.4f);
        break;
    }
    case SoraPractice::Decoy:
    default:
    {
        // Shinobi's decoy stands as its owner did: same body, weapon and banner.
        FActorSpawnParameters Params; Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        Decoy=GetWorld()->SpawnActor<ASoraPracticePawn>(Entity.Position,FRotator(0,Entity.Yaw,0),Params);
        if(Decoy)
        {
            FSoraPracticePlayer Body;
            if(Owner) Body=*Owner;
            Body.Feet=Entity.Position; Body.Aim=FRotator(0,Entity.Yaw,0); Body.Alive=true; Body.Health=FMath::Max(1,Entity.Health);
            Decoy->InitDecoy(Body,Map,Color,bSora,bAlienBody);
        }
        break;
    }
    }
}
void ASoraPracticeEntityActor::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    Time+=DeltaSeconds;
    // Presentation motion only; the kernel's entity never moves.
    for(int32 Index=0;Index<Flames.Num();++Index)
        if(Flames[Index]) Flames[Index]->SetRelativeScale3D(FVector(.28f,.28f,.42f+.16f*FMath::Sin(Time*9.f+Index*1.7f)+.08f*FMath::Sin(Time*23.f+Index)));
    if(Talisman)
    {
        Talisman->SetRelativeRotation(FRotator(0,Time*45.f,0));
        Talisman->SetRelativeLocation(FVector(0,0,245.f+6.f*FMath::Sin(Time*1.6f)));
    }
    if(Lamp&&Current.Kind==SoraPractice::FireZone) Lamp->SetIntensity(2600.f*(.85f+.15f*FMath::Sin(Time*13.f)));
}
void ASoraPracticeEntityActor::Destroyed()
{
    if(IsValid(Decoy)) Decoy->Destroy();
    Decoy=nullptr;
    Super::Destroyed();
}

ASoraPracticeControlPoint::ASoraPracticeControlPoint()
{
    PrimaryActorTick.bCanEverTick=true;
    RootComponent=CreateDefaultSubobject<USceneComponent>(TEXT("ControlRoot"));
}
void ASoraPracticeControlPoint::Build(const FSoraPracticeMap& Map)
{
    using namespace SoraPracticeArt;
    Radius=Map.ControlRadius;
    SetActorLocation(Map.ControlCenter);
    Surface(Part(this,RootComponent,TEXT("ControlPlaza"),Cylinder,FVector(0,0,.6f),FVector(2*Radius/100.f,2*Radius/100.f,.012f)),TEXT("Stone"),FLinearColor(.86f,.82f,.74f));
    for(int32 Index=0;Index<Segments;++Index)
    {
        // Clockwise from north, as a clock face reads from above.
        const float Angle=Index*2*PI/Segments;
        const FVector At(FMath::Cos(Angle)*(Radius-10.f),FMath::Sin(Angle)*(Radius-10.f),1.6f);
        Ring.Add(Part(this,RootComponent,FString::Printf(TEXT("ControlLamp%d"),Index),Cube,At,FVector(2*PI*Radius/Segments*.78f/100.f,.12f,.028f),FRotator(0,FMath::RadiansToDegrees(Angle)+90.f,0)));
    }
    // The owner's kamon lies at the centre: SORA, the debt coin or plain stone.
    for(int32 Team=0;Team<2;++Team)
    {
        TArray<UStaticMeshComponent*> Pieces;
        Kamon(this,RootComponent,Team==0?TEXT("ControlSora"):TEXT("ControlCoin"),FVector(0,0,1.2f),FRotator(90,0,0),170.f,2.f,Team==0,TeamColor(Team),
            Team==0?FLinearColor(.93f,.9f,.84f):FLinearColor(.04f,.05f,.06f),&Pieces);
        for(UStaticMeshComponent* Piece:Pieces) (Team==0?SoraEmblem:CoinEmblem).Add(Piece);
    }
    Unclaimed=Part(this,RootComponent,TEXT("ControlUnclaimed"),Cylinder,FVector(0,0,1.2f),FVector(1.7f,1.7f,.02f));
    Surface(Unclaimed,TEXT("Stone"),FLinearColor(.55f,.53f,.5f));
    Beacon=Light(this,RootComponent,TEXT("ControlBeacon"),FVector(0,0,420),FLinearColor(1.f,.85f,.62f),5200.f,Radius*2.2f,true);
    Present(FSoraPracticeObjective(),0);
}
void ASoraPracticeControlPoint::Present(const FSoraPracticeObjective& Objective,uint32 Tick)
{
    using namespace SoraPracticeArt;
    const bool bNowLocked=Tick<Objective.UnlockTick;
    const int32 Progress=Objective.ControlProgress;
    const int32 NowLeading=Progress<0?0:Progress>0?1:INDEX_NONE;
    const int32 NowLit=FMath::Clamp(FMath::RoundToInt(FMath::Abs(Progress)*static_cast<float>(Segments)/FMath::Max(1,Objective.ControlCapture)),0,Segments);
    if(NowLit==Lit&&NowLeading==Leading&&Objective.ControlOwner==Owner&&Objective.Contested==bContested&&bNowLocked==bLocked) return;
    Lit=NowLit; Leading=NowLeading; Owner=Objective.ControlOwner; bContested=Objective.Contested; bLocked=bNowLocked;
    const FLinearColor Idle=Owner==INDEX_NONE?FLinearColor(.95f,.86f,.66f):TeamColor(Owner);
    for(int32 Index=0;Index<Ring.Num();++Index)
    {
        if(bLocked) Glow(Ring[Index],FLinearColor(.5f,.5f,.5f),.08f);
        else if(Index<Lit&&Leading!=INDEX_NONE) Glow(Ring[Index],TeamColor(Leading),1.4f);
        else Glow(Ring[Index],Idle,Owner==INDEX_NONE?.22f:.35f);
    }
    for(UStaticMeshComponent* Piece:SoraEmblem) Piece->SetVisibility(Owner==0);
    for(UStaticMeshComponent* Piece:CoinEmblem) Piece->SetVisibility(Owner==1);
    if(Unclaimed) Unclaimed->SetVisibility(Owner==INDEX_NONE);
    if(Beacon) Beacon->SetLightColor(Owner==INDEX_NONE?FLinearColor(1.f,.85f,.62f):TeamColor(Owner));
}
void ASoraPracticeControlPoint::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    Time+=DeltaSeconds;
    // A contested point's beacon falters; presentation only.
    if(Beacon) Beacon->SetIntensity(bContested?5200.f*(.55f+.45f*FMath::Abs(FMath::Sin(Time*6.f))):bLocked?1800.f:5200.f);
}

ASoraPracticePayload::ASoraPracticePayload()
{
    PrimaryActorTick.bCanEverTick=false;
    RootComponent=CreateDefaultSubobject<USceneComponent>(TEXT("PayloadRoot"));
}
void ASoraPracticePayload::Build(const FSoraPracticeMap& Map)
{
    using namespace SoraPracticeArt;
    Route=Map.Route;
    // Rails and sleepers along the kernel route, flat on the floor.
    for(int32 Index=1;Index<Route.Num();++Index)
    {
        const FVector A=Route[Index-1], B=Route[Index], Along=(B-A).GetSafeNormal2D();
        const float Length=FVector::Dist2D(A,B);
        const FRotator Yaw=Along.Rotation();
        const FVector Side=FVector(-Along.Y,Along.X,0);
        for(int32 Rail:{-1,1})
            Surface(Part(this,RootComponent,FString::Printf(TEXT("PayloadRail%d_%d"),Index,Rail),Cube,(A+B)*.5f+Side*Rail*55.f+FVector(0,0,1.75f),FVector((Length+10.f)/100.f,.06f,.015f),Yaw),TEXT("Metal"),FLinearColor(.4f,.4f,.42f));
        const int32 Sleepers=FMath::Max(1,FMath::FloorToInt(Length/120.f));
        for(int32 Sleeper=0;Sleeper<Sleepers;++Sleeper)
            Surface(Part(this,RootComponent,FString::Printf(TEXT("PayloadSleeper%d_%d"),Index,Sleeper),Cube,A+Along*(60.f+Sleeper*120.f)+FVector(0,0,.5f),FVector(.2f,1.5f,.01f),Yaw),TEXT("Timber"),FLinearColor(.34f,.22f,.14f));
    }
    // A brass gate band across the route at each checkpoint.
    for(int32 Index=0;Index<3;++Index)
    {
        const float Distance=Map.Checkpoints[Index];
        const FVector At=Map.RoutePoint(Distance), Ahead=Map.RoutePoint(Distance+10.f);
        const FRotator Yaw=(Ahead-At).GetSafeNormal2D().Rotation();
        Gates.Add(Part(this,RootComponent,FString::Printf(TEXT("PayloadGate%d"),Index),Cube,At+FVector(0,0,2.1f),FVector(.45f,2.6f,.018f),Yaw));
        Kamon(this,RootComponent,FString::Printf(TEXT("PayloadGateKamon%d"),Index),At+Yaw.RotateVector(FVector(0,165.f,2.2f)),FRotator(90,Yaw.Yaw,0),60.f,1.6f,true,TeamColor(0),FLinearColor(.93f,.9f,.84f));
    }
    // The cart: a timber daisha with four spoked wheels carrying Nyaagyu goods.
    CartRoot=NewObject<USceneComponent>(this,TEXT("PayloadCart"));
    CartRoot->SetupAttachment(RootComponent); CartRoot->RegisterComponent(); AddInstanceComponent(CartRoot);
    Surface(Part(this,CartRoot,TEXT("CartBed"),Cube,FVector(0,0,52),FVector(1.7f,1.1f,.16f)),TEXT("Timber"),FLinearColor(.62f,.42f,.26f));
    for(int32 Side:{-1,1})
    {
        Surface(Part(this,CartRoot,FString::Printf(TEXT("CartShaft%d"),Side),Cube,FVector(118,Side*40,48),FVector(.9f,.07f,.07f)),TEXT("Timber"),FLinearColor(.45f,.3f,.18f));
        for(int32 End:{-1,1})
        {
            auto* Wheel=Part(this,CartRoot,FString::Printf(TEXT("CartWheel%d_%d"),Side,End),Cylinder,FVector(End*55,Side*62,38),FVector(.76f,.76f,.12f),FRotator(0,0,90));
            Surface(Wheel,TEXT("Timber"),FLinearColor(.36f,.24f,.15f));
            Wheels.Add(Wheel);
        }
    }
    UStaticMesh* Goods=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/Generated/Environment/Props/SM_Nyaagyu_CargoStack.SM_Nyaagyu_CargoStack"),nullptr,LOAD_NoWarn);
    if(Goods)
    {
        auto* Cargo=Part(this,CartRoot,TEXT("CartGoods"),Cube,FVector(0,0,60),FVector(.6f));
        Cargo->SetStaticMesh(Goods);
    }
    else
        for(int32 Crate=0;Crate<3;++Crate)
            Surface(Part(this,CartRoot,FString::Printf(TEXT("CartCrate%d"),Crate),Cube,FVector(-45+Crate*45,0,85+Crate%2*10),FVector(.4f,.8f,.5f+Crate%2*.2f)),TEXT("Timber"),FLinearColor(.7f,.5f,.3f));
    Kamon(this,CartRoot,TEXT("CartKamon"),FVector(86,0,56),FRotator::ZeroRotator,30.f,1.2f,true,TeamColor(0),FLinearColor(.93f,.9f,.84f));
    CartLamp=Light(this,CartRoot,TEXT("CartLamp"),FVector(0,0,190),FLinearColor(1.f,.72f,.42f),1500.f,700.f);
    const int32 Count=36;
    for(int32 Index=0;Index<Count;++Index)
    {
        const float Angle=Index*2*PI/Count;
        PushRing.Add(Part(this,CartRoot,FString::Printf(TEXT("PushRing%d"),Index),Cube,FVector(FMath::Cos(Angle)*Map.PushRadius,FMath::Sin(Angle)*Map.PushRadius,1.4f),
            FVector(2*PI*Map.PushRadius/Count*.6f/100.f,.08f,.02f),FRotator(0,FMath::RadiansToDegrees(Angle)+90.f,0)));
    }
    Present(FSoraPracticeObjective(),Map.RoutePoint(0.f));
}
void ASoraPracticePayload::Present(const FSoraPracticeObjective& Objective,FVector Position)
{
    using namespace SoraPracticeArt;
    // Heading follows the route segment under the cart.
    FVector Ahead=FVector::ForwardVector;
    float Remaining=Objective.PayloadProgress;
    for(int32 Index=1;Index<Route.Num();++Index)
    {
        const float Length=FVector::Dist2D(Route[Index-1],Route[Index]);
        Ahead=(Route[Index]-Route[Index-1]).GetSafeNormal2D();
        if(Remaining<Length) break;
        Remaining-=Length;
    }
    Travelled+=FVector::Dist2D(Position,LastPosition)*(LastPosition.IsZero()?0.f:1.f);
    LastPosition=Position;
    CartRoot->SetWorldLocationAndRotation(Position,Ahead.Rotation());
    for(UStaticMeshComponent* Wheel:Wheels) Wheel->SetRelativeRotation(FRotator(-FMath::RadiansToDegrees(Travelled/38.f),0,90));
    // The ring shows who holds the cart: attackers pushing, contested, idle
    // or rolling back.
    const int32 State=Objective.PayloadAttackers>0&&Objective.PayloadDefenders>0?1:Objective.PayloadAttackers>0?2
        :Objective.PayloadIdle>=Objective.PayloadRollbackDelay&&Objective.PayloadRollbackDelay>0?3:0;
    if(State!=RingState)
    {
        RingState=State;
        const FLinearColor Color=State==1?FLinearColor(1.f,.72f,.15f):State==2?TeamColor(0):State==3?TeamColor(1):FLinearColor(.95f,.86f,.66f);
        for(UStaticMeshComponent* Segment:PushRing) Glow(Segment,Color,State==0?.25f:1.1f);
    }
    if(Objective.PayloadCheckpoints!=Reached)
    {
        Reached=Objective.PayloadCheckpoints;
        for(int32 Index=0;Index<Gates.Num();++Index)
            if(Index<Reached) Glow(Gates[Index],TeamColor(0),1.2f);
            else Paint(Gates[Index],FLinearColor(.58f,.42f,.16f),.35f,.9f);
    }
}
