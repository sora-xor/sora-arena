#include "ArenaKernelSubsystem.h"
#include "HAL/PlatformProcess.h"
#include "Misc/Paths.h"
#include "arena.h"

static_assert(sizeof(ArenaPlayerPresentation)==44,"Unexpected ABI 3 player presentation layout");
static_assert(offsetof(ArenaPlayerPresentation,charge_ticks_current)==36,"Unexpected ABI 3 charge offset");
static_assert(sizeof(ArenaWeaponSpec)==48,"Unexpected ABI 3 weapon layout");

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
    ArenaHandle* Practice = nullptr;
    TArray<TArray<FVector>> Routes;
};
namespace
{
constexpr uint32 ExpectedKernelAbi = 3;
FVector Millimeters(int32 X,int32 Y,int32 Z) { return FVector(X/10.0,Y/10.0,Z/10.0); }
uint16 CanonicalYaw(float Yaw) { return static_cast<uint16>(FMath::RoundToInt(FRotator::ClampAxis(Yaw)*65536.f/360.f)&65535); }
int16 CanonicalPitch(float Pitch) { return static_cast<int16>(FMath::Clamp(FMath::RoundToInt(Pitch*16384.f/90.f),-16384,16384)); }
bool ClearRoute(const FSoraPracticeMap& Map,FVector A,FVector B,float Margin)
{
    A.Z=B.Z=Map.EyeHeight;
    for(const auto& Wall:Map.Walls)
    {
        const FBox Bounds(Wall.Minimum-FVector(Margin,Margin,0),Wall.Maximum+FVector(Margin,Margin,0));
        if(FMath::LineBoxIntersection(Bounds,A,B,B-A)) return false;
    }
    return true;
}
// Small visibility graph around the reference obstacles. It proposes inputs only;
// the Rust collision solver remains the sole authority over actual movement.
TArray<FVector> Route(const FSoraPracticeMap& Map,FVector Start,FVector End)
{
    const float Margin=Map.PlayerRadius+12.f;
    TArray<FVector> Points{Start,End};
    for(const auto& Wall:Map.Walls)
        for(int32 X:{-1,1}) for(int32 Y:{-1,1})
        {
            FVector P(X<0?Wall.Minimum.X-Margin:Wall.Maximum.X+Margin,Y<0?Wall.Minimum.Y-Margin:Wall.Maximum.Y+Margin,0);
            if(P.X>Map.Minimum.X+Margin&&P.X<Map.Maximum.X-Margin&&P.Y>Map.Minimum.Y+Margin&&P.Y<Map.Maximum.Y-Margin) Points.Add(P);
        }
    TArray<float> Dist; Dist.Init(TNumericLimits<float>::Max(),Points.Num()); Dist[0]=0;
    TArray<int32> Previous; Previous.Init(INDEX_NONE,Points.Num()); TSet<int32> Visited;
    for(int32 Count=0;Count<Points.Num();++Count)
    {
        int32 Best=INDEX_NONE;
        for(int32 I=0;I<Points.Num();++I) if(!Visited.Contains(I)&&(Best==INDEX_NONE||Dist[I]<Dist[Best])) Best=I;
        if(Best==INDEX_NONE||Dist[Best]==TNumericLimits<float>::Max()||Best==1) break;
        Visited.Add(Best);
        for(int32 I=0;I<Points.Num();++I)
        {
            if(I==Best||Visited.Contains(I)||!ClearRoute(Map,Points[Best],Points[I],Map.PlayerRadius+2.f)) continue;
            const float Cost=Dist[Best]+FVector::Dist2D(Points[Best],Points[I]);
            if(Cost<Dist[I]) { Dist[I]=Cost; Previous[I]=Best; }
        }
    }
    TArray<FVector> Result;
    if(Previous[1]!=INDEX_NONE)
    {
        for(int32 I=1;I!=0&&I!=INDEX_NONE;I=Previous[I]) Result.Insert(Points[I],0);
    }
    return Result;
}
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
#undef LOAD_KERNEL
    const auto& R=*Runtime;
    if(!R.Abi||!R.Qualified||!R.Create||!R.Destroy||!R.Step||!R.Snapshot||!R.Player||!R.Hash||!R.MapInfo||!R.MapWall||!R.Presentation||!R.WeaponSpec||!R.Event||!R.ProjectileCount||!R.Projectile||R.Abi()!=ExpectedKernelAbi)
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
    PracticePlayers.Reset(); PracticeEvents.Reset(); PracticeProjectiles.Reset();
    PracticeTick=0; PracticeTerminal=false; PracticeHash.Empty();
}
bool UArenaKernelSubsystem::StartPractice(int32 ClassId,int32 WeaponSlot,int32 MapId)
{
    StopPractice(); PracticeError.Empty();
    if(!Available||!Runtime) { PracticeError=TEXT("稽古には、検証済みの実物 Rust ライブラリが必要です。"); return false; }
    if(ClassId<0||ClassId>5||WeaponSlot<0||WeaponSlot>2||MapId<0||MapId>3) { PracticeError=TEXT("稽古の設定が範囲外です。"); return false; }
    ArenaMapInfo Info{};
    if(Runtime->MapInfo(MapId,&Info)!=0||Info.wall_count>64||Info.player_height<=0||Info.player_radius<=0) { PracticeError=TEXT("参照マップを読み込めません。"); return false; }
    PracticeMap.Minimum=Millimeters(Info.min_x,Info.min_y,Info.floor_z);
    PracticeMap.Maximum=Millimeters(Info.max_x,Info.max_y,Info.floor_z);
    PracticeMap.PlayerRadius=Info.player_radius/10.f; PracticeMap.PlayerHalfHeight=Info.player_height/20.f; PracticeMap.EyeHeight=Info.eye_height/10.f;
    PracticeMap.Walls.Reset();
    for(uint32 I=0;I<Info.wall_count;++I)
    {
        ArenaMapWall Wall{};
        if(Runtime->MapWall(MapId,I,&Wall)!=0) { PracticeError=TEXT("参照マップの障害物が不正です。"); return false; }
        PracticeMap.Walls.Add({Millimeters(Wall.min_x,Wall.min_y,Wall.min_z),Millimeters(Wall.max_x,Wall.max_y,Wall.max_z)});
    }
    ArenaConfig Config{}; Config.abi_version=AbiVersion; Config.mode=0; Config.map_id=MapId; Config.max_ticks=36000; Config.player_count=6; Config.offline=1;
    ArenaParticipant Roster[6]{};
    for(uint32 I=0;I<6;++I)
    {
        auto& P=Roster[I]; P.slot=I; P.team=I%2; P.class_id=I==0?ClassId:I;
        P.weapon_id=I==0?(WeaponSlot==2?12+ClassId:2*ClassId+WeaponSlot):2*P.class_id+1;
    }
    Runtime->Practice=Runtime->Create(&Config,Roster,6);
    Runtime->Routes.SetNum(6); for(auto& Waypoints:Runtime->Routes) Waypoints.Reset();
    if(!Runtime->Practice) { PracticeError=TEXT("Rust カーネルが稽古の作成を拒否しました。"); return false; }
    if(!RefreshPractice()) { StopPractice(); return false; }
    return true;
}
bool UArenaKernelSubsystem::StepPractice(const FSoraPracticeInput& Local)
{
    if(!PracticeActive()||PracticeTerminal) return false;
    ArenaInput Inputs[6]{};
    Inputs[0].slot=0; Inputs[0].buttons=Local.Buttons; Inputs[0].move_x=Local.Forward; Inputs[0].move_y=Local.Right; Inputs[0].yaw=Local.Yaw; Inputs[0].pitch=Local.Pitch;
    for(int32 Slot=1;Slot<PracticePlayers.Num();++Slot)
    {
        auto& Input=Inputs[Slot]; Input.slot=Slot;
        const auto& Bot=PracticePlayers[Slot]; if(!Bot.Alive) continue;
        int32 Target=INDEX_NONE; float Best=TNumericLimits<float>::Max();
        for(int32 I=0;I<PracticePlayers.Num();++I) if(I!=Slot&&PracticePlayers[I].Alive)
        {
            const float D=FVector::DistSquared2D(Bot.Feet,PracticePlayers[I].Feet);
            if(D<Best) { Best=D; Target=I; }
        }
        if(Target==INDEX_NONE) continue;
        const auto& Other=PracticePlayers[Target];
        const FVector Eye=Bot.Feet+FVector(0,0,PracticeMap.EyeHeight);
        const FVector AimAt=Other.Feet+FVector(0,0,PracticeMap.PlayerHalfHeight);
        FRotator Aim=(AimAt-Eye).Rotation();
        // Deterministic cadence and bounded aim error make these practice opponents beatable.
        Aim.Yaw+=static_cast<int32>((PracticeTick/45+Slot)%5)-2;
        Input.yaw=CanonicalYaw(Aim.Yaw); Input.pitch=CanonicalPitch(Aim.Pitch);
        const bool Visible=ClearRoute(PracticeMap,Bot.Feet,Other.Feet,0);
        ArenaWeaponSpec Weapon{};
        if(Runtime->WeaponSpec(Bot.WeaponId,&Weapon)!=0) { PracticeError=TEXT("武器の参照データを読み込めません。"); return false; }
        if(Visible&&Best<FMath::Square(Weapon.range_mm/10.f)&&(PracticeTick+Slot*13)%180<115) Input.buttons|=1;
        if(Bot.Magazine>0&&Bot.Ammo==0&&Bot.ReloadTicks==0) Input.buttons|=32;
        if(Best<FMath::Square(165.f)) Input.buttons|=2;
        if((PracticeTick+Slot*47)%360==0) Input.buttons|=16;
        auto& Waypoints=Runtime->Routes[Slot];
        if((PracticeTick+Slot*5)%30==0||Waypoints.IsEmpty()) Waypoints=Route(PracticeMap,Bot.Feet,Other.Feet);
        while(!Waypoints.IsEmpty()&&FVector::Dist2D(Bot.Feet,Waypoints[0])<65) Waypoints.RemoveAt(0);
        const bool Approach=!Visible||Best>FMath::Square(600.f);
        if(Approach&&!Waypoints.IsEmpty())
        {
            const FVector Direction=(Waypoints[0]-Bot.Feet).GetSafeNormal2D();
            const FVector Forward=FRotator(0,Aim.Yaw,0).Vector(),Right=FRotator(0,Aim.Yaw+90,0).Vector();
            Input.move_x=static_cast<int16>(FMath::Clamp(FMath::RoundToInt(FVector::DotProduct(Direction,Forward)*92),-127,127));
            Input.move_y=static_cast<int16>(FMath::Clamp(FMath::RoundToInt(FVector::DotProduct(Direction,Right)*92),-127,127));
        }
        else if(Visible) Input.move_y=((PracticeTick/120+Slot)%2?36:-36);
    }
    if(Runtime->Step(Runtime->Practice,Inputs,6)!=0) { PracticeError=TEXT("稽古の入力が拒否されました。処理を停止しました。"); return false; }
    return RefreshPractice();
}
bool UArenaKernelSubsystem::RefreshPractice()
{
    ArenaSnapshot State{};
    if(Runtime->Snapshot(Runtime->Practice,&State)!=0||State.abi_version!=ExpectedKernelAbi||State.player_count!=6||State.deposited||State.remaining||State.earnings)
    { PracticeError=TEXT("無入金の稽古状態を検証できません。処理を停止しました。"); return false; }
    PracticeTick=State.tick; PracticeTerminal=State.terminal!=0; PracticePlayers.Reset(); PracticeEvents.Reset(); PracticeProjectiles.Reset();
    for(uint32 I=0;I<State.player_count;++I)
    {
        ArenaPlayerSnapshot P{}; ArenaPlayerPresentation Visual{};
        if(Runtime->Player(Runtime->Practice,I,&P)!=0||Runtime->Presentation(Runtime->Practice,I,&Visual)!=0||P.initial_bond||P.remaining_bond||P.earnings||Visual.charge_ticks_required>600||Visual.charge_ticks_current>Visual.charge_ticks_required)
        { PracticeError=TEXT("稽古の参加者状態を検証できません。"); return false; }
        FSoraPracticePlayer Player; Player.Feet=Millimeters(P.x,P.y,P.z); Player.Slot=P.slot; Player.ClassId=P.class_id; Player.WeaponId=P.weapon_id;
        Player.Aim=FRotator(Visual.pitch*90.f/16384.f,Visual.yaw*360.f/65536.f,0);
        Player.Health=P.health; Player.MaxHealth=Visual.max_health; Player.Stamina=P.stamina; Player.Cooldown=Visual.cooldown_ticks;
        Player.Ammo=Visual.ammo; Player.Magazine=Visual.magazine; Player.ReloadTicks=Visual.reload_ticks;
        Player.ChargeTicks=Visual.charge_ticks_current; Player.ChargeRequired=Visual.charge_ticks_required;
        Player.RespawnTicks=P.respawn_ticks; Player.Alive=P.alive!=0; Player.Kills=P.kills; Player.Deaths=P.deaths;
        PracticePlayers.Add(Player);
    }
    for(uint32 I=0;I<State.event_count;++I)
    {
        ArenaEvent E{};
        if(Runtime->Event(Runtime->Practice,I,&E)!=0) { PracticeError=TEXT("稽古の出来事を読み込めません。"); return false; }
        FSoraPracticeEvent Event; Event.Kind=E.kind; Event.Actor=E.actor_slot==UINT32_MAX?INDEX_NONE:static_cast<int32>(E.actor_slot);
        Event.Target=E.target_slot==UINT32_MAX?INDEX_NONE:static_cast<int32>(E.target_slot); Event.WeaponId=E.weapon_id==UINT32_MAX?INDEX_NONE:static_cast<int32>(E.weapon_id);
        Event.Value=E.value; Event.From=Millimeters(E.x,E.y,E.z); Event.To=Event.From;
        if(E.kind==1&&PracticePlayers.IsValidIndex(Event.Actor))
        {
            ArenaWeaponSpec Spec{};
            if(Runtime->WeaponSpec(E.weapon_id,&Spec)!=0) { PracticeError=TEXT("射撃の参照データを読み込めません。"); return false; }
            Event.WeaponKind=Spec.kind;
            Event.To+=PracticePlayers[Event.Actor].Aim.Vector()*(Spec.range_mm/10.f);
        }
        PracticeEvents.Add(Event);
    }
    uint32 Count=0;
    if(Runtime->ProjectileCount(Runtime->Practice,&Count)!=0||Count>256) { PracticeError=TEXT("投射物の状態を読み込めません。"); return false; }
    for(uint32 I=0;I<Count;++I)
    {
        ArenaProjectileSnapshot P{};
        if(Runtime->Projectile(Runtime->Practice,I,&P)!=0) { PracticeError=TEXT("投射物の位置を読み込めません。"); return false; }
        FSoraPracticeProjectile Projectile; Projectile.Id=P.id; Projectile.Owner=P.owner_slot; Projectile.WeaponId=P.weapon_id; Projectile.Position=Millimeters(P.x,P.y,P.z);
        PracticeProjectiles.Add(Projectile);
    }
    if(PracticeTick%60==0||PracticeTerminal)
    {
        uint8 Digest[32]{};
        if(Runtime->Hash(Runtime->Practice,Digest,32)!=0) { PracticeError=TEXT("状態ハッシュを読み込めません。"); return false; }
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
