#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraWoodAutomation.h"
#include "SoraCatalogWood.h"
#include "Dom/JsonObject.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

namespace
{
bool ReloadWood(SoraFieldcraftAutomation::FBeatWorld& W)
{
    W.Fieldcraft()->OnEvent.Remove(W.EventsHandle);
    if(!W.World->DestroyTestWorld(true)) return false;
    W.World->ForwardErrorMessages(&W.Test); W.World.Reset();
    W.World=MakeUnique<FSoraAutomationWorld>();
    return W.World->Start(W.Slot)&&W.Tick(1)&&W.World->EnableKeyInput()&&
        W.Press(EKeys::Enter)&&W.Press(EKeys::Enter)&&W.Press(EKeys::Enter)&&W.Tick(30);
}
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraWoodExploreTest,"SoraArena.Campaign.WoodExplore",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraWoodExploreTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if(!TestTrue(TEXT("Catalog loads the separate wood contract"),FSoraCatalog::Get().Load())) return false;
    SoraFieldcraftAutomation::FBeatWorld W(*this,TEXT("WoodExplore"),0,7);
    if(!W.Start()||!W.Tick(30)||!W.Press(EKeys::E)) return false;
    auto* C=W.Campaign();
    TestEqual(TEXT("Entering wood and remote Interact collect nothing"),C->WoodPoiMask(),0);
    TestEqual(TEXT("Entering wood does not complete it"),C->Progress().CompletedMask&SoraBeatRules::BeatBit(7),0u);
    if(!TestTrue(TEXT("Actual walking and Interact inspect the stone"),SoraWoodAutomation::Poi(*W.World,SoraWoodRules::Stone))) return false;
    auto* Saved=Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(W.Slot,0));
    if(!TestNotNull(TEXT("Stone discovery is immediately saved"),Saved)) return false;
    TestEqual(TEXT("Stone grants c01 alone"),Saved->Collectibles,static_cast<int64>(1));
    TestEqual(TEXT("Stone does not grant c02, vista, shrine or toshiya"),Saved->WoodPoiMask,SoraWoodRules::Bit(SoraWoodRules::Stone));
    if(!W.Tick(240)||!W.Press(EKeys::E)||!ReloadWood(W)) return false;
    C=W.Campaign();
    TestEqual(TEXT("Fresh-world retry retains only the discovered stone"),C->WoodPoiMask(),SoraWoodRules::Bit(SoraWoodRules::Stone));
    TestTrue(TEXT("Optional checkpoint remains the unfinished wood"),C->IsWoodExplore());
    if(!SoraWoodAutomation::Poi(*W.World,SoraWoodRules::Boundary)||!SoraWoodAutomation::Poi(*W.World,SoraWoodRules::Shrine)||
        !SoraWoodAutomation::Poi(*W.World,SoraWoodRules::Vista)) return false;
    if(!W.Tick(240)||!W.Press(EKeys::One)||!W.Hold(EKeys::LeftMouseButton,50)) return false;
    TestFalse(TEXT("A real melee attack at the vista grants no clapper reward"),C->HasToshiyaCodex());
    const auto Vista=C->ActiveChapter()->Wood.Pois[SoraWoodRules::Vista];
    if(!SoraWoodAutomation::Walk(*W.World,Vista+FVector2D(0,300))||
        !SoraWoodAutomation::Arrow(*this,*W.World,true,false)) return false;
    TestFalse(TEXT("A shot released outside the vista cannot claim the challenge"),C->HasToshiyaCodex());
    if(!SoraWoodAutomation::Arrow(*this,*W.World,false)) return false;
    TestFalse(TEXT("A real vista arrow that misses grants no codex"),C->HasToshiyaCodex());
    if(!SoraWoodAutomation::Arrow(*this,*W.World,true)) return false;
    if(!TestTrue(TEXT("Only the actual vista arrow impact unlocks toshiya"),C->HasToshiyaCodex())) return false;
    TestFalse(TEXT("The clapper never completes the wood"),(C->Progress().CompletedMask&SoraBeatRules::BeatBit(7))!=0);
    Saved=Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(W.Slot,0));
    if(!TestNotNull(TEXT("Codex reward has a durable separate ledger"),Saved)) return false;
    TestEqual(TEXT("Only the two authored collectible bits are granted"),Saved->Collectibles,static_cast<int64>(3));
    TestEqual(TEXT("Four independent POIs and the challenge are recorded"),Saved->WoodPoiMask,SoraWoodRules::All);
    if(!ReloadWood(W)) return false;
    C=W.Campaign();
    TestTrue(TEXT("Fresh-world reload retains the separate toshiya codex"),C->HasToshiyaCodex());
    TestTrue(TEXT("Sourced Toshiya history remains accessible after reload"),
        C->ToshiyaCodex(true).Contains(TEXT("Keichō 11 (1606)"))&&C->ToshiyaCodex(true).Contains(TEXT("51 arrows through from 100 shots"))&&
        C->ToshiyaCodex(false).Contains(TEXT("百本のうち五十一本")));
    const int32 Notices=C->StoryNotices().Num();
    if(!SoraWoodAutomation::Arrow(*this,*W.World,true)) return false;
    TestTrue(TEXT("A repeated real clapper hit creates no second reward notice"),C->StoryNotices().Num()<=Notices);
    if(!TestTrue(TEXT("Walking the authored exit then bridge reaches b09"),SoraWoodAutomation::Exit(*W.World))) return false;
    TestTrue(TEXT("Only exit arrival completes b08"),(C->Progress().CompletedMask&SoraBeatRules::BeatBit(7))!=0);
    TestEqual(TEXT("B09 still depends on b07 alone"),C->ActiveChapter()->Rules[8].RequiresMask,SoraBeatRules::BeatBit(6));
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraWoodExitOnlyTest,"SoraArena.Campaign.WoodExitOnly",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraWoodExitOnlyTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    SoraFieldcraftAutomation::FBeatWorld W(*this,TEXT("WoodExitOnly"),0,7);
    if(!W.Start()||!W.Tick(30)||!SoraWoodAutomation::Exit(*W.World)) return false;
    auto* C=W.Campaign();
    TestTrue(TEXT("The trail exit completes b08 without requiring discoveries"),(C->Progress().CompletedMask&SoraBeatRules::BeatBit(7))!=0);
    TestEqual(TEXT("Exit does not grant any POI or clapper reward"),C->WoodPoiMask(),0);
    auto* Saved=Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(W.Slot,0));
    if(!TestNotNull(TEXT("Exit and bridge save b09"),Saved)) return false;
    TestEqual(TEXT("Exit grants neither c01 nor c02"),Saved->Collectibles,static_cast<int64>(0));
    TestEqual(TEXT("Smithy checkpoint is saved"),Saved->CheckpointBeat,8);
    TestFalse(TEXT("Completed wood has no stale junction choice flag"),Saved->WoodJunction);
    if(!ReloadWood(W)) return false;
    TestEqual(TEXT("Fresh reload retains normal smithy arrival"),W.Campaign()->ActiveBeat(),8);
    TestTrue(TEXT("Fresh reload retains the independent optional exit"),(W.Campaign()->Progress().CompletedMask&SoraBeatRules::BeatBit(7))!=0);
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraWoodLoaderTest,"SoraArena.Campaign.WoodLoader",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraWoodLoaderTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    FString Text;
    if(!TestTrue(TEXT("Read the real generated chapter"),FFileHelper::LoadFileToString(Text,
        *FPaths::Combine(FPaths::ProjectContentDir(),TEXT("Data/campaign/chapter_01.json"))))) return false;
    const auto Check=[&](TFunction<void(FJsonObject&)> Mutate,bool Accepted)
    {
        TSharedPtr<FJsonObject> Data;
        if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Data)) return false;
        Mutate(*Data);
        FSoraChapter Copy=FSoraCatalog::Get().Chapter(0); Copy.Wood={};
        return TestEqual(TEXT("Actual wood reader accepts only its typed physical contract"),SoraCatalogWood::Read(*Data,Copy),Accepted);
    };
    Check([](FJsonObject&){},true);
    for(const TCHAR* Field:{TEXT("distance_cm"),TEXT("face_cm"),TEXT("entry"),TEXT("naruko"),TEXT("trail"),TEXT("pois")})
        Check([Field](FJsonObject& D){D.GetObjectField(TEXT("space"))->GetObjectField(TEXT("wood"))->SetBoolField(Field,true);},false);
    Check([](FJsonObject& D){D.GetObjectField(TEXT("space"))->GetObjectField(TEXT("wood"))->SetNumberField(TEXT("distance_cm"),4499);},false);
    Check([](FJsonObject& D){D.GetObjectField(TEXT("space"))->RemoveField(TEXT("wood"));},false);
    return !HasAnyErrors();
}
#endif
