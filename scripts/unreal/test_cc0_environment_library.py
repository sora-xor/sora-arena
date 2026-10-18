"""Host tests for the CC0 environment library's period-accuracy policy and naming rules.

Run: python3 scripts/unreal/test_cc0_environment_library.py
The policy, measured-rank and cook tests need only committed files; the tests
that build the full plan also need the fetched raw files in Local/ (they are
skipped, and say so, without them).
"""

from __future__ import annotations

from dataclasses import replace
import io
import json
from pathlib import Path
import re
import struct
import sys
import tempfile
import unittest
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cc0_environment_library as L  # noqa: E402
import cc0_environment_hlsl as H  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
HAS_LOCAL = (L.storage_root(ROOT) / "Local/ThirdPartyRaw/cc0").is_dir()
NO_LOCAL = "Local/ThirdPartyRaw/cc0 not fetched (scripts/assets/fetch_cc0.py)"


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

    def test_breakup_layers_stay_a_breakup(self):
        # patterned_clay_plaster is allowed only as "masked breakup"; the old tuning covered 99.98% of the wall.
        daub = next(item for item in L.PLACE_INSTANCES if item.name == "MI_Kakuredani_CharcoalHutDaub")
        self.check(daub)
        self.rejects(replace(daub, scalars={**daub.scalars, "LayerBCoverage": 0.9}), "covers 0.90")
        self.rejects(replace(daub, scalars={**daub.scalars, "TopFacingBias": 0.2}), "more than 0.3")

    def test_tatami_follows_mesh_uvs(self):
        tatami = next(item for item in L.PLACE_INSTANCES if item.name == "MI_EstateDay_Tatami")
        self.check(tatami)
        self.assertFalse(tatami.world_aligned)
        self.assertEqual(tatami.vectors["UVScale"], (1.0, 0.5, 0.0, 0.0))  # one 180 x 90 cm mat per UV square
        self.rejects(replace(tatami, world_aligned=True), "needs mesh UVs")

    def test_authoring_bases_are_not_places(self):
        # Rope001 is only the base of the authored shimenawa at the One-Claw Stone Wood.
        rope = self.records["Rope001"]
        self.assertTrue(any(use["place"] == "pl_issoseki_wood" for use in rope.data["game_use"]))
        self.assertNotIn("pl_issoseki_wood", L.places(rope))
        self.rejects(L._inst("MI_Test", "pl_issoseki_wood", "M_Env_Surface", ["Rope001"]),
                     "not planned for pl_issoseki_wood")
        self.check(L._inst("MI_Test", "pl_matoba", "M_Env_Surface", ["Rope001"]))

    def test_silk_is_anisotropic_shot_silk(self):
        silk = next(item for item in L.PLACE_INSTANCES if item.name == "MI_Kakuredani_JinmakuSilk")
        self.assertEqual(L.MASTERS[silk.master].family, "silk")
        self.assertGreater(silk.scalars["Anisotropy"], 0.0)
        self.assertGreater(silk.scalars["ShotAmount"], 0.0)
        self.assertIn("anisotropic", " ".join(use["use"] for use in self.records["crepe_satin"].data["game_use"]))
        self.rejects(replace(silk, scalars={**silk.scalars, "ClothAmount": 0.3}), "ClothAmount")

    def test_layers_and_parameters_fit_the_master(self):
        self.rejects(L._inst("MI_Test", "pl_kaido", "M_Env_HeightBlend2", ["ForestGround04"]), "layer count")
        self.rejects(L._inst("MI_Test", "pl_kakuredani", "M_Env_Cloth", ["Hessian230"], wet=L._wet(0.4, puddles=1.0)),
                     "PuddleResponse")
        self.rejects(L._inst("MI_Test", "pl_kakuredani", "M_Env_Cloth", ["Hessian230"], world_aligned=True),
                     "mesh UVs only")


def _png(width, height):
    header = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    chunk = b"IHDR" + header
    return (b"\x89PNG\r\n\x1a\n" + struct.pack(">I", len(header)) + chunk
            + struct.pack(">I", zlib.crc32(chunk)))


def _exr(x0, y0, x1, y1):
    def attribute(name, kind, value):
        return name + b"\0" + kind + b"\0" + struct.pack("<i", len(value)) + value
    return (b"\x76\x2f\x31\x01" + struct.pack("<I", 2)
            + attribute(b"compression", b"compression", b"\x03")
            + attribute(b"dataWindow", b"box2i", struct.pack("<4i", x0, y0, x1, y1)) + b"\0")


class SourceTest(unittest.TestCase):
    def test_image_size_reads_png_jpeg_and_exr_headers(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as scratch:
            png, jpeg, exr = (Path(scratch, name) for name in ("a.png", "b.jpg", "c.exr"))
            png.write_bytes(_png(2048, 2036))
            stream = io.BytesIO()
            Image.new("RGB", (2048, 2085)).save(stream, format="JPEG")
            jpeg.write_bytes(stream.getvalue())
            exr.write_bytes(_exr(0, 0, 4095, 2047))
            self.assertEqual(L.image_size(png), (2048, 2036))
            self.assertEqual(L.image_size(jpeg), (2048, 2085))
            self.assertEqual(L.image_size(exr), (4096, 2048))

    @unittest.skipUnless(HAS_LOCAL, NO_LOCAL)
    def test_power_of_two_mode_comes_from_the_source(self):
        # The six cloth maps a few pixels off a power of two are stretched; whatever size an
        # editor reports after building them, the expectation is fixed by the source bytes.
        plan = L.build_plan(ROOT, verify=False)
        stretched = set()
        for texture_set in plan.sets.values():
            if not texture_set.imported:
                continue
            for role, channel in texture_set.channels.items():
                if channel.root == "packed" and not (ROOT / L.PACKED_ROOT / channel.file).is_file():
                    continue
                size = L.image_size(plan.source_path(channel))
                if L.texture_expectations(channel, texture_set, size)["power_of_two_mode"] != "NONE":
                    stretched.add((texture_set.name, role))
        self.assertEqual(stretched, {(name, role) for name in ("Hessian230", "CrepeSatin")
                                     for role in ("BaseColor", "Normal", "ARM")})

    def test_material_compilation_needs_a_renderer(self):
        self.assertFalse(L.can_ever_render('"/x/Proj.uproject" -ExecutePythonScript=a.py -unattended -nullrhi'))
        self.assertFalse(L.can_ever_render("Proj -NullRHI"))
        self.assertTrue(L.can_ever_render("Proj -RenderOffScreen -unattended"))

    def test_the_library_is_never_cooked(self):
        # /Game/Generated is always cooked; only the never-cook entry keeps the library out.
        config = (ROOT / L.COOK_CONFIG).read_text(encoding="utf-8")
        always = re.findall(r'^\+DirectoriesToAlwaysCook=\(Path="([^"]+)"\)', config, re.MULTILINE)
        self.assertTrue(any(L.PACKAGE_ROOT.startswith(path + "/") for path in always))
        self.assertIn(L.PACKAGE_ROOT, L.never_cook_directories(ROOT))
        lookdev = (ROOT / "scripts/unreal/render_cc0_environment_lookdev.py").read_text(encoding="utf-8")
        self.assertIn('LEVEL = f"{library.PACKAGE_ROOT}/LookDev/L_CC0LookDev"', lookdev)


def _distribution(entry, bins):
    return [((entry["first_bin"] + index + 0.5) / bins, count / sum(entry["counts"]))
            for index, count in enumerate(entry["counts"]) if count]


def _rank_histogram(entry, bins, knots, steps=400):
    """Probability of each rank bucket (of ``steps``) when the HLSL ranks this measured distribution."""
    buckets = [0.0] * steps
    for value, weight in _distribution(entry, bins):
        buckets[min(int(L.value_rank(value, knots) * steps), steps - 1)] += weight
    return [((index + 0.5) / steps, weight) for index, weight in enumerate(buckets) if weight]


class MeasuredRankTest(unittest.TestCase):
    """The height blend and puddles against the AO and macro distributions measured from the real maps."""

    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads((ROOT / L.AO_RANKS).read_text(encoding="utf-8"))
        cls.bins = cls.doc["bins"]
        cls.instances = {item.name: item for item in L.PLACE_INSTANCES + L.EVALUATION_INSTANCES}

    def test_the_mirrored_formulas_are_the_hlsl(self):
        # The coverage and puddle tests below evaluate these exact lines on the measured data.
        self.assertIn("float h = lerp(RankA, 1.0 - RankA, HeightFromCrevices);", H.HLSL_BLEND)
        self.assertIn("float alpha = saturate((h - (1.0 - coverage)) * Contrast + 0.5);", H.HLSL_BLEND)
        self.assertIn(f"float lowness = {H.PUDDLE_MACRO!r} * (1.0 - macroRank) + (1.0 - {H.PUDDLE_MACRO!r})"
                      " * (1.0 - AORank);", H.HLSL_FINISH)
        self.assertIn(f"float puddle = saturate((lowness - 1.0 + {H.PUDDLE_REACH!r} * PuddleAmount * PuddleResponse)"
                      f" * {H.PUDDLE_SHARPNESS!r}) * flatness;", H.HLSL_FINISH)

    def test_knots_are_the_measured_quantiles(self):
        self.assertEqual(self.doc["ranks"], list(H.RANKS))
        self.assertEqual(self.doc["tails"], list(L.RANK_TAILS))
        for name, entry in list(self.doc["sets"].items()) + [("macro", self.doc["macro"])]:
            self.assertEqual(entry["knots"], L.histogram_knots(entry["first_bin"], entry["counts"], self.bins), name)
        self.assertEqual(list(H.MACRO_KNOTS), self.doc["macro"]["knots"])
        # Every ranked instance's layer A is measured.
        ranked = {item.layers[0] for item in self.instances.values() if L.needs_ao_ranks(item)}
        self.assertEqual(ranked, set(self.doc["sets"]))

    def test_layer_b_covers_the_share_each_instance_asks_for(self):
        # The old absolute threshold showed no Plaster007 on shikkui, no moss in the roji joints
        # or on the thatch, and patterned plaster over 99.98% of the daub wall.
        for item in self.instances.values():
            if L.MASTERS[item.master].family != "heightblend":
                continue
            entry = self.doc["sets"][item.layers[0]]
            ranks = _rank_histogram(entry, self.bins, entry["knots"])
            crevices, contrast = item.scalars["HeightFromCrevices"], item.scalars["BlendContrast"]
            for nz in (0.0, 1.0):
                coverage = min(item.scalars["LayerBCoverage"] + item.scalars.get("TopFacingBias", 0.0) * nz, 1.0)
                covered = sum(weight for rank, weight in ranks
                              if (crevices * (1 - rank) + (1 - crevices) * rank - (1 - coverage)) * contrast > 0)
                self.assertAlmostEqual(covered, coverage, delta=0.03, msg=f"{item.name} at Nz {nz}")

    def puddle_share(self, entry, amount):
        """Share of flat ground whose puddle mask exceeds 0.5 (HLSL_FINISH at Nz 1)."""
        ao = _rank_histogram(entry, self.bins, entry["knots"], 200)
        macro = _rank_histogram(self.doc["macro"], self.bins, H.MACRO_KNOTS, 200)
        share = 0.0
        for ao_rank, ao_weight in ao:
            for macro_rank, macro_weight in macro:
                lowness = H.PUDDLE_MACRO * (1 - macro_rank) + (1 - H.PUDDLE_MACRO) * (1 - ao_rank)
                if (lowness - 1 + H.PUDDLE_REACH * amount) * H.PUDDLE_SHARPNESS > 0.5:
                    share += ao_weight * macro_weight
        return share

    def test_puddles_grow_from_none_and_never_flood(self):
        # The old mask put a road-wide mirror on the packed-earth road from PuddleAmount 0.7.
        road = self.doc["sets"]["ForestGround05"]
        shares = [self.puddle_share(road, amount) for amount in (0.0, 0.3, 0.5, 0.7, 0.8, 1.0)]
        self.assertEqual(shares[0], 0.0)
        self.assertEqual(shares, sorted(shares))
        self.assertLess(shares[2], 0.1)                     # a passing shower: a few puddles
        self.assertTrue(0.1 <= shares[3] <= 0.2, shares)     # the look-dev wet state
        self.assertTrue(0.15 <= shares[4] <= 0.3, shares)    # ch03 dusk rain (PuddleAmount 0.8)
        self.assertLessEqual(shares[5], 0.4)
        for item in self.instances.values():
            response = item.scalars.get("PuddleResponse", 0.0)
            if response:
                self.assertLessEqual(self.puddle_share(self.doc["sets"][item.layers[0]], response), 0.4, item.name)

    @unittest.skipUnless(HAS_LOCAL, NO_LOCAL)
    def test_instances_bind_their_measured_knots(self):
        plan = L.build_plan(ROOT, verify=False)
        for item in plan.instances:
            vectors = L.resolved_vectors(plan, item)
            if L.needs_ao_ranks(item):
                knots = self.doc["sets"][item.layers[0]]["knots"]
                self.assertEqual(list(vectors["AOKnotsLo"] + vectors["AOKnotsHi"]), knots, item.name)
            else:
                self.assertNotIn("AOKnotsLo", vectors, item.name)


class LedgerTest(unittest.TestCase):
    @unittest.skipUnless(HAS_LOCAL, NO_LOCAL)
    def test_used_by_lists_every_package_built_from_a_record(self):
        sys.path.insert(0, str(ROOT / "scripts/unreal"))
        import record_cc0_ledger_uses as uses_tool
        plan = L.build_plan(ROOT, verify=False)
        uses = L.ledger_uses(plan)
        targets = uses_tool.ledger_targets(ROOT)
        self.assertEqual(set(uses) - set(targets), set(uses_tool.UNRECORDED))
        records = {}
        for relative in {relative for relative, _ in targets.values()}:
            for record in json.loads((ROOT / relative).read_text(encoding="utf-8"))["records"]:
                records[(relative, record["asset_id"])] = record
        for key, (relative, asset_id) in targets.items():
            library_uses = [path for path in records[(relative, asset_id)]["used_by"]
                            if path.startswith(L.PACKAGE_ROOT + "/")]
            self.assertEqual(library_uses, uses.get(key, []), f"{key}: run scripts/unreal/record_cc0_ledger_uses.py")

    def test_paper_0017_has_a_schema_2_record_of_the_imported_maps(self):
        ledger = json.loads((ROOT / "Content/SourceArt/Environment/ShojiPaperArtReview/manifest.ledger.json")
                            .read_text(encoding="utf-8"))
        self.assertEqual(ledger["schema_version"], 2)
        (record,) = ledger["records"]
        self.assertEqual((record["tier"], record["license"]), ("PUB-CC0", "CC0-1.0"))
        recorded = {entry["path"]: entry["sha256"] for entry in record["files"]}
        paper = L._project_sets(ROOT, [])["Paper0017"]
        for channel in paper.channels.values():
            if channel.root == "project":
                self.assertEqual(recorded.get(channel.file), channel.sha256, channel.file)
        self.assertTrue(record["used_by"])


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

    @unittest.skipUnless((L.storage_root(ROOT) / "Local/ThirdPartyRaw/cc0").is_dir(),
                         "Local/ThirdPartyRaw/cc0 not fetched (scripts/assets/fetch_cc0.py)")
    def test_master_graph_digest_tracks_graph_inputs(self):
        plan = L.build_plan(ROOT, verify=False)
        defaults = L.master_defaults(plan)
        self.assertEqual(set(defaults), set(L.MASTERS))
        for name, master in L.MASTERS.items():
            self.assertEqual(set(defaults[name]), set(L.TEXTURE_PARAMS[master.family]), name)
        digests = {name: L.master_graph_digest(plan, name, defaults[name]) for name in L.MASTERS}
        self.assertEqual(len(set(digests.values())), len(L.MASTERS))
        name = "M_Env_Surface"
        self.assertEqual(L.master_graph_digest(plan, name, dict(defaults[name])), digests[name])
        moved = dict(defaults[name], Normal="/Game/Elsewhere/T_Other.T_Other")
        self.assertNotEqual(L.master_graph_digest(plan, name, moved), digests[name])



class CustomHlslTest(unittest.TestCase):
    def test_translator_wrapper(self):
        # FHLSLMaterialTranslator::CustomExpression: LWC inputs arrive demoted plus raw,
        # extra outputs are inout, and the node code is the body.
        self.assertEqual(
            H.translator_function(H.CUSTOM["project"], 0).splitlines()[0],
            "MaterialFloat2 CustomExpression0(FMaterialPixelParameters Parameters,float3 P, FWSVector3 LWCP,"
            "MaterialFloat3 N)")
        header = H.translator_function(H.CUSTOM["blend"], 3).splitlines()[0]
        self.assertTrue(header.endswith(", inout MaterialFloat3 NormalOut, inout MaterialFloat3 ArmOut)"), header)
        self.assertIn("return", H.translator_function(H.Custom("x", "A * 2.0", "float", (("A", "float"),)), 1))

    def test_every_node_names_its_pins_once(self):
        for key, custom in H.CUSTOM.items():
            names = [name for name, _ in custom.inputs + custom.outputs]
            self.assertEqual(len(names), len(set(names)), key)
            self.assertTrue(all(kind in ("float", "float3", "float4", "lwc3") for _, kind in custom.inputs), key)

    def test_rank_code_matches_its_python_mirror(self):
        # The HLSL sums each segment's share of rank; the host mirror must be the same curve.
        self.assertIn("[unroll] for (int rankIndex = 0; rankIndex < 7; ++rankIndex)", H.HLSL_RANK)
        identity = list(H.RANKS)
        for value in (0.0, 0.03, 0.2, 0.5, 0.9, 1.0):
            self.assertAlmostEqual(L.value_rank(value, identity), value)
        knots = [0.4, 0.5, 0.55, 0.6, 0.7, 0.8, 0.9, 0.95]
        self.assertEqual((L.value_rank(0.1, knots), L.value_rank(0.99, knots)), (0.0, 1.0))
        self.assertAlmostEqual(L.value_rank(0.65, knots), 0.5)
        literal = ", ".join(repr(value) for value in H.MACRO_KNOTS)
        self.assertIn(literal, H.HLSL_FINISH)

    def test_graph_digest_covers_the_hlsl(self):
        self.assertIn("scripts/unreal/cc0_environment_hlsl.py", L.GRAPH_SOURCES)


if __name__ == "__main__":
    unittest.main(verbosity=2)
