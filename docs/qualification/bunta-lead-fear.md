# Bunta's fear and lead-rope steering

Chapter four §6.4 specifies a 900 cm cyan-light fear radius for the led pack
mare, 2.5 seconds of recovery, and one second of interrupted steering for
Kurimaru. The normalized b14 mount already supplies the radius and recovery;
the steering duration comes from that prose contract.

Bunta now measures living campaign opponents and active fieldcraft light
spots from her own position. Entering any such source starts recovery once.
Remaining inside the combined radius cannot restart it indefinitely; leaving
and returning after recovery starts a new encounter. Re-entry during recovery
does not extend it. During fear her catch-up pace is capped at a walk. Her
leader keeps forward/rein control but loses manual and automatic steering for
one active second. Dismount and recall clear that tug; an unmounted rider
cannot bank a tug for a later mount. The leader relationship persists on foot.

Both timers use fresh fractional millisecond clocks. The event's world frame
is excluded because its elapsed delta precedes the event. Paused gameplay
advances neither timer. A frame that consumes the last steering millisecond
still belongs to the interruption; steering resumes on the next frame.
Checkpoint retry recreates the horses and both clocks.

The host progression suite checks 30/60/120/144 Hz, sub-millisecond onset,
encounter rearming, non-extension and reset. The source-only candidate adds
`SoraArena.Campaign.BuntaLeadFear` for runtime qualification. It tests manual
and automatic steering at 60/120 Hz, source positions on Bunta's side of the
900 cm boundary while outside Kurimaru's radius, menu pause, dismount,
whistle, remount, retry, and an ordinary three-second unload on foot.
Steering and fear may finish no earlier than 1.0/2.5 active seconds and no
later than one sampled frame plus 1 ms of clock quantization.

The runtime fixture is assisted: it positions the horse in the authored toll
volume to release its real registered wave, freezes opponent AI/movement, and
restores both horses to their starting positions. It then positions the wave's
real cyan drone as the controlled stimulus. A separate heading setup gives
automatic steering a measurable correction. A post-retry setup places the
horse near Kami; the hero dismounts outside unloading reach and walks in.
Health, damage, collision, task credit and movement constants stay intact.
This is control/timing qualification, not a live combat or complete route
playthrough. The actual b14 fixture uses its drone, not a synthetic searchlight.

Unreal compilation and execution remain pending until the root test lane
records an actual result. Host checks do not establish runtime acceptance.

The b14 prose also requires **Kurimaru's own spook to dismount the rider** with
foot continuation and the existing three-second whistle. That is separate
from Bunta's lead-rope tug; its subsequent source implementation and pending
runtime qualification are described in [kurimaru-spook-dismount.md](kurimaru-spook-dismount.md).
Existing net-induced dismount behavior is unchanged. No cargo loss,
pack proximity gate for unloading, extra spook damage, or training-ride
dismount rule is introduced.
