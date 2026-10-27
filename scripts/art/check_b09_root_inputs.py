"""Check b09_workshop_craft's pinned inputs against root's tree, read-only (git show and rev-parse only).

For each file in b09_workshop_craft.INPUTS:
- its blob at the pinned commit must be the pinned blob;
- its blob at root's HEAD is reported, so drift since the pin is visible.

The constants the design rests on are parsed from the pinned files and compared with the module's:
- the stations and their steps;
- the room's solids, box by box (b09_workshop_craft.SOLIDS and SOLID_SURFACES);
- the bend and paste timing;
- the reach;
- the hero's capsule and standing eye;
- the station trace's end height;
- the view the presentation reads (SoraWorkshopCraftRules::FView, FSoraKitView::LanternCraft);
- the b09 recipe and output;
- weapon 7's bore, culm, muzzle and fuse.

Prints B09_ROOT_INPUTS <json>; exits 1 on any mismatch.

Run (host): /usr/bin/python3 scripts/art/check_b09_root_inputs.py <root tree>
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import b09_workshop_craft as B  # noqa: E402


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True).stdout


def main():
    root = Path(sys.argv[1])
    commit = B.INPUTS["root_commit"]
    head = git(root, "rev-parse", "HEAD").strip()
    problems, files = [], {}
    for path, blob in B.INPUTS["blobs"].items():
        at_pin = git(root, "rev-parse", f"{commit}:{path}").strip()
        at_head = git(root, "rev-parse", f"HEAD:{path}").strip()
        files[path] = {"pinned": blob, "at_commit": at_pin, "at_head": at_head, "changed_since": at_head != blob}
        if at_pin != blob:
            problems.append(f"{path}: blob {at_pin} at {commit}, pinned {blob}")
    show = lambda p: git(root, "show", f"{commit}:{p}")  # noqa: E731
    rules = show("Source/SoraArena/Public/SoraLanternWorkshopRules.h")
    solids = parse_solids(rules)
    mine = [(list(c), list(sz), surf) for (c, sz), surf in zip(B.SOLIDS, B.SOLID_SURFACES)]
    if solids[0][2] != "Soil" or [(c, sz, srf) for c, sz, srf in solids[1:]] != mine:
        problems.append(f"Solids: the header has {len(solids)} boxes; the module's {len(mine)} (with the ground slab "
                        "left out) differ")
    stations = [(float(x), float(y)) for x, y in re.findall(r"\{(-?\d+),(-?\d+)\}",
                                                             re.search(r"Stations\[\]=\{(.*?)\};", rules).group(1))]
    steps = tuple(int(v) for v in re.search(r"StepStations\[\]=\{(.*?)\}", rules).group(1).split(","))
    if stations != [xy for _, xy in B.STATIONS]:
        problems.append(f"stations {stations}")
    if steps != B.STEP_STATIONS:
        problems.append(f"step stations {steps}")
    timing = show("Source/SoraArena/Public/SoraWorkshopCraftRules.h")
    t = dict(re.findall(r"(BendMs|BendToleranceMs|PasteMs)=(\d+)", timing))
    if (int(t["BendMs"]), int(t["BendToleranceMs"]), int(t["PasteMs"])) != (B.BEND_MS, B.BEND_TOL_MS, B.PASTE_MS):
        problems.append(f"timing {t}")
    reach = float(re.search(r"Interact = ([\d.]+)f", show("Source/SoraArena/Private/Game/SoraCampaignReach.h")).group(1))
    if reach != B.REACH_CM:
        problems.append(f"reach {reach}")
    cap = re.search(r"InitCapsuleSize\((\d+),(\d+)\)", show("Source/SoraArena/Private/Characters/SoraCharacterBase.cpp")).groups()
    if (float(cap[0]), float(cap[1])) != (B.CAPSULE_R, B.CAPSULE_HALF):
        problems.append(f"capsule {cap}")
    eye = float(re.search(r"StandingEyeZ=([\d.]+)f", show("Source/SoraArena/Private/Characters/SoraPlayerCharacter.cpp")).group(1))
    if eye != B.EYE[2]:
        problems.append(f"eye {eye}")
    view = re.search(r"struct FView\s*\{(.*?)\};", timing, re.S)
    want_fields = ("Active", "RecipeComplete", "Assist", "Step", "Committed[6]", "HeldStep", "HeldMs", "FailedStripSerial", "FailedStripAgeMs")
    if view is None or any(f not in view.group(1) for f in want_fields):
        problems.append("SoraWorkshopCraftRules::FView lacks a field the presentation reads")
    if "SoraWorkshopCraftRules::FView LanternCraft;" not in show("Source/SoraArena/Public/SoraWorldBuilder.h"):
        problems.append("FSoraKitView::LanternCraft is missing")
    trace = show("Source/SoraArena/Private/Game/SoraCampaignWorkshopCraft.cpp")
    if "Space->FloorAt(P)+110" not in trace or "ECC_Visibility" not in trace:
        problems.append("the station trace is not to FloorAt(P)+110 on Visibility")
    chapter = json.loads(show("Content/Data/campaign/chapter_03.json"))
    beat = next(b for b in (chapter if isinstance(chapter, list) else chapter.get("beats", []))
                if isinstance(b, dict) and b.get("id") == "ch03.b09") if isinstance(chapter, list) else None
    if beat is None:
        beat = _find_beat(chapter)
    man = beat["params"]["manufacture"]
    recipe = [(s["kind"], s["count"]) for s in man["steps"]]
    if tuple(recipe) != B.STEPS or man["output"]["qty"] != B.OUTPUT_LANTERNS or man["stations"] != [s for s, _ in B.STATIONS]:
        problems.append(f"recipe {recipe} output {man['output']}")
    rec = json.loads(show("Content/SourceArt/Weapons/Runtime/W07_GrenadeLauncher/build_record.json"))
    sock = rec["assets"]["SM_Weapon_07"]["sockets"]
    w = {"bore_cm": round(rec["notes"]["bore_m"] * 100, 4), "culm_cm": round(rec["notes"]["culm_diameter_m"] * 100, 4),
         "muzzle_cm": [round(sock["Muzzle"][0] * 100, 4), round(-sock["Muzzle"][1] * 100, 4), round(sock["Muzzle"][2] * 100, 4)],
         "fuse_cm": [round(sock["Fuse"][0] * 100, 4), round(-sock["Fuse"][1] * 100, 4), round(sock["Fuse"][2] * 100, 4)]}
    if (w["bore_cm"], w["culm_cm"]) != (B.WEAPON7["bore_cm"], B.WEAPON7["culm_cm"]) or \
            w["muzzle_cm"] != list(B.WEAPON7["muzzle_cm"]) or w["fuse_cm"] != list(B.WEAPON7["fuse_cm"]):
        problems.append(f"weapon 7 {w}")
    out = {"root": str(root), "pinned_commit": commit, "head": head, "files": files, "problems": problems,
           "changed_since_pin": sorted(p for p, f in files.items() if f["changed_since"])}
    print("B09_ROOT_INPUTS " + json.dumps(out, indent=1))
    sys.exit(1 if problems else 0)


def parse_solids(text):
    """SoraLanternWorkshopRules::Solids as [(centre, size, surface)], its one `for(int S:{-1,1})` loop expanded."""
    body = text[text.index("Solids()"):]
    body = body[:body.index("return B;")]
    call = re.compile(r"Box\(([^;]*?)\);")

    def boxes(chunk, env):
        out = []
        for m in call.finditer(chunk):
            args = [a.strip() for a in m.group(1).split(",")]
            surf = args[6].split("::")[1] if len(args) > 6 else "Wood"
            vals = []
            for a in args[:6]:
                if not re.fullmatch(r"[-+*0-9.S ]+", a):
                    raise ValueError(f"unparsed Box argument {a!r}")
                vals.append(float(eval(a, {"__builtins__": {}}, env)))
            out.append((vals[:3], vals[3:], surf))
        return out
    loop = re.search(r"for\(int S:\{-1,1\}\)\s*\{(.*?)\}", body, re.S)
    before, after = (body[:loop.start()], body[loop.end():]) if loop else (body, "")
    out = boxes(before, {})
    if loop:
        for sgn in (-1, 1):
            out += boxes(loop.group(1), {"S": sgn})
    return out + boxes(after, {})


def _find_beat(node):
    if isinstance(node, dict):
        if node.get("id") == "ch03.b09" and "params" in node:
            return node
        for v in node.values():
            r = _find_beat(v)
            if r is not None:
                return r
    elif isinstance(node, list):
        for v in node:
            r = _find_beat(v)
            if r is not None:
                return r
    return None


if __name__ == "__main__":
    main()
