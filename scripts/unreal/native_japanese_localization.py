"""Gather, check and compile the game's Japanese-native localization.

Every player-facing interface string is an NSLOCTEXT in Source/SoraArena whose
native text is Japanese. Its English subtitle is the translation of the same
namespace and key in Content/Localization/Game/en/Game.po, the gettext format
that Unreal's localization dashboard imports and exports. Running this script
gathers the NSLOCTEXT macros, merges them into Game.po and compiles
Game.locmeta, ja/Game.locres and en/Game.locres. A new key gets an empty
English entry, and a changed Japanese source marks its entry fuzzy. Either one
stops the build until a translator fills in the entry, or reviews it and
removes the fuzzy flag. --check verifies everything without writing.

The interface sources in LOCALIZED may hold Japanese only inside NSLOCTEXT.
An English translation must use the same {Name} arguments as its Japanese
and must contain no Japanese. Both follow the story bible's text style
(section 18): the Japanese ellipsis is 「……」, two three-dot characters, and
the English one the single character 「…」, never three periods.

The compact LocRes format is defined by FTextLocalizationResourceVersion and
FTextLocalizationResource in Unreal's Core module. Version 1 avoids embedding
engine-generated content or local paths. The Unreal automation tests load the
resources with the engine's own parser. Authored story dialogue stays
bilingual in the campaign data files.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import re
import struct
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "Source/SoraArena"
TARGET = ROOT / "Content/Localization/Game"
META = TARGET / "Game.locmeta"
RESOURCE = TARGET / "ja/Game.locres"
ENGLISH_RESOURCE = TARGET / "en/Game.locres"
TRANSLATIONS = TARGET / "en/Game.po"
# The title screen's native FText, which the automation test also reads.
TITLE = ("SoraArena", "MenuTitle", "猫柳生")
# Interface sources whose every Japanese string literal must be an NSLOCTEXT.
LOCALIZED = (
    "Private/UI/*.cpp", "Private/UI/*.h", "Private/HUD/SoraHUD.cpp", "Private/HUD/SoraHUDCaptions.cpp",
    "Private/HUD/SoraHUDFieldcraftPanel.cpp", "Private/Game/SoraCampaignDirectorWorld.cpp",
    "Private/HUD/SoraHUDPanels.h", "Private/Game/SoraGameMode.cpp", "Public/SoraFrontEnd.h", "Public/SoraText.h",
    "Public/SoraCaptions.h", "Public/SoraSettings.h", "Public/SoraPracticeLobby.h",
)
JAPANESE = re.compile(r"[\u3000-\u9fff\uff00-\uffef]")
ARGUMENT = re.compile(r"\{([A-Za-z0-9_]+)\}")
ELLIPSES = re.compile(r"…+")
LITERAL = r'"((?:[^"\\\n]|\\.)*)"'
NSLOCTEXT = re.compile(r"\bNSLOCTEXT\s*\(")
NSLOCTEXT_CALL = re.compile(rf"NSLOCTEXT\s*\(\s*{LITERAL}\s*,\s*{LITERAL}\s*,\s*{LITERAL}\s*\)")
PO_HEADER = (
    "# English subtitles for SORA Arena: Nyaagyu Rebellion. The native text is Japanese.\n"
    "# scripts/unreal/native_japanese_localization.py keeps this file; translate msgstr only.\n"
    'msgid ""\n'
    'msgstr ""\n'
    '"Project-Id-Version: Game\\n"\n'
    '"Language: en\\n"\n'
    '"MIME-Version: 1.0\\n"\n'
    '"Content-Type: text/plain; charset=UTF-8\\n"\n'
    '"Content-Transfer-Encoding: 8bit\\n"\n'
    '"Plural-Forms: nplurals=2; plural=(n != 1);\\n"\n'
)

# FGuid values from TextLocalizationResource.cpp, serialized as four LE u32s.
LOCMETA_MAGIC = (0xA14CEE4F, 0x83554868, 0xBD464C6C, 0x7C50DA70)
LOCRES_MAGIC = (0x7574140E, 0xFC034A67, 0x9D90154A, 0x1B7F37C3)


@dataclass
class Entry:
    source: str
    english: str = ""
    fuzzy: bool = False
    # The Japanese the English was translated from, while it is fuzzy.
    previous: str | None = None
    files: list[str] = field(default_factory=list)


def unreal_string(value: str) -> bytes:
    """FArchive FString layout: signed code-unit count plus NUL data."""
    if value.isascii():
        encoded = value.encode("ascii") + b"\0"
        return struct.pack("<i", len(encoded)) + encoded
    encoded = value.encode("utf-16-le") + b"\0\0"
    return struct.pack("<i", -(len(encoded) // 2)) + encoded


def source_hash(value: str) -> int:
    # FCrc::StrCrc32<TCHAR> feeds each TCHAR as four LE bytes; TCHAR is a
    # UTF-16 code unit on Mac and Windows.
    units = value.encode("utf-16-le")
    return zlib.crc32(b"".join(struct.pack("<I", int.from_bytes(units[i:i + 2], "little")) for i in range(0, len(units), 2)))


def line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def blank_comments(text: str) -> tuple[str, list[tuple[int, int]]]:
    """Return text with comments blanked (offsets kept) and its string literals' spans."""
    code, literals = [], []
    index, size = 0, len(text)
    while index < size:
        if text.startswith("//", index) or text.startswith("/*", index):
            end = text.find("\n", index) if text[index + 1] == "/" else text.find("*/", index + 2)
            end = size if end < 0 else end + (2 if text[index + 1] == "*" else 0)
            code.append(re.sub(r"[^\n]", " ", text[index:end]))
        elif text[index] in "\"'":
            end = index + 1
            while end < size and text[end] not in (text[index], "\n"):
                end += 2 if text[end] == "\\" else 1
            end = min(end + 1, size)
            code.append(text[index:end])
            if text[index] == '"':
                literals.append((index, end))
        else:
            end = index + 1
            code.append(text[index])
        index = end
    return "".join(code), literals


def unescape(value: str, where: str) -> str:
    def replace(match: re.Match) -> str:
        escape = match.group(1)
        if escape not in {"n", "t", '"', "\\", "'"}:
            raise SystemExit(f"{where}: NSLOCTEXT text may use only \\n, \\t, \\\", \\' and \\\\ escapes")
        return {"n": "\n", "t": "\t"}.get(escape, escape)
    return re.sub(r"\\(.)", replace, value)


def scan(name: str, text: str) -> tuple[list[tuple[str, str, str, int]], list[int]]:
    """Return a source's NSLOCTEXT calls (namespace, key, text, line) and the
    lines of Japanese string literals outside them."""
    code, literals = blank_comments(text)
    calls, spans = [], []
    for start in NSLOCTEXT.finditer(code):
        match = NSLOCTEXT_CALL.match(code, start.start())
        where = f"{name}:{line_of(text, start.start())}"
        if not match:
            raise SystemExit(f"{where}: NSLOCTEXT takes three plain string literals")
        namespace, key, native = match.group(1), match.group(2), unescape(match.group(3), where)
        if not re.fullmatch(r"[A-Za-z0-9_.]+", namespace) or not re.fullmatch(r"[A-Za-z0-9_.]+", key) or not native:
            raise SystemExit(f"{where}: NSLOCTEXT needs a dotted namespace and key and a native text")
        calls.append((namespace, key, native, line_of(text, start.start())))
        spans.append((match.start(), match.end()))
    stray = [line_of(text, start) for start, end in literals
             if JAPANESE.search(text[start:end]) and not any(low <= start and end <= high for low, high in spans)]
    return calls, stray


def module_sources() -> list[Path]:
    return sorted(path for pattern in ("**/*.cpp", "**/*.h") for path in SOURCE.glob(pattern))


def localized_sources() -> list[Path]:
    return sorted({path for pattern in LOCALIZED for path in SOURCE.glob(pattern)})


def gather() -> dict[tuple[str, str], Entry]:
    """Every NSLOCTEXT in the module; one key may not carry two native texts."""
    gathered: dict[tuple[str, str], Entry] = {}
    for path in module_sources():
        relative = path.relative_to(ROOT).as_posix()
        for namespace, key, native, line in scan(relative, path.read_text())[0]:
            entry = gathered.setdefault((namespace, key), Entry(native))
            if entry.source != native:
                raise SystemExit(f"{relative}:{line}: {namespace},{key} is also \"{entry.source}\" elsewhere")
            if relative not in entry.files:
                entry.files.append(relative)
    return gathered


def po_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t") + '"'


def po_unquote(token: str) -> str:
    if len(token) < 2 or token[0] != '"' or token[-1] != '"':
        raise SystemExit(f"{TRANSLATIONS}: malformed string {token}")
    return re.sub(r"\\(.)", lambda match: {"n": "\n", "t": "\t"}.get(match.group(1), match.group(1)), token[1:-1])


def parse_po(text: str) -> dict[tuple[str, str], Entry]:
    """The msgctxt "Namespace,Key" entries of a PO file, with fuzzy flags and previous msgids."""
    entries: dict[tuple[str, str], Entry] = {}
    for block in re.split(r"\n\s*\n", text.strip()):
        fields: dict[str, str] = {}
        fuzzy, current = False, None
        for line in block.splitlines():
            line = line.strip()
            if line.startswith("#,"):
                fuzzy |= "fuzzy" in line
            elif line.startswith("#| msgid "):
                fields["previous"] = po_unquote(line[len("#| msgid "):])
            elif line.startswith("#"):
                continue
            elif line.startswith('"') and current:
                fields[current] += po_unquote(line)
            else:
                name, _, value = line.partition(" ")
                if name not in ("msgctxt", "msgid", "msgstr"):
                    raise SystemExit(f"{TRANSLATIONS}: unexpected line {line}")
                current, fields[name] = name, po_unquote(value)
        if "msgctxt" not in fields:
            if fields.get("msgid"):
                raise SystemExit(f"{TRANSLATIONS}: every entry needs msgctxt \"Namespace,Key\"")
            continue
        namespace, comma, key = fields["msgctxt"].partition(",")
        if not comma or (namespace, key) in entries:
            raise SystemExit(f"{TRANSLATIONS}: bad or repeated msgctxt {fields['msgctxt']}")
        entries[(namespace, key)] = Entry(fields.get("msgid", ""), fields.get("msgstr", ""), fuzzy, fields.get("previous"))
    return entries


def merge(gathered: dict[tuple[str, str], Entry], existing: dict[tuple[str, str], Entry]) -> tuple[dict, list]:
    """Gathered keys with their English. A changed native text keeps its old
    English, marked fuzzy with the Japanese it was made from."""
    merged = {}
    for ident, entry in sorted(gathered.items()):
        old = existing.get(ident)
        result = Entry(entry.source, files=sorted(entry.files))
        if old:
            result.english = old.english
            if old.source == entry.source:
                result.fuzzy, result.previous = old.fuzzy, old.previous if old.fuzzy else None
            else:
                result.fuzzy, result.previous = True, old.previous if old.fuzzy and old.previous else old.source
        merged[ident] = result
    return merged, sorted(set(existing) - set(gathered))


def render_po(entries: dict[tuple[str, str], Entry]) -> str:
    blocks = [PO_HEADER]
    for (namespace, key), entry in entries.items():
        lines = [f"#. Key:\t{key}"] + [f"#: {path}" for path in entry.files]
        if entry.fuzzy:
            lines.append("#, fuzzy")
            if entry.previous is not None:
                lines.append(f"#| msgid {po_quote(entry.previous)}")
        lines += [f"msgctxt {po_quote(namespace + ',' + key)}", f"msgid {po_quote(entry.source)}", f"msgstr {po_quote(entry.english)}"]
        blocks.append("\n".join(lines) + "\n")
    return "\n".join(blocks)


def translation_problems(entries: dict[tuple[str, str], Entry]) -> list[str]:
    problems = []
    for (namespace, key), entry in entries.items():
        name = f"{namespace},{key}"
        if not entry.english:
            problems.append(f"{name} (\"{entry.source}\") has no English")
        elif entry.fuzzy:
            problems.append(f"{name} changed from \"{entry.previous}\" to \"{entry.source}\"; review its English and remove the fuzzy flag")
        elif JAPANESE.search(entry.english):
            problems.append(f"{name}: the English subtitle \"{entry.english}\" contains Japanese")
        elif sorted(ARGUMENT.findall(entry.source)) != sorted(ARGUMENT.findall(entry.english)):
            problems.append(f"{name}: \"{entry.english}\" must use the arguments of \"{entry.source}\"")
        if any(len(run) != 2 for run in ELLIPSES.findall(entry.source)):
            problems.append(f"{name}: the Japanese \"{entry.source}\" must write its ellipsis as 「……」")
        if "..." in entry.english or any(len(run) != 1 for run in ELLIPSES.findall(entry.english)):
            problems.append(f"{name}: the English \"{entry.english}\" must write its ellipsis as the single character 「…」")
    return problems


def translations() -> dict[tuple[str, str], Entry]:
    """The gathered keys with their English; stops on any missing, stale or obsolete entry."""
    existing = parse_po(TRANSLATIONS.read_text()) if TRANSLATIONS.is_file() else {}
    entries, obsolete = merge(gather(), existing)
    problems = translation_problems(entries) + [f"{namespace},{key} is no longer in the source" for namespace, key in obsolete]
    if problems:
        raise SystemExit(f"{TRANSLATIONS} is incomplete; run scripts/unreal/native_japanese_localization.py:\n  " + "\n  ".join(problems))
    return entries


def expected_meta() -> bytes:
    return b"".join(
        [
            struct.pack("<4I", *LOCMETA_MAGIC),
            b"\x02",  # AddedIsUGC
            unreal_string("ja"),
            unreal_string("ja/Game.locres"),
            struct.pack("<i", 2),
            unreal_string("ja"),
            unreal_string("en"),
            struct.pack("<I", 0),  # FArchive serializes bool as a 32-bit UBOOL
        ]
    )


def compile_resource(strings: dict[tuple[str, str], tuple[str, str]]) -> bytes:
    """Compact version 1: header, string-table offset, then per namespace its
    keys with source CRC and string-table index, then the shared strings."""
    table: list[str] = []
    index: dict[str, int] = {}
    namespaces: dict[str, list[tuple[str, str, str]]] = {}
    for (namespace, key), (source, localized) in sorted(strings.items()):
        namespaces.setdefault(namespace, []).append((key, source, localized))
    body = [struct.pack("<I", len(namespaces))]
    for namespace, keys in namespaces.items():
        body += [unreal_string(namespace), struct.pack("<I", len(keys))]
        for key, source, localized in keys:
            if localized not in index:
                index[localized] = len(table)
                table.append(localized)
            body += [unreal_string(key), struct.pack("<I", source_hash(source)), struct.pack("<i", index[localized])]
    entries = b"".join(body)
    string_table_offset = 16 + 1 + 8 + len(entries)
    return b"".join(
        [
            struct.pack("<4I", *LOCRES_MAGIC),
            b"\x01",  # Compact
            struct.pack("<q", string_table_offset),
            entries,
            struct.pack("<i", len(table)),
            b"".join(unreal_string(value) for value in table),
        ]
    )


def expected_resource() -> bytes:
    """ja/Game.locres: every native text as its own display string."""
    return compile_resource({ident: (entry.source, entry.source) for ident, entry in gather().items()})


def expected_english_resource(entries: dict[tuple[str, str], Entry] | None = None) -> bytes:
    """en/Game.locres: the English, keyed to the Japanese it translates."""
    entries = translations() if entries is None else entries
    return compile_resource({ident: (entry.source, entry.english) for ident, entry in entries.items()})


def expected_resources() -> dict[Path, bytes]:
    return {META: expected_meta(), RESOURCE: expected_resource(), ENGLISH_RESOURCE: expected_english_resource()}


def validate_source() -> None:
    game_config = (ROOT / "Config/DefaultGame.ini").read_text()
    if not re.search(r"^Culture=ja$", game_config, re.MULTILINE):
        raise SystemExit("DefaultGame.ini must request native Japanese")
    if set(re.findall(r"^\+CulturesToStage=(\S+)$", game_config, re.MULTILINE)) != {"ja", "en"}:
        raise SystemExit("the package must stage Japanese and English cultures")
    gathered = gather()
    namespace, key, title = TITLE
    if gathered.get((namespace, key), Entry("")).source != title:
        raise SystemExit("the title screen's native FText title no longer matches Game.locres")
    stray = []
    for path in localized_sources():
        relative = path.relative_to(ROOT).as_posix()
        stray += [f"{relative}:{line}" for line in scan(relative, path.read_text())[1]]
    if stray:
        raise SystemExit("Japanese interface text outside NSLOCTEXT:\n  " + "\n  ".join(stray))


def unlocalized_elsewhere() -> dict[str, int]:
    """Japanese literals outside NSLOCTEXT in the module's other non-test sources."""
    localized = set(localized_sources())
    counts = {}
    for path in module_sources():
        if path in localized or "Automation" in path.name:
            continue
        relative = path.relative_to(ROOT).as_posix()
        stray = scan(relative, path.read_text())[1]
        if stray:
            counts[relative] = len(stray)
    return counts


def expect_failure(action, fragment: str) -> None:
    try:
        action()
    except SystemExit as error:
        if fragment in str(error):
            return
        raise AssertionError(f"self-test expected '{fragment}', got: {error}")
    raise AssertionError(f"self-test expected a failure containing '{fragment}'")


def self_test() -> None:
    """The checks must reject known-bad input, so a broken checker cannot pass silently."""
    calls, stray = scan("t.cpp", 'A(NSLOCTEXT("SoraArena.T", "K", "日本語\\n")); // 「註」\nB(TEXT("生の日本語")); C(TEXT("ascii"));\n')
    assert calls == [("SoraArena.T", "K", "日本語\n", 1)] and stray == [2], (calls, stray)
    expect_failure(lambda: scan("t.cpp", 'NSLOCTEXT("SoraArena.T", "K", "上" "下")'), "three plain string literals")
    expect_failure(lambda: scan("t.cpp", 'NSLOCTEXT("SoraArena.T", "K", "\\x41")'), "escapes")
    for value in ('引用"と\\と\n改行\t', "plain"):
        assert po_unquote(po_quote(value)) == value
    ident = ("SoraArena.T", "K")
    merged, obsolete = merge({ident: Entry("新しい")}, {ident: Entry("古い", "Old"), ("SoraArena.T", "Gone"): Entry("消", "Gone")})
    assert merged[ident].fuzzy and merged[ident].previous == "古い" and merged[ident].english == "Old", merged
    assert obsolete == [("SoraArena.T", "Gone")]
    assert parse_po(render_po(merged))[ident] == Entry("新しい", "Old", True, "古い")
    assert any("review" in problem for problem in translation_problems(merged))
    assert any("arguments" in problem for problem in translation_problems({ident: Entry("第{Chapter}章", "Chapter {Number}")}))
    assert any("contains Japanese" in problem for problem in translation_problems({ident: Entry("戻る", "Back 戻る")}))
    assert any("no English" in problem for problem in translation_problems({ident: Entry("戻る")}))
    assert any("「……」" in problem for problem in translation_problems({ident: Entry("準備中…", "Preparing…")}))
    assert any("single character" in problem for problem in translation_problems({ident: Entry("準備中……", "Preparing...")}))
    assert not translation_problems({ident: Entry("準備中……", "Preparing…")})
    # Unreal's FCrc::StrCrc32 over UTF-16 units, as the title's committed hash was made.
    assert source_hash("猫柳生") == zlib.crc32(b"".join(struct.pack("<I", ord(char)) for char in "猫柳生"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="verify the committed translations and resources without changing them")
    args = parser.parse_args()
    self_test()
    validate_source()
    existing = parse_po(TRANSLATIONS.read_text()) if TRANSLATIONS.is_file() else {}
    entries, obsolete = merge(gather(), existing)
    po_text = render_po(entries)
    if args.check:
        if not TRANSLATIONS.is_file() or TRANSLATIONS.read_text() != po_text:
            raise SystemExit(f"{TRANSLATIONS} is stale; run scripts/unreal/native_japanese_localization.py")
        translations()
        for path, expected in expected_resources().items():
            if not path.is_file() or path.read_bytes() != expected:
                raise SystemExit(f"native Japanese localization resource is missing or stale: {path}")
    else:
        TRANSLATIONS.parent.mkdir(parents=True, exist_ok=True)
        TRANSLATIONS.write_text(po_text)
        for namespace, key in obsolete:
            print(f"Dropped {namespace},{key}: no longer in the source")
        problems = translation_problems(entries)
        if problems:
            raise SystemExit(f"Fill in {TRANSLATIONS}, then run again:\n  " + "\n  ".join(problems))
        for path, data in expected_resources().items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    elsewhere = unlocalized_elsewhere()
    print(f"Native Japanese Game localization valid: {len(entries)} keys in "
          f"{len({namespace for namespace, _ in entries})} namespaces, ja native with en subtitles; "
          f"{len(localized_sources())} interface sources hold Japanese only in NSLOCTEXT")
    if elsewhere:
        print("Not yet localized (Japanese literals outside NSLOCTEXT): " +
              ", ".join(f"{path} {count}" for path, count in sorted(elsewhere.items())))


if __name__ == "__main__":
    main()
