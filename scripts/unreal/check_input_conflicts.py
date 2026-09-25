"""Reject input keys that trigger two actions in one game state.

Reads Config/DefaultInput.ini and the action-state table in
Source/SoraArena/Public/SoraInputStates.h, which ASoraPlayerCharacter uses to ignore
presses outside their states. Two actions may share a physical key only when no
state lets both act. Unreal compares key names without regard to case, so this
check does too. Menu actions may not sit on a thumbstick click, which players
press by accident while moving or aiming. Every mapped action must be bound
through the state gate in SoraPlayerCharacter.cpp, and no source in
Source/SoraArena other than the automation tests may bind input any other way.

The built-in self-test runs first and must reject known-bad layouts, including
the pre-fix pad layout, so a broken checker cannot pass silently.
"""
import argparse
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
INPUT_INI = ROOT / "Config/DefaultInput.ini"
STATE_TABLE = ROOT / "Source/SoraArena/Public/SoraInputStates.h"
SOURCE = ROOT / "Source/SoraArena"
CHARACTER = SOURCE / "Private/Characters/SoraPlayerCharacter.cpp"
CLASS = "ASoraPlayerCharacter"

STATES = {"Menu": 1, "Confirm": 2, "Card": 4, "Play": 8, "Result": 16}
STATES["Always"] = sum(STATES.values())
MENU_STATES = STATES["Menu"] | STATES["Confirm"]
STICK_CLICKS = {"gamepad_leftthumbstick", "gamepad_rightthumbstick"}
MODIFIERS = ("bShift", "bCtrl", "bAlt", "bCmd")
# FBoolProperty's import compares without case against these (and localized True/Yes).
TRUE_VALUES = {"1", "true", "yes"}
# UInputComponent and Enhanced Input calls that bind a key, touch, gesture or
# action straight to a handler, and the binding arrays behind them. Only the
# gated BindPress/BindRelease helpers may call AddActionBinding.
RAW_BINDING = re.compile(
    r"\b(Bind(?:Action\w*|Key|Touch|Gesture|AxisKey|VectorAxis|DebugKey)|Add\w*Binding"
    r"|(?:Action|Axis|Key|Touch|Gesture|AxisKey|VectorAxis)Bindings)\b")
AXIS_BINDING = re.compile(r"\bBindAxis\b")
PRESS = re.compile(r'\bBindPress\s*\(\s*\w+\s*,\s*TEXT\s*\(\s*"(\w+)"\s*\)')
AXIS = re.compile(r'\bBindAxis\s*\(\s*TEXT\s*\(\s*"(\w+)"\s*\)')


def state_names(mask):
    return "|".join(name for name, bit in STATES.items() if name != "Always" and mask & bit)


def ini_value(raw):
    """An ini struct field as Unreal reads it, without surrounding space or quotes."""
    return raw.strip().strip('"').strip()


def parse_mappings(text):
    """Return [(kind, name, key, label)] for every +ActionMappings/+AxisMappings line.

    key is the casefolded key name, prefixed by any held modifiers; label is
    the same chord as the ini spells it."""
    mappings = []
    for number, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not re.match(r"^[-+.!]?(ActionMappings|AxisMappings)=", line):
            continue
        match = re.fullmatch(r"\+(ActionMappings|AxisMappings)=\((.*)\)", line)
        if not match:
            raise ValueError(f"DefaultInput.ini:{number}: only '+' mapping lines are supported: {line}")
        fields = {name: ini_value(value) for name, value in re.findall(r'(\w+)=("[^"]*"|[^,]+)', match.group(2))}
        name = fields.get("ActionName") or fields.get("AxisName") or ""
        key = fields.get("Key", "")
        if not name or not key:
            raise ValueError(f"DefaultInput.ini:{number}: mapping lacks a name or key: {line}")
        held = [modifier[1:] for modifier in MODIFIERS if fields.get(modifier, "").casefold() in TRUE_VALUES]
        kind = "action" if match.group(1) == "ActionMappings" else "axis"
        mappings.append((kind, name, "+".join(held + [key.casefold()]), "+".join(held + [key])))
    return mappings


def parse_states(text):
    """Return {action: state mask} from the SoraInput::Actions table."""
    try:
        body = text.split("Actions[] = {", 1)[1].split("};", 1)[0]
    except IndexError:
        raise ValueError("SoraInputStates.h has no Actions[] table") from None
    table = {}
    for name, expression in re.findall(r'\{TEXT\("(\w+)"\),\s*([A-Za-z|\s]+)\}', body):
        if name in table:
            raise ValueError(f"SoraInputStates.h lists {name} twice")
        mask = 0
        for token in expression.split("|"):
            token = token.strip()
            if token not in STATES:
                raise ValueError(f"SoraInputStates.h: {name} uses unknown state {token!r}")
            mask |= STATES[token]
        table[name] = mask
    if not table:
        raise ValueError("SoraInputStates.h Actions[] table has no rows")
    return table


def blank_source(text):
    """Return (code, bare) with the offsets and line breaks of text.

    code has comments blanked; bare also blanks the contents of string and
    character literals, so neither can hide or fake a call."""
    code, bare = [], []
    index, size = 0, len(text)
    while index < size:
        if text.startswith("//", index) or text.startswith("/*", index):
            end = text.find("\n", index) if text[index + 1] == "/" else text.find("*/", index + 2)
            end = size if end < 0 else end + (2 if text[index + 1] == "*" else 0)
            blank = re.sub(r"[^\n]", " ", text[index:end])
            code.append(blank)
            bare.append(blank)
        elif text[index] in "\"'":
            end = index + 1
            while end < size and text[end] not in (text[index], "\n"):
                end += 2 if text[end] == "\\" else 1
            end = min(end + 1, size)
            code.append(text[index:end])
            bare.append(text[index] + " " * (end - index - 2) + text[end - 1] if end - index > 1 else text[index])
        else:
            end = index + 1
            code.append(text[index])
            bare.append(text[index])
        index = end
    return "".join(code), "".join(bare)


def function_body(bare, name):
    """Return the (start, end) offsets of void CLASS::name(...) { ... }, or None."""
    match = re.search(rf"\bvoid\s+{CLASS}::{name}\s*\(", bare)
    if not match:
        return None
    depth, index = 0, match.end() - 1
    for index in range(match.end() - 1, len(bare)):
        depth += {"(": 1, ")": -1}.get(bare[index], 0)
        if depth == 0:
            break
    start = bare.find("{", index)
    if start < 0:
        return None
    depth = 0
    for index in range(start, len(bare)):
        depth += {"{": 1, "}": -1}.get(bare[index], 0)
        if depth == 0:
            return start, index + 1
    return None


def line_of(text, offset):
    return text.count("\n", 0, offset) + 1


def parse_bindings(text):
    """Return (gated presses, bound axes, errors) for the player character source."""
    code, bare = blank_source(text)
    spans = {}
    for name in ("SetupPlayerInputComponent", "BindPress", "BindRelease"):
        spans[name] = function_body(bare, name)
        if spans[name] is None:
            raise ValueError(f"the player character source has no void {CLASS}::{name}(...) definition")
    errors = []
    start, end = spans["SetupPlayerInputComponent"]
    setup = code[start:end]
    presses = set(PRESS.findall(setup))
    axes = set(AXIS.findall(setup))
    if len(AXIS_BINDING.findall(bare[start:end])) != len(AXIS.findall(setup)):
        errors.append("SoraPlayerCharacter.cpp binds an axis whose name is not a TEXT literal")
    press_start, press_end = spans["BindPress"]
    if not re.search(r"\bAcceptsInput\s*\(", bare[press_start:press_end]):
        errors.append("SoraPlayerCharacter.cpp BindPress no longer asks AcceptsInput, so no press is gated")
    helpers = [spans["BindPress"], spans["BindRelease"]]
    for match in RAW_BINDING.finditer(bare):
        if not any(first <= match.start() < last for first, last in helpers):
            errors.append(f"SoraPlayerCharacter.cpp:{line_of(bare, match.start())} uses {match.group(1)} "
                          "outside BindPress/BindRelease, bypassing the state gate")
    for match in AXIS_BINDING.finditer(bare):
        if not start <= match.start() < end:
            errors.append(f"SoraPlayerCharacter.cpp:{line_of(bare, match.start())} binds an axis "
                          "outside SetupPlayerInputComponent")
    return presses, axes, errors


def other_binding_errors(name, text):
    """Every input binding in a source other than the player character."""
    _, bare = blank_source(text)
    errors = []
    for pattern in (RAW_BINDING, AXIS_BINDING):
        for match in pattern.finditer(bare):
            errors.append(f"{name}:{line_of(bare, match.start())} uses {match.group(0)}, bypassing the state gate; "
                          f"bind input only in {CLASS}::SetupPlayerInputComponent")
    return errors


def check(ini_text, table_text, character_text=None, sources=()):
    """Return a list of human-readable errors; empty means the layout is safe.

    sources holds (name, text) for every other module source to scan."""
    errors = []
    mappings = parse_mappings(ini_text)
    table = parse_states(table_text)
    actions = {name for kind, name, *_ in mappings if kind == "action"}
    axes = {name for kind, name, *_ in mappings if kind == "axis"}
    for name in sorted((actions | axes) - table.keys()):
        errors.append(f"{name} is mapped in DefaultInput.ini but has no row in SoraInputStates.h")
    for name in sorted(table.keys() - (actions | axes)):
        errors.append(f"SoraInputStates.h lists {name}, which DefaultInput.ini does not map")
    for name, mask in sorted(table.items()):
        if mask == 0:
            errors.append(f"{name} has no states and could never act")
    by_key, labels = {}, {}
    for _, name, key, label in mappings:
        by_key.setdefault(key, [])
        labels.setdefault(key, label)
        if name not in by_key[key]:
            by_key[key].append(name)
    for key, names in sorted(by_key.items()):
        for index, first in enumerate(names):
            for second in names[index + 1:]:
                both = table.get(first, 0) & table.get(second, 0)
                if both:
                    errors.append(f"{labels[key]} triggers {first} and {second} together in {state_names(both)}")
        if key.split("+")[-1] in STICK_CLICKS:
            for name in names:
                if table.get(name, 0) & MENU_STATES:
                    errors.append(f"{labels[key]} carries menu action {name}; stick clicks are pressed by accident")
    if character_text is not None:
        presses, bound_axes, binding_errors = parse_bindings(character_text)
        errors += binding_errors
        for name in sorted(actions - presses):
            errors.append(f"{name} is mapped but not bound through BindPress in SoraPlayerCharacter.cpp")
        for name in sorted(presses - actions):
            errors.append(f"SoraPlayerCharacter.cpp binds {name}, which DefaultInput.ini does not map")
        for name in sorted(axes ^ bound_axes):
            errors.append(f"Axis {name} is not both mapped and bound")
    for name, text in sources:
        errors += other_binding_errors(name, text)
    return errors


def shared_keys(ini_text, table_text):
    table = parse_states(table_text)
    by_key, labels = {}, {}
    for _, name, key, label in parse_mappings(ini_text):
        by_key.setdefault(key, set()).add(name)
        labels.setdefault(key, label)
    return {labels[key]: sorted(names, key=lambda name: table[name]) for key, names in by_key.items() if len(names) > 1}


def module_sources(root, character):
    """(name, text) for each module source except the player character and the
    automation tests, which drive bound handlers directly."""
    skip = {CHARACTER.resolve(), character.resolve()}
    for path in sorted(root.rglob("*")):
        if (path.suffix in (".cpp", ".h", ".inl") and path.resolve() not in skip
                and not path.name.endswith("Automation.cpp") and not path.stem == "SoraAutomationWorld"):
            yield str(path.relative_to(root)), path.read_text(errors="replace")


SELF_TEST_TABLE = """inline constexpr FAction Actions[] = {
    {TEXT("Jump"), Play},
    {TEXT("Sprint"), Play},
    {TEXT("Enter"), Menu | Card | Result},
    {TEXT("NewCampaign"), Menu | Confirm},
    {TEXT("Menu"), Always},
};"""

SELF_TEST_CHARACTER = """void ASoraPlayerCharacter::BindPress(UInputComponent* Input,const TCHAR* Action,void (ASoraPlayerCharacter::*Handler)())
{
    FInputActionBinding Binding(Action,IE_Pressed);
    Binding.ActionDelegate.GetDelegateForManualSet().BindWeakLambda(this,[this,Handler]() { if(AcceptsInput(1)) (this->*Handler)(); });
    Input->AddActionBinding(MoveTemp(Binding));
}
void ASoraPlayerCharacter::BindRelease(UInputComponent* Input,const TCHAR* Action,void (ASoraPlayerCharacter::*Handler)())
{
    FInputActionBinding Binding(Action,IE_Released);
    Binding.ActionDelegate.BindDelegate(this,Handler);
    Input->AddActionBinding(MoveTemp(Binding));
}
void ASoraPlayerCharacter::SetupPlayerInputComponent(UInputComponent* I)
{
    // I->BindAction(TEXT("Menu"),IE_Pressed,this,&A::B) stays a comment.
    BindPress(I,TEXT("Jump"),&A::B); BindPress(I, TEXT("Sprint"), &A::B);
    BindPress(I,TEXT("Enter"),&A::B); BindPress(I,TEXT("NewCampaign"),&A::B);
    BindPress(I,TEXT("Menu"),&A::B);
    UE_LOG(LogTemp,Display,TEXT("BindKey( in a string is not a call"));
}
"""


def expect_error(errors, fragment):
    assert any(fragment in error for error in errors), (fragment, errors)


def self_test():
    """Known-bad layouts must fail and a disjoint shared key must pass."""
    good = ('+ActionMappings=(ActionName="Jump",Key=Gamepad_FaceButton_Bottom)\n'
            '+ActionMappings=(ActionName="Enter",Key=Gamepad_FaceButton_Bottom)\n'
            '+ActionMappings=(ActionName="Sprint",Key=Gamepad_LeftThumbstick)\n'
            '+ActionMappings=(ActionName="NewCampaign",Key=Gamepad_FaceButton_Top)\n'
            '+ActionMappings=(ActionName="Menu",Key=Gamepad_Special_Right)\n')
    assert check(good, SELF_TEST_TABLE) == [], check(good, SELF_TEST_TABLE)
    # The pre-fix pad layout put New Campaign on the sprint stick click.
    stick = good.replace("NewCampaign\",Key=Gamepad_FaceButton_Top", "NewCampaign\",Key=Gamepad_LeftThumbstick")
    expect_error(check(stick, SELF_TEST_TABLE), "stick clicks")
    # Unreal matches key names without case, so a respelled key is the same key.
    expect_error(check(stick.replace("Key=Gamepad_LeftThumbstick", "Key=gamepad_leftthumbstick"), SELF_TEST_TABLE),
                 "stick clicks")
    expect_error(check(good.replace("Enter\",Key=Gamepad_FaceButton_Bottom", "Enter\",Key=\"GAMEPAD_FACEBUTTON_BOTTOM\""),
                       SELF_TEST_TABLE.replace("Menu | Card | Result", "Menu | Card | Play | Result")),
                 "triggers Jump and Enter together in Play")
    # Enter live in play would make pad A jump and confirm in one press.
    overlap = SELF_TEST_TABLE.replace("Menu | Card | Result", "Menu | Card | Play | Result")
    expect_error(check(good, overlap), "triggers Jump and Enter together in Play")
    # Menu toggles in every state, so it can never share a key.
    menu_share = good + '+ActionMappings=(ActionName="Jump",Key=Gamepad_Special_Right)\n'
    expect_error(check(menu_share, SELF_TEST_TABLE), "triggers Menu and Jump together in Play")
    # Unlisted actions and stale rows fail closed.
    expect_error(check(good + '+ActionMappings=(ActionName="Fire",Key=Z)\n', SELF_TEST_TABLE), "no row")
    stale = SELF_TEST_TABLE.replace("};", '    {TEXT("Ability"), Play},\n};')
    expect_error(check(good, stale), "does not map")
    # Chords are distinct keys, whatever the case of the modifier value.
    chord = good + '+ActionMappings=(ActionName="Sprint",Key=Enter,bShift=true)\n'
    assert check(chord, SELF_TEST_TABLE) == [], check(chord, SELF_TEST_TABLE)
    unheld = good + ('+ActionMappings=(ActionName="Sprint",Key=Escape,bShift=False)\n'
                     '+ActionMappings=(ActionName="Menu",Key=escape)\n')
    expect_error(check(unheld, SELF_TEST_TABLE), "triggers Sprint and Menu together in Play")
    try:
        check(good + '-ActionMappings=(ActionName="Jump",Key=SpaceBar)\n', SELF_TEST_TABLE)
    except ValueError:
        pass
    else:
        raise AssertionError("a '-' mapping line was accepted")
    # The gated helpers, comments and strings pass; every raw binding fails.
    assert check(good, SELF_TEST_TABLE, SELF_TEST_CHARACTER) == [], check(good, SELF_TEST_TABLE, SELF_TEST_CHARACTER)
    body_end = SELF_TEST_CHARACTER.rindex("}")
    for raw in ('I->BindAction(TEXT("Menu"),IE_Pressed,this,&A::B);',
                'I->BindAction(FName("Enter"),IE_Pressed,this,&A::B);',
                'I->BindAction("Enter",IE_Pressed,this,&A::B);',
                'I->BindKey(EKeys::Gamepad_FaceButton_Bottom,IE_Pressed,this,&A::B);',
                'I->BindTouch(IE_Pressed,this,&A::B);',
                'I->BindAxisKey(EKeys::Gamepad_LeftX,this,&A::B);',
                'I->BindVectorAxis(EKeys::Tilt,this,&A::B);',
                'I->AddActionBinding(FInputActionBinding(TEXT("Enter"),IE_Pressed));',
                'I->KeyBindings.Emplace(FInputChord(EKeys::Enter),IE_Pressed);'):
        character = SELF_TEST_CHARACTER[:body_end] + "    " + raw + "\n" + SELF_TEST_CHARACTER[body_end:]
        expect_error(check(good, SELF_TEST_TABLE, character), "bypassing the state gate")
        expect_error(check(good, SELF_TEST_TABLE, None, [("Game/SoraGameMode.cpp", raw)]), "Game/SoraGameMode.cpp:1 uses")
    # An axis bound by a name the check cannot read, or in another class, fails.
    unread = SELF_TEST_CHARACTER.replace("BindPress(I,TEXT(\"Menu\"),&A::B);",
                                         "BindPress(I,TEXT(\"Menu\"),&A::B); I->BindAxis(Name,this,&A::B);")
    expect_error(check(good, SELF_TEST_TABLE, unread), "not a TEXT literal")
    expect_error(check(good, SELF_TEST_TABLE, SELF_TEST_CHARACTER,
                       [("HUD/SoraHUD.cpp", 'InputComponent->BindAxis(TEXT("MoveForward"),this,&A::B);')]),
                 "HUD/SoraHUD.cpp:1 uses BindAxis")
    # A binding outside the helpers in the character file fails even in another function.
    helper = SELF_TEST_CHARACTER + "void ASoraPlayerCharacter::Other(UInputComponent* I)\n{\n    I->AddActionBinding(X);\n}\n"
    expect_error(check(good, SELF_TEST_TABLE, helper), "outside BindPress/BindRelease")
    # A press helper that no longer asks the gate fails.
    expect_error(check(good, SELF_TEST_TABLE, SELF_TEST_CHARACTER.replace("if(AcceptsInput(1)) ", "")), "no press is gated")
    # A mapped action left unbound fails.
    unbound = SELF_TEST_CHARACTER.replace("BindPress(I,TEXT(\"Menu\"),&A::B);", "")
    expect_error(check(good, SELF_TEST_TABLE, unbound), "Menu is mapped but not bound")
    # A renamed or moved input setup must not pass by finding no bindings.
    try:
        check(good, SELF_TEST_TABLE, SELF_TEST_CHARACTER.replace("ASoraPlayerCharacter::Setup", "ASoraHero::Setup"))
    except ValueError:
        pass
    else:
        raise AssertionError("a source without the player input setup was accepted")


def check_project(ini=INPUT_INI, table=STATE_TABLE, character=CHARACTER, source=SOURCE):
    """Raise SystemExit with every problem, or return a summary line."""
    self_test()
    ini_text, table_text = ini.read_text(), table.read_text()
    sources = list(module_sources(source, character))
    errors = check(ini_text, table_text, character.read_text(), sources)
    if errors:
        raise SystemExit("Input conflict check failed:\n  " + "\n  ".join(errors))
    shared = shared_keys(ini_text, table_text)
    table_rows = parse_states(table_text)
    detail = ", ".join(f"{key} ({' / '.join(f'{name}:{state_names(table_rows[name])}' for name in names)})"
                       for key, names in sorted(shared.items()))
    mappings = parse_mappings(ini_text)
    return (f"Input conflict check passed: {len({name for _, name, *_ in mappings})} actions and axes on "
            f"{len({key for _, _, key, _ in mappings})} keys; no other input binding in {len(sources)} module sources; "
            f"shared keys act in disjoint states: {detail}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ini", type=Path, default=INPUT_INI, help="input ini to check (default: Config/DefaultInput.ini)")
    parser.add_argument("--table", type=Path, default=STATE_TABLE, help="state table header (default: SoraInputStates.h)")
    parser.add_argument("--character", type=Path, default=CHARACTER, help="character source with the bindings")
    parser.add_argument("--source", type=Path, default=SOURCE, help="module sources to scan (default: Source/SoraArena)")
    args = parser.parse_args()
    print(check_project(args.ini, args.table, args.character, args.source))


if __name__ == "__main__":
    sys.exit(main())
