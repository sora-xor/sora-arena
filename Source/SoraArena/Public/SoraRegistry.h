#pragma once
#include "CoreMinimal.h"
#include "SoraText.h"
struct FSoraChapter;

// Offline narrative goods and counters, never currency or wallet state.
enum class ESoraRegistryMode : uint8 { Production, RecordOnly };
struct FSoraRegistryEntry
{
    FString ItemJapanese, ItemEnglish;
    int32 Quantity = 0;
    FString UnitJapanese, UnitEnglish;
    ESoraRegistryMode Mode = ESoraRegistryMode::Production;
    FString Japanese() const;
    FString English() const;
};
enum class ESoraRegistryState : uint8 { Recorded, Inspected, Returned };
struct FSoraRegistryRow
{
    FString BeatId;
    FSoraRegistryEntry Entry;
    ESoraRegistryState State = ESoraRegistryState::Recorded;
    bool HasSplitTally() const { return State == ESoraRegistryState::Inspected; }
};
namespace SoraRegistry
{
// One row per completed authored production, in chapter order. Existing
// checkpoint progress is the only state: retries cannot accumulate quantities.
TArray<FSoraRegistryRow> Completed(const FSoraChapter& Chapter, int32 ChapterIndex, unsigned CompletedMask);
SoraText::FLine Status(ESoraRegistryState State);
}
