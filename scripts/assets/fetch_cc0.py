#!/usr/bin/env python3
"""Reproducible CC0 fetcher for Poly Haven and ambientCG (plan sections 2, 4.1, 5, 6).

Generalises scripts/art/fetch_polyhaven_palette.py:

* Poly Haven API (api.polyhaven.com, files on dl.polyhaven.org) and ambientCG API v3
  (ambientcg.com, files on acg-download.struffelproductions.com). Every request and
  redirect target must be on the host allowlist and use HTTPS.
* A unique User-Agent (Poly Haven API terms 2.4). "Powered by Poly Haven" is kept in
  the ledger and in ThirdPartyNotices/ASSETS.md (API terms 2.5 courtesy).
* Upstream checksums: Poly Haven API MD5 plus the CDN's Backblaze x-bz-content-sha1;
  ambientCG zip-member CRC32 from the archive's central directory. Every file is then
  pinned by SHA-256; a later run that sees a different SHA-256 stops unless --repin.
* ambientCG ships one zip per material. Only the needed members are extracted with
  HTTP Range reads (the archive is never stored), so nothing half-used is kept.
* Resumable: completed files are re-verified and skipped; a *.partial file resumes
  with a Range request.
* --dry-run prints the exact byte estimate per priority against the lane budget and
  the free-disk floor without writing anything.

Raw files go to the gitignored Local/ThirdPartyRaw/cc0/<source>/<id>/ (one copy, no
LFS duplicate). The committed outputs are scripts/assets/manifests/<source>-<selection>.json
(schema-2 ledger records) - never the raw files. License pages are snapshotted
privately under Local/ThirdPartyRaw/_licenses/ and only their URL, date and SHA-256
are committed. The script never deletes anything.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import datetime as _dt
import hashlib
import html
import io
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
import zlib
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import asset_ledger as L  # noqa: E402

GIB = 1024 ** 3
USER_AGENT = "SORA-Arena-Asset-Authoring/0.2 (scripts/assets/fetch_cc0.py; Powered by Poly Haven; offline game production)"
POLYHAVEN_HOSTS = ("api.polyhaven.com", "dl.polyhaven.org", "dl.polyhaven.com")
AMBIENTCG_HOSTS = ("ambientcg.com", "acg-download.struffelproductions.com")
LICENSE_HOSTS = ("polyhaven.com", "docs.ambientcg.com", "raw.githubusercontent.com")
DEFAULT_SELECTION = L.REPO_ROOT / "scripts/assets/selections/first_slice.json"
RAW_ROOT = "Local/ThirdPartyRaw/cc0"
LICENSE_ROOT = "Local/ThirdPartyRaw/_licenses"

# Format policy (plan section 1 and F7 measured sizes). Poly Haven 16-bit PNG normal and
# ARM maps are about 4x the size of the half-float EXR equivalents, so non-colour data
# comes as EXR; base colour stays sRGB JPG. ambientCG follows the plan: 2K-JPG members.
POLYHAVEN_TEXTURE_CHANNELS = (("Diffuse", "jpg"), ("nor_dx", "exr"), ("arm", "exr"))
AMBIENTCG_MAPS = ("Color", "NormalDX", "Roughness", "AmbientOcclusion", "Metalness", "Opacity")

# Terms pages snapshotted at fetch time; each must still contain its CC0 statement.
LICENSE_PAGES = {
    "polyhaven": [
        ("polyhaven-license", "https://polyhaven.com/license", "Our assets are all licensed as CC0"),
        ("polyhaven-api-terms", "https://raw.githubusercontent.com/Poly-Haven/Public-API/master/ToS.md",
         "free to access and use by anyone"),
    ],
    "ambientcg": [
        ("ambientcg-license", "https://docs.ambientcg.com/license/",
         "All ambientCG assets are provided under the Creative Commons CC0 1.0 Universal License"),
    ],
}
SOURCE_INFO = {
    "polyhaven": {
        "license_url": "https://polyhaven.com/license",
        "credit": "Powered by Poly Haven - https://polyhaven.com (assets CC0 1.0; credit kept as the API-terms courtesy)",
        "origin": "https://polyhaven.com/a/{id}",
        "metadata": "https://api.polyhaven.com/files/{id}",
    },
    "ambientcg": {
        "license_url": "https://docs.ambientcg.com/license/",
        "credit": "Created using assets from ambientCG.com, licensed under the Creative Commons CC0 1.0 Universal License",
        "origin": "https://ambientcg.com/a/{id}",
        "metadata": "https://ambientcg.com/api/v3/assets?id={id}",
    },
}
LEGAL_CODE_URL = "https://creativecommons.org/publicdomain/zero/1.0/legalcode"

# Automatic period-risk flags from upstream descriptions and tags (setting: 1623).
AUTO_FLAGS = (
    (r"\bmortar", "Upstream text mentions mortar; ishigaki, dry-stone walls and the granite slab-beam bridge are laid without mortar (plan F16). Check visually and mask or re-author the joints."),
    (r"\btire|\btyre", "Upstream text mentions tire tracks; wheeled-vehicle tread is anachronistic for 1623 roads. Do not use unmasked."),
    (r"varnish", "Upstream text mentions varnish; Western varnish sheen is not period timber or urushi. Re-grade roughness before use."),
    (r"metal bands|iron handle|colonial|maritime", "Upstream prop is a Western coopered design with metal hoops; Japanese oke/tsurube use split-bamboo hoops. Re-author hoops and handle."),
    (r"\bconcrete|\bcement|\bbrick", "Upstream material is concrete, cement or brick; not period Japanese construction."),
    (r"\bsteel\b|\bmetal\b.*\brope|\brope\b.*\bsteel", "Upstream rope is tagged steel/metal; wire rope is anachronistic. Evaluation only."),
    (r"\bmodern\b", "Upstream text or tags say modern; check for anachronistic manufacture."),
    (r"\bwool", "Wool cloth was a rare imported luxury (rasha) in 1623; not for commoner or practice clothing."),
    (r"\bmilky way|night sky", "Star field photographed in the southern hemisphere; lighting only, never a visible Japanese sky."),
)


def utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def human(nbytes: float) -> str:
    for unit in ("B", "KiB", "MiB", "GiB"):
        if abs(nbytes) < 1024 or unit == "GiB":
            return f"{nbytes:.1f} {unit}" if unit != "B" else f"{int(nbytes)} B"
        nbytes /= 1024
    return f"{nbytes:.1f} GiB"


# ---------------------------------------------------------------------------
# HTTP with host allowlist, retries and Range support
# ---------------------------------------------------------------------------

class FetchError(RuntimeError):
    pass


class Http:
    def __init__(self, allowed_hosts: Iterable[str], user_agent: str = USER_AGENT, allow_http: bool = False,
                 retries: int = 4, timeout: float = 90.0, backoff: float = 2.0):
        self.allowed = set(allowed_hosts)
        self.user_agent = user_agent
        self.allow_http = allow_http
        self.retries = retries
        self.timeout = timeout
        self.backoff = backoff

    def check_url(self, url: str) -> None:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "https" and not (self.allow_http and parsed.scheme == "http"):
            raise FetchError(f"refusing non-HTTPS URL {url}")
        host = parsed.hostname or ""
        if host not in self.allowed:
            raise FetchError(f"host {host!r} is not on the allowlist ({url})")

    def open(self, url: str, headers: Optional[Dict[str, str]] = None, method: str = "GET"):
        self.check_url(url)
        request = urllib.request.Request(url, method=method, headers={"User-Agent": self.user_agent, **(headers or {})})
        last: Optional[BaseException] = None
        for attempt in range(self.retries):
            try:
                response = urllib.request.urlopen(request, timeout=self.timeout)
                self.check_url(response.geturl())  # redirect target must also be allowed
                return response
            except FetchError:
                raise
            except urllib.error.HTTPError as err:
                last = err
                if err.code in (400, 401, 403, 404, 410, 416):
                    raise FetchError(f"HTTP {err.code} for {url}") from err
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as err:
                last = err
            time.sleep(self.backoff * (attempt + 1))
        raise FetchError(f"giving up on {url}: {last}")

    def get_bytes(self, url: str) -> bytes:
        with self.open(url) as response:
            return response.read()

    def get_json(self, url: str):
        return json.loads(self.get_bytes(url).decode("utf-8"))

    def head(self, url: str, max_hops: int = 5) -> Tuple[str, Dict[str, str]]:
        """HEAD that follows redirects itself (urllib would turn HEAD into GET)."""
        opener = urllib.request.build_opener(_NoRedirect)
        for _ in range(max_hops):
            self.check_url(url)
            request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": self.user_agent})
            last: Optional[BaseException] = None
            for attempt in range(self.retries):
                try:
                    response = opener.open(request, timeout=self.timeout)
                    headers = {k.lower(): v for k, v in response.headers.items()}
                    response.close()
                    return url, headers
                except urllib.error.HTTPError as err:
                    if err.code in (301, 302, 303, 307, 308) and err.headers.get("Location"):
                        url = urllib.parse.urljoin(url, err.headers["Location"])
                        break
                    last = err
                    if err.code in (400, 401, 403, 404, 410):
                        raise FetchError(f"HTTP {err.code} for HEAD {url}") from err
                except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as err:
                    last = err
                time.sleep(self.backoff * (attempt + 1))
            else:
                raise FetchError(f"giving up on HEAD {url}: {last}")
        raise FetchError(f"too many redirects from {url}")

    def read_range(self, url: str, start: int, length: int) -> bytes:
        headers = {"Range": f"bytes={start}-{start + length - 1}"}
        for attempt in range(self.retries):
            with self.open(url, headers=headers) as response:
                if response.status != 206:
                    raise FetchError(f"{url} ignored the Range request (HTTP {response.status})")
                data = response.read()
            if len(data) == length:
                return data
            time.sleep(self.backoff * (attempt + 1))
        raise FetchError(f"short Range read from {url}")

    def download(self, url: str, dest: Path, size: int, span: Optional[Tuple[int, int]] = None) -> Dict[str, str]:
        """Download url (or the byte span [start, start+length) of it) to dest.

        Resumes an existing dest.partial. Returns the response headers of the last
        request (lower-cased). The caller verifies checksums before promoting.
        """
        partial = dest.with_name(dest.name + ".partial")
        dest.parent.mkdir(parents=True, exist_ok=True)
        headers_seen: Dict[str, str] = {}
        for attempt in range(self.retries):
            have = partial.stat().st_size if partial.exists() else 0
            if have > size:
                raise FetchError(f"{partial} is larger than the expected {size} bytes; inspect it manually")
            if have == size:
                return headers_seen
            base = span[0] if span else 0
            request_headers = {}
            if span or have:
                end = (span[0] + span[1] - 1) if span else size - 1
                request_headers["Range"] = f"bytes={base + have}-{end}"
            try:
                with self.open(url, headers=request_headers) as response:
                    headers_seen = {k.lower(): v for k, v in response.headers.items()}
                    if request_headers and response.status != 206:
                        raise FetchError(f"{url} ignored the Range request (HTTP {response.status})")
                    with open(partial, "ab") as handle:
                        for block in iter(lambda: response.read(1 << 20), b""):
                            handle.write(block)
            except (FetchError, OSError) as err:
                if attempt == self.retries - 1:
                    raise FetchError(f"download failed for {url}: {err}") from err
                time.sleep(self.backoff * (attempt + 1))
        if not partial.exists() or partial.stat().st_size != size:
            raise FetchError(f"incomplete download of {url}")
        return headers_seen


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401 - urllib hook
        return None


class RangeFile(io.RawIOBase):
    """Seekable read-only view of a remote file, fetched with HTTP Range requests."""

    def __init__(self, http: Http, url: str, size: int):
        self.http, self.url, self.size, self.pos, self.requests = http, url, size, 0, 0

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self.pos

    def seek(self, offset: int, whence: int = 0) -> int:
        self.pos = {0: offset, 1: self.pos + offset, 2: self.size + offset}[whence]
        return self.pos

    def readinto(self, buffer) -> int:
        if self.pos >= self.size:
            return 0
        length = min(len(buffer), self.size - self.pos)
        data = self.http.read_range(self.url, self.pos, length)
        buffer[:len(data)] = data
        self.pos += len(data)
        self.requests += 1
        return len(data)


# ---------------------------------------------------------------------------
# Plan structures
# ---------------------------------------------------------------------------

class PlannedFile:
    def __init__(self, channel: str, url: str, rel_path: str, size: int, fmt: str, md5: Optional[str] = None,
                 crc32: Optional[int] = None, span: Optional[Tuple[int, int]] = None, archive: Optional[dict] = None,
                 member: Optional[str] = None, compressed: bool = False, resolved_url: Optional[str] = None):
        self.channel, self.url, self.rel_path, self.size, self.format = channel, url, rel_path, size, fmt
        self.md5, self.crc32, self.span, self.archive, self.member = md5, crc32, span, archive, member
        self.compressed, self.resolved_url = compressed, resolved_url
        self.sha256: Optional[str] = None
        self.sha1: Optional[str] = None
        self.status = "planned"

    def record(self) -> dict:
        entry = {"channel": self.channel, "path": self.rel_path, "format": self.format, "url": self.url,
                 "bytes": self.size, "sha256": self.sha256}
        if self.md5:
            entry["upstream_md5"] = self.md5
        if self.sha1:
            entry["upstream_sha1"] = self.sha1
        if self.crc32 is not None:
            entry["zip_crc32"] = f"{self.crc32:08x}"
        if self.archive:
            entry["archive"] = self.archive
            entry["member"] = self.member
        return entry


class PlannedAsset:
    def __init__(self, source: str, item: dict, group: dict, meta: dict, files: List[PlannedFile]):
        self.source, self.item, self.group, self.meta, self.files = source, item, group, meta, files

    @property
    def asset_id(self) -> str:
        return self.item["id"]

    @property
    def total(self) -> int:
        return sum(f.size for f in self.files)


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------

class PolyHavenSource:
    name = "polyhaven"

    def __init__(self, http: Http, api_base: str = "https://api.polyhaven.com", dl_hosts=("dl.polyhaven.org", "dl.polyhaven.com")):
        self.http, self.api_base, self.dl_hosts = http, api_base.rstrip("/"), set(dl_hosts)
        self._index: Optional[dict] = None

    def index(self) -> dict:
        if self._index is None:
            self._index = self.http.get_json(self.api_base + "/assets")
        return self._index

    def _pick(self, files: dict, channel: str, res: str, fmt: str) -> dict:
        try:
            return files[channel][res][fmt]
        except KeyError as err:
            raise FetchError(f"Poly Haven file listing has no {channel}/{res}/{fmt}") from err

    def _file(self, asset_id: str, channel: str, entry: dict, rel_name: Optional[str] = None, fmt: Optional[str] = None) -> PlannedFile:
        url = entry["url"]
        host = urllib.parse.urlparse(url).hostname
        if host not in self.dl_hosts:
            raise FetchError(f"unexpected Poly Haven production host in {url}")
        name = rel_name or Path(urllib.parse.urlparse(url).path).name
        return PlannedFile(channel, url, f"{RAW_ROOT}/polyhaven/{asset_id}/{name}", int(entry["size"]),
                           fmt or name.rsplit(".", 1)[-1], md5=entry.get("md5"))

    def plan(self, item: dict, group: dict) -> PlannedAsset:
        asset_id, res, kind = item["id"], item.get("resolution", group.get("resolution", "2k")), group["kind"]
        meta = self.index().get(asset_id)
        if meta is None:
            raise FetchError(f"Poly Haven has no asset {asset_id!r}")
        files = self.http.get_json(f"{self.api_base}/files/{asset_id}")
        planned: List[PlannedFile] = []
        if kind == "texture":
            channels = [tuple(c) for c in item.get("channels", POLYHAVEN_TEXTURE_CHANNELS)]
            for channel, fmt in channels:
                planned.append(self._file(asset_id, channel, self._pick(files, channel, res, fmt), fmt=fmt))
        elif kind == "hdri":
            planned.append(self._file(asset_id, "hdri", self._pick(files, "hdri", res, item.get("format", "hdr"))))
        elif kind == "model":
            gltf = self._pick(files, "gltf", res, "gltf")
            planned.append(self._file(asset_id, "gltf", gltf, fmt="gltf"))
            for rel, include in sorted(gltf.get("include", {}).items()):
                if ".." in Path(rel).parts or rel.startswith("/"):
                    raise FetchError(f"unsafe include path {rel!r} in {asset_id}")
                planned.append(self._file(asset_id, "gltf-include", include, rel_name=rel))
            for channel, fmt in [tuple(c) for c in item.get("extra_channels", [])]:
                planned.append(self._file(asset_id, channel, self._pick(files, channel, res, fmt), fmt=fmt))
        else:
            raise FetchError(f"unknown Poly Haven kind {kind!r}")
        info = {
            "name": meta.get("name"), "authors": meta.get("authors", {}), "description": meta.get("description"),
            "tags": meta.get("tags", []), "categories": meta.get("categories", []),
            "dimensions_mm": meta.get("dimensions"), "files_hash": meta.get("files_hash"),
            "date_published": meta.get("date_published"), "polycount": meta.get("polycount"),
        }
        return PlannedAsset(self.name, dict(item, resolution=res), group, info, planned)


def zip_member_span(http: Http, url: str, info: zipfile.ZipInfo) -> Tuple[int, int]:
    """Absolute byte span of a STORED member's data inside a remote zip."""
    header = http.read_range(url, info.header_offset, 30)
    signature, = struct.unpack("<I", header[:4])
    if signature != 0x04034B50:
        raise FetchError(f"bad local header for {info.filename}")
    name_len, extra_len = struct.unpack("<HH", header[26:30])
    return info.header_offset + 30 + name_len + extra_len, info.compress_size


class AmbientCGSource:
    name = "ambientcg"

    def __init__(self, http: Http, api_base: str = "https://ambientcg.com/api/v3/assets",
                 get_base: str = "https://ambientcg.com/get"):
        self.http, self.api_base, self.get_base = http, api_base, get_base
        self._meta: Dict[str, dict] = {}

    def prefetch(self, ids: List[str]) -> None:
        missing = [i for i in ids if i not in self._meta]
        for start in range(0, len(missing), 50):
            chunk = missing[start:start + 50]
            query = urllib.parse.urlencode({
                "id": ",".join(chunk), "limit": 500,
                "include": "title,url,technique,dimensions,maps,downloads,tags,type,releaseDate",
            })
            data = self.http.get_json(f"{self.api_base}?{query}")
            for asset in data.get("assets", []):
                self._meta[asset["id"]] = asset

    def plan(self, item: dict, group: dict) -> PlannedAsset:
        asset_id = item["id"]
        self.prefetch([asset_id])
        meta = self._meta.get(asset_id)
        if meta is None:
            raise FetchError(f"ambientCG has no asset {asset_id!r}")
        attribute = item.get("download", group.get("download", "2K-JPG"))
        download = next((d for d in meta.get("downloads", []) if d.get("attributes") == attribute), None)
        if download is None:
            raise FetchError(f"ambientCG {asset_id} has no {attribute} download")
        resolved, headers = self.http.head(download["url"])
        size = int(headers.get("content-length", download["size"]))
        if size != int(download["size"]):
            raise FetchError(f"ambientCG {asset_id} archive size {size} differs from the API ({download['size']})")
        archive = {"url": download["url"], "resolved_url": resolved, "bytes": size,
                   "upstream_sha1": headers.get("x-bz-content-sha1"), "attribute": attribute,
                   "note": "archive not stored; members extracted by HTTP Range; member CRC32 verified"}
        reader = RangeFile(self.http, resolved, size)
        with zipfile.ZipFile(io.BufferedReader(reader, buffer_size=1 << 16)) as archive_zip:
            members = archive_zip.infolist()
        wanted_maps = item.get("maps", group.get("maps", AMBIENTCG_MAPS))
        planned: List[PlannedFile] = []
        for map_name in wanted_maps:
            member = next((m for m in members if re.search(rf"_{map_name}\.(jpg|png|exr)$", m.filename)), None)
            if member is None:
                continue  # maps differ per material (e.g. only some have Opacity)
            if "/" in member.filename or ".." in member.filename:
                raise FetchError(f"unsafe member name {member.filename!r}")
            compressed = member.compress_type != zipfile.ZIP_STORED
            span = None if compressed else zip_member_span(self.http, resolved, member)
            planned.append(PlannedFile(map_name, download["url"], f"{RAW_ROOT}/ambientcg/{asset_id}/{member.filename}",
                                       member.file_size, member.filename.rsplit(".", 1)[-1], crc32=member.CRC,
                                       span=span, archive=archive, member=member.filename, compressed=compressed,
                                       resolved_url=resolved))
        if not planned:
            raise FetchError(f"no wanted maps found in {download['url']}")
        info = {
            "name": meta.get("title") or asset_id, "authors": {"ambientCG (Lennart Demes)": "All"},
            "description": None, "tags": meta.get("tags", []), "technique": meta.get("technique"),
            "maps": meta.get("maps", []), "release_date": meta.get("releaseDate"),
            # Raw API values; the unit is not stated in the v3 docs, so no mm conversion is claimed.
            "dimensions_raw": meta.get("dimensions"), "dimensions_mm": None,
        }
        return PlannedAsset(self.name, dict(item, resolution=attribute), group, info, planned)


# ---------------------------------------------------------------------------
# Fetch execution
# ---------------------------------------------------------------------------

def verify_file(path: Path, planned: PlannedFile) -> Tuple[bool, str]:
    if not path.is_file() or path.stat().st_size != planned.size:
        return False, "size"
    data_md5 = hashlib.md5() if planned.md5 else None
    crc = 0
    sha = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            sha.update(block)
            if data_md5:
                data_md5.update(block)
            if planned.crc32 is not None:
                crc = zlib.crc32(block, crc)
    if data_md5 and data_md5.hexdigest() != planned.md5:
        return False, "upstream md5"
    if planned.crc32 is not None and (crc & 0xFFFFFFFF) != planned.crc32:
        return False, "zip crc32"
    planned.sha256 = sha.hexdigest()
    return True, "ok"


class Fetcher:
    def __init__(self, root: Path, http_factory: Callable[[Iterable[str]], Http], budget_bytes: int, min_free_bytes: int,
                 pins: Dict[str, str], repin: bool = False, workers: int = 3, log: Callable[[str], None] = print,
                 free_bytes: Optional[Callable[[], int]] = None):
        self.root, self.http_factory, self.budget, self.min_free = root, http_factory, budget_bytes, min_free_bytes
        self.pins, self.repin, self.workers, self.log = pins, repin, workers, log
        self.free_bytes = free_bytes or (lambda: shutil.disk_usage(self.root).free)
        self.new_bytes = 0
        self.lock = threading.Lock()
        self.stopped_reason: Optional[str] = None

    def _promote(self, planned: PlannedFile, dest: Path, headers: Dict[str, str]) -> None:
        partial = dest.with_name(dest.name + ".partial")
        ok, why = verify_file(partial, planned)
        if not ok:
            bad = partial.with_name(partial.name + ".rejected")
            partial.replace(bad)  # kept for inspection, never deleted
            raise FetchError(f"{planned.rel_path}: {why} check failed; bytes kept at {bad.name}")
        sha1 = (headers.get("x-bz-content-sha1") or "").replace("unverified:", "").lower()
        if re.fullmatch(r"[0-9a-f]{40}", sha1) and not planned.span and not planned.compressed:
            digest = hashlib.sha1()
            with open(partial, "rb") as handle:
                for block in iter(lambda: handle.read(1 << 20), b""):
                    digest.update(block)
            actual_sha1 = digest.hexdigest()
            if actual_sha1 != sha1:
                bad = partial.with_name(partial.name + ".rejected")
                partial.replace(bad)
                raise FetchError(f"{planned.rel_path}: CDN SHA-1 mismatch; bytes kept at {bad.name}")
            planned.sha1 = sha1
        partial.replace(dest)

    def fetch_file(self, http: Http, planned: PlannedFile) -> None:
        dest = self.root / planned.rel_path
        pinned = self.pins.get(planned.rel_path)
        if dest.exists():
            ok, why = verify_file(dest, planned)
            if ok:
                planned.status = "present"
                self._check_pin(planned, pinned)
                if planned.archive is None and planned.md5 is None and pinned is None:
                    raise FetchError(f"{planned.rel_path}: no upstream checksum and no pin; cannot trust existing file")
                return
            raise FetchError(f"{planned.rel_path} exists but fails its {why} check; it is left untouched - inspect it manually")
        with self.lock:
            free = self.free_bytes()
            if free - planned.size < self.min_free:
                self.stopped_reason = f"free disk {human(free)} would drop below the {human(self.min_free)} floor"
                planned.status = "skipped-disk"
                return
            if self.new_bytes + planned.size > self.budget:
                self.stopped_reason = f"lane budget {human(self.budget)} reached"
                planned.status = "skipped-budget"
                return
            self.new_bytes += planned.size
        if planned.compressed:
            reader = RangeFile(http, planned.resolved_url, planned.archive["bytes"])
            partial = dest.with_name(dest.name + ".partial")
            dest.parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(io.BufferedReader(reader, buffer_size=1 << 16)) as archive_zip:
                with archive_zip.open(planned.member) as member, open(partial, "wb") as handle:
                    shutil.copyfileobj(member, handle, 1 << 20)
            headers: Dict[str, str] = {}
        else:
            url = planned.resolved_url or planned.url
            headers = http.download(url, dest, planned.size, span=planned.span)
        self._promote(planned, dest, headers)
        self._check_pin(planned, pinned)
        planned.status = "downloaded"
        self.log(f"  verified {planned.rel_path} ({human(planned.size)})")

    def _check_pin(self, planned: PlannedFile, pinned: Optional[str]) -> None:
        if pinned and pinned != planned.sha256 and not self.repin:
            raise FetchError(f"{planned.rel_path}: SHA-256 {planned.sha256} differs from pinned {pinned} (upstream changed? use --repin after review)")

    def fetch_assets(self, http: Http, assets: List[PlannedAsset]) -> None:
        jobs = [(asset, f) for asset in assets for f in asset.files]
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.workers) as pool:
            futures = {pool.submit(self.fetch_file, http, f): (a, f) for a, f in jobs}
            for future in concurrent.futures.as_completed(futures):
                asset, planned = futures[future]
                try:
                    future.result()
                except Exception as err:  # noqa: BLE001 - reported and recorded
                    planned.status = "failed"
                    self.log(f"  FAILED {planned.rel_path}: {err}")


# ---------------------------------------------------------------------------
# Selection, licenses, ledger output
# ---------------------------------------------------------------------------

def html_text(raw: bytes) -> str:
    text = raw.decode("utf-8", errors="replace")
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", text, flags=re.S)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    return re.sub(r"\s+", " ", text)


def snapshot_licenses(root: Path, http: Http, source: str, write: bool, today: str) -> List[dict]:
    snapshots = []
    for name, url, required in LICENSE_PAGES[source]:
        raw = http.get_bytes(url)
        if required not in html_text(raw):
            raise FetchError(f"{url} no longer contains {required!r}; license must be re-reviewed before fetching")
        suffix = ".md" if url.endswith(".md") else ".html"
        rel = f"{LICENSE_ROOT}/{source}/{name}-{today}{suffix}"
        if write:
            dest = root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                dest.write_bytes(raw)
            elif hashlib.sha256(dest.read_bytes()).hexdigest() != hashlib.sha256(raw).hexdigest():
                rel = f"{LICENSE_ROOT}/{source}/{name}-{today}-{hashlib.sha256(raw).hexdigest()[:8]}{suffix}"
                (root / rel).write_bytes(raw)
        snapshots.append({"name": name, "url": url, "path": rel, "sha256": hashlib.sha256(raw).hexdigest(),
                          "retrieved_at_utc": utc_now(), "via": "direct", "verified_statement": required,
                          "stored": "private (Local/, gitignored; page text is copyrighted)"})
    return snapshots


def auto_flags(meta: dict) -> List[dict]:
    text = " ".join([meta.get("description") or ""] + list(meta.get("tags") or [])).lower()
    flags = []
    for pattern, risk in AUTO_FLAGS:
        if re.search(pattern, text):
            flags.append({"source": "auto:upstream-description", "risk": risk})
    return flags


def build_record(asset: PlannedAsset, snapshot: dict, acquired: str, previous: Optional[dict]) -> dict:
    info = SOURCE_INFO[asset.source]
    item, meta = asset.item, asset.meta
    manual_flags = [dict(flag, source="selection") for flag in item.get("period_flags", [])]
    flags = manual_flags + auto_flags(meta)
    dims = meta.get("dimensions_mm")
    record = {
        "asset_id": asset.asset_id,
        "name": meta.get("name") or asset.asset_id,
        "kind": asset.group["kind"],
        "tier": "PUB-CC0",
        "license": "CC0-1.0",
        "license_url": info["license_url"],
        "legal_code_url": LEGAL_CODE_URL,
        "origin_url": info["origin"].format(id=asset.asset_id),
        "mirror_url": None,
        "metadata_url": info["metadata"].format(id=asset.asset_id),
        "authors": meta.get("authors", {}),
        "upstream_description": meta.get("description"),
        "upstream_tags": meta.get("tags", []),
        "commercial_use": True,
        "redistribution": "unrestricted",
        "derivatives": True,
        "platform_restriction": None,
        "ai_terms": "none",
        "agent_handling": "allowed",
        "attribution_text": None,
        "courtesy_credit": info["credit"],
        "changes": None,
        "license_snapshot": {k: snapshot[k] for k in ("url", "path", "sha256", "retrieved_at_utc", "via")},
        "access": "api",
        "acquired_at_utc": (previous or {}).get("acquired_at_utc") or acquired,
        "acquired_by": "agent",
        "storage": "local-raw",
        "used_by": (previous or {}).get("used_by", []),
        "fallback": None,
        "priority": asset.group["priority"],
        "backlog_item": asset.group.get("backlog_item"),
        "resolution": item["resolution"],
        "hero": bool(item.get("hero")),
        "hero_reason": item.get("hero_reason"),
        "source_dimensions_mm": dims,
        "tile_size_cm": round(dims[0] / 10, 2) if dims and asset.group["kind"] in ("texture", "material") and dims[0] else None,
        "game_use": item.get("game_use", []),
        "period_flags": flags,
        "period_risk": item.get("period_risk") or ("review" if flags else "none"),
        "visual_review": item.get("visual_review"),
        "photoreal_gate": "Not admitted: needs the packaged A/B comparison, measured frame cost and license check in docs/art-direction/photoreal-acceptance.md before any runtime use.",
        "files": [f.record() for f in asset.files],
    }
    for key in ("technique", "maps", "release_date", "files_hash", "polycount", "dimensions_raw"):
        if meta.get(key) is not None:
            record["upstream_" + key] = meta[key]
    return record


def git_tracked_under(root: Path, prefix: str) -> List[str]:
    try:
        return [p for p in L.tracked_files(root) if p.startswith(prefix)]
    except RuntimeError:
        return []


def du_kib(path: Path) -> Optional[int]:
    if not path.exists():
        return None
    result = subprocess.run(["du", "-sk", str(path)], capture_output=True, text=True)
    try:
        return int(result.stdout.split()[0])
    except (IndexError, ValueError):
        return None


def disk_snapshot(root: Path) -> dict:
    return {
        "free_gib": round(shutil.disk_usage(root).free / GIB, 2),
        "du_kib": {name: du_kib(root / name) for name in ("Local", "Content/SourceArt", ".git/lfs", "DerivedDataCache", "Content/Generated")},
    }


def load_selection(path: Path) -> dict:
    selection = L.load_json(path)
    if selection.get("format") != "sora-cc0-selection/1":
        raise FetchError(f"{path} is not a sora-cc0-selection/1 file")
    return selection


def manifest_path(root: Path, source: str, selection: dict) -> Path:
    return root / "scripts/assets/manifests" / f"{source}-{selection['name']}.json"


def load_pins(path: Path) -> Tuple[Dict[str, str], Dict[str, dict], Optional[dict]]:
    if not path.exists():
        return {}, {}, None
    doc = L.load_json(path)
    pins, records = {}, {}
    for record in doc.get("records", []):
        records[record["asset_id"]] = record
        for entry in record.get("files", []):
            if entry.get("sha256"):
                pins[entry["path"]] = entry["sha256"]
    return pins, records, doc


def run(argv=None, root: Path = L.REPO_ROOT, http_factory: Optional[Callable[[Iterable[str]], Http]] = None,
        source_factories: Optional[dict] = None, log: Callable[[str], None] = print,
        free_bytes: Optional[Callable[[], int]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--selection", type=Path, default=DEFAULT_SELECTION)
    parser.add_argument("--dry-run", action="store_true", help="plan and print the size estimate only")
    parser.add_argument("--source", choices=("polyhaven", "ambientcg"), action="append")
    parser.add_argument("--only", help="comma-separated asset ids")
    parser.add_argument("--max-priority", type=int, default=99)
    parser.add_argument("--budget-gib", type=float, default=16.0, help="new bytes this run may add")
    parser.add_argument("--min-free-gib", type=float, default=35.0, help="free-disk floor that must survive every file")
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--repin", action="store_true", help="accept SHA-256 changes against the committed pins")
    args = parser.parse_args(argv)

    selection = load_selection(args.selection if args.selection.is_absolute() else root / args.selection)
    only = set(args.only.split(",")) if args.only else None
    groups = [g for g in selection["groups"] if g["priority"] <= args.max_priority
              and (not args.source or g["source"] in args.source)]
    groups.sort(key=lambda g: g["priority"])
    http_factory = http_factory or (lambda hosts: Http(hosts))
    tracked_raw = git_tracked_under(root, "Local/")
    if tracked_raw:
        raise FetchError(f"Local/ has tracked files ({tracked_raw[:3]}); refusing to write raw assets there")

    sources = {}
    https = {}
    for source in sorted({g["source"] for g in groups}):
        hosts = (POLYHAVEN_HOSTS if source == "polyhaven" else AMBIENTCG_HOSTS) + LICENSE_HOSTS
        https[source] = http_factory(hosts)
        factory = (source_factories or {}).get(source)
        sources[source] = factory(https[source]) if factory else (PolyHavenSource(https[source]) if source == "polyhaven" else AmbientCGSource(https[source]))

    today = _dt.date.today().isoformat()
    snapshots = {s: snapshot_licenses(root, https[s], s, write=not args.dry_run, today=today) for s in sources}
    for source, snaps in snapshots.items():
        for snap in snaps:
            log(f"license {source}: {snap['url']} verified ({snap['sha256'][:12]}...)")

    plans: Dict[str, List[PlannedAsset]] = {s: [] for s in sources}
    failures: List[str] = []
    for group in groups:
        items = [i for i in group["items"] if not only or i["id"] in only]
        if group["source"] == "ambientcg":
            sources["ambientcg"].prefetch([i["id"] for i in items])
        for item in items:
            try:
                plans[group["source"]].append(sources[group["source"]].plan(item, group))
            except FetchError as err:
                failures.append(f"{group['source']}:{item['id']}: {err}")
                log(f"PLAN FAILED {group['source']}:{item['id']}: {err}")

    # Size estimate in priority order.
    free = (free_bytes or (lambda: shutil.disk_usage(root).free))()
    budget = int(args.budget_gib * GIB)
    floor = int(args.min_free_gib * GIB)
    log(f"free disk {human(free)}; floor {human(floor)}; lane budget {human(budget)}")
    cumulative = 0
    ordered = sorted((a for plan in plans.values() for a in plan), key=lambda a: (a.group["priority"], a.source))
    by_priority: Dict[int, List[PlannedAsset]] = {}
    for asset in ordered:
        by_priority.setdefault(asset.group["priority"], []).append(asset)
    for priority, assets in by_priority.items():
        present = sum(f.size for a in assets for f in a.files if (root / f.rel_path).is_file())
        total = sum(a.total for a in assets)
        cumulative += total - present
        log(f"priority {priority}: {len(assets)} assets, {sum(len(a.files) for a in assets)} files, {human(total)} "
            f"({human(total - present)} to fetch); cumulative new {human(cumulative)}")
        if args.dry_run:
            for asset in assets:
                log(f"    {asset.source}:{asset.asset_id} {asset.item['resolution']} {human(asset.total)} "
                    + ", ".join(f"{f.channel}.{f.format}" for f in asset.files))
    verdict = "fits" if cumulative <= budget and free - cumulative >= floor else "DOES NOT FIT"
    log(f"estimate: {human(cumulative)} new bytes; {verdict} the budget and floor")
    if args.dry_run:
        return 1 if failures else 0

    before = disk_snapshot(root)
    started = utc_now()
    status = 0
    loaded = {s: load_pins(manifest_path(root, s, selection)) for s in plans}
    all_pins: Dict[str, str] = {}
    for pins, _, _ in loaded.values():
        all_pins.update(pins)
    # One fetcher so the lane budget and the disk floor are shared by every source.
    fetcher = Fetcher(root, http_factory, budget, floor, all_pins, args.repin, args.workers, log, free_bytes)
    for priority in sorted(by_priority):
        for source in sorted(plans):
            batch = [a for a in plans[source] if a.group["priority"] == priority]
            if batch:
                log(f"{source} priority {priority}: fetching {len(batch)} assets")
                fetcher.fetch_assets(https[source], batch)
    if fetcher.stopped_reason:
        failures.append(f"stopped early - {fetcher.stopped_reason}")
    for source, assets in plans.items():
        path = manifest_path(root, source, selection)
        _, previous, old_doc = loaded[source]
        records = dict(previous)
        acquired = utc_now()
        for asset in assets:
            statuses = {f.status for f in asset.files}
            if statuses <= {"present", "downloaded"}:
                records[asset.asset_id] = build_record(asset, snapshots[source][0], acquired, previous.get(asset.asset_id))
            else:
                bad = sorted(f"{f.rel_path}:{f.status}" for f in asset.files if f.status not in ("present", "downloaded"))
                failures.append(f"{source}:{asset.asset_id}: incomplete ({', '.join(bad[:4])})")
        source_new = sum(f.size for a in assets for f in a.files if f.status == "downloaded")
        order = {a.asset_id: (a.group["priority"], i) for i, a in enumerate(assets)}
        ordered_records = sorted(records.values(), key=lambda r: order.get(r["asset_id"], (99, r["asset_id"])))
        batch_log = list((old_doc or {}).get("batch_log", []))
        batch_log.append({"started_at_utc": started, "finished_at_utc": utc_now(), "new_bytes": source_new,
                          "run_new_bytes_all_sources": fetcher.new_bytes,
                          "command": "scripts/assets/fetch_cc0.py " + " ".join(argv or sys.argv[1:]),
                          "before": before, "after": disk_snapshot(root)})
        doc = {
            "schema_version": L.SCHEMA_VERSION,
            "kind": "asset-ledger",
            "ledger_id": f"{source}-{selection['name']}",
            "source": source,
            "purpose": selection.get("purpose"),
            "selection": L.posix(os.path.relpath(args.selection if args.selection.is_absolute() else root / args.selection, root)),
            "generator": "scripts/assets/fetch_cc0.py",
            "storage_root": f"{RAW_ROOT}/{source}",
            "credit": SOURCE_INFO[source]["credit"],
            "format_policy": selection.get("format_policy", {}).get(source),
            "license_snapshots": snapshots[source],
            "batch_log": batch_log,
            "records": ordered_records,
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        log(f"wrote {L.posix(str(path.relative_to(root)))}: {len(ordered_records)} records; {human(source_new)} new this run")
    for failure in failures:
        log("FAILURE: " + failure)
        status = 1
    return status


def main() -> int:
    try:
        return run()
    except FetchError as err:
        print("FETCH_ERROR:", err, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
