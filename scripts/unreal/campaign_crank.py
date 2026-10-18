"""Authored cooperative crank rules; ch08's crew interpretation is separate."""


def cooperation(beat, fail):
    if beat["params"].get("task") != "crank" or beat["id"] == "ch08.b11":
        return None
    block, ext = beat["params"]["crank"], beat["ext"]
    npc = block.get("coop_npc")
    if npc is None:
        return None
    where = beat["id"] + ".crank.cooperation"
    if beat["id"] == "ch04.b06" and npc == "otane":
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
    rate = scaled(rate, 1000, .001, 10)
    mult = scaled(mult, 1000, .001, 1)
    if type(suspend) is not bool or type(retreat) is not int or not 0 <= retreat <= 10000 or not isinstance(locks, list) or len(locks) > 3:
        fail(where, "invalid cooperative suspension, retreat or ratchets")
    locks = [scaled(lock, 1000, .001, .999) for lock in locks]
    if locks != sorted(set(locks)):
        fail(where, "ratchets must be unique and increasing")
    return {"npc": npc, "rate_milliturns_s": rate, "progress_permille": mult,
            "suspends_decay": suspend, "retreat_cm": retreat, "ratchets_permille": locks}
