"""Unit tests for scripts/assets/fetch_cc0.py against a local fake Poly Haven/ambientCG.

The fake server supports HTTP Range, a 302 redirect for ambientCG downloads and the
Backblaze x-bz-content-sha1 header, so resume, member extraction, checksum and
allowlist behaviour are exercised without touching the network.
"""
from __future__ import annotations

import hashlib
import http.server
import io
import json
import shutil
import sys
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import fetch_cc0 as F  # noqa: E402


def md5(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


class FakeUpstream:
    def __init__(self):
        self.files = {}
        self.requests = []
        self.bad_md5 = set()
        self.evil_host = False
        handler = self._handler()
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.texture = {name: (name * 5000).encode()[:40000 + i] for i, name in enumerate(["diff", "nor", "arm"])}
        self.hdr = b"#?RADIANCE\n" + b"x" * 30000
        for name, data in self.texture.items():
            self.files[f"/dl/hinoki_planks_{name}_2k"] = data
        self.files["/dl/sky_4k.hdr"] = self.hdr
        members = {"Rope001_2K-JPG_Color.jpg": b"C" * 20000, "Rope001_2K-JPG_NormalDX.jpg": b"N" * 25000,
                   "Rope001_2K-JPG_NormalGL.jpg": b"G" * 25000, "Rope001_2K-JPG_Roughness.jpg": b"R" * 9000,
                   "Rope001.png": b"P" * 100}
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
            for name, data in members.items():
                archive.writestr(name, data)
        self.members = members
        self.files["/cdn/Rope001_2K-JPG.zip"] = buffer.getvalue()
        self.files["/license/ph"] = b"<p>Our assets are all licensed as CC0 , which is effectively Public Domain</p>"
        self.files["/license/ph-api"] = b"The API is free to access and use by anyone - individuals"
        self.files["/license/acg"] = b"All ambientCG assets are provided under the Creative Commons CC0 1.0 Universal License ."

    def start(self):
        self.thread.start()
        return self

    def stop(self):
        self.server.shutdown()
        self.server.server_close()

    def api(self, path: str):
        dl_host = "evil.example" if self.evil_host else "127.0.0.1"
        port = self.server.server_address[1]
        if path == "/ph/assets":
            return {"hinoki_planks": {"name": "Hinoki Planks", "authors": {"Charlotte Baglioni": "All"}, "type": 1,
                                      "description": "hinoki with deep mortar joints", "tags": ["wood"], "dimensions": [1890, 1890]},
                    "sky": {"name": "Sky", "authors": {"Greg Zaal": "All"}, "type": 0, "description": "sky", "tags": []}}
        if path == "/ph/files/hinoki_planks":
            out = {}
            for channel, name, fmt in (("Diffuse", "diff", "jpg"), ("nor_dx", "nor", "exr"), ("arm", "arm", "exr")):
                data = self.texture[name]
                digest = "0" * 32 if name in self.bad_md5 else md5(data)
                out[channel] = {"2k": {fmt: {"url": f"http://{dl_host}:{port}/dl/hinoki_planks_{name}_2k", "size": len(data), "md5": digest}}}
            return out
        if path == "/ph/files/sky":
            return {"hdri": {"4k": {"hdr": {"url": f"http://127.0.0.1:{port}/dl/sky_4k.hdr", "size": len(self.hdr), "md5": md5(self.hdr)}}}}
        if path == "/acg/assets":
            size = len(self.files["/cdn/Rope001_2K-JPG.zip"])
            return {"assets": [{"id": "Rope001", "title": "Rope 001", "technique": "surface-fully-procedural",
                                "maps": ["color", "normal", "roughness"], "tags": ["rope"],
                                "downloads": [{"attributes": "2K-JPG", "extension": "zip", "size": size,
                                               "url": f"http://127.0.0.1:{port}/get?file=Rope001_2K-JPG.zip"}]}]}
        return None

    def _handler(self):
        upstream = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _serve(self, body_wanted: bool):
                parsed = urlparse(self.path)
                upstream.requests.append((self.command, self.path, self.headers.get("Range")))
                if parsed.path == "/get":
                    name = parse_qs(parsed.query)["file"][0]
                    self.send_response(302)
                    self.send_header("Location", f"/cdn/{name}")
                    self.end_headers()
                    return
                payload = upstream.api(parsed.path)
                if payload is not None:
                    data = json.dumps(payload).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    if body_wanted:
                        self.wfile.write(data)
                    return
                data = upstream.files.get(parsed.path)
                if data is None:
                    self.send_response(404)
                    self.end_headers()
                    return
                status, body = 200, data
                rng = self.headers.get("Range")
                if rng:
                    start, end = rng.replace("bytes=", "").split("-")
                    start, end = int(start), int(end) if end else len(data) - 1
                    status, body = 206, data[start:end + 1]
                self.send_response(status)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("x-bz-content-sha1", hashlib.sha1(data).hexdigest())
                if status == 206:
                    self.send_header("Content-Range", f"bytes {start}-{start + len(body) - 1}/{len(data)}")
                self.end_headers()
                if body_wanted:
                    self.wfile.write(body)

            def do_GET(self):
                self._serve(True)

            def do_HEAD(self):
                self._serve(False)

        return Handler


class FetchCase(unittest.TestCase):
    def setUp(self):
        self.up = FakeUpstream().start()
        self.root = Path(tempfile.mkdtemp(prefix="fetch-test-"))
        base = self.up.base
        self.saved_pages = F.LICENSE_PAGES
        F.LICENSE_PAGES = {
            "polyhaven": [("polyhaven-license", base + "/license/ph", "Our assets are all licensed as CC0"),
                          ("polyhaven-api-terms", base + "/license/ph-api", "free to access and use by anyone")],
            "ambientcg": [("ambientcg-license", base + "/license/acg",
                           "All ambientCG assets are provided under the Creative Commons CC0 1.0 Universal License")],
        }
        selection = {
            "format": "sora-cc0-selection/1", "name": "test", "purpose": "unit test",
            "groups": [
                {"priority": 3, "source": "polyhaven", "kind": "texture", "items": [
                    {"id": "hinoki_planks", "resolution": "2k", "game_use": [{"place": "pl_tsumagizaka_dojo", "use": "floor"}],
                     "period_flags": [{"risk": "knotty"}], "period_risk": "low"}]},
                {"priority": 5, "source": "polyhaven", "kind": "hdri", "items": [{"id": "sky", "resolution": "4k"}]},
                {"priority": 7, "source": "ambientcg", "kind": "material", "download": "2K-JPG", "items": [{"id": "Rope001"}]},
            ],
        }
        (self.root / "sel.json").write_text(json.dumps(selection))
        self.logs = []

    def tearDown(self):
        F.LICENSE_PAGES = self.saved_pages
        self.up.stop()
        shutil.rmtree(self.root, ignore_errors=True)  # temp directory created by this test only

    def run_fetch(self, *extra, free=10 ** 12):
        base = self.up.base

        def http_factory(hosts):
            return F.Http(list(hosts) + ["127.0.0.1"], allow_http=True, retries=2, backoff=0.01, timeout=10)

        factories = {
            "polyhaven": lambda http: F.PolyHavenSource(http, api_base=base + "/ph", dl_hosts=("127.0.0.1",)),
            "ambientcg": lambda http: F.AmbientCGSource(http, api_base=base + "/acg/assets"),
        }
        return F.run(["--selection", str(self.root / "sel.json"), *extra], root=self.root, http_factory=http_factory,
                     source_factories=factories, log=self.logs.append, free_bytes=lambda: free)

    def manifest(self, source):
        return json.loads((self.root / f"scripts/assets/manifests/{source}-test.json").read_text())

    def test_full_fetch_writes_pinned_schema2_records(self):
        self.assertEqual(self.run_fetch(), 0, self.logs)
        ph = self.manifest("polyhaven")
        self.assertEqual(ph["schema_version"], 2)
        hinoki = next(r for r in ph["records"] if r["asset_id"] == "hinoki_planks")
        self.assertEqual(hinoki["tier"], "PUB-CC0")
        self.assertEqual(hinoki["storage"], "local-raw")
        self.assertEqual(hinoki["game_use"][0]["place"], "pl_tsumagizaka_dojo")
        self.assertTrue(any("mortar" in f["risk"] for f in hinoki["period_flags"]))
        for entry in hinoki["files"]:
            data = (self.root / entry["path"]).read_bytes()
            self.assertEqual(entry["sha256"], hashlib.sha256(data).hexdigest())
            self.assertEqual(entry["upstream_sha1"], hashlib.sha1(data).hexdigest())
            self.assertTrue(entry["path"].startswith("Local/ThirdPartyRaw/cc0/polyhaven/hinoki_planks/"))
        acg = self.manifest("ambientcg")
        rope = acg["records"][0]
        names = sorted(Path(f["path"]).name for f in rope["files"])
        self.assertEqual(names, ["Rope001_2K-JPG_Color.jpg", "Rope001_2K-JPG_NormalDX.jpg", "Rope001_2K-JPG_Roughness.jpg"])
        for entry in rope["files"]:
            self.assertEqual((self.root / entry["path"]).read_bytes(), self.up.members[Path(entry["path"]).name])
        self.assertFalse(any(p.suffix == ".zip" for p in self.root.rglob("*")), "archive must not be stored")
        self.assertTrue((self.root / ph["license_snapshots"][0]["path"]).is_file())
        self.assertEqual(len(ph["batch_log"]), 1)

    def test_rerun_verifies_and_skips(self):
        self.assertEqual(self.run_fetch(), 0)
        count = len([r for r in self.up.requests if r[1].startswith("/dl/")])
        self.assertEqual(self.run_fetch(), 0, self.logs)
        self.assertEqual(len([r for r in self.up.requests if r[1].startswith("/dl/")]), count)

    def test_partial_download_resumes_with_range(self):
        data = self.up.texture["nor"]
        dest = self.root / "Local/ThirdPartyRaw/cc0/polyhaven/hinoki_planks/hinoki_planks_nor_2k.partial"
        dest.parent.mkdir(parents=True)
        dest.write_bytes(data[:1000])
        self.assertEqual(self.run_fetch("--only", "hinoki_planks"), 0, self.logs)
        self.assertIn(("GET", "/dl/hinoki_planks_nor_2k", f"bytes=1000-{len(data) - 1}"), self.up.requests)
        self.assertEqual((self.root / "Local/ThirdPartyRaw/cc0/polyhaven/hinoki_planks/hinoki_planks_nor_2k").read_bytes(), data)

    def test_upstream_md5_mismatch_is_rejected_and_kept(self):
        self.up.bad_md5.add("arm")
        self.assertEqual(self.run_fetch("--only", "hinoki_planks"), 1)
        folder = self.root / "Local/ThirdPartyRaw/cc0/polyhaven/hinoki_planks"
        self.assertFalse((folder / "hinoki_planks_arm_2k").exists())
        self.assertTrue((folder / "hinoki_planks_arm_2k.partial.rejected").exists())
        self.assertFalse(any(r["asset_id"] == "hinoki_planks" for r in self.manifest("polyhaven")["records"]))

    def test_host_outside_allowlist_is_refused(self):
        self.up.evil_host = True
        self.assertEqual(self.run_fetch("--only", "hinoki_planks"), 1)
        self.assertTrue(any("unexpected Poly Haven production host" in line or "allowlist" in line for line in self.logs), self.logs)
        self.assertFalse((self.root / "Local/ThirdPartyRaw/cc0/polyhaven/hinoki_planks").exists())

    def test_pinned_hash_change_stops(self):
        self.assertEqual(self.run_fetch("--only", "sky"), 0)
        manifest_path = self.root / "scripts/assets/manifests/polyhaven-test.json"
        doc = json.loads(manifest_path.read_text())
        doc["records"][0]["files"][0]["sha256"] = "0" * 64
        manifest_path.write_text(json.dumps(doc))
        self.assertEqual(self.run_fetch("--only", "sky"), 1)
        self.assertTrue(any("differs from pinned" in line for line in self.logs))

    def test_dry_run_writes_nothing(self):
        self.assertEqual(self.run_fetch("--dry-run"), 0)
        self.assertFalse((self.root / "Local").exists())
        self.assertFalse((self.root / "scripts").exists())
        self.assertTrue(any(line.startswith("estimate:") for line in self.logs))

    def test_budget_and_disk_floor_stop_cleanly(self):
        self.assertEqual(self.run_fetch("--budget-gib", "0.00005"), 1)
        self.assertTrue(any("lane budget" in line for line in self.logs), self.logs)
        self.logs.clear()
        self.assertEqual(self.run_fetch("--min-free-gib", "2", free=2 * F.GIB + 10), 1)
        self.assertTrue(any("floor" in line for line in self.logs if line.startswith("FAILURE")), self.logs)

    def test_https_required_without_test_override(self):
        http = F.Http(["127.0.0.1"])
        with self.assertRaises(F.FetchError):
            http.check_url(self.up.base + "/ph/assets")
        with self.assertRaises(F.FetchError):
            F.Http(["api.polyhaven.com"]).check_url("https://evil.example/x")


if __name__ == "__main__":
    unittest.main()
