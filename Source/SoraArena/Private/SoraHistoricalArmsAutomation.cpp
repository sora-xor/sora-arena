#include "SoraCatalog.h"
#include "SoraHistoricalArms.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraHistoricalArmsCatalogTest,
    "SoraArena.Campaign.HistoricalArmsCatalog",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraHistoricalArmsCatalogTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    FSoraCatalog& Catalog=FSoraCatalog::Get();
    if(!TestTrue(TEXT("Offline catalog loads in Unreal"),Catalog.Load())) return false;

    TestEqual(TEXT("Arena weapon table remains separate"),Catalog.Weapons.Num(),18);
    TestEqual(TEXT("Historical campaign-only arms"),Catalog.CampaignWeapons.Num(),3);
    const FSoraHero& Hero=Catalog.Hero();
    TestEqual(TEXT("Protagonist Japanese name"),Hero.NameJapanese,FString(TEXT("ニャーコト")));
    TestEqual(TEXT("Protagonist English name"),Hero.NameEnglish,FString(TEXT("Nyaakoto")));
    TestEqual(TEXT("Starting katana"),Hero.KatanaId,0);
    TestEqual(TEXT("Bow in the campaign inventory"),Hero.YumiId,18);
    TestEqual(TEXT("Quiver count matches bow magazine"),Hero.QuiverArrows,Catalog.Weapon(18).Magazine);

    TestEqual(TEXT("Katana is a standard melee arm"),Catalog.Weapon(0).Kind,FString(TEXT("melee")));
    TestEqual(TEXT("Yumi fires arrows"),Catalog.Weapon(18).Kind,FString(TEXT("bow")));
    TestEqual(TEXT("Yari is a distinct melee arm"),Catalog.Weapon(19).NameEnglish,FString(TEXT("Yari")));
    TestEqual(TEXT("Naginata is a distinct melee arm"),Catalog.Weapon(20).NameEnglish,FString(TEXT("Naginata")));
    for(int32 Id=18;Id<=20;++Id)
    {
        const FSoraWeapon& Arm=Catalog.Weapon(Id);
        TestEqual(*FString::Printf(TEXT("Offline arm %d belongs to Nyaakoto"),Id),Arm.ClassId,0);
        TestFalse(*FString::Printf(TEXT("Offline arm %d is not an NFT entitlement"),Id),Arm.Special);
    }

    using namespace SoraHistoricalArms;
    const FProfile Sword=Profile(EForm::Katana);
    const FProfile Spear=Profile(EForm::Yari);
    const FProfile Poleblade=Profile(EForm::Naginata);
    TestTrue(TEXT("Katana catalog and committed timing agree"),
        FMath::IsNearlyEqual(Catalog.Weapon(0).Cooldown,Sword.WindupSeconds+Sword.RecoverySeconds));
    TestTrue(TEXT("Yari catalog and reach agree"),
        FMath::IsNearlyEqual(Catalog.Weapon(19).Range,Spear.MaximumDistanceCm));
    TestTrue(TEXT("Naginata catalog and reach agree"),
        FMath::IsNearlyEqual(Catalog.Weapon(20).Range,Poleblade.MaximumDistanceCm));
    TestTrue(TEXT("Sword contact at useful distance"),CanStrike(EForm::Katana,110.f,1.f));
    TestFalse(TEXT("Crowded spear thrust cannot score"),CanStrike(EForm::Yari,80.f,1.f));
    TestFalse(TEXT("Sideways spear thrust cannot score"),CanStrike(EForm::Yari,260.f,.7f));
    TestFalse(TEXT("Long poleblade cut cannot score behind"),CanStrike(EForm::Naginata,245.f,-.8f));
    TestTrue(TEXT("Timed frontal parry"),DefendBlade(true,.9f,180,35.f)==EDefense::Parry);
    TestTrue(TEXT("Sustained guard"),DefendBlade(true,.9f,500,35.f)==EDefense::Guard);
    TestTrue(TEXT("Guard fails behind"),DefendBlade(true,-.9f,180,35.f)==EDefense::Exposed);
    TestTrue(TEXT("Spent guard fails"),DefendBlade(true,.9f,180,10.f)==EDefense::Exposed);
    TestTrue(TEXT("Sword retainer withdraws when crowded"),RetainerFootwork(50.f)==EFootwork::Withdraw);
    TestTrue(TEXT("Sword retainer closes outside maai"),RetainerFootwork(220.f)==EFootwork::Close);
    TestTrue(TEXT("Sword retainer retains a telegraphed opening"),RetainerWindupSeconds>Sword.WindupSeconds);
    UE_LOG(LogTemp,Display,TEXT("SORA_HISTORICAL_ARMS_CATALOG_OK: hero=%s arms=katana/yumi/yari/naginata arena_weapons=%d"),
        *Hero.NameEnglish,Catalog.Weapons.Num());
    return !HasAnyErrors();
}
#endif
