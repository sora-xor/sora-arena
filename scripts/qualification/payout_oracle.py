#!/usr/bin/env python3
"""Independent exact-rational oracle for unfunded Arena death-transfer qualification.

Prints tab-separated scenario input and expected state for the Rust test-only
adapter. This script never reads the Rust implementation, a wallet, or a ledger.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from random import Random


@dataclass
class Account:
    initial: int
    remaining: int
    earnings: int = 0
    kills: int = 0
    deaths: int = 0
    paid_deaths: int = 0


@dataclass(frozen=True)
class Death:
    victim: int
    killer: int | None
    assists: tuple[tuple[int, int], ...] = ()
    teammates: tuple[int, ...] = ()
    team_mode: bool = False


class Rejected(Exception):
    pass


def exact_awards(amount: int, event: Death, player_count: int) -> list[tuple[int, int]]:
    """Allocate the policy as rational shares, then round by permanent slot."""
    assert event.killer is not None
    killer = event.killer
    assistants = [slot for slot, _ in event.assists]
    team = list(event.teammates)
    if (
        killer < 0
        or killer >= player_count
        or any(slot < 0 or slot >= player_count or slot == killer or damage <= 0
               for slot, damage in event.assists)
        or len(set(assistants)) != len(assistants)
        or any(slot < 0 or slot >= player_count or slot == killer for slot in team)
        or len(set(team)) != len(team)
        or (team and not event.team_mode)
    ):
        raise Rejected("invalid recipients")

    killer_share = Fraction(3, 5) if event.team_mode else Fraction(4, 5)
    assist_share = Fraction(1, 5)
    team_share = Fraction(1, 5) if event.team_mode else Fraction(0)
    if not assistants:
        if event.team_mode:
            team_share += assist_share
        else:
            killer_share += assist_share
        assist_share = Fraction(0)
    if not team:
        killer_share += team_share
        team_share = Fraction(0)

    shares = [Fraction(0) for _ in range(player_count)]
    shares[killer] += killer_share
    if assistants:
        total_damage = sum(damage for _, damage in event.assists)
        for slot, damage in event.assists:
            shares[slot] += assist_share * Fraction(damage, total_damage)
    if team:
        for slot in team:
            shares[slot] += team_share / len(team)
    assert sum(shares) == 1

    amounts = [int(amount * share) for share in shares]
    unallocated = amount - sum(amounts)
    # Residual units go to eligible permanent slots, not share categories.
    for slot, share in enumerate(shares):
        if unallocated == 0:
            break
        if share:
            amounts[slot] += 1
            unallocated -= 1
    assert unallocated == 0
    assert sum(amounts) == amount
    return [(slot, value) for slot, value in enumerate(amounts) if value]


def apply_reference(accounts: list[Account], event: Death) -> list[tuple[int, int]]:
    count = len(accounts)
    victim = event.victim
    killer = event.killer
    if victim < 0 or victim >= count or killer == victim or (killer is not None and not 0 <= killer < count):
        raise Rejected("invalid death slots")

    # Calculate on a copy. Any rejected event leaves all balances and counters
    # unchanged, including the victim's visible death counter.
    after = [Account(**vars(account)) for account in accounts]
    after[victim].deaths += 1
    if killer is None:
        accounts[:] = after
        return []
    after[killer].kills += 1
    tranche = after[victim].initial // 10
    if tranche == 0:
        accounts[:] = after
        return []
    if after[victim].remaining < tranche or after[victim].paid_deaths >= 10:
        raise Rejected("exhausted reserve")
    if victim in (slot for slot, _ in event.assists) or victim in event.teammates:
        raise Rejected("victim cannot receive own award")

    awards = exact_awards(tranche, event, count)
    after[victim].remaining -= tranche
    after[victim].paid_deaths += 1
    for slot, value in awards:
        after[slot].earnings += value
    assert sum(account.initial for account in after) == sum(
        account.remaining + account.earnings for account in after
    )
    accounts[:] = after
    return awards


def csv(values) -> str:
    values = list(values)
    return ",".join(str(value) for value in values) if values else "-"


def pairs(values) -> str:
    return csv(f"{slot}:{value}" for slot, value in values)


def snapshot(accounts: list[Account]) -> str:
    return ";".join(
        ":".join(str(value) for value in vars(account).values())
        for account in accounts
    )


def scenarios():
    yield (
        "unequal_team_overlapping_assists",
        [1000, 2000, 500, 3000, 10000, 400],
        [
            Death(1, 0, ((4, 30), (2, 70)), (2, 3, 4, 5), True),
            Death(0, 1, (), (3, 4), True),
            Death(4, 5, ((1, 1), (2, 7)), (1, 2, 3), True),
            Death(5, None),
        ],
    )
    yield (
        "ffa_low_slot_rounding",
        [10, 20, 30, 40],
        [
            Death(1, 3, ((2, 1), (0, 1))),
            Death(0, 3, ((2, 17),)),
            Death(2, 0),
        ],
    )
    yield (
        "ten_fixed_tranches_then_spectator",
        [10, 100, 100],
        [Death(0, 1) for _ in range(11)] + [Death(0, None), Death(0, 0)],
    )
    yield (
        "environment_and_credited_environment",
        [500, 700, 900, 1100],
        [
            Death(0, None),
            Death(0, 2, ((1, 7),)),
            Death(2, None),
            Death(3, 0, ((1, 20), (2, 1))),
        ],
    )
    # These paired deaths represent the same combat tick. Their earned awards
    # remain independent of the reserve debited when each player also dies.
    yield (
        "reciprocal_same_tick_forward",
        [1000, 2000, 3000, 4000],
        [Death(0, 1, ((2, 7),)), Death(1, 0, ((3, 11),))],
    )
    yield (
        "reciprocal_same_tick_reverse",
        [1000, 2000, 3000, 4000],
        [Death(1, 0, ((3, 11),)), Death(0, 1, ((2, 7),))],
    )
    yield (
        "missing_assist_share_to_team",
        [1000, 1000, 1000, 1000],
        [Death(1, 0, (), (2, 3), True)],
    )
    yield (
        "missing_team_share_to_killer",
        [1000, 1000, 1000, 1000],
        [Death(1, 0, ((2, 1), (3, 4)), (), True)],
    )
    yield (
        "large_atomic_amounts",
        [18446744073709551610, 1000, 1000],
        [Death(0, 2, ((1, 4294967295),)), Death(1, 0)],
    )
    yield (
        "zero_bond_offline_only",
        [0, 0],
        [Death(0, 1), Death(1, None)],
    )
    yield (
        "invalid_recipients_do_not_mutate",
        [100, 100, 100, 100],
        [
            Death(0, 1, ((2, 5), (2, 6))),
            Death(0, 1, (), (0, 3), True),
            Death(0, 1, ((2, 1),), (2, 3), True),
        ],
    )

    rng = Random(0x50AFA11)
    for index in range(48):
        count = rng.randrange(2, 13)
        bonds = [10 * rng.randrange(1, 2001) for _ in range(count)]
        events = []
        for _ in range(12):
            victim = rng.randrange(count)
            killer = None if rng.randrange(7) == 0 else rng.choice(
                [slot for slot in range(count) if slot != victim]
            )
            team_mode = bool(rng.randrange(2))
            others = [slot for slot in range(count) if slot not in (victim, killer)]
            rng.shuffle(others)
            assistants = tuple(
                (slot, rng.randrange(1, 1001)) for slot in others[:rng.randrange(len(others) + 1)]
            ) if killer is not None else ()
            rng.shuffle(others)
            teammates = tuple(others[:rng.randrange(len(others) + 1)]) if team_mode and killer is not None else ()
            events.append(Death(victim, killer, assistants, teammates, team_mode))
        yield (f"seeded_{index:02}", bonds, events)


def self_check():
    assert exact_awards(1, Death(1, 2, ((0, 1),)), 3) == [(0, 1)]
    assert exact_awards(200, Death(1, 0, ((2, 70),), (2, 3), True), 4) == [
        (0, 120), (2, 60), (3, 20)
    ]
    assert exact_awards(100, Death(1, 0, (), (2, 3), True), 4) == [
        (0, 60), (2, 20), (3, 20)
    ]


def main():
    self_check()
    for name, bonds, events in scenarios():
        assert len(bonds) <= 12 and all(bond % 10 == 0 for bond in bonds)
        accounts = [Account(bond, bond) for bond in bonds]
        print("\t".join(("CASE", name, csv(bonds))))
        for event in events:
            try:
                awards = apply_reference(accounts, event)
                status = "OK"
            except Rejected:
                awards = []
                status = "ERR"
            print("\t".join((
                "EVENT",
                str(event.victim),
                "-" if event.killer is None else str(event.killer),
                pairs(event.assists),
                csv(event.teammates),
                "T" if event.team_mode else "F",
                status,
                pairs(awards),
                snapshot(accounts),
            )))
        print("\t".join((
            "END",
            csv(account.remaining for account in accounts),
            csv(account.earnings for account in accounts),
        )))


if __name__ == "__main__":
    main()
