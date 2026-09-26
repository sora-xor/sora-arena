#include "SoraPracticeActors.h"
#include "SoraPracticePawn.h"
#include "Components/InstancedStaticMeshComponent.h"
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
const TCHAR* const SoraPracticeArt::SoraMon=TEXT("/Game/Generated/UI/SM_SoraKamon.SM_SoraKamon");
const FLinearColor SoraPracticeArt::LedgerCyan(.1f,.75f,1.f);

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
// The imported SORA mon, loaded once. It is never redrawn: without the
// import there is no mark at all, and the error names the importer.
UStaticMesh* SoraMonMesh()
{
    static TWeakObjectPtr<UStaticMesh> Cache;
    static bool bReported=false;
    if(!Cache.IsValid()) Cache=LoadObject<UStaticMesh>(nullptr,SoraPracticeArt::SoraMon,nullptr,LOAD_NoWarn);
    if(!Cache.IsValid()&&!bReported)
    {
        bReported=true;
        UE_LOG(LogTemp,Error,TEXT("SORA mon mesh is missing: %s; run scripts/unreal/import_sora_kamon_mon.py"),SoraPracticeArt::SoraMon);
    }
    return Cache.Get();
}
// The ledger sigil's tally ring: notches in groups of five, the fifth
// longer, inside a closed rim.
constexpr int32 SigilNotches=30, SigilRim=40;
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
USceneComponent* SoraPracticeArt::Kamon(AActor* Owner,USceneComponent* Parent,const FString& Name,FVector Location,FRotator Rotation,float Diameter,float Thickness,bool bSora,FLinearColor Field,TArray<USceneComponent*>* Out)
{
    // A scene root turns the whole mark; parts are laid out facing +X.
    auto* Root=NewObject<USceneComponent>(Owner,MakeUniqueObjectName(Owner,USceneComponent::StaticClass(),FName(*(Name+TEXT("Root")))));
    Root->SetupAttachment(Parent); Root->SetRelativeLocation(Location); Root->SetRelativeRotation(Rotation);
    Root->RegisterComponent(); Owner->AddInstanceComponent(Root);
    if(Out) Out->Add(Root);
    // Discs lie in the mark's plane: the engine cylinder's axis turned to +X.
    // The mon's field sits just inside its rim and within its thickness.
    const float Across=bSora?Diameter*.996f:Diameter;
    UStaticMeshComponent* Disc=Part(Owner,Root,Name+(bSora?TEXT("Field"):TEXT("SigilDisc")),Cylinder,FVector::ZeroVector,
        FVector(Across,Across,bSora?Thickness*.6f:Thickness)/100.f,FRotator(90,0,0));
    if(Out) Out->Add(Disc);
    if(bSora)
    {
        // The field shows through the mon's open strokes; the mon, one metre
        // across and 1 cm thick as imported, stands proud of it on both faces
        // in the SVG's own red.
        Paint(Disc,Field,.8f);
        if(SoraMonMesh())
        {
            UStaticMeshComponent* Mon=Part(Owner,Root,Name+TEXT("SoraMon"),SoraMon,FVector::ZeroVector,FVector(Thickness,Diameter/100.f,Diameter/100.f));
            if(Out) Out->Add(Mon);
        }
        return Root;
    }
    // The Stellar Credit House's ledger sigil (story bible §17): a closed ring
    // of tally notches, cold cyan on graphite. It shares nothing with the mon.
    Paint(Disc,Field,.28f,.55f);
    auto* Tally=NewObject<UInstancedStaticMeshComponent>(Owner,MakeUniqueObjectName(Owner,UInstancedStaticMeshComponent::StaticClass(),FName(*(Name+TEXT("SigilTally")))));
    Tally->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,Cube));
    Tally->SetupAttachment(Root);
    Tally->SetCollisionEnabled(ECollisionEnabled::NoCollision); Tally->SetGenerateOverlapEvents(false); Tally->SetCanEverAffectNavigation(false);
    Tally->RegisterComponent(); Owner->AddInstanceComponent(Tally);
    if(Out) Out->Add(Tally);
    const float Depth=Thickness*1.3f/100.f;
    for(int32 Index=0;Index<SigilNotches;++Index)
    {
        const float Angle=Index*2*PI/SigilNotches;
        const bool bFifth=Index%5==4;
        const float Inner=Diameter*(bFifth?.22f:.29f), Outer=Diameter*.39f, Mid=(Inner+Outer)*.5f;
        Tally->AddInstance(FTransform(FRotator(0,0,-FMath::RadiansToDegrees(Angle)),FVector(0,FMath::Sin(Angle)*Mid,FMath::Cos(Angle)*Mid),
            FVector(Depth,Diameter*.022f/100.f,(Outer-Inner)/100.f)));
    }
    for(int32 Index=0;Index<SigilRim;++Index)
    {
        const float Angle=Index*2*PI/SigilRim, Reach=Diameter*.44f;
        Tally->AddInstance(FTransform(FRotator(0,0,-FMath::RadiansToDegrees(Angle)),FVector(0,FMath::Sin(Angle)*Reach,FMath::Cos(Angle)*Reach),
            FVector(Depth,2*PI*Reach/SigilRim*1.02f/100.f,Diameter*.028f/100.f)));
    }
    Glow(Tally,LedgerCyan,1.4f);
    return Root;
}
void SoraPracticeArt::Sashimono(AActor* Owner,USceneComponent* Parent,float HalfHeight,FLinearColor Color,bool bSora,bool bOwnerNoSee,TArray<USceneComponent*>* Out)
{
    TArray<USceneComponent*> Parts;
    const float Back=-24.f, Bottom=HalfHeight*.3f, Top=HalfHeight+48.f;
    // League flags are undyed silk carrying the red mon; the Credit House
    // and free-for-all rivals fly their own colour with the ledger sigil.
    const FLinearColor Lacquer(.05f,.035f,.03f), Cloth=bSora?FLinearColor(.80f,.76f,.66f):Color*.85f;
    UStaticMeshComponent* Pole=Part(Owner,Parent,TEXT("SashimonoPole"),Cylinder,FVector(Back,0,(Bottom+Top)*.5f),FVector(.028f,.028f,(Top-Bottom)/100.f));
    UStaticMeshComponent* Yard=Part(Owner,Parent,TEXT("SashimonoYard"),Cylinder,FVector(Back,0,Top-2.f),FVector(.022f,.022f,.36f),FRotator(0,0,90));
    // The flag hangs below the yard, flat across the wearer's back.
    UStaticMeshComponent* Flag=Part(Owner,Parent,TEXT("SashimonoFlag"),Cube,FVector(Back-2.f,0,Top-40.f),FVector(.012f,.32f,.72f));
    Paint(Pole,Lacquer,.35f); Paint(Yard,Lacquer,.35f); Paint(Flag,Cloth,.88f);
    Parts.Append({Pole,Yard,Flag});
    Kamon(Owner,Parent,TEXT("SashimonoKamon"),FVector(Back-2.f,0,Top-38.f),FRotator::ZeroRotator,23.f,1.6f,bSora,
        bSora?Cloth:FLinearColor(.035f,.038f,.045f),&Parts);
    for(USceneComponent* Component:Parts)
    {
        if(auto* Primitive=Cast<UPrimitiveComponent>(Component)) Primitive->SetOwnerNoSee(bOwnerNoSee);
        if(Out) Out->Add(Component);
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
            Kamon(this,RootComponent,FString::Printf(TEXT("BarricadeKamon%d"),Side),Face,FRotator(0,bAlongX?90.f:0.f,0),Diameter,.4f,bSora,
                bSora?FLinearColor(.93f,.90f,.84f):FLinearColor(.035f,.038f,.045f));
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
        Kamon(this,Talisman,TEXT("WardSeal"),FVector(0,0,8.f),FRotator::ZeroRotator,10.f,4.f,bSora,bSora?FLinearColor(.92f,.88f,.76f):FLinearColor(.035f,.038f,.045f));
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
    // The owner's mark lies at the centre, face up: the SORA mon, the ledger
    // sigil, or plain stone while nobody holds the point.
    SoraEmblem=Kamon(this,RootComponent,TEXT("ControlSora"),FVector(0,0,1.2f),FRotator(90,0,0),170.f,2.f,true,FLinearColor(.93f,.9f,.84f));
    SigilEmblem=Kamon(this,RootComponent,TEXT("ControlSigil"),FVector(0,0,1.2f),FRotator(90,0,0),170.f,2.f,false,FLinearColor(.035f,.038f,.045f));
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
    if(SoraEmblem) SoraEmblem->SetVisibility(Owner==0,true);
    if(SigilEmblem) SigilEmblem->SetVisibility(Owner==1,true);
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
        Kamon(this,RootComponent,FString::Printf(TEXT("PayloadGateKamon%d"),Index),At+Yaw.RotateVector(FVector(0,165.f,2.2f)),FRotator(90,Yaw.Yaw,0),60.f,1.6f,true,FLinearColor(.93f,.9f,.84f));
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
    Kamon(this,CartRoot,TEXT("CartKamon"),FVector(86,0,56),FRotator::ZeroRotator,30.f,1.2f,true,FLinearColor(.93f,.9f,.84f));
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
