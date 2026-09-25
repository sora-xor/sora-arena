#pragma once
#include "CoreMinimal.h"

class AActor;
class ASoraPlayerCharacter;
struct FSoraHit;

// Nyaakoto's side of a hit. In chapter one a raised guard takes a sparring
// pupil's whole cut and the dojo lessons record it; a fresh one meets the cut
// and staggers the pupil. Afterwards his blade's guard meets every attacker
// by SoraCombatRules::Defend: a parry stops a blade, retainer's, pupil's,
// shield enforcer's, conscript's, automaton's or the collector's cleave alike,
// and staggers its attacker; a held guard takes the attack's chip; bullets,
// arrows and blasts from the front are halved; his own blast is never guarded.
// A landed heavy blow may push him back or stagger him. With his blade
// sheathed he guards nothing, but a guard pressed just before a committed cut
// that allows it lands is 無刀取り: he takes the blade and the blow misses.
namespace SoraDefense
{
// ASoraPlayerCharacter::AdmitDamage. Writes Hit.Defense and the damage that
// still reaches the hero; false when none does.
bool AdmitHero(ASoraPlayerCharacter& Hero, float& Damage, FSoraHit& Hit, AActor* Causer);
}
