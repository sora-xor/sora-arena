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
    assert(DefendBlade(true, .9f, 180, 35.f) == EDefense::Parry);
    assert(DefendBlade(true, .9f, 500, 35.f) == EDefense::Guard);
    assert(DefendBlade(true, -.9f, 180, 35.f) == EDefense::Exposed);
    assert(DefendBlade(true, .9f, 180, 10.f) == EDefense::Exposed);
    assert(DefendBlade(false, .9f, 180, 35.f) == EDefense::Exposed);
    assert(RetainerFootwork(50.f) == EFootwork::Withdraw);
    assert(RetainerFootwork(130.f) == EFootwork::Hold);
    assert(RetainerFootwork(220.f) == EFootwork::Close);
    assert(RetainerWindupSeconds > Katana.WindupSeconds);
    assert(RetainerRecoverySeconds > Katana.RecoverySeconds);
}
