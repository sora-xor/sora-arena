"""Authored cargo quantities: one bounded delivery group per destination."""

MAX_QUANTITY = (1 << 31) - 1
MAX_DESTINATIONS = 8


def cargo_manifest(beat, fail):
    params, where = beat["params"], beat["id"]
    active = beat["type"] == "horseback_ride" and params.get("mode") == "cargo"
    if not active:
        if "cargo" in params:
            fail(where, "cargo quantities belong only to a cargo ride")
        return None
    cargo = params.get("cargo")
    if not isinstance(cargo, dict) or cargo.get("item") != "barley_sheaf" or cargo.get("carrier") != "pack_horse":
        fail(where, "cargo requires authored barley sheaves on a led pack horse")
    total, per = cargo.get("qty"), cargo.get("per_dropoff")
    points = cargo.get("dropoffs")
    if (type(total) is not int or type(per) is not int or
            not 0 < total <= MAX_QUANTITY or not 0 < per <= MAX_QUANTITY or
            not isinstance(points, list) or not 0 < len(points) <= MAX_DESTINATIONS or
            any(not isinstance(p, str) or not p for p in points) or len(set(points)) != len(points) or
            total != per * len(points)):
        fail(where, "cargo total must equal positive per-dropoff quantity times unique destinations")
    return {"item": cargo["item"], "total": total, "per_dropoff": per}
