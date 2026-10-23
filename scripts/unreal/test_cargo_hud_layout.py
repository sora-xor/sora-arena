"""Independent font capacity for the exact cargo HUD failures; no Unreal/render.

The live capture checks actual Canvas rows and every obstacle separately. These
host font measurements exercise the existing production free-region planner.
"""
import itertools
import json
import subprocess
import unittest
from PIL import ImageFont
import test_caption_layout as c


class CargoHUDLayoutTests(unittest.TestCase):
    setUpClass=classmethod(c.CaptionLayoutTests.setUpClass.__func__)
    tearDownClass=classmethod(c.CaptionLayoutTests.tearDownClass.__func__)

    def regions(self, view, blocks, gap):
        values=(*view,len(blocks),gap,*itertools.chain.from_iterable(blocks))
        out=subprocess.check_output([str(self.binary),'aim-free'],input=' '.join(map(str,values))+'\n',text=True)
        return [tuple(map(float,line.split())) for line in out.splitlines()]

    def test_cargo_objectives_wrap_inside_allocated_panel_without_lost_text(self):
        chapter=json.loads((c.R/'Content/Data/campaign/chapter_04.json').read_text())
        beat=chapter['beats'][13]
        for px,(w,h),done in itertools.product((37,38),((1280,720),(1920,1080)),range(4)):
            c.font=ImageFont.truetype(str(c.FONT),px); scale=min(w/1600,h/1000)
            inner=min(w-40*scale,850*scale)-20*scale
            text=f"{beat['title_en']} / Barley: {30-10*done} sheaves left / Delivered {done} of 3"
            size=max(.60*scale,.60)
            rows=c.wrap(text,size,inner)
            self.assertEqual(''.join(rows),text)
            self.assertTrue(all(c.width(row,size)<=inner+.01 for row in rows))
            if w==1280:  # The actual failed single line cannot fit at 720p.
                self.assertGreater(len(rows),1)
                self.assertGreater(c.width(text,size),inner)
            leading=max(20*scale,20,c.font.font.height*size+4*scale)
            for a,b in zip(range(len(rows)),range(1,len(rows))):
                self.assertGreaterEqual(b*leading,a*leading+c.font.font.height*size)

    def test_final_registry_title_and_detail_fit_clear_of_boss_tracker_and_dialogue(self):
        # Observed failed 720p run: lower-story top is 305.16, strict limit
        # 300.84, and the rejected right notice starts273.18 and ends328.35.
        # The objective envelope below is deliberately taller than that run's
        # new one-line b16 header; the boss/tracker envelopes stay untouched.
        heading=c.strings['SoraArena.Registry,Notice']
        ja=heading[0].replace('{Goods}','麦 30束')+'  |  麦 残り 0束'
        en=heading[1].replace('{Goods}','Barley: 30 sheaves')+' / Barley: 0 sheaves left'
        for px,(w,h) in itertools.product((37,38),((1280,720),(1920,1080))):
            c.font=ImageFont.truetype(str(c.FONT),px); s=min(w/1600,h/1000); ratio=w/1280; gap=6*s
            limit=300.84*ratio
            blocks=[(20*s,87*s,850*s,110*ratio),
                    (400*ratio,165*ratio,480*ratio,142*ratio),
                    (725.6*ratio,62.64*ratio,540*ratio,210.54*ratio)]
            free=self.regions((20*s,87*s,w-40*s,limit-87*s),blocks,gap)
            fits=[]
            for x,y,width,height in free:
                inner=width-20*s
                title=c.row(ja,en,inner,s,True)
                detail=c.row('記帳済み','Recorded',inner,s,True)
                required=title+gap+detail+6*s
                if required<=height:
                    fits.append((x,y,width,required))
                    self.assertLessEqual(y+required,limit+.01)
                    for bx,by,bw,bh in blocks:
                        self.assertFalse(x<bx+bw and x+width>bx and y<by+bh and y+required>by)
            self.assertTrue(fits,(px,w,h,free))
        self.assertGreater(328.35,300.84)  # Preserve the actual failed bound as a rejection.

    def test_source_draw_and_gate_share_rows_and_actual_panel_obstacles(self):
        combat=(c.R/'Source/SoraArena/Private/HUD/SoraHUDCombatPanels.cpp').read_text()
        story=(c.R/'Source/SoraArena/Private/HUD/SoraHUDStoryPanels.cpp').read_text()
        self.assertIn('FBox2D ObjectivePanelBounds(const FSoraHUDFrame& F) { return ObjectiveLayout(F).Bounds; }',combat)
        self.assertIn('const auto L=ObjectiveLayout(Frame);',combat)
        self.assertIn('if(!ObjectiveLayoutFits(F,Why)) return false;',story)
        self.assertIn('Objective wrapping lost localized text',combat)
        self.assertNotIn('W-60*S,EnglishSubtitleLineHeight,2',combat)
        self.assertIn('if(Panel.bNotice)',story)
        self.assertNotIn('if(Panel.bNotice&&Panel.Bounds.Min.X<870*F.S)',story)


if __name__=='__main__': unittest.main()
