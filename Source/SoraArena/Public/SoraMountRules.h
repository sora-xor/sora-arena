#pragma once

// Horseback rules for the offline campaign (bible §4.2-4.5, chapter-04 §6.5),
// shared by ASoraHorse and a host-compiled acceptance driver. Above a halt a
// horse has four gaits: 常歩 walk, 速歩 trot, 駈歩 canter and 襲歩 gallop.
// With his legs on, the rider holds the gait (a halted horse walks on); urging
// asks for one gait more at a time, gathering the reins one gait less, and a
// horse left alone eases down. Wind (stamina) rises or falls per gait; a
// winded horse drops out of the gallop and cannot gallop again until she
// recovers. A hazard entering her fear radius spooks her to a walk until she
// settles. The rider mounts and dismounts on the horse's right, as period
// riders did, and a weapon acts only in its mounted arc: the yumi to the left
// (弓手), the katana cut and yari thrust forward and to the right (馬手).
// Time is integer milliseconds, distance centimetres and angles whole
// degrees (0 = the horse's heading, negative = her left). No Unreal headers
// belong here.
namespace SoraMountRules
{
enum class EGait : unsigned char { Halt, Walk, Trot, Canter, Gallop };
constexpr int GaitCount = 5;
// Wind in thousandths of a point, out of 100 points.
constexpr int StaminaFull = 100000;
// Held urging per gait up, held reins per gait down, and untouched reins per
// gait eased down.
constexpr int UrgeStepMs = 700;
constexpr int ReinStepMs = 400;
constexpr int EaseStepMs = 1500;
// Chapter-04 §6.4: a frightened laden mare pulls the riding horse's head
// for one second. A continuous encounter cannot renew that loss of steering.
constexpr int LeadTugMs = 1000;
struct FLeadFear
{
    int RemainingMs = 0;
    bool Near = false;
};
struct FLeadTug { int RemainingMs = 0; };
constexpr bool StartLeadFear(FLeadFear& State, int RecoveryMs)
{
    if (RecoveryMs <= 0 || State.RemainingMs > 0) return false;
    State.RemainingMs = RecoveryMs;
    return true;
}
constexpr bool ObserveLeadFear(FLeadFear& State, bool Near, int RecoveryMs)
{
    const bool Entered = Near && !State.Near;
    State.Near = Near;
    return Entered && StartLeadFear(State, RecoveryMs);
}
constexpr void StepLeadFear(FLeadFear& State, int DeltaMs)
{
    if (DeltaMs > 0) State.RemainingMs = DeltaMs >= State.RemainingMs ? 0 : State.RemainingMs - DeltaMs;
}
constexpr bool StartLeadTug(FLeadTug& State)
{
    if (State.RemainingMs > 0) return false;
    State.RemainingMs = LeadTugMs;
    return true;
}
// The frame that consumes the last held millisecond still belongs to the
// tug. Steering resumes next frame, never one frame before the full second.
constexpr bool StepLeadTug(FLeadTug& State, int DeltaMs)
{
    const bool Blocked = State.RemainingMs > 0;
    if (DeltaMs > 0) State.RemainingMs = DeltaMs >= State.RemainingMs ? 0 : State.RemainingMs - DeltaMs;
    return Blocked;
}
// Degrees per second she turns at each gait, from a halt to the gallop.
constexpr int TurnDegS[GaitCount] = {120, 90, 75, 60, 45};
// Mounting: the rider stands by her right flank, beside the saddle.
constexpr int MountNearCm = 40;
constexpr int MountFarCm = 220;
constexpr int MountReachCm = 140;
// Dismounting sets him down this far to her right.
constexpr int DismountSideCm = 130;
// The weapons a rider may use, by arc slot: katana, yumi, yari (catalog 0, 18, 19).
constexpr int ArcWeapons[3] = {0, 18, 19};

// A ride as its beat authors it.
struct FHorse
{
    EGait MaxGait = EGait::Trot;
    int SpeedCmS[GaitCount] = {0, 170, 350, 550, 800};
    // Wind per second at each gait; a halt breathes like a walk.
    int StaminaPerS[GaitCount] = {8, 8, 8, 0, -12};
    // Points of wind below which the gallop locks out, and at which it returns.
    int LockoutBelow = 20;
    int RecoverAt = 50;
    int FearRecoverMs = 0;
    // Weapon ids by bit, and each arc slot's arc in degrees.
    unsigned WeaponsMask = 0u;
    int ArcMin[3] = {0, 0, 0};
    int ArcMax[3] = {0, 0, 0};
};

struct FRide
{
    EGait Gait = EGait::Halt;
    int Stamina = StaminaFull;
    bool GallopLocked = false;
    int UrgeMs = 0;
    int ReinMs = 0;
    int EaseMs = 0;
    int SpookMs = 0;
};

// One step of the rider's hands and the road ahead.
struct FControl
{
    int DeltaMs = 0;
    // Legs on: walk on from a halt and hold the gait.
    bool Forward = false;
    // With the legs on: ask for the next gait.
    bool Urge = false;
    // Gather the reins: the next gait down.
    bool Rein = false;
    // The road, a laden pack horse or a forced-gait stretch.
    EGait Cap = EGait::Gallop;
    // A hazard entered her fear radius, or a scripted spook, this step.
    bool Spook = false;
};

constexpr int Index(EGait Gait)
{
    return static_cast<int>(Gait);
}

constexpr EGait Slower(EGait A, EGait B)
{
    return Index(A) < Index(B) ? A : B;
}

constexpr EGait Up(EGait Gait)
{
    return Gait == EGait::Gallop ? Gait : static_cast<EGait>(Index(Gait) + 1);
}

constexpr EGait Down(EGait Gait)
{
    return Gait == EGait::Halt ? Gait : static_cast<EGait>(Index(Gait) - 1);
}

// The fastest gait she may take now: the ride's, the road's, a walk while
// spooked, and a canter while winded.
constexpr EGait Ceiling(const FRide& Ride, const FHorse& Horse, EGait Cap)
{
    EGait Top = Slower(Horse.MaxGait, Cap);
    if (Ride.SpookMs > 0)
        Top = Slower(Top, EGait::Walk);
    if (Ride.GallopLocked)
        Top = Slower(Top, EGait::Canter);
    return Top;
}

constexpr bool Spooked(const FRide& Ride)
{
    return Ride.SpookMs > 0;
}

// Advances wind, a spook and the gait by one step. True when the gait changed.
constexpr bool Step(FRide& Ride, const FHorse& Horse, FControl Control)
{
    if (Control.DeltaMs <= 0)
        return false;
    const int Delta = Control.DeltaMs > 60000 ? 60000 : Control.DeltaMs;
    const EGait Before = Ride.Gait;
    if (Control.Spook && Ride.SpookMs <= 0 && Horse.FearRecoverMs > 0)
        Ride.SpookMs = Horse.FearRecoverMs;
    else if (Ride.SpookMs > 0)
        Ride.SpookMs = Ride.SpookMs > Delta ? Ride.SpookMs - Delta : 0;
    const long long Wind = Ride.Stamina + static_cast<long long>(Horse.StaminaPerS[Index(Ride.Gait)]) * Delta;
    Ride.Stamina = static_cast<int>(Wind < 0 ? 0 : Wind > StaminaFull ? StaminaFull : Wind);
    if (Ride.Gait == EGait::Gallop && Ride.Stamina < Horse.LockoutBelow * 1000)
        Ride.GallopLocked = true;
    else if (Ride.GallopLocked && Ride.Stamina >= Horse.RecoverAt * 1000)
        Ride.GallopLocked = false;
    const EGait Top = Ceiling(Ride, Horse, Control.Cap);
    if (Control.Rein)
    {
        Ride.UrgeMs = Ride.EaseMs = 0;
        for (Ride.ReinMs += Delta; Ride.ReinMs >= ReinStepMs; Ride.ReinMs -= ReinStepMs)
            Ride.Gait = Down(Ride.Gait);
    }
    else if (Control.Forward)
    {
        Ride.ReinMs = Ride.EaseMs = 0;
        if (Ride.Gait == EGait::Halt && Index(Top) >= Index(EGait::Walk))
            Ride.Gait = EGait::Walk;
        if (!Control.Urge)
            Ride.UrgeMs = 0;
        for (Ride.UrgeMs += Control.Urge ? Delta : 0; Ride.UrgeMs >= UrgeStepMs; Ride.UrgeMs -= UrgeStepMs)
            if (Index(Up(Ride.Gait)) <= Index(Top))
                Ride.Gait = Up(Ride.Gait);
    }
    else
    {
        Ride.UrgeMs = Ride.ReinMs = 0;
        for (Ride.EaseMs += Delta; Ride.EaseMs >= EaseStepMs; Ride.EaseMs -= EaseStepMs)
            Ride.Gait = Down(Ride.Gait);
    }
    while (Index(Ride.Gait) > Index(Top))
        Ride.Gait = Down(Ride.Gait);
    return Ride.Gait != Before;
}

constexpr int SpeedCmS(const FRide& Ride, const FHorse& Horse)
{
    return Horse.SpeedCmS[Index(Ride.Gait)];
}

// Whether a rider standing at (LocalX, LocalY) in her frame (x toward her
// head, y to her right) is at her right flank, beside the saddle.
constexpr bool CanMount(int LocalXCm, int LocalYCm)
{
    return LocalYCm >= MountNearCm && LocalYCm <= MountFarCm && LocalXCm >= -MountReachCm && LocalXCm <= MountReachCm;
}

// The same place on her left: the wrong side, which a period rider refuses.
constexpr bool AtLeftFlank(int LocalXCm, int LocalYCm)
{
    return CanMount(LocalXCm, -LocalYCm);
}

constexpr int NormalizeDeg(int Degrees)
{
    int Result = Degrees % 360;
    if (Result > 180)
        Result -= 360;
    if (Result < -180)
        Result += 360;
    return Result;
}

constexpr int ArcSlot(int WeaponId)
{
    return WeaponId == ArcWeapons[0] ? 0 : WeaponId == ArcWeapons[1] ? 1 : WeaponId == ArcWeapons[2] ? 2 : -1;
}

// A weapon acts from the saddle only if the ride allows it and the rider aims
// within its arc of her heading. Firearms have no arc.
constexpr bool ArcAllows(const FHorse& Horse, int WeaponId, int AimYawDeg, int HorseYawDeg)
{
    const int Slot = ArcSlot(WeaponId);
    if (Slot < 0 || (Horse.WeaponsMask & (1u << WeaponId)) == 0u)
        return false;
    const int Relative = NormalizeDeg(AimYawDeg - HorseYawDeg);
    return Relative >= Horse.ArcMin[Slot] && Relative <= Horse.ArcMax[Slot];
}

// An authored ride: gaits rise in speed, wind thresholds make sense, the
// weapons are the katana, yumi and yari with arcs inside a turn, and the yumi
// shoots to the left.
constexpr bool HorseValid(const FHorse& Horse)
{
    if (Horse.MaxGait == EGait::Halt || Horse.SpeedCmS[0] != 0 || Horse.LockoutBelow < 0 ||
        Horse.LockoutBelow >= Horse.RecoverAt || Horse.RecoverAt > 100 || Horse.FearRecoverMs < 0 ||
        (Horse.WeaponsMask & ~((1u << ArcWeapons[0]) | (1u << ArcWeapons[1]) | (1u << ArcWeapons[2]))) != 0u)
        return false;
    for (int Gait = 1; Gait < GaitCount; ++Gait)
        if (Horse.SpeedCmS[Gait] <= Horse.SpeedCmS[Gait - 1])
            return false;
    for (int Slot = 0; Slot < 3; ++Slot)
        if ((Horse.WeaponsMask & (1u << ArcWeapons[Slot])) != 0u &&
            (Horse.ArcMin[Slot] < -180 || Horse.ArcMin[Slot] >= Horse.ArcMax[Slot] || Horse.ArcMax[Slot] > 180))
            return false;
    return (Horse.WeaponsMask & (1u << ArcWeapons[1])) == 0u || Horse.ArcMax[1] <= 15;
}
} // namespace SoraMountRules
