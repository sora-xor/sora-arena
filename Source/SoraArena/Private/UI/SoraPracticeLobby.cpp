#include "SoraPracticeLobby.h"
#include "SoraCatalog.h"

TArray<int32> SoraPracticeLobby::SpecialOptions(int32 Mode, int32 ClassId)
{
    TArray<int32> Options = {INDEX_NONE};
    const FSoraCatalog& Catalog = FSoraCatalog::Get();
    if (!Catalog.IsReady() || ClassId < 0 || ClassId >= ClassCount)
        return Options;
    for (const int32 WeaponId : Catalog.Class(ClassId).Weapons)
    {
        const FSoraWeapon& Weapon = Catalog.Weapon(WeaponId);
        if (Weapon.Special && Weapon.ClassId == ClassId && (Mode != Melee || Weapon.Kind == TEXT("melee")))
            Options.Add(WeaponId);
    }
    return Options;
}

bool SoraPracticeLobby::IsValid(const FSoraPracticeLobbySelection& Selection, FText* Why)
{
    const auto Reject = [Why](const FText& Reason)
    {
        if (Why)
            *Why = Reason;
        return false;
    };
    if (!FSoraCatalog::Get().IsReady())
        return Reject(NSLOCTEXT("SoraArena.Menu", "Lobby.Invalid.Catalog", "内容の一覧を読み込めていない"));
    if (Selection.Mode < 0 || Selection.Mode >= ModeCount)
        return Reject(NSLOCTEXT("SoraArena.Menu", "Lobby.Invalid.Mode", "形式が範囲外"));
    if (Selection.PlayerCount < MinPlayers(Selection.Mode) || Selection.PlayerCount > MaxPlayers(Selection.Mode) ||
        (Selection.PlayerCount - MinPlayers(Selection.Mode)) % PlayerStep(Selection.Mode) != 0)
        return Reject(NSLOCTEXT("SoraArena.Menu", "Lobby.Invalid.Players", "人数が形式に合わない"));
    if (Selection.MapId < 0 || Selection.MapId >= MapCount || Selection.MapId >= FSoraCatalog::Get().Maps.Num())
        return Reject(NSLOCTEXT("SoraArena.Menu", "Lobby.Invalid.Map", "舞台が範囲外"));
    if (Selection.ClassId < 0 || Selection.ClassId >= ClassCount || Selection.ClassId >= FSoraCatalog::Get().Classes.Num())
        return Reject(NSLOCTEXT("SoraArena.Menu", "Lobby.Invalid.Class", "流儀が範囲外"));
    if (!SpecialOptions(Selection.Mode, Selection.ClassId).Contains(Selection.SpecialWeaponId))
        return Reject(NSLOCTEXT("SoraArena.Menu", "Lobby.Invalid.Special", "特殊武器がこの流儀とこの形式のものではない"));
    if (Selection.Difficulty < 0 || Selection.Difficulty >= DifficultyCount)
        return Reject(NSLOCTEXT("SoraArena.Menu", "Lobby.Invalid.Difficulty", "難易度が範囲外"));
    return true;
}
