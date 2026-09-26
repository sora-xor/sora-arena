#include "HUD/SoraPracticeText.h"
#include "ArenaKernelSubsystem.h"
#include "SoraCatalog.h"
#include "SoraPracticeDirector.h"

namespace SoraPracticeText
{
FLine ModeName(int32 Mode)
{
    switch(Mode)
    {
    case SoraPractice::Control: return {TEXT("拠点制圧"),TEXT("Control")};
    case SoraPractice::Payload: return {TEXT("護送"),TEXT("Payload")};
    case SoraPractice::Melee: return {TEXT("近接のみ"),TEXT("Melee only")};
    default: return {TEXT("乱戦"),TEXT("Free-for-all")};
    }
}
FLine SideName(int32 Team)
{
    return Team==0?FLine{TEXT("空紋一揆"),TEXT("The Sora League")}:FLine{TEXT("恒星信用院"),TEXT("The Stellar Credit House")};
}
FLine Relative(int32 Team)
{
    return Team==0?FLine{TEXT("味方"),TEXT("Allies")}:FLine{TEXT("敵"),TEXT("Enemies")};
}
FLine Participant(const UArenaKernelSubsystem& Kernel,int32 Slot)
{
    if(Slot==0) return {TEXT("あなた"),TEXT("You")};
    if(!Kernel.PracticePlayers.IsValidIndex(Slot)) return {TEXT("—"),TEXT("—")};
    const FSoraClass& Class=FSoraCatalog::Get().Class(Kernel.PracticePlayers[Slot].ClassId);
    return {FString::Printf(TEXT("%s %d"),*Class.Name,Slot),FString::Printf(TEXT("%s %d"),*Class.NameEnglish,Slot)};
}
FLine SeatSide(const FSoraPracticePlayer& Player,int32 Slot,bool bTeams)
{
    if(bTeams) return SideName(Player.Team);
    return Slot==0?SideName(0):FLine{TEXT("単騎"),TEXT("Lone blade")};
}
FLine SeatStatus(const FSoraPracticePlayer& Player)
{
    if(Player.Alive) return {TEXT("健在"),TEXT("Standing")};
    return {FString::Printf(TEXT("復帰まで %.1f 秒"),Player.RespawnTicks/60.f),FString::Printf(TEXT("Back in %.1f s"),Player.RespawnTicks/60.f)};
}
FLine FeedLine(const UArenaKernelSubsystem& Kernel,const FSoraPracticeFeedEntry& Entry)
{
    const FLine Target=Participant(Kernel,Entry.Target);
    switch(Entry.Kind)
    {
    case FSoraPracticeFeedEntry::Kill:
    {
        const FLine Actor=Participant(Kernel,Entry.Actor);
        if(Entry.WeaponId<0) return {FString::Printf(TEXT("%s ─→ %s"),*Actor.Japanese,*Target.Japanese),FString::Printf(TEXT("%s ─→ %s"),*Actor.English,*Target.English)};
        const FSoraWeapon& Weapon=FSoraCatalog::Get().Weapon(Entry.WeaponId);
        return {FString::Printf(TEXT("%s ─%s→ %s"),*Actor.Japanese,*Weapon.Name,*Target.Japanese),
            FString::Printf(TEXT("%s ─%s→ %s"),*Actor.English,*Weapon.NameEnglish,*Target.English)};
    }
    case FSoraPracticeFeedEntry::Hazard:
        return {FString::Printf(TEXT("%s は火と罠に倒れた"),*Target.Japanese),FString::Printf(TEXT("%s fell to a hazard"),*Target.English)};
    case FSoraPracticeFeedEntry::Fall:
        return {FString::Printf(TEXT("%s 自滅"),*Target.Japanese),FString::Printf(TEXT("%s fell"),*Target.English)};
    case FSoraPracticeFeedEntry::Captured:
    {
        const FLine Side=Relative(Entry.Detail);
        return {FString::Printf(TEXT("%sが拠点を奪った"),*Side.Japanese),FString::Printf(TEXT("%s took the point"),*Side.English)};
    }
    case FSoraPracticeFeedEntry::Overtime:
        return {TEXT("延長戦"),TEXT("Overtime")};
    case FSoraPracticeFeedEntry::Checkpoint:
        return {FString::Printf(TEXT("荷車が関所 %d を越えた"),Entry.Detail+1),FString::Printf(TEXT("The cart passed checkpoint %d"),Entry.Detail+1)};
    case FSoraPracticeFeedEntry::Winner:
    default:
        return {TEXT("決着"),TEXT("Decided")};
    }
}
FLine LoadoutCell(const USoraPracticeDirector& Director,int32 ClassId,int32 LoadoutIndex)
{
    const FSoraWeapon& Weapon=FSoraCatalog::Get().Weapon(FMath::Max(0,USoraPracticeDirector::LoadoutWeapon(ClassId,LoadoutIndex)));
    if(Director.CanSelectLoadout(ClassId,LoadoutIndex)) return {Weapon.Name,Weapon.NameEnglish};
    // combat-rules §10: a special only when admitted, and only blades in Melee only.
    if(LoadoutIndex==2) return {FString::Printf(TEXT("%s（未承認）"),*Weapon.Name),FString::Printf(TEXT("%s (not admitted)"),*Weapon.NameEnglish)};
    return {FString::Printf(TEXT("%s（近接のみでは不可）"),*Weapon.Name),FString::Printf(TEXT("%s (not in Melee only)"),*Weapon.NameEnglish)};
}
TArray<int32> TableOrder(const TArray<FSoraPracticePlayer>& Players,bool bTeams)
{
    TArray<int32> Order;
    for(int32 Slot=0;Slot<Players.Num();++Slot) Order.Add(Slot);
    Order.Sort([&Players,bTeams](int32 A,int32 B)
    {
        const FSoraPracticePlayer& P=Players[A]; const FSoraPracticePlayer& Q=Players[B];
        if(bTeams&&P.Team!=Q.Team) return P.Team<Q.Team;
        return P.Kills!=Q.Kills?P.Kills>Q.Kills:P.Deaths!=Q.Deaths?P.Deaths<Q.Deaths:A<B;
    });
    return Order;
}
}
