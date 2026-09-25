#include "SoraWorldBuilder.h"
#include "SoraCatalog.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/PointLight.h"
#include "Engine/World.h"

// A campaign zone or route corridor from its space data: a floor slab at z 0,
// four walls and the cover boxes (the only collision), a packed-earth road
// along a corridor, and the style's dressing. Estate yards wear the authored
// four-metre wall module over their walls and cargo stacks over their cover;
// lantern posts keep a pole proxy like the arena's. Pines, broadleaf trees,
// storehouses, halls and street buildings stand outside the walls, so a
// visual-only prop never covers a work spot.
namespace
{
const FLinearColor ZoneWeathered(.55f,.52f,.47f);
bool ZoneIsAlien(FName Style) { return Style==TEXT("citadel")||Style==TEXT("foundry"); }
}

void ASoraWorldBuilder::BuildZone(const FSoraZone& Zone,int32 Index)
{
    const FString Name=FString::Printf(TEXT("Zone%d"),Index);
    const bool bRoute=Zone.IsRoute(),bHall=Zone.Form==TEXT("hall"),bField=Zone.Form==TEXT("field");
    const bool bEstate=Zone.Style==TEXT("estate"),bAlien=ZoneIsAlien(Zone.Style);
    // Packed earth for fields and roads, stone flags for yards, boards in an
    // estate hall and iron plate in an alien one.
    const TCHAR* FloorRole=bHall&&bAlien?TEXT("Metal"):bField||bRoute?TEXT("Soil"):bHall?TEXT("Timber"):TEXT("Stone");
    const FVector2D Center=Zone.Rect.GetCenter(),Size=Zone.Rect.GetSize();
    Box(Name+TEXT("Floor"),FVector(Center.X,Center.Y,-50.f),FVector(Size.X+160.f,Size.Y+160.f,100.f),
        FLinearColor(.18f,.19f,.16f),true,FRotator::ZeroRotator,FloorRole);
    const TCHAR* WallRole=bAlien?TEXT("Metal"):bHall||bRoute?TEXT("Timber"):TEXT("Stone");
    for(int32 WallIndex=0;WallIndex<Zone.Walls.Num();++WallIndex)
    {
        const FSoraBox& Wall=Zone.Walls[WallIndex];
        auto* Mesh=Box(FString::Printf(TEXT("%sWall%d"),*Name,WallIndex),FVector(Wall.Center.X,Wall.Center.Y,Wall.Height*.5f),
            FVector(Wall.Size.X,Wall.Size.Y,Wall.Height),FLinearColor(.2f,.23f,.23f),true,FRotator::ZeroRotator,WallRole);
        if(!bEstate||bHall||bField||bRoute) continue;
        // The estate's four-metre wall module repeats inside the wall volume;
        // the box stays the collision and hides once every module is in place.
        const bool bAlongX=Wall.Size.X>Wall.Size.Y;
        const float Length=bAlongX?Wall.Size.X:Wall.Size.Y;
        const int32 Modules=FMath::Max(1,FMath::FloorToInt32(Length/400.f));
        bool bComplete=true;
        for(int32 Module=0;Module<Modules&&bComplete;++Module)
        {
            const float Offset=-Length*.5f+200.f+Module*(Length-400.f)/FMath::Max(1,Modules-1);
            const FVector At=bAlongX?FVector(Wall.Center.X+Offset,Wall.Center.Y,220.f):FVector(Wall.Center.X,Wall.Center.Y+Offset,220.f);
            bComplete=ImportedProp(TEXT("SM_Nyaagyu_EstateWall_4m"),At,FRotator(0,bAlongX?90.f:0.f,0));
        }
        if(bComplete) Mesh->SetVisibility(false);
    }
    if(bRoute)
    {
        // The road: a slightly raised strip of packed earth along each stretch.
        for(int32 Node=1;Node<Zone.Route.Num();++Node)
        {
            const FVector2D A=Zone.Route[Node-1],B=Zone.Route[Node];
            const FVector2D Mid=(A+B)*.5f;
            const float Yaw=FMath::RadiansToDegrees(FMath::Atan2(B.Y-A.Y,B.X-A.X));
            auto* Road=Box(FString::Printf(TEXT("%sRoad%d"),*Name,Node),FVector(Mid.X,Mid.Y,1.f),
                FVector(FVector2D::Distance(A,B)+220.f,420.f,4.f),FLinearColor(.3f,.26f,.2f),false,FRotator(0,Yaw,0));
            Surface(Road,bAlien?TEXT("Metal"):TEXT("Stone"),bAlien?FLinearColor(.5f,.55f,.6f):FLinearColor(.62f,.52f,.4f));
        }
    }
    for(int32 CoverIndex=0;CoverIndex<Zone.Cover.Num();++CoverIndex)
    {
        const FSoraBox& Piece=Zone.Cover[CoverIndex];
        const FVector Base(Piece.Center.X,Piece.Center.Y,0.f);
        auto* Cover=Box(FString::Printf(TEXT("%sCover%d"),*Name,CoverIndex),Base+FVector(0,0,Piece.Height*.5f),
            FVector(Piece.Size.X,Piece.Size.Y,Piece.Height),CoverIndex%2?FLinearColor(.29f,.19f,.09f):FLinearColor(.23f,.27f,.28f),
            true,FRotator::ZeroRotator,bAlien?TEXT("Metal"):CoverIndex%2?TEXT("Timber"):TEXT("Stone"));
        // Estate cover wears the authored cargo stack, as the arena's does.
        if(bEstate&&ImportedProp(TEXT("SM_Nyaagyu_CargoStack"),Base,FRotator(0,CoverIndex%2?180.f:0.f,0)))
            Cover->SetVisibility(false);
    }
    for(int32 PropIndex=0;PropIndex<Zone.Props.Num();++PropIndex) ZoneProp(Zone,Zone.Props[PropIndex],PropIndex);
}
void ASoraWorldBuilder::ZoneProp(const FSoraZone& Zone,const FSoraProp& Prop,int32 Index)
{
    const FVector At(Prop.At.X,Prop.At.Y,0.f);
    const FRotator Facing(0,Prop.Yaw,0);
    if(Prop.Mesh==TEXT("SM_Edo_LanternPost"))
    {
        // Zone corners are lit; along a road every third post is, to keep
        // local lights affordable on the Mac preset.
        ZoneLantern(At,!Zone.IsRoute()||Index%3==0);
        return;
    }
    if(Prop.Mesh==TEXT("pine")) { NyaagyuPine(At,Facing,1.5f+.1f*(Index%4),Index%3); return; }
    if(Prop.Mesh==TEXT("tree")) { NyaagyuTree(At,Facing,.9f+.05f*(Index%5)); return; }
    if(Prop.Mesh==TEXT("building")||Prop.Mesh==TEXT("building_hightech"))
    {
        const bool bHighTech=Prop.Mesh==TEXT("building_hightech");
        Building(At,FVector(650,700,bHighTech?620.f+(Index%3)*160.f:330.f+(Index%2)*100.f),
            bHighTech?FLinearColor(.12f,.15f,.19f):FLinearColor(.63f,.56f,.40f),bHighTech);
        return;
    }
    ImportedProp(Prop.Mesh.ToString(),At,Facing);
}
void ASoraWorldBuilder::ZoneLantern(FVector Location,bool bLit)
{
    const bool bAuthored=ImportedProp(TEXT("SM_Edo_LanternPost"),Location,FRotator::ZeroRotator);
    auto* Pole=Shape(this,RootComponent,FString::Printf(TEXT("ZoneLanternCollision%d"),Pieces.Num()),TEXT("/Engine/BasicShapes/Cube.Cube"),
        Location+FVector(0,0,175),FVector(.14,.14,3.5),ZoneWeathered,true);
    Pole->SetVisibility(!bAuthored); Pieces.Add(Pole);
    if(!bLit||!GetWorld()) return;
    if(auto* Light=GetWorld()->SpawnActor<APointLight>(Location+FVector(0,0,bAuthored?252.f:350.f),FRotator::ZeroRotator))
    {
        auto* Flame=Light->PointLightComponent.Get();
        Flame->SetIntensityUnits(ELightUnits::Lumens);
        Flame->SetIntensity(420.f);
        Flame->SetAttenuationRadius(500.f);
        Flame->SetSourceRadius(9.f);
        Flame->SetUseTemperature(true);
        Flame->SetTemperature(2450.f);
        Flame->SetCastShadows(false);
        DecorActors.Add(Light);
    }
}
