#pragma once
#include "CoreMinimal.h"
class FJsonObject;
struct FSoraBeat;
struct FSoraSpace;
namespace SoraCatalogLedger
{
bool Read(const FJsonObject& Object,FSoraBeat& Beat,const FSoraSpace& Space);
bool ReadLockdown(const FJsonObject& Params,FSoraBeat& Beat);
}
