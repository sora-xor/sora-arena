#pragma once
#include "CoreMinimal.h"

// The game states in which each input action may act. ASoraPlayerCharacter binds
// every action press through this table and ignores a press outside its states.
// Menus are the Slate front end (USoraFrontEnd), which takes keyboard and pad
// focus while open, so no action here acts in Menu.
// scripts/unreal/check_input_conflicts.py reads the same rows together with
// Config/DefaultInput.ini and fails when two actions that share a key can act
// in one state. Keep one {TEXT("Action"), States} row per line.
namespace SoraInput
{
// Bit 1 is unused: confirmations are front-end dialogs now. The values stay
// as they were so recorded combat traces, which log the state, still match.
enum EState : uint8
{
    Menu = 1 << 0,     // a front-end screen; it holds input and the world is paused
    Card = 1 << 2,     // chapter title card, before dialogue and the round timer
    Play = 1 << 3,     // live combat
    Result = 1 << 4,   // defeat, chapter-complete or practice-complete screen
};
struct FAction
{
    const TCHAR* Name;
    uint8 States;
};

inline constexpr FAction Actions[] = {
    {TEXT("MoveForward"), Play},
    {TEXT("MoveRight"), Play},
    {TEXT("LookYaw"), Play},
    {TEXT("LookPitch"), Play},
    {TEXT("GamepadLookYaw"), Play},
    {TEXT("GamepadLookPitch"), Play},
    {TEXT("Fire"), Play},
    {TEXT("Melee"), Play},
    {TEXT("Jump"), Play},
    {TEXT("Sprint"), Play},
    {TEXT("Reload"), Play},
    {TEXT("Interact"), Play},
    {TEXT("Block"), Play},
    {TEXT("Ability"), Play},
    // Practice takes its loadout from the lobby; campaign play equips.
    {TEXT("WeaponOne"), Play},
    {TEXT("WeaponTwo"), Play},
    {TEXT("WeaponThree"), Play},
    {TEXT("WeaponFour"), Play},
    {TEXT("WeaponFive"), Play},
    {TEXT("WeaponSix"), Play},
    {TEXT("CampaignWeaponNext"), Play},
    // Held in play: the practice scoreboard of every seat.
    {TEXT("Scoreboard"), Play},
    // Esc/Start opens the pause menu; the front end closes it.
    {TEXT("Menu"), Card | Play | Result},
    // Enter skips the chapter card and continues a result.
    {TEXT("Enter"), Card | Result},
    {TEXT("Subtitles"), Card | Play | Result},
};

// An action without a row has no states, so it can never act.
inline uint8 StatesFor(const TCHAR* Name)
{
    for (const FAction& Action : Actions)
        if (FCString::Strcmp(Action.Name, Name) == 0)
            return Action.States;
    return 0;
}

// The controls a player may rebind on the Controls screen, in its order. An
// entry with an Axis direction is one half of a movement axis and takes one
// keyboard key; every other entry is an action with one keyboard-or-mouse key
// and one pad button. Menu, Enter and Subtitles stay fixed, as do the axes
// the sticks and the mouse drive. check_input_conflicts.py requires every
// play-only action to be listed here and nothing that acts outside play.
struct FRemappable
{
    const TCHAR* Name;
    // +1 or -1 for a movement axis half, the mapping's Scale; 0 for an action.
    int32 Axis;
};

inline constexpr FRemappable Remappable[] = {
    {TEXT("MoveForward"), 1},
    {TEXT("MoveForward"), -1},
    {TEXT("MoveRight"), -1},
    {TEXT("MoveRight"), 1},
    {TEXT("Fire"), 0},
    {TEXT("Melee"), 0},
    {TEXT("Block"), 0},
    {TEXT("Jump"), 0},
    {TEXT("Sprint"), 0},
    {TEXT("Reload"), 0},
    {TEXT("Interact"), 0},
    {TEXT("Ability"), 0},
    {TEXT("WeaponOne"), 0},
    {TEXT("WeaponTwo"), 0},
    {TEXT("WeaponThree"), 0},
    {TEXT("WeaponFour"), 0},
    {TEXT("WeaponFive"), 0},
    {TEXT("WeaponSix"), 0},
    {TEXT("CampaignWeaponNext"), 0},
    {TEXT("Scoreboard"), 0},
};
inline constexpr int32 RemappableCount = UE_ARRAY_COUNT(Remappable);

// The Remappable entry for an action or a movement half, or INDEX_NONE.
inline int32 FindRemappable(const TCHAR* Name, int32 Axis)
{
    for (int32 Index = 0; Index < RemappableCount; ++Index)
        if (FCString::Strcmp(Remappable[Index].Name, Name) == 0 && Remappable[Index].Axis == Axis)
            return Index;
    return INDEX_NONE;
}
}
