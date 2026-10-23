"""Check the actual bundled composite faces without an Unreal installation.

This checks character coverage, not bidirectional shaping or rendered layout;
SoraArena.UI.CreditsFontCoverage exercises font selection and shaping in UE.
"""
from hashlib import sha256
from pathlib import Path
import re

from fontTools.ttLib import TTFont


# Match the explicit Unicode blocks in SoraUI::CreateUIFont. Arabic must be
# supported by its selected subfont, not accidentally by the Japanese cmap.
ARABIC_BLOCKS = {
    "Arabic": (0x0600, 0x06FF),
    "ArabicSupplement": (0x0750, 0x077F),
    "ArabicExtendedA": (0x08A0, 0x08FF),
    "ArabicPresentationFormsA": (0xFB50, 0xFDFF),
    "ArabicPresentationFormsB": (0xFE70, 0xFEFF),
    "ArabicMathematicalAlphabeticSymbols": (0x1EE00, 0x1EEFF),
}
FONT_HASHES = {
    "NotoSansCJKjp-Regular.otf": "68a3fc98800b2a27b371f2fb79991daf3633bd89309d4ffaa6946fd587f375b5",
    "NotoNaskhArabicUI-Regular.ttf": "f3878be872cc1d4ad9bd63535db480e3c5752c6313842656208872275cb32226",
}


def missing_characters(text, default_cmap, arabic_cmap):
    absent = set()
    for char in set(text):
        codepoint = ord(char)
        if codepoint <= 127:
            continue
        arabic = any(low <= codepoint <= high for low, high in ARABIC_BLOCKS.values())
        if codepoint not in (arabic_cmap if arabic else default_cmap):
            absent.add(char)
    return sorted(absent)


def validate_font_coverage(root: Path, text: str):
    source = (root / "Source/SoraArena/Private/UI/SoraUIFont.cpp").read_text()
    actual_blocks = set(re.findall(r"EUnicodeBlockRange::(\w+)", source))
    assert actual_blocks == set(ARABIC_BLOCKS), "Source font checker and runtime Arabic ranges differ"
    cmaps = []
    for name, digest in FONT_HASHES.items():
        path = root / "Content/SourceArt/Fonts" / name
        assert sha256(path.read_bytes()).hexdigest() == digest, f"Bundled font bytes changed: {name}"
        assert f'FPaths::ProjectContentDir() / TEXT("SourceArt/Fonts/{name}")' in source
        with TTFont(path) as face:
            cmaps.append(face.getBestCmap())
    absent = missing_characters(text, *cmaps)
    assert not absent, f"Bundled composite font lacks glyphs: {absent}"
