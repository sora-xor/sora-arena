#pragma once
#include "CoreMinimal.h"
class UArenaKernelSubsystem;
class USoraPracticeDirector;
struct FSoraPracticeFeedEntry;
struct FSoraPracticePlayer;

// The practice lines a player reads, each in Japanese with its English
// subtitle. The practice HUD, the director's notices and objective line and
// the results draw from here, and automation checks that no line lacks
// either language. Faction names follow the story bible (§5); mode names
// follow the practice lobby.
namespace SoraPracticeText
{
struct FLine
{
    FString Japanese;
    FString English;
};
// 乱戦 Free-for-all, 拠点制圧 Control, 護送 Payload, 近接のみ Melee only.
FLine ModeName(int32 Mode);
// Team 0 is 空紋一揆, the Sora League; team 1 恒星信用院, the Stellar Credit House.
FLine SideName(int32 Team);
// The player's side and the other one, as the HUD addresses them.
FLine Relative(int32 Team);
// あなた, You, for slot 0; otherwise the seat's class and slot.
FLine Participant(const UArenaKernelSubsystem& Kernel, int32 Slot);
// A seat's side in the tables: its team, or in free-for-all and Melee only
// the League for the player and a lone blade for everyone else.
FLine SeatSide(const FSoraPracticePlayer& Player, int32 Slot, bool bTeams);
// Standing, or the time until the kernel returns the seat.
FLine SeatStatus(const FSoraPracticePlayer& Player);
// One feed line: a kill names the killer, the weapon held and the victim.
FLine FeedLine(const UArenaKernelSubsystem& Kernel, const FSoraPracticeFeedEntry& Entry);
// A respawn weapon choice: the weapon, and why it cannot be chosen.
FLine LoadoutCell(const USoraPracticeDirector& Director, int32 ClassId, int32 LoadoutIndex);
// Seats in table order: by team in the team modes, then most kills, fewest
// deaths and slot.
TArray<int32> TableOrder(const TArray<FSoraPracticePlayer>& Players, bool bTeams);
}
