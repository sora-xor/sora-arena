# Ledger alarm and C3 shutter — implementation checkpoint

The chapter-six contract calls for two riflemen from each entrance and a C3
shutter closed for 30 seconds after the alarm is raised. Previously, detection
released the wave immediately, spawn identities were discarded, and no shutter
existed. This change preserves the authored distinction between detection and
alarm, admits the exact four-member wave/effect contract, and assigns each
member a distinct position behind its north or south entrance.

The north pair enters through the existing palace-link doorway. A 2.7 m south
door and enclosed 3 m service bay provide floor and an actual entrance for the
south pair. These are implementation dimensions where the chapter gives only
an entrance identity; the 24 × 64 × 6 m hall, five 3.2 m aisles, shelves and
5.5 m drone flight plane are unchanged. The service door retracts on alarm.

A construction shutter at C3, y=44 m, changes its hanging length below its
fixed ceiling edge. Its collision stays enabled. It stops for any pawn below
it, resumes when clear, holds fully closed for 30 active game seconds, then
retracts. Pause stops its clock; a duplicate alarm cannot restart it or spawn
another wave; retry restores the original state. Final slatted construction,
motor/alarm recordings and ordinary stealth difficulty remain unfinished.

## Evidence and limits

All 59 CPU gameplay gates passed on the frozen working input based on
`ed9c39e561966bb8817bac18ca48a5c4a6275828`. Inputs were unchanged throughout.
The ledger tests additionally exercise supported entrance paths, rejected
wave/effect mutations, and the compiled C++ obstruction/hold/reopen clock.
Evidence: `Saved/Qualification/2026-10-26/ledger-lockdown-working-source-attempt1`;
review SHA-256 `cda6209ef06a98f46633fa5951cbc6ab8cbc29684ba5bde9c799a5d03199d2f9`.

At signed `47b49669`, `SoraArena.Campaign.LedgerLockdown` **builds and passes**.
It holds original patrol AI, raises the real stealth alarm, observes four live
riflemen entering through their doors, then holds them while testing actual
shutter collision, obstruction, mapped walking, pause, 30-second hold and
retry. LedgerPatrols, LedgerRoute, PalaceFusuma and Spaces also pass in the
same 27-filter run. It has 25 passes and two separate failures (Playthrough
and ConvoyNets); review SHA-256
`58e08bc7cbdc71695417063c817543aefe60509ad826a3ddef1f4e0412c63bb3`.
This is functional fixture evidence, not ordinary stealth or visual acceptance.
