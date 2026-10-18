#!/usr/bin/env python3
"""Every timber column placement in the estate halls, for one log per placement.

Reads Content/Data/campaign/chapter_*.json and replays the bay layout of
ASoraWorldBuilder::HallInterior (Source/SoraArena/Private/World/
SoraWorldBuilderDojoHall.cpp) for each zone with style "estate" and form "hall".
Halls are identified by their rect, so the same building in several chapters
keeps the same columns and different buildings never share a log.

A placement's name is SM_DojoTimberColumn_<x0>_<y0>_<x1>_<y1>_S<side>_B<bay>
(rect in cm, negative values as m<n>; side 0 south, 1 east, 2 north, 3 west),
which the C++ forms the same way, and its seed is the first 32 bits of the
name's SHA-256. ``kind`` is "open" beside a door or engawa bay (every face shows)
and "wall" otherwise.

  python3 scripts/art/dojo_hall_placements.py [--json]

Keep this in step with HallInterior: BayCm, the rounding of bay counts, BayFor
and the kamiza span. A drift shows in game as SORA_DOJO_TIMBERS missing logs.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BAY_CM = 180.0
PANEL, RENJI, RENJI_HIGH, SHOJI, DOOR_OPEN, KAMIZA = range(6)


def round_half_up(x: float) -> int:
    """FMath::RoundToInt32: floor(x + 0.5)."""
    return int(math.floor(x + 0.5))


def bay_for(side: int, index: int, count: int) -> int:
    mid = count // 2
    if side == 0:
        return DOOR_OPEN if index % 4 == 2 else SHOJI
    if side == 1:
        if count >= 8 and mid - 2 <= index < mid + 2:
            return KAMIZA
        return RENJI if index % 2 else PANEL
    if side == 2:
        return RENJI_HIGH if index % 2 else PANEL
    return DOOR_OPEN if index == count - 1 else (RENJI_HIGH if index % 3 == 1 else PANEL)


def tag(v: int) -> str:
    return f"m{-v}" if v < 0 else str(v)


def column_name(rect, side: int, index: int) -> str:
    x0, y0, x1, y1 = rect
    return f"SM_DojoTimberColumn_{tag(x0)}_{tag(y0)}_{tag(x1)}_{tag(y1)}_S{side}_B{index:02d}"


def seed_of(name: str) -> int:
    return int(hashlib.sha256(name.encode()).hexdigest()[:8], 16)


def hall_columns(rect):
    x0, y0, x1, y1 = rect
    counts = [max(1, round_half_up(((x1 - x0) if s % 2 == 0 else (y1 - y0)) / BAY_CM)) for s in range(4)]
    out = []
    for side in range(4):
        count = counts[side]
        index = 0
        while index < count:
            kind = bay_for(side, index, count)
            span = 4 if kind == KAMIZA else 1
            prev = (side + 3) % 4
            before = bay_for(side, index - 1, count) if index > 0 else bay_for(prev, counts[prev] - 1, counts[prev])
            is_open = kind == DOOR_OPEN or before == DOOR_OPEN
            name = column_name(rect, side, index)
            out.append({"name": name, "side": side, "bay": index, "kind": "open" if is_open else "wall",
                        "seed": seed_of(name)})
            index += span
    return out


def estate_halls(root: Path = ROOT):
    """{rect tuple: [(chapter file, zone id), ...]} for every estate hall zone."""
    halls: dict[tuple, list] = {}
    for path in sorted((root / "Content/Data/campaign").glob("chapter_*.json")):
        data = json.loads(path.read_text())
        for zone in (data.get("space") or {}).get("zones", []):
            if zone.get("style") == "estate" and zone.get("form") == "hall":
                rect = tuple(int(round(v)) for v in zone["rect"])
                halls.setdefault(rect, []).append((path.name, zone["id"]))
    return halls


def placements(root: Path = ROOT):
    rows = []
    for rect, uses in estate_halls(root).items():
        for col in hall_columns(rect):
            rows.append({**col, "rect": list(rect), "used_by": [f"{f}:{z}" for f, z in uses]})
    return rows


if __name__ == "__main__":
    rows = placements()
    if "--json" in sys.argv:
        print(json.dumps(rows, indent=1))
    else:
        halls = estate_halls()
        for rect, uses in halls.items():
            cols = hall_columns(rect)
            print(rect, len(cols), "columns:", sum(c["kind"] == "wall" for c in cols), "wall",
                  sum(c["kind"] == "open" for c in cols), "open; used by", ", ".join(f"{f}:{z}" for f, z in uses))
        print("total", len(rows), "placements in", len(halls), "estate halls")
