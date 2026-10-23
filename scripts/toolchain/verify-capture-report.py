#!/usr/bin/env python3
"""Require complete Unreal automation results from a rendered editor-game run."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import struct
import sys
import zlib

BOW_SPEC = importlib.util.spec_from_file_location("bow_capture_validation", Path(__file__).with_name("bow_capture_validation.py"))
bow_capture_validation = importlib.util.module_from_spec(BOW_SPEC)
BOW_SPEC.loader.exec_module(bow_capture_validation)


def problems(report: dict, log: str, status: int, shader_model: str) -> list[str]:
    failures = []
    if status:
        failures.append(f"editor exited {status}")
    tests = report.get("tests", [])
    if not tests:
        failures.append("no automation tests were reported")
    found = re.findall(r"Found (\d+) automation tests based on '[^']*'", log)
    if not found or sum(map(int, found)) != len(tests):
        failures.append("reported test count does not match discovered tests")
    if any(report.get(key, 0) for key in ("failed", "notRun", "inProcess")):
        failures.append("report contains failed or unfinished tests")
    for test in tests:
        events = [entry.get("event", {}) for entry in test.get("entries", [])]
        if (test.get("state") != "Success" or test.get("errors", 0)
                or any(event.get("type") == "Error" for event in events)):
            failures.append(f"unsuccessful test: {test.get('fullTestPath', '<unnamed>')}")
    devices = report.get("devices", [])
    if not devices or any("metal" not in device.get("rHI", "").lower() for device in devices):
        failures.append("report does not identify the Metal renderer")
    if shader_model != "auto" and any(
            device.get("renderMode", "").lower() != shader_model for device in devices):
        failures.append(f"actual shader model differs from requested {shader_model}")
    return failures


def log_completion_problems(receipt: dict, data: bytes, status: int) -> list[str]:
    """A quiet or merely exited editor does not establish a completed log."""
    failures = []
    if receipt.get("stream_eof") is not True:
        failures.append("capture log stream did not reach EOF")
    if receipt.get("failure"):
        failures.append(f"capture log collection: {receipt['failure']}")
    code = receipt.get("process_returncode")
    if type(code) is not int:
        failures.append("capture log receipt has no process exit status")
    elif not receipt.get("failure") and receipt.get("runner_status") != (code if code >= 0 else 128 - code):
        failures.append("capture log receipt has inconsistent process/runner status")
    if receipt.get("runner_status") != status:
        failures.append("capture runner exit differs from log receipt")
    if (receipt.get("log_bytes") != len(data)
            or receipt.get("log_sha256") != hashlib.sha256(data).hexdigest()):
        failures.append("capture log differs from completed stream receipt")
    return failures


def png_dimensions(data: bytes) -> tuple[int, int]:
    """Reject truncated/corrupt screenshots without changing their pixels."""
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("not a PNG")
    offset, dimensions, image_data = 8, None, bytearray()
    row_sizes = []
    while offset + 12 <= len(data):
        size = struct.unpack_from(">I", data, offset)[0]
        kind = data[offset + 4:offset + 8]
        end = offset + 12 + size
        if end > len(data):
            raise ValueError("truncated PNG chunk")
        payload = data[offset + 8:end - 4]
        if zlib.crc32(kind + payload) != struct.unpack_from(">I", data, end - 4)[0]:
            raise ValueError("PNG chunk checksum mismatch")
        if dimensions is None:
            if kind != b"IHDR" or size != 13:
                raise ValueError("PNG has no valid header")
            dimensions = struct.unpack_from(">II", payload)
            if not all(0 < value <= 16384 for value in dimensions):
                raise ValueError("invalid PNG dimensions")
            depth, color, compression, filtering, interlace = payload[8:]
            depths = {0: (1, 2, 4, 8, 16), 2: (8, 16), 3: (1, 2, 4, 8), 4: (8, 16), 6: (8, 16)}
            if depth not in depths.get(color, ()) or compression or filtering or interlace not in (0, 1):
                raise ValueError("invalid PNG format")
            bits = depth * {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color]
            passes = ((0, 0, 1, 1),) if not interlace else (
                (0, 0, 8, 8), (4, 0, 8, 8), (0, 4, 4, 8), (2, 0, 4, 4),
                (0, 2, 2, 4), (1, 0, 2, 2), (0, 1, 1, 2))
            for x, y, dx, dy in passes:
                columns = max(0, (dimensions[0] - x + dx - 1) // dx)
                rows = max(0, (dimensions[1] - y + dy - 1) // dy)
                if columns:
                    row_sizes.extend([(columns * bits + 7) // 8] * rows)
        if kind == b"IDAT":
            image_data.extend(payload)
        if kind == b"IEND":
            if size or end != len(data) or not image_data:
                raise ValueError("incomplete PNG image")
            decoder = zlib.decompressobj()
            expected_bytes = sum(row_sizes) + len(row_sizes)
            pixels = decoder.decompress(image_data, expected_bytes + 1)
            if not decoder.eof or decoder.unused_data or len(pixels) != expected_bytes:
                raise ValueError("incomplete or oversized PNG pixel stream")
            row_start = 0
            for row_size in row_sizes:
                if pixels[row_start] > 4:
                    raise ValueError("invalid PNG row filter")
                row_start += row_size + 1
            return dimensions
        offset = end
    raise ValueError("PNG has no end chunk")


def archive_frames(log: str, report: dict, project: Path, engine_base: Path,
                   output: Path, start_ns: int, width: int, height: int) -> list[dict]:
    """Copy acknowledged original frames, retaining each fixture's scope."""
    kinds = {
        "SORA_ART_REVIEW_FRAME": ("SoraCapture.ArtReview.", "art-review"),
        "SORA_REGISTRY_FIXTURE_FRAME": ("SoraCapture.RegistryFixture.", "completed-save registry UI fixture; not playthrough evidence"),
        "SORA_WEAPON_HUD_FIXTURE_FRAME": ("SoraCapture.WeaponHUDFixture.", "prepared gameplay UI fixture; not playthrough evidence"),
        "SORA_BOW_AIM_FRAME": ("SoraCapture.BowAim.", "live mapped bow aim from prepared checkpoint/view; not playthrough or art acceptance"),
    }
    # Failed automation replays captured log events through
    # LogAutomationController, appending " [log]". Those are not new frame
    # acknowledgements. Accept only the original UE_LOG(LogTemp, Display)
    # records, with the optional engine timestamp/frame-number prefix.
    names = re.findall(r"^(?:\[[^\]\r\n]*\])*[ \t]*LogTemp: Display: ("
                       + "|".join(kinds) + r") ([^\r\n]+\.png)[ \t]*$", log, re.MULTILINE)
    for marker, (prefix, _) in kinds.items():
        if not any(kind == marker for kind, _ in names) and any(
                test.get("fullTestPath", "").startswith(prefix) for test in report.get("tests", [])):
            raise ValueError(f"{prefix} reported no screenshot paths")
    screenshot_root = (project / "Saved/Screenshots").resolve()
    frames = []
    bow_sequences = {}
    seen = set()
    for marker, name in names:
        path = (engine_base / name.strip()).resolve()
        relative = path.relative_to(screenshot_root)
        if relative in seen:
            raise ValueError(f"duplicate/overwritten capture frame: {relative}")
        seen.add(relative)
        if path.stat().st_mtime_ns < start_ns:
            raise ValueError(f"stale capture frame: {relative}")
        data = path.read_bytes()
        if png_dimensions(data) != (width, height):
            raise ValueError(f"unexpected screenshot dimensions: {relative}")
        target = output / "frames" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(data)
        frame = {"path": str(target.relative_to(output)), "source": str(path),
                       "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                       "capture_kind": kinds[marker][1]}
        if marker == "SORA_BOW_AIM_FRAME":
            sidecar = path.with_suffix(".json")
            if sidecar.stat().st_mtime_ns < start_ns:
                raise ValueError("stale bow frame observations")
            metadata_bytes = sidecar.read_bytes()
            metadata = json.loads(metadata_bytes)
            if not isinstance(metadata, dict) or metadata.get("phase") != path.stem:
                raise ValueError("bow frame observations do not identify their original PNG")
            pixels = bow_capture_validation.verify_frame(metadata, data, width, height)
            bow_sequences.setdefault(path.parent, []).append((metadata, pixels))
            metadata_target = target.with_suffix(".json")
            with metadata_target.open("xb") as stream:
                stream.write(metadata_bytes)
            frame.update(observations=str(metadata_target.relative_to(output)),
                         observations_sha256=hashlib.sha256(metadata_bytes).hexdigest(), reticle_pixels=pixels)
        frames.append(frame)
    for sequence in bow_sequences.values():
        bow_capture_validation.verify_sequence(sequence)
    return frames


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("log", type=Path)
    parser.add_argument("status", type=int)
    parser.add_argument("shader_model", choices=("auto", "sm5", "sm6"))
    parser.add_argument("--log-completion", type=Path,
                        help="owned stream receipt; required when archiving a capture")
    parser.add_argument("--archive", nargs=7,
                        metavar=("PROJECT", "ENGINE_BASE", "OUTPUT", "START_NS", "WIDTH", "HEIGHT", "FILTER"))
    args = parser.parse_args()
    report_path, log_path = args.report, args.log
    status, shader_model = args.status, args.shader_model
    try:
        report = json.loads(report_path.read_text(encoding="utf-8-sig"))
        log_data = log_path.read_bytes()
        # Match read_text's universal-newline parsing while hashing raw bytes.
        log = log_data.decode(errors="replace").replace("\r\n", "\n").replace("\r", "\n")
    except (OSError, ValueError) as error:
        print(f"FAIL: missing or invalid capture report: {error}", file=sys.stderr)
        return 1
    completion = None
    completion_sha256 = None
    failures = []
    if args.log_completion:
        try:
            receipt_data = args.log_completion.read_bytes()
            parsed = json.loads(receipt_data)
            if not isinstance(parsed, dict):
                raise ValueError("receipt is not an object")
            completion = parsed
            completion_sha256 = hashlib.sha256(receipt_data).hexdigest()
            failures.extend(log_completion_problems(completion, log_data, status))
        except (OSError, ValueError) as error:
            failures.append(f"missing or invalid log completion receipt: {error}")
    elif args.archive:
        failures.append("capture archive requires a log completion receipt")
    # A collection timeout is not an editor failure: retain its actual exit
    # separately and report the failed EOF gate above.
    editor_status = completion.get("process_returncode") if completion else None
    failures.extend(problems(report, log, editor_status if type(editor_status) is int else status, shader_model))
    if args.archive:
        project, engine_base, output = map(Path, args.archive[:3])
        start_ns, width, height = map(int, args.archive[3:6])
        frames = []
        try:
            frames = archive_frames(log, report, project, engine_base, output, start_ns, width, height)
        except (OSError, ValueError, zlib.error) as error:
            failures.append(f"screenshot archive: {error}")
        manifest = {"source_commit": (output / "source-commit.txt").read_text().strip(),
                    "source_status": (output / "source-status.txt").read_text(),
                    "filter": args.archive[6], "requested_shader_model": shader_model,
                    "devices": report.get("devices", []), "started_ns": start_ns,
                    "viewport": [width, height], "frames": frames, "failures": failures,
                    "evidence": "uncooked editor-game", "release_qualified": False,
                    "report_sha256": hashlib.sha256(report_path.read_bytes()).hexdigest(),
                    "log_sha256": hashlib.sha256(log_data).hexdigest(),
                    "log_completion": completion, "log_completion_sha256": completion_sha256}
        (output / "capture.json").write_text(json.dumps(manifest, indent=2) + "\n")
    for test in report.get("tests", []):
        print(f"{test.get('state', 'Unknown')}: {test.get('fullTestPath', '<unnamed>')}")
    print(f"Report: {report_path}")
    if failures:
        print("FAIL: " + "; ".join(failures), file=sys.stderr)
        return 1
    print(f"PASS: {len(report['tests'])} rendered automation tests; "
          "uncooked editor-game evidence, not packaged qualification")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
