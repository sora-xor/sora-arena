"""The first-slice CC0 environment material library: sources, masters and place instances.

One definition shared by the host packer (``pack_cc0_environment.py``), the
editor importer (``import_cc0_environment.py``) and the validator
(``validate_cc0_environment.py``). It is plain Python, so the host checks and
the unit test read exactly what the editor builds.

Every CC0 input comes from the schema-2 ledgers
``scripts/assets/manifests/{polyhaven,ambientcg}-first-slice.json``; the raw
files stay read-only in the clone's gitignored ``Local/`` tree, which git
worktrees share with the main checkout. ``build_plan`` checks each ledger
record, its file hashes and the period-accuracy policy below before anything
is imported. The library lives under ``/Game/Generated/Environment/CC0``.

Period-accuracy policy (the ledger's ``period_risk`` and ``period_flags``):

* ``high`` records are flagged inaccurate for the 1623 setting (mortar joints
  on dry-laid walls, tyre tracks, Western roof tiles, wire rope, metal-hooped
  buckets, possible moso bamboo). They are imported under ``CC0/Evaluation``
  and bound only to ``MI_Eval_*`` instances, never to a place instance.
* ``medium`` records may only fill the restricted role their flag names
  (``MEDIUM_ROLES``); anything else is evaluation-only.
* ``low``/``none`` records may be used at the places their ``game_use`` names;
  the flag text travels with the instance as a caveat.
* A place instance may only bind a record whose ``game_use`` lists that place,
  and never a record meant only for characters or weapons.

Nothing here is admitted as photoreal game art: each ledger record keeps its
``photoreal_gate`` and every instance carries it as metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import re

LIBRARY_VERSION = 1
PACKAGE_ROOT = "/Game/Generated/Environment/CC0"
TEXTURES = f"{PACKAGE_ROOT}/Textures"
EVALUATION = f"{PACKAGE_ROOT}/Evaluation"
MATERIALS = f"{PACKAGE_ROOT}/Materials"
INSTANCES = f"{PACKAGE_ROOT}/Instances"
MESHES = f"{PACKAGE_ROOT}/Meshes"
HDRI = f"{PACKAGE_ROOT}/HDRI"
PALETTE_TEXTURES = "/Game/Generated/Environment/Textures"
MACRO_VARIATION = "/Engine/EngineMaterials/T_Default_MacroVariation.T_Default_MacroVariation"
LEDGERS = {
    "polyhaven": "scripts/assets/manifests/polyhaven-first-slice.json",
    "ambientcg": "scripts/assets/manifests/ambientcg-first-slice.json",
}
PACKED_ROOT = "Saved/CC0Environment/Packed"
PACKED_MANIFEST = f"{PACKED_ROOT}/packed.json"
PACK_GENERATOR = "scripts/unreal/pack_cc0_environment.py"
MPC_NAME = "MPC_EnvironmentWeather"
MPC_SCALARS = {"Wetness": 0.0, "PuddleAmount": 0.0, "LanternIntensity": 1.0}
NOT_ADMITTED = ("Not admitted: needs the packaged A/B comparison, measured frame cost and "
                "license check in docs/art-direction/photoreal-acceptance.md before any runtime use.")
CHARACTER_ONLY = {"characters", "weapons"}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def camel(asset_id: str) -> str:
    """hinoki_planks -> HinokiPlanks, Moss001 -> Moss001."""
    return "".join(part[:1].upper() + part[1:] for part in re.split(r"[_\-]", asset_id) if part)


def storage_root(project_root: Path) -> Path:
    """The checkout that holds ``Local/``: the main worktree of this clone.

    Git worktrees keep ``.git`` as a file naming their private git directory,
    whose ``commondir`` points at the shared repository; ``Local/`` lives once,
    beside that repository.
    """
    dot_git = project_root / ".git"
    if dot_git.is_dir():
        return project_root
    text = dot_git.read_text(encoding="utf-8").strip()
    require(text.startswith("gitdir:"), f"Unrecognised .git file: {dot_git}")
    gitdir = Path(text.split(":", 1)[1].strip())
    if not gitdir.is_absolute():
        gitdir = (project_root / gitdir).resolve()
    common = (gitdir / (gitdir / "commondir").read_text(encoding="utf-8").strip()).resolve()
    require(common.name == ".git" and common.is_dir(), f"Unexpected git common directory: {common}")
    return common.parent


def places(record) -> set[str]:
    """Normalised place ids of a ledger record's game_use entries."""
    result = set()
    for use in record.data.get("game_use") or []:
        for token in use["place"].split(" / "):
            token = token.strip().removeprefix("later: ")
            if token.startswith("ch01 lane kit"):
                result.add("lane_kit")
            elif (match := re.match(r"pl_[a-z_]+", token)):
                result.add(match.group(0))
            else:
                result.add(token.lower())
    return result


# --- Ledger records -----------------------------------------------------------

@dataclass(frozen=True)
class Record:
    source: str
    data: dict

    @property
    def asset_id(self) -> str:
        return self.data["asset_id"]

    @property
    def risk(self) -> str:
        return self.data["period_risk"]

    @property
    def flags(self) -> list[str]:
        return [flag["risk"] for flag in self.data.get("period_flags") or []]

    @property
    def key(self) -> str:
        return f"{self.source}:{self.asset_id}"

    def files(self, channel: str) -> list[dict]:
        return [entry for entry in self.data["files"] if entry["channel"] == channel]

    def file(self, channel: str, contains: str = "") -> dict:
        matches = [entry for entry in self.files(channel) if contains in entry["path"]]
        require(len(matches) == 1, f"{self.key}: expected one {channel} file containing {contains!r}")
        return matches[0]


def load_ledgers(project_root: Path) -> dict[str, Record]:
    records = {}
    for source, relative in LEDGERS.items():
        doc = json.loads((project_root / relative).read_text(encoding="utf-8"))
        require(doc.get("schema_version") == 2 and doc.get("kind") == "asset-ledger"
                and doc.get("ledger_id") == f"{source}-first-slice" and doc.get("source") == source
                and doc.get("storage_root") == f"Local/ThirdPartyRaw/cc0/{source}",
                f"First-slice ledger identity changed: {relative}")
        for data in doc["records"]:
            require(data.get("tier") == "PUB-CC0" and data.get("license") == "CC0-1.0"
                    and data.get("commercial_use") is True and data.get("redistribution") == "unrestricted"
                    and data.get("period_risk") in ("none", "low", "medium", "high"),
                    f"{source}:{data.get('asset_id')}: not a usable CC0 record")
            for entry in data["files"]:
                require(entry["path"].startswith(f"Local/ThirdPartyRaw/cc0/{source}/{data['asset_id']}/")
                        and re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]),
                        f"{source}:{data['asset_id']}: unexpected file record {entry['path']}")
            record = Record(source, data)
            require(record.asset_id not in records, f"Duplicate first-slice asset id {record.asset_id}")
            records[record.asset_id] = record
    return records


def is_environment(record: Record) -> bool:
    return bool(places(record) - CHARACTER_ONLY)


# --- Texture sets ---------------------------------------------------------------

@dataclass(frozen=True)
class Channel:
    """One texture package and the file it is imported from."""
    package: str             # /Game/... object path
    file: str | None         # path relative to its root, None for existing palette packages
    root: str                # "storage" (Local/), "project" or "packed"
    sha256: str | None
    kind: str                # color | normal | masks | grayscale
    flip_green: bool = False


@dataclass(frozen=True)
class TextureSet:
    name: str
    origin: str              # ledger key, "palette:<id>" or "project:<id>"
    evaluation: bool
    virtual: bool
    channels: dict           # role -> Channel (BaseColor, Normal, ARM, optional Thickness)
    tile_cm: tuple[float, float] | None
    imported: bool = True    # False: bound from the existing Nyaagyu palette import


@dataclass(frozen=True)
class PackJob:
    output: str              # PACKED_ROOT-relative PNG
    inputs: dict             # "R"/"G"/"B"/"A" -> (storage|project, relative path, sha256) or a constant 0-255


def _package(folder: str, name: str) -> str:
    return f"{folder}/{name}.{name}"


def _texture_folder(name: str, evaluation: bool) -> str:
    return f"{EVALUATION}/Textures/{name}" if evaluation else f"{TEXTURES}/{name}"


def _record_set(record: Record, packs: list[PackJob], evaluation: bool) -> TextureSet:
    name = camel(record.asset_id)
    folder = _texture_folder(name, evaluation)
    virtual = record.data["kind"] == "texture" and record.data["resolution"] == "4k"

    def channel(suffix, entry, kind, flip=False):
        return Channel(_package(folder, f"T_{name}_{suffix}"), entry["path"], "storage",
                       entry["sha256"], kind, flip)

    def packed(sources):
        job = PackJob(f"{record.source}/{record.asset_id}_ARM.png", sources)
        packs.append(job)
        return Channel(_package(folder, f"T_{name}_ARM"), job.output, "packed", None, "masks")

    def raw(entry):
        return ("storage", entry["path"], entry["sha256"])

    kind = record.data["kind"]
    if kind == "texture":
        color = channel("BaseColor", record.file("Diffuse"), "color")
        normal = channel("Normal", record.file("nor_dx"), "normal")
        arm = channel("ARM", record.file("arm"), "masks")
    elif kind == "material":
        color = channel("BaseColor", record.file("Color"), "color")
        normal = channel("Normal", record.file("NormalDX"), "normal")
        sources = {"R": 255, "G": raw(record.file("Roughness")), "B": 0}
        if record.files("AmbientOcclusion"):
            sources["R"] = raw(record.file("AmbientOcclusion"))
        if record.files("Metalness"):
            sources["B"] = raw(record.file("Metalness"))
        if record.files("Opacity"):
            sources["A"] = raw(record.file("Opacity"))
        arm = packed(sources)
    else:
        require(kind == "model", f"{record.key}: unexpected kind {kind}")
        includes = record.files("gltf-include")
        color = channel("BaseColor", record.file("gltf-include", "_diff_"), "color")
        if record.files("nor_dx"):
            normal = channel("Normal", record.file("nor_dx"), "normal")
        else:
            normal = channel("Normal", record.file("gltf-include", "_nor_gl_"), "normal", flip=True)
        if any("_arm_" in entry["path"] for entry in includes):
            arm = channel("ARM", record.file("gltf-include", "_arm_"), "masks")
        else:
            arm = packed({"R": 255, "G": raw(record.file("gltf-include", "_rough_")), "B": 0})
    # tile_size_cm is the scan's width; its measured height sets the V size (the cedar bark is 1 x 2 m).
    tile, dims = record.data.get("tile_size_cm"), record.data.get("source_dimensions_mm")
    tile_cm = (float(tile), round(float(tile) * dims[1] / dims[0], 2)) if tile else None
    return TextureSet(name, record.key, evaluation, virtual,
                      {"BaseColor": color, "Normal": normal, "ARM": arm}, tile_cm)


def _palette_set(name, asset_id, prefix, channels, tile_cm) -> TextureSet:
    """A surface already imported by import_environment_palette.py; bound, never re-imported."""
    kinds = {"BaseColor": "color", "Normal": "normal", "ARM": "masks"}
    return TextureSet(name, f"palette:{asset_id}", False, False,
                      {role: Channel(_package(PALETTE_TEXTURES, f"{prefix}_{suffix}"), None, "palette",
                                     None, kinds[role])
                       for role, suffix in channels.items()}, tile_cm, imported=False)


def _project_sets(project_root: Path, packs: list[PackJob]) -> dict[str, TextureSet]:
    sets = {}
    # Original, project-owned ibushi kawara atlas (no third-party pixels); the
    # first-slice ledger names it primary over every RoofingTiles set.
    ibushi_root = "Content/SourceArt/Environment/NyaagyuKawaraBay"
    ibushi = json.loads((project_root / ibushi_root / "ibushi_texture_manifest.json").read_text())
    require(ibushi.get("generator") == "scripts/art/build_nyaagyu_ibushi_surface.py"
            and ibushi.get("source_type") == "algorithmically painted; no third-party pixels"
            and ibushi.get("layout") == "4x4" and ibushi.get("size") == [2048, 2048]
            and set(ibushi["files"]) == {"Albedo", "NormalDX", "ORM"},
            "Nyaagyu ibushi atlas identity changed")
    folder = _texture_folder("NyaagyuIbushi", False)
    sets["NyaagyuIbushi"] = TextureSet(
        "NyaagyuIbushi", "project:nyaagyu_ibushi", False, False,
        {role: Channel(_package(folder, f"T_NyaagyuIbushi_{role}"),
                       f"{ibushi_root}/{ibushi['files'][key]['file']}", "project",
                       ibushi["files"][key]["sha256"], kind)
         for role, key, kind in (("BaseColor", "Albedo", "color"), ("Normal", "NormalDX", "normal"),
                                 ("ARM", "ORM", "masks"))}, None)
    # TextureCan Paper 0017 (CC0), already retained by the shoji paper study.
    paper_root = "Content/SourceArt/Environment/ShojiPaperArtReview"
    paper = json.loads((project_root / paper_root / "manifest.json").read_text())
    maps = paper["source_maps"]
    require(paper.get("source_page") == "https://www.texturecan.com/details/281/"
            and paper.get("license", "").startswith("TextureCan states CC0 1.0")
            and set(maps) == {"Color", "Height", "NormalDX", "Roughness"},
            "Paper 0017 source identity changed")
    folder = _texture_folder("Paper0017", False)
    job = PackJob("project/paper_0017_ARM.png",
                  {"R": 255, "G": ("project", f"{paper_root}/{maps['Roughness']['file']}",
                                   maps["Roughness"]["sha256"]), "B": 0})
    packs.append(job)
    sets["Paper0017"] = TextureSet(
        "Paper0017", "project:texturecan_paper_0017", False, False,
        {"BaseColor": Channel(_package(folder, "T_Paper0017_BaseColor"), f"{paper_root}/{maps['Color']['file']}",
                              "project", maps["Color"]["sha256"], "color"),
         "Normal": Channel(_package(folder, "T_Paper0017_Normal"), f"{paper_root}/{maps['NormalDX']['file']}",
                           "project", maps["NormalDX"]["sha256"], "normal"),
         "ARM": Channel(_package(folder, "T_Paper0017_ARM"), job.output, "packed", None, "masks"),
         "Thickness": Channel(_package(folder, "T_Paper0017_Thickness"),
                              f"{paper_root}/{maps['Height']['file']}", "project",
                              maps["Height"]["sha256"], "grayscale")}, (64.0, 64.0))
    return sets


PALETTE_SETS = {
    # Content/SourceArt/Environment/PolyHaven/WhitePlaster02 (CC0), imported as T_Plaster_*.
    "WhitePlaster02": ("white_plaster_02", "T_Plaster",
                       {"BaseColor": "Diffuse", "Normal": "nor_dx", "ARM": "arm"}, (100.0, 100.0)),
    # Content/SourceArt/Environment/NyaagyuTerrain grey_stone_path scan (CC0).
    "GreyStonePath": ("grey_stone_path", "T_TerrainGreyStonePath",
                      {"BaseColor": "Diffuse", "Normal": "nor_dx", "ARM": "arm"}, (180.0, 180.0)),
}
EXTERNAL_NOTES = {
    "palette:white_plaster_02": "Surface scan, not a historical reconstruction (its manifest).",
    "palette:grey_stone_path": "Estate roji path scan already on the playable terrain.",
    "project:nyaagyu_ibushi": ("Original procedural ibushi atlas (4x4 cells) for per-tile UV kawara meshes; "
                               "source-only, reflectance unmeasured (NyaagyuKawaraBay README)."),
    "project:texturecan_paper_0017": ("Procedural CC0 paper, not certified washi; its fibres failed the "
                                      "shoji gate, so lanterns need their own A/B."),
}


# --- Masters --------------------------------------------------------------------

@dataclass(frozen=True)
class Master:
    name: str
    family: str              # surface | heightblend | foliage | cloth | lantern
    virtual: bool = False    # layer A (or only layer) samples streaming virtual textures


MASTERS = {m.name: m for m in (
    Master("M_Env_Surface", "surface"),
    Master("M_Env_Surface_VT", "surface", virtual=True),
    Master("M_Env_HeightBlend2", "heightblend"),
    Master("M_Env_HeightBlend2_VTBase", "heightblend", virtual=True),
    Master("M_Env_Foliage", "foliage"),
    Master("M_Env_Cloth", "cloth"),
    Master("M_Env_LanternPaper", "lantern"),
)}

# Parameter names shared by the importer and the validator.
TEXTURE_PARAMS = {
    "surface": ("BaseColor", "Normal", "ARM"),
    "heightblend": ("BaseColor", "Normal", "ARM", "LayerBBaseColor", "LayerBNormal", "LayerBARM"),
    "foliage": ("BaseColor", "Normal", "ARM"),
    "cloth": ("BaseColor", "Normal", "ARM"),
    "lantern": ("BaseColor", "Normal", "ARM", "Thickness"),
}
WORLD_ALIGNED_FAMILIES = ("surface", "heightblend")
_FINISH = {"Desaturation", "RoughnessMin", "RoughnessMax", "AOStrength", "NormalStrength", "MacroStrength",
           "MacroRoughness", "WetnessResponse", "BaseWetness", "WetDarkening", "WetRoughness"}
_SURFACE = _FINISH | {"MetallicScale", "PuddleResponse", "MacroScaleACm", "MacroScaleBCm", "DetailTiling",
                      "DetailNormalStrength"}
# Exact parameter names of each master family (the validator compares them with the built graphs).
FAMILY_PARAMETERS = {
    "surface": {"scalar": _SURFACE, "vector": {"BaseColorTint", "UVScale", "TileSizeCm"},
                "switch": {"WorldAlignedUV", "UseDetailNormal"},
                "texture": {"BaseColor", "Normal", "ARM", "MacroVariation", "DetailNormal"}},
    "heightblend": {"scalar": _SURFACE | {"LayerBCoverage", "VertexColorBlend", "TopFacingBias", "HeightFromCrevices",
                                          "BlendContrast", "LayerBRoughnessMin", "LayerBRoughnessMax"},
                    "vector": {"BaseColorTint", "UVScale", "TileSizeCm", "LayerBUVScale", "LayerBTileSizeCm",
                               "LayerBTint"},
                    "switch": {"WorldAlignedUV", "UseDetailNormal"},
                    "texture": {"BaseColor", "Normal", "ARM", "LayerBBaseColor", "LayerBNormal", "LayerBARM",
                                "MacroVariation", "DetailNormal"}},
    "foliage": {"scalar": _FINISH | {"MacroScaleACm", "MacroScaleBCm", "Transmission"},
                "vector": {"BaseColorTint", "UVScale", "SubsurfaceTint"}, "switch": set(),
                "texture": {"BaseColor", "Normal", "ARM", "MacroVariation"}},
    "cloth": {"scalar": _FINISH | {"MacroScaleACm", "MacroScaleBCm", "ClothAmount"},
              "vector": {"BaseColorTint", "UVScale", "FuzzColor"}, "switch": set(),
              "texture": {"BaseColor", "Normal", "ARM", "MacroVariation"}},
    "lantern": {"scalar": _FINISH | {"ColorTemperatureK", "EmissiveIntensity", "TransmissionMin", "TransmissionMax",
                                     "FlickerSpeed", "FlickerAmount"},
                "vector": {"BaseColorTint", "UVScale"}, "switch": set(),
                "texture": {"BaseColor", "Normal", "ARM", "Thickness"}},
}


# --- Instances ------------------------------------------------------------------

@dataclass(frozen=True)
class Instance:
    name: str
    place: str               # story-bible place id, "lane_kit" or "evaluation"
    master: str
    layers: tuple            # texture-set names: (A,) or (A, B)
    scalars: dict = field(default_factory=dict)
    vectors: dict = field(default_factory=dict)
    world_aligned: bool = False
    detail: bool = False
    blend_mode: str | None = None   # base-property override: "opaque" | "masked"
    roles: dict = field(default_factory=dict)  # asset_id -> medium role claimed

    @property
    def evaluation(self) -> bool:
        return self.place == "evaluation"


def _wet(response, darkening=0.3, rough=0.25, puddles=None, base=0.0):
    values = {"WetnessResponse": response, "WetDarkening": darkening, "WetRoughness": rough, "BaseWetness": base}
    if puddles is not None:  # world-aligned masters only
        values["PuddleResponse"] = puddles
    return values


def _grade(tint=(1.0, 1.0, 1.0), rough=(0.0, 1.0), desat=0.0):
    return ({"RoughnessMin": rough[0], "RoughnessMax": rough[1], "Desaturation": desat},
            {"BaseColorTint": (*tint, 1.0)})


def _inst(name, place, master, layers, *, grade=None, wet=None, extra=None, vectors=None, **kw):
    scalars, vecs = grade or _grade()
    scalars = {**scalars, **(wet or _wet(0.0)), **(extra or {})}
    return Instance(name, place, master, tuple(layers), scalars, {**vecs, **(vectors or {})}, **kw)


# Medium-risk records and the only role their flag allows.
MEDIUM_ROLES = {
    "patterned_clay_plaster": "layer_b",      # "Use only as masked breakup under clay_plaster"
    "Plaster007": "layer_b",                  # "use for crack and spall breakup only"
    "roof_planks": "plank_roof_regraded",     # "Not for the stable" + "Re-grade roughness before use"
    "trident_maple_bark": "maple_bark",       # "Use only as generic maple bark for iroha-momiji"
    "bamboo_wall_02": "review_pending",       # species/weave must be checked before admission
    "bamboo_wall_03": "review_pending",
}

PLACE_INSTANCES = (
    # Timber and floors.
    _inst("MI_TsumagizakaDojo_HinokiFloor", "pl_tsumagizaka_dojo", "M_Env_Surface_VT", ["HinokiPlanks"],
          grade=_grade((1.04, 1.02, 0.98), (0.32, 0.62)), world_aligned=True, detail=True,
          extra={"DetailTiling": 3.3, "DetailNormalStrength": 0.35}),
    _inst("MI_EstateDay_EngawaHinoki", "pl_estate_day", "M_Env_Surface_VT", ["HinokiPlanks"],
          grade=_grade((0.93, 0.93, 0.92), (0.45, 0.82), 0.12), wet=_wet(0.35, 0.28, 0.3),
          world_aligned=True),
    _inst("MI_TsumagizakaDojo_SugiHameita", "pl_tsumagizaka_dojo", "M_Env_Surface_VT", ["JapaneseCedarPlanks"],
          grade=_grade((0.9, 0.86, 0.8), (0.55, 0.85), 0.1), world_aligned=True),
    _inst("MI_Umaya_SugiBoardWall", "pl_umaya", "M_Env_Surface_VT", ["JapaneseCedarPlanks"],
          grade=_grade((0.8, 0.78, 0.75), (0.6, 0.88), 0.35), wet=_wet(0.6, 0.3, 0.3), world_aligned=True),
    _inst("MI_DojoSmithy_ItabukiRoof", "pl_dojo_smithy", "M_Env_Surface", ["RoofPlanks"],
          grade=_grade((0.86, 0.84, 0.82), (0.62, 0.9), 0.2), wet=_wet(1.0, 0.3, 0.25), world_aligned=True,
          roles={"roof_planks": "plank_roof_regraded"}),
    # Earth walls, plaster and floors.
    _inst("MI_EstateDay_Tsuchikabe", "pl_estate_day", "M_Env_Surface_VT", ["ClayPlaster"],
          wet=_wet(1.0, 0.35, 0.35), world_aligned=True, detail=True,
          extra={"DetailTiling": 2.7, "DetailNormalStrength": 0.4}),
    _inst("MI_Kakuredani_CharcoalHutDaub", "pl_kakuredani", "M_Env_HeightBlend2_VTBase",
          ["ClayPlaster", "PatternedClayPlaster"], wet=_wet(1.0, 0.35, 0.35), world_aligned=True,
          extra={"LayerBCoverage": 0.32, "HeightFromCrevices": 0.0, "BlendContrast": 3.0},
          vectors={"LayerBTint": (0.82, 0.74, 0.62, 1.0)}, roles={"patterned_clay_plaster": "layer_b"}),
    _inst("MI_EstateDay_Shikkui", "pl_estate_day", "M_Env_HeightBlend2", ["WhitePlaster02", "Plaster007"],
          wet=_wet(1.0, 0.22, 0.3), world_aligned=True,
          extra={"LayerBCoverage": 0.22, "HeightFromCrevices": 1.0, "BlendContrast": 5.0},
          roles={"Plaster007": "layer_b"}),
    _inst("MI_EstateDay_Tatami", "pl_estate_day", "M_Env_Surface", ["TatamiMat"],
          grade=_grade((0.97, 0.97, 0.93), (0.5, 0.8)), world_aligned=True),
    # Kawara (the ledger keeps the project's ibushi maps primary over every RoofingTiles set).
    _inst("MI_EstateDay_IbushiKawara", "pl_estate_day", "M_Env_Surface", ["NyaagyuIbushi"],
          grade=_grade((1.0, 1.0, 1.0), (0.35, 0.5)), wet=_wet(1.0, 0.15, 0.12)),
    # Stone paths, stream beds and ground.
    _inst("MI_EstateDay_RojiStonePath", "pl_estate_day", "M_Env_HeightBlend2", ["GreyStonePath", "Moss002"],
          wet=_wet(1.0, 0.3, 0.2, puddles=0.6), world_aligned=True,
          extra={"LayerBCoverage": 0.34, "HeightFromCrevices": 1.0, "BlendContrast": 6.0},
          vectors={"LayerBTileSizeCm": (100.0, 100.0, 0.0, 0.0)}),
    _inst("MI_Kaido_PackedEarthRoad", "pl_kaido", "M_Env_Surface_VT", ["ForestGround05"],
          wet=_wet(1.0, 0.32, 0.22, puddles=1.0), world_aligned=True, extra={"MacroStrength": 0.16}),
    _inst("MI_Kaido_GravelPitch", "pl_kaido", "M_Env_Surface", ["ForestGround04"],
          wet=_wet(1.0, 0.3, 0.22, puddles=0.4), world_aligned=True, extra={"MacroStrength": 0.12}),
    _inst("MI_Kakuredani_ValleyFloor", "pl_kakuredani", "M_Env_Surface", ["ForestGround06"],
          wet=_wet(1.0, 0.3, 0.25, puddles=0.5), world_aligned=True, extra={"MacroStrength": 0.12}),
    _inst("MI_IssosekiWood_MossForestFloor", "pl_issoseki_wood", "M_Env_HeightBlend2",
          ["ForestGround06", "Moss001"], wet=_wet(1.0, 0.3, 0.25, puddles=0.2, base=0.2), world_aligned=True,
          extra={"LayerBCoverage": 0.45, "HeightFromCrevices": 0.0, "BlendContrast": 3.0, "MacroStrength": 0.12},
          vectors={"LayerBTileSizeCm": (150.0, 150.0, 0.0, 0.0)}),
    _inst("MI_Ishibashi_StreamBed", "pl_ishibashi", "M_Env_Surface", ["RiverSmallRocks"],
          wet=_wet(1.0, 0.3, 0.12, puddles=0.8, base=0.55), world_aligned=True),
    _inst("MI_Kaido_MossBank", "pl_kaido", "M_Env_Surface", ["Moss003"],
          wet=_wet(1.0, 0.2, 0.3), world_aligned=True, vectors={"TileSizeCm": (200.0, 200.0, 0.0, 0.0)}),
    # Thatch and straw.
    _inst("MI_Kakuredani_KayabukiThatchField", "pl_kakuredani", "M_Env_Surface", ["ThatchRoofAngled"],
          wet=_wet(1.0, 0.3, 0.35), world_aligned=True),
    _inst("MI_Kakuredani_MossyThatch", "pl_kakuredani", "M_Env_HeightBlend2", ["Riet01", "Moss004"],
          wet=_wet(1.0, 0.3, 0.35), world_aligned=True,
          extra={"LayerBCoverage": 0.3, "HeightFromCrevices": 1.0, "BlendContrast": 4.0, "TopFacingBias": 0.15},
          vectors={"LayerBTileSizeCm": (150.0, 150.0, 0.0, 0.0)}),
    _inst("MI_Umaya_WaraStraw", "pl_umaya", "M_Env_Surface", ["ThatchedRoof001A"],
          grade=_grade((1.02, 0.98, 0.9)), wet=_wet(0.3, 0.3, 0.4), world_aligned=True,
          vectors={"TileSizeCm": (150.0, 150.0, 0.0, 0.0)}),
    _inst("MI_Matoba_MakiwaraStraw", "pl_matoba", "M_Env_Surface", ["ThatchedRoof002A"],
          grade=_grade((1.02, 0.98, 0.88), (0.0, 1.0), 0.25), wet=_wet(0.3, 0.3, 0.4)),
    # Bamboo fences (review pending: species and weave, per the ledger flags).
    _inst("MI_LaneKit_AjiroTakegaki", "lane_kit", "M_Env_Surface", ["BambooWall02"],
          wet=_wet(1.0, 0.25, 0.3), world_aligned=True, roles={"bamboo_wall_02": "review_pending"}),
    _inst("MI_Bugugura_TakegakiPanel", "pl_bugugura", "M_Env_Surface", ["BambooWall03"],
          wet=_wet(0.6, 0.25, 0.3), world_aligned=True, roles={"bamboo_wall_03": "review_pending"}),
    # Bark (mesh UVs of the in-house trees).
    _inst("MI_IssosekiWood_SugiBark", "pl_issoseki_wood", "M_Env_Surface_VT", ["JapaneseCedarBark"],
          wet=_wet(1.0, 0.3, 0.3)),
    _inst("MI_EstateDay_MatsuBark", "pl_estate_day", "M_Env_Surface", ["PineBark"], wet=_wet(1.0, 0.3, 0.3)),
    _inst("MI_TsumagizakaDojo_KeyakiBark", "pl_tsumagizaka_dojo", "M_Env_Surface", ["JapaneseZelkovaBark"],
          wet=_wet(1.0, 0.3, 0.3)),
    _inst("MI_IssosekiWood_YamazakuraBark", "pl_issoseki_wood", "M_Env_Surface", ["SakuraBark"],
          wet=_wet(1.0, 0.3, 0.3)),
    _inst("MI_IssosekiWood_MomijiBark", "pl_issoseki_wood", "M_Env_Surface", ["TridentMapleBark"],
          wet=_wet(1.0, 0.3, 0.3), roles={"trident_maple_bark": "maple_bark"}),
    _inst("MI_Kaido_KusunokiBark", "pl_kaido", "M_Env_Surface", ["JapaneseCamphorBark"],
          wet=_wet(1.0, 0.3, 0.3)),
    # Cordage, leather and basketry (mesh UVs).
    _inst("MI_Matoba_HempLashing", "pl_matoba", "M_Env_Surface", ["Rope001"],
          grade=_grade((0.98, 0.95, 0.86), (0.6, 0.95), 0.2), wet=_wet(0.5, 0.3, 0.45)),
    _inst("MI_Umaya_HempRope", "pl_umaya", "M_Env_Surface", ["Rope003"],
          grade=_grade((1.1, 1.05, 0.92), (0.6, 0.95), 0.35), wet=_wet(0.3, 0.3, 0.45)),
    _inst("MI_Umaya_TackLeather", "pl_umaya", "M_Env_Surface", ["Leather014"],
          grade=_grade((0.78, 0.7, 0.62), (0.5, 0.85), 0.2), wet=_wet(0.3, 0.2, 0.3)),
    _inst("MI_Bugugura_ArmorChestLeather", "pl_bugugura", "M_Env_Surface", ["Leather007"],
          grade=_grade((0.82, 0.74, 0.66), (0.5, 0.85), 0.2)),
    _inst("MI_DojoSmithy_TakeKago", "pl_dojo_smithy", "M_Env_Surface", ["Wicker013"],
          grade=_grade((0.82, 0.76, 0.62), (0.45, 0.8), 0.25)),
    # Fabrics.
    _inst("MI_Kakuredani_AsaSacking", "pl_kakuredani", "M_Env_Cloth", ["Hessian230"],
          grade=_grade((0.96, 0.9, 0.78), (0.7, 1.0), 0.45), wet=_wet(0.4, 0.35, 0.5)),
    _inst("MI_Umaya_AsaHorseBlanket", "pl_umaya", "M_Env_Cloth", ["Hessian380"],
          grade=_grade((0.92, 0.88, 0.8), (0.7, 1.0), 0.45)),
    _inst("MI_Kakuredani_JinmakuSilk", "pl_kakuredani", "M_Env_Cloth", ["CrepeSatin"],
          grade=_grade((1.2, 1.17, 1.07), (0.28, 0.5), 1.0), wet=_wet(0.4, 0.3, 0.3),
          extra={"ClothAmount": 0.35}, vectors={"FuzzColor": (0.5, 0.49, 0.45, 1.0)}),
    _inst("MI_Kakuredani_PackWrapCloth", "pl_kakuredani", "M_Env_Cloth", ["Fabric011"],
          grade=_grade((0.96, 0.92, 0.84), (0.6, 1.0), 0.5)),
    _inst("MI_Umaya_ShitaguraPad", "pl_umaya", "M_Env_Cloth", ["Fabric013"],
          grade=_grade((0.95, 0.9, 0.85), (0.6, 1.0), 0.15)),
    # Scanned models (mesh UVs).
    _inst("MI_IssosekiWood_MossRockSet01", "pl_issoseki_wood", "M_Env_Surface", ["RockMossSet01"],
          wet=_wet(1.0, 0.3, 0.25)),
    _inst("MI_Ishibashi_MossRockSet02", "pl_ishibashi", "M_Env_Surface", ["RockMossSet02"],
          wet=_wet(1.0, 0.3, 0.2, base=0.2)),
    _inst("MI_IssosekiWood_Boulder01", "pl_issoseki_wood", "M_Env_Surface", ["Boulder01"],
          wet=_wet(1.0, 0.3, 0.25)),
    _inst("MI_IssosekiWood_RootCluster01", "pl_issoseki_wood", "M_Env_Surface", ["RootCluster01"],
          wet=_wet(1.0, 0.3, 0.3)),
    _inst("MI_IssosekiWood_TreeStump01", "pl_issoseki_wood", "M_Env_Surface", ["TreeStump01"],
          wet=_wet(1.0, 0.3, 0.3)),
    _inst("MI_IssosekiWood_MossClump01", "pl_issoseki_wood", "M_Env_Foliage", ["Moss01"],
          wet=_wet(0.6, 0.12, 0.35), blend_mode="opaque"),
    # Lantern paper (1900 K ward chochin, 1800-2200 K andon; story bible 15.1 and 16).
    _inst("MI_LanternWardRain_ChochinPaper", "pl_lantern_ward_rain", "M_Env_LanternPaper", ["Paper0017"],
          grade=_grade((1.0, 0.97, 0.9)), wet=_wet(0.3, 0.15, 0.3),
          extra={"ColorTemperatureK": 1900.0, "EmissiveIntensity": 14.0}),
    _inst("MI_EstateNight_AndonPaper", "pl_estate_night", "M_Env_LanternPaper", ["Paper0017"],
          grade=_grade((1.0, 0.97, 0.92)),
          extra={"ColorTemperatureK": 2000.0, "EmissiveIntensity": 8.0, "FlickerAmount": 0.04}),
)

# Evaluation-only combinations beyond the one-per-set MI_Eval_* instances.
EVALUATION_INSTANCES = (
    # Mortar joints masked by moss/soil: the remedy the stacked_stone_wall flag names,
    # kept for review until the joints are checked on screen.
    _inst("MI_Eval_StackedStoneWall_MossJoints", "evaluation", "M_Env_HeightBlend2_VTBase",
          ["StackedStoneWall", "Moss003"], wet=_wet(1.0, 0.3, 0.2), world_aligned=True,
          extra={"LayerBCoverage": 0.5, "HeightFromCrevices": 1.0, "BlendContrast": 8.0},
          vectors={"LayerBTileSizeCm": (120.0, 120.0, 0.0, 0.0)}),
)

# ambientCG sets carry no measured size; these world-aligned estimates are overridden per instance.
AMBIENTCG_TILE_CM = 200.0

HDRIS = {
    # asset_id -> (package name, lighting use); every one is lighting-only per its ledger flag.
    "kloofendal_misty_morning_puresky": ("HDRI_KloofendalMistyMorning", "lighting"),
    "qwantani_dusk_2_puresky": ("HDRI_QwantaniDusk2", "lighting"),
    "qwantani_night_puresky": ("HDRI_QwantaniNight", "lighting"),
    "ninomaru_teien": ("HDRI_LookDev_NinomaruTeien", "lookdev"),
    "bamboo_tunnel": ("HDRI_LookDev_BambooTunnel", "lookdev"),
    "spooky_bamboo_morning": ("HDRI_LookDev_SpookyBambooMorning", "lookdev"),
}


# --- Plan -----------------------------------------------------------------------

def mesh_asset_name(asset_id: str, node_name: str) -> str:
    """rock_moss_set_01_rock01 -> SM_RockMossSet01_Rock01, moss_01_c_LOD0 -> SM_Moss01_C."""
    rest = re.sub(r"_?LOD0$", "", node_name.removeprefix(asset_id)).strip("_")
    return f"SM_{camel(asset_id)}" + (f"_{camel(rest)}" if rest else "")


@dataclass
class MeshImport:
    record: Record
    folder: str
    gltf: str                # storage-relative
    nodes: tuple             # glTF node names with a mesh, in file order
    instance: str            # material instance bound to every slot
    nanite: bool = True

    @property
    def assets(self) -> list[tuple[str, str]]:
        return [(node, mesh_asset_name(self.record.asset_id, node)) for node in self.nodes]


@dataclass
class Plan:
    project_root: Path
    storage: Path
    records: dict
    sets: dict
    packs: list
    instances: list
    meshes: list
    hdris: list              # (record, package path)
    expected: dict           # object path -> class name

    def source_path(self, channel: Channel) -> Path:
        if channel.root == "storage":
            return self.storage / channel.file
        if channel.root == "project":
            return self.project_root / channel.file
        require(channel.root == "packed", f"Channel {channel.package} is not imported")
        return self.project_root / PACKED_ROOT / channel.file

    def layers_of(self, instance: Instance) -> list[TextureSet]:
        return [self.sets[name] for name in instance.layers]


def check_instance(instance: Instance, sets: dict, records: dict):
    """Raise if an instance breaks the period-accuracy policy in the module docstring,
    mixes virtual and regular textures, or sets a parameter its master does not have."""
    master = MASTERS[instance.master]
    family = FAMILY_PARAMETERS[master.family]
    unknown = (set(instance.scalars) - family["scalar"]) | (set(instance.vectors) - family["vector"])
    require(not unknown, f"{instance.name}: parameters not on {instance.master}: {sorted(unknown)}")
    resolved_switches(instance)
    require(len(instance.layers) == (2 if master.family == "heightblend" else 1),
            f"{instance.name}: wrong layer count for {master.name}")
    for index, name in enumerate(instance.layers):
        texture_set = sets[name]
        require(master.virtual == texture_set.virtual if index == 0 else not texture_set.virtual,
                f"{instance.name}: {name} virtual-texture state does not match {master.name}")
        if instance.evaluation:
            continue
        require(not texture_set.evaluation, f"{instance.name}: evaluation set {name} bound at a place")
        if not texture_set.origin.startswith(("polyhaven:", "ambientcg:")):
            continue
        record = records[texture_set.origin.split(":", 1)[1]]
        require(record.risk != "high",
                f"{instance.name}: {record.asset_id} is flagged period-inaccurate ({'; '.join(record.flags)})")
        require(instance.place in places(record),
                f"{instance.name}: {record.asset_id} is not planned for {instance.place} ({sorted(places(record))})")
        claimed = instance.roles.get(record.asset_id)
        if record.risk == "medium":
            role = MEDIUM_ROLES.get(record.asset_id)
            require(role is not None and claimed == role,
                    f"{instance.name}: medium-risk {record.asset_id} has no allowed role here")
            if role == "layer_b":
                require(index == 1, f"{instance.name}: {record.asset_id} may only be a breakup layer B")
            elif role == "plank_roof_regraded":
                require(instance.place != "pl_umaya" and instance.scalars.get("RoughnessMin", 0) >= 0.5,
                        f"{instance.name}: roof_planks must not roof the stable and needs re-graded roughness")
            elif role == "maple_bark":
                require("Momiji" in instance.name, f"{instance.name}: trident maple bark is generic momiji bark only")
        else:
            require(claimed is None, f"{instance.name}: role claimed for non-medium {record.asset_id}")


def _gltf_nodes(path: Path) -> tuple:
    gltf = json.loads(path.read_text(encoding="utf-8"))
    return tuple(node["name"] for node in gltf["nodes"] if "mesh" in node)


def build_plan(project_root: Path, *, verify: bool = True) -> Plan:
    project_root = Path(project_root).resolve()
    storage = storage_root(project_root)
    records = load_ledgers(project_root)
    # A set no place instance binds is imported under CC0/Evaluation.
    used = {name for instance in PLACE_INSTANCES for name in instance.layers}
    packs: list[PackJob] = []
    sets: dict[str, TextureSet] = {}
    hdris = []
    meshes_records = []
    for record in records.values():
        if not is_environment(record):
            continue
        kind = record.data["kind"]
        if kind == "hdri":
            name, _ = HDRIS[record.asset_id]
            hdris.append((record, _package(HDRI, name)))
            continue
        texture_set = _record_set(record, packs, camel(record.asset_id) not in used)
        require(texture_set.name not in sets, f"Duplicate texture set {texture_set.name}")
        sets[texture_set.name] = texture_set
        if kind == "model":
            meshes_records.append(record)
    require({record.asset_id for record, _ in hdris} == set(HDRIS), "HDRI list does not match the ledger")
    for name, (asset_id, prefix, channels, tile) in PALETTE_SETS.items():
        sets[name] = _palette_set(name, asset_id, prefix, channels, tile)
    sets.update(_project_sets(project_root, packs))

    require(used <= set(sets), f"Place instances name unknown sets: {sorted(used - set(sets))}")

    instances = list(PLACE_INSTANCES) + list(EVALUATION_INSTANCES)
    for name, texture_set in sets.items():
        if not texture_set.evaluation:
            continue
        kind = records[texture_set.origin.split(":", 1)[1]].data["kind"]
        instances.append(_inst(f"MI_Eval_{name}", "evaluation",
                               "M_Env_Surface_VT" if texture_set.virtual else "M_Env_Surface", [name],
                               wet=_wet(1.0), world_aligned=kind != "model"))
    for instance in instances:
        check_instance(instance, sets, records)
    names = [instance.name for instance in instances]
    require(len(names) == len(set(names)), "Duplicate material instance names")

    # Each scanned model's slots take the one instance built from its own maps.
    meshes = []
    for record in meshes_records:
        name = camel(record.asset_id)
        owners = [item for item in instances if item.layers == (name,)]
        require(len(owners) == 1, f"{record.asset_id}: needs exactly one instance of its own maps")
        folder = f"{EVALUATION}/Meshes/{name}" if sets[name].evaluation else f"{MESHES}/{name}"
        gltf = record.file("gltf")
        meshes.append(MeshImport(record, folder, gltf["path"], _gltf_nodes(storage / gltf["path"]),
                                 owners[0].name))

    expected = {}

    def add(path, cls):
        require(path not in expected, f"Duplicate package {path}")
        expected[path] = cls

    for texture_set in sets.values():
        if texture_set.imported:
            for channel in texture_set.channels.values():
                add(channel.package, "Texture2D")
    for _, path in hdris:
        add(path, "TextureCube")
    add(_package(MATERIALS, MPC_NAME), "MaterialParameterCollection")
    for master in MASTERS:
        add(_package(MATERIALS, master), "Material")
    for instance in instances:
        add(instance_path(instance), "MaterialInstanceConstant")
    for mesh in meshes:
        for _, name in mesh.assets:
            add(_package(mesh.folder, name), "StaticMesh")

    plan = Plan(project_root, storage, records, sets, packs, instances, meshes, hdris, expected)
    if verify:
        verify_sources(plan)
    return plan


def resolved_vectors(plan: Plan, instance: Instance) -> dict:
    """Vector overrides with the world-aligned tile sizes filled in from the sets."""
    vectors = dict(instance.vectors)
    family = MASTERS[instance.master].family
    if family in WORLD_ALIGNED_FAMILIES and instance.world_aligned:
        for index, key in enumerate(("TileSizeCm", "LayerBTileSizeCm")[:len(instance.layers)]):
            if key not in vectors:
                tile = plan.sets[instance.layers[index]].tile_cm or (AMBIENTCG_TILE_CM, AMBIENTCG_TILE_CM)
                vectors[key] = (tile[0], tile[1], 0.0, 0.0)
    return vectors


def resolved_switches(instance: Instance) -> dict:
    if MASTERS[instance.master].family not in WORLD_ALIGNED_FAMILIES:
        require(not instance.world_aligned and not instance.detail,
                f"{instance.name}: {instance.master} samples mesh UVs only")
        return {}
    return {"WorldAlignedUV": instance.world_aligned, "UseDetailNormal": instance.detail}


def texture_expectations(channel: Channel, texture_set: TextureSet, size: tuple[int, int]) -> dict:
    """Unreal texture settings (enum member names) for one imported channel of ``size`` source pixels.

    sRGB only for base colour; DirectX normals as TC_Normalmap (the glTF-only OpenGL normal is
    flipped); ARM as linear TC_Masks; BC7 base colour and streaming virtual textures for the 4K
    hero sets; the few cloth scans a few pixels off a power of two are stretched to one.
    """
    color = "TC_BC7" if texture_set.virtual else "TC_DEFAULT"
    srgb, group, compression = {
        "color": (True, "TEXTUREGROUP_WORLD", color),
        "normal": (False, "TEXTUREGROUP_WORLD_NORMAL_MAP", "TC_NORMALMAP"),
        "masks": (False, "TEXTUREGROUP_WORLD_SPECULAR", "TC_MASKS"),
        "grayscale": (False, "TEXTUREGROUP_WORLD", "TC_GRAYSCALE"),
    }[channel.kind]
    pow2 = not any(value & (value - 1) for value in size)
    return {"srgb": srgb, "lod_group": group, "compression_settings": compression,
            "flip_green_channel": channel.flip_green, "virtual_texture_streaming": texture_set.virtual,
            "power_of_two_mode": "NONE" if pow2 else "STRETCH_TO_POWER_OF_TWO"}


ENUM_SETTINGS = {"lod_group": "TextureGroup", "compression_settings": "TextureCompressionSettings",
                 "power_of_two_mode": "TexturePowerOfTwoSetting"}


def instance_path(instance: Instance) -> str:
    return _package(EVALUATION if instance.evaluation else INSTANCES, instance.name)


def master_path(name: str) -> str:
    return _package(MATERIALS, name)


def mpc_path() -> str:
    return _package(MATERIALS, MPC_NAME)


def verify_sources(plan: Plan):
    """Hash every raw and project file the plan imports or packs."""
    checked = {}

    def check(root, relative, digest):
        path = (plan.storage if root == "storage" else plan.project_root) / relative
        require(path.is_file(), f"Missing CC0 environment source {path}; fetch it with scripts/assets/fetch_cc0.py")
        if path not in checked:
            checked[path] = sha256(path)
        require(checked[path] == digest, f"Source hash mismatch: {path}")

    for texture_set in plan.sets.values():
        for channel in texture_set.channels.values():
            if channel.root in ("storage", "project"):
                check(channel.root, channel.file, channel.sha256)
    for job in plan.packs:
        for source in job.inputs.values():
            if isinstance(source, tuple):
                check(*source)
    for record, _ in plan.hdris:
        entry = record.file("hdri")
        check("storage", entry["path"], entry["sha256"])
    for mesh in plan.meshes:
        for entry in mesh.record.data["files"]:
            if entry["channel"] in ("gltf", "gltf-include"):
                check("storage", entry["path"], entry["sha256"])
    return len(checked)


def read_packed_manifest(project_root: Path) -> dict:
    path = Path(project_root) / PACKED_MANIFEST
    require(path.is_file(), f"Missing {PACKED_MANIFEST}; run {PACK_GENERATOR} first")
    return json.loads(path.read_text(encoding="utf-8"))


def pack_inputs_record(job: PackJob) -> dict:
    return {band: (list(source) if isinstance(source, tuple) else source)
            for band, source in sorted(job.inputs.items())}


def verify_packed(plan: Plan) -> int:
    """Check every packed map against the packer's manifest and the ledger hashes."""
    manifest = read_packed_manifest(plan.project_root)
    require(manifest.get("generator") == PACK_GENERATOR and manifest.get("library_version") == LIBRARY_VERSION,
            "Packed-map manifest is from another generator or library version")
    outputs = manifest["outputs"]
    for job in plan.packs:
        entry = outputs.get(job.output)
        require(entry is not None and entry["inputs"] == pack_inputs_record(job),
                f"Packed map {job.output} is missing or was packed from other sources; rerun {PACK_GENERATOR}")
        path = plan.project_root / PACKED_ROOT / job.output
        require(path.is_file() and sha256(path) == entry["sha256"], f"Packed map changed on disk: {path}")
    return len(plan.packs)


def metadata(plan: Plan, instance: Instance) -> dict:
    """Asset metadata tags recording provenance and period status on each instance."""
    origins, risks, notes = [], [], []
    for index, texture_set in enumerate(plan.layers_of(instance)):
        origins.append(texture_set.origin)
        if texture_set.origin.startswith(("polyhaven:", "ambientcg:")):
            record = plan.records[texture_set.origin.split(":", 1)[1]]
            risks.append(record.risk)
            role = instance.roles.get(record.asset_id)
            if role:
                notes.append(f"{record.asset_id} role {role}")
            notes.extend(f"{record.asset_id}: {flag}" for flag in record.flags)
        else:
            risks.append("none")
            notes.append(f"{texture_set.origin}: {EXTERNAL_NOTES[texture_set.origin]}")
    order = ("none", "low", "medium", "high")
    return {
        "SoraLibrary": f"cc0-environment v{LIBRARY_VERSION}",
        "SoraPlace": instance.place,
        "SoraSources": " + ".join(origins),
        "SoraPeriodRisk": max(risks, key=order.index),
        "SoraPeriodNotes": " | ".join(notes) or "none",
        "SoraPhotorealGate": NOT_ADMITTED,
    }
