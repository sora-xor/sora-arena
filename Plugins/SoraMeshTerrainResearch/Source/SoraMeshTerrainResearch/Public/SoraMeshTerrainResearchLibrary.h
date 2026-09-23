#pragma once

#include "Kismet/BlueprintFunctionLibrary.h"
#include "SoraMeshTerrainResearchLibrary.generated.h"

/** Opt-in editor bridge for native Mesh Partition APIs which Unreal Python does not expose. */
UCLASS()
class SORAMESHTERRAINRESEARCH_API USoraMeshTerrainResearchLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()

public:
    /** Convert exactly sixteen validated HI tile actors in the separate WP research map. */
    UFUNCTION(BlueprintCallable, Category="SORA|Research")
    static bool ConvertPlacedHiTiles();

    /** Require persisted compiled runtime sections with static meshes and all 16 source modifiers. */
    UFUNCTION(BlueprintCallable, Category="SORA|Research")
    static bool VerifyCompiledSections();
};
