"""Build/check the project's native Japanese Unreal localization resources.

The compact LocRes format is defined by FTextLocalizationResourceVersion and
FTextLocalizationResource in Unreal's Core module. Version 1 avoids embedding
engine-generated content or local paths. The Unreal automation test loads the
resource with the engine's own parser. The entry is the Japanese HUD title, not a translation
of story subtitles. Add future FText entries through Unreal's localization
tools; the authored bilingual dialogue remains in Content/Data/catalog.json.
"""

from __future__ import annotations

import argparse
import re
import struct
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "Content/Localization/Game"
META = TARGET / "Game.locmeta"
RESOURCE = TARGET / "ja/Game.locres"
NAMESPACE = "SoraArena"
KEY = "MenuTitle"
TITLE = "猫柳生"

# FGuid values from TextLocalizationResource.cpp, serialized as four LE u32s.
LOCMETA_MAGIC = (0xA14CEE4F, 0x83554868, 0xBD464C6C, 0x7C50DA70)
LOCRES_MAGIC = (0x7574140E, 0xFC034A67, 0x9D90154A, 0x1B7F37C3)


def unreal_string(value: str) -> bytes:
    """FArchive FString layout: signed code-unit count plus NUL data."""
    if value.isascii():
        encoded = value.encode("ascii") + b"\0"
        return struct.pack("<i", len(encoded)) + encoded
    encoded = value.encode("utf-16-le") + b"\0\0"
    return struct.pack("<i", -(len(encoded) // 2)) + encoded


def source_hash(value: str) -> int:
    # FCrc::StrCrc32<TCHAR> processes each character as four LE bytes.
    # The game's Japanese title uses BMP code points on Mac and Windows.
    return zlib.crc32(b"".join(struct.pack("<I", ord(char)) for char in value))


def expected_meta() -> bytes:
    return b"".join(
        [
            struct.pack("<4I", *LOCMETA_MAGIC),
            b"\x02",  # AddedIsUGC
            unreal_string("ja"),
            unreal_string("ja/Game.locres"),
            struct.pack("<i", 1),
            unreal_string("ja"),
            struct.pack("<I", 0),  # FArchive serializes bool as a 32-bit UBOOL
        ]
    )


def expected_resource() -> bytes:
    # Compact version 1: header, string-table offset, one namespace/key,
    # source CRC, string-table index, then the localized-string array.
    entries = b"".join(
        [
            struct.pack("<I", 1),
            unreal_string(NAMESPACE),
            struct.pack("<I", 1),
            unreal_string(KEY),
            struct.pack("<I", source_hash(TITLE)),
            struct.pack("<i", 0),
        ]
    )
    string_table_offset = 16 + 1 + 8 + len(entries)
    return b"".join(
        [
            struct.pack("<4I", *LOCRES_MAGIC),
            b"\x01",  # Compact
            struct.pack("<q", string_table_offset),
            entries,
            struct.pack("<i", 1),
            unreal_string(TITLE),
        ]
    )


def validate_source() -> None:
    game_config = (ROOT / "Config/DefaultGame.ini").read_text()
    if not re.search(r"^Culture=ja$", game_config, re.MULTILINE):
        raise SystemExit("DefaultGame.ini must request native Japanese")
    if set(re.findall(r"^\+CulturesToStage=(\S+)$", game_config, re.MULTILINE)) != {"ja", "en"}:
        raise SystemExit("the package must stage Japanese and English cultures")
    # The HUD draws its panels from Source/SoraArena/Private/HUD.
    hud_source = "".join(path.read_text() for path in sorted((ROOT / "Source/SoraArena/Private/HUD").glob("*.cpp")))
    if 'NSLOCTEXT("SoraArena", "MenuTitle", "猫柳生")' not in hud_source:
        raise SystemExit("the HUD's native FText title no longer matches Game.locres")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify the committed resources without changing them")
    args = parser.parse_args()
    validate_source()
    for path, expected in ((META, expected_meta()), (RESOURCE, expected_resource())):
        if args.check:
            if not path.is_file() or path.read_bytes() != expected:
                raise SystemExit(f"native Japanese localization resource is missing or stale: {path}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(expected)
    print("Native Japanese Game localization valid: ja, one HUD title entry, English subtitles remain separate")


if __name__ == "__main__":
    main()
