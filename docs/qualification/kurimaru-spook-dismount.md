# Kurimaru's cargo-ride spook dismount

The ch04.b14 fail paragraph explicitly says that Kurimaru spooking or being
netted dismounts the rider, permits foot continuation, and retains the
three-second whistle. This is distinct from §6.4's one-second lead tug when
the pack mare Bunta is frightened.

The chapter's YAML now states `on_spook: dismount_continue`. Mount
normalization emits `spook_dismount` for every mount, true only for ch04.b14.
An absent policy means `shy`, preserving the other seven mounts. Author and
catalog validation reject invalid policy values, missing or mismatched
normalized flags, or dismount policies without a fearful cargo mount, a led
pack horse, permitted dismount and foot continuation. `on_horse_down` alone
does not imply this behavior: the chapter-two convoy also continues on foot
after a net, but its ordinary spook remains a shy.

Enemy proximity, scripted volumes, road searchlights and nearby net impacts
already call `ASoraHorse::Spook()`. The horse records one onset only when its
mounted ride state actually changes from calm to spooked. A sub-millisecond
tick retains a pending request until a whole-millisecond step can consume it.
The director consumes the onset once, independently of which actor ticks
first. The notice belongs to the current mounted lifecycle and is cleared
by placement/recall, dismount, remount and ride setup. A led mare's fear does
not create this own-spook notice.

The existing rooted/net branch runs first and retains its thrown damage. The
new pure-spook branch dismounts without applying damage and raises the
existing `horse_down` continuation event. It does not discard cargo, change
delivery counts, require the pack horse near unloading, or alter the
chapter-one pheasant lesson. The existing whistle deadline uses paused
world time and remains three seconds; no alternative recall clock is added.

`SoraArena.Campaign.KurimaruSpookDismount` is the new runtime selector. It
forces both legal horse/director tick orders, positions a real authored
drone inside Kurimaru's radius but outside Bunta's, checks damage-free
dismount and no replay on immediate ordinary remount, then uses mapped
walking, Interact, pause and retry controls. Recall must occur no earlier
than three active world seconds and no later than one frame plus 1 ms.
The hero then completes a full foot unload after an actual spook dismount.
A separate simultaneous-net case establishes the existing 15 HP thrown
damage still takes priority. The production root effect is injected only
in that net-priority isolation case; it is not a projectile accuracy test.

The fixture remains assisted. Initial horse placement enters the authored
toll volume, choosing a point clear of authored spawn positions, to release
its registered wave with the policy active. Opponents are frozen and their
real drone is repositioned for controlled proximity. Later setup places the
horses outside Kami's unload radius. Health, damage constants, collisions,
normal movement and task credit are unchanged. Existing Bunta, mount,
cargo, convoy, searchlight, horse-down and campaign playthrough selectors
remain necessary regression checks.

This candidate has source/host validation only. Unreal compilation, the new
selector and the existing runtime regressions require the root's actual
engine test lane; no runtime success is claimed here.
