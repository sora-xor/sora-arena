#include "SoraCatalog.h"
#include "SoraCombatRules.h"
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
    // Every melee arm, Nyaakoto's and each class's, strikes with commitment:
    // its windup and recovery make up its catalog cooldown, and its useful
    // distance ends at its catalog range.
    int32 MeleeArms=0;
    for(int32 Id=0;Id<=20;++Id)
    {
        const FSoraWeapon& Arm=Catalog.Weapon(Id);
        TestEqual(*FString::Printf(TEXT("Weapon %d is melee exactly when it strikes with commitment"),Id),
            Arm.Kind==TEXT("melee"),IsMelee(Id));
        if(!IsMelee(Id)) continue;
        ++MeleeArms;
        const FProfile Handling=Profile(FormFor(Id));
        TestTrue(*FString::Printf(TEXT("Weapon %d catalog cooldown is its windup and recovery"),Id),
            FMath::IsNearlyEqual(Arm.Cooldown,Handling.WindupSeconds+Handling.RecoverySeconds,.001f));
        TestTrue(*FString::Printf(TEXT("Weapon %d catalog range is its useful distance"),Id),
            FMath::IsNearlyEqual(Arm.Range,Handling.MaximumDistanceCm));
        TestTrue(*FString::Printf(TEXT("Weapon %d has a windup, a recovery and a weight"),Id),
            Handling.WindupSeconds>0.f&&Handling.RecoverySeconds>Handling.WindupSeconds&&Handling.StaggerMs>0&&
            Handling.MinimumDistanceCm<Handling.MaximumDistanceCm);
    }
    TestEqual(TEXT("Six class blades, the monofilament naginata and Nyaakoto's yari and naginata"),MeleeArms,9);
    TestTrue(TEXT("Sword contact at useful distance"),CanStrike(EForm::Katana,110.f,1.f));
    TestFalse(TEXT("Crowded spear thrust cannot score"),CanStrike(EForm::Yari,80.f,1.f));
    TestFalse(TEXT("Sideways spear thrust cannot score"),CanStrike(EForm::Yari,260.f,.7f));
    TestFalse(TEXT("Long poleblade cut cannot score behind"),CanStrike(EForm::Naginata,245.f,-.8f));
    namespace Combat=SoraCombatRules;
    const Combat::FAttack Cut{Combat::EHit::Melee,22,true,6,30,Combat::ParryStaggerMs,false};
    TestTrue(TEXT("Timed frontal parry"),Combat::Defend({true,180,35,900},Cut).Defense==Combat::EDefense::Parry);
    TestTrue(TEXT("Sustained guard"),Combat::Defend({true,500,35,900},Cut).Defense==Combat::EDefense::Guard);
    TestTrue(TEXT("Guard fails behind"),Combat::Defend({true,180,35,-900},Cut).Defense==Combat::EDefense::Exposed);
    TestTrue(TEXT("Spent guard fails"),Combat::Defend({true,180,10,900},Cut).Defense==Combat::EDefense::Exposed);
    TestTrue(TEXT("Sword retainer withdraws when crowded"),RetainerFootwork(50.f)==EFootwork::Withdraw);
    TestTrue(TEXT("Sword retainer closes outside maai"),RetainerFootwork(220.f)==EFootwork::Close);
    UE_LOG(LogTemp,Display,TEXT("SORA_HISTORICAL_ARMS_CATALOG_OK: hero=%s arms=katana/yumi/yari/naginata arena_weapons=%d"),
        *Hero.NameEnglish,Catalog.Weapons.Num());
    return !HasAnyErrors();
}
#endif
