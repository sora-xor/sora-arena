#pragma once
class FJsonObject;
struct FSoraBeat;
struct FSoraChapter;
namespace SoraCatalogTenements
{
bool Read(const FJsonObject& Object,FSoraBeat& Beat,const FSoraChapter& Chapter);
bool ReadDefense(const FJsonObject& Params,FSoraBeat& Beat);
}
