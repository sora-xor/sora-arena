#pragma once
#include "CoreMinimal.h"
#include "Dom/JsonObject.h"
struct FSoraBeat;
struct FSoraSpace;
namespace SoraCatalogWardGate { bool Read(const FJsonObject&,FSoraBeat&,const FSoraSpace&); }
