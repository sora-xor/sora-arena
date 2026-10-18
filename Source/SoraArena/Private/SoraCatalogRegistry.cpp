#include "SoraCatalogRegistry.h"
#include "SoraCatalog.h"
#include "SoraCatalogJson.h"

bool SoraCatalogRegistry::Read(const FJsonObject& Object, FSoraBeat& Beat)
{
    using namespace SoraCatalogJson;
    Beat.Registry.Reset();
    const auto Value = Object.TryGetField(TEXT("registry"));
    const auto Ext = Child(Object, TEXT("ext"));
    if (!Value || !Ext) return false;
    const bool bHasMode = Ext->HasField(TEXT("registry_mode"));
    FString Mode;
    if (bHasMode && (Ext->TryGetField(TEXT("registry_mode"))->Type != EJson::String ||
        !Str(*Ext, TEXT("registry_mode"), Mode) || Mode != TEXT("record_only"))) return false;
    if (Value->IsNull()) return !bHasMode;
    const auto Row = Value->Type == EJson::Object ? Value->AsObject() : nullptr;
    const auto Params = Child(Object, TEXT("params"));
    FString RideMode;
    const bool bCargo = Beat.Is(SoraBeatRules::EType::HorsebackRide) && Params &&
        Str(*Params, TEXT("mode"), RideMode) && RideMode == TEXT("cargo");
    if (!Row || Row->Values.Num() != 5 || (!Beat.Is(SoraBeatRules::EType::ProductionTask) && !bCargo)) return false;
    FSoraRegistryEntry Entry;
    const auto Text = [&](const TCHAR* Key, FString& Out)
    {
        const auto Field = Row->TryGetField(Key);
        return Field && Field->Type == EJson::String && Str(*Row, Key, Out) && !Out.TrimStartAndEnd().IsEmpty();
    };
    const auto Quantity = Row->TryGetField(TEXT("qty"));
    if (!Text(TEXT("item_ja"), Entry.ItemJapanese) || !Text(TEXT("item_en"), Entry.ItemEnglish) ||
        !Text(TEXT("unit_ja"), Entry.UnitJapanese) || !Text(TEXT("unit_en"), Entry.UnitEnglish) ||
        !Quantity || Quantity->Type != EJson::Number || !Int(*Row, TEXT("qty"), Entry.Quantity) || Entry.Quantity <= 0) return false;
    Entry.Mode = bHasMode ? ESoraRegistryMode::RecordOnly : ESoraRegistryMode::Production;
    Beat.Registry = MoveTemp(Entry);
    return true;
}
