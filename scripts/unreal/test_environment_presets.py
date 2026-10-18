"""Host tests for the environment lighting presets, CC0 surface assignments and seeded scatter.

Run: python3 scripts/unreal/test_environment_presets.py
Needs only the committed ledgers, the story bible and the world-builder lighting source; the
moss-cushion coverage test also reads moss_01's glTF from Local/ and is skipped without it.
"""

from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cc0_environment_library as L  # noqa: E402
import environment_presets as P  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
BIBLE = ROOT / "docs/campaign/story-bible.md"
LIGHTING_CPP = ROOT / "Source/SoraArena/Private/World/SoraWorldBuilderLighting.cpp"


def bible_places() -> dict[str, str]:
    """Place id -> chapter ("ch0N") from the story bible's §14 table."""
    rows = re.findall(r"^\| (\d) \| (pl_[a-z_]+) \|", BIBLE.read_text(encoding="utf-8"), re.MULTILINE)
    return {place: f"ch0{chapter}" for chapter, place in rows}


def library_sets(records):
    sets = {L.camel(record.asset_id): L._record_set(record, [], False)
            for record in records.values() if L.is_environment(record) and record.data["kind"] != "hdri"}
    for name, (asset_id, prefix, channels, tile) in L.PALETTE_SETS.items():
        sets[name] = L._palette_set(name, asset_id, prefix, channels, tile)
    sets.update(L._project_sets(ROOT, []))
    return sets


class LightingTest(unittest.TestCase):
    def test_every_chapter_and_arena_has_a_preset(self):
        chapters = {chapter for preset in P.LIGHTING for chapter in preset.chapters}
        self.assertEqual(chapters, {f"ch0{n}" for n in range(1, 9)})
        self.assertEqual(set(P.ARENAS), {0, 1, 2, 3})
        primary = {0: "pl_estate_day", 1: "pl_lantern_ward_rain", 2: "pl_silk_foundry", 3: "pl_citadel_moat"}
        for arena, preset_id in P.ARENAS.items():
            self.assertIn(primary[arena], P.lighting(preset_id).places, arena)
        self.assertEqual(len({preset.id for preset in P.LIGHTING}), len(P.LIGHTING))

    def test_places_are_story_bible_places_of_the_preset_chapter(self):
        places = bible_places()
        self.assertEqual(set(places.values()), {f"ch0{n}" for n in range(1, 9)})  # the §14 table parsed
        for preset in P.LIGHTING:
            for place in preset.places:
                self.assertIn(place, places, preset.id)
                self.assertIn(places[place], preset.chapters, f"{preset.id}: {place}")

    def test_hdris_are_lighting_only_ledger_skies_of_that_chapter(self):
        records = L.load_ledgers(ROOT)
        by_path = {f"{L.HDRI}/{name}.{name}": (asset_id, use) for asset_id, (name, use) in L.HDRIS.items()}
        for preset in P.LIGHTING:
            if preset.sky_hdri in (None, P.ESTATE_OVERCAST_HDRI):
                continue
            self.assertIn(preset.sky_hdri, by_path, preset.id)
            asset_id, use = by_path[preset.sky_hdri]
            self.assertEqual(use, "lighting", f"{preset.id}: look-development HDRIs are never game skies")
            chapters = {chapter for entry in records[asset_id].data["game_use"] for chapter in entry["chapters"]}
            self.assertTrue(chapters & set(preset.chapters), f"{preset.id}: {asset_id} is planned for {chapters}")
            self.assertTrue(any("lighting only" in flag for flag in records[asset_id].flags), asset_id)

    def test_colour_temperatures_follow_the_bible(self):
        expected_keys = {"estate_day": 5200, "wood_dawn_mist": 5200, "estate_golden_dusk": 3800,
                         "estate_night_fire": 4100, "village_hazy_day": 5600, "village_golden_dusk": 3800,
                         "foundry_furnace_night": 1600, "flagship_typhoon": 4100, "causeway_clear_dawn": 3500,
                         "festival_night": 4100}
        for preset in P.LIGHTING:
            self.assertEqual(preset.key_kelvin, expected_keys.get(preset.id), preset.id)
            self.assertEqual(preset.key == "none", preset.key_kelvin is None, preset.id)
            if preset.lantern_kelvin is not None:
                self.assertTrue(1800 <= preset.lantern_kelvin <= 2200, preset.id)  # §15.1 lantern light
        self.assertEqual(P.lighting("lantern_ward_dusk_rain").lantern_kelvin, 1900)  # §16 ch3
        self.assertEqual(P.lighting("lantern_ward_dusk_rain").fog_kelvin, 9000)      # §16 ch3 ambient sky
        self.assertTrue(7000 <= P.lighting("citadel_new_moon").fog_kelvin <= 9000)   # §16 ch6 alien light

    def test_weather_values_drive_the_collection(self):
        for preset in P.LIGHTING:
            for value in (preset.wetness, preset.puddles, preset.lantern_intensity):
                self.assertTrue(0.0 <= value <= 1.0, preset.id)
            if preset.rain:
                self.assertGreaterEqual(preset.wetness, 0.8, preset.id)
            self.assertLessEqual(preset.puddles, preset.wetness, preset.id)
        self.assertTrue(P.lighting("lantern_ward_dusk_rain").rain and P.lighting("flagship_typhoon").rain)
        self.assertEqual(P.MAC_MAX_SHADOWED_LIGHTS, 8)

    def test_the_shipped_preset_matches_the_world_builder(self):
        shipped = [preset for preset in P.LIGHTING if preset.shipped]
        self.assertEqual([preset.id for preset in shipped], ["estate_day"])
        source = LIGHTING_CPP.read_text(encoding="utf-8")
        estate = shipped[0]
        self.assertIn("SetIntensity(bEstate?25.f", source)
        self.assertEqual(estate.key_lux, 25.0)
        self.assertIn("SetIntensity(bEstate?.65f", source)
        self.assertEqual(estate.sky_intensity, 0.65)
        self.assertIn("AutoExposureBias=bEstate?-.45f", source)
        self.assertEqual(estate.exposure_bias, -0.45)
        self.assertIn("SetFogDensity(bEstate?.0045f", source)
        self.assertEqual(estate.fog_density, 0.0045)
        self.assertIn("SetLightSourceAngle(6.f)", source)
        self.assertIn(P.ESTATE_OVERCAST_HDRI.split(".")[0], source)
        self.assertEqual(estate.sky_hdri, P.ESTATE_OVERCAST_HDRI)


class SurfaceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = L.load_ledgers(ROOT)
        cls.sets = library_sets(cls.records)
        cls.instances = {instance.name: instance for instance in L.PLACE_INSTANCES}

    def test_places_exist(self):
        places = bible_places()
        for place in P.SURFACES:
            self.assertTrue(place in places or place == "lane_kit", place)

    def test_assignments_pass_the_library_policy_at_their_place(self):
        for place, roles in P.SURFACES.items():
            for role, names in roles.items():
                self.assertTrue(names, f"{place}.{role}")
                for name in names:
                    self.assertIn(name, self.instances, f"{place}.{role}: {name} is not a place instance")
                    # Every bound ledger record must list this place (and keep its medium role).
                    L.check_instance(replace(self.instances[name], place=place), self.sets, self.records)

    def test_policy_rejects_an_unplanned_place(self):
        # Plaster007 (medium, layer B) is planned for the day estate only.
        with self.assertRaisesRegex(RuntimeError, "not planned for pl_estate_night"):
            L.check_instance(replace(self.instances["MI_EstateDay_Shikkui"], place="pl_estate_night"),
                             self.sets, self.records)
        self.assertNotIn("wall_plaster", P.SURFACES["pl_estate_night"])

    def test_the_shimenawa_is_not_hemp_lashing(self):
        # Rope001's flag: a shimenawa is left-laid rice straw; use Rope001 for hemp lashings only.
        flags = " ".join(self.records["Rope001"].flags)
        self.assertIn("hemp lashings only", flags)
        self.assertNotIn("rope", P.SURFACES["pl_issoseki_wood"])
        self.assertIn("shimenawa", P.UNFILLED["pl_issoseki_wood"])
        with self.assertRaisesRegex(RuntimeError, "not planned for pl_issoseki_wood"):
            L.check_instance(replace(self.instances["MI_Matoba_HempLashing"], place="pl_issoseki_wood"),
                             self.sets, self.records)
        for place, roles in P.UNFILLED.items():
            self.assertFalse(set(roles) & set(P.SURFACES.get(place, {})), place)

    def test_every_place_instance_is_assigned_somewhere(self):
        assigned = {name for roles in P.SURFACES.values() for names in roles.values() for name in names}
        meshes = {name for name, instance in self.instances.items()
                  if self.records.get(self._asset(instance), None) is not None
                  and self.records[self._asset(instance)].data["kind"] == "model"}
        unassigned = set(self.instances) - assigned - meshes - {rule.instance for rule in P.SCATTER}
        self.assertEqual(unassigned, set())

    def _asset(self, instance):
        origin = self.sets[instance.layers[0]].origin
        return origin.split(":", 1)[1] if origin.startswith(("polyhaven:", "ambientcg:")) else None


class ScatterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = L.load_ledgers(ROOT)
        cls.sets = library_sets(cls.records)
        cls.instances = {instance.name: instance for instance in L.PLACE_INSTANCES}

    def test_rules_scatter_scanned_meshes_planned_for_the_place(self):
        places = bible_places()
        for rule in P.SCATTER:
            self.assertIn(rule.place, places)
            instance = self.instances[rule.instance]
            record = self.records[self.sets[instance.layers[0]].origin.split(":", 1)[1]]
            self.assertEqual(record.data["kind"], "model", rule.instance)
            L.check_instance(replace(instance, place=rule.place), self.sets, self.records)
            self.assertGreater(rule.per_100_m2, 0.0)
            self.assertTrue(0 < rule.scale_milli[0] <= rule.scale_milli[1] <= 3000, rule)
            self.assertGreaterEqual(rule.clearance_cm, 0)

    def test_scatter_is_seeded_bounded_and_clear_of_exclusions(self):
        rule = P.SCATTER[1]
        variants = ("A", "B", "C")
        bounds = (-3000, -2000, 3000, 2000)
        path = P.path_exclusions([(-3000, 0), (0, 300), (3000, -200)], 150)
        spawns = [(1500, 1200, 250), (-1800, -1400, 400)]
        first = P.scatter(rule, variants, 7, bounds, path + spawns)
        self.assertEqual(first, P.scatter(rule, variants, 7, bounds, path + spawns))
        self.assertNotEqual(first, P.scatter(rule, variants, 8, bounds, path + spawns))
        self.assertTrue(first)
        for variant, x, y, yaw, scale in first:
            self.assertIn(variant, variants)
            self.assertTrue(bounds[0] <= x < bounds[2] and bounds[1] <= y < bounds[3])
            self.assertTrue(0 <= yaw < 3600)
            self.assertTrue(rule.scale_milli[0] <= scale <= rule.scale_milli[1])
            for cx, cy, radius in path + spawns:
                self.assertGreaterEqual((x - cx) ** 2 + (y - cy) ** 2, (radius + rule.clearance_cm) ** 2)
        self.assertEqual(len({v for v, *_ in first}), 3)

    def test_density_without_exclusions_is_one_per_cell(self):
        rule = P.ScatterRule("pl_kaido", "MI_IssosekiWood_MossRockSet01", 4.0, (1000, 1000), 0)
        cell = P.isqrt_cell_cm(rule.per_100_m2)
        self.assertEqual(cell, 500)
        placed = P.scatter(rule, ("A",), 3, (0, 0, 20 * cell, 10 * cell))
        self.assertEqual(len(placed), 200)  # 4 per 100 m^2: one candidate per 25 m^2 cell, 200 cells
        self.assertEqual({scale for *_, scale in placed}, {1000})

    def test_path_samples_overlap(self):
        circles = P.path_exclusions([(0, 0), (1000, 0), (1000, 777)], 100)
        for (ax, ay, _), (bx, by, _) in zip(circles, circles[1:]):
            self.assertLessEqual((ax - bx) ** 2 + (ay - by) ** 2, 100 ** 2)
        self.assertEqual(circles[0][:2], (0, 0))
        self.assertEqual(circles[-1][:2], (1000, 777))

    def test_path_division_is_the_same_in_cpp(self):
        # C++ `/` truncates toward zero; Python `//` floors. The reviewer's path runs toward -x and -y.
        def truncating(points, half_width):
            circles, step = [], max(1, half_width // 2)
            for (ax, ay), (bx, by) in zip(points, points[1:]):
                dx, dy = bx - ax, by - ay
                count = max(1, int(Fraction(max(abs(dx), abs(dy)) + step - 1, step)))
                circles += [(ax + int(Fraction(dx * index, count)), ay + int(Fraction(dy * index, count)), half_width)
                            for index in range(count + 1)]
            return circles

        paths = ([(1000, 0), (-1000, -777)], [(0, 0), (-333, 1000), (500, -251), (-7, -7)], [(-1000, 0), (1000, 0)])
        for path in paths:
            self.assertEqual(P.path_exclusions(path, 120), truncating(path, 120), path)
            mirrored = P.path_exclusions([(-x, -y) for x, y in path], 120)
            self.assertEqual(mirrored, [(-x, -y, r) for x, y, r in P.path_exclusions(path, 120)], path)
        self.assertIn((942, -22, 120), P.path_exclusions(paths[0], 120))  # floor division gave (941, -23)

    def test_moss_is_scattered_as_cushions(self):
        rule = next(item for item in P.SCATTER if item.place == "pl_issoseki_wood"
                    and item.instance == "MI_IssosekiWood_MossClump01")
        low, high, radius = rule.cluster
        placed = P.scatter(rule, ("A", "B"), 11, (0, 0, 4000, 4000))
        self.assertEqual(placed, P.scatter(rule, ("A", "B"), 11, (0, 0, 4000, 4000)))
        # Group the sprigs by cushion: the plain scatter of the same rule gives the centres.
        centres = P.scatter(replace(rule, cluster=()), ("A",), 11, (0, 0, 4000, 4000))
        for _, x, y, _, _ in placed:
            self.assertTrue(any((x - cx) ** 2 + (y - cy) ** 2 <= radius * radius for _, cx, cy, _, _ in centres))
        per_cushion = len(placed) / len(centres)
        self.assertTrue(low * 0.7 <= per_cushion <= high, per_cushion)  # square offsets outside the circle drop
        self.assertTrue(all(rule.scale_milli[0] <= scale <= rule.scale_milli[1] for *_, scale in placed))

    @unittest.skipUnless((L.storage_root(ROOT) / "Local/ThirdPartyRaw/cc0").is_dir(), "Local/ not fetched")
    def test_moss_cushions_are_covered_by_sprigs(self):
        # moss_01's sprigs are 0.9-3.7 cm: alone at 0.6 per m^2 they would be invisible specks.
        plan = L.build_plan(ROOT, verify=False)
        mesh = next(item for item in plan.meshes if item.record.asset_id == "moss_01")
        gltf = json.loads((plan.storage / mesh.gltf).read_text(encoding="utf-8"))
        footprints = []
        for node in gltf["nodes"]:
            if "mesh" not in node:
                continue
            scale = node.get("scale", [1.0, 1.0, 1.0])
            accessors = [gltf["accessors"][primitive["attributes"]["POSITION"]]
                         for primitive in gltf["meshes"][node["mesh"]]["primitives"]]
            width = [100 * (max(a["max"][axis] for a in accessors) - min(a["min"][axis] for a in accessors))
                     * scale[axis] for axis in (0, 2)]  # glTF is Y-up: X and Z lie on the ground
            footprints.append(width[0] * width[1])
            self.assertLess(max(width), 4.0, node["name"])
        for rule in P.SCATTER:
            if rule.instance != "MI_IssosekiWood_MossClump01":
                continue
            low, high, radius = rule.cluster
            mean_scale = sum(rule.scale_milli) / 2000
            covered = (low + high) / 2 * 0.785 * sum(footprints) / len(footprints) * mean_scale ** 2
            self.assertGreater(covered / (3.14159 * radius * radius), 0.4, rule)

    def test_cluster_scatter_is_pinned(self):
        # A C++ port must reproduce this digest bit for bit, with a path running toward -x and -y.
        rule = P.ScatterRule("pl_issoseki_wood", "MI_IssosekiWood_MossClump01", 25.0, (1100, 1800), 20, (24, 48, 9))
        placed = P.scatter(rule, ("C", "D", "E"), 20260927, (-1000, -1000, 1000, 1000),
                           P.path_exclusions([(1000, 0), (-1000, -777)], 120))
        self.assertEqual(hashlib.sha256(repr(placed).encode()).hexdigest(), CLUSTER_DIGEST)

    def test_integer_algorithm_is_pinned(self):
        # A C++ port must reproduce this digest bit for bit.
        rule = P.ScatterRule("pl_issoseki_wood", "MI_IssosekiWood_MossClump01", 60.0, (900, 1800), 20)
        placed = P.scatter(rule, ("C", "D", "E"), 20260926, (-1000, -1000, 1000, 1000),
                           P.path_exclusions([(-1000, 0), (1000, 0)], 120))
        digest = hashlib.sha256(repr(placed).encode()).hexdigest()
        self.assertEqual(P.splitmix64(0), 0xE220A8397B1DCDAF)
        self.assertEqual(digest, PINNED_DIGEST, digest)


PINNED_DIGEST = "f76f09e69eabd0f93ea2cac9ee2593331eaf76615b862841e5bccc9662a26933"
CLUSTER_DIGEST = "631bf3713fbebf22d04c2aa6954d2da18e610ee22b907636c2011e04088f79c5"


if __name__ == "__main__":
    unittest.main(verbosity=2)
