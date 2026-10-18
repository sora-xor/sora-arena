"""Measured specification of every runtime weapon mesh (no Blender needed).

The builders (``scripts/art/create_runtime_weapon_<family>.py``) read the part
dimensions from here, and ``scripts/art/create_runtime_weapon_validation.py``
re-measures the exported geometry against the ``checks`` of each entry.

Units are metres. Axes follow the existing runtime weapons: +X is the line of
action (blade tip, spear point, bore), +Z is up (a sword's mune; its edge faces
-Z), +Y is the wielder's left. The origin of every main mesh is its primary
hold point, which is also the ``Grip_R`` socket, except for the yumi, whose
origin is the bow hand (``Grip_L``).

``basis`` says where a value comes from:
  reference  a museum record, federation rule or cited document in this repo;
  period     a common period proportion given as a design value, not a record;
  design     a game/design value (the item is fictional or has no record).
Historical-accuracy claims still need the expert review named in
docs/historical-arms.md and docs/art-direction/photoreal-acceptance.md.
"""

from __future__ import annotations

SHAKU = 0.30303  # 1 shaku (曲尺) in metres
SUN = SHAKU / 10.0

HIST = "docs/historical-arms.md"
PLAN = "docs/art-research/free-asset-acquisition-plan.md section 3.8"
BIBLE = "docs/campaign/story-bible.md"


def check(name, method, expected, tol, basis, source, **args):
    """One metric check: ``method`` is implemented by the validation script."""
    return {"name": name, "method": method, "expected": expected, "tol": tol,
            "basis": basis, "source": source, "args": args}


# Shared socket meaning (documented in the Runtime README and manifest):
#   Grip_R  dominant (right) paw hold, X along the handle toward the business end
#   Grip_L  support (left) paw hold
#   Muzzle  bore exit for firearms; arrow rest for the bow; the striking point
#           (trace end) for melee weapons
SOCKETS = ("Grip_R", "Grip_L", "Muzzle")

NIHONTO = {
    # Keichō-shintō uchigatana carried by Nyaakoto. Nagasa and the ~1 m mounted
    # length follow the Met Edo katana quoted in docs/historical-arms.md.
    0: dict(
        nagasa=0.727, sori=0.015, motohaba=0.032, sakihaba=0.0228, motokasane=0.0074,
        sakikasane=0.0054, kissaki=0.040, shinogi_ji=0.30, zukuri="shinogi",
        tsuka=8.0 * SUN, tsuka_height=0.0318, tsuka_width=0.0244, ito_color="kon",
        # Maru-gata: height along the edge-spine axis (Z) >= width across (Y).
        tsuba=dict(shape="maru", d_y=0.073, d_z=0.076, t=0.0050, hitsu=("kogai", "kozuka"), mon=True),
        habaki="kinkise", seppa="kinkise", fittings="shakudo", menuki="sora_mon",
        hamon="notare_gunome", saya_color="kuro_roiro", sageo="kon", ito_diamonds=9,
    ),
    # Travel short sword (道中差) of the ch03 disguise: plain iron guard, black
    # ito and black saya, no clan mark.
    4: dict(
        nagasa=0.448, sori=0.011, motohaba=0.0300, sakihaba=0.0222, motokasane=0.0068,
        sakikasane=0.0050, kissaki=0.030, shinogi_ji=0.30, zukuri="shinogi",
        tsuka=5.5 * SUN, tsuka_height=0.0300, tsuka_width=0.0232, ito_color="kuro",
        tsuba=dict(shape="maru", d_y=0.065, d_z=0.068, t=0.0045, hitsu=("kozuka",), mon=False),
        habaki="suaka", seppa="suaka", fittings="iron", menuki="shakudo_plain",
        hamon="suguha_ko_notare", saya_color="kuro_roiro_plain", sageo="cha", ito_diamonds=6,
    ),
    # Toranosuke's 鎧通し (yoroidōshi) in an aikuchi mount: hira-zukuri,
    # thick kasane, slight uchizori; no tsuba.
    10: dict(
        nagasa=7.5 * SUN, sori=-0.0010, motohaba=0.0248, sakihaba=0.0205, motokasane=0.0098,
        sakikasane=0.0062, kissaki=0.050, shinogi_ji=0.0, zukuri="hira",
        tsuka=3.5 * SUN, tsuka_height=0.0290, tsuka_width=0.0215, ito_color=None,
        tsuba=None, habaki="suaka", seppa=None, fittings="horn", menuki="shakudo_plain",
        hamon="suguha", saya_color="kuro_roiro_plain", sageo="kuro", ito_diamonds=0,
    ),
}


WEAPONS = {
    0: dict(
        key="W00_Katana", asset="SM_Weapon_00", ja="刀", en="Katana", family="nihonto",
        faction="League hero (Nyaakoto)", builder="scripts/art/create_runtime_weapon_nihonto.py",
        extra_assets=["SM_Weapon_00_Saya"], texture_res=2048, lod0_tri_budget=90000,
        focus=(0.18, 0.0, 0.0),
        checks=[
            check("nagasa", "blade_nagasa", NIHONTO[0]["nagasa"], 0.003, "reference",
                  f"{HIST}: Met Edo katana (638804) 72.7 cm cutting edge", part="Blade"),
            check("sori", "blade_sori", NIHONTO[0]["sori"], 0.002, "period",
                  f"{PLAN}: Met 24378 curvature 0.9 cm; shallow Keichō-shintō sori chosen", part="Blade"),
            check("mounted_length", "extent_x", 0.998, 0.015, "reference",
                  f"{HIST}: Met Edo katana (638804) 99.8 cm overall", asset="SM_Weapon_00"),
            check("tsuka_length", "span_x", NIHONTO[0]["tsuka"], 0.003, "period",
                  "8 sun uchigatana tsuka (fuchi face to kashira end)", parts=["Fuchi", "Kashira"]),
            check("tsuba_height", "extent_z", 0.076, 0.002, "period",
                  "maru-gata iron tsuba, height (edge to spine) >= width", part="Tsuba"),
            check("tsuba_width", "extent_y", 0.073, 0.002, "period", "maru-gata iron tsuba", part="Tsuba"),
            check("saya_length", "extent_x", 0.786, 0.012, "derived",
                  "habaki + nagasa + kojiri clearance", asset="SM_Weapon_00_Saya"),
        ],
    ),
    4: dict(
        key="W04_Wakizashi", asset="SM_Weapon_04", ja="脇差", en="Wakizashi", family="nihonto",
        faction="League (ch03 travel mount)", builder="scripts/art/create_runtime_weapon_nihonto.py",
        extra_assets=["SM_Weapon_04_Saya"], texture_res=2048, lod0_tri_budget=70000,
        focus=(0.10, 0.0, 0.0),
        checks=[
            check("nagasa", "blade_nagasa", NIHONTO[4]["nagasa"], 0.003, "reference",
                  f"{PLAN}: Met 21880 wakizashi blade 44.8 cm", part="Blade"),
            check("tsuka_length", "span_x", NIHONTO[4]["tsuka"], 0.003, "period",
                  "5.5 sun wakizashi tsuka", parts=["Fuchi", "Kashira"]),
            check("tsuba_height", "extent_z", 0.068, 0.002, "period",
                  "plain iron maru tsuba, height (edge to spine) >= width", part="Tsuba"),
            check("tsuba_width", "extent_y", 0.065, 0.002, "period", "plain iron maru tsuba", part="Tsuba"),
        ],
    ),
    10: dict(
        key="W10_Tanto", asset="SM_Weapon_10", ja="短刀", en="Tantō", family="nihonto",
        faction="Toranosuke's pledge (ch06)", builder="scripts/art/create_runtime_weapon_nihonto.py",
        extra_assets=["SM_Weapon_10_Saya"], texture_res=2048, lod0_tri_budget=40000,
        focus=(0.05, 0.0, 0.0),
        checks=[
            check("nagasa", "blade_nagasa", NIHONTO[10]["nagasa"], 0.003, "period",
                  "yoroidōshi tantō under 1 shaku; 7.5 sun design value", part="Blade"),
            check("kasane", "extent_y_at_base", NIHONTO[10]["motokasane"], 0.0008, "period",
                  "thick yoroidōshi kasane (design value)", part="Blade"),
            check("tsuka_length", "span_x", NIHONTO[10]["tsuka"], 0.003, "period",
                  "aikuchi tsuka 3.5 sun", parts=["Fuchi", "Kashira"]),
        ],
    ),
    2: dict(
        key="W02_Kusarigama", asset="SM_Weapon_02", ja="鎖鎌", en="Kusarigama", family="kusarigama",
        faction="League (Otane's farm sickle on a chain)", builder="scripts/art/create_runtime_weapon_kusarigama.py",
        extra_assets=["SM_Weapon_02_Chain"], texture_res=2048, lod0_tri_budget=90000, focus=(0.10, 0.10, 0.0),
        handle=0.45, blade=0.175, chain=2.70, link_pitch=0.0175, link_wire=0.0042, fundo=(0.058, 0.026),
        checks=[
            check("handle_length", "span_x", 0.45, 0.004, "period",
                  "farm-sickle handle 1.5 shaku, butt cap to ferrule (design value)",
                  parts=["Handle", "Ferrule", "Butt_Cap"]),
            check("blade_overall", "extent_z", 0.197, 0.006, "period",
                  "17.5 cm below the handle plus 2.2 cm set into its head (design value)", part="Kama_Blade"),
            check("chain_length", "chain_length", 2.70, 0.08, "period",
                  "9 shaku chain (design value)", prefix="Chain_Link"),
        ],
    ),
    6: dict(
        key="W06_Kanabo", asset="SM_Weapon_06", ja="金棒", en="Kanabō", family="blunt",
        faction="League (Kōzō's gate breaker, ch08)", builder="scripts/art/create_runtime_weapon_blunt.py",
        texture_res=2048, lod0_tri_budget=80000, focus=(0.55, 0.0, 0.0),
        length=1.52, head_flats=(0.088, 0.058), grip_d=0.042,
        checks=[
            check("overall_length", "extent_x", 1.52, 0.010, "design",
                  f"{PLAN}: kanabō dimensions are a documented gap (TNM F-15962/3, F-16879 have no size data)",
                  asset="SM_Weapon_06"),
            check("head_across_flats", "max_across_flats", 0.088, 0.003, "design",
                  "octagonal oak body tapering by a third to the grip", part="Body"),
        ],
    ),
    8: dict(
        key="W08_ForgeHammer", asset="SM_Weapon_08", ja="鍛冶槌", en="Forge Hammer", family="blunt",
        faction="League (向こう鎚 striker's sledge, ch05)", builder="scripts/art/create_runtime_weapon_blunt.py",
        texture_res=2048, lod0_tri_budget=40000, focus=(0.30, 0.0, 0.0),
        handle=0.80, head=(0.165, 0.056, 0.056),
        checks=[
            check("handle_length", "extent_x", 0.80, 0.006, "period", "mukōzuchi handle (design value)", part="Handle"),
            check("head_length", "extent_z", 0.165, 0.003, "period", "mukōzuchi head ~3.7 kg steel (design value)",
                  part="Head"),
            check("head_mass_kg", "mass", 3.9, 0.5, "period", "7.85 g/cm3 steel", part="Head", density=7850),
        ],
    ),
    12: dict(
        key="W12_MonofilamentNaginata", asset="SM_Weapon_12", ja="単分子薙刀", en="Monofilament Naginata",
        family="polearm", faction="League special (Kōzō and Okinu, ch08)",
        builder="scripts/art/create_runtime_weapon_polearms.py", texture_res=2048, lod0_tri_budget=70000,
        focus=(1.45, 0.0, 0.05),
        checks=[
            check("overall_length", "extent_x", 2.31, 0.015, "design",
                  "Content/SourceArt/Weapons/MonofilamentNaginata (2.31 m source study)", asset="SM_Weapon_12"),
            check("blade_length", "blade_nagasa", 0.54, 0.004, "design", "fictional special blade", part="Blade"),
        ],
    ),
    17: dict(
        key="W17_HealingLance", asset="SM_Weapon_17", ja="治癒の槍", en="Healing Lance", family="polearm",
        faction="League special (Okuzu the apothecary, ch08)", builder="scripts/art/create_runtime_weapon_polearms.py",
        texture_res=2048, lod0_tri_budget=70000, focus=(1.10, 0.0, 0.0),
        checks=[
            check("overall_length", "extent_x", 1.85, 0.015, "design", "fictional apothecary lance", asset="SM_Weapon_17"),
        ],
    ),
    18: dict(
        key="W18_Yumi", asset="SM_Weapon_18", ja="和弓", en="Yumi", family="yumi",
        faction="Nyaakoto (shigetō war bow)", builder="scripts/art/create_runtime_weapon_yumi.py",
        extra_assets=["SM_Weapon_18_Ya"], texture_res=2048, lod0_tri_budget=80000, origin="Grip_L",
        focus=(0.0, 0.0, 0.10),
        checks=[
            check("bow_length", "yumi_length", 2.21, 0.012, "reference",
                  f"{HIST}: All Japan Kyudo Federation standard 221 cm (Cleveland 1921.403: 220.9 cm)", part="Stave"),
            check("grip_from_lower_tip", "yumi_grip_ratio", 1.0 / 3.0, 0.03, "reference",
                  f"{HIST}: grip about one-third from the lower end", part="Stave", grip="Nigiri"),
            check("brace_height", "yumi_brace", 0.15, 0.015, "period",
                  "~15 cm bow-to-string brace (NyaagyuYumi study sources)", part="Stave", string="Tsuru"),
            check("arrow_length", "extent_x", 0.98, 0.01, "period", "war arrow for a ~90 cm draw (design)",
                  asset="SM_Weapon_18_Ya"),
        ],
    ),
    19: dict(
        key="W19_Yari", asset="SM_Weapon_19", ja="槍", en="Yari", family="polearm",
        faction="Nyaakoto (su-yari)", builder="scripts/art/create_runtime_weapon_polearms.py",
        texture_res=2048, lod0_tri_budget=50000, focus=(1.55, 0.0, 0.0),
        checks=[
            check("overall_length", "extent_x", 2.13, 0.015, "reference",
                  f"{HIST}: Met 1727 foot yari note, foot spears commonly ~7 ft", asset="SM_Weapon_19"),
            check("blade_length", "blade_nagasa", 0.206, 0.003, "reference",
                  f"{PLAN}: Met 30843 su-yari blade 20.6 cm", part="Blade"),
        ],
    ),
    20: dict(
        key="W20_Naginata", asset="SM_Weapon_20", ja="薙刀", en="Naginata", family="polearm",
        faction="Okinu's mother's naginata (ch05)", builder="scripts/art/create_runtime_weapon_polearms.py",
        texture_res=2048, lod0_tri_budget=60000, focus=(1.35, 0.0, 0.05),
        checks=[
            check("blade_length", "blade_nagasa", 0.467, 0.004, "reference",
                  f"{PLAN}: ColBase F-20202 blade 46.7 cm", part="Blade"),
            check("sori", "blade_sori", 0.021, 0.003, "reference",
                  f"{PLAN}: ColBase F-20202 curvature 2.1 cm", part="Blade"),
            check("overall_length", "extent_x", 2.15, 0.02, "period", "Edo women's naginata (design value)",
                  asset="SM_Weapon_20"),
        ],
    ),
    5: dict(
        key="W05_CoilMatchlock", asset="SM_Weapon_05", ja="コイル火縄銃", en="Coil Matchlock", family="firearm",
        faction="League village gun with an alien coil breech (ch04; no SORA mon)",
        builder="scripts/art/create_runtime_weapon_firearms.py", texture_res=2048, lod0_tri_budget=90000,
        focus=(0.15, 0.0, 0.03),
        checks=[
            check("overall_length", "extent_x", 1.038, 0.012, "reference",
                  f"{PLAN}: Met 22492 tanegashima overall 103.8 cm", asset="SM_Weapon_05"),
            check("barrel_length", "extent_x", 0.73, 0.006, "reference",
                  f"{PLAN}: Met 22492 barrel 73 cm", part="Barrel"),
            check("bore", "bore_diameter", 0.016, 0.0008, "reference", f"{PLAN}: Met 22492 16 mm bore",
                  part="Barrel"),
        ],
    ),
    9: dict(
        key="W09_Repeater", asset="SM_Weapon_09", ja="連発銃", en="Repeater", family="firearm",
        faction="League foundry-built (bronze, iron, timber; SORA mon)", builder="scripts/art/create_runtime_weapon_firearms.py",
        texture_res=2048, lod0_tri_budget=90000, focus=(0.10, 0.0, 0.04),
        checks=[
            check("overall_length", "extent_x", 1.12, 0.015, "design", "fictional League repeater", asset="SM_Weapon_09"),
            check("bore", "bore_diameter", 0.0125, 0.0008, "design", "reduced-calibre drum repeater", part="Barrel"),
        ],
    ),
    1: dict(
        key="W01_ArcCarbine", asset="SM_Weapon_01", ja="アーク・カービン", en="Arc Carbine", family="firearm",
        faction="League-built (Tetsugorō, ch05; SORA mon on the receiver cheeks)",
        builder="scripts/art/create_runtime_weapon_firearms.py", texture_res=2048, lod0_tri_budget=90000,
        focus=(0.08, 0.0, 0.03),
        checks=[
            check("overall_length", "extent_x", 0.86, 0.015, "design", "fictional League carbine", asset="SM_Weapon_01"),
        ],
    ),
    7: dict(
        key="W07_GrenadeLauncher", asset="SM_Weapon_07", ja="擲弾筒", en="Grenade Launcher", family="firearm",
        faction="League (Tamakichi's 花火筒 hand-mortar, ch03)", builder="scripts/art/create_runtime_weapon_firearms.py",
        texture_res=2048, lod0_tri_budget=80000, focus=(0.20, 0.0, 0.0),
        checks=[
            check("overall_length", "extent_x", 0.84, 0.015, "design",
                  "rope-bound bamboo hand tube after the Edo 手筒花火 (design)", asset="SM_Weapon_07"),
            check("bore", "bore_diameter", 0.056, 0.002, "design", "festival-shell bore", part="Tube_Liner"),
        ],
    ),
    15: dict(
        key="W15_MicroMortar", asset="SM_Weapon_15", ja="小型迫撃砲", en="Micro-Mortar", family="firearm",
        faction="League siege train (Tamakichi, ch08; cast SORA mon)", builder="scripts/art/create_runtime_weapon_firearms.py",
        texture_res=2048, lod0_tri_budget=80000, focus=(0.10, 0.0, 0.06),
        checks=[
            check("overall_length", "extent_x", 0.64, 0.015, "design", "hand-held bronze mortar after 抱え大筒 (design)",
                  asset="SM_Weapon_15"),
            check("bore", "bore_diameter", 0.075, 0.002, "design", "mortar bore", part="Barrel"),
        ],
    ),
    14: dict(
        key="W14_PlasmaMatchlock", asset="SM_Weapon_14", ja="プラズマ火縄銃", en="Plasma Matchlock", family="alien",
        faction="Alien-built, captured (ch07)", builder="scripts/art/create_runtime_weapon_alien.py",
        texture_res=2048, lod0_tri_budget=90000, focus=(0.20, 0.0, 0.03),
        checks=[
            check("overall_length", "extent_x", 1.32, 0.02, "design", "long matchlock silhouette (ch07 asset table)",
                  asset="SM_Weapon_14"),
        ],
    ),
    3: dict(
        key="W03_NeedleSMG", status="blockout", asset="SM_Weapon_03", ja="ニードル短機関銃", en="Needle SMG", family="alien",
        faction="Alien (given by Iota, ch06)", builder="scripts/art/create_runtime_weapon_alien.py",
        texture_res=2048, lod0_tri_budget=80000, focus=(0.06, 0.0, 0.03),
        checks=[check("overall_length", "extent_x", 0.56, 0.015, "design", "compact SMG", asset="SM_Weapon_03")],
    ),
    13: dict(
        key="W13_PhantomSMG", status="blockout", asset="SM_Weapon_13", ja="幻影短機関銃", en="Phantom SMG", family="alien",
        faction="Alien vault armory (ch06)", builder="scripts/art/create_runtime_weapon_alien.py",
        texture_res=2048, lod0_tri_budget=80000, focus=(0.08, 0.0, 0.03),
        checks=[check("overall_length", "extent_x", 0.64, 0.015, "design", "suppressed SMG", asset="SM_Weapon_13")],
    ),
    11: dict(
        key="W11_PulseCarbine", status="blockout", asset="SM_Weapon_11", ja="パルス・カービン", en="Pulse Carbine", family="alien",
        faction="Alien levy carbine (enforcers)", builder="scripts/art/create_runtime_weapon_alien.py",
        texture_res=2048, lod0_tri_budget=80000, focus=(0.10, 0.0, 0.03),
        checks=[check("overall_length", "extent_x", 0.84, 0.015, "design", "levy carbine", asset="SM_Weapon_11")],
    ),
    16: dict(
        key="W16_ShockEmitter", status="blockout", asset="SM_Weapon_16", ja="電撃放射器", en="Shock Emitter", family="alien",
        faction="Alien security arm (ch07)", builder="scripts/art/create_runtime_weapon_alien.py",
        texture_res=2048, lod0_tri_budget=80000, focus=(0.10, 0.0, 0.03),
        checks=[check("overall_length", "extent_x", 0.72, 0.015, "design", "short-range emitter", asset="SM_Weapon_16")],
    ),
}

# LOD policy: LOD1 and LOD2 are decimated from LOD0 (UVs kept); LOD2 also
# drops parts smaller than a few millimetres (their ``lod_drop`` is 2).
LOD_RATIOS = (1.0, 0.42, 0.16)
LOD_SCREEN_SIZES = (1.0, 0.35, 0.12)
MIN_TEXEL_DENSITY = 1024.0  # px/m; story bible section 15.1 hero set pieces


def weapon(weapon_id: int) -> dict:
    return WEAPONS[weapon_id]


def by_builder(script_name: str, include_held: bool = False):
    """Weapon ids a builder script makes by default; weapons still marked
    ``status="blockout"`` are built only when asked for by id."""
    return sorted(i for i, w in WEAPONS.items() if w["builder"].endswith(script_name)
                  and (include_held or w.get("status") != "blockout"))
