#pragma once
class FJsonObject;
struct FSoraBeat;
struct FSoraSpace;
namespace SoraCatalogLanternWorkshop
{
bool Read(const FJsonObject& Object,FSoraBeat& Beat,const FSoraSpace& Space);
}
