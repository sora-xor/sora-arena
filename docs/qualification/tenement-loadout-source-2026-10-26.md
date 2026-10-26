# Chapter-three carried equipment: source checkpoint

The dry-well pickup previously changed `EquipmentRecovered` into permission for
every earlier unlocked weapon, and b06 onward had an unrestricted equipment mask.
That did not match the chapter's loadout table or the kitchen supply contract.

Recovery now permits only the three arms actually in the bundle: katana (0),
wakizashi (4) and yumi (18). Generated carrying masks retain those arms through
b08, add weapon 7 at b09, and add yari (19) from b14 onward. Earlier earned weapon
unlocks remain unchanged. During b14 itself, the yari becomes available after
successful ordinary Interact at the manager's supply crate. Failed/cooldown,
distant and menu interactions cannot collect it; full ammunition does not prevent
collection. Retrying b14 restores its entry state and requires collecting the
optional yari again. Later beats use the authored post-supply carrying mask.

The supply hint and confirmation explain the yari pickup alongside the existing
ammunition refill. Normal polearm selection then uses the existing arms wheel and
group key. No new weapon entitlement or health is granted. The chapter data is
regenerated from its authored document; the timber binding updates only that
chapter's digest, with placements and coverage unchanged.

Host coverage checks the complete recovery weapon mask, every chapter-three
phase's generated carrying set, and rejects changed supply slots/refills or a
different b09 handoff. The compiled eight-chapter rules and campaign validator
pass. Existing warnings about the ch02 b10/b13 ideal timing overruns remain.

The Unreal recovery fixture now checks every arm after the actual bundle pickup.
The kitchen supply fixture adds ordinary polearm input, actual defeat/retry and
full-ammunition collection. `SoraArena.Campaign.Tenements.Loadout` checks five
checkpoint phases. These new/changed runtime assertions and compilation are
**pending**. Earlier runtime results predate this change. The next combined
selection also retains `SoraArena.Campaign.InfiltrationLoadout` because the shared
equipment rule changed. No ordinary play, current package or release acceptance
is established here.
