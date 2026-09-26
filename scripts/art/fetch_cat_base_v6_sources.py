#!/usr/bin/env python3
"""Fetch the private anatomy scans and reference photos for CatBaseV6.

Everything third-party lands in the gitignored ``Local/ThirdPartyRaw`` tree
(decision D6: raw CC BY scans stay private). For each object the license is
re-read from its primary record at fetch time (Sketchfab public model API for
Objaverse mirrors, the Wikimedia Commons ``extmetadata`` API for photographs).

License gate (docs/art-research/free-asset-acquisition-plan.md sections 2.1 and
2.5 rule 3): ``scans`` and ``photos`` accept only the plan's allowlist - CC0,
the Public Domain Mark, CC BY 3.0 and CC BY 4.0 (NC/ND/SA are refused).
``ref-photos`` also accepts CC BY 1.0/2.0/2.5 photographs, recorded as tier REF
(viewed on screen only, never shipped, traced or sampled).

Records (``manifest``, also run after every fetch) are generated from the
private ledger ``Local/ThirdPartyRaw/_ledger/cat_base_v6_ledger.json``:

* ``scripts/assets/manifests/catbasev6-sources.json`` - schema-2 ledger records
  for the PUB-CC0 / PUB-BY inputs, with attribution_text, changes and access,
  read by ``scripts/assets/validate_asset_ledger.py`` and the notices generator;
* ``scripts/assets/restricted/catbasev6-reference-photos.json`` - REF records
  (hashes and paths only);
* ``Content/SourceArt/Characters/CatBaseV6/sources_manifest.json`` - the lane's
  draft read by ``scripts/art/create_cat_base_v6.py``; the validator requires
  each file it lists to appear in the ledger with the same hash and tier.

The Objaverse 1.0 mirror on Hugging Face is itself a dataset under ODC-By 1.0;
``mirror`` re-reads that record (it must be ungated and ODC-By) and every scan
record carries it as ``mirror_license``.

Round 3 adds CC0 Poly Haven HDRIs for the exterior review pass and the
reference-matched A/B frame (``hdris``). Their license is re-read from the
Poly Haven license page and the asset record from the public API at fetch
time; the upstream MD5 is checked and the SHA-256 recorded. Poly Haven asks
API users for a lightweight "Powered by Poly Haven" credit; the README keeps it.

Usage (repository root):
  python3 scripts/art/fetch_cat_base_v6_sources.py scans
  python3 scripts/art/fetch_cat_base_v6_sources.py photos [VIEW=]FILE_TITLE [...]
  python3 scripts/art/fetch_cat_base_v6_sources.py ref-photos [VIEW=]FILE_TITLE [...]
  python3 scripts/art/fetch_cat_base_v6_sources.py hdris
  python3 scripts/art/fetch_cat_base_v6_sources.py mirror
  python3 scripts/art/fetch_cat_base_v6_sources.py manifest

It never logs in, accepts terms or uses credentials.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import shutil
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "Local/ThirdPartyRaw"
SCANS = RAW / "scans/objaverse"
REF = RAW / "reference/wikimedia"
HDRI_DIR = RAW / "hdri/polyhaven"
LIC = RAW / "_licenses"
LEDGER = RAW / "_ledger/cat_base_v6_ledger.json"
MANIFEST = ROOT / "Content/SourceArt/Characters/CatBaseV6/sources_manifest.json"
LEDGER_DOC = ROOT / "scripts/assets/manifests/catbasev6-sources.json"
RESTRICTED_DOC = ROOT / "scripts/assets/restricted/catbasev6-reference-photos.json"
UA = "SORA-Arena-art-pipeline/1.0 (offline game production; reference fetch)"
MIRROR = "https://huggingface.co/datasets/allenai/objaverse/resolve/main/"
MIN_FREE_GIB = 35.0

# uid -> (objaverse glb path, role). UIDs were located with the public
# Sketchfab search API and checked in the Objaverse 1.0 object-path index.
SCAN_OBJECTS = {
    "7c99ca836d834c39872ecf5e9b5e2087": (
        "glbs/000-131/7c99ca836d834c39872ecf5e9b5e2087.glb",
        "Edinburgh R(D)SVS domestic-cat CT: primary skull proportions under the face",
    ),
    "1254ff5a110a45299b39a9469f565ea3": (
        "glbs/000-086/1254ff5a110a45299b39a9469f565ea3.glb",
        "RISD Nature Lab domestic cat skull (437 03): cross-check",
    ),
    "42f9f5f91f1844688bf717a59586da40": (
        "glbs/000-120/42f9f5f91f1844688bf717a59586da40.glb",
        "RISD Nature Lab domestic cat skull (full, 18.85): cross-check with mandible",
    ),
    "ee8876449c5b48ecad78f89a26c2427c": (
        "glbs/000-034/ee8876449c5b48ecad78f89a26c2427c.glb",
        "Mammal Research Institute PAS domestic cat skull: cross-check",
    ),
    "94cc7033cd1549398ae26118d6edd086": (
        "glbs/000-018/94cc7033cd1549398ae26118d6edd086.glb",
        "RISD Nature Lab domestic cat mandible (439.03): jaw depth and chin",
    ),
}

# Already vetted on 2026-09-24 (docs/art-research/*.md); copied, not moved,
# from the earlier evaluation folder when present, else re-fetched.
PRIOR_SCANS = {
    "2996f59c517245aa91cf513a5624935e": (
        "glbs/000-065/2996f59c517245aa91cf513a5624935e.glb",
        "Neo_minigan Cat (Take 2) photogrammetry: real head/cheek/ear/coat form",
        "/tmp/sora-cat-scan-eval/neominigan-cat-take-2.glb",
    ),
    "3ffbfcabc4c34b58b03d43fd4f445b54": (
        "glbs/000-153/3ffbfcabc4c34b58b03d43fd4f445b54.glb",
        "elaughli Cat sitting upright scan: geometric ground truth of the round-5 head and neck",
        "/tmp/sora-cat-scan-eval/elaughli-cat-sitting-upright.glb",
    ),
}

# Poly Haven HDRIs (CC0): slug -> (resolution, role)
HDRI_OBJECTS = {
    "misty_pines": ("4k", "exterior overcast review pass (pine forest, real environment background)"),
    "overcast_soil": ("4k", "reference-matched A/B frame: overcast light over bare ground, like profile ref Cat (4938330260)"),
}
PH_API = "https://api.polyhaven.com"
PH_HOSTS = ("dl.polyhaven.org",)

ALLOWED_SKETCHFAB = {"cc0", "by"}
# Plan section 2.5 rule 3 allowlist, as Commons LicenseShortName prefixes. A bare
# "Public domain" tag is refused: its legal basis differs per file.
ALLOWED_COMMONS_PREFIX = ("cc0", "public domain mark", "cc by 3.0", "cc by 4.0")
# Outside the allowlist: accepted only by `ref-photos`, as REF (viewed, never shipped).
REF_ONLY_COMMONS_PREFIX = ("cc by 1.0", "cc by 2.0", "cc by 2.5")

OBJAVERSE_DATASET = "allenai/objaverse"
OBJAVERSE_API = f"https://huggingface.co/api/datasets/{OBJAVERSE_DATASET}"
ODC_BY_URL = "https://opendatacommons.org/licenses/by/1-0/"
CC_BY_4_URL = "https://creativecommons.org/licenses/by/4.0/"
CT_UID = "7c99ca836d834c39872ecf5e9b5e2087"
CAT_BASE_V6 = "Content/SourceArt/Characters/CatBaseV6"
VIEW_ONLY_CHANGES = ("None: viewed on screen as anatomy, coat and eye reference only; no pixels were copied, "
                     "traced, projected, sampled or shipped.")
# Credit and statement of changes per scan (plan section 2.3 CC BY credit format). The CT
# entry must stay in step with derived_from.skull in scripts/art/create_cat_base_v6.py.
SCAN_USE = {
    CT_UID: {
        "credit_detail": "original CT information courtesy of Dr Tobias Schwarz; adapted and prepared by "
                         "Brian Mather, The Royal (Dick) School of Veterinary Studies, The University of Edinburgh",
        "changes": "Rounds 1-4 used it as the skull under the CatBaseV6 art study: aligned to the midsagittal plane, "
                   "scaled 2.2x, pitched 12 deg, Laplacian-smoothed, converted to a level set and used only as the bone "
                   "surface under a procedurally sculpted soft-tissue skin. Round 5 (2026-09-26) keeps it for landmarks "
                   "only: its orbits place the eye globes, and a tissue-depth fit checks the scan-derived head against "
                   "it; no CT surface is part of the round-5 skin. Round 6 (2026-09-26) keeps the same role; the globes "
                   "sit 2 mm further forward along the gaze than the orbit placement. Round 7 (2026-09-26) keeps the same "
                   "landmark-only role and eye placement. Round 8 (2026-09-26) keeps the landmark-only role; the globes "
                   "sit a further 2.5 mm forward, and the round-5 finding that the CT vertex stands ~14 mm above the "
                   "scanned crown sets the round-8 crown lift. No CT triangles are stored in the "
                   ".blend or shipped. The raw scan stays private (Local/ThirdPartyRaw).",
        "derived_art": [CAT_BASE_V6],
    },
    "1254ff5a110a45299b39a9469f565ea3": {"changes": "None: not incorporated into any output; kept privately as a "
                                                    "skull-proportion cross-check."},
    "42f9f5f91f1844688bf717a59586da40": {"changes": "None: not incorporated into any output; kept privately as a "
                                                    "skull-proportion cross-check."},
    "ee8876449c5b48ecad78f89a26c2427c": {"changes": "None: not incorporated into any output; kept privately as a "
                                                    "skull-proportion cross-check."},
    "94cc7033cd1549398ae26118d6edd086": {"changes": "None: not incorporated into any output; kept privately as a "
                                                    "jaw-proportion cross-check."},
    "2996f59c517245aa91cf513a5624935e": {"changes": "None: not incorporated into any output; kept privately as a "
                                                    "head and coat form reference. Inspected in round 5 as a head source "
                                                    "and rejected (sleeping, curled pose; head fused to the cushion; "
                                                    "coarse surface noise)."},
    "3ffbfcabc4c34b58b03d43fd4f445b54": {
        "changes": "Adapted in round 5 (2026-09-26) as the geometric ground truth of the CatBaseV6 head and neck "
                   "(scripts/art/create_cat_base_v7.py). Taken: the shape of the scanned surface of the head, face, "
                   "cheeks, throat, nape and upper neck, from the clean left half only; nothing else (no vertex "
                   "colour, texture, topology or ears). Changed: expressed in a head frame found by mirror-ICP (the "
                   "head was turned about 85 deg on the body); the noisy right half discarded and replaced by the "
                   "mirror image of the left; converted to a 0.5 mm signed distance field with tunnels under 8 mm "
                   "(the open ear canals) sealed and smoothed 0.7-2.2 mm to remove fur-clump noise; the laid-back "
                   "noisy pinnae removed by a morphological opening and replaced by new modelled pinnae; inset 1-15 mm "
                   "by region (the thickness of the new groom) to turn the fur surface into a skin; scaled 1.874x and "
                   "pitched 5 deg onto the round-4 face profile (the scan is not metric); faded out below the neck into "
                   "an original biped bust; new eyes, lids, nose leather, lip and whisker-pad details, markings and "
                   "groom. Round 6 (2026-09-26, scripts/art/create_cat_base_v8.py) keeps the same scan field and "
                   "changes only what is layered on it: throat and neck insets reduced to 4.5 and 11 mm, a smooth "
                   "conchal bowl and funnel carved under each new pinna instead of the round-5 cup, and a narrower, "
                   "higher original bust. Round 7 (2026-09-26, scripts/art/create_cat_base_v9.py) samples the same "
                   "scan field through a smooth warp in front of the eyes (the muzzle and nose 11 mm forward, the lower "
                   "muzzle, lips and chin 8 mm up, so the upper lip is shorter), fills the hollows left round the removed "
                   "scan ears with a morphological closing (r 6 scan units) and two capsule plugs in the open canal pits, "
                   "insets the neck sides up to 15 mm more and the nape 15 mm, replaces the round-6 bowl carve by a "
                   "concha voxelised from each new pinna, and adds new surface details (a domed nose pad, a nasal "
                   "bridge and stop, a chin, puffier whisker pads, a lid fill band round each eye) and a new original "
                   "bust with scapulae and forelimbs. Round 8 (2026-09-26, scripts/art/create_cat_base_v10.py) keeps the "
                   "same scan field and changes how it is sampled and what is layered on it: floating remnants of the "
                   "scanned pinnae dropped, then a morphological opening (r 7 scan units), a wider closing (r 14) and a "
                   "heavy blur round the former ears and the scanned canals, so the scan's old ear canals, sockets and "
                   "ear ledge are gone (the round-7 canal plugs removed); "
                   "the cranium behind the ears 18 % shorter and the occiput 10 % flatter (a smooth warp), the crown "
                   "lifted up to 13 mm, the temples pared up to 3 mm, the muzzle warp cut from 11 to 9 mm and the chin raised "
                   "10 mm and tucked 4 mm back; neck side and nape insets cut to 2 and 9 mm; new modelled pinnae whose "
                   "back and margins flare into the head skin, a concha carved only in front of each inner face with "
                   "a canal tube, and new surface details (a flat nose planum, a deeper stop, a mentum crease) and a "
                   "new original bust. The committed .blend stores a new QuadriFlow quad cage and the decimated "
                   "derived level set it is shrink-wrapped onto (the sculpt target); no scan triangle, vertex colour or "
                   "texture is stored or shipped. The raw scan stays private (Local/ThirdPartyRaw).",
        "derived_art": [CAT_BASE_V6],
    },
}


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def utc_day() -> str:
    return dt.datetime.now(dt.timezone.utc).date().isoformat()


def free_gib() -> float:
    usage = shutil.disk_usage("/System/Volumes/Data")
    return usage.free / 2**30


def guard_disk() -> None:
    free = free_gib()
    if free < MIN_FREE_GIB:
        raise SystemExit(f"refusing to download: {free:.1f} GiB free < {MIN_FREE_GIB} GiB floor")


def get(url: str, dest: Path | None = None, timeout: int = 900) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if dest is None:
                    return resp.read()
                dest.parent.mkdir(parents=True, exist_ok=True)
                tmp = dest.with_suffix(dest.suffix + ".part")
                with open(tmp, "wb") as fh:
                    shutil.copyfileobj(resp, fh, 1 << 20)
                tmp.rename(dest)
                return b""
        except Exception as exc:  # network retry
            if attempt == 3:
                raise
            print(f"  retry {attempt + 1} for {url}: {exc}")
            time.sleep(3 * (attempt + 1))
    return b""


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_ledger() -> dict:
    if LEDGER.exists():
        return json.loads(LEDGER.read_text())
    return {"scans": {}, "photos": {}}


def save_ledger(ledger: dict) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n")


def sketchfab_record(uid: str) -> dict:
    data = get(f"https://api.sketchfab.com/v3/models/{uid}")
    snap = LIC / "sketchfab-api" / f"{uid}-{dt.date.today().isoformat()}.json"
    snap.parent.mkdir(parents=True, exist_ok=True)
    snap.write_bytes(data)
    rec = json.loads(data)
    rec["_snapshot"] = {"path": str(snap.relative_to(ROOT)), "sha256": hashlib.sha256(data).hexdigest()}
    return rec


def fetch_scan(ledger: dict, uid: str, rel: str, role: str, local_copy: str | None = None) -> None:
    rec = sketchfab_record(uid)
    lic = rec.get("license") or {}
    slug = lic.get("slug")
    if slug not in ALLOWED_SKETCHFAB or not rec.get("isDownloadable"):
        print(f"SKIP {uid}: license {slug!r} downloadable={rec.get('isDownloadable')}")
        ledger["scans"][uid] = {"status": "refused", "license": slug, "checked_at_utc": now()}
        return
    dest = SCANS / f"{uid}.glb"
    source_note = "objaverse-mirror"
    if not dest.exists():
        guard_disk()
        if local_copy and Path(local_copy).exists():
            shutil.copy2(local_copy, dest)
            source_note = f"copied from earlier evaluation file {local_copy} (originally from the Objaverse mirror)"
        else:
            print(f"GET {uid}")
            get(MIRROR + rel, dest)
    digest = sha256(dest)
    user = rec["user"]
    ledger["scans"][uid] = {
        "asset_id": f"sketchfab-{uid}",
        "name": rec["name"],
        "role": role,
        "tier": "PUB-BY" if slug == "by" else "PUB-CC0",
        "authors": [user.get("displayName"), user.get("username")],
        "origin_url": rec.get("viewerUrl"),
        "metadata_url": f"https://api.sketchfab.com/v3/models/{uid}",
        "mirror_url": MIRROR + rel,
        "license": lic.get("label"),
        "license_slug": slug,
        "license_url": "https://creativecommons.org/licenses/by/4.0/" if slug == "by" else "https://creativecommons.org/publicdomain/zero/1.0/",
        "license_requirements": lic.get("requirements"),
        "description_excerpt": (rec.get("description") or "")[:400],
        "face_count_listed": rec.get("faceCount"),
        "commercial_use": True,
        "derivatives": True,
        "redistribution": "attribution",
        "storage": "local-private",
        "access": "direct",
        "acquired_by": "agent",
        "acquired_at_utc": now(),
        "acquisition_note": source_note,
        "license_snapshot": rec["_snapshot"],
        "file": str(dest.relative_to(ROOT)),
        "bytes": dest.stat().st_size,
        "sha256": digest,
    }
    print(f"OK  {uid} {rec['name']!r} {slug} {dest.stat().st_size} {digest[:16]}")


def commons_info(title: str) -> dict:
    q = urllib.parse.urlencode({
        "action": "query", "format": "json", "prop": "imageinfo", "titles": title,
        "iiprop": "url|size|sha1|extmetadata|mime", "iiurlwidth": 2400,
    })
    data = get("https://commons.wikimedia.org/w/api.php?" + q)
    pages = json.loads(data)["query"]["pages"]
    page = next(iter(pages.values()))
    info = page["imageinfo"][0]
    safe = title.replace("File:", "").replace("/", "_")
    snap = LIC / "wikimedia" / f"{safe}-{dt.date.today().isoformat()}.json"
    snap.parent.mkdir(parents=True, exist_ok=True)
    snap.write_bytes(data)
    info["_snapshot"] = {"path": str(snap.relative_to(ROOT)), "sha256": hashlib.sha256(data).hexdigest()}
    info["_pageid"] = page.get("pageid")
    return info


def strip_html(text: str) -> str:
    import re
    return re.sub(r"<[^>]+>", "", text or "").strip()


def fetch_photo(ledger: dict, title: str, view: str, reference_only: bool = False) -> None:
    info = commons_info(title)
    meta = info.get("extmetadata", {})
    short = strip_html(meta.get("LicenseShortName", {}).get("value", ""))
    low = short.lower()
    if "sa" in low.replace("usage", "").split() or "-sa" in low or " sa " in f" {low} " or "nc" in low.split() or "nd" in low.split():
        print(f"SKIP {title}: {short}")
        ledger["photos"][title] = {"status": "refused", "license": short, "checked_at_utc": now()}
        return
    allowed = ALLOWED_COMMONS_PREFIX + (REF_ONLY_COMMONS_PREFIX if reference_only else ())
    if not low.startswith(allowed):
        hint = " (older CC BY versions: use ref-photos)" if low.startswith(REF_ONLY_COMMONS_PREFIX) else ""
        print(f"SKIP {title}: license {short!r} is outside the plan allowlist{hint}")
        ledger["photos"][title] = {"status": "refused", "license": short, "checked_at_utc": now()}
        return
    guard_disk()
    ext = Path(urllib.parse.urlparse(info["url"]).path).suffix.lower()
    safe = title.replace("File:", "")
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in Path(safe).stem)[:80]
    # Use the 2400 px rendition: plenty for anatomy reference and small on disk.
    src = info.get("thumburl") or info["url"]
    dest = REF / f"{view}__{safe}{ext}"
    if not dest.exists():
        print(f"GET {title}")
        get(src, dest)
    ledger["photos"][title] = {
        "asset_id": f"commons-{info['_pageid']}",
        "view": view,
        "tier": "PUB-CC0" if ("cc0" in low or "public domain" in low or low.startswith("pd")) else "PUB-BY",
        "origin_url": info.get("descriptionurl"),
        "original_url": info["url"],
        "downloaded_url": src,
        "original_size": [info.get("width"), info.get("height")],
        "license": short,
        "license_url": strip_html(meta.get("LicenseUrl", {}).get("value", "")) or None,
        "artist": strip_html(meta.get("Artist", {}).get("value", "")),
        "credit": strip_html(meta.get("Credit", {}).get("value", ""))[:200],
        "attribution_required": strip_html(meta.get("AttributionRequired", {}).get("value", "")),
        "commons_sha1_original": info.get("sha1"),
        "storage": "local-private",
        "use": "reference only (anatomy, coat pattern, eye and nose macro); no pixels are shipped or projected",
        "reference_only": reference_only,
        "license_snapshot": info["_snapshot"],
        "acquired_by": "agent",
        "acquired_at_utc": now(),
        "file": str(dest.relative_to(ROOT)),
        "bytes": dest.stat().st_size,
        "sha256": sha256(dest),
    }
    print(f"OK  {title} [{short}] -> {dest.name}")


def fetch_hdri(ledger: dict, slug: str, res: str, role: str) -> None:
    today = dt.date.today().isoformat()
    lic_html = get("https://polyhaven.com/license")
    snap_l = LIC / "polyhaven" / f"polyhaven-license-{today}.html"
    snap_l.parent.mkdir(parents=True, exist_ok=True)
    snap_l.write_bytes(lic_html)
    if b"CC0" not in lic_html:
        print(f"SKIP {slug}: the Poly Haven license page no longer states CC0")
        ledger.setdefault("hdris", {})[slug] = {"status": "refused", "license": "unverified", "checked_at_utc": now()}
        return
    info = get(f"{PH_API}/info/{slug}")
    files = get(f"{PH_API}/files/{slug}")
    snap_i = LIC / "polyhaven" / f"{slug}-info-{today}.json"
    snap_i.write_bytes(info)
    rec = json.loads(info)
    f = json.loads(files)["hdri"][res]["hdr"]
    url = f["url"]
    if urllib.parse.urlparse(url).hostname not in PH_HOSTS:
        raise SystemExit(f"refusing unexpected download host for {slug}: {url}")
    dest = HDRI_DIR / Path(urllib.parse.urlparse(url).path).name
    if not dest.exists():
        guard_disk()
        print(f"GET {url}")
        get(url, dest)
    md5 = hashlib.md5(dest.read_bytes()).hexdigest()
    if md5 != f["md5"]:
        dest.rename(dest.with_suffix(".bad"))
        raise SystemExit(f"MD5 mismatch for {slug}: {md5} != {f['md5']}")
    ledger.setdefault("hdris", {})[slug] = {
        "asset_id": f"polyhaven-{slug}",
        "name": rec.get("name"),
        "role": role,
        "tier": "PUB-CC0",
        "authors": list((rec.get("authors") or {}).keys()),
        "asset_url": f"https://polyhaven.com/a/{slug}",
        "metadata_url": f"{PH_API}/info/{slug}",
        "license": "CC0 1.0",
        "license_url": "https://polyhaven.com/license",
        "legal_code_url": "https://creativecommons.org/publicdomain/zero/1.0/legalcode",
        "credit_note": "Powered by Poly Haven (API use); the CC0 files themselves need no attribution",
        "resolution": res,
        "storage": "local-private (Local/ThirdPartyRaw; referenced by the render stage, not committed)",
        "acquired_by": "agent",
        "acquired_at_utc": now(),
        "license_snapshot": {"path": str(snap_l.relative_to(ROOT)), "sha256": hashlib.sha256(lic_html).hexdigest()},
        "record_snapshot": {"path": str(snap_i.relative_to(ROOT)), "sha256": hashlib.sha256(info).hexdigest()},
        "files": [{"url": url, "file": str(dest.relative_to(ROOT)), "bytes": dest.stat().st_size,
                   "upstream_md5": f["md5"], "sha256": sha256(dest)}],
    }
    print(f"OK  {slug} {res} {dest.stat().st_size} {md5}")


def fetch_mirror_license(ledger: dict) -> None:
    """Re-read the Objaverse dataset record: it must be public, ungated and ODC-By."""
    data = get(OBJAVERSE_API)
    rec = json.loads(data)
    snap = LIC / "objaverse" / f"hf-api-datasets-allenai-objaverse-{utc_day()}.json"
    snap.parent.mkdir(parents=True, exist_ok=True)
    snap.write_bytes(data)
    tags = [t for t in rec.get("tags", []) if t.startswith("license:")]
    card = (rec.get("cardData") or {}).get("license")
    if rec.get("gated") or rec.get("private") or card != "odc-by":
        raise SystemExit(f"Objaverse dataset terms changed (gated={rec.get('gated')}, license={card!r}); stop and review")
    ledger["mirror"] = {
        "dataset": OBJAVERSE_DATASET,
        "dataset_url": f"https://huggingface.co/datasets/{OBJAVERSE_DATASET}",
        "license": "ODC-By-1.0",
        "license_url": ODC_BY_URL,
        "license_tags": tags,
        "gated": bool(rec.get("gated")),
        "dataset_revision": rec.get("sha"),
        "note": "The collection is ODC-By 1.0; each object keeps its own Sketchfab license (re-read per object).",
        "snapshot": {"url": OBJAVERSE_API, "path": str(snap.relative_to(ROOT)),
                     "sha256": hashlib.sha256(data).hexdigest(), "retrieved_at_utc": now(), "via": "api"},
    }
    print(f"OK  {OBJAVERSE_DATASET}: license {card}, gated={rec.get('gated')}")


# ---------------------------------------------------------------------------
# Schema-2 records (plan section 2.2), generated from the private ledger
# ---------------------------------------------------------------------------

def https(url: str | None) -> str | None:
    return url.replace("http://", "https://", 1) if url and url.startswith("http://") else url


def commons_license(short: str, reference_only: bool = False) -> tuple[str, str]:
    """(ledger license id, tier) for a Commons LicenseShortName."""
    low = short.lower().strip()
    if low.startswith("cc0"):
        lic, tier = "CC0-1.0", "PUB-CC0"
    elif low.startswith("public domain mark"):
        lic, tier = "PDM-1.0", "PUB-CC0"
    elif low.startswith(("cc by 3.0", "cc by 4.0")):
        lic, tier = "CC-BY-" + low[6:9], "PUB-BY"
    elif low.startswith(REF_ONLY_COMMONS_PREFIX):
        lic, tier = "CC-BY-" + low[6:9], "REF"
    else:
        raise SystemExit(f"license {short!r} is outside the plan allowlist; refusing to record it")
    return lic, ("REF" if reference_only else tier)


def commons_api_url(title: str) -> str:
    return "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query", "format": "json", "prop": "imageinfo", "titles": title,
        "iiprop": "url|size|sha1|extmetadata|mime", "iiurlwidth": 2400,
    })


def common_fields() -> dict:
    return {"platform_restriction": None, "ai_terms": "none", "agent_handling": "allowed",
            "acquired_by": "agent", "storage": "local-private", "used_by": [], "fallback": None}


def scan_record(uid: str, v: dict, mirror: dict | None) -> dict:
    use = SCAN_USE.get(uid, {"changes": "None: not incorporated into any output."})
    author = (v.get("authors") or ["unknown"])[0]
    handle = (v.get("authors") or [None, None])[1:2]
    detail = f" ({use['credit_detail']})" if use.get("credit_detail") else ""
    snap = dict(v["license_snapshot"], url=v["metadata_url"], retrieved_at_utc=v["acquired_at_utc"], via="api")
    rec = {
        "asset_id": v["asset_id"], "name": v["name"], "kind": "scan", "role": v["role"],
        "tier": v["tier"], "license": "CC-BY-4.0" if v.get("license_slug") == "by" else "CC0-1.0",
        "license_label": v["license"], "license_url": v["license_url"],
        "origin_url": v["origin_url"], "metadata_url": v["metadata_url"], "mirror_url": v["mirror_url"],
        "mirror_license": mirror, "authors": [author],
        "author_profile": f"https://sketchfab.com/{handle[0]}" if handle and handle[0] else None,
        "commercial_use": True, "redistribution": "attribution" if v.get("license_slug") == "by" else "unrestricted",
        "derivatives": True,
        "attribution_text": (f'"{v["name"]}" by {author}{detail}, {v["origin_url"]}, '
                             f'licensed under CC BY 4.0 ({CC_BY_4_URL})') if v.get("license_slug") == "by" else None,
        "changes": use["changes"],
        "derived_art": use.get("derived_art", []),
        "license_snapshot": snap, "access": v.get("access", "direct"),
        "acquired_at_utc": v["acquired_at_utc"], "acquisition_note": v.get("acquisition_note"),
        **common_fields(),
        "files": [{"path": v["file"], "url": v["mirror_url"], "bytes": v["bytes"], "sha256": v["sha256"]}],
    }
    return rec


def photo_record(title: str, v: dict) -> dict:
    lic, tier = commons_license(v["license"], bool(v.get("reference_only")))
    name = title.replace("File:", "", 1)
    license_url = https(v.get("license_url"))
    by = lic.startswith("CC-BY")
    snap = dict(v["license_snapshot"], url=commons_api_url(title), retrieved_at_utc=v["acquired_at_utc"], via="api")
    rec = {
        "asset_id": v["asset_id"], "name": name, "kind": "reference-photo", "view": v.get("view"),
        "role": v.get("use"), "tier": tier, "license": lic, "license_label": v["license"], "license_url": license_url,
        "origin_url": v["origin_url"], "mirror_url": None, "authors": [v.get("artist") or "unknown"],
        "credit": v.get("credit"), "commercial_use": True, "redistribution": "attribution" if by else "unrestricted",
        "derivatives": True,
        "attribution_text": (f'"{name}" by {v.get("artist")}, Wikimedia Commons, {v["origin_url"]}, '
                             f'{v["license"]} ({license_url})') if by else None,
        "changes": VIEW_ONLY_CHANGES,
        "use_policy": "reference-only: viewed on screen; nothing from the photograph is shipped",
        "license_snapshot": snap, "access": "api", "acquired_at_utc": v["acquired_at_utc"],
        "commons_sha1_original": v.get("commons_sha1_original"),
        **common_fields(),
        "files": [{"path": v["file"], "url": v["downloaded_url"], "bytes": v["bytes"], "sha256": v["sha256"]}],
    }
    if tier == "REF":
        rec.update({
            "listing_url": v["origin_url"],
            "entitlement_owner": "none (public Wikimedia Commons file; no account, entitlement or terms acceptance)",
            "user_step": None,
            "reason": (f"{v['license']} is outside the plan allowlist (CC BY 3.0/4.0); kept as REF: "
                       "viewed only, never shipped, traced or sampled"),
        })
    return rec


def hdri_record(v: dict) -> dict:
    snap = dict(v["license_snapshot"], url=v["license_url"], retrieved_at_utc=v["acquired_at_utc"], via="direct")
    return {
        "asset_id": v["asset_id"], "name": v["name"], "kind": "hdri", "role": v["role"], "tier": "PUB-CC0",
        "license": "CC0-1.0", "license_url": v["license_url"], "legal_code_url": v["legal_code_url"],
        "origin_url": v["asset_url"], "metadata_url": v["metadata_url"], "mirror_url": None, "authors": v["authors"],
        "commercial_use": True, "redistribution": "unrestricted", "derivatives": True,
        "attribution_text": None, "courtesy_credit": "Powered by Poly Haven", "changes": None,
        "license_snapshot": snap, "record_snapshot": v.get("record_snapshot"), "access": "api",
        "acquired_at_utc": v["acquired_at_utc"], "resolution": v.get("resolution"), **common_fields(),
        "files": [{"path": f["file"], "url": f["url"], "bytes": f["bytes"], "upstream_md5": f.get("upstream_md5"),
                   "sha256": f["sha256"]} for f in v["files"]],
    }


def draft_entry(raw: dict, rec: dict) -> dict:
    """The lane draft keeps the raw layout create_cat_base_v6.py reads, plus the ledger fields."""
    return {**raw, **{k: v for k, v in rec.items() if k not in ("files", "authors")}}


def write_json(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {path.relative_to(ROOT)}")


def write_manifest(ledger: dict) -> None:
    mirror = ledger.get("mirror")
    scans = {uid: v for uid, v in ledger["scans"].items() if v.get("status") != "refused"}
    if scans and not mirror:
        raise SystemExit("run `mirror` first: the Objaverse dataset license is not recorded")
    photos = {t: v for t, v in ledger["photos"].items() if v.get("status") != "refused"}
    hdris = {k: v for k, v in ledger.get("hdris", {}).items() if v.get("status") != "refused"}
    scan_recs = {uid: scan_record(uid, v, mirror) for uid, v in scans.items()}
    photo_recs = {t: photo_record(t, v) for t, v in photos.items()}
    hdri_recs = {k: hdri_record(v) for k, v in hdris.items()}
    stamps = [v["acquired_at_utc"] for v in [*scans.values(), *photos.values(), *hdris.values()]]
    public = [*scan_recs.values(), *[r for r in photo_recs.values() if r["tier"] != "REF"], *hdri_recs.values()]
    restricted = [r for r in photo_recs.values() if r["tier"] == "REF"]
    head = {
        "schema_version": 2,
        "generator": "scripts/art/fetch_cat_base_v6_sources.py",
        "lane_draft": str(MANIFEST.relative_to(ROOT)),
        "derived_art": CAT_BASE_V6,
        "ledger_policy": "docs/art-research/free-asset-acquisition-plan.md sections 2.1-2.5",
    }
    write_json(LEDGER_DOC, {
        **head, "kind": "asset-ledger", "ledger_id": "catbasev6-sources", "source": "catbasev6",
        "title": "CatBaseV6 anatomy inputs (Objaverse-mirrored Sketchfab scans, Wikimedia Commons photos, Poly Haven HDRIs)",
        "purpose": "Private third-party inputs consulted for the CatBaseV6 cat head study; raw files stay in the "
                   "gitignored Local/ThirdPartyRaw tree (decision D6).",
        "credits": [
            f"Scans downloaded from the Objaverse 1.0 dataset ({mirror['dataset_url']}), made available under the "
            f"ODC Attribution License 1.0 ({ODC_BY_URL}); each object keeps its own Sketchfab license.",
            "HDRIs: Powered by Poly Haven - https://polyhaven.com (CC0 1.0).",
        ],
        "mirror_license": mirror,
        "records": public,
    })
    write_json(RESTRICTED_DOC, {
        **head, "kind": "restricted-manifest", "source": "catbasev6-reference",
        "purpose": "CatBaseV6 reference photographs whose license is outside the plan allowlist; viewed only (REF).",
        "records": restricted,
    })
    write_json(MANIFEST, {
        "schema": "sora-arena-source-ledger/2-draft",
        "purpose": "Private third-party inputs consulted for CatBaseV6. Raw files are not committed (decision D6).",
        "ledger": {"public": str(LEDGER_DOC.relative_to(ROOT)), "restricted": str(RESTRICTED_DOC.relative_to(ROOT))},
        "generated_at_utc": max(stamps) if stamps else None,
        "scans": [draft_entry(scans[uid], scan_recs[uid]) for uid in scans],
        "photos": [draft_entry(photos[t], photo_recs[t]) for t in photos],
        "hdris": [draft_entry(hdris[k], hdri_recs[k]) for k in hdris],
        "refused": {
            "scans": {k: v for k, v in ledger["scans"].items() if v.get("status") == "refused"},
            "photos": {k: v for k, v in ledger["photos"].items() if v.get("status") == "refused"},
        },
    })


def main(argv: list[str]) -> None:
    if not argv:
        raise SystemExit(__doc__)
    ledger = load_ledger()
    cmd = argv[0]
    if cmd == "scans":
        fetch_mirror_license(ledger)  # the mirror's own dataset terms, re-read with the objects
        for uid, (rel, role) in SCAN_OBJECTS.items():
            fetch_scan(ledger, uid, rel, role)
            save_ledger(ledger)
        for uid, (rel, role, local) in PRIOR_SCANS.items():
            fetch_scan(ledger, uid, rel, role, local)
            save_ledger(ledger)
    elif cmd in ("photos", "ref-photos"):
        for item in argv[1:]:
            view, _, title = item.partition("=")
            if not title:
                view, title = "ref", item
            fetch_photo(ledger, title, view, reference_only=cmd == "ref-photos")
            save_ledger(ledger)
    elif cmd == "hdris":
        for slug, (res, role) in HDRI_OBJECTS.items():
            fetch_hdri(ledger, slug, res, role)
            save_ledger(ledger)
    elif cmd == "mirror":
        fetch_mirror_license(ledger)
    elif cmd == "manifest":
        pass
    else:
        raise SystemExit(__doc__)
    save_ledger(ledger)
    write_manifest(ledger)
    print(f"free: {free_gib():.1f} GiB")


if __name__ == "__main__":
    main(sys.argv[1:])
