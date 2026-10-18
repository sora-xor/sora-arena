#pragma once

// Offline campaign fieldcraft rules, shared by USoraFieldcraft, the hero,
// the companions and a host-compiled driver
// (scripts/unreal/test_fieldcraft_rules.py): the people who walk and fight
// beside Nyaakoto (escorted parties and allies, who can be downed, revived,
// hidden on his signal and lost), work held at a point (snuffing a lamp,
// cutting a collar, opening a cell, raising the downed), lamps that go dark
// and relight, breath in the water, grip on a wall, thrown stones, a carried
// candle, vaulting low cover, the kusarigama's weighted chain, the
// rotating volley ranks the hero commands and their smoke, seizure nets on
// what the hero guards, searchlights, a one-shot bell lure, ladders onto the
// roofs and the League riders who charge beside him. Time is
// integer milliseconds, distance integer centimetres and fractions permille,
// so no rule depends on a floating-point frame boundary. No Unreal headers
// belong here.
namespace SoraFieldcraftRules
{
constexpr int Permille = 1000;

constexpr int Clamp(int Value, int Low, int High)
{
    return Value < Low ? Low : Value > High ? High : Value;
}

// ---------------------------------------------------------------------------
// Companions. Up: walking, working or fighting. Hidden: crouched still at a
// hide spot on the hero's signal (or when a patrol finds the group). Down: a
// blow emptied its health; Interact held beside it for ReviveMs raises it, a
// healing lance round raises it LanceReviveMs later, and after BleedoutMs
// down it dies. Bound: collared or locked in a cell until the hero frees it.
// ---------------------------------------------------------------------------
enum class EState : unsigned char { Up, Hidden, Down, Dead, Bound };
enum class EChange : unsigned char { None, Downed, Revived, Died, Freed };

struct FCompanionRules
{
    int Health;
    // A blow that empties its health downs it. One that is not downable
    // cannot be hurt at all (a guide, a bystander the story needs).
    bool Downable;
    int ReviveMs;
    // Down this long it dies; 0: it waits to be raised however long it takes.
    int BleedoutMs;
    // A healing lance round on a downed companion raises it this long after; 0: no effect.
    int LanceReviveMs;
    // Collared or behind a cell door at the start; Interact held FreeMs frees it.
    bool Bound;
    int FreeMs;
};

// It rises with this share of its health.
constexpr int ReviveHealthPermille = 500;

struct FCompanion
{
    EState State;
    int Health;
    int DownMs;
    // Unbroken ms of Interact held beside it (reviving, or freeing it).
    int HeldMs;
    // Ms until a healing lance round raises it, or -1.
    int LanceMs;
};

constexpr FCompanion Fresh(const FCompanionRules& Rules)
{
    return {Rules.Bound ? EState::Bound : EState::Up, Rules.Health, 0, 0, -1};
}

constexpr bool IsStanding(const FCompanion& Companion)
{
    return Companion.State == EState::Up || Companion.State == EState::Hidden;
}

constexpr bool RulesValid(const FCompanionRules& Rules)
{
    return Rules.Health > 0 && Rules.ReviveMs > 0 && Rules.BleedoutMs >= 0 && Rules.LanceReviveMs >= 0 &&
        (!Rules.Bound || Rules.FreeMs > 0) && (Rules.Downable || Rules.BleedoutMs == 0);
}

// A blow of Damage. A bound or hidden companion is struck as a standing one;
// a downed or dead one takes nothing more.
constexpr EChange Hit(FCompanion& Companion, const FCompanionRules& Rules, int Damage)
{
    if (Damage <= 0 || !Rules.Downable || Companion.State == EState::Down || Companion.State == EState::Dead)
        return EChange::None;
    Companion.Health = Companion.Health > Damage ? Companion.Health - Damage : 0;
    if (Companion.Health > 0)
        return EChange::None;
    Companion.State = EState::Down;
    Companion.DownMs = 0;
    Companion.HeldMs = 0;
    Companion.LanceMs = -1;
    return EChange::Downed;
}

// A healing lance round: true when it starts raising a downed companion.
constexpr bool Lance(FCompanion& Companion, const FCompanionRules& Rules)
{
    if (Companion.State != EState::Down || Rules.LanceReviveMs <= 0 || Companion.LanceMs >= 0)
        return false;
    Companion.LanceMs = Rules.LanceReviveMs;
    return true;
}

// One step: Held is Interact held beside it this step. A downed companion
// is raised by an unbroken hold or a lance round, or bleeds out; a bound one
// is freed by an unbroken hold. Letting go starts the hold over.
constexpr EChange Tick(FCompanion& Companion, const FCompanionRules& Rules, int DtMs, bool Held)
{
    if (DtMs <= 0)
        return EChange::None;
    if (Companion.State == EState::Bound)
    {
        Companion.HeldMs = Held ? Companion.HeldMs + DtMs : 0;
        if (Companion.HeldMs < Rules.FreeMs)
            return EChange::None;
        Companion.State = EState::Up;
        Companion.HeldMs = 0;
        return EChange::Freed;
    }
    if (Companion.State != EState::Down)
        return EChange::None;
    Companion.DownMs += DtMs;
    Companion.HeldMs = Held ? Companion.HeldMs + DtMs : 0;
    if (Companion.LanceMs >= 0)
        Companion.LanceMs = Companion.LanceMs > DtMs ? Companion.LanceMs - DtMs : 0;
    if (Companion.HeldMs >= Rules.ReviveMs || Companion.LanceMs == 0)
    {
        Companion.State = EState::Up;
        Companion.Health = Rules.Health * ReviveHealthPermille / Permille;
        Companion.DownMs = 0;
        Companion.HeldMs = 0;
        Companion.LanceMs = -1;
        return EChange::Revived;
    }
    if (Rules.BleedoutMs > 0 && Companion.DownMs >= Rules.BleedoutMs)
    {
        Companion.State = EState::Dead;
        return EChange::Died;
    }
    return EChange::None;
}

// The hero's signal (bible §12.2 hide_on_signal): a standing companion hides
// where it is sent, a hidden one goes on. Nothing else answers it.
constexpr bool Signal(FCompanion& Companion, bool Hide)
{
    if (Companion.State != (Hide ? EState::Up : EState::Hidden))
        return false;
    Companion.State = Hide ? EState::Hidden : EState::Up;
    return true;
}

// An escorted party walks while the hero keeps up, and only when every one
// of it is free, standing and not hidden.
constexpr bool PartyWalks(bool HeroNear, bool AnyHidden, bool AnyDown, bool AnyBound)
{
    return HeroNear && !AnyHidden && !AnyDown && !AnyBound;
}

// A hidden companion is seen only this close.
constexpr int HiddenSightCm = 300;

// ---------------------------------------------------------------------------
// Work held at a point: an unbroken hold of NeedMs completes it; letting go
// starts it over.
// ---------------------------------------------------------------------------
constexpr bool Hold(int& HeldMs, bool Held, int DtMs, int NeedMs)
{
    HeldMs = Held && DtMs > 0 ? HeldMs + DtMs : Held ? HeldMs : 0;
    if (!Held || HeldMs < NeedMs)
        return false;
    HeldMs = 0;
    return true;
}

// ---------------------------------------------------------------------------
// Lamps. A lit lamp goes dark when snuffed (held), smothered (a brazier) or
// its cable is cut by an arrow or round; one with a relight time comes back
// on after it. A lamp that cannot be put out never goes dark.
// ---------------------------------------------------------------------------
struct FLamp
{
    bool Lit;
    int DarkMs;
};

constexpr bool Snuff(FLamp& Lamp, bool Extinguishable)
{
    if (!Lamp.Lit || !Extinguishable)
        return false;
    Lamp.Lit = false;
    Lamp.DarkMs = 0;
    return true;
}

// True when the lamp comes back on this step.
constexpr bool LampTick(FLamp& Lamp, int RelightMs, int DtMs)
{
    if (Lamp.Lit || DtMs <= 0)
        return false;
    Lamp.DarkMs += DtMs;
    if (RelightMs <= 0 || Lamp.DarkMs < RelightMs)
        return false;
    Lamp.Lit = true;
    Lamp.DarkMs = 0;
    return true;
}

// ---------------------------------------------------------------------------
// Water (ch06.b02 traversal swim). On the surface the hero swims at its pace
// and his strokes are heard; diving he is hidden and silent, spends breath
// and, with none left, takes DrownHpPerSecond. Breath comes back to full in
// RecoverMs on the surface. No weapon is used in the water.
// ---------------------------------------------------------------------------
struct FWaterRules
{
    int SurfaceCmS;
    int DiveCmS;
    int BreathMs;
    int RecoverMs;
    int DrownHpPerSecond;
};

struct FBreath
{
    int BreathMs;
    // Sub-unit carries so the same time costs the same breath and health at any frame rate.
    int RecoverCarry;
    int DrownCarry;
};

constexpr FBreath FullBreath(const FWaterRules& Rules)
{
    return {Rules.BreathMs, 0, 0};
}

constexpr bool WaterValid(const FWaterRules& Rules)
{
    return Rules.SurfaceCmS > 0 && Rules.DiveCmS > 0 && Rules.BreathMs > 0 && Rules.RecoverMs > 0 && Rules.DrownHpPerSecond >= 0;
}

// One step; returns the drowning damage it deals.
constexpr int Breathe(FBreath& Breath, const FWaterRules& Rules, bool Diving, int DtMs)
{
    if (DtMs <= 0)
        return 0;
    if (!Diving)
    {
        Breath.DrownCarry = 0;
        const long long Total = Breath.RecoverCarry + static_cast<long long>(DtMs) * Rules.BreathMs;
        const long long Gain = Total / Rules.RecoverMs;
        Breath.RecoverCarry = static_cast<int>(Total - Gain * Rules.RecoverMs);
        Breath.BreathMs = Breath.BreathMs + Gain >= Rules.BreathMs ? Rules.BreathMs : Breath.BreathMs + static_cast<int>(Gain);
        if (Breath.BreathMs == Rules.BreathMs)
            Breath.RecoverCarry = 0;
        return 0;
    }
    Breath.RecoverCarry = 0;
    const int Spent = Breath.BreathMs < DtMs ? Breath.BreathMs : DtMs;
    Breath.BreathMs -= Spent;
    const int Choking = DtMs - Spent;
    if (Choking <= 0)
        return 0;
    const long long Total = Breath.DrownCarry + static_cast<long long>(Choking) * Rules.DrownHpPerSecond;
    const long long Damage = Total / 1000;
    Breath.DrownCarry = static_cast<int>(Total - Damage * 1000);
    return static_cast<int>(Damage);
}

// ---------------------------------------------------------------------------
// Climbing (ch06.b03 traversal climb): Holds evenly up a face HeightCm tall.
// Each hold reached, up or down, costs GripPerHold; resting at a ledge hold
// gives back RegenPerSecond; with too little grip for the next hold, or none
// at all, he falls. A fall over HurtCm hurts, one over LethalCm kills.
// ---------------------------------------------------------------------------
constexpr int GripMax = 100;

struct FClimbRules
{
    int Holds;
    int HeightCm;
    int GripPerHold;
    int RegenPerSecond;
    // Holds that are ledges, bit N for hold N (hold 0 is the ground).
    unsigned LedgeMask;
    int HurtCm;
    int HurtHp;
    int LethalCm;
};

struct FClimb
{
    int Hold;
    // Grip in thousandths of a point.
    int GripMilli;
};

constexpr bool ClimbValid(const FClimbRules& Rules)
{
    return Rules.Holds > 0 && Rules.Holds < 32 && Rules.HeightCm > 0 && Rules.GripPerHold > 0 &&
        Rules.GripPerHold <= GripMax && Rules.RegenPerSecond >= 0 && (Rules.LedgeMask & 1u) == 0u &&
        (Rules.LedgeMask >> Rules.Holds) == 0u && Rules.HurtCm > 0 && Rules.HurtCm < Rules.LethalCm && Rules.HurtHp > 0;
}

constexpr FClimb StartClimb()
{
    return {0, GripMax * 1000};
}

constexpr int HoldHeightCm(const FClimbRules& Rules, int Hold)
{
    return Rules.HeightCm * Clamp(Hold, 0, Rules.Holds) / Rules.Holds;
}

constexpr bool AtLedge(const FClimbRules& Rules, const FClimb& Climb)
{
    return Climb.Hold > 0 && Climb.Hold < Rules.Holds && (Rules.LedgeMask & (1u << Climb.Hold)) != 0u;
}

enum class EReach : unsigned char { Moved, Top, Ground, Fell };

// Reaching for the next hold up (+1) or down (-1).
constexpr EReach Reach(FClimb& Climb, const FClimbRules& Rules, int Step)
{
    const int Cost = Rules.GripPerHold * 1000;
    if (Climb.GripMilli < Cost)
    {
        Climb.GripMilli = 0;
        return EReach::Fell;
    }
    Climb.GripMilli -= Cost;
    Climb.Hold = Clamp(Climb.Hold + (Step < 0 ? -1 : 1), 0, Rules.Holds);
    return Climb.Hold == Rules.Holds ? EReach::Top : Climb.Hold == 0 ? EReach::Ground : EReach::Moved;
}

// Resting at a ledge gives grip back.
constexpr void Rest(FClimb& Climb, const FClimbRules& Rules, int DtMs)
{
    if (DtMs > 0 && AtLedge(Rules, Climb))
        Climb.GripMilli = Clamp(Climb.GripMilli + Rules.RegenPerSecond * DtMs, 0, GripMax * 1000);
}

// A fall's damage: 0, HurtHp, or -1 for a lethal fall.
constexpr int FallDamage(const FClimbRules& Rules, int FallCm)
{
    return FallCm > Rules.LethalCm ? -1 : FallCm > Rules.HurtCm ? Rules.HurtHp : 0;
}

// ---------------------------------------------------------------------------
// Tsubute (礫): stones carried up to Max, refilled at a rubble pile, thrown
// one at a time. Where one lands the guards hear it (StoneNoiseCm) and go to
// look, but a stone alone never convinces them the hero is there.
// ---------------------------------------------------------------------------
constexpr bool Throw(int& Carried)
{
    if (Carried <= 0)
        return false;
    --Carried;
    return true;
}

constexpr int Refill(int Carried, int Max)
{
    return Carried < Max ? Max : Carried;
}

// The most awareness (x1000 of the full meter) a lure's noise can leave a
// guard with: enough to send it looking, never enough to call the hero found.
constexpr int LureCeilingPermille = 900;

constexpr int LureImpulsePermille(int HeardPermille, int AwarenessPermille)
{
    const int Room = LureCeilingPermille - Clamp(AwarenessPermille, 0, Permille);
    return Clamp(HeardPermille, 0, Room > 0 ? Room : 0);
}

// ---------------------------------------------------------------------------
// The carried candle (ch06.b08 light_carried): lit it gives the hero away,
// cupped (Guard held) less so, but work goes at a reduced rate.
// ---------------------------------------------------------------------------
struct FCandle
{
    int VisibilityPermille;
    int CuppedVisibilityPermille;
    int CuppedRatePermille;
};

constexpr int CandleVisibility(const FCandle& Candle, bool Cupped)
{
    return Cupped ? Candle.CuppedVisibilityPermille : Candle.VisibilityPermille;
}

constexpr int WorkRatePermille(const FCandle& Candle, bool Cupped)
{
    return Cupped ? Candle.CuppedRatePermille : Permille;
}

// ---------------------------------------------------------------------------
// Vaulting: Jump facing an obstacle whose top stands between the knee and the
// shoulder, and which is shallow enough to cross, carries the hero over it.
// ---------------------------------------------------------------------------
constexpr int VaultLowCm = 45;
constexpr int VaultHighCm = 165;
constexpr int VaultDepthCm = 140;
constexpr int VaultMs = 450;

constexpr bool CanVault(int TopCm, int DepthCm, bool LandingClear)
{
    return TopCm >= VaultLowCm && TopCm <= VaultHighCm && DepthCm > 0 && DepthCm <= VaultDepthCm && LandingClear;
}

// ---------------------------------------------------------------------------
// The kusarigama's weighted chain (分銅鎖): a strike at an opponent beyond the
// sickle's reach, within ChainReachCm, casts the weight. It binds a blade
// (the opponent staggered, its guard down, for SnareMs), pulls a shield's
// rim aside (its shield open for ShieldOpenMs) or wraps a drone's rotors and
// drags it down (DroneDamagePermille of its health).
// ---------------------------------------------------------------------------
enum class ESnare : unsigned char { None, Blade, Shield, Drone };

constexpr int ChainReachCm = 620;
constexpr int SnareMs = 2200;
constexpr int ShieldOpenMs = 2400;
constexpr int DroneDamagePermille = 600;
constexpr int ChainWindupMs = 260;
constexpr int ChainRecoveryMs = 700;

constexpr ESnare Snare(int DistanceCm, int SickleReachCm, bool Flying, bool Shielded)
{
    if (DistanceCm <= SickleReachCm || DistanceCm > ChainReachCm)
        return ESnare::None;
    return Flying ? ESnare::Drone : Shielded ? ESnare::Shield : ESnare::Blade;
}
// ---------------------------------------------------------------------------
// Rotating volley ranks (輪番撃ち, ch08 volley_command). Command held marks a
// ring at the aim point; released, the next ready rank fires OrderDelayMs
// later and goes back to reload for CycleMs while the next steps up. A volley
// never misses: VolleyDamage split evenly across up to VolleyTargets
// unshielded opponents in the ring, nearest first (the remainder to the
// nearest), each shield in it staggered ShieldStaggerMs and each walker
// struck for WalkerPermille of its health and staggered WalkerStaggerMs.
// A rank with gunners down fires in proportion.
// ---------------------------------------------------------------------------
constexpr int MaxRanks = 4;
constexpr int VolleyDamage = 288;
constexpr int VolleyTargets = 4;
constexpr int ShieldStaggerMs = 2000;
constexpr int WalkerPermille = 80;
constexpr int WalkerStaggerMs = 1000;

struct FVolleyRules
{
    int Ranks;
    int OrderDelayMs;
    int CycleMs;
    int RadiusCm;
    int RangeCm;
};

struct FVolley
{
    // World ms each rank is ready again; which rank stands in front; orders given.
    int ReadyAtMs[MaxRanks];
    int Front;
    int Orders;
};

constexpr bool VolleyValid(const FVolleyRules& Rules)
{
    return Rules.Ranks > 0 && Rules.Ranks <= MaxRanks && Rules.OrderDelayMs >= 0 && Rules.CycleMs > 0 &&
        Rules.RadiusCm > 0 && Rules.RangeCm > 0;
}

constexpr FVolley StartVolley()
{
    return {{0, 0, 0, 0}, 0, 0};
}

// An order at NowMs: the front rank, if it is loaded; it goes back to reload
// and the next rank steps up. -1 when the front rank is still loading.
constexpr int Order(FVolley& Volley, const FVolleyRules& Rules, int NowMs)
{
    const int Rank = Volley.Front;
    if (Rank < 0 || Rank >= Rules.Ranks || NowMs < Volley.ReadyAtMs[Rank])
        return -1;
    Volley.ReadyAtMs[Rank] = NowMs + Rules.CycleMs;
    Volley.Front = (Rank + 1) % Rules.Ranks;
    ++Volley.Orders;
    return Rank;
}

// Each of Targets unshielded opponents' share of a volley from Standing of
// PerRank gunners, nearest first: Share(0) is the nearest's.
constexpr int VolleyShare(int Targets, int Standing, int PerRank, int Nearest)
{
    if (Targets <= 0 || Standing <= 0 || PerRank <= 0 || Nearest < 0 || Nearest >= Targets)
        return 0;
    const int Count = Targets < VolleyTargets ? Targets : VolleyTargets;
    if (Nearest >= Count)
        return 0;
    const int Total = VolleyDamage * (Standing < PerRank ? Standing : PerRank) / PerRank;
    return Total / Count + (Nearest == 0 ? Total % Count : 0);
}

// The white smoke bank a volley leaves hides its ring for this long, for both sides.
constexpr int SmokeMs = 4000;

// Easy's auto-order (ch08 easy_auto_order): with the front rank loaded and
// the hero not marking, the ranks fire on the opponent nearest the hero
// within reach, the ring on it.
constexpr bool AutoOrders(bool Easy, bool Enabled, bool FrontLoaded, bool Marking, bool TargetInReach)
{
    return Easy && Enabled && FrontLoaded && !Marking && TargetInReach;
}

// ---------------------------------------------------------------------------
// Seizure nets (差押え網, ch02.b08, ch04.b10, ch04.b12). A drone over a free
// quarry (a pack horse, the ox, a planter) locks it for WindupMs under a cyan
// ring, then drops its net. A netted quarry stands where it is, and a tied
// string or a cart halts with it, until the hero cuts the net (Interact held
// CutMs beside it, or a blade from the saddle) or brings its tether drone
// down. Left netted HaulMs it is hauled away (0: never). A lock breaks when
// its drone is downed or gone. A load freed is let be NetRearmMs (below).
// ---------------------------------------------------------------------------
enum class ENet : unsigned char { Free, Locking, Netted, Taken };
enum class ENetChange : unsigned char { None, Netted, Freed, Taken };

struct FNetRules
{
    int WindupMs;
    int HaulMs;
    int CutMs;
};

struct FNet
{
    ENet State;
    // Ms into the lock, or netted.
    int Ms;
    // Unbroken ms of the hero's hand on the net.
    int HeldMs;
};

constexpr FNet FreeNet()
{
    return {ENet::Free, 0, 0};
}

constexpr bool NetValid(const FNetRules& Rules)
{
    return Rules.WindupMs > 0 && Rules.HaulMs >= 0 && Rules.CutMs > 0;
}

// A drone over a free quarry begins its lock.
constexpr bool BeginLock(FNet& Net)
{
    if (Net.State != ENet::Free)
        return false;
    Net = {ENet::Locking, 0, 0};
    return true;
}

// Its drone is downed or gone: a lock breaks and a net goes slack.
constexpr ENetChange Loosen(FNet& Net)
{
    const bool Netted = Net.State == ENet::Netted;
    if (Net.State == ENet::Locking || Netted)
        Net = FreeNet();
    return Netted ? ENetChange::Freed : ENetChange::None;
}

// A blade from the saddle cuts a net at once.
constexpr bool CutNet(FNet& Net)
{
    if (Net.State != ENet::Netted)
        return false;
    Net = FreeNet();
    return true;
}

// One step: Held is the hero's hand on the net (Interact held beside it).
constexpr ENetChange NetTick(FNet& Net, const FNetRules& Rules, int DtMs, bool Held)
{
    if (DtMs <= 0)
        return ENetChange::None;
    if (Net.State == ENet::Locking)
    {
        Net.Ms += DtMs;
        if (Net.Ms < Rules.WindupMs)
            return ENetChange::None;
        Net = {ENet::Netted, 0, 0};
        return ENetChange::Netted;
    }
    if (Net.State != ENet::Netted)
        return ENetChange::None;
    Net.HeldMs = Held ? Net.HeldMs + DtMs : 0;
    if (Net.HeldMs >= Rules.CutMs)
    {
        Net = FreeNet();
        return ENetChange::Freed;
    }
    Net.Ms += DtMs;
    if (Rules.HaulMs <= 0 || Net.Ms < Rules.HaulMs)
        return ENetChange::None;
    Net.State = ENet::Taken;
    Net.HeldMs = 0;
    return ENetChange::Taken;
}

// A drone locks a quarry it hovers within this reach of (2D).
constexpr int NetReachCm = 320;

// A drone whose net is cut (by hand or from the saddle) reloads its launcher
// for NetRearmMs before it can lock anything again, as the Credit House's
// seizure-net launcher does (ch04.b16: 9 s); with its tether brought down it
// is gone. A load freed either way is not locked again for as long, so a cut
// buys the string, the cart or the planter that much. The ms left after a
// step of DtMs:
constexpr int NetRearmMs = 9000;
constexpr int Rearm(int LeftMs, int DtMs)
{
    return DtMs <= 0 ? LeftMs : LeftMs > DtMs ? LeftMs - DtMs : 0;
}

// A blade from the saddle reaches a netted pack horse this far off the rider's
// flank; the ride's own arc says which flank (ch02.b08: the katana to the right).
constexpr int SaddleCutCm = 420;

// ---------------------------------------------------------------------------
// Searchlights (探照灯, ch06.b02). A lamp on a wall swings its beam SweepDeg
// across its centre line and back every PeriodMs, lighting a spot SpotCm
// across where the beam meets the water or the road. A head in the spot for
// SuspiciousMs sends the guards to look; for AlertMs, it raises the zone's
// alarm. Out of the spot the count runs down as fast as it built. Once the
// hero is detected the lights lock on the last place seen for LockMs.
// ---------------------------------------------------------------------------
struct FSearchlightRules
{
    int SweepDeg;
    int PeriodMs;
    int SpotCm;
    int SuspiciousMs;
    int AlertMs;
    int LockMs;
};

constexpr bool SearchlightValid(const FSearchlightRules& Rules)
{
    return Rules.SweepDeg > 0 && Rules.SweepDeg <= 180 && Rules.PeriodMs >= 2 && Rules.SpotCm > 0 &&
        Rules.SuspiciousMs > 0 && Rules.AlertMs > Rules.SuspiciousMs && Rules.LockMs >= 0;
}

// The beam's bearing at world time NowMs, in thousandths of a degree off its
// centre line: from -Sweep/2 to +Sweep/2 over the first half of the period
// and back over the second, shifted by PhaseMs.
constexpr int BeamMilliDeg(const FSearchlightRules& Rules, int NowMs, int PhaseMs)
{
    const int Period = Rules.PeriodMs;
    int At = (NowMs % Period + PhaseMs % Period) % Period;
    if (At < 0)
        At += Period;
    const int Half = Period / 2;
    const long long Along = At <= Half ? At : Period - At;
    const long long Sweep = static_cast<long long>(Rules.SweepDeg) * 1000;
    return static_cast<int>(-Sweep / 2 + Sweep * Along / Half);
}

enum class ESpotted : unsigned char { None, Suspicious, Alert };

// The hero's time in the spot: it builds while his head is in it and runs
// down out of it; crossing SuspiciousMs, then AlertMs, reports once each.
constexpr ESpotted Spotted(int& InSpotMs, bool InSpot, int DtMs, const FSearchlightRules& Rules)
{
    if (DtMs <= 0)
        return ESpotted::None;
    const int Before = InSpotMs;
    InSpotMs = InSpot ? (InSpotMs + DtMs > Rules.AlertMs ? Rules.AlertMs : InSpotMs + DtMs)
                      : (InSpotMs > DtMs ? InSpotMs - DtMs : 0);
    if (Before < Rules.AlertMs && InSpotMs >= Rules.AlertMs)
        return ESpotted::Alert;
    if (Before < Rules.SuspiciousMs && InSpotMs >= Rules.SuspiciousMs)
        return ESpotted::Suspicious;
    return ESpotted::None;
}

// ---------------------------------------------------------------------------
// A one-shot lure (ch07.b04's temple bell): a stone that strikes it rings it
// once, and every guard within RadiusCm that has not placed the hero
// (unaware or suspicious) goes to it and looks it over for HoldMs.
// ---------------------------------------------------------------------------
struct FBellRules
{
    int RadiusCm;
    int Uses;
    int HoldMs;
};

constexpr bool RingBell(int& UsesLeft)
{
    if (UsesLeft <= 0)
        return false;
    --UsesLeft;
    return true;
}

// A stone within this of the bell's lip strikes it.
constexpr int BellStrikeCm = 110;

// ---------------------------------------------------------------------------
// A cook-fire (ch03.b14 竈): at each of the hold's fire_out progress marks
// the next fire gutters, and the hold's progress waits until the hero relights
// it (Interact held RelightMs at it).
// ---------------------------------------------------------------------------
// The fire that gutters at the Mark-th mark (0 first), of Fires.
constexpr int GutteringFire(int Mark, int Fires)
{
    return Fires > 0 && Mark >= 0 ? Mark % Fires : -1;
}

// Marks passed between two progress readings (permille), for OutAt ascending.
constexpr int MarksCrossed(const int* OutAt, int Marks, int Before, int After)
{
    int Crossed = 0;
    for (int Mark = 0; Mark < Marks; ++Mark)
        Crossed += Before < OutAt[Mark] && After >= OutAt[Mark];
    return Crossed;
}

// ---------------------------------------------------------------------------
// Ladders onto the board roofs (ch03.b03, b10): Jump at a ladder's foot,
// facing it, climbs it at LadderCmS and steps off onto the roof. Coming down
// off a roof, a drop of more than DropNoiseOverCm lands with a thud heard
// DropNoiseCm away, unless it lands on straw.
// ---------------------------------------------------------------------------
constexpr int LadderCmS = 150;
constexpr int DropNoiseOverCm = 200;

constexpr bool LandingHeard(int DropCm, bool OnStraw)
{
    return DropCm > DropNoiseOverCm && !OnStraw;
}

// ---------------------------------------------------------------------------
// The League's charge (ch08.b02). The pack of riders runs the causeway at
// PaceCmS in a column of twos; when the hero falls more than LagCm behind his
// place in it the pack eases off, up to CatchUpCmS, but it never waits. A seal
// stake bars the causeway until broken: a yari thrust from a horse at a canter
// or faster breaks it, or two arrows; a stake the hero leaves standing is
// broken by the riders behind StakeBreakMs after the pack reaches it. Each
// rider strikes an opponent on the causeway within RiderReachCm once every
// RiderStrikeMs.
// ---------------------------------------------------------------------------
constexpr int LagCm = 3000;
constexpr int RiderReachCm = 350;
constexpr int RiderStrikeMs = 1500;
constexpr int RiderStrikeDamage = 40;
constexpr int StakeArrows = 2;

// The pack's pace with the hero Lag cm behind his place in it: full pace
// within LagCm, easing by up to CatchUp as he falls another LagCm behind.
constexpr int PackPaceCmS(int PaceCmS, int CatchUpCmS, int Lag)
{
    const int Over = Lag - LagCm;
    if (Over <= 0)
        return PaceCmS;
    const int Ease = Over >= LagCm ? CatchUpCmS : CatchUpCmS * Over / LagCm;
    return PaceCmS - Ease;
}

enum class EStakeHit : unsigned char { None, Yari, Arrow };

// A hit on a standing stake: true when it breaks. Arrows counts the arrows it has taken.
constexpr bool StakeStruck(int& Arrows, EStakeHit Hit, bool CanterOrFaster)
{
    if (Hit == EStakeHit::Yari)
        return CanterOrFaster;
    if (Hit != EStakeHit::Arrow)
        return false;
    ++Arrows;
    return Arrows >= StakeArrows;
}

} // namespace SoraFieldcraftRules
