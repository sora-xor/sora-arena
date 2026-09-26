#include "SoraHistoricalArms.h"
#include <cassert>

using namespace SoraHistoricalArms;

int main()
{
    const FProfile Katana = Profile(EForm::Katana);
    const FProfile Yari = Profile(EForm::Yari);
    const FProfile Naginata = Profile(EForm::Naginata);

    // A cut has a useful interval and a post-commitment recovery. The spear
    // covers farther ground, but loses useful point control when crowded.
    assert(CanStrike(EForm::Katana, 110.f, 1.f));
    assert(!CanStrike(EForm::Katana, 40.f, 1.f));
    assert(!CanStrike(EForm::Katana, 210.f, 1.f));
    assert(!CanStrike(EForm::Katana, 110.f, -1.f));
    assert(CanStrike(EForm::Yari, 260.f, .98f));
    assert(!CanStrike(EForm::Yari, 80.f, 1.f));
    assert(!CanStrike(EForm::Yari, 260.f, .75f));
    assert(!CanStrike(EForm::Yari, 290.f, 1.f));
    assert(CanStrike(EForm::Naginata, 245.f, .9f));
    assert(!CanStrike(EForm::Naginata, 80.f, 1.f));
    assert(!CanStrike(EForm::Naginata, 245.f, -.9f));
    assert(Yari.MaximumDistanceCm > Naginata.MaximumDistanceCm);
    assert(Naginata.MaximumDistanceCm > Katana.MaximumDistanceCm);
    assert(Katana.WindupSeconds > 0.f && Katana.RecoverySeconds > Katana.WindupSeconds);
    assert(Yari.WindupSeconds > Katana.WindupSeconds);
    assert(Naginata.RecoverySeconds > Yari.RecoverySeconds);
    assert(RetainerFootwork(50.f) == EFootwork::Withdraw);
    assert(RetainerFootwork(130.f) == EFootwork::Hold);
    assert(RetainerFootwork(220.f) == EFootwork::Close);

    // Every melee arm strikes with commitment; nothing else does. Heavy arms
    // weigh more against an opponent's poise, and the short blades are quickest.
    const int Melee[] = {0, 2, 4, 6, 8, 10, 12, 19, 20};
    int Count = 0;
    for (int Id = 0; Id <= 20; ++Id)
        Count += IsMelee(Id);
    assert(Count == 9);
    for (const int Id : Melee)
    {
        const FProfile P = Profile(FormFor(Id));
        assert(IsMelee(Id));
        assert(P.WindupSeconds > 0.f && P.RecoverySeconds > P.WindupSeconds);
        assert(P.MinimumDistanceCm < P.MaximumDistanceCm && P.StaggerMs > 0);
        assert(CanStrike(FormFor(Id), (P.MinimumDistanceCm + P.MaximumDistanceCm) * .5f, 1.f));
        assert(!CanStrike(FormFor(Id), P.MaximumDistanceCm + 1.f, 1.f));
    }
    assert(!IsMelee(1) && !IsMelee(7) && !IsMelee(18));
    assert(FormFor(0) == EForm::Katana && FormFor(19) == EForm::Yari && FormFor(20) == EForm::Naginata);
    assert(Profile(EForm::Kanabo).StaggerMs >= 800 && Profile(EForm::ForgeHammer).StaggerMs >= 800);
    assert(Profile(EForm::Katana).StaggerMs < Profile(EForm::Kanabo).StaggerMs);
    assert(Profile(EForm::Tanto).WindupSeconds < Katana.WindupSeconds);
    assert(Profile(EForm::Wakizashi).WindupSeconds < Katana.WindupSeconds);
    assert(Profile(EForm::MonofilamentNaginata).MaximumDistanceCm > Yari.MaximumDistanceCm);
}
