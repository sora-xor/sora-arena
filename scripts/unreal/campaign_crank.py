"""Authored cooperative crank rates, explicitly per named worker."""


def cooperation(beat, fail):
    if beat["params"].get("task") != "crank":
        return None
    block, ext = beat["params"]["crank"], beat["ext"]
    npc = block.get("coop_npc")
    if npc is None:
        return None
    where = beat["id"] + ".crank.cooperation"
    if beat["id"] == "ch08.b11":
        if not isinstance(npc, dict) or set(npc) != {"npcs", "turns_per_s_per_npc"}:
            fail(where, "lift crew requires an explicit rate per named NPC")
        npcs = npc["npcs"]
        if not isinstance(npcs, list) or not 1 <= len(npcs) <= 3 or any(not isinstance(name, str) or not name for name in npcs) or len(set(npcs)) != len(npcs):
            fail(where, "lift crew requires one to three unique named NPCs")
        rate, mult, suspend, retreat, locks = npc["turns_per_s_per_npc"], 1, False, 0, []
    elif beat["id"] == "ch04.b06" and npc == "otane":
        # Chapter 04 b06 prose and §6: Otane .2 turns/s; decay only
        # while nobody cranks. The YAML names her but omits her rate.
        rate, mult, suspend, retreat, locks = .2, 1, True, 0, []
    elif beat["id"] == "ch05.b06" and npc == "bellows_boy":
        rate, mult = ext.get("coop_npc_rate"), ext.get("coop_npc_progress_mult")
        # No suspension is authored here: at .2 credited turns/s the boy
        # slows the 1% full-goal loss while the player is away.
        suspend, retreat, locks = False, 0, []
    elif beat["id"] == "ch07.b07" and npc == "kohagi":
        override = ext.get("override") or {}
        if not isinstance(override, dict):
            fail(where, "override cooperation must be an object")
        rate, mult = override.get("coop_npc_rate_turns_s"), 1
        suspend = override.get("coop_npc_suspends_decay")
        retreat = override.get("coop_npc_leaves_if_enemy_within_cm")
        locks = override.get("ratchet_locks")
    else:
        fail(where, "cooperative crank has no authored rate contract")
    def scaled(value, scale, low, high):
        if type(value) not in (int, float) or not low <= value <= high or abs(value * scale - round(value * scale)) > 1e-6:
            fail(where, "invalid cooperative rate, multiplier or ratchet threshold")
        return round(value * scale)
    npcs = npcs if beat["id"] == "ch08.b11" else [npc]
    rate = scaled(rate, 1000, .001, 10)
    mult = scaled(mult, 1000, .001, 1)
    if type(suspend) is not bool or type(retreat) is not int or not 0 <= retreat <= 10000 or not isinstance(locks, list) or len(locks) > 3:
        fail(where, "invalid cooperative suspension, retreat or ratchets")
    locks = [scaled(lock, 1000, .001, .999) for lock in locks]
    if locks != sorted(set(locks)):
        fail(where, "ratchets must be unique and increasing")
    return {"npcs": npcs, "per_npc_milliturns_s": rate, "progress_permille": mult,
            "suspends_decay": suspend, "retreat_cm": retreat, "ratchets_permille": locks}


def player_work(beat, fail):
    """Player effort and opt-in input; helper rates never spend this resource."""
    if beat["params"].get("task") != "crank":
        return None
    where = beat["id"] + ".crank.player"
    crank, ext = beat["params"]["crank"], beat["ext"]
    cost = crank.get("stamina_per_turn")
    if type(cost) is not int or not 1 <= cost <= 100:
        fail(where, "stamina_per_turn must be a whole amount from 1 to 100")
    overspeed, two_handed, hold_rate = 0, False, 0
    if beat["id"] == "ch05.b06":
        # Chapter 05 b06 prose and x_flame_gauge.above explicitly charge
        # double for overspeed, despite the gear making no progress.
        gauge = ext.get("flame_gauge")
        if not isinstance(gauge, dict) or gauge.get("above") != "white with sparks + 3 notches; stamina cost x2":
            fail(where, "bellows overspeed stamina exception must remain explicit")
        overspeed = 2
    if cost * overspeed > 100:
        fail(where, "overspeed cost cannot exceed the stamina reserve")
    override = ext.get("override")
    if beat["id"] == "ch07.b07" and override is None:
        fail(where, "override player contract is required")
    if override is not None:
        if not isinstance(override, dict) or beat["id"] != "ch07.b07":
            fail(where, "unknown player crank override")
        two_handed = override.get("two_handed")
        rate = override.get("accessibility_hold_to_crank_turns_s")
        band = crank["turn_rate_band"]
        if (two_handed is not True or override.get("loadout_while_cranking") != "none" or
                override.get("overspeed") != "gear_slip_no_progress" or type(rate) not in (int, float) or
                not band[0] <= rate <= band[1] or rate != .6):
            fail(where, "override requires two hands, no loadout, free overspeed and authored 0.6 turns/s assist")
        hold_rate = round(rate * 1000)
    return {"stamina_per_turn": cost, "overspeed_cost_multiplier": overspeed,
            "two_handed": two_handed, "hold_milliturns_s": hold_rate}
