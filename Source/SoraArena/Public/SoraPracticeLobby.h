#pragma once
#include "CoreMinimal.h"

// The practice lobby's choice. The front end builds it and hands it to
// ASoraGameMode::StartPracticeFromLobby. Its fields match
// USoraPracticeDirector's FSoraPracticeConfig one for one (Mode, PlayerCount,
// MapId, ClassId, SpecialWeaponId, Difficulty), so the director takes them
// directly. Practice is offline and bonds nothing.
namespace SoraPracticeLobby
{
// Numbered as the kernel's ArenaConfig.mode.
enum EMode : int32 { FreeForAll = 0, Control = 1, Payload = 2, Melee = 3, ModeCount = 4 };
// Bot tiers, weakest first.
enum EDifficulty : int32 { Novice = 0, Standard = 1, Veteran = 2, Master = 3, DifficultyCount = 4 };
constexpr int32 MapCount = 4;
constexpr int32 ClassCount = 6;

inline bool IsTeamMode(int32 Mode) { return Mode == Control || Mode == Payload; }
// Free-for-all and Melee seat two to eight cats; the team modes seat two even
// teams, up to six against six.
inline int32 MinPlayers(int32 Mode) { return IsTeamMode(Mode) ? 4 : 2; }
inline int32 MaxPlayers(int32 Mode) { return IsTeamMode(Mode) ? 12 : 8; }
inline int32 PlayerStep(int32 Mode) { return IsTeamMode(Mode) ? 2 : 1; }
}

struct FSoraPracticeLobbySelection
{
    int32 Mode = SoraPracticeLobby::FreeForAll;
    // Every participant, the player included.
    int32 PlayerCount = 8;
    // Catalog map: Nyaagyu Estate, Lantern Ward, Silk Foundry, Debt Citadel.
    int32 MapId = 0;
    // Catalog class: Samurai, Shinobi, Teppo, Hanabi, Karakuri, Kusushi.
    int32 ClassId = 0;
    // The one special weapon admitted for the match: the class's special
    // sidegrade, or INDEX_NONE for the standard loadout. Melee admits only a
    // melee special.
    int32 SpecialWeaponId = INDEX_NONE;
    int32 Difficulty = SoraPracticeLobby::Standard;
};

namespace SoraPracticeLobby
{
// Every field in range for the loaded catalog; Why names the first problem
// (an NSLOCTEXT with its English subtitle).
SORAARENA_API bool IsValid(const FSoraPracticeLobbySelection& Selection, FText* Why = nullptr);
// The special weapons the class may bring in this mode, INDEX_NONE first.
SORAARENA_API TArray<int32> SpecialOptions(int32 Mode, int32 ClassId);
}
