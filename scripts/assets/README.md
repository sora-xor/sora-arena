# Asset ledger tooling

Implements backlog items 1-7 of [`docs/art-research/free-asset-acquisition-plan.md`](../../docs/art-research/free-asset-acquisition-plan.md) (policy: sections 2.1-2.5). Everything here runs with the system `python3` (3.9+) and needs no third-party packages.

| Script | What it does |
|---|---|
| `fetch_cc0.py` | Reproducible CC0 fetcher for Poly Haven and ambientCG. Allowlisted HTTPS hosts; upstream checksums (Poly Haven MD5 plus CDN SHA-1; ambientCG zip-member CRC32); SHA-256 pinning; resumable; `--dry-run` size estimate; `--budget-gib` and `--min-free-gib` guards. Raw files go to the gitignored `Local/ThirdPartyRaw/cc0/<source>/<id>/`; schema-2 records go to `manifests/<source>-<selection>.json`. |
| `selections/first_slice.json` | What to fetch, in priority order, with each item's game use (story bible and chapter places), period-accuracy flags and visual-review notes. |
| `validate_asset_ledger.py` | Section 2.5 rules 1-7, plus the `Content/Fab/` guard, the ban on committed archives, videos and Blender backups (`*.blend1`, ...), base-manifest pinning for schema-2 extensions, and lane drafts: every file a `Content/SourceArt/**/sources_manifest.json` lists must be in the ledger with the same SHA-256 and tier. `--strict` also fails on legacy schema-1 coverage; `--require-local` fails on missing `Local/` raw files. |
| `check_restricted.py` | Restricted manifests (`restricted/*.json`) list hashes, never files. The script checks local copies, prints the user step for anything missing, and fails if a restricted root, or restricted content under any name, is tracked by git. It never downloads anything. |
| `generate_asset_notices.py` | Writes `ThirdPartyNotices/ASSETS.md` from the ledger: CC0 credits, the plan section 2.3 CC BY credit for every PUB-BY record ("Title" by Author, source, license, changes, plus the mirror and its dataset license), OWN outputs and REF/RST items; `--check` fails when it is stale. |
| `migrate_polyhaven_ledger.py` | Writes `Content/SourceArt/Environment/PolyHaven/manifest.ledger.json`, the schema-2 extension of the committed Poly Haven manifests. The schema-1 files stay byte-identical because other manifests pin their SHA-256. |

## Typical run

```sh
python3 scripts/assets/fetch_cc0.py --dry-run          # estimate only
python3 scripts/assets/fetch_cc0.py                    # fetch, verify, pin
python3 scripts/assets/validate_asset_ledger.py        # repo gate
python3 scripts/assets/check_restricted.py
python3 scripts/assets/generate_asset_notices.py
python3 -m unittest discover -s scripts/assets/tests -v
```

Other lanes write their own ledger documents: `scripts/audio/fetch_cc0_audio.py` (`manifests/audio_*.json`, and `restricted/audio_*_reference.json` for REF audio) and `scripts/art/fetch_cat_base_v6_sources.py` (`manifests/catbasev6-sources.json`, `restricted/catbasev6-reference-photos.json`, and the lane draft `Content/SourceArt/Characters/CatBaseV6/sources_manifest.json`).

## Ledger documents

- **Where they are read from:** `manifests/*.json`, `restricted/*.json`, `Content/SourceArt/**/manifest.ledger.json`, and `Content/SourceArt/**/manifest.json` files that are schema 2 *and* declare a top-level `tier` (older art manifests use their own "schema_version 2" without a tier and are not ledger documents).
- **Schema-2 JSON** (`"schema_version": 2`), one record per asset. Records sit under `records`, or under `assets` in the audio lane's manifests; both are read. A document-level OWN manifest (top-level `tier: OWN`, a generator and `files`, as in `Content/SourceArt/Audio/*/manifest.json`) is read as one OWN record.
- **Re-hosted files:** `origin_url` is the true source (for example a Freesound page) and `mirror_url` the page or dataset actually downloaded from; a mirror that is itself a licensed dataset records it as `mirror_license` (Objaverse 1.0: ODC-By 1.0).
- **Hashed files:** `files[]`, plus the audio lane's direct `downloads[]` and `archive` (archives stay in `Local/`).
- **Required record fields:** plan section 2.2, plus `files[]` with a repo-relative `path` (or `file`), `sha256` and `bytes`.
- **License evidence:** either `license_snapshot` (`url`, `sha256`, date), or a hashed snapshot inside `license_evidence`.
- **Where license snapshots live:** privately under `Local/ThirdPartyRaw/_licenses/`. Terms pages are copyrighted, so only their URL, date and SHA-256 are committed.
- **Storage values:**
  - `local-raw`: CC0 raw files that `fetch_cc0.py` can reproduce.
  - `local-private`: files kept private for other reasons.
  - `repo-lfs`: committed art.
  - `ue-restricted`: imported restricted packages.
- **Admission:** a ledger record does not admit an asset to the game. Every asset still needs the photoreal acceptance gate (`docs/art-direction/photoreal-acceptance.md`).
