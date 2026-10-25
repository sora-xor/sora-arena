import copy
import json
from pathlib import Path
import unittest
from campaign_archive import archive_valid


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.chapter=json.loads((Path(__file__).resolve().parents[2]/'Content/Data/campaign/chapter_06.json').read_text())

    def test_authored_posts_are_inside_the_duel_ring(self):
        self.assertTrue(archive_valid(self.chapter))
        record=self.chapter['space']['beats'][8];zone=self.chapter['space']['zones'][record['zone']]
        x,y=zone['rect'][:2]
        self.assertEqual([(p[0]-x,p[1]-y) for p in zone['cover']],[(900,600),(1700,600),(900,1200),(1700,1200)])
        for px,py,w,h,z in zone['cover']:
            self.assertTrue(x+700<px-w/2<px+w/2<x+1900)
            self.assertTrue(y+400<py-h/2<py+h/2<y+1400)
            self.assertEqual(z,600)

    def test_room_and_work_anchors_cannot_silently_return_to_generic_layout(self):
        for mutate in (lambda z:z['rect'].__setitem__(2,z['rect'][2]+1000),
                       lambda z:z['cover'].pop(),lambda z:z['cover'][0].__setitem__(4,100),
                       lambda z:z.update(wall_cm=700)):
            c=copy.deepcopy(self.chapter);mutate(c['space']['zones'][c['space']['beats'][8]['zone']]);self.assertFalse(archive_valid(c))
        c=copy.deepcopy(self.chapter);c['space']['beats'][9]['anchor'][0]+=100
        self.assertFalse(archive_valid(c))


if __name__=='__main__': unittest.main()
