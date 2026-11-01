"""Tests for replay_parity_evidence: a run's parity disagreements, replayed in float64 from the saved evidence alone.

Run: python3 -m unittest scripts/art/test_replay_parity_evidence.py

Evidence is written as rig_nyaakoto_runtime.save_evidence writes it (one .npz per event, index.jsonl with each one's
SHA-256), from mesh_clearance._inside with its two rays made to disagree:
- a point outside a tetrahedron (inside its bounds) and one inside replay to the recorded verdicts, and the
  independent rays find the truth (both even outside, both odd inside);
- root's counterexample, a tetrahedron with two faces turned, replays as undecidable;
- a file changed after it was indexed fails its hash.
"""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mesh_clearance as MC  # noqa: E402
import replay_parity_evidence as R  # noqa: E402


class Miscount(MC.BruteBackend):
    def ray_hits(self, tree, origin, direction):
        n = super().ray_hits(tree, origin, direction)
        if np.allclose(direction, MC.RAYS[0]):
            other = super().ray_hits(tree, origin, MC.RAYS[1])
            return n + 1 if n % 2 == other % 2 else n
        return n


def write(d, label, faces, verts, p):
    s = MC.TriSet(faces, ["t"] * len(faces))
    log = []
    MC._inside(Miscount(), {}, "k", s, verts, 0, np.asarray(p, np.float64), resolve=True, log=log, name="t")
    e = log[0]
    path = d / f"{label}.npz"

    def hits(lst):
        return np.array([[h[0], h[1], np.nan, np.nan, np.nan] for h in lst], np.float64).reshape(-1, 5)
    np.savez(path, point=e["point"], vertices=e["vertices"], triangles=e["triangles"], rays=e["rays"],
             hits_0=hits(e["ray_hit_lists"][0]), hits_1=hits(e["ray_hit_lists"][1]))
    row = {"file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "frame": label, "gate": "test",
           "test": "t", "ray_hits": e["ray_hits"], "resolve_parity": True, "decidable": e["decidable"],
           "verdict": e["verdict"], **{k: e[k] for k in ("oriented_manifold", "finite", "min_area_m2",
                                                         "signed_volume_m3", "gap_m", "winding", "nearest_integer",
                                                         "off_integer")}}
    with open(d / "index.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")
    return e


class Replay(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        v, f = MC.tetra((0.0, 0.0, 0.0), 0.05)
        turned = f.copy()
        turned[:2] = turned[:2, ::-1]
        corner = v.min(0) + 0.05 * (v.max(0) - v.min(0))
        self.events = {"outside": write(self.d, "outside", f, v, corner), "inside": write(self.d, "inside", f, v, np.zeros(3)),
                       "turned": write(self.d, "turned", turned, v, np.zeros(3))}

    def tearDown(self):
        self.tmp.cleanup()

    def test_each_verdict_replays(self):
        s = R.replay(self.d)
        self.assertTrue(s["sha256_ok"] and s["agree"])
        rows = {r["frame"]: r for r in s["rows"]}
        self.assertIs(rows["outside"]["replay"]["verdict_by_rule"], False)
        self.assertIs(rows["inside"]["replay"]["verdict_by_rule"], True)
        self.assertIsNone(rows["turned"]["replay"]["verdict_by_rule"])
        self.assertFalse(rows["turned"]["replay"]["oriented_manifold"])
        # the independent rays' merged counts agree with each other, and with the truth
        self.assertEqual([c % 2 for c in rows["outside"]["replay"]["ray_counts_merged_1e-9"]], [0, 0])
        self.assertEqual([c % 2 for c in rows["inside"]["replay"]["ray_counts_merged_1e-9"]], [1, 1])

    def test_a_changed_file_fails_its_hash(self):
        z = dict(np.load(self.d / "outside.npz"))
        z["point"] = z["point"] + 1e-3
        np.savez(self.d / "outside.npz", **z)
        s = R.replay(self.d)
        self.assertFalse(s["sha256_ok"])


if __name__ == "__main__":
    unittest.main()
