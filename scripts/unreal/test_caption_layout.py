"""Font-measured caption packing contracts; no Unreal or image rendering.

Pillow/FreeType reads the shipped Noto font at both adjacent integer raster
sizes for the HUD's 28pt/96-DPI font. These are independent capacity inputs,
not screenshots or claims that Canvas matches Pillow pixel for pixel. The
runtime capture asserts the actual Canvas glyph/panel bounds separately.
"""
import os
import platform
import shutil
import subprocess
import tempfile
import unittest
from PIL import ImageFont
from pathlib import Path
import json
import re
import itertools
R = Path(__file__).resolve().parents[2]
FONT = R / 'Content/SourceArt/Fonts/NotoSansCJKjp-Regular.otf'
if FONT.stat().st_size < 1000:
    raise RuntimeError('Materialize the shipped HUD font: git lfs pull --include=Content/SourceArt/Fonts/NotoSansCJKjp-Regular.otf')
font = ImageFont.truetype(str(FONT), 38)
po = (R / 'Content/Localization/Game/en/Game.po').read_text()
strings = {k: (j, e) for k, j, e in re.findall('msgctxt "([^"\\n]+)"\\nmsgid "([^"\\n]+)"\\nmsgstr "([^"\\n]+)"', po)}

def width(t, z):
    return font.getlength(t) * z

def ink(t, z):
    b = font.getbbox(t)
    return (b[3] - b[1]) * z

def wrap(t, z, w):
    out = []
    line = ''
    for c in t:
        if line and width(line + c, z) > w:
            at = line.rfind(' ')
            if at > 0:
                out.append(line[:at + 1])
                line = line[at + 1:]
            else:
                out.append(line)
                line = ''
        line += c
    if line:
        out.append(line)
    return out

def caption(key, w, s, sz, en, count=2):
    j, e = strings['SoraArena.Captions,' + key]
    behind_ja, behind_en = strings['SoraArena.Captions,Behind']
    j = j + ' ' + behind_ja if en else '［' + j + f' ×{count}］ ' + behind_ja
    e = e + f' ×{count} ' + behind_en
    jz = max(0.65 * s, 0.65) * sz
    ez = max(0.6 * s, 0.6) * sz
    i = w - 28 * s
    jl = max(max(24 * s, 22) * sz, max((ink(x, jz) + 3 for x in wrap(j, jz, i))))
    el = max(max(20 * s, 20) * sz, max((ink(x, ez) + 3 for x in wrap(e, ez, i))))
    return 4 * s + (max(jl, el) if en and width(j, jz) + 10 * s + width(e, ez) <= i else len(wrap(j, jz, i)) * jl + (len(wrap(e, ez, i)) * el if en else 0))

def row(j, e, w, s, en, target=False, frac=False):
    jz = max(0.44 * s, 0.6)
    ez = max(0.34 * s, 0.55)
    jlines = wrap(j, jz, w)
    elines = wrap(e, ez, w)
    jl = max(22, max((ink(x, jz) + 3 for x in jlines)))
    el = max(20, max((ink(x, ez) + 3 for x in elines)))
    inline = en and len(jlines) == len(elines) == 1 and (width(j, jz) + 10 * s + width(e, ez) <= w)
    return (max(jl, el) if inline else len(jlines) * jl + (len(elines) * el if en else 0)) + (4 if frac and (not target) else 0)

def model(W, H, sz, en, keys, count=2, dialogue_active=True, net_prompt=False):
    s = min(W / 1600, H / 1000)
    gap = 6 * s
    w = min(max(435 * s, 540), W - 902 * s)
    x = W - 20 * s - w
    inner = w - 20 * s
    # Reserve the real katana lines, including wrapped English ammo text.
    # Weapon text uses the font global height; the compact tracker uses ink.
    wh = 10 * s + 4 * s + 8 * s + 3 * s
    weapon = json.loads((R / 'Content/Data/catalog.json').read_text())['weapons'][0]
    for t, z in [(weapon['name'], max(0.72 * s, 0.6)), (weapon['name_en'], max(0.36 * s, 0.5)), (strings['SoraArena.HUD,Ammo.Melee'][0], max(0.54 * s, 0.55)), (strings['SoraArena.HUD,Ammo.Melee'][1], max(0.54 * 0.8 * s, 0.5))]:
        if t.isascii() and (not en):
            continue
        wh += len(wrap(t, z, 315 * s)) * (font.font.height * z + 4)
    bottom = min(H - 130 * s, H - 30 * s - wh - gap)
    jgrowth = max(24 * s, 22) * (sz - 1)
    egrowth = max(20 * s, 20) * (sz - 1)
    dialogue = max(170 * s, 170 * s + 3 * jgrowth + (2 * egrowth if en else 0))
    limit = bottom - (dialogue if dialogue_active else 0) - gap
    chapter = json.loads((R / 'Content/Data/campaign/chapter_04.json').read_text())
    task = chapter['beats'][11]['task']
    required = sum(not beat.get('optional', False) for beat in chapter['beats'])
    number = sum(not beat.get('optional', False) for beat in chapter['beats'][:12])
    seconds = (task['duration_ms'] + 999) // 1000
    if net_prompt:
        prompt=next(p for p in chapter['ui_prompts'] if p['id']=='ui.ch04.b12.net')
        prompt_height=10*s
        texts=[(prompt['ja'].replace('{Interact}','［E］'),max(.65*s,.65),max(24*s,22))]
        if en: texts.append((prompt['en'].replace('{Interact}','[E]'),max(.60*s,.60),max(20*s,20)))
        for text,scale,leading in texts:
            prompt_height+=len(wrap(text,scale,W-70*s))*max(leading,font.font.height*scale+4)
        limit-=prompt_height+gap
    at = 87 * s + 3 * s
    at += row(f'第{number}場 / {required}', f'Beat {number} of {required}', inner, s, en) + max(2 * s, 1.5)
    at += row(f'持ちこたえる  残り {seconds} 秒', f'Hold out: {seconds} s left', inner, s, en, frac=True) + max(2 * s, 1.5)
    data = json.loads((R / 'Content/Data/campaign/campaign.json').read_text())
    labels = {t['id']: t for t in data['targets']}
    targets = [labels[t['id']] for t in task['targets']]
    assert len(targets) == 8
    for a, b in zip(targets[::2], targets[1::2]):
        at += max((row(t['ja'], t['en'], (inner - gap) / 2, s, en, target=True, frac=True) for t in (a, b))) + max(2 * s, 1.5)
    nexty = at - max(2 * s, 1.5) + 3 * s + gap
    objbottom = max((212 if en else 177) * s, 137 * s + font.font.height * 0.52 * s + 4 * s, 164 * s + max(20 * s, 20) + font.font.height * max(0.6 * s, 0.6) + 4 * s if en else 0)
    regions = [(20 * s, objbottom + gap, x - gap - 20 * s, limit - objbottom - gap), (x, nexty, w, limit - nexty), (20 * s, max(objbottom + gap, nexty), W - 40 * s, limit - max(objbottom + gap, nexty))]
    # Space below the full-width story panels, left of the weapon stack,
    # and above health. It remains available even with a net-cut prompt.
    regions.append((20*s,bottom+gap,W-390*s-gap-20*s,H-110*s-gap-(bottom+gap)))
    regions.append((365*s+gap,bottom+gap,W-390*s-gap-(365*s+gap),H-30*s-(bottom+gap)))
    regions=[region for region in regions if region[3]>0]
    heights = [[caption(k, reg[2], s, sz, en, count) for reg in regions] for k in keys]
    # The packer receives these measured obstacles; assertions below only
    # require containment, separation and complete row retention, not a
    # copied list of expected positions.
    return (regions, heights, gap, dict(s=s, limit=limit, trackerbottom=nexty, weapon=wh, objbottom=objbottom))

class CaptionLayoutTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='sora-caption-layout-')
        cls.binary = Path(cls.temp.name) / 'caption-layout'
        env = os.environ.copy()
        compiler = shutil.which('clang++') or shutil.which('c++')
        flags = []
        if platform.system() == 'Darwin':
            pins = json.loads((R / 'scripts/toolchain/versions.json').read_text())
            pinned=Path(pins['default_macos_xcode']).expanduser()
            # This compiles the pure host helper, not UE. Use the local pin
            # when installed; hosted CI can use its own selected SDK.
            if env.get('SORA_DEVELOPER_DIR'):
                env['DEVELOPER_DIR']=env['SORA_DEVELOPER_DIR']
            elif pinned.is_dir():
                env['DEVELOPER_DIR']=str(pinned)
            compiler = subprocess.check_output(['xcrun', '--find', 'clang++'], env=env, text=True).strip()
            flags = ['-isysroot', subprocess.check_output(['xcrun', '--sdk', 'macosx', '--show-sdk-path'], env=env, text=True).strip()]
        if not compiler:
            raise RuntimeError('A host C++ compiler is required')
        subprocess.run([compiler, '-std=c++20', '-UNDEBUG', '-O2', '-fsanitize=undefined', '-fsanitize-trap=undefined', '-Wall', '-Werror', *flags, '-I', str(R / 'Source/SoraArena/Public'), str(R / 'scripts/unreal/caption_layout_driver.cpp'), '-o', str(cls.binary)], env=env, check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def arrange(self, regions, heights, gap):
        request = f'{len(heights)} {len(regions)} {gap}\n' + '\n'.join((' '.join(map(str, row)) for row in [*regions, *heights])) + '\n'
        response = subprocess.check_output([str(self.binary)], input=request, text=True).splitlines()
        if response[0] == '0':
            return None
        return [tuple(map(float, line.split())) for line in response[1:]]

    def assert_clear(self, regions, heights, gap, plan):
        self.assertIsNotNone(plan, (regions, heights, gap))
        self.assertEqual(len(plan), len(heights))
        for i, (region, x, y, w, h) in enumerate(plan):
            rx, ry, rw, rh = regions[int(region)]
            self.assertGreaterEqual(x + 0.02, rx)
            self.assertGreaterEqual(y + 0.02, ry)
            self.assertLessEqual(x + w, rx + rw + 0.02)
            self.assertLessEqual(y + h, ry + rh + 0.02)
            self.assertAlmostEqual(h, heights[i][int(region)], delta=0.02)
            for _, ox, oy, ow, oh in plan[:i]:
                self.assertTrue(x + w + gap <= ox + 0.02 or ox + ow + gap <= x + 0.02 or y + h + gap <= oy + 0.02 or (oy + oh + gap <= y + 0.02))

    def test_eight_target_arrival_all_sizes_languages_resolutions(self):
        global font
        cases = 0
        for pixels in (37, 38):
            font = ImageFont.truetype(str(FONT), pixels)
            for W, H in ((1280, 720), (1920, 1080)):
                for size in (1, 1.25, 1.5):
                    for english in (False, True):
                        for count in (2, 99):
                            for n in range(1, 5):
                                keys = ('Gunfire', 'BladeDrawnBack', 'BeamHum', 'Explosion')[:n]
                                with self.subTest(pixels=pixels, resolution=(W, H), size=size, english=english, count=count, captions=n):
                                    regions, heights, gap, _ = model(W, H, size, english, keys, count)
                                    self.assert_clear(regions, heights, gap, self.arrange(regions, heights, gap))
                                cases += 1
        print(f'{cases} font-measured eight-target/arrival caption layouts checked')

    def test_every_four_common_combat_captions_with_arrival_and_eight_targets(self):
        keys = ('Gunfire', 'BladeDrawnBack', 'BeamHum', 'Explosion', 'BladeBlocked', 'BladesClash')
        for selected in itertools.combinations(keys, 4):
            with self.subTest(captions=selected):
                regions, heights, gap, _ = model(1280, 720, 1.5, True, selected, 99)
                self.assert_clear(regions, heights, gap, self.arrange(regions, heights, gap))

    def test_common_combat_captions_also_clear_the_authored_net_prompt(self):
        keys = ('Gunfire', 'BladeDrawnBack', 'BeamHum', 'Explosion', 'BladeBlocked', 'BladesClash')
        for selected in itertools.combinations(keys, 4):
            with self.subTest(captions=selected):
                regions, heights, gap, info = model(1280, 720, 1.5, True, selected, 99, net_prompt=True)
                self.assertLessEqual(info['trackerbottom'], info['limit'])
                self.assert_clear(regions, heights, gap, self.arrange(regions, heights, gap))

    def test_original_single_stack_reproduces_overlap(self):
        regions, heights, gap, info = model(1280, 720, 1.5, True, ('Gunfire', 'BladeDrawnBack', 'BeamHum', 'Explosion'))
        self.assertGreater(sum((h[1] for h in heights)) + 3 * gap + info['trackerbottom'], info['limit'])
        self.assert_clear(regions, heights, gap, self.arrange(regions, heights, gap))

    def test_long_authored_caption_wrap_keeps_every_character(self):
        for key, (ja, en) in strings.items():
            if not key.startswith('SoraArena.Captions,'):
                continue
            for text, z in ((ja, 0.975), (en, 0.9)):
                lines = wrap(text, z, 240)
                self.assertEqual(''.join(lines), text)
                for line in lines:
                    self.assertLessEqual(width(line, z), 240 + 0.01)

    def test_backtracks_when_first_caption_uses_needed_column(self):
        regions = [(0, 0, 200, 80), (210, 0, 200, 40)]
        heights = [[40, 40], [70, 70]]
        plan = self.arrange(regions, heights, 4)
        self.assert_clear(regions, heights, 4, plan)
        self.assertEqual(plan[0][0], 1)

    def test_overlapping_wide_region_respects_prior_panels(self):
        regions = [(0, 0, 200, 50), (210, 0, 200, 50), (0, 0, 410, 110)]
        heights = [[40, 40, 40], [60, 60, 60]]
        self.assert_clear(regions, heights, 4, self.arrange(regions, heights, 4))

    def test_empty_and_impossible_do_not_drop_rows(self):
        self.assertEqual(self.arrange([], [], 4), [])
        self.assertIsNone(self.arrange([(0, 0, 200, 40)], [[41]], 4))
        self.assertIsNone(self.arrange([(0, 0, 200, 40)], [[20], [20]], 4))

    def test_plan_is_stable_for_unchanged_live_rows(self):
        regions, heights, gap, _ = model(1280, 720, 1.5, True, ('Gunfire', 'BladeDrawnBack', 'BeamHum', 'Explosion'))
        self.assertEqual(self.arrange(regions, heights, gap), self.arrange(regions, heights, gap))
if __name__ == '__main__':
    unittest.main()
