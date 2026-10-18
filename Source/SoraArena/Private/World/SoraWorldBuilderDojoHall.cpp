#include "SoraWorldBuilder.h"
#include "SoraCatalog.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "HAL/IConsoleManager.h"

// The estate hall interior: the Tsumagizaka dojo kit
// (Content/SourceArt/Environment/NyaagyuDojoKit, imported by
// scripts/unreal/import_nyaagyu_dojo_kit.py) repeated along a hall zone's
// walls. Every module is visual only: the zone's floor, wall and cover boxes
// stay the collision and navigation, and they hide only when the whole kit
// loads. Modules sit on the walls' inner faces and the floor's top at z 0.
//
// Bays are about one ken wide (1.8 m), stretched to fill each wall. The east
// wall faces the entrance: its middle four bays open into the kamiza alcove
// with the SORA maku against dawn-lit shoji, flanked by low renji windows.
// The south wall is shoji with open bays onto the engawa, the north wall
// alternates boards and high windows for the morning light, and the west
// wall holds the entrance. A coffered ceiling closes the hall at the walls'
// height. Instanced components keep a 36 x 26 m hall to a few dozen draws.
namespace
{
// Art review: 0 places every module as its own static mesh component, to
// compare against the instanced sets (1, the default).
TAutoConsoleVariable<int32> CVarHallInstanced(TEXT("sora.HallInstanced"),1,
    TEXT("1: dojo hall modules in instanced sets; 0: one component per module (art review)."));
const TCHAR* DojoKit=TEXT("/Game/Generated/Environment/DojoKit/");
constexpr float BayCm=180.f, FloorTileX=360.f, FloorTileY=260.f, KitWallCm=700.f;

enum class EBay : uint8 { Panel, Renji, RenjiHigh, Shoji, DoorOpen, Kamiza, Count };
const TCHAR* BayMesh[]={TEXT("SM_DojoBay_Panel"),TEXT("SM_DojoBay_Renji"),TEXT("SM_DojoBay_RenjiHigh"),
    TEXT("SM_DojoBay_Shoji"),TEXT("SM_DojoBay_DoorOpen"),TEXT("SM_DojoKamiza")};

UStaticMesh* KitMesh(const TCHAR* Name)
{
    const FString Path=FString::Printf(TEXT("%s%s.%s"),DojoKit,Name,Name);
    return LoadObject<UStaticMesh>(nullptr,*Path,nullptr,LOAD_NoWarn);
}

// Unique timber columns (scripts/art/create_nyaagyu_dojo_timbers.py, imported by
// scripts/unreal/import_nyaagyu_dojo_timbers.py): each is cut from its own seeded
// log, drawn by Nanite on SM6 and by its baked conventional fallback on SM5, with
// the box column's section, height and pivot. "Wall" variants detail the room
// face and the strip of each side in front of the infill; "Open" variants, beside
// door and engawa bays, detail every face. Variants load by index until one is
// missing; with none, the hall keeps the box column.
const TCHAR* DojoTimbers=TEXT("/Game/Generated/Environment/DojoTimbers/");

TArray<UStaticMesh*> TimberColumns(const TCHAR* Kind)
{
    TArray<UStaticMesh*> Out;
    for(int32 I=0;I<64;++I)
    {
        const FString Name=FString::Printf(TEXT("SM_DojoTimberColumn_%s_%02d"),Kind,I);
        UStaticMesh* Mesh=LoadObject<UStaticMesh>(nullptr,*FString::Printf(TEXT("%s%s.%s"),DojoTimbers,*Name,*Name),
            nullptr,LOAD_NoWarn|LOAD_Quiet);
        if(!Mesh) break;
        Out.Add(Mesh);
    }
    return Out;
}

// Which bay a wall's Index-th of Count bays is. Side: 0 south, 1 east, 2 north, 3 west.
EBay BayFor(int32 Side,int32 Index,int32 Count)
{
    const int32 Mid=Count/2;
    switch(Side)
    {
    case 0: return Index%4==2?EBay::DoorOpen:EBay::Shoji;                // south: shoji, engawa every fourth bay
    case 1: if(Count>=8&&Index>=Mid-2&&Index<Mid+2) return EBay::Kamiza; // east: kamiza in the middle
            return Index%2?EBay::Renji:EBay::Panel;
    case 2: return Index%2?EBay::RenjiHigh:EBay::Panel;                  // north: boards and high windows
    default: return Index==Count-1?EBay::DoorOpen:(Index%3==1?EBay::RenjiHigh:EBay::Panel); // west: genkan at the south end
    }
}
}

bool ASoraWorldBuilder::HallInterior(const FSoraZone& Zone,int32 ZoneIndex)
{
    UStaticMesh* Bays[(int32)EBay::Count];
    for(int32 B=0;B<(int32)EBay::Count;++B)
        if(!(Bays[B]=KitMesh(BayMesh[B])))
        {
            UE_LOG(LogTemp,Error,TEXT("SORA dojo kit %s is missing; run scripts/unreal/import_nyaagyu_dojo_kit.py. The hall keeps its primitive walls."),BayMesh[B]);
            return false;
        }
    UStaticMesh* Column=KitMesh(TEXT("SM_DojoColumn"));
    UStaticMesh* Ceiling=KitMesh(TEXT("SM_DojoCeiling"));
    UStaticMesh* Floors[4]={KitMesh(TEXT("SM_DojoFloor_0")),KitMesh(TEXT("SM_DojoFloor_1")),KitMesh(TEXT("SM_DojoFloor_2")),KitMesh(TEXT("SM_DojoFloor_3"))};
    if(!Column||!Ceiling||!Floors[0]||!Floors[1]||!Floors[2]||!Floors[3])
    {
        UE_LOG(LogTemp,Error,TEXT("SORA dojo kit columns, floor or ceiling are missing; the hall keeps its primitive walls."));
        return false;
    }
    TMap<UStaticMesh*,UInstancedStaticMeshComponent*> Sets;
    struct FSingles
    {
        ASoraWorldBuilder* Owner; UStaticMesh* Mesh;
        void AddInstance(const FTransform& T,bool)
        {
            auto* M=NewObject<UStaticMeshComponent>(Owner,MakeUniqueObjectName(Owner,UStaticMeshComponent::StaticClass(),FName(*Mesh->GetName())));
            M->SetCollisionEnabled(ECollisionEnabled::NoCollision); M->SetCanEverAffectNavigation(false);
            M->SetGenerateOverlapEvents(false); M->SetStaticMesh(Mesh); M->SetupAttachment(Owner->GetRootComponent());
            M->SetRelativeTransform(T); M->RegisterComponent(); Owner->AddInstanceComponent(M); Owner->Pieces.Add(M);
        }
    };
    TArray<TUniquePtr<FSingles>> SingleSets;
    const bool bInstanced=CVarHallInstanced.GetValueOnGameThread()!=0;
    auto Singles=[this,&SingleSets](UStaticMesh* Mesh){ SingleSets.Add(MakeUnique<FSingles>(FSingles{this,Mesh})); return SingleSets.Last().Get(); };
    auto Instances=[this,&Sets,ZoneIndex](UStaticMesh* Mesh)
    {
        if(auto** Found=Sets.Find(Mesh)) return *Found;
        auto* Set=NewObject<UInstancedStaticMeshComponent>(this,MakeUniqueObjectName(this,UInstancedStaticMeshComponent::StaticClass(),
            FName(*FString::Printf(TEXT("Zone%dHall_%s"),ZoneIndex,*Mesh->GetName()))));
        // Visual only, never in the navigation octree (see Shape): collision
        // and navigation are off before the mesh is set.
        Set->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Set->SetCanEverAffectNavigation(false);
        Set->SetGenerateOverlapEvents(false);
        Set->SetStaticMesh(Mesh);
        Set->SetupAttachment(RootComponent);
        Set->SetCastShadow(true);
        Set->SetAffectDistanceFieldLighting(true);
        Set->SetAffectDynamicIndirectLighting(true);
        Set->RegisterComponent(); AddInstanceComponent(Set); Pieces.Add(Set);
        Sets.Add(Mesh,Set);
        return Set;
    };
    const FVector2D Min=Zone.Rect.Min,Max=Zone.Rect.Max;
    const float Height=Zone.WallHeight>0.f?Zone.WallHeight:KitWallCm,ZScale=Height/KitWallCm;
    const TArray<UStaticMesh*> WallTimbers=TimberColumns(TEXT("Wall")),OpenTimbers=TimberColumns(TEXT("Open"));
    if(WallTimbers.Num()==0)
        UE_LOG(LogTemp,Warning,TEXT("SORA dojo timber columns are missing; run scripts/unreal/import_nyaagyu_dojo_timbers.py. The hall uses the box column."));
    int32 Counts[4];
    for(int32 Side=0;Side<4;++Side)
        Counts[Side]=FMath::Max(1,FMath::RoundToInt32(((Side%2==0)?Max.X-Min.X:Max.Y-Min.Y)/BayCm));
    UStaticMesh* LastTimber=nullptr;
    // Walls, each walked from its first inner corner with the room on the
    // module's local +Y: south (+X), east (+Y), north (-X), west (-Y).
    const FVector2D Start[4]={FVector2D(Min.X,Min.Y),FVector2D(Max.X,Min.Y),FVector2D(Max.X,Max.Y),FVector2D(Min.X,Max.Y)};
    const FVector2D Along[4]={FVector2D(1,0),FVector2D(0,1),FVector2D(-1,0),FVector2D(0,-1)};
    const float Yaw[4]={0.f,90.f,180.f,-90.f};
    for(int32 Side=0;Side<4;++Side)
    {
        const float Length=(Side%2==0)?Max.X-Min.X:Max.Y-Min.Y;
        const int32 Count=Counts[Side];
        const float Width=Length/Count;
        int32 Index=0;
        while(Index<Count)
        {
            const EBay Kind=BayFor(Side,Index,Count);
            const int32 Span=Kind==EBay::Kamiza?4:1;
            const FVector2D Centre=Start[Side]+Along[Side]*(Index+Span*.5f)*Width;
            const FTransform Bay(FRotator(0,Yaw[Side],0),FVector(Centre,0.f),
                FVector(Width/BayCm,1.f,Kind==EBay::Kamiza?1.f:ZScale));
            if(bInstanced) Instances(Bays[(int32)Kind])->AddInstance(Bay,true); else Singles(Bays[(int32)Kind])->AddInstance(Bay,true);
            // A column at each bay's start; none inside the kamiza opening.
            for(int32 Inner=0;Inner<Span;++Inner)
                if(Inner==0)
                {
                    // Beside a door or engawa bay every face of the column shows.
                    const int32 Prev=(Side+3)%4;
                    const EBay Before=Index>0?BayFor(Side,Index-1,Count):BayFor(Prev,Counts[Prev]-1,Counts[Prev]);
                    const bool bOpen=Kind==EBay::DoorOpen||Before==EBay::DoorOpen;
                    const TArray<UStaticMesh*>& Pool=(bOpen&&OpenTimbers.Num())?OpenTimbers:WallTimbers;
                    UStaticMesh* Mesh=Column;
                    bool bMirror=false;
                    if(Pool.Num())
                    {
                        // A stable pick per bay; no two neighbours alike, and a
                        // mirrored copy (room face still -Y) reads as another column.
                        const uint32 H=HashCombine(HashCombine(GetTypeHash(ZoneIndex),GetTypeHash(Side)),GetTypeHash(Index));
                        const uint32 N=(uint32)Pool.Num();
                        Mesh=Pool[(int32)(H%N)];
                        if(Mesh==LastTimber&&N>1) Mesh=Pool[(int32)((H+1)%N)];
                        bMirror=((H>>8)&1u)!=0;
                        LastTimber=Mesh;
                    }
                    const FTransform Post(FRotator(0,Yaw[Side],0),FVector(Start[Side]+Along[Side]*(Index+Inner)*Width,0.f),
                        FVector(bMirror?-1.f:1.f,1.f,ZScale));
                    if(bInstanced) Instances(Mesh)->AddInstance(Post,true); else Singles(Mesh)->AddInstance(Post,true);
                }
            Index+=Span;
        }
    }
    // Floor tiles cover the hall exactly (each stretched by a few percent),
    // in four board layouts so no two neighbours repeat.
    const int32 NX=FMath::Max(1,FMath::RoundToInt32((Max.X-Min.X)/FloorTileX)),NY=FMath::Max(1,FMath::RoundToInt32((Max.Y-Min.Y)/FloorTileY));
    const float TX=(Max.X-Min.X)/NX,TY=(Max.Y-Min.Y)/NY;
    for(int32 X=0;X<NX;++X) for(int32 Y=0;Y<NY;++Y)
    {
        const int32 Variant=(X*7+Y*13+ZoneIndex)%4;
        const FTransform Tile(FRotator::ZeroRotator,FVector(Min.X+(X+.5f)*TX,Min.Y+(Y+.5f)*TY,0.f),FVector(TX/FloorTileX,TY/FloorTileY,1.f));
        if(bInstanced) Instances(Floors[Variant])->AddInstance(Tile,true); else Singles(Floors[Variant])->AddInstance(Tile,true);
    }
    // The coffered ceiling at the walls' height (the tile is modelled at 7 m).
    const int32 CX=FMath::Max(1,FMath::RoundToInt32((Max.X-Min.X)/BayCm)),CY=FMath::Max(1,FMath::RoundToInt32((Max.Y-Min.Y)/BayCm));
    const float CW=(Max.X-Min.X)/CX,CH=(Max.Y-Min.Y)/CY;
    for(int32 X=0;X<CX;++X) for(int32 Y=0;Y<CY;++Y)
    {
        const FTransform Tile(FRotator::ZeroRotator,FVector(Min.X+(X+.5f)*CW,Min.Y+(Y+.5f)*CH,Height-KitWallCm),FVector(CW/BayCm,CH/BayCm,1.f));
        if(bInstanced) Instances(Ceiling)->AddInstance(Tile,true); else Singles(Ceiling)->AddInstance(Tile,true);
    }
    // A roof deck over the coffers and the wall tops: closed and thick, so
    // neither the shadow maps nor software Lumen's distance fields let the
    // sky in through the ceiling's seams. Never seen from inside the hall.
    auto* Deck=Box(FString::Printf(TEXT("Zone%dHallRoofDeck"),ZoneIndex),
        FVector((Min.X+Max.X)*.5f,(Min.Y+Max.Y)*.5f,Height+14.f+35.f),
        FVector(Max.X-Min.X+260.f,Max.Y-Min.Y+260.f,70.f),FLinearColor(.06f,.05f,.045f),false);
    Deck->SetCanEverAffectNavigation(false);
    return true;
}
