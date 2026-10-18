#!/usr/bin/env python3
"""Rebuild, validate and record every runtime weapon (system python3).

    python3 scripts/art/create_runtime_weapon_build_all.py              # build all, validate, manifests
    python3 scripts/art/create_runtime_weapon_build_all.py --only 0,19  # rebuild some, then re-record
    python3 scripts/art/create_runtime_weapon_build_all.py --manifests-only

Each builder runs in its own Blender 5.2 process (one job at a time). The
script refuses to start a family when that could leave less than 30 GiB free
on the data volume (measured ~15 MB per new weapon; a rebuild overwrites
files of about the same size). Afterwards it runs the metric validation and
writes

* Content/SourceArt/Weapons/Runtime/manifest.json - the schema-2 OWN ledger
  document listing every generated file (SHA-256, bytes);
* Content/SourceArt/Weapons/Runtime/sources_manifest.json - the lane draft
  listing every third-party input the materials and renders read, each
  looked up in the asset ledger (same SHA-256 and tier, or the run fails).
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "scripts/assets"))
import create_runtime_weapon_specs as S  # noqa: E402

BLENDER = os.environ.get("BLENDER", "/Applications/Blender.app/Contents/MacOS/Blender")
RUNTIME = ROOT / "Content/SourceArt/Weapons/Runtime"
BUILDERS = ["nihonto", "polearms", "blunt", "kusarigama", "yumi", "firearms", "alien"]
# Hard floor for the data volume (lane rule: keep >= 30 GiB free). One family
# writes well under 0.3 GiB (textures, FBX, compressed blends, renders).
MIN_FREE_GIB = 30.0


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def free_gib() -> float:
    return shutil.disk_usage(ROOT).free / (1 << 30)


def run_blender(script: str, extra=()):
    cmd = [BLENDER, "-b", "--factory-startup", "--python", str(HERE / script), "--", *extra]
    print("$", " ".join(cmd), flush=True)
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    log = proc.stdout + proc.stderr
    for line in log.splitlines():
        if line.startswith("[") or "Error" in line or "Traceback" in line:
            print("  " + line, flush=True)
    if proc.returncode != 0 or "Traceback" in log:
        raise SystemExit(f"{script} failed (exit {proc.returncode})")


def ledger_lookup():
    import asset_ledger as AL
    table = {}
    for path, doc in AL.load_ledgers(ROOT):
        for record in AL.doc_records(doc):
            for entry in AL.record_files(record):
                p = AL.file_path(entry)
                if p and entry.get("sha256"):
                    table[p] = (entry["sha256"], record.get("tier"), record.get("asset_id"),
                                str(path.relative_to(ROOT)), record.get("license"))
    return table


def held_back(wid) -> bool:
    """A weapon whose builder is still at blockout level: its local outputs
    are not admitted to the manifests or the README until it is redesigned
    and reviewed (specs ``status="blockout"``)."""
    return S.WEAPONS[wid].get("status") == "blockout"


def write_manifests():
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    records = []
    sources = set()
    incomplete = []
    held_assets = []
    for wid in sorted(S.WEAPONS):
        if held_back(wid):
            incomplete.append(S.WEAPONS[wid]["key"])
            held_assets.append(S.WEAPONS[wid]["asset"] + "_")
            continue
        rec_path = RUNTIME / S.WEAPONS[wid]["key"] / "build_record.json"
        if rec_path.is_file():
            rec = json.loads(rec_path.read_text())
            if "textures" not in rec or "renders" not in rec:
                # A geometry-only (--no-bake/--no-render) run: not a deliverable.
                incomplete.append(S.WEAPONS[wid]["key"])
                continue
            records.append(rec)
            sources.update(rec.get("sources", []))
    files = []
    for path in sorted(RUNTIME.rglob("*")):
        if not path.is_file() or path.name in ("manifest.json", "sources_manifest.json") or path.suffix == ".blend1":
            continue
        if any(part in incomplete for part in path.relative_to(RUNTIME).parts):
            continue
        if path.parent.name == "Renders" and any(path.name.startswith(a) for a in held_assets):
            continue
        rel = str(path.relative_to(ROOT)).replace(os.sep, "/")
        files.append({"file": rel, "bytes": path.stat().st_size, "sha256": sha256(path)})
    table = ledger_lookup()
    inputs, missing = [], []
    for src in sorted(sources):
        full = ROOT / src
        digest = sha256(full) if full.is_file() else None
        hit = table.get(src)
        if hit is None or digest != hit[0]:
            missing.append(src)
            continue
        inputs.append({"file": src, "sha256": digest, "bytes": full.stat().st_size, "tier": hit[1],
                       "ledger_record": hit[2], "ledger_document": hit[3], "license": hit[4]})
    if missing:
        raise SystemExit("third-party inputs missing from the ledger (or changed): " + ", ".join(missing))
    manifest = {
        "schema_version": 2,
        "tier": "OWN",
        "asset_id": "runtime-weapons",
        "name": "SORA Arena runtime weapon meshes SM_Weapon_00..20 (LOD0-2, sockets, baked PBR, renders)",
        "license": ("Project-owned original work (SORA Arena): procedural Blender geometry, original masks "
                    "(hamon, lacquer wear, ledger lines) and bakes. The baked maps include derived detail from "
                    "CC0 scans listed in sources_manifest.json (Poly Haven, ambientCG); no paid or restricted asset."),
        "generator_scripts": sorted({r["builder"] for r in records} | {
            "scripts/art/create_runtime_weapon_lib.py", "scripts/art/create_runtime_weapon_specs.py",
            "scripts/art/create_runtime_weapon_validation.py", "scripts/art/create_runtime_weapon_build_all.py"}),
        "regenerate": "python3 scripts/art/create_runtime_weapon_build_all.py",
        "tool": "Blender 5.2.2 LTS (Cycles bake and renders)",
        "generated_at_utc": now,
        "storage": "repo-lfs",
        "sources_manifest": "Content/SourceArt/Weapons/Runtime/sources_manifest.json",
        "weapons": [{"id": r["id"], "key": r["key"], "ja": r["ja"], "en": r["en"], "assets": sorted(r["assets"])}
                    for r in records],
        "not_built": [S.WEAPONS[w]["key"] for w in sorted(S.WEAPONS)
                      if S.WEAPONS[w]["key"] not in {r["key"] for r in records} and not held_back(w)],
        "held_back_blockout": [S.WEAPONS[w]["key"] for w in sorted(S.WEAPONS) if held_back(w)],
        "admission": ("Source art only: not yet imported by scripts/toolchain/import-mac.sh, not reviewed in Unreal, "
                      "and not admitted by docs/art-direction/photoreal-acceptance.md or a historian."),
        "files": files,
    }
    (RUNTIME / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    draft = {
        "schema": "sora-arena-source-ledger/2-draft",
        "purpose": ("Third-party inputs read by the runtime weapon authoring materials and review renders. "
                    "Raw CC0 files stay in the gitignored Local/ThirdPartyRaw tree; committed palette files are "
                    "already recorded in the Poly Haven ledger extension."),
        "ledger": sorted({i["ledger_document"] for i in inputs}),
        "generated_at_utc": now,
        "inputs": inputs,
    }
    (RUNTIME / "sources_manifest.json").write_text(json.dumps(draft, ensure_ascii=False, indent=1) + "\n",
                                                   encoding="utf-8")
    print(f"manifest.json: {len(files)} files; sources_manifest.json: {len(inputs)} inputs", flush=True)


README_HEAD = """# Runtime weapon meshes (SM_Weapon_00 to SM_Weapon_20)

Editable, measured source art for every catalog weapon: the 18 arena weapons
and the campaign yumi, yari and naginata. Each weapon folder holds the LOD0,
LOD1 and LOD2 FBX files, the baked 2048 x 2048 texture set, the Blender
source (named, editable parts in the `RW_Source` collection plus the exported
LOD objects) and a `build_record.json`. `Renders/` has three Blender Cycles
images per weapon: `_Neutral_1m` (35 mm lens, camera 1.0 m from the focus
point, neutral grey studio exposed 0.6 EV under the AgX default),
`_Estate_1m` (camera 1.0 m, lying on the Estate's timber boards under the
Estate's own overcast sky, `kloofendal_overcast_puresky`) and `_Profile`
(orthographic side view over a ruler with 1 cm or 10 cm ticks). Because the
pure-sky dome has no horizon or features for polished steel and lacquer to
reflect, both lit renders add three glossy-only reflection cards (a dark
eave, a bright sky strip and a dark tree line; invisible to camera, diffuse
and shadow rays), so blades and urushi show a horizon instead of flat grey.

These are Blender renders, not Unreal captures. Nothing here is imported by
`scripts/toolchain/import-mac.sh` yet, and nothing is admitted by the photoreal
gate (`docs/art-direction/photoreal-acceptance.md`) or reviewed by a historian.
The gate needs in-engine A/B captures; these renders cannot pass it alone.
The viewmodel still loads the old `Content/SourceArt/SM_Weapon_XX` primitives
until the import step switches to these files.

## Conventions

- Units are metres in Blender; the FBX files use `apply_unit_scale`, so Unreal
  imports centimetres. Real-world (human) dimensions; the viewmodel applies
  its own 0.75 scale.
- Axes: +X is the line of action (blade tip, spear point, bore), +Z is up
  (a sword's edge faces -Z), +Y is the wielder's left (Unreal -Y).
- Origin: the dominant paw's hold, which is also `Grip_R`; the yumi's origin
  is the bow hand (`Grip_L`).
- Sockets are `SOCKET_` empties parented to the LOD0 mesh (Unreal imports them
  as static-mesh sockets): `Grip_R`, `Grip_L` and `Muzzle` on every weapon
  (`Muzzle` is the bore exit, the arrow rest, or the striking point/trace end
  of a melee weapon), plus extras where useful (`Pan`, `MatchTip`, `Fuse`,
  `Charge`, `Magazine`, `Chain_Anchor`, `String_Upper/Lower`; the saya has
  `Koiguchi` and `Kurikata`; the ya has `Nock` and `Tip`; the kusarigama chain
  has `Anchor` and `Fundo`).
- One material slot per mesh. `T_Weapon_XX_BaseColor` (sRGB; A is an opacity
  mask where the weapon has alpha cards: the ya's vanes, the hand-mortar's
  straw fibres), `T_Weapon_XX_NormalDX` (tangent space, DirectX green-down,
  baked on the exported triangulation), `T_Weapon_XX_ORM` (R ambient
  occlusion, G roughness, B metallic) and `T_Weapon_XX_Mask` (R hamon or
  emissive, G lacquer/edge wear, B cavity). Emissive weapons record their
  glow colour in `build_record.json` (League glows are warm; only alien arms
  are cyan). `build_record.json` also records the baked microsurface: the
  mean tangent tilt of the NormalDX over all texels and per authoring material.
- UV channel 0 (`UV0`) is a unique non-overlapping atlas for the baked maps;
  channel 1 (`UVMetric`) keeps continuous metre-scale coordinates for detail
  tiling. Extra meshes (saya, ya, chain) share their weapon's atlas.
- LOD1 and LOD2 are decimated from LOD0 (about 42 % and 16 % of its triangles;
  LOD2 drops parts of a few millimetres). Suggested screen sizes 1.0 / 0.35 / 0.12.

## Design notes

- **Nihontō (0, 4, 10).** Blades are lofted along a circular mune arc with the
  measured nagasa and sori: shinogi-zukuri with iori-mune, a crisp yokote,
  ko-shinogi and a fukura drawn as a tangent arc (katana, wakizashi), or
  hira-zukuri with no yokote, a thick yoroidōshi kasane and slight uchizori
  (tantō). The hamon is an original procedural mask (Mask R): gunome heads
  on a noise-modulated spacing and height over a slow notare (katana,
  naginata), suguha with ko-notare, or suguha; a 0.5-1.5 mm nioiguchi, ashi,
  nie and a turned-back bōshi; the ha is hadori-whitened (+13 % value,
  roughness ~0.3) against a near-mirror ji (~0.08) that shows itame hada in
  the normal, and the shinogi-ji and mune are burnished darker and nearly
  mirror (~0.03). The katana has a gold-foiled habaki that tapers toward the
  ha with crossing neko-gaki file marks (roughness ~0.24), seppa, a maru iron
  tsuba (7.6 cm edge-to-spine by 7.3 cm) with tsuchime and a tekkotsu mimi,
  kogai and kozuka hitsu-ana and small SORA-mon inlays, shakudō fuchi and a
  domed oval kashira with shitodome, SORA-mon menuki, a bamboo mekugi, and two
  hineri-maki ito strands that start under the fuchi and cross the kashira
  (kashira-kake) over samegawa of scattered 0.4-1.2 mm nodules with the
  oyatsubu under the omote menuki. The wakizashi is the plain ch03 travel
  mount (suaka copper habaki and seppa under a brown oxide, iron fittings);
  the tantō is an aikuchi with black-lacquered same polished back to the
  nodule crowns and a domed horn kashira. Each saya carries one continuous
  flat braided sageo (~9 mm wide) threaded through the kurikata, crossing
  down the saya to a knot and two tails; the renders show the saya below the
  blade.
- **Polearms (19, 20, 12, 17).** Sankaku su-yari whose blade, bevelled machi
  and kerakubi are one welded loft, carried flat side up with a hi and
  suguha on both edges; habaki, kuchigane, a lacquered 千段巻 cord (pitch
  jitter, lacquer pooling, dielectric) and a roiro shaft tapering to the
  iron ishizuki. Naginata-zukuri blades widen toward the fukura with a
  naginata-hi groove; small tsuba, a dōgane with end rims, a brazed seam and
  mekugi, a semegane band and a 千段巻 run onto an oval ebu that tapers to a
  long ishizuki. The monofilament naginata's 0.5 mm filament stands 1.5 mm
  off the ha on multi-turn dark silk bindings and glows warm amber-white
  (Mask R). The healing lance is fictional: a hollow bronze needle under a
  brown-green patina, a caged glass reservoir (warm honey-gold glow in Mask
  R), a deep shu urushi shaft worn through to its black undercoat where it
  is handled, with fine craquelure, and spiral, shingled indigo cotton
  wraps soiled by handling. The yari, naginata and lance shafts carry the
  craquelure (danmon) of old lacquer.
- **Kanabō (6) and forge hammer (8).** A 1.52 m octagonal oak club that
  tapers by a third from the head to the grip, densely shod with ~230
  hand-forged pyramidal studs in staggered rows every 3.3 cm (each differs in
  size, height, lean and twist), iron-tannate and rust staining bled into the
  oak round every stud and band, iron bands, a domed cap, an iron butt with
  a ring and a braided tekubi cord loop, and a shingled leather grip wrap.
  The 向こう鎚 head is under black forge scale, both striking faces
  mushroomed into a 2-3 mm chipped lip and worked bright (roughness ~0.2),
  on an oval kashi handle that tapers into the eye, with grip grime and an
  iron wedge in the end grain.
- **Kusarigama (2).** Kashi handle with ferrule, rivet, butt cap and chain
  ring; a kataba sickle with a rounded 4.8 mm spine, a black-forged kurouchi
  flat and a 6 mm stone-ground bevel on the omote whose bright hagane band
  (roughness ~0.12) runs under a wavering lamination line. The 2.7 m chain is
  its own runtime mesh (`SM_Weapon_02_Chain`, driven from the handle's
  `Chain_Anchor` in Unreal): ~155 hand-forged links within +-10 % of the
  nominal size, out of round, with forge-weld swellings and their own lean,
  lying as a loose flat coil with the octagonal fundō at its centre.
- **Yumi (18) and ya.** The braced shape is integrated from a curvature
  profile solved so both tips meet the string line at the brace height; a
  rounded-rectangular stave section (2.85 x 2.15 cm at the grip, tapering)
  in black urushi; shigetō bands of flat split rattan wound two-and-a-bit
  turns by hand under lacquer, worn to the golden skin on the crowns; a
  deerskin nigiri wound as a shingled spiral strip; horn hazu; a
  resin-coated hemp string with nakajikake. The ya has a tapered yadake
  shaft with four nodes, horn hazu, silk bindings, a yanagi-ba point and
  three dyed hawk-feather vanes (the red is Nyaakoto's character choice)
  whose barbs, natural barring and ragged trimmed edge are an alpha mask on
  thin vane geometry.
- **League firearms (5, 9, 1, 7, 15).** All share the League's Japanese
  gunsmithing language: a carved dai stock with a slim cheek butt whose
  underline curves down from the wrist, barrels pinned through the forestock
  with mekugi in brass escutcheons, brass karakuri on the right with springs
  and slotted screws, brass triggers without a guard, and brass and bronze
  under their own patina. The coil matchlock follows the tanegashima of Met
  22492 with an alien coil sleeve grafted over the breech and a soft hinawa
  wound round the wrist. The repeater has a two-piece cast bronze karakuri
  box (seam, engraved border, screws), a ribbed bronze side drum with a
  riveted hub and loading gate, and a brass butt cap. The arc carbine is a
  short negoro stock (shu worn through to black) with brass cheek plates
  carrying the SORA mon and a pinned barrel through copper coil stages in a
  bronze cage (warm white arc glow). The hand-mortar is a thick-walled madake
  culm with a node, bound in hairy two-ply rice-straw nawa (hand-laid, loose
  fibre cards, frayed ends) and closed by a turned oak plug handle lashed
  and nailed into its base. The micro-mortar is cast bronze under a
  brown-green patina with casting flash, pits and the cast SORA mon, bedded
  in a carved oak cradle and held by iron capsquare straps nailed to it.
- **Alien arms (14, 3, 13, 11, 16).** Chamfered near-black graphite (albedo
  ~0.04) machined with directional micro-grooves and face-milling swirls,
  brushed titanium, clear black glass, hex fasteners and clamp collars, rails,
  louvred vents, cables, sparse cyan ledger lines and the ledger sigil (a ring
  of tally notches, unlike the SORA mon).

## Materials and licences

Geometry, masks and bakes are original (project-owned, see `manifest.json`).
The authoring materials read these third-party CC0 inputs, all recorded in the
asset ledger and listed with their SHA-256 in `sources_manifest.json`:

- wood: Poly Haven `japanese_cedar_planks` (photo scan), cut at its plank
  seams, tone-matched and cross-faded into a seamless straight-grain board;
  only its grain structure is used, re-toned to measured hardwood colours
  (kashi, gun-stock oak, cherry, smoked oak) with original oak ray fleck,
  vessel pores, grip grime and iron staining;
- iron and steel breakup: Poly Haven `rusty_metal_02` (photo scan, committed
  Estate palette); polished blade steel, hamon, nie, hada, file marks, nanako,
  tsuchime, forge scale, casting pits and lacquer are original procedural
  masks, because no CC0 polished steel scan is in the local library;
- fabric and cord: Poly Haven `crepe_satin` and `rough_linen` (photo scans);
  ambientCG `Fabric001` (surface-approximated), `Rope001` and `Rope002` (upstream
  procedural);
- straw: ambientCG `ThatchedRoof001A` (the nawa's fibre);
- leather: ambientCG `Leather014` (surface-approximated);
- render environment only: the Estate `kloofendal_overcast_puresky` HDRI and
  `wood_planks_dirt` boards (committed palette).

## Rebuild and validate

```sh
python3 scripts/art/create_runtime_weapon_build_all.py            # all builders, validation, manifests
python3 scripts/art/create_runtime_weapon_build_all.py --only 0   # one weapon
blender -b --factory-startup --python scripts/art/create_runtime_weapon_validation.py
python3 scripts/assets/validate_asset_ledger.py
```

The CC0 inputs come from `python3 scripts/assets/fetch_cc0.py`. The metric
validator re-measures the saved source parts and the re-imported FBX files and
writes `metric_report.json`.

## Open items (not claimed here)

- Unreal import, material instances (masked two-sided for the alpha cards),
  LOD screen sizes and socket use in `USoraViewmodelComponent`, and
  first-person paw fitting.
- Packaged-game A/B captures, Mac/Windows frame cost and the photoreal gate.
- Historian and practitioner review of the nihontō mounts, hamon, yari and
  naginata sections, the yumi's braced profile, shigetō binding layout and ya,
  the tanegashima lock and the kusarigama configuration. Kanabō, kusarigama,
  mukōzuchi and tantō sizes are period design values, not museum records.
- Chain physics, bowstring and arrow rigging, and charge/pulse emissive states.
- The polished blade steel has no photographic scan source.
"""


def write_readme():
    report_path = RUNTIME / "metric_report.json"
    report = json.loads(report_path.read_text()) if report_path.is_file() else {"weapons": {}}
    lines = [README_HEAD, "## Weapons\n",
             "| ID | Weapon | Faction / use | LOD0 / LOD1 / LOD2 triangles | Texel density p05 (px/m) | Metric validation |",
             "|---:|---|---|---|---:|---|"]
    detail = ["", "## Measured checks\n",
              "Values in metres (mass in kg, grip position as a fraction of the stave). *reference*: a museum record "
              "or rule cited in the repo; *period*: a common period proportion used as a design value; *derived*: "
              "follows from other measured parts; *design*: fictional or undocumented.\n",
              "| Weapon | Check | Measured | Target +- tol | Basis | Source |", "|---|---|---:|---:|---|---|"]
    for wid in sorted(S.WEAPONS):
        spec = S.WEAPONS[wid]
        rec_path = RUNTIME / spec["key"] / "build_record.json"
        if not rec_path.is_file() or held_back(wid):
            continue
        rec = json.loads(rec_path.read_text())
        if "textures" not in rec or "renders" not in rec:
            continue
        main = rec["assets"][spec["asset"]]
        tris = " / ".join(str(l["triangles"]) for l in main["lods"])
        extra = [a for a in rec["assets"] if a != spec["asset"]]
        if extra:
            ex = rec["assets"][extra[0]]
            tris += f" (+ {extra[0].split('_')[-1]}: " + " / ".join(str(l["triangles"]) for l in ex["lods"]) + ")"
        rr = report["weapons"].get(str(wid), {})
        status = "pass" if rr.get("pass") else ("fail" if rr else "not run")
        dens = rec.get("texel_density_px_per_m", {}).get("p05", 0)
        lines.append(f"| {wid} | {spec['ja']} {spec['en']} (`{spec['asset']}`) | {spec['faction']} | {tris} | "
                     f"{dens:.0f} | {status} |")
        for c in rr.get("checks", []):
            if "basis" not in c:
                continue
            meas = c.get("measured")
            meas = f"{meas:.4f}" if isinstance(meas, (int, float)) else str(meas)
            detail.append(f"| {spec['en']} | {c['name']} | {meas} | {c['expected']:.4f} +- {c['tol']:.4f} | "
                          f"{c['basis']} | {c['source']} |")
    built = set()
    for wid in sorted(S.WEAPONS):
        rp = RUNTIME / S.WEAPONS[wid]["key"] / "build_record.json"
        if rp.is_file():
            rr = json.loads(rp.read_text())
            if "textures" in rr and "renders" in rr:
                built.add(wid)
    missing = [f"{w} {S.WEAPONS[w]['en']}" for w in sorted(S.WEAPONS) if w not in built and not held_back(w)]
    if missing:
        lines.append("")
        lines.append("**Not built yet:** " + ", ".join(missing) + ". Their builders and specs are in place; run "
                     "`python3 scripts/art/create_runtime_weapon_build_all.py --only " +
                     ",".join(str(w) for w in sorted(S.WEAPONS) if w not in built and not held_back(w)) +
                     "` when the data volume has room (the lane keeps at least 30 GiB free).")
    held = [f"{w} {S.WEAPONS[w]['en']}" for w in sorted(S.WEAPONS) if held_back(w)]
    if held:
        lines.append("")
        lines.append("**Blockout, not admitted:** " + ", ".join(held) + ". Their builders still produce "
                     "blockout-level forms (slab stocks, plain boxes); any local outputs are left out of "
                     "`manifest.json` and this table until the designs are redone and reviewed.")
    (RUNTIME / "README.md").write_text("\n".join(lines + detail) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", default=None, help="comma-separated weapon ids")
    ap.add_argument("--manifests-only", action="store_true")
    ap.add_argument("--skip-validation", action="store_true")
    args = ap.parse_args()
    if not args.manifests_only:
        ids = [int(x) for x in args.only.split(",")] if args.only else [w for w in sorted(S.WEAPONS)
                                                                        if not held_back(w)]
        for fam in BUILDERS:
            chosen = [i for i in ids if S.WEAPONS[i]["builder"].endswith(f"create_runtime_weapon_{fam}.py")]
            if not chosen:
                continue
            gib = free_gib()
            # A rebuild overwrites files of about the same size; only weapons
            # without outputs yet add ~15 MB each.
            new_ids = [i for i in chosen if not (RUNTIME / S.WEAPONS[i]["key"] / "build_record.json").is_file()
                       or "textures" not in json.loads((RUNTIME / S.WEAPONS[i]["key"] / "build_record.json").read_text())]
            budget = 0.02 * len(new_ids) + 0.005 * (len(chosen) - len(new_ids))
            if gib - budget < MIN_FREE_GIB:
                raise SystemExit(f"only {gib:.2f} GiB free; refusing to start {fam} "
                                 f"(estimated +{budget:.3f} GiB would leave less than {MIN_FREE_GIB} GiB)")
            print(f"[disk] {gib:.2f} GiB free before {fam} (estimated +{budget:.3f} GiB)", flush=True)
            run_blender(f"create_runtime_weapon_{fam}.py", ["--only", ",".join(map(str, chosen))])
        if not args.skip_validation:
            run_blender("create_runtime_weapon_validation.py", ["--only", ",".join(map(str, ids))] if args.only else [])
    write_readme()
    write_manifests()
    subprocess.run([sys.executable, str(ROOT / "scripts/assets/validate_asset_ledger.py"), "--quiet-warnings"],
                   cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
