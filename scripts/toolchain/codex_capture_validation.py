"""Bind the prepared Codex UI capture's eight original frames to its observations.

This validates capture identity/completeness and the observed input/layout gates;
original PNG review is still required. It does not claim earned unlocks or art
acceptance and never edits or re-encodes an image.
"""
import math
import re

PHASES = ("empty", "index-first", "index-last", "reader-standard", "reader-xl-top",
          "reader-xl-end", "reader-ja-only", "toshiya")
SCHEMA = "sora-arena.codex-capture.v1"
SCOPE = "prepared Codex discovery ledger; not playthrough or art acceptance"


def number(row, key, integer=False):
    value = row.get(key)
    try:
        finite = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        raise ValueError(f"invalid Codex observation {key}")
    if integer and (value < 0 or value > 2**53 - 1 or value != int(value)):
        raise ValueError(f"invalid Codex integer observation {key}")
    return value


def verify_sequence(metadata, filenames, width, height):
    if not isinstance(metadata, dict) or metadata.get("schema") != SCHEMA:
        raise ValueError("invalid Codex capture schema")
    if metadata.get("passed") is not True:
        raise ValueError("Codex source capture did not pass")
    if metadata.get("prepared_discoveries") is not True or metadata.get("scope") != SCOPE:
        raise ValueError("Codex capture must declare its prepared-ledger scope")
    if (metadata.get("viewport") != [width, height] or
            any(type(value) not in (int, float) for value in metadata.get("viewport", []))):
        raise ValueError("Codex metadata viewport mismatch")
    rows = metadata.get("frames")
    if not isinstance(rows, list) or len(rows) != len(PHASES) or number(metadata, "frame_count", True) != len(PHASES):
        raise ValueError("Codex capture requires exactly eight frame observations")
    expected_files = [phase + ".png" for phase in PHASES]
    if filenames != expected_files:
        raise ValueError("Codex acknowledgements must identify eight unique phases in order")
    previous_frame = -1
    longest = None
    for index, (phase, row) in enumerate(zip(PHASES, rows)):
        if not isinstance(row, dict) or row.get("name") != phase or row.get("file") != expected_files[index]:
            raise ValueError("Codex phase/filename mismatch or duplicate observation")
        if row.get("prepared_discoveries") is not True:
            raise ValueError("Codex frame lost its prepared-ledger scope")
        if row.get("screen_name") != ("reader" if index >= 3 else "index"):
            raise ValueError("Codex observed screen does not match its phase")
        if row.get("english") is not (index != 6) or number(row, "text_scale") != (1 if index < 4 else 1.5):
            raise ValueError("Codex language/text-size observations do not match the phase")
        if number(row, "entries", True) != (0 if index == 0 else 49):
            raise ValueError("Codex discovery count does not match the prepared ledger")
        if number(row, "focus", True) != (1 if index == 0 else 48 if index == 2 else 0):
            raise ValueError("Codex focus does not match its first/last/reader phase")
        request = number(row, "request_frame", True)
        processed = number(row, "screenshot_processed_frame", True)
        if request <= previous_frame or processed < request:
            raise ValueError("Codex request/processed frames are duplicated or out of order")
        previous_frame = processed
        if index < 3:
            continue
        entry = row.get("entry_id")
        if index == 7:
            if entry != "codex_toshiya" or number(row, "entry_key", True) != 48:
                raise ValueError("Codex final reader is not the Toshiya challenge")
        else:
            match = re.fullmatch(r"ch0([1-8])\.c0([1-6])", entry) if isinstance(entry, str) else None
            if not match or number(row, "entry_key", True) != (int(match[1]) - 1) * 6 + int(match[2]) - 1:
                raise ValueError("Codex reader does not identify its actual collectible")
            if longest is None:
                longest = entry
            if entry != longest:
                raise ValueError("Codex reader phases changed the selected collectible")
        offset, end = number(row, "scroll_offset"), number(row, "scroll_end")
        bottom, viewport = number(row, "content_bottom"), number(row, "viewport_height")
        if offset < 0 or end < 0 or offset > end + 1 or viewport <= 0:
            raise ValueError("invalid Codex arranged scroll bounds")
        if index == 5:
            if end <= 1 or abs(offset - end) > 1 or not 0 <= bottom <= viewport + 1:
                raise ValueError("Codex extra-large tail is not reached inside its clip")
        elif abs(offset) >= 1:
            raise ValueError("Codex top phase is not at the top of its reader")
    return {phase: row for phase, row in zip(PHASES, rows)}
