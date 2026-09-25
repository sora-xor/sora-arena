#include "Combat/SoraDefense.h"
#include "Combat/SoraDamage.h"
#include "SoraCampaignDirector.h"
#include "SoraDojoRules.h"
#include "SoraEnemy.h"
#include "SoraEquipmentComponent.h"
#include "SoraGameEvents.h"
#include "SoraGameMode.h"
#include "SoraPlayerCharacter.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"

namespace Rules = SoraCombatRules;

namespace
{
// The dojo's guard lesson counts a block from the front half-plane and a little beyond.
constexpr int32 DojoFacingMilli = 250;

void Announce(USoraGameEvents* Events, bool bParried, ASoraPlayerCharacter& Hero, AActor* Causer, int32 HeldMs, float Damage, bool bDojo)
{
    if (!Events)
        return;
    FSoraDefenseEvent Defense;
    Defense.Defender = &Hero; Defense.Attacker = Causer; Defense.HeldMs = HeldMs; Defense.Damage = Damage; Defense.bDojo = bDojo;
    (bParried ? Events->OnParried : Events->OnGuarded).Broadcast(Defense);
}
}

bool SoraDefense::AdmitHero(ASoraPlayerCharacter& Hero, float& Damage, FSoraHit& Hit, AActor* Causer)
{
    USoraEquipmentComponent* Kit = Hero.GetEquipment();
    USoraGameEvents* Events = USoraGameEvents::Get(&Hero);
    const int32 HeldMs = FMath::RoundToInt32((Hero.GetWorld()->GetTimeSeconds() - Kit->GuardPressedAt()) * 1000.f);
    const FVector From = Hit.bHasOrigin ? Hit.Origin : Causer ? Causer->GetActorLocation() : Hero.GetActorLocation();
    const int32 Facing = SoraDamage::FacingMilli(Hero, From);
    ASoraEnemy* Opponent = Cast<ASoraEnemy>(Causer);
    if (Hero.IsDojoTraining())
    {
        // Chapter one: the raised guard takes a sparring cut whole, and the
        // lesson in progress records it.
        if (!Kit->IsGuardHeld() || !Opponent || !Opponent->IsDojoPupil() || Facing < DojoFacingMilli)
            return true;
        if (auto* Mode = Cast<ASoraGameMode>(UGameplayStatics::GetGameMode(&Hero)))
        {
            if (Mode->Campaign()->DojoLessonStage() == 2)
                Mode->Campaign()->RecordDojoLesson(SoraDojoRules::EAction::Parry, HeldMs, true);
            else if (Mode->Campaign()->DojoLessonStage() == 1)
                Mode->Campaign()->RecordDojoLesson(SoraDojoRules::EAction::Guard, HeldMs, true);
        }
        // 合わせ: a guard raised just before the cut staggers the pupil.
        const bool bParried = HeldMs >= 0 && HeldMs <= SoraDojoRules::ParryWindowMs;
        Hit.Defense = bParried ? Rules::EDefense::Parry : Rules::EDefense::Guard;
        if (bParried)
            Opponent->Stagger(Hit.ParryStaggerMs);
        Announce(Events, bParried, Hero, Causer, HeldMs, 0.f, true);
        return false;
    }
    // 無刀取り: sheathed, a guard pressed just before a committed cut lands
    // takes the blade, and none of the blow. A sheathed hand guards nothing else.
    const bool bSheathed = Kit->IsSheathed();
    if (Opponent && Rules::MutoDori(Hit.MutoWindowMs > 0, bSheathed, Kit->IsGuardHeld(), HeldMs, Hit.MutoWindowMs, Facing) &&
        Opponent->Disarm(&Hero))
    {
        Hit.Defense = Rules::EDefense::MutoDori;
        Damage = 0.f;
        return false;
    }
    // Nobody guards against his own blast.
    const bool bSelf = SoraDamage::AttackerOf(Causer) == &Hero;
    const Rules::FGuard Guard{Kit->IsGuardHeld() && !bSheathed && Rules::BlastDefensible(bSelf), HeldMs,
        FMath::FloorToInt32(Kit->GuardReserve()), Facing};
    const Rules::FOutcome Outcome = Rules::Defend(Guard, Hit.Attack(FMath::RoundToInt32(Damage)));
    Hit.Defense = Outcome.Defense;
    if (Outcome.Defense != Rules::EDefense::Exposed)
    {
        Kit->SpendGuard(Outcome.Stamina);
        if (Outcome.Defense == Rules::EDefense::Parry && Opponent)
            Opponent->Parried(Outcome.AttackerStaggerMs);
        Announce(Events, Outcome.Defense == Rules::EDefense::Parry, Hero, Causer, HeldMs, Outcome.Damage, false);
        if (Outcome.GuardBroken)
            Kit->Stagger(Rules::GuardBreakMs / 1000.f);
    }
    // A blow that was not parried may still carry its weight.
    if (Hit.Kind == Rules::EHit::Melee && Outcome.Defense != Rules::EDefense::Parry)
    {
        if (Hit.KnockbackCm > 0)
        {
            const FVector Away = (Hero.GetActorLocation() - From).GetSafeNormal2D();
            Hero.LaunchCharacter(Away * Hit.KnockbackCm * 4.f + FVector(0.f, 0.f, 160.f), true, true);
        }
        if (Outcome.Defense == Rules::EDefense::Exposed && Hit.HeroStaggerMs > 0)
            Kit->Stagger(Hit.HeroStaggerMs / 1000.f);
    }
    Damage = Outcome.Damage;
    return Outcome.Damage > 0;
}
