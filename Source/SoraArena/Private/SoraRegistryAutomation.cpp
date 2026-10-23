#if WITH_DEV_AUTOMATION_TESTS
#include "SoraCatalog.h"
#include "SoraCatalogJson.h"
#include "SoraCatalogRegistry.h"
#include "Misc/AutomationTest.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraRegistryDataTest,"SoraArena.Campaign.Registry.Data",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraRegistryDataTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    const int32 Counts[]={1,2,2,4,3,1,1,2};
    for(int32 ChapterIndex=0;ChapterIndex<8;++ChapterIndex)
    {
        const FSoraChapter& Chapter=FSoraCatalog::Get().Chapter(ChapterIndex);
        TestEqual(TEXT("A fresh chapter has no completed goods"),SoraRegistry::Completed(Chapter,ChapterIndex,0u).Num(),0);
        SoraBeatRules::FProgress State{0u,0u,FSoraCatalog::Get().EarlierWeapons(ChapterIndex),
            FSoraCatalog::Get().EarlierMechanics(ChapterIndex),FSoraCatalog::Get().EarlierFlags(ChapterIndex),false};
        int32 Entries=0;
        for(int32 Index=0;Index<Chapter.Beats.Num();++Index)
        {
            if(Chapter.Rules[Index].Optional) continue;
            const FSoraBeat& Beat=Chapter.Beats[Index];
            if(!TestTrue(*Beat.Id,SoraBeatRules::CompleteBeat(State,Chapter.Rules.GetData(),Chapter.Rules.Num(),Index))) return false;
            if(Beat.Registry.IsSet()) ++Entries;
            const auto Rows=SoraRegistry::Completed(Chapter,ChapterIndex,State.CompletedMask);
            TestEqual(*(Beat.Id+TEXT(" adds only its authored goods")),Rows.Num(),Entries);
            for(const FSoraRegistryRow& Row:Rows)
            {
                const bool Inspected=ChapterIndex>4||(ChapterIndex==4&&Index>=Chapter.BeatIndex(TEXT("ch05.b12")));
                TestEqual(TEXT("Split tallies follow the first inspection and exclude returns"),Row.HasSplitTally(),
                    Inspected&&Row.Entry.Mode!=ESoraRegistryMode::RecordOnly);
            }
            if(Beat.Id==TEXT("ch05.b11")) TestEqual(TEXT("Three entries await inspection"),Rows.Num(),3);
            if(Beat.Id==TEXT("ch05.b12")) TestEqual(TEXT("Inspection creates no fourth entry"),Rows.Num(),3);
            if(Beat.Id==TEXT("ch05.b17")) TestEqual(TEXT("Delivery never enters those goods again"),Rows.Num(),3);
            if(Beat.Id==TEXT("ch08.b16")) TestEqual(TEXT("Posting the registry creates no goods"),Rows.Num(),2);
        }
        const auto Rows=SoraRegistry::Completed(Chapter,ChapterIndex,State.CompletedMask);
        TestEqual(TEXT("The chapter page has its authored number of entries"),Rows.Num(),Counts[ChapterIndex]);
        if(ChapterIndex==4&&Rows.Num()==3)
        {
            TestEqual(TEXT("Japanese counter is preserved"),Rows[0].Entry.Japanese(),FString(TEXT("鏃 24本")));
            TestEqual(TEXT("English counter is preserved"),Rows[0].Entry.English(),FString(TEXT("Arrowheads: 24 pieces")));
            TestEqual(TEXT("Firearms name their goods, not a currency"),Rows[1].Entry.Japanese(),FString(TEXT("アーク・カービン 3挺")));
            TestEqual(TEXT("The banner keeps its period counter"),Rows[2].Entry.Japanese(),FString(TEXT("絹幟 1旒")));
        }
        if(ChapterIndex==6&&Rows.Num()==1)
        {
            TestEqual(TEXT("Returns keep their distinct narrative state"),Rows[0].State,ESoraRegistryState::Returned);
            TestEqual(TEXT("430 horse-loads in Japanese"),Rows[0].Entry.Japanese(),FString(TEXT("押収品の返還 430駄")));
            TestEqual(TEXT("430 horse-loads in English"),Rows[0].Entry.English(),FString(TEXT("Seized goods returned: 430 horse-loads")));
        }
    }
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraRegistryInvalidDataTest,"SoraArena.Campaign.Registry.InvalidData",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraRegistryInvalidDataTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    const auto Read=[&](const FString& Registry,const FString& Ext,SoraBeatRules::EType Type,const TCHAR* RideMode=TEXT("cargo"))
    {
        TSharedPtr<FJsonObject> Object;
        const FString Json=TEXT("{\"registry\":")+Registry+TEXT(",\"ext\":")+Ext+
            TEXT(",\"params\":{\"mode\":\"")+RideMode+TEXT("\"}}");
        if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Object)||!Object) return false;
        FSoraBeat Beat; Beat.Task.Type=Type;
        return SoraCatalogRegistry::Read(*Object,Beat);
    };
    const FString Entry=TEXT("{\"item_ja\":\"鏃\",\"item_en\":\"Arrowheads\",\"qty\":24,\"unit_ja\":\"本\",\"unit_en\":\"pieces\"}");
    using SoraBeatRules::EType;
    TestTrue(TEXT("Finished production is accepted"),Read(Entry,TEXT("{}"),EType::ProductionTask));
    TestTrue(TEXT("Cargo delivery is accepted"),Read(Entry,TEXT("{}"),EType::HorsebackRide));
    TestTrue(TEXT("Record-only return is accepted"),Read(Entry,TEXT("{\"registry_mode\":\"record_only\"}"),EType::ProductionTask));
    TestTrue(TEXT("No entry on a cinematic is accepted"),Read(TEXT("null"),TEXT("{}"),EType::Cinematic));
    for(const TCHAR* Qty:{TEXT("0"),TEXT("-1"),TEXT("true"),TEXT("1.5"),TEXT("\"24\""),TEXT("2147483648")})
        TestFalse(TEXT("Malformed counts are refused"),Read(Entry.Replace(TEXT(":24"),*(TEXT(":")+FString(Qty))),TEXT("{}"),EType::ProductionTask));
    for(const TCHAR* Mode:{TEXT("null"),TEXT("\"balance\""),TEXT("1")})
        TestFalse(TEXT("Unknown or mistyped registry modes are refused"),Read(Entry,TEXT("{\"registry_mode\":")+FString(Mode)+TEXT("}"),EType::ProductionTask));
    TestFalse(TEXT("Mode without goods is refused"),Read(TEXT("null"),TEXT("{\"registry_mode\":\"record_only\"}"),EType::ProductionTask));
    TestFalse(TEXT("Combat cannot produce registry entries"),Read(Entry,TEXT("{}"),EType::CombatWave));
    TestFalse(TEXT("Ordinary riding cannot produce registry entries"),Read(Entry,TEXT("{}"),EType::HorsebackRide,TEXT("travel")));
    TestFalse(TEXT("Missing units are refused"),Read(Entry.Replace(TEXT(",\"unit_en\":\"pieces\""),TEXT("")),TEXT("{}"),EType::ProductionTask));
    TestFalse(TEXT("Empty text is refused"),Read(Entry.Replace(TEXT("pieces"),TEXT("  ")),TEXT("{}"),EType::ProductionTask));
    TestFalse(TEXT("Extra balance field is refused"),Read(Entry.LeftChop(1)+TEXT(",\"balance\":24}"),TEXT("{}"),EType::ProductionTask));
    return true;
}
#endif
