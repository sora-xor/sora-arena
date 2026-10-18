#pragma once

// Nyaakoto's campaign arms selection, shared by ASoraPlayerCharacter, the
// HUD's arms wheel and a host-compiled driver
// (scripts/unreal/test_fieldcraft_rules.py). He carries every arm the
// campaign has unlocked (catalog IDs 0-20), kept in six groups in a fixed
// order; the wheel's ring is that order. A group key (1-6 on the keyboard,
// the d-pad's left, down and right for the first three) takes up the group's
// arm he last held, and a second press steps through the group. A tap on the
// wheel key, or the mouse wheel, steps to the next or previous arm he can
// hold; holding the wheel key opens the wheel. Whether an arm can be held
// right now (unlocked, and allowed in the saddle or under a load) is the
// caller's mask. No Unreal headers belong here.
namespace SoraArmsRules
{
constexpr int ArmsCount = 21;
constexpr int GroupCount = 6;
// 刀剣 swords, 長柄 polearms, 弓 the bow, 鉄砲 firearms, 鎖・打物 chain and
// striking arms, 火具・支援 explosives and support.
enum class EGroup : unsigned char { Swords, Polearms, Bow, Firearms, ChainAndImpact, FireAndSupport };

// The 21 arms in ring order, each group's arms together: katana, wakizashi,
// tantō; yari, naginata, monofilament naginata; yumi; coil matchlock, plasma
// matchlock, arc carbine, pulse carbine, repeater, needle SMG, phantom SMG;
// kusarigama, kanabō, forge hammer; grenade launcher, micro-mortar, shock
// emitter, healing lance.
constexpr int Ring[ArmsCount] = {0, 4, 10, 19, 20, 12, 18, 5, 14, 1, 11, 9, 3, 13, 2, 6, 8, 7, 15, 16, 17};
constexpr int GroupStart[GroupCount + 1] = {0, 3, 6, 7, 14, 17, 21};

// A tap on the wheel key is shorter than this; a longer hold opens the wheel.
constexpr int WheelHoldMs = 250;
// The wheel cursor must leave this share of its radius, x1000, to choose;
// released inside it, the wheel keeps the arm in hand.
constexpr int WheelDeadPermille = 350;
// While the wheel is open the world runs at this share of its pace, x1000.
constexpr int WheelTimePermille = 250;

constexpr int RingIndex(int WeaponId)
{
    for (int Index = 0; Index < ArmsCount; ++Index)
        if (Ring[Index] == WeaponId)
            return Index;
    return -1;
}

constexpr int GroupOf(int WeaponId)
{
    const int Index = RingIndex(WeaponId);
    if (Index < 0)
        return -1;
    int Group = 0;
    while (Index >= GroupStart[Group + 1])
        ++Group;
    return Group;
}

constexpr bool Holds(unsigned Mask, int WeaponId)
{
    return WeaponId >= 0 && WeaponId < ArmsCount && (Mask & (1u << WeaponId)) != 0u;
}

// The arms in Mask in ring order, written to Out; returns how many.
constexpr int HeldRing(unsigned Mask, int (&Out)[ArmsCount])
{
    int Count = 0;
    for (int Index = 0; Index < ArmsCount; ++Index)
        if (Holds(Mask, Ring[Index]))
            Out[Count++] = Ring[Index];
    return Count;
}

// The next arm in Mask after Current in ring order (Step +1), or before it
// (Step -1), wrapping. Current when it is the only one; -1 when Mask is empty.
// An arm outside Mask as Current starts from its place in the ring.
constexpr int Next(unsigned Mask, int Current, int Step)
{
    const int Direction = Step < 0 ? -1 : 1;
    const int Start = RingIndex(Current);
    for (int Offset = 1; Offset <= ArmsCount; ++Offset)
    {
        const int Index = ((Start < 0 ? (Direction > 0 ? -1 : 0) : Start) + Direction * Offset + 2 * ArmsCount) % ArmsCount;
        if (Holds(Mask, Ring[Index]))
            return Ring[Index];
    }
    return -1;
}

// A group key: the next arm of the group in Mask after Current when Current
// belongs to the group; otherwise Remembered, the group's arm last held, when
// it is in Mask; otherwise the group's first arm in Mask. -1 when the group
// has none in Mask.
constexpr int Pick(unsigned Mask, int Group, int Current, int Remembered)
{
    if (Group < 0 || Group >= GroupCount)
        return -1;
    const int First = GroupStart[Group], Last = GroupStart[Group + 1];
    const int Size = Last - First;
    const int At = RingIndex(Current);
    if (At >= First && At < Last)
    {
        for (int Offset = 1; Offset <= Size; ++Offset)
        {
            const int Index = First + (At - First + Offset) % Size;
            if (Holds(Mask, Ring[Index]))
                return Ring[Index];
        }
        return -1;
    }
    if (GroupOf(Remembered) == Group && Holds(Mask, Remembered))
        return Remembered;
    for (int Index = First; Index < Last; ++Index)
        if (Holds(Mask, Ring[Index]))
            return Ring[Index];
    return -1;
}

// The wheel's sector under an angle in millidegrees clockwise from the top,
// for Count sectors centred on the top and spaced evenly: an index into
// HeldRing's output, or -1 when there are none.
constexpr int Sector(int AngleMilliDegrees, int Count)
{
    if (Count <= 0)
        return -1;
    const long long Angle = ((AngleMilliDegrees % 360000) + 360000) % 360000;
    return static_cast<int>((Angle * Count + 180000) / 360000 % Count);
}
} // namespace SoraArmsRules
