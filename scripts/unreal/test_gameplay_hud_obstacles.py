"""Observed Campaign reticle/stealth failures, with real font and free-region code.

Host capacity checks only. Paused current-Canvas gates and original PNG review
remain required; these measurements are not rendered acceptance.
"""
import itertools
import json
import subprocess
import unittest
from PIL import ImageFont
import test_caption_layout as c
import test_boss_hud_layout as b


class GameplayHUDObstacleTests(unittest.TestCase):
    setUpClass=classmethod(c.CaptionLayoutTests.setUpClass.__func__)
    tearDownClass=classmethod(c.CaptionLayoutTests.tearDownClass.__func__)
    regions=b.BossHUDLayoutTests.regions
    placements=b.BossHUDLayoutTests.placements

    def test_observed_tarifa_hint_clears_ordinary_projected_and_maai_reticles(self):
        boss=next(x for x in b.BOSSES if x['id']=='boss_tarifa')
        attack=next(x for x in boss['attacks'] if x['id']=='tether_lash')
        # Actual failed 720p frame: boss spans230..384 and its English hint
        # crosses the katana crosshair at640,360. Keep the other HUD regions.
        old=(14.4,230,1251.2,154)
        self.assertTrue(b.overlaps(old,(629.25,349.25,21.5,21.5)))
        observed=[(14.4,62.64,612,98),(725.6,62.64,540,163),
                  (14.4,392,1251.2,122),(999.2,518,262.8,180.4),(18,640.8,244.8,57.6)]
        for px,ratio,en,(dx,dy),moon in itertools.product((37,38),(1,1.5),(False,True),((0,0),(32,-14)),(False,True)):
            c.font=ImageFont.truetype(str(c.FONT),px); w,h=1280*ratio,720*ratio; s=min(w/1600,h/1000)
            radius=max(10.75,22*s+.6 if moon else 0)
            center=(w*.5+dx*ratio,h*.5+dy*ratio)
            blocks=[tuple(v*ratio for v in box) for box in observed]
            blocks.append((center[0]-radius,center[1]-radius,2*radius,2*radius))
            # Only the actually observed mantle is active, not every possible
            # hypothetical defense at once. Retain the complete bilingual tell.
            rows=[(boss['name_ja'],boss['name_en'] if en else '',max(.65*s,.65),max(.60*s,.60)),
                  ('冷却外套：被害七割減','MANTLE: 70% less damage' if en else '',.34,.30),
                  (attack['tell_ja'],attack['tell_en'] if en else '',max(.65*s,.65),max(.60*s,.60)),
                  ('0.5 s','',.48,.48),(b.MAROBASHI[0],b.MAROBASHI[1] if en else '',.36,.32)]
            self.assertTrue(self.placements(rows,self.regions(w,h,blocks),blocks,True),(px,ratio,en,dx,dy,moon))

    def test_three_observed_stealth_trackers_fit_without_covering_detection_or_alarm(self):
        for px,ratio,en,(chapter,beat,objective_h,lower,alarm) in itertools.product(
                (37,38),(1,1.5),(False,True),((3,1,98,432,False),(6,5,132.28,392,True),(7,3,98,305.16,False))):
            c.font=ImageFont.truetype(str(c.FONT),px); w,h=1280*ratio,720*ratio; s=min(w/1600,h/1000); gap=6*s
            beats=json.loads((c.R/f'Content/Data/campaign/chapter_{chapter:02}.json').read_text())['beats']; data=beats[beat]
            total=sum(not x['optional'] for x in beats); number=sum(not x['optional'] for x in beats[:beat+1])
            ja=f"第{number}場  {data['title_ja']}"; eng=f"Beat {number} of {total}: {data['title_en']}"
            width=min(max(435*s,540),w-902*s); x=w-20*s-width
            stealth=(w-365*s,87*s,340*s,(104 if en else 84)*s)
            blocks=[(20*s,87*s,850*s,objective_h*ratio),stealth]
            if alarm: blocks.append((stealth[0],stealth[1]+stealth[3]+4*s,stealth[2],(48 if en else 32)*s))
            self.assertTrue(b.overlaps((x,87*s,width,60*ratio),stealth))
            view=(20*s,87*s,w-40*s,lower*ratio-gap-87*s)
            values=(*view,len(blocks),gap,*itertools.chain.from_iterable(blocks))
            output=subprocess.check_output([str(self.binary),'aim-free'],input=' '.join(map(str,values))+'\n',text=True)
            fits=[]
            for line in output.splitlines():
                rx,ry,rw,rh=map(float,line.split()); inner=rw-20*s
                # Compact packing uses visible glyph extents, never smaller type.
                height=6*s+c.row(ja,eng,inner,s,en)+max(2*s,1.5)+c.row('出口まで  0%','0% of the way',inner,s,en,frac=True)
                if height<=rh:
                    fits.append((rx,ry,rw,height))
                    self.assertTrue(all(not b.overlaps(fits[-1],box) for box in blocks))
                    self.assertLessEqual(ry+height,lower*ratio-gap+.01)
                    self.assertEqual(''.join(c.wrap(ja,max(.44*s,.6),inner)),ja)
                    if en: self.assertEqual(''.join(c.wrap(eng,max(.34*s,.55),inner)),eng)
            self.assertTrue(fits,(chapter,px,ratio,en,blocks))

    def test_relocated_tracker_uses_production_caption_regions_and_below_dialogue_fallback(self):
        # Exact ordinary dense-branch region helper, not the separate aim/free
        # planner. A left/wide tracker consumes the former left caption column.
        tracker=(14.4,180,800,105)
        fixed=[(14.4,62.64,612,98),(1017.2,62.64,244.8,112.32),
               (629.25,349.25,21.5,21.5)]
        lower=[(14.4,305.16,1251.2,82),(14.4,392,1251.2,122),
               (999.2,518,262.8,180.4),(18,640.8,244.8,57.6)]
        old_left=(14.4,164.32,706.88,136.52)
        self.assertTrue(b.overlaps(old_left,tracker))
        def regions(blocks):
            # W,H,S,X,Width,NextY,Limit,NoticeReserve,HasHero,WeaponLeft,BottomTop
            values=(1280,720,.72,725.6,540,289.32,300.84,0,1,994.88,518.32,
                    len(blocks),*itertools.chain.from_iterable(blocks))
            output=subprocess.check_output([str(self.binary),'ordinary-caption-regions'],
                input=' '.join(map(str,values))+'\n',text=True)
            return [tuple(map(float,line.split())) for line in output.splitlines()]
        actual=regions(fixed+[tracker])
        self.assertTrue(actual)
        self.assertTrue(all(not b.overlaps(region,tracker) for region in actual))
        # Omitting the tracker recreates falsely free space in this same branch.
        self.assertTrue(any(b.overlaps(region,tracker) for region in regions(fixed)))
        for px,en,size in itertools.product((37,38),(False,True),(1,1.25,1.5)):
            c.font=ImageFont.truetype(str(c.FONT),px)
            heights=[[c.caption(key,r[2],.72,size,en) for r in actual] for key in ('Gunfire','BladeDrawnBack')]
            plan=c.CaptionLayoutTests.arrange(self,actual,heights,4.32)
            c.CaptionLayoutTests.assert_clear(self,actual,heights,4.32,plan)
            for _,x,y,w,h in plan:
                self.assertGreaterEqual(y,518.32-.02)
                for block in fixed+[tracker]+lower:
                    self.assertFalse(b.overlaps((x,y,w,h),block))

    def test_actual_frame_guard_rejects_hidden_unpaused_stale_and_mismatched_originals(self):
        def check(values):
            return tuple(map(int,subprocess.check_output([str(self.binary),'capture-frame'],
                input=' '.join(map(str,values))+'\n',text=True).split()))
        valid=[1,1,1,1234.5678912345,1234.5678912345,5001,5001,1,1]
        self.assertEqual(check(valid),(1,1))
        for index,bad in ((0,0),(1,0),(2,0),(3,1234.5678912346)):
            value=valid.copy(); value[index]=bad
            with self.subTest(index=index): self.assertEqual(check(value),(0,0))
        for index,bad in ((5,0),(6,5002),(7,0),(8,0)):
            value=valid.copy(); value[index]=bad
            with self.subTest(index=index): self.assertEqual(check(value),(1,0))

    def test_shared_geometry_and_ordinary_gameplay_capture_guard_preserve_content(self):
        combat=(c.R/'Source/SoraArena/Private/HUD/SoraHUDCombatPanels.cpp').read_text()
        story=(c.R/'Source/SoraArena/Private/HUD/SoraHUDStoryPanels.cpp').read_text()
        campaign=(c.R/'Source/SoraArena/Private/SoraCaptureAutomation.cpp').read_text()
        self.assertIn('const auto Reticle=ReticleLayout(Frame,Hero);',combat)
        self.assertIn('return ReticleLayout(Frame,Hero).Bounds;',combat)
        self.assertIn('Kit->BowAimDirection()*10000.f',combat)
        self.assertIn('L.MoonRadius+.6f',combat)
        self.assertIn('for(const auto& Text:Reticle.Text) HUD.Label(',combat)
        self.assertIn('Result.Append(ReticlePanelBounds(F,*Hero));',story)
        tracker=story[story.index('TArray<FTrackerRow> Rows=TrackerRows(F);'):story.index('float NoticeReserve=0.f;')]
        self.assertIn('FixedGameplayPanelBounds(F)',tracker)
        self.assertIn('auto Trial=Tracker(R.X,R.Y,R.W)',tracker)
        self.assertIn('Rows[0]=CompactHeading',tracker)
        self.assertIn('for(const auto& Panel:L.Panels) Obstacles.Add(Panel.Bounds);',story)
        self.assertIn('OrdinaryCaptionRegions(Input,Blocks.GetData(),Blocks.Num())',story)
        registry=(c.R/'scripts/qualification/source_checks.py').read_text()
        self.assertIn('scripts/unreal/test_gameplay_hud_obstacles.py',registry)
        caption_gate=story[story.index('bool SoraHUDPanels::CaptionStoryLayoutFits'):story.index('float SoraHUDPanels::GameplayStoryTop')]
        self.assertIn('Occupied.Append(ReticlePanelBounds(F,*Hero))',caption_gate)
        gate=story[story.index('bool SoraHUDPanels::StoryTrackerLayoutFits'):story.index('bool SoraHUDPanels::BottomHUDLayoutFits')]
        self.assertNotIn('if(Panel.bNotice)',gate)
        self.assertIn('Tracker/notice wrapping lost localized content',gate)
        guard=campaign[campaign.index('bool CampaignGameplayFrame('):campaign.index('FString BossSeen(')]
        for token in ('Mode->bCampaign','Mode->Hero()','EType::Cinematic','!Mode->bMenu','!Mode->TitleCardChapter()','!SoraHUDPanels::ShowsRegistry',
                      'OnReticleDrawn.AddLambda','StoryTrackerLayoutFits','CaptionStoryLayoutFits(Layout,Why)','OnScreenshotRequestProcessed().AddLambda','SoraCaptureFrameRules::Processed(State,Current->GameplayRequestFrame,GFrameCounter'):
            self.assertIn(token,guard)
        self.assertNotIn('CampaignBoss()',guard)


if __name__=='__main__': unittest.main()
