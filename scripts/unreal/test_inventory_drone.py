"""Reject corrupt source and plausible-but-wrong imported drone geometry."""
import copy
import json
import math
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from inventory_drone import NAME, SOURCE, geometry_readback, socket_readback, source_record

ROOT = Path(__file__).resolve().parents[2]


class InventoryDroneAdmission(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = source_record(ROOT)

    def geometry(self):
        lods = []
        for row in self.record["envelope"]["lods"]:
            low, high = row["bounds_min_m"], row["bounds_max_m"]
            points = [(100*low[0], 0, 0), (100*high[0], 0, 0),
                      (0, -100*high[1], 0), (0, -100*low[1], 0),
                      (0, 0, 100*low[2]), (0, 0, 100*high[2])]
            lods.append((points, row["triangles"]))
        return lods

    def sockets(self):
        return {name: {"position": [100*p[0], -100*p[1], 100*p[2]], "scale": [1, 1, 1],
                       "forward": [1, 0, 0] if name == "Eye" else [math.sqrt(.5), 0, -math.sqrt(.5)]}
                for name, p in self.record["assets"][NAME]["sockets"].items()}

    def test_reviewed_source_bytes_and_valid_measurements(self):
        self.assertEqual(len(geometry_readback(self.record, self.geometry(), [1, .35, .12])), 3)
        self.assertEqual(set(socket_readback(self.record, self.sockets())), {"Eye", "NetMuzzle"})

    def test_a_corrupt_fbx_cannot_be_imported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(ROOT / SOURCE, root / SOURCE)
            file = root / self.record["assets"][NAME]["lods"][0]["file"]
            file.write_bytes(file.read_bytes() + b"corruption")
            with self.assertRaisesRegex(RuntimeError, "changed source"):
                source_record(root)

    def test_record_cannot_redefine_the_envelope_to_admit_bad_art(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / SOURCE).mkdir(parents=True)
            bad = copy.deepcopy(self.record)
            bad["envelope"]["design_bound_m"] = .50
            (root / SOURCE / "build_record.json").write_text(json.dumps(bad))
            with self.assertRaisesRegex(RuntimeError, "unreviewed build record"):
                source_record(root)

    def test_correct_triangle_count_does_not_hide_wrong_scale_or_pivot(self):
        for scale, offset in ((.6, 0), (1, 2), (100, 0)):
            with self.subTest(scale=scale, offset=offset):
                lods = [([tuple(scale*v+offset for v in p) for p in points], count)
                        for points, count in self.geometry()]
                with self.assertRaises(RuntimeError):
                    geometry_readback(self.record, lods, [1, .35, .12])

    def test_bounds_alone_do_not_hide_a_vertex_outside_the_sphere(self):
        lods = self.geometry()
        lods[0][0].append((30, 30, 0))  # within the AABB, outside the sphere
        with self.assertRaisesRegex(RuntimeError, "escaped its design sphere"):
            geometry_readback(self.record, lods, [1, .35, .12])

    def test_reduced_or_missing_lod_is_rejected(self):
        lods = self.geometry()
        lods[1] = (lods[1][0], lods[1][1]-1)
        with self.assertRaisesRegex(RuntimeError, "lost authored triangles"):
            geometry_readback(self.record, lods, [1, .35, .12])
        with self.assertRaisesRegex(RuntimeError, "three authored LODs"):
            geometry_readback(self.record, lods[:1], [1])

    def test_missing_reversed_scaled_and_moved_sockets_are_rejected(self):
        for bad in ("missing", "reversed", "scaled", "moved"):
            with self.subTest(bad=bad):
                sockets = self.sockets()
                if bad == "missing":
                    del sockets["Eye"]
                elif bad == "reversed":
                    sockets["NetMuzzle"]["forward"] = [-math.sqrt(.5), 0, math.sqrt(.5)]
                elif bad == "scaled":
                    sockets["Eye"]["scale"] = [100, 100, 100]
                else:
                    sockets["Eye"]["position"][0] += 1
                with self.assertRaises(RuntimeError):
                    socket_readback(self.record, sockets)

    def test_nonfinite_vertex_is_rejected(self):
        lods = self.geometry()
        lods[0][0].append((float("nan"), 0, 0))
        with self.assertRaisesRegex(RuntimeError, "invalid render vertex"):
            geometry_readback(self.record, lods, [1, .35, .12])


if __name__ == "__main__":
    unittest.main()
