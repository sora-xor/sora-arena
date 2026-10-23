#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraCampaignRules.h"
#include "SoraWorldBuilder.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraRecoveryCacheTest,"SoraArena.Campaign.RecoveryCache",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraRecoveryCacheTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    SoraFieldcraftAutomation::FBeatWorld W(*this,TEXT("RecoveryCache"),2,4);
    if(!W.Start()) return false;
    W.Harden();
    auto* Campaign=W.Campaign();
    const auto& Chapter=FSoraCatalog::Get().Chapter(2);
    const int32 Cache=Chapter.BeatIndex(TEXT("ch03.b04"));
    if(!TestTrue(TEXT("The optional archive is available before equipment recovery"),
        Campaign->NeedsEquipmentRecovery()&&Campaign->AvailableCaches().Contains(Cache))) return false;
    W.Stand(Campaign->CacheLocation(Cache));
    if(!W.Press(EKeys::E)) return false;
    TestTrue(TEXT("Ordinary Interact opens the available cache"),
        (Campaign->Progress().CompletedMask&SoraBeatRules::BeatBit(Cache))!=0u);
    for(const int32 Reward:Chapter.Beats[Cache].Rewards)
        TestTrue(TEXT("The archive grants its authored collectible"),
            (Campaign->CollectedMask()&SoraCampaignRules::CollectibleBit(2,Chapter.Collectibles[Reward].MaskBit))!=0ull);
    TestTrue(TEXT("Opening a cache does not recover the hidden weapons"),Campaign->NeedsEquipmentRecovery());
    TestFalse(TEXT("The katana remains unavailable"),Campaign->CanHold(0,false));
    const auto* Space=Campaign->ActiveSpace();
    if(!TestTrue(TEXT("The guarded hoist has its pickup"),Space&&!Space->Pickups.IsEmpty())) return false;
    W.Stand(ASoraWorldBuilder::Floor(Space->Pickups[0]));
    if(!W.World->InjectKey(EKeys::E,IE_Pressed)||!W.Tick(240)||
        !W.World->InjectKey(EKeys::E,IE_Released)) return false;
    TestFalse(TEXT("Holding the hoist before retrieval takes no load"),Campaign->TaskProgress().Carrying);
    TestEqual(TEXT("No recovery requirement or delivery is bypassed"),Campaign->TaskProgress().Done,0);
    TestTrue(TEXT("Equipment recovery is still mandatory"),Campaign->NeedsEquipmentRecovery());
    return true;
}
#endif
