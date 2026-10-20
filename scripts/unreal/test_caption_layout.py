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

    def marker(self, label, view, obstacles, gap=4):
        data = ' '.join(map(str, (*label, *view, len(obstacles), gap))) + '\n'
        data += '\n'.join(' '.join(map(str, o)) for o in obstacles) + '\n'
        values = subprocess.check_output([str(self.binary), 'marker'], input=data, text=True).split()
        return bool(int(values[0])), tuple(map(float, values[1:]))

    def test_projected_marker_keeps_text_clear_of_the_work_prompt(self):
        # Observed 720p regression: cyan site marker at x586/y359 crosses
        # the gold working cue. Use real Noto dimensions, then vary viewport.
        for W, H in ((1280, 720), (1920, 1080)):
            scale = min(W / 1600, H / 1000)
            text = '生産の作業場 / 16m'
            label = (W * .5 - 75 * scale, H * .5, width(text, .42 * scale), font.font.height * .42 * scale)
            prompt = (W * .5 - 75 * scale, H * .5 - 5, width('E 作業する', .65), font.font.height * .65)
            view = (20 * scale, 87 * scale, W - 40 * scale, H - 207 * scale)
            fits, placed = self.marker(label, view, [prompt])
            self.assertTrue(fits)
            self.assertAlmostEqual(placed[2], label[2], places=3)
            self.assertAlmostEqual(placed[3], label[3], places=3)
            x, y, w, h = placed
            px, py, pw, ph = prompt
            self.assertTrue(x + w + 4 <= px + .01 or px + pw + 4 <= x + .01 or y + h + 4 <= py + .01 or py + ph + 4 <= y + .01)
            self.assertEqual(self.marker(label, view, [prompt]), (fits, placed))

    def test_relocated_site_and_examine_labels_do_not_overlap_each_other(self):
        obstacles = [(466, 317, 242, 108), (14, 434, 1252, 173), (726, 62, 540, 328)]
        view = (14, 62, 1252, 571)
        for text, position, z in [('生産の作業場 / 16m', (586, 359), .42 * .72),
                                  ('E 調べる', (586, 403), .65 * .72),
                                  ('目標 / 16m', (596, 363), .42 * .72)]:
            label = (*position, width(text, z), font.font.height * z)
            fits, placed = self.marker(label, view, obstacles)
            self.assertTrue(fits)
            x, y, w, h = placed
            self.assertAlmostEqual(w, label[2], places=3)
            self.assertAlmostEqual(h, label[3], places=3)
            for ox, oy, ow, oh in obstacles:
                self.assertTrue(x + w + 4 <= ox + .01 or ox + ow + 4 <= x + .01 or y + h + 4 <= oy + .01 or oy + oh + 4 <= y + .01)
            obstacles.append(placed)

    def test_projected_markers_can_use_viewport_edges_without_dropping_text(self):
        fits, placed = self.marker((-15, 30, 80, 25), (0, 0, 200, 100), [])
        self.assertTrue(fits)
        self.assertGreaterEqual(placed[0], 0)
        self.assertEqual(placed[2:], (80, 25))
        fits, placed = self.marker((70, 40, 80, 25), (0, 0, 200, 100), [(50, 40, 150, 60)])
        self.assertTrue(fits)
        self.assertGreaterEqual(placed[0], 0)
        self.assertGreaterEqual(placed[1], 0)
        self.assertLessEqual(placed[0] + placed[2], 200)
        self.assertLessEqual(placed[1] + placed[3], 100)
        fits, placed = self.marker((0, 0, 80, 25), (0, 0, 200, 100), [(0, 0, 200, 100)])
        self.assertFalse(fits)
        self.assertEqual(placed[2:], (80, 25))

    def test_bilingual_bellows_uses_measured_compact_rows_and_notice_column(self):
        global font
        chapter = json.loads((R / 'Content/Data/campaign/chapter_05.json').read_text())
        prompt = next(p for p in chapter['ui_prompts'] if p['id'] == 'ui.ch05.tut.08')
        count = chapter['beats'][5]['task']['count']
        for pixels, (W, H), pad, en in itertools.product((37, 38), ((1280, 720), (1920, 1080)), (False, True), (False, True)):
            font = ImageFont.truetype(str(FONT), pixels)
            with self.subTest(pixels=pixels, resolution=(W, H), gamepad=pad, english=en):
                _, _, _, info = model(W, H, 1, en, ())
                scale = info['s']; gap = 6 * scale
                panel_width = min(max(435 * scale, 540), W - 902 * scale)
                inner = panel_width - 20 * scale
                key = 'Y' if pad else 'E'
                left, right = ('左スティック左', '左スティック右') if pad else ('A', 'D')
                el, er = ('left stick left', 'left stick right') if pad else ('A', 'D')
                lines = [('第6場 / 17', 'Beat 6 of 17'),
                    (f'踏む（左右一組） 1 / {count}', f'Tread pairs: 1 of {count}'),
                    ('火勢 II — 適正', 'Flame II: in rhythm'),
                    (f'{key} 長押し＋左 {left} → 右 {right}（毎回離す）', f'Hold {key} + left {el} then right {er}; release each tread'),
                    ('次は右足', 'Next: right tread')]
                prompt_height = 10 * scale
                for text, z in [(prompt['ja'], max(.65 * scale, .65)), *([(prompt['en'], max(.6 * scale, .6))] if en else [])]:
                    prompt_height += len(wrap(text, z, W - 70 * scale)) * (font.font.height * z + 4)
                limit = info['limit'] - prompt_height - gap
                tracker_bottom = 87 * scale + 6 * scale + 4 * max(2 * scale, 1.5)
                tracker_bottom += sum(row(ja, english, inner, scale, en, frac=i == 1) for i, (ja, english) in enumerate(lines))
                self.assertLessEqual(tracker_bottom, limit)
                if en:
                    prompts = [strings['SoraArena.HUD,Prompt.' + p] for p in ('Capture', 'Work', 'Search', 'PickUp')]
                    z = max(.65 * scale, .65)
                    jw = max(width(j.replace('{Interact}', key), z) for j, _ in prompts)
                    ew = max(width(e.replace('{Interact}', key), z * .8) for _, e in prompts)
                    inline = jw + 14 * scale + ew
                    prompt_x = W * .5 - 75 * scale
                    tracker_x = W - 20 * scale - panel_width
                    actual_width = max(jw, ew) if prompt_x + inline > tracker_x - gap else inline
                    self.assertLessEqual(prompt_x + actual_width, tracker_x - gap)

                # The longest pad instruction and newest title keep every
                # character; no expected line count or baked position.
                for ja, english in lines:
                    self.assertEqual(''.join(wrap(ja, max(.44 * scale, .6), inner)), ja)
                    self.assertEqual(''.join(wrap(english, max(.34 * scale, .55), inner)), english)
                notices = [('見つけた：伝書の断簡', 'Found: Scroll fragment'), ('通知を要約：ほか 2 件・詳細 3 件', 'Condensed: 2 more notices; 3 details')]
                right_heights = [[row(*text, inner, scale, en) + 6 * scale] for text in notices]
                right_region = (W - 20 * scale - panel_width, tracker_bottom + gap, panel_width, limit - tracker_bottom - gap)
                plan = self.arrange([right_region], right_heights, gap)
                if plan is None:
                    # The ring has a fixed 54px outer radius and 12px gap.
                    # This is the actual free column left of that whole group.
                    left_width = W * .5 - 75 * scale - 12 - 108 - gap - 20 * scale
                    top = info['objbottom'] + gap
                    regions = [(20 * scale, top, left_width, limit - top)]
                    heights = [[row(*text, left_width - 20 * scale, scale, en) + 6 * scale] for text in notices]
                    self.assert_clear(regions, heights, gap, self.arrange(regions, heights, gap))
                else:
                    self.assert_clear([right_region], right_heights, gap, plan)

    def test_bokken_arrival_retains_all_manufacturing_rows_at_readable_sizes(self):
        global font
        chapter = json.loads((R / 'Content/Data/campaign/chapter_01.json').read_text())
        campaign = json.loads((R / 'Content/Data/campaign/campaign.json').read_text())
        task = chapter['beats'][8]['task']
        prompt = next(p for p in chapter['ui_prompts'] if p['id'] == 'ch01.b09.prompt.02')
        step = next(s for s in campaign['step_kinds'] if s['id'] == task['steps'][0]['kind'])
        n = len(task['steps'])
        required = sum(not beat.get('optional', False) for beat in chapter['beats'])
        number = sum(not beat.get('optional', False) for beat in chapter['beats'][:9])
        rows = [(f'第{number}場 / {required}', f'Beat {number} of {required}'),
                (f'工程 1 / {n}', f'Step 1 of {n}'),
                (f'▶ {step["ja"]} 0 / {task["steps"][0]["count"]}', f'Now: {step["en"]}, 0 of {task["steps"][0]["count"]}'),
                (f'工程一覧を要約：完了 0・後続 {n-1}', f'Recipe summary: 0 completed, {n-1} later steps')]
        for pixels, (W, H), en in itertools.product((37, 38), ((1280, 720), (1920, 1080)), (False, True)):
            font = ImageFont.truetype(str(FONT), pixels)
            scale = min(W / 1600, H / 1000)
            with self.subTest(pixels=pixels, resolution=(W, H), english=en):
                weapon_height = (10 + 4 + 8 + 3) * scale
                ja, english = strings['SoraArena.Arms,Bokken']
                texts = [(ja, max(.72 * scale, .6)), *([(english, max(.36 * scale, .5))] if en else []),
                         (strings['SoraArena.HUD,Ammo.Melee'][0], max(.54 * scale, .55)),
                         *([(strings['SoraArena.HUD,Ammo.Melee'][1], max(.54 * .8 * scale, .5))] if en else [])]
                for text, z in texts:
                    weapon_height += len(wrap(text, z, 315 * scale)) * (font.font.height * z + 4)
                bottom = min(H - 130 * scale, H - 30 * scale - weapon_height - 6 * scale)
                limit = bottom - 170 * scale - 12 * scale - 10 * scale
                for text, z in [(prompt['ja'], max(.65 * scale, .65)), *([(prompt['en'], max(.6 * scale, .6))] if en else [])]:
                    limit -= len(wrap(text, z, W - 70 * scale)) * (font.font.height * z + 4)
                inner = min(max(435 * scale, 540), W - 902 * scale) - 20 * scale
                height = 6 * scale + (len(rows) - 1) * max(2 * scale, 1.5)
                height += sum(row(ja, english, inner, scale, en, frac=i == 1) for i, (ja, english) in enumerate(rows))
                self.assertLessEqual(87 * scale + height, limit)
                for ja, english in rows:
                    self.assertEqual(''.join(wrap(ja, max(.44 * scale, .6), inner)), ja)
                    self.assertEqual(''.join(wrap(english, max(.34 * scale, .55), inner)), english)

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
