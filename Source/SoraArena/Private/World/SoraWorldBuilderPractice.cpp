#include "SoraWorldBuilder.h"
#include "ArenaKernelSubsystem.h"
#include "SoraPracticeActors.h"
#include "World/SoraPracticeArena.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/PointLight.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"

// Deterministic practice: the Rust kernel's arena. The ground slab and one
// hidden box per kernel wall are the only collision; every visible piece
// follows the rules in World/SoraPracticeArena.h.
void ASoraWorldBuilder::BuildPractice(int32 MapId,const FSoraPracticeMap& Map)
{
    ClearArena();
    FSoraPracticeArenaKit Kit(*this,Map);
    const FVector Size=Map.Maximum-Map.Minimum;
    const FVector Center=(Map.Minimum+Map.Maximum)*.5;
    // The ground reaches well past the perimeter so the view over the walls
    // lands on ground; its top is the kernel's floor.
    static const TCHAR* GroundRole[]={TEXT("TerrainSoil"),TEXT("Stone"),TEXT("Stone"),TEXT("Stone")};
    static const FLinearColor GroundTint[]={FLinearColor(1,1,1),FLinearColor(.78f,.74f,.68f),FLinearColor(.52f,.5f,.48f),FLinearColor(.42f,.44f,.5f)};
    auto* Ground=Box(TEXT("KernelGround"),FVector(Center.X,Center.Y,Map.Minimum.Z-25),FVector(Size.X+6000,Size.Y+6000,50),FLinearColor(.2,.22,.18),true);
    Surface(Ground,GroundRole[MapId],GroundTint[MapId]);
    Ground->ComponentTags.Add(TEXT("KernelGround"));
    for(int32 I=0;I<Map.Walls.Num();++I)
    {
        const FSoraPracticeWall& Wall=Map.Walls[I];
        // Exactly the kernel's wall: it stops cosmetic tracers, the spectator
        // camera and the HUD's sight checks where the kernel stops rays.
        auto* Collision=Box(FString::Printf(TEXT("KernelWall%d"),I),(Wall.Minimum+Wall.Maximum)*.5,Wall.Maximum-Wall.Minimum,FLinearColor(.3,.31,.29),true);
        Collision->SetVisibility(false);
        Collision->ComponentTags.Add(TEXT("KernelWall"));
        Kit.bWallPieces=true;
        switch(MapId)
        {
        case 0: SoraPracticeDressing::EstateWall(Kit,Wall,I); break;
        case 1: SoraPracticeDressing::LanternWardWall(Kit,Wall,I); break;
        case 2: SoraPracticeDressing::SilkFoundryWall(Kit,Wall,I); break;
        default: SoraPracticeDressing::DebtCitadelWall(Kit,Wall,I); break;
        }
        Kit.bWallPieces=false;
    }
    switch(MapId)
    {
    case 0: SoraPracticeDressing::EstateGrounds(Kit); break;
    case 1: SoraPracticeDressing::LanternWardGrounds(Kit); break;
    case 2: SoraPracticeDressing::SilkFoundryGrounds(Kit); break;
    default: SoraPracticeDressing::DebtCitadelGrounds(Kit); break;
    }
    SoraPracticeDressing::Hazards(Kit);
    Lighting(MapId);
}

void FSoraPracticeArenaKit::Place(const FString& Look,TFunctionRef<void(UStaticMeshComponent*)> Style,const FVector& Center,const FVector& Size,FRotator Rotation)
{
    // One instanced component per look and group: the whole arena draws in a
    // few dozen batches instead of thousands of components.
    UInstancedStaticMeshComponent*& Batch=Batches.FindOrAdd((bWallPieces?TEXT("Wall|"):TEXT("Ground|"))+Look);
    if(!Batch)
    {
        Batch=NewObject<UInstancedStaticMeshComponent>(&Builder,MakeUniqueObjectName(&Builder,UInstancedStaticMeshComponent::StaticClass(),TEXT("PracticeBatch")));
        Batch->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,SoraPracticeArt::Cube));
        Batch->SetupAttachment(Builder.GetRootComponent());
        Batch->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Batch->SetGenerateOverlapEvents(false);
        Batch->SetCanEverAffectNavigation(false);
        Batch->ComponentTags.Add(bWallPieces?TEXT("PracticeWallPiece"):TEXT("PracticeGroundPiece"));
        Batch->RegisterComponent(); Builder.AddInstanceComponent(Batch); Builder.Pieces.Add(Batch);
        Style(Batch);
    }
    Batch->AddInstance(FTransform(Rotation,Center,Size/100.f),true);
    ++Pieces;
}
void FSoraPracticeArenaKit::Block(const FVector& Minimum,const FVector& Maximum,const TCHAR* Role,FLinearColor Tint)
{
    Place(FString::Printf(TEXT("Surface|%s|%s"),Role,*Tint.ToString()),[Role,Tint](UStaticMeshComponent* Mesh) { SoraPracticeArt::Surface(Mesh,Role,Tint); },
        (Minimum+Maximum)*.5,Maximum-Minimum,FRotator::ZeroRotator);
}
void FSoraPracticeArenaKit::Painted(const FVector& Minimum,const FVector& Maximum,FLinearColor Color,float Roughness,float Metallic)
{
    Place(FString::Printf(TEXT("Paint|%s|%.3f|%.3f"),*Color.ToString(),Roughness,Metallic),[Color,Roughness,Metallic](UStaticMeshComponent* Mesh) { SoraPracticeArt::Paint(Mesh,Color,Roughness,Metallic); },
        (Minimum+Maximum)*.5,Maximum-Minimum,FRotator::ZeroRotator);
}
void FSoraPracticeArenaKit::Lit(const FVector& Minimum,const FVector& Maximum,FLinearColor Color,float Strength)
{
    Place(FString::Printf(TEXT("Glow|%s|%.3f"),*Color.ToString(),Strength),[Color,Strength](UStaticMeshComponent* Mesh) { SoraPracticeArt::Glow(Mesh,Color,Strength); },
        (Minimum+Maximum)*.5,Maximum-Minimum,FRotator::ZeroRotator);
}
void FSoraPracticeArenaKit::Lamp(FVector Location,FLinearColor Color,float Lumens,float Radius,bool bShadows)
{
    // A light actor, so ClearArena removes it with the rest of the dressing.
    auto* Light=Builder.GetWorld()->SpawnActor<APointLight>(Location,FRotator::ZeroRotator);
    auto* Component=Light->PointLightComponent.Get();
    Component->SetIntensityUnits(ELightUnits::Lumens); Component->SetIntensity(Lumens);
    Component->SetAttenuationRadius(Radius); Component->SetLightColor(Color); Component->SetSourceRadius(10.f);
#if PLATFORM_MAC
    // Conventional local-light shadows are costly on the M1 preset.
    Component->SetCastShadows(false);
#else
    Component->SetCastShadows(bShadows);
#endif
    Builder.DecorActors.Add(Light);
}
void FSoraPracticeArenaKit::EstateTerrain() { Builder.NyaagyuTerrain(); }
void FSoraPracticeArenaKit::Tree(FVector Location,FRotator Rotation,float Scale) { Builder.NyaagyuTree(Location,Rotation,Scale); ++Pieces; }
bool FSoraPracticeArenaKit::Prop(const TCHAR* Asset,FVector Location,FRotator Rotation,float Scale)
{
    const bool bPlaced=Builder.ImportedProp(Asset,Location,Rotation,Scale);
    Pieces+=bPlaced?1:0;
    return bPlaced;
}
void FSoraPracticeArenaKit::Adopt(UStaticMeshComponent* Mesh) { Builder.Pieces.Add(Mesh); ++Pieces; }
float FSoraPracticeArenaKit::Height(const FSoraPracticeWall& Wall) { return Wall.Maximum.Z-Wall.Minimum.Z; }
bool FSoraPracticeArenaKit::Labelled(const FSoraPracticeWall& Wall,const TCHAR* Word) { return Wall.Label.Contains(Word); }
void FSoraPracticeArenaKit::Course(const FSoraPracticeWall& Wall,float Bottom,float Top,const TCHAR* Role,FLinearColor Tint)
{
    if(Top<=Bottom) return;
    Block(FVector(Wall.Minimum.X,Wall.Minimum.Y,Wall.Minimum.Z+Bottom),FVector(Wall.Maximum.X,Wall.Maximum.Y,Wall.Minimum.Z+Top),Role,Tint);
}
void FSoraPracticeArenaKit::PaintedCourse(const FSoraPracticeWall& Wall,float Bottom,float Top,FLinearColor Color,float Roughness,float Metallic)
{
    if(Top<=Bottom) return;
    Painted(FVector(Wall.Minimum.X,Wall.Minimum.Y,Wall.Minimum.Z+Bottom),FVector(Wall.Maximum.X,Wall.Maximum.Y,Wall.Minimum.Z+Top),Color,Roughness,Metallic);
}
void FSoraPracticeArenaKit::Bays(const FSoraPracticeWall& Wall,float Bottom,float Top,float Spacing,float Post,const TCHAR* PostRole,FLinearColor PostTint,const TCHAR* PanelRole,FLinearColor PanelTint)
{
    if(Top<=Bottom) return;
    const FVector Min(Wall.Minimum.X,Wall.Minimum.Y,Wall.Minimum.Z+Bottom), Max(Wall.Maximum.X,Wall.Maximum.Y,Wall.Minimum.Z+Top);
    const bool bAlongX=Max.X-Min.X>=Max.Y-Min.Y;
    const float Start=bAlongX?Min.X:Min.Y, Length=bAlongX?Max.X-Min.X:Max.Y-Min.Y;
    const int32 Count=FMath::Max(1,FMath::RoundToInt((Length-Post)/FMath::Max(Spacing,Post+1.f)));
    const float Panel=(Length-Post*(Count+1))/Count;
    if(Panel<=1.f) { Block(Min,Max,PostRole,PostTint); return; }
    // Slices along the long side; each spans the whole thickness and height.
    const auto Slice=[&](float From,float To,bool bPost)
    {
        FVector A=Min, B=Max;
        if(bAlongX) { A.X=From; B.X=To; } else { A.Y=From; B.Y=To; }
        if(bPost) Block(A,B,PostRole,PostTint);
        else if(PanelRole) Block(A,B,PanelRole,PanelTint);
        else Painted(A,B,PanelTint,.85f);
    };
    float At=Start;
    for(int32 Index=0;Index<Count;++Index)
    {
        Slice(At,At+Post,true); At+=Post;
        Slice(At,At+Panel,false); At+=Panel;
    }
    // The last post ends exactly on the wall's end.
    Slice(At,Start+Length,true);
}
void FSoraPracticeArenaKit::LitCourse(const FSoraPracticeWall& Wall,float Bottom,float Top,const TCHAR* FrameRole,FLinearColor FrameTint,FLinearColor Core,FLinearColor Glow,float Strength,float Spacing,float Pane)
{
    constexpr float Skin=2.f, Rail=6.f;
    const FVector Min(Wall.Minimum.X,Wall.Minimum.Y,Wall.Minimum.Z+Bottom), Max(Wall.Maximum.X,Wall.Maximum.Y,Wall.Minimum.Z+Top);
    const FVector Size=Max-Min;
    if(Size.Z<=2*Rail+2.f||Size.X<=4*Skin||Size.Y<=4*Skin)
    {
        Block(Min,Max,FrameRole,FrameTint);
        return;
    }
    // An opaque core, so the lit panes never show through the wall.
    Painted(Min+FVector(Skin,Skin,0),Max-FVector(Skin,Skin,0),Core,.9f);
    // The four skins: the Y faces run the full length, the X faces fit between.
    struct FFace { FVector A, B; bool bAlongX; };
    const FFace Faces[4]={
        {Min,FVector(Max.X,Min.Y+Skin,Max.Z),true},
        {FVector(Min.X,Max.Y-Skin,Min.Z),Max,true},
        {FVector(Min.X,Min.Y+Skin,Min.Z),FVector(Min.X+Skin,Max.Y-Skin,Max.Z),false},
        {FVector(Max.X-Skin,Min.Y+Skin,Min.Z),FVector(Max.X,Max.Y-Skin,Max.Z),false}};
    for(const FFace& Face:Faces)
    {
        // Rails top and bottom; between them, frame and panes alternate.
        Block(Face.A,FVector(Face.B.X,Face.B.Y,Face.A.Z+Rail),FrameRole,FrameTint);
        Block(FVector(Face.A.X,Face.A.Y,Face.B.Z-Rail),Face.B,FrameRole,FrameTint);
        const float Start=Face.bAlongX?Face.A.X:Face.A.Y, Length=Face.bAlongX?Face.B.X-Face.A.X:Face.B.Y-Face.A.Y;
        const int32 Cells=FMath::Max(1,FMath::FloorToInt(Length/FMath::Max(Spacing,1.f)));
        const float Cell=Length/Cells, Glass=FMath::Clamp(Pane,0.f,Cell-4.f), Side=(Cell-Glass)*.5f;
        for(int32 Index=0;Index<Cells;++Index)
        {
            const float From=Start+Index*Cell;
            const float Cuts[4]={From,From+Side,From+Side+Glass,From+Cell};
            for(int32 Part=0;Part<3;++Part)
            {
                if(Cuts[Part+1]-Cuts[Part]<=.01f) continue;
                FVector A(Face.A.X,Face.A.Y,Face.A.Z+Rail), B(Face.B.X,Face.B.Y,Face.B.Z-Rail);
                if(Face.bAlongX) { A.X=Cuts[Part]; B.X=Cuts[Part+1]; } else { A.Y=Cuts[Part]; B.Y=Cuts[Part+1]; }
                if(Part==1) Lit(A,B,Glow,Strength);
                else Block(A,B,FrameRole,FrameTint);
            }
        }
    }
}
bool FSoraPracticeArenaKit::FittedProp(const TCHAR* Asset,const FVector& Minimum,const FVector& Maximum,float MaxStretch)
{
    const FString Path=FString::Printf(TEXT("/Game/Generated/Environment/Props/%s.%s"),Asset,Asset);
    UStaticMesh* Mesh=LoadObject<UStaticMesh>(nullptr,*Path,nullptr,LOAD_NoWarn);
    if(!Mesh) return false;
    const FBox Local=Mesh->GetBoundingBox();
    const FVector LocalSize=Local.GetSize(), Size=Maximum-Minimum;
    float BestStretch=MAX_flt; int32 BestYaw=0; FVector BestScale=FVector::OneVector;
    for(const int32 Yaw:{0,90})
    {
        const FVector Turned=Yaw==0?LocalSize:FVector(LocalSize.Y,LocalSize.X,LocalSize.Z);
        if(Turned.GetMin()<=1.f) continue;
        const FVector Scale=Size/Turned;
        const float Stretch=Scale.GetMax()/Scale.GetMin();
        if(Stretch<BestStretch) { BestStretch=Stretch; BestYaw=Yaw; BestScale=Scale; }
    }
    if(BestStretch>MaxStretch) return false;
    // Scale applies in the prop's own axes, before its turn.
    const FVector LocalScale=BestYaw==0?BestScale:FVector(BestScale.Y,BestScale.X,BestScale.Z);
    const FRotator Rotation(0,BestYaw,0);
    const FVector Location=(Minimum+Maximum)*.5-Rotation.RotateVector(Local.GetCenter()*LocalScale);
    if(!Builder.ImportedProp(Asset,Location,Rotation,1.f)) return false;
    Builder.Pieces.Last()->SetRelativeScale3D(LocalScale);
    Builder.Pieces.Last()->ComponentTags.Add(TEXT("FittedProp"));
    ++Pieces;
    return true;
}
bool FSoraPracticeArenaKit::FittedRun(const TCHAR* Asset,const FSoraPracticeWall& Wall,float ModuleLength,float MaxStretch)
{
    const FVector Size=Wall.Maximum-Wall.Minimum;
    const bool bAlongX=Size.X>=Size.Y;
    const float Length=bAlongX?Size.X:Size.Y;
    const int32 Count=FMath::Max(1,FMath::RoundToInt(Length/ModuleLength));
    const float Step=Length/Count;
    for(int32 Index=0;Index<Count;++Index)
    {
        FVector A=Wall.Minimum, B=Wall.Maximum;
        if(bAlongX) { A.X+=Index*Step; B.X=A.X+Step; } else { A.Y+=Index*Step; B.Y=A.Y+Step; }
        // Every segment is the same size, so the first decides for all.
        if(!FittedProp(Asset,A,B,MaxStretch)) { check(Index==0); return false; }
    }
    return true;
}
void FSoraPracticeArenaKit::Strip(FVector A,FVector B,float Width,float StripHeight,const TCHAR* Role,FLinearColor Tint)
{
    const FVector Along=(B-A).GetSafeNormal2D();
    const float Length=FVector::Dist2D(A,B)+Width;
    Place(FString::Printf(TEXT("Surface|%s|%s"),Role,*Tint.ToString()),[Role,Tint](UStaticMeshComponent* Mesh) { SoraPracticeArt::Surface(Mesh,Role,Tint); },
        FVector((A.X+B.X)*.5,(A.Y+B.Y)*.5,Map.Minimum.Z+StripHeight*.5f),FVector(Length,Width,StripHeight),Along.Rotation());
}

// Architectural styles shared by the arenas. Heights run from the wall's
// base; each style fills its wall's box exactly.
namespace SoraPracticeDressing
{
void PlasterWall(FSoraPracticeArenaKit& Kit,const FSoraPracticeWall& Wall,FLinearColor Plaster)
{
    // A tsuiji wall: stone footing, lime plaster, a timber rail and tiled coping.
    const float H=FSoraPracticeArenaKit::Height(Wall), Footing=FMath::Min(60.f,.15f*H), Cap=FMath::Min(70.f,.14f*H), Rail=FMath::Min(12.f,.03f*H);
    Kit.Course(Wall,0,Footing,TEXT("Stone"),FLinearColor(.75f,.72f,.68f));
    Kit.Course(Wall,Footing,H-Cap-Rail,TEXT("Plaster"),Plaster);
    Kit.Course(Wall,H-Cap-Rail,H-Cap,TEXT("Timber"),FLinearColor(.34f,.25f,.2f));
    Kit.Course(Wall,H-Cap,H,TEXT("Kawara"),FLinearColor(.82f,.84f,.87f));
}
void Townhouse(FSoraPracticeArenaKit& Kit,const FSoraPracticeWall& Wall,FLinearColor Plaster,bool bLattice,bool bLit)
{
    // Stone footing and sill, a latticed or timber-framed lower storey, lit
    // shoji, a plastered upper storey between posts and a tiled roof band.
    const float H=FSoraPracticeArenaKit::Height(Wall);
    const float Footing=FMath::Min(45.f,.1f*H), Sill=Footing+15.f, Roof=FMath::Min(100.f,.18f*H);
    const float Lower=FMath::Min(260.f,.45f*H), Shoji=bLit?FMath::Min(80.f,.15f*H):0.f;
    const FLinearColor Dark(.3f,.21f,.16f);
    Kit.Course(Wall,0,Footing,TEXT("Stone"),FLinearColor(.72f,.7f,.66f));
    Kit.Course(Wall,Footing,Sill,TEXT("Timber"),Dark);
    if(bLattice) Kit.Bays(Wall,Sill,Lower,14.f,7.f,TEXT("Timber"),Dark,nullptr,FLinearColor(.05f,.035f,.03f));
    else Kit.Bays(Wall,Sill,Lower,180.f,20.f,TEXT("Timber"),Dark,TEXT("Plaster"),Plaster);
    if(bLit) Kit.LitCourse(Wall,Lower,Lower+Shoji,TEXT("Timber"),Dark,FLinearColor(.26f,.2f,.14f),FLinearColor(1.f,.62f,.28f),.9f,160.f,90.f);
    Kit.Bays(Wall,Lower+Shoji,H-Roof,200.f,20.f,TEXT("Timber"),Dark,TEXT("Plaster"),Plaster);
    Kit.Course(Wall,H-Roof,H,TEXT("Kawara"),FLinearColor(.8f,.82f,.85f));
}
void Storehouse(FSoraPracticeArenaKit& Kit,const FSoraPracticeWall& Wall)
{
    // A kura: namako tiling below, thick white plaster, a black band and tiles.
    const float H=FSoraPracticeArenaKit::Height(Wall), Namako=FMath::Min(170.f,.35f*H);
    Kit.Course(Wall,0,40,TEXT("Stone"),FLinearColor(.7f,.68f,.64f));
    Kit.Bays(Wall,40,Namako,40.f,6.f,TEXT("Plaster"),FLinearColor(.95f,.95f,.92f),nullptr,FLinearColor(.12f,.13f,.14f));
    Kit.Course(Wall,Namako,H-90,TEXT("Plaster"),FLinearColor(.97f,.96f,.93f));
    Kit.PaintedCourse(Wall,H-90,H-70,FLinearColor(.07f,.06f,.06f),.5f);
    Kit.Course(Wall,H-70,H,TEXT("Kawara"),FLinearColor(.84f,.86f,.88f));
}
void StoneLantern(FSoraPracticeArenaKit& Kit,const FSoraPracticeWall& Wall)
{
    // A toro: stone base and shaft, a lit firebox and a heavy cap.
    const float H=FSoraPracticeArenaKit::Height(Wall);
    Kit.Course(Wall,0,30,TEXT("Stone"),FLinearColor(.7f,.68f,.64f));
    Kit.Course(Wall,30,H-85,TEXT("Stone"),FLinearColor(.8f,.78f,.74f));
    Kit.LitCourse(Wall,H-85,H-35,TEXT("Stone"),FLinearColor(.66f,.64f,.6f),FLinearColor(.2f,.16f,.12f),FLinearColor(1.f,.6f,.25f),1.4f,30.f,18.f);
    Kit.Course(Wall,H-35,H,TEXT("Stone"),FLinearColor(.56f,.55f,.53f));
    const FVector Center=(Wall.Minimum+Wall.Maximum)*.5;
    Kit.Lamp(FVector(Center.X,Center.Y,Wall.Minimum.Z+H-60.f),FLinearColor(1.f,.66f,.36f),700.f,700.f);
}
void Screen(FSoraPracticeArenaKit& Kit,const FSoraPracticeWall& Wall)
{
    // A veranda screen: a timber frame and washi panes.
    const float H=FSoraPracticeArenaKit::Height(Wall);
    Kit.Course(Wall,0,10,TEXT("Timber"),FLinearColor(.3f,.21f,.16f));
    Kit.Bays(Wall,10,H-10,90.f,6.f,TEXT("Timber"),FLinearColor(.3f,.21f,.16f),nullptr,FLinearColor(.93f,.9f,.82f));
    Kit.Course(Wall,H-10,H,TEXT("Timber"),FLinearColor(.3f,.21f,.16f));
}
void Hedge(FSoraPracticeArenaKit& Kit,const FSoraPracticeWall& Wall)
{
    // Clipped planting on a stone kerb, pruned in cloud layers.
    const float H=FSoraPracticeArenaKit::Height(Wall), Layer=(H-35.f)/3.f;
    Kit.Course(Wall,0,35,TEXT("Stone"),FLinearColor(.66f,.64f,.6f));
    const FLinearColor Greens[3]={FLinearColor(.07f,.16f,.05f),FLinearColor(.09f,.2f,.06f),FLinearColor(.11f,.23f,.07f)};
    for(int32 Index=0;Index<3;++Index) Kit.PaintedCourse(Wall,35.f+Index*Layer,35.f+(Index+1)*Layer,Greens[Index],.95f);
}
void Goods(FSoraPracticeArenaKit& Kit,const FSoraPracticeWall& Wall)
{
    // Stacked goods: a pallet, crates, straw bales and hooped barrels.
    const float H=FSoraPracticeArenaKit::Height(Wall);
    Kit.Course(Wall,0,20,TEXT("Timber"),FLinearColor(.36f,.26f,.18f));
    float At=20.f; int32 Layer=0;
    while(At<H-.5f)
    {
        const float Top=FMath::Min(H,At+(Layer%3==1?55.f:70.f));
        if(Layer%3==0) Kit.Bays(Wall,At,Top,60.f,5.f,TEXT("Metal"),FLinearColor(.3f,.3f,.32f),TEXT("Timber"),FLinearColor(.72f,.52f,.34f));
        else if(Layer%3==1) Kit.PaintedCourse(Wall,At,Top,FLinearColor(.6f,.5f,.29f),.95f);
        else Kit.Bays(Wall,At,Top,55.f,8.f,TEXT("Metal"),FLinearColor(.26f,.26f,.28f),TEXT("Timber"),FLinearColor(.5f,.34f,.2f));
        At=Top; ++Layer;
    }
}
void Rock(FSoraPracticeArenaKit& Kit,const FSoraPracticeWall& Wall)
{
    const float H=FSoraPracticeArenaKit::Height(Wall);
    Kit.Course(Wall,0,H*.4f,TEXT("Stone"),FLinearColor(.62f,.6f,.56f));
    Kit.Course(Wall,H*.4f,H*.75f,TEXT("Stone"),FLinearColor(.7f,.68f,.63f));
    Kit.Course(Wall,H*.75f,H,TEXT("Stone"),FLinearColor(.58f,.57f,.54f));
}
void Fence(FSoraPracticeArenaKit& Kit,const FSoraPracticeWall& Wall)
{
    const float H=FSoraPracticeArenaKit::Height(Wall);
    Kit.Course(Wall,0,20,TEXT("Stone"),FLinearColor(.66f,.64f,.6f));
    Kit.Bays(Wall,20,H-15,22.f,10.f,TEXT("Timber"),FLinearColor(.3f,.21f,.16f),TEXT("Timber"),FLinearColor(.58f,.42f,.28f));
    Kit.Course(Wall,H-15,H,TEXT("Timber"),FLinearColor(.3f,.21f,.16f));
}
void LanternPost(FSoraPracticeArenaKit& Kit,const FSoraPracticeWall& Wall)
{
    // A street lantern: stone foot, timber post and a lit paper head.
    const float H=FSoraPracticeArenaKit::Height(Wall);
    Kit.Course(Wall,0,40,TEXT("Stone"),FLinearColor(.7f,.68f,.64f));
    Kit.Course(Wall,40,H-90,TEXT("Timber"),FLinearColor(.34f,.24f,.18f));
    Kit.LitCourse(Wall,H-90,H-20,TEXT("Timber"),FLinearColor(.3f,.2f,.15f),FLinearColor(.3f,.12f,.06f),FLinearColor(1.f,.42f,.16f),1.3f,40.f,30.f);
    Kit.Course(Wall,H-20,H,TEXT("Timber"),FLinearColor(.2f,.14f,.1f));
    const FVector Center=(Wall.Minimum+Wall.Maximum)*.5;
    Kit.Lamp(FVector(Center.X,Center.Y,Wall.Minimum.Z+H-55.f),FLinearColor(1.f,.55f,.28f),1100.f,900.f);
}
void Industrial(FSoraPracticeArenaKit& Kit,const FSoraPracticeWall& Wall,FLinearColor Brick,FLinearColor Glow,bool bLit)
{
    // A brick and iron hall: dark footing, brick body, iron bands and cap.
    const float H=FSoraPracticeArenaKit::Height(Wall), Band=.55f*H;
    Kit.Course(Wall,0,90,TEXT("Stone"),FLinearColor(.45f,.44f,.42f));
    Kit.Course(Wall,90,Band,TEXT("Stone"),Brick);
    Kit.Course(Wall,Band,Band+20,TEXT("Metal"),FLinearColor(.38f,.38f,.4f));
    if(bLit)
    {
        Kit.LitCourse(Wall,Band+20,Band+110,TEXT("Metal"),FLinearColor(.3f,.3f,.32f),FLinearColor(.08f,.07f,.06f),Glow,1.1f,220.f,140.f);
        Kit.Course(Wall,Band+110,H-25,TEXT("Stone"),Brick);
    }
    else Kit.Course(Wall,Band+20,H-25,TEXT("Stone"),Brick);
    Kit.Course(Wall,H-25,H,TEXT("Metal"),FLinearColor(.3f,.3f,.32f));
}
void Machine(FSoraPracticeArenaKit& Kit,const FSoraPracticeWall& Wall,FLinearColor Accent)
{
    // Machinery: an iron bed, ribbed timber and iron casing, a brass band.
    const float H=FSoraPracticeArenaKit::Height(Wall);
    Kit.Course(Wall,0,25,TEXT("Metal"),FLinearColor(.26f,.26f,.28f));
    Kit.Bays(Wall,25,H-40,80.f,12.f,TEXT("Metal"),FLinearColor(.5f,.5f,.52f),TEXT("Timber"),FLinearColor(.45f,.3f,.2f));
    Kit.PaintedCourse(Wall,H-40,H-25,Accent,.35f,.85f);
    Kit.Course(Wall,H-25,H,TEXT("Metal"),FLinearColor(.34f,.34f,.36f));
}
void Column(FSoraPracticeArenaKit& Kit,const FSoraPracticeWall& Wall,FLinearColor Band,float Strength)
{
    // A pillar: stone plinth, iron shaft ringed with light, stone capital.
    const float H=FSoraPracticeArenaKit::Height(Wall), Ring=.6f*H;
    Kit.Course(Wall,0,60,TEXT("Stone"),FLinearColor(.5f,.5f,.52f));
    Kit.Course(Wall,60,Ring,TEXT("Metal"),FLinearColor(.3f,.3f,.33f));
    Kit.LitCourse(Wall,Ring,Ring+30,TEXT("Metal"),FLinearColor(.3f,.3f,.33f),FLinearColor(.05f,.05f,.06f),Band,Strength,40.f,34.f);
    Kit.Course(Wall,Ring+30,H-40,TEXT("Metal"),FLinearColor(.3f,.3f,.33f));
    Kit.Course(Wall,H-40,H,TEXT("Stone"),FLinearColor(.5f,.5f,.52f));
}
void Vault(FSoraPracticeArenaKit& Kit,const FSoraPracticeWall& Wall,FLinearColor Seam,bool bWindows)
{
    // Alien vault masonry: dark stone, riveted panels between iron ribs and
    // thin lit seams; tall blocks carry slit windows.
    const float H=FSoraPracticeArenaKit::Height(Wall);
    Kit.Course(Wall,0,80,TEXT("Stone"),FLinearColor(.3f,.31f,.34f));
    float At=80.f; int32 Index=0;
    while(At<H-60.f-1.f)
    {
        const float Top=FMath::Min(H-60.f,At+150.f);
        if(bWindows&&Index==1) Kit.LitCourse(Wall,At,Top,TEXT("Metal"),FLinearColor(.24f,.25f,.29f),FLinearColor(.04f,.02f,.03f),Seam,1.2f,120.f,20.f);
        else Kit.Bays(Wall,At,Top,240.f,14.f,TEXT("Metal"),FLinearColor(.25f,.26f,.3f),TEXT("Stone"),FLinearColor(.36f,.37f,.4f));
        At=Top;
        if(At+8.f<H-60.f) { Kit.LitCourse(Wall,At,At+8.f,TEXT("Metal"),FLinearColor(.2f,.21f,.24f),FLinearColor(.02f,.03f,.04f),Seam,1.f,60.f,56.f); At+=8.f; }
        ++Index;
    }
    Kit.Course(Wall,At,H,TEXT("Metal"),FLinearColor(.2f,.21f,.24f));
}
void Shelves(FSoraPracticeArenaKit& Kit,const FSoraPracticeWall& Wall)
{
    // Ledger shelves: timber frames packed with paper ledgers.
    const float H=FSoraPracticeArenaKit::Height(Wall);
    float At=0.f;
    while(At<H-.5f)
    {
        const float Top=FMath::Min(H,At+40.f);
        Kit.Bays(Wall,At,Top-6.f,60.f,6.f,TEXT("Timber"),FLinearColor(.34f,.24f,.18f),nullptr,FLinearColor(.86f,.8f,.66f));
        Kit.Course(Wall,Top-6.f,Top,TEXT("Timber"),FLinearColor(.3f,.21f,.16f));
        At=Top;
    }
}
void Lanes(FSoraPracticeArenaKit& Kit,const TCHAR* Role,FLinearColor Tint,float Width,float Height,bool bSkipMid)
{
    // The bots' lanes, laid as paths: the routes the arena was drawn around.
    for(const FSoraPracticeLane& Lane:Kit.Map.Lanes)
    {
        if(bSkipMid&&Lane.Name==TEXT("mid")) continue;
        for(int32 Index=1;Index<Lane.Points.Num();++Index)
            // Alternate legs differ by 3 mm so overlapping joints never flicker.
            Kit.Strip(Lane.Points[Index-1],Lane.Points[Index],Width,Height+(Index%2)*.3f,Role,Tint);
    }
}
void Hazards(FSoraPracticeArenaKit& Kit)
{
    // Hazard volumes never block anything; their look stays inside them.
    for(int32 Index=0;Index<Kit.Map.Hazards.Num();++Index)
    {
        const FSoraPracticeHazard& Hazard=Kit.Map.Hazards[Index];
        const FVector Min=Hazard.Minimum, Max=Hazard.Maximum, Center=(Min+Max)*.5;
        const FString Name=FString::Printf(TEXT("PracticeHazard%d"),Index);
        switch(Hazard.Kind)
        {
        case SoraPractice::HazardSlag:
        {
            // A molten channel between dark crust edges.
            const bool bAlongX=Max.X-Min.X>=Max.Y-Min.Y;
            const FVector Edge=bAlongX?FVector(0,(Max.Y-Min.Y)*.2f,0):FVector((Max.X-Min.X)*.2f,0,0);
            Kit.Painted(Min,FVector(bAlongX?Max.X:Min.X+Edge.X,bAlongX?Min.Y+Edge.Y:Max.Y,Min.Z+2.f),FLinearColor(.08f,.06f,.05f),.9f);
            Kit.Painted(FVector(bAlongX?Min.X:Max.X-Edge.X,bAlongX?Max.Y-Edge.Y:Min.Y,Min.Z),FVector(Max.X,Max.Y,Min.Z+2.f),FLinearColor(.08f,.06f,.05f),.9f);
            Kit.Lit(FVector(Min.X+(bAlongX?0:Edge.X),Min.Y+(bAlongX?Edge.Y:0),Min.Z),FVector(Max.X-(bAlongX?0:Edge.X),Max.Y-(bAlongX?Edge.Y:0),Min.Z+1.5f),FLinearColor(1.f,.32f,.05f),2.2f);
            const float Length=bAlongX?Max.X-Min.X:Max.Y-Min.Y;
            for(int32 Light=0;Light<FMath::Max(1,FMath::RoundToInt(Length/600.f));++Light)
            {
                const float T=(Light+.5f)/FMath::Max(1,FMath::RoundToInt(Length/600.f));
                const FVector At=bAlongX?FVector(FMath::Lerp(Min.X,Max.X,T),Center.Y,Min.Z+30.f):FVector(Center.X,FMath::Lerp(Min.Y,Max.Y,T),Min.Z+30.f);
                Kit.Lamp(At,FLinearColor(1.f,.4f,.1f),2400.f,700.f);
            }
            break;
        }
        case SoraPractice::HazardShredder:
        {
            // A shredder grate: iron slats over a red-lit pit.
            Kit.Lit(Min,FVector(Max.X,Max.Y,Min.Z+.8f),FLinearColor(.9f,.05f,.04f),.8f);
            const bool bAlongX=Max.X-Min.X>=Max.Y-Min.Y;
            const float Length=bAlongX?Max.X-Min.X:Max.Y-Min.Y;
            const int32 Slats=FMath::Max(2,FMath::RoundToInt(Length/25.f));
            for(int32 Slat=0;Slat<Slats;++Slat)
            {
                const float From=(bAlongX?Min.X:Min.Y)+Slat*Length/Slats;
                const float To=From+Length/Slats*.55f;
                Kit.Block(bAlongX?FVector(From,Min.Y,Min.Z+.8f):FVector(Min.X,From,Min.Z+.8f),
                    bAlongX?FVector(To,Max.Y,Min.Z+3.f):FVector(Max.X,To,Min.Z+3.f),TEXT("Metal"),FLinearColor(.3f,.3f,.32f));
            }
            Kit.Lamp(FVector(Center.X,Center.Y,Min.Z+40.f),FLinearColor(1.f,.08f,.06f),1800.f,600.f);
            break;
        }
        case SoraPractice::HazardFire:
        default:
        {
            // Burning embers: a glowing bed and low tongues of flame.
            Kit.Lit(Min,FVector(Max.X,Max.Y,Min.Z+1.2f),FLinearColor(1.f,.3f,.05f),.9f);
            const FVector Size=Max-Min;
            for(int32 Flame=0;Flame<9;++Flame)
            {
                const float U=((Flame*37)%100)/100.f, V=((Flame*61+17)%100)/100.f, Tall=FMath::Min(Size.Z-2.f,30.f+(Flame%3)*12.f);
                const FVector At(Min.X+Size.X*(.12f+.76f*U),Min.Y+Size.Y*(.12f+.76f*V),Min.Z);
                auto* Tongue=SoraPracticeArt::Part(&Kit.Builder,Kit.Builder.GetRootComponent(),FString::Printf(TEXT("%sFlame%d"),*Name,Flame),SoraPracticeArt::Cone,
                    At+FVector(0,0,Tall*.5f),FVector(.3f,.3f,Tall/100.f));
                SoraPracticeArt::Glow(Tongue,FLinearColor(1.f,.45f,.08f),1.8f);
                Kit.Adopt(Tongue);
            }
            Kit.Lamp(FVector(Center.X,Center.Y,Min.Z+45.f),FLinearColor(1.f,.5f,.18f),2600.f,800.f);
            break;
        }
        }
    }
}
}
