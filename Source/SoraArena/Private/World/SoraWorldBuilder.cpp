#include "SoraWorldBuilder.h"
#include "SoraTerminalChargeRules.h"
#include "SoraNoticeSquareRules.h"
#include "SoraCatalog.h"
#include "Components/PointLightComponent.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/WidgetComponent.h"
#include "Engine/PointLight.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"

ASoraWorldBuilder::ASoraWorldBuilder()
{
    PrimaryActorTick.bCanEverTick=true;
    PrimaryActorTick.bStartWithTickEnabled=false;
    RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("ArenaRoot"));
}
UStaticMeshComponent* ASoraWorldBuilder::Shape(AActor* Owner, USceneComponent* Parent, const FString& Name, const TCHAR* Asset, FVector Location, FVector Scale, FLinearColor Color, bool Collision)
{
    UStaticMeshComponent* M = NewObject<UStaticMeshComponent>(Owner, MakeUniqueObjectName(Owner,UStaticMeshComponent::StaticClass(),FName(*Name)));
    // Collision and navigation come before the mesh. Setting a mesh on a new
    // component that still has the default blocking collision enters it in
    // the navigation octree at the origin; a cooked game (whose meshes are
    // never still compiling) keeps that entry after the collision is turned
    // off, and the next rebuild cuts holes wherever the visual shape stands.
    M->SetCollisionEnabled(Collision ? ECollisionEnabled::QueryAndPhysics : ECollisionEnabled::NoCollision);
    M->SetCollisionResponseToAllChannels(ECR_Block);
    M->SetCanEverAffectNavigation(Collision);
    M->SetStaticMesh(LoadObject<UStaticMesh>(nullptr, Asset));
    M->SetupAttachment(Parent);
    M->SetRelativeLocation(Location); M->SetRelativeScale3D(Scale);
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
        UE_LOG(LogTemp,Error,TEXT("SORA authored environment prop %s is missing; run scripts/toolchain/import-mac.sh. Primitive fallback is provisional."),*Path);
        return false;
    }
    auto* Mesh=NewObject<UStaticMeshComponent>(this,MakeUniqueObjectName(this,UStaticMeshComponent::StaticClass(),FName(*Name)));
    // Visual only, so never in the navigation octree (see Shape).
    Mesh->SetCanEverAffectNavigation(false);
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
    ShowObjective(nullptr); ShowCaches({}); ClearKit(); ClearSummitTiles(); ClearBridge();
    for(const auto& M:PickupPieces) if(M) M->DestroyComponent(); PickupPieces.Reset();
    for(const auto& A:PickupLights) if(A) A->Destroy(); PickupLights.Reset();
    for(const auto& M:Pieces) if(M) M->DestroyComponent(); Pieces.Reset();
    WoodTargets.Reset(); WoodFloors.Reset(); WoodClapper=nullptr;
    TenementFindTargets.Reset();
    if(IsValid(ArchivePageText)) ArchivePageText->DestroyComponent();
    ArchivePageText=nullptr; ArchivePageFont=nullptr;
    ArchivePage=nullptr; ArchivePageLight=nullptr; ArchiveNorthGate=nullptr; ArchiveEastRack=nullptr; ArchiveExposure=nullptr;
    RidgeAnchors.Reset(); RidgeOrigin=FVector2D::ZeroVector;
    SummitSpine=nullptr; SummitSeam=nullptr;
    WorkshopDoor=nullptr; WorkshopSeal=nullptr; WorkshopBar=nullptr;
    WorkshopWindows.Reset(); WorkshopWindowLights.Reset();
    SpireShutter=nullptr; SpirePanels.Reset(); SpirePanelGoals.Reset();
    for(const auto& A:DecorActors) if(A) A->Destroy(); DecorActors.Reset(); Nodes.Reset(); SiteEffects.Reset(); SiteRestoredColors.Reset(); Activated.Reset(); NodePositions.Reset();
    bCampaignSpace=false; CampaignStart=FVector::ZeroVector; CampaignStartYaw=0.f;
}
FVector ASoraWorldBuilder::PlayerStart() const
{
    return bCampaignSpace?CampaignStart:FVector(-2700,0,120);
}
void ASoraWorldBuilder::Build(int32 MapId,const FSoraChapter* Chapter)
{
    ClearArena();
    // A campaign chapter builds its own space; the training arena keeps the
    // shared layout with its three workshops.
    if(Chapter) BuildCampaign(*Chapter);
    else BuildArena(MapId,true);
}
void ASoraWorldBuilder::BuildArena(int32 MapId,bool bSites,bool bTenements,bool bLanternWorkshop)
{
    const FLinearColor Accent=FSoraCatalog::Get().Map(MapId).Accent;
    Box(TEXT("Ground"),FVector(0,0,-50),FVector(6400,5200,100),FLinearColor(.14f,.16f,.13f),true,FRotator::ZeroRotator,TEXT("Soil"));
    const bool NoticeSquare=MapId==1&&bTenements;
    if(NoticeSquare)
    {
        namespace N=SoraNoticeSquareRules;
        for(int I=0;I<3;++I)
        {
            const auto B=N::StreetFloors[I];
            Box(FString::Printf(TEXT("NoticeSquareStreet%d"),I),FVector(B.X,B.Y,B.Z),FVector(B.SX,B.SY,B.SZ),
                FLinearColor(.14f,.16f,.13f),true,FRotator::ZeroRotator,TEXT("Soil"));
        }
        for(int I=0;I<6;++I)
        {
            const auto B=N::StreetWalls[I];
            Box(FString::Printf(TEXT("NoticeSquareBoundary%d"),I),FVector(B.X,B.Y,B.Z),FVector(B.SX,B.SY,B.SZ),
                FLinearColor(.2f,.23f,.23f),true,FRotator::ZeroRotator,TEXT("Stone"));
        }
    }
    if(MapId==0) NyaagyuTerrain();
    // The imported estate tiles already carry the photographed stone route.
    // The old raised blockout covered that path and hid its relief entirely.
    if(MapId!=0)
        Box(TEXT("CentralRoad"),FVector(0,0,2),FVector(5600,660,5),FLinearColor(.29f,.30f,.28f),false,FRotator::ZeroRotator,TEXT("Stone"));
    for(int32 S:{-1,1})
    {
        const bool WestJoin=bTenements&&MapId==1&&S==-1;
        const bool EastJoin=bLanternWorkshop&&MapId==1&&S==1;
        auto* WallX=Box(FString::Printf(TEXT("WallX%d"),S),FVector(S*3150,WestJoin?-1425:EastJoin?1400:0,220),
            FVector(100,WestJoin?2350:EastJoin?2400:5200,540),FLinearColor(.2f,.23f,.23f),true,FRotator::ZeroRotator,TEXT("Stone"));
        if(EastJoin)Box(TEXT("WardEastWallSouth"),FVector(3150,-2500,220),FVector(100,200,540),
            FLinearColor(.2f,.23f,.23f),true,FRotator::ZeroRotator,TEXT("Stone"));
        UStaticMeshComponent* WallY=nullptr;
        if(bTenements&&MapId==1&&S==1)
        {
            // Keep the old wall outside the alley/court and the 1.2 m
            // north passage. The new district owns those openings.
            Box(TEXT("WardNorthWallWest"),FVector(-1630,2550,220),FVector(1140,100,540),
                FLinearColor(.2f,.23f,.23f),true,FRotator::ZeroRotator,TEXT("Stone"));
            for(int I=0;I<2;++I)
            {
                const auto B=SoraNoticeSquareRules::NorthWalls[I];
                WallY=Box(FString::Printf(TEXT("WardNorthWallEast%d"),I),FVector(B.X,B.Y,B.Z),FVector(B.SX,B.SY,B.SZ),
                    FLinearColor(.2f,.23f,.23f),true,FRotator::ZeroRotator,TEXT("Stone"));
            }
        }
        else WallY=Box(FString::Printf(TEXT("WallY%d"),S),FVector(0,S*2550,220),FVector(6400,100,540),FLinearColor(.2f,.23f,.23f),true,FRotator::ZeroRotator,TEXT("Stone"));
        if(MapId==0) EstatePerimeter(S,WallX,WallY);
        for(int32 I=0;I<5;++I)
        {
            // The original repeated row placed a house in both arms of the
            // authored north-south street. Leave the crossing's stubs open.
            if(NoticeSquare&&!SoraNoticeSquareRules::KeepLegacyHouse(I))continue;
            if(bLanternWorkshop&&MapId==1&&S==-1&&I==4)continue;
            FVector P(-2000+I*1000,S*(MapId==1?1200:1800),0);
            const float Height=MapId==3?780.f:330.f+(I%2)*100.f;
            if(bTenements&&MapId==1&&S==1&&I==1)
            {
                // Split this house around the authored side passage. Its
                // foundations, rather than just the walls, clear all 120 cm.
                for(float X:{-1201.25f,-798.75f})
                    Building(FVector(X,P.Y,0),FVector(247.5f,700,Height),FLinearColor(.63f,.56f,.40f),false);
                continue;
            }
            const int32 BuildingStart=Pieces.Num();
            Building(P,FVector(650,700,Height),MapId==3?FLinearColor(.12f,.15f,.19f):FLinearColor(.63f,.56f,.40f),MapId>=2);
            if(MapId==0) EstateHall(I,S,P,BuildingStart);
        }
    }
    if(MapId==0) EstateGrounds();
    for(int32 I=0;I<12;++I)
    {
        if(bLanternWorkshop&&MapId==1&&I==5)continue;
        const float X=-2300+(I%6)*900; const float Y=(I<6?-1:1)*(680+(I%2)*200);
        if(NoticeSquare&&!SoraNoticeSquareRules::KeepLegacyCover(X,Y))continue;
        auto* Cover=Box(FString::Printf(TEXT("Cover%d"),I),FVector(X,Y,70),FVector(230,180,140),I%2?FLinearColor(.29f,.19f,.09f):FLinearColor(.23f,.27f,.28f),true,FRotator::ZeroRotator,I%2?TEXT("Timber"):TEXT("Stone"));
        // Keep the established cover volume for campaign combat. Dressing
        // meshes are visual only and never enter a P2P practice map.
        if(MapId==0) EstateCargo(I,FVector(X,Y,0),Cover);
    }
    Torii(FVector(-2250,0,0),0); Torii(FVector(2300,0,0),0);
    // The arena's three site positions; a campaign hub builds its chapter's
    // sites where its space puts them instead.
    NodePositions={FVector(-1250,-700,0),FVector(0,1000,0),FVector(1250,-800,0)};
    if(bSites) ProductionSites(MapId,Accent);
    if(MapId==3) DebtCitadelKiosk();
    if(MapId==1) LanternWardTerminal();
    if(MapId==1&&bTenements)
    {
        // 103 cm clear behind the terminal fits the fixed 68 cm capsule.
        // The authored 60 cm squeeze needs a narrower movement mode before it can be restored.
        for(int I=1;I<3;++I)
        {
            const auto S=SoraTerminalChargeRules::Solids[I];
            Box(I==1?TEXT("NoticeBoard"):TEXT("NoticeBoardRoof"),FVector(S.X,S.Y,S.Z),FVector(S.SX,S.SY,S.SZ),
                FLinearColor(.30f,.22f,.12f),true);
        }
    }
    Lanterns(bLanternWorkshop&&MapId==1);
    Lighting(MapId);
}
void ASoraWorldBuilder::ProductionSites(int32 MapId,FLinearColor Accent)
{
    for(int32 I=0;I<NodePositions.Num();++I) SiteStructure(I,NodePositions[I],TEXT("workshop"),MapId,Accent);
}
void ASoraWorldBuilder::SiteStructure(int32 I,FVector P,const FString& Kind,int32 MapId,FLinearColor Accent)
{
    Box(FString::Printf(TEXT("ProductionBase%d"),I),P+FVector(0,0,45),FVector(200,200,90),FLinearColor(.14f,.19f,.23f),true,FRotator::ZeroRotator,TEXT("Metal"));
    auto* N=Shape(this,RootComponent,FString::Printf(TEXT("ProductionCore%d"),I),TEXT("/Engine/BasicShapes/Cylinder.Cylinder"),P+FVector(0,0,145),FVector(.7f,.7f,1.5f),FLinearColor(.8f,.07f,.12f),true); Pieces.Add(N);
    if(Nodes.Num()<=I) { Nodes.SetNum(I+1); SiteEffects.SetNum(I+1); SiteRestoredColors.SetNum(I+1); }
    Nodes[I]=N; SiteEffects[I]=nullptr;
    SiteRestoredColors[I]=Kind==TEXT("foundry")?FLinearColor(.96f,.37f,.08f)
        :Kind==TEXT("irrigation")?FLinearColor(.08f,.45f,.83f)
        :Kind==TEXT("supplies")||Kind==TEXT("training")||Kind==TEXT("workshop")?FLinearColor(.82f,.59f,.19f)
        :FLinearColor(.07f,.62f,.53f);
    if(Kind==TEXT("irrigation"))
    {
        SiteEffects[I]=Box(FString::Printf(TEXT("WaterChannel%d"),I),P+FVector(0,-205,18),FVector(420,130,35),FLinearColor(.04f,.07f,.09f),false);
        auto* Wheel=Shape(this,RootComponent,FString::Printf(TEXT("Waterwheel%d"),I),TEXT("/Engine/BasicShapes/Cylinder.Cylinder"),P+FVector(0,0,290),FVector(2.1f,.32f,2.1f),FLinearColor(.27f,.18f,.08f),false);
        Wheel->SetRelativeRotation(FRotator(90,0,0)); Pieces.Add(Wheel);
        if(MapId==0) EstateSluice(P);
    }
    else if(Kind==TEXT("foundry"))
    {
        Box(FString::Printf(TEXT("Furnace%d"),I),P+FVector(0,0,255),FVector(280,250,290),FLinearColor(.19f,.21f,.24f),true,FRotator::ZeroRotator,TEXT("Stone"));
        SiteEffects[I]=Box(FString::Printf(TEXT("ForgeMouth%d"),I),P+FVector(0,-130,220),FVector(125,20,100),FLinearColor(.12f,.05f,.03f),false);
        Box(FString::Printf(TEXT("ForgeStack%d"),I),P+FVector(80,70,475),FVector(80,80,220),FLinearColor(.14f,.16f,.18f),true,FRotator::ZeroRotator,TEXT("Metal"));
        if(MapId==2) SilkFoundryLoom(P);
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
void ASoraWorldBuilder::Lanterns(bool bLanternWorkshop)
{
    for(int32 I=0;I<10;++I)
    {
        if(bLanternWorkshop&&I==4)continue;
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
