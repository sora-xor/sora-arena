"""Independent boss font capacity and the observed tracker-overlap regression.

Exercises the production free-region planner with shipped-font measurements,
not Unreal or rendered acceptance. Actual Canvas rows, meters and obstacles
are validated by the shared rendered-capture gate before screenshot requests.
"""
import itertools
import json
import subprocess
import unittest
from PIL import ImageFont
import test_caption_layout as c
import native_japanese_localization as localization

BOSSES=json.loads((c.R/'Content/Data/bosses.json').read_text())['bosses']
MUTO_ENTRIES=localization.parse_po(localization.TRANSLATIONS.read_text())
MUTO_HINTS=tuple((MUTO_ENTRIES[("SoraArena.HUD",key)].source,MUTO_ENTRIES[("SoraArena.HUD",key)].english)
                 for key in ("Boss.MutoDrawn","Boss.MutoSheathing","Boss.MutoReady"))
MAROBASHI=('転 ― 着く寸前に 左右＋［跳躍］で脇へ',
           'Marobashi: Left/Right + [Jump] just before it lands to reach the flank')


def overlaps(a,b):
    x,y,w,h=a; X,Y,W,H=b
    return x<X+W and x+w>X and y<Y+H and y+h>Y


def text_rows(boss,scale,english,attack=None,hint=None):
    """Authored title/tell/style plus conservative live-status fixtures."""
    jz=max(.65*scale,.65); ez=max(.60*scale,.60)
    rows=[(boss['name_ja'],boss['name_en'],jz,ez)]
    # Exercise full defense names/weak points/wards rather than only the short
    # single SEIZED status visible in the observed final image.
    ja=['無敵','崩れ：好機']; en=['INVULNERABLE','STAGGERED: strike now']
    for flag,j,e in [('shield','大盾：正面不可','SHIELD: front blocked'),
                     ('barrier','障壁：停止中','BARRIER: down'),
                     ('mantle','冷却外套：被害七割減','MANTLE: 70% less damage')]:
        if boss.get(flag): ja.append(j); en.append(e)
    for point in boss.get('weak_points',[]): ja.append(point['name_ja']); en.append(point['name_en'])
    for ward in boss.get('wards',[]): ja.append(ward['name_ja']+' ×2'); en.append(ward['name_en']+' x2')
    for item in boss['attacks']:
        if item.get('event_limit',0)>0: ja.append('差押え 1 / 3'); en.append('SEIZED 1 / 3')
    rows.append(('　'.join(ja),'  '.join(en),.34,.30))
    rows.append((attack['tell_ja'],attack['tell_en'],jz,ez) if attack else
                (boss['style_ja'],boss['style_en'],.42,.34))
    if attack: rows.append(('9.9 s','',.48,.48))
    if hint: rows.append((*hint,.36,.32))
    return [(ja,en if english else '',js,es) for ja,en,js,es in rows]


def measured_height(rows,width,telegraph=False,compact=False,glyph_margin=0):
    # Pair rows keep their entire strings. The font's glyph heights are an
    # independent bound, with the same 17px panel padding and 4px row clearance.
    inner=width-34
    gap=2 if compact else 4
    height=14+20+(4+gap if telegraph else 0)  # padding + health/phase/barrier + warning meter
    for ja,en,js,es in rows:
        jl=c.wrap(ja,js,inner); el=c.wrap(en,es,inner)
        assert ''.join(jl)==ja and ''.join(el)==en
        assert all(c.width(t,js)<=inner+.01 for t in jl)
        assert all(c.width(t,es)<=inner+.01 for t in el)
        if len(jl)==len(el)==1 and c.width(ja,js)+14+c.width(en,es)<=inner:
            height+=max(c.ink(ja,js),c.ink(en,es))+glyph_margin+gap
        else:
            height+=sum(c.ink(t,js)+glyph_margin+gap for t in jl)+sum(c.ink(t,es)+glyph_margin+gap for t in el)
    return height


class BossHUDLayoutTests(unittest.TestCase):
    setUpClass=classmethod(c.CaptionLayoutTests.setUpClass.__func__)
    tearDownClass=classmethod(c.CaptionLayoutTests.tearDownClass.__func__)

    def regions(self,w,h,blocks):
        s=min(w/1600,h/1000); view=(20*s,87*s,w-40*s,h-117*s)
        values=(*view,len(blocks),6*s,*itertools.chain.from_iterable(blocks))
        result=subprocess.check_output([str(self.binary),'aim-free'],input=' '.join(map(str,values))+'\n',text=True)
        return [tuple(map(float,line.split())) for line in result.splitlines()]

    def placements(self,rows,regions,blocks,telegraph=False):
        result=[]
        for x,y,width,height in regions:
            used=measured_height(rows,width,telegraph)
            if used<=height:
                placed=(x,y,width,used)
                self.assertTrue(all(not overlaps(placed,block) for block in blocks))
                result.append(placed)
        return result

    def test_actual_rejected_final_geometry_has_a_complete_clear_boss_region(self):
        # Actual 235e810 720p original: the tracker paints over the old boss.
        old=(400,165,480,142); tracker=(725.6,62.64,540,207)
        self.assertTrue(overlaps(old,tracker))
        # Retain the observed objective, zero notice, prompt, villager dialogue,
        # weapon and vitals envelopes. This is deliberately conservative after
        # the story-first allocator frees the old center boss rectangle.
        observed=[(14.4,62.64,612,98),(14.4,165,382,115),tracker,
                  (14.4,305,1251.2,82),(14.4,392,1251.2,122),
                  (999.2,518,262.8,180.4),(18,640.8,244.8,57.6)]
        boss=next(b for b in BOSSES if b['id']=='boss_hakari')
        for px,ratio,en in itertools.product((37,38),(1,1.5),(False,True)):
            c.font=ImageFont.truetype(str(c.FONT),px); w,h=1280*ratio,720*ratio; s=min(w/1600,h/1000)
            blocks=[tuple(v*ratio for v in block) for block in observed]
            regions=self.regions(w,h,blocks)
            rows=[(boss['name_ja'],boss['name_en'] if en else '',max(.65*s,.65),max(.60*s,.60)),
                  ('差押え 0 / 3','SEIZED 0 / 3' if en else '',.34,.30),
                  (boss['style_ja'],boss['style_en'] if en else '',.42,.34)]
            placements=self.placements(rows,regions,blocks)
            self.assertTrue(placements,(px,w,en,regions))
            if ratio==1: self.assertTrue(any(y>=514 for _,y,_,_ in placements))

    def test_all_authored_boss_tells_and_both_defense_hints_retain_text_in_free_space(self):
        scenarios=0
        for px,(w,h),en in itertools.product((37,38),((1280,720),(1920,1080)),(False,True)):
            c.font=ImageFont.truetype(str(c.FONT),px); s=min(w/1600,h/1000)
            # Busy top and bottom HUD, leaving the fight's center for complete
            # active tells. Lower-story/caption pressure has its own exact case.
            blocks=[(20*s,87*s,850*s,150*s),(w-20*s-max(435*s,540),87*s,max(435*s,540),230*s),
                    (25*s,h-110*s,340*s,80*s),(w-390*s,h-280*s,365*s,250*s),
                    (w*.5-10.75,h*.5-10.75,21.5,21.5)]
            regions=self.regions(w,h,blocks)
            for boss in BOSSES:
                for attack,hint in [(None,None)]+[(a,None) for a in boss['attacks']]+[(boss['attacks'][0],hint) for hint in (*MUTO_HINTS,MAROBASHI)]:
                    rows=text_rows(boss,s,en,attack,hint)
                    self.assertTrue(self.placements(rows,regions,blocks,attack is not None),(px,w,en,boss['id'],attack and attack['id'],hint))
                    scenarios+=1
        self.assertGreater(scenarios,400)

    def test_tarifa_raster_margin_requires_complete_compact_spacing(self):
        # The actual c139192 720p capture rejected Tarifa before requesting a
        # fresh frame. Its log did not retain Canvas geometry. Reuse the prior
        # original's obstacle envelopes and stress the host model by one extra
        # pixel per glyph row; this is a deliberate capacity margin, not a
        # claim to reproduce the unknown Canvas metrics exactly.
        boss=next(x for x in BOSSES if x['id']=='boss_tarifa')
        attack=next(x for x in boss['attacks'] if x['id']=='tether_lash')
        c.font=ImageFont.truetype(str(c.FONT),38)
        blocks=[(14.4,62.64,612,98),(725.6,62.64,540,163),
                (14.4,392,1251.2,122),(999.2,518,262.8,180.4),(18,640.8,244.8,57.6),
                (629.25,349.25,21.5,21.5)]
        regions=self.regions(1280,720,blocks)
        rows=[(boss['name_ja'],boss['name_en'],.65,.60),
              ('冷却外套：被害七割減','MANTLE: 70% less damage',.34,.30),
              (attack['tell_ja'],attack['tell_en'],.65,.60),('0.5 s','',.48,.48),(*MAROBASHI,.36,.32)]
        normal=[r for r in regions if measured_height(rows,r[2],True,glyph_margin=1)<=r[3]]
        compact=[r for r in regions if measured_height(rows,r[2],True,compact=True,glyph_margin=1)<=r[3]]
        self.assertFalse(normal,'One pixel per row consumes the earlier host-only fit')
        self.assertTrue(compact,'Whitespace fallback must retain capacity with the extra row margin')
        for region in compact:
            placed=(*region[:3],measured_height(rows,region[2],True,compact=True,glyph_margin=1))
            self.assertTrue(all(not overlaps(placed,block) for block in blocks))
        # No smaller type, missing row or changed meter can manufacture a fit.
        combat=(c.R/'Source/SoraArena/Private/HUD/SoraHUDCombatPanels.cpp').read_text()
        measure=combat[combat.index('FBossLayout MeasureBoss'):combat.index('FBossLayout BossLayout')]
        self.assertEqual(measure.count('Compact?'),1) # only the gap changes by mode
        self.assertIn('Gap=Compact?2.f:4.f',measure)
        for token in ('Y+=3.f','Inner,7.f','2.f,13.f','Inner,3.f','Y+=17.f','Inner,4.f'):
            self.assertIn(token,measure)
        layout=combat[combat.index('FBossLayout BossLayout'):combat.index('FBox2D BossPanelBounds')]
        self.assertLess(layout.index('if(Clear(Preferred))'),layout.index('Pass<2'))
        self.assertIn('const bool Compact=Pass==1',layout)
        self.assertIn('if(Trial.Bounds.GetSize().Y>R.H) continue',layout)
        for field in ('boss=%s phase_index=%d health=','attack=%s serial=','free_region_%d','rows=%d meters=%d',
                      'row group=%d scale=','obstacle_%d='):
            self.assertIn(field,layout)

    def test_no_capacity_is_a_failure_not_hidden_content(self):
        blocks=[(0,0,1280,720)]
        self.assertEqual(self.regions(1280,720,blocks),[])
        combat=(c.R/'Source/SoraArena/Private/HUD/SoraHUDCombatPanels.cpp').read_text()
        self.assertIn('return Preferred;',combat)
        self.assertIn('if(!L.bFits)',combat)
        self.assertIn('Boss wrapping lost localized content',combat)

    def test_shared_draw_gate_and_story_first_dependency_are_explicit(self):
        combat=(c.R/'Source/SoraArena/Private/HUD/SoraHUDCombatPanels.cpp').read_text()
        story=(c.R/'Source/SoraArena/Private/HUD/SoraHUDStoryPanels.cpp').read_text()
        self.assertIn('const auto L=BossLayout(Frame);',combat)
        self.assertIn('const auto L=BossLayout(F,&Why);',combat)
        self.assertIn('if(!BossLayoutFits(F,Why)) return false;',story)
        builders=story[:story.index('void DrawUpperStory(')]
        self.assertNotIn('UpperGameplayPanelBounds',builders)
        self.assertEqual(builders.count('FixedGameplayPanelBounds(F)'),6)
        obstacles=story[story.index('TArray<FBox2D> SoraHUDPanels::BossLayoutObstacles'):story.index('bool SoraHUDPanels::StoryNoticeTitleVisible')]
        for token in ('FixedGameplayPanelBounds','UpperStoryPanelBounds','BuildLowerStoryLayout','RhythmPanelBounds','AimWindow','WeaponPanelBounds','ReticlePanelBounds'):
            self.assertIn(token,obstacles)
        self.assertNotIn('UpperGameplayPanelBounds',obstacles)
        for capture in ('SoraBowAimCapture.cpp','SoraCargoCapture.cpp'):
            self.assertIn('StoryTrackerLayoutFits(Layout,',(c.R/'Source/SoraArena/Private'/capture).read_text())
        campaign=(c.R/'Source/SoraArena/Private/SoraCaptureAutomation.cpp').read_text()
        save=campaign[campaign.index('void SaveFrame('):campaign.index('FString BossSeen(')]
        self.assertLess(save.index('StoryTrackerLayoutFits'),save.index('FScreenshotRequest::RequestScreenshot'))
        self.assertIn('Session->bFrameLayoutRejected ||',save)
        self.assertIn('OnReticleDrawn.AddLambda',save)
        self.assertIn('OnScreenshotRequestProcessed().AddLambda',save)
        self.assertIn('!HUD->bShowHUD||!M->GetWorld()->IsPaused()',save)
        self.assertIn('SoraCaptureFrameRules::Processed(State,Current->GameplayRequestFrame,GFrameCounter',save)
        self.assertIn('GetTimeSeconds(),Current->GameplayPausedWorld',save)
        self.assertIn('double GameplayPausedWorld',campaign)
        self.assertNotIn('float GameplayPausedWorld',campaign)
        self.assertIn('Queue([Session]() { Session->CloseGameplayFrameGuard(); });',save)
        association=campaign[campaign.index('SaveFrame(Test, Session, Shot.Name);'):campaign.index('// ---- Practice ----')]
        self.assertLess(association.index('if(!Session->bFrameWritten||Session->bFrameLayoutRejected)'),association.index('TEXT("SORA_CAPTURE %s'))
        self.assertIn('SORA_CAPTURE_REJECTED',association)


if __name__=='__main__': unittest.main()
