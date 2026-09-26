#include "SoraFrontEnd.h"
#include "SoraGameMode.h"
#include "SoraPlayerCharacter.h"
#include "GameFramework/InputSettings.h"
#include "InputCoreTypes.h"
#include "Kismet/GameplayStatics.h"

SoraUI::ECommand SoraUI::CommandForKey(const FKey& Key)
{
    if (Key == EKeys::Up || Key == EKeys::W || Key == EKeys::Gamepad_DPad_Up || Key == EKeys::Gamepad_LeftStick_Up)
        return ECommand::Up;
    if (Key == EKeys::Down || Key == EKeys::S || Key == EKeys::Gamepad_DPad_Down || Key == EKeys::Gamepad_LeftStick_Down)
        return ECommand::Down;
    if (Key == EKeys::Left || Key == EKeys::A || Key == EKeys::Gamepad_DPad_Left || Key == EKeys::Gamepad_LeftStick_Left ||
        Key == EKeys::Gamepad_LeftShoulder)
        return ECommand::Left;
    if (Key == EKeys::Right || Key == EKeys::D || Key == EKeys::Gamepad_DPad_Right || Key == EKeys::Gamepad_LeftStick_Right ||
        Key == EKeys::Gamepad_RightShoulder)
        return ECommand::Right;
    if (Key == EKeys::Enter || Key == EKeys::SpaceBar || Key == EKeys::Gamepad_FaceButton_Bottom)
        return ECommand::Accept;
    if (Key == EKeys::Escape || Key == EKeys::BackSpace || Key == EKeys::Gamepad_FaceButton_Right)
        return ECommand::Back;
    if (Key == EKeys::Gamepad_Special_Right)
        return ECommand::Start;
    if (Key == EKeys::F10)
        return ECommand::Subtitles;
    return ECommand::None;
}

SoraUI::EDevice SoraUI::DeviceForKey(const FKey& Key)
{
    return Key.IsGamepadKey() ? EDevice::Gamepad : EDevice::KeyboardMouse;
}

FString SoraUI::PromptKey(ECommand Command, EDevice Device)
{
    const bool bPad = Device == EDevice::Gamepad;
    switch (Command)
    {
    case ECommand::Up:
    case ECommand::Down: return TEXT("↑↓");
    case ECommand::Left:
    case ECommand::Right: return bPad ? TEXT("←→ / LB RB") : TEXT("←→");
    case ECommand::Accept: return bPad ? TEXT("A") : TEXT("Enter");
    case ECommand::Back: return bPad ? TEXT("B") : TEXT("Esc");
    case ECommand::Start: return bPad ? TEXT("Start") : TEXT("Esc");
    // The pad has no subtitle button; Settings has the switch.
    case ECommand::Subtitles: return bPad ? FString() : FString(TEXT("F10"));
    case ECommand::None: break;
    }
    return FString();
}

SoraText::FLine SoraUI::KeyLabel(const FKey& Key)
{
    if (!Key.IsValid())
        return SoraText::Same(TEXT("—"));
    struct FLabel
    {
        FKey Key;
        FText Name;
    };
    // Mouse buttons, the d-pad, the view button, arrows and the sided
    // modifiers read in Japanese.
    const FLabel Labels[] = {
        {EKeys::LeftMouseButton, NSLOCTEXT("SoraArena.Keys", "LeftMouseButton", "左クリック")},
        {EKeys::RightMouseButton, NSLOCTEXT("SoraArena.Keys", "RightMouseButton", "右クリック")},
        {EKeys::MiddleMouseButton, NSLOCTEXT("SoraArena.Keys", "MiddleMouseButton", "ホイール押し")},
        {EKeys::ThumbMouseButton, NSLOCTEXT("SoraArena.Keys", "ThumbMouseButton", "サイドボタン1")},
        {EKeys::ThumbMouseButton2, NSLOCTEXT("SoraArena.Keys", "ThumbMouseButton2", "サイドボタン2")},
        {EKeys::MouseScrollUp, NSLOCTEXT("SoraArena.Keys", "MouseScrollUp", "ホイール上")},
        {EKeys::MouseScrollDown, NSLOCTEXT("SoraArena.Keys", "MouseScrollDown", "ホイール下")},
        {EKeys::Gamepad_DPad_Up, NSLOCTEXT("SoraArena.Keys", "DPadUp", "十字↑")},
        {EKeys::Gamepad_DPad_Down, NSLOCTEXT("SoraArena.Keys", "DPadDown", "十字↓")},
        {EKeys::Gamepad_DPad_Left, NSLOCTEXT("SoraArena.Keys", "DPadLeft", "十字←")},
        {EKeys::Gamepad_DPad_Right, NSLOCTEXT("SoraArena.Keys", "DPadRight", "十字→")},
        {EKeys::Gamepad_Special_Left, NSLOCTEXT("SoraArena.Keys", "ViewButton", "ビュー")},
        {EKeys::LeftShift, NSLOCTEXT("SoraArena.Keys", "LeftShift", "左 Shift")},
        {EKeys::RightShift, NSLOCTEXT("SoraArena.Keys", "RightShift", "右 Shift")},
        {EKeys::LeftControl, NSLOCTEXT("SoraArena.Keys", "LeftControl", "左 Ctrl")},
        {EKeys::RightControl, NSLOCTEXT("SoraArena.Keys", "RightControl", "右 Ctrl")},
        {EKeys::LeftAlt, NSLOCTEXT("SoraArena.Keys", "LeftAlt", "左 Alt")},
        {EKeys::RightAlt, NSLOCTEXT("SoraArena.Keys", "RightAlt", "右 Alt")},
        {EKeys::LeftCommand, NSLOCTEXT("SoraArena.Keys", "LeftCommand", "左 Cmd")},
        {EKeys::RightCommand, NSLOCTEXT("SoraArena.Keys", "RightCommand", "右 Cmd")},
        {EKeys::Up, NSLOCTEXT("SoraArena.Keys", "Up", "↑")},
        {EKeys::Down, NSLOCTEXT("SoraArena.Keys", "Down", "↓")},
        {EKeys::Left, NSLOCTEXT("SoraArena.Keys", "Left", "←")},
        {EKeys::Right, NSLOCTEXT("SoraArena.Keys", "Right", "→")},
    };
    for (const FLabel& Label : Labels)
        if (Label.Key == Key)
            return SoraText::Line(Label.Name);
    // Key caps and the pad's lettered buttons keep the names printed on them
    // in both languages.
    struct FPrinted
    {
        FKey Key;
        const TCHAR* Name;
    };
    static const FPrinted Printed[] = {
        {EKeys::Gamepad_FaceButton_Bottom, TEXT("A")}, {EKeys::Gamepad_FaceButton_Right, TEXT("B")},
        {EKeys::Gamepad_FaceButton_Left, TEXT("X")}, {EKeys::Gamepad_FaceButton_Top, TEXT("Y")},
        {EKeys::Gamepad_LeftShoulder, TEXT("LB")}, {EKeys::Gamepad_RightShoulder, TEXT("RB")},
        {EKeys::Gamepad_LeftTrigger, TEXT("LT")}, {EKeys::Gamepad_RightTrigger, TEXT("RT")},
        {EKeys::Gamepad_LeftThumbstick, TEXT("L3")}, {EKeys::Gamepad_RightThumbstick, TEXT("R3")},
        {EKeys::Gamepad_Special_Right, TEXT("Start")}, {EKeys::SpaceBar, TEXT("Space")},
        {EKeys::Escape, TEXT("Esc")}, {EKeys::Enter, TEXT("Enter")}, {EKeys::BackSpace, TEXT("Backspace")},
        {EKeys::Zero, TEXT("0")}, {EKeys::One, TEXT("1")}, {EKeys::Two, TEXT("2")}, {EKeys::Three, TEXT("3")},
        {EKeys::Four, TEXT("4")}, {EKeys::Five, TEXT("5")}, {EKeys::Six, TEXT("6")}, {EKeys::Seven, TEXT("7")},
        {EKeys::Eight, TEXT("8")}, {EKeys::Nine, TEXT("9")},
    };
    for (const FPrinted& Cap : Printed)
        if (Cap.Key == Key)
            return SoraText::Same(Cap.Name);
    // Letters, function keys and the rest: Unreal's own short name.
    return SoraText::Same(Key.GetDisplayName(false).ToString());
}

SoraText::FLine SoraUI::ControlName(FName Name, int32 Axis)
{
    struct FControl
    {
        const TCHAR* Name;
        int32 Axis;
        FText Label;
    };
    // Every SoraInput::Remappable entry, then the fixed actions and the look
    // axes, named as a refusal would name them.
    const FControl Controls[] = {
        {TEXT("MoveForward"), 1, NSLOCTEXT("SoraArena.Controls", "Control.MoveForward", "前へ進む")},
        {TEXT("MoveForward"), -1, NSLOCTEXT("SoraArena.Controls", "Control.MoveBack", "後ろへ下がる")},
        {TEXT("MoveRight"), -1, NSLOCTEXT("SoraArena.Controls", "Control.MoveLeft", "左へ動く")},
        {TEXT("MoveRight"), 1, NSLOCTEXT("SoraArena.Controls", "Control.MoveRight", "右へ動く")},
        {TEXT("Fire"), 0, NSLOCTEXT("SoraArena.Controls", "Control.Fire", "射撃・弓を引く")},
        {TEXT("Melee"), 0, NSLOCTEXT("SoraArena.Controls", "Control.Melee", "斬撃")},
        {TEXT("Block"), 0, NSLOCTEXT("SoraArena.Controls", "Control.Block", "構え・受け")},
        {TEXT("Jump"), 0, NSLOCTEXT("SoraArena.Controls", "Control.Jump", "跳ぶ")},
        {TEXT("Sprint"), 0, NSLOCTEXT("SoraArena.Controls", "Control.Sprint", "走る")},
        {TEXT("Reload"), 0, NSLOCTEXT("SoraArena.Controls", "Control.Reload", "装填")},
        {TEXT("Interact"), 0, NSLOCTEXT("SoraArena.Controls", "Control.Interact", "調べる")},
        {TEXT("Ability"), 0, NSLOCTEXT("SoraArena.Controls", "Control.Ability", "技")},
        {TEXT("WeaponOne"), 0, NSLOCTEXT("SoraArena.Controls", "Control.WeaponOne", "主武器")},
        {TEXT("WeaponTwo"), 0, NSLOCTEXT("SoraArena.Controls", "Control.WeaponTwo", "近接武器")},
        {TEXT("WeaponThree"), 0, NSLOCTEXT("SoraArena.Controls", "Control.WeaponThree", "特殊武器")},
        {TEXT("WeaponFour"), 0, NSLOCTEXT("SoraArena.Controls", "Control.WeaponFour", "弓（物語）")},
        {TEXT("WeaponFive"), 0, NSLOCTEXT("SoraArena.Controls", "Control.WeaponFive", "槍（物語）")},
        {TEXT("WeaponSix"), 0, NSLOCTEXT("SoraArena.Controls", "Control.WeaponSix", "薙刀（物語）")},
        {TEXT("CampaignWeaponNext"), 0, NSLOCTEXT("SoraArena.Controls", "Control.CampaignWeaponNext", "次の武器（物語）")},
        {TEXT("Scoreboard"), 0, NSLOCTEXT("SoraArena.Controls", "Control.Scoreboard", "戦況表（稽古）")},
        {TEXT("Menu"), 0, NSLOCTEXT("SoraArena.Controls", "Control.Menu", "一時停止メニュー")},
        {TEXT("Enter"), 0, NSLOCTEXT("SoraArena.Controls", "Control.Enter", "決定・続ける")},
        {TEXT("Subtitles"), 0, NSLOCTEXT("SoraArena.Controls", "Control.Subtitles", "英語字幕の切り替え")},
        {TEXT("LookYaw"), 0, NSLOCTEXT("SoraArena.Controls", "Control.Look", "視点")},
        {TEXT("LookPitch"), 0, NSLOCTEXT("SoraArena.Controls", "Control.Look", "視点")},
        {TEXT("GamepadLookYaw"), 0, NSLOCTEXT("SoraArena.Controls", "Control.Look", "視点")},
        {TEXT("GamepadLookPitch"), 0, NSLOCTEXT("SoraArena.Controls", "Control.Look", "視点")},
    };
    for (const FControl& Control : Controls)
        if (Name == Control.Name && (Control.Axis == 0 || Control.Axis == Axis))
            return SoraText::Line(Control.Label);
    // An action this table misses shows its input name rather than nothing.
    return SoraText::Same(Name.ToString());
}

SoraText::FLine SoraUI::ActionKey(const UObject* WorldContext, FName Action)
{
    const ASoraGameMode* Mode = WorldContext ? Cast<ASoraGameMode>(UGameplayStatics::GetGameMode(WorldContext)) : nullptr;
    const bool bPad = Mode && Mode->FrontEnd() && Mode->FrontEnd()->Device() == EDevice::Gamepad;
    TArray<FKey> Keys;
    if (const ASoraPlayerCharacter* Hero = Mode ? Mode->Hero() : nullptr)
        Keys = Hero->GetActionKeys(Action);
    if (Keys.IsEmpty())
    {
        TArray<FInputActionKeyMapping> Mappings;
        GetDefault<UInputSettings>()->GetActionMappingByName(Action, Mappings);
        for (const FInputActionKeyMapping& Mapping : Mappings)
            Keys.AddUnique(Mapping.Key);
    }
    for (const bool bWanted : {bPad, !bPad})
        for (const FKey& Key : Keys)
            if (Key.IsGamepadKey() == bWanted)
                return KeyLabel(Key);
    return KeyLabel(EKeys::Invalid);
}

FText SoraUI::SpecialTradeoff(int32 WeaponId)
{
    // Keyed by catalog weapon id: the six special sidegrades.
    switch (WeaponId)
    {
    case 12: return NSLOCTEXT("SoraArena.Menu", "Tradeoff.MonofilamentNaginata", "間合いは長いが、刀より振りが遅い。");
    case 13: return NSLOCTEXT("SoraArena.Menu", "Tradeoff.PhantomSMG", "一発ごとの当たりは重いが、弾倉は小さい。");
    case 14: return NSLOCTEXT("SoraArena.Menu", "Tradeoff.PlasmaMatchlock", "重く正確な一撃。装弾数は少なく、立て直しに時間がかかる。");
    case 15: return NSLOCTEXT("SoraArena.Menu", "Tradeoff.MicroMortar", "爆風は広いが、弾道は遅く予兆が見え、自分も巻き込む。");
    case 16: return NSLOCTEXT("SoraArena.Menu", "Tradeoff.ShockEmitter", "間近の敵を強く抑えるが、射程は短い。");
    case 17: return NSLOCTEXT("SoraArena.Menu", "Tradeoff.HealingLance", "オフラインの稽古では使い手の体力を少し戻すが、威力は低い。");
    default: return FText::GetEmpty();
    }
}
