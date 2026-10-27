#!/usr/bin/env python3
"""Require complete Unreal automation results from a rendered editor-game run."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
import zlib

BOW_SPEC = importlib.util.spec_from_file_location("bow_capture_validation", Path(__file__).with_name("bow_capture_validation.py"))
bow_capture_validation = importlib.util.module_from_spec(BOW_SPEC)
BOW_SPEC.loader.exec_module(bow_capture_validation)
CODEX_SPEC = importlib.util.spec_from_file_location("codex_capture_validation", Path(__file__).with_name("codex_capture_validation.py"))
codex_capture_validation = importlib.util.module_from_spec(CODEX_SPEC)
CODEX_SPEC.loader.exec_module(codex_capture_validation)
NANITE_SPEC = importlib.util.spec_from_file_location("nanite_capture_validation", Path(__file__).with_name("nanite_capture_validation.py"))
nanite_capture_validation = importlib.util.module_from_spec(NANITE_SPEC)
NANITE_SPEC.loader.exec_module(nanite_capture_validation)
PROBE_SPEC = importlib.util.spec_from_file_location("timber_probe_capture_validation", Path(__file__).with_name("timber_probe_capture_validation.py"))
timber_probe_capture_validation = importlib.util.module_from_spec(PROBE_SPEC)
PROBE_SPEC.loader.exec_module(timber_probe_capture_validation)


CARGO_SPEC = importlib.util.spec_from_file_location("cargo_capture_validation", Path(__file__).with_name("cargo_capture_validation.py"))
cargo_capture_validation = importlib.util.module_from_spec(CARGO_SPEC)
CARGO_SPEC.loader.exec_module(cargo_capture_validation)


WITHDRAWAL_SPEC = importlib.util.spec_from_file_location("withdrawal_capture_validation", Path(__file__).with_name("withdrawal_capture_validation.py"))
withdrawal_capture_validation = importlib.util.module_from_spec(WITHDRAWAL_SPEC)
WITHDRAWAL_SPEC.loader.exec_module(withdrawal_capture_validation)


class WithdrawalCaptureEvidenceError(ValueError):
    """Preserve originals even when live retreat observations fail."""
    def __init__(self, message, frames):
        super().__init__(message)
        self.frames = frames


class NaniteDrawEvidenceError(ValueError):
    """The originals are complete, but their visible-draw gate failed."""
    def __init__(self, message, frames):
        super().__init__(message)
        self.frames = frames


class CargoCaptureEvidenceError(ValueError):
    """Retain authenticated originals when observed cargo semantics fail."""
    def __init__(self, message, frames):
        super().__init__(message)
        self.frames = frames


class CampaignCaptureEvidenceError(ValueError):
    """Retain authenticated fresh campaign originals on incomplete associations."""
    def __init__(self, message, frames):
        super().__init__(message)
        self.frames = frames


class FrontEndCaptureEvidenceError(ValueError):
    """Keep authenticated menu originals when the tour is incomplete."""
    def __init__(self, message, frames):
        super().__init__(message)
        self.frames = frames


def frontend_frames(log: str, report: dict, project: Path, output: Path,
                    width: int, height: int) -> tuple[list[tuple[str, dict]], list[str]]:
    """The menu tour uses engine screenshot acknowledgements, not art markers."""
    tests = [test.get("fullTestPath", "") for test in report.get("tests", [])
             if test.get("fullTestPath", "").startswith("SoraArena.UIRendered.")]
    if not tests:
        return [], []
    if tests != ["SoraArena.UIRendered.FrontEndScreens"]:
        raise ValueError("unsupported or duplicate rendered front-end tour")
    # Execution order differs from the numeric filenames: settings precede
    # the controller tour. Bind this supported inventory to the run's source.
    expected = ("01_Title", "02_MainKeyboard", "03_ChapterSelect", "04_PracticeLobby",
                "05_Wallet", "06_Settings", "07_Credits", "08_CreditsScrolled", "09_QuitConfirm",
                "12_Graphics", "13_Audio", "14_Subtitles", "15_Controls", "16_ControlsBindings",
                "17_Rebind", "18_Accessibility", "10_MainPad", "11_TitlePad", "19_Pause")
    commit = (output / "source-commit.txt").read_text().strip()
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("front-end archive requires its exact source commit")
    source_path = "Source/SoraArena/Private/SoraFrontEndAutomation.cpp"
    result = subprocess.run(["git", "-C", str(project), "show", f"{commit}:{source_path}"], capture_output=True)
    if result.returncode:
        raise ValueError("cannot authenticate front-end tour source")
    source = result.stdout.decode().split("bool FSoraFrontEndRenderedTest::RunTest", 1)
    inventory = re.findall(r'TEXT\("([0-9]{2}_[A-Za-z0-9_]+)"\)', source[1]) if len(source) == 2 else []
    if Counter(inventory) != Counter(expected):
        raise ValueError("unsupported committed front-end screenshot inventory")
    records = re.findall(r'^(?:\[[^\]\r\n]*\])*[ \t]*LogCore: Display: Tracing Screenshot '
                         r'"([0-9]{2}_[A-Za-z0-9_]+)" taken with size: ([0-9]+) x ([0-9]+)[ \t]*$',
                         log, re.MULTILINE)
    counts = Counter(name for name, _, _ in records)
    errors = []
    if [name for name, _, _ in records] != list(expected):
        errors.append("front-end tour has missing, duplicate, unknown or reordered screenshot acknowledgements")
    frames = []
    for name, shot_width, shot_height in records:
        if name not in expected or counts[name] != 1:
            continue  # A duplicate may have overwritten its first original.
        if (int(shot_width), int(shot_height)) != (width, height):
            errors.append(f"front-end acknowledgement has wrong dimensions: {name}")
            continue
        path = project.resolve() / "Saved/Screenshots/SoraFrontEnd" / f"{width}x{height}" / (name + ".png")
        if path.resolve() != path:
            errors.append(f"front-end original path is a symlink: {name}")
            continue
        frames.append((str(path), dict(test=tests[0], screen=name, source_commit=commit,
            shot_inventory_path=source_path, shot_inventory_sha256=hashlib.sha256(result.stdout).hexdigest(),
            acknowledgement=f'Tracing Screenshot "{name}" taken with size: {width} x {height}')))
    return frames, errors


def campaign_frames(log: str, report: dict, project: Path, output: Path,
                    width: int, height: int) -> tuple[list[tuple[str, dict]], list[str]]:
    """Bind original campaign acknowledgements to exact committed shot/catalog data."""
    tests = [test.get("fullTestPath", "") for test in report.get("tests", [])
             if test.get("fullTestPath", "").startswith("SoraCapture.Campaign.")]
    records = re.findall(r"^(?:\[[^\]\r\n]*\])*[ \t]*LogTemp: Display: SORA_CAPTURE "
                         r"([A-Za-z0-9_]+) chapter ([0-9]+) ([^\s]+) \(([^)\r\n]+)\): ([^\r\n]*)$",
                         log, re.MULTILINE)
    if not tests and not records:
        return [], []
    chapters = []
    for test in tests:
        match = re.fullmatch(r"SoraCapture\.Campaign\.Chapter([1-8])", test)
        if not match or int(match[1]) in chapters:
            raise ValueError("invalid or duplicate Campaign chapter report")
        chapters.append(int(match[1]))
    commit = (output / "source-commit.txt").read_text().strip()
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Campaign archive requires its exact source commit")

    def blob(name):
        result = subprocess.run(["git", "-C", str(project), "show", f"{commit}:{name}"], capture_output=True)
        if result.returncode:
            raise ValueError(f"cannot authenticate Campaign source blob: {name}")
        return result.stdout

    source_path = "Source/SoraArena/Private/SoraCaptureAutomation.cpp"
    source_raw = blob(source_path)
    source = source_raw.decode()
    table = re.search(r"const FShot Shots\[\] = \{(.*?)\n\};", source, re.DOTALL)
    pattern = r'\{(\d+),\s*(\d+),\s*ESubject::(\w+),\s*TEXT\("([A-Za-z0-9_]+)"\)(?:,\s*\d+)?\}'
    if not table or re.sub(pattern, "", table[1]).strip(" \r\n\t,"):
        raise ValueError("unsupported committed Campaign shot inventory")
    subjects = dict(re.findall(r'case ESubject::(\w+):\s*return TEXT\("([^"\r\n]+)"\);', source))
    expected = {}; chapter_names = {chapter: [] for chapter in chapters}; catalog_hashes = {}
    for chapter in chapters:
        catalog_path = f"Content/Data/campaign/chapter_{chapter:02d}.json"
        raw = blob(catalog_path); catalog = json.loads(raw)
        catalog_hashes[chapter] = hashlib.sha256(raw).hexdigest()
        for ch, beat, kind, name in re.findall(pattern, table[1]):
            if int(ch) + 1 != chapter:
                continue
            if name in expected or kind not in subjects:
                raise ValueError("ambiguous committed Campaign shot inventory")
            try:
                beat_id = catalog["beats"][int(beat)]["id"]
            except (KeyError, IndexError, TypeError) as error:
                raise ValueError("Campaign shot does not identify a committed catalog beat") from error
            expected[name] = (chapter, beat_id, subjects[kind]); chapter_names[chapter].append(name)
        if not chapter_names[chapter]:
            raise ValueError("reported Campaign chapter has no committed shots")
    # A repeated basename can have been overwritten by its later capture.
    # Exclude every association for that name, even if the later record has
    # mismatched fields. Replayed log events are not new acknowledgements.
    records = [record for record in records if not record[-1].endswith(" [log]")]
    counts = Counter(record[0] for record in records)
    ambiguous = {name for name, count in counts.items() if count > 1}
    frames = []; errors = [f"duplicate/ambiguous Campaign acknowledgement: {name}" for name in sorted(ambiguous)]
    actual = {chapter: [] for chapter in chapters}
    for name, chapter_text, beat, subject, note in records:
        if name in ambiguous:
            continue
        chapter = int(chapter_text)
        if expected.get(name) != (chapter, beat, subject):
            errors.append(f"Campaign acknowledgement differs from committed chapter/beat/subject/name: {name}")
            continue
        actual[chapter].append(name)
        folder = (project / "Saved/Screenshots/SoraCapture" / f"{width}x{height}").resolve()
        path = folder / (name + ".png")
        if path.resolve() != path:
            errors.append(f"Campaign original filename is a symlink: {name}")
            continue
        frames.append((str(path), dict(chapter=chapter, beat=beat, subject=subject, observed=note,
            source_commit=commit, shot_inventory_path=source_path, shot_inventory_sha256=hashlib.sha256(source_raw).hexdigest(),
            catalog_path=f"Content/Data/campaign/chapter_{chapter:02d}.json", catalog_sha256=catalog_hashes[chapter])))
    for chapter in chapters:
        if actual[chapter] != chapter_names[chapter]:
            errors.append(f"Campaign Chapter{chapter} is missing, reordered or has rejected screenshot acknowledgements")
    return frames, errors


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
        "SORA_CARGO_FRAME": ("SoraCapture.Cargo.", cargo_capture_validation.SCOPE),
        "SORA_WITHDRAWAL_FRAME": ("SoraCapture.HorseWithdrawal.", withdrawal_capture_validation.SCOPE),
        "SORA_CODEX_FRAME": ("SoraCapture.Codex.", codex_capture_validation.SCOPE),
        "SORA_NANITE_DRAW_FRAME": ("SoraCapture.NaniteDraw.", nanite_capture_validation.SCOPE),
        "SORA_TIMBER_PROBE_FRAME": ("SoraCapture.TimberProbe.", timber_probe_capture_validation.SCOPE),
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
    campaign, campaign_errors = campaign_frames(log, report, project, output, width, height)
    campaign_metadata = {path: data for path, data in campaign}
    names.extend(("SORA_CAPTURE", path) for path, _ in campaign)
    kinds["SORA_CAPTURE"] = ("SoraCapture.Campaign.", "assisted campaign checkpoint/camera capture; not playthrough or art acceptance")
    frontend, frontend_errors = frontend_frames(log, report, project, output, width, height)
    frontend_metadata = dict(frontend)
    names.extend(("SORA_FRONTEND", path) for path, _ in frontend)
    kinds["SORA_FRONTEND"] = ("SoraArena.UIRendered.", "rendered menu navigation tour; not visual approval or playthrough evidence")
    screenshot_root = (project / "Saved/Screenshots").resolve()
    frames = []
    bow_sequences = {}
    codex_sequences = {}
    cargo_sequences = {}
    withdrawal_sequences = {}
    nanite_sequences = {}
    probe_sequences = {}
    seen = set()
    for marker, name in names:
        try:
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
        except (OSError, ValueError, zlib.error) as error:
            if marker == "SORA_FRONTEND":
                frontend_errors.append(str(error))
                continue
            if marker != "SORA_CAPTURE":
                raise
            campaign_errors.append(str(error))
            continue
        target = output / "frames" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(data)
        frame = {"path": str(target.relative_to(output)), "source": str(path),
                       "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                       "capture_kind": kinds[marker][1]}
        if marker == "SORA_CAPTURE":
            frame["campaign"] = campaign_metadata[name]
        if marker == "SORA_FRONTEND":
            frame["frontend"] = frontend_metadata[name]
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
        if marker == "SORA_WITHDRAWAL_FRAME":
            withdrawal_sequences.setdefault(path.parent, []).append((path, target, frame))
        if marker == "SORA_CARGO_FRAME":
            cargo_sequences.setdefault(path.parent, []).append((path, target, frame))
        if marker == "SORA_CODEX_FRAME":
            codex_sequences.setdefault(path.parent, []).append((path, target, frame))
        if marker == "SORA_NANITE_DRAW_FRAME":
            nanite_sequences.setdefault(path.parent, []).append((path, target, frame))
        if marker == "SORA_TIMBER_PROBE_FRAME":
            probe_sequences.setdefault(path.parent, []).append((path, target, frame))
        frames.append(frame)
    if withdrawal_sequences:
        expected = [test.get("fullTestPath") for test in report.get("tests", [])
                    if test.get("fullTestPath", "").startswith("SoraCapture.HorseWithdrawal.")]
        if len(withdrawal_sequences) != 1 or expected != ["SoraCapture.HorseWithdrawal.Live"]:
            raise WithdrawalCaptureEvidenceError("withdrawal requires one matching Live run", frames)
        for folder, sequence in withdrawal_sequences.items():
            sidecar = (folder / "capture.json").resolve()
            if sidecar.parent != folder or sidecar.stat().st_mtime_ns < max(start_ns, *(p.stat().st_mtime_ns for p, _, _ in sequence)):
                raise WithdrawalCaptureEvidenceError("stale/escaped withdrawal metadata", frames)
            raw = sidecar.read_bytes()
            target = sequence[0][1].parent / "capture.json"
            with target.open("xb") as stream:
                stream.write(raw)
            for path, _, frame in sequence:
                frame.update(observations=str(target.relative_to(output)), observations_source=str(sidecar),
                             observations_sha256=hashlib.sha256(raw).hexdigest(), withdrawal_phase=path.stem)
            try:
                withdrawal_capture_validation.verify_sequence(json.loads(raw), [p.name for p, _, _ in sequence], width, height)
            except (ValueError, TypeError, KeyError) as error:
                raise WithdrawalCaptureEvidenceError(str(error), frames) from error
    if cargo_sequences:
        expected = [test.get("fullTestPath") for test in report.get("tests", [])
                    if test.get("fullTestPath", "").startswith("SoraCapture.Cargo.")]
        if len(cargo_sequences) != 1 or expected != ["SoraCapture.Cargo.Transfer"]:
            raise ValueError("cargo capture requires one matching four-frame Transfer run")
        for folder, sequence in cargo_sequences.items():
            sidecar = (folder / "capture.json").resolve()
            if sidecar.parent != folder:
                raise ValueError("cargo source metadata escapes its original frame folder")
            if sidecar.stat().st_mtime_ns < max(start_ns, *(path.stat().st_mtime_ns for path, _, _ in sequence)):
                raise ValueError("stale cargo source capture metadata")
            raw = sidecar.read_bytes()
            target = sequence[0][1].parent / "capture.json"
            # Preserve the untouched originals and sidecar before semantic
            # checks. A failure must not erase the actual review evidence.
            with target.open("xb") as stream:
                stream.write(raw)
            for path, _, frame in sequence:
                frame.update(observations=str(target.relative_to(output)), observations_source=str(sidecar),
                             observations_sha256=hashlib.sha256(raw).hexdigest(), cargo_phase=path.stem)
            try:
                cargo_capture_validation.verify_sequence(json.loads(raw), [path.name for path, _, _ in sequence], width, height)
            except ValueError as error:
                raise CargoCaptureEvidenceError(str(error), frames) from error
    if codex_sequences:
        if len(codex_sequences) != 1:
            raise ValueError("Codex capture requires one nine-frame sequence, not multiple runs")
        for folder, sequence in codex_sequences.items():
            sidecar = (folder / "capture.json").resolve()
            if sidecar.parent != folder:
                raise ValueError("Codex source metadata escapes its original frame folder")
            if sidecar.stat().st_mtime_ns < max(start_ns, *(path.stat().st_mtime_ns for path, _, _ in sequence)):
                raise ValueError("stale Codex source capture metadata")
            metadata_bytes = sidecar.read_bytes()
            metadata = json.loads(metadata_bytes)
            codex_capture_validation.verify_sequence(metadata, [path.name for path, _, _ in sequence], width, height)
            metadata_target = sequence[0][1].parent / "capture.json"
            with metadata_target.open("xb") as stream:
                stream.write(metadata_bytes)
            for path, _, frame in sequence:
                frame.update(observations=str(metadata_target.relative_to(output)), observations_source=str(sidecar),
                             observations_sha256=hashlib.sha256(metadata_bytes).hexdigest(), codex_phase=path.stem)
    expected_nanite = [test.get("fullTestPath") for test in report.get("tests", [])
                       if test.get("fullTestPath", "").startswith("SoraCapture.NaniteDraw.")]
    if nanite_sequences and (len(expected_nanite) != len(nanite_sequences) or len(set(expected_nanite)) != len(expected_nanite)):
        raise ValueError("Nanite original sequences do not match the requested diagnostic tests")
    for folder, sequence in nanite_sequences.items():
        sidecar = (folder / "capture.json").resolve()
        if sidecar.parent != folder:
            raise ValueError("Nanite source metadata escapes its original frame folder")
        if sidecar.stat().st_mtime_ns < max(start_ns, *(path.stat().st_mtime_ns for path, _, _ in sequence)):
            raise ValueError("stale Nanite source capture metadata")
        raw = sidecar.read_bytes()
        target = sequence[0][1].parent / "capture.json"
        with target.open("xb") as stream:
            stream.write(raw)
        # Archive original metadata before the draw gate, retaining genuine
        # zero-coverage failure evidence alongside its untouched PNGs.
        metadata = json.loads(raw)
        if not isinstance(metadata, dict):
            raise ValueError("Nanite source metadata is not an object")
        actual_test = "SoraCapture.NaniteDraw.DojoSM6" if metadata.get("sm6_requested") is True else "SoraCapture.NaniteDraw.DojoSM5"
        if actual_test not in expected_nanite:
            raise ValueError("Nanite metadata does not match the requested SM6/SM5 test")
        expected_nanite.remove(actual_test)
        actual_model = "sm6" if metadata.get("sm6_requested") is True else "sm5"
        if any(device.get("renderMode", "").lower() != actual_model for device in report.get("devices", [])):
            raise ValueError("Nanite metadata differs from actual automation device shader model")
        asset_identities = nanite_capture_validation.asset_identities(metadata, project)
        source_commit = output / "source-commit.txt"
        placement = nanite_capture_validation.placement_coverage(metadata, project,
            source_commit.read_text().strip() if source_commit.is_file() else None)
        result = nanite_capture_validation.inspect(metadata,
            {path.name: destination.read_bytes() for path, destination, _ in sequence},
            width, height, bow_capture_validation.rgb8, placement)
        result["asset_files"] = asset_identities
        review = target.with_name("pixel-review.json")
        with review.open("x") as stream:
            stream.write(json.dumps(result, indent=2) + "\n")
        for path, _, frame in sequence:
            frame.update(observations=str(target.relative_to(output)), observations_source=str(sidecar),
                         observations_sha256=hashlib.sha256(raw).hexdigest(),
                         pixel_review=str(review.relative_to(output)),
                         pixel_review_sha256=hashlib.sha256(review.read_bytes()).hexdigest(), nanite_phase=path.stem)
        if result["errors"]:
            raise NaniteDrawEvidenceError("Nanite draw evidence: " + "; ".join(result["errors"]), frames)
    expected_probe = [test.get("fullTestPath") for test in report.get("tests", [])
                      if test.get("fullTestPath", "").startswith("SoraCapture.TimberProbe.")]
    for folder, sequence in probe_sequences.items():
        sidecar = (folder / "capture.json").resolve()
        if sidecar.parent != folder or sidecar.stat().st_mtime_ns < max(start_ns, *(p.stat().st_mtime_ns for p, _, _ in sequence)):
            raise NaniteDrawEvidenceError("stale/escaped timber probe metadata", frames)
        raw = sidecar.read_bytes()
        target = sequence[0][1].parent / "capture.json"
        with target.open("xb") as stream:
            stream.write(raw)
        # Keep every original and its metadata even when provenance or actual
        # visible-draw validation fails. Production Nanite rules stay separate.
        try:
            metadata = json.loads(raw)
            actual_model = "sm6" if metadata.get("sm6_requested") is True else "sm5"
            actual_test = "SoraCapture.TimberProbe." + actual_model.upper()
            if len(probe_sequences) != 1 or expected_probe != [actual_test]:
                raise ValueError("timber probe originals differ from requested tests")
            if not report.get("devices") or any(d.get("renderMode", "").lower() != actual_model for d in report["devices"]):
                raise ValueError("timber probe shader model differs from actual automation device")
            identities = timber_probe_capture_validation.identities(metadata, project, (output / "source-commit.txt").read_text().strip())
            result = timber_probe_capture_validation.inspect(metadata,
                {p.name: destination.read_bytes() for p, destination, _ in sequence}, width, height, bow_capture_validation.rgb8)
            result["provenance"] = identities
        except (ValueError, KeyError, TypeError, AttributeError, OSError, subprocess.CalledProcessError) as error:
            result = {"scope": timber_probe_capture_validation.SCOPE, "errors": [str(error)],
                      "nanite_draw_evidence": False, "release_qualified": False}
        review = target.with_name("pixel-review.json")
        with review.open("x") as stream:
            stream.write(json.dumps(result, indent=2) + "\n")
        for path, _, frame in sequence:
            frame.update(observations=str(target.relative_to(output)), observations_source=str(sidecar),
                         observations_sha256=hashlib.sha256(raw).hexdigest(),
                         pixel_review=str(review.relative_to(output)), pixel_review_sha256=hashlib.sha256(review.read_bytes()).hexdigest(),
                         timber_probe_phase=path.stem)
        if result["errors"]:
            raise NaniteDrawEvidenceError("Timber probe evidence: " + "; ".join(result["errors"]), frames)
    for sequence in bow_sequences.values():
        bow_capture_validation.verify_sequence(sequence)
    if campaign_errors:
        raise CampaignCaptureEvidenceError("; ".join(campaign_errors), frames)
    if frontend_errors:
        raise FrontEndCaptureEvidenceError("; ".join(frontend_errors), frames)
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
            if isinstance(error, (NaniteDrawEvidenceError, CargoCaptureEvidenceError, CampaignCaptureEvidenceError,
                                  WithdrawalCaptureEvidenceError, FrontEndCaptureEvidenceError)):
                frames = error.frames
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
