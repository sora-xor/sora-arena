"""Write the CC0 environment library's packages into the asset ledgers' ``used_by``.

Host tool. The ledger's ``used_by`` names the /Game packages each third-party
record feeds, so audits, removals and notice checks can find them.
``cc0_environment_library.ledger_uses`` lists, for every record the library
builds from or binds, its imported textures, cubemaps and meshes and every
material instance that binds it. This replaces the entries under the library's
package root in each record's ``used_by`` and keeps the others (for example the
palette's own instances), then rewrites the ledger in its generator's format.
``test_cc0_environment_library.py`` fails when the ledgers and the plan differ.

The library is excluded from cooking until admission (``DirectoriesToNeverCook``),
so these packages are built in the editor but not shipped yet.

    python3 scripts/unreal/record_cc0_ledger_uses.py
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cc0_environment_library as library  # noqa: E402

# Ledgers outside the first slice that hold records the library binds: origin -> (ledger, asset_id).
OTHER_LEDGERS = {
    "palette:white_plaster_02": ("Content/SourceArt/Environment/PolyHaven/manifest.ledger.json", "white_plaster_02"),
    "project:texturecan_paper_0017": ("Content/SourceArt/Environment/ShojiPaperArtReview/manifest.ledger.json",
                                      "texturecan_paper_0017"),
}
# Origins with no schema-2 record to write to, and why.
UNRECORDED = {
    "palette:grey_stone_path": "covered only by the schema-1 NyaagyuTerrain manifest (terrain lane)",
    "project:nyaagyu_ibushi": "project-owned generator output, not a third-party record",
}


def ledger_targets(root: Path) -> dict[str, tuple[str, str]]:
    """Every ledger key the library can use -> (ledger path, asset_id)."""
    targets = {}
    for source, relative in library.LEDGERS.items():
        doc = json.loads((root / relative).read_text(encoding="utf-8"))
        for record in doc["records"]:
            targets[f"{source}:{record['asset_id']}"] = (relative, record["asset_id"])
    targets.update(OTHER_LEDGERS)
    return targets


def merged(existing: list, uses: list) -> list:
    return [path for path in existing if not path.startswith(library.PACKAGE_ROOT + "/")] + uses


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    plan = library.build_plan(root, verify=False)
    uses = library.ledger_uses(plan)
    targets = ledger_targets(root)
    unknown = set(uses) - set(targets) - set(UNRECORDED)
    library.require(not unknown, f"Library origins without a ledger record: {sorted(unknown)}")
    by_ledger: dict[str, dict] = {}
    for key, (relative, asset_id) in targets.items():
        by_ledger.setdefault(relative, {})[asset_id] = uses.get(key, [])
    changed = 0
    for relative, wanted in sorted(by_ledger.items()):
        path = root / relative
        text = path.read_text(encoding="utf-8")
        doc = json.loads(text)
        found = set()
        for record in doc["records"]:
            if record["asset_id"] in wanted:
                found.add(record["asset_id"])
                record["used_by"] = merged(record.get("used_by") or [], wanted[record["asset_id"]])
        library.require(found == set(wanted), f"{relative}: records {sorted(set(wanted) - found)} are missing")
        output = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
        if output != text:
            path.write_text(output, encoding="utf-8")
            changed += 1
    recorded = sum(bool(uses.get(key)) for key in targets)
    for key, reason in sorted(UNRECORDED.items()):
        if uses.get(key):
            print(f"not recorded: {key} ({len(uses[key])} packages): {reason}")
    print(f"SORA_CC0_LEDGER_USES_RECORDED: {recorded} records in {len(by_ledger)} ledgers ({changed} rewritten)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
