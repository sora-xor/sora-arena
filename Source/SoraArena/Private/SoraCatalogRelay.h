#pragma once
struct FJsonObject;
struct FSoraBeat;
struct FSoraSpace;
namespace SoraCatalogRelay
{
bool Read(const FJsonObject& Object,FSoraBeat& Beat,const FSoraSpace& Space);
}
