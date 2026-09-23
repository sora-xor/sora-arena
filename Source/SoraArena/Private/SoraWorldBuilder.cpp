#include "SoraWorldBuilder.h"
#include "SoraCatalog.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SceneComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Engine/DirectionalLight.h"
#include "Engine/SkyLight.h"
#include "Engine/ExponentialHeightFog.h"
#include "Engine/PostProcessVolume.h"
#include "Components/SkyAtmosphereComponent.h"
#include "Engine/PointLight.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Engine/TextureCube.h"
#include "ArenaKernelSubsystem.h"

ASoraWorldBuilder::ASoraWorldBuilder()
{
    RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("ArenaRoot"));
}
UStaticMeshComponent* ASoraWorldBuilder::Shape(AActor* Owner, USceneComponent* Parent, const FString& Name, const TCHAR* Asset, FVector Location, FVector Scale, FLinearColor Color, bool Collision)
{
    UStaticMeshComponent* M = NewObject<UStaticMeshComponent>(Owner, MakeUniqueObjectName(Owner,UStaticMeshComponent::StaticClass(),FName(*Name)));
    M->SetStaticMesh(LoadObject<UStaticMesh>(nullptr, Asset));
    M->SetupAttachment(Parent);
    M->SetRelativeLocation(Location); M->SetRelativeScale3D(Scale);
    M->SetCollisionEnabled(Collision ? ECollisionEnabled::QueryAndPhysics : ECollisionEnabled::NoCollision);
    M->SetCollisionResponseToAllChannels(ECR_Block);
    M->SetGenerateOverlapEvents(false);
    M->RegisterComponent(); Owner->AddInstanceComponent(M);
    Tint(M, Color);
    return M;
}
void ASoraWorldBuilder::Tint(UStaticMeshComponent* Mesh, FLinearColor Color)
{
    UMaterialInterface* Base = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/Generated/Materials/M_ArenaSurface.M_ArenaSurface"));
    if (!Base) Base = LoadObject<UMaterialInterface>(nullptr, TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"));
    if (Base)
    {
        auto* Material = UMaterialInstanceDynamic::Create(Base, Mesh);
        Material->SetVectorParameterValue(TEXT("BaseColor"), Color);
        Material->SetVectorParameterValue(TEXT("Color"), Color);
        Material->SetScalarParameterValue(TEXT("Roughness"), .72f);
        Mesh->SetMaterial(0, Material);
    }
}
void ASoraWorldBuilder::Surface(UStaticMeshComponent* Mesh,const FString& Role,FLinearColor Color)
{
    const FString Path=TEXT("/Game/Generated/Environment/MI_Nyaagyu_")+Role+TEXT(".MI_Nyaagyu_")+Role;
    if(auto* Material=LoadObject<UMaterialInterface>(nullptr,*Path,nullptr,LOAD_NoWarn))
    {
        auto* Instance=UMaterialInstanceDynamic::Create(Material,Mesh);
        Instance->SetVectorParameterValue(TEXT("Tint"),Color); Mesh->SetMaterial(0,Instance);
    }
}
UStaticMeshComponent* ASoraWorldBuilder::Box(const FString& Name, FVector Location, FVector Size, FLinearColor Color, bool Collision, FRotator Rotation,const FString& SurfaceRole)
{
    auto* M = Shape(this,RootComponent,Name,TEXT("/Engine/BasicShapes/Cube.Cube"),Location,Size/100.f,Color,Collision);
    M->SetRelativeRotation(Rotation); Pieces.Add(M);
    if(!SurfaceRole.IsEmpty()) Surface(M,SurfaceRole);
    return M;
}
void ASoraWorldBuilder::Building(FVector L, FVector Size, FLinearColor Wall, bool HighTech)
{
    const FString N = FString::Printf(TEXT("Building%d"), Pieces.Num());
    Box(N,L+FVector(0,0,Size.Z*.5f),Size,Wall,true,FRotator::ZeroRotator,HighTech?TEXT("Metal"):TEXT("Timber"));
    Box(N+TEXT("Foundation"),L+FVector(0,0,24),FVector(Size.X+35,Size.Y+35,48),FLinearColor(.22f,.25f,.25f),true,FRotator::ZeroRotator,TEXT("Stone"));
    for (int32 Side : {-1,1})
    {
        Box(N+FString::FromInt(Side)+TEXT("Roof"),L+FVector(0,Side*Size.Y*.26f,Size.Z+35),FVector(Size.X+90,Size.Y*.62f,35),FLinearColor(.08f,.12f,.16f),true,FRotator(0,0,Side*22.f),TEXT("Timber"));
        Box(N+FString::FromInt(Side)+TEXT("Trim"),L+FVector(Size.X*.505f,Side*Size.Y*.35f,Size.Z*.5f),FVector(15,18,Size.Z),FLinearColor(.15f,.08f,.055f),true,FRotator::ZeroRotator,TEXT("Timber"));
    }
    for (int32 I=-1;I<=1;++I)
        Box(N+FString::FromInt(I)+TEXT("Window"),L+FVector(Size.X*.505f,I*Size.Y*.24f,Size.Z*.55f),FVector(8,Size.Y*.17f,Size.Z*.42f),HighTech?FLinearColor(.04f,.62f,.66f):FLinearColor(.88f,.66f,.34f),false);
    if (HighTech) Box(N+TEXT("Antenna"),L+FVector(0,0,Size.Z+220),FVector(25,25,340),FLinearColor(.12f,.65f,.68f));
}
bool ASoraWorldBuilder::ImportedProp(const FString& Name, FVector Location, FRotator Rotation, float Scale)
{
    const FString Path=FString::Printf(TEXT("/Game/Generated/Environment/Props/%s.%s"),*Name,*Name);
    auto* Asset=LoadObject<UStaticMesh>(nullptr,*Path,nullptr,LOAD_NoWarn);
    if (!Asset)
    {
        UE_LOG(LogTemp,Error,TEXT("SORA authored environment prop %s is missing; run import_original_assets.py in UE 5.8.2. Primitive fallback is provisional."),*Path);
        return false;
    }
    auto* Mesh=NewObject<UStaticMeshComponent>(this,MakeUniqueObjectName(this,UStaticMeshComponent::StaticClass(),FName(*Name)));
    Mesh->SetStaticMesh(Asset); Mesh->SetupAttachment(RootComponent);
    Mesh->SetRelativeLocation(Location); Mesh->SetRelativeRotation(Rotation);
    Mesh->SetRelativeScale3D(FVector(Scale));
    // In campaign the authored UCX is useful for placement review. The world
    // builder keeps its established simple collision proxies for combat.
    Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Mesh->SetGenerateOverlapEvents(false);
    Mesh->SetCastShadow(true);
    Mesh->SetAffectDistanceFieldLighting(true);
    Mesh->SetAffectDynamicIndirectLighting(true);
    Mesh->SetVisibleInRayTracing(true);
    const bool bEstateDojo=Name==TEXT("SM_Nyaagyu_EstateDojo");
    const bool bProvisionKura=Name==TEXT("SM_Nyaagyu_ProvisionKura");
    for(int32 Index=0;Index<Asset->GetStaticMaterials().Num();++Index)
    {
        const FString Slot=Asset->GetStaticMaterials()[Index].MaterialSlotName.ToString();
        FString Role;
        FLinearColor TintColor=FLinearColor::White;
        float TileSizeCm=0.f;
        if(Slot.Contains(TEXT("M_Env_Timber"))) Role=TEXT("Timber");
        else if(Slot.Contains(TEXT("M_Env_Stone"))) Role=TEXT("Stone");
        else if(Slot.Contains(TEXT("M_Env_Metal"))) Role=TEXT("Metal");
        else if(bEstateDojo&&Slot.StartsWith(TEXT("M_Dojo_Kawara_")))
        {
            // The original curved tiles supply the roof silhouette. The
            // pinned grey ceramic scan supplies color and PBR surface detail
            // at its measured three-metre scale, with restrained tile variation.
            Role=TEXT("Kawara"); TileSizeCm=300.f;
            TintColor=Slot.EndsWith(TEXT("_1"))?FLinearColor(.86f,.88f,.90f)
                :Slot.EndsWith(TEXT("_2"))?FLinearColor(.77f,.80f,.83f)
                :FLinearColor(.94f,.95f,.96f);
        }
        else if(bEstateDojo&&Slot==TEXT("M_Dojo_CharredCedar"))
        {
            Role=TEXT("Timber"); TileSizeCm=140.f;
            TintColor=FLinearColor(.24f,.23f,.24f);
        }
        else if(bProvisionKura&&Slot==TEXT("M_Kura_Kawara"))
        {
            Role=TEXT("Kawara"); TileSizeCm=300.f;
            TintColor=FLinearColor(.93f,.94f,.96f);
        }
        else if(bProvisionKura&&Slot==TEXT("M_Kura_LimePlaster"))
        {
            Role=TEXT("Plaster"); TileSizeCm=100.f;
            TintColor=FLinearColor(1.0f,.98f,.93f);
        }
        else if(bProvisionKura&&Slot==TEXT("M_Kura_CharredCedar"))
        {
            Role=TEXT("Timber"); TileSizeCm=140.f;
            TintColor=FLinearColor(.23f,.22f,.22f);
        }
        if(!Role.IsEmpty())
        {
            const FString MaterialPath=TEXT("/Game/Generated/Environment/MI_Nyaagyu_")+Role+TEXT(".MI_Nyaagyu_")+Role;
            if(auto* Material=LoadObject<UMaterialInterface>(nullptr,*MaterialPath,nullptr,LOAD_NoWarn))
            {
                if(TileSizeCm>0.f)
                {
                    auto* Instance=UMaterialInstanceDynamic::Create(Material,Mesh);
                    Instance->SetVectorParameterValue(TEXT("Tint"),TintColor);
                    Instance->SetVectorParameterValue(TEXT("TileSize"),FLinearColor(TileSizeCm,TileSizeCm,TileSizeCm,1.f));
                    Mesh->SetMaterial(Index,Instance);
                }
                else Mesh->SetMaterial(Index,Material);
            }
        }
    }
    Mesh->RegisterComponent(); AddInstanceComponent(Mesh); Pieces.Add(Mesh);
    return true;
}
void ASoraWorldBuilder::NyaagyuTerrain()
{
#if PLATFORM_MAC
    // M1 uses authored conventional meshes; Nanite is disabled by MacEngine.ini.
    const TCHAR* Tier=TEXT("MAC");
#else
    const TCHAR* Tier=TEXT("HI");
#endif
    auto* Soil=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Generated/Environment/MI_Nyaagyu_TerrainSoil.MI_Nyaagyu_TerrainSoil"),nullptr,LOAD_NoWarn);
    auto* Stone=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Generated/Environment/MI_Nyaagyu_TerrainStone.MI_Nyaagyu_TerrainStone"),nullptr,LOAD_NoWarn);
    if (!Soil || !Stone)
        UE_LOG(LogTemp,Error,TEXT("SORA estate terrain needs the pinned CC0 soil and stone PBR materials"));
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
void ASoraWorldBuilder::Torii(FVector L,float Yaw)
{
    const FRotator R(0,Yaw,0); const FVector Side=R.RotateVector(FVector(0,1,0));
    if(ImportedProp(TEXT("SM_Nyaagyu_ToriiGate"),L,FRotator(0,Yaw+90.f,0)))
    {
        for(int32 S:{-1,1})
        {
            auto* Proxy=Shape(this,RootComponent,FString::Printf(TEXT("ToriiCollision%d"),Pieces.Num()),TEXT("/Engine/BasicShapes/Cube.Cube"),
                L+Side*S*235+FVector(0,0,250),FVector(.42,.42,5),FLinearColor::White,true);
            Proxy->SetRelativeRotation(R); Proxy->SetVisibility(false); Pieces.Add(Proxy);
        }
        auto* Lintel=Shape(this,RootComponent,FString::Printf(TEXT("ToriiCollisionLintel%d"),Pieces.Num()),TEXT("/Engine/BasicShapes/Cube.Cube"),
            L+FVector(0,0,511),FVector(.6,5.75,.49),FLinearColor::White,true);
        Lintel->SetRelativeRotation(R); Lintel->SetVisibility(false); Pieces.Add(Lintel);
        return;
    }
    for(int32 S:{-1,1}) Box(FString::Printf(TEXT("Torii%d"),Pieces.Num()),L+Side*S*240+FVector(0,0,250),FVector(44,44,500),FLinearColor(.55f,.035f,.025f),true,R);
    Box(FString::Printf(TEXT("Lintel%d"),Pieces.Num()),L+FVector(0,0,510),FVector(80,660,65),FLinearColor(.4f,.025f,.02f),true,R);
    Box(FString::Printf(TEXT("Crossbeam%d"),Pieces.Num()),L+FVector(0,0,415),FVector(42,610,35),FLinearColor(.55f,.035f,.025f),true,R);
}
void ASoraWorldBuilder::ClearArena()
{
    for(const auto& M:Pieces) if(M) M->DestroyComponent(); Pieces.Reset();
    for(const auto& A:DecorActors) if(A) A->Destroy(); DecorActors.Reset(); Nodes.Reset(); SiteEffects.Reset(); SiteRestoredColors.Reset(); Activated.Reset(); NodePositions.Reset();
}
void ASoraWorldBuilder::BuildPractice(int32 MapId,const FSoraPracticeMap& Map)
{
    ClearArena();
    const FVector Size=Map.Maximum-Map.Minimum;
    const FVector Center=(Map.Minimum+Map.Maximum)*.5;
    Box(TEXT("KernelGround"),FVector(Center.X,Center.Y,Map.Minimum.Z-25),FVector(Size.X+160,Size.Y+160,50),FLinearColor(.2,.22,.18),true,FRotator::ZeroRotator,TEXT("Soil"));
    // Visual/collision bounds and every obstacle come from the loaded reference kernel.
    // No campaign cover, trees or scenery may introduce additional collision here.
    for(int32 I=0;I<Map.Walls.Num();++I)
    {
        const auto& Wall=Map.Walls[I];
        Box(FString::Printf(TEXT("KernelWall%d"),I),(Wall.Minimum+Wall.Maximum)*.5,Wall.Maximum-Wall.Minimum,FLinearColor(.3,.31,.29),true,FRotator::ZeroRotator,MapId<2?TEXT("Timber"):TEXT("Metal"));
    }
    for(int32 Side:{-1,1})
    {
        const float X=Side<0?Map.Minimum.X:Map.Maximum.X;
        const float Y=Side<0?Map.Minimum.Y:Map.Maximum.Y;
        // The kernel clamps movement at the perimeter but does not define tall
        // bullet-blocking perimeter walls. Mark that limit on the floor only.
        Box(FString::Printf(TEXT("KernelBoundaryX%d"),Side),FVector(X,Center.Y,1),FVector(12,Size.Y,2),FLinearColor(.08,.6,.65),false);
        Box(FString::Printf(TEXT("KernelBoundaryY%d"),Side),FVector(Center.X,Y,1),FVector(Size.X,12,2),FLinearColor(.08,.6,.65),false);
    }
    Lighting(MapId);
}
void ASoraWorldBuilder::Build(int32 MapId,const FSoraChapter* Chapter)
{
    ClearArena();
    const FLinearColor Accent=FSoraCatalog::Get().Map(MapId).Accent;
    Box(TEXT("Ground"),FVector(0,0,-50),FVector(6400,5200,100),FLinearColor(.14f,.16f,.13f),true,FRotator::ZeroRotator,TEXT("Soil"));
    if(MapId==0) NyaagyuTerrain();
    // The imported estate tiles already carry the photographed stone route.
    // The old raised blockout covered that path and hid its relief entirely.
    if(MapId!=0)
        Box(TEXT("CentralRoad"),FVector(0,0,2),FVector(5600,660,5),FLinearColor(.29f,.30f,.28f),false,FRotator::ZeroRotator,TEXT("Stone"));
    for(int32 S:{-1,1})
    {
        auto* WallX=Box(FString::Printf(TEXT("WallX%d"),S),FVector(S*3150,0,220),FVector(100,5200,540),FLinearColor(.2f,.23f,.23f),true,FRotator::ZeroRotator,TEXT("Stone"));
        auto* WallY=Box(FString::Printf(TEXT("WallY%d"),S),FVector(0,S*2550,220),FVector(6400,100,540),FLinearColor(.2f,.23f,.23f),true,FRotator::ZeroRotator,TEXT("Stone"));
        if(MapId==0)
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
        for(int32 I=0;I<5;++I)
        {
            FVector P(-2000+I*1000,S*(MapId==1?1200:1800),0);
            const float Height=MapId==3?780.f:330.f+(I%2)*100.f;
            const int32 BuildingStart=Pieces.Num();
            Building(P,FVector(650,700,Height),MapId==3?FLinearColor(.12f,.15f,.19f):FLinearColor(.63f,.56f,.40f),MapId>=2);
            if(MapId==0)
            {
                // Six dojo halls and four provision storehouses break up the
                // estate's silhouette. Every original Building() component
                // remains as collision; only its blockout render is hidden.
                // These visual meshes never enter the P2P practice map.
                const TCHAR* VisualAsset=(I==1||I==3)
                    ?TEXT("SM_Nyaagyu_ProvisionKura"):TEXT("SM_Nyaagyu_EstateDojo");
                if(ImportedProp(VisualAsset,P,FRotator(0,S>0?0.f:180.f,0)))
                    for(int32 Piece=BuildingStart;Piece<Pieces.Num()-1;++Piece)
                        if(Pieces[Piece]) Pieces[Piece]->SetVisibility(false);
                const float TreeScale=.90f+.05f*((I+3*(S+1))%5);
                NyaagyuTree(P+FVector(450,-S*250,0),FRotator(0,37.f*I+(S>0?73.f:0.f),0),TreeScale);
            }
        }
    }
    if(MapId==0)
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
    for(int32 I=0;I<12;++I)
    {
        const float X=-2300+(I%6)*900; const float Y=(I<6?-1:1)*(680+(I%2)*200);
        auto* Cover=Box(FString::Printf(TEXT("Cover%d"),I),FVector(X,Y,70),FVector(230,180,140),I%2?FLinearColor(.29f,.19f,.09f):FLinearColor(.23f,.27f,.28f),true,FRotator::ZeroRotator,I%2?TEXT("Timber"):TEXT("Stone"));
        // Keep the established cover volume for campaign combat. The cargo
        // stack is a visual mesh only and never enters a P2P practice map.
        if(MapId==0 && ImportedProp(TEXT("SM_Nyaagyu_CargoStack"),FVector(X,Y,0),FRotator(0,I%2?180.f:0.f,0)))
            Cover->SetVisibility(false);
    }
    Torii(FVector(-2250,0,0),0); Torii(FVector(2300,0,0),0);
    NodePositions={FVector(-1250,-700,0),FVector(0,1000,0),FVector(1250,-800,0)};
    for(int32 I=0;I<NodePositions.Num();++I)
    {
        const FVector P=NodePositions[I];
        const FString Kind=Chapter&&Chapter->Sites.IsValidIndex(I)?Chapter->Sites[I].Kind:TEXT("workshop");
        Box(FString::Printf(TEXT("ProductionBase%d"),I),P+FVector(0,0,45),FVector(200,200,90),FLinearColor(.14f,.19f,.23f),true,FRotator::ZeroRotator,TEXT("Metal"));
        auto* N=Shape(this,RootComponent,FString::Printf(TEXT("ProductionCore%d"),I),TEXT("/Engine/BasicShapes/Cylinder.Cylinder"),P+FVector(0,0,145),FVector(.7f,.7f,1.5f),FLinearColor(.8f,.07f,.12f),true); Pieces.Add(N); Nodes.Add(N);
        SiteEffects.Add(nullptr);
        SiteRestoredColors.Add(Kind==TEXT("foundry")?FLinearColor(.96f,.37f,.08f)
            :Kind==TEXT("irrigation")?FLinearColor(.08f,.45f,.83f)
            :Kind==TEXT("supplies")||Kind==TEXT("training")||Kind==TEXT("workshop")?FLinearColor(.82f,.59f,.19f)
            :FLinearColor(.07f,.62f,.53f));
        if(Kind==TEXT("irrigation"))
        {
            SiteEffects[I]=Box(FString::Printf(TEXT("WaterChannel%d"),I),P+FVector(0,-205,18),FVector(420,130,35),FLinearColor(.04f,.07f,.09f),false);
            auto* Wheel=Shape(this,RootComponent,FString::Printf(TEXT("Waterwheel%d"),I),TEXT("/Engine/BasicShapes/Cylinder.Cylinder"),P+FVector(0,0,290),FVector(2.1f,.32f,2.1f),FLinearColor(.27f,.18f,.08f),false);
            Wheel->SetRelativeRotation(FRotator(90,0,0)); Pieces.Add(Wheel);
            // The authored sluice makes restored agricultural production visible
            // in the Nyaagyu Estate campaign. It is decorative; multiplayer
            // practice continues to use only deterministic kernel collision.
            if(MapId==0) ImportedProp(TEXT("SM_Nyaagyu_IrrigationSluice"),P+FVector(0,-295,0),FRotator::ZeroRotator);
        }
        else if(Kind==TEXT("foundry"))
        {
            Box(FString::Printf(TEXT("Furnace%d"),I),P+FVector(0,0,255),FVector(280,250,290),FLinearColor(.19f,.21f,.24f),true,FRotator::ZeroRotator,TEXT("Stone"));
            SiteEffects[I]=Box(FString::Printf(TEXT("ForgeMouth%d"),I),P+FVector(0,-130,220),FVector(125,20,100),FLinearColor(.12f,.05f,.03f),false);
            Box(FString::Printf(TEXT("ForgeStack%d"),I),P+FVector(80,70,475),FVector(80,80,220),FLinearColor(.14f,.16f,.18f),true,FRotator::ZeroRotator,TEXT("Metal"));
            // The original silk loom is decorative beside the Silk Foundry
            // production station. Its meter and operator face the approach;
            // the established simple boxes retain gameplay collision.
            if(MapId==2) ImportedProp(TEXT("SM_SilkFoundry_LevyLoom"),P+FVector(-100,-450,0),FRotator::ZeroRotator);
        }
        else if(Kind==TEXT("ledger")||Kind==TEXT("debt_seal"))
        {
            Box(FString::Printf(TEXT("LedgerFrame%d"),I),P+FVector(0,0,305),FVector(275,58,245),FLinearColor(.08f,.10f,.15f),true,FRotator::ZeroRotator,TEXT("Metal"));
            SiteEffects[I]=Box(FString::Printf(TEXT("LedgerScreen%d"),I),P+FVector(0,-31,305),FVector(250,8,220),FLinearColor(.75f,.06f,.12f),false);
        }
        else if(Kind==TEXT("supplies"))
        {
            for(int32 Stack=0;Stack<3;++Stack)
            {
                auto* Crate=Box(FString::Printf(TEXT("SupplyCrate%d_%d"),I,Stack),P+FVector(-120+Stack*115,85,145+Stack*24),FVector(95,95,100),FLinearColor(.42f,.28f,.13f),true,FRotator::ZeroRotator,TEXT("Timber"));
                if(Stack==0) SiteEffects[I]=Crate;
            }
        }
        else if(Kind==TEXT("training"))
        {
            for(int32 Rack:{-1,1}) Box(FString::Printf(TEXT("SwordRack%d_%d"),I,Rack),P+FVector(Rack*125,50,255),FVector(22,160,200),FLinearColor(.33f,.16f,.07f),true,FRotator::ZeroRotator,TEXT("Timber"));
            SiteEffects[I]=Box(FString::Printf(TEXT("PracticeBeam%d"),I),P+FVector(0,50,360),FVector(300,36,26),FLinearColor(.45f,.22f,.09f),true,FRotator::ZeroRotator,TEXT("Timber"));
        }
        else if(Kind==TEXT("power"))
        {
            Box(FString::Printf(TEXT("PowerPylon%d"),I),P+FVector(0,0,380),FVector(75,75,460),FLinearColor(.12f,.18f,.23f),true,FRotator::ZeroRotator,TEXT("Metal"));
            SiteEffects[I]=Box(FString::Printf(TEXT("PowerBeacon%d"),I),P+FVector(0,0,625),FVector(120,120,50),FLinearColor(.72f,.06f,.10f),false);
        }
        else
        {
            for(int32 S:{-1,1})
            {
                auto* Panel=Box(FString::Printf(TEXT("WorkshopPanel%d%d"),I,S),P+FVector(S*110,0,185),FVector(150,150,12),Accent,true,FRotator(0,0,S*20));
                if(S==-1) SiteEffects[I]=Panel;
            }
        }
    }
    if(MapId==3) ImportedProp(TEXT("SM_Alien_DebtKiosk"),NodePositions[1]+FVector(315,0,0),FRotator(0,90,0));
    if(MapId==1)
    {
        // The occupied street faces the road at local -Y. Use the same simple
        // campaign collision whether the authored mesh imported or not.
        const FVector StreetTerminal(-730,460,0);
        const bool HasStreetTerminal=ImportedProp(TEXT("SM_Alien_StreetDebtTerminal"),StreetTerminal,FRotator::ZeroRotator);
        auto* Proxy=Box(TEXT("StreetDebtTerminalCollision"),StreetTerminal+FVector(0,0,121),
            FVector(140,74,242),FLinearColor(.10f,.15f,.20f),true);
        if(HasStreetTerminal) Proxy->SetVisibility(false);
    }
    for(int32 I=0;I<10;++I)
    {
        FVector P(-2250+(I%5)*1125,(I<5?-1:1)*470,0);
        const bool HasAuthoredLantern=ImportedProp(TEXT("SM_Edo_LanternPost"),P,FRotator::ZeroRotator);
        if(HasAuthoredLantern)
        {
            auto* Pole=Shape(this,RootComponent,FString::Printf(TEXT("LanternCollision%d"),I),TEXT("/Engine/BasicShapes/Cube.Cube"),
                P+FVector(0,0,175),FVector(.14,.14,3.5),FLinearColor::White,true);
            Pole->SetVisibility(false); Pieces.Add(Pole);
        }
        else
        {
            Box(FString::Printf(TEXT("LanternPole%d"),I),P+FVector(0,0,180),FVector(14,14,360),FLinearColor(.12,.08,.06));
            Pieces.Add(Shape(this,RootComponent,FString::Printf(TEXT("Lantern%d"),I),TEXT("/Engine/BasicShapes/Sphere.Sphere"),P+FVector(0,0,355),FVector(.7,.7,1),FLinearColor(.95,.53,.16)));
        }
        auto* Light=GetWorld()->SpawnActor<APointLight>(P+FVector(0,0,HasAuthoredLantern?252.f:350.f),FRotator::ZeroRotator);
        auto* Flame=Light->PointLightComponent.Get();
        // A small paper lantern should light its immediate path, not flood the
        // whole courtyard. Use explicit photometric units on both platforms.
        Flame->SetIntensityUnits(ELightUnits::Lumens);
        Flame->SetIntensity(520.f);
        Flame->SetAttenuationRadius(530.f);
        Flame->SetSourceRadius(9.f);
        Flame->SetUseTemperature(true);
        Flame->SetTemperature(2450.f);
#if PLATFORM_MAC
        // Conventional local-light shadows are costly on the M1 preset.
        Flame->SetCastShadows(I%5==0);
#else
        Flame->SetCastShadows(I%3==0);
#endif
        DecorActors.Add(Light);
    }
    Lighting(MapId);
}
void ASoraWorldBuilder::Lighting(int32 MapId)
{
    const bool bEstate=MapId==0;
    const bool bOccupiedStreet=MapId==1;
    auto* Sun=GetWorld()->SpawnActor<ADirectionalLight>(FVector(0,0,1200),FRotator(bOccupiedStreet?-10.f:-28.f,-35.f,0));
    Sun->SetMobility(EComponentMobility::Movable);
    // The Estate's earlier 0.45-lux key left roofs and tabby faces nearly
    // black against a bright overcast dome. A packaged M1 diagnostic A/B at
    // the same camera found 25 lux readable while 250 washed out the paving.
    Sun->GetLightComponent()->SetIntensity(bEstate?25.f:(bOccupiedStreet?1.8f:4.f));
    Sun->SetLightColor(bEstate?FLinearColor(.83f,.89f,1.f):FLinearColor(1.f,.82f,.66f));
    auto* SunComponent=CastChecked<UDirectionalLightComponent>(Sun->GetLightComponent());
    SunComponent->SetAtmosphereSunLight(true);
    if(bEstate) SunComponent->SetLightSourceAngle(6.f);
    DecorActors.Add(Sun);

    // The atmosphere must exist before the movable sky capture. The estate
    // uses its licensed overcast HDRI for diffuse/reflection lighting instead.
    auto* Atmosphere=GetWorld()->SpawnActor<ASkyAtmosphere>();
    if(!bEstate) Atmosphere->GetComponent()->SetMieScatteringScale(bOccupiedStreet?2.f:1.35f);
    DecorActors.Add(Atmosphere);
    auto* Sky=GetWorld()->SpawnActor<ASkyLight>();
    Sky->GetLightComponent()->SetMobility(EComponentMobility::Movable);
    Sky->GetLightComponent()->bRealTimeCapture=true;
    Sky->GetLightComponent()->SetIntensity(bEstate?.65f:.7f);
    DecorActors.Add(Sky);
    if(MapId==0)
    {
        if(auto* HDRI=LoadObject<UTextureCube>(nullptr,TEXT("/Game/Generated/Environment/Textures/T_NyaagyuOvercast.T_NyaagyuOvercast"),nullptr,LOAD_NoWarn))
        {
            Sky->GetLightComponent()->bRealTimeCapture=false; Sky->GetLightComponent()->SourceType=SLS_SpecifiedCubemap;
            Sky->GetLightComponent()->SetCubemap(HDRI);
            if(auto* SkyMaterial=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Generated/Environment/M_Nyaagyu_Sky.M_Nyaagyu_Sky"),nullptr,LOAD_NoWarn))
            {
                auto* Dome=Shape(this,RootComponent,TEXT("OvercastSky"),TEXT("/Engine/BasicShapes/Sphere.Sphere"),FVector::ZeroVector,FVector(3000),FLinearColor::White);
                Dome->SetMaterial(0,SkyMaterial); Dome->SetCastShadow(false); Pieces.Add(Dome);
            }
        }
    }
    Sky->GetLightComponent()->RecaptureSky();

    auto* Fog=GetWorld()->SpawnActor<AExponentialHeightFog>();
    auto* FogComponent=Fog->GetComponent();
    FogComponent->SetFogDensity(bEstate?.0045f:.0035f);
    FogComponent->SetStartDistance(350.f);
    FogComponent->SetFogMaxOpacity(.58f);
    FogComponent->SetFogInscatteringColor(bEstate?FLinearColor(.38f,.43f,.47f):FLinearColor(.25f,.30f,.35f));
#if PLATFORM_WINDOWS
    FogComponent->SetVolumetricFog(true);
    FogComponent->SetVolumetricFogDistance(4500.f);
    FogComponent->SetVolumetricFogStartDistance(350.f);
    FogComponent->SetVolumetricFogScatteringDistribution(.35f);
    FogComponent->SetVolumetricFogExtinctionScale(.55f);
#endif
    DecorActors.Add(Fog);

    auto* Grade=GetWorld()->SpawnActor<APostProcessVolume>();
    Grade->bUnbound=true;
    auto& Settings=Grade->Settings;
    // Keep silhouettes readable and prevent the sky and lanterns from driving
    // large exposure swings as the first-person camera turns during combat.
    Settings.bOverride_AutoExposureMethod=1;
    Settings.AutoExposureMethod=AEM_Histogram;
    Settings.bOverride_AutoExposureLowPercent=1;
    Settings.AutoExposureLowPercent=12.f;
    Settings.bOverride_AutoExposureHighPercent=1;
    Settings.AutoExposureHighPercent=88.f;
    Settings.bOverride_AutoExposureSpeedUp=1;
    Settings.AutoExposureSpeedUp=1.2f;
    Settings.bOverride_AutoExposureSpeedDown=1;
    Settings.AutoExposureSpeedDown=.7f;
    Settings.bOverride_AutoExposureBias=1;
    Settings.AutoExposureBias=bEstate?-.45f:(bOccupiedStreet?-.3f:0.f);
    Settings.bOverride_ColorSaturation=1;
    Settings.ColorSaturation=FVector4(.96f,.96f,.96f,1.f);
    Settings.bOverride_BloomIntensity=1;
    Settings.BloomIntensity=bOccupiedStreet?.28f:.2f;
    DecorActors.Add(Grade);
}
bool ASoraWorldBuilder::ActivateNearest(const FVector& Location)
{
    const int32 I=NearestInactiveNode(Location);
    if(I>=0&&Nodes.IsValidIndex(I)&&IsValid(Nodes[I]))
    {
        Activated.Add(I); Tint(Nodes[I],FLinearColor(.05f,.75f,.5f));
        if(SiteEffects.IsValidIndex(I)&&IsValid(SiteEffects[I])) Tint(SiteEffects[I],SiteRestoredColors[I]);
        return true;
    }
    return false;
}
int32 ASoraWorldBuilder::NearestInactiveNode(const FVector& Location) const
{
    for(int32 I=0;I<NodePositions.Num();++I)
        if(!Activated.Contains(I)&&FVector::Dist2D(Location,NodePositions[I])<230.f) return I;
    return INDEX_NONE;
}
int32 ASoraWorldBuilder::ActivatedMask() const
{
    int32 Mask=0;
    for(int32 I:Activated) if(I>=0&&I<NodePositions.Num()&&I<31) Mask|=1<<I;
    return Mask;
}
void ASoraWorldBuilder::RestoreActivatedMask(int32 Mask)
{
    Activated.Reset();
    for(int32 I=0;I<NodePositions.Num()&&I<31;++I)
        if((Mask&(1<<I))!=0&&Nodes.IsValidIndex(I)&&IsValid(Nodes[I]))
        {
            Activated.Add(I); Tint(Nodes[I],FLinearColor(.05f,.75f,.5f));
            if(SiteEffects.IsValidIndex(I)&&IsValid(SiteEffects[I])) Tint(SiteEffects[I],SiteRestoredColors[I]);
        }
}
FVector ASoraWorldBuilder::SpawnPoint(int32 Index) const
{
    static const FVector Points[]={FVector(2050,-1100,120),FVector(1850,1100,120),FVector(600,1800,120),FVector(-400,-1850,120),FVector(2100,450,120),FVector(400,-1400,120)};
    return Points[FMath::Abs(Index)%UE_ARRAY_COUNT(Points)];
}
