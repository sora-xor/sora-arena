#include "SoraWorldBuilder.h"
#include "ArenaKernelSubsystem.h"
#include "World/SoraPracticeArena.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInterface.h"

// Nyaagyu Estate, map 0: scanned mesh terrain, authored perimeter wall modules,
// dojo halls and provision storehouses, CC0 trees and pines, roadside
// dressing, cargo stacks and the irrigation sluice. All of it is visual; the
// shared layout's primitive boxes stay the collision. Practice (at the end of
// this file) reuses the terrain, wall module, leaf silt and trees only as
// World/SoraPracticeArena.h allows.
void ASoraWorldBuilder::NyaagyuTerrain()
{
#if PLATFORM_MAC
    // M1 uses authored conventional meshes; Nanite is disabled by MacEngine.ini.
    const TCHAR* Tier=TEXT("MAC");
#else
    const TCHAR* Tier=TEXT("HI");
#endif
    auto* Soil=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Generated/Environment/MI_Nyaagyu_TerrainSoil.MI_Nyaagyu_TerrainSoil"),nullptr,LOAD_NoWarn);
    auto* Stone=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Generated/Environment/M_NyaagyuRoadScanVariation_PBR.M_NyaagyuRoadScanVariation_PBR"),nullptr,LOAD_NoWarn);
    if (!Soil || !Stone)
        UE_LOG(LogTemp,Error,TEXT("SORA estate terrain needs the pinned CC0 soil and varied stone-scan PBR materials"));
    for(int32 Y=0;Y<4;++Y)
    for(int32 X=0;X<4;++X)
    {
        const FString Name=FString::Printf(TEXT("SM_NyaagyuTerrain_%s_X%d_Y%d"),Tier,X,Y);
        const FString Path=FString::Printf(TEXT("/Game/Generated/Environment/Terrain/%s.%s"),*Name,*Name);
        auto* Asset=LoadObject<UStaticMesh>(nullptr,*Path,nullptr,LOAD_NoWarn);
        if(!Asset)
        {
            UE_LOG(LogTemp,Error,TEXT("SORA authored estate terrain tile missing: %s"),*Path);
            continue;
        }
        auto* Mesh=NewObject<UStaticMeshComponent>(this,MakeUniqueObjectName(this,UStaticMeshComponent::StaticClass(),FName(*Name)));
        Mesh->SetStaticMesh(Asset); Mesh->SetupAttachment(RootComponent);
        Mesh->SetRelativeLocation(FVector(-2400+X*1600,-1950+Y*1300,0));
        // This relief is visual only. The offline campaign retains its flat
        // gameplay ground, and the P2P kernel map never loads these tiles.
        Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Mesh->SetCastShadow(true);
        // Static-mesh distance fields feed software Lumen on the M1 path;
        // supported Windows hardware can include the tile in ray tracing.
        Mesh->SetAffectDistanceFieldLighting(true);
        Mesh->SetAffectDynamicIndirectLighting(true);
        Mesh->SetVisibleInRayTracing(true);
        for(int32 Index=0;Index<Asset->GetStaticMaterials().Num();++Index)
        {
            const FString Slot=Asset->GetStaticMaterials()[Index].MaterialSlotName.ToString();
            if(Slot.Contains(TEXT("M_Terrain_Soil")) && Soil) Mesh->SetMaterial(Index,Soil);
            else if(Slot.Contains(TEXT("M_Terrain_Stone")) && Stone) Mesh->SetMaterial(Index,Stone);
        }
        Mesh->RegisterComponent(); AddInstanceComponent(Mesh); Pieces.Add(Mesh);
    }
}
void ASoraWorldBuilder::NyaagyuTree(FVector Location, FRotator Rotation, float Scale)
{
#if PLATFORM_MAC
    const TCHAR* Tier=TEXT("MAC");
#else
    const TCHAR* Tier=TEXT("HI");
#endif
    const FString Name=FString::Printf(TEXT("SM_NyaagyuTree_%s"),Tier);
    const FString Path=FString::Printf(TEXT("/Game/Generated/Environment/Foliage/%s.%s"),*Name,*Name);
    auto* Asset=LoadObject<UStaticMesh>(nullptr,*Path,nullptr,LOAD_NoWarn);
    if(!Asset)
    {
        UE_LOG(LogTemp,Error,TEXT("SORA pinned CC0 Nyaagyu tree is missing: %s"),*Path);
        return;
    }
    auto* Mesh=NewObject<UStaticMeshComponent>(this,MakeUniqueObjectName(this,UStaticMeshComponent::StaticClass(),FName(*Name)));
    Mesh->SetStaticMesh(Asset); Mesh->SetupAttachment(RootComponent);
    Mesh->SetRelativeLocation(Location); Mesh->SetRelativeRotation(Rotation); Mesh->SetRelativeScale3D(FVector(Scale));
    // Tree silhouettes, leaf masks and lighting are presentation only. The
    // campaign retains its existing proxies; practice loads none of these.
    Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Mesh->SetGenerateOverlapEvents(false);
    Mesh->SetCastShadow(true);
    Mesh->SetAffectDistanceFieldLighting(true);
    Mesh->SetAffectDynamicIndirectLighting(true);
    Mesh->SetVisibleInRayTracing(true);
    Mesh->RegisterComponent(); AddInstanceComponent(Mesh); Pieces.Add(Mesh);
}
void ASoraWorldBuilder::NyaagyuPine(FVector Location, FRotator Rotation, float Scale, int32 Variant)
{
#if PLATFORM_MAC
    const TCHAR* Tier=TEXT("MAC");
#else
    const TCHAR* Tier=TEXT("HI");
#endif
    const TCHAR* Form=Variant==0?TEXT("A"):Variant==1?TEXT("B"):TEXT("C");
    const FString Name=FString::Printf(TEXT("SM_NyaagyuPine_%s_%s"),Form,Tier);
    const FString Path=FString::Printf(TEXT("/Game/Generated/Environment/Foliage/%s.%s"),*Name,*Name);
    auto* Asset=LoadObject<UStaticMesh>(nullptr,*Path,nullptr,LOAD_NoWarn);
    if(!Asset)
    {
        UE_LOG(LogTemp,Error,TEXT("SORA pinned CC0 Nyaagyu pine is missing: %s"),*Path);
        return;
    }
    auto* Mesh=NewObject<UStaticMeshComponent>(this,MakeUniqueObjectName(this,UStaticMeshComponent::StaticClass(),FName(*Name)));
    Mesh->SetStaticMesh(Asset); Mesh->SetupAttachment(RootComponent);
    Mesh->SetRelativeLocation(Location); Mesh->SetRelativeRotation(Rotation); Mesh->SetRelativeScale3D(FVector(Scale));
    // Young pines add silhouette and dappled light only; campaign/practice
    // hit volumes and the deterministic kernel stay unchanged.
    Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Mesh->SetGenerateOverlapEvents(false);
    Mesh->SetCastShadow(true);
    Mesh->SetAffectDistanceFieldLighting(true);
    Mesh->SetAffectDynamicIndirectLighting(true);
    Mesh->SetVisibleInRayTracing(true);
    Mesh->RegisterComponent(); AddInstanceComponent(Mesh); Pieces.Add(Mesh);
}
void ASoraWorldBuilder::EstatePerimeter(int32 S,UStaticMeshComponent* WallX,UStaticMeshComponent* WallY)
{
    // One four-metre authored module repeats inside each established
    // wall volume. The primitive boxes remain the only collision.
    bool bCompleteX=true;
    for(int32 I=0;I<13;++I)
        if(!ImportedProp(TEXT("SM_Nyaagyu_EstateWall_4m"),FVector(S*3150,-2400+I*400,220),FRotator::ZeroRotator))
        { bCompleteX=false; break; }
    if(bCompleteX) WallX->SetVisibility(false);
    bool bCompleteY=true;
    for(int32 I=0;I<16;++I)
        if(!ImportedProp(TEXT("SM_Nyaagyu_EstateWall_4m"),FVector(-3000+I*400,S*2550,220),FRotator(0,90.f,0)))
        { bCompleteY=false; break; }
    if(bCompleteY) WallY->SetVisibility(false);
}
void ASoraWorldBuilder::EstateHall(int32 I,int32 S,FVector P,int32 BuildingStart)
{
    // Six dojo halls and four provision storehouses break up the
    // estate's silhouette. Every original Building() component
    // remains as collision; only its blockout render is hidden.
    // These visual meshes never enter the P2P practice map.
    const TCHAR* VisualAsset=(I==1||I==3)
        ?TEXT("SM_Nyaagyu_ProvisionKura"):TEXT("SM_Nyaagyu_EstateDojo");
    // FBX conversion reverses the source's frontage axis. Face
    // both visual entrances toward the central estate road;
    // Building()'s hidden collision pieces stay at their
    // established transforms.
    if(ImportedProp(VisualAsset,P,FRotator(0,S>0?180.f:0.f,0)))
        for(int32 Piece=BuildingStart;Piece<Pieces.Num()-1;++Piece)
            if(Pieces[Piece]) Pieces[Piece]->SetVisibility(false);
    const float TreeScale=.90f+.05f*((I+3*(S+1))%5);
    NyaagyuTree(P+FVector(450,-S*250,0),FRotator(0,37.f*I+(S>0?73.f:0.f),0),TreeScale);
}
void ASoraWorldBuilder::EstateGrounds()
{
    // Three scanned forms break up repetition between the established
    // broadleaf trees. Keep trunks in the gaps along the estate edge.
    for(int32 I=0;I<9;++I)
    {
        const float X=-2500.f+(I%5)*1000.f;
        const float Y=(I<5?-1.f:1.f)*(2280.f-(I%3)*65.f);
        const float TreeScale=1.65f+.14f*(I%4);
        NyaagyuPine(FVector(X,Y,0),FRotator(0,31.f*I+17.f,0),TreeScale,I%3);
    }
    // Thin scanned silt, moss, fallen leaves, and small stones sit along
    // peripheral gaps. The center stone route and combat cover stay clear.
    // Scale/yaw variation avoids a visibly tiled four-metre carpet.
    const FVector DressingLocations[] = {
        FVector(-2600,-500,2), FVector(-2600,500,2),
        FVector(-1850,540,2),
        FVector(2700,-1700,2), FVector(2700,1700,2),
        FVector(-1750,1180,2), FVector(1750,-1180,2),
    };
    const float DressingYaw[] = {14.f,171.f,39.f,-22.f,49.f,-31.f,157.f};
    const float DressingScale[] = {.82f,.78f,.58f,.87f,.96f,.83f,.91f};
    for(int32 I=0;I<7;++I)
        ImportedProp(TEXT("SM_Nyaagyu_RoadsideLeafSilt_4m"),DressingLocations[I],
            FRotator(0,DressingYaw[I],0),DressingScale[I]);
}
void ASoraWorldBuilder::EstateCargo(int32 I,FVector Location,UStaticMeshComponent* Cover)
{
    if(ImportedProp(TEXT("SM_Nyaagyu_CargoStack"),Location,FRotator(0,I%2?180.f:0.f,0)))
        Cover->SetVisibility(false);
}
void ASoraWorldBuilder::EstateSluice(FVector P)
{
    // The authored sluice makes restored agricultural production visible
    // in the Nyaagyu Estate campaign. It is decorative; multiplayer
    // practice continues to use only deterministic kernel collision.
    ImportedProp(TEXT("SM_Nyaagyu_IrrigationSluice"),P+FVector(0,-295,0),FRotator::ZeroRotator);
}

// Practice: the estate as the kernel draws it. The perimeter and the east
// gatehouse take the authored wall module where it fits the kernel's box;
// the halls, storehouses, screens, lanterns, rocks and hedges are dressed in
// courses that fill each box exactly. The scanned terrain and stone paths lie
// flat, and the trees stand outside the walls.
void SoraPracticeDressing::EstateWall(FSoraPracticeArenaKit& Kit,const FSoraPracticeWall& Wall,int32 Index)
{
    using K=FSoraPracticeArenaKit;
    if(K::Labelled(Wall,TEXT("perimeter"))||K::Labelled(Wall,TEXT("gatehouse")))
    {
        if(!Kit.FittedRun(TEXT("SM_Nyaagyu_EstateWall_4m"),Wall,400.f,1.35f)) PlasterWall(Kit,Wall,FLinearColor(.95f,.93f,.88f));
    }
    else if(K::Labelled(Wall,TEXT("dojo hall"))) Townhouse(Kit,Wall,FLinearColor(.95f,.93f,.88f),false,true);
    else if(K::Labelled(Wall,TEXT("screen"))) Screen(Kit,Wall);
    else if(K::Labelled(Wall,TEXT("toro"))) StoneLantern(Kit,Wall);
    else if(K::Labelled(Wall,TEXT("kura"))) Storehouse(Kit,Wall);
    else if(K::Labelled(Wall,TEXT("rock"))) Rock(Kit,Wall);
    else if(K::Labelled(Wall,TEXT("hedge"))||K::Labelled(Wall,TEXT("planter"))) Hedge(Kit,Wall);
    else if(K::Labelled(Wall,TEXT("well house"))) Townhouse(Kit,Wall,FLinearColor(.9f,.86f,.78f),false,false);
    else PlasterWall(Kit,Wall,FLinearColor(.93f,.9f,.84f));
}
void SoraPracticeDressing::EstateGrounds(FSoraPracticeArenaKit& Kit)
{
    // The scanned mesh terrain rises 1-4 cm; its photographed stone route
    // already runs along the mid lane, so only the flanking lanes are laid.
    Kit.EstateTerrain();
    Lanes(Kit,TEXT("TerrainStone"),FLinearColor(.95f,.93f,.9f),170.f,5.f,true);
    // Leaf silt along the inner edges of the long walls, flat on the ground.
    const float Edge=Kit.Map.Maximum.Y-110.f;
    const float Along[]={-1500.f,-450.f,650.f,1650.f};
    for(int32 Index=0;Index<UE_ARRAY_COUNT(Along);++Index)
        for(int32 Side:{-1,1})
            Kit.Prop(TEXT("SM_Nyaagyu_RoadsideLeafSilt_4m"),FVector(Along[Index]*Side,Side*Edge,1.f),FRotator(0,Side>0?180.f:0.f,0),.8f);
    // Broadleaf trees behind the perimeter, far enough out that no branch
    // reaches over the arena.
    const FVector Min=Kit.Map.Minimum, Max=Kit.Map.Maximum;
    int32 Tree=0;
    for(float X=Min.X+200.f;X<=Max.X-200.f;X+=750.f)
        for(int32 Side:{-1,1})
        {
            ++Tree;
            Kit.Tree(FVector(X,Side>0?Max.Y+780.f:Min.Y-780.f,0),FRotator(0,37.f*Tree,0),1.9f+.1f*(Tree%3));
        }
    for(float Y=Min.Y+400.f;Y<=Max.Y-400.f;Y+=800.f)
        for(int32 Side:{-1,1})
        {
            ++Tree;
            Kit.Tree(FVector(Side>0?Max.X+780.f:Min.X-780.f,Y,0),FRotator(0,53.f*Tree,0),1.9f+.1f*(Tree%3));
        }
}
