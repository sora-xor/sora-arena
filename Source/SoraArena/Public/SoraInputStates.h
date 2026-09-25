#pragma once
#include "CoreMinimal.h"

// The game states in which each input action may act. ASoraPlayerCharacter binds
// every action press through this table and ignores a press outside its states.
// scripts/unreal/check_input_conflicts.py reads the same rows together with
// Config/DefaultInput.ini and fails when two actions that share a key can act
// in one state. Keep one {TEXT("Action"), States} row per line.
namespace SoraInput
{
enum EState : uint8
{
    Menu = 1 << 0,     // title or pause menu; the world is paused
    Confirm = 1 << 1,  // menu showing the New Campaign confirmation
    Card = 1 << 2,     // chapter title card, before dialogue and the round timer
    Play = 1 << 3,     // live combat
    Result = 1 << 4,   // defeat, chapter-complete or practice-complete screen
};
constexpr uint8 Always = Menu | Confirm | Card | Play | Result;

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
    {TEXT("Crouch"), Play},
    {TEXT("Sheathe"), Play},
    {TEXT("Block"), Play},
    {TEXT("Ability"), Play},
    // Practice picks its loadout with 1/2/3 in the menu; campaign play equips.
    {TEXT("WeaponOne"), Menu | Play},
    {TEXT("WeaponTwo"), Menu | Play},
    {TEXT("WeaponThree"), Menu | Play},
    {TEXT("WeaponFour"), Play},
    {TEXT("WeaponFive"), Play},
    {TEXT("WeaponSix"), Play},
    {TEXT("CampaignWeaponNext"), Play},
    // Esc/Start opens and closes the menu and withdraws a pending confirmation.
    {TEXT("Menu"), Always},
    // Enter starts from the menu, skips the chapter card and continues a result.
    {TEXT("Enter"), Menu | Card | Result},
    {TEXT("Map"), Menu},
    // The first press only asks; a second press erases the saved campaign.
    {TEXT("NewCampaign"), Menu | Confirm},
    {TEXT("ReturnCampaign"), Menu},
    {TEXT("DeterministicPractice"), Menu},
    {TEXT("ClassOne"), Menu},
    {TEXT("ClassTwo"), Menu},
    {TEXT("ClassThree"), Menu},
    {TEXT("ClassFour"), Menu},
    {TEXT("ClassFive"), Menu},
    {TEXT("ClassSix"), Menu},
    {TEXT("ClassPrevious"), Menu},
    {TEXT("ClassNext"), Menu},
    {TEXT("Subtitles"), Always},
    {TEXT("PairWallet"), Menu},
    {TEXT("OpenWallet"), Menu},
    {TEXT("DisconnectWallet"), Menu},
};

// An action without a row has no states, so it can never act.
inline uint8 StatesFor(const TCHAR* Name)
{
    for (const FAction& Action : Actions)
        if (FCString::Strcmp(Action.Name, Name) == 0)
            return Action.States;
    return 0;
}
}
