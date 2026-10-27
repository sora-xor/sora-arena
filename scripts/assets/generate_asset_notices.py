#!/usr/bin/env python3
"""Generate the asset audit and player-facing credits from the same ledger.

The notices file and the in-game credits both read the ledger, so they cannot drift.
Output is deterministic (sorted, no generation timestamp) so --check can detect a
stale file. Schema-1 third-party records that are not yet covered by a schema-2
ledger are listed in their own section so nothing is silently omitted.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))
import asset_ledger as L  # noqa: E402

OUT = "ThirdPartyNotices/ASSETS.md"
CREDITS_OUT = "ThirdPartyNotices/CREDITS.md"
SOURCE_TITLES = {"polyhaven": "Poly Haven", "ambientcg": "ambientCG", "catbasev6": "CatBaseV6 anatomy inputs"}
LEGACY_LICENSE_WORDS = ("CC0", "CC BY", "CC-BY", "OFL", "Public Domain", "public domain", "OGA-BY")
LEGACY_URL_KEYS = ("asset_url", "upstream_page", "source_url", "source_page", "source_archive_url", "archive_url", "license_page")


def clean_name(value) -> str:
    """Drop scraped HTML debris (e.g. 'field-label-above"> name') from ledger author strings."""
    text = re.sub(r"<[^>]*>", " ", str(value))
    text = re.sub(r'^.*">\s*', "", text)
    return re.sub(r"\s+", " ", text).strip(" (") or "-"


def authors_text(authors) -> str:
    if isinstance(authors, dict):
        return ", ".join(sorted(clean_name(a) for a in authors)) or "-"
    if isinstance(authors, list):
        return ", ".join(clean_name(a) for a in authors) or "-"
    return clean_name(authors or "-")


def md_cell(text) -> str:
    return str(text if text is not None else "-").replace("|", "\\|").replace("\n", " ")


def code_references(value) -> str:
    """Render legacy strings and schema-2 path objects as readable references."""
    items = value if isinstance(value, list) else [value]
    paths = [item.get("path") if isinstance(item, dict) else item for item in items]
    return ", ".join(f"`{md_cell(path)}`" for path in paths if isinstance(path, str) and path) or "-"


def content_files(record: dict) -> List[dict]:
    """The asset's content files: extracted/recorded ``files``, else its direct ``downloads``."""
    return list(record.get("files") or record.get("downloads") or [])


def license_text(record: dict) -> str:
    license_id = str(record.get("license") or "-")
    if license_id.startswith("CC-BY-"):
        return "CC BY " + license_id[len("CC-BY-"):]
    return {"CC0-1.0": "CC0 1.0", "PDM-1.0": "Public Domain Mark 1.0"}.get(license_id, license_id)


def doc_credits(doc: dict) -> List[str]:
    credits = doc.get("credits") or []
    if doc.get("credit"):
        credits = [doc["credit"], *credits]
    return [str(c) for c in credits]


def source_title(doc: dict) -> str:
    return SOURCE_TITLES.get(doc.get("source", "other"), doc.get("source", "other"))


def source_links(record: dict) -> str:
    origin = f"<{record['origin_url']}>" if record.get("origin_url") else "-"
    if record.get("mirror_url"):
        origin += f" via <{record['mirror_url']}>"
    return origin


def by_credit_lines(record: dict, include_paths: bool = True) -> List[str]:
    """Plan section 2.3 CC BY credit: "Title" by Author, source link, license link, changes."""
    lines = [f"- \"{md_cell(record.get('name'))}\" by {md_cell(authors_text(record.get('authors')))}, "
             f"<{record.get('origin_url')}>, {license_text(record)} <{record.get('license_url')}>"]
    lines.append(f"  - Credit: {md_cell(record.get('attribution_text'))}")
    lines.append(f"  - Changes: {md_cell(record.get('changes'))}")
    if record.get("mirror_url"):
        mirror = record.get("mirror_license") or {}
        terms = (f" ({mirror.get('dataset')}, {mirror.get('license')} <{mirror.get('license_url')}>)"
                 if mirror.get("license") else "")
        lines.append(f"  - Downloaded from: <{record['mirror_url']}>{terms}")
    derived = record.get("derived_art") or []
    if derived and include_paths:
        lines.append("  - Used in: " + ", ".join(f"`{d}`" for d in derived))
    return lines


def storage_text(record: dict) -> str:
    return {"repo-lfs": "repository (LFS)", "repo": "repository", "local-raw": "local raw cache (not committed)",
            "local-private": "local private", "ue-restricted": "restricted UE import"}.get(record.get("storage"), str(record.get("storage")))


def legacy_third_party(root: Path, ledgers, compact: bool = True) -> List[dict]:
    extended = {base["manifest"] for _, doc in ledgers for base in doc.get("extends", []) or []}
    extended |= {L.posix(str(path.relative_to(root))) for path, _ in ledgers}  # schema-2 documents themselves
    found = []
    for path in L.tracked_files(root):
        name = path.rsplit("/", 1)[-1]
        if not path.startswith(L.SOURCE_ART_ROOT) or not name.endswith(".json") or "manifest" not in name:
            continue
        if path in extended or name in ("manifest.ledger.json", "sources_manifest.json"):
            continue  # sources_manifest.json drafts are checked against the ledger by the validator
        try:
            doc = L.load_json(root / path)
        except (OSError, ValueError):
            continue
        licenses, urls = set(), set()

        def walk(node, key=""):
            if isinstance(node, dict):
                for k, v in node.items():
                    walk(v, k)
            elif isinstance(node, list):
                for v in node:
                    walk(v, key)
            elif isinstance(node, str):
                if "license" in key.lower() and any(word in node for word in LEGACY_LICENSE_WORDS):
                    licenses.add(node if not compact or len(node) <= 160 else node[:157] + "...")
                if key in LEGACY_URL_KEYS and node.startswith("http"):
                    urls.add(node)
        walk(doc)
        if licenses:
            found.append({"manifest": path, "licenses": sorted(licenses), "urls": sorted(urls)})
    return found


def render(root: Path) -> str:
    ledgers = L.load_ledgers(root)
    records = [(path, doc, record) for path, doc in ledgers for record in L.doc_records(doc)]
    lines: List[str] = [
        "# Third-party asset notices",
        "",
        "Generated by `scripts/assets/generate_asset_notices.py` from the asset ledger "
        "(`scripts/assets/manifests/*.json`, `Content/SourceArt/**/manifest.ledger.json`, schema-2 "
        "`Content/SourceArt/**/manifest.json` output manifests and `scripts/assets/restricted/*.json`). "
        "Do not edit by hand; run the generator.",
        "",
        "Policy: `docs/art-research/free-asset-acquisition-plan.md` section 2. Every asset listed here is an "
        "*input*; none is admitted to the game until it passes the photoreal acceptance gate "
        "(`docs/art-direction/photoreal-acceptance.md`).",
        "",
        "## Summary",
        "",
        "| Tier | Records | Files | Bytes recorded |",
        "|---|---:|---:|---:|",
    ]
    tiers: Dict[str, List[int]] = {}
    for _, _, record in records:
        stats = tiers.setdefault(record.get("tier", "?"), [0, 0, 0])
        stats[0] += 1
        stats[1] += len(content_files(record))
        stats[2] += sum(int(f.get("bytes") or 0) for f in content_files(record))
    for tier in L.TIERS:
        if tier in tiers:
            count, files, size = tiers[tier]
            lines.append(f"| {tier} | {count} | {files} | {size:,} |")
    lines += [""]

    public = [(p, d, r) for p, d, r in records if r.get("tier") in ("PUB-CC0", "PUB-PD")]
    lines += [
        "## Public domain and CC0 (PUB-CC0, PUB-PD)",
        "",
        "These assets are dedicated to the public domain under CC0 1.0 "
        "(<https://creativecommons.org/publicdomain/zero/1.0/legalcode>). No attribution is required; "
        "the credits below are kept voluntarily and, for Poly Haven, as the API-terms courtesy.",
        "",
    ]
    by_source: Dict[str, List[tuple]] = {}
    for path, doc, record in public:
        by_source.setdefault(doc.get("source", "other"), []).append((path, doc, record))
    for source in sorted(by_source):
        entries = by_source[source]
        credits = sorted({c for _, doc, _ in entries for c in doc_credits(doc)})
        lines += [f"### {source_title(entries[0][1])}", ""]
        for credit in credits:
            lines.append(f"- {credit}")
        if credits:
            lines.append("")
        lines += ["| Asset | Name | Authors | License | Stored | Files | Source |", "|---|---|---|---|---|---:|---|"]
        for _, doc, record in sorted(entries, key=lambda e: (e[2].get("storage", ""), e[2].get("asset_id", ""))):
            lines.append("| " + " | ".join([
                md_cell(record.get("asset_id")), md_cell(record.get("name")), md_cell(authors_text(record.get("authors"))),
                md_cell(record.get("license")), md_cell(storage_text(record)), str(len(content_files(record))),
                source_links(record),
            ]) + " |")
        lines.append("")

    by = [(p, d, r) for p, d, r in records if r.get("tier") == "PUB-BY"]
    lines += ["## Attribution required (PUB-BY)", "",
              "Credit format (plan section 2.3): \"Title\" by Author, source link, license link, and the changes made. "
              "Raw PUB-BY files stay private in `Local/ThirdPartyRaw`; only derived art is committed, and it keeps "
              "these credits here and in the in-game credits.", ""]
    if by:
        by_doc: Dict[str, List[tuple]] = {}
        for path, doc, record in by:
            by_doc.setdefault(doc.get("source", "other"), []).append((path, doc, record))
        for source in sorted(by_doc):
            entries = by_doc[source]
            lines += [f"### {source_title(entries[0][1])}", ""]
            credits = sorted({c for _, doc, _ in entries for c in doc_credits(doc)})
            for credit in credits:
                lines.append(f"- {credit}")
            if credits:
                lines.append("")
            for _, _, record in sorted(entries, key=lambda e: (not e[2].get("derived_art"), e[2].get("asset_id", ""))):
                lines += by_credit_lines(record)
            lines.append("")
    else:
        lines += ["None recorded in schema 2 yet.", ""]

    own = [(p, d, r) for p, d, r in records if r.get("tier") == "OWN"]
    lines += ["## Project-owned work recorded in the ledger (OWN)", ""]
    if own:
        for _, _, record in sorted(own, key=lambda e: e[2].get("asset_id", "")):
            derived = code_references(record.get("derived_from"))
            generators = code_references(record.get("generator") or record.get("origin_url"))
            lines.append(f"- `{record.get('asset_id')}`: {len(record.get('files', []))} files, generator "
                         f"{generators}, derived from {derived}")
    else:
        lines.append("None.")
    lines.append("")

    restricted = [(p, d, r) for p, d, r in records if r.get("tier") in L.NEVER_TRACKED_TIERS]
    lines += ["## Restricted and reference-only content (RST, REF, EXCL)", "",
              "Never committed and never shipped as files. REF items are only looked at or listened to; "
              "RST items ship only inside cooked builds and need a PUB/OWN fallback.", ""]
    if restricted:
        for _, _, record in sorted(restricted, key=lambda e: e[2].get("asset_id", "")):
            line = (f"- `{record.get('asset_id')}` ({record.get('tier')}, {license_text(record)}): "
                    f"\"{md_cell(record.get('name'))}\" by {md_cell(authors_text(record.get('authors')))}, "
                    f"<{record.get('origin_url')}>")
            if record.get("reason"):
                line += f". {md_cell(record['reason'])}"
            if record.get("tier") == "RST":
                line += f". Fallback `{record.get('fallback')}`"
            lines.append(line)
    else:
        lines.append("None recorded.")
    lines.append("")

    legacy = legacy_third_party(root, ledgers)
    lines += ["## Schema-1 third-party records not yet migrated", "",
              "Found by scanning committed `Content/SourceArt` manifests for third-party license statements. "
              "They remain valid schema-1 records; each still needs a schema-2 extension.", ""]
    if legacy:
        lines += ["| Manifest | License statement | Source URLs |", "|---|---|---|"]
        for entry in legacy:
            lines.append(f"| `{entry['manifest']}` | {md_cell('; '.join(entry['licenses']))} | "
                         + (", ".join(f"<{u}>" for u in entry["urls"]) or "-") + " |")
    else:
        lines.append("None.")
    lines.append("")
    return "\n".join(lines)


def render_credits(root: Path) -> str:
    """Keep source acknowledgements intact without displaying the production audit."""
    ledgers = L.load_ledgers(root)
    records = [(doc, record) for _, doc in ledgers for record in L.doc_records(doc)]
    lines = ["# Art, sound and reference sources", "",
             "Acknowledgements include sources consulted during development.", ""]
    sections = (("Public domain and CC0", ("PUB-CC0", "PUB-PD")),
                ("Licensed sources", ("PUB-BY",)),
                ("Reference acknowledgements", tuple(L.NEVER_TRACKED_TIERS)))
    for heading, tiers in sections:
        by_source: Dict[str, List[tuple]] = {}
        for doc, record in records:
            if record.get("tier") in tiers:
                by_source.setdefault(source_title(doc), []).append((doc, record))
        if not by_source:
            continue
        lines += [f"## {heading}", ""]
        for source, entries in sorted(by_source.items()):
            lines += [f"### {source}", ""]
            lines += [c for c in sorted({c for doc, _ in entries for c in doc_credits(doc)})]
            lines.append("")
            for _, record in sorted(entries, key=lambda e: e[1].get("asset_id", "")):
                if record.get("tier") == "PUB-BY":
                    lines += by_credit_lines(record, include_paths=False)
                else:
                    lines.append(f"- \"{md_cell(record.get('name'))}\" by {md_cell(authors_text(record.get('authors')))}")
                    lines.append(f"  - {license_text(record)}" +
                                 (f" <{record['license_url']}>" if record.get("license_url") else ""))
                    lines.append(f"  - Source: {source_links(record)}")
                    if record.get("attribution_text"):
                        lines.append(f"  - Credit: {md_cell(record['attribution_text'])}")
                    if record.get("changes"):
                        lines.append(f"  - Changes: {md_cell(record['changes'])}")
                lines.append("")

    # Older manifests still carry source notices. Retain those acknowledgements
    # until migration, but do not show manifest paths or schema instructions.
    legacy = legacy_third_party(root, ledgers, compact=False)
    if legacy:
        lines += ["## Additional source acknowledgements", ""]
        for entry in legacy:
            folder = Path(entry["manifest"]).parent.name
            name = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", folder).replace("_", " ")
            lines += [f"### {name}", "", "; ".join(entry["licenses"])]
            lines += [f"Source: <{url}>" for url in entry["urls"]]
            lines.append("")
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=L.REPO_ROOT)
    parser.add_argument("--check", action="store_true", help="fail if either generated file is missing or stale")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    outputs = {OUT: render(root), CREDITS_OUT: render_credits(root)}
    if args.check:
        stale = [name for name, text in outputs.items()
                 if not (root / name).is_file() or (root / name).read_text(encoding="utf-8") != text]
        print("NOTICES_STALE: " + ", ".join(stale) if stale else "NOTICES_CURRENT")
        return int(bool(stale))
    for name, text in outputs.items():
        out = root / name
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(f"wrote {name} ({len(text.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
