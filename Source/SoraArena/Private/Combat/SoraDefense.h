#pragma once
#include "CoreMinimal.h"

class AActor;
class ASoraEnemy;
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
// being sheathed or fully sheathed he guards nothing. Once fully sheathed,
// a guard pressed just before a committed cut
// that allows it lands is 無刀取り: he takes the blade and the blow misses.
// 転 (marobashi) rolls him to an opponent's flank: Left or Right with Jump
// within SoraCombatRules::MarobashiWindowMs of an awase on it, or in the
// last stretch of a boss blow whose windup allows it (bosses.json
// marobashi_ms). That blow misses him, and the opponent cannot turn after
// him for SoraCombatRules::MarobashiTurnLagMs.
namespace SoraDefense
{
// ASoraPlayerCharacter::AdmitDamage. Writes Hit.Defense and the damage that
// still reaches the hero; false when none does.
bool AdmitHero(ASoraPlayerCharacter& Hero, float& Damage, FSoraHit& Hit, AActor* Causer);
// The opponent a 転 step would answer now, or null; bAfterAwase says whether
// it follows an awase rather than a blow's windup.
ASoraEnemy* MarobashiTarget(const ASoraPlayerCharacter& Hero, bool* bAfterAwase = nullptr);
// A Jump press with the MoveRight input Side: true, with the step begun,
// when a 転 window is open and Side leans far enough to one side.
bool Marobashi(ASoraPlayerCharacter& Hero, float Side);
}
