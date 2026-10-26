# Ward-gate light correction — directed runtime check

Chapter 3 specifies a permanent charcoal brazier with a four-metre light
radius. Its machine-readable entry previously supplied only an ID, so the
normalizer selected the generic brazier defaults: six metres and a one-second
snuff interaction. The chapter entry now carries the explicit four-metre
radius and `extinguishable: false`; normalization retains that radius and
uses the existing runtime `None` snuff mode. Other lamps retain their defaults.

The new authoring checks cover the generated ward brazier, rejection of
invalid explicit radii, independent extinguish/relight settings and unchanged
defaults. Only chapter 3's generated file changes. These are source/data checks.

`SoraArena.Fieldcraft.WardGateBrazier` checks the actual point-light
radius, absence of a snuff prompt, held player interaction and the lamp damage
interface, followed by snuffing the nearby andon. Threats are held to isolate
the light contract. The editor compiled and this case passed at signed
`25789bc5`, with no test errors or warnings. Source, Config and Generated
inputs were unchanged. The enclosing run had a separate melee-fixture failure;
it is retained as failed, not relabeled as a passing run. See
[runtime evidence](landing-melee-runtime-2026-10-26.md).

The complete ward-gate encounter remains unfinished. A focused review at
`a8f6455b` found these separate gaps:

- Runtime space still uses a generic zone, two rectangular patrol routes and
  generated interaction positions. The authored gate at X −62 m, 18 × 14 m
  exterior plaza, posts and 40/50-second routes are retained in the raw layout
  but are not the runtime geometry/routes.
- The scanner's raw `on_enter: alert` hazard is not normalized into an active
  fieldcraft sensor. Its light remains a generic strip lamp, including the
  default snuff behavior; changing the brazier does not implement the scanner.
- The running-water noise multiplier exists, but its generated floor patch
  does not establish the authored 0.9-metre crouch-only culvert.
- A 3.2-metre ladder/roof and 900 cm drop-noise/straw mechanics already exist.
  Their generated positions do not establish the authored route across the
  gate fence and firewall.
- C1's twelve-second turn and the conscripts' 0.7 suspicion multiplier are
  normalized. General nonlethal knockdown and held seal cutting also exist.
  Guard identity is not retained by the generic guard row, and its freed cue
  emits `conscript_freed`; the authored `npc_freed:kidoban` dialogue and a
  physical wicket-bar release still need a concrete binding.

These are source findings, not reproduced ordinary-play failures. Completion
requires the authored physical routes, scanner/wicket behavior, patrol timing,
real input traversal and detection/retry checks, followed by final art and
ordinary stealth play. The existing assisted campaign is not that evidence.
