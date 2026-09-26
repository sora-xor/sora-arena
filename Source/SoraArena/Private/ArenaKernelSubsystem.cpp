#include "ArenaKernelSubsystem.h"
#include "Dom/JsonObject.h"
#include "HAL/PlatformProcess.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "arena.h"

static_assert(ARENA_ABI_VERSION==4,"This loader is written against kernel ABI 4");
static_assert(sizeof(ArenaPlayerPresentation)==72,"Unexpected ABI 4 player presentation layout");
static_assert(offsetof(ArenaPlayerPresentation,charge_ticks_current)==36,"Unexpected ABI 4 charge offset");
static_assert(sizeof(ArenaWeaponSpec)==48,"Unexpected ABI 4 weapon layout");
static_assert(sizeof(ArenaEvent)==48&&offsetof(ArenaEvent,detail)==44,"Unexpected ABI 4 event layout");
static_assert(sizeof(ArenaMapInfo)==76&&sizeof(ArenaEntitySnapshot)==60&&sizeof(ArenaObjectiveSnapshot)==96,"Unexpected ABI 4 query layout");
static_assert(SoraPractice::FreeForAll==0&&SoraPractice::Control==1&&SoraPractice::Payload==2&&SoraPractice::Melee==3,"Practice modes are ArenaConfig.mode");
static_assert(SoraPractice::BotNovice==ARENA_BOT_NOVICE&&SoraPractice::BotStandard==ARENA_BOT_STANDARD&&SoraPractice::BotVeteran==ARENA_BOT_VETERAN
    &&SoraPractice::BotMaster==ARENA_BOT_MASTER&&SoraPractice::BotCount==ARENA_BOT_MASTER+1,"Practice tiers are ARENA_BOT_*");
static_assert(SoraPractice::Decoy==ARENA_ENTITY_DECOY&&SoraPractice::Barricade==ARENA_ENTITY_BARRICADE&&SoraPractice::FireZone==ARENA_ENTITY_FIRE_ZONE&&SoraPractice::Ward==ARENA_ENTITY_WARD,"Practice entity kinds are ARENA_ENTITY_*");
static_assert(SoraPractice::WinnerNone==ARENA_WINNER_NONE&&SoraPractice::WinnerTeam==ARENA_WINNER_TEAM&&SoraPractice::WinnerSlot==ARENA_WINNER_SLOT&&SoraPractice::WinnerDraw==ARENA_WINNER_DRAW,"Practice winners are ARENA_WINNER_*");
static_assert(SoraPractice::HazardFire==ARENA_HAZARD_FIRE&&SoraPractice::HazardSlag==ARENA_HAZARD_SLAG&&SoraPractice::HazardShredder==ARENA_HAZARD_SHREDDER,"Practice hazards are ARENA_HAZARD_*");

struct FKernelRuntime
{
    decltype(&arena_abi_version) Abi = nullptr;
    decltype(&arena_proof_qualified) Qualified = nullptr;
    decltype(&arena_create) Create = nullptr;
    decltype(&arena_destroy) Destroy = nullptr;
    decltype(&arena_step) Step = nullptr;
    decltype(&arena_snapshot) Snapshot = nullptr;
    decltype(&arena_player) Player = nullptr;
    decltype(&arena_state_hash) Hash = nullptr;
    decltype(&arena_map_info) MapInfo = nullptr;
    decltype(&arena_map_wall) MapWall = nullptr;
    decltype(&arena_player_presentation) Presentation = nullptr;
    decltype(&arena_weapon_spec) WeaponSpec = nullptr;
    decltype(&arena_event) Event = nullptr;
    decltype(&arena_projectile_count) ProjectileCount = nullptr;
    decltype(&arena_projectile) Projectile = nullptr;
    decltype(&arena_map_route_point) MapRoutePoint = nullptr;
    decltype(&arena_map_hazard) MapHazard = nullptr;
    decltype(&arena_entity_count) EntityCount = nullptr;
    decltype(&arena_entity) Entity = nullptr;
    decltype(&arena_objective) Objective = nullptr;
    decltype(&arena_bot_input) BotInput = nullptr;
    ArenaHandle* Practice = nullptr;
};
namespace
{
constexpr uint32 ExpectedKernelAbi = ARENA_ABI_VERSION;
// At most 48 live entities (combat-rules §5.1) and 256 projectiles.
constexpr uint32 MaxEntities = 48;
constexpr uint32 MaxProjectiles = 256;
FVector Millimeters(int32 X,int32 Y,int32 Z) { return FVector(X/10.0,Y/10.0,Z/10.0); }
int32 Slot32(uint32 Value) { return Value==ARENA_NONE?INDEX_NONE:static_cast<int32>(Value); }
FSoraPracticeInput FromArena(const ArenaInput& In)
{
    FSoraPracticeInput Out; Out.Forward=In.move_x; Out.Right=In.move_y; Out.Yaw=In.yaw; Out.Pitch=In.pitch; Out.Buttons=In.buttons;
    return Out;
}
// Bots fill each team by rank in this order after the player's own class: a
// blade, a medic, a marksman, a bomber, an engineer and a flanker.
constexpr int32 TeamRoleOrder[SoraPractice::ClassCount]={0,5,2,3,4,1};
// The practice roster. Slot 0 is the player on team 0 (the Payload
// attackers); team modes alternate teams by slot so both sides are even.
// Free-for-all and Melee bots take the classes after the player's in turn.
// Samurai bots draw the katana and Melee bots their class blade; everyone
// else starts ranged. Bots change loadout themselves at respawn.
void BuildRoster(const FSoraPracticeConfig& Config,TArray<ArenaParticipant>& Roster)
{
    Roster.SetNumZeroed(Config.PlayerCount);
    const bool bTeams=SoraPractice::IsTeamMode(Config.Mode);
    const bool bMelee=Config.Mode==SoraPractice::Melee;
    TArray<int32> Taken[2];
    for(int32 Slot=0;Slot<Config.PlayerCount;++Slot)
    {
        ArenaParticipant& P=Roster[Slot];
        P.slot=Slot; P.team=Slot%2; P.bond=0; P.special_entitled=0; P.reserved=0;
        int32 Class=Config.ClassId;
        if(Slot>0&&!bTeams) Class=(Config.ClassId+Slot)%SoraPractice::ClassCount;
        else if(Slot>0)
        {
            // The next role in TeamRoleOrder that this team does not field yet.
            TArray<int32>& Team=Taken[P.team];
            Class=TeamRoleOrder[Team.Num()%SoraPractice::ClassCount];
            for(const int32 Role:TeamRoleOrder) if(!Team.Contains(Role)) { Class=Role; break; }
        }
        Taken[P.team].Add(Class);
        P.class_id=Class;
        if(Slot==0) P.weapon_id=SoraPractice::EntryWeapon(Config.Mode,Class,Config.SpecialWeaponId);
        else P.weapon_id=bMelee||Class==0?2*Class:2*Class+1;
    }
}
// Reads an exact 32-bit integer from the arena JSON.
bool JsonInt(const TSharedPtr<FJsonValue>& Value,int32& Out)
{
    double Number=0;
    if(!Value.IsValid()||!Value->TryGetNumber(Number)||Number!=FMath::RoundToDouble(Number)||Number<MIN_int32||Number>MAX_int32) return false;
    Out=static_cast<int32>(Number); return true;
}
bool JsonField(const TSharedPtr<FJsonObject>& Object,const TCHAR* Name,int32& Out)
{
    return Object.IsValid()&&JsonInt(Object->TryGetField(Name),Out);
}
// An [x, y] or [x, y, z] array of exact integers.
bool JsonPoint(const TSharedPtr<FJsonValue>& Value,int32 Count,int32* Out)
{
    const TArray<TSharedPtr<FJsonValue>>* Items=nullptr;
    if(!Value.IsValid()||!Value->TryGetArray(Items)||Items->Num()!=Count) return false;
    for(int32 I=0;I<Count;++I) if(!JsonInt((*Items)[I],Out[I])) return false;
    return true;
}
const TArray<TSharedPtr<FJsonValue>>* JsonArray(const TSharedPtr<FJsonObject>& Object,const TCHAR* Name)
{
    const TArray<TSharedPtr<FJsonValue>>* Items=nullptr;
    return Object.IsValid()&&Object->TryGetArrayField(Name,Items)?Items:nullptr;
}
}
FVector FSoraPracticeMap::RoutePoint(float Distance) const
{
    if(Route.IsEmpty()) return FVector::ZeroVector;
    float Remaining=FMath::Max(0.f,Distance);
    for(int32 I=1;I<Route.Num();++I)
    {
        const float Length=FVector::Dist2D(Route[I-1],Route[I]);
        if(Remaining<=Length&&Length>0.f) return FMath::Lerp(Route[I-1],Route[I],Remaining/Length);
        Remaining-=Length;
    }
    return Route.Last();
}
void UArenaKernelSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    StatusText=TEXT("決定論的戦闘カーネル：未読込");
#if PLATFORM_MAC
    const FString File=TEXT("Mac/libarena_ffi.dylib");
#elif PLATFORM_WINDOWS
    const FString File=TEXT("Win64/arena_ffi.dll");
#else
    StatusText=TEXT("このプラットフォームのカーネルは未対応です。"); return;
#endif
#if PLATFORM_MAC || PLATFORM_WINDOWS
    Library=FPlatformProcess::GetDllHandle(*(FPaths::ProjectDir()/TEXT("Binaries")/File));
    if(!Library) return;
    Runtime=new FKernelRuntime();
#define LOAD_KERNEL(Member,Export) Runtime->Member=reinterpret_cast<decltype(Runtime->Member)>(FPlatformProcess::GetDllExport(Library,TEXT(#Export)))
    LOAD_KERNEL(Abi,arena_abi_version); LOAD_KERNEL(Qualified,arena_proof_qualified);
    LOAD_KERNEL(Create,arena_create); LOAD_KERNEL(Destroy,arena_destroy); LOAD_KERNEL(Step,arena_step);
    LOAD_KERNEL(Snapshot,arena_snapshot); LOAD_KERNEL(Player,arena_player); LOAD_KERNEL(Hash,arena_state_hash);
    LOAD_KERNEL(MapInfo,arena_map_info); LOAD_KERNEL(MapWall,arena_map_wall); LOAD_KERNEL(Presentation,arena_player_presentation);
    LOAD_KERNEL(WeaponSpec,arena_weapon_spec); LOAD_KERNEL(Event,arena_event);
    LOAD_KERNEL(ProjectileCount,arena_projectile_count); LOAD_KERNEL(Projectile,arena_projectile);
    LOAD_KERNEL(MapRoutePoint,arena_map_route_point); LOAD_KERNEL(MapHazard,arena_map_hazard);
    LOAD_KERNEL(EntityCount,arena_entity_count); LOAD_KERNEL(Entity,arena_entity); LOAD_KERNEL(Objective,arena_objective);
    LOAD_KERNEL(BotInput,arena_bot_input);
#undef LOAD_KERNEL
    const auto& R=*Runtime;
    // Every ABI 4 export must resolve before the version call; a stale library fails here.
    if(!R.Abi||!R.Qualified||!R.Create||!R.Destroy||!R.Step||!R.Snapshot||!R.Player||!R.Hash||!R.MapInfo||!R.MapWall||!R.Presentation||!R.WeaponSpec||!R.Event||!R.ProjectileCount||!R.Projectile
        ||!R.MapRoutePoint||!R.MapHazard||!R.EntityCount||!R.Entity||!R.Objective||!R.BotInput||R.Abi()!=ExpectedKernelAbi)
    { StatusText=TEXT("戦闘カーネルの ABI 検証に失敗しました。現在のソースから再ビルドしてください。"); return; }
    AbiVersion=R.Abi(); ProofQualified=R.Qualified()!=0;
    ArenaConfig Config{}; Config.abi_version=AbiVersion; Config.mode=0; Config.map_id=0; Config.max_ticks=60; Config.player_count=1; Config.offline=1;
    ArenaParticipant Participant{}; Participant.slot=0; Participant.team=0; Participant.class_id=0; Participant.weapon_id=1;
    ArenaHandle* Handle=R.Create(&Config,&Participant,1);
    if(!Handle) { StatusText=TEXT("オフライン検証セッションを作成できませんでした。"); return; }
    ArenaInput Input{}; Input.slot=0; Input.move_x=32;
    bool Good=true;
    for(int32 Tick=0;Tick<60;++Tick) if(R.Step(Handle,&Input,1)!=0) { Good=false; break; }
    ArenaSnapshot State{}; uint8 Digest[32]{};
    Good=Good&&R.Snapshot(Handle,&State)==0&&R.Hash(Handle,Digest,sizeof(Digest))==0;
    R.Destroy(Handle);
    if(!Good||State.abi_version!=ExpectedKernelAbi||State.deposited!=0||State.remaining!=0||State.earnings!=0||State.tick!=60)
    { StatusText=TEXT("戦闘カーネルの無入金テストに失敗しました。"); return; }
    VerifiedOfflineTicks=State.tick; OfflineStateHash=BytesToHex(Digest,32); Available=true;
    StatusText=FString::Printf(TEXT("Rust ABI %d：%d tick 検証済み / 対戦証明 %s"),AbiVersion,VerifiedOfflineTicks,ProofQualified?TEXT("認証済み"):TEXT("未認証"));
#endif
}
bool UArenaKernelSubsystem::PracticeActive() const { return Runtime&&Runtime->Practice; }
void UArenaKernelSubsystem::StopPractice()
{
    if(Runtime&&Runtime->Practice) { Runtime->Destroy(Runtime->Practice); Runtime->Practice=nullptr; }
    PracticePlayers.Reset(); PracticeEvents.Reset(); PracticeProjectiles.Reset(); PracticeEntities.Reset();
    PracticeObjective=FSoraPracticeObjective();
    PracticeTick=0; PracticeTerminal=false; PracticeHash.Empty();
    PracticeDeposited=PracticeRemaining=PracticeEarnings=0;
}
bool UArenaKernelSubsystem::Refuse(const TCHAR* Japanese,const TCHAR* English)
{
    PracticeError=Japanese; PracticeErrorEnglish=English;
    return false;
}
bool UArenaKernelSubsystem::ValidatePractice(const FSoraPracticeConfig& Config,FString* Why,FString* WhyEnglish) const
{
    const auto Reject=[Why,WhyEnglish](const TCHAR* Japanese,const TCHAR* English)
    {
        if(Why) *Why=Japanese;
        if(WhyEnglish) *WhyEnglish=English;
        return false;
    };
    using namespace SoraPractice;
    if(!Available||!Runtime) return Reject(TEXT("稽古には、検証済みの実物 Rust ライブラリが必要です。"),TEXT("Practice needs the staged, verified Rust kernel library."));
    if(Config.Mode<0||Config.Mode>=ModeCount) return Reject(TEXT("稽古の形式が範囲外です。"),TEXT("The practice mode is out of range."));
    if(Config.MapId<0||Config.MapId>=MapCount) return Reject(TEXT("稽古の舞台が範囲外です。"),TEXT("The practice arena is out of range."));
    if(Config.ClassId<0||Config.ClassId>=ClassCount) return Reject(TEXT("稽古の流儀が範囲外です。"),TEXT("The practice class is out of range."));
    if(Config.Difficulty<BotNovice||Config.Difficulty>=BotCount) return Reject(TEXT("ボットの難易度が範囲外です。"),TEXT("The bot difficulty is out of range."));
    if(Config.PlayerCount<MinPlayers(Config.Mode)||Config.PlayerCount>MaxPlayers(Config.Mode)||Config.PlayerCount%PlayerStep(Config.Mode)!=0)
        return Reject(TEXT("この形式に合わない人数です（乱戦・近接のみは 2〜8 人、団体戦は 2〜12 人の偶数）。"),
            TEXT("That many players does not fit the mode (2-8 in free-for-all and Melee only, an even 2-12 in team modes)."));
    if(Config.SpecialWeaponId!=INDEX_NONE)
    {
        ArenaWeaponSpec Spec{};
        if(Config.SpecialWeaponId!=SpecialOf(Config.ClassId)) return Reject(TEXT("特殊武器はその流儀のものに限られます。"),TEXT("The special weapon must be the class's own."));
        if(Runtime->WeaponSpec(Config.SpecialWeaponId,&Spec)!=0) return Reject(TEXT("特殊武器の参照データを読み込めません。"),TEXT("The kernel has no data for that special weapon."));
        if(Config.Mode==Melee&&Spec.kind!=0) return Reject(TEXT("近接のみでは近接の特殊武器しか持ち込めません。"),TEXT("In Melee only, the special weapon must be a melee weapon."));
    }
    return true;
}
bool UArenaKernelSubsystem::LoadPracticeMap(int32 MapId,FSoraPracticeMap& Map,FString& Why,FString& WhyEnglish) const
{
    const auto Reject=[&Why,&WhyEnglish](const TCHAR* English)
    {
        Why=TEXT("舞台データがカーネルと一致しません。稽古を開始できません。"); WhyEnglish=English;
        UE_LOG(LogTemp,Error,TEXT("SORA practice arena data rejected: %s"),English);
        return false;
    };
    ArenaMapInfo Info{};
    if(Runtime->MapInfo(MapId,&Info)!=0||Info.wall_count>64||Info.player_height<=0||Info.player_radius<=0||Info.route_point_count<2||Info.route_point_count>32||Info.hazard_count>16)
        return Reject(TEXT("The kernel refused the arena query."));
    Map=FSoraPracticeMap(); Map.MapId=MapId;
    Map.Minimum=Millimeters(Info.min_x,Info.min_y,Info.floor_z);
    Map.Maximum=Millimeters(Info.max_x,Info.max_y,Info.floor_z);
    Map.PlayerRadius=Info.player_radius/10.f; Map.PlayerHalfHeight=Info.player_height/20.f; Map.EyeHeight=Info.eye_height/10.f;
    Map.ControlCenter=Millimeters(Info.control_x,Info.control_y,Info.floor_z); Map.ControlRadius=Info.control_radius/10.f;
    Map.RouteLength=Info.route_length/10.f; Map.PushRadius=Info.push_radius/10.f;
    Map.Checkpoints[0]=Info.checkpoint_0/10.f; Map.Checkpoints[1]=Info.checkpoint_1/10.f; Map.Checkpoints[2]=Info.checkpoint_2/10.f;
    TArray<ArenaMapWall> Walls; TArray<ArenaMapPoint> Route; TArray<ArenaMapHazard> Hazards;
    Walls.SetNumZeroed(Info.wall_count); Route.SetNumZeroed(Info.route_point_count); Hazards.SetNumZeroed(Info.hazard_count);
    for(uint32 I=0;I<Info.wall_count;++I) if(Runtime->MapWall(MapId,I,&Walls[I])!=0) return Reject(TEXT("The kernel refused a wall query."));
    for(uint32 I=0;I<Info.route_point_count;++I) if(Runtime->MapRoutePoint(MapId,I,&Route[I])!=0) return Reject(TEXT("The kernel refused a route query."));
    for(uint32 I=0;I<Info.hazard_count;++I) if(Runtime->MapHazard(MapId,I,&Hazards[I])!=0) return Reject(TEXT("The kernel refused a hazard query."));

    // The shared arena data file: every value the kernel also exports must
    // match exactly before its labels, spawns and lanes are used.
    FString Text;
    const FString Path=FPaths::ProjectDir()/TEXT("crates/arena-core/data/arena-map-v1.json");
    if(!FFileHelper::LoadFileToString(Text,*Path)) return Reject(TEXT("crates/arena-core/data/arena-map-v1.json is missing."));
    TSharedPtr<FJsonObject> Root;
    if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Root)||!Root.IsValid()) return Reject(TEXT("The arena data is not valid JSON."));
    FString Schema;
    if(!Root->TryGetStringField(TEXT("schema"),Schema)||Schema!=TEXT("sora-arena-arena-map-v1")) return Reject(TEXT("The arena data schema is not sora-arena-arena-map-v1."));
    const TSharedPtr<FJsonObject>* Player=nullptr; int32 Radius=0,Height=0,Eye=0;
    if(!Root->TryGetObjectField(TEXT("player"),Player)||!JsonField(*Player,TEXT("radius"),Radius)||!JsonField(*Player,TEXT("height"),Height)||!JsonField(*Player,TEXT("eye_height"),Eye)
        ||Radius!=Info.player_radius||Height!=Info.player_height||Eye!=Info.eye_height)
        return Reject(TEXT("The player body differs from the kernel."));
    TSharedPtr<FJsonObject> Arena;
    if(const auto* Arenas=JsonArray(Root,TEXT("arenas")))
        for(const TSharedPtr<FJsonValue>& Item:*Arenas)
        {
            int32 Id=-1;
            if(Item.IsValid()&&Item->Type==EJson::Object&&JsonField(Item->AsObject(),TEXT("id"),Id)&&Id==MapId) { Arena=Item->AsObject(); break; }
        }
    if(!Arena.IsValid()) return Reject(TEXT("The arena is missing from the data file."));
    Arena->TryGetStringField(TEXT("slug"),Map.Slug);
    const TSharedPtr<FJsonObject>* Bounds=nullptr; int32 B[4]={};
    if(!Arena->TryGetObjectField(TEXT("bounds"),Bounds)||!JsonField(*Bounds,TEXT("min_x"),B[0])||!JsonField(*Bounds,TEXT("min_y"),B[1])||!JsonField(*Bounds,TEXT("max_x"),B[2])||!JsonField(*Bounds,TEXT("max_y"),B[3])
        ||B[0]!=Info.min_x||B[1]!=Info.min_y||B[2]!=Info.max_x||B[3]!=Info.max_y)
        return Reject(TEXT("The arena bounds differ from the kernel."));
    const auto* WallItems=JsonArray(Arena,TEXT("walls"));
    if(!WallItems||WallItems->Num()!=Walls.Num()) return Reject(TEXT("The wall count differs from the kernel."));
    for(int32 I=0;I<Walls.Num();++I)
    {
        const TSharedPtr<FJsonObject> Wall=(*WallItems)[I].IsValid()?(*WallItems)[I]->AsObject():nullptr;
        int32 Index=-1,Min[3]={},Max[3]={}; FString Label;
        if(!Wall.IsValid()||!JsonField(Wall,TEXT("index"),Index)||Index!=I||!Wall->TryGetStringField(TEXT("label"),Label)
            ||!JsonPoint(Wall->TryGetField(TEXT("min")),3,Min)||!JsonPoint(Wall->TryGetField(TEXT("max")),3,Max))
            return Reject(TEXT("A wall record is malformed."));
        const ArenaMapWall& K=Walls[I];
        if(Min[0]!=K.min_x||Min[1]!=K.min_y||Min[2]!=K.min_z||Max[0]!=K.max_x||Max[1]!=K.max_y||Max[2]!=K.max_z)
            return Reject(TEXT("A wall differs from the kernel."));
        Map.Walls.Add({Millimeters(K.min_x,K.min_y,K.min_z),Millimeters(K.max_x,K.max_y,K.max_z),Label});
    }
    const TSharedPtr<FJsonObject>* Control=nullptr; int32 C[3]={};
    if(!Arena->TryGetObjectField(TEXT("control"),Control)||!JsonField(*Control,TEXT("x"),C[0])||!JsonField(*Control,TEXT("y"),C[1])||!JsonField(*Control,TEXT("radius"),C[2])
        ||C[0]!=Info.control_x||C[1]!=Info.control_y||C[2]!=Info.control_radius)
        return Reject(TEXT("The Control circle differs from the kernel."));
    const TSharedPtr<FJsonObject>* Payload=nullptr; int32 Length=0,Push=0,Checkpoint[3]={};
    const TArray<TSharedPtr<FJsonValue>>* Checkpoints=nullptr;
    if(!Arena->TryGetObjectField(TEXT("payload"),Payload)||!JsonField(*Payload,TEXT("length"),Length)||!JsonField(*Payload,TEXT("push_radius"),Push)
        ||!(*Payload)->TryGetArrayField(TEXT("checkpoints"),Checkpoints)||Checkpoints->Num()!=3
        ||!JsonInt((*Checkpoints)[0],Checkpoint[0])||!JsonInt((*Checkpoints)[1],Checkpoint[1])||!JsonInt((*Checkpoints)[2],Checkpoint[2])
        ||Length!=Info.route_length||Push!=Info.push_radius||Checkpoint[0]!=Info.checkpoint_0||Checkpoint[1]!=Info.checkpoint_1||Checkpoint[2]!=Info.checkpoint_2)
        return Reject(TEXT("The payload route differs from the kernel."));
    const auto* RouteItems=JsonArray(*Payload,TEXT("route"));
    if(!RouteItems||RouteItems->Num()!=Route.Num()) return Reject(TEXT("The payload route length differs from the kernel."));
    for(int32 I=0;I<Route.Num();++I)
    {
        int32 P[2]={};
        if(!JsonPoint((*RouteItems)[I],2,P)||P[0]!=Route[I].x||P[1]!=Route[I].y) return Reject(TEXT("A payload route point differs from the kernel."));
        Map.Route.Add(Millimeters(P[0],P[1],Info.floor_z));
    }
    const auto* HazardItems=JsonArray(Arena,TEXT("hazards"));
    if(!HazardItems||HazardItems->Num()!=Hazards.Num()) return Reject(TEXT("The hazard count differs from the kernel."));
    for(int32 I=0;I<Hazards.Num();++I)
    {
        const TSharedPtr<FJsonObject> Hazard=(*HazardItems)[I].IsValid()?(*HazardItems)[I]->AsObject():nullptr;
        int32 Index=-1,Kind=0,Damage=0,Period=0,Min[3]={},Max[3]={}; FString Label;
        const ArenaMapHazard& K=Hazards[I];
        if(!Hazard.IsValid()||!JsonField(Hazard,TEXT("index"),Index)||Index!=I||!JsonField(Hazard,TEXT("kind_id"),Kind)||!JsonField(Hazard,TEXT("damage"),Damage)
            ||!JsonField(Hazard,TEXT("period"),Period)||!JsonPoint(Hazard->TryGetField(TEXT("min")),3,Min)||!JsonPoint(Hazard->TryGetField(TEXT("max")),3,Max)
            ||!Hazard->TryGetStringField(TEXT("label"),Label)
            ||static_cast<uint32>(Kind)!=K.kind||Damage!=K.damage||static_cast<uint32>(Period)!=K.period
            ||Min[0]!=K.min_x||Min[1]!=K.min_y||Min[2]!=K.min_z||Max[0]!=K.max_x||Max[1]!=K.max_y||Max[2]!=K.max_z)
            return Reject(TEXT("A hazard differs from the kernel."));
        FSoraPracticeHazard Out; Out.Kind=Kind; Out.Damage=Damage; Out.Period=Period; Out.Label=Label;
        Out.Minimum=Millimeters(K.min_x,K.min_y,K.min_z); Out.Maximum=Millimeters(K.max_x,K.max_y,K.max_z);
        Map.Hazards.Add(Out);
    }
    // Presentation-only data: spawn pads and the bots' lanes.
    const TSharedPtr<FJsonObject>* Spawns=nullptr;
    if(!Arena->TryGetObjectField(TEXT("spawns"),Spawns)) return Reject(TEXT("The arena has no spawns."));
    const TCHAR* SpawnSets[3]={TEXT("team0"),TEXT("team1"),TEXT("ffa")};
    for(int32 Set=0;Set<3;++Set)
    {
        const auto* Items=JsonArray(*Spawns,SpawnSets[Set]);
        if(!Items||Items->IsEmpty()) return Reject(TEXT("A spawn set is missing."));
        TArray<FSoraPracticeSpawn>& Out=Set<2?Map.TeamSpawns[Set]:Map.FreeForAllSpawns;
        for(const TSharedPtr<FJsonValue>& Item:*Items)
        {
            const TSharedPtr<FJsonObject> Spawn=Item.IsValid()&&Item->Type==EJson::Object?Item->AsObject():nullptr;
            int32 X=0,Y=0,Yaw=0;
            if(!JsonField(Spawn,TEXT("x"),X)||!JsonField(Spawn,TEXT("y"),Y)||!JsonField(Spawn,TEXT("yaw"),Yaw)||Yaw<0||Yaw>65535||!FMath::IsWithinInclusive(X,Info.min_x,Info.max_x)||!FMath::IsWithinInclusive(Y,Info.min_y,Info.max_y))
                return Reject(TEXT("A spawn record is malformed."));
            Out.Add({Millimeters(X,Y,Info.floor_z),Yaw*360.f/65536.f});
        }
    }
    if(const auto* Lanes=JsonArray(Arena,TEXT("lanes")))
        for(const TSharedPtr<FJsonValue>& Item:*Lanes)
        {
            const TSharedPtr<FJsonObject> Lane=Item.IsValid()&&Item->Type==EJson::Object?Item->AsObject():nullptr;
            const auto* Points=JsonArray(Lane,TEXT("points"));
            FSoraPracticeLane Out;
            if(!Points||!Lane->TryGetStringField(TEXT("name"),Out.Name)) return Reject(TEXT("A lane record is malformed."));
            for(const TSharedPtr<FJsonValue>& Point:*Points)
            {
                int32 P[2]={};
                if(!JsonPoint(Point,2,P)) return Reject(TEXT("A lane point is malformed."));
                Out.Points.Add(Millimeters(P[0],P[1],Info.floor_z));
            }
            Map.Lanes.Add(MoveTemp(Out));
        }
    return true;
}
bool UArenaKernelSubsystem::StartPractice(const FSoraPracticeConfig& Config)
{
    StopPractice(); PracticeError.Empty(); PracticeErrorEnglish.Empty();
    FString Why,WhyEnglish;
    if(!ValidatePractice(Config,&Why,&WhyEnglish)) { PracticeError=Why; PracticeErrorEnglish=WhyEnglish; return false; }
    FSoraPracticeMap Map;
    if(!LoadPracticeMap(Config.MapId,Map,Why,WhyEnglish)) { PracticeError=Why; PracticeErrorEnglish=WhyEnglish; return false; }
    PracticeMap=MoveTemp(Map); PracticeConfig=Config;
    ArenaConfig Arena{}; Arena.abi_version=AbiVersion; Arena.mode=Config.Mode; Arena.map_id=Config.MapId;
    Arena.max_ticks=SoraPractice::MatchTicks; Arena.base_bond=0; Arena.player_count=Config.PlayerCount; Arena.offline=1;
    TArray<ArenaParticipant> Roster;
    BuildRoster(Config,Roster);
    Runtime->Practice=Runtime->Create(&Arena,Roster.GetData(),Roster.Num());
    if(!Runtime->Practice) return Refuse(TEXT("Rust カーネルが稽古の作成を拒否しました。"),TEXT("The Rust kernel refused to create the practice match."));
    if(!RefreshPractice()) { const FString Japanese=PracticeError,English=PracticeErrorEnglish; StopPractice(); PracticeError=Japanese; PracticeErrorEnglish=English; return false; }
    return true;
}
bool UArenaKernelSubsystem::PracticeBotInput(int32 Slot,FSoraPracticeInput& Out) const
{
    if(!PracticeActive()||!PracticePlayers.IsValidIndex(Slot)) return false;
    ArenaInput In{};
    if(Runtime->BotInput(Runtime->Practice,Slot,PracticeConfig.Difficulty,&In)!=0||In.slot!=static_cast<uint32>(Slot)) return false;
    Out=FromArena(In);
    return true;
}
bool UArenaKernelSubsystem::StepPractice(const FSoraPracticeInput& Local)
{
    if(!PracticeActive()||PracticeTerminal) return false;
    if(StepOnce(Local)) return true;
    // Fail closed: a refused tick ends the session, so nothing can step on
    // from a state that was not verified; the reason outlives the handle.
    const FString Japanese=PracticeError,English=PracticeErrorEnglish;
    StopPractice(); PracticeError=Japanese; PracticeErrorEnglish=English;
    return false;
}
bool UArenaKernelSubsystem::StepOnce(const FSoraPracticeInput& Local)
{
    const int32 Count=PracticePlayers.Num();
    TArray<ArenaInput,TInlineAllocator<12>> Inputs; Inputs.SetNumZeroed(Count);
    for(int32 Slot=0;Slot<Count;++Slot) Inputs[Slot].slot=Slot;
    Inputs[0].buttons=Local.Buttons; Inputs[0].move_x=Local.Forward; Inputs[0].move_y=Local.Right; Inputs[0].yaw=Local.Yaw; Inputs[0].pitch=Local.Pitch;
    // Every other slot is a Rust practice bot (crates/arena-bots): integer,
    // deterministic, planned from the same kernel state on every platform.
    for(int32 Slot=bPracticeAutopilot?0:1;Slot<Count;++Slot)
        if(Runtime->BotInput(Runtime->Practice,Slot,PracticeConfig.Difficulty,&Inputs[Slot])!=0)
            return Refuse(TEXT("稽古の相手の入力を作成できません。処理を停止しました。"),TEXT("A practice bot could not plan its input. Simulation stopped."));
    if(Runtime->Step(Runtime->Practice,Inputs.GetData(),Count)!=0)
        return Refuse(TEXT("稽古の入力が拒否されました。処理を停止しました。"),TEXT("The kernel rejected the practice input. Simulation stopped."));
    return RefreshPractice();
}
bool UArenaKernelSubsystem::RefreshPractice()
{
    ArenaSnapshot State{};
    // Practice is zero-stake: any deposit, balance or earning stops it.
    if(Runtime->Snapshot(Runtime->Practice,&State)!=0||State.abi_version!=ExpectedKernelAbi||State.player_count!=static_cast<uint32>(PracticeConfig.PlayerCount)
        ||State.deposited||State.remaining||State.earnings||State.deposited!=State.remaining+State.earnings)
        return Refuse(TEXT("無入金の稽古状態を検証できません。処理を停止しました。"),TEXT("The zero-stake practice state failed verification. Simulation stopped."));
    PracticeTick=State.tick; PracticeTerminal=State.terminal!=0;
    PracticeDeposited=State.deposited; PracticeRemaining=State.remaining; PracticeEarnings=State.earnings;
    PracticePlayers.Reset(); PracticeEvents.Reset(); PracticeProjectiles.Reset(); PracticeEntities.Reset();
    for(uint32 I=0;I<State.player_count;++I)
    {
        ArenaPlayerSnapshot P{}; ArenaPlayerPresentation Visual{};
        if(Runtime->Player(Runtime->Practice,I,&P)!=0||Runtime->Presentation(Runtime->Practice,I,&Visual)!=0||P.initial_bond||P.remaining_bond||P.earnings||P.exhausted
            ||Visual.charge_ticks_required>600||Visual.charge_ticks_current>Visual.charge_ticks_required||P.team>1)
            return Refuse(TEXT("稽古の参加者状態を検証できません。"),TEXT("A practice participant's state failed verification."));
        FSoraPracticePlayer Player; Player.Feet=Millimeters(P.x,P.y,P.z); Player.Slot=P.slot; Player.Team=P.team; Player.ClassId=P.class_id; Player.WeaponId=P.weapon_id;
        Player.Aim=FRotator(Visual.pitch*90.f/16384.f,Visual.yaw*360.f/65536.f,0);
        Player.Health=P.health; Player.MaxHealth=Visual.max_health; Player.Stamina=P.stamina; Player.Cooldown=Visual.cooldown_ticks;
        Player.Ammo=Visual.ammo; Player.Magazine=Visual.magazine; Player.ReloadTicks=Visual.reload_ticks;
        Player.ChargeTicks=Visual.charge_ticks_current; Player.ChargeRequired=Visual.charge_ticks_required;
        Player.SpawnProtectionTicks=Visual.spawn_protection_ticks; Player.GuardTicks=Visual.guard_ticks; Player.Guarding=Visual.guarding!=0;
        Player.StanceTicks=Visual.stance_ticks; Player.MarkedTicks=Visual.marked_ticks;
        Player.AbilityCooldown=Visual.ability_cooldown_ticks; Player.AbilityCooldownTotal=FMath::Max(1,static_cast<int32>(Visual.ability_cooldown_total));
        Player.PendingClass=Slot32(Visual.pending_class); Player.PendingWeapon=Slot32(Visual.pending_weapon); Player.AdmittedSpecial=Slot32(Visual.admitted_special);
        Player.InitialBond=P.initial_bond; Player.RemainingBond=P.remaining_bond; Player.Earnings=P.earnings;
        Player.RespawnTicks=P.respawn_ticks; Player.Alive=P.alive!=0; Player.Exhausted=P.exhausted!=0; Player.Kills=P.kills; Player.Deaths=P.deaths;
        PracticePlayers.Add(Player);
    }
    for(uint32 I=0;I<State.event_count;++I)
    {
        ArenaEvent E{};
        if(Runtime->Event(Runtime->Practice,I,&E)!=0) return Refuse(TEXT("稽古の出来事を読み込めません。"),TEXT("A practice event could not be read."));
        FSoraPracticeEvent Event; Event.Kind=E.kind; Event.Actor=Slot32(E.actor_slot); Event.Target=Slot32(E.target_slot); Event.WeaponId=Slot32(E.weapon_id);
        Event.Value=E.value; Event.EntityId=E.entity_id; Event.EntityKind=E.entity_kind; Event.Detail=E.detail;
        Event.From=Millimeters(E.x,E.y,E.z); Event.To=Event.From;
        if(E.kind==ARENA_EVENT_SHOT&&PracticePlayers.IsValidIndex(Event.Actor))
        {
            ArenaWeaponSpec Spec{};
            if(Runtime->WeaponSpec(E.weapon_id,&Spec)!=0) return Refuse(TEXT("射撃の参照データを読み込めません。"),TEXT("A shot's weapon data could not be read."));
            Event.WeaponKind=Spec.kind;
            Event.To+=PracticePlayers[Event.Actor].Aim.Vector()*(Spec.range_mm/10.f);
        }
        PracticeEvents.Add(Event);
    }
    uint32 Count=0;
    if(Runtime->ProjectileCount(Runtime->Practice,&Count)!=0||Count>MaxProjectiles) return Refuse(TEXT("投射物の状態を読み込めません。"),TEXT("The projectile state could not be read."));
    for(uint32 I=0;I<Count;++I)
    {
        ArenaProjectileSnapshot P{};
        if(Runtime->Projectile(Runtime->Practice,I,&P)!=0) return Refuse(TEXT("投射物の位置を読み込めません。"),TEXT("A projectile could not be read."));
        FSoraPracticeProjectile Projectile; Projectile.Id=P.id; Projectile.Owner=P.owner_slot; Projectile.WeaponId=P.weapon_id; Projectile.Position=Millimeters(P.x,P.y,P.z);
        PracticeProjectiles.Add(Projectile);
    }
    if(Runtime->EntityCount(Runtime->Practice,&Count)!=0||Count>MaxEntities) return Refuse(TEXT("技の設置物を読み込めません。"),TEXT("The ability entities could not be read."));
    for(uint32 I=0;I<Count;++I)
    {
        ArenaEntitySnapshot E{};
        if(Runtime->Entity(Runtime->Practice,I,&E)!=0||E.kind<ARENA_ENTITY_DECOY||E.kind>ARENA_ENTITY_WARD||E.owner_slot>=State.player_count||E.lifetime==0)
            return Refuse(TEXT("技の設置物の状態が不正です。"),TEXT("An ability entity failed verification."));
        FSoraPracticeEntity Entity; Entity.Id=E.id; Entity.Kind=E.kind; Entity.Owner=E.owner_slot; Entity.Team=E.team;
        Entity.Position=Millimeters(E.x,E.y,E.z); Entity.Extent=Millimeters(E.half_x,E.half_y,E.height); Entity.Yaw=E.yaw*360.f/65536.f;
        Entity.Health=E.health; Entity.MaxHealth=E.max_health; Entity.Age=E.age; Entity.Lifetime=E.lifetime;
        PracticeEntities.Add(Entity);
    }
    ArenaObjectiveSnapshot O{};
    if(Runtime->Objective(Runtime->Practice,&O)!=0||O.mode!=static_cast<uint32>(PracticeConfig.Mode)||O.winner_kind>ARENA_WINNER_DRAW||(PracticeTerminal!=(O.winner_kind!=ARENA_WINNER_NONE)))
        return Refuse(TEXT("目標の状態を検証できません。"),TEXT("The objective state failed verification."));
    FSoraPracticeObjective& Objective=PracticeObjective;
    Objective.Mode=O.mode; Objective.UnlockTick=O.unlock_tick; Objective.Score[0]=O.score_0; Objective.Score[1]=O.score_1; Objective.ScoreTarget=O.score_target;
    Objective.ControlOwner=Slot32(O.control_owner); Objective.ControlProgress=O.control_progress; Objective.ControlCapture=FMath::Max(1,O.control_capture);
    Objective.ControlCount[0]=O.control_team_0; Objective.ControlCount[1]=O.control_team_1; Objective.Contested=O.contested!=0; Objective.Overtime=O.overtime!=0;
    Objective.PayloadProgress=O.payload_progress/10.f; Objective.PayloadLength=O.payload_length/10.f; Objective.PayloadCheckpoints=O.payload_checkpoints;
    Objective.PayloadIdle=O.payload_idle; Objective.PayloadRollbackDelay=O.payload_rollback_delay;
    Objective.PayloadAttackers=O.payload_attackers; Objective.PayloadDefenders=O.payload_defenders;
    Objective.PayloadPosition=Millimeters(O.payload_x,O.payload_y,O.payload_z);
    Objective.WinnerKind=O.winner_kind; Objective.WinnerValue=O.winner_value;
    if(PracticeTick%60==0||PracticeTerminal)
    {
        uint8 Digest[32]{};
        if(Runtime->Hash(Runtime->Practice,Digest,32)!=0) return Refuse(TEXT("状態ハッシュを読み込めません。"),TEXT("The state hash could not be read."));
        PracticeHash=BytesToHex(Digest,32);
    }
    return true;
}
void UArenaKernelSubsystem::Deinitialize()
{
    StopPractice(); delete Runtime; Runtime=nullptr;
    if(Library) { FPlatformProcess::FreeDllHandle(Library); Library=nullptr; }
    Available=false; Super::Deinitialize();
}
