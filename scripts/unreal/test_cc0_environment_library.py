"""Host tests for the CC0 environment library's period-accuracy policy and naming rules.

Run: python3 scripts/unreal/test_cc0_environment_library.py
The policy tests need only the committed ledgers; the full-plan test also needs
the fetched raw files in Local/ (it is skipped, and says so, without them).
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cc0_environment_library as L  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def ledger_sets():
    records = L.load_ledgers(ROOT)
    sets = {L.camel(record.asset_id): L._record_set(record, [], False)
            for record in records.values() if L.is_environment(record) and record.data["kind"] != "hdri"}
    return records, sets


class PolicyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records, cls.sets = ledger_sets()

    def check(self, instance):
        L.check_instance(instance, self.sets, self.records)

    def rejects(self, instance, message):
        with self.assertRaisesRegex(RuntimeError, message):
            self.check(instance)

    def test_every_place_instance_passes(self):
        sets = dict(self.sets)
        for name, (asset_id, prefix, channels, tile) in L.PALETTE_SETS.items():
            sets[name] = L._palette_set(name, asset_id, prefix, channels, tile)
        sets.update(L._project_sets(ROOT, []))
        for instance in L.PLACE_INSTANCES:
            L.check_instance(instance, sets, self.records)

    def test_high_risk_surfaces_never_reach_a_place(self):
        for layers, place in ((["StackedStoneWall"], "lane_kit"), (["MuddyTracks"], "pl_umaya"),
                              (["GraniteWall"], "pl_ishibashi"), (["JapaneseStoneWall"], "pl_ishibashi")):
            master = "M_Env_Surface_VT" if self.sets[layers[0]].virtual else "M_Env_Surface"
            self.rejects(L._inst("MI_Test", place, master, layers), "period-inaccurate")
        self.rejects(L._inst("MI_Test", "pl_estate_day", "M_Env_Surface", ["RoofingTiles015A"]), "period-inaccurate")

    def test_evaluation_instances_may_hold_flagged_surfaces(self):
        self.check(L._inst("MI_Eval_Test", "evaluation", "M_Env_Surface", ["RoofingTiles015A"]))
        self.check(L._inst("MI_Eval_Test", "evaluation", "M_Env_Surface_VT", ["StackedStoneWall"]))

    def test_medium_surfaces_only_in_their_flagged_role(self):
        daub = L._inst("MI_Test", "pl_kakuredani", "M_Env_HeightBlend2", ["PatternedClayPlaster", "Moss004"],
                       roles={"patterned_clay_plaster": "layer_b"})
        self.rejects(daub, "breakup layer B")
        self.rejects(replace(daub, layers=("Moss004", "PatternedClayPlaster"), roles={}), "no allowed role")
        self.check(replace(daub, layers=("Moss004", "PatternedClayPlaster")))
        self.rejects(L._inst("MI_Test", "pl_issoseki_wood", "M_Env_Surface", ["LacqueredCherryWood"]),
                     "not planned|no allowed role")
        self.rejects(L._inst("MI_Test", "pl_kaido", "M_Env_Surface", ["MossyStoneWall"]), "no allowed role")

    def test_roof_planks_keep_off_the_stable_and_are_regraded(self):
        roof = L._inst("MI_Test", "pl_dojo_smithy", "M_Env_Surface", ["RoofPlanks"],
                       grade=L._grade(rough=(0.62, 0.9)), roles={"roof_planks": "plank_roof_regraded"})
        self.check(roof)
        self.rejects(replace(roof, scalars={**roof.scalars, "RoughnessMin": 0.2}), "re-graded roughness")
        self.rejects(replace(roof, place="pl_umaya"), "not planned|stable")

    def test_trident_maple_is_generic_momiji_bark_only(self):
        bark = L._inst("MI_IssosekiWood_MomijiBark", "pl_issoseki_wood", "M_Env_Surface", ["TridentMapleBark"],
                       roles={"trident_maple_bark": "maple_bark"})
        self.check(bark)
        self.rejects(replace(bark, name="MI_IssosekiWood_TokaedeBark"), "generic momiji")

    def test_places_follow_the_ledger_game_use(self):
        self.rejects(L._inst("MI_Test", "pl_kaido", "M_Env_Surface_VT", ["HinokiPlanks"]), "not planned for pl_kaido")
        self.rejects(L._inst("MI_Test", "pl_umaya", "M_Env_Surface", ["Rope001"]), "not planned for pl_umaya")

    def test_roles_cannot_be_claimed_for_other_records(self):
        self.rejects(L._inst("MI_Test", "pl_matoba", "M_Env_Surface", ["Rope001"], roles={"Rope001": "layer_b"}),
                     "role claimed")

    def test_virtual_texture_state_matches_the_master(self):
        self.rejects(L._inst("MI_Test", "pl_tsumagizaka_dojo", "M_Env_Surface", ["HinokiPlanks"]), "virtual-texture")
        self.rejects(L._inst("MI_Test", "pl_kaido", "M_Env_Surface_VT", ["ForestGround04"]), "virtual-texture")
        self.rejects(L._inst("MI_Test", "pl_issoseki_wood", "M_Env_HeightBlend2", ["ForestGround06", "JapaneseCedarBark"]),
                     "virtual-texture")

    def test_layers_and_parameters_fit_the_master(self):
        self.rejects(L._inst("MI_Test", "pl_kaido", "M_Env_HeightBlend2", ["ForestGround04"]), "layer count")
        self.rejects(L._inst("MI_Test", "pl_kakuredani", "M_Env_Cloth", ["Hessian230"], wet=L._wet(0.4, puddles=1.0)),
                     "PuddleResponse")
        self.rejects(L._inst("MI_Test", "pl_kakuredani", "M_Env_Cloth", ["Hessian230"], world_aligned=True),
                     "mesh UVs only")


class NamingTest(unittest.TestCase):
    def test_places(self):
        record = L.Record("polyhaven", {"game_use": [
            {"place": "ch01 lane kit (pl_umaya to pl_matoba)"}, {"place": "later: pl_shimomura"},
            {"place": "pl_tsumagizaka_dojo / pl_issoseki_wood"}, {"place": "pl_tsumagizaka_dojo yard"},
            {"place": "characters"}]})
        self.assertEqual(L.places(record), {"lane_kit", "pl_shimomura", "pl_tsumagizaka_dojo",
                                            "pl_issoseki_wood", "characters"})
        self.assertFalse(L.is_environment(L.Record("ambientcg", {"game_use": [{"place": "weapons"}]})))

    def test_mesh_asset_names(self):
        self.assertEqual(L.mesh_asset_name("rock_moss_set_01", "rock_moss_set_01_rock01"), "SM_RockMossSet01_Rock01")
        self.assertEqual(L.mesh_asset_name("moss_01", "moss_01_tall_a_LOD0"), "SM_Moss01_TallA")
        self.assertEqual(L.mesh_asset_name("boulder_01", "boulder_01"), "SM_Boulder01")

    def test_texture_expectations(self):
        records, sets = ledger_sets()
        hinoki, hessian = sets["HinokiPlanks"], sets["Hessian230"]
        color = L.texture_expectations(hinoki.channels["BaseColor"], hinoki, (4096, 4096))
        self.assertEqual((color["srgb"], color["compression_settings"], color["virtual_texture_streaming"]),
                         (True, "TC_BC7", True))
        normal = L.texture_expectations(hessian.channels["Normal"], hessian, (2048, 2036))
        self.assertEqual((normal["srgb"], normal["compression_settings"], normal["power_of_two_mode"]),
                         (False, "TC_NORMALMAP", "STRETCH_TO_POWER_OF_TWO"))
        self.assertTrue(sets["Moss01"].channels["Normal"].flip_green)  # only an OpenGL glTF normal
        self.assertEqual(hessian.tile_cm, (26.88, 26.72))
        self.assertEqual(sets["JapaneseCedarBark"].tile_cm, (100.0, 200.0))

    def test_storage_root_of_a_worktree(self):
        with tempfile.TemporaryDirectory() as scratch:
            main = Path(scratch, "main")
            (main / ".git/worktrees/lane").mkdir(parents=True)
            (main / ".git/worktrees/lane/commondir").write_text("../..\n")
            tree = Path(scratch, "lane")
            tree.mkdir()
            (tree / ".git").write_text(f"gitdir: {main}/.git/worktrees/lane\n")
            self.assertEqual(L.storage_root(tree), main.resolve())
            self.assertEqual(L.storage_root(main), main)


class PlanTest(unittest.TestCase):
    @unittest.skipUnless((L.storage_root(ROOT) / "Local/ThirdPartyRaw/cc0").is_dir(),
                         "Local/ThirdPartyRaw/cc0 not fetched (scripts/assets/fetch_cc0.py)")
    def test_full_plan(self):
        plan = L.build_plan(ROOT, verify=False)
        places = [instance for instance in plan.instances if not instance.evaluation]
        self.assertEqual(len(places), len(L.PLACE_INSTANCES))
        for instance in places:
            for layer in plan.layers_of(instance):
                self.assertFalse(layer.evaluation, instance.name)
                if layer.origin.startswith(("polyhaven:", "ambientcg:")):
                    self.assertNotEqual(plan.records[layer.origin.split(":", 1)[1]].risk, "high")
        high = {record.asset_id for record in plan.records.values()
                if record.risk == "high" and L.is_environment(record)}
        evaluated = {plan.sets[name].origin.split(":", 1)[1] for instance in plan.instances
                     if instance.evaluation for name in instance.layers}
        self.assertTrue(high <= evaluated, sorted(high - evaluated))
        self.assertEqual(sum(cls == "StaticMesh" for cls in plan.expected.values()),
                         sum(len(mesh.nodes) for mesh in plan.meshes))


if __name__ == "__main__":
    unittest.main(verbosity=2)
