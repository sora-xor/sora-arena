#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "SoraAudioImportLibrary.generated.h"

class USoundClass;
class USoundSubmix;

// Editor-only links for scripts/unreal/import_audio.py, which builds the mix
// buses of docs/audio.md section 2. The engine keeps a submix's parent
// read-only outside its graph editor, so Python cannot build the submix tree
// on its own; sound classes use the same route so both trees are linked alike.
UCLASS()
class USoraAudioImportLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
#if WITH_EDITOR
    // Makes Parent the parent of Child, moving Child from any previous parent,
    // as the submix graph editor does. False, with nothing changed, when the
    // link would close a cycle.
    UFUNCTION(BlueprintCallable, Category = "Sora|Audio")
    static bool SetSubmixParent(USoundSubmix* Child, USoundSubmix* Parent);
    // The same for a sound class.
    UFUNCTION(BlueprintCallable, Category = "Sora|Audio")
    static bool SetSoundClassParent(USoundClass* Child, USoundClass* Parent);
#endif
};
