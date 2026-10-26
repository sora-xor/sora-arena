# Inventory drone (目録): body envelope and collision proposal

**Status (2026-10-26):**
- Root accepts the direction (70 cm disc, actor scale 1.0, movement capsule 38/38), pending the kit and the route tests.
- The source kit is built and checked against this envelope (section 5). It is not yet imported into Unreal.
- No final visual acceptance.

![Ledger hall section and the proposed body](data/inventory_drone_envelope.png)

## 1. What the drone is today (measured from root's 65f4aaea, read-only)

**The story bible, §7:**
- `drone`, 目録 (もくろく), "Inventory" drone: a floating disc with a cyan eye.
- It scouts, marks, and drops seizure nets. First seen in ch02.
- Every enemy type needs a readable silhouette.
- It flies in ch02-ch07: ten shot from the saddle in ch02.b08, two sweeping in ch03.b02 and ch06.b06, and drone pairs
  as boss adds.

**`enemies.json` `drone`:**

| field | value |
| --- | --- |
| `body`, `behavior` | `drone` |
| `scale_permille` | 600 |
| speed | 500 cm/s |
| `hover_cm` | 450 |
| `keep_distance_cm` | 600 |
| sight | 2200 cm |
| the seizure net | range 0-1500 cm, radius 150 cm, root 1.5 s, 800 ms windup, cyan telegraph |
| variant | `audit_hound` (health 60, sight 900) |

**The runtime:**
- The drone is an `ASoraEnemy`, an `ASoraCharacterBase` whose 34 x 88 cm capsule (`InitCapsuleSize(34,88)`) is scaled by
  `scale_permille`. So its body is 20.4 cm in radius with a 52.8 cm half-height.
- It flies in `MOVE_Flying` and wears the humanoid alien visual.

**The ledger hall** (`SoraLedgerRules.h`):

| what | value |
| --- | --- |
| the hall | 2400 x 6400 cm, ceiling 600 |
| shelves | 120 cm wide at x 0, 440, ..., 2200; their tops at 450 |
| aisles | 320 cm wide |
| drones 6 and 7 | at z 550, on rectangular routes along aisles x 280-2040 and cross-aisles y 1200-6000, at least 280 cm from either wall |

**Root's LedgerPatrols on 65f4aaea:**
- The centres sit at 547.077 and 547.079 cm. Physics depenetrates the 52.8 cm half-height about 2.92 cm below the
  authored 550, under the 600 ceiling.
- An earlier 5 cm tolerance hid this.

## 2. The constraints

| constraint | measured | limit on the body |
| --- | --- | --- |
| ceiling over the flight plane | 600 - 550 = 50 cm | half-height under 50. **45** keeps a margin over the movement skin |
| shelf tops under the flight plane | 550 - 450 = 100 cm | the bottom stays above 450 (a weak limit) |
| walls and shelves beside the route | above 450 nothing stands within 280 cm | none at the flight height |
| Unreal's capsule | half-height at least the radius | a disc's collision is at best a sphere (half-height = radius) |
| visual inside collision | — | no vertex outside the sphere, so the body never shows inside a wall it touches |
| readability | at 20 m and a 90° view, about 21 px per degree at 1080p | a 70 cm disc spans about 42 px; a 50 cm one about 30 |
| the net | a 150 cm net folded under the body | a canister of about 16-20 cm |

## 3. The proposal

**The body** is authored at its real size: actor scale 1.0, not a scaled humanoid. Its pivot is its centre, so the
authored flight height is the disc's centre.
- **The hull:** a lens-shaped disc 70 cm across, its rim about 8 cm thick. It rises to a low dorsal dome (+9.4 cm)
  and carries a ventral net pod (to -14 cm), whose muzzle reaches -17.7 cm. Overall it is 27 cm tall.
- **The eye:** a cyan lens on the front rim (+X), recessed so it stays inside the rim's radius.
- **The materials:** the alien family's (story bible §15.1):
  - micro-engraved graphite;
  - black glass;
  - brushed titanium;
  - a thin cyan ledger line round the rim.

  The ledger sigil, a ring of tally notches, goes on top. It never carries the SORA mon. The eye and ledger lines are
  flagged in Mask R, so Unreal can drive the net's cyan telegraph.
- **The net pod:** a short canister under the centre, its muzzle angled down and forward.
- **The sockets** (Unreal component cm, X forward):

  | socket | position | direction |
  | --- | --- | --- |
  | `Eye` | the lens centre, on the front rim | +X |
  | `NetMuzzle` | the pod's mouth | about 45° down and forward |

  Both are checked at build.

**The collision:** a sphere, capsule **38 / 38** cm at actor scale 1.0 (`scale_permille` 1000), centred on the body.
- In the ledger hall its top is at 588, 12 cm clear of the ceiling; its bottom at 512, 62 cm above the shelf tops.
- The body's furthest vertex is about 36.5 cm from the centre, inside 38. The kit checks every vertex against the
  sphere.

**For root to decide (not art):**
- **The hit volume.** The sphere is 76 cm tall, but the body is 27 cm. Root asked for hit hulls, so the kit carries
  three convex ones for precision shots (section 5). Root owns the collision responses.
- **Every other drone route** needs checking with a 38 cm sphere: ceilings, doorways and gaps in ch02.b08, ch03.b02,
  ch04.b05, ch06.b06 and the boss adds. Root's regressions cover those. Nothing is widened or lowered to fit.
- **The eye height:** `Eye()` today is `EyeHeight` x scale. The drone's eye is the `Eye` socket.

## 4. The source kit

`scripts/art/create_inventory_drone.py` (Blender 5.2.2) uses the weapon library's materials, bake, LODs and FBX
export (`create_runtime_weapon_lib.py`), unchanged. A drone is not a weapon, so `DroneBuild` replaces only:
- the spec and the folder;
- the socket set;
- the renders;
- a record amendment.

`scripts/art/validate_inventory_drone.py` round-trips the FBXs in a clean session.
`scripts/art/test_inventory_drone_record.py` checks the record on the CPU.

**Not here:**
- the runtime collision response, eye light, net launch and hover motion (root's integration);
- the `audit_hound` variant's look;
- any change to the hall's 600 or the flight's 550, or to root's source and `enemies.json`.

## 5. As built (measured, 2026-10-26)

**Files** (`Content/SourceArt/Characters/Enemies/InventoryDrone/`):

| file | what |
| --- | --- |
| `SM_Drone_Inventory.fbx` | LOD0, 10,386 triangles, with the sockets and the UCX hulls |
| `SM_Drone_Inventory_LOD1.fbx` | 4,362 triangles |
| `SM_Drone_Inventory_LOD2.fbx` | 1,660 triangles |
| `T_Drone_Inventory_{BaseColor,ORM,Mask,NormalDX}.png` | the maps, 2048 |
| `SM_Drone_Inventory.blend` | the blend |
| `build_record.json` | the record, with every number below |

The review originals are in `../Renders/SM_Drone_Inventory_{Front,Side,Top,ThreeQuarter,Envelope,Lineup}.png`.

**The envelope:**
- The farthest vertex of any LOD is 36.23 cm from the centre: inside 36.5, and 1.77 cm inside the 38 cm sphere.
- The build fails otherwise, and the validator rechecks it from the FBXs.
- The bounds are 71.8 x 71.2 x 26.9 cm.

**The sockets** (Unreal cm = 100 x (x, -y, z) of these Blender metres):

| socket | position | direction |
| --- | --- | --- |
| `Eye` | (0.3622, 0, 0), the pupil's front | +X |
| `NetMuzzle` | (0.0768, 0, -0.1518) | X 45° down and forward |

Both are within 0.1 mm of the record, and the muzzle within 0.5° of its axis, from the FBX.

**The hit hulls** (Unreal custom collision in the LOD0 FBX):

| hull | encloses | vertices | span z (cm) |
| --- | --- | --- | --- |
| `UCX_SM_Drone_Inventory_00` | the disc: hull, rim, ledger line, eye, sigil, vents | 235 | -6.0 to 6.6 |
| `UCX_SM_Drone_Inventory_01` | the dorsal dome | 65 | 5.8 to 9.4 |
| `UCX_SM_Drone_Inventory_02` | the net pod and muzzle | 72 | -17.7 to -5.5 |

- **How each hull is made:** the exact convex hull of low-poly, circumscribed proxies of its parts, grown 0.3 %. Every
  visual vertex of its group is proved inside it at build: the deepest is 0.05 mm inside.
- **The validator** confirms each hull convex: its volume equals the volume of its own convex hull, and the worst
  face-plane deviation is 0.1 µm. It also confirms every LOD0 vertex inside their union.
- **Together** they span 27 cm, against the sphere's 76, and fill 17.2 % of its volume.

**Ledger hall fit:** with the 38 cm sphere at 550 its top is at 588, 12 cm clear of the ceiling, and its bottom at
512, 62 cm over the shelf tops.

**The maps:** 867 px/m at 2048 (UV coverage 0.35); emissive Mask R on the eye lens and the ledger lines. This is
adequate at gameplay distance; a close-up hero shot would want a 4096 bake or a planar top and bottom unwrap.

**Attempts kept** in `Saved/W18Rebuild/s70_drone_kit.attempt*` and `Saved/InventoryDrone/Archive/`:
- attempt 0: a duplicate vertex passed to the hull's delete;
- attempts 1-3: the eye lens, then the bezel, outside the disc hull by up to 2.2 mm, then 3-10 µm on tangent edges.
  Fixed by the lens and bezel proxies and the 0.3 % growth;
- attempt 4: passing, but visually rejected. The concentric groove banding, a light-grey read under a hot key light,
  and the hero lineup's rig were held at the origin by its baked take;
- attempt 5: the lineup still held by the take.

**My review of the final originals:**
- From the front and three-quarter views it reads as a near-black graphite disc with a cyan eye (iris and pupil), a
  cyan ledger line under its rim, a black-glass dome ringed by the tally-notch sigil, and a net pod with a cyan muzzle.
- The side view shows the eye's brow housing and the angled muzzle.
- The envelope view shows it inside its sphere, today's capsule crossing the ceiling, and the shelf tops a metre
  below.
- The lineup shows it at 1.6 m beside the hero for scale.
- **Open:** the top view keeps a faint trace of the graphite's machining rings near the highlight. The `audit_hound`
  variant has no look of its own yet.
