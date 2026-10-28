#pragma once
#include "SoraCatalogJson.h"
#include "Combat/SoraEnemyCatalog.h"

namespace SoraCatalogDialogue
{
inline bool ReadSources(const FJsonObject& Row,TArray<FName>& Out)
{
    Out.Reset();
    const auto Ext=SoraCatalogJson::Child(Row,TEXT("ext"));
    if(!Ext)return false;
    if(!Ext->HasField(TEXT("source")))return true;
    TArray<FString> Sources;
    if(!SoraCatalogJson::Strings(SoraCatalogJson::Rows(*Ext,TEXT("source")),Sources)||Sources.IsEmpty()||
       !FSoraEnemyCatalog::Get().Load())return false;
    for(const FString& Source:Sources)
    {
        const FName Name(*Source);
        const auto* Enemy=FSoraEnemyCatalog::Get().Find(Name);
        if(!Enemy||Enemy->Id.ToString()!=Source||Out.Contains(Name))return false;
        Out.Add(Name);
    }
    return true;
}
}
