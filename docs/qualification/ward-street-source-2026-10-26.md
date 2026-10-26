# Continuous ward street: source checkpoint

The chapter-three ward previously ended at X −5600 cm with a closed boundary,
while tenement ground began at X −4700 cm. Its exit advanced the beat before
that gap, so normal progression relocated the hero to the tenement checkpoint.

This source adds a 900 × 720 cm ground connection, splits the ward's east wall
around it and retains solid side boundaries. The ward's spatial extent includes
the street. Its exit volume now lies wholly inside the tenements, with its west
edge 100 cm beyond their boundary. Normal progression therefore uses the
existing same-zone behavior without a relocation exception. The tenement entry
is unchanged for checkpoint loads. The gate, scanner, wicket and culvert retain
their dimensions and interactions.

The host geometry tests compile both construction tables. They check continuous
floor, full capsule clearance across the connector's width, no coplanar overlap
at the join, and every exit corner's membership in the next district. Mutations
restore the old exit, truncate the connector or move the spatial exceptions and
must fail admission. Eleven ward tests, sixteen tenement tests and campaign
validation pass. The validator admits only the exact authored connections; its
general separation and wall-count requirements remain for other places.

The three Unreal route fixtures now measure every movement step across the beat
transition, continue onto the tenement street, and check that retry uses its
checkpoint entry. Additional floor traces cover both joins and the old wall.
These changes have **not been compiled or run in Unreal**. Claude owns the engine
lane for character work. The previous 32-test pass belongs to `ca98e606` and does
not validate this connection. Ordinary play, visuals and release acceptance
remain open.
