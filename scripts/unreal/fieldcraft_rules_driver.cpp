#include "SoraArmsRules.h"
#include "SoraFieldcraftRules.h"
#include <cassert>
#include <initializer_list>

using namespace SoraFieldcraftRules;

namespace
{
constexpr int Frame = 17;

unsigned Mask(std::initializer_list<int> Ids)
{
    unsigned Bits = 0u;
    for (const int Id : Ids)
        Bits |= 1u << Id;
    return Bits;
}

void Arms()
{
    using namespace SoraArmsRules;
    // The ring holds all 21 arms once, grouped.
    unsigned Seen = 0u;
    for (const int Id : Ring)
    {
        assert(Id >= 0 && Id < ArmsCount && (Seen & (1u << Id)) == 0u);
        Seen |= 1u << Id;
    }
    assert(Seen == (1u << ArmsCount) - 1u);
    assert(GroupStart[0] == 0 && GroupStart[GroupCount] == ArmsCount);
    assert(GroupOf(0) == 0 && GroupOf(4) == 0 && GroupOf(10) == 0);
    assert(GroupOf(19) == 1 && GroupOf(20) == 1 && GroupOf(12) == 1);
    assert(GroupOf(18) == 2);
    for (const int Id : {5, 14, 1, 11, 9, 3, 13})
        assert(GroupOf(Id) == 3);
    for (const int Id : {2, 6, 8})
        assert(GroupOf(Id) == 4);
    for (const int Id : {7, 15, 16, 17})
        assert(GroupOf(Id) == 5);
    assert(GroupOf(21) == -1 && GroupOf(-1) == -1);

    // Ring stepping skips what he cannot hold and wraps.
    const unsigned Early = Mask({0, 18, 19});
    assert(Next(Early, 0, 1) == 19 && Next(Early, 19, 1) == 18 && Next(Early, 18, 1) == 0);
    assert(Next(Early, 0, -1) == 18 && Next(Early, 18, -1) == 19);
    assert(Next(Mask({0}), 0, 1) == 0);
    assert(Next(0u, 0, 1) == -1);
    // An arm outside the mask starts from its own place in the ring.
    assert(Next(Early, 4, 1) == 19 && Next(Early, 4, -1) == 0);
    int Out[ArmsCount] = {};
    assert(HeldRing(Early, Out) == 3 && Out[0] == 0 && Out[1] == 19 && Out[2] == 18);
    assert(HeldRing((1u << ArmsCount) - 1u, Out) == ArmsCount && Out[20] == 17);

    // A group key: the remembered arm, then the group's next, and the first when nothing is remembered.
    const unsigned Late = (1u << ArmsCount) - 1u;
    assert(Pick(Late, 0, 18, -1) == 0);
    assert(Pick(Late, 0, 0, -1) == 4 && Pick(Late, 0, 4, -1) == 10 && Pick(Late, 0, 10, -1) == 0);
    assert(Pick(Late, 3, 0, 11) == 11);
    assert(Pick(Late, 3, 0, 19) == 5);
    assert(Pick(Mask({0, 19}), 1, 0, -1) == 19 && Pick(Mask({0, 19}), 1, 19, -1) == 19);
    assert(Pick(Mask({0}), 3, 0, -1) == -1);
    assert(Pick(Late, 6, 0, -1) == -1 && Pick(Late, -1, 0, -1) == -1);
    // A remembered arm now out of reach (a load, the saddle) gives way to the group's first.
    assert(Pick(Mask({0, 5, 1}), 3, 0, 14) == 5);

    // Wheel sectors are centred on the top and run clockwise.
    assert(Sector(0, 4) == 0 && Sector(44999, 4) == 0 && Sector(45000, 4) == 1 && Sector(90000, 4) == 1);
    assert(Sector(-1, 4) == 0 && Sector(315000, 4) == 0 && Sector(314999, 4) == 3);
    assert(Sector(0, 0) == -1 && Sector(123456, 1) == 0);
    assert(Sector(360000 / 21 * 20, 21) == 20 && Sector(720000, 21) == 0);
}

void Companions()
{
    const FCompanionRules Escort{100, true, 2000, 8000, 0, false, 0};
    assert(RulesValid(Escort));
    FCompanion Person = Fresh(Escort);
    assert(Person.State == EState::Up && Person.Health == 100 && IsStanding(Person));
    assert(Hit(Person, Escort, 60) == EChange::None && Person.Health == 40);
    assert(Hit(Person, Escort, 60) == EChange::Downed && Person.State == EState::Down && Person.Health == 0);
    // Nothing more lands on the downed.
    assert(Hit(Person, Escort, 60) == EChange::None && Person.State == EState::Down);
    // A hold let go starts over; an unbroken one raises them at half health.
    for (int Ms = 0; Ms < 1500; Ms += Frame)
        assert(Tick(Person, Escort, Frame, true) == EChange::None);
    assert(Tick(Person, Escort, Frame, false) == EChange::None && Person.HeldMs == 0);
    EChange Change = EChange::None;
    int Held = 0;
    for (; Held < 2100 && Change == EChange::None; Held += Frame)
        Change = Tick(Person, Escort, Frame, true);
    assert(Change == EChange::Revived && Held >= 2000 && Held < 2000 + Frame * 2);
    assert(Person.State == EState::Up && Person.Health == 50 && Person.DownMs == 0);
    // Unattended, the downed bleed out after BleedoutMs.
    assert(Hit(Person, Escort, 50) == EChange::Downed);
    int Down = 0;
    for (Change = EChange::None; Change == EChange::None; Down += Frame)
        Change = Tick(Person, Escort, Frame, false);
    assert(Change == EChange::Died && Person.State == EState::Dead && Down >= 8000 && Down < 8000 + Frame);
    assert(Tick(Person, Escort, Frame, true) == EChange::None && Hit(Person, Escort, 5) == EChange::None);

    // Allies wait to be raised however long it takes; guides cannot be hurt.
    const FCompanionRules Ally{120, true, 3000, 0, 0, false, 0};
    FCompanion Pupil = Fresh(Ally);
    assert(Hit(Pupil, Ally, 500) == EChange::Downed);
    for (int Ms = 0; Ms < 120000; Ms += 1000)
        assert(Tick(Pupil, Ally, 1000, false) == EChange::None);
    assert(Pupil.State == EState::Down);
    const FCompanionRules Guide{100, false, 3000, 0, 0, false, 0};
    FCompanion Kohagi = Fresh(Guide);
    assert(Hit(Kohagi, Guide, 1000) == EChange::None && Kohagi.Health == 100);
    assert(!RulesValid({100, false, 3000, 5000, 0, false, 0}));

    // The healing lance raises the downed LanceReviveMs after its round, once.
    const FCompanionRules Prisoner{150, true, 3000, 30000, 1000, false, 0};
    FCompanion Held8 = Fresh(Prisoner);
    assert(!Lance(Held8, Prisoner));
    assert(Hit(Held8, Prisoner, 150) == EChange::Downed);
    assert(Lance(Held8, Prisoner) && !Lance(Held8, Prisoner));
    int Lanced = 0;
    for (Change = EChange::None; Change == EChange::None; Lanced += Frame)
        Change = Tick(Held8, Prisoner, Frame, false);
    assert(Change == EChange::Revived && Lanced >= 1000 && Lanced < 1000 + Frame);

    // The bound are freed by an unbroken hold, and only then stand.
    const FCompanionRules Collared{120, true, 4000, 4000, 0, true, 2000};
    assert(RulesValid(Collared));
    FCompanion Okinu = Fresh(Collared);
    assert(Okinu.State == EState::Bound && !IsStanding(Okinu));
    assert(Tick(Okinu, Collared, 1500, true) == EChange::None && Tick(Okinu, Collared, 10, false) == EChange::None);
    assert(Tick(Okinu, Collared, 1990, true) == EChange::None && Tick(Okinu, Collared, 10, true) == EChange::Freed);
    assert(Okinu.State == EState::Up);
    assert(!RulesValid({120, true, 4000, 4000, 0, true, 0}));

    // Signals hide the standing and send the hidden on.
    assert(Signal(Okinu, true) && Okinu.State == EState::Hidden && !Signal(Okinu, true));
    assert(Signal(Okinu, false) && Okinu.State == EState::Up && !Signal(Okinu, false));
    FCompanion Downed = Fresh(Escort);
    Hit(Downed, Escort, 100);
    assert(!Signal(Downed, true) && Downed.State == EState::Down);

    // The party walks only with the hero close and all of it free, standing and in the open.
    assert(PartyWalks(true, false, false, false));
    assert(!PartyWalks(false, false, false, false) && !PartyWalks(true, true, false, false));
    assert(!PartyWalks(true, false, true, false) && !PartyWalks(true, false, false, true));
}

void Holds()
{
    int HeldMs = 0;
    assert(!Hold(HeldMs, true, 600, 1000) && HeldMs == 600);
    assert(!Hold(HeldMs, false, 17, 1000) && HeldMs == 0);
    assert(!Hold(HeldMs, true, 990, 1000) && Hold(HeldMs, true, 10, 1000) && HeldMs == 0);

    FLamp Andon{true, 0};
    assert(!Snuff(Andon, false) && Andon.Lit);
    assert(Snuff(Andon, true) && !Andon.Lit && !Snuff(Andon, true));
    for (int Ms = 0; Ms < 60000; Ms += 1000)
        assert(!LampTick(Andon, 0, 1000));
    FLamp Flood{true, 0};
    assert(Snuff(Flood, true));
    assert(!LampTick(Flood, 10000, 9999) && LampTick(Flood, 10000, 1) && Flood.Lit && Flood.DarkMs == 0);
}

void Water()
{
    const FWaterRules Moat{180, 140, 8000, 3000, 10};
    assert(WaterValid(Moat) && !WaterValid({180, 0, 8000, 3000, 10}));
    FBreath Breath = FullBreath(Moat);
    // Eight seconds under, then ten damage a second whatever the frame rate.
    int Damage = 0;
    for (int Ms = 0; Ms < 8000; Ms += 1)
        Damage += Breathe(Breath, Moat, true, 1);
    assert(Breath.BreathMs == 0 && Damage == 0);
    for (int Ms = 0; Ms < 10000; Ms += 1)
        Damage += Breathe(Breath, Moat, true, 1);
    assert(Damage == 100);
    FBreath Coarse = FullBreath(Moat);
    int CoarseDamage = 0;
    for (int Ms = 0; Ms < 18000; Ms += 250)
        CoarseDamage += Breathe(Coarse, Moat, true, 250);
    assert(CoarseDamage == 100);
    // Three seconds at the surface bring it all back, at any frame rate.
    for (const int Step : {1, 7, 17, 33, 250})
    {
        FBreath Empty{0, 0, 0};
        int Spent = 0;
        while (Empty.BreathMs < Moat.BreathMs)
        {
            assert(Breathe(Empty, Moat, false, Step) == 0);
            Spent += Step;
        }
        assert(Spent >= 3000 - Step && Spent <= 3000 + Step);
    }
}

void Climbing()
{
    const FClimbRules Corner{14, 900, 6, 25, (1u << 5) | (1u << 9), 400, 30, 800};
    assert(ClimbValid(Corner));
    assert(!ClimbValid({14, 900, 6, 25, 1u, 400, 30, 800}));
    assert(!ClimbValid({14, 900, 6, 25, 1u << 14, 400, 30, 800}));
    // Fourteen holds at six each is 84 of 100: the route can be climbed without resting.
    FClimb Climb = StartClimb();
    EReach Reached = EReach::Moved;
    for (int Hold = 0; Hold < Corner.Holds; ++Hold)
        Reached = Reach(Climb, Corner, 1);
    assert(Reached == EReach::Top && Climb.GripMilli == 16000 && HoldHeightCm(Corner, Climb.Hold) == 900);
    // Dithering on the wall spends grip; the ledges give it back.
    Climb = StartClimb();
    for (int Hold = 0; Hold < 5; ++Hold)
        Reach(Climb, Corner, 1);
    assert(AtLedge(Corner, Climb) && Climb.GripMilli == 70000);
    Rest(Climb, Corner, 1000);
    assert(Climb.GripMilli == 95000);
    Rest(Climb, Corner, 10000);
    assert(Climb.GripMilli == 100000);
    Reach(Climb, Corner, 1);
    assert(!AtLedge(Corner, Climb));
    Rest(Climb, Corner, 1000);
    assert(Climb.GripMilli == 94000);
    // Out of grip, the next reach is a fall.
    Climb.GripMilli = 5999;
    assert(Reach(Climb, Corner, 1) == EReach::Fell && Climb.GripMilli == 0);
    Climb = StartClimb();
    assert(Reach(Climb, Corner, 1) == EReach::Moved && Reach(Climb, Corner, -1) == EReach::Ground);
    assert(FallDamage(Corner, 399) == 0 && FallDamage(Corner, 401) == 30 && FallDamage(Corner, 800) == 30 &&
        FallDamage(Corner, 801) == -1);
}

void Lures()
{
    int Carried = 0;
    assert(!Throw(Carried));
    Carried = Refill(Carried, 3);
    assert(Carried == 3 && Throw(Carried) && Carried == 2 && Refill(Carried, 3) == 3 && Refill(5, 3) == 5);
    // A stone sends an unaware guard looking but never convinces a suspicious one.
    assert(LureImpulsePermille(600, 0) == 600);
    assert(LureImpulsePermille(600, 500) == 400);
    assert(LureImpulsePermille(600, 900) == 0 && LureImpulsePermille(600, 1000) == 0);
    assert(LureImpulsePermille(-5, 0) == 0);

    const FCandle Teshoku{2000, 1200, 500};
    assert(CandleVisibility(Teshoku, false) == 2000 && CandleVisibility(Teshoku, true) == 1200);
    assert(WorkRatePermille(Teshoku, false) == Permille && WorkRatePermille(Teshoku, true) == 500);

    assert(CanVault(140, 130, true) && !CanVault(140, 130, false));
    assert(!CanVault(30, 50, true) && !CanVault(200, 50, true) && !CanVault(120, 400, true));

    assert(Snare(200, 250, false, false) == ESnare::None);
    assert(Snare(400, 250, false, false) == ESnare::Blade);
    assert(Snare(400, 250, false, true) == ESnare::Shield);
    assert(Snare(600, 250, true, true) == ESnare::Drone);
    assert(Snare(ChainReachCm + 1, 250, false, false) == ESnare::None);
}

void Volleys()
{
    const FVolleyRules Bailey{3, 800, 9000, 400, 6000};
    assert(VolleyValid(Bailey) && !VolleyValid({5, 800, 9000, 400, 6000}) && !VolleyValid({3, 800, 0, 400, 6000}));
    FVolley Volley = StartVolley();
    // Three ranks in turn, each back in nine seconds: an order about every three.
    assert(Order(Volley, Bailey, 0) == 0 && Order(Volley, Bailey, 100) == 1 && Order(Volley, Bailey, 200) == 2);
    assert(Order(Volley, Bailey, 300) == -1 && Volley.Orders == 3);
    assert(Order(Volley, Bailey, 8999) == -1 && Order(Volley, Bailey, 9000) == 0 && Volley.Front == 1);
    // 288 split across up to four in the ring, the remainder to the nearest.
    assert(VolleyShare(1, 4, 4, 0) == 288);
    assert(VolleyShare(4, 4, 4, 0) == 72 && VolleyShare(4, 4, 4, 3) == 72);
    assert(VolleyShare(5, 4, 4, 3) == 72 && VolleyShare(5, 4, 4, 4) == 0);
    assert(VolleyShare(7, 4, 4, 0) + 3 * VolleyShare(7, 4, 4, 1) == 288);
    assert(VolleyShare(3, 4, 4, 0) == 96 && VolleyShare(3, 4, 4, 2) == 96);
    // Two of four gunners down: half the volley.
    assert(VolleyShare(1, 2, 4, 0) == 144 && VolleyShare(1, 0, 4, 0) == 0);
    assert(VolleyShare(0, 4, 4, 0) == 0);
}

void Nets()
{
    const FNetRules Convoy{800, 15000, 1000};
    const FNetRules Cart{800, 0, 1000};
    assert(NetValid(Convoy) && NetValid(Cart) && !NetValid({0, 15000, 1000}) && !NetValid({800, 15000, 0}));
    // Locked for 800 ms under the ring, then netted; nothing locks twice.
    FNet Net = FreeNet();
    assert(BeginLock(Net) && !BeginLock(Net) && Net.State == ENet::Locking);
    ENetChange Change = ENetChange::None;
    int Ms = 0;
    for (; Change == ENetChange::None; Ms += Frame)
        Change = NetTick(Net, Convoy, Frame, false);
    assert(Change == ENetChange::Netted && Ms >= 800 && Ms < 800 + Frame && Net.State == ENet::Netted);
    // A hand on the net for a full second cuts it; letting go starts over.
    assert(NetTick(Net, Convoy, 600, true) == ENetChange::None && NetTick(Net, Convoy, 17, false) == ENetChange::None);
    assert(NetTick(Net, Convoy, 990, true) == ENetChange::None && NetTick(Net, Convoy, 10, true) == ENetChange::Freed);
    assert(Net.State == ENet::Free);
    // Left netted it is hauled away at 15 s, the lift's clock never paused by a broken hold.
    assert(BeginLock(Net) && NetTick(Net, Convoy, 800, false) == ENetChange::Netted);
    for (Ms = 0, Change = ENetChange::None; Change == ENetChange::None; Ms += 250)
        Change = NetTick(Net, Convoy, 250, Ms % 1000 == 0);
    assert(Change == ENetChange::Taken && Ms == 15000 && Net.State == ENet::Taken);
    assert(NetTick(Net, Convoy, 1000, true) == ENetChange::None && !BeginLock(Net) && !CutNet(Net));
    // The ox's net holds until it is cut: no haul.
    FNet Ox = FreeNet();
    assert(BeginLock(Ox) && NetTick(Ox, Cart, 800, false) == ENetChange::Netted);
    for (Ms = 0; Ms < 120000; Ms += 1000)
        assert(NetTick(Ox, Cart, 1000, false) == ENetChange::None);
    // A blade from the saddle cuts at once; a tether downed loosens a net and breaks a lock.
    assert(CutNet(Ox) && Ox.State == ENet::Free && !CutNet(Ox));
    assert(BeginLock(Ox) && Loosen(Ox) == ENetChange::None && Ox.State == ENet::Free);
    assert(BeginLock(Ox) && NetTick(Ox, Cart, 800, false) == ENetChange::Netted && Loosen(Ox) == ENetChange::Freed);
    assert(Loosen(Ox) == ENetChange::None);
    // A drone whose net was cut reloads for 9 s before it locks again, at any frame rate.
    for (const int Step : {1, 16, 17, 33, 250})
    {
        int Left = NetRearmMs, Ms = 0;
        for (; Left > 0; Ms += Step)
            Left = Rearm(Left, Step);
        assert(Ms >= NetRearmMs && Ms < NetRearmMs + Step);
    }
    assert(Rearm(0, Frame) == 0 && Rearm(500, 0) == 500 && Rearm(500, -Frame) == 500 && NetRearmMs > 2 * 800);
}

void Searchlights()
{
    const FSearchlightRules Moat{70, 10000, 800, 500, 1500, 6000};
    assert(SearchlightValid(Moat) && !SearchlightValid({70, 10000, 800, 1500, 1500, 0}) && !SearchlightValid({0, 10000, 800, 500, 1500, 0}));
    // The beam swings 35 degrees each way and back every ten seconds.
    assert(BeamMilliDeg(Moat, 0, 0) == -35000 && BeamMilliDeg(Moat, 2500, 0) == 0 && BeamMilliDeg(Moat, 5000, 0) == 35000);
    assert(BeamMilliDeg(Moat, 7500, 0) == 0 && BeamMilliDeg(Moat, 10000, 0) == -35000 && BeamMilliDeg(Moat, 12500, 0) == 0);
    assert(BeamMilliDeg(Moat, 0, 5000) == 35000 && BeamMilliDeg(Moat, 99999, 5000) == BeamMilliDeg(Moat, 104999, 0));
    for (int At = 0; At < 30000; At += 7)
        assert(BeamMilliDeg(Moat, At, 0) >= -35000 && BeamMilliDeg(Moat, At, 0) <= 35000);
    // Half a second in the spot: suspicion; a second and a half: the alarm. Out of it the count runs down.
    int InSpot = 0;
    ESpotted Seen = ESpotted::None;
    int Ms = 0;
    for (; Seen == ESpotted::None; Ms += Frame)
        Seen = Spotted(InSpot, true, Frame, Moat);
    assert(Seen == ESpotted::Suspicious && Ms >= 500 && Ms < 500 + Frame);
    for (Seen = ESpotted::None; Seen == ESpotted::None; Ms += Frame)
        Seen = Spotted(InSpot, true, Frame, Moat);
    assert(Seen == ESpotted::Alert && Ms >= 1500 && Ms < 1500 + Frame && InSpot == 1500);
    assert(Spotted(InSpot, true, 1000, Moat) == ESpotted::None && InSpot == 1500);
    int Out = 0;
    while (InSpot > 0)
    {
        assert(Spotted(InSpot, false, Frame, Moat) == ESpotted::None);
        Out += Frame;
    }
    assert(Out >= 1500 && Out < 1500 + Frame);
    // A quick pass through the spot is not enough to be noticed.
    for (int Pass = 0; Pass < 20; ++Pass)
    {
        assert(Spotted(InSpot, true, 400, Moat) == ESpotted::None);
        assert(Spotted(InSpot, false, 400, Moat) == ESpotted::None);
    }
}

void BellFiresAndRoofs()
{
    int Uses = 1;
    assert(RingBell(Uses) && Uses == 0 && !RingBell(Uses));
    // Three fires gutter in turn at 25, 55 and 80 percent.
    const int OutAt[] = {250, 550, 800};
    assert(MarksCrossed(OutAt, 3, 0, 249) == 0 && MarksCrossed(OutAt, 3, 249, 250) == 1 && MarksCrossed(OutAt, 3, 250, 900) == 2);
    assert(MarksCrossed(OutAt, 3, 0, 1000) == 3 && MarksCrossed(OutAt, 3, 800, 1000) == 0);
    assert(GutteringFire(0, 3) == 0 && GutteringFire(2, 3) == 2 && GutteringFire(3, 3) == 0 && GutteringFire(0, 0) == -1);
    // A drop off a roof is heard unless it lands on straw; stepping down a ladder is not.
    assert(LandingHeard(320, false) && !LandingHeard(320, true) && !LandingHeard(DropNoiseOverCm, false));
}

void Charge()
{
    // Within 30 m of his place the pack keeps its pace; it eases by up to
    // 150 cm/s as he falls another 30 m behind, and never stops.
    assert(PackPaceCmS(600, 150, -500) == 600 && PackPaceCmS(600, 150, LagCm) == 600);
    assert(PackPaceCmS(600, 150, LagCm + 1500) == 525 && PackPaceCmS(600, 150, 2 * LagCm) == 450);
    assert(PackPaceCmS(600, 150, 100000) == 450);
    // A stake breaks to a yari at a canter or faster, or to its second arrow.
    int Arrows = 0;
    assert(!StakeStruck(Arrows, EStakeHit::Yari, false) && StakeStruck(Arrows, EStakeHit::Yari, true));
    assert(!StakeStruck(Arrows, EStakeHit::Arrow, false) && Arrows == 1 && StakeStruck(Arrows, EStakeHit::Arrow, false));
    assert(!StakeStruck(Arrows = 0, EStakeHit::None, true) && Arrows == 0);
    // Easy's auto-order fires only with the toggle on, the front loaded, no ring held and a target in reach.
    assert(AutoOrders(true, true, true, false, true));
    assert(!AutoOrders(false, true, true, false, true) && !AutoOrders(true, false, true, false, true));
    assert(!AutoOrders(true, true, false, false, true) && !AutoOrders(true, true, true, true, true) &&
        !AutoOrders(true, true, true, false, false));
    assert(SmokeMs == 4000);
}
}

int main()
{
    Arms();
    Companions();
    Holds();
    Water();
    Climbing();
    Lures();
    Volleys();
    Nets();
    Searchlights();
    BellFiresAndRoofs();
    Charge();
    return 0;
}
