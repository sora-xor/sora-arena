#include "SoraGameEvents.h"
#include "Engine/World.h"

USoraGameEvents* USoraGameEvents::Get(const UObject* WorldContext)
{
    const UWorld* World = WorldContext ? WorldContext->GetWorld() : nullptr;
    return World ? World->GetSubsystem<USoraGameEvents>() : nullptr;
}

bool USoraGameEvents::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
    // Only played worlds raise gameplay events; editor and preview worlds do not.
    return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}
