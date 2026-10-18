#!/usr/bin/env python3
"""Print how many Niagara systems a complete scripts/unreal/create_sora_vfx.py build makes.

The builder imports `unreal`, so the host reads its SYSTEMS list from the source
instead: import-mac.sh requires the step to log `SORA_VFX_READY: <this> systems`.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

BUILDER = Path(__file__).resolve().parents[1] / "unreal/create_sora_vfx.py"


def system_count(source: str) -> int:
    """Length of the module-level SYSTEMS list, each entry a builder function the module defines."""
    tree = ast.parse(source)
    functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    lists = [node.value for node in tree.body if isinstance(node, ast.Assign)
             and any(isinstance(target, ast.Name) and target.id == "SYSTEMS" for target in node.targets)]
    if len(lists) != 1 or not isinstance(lists[0], ast.List):
        raise ValueError("create_sora_vfx.py must assign SYSTEMS exactly once, as a list literal")
    names = [entry.id if isinstance(entry, ast.Name) else None for entry in lists[0].elts]
    if None in names or not set(names) <= functions or len(set(names)) != len(names) or not names:
        raise ValueError(f"SYSTEMS must list distinct builder functions of the module: {names}")
    return len(names)


def main() -> int:
    try:
        print(system_count(BUILDER.read_text(encoding="utf-8")))
    except (OSError, ValueError, SyntaxError) as error:
        print(f"vfx_system_count: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
