"""Independent Noto/FreeType inputs to the production archery HUD packer.

No Unreal or screenshots. Canvas glyph assertions run on each live BowAim
capture frame; the unchanged archive pixel gate remains separately required.
"""
import itertools
from functools import lru_cache
import json
import subprocess
import unittest
from PIL import ImageFont
import test_caption_layout as c

# Memoize identical FreeType queries across the exhaustive content matrix.
_fonts={n:ImageFont.truetype(str(c.FONT),n) for n in (37,38)}
@lru_cache(maxsize=65536)
def width(px,text,scale): return _fonts[px].getlength(text)*scale
@lru_cache(maxsize=65536)
def ink(px,text,scale):
    b=_fonts[px].getbbox(text); return (b[3]-b[1])*scale
c.width=lambda text,scale:width(c.font.size,text,scale)
c.ink=lambda text,scale:ink(c.font.size,text,scale)
R = c.R
chapter = json.loads((R / 'Content/Data/campaign/chapter_01.json').read_text())
lines = [x for x in chapter['lines'] if x['beat'] == 'ch01.b07']
prompts = [x for x in chapter['ui_prompts'] if 'ch01.b07' in x['beats']]
catalog=json.loads((R / 'Content/Data/catalog.json').read_text())
speakers = {x['id']: x for x in catalog['dialogue_speakers']}
# Production CampaignUnlocked refusal: any locked weapon can be requested
# while the bow tutorial/dialogue is active. Keep the actual catalog names.
refusals=[{'ja':x['name']+'はまだ手にしていない。',
           'en':x['name_en']+' is not yet unlocked in the campaign.'} for x in catalog['weapons']]



def overlaps(a, b):
    x,y,w,h=a; u,v,p,q=b
    return x < u+p-.03 and u < x+w-.03 and y < v+q-.03 and v < y+h-.03


def story(text, width, scale, size, english, speaker_names, dialogue):
    inner=width-20*scale
    def block(t,z,base):
        wrapped=c.wrap(t,z,inner)
        assert ''.join(wrapped)==t, (t,wrapped)
        assert all(c.width(x,z)<=inner+.01 for x in wrapped)
        return len(wrapped)*max(base,max((c.ink(x,z)+3 for x in wrapped),default=0))
    jz=max(.65*scale,.65); ez=max(.60*scale,.60)
    jl=max(24*scale,22); el=max(20*scale,20)
    height=20*scale
    if dialogue:
        if speaker_names:
            speaker=speakers[text['speaker']]
            j=max(.55*scale,.55)*size; e=max(.52*scale,.52)*size
            jh=block(speaker['ja'],j,0)
            eh=block(speaker['en'],e,0) if english else 0
            height += max(jh,eh) if english and c.width(speaker['ja'],j)+6*scale+c.width(speaker['en'],e)<=inner else jh+eh
        jz*=size; ez*=size; jl*=size; el*=size
    height+=block(text['ja'],jz,jl)
    if english: height+=block(text['en'],ez,el)
    return height


class AimLayoutTests(unittest.TestCase):
    setUpClass=classmethod(c.CaptionLayoutTests.setUpClass.__func__)
    tearDownClass=classmethod(c.CaptionLayoutTests.tearDownClass.__func__)
    arrange=c.CaptionLayoutTests.arrange
    assert_clear=c.CaptionLayoutTests.assert_clear

    def regions(self, mode, values):
        out=subprocess.check_output([str(self.binary),mode],input=' '.join(map(str,values))+'\n',text=True)
        return [tuple(map(float,x.split())) for x in out.splitlines()]

    def test_authored_tutorial_complete_and_center_clear(self):
        cases=0
        for px,(W,H),size,en,names in itertools.product((37,38),((1280,720),(1920,1080)),(1,1.25,1.5),(False,True),(False,True)):
            c.font=ImageFont.truetype(str(c.FONT),px)
            s=min(W/1600,H/1000); gap=6*s
            # Bounds from the production panels; the windup is at the same X
            # as weapon. Objective uses full-font leading, not ink leading.
            left=W-390*s
            obj=max((212 if en else 177)*s,137*s+c.font.font.height*.52*s+4*s,
                    164*s+max(20*s,20)+c.font.font.height*max(.6*s,.6)+4*s if en else 0)
            regions=self.regions('aim-regions',(W,H,s,obj,left))
            aim=(W*.4,H*.38,W*.2,H*.24)
            fixed=[aim,(25*s,H-110*s,340*s,80*s),(left,0,390*s,H),(20*s,87*s,850*s,obj-87*s)]
            for cue,prompt,key in itertools.product(lines,prompts,(('［左マウスボタン］','[Left Mouse Button]'),('［右トリガー］','[Right Trigger]'))):
                prompt={**prompt,'ja':prompt['ja'].replace('{Fire}',key[0]),'en':prompt['en'].replace('{Fire}',key[1])}
                texts=[(cue,True),(prompt,False)]
                heights=[[story(t,r[2],s,size,en,names,d) for r in regions] for t,d in texts]
                plan=self.arrange(regions,heights,gap)
                self.assert_clear(regions,heights,gap,plan)
                for _,x,y,w,h in plan:
                    self.assertFalse(any(overlaps((x,y,w,h),b) for b in fixed),(cue['id'],prompt['id'],px,W,H,size,en,names,plan))
                cases+=1
        print(f'{cases} complete authored tutorial layouts; JA/EN, all subtitle sizes/speakers, mouse/gamepad, 720p/1080p, 37/38px font')

    def test_locked_weapon_notice_with_complete_tutorial(self):
        cases=0
        for (W,H),size,en in itertools.product(((1280,720),(1920,1080)),(1,1.25,1.5),(False,True)):
            c.font=ImageFont.truetype(str(c.FONT),38)
            s=min(W/1600,H/1000); gap=6*s; left=W-390*s
            obj=max(212*s,164*s+max(20*s,20)+c.font.font.height*max(.6*s,.6)+4*s)
            regions=self.regions('aim-regions',(W,H,s,obj,left))
            # Envelope of every actual catalog refusal at each candidate
            # width proves capacity for each reachable locked-weapon notice.
            notice=[max(story(t,r[2],s,size,en,True,False) for t in refusals) for r in regions]
            for cue,prompt in itertools.product(lines,prompts):
                prompt={**prompt,'ja':prompt['ja'].replace('{Fire}','［左マウスボタン］'),'en':prompt['en'].replace('{Fire}','[Left Mouse Button]')}
                heights=[[story(cue,r[2],s,size,en,True,True) for r in regions],notice,
                         [story(prompt,r[2],s,size,en,True,False) for r in regions]]
                plan=self.arrange(regions,heights,gap); self.assert_clear(regions,heights,gap,plan)
                for p in plan: self.assertFalse(overlaps(p[1:],(W*.4,H*.38,W*.2,H*.24)))
                cases+=1
        print(f'{cases} three-panel layouts with every catalog locked-weapon notice bounded')

    def test_captions_keep_all_text_around_live_tutorial(self):
        # Four captions with dialogue+prompt, or two with the additional
        # worst-catalog refusal. The synthetic all-three-panels + four combat
        # captions overload at 720p/extra-large is outside verified capacity;
        # production still retains the text and reports capacity failure.
        # Hero bow shots do not create captions (USoraCaptions::WeaponFired).
        cue=next(x for x in lines if x['id'].endswith('baio.008'))
        prompt=prompts[0]; prompt={**prompt,'ja':prompt['ja'].replace('{Fire}','［左マウスボタン］'),'en':prompt['en'].replace('{Fire}','[Left Mouse Button]')}
        for (W,H),size,en,notice in itertools.product(((1280,720),(1920,1080)),(1,1.25,1.5),(False,True),(False,True)):
            c.font=ImageFont.truetype(str(c.FONT),38)
            s=min(W/1600,H/1000); gap=6*s; left=W-390*s
            obj=max(212*s,164*s+max(20*s,20)+c.font.font.height*max(.6*s,.6)+4*s)
            regions=self.regions('aim-regions',(W,H,s,obj,left))
            heights=[[story(t,r[2],s,size,en,True,d) for r in regions] for t,d in ((cue,True),(prompt,False))]
            if notice: heights.insert(1,[max(story(t,r[2],s,size,en,True,False) for t in refusals) for r in regions])
            plan=self.arrange(regions,heights,gap); self.assert_clear(regions,heights,gap,plan)
            aim=(W*.4,H*.38,W*.2,H*.24)
            tx=max(W-20*s-min(max(435*s,540),W-902*s),W*.6+gap)
            inner=W-40*s-tx
            tracker=6*s+2*max(2*s,1.5)+sum(c.row(j,e,inner,s,en,frac=f) for j,e,f in (
                ('第7場 / 17','Beat 7 of 17',False),('近的：6 / 6 射・3 / 4 中','Near target: 6 / 6 arrows, 3 / 4 hits',True),
                ('矢取り：残り 8 秒','Fetching arrows: 8 s remaining',False)))
            fixed=[aim,(25*s,H-110*s,340*s,80*s),(left,H-440*s,365*s,410*s),
                   (20*s,87*s,850*s,obj-87*s),(tx,87*s,W-20*s-tx,tracker)]
            fixed += [p[1:] for p in plan]
            free=self.regions('aim-free',(20*s,87*s,W-40*s,H-117*s,len(fixed),gap,*itertools.chain.from_iterable(fixed)))
            for region in free: self.assertFalse(any(overlaps(region,b) for b in fixed))
            keys=['ArrowLoosed','WoodenSwordsKnock'] if notice else ['ArrowLoosed','WoodenSwordsKnock','BladesClash','BladeDrawnBack']
            hs=[[c.caption(k,r[2],s,size,en) for r in free] for k in keys]
            captions=self.arrange(free,hs,gap)
            self.assert_clear(free,hs,gap,captions)
            for p in captions: self.assertFalse(any(overlaps(p[1:],b) for b in fixed))
            if notice and W==1280 and size==1.5 and en:
                overload=[[c.caption(k,r[2],s,size,en) for r in free] for k in
                          ('ArrowLoosed','WoodenSwordsKnock','BladesClash','BladeDrawnBack')]
                self.assertIsNone(self.arrange(free,overload,gap),
                    'Revisit the documented unsupported overload if allocation capacity changes')

    def test_old_capture_geometry_is_rejected(self):
        aim=(512,273.6,256,172.8)
        # Actual 720p capture frames: the former full-width prompt/dialogue.
        for box in ((14,280,1252,122),(14,320,1252,82),(14,361,1252,122)):
            self.assertTrue(overlaps(aim,box))

    def test_progress_uses_resolved_arrows_and_unique_hanging_targets(self):
        self.assertEqual(subprocess.check_output([str(self.binary),'aim-progress'],text=True).strip(),'progress passed')

    def test_unsupported_capacity_is_not_silently_accepted(self):
        self.assertIsNone(self.arrange([(0,0,200,20)],[[40]],4))

if __name__=='__main__': unittest.main()
