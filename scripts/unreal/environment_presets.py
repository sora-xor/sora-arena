"""Lighting presets, CC0 surface assignments and seeded scatter rules for the environment lane.

Plain data shared by the host tests and, when the world builder adopts it,
by an exporter to ``Content/Data``. Nothing in the game reads it yet.

* ``LIGHTING``: one preset per story-bible lighting state (§16 "Lighting and
  weather by chapter", §15.2 per-location direction), with the chapters and
  arenas that use it. Colour temperatures, weather and the Mac fallback caps
  come from the bible. Only ``estate_day`` is ``shipped``: it holds the values
  ``SoraWorldBuilderLighting.cpp`` uses today, whose 25 lux key a packaged
  fixed-camera A/B chose. Every other intensity is an unverified starting value
  to be tuned against fixed-camera captures.
* ``SURFACES``: for each story-bible place, the CC0 library instance for each
  surface role. A place may use an instance only when every ledger record the
  instance binds lists that place in its ``game_use``, the same rule
  ``cc0_environment_library`` applies to the instance's own place.
* ``SCATTER``: per-place rules for the scanned CC0 meshes, and ``scatter()``, a
  seeded placement in integer centimetres, tenths of a degree and thousandths
  of scale. Past the grid cell size (the rounded square root of the rule's
  density, fixed per rule) it uses only 64-bit integer arithmetic (SplitMix64
  hashes and squared distances), so a C++ port reproduces it bit for bit.

HDRIs are lighting-only by their ledger flags: the visible sky stays
SkyAtmosphere and clouds. The look-development HDRIs are never game presets.
"""

from __future__ import annotations

from dataclasses import dataclass

import cc0_environment_library as library

ESTATE_OVERCAST_HDRI = "/Game/Generated/Environment/Textures/T_NyaagyuOvercast.T_NyaagyuOvercast"
MAC_MAX_SHADOWED_LIGHTS = 8  # story bible §15.1 platforms: Mac shadow-casting dynamic lights per view


def cc0_hdri(name: str) -> str:
    return f"{library.HDRI}/{name}.{name}"


@dataclass(frozen=True)
class Lighting:
    id: str
    chapters: tuple          # "ch01".."ch08" whose §16 row this preset realises
    places: tuple            # story-bible place ids lit by it
    key: str                 # "sun" | "moon" | "fire" | "none" (the dominant directional or local key)
    key_kelvin: float | None
    key_pitch_deg: float     # Unreal pitch of the directional key; negative points down
    key_yaw_deg: float
    key_lux: float           # in the project's established scale (estate day key = 25)
    sky_hdri: str | None     # lighting-only cubemap; None: real-time capture of SkyAtmosphere
    sky_intensity: float
    exposure_bias: float     # histogram auto-exposure compensation, EV
    fog_density: float
    fog_kelvin: float        # colour temperature of the fog inscattering
    volumetric_fog: bool     # Windows only; the Mac falls back to height fog (§16)
    wetness: float           # MPC_EnvironmentWeather.Wetness
    puddles: float           # MPC_EnvironmentWeather.PuddleAmount
    rain: bool
    lantern_kelvin: float | None
    lantern_intensity: float  # MPC_EnvironmentWeather.LanternIntensity
    mac_fallback: str        # §16 "Mac fallback" column
    shipped: bool = False    # the values the world builder uses today


LIGHTING = (
    # ch01 overcast day at the estate (Arena 0): the values SoraWorldBuilderLighting.cpp
    # uses today (25 lux key from a packaged A/B; sky 0.65, bias -0.45 EV, fog 0.0045).
    Lighting("estate_day", ("ch01",), ("pl_estate_day", "pl_tsumagizaka_dojo", "pl_umaya", "pl_matoba",
                                       "pl_dojo_smithy"),
             "sun", 5200.0, -28.0, -35.0, 25.0, ESTATE_OVERCAST_HDRI, 0.65, -0.45, 0.0045, 6500.0, False,
             0.0, 0.0, False, None, 1.0, "Software Lumen; limit dust particles", shipped=True),
    Lighting("wood_dawn_mist", ("ch01",), ("pl_issoseki_wood", "pl_tsumagizaka_dojo"),
             "sun", 5200.0, -8.0, -60.0, 12.0, cc0_hdri("HDRI_KloofendalMistyMorning"), 0.7, -0.3, 0.012, 6500.0,
             True, 0.35, 0.0, False, None, 1.0, "Software Lumen; morning mist as height fog"),
    Lighting("estate_golden_dusk", ("ch01",), ("pl_estate_day",),
             "sun", 3800.0, -9.0, 60.0, 14.0, cc0_hdri("HDRI_QwantaniDusk2"), 0.6, -0.2, 0.005, 5200.0, False,
             0.0, 0.0, False, 2000.0, 0.6, "Software Lumen"),
    Lighting("estate_night_fire", ("ch02",), ("pl_estate_night", "pl_bugugura", "pl_kaido", "pl_ishibashi",
                                              "pl_kakuredani"),
             "moon", 4100.0, -40.0, 120.0, 0.6, cc0_hdri("HDRI_QwantaniNight"), 0.35, 0.4, 0.006, 8500.0, True,
             0.1, 0.0, False, 2000.0, 1.0, "Fewer shadowed fire lights; emissive smoke cards"),
    Lighting("lantern_ward_dusk_rain", ("ch03",), ("pl_lantern_ward_rain", "pl_horiwari", "pl_ura_nagaya",
                                                   "pl_kido", "pl_kosatsuba", "pl_chochin_gashi"),
             "none", None, -6.0, -35.0, 0.0, None, 0.7, 0.3, 0.008, 9000.0, True,
             1.0, 0.8, True, 1900.0, 1.0, "At most 8 shadowed lanterns per view; the rest emissive"),
    Lighting("village_hazy_day", ("ch04",), ("pl_shimomura", "pl_shoya_yashiki", "pl_otameike", "pl_tanada",
                                             "pl_suisha_goya", "pl_gogura"),
             "sun", 5600.0, -40.0, -20.0, 25.0, None, 0.75, -0.3, 0.007, 6500.0, True,
             0.0, 0.0, False, None, 1.0, "Reduce foliage density; card barley LODs"),
    Lighting("village_golden_dusk", ("ch04",), ("pl_shimomura", "pl_tanada"),
             "sun", 3800.0, -8.0, 70.0, 12.0, None, 0.6, -0.2, 0.006, 5200.0, True,
             0.2, 0.1, False, 2000.0, 0.6, "Reduce foliage density; card barley LODs"),
    Lighting("foundry_furnace_night", ("ch05",), ("pl_silk_foundry", "pl_itotoriba", "pl_hataba", "pl_takadono",
                                                  "pl_okaji", "pl_aratamejo", "pl_sumigoya", "pl_toritategura",
                                                  "pl_imonoba", "pl_kanna_nagashi"),
             "fire", 1600.0, -35.0, 40.0, 0.5, None, 0.3, 0.3, 0.005, 3000.0, True,
             0.0, 0.0, False, 2000.0, 1.0, "Cap spark counts; baked emissive furnace"),
    Lighting("citadel_new_moon", ("ch06",), ("pl_citadel_moat", "pl_ishigaki", "pl_relay_room",
                                            "pl_ledger_corridors", "pl_uguisu_hall", "pl_archive", "pl_press_hall",
                                            "pl_vault_core"),
             "none", None, -45.0, 0.0, 0.0, None, 0.15, 0.8, 0.02, 8000.0, True,
             0.3, 0.0, False, 1800.0, 0.3, "Fog as height fog only"),
    Lighting("flagship_typhoon", ("ch07",), ("pl_anchor_bastion", "pl_hull_ridge", "pl_kayanohara"),
             "moon", 4100.0, -30.0, 150.0, 0.8, None, 0.3, 0.4, 0.01, 7000.0, True,
             1.0, 0.5, True, None, 1.0, "Simplify volumetric clouds; skybox cloud sea"),
    Lighting("causeway_clear_dawn", ("ch08",), ("pl_causeway", "pl_outer_bailey", "pl_otemon", "pl_higashi_torii"),
             "sun", 3500.0, -7.0, -80.0, 18.0, None, 0.6, -0.2, 0.004, 6000.0, True,
             0.25, 0.1, False, None, 1.0, "Lantern clusters as emissive cards"),
    Lighting("festival_night", ("ch08",), ("pl_lantern_ward_festival",),
             "moon", 4100.0, -50.0, 100.0, 0.4, None, 0.25, 0.4, 0.003, 8000.0, False,
             0.0, 0.0, False, 1900.0, 1.0, "Lantern clusters as emissive cards"),
)

# Arena id -> preset used by practice and multiplayer (story bible §14 arena reuse).
ARENAS = {0: "estate_day", 1: "lantern_ward_dusk_rain", 2: "foundry_furnace_night", 3: "citadel_new_moon"}

# Surface role -> CC0 place instance(s), per story-bible place. Variants of one role are listed together.
SURFACES = {
    "pl_tsumagizaka_dojo": {"floor": ("MI_TsumagizakaDojo_HinokiFloor",),
                            "wall_board": ("MI_TsumagizakaDojo_SugiHameita",),
                            "tree_bark": ("MI_TsumagizakaDojo_KeyakiBark",)},
    "pl_estate_day": {"floor": ("MI_EstateDay_EngawaHinoki",), "tatami": ("MI_EstateDay_Tatami",),
                      "wall_earth": ("MI_EstateDay_Tsuchikabe",), "wall_plaster": ("MI_EstateDay_Shikkui",),
                      "roof": ("MI_EstateDay_IbushiKawara",), "path": ("MI_EstateDay_RojiStonePath",),
                      "tree_bark": ("MI_EstateDay_MatsuBark",), "rope": ("MI_Umaya_HempRope",)},
    # The ledger lists clay plaster and tatami for the night estate, but not Plaster007 or
    # Moss002: shikkui and the roji path need a ledger game_use entry before they reach it.
    "pl_estate_night": {"wall_earth": ("MI_EstateDay_Tsuchikabe",), "tatami": ("MI_EstateDay_Tatami",),
                        "roof": ("MI_EstateDay_IbushiKawara",), "straw": ("MI_Umaya_WaraStraw",),
                        "lantern_paper": ("MI_EstateNight_AndonPaper",)},
    "pl_umaya": {"wall_board": ("MI_Umaya_SugiBoardWall",), "straw": ("MI_Umaya_WaraStraw",),
                 "rope": ("MI_Umaya_HempRope",), "leather": ("MI_Umaya_TackLeather",),
                 "cloth": ("MI_Umaya_AsaHorseBlanket", "MI_Umaya_ShitaguraPad")},
    "pl_matoba": {"ground": ("MI_Kaido_GravelPitch",), "straw": ("MI_Matoba_MakiwaraStraw",),
                  "rope": ("MI_Matoba_HempLashing",)},
    "pl_dojo_smithy": {"roof": ("MI_DojoSmithy_ItabukiRoof",), "wall_board": ("MI_Umaya_SugiBoardWall",),
                       "wall_earth": ("MI_EstateDay_Tsuchikabe",), "basket": ("MI_DojoSmithy_TakeKago",)},
    "pl_bugugura": {"ground": ("MI_Kaido_PackedEarthRoad",), "wall_board": ("MI_Umaya_SugiBoardWall",),
                    "fence": ("MI_Bugugura_TakegakiPanel",), "leather": ("MI_Bugugura_ArmorChestLeather",)},
    "pl_kaido": {"ground": ("MI_Kaido_PackedEarthRoad",), "path": ("MI_Kaido_GravelPitch",),
                 "bank": ("MI_Kaido_MossBank",),
                 "tree_bark": ("MI_IssosekiWood_SugiBark", "MI_EstateDay_MatsuBark", "MI_Kaido_KusunokiBark")},
    "pl_ishibashi": {"stream_bed": ("MI_Ishibashi_StreamBed",), "tree_bark": ("MI_IssosekiWood_SugiBark",)},
    "pl_kakuredani": {"ground": ("MI_Kakuredani_ValleyFloor",), "stream_bed": ("MI_Ishibashi_StreamBed",),
                      "wall_earth": ("MI_Kakuredani_CharcoalHutDaub",),
                      "roof": ("MI_Kakuredani_KayabukiThatchField", "MI_Kakuredani_MossyThatch"),
                      "cloth": ("MI_Kakuredani_AsaSacking", "MI_Kakuredani_JinmakuSilk",
                                "MI_Kakuredani_PackWrapCloth")},
    "pl_issoseki_wood": {"ground": ("MI_IssosekiWood_MossForestFloor",), "stream_bed": ("MI_Ishibashi_StreamBed",),
                         "tree_bark": ("MI_IssosekiWood_SugiBark", "MI_IssosekiWood_YamazakuraBark",
                                       "MI_IssosekiWood_MomijiBark"),
                         "rope": ("MI_Matoba_HempLashing",)},
    "pl_lantern_ward_rain": {"lantern_paper": ("MI_LanternWardRain_ChochinPaper",)},
    "lane_kit": {"ground": ("MI_Kaido_PackedEarthRoad",), "fence": ("MI_LaneKit_AjiroTakegaki",)},
}


@dataclass(frozen=True)
class ScatterRule:
    place: str
    instance: str            # CC0 library mesh instance; its meshes are the variants
    per_100_m2: float        # mean count per 100 m^2 before exclusions
    scale_milli: tuple       # (min, max) uniform scale in thousandths
    clearance_cm: int        # added to every exclusion radius for this rule


# Densities follow §15.2: a moss-and-fern cedar floor in the wood, a rocky stream at the
# bridge, a cut-over valley at the charcoal burners' huts, rocks and roots along the road.
SCATTER = (
    ScatterRule("pl_issoseki_wood", "MI_IssosekiWood_MossClump01", 60.0, (900, 1800), 20),
    ScatterRule("pl_issoseki_wood", "MI_IssosekiWood_MossRockSet01", 2.0, (700, 1300), 80),
    ScatterRule("pl_issoseki_wood", "MI_IssosekiWood_RootCluster01", 0.4, (800, 1200), 120),
    ScatterRule("pl_issoseki_wood", "MI_IssosekiWood_TreeStump01", 0.3, (850, 1150), 150),
    ScatterRule("pl_kaido", "MI_IssosekiWood_MossRockSet01", 1.0, (600, 1200), 100),
    ScatterRule("pl_kaido", "MI_IssosekiWood_RootCluster01", 0.2, (800, 1200), 150),
    ScatterRule("pl_kaido", "MI_IssosekiWood_MossClump01", 25.0, (900, 1600), 40),
    ScatterRule("pl_ishibashi", "MI_Ishibashi_MossRockSet02", 4.0, (700, 1400), 80),
    ScatterRule("pl_kakuredani", "MI_Ishibashi_MossRockSet02", 1.5, (700, 1300), 100),
    ScatterRule("pl_kakuredani", "MI_IssosekiWood_TreeStump01", 0.8, (850, 1150), 150),
)

MASK64 = (1 << 64) - 1
MAX_COORD_CM = 1 << 18       # scatter coordinates stay within +-2.6 km of the area origin


def splitmix64(value: int) -> int:
    value = (value + 0x9E3779B97F4A7C15) & MASK64
    value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
    value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & MASK64
    return value ^ (value >> 31)


def hash_keys(seed: int, *keys: int) -> int:
    value = splitmix64(seed & MASK64)
    for key in keys:
        value = splitmix64(value ^ (key & MASK64))
    return value


def isqrt_cell_cm(per_100_m2: float) -> int:
    """Jittered-grid cell side in centimetres for a mean density (one candidate per cell)."""
    library.require(per_100_m2 > 0.0, "scatter density must be positive")
    side = 1000.0 / per_100_m2 ** 0.5   # 100 m^2 = 1e6 cm^2
    return max(1, int(round(side)))


def path_exclusions(points, half_width_cm: int) -> list:
    """A path polyline (integer cm) as overlapping exclusion circles no more than half a width apart."""
    library.require(half_width_cm > 0 and len(points) >= 2, "a path needs two points and a width")
    circles = []
    step = max(1, half_width_cm // 2)
    for (ax, ay), (bx, by) in zip(points, points[1:]):
        dx, dy = bx - ax, by - ay
        length = max(abs(dx), abs(dy))
        count = max(1, -(-length // step))
        for index in range(count + 1):
            circles.append((ax + dx * index // count, ay + dy * index // count, half_width_cm))
    return circles


def scatter(rule: ScatterRule, variants: tuple, seed: int, bounds_cm: tuple, exclusions=()) -> list:
    """Seeded placements of ``rule`` inside ``bounds_cm`` (x0, y0, x1, y1) away from ``exclusions``.

    ``exclusions`` are integer circles (x, y, radius_cm): spawns, objectives and path
    samples from ``path_exclusions``. Returns (variant, x_cm, y_cm, yaw_tenths_deg,
    scale_milli) tuples, sorted, identical for identical inputs on every platform.
    """
    x0, y0, x1, y1 = bounds_cm
    library.require(x0 < x1 and y0 < y1, "empty scatter bounds")
    library.require(all(abs(value) <= MAX_COORD_CM for value in bounds_cm), "scatter bounds too large")
    library.require(variants, f"{rule.instance}: no mesh variants")
    cell = isqrt_cell_cm(rule.per_100_m2)
    low, high = rule.scale_milli
    library.require(0 < low <= high, f"{rule.instance}: bad scale range")
    placed = []
    for i in range((x1 - x0 + cell - 1) // cell):
        for j in range((y1 - y0 + cell - 1) // cell):
            h = hash_keys(seed, i, j)
            x = x0 + i * cell + h % cell
            y = y0 + j * cell + (h >> 20) % cell
            if x >= x1 or y >= y1:
                continue
            if any((x - cx) ** 2 + (y - cy) ** 2 < (radius + rule.clearance_cm) ** 2
                   for cx, cy, radius in exclusions):
                continue
            g = hash_keys(seed, i, j, 1)
            variant = variants[g % len(variants)]
            yaw = (g >> 16) % 3600
            scale = low + (g >> 32) % (high - low + 1)
            placed.append((variant, x, y, yaw, scale))
    return sorted(placed)


def lighting(preset_id: str) -> Lighting:
    matches = [preset for preset in LIGHTING if preset.id == preset_id]
    library.require(len(matches) == 1, f"Unknown lighting preset {preset_id}")
    return matches[0]
